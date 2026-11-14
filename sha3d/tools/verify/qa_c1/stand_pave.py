import sys, json, math, numpy as np
sys.path.insert(0, '/home/user/Calc/sha3d/tools/common'); sys.path.insert(0, '/home/user/Calc/sha3d/tools/airport'); sys.path.insert(0, '.')
import frame as F
from acplan import planform, CLS_REF, CLASS_MAX
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from shapely import vectorized
from pave import ndvi
S = json.load(open('/home/user/Calc/sha3d/data/sha_stands.json')); A = json.load(open('/home/user/Calc/sha3d/data/sha_airport.json'))
st = S['stands']
def place(polys, nose, hdg):
    f = F.hdg_vec(hdg); r = (-f[1], f[0])
    return unary_union([Polygon([(nose[0] + u * f[0] + v * r[0], nose[1] + u * f[1] + v * r[1]) for u, v in p]) for p in polys])
aprons = unary_union([Polygon(a['ring']).buffer(0) for a in A['aprons']])
tw = unary_union([Polygon(p['ring'], p.get('holes') or []).buffer(0) for p in A['surfaces']['taxiway']])
rw = unary_union([Polygon(p['ring']).buffer(0) for p in A['surfaces']['runway']])
paved_noleadin = unary_union([aprons, tw, rw])
rows = []
for s in st:
    _, L, span, w, sw = CLS_REF[s['cls']]
    if s.get('span_max'): span = min(span, s['span_max'])
    P = place(planform(L, span, w, sw), s['nose'], s['hdg'])
    x0, z0, x1, z1 = P.bounds
    X, Z = np.meshgrid(np.arange(x0, x1, 1.0), np.arange(z0, z1, 1.0))
    m = vectorized.contains(P, X, Z)
    xs, zs = X[m], Z[m]
    nb = ndvi('S2B', xs, zs); nc = ndvi('S2C', xs, zs)
    veg = (nb > 0.22) & (nc > 0.13)
    out_osm = 1 - P.intersection(paved_noleadin).area / P.area
    rows.append((s['name'], s['cls'], s['area'], round(float(veg.mean()), 3), round(out_osm, 3), round(s['pavement_outside_frac'], 3)))
rows.sort(key=lambda r: -r[3])
print('stands with >5% of the reference planform on vegetation in BOTH S2 scenes:', sum(1 for r in rows if r[3] > 0.05))
for r in rows[:15]: print('  ', r)
r2 = sorted(rows, key=lambda r: -r[4])
print('stands with >5% of planform outside OSM aprons + taxiway/runway surfaces (no lead-in buffer):', sum(1 for r in rows if r[4] > 0.05))
for r in r2[:20]: print('  ', r)
json.dump(rows, open('stand_pave.json', 'w'))
