"""Overlay check of a registered image: the SfM points (frame S) projected through its camera, drawn in their own
colour (left) next to the image (right), and a 50 % blend.

    python3 -I tools/ptcheck.py IMG OUT.jpg [cams_file]
"""
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from tools import cams as CAMS  # noqa: E402

CACHE = os.path.join(HERE, 'refs', 'cache')

if __name__ == '__main__':
    img, out = sys.argv[1], sys.argv[2]
    src = sys.argv[3] if len(sys.argv) > 3 else 'cams_fixed.json'
    cam = CAMS.load(os.path.join(CACHE, src))[img]
    d = np.load(os.path.join(CACHE, 'sfm_points_S.npz'))
    P, col = d['P'].astype(float), d['col']
    uv, z = CAMS.project(cam, P, depth=True)
    im = cv2.imread(os.path.join(CACHE, img))
    h, w = im.shape[:2]
    ok = (z > 0) & (uv[:, 0] >= 0) & (uv[:, 0] < w) & (uv[:, 1] >= 0) & (uv[:, 1] < h)
    o = np.argsort(-z[ok])
    pts = np.zeros_like(im)
    for (u, v), c in zip(uv[ok][o].astype(int), col[ok][o]):
        cv2.circle(pts, (u, v), max(1, w // 900), tuple(int(x) for x in c[::-1]), -1)
    blend = cv2.addWeighted(im, 0.5, pts, 0.8, 0)
    s = 1200 / w
    cv2.imwrite(out, cv2.resize(np.vstack([np.hstack([pts, im]), np.hstack([blend, im])]), None, fx=s / 2 * 2 / 2,
                                fy=s / 2 * 2 / 2, interpolation=cv2.INTER_AREA))
    print(out, ok.sum(), 'points')
