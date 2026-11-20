"""Low-detail far ground for SHA Live 3D: ESA WorldCover 2021 land-cover classes beyond the detailed extent, as a coarse
colour map on the world frame (package P2d).

usage: python3 -I tools/terrain/worldcover_far.py            (from sha3d/; deterministic)
  -> data/sha_landcover_far.js   window.SHA_LANDCOVER_FAR = {rect, w, h, res_m, png_col, png_attr, classes, ...}

Why: the core ground (js/world/ground.js + js/shaders/ground.js) draws one neutral colour beyond the 23.5 km2 detailed
extent (PLAN s.6b Q3), which reads as an island in the sea from overview heights. This file gives that far ground the
colours of its land cover, so the airport sits in an urban plain that fades into haze.

Legal default kept (PLAN s.6b Q3, the lead's P2d brief): detail stays inside the extent. Beyond it there are NO buildings,
NO roads and NO imagery - only land-cover class fractions averaged over 50 m cells (five times coarser than the 10 m
source, and far coarser than the 10 m / 0.5 m imagery thresholds discussed in PLAN R3); colours are class means, not
pixels of a photograph.

Input (local, CC BY 4.0): refs/cache/landcover/derived_zsss/esa_worldcover_2021_v200_zsss_20km.tif - the 20 km crop of
ESA WorldCover 10 m 2021 v200 tile N30E120 (tools/terrain/worldcover_crop.py; refs/cache/landcover/SOURCES.json).
Calibration (optional, obs): the committed Sentinel-2 L2A crop refs/cache/s2/S2B_51RUQ_20261014_0_L2A (10 m, inside
the detailed extent) gives each class its mean surface reflectance on "pure" pixels (the same WorldCover class in the
3 x 3 neighbourhood), so the far colours continue the Sentinel-2 ground colour of the extent without a seam. Classes
with fewer than 500 pure pixels inside the extent keep the fallback palette below [inf].

Method:
  1. every WorldCover pixel centre (lat, lon) -> world (x, z) via tools/common/frame.py (vectorised: the exact local
     tangent plane is evaluated on a coarse lat/lon grid and interpolated bilinearly; error < 1 cm over 20 km, checked);
  2. binned into 50 m world cells over the crop's world bbox -> class fractions per cell;
  3. colour = sum(fraction x class reflectance) -> 8-bit sRGB of 2 x reflectance (the same encoding as data/sha_ground_s2.js:
     decode rho = srgb_to_linear(v / 255) / 2), stored as JPEG (quality 90, deterministic with this Pillow);
     attributes (PNG): R = water (class 80) fraction, G = built-up (50) fraction, B = distance outside the detailed extent
     / 6000 m (0 inside; the renderer's haze ramp);
  4. base64 in a JS wrapper.
Attribution: (c) ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA
WorldCover consortium (CC BY 4.0); calibration: Contains modified Copernicus Sentinel data 2026.
"""
import base64
import io
import json
import os
import sys

import numpy as np
import rasterio
from PIL import Image
from pyproj import Transformer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'common'))
import frame  # noqa: E402

WC = os.path.join(ROOT, 'refs', 'cache', 'landcover', 'derived_zsss', 'esa_worldcover_2021_v200_zsss_20km.tif')
S2 = os.path.join(ROOT, 'refs', 'cache', 's2', 'S2B_51RUQ_20261014_0_L2A')
OUT = os.path.join(ROOT, 'data', 'sha_landcover_far.js')
RES = 50.0
NAMES = {10: 'Tree cover', 20: 'Shrubland', 30: 'Grassland', 40: 'Cropland', 50: 'Built-up', 60: 'Bare / sparse vegetation',
         70: 'Snow and ice', 80: 'Permanent water bodies', 90: 'Herbaceous wetland', 95: 'Mangroves', 100: 'Moss and lichen'}
# fallback surface reflectance (R, G, B) per class [inf: typical values], replaced by the Sentinel-2 calibration where possible
FALLBACK = {10: (0.045, 0.065, 0.040), 20: (0.070, 0.080, 0.055), 30: (0.080, 0.095, 0.060), 40: (0.085, 0.095, 0.060),
            50: (0.130, 0.125, 0.115), 60: (0.150, 0.140, 0.120), 70: (0.8, 0.8, 0.8), 80: (0.030, 0.040, 0.040),
            90: (0.060, 0.075, 0.050), 95: (0.04, 0.06, 0.04), 100: (0.1, 0.1, 0.08)}
CLASSES = sorted(NAMES)


def srgb(c):
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def png_b64(arr, mode='RGBA'):
    buf = io.BytesIO(); Image.fromarray(arr, mode).save(buf, format='PNG', optimize=False, compress_level=9)
    return base64.b64encode(buf.getvalue()).decode('ascii'), len(buf.getvalue())


def jpg_b64(arr):
    buf = io.BytesIO(); Image.fromarray(arr, 'RGB').save(buf, format='JPEG', quality=90, subsampling=0, optimize=True)
    return base64.b64encode(buf.getvalue()).decode('ascii'), len(buf.getvalue())


