"""Green no-taxi island paint (FAA AC 150/5340-1M 1.5.2: green border, FS 595 #34108) mapped from the georeferenced
screenshots: per grid cell the highest-resolution screenshot decides; output world polygons."""
import json, math
import numpy as np, cv2
from scipy import ndimage as ndi
from common import *
from stview import V, UV, st2w
from rectify import REG, sim_of
RES = 1.0
S0, T0, S1, T1 = -2050.0, -1560.0, 1850.0, 1300.0
W, H = int((S1 - S0) / RES), int((T1 - T0) / RES)
U = open(SP + 'uniq.txt').read().split()
def grid_maps(n):
    jj, ii = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    S = S0 + (jj + 0.5) * RES; T = T1 - (ii + 0.5) * RES
    ex = S * V[0] + T * UV[0]; en = S * V[1] + T * UV[1]
    sim = sim_of(n)
    P = sim.fwd(np.stack([ex.ravel(), (-en).ravel()], 1)).astype(np.float32)
    return P[:, 0].reshape(H, W), P[:, 1].reshape(H, W)
def paint_mask(img):
    b, g, r = [img[..., i].astype(np.int16) for i in range(3)]
    lum = (r + g + b) / 3
    return (g - r > 20) & (b - r > 3) & (g - b > 5) & (lum > 85) & (lum < 235)
if __name__ == '__main__':
    best_res = np.zeros((H, W), np.float32); mask = np.zeros((H, W), bool)
    for n in sorted(REG, key=lambda k: REG[k]['s']):
        if n in ('8b334c52',): continue
        img = cv2.imread([u for u in U if n in u][0])
        mx, my = grid_maps(n)
        bottom = 2150 if n in ('0af09b78', '35809e3e', '4637f855', 'bc91df95') else 2230
        valid = (mx > 8) & (mx < 1282) & (my > 345) & (my < bottom) & ~((my < 905) & (mx > 1075)) & ~((my > 1875) & (mx > 1025))
        # UI overlays (labels, pins): saturated / pure white blobs
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        ui = ((hsv[..., 1] > 150) & (hsv[..., 2] > 150)) | (img.min(2) > 245)
        ui = cv2.dilate(ui.astype(np.uint8), np.ones((9, 9), np.uint8))
        uiw = cv2.remap(ui, mx, my, cv2.INTER_NEAREST, borderValue=1) > 0
        valid &= ~uiw
        s = REG[n]['s']
        take = valid & (s > best_res)
        if not take.any(): continue
        # smooth a little before colour classification (JPEG noise); scale-aware
        im = cv2.GaussianBlur(img, (0, 0), max(0.6, 0.35 * s))
        rect = cv2.remap(im, mx, my, cv2.INTER_LINEAR)
        m = paint_mask(rect)
        mask[take] = m[take]; best_res[take] = s
        print(n, 's', round(s, 2), 'cells', int(take.sum()), 'paint', int((m & take).sum()))
    np.save(SP + 'paint_mask.npy', mask); np.save(SP + 'paint_res.npy', best_res)
    print('coverage', float((best_res > 0).mean()), 'paint cells', int(mask.sum()))
