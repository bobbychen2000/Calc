import sys, json, numpy as np
sys.path.insert(0, '.')
from qa_img import umbra
A = json.load(open('/home/user/Calc/sha3d/data/sha_airport.json'))
OSMGJ = None
U = umbra((3.0, 0.0))
def straight_runs(pts, tol=1.0, minlen=80):
    pts = np.array(pts); out = []; i = 0
    while i < len(pts) - 1:
        j = i + 1; best = None
        while j < len(pts):
            a, b = pts[i], pts[j]; L = np.linalg.norm(b - a)
            if L < 1e-6: j += 1; continue
            u = (b - a) / L; n = np.array([-u[1], u[0]])
            dev = np.abs((pts[i:j + 1] - a) @ n).max()
            if dev > tol: break
            best = j; j += 1
        if best is not None and np.linalg.norm(pts[best] - pts[i]) >= minlen:
            out.append((i, best, pts[i], pts[best])); i = best
        else: i += 1
    return out
res = []
for kind in ('taxiways',):
    for t in A[kind]:
        for (i, j, a, b) in straight_runs(t['pts']):
            L = np.linalg.norm(b - a); u = (b - a) / L; n = np.array([-u[1], u[0]])
            tt = np.arange(-45, 45.1, 0.5); ss = np.arange(10, L - 10, 3.0)
            if len(ss) < 5: continue
            S_, T_ = np.meshgrid(ss, tt, indexing='ij')
            X = a[0] + S_ * u[0] + T_ * n[0]; Z = a[1] + S_ * u[1] + T_ * n[1]
            prof = np.nanmedian(U.sample(X, Z), axis=0)
            if not np.isfinite(prof).all(): continue
            pave = np.nanmedian(prof[np.abs(tt) < 5]); gl = np.nanmedian(prof[(tt < -25) & (tt > -40)]); gr = np.nanmedian(prof[(tt > 25) & (tt < 40)])
            if not (gl > 3 * pave and gr > 3 * pave): continue
            mid_l = (gl + pave) / 2; mid_r = (gr + pave) / 2
            i0 = np.argmin(np.abs(tt)); l = i0
            while l > 0 and prof[l - 1] < mid_l: l -= 1
            r = i0
            while r < len(tt) - 1 and prof[r + 1] < mid_r: r += 1
            w = tt[r] - tt[l]
            if w < 15 or w > 70: continue
            c = (tt[l] + tt[r]) / 2
            # convert normal offset to east/north
            res.append(dict(id=t['id'], ref=t.get('ref'), refit=bool(t.get('refit')), L=round(L), off=round(c, 2), width=round(w, 1),
                            n_east=round(n[0], 2), n_north=round(-n[1], 2), mid=[round(float(x), 1) for x in (a + b) / 2]))
res.sort(key=lambda r: -abs(r['off']))
print('runs measured (grass both sides in Umbra):', len(res))
offs = np.array([r['off'] for r in res])
print('|offset| median %.2f p90 %.2f max %.2f; n >= 3.5 m: %d' % (np.median(np.abs(offs)), np.percentile(np.abs(offs), 90), np.abs(offs).max(), (np.abs(offs) >= 3.5).sum()))
for r in res[:20]: print(r)
json.dump(res, open('twy_offset.json', 'w'))
# compare with A1 meas
M = json.load(open('/home/user/Calc/sha3d/data/meas/twy_refit.json'))
print('A1 twy_refit keys', list(M.keys())[:10])
