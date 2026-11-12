"""Parse the pinned OSM extract of KHWD (tools/osm/fetch_osm.py) into airfield features in the HWD world frame.

Forked from sfo3d/tools/xcheck/parse_osm.py @ a967f9b. Kept: geom() / prov() helpers, one record per OSM element with its
provenance and tags, world coordinates from the shared frame module. Changed: input = overpass_khwd_latest.meta.json
-> its file; frame = tools/common/hwd_frame.py wgs84_to_world (OSM coordinates are WGS 84; the function applies the
NAD83(2011) -> WGS 84 (G2296) displacement at the HWD ARP @ 2026.86); features grouped by kind (list below) with
airfield subsets of the bbox-wide keys (buildings, fences, roads, landuse) selected by the aerodrome polygon; multipolygon
relations assembled from their member geometry; OSM user names are not copied (type/id/version/timestamp/changeset
are; since the Phase 1 review the pinned extract itself carries no user / uid); the output carries the ODbL licence URI
and the OSM attribution (ODbL 4.2(b)/(c)). Dropped (SFO only): parking_position / gate / jet_bridge handling (the HWD extract has none: checked below),
lighting masts by tower:type=lighting (kept generically in `mast_beacon`).

Kinds (one per element, first rule that matches, in this order):
  aerodrome         aeroway=aerodrome (the polygon that defines "inside the aerodrome")
  runway            aeroway=runway (ref, width, length, surface tags as mapped)
  runway_feature    aeroway in threshold / displaced_threshold / stopway / blast_pad
  taxiway           aeroway=taxiway (ref; status = disused / abandoned when tagged so)
  taxilane          aeroway=taxilane
  apron             aeroway=apron (name / ref)
  holding_position  aeroway=holding_position (ref)
  helipad           aeroway=helipad
  control_tower     aeroway in control_tower / tower, building=control_tower, or man_made=tower with tower:type in
                    observation / air_traffic_control or service=aircraft_control
  windsock          aeroway=windsock or man_made=windsock
  fuel              amenity=fuel
  fire_station      amenity=fire_station or building=fire_station
  hangar            aeroway=hangar or building=hangar (name)
  navaid            aeroway=navigationaid or navigationaid=*
  airmark           airmark=*
  mast_beacon       man_made in mast / beacon / flagpole / tower (other than control towers)
  lifecycle_aeroway a [prefix]:aeroway key (disused:, abandoned:, construction:, proposed:, area: ...)
  building          building=*                             } kept when the footprint meets the aerodrome polygon grown
  fence             barrier in fence / wall                } by NEAR_M (perimeter features are drawn on or just outside
  gate              barrier in gate / lift_gate / sliding_ } the boundary line); the others are only counted
                    gate / swing_gate                      } (`outside_counts`)
  service_road      highway in service / footway meeting the aerodrome polygon itself (airside roads; `inside_frac` =
                    share of the length inside)
  landuse           landuse=* meeting the aerodrome polygon
  poi               any other element with a name or an amenity whose position is within NEAR_M of the aerodrome
  other_aeroway     any other aeroway value (none expected)
Each record: osm {type, id, version, timestamp, changeset}, tags, geom ('point' | 'line' | 'area'), ll [[lat, lon], ...]
(WGS 84, as in OSM; areas: outer ring, closed), w [[x, z], ...] (world metres, 0.01 m), c_w (centroid / midpoint),
len_m (lines), area_m2 (areas), in_aerodrome (centroid inside the aerodrome polygon), d_aerodrome_m (distance of the
geometry to the aerodrome polygon, 0 inside), plus ref / name / status where they apply. Multipolygons carry `rings_w`
(outer and inner rings).
Writes refs/cache/osm/khwd_features.json (ODbL 1.0, (c) OpenStreetMap contributors).
Usage: python3 tools/osm/parse_osm.py
"""
import json, math, os, re, sys
from collections import Counter

import numpy as np
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import linemerge, polygonize, unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))            # hwd3d/
sys.path.insert(0, os.path.join(ROOT, 'tools', 'common'))
import hwd_frame as G                                               # noqa: E402

OSM_DIR = os.path.join(ROOT, 'refs', 'cache', 'osm')
LATEST = os.path.join(OSM_DIR, 'overpass_khwd_latest.meta.json')
OUT = os.path.join(OSM_DIR, 'khwd_features.json')
AERO_WAY = 186495935          # aeroway=aerodrome "Hayward Executive Airport" (tools/osm/fetch_osm.py AERO_WAY)
NEAR_M = 30.0                 # buildings / fences / gates / POIs kept within this distance of the aerodrome polygon
                              # [chosen: the aerodrome way follows the fence line in places and the street front in
                              # others; 30 m keeps features on or just outside it - see the report for what it drops]
AREA_KEYS = ('building', 'landuse', 'amenity', 'leisure', 'natural', 'man_made', 'area:aeroway')
AREA_AEROWAY = ('aerodrome', 'apron', 'hangar', 'helipad', 'terminal', 'control_tower', 'tower', 'heliport')
BARRIER_GATE = ('gate', 'lift_gate', 'sliding_gate', 'swing_gate')
LIFECYCLE = re.compile(r'^([a-z_]+):aeroway$')


