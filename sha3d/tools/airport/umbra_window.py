"""Read small full-resolution (0.35 m) windows of the Umbra GEC over ZSSS by HTTP range requests (CC BY 4.0).

usage: python3 -I umbra_window.py OUT_DIR NAME LAT LON HALF_M [NAME LAT LON HALF_M ...]
Writes OUT_DIR/<NAME>.tif: the pixel window (rotated geotransform kept) covering a square of +-HALF_M metres.
"""
import math
import os
import sys

os.environ.setdefault('CURL_CA_BUNDLE', '/root/.ccr/ca-bundle.crt')
os.environ.setdefault('GDAL_DISABLE_READDIR_ON_OPEN', 'EMPTY_DIR')
import rasterio  # noqa: E402
from rasterio.windows import Window  # noqa: E402

URL = ('https://umbra-open-data-catalog.s3.amazonaws.com/sar-data/tasks/ad%20hoc/Shanghai_CHN/'
       '96b8bdc7-96bf-415e-b43b-20adc327995f/2024-06-02-01-46-47_UMBRA-05/2024-06-02-01-46-47_UMBRA-05_GEC.tif')
out = sys.argv[1]
args = sys.argv[2:]
with rasterio.open('/vsicurl/' + URL) as s:
    inv = ~s.transform
    for k in range(0, len(args), 4):
        name, lat, lon, half = args[k], float(args[k + 1]), float(args[k + 2]), float(args[k + 3])
        dlat = half / 110857.0; dlon = half / (111320 * math.cos(math.radians(lat)))
        cs, rs = zip(*[inv * (lon + a * dlon, lat + b * dlat) for a in (-1, 1) for b in (-1, 1)])
        c0, c1, r0, r1 = int(min(cs)), int(max(cs)) + 1, int(min(rs)), int(max(rs)) + 1
        win = Window(c0, r0, c1 - c0, r1 - r0)
        a = s.read(1, window=win)
        prof = s.profile.copy()
        prof.update(width=a.shape[1], height=a.shape[0], transform=s.window_transform(win), compress='deflate',
                    tiled=False)
        prof.pop('blockxsize', None); prof.pop('blockysize', None)
        with rasterio.open(os.path.join(out, name + '.tif'), 'w', **prof) as d:
            d.write(a, 1)
        print(name, a.shape, a.dtype, win)
