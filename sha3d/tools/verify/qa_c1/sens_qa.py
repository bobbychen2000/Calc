# Local-only inspection: prints counts; ids are used only in memory for cross-referencing.
import sys, os, json, glob, re, math
sys.path.insert(0, '/home/user/Calc/sha3d/tools/law'); sys.path.insert(0, '/home/user/Calc/sha3d/tools/common')
import osm_sensitive as S, frame as F
import xml.etree.ElementTree as ET
from shapely.geometry import Polygon, Point, LineString, shape
from shapely.ops import unary_union
RAW = '/home/user/Calc/sha3d/refs/cache/osm_pinned_raw/20261114'
nodes = {}; ways = {}; rels = {}; wtags = {}; ntags = {}; rtags = {}
for fn in sorted(glob.glob(RAW + '/*.osm')):
    root = ET.parse(fn).getroot()
    for el in root:
        t = {x.get('k'): x.get('v') for x in el.findall('tag')}
        if el.tag == 'node':
            nodes[el.get('id')] = (float(el.get('lat')), float(el.get('lon'))); 
            if t: ntags[el.get('id')] = t
        elif el.tag == 'way':
            ways[el.get('id')] = [n.get('ref') for n in el.findall('nd')]; wtags[el.get('id')] = t
        elif el.tag == 'relation':
            rels[el.get('id')] = [(m.get('type'), m.get('ref'), m.get('role')) for m in el.findall('member')]; rtags[el.get('id')] = t
drop = {}
for i, t in ntags.items():
    r = S.sensitive_reason(t)
    if r: drop[('node', i)] = r
for i, t in wtags.items():
    r = S.sensitive_reason(t)
    if r: drop[('way', i)] = r
for i, t in rtags.items():
    r = S.sensitive_reason(t)
    if r: drop[('relation', i)] = r
from collections import Counter
print('raw sensitive by (type,class):', Counter((k[0], v) for k, v in drop.items()))
ext = shape(json.load(open('/home/user/Calc/sha3d/refs/cache/osm_pinned/extent_hull1km.geojson'))['features'][0]['geometry'])
# geometry of dropped ways (world xz)
def wgeom(wid):
    pts = [nodes[n] for n in ways[wid] if n in nodes]
    xz = [F.ll_to_world(a, b) for a, b in pts]
    if len(xz) >= 4 and ways[wid][0] == ways[wid][-1]:
        return Polygon(xz)
    return LineString(xz) if len(xz) > 1 else None
dpolys = []
inext = Counter()
for (typ, i), r in drop.items():
    if typ == 'way':
        g = wgeom(i)
        if g is None: continue
        c = g.centroid; la, lo = F.world_to_ll(c.x, c.y)
        inside = ext.contains(Point(lo, la))
        inext[(typ, r, inside)] += 1
        if isinstance(g, Polygon) and inside: dpolys.append((r, g.buffer(0)))
    elif typ == 'node':
        la, lo = nodes[i]
        inext[(typ, r, ext.contains(Point(lo, la)), drop and ntags[i].get('man_made') == 'surveillance')] += 1
    else:
        inext[(typ, r, 'rel')] += 1
print('dropped by inside-extent:', inext)
print('dropped area polygons inside extent:', len(dpolys), 'areas m2:', sorted(round(p.area) for _, p in dpolys))
DROPPED_IDS = {(t, int(i)) for (t, i) in drop}
# (no dropped ids are ever written to disk)
# nodes used only by dropped ways
used_by = {}
for w, nds in ways.items():
    for n in nds: used_by.setdefault(n, set()).add(w)
only_dropped_nodes = {n for n, ws in used_by.items() if all(('way', w) in drop for w in ws) and n not in ntags}
print('untagged nodes used only by dropped ways:', len(only_dropped_nodes))
# pinned outputs
el = json.load(open('/home/user/Calc/sha3d/refs/cache/osm_pinned/osm_elements.json'))
print('osm_elements keys', list(el.keys())[:10])
def ids_of(el, k):
    v = el.get(k)
    if isinstance(v, dict): return {int(x) for x in v}
    if isinstance(v, list): return {int(x[0]) if isinstance(x, list) else int(x) for x in v}
    return set()
for k in ('node', 'nodes', 'way', 'ways', 'relation', 'relations'):
    if k in el:
        ids = ids_of(el, k); typ = k.rstrip('s')
        hit = {(typ, i) for i in ids} & DROPPED_IDS
        print('osm_elements', k, len(ids), 'dropped ids present:', len(hit))
        if typ == 'node':
            print('  nodes used only by dropped ways present in osm_elements:', len({int(n) for n in only_dropped_nodes} & ids))
gj = json.load(open('/home/user/Calc/sha3d/refs/cache/osm_pinned/zsss_osm_pinned.geojson'))
bad = Counter(); refhit = 0; inside_drop = Counter()
for f in gj['features']:
    p = f['properties']
    tags = {k: v for k, v in p.items() if not k.startswith('@')}
    r = S.sensitive_reason(tags)
    if r: bad[r] += 1
    if (p.get('@type'), int(p.get('@id'))) in DROPPED_IDS: refhit += 1
    for m in p.get('@members', []) or []:
        if isinstance(m, dict) and (m.get('type'), int(m.get('ref', -1))) in DROPPED_IDS: refhit += 1
    if f.get('geometry') and dpolys:
        g = shape(f['geometry'])
        c = g.representative_point(); x, z = F.ll_to_world(c.y, c.x)
        for cls, dp in dpolys:
            if dp.contains(Point(x, z)):
                key = [k for k in ('building', 'highway', 'landuse', 'amenity', 'barrier', 'man_made', 'leisure', 'natural', 'power') if k in tags]
                inside_drop[(cls, key[0] if key else 'other')] += 1
print('pinned geojson: sensitive by rule', dict(bad), '; dropped ids referenced', refhit)
print('pinned features with a representative point INSIDE a dropped area:', dict(inside_drop))
# keys in pinned props list
print('sample prop keys', list(gj['features'][0]['properties'].keys())[:12])
