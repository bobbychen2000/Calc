import sys, json, numpy as np
sys.path.insert(0, '.')
from qa_img import s2, umbra
from scipy.optimize import least_squares
from scipy.special import erf
A = json.load(open('/home/user/Calc/sha3d/data/sha_airport.json'))
U = umbra()
def fit_step(s, y, s0):
    ok = np.isfinite(y); s = s[ok]; y = y[ok]
    f = lambda p: p[0] + p[1] * 0.5 * (1 + erf((s - p[2]) / (np.sqrt(2) * abs(p[3]) + 1e-6))) - y
    r = least_squares(f, [y[:5].mean(), y[-5:].mean() - y[:5].mean(), s0, 5.0])
    return r.x[2], abs(r.x[3]), r.x[1]
windows = {  # (runway, label, s_lo, s_hi, s_guess, band)
 ('18L/36R', '18L paved edge (grass->pavement)', -170, -40, -105),
 ('18L/36R', '18L blast pad -> CONC', -60, 40, -10),
 ('18L/36R', '18L CONC -> ASPH', 40, 160, 95),
 ('18L/36R', '36R ASPH -> CONC', 3190, 3330, 3260),
 ('18L/36R', '36R CONC -> blast pad', 3340, 3430, 3390),
 ('18L/36R', '36R paved edge', 3400, 3520, 3450),
 ('18R/36L', '18R paved edge', -200, -60, -128),
 ('18R/36L', '18R blast pad -> runway', -60, 40, -10),
 ('18R/36L', '36L runway -> blast pad', 3240, 3340, 3290),
 ('18R/36L', '36L paved edge', 3360, 3470, 3412),
}
for rw in A['runways']:
    n0 = np.array(rw['ends'][0]['osm_end_node']['xz']); n1 = np.array(rw['ends'][1]['osm_end_node']['xz'])
    L = np.linalg.norm(n1 - n0); u = (n1 - n0) / L; v = np.array([-u[1], u[0]])
    half = rw['width_m'] / 2
    for (rid, lab, lo, hi, g) in sorted(windows):
        if rid != rw['id']: continue
        s = np.arange(lo, hi, 1.0); acr = np.arange(-half + 5, half - 5 + 0.1, 2.5)
        S_, A_ = np.meshgrid(s, acr, indexing='ij')
        X = n0[0] + S_ * u[0] + A_ * v[0]; Z = n0[1] + S_ * u[1] + A_ * v[1]
        row = [rid, lab]
        for sc in ('S2B', 'S2C'):
            for b in ('B04', 'B08') if 'paved' in lab else ('B02', 'B04'):
                y = np.nanmedian(s2(sc, b).sample(X, Z), axis=1)
                s0, w, amp = fit_step(s, y, g)
                row.append(f'{sc}.{b} {s0:7.1f}')
        y = np.nanmedian(U.sample(X + 3.4, Z), axis=1); s0, w, amp = fit_step(s, y, g)
        row.append(f'UMB {s0:7.1f} (amp {amp:+.0f})')
        print(' | '.join(row))
