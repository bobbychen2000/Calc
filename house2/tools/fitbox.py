"""Fit a plane to the SfM points inside a world box (RANSAC):  python3 -I tools/fitbox.py x0 x1 y0 y1 z0 z1 [tol] [name]
Prints pitch, downhill azimuth (clockwise from +Y), z = a x + b y + c, inliers and their extent.
Also:  python3 -I tools/fitbox.py section x=VAL|y=VAL  -> height profile of the aerial height map + SfM points along a line."""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from model import frame  # noqa: E402


def sfm():
    d = np.load(os.path.join(HERE, 'refs', 'cache', 'sfm_points_S.npz'))
    return frame.to_world(d['P'].astype(float))


def fit(P, box, tol=0.035, iters=1500, seed=0):
    m = (P[:, 0] > box[0]) & (P[:, 0] < box[1]) & (P[:, 1] > box[2]) & (P[:, 1] < box[3]) & (P[:, 2] > box[4]) & (P[:, 2] < box[5])
    Q = P[m]
    if len(Q) < 12:
        return None
    rng = np.random.default_rng(seed)
    best = None
    for _ in range(iters):
        t = Q[rng.choice(len(Q), 3, replace=False)]
        n = np.cross(t[1] - t[0], t[2] - t[0])
        ln = np.linalg.norm(n)
        if ln < 1e-9:
            continue
        inl = np.abs((Q - t[0]) @ (n / ln)) < tol
        if best is None or inl.sum() > best.sum():
            best = inl
    T = Q[best]
    A = np.c_[T[:, 0], T[:, 1], np.ones(len(T))]
    c = np.linalg.lstsq(A, T[:, 2], rcond=None)[0]
    return dict(n=int(best.sum()), total=len(Q), abc=c, pitch=float(np.degrees(np.arctan(np.hypot(c[0], c[1])))),
                az=float((np.degrees(np.arctan2(-c[0], -c[1])) + 360) % 360), lo=np.percentile(T, 2, 0), hi=np.percentile(T, 98, 0))


def section(spec):
    ax, val = spec.split('=')
    val = float(val)
    d = np.load(os.path.join(HERE, 'refs', 'cache', 'dsm.npz'))
    D = d['P'].astype(float)
    S = sfm()
    i, j = (0, 1) if ax == 'x' else (1, 0)
    rng = np.arange(-6, 20.01, 0.5) if ax == 'x' else np.arange(-2, 27.01, 0.5)
    row = []
    for t in rng:
        m = (np.abs(D[:, i] - val) < 0.35) & (np.abs(D[:, j] - t) < 0.25)
        ms = (np.abs(S[:, i] - val) < 0.35) & (np.abs(S[:, j] - t) < 0.25) & (S[:, 2] > 2.0)
        z = np.max(D[m, 2]) if m.sum() else np.nan
        zs = np.percentile(S[ms, 2], 90) if ms.sum() >= 3 else np.nan
        row.append((t, z, zs))
    print('%s = %.1f   (%s: map / SfM p90)' % (ax, val, 'y' if ax == 'x' else 'x'))
    print('  '.join('%.1f:%.1f%s' % (t, z, ('/%.1f' % zs) if zs == zs else '') for t, z, zs in row))


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'section':
        for s in a[1:]:
            section(s)
    else:
        box = [float(v) for v in a[:6]]
        r = fit(sfm(), box, float(a[6]) if len(a) > 6 else 0.035)
        if r is None:
            print('too few points')
        else:
            print('%s n=%d/%d pitch %.1f az %.0f  z = %+.4f x %+.4f y %+.3f  X %.2f..%.2f Y %.2f..%.2f Z %.2f..%.2f' % (
                a[7] if len(a) > 7 else '', r['n'], r['total'], r['pitch'], r['az'], *r['abc'], r['lo'][0], r['hi'][0], r['lo'][1], r['hi'][1], r['lo'][2], r['hi'][2]))
