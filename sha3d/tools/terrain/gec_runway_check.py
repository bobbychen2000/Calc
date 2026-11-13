"""Rough registration check of the Umbra GEC overview against OSM runway centrelines.
Usage: python3 -I gec_runway_check.py <umbra_gec_ovr4.tif> <osm_context.geojson>
For offsets -60..+60 m perpendicular (east positive) to each runway, mean GEC amplitude along the line;
the runway pavement is a dark (specular) band, so the minimum-amplitude band centre estimates the E-W offset.
"""
import sys, json
import numpy as np
import rasterio
from pyproj import Geod
G = Geod(ellps="WGS84")
src, osm = sys.argv[1:3]
fc = json.load(open(osm))
with rasterio.open(src) as s:
    a = s.read(1).astype(float); inv = ~s.transform
    for f in [f for f in fc["features"] if f["properties"]["kind"] == "runway"]:
        c = f["geometry"]["coordinates"]; (lo0, la0), (lo1, la1) = c[0], c[-1]
        az, _, L = G.inv(lo0, la0, lo1, la1)
        perp = az + 90
        prof = []
        for off in range(-80, 81, 2):
            vals = []
            for t in np.linspace(0.1, 0.9, 300):
                lo, la, _ = G.fwd(lo0, la0, az, L * t)
                lo, la, _ = G.fwd(lo, la, perp, off)
                col, row = inv * (lo, la)
                r, cc = int(row), int(col)
                if 0 <= r < a.shape[0] and 0 <= cc < a.shape[1] and a[r, cc] > 0:
                    vals.append(a[r, cc])
            prof.append((off, float(np.median(vals)) if vals else np.nan))
        p = np.array(prof)
        lo_thr = np.nanmin(p[:, 1]) + 0.5 * (np.nanmedian(p[:, 1]) - np.nanmin(p[:, 1]))
        dark = p[p[:, 1] <= lo_thr, 0]
        sgn = 1 if (az % 360) < 90 or (az % 360) > 270 else -1  # perp points east for northbound lines
        print(f["properties"]["ref"], "az", round(az % 360, 2), "dark band offsets (m, +=perp az %.1f):" % (perp % 360), dark.min(), "to", dark.max(),
              "centre", (dark.min() + dark.max()) / 2, "width", dark.max() - dark.min())
