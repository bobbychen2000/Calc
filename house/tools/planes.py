"""Find the dominant planes in the SfM point cloud (world metres): roof pitches, eave / ridge heights, wall lines.

    python3 -I tools/planes.py [x0 x1 y0 y1 z0 z1] [tol_m] [min_points]
Sequential RANSAC; prints for each plane its normal as (pitch from horizontal, downhill azimuth clockwise from +Y),
the height range and plan extent of its inliers and the plane equation z = a x + b y + c (or the wall line).
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from model import frame  # noqa: E402


def main():
    a = [float(v) for v in sys.argv[1:]]
    box = a[:6] if len(a) >= 6 else [-2, 28, -6, 24, 2.2, 12]
    tol = a[6] if len(a) > 6 else 0.04
    nmin = int(a[7]) if len(a) > 7 else 120
    d = np.load(os.path.join(HERE, 'refs', 'cache', 'sfm_points_S.npz'))
    P = frame.to_world(d['P'].astype(float))
    col = d['col']
    m = (P[:, 0] > box[0]) & (P[:, 0] < box[1]) & (P[:, 1] > box[2]) & (P[:, 1] < box[3]) & (P[:, 2] > box[4]) & (P[:, 2] < box[5])
    P, col = P[m], col[m]
    print(len(P), 'points in the box')
    rng = np.random.default_rng(1)
    rest = np.arange(len(P))
    found = []
    for it in range(40):
        if len(rest) < nmin:
            break
        Q = P[rest]
        best = None
        for _ in range(1500):
            i = rng.integers(len(Q))
            near = np.where(np.linalg.norm(Q - Q[i], axis=1) < 2.5)[0]      # local seeds: planes are patches
            if len(near) < 8:
                continue
            tri = Q[rng.choice(near, 3, replace=False)]
            n = np.cross(tri[1] - tri[0], tri[2] - tri[0])
            ln = np.linalg.norm(n)
            if ln < 1e-6:
                continue
            n /= ln
            dist = np.abs((Q - tri[0]) @ n)
            inl = dist < tol
            if best is None or inl.sum() > best[0]:
                best = (inl.sum(), inl)
        if best is None or best[0] < nmin:
            break
        inl = best[1]
        pts = Q[inl]
        c = pts.mean(0)
        n = np.linalg.svd(pts - c)[2][-1]
        if n[2] < 0:
            n = -n
        pitch = np.degrees(np.arccos(np.clip(n[2], -1, 1)))
        az = (np.degrees(np.arctan2(n[0], n[1])) + 360) % 360           # downhill direction (the normal's plan heading)
        lo, hi = np.percentile(pts, 2, 0), np.percentile(pts, 98, 0)
        rgb = np.median(col[rest][inl], 0).astype(int)
        if pitch < 80:
            aa, bb = -n[0] / n[2], -n[1] / n[2]
            eq = 'z = %+.4f x %+.4f y %+.3f' % (aa, bb, c[2] - aa * c[0] - bb * c[1])
        else:
            eq = 'wall: %.3f x %+.3f y = %.3f' % (n[0], n[1], n[:2] @ c[:2])
        found.append((best[0], pitch, az, lo, hi, rgb, eq))
        print('%2d  n=%5d  pitch %5.1f  downhill az %5.1f  X %.2f..%.2f  Y %.2f..%.2f  Z %.2f..%.2f  rgb %s  %s' % (
            it, best[0], pitch, az, lo[0], hi[0], lo[1], hi[1], lo[2], hi[2], rgb.tolist(), eq))
        rest = rest[~inl]


if __name__ == '__main__':
    main()
