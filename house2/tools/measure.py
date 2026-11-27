"""Measure in world metres through the registered cameras (survey/frame.json + refs/cache/cams_S.json).

    python3 -I tools/measure.py ray  IMAGE u v x=VAL|y=VAL|z=VAL     where the pixel's ray meets an axis plane
    python3 -I tools/measure.py tri  IMAGE1 u v IMAGE2 u v [IMAGE3 u v ...]   triangulate one point (+ pixel residuals)
    python3 -I tools/measure.py proj IMAGE X Y Z [X Y Z ...]         project world points into an image
    python3 -I tools/measure.py cams                                 list the registered cameras (world pose)

World axes: X right along the street (seen from the street), Y into the lot, Z up; metres.
IMAGE is a path relative to refs/cache (e.g. frames/seg002_043.jpg).  Pixels are original-image pixels.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from model import frame  # noqa: E402
from tools import cams as CAMS  # noqa: E402


def main():
    a = sys.argv[1:]
    W = frame.world_cams()
    if a[0] == 'cams':
        for k in sorted(W):
            print('%-28s %s' % (k, CAMS.describe(W[k])))
    elif a[0] == 'ray':
        cam = W[a[1]]
        ax, val = a[4].split('=')
        P = CAMS.hit_plane(cam, [[float(a[2]), float(a[3])]], **{ax: float(val)})[0]
        print('X=%.3f Y=%.3f Z=%.3f' % tuple(P))
    elif a[0] == 'tri':
        obs = [(W[a[i]], (float(a[i + 1]), float(a[i + 2]))) for i in range(1, len(a), 3)]
        X, res = CAMS.triangulate(obs)
        print('X=%.3f Y=%.3f Z=%.3f   residuals px: %s' % (*X, np.round(res, 1).tolist()))
    elif a[0] == 'proj':
        cam = W[a[1]]
        pts = np.array([float(v) for v in a[2:]]).reshape(-1, 3)
        uv, z = CAMS.project(cam, pts, depth=True)
        for p, q, d in zip(pts, uv, z):
            print('(%.2f, %.2f, %.2f) -> u=%.1f v=%.1f  depth %.1f m%s' % (*p, q[0], q[1], d, '' if d > 0 else '  (behind)'))


if __name__ == '__main__':
    main()
