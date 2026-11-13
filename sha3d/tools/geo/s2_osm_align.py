"""Measure the offset between OSM aeroway centrelines and Sentinel-2 L2A imagery (WGS-84 / UTM 51N).

Usage (run with python3 -I; all paths are arguments):
    python3 -I s2_osm_align.py OSM_DIR S2_SCENE_DIR OUT_JSON [OVERLAY_JPG]

Method
1. Coarse: shift all OSM runway/taxiway centrelines over a +-900 m grid (10 m steps) and score the mean NDVI
   sampled along them (pavement = low NDVI).  The minimum must sit near (0,0) for WGS-84 data and near the
   GCJ-02 shift (+434 m E, -214 m N at ZSSS) for data traced from a GCJ-02 map.
2. Fine: split every runway/taxiway way into straight runs (nodes within 1 m of the chord, >= 120 m), stack
   perpendicular profiles of B04 (red) and B08 (NIR) every 2.5 m (0.25 m sampling, bilinear), take the median
   profile and find its mirror-symmetry centre c (min SSD of m(c+t) vs m(c-t), parabolic sub-sample refinement),
   bootstrap over stations for the uncertainty.  c is the imaged pavement centre relative to the OSM line along
   the run's normal n (n points east), so OSM - S2 along n is -c.
   Least squares over all segments (Huber-weighted) gives (dx, dy) = OSM - S2 in metres E/N; formal errors
   and the scatter between segments are both reported.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from pyproj import Transformer  # noqa: E402
from scipy.ndimage import map_coordinates  # noqa: E402

import glob  # noqa: E402
import osm_load  # noqa: E402

osm_dir, s2_dir, out_json = sys.argv[1:4]
overlay = sys.argv[4] if len(sys.argv) > 4 else None

paths = sorted(glob.glob(os.path.join(osm_dir, "map_*.osm"))) + sorted(glob.glob(os.path.join(osm_dir, "*_full.xml")))
N, W, R = osm_load.load(paths)

ds = {b: rasterio.open(os.path.join(s2_dir, b + ".tif")) for b in ("B02", "B03", "B04", "B08", "TCI")}
T = ds["B08"].transform
epsg = ds["B08"].crs.to_epsg()
tr = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
B = {b: ds[b].read(1).astype(float) for b in ("B02", "B03", "B04", "B08")}
ndvi = (B["B08"] - B["B04"]) / np.maximum(B["B08"] + B["B04"], 1.0)
nir = B["B08"]


def to_pix(E, Nn):
    # pixel-centre convention: map_coordinates index i <-> centre of pixel i
    col = (E - T.c) / T.a - 0.5
    row = (Nn - T.f) / T.e - 0.5
    return row, col


def sample(img, E, Nn):
    r, c = to_pix(np.asarray(E), np.asarray(Nn))
    return map_coordinates(img, [r, c], order=1, mode="nearest")


def way_xy(nds):
    pts = [(N[x][1], N[x][0]) for x in nds if x in N]
    E, Nn = tr.transform([p[0] for p in pts], [p[1] for p in pts])
    return np.array(E), np.array(Nn)


lines = []  # (kind, ref, way_id, E, N, width)
for wid, (nds, t, m) in W.items():
    a = t.get("aeroway")
    if a in ("runway", "taxiway"):
        E, Nn = way_xy(nds)
        if len(E) >= 2:
            w = t.get("width")
            try:
                w = float(w)
            except (TypeError, ValueError):
                w = 60.0 if a == "runway" else 23.0
            lines.append((a, t.get("ref", ""), wid, E, Nn, w))

# ---------- coarse search ----------
pts = []
for a, ref, wid, E, Nn, w in lines:
    for i in range(len(E) - 1):
        L = math.hypot(E[i + 1] - E[i], Nn[i + 1] - Nn[i])
        k = max(2, int(L / 5))
        s = np.linspace(0, 1, k)
        pts.append(np.c_[E[i] + s * (E[i + 1] - E[i]), Nn[i] + s * (Nn[i + 1] - Nn[i])])
P = np.vstack(pts)
shifts = np.arange(-900, 901, 10)
score = np.zeros((len(shifts), len(shifts)))
for iy, sy in enumerate(shifts):
    for ix, sx in enumerate(shifts):
        # sample S2 at OSM position minus candidate offset (offset = OSM - S2)
        score[iy, ix] = sample(ndvi, P[:, 0] - sx, P[:, 1] - sy).mean()
iy, ix = np.unravel_index(np.argmin(score), score.shape)
coarse = dict(dx=float(shifts[ix]), dy=float(shifts[iy]), ndvi_min=float(score[iy, ix]),
              ndvi_at_zero=float(score[len(shifts) // 2, len(shifts) // 2]),
              ndvi_at_gcj=float(score[np.argmin(abs(shifts + 210)), np.argmin(abs(shifts - 430))]),
              ndvi_median=float(np.median(score)))

# ---------- fine: mirror-symmetry centre of stacked cross profiles ----------
def straight_runs(E, Nn, tol=1.0, min_len=120.0):
    runs, i = [], 0
    while i < len(E) - 1:
        j = i + 1
        while j + 1 < len(E):
            p0, p1 = np.array([E[i], Nn[i]]), np.array([E[j + 1], Nn[j + 1]])
            L = np.linalg.norm(p1 - p0)
            u = (p1 - p0) / L
            nn = np.array([-u[1], u[0]])
            dev = max(abs((np.array([E[k], Nn[k]]) - p0) @ nn) for k in range(i, j + 2))
            if dev > tol:
                break
            j += 1
        L = math.hypot(E[j] - E[i], Nn[j] - Nn[i])
        if L >= min_len:
            runs.append((i, j, L))
        i = j
    return runs


def sym_centre(mp, tt, cmax, tau_min=1.0):
    dt = tt[1] - tt[0]
    H = tt[-1]
    taus = np.arange(tau_min, H - cmax, dt)
    best = (None, np.inf)
    cs = np.arange(-cmax, cmax + 1e-9, 0.1)
    ssd = []
    for c in cs:
        a = np.interp(c + taus, tt, mp)
        b = np.interp(c - taus, tt, mp)
        v = np.mean((a - b) ** 2)
        ssd.append(v)
    ssd = np.array(ssd)
    k = int(np.argmin(ssd))
    if 0 < k < len(cs) - 1:  # parabolic refinement
        y0, y1, y2 = ssd[k - 1], ssd[k], ssd[k + 1]
        den = y0 - 2 * y1 + y2
        off = 0.5 * (y0 - y2) / den if den > 0 else 0.0
        c = cs[k] + off * 0.1
    else:
        c = cs[k]
    q = ssd[k] / max(np.var(mp), 1e-9)  # 0 = perfectly symmetric
    return float(c), float(q), (k == 0 or k == len(cs) - 1)


rng = np.random.default_rng(1)
segs = []
for a, ref, wid, E, Nn, w in lines:
    for (i, j, L) in straight_runs(E, Nn):
        p0 = np.array([E[i], Nn[i]])
        u = (np.array([E[j], Nn[j]]) - p0) / L
        n = np.array([-u[1], u[0]])
        if n[0] < 0 or (abs(n[0]) < 1e-9 and n[1] < 0):
            n = -n
        cmax = 12.0
        H = w / 2 + (25.0 if a == "runway" else 12.0) + cmax
        tt = np.arange(-H, H + 1e-9, 0.25)
        st = np.arange(15.0, L - 15.0, 2.5)
        res_b = {}
        for band in ("B04", "B08"):
            prof = np.array([sample(B[band], (p0 + s * u)[0] + tt * n[0], (p0 + s * u)[1] + tt * n[1]) for s in st])
            mp = np.median(prof, axis=0)
            c, q, edge = sym_centre(mp, tt, cmax)
            boots = []
            for _ in range(60):
                idx = rng.integers(0, len(st), len(st))
                cb, _, _ = sym_centre(np.median(prof[idx], axis=0), tt, cmax)
                boots.append(cb)
            centre = mp[np.abs(tt) < w / 4].mean()
            outer = np.r_[mp[np.abs(tt) > H - cmax - 4]].mean()
            res_b[band] = dict(c=c, q=q, at_edge=edge, sd_boot=float(np.std(boots)), contrast=float(centre - outer))
        segs.append(dict(kind=a, ref=ref, way=wid, nodes=[i, j], length=round(L, 1),
                         bearing=round(math.degrees(math.atan2(u[0], u[1])) % 180, 2), n=n.tolist(), bands=res_b))


def seg_ok(s, band):
    r = s["bands"][band]
    return (not r["at_edge"]) and r["q"] < 0.08 and r["sd_boot"] < 2.0 and abs(r["contrast"]) > 150


good = []
for s in segs:
    oks = [b for b in ("B04", "B08") if seg_ok(s, b)]
    if not oks:
        continue
    cs = [s["bands"][b]["c"] for b in oks]
    sd = [s["bands"][b]["sd_boot"] for b in oks]
    if len(cs) == 2 and abs(cs[0] - cs[1]) > 3.0:
        continue  # bands disagree: structure not a clean symmetric pavement
    s["c"] = float(np.mean(cs))
    s["sd"] = float(max(np.mean(sd), 0.3))
    s["bands_used"] = oks
    good.append(s)


def solve(ss):
    A = np.array([s["n"] for s in ss])
    y = -np.array([s["c"] for s in ss])  # OSM - S2 along n
    wts = np.ones(len(ss))
    for _ in range(30):
        Aw = A * wts[:, None]
        x, *_ = np.linalg.lstsq(Aw, y * wts, rcond=None)
        r = y - A @ x
        mad = np.median(abs(r)) * 1.4826 + 1e-6
        k = 1.5 * mad
        wts = np.where(abs(r) <= k, 1.0, np.sqrt(k / abs(r)))
    r = y - A @ x
    dof = max(1, len(ss) - 2)
    s2 = np.sum((wts * r) ** 2) / dof
    cov = np.linalg.inv((A * wts[:, None]).T @ (A * wts[:, None])) * s2
    return dict(dx=float(x[0]), dy=float(x[1]), se_dx=float(math.sqrt(cov[0, 0])), se_dy=float(math.sqrt(cov[1, 1])),
                rms_resid=float(np.sqrt(np.mean(r ** 2))), mad_resid=float(np.median(abs(r)) * 1.4826), n=len(ss),
                resid=[round(float(v), 2) for v in r])


result = dict(scene=os.path.basename(os.path.normpath(s2_dir)), epsg=epsg, coarse=coarse,
              n_runs=len(segs), n_good=len(good))
result["fine_all"] = solve(good)
result["runways"] = [dict(ref=s["ref"], way=s["way"], length=s["length"], bearing_grid=s["bearing"],
                          normal_EN=[round(v, 4) for v in s["n"]],
                          osm_minus_s2_along_normal={b: round(-s["bands"][b]["c"], 2) for b in ("B04", "B08")},
                          sd_boot={b: round(s["bands"][b]["sd_boot"], 2) for b in ("B04", "B08")},
                          asym_q={b: round(s["bands"][b]["q"], 4) for b in ("B04", "B08")})
                     for s in segs if s["kind"] == "runway"]
tw = [s for s in good if s["kind"] == "taxiway"]
result["fine_taxiways_only"] = solve(tw) if len(tw) > 3 else None
ew = [s for s in tw if 60 < s["bearing"] < 120]
result["ew_taxiways_osm_minus_s2_north"] = [dict(ref=s["ref"], way=s["way"], len=s["length"],
                                                 dy=round(-s["c"] / s["n"][1], 2), sd=round(s["sd"], 2)) for s in ew]
if ew:
    v = np.array([-s["c"] / s["n"][1] for s in ew])
    result["ew_taxiways_dy_median"] = float(np.median(v))
    result["ew_taxiways_dy_mean_se"] = [float(v.mean()), float(v.std(ddof=1) / math.sqrt(len(v))) if len(v) > 1 else None]
ns = [s for s in good if s["bearing"] < 20 or s["bearing"] > 160]
if ns:
    v = np.array([-s["c"] / s["n"][0] for s in ns])
    result["ns_features_dx_median"] = float(np.median(v))
    result["ns_features_dx_mean_se"] = [float(v.mean()), float(v.std(ddof=1) / math.sqrt(len(v))) if len(v) > 1 else None]
    result["ns_features"] = [dict(kind=s["kind"], ref=s["ref"], way=s["way"], len=s["length"],
                                  dx=round(-s["c"] / s["n"][0], 2), sd=round(s["sd"], 2)) for s in ns]
result["segments"] = segs
json.dump(result, open(out_json, "w"), indent=1)
print(json.dumps({k: v for k, v in result.items() if k not in ("segments",)}, indent=1))

# ---------- overlay ----------
if overlay:
    from PIL import Image, ImageDraw, ImageFont
    tci = np.moveaxis(ds["TCI"].read(), 0, 2)
    S = 3  # upsample for drawing
    img = Image.fromarray(tci).resize((tci.shape[1] * S, tci.shape[0] * S), Image.NEAREST)
    dr = ImageDraw.Draw(img)

    def pxy(E, Nn):
        r, c = to_pix(np.asarray(E), np.asarray(Nn))
        return list(zip(((c + 0.5) * S).tolist(), ((r + 0.5) * S).tolist()))

    for wid, (nds, t, m) in W.items():
        a = t.get("aeroway")
        if a in ("apron",):
            E, Nn = way_xy(nds)
            dr.line(pxy(E, Nn), fill=(80, 160, 255), width=1)
    for rel in R.values():
        if rel[1].get("aeroway") == "aerodrome":
            for typ, ref, role in rel[0]:
                if typ == "way" and ref in W:
                    E, Nn = way_xy(W[ref][0])
                    dr.line(pxy(E, Nn), fill=(255, 255, 255), width=1)
    for a, ref, wid, E, Nn, w in lines:
        dr.line(pxy(E, Nn), fill=(255, 40, 40) if a == "runway" else (255, 230, 0), width=2 if a == "runway" else 1)
    for nid, (la, lo, t, m) in N.items():
        if t.get("aeroway") in ("parking_position", "holding_position"):
            E, Nn = tr.transform(lo, la)
            (x, y), = pxy([E], [Nn])
            col = (0, 255, 255) if t["aeroway"] == "parking_position" else (255, 0, 255)
            dr.ellipse([x - 2, y - 2, x + 2, y + 2], outline=col)
    # GCJ-02 ghost of the runways, to show what a GCJ-traced map would look like
    from gcj02 import wgs_to_gcj
    for a, ref, wid, E, Nn, w in lines:
        if a != "runway":
            continue
        tinv = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
        lo, la = tinv.transform(E, Nn)
        g = [wgs_to_gcj(y, x) for x, y in zip(lo, la)]
        gE, gN = tr.transform([p[1] for p in g], [p[0] for p in g])
        dr.line(pxy(gE, gN), fill=(255, 0, 255), width=1)
    W_, H_ = img.size
    dr.rectangle([0, H_ - 46, W_, H_], fill=(0, 0, 0))
    txt = (f"Sentinel-2 L2A TCI {result['scene']} (10 m, UTM {epsg}). Contains modified Copernicus Sentinel data 2026. "
           f"OSM (c) OpenStreetMap contributors, ODbL.\n"
           f"red=OSM runways  yellow=OSM taxiways  blue=aprons  white=aerodrome  cyan=stands  magenta dots=holding pts  "
           f"magenta line=runways shifted by GCJ-02 formula.  Fit OSM-S2: dx={result['fine_all']['dx']:+.1f} m, "
           f"dy={result['fine_all']['dy']:+.1f} m")
    dr.multiline_text((6, H_ - 42), txt, fill=(255, 255, 255))
    img.convert("RGB").save(overlay, quality=88)
