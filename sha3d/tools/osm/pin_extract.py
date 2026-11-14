"""Build the pinned, filtered, clipped OSM extract of the SHA detailed extent (committed: refs/cache/osm_pinned/).

usage: python3 -I sha3d/tools/osm/pin_extract.py RAW_DIR OUT_DIR
  RAW_DIR  = fetch_osm.py output (map_*.osm tiles + relation_*_full.osm + download_log.jsonl); local only, never
             committed (it still holds the sensitive features)
  OUT_DIR  = refs/cache/osm_pinned/: zsss_osm_pinned.geojson, osm_elements.json, extent_hull1km.geojson,
             pin_summary.json (SOURCES.json is written by write_sources.py)

Steps
1. Merge every tile and relation file (same id must have the same version everywhere: checked).
2. Extent = convex hull of aerodrome relation 21913346 + 1 km (tools/osm/extent.py), 23.5 km2.
3. Sensitive-feature filter (tools/law/osm_sensitive.py): a tagged element that matches is dropped, and so are
   (a) untagged ways / nodes used only by dropped elements, (b) every feature ON / WITHIN 10 m of a dropped area: its
   whole geometry lies inside the dropped areas buffered by SENS_BUFFER_M = 10 m (world metres, tools/common/frame.py;
   e.g. buildings, walls and internal roads of a compound), and (c) every feature ALONG a dropped area: at least
   ALONG_MIN_M = 25 m of its line (or polygon outline) runs within 10 m of a dropped outline (e.g. a perimeter wall
   that continues outside, an adjacent landuse polygon sharing the edge, an admin boundary way). Exception to (c)
   only: public lines that merely pass along (highway=* with a name or of a public road class, railway=*,
   waterway=*) and the aerodrome boundary (aeroway=aerodrome). QA C1 H1
   (docs/phase1/qa_data.md): the earlier rule (representative point strictly inside AND geometry inside a 1 cm buffer)
   kept a perimeter wall.
   Dropped LINES (e.g. military-usage railways) count as sensitive geometry too (re-verify N1,
   docs/phase1/reverify_data.md; fix round 2 in qa_data.md):
   (d) line ON / ALONG: a feature whose whole geometry lies within 10 m of a dropped line (not public roads,
       waterways, passenger railways), or of which >= ALONG_MIN_M of line / outline runs within 10 m of a dropped
       line AND parallel to it (local direction within ALONG_ANG_DEG = 30 deg, so that a road crossing the line at
       a point does not count). Public roads are not exempt here: a road that runs along a dropped line is dropped.
       Exempt: waterways, the aerodrome boundary and passenger railway lines (no service=*, passenger usage).
   (e) railway points: every node with a railway=* tag (level crossing, crossing, buffer stop, switch, ...) within
       RAIL_POINT_M = 30 m of any dropped feature, and every railway point that is a vertex of a dropped railway way
       and of no kept railway way; any other tagged node within 2 m of a dropped line.
   (f) non-passenger railway (service=*, a non-passenger usage, or a disused / abandoned / other non-passenger
       railway value) within RAIL_WAY_M = 100 m of a dropped line or area, and every non-passenger railway way
       connected to one of those through spur / yard / industrial / disused track. Main / high-speed / metro lines and
       the station tracks (sidings, crossovers) away from dropped features are kept.
   Only counts per class are written; ids, names and positions of dropped elements appear in no output file, and
   osm_elements.json lists no node that belongs only to dropped features.
4. Geometry: tagged nodes -> Point; ways -> LineString, or Polygon for closed area ways (area rule below);
   multipolygon relations -> (Multi)Polygon (outer rings minus inner rings, from the member ways); other relations
   (routes, sites, ...) -> geometry null with their member list (members filtered to kept elements).
5. Clip every geometry to the extent polygon (lon/lat; property clipped = true when cut); features fully outside are
   dropped. Coordinates rounded to 1e-7 deg (1 cm).
Each feature carries @type, @id, @version, @timestamp (OSM element metadata; user names are not copied) and its tags.
osm_elements.json lists [id, version] of every kept element, tagged or not (nodes / ways that only shape a kept
feature included), so the pinned state can be re-fetched or compared later (api/0.6/<type>/<id>/<version>).
"""
import glob
import json
import math
import os
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'law'))
sys.path.insert(0, os.path.join(HERE, '..', 'common'))
import extent as EXT  # noqa: E402
import frame as F  # noqa: E402
import osm_sensitive  # noqa: E402
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, mapping, shape  # noqa: E402
from shapely.ops import linemerge, polygonize, unary_union  # noqa: E402
import shapely  # noqa: E402
from shapely.prepared import prep  # noqa: E402

