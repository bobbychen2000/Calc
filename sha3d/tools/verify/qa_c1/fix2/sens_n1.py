"""Fix round 2 check for re-verify N1 (dropped lines traceable in the pinned extract). Counts only: never prints ids,
names or positions of dropped elements.
usage: python3 -I sens_n1.py SHA3D_DIR
Reads the raw tiles (local only), applies the tag rule (tools/law/osm_sensitive.py) and checks the committable pinned
extract (refs/cache/osm_pinned/) and data/sha_airport.json context.rail against the dropped lines, areas and points:
 1. railway=* point features within 30 m of any dropped feature, and other tagged points within 2 m of a dropped line;
 2. non-passenger railway ways within 100 m of a dropped line / area; kept railway ways sharing a node with a dropped
    railway way;
 3. kept features with >= 25 m of line / outline within 10 m of a dropped line AND within 30 deg of its direction
    (by class; exempt classes are reported separately);
 4. kept roads sharing vertex nodes with a dropped line: nodes per road, and the longest stretch of a road whose
    consecutive vertices are all within 2 m of the line (a road running ON it); since fix round 3 only the vertices
    that the committed geometry still holds count (pin_extract.py rule g removes crossing vertices);
 5. osm_elements.json: listed nodes that belong to no kept feature, and listed nodes that belong only to dropped ones;
 6. sha_airport.json context.rail polylines within 10 m of a dropped line (length).
"""
import glob, json, math, os, sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
ROOT = sys.argv[1]
sys.path.insert(0, os.path.join(ROOT, 'tools/law')); sys.path.insert(0, os.path.join(ROOT, 'tools/common'))
import osm_sensitive as S
import frame as F
import shapely
from shapely.geometry import shape, Polygon, LineString, Point, MultiPoint
from shapely.ops import unary_union

nodes, ntags, ways, wtags = {}, {}, {}, {}
for fn in sorted(glob.glob(os.path.join(ROOT, 'refs/cache/osm_pinned_raw/20261114/*.osm'))):
    for el in ET.parse(fn).getroot():
        t = {x.get('k'): x.get('v') for x in el.findall('tag')}
        if el.tag == 'node':
            nodes[int(el.get('id'))] = F.ll_to_world(float(el.get('lat')), float(el.get('lon'))); ntags[int(el.get('id'))] = t
        elif el.tag == 'way':
            ways[int(el.get('id'))] = [int(n.get('ref')) for n in el.findall('nd')]; wtags[int(el.get('id'))] = t
dnode = {i for i, t in ntags.items() if S.sensitive_reason(t)}
dway = {i for i, t in wtags.items() if S.sensitive_reason(t)}
lines, areas = [], []
for w in dway:
    L = [nodes[n] for n in ways[w] if n in nodes]
    (areas if ways[w][0] == ways[w][-1] and len(L) >= 4 else lines).append(Polygon(L) if ways[w][0] == ways[w][-1] and len(L) >= 4 else LineString(L))
pts = [Point(nodes[i]) for i in dnode if i in nodes]
LU = unary_union(lines); AU = unary_union(areas); ALL = unary_union(lines + areas + pts)
print('dropped by the tag rule: %d lines, %d areas, %d points' % (len(lines), len(areas), len(pts)))
G = json.load(open(os.path.join(ROOT, 'refs/cache/osm_pinned/zsss_osm_pinned.geojson')))
to_xz = lambda g: shapely.transform(g, lambda c: [F.ll_to_world(la, lo) for lo, la in c])
kept = [(f['properties'], to_xz(shape(f['geometry']))) for f in G['features'] if f.get('geometry')]
def cls(t):
    for k in ('highway', 'railway', 'waterway', 'aeroway', 'boundary', 'landuse', 'building', 'barrier', 'man_made', 'leisure', 'amenity', 'natural'):
        if k in t: return k + '=' + t[k]
    return 'other'
def passenger(t):
    r = t.get('railway')
    if r in ('platform', 'station', 'halt', 'stop', 'subway_entrance', 'platform_edge'): return True
    if r == 'construction': r = t.get('construction') or ('rail' if t.get('usage') in ('main', 'branch') else None)
    return r in ('rail', 'subway', 'light_rail', 'tram', 'monorail') and 'service' not in t and t.get('usage') not in ('industrial', 'military', 'freight', 'test', 'tourism')
# 1
c1 = Counter()
for p, g in kept:
    t = p['tags']
    if g.geom_type != 'Point': continue
    if 'railway' in t and g.distance(ALL) < 30: c1['railway point < 30 m of a dropped feature'] += 1
    if g.distance(LU) < 2: c1['tagged point < 2 m of a dropped line'] += 1
