"""Warp registered screenshots into a north-up world grid (x east -> right, z south -> down)."""
import json
from common import *
import numpy as np, cv2
U = open(SP + 'uniq.txt').read().split()
REG = json.load(open(SP + 'reg.json'))
def sim_of(name):
    r = REG[name]; return Sim(r['s'], r['th'], r['tx'], r['ty'])
def rectify(name, x0, z0, x1, z1, res=0.25, bottom=2200):
    """returns image (H,W,3) BGR and a validity mask; pixel (i,j) <-> world (x0 + (j+.5)*res, z0 + (i+.5)*res)"""
    img = cv2.imread([u for u in U if name in u][0])
    H, W = int((z1 - z0) / res), int((x1 - x0) / res)
    jj, ii = np.meshgrid(np.arange(W), np.arange(H))
    X = x0 + (jj + 0.5) * res; Z = z0 + (ii + 0.5) * res
    P = sim_of(name).fwd(np.stack([X.ravel(), Z.ravel()], 1)).astype(np.float32)
    mx = P[:, 0].reshape(H, W); my = P[:, 1].reshape(H, W)
    out = cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
    valid = (mx >= 0) & (my >= 330) & (mx < img.shape[1]) & (my < bottom)
    valid &= ~((my < 900) & (mx > 1090)) & ~((my > 1900) & (mx > 1040))
    return out, valid
def w2p(x, z, x0, z0, res): return ((x - x0) / res, (z - z0) / res)
