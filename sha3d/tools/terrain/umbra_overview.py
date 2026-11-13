"""Fetch a decimated overview of the Umbra open-data GEC over ZSSS (CC BY 4.0) via HTTP range reads.

Usage: python3 -I umbra_overview.py <url> <out_dir> <factor>
Writes <out_dir>/umbra_gec_ovr<factor>.tif (same rotated geotransform, scaled) and a PNG preview.
"""
import sys, os
import numpy as np
import rasterio
from rasterio.enums import Resampling
from PIL import Image

url, out, f = sys.argv[1], sys.argv[2], int(sys.argv[3])
with rasterio.open('/vsicurl/' + url) as s:
    h, w = s.height // f, s.width // f
    a = s.read(1, out_shape=(h, w), resampling=Resampling.average)
    tr = s.transform * s.transform.scale(s.width / w, s.height / h)
    prof = s.profile.copy()
prof.update(width=w, height=h, transform=tr, compress='deflate', tiled=True, blockxsize=512, blockysize=512)
p = os.path.join(out, f'umbra_gec_ovr{f}.tif')
with rasterio.open(p, 'w', **prof) as d:
    d.write(a, 1)
# north-up-ish preview only for eyeballing (array order, NOT georeferenced)
Image.fromarray(a).save(os.path.join(out, f'umbra_gec_ovr{f}_array.png'))
print(p, a.shape, tr, float((a > 0).mean()))
