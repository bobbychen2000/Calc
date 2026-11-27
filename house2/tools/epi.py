"""Guided triangulation: the ray of a pixel in image A, sampled at world heights, drawn into image B.

    python3 -I tools/epi.py A u,v B OUT.jpg [z0 z1 dz] [scale]       # images as paths under refs/cache
Draws the track (a tick + the height label every dz metres) on a crop of B around it; read off where the track
crosses the feature in B to get its height (and so its world position). Cameras: model.frame.world_cams().
"""
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from model import frame  # noqa: E402
from tools import cams as CAMS  # noqa: E402


def track(ca, uv, cb, zs):
    o, d = CAMS.ray(ca, [uv])
    t = (np.asarray(zs) - o[2]) / d[0][2]
    X = o + t[:, None] * d[0]
    return X, CAMS.project(cb, X)


if __name__ == '__main__':
    a, uv, b, out = sys.argv[1], [float(x) for x in sys.argv[2].split(',')], sys.argv[3], sys.argv[4]
    z0, z1, dz = (float(x) for x in sys.argv[5:8]) if len(sys.argv) > 7 else (0.0, 10.0, 0.5)
    sc = float(sys.argv[8]) if len(sys.argv) > 8 else 2.0
    W = frame.world_cams()
    zs = np.arange(z0, z1 + 1e-9, dz)
    X, P = track(W[a], uv, W[b], zs)
    im = cv2.imread(os.path.join(HERE, 'refs', 'cache', b))
    x0, y0 = np.maximum(P.min(0) - 60, 0).astype(int)
    x1, y1 = np.minimum(P.max(0) + 60, [im.shape[1], im.shape[0]]).astype(int)
    crop = cv2.resize(im[y0:y1, x0:x1], None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)
    q = (P - [x0, y0]) * sc
    for i in range(len(zs) - 1):
        cv2.line(crop, tuple(q[i].astype(int)), tuple(q[i + 1].astype(int)), (0, 255, 255), 1)
    for z, p in zip(zs, q):
        cv2.circle(crop, tuple(p.astype(int)), 2, (0, 0, 255), -1)
        if abs(z / (2 * dz) - round(z / (2 * dz))) < 1e-6:
            cv2.putText(crop, '%.1f' % z, tuple((p + [5, -3]).astype(int)), 0, 0.4, (0, 0, 255), 1)
    cv2.imwrite(out, crop)
    for z, x, p in zip(zs, X, P):
        print('z %5.2f  world (%7.2f, %7.2f)  ->  %s (%.1f, %.1f)' % (z, x[0], x[1], os.path.basename(b), p[0], p[1]))
