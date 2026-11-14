import sys, json, numpy as np
sys.path.insert(0, '.')
from pave import umb_med, ndvi
from shapely.geometry import LineString, Polygon, Point
from shapely.ops import unary_union
from shapely.prepared import prep
A = json.load(open('/home/user/Calc/sha3d/data/sha_airport.json'))
bld = unary_union([Polygon(b['ring']).buffer(0) for b in A['buildings'] if len(b.get('ring') or []) >= 3] +
                  [Polygon(b['ring']).buffer(0) for b in A['context']['buildings'] if len(b.get('ring') or []) >= 3])
bldp = prep(bld)
def densify(pts, step=2.0):
    ls = LineString(pts); n = max(2, int(ls.length / step) + 1)
    d = np.linspace(0, ls.length, n); P = np.array([ls.interpolate(x).coords[0] for x in d]); return P, d
def runs(mask, d):
    out = []; i = 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j + 1 < len(mask) and mask[j + 1]: j += 1
            out.append((d[i], d[j])); i = j + 1
        else: i += 1
    return out
rows = []
for kind in ('taxiways', 'taxilanes'):
    for t in A[kind]:
        P, d = densify(t['pts'])
        u = umb_med(P[:, 0], P[:, 1]); nb = ndvi('S2B', P[:, 0], P[:, 1]); nc = ndvi('S2C', P[:, 0], P[:, 1])
        grass3 = (u > 7) & (nb > 0.22) & (nc > 0.13)
        grass_s2 = (nb > 0.22) & (nc > 0.13)
        inb = np.array([bldp.contains(Point(p)) for p in P])
        r3 = [b - a + 2 for a, b in runs(grass3, d)]; rs2 = [b - a + 2 for a, b in runs(grass_s2, d)]; rb = [b - a + 2 for a, b in runs(inb, d)]
        rows.append(dict(kind=kind, id=t['id'], ref=t.get('ref'), status=t.get('construction') or t.get('status'), len=float(d[-1]),
                         grass3_max=max(r3) if r3 else 0, grass3_tot=sum(r3), s2_max=max(rs2) if rs2 else 0, bld_max=max(rb) if rb else 0,
                         umb_dark_frac=float(np.nanmean(u < 7))))
json.dump(rows, open('twy_pave.json', 'w'))
print('ways', len(rows))
for key, thr in (('grass3_max', 20), ('s2_max', 30), ('bld_max', 4)):
    bad = sorted([r for r in rows if r[key] >= thr], key=lambda r: -r[key])
    print(f'--- {key} >= {thr} m: {len(bad)} ways')
    for r in bad[:25]:
        print(f"{r['kind'][:7]} {r['id']:22s} ref={str(r['ref']):6s} status={str(r['status'])[:14]:14s} len={r['len']:6.0f} grass3_max={r['grass3_max']:5.0f} s2_max={r['s2_max']:5.0f} bld_max={r['bld_max']:4.0f} umb_dark={r['umb_dark_frac']:.2f}")
print('sample taxiway keys', list(A['taxiways'][0].keys()))
