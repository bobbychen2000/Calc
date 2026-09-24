"""Small numpy triangle rasteriser for texture-space baking (no GPU).

raster(tri, W, H, depth=None) -> (tid, bary)
  tri   (n, 3, 2) float pixel coordinates (x right, y down; pixel centres at i + 0.5)
  depth optional (n, 3) per-vertex depth: nearest (smallest) wins; without it the last triangle wins
  tid   (H, W) int32 triangle index covering the pixel centre, -1 where empty
  bary  (H, W, 3) float32 barycentric weights of the pixel centre in that triangle
Pixel centres exactly on a shared edge belong to both triangles (inclusive test): no cracks between neighbours.
"""
import numpy as np


def raster(tri, W, H, depth=None, counts=False):
    tid = np.full((H, W), -1, np.int32)
    bary = np.zeros((H, W, 3), np.float32)
    zbuf = np.full((H, W), np.inf, np.float32) if depth is not None else None
    n = len(tri)
    cnt = np.zeros(n, np.int32) if counts else None
    x0 = np.clip(np.floor(tri[:, :, 0].min(1) - 0.5).astype(np.int64), 0, W - 1)
    x1 = np.clip(np.ceil(tri[:, :, 0].max(1) - 0.5).astype(np.int64), 0, W - 1)
    y0 = np.clip(np.floor(tri[:, :, 1].min(1) - 0.5).astype(np.int64), 0, H - 1)
    y1 = np.clip(np.ceil(tri[:, :, 1].max(1) - 0.5).astype(np.int64), 0, H - 1)
    for i in range(n):
        if x1[i] < x0[i] or y1[i] < y0[i]: continue
        (ax, ay), (bx, by), (cx, cy) = tri[i]
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-12: continue
        xs = np.arange(x0[i], x1[i] + 1) + 0.5; ys = np.arange(y0[i], y1[i] + 1) + 0.5
        X, Y = np.meshgrid(xs, ys)
        w0 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / den
        w1 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / den
        w2 = 1 - w0 - w1
        e = -1e-6
        m = (w0 >= e) & (w1 >= e) & (w2 >= e)
        if not m.any(): continue
        sl = (slice(y0[i], y1[i] + 1), slice(x0[i], x1[i] + 1))
        if zbuf is not None:
            z = w0 * depth[i, 0] + w1 * depth[i, 1] + w2 * depth[i, 2]
            m &= z < zbuf[sl]
            zbuf[sl] = np.where(m, z, zbuf[sl])
        if counts: cnt[i] = int(m.sum())
        tid[sl] = np.where(m, i, tid[sl])
        B = bary[sl]
        B[..., 0] = np.where(m, w0, B[..., 0]); B[..., 1] = np.where(m, w1, B[..., 1]); B[..., 2] = np.where(m, w2, B[..., 2])
    if counts: return tid, bary, cnt
    return tid, bary


def dilate_fill(img, valid, radius=16):
    """Fill invalid pixels near valid ones with the nearest valid value (for mip-map / filtering bleed at chart edges).
    img (H, W, C) float; valid (H, W) bool. Returns (img, valid)."""
    from scipy import ndimage
    if valid.all(): return img, valid
    d, (iy, ix) = ndimage.distance_transform_edt(~valid, return_indices=True)
    fill = (d <= radius) & ~valid
    out = img.copy(); out[fill] = img[iy[fill], ix[fill]]
    return out, valid | fill


def sample_bilinear(img, u, v, wrap=True):
    """img (H, W, C) float; u, v arrays in [0, 1) texture coordinates (v = 0 is the first row). Returns (..., C)."""
    H, W = img.shape[:2]
    x = u * W - 0.5; y = v * H - 0.5
    x0 = np.floor(x).astype(np.int64); y0 = np.floor(y).astype(np.int64); fx = (x - x0)[..., None]; fy = (y - y0)[..., None]
    if wrap:
        X0 = x0 % W; X1 = (x0 + 1) % W; Y0 = y0 % H; Y1 = (y0 + 1) % H
    else:
        X0 = np.clip(x0, 0, W - 1); X1 = np.clip(x0 + 1, 0, W - 1); Y0 = np.clip(y0, 0, H - 1); Y1 = np.clip(y0 + 1, 0, H - 1)
    return (img[Y0, X0] * (1 - fx) * (1 - fy) + img[Y0, X1] * fx * (1 - fy) + img[Y1, X0] * (1 - fx) * fy + img[Y1, X1] * fx * fy)


def occlusion(tri, depth, W, H, bias=0.12):
    """per-triangle fraction of its covered pixel centres that lie more than `bias` behind the nearest surface
    (smallest depth) of the whole set. tri (n, 3, 2) px, depth (n, 3)."""
    zbuf = np.full((H, W), np.inf, np.float32)
    n = len(tri)
    boxes = []
    for pass_ in (0, 1):
        occ = np.zeros(n, np.float32); tot = np.zeros(n, np.int32)
        for i in range(n):
            (ax, ay), (bx, by), (cx, cy) = tri[i]
            den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(den) < 1e-12: continue
            x0 = max(int(np.floor(min(ax, bx, cx) - 0.5)), 0); x1 = min(int(np.ceil(max(ax, bx, cx) - 0.5)), W - 1)
            y0 = max(int(np.floor(min(ay, by, cy) - 0.5)), 0); y1 = min(int(np.ceil(max(ay, by, cy) - 0.5)), H - 1)
            if x1 < x0 or y1 < y0: continue
            X, Y = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            w0 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / den
            w1 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / den
            w2 = 1 - w0 - w1
            m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
            if not m.any(): continue
            z = w0 * depth[i, 0] + w1 * depth[i, 1] + w2 * depth[i, 2]
            sl = (slice(y0, y1 + 1), slice(x0, x1 + 1))
            if pass_ == 0:
                zbuf[sl] = np.where(m, np.minimum(zbuf[sl], z), zbuf[sl])
            else:
                tot[i] = int(m.sum()); occ[i] = float((m & (z > zbuf[sl] + bias)).sum())
    return occ / np.maximum(tot, 1), tot
