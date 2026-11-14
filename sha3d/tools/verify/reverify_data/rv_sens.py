"""Re-verify (data) H1: sensitive features vs the pinned extract. Counts only: never prints ids, names or positions.
usage: python3 -I rv_sens.py SHA3D_DIR
1. dropped elements from the raw tiles with tools/law/osm_sensitive.py (the tag rule), nodes, ways AND relations;
2. no dropped id (node / way / relation) and no vertex node of a dropped way in osm_elements.json, except nodes that
   a kept public road shares (counted);
3. every kept feature of zsss_osm_pinned.geojson, in world metres: length within 5 m and 10 m of each dropped
   outline (areas) or line (military railways), share inside dropped areas, and distance to dropped points;
4. kept vertices that coincide (< 0.5 m) with a dropped node.
"""
import sys, os, glob, json
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
ROOT = sys.argv[1]
sys.path.insert(0, os.path.join(ROOT, 'tools/law')); sys.path.insert(0, os.path.join(ROOT, 'tools/common'))
import osm_sensitive as S
import frame as F
import shapely
from shapely.geometry import shape, Polygon, LineString, Point, MultiPoint
from shapely.ops import unary_union, polygonize, linemerge
from shapely.strtree import STRtree

RAW = os.path.join(ROOT, 'refs/cache/osm_pinned_raw/20261114')
nodes = {}; ntags = {}; ways = {}; wtags = {}; rels = {}; rtags = {}
for fn in sorted(glob.glob(RAW + '/*.osm')):
    for el in ET.parse(fn).getroot():
        t = {x.get('k'): x.get('v') for x in el.findall('tag')}
        i = el.get('id')
        if el.tag == 'node':
            nodes[i] = (float(el.get('lat')), float(el.get('lon'))); ntags[i] = t
        elif el.tag == 'way':
            ways[i] = [n.get('ref') for n in el.findall('nd')]; wtags[i] = t
        elif el.tag == 'relation':
            rels[i] = [(m.get('type'), m.get('ref'), m.get('role')) for m in el.findall('member')]; rtags[i] = t
xz = lambda la, lo: F.ll_to_world(la, lo)
def wline(w):
    return [xz(*nodes[n]) for n in ways[w] if n in nodes]
drop = {'node': {}, 'way': {}, 'relation': {}}
for typ, T in (('node', ntags), ('way', wtags), ('relation', rtags)):
    for i, t in T.items():
        r = S.sensitive_reason(t)
        if r:
            drop[typ][i] = r
print('dropped by tag rule (raw tiles): ', {k: dict(Counter(v.values())) for k, v in drop.items()})
# geometries in world metres
areas = []; lines = []; pts = []
for w, r in drop['way'].items():
    nd = ways[w]; L = wline(w)
    if nd[0] == nd[-1] and len(L) >= 4:
        areas.append((r, Polygon(L)))
    elif len(L) >= 2:
        lines.append((r, LineString(L)))
for i, r in drop['node'].items():
    pts.append((r, Point(xz(*nodes[i]))))
for i, r in drop['relation'].items():
    segs = [LineString(wline(ref)) for t, ref, role in rels[i] if t == 'way' and ref in ways and len(wline(ref)) >= 2]
    polys = list(polygonize(unary_union(segs))) if segs else []
    if polys:
        areas.append((r, unary_union(polys)))
    elif segs:
        lines.append((r, unary_union(segs)))
print('dropped geometries: areas %d (%s), lines %d (%s), points %d' % (len(areas), dict(Counter(r for r, _ in areas)),
      len(lines), dict(Counter(r for r, _ in lines)), len(pts)))
# 2. ids in osm_elements.json
E = json.load(open(os.path.join(ROOT, 'refs/cache/osm_pinned/osm_elements.json')))
kn = {str(i) for i, v in E['node']}; kw = {str(i) for i, v in E['way']}; kr = {str(i) for i, v in E['relation']}
print('dropped ids listed in osm_elements.json: node %d, way %d, relation %d' % (len(kn & set(drop['node'])),
      len(kw & set(drop['way'])), len(kr & set(drop['relation']))))
