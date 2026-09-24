"""Patch matching of a registered screenshot against NAIP in the world frame.

For a world point P, the screenshot is resampled (through its reg.json similarity) onto a world-aligned template
of half-size `half` m centred on P, and NAIP (exact mapping) onto a search window `half + search`.  Both are
brought to a common effective resolution (the coarser of the two gets no blur, the sharper one is Gaussian-
blurred to NAIP's 0.6 m or to the screenshot's 1/s m/px), converted to gradient magnitude (robust to the
different sensors / sun / season) and compared by normalised cross-correlation (cv2.TM_CCOEFF_NORMED).
Result: delta = where the screenshot content actually sits in NAIP relative to where the registration puts it;
the registration residual is  r = registered position - NAIP position = -delta.
Quality: peak NCC and the ratio of the peak to the best NCC more than 3 m away (uniqueness).
"""
import math
import numpy as np
import cv2

NAIP_RES = 0.6
_BMASK = None


def building_mask(buffer=10.0):
    """world raster (1 m) of SFO Museum buildings (terminal complex, terminals, boarding areas, structures incl.
    garages/AirTrain) dilated by `buffer` m: roofs are displaced by relief (not true orthophotos) differently in NAIP
    and in the Google imagery, so they are excluded from matching."""
    global _BMASK
    if _BMASK is None:
        import json, os
        from common import ROOT
        D = json.load(open(os.path.join(ROOT, 'data', 'sfo_airport.json')))
        x0, z0, x1, z1 = -2800, -2500, 2300, 2700
        M = np.zeros((z1 - z0, x1 - x0), np.uint8)
        polys = [p for p in D['terminalComplex']]
        for k in ('terminals', 'boardingAreas', 'structures'):
            for f in D[k]:
                if f.get('kind') == 'rail': continue
                polys += f['polys']
        for poly in polys:
            ring = np.array(poly[0], float)
            cv2.fillPoly(M, [np.round(ring - [x0, z0]).astype(np.int32)], 1)
        r = int(buffer)
        M = cv2.dilate(M, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
        _BMASK = (M, x0, z0)
    return _BMASK


def sample_bmask(X, Z):
    M, x0, z0 = building_mask()
    c = np.clip(np.floor(X - x0).astype(int), 0, M.shape[1] - 1); r = np.clip(np.floor(Z - z0).astype(int), 0, M.shape[0] - 1)
    return M[r, c] > 0


def bright_blobs(g, res, size=4.0, thr=None):
    """large bright objects (aircraft, white roofs, vehicles): survive a grey opening with a `size` m disk;
    paint markings (<= 3 m wide) do not.  Dilated by 3 m (shadows / wings)."""
    k = max(3, int(round(size / res)) | 1)
    op = cv2.morphologyEx(g, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    t = thr if thr is not None else np.percentile(g, 50) + 45
    m = (op > t).astype(np.uint8)
    d = max(3, int(round(3.0 / res)) | 1)
    return cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (d, d))) > 0


def grad(g, sig):
    if sig > 0.05: g = cv2.GaussianBlur(g, (0, 0), sig)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    return np.sqrt(gx * gx + gy * gy)


def match_point(S, img, mask, sim, P, half=24.0, search=15.0, res=None, min_valid=0.90, mode='grad', min_used=0.5,
                use_masks=True):
    from screens import rectify
    scr_res = 1.0 / sim.s
    if res is None: res = min(max(0.25, scr_res), 3.2)
    nt = int(round(2 * half / res)); ns = int(round(2 * (half + search) / res))
    ct = (np.arange(nt) + 0.5) * res - half; cs = (np.arange(ns) + 0.5) * res - (half + search)
    Xt, Zt = np.meshgrid(P[0] + ct, P[1] + ct); Xs, Zs = np.meshgrid(P[0] + cs, P[1] + cs)
    T, val = rectify(img, mask, sim, Xt, Zt)
    if val.mean() < min_valid: return None
    N = S(Xs, Zs)
    if (N == 0).mean() > 0.01: return None
    W = val.copy()
    if use_masks:
        k0 = int(round(search / res)); Nc = N[k0:k0 + nt, k0:k0 + nt]
        W &= ~sample_bmask(Xt, Zt) & ~bright_blobs(T, res) & ~bright_blobs(Nc, res)
    used = float(W.mean())
    if used < min_used: return None
    eff = max(scr_res, NAIP_RES)   # common effective resolution (m)
    sT = 0.5 * math.sqrt(max(eff ** 2 - scr_res ** 2, 0)) / res
    sN = 0.5 * math.sqrt(max(eff ** 2 - NAIP_RES ** 2, 0)) / res
    base = 0.5 * 1.0   # light common smoothing (px) before the gradient
    if mode == 'grad':
        Tg, Ng = grad(T, math.hypot(sT, base)), grad(N, math.hypot(sN, base))
    else:
        Tg = cv2.GaussianBlur(T, (0, 0), math.hypot(sT, base)); Ng = cv2.GaussianBlur(N, (0, 0), math.hypot(sN, base))
    if Tg.std() < 1e-3: return None
    R = cv2.matchTemplate(Ng, Tg, cv2.TM_CCOEFF_NORMED, mask=W.astype(np.float32))
    R = np.nan_to_num(R, nan=-1, posinf=-1, neginf=-1)
    _, pk, _, loc = cv2.minMaxLoc(R)
    j, i = loc
    # sub-pixel (separable quadratic)
    dx = dy = 0.0
    if 0 < j < R.shape[1] - 1:
        a, b, c = R[i, j - 1], R[i, j], R[i, j + 1]; den = a - 2 * b + c
        dx = 0.5 * (a - c) / den if den < 0 else 0.0
    if 0 < i < R.shape[0] - 1:
        a, b, c = R[i - 1, j], R[i, j], R[i + 1, j]; den = a - 2 * b + c
        dy = 0.5 * (a - c) / den if den < 0 else 0.0
    off = (R.shape[1] - 1) / 2.0
    delta = np.array([(j + dx - off) * res, (i + dy - off) * res])
    # uniqueness: best NCC outside max(3 m, 2.5 px)
    yy, xx = np.mgrid[0:R.shape[0], 0:R.shape[1]]
    far = np.hypot((xx - j) * res, (yy - i) * res) > max(3.0, 2.5 * res)
    second = float(R[far].max()) if far.any() else -1.0
    edge = min(j, i, R.shape[1] - 1 - j, R.shape[0] - 1 - i) * res < 1.0   # peak on the search border -> unreliable
    return dict(delta=delta.tolist(), resid=(-delta).tolist(), ncc=float(pk), second=second, res=res, edge=bool(edge), used=used)