AREA_KEYS = {'building', 'landuse', 'amenity', 'leisure', 'natural', 'place', 'shop', 'tourism', 'office', 'water',
             'parking', 'building:part', 'craft', 'historic', 'sport', 'golf', 'military', 'healthcare', 'boundary'}
AREA_AEROWAY = {'apron', 'terminal', 'hangar', 'helipad', 'aerodrome', 'heliport', 'gate', 'stopway', 'blast_pad',
                'runway_area', 'taxiway_area'}
LINE_NATURAL = {'coastline', 'tree_row', 'cliff', 'ridge', 'arete'}
SENS_BUFFER_M = 10.0      # on / within this distance of a dropped (sensitive) area -> dropped
ALONG_MIN_M = 25.0        # at least this length within SENS_BUFFER_M of a dropped outline -> dropped (unless public)
PUBLIC_ROADS = {'motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'unclassified', 'residential',
                'motorway_link', 'trunk_link', 'primary_link', 'secondary_link', 'tertiary_link', 'living_street'}
ALONG_ANG_DEG = 30.0      # rule (d): "along a dropped line" = within SENS_BUFFER_M and within this angle of its direction
ON_LINE_M = 2.0           # rule (e): any tagged node this close to a dropped line is dropped
RAIL_POINT_M = 30.0       # rule (e): railway=* nodes within this distance of any dropped feature are dropped
RAIL_WAY_M = 100.0        # rule (f): non-passenger railway ways within this distance of a dropped line / area are dropped
PASSENGER_RAIL = {'rail', 'subway', 'light_rail', 'tram', 'monorail'}
RAIL_STATION = {'platform', 'station', 'halt', 'stop', 'subway_entrance', 'platform_edge', 'train_station_entrance'}
NON_PASSENGER_USAGE = {'industrial', 'military', 'freight', 'test', 'tourism'}


def _xz(g):
    """lon/lat shapely geometry -> world metres (x east, z south; tools/common/frame.py)"""
    return shapely.transform(g, lambda c: [F.ll_to_world(la, lo) for lo, la in c])


def passenger_rail(tags):
    """railway that is a passenger line or station (kept near dropped features); everything else with railway=* is
    non-passenger for rule (f)"""
    r = tags.get('railway')
    if r in RAIL_STATION:
        return True
    if r == 'construction':
        r = tags.get('construction') or ('rail' if tags.get('usage') in ('main', 'branch') else None)
    return (r in PASSENGER_RAIL and 'service' not in tags and tags.get('usage') not in NON_PASSENGER_USAGE)


def cascade_rail(tags):
    """non-passenger track through which rule (f) spreads from a dropped railway way to the ways connected to it:
    spur / yard / industrial / disused track, not the sidings and crossovers of a station"""
    if 'railway' not in tags or passenger_rail(tags):
        return False
    return tags.get('usage') in NON_PASSENGER_USAGE or tags.get('service') not in ('siding', 'crossover')


def line_exempt(tags):
    """rule (d) exemptions: waterways, the aerodrome boundary, passenger railway lines"""
    return 'waterway' in tags or tags.get('aeroway') == 'aerodrome' or ('railway' in tags and passenger_rail(tags))


def parallel_len(line, dls, band_geom, ang_deg, step=1.0):
    """length of `line` (world metres) inside `band_geom` (the dropped lines `dls` buffered) and within `ang_deg` of
    the local direction of the nearest dropped line (a road crossing the line at a point does not count)"""
    near = line.intersection(band_geom)
    if near.is_empty:
        return 0.0
    parts = [g for g in getattr(near, 'geoms', [near]) if g.geom_type == 'LineString' and g.length > 0]
    tot = 0.0
    for p in parts:
        n = max(1, int(math.ceil(p.length / step)))
        for k in range(n):
            a, b = p.length * k / n, p.length * (k + 1) / n
            pa, pb, m = p.interpolate(a), p.interpolate(b), p.interpolate((a + b) / 2)
            dl = min(dls, key=lambda g: g.distance(m))
            t = dl.project(m)
            q1, q2 = dl.interpolate(max(0.0, t - 1.0)), dl.interpolate(min(dl.length, t + 1.0))
            d = math.degrees(math.atan2(pb.y - pa.y, pb.x - pa.x) - math.atan2(q2.y - q1.y, q2.x - q1.x))
            if abs((d + 90.0) % 180.0 - 90.0) <= ang_deg:
                tot += b - a
    return tot