print('1. points:', dict(c1) or 0)
# 2
c2 = Counter()
kept_way_ids = {p['@id'] for p, g in kept if p['@type'] == 'way'}
drop_rail_nodes = set(n for w in dway if 'railway' in wtags[w] for n in ways[w])
for p, g in kept:
    t = p['tags']
    if p['@type'] != 'way' or 'railway' not in t or g.geom_type == 'Point': continue
    if not passenger(t) and g.distance(unary_union([LU, AU])) < 100: c2['non-passenger railway < 100 m'] += 1
    if drop_rail_nodes & set(ways.get(p['@id'], [])): c2['railway way sharing a node with a dropped railway'] += 1
print('2. railway ways:', dict(c2) or 0)
# 3
band = LU.buffer(10)
def parallel_len(line, step=1.0):
    near = line.intersection(band)
    tot = 0.0
    for q in getattr(near, 'geoms', [near]):
        if q.geom_type != 'LineString' or q.length == 0: continue
        n = max(1, int(math.ceil(q.length / step)))
        for k in range(n):
            a, b = q.length * k / n, q.length * (k + 1) / n
            pa, pb, m = q.interpolate(a), q.interpolate(b), q.interpolate((a + b) / 2)
            dl = min(lines, key=lambda g: g.distance(m)); s = dl.project(m)
            q1, q2 = dl.interpolate(max(0, s - 1)), dl.interpolate(min(dl.length, s + 1))
            d = math.degrees(math.atan2(pb.y - pa.y, pb.x - pa.x) - math.atan2(q2.y - q1.y, q2.x - q1.x))
            if abs((d + 90) % 180 - 90) <= 30: tot += b - a
    return tot
c3 = Counter(); worst = Counter()
for p, g in kept:
    if g.geom_type == 'Point' or not band.intersects(g): continue
    line = g.boundary if g.geom_type in ('Polygon', 'MultiPolygon') else g
    L = parallel_len(line)
    k = 'aerodrome boundary (exempt)' if p['tags'].get('aeroway') == 'aerodrome' else cls(p['tags'])
    worst[k] = max(worst[k], round(L))
    if L >= 25: c3[k] += 1
print('3. kept features >= 25 m parallel within 10 m of a dropped line:', dict(c3) or 0, '| longest parallel length per class (m):', dict(worst))
# 4
def gcoords(g):
    out = []
    for part in getattr(g, 'geoms', [g]):
        if part.geom_type == 'Polygon':
            out += list(part.exterior.coords) + [c for r in part.interiors for c in r.coords]
        else:
            out += list(part.coords)
    return out
dl_nodes = set(n for w in dway if not (ways[w][0] == ways[w][-1]) for n in ways[w])
per_road = []; run_max = 0.0
for p, g in kept:
    if p['@type'] != 'way' or 'highway' not in p['tags']: continue
    nd = ways.get(p['@id'], [])
    if any(n in dl_nodes for n in nd):
        # fix round 3 (rule g of pin_extract.py): count only the vertices the committed geometry still holds
        vx = MultiPoint(gcoords(g))
        nd = [n for n in nd if n in nodes and vx.distance(Point(nodes[n])) <= 0.05]
    sh = [n for n in nd if n in dl_nodes]
    if not sh: continue
    per_road.append(len(set(sh)))
    run = 0.0
    for a, b in zip(nd[:-1], nd[1:]):
        if a in nodes and b in nodes and LU.distance(Point(nodes[a])) < 2 and LU.distance(Point(nodes[b])) < 2:
            run += math.dist(nodes[a], nodes[b]); run_max = max(run_max, run)
        else:
            run = 0.0
print('4. kept roads sharing a vertex with a dropped line: %d; shared vertices per road: %s; longest road stretch ON a line: %.1f m'
      % (len(per_road), dict(Counter(per_road)), run_max))
# 5
E = json.load(open(os.path.join(ROOT, 'refs/cache/osm_pinned/osm_elements.json')))
listed = {i for i, v in E['node']}
owned = {p['@id'] for p, g in kept if p['@type'] == 'node'}
for w, v in E['way']:
    owned.update(ways.get(w, []))
dropped_only = set(n for w in dway for n in ways[w]) | dnode
print('5. osm_elements.json: listed nodes %d; without a kept owner: %d; belonging only to dropped features: %d; dropped ids listed: %d'
      % (len(listed), len(listed - owned), len((listed & dropped_only) - owned), len(listed & dnode) + len({i for i, v in E['way']} & dway)))
# 6
A = json.load(open(os.path.join(ROOT, 'data/sha_airport.json')))
L6 = 0.0; n6 = 0
for r in A['context']['rail']:
    l = sum(LineString([(q[0], q[1]) for q in pl]).intersection(band).length for pl in r['lines'] if len(pl) >= 2)
    if l >= 10: n6 += 1; L6 += l
print('6. sha_airport.json context.rail: %d records, %d with >= 10 m within 10 m of a dropped line (%.0f m)' % (len(A['context']['rail']), n6, L6))
