"""Top-down photo layers: the aerial photograph re-projected onto the model's up-facing surfaces and stored as
orthographic images (one per height band), so that the viewer can paint ground and roofs without seams.

A perspective cast of the aerial leaves gaps wherever the photograph cannot see the surface (the ground beside a
wall under the eave, a lower roof under the upper eave, the patio under the pergola); here those texels are filled
from the nearest visible ones of the SAME layer, which is what lies beside them in reality (lawn beside lawn, seams
beside seams).  Layers: ground (below 2.6 m), lower roofs (2.6 .. 6.2 m), upper roofs (above).

    bake(parts, cam, image) -> [{image, rect: [x0, y0, x1, y1], z: [z0, z1]}]   (files written into out/)
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECT = (-5.0, -10.4, 30.6, 37.8)                    # world x0, y0, x1, y1 covered by the aerial photograph
RES = 40.0                                          # texels per metre
LAYERS = [('ground', -2.0, 2.6), ('roof_lo', 2.6, 6.2), ('roof_hi', 6.2, 20.0)]
TOP_MATS = {'lawn', 'paver_drive', 'bluestone', 'concrete', 'mulch', 'soil', 'roof_shingle', 'roof_seam', 'roof_flat'}
NOT_OCCLUDERS = {'plants', 'trees', 'backdrop'}


def raster(tris, W, H):
    """Highest z of the triangles over every texel centre; -1e9 where there is none.  Row 0 = RECT's y0."""
    Z = np.full((H, W), -1e9, np.float32)
    x0, y0 = RECT[0], RECT[1]
    P = tris.copy()
    P[..., 0] = (P[..., 0] - x0) * RES
    P[..., 1] = (P[..., 1] - y0) * RES
    lo = np.floor(P[..., :2].min(1)).astype(int)
    hi = np.ceil(P[..., :2].max(1)).astype(int)
    for (a, b, c), l, h in zip(P, lo, hi):
        ix0, iy0, ix1, iy1 = max(l[0], 0), max(l[1], 0), min(h[0], W - 1), min(h[1], H - 1)
        if ix0 > ix1 or iy0 > iy1:
            continue
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-9:
            continue
        X, Y = np.meshgrid(np.arange(ix0, ix1 + 1) + 0.5, np.arange(iy0, iy1 + 1) + 0.5)
        w0 = ((b[1] - c[1]) * (X - c[0]) + (c[0] - b[0]) * (Y - c[1])) / den
        w1 = ((c[1] - a[1]) * (X - c[0]) + (a[0] - c[0]) * (Y - c[1])) / den
        w2 = 1 - w0 - w1
        z = np.where((w0 >= -1e-3) & (w1 >= -1e-3) & (w2 >= -1e-3), w0 * a[2] + w1 * b[2] + w2 * c[2], -1e9)
        sub = Z[iy0:iy1 + 1, ix0:ix1 + 1]
        np.maximum(sub, z.astype(np.float32), out=sub)
    return Z


def triangles(parts, top_only):
    out = []
    for p in parts:
        if p.name in NOT_OCCLUDERS:
            continue
        for m in p.geo.meshes():
            if top_only and m.mat not in TOP_MATS:
                continue
            if not top_only and any(k in m.mat for k in ('glass', 'water')):
                continue
            T = np.asarray(m.V, float)[np.asarray(m.F, int)]
            if top_only:
                n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
                ln = np.linalg.norm(n, axis=1)
                T = T[(ln > 1e-12) & (n[:, 2] > 0.3 * np.maximum(ln, 1e-12))]
            out.append(T)
    return np.concatenate(out) if out else np.zeros((0, 3, 3))


def bake(parts, cam, image, prefix='ortho'):
    import cv2
    from scipy import ndimage
    sys.path.insert(0, os.path.join(HERE, 'tools'))
    import cams as CAMS
    W, H = int(round((RECT[2] - RECT[0]) * RES)), int(round((RECT[3] - RECT[1]) * RES))
    full = raster(triangles(parts, False), W, H)
    full = ndimage.maximum_filter(full, size=9)                      # occluders a little fatter: no fringe of roof colour
    top = triangles(parts, True)
    zc = top[..., 2].mean(1)
    src = np.asarray(image.convert('RGB'))
    xs, ys = RECT[0] + (np.arange(W) + 0.5) / RES, RECT[1] + (np.arange(H) + 0.5) / RES
    X, Y = np.meshgrid(xs, ys)
    C = np.asarray(cam['C'], float)
    out = []
    for name, z0, z1 in LAYERS:
        Z = raster(top[(zc >= z0) & (zc < z1)], W, H)
        have = Z > -1e8
        iy, ix = np.nonzero(have)
        x, y, z = X[iy, ix], Y[iy, ix], Z[iy, ix].astype(float)
        occ = np.zeros(len(x), bool)
        for zq in np.arange(z0 + 0.15, 11.0, 0.12):                  # walk toward the camera: is anything in the way?
            t = (zq - z) / (C[2] - z)
            act = (zq > z + 0.14) & ~occ
            qx = np.clip(((x + (C[0] - x) * t - RECT[0]) * RES).astype(int), 0, W - 1)
            qy = np.clip(((y + (C[1] - y) * t - RECT[1]) * RES).astype(int), 0, H - 1)
            occ |= act & (full[qy, qx] > zq + 0.10)
        uv = CAMS.project(cam, np.stack([x, y, z], -1))
        inside = (uv[:, 0] > 2) & (uv[:, 0] < src.shape[1] - 3) & (uv[:, 1] > 2) & (uv[:, 1] < src.shape[0] - 3)
        ok = ~occ & inside
        col = cv2.remap(src, uv[:, 0].astype(np.float32)[None], uv[:, 1].astype(np.float32)[None], cv2.INTER_LINEAR)[0]
        img = np.zeros((H, W, 3), np.uint8)
        valid = np.zeros((H, W), bool)
        img[iy[ok], ix[ok]] = col[ok]
        valid[iy[ok], ix[ok]] = True
        valid = ndimage.binary_erosion(valid, iterations=2)          # drop the mixed texels along every hidden edge
        if valid.sum() > 100:
            idx = ndimage.distance_transform_edt(~valid, return_distances=False, return_indices=True)
            img = img[idx[0], idx[1]]
            soft = cv2.GaussianBlur(img, (0, 0), 1.6)                # the filled texels lose their nearest-neighbour streaks
            wgt = cv2.GaussianBlur((~valid).astype(np.float32), (0, 0), 2.0)[..., None]
            img = (img * (1 - wgt) + soft * wgt).astype(np.uint8)
        from PIL import Image
        fn = '%s_%s.jpg' % (prefix, name)
        Image.fromarray(img[::-1]).save(os.path.join(HERE, 'out', fn), quality=88)
        print('ortho %-8s %d x %d, %.0f %% of its surface seen by the aerial' % (name, W, H, 100.0 * ok.sum() / max(1, len(x))))
        out.append(dict(image=fn, rect=list(RECT), z=[z0, z1]))
    return out
