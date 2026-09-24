"""Best-resolution mosaic of all registered screenshots over a grid box (s,t), for measurement views."""
import numpy as np, cv2
from common import *
from stview import V, UV, annotate
from rectify import REG, sim_of
U = open(SP + 'uniq.txt').read().split()
def mosaic(box, res):
    s0, t0, s1, t1 = box
    W, H = int((s1 - s0) / res), int((t1 - t0) / res)
    jj, ii = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    S = s0 + (jj + 0.5) * res; T = t1 - (ii + 0.5) * res
    ex = S * V[0] + T * UV[0]; en = S * V[1] + T * UV[1]
    out = np.zeros((H, W, 3), np.uint8); best = np.zeros((H, W), np.float32)
    for n in REG:
        if n == '8b334c52': continue
        img = cv2.imread([u for u in U if n in u][0])
        P = sim_of(n).fwd(np.stack([ex.ravel(), (-en).ravel()], 1)).astype(np.float32)
        mx = P[:, 0].reshape(H, W); my = P[:, 1].reshape(H, W)
        bottom = 2150 if n in ('0af09b78', '35809e3e', '4637f855', 'bc91df95') else 2230
        valid = (mx > 8) & (mx < 1282) & (my > 345) & (my < bottom) & ~((my < 905) & (mx > 1075)) & ~((my > 1875) & (mx > 1025))
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        ui = ((hsv[..., 1] > 150) & (hsv[..., 2] > 150)) | (img.min(2) > 245)
        ui = cv2.dilate(ui.astype(np.uint8), np.ones((9, 9), np.uint8))
        valid &= ~(cv2.remap(ui, mx, my, cv2.INTER_NEAREST, borderValue=1) > 0)
        take = valid & (REG[n]['s'] > best)
        if not take.any(): continue
        r = cv2.remap(img, mx, my, cv2.INTER_CUBIC)
        out[take] = r[take]; best[take] = REG[n]['s']
    return out, best
def mview(box, res, out, **kw):
    m, b = mosaic(box, res)
    m = annotate(m, *box, res, **kw)
    cv2.imwrite(out, m); return m, b
