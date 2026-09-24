"""Detect the red equipment-staging boxes painted on the ramps in each registered screenshot -> world positions."""
import json, math
import numpy as np, cv2
from scipy import ndimage as ndi
from common import *
from stview import st_view, st2w, w2st, V, UV
from rectify import REG, sim_of
RES = 0.25
def valid_region(n, s0, t0, s1, t1, res):
    W, H = int((s1 - s0) / res), int((t1 - t0) / res)
    jj, ii = np.meshgrid(np.arange(W), np.arange(H))
    S = s0 + (jj + 0.5) * res; T = t1 - (ii + 0.5) * res
    ex = S * V[0] + T * UV[0]; en = S * V[1] + T * UV[1]
    P = sim_of(n).fwd(np.stack([ex.ravel(), (-en).ravel()], 1)); mx = P[:, 0].reshape(H, W); my = P[:, 1].reshape(H, W)
    bottom = 2150 if n in ('0af09b78', '35809e3e', '4637f855', 'bc91df95') else 2230
    return (mx > 8) & (mx < 1282) & (my > 345) & (my < bottom) & ~((my < 905) & (mx > 1075)) & ~((my > 1875) & (mx > 1025))
def detect(n, box):
    s0, t0, s1, t1 = box
    im = st_view(n, s0, t0, s1, t1, RES).astype(np.int32)
    v = valid_region(n, s0, t0, s1, t1, RES)
    B, G_, R = im[..., 0], im[..., 1], im[..., 2]
    red = (R - (G_ + B) / 2 > 28) & (R > 120) & (R - G_ > 22) & v
    red = ndi.binary_closing(red, iterations=2)
    lab, nl = ndi.label(red)
    out = []
    for i, sl in enumerate(ndi.find_objects(lab)):
        m = lab[sl] == i + 1; a = m.sum() * RES * RES
        h, w = (sl[0].stop - sl[0].start) * RES, (sl[1].stop - sl[1].start) * RES
        if not (2.8 < h < 8 and 2.8 < w < 8 and a > 3.0): continue
        ys, xs = np.nonzero(m)
        cnt = np.stack([xs + sl[1].start, ys + sl[0].start], 1).astype(np.float32)
        (cx, cy), (rw, rh), ang = cv2.minAreaRect(cnt)
        if not (2.6 < rw * RES < 7.5 and 2.6 < rh * RES < 7.5): continue
        fill = a / (rw * rh * RES * RES + 1e-6)
        s = s0 + (cx + 0.5) * RES; t = t1 - (cy + 0.5) * RES
        out.append({'s': s, 't': t, 'w': rw * RES, 'h': rh * RES, 'ang': float(ang), 'fill': float(fill), 'img': n})
    return out
if __name__ == '__main__':
    box = (-1480, -1400, -230, -190)
    allb = []
    for n in sorted(REG, key=lambda k: -REG[k]['s']):   # best resolution first
        if REG[n]['s'] < 1.7: continue
        bs = detect(n, box)
        for b in bs:
            if any(math.hypot(b['s'] - o['s'], b['t'] - o['t']) < 4.0 for o in allb): continue
            allb.append(b)
        print(n, len(bs), 'total', len(allb))
    res = []
    for b in allb:
        x, z = st2w(b['s'], b['t'])
        res.append([round(x, 2), round(z, 2), round((b['w'] + b['h']) / 2, 2), round(b['ang'] % 90, 1)])
    json.dump({'frame': GF.FRAME_ID, 'boxes': res}, open(SP + 'redboxes.json', 'w'))   # current world frame (a bare list = legacy frame)
    print(len(res), 'boxes; size median', np.median([r[2] for r in res]))
