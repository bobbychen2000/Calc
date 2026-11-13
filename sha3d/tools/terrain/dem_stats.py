"""Copernicus DEM (GLO-30 / GLO-90) statistics over ZSSS, plus a 20 km crop.

Usage:
  python3 -I dem_stats.py <glo30_dir> <glo90_dir> <osm_context.geojson> <out_dir>

Reads the GLO-30 DEM + aux masks (HEM/EDM/FLM/WBM) and the GLO-90 DEM, the aerodrome polygon and runway
centrelines from the OSM extract, and prints elevation statistics (EGM2008 heights, metres).
Writes <out_dir>/cop_dem_glo30_zsss_20km.tif (crop, unmodified values) and a JSON summary.
"""
import sys, os, json, glob
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.features import geometry_mask
from pyproj import Geod

G = Geod(ellps="WGS84")
ARP = (121.33426, 31.198104)  # OurAirports hypothesis, used only as the crop centre / probe point
HALF_KM = 10.0


def box(lon, lat, half_km):
    dlat = half_km * 1000 / 110852.0  # metres per degree latitude near 31 N (GRS80 meridional ~110.85 km)
    dlon = half_km * 1000 / (111412.84 * np.cos(np.radians(lat)) - 93.5 * np.cos(np.radians(3 * lat)))
    return lon - dlon, lat - dlat, lon + dlon, lat + dlat


def one(d, pat):
    f = glob.glob(os.path.join(d, pat))
    return f[0] if f else None


def sample(ds, lonlat):
    return np.array([v[0] for v in ds.sample(lonlat)], dtype=float)


def pct(a):
    a = a[np.isfinite(a)]
    return dict(n=int(a.size), min=round(float(a.min()), 2), p05=round(float(np.percentile(a, 5)), 2),
                median=round(float(np.median(a)), 2), mean=round(float(a.mean()), 2),
                p95=round(float(np.percentile(a, 95)), 2), max=round(float(a.max()), 2), std=round(float(a.std()), 2))


def line_points(coords, step=30.0):
    pts = []
    for (lo0, la0), (lo1, la1) in zip(coords[:-1], coords[1:]):
        az, _, dist = G.inv(lo0, la0, lo1, la1)
        n = max(1, int(dist // step))
        for i in range(n):
            lo, la, _ = G.fwd(lo0, la0, az, dist * i / n)
            pts.append((lo, la))
    pts.append(tuple(coords[-1]))
    return pts


def main():
    d30, d90, osm, out = sys.argv[1:5]
    os.makedirs(out, exist_ok=True)
    fc = json.load(open(osm))
    aero = [f for f in fc["features"] if f["properties"]["kind"] == "aerodrome"][0]["geometry"]
    rwys = [f for f in fc["features"] if f["properties"]["kind"] == "runway"]
    res = {}
    dem30 = one(d30, "*_DEM.tif")
    with rasterio.open(dem30) as s:
        res["glo30_profile"] = dict(crs=str(s.crs), transform=list(s.transform)[:6], width=s.width, height=s.height,
                                    dtype=s.dtypes[0], nodata=s.nodata, bounds=list(s.bounds), tags=s.tags())
        b = box(*ARP, HALF_KM)
        win = from_bounds(*b, transform=s.transform).round_offsets().round_lengths()
        z = s.read(1, window=win).astype(float)
        tr = s.window_transform(win)
        prof = s.profile.copy()
        prof.update(width=z.shape[1], height=z.shape[0], transform=tr, compress="deflate", predictor=3,
                    tiled=True, blockxsize=256, blockysize=256)
        crop_path = os.path.join(out, "cop_dem_glo30_zsss_20km.tif")
        with rasterio.open(crop_path, "w", **prof) as o:
            o.write(z.astype("float32"), 1)
            o.update_tags(LICENCE_NOTICE="produced using Copernicus WorldDEM-30 (c) DLR e.V. 2010-2014 and (c) Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved",
                          LIABILITY="The organisations in charge of the Copernicus programme by law or by delegation do not incur any liability for any use of the Copernicus WorldDEM-30",
                          SOURCE="s3://copernicus-dem-30m/Copernicus_DSM_COG_10_N31_00_E121_00_DEM (crop, values unmodified)",
                          VERTICAL_DATUM="EGM2008 (EPSG:3855), metres")
        res["crop"] = dict(path=crop_path, bounds_requested=b, window=[int(win.col_off), int(win.row_off), int(win.width), int(win.height)],
                           shape=list(z.shape), stats=pct(z))
        inside = ~geometry_mask([aero], out_shape=z.shape, transform=tr, invert=False)
        res["aerodrome_polygon_glo30"] = pct(z[inside])
        res["outside_aerodrome_in_20km_box_glo30"] = pct(z[~inside])
        res["arp_glo30"] = round(float(sample(s, [ARP])[0]), 2)
        # aux masks inside the aerodrome
        aux = {}
        for key in ("HEM", "EDM", "FLM", "WBM"):
            p = one(d30, f"*_{key}.tif")
            with rasterio.open(p) as a:
                w2 = from_bounds(*b, transform=a.transform).round_offsets().round_lengths()
                m = a.read(1, window=w2)
                if m.shape != z.shape:
                    aux[key] = f"shape mismatch {m.shape} vs {z.shape}"
                    continue
                mi = m[inside]
                if key == "HEM":
                    aux[key] = dict(aerodrome=pct(mi.astype(float)), box=pct(m.astype(float)))
                else:
                    vals, cnt = np.unique(mi, return_counts=True)
                    vb, cb = np.unique(m, return_counts=True)
                    aux[key] = dict(aerodrome={int(v): int(c) for v, c in zip(vals, cnt)}, box={int(v): int(c) for v, c in zip(vb, cb)})
        res["aux_masks"] = aux
        rr = {}
        for f in rwys:
            pts = line_points(f["geometry"]["coordinates"], 30.0)
            h = sample(s, pts)
            ref = f["properties"].get("ref")
            k = max(1, len(h) // 10)
            rr[ref] = dict(stats=pct(h), first_end=round(float(np.mean(h[:5])), 2), last_end=round(float(np.mean(h[-5:])), 2),
                           profile_every_10pct=[round(float(np.median(h[i:i + k])), 2) for i in range(0, len(h), k)])
        res["runways_glo30"] = rr
    dem90 = one(d90, "*_DEM.tif")
    with rasterio.open(dem90) as s:
        res["glo90_profile"] = dict(transform=list(s.transform)[:6], width=s.width, height=s.height)
        w9 = from_bounds(*box(*ARP, HALF_KM), transform=s.transform).round_offsets().round_lengths()
        z9 = s.read(1, window=w9).astype(float)
        tr9 = s.window_transform(w9)
        in9 = ~geometry_mask([aero], out_shape=z9.shape, transform=tr9, invert=False)
        res["aerodrome_polygon_glo90"] = pct(z9[in9])
        res["arp_glo90"] = round(float(sample(s, [ARP])[0]), 2)
        res["runways_glo90"] = {f["properties"].get("ref"): pct(sample(s, line_points(f["geometry"]["coordinates"], 30.0))) for f in rwys}
    json.dump(res, open(os.path.join(out, "dem_stats_zsss.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
