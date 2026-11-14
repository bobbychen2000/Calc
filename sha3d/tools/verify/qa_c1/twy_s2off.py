import sys, json, numpy as np
sys.path.insert(0, '.')
from qa_img import s2
A = json.load(open('/home/user/Calc/sha3d/data/sha_airport.json'))
offs = json.load(open('twy_offset.json'))
# S2 registration: OSM - S2 (E, N) from A1 checks: feature at OSM p appears in S2 at p - (OSM-S2)
reg = {'S2B': (-3.09, -1.0), 'S2C': (-1.61, -0.14)}
def straight(t, mid, L):
    return None
for r in offs[:12]:
    t = next(x for x in A['taxiways'] if x['id'] == r['id'])
    # rebuild run around mid along the polyline: take the longest straight segment containing mid
    P = np.array(t['pts']); mid = np.array(r['mid'])
    best = None
    for i in range(len(P) - 1):
        a, b = P[i], P[i + 1]; L = np.linalg.norm(b - a); u = (b - a) / L
        d = abs(np.cross(u, mid - a)) if False else abs((mid - a) @ np.array([-u[1], u[0]]))
        if best is None or d < best[0]: best = (d, a, b)
    _, a, b = best
    L = np.linalg.norm(b - a); u = (b - a) / L; n = np.array([-u[1], u[0]])
    tt = np.arange(-45, 45.1, 1.0); ss = np.arange(5, L - 5, 3.0)
    S_, T_ = np.meshgrid(ss, tt, indexing='ij')
    X = a[0] + S_ * u[0] + T_ * n[0]; Z = a[1] + S_ * u[1] + T_ * n[1]
    row = [str(r['ref']), r['id'].split('/')[-1], 'UMB %.2f' % r['off']]
    for sc in ('S2B', 'S2C'):
        dE, dN = -reg[sc][0], -reg[sc][1]   # shift to apply to world coords to sample S2: S2 = OSM - (OSM-S2)
        b4 = s2(sc, 'B04', shift_en=(dE, dN)); b8 = s2(sc, 'B08', shift_en=(dE, dN))
        v4 = b4.sample(X, Z); v8 = b8.sample(X, Z)
        nd = np.nanmedian((v8 - v4) / (v8 + v4), axis=0)
        # symmetric centre: minimise mismatch of nd(c+t) vs nd(c-t)
        cs = np.arange(-15, 15.01, 0.25); cost = []
        from numpy import interp
        for c in cs:
            q = np.arange(3, 35, 1.0)
            cost.append(np.nanmean((interp(c + q, tt, nd) - interp(c - q, tt, nd)) ** 2))
        c0 = cs[int(np.argmin(cost))]
        row.append(f'{sc} {c0:+.2f} (grass L {np.nanmedian(nd[tt<-30]):.2f} R {np.nanmedian(nd[tt>30]):.2f})')
    print(' | '.join(row))
