"""Crop a Sentinel-2 L2A 'visual' (TCI, 10 m) COG + SCL around ZSSS via HTTP range reads (earth-search, AWS).

Usage: python3 -I s2_crop.py <item.json> <out_dir>
Writes s2_<id>_visual_zsss_20km.tif (EPSG:326xx, values unmodified), a PNG preview and SCL class shares.
Licence: Copernicus Sentinel data legal notice; credit 'Contains modified Copernicus Sentinel data <year>'.
"""
import sys, os, json
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds
from PIL import Image

ARP = (121.33426, 31.198104)
item = json.load(open(sys.argv[1])); out = sys.argv[2]
os.makedirs(out, exist_ok=True)
dlat = 10000 / 110852.0; dlon = 10000 / (111412.84 * np.cos(np.radians(ARP[1])))
bb = (ARP[0] - dlon, ARP[1] - dlat, ARP[0] + dlon, ARP[1] + dlat)
res = dict(id=item["id"], datetime=item["properties"]["datetime"], cloud=item["properties"].get("eo:cloud_cover"))
for key in ("visual", "scl"):
    href = item["assets"][key]["href"]
    with rasterio.open(href) as s:
        b = transform_bounds("EPSG:4326", s.crs, *bb)
        w = from_bounds(*b, transform=s.transform).round_offsets().round_lengths()
        a = s.read(window=w)
        tr = s.window_transform(w)
        prof = s.profile.copy()
        prof.update(width=a.shape[2], height=a.shape[1], transform=tr, compress="deflate", tiled=True, blockxsize=256, blockysize=256)
        p = os.path.join(out, f"s2_{item['id']}_{key}_zsss_20km.tif")
        with rasterio.open(p, "w", **prof) as o:
            o.write(a)
            o.update_tags(CREDIT=f"Contains modified Copernicus Sentinel data {res['datetime'][:4]}", SOURCE=href)
        res[key] = dict(path=p, crs=str(s.crs), shape=list(a.shape), res=list(s.res))
        if key == "visual":
            Image.fromarray(np.moveaxis(a[:3], 0, -1)).save(os.path.join(out, f"s2_{item['id']}_visual_zsss_20km.png"))
        else:
            v, c = np.unique(a, return_counts=True)
            res["scl_shares_pct"] = {int(k): round(100 * cc / c.sum(), 2) for k, cc in zip(v, c)}
json.dump(res, open(os.path.join(out, f"s2_{item['id']}_crop.json"), "w"), indent=1)
print(json.dumps(res, indent=1))