def public_passing(tags):
    """public transport lines kept when they only pass along a dropped area (rule (c) exception)"""
    if 'railway' in tags or 'waterway' in tags or tags.get('aeroway') == 'aerodrome':
        return True     # aerodrome: the boundary of the aerodrome itself (public, charted), not a facility outline
    h = tags.get('highway')
    return bool(h) and (h in PUBLIC_ROADS or bool(tags.get('name')))


def is_area(tags, closed):
    if not closed:
        return False
    if tags.get('area') == 'no':
        return False
    if tags.get('area') == 'yes':
        return True
    if tags.get('aeroway') in AREA_AEROWAY:
        return True
    if tags.get('natural') in LINE_NATURAL:
        return False
    if tags.get('waterway') in ('riverbank', 'dock', 'boatyard'):
        return True
    if tags.get('man_made') in ('bridge', 'pier', 'tower', 'works', 'wastewater_plant', 'water_works', 'storage_tank',
                                'silo', 'reservoir_covered', 'mast', 'chimney'):
        return True
    if tags.get('railway') == 'platform' or tags.get('public_transport') in ('platform', 'station'):
        return True
    if tags.get('highway') in ('pedestrian', 'services', 'rest_area', 'platform'):
        return True
    if any(k in tags for k in ('highway', 'barrier', 'railway', 'waterway', 'power', 'route')):
        return False
    return any(k in tags for k in AREA_KEYS)


def load(raw):
    paths = sorted(glob.glob(os.path.join(raw, 'map_*.osm'))) + sorted(glob.glob(os.path.join(raw, '*_full.osm')))
    N, W, R = {}, {}, {}
    conflicts = 0
    for p in paths:
        for e in ET.parse(p).getroot():
            if e.tag not in ('node', 'way', 'relation'):
                continue
            meta = dict(version=int(e.get('version')), timestamp=e.get('timestamp'))
            tags = {t.get('k'): t.get('v') for t in e.findall('tag')}
            i = int(e.get('id'))
            if e.tag == 'node':
                rec = dict(lat=float(e.get('lat')), lon=float(e.get('lon')), tags=tags, **meta); D = N
            elif e.tag == 'way':
                rec = dict(nds=[int(n.get('ref')) for n in e.findall('nd')], tags=tags, **meta); D = W
            else:
                rec = dict(members=[(m.get('type'), int(m.get('ref')), m.get('role')) for m in e.findall('member')],
                           tags=tags, **meta); D = R
            if i in D and D[i]['version'] != rec['version']:
                conflicts += 1
                if rec['version'] < D[i]['version']:
                    continue
            D[i] = rec
    return N, W, R, conflicts, paths


