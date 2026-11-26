"""Plot the SfM points (S frame) as top / front / side views with ticks, optionally limited to a box.

    python3 -I tools/cloud_plot.py OUT_PREFIX [x0 x1 y0 y1 z0 z1] [px_per_unit]
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    d = np.load(os.path.join(HERE, 'refs', 'cache', 'sfm_points_S.npz'))
    P, col = d['P'].astype(float), d['col']
    a = sys.argv
    box = [float(v) for v in a[2:8]] if len(a) >= 8 else list(np.percentile(P, 1, 0)) + list(np.percentile(P, 99, 0))
    if len(a) < 8:
        box = [box[0], box[3], box[1], box[4], box[2], box[5]]
    s = float(a[8]) if len(a) > 8 else 500.0
    x0, x1, y0, y1, z0, z1 = box
    m = (P[:, 0] >= x0) & (P[:, 0] <= x1) & (P[:, 1] >= y0) & (P[:, 1] <= y1) & (P[:, 2] >= z0) & (P[:, 2] <= z1)
    P, col = P[m], col[m]
    print('points in box', len(P))
    views = {'top': (0, 1, 2, x0, x1, y0, y1), 'front': (0, 2, 1, x0, x1, z0, z1), 'side': (1, 2, 0, y0, y1, z0, z1)}
    for name, (i, j, k, a0, a1, b0, b1) in views.items():
        W, H = int((a1 - a0) * s) + 1, int((b1 - b0) * s) + 1
        img = np.full((H, W, 3), 24, np.uint8)
        order = np.argsort(P[:, k]) if name == 'top' else np.argsort(-P[:, k])
        u = ((P[order, i] - a0) * s).astype(int)
        v = (H - 1 - (P[order, j] - b0) * s).astype(int)
        for du in (0, 1, 2):
            for dv in (0, 1, 2):
                img[np.clip(v + dv, 0, H - 1), np.clip(u + du, 0, W - 1)] = col[order]
        im = Image.fromarray(img)
        dr = ImageDraw.Draw(im)
        step = 0.1
        t = np.ceil(a0 / step) * step
        while t < a1:
            px = (t - a0) * s
            dr.line([(px, 0), (px, 10)], fill=(255, 255, 0))
            dr.line([(px, H - 10), (px, H)], fill=(255, 255, 0))
            dr.text((px + 2, 1), '%.1f' % t, fill=(255, 255, 0))
            t += step
        t = np.ceil(b0 / step) * step
        while t < b1:
            py = H - 1 - (t - b0) * s
            dr.line([(0, py), (10, py)], fill=(255, 255, 0))
            dr.line([(W - 10, py), (W, py)], fill=(255, 255, 0))
            dr.text((12, py - 5), '%.1f' % t, fill=(255, 255, 0))
            t += step
        im.save('%s_%s.png' % (a[1], name))
        print(name, im.size)


if __name__ == '__main__':
    main()
