"""Slope-direction map of the roofs from the aerial height map (refs/cache/dsm.npz): each network pixel over the
house is coloured by which way its surface falls (S = toward the street red, N = toward the back blue, W yellow,
E green, flat grey), over the dimmed aerial photo, with ticks in ORIGINAL aerial pixels.

    python3 -I tools/roof_seg.py OUT.png [scale]
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def labels():
    d = np.load(os.path.join(HERE, 'refs', 'cache', 'dsm.npz'))
    nh, nw = d['shape']
    P = d['P'].reshape(nh, nw, 3).astype(float)
    col = d['col'].reshape(nh, nw, 3)
    Z = P[..., 2]
    gx, gy = np.gradient(P, axis=1), np.gradient(P, axis=0)
    n = np.cross(gx, gy)
    n /= np.linalg.norm(n, axis=2, keepdims=True) + 1e-9
    n[n[..., 2] < 0] *= -1
    pitch = np.degrees(np.arccos(np.clip(n[..., 2], -1, 1)))
    az = (np.degrees(np.arctan2(n[..., 0], n[..., 1])) + 360) % 360
    roof = (Z > 2.6) & (P[..., 0] > -1) & (P[..., 0] < 27) & (P[..., 1] > -5) & (P[..., 1] < 24)
    lab = np.zeros((nh, nw), np.uint8)
    lab[roof & (pitch < 9)] = 1
    for k, a0 in ((2, 180), (3, 0), (4, 270), (5, 90)):
        dd = np.abs((az - a0 + 180) % 360 - 180)
        lab[roof & (pitch >= 9) & (pitch < 50) & (dd <= 45)] = k
    return lab, P, col, pitch


def main():
    out = sys.argv[1]
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    lab, P, col, pitch = labels()
    nh, nw = lab.shape
    pal = np.array([(0, 0, 0), (150, 150, 150), (255, 80, 80), (80, 160, 255), (255, 220, 60), (80, 220, 120)], np.uint8)
    img = np.where((lab > 0)[..., None], (0.5 * pal[lab] + 0.5 * col).astype(np.uint8), (col * 0.5).astype(np.uint8))
    ys, xs = np.where(lab > 0)
    y0, y1, x0, x1 = max(ys.min() - 6, 0), min(ys.max() + 6, nh), max(xs.min() - 6, 0), min(xs.max() + 6, nw)
    im = Image.fromarray(img[y0:y1, x0:x1]).resize(((x1 - x0) * k, (y1 - y0) * k), Image.NEAREST)
    d = ImageDraw.Draw(im)
    s = 1843 / nw                               # network px -> original aerial px (same factor both ways)
    for g in range(0, 2600, 100):
        px = (g / s - x0) * k
        if 0 < px < im.width:
            d.line([(px, 0), (px, 12)], fill=(255, 255, 255)); d.text((px + 2, 1), str(g), fill=(255, 255, 255))
        py = (g / s - y0) * k
        if 0 < py < im.height:
            d.line([(0, py), (12, py)], fill=(255, 255, 255)); d.text((14, py - 5), str(g), fill=(255, 255, 255))
    im.save(out)
    print(im.size, 'network px per original px', round(1 / s, 4))




def regions(min_px=60):
    """Connected regions of one slope class: bbox in ORIGINAL aerial pixels, plane fit (z = a x + b y + c, world),
    pitch, height range, and the same from the SfM points that fall in the region when there are enough."""
    import json
    from scipy import ndimage
    sys.path.insert(0, HERE)
    from model import frame
    from tools import cams as CAMS
    lab, P, col, pitch = labels()
    nh, nw = lab.shape
    s = 1843 / nw
    cam = frame.world_cams()['photos/p30_b7b282.jpg']
    S = frame.to_world(np.load(os.path.join(HERE, 'refs', 'cache', 'sfm_points_S.npz'))['P'].astype(float))
    uv, zc = CAMS.project(cam, S, depth=True)
    su, sv = (uv[:, 0] / s).astype(int), (uv[:, 1] / s).astype(int)
    ok = (zc > 0) & (su >= 0) & (su < nw) & (sv >= 0) & (sv < nh)
    names = {1: 'flat', 2: 'S', 3: 'N', 4: 'W', 5: 'E'}
    out = []
    for k in range(1, 6):
        cc, n = ndimage.label(ndimage.binary_opening(lab == k, iterations=1))
        for i in range(1, n + 1):
            m = cc == i
            if m.sum() < min_px:
                continue
            ys, xs = np.where(m)
            Q = P[m]
            A = np.c_[Q[:, 0], Q[:, 1], np.ones(len(Q))]
            c = np.linalg.lstsq(A, Q[:, 2], rcond=None)[0]
            r = dict(cls=names[k], px=int(m.sum()), bbox=[int(xs.min() * s), int(ys.min() * s), int(xs.max() * s), int(ys.max() * s)],
                     X=[round(float(Q[:, 0].min()), 1), round(float(Q[:, 0].max()), 1)], Y=[round(float(Q[:, 1].min()), 1), round(float(Q[:, 1].max()), 1)],
                     z=[round(float(np.percentile(Q[:, 2], 3)), 2), round(float(np.percentile(Q[:, 2], 97)), 2)],
                     pitch=round(float(np.degrees(np.arctan(np.hypot(c[0], c[1])))), 1), plane=[round(float(v), 4) for v in c])
            inside = ok & False
            inside[ok] = m[sv[ok], su[ok]]
            if inside.sum() >= 25:
                T = S[inside]
                A2 = np.c_[T[:, 0], T[:, 1], np.ones(len(T))]
                c2 = np.linalg.lstsq(A2, T[:, 2], rcond=None)[0]
                res = A2 @ c2 - T[:, 2]
                keep = np.abs(res) < 0.12
                if keep.sum() >= 20:
                    c2 = np.linalg.lstsq(A2[keep], T[keep, 2], rcond=None)[0]
                    r['sfm'] = dict(n=int(keep.sum()), pitch=round(float(np.degrees(np.arctan(np.hypot(c2[0], c2[1])))), 1),
                                    plane=[round(float(v), 4) for v in c2], z=[round(float(T[keep, 2].min()), 2), round(float(T[keep, 2].max()), 2)])
            out.append(r)
    out.sort(key=lambda r: -r['px'])
    return out


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'regions':
    for r in regions():
        sf = r.get('sfm')
        print('%-4s %5d px  aerial bbox %s  X %s Y %s  z %s  pitch %4.1f%s' % (
            r['cls'], r['px'], r['bbox'], r['X'], r['Y'], r['z'], r['pitch'],
            ('   | SfM n=%d pitch %.1f z %s plane %s' % (sf['n'], sf['pitch'], sf['z'], sf['plane'])) if sf else ''))

if __name__ == '__main__' and not (len(sys.argv) > 1 and sys.argv[1] == 'regions'):
    main()
