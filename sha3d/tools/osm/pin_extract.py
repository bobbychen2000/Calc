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
   (a) untagged ways / nodes used only by dropped elements, (b) every feature whose geometry lies inside a dropped
   area (e.g. buildings in a compound). Only counts per class are written; ids, names and positions of dropped
   elements appear in no output file.
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
import os
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'law'))
import extent as EXT  # noqa: E402
import osm_sensitive  # noqa: E402
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, mapping, shape  # noqa: E402
from shapely.ops import linemerge, polygonize, unary_union  # noqa: E402
from shapely.prepared import prep  # noqa: E402

AREA_KEYS = {'building', 'landuse', 'amenity', 'leisure', 'natural', 'place', 'shop', 'tourism', 'office', 'water',
             'parking', 'building:part', 'craft', 'historic', 'sport', 'golf', 'military', 'healthcare', 'boundary'}
AREA_AEROWAY = {'apron', 'terminal', 'hangar', 'helipad', 'aerodrome', 'heliport', 'gate', 'stopway', 'blast_pad',
                'runway_area', 'taxiway_area'}
LINE_NATURAL = {'coastline', 'tree_row', 'cliff', 'ridge', 'arete'}


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
    # areas of dropped features (for the containment rule)
    dropped_areas = []
    for (typ, i), why in drop_reason.items():
        try:
            if typ == 'way' and W[i]['nds'][0] == W[i]['nds'][-1] and len(W[i]['nds']) >= 4:
                dropped_areas.append(Polygon(way_line(i)))
            elif typ == 'relation':
                g = mp_geometry(R[i], W, N, way_line)
                if g is not None and not g.is_empty:
                    dropped_areas.append(g)
        except (ValueError, KeyError):
            pass
    dropped_union = unary_union([g.buffer(0) for g in dropped_areas]) if dropped_areas else None
    dropped_prep = prep(dropped_union) if dropped_union is not None else None
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

    def contained(g):
        return dropped_prep is not None and dropped_prep.contains(g.representative_point()) and \
            dropped_union.buffer(1e-7).contains(g)

    def emit(typ, i, rec, geom, extra=None):
        if geom is not None:
            if geom.is_empty:
                return False
            if not ext_p.intersects(geom):
                counts['outside_extent'] += 1
                return False
            clipped = not ext_p.contains(geom)
            if clipped:
                geom = geom.intersection(ext_ll)
                if geom.is_empty:
                    counts['outside_extent'] += 1
                    return False
            if contained(geom):
                drop_counts[f'{typ}:inside_sensitive_area'] += 1
                return False
        else:
            clipped = None
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

    for i, n in N.items():
        if n['tags'] and ('node', i) not in drop_reason:
            emit('node', i, n, Point(n['lon'], n['lat']))
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
        if emit('way', i, w, g):
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
            if emit('relation', i, r, g):
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
        emit('relation', i, r, None, {'members': mem})
    kept['node'] = {n for n in kept['node'] if n in N and ('node', n) not in drop_reason}

    fc = {'type': 'FeatureCollection',
          'name': 'zsss_osm_pinned',
          'license': 'ODbL-1.0',
          'attribution': '(c) OpenStreetMap contributors, https://www.openstreetmap.org/copyright',
          'note': ('OpenStreetMap extract of the SHA Live 3D detailed extent (convex hull of aerodrome relation '
                   '21913346 + 1 km), downloaded from api.openstreetmap.org/api/0.6/map on 2026-11-14 (UTC times in '
                   'SOURCES.json), sensitive features removed (military, armed police, police, prison, GNSS: counts '
                   'only, in pin_summary.json), clipped to the extent. Database: ODbL 1.0.'),
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
