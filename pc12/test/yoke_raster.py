"""
A small numpy rasteriser for inspecting the yoke meshes (and rendering them through the photo overlays' fitted
cameras): z-buffered triangles with per-corner normals interpolated per pixel, shaded as a studio (key / fill lights,
a soft environment with two softbox reflections) or as ZEBRA stripes (reflection lines: a curvature discontinuity
breaks them, a crease kinks them -- the classic class-A surface check).

    img = render(meshes, cam, W, H, mode='studio')      meshes: [(V (n, 3), F (m, 3), N (m, 3, 3) corner normals,
                                                         rgb base, gloss)], cam(X) -> pixel (n, 2) + depth
"""
from __future__ import annotations

import numpy as np


def look_at(eye, tgt, up=(0.0, 0.0, 1.0), fov=30.0, W=800, H=600):
    """Pinhole camera: returns cam(X) -> (px (n, 2), depth (n,)), and the eye."""
    eye, tgt, up = (np.asarray(v, float) for v in (eye, tgt, up))
    f = tgt - eye
    f /= np.linalg.norm(f)
    r = np.cross(f, up)
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    foc = 0.5 * H / np.tan(np.radians(0.5 * fov))

    def cam(X):
        d = np.atleast_2d(X) - eye
        z = d @ f
        return np.c_[0.5 * W + foc * (d @ r) / z, 0.5 * H - foc * (d @ u) / z], z
    cam.eye = eye
    return cam