def main(raw, out):
    os.makedirs(out, exist_ok=True)
    N, W, R, conflicts, paths = load(raw)
    ex = EXT.extent_from_relation(os.path.join(raw, 'relation_21913346_full.osm'))
    ext_ll = Polygon([(lon, lat) for lat, lon in ex['ring_ll']])
    ext_p = prep(ext_ll)

    def way_line(w):
        pts = [(N[n]['lon'], N[n]['lat']) for n in W[w]['nds'] if n in N]
        return pts

    # ---------------- 3. sensitive filter
    drop_reason = {}                      # (type, id) -> class
    for typ, D in (('node', N), ('way', W), ('relation', R)):
        for i, rec in D.items():
            why = osm_sensitive.sensitive_reason(rec['tags'])
            if why:
                drop_reason[(typ, i)] = why
    # members of dropped relations that are untagged (or only used by dropped things) go too
    used_by_kept_way = defaultdict(int)
    for wid, w in W.items():
        if ('way', wid) not in drop_reason:
            for n in w['nds']:
                used_by_kept_way[n] += 1
    rel_member_ways = defaultdict(set)
    for rid, r in R.items():
        for t, ref, role in r['members']:
            if t == 'way':
                rel_member_ways[ref].add(rid)
    for (typ, i), why in list(drop_reason.items()):
        if typ == 'relation':
            for t, ref, role in R[i]['members']:
                if t == 'way' and ref in W and not W[ref]['tags'] and all(
                        ('relation', r2) in drop_reason for r2 in rel_member_ways[ref]):
                    drop_reason[('way', ref)] = why + '_member'
    # dropped geometries: areas (rules b, c), lines (rule d), points; any of them (rule e)
    dropped_areas, dropped_lines, dropped_points = [], [], []
    for (typ, i), why in drop_reason.items():
        try:
            if typ == 'way' and W[i]['nds'][0] == W[i]['nds'][-1] and len(W[i]['nds']) >= 4:
                dropped_areas.append(Polygon(way_line(i)))
            elif typ == 'way' and not why.endswith('_member') and len(way_line(i)) >= 2:
                dropped_lines.append(LineString(way_line(i)))
            elif typ == 'node' and i in N:
                dropped_points.append(Point(N[i]['lon'], N[i]['lat']))
            elif typ == 'relation':
                g = mp_geometry(R[i], W, N, way_line)
                if g is not None and not g.is_empty:
                    dropped_areas.append(g)
        except (ValueError, KeyError):
            pass
    dropped_union = unary_union([g.buffer(0) for g in dropped_areas]) if dropped_areas else None
    if dropped_union is not None:
        du_xz = _xz(dropped_union)
        near_area = prep(du_xz.buffer(SENS_BUFFER_M))                 # rule (b): whole geometry inside -> drop
        outline_band = du_xz.boundary.buffer(SENS_BUFFER_M)           # rule (c): length along the outline
        outline_band_p = prep(outline_band)
    else:
        du_xz = near_area = outline_band = outline_band_p = None
    dl_xz = [_xz(g) for g in dropped_lines]
    if dl_xz:
        dl_union = unary_union(dl_xz)
        line_band = dl_union.buffer(SENS_BUFFER_M)                    # rule (d)
        line_band_p = prep(line_band)
        on_line_p = prep(dl_union.buffer(ON_LINE_M))                  # rule (e), any tagged node on the line
    else:
        dl_union = line_band = line_band_p = on_line_p = None
    sens_lines_areas = [g for g in (du_xz, dl_union) if g is not None]
    sens_all = sens_lines_areas + [_xz(g) for g in dropped_points]
    rail_point_zone = prep(unary_union(sens_all).buffer(RAIL_POINT_M)) if sens_all else None     # rule (e)
    rail_way_zone = prep(unary_union(sens_lines_areas).buffer(RAIL_WAY_M)) if sens_lines_areas else None  # (f)
    # recompute node usage after member drops
    used_by_kept_way = defaultdict(int)
    for wid, w in W.items():
        if ('way', wid) not in drop_reason:
            for n in w['nds']:
                used_by_kept_way[n] += 1

    # ---------------- 4/5. geometry + clip
    feats = []
    kept = {'node': set(), 'way': set(), 'relation': set()}
    counts = Counter()
    drop_counts = Counter()
    for (typ, i), why in drop_reason.items():
        drop_counts[f'{typ}:{why}'] += 1

    def sensitive_near(g, tags):
        """rule (b) 'inside_sensitive_area', (c) 'along_sensitive_area', (d) 'on_dropped_line' /
        'along_dropped_line', (e) 'railway_point_near_dropped' (points), or None"""
        gx = _xz(g)
        if near_area is not None:
            if near_area.contains(gx):
                return 'inside_sensitive_area'
            if not public_passing(tags) and outline_band_p.intersects(gx):
                line = gx.boundary if gx.geom_type in ('Polygon', 'MultiPolygon') else gx
                if line.geom_type in ('LineString', 'MultiLineString', 'LinearRing') and \
                        line.intersection(outline_band).length >= ALONG_MIN_M:
                    return 'along_sensitive_area'
        if gx.geom_type == 'Point':
            if rail_point_zone is not None and any(k == 'railway' or k.startswith('railway:') for k in tags) and \
                    rail_point_zone.contains(gx):
                return 'railway_point_near_dropped'
            if on_line_p is not None and on_line_p.contains(gx):
                return 'on_dropped_line'
            return None
        if line_band_p is None or line_exempt(tags) or not line_band_p.intersects(gx):
            return None
        if 'highway' not in tags and line_band_p.contains(gx):
            return 'on_dropped_line'
        line = gx.boundary if gx.geom_type in ('Polygon', 'MultiPolygon') else gx
        if line.geom_type in ('LineString', 'MultiLineString', 'LinearRing') and \
                parallel_len(line, dl_xz, line_band, ALONG_ANG_DEG) >= ALONG_MIN_M:
            return 'along_dropped_line'
        return None

    def prepare(rec, geom):
        """clip + sensitive rules -> ('ok', geom, clipped) | ('outside', None, None) | ('drop', reason, None)"""
        if geom is None:
            return ('ok', None, None)
        if geom.is_empty or not ext_p.intersects(geom):
            return ('outside', None, None) if not geom.is_empty else ('empty', None, None)
        clipped = not ext_p.contains(geom)
        if clipped:
            geom = geom.intersection(ext_ll)
            if geom.is_empty:
                return ('outside', None, None)
        why_near = sensitive_near(geom, rec['tags'])
        if why_near:
            return ('drop', why_near, None)
        return ('ok', geom, clipped)

    def emit(typ, i, rec, dec, extra=None):
        st, geom, clipped = dec
        if st == 'empty':
            return False
        if st == 'outside':
            counts['outside_extent'] += 1
            return False
        if st == 'drop':
            drop_counts[f'{typ}:{geom}'] += 1
            return False
        props = {'@type': typ, '@id': i, '@version': rec['version'], '@timestamp': rec['timestamp']}
        if clipped:
            props['clipped'] = True
        props['tags'] = rec['tags']
        if extra:
            props.update(extra)
        feats.append({'type': 'Feature', 'properties': props,
                      'geometry': _round(mapping(geom)) if geom is not None else None})
        kept[typ].add(i)
        counts[f'{typ}_features'] += 1
        return True

    # ways first (decisions only), so that rule (e) can see which railway ways are dropped
    way_dec = {}
    for i, w in W.items():
        if ('way', i) in drop_reason or not w['tags']:
            continue
        pts = way_line(i)
        if len(pts) < 2:
            continue
        closed = w['nds'][0] == w['nds'][-1] and len(pts) >= 4
        if is_area(w['tags'], closed):
            g = Polygon(pts)
            if not g.is_valid:
                g = g.buffer(0)
        else:
            g = LineString(pts)
        way_dec[i] = prepare(w, g)
    # rule (f): non-passenger railway near dropped lines / areas, and the non-passenger track connected to it
    if rail_way_zone is not None:
        rail_n2w = defaultdict(list)
        for i, dec in way_dec.items():
            if dec[0] == 'ok' and 'railway' in W[i]['tags']:
                for n in W[i]['nds']:
                    rail_n2w[n].append(i)
        seeds = [i for i, dec in way_dec.items() if dec[0] == 'ok' and 'railway' in W[i]['tags'] and
                 not passenger_rail(W[i]['tags']) and rail_way_zone.intersects(_xz(dec[1]))]
        for i in seeds:
            way_dec[i] = ('drop', 'non_passenger_railway_near_dropped', None)
        todo = list(seeds)
        while todo:
            j = todo.pop()
            for n in W[j]['nds']:
                for k in rail_n2w[n]:
                    if way_dec[k][0] == 'ok' and cascade_rail(W[k]['tags']):
                        way_dec[k] = ('drop', 'non_passenger_railway_connected', None)
                        todo.append(k)
    # rule (e), second part: railway points on dropped railway ways only
    rail_nodes_dropped, rail_nodes_kept = set(), set()
    for (typ, i), why in drop_reason.items():
        if typ == 'way' and 'railway' in W[i]['tags']:
            rail_nodes_dropped.update(W[i]['nds'])
    for i, dec in way_dec.items():
        if 'railway' in W[i]['tags']:
            (rail_nodes_kept if dec[0] == 'ok' else rail_nodes_dropped if dec[0] == 'drop' else set()).update(
                W[i]['nds'])

    for i, n in N.items():
        if n['tags'] and ('node', i) not in drop_reason:
            dec = prepare(n, Point(n['lon'], n['lat']))
            if dec[0] == 'ok' and 'railway' in n['tags'] and i in rail_nodes_dropped and i not in rail_nodes_kept:
                dec = ('drop', 'railway_point_of_dropped_railway', None)
            emit('node', i, n, dec)
    for i, w in W.items():
        if i in way_dec and emit('way', i, w, way_dec[i]):
            for n in w['nds']:
                kept['node'].add(n)
    # multipolygons; untagged member ways of kept multipolygons are kept as elements (no own feature)
    for i, r in R.items():
        if ('relation', i) in drop_reason or not r['tags']:
            continue
        if r['tags'].get('type') in ('multipolygon',):
            g = mp_geometry(r, W, N, way_line)
            if g is None:
                counts['multipolygon_incomplete'] += 1
                continue
            if emit('relation', i, r, prepare(r, g)):
                for t, ref, role in r['members']:
                    if t == 'way' and ref in W and ('way', ref) not in drop_reason:
                        kept['way'].add(ref)
                        kept['node'].update(W[ref]['nds'])
    for i, r in R.items():
        if ('relation', i) in drop_reason or not r['tags'] or r['tags'].get('type') == 'multipolygon':
            continue
        if r['tags'].get('type') == 'boundary' or 'admin_level' in r['tags']:
            counts['boundary_relations_skipped'] += 1
            continue
        mem = [[t, ref, role] for t, ref, role in r['members'] if ref in kept.get(t, set())]
        if not mem:
            counts['relations_without_kept_members'] += 1
            continue
        emit('relation', i, r, ('ok', None, None), {'members': mem})
    kept['node'] = {n for n in kept['node'] if n in N and ('node', n) not in drop_reason}
    # osm_elements.json must not list a node that belongs only to dropped features: every listed node is a kept
    # tagged node, a vertex of a kept way (incl. kept multipolygon member ways) or a node member of a kept relation
    owners = {f['properties']['@id'] for f in feats if f['properties']['@type'] == 'node'}
    for wid in kept['way']:
        owners.update(W[wid]['nds'])
    for rid in kept['relation']:
        owners.update(ref for t, ref, role in R[rid]['members'] if t == 'node')
    orphans = kept['node'] - owners
    assert not orphans, 'listed nodes without a kept owner: %d' % len(orphans)

    fc = {'type': 'FeatureCollection',
          'name': 'zsss_osm_pinned',
          'license': 'ODbL-1.0',
          'attribution': '(c) OpenStreetMap contributors, https://www.openstreetmap.org/copyright',
          'note': ('OpenStreetMap extract of the SHA Live 3D detailed extent (convex hull of aerodrome relation '
                   '21913346 + 1 km), downloaded from api.openstreetmap.org/api/0.6/map on 2026-11-14 (UTC times in '
                   'SOURCES.json), sensitive features removed (military, armed police, police, prison, GNSS), together with '
                   'every feature on, within %g m of, or running >= %g m along a dropped area or line, railway '
                   'points within %g m of a dropped feature and non-passenger railway within %g m of a dropped line '
                   'or area (counts only, in pin_summary.json), clipped to the extent. Database: ODbL 1.0.'
                   % (SENS_BUFFER_M, ALONG_MIN_M, RAIL_POINT_M, RAIL_WAY_M)),
          'features': feats}
    with open(os.path.join(out, 'zsss_osm_pinned.geojson'), 'w') as f:
        json.dump(fc, f, ensure_ascii=False, separators=(',', ':'))
    elements = {t: sorted([[i, (N if t == 'node' else W if t == 'way' else R)[i]['version']] for i in s])
                for t, s in kept.items()}
    with open(os.path.join(out, 'osm_elements.json'), 'w') as f:
        json.dump({'what': 'id and version of every OSM element kept in zsss_osm_pinned.geojson (incl. untagged '
                           'nodes and member ways that only shape kept features)', **elements}, f,
                  separators=(',', ':'))
    with open(os.path.join(out, 'extent_hull1km.geojson'), 'w') as f:
        json.dump({'type': 'FeatureCollection', 'features': [
            {'type': 'Feature', 'properties': {
                'what': 'SHA Live 3D detailed extent: convex hull of OSM relation 21913346 (v%d, %s) + 1000 m buffer'
                        % (ex['relation_version'], ex['relation_timestamp']),
                'area_km2': round(ex['area_km2'], 3), 'hull_area_km2': round(ex['hull_area_km2'], 3),
                'frame': 'buffered in the world frame (tools/common/frame.py), vertices mapped back to WGS 84'},
             'geometry': _round(mapping(ext_ll))}]}, f)
    ts = [rec['timestamp'] for D in (N, W, R) for rec in D.values()]
    log = [json.loads(l) for l in open(os.path.join(raw, 'download_log.jsonl'))]
    summary = {
        'downloaded_utc': [log[0]['start_utc'], log[-1]['end_utc']],
        'requests': len(log),
        'newest_element_timestamp': max(ts),
        'raw_elements': {'node': len(N), 'way': len(W), 'relation': len(R)},
        'version_conflicts_between_tiles': conflicts,
        'extent': {'area_km2': round(ex['area_km2'], 3), 'hull_area_km2': round(ex['hull_area_km2'], 3),
                   'bbox_ll': [round(v, 6) for v in ex['bbox_ll']], 'relation': ex['relation'],
                   'relation_version': ex['relation_version'], 'relation_timestamp': ex['relation_timestamp']},
        'kept_features': len(feats),
        'kept_elements': {t: len(s) for t, s in kept.items()},
        'counts': dict(counts),
        'dropped_sensitive': dict(sorted(drop_counts.items())),
        'dropped_note': 'counts only; ids, names and positions of dropped elements are not written anywhere',
        'dropped_rules': {
            'tags': 'tools/law/osm_sensitive.py',
            'inside_sensitive_area': 'whole geometry within %g m of a dropped area' % SENS_BUFFER_M,
            'along_sensitive_area': '>= %g m of line / outline within %g m of a dropped outline (public roads, '
                                    'railways, waterways and the aerodrome boundary exempt)' % (ALONG_MIN_M, SENS_BUFFER_M),
            'on_dropped_line': 'whole geometry within %g m of a dropped line (roads, waterways, passenger railways and '
                               'the aerodrome boundary exempt), or a tagged node within %g m of it'
                               % (SENS_BUFFER_M, ON_LINE_M),
            'along_dropped_line': '>= %g m of line / outline within %g m of a dropped line and within %g deg of its '
                                  'direction (crossings do not count; public roads NOT exempt; waterways, passenger '
                                  'railways and the aerodrome boundary exempt)' % (ALONG_MIN_M, SENS_BUFFER_M, ALONG_ANG_DEG),
            'railway_point_near_dropped': 'node with a railway=* tag within %g m of any dropped feature' % RAIL_POINT_M,
            'railway_point_of_dropped_railway': 'railway=* node that is a vertex of a dropped railway way and of no '
                                                'kept railway way',
            'non_passenger_railway_near_dropped': 'railway way that is not a passenger line or station (service=*, '
                                                  'non-passenger usage, disused, ...) within %g m of a dropped line or '
                                                  'area' % RAIL_WAY_M,
            'non_passenger_railway_connected': 'non-passenger railway way connected to a dropped one through spur / '
                                               'yard / industrial / disused track (not station sidings or crossovers)'},
        'osm_elements_check': {'listed_nodes_without_kept_owner': 0,
                               'note': 'every listed node is a kept tagged node, a vertex of a kept way or a member of '
                                       'a kept relation; kept roads keep their vertex where they cross a dropped line '
                                       '(a crossing point; no kept road runs along one)'},
        'origin_nodes_check': {str(i): [N[i]['lat'], N[i]['lon'], N[i]['version']] for i in (3336195147, 13556389849)
                               if i in N},
    }
    with open(os.path.join(out, 'pin_summary.json'), 'w') as f:
        json.dump(summary, f, indent=1)
    print(json.dumps(summary, indent=1))


def mp_geometry(r, W, N, way_line):
    outer, inner = [], []
    for t, ref, role in r['members']:
        if t != 'way':
            continue
        if ref not in W:
            return None
        pts = way_line(ref)
        if len(pts) < 2:
            return None
        (inner if role == 'inner' else outer).append(LineString(pts))
    if not outer:
        return None

    def rings(lines):
        polys = list(polygonize(linemerge(lines) if len(lines) > 1 else lines))
        return polys
    po = rings(outer)
    if not po:
        return None
    g = unary_union([p.buffer(0) for p in po])
    if inner:
        pi = rings(inner)
        if pi:
            g = g.difference(unary_union([p.buffer(0) for p in pi]))
    return g


def _round(geo):
    def rr(c):
        if isinstance(c, (list, tuple)) and c and isinstance(c[0], (int, float)):
            return [round(c[0], 7), round(c[1], 7)]
        return [rr(x) for x in c]
    if geo['type'] == 'GeometryCollection':
        return {'type': 'GeometryCollection', 'geometries': [_round(g) for g in geo['geometries']]}
    return {'type': geo['type'], 'coordinates': rr(geo['coordinates'])}


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