def ll_to_world_grid(lat, lon):
    """vectorised frame.ll_to_world: exact on a 41 x 41 lat/lon grid, bilinear in between (the map is smooth)"""
    la0, la1, lo0, lo1 = float(lat.min()), float(lat.max()), float(lon.min()), float(lon.max())
    n = 41; gla = np.linspace(la0, la1, n); glo = np.linspace(lo0, lo1, n)
    GX = np.empty((n, n)); GZ = np.empty((n, n))
    for j, a in enumerate(gla):
        for i, o in enumerate(glo):
            GX[j, i], GZ[j, i] = frame.ll_to_world(float(a), float(o))
    fj = (lat - la0) / (la1 - la0) * (n - 1); fi = (lon - lo0) / (lo1 - lo0) * (n - 1)
    j0 = np.clip(np.floor(fj).astype(int), 0, n - 2); i0 = np.clip(np.floor(fi).astype(int), 0, n - 2); tj = fj - j0; ti = fi - i0
    def bil(G):
        return (G[j0, i0] * (1 - ti) + G[j0, i0 + 1] * ti) * (1 - tj) + (G[j0 + 1, i0] * (1 - ti) + G[j0 + 1, i0 + 1] * ti) * tj
    # accuracy check at a few points
    err = 0.0
    for a, o in ((la0 + 0.3 * (la1 - la0), lo0 + 0.7 * (lo1 - lo0)), (la0 + 0.91 * (la1 - la0), lo0 + 0.13 * (lo1 - lo0))):
        ex, ez = frame.ll_to_world(a, o)
        fj_ = (a - la0) / (la1 - la0) * (n - 1); fi_ = (o - lo0) / (lo1 - lo0) * (n - 1)
        jj = min(int(fj_), n - 2); ii = min(int(fi_), n - 2); t_ = fj_ - jj; s_ = fi_ - ii
        bx = (GX[jj, ii] * (1 - s_) + GX[jj, ii + 1] * s_) * (1 - t_) + (GX[jj + 1, ii] * (1 - s_) + GX[jj + 1, ii + 1] * s_) * t_
        bz = (GZ[jj, ii] * (1 - s_) + GZ[jj, ii + 1] * s_) * (1 - t_) + (GZ[jj + 1, ii] * (1 - s_) + GZ[jj + 1, ii + 1] * s_) * t_
        err = max(err, abs(bx - ex), abs(bz - ez))
    return bil(GX), bil(GZ), err


OUT_RANGE = 6000.0


def out_distance(x0, z0, w, h):
    """per 50 m cell: distance (m) outside the extent polygon of data/sha_airport.json, scaled to 0..255 over OUT_RANGE"""
    from matplotlib.path import Path
    from scipy.ndimage import distance_transform_edt
    with open(os.path.join(ROOT, 'data', 'sha_airport.json'), encoding='utf-8') as fh:
        ring = json.load(fh)['extent']['ring']
    xs = x0 + (np.arange(w) + 0.5) * RES; zs = z0 + (np.arange(h) + 0.5) * RES
    XX, ZZ = np.meshgrid(xs, zs)
    inside = Path(np.array(ring)).contains_points(np.stack([XX.ravel(), ZZ.ravel()], axis=1)).reshape(h, w)
    d = distance_transform_edt(~inside) * RES
    return np.round(255 * np.clip(d / OUT_RANGE, 0, 1)).astype(np.uint8)


def calibrate(wc, wtr):
    """mean Sentinel-2 reflectance per WorldCover class on pure pixels inside the detailed extent (S2 crop nodata outside)"""
    out, counts = {}, {}
    bands = []
    for b in ('B04', 'B03', 'B02'):
        p = os.path.join(S2, b + '.tif')
        if not os.path.exists(p):
            return out, counts
        with rasterio.open(p) as ds:
            bands.append((ds.read(1).astype(np.float64), ds.transform, ds.crs))
    arr0, T, crs = bands[0]
    H, W = arr0.shape
    rr, cc = np.mgrid[0:H, 0:W]
    E = T.c + (cc + 0.5) * T.a; N = T.f + (rr + 0.5) * T.e
    tr = Transformer.from_crs(crs, 'EPSG:4326', always_xy=True)
    lon, lat = tr.transform(E, N)
    inv = ~wtr
    col, row = inv * (lon, lat)
    col = np.floor(col).astype(int); row = np.floor(row).astype(int)
    ok = (col >= 1) & (row >= 1) & (col < wc.shape[1] - 1) & (row < wc.shape[0] - 1) & (arr0 > 0) & (bands[1][0] > 0) & (bands[2][0] > 0)
    colc = np.clip(col, 1, wc.shape[1] - 2); rowc = np.clip(row, 1, wc.shape[0] - 2)
    cls = wc[rowc, colc]
    pure = ok.copy()
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            pure &= wc[rowc + dj, colc + di] == cls
    for k in CLASSES:
        m = pure & (cls == k)
        n = int(m.sum()); counts[k] = n
        if n >= 500:
            out[k] = tuple(round(float(np.median(b[0][m]) * 0.0001), 4) for b in bands)
    return out, counts


