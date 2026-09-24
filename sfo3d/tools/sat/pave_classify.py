import json, os
import numpy as np, cv2
from scipy import ndimage as ndi
from common import *
from pavement import W, H, RES, S0, T1, P
from stview import w2st, st2w
img = np.load(SP + 'apt_mosaic.npy'); best = np.load(SP + 'apt_best.npy')
b, g, r = [img[..., i].astype(np.int16) for i in range(3)]
mx = np.maximum(np.maximum(r, g), b); mn = np.minimum(np.minimum(r, g), b); lum = (r + g + b) / 3
sat = mx - mn
gray = (sat < 26) & (lum > 72) & (lum < 250) & (np.abs(r - b) < 20)
soil = (r - b > 24) & (sat >= 20)
veg = (g - b > 12) & (g >= r - 4) & (sat >= 18) & ~((g - r > 20) & (b - r > 3))  # not green paint
water = (b > r + 6) & (g > r + 4) & (lum < 110)
paint = (g - r > 20) & (b - r > 3) & (g - b > 5) & (lum > 85)
cov = best > 0
pave = (gray | paint) & cov
# smooth: majority in 5x5 then open/close
pave = ndi.binary_opening(pave, iterations=2)
pave = ndi.binary_closing(pave, iterations=3)
# fill small holes (< 250 m2: aircraft shadows, vehicles, markings); drop small blobs (< 600 m2)
holes = ndi.binary_fill_holes(pave) & ~pave
lab, nl = ndi.label(holes); hs = ndi.sum(holes, lab, range(1, nl + 1))
pave |= np.isin(lab, 1 + np.nonzero(hs * RES * RES < 250)[0])
lab, nl = ndi.label(pave); ps = ndi.sum(pave, lab, range(1, nl + 1))
pave &= np.isin(lab, 1 + np.nonzero(ps * RES * RES >= 600)[0])
np.save(SP + 'pave_sat.npy', pave)
vis = img.copy() // 2
vis[pave] = (vis[pave] * 0.4 + np.array([200, 120, 40]) * 0.6).astype(np.uint8)
cv2.imwrite(SP + 'pave_sat.jpg', cv2.resize(vis, None, fx=0.3, fy=0.3, interpolation=cv2.INTER_AREA))
print('paved fraction of covered', float(pave.sum() / cov.sum()))
