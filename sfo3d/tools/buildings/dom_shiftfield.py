"""Domestic terminals - inter-epoch NAIP displacement field (relief parallax) for roof heights.

Principle (docs/research/imagery.md s.6; tools/buildings/tower_lean_ratio.py): NAIP is orthorectified to a terrain DEM,
so a point at height h above grade is imaged displaced by k_e * h, where k_e (m per m, a 2-D vector) depends on the
epoch's flight line and varies slowly over the scene. Between epochs a and b a roof point therefore moves by
(k_b - k_a) * h while the ground does not move. NAIP 2020 (2020-05-24, ~16:55 PDT) and 2024 (2024-05-20, ~13:15 PDT)
were flown on different lines, so the parallax is large (~0.6 m per m of height near the ATCT).

Method: both epochs are resampled to 0.5 m on the world grid (native GSD 0.6 m); gradient-magnitude images (Gaussian
sigma 1 px) are block-matched with normalised cross-correlation: a 20 m x 20 m template of epoch a, centred on a node of
a 5 m lattice, is searched in epoch b over dx in [-8, +30] m, dz in [-8, +8] m; parabolic sub-pixel refinement. Kept per
node: shift (dx, dz), peak NCC, and the peak ratio (best / second-best peak outside 3 m) as an ambiguity measure
(regular PV-panel rows can alias). Only nodes inside the dilated SFO Museum footprints (+ a 40 m apron ring as the
zero-parallax control) are evaluated.

Output: refs/cache/buildings/domestic/shift_<a>_<b>.npz (arrays x, z, dx, dz, ncc, ratio) and a QA map
out/buildings/domestic/shift_<a>_<b>.jpg (colour = dx over the 2024 image). Heights are derived in dom_heights.py.

usage: python3 tools/buildings/dom_shiftfield.py [--a 2020 --b 2024]
"""
import argparse, os
import numpy as np
import cv2
import dom_common as C

RES = 0.5
TPL = 20.0      # template size (m)
STEP = 5.0      # lattice step (m)
DX = (-8.0, 30.0)
DZ = (-8.0, 8.0)


def grad(img):
    g = cv2.GaussianBlur(C.gray(img), (0, 0), 1.0)
    return cv2.magnitude(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--a', default='2020'); ap.add_argument('--b', default='2024')
    a = ap.parse_args()
    _, m = C.epoch(int(a.b))
    X0, X1, Z0, Z1 = m['x0'], m['x1'], m['z0'], m['z1']
    IA, o = C.crop(int(a.a), X0, X1, Z0, Z1, res=RES); IB, _ = C.crop(int(a.b), X0, X1, Z0, Z1, res=RES)
    GA, GB = grad(IA), grad(IB)
    H, W = GA.shape
    # evaluation mask: footprints dilated by 40 m
    mask = np.zeros((H, W), np.uint8)
    for rings in C.footprints().values():
        for ring in rings:
            pts = np.array([[(x - X0) / RES, (z - Z0) / RES] for x, z in ring], np.int32)
            cv2.fillPoly(mask, [pts], 1)
    mask = cv2.dilate(mask, np.ones((161, 161), np.uint8))
    t = int(TPL / RES); h = t // 2
    sx0, sx1 = int(DX[0] / RES), int(DX[1] / RES); sz0, sz1 = int(DZ[0] / RES), int(DZ[1] / RES)
    out = {k: [] for k in ('x', 'z', 'dx', 'dz', 'ncc', 'ratio')}
    for zc in np.arange(Z0 + TPL, Z1 - TPL, STEP):
        for xc in np.arange(X0 + TPL, X1 - TPL - DX[1], STEP):
            r, c = int((zc - Z0) / RES), int((xc - X0) / RES)
            if not mask[r, c]: continue
            tpl = GA[r - h:r + h, c - h:c + h]
            if tpl.std() < 2.0: continue
            R0, R1 = r - h + sz0, r + h + sz1; C0, C1 = c - h + sx0, c + h + sx1
            if R0 < 0 or C0 < 0 or R1 > H or C1 > W: continue
            res = cv2.matchTemplate(GB[R0:R1, C0:C1], tpl, cv2.TM_CCOEFF_NORMED)
            _, mx, _, loc = cv2.minMaxLoc(res)
            x, y = loc
            def sub(p, q, s):
                d = p - 2 * q + s
                return 0.0 if abs(d) < 1e-9 else 0.5 * (p - s) / d
            fx = sub(res[y, x - 1], res[y, x], res[y, x + 1]) if 0 < x < res.shape[1] - 1 else 0.0
            fy = sub(res[y - 1, x], res[y, x], res[y + 1, x]) if 0 < y < res.shape[0] - 1 else 0.0
            r2 = res.copy(); rr = int(3 / RES)
            r2[max(0, y - rr):y + rr + 1, max(0, x - rr):x + rr + 1] = -1
            second = r2.max()
            out['x'].append(xc); out['z'].append(zc)
            out['dx'].append((x + fx + sx0) * RES); out['dz'].append((y + fy + sz0) * RES)
            out['ncc'].append(mx); out['ratio'].append(mx / max(second, 1e-3))
    arr = {k: np.array(v, np.float32) for k, v in out.items()}
    np.savez(os.path.join(C.NAIP_DIR, '..', f'shift_{a.a}_{a.b}.npz'), **arr)
    # QA map
    base, o = C.crop(int(a.b), X0, X1, Z0, Z1, res=1.0)
    im = (base * 0.55).astype(np.uint8)
    good = (arr['ncc'] > 0.5) & (arr['ratio'] > 1.15)
    for x, z, dx, g in zip(arr['x'], arr['z'], arr['dx'], good):
        if not g: continue
        v = np.clip((dx + 2) / 24.0, 0, 1)
        col = cv2.applyColorMap(np.uint8([[v * 255]]), cv2.COLORMAP_TURBO)[0, 0].tolist()
        cv2.circle(im, (int(x - X0), int(z - Z0)), 2, col, -1)
    C.save_qa(f'shift_{a.a}_{a.b}.jpg', C.grid_overlay(im, o, step=50, label=100))
    print('nodes', len(arr['x']), 'good', int(good.sum()))


if __name__ == '__main__':
    main()
