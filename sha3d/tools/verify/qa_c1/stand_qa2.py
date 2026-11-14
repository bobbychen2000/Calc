import sys, json, math, numpy as np
sys.path.insert(0, '/home/user/Calc/sha3d/tools/common'); sys.path.insert(0, '/home/user/Calc/sha3d/tools/airport'); sys.path.insert(0, '.')
import frame as F
from acplan import planform, CLS_REF, CLASS_MAX, ORDER
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union
from shapely.strtree import STRtree
from collections import Counter, defaultdict
S = json.load(open('/home/user/Calc/sha3d/data/sha_stands.json'))
A = json.load(open('/home/user/Calc/sha3d/data/sha_airport.json'))
st = S['stands']; by = {s['name']: s for s in st}
def place(polys, nose, hdg):
    f = F.hdg_vec(hdg); r = (-f[1], f[0])
    return unary_union([Polygon([(nose[0] + u * f[0] + v * r[0], nose[1] + u * f[1] + v * r[1]) for u, v in p]) for p in polys])
def pf_ref(cls, s):
    _, L, span, w, sw = CLS_REF[cls]
    if s.get('span_max'): span = min(span, s['span_max'])
    return place(planform(L, span, w, sw), s['nose'], s['hdg'])
def pf_max(cls, s):
    _, L, span, w, sw = CLS_REF[cls]
    smax, lmax = CLASS_MAX[cls]
    if s.get('span_max'): smax = min(smax, s['span_max'])
    if s.get('len_max'): lmax = min(lmax, s['len_max'])
    return place(planform(lmax, smax, w, sw), s['nose'], s['hdg'])
excl = set()
for s in st:
    for e in s['excl']: excl.add(frozenset((s['name'], e)))
alt = defaultdict(set)
for s in st:
    if s.get('alt_group'): alt[str(s['alt_group'])].add(s['name'])
def exempt(a, b):
    if frozenset((a, b)) in excl: return True
    for g in alt.values():
        if a in g and b in g: return True
    return False
for label, fn in (('reference planform (CLS_REF)', pf_ref), ('class-max planform (CLASS_MAX span/length)', pf_max)):
    P = {s['name']: fn(s['cls'], s) for s in st}
    names = list(P); tree = STRtree([P[n] for n in names])
    ov = []; clear = []
    for i, n in enumerate(names):
        for j in tree.query(P[n].buffer(10)):
            m = names[j]
            if m <= n: continue
            d = P[n].distance(P[m]); a = P[n].intersection(P[m]).area
            if exempt(n, m): continue
            if a > 0.01: ov.append((n, m, by[n]['cls'], by[m]['cls'], round(a, 1)))
            elif d < 2.5: clear.append((n, m, by[n]['cls'], by[m]['cls'], round(d, 2)))
    print(f'== {label}: overlapping pairs (not excl/alt): {len(ov)}; pairs closer than 2.5 m: {len(clear)}')
    for o in sorted(ov, key=lambda o: -o[4])[:40]: print('   overlap', o)
    for c in clear: print('   close', c)
    if label.startswith('class-max'):
        json.dump(ov, open('overlaps_max.json', 'w'))
    # buildings
    bl = [Polygon(b['ring']).buffer(0) for b in A['buildings'] if len(b.get('ring') or []) >= 3]
    bu = unary_union(bl)
    bi = [(n, by[n]['cls'], round(P[n].intersection(bu).area, 1), round(P[n].distance(bu), 2)) for n in names if P[n].distance(bu) < 3.0]
    print(f'   planforms within 3 m of / intersecting OSM airport buildings: {len(bi)}', sorted(bi, key=lambda x: -x[2])[:15])