dnodes = defaultdict(set)
for w, r in drop['way'].items():
    for n in ways[w]:
        dnodes[r].add(n)
for r, ns in dnodes.items():
    listed = ns & kn
    sharers = Counter()
    for n in listed:
        for w in kw:
            if w in ways and n in ways[w]:
                t = wtags.get(w, {})
                sharers[next((k + '=' + t[k] for k in ('highway', 'railway', 'waterway', 'aeroway', 'boundary', 'landuse',
                                                      'building', 'barrier') if k in t), 'untagged/other')] += 1
    print('  vertex nodes of dropped %s ways: %d, listed as kept: %d; kept ways sharing them by class: %s'
          % (r, len(ns), len(listed), dict(sharers)))
# 3. kept features vs dropped geometries
G = json.load(open(os.path.join(ROOT, 'refs/cache/osm_pinned/zsss_osm_pinned.geojson')))
def to_xz(g):
    return shapely.transform(g, lambda c: [xz(la, lo) for lo, la in c])
kept = []
for f in G['features']:
    if not f.get('geometry'):
        continue
    t = f['properties'].get('tags', {})
    kept.append((t, to_xz(shape(f['geometry']))))
def cls(t):
    for k in ('highway', 'railway', 'waterway', 'aeroway', 'boundary', 'landuse', 'building', 'barrier', 'man_made', 'leisure',
              'amenity', 'natural', 'power'):
        if k in t:
            return k + ('=' + t[k] if k in ('highway', 'railway', 'boundary', 'landuse', 'aeroway') else '')
    return 'other'
tree = STRtree([g for _, g in kept])
res = Counter(); detail = Counter()
for kind, items in (('area', areas), ('line', lines)):
    for r, g in items:
        ref = g.boundary if kind == 'area' else g
        b5, b10 = ref.buffer(5), ref.buffer(10)
        for j in tree.query(g.buffer(30)):
            t, kg = kept[j]
            line = kg.boundary if kg.geom_type in ('Polygon', 'MultiPolygon') else kg
            if line.geom_type in ('Point', 'MultiPoint'):
                d = line.distance(ref)
                if d < 10 or (kind == 'area' and g.contains(line)):
                    detail[(r, kind, 'point', cls(t), 'within area' if kind == 'area' and g.contains(line) else '<10 m')] += 1
                continue
            l5 = line.intersection(b5).length; l10 = line.intersection(b10).length
            ins = kg.intersection(g).area / kg.area if (kind == 'area' and kg.area > 0) else (
                line.intersection(g).length / line.length if kind == 'area' and line.length > 0 else 0)
            if l5 >= 10 or l10 >= 25 or ins > 0.5:
                detail[(r, kind, cls(t), 'len<=5m %.0f' % l5, 'len<=10m %.0f' % l10, 'inside %.0f%%' % (100 * ins),
                        'feature len %.0f' % line.length)] += 1
print('kept features near dropped geometries (>= 10 m within 5 m, or >= 25 m within 10 m, or > 50 % inside):')
for k, v in sorted(detail.items(), key=str):
    print('  ', v, '|', ' | '.join(str(x) for x in k))
# points: kept vertices / nodes within 2 m of a dropped node
pt_hits = Counter()
for r, p in pts:
    for j in tree.query(p.buffer(2)):
        t, kg = kept[j]
        if kg.distance(p) < 0.5:
            pt_hits[(r, cls(t))] += 1
print('kept features within 0.5 m of a dropped point:', dict(pt_hits))
# vertices of kept features coinciding with dropped nodes (node ids)
dn = set(drop['node'])
print('dropped nodes used as a vertex of a kept way:', sum(1 for w in kw if w in ways and dn & set(ways[w])))