def prov(e):
    return {k: e.get(k) for k in ('type', 'id', 'version', 'timestamp', 'changeset')}


def way_ll(e):
    return [(g['lat'], g['lon']) for g in e.get('geometry', []) if g]


def to_w(ll):
    if not ll: return np.zeros((0, 2))
    a = np.asarray(ll, float); x, z = G.wgs84_to_world_np(a[:, 0], a[:, 1])
    return np.stack([x, z], 1)


def is_area(e, t):
    """closed way that is an area by OSM convention (area=yes, or an area-type key)"""
    g = e.get('geometry') or []
    if len(g) < 4 or (g[0]['lat'], g[0]['lon']) != (g[-1]['lat'], g[-1]['lon']): return False
    if t.get('area') == 'no': return False
    if t.get('area') == 'yes': return True
    if t.get('aeroway') in AREA_AEROWAY: return True
    if t.get('barrier') or t.get('highway') or t.get('aeroway') in ('runway', 'taxiway', 'taxilane'): return False
    return any(k in t for k in AREA_KEYS)


def relation_rings(e):
    """multipolygon relation (Overpass `out geom`: members carry geometry) -> [outer rings], [inner rings] as lat/lon"""
    outer, inner = [], []
    for m in e.get('members', []):
        if m.get('type') != 'way' or not m.get('geometry'): continue
        ls = LineString([(g['lon'], g['lat']) for g in m['geometry'] if g])
        (inner if m.get('role') == 'inner' else outer).append(ls)
    def rings(lines):
        out = []
        for p in polygonize(linemerge(lines) if lines else []):
            out.append([(y, x) for x, y in p.exterior.coords])
        return out
    return rings(outer), rings(inner)


def kind_of(t):
    a = t.get('aeroway'); mm = t.get('man_made'); b = t.get('building'); am = t.get('amenity'); br = t.get('barrier')
    if a == 'aerodrome': return 'aerodrome'
    if a == 'runway': return 'runway'
    if a in ('threshold', 'displaced_threshold', 'stopway', 'blast_pad'): return 'runway_feature'
    if a == 'taxiway': return 'taxiway'
    if a == 'taxilane': return 'taxilane'
    if a == 'apron': return 'apron'
    if a == 'holding_position': return 'holding_position'
    if a == 'helipad': return 'helipad'
    if a in ('control_tower', 'tower') or b == 'control_tower' or (mm == 'tower' and (
            t.get('tower:type') in ('observation', 'air_traffic_control') or 'aircraft_control' in t.get('service', ''))):
        return 'control_tower'
    if a == 'windsock' or mm == 'windsock': return 'windsock'
    if am == 'fuel': return 'fuel'
    if am == 'fire_station' or b == 'fire_station': return 'fire_station'
    if a == 'hangar' or b == 'hangar': return 'hangar'
    if a == 'navigationaid' or 'navigationaid' in t: return 'navaid'
    if 'airmark' in t: return 'airmark'
    if mm in ('mast', 'beacon', 'flagpole', 'tower'): return 'mast_beacon'
    if any(LIFECYCLE.match(k) for k in t): return 'lifecycle_aeroway'
    if b: return 'building'
    if br in ('fence', 'wall'): return 'fence'
    if br in BARRIER_GATE: return 'gate'
    if t.get('highway') in ('service', 'footway'): return 'service_road'
    if 'landuse' in t: return 'landuse'
    if 'name' in t or am: return 'poi'
    if a: return 'other_aeroway'
    return None


NEAR_KINDS = ('building', 'fence', 'gate', 'poi')      # kept within NEAR_M of the aerodrome polygon
INSIDE_KINDS = ('service_road', 'landuse')             # kept when they meet the aerodrome polygon itself


