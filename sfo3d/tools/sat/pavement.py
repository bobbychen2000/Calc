"""Paved-surface map from the georeferenced satellite screenshots (best resolution wins per cell): low-saturation grey
pixels inside the airport land area, cleaned morphologically; output polygons (world x,z) for areas that the SFO Museum
geometry does not cover (cargo / maintenance aprons, service roads, GA ramps)."""
import json, os, math
import numpy as np, cv2
from scipy import ndimage as ndi
from common import *
from stview import V, UV, st2w, w2st
from rectify import REG, sim_of
RES = 1.0
S0, T0, S1, T1 = -2800.0, -1760.0, 1900.0, 1460.0
W, H = int((S1 - S0) / RES), int((T1 - T0) / RES)
U = open(SP + 'uniq.txt').read().split()
def P(pts): return np.array([[(s - S0) / RES, (T1 - t) / RES] for s, t in pts])
def mosaic():
    jj, ii = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    S = S0 + (jj + 0.5) * RES; T = T1 - (ii + 0.5) * RES
    ex = (S * V[0] + T * UV[0]).ravel(); en = (S * V[1] + T * UV[1]).ravel()
    out = np.zeros((H, W, 3), np.uint8); best = np.zeros((H, W), np.float32)
    for n in REG:
        if n == '8b334c52': continue
        img = cv2.imread([u for u in U if n in u][0])
        Pp = sim_of(n).fwd(np.stack([ex, -en], 1)).astype(np.float32)
        mx = Pp[:, 0].reshape(H, W); my = Pp[:, 1].reshape(H, W)
        bottom = 2150 if n in ('0af09b78', '35809e3e', '4637f855', 'bc91df95') else 2230
        valid = (mx > 8) & (mx < 1282) & (my > 345) & (my < bottom) & ~((my < 905) & (mx > 1075)) & ~((my > 1875) & (mx > 1025))
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        ui = ((hsv[..., 1] > 150) & (hsv[..., 2] > 150)) | (img.min(2) > 245)
        ui = cv2.dilate(ui.astype(np.uint8), np.ones((11, 11), np.uint8))
        valid &= ~(cv2.remap(ui, mx, my, cv2.INTER_NEAREST, borderValue=1) > 0)
        take = valid & (REG[n]['s'] > best)
        if not take.any(): continue
        k = max(1, int(round(REG[n]['s'] * RES * 0.6)))
        src = cv2.blur(img, (k, k)) if k > 1 else img
        r = cv2.remap(src, mx, my, cv2.INTER_LINEAR)
        out[take] = r[take]; best[take] = REG[n]['s']
        del mx, my, Pp
    return out, best
if __name__ == '__main__':
    img, best = mosaic()
    np.save(SP + 'apt_mosaic.npy', img); np.save(SP + 'apt_best.npy', best)
    cv2.imwrite(SP + 'apt_mosaic.jpg', cv2.resize(img, None, fx=0.3, fy=0.3, interpolation=cv2.INTER_AREA))
    print('mosaic', img.shape, 'coverage', float((best > 0).mean()))
