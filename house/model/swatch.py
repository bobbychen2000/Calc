"""Material swatches cut from the reference photographs: a small clean patch of a real surface, straightened to
true scale on its plane, evened out (the photograph's light gradient divided away), made to tile, and given the
mean colour the material should have under the viewer's light.  The viewer lays them over the model with the
model's own UVs (metres), so they repeat without gaps and take the scene's light and shadows.

    make(cams) -> {material: {image, size: [u metres, v metres]}}      (files written into out/, never committed)
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PPM = 96                                             # texels per metre of the swatches


def rectify(src, cam, origin, eu, ev, w_m, h_m):
    """Sample the photograph on the world rectangle origin + u eu + v ev (u in [0, w_m], v in [0, h_m]).
    Row 0 of the result is v = h_m (so that v runs up the image, as texture coordinates do)."""
    import cv2
    sys.path.insert(0, os.path.join(HERE, 'tools'))
    import cams as CAMS
    W, H = int(round(w_m * PPM)), int(round(h_m * PPM))
    u, v = np.meshgrid((np.arange(W) + 0.5) / PPM, h_m - (np.arange(H) + 0.5) / PPM)
    P = np.asarray(origin, float) + u[..., None] * np.asarray(eu, float) + v[..., None] * np.asarray(ev, float)
    uv = CAMS.project(cam, P.reshape(-1, 3)).reshape(H, W, 2).astype(np.float32)
    return cv2.remap(src, uv[..., 0], uv[..., 1], cv2.INTER_CUBIC).astype(float)


def delight(a, sigma_m=0.7):
    """Divide the slow light gradient away (shade toward one side, a soft shadow), keep the pattern."""
    import cv2
    low = cv2.GaussianBlur(a, (0, 0), sigma_m * PPM, borderType=cv2.BORDER_REFLECT)
    return a / np.maximum(low, 1.0) * a.reshape(-1, 3).mean(0)


def tileable(a, band=0.3):
    """Blend the patch with its half-shifted copies so that opposite edges continue each other."""
    H, W = a.shape[:2]

    def ramp(n):
        t = np.minimum(np.arange(n) + 0.5, n - np.arange(n) - 0.5) / (band * n)
        t = np.clip(t, 0, 1)
        return t * t * (3 - 2 * t)
    wx, wy = ramp(W)[None, :, None], ramp(H)[:, None, None]
    ax, ay = np.roll(a, W // 2, 1), np.roll(a, H // 2, 0)
    axy = np.roll(ax, H // 2, 0)
    return a * wx * wy + ax * (1 - wx) * wy + ay * wx * (1 - wy) + axy * (1 - wx) * (1 - wy)


def finish(a, mean_linear, contrast=1.0):
    """Give the patch the wanted mean colour (linear albedo), keeping its pattern; returns 8-bit sRGB."""
    lin = (np.clip(a, 0, 255) / 255.0) ** 2.2
    m = lin.reshape(-1, 3).mean(0)
    lin = np.asarray(mean_linear, float) * (1 + contrast * (lin / m - 1))
    return (np.clip(lin, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)


def roof_point(planes, cam, uv):
    """Where the pixel's ray meets the roofs: (point, plane) of the highest plane it crosses inside its outline."""
    sys.path.insert(0, os.path.join(HERE, 'tools'))
    import cams as CAMS
    C = np.asarray(cam['C'], float)
    d = np.asarray(CAMS.ray(cam, [uv])[1], float).reshape(-1, 3)[0]
    best = None
    for p in planes:
        a, b, c = p.abc
        den = d[2] - a * d[0] - b * d[1]
        if abs(den) < 1e-9:
            continue
        t = (a * C[0] + b * C[1] + c - C[2]) / den
        q = C + t * d
        if t > 0 and p.contains(q[0], q[1]) and (best is None or q[2] > best[0][2]):
            best = (q, p)
    return best


def make(cams):
    from PIL import Image
    from model.zones import house, site
    out = {}
    cam = cams.get('photos/p30_b7b282.jpg')
    path = os.path.join(HERE, 'refs', 'cache', 'photos', 'p30_b7b282.jpg')
    if cam is None or not os.path.exists(path):
        return out
    src = np.asarray(Image.open(path).convert('RGB'))
    # asphalt shingles: a sunlit rear-facing plane, clear of vents and of the oak's shadow.  14 courses of 0.143 m.
    hit = roof_point(house.planes(), cam, (1330.0, 1538.0))
    if hit is not None:
        q, p = hit
        dn = p.downhill
        sl = float(np.hypot(p.abc[0], p.abc[1]))
        up = np.array([-dn[0], -dn[1], sl]) / np.sqrt(1 + sl * sl)
        eu = np.array([-dn[1], dn[0], 0.0])
        w_m, h_m = 2.3, 14 * 0.143
        a = rectify(src, cam, q - eu * w_m / 2 - up * h_m / 2, eu, up, w_m, h_m)
        img = finish(tileable(delight(a)), (0.21, 0.21, 0.215), contrast=1.15)
        Image.fromarray(img).save(os.path.join(HERE, 'out', 'swatch_shingle.jpg'), quality=92)
        out['roof_shingle'] = dict(image='swatch_shingle.jpg', size=[w_m, h_m])
    # driveway pavers: the evenly shaded part of the driveway.  7 x 20 courses of 0.2286 m.
    w_m, h_m = 7 * 0.2286, 20 * 0.2286
    x0, y0 = 1.05, -6.5
    zz = lambda y: site.drive_z(y)                                   # noqa: E731
    o = np.array([x0, y0, zz(y0)])
    ev = np.array([0.0, h_m, zz(y0 + h_m) - zz(y0)]) / h_m
    a = rectify(src, cam, o, np.array([1.0, 0, 0]), ev, w_m, h_m)
    img = finish(tileable(delight(a, 0.9)), (0.47, 0.455, 0.44), contrast=1.1)
    Image.fromarray(img).save(os.path.join(HERE, 'out', 'swatch_pavers.jpg'), quality=92)
    out['paver_drive'] = dict(image='swatch_pavers.jpg', size=[w_m, h_m])
    return out