def raster(tris_px, tris_z, W, H):
    """Visibility: tris_px (m, 3, 2) pixel coords, tris_z (m, 3) depths -> (tri id (H, W) or -1, barycentrics (H, W, 3))."""
    m = len(tris_px)
    good = np.isfinite(tris_px).all((1, 2)) & (tris_z.min(1) > 1e-6) & (np.abs(tris_px).max((1, 2)) < 1e6)
    tris_px = np.where(good[:, None, None], tris_px, 0.0)
    zbuf = np.full(H * W, np.inf)
    tid = np.full(H * W, -1, np.int64)
    bary = np.zeros((H * W, 3))
    lo = np.floor(tris_px.min(1)).astype(int)
    hi = np.ceil(tris_px.max(1)).astype(int)
    lo = np.maximum(lo, 0)
    hi = np.minimum(hi, [W - 1, H - 1])
    ext = np.maximum(hi - lo + 1, 0).max(1)
    ok = (ext > 0) & good
    for K in (2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048):
        sel = np.nonzero(ok & (ext <= K) & (ext > K // 2 if K > 2 else True))[0]
        if not len(sel):
            continue
        for c0 in range(0, len(sel), max(1, 4_000_000 // (K * K))):
            s = sel[c0:c0 + max(1, 4_000_000 // (K * K))]
            gx, gy = np.meshgrid(np.arange(K), np.arange(K))
            X = lo[s, 0][:, None, None] + gx[None] + 0.5
            Y = lo[s, 1][:, None, None] + gy[None] + 0.5
            P = tris_px[s]
            x0, y0 = P[:, 0, 0][:, None, None], P[:, 0, 1][:, None, None]
            x1, y1 = P[:, 1, 0][:, None, None], P[:, 1, 1][:, None, None]
            x2, y2 = P[:, 2, 0][:, None, None], P[:, 2, 1][:, None, None]
            den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
            den = np.where(np.abs(den) < 1e-12, 1e-12, den)
            w0 = ((y1 - y2) * (X - x2) + (x2 - x1) * (Y - y2)) / den
            w1 = ((y2 - y0) * (X - x2) + (x0 - x2) * (Y - y2)) / den
            w2 = 1 - w0 - w1
            inside = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9) & (X < W) & (Y < H)
            # perspective-correct depth: interpolate 1/z
            iz = (w0 / tris_z[s, 0][:, None, None] + w1 / tris_z[s, 1][:, None, None]
                  + w2 / tris_z[s, 2][:, None, None])
            z = 1.0 / np.maximum(iz, 1e-12)
            ii = np.nonzero(inside)
            if not len(ii[0]):
                continue
            pix = (Y[ii].astype(int)) * W + X[ii].astype(int)
            zz = z[ii]
            order = np.lexsort((zz, pix))
            pix, zz = pix[order], zz[order]
            first = np.r_[True, pix[1:] != pix[:-1]]
            pix, zz = pix[first], zz[first]
            idx = tuple(a[order][first] for a in ii)
            better = zz < zbuf[pix]
            pix, zz = pix[better], zz[better]
            idx = tuple(a[better] for a in idx)
            zbuf[pix] = zz
            tid[pix] = s[idx[0]]
            # perspective-correct barycentrics
            b0 = w0[idx] / tris_z[s[idx[0]], 0]
            b1 = w1[idx] / tris_z[s[idx[0]], 1]
            b2 = w2[idx] / tris_z[s[idx[0]], 2]
            sb = b0 + b1 + b2
            bary[pix] = np.c_[b0 / sb, b1 / sb, b2 / sb]
    return tid.reshape(H, W), bary.reshape(H, W, 3), zbuf.reshape(H, W)


zebra_dir = (0.0, 1.0, 0.0)


def shade(N, view, base, gloss, mode="studio", P=None, stripe=4.0):
    """N (k, 3) unit normals, view (k, 3) unit directions from the surface to the eye, base (k, 3), gloss (k,) 0..1."""
    N = N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)
    R = 2 * np.sum(N * view, 1)[:, None] * N - view
    if mode == "zebra":
        # reflection stripes of a vertical-stripe environment (azimuth of the reflected ray)
        d = np.asarray(zebra_dir, float)
        d = d / np.linalg.norm(d)
        el = np.arcsin(np.clip(R @ d, -1, 1))
        v = 0.5 + 0.5 * np.tanh(6.0 * np.sin(stripe * 6 * el))
        return np.repeat((0.12 + 0.8 * v)[:, None], 3, 1)
    keys = [(np.array([0.45, -0.55, 0.70]), 0.9), (np.array([-0.6, 0.4, 0.5]), 0.45), (np.array([0.8, 0.5, -0.2]), 0.25)]
    diff = np.full(len(N), 0.18)
    for L, c in keys:
        L = L / np.linalg.norm(L)
        diff = diff + c * np.maximum(N @ L, 0.0)
    # environment: soft sky gradient + two softbox stripes in reflection
    env = 0.25 + 0.35 * np.clip(R[:, 2], -1, 1)
    for d, w in ((np.array([0.5, -0.6, 0.62]), 0.18), (np.array([-0.7, 0.3, 0.64]), 0.22)):
        d = d / np.linalg.norm(d)
        env = env + 2.2 * np.exp(-(1 - np.clip(R @ d, -1, 1)) / (w * w * 0.25 + 1e-3 * (1 - gloss)[:]) )
    fres = 0.04 + 0.96 * (1 - np.clip(np.sum(N * view, 1), 0, 1)) ** 5
    spec = (0.25 + 0.75 * gloss)[:, None] * (fres[:, None] * 0.8 + 0.06) * env[:, None]
    return np.clip(base * diff[:, None] + spec, 0, 1)


def render(meshes, cam, W, H, mode="studio", bg=(0.93, 0.94, 0.95), wire=False):
    """meshes: [(V, F, Nc (m, 3, 3), base rgb, gloss)] -> uint8 image (H, W, 3)."""
    allpx, allz, allN, allB, allG, allP = [], [], [], [], [], []
    for V, F, Nc, base, gloss in meshes:
        if len(F) == 0:
            continue
        px, z = cam(V)
        allpx.append(px[F])
        allz.append(z[F])
        allN.append(Nc)
        allB.append(np.repeat(np.asarray(base, float)[None], len(F), 0))
        allG.append(np.full(len(F), float(gloss)))
        allP.append(V[F])
    tp = np.concatenate(allpx)
    tz = np.concatenate(allz)
    TN = np.concatenate(allN)
    TB = np.concatenate(allB)
    TG = np.concatenate(allG)
    TP = np.concatenate(allP)
    tid, bary, _ = raster(tp, tz, W, H)
    img = np.empty((H, W, 3))
    img[:] = bg
    m = tid >= 0
    t = tid[m]
    b = bary[m]
    N = np.einsum("kj,kjd->kd", b, TN[t])
    P = np.einsum("kj,kjd->kd", b, TP[t])
    view = cam.eye - P
    view /= np.linalg.norm(view, axis=1, keepdims=True)
    img[m] = shade(N, view, TB[t], TG[t], mode)
    if wire:
        # distance (px) to the nearest triangle edge from the barycentrics and the edges' pixel heights
        P2 = tp[t]
        e = [np.linalg.norm(P2[:, (k + 2) % 3] - P2[:, (k + 1) % 3], axis=1) for k in range(3)]
        A2 = np.abs((P2[:, 1, 0] - P2[:, 0, 0]) * (P2[:, 2, 1] - P2[:, 0, 1])
                    - (P2[:, 2, 0] - P2[:, 0, 0]) * (P2[:, 1, 1] - P2[:, 0, 1]))
        dpx = np.min(np.stack([b[:, k] * A2 / np.maximum(e[k], 1e-9) for k in range(3)], 1), 1)
        sub = img[m]
        sub[dpx < 0.6] = sub[dpx < 0.6] * 0.35 + np.array([0.0, 0.25, 0.6]) * 0.65
        img[m] = sub
    return (np.clip(img, 0, 1) ** (1 / 1.0) * 255).astype(np.uint8)
