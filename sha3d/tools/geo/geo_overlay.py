"""Overlay OSM aeroway geometry on a Sentinel-2 true-colour crop (overview + zoom inset).

Usage: python3 -I geo_overlay.py OSM_DIR S2_SCENE_DIR ALIGN_JSON_A ALIGN_JSON_B OUT_JPG
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from pyproj import Transformer  # noqa: E402

import osm_load  # noqa: E402
from gcj02 import wgs_to_gcj  # noqa: E402

osm_dir, s2_dir, ja, jb, out = sys.argv[1:6]
N, W, R = osm_load.load(sorted(glob.glob(os.path.join(osm_dir, "map_*.osm"))) +
                        sorted(glob.glob(os.path.join(osm_dir, "*_full.xml"))))
ds = rasterio.open(os.path.join(s2_dir, "TCI.tif"))
T = ds.transform
tci = np.moveaxis(ds.read(), 0, 2)
tr = Transformer.from_crs("EPSG:4326", f"EPSG:{ds.crs.to_epsg()}", always_xy=True)
A = json.load(open(ja))
B = json.load(open(jb))
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def font(sz):
    try:
        return ImageFont.truetype(FONT, sz)
    except OSError:
        return ImageFont.load_default()


def en(lat, lon):
    return tr.transform(lon, lat)


def way_en(nds):
    p = [(N[x][0], N[x][1]) for x in nds if x in N]
    return [en(a, b) for a, b in p]


def panel(E0, N0, E1, N1, scale, gcj=True, stands=True, lw=1):
    """Crop [E0,E1]x[N0,N1] (metres, UTM) and upsample by `scale` px per 10 m pixel."""
    c0 = int((E0 - T.c) / T.a)
    c1 = int((E1 - T.c) / T.a)
    r0 = int((N1 - T.f) / T.e)
    r1 = int((N0 - T.f) / T.e)
    sub = tci[r0:r1, c0:c1]
    im = Image.fromarray(sub).resize(((c1 - c0) * scale, (r1 - r0) * scale), Image.BICUBIC)
    dr = ImageDraw.Draw(im)

    def px(E, Nn):
        return ((E - (T.c + c0 * T.a)) / T.a * scale, (Nn - (T.f + r0 * T.e)) / T.e * scale)

    def line(pts, col, w):
        dr.line([px(e, n) for e, n in pts], fill=col, width=w)

    for rel in R.values():
        if rel[1].get("aeroway") == "aerodrome":
            for typ, ref, role in rel[0]:
                if typ == "way" and ref in W:
                    line(way_en(W[ref][0]), (255, 255, 255), lw)
    for wid, (nds, t, m) in W.items():
        a = t.get("aeroway")
        if a == "apron":
            line(way_en(nds), (90, 170, 255), lw)
        elif a == "terminal" or (a == "hangar"):
            line(way_en(nds), (255, 140, 0), lw)
        elif a == "parking_position":
            line(way_en(nds), (0, 200, 200), max(1, lw - 1))
    for wid, (nds, t, m) in W.items():
        a = t.get("aeroway")
        if a == "taxiway":
            line(way_en(nds), (255, 230, 0), lw)
        elif a == "runway":
            line(way_en(nds), (255, 30, 30), lw + 1)
            if gcj:
                g = [wgs_to_gcj(N[x][0], N[x][1]) for x in nds if x in N]
                line([en(la, lo) for la, lo in g], (255, 0, 255), lw)
    if stands:
        for nid, (la, lo, t, m) in N.items():
            a = t.get("aeroway")
            if a in ("parking_position", "holding_position", "gate"):
                x, y = px(*en(la, lo))
                col = {"parking_position": (0, 255, 255), "holding_position": (255, 0, 255), "gate": (0, 255, 0)}[a]
                rr = 1.5 + lw
                dr.ellipse([x - rr, y - rr, x + rr, y + rr], outline=col, width=1)
    return im, px


# overview: aerodrome bbox + margin
E0, N0 = en(31.170, 121.312)
E1, N1 = en(31.226, 121.356)
ov, pxo = panel(E0, N0, E1, N1, 2, lw=1)
# zoom: centre of the airfield (between the runways and east apron), 1.2 km x 1.2 km at 8 px / 10 m
cE, cN = en(31.1985, 121.3365)
zm, pxz = panel(cE - 600, cN - 600, cE + 600, cN + 600, 8, gcj=True, lw=2)
zm = zm.resize((zm.width * 3 // 4, zm.height * 3 // 4), Image.LANCZOS)

# mark zoom box on overview
d = ImageDraw.Draw(ov)
x0, y0 = pxo(cE - 600, cN + 600)
x1, y1 = pxo(cE + 600, cN - 600)
d.rectangle([x0, y0, x1, y1], outline=(255, 255, 255), width=2)

pad = 12
Wt = ov.width + zm.width + 3 * pad
Ht = max(ov.height, zm.height + 520) + 2 * pad
canvas = Image.new("RGB", (Wt, Ht), (16, 16, 16))
canvas.paste(ov, (pad, pad))
canvas.paste(zm, (ov.width + 2 * pad, pad))
d = ImageDraw.Draw(canvas)
f1, f2 = font(20), font(15)
d.text((pad + 8, pad + 6), "Overview (2 px per 10 m S2 pixel); white box = zoom", fill=(255, 255, 255), font=f2)
d.text((ov.width + 2 * pad + 8, pad + 6), "Zoom 1.2 x 1.2 km (6 px per S2 pixel)", fill=(255, 255, 255), font=f2)
fa, fb = A["fine_all"], B["fine_all"]
paras = [
    ("OSM aeroway geometry over Sentinel-2 L2A true colour, Shanghai Hongqiao (ZSSS)", f1),
    ("Background: " + A["scene"] + " (10 m, UTM 51N / WGS-84). Contains modified Copernicus Sentinel data 2026. "
     "Map data (c) OpenStreetMap contributors, ODbL 1.0, downloaded 2026-11-13.", f2),
    ("Red = OSM runways; yellow = taxiways; cyan = stands (lead-in lines and ref nodes); green = gates; "
     "magenta circles = holding positions; blue = aprons; orange = terminals and hangars; white = aerodrome boundary.", f2),
    ("Magenta lines = the OSM runways moved by the GCJ-02 formula (+434 m E, -214 m N at ZSSS), i.e. where a feature "
     "traced from a GCJ-02 map would sit. No OSM feature sits there.", f2),
    (f"Measured OSM minus S2 (mirror-symmetry centres of straight runway and taxiway runs, robust LSQ): "
     f"{A['scene'][:24]} ({fa['n']} runs): dx {fa['dx']:+.1f} +/- {fa['se_dx']:.1f} m, dy {fa['dy']:+.1f} +/- {fa['se_dy']:.1f} m. "
     f"{B['scene'][:24]} ({fb['n']} runs): dx {fb['dx']:+.1f} +/- {fb['se_dx']:.1f} m, dy {fb['dy']:+.1f} +/- {fb['se_dy']:.1f} m.", f2),
    ("Per-run scatter about 3-4 m RMS. It is OSM tracing error: it repeats between the two scenes (r = 0.89). "
     "Sentinel-2 absolute geolocation spec: better than 12.5 m CE95, so the absolute check is about +/-10 m; "
     "the GCJ-02 shift (about 480 m) is ruled out.", f2),
]
x0 = ov.width + 2 * pad + 4
maxw = zm.width - 8
y = zm.height + pad + 14
for txt, f in paras:
    words, cur = txt.split(" "), ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if d.textlength(trial, font=f) > maxw:
            d.text((x0, y), cur, fill=(235, 235, 235), font=f)
            y += 22 if f is f2 else 28
            cur = wd
        else:
            cur = trial
    d.text((x0, y), cur, fill=(235, 235, 235), font=f)
    y += (22 if f is f2 else 28) + 10
canvas = canvas.crop((0, 0, Wt, max(ov.height + 2 * pad, y + pad)))
canvas.save(out, quality=90)
print(out, canvas.size)