def main():
    with rasterio.open(WC) as ds:
        wc = ds.read(1); wtr = ds.transform
    H, W = wc.shape
    rows, cols = np.mgrid[0:H, 0:W]
    lon = wtr.c + (cols + 0.5) * wtr.a; lat = wtr.f + (rows + 0.5) * wtr.e
    X, Z, err = ll_to_world_grid(lat, lon)
    # output grid: the crop's world bbox shrunk to whole 50 m cells that are fully covered
    x0 = np.ceil(max(X[:, 0].max(), X[:, 0].max()) / RES) * RES; x1 = np.floor(X[:, -1].min() / RES) * RES
    z0 = np.ceil(Z[0, :].max() / RES) * RES; z1 = np.floor(Z[-1, :].min() / RES) * RES
    w = int((x1 - x0) / RES); h = int((z1 - z0) / RES)
    ci = np.floor((X - x0) / RES).astype(int); cj = np.floor((Z - z0) / RES).astype(int)
    ok = (ci >= 0) & (cj >= 0) & (ci < w) & (cj < h) & (wc > 0)
    idx = (cj * w + ci)[ok]; cls = wc[ok]
    total = np.bincount(idx, minlength=w * h).astype(np.float64)
    frac = {}
    for k in CLASSES:
        frac[k] = np.bincount(idx[cls == k], minlength=w * h) / np.maximum(total, 1)
    cal, counts = calibrate(wc, wtr)
    refl = {k: cal.get(k, FALLBACK[k]) for k in CLASSES}
    rgb = np.zeros((w * h, 3))
    for k in CLASSES:
        rgb += frac[k][:, None] * np.array(refl[k])[None, :]
    valid = total > 0
    col = np.round(255 * srgb(np.minimum(1.0, 2.0 * rgb))).reshape(h, w, 3).astype(np.uint8)
    attr = np.zeros((h, w, 3), np.uint8)
    for ch, f in enumerate((frac[80], frac[50])):
        attr[..., ch] = np.round(255 * np.clip(f, 0, 1)).reshape(h, w).astype(np.uint8)
    # B = distance outside the detailed extent (0 inside, 255 at >= OUT_RANGE m): the haze ramp starts at the extent edge
    # (js/live/terminals.js), so the far ground next to the extent is not hazier than the extent itself
    attr[..., 2] = out_distance(x0, z0, w, h)
    pc, nc = jpg_b64(col); pa, na = png_b64(attr, 'RGB')
    shares = {NAMES[k]: round(float(frac[k][valid].mean()), 4) for k in CLASSES if frac[k][valid].mean() > 0}
    mean_rgb = [round(float(v), 4) for v in rgb[valid].mean(axis=0)]
    meta = {
        'what': 'ESA WorldCover 2021 land-cover colours for the far ground beyond the detailed extent (class fractions over 50 m cells; '
                'no buildings, no roads, no imagery)',
        'attribution': '(c) ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium',
        'licence': 'CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/), adapted: resampled to 50 m class fractions and coloured',
        'citation': 'Zanaga, D. et al., 2022. ESA WorldCover 10 m 2021 v200. doi:10.5281/zenodo.7254221',
        'calibration': 'class colours = median Sentinel-2 L2A reflectance (S2B_51RUQ_20261014_0_L2A, inside the detailed extent) on pure pixels; '
                       'Contains modified Copernicus Sentinel data 2026',
        'frame': frame.FRAME_ID, 'rect': [float(x0), float(z0), float(x1 - x0), float(z1 - z0)], 'res_m': RES, 'w': w, 'h': h,
        'encoding': 'png_col (JPEG q90) RGB = 255 * srgb(min(1, 2 * reflectance)); png_attr (PNG) R water fraction, G built-up fraction, '
                    'B = 255 * min(1, distance outside the extent / %d m)' % OUT_RANGE,
        'classes': {str(k): {'name': NAMES[k], 'reflectance_rgb': refl[k], 'src': 'obs (S2 calibration)' if k in cal else 'inf (fallback)',
                             'pure_px_in_extent': counts.get(k, 0)} for k in CLASSES},
        'shares': shares, 'mean_reflectance_rgb': mean_rgb, 'grid_interp_err_m': round(err, 4),
        'generator': 'tools/terrain/worldcover_far.py', 'src': 'obs (land cover) / inf (colours where not calibrated, the far rendering)',
    }
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('// generated by tools/terrain/worldcover_far.py - do not edit. (c) ESA WorldCover project 2021 / Contains modified Copernicus '
                'Sentinel data (2021) processed by ESA WorldCover consortium (CC BY 4.0); calibration: Contains modified Copernicus Sentinel data 2026.\n')
        f.write('window.SHA_LANDCOVER_FAR = ' + json.dumps({**meta, 'png_col': pc, 'png_attr': pa}, separators=(',', ':')) + ';\n')
    print(json.dumps(meta, indent=1)[:3000], 'png bytes', nc, na)


if __name__ == '__main__':
    main()
