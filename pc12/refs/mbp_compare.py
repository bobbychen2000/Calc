"""
refs.mbp_compare -- how far the current model deviates from the Pilatus drawing 190.10.40.432
(PC-12 NGX Model Building Plan, registered by refs/mbp.py).  Emphasis: cockpit glazing and the
forward fuselage.  Read-only with respect to the model (nothing in model/ is changed).

Run from pc12/:
    python3 -m refs.mbp_compare              # analysis + overlays + report (renders re-used when fresh)
    python3 -m refs.mbp_compare --render     # force new Blender renders
    python3 -m refs.mbp_compare --no-render  # skip Blender (vector overlays only)

Outputs
    refs/MBP_COMPARISON.md          report (tracked): our own measurements only -- tables of numbers,
                                    no Pilatus polylines
    out/tmp/compare/*.png           overlays (git-ignored): drawing lines in red over calibrated
                                    Blender/Cycles renders of out/pc12.glb (render/blender_ortho.py,
                                    run in /opt/venv-blender), vector glazing plots, frame sections,
                                    profile-deviation plots
    out/tmp/compare/compare.json    every number in the report (git-ignored)

Sources of the model geometry (all from the current code / GLB, never modified):
    * glazing outlines = zero contours of the model/cockpit_glazing.py signed-distance fields evaluated
      on the lofted OML (model/fuselage.py), i.e. the edge of the hole cut into the skin by
      model/fuselage_parts.openings_field; the GLB glass meshes (glazing_flightdeck) are 10-12 mm larger
      (trim at sdf < +0.010/0.012) and are reported only as a cross-check
    * fuselage OML = model.fuselage control lines / section(x, t)
    * other components = out/pc12.glb (mbp.read_glb) and the model constants
Drawing geometry = refs.mbp.load() (anchor 'spinner': spinner tip at STA 0.39, ground line = WL 0).

Coordinates: x = station aft of the datum, y = butt line (+ starboard), z = water line (ground 0) [m].
Deviations are drawing - model unless stated otherwise; 'signed' loop distances are + where the model
outline lies OUTSIDE the drawing's pane (model pane too big there).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "out" / "tmp" / "compare"
RENDER_DIR = OUT / "render"
REPORT = HERE / "MBP_COMPARISON.md"
GLB = ROOT / "out" / "pc12.glb"

RED = (220, 0, 0, 255)
BLUE = (0, 90, 255, 255)

# =============================================================================================
# 1. Blender renders (calibrated, render/blender_ortho.py)
# =============================================================================================

RENDER_JOBS = {
    # name: job (natural bounds: side x0,x1,z0,z1; top x0,x1,y0,y1; front y0,y1,z0,z1)
    "side_full": dict(view="side_port", bounds=(0.0, 15.2, -0.25, 4.55), px_per_m=150),
    "top_full": dict(view="top", bounds=(0.0, 15.2, -8.45, 8.45), px_per_m=130),
    "front_full": dict(view="front", bounds=(-8.45, 8.45, -0.25, 4.55), px_per_m=140,
                       hide="structure,blade"),
    "side_nose": dict(view="side_port", bounds=(0.2, 4.9, 0.7, 2.95), px_per_m=440),
    "top_nose": dict(view="top", bounds=(0.2, 4.9, -1.0, 1.0), px_per_m=440),
    "side_cockpit": dict(view="side_port", bounds=(2.8, 4.6, 1.8, 2.85), px_per_m=1100),
    "top_cockpit": dict(view="top", bounds=(2.95, 4.55, -0.95, 0.95), px_per_m=1100),
    "front_cockpit": dict(view="front", bounds=(-0.95, 0.95, 1.9, 2.7), px_per_m=1100,
                          hide="structure,propeller,blade"),
}
RENDER_COMMON = dict(style="shaded", samples=8, denoise="fast", glass="tint", bg="white")


def _job_key(job):
    st = GLB.stat()
    blob = json.dumps([job, st.st_size, int(st.st_mtime)], sort_keys=True, default=str)
    return hashlib.sha1(blob.encode()).hexdigest()[:16]


def renders(force=False, skip=False, names=None):
    """-> {name: png path} (sidecar = same name .json).  Re-uses renders whose job key matches."""
    from render import blender_ortho as bo
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    keyf = RENDER_DIR / "_keys.json"
    try:
        keys = json.loads(keyf.read_text())
    except Exception:
        keys = {}
    todo, out = [], {}
    for name, j in RENDER_JOBS.items():
        if names and name not in names:
            continue
        job = dict(RENDER_COMMON, **j, out=str(RENDER_DIR / f"{name}.png"))
        png = Path(job["out"])
        k = _job_key(job)
        fresh = (not force) and png.exists() and png.with_suffix(".json").exists() and keys.get(name) == k
        if fresh or (skip and png.exists()):
            out[name] = png
        elif not skip:
            todo.append((name, job, k))
    if todo:
        t0 = time.time()
        print(f"[compare] Blender: rendering {len(todo)} views ({', '.join(n for n, _, _ in todo)}) ...", flush=True)
        res = bo.render_many([j for _, j, _ in todo], glb=str(GLB))
        for (name, job, k), r in zip(todo, res):
            keys[name] = k
            out[name] = Path(job["out"])
        keyf.write_text(json.dumps(keys, indent=1))
        print(f"[compare] Blender renders done in {time.time() - t0:.0f} s", flush=True)
    return out




# =============================================================================================
# 2. 2-D loop helpers (numpy / scipy / contourpy only)
# =============================================================================================

def _close(P):
    P = np.asarray(P, float)
    return P if np.allclose(P[0], P[-1]) else np.vstack([P, P[:1]])


def densify(P, step):
    P = np.asarray(P, float)
    out = [P[:1]]
    for a, b in zip(P[:-1], P[1:]):
        L = float(np.hypot(*(b - a)))
        n = max(1, int(math.ceil(L / step)))
        t = (np.arange(1, n + 1) / n)[:, None]
        out.append(a + (b - a) * t)
    return np.vstack(out)


def resample_closed(P, ds):
    """Closed loop -> points at (approximately) equal arc length ds (last point != first)."""
    P = _close(P)
    seg = np.hypot(*np.diff(P, axis=0).T)
    s = np.r_[0, np.cumsum(seg)]
    n = max(8, int(round(s[-1] / ds)))
    u = np.linspace(0, s[-1], n, endpoint=False)
    return np.c_[np.interp(u, s, P[:, 0]), np.interp(u, s, P[:, 1])]


def area(P):
    P = _close(P)
    return 0.5 * float(np.sum(P[:-1, 0] * P[1:, 1] - P[1:, 0] * P[:-1, 1]))


def centroid(P):
    P = _close(P)
    a = area(P)
    c = P[:-1, 0] * P[1:, 1] - P[1:, 0] * P[:-1, 1]
    return np.array([np.sum((P[:-1, 0] + P[1:, 0]) * c), np.sum((P[:-1, 1] + P[1:, 1]) * c)]) / (6 * a)


def inside(P, pts):
    from matplotlib.path import Path as MPath
    return MPath(_close(P)).contains_points(np.asarray(pts, float))


def crossings(P, axis, v):
    """Values of the other coordinate where the closed loop P crosses coordinate[axis] == v (sorted)."""
    P = _close(P)
    a, b = P[:-1], P[1:]
    m = ((a[:, axis] - v) * (b[:, axis] - v) <= 0) & (a[:, axis] != b[:, axis])
    t = (v - a[m, axis]) / (b[m, axis] - a[m, axis])
    return np.sort(a[m, 1 - axis] + t * (b[m, 1 - axis] - a[m, 1 - axis]))


def raster_mask(loops, lo, hi, res):
    """Union of closed loops rasterised on a grid (pixel centres lo + (i + 0.5) res)."""
    from matplotlib.path import Path as MPath
    nx = int(math.ceil((hi[0] - lo[0]) / res))
    ny = int(math.ceil((hi[1] - lo[1]) / res))
    gx = lo[0] + (np.arange(nx) + 0.5) * res
    gy = lo[1] + (np.arange(ny) + 0.5) * res
    G = np.stack(np.meshgrid(gx, gy, indexing="ij"), -1).reshape(-1, 2)
    m = np.zeros(len(G), bool)
    for L in loops:
        m |= MPath(_close(L)).contains_points(G)
    return m.reshape(nx, ny), gx, gy


def mask_loop(mask, gx, gy, blur=1.2):
    """Largest outer contour of a boolean mask -> closed loop in the grid's coordinates (the mask is
    Gaussian-blurred by `blur` pixels first so that the 0.5 contour is smooth, not a staircase)."""
    import contourpy
    from scipy import ndimage
    Z = np.pad(mask.astype(float), 1)
    if blur:
        Z = ndimage.gaussian_filter(Z, blur)
    res = gx[1] - gx[0]
    ex = np.r_[gx[0] - res, gx, gx[-1] + res]
    ey = np.r_[gy[0] - res, gy, gy[-1] + res]
    lines = contourpy.contour_generator(x=ey, y=ex, z=Z).lines(0.5)
    L = max(lines, key=lambda l: abs(area(l)))
    return _close(L[:, ::-1])


def union_closed(loops, gap, res=0.001):
    """Union of pane loops with the mullion strip between them filled: morphological closing with a
    disc of radius gap/2 + 4 mm (it also rounds concave corners of the union with that radius)."""
    from scipy import ndimage
    A = np.vstack(loops)
    r = gap / 2 + 0.004
    lo, hi = A.min(0) - r - 5 * res, A.max(0) + r + 5 * res
    m, gx, gy = raster_mask(loops, lo, hi, res)
    dil = ndimage.distance_transform_edt(~m) * res <= r
    clo = ~(ndimage.distance_transform_edt(dil) * res <= r)
    clo |= m
    return mask_loop(clo, gx, gy)


def min_gap(A, B):
    from scipy.spatial import cKDTree
    return float(cKDTree(densify(_close(B), 0.001)).query(densify(_close(A), 0.001))[0].min())


def loop_metrics(M, D, res=0.002):
    """Model loop M vs drawing loop D (same 2-D plane).  Distances in mm."""
    from scipy.spatial import cKDTree
    Md, Dd = densify(_close(M), 0.001), densify(_close(D), 0.001)
    dm = cKDTree(Dd).query(Md)[0]
    dd = cKDTree(Md).query(Dd)[0]
    sgn = np.where(inside(D, Md), -1.0, 1.0)          # + : model outline outside the drawing pane
    allv = np.r_[dm, dd]
    lo = np.minimum(Md.min(0), Dd.min(0)) - 0.01
    hi = np.maximum(Md.max(0), Dd.max(0)) + 0.01
    mm, gx, gy = raster_mask([M], lo, hi, res)
    md, _, _ = raster_mask([D], lo, hi, res)
    inter, uni = (mm & md).sum(), (mm | md).sum()
    cm, cd = centroid(M), centroid(D)
    return dict(max_mm=1000 * float(allv.max()), rms_mm=1000 * float(np.sqrt(np.mean(allv ** 2))),
                mean_mm=1000 * float(allv.mean()), max_model_to_dwg_mm=1000 * float(dm.max()),
                max_dwg_to_model_mm=1000 * float(dd.max()),
                signed_mean_mm=1000 * float(np.mean(sgn * dm)), signed_min_mm=1000 * float(np.min(sgn * dm)),
                signed_max_mm=1000 * float(np.max(sgn * dm)),
                area_model_m2=abs(area(M)), area_dwg_m2=abs(area(D)), iou=float(inter / max(uni, 1)),
                centroid_model=cm.tolist(), centroid_dwg=cd.tolist(), centroid_shift_mm=(1000 * (cd - cm)).tolist())


def circle_fit(P):
    """Algebraic (Kasa) circle fit -> (cx, cy, r, rms residual)."""
    P = np.asarray(P, float)
    A = np.c_[2 * P, np.ones(len(P))]
    b = (P ** 2).sum(1)
    (cx, cy, c), *_ = np.linalg.lstsq(A, b, rcond=None)
    r = math.sqrt(max(c + cx * cx + cy * cy, 0.0))
    res = np.hypot(P[:, 0] - cx, P[:, 1] - cy) - r
    return float(cx), float(cy), float(r), float(np.sqrt(np.mean(res ** 2)))


def corners(P, ds=0.002, rmax=0.30, min_turn_deg=20.0, smooth=7):
    """Rounded corners of a closed loop: runs where the (smoothed) curvature radius < rmax.
    -> list of dict(pos (mid point), r (circle fit to the run's points), turn_deg, centre)."""
    Q = resample_closed(P, ds)
    n = len(Q)
    d = np.roll(Q, -1, 0) - Q
    th = np.unwrap(np.arctan2(d[:, 1], d[:, 0]))
    th = np.r_[th, th[0] + 2 * np.pi * np.sign(th[-1] - th[0] or 1) * round(abs(th[-1] - th[0]) / (2 * np.pi))]
    k = np.diff(th)                                   # turning per sample
    k = np.convolve(np.r_[k[-smooth:], k, k[:smooth]], np.ones(smooth) / smooth, "same")[smooth:-smooth]
    hot = np.abs(k) / ds > 1.0 / rmax
    if hot.all() or not hot.any():
        return []
    start = int(np.argmin(hot))                       # rotate so that index 0 is not in a run
    hot = np.roll(hot, -start)
    Qr = np.roll(Q, -start, 0)
    kr = np.roll(k, -start)
    out = []
    i = 0
    while i < n:
        if not hot[i]:
            i += 1
            continue
        j = i
        while j < n and hot[j]:
            j += 1
        turn = float(np.degrees(np.sum(kr[i:j])))
        if abs(turn) >= min_turn_deg and j - i >= 3:
            pts = Qr[i:j + 1]
            cx, cy, r, rr = circle_fit(pts)
            out.append(dict(pos=pts[len(pts) // 2].tolist(), r=r, turn_deg=turn, centre=[cx, cy], fit_rms=rr,
                            span=[pts[0].tolist(), pts[-1].tolist()]))
        i = j
    return out


def line_fit(u, v):
    """v = a + b u (least squares) -> (a, b, rms)."""
    u, v = np.asarray(u, float), np.asarray(v, float)
    ok = np.isfinite(u) & np.isfinite(v)
    if ok.sum() < 3:
        return None
    b, a = np.polyfit(u[ok], v[ok], 1)
    return float(a), float(b), float(np.sqrt(np.mean((a + b * u[ok] - v[ok]) ** 2)))


# =============================================================================================
# 3. model geometry
# =============================================================================================

VIEW_AX = {"side": (0, 2), "plan": (0, 1), "front": (1, 2)}      # model axes shown in each view


def proj(P3, view):
    return np.asarray(P3)[:, list(VIEW_AX[view])]


def model_glazing(dx=0.002, dt=0.0004):
    """Flight-deck glazing outlines of the model = zero contours of the cockpit_glazing SDFs on the OML.
    -> {'ws_stbd','ws_port','sw_stbd','sw_port','surround'}: (N, 3) closed loops in model coordinates."""
    import contourpy
    from model import fuselage as F
    from model import cockpit_glazing as CG
    from model import fuselage_parts as FP
    xs = np.arange(3.0, 4.6 + 1e-9, dx)
    ts = np.arange(-0.5, 0.5, dt)
    X, T = np.meshgrid(xs, ts, indexing="ij")
    Tm = np.mod(T, 1.0)
    P = F.section(X, Tm)
    x, y, z = P[..., 0], P[..., 1], P[..., 2]
    s = FP.signed_s(x, Tm)
    fields = dict(ws=CG.windshield_sdf(x, s, z, y), sw=CG.sidewindow_sdf(x, y, z), surround=CG.surround_sdf(x, y, z, s))
    out = {}
    for name, f in fields.items():
        lines = contourpy.contour_generator(x=ts, y=xs, z=f).lines(0.0)
        loops = []
        for l in lines:
            if len(l) < 20:
                continue
            Q = F.section(l[:, 1], np.mod(l[:, 0], 1.0))
            loops.append(_close(Q))
        if name == "surround":
            out["surround"] = max(loops, key=len)
            continue
        for Q in loops:
            side = "stbd" if Q[:, 1].mean() > 0 else "port"
            out[f"{name}_{side}"] = Q
    return out


def mesh_outline_2d(V, Fc, view, res=0.002):
    """Outline of the projection of a triangle mesh onto a view plane (rasterised with PIL at res)."""
    from PIL import Image, ImageDraw
    Q = proj(V, view)
    lo = Q.min(0) - 5 * res
    nx, ny = (np.ceil((Q.max(0) - lo) / res) + 5).astype(int)
    im = Image.new("L", (int(nx), int(ny)), 0)
    dr = ImageDraw.Draw(im)
    T = (Q[Fc] - lo) / res
    for t in T:
        dr.polygon([tuple(p) for p in t], fill=255, outline=255)
    m = np.asarray(im).T > 127
    gx = lo[0] + (np.arange(m.shape[0]) + 0.5) * res
    gy = lo[1] + (np.arange(m.shape[1]) + 0.5) * res
    return mask_loop(m, gx, gy)


def glb_glass_outlines(parts=None):
    """Projected outlines of the GLB flight-deck glass meshes (primitive 0 = windshield glass,
    1 = side-window glass) -> {view: {'ws_stbd', 'ws_port', 'sw_stbd', 'sw_port'}} closed 2-D loops."""
    from refs import mbp
    parts = parts or mbp.read_glb(GLB)
    prims = parts.get("glazing_flightdeck", [])
    out = {v: {} for v in VIEW_AX}
    for pi, kind in ((0, "ws"), (1, "sw")):
        if pi >= len(prims):
            continue
        V, Fc = prims[pi]
        cy = V[Fc][:, :, 1].mean(1)
        for side, sel in (("stbd", cy > 0), ("port", cy < 0)):
            for v in VIEW_AX:
                out[v][f"{kind}_{side}"] = mesh_outline_2d(V, Fc[sel], v)
    return out


def slice_parts(parts, names, axis, c):
    from refs import mbp
    P = [mbp.slice_mesh(V, Fc, axis, c) for n in names for V, Fc in parts.get(n, [])]
    P = [p for p in P if len(p)]
    return np.vstack(P) if P else np.zeros((0, 3))


# =============================================================================================
# 4. drawing geometry (registered, model coordinates)
# =============================================================================================

def dwg_lines(d, view, kinds=("outline",), hair=False, min_len=0.0):
    out = []
    for it in d[view]:
        if it["kind"] in kinds and (hair or not it["hair"]):
            P = it["pts"]
            if min_len and np.ptp(P, axis=0).max() < min_len:
                continue
            out.append(P)
    return out


def dwg_crossings(lines, axis, v):
    """Crossings of a set of open polylines with coordinate[axis] == v -> sorted other coordinate."""
    out = []
    for P in lines:
        a, b = P[:-1], P[1:]
        m = ((a[:, axis] - v) * (b[:, axis] - v) <= 0) & (a[:, axis] != b[:, axis])
        t = (v - a[m, axis]) / (b[m, axis] - a[m, axis])
        out.extend(a[m, 1 - axis] + t * (b[m, 1 - axis] - a[m, 1 - axis]))
    return np.sort(np.array(out, float))


def dwg_glazing(d):
    """Drawing glazing loops per view + the NGX port side window as one PRO-equivalent pane
    (side window + DV window + the mullion between them, filled by a morphological closing)."""
    G = {v: {k: _close(P) for k, P in g.items()} for v, g in d["glazing"].items()}
    info = {}
    for v in ("side", "plan", "front"):
        g = G[v]
        if "sw_port" in g and "dv_port" in g:
            gap = min_gap(g["dv_port"], g["sw_port"])
            g["sw_port_union"] = union_closed([g["sw_port"], g["dv_port"]], gap)
            info[f"{v}_mullion_gap_mm"] = 1000 * gap
        if "ws_port" in g and "ws_stbd" in g and v != "side":
            info[f"{v}_centre_post_gap_mm"] = 1000 * min_gap(g["ws_port"], g["ws_stbd"])
    if "ws_port" in G["side"] and "sw_port" in G["side"]:
        info["side_ws_to_sw_gap_mm"] = 1000 * min_gap(G["side"]["ws_port"], G["side"]["sw_port"])
        info["side_ws_to_dv_gap_mm"] = 1000 * min_gap(G["side"]["ws_port"], G["side"]["dv_port"])
    return G, info


def mirror(P, axis_y):
    Q = np.array(P, float)
    Q[:, axis_y] *= -1
    return Q[::-1]


# =============================================================================================
# 5. glazing: features + pane-by-pane comparison
# =============================================================================================

def _edge_pts(L, axis, lo, hi, pick, n=60):
    """Sample one edge of a closed 2-D loop: at n values of coordinate[axis] in [lo, hi] the min or max
    crossing of the other coordinate -> (u, v) arrays."""
    us = np.linspace(lo, hi, n)
    vs = []
    for u in us:
        c = crossings(L, axis, u)
        vs.append((c.min() if pick == "min" else c.max()) if len(c) else np.nan)
    return us, np.array(vs)


def _flat_run(u, v, max_slope):
    """Longest run of an edge sample whose local slope |dv/du| < max_slope (trimmed by 2 samples)."""
    g = np.abs(np.gradient(v, u))
    ok = np.isfinite(g) & (g < max_slope)
    best, cur = (0, 0), None
    for i, o in enumerate(np.r_[ok, False]):
        if o and cur is None:
            cur = i
        elif not o and cur is not None:
            if i - cur > best[1] - best[0]:
                best = (cur, i)
            cur = None
    a, b = best
    a, b = a + 2, b - 2
    return (u[a:b], v[a:b]) if b - a >= 4 else (u[:0], v[:0])


def _corner_named(cs, bb, ax_names):
    """Name corners by their position in the loop's bounding box, e.g. 'fwd-low', 'aft-high'."""
    (x0, y0), (x1, y1) = bb
    out = []
    for c in cs:
        px, py = c["pos"]
        hn = ("fwd" if px < 0.5 * (x0 + x1) else "aft") if ax_names[0] == "x" else ("in" if abs(px) < 0.5 * (abs(x0) + abs(x1)) else "out")
        vn = ("low" if py < 0.5 * (y0 + y1) else "high") if ax_names[1] == "z" else ("in" if abs(py) < 0.5 * (abs(y0) + abs(y1)) else "out")
        out.append(dict(c, name=f"{hn}-{vn}"))
    return out


def features_side_window(L):
    """Side window in side projection (x, z)."""
    L = _close(L)
    (x0, z0), (x1, z1) = L.min(0), L.max(0)
    H = z1 - z0
    f = dict(x_min=x0, x_max=x1, z_min=z0, z_max=z1)
    # A-pillar (front) edge: x = a + b z over the middle 40 % of the height
    zs, xf = _edge_pts(L, 1, z0 + 0.3 * H, z1 - 0.3 * H, "min")
    a, b, r = line_fit(zs, xf)
    f["pillar_x_at_z"] = lambda z, a=a, b=b: a + b * z
    f["pillar_angle_deg"] = math.degrees(math.atan2(1.0, b))
    f["pillar_fit_rms_mm"] = 1000 * r
    # sill and top edge: flat runs of the lower / upper edge
    xs, zb = _edge_pts(L, 0, x0 + 0.01, x1 - 0.01, "min", 120)
    us, vs = _flat_run(xs, zb, 0.25)
    sl = line_fit(us, vs)
    f["sill_z"] = float(np.median(vs)) if len(vs) else z0
    f["sill_slope_deg"] = math.degrees(math.atan(sl[1])) if sl else float("nan")
    f["sill_x_range"] = (float(us.min()), float(us.max())) if len(us) else (np.nan, np.nan)
    xs, zt = _edge_pts(L, 0, x0 + 0.01, x1 - 0.01, "max", 120)
    us, vs = _flat_run(xs, zt, 0.25)
    tl = line_fit(us, vs)
    f["top_line"] = tl
    f["top_x_range"] = (float(us.min()), float(us.max())) if len(us) else (np.nan, np.nan)
    f["top_slope_deg"] = math.degrees(math.atan(tl[1])) if tl else float("nan")
    # sharp-corner equivalents: pillar line with the sill / top line
    if tl:
        # x = a + b z and z = c + m x  ->  z = c + m (a + b z)
        c, m = tl[0], tl[1]
        zt_ = (c + m * a) / (1 - m * b)
        f["corner_top_front"] = (a + b * zt_, zt_)
    zsill = f["sill_z"]
    f["corner_sill_front"] = (a + b * zsill, zsill)
    f["top_z_front"] = f["corner_top_front"][1] if tl else np.nan
    # aft end: extreme station, its WL extent (vertical flat), and height at mid length
    near = L[np.abs(L[:, 0] - x1) < 0.002]
    f["aft_z_range"] = (float(near[:, 1].min()), float(near[:, 1].max()))
    xm = 0.5 * (f["corner_sill_front"][0] + x1)
    c = crossings(L, 0, xm)
    f["height_mid"] = float(c.max() - c.min()) if len(c) >= 2 else np.nan
    f["x_mid"] = xm
    f["corners"] = _corner_named(corners(L), ((x0, z0), (x1, z1)), ("x", "z"))
    f["area_m2"] = abs(area(L))
    # aft end: circle fits to the rounded aft-bottom and aft-top arcs (between the flat sill / top edge
    # and the vertical aft extreme)
    za, zb_ = f["aft_z_range"]
    Q = resample_closed(L, 0.002)
    xs_e = f["sill_x_range"][1] if np.isfinite(f["sill_x_range"][1]) else x1 - 0.3
    xt_e = f["top_x_range"][1] if np.isfinite(f["top_x_range"][1]) else x1 - 0.3
    bot = Q[(Q[:, 0] > xs_e + 0.005) & (Q[:, 1] < za - 0.003) & (Q[:, 1] < 0.5 * (z0 + z1))]
    top = Q[(Q[:, 0] > xt_e + 0.005) & (Q[:, 1] > zb_ + 0.003) & (Q[:, 1] > 0.5 * (z0 + z1))]
    f["aft_bottom_arc"] = circle_fit(bot) if len(bot) > 5 else None
    f["aft_top_arc"] = circle_fit(top) if len(top) > 5 else None
    return f


def features_ws_side(L):
    """Windshield pane in side projection (x, z)."""
    L = _close(L)
    (x0, z0), (x1, z1) = L.min(0), L.max(0)
    H = z1 - z0
    f = dict(x_min=x0, x_max=x1, z_min=z0, z_max=z1)
    f["z_at_x_min"] = float(L[np.argmin(L[:, 0]), 1])
    f["x_at_z_min"] = float(L[np.argmin(L[:, 1]), 0])
    f["x_at_z_max"] = float(L[np.argmax(L[:, 1]), 0])
    zs, xa = _edge_pts(L, 1, z0 + 0.3 * H, z1 - 0.3 * H, "max")
    a, b, r = line_fit(zs, xa)
    f["lower_edge_x_at_z"] = lambda z, a=a, b=b: a + b * z
    f["lower_edge_angle_deg"] = math.degrees(math.atan2(1.0, b))
    f["corners"] = _corner_named(corners(L), ((x0, z0), (x1, z1)), ("x", "z"))
    return f


YS_WS = (0.08, 0.20, 0.30, 0.40, 0.50)


def features_ws_plan(L):
    """Windshield pane in plan (x, y) -- uses |y|."""
    L = _close(L)
    L = np.c_[L[:, 0], np.abs(L[:, 1])]
    f = dict(x_min=L[:, 0].min(), x_max=L[:, 0].max(), ay_min=L[:, 1].min(), ay_max=L[:, 1].max())
    f["x_at_ay_max"] = float(L[np.argmax(L[:, 1]), 0])
    for yv in YS_WS:
        c = crossings(L, 1, yv)
        f[f"fwd_x@{yv}"] = float(c.min()) if len(c) else np.nan
        f[f"aft_x@{yv}"] = float(c.max()) if len(c) else np.nan
    xm = 0.5 * (f["x_min"] + f["x_max"])
    c = crossings(L, 0, xm)
    f["post_half_width"] = float(c.min()) if len(c) else np.nan
    f["corners"] = corners(L)
    return f


def features_ws_front(L):
    """Windshield pane in front view (y, z) -- uses |y|."""
    L = _close(L)
    L = np.c_[np.abs(L[:, 0]), L[:, 1]]
    f = dict(ay_min=L[:, 0].min(), ay_max=L[:, 0].max(), z_min=L[:, 1].min(), z_max=L[:, 1].max())
    for yv in YS_WS:
        c = crossings(L, 0, yv)
        f[f"bot_z@{yv}"] = float(c.min()) if len(c) else np.nan
        f[f"top_z@{yv}"] = float(c.max()) if len(c) else np.nan
    return f


def features_box(L, ax=("x", "y")):
    L = _close(L)
    lo, hi = L.min(0), L.max(0)
    return {f"{ax[0]}_min": lo[0], f"{ax[0]}_max": hi[0], f"{ax[1]}_min": lo[1], f"{ax[1]}_max": hi[1],
            "area_m2": abs(area(L))}


def glazing_analysis(d):
    M3 = model_glazing()
    G, ginfo = dwg_glazing(d)
    try:
        GL = glb_glass_outlines()
    except Exception as e:                               # the GLB is only a cross-check
        GL, ginfo["glb_error"] = {}, repr(e)
    M = {v: {k: proj(P, v) for k, P in M3.items()} for v in VIEW_AX}
    pairs = [  # (view, model pane, drawing pane, label)
        ("side", "ws_port", "ws_port", "Windshield, port pane"),
        ("side", "sw_port", "sw_port_union", "Side window, port (PRO) vs NGX side window + DV + mullion"),
        ("side", "sw_port", "sw_port", "Side window, port vs NGX main pane only (info)"),
        ("plan", "ws_stbd", "ws_stbd", "Windshield, starboard pane"),
        ("plan", "ws_port", "ws_port", "Windshield, port pane"),
        ("plan", "sw_stbd", "sw_stbd", "Side window, starboard (single pane on NGX)"),
        ("plan", "sw_port", "sw_port_union", "Side window, port vs NGX union"),
        ("front", "ws_stbd", "ws_stbd", "Windshield, starboard pane"),
        ("front", "ws_port", "ws_port", "Windshield, port pane"),
        ("front", "sw_stbd", "sw_stbd", "Side window, starboard"),
        ("front", "sw_port", "sw_port_union", "Side window, port vs NGX union"),
    ]
    rows = []
    for v, mk, dk, lab in pairs:
        if mk not in M[v] or dk not in G[v]:
            continue
        r = loop_metrics(M[v][mk], G[v][dk])
        if GL and mk in GL.get(v, {}):
            rg = loop_metrics(GL[v][mk], M[v][mk])
            r["glb_glass_vs_sdf_rms_mm"], r["glb_glass_vs_sdf_max_mm"] = rg["rms_mm"], rg["max_mm"]
        rows.append(dict(view=v, model=mk, dwg=dk, label=lab, **r))
    # symmetry check of the drawing: port pane mirrored onto the starboard pane
    sym = {}
    for v, ay in (("plan", 1), ("front", 0)):
        if "ws_port" in G[v] and "ws_stbd" in G[v]:
            sym[f"{v}_ws"] = loop_metrics(mirror(G[v]["ws_port"], ay), G[v]["ws_stbd"])["max_mm"]
        if "sw_port_union" in G[v] and "sw_stbd" in G[v]:
            sym[f"{v}_sw_union_vs_stbd"] = loop_metrics(mirror(G[v]["sw_port_union"], ay), G[v]["sw_stbd"])["max_mm"]
    # ---------------------------------------------------------------- features
    fe = {}
    fe["sw_side"] = dict(dwg=features_side_window(G["side"]["sw_port_union"]),
                         dwg_main=features_side_window(G["side"]["sw_port"]),
                         model=features_side_window(M["side"]["sw_port"]))
    fe["ws_side"] = dict(dwg=features_ws_side(G["side"]["ws_port"]), model=features_ws_side(M["side"]["ws_port"]))
    fe["ws_plan"] = dict(dwg={k: features_ws_plan(G["plan"][k]) for k in ("ws_stbd", "ws_port")},
                         model={k: features_ws_plan(M["plan"][k]) for k in ("ws_stbd", "ws_port")})
    fe["ws_front"] = dict(dwg={k: features_ws_front(G["front"][k]) for k in ("ws_stbd", "ws_port")},
                          model={k: features_ws_front(M["front"][k]) for k in ("ws_stbd", "ws_port")})
    fe["sw_plan"] = dict(dwg={k: features_box(G["plan"][k]) for k in ("sw_stbd", "sw_port_union")},
                         model={k: features_box(M["plan"][k]) for k in ("sw_stbd", "sw_port")})
    fe["sw_front"] = dict(dwg={k: features_box(G["front"][k], ("y", "z")) for k in ("sw_stbd", "sw_port_union")},
                          model={k: features_box(M["front"][k], ("y", "z")) for k in ("sw_stbd", "sw_port")})
    # A-pillar in side projection.  Drawing (NGX): the pillar-parallel edges are the windshield's lower
    # edge, the DV window's front edge (hypotenuse) and the upper part of the main pane's front edge (its
    # lower part is the DV mullion); model: windshield outer edge and side-window front edge.
    def edge(L, lo, hi, pick):
        zs, xs_ = _edge_pts(_close(L), 1, lo, hi, pick, 40)
        return zs, xs_
    gs = G["side"]
    dv, sw, ws = gs["dv_port"], gs["sw_port"], gs["ws_port"]
    Hdv = np.ptp(dv[:, 1]); Hsw = np.ptp(sw[:, 1]); Hws = np.ptp(ws[:, 1])
    z1, x1 = edge(dv, dv[:, 1].min() + 0.45 * Hdv, dv[:, 1].max() - 0.15 * Hdv, "min")   # above its slanted fwd-low edge
    z2, x2 = edge(sw, sw[:, 1].max() - 0.40 * Hsw, sw[:, 1].max() - 0.12 * Hsw, "min")
    z3, x3 = edge(ws, ws[:, 1].min() + 0.3 * Hws, ws[:, 1].max() - 0.3 * Hws, "max")
    fr_dv, fr_sw, fr_all, fr_ws = line_fit(z1, x1), line_fit(z2, x2), line_fit(np.r_[z1, z2], np.r_[x1, x2]), line_fit(z3, x3)
    ang = lambda fr: math.degrees(math.atan2(1.0, fr[1]))
    zc = 2.30
    pd = dict(z_ref=zc, dv_edge_angle=ang(fr_dv), sw_upper_front_angle=ang(fr_sw), sw_front_angle=ang(fr_all),
              sw_front_fit_rms_mm=1000 * fr_all[2], ws_edge_angle=ang(fr_ws),
              sw_front_x=fr_all[0] + fr_all[1] * zc, ws_edge_x=fr_ws[0] + fr_ws[1] * zc,
              dv_vs_sw_offset_mm=1000 * ((fr_sw[0] + fr_sw[1] * 2.30) - (fr_dv[0] + fr_dv[1] * 2.30)),
              sw_front_line=fr_all[:2], ws_edge_line=fr_ws[:2])
    pd["gap_x"] = pd["sw_front_x"] - pd["ws_edge_x"]
    pd["centre_x"] = 0.5 * (pd["sw_front_x"] + pd["ws_edge_x"])
    fe["sw_side"]["dwg"]["pillar_x_at_z"] = lambda z, a=fr_all[0], b=fr_all[1]: a + b * z
    fe["sw_side"]["dwg"]["pillar_angle_deg"] = pd["sw_front_angle"]
    fe["sw_side"]["dwg"]["pillar_fit_rms_mm"] = pd["sw_front_fit_rms_mm"]
    a_, b_ = fr_all[0], fr_all[1]
    zs_ = fe["sw_side"]["dwg"]["sill_z"]
    fe["sw_side"]["dwg"]["corner_sill_front"] = (a_ + b_ * zs_, zs_)
    tl = fe["sw_side"]["dwg"]["top_line"]
    zt_ = (tl[0] + tl[1] * a_) / (1 - tl[1] * b_)
    fe["sw_side"]["dwg"]["corner_top_front"] = (a_ + b_ * zt_, zt_)
    fe["sw_side"]["dwg"]["top_z_front"] = zt_
    w, s_ = fe["ws_side"]["model"], fe["sw_side"]["model"]
    pm = dict(z_ref=zc, sw_front_angle=s_["pillar_angle_deg"], ws_edge_angle=w["lower_edge_angle_deg"],
              sw_front_x=s_["pillar_x_at_z"](zc), ws_edge_x=w["lower_edge_x_at_z"](zc))
    pm["gap_x"] = pm["sw_front_x"] - pm["ws_edge_x"]
    pm["centre_x"] = 0.5 * (pm["sw_front_x"] + pm["ws_edge_x"])
    fe["pillar"] = dict(dwg=pd, model=pm)
    # centre post (plan + front): gap between the two panes
    for who, src in (("dwg", G), ("model", M)):
        fe.setdefault("post", {})[who] = dict(plan=1000 * min_gap(src["plan"]["ws_port"], src["plan"]["ws_stbd"]),
                                              front=1000 * min_gap(src["front"]["ws_port"], src["front"]["ws_stbd"]))
    return dict(M3=M3, M=M, G=G, GL=GL, info=ginfo, rows=rows, sym=sym, fe=fe)


# =============================================================================================
# 6. fuselage OML: profiles and frame sections
# =============================================================================================

X_PROFILE = np.r_[np.arange(0.40, 1.0, 0.05), np.arange(1.0, 4.61, 0.10), [4.8, 5.0, 5.5, 6.0, 7.0, 8.0, 8.5, 9.0, 9.25, 9.5,
                                                                         9.75, 10.0, 10.5, 11.0, 11.5, 12.0, 12.5, 13.0, 13.5]]


def dwg_spinner(d, xs):
    """Side view: spinner top / bottom silhouette for x < 1.0 (the propeller-disc line excluded)."""
    L = [P for P in dwg_lines(d, "side") if not (np.ptp(P[:, 1]) > 1.5 and np.ptp(P[:, 0]) < 0.2)]
    L = [P for P in L if P[:, 0].min() < 1.05 and P[:, 0].max() > 0.3]
    top, bot = [], []
    for x in xs:
        c = dwg_crossings(L, 0, x)
        c = c[np.abs(c - 1.655) < 0.40]
        top.append(c.max() if len(c) else np.nan)
        bot.append(c.min() if len(c) else np.nan)
    return np.array(top), np.array(bot)


def dwg_plan_spinner(d, xs):
    L = [P for P in dwg_lines(d, "plan") if P[:, 0].min() < 1.05 and P[:, 0].max() > 0.3 and np.ptp(P[:, 1]) < 1.5]
    out = []
    for x in xs:
        c = dwg_crossings(L, 0, x)
        c = c[np.abs(c) < 0.40]
        out.append(0.5 * (c.max() - c.min()) if len(c) >= 2 else np.nan)
    return np.array(out)


def spinner_model(parts, xs):
    """Spinner (GLB part 'propeller' = spinner + hub; blades are separate parts): top, bottom, half-width
    of the slice at each station (NaN outside the spinner)."""
    top, bot, hw = (np.full(len(xs), np.nan) for _ in range(3))
    for i, x in enumerate(xs):
        if x > 0.95:
            continue
        S = slice_parts(parts, ["propeller"], 0, float(x))
        if len(S):
            top[i], bot[i], hw[i] = S[:, 2].max(), S[:, 2].min(), np.abs(S[:, 1]).max()
    return top, bot, hw


def despike(pr, win=9, tol=0.02):
    """Profile (x, v) sampled every 1 cm: replace isolated spikes (panel-joint lines crossing the tracked line,
    e.g. the vertical cowl joint at x 1.03) by the running median."""
    from scipy.ndimage import median_filter
    v = pr[:, 1].copy()
    ok = np.isfinite(v)
    if ok.sum() < win:
        return pr
    med = v.copy()
    med[ok] = median_filter(v[ok], size=win, mode="nearest")
    bad = ok & (np.abs(v - med) > tol)
    v[bad] = med[bad]
    return np.c_[pr[:, 0], v]


def profiles_analysis(d, parts):
    from model import fuselage as F
    pr = d["profiles"]
    xs = X_PROFILE
    pr = {k: despike(v) for k, v in pr.items()}
    it = lambda k: np.interp(xs, pr[k][:, 0], pr[k][:, 1], left=np.nan, right=np.nan)
    crown_d, keel_d, bottom_d = it("side_crown"), it("side_keel"), it("side_bottom")
    hb_d = 0.5 * (it("plan_hb_stbd") - it("plan_hb_port"))
    hb_asym = it("plan_hb_stbd") + it("plan_hb_port")
    sp_t, sp_b = dwg_spinner(d, xs)
    sp_h = dwg_plan_spinner(d, xs)
    nose = xs < 1.0
    crown_d = np.where(nose, sp_t, crown_d)
    keel_d = np.where(nose, sp_b, keel_d)
    bottom_d = np.where(nose, sp_b, bottom_d)
    hb_d = np.where(nose, sp_h, hb_d)
    # model: OML control lines from the cowl front (0.95) aft; the spinner from the GLB 'propeller' part
    crown_m = np.where(xs >= 0.95, F.z_top(np.maximum(xs, 0.95)), np.nan)
    keel_m = np.where(xs >= 0.95, F.z_bot(np.maximum(xs, 0.95)), np.nan)
    hb_m = np.where(xs >= 0.95, F.half_w(np.maximum(xs, 0.95)), np.nan)
    if parts:
        st, sb, sh = spinner_model(parts, xs)
        crown_m = np.where(xs < 0.95, st, crown_m)
        keel_m = np.where(xs < 0.95, sb, keel_m)
        hb_m = np.where(xs < 0.95, sh, hb_m)
    rows = []
    for i, x in enumerate(xs):
        rows.append(dict(x=float(x), crown_dwg=crown_d[i], crown_model=crown_m[i], keel_dwg=keel_d[i],
                         bottom_dwg=bottom_d[i], keel_model=keel_m[i], hb_dwg=hb_d[i], hb_model=hb_m[i],
                         hb_asym_mm=1000 * hb_asym[i] if np.isfinite(hb_asym[i]) else np.nan))
    # dense curves for the plots (1 cm)
    xd = np.arange(0.40, 13.61, 0.01)
    itd = lambda k: np.interp(xd, pr[k][:, 0], pr[k][:, 1], left=np.nan, right=np.nan)
    st, sb = dwg_spinner(d, xd[xd < 1.0])
    dense = dict(x=xd, crown_dwg=np.r_[st, itd("side_crown")[xd >= 1.0]],
                 keel_dwg=np.r_[sb, itd("side_keel")[xd >= 1.0]], bottom_dwg=np.r_[sb, itd("side_bottom")[xd >= 1.0]],
                 hb_dwg=np.r_[dwg_plan_spinner(d, xd[xd < 1.0]), 0.5 * (itd("plan_hb_stbd") - itd("plan_hb_port"))[xd >= 1.0]])
    xm = np.maximum(xd, 0.95)
    dense.update(crown_model=np.where(xd >= 0.95, F.z_top(xm), np.nan), keel_model=np.where(xd >= 0.95, F.z_bot(xm), np.nan),
                 hb_model=np.where(xd >= 0.95, F.half_w(xm), np.nan))
    if parts:
        st, sb, sh = spinner_model(parts, xd)
        for k, v in (("crown_model", st), ("keel_model", sb), ("hb_model", sh)):
            dense[k] = np.where(xd < 0.95, v, dense[k])
    return dict(rows=rows, dense=dense)


SEC_MAIN = ["EF1", "EF2", "FR10", "FR12", "FR14", "FR16-30", "FR33", "FR36", "FR38", "FR40"]
SEC_SHEET2 = ["FR19", "FR21", "FR23", "FR25", "FR27", "FR29", "FR31"]


def _sec_x(rec):
    if rec.get("x") is not None:
        return float(rec["x"])
    if rec.get("x_range"):
        return 6.0                                       # constant cabin section in the model
    return None


def section_body_loop(lines, seed, res=0.002):
    """Closed body contour of a drawn section: flood fill of the outline raster from a seed point."""
    from scipy import ndimage
    A = np.vstack(lines)
    lo, hi = A.min(0) - 0.03, A.max(0) + 0.03
    nx, ny = (np.ceil((hi - lo) / res)).astype(int) + 1
    img = np.zeros((nx, ny), bool)
    for P in lines:
        D = densify(P, res / 3)
        ij = np.round((D - lo) / res).astype(int)
        ok = (ij[:, 0] >= 0) & (ij[:, 0] < nx) & (ij[:, 1] >= 0) & (ij[:, 1] < ny)
        img[ij[ok, 0], ij[ok, 1]] = True
    img = ndimage.binary_dilation(img, iterations=1)
    lab, n = ndimage.label(~img)
    si = np.round((np.asarray(seed) - lo) / res).astype(int)
    k = lab[si[0], si[1]]
    if k == 0:
        return None
    m = lab == k
    if m[0].any() or m[-1].any() or m[:, 0].any() or m[:, -1].any():
        return None                                      # leaks: the outline is not closed
    m = ndimage.binary_dilation(m, iterations=1)         # back onto the stroke centre
    gx = lo[0] + np.arange(nx) * res
    gy = lo[1] + np.arange(ny) * res
    return mask_loop(m, gx, gy, blur=1.0)


def superellipse(zt, zb, hw, zm, nt, nb, n=720):
    t = np.linspace(0, 1, n, endpoint=False)
    a = 2 * np.pi * t
    s, c = np.sin(a), np.cos(a)
    nn = np.where(c >= 0, nt, nb)
    hz = np.where(c >= 0, zt - zm, zm - zb)
    y = hw * np.sign(s) * np.abs(s) ** (2.0 / nn)
    z = zm + hz * np.sign(c) * np.abs(c) ** (2.0 / nn)
    return np.c_[y, z]


def fit_superellipse(L, x_model):
    """Section-law parameters (model.fuselage.section form) that best fit a drawn body contour:
    crown, keel, half-breadth, max-breadth WL, upper / lower exponents (least-squares normal distance)."""
    from scipy.optimize import minimize
    from scipy.spatial import cKDTree
    from model import fuselage as F
    P = resample_closed(L, 0.004)
    tree_pts = P
    c = crossings(L, 0, 0.0)
    zt0, zb0 = (c.max(), c.min()) if len(c) >= 2 else (P[:, 1].max(), P[:, 1].min())
    hw0 = 0.5 * np.ptp(P[:, 0])
    zm0 = float(P[np.argmax(np.abs(P[:, 0])), 1])
    x0 = np.array([zt0, zb0, hw0, zm0, float(F.n_top(x_model)), float(F.n_bot(x_model))])
    tree = cKDTree(tree_pts)

    def J(p):
        zt, zb, hw, zm, nt, nb = p
        if not (zb < zm < zt) or nt < 1.2 or nb < 1.2 or hw <= 0:
            return 1e3
        S = superellipse(zt, zb, hw, zm, nt, nb, 480)
        d1 = tree.query(S)[0]
        d2 = cKDTree(S).query(tree_pts)[0]
        return float(np.mean(d1 ** 2) + np.mean(d2 ** 2))
    r = minimize(J, x0, method="Nelder-Mead", options=dict(xatol=1e-5, fatol=1e-10, maxiter=6000, maxfev=12000))
    zt, zb, hw, zm, nt, nb = r.x
    return dict(crown=zt, keel=zb, hw=hw, zmw=zm, ntop=nt, nbot=nb, rms_mm=1000 * math.sqrt(r.fun / 2))


def sections_analysis(d):
    from model import fuselage as F
    from scipy.spatial import cKDTree
    out = {}
    for name in SEC_MAIN + SEC_SHEET2:
        rec = d["sections"].get(name)
        if rec is None:
            continue
        x = _sec_x(rec)
        if x is None:
            continue
        lines = [l["pts"] for l in rec["lines"] if l["kind"] == "outline" and not l["hair"]]
        phantom = [l["pts"] for l in rec["lines"] if l.get("tag") == "phantom"]
        t = np.linspace(0, 1, 721)
        Msec = F.section(np.full_like(t, x), t)[:, 1:]
        zc = float(F.z_mw(x))
        r = dict(name=name, x=x, sheet=rec.get("sheet", 1), x_range=rec.get("x_range"))
        if name in SEC_SHEET2:
            if phantom:
                A = np.vstack(phantom)
                r.update(keel_dwg=float(A[:, 1].min()), hb_dwg=float(np.abs(A[:, 0]).max()),
                         keel_model=float(F.z_bot(x)), hb_model=float(F.half_w(x)))
            r["lines"] = lines + phantom
            r["model"] = Msec
            out[name] = r
            continue
        body = section_body_loop(lines, (0.0, zc))
        r["lines"] = lines
        r["model"] = Msec
        r["body"] = body
        r["model_params"] = dict(crown=float(F.z_top(x)), keel=float(F.z_bot(x)), hw=float(F.half_w(x)),
                                 zmw=float(F.z_mw(x)), ntop=float(F.n_top(x)), nbot=float(F.n_bot(x)))
        if body is not None:
            B = densify(body, 0.002)
            dm = cKDTree(B).query(densify(Msec, 0.002))[0]
            db = cKDTree(densify(Msec, 0.002)).query(B)[0]
            allv = np.r_[dm, db]
            r.update(max_mm=1000 * allv.max(), rms_mm=1000 * math.sqrt(np.mean(allv ** 2)))
            c = crossings(body, 0, 0.0)
            r["crown_dwg"], r["keel_dwg"] = (float(c.max()), float(c.min())) if len(c) >= 2 else (np.nan, np.nan)
            r["hb_dwg"] = 0.5 * float(np.ptp(body[:, 0]))
            r["zmw_dwg_raw"] = float(body[np.argmax(np.abs(body[:, 0])), 1])
            # half-breadth at fixed WLs (drawing vs model)
            r["hb_at"] = {}
            for zz in (1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4, 2.6):
                cb = crossings(body, 1, zz)
                cm = crossings(Msec, 1, zz)
                r["hb_at"][zz] = (0.5 * float(np.ptp(cb)) if len(cb) >= 2 else np.nan,
                                  0.5 * float(np.ptp(cm)) if len(cm) >= 2 else np.nan)
            try:
                r["fit"] = fit_superellipse(body, x)
            except Exception as e:
                r["fit_error"] = repr(e)
        out[name] = r
    return out


# =============================================================================================
# 7. other components
# =============================================================================================

def _chk(d, prefix):
    for c in d["meta"]["checks"]:
        if c["name"].startswith(prefix):
            return c["measured"]
    return None


def _side_faces(lines, lo, hi, res=0.004, amin=0.02, amax=1.5):
    """Enclosed regions of a set of model-coordinate polylines (x, z) inside the box lo..hi."""
    from scipy import ndimage
    nx, ny = (np.ceil((np.asarray(hi) - lo) / res)).astype(int) + 1
    img = np.zeros((nx, ny), bool)
    for P in lines:
        D = densify(P, res / 3)
        ij = np.round((D - lo) / res).astype(int)
        ok = (ij[:, 0] >= 0) & (ij[:, 0] < nx) & (ij[:, 1] >= 0) & (ij[:, 1] < ny)
        img[ij[ok, 0], ij[ok, 1]] = True
    img = ndimage.binary_dilation(img, iterations=1)
    lab, n = ndimage.label(~img)
    border = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    out = []
    for k in range(1, n + 1):
        if k in border:
            continue
        m = lab == k
        a = m.sum() * res * res
        if amin <= a <= amax:
            ii, jj = np.nonzero(m)
            out.append(dict(x0=lo[0] + ii.min() * res, x1=lo[0] + ii.max() * res, z0=lo[1] + jj.min() * res,
                            z1=lo[1] + jj.max() * res, area=a))
    return out


def other_analysis(d, parts):
    from refs import mbp
    from model import fuselage_parts as FP
    R = []                                               # rows: group, item, model, drawing, note

    def add(group, item, model, dwg, note="", unit="m"):
        dm = None if (model is None or dwg is None or not np.isfinite(model) or not np.isfinite(dwg)) else dwg - model
        R.append(dict(group=group, item=item, model=model, dwg=dwg, delta_mm=None if dm is None else 1000 * dm if unit == "m" else dm,
                      unit=unit, note=note))

    plan = dwg_lines(d, "plan")
    front = dwg_lines(d, "front")
    side = dwg_lines(d, "side")
    wingS = ["wing_R", "flap_R", "aileron_R", "ail_tab_R"]
    wingP = ["wing_L", "flap_L", "aileron_L", "ail_tab_L"]
    # ---------------- wing planform
    for y in (0.95, 2.0, 4.0, 6.0, 7.395):          # (outboard of 7.43 the starboard radar pod interferes)
        le, te = [], []
        for sgn in (1, -1):
            cr = dwg_crossings(plan, 1, sgn * y)
            cr = cr[(cr > 4.0) & (cr < 9.0)]
            if len(cr):
                le.append(cr.min()); te.append(cr.max())
        S = slice_parts(parts, wingS, 1, y)
        if len(S) and le:
            add("Wing", f"LE station at BL {y}", float(S[:, 0].min()), float(np.mean(le)))
            add("Wing", f"TE station at BL {y}", float(S[:, 0].max()), float(np.mean(te)))
            add("Wing", f"chord at BL {y}", float(np.ptp(S[:, 0])), float(np.mean(te) - np.mean(le)))
    ms = d["meta"]
    s_ = ms["scale_m_per_pt"]
    P8 = mbp.processed(verbose=False)
    mp = P8["meas"]["plan"]
    span_d = (mp["port_tip"][0] - mp["stbd_tip"][0]) * s_
    W = np.vstack([V for n in ("winglet_R", "winglet_L", "wing_R", "wing_L") for V, _ in parts.get(n, [])])
    add("Wing", "span over winglets (plan)", float(np.ptp(W[:, 1])), float(span_d), "sheet label 16.114; sourced 16.28")
    WR = np.vstack([V for V, _ in parts.get("winglet_R", [])])
    # winglet in the front view: highest point outboard of BL 7.4
    ztops = []
    for yv in np.arange(7.45, 8.10, 0.01):
        for sgn in (1, -1):
            cz = dwg_crossings(front, 0, sgn * yv)
            cz = cz[(cz > 1.2) & (cz < 2.5)]
            if len(cz):
                ztops.append((cz.max(), yv))
    if ztops:
        zt, yt = max(ztops)
        add("Wing", "winglet top WL (front)", float(WR[:, 2].max()), float(zt))
        add("Wing", "winglet top BL (front)", float(WR[np.argmax(WR[:, 2]), 1]), float(yt))
    # front-view dihedral: straight-line fits of the upper / lower silhouette and of the mid-thickness line over
    # BL 3.5..7.0 (inboard of 3.5 the lower crossings hit the flap-track fairings), both wings averaged
    fitd = {}
    ys_ = np.arange(3.5, 7.01, 0.25)
    for who in ("dwg", "model"):
        acc = {"upper": [], "lower": [], "mid": []}
        for sgn, pn in ((1, wingS), (-1, wingP)):
            lo_, up_ = [], []
            for y in ys_:
                if who == "dwg":
                    c = dwg_crossings(front, 0, sgn * y)
                    c = c[(c > 0.6) & (c < 2.4)]
                    lo_.append(c.min() if len(c) else np.nan); up_.append(c.max() if len(c) else np.nan)
                else:
                    S = slice_parts(parts, pn, 1, sgn * y)
                    lo_.append(S[:, 2].min()); up_.append(S[:, 2].max())
            lo_, up_ = np.array(lo_), np.array(up_)
            for k, v in (("upper", up_), ("lower", lo_), ("mid", 0.5 * (lo_ + up_))):
                ok = np.isfinite(v)
                acc[k].append(math.degrees(math.atan(np.polyfit(ys_[ok], v[ok], 1)[0])))
        fitd[who] = {k: float(np.mean(v)) for k, v in acc.items()}
    for k in ("mid", "upper", "lower"):
        add("Wing", f"front-view slope of the {k}{'-thickness line' if k == 'mid' else ' surface'}, BL 3.5-7.0 [deg]",
            fitd["model"][k], fitd["dwg"][k],
            ("= dihedral; WR dimension line on the sheet: "
             f"{P8['meas']['extra'].get('wr_line_deg', float('nan')):.2f} deg; model dihedral 4.5 deg") if k == "mid" else "", unit="deg")
    # winglet rise above the wing upper surface at BL 7.5
    c = np.r_[dwg_crossings(front, 0, 7.5), dwg_crossings(front, 0, -7.5)]
    c = c[(c > 1.2) & (c < 2.4)]
    S = slice_parts(parts, wingS, 1, 7.5)
    if ztops and len(c) and len(S):
        add("Wing", "winglet top above the wing upper surface at BL 7.5", float(WR[:, 2].max() - S[:, 2].max()), float(zt - c.max()))
    # weather-radar pod (starboard): drawing = leading-edge pod near the tip (plan + front circle)
    pod_p = [P for P in plan if P[:, 0].min() > 5.0 and P[:, 0].max() < 5.7 and P[:, 1].min() > 7.3 and P[:, 1].max() < 7.9]
    pod_f = [P for P in front if P[:, 0].min() > 7.38 and P[:, 0].max() < 7.82 and P[:, 1].min() > 1.55 and P[:, 1].max() < 1.95]
    RP = np.vstack([V for V, _ in parts.get("radar_pod", [])]) if "radar_pod" in parts else None
    if pod_p and pod_f and RP is not None:
        A_ = np.vstack(pod_f)
        add("Wing", "weather-radar pod (starboard): butt line of its axis", float(RP[:, 1].mean()), float(0.5 * (A_[:, 0].min() + A_[:, 0].max())))
        add("Wing", "weather-radar pod: forward tip station", float(RP[:, 0].min()), float(np.vstack(pod_p)[:, 0].min()))
        add("Wing", "weather-radar pod: axis WL", float(0.5 * (RP[:, 2].min() + RP[:, 2].max())), float(0.5 * (A_[:, 1].min() + A_[:, 1].max())))
        add("Wing", "weather-radar pod: diameter (front)", float(np.ptp(RP[:, 2])), float(np.ptp(A_[:, 1])))
    for y in (2.0, 4.0, 6.0):
        c = np.r_[dwg_crossings(front, 0, y), dwg_crossings(front, 0, -y)]
        c = c[(c > 0.6) & (c < 2.4)]
        S = slice_parts(parts, wingS, 1, y)
        if len(c) and len(S):
            add("Wing", f"lower surface WL at BL {y} (front silhouette)", float(S[:, 2].min()), float(c.min()))
    # ---------------- landing gear
    def tyre(names):
        V = np.vstack([Vv for n in names for Vv, _ in parts.get(n, [])])
        lo = V[V[:, 2] < V[:, 2].min() + 0.004]
        return float(lo[:, 0].mean()), float(lo[:, 1].mean())
    xn, _ = tyre(["gear_nose"])
    xmR, ymR = tyre(["gear_main_R"])
    xmL, ymL = tyre(["gear_main_L"])
    add("Landing gear", "nose wheel axle / contact station", xn, _chk(d, "Nose wheel axle station"))
    add("Landing gear", "main wheel axle / contact station", 0.5 * (xmR + xmL), _chk(d, "Main wheel axle station"))
    add("Landing gear", "wheelbase", 0.5 * (xmR + xmL) - xn, _chk(d, "Wheelbase, side"), "sourced 3.48 (POH three-view)")
    add("Landing gear", "track", ymR - ymL, _chk(d, "Track, front"), "sourced 4.53")
    # ---------------- propeller
    pl = np.asarray(P8["meas"]["side"]["prop_line"], float)
    Xs = mbp.Xf(**{k: v for k, v in ms["transforms"]["side"].items() if k in ("A", "b")}, axes=("x", "z"))
    Q = Xs(pl)
    tt = (1.655 - Q[0, 1]) / (Q[1, 1] - Q[0, 1])
    x_disc = Q[0, 0] + tt * (Q[1, 0] - Q[0, 0])
    B = np.vstack([V for n in parts if n.startswith("blade_") for V, _ in parts[n]])
    add("Propeller", "disc station at the prop axis (side)", float(0.5 * (B[:, 0].min() + B[:, 0].max())), float(x_disc),
        "model: mid of the blade x-extent (STA prop_plane 0.80)")
    add("Propeller", "diameter (front circle)", 2.67, _chk(d, "Propeller diameter, front"), "sourced 2.67")
    add("Propeller", "disc centre WL (side)", 1.655, _chk(d, "Propeller disc centre WL"), "model PROP_AXIS_Z")
    add("Propeller", "disc tilt from vertical [deg] (+ top fwd)", 0.0, _chk(d, "Propeller disc tilt"), unit="deg")
    add("Propeller", "spinner max half-width (plan)", float(np.abs(np.vstack([V for V, _ in parts["propeller"]])[:, 1]).max()),
        float(np.nanmax(dwg_plan_spinner(d, np.arange(0.5, 1.0, 0.01)))), "model SPINNER_R 0.29")
    # ---------------- fin / dorsal fin
    finN = ["fin", "rudder", "dorsal_fin", "rudder_tab"]
    for z in (3.0, 3.5, 3.9):
        c = dwg_crossings(side, 1, z)
        c = c[(c > 10.5) & (c < 15.2)]
        S = slice_parts(parts, finN, 2, z)
        if len(c) and len(S):
            add("Fin", f"{'dorsal-fin / fin' if z < 3.2 else 'fin'} LE station at WL {z} (side)", float(S[:, 0].min()), float(c.min()))
            add("Fin", f"TE (rudder) station at WL {z} (side)", float(S[:, 0].max()), float(c.max()))
    for x in (9.25, 9.5, 10.0, 10.5, 11.0, 11.5, 12.0):
        c = dwg_crossings(side, 0, x)
        c = c[(c > 2.0) & (c < 3.6)]
        S = slice_parts(parts, ["fus_aft", "fus_center", "dorsal_fin", "fin", "antennas"], 0, x)
        if len(c) and len(S):
            add("Fin", f"top silhouette WL at x={x} (crown / dorsal fin, side)", float(S[:, 2].max()), float(c.max()))
    # ---------------- tailplane
    tail = ["stabilizer", "elevator_R", "elevator_L"]
    for y in (0.5, 1.0, 2.27, 2.5):
        le, te = [], []
        for sgn in (1, -1):
            cr = dwg_crossings(plan, 1, sgn * y)
            cr = cr[(cr > 12.0) & (cr < 15.3)]
            if len(cr):
                le.append(cr.min()); te.append(cr.max())
        S = slice_parts(parts, tail, 1, y)
        if len(S) and le:
            add("Tailplane", f"LE station at BL {y} (plan)", float(S[:, 0].min()), float(np.mean(le)))
            add("Tailplane", f"TE station at BL {y} (plan)", float(S[:, 0].max()), float(np.mean(te)))
    T = np.vstack([V for n in tail for V, _ in parts.get(n, [])])
    add("Tailplane", "span (plan)", float(np.ptp(T[:, 1])), _chk(d, "Tailplane span, plan"), "sourced 5.20")
    c = dwg_crossings(front, 0, 1.0)
    add("Tailplane", "top WL at BL 1.0 (front)", float(slice_parts(parts, tail, 1, 1.0)[:, 2].max()),
        float(c[c > 3.3].max()) if len(c[c > 3.3]) else None)
    add("Tailplane", "tail-bullet end station (side, lens excluded)", float(np.vstack([V for V, _ in parts["tail_bullet"]])[:, 0].max()),
        _chk(d, "Aft-most station (side"), "overall length 14.40 from the spinner tip 0.39")
    add("Tailplane", "overall height (top of bullet)", float(np.vstack([V for V, _ in parts["tail_bullet"]])[:, 2].max()),
        _chk(d, "Height, side"), "sourced 4.26")
    # ---------------- fuselage openings
    O = d["openings"]["side"]
    for n, o in (("door_airstair", FP.AIRSTAIR), ("door_cargo", FP.CARGO)):
        if n in O:
            P = O[n]
            add("Doors (port)", f"{n}: fwd edge", o["cx"] - o["hx"], float(P[:, 0].min()))
            add("Doors (port)", f"{n}: aft edge", o["cx"] + o["hx"], float(P[:, 0].max()))
            add("Doors (port)", f"{n}: sill WL", o["cz"] - o["hz"], float(P[:, 1].min()))
            add("Doors (port)", f"{n}: top WL", o["cz"] + o["hz"], float(P[:, 1].max()))
    # exit hatch (starboard): starboard detail (sheet 1, top left) and the plan's bump
    det = [it["pts"] for it in d.get("detail_stbd", []) if it["kind"] == "outline" and not it["hair"]]
    ex = [P for P in det if 0.4 < np.ptp(P[:, 0]) < 0.6 and 0.5 < np.ptp(P[:, 1]) < 1.0]
    E = FP.EXIT
    if ex:
        P = ex[0]
        add("Doors (stbd)", "exit hatch: fwd edge", E["cx"] - E["hx"], float(P[:, 0].min()), "starboard detail; plan agrees")
        add("Doors (stbd)", "exit hatch: width", 2 * E["hx"], float(np.ptp(P[:, 0])), "model = Type III minimum 0.51 x 0.91 (Jane's)")
        add("Doors (stbd)", "exit hatch: height", 2 * E["hz"], float(np.ptp(P[:, 1])), "drawing 0.48 x 0.64: confirm with photos")
        add("Doors (stbd)", "exit hatch: aft edge", E["cx"] + E["hx"], float(P[:, 0].max()))
        add("Doors (stbd)", "exit hatch: sill WL", E["cz"] - E["hz"], float(P[:, 1].min()))
        add("Doors (stbd)", "exit hatch: top WL", E["cz"] + E["hz"], float(P[:, 1].max()))
    # cabin windows: plan-view bumps on both sides (0.25-0.40 m long, at |y| 0.70-0.85)
    wins = {1: [], -1: []}
    for P in plan:
        if 0.25 < np.ptp(P[:, 0]) < 0.40 and 0.7 < np.abs(P[:, 1]).min() and np.abs(P[:, 1]).max() < 0.85 \
                and 4.3 < P[:, 0].mean() < 10.0:
            wins[int(np.sign(P[:, 1].mean()))].append((float(P[:, 0].min()), float(P[:, 0].max())))
    win_model = {1: sorted(FP.FIXED_WINDOWS[1] + [FP.DOOR_WINDOWS["exit_hatch"]]),
                 -1: sorted(FP.FIXED_WINDOWS[-1] + [FP.DOOR_WINDOWS["door_airstair"], FP.DOOR_WINDOWS["door_cargo"]])}
    wsum = {}
    for sgn, nm in ((-1, "port"), (1, "stbd")):
        dw = sorted(0.5 * (a + b) for a, b in wins[sgn])
        wsum[nm] = dict(dwg=dw, model=win_model[sgn], dwg_width=[b - a for a, b in sorted(wins[sgn])])
        add("Cabin windows", f"{nm}: number of windows (incl. door / exit windows)", len(win_model[sgn]), len(dw), unit="count")
        for k, xd in enumerate(dw):
            xm = min(win_model[sgn], key=lambda v: abs(v - xd))
            add("Cabin windows", f"{nm}: window {k + 1} centre station (nearest model window)", xm, xd)
    # port side-view window size / height (openings found in the side view)
    wv = [P for k, P in O.items() if k.startswith("cabin_win") or k == "door_cargo_win"]
    if wv:
        add("Cabin windows", "window width (side, mean)", 2 * FP.WIN_HX, float(np.mean([np.ptp(P[:, 0]) for P in wv])))
        add("Cabin windows", "window height (side, mean)", 2 * FP.WIN_HZ, float(np.mean([np.ptp(P[:, 1]) for P in wv])))
        add("Cabin windows", "window sill WL (side, mean)", FP.WIN_CZ - FP.WIN_HZ, float(np.mean([P[:, 1].min() for P in wv])))
        add("Cabin windows", "window top WL (side, mean)", FP.WIN_CZ + FP.WIN_HZ, float(np.mean([P[:, 1].max() for P in wv])))
    return dict(rows=R, windows=wsum)


# =============================================================================================
# 8. overlays
# =============================================================================================

RENDER_VIEW = {"side": "side", "top": "plan", "front": "front"}


def _font(px):
    from PIL import ImageFont
    for f in ("DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, px)
        except Exception:
            pass
    return ImageFont.load_default()


def _caption(im, lines, px=18):
    from PIL import Image, ImageDraw
    f = _font(px)
    h = (px + 6) * len(lines) + 8
    out = Image.new("RGB", (im.width, im.height + h), "white")
    out.paste(im.convert("RGB"), (0, h))
    dr = ImageDraw.Draw(out)
    for i, (t, c) in enumerate(lines):
        dr.text((8, 4 + i * (px + 6)), t, fill=c, font=f)
    return out


def render_overlays(d, A, rend):
    from refs import overlay as ov
    made = []
    for name, png in rend.items():
        kind = name.split("_")[0]
        dv = RENDER_VIEW[kind]
        close = not name.endswith("_full")
        sc = ov.load_sidecar(None, png)
        step = 1.0 if name.endswith("_full") else (0.25 if name.endswith("_nose") else 0.1)
        im = ov.draw_grid(png, sc, None, step=step, color=(0, 150, 60, 70), width=1.0, font_px=12 if close else 11)
        lines = d[dv]
        cl = [it["pts"] for it in lines if it["kind"] == "centerline"]
        hid = [it["pts"] for it in lines if it["kind"] == "hidden"]
        out = [it["pts"] for it in lines if it["kind"] == "outline"]
        lw = 2.0 if close else 1.4
        im = ov.draw_polylines(im, sc, cl, None, color=(220, 0, 0, 110), width=1.0)
        im = ov.draw_polylines(im, sc, hid, None, color=RED, width=lw * 0.8, dash=(6, 4))
        im = ov.draw_polylines(im, sc, out, None, color=RED, width=lw)
        cap = [("Red: Pilatus drawing 190.10.40.432 (PC-12 NGX Model Building Plan), registered by refs/mbp.py "
                "(anchor: spinner tip STA 0.39, ground WL 0)", (200, 0, 0)),
               (f"Background: Blender/Cycles render of out/pc12.glb ({kind} view, render/blender_ortho.py); "
                f"green grid every {step:g} m in model coordinates (x station, y butt line, z water line)", (0, 110, 40))]
        if close and name.endswith("_cockpit"):
            M3 = A["glz"]["M3"]
            ml = [proj(P, dv) for k, P in M3.items() if k != "surround"]
            im = ov.draw_polylines(im, sc, ml, None, color=BLUE, width=1.6, closed=True)
            if dv == "side":
                im = ov.draw_polylines(im, sc, [A["glz"]["G"]["side"]["sw_port_union"]], None, color=(255, 120, 0, 255),
                                       width=1.4, closed=True, dash=(5, 4))
                cap.append(("Blue: model glazing outlines (zero contours of model/cockpit_glazing.py on the OML); orange dashed: "
                            "NGX side window + DV window + mullion as one PRO-equivalent pane", (0, 60, 220)))
            else:
                cap.append(("Blue: model glazing outlines (zero contours of model/cockpit_glazing.py on the OML)", (0, 60, 220)))
        o = OUT / f"overlay_{name}.png"
        _caption(im, cap, 16 if not close else 18).save(o)
        made.append(o)
    return made


def _mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def glazing_plots(d, A, P):
    """Vector plots: drawing panes (red), model panes (blue), GLB glass outline (grey), key lines."""
    plt = _mpl()
    from model import fuselage as F
    g = A["glz"]
    G, M, GL, fe = g["G"], g["M"], g["GL"], g["fe"]
    made = []
    # ---------------------------------------------------------------- side
    fig, ax = plt.subplots(figsize=(15, 8.2))
    xd = P["dense"]["x"]
    ax.plot(xd, P["dense"]["crown_dwg"], color="r", lw=1.0, label="drawing crown line")
    ax.plot(xd, P["dense"]["crown_model"], color="b", lw=1.0, label="model crown z_top(x)")
    for k in ("ws_port", "sw_port", "dv_port"):
        L = G["side"][k]
        ax.plot(L[:, 0], L[:, 1], color="r", lw=1.8, label="drawing panes (NGX, port side)" if k == "ws_port" else None)
    L = G["side"]["sw_port_union"]
    ax.plot(L[:, 0], L[:, 1], color="darkorange", lw=1.2, ls="--", label="drawing SW + DV + mullion (PRO-equivalent)")
    for k in ("ws_port", "sw_port"):
        L = M["side"][k]
        ax.plot(L[:, 0], L[:, 1], color="b", lw=1.8, label="model panes (SDF zero contour)" if k == "ws_port" else None)
        if GL:
            Q = GL["side"][k]
            ax.plot(Q[:, 0], Q[:, 1], color="0.55", lw=0.8, label="model GLB glass outline" if k == "ws_port" else None)
    L = M["side"]["surround"]
    ax.plot(L[:, 0], L[:, 1], color="b", lw=0.7, ls=":", label="model dark surround (surround_sdf)")
    zz = np.array([1.95, 2.62])
    for who, col in (("dwg", "r"), ("model", "b")):
        f = fe["sw_side"][who]["pillar_x_at_z"]
        ax.plot(f(zz), zz, color=col, lw=0.8, ls="-.")
        fs = fe["sw_side"][who]
        ax.axhline(fs["sill_z"], color=col, lw=0.6, ls="--")
        ax.plot([fs["x_max"]] * 2, [1.95, 2.6], color=col, lw=0.6, ls="--")
    fd, fm = fe["sw_side"]["dwg"], fe["sw_side"]["model"]
    txt = (f"side window (port) sill WL: drawing {fd['sill_z']:.3f} (DV {G['side']['dv_port'][:, 1].min():.3f}) | model {fm['sill_z']:.3f}\n"
           f"aft edge station: drawing {fd['x_max']:.3f} | model {fm['x_max']:.3f}\n"
           f"front edge (A-pillar) angle: drawing {fe['pillar']['dwg']['sw_upper_front_angle']:.1f} deg (main pane), DV {fe['pillar']['dwg']['dv_edge_angle']:.1f}, "
           f"windshield edge {fe['pillar']['dwg']['ws_edge_angle']:.1f} | model {fe['pillar']['model']['sw_front_angle']:.1f}\n"
           f"pillar centre x at WL 2.30: drawing {fe['pillar']['dwg']['centre_x']:.3f} | model {fe['pillar']['model']['centre_x']:.3f}")
    ax.text(0.01, 0.99, txt, transform=ax.transAxes, va="top", fontsize=9, family="monospace",
            bbox=dict(fc="white", ec="0.6", alpha=0.9))
    ax.set_xlim(3.0, 4.6); ax.set_ylim(1.9, 2.85); ax.set_aspect("equal"); ax.grid(True, lw=0.3)
    ax.set_xlabel("x station [m]"); ax.set_ylabel("z water line [m]")
    ax.set_title("Cockpit glazing, side view from port: Pilatus drawing (red, NGX) vs model (blue, PRO)")
    ax.legend(loc="lower right", fontsize=8)
    o = OUT / "glazing_side.png"; fig.savefig(o, dpi=130, bbox_inches="tight"); plt.close(fig); made.append(o)
    # ---------------------------------------------------------------- plan
    fig, ax = plt.subplots(figsize=(11, 11))
    ax.plot(xd, P["dense"]["hb_dwg"], color="r", lw=1.0); ax.plot(xd, -P["dense"]["hb_dwg"], color="r", lw=1.0)
    ax.plot(xd, P["dense"]["hb_model"], color="b", lw=1.0); ax.plot(xd, -P["dense"]["hb_model"], color="b", lw=1.0)
    for k, L in G["plan"].items():
        if k == "sw_port_union":
            ax.plot(L[:, 0], L[:, 1], color="darkorange", lw=1.2, ls="--")
        else:
            ax.plot(L[:, 0], L[:, 1], color="r", lw=1.8)
    for k in ("ws_stbd", "ws_port", "sw_stbd", "sw_port"):
        L = M["plan"][k]
        ax.plot(L[:, 0], L[:, 1], color="b", lw=1.8)
        if GL:
            Q = GL["plan"][k]
            ax.plot(Q[:, 0], Q[:, 1], color="0.55", lw=0.8)
    L = M["plan"]["surround"]
    ax.plot(L[:, 0], L[:, 1], color="b", lw=0.7, ls=":")
    wd = fe["ws_plan"]["dwg"]["ws_stbd"]; wm = fe["ws_plan"]["model"]["ws_stbd"]
    txt = ("windshield (plan)         drawing   model\n" +
           "".join(f"fwd edge x @|y|={yv:.2f}   {wd[f'fwd_x@{yv}']:.3f}    {wm[f'fwd_x@{yv}']:.3f}\n" for yv in YS_WS) +
           "".join(f"aft edge x @|y|={yv:.2f}   {wd[f'aft_x@{yv}']:.3f}    {wm[f'aft_x@{yv}']:.3f}\n" for yv in YS_WS) +
           f"max |y|                  {wd['ay_max']:.3f}    {wm['ay_max']:.3f}\n"
           f"centre post width [mm]   {fe['post']['dwg']['plan']:.0f}       {fe['post']['model']['plan']:.0f}")
    ax.text(0.995, 0.5, txt, transform=ax.transAxes, va="center", ha="right", fontsize=8.5, family="monospace",
            bbox=dict(fc="white", ec="0.6", alpha=0.9))
    ax.set_xlim(2.9, 4.95); ax.set_ylim(-0.95, 0.95); ax.set_aspect("equal"); ax.grid(True, lw=0.3)
    ax.invert_yaxis()
    ax.set_xlabel("x station [m]"); ax.set_ylabel("y butt line [m] (+ starboard, drawn downward)")
    ax.set_title("Cockpit glazing, plan view: drawing (red; orange dashed = port SW+DV+mullion) vs model (blue; grey = GLB glass)")
    o = OUT / "glazing_plan.png"; fig.savefig(o, dpi=130, bbox_inches="tight"); plt.close(fig); made.append(o)
    # ---------------------------------------------------------------- front
    fig, ax = plt.subplots(figsize=(13, 7.5))
    for k, L in G["front"].items():
        if k == "sw_port_union":
            ax.plot(L[:, 0], L[:, 1], color="darkorange", lw=1.2, ls="--")
        else:
            ax.plot(L[:, 0], L[:, 1], color="r", lw=1.8)
    for k in ("ws_stbd", "ws_port", "sw_stbd", "sw_port"):
        L = M["front"][k]
        ax.plot(L[:, 0], L[:, 1], color="b", lw=1.8)
    # OML sections at the windshield base / top / side-window aft for context
    for x, ls in ((3.30, ":"), (3.90, "--"), (4.30, "-")):
        t = np.linspace(0, 1, 361)
        S = F.section(np.full_like(t, x), t)
        ax.plot(S[:, 1], S[:, 2], color="b", lw=0.6, ls=ls)
    for n in ("FR12", "FR14"):
        r = A["sec"].get(n)
        if r is not None and r.get("body") is not None:
            ax.plot(r["body"][:, 0], r["body"][:, 1], color="r", lw=0.6, ls="--" if n == "FR12" else "-")
    wd = fe["ws_front"]["dwg"]["ws_stbd"]; wm = fe["ws_front"]["model"]["ws_stbd"]
    txt = ("windshield (front)        drawing   model\n" +
           "".join(f"bottom z @|y|={yv:.2f}     {wd[f'bot_z@{yv}']:.3f}    {wm[f'bot_z@{yv}']:.3f}\n" for yv in YS_WS) +
           "".join(f"top z    @|y|={yv:.2f}     {wd[f'top_z@{yv}']:.3f}    {wm[f'top_z@{yv}']:.3f}\n" for yv in YS_WS))
    ax.text(0.01, 0.99, txt, transform=ax.transAxes, va="top", fontsize=8.5, family="monospace",
            bbox=dict(fc="white", ec="0.6", alpha=0.9))
    ax.set_xlim(0.95, -0.95); ax.set_ylim(1.9, 2.85); ax.set_aspect("equal"); ax.grid(True, lw=0.3)
    ax.set_xlabel("y butt line [m] (starboard on the LEFT, as seen from ahead)"); ax.set_ylabel("z water line [m]")
    ax.set_title("Cockpit glazing, front view: drawing (red) vs model (blue); thin: OML sections "
                 "(model x=3.30 dotted / 3.90 dashed / 4.30 solid; drawing FR12 dashed / FR14 solid)", fontsize=9)
    o = OUT / "glazing_front.png"; fig.savefig(o, dpi=130, bbox_inches="tight"); plt.close(fig); made.append(o)
    return made


def section_plots(A):
    plt = _mpl()
    S = A["sec"]
    names = [n for n in SEC_MAIN if n in S]
    fig, axs = plt.subplots(2, 5, figsize=(22, 10.5))
    for ax, n in zip(axs.ravel(), names):
        r = S[n]
        for L in r["lines"]:
            ax.plot(L[:, 0], L[:, 1], color="r", lw=0.8)
        if r.get("body") is not None:
            B = r["body"]
            ax.plot(B[:, 0], B[:, 1], color="r", lw=1.8)
        Mm = r["model"]
        ax.plot(Mm[:, 0], Mm[:, 1], color="b", lw=1.6)
        if "fit" in r:
            f = r["fit"]
            E = superellipse(f["crown"], f["keel"], f["hw"], f["zmw"], f["ntop"], f["nbot"])
            ax.plot(E[:, 0], E[:, 1], color="g", lw=0.8, ls="--")
        xr = f" (drawn for x {r['x_range'][0]:.2f}..{r['x_range'][1]:.2f}; model at x=6.0)" if r.get("x_range") else ""
        t = f"{n}  x={r['x']:.3f}{xr}"
        if "max_mm" in r:
            mp = r["model_params"]
            t += (f"\nmax {r['max_mm']:.0f} / RMS {r['rms_mm']:.0f} mm; crown {1000 * (r['crown_dwg'] - mp['crown']):+.0f}, "
                  f"keel {1000 * (r['keel_dwg'] - mp['keel']):+.0f}, half-breadth {1000 * (r['hb_dwg'] - mp['hw']):+.0f} mm")
        ax.set_title(t, fontsize=8.5)
        ax.set_aspect("equal"); ax.grid(True, lw=0.3); ax.invert_xaxis()
    fig.suptitle("Frame sections: drawing (red; thick = body contour used), model.fuselage.section(x, t) (blue), "
                 "super-ellipse fit to the drawing (green dashed); y + starboard on the left (seen from ahead), z WL [m]; "
                 "deltas = drawing - model", fontsize=11)
    o = OUT / "sections.png"; fig.tight_layout(rect=(0, 0, 1, 0.96)); fig.savefig(o, dpi=110); plt.close(fig)
    made = [o]
    names2 = [n for n in SEC_SHEET2 if n in S]
    if names2:
        fig, axs = plt.subplots(1, len(names2), figsize=(3.2 * len(names2), 4.2))
        for ax, n in zip(np.atleast_1d(axs), names2):
            r = S[n]
            for L in r["lines"]:
                ax.plot(L[:, 0], L[:, 1], color="r", lw=0.8)
            ax.plot(r["model"][:, 0], r["model"][:, 1], color="b", lw=1.2)
            ax.set_title(f"{n} x={r['x']:.2f}\nkeel {1000 * (r.get('keel_dwg', np.nan) - r.get('keel_model', np.nan)):+.0f} mm", fontsize=8)
            ax.set_aspect("equal"); ax.grid(True, lw=0.3); ax.invert_xaxis(); ax.set_ylim(0.7, 1.9)
        fig.suptitle("Sheet 2 lower-fuselage / wing-root-fairing sections (drawing red incl. the phantom fuselage line; "
                     "model section blue; sheet 2 is +/-15 mm in x, +/-45 mm in z)", fontsize=9)
        o = OUT / "sections_sheet2.png"; fig.tight_layout(); fig.savefig(o, dpi=110); plt.close(fig)
        made.append(o)
    return made


def profile_plots(P):
    plt = _mpl()
    D = P["dense"]
    x = D["x"]
    made = []
    for tag, (x0, x1) in (("nose", (0.35, 4.7)), ("full", (0.35, 13.7))):
        fig, axs = plt.subplots(3, 1, figsize=(15, 11), sharex=True, gridspec_kw=dict(height_ratios=[3, 2, 2]))
        a = axs[0]
        a.plot(x, D["crown_dwg"], "r", lw=1.4, label="drawing crown (side)")
        a.plot(x, D["keel_dwg"], "r", lw=1.4, label="drawing keel (side)")
        a.plot(x, D["bottom_dwg"], "r", lw=0.6, ls=":", label="drawing lowest line (fairing / strake where keel hidden)")
        a.plot(x, D["crown_model"], "b", lw=1.4, label="model z_top / spinner")
        a.plot(x, D["keel_model"], "b", lw=1.4, label="model z_bot / spinner")
        a.plot(x, D["hb_dwg"], "r", lw=1.0, ls="--", label="drawing half-breadth (plan)")
        a.plot(x, D["hb_model"], "b", lw=1.0, ls="--", label="model half_w")
        a.set_ylabel("z or |y| [m]"); a.legend(fontsize=8, ncol=2); a.grid(True, lw=0.3)
        a = axs[1]
        a.plot(x, 1000 * (D["crown_dwg"] - D["crown_model"]), "k", lw=1.2, label="crown")
        a.plot(x, 1000 * (D["keel_dwg"] - D["keel_model"]), "m", lw=1.2, label="keel")
        a.axhline(0, color="0.5", lw=0.5)
        a.set_ylabel("drawing - model [mm]"); a.legend(fontsize=8); a.grid(True, lw=0.3)
        a = axs[2]
        a.plot(x, 1000 * (D["hb_dwg"] - D["hb_model"]), "g", lw=1.2, label="half-breadth")
        a.axhline(0, color="0.5", lw=0.5)
        a.set_ylabel("drawing - model [mm]"); a.legend(fontsize=8); a.grid(True, lw=0.3)
        a.set_xlabel("x station [m]")
        for a in axs:
            a.set_xlim(x0, x1)
            for xs_, lab in ((0.95, "cowl front"), (3.0, "firewall"), (3.08, ""), (4.4, "cockpit aft"), (9.85, "aft bulkhead (model)")):
                if x0 < xs_ < x1:
                    a.axvline(xs_, color="0.7", lw=0.5, ls="--")
        axs[0].set_title(f"Fuselage profiles, drawing (red) vs model (blue) -- {tag}")
        o = OUT / f"profiles_{tag}.png"; fig.tight_layout(); fig.savefig(o, dpi=110); plt.close(fig)
        made.append(o)
    return made


# =============================================================================================
# 9. driver
# =============================================================================================

def analyse():
    from refs import mbp
    t0 = time.time()
    d = mbp.load()
    parts = mbp.read_glb(GLB)
    A = dict(d=d)
    A["glz"] = glazing_analysis(d)
    A["prof"] = profiles_analysis(d, parts)
    A["sec"] = sections_analysis(d)
    A["other"] = other_analysis(d, parts)
    A["meta"] = dict(mbp_anchor=d["meta"]["anchor"], scale=d["meta"]["scale_ratio"], fr10=d["meta"]["fr10_station"],
                     glb=str(GLB.relative_to(ROOT)), glb_mtime=time.strftime("%Y-%m-%d %H:%M", time.localtime(GLB.stat().st_mtime)),
                     seconds=time.time() - t0)
    return A


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python3 -m refs.mbp_compare", description=__doc__.strip().split("\n")[0])
    ap.add_argument("--render", action="store_true", help="force new Blender renders")
    ap.add_argument("--no-render", action="store_true", help="skip the Blender renders / render overlays")
    ap.add_argument("--no-report", action="store_true")
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    A = analyse()
    print(f"[compare] analysis done in {A['meta']['seconds']:.1f} s", flush=True)
    imgs = []
    if not a.no_render:
        try:
            rend = renders(force=a.render)
            imgs += render_overlays(A["d"], A, rend)
        except Exception as e:
            print(f"[compare] Blender renders unavailable: {e!r}", flush=True)
    imgs += glazing_plots(A["d"], A, A["prof"])
    imgs += section_plots(A)
    imgs += profile_plots(A["prof"])
    A["images"] = [str(p.relative_to(ROOT)) for p in imgs]
    if not a.no_report:
        write_report(A)
    print("[compare] images:\n  " + "\n  ".join(A["images"]))
    return A



# =============================================================================================
# 10. report
# =============================================================================================

def _f(v, nd=3):
    if v is None:
        return "-"
    try:
        v = float(v)
    except Exception:
        return str(v)
    return "-" if not np.isfinite(v) else f"{v:.{nd}f}"


def _mm(v, sign=True):
    if v is None:
        return "-"
    v = float(v)
    if not np.isfinite(v):
        return "-"
    return f"{v:+.0f}" if sign else f"{v:.0f}"


def _table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def _crowns(A):
    from model import fuselage as F
    D = A["prof"]["dense"]
    ok = np.isfinite(D["crown_dwg"])
    cd = lambda x: float(np.interp(x, D["x"][ok], D["crown_dwg"][ok]))
    cm = lambda x: float(F.z_top(x))
    return cd, cm


def glazing_feature_rows(A):
    """(feature, drawing, model, delta_mm, delta_rel_crown_mm, controlled by)."""
    fe = A["glz"]["fe"]
    G = A["glz"]["G"]
    cd, cm = _crowns(A)
    ROOF = (4.4, 4.4)            # side-window WLs are referred to the cabin roof crown (drawing 2.769, model 2.630)
    rows = []

    def add(name, dv, mv, ctrl, z_at=None):
        dl = None if dv is None or mv is None else 1000 * (dv - mv)
        rel = None
        if z_at is not None and dl is not None:
            xd, xm = z_at
            rel = 1000 * ((dv - cd(xd)) - (mv - cm(xm)))
        rows.append((name, _f(dv), _f(mv), _mm(dl), _mm(rel), ctrl))

    avg = lambda d, k: 0.5 * (d["ws_stbd"][k] + d["ws_port"][k])
    wpd, wpm = fe["ws_plan"]["dwg"], fe["ws_plan"]["model"]
    wfd, wfm = fe["ws_front"]["dwg"], fe["ws_front"]["model"]
    for yv in (0.08, 0.30, 0.50):
        add(f"Windshield fwd edge (base) station at abs(y)={yv} (plan)", avg(wpd, f"fwd_x@{yv}"), avg(wpm, f"fwd_x@{yv}"),
            "WS_PLAN fwd vertices (x 3.215 / 3.305)")
    for yv in (0.08, 0.30, 0.50):
        add(f"Windshield base WL at abs(y)={yv} (front)", avg(wfd, f"bot_z@{yv}"), avg(wfm, f"bot_z@{yv}"),
            "OML (z_top, n_top) at the base + WS_PLAN", z_at=(avg(wpd, f"fwd_x@{yv}"), avg(wpm, f"fwd_x@{yv}")))
    for yv in (0.08, 0.30, 0.50):
        add(f"Windshield aft (top) edge station at abs(y)={yv} (plan)", avg(wpd, f"aft_x@{yv}"), avg(wpm, f"aft_x@{yv}"),
            "WS_PLAN aft vertices (x 3.832) and PILLAR cut")
    for yv in (0.08, 0.30, 0.50):
        add(f"Windshield top edge WL at abs(y)={yv} (front)", avg(wfd, f"top_z@{yv}"), avg(wfm, f"top_z@{yv}"),
            "OML crown at the aft edge + PILLAR", z_at=(avg(wpd, f"aft_x@{yv}"), avg(wpm, f"aft_x@{yv}")))
    add("Windshield max abs(y) (plan)", avg(wpd, "ay_max"), avg(wpm, "ay_max"), "WS_PLAN outboard vertex (0.565-0.62)")
    add("Windshield station of max abs(y) (plan)", avg(wpd, "x_at_ay_max"), avg(wpm, "x_at_ay_max"), "WS_PLAN outboard vertex")
    wsd, wsm = fe["ws_side"]["dwg"], fe["ws_side"]["model"]
    add("Windshield aft-most station (side; outboard-aft corner)", wsd["x_max"], wsm["x_max"], "PILLAR / WS_PLAN")
    add("Windshield lowest WL (side; outboard-fwd corner)", wsd["z_min"], wsm["z_min"], "WS_PLAN + OML", z_at=(wsd["x_at_z_min"], wsm["x_at_z_min"]))
    add("Windshield highest WL (side)", wsd["z_max"], wsm["z_max"], "OML crown at the aft edge", z_at=(wsd["x_at_z_max"], wsm["x_at_z_max"]))
    add("Centre post width [m] (plan gap between panes)", fe["post"]["dwg"]["plan"] / 1000, fe["post"]["model"]["plan"] / 1000, "2 x WS_POST (0.034)")
    pd, pm = fe["pillar"]["dwg"], fe["pillar"]["model"]
    rows.append(("A-pillar: windshield outer edge angle above horizontal (side) [deg]", _f(pd["ws_edge_angle"], 1),
                 _f(pm["ws_edge_angle"], 1), _f(pd["ws_edge_angle"] - pm["ws_edge_angle"], 1) + " deg", "", "PILLAR slope (45 deg)"))
    rows.append(("A-pillar: side-window front edge angle (side) [deg] (NGX: DV / main pane upper part)",
                 f"{pd['sw_front_angle']:.1f} ({pd['dv_edge_angle']:.1f} / {pd['sw_upper_front_angle']:.1f})",
                 _f(pm["sw_front_angle"], 1), _f(pd["sw_front_angle"] - pm["sw_front_angle"], 1) + " deg", "", "PILLAR slope"))
    add("A-pillar centre-line station at WL 2.30 (side)", pd["centre_x"], pm["centre_x"], "PILLAR (3.30,2.02)-(3.80,2.52)")
    add("A-pillar width in side projection, x-gap at WL 2.30 [m]", pd["gap_x"], pm["gap_x"], "2 x PILLAR_HALF (0.030)")
    sd, sm, sdm = fe["sw_side"]["dwg"], fe["sw_side"]["model"], fe["sw_side"]["dwg_main"]
    add("Side window fwd-most station (side; NGX = DV fwd corner)", sd["x_min"], sm["x_min"], "PILLAR + SW_BOTTOM + smax k")
    add("Side window sill WL (NGX main pane; DV sill below)", sdm["sill_z"], sm["sill_z"], "SW_BOTTOM (1.985)", z_at=ROOF)
    add("Side window sill WL, DV pane (NGX)", float(G["side"]["dv_port"][:, 1].min()), sm["sill_z"], "SW_BOTTOM", z_at=ROOF)
    add("Side window top-front corner station (pillar line x top line)", sd["corner_top_front"][0], sm["corner_top_front"][0], "PILLAR, SW_TOP[0]")
    add("Side window top edge WL at the top-front corner", sd["corner_top_front"][1], sm["corner_top_front"][1], "SW_TOP[0] (2.445)",
        z_at=ROOF)
    tl_d, tl_m = sd["top_line"], sm["top_line"]
    add("Side window top edge WL at x=4.20", tl_d[0] + tl_d[1] * 4.2, tl_m[0] + tl_m[1] * 4.2, "SW_TOP[1] (2.475 @ 4.268)", z_at=ROOF)
    rows.append(("Side window top edge slope [deg] (+ = rising aft)", _f(sd["top_slope_deg"], 1), _f(sm["top_slope_deg"], 1),
                 _f(sd["top_slope_deg"] - sm["top_slope_deg"], 1) + " deg", "", "SW_TOP"))
    add("Side window highest WL", sd["z_max"], sm["z_max"], "SW_TOP / PILLAR", z_at=ROOF)
    add("Side window aft edge station", sd["x_max"], sm["x_max"], "SW_REAR (4.268)")
    add("Side window aft edge: centre of the vertical flat, WL", 0.5 * sum(sd["aft_z_range"]), 0.5 * sum(sm["aft_z_range"]), "SW_BOTTOM/SW_TOP")
    for k, lab in (("aft_bottom_arc", "aft-bottom"), ("aft_top_arc", "aft-top")):
        a_, b_ = sd.get(k), sm.get(k)
        add(f"Side window {lab} corner radius [m]", a_[2] if a_ else None, b_[2] if b_ else None, "smax k=0.05 (no explicit radius)")
    hh = lambda L_: float(np.ptp(crossings(L_, 0, 4.15)))
    add("Side window height at x=4.15 [m]", hh(G["side"]["sw_port_union"]), hh(A["glz"]["M"]["side"]["sw_port"]), "SW_TOP - SW_BOTTOM")
    add("Side window area, side projection [m2]", sd["area_m2"], sm["area_m2"], "all SW_*")
    pdd, pmm = fe["sw_plan"]["dwg"], fe["sw_plan"]["model"]
    add("Side window (stbd) inboard edge abs(y) min (plan)", pdd["sw_stbd"]["y_min"], pmm["sw_stbd"]["y_min"], "SW_TOP on the OML")
    add("Side window (stbd) fwd-most station (plan)", pdd["sw_stbd"]["x_min"], pmm["sw_stbd"]["x_min"], "PILLAR + SW_BOTTOM")
    fdd, fmm = fe["sw_front"]["dwg"], fe["sw_front"]["model"]
    add("Side window (stbd) sill WL (front)", fdd["sw_stbd"]["z_min"], fmm["sw_stbd"]["z_min"], "SW_BOTTOM")
    add("Side window (stbd) top WL (front)", fdd["sw_stbd"]["z_max"], fmm["sw_stbd"]["z_max"], "SW_TOP")
    add("Side window (stbd) inboard abs(y) min (front)", fdd["sw_stbd"]["y_min"], fmm["sw_stbd"]["y_min"], "SW_TOP on the OML")
    return rows


def recommended_glazing(A):
    """Suggested cockpit_glazing.py constants in absolute drawing coordinates (valid once the OML follows
    the drawing; see the report)."""
    fe = A["glz"]["fe"]
    wpd = fe["ws_plan"]["dwg"]
    avg = lambda k: 0.5 * (wpd["ws_stbd"][k] + wpd["ws_port"][k])
    post = fe["post"]["dwg"]["plan"] / 2000.0
    ws_plan = [(avg("fwd_x@0.08"), post)] + [(avg(f"fwd_x@{y}"), y) for y in (0.2, 0.3, 0.4, 0.5)] + \
              [(avg("x_at_ay_max"), avg("ay_max")), (avg("x_max"), 0.5), ] + \
              [(avg(f"aft_x@{y}"), y) for y in (0.4, 0.3, 0.2)] + [(avg("aft_x@0.08"), post)]
    pd = fe["pillar"]["dwg"]
    aw, bw = pd["ws_edge_line"]
    as_, bs = pd["sw_front_line"]
    xc = lambda z: 0.5 * ((aw + bw * z) + (as_ + bs * z))
    pillar = ((xc(2.08), 2.08), (xc(2.58), 2.58))
    sd, sdm = fe["sw_side"]["dwg"], fe["sw_side"]["dwg_main"]
    tl = sd["top_line"]
    x0t = sd["corner_top_front"][0]
    sw_top = ((x0t, tl[0] + tl[1] * x0t), (4.25, tl[0] + tl[1] * 4.25))
    dv_sill = float(A["glz"]["G"]["side"]["dv_port"][:, 1].min())
    return dict(WS_POST=post, WS_PLAN=ws_plan, PILLAR=pillar, PILLAR_HALF=pd["gap_x"] / 2,
                SW_BOTTOM=0.5 * (sdm["sill_z"] + dv_sill), SW_REAR=sd["x_max"], SW_TOP=sw_top,
                R_AFT_BOTTOM=(sd["aft_bottom_arc"] or [0, 0, np.nan])[2], R_AFT_TOP=(sd["aft_top_arc"] or [0, 0, np.nan])[2],
                pillar_angle=0.5 * (pd["ws_edge_angle"] + pd["sw_front_angle"]))


def recommended_oml(A):
    """Suggested control-line values at the model's own control stations, interpolated in a combined drawing
    curve: side / plan profiles where they show the fuselage line, plus the frame-section fits (sheet 1) and the
    sheet-2 phantom keel where the side-view keel is hidden.  Also the section-law parameters of the drawn frames."""
    from model import fuselage as F
    D = A["prof"]["dense"]
    S = A["sec"]
    fits = {n: r for n, r in S.items() if "fit" in r}

    def curve(key, lo, hi, fkey, extra=()):
        x = D["x"]
        v = D[key]
        ok = np.isfinite(v) & (x >= lo) & (x <= hi)
        pts = list(zip(x[ok], v[ok]))
        for n, r in fits.items():
            if n != "FR16-30" and not (lo <= r["x"] <= hi and np.isfinite(np.interp(r["x"], x[ok], v[ok], left=np.nan, right=np.nan))):
                pts.append((r["x"], r["fit"][fkey]))
        pts += list(extra)
        pts.sort()
        return np.array(pts)

    sheet2 = [(r["x"], r["keel_dwg"]) for n, r in S.items() if r.get("sheet") == 2 and "keel_dwg" in r]
    C = {"_top": curve("crown_dwg", 0.95, 9.0, "crown"),
         "_bot": curve("keel_dwg", 0.95, 10.7, "keel", sheet2),
         "_hw": curve("hb_dwg", 0.95, 12.0, "hw")}
    src = {"_top": "side profile to x 9.0, then frames FR36/FR38/FR40", "_bot": "side profile (keel), sheet-2 phantom keel "
           "under the wing fairing, frames FR38/FR40 aft of 10.7", "_hw": "plan profile to x 12.0 (strake tips about 11.7-11.95)"}
    out = {}
    for name, table in (("_top", F._top), ("_bot", F._bot), ("_hw", F._hw)):
        P = C[name]
        rows = []
        for x, v in table:
            k = np.searchsorted(P[:, 0], x)
            gap = min(abs(P[max(k - 1, 0), 0] - x), abs(P[min(k, len(P) - 1), 0] - x))
            nv = float(np.interp(x, P[:, 0], P[:, 1])) if (P[0, 0] - 0.01 <= x <= P[-1, 0] + 0.01 and gap < 0.6) else np.nan
            rows.append((x, v, nv))
        out[name] = dict(rows=rows, source=src[name])
    out["fits"] = [(n, r["x"], r["fit"], r["model_params"]) for n, r in sorted(fits.items(), key=lambda t: t[1]["x"])]
    return out


RANK_NOTES = {
    "tail": ("Aft fuselage / tail cone (FR36-FR40)", "model error",
             "The drawn tail cone starts tapering at about x 9.0 (keel) / 9.3 (half-breadth) and is much slimmer and higher: "
             "at FR40 the body is 0.83 m wide against the model's 1.22 m. The model keeps the full cabin section to its aft "
             "bulkhead at 9.85 m. Re-loft _bot/_hw/_zmw aft of 8.8 m from the FR33..FR40 fits (section 3.4)."),
    "dorsal": ("Dorsal fin / fin leading edge", "model error",
               "The drawing's dorsal fin starts on the crown at about x 9.0 and rises in a straight line to the fin, which "
               "is about 0.13-0.4 m further forward than the model's (see the Fin rows)."),
    "tailplane": ("Tailplane position / planform", "model error",
                  "Drawn LE 0.35-0.58 m and TE 0.23-0.45 m further forward, larger root chord, less LE sweep; the bullet end "
                  "and the span agree."),
    "doors": ("Cargo door, exit hatch, airstair door", "model error",
              "Cargo door 0.66-0.71 m further forward in the drawing, exit hatch 0.7 m further aft and much smaller "
              "(0.48 x 0.64 m against the model's 0.51 x 0.91 m Type III), airstair door 0.24-0.27 m further aft. The airstair "
              "and cargo door sills and tops are 125-190 mm higher, because the cabin sits 139 mm higher; the exit sill is 0.43 m higher."),
    "windows": ("Cabin windows (count, stations, height)", "model error",
                "The drawing has 4 port windows (the 4th in the cargo door; none in the airstair door) and 5 starboard (one in "
                "the exit); 0.30 x 0.38 m, sill WL 1.995. The model has 6 per side, 0.31 x 0.43 m, sill WL 1.795."),
    "windshield": ("Windshield panes", "model error",
                   "The drawn panes are larger: they reach aft to x 3.86 (centre) - 4.00 (outboard) against the model's "
                   "3.76 - 3.50, the base starts 57 mm further aft, and the outboard edge follows a 34 deg A-pillar (model 45)."),
    "sidewindow": ("Cockpit side window", "model error (partly the cabin offset)",
                   "Drawn window (PRO-equivalent) sill 0.10 m higher, starts 0.17 m further aft, ends 0.09 m further aft, "
                   "top edge 0.04-0.09 m higher and sloping down aft, large aft radii (0.21 / 0.12 m). Relative to the "
                   "cabin roof, the drawn window sits 37-97 mm lower than the model's (the cabin itself is 139 mm low)."),
    "cabin_z": ("Cabin vertical position (crown / keel)", "model error",
                "The drawn cabin section has the same 1.83 m height and 1.69 m breadth, but sits 139 mm higher "
                "(crown 2.769, keel 0.939). The keel runs level from the firewall aft, whereas the model's keel drops "
                "from 0.945 at the firewall to 0.800. Prop axis, ground line, tyres, overall height and wing root all agree "
                "within 0-17 mm, so this is not a registration offset."),
    "wing_x": ("Wing fore-and-aft position", "model assumption (LEMAC from the assumed 46 % MAC CG limit)",
               "The drawn LE is 129-168 mm aft of the model's at every butt line, and the TE 131-190 mm; the chords agree within "
               "30 mm. Wheels agree (main axle -2 mm), so it is not an x-registration error (+/-21 mm)."),
    "dihedral": ("Wing dihedral / tip height", "model error or drawing simplification (to confirm with photos)",
                 "The front view's wing surfaces rise about 1.7 deg more steeply than the model's (mid-thickness line "
                 "about 6.2 deg against 4.5 deg; the WR dimension line on the sheet is 5.0 deg). The tip is about 0.24 m higher."),
    "nose": ("Cowling belly and width (x 1.1-2.4)", "model error",
             "The drawn lower cowling is up to 130 mm deeper (keel lower) and up to 105 mm narrower (x 1.2-1.8). "
             "The crown agrees within 10-35 mm."),
    "cockpit_roof": ("Cockpit roof / windshield crown (x 3.1-4.4)", "model error",
                     "The drawn crown kinks up at the windshield base (x 3.15-3.2) and rises in a straight line at about 28 deg to "
                     "the roof at x 4.0-4.4. The model's crown lags 30-75 mm at x 3.2-3.9 and 90-139 mm at x 4.1-4.4. "
                     "The keel is up to 139 mm too low aft of the firewall."),
    "spinner_prop": ("Spinner and propeller plane", "model error",
                     "Drawn spinner max radius 0.245 (model 0.29) with a more pointed profile. Drawn disc plane about 0.1 m further "
                     "aft (x 0.925) and tilted 2 deg (top forward)."),
    "radar": ("Weather-radar pod (small part; lateral position)", "model error (position; confirm with photos)",
              "The drawing shows a leading-edge pod near the starboard tip (BL about 7.6, z 1.76, diameter 0.30); "
              "the model's pod is under the wing at BL 3.9."),
    "span": ("Span over winglets", "drawing / sheet label vs sourced 16.28",
             "The sheet's own label says 16.114 m, and the drawing measures 16.137 m. The sourced Pilatus value is 16.28 m. "
             "Keep 16.28 and treat the difference as a winglet-tip simplification or the older winglet."),
}


def ranking(A):
    other = {r["item"]: r for r in A["other"]["rows"]}
    S = A["sec"]
    rows = A["prof"]["rows"]
    g = lambda k: abs(other[k]["delta_mm"]) if k in other and other[k]["delta_mm"] is not None else 0.0
    out = []

    def add(key, mag, where):
        t, kind, txt = RANK_NOTES[key]
        out.append((mag, t, where, kind, txt))
    tail = max(S[n]["max_mm"] for n in ("FR36", "FR38", "FR40") if n in S and "max_mm" in S[n])
    add("tail", tail, "FR36-FR40 section max distance")
    dors = max(g(k) for k in other if k.startswith("top silhouette WL"))
    add("dorsal", dors, "top silhouette x 9.5-12")
    add("tailplane", max(abs(r["delta_mm"]) for r in A["other"]["rows"] if r["group"] == "Tailplane" and r["delta_mm"] is not None
                         and "station" in r["item"] and "bullet" not in r["item"]), "LE / TE stations")
    add("doors", max(abs(r["delta_mm"]) for r in A["other"]["rows"] if r["group"].startswith("Doors") and r["delta_mm"] is not None),
        "edges / sills")
    wz = [abs(r["delta_mm"]) for r in A["other"]["rows"] if r["group"] == "Cabin windows" and r["unit"] == "m" and r["delta_mm"] is not None]
    add("windows", max(wz) if wz else 0, "window stations / sill")
    wsr = [r for r in A["glz"]["rows"] if r["model"].startswith("ws")]
    add("windshield", max(r["max_mm"] for r in wsr), "pane outline (plan) max distance")
    swr = [r for r in A["glz"]["rows"] if r["dwg"] in ("sw_port_union", "sw_stbd")]
    add("sidewindow", max(r["max_mm"] for r in swr), "pane outline max distance")
    add("cabin_z", abs(1000 * (S["FR16-30"]["crown_dwg"] - S["FR16-30"]["model_params"]["crown"])), "FR16-30 crown and keel")
    add("wing_x", max(abs(r["delta_mm"]) for r in A["other"]["rows"] if r["group"] == "Wing" and "station at BL" in r["item"]
                      and r["delta_mm"] is not None and "7.7" not in r["item"]), "LE / TE stations")
    add("dihedral", g("lower surface WL at BL 6.0 (front silhouette)"), "wing lower surface at BL 6")
    nose = [abs(1000 * (r["keel_dwg"] - r["keel_model"])) for r in rows if 1.2 <= r["x"] <= 2.4 and np.isfinite(r["keel_dwg"] - r["keel_model"])]
    add("nose", max(nose), "keel x 1.2-2.4")
    roof = [abs(1000 * (r[k + "_dwg"] - r[k + "_model"])) for r in rows if 3.1 <= r["x"] <= 4.4 for k in ("crown", "keel")
            if np.isfinite(r[k + "_dwg"] - r[k + "_model"])]
    add("cockpit_roof", max(roof), "crown / keel x 3.1-4.4")
    add("spinner_prop", max(g("disc station at the prop axis (side)"), g("spinner max half-width (plan)")), "disc station")
    rp = [abs(r["delta_mm"]) for r in A["other"]["rows"] if "radar pod" in r["item"] and r["delta_mm"] is not None]
    if rp:
        add("radar", max(rp), "pod butt line")
    add("span", g("span over winglets (plan)"), "plan")
    out.sort(key=lambda t: -t[0])
    return out


def write_report(A):
    import datetime
    L = []
    w = L.append
    meta = A["meta"]
    w("# Model vs Pilatus drawing 190.10.40.432: deviation report")
    w("")
    w(f"Generated by `python3 -m refs.mbp_compare` (from `pc12/`) on {datetime.date.today().isoformat()}. It compares the "
      f"current model (`{meta['glb']}` of {meta['glb_mtime']}, plus the `model/` code it was built from) with the Pilatus "
      "drawing \"PC-12 MODELL ZEICHNUNG / MODEL DRAWING SN2001UP\" (NGX Model Building Plan, sheets 1-2). The drawing is "
      f"registered by `refs/mbp.py` at a scale of 1:{meta['scale']:.3f}, with the anchor on the spinner tip (STA 0.39) and ground = WL 0. "
      "This file contains only our own measurements; the drawing and anything extracted from it stay in the git-ignored "
      "`refs/cache/` and `out/tmp/`. Re-run the script after any model change.")
    w("")
    w("**Conventions.** Coordinates: x = station aft of the datum, y = butt line (+ starboard), z = water line; all in metres. "
      "**Delta = drawing - model**, in mm unless marked. The drawing shows the **NGX**; the model is the **PRO**. The PRO "
      "deletes the pilot's DV window, so the model's port side window is compared with the NGX side window, DV window and "
      "mullion taken together as one pane. That union is built as a morphological closing of the two panes across the "
      "mullion gap.")
    w("")
    w("Images, all in `out/tmp/compare/` (git-ignored). In each one, red = drawing and blue = model.")
    w("- `overlay_{side,top,front}_{full,nose,cockpit}.png`: drawing lines over calibrated Blender/Cycles renders of "
      "the GLB (`render/blender_ortho.py`, run in `/opt/venv-blender`). The cockpit close-ups also show the model's glazing "
      "outlines in blue.")
    w("- `glazing_{side,plan,front}.png`: vector plots of the panes, with the key dimensions tabulated on the plot.")
    w("- `sections.png` / `sections_sheet2.png`: the drawn frame sections over `model.fuselage.section(x, t)`, "
      "with the super-ellipse fit to each drawn frame.")
    w("- `profiles_{nose,full}.png`: crown, keel and half-breadth, plus the deviation curves.")
    w("")
    # ------------------------------------------------------------------ 1 ranking
    w("## 1. Deviations ranked by magnitude")
    w("")
    rk = ranking(A)
    w(_table(["#", "Deviation", "max abs(delta) [mm]", "measured on", "cause", "interpretation"],
             [(i + 1, t, f"{m:.0f}", wh, kind, txt) for i, (m, t, wh, kind, txt) in enumerate(rk)]))
    w("")
    w("**Model error vs drawing.** The drawing agrees with every sourced overall dimension within 0-41 mm: length, "
      "height 4.26, prop diameter 2.67 and clearance, track 4.53, wheelbase, tailplane span 5.20 and tyre sizes. "
      "The only exception is the span, where the sheet itself says 16.114 m. Its frames and dimensions are internally "
      "consistent (see `refs/mbp.py` checks). The large deviations above are therefore model reconstruction errors, "
      "not drawing simplifications. The exceptions are the DV window (NGX vs PRO), the span, and possibly the dihedral.")
    w("")
    # ------------------------------------------------------------------ 2 glazing
    g = A["glz"]
    w("## 2. Cockpit glazing")
    w("")
    w("Model outlines are the zero contours of the `model/cockpit_glazing.py` SDFs on the lofted OML, i.e. the edge of "
      "the skin cut-out. The GLB glass meshes (`glazing_flightdeck`) are trimmed 10-12 mm outside that line; their "
      "projected outlines are shown only as a cross-check (RMS about 10-18 mm from the SDF contour).")
    w("")
    w("### 2.1 Pane-by-pane outline distance")
    w("")
    rows = []
    for r in g["rows"]:
        rows.append((r["view"], r["label"], f"{r['max_mm']:.0f}", f"{r['rms_mm']:.0f}", f"{r['signed_mean_mm']:+.0f}",
                     f"{r['area_model_m2']:.4f} / {r['area_dwg_m2']:.4f}", f"{r['iou']:.2f}",
                     f"{r['centroid_shift_mm'][0]:+.0f}, {r['centroid_shift_mm'][1]:+.0f}",
                     _f(r.get("glb_glass_vs_sdf_rms_mm"), 0)))
    w(_table(["view", "pane (model vs drawing)", "max [mm]", "RMS [mm]", "mean signed [mm]", "area model / drawing [m2]",
              "IoU", "centroid shift dwg-model [mm] (view axes)", "GLB glass vs SDF RMS [mm]"], rows))
    w("")
    w("Max and RMS are symmetric closest-point distances between the two outlines. \"Mean signed\" is positive where the "
      "model outline lies outside the drawn pane. The view axes are side (x, z), plan (x, y) and front (y, z). "
      f"Drawing symmetry checks: the port windshield mirrored onto starboard differs by {g['sym'].get('plan_ws', float('nan')):.1f} mm "
      f"in plan. The port SW+DV union mirrored onto the starboard single pane differs by "
      f"{g['sym'].get('plan_sw_union_vs_stbd', float('nan')):.0f} mm (plan) and "
      f"{g['sym'].get('front_sw_union_vs_stbd', float('nan')):.0f} mm (front). That residual is mostly at the mullion ends, "
      f"where the closing bridges the {g['info'].get('side_mullion_gap_mm', float('nan')):.0f} mm mullion gap.")
    w("")
    w("### 2.2 Key features")
    w("")
    w("The \"delta rel. crown\" column compares WLs measured from the fuselage crown (drawing crown vs model `z_top`), "
      "i.e. the glazing error that remains once the fuselage OML itself is corrected. Windshield WLs use the local crown "
      "at the same station; side-window WLs use the cabin-roof crown at x 4.4 (drawing 2.769, model 2.630).")
    w("")
    w(_table(["feature", "drawing", "model", "delta [mm]", "delta rel. crown [mm]", "controlled by (cockpit_glazing.py / fuselage.py)"],
             glazing_feature_rows(A)))
    w("")
    fe = g["fe"]
    sd, sm = fe["sw_side"]["dwg"], fe["sw_side"]["model"]
    w("Corner radii detected on the outlines (circle fits to runs with a radius below 0.3 m), in metres:")
    w("")
    crow = []
    for lab, f_ in (("side window, drawing (SW+DV union)", sd), ("side window, NGX main pane", fe["sw_side"]["dwg_main"]),
                    ("side window, model", sm), ("windshield side proj., drawing", fe["ws_side"]["dwg"]),
                    ("windshield side proj., model", fe["ws_side"]["model"])):
        cs = [c for c in f_["corners"] if abs(c["turn_deg"]) >= 30]
        crow.append((lab, "; ".join(f"{c['name']} ({c['pos'][0]:.3f}, {c['pos'][1]:.3f}) r={c['r']:.3f}" for c in cs)))
    for lab, key in (("windshield plan, drawing", "dwg"), ("windshield plan, model", "model")):
        cs = [c for c in fe["ws_plan"][key]["ws_stbd"]["corners"] if abs(c["turn_deg"]) >= 30]
        crow.append((lab, "; ".join(f"({c['pos'][0]:.3f}, {c['pos'][1]:.3f}) r={c['r']:.3f}" for c in cs)))
    w(_table(["outline", "corners: position (x, z or x, abs(y)) and radius"], crow))
    w("")
    w("### 2.3 Interpretation")
    w("")
    pd, pm = fe["pillar"]["dwg"], fe["pillar"]["model"]
    cd, cm = _crowns(A)
    w(f"- **A-pillar.** Three edges in the drawing are parallel within 1 deg: the windshield's outer edge "
      f"({pd['ws_edge_angle']:.1f} deg above horizontal in side projection), the DV window's front edge "
      f"({pd['dv_edge_angle']:.1f} deg) and the upper front edge of the main pane ({pd['sw_upper_front_angle']:.1f} deg). "
      f"The model uses 45 deg. At WL 2.30 the drawn pillar centre is at x {pd['centre_x']:.3f} (model {pm['centre_x']:.3f}), and "
      f"its side-projected width is {1000 * pd['gap_x']:.0f} mm (model {1000 * pm['gap_x']:.0f}). "
      f"The DV front edge and the main pane's upper front edge are collinear within {abs(pd['dv_vs_sw_offset_mm']):.0f} mm "
      "at WL 2.30. The PRO pane, which has no DV, can therefore have one straight front edge on this line, as the "
      "photo notes (`refs/photo_notes.md`) describe.")
    w(f"- **Windshield.** The drawn panes are rounded quadrilaterals. The base is arched: x "
      f"{fe['ws_plan']['dwg']['ws_stbd']['fwd_x@0.08']:.3f} at the post and {fe['ws_plan']['dwg']['ws_stbd']['fwd_x@0.5']:.3f} "
      f"at abs(y) 0.5. The aft edge is also arched: x {fe['ws_plan']['dwg']['ws_stbd']['aft_x@0.08']:.3f} at the post and "
      f"{fe['ws_plan']['dwg']['ws_stbd']['aft_x@0.5']:.3f} at abs(y) 0.5. The outboard edge runs along the 34 deg pillar, from "
      f"(x {fe['ws_plan']['dwg']['ws_stbd']['x_at_ay_max']:.3f}, abs(y) {fe['ws_plan']['dwg']['ws_stbd']['ay_max']:.3f}) back to "
      f"(x {fe['ws_side']['dwg']['x_max']:.3f}, abs(y) about 0.50). The model's pane has a straight base at x 3.215, and its 45 deg pillar "
      "cuts the outboard-aft half away. The model pane covers only "
      f"{g['rows'][3]['area_model_m2'] / g['rows'][3]['area_dwg_m2'] * 100:.0f} % of the drawn plan area. "
      f"The centre post is {fe['post']['dwg']['plan']:.0f} mm wide in the drawing and {fe['post']['model']['plan']:.0f} mm in the model. "
      "Seen from ahead, the drawn panes have a nearly level top edge (WL 2.58 to 2.56 out to abs(y) 0.4) and a flat, gently sloping base. "
      "The model's panes are arches, because they follow its lower, more rounded roof.")
    w(f"- **Side window.** The PRO-equivalent drawn pane runs from x {sd['x_min']:.3f} (DV front corner) to "
      f"{sd['x_max']:.3f}. The model's runs from {sm['x_min']:.3f} to {sm['x_max']:.3f}. The drawn sill is at WL {fe['sw_side']['dwg_main']['sill_z']:.3f} "
      f"(DV {float(g['G']['side']['dv_port'][:, 1].min()):.3f}) against the model's {sm['sill_z']:.3f}. The top edge descends aft at "
      f"{-sd['top_slope_deg']:.1f} deg from the pillar corner at WL {sd['corner_top_front'][1]:.3f}, whereas the model's rises "
      f"{sm['top_slope_deg']:.1f} deg. The drawn aft end is a vertical flat at x {sd['x_max']:.3f} (WL {sd['aft_z_range'][0]:.2f}-"
      f"{sd['aft_z_range'][1]:.2f}), blended by an R about {sd['aft_bottom_arc'][2]:.2f} m arc into the sill and an R about "
      f"{sd['aft_top_arc'][2]:.2f} m arc into the top. The model uses about 0.04 m corners. "
      f"Measured from the cabin roof, the drawn sill is {cd(4.4) - fe['sw_side']['dwg_main']['sill_z']:.3f} below the crown and the "
      f"model's {cm(4.4) - sm['sill_z']:.3f}. The drawn top edge at x 4.2 is {cd(4.4) - (sd['top_line'][0] + 4.2 * sd['top_line'][1]):.3f} "
      f"below the crown and the model's {cm(4.4) - (sm['top_line'][0] + 4.2 * sm['top_line'][1]):.3f}. So the drawn sill is "
      f"{1000 * (fe['sw_side']['dwg_main']['sill_z'] - sm['sill_z']):.0f} mm higher in absolute terms because the drawn cabin is "
      f"{1000 * (cd(4.4) - cm(4.4)):.0f} mm higher (section 3). Relative to the cabin, the model's window sits too high by about "
      f"{abs(1000 * ((cm(4.4) - sm['sill_z']) - (cd(4.4) - fe['sw_side']['dwg_main']['sill_z']))):.0f} mm at the sill and "
      f"{abs(1000 * ((cm(4.4) - (sm['top_line'][0] + 4.2 * sm['top_line'][1])) - (cd(4.4) - (sd['top_line'][0] + 4.2 * sd['top_line'][1])))):.0f} mm "
      "at the top edge. The window's fore-aft extent, pillar angle, top-edge slope and aft radii are glazing-definition errors "
      "that do not depend on the OML.")
    w("- **What the drawing does not show.** It has no dark surround trim (`surround_sdf`); the model's trim stays "
      "a styling assumption. The drawing shows the NGX DV window; for the PRO use the union, or the starboard pane mirrored.")
    w("")
    w("### 2.4 Recommended changes to `model/cockpit_glazing.py`")
    w("")
    R = recommended_glazing(A)
    w("These values are in absolute drawing coordinates. They assume the forward-fuselage OML is corrected first "
      "(section 3.4), so that the plan-view polygon and the side-projection lines sit on the drawn surface. If the OML "
      "is **not** changed, lower the z values by the local crown difference (the \"rel. crown\" column above), or the "
      "panes will run off the roof.")
    w("")
    w("```python")
    w(f"WS_POST = {R['WS_POST']:.3f}                  # was 0.034: drawn centre post {2000 * R['WS_POST']:.0f} mm wide")
    w("# pane edge points (x, abs(y)) traced on the drawn plan view: arched base, arched aft edge, and the outboard edge along the")
    w("# pillar.  The corners are rounded (r about 0.035-0.06): implement as sdf2d.rounded_polygon(core inset by r, r) or keep")
    w("# the sharp polygon and round with smax.")
    w("WS_PLAN = [" + ", ".join(f"({x:.3f}, {y:.3f})" for x, y in R["WS_PLAN"]) + "]")
    w(f"PILLAR = (({R['PILLAR'][0][0]:.3f}, {R['PILLAR'][0][1]:.3f}), ({R['PILLAR'][1][0]:.3f}, {R['PILLAR'][1][1]:.3f}))"
      f"   # centre line, {R['pillar_angle']:.1f} deg (was 45 deg)")
    w(f"PILLAR_HALF = {R['PILLAR_HALF']:.3f}           # half the side-projected x-gap between windshield edge and side-window edge")
    w(f"SW_BOTTOM = {R['SW_BOTTOM']:.3f}             # NGX main-pane sill {fe['sw_side']['dwg_main']['sill_z']:.3f}, DV sill "
      f"{float(g['G']['side']['dv_port'][:, 1].min()):.3f} (was 1.985)")
    w(f"SW_REAR = {R['SW_REAR']:.3f}               # was 4.268")
    w(f"SW_TOP = (({R['SW_TOP'][0][0]:.3f}, {R['SW_TOP'][0][1]:.3f}), ({R['SW_TOP'][1][0]:.3f}, {R['SW_TOP'][1][1]:.3f}))"
      f"   # descends aft {-sd['top_slope_deg']:.1f} deg (was rising)")
    w(f"# aft end: vertical flat at SW_REAR, R {R['R_AFT_BOTTOM']:.2f} into the sill, R {R['R_AFT_TOP']:.2f} into the top edge")
    w("# (smax k=0.05 gives about 0.04; use explicit arcs, e.g. a rounded-rectangle SDF for the aft half).")
    w("```")
    w("")
    w("The windshield's lower (base) edge in the front view then follows from the OML. Check it against the "
      "\"Windshield base WL\" rows by re-running this script. `EYE` (the design eye point) should be re-derived after the "
      "roof is raised: the drawn sill is 0.10 m higher.")
    w("")
    # ------------------------------------------------------------------ 3 OML
    w("## 3. Fuselage OML")
    w("")
    w("### 3.1 Side profile and plan half-breadth, x 0.40-4.60 (spinner, cowling, windshield, cockpit roof)")
    w("")
    w("Drawing crown and keel come from the side view (tracked lines; the vertical cowl-joint glitch at x 1.03 is "
      "median-filtered). The half-breadth comes from the plan view, and the spinner (x < 0.95) from the outline crossings. "
      "Model values are `z_top`, `z_bot` and `half_w`, with the GLB spinner forward of 0.95. At x 1.0-1.15 the drawn "
      "\"keel\" is the chin-intake lip; the model's inlet is a separate part (`chin_inlet`).")
    w("")
    rows = []
    for r in A["prof"]["rows"]:
        if r["x"] > 4.61:
            continue
        rows.append((f"{r['x']:.2f}", _f(r["crown_dwg"]), _f(r["crown_model"]), _mm(1000 * (r["crown_dwg"] - r["crown_model"])),
                     _f(r["keel_dwg"]), _f(r["keel_model"]), _mm(1000 * (r["keel_dwg"] - r["keel_model"])),
                     _f(r["hb_dwg"]), _f(r["hb_model"]), _mm(1000 * (r["hb_dwg"] - r["hb_model"]))))
    w(_table(["x", "crown dwg", "crown model", "delta", "keel dwg", "keel model", "delta", "half-br. dwg", "half-br. model", "delta"], rows))
    w("")
    w("### 3.2 Cabin and aft fuselage (x 4.8-13.5)")
    w("")
    w("Keel NaN = hidden in the side view behind the wing-root fairing or the ventral strake; the lowest drawn line is "
      "given in brackets. The crown aft of 9.0 is hidden by the dorsal fin, so see the sections. Half-breadth at x > 11.6 "
      "follows the strake tips and the tailplane root (low reliability).")
    w("")
    rows = []
    for r in A["prof"]["rows"]:
        if r["x"] <= 4.61:
            continue
        kd = _f(r["keel_dwg"]) if np.isfinite(r["keel_dwg"]) else f"- ({_f(r['bottom_dwg'])})"
        rows.append((f"{r['x']:.2f}", _f(r["crown_dwg"]), _f(r["crown_model"]), _mm(1000 * (r["crown_dwg"] - r["crown_model"])),
                     kd, _f(r["keel_model"]), _mm(1000 * (r["keel_dwg"] - r["keel_model"])),
                     _f(r["hb_dwg"]), _f(r["hb_model"]), _mm(1000 * (r["hb_dwg"] - r["hb_model"]))))
    w(_table(["x", "crown dwg", "crown model", "delta", "keel dwg", "keel model", "delta", "half-br. dwg", "half-br. model", "delta"], rows))
    w("")
    w("### 3.3 Frame sections (sheet 1)")
    w("")
    w("Each drawn body contour is the closed region around the section centre; dorsal fin, strakes and intake are "
      "excluded. It is compared with `model.fuselage.section(x, t)` at the labelled station. FR16-30 is drawn as one "
      "section valid from FR16 to FR30 and is compared at x 6.0. Max and RMS are symmetric closest-point distances.")
    w("")
    rows = []
    for n in SEC_MAIN:
        r = A["sec"].get(n)
        if r is None or "max_mm" not in r:
            continue
        mp = r["model_params"]
        rows.append((n, f"{r['x']:.3f}", f"{r['max_mm']:.0f}", f"{r['rms_mm']:.0f}",
                     f"{r['crown_dwg']:.3f} / {mp['crown']:.3f}", _mm(1000 * (r["crown_dwg"] - mp["crown"])),
                     f"{r['keel_dwg']:.3f} / {mp['keel']:.3f}", _mm(1000 * (r["keel_dwg"] - mp["keel"])),
                     f"{r['hb_dwg']:.3f} / {mp['hw']:.3f}", _mm(1000 * (r["hb_dwg"] - mp["hw"]))))
    w(_table(["frame", "x", "max [mm]", "RMS [mm]", "crown dwg / model", "delta", "keel dwg / model", "delta",
              "half-breadth dwg / model", "delta"], rows))
    w("")
    w("Half-breadth at fixed WLs (drawing / model, m):")
    w("")
    zz = (1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4, 2.6)
    rows = []
    for n in SEC_MAIN:
        r = A["sec"].get(n)
        if r is None or "hb_at" not in r:
            continue
        rows.append([n] + [f"{_f(r['hb_at'][z][0])} / {_f(r['hb_at'][z][1])}" for z in zz])
    w(_table(["frame"] + [f"WL {z}" for z in zz], rows))
    w("")
    s2 = [(n, A["sec"][n]) for n in SEC_SHEET2 if n in A["sec"] and "keel_dwg" in A["sec"][n]]
    if s2:
        w("Sheet 2 (FR19-FR31, lower fuselage and wing-root fairing; about +/-15 mm in x and +/-45 mm in z). The phantom "
          "fuselage line gives keel WL " + ", ".join(f"{n} {r['keel_dwg']:.3f}" for n, r in s2) +
          f" against the model's {s2[0][1]['keel_model']:.3f}, and half-breadth {s2[0][1]['hb_dwg']:.3f} against "
          f"{s2[0][1]['hb_model']:.3f}. This confirms the level keel at WL 0.94 along the whole cabin.")
        w("")
    w("### 3.4 Recommended control-line changes (`model/fuselage.py`)")
    w("")
    RO = recommended_oml(A)
    w("Drawing values are interpolated at the model's own control stations. Each control line uses a combined drawing "
      "curve: profiles where they show the fuselage line, otherwise frame sections and the sheet-2 phantom keel. "
      "\"-\" = no drawing information (crown under the dorsal fin aft of FR40, tail cone aft of x 12): re-fair those "
      "points by hand, keeping them consistent with the neighbouring values.")
    w("")
    rows = []
    tabs = {k: {x: (v, nv) for x, v, nv in RO[k]["rows"]} for k in ("_top", "_bot", "_hw")}
    xs_all = sorted(set().union(*[set(t) for t in tabs.values()]))
    for x in xs_all:
        cells = [f"{x:.2f}"]
        for k in ("_top", "_bot", "_hw"):
            if x in tabs[k]:
                v, nv = tabs[k][x]
                cells.append(f"{v:.3f} -> {_f(nv)}" + (f" ({_mm(1000 * (nv - v))})" if np.isfinite(nv) else ""))
            else:
                cells.append("")
        rows.append(cells)
    w(_table(["x", "_top: model -> drawing (delta mm)", "_bot: model -> drawing (delta mm)", "_hw: model -> drawing (delta mm)"], rows))
    w("")
    w("Sources: _top = " + RO["_top"]["source"] + "; _bot = " + RO["_bot"]["source"] + "; _hw = " + RO["_hw"]["source"] +
      ". Additional control points worth adding at the drawn frames are the fit values in the next table "
      "(e.g. FR33 x 9.00, FR36 9.75, FR38 10.80, FR40 11.85).")
    w("")
    w("Section law fitted to the drawn frames (least-squares super-ellipse of the `model.fuselage.section` form; "
      "suggested new `_zmw`, `_ntop`, `_nbot` points at these stations). The fits' crown, keel and half-breadth "
      "should match the control lines above:")
    w("")
    rows = []
    for n, x, f_, mp in RO["fits"]:
        rows.append((n, f"{x:.3f}", f"{f_['crown']:.3f} ({mp['crown']:.3f})", f"{f_['keel']:.3f} ({mp['keel']:.3f})",
                     f"{f_['hw']:.3f} ({mp['hw']:.3f})", f"{f_['zmw']:.3f} ({mp['zmw']:.3f})",
                     f"{f_['ntop']:.2f} ({mp['ntop']:.2f})", f"{f_['nbot']:.2f} ({mp['nbot']:.2f})", f"{f_['rms_mm']:.1f}"))
    w(_table(["frame", "x", "crown (model)", "keel (model)", "half-breadth (model)", "z max-breadth (model)",
              "n top (model)", "n bot (model)", "fit RMS [mm]"], rows))
    w("")
    w("Main points:")
    w("1. **Cabin 139 mm higher.** Set the constant cabin section to crown 2.769 and keel 0.939 (`_top` 2.630 -> 2.769, "
      "`_bot` 0.800 -> 0.939), with `_zmw` about 1.86, `_ntop` about 2.25 and `_nbot` about 3.3 (a flatter floor). The keel runs level at "
      "0.94 from x 2.8 aft, so delete the model's forward keel drop (x 3.0-4.4).")
    w("2. **Windshield crown.** Put the kink at the windshield base (x about 3.15-3.2, WL about 2.20), then a straight "
      "line at about 28 deg to x 4.0 (WL 2.66), and round it into the roof by x 4.4 (WL 2.769). The drawing has no "
      "separate hump over the windshield: the crown line is the windshield.")
    w("3. **Cowling.** Make it narrower at x 1.0-2.0 (half-breadth 0.25-0.51 against 0.31-0.54) and deeper underneath "
      "(keel 1.23 at 1.2 to 1.01 at 2.0). Reduce the spinner radius to about 0.245. The drawn section at EF1 (x 1.2) is "
      "a 0.56 m circle about WL 1.68, with the chin intake below it.")
    w("4. **Tail cone.** Start the taper at about x 8.8 (keel) / 9.2 (half-breadth) instead of 9.85. Use FR36/38/40 "
      "(crown 2.75/2.69/2.61, keel 1.18/1.44/1.73, half-breadth 0.77/0.60/0.41). The cargo door, aft windows, strakes, "
      "dorsal fin and empennage must move with it (section 4).")
    w("5. `STA` markers to update: windshield_base about 3.27 (pane base at the post; crown kink about 3.2), "
      "windshield_top about 3.86 (aft edge at the post), cockpit_aft about 4.4, aft_pressure_bulkhead / tail-cone "
      "start about 9.0 (the drawing shows the taper there, and the cargo door ends at 8.94).")
    w("")
    # ------------------------------------------------------------------ 4 other
    w("## 4. Other components (model vs drawing)")
    w("")
    rows = []
    for r in A["other"]["rows"]:
        u = r["unit"]
        dl = "-" if r["delta_mm"] is None else (f"{r['delta_mm']:+.0f}" if u == "m" else f"{r['delta_mm']:+.2f} {u}")
        nd = 3 if u == "m" else (2 if u == "deg" else 0)
        rows.append((r["group"], r["item"], _f(r["model"], nd), _f(r["dwg"], nd), dl, r["note"]))
    w(_table(["group", "item", "model", "drawing", "delta [mm]", "note"], rows))
    w("")
    wn = A["other"]["windows"]
    w(f"Cabin-window centre stations. Port: drawing {', '.join(f'{v:.2f}' for v in wn['port']['dwg'])} (the last one in "
      f"the cargo door) against model {', '.join(f'{v:.2f}' for v in wn['port']['model'])} (the first in the airstair "
      f"door, the last in the cargo door). Starboard: drawing {', '.join(f'{v:.2f}' for v in wn['stbd']['dwg'])} (the "
      f"second in the exit hatch) against model {', '.join(f'{v:.2f}' for v in wn['stbd']['model'])} (the second in the "
      "exit). The sheet-1 starboard detail repeats the port stations; the plan is used here (see the `refs/mbp.py` notes).")
    w("")
    w("Interpretation and recommendations:")
    w("- **Wing.** Move it 0.13-0.17 m aft (LEMAC about 5.47 instead of 5.323; the drawing's chords match the model's "
      "within 30 mm). This conflicts with the assumed 46 % MAC CG limit, so re-check that assumption against the POH "
      "before moving the wing. Dihedral: the front view suggests about 6.2 deg (the sheet's WR line says 5.0). Confirm "
      "with a straight-on photo before changing 4.5.")
    w("- **Empennage.** Tailplane LE 0.35-0.58 m further forward with a larger root chord, fin and rudder 0.13-0.40 m "
      "further forward, and a long straight dorsal fin from about x 9.0. The tail-bullet end, the tail height and the "
      "tailplane span agree.")
    w("- **Openings.** Airstair door 4.65-5.29, cargo door 7.54-8.94, both sills at WL 1.23-1.25 and tops at 2.63. "
      "Starboard exit hatch 5.96-6.45 x WL 1.88-2.52. Windows 0.30 x 0.38 m with the sill at WL 1.995. All of these "
      "sit with the cabin 139 mm higher.")
    w("- **Propeller.** Disc plane about 0.925 at the axis, tilted 2 deg (top forward), which implies a slight "
      "nose-down thrust line. Spinner radius about 0.245.")
    w("- **Radar pod.** Starboard wing leading edge near the tip (BL about 7.6), not at BL 3.9.")
    w("")
    # ------------------------------------------------------------------ 5 caveats
    w("## 5. Method and caveats")
    w("")
    w("- Registration accuracy (from `refs/mbp.py`): scale residual below 0.05 mm on the sheet. The x anchor carries "
      "+/-21 mm (spinner vs tail anchor). z = ground line; the prop centre comes out 14 mm high. Sheet 2 is about "
      "+/-15 mm in x and +/-45 mm in z. Wing and fin section registration is weaker (see the `refs/mbp.py` verifier notes).")
    w("- The drawing's glazing loops are enclosed regions of the drawn strokes (stroke centre lines), so they are "
      "accurate to about 1-2 mm on the sheet scale.")
    w("- The PRO port pane is taken as the union of the NGX side window, DV window and mullion (morphological closing, "
      f"radius = half the {A['glz']['info'].get('side_mullion_gap_mm', float('nan')):.0f} mm mullion gap + 4 mm). The union's "
      "concave corners are therefore rounded at about 30 mm near the mullion ends.")
    w("- Key-feature edges are straight-line fits over the middle of each edge. Corner radii are circle fits to "
      "curvature runs, or to the aft-end arcs.")
    w("- Model glazing is evaluated on the current OML. Any change to `model/fuselage.py` moves the panes, so re-run "
      "this script after each change.")
    w("")
    REPORT.write_text("\n".join(L) + "\n")
    # machine-readable dump (git-ignored)
    def clean(o):
        if isinstance(o, dict):
            return {str(k): clean(v) for k, v in o.items() if not callable(v)}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        if isinstance(o, np.ndarray):
            return None if o.ndim > 1 else [clean(v) for v in o.tolist()]
        if isinstance(o, (np.floating, float)):
            return None if not np.isfinite(o) else float(o)
        if isinstance(o, (np.integer,)):
            return int(o)
        return o
    dump = dict(meta=A["meta"], glazing_rows=[{k: v for k, v in r.items()} for r in A["glz"]["rows"]],
                glazing_features={k: v for k, v in A["glz"]["fe"].items()}, glazing_info=A["glz"]["info"],
                recommended_glazing=recommended_glazing(A),
                profiles=A["prof"]["rows"], sections={n: {k: v for k, v in r.items() if k not in ("lines", "model", "body")}
                                                      for n, r in A["sec"].items()},
                other=A["other"], ranking=[dict(mag_mm=m, item=t, where=wh, cause=k, text=tx) for m, t, wh, k, tx in ranking(A)])
    (OUT / "compare.json").write_text(json.dumps(clean(dump), indent=1))
    print(f"[compare] wrote {REPORT.relative_to(ROOT)} and {(OUT / 'compare.json').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
