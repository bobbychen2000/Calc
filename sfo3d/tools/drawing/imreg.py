"""Residual registration of each Google screenshot against NAIP (public domain, independently georeferenced).

Why: the screenshots were registered (tools/sat/work/reg.json) by chamfer matching against the SFO Museum outlines, so
their georeference is neither independent of the data under test nor as good as NAIP's. The review of the first drawing
run found Google - NAIP offsets of ~2 m (buildings, pavement) and up to 5-10 m for single screenshots. This step measures,
per screenshot, the translation c such that a ground feature at world p (NAIP) shows at p + c in the screenshot as
registered; background.GoogleScreens then reads pixel(p + c), i.e. the Google numbers share NAIP's georeference.

Method: the screenshot's footprint is cut into square patches; each patch is resampled from that ONE screenshot and
from NAIP to the same north-up world grid (0.5 m/px, or the screenshot's own resolution when coarser), both converted to
colour-gradient magnitude (Lab, Gaussian sigma 1 px); building footprints (+8 m, roofs lean by relief displacement) and
the Google UI mask are zeroed in both; the NAIP gradient patch is searched +-15 m with normalised cross-correlation
(sub-pixel by a parabola through the peak). Patches with NCC < 0.35 or a flat peak are rejected. Per screenshot: median
shift of the accepted patches, MAD spread, and a use flag (>= 3 patches, MAD <= 1.5 m); a large spread means rotation /
scale error that a translation cannot fix and is reported as such.
Output: out/draw/google_vs_naip.json (local), keyed to the sha of reg.json and the NAIP files it was made from.
Run:  python3 imreg.py        (needs NAIP in refs/cache/naip/ and the screenshots in tools/sat/screens/)
"""
import json, math, os, sys, time
import numpy as np
import cv2
from shapely.geometry import Point
from common import OUT, ROOT, GF, _sha, buildings, poly_rings
import background

SEARCH = 15.0; NCC_MIN = 0.35


