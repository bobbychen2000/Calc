"""Ground-colour hint for the SHA Live 3D app: Sentinel-2 L2A surface reflectance resampled onto the world frame.

usage: python3 -I tools/terrain/s2_ground_hint.py            (from sha3d/; deterministic)
  -> data/sha_ground_s2.js   window.SHA_GROUND_S2 = {rect, w, h, png (base64), ...}

What it is: the low-frequency colour of the ground (fields, canals, urban fabric, apron concrete) for the app's ground
shader (js/world/ground.js), which mixes it into its procedural grass / urban albedo outside the airside pavement. It
is a colour hint only: 10 m pixels cannot show markings or edges, and no geometry is taken from it.

Input: the committed Sentinel-2 crops refs/cache/s2/S2B_51RUQ_20261014_0_L2A/B04.tif, B03.tif, B02.tif (10 m, UTM 51N,
cut to the detailed extent bbox, nodata 0 outside the extent polygon; refs/cache/s2/SOURCES.json: Copernicus Sentinel
data, free and open; notice "Contains modified Copernicus Sentinel data 2026"). Scene 2026-10-14 (tile cloud cover
1.98 %), the newer of the two committed scenes.

Method:
  1. output grid in the world frame (tools/common/frame.py, x east / z south): 10 m pixels over the extent bbox (rect
     below); every pixel centre (x, z) -> WGS 84 (frame.world_to_ll) -> UTM 51N (pyproj) -> bilinear sample of the three
     bands (pixels whose 2 x 2 neighbourhood touches nodata are nodata);
  2. surface reflectance = DN * 0.0001, clamped to [0, 0.6]. The STAC raster:bands list scale 0.0001 and offset -0.1,
     but the item says earthsearch:boa_offset_applied = true, and the pixel values show the offset is already removed:
     5th-percentile DN of B04 / B03 / B02 = 256 / 366 / 239 (with the -0.1 offset that would be negative reflectance
     over 5 % of the extent) and the median red DN 925 matches the TCI (DN x 255 / 2000 = 118 vs TCI mean 107) [obs];
     so only the scale is applied [inf, from those statistics];
  3. stored as 8-bit sRGB-encoded reflectance x 2 (value = round(255 * srgb(min(1, 2 rho)))) - the app decodes it back
     to linear reflectance; alpha = 255 inside the data, 0 at nodata (outside the extent polygon);
  4. PNG (deterministic encoder settings), base64, in a JS wrapper so it also loads from file://.
The scale factor 2 keeps 8-bit precision for dark surfaces (water 0.02-0.05, vegetation 0.03-0.08).
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

SCENE = 'S2B_51RUQ_20261014_0_L2A'
RES = 10.0
# world rect (x0, z0, x1, z1): the detailed-extent bbox (data/sha_airport.json extent ring: -2477..2082 x -3489..3533),
# rounded outwards to 10 m
RECT = (-2480.0, -3490.0, 2090.0, 3540.0)


def srgb(c):
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def main():
    x0, z0, x1, z1 = RECT
    W = int(round((x1 - x0) / RES)); H = int(round((z1 - z0) / RES))
    xs = x0 + (np.arange(W) + 0.5) * RES; zs = z0 + (np.arange(H) + 0.5) * RES
    lat = np.empty((H, W)); lon = np.empty((H, W))
    for j, z in enumerate(zs):
        for i, x in enumerate(xs):
            lat[j, i], lon[j, i] = frame.world_to_ll(float(x), float(z))
    d = os.path.join(ROOT, 'refs', 'cache', 's2', SCENE)
    bands = []
    for b in ('B04', 'B03', 'B02'):
        with rasterio.open(os.path.join(d, b + '.tif')) as ds:
            tr = Transformer.from_crs('EPSG:4326', ds.crs, always_xy=True)
            E, N = tr.transform(lon, lat)
            T = ds.transform
            arr = ds.read(1).astype(np.float64)
            # fractional pixel coordinates (pixel centres at +0.5)
            c = (E - T.c) / T.a - 0.5; r = (N - T.f) / T.e - 0.5
            c0 = np.floor(c).astype(int); r0 = np.floor(r).astype(int); fc = c - c0; fr = r - r0
            ok = (c0 >= 0) & (r0 >= 0) & (c0 + 1 < arr.shape[1]) & (r0 + 1 < arr.shape[0])
            c0c = np.clip(c0, 0, arr.shape[1] - 2); r0c = np.clip(r0, 0, arr.shape[0] - 2)
            v00 = arr[r0c, c0c]; v01 = arr[r0c, c0c + 1]; v10 = arr[r0c + 1, c0c]; v11 = arr[r0c + 1, c0c + 1]
            ok &= (v00 > 0) & (v01 > 0) & (v10 > 0) & (v11 > 0)
            v = (v00 * (1 - fc) + v01 * fc) * (1 - fr) + (v10 * (1 - fc) + v11 * fc) * fr
            rho = np.clip(v * 0.0001, 0.0, 0.6)
            bands.append((rho, ok))
    ok = bands[0][1] & bands[1][1] & bands[2][1]
    rgb = np.stack([np.round(255 * srgb(np.minimum(1.0, 2.0 * b[0]))) for b in bands], axis=-1)
    rgba = np.zeros((H, W, 4), np.uint8); rgba[..., :3] = np.where(ok[..., None], rgb, 0).astype(np.uint8); rgba[..., 3] = np.where(ok, 255, 0)
    buf = io.BytesIO(); Image.fromarray(rgba, 'RGBA').save(buf, format='PNG', optimize=False, compress_level=9)
    png = base64.b64encode(buf.getvalue()).decode('ascii')
    meta = {
        'what': 'Sentinel-2 L2A surface-reflectance colour hint on the world frame (ground colour only, no geometry)',
        'attribution': 'Contains modified Copernicus Sentinel data 2026',
        'licence': 'Copernicus Sentinel data legal notice (free, full and open; reproduction, distribution and adaptation allowed with the notice)',
        'scene': SCENE, 'bands': ['B04', 'B03', 'B02'], 'frame': frame.FRAME_ID,
        'rect': [x0, z0, x1 - x0, z1 - z0], 'res_m': RES, 'w': W, 'h': H,
        'encoding': 'RGB = 255 * srgb(min(1, 2 * reflectance)); A = 255 data / 0 nodata; decode: rho = srgb_to_linear(v / 255) / 2',
        'generator': 'tools/terrain/s2_ground_hint.py', 'src': 'obs',
        'valid_px': int(ok.sum()),
        'mean_reflectance_rgb': [round(float(b[0][ok].mean()), 4) for b in bands],
    }
    out = os.path.join(ROOT, 'data', 'sha_ground_s2.js')
    with open(out, 'w', encoding='utf-8') as f:
        f.write('// generated by tools/terrain/s2_ground_hint.py - do not edit. Contains modified Copernicus Sentinel data 2026 (Sentinel-2 L2A, ' + SCENE + ').\n')
        f.write('window.SHA_GROUND_S2 = ' + json.dumps({**meta, 'png': png}, separators=(',', ':')) + ';\n')
    print(json.dumps(meta), 'png bytes', len(buf.getvalue()))


if __name__ == '__main__':
    main()
