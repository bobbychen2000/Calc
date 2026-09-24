"""Mosaic of all registered screenshots in the airport grid frame (best resolution wins), with stands + bridges."""
import json, math
import numpy as np, cv2
from common import *
from stview import st_view, annotate, st_px, w2st, st2w
from rectify import REG
import stand_defs
from stands import draw_stands
from export_stands import door_st
def mosaic(box, res, names=None):
    s0, t0, s1, t1 = box
    W, H = int((s1 - s0) / res), int((t1 - t0) / res)
    out = np.zeros((H, W, 3), np.uint8)
    order = sorted([n for n in REG if (names is None or n in names)], key=lambda n: REG[n]['s'])
    for n in order:
        if n == '8b334c52': continue
        im = st_view(n, s0, t0, s1, t1, res)
        # valid region: inside the screenshot map area (exclude UI bands)
        img = cv2.imread([u for u in open(SP + 'uniq.txt').read().split() if n in u][0])
        jj, ii = np.meshgrid(np.arange(W), np.arange(H))
        S = s0 + (jj + 0.5) * res; T = t1 - (ii + 0.5) * res
        e, nn = st2w(S, T) if False else (None, None)
        from stview import V, UV
        ex = S * V[0] + T * UV[0]; en = S * V[1] + T * UV[1]
        from rectify import sim_of
        P = sim_of(n).fwd(np.stack([ex.ravel(), (-en).ravel()], 1))
        mx = P[:, 0].reshape(H, W); my = P[:, 1].reshape(H, W)
        bottom = 2150 if n in ('0af09b78', '35809e3e', '4637f855', 'bc91df95') else 2230
        valid = (mx > 5) & (mx < 1285) & (my > 340) & (my < bottom) & ~((my < 900) & (mx > 1080)) & ~((my > 1880) & (mx > 1030))
        out[valid] = im[valid]
    return out
if __name__ == '__main__':
    box = (-1480, -1400, -230, -190); res = 0.6
    m = mosaic(box, res)
    m = annotate(m, *box, res, grid=50, lab=100, gates=False)
    stands = stand_defs.STANDS
    m = draw_stands(m, *box, res, stands, env=False)
    # bridges: attach -> door
    data = json.load(open(ROOT + '/data/sfo_stands.json')); S = {s['name']: s for s in stands}
    for st in data['stands']:
        for b in st['bridges']:
            a = w2st(*b['attach']); d = door_st(S[st['name']], b['door'])
            cv2.line(m, st_px(*a, box[0], box[3], res), st_px(*d, box[0], box[3], res), (0, 200, 255), 2, cv2.LINE_AA)
    cv2.imwrite(SP + 'mosaic_stands.png', m)
    cv2.imwrite(SP + 'mosaic_stands_small.jpg', cv2.resize(m, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(m.shape)
