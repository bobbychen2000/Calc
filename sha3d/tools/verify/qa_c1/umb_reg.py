import sys, json, numpy as np
sys.path.insert(0, '.')
from qa_img import umbra, s2
A = json.load(open('/home/user/Calc/sha3d/data/sha_airport.json'))
U = umbra((0, 0))
out = {}
for rw in A['runways']:
    n0 = np.array(rw['ends'][0]['osm_end_node']['xz']); n1 = np.array(rw['ends'][1]['osm_end_node']['xz'])
    L = np.linalg.norm(n1 - n0); u = (n1 - n0) / L; v = np.array([-u[1], u[0]])   # v = +x-ish? check sign
    # v = (-uz, ux): u ~ (0.046, 0.999) -> v ~ (-0.999, 0.046): points WEST. use e = -v (east)
    e = -v
    pav = (rw['width_m'] + 2 * rw['shoulder_m'])
    offs = []; offs_s2 = {'S2B': [], 'S2C': []}
    for s in np.arange(300, L - 300, 50):
        c = n0 + s * u
        t = np.arange(-90, 90.1, 0.5)
        # along-track median over +-20 m
        aa = np.arange(-20, 20.1, 2)
        T, AA = np.meshgrid(t, aa, indexing='ij')
        X = c[0] + T * e[0] + AA * u[0]; Z = c[1] + T * e[1] + AA * u[1]
        prof = np.nanmedian(U.sample(X, Z), axis=1)
        grass = np.nanmedian(prof[np.abs(t) > pav / 2 + 15]); pave = np.nanmedian(prof[np.abs(t) < pav / 2 - 10])
        if not (grass > 2.5 * pave): continue
        mid = (grass + pave) / 2
        inside = prof < mid
        # find contiguous dark band containing t ~ 0 (search near centre)
        i0 = np.argmin(np.abs(t))
        if not inside[i0]: continue
        l = i0
        while l > 0 and inside[l - 1]: l -= 1
        r = i0
        while r < len(t) - 1 and inside[r + 1]: r += 1
        # subpixel
        tl = t[l] - 0.5 * (mid - prof[l]) / max(prof[l - 1] - prof[l], 1e-6) if l > 0 else t[l]
        tr = t[r] + 0.5 * (mid - prof[r]) / max(prof[r + 1] - prof[r], 1e-6) if r < len(t) - 1 else t[r]
        w = tr - tl
        if abs(w - pav) > 12: continue
        offs.append(((tl + tr) / 2, w, s))
    o = np.array(offs)
    print(rw['id'], 'n stations', len(o), 'Umbra dark band centre - OSM centreline (m, +east): median %.2f  IQR %.2f..%.2f' % (np.median(o[:, 0]), *np.percentile(o[:, 0], [25, 75])), 'band width median %.1f (expected %.0f)' % (np.median(o[:, 1]), pav))
    out[rw['id']] = o
allo = np.concatenate([out[k][:, 0] for k in out])
print('both runways median east offset %.2f m (n=%d)' % (np.median(allo), len(allo)))
