"""Independent check of the painted-line data against NAIP 2024 (review round 4, 26 Sep 2026).

A second detector, deliberately different from the generators' (tools/imagery/paintline.py Yellow.cross_peak, which the
generators snap to): CIE Lab b* (yellowness) of NAIP resampled on a profile across the line (+-3.5 m, 0.1 m step,
averaged over 2 m along), the b* peak above the profile median by >= `min_c` (b* units), sub-sample parabola refinement.
Measured every 2 m along each line of data/sfo_details.json:
  centerlines  (drawn ones and those flagged not drawn, separately)
  edges        (the double edge line: one merged b* ridge at NAIP's 0.6 m resolution)
Reports per line the median |offset|, the samples with paint, and the longest run of consecutive samples (2 m apart)
more than 1.5 m off; lists every line with a run >= 6 m. No NAIP pixels are written (numbers only).
Usage: python3 tools/xcheck/paint_lines_check.py [--json OUT]
"""
import json, math, os, sys
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'stands'))
from common import Naip  # noqa: E402

N = Naip()


def bstar_profile(p, t, half=3.5, step=0.1, avg=2.0):
    n = np.array([-t[1], t[0]]); v = np.arange(-half, half + 1e-9, step); u = np.linspace(-avg / 2, avg / 2, 5)
    X = p[0] + np.outer(u, np.ones_like(v)) * t[0] + np.outer(np.ones_like(u), v) * n[0]
    Z = p[1] + np.outer(u, np.ones_like(v)) * t[1] + np.outer(np.ones_like(u), v) * n[1]
    c, r = N.px(X, Z); c0, r0 = int(np.floor(c.min())) - 2, int(np.floor(r.min())) - 2
    win = np.ascontiguousarray(N.im[max(0, r0):int(np.ceil(r.max())) + 3, max(0, c0):int(np.ceil(c.max())) + 3])
    lab = cv2.cvtColor(win, cv2.COLOR_BGR2LAB).astype(np.float32)
    b = cv2.remap(lab[..., 2], (c - max(0, c0)).astype(np.float32), (r - max(0, r0)).astype(np.float32), cv2.INTER_LINEAR)
    return v, b.mean(axis=0)


def offset(p, t, min_c=6.0):
    v, b = bstar_profile(p, t)
    k = int(np.argmax(b)); c = b[k] - np.median(b)
    if c < min_c or k in (0, len(b) - 1): return None
    d = b[k - 1] - 2 * b[k] + b[k + 1]; sub = 0.5 * (b[k - 1] - b[k + 1]) / d if d < 0 else 0.0
    return float(v[k] + sub * (v[1] - v[0]))


def check_line(pl, step=2.0):
    P = np.asarray(pl, float); seg = np.hypot(*np.diff(P, axis=0).T); S = np.r_[0, np.cumsum(seg)]
    if S[-1] < 4: return None
    ss = np.arange(1.0, S[-1] - 0.5, step); offs = []
    for s_ in ss:
        i = min(np.searchsorted(S, s_, 'right') - 1, len(P) - 2); f = (s_ - S[i]) / max(seg[i], 1e-9)
        p = P[i] + (P[i + 1] - P[i]) * f; t = (P[i + 1] - P[i]) / max(seg[i], 1e-9)
        offs.append(offset(p, t))
    good = [o for o in offs if o is not None]
    run = best = 0; where = None; cur0 = None
    for s_, o in zip(ss, offs):
        if o is not None and abs(o) > 1.5:
            if run == 0: cur0 = s_
            run += 1
            if run > best: best = run; where = cur0
        elif o is not None: run = 0
    return {'len': round(float(S[-1]), 1), 'n': len(ss), 'paint': len(good), 'med': round(float(np.median(np.abs(good))), 2) if good else None,
            'run_gt1.5_m': round(best * step, 1), 'run_at_s': where}


def main():
    D = json.load(open(os.path.join(ROOT, 'data', 'sfo_details.json')))
    out = {'centerlines': [], 'edges': []}
    meta = D.get('centerlineMeta') or [{}] * len(D['centerlines'])
    for i, (pl, m) in enumerate(zip(D['centerlines'], meta)):
        r = check_line(pl)
        if r: out['centerlines'].append(dict(r, i=i, ref=m.get('ref'), osm=m.get('osm_id'), drawn=m.get('drawn', True)))
    for i, pl in enumerate(D['edges']):
        r = check_line(pl)
        if r: out['edges'].append(dict(r, i=i))
    for k in ('centerlines', 'edges'):
        L = out[k]; drawn = [r for r in L if r.get('drawn', True)]
        meds = [r['med'] for r in drawn if r['med'] is not None]
        bad = [r for r in drawn if r['run_gt1.5_m'] >= 6]
        nop = [r for r in drawn if r['n'] and r['paint'] < 0.25 * r['n']]
        print('%s: %d lines (%d drawn), median of line medians %.2f m; drawn lines with a run >= 6 m over 1.5 m: %d; drawn with paint in < 25 %% of samples: %d (%.2f km)' % (
            k, len(L), len(drawn), float(np.median(meds)), len(bad), len(nop), sum(r['len'] for r in nop) / 1000))
        for r in sorted(bad, key=lambda r: -r['run_gt1.5_m']):
            print('   %s %d%s: run %.0f m at s=%.0f (len %.0f, median %.2f, paint %d/%d)' % (k[:-1], r['i'], ' ' + str(r.get('ref')) if r.get('ref') else '', r['run_gt1.5_m'], r['run_at_s'], r['len'], r['med'] or -1, r['paint'], r['n']))
    if '--json' in sys.argv: json.dump(out, open(sys.argv[sys.argv.index('--json') + 1], 'w'))


if __name__ == '__main__':
    main()