def raster_one(src, k, box, res):
    """(BGR, valid) of ONE image k of source src on the north-up world grid box = (x0, z0, x1, z1)"""
    x0, z0, x1, z1 = box
    W, H = int(round((x1 - x0) / res)), int(round((z1 - z0) / res))
    jj, ii = np.meshgrid(np.arange(W, dtype=np.float64), np.arange(H, dtype=np.float64))
    X = x0 + (jj + 0.5) * res; Z = z0 + (ii + 0.5) * res
    mx, my = src.pixel(k, X.ravel(), Z.ravel()); mx = mx.reshape(H, W).astype(np.float32); my = my.reshape(H, W).astype(np.float32)
    v = src.valid(k, mx, my); im = src.image(k); r = src.gsd(k)
    if res > 1.5 * r:
        f = r / res * 1.5; small = cv2.resize(im, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
        out = cv2.remap(small, mx * f, my * f, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    else: out = cv2.remap(im, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    return out, v


def grad(img, valid, bmask):
    L = cv2.cvtColor(img, cv2.COLOR_BGR2Lab).astype(np.float32)
    L = cv2.GaussianBlur(L, (0, 0), 1.0)
    gx = cv2.Sobel(L, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(L, cv2.CV_32F, 0, 1, ksize=3)
    g = np.sqrt((gx ** 2 + gy ** 2).sum(2))
    bad = ~valid | bmask
    bad = cv2.dilate(bad.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    g[bad] = 0
    return np.log1p(g)


def building_mask(box, res):
    x0, z0, x1, z1 = box; W, H = int(round((x1 - x0) / res)), int(round((z1 - z0) / res))
    m = np.zeros((H, W), np.uint8)
    for b in buildings():
        if b.get('notBuilt') or b['kind'] == 'rail': continue
        p = poly_rings(b['rings']).buffer(8.0)
        bx = p.bounds
        if bx[2] < x0 or bx[0] > x1 or bx[3] < z0 or bx[1] > z1: continue
        for g in (p.geoms if hasattr(p, 'geoms') else [p]):
            c = np.asarray(g.exterior.coords); P = np.round(((c - [x0, z0]) / res - 0.5) * 16).astype(np.int32)
            cv2.fillPoly(m, [P], 1, cv2.LINE_8, 4)
    return m > 0


def sub_peak(R, i, j):
    def par(a, b, c):
        d = a - 2 * b + c
        return 0.0 if abs(d) < 1e-9 else 0.5 * (a - c) / d
    di = par(R[i - 1, j], R[i, j], R[i + 1, j]) if 0 < i < R.shape[0] - 1 else 0.0
    dj = par(R[i, j - 1], R[i, j], R[i, j + 1]) if 0 < j < R.shape[1] - 1 else 0.0
    return i + di, j + dj


def patch_shift(G, N, k, box, res):
    """translation c (world x, z) of screenshot k against NAIP over patch box, NCC, sharpness"""
    x0, z0, x1, z1 = box; S = SEARCH
    big = (x0 - S, z0 - S, x1 + S, z1 + S)
    gi, gv = raster_one(G, k, box, res)
    if gv.mean() < 0.8: return None
    ni, nv, _ = N.raster(*big, res)
    if nv.mean() < 0.95: return None
    tg = grad(gi, gv, building_mask(box, res)); ng = grad(ni, nv, building_mask(big, res))
    if (tg > 0).mean() < 0.4 or tg.std() < 1e-3: return None
    R = cv2.matchTemplate(ng, tg, cv2.TM_CCOEFF_NORMED)
    i, j = np.unravel_index(np.argmax(R), R.shape); peak = float(R[i, j])
    # sharpness: best value outside a 3 m radius around the peak
    yy, xx = np.mgrid[0:R.shape[0], 0:R.shape[1]]; far = np.hypot(yy - i, xx - j) * res > 3.0
    second = float(R[far].max()) if far.any() else 0.0
    fi, fj = sub_peak(R, i, j)
    cx = S - fj * res; cz = S - fi * res
    edge = min(i, j, R.shape[0] - 1 - i, R.shape[1] - 1 - j) * res < 0.5
    return dict(box=[round(v, 1) for v in box], shift=[round(cx, 2), round(cz, 2)], ncc=round(peak, 3), second=round(second, 3), edge=bool(edge))


def run():
    srcs = background.sources()
    if 'naip' not in srcs or 'google' not in srcs: print('  imreg: needs NAIP and the Google screenshots - skipped'); return None
    N = srcs['naip']; G = srcs['google'].uncorrected()
    t0 = time.time(); out = {}
    for k in G.images():
        gsd = G.gsd(k); res = max(0.5, gsd); P = max(90.0, 140 * res)
        # footprint of the valid screenshot area in world (uncorrected registration)
        im = G.image(k); h, w = im.shape[:2]
        jj, ii = np.meshgrid(np.arange(0, w, 16.0), np.arange(0, h, 16.0))
        v = G.valid(k, jj, ii)
        W = G.sim[k].inv(np.stack([jj[v], ii[v]], -1))
        if not len(W): continue
        x0, z0 = W.min(0); x1, z1 = W.max(0)
        pts = []
        cent = [(xc, zc) for zc in np.arange(z0 + P / 2, z1 - P / 2 + 1e-6, P * 0.75) for xc in np.arange(x0 + P / 2, x1 - P / 2 + 1e-6, P * 0.75)]
        # inside the screenshot's valid area only; at most 40 patches, evenly spread
        from shapely.geometry import MultiPoint
        hull = MultiPoint([tuple(q) for q in W[::7]]).convex_hull.buffer(-P / 2)
        cent = [c for c in cent if hull.contains(Point(c))]
        if len(cent) > 40: cent = [cent[i] for i in np.linspace(0, len(cent) - 1, 40).round().astype(int)]
        for xc, zc in cent:
            r = patch_shift(G, N, k, (xc - P / 2, zc - P / 2, xc + P / 2, zc + P / 2), res)
            if r: pts.append(r)
        good = [p for p in pts if p['ncc'] >= NCC_MIN and p['ncc'] - p['second'] >= 0.05 and not p['edge']]
        rec = dict(gsd=round(gsd, 3), res=res, patch=P, patches=pts, accepted=len(good), tested=len(pts))
        if good:
            A = np.array([p['shift'] for p in good]); med = np.median(A, 0); mad = np.median(np.hypot(*(A - med).T))
            rec.update(shift=[round(float(med[0]), 2), round(float(med[1]), 2)], mad=round(float(mad), 2), ncc=round(float(np.median([p['ncc'] for p in good])), 3),
                       spread=[round(float(A[:, 0].max() - A[:, 0].min()), 2), round(float(A[:, 1].max() - A[:, 1].min()), 2)])
            rec['use'] = bool(len(good) >= 3 and mad <= 1.5) or bool(len(good) >= 2 and mad <= 0.6)
            rec['note'] = ('ok' if rec['use'] else f'not applied: {len(good)} patch(es), MAD {mad:.1f} m') + (' - spread > 3 m: rotation/scale error beyond a translation' if max(rec['spread']) > 3 and len(good) >= 3 else '')
        else: rec.update(use=False, note='no reliable patch (NCC < %.2f or flat peak)' % NCC_MIN)
        out[k] = rec
        print(f'  {k} gsd {gsd:.2f}: {len(good)}/{len(pts)} patches, shift {rec.get("shift")} MAD {rec.get("mad")} NCC {rec.get("ncc")} use={rec["use"]} ({time.time() - t0:.0f} s)', flush=True)
    res = dict(method=__doc__.split('\n\n')[2].strip() if __doc__.count('\n\n') >= 2 else '', frame=GF.FRAME_ID, reg_sha=_sha(background.REGF), naip=N.provenance(), search_m=SEARCH, ncc_min=NCC_MIN,
               generated=time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime()), images=out)
    json.dump(res, open(os.path.join(OUT, 'google_vs_naip.json'), 'w'), indent=1)
    return res


if __name__ == '__main__':
    run()
