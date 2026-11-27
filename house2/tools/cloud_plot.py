"""Plot a coloured point cloud as top / front / side / rear views with coordinate ticks.

    python3 -I tools/cloud_plot.py NPZ OUT_PREFIX x0 x1 y0 y1 z0 z1 [px_per_unit] [min_conf] [tick]

NPZ: refs/cache/sfm_points_S.npz (S frame) or refs/cache/vggt/run1_cloud.npz (world metres; has 'conf').
Views: top (x right, y up), front (looking +y: x right, z up), rear (looking -y: x reversed), side (looking +x from the left: y right).
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw


def main():
    a = sys.argv
    d = np.load(a[1], allow_pickle=True)
    P, col = d['P'].astype(float), d['col']
    x0, x1, y0, y1, z0, z1 = [float(v) for v in a[3:9]]
    s = float(a[9]) if len(a) > 9 else 500.0
    m = (P[:, 0] >= x0) & (P[:, 0] <= x1) & (P[:, 1] >= y0) & (P[:, 1] <= y1) & (P[:, 2] >= z0) & (P[:, 2] <= z1)
    if len(a) > 10 and 'conf' in d:
        m &= d['conf'] >= float(a[10])
    step = float(a[11]) if len(a) > 11 else (0.1 if s > 100 else 5.0)
    P, col = P[m], col[m]
    print('points in box', len(P))
    views = {'top': (0, 1, 2, x0, x1, y0, y1, 1, False), 'front': (0, 2, 1, x0, x1, z0, z1, -1, False),
             'rear': (0, 2, 1, x0, x1, z0, z1, 1, True), 'side': (1, 2, 0, y0, y1, z0, z1, -1, False)}
    for name, (i, j, k, a0, a1, b0, b1, sign, flip) in views.items():
        W, H = int((a1 - a0) * s) + 1, int((b1 - b0) * s) + 1
        img = np.full((H, W, 3), 24, np.uint8)
        order = np.argsort(sign * P[:, k])            # draw far points first
        u = ((P[order, i] - a0) * s).astype(int)
        if flip:
            u = W - 1 - u
        v = (H - 1 - (P[order, j] - b0) * s).astype(int)
        r = 2 if len(P) < 200000 else 1
        for du in range(r):
            for dv in range(r):
                img[np.clip(v + dv, 0, H - 1), np.clip(u + du, 0, W - 1)] = col[order]
        im = Image.fromarray(img)
        dr = ImageDraw.Draw(im)
        t = np.ceil(a0 / step) * step
        while t < a1:
            px = (t - a0) * s
            if flip:
                px = W - 1 - px
            dr.line([(px, 0), (px, 10)], fill=(255, 255, 0))
            dr.line([(px, H - 10), (px, H)], fill=(255, 255, 0))
            dr.text((px + 2, 1), ('%.1f' if step < 1 else '%.0f') % t, fill=(255, 255, 0))
            t += step
        t = np.ceil(b0 / step) * step
        while t < b1:
            py = H - 1 - (t - b0) * s
            dr.line([(0, py), (10, py)], fill=(255, 255, 0))
            dr.line([(W - 10, py), (W, py)], fill=(255, 255, 0))
            dr.text((12, py - 5), ('%.1f' if step < 1 else '%.0f') % t, fill=(255, 255, 0))
            t += step
        im.save('%s_%s.png' % (a[2], name))
        print(name, im.size)


if __name__ == '__main__':
    main()
