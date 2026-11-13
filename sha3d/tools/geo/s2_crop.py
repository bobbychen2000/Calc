"""Read a window of Sentinel-2 L2A COG bands (Earth Search STAC item JSON) via HTTP range requests.

Usage: python3 -I s2_crop.py ITEM_JSON OUT_DIR lon0 lat0 lon1 lat1
Writes OUT_DIR/<band>.tif (GeoTIFF, native UTM grid, uint16 DN / uint8 TCI) for B02 B03 B04 B08 TCI SCL.
"""
import json
import os
import sys

os.environ.setdefault("CURL_CA_BUNDLE", "/root/.ccr/ca-bundle.crt")
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("GDAL_HTTP_MAX_RETRY", "4")

import rasterio  # noqa: E402
from rasterio.windows import from_bounds  # noqa: E402
from pyproj import Transformer  # noqa: E402

item = json.load(open(sys.argv[1]))
out = sys.argv[2]
lon0, lat0, lon1, lat1 = map(float, sys.argv[3:7])
os.makedirs(out, exist_ok=True)
epsg = item["properties"]["proj:epsg"]
tr = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
xs, ys = zip(*[tr.transform(lo, la) for lo in (lon0, lon1) for la in (lat0, lat1)])
bounds = (min(xs), min(ys), max(xs), max(ys))
names = {"blue": "B02", "green": "B03", "red": "B04", "nir": "B08", "visual": "TCI", "scl": "SCL"}
for key, nm in names.items():
    href = item["assets"][key]["href"]
    with rasterio.open(href) as src:
        win = from_bounds(*bounds, transform=src.transform).round_offsets().round_lengths()
        data = src.read(window=win)
        prof = src.profile.copy()
        prof.update(width=data.shape[2], height=data.shape[1], transform=src.window_transform(win),
                    tiled=False, compress="deflate", driver="GTiff")
        prof.pop("blockxsize", None); prof.pop("blockysize", None)
        with rasterio.open(os.path.join(out, nm + ".tif"), "w", **prof) as dst:
            dst.write(data)
        print(nm, href, data.shape, src.window_transform(win))
