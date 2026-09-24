import json, os
import numpy as np, cv2
from scipy import ndimage as ndi
from common import *
from pavement import W, H, RES, S0, T1, P
from stview import w2st, st2w
pave = np.load(SP + 'pave_sat.npy'); img = np.load(SP + 'apt_mosaic.npy'); best = np.load(SP + 'apt_best.npy')
DET = json.load(open(os.path.join(ROOT, 'data', 'sfo_details.json')))
def fillw(mask, rings, val=1):
    for i, ring in enumerate(rings):
        cv2.fillPoly(mask, [np.round(P([w2st(*q) for q in ring]) * 4).astype(np.int32)], val if i == 0 else 0, shift=2)
ex = np.zeros((H, W), np.uint8)
for k in ('taxiways', 'runways'):
    for t in D[k]:
        for poly in t['polys']: fillw(ex, poly)
for poly in DET['apron']: fillw(ex, poly)
for poly in D['terminalComplex']: fillw(ex, poly)
for b in D['boardingAreas']:
    for poly in b['polys']: fillw(ex, poly)
for s in D['structures']:
    for poly in s['polys']: fillw(ex, poly)
# airport land polygon (coarse) as a limit
from stview import w2st as _w
LAND = [[-2600, -1650], [-600, -1650], [-300, -1660], [420, -1640], [470, -1500], [420, -200], [1790, -210], [1850, -60], [1850, 330], [1790, 460], [470, 460], [470, 1320], [300, 1400], [-900, 1400], [-1500, 1350], [-2600, 1200]]
land = np.zeros((H, W), np.uint8); cv2.fillPoly(land, [np.round(P(LAND) * 4).astype(np.int32)], 1, shift=2)
exd = ndi.binary_dilation(ex > 0, iterations=3)
add = pave & ~exd & (land > 0)
add = ndi.binary_opening(add, iterations=3)
lab, nl = ndi.label(add); sz = ndi.sum(add, lab, range(1, nl + 1))
big = [i + 1 for i in range(nl) if sz[i] * RES * RES > 2500]
print(nl, 'blobs,', len(big), '> 2500 m2')
vis = img.copy() // 2
vis[ex > 0] = (vis[ex > 0] * 0.5 + np.array([90, 90, 90]) * 0.5).astype(np.uint8)
cols = [(40, 200, 255), (255, 120, 60), (60, 255, 120), (255, 60, 200), (200, 255, 60), (60, 120, 255)]
info = []
for k, i in enumerate(big):
    m = lab == i; vis[m] = (vis[m] * 0.3 + np.array(cols[k % len(cols)]) * 0.7).astype(np.uint8)
    ys, xs = np.nonzero(m); cy, cx = int(ys.mean()), int(xs.mean())
    cv2.putText(vis, str(k), (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (255, 255, 255), 4)
    info.append((k, int(sz[i - 1]), round(S0 + cx * RES), round(T1 - cy * RES)))
np.save(SP + 'pave_add_lab.npy', lab); json.dump({'big': big, 'info': info}, open(LSP + 'pave_add.json', 'w'))
cv2.imwrite(SP + 'pave_add.jpg', cv2.resize(vis, None, fx=0.3, fy=0.3, interpolation=cv2.INTER_AREA))
for x in info: print(x)
