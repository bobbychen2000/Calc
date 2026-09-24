"""Refine an observed aircraft (nose, heading, class) by local template matching on the whiteness map (ST frame)."""
import math
import numpy as np, cv2
from common import *
from stview import st_view, st_px
from detect import whiteness
from stands import planform_st, CLS
def render_plan(nose, hdg, cls, s0, t1, res, shape):
    m = np.zeros(shape, np.float32)
    for poly in planform_st(nose, hdg, cls):
        pts = np.array([[(s - s0) / res, (t1 - t) / res] for s, t in poly])
        cv2.fillPoly(m, [np.round(pts * 8).astype(np.int32)], 1.0, shift=3)
    return m
def refine(img, nose, hdg, classes=('B', 'C', 'CL', 'D', 'E', 'EL', 'F'), dpos=4.0, dh=8.0, res=0.25, pad=45):
    L = max(CLS[c][0] for c in classes)
    s0, s1 = nose[0] - L - pad, nose[0] + L + pad
    t0, t1 = nose[1] - L - pad, nose[1] + L + pad
    im = st_view(img, s0, t0, s1, t1, res)
    W = whiteness(im); valid = (im.sum(2) > 0)
    W = cv2.GaussianBlur(W, (0, 0), 0.8)
    best = (-9,)
    def score(n, h, c):
        T = render_plan(n, h, c, s0, t1, res, W.shape)
        ring = cv2.dilate(T, np.ones((9, 9), np.uint8)) - T  # background band around the silhouette
        if T.sum() < 10: return -9
        inside = (W * T).sum() / T.sum(); outside = (W * ring).sum() / max(ring.sum(), 1)
        return inside - outside
    for c in classes:
        for dhh in np.arange(-dh, dh + 1e-6, 2.0):
            for ds in np.arange(-dpos, dpos + 1e-6, 1.0):
                for dt in np.arange(-dpos, dpos + 1e-6, 1.0):
                    n = (nose[0] + ds, nose[1] + dt); h = hdg + dhh
                    sc = score(n, h, c)
                    if sc > best[0]: best = (sc, n, h, c)
    # fine pass around best
    sc0, n0, h0, c0 = best
    for dhh in np.arange(-1.5, 1.51, 0.5):
        for ds in np.arange(-1.0, 1.01, 0.25):
            for dt in np.arange(-1.0, 1.01, 0.25):
                n = (n0[0] + ds, n0[1] + dt); h = h0 + dhh
                sc = score(n, h, c0)
                if sc > best[0]: best = (sc, n, h, c0)
    return {'score': round(best[0], 3), 'nose': (round(best[1][0], 2), round(best[1][1], 2)), 'hdg': round(best[2] % 360, 2), 'cls': best[3]}
