"""Detect parked aircraft in rectified satellite crops by rotated silhouette template matching."""
import math, json
import numpy as np, cv2
from common import *
from rectify import rectify, sim_of

TYPES = {  # L, span, fuselage width, wing LE root pos (frac of L), root chord, tip chord, LE sweep deg, tailplane span
    'RJ':  (31.7, 26.0, 3.0, 0.40, 4.6, 1.2, 27, 9.0),
    'NB':  (39.0, 35.8, 3.9, 0.36, 6.3, 1.5, 27, 12.5),
    'NBL': (44.5, 35.8, 3.9, 0.38, 6.3, 1.5, 27, 12.5),
    'WB':  (63.5, 60.5, 5.8, 0.34, 10.5, 2.5, 33, 20.0),
    'WBL': (73.9, 64.8, 6.2, 0.35, 11.5, 2.6, 33, 21.5),
}
def planform(t, res, pad=4):
    L, B, F, xle, cr, ct, sw, bh = TYPES[t]
    n = int(math.ceil(max(L, B) / res)) + 2 * pad
    img = np.zeros((n, n), np.float32)
    c = n / 2
    # aircraft frame: nose at (0,0) pointing up (-y), x to the right; centre the aircraft's bbox midpoint
    def P(x, y): return [c + x / res, c + (y - L / 2) / res]
    fus = [P(-F / 2, F * 0.9), P(-F * 0.3, 0.3), P(F * 0.3, 0.3), P(F / 2, F * 0.9), P(F / 2, L * 0.86), P(F * 0.15, L), P(-F * 0.15, L), P(-F / 2, L * 0.86)]
    cv2.fillPoly(img, [np.round(np.array(fus) * 16).astype(np.int32)], 1.0, shift=4)
    yl = xle * L; tan = math.tan(math.radians(sw))
    for s in (-1, 1):
        wing = [P(0, yl), P(s * B / 2, yl + tan * (B / 2)), P(s * B / 2, yl + tan * (B / 2) + ct), P(0, yl + cr)]
        cv2.fillPoly(img, [np.round(np.array(wing) * 16).astype(np.int32)], 1.0, shift=4)
        yh = L * 0.84
        hs = [P(0, yh), P(s * bh / 2, yh + tan * bh / 2 * 1.1), P(s * bh / 2, yh + tan * bh / 2 * 1.1 + 1.2), P(0, L * 0.98)]
        cv2.fillPoly(img, [np.round(np.array(hs) * 16).astype(np.int32)], 1.0, shift=4)
    return img
def rot(img, deg):
    n = img.shape[0]; M = cv2.getRotationMatrix2D((n / 2, n / 2), -deg, 1.0)
    return cv2.warpAffine(img, M, (n, n), flags=cv2.INTER_LINEAR)
def whiteness(bgr):
    b, g, r = [bgr[..., i].astype(np.float32) for i in range(3)]
    mn = np.minimum(np.minimum(r, g), b); mx = np.maximum(np.maximum(r, g), b)
    w = np.clip((mn - 185) / 45, 0, 1) * np.clip(1 - (mx - mn) / 40, 0, 1)
    return w
def detect(name, box, res=0.5, types=('RJ', 'NB', 'NBL', 'WB', 'WBL'), step=3, thr=0.45, mask_poly=None):
    x0, z0, x1, z1 = box
    bgr, valid = rectify(name, x0, z0, x1, z1, res)
    W = whiteness(bgr) * valid
    if mask_poly is not None: W *= (1 - mask_poly)
    dets = []
    for t in types:
        base = planform(t, res)
        n = base.shape[0]
        mu = cv2.boxFilter(W, -1, (n, n), normalize=True, borderType=cv2.BORDER_CONSTANT)
        mu2 = cv2.boxFilter(W * W, -1, (n, n), normalize=True, borderType=cv2.BORDER_CONSTANT)
        sd = np.sqrt(np.maximum(mu2 - mu * mu, 0))
        # matchTemplate result index (y,x) = window top-left; window centre = (y + n/2, x + n/2)
        sdw = sd[n // 2: n // 2 + W.shape[0] - n + 1, n // 2: n // 2 + W.shape[1] - n + 1]
        for a in range(0, 360, step):
            T = rot(base, a)
            R = cv2.matchTemplate(W, T, cv2.TM_CCOEFF_NORMED)
            R[sdw < 0.12] = 0
            # peaks
            k = 9
            mxf = cv2.dilate(R, np.ones((k, k), np.uint8))
            ys, xs = np.nonzero((R >= mxf) & (R > thr))
            for y, x in zip(ys, xs):
                cx = x + T.shape[1] / 2; cy = y + T.shape[0] / 2
                dets.append((float(R[y, x]), t, a, x0 + cx * res, z0 + cy * res))
    # non-max suppression across types/angles: keep best within 15 m
    dets.sort(reverse=True); keep = []
    for d in dets:
        if all(math.hypot(d[3] - k[3], d[4] - k[4]) > 15 for k in keep): keep.append(d)
    return keep, bgr, valid
def nose_tail(d):
    sc, t, a, cx, cz = d; L = TYPES[t][0]
    # heading a: template nose points up (-z) rotated clockwise by a  => heading = a (deg, clockwise from north)
    hx, hz = math.sin(math.radians(a)), -math.cos(math.radians(a))
    return (cx + hx * L / 2, cz + hz * L / 2), (cx - hx * L / 2, cz - hz * L / 2)