def main():
    meta = json.load(open(LATEST))
    src = os.path.join(OSM_DIR, meta['file'])
    raw = json.load(open(src))
    E = raw['elements']
    aero = [e for e in E if e['type'] == 'way' and e['id'] == AERO_WAY]
    assert aero, 'aerodrome way %d not in %s' % (AERO_WAY, meta['file'])
    APW = Polygon(to_w(way_ll(aero[0])))
    assert APW.is_valid and APW.area > 1e5, 'aerodrome polygon invalid'
    feats, outside, notes = {}, Counter(), []
    unparsed = Counter()
    for e in E:
        t = e.get('tags') or {}
        k = kind_of(t)
        if k is None: unparsed[e['type']] += 1; continue
        rec = {'osm': prov(e), 'tags': t}
        rings_ll = None
        if e['type'] == 'node':
            ll = [(e['lat'], e['lon'])]; gk = 'point'
        elif e['type'] == 'way':
            ll = way_ll(e); gk = 'area' if is_area(e, t) else ('line' if len(ll) >= 2 else 'point')
        else:
            if t.get('type') not in ('multipolygon', 'boundary'):
                notes.append('relation %d (%s) type=%s: members only' % (e['id'], k, t.get('type')))
                rec.update({'geom': 'relation', 'members': [{x: m.get(x) for x in ('type', 'ref', 'role')} for m in e.get('members', [])]})
                feats.setdefault(k, []).append(rec); continue
            outer, inner = relation_rings(e)
            if not outer: notes.append('relation %d (%s): no closed outer ring from member geometry' % (e['id'], k)); continue
            outer.sort(key=lambda r: -Polygon([(b, a) for a, b in r]).area)
            ll = outer[0]; gk = 'area'; rings_ll = (outer, inner)
        W = to_w(ll)
        if gk == 'point':
            geo = Point(W[0]); c = W[0]
        elif gk == 'line':
            geo = LineString(W); c = np.asarray(geo.interpolate(0.5, normalized=True).coords[0])
            rec['len_m'] = round(geo.length, 2)
        else:
            if rings_ll:
                polys = [Polygon(to_w(r)) for r in rings_ll[0]]
                holes = [Polygon(to_w(r)) for r in rings_ll[1]]
                geo = unary_union(polys).difference(unary_union(holes)) if holes else unary_union(polys)
                rec['rings_w'] = {'outer': [np.round(to_w(r), 2).tolist() for r in rings_ll[0]],
                                  'inner': [np.round(to_w(r), 2).tolist() for r in rings_ll[1]]}
            else:
                geo = Polygon(W)
                if not geo.is_valid: geo = geo.buffer(0); notes.append('%s %d: invalid polygon repaired' % (e['type'], e['id']))
            c = np.asarray(geo.centroid.coords[0]); rec['area_m2'] = round(geo.area, 1)
        d = 0.0 if geo.intersects(APW) else geo.distance(APW)
        rec.update({'geom': gk, 'll': [[round(a, 7), round(b, 7)] for a, b in ll], 'w': np.round(W, 2).tolist(),
                    'c_w': [round(float(c[0]), 2), round(float(c[1]), 2)],
                    'in_aerodrome': bool(APW.contains(Point(c))), 'd_aerodrome_m': round(float(d), 1)})
        for key in ('ref', 'name'):
            if key in t: rec[key] = t[key]
        if k == 'taxiway':
            st = [s for s in ('disused', 'abandoned', 'construction', 'proposed') if t.get(s) == 'yes']
            rec['status'] = st[0] if st else ('closed' if t.get('access') == 'no' else 'open')
        if k == 'building': rec['type'] = t.get('building')
        if k == 'service_road':
            if gk == 'line' and geo.length > 0:
                rec['inside_frac'] = round(geo.intersection(APW).length / geo.length, 3)
        if k in NEAR_KINDS and d > NEAR_M:
            outside[k] += 1; continue
        if k in INSIDE_KINDS and d > 0:
            outside[k] += 1; continue
        feats.setdefault(k, []).append(rec)
    for k in feats:
        feats[k].sort(key=lambda r: (str(r.get('ref') or r.get('name') or ''), r['osm']['type'], r['osm']['id']))
    counts = {k: len(v) for k, v in sorted(feats.items())}
    out = {'source': os.path.relpath(src, ROOT), 'source_sha256': meta['sha256'], 'osm_base': raw['osm3s']['timestamp_osm_base'],
           'attic_date': meta.get('attic_date'), 'endpoint': meta['endpoint'], 'fetched_utc': meta.get('fetched_utc'),
           'bbox': meta['bbox'],
           'licence': 'ODbL 1.0 - derived from OpenStreetMap, made available under the Open Database License 1.0 (https://opendatacommons.org/licenses/odbl/1-0/)',
           'attribution': '(c) OpenStreetMap contributors - https://www.openstreetmap.org/copyright',
           'frame': {'id': G.FRAME_ID, 'fn': 'tools/common/hwd_frame.py wgs84_to_world (OSM = WGS 84)',
                     'x': 'east m', 'z': 'south m', 'origin': [G.ARP_LAT, G.ARP_LON],
                     'wgs84_minus_nad83_en_m': [G.WGS84_MINUS_NAD83_E, G.WGS84_MINUS_NAD83_N], 'epoch': G.WGS84_EPOCH},
           'rules': {'near_m': NEAR_M, 'near_kinds': NEAR_KINDS, 'inside_kinds': INSIDE_KINDS,
                     'aerodrome': 'way %d' % AERO_WAY, 'aerodrome_area_m2': round(APW.area, 1)},
           'counts': counts, 'outside_counts': dict(sorted(outside.items())), 'unparsed_elements': dict(unparsed),
           'notes': notes, 'features': dict(sorted(feats.items()))}
    json.dump(out, open(OUT, 'w'), separators=(',', ':'))
    print('wrote', os.path.relpath(OUT, ROOT), os.path.getsize(OUT) // 1024, 'KB; osm_base', out['osm_base'])
    print('counts', json.dumps(counts)); print('outside (dropped)', dict(outside)); print('unparsed', dict(unparsed))
    for n in notes: print('note:', n)


if __name__ == '__main__':
    main()
