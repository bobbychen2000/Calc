"""ESA WorldCover 10 m 2021 v200: crop a ~20 km box around ZSSS, report class shares.

Usage: python3 -I worldcover_crop.py <N30E120_Map.tif> <osm_context.geojson> <out_dir>

Writes <out_dir>/esa_worldcover_2021_v200_zsss_20km.tif (crop, values unmodified, EPSG:4326),
a colour PNG preview (official class palette from the PUM v2.0) and class-share JSON for: the 20 km box,
the OSM aerodrome polygon, and a 1.5 km box around the Hongqiao railway station.
"""
import sys, os, json
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.features import geometry_mask
from PIL import Image

ARP = (121.33426, 31.198104)  # hypothesis (OurAirports), used only as the crop centre
HALF_KM = 10.0
CLASSES = {10: ("Tree cover", (0, 100, 0)), 20: ("Shrubland", (255, 187, 34)), 30: ("Grassland", (255, 255, 76)),
           40: ("Cropland", (240, 150, 255)), 50: ("Built-up", (250, 0, 0)), 60: ("Bare / sparse vegetation", (180, 180, 180)),
           70: ("Snow and ice", (240, 240, 240)), 80: ("Permanent water bodies", (0, 100, 200)),
           90: ("Herbaceous wetland", (0, 150, 160)), 95: ("Mangroves", (0, 207, 117)), 100: ("Moss and lichen", (250, 230, 160))}
ATTRIB = "(c) ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium"


def box(lon, lat, half_km):
    dlat = half_km * 1000 / 110852.0
    dlon = half_km * 1000 / (111412.84 * np.cos(np.radians(lat)) - 93.5 * np.cos(np.radians(3 * lat)))
    return lon - dlon, lat - dlat, lon + dlon, lat + dlat


def shares(a):
    v, c = np.unique(a, return_counts=True)
    n = c.sum()
    return {f"{int(k)} {CLASSES.get(int(k), ('?',))[0]}": dict(px=int(cc), pct=round(100.0 * cc / n, 2)) for k, cc in zip(v, c)}


def main():
    src, osm, out = sys.argv[1:4]
    os.makedirs(out, exist_ok=True)
    fc = json.load(open(osm))
    aero = [f for f in fc["features"] if f["properties"]["kind"] == "aerodrome"][0]["geometry"]
    stn = [f for f in fc["features"] if f["properties"].get("name:en") == "Shanghai Hongqiao Station"][0]
    ring = stn["geometry"]["coordinates"][0]
    slon = sum(p[0] for p in ring) / len(ring)
    slat = sum(p[1] for p in ring) / len(ring)
    res = {}
    with rasterio.open(src) as s:
        res["profile"] = dict(crs=str(s.crs), res=list(s.res), bounds=list(s.bounds), nodata=s.nodata, dtype=s.dtypes[0])
        b = box(*ARP, HALF_KM)
        w = from_bounds(*b, transform=s.transform).round_offsets().round_lengths()
        a = s.read(1, window=w)
        tr = s.window_transform(w)
        prof = s.profile.copy()
        prof.update(width=a.shape[1], height=a.shape[0], transform=tr, compress="deflate", tiled=True, blockxsize=256, blockysize=256)
        p = os.path.join(out, "esa_worldcover_2021_v200_zsss_20km.tif")
        with rasterio.open(p, "w", **prof) as o:
            o.write(a, 1)
            o.update_tags(ATTRIBUTION=ATTRIB, LICENCE="CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)",
                          CITATION="Zanaga, D. et al. 2022. ESA WorldCover 10 m 2021 v200. doi:10.5281/zenodo.7254221",
                          SOURCE="s3://esa-worldcover/v200/2021/map/ESA_WorldCover_10m_2021_v200_N30E120_Map.tif (crop, values unmodified)")
        res["crop"] = dict(path=p, bounds_requested=b, shape=list(a.shape), transform=list(tr)[:6])
        res["box_20km"] = shares(a)
        ins = ~geometry_mask([aero], out_shape=a.shape, transform=tr)
        res["aerodrome_polygon"] = shares(a[ins])
        res["outside_aerodrome"] = shares(a[~ins])
        sb = box(slon, slat, 0.75)
        ws = from_bounds(*sb, transform=s.transform).round_offsets().round_lengths()
        res["hongqiao_station_1p5km_box"] = dict(centre=[round(slon, 6), round(slat, 6)], shares=shares(s.read(1, window=ws)))
    rgb = np.zeros(a.shape + (3,), np.uint8)
    for k, (_, col) in CLASSES.items():
        rgb[a == k] = col
    Image.fromarray(rgb).save(os.path.join(out, "esa_worldcover_2021_v200_zsss_20km_preview.png"))
    json.dump(res, open(os.path.join(out, "worldcover_shares_zsss.json"), "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
