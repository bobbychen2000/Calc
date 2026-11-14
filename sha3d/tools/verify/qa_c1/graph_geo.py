import sys, json, numpy as np
sys.path.insert(0, '.')
from pave import umb_med, ndvi
from shapely.geometry import LineString, Polygon, Point
from shapely.ops import unary_union
from shapely.prepared import prep
from collections import Counter
T = json.load(open('/home/user/Calc/sha3d/data/sha_taxigraph.json')); A = json.load(open('/home/user/Calc/sha3d/data/sha_airport.json'))
S = json.load(open('/home/user/Calc/sha3d/data/sha_stands.json'))
blds = [Polygon(b['ring']).buffer(0) for b in A['buildings'] if len(b.get('ring') or []) >= 3]
bld = prep(unary_union(blds))
res = Counter(); worst = []
for l in T['links']:
    ls = LineString(l['pts']); n = max(2, int(ls.length / 2) + 1)
    P = np.array([ls.interpolate(t, normalized=True).coords[0] for t in np.linspace(0, 1, n)])
    u = umb_med(P[:, 0], P[:, 1]); nb = ndvi('S2B', P[:, 0], P[:, 1]); nc = ndvi('S2C', P[:, 0], P[:, 1])
    g = (u > 7) & (nb > 0.22) & (nc > 0.13)
    inb = np.array([bld.contains(Point(p)) for p in P])
    gl = g.sum() * ls.length / n; bl = inb.sum() * ls.length / n
    if gl > 10: res[(l['kind'], 'grass>10m')] += 1; worst.append(('grass', l['kind'], l['id'], l.get('ref'), round(gl), l['status']))
    if bl > 2: res[(l['kind'], 'building>2m')] += 1; worst.append(('building', l['kind'], l['id'], l.get('ref'), round(bl), l['status']))
print(dict(res))
for w in sorted(worst, key=lambda w: -w[4])[:25]: print(w)
json.dump(worst, open('graph_geo.json', 'w'))
