"""
Sheet L2 -- COCKPIT GLAZING & PRO MASK, drawn from the parameters of model/cockpit_glazing.py.

    python3 -m drawing.master L2          (or: python3 -m drawing.cockpit_detail)
    python3 -m drawing.cockpit_detail eval    deviation + photo tables only (needs refs/cache)

The panes and the mask are the zero contours of the glazing signed-distance fields evaluated ON the
outer mould line of model/fuselage.py (OML.section grid, contourpy), projected into the side, plan and
front views -- the same fields the 3-D builder trims the skin with; nothing comes from the mesh.  In
side projection every edge except the centre post is a straight construction line (a plane normal to
the plane of symmetry), drawn chain-dotted.

Layout (A2, 1:10, first-angle): side view from port (principal view) top left, plan below it, front
view (seen from ahead) to the right of the side view, VIEW B (seen from starboard, nose right) below the
front view; tables and notes in the right-hand column.  The overlay variant adds the registered Pilatus
drawing in red and photo-derived marks (refs/photo_notes.md, ngx_kenia_stbd_pilatus) in blue.
"""
from __future__ import annotations

import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from drawing import master as M  # noqa: E402
from drawing.master import (INK, GRID, MUTED, PAPER, W_OBJ, W_FINE, W_GRID, W_THIN, CHAIN, PHANTOM,  # noqa: E402
                            callout, table, notes, scale_bar, view_title, side_view, plan_view, front_view)
from model import cockpit_glazing as CG  # noqa: E402
from model import fuselage as F  # noqa: E402

SHEET = dict(id="L2", title="COCKPIT GLAZING & MASK", subtitle="COCKPIT GLAZING & PRO MASK", size="A2",
             scale="1:10", rev="A", order=20)

MASK_FILL = "#39434A"            # the dark surround (clean sheet)
GLASS_FILL = "#E4EEF3"
CONSTR = "#4F7C8A"               # construction lines (planes normal to the plane of symmetry)
DX = 0.002                       # contour grid (m) on the OML

# photo measurements (refs/photo_notes.md; ngx_kenia_stbd_pilatus registration: spinner tip STA 0.39,
# prop axis WL 1.655, 166 px/m; +-0.05-0.1 m absolute, ratios better) -- (label, x, z)
PHOTO_PTS = [
    ("aft extreme", 4.34, 2.29), ("top-front", 4.00, 2.51), ("front-bottom", 3.51, 2.155),
    ("sill", 3.54, 2.11), ("sill", 4.23, 2.11), ("ws tip", 3.20, 2.20), ("ws roof/pillar", 3.93, 2.57),
    ("mask point", 3.17, 2.21), ("mask aft top", 4.48, 2.58), ("mask aft bottom", 4.30, 2.03),
]


# =====================================================================================================
# geometry drawn from the parameters
# =====================================================================================================
@lru_cache(maxsize=4)
def glazing_edges(dx=DX):
    """3-D contours of the fields on the OML: {'stbd': {'ws','sw'}, 'port': {...}, 'mask': [loops]}."""
    st = CG.edges(+1, which=("ws", "sw", "mask"), dx=dx)
    po = CG.edges(-1, which=("ws", "sw"), dx=dx)
    big = lambda L: max(L, key=len)                                 # noqa: E731
    return dict(stbd=dict(ws=big(st["ws"]), sw=big(st["sw"])), port=dict(ws=big(po["ws"]), sw=big(po["sw"])),
                mask=st["mask"])


def proj(P, view):
    P = np.asarray(P)
    return {"side": P[:, [0, 2]], "plan": P[:, [0, 1]], "front": P[:, [1, 2]]}[view]


def crown_side(x):
    return F.z_top(x)


# =====================================================================================================
# comparison with the registered Pilatus drawing (sheet 1)
# =====================================================================================================
def _dens(P, step=0.002):
    P = np.asarray(P, float)
    out = []
    for a, b in zip(P[:-1], P[1:]):
        n = max(1, int(math.ceil(np.linalg.norm(b - a) / step)))
        out.append(a + np.outer(np.arange(n) / n, b - a))
    out.append(P[-1:])
    return np.vstack(out)


def _closed(P):
    P = np.asarray(P, float)
    return P if np.allclose(P[0], P[-1]) else np.vstack([P, P[:1]])


def ngx_opening(view, gap=0.150, res=0.001):
    """The NGX port side-window OPENING (DV pane + main pane with the post between them filled) of the
    drawing in one view: raster union of the two loops, closed with a disk of radius `gap`."""
    from scipy import ndimage
    import contourpy
    from matplotlib.path import Path as MPath
    G = M.mbp_data()["glazing"][view]
    A, B = _closed(G["sw_port"]), _closed(G["dv_port"])
    lo = np.minimum(A.min(0), B.min(0)) - 2 * gap
    hi = np.maximum(A.max(0), B.max(0)) + 2 * gap
    xs = np.arange(lo[0], hi[0], res)
    ys = np.arange(lo[1], hi[1], res)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    Q = np.c_[X.ravel(), Y.ravel()]
    m = (MPath(A).contains_points(Q) | MPath(B).contains_points(Q)).reshape(X.shape)
    r = gap / res                                   # closing = dilation then erosion by a disk (EDT)
    dil = ndimage.distance_transform_edt(~m) <= r
    m = ndimage.distance_transform_edt(dil) > r
    L = max(contourpy.contour_generator(z=m.astype(float)).lines(0.5), key=len)
    return np.c_[np.interp(L[:, 1], np.arange(len(xs)), xs), np.interp(L[:, 0], np.arange(len(ys)), ys)]


def _dist(P, Q):
    from scipy.spatial import cKDTree
    return cKDTree(_dens(_closed(Q), 0.001)).query(P)[0]


def compare(ours, ref, exclude=None):
    """Symmetric point-to-outline distances (m): ref -> ours and ours -> ref.  exclude(P) -> bool mask
    of points to ignore (both directions)."""
    R = _dens(_closed(ref), 0.002)
    O = _dens(_closed(ours), 0.002)
    if exclude is not None:
        R, O = R[~exclude(R)], O[~exclude(O)]
    d1, d2 = _dist(R, ours), _dist(O, ref)
    k = int(np.argmax(d1)) if d1.max() >= d2.max() else None
    worst = R[k] if k is not None else O[int(np.argmax(d2))]
    return dict(n=len(R), rms=float(np.sqrt(np.mean(d1 ** 2))), max=float(max(d1.max(), d2.max())),
                max_ref=float(d1.max()), max_ours=float(d2.max()), worst=worst)


def stbd_side_from_plan():
    """Side view of the drawing's STARBOARD pane (not drawn on sheet 1): its plan loop lifted onto our
    OML (z = z_at(x, |y|)).  Poorly conditioned along the sill (the skin is near-vertical there)."""
    P = M.mbp_data()["glazing"]["plan"]["sw_stbd"]
    return np.c_[P[:, 0], F.z_at(P[:, 0], np.abs(P[:, 1]), upper=True)]


def deviations():
    """Rows (pane, view, reference, n, rms mm, max mm, worst at, remark) + the raw dict."""
    d = M.mbp_data()
    G = d["glazing"]
    E = glazing_edges()
    s_ws, s_sw = E["stbd"]["ws"], E["stbd"]["sw"]
    p_ws, p_sw = E["port"]["ws"], E["port"]["sw"]
    rows, raw = [], {}

    def add(pane, view, refname, ours, ref, remark="", exclude=None):
        c = compare(ours, ref, exclude)
        raw[(pane, view, refname)] = c
        w = c["worst"]
        rows.append((pane, view, refname, str(c["n"]), f"{c['rms'] * 1e3:.1f}", f"{c['max'] * 1e3:.1f}",
                     f"{w[0] * 1e3:.0f} / {w[1] * 1e3:.0f}", remark))

    # side view (both panes of a side project onto the same place; the drawing shows the port side)
    add("windshield", "side", "ws_port", proj(p_ws, "side"), G["side"]["ws_port"],
        "post edge = OML at BL 23")
    add("side window", "side", "NGX port DV+main", proj(p_sw, "side"), ngx_opening("side"),
        "DV + main pane, post filled")
    add("side window", "side", "sw_stbd plan>OML *", proj(s_sw, "side"), stbd_side_from_plan(),
        "starboard pane lifted from plan; sill ill-cond.")
    # plan
    add("windshield stbd", "plan", "ws_stbd", proj(s_ws, "plan"), G["plan"]["ws_stbd"])
    add("windshield port", "plan", "ws_port", proj(p_ws, "plan"), G["plan"]["ws_port"])
    add("side window stbd", "plan", "sw_stbd", proj(s_sw, "plan"), G["plan"]["sw_stbd"], "the PRO pane shape")
    add("side window port", "plan", "NGX port DV+main", proj(p_sw, "plan"), ngx_opening("plan"))
    # front
    add("windshield stbd", "front", "ws_stbd", proj(s_ws, "front"), G["front"]["ws_stbd"])
    add("windshield port", "front", "ws_port", proj(p_ws, "front"), G["front"]["ws_port"])
    add("side window stbd", "front", "sw_stbd", proj(s_sw, "front"), G["front"]["sw_stbd"])
    add("side window port", "front", "NGX port DV+main", proj(p_sw, "front"), ngx_opening("front"))
    return rows, raw


def photo_rows():
    """Our numbers vs the photo measurements (refs/photo_notes.md + the kenia overlay) and the drawing:
    (item, photos, ours, drawing / remark)."""
    K = CG.key_points()
    sw = CG.side_outline("sw")
    H = sw[:, 1].max() - sw[:, 1].min()
    top_len = CG.SW_AFT - K["sw_top_front"][0]
    sill_len = CG.SW_AFT - K["sw_low_front"][0]
    # straight vertical part of the D
    v_lo = CG.SW_SILL + CG.SW_R["bot_aft"]
    ztop_aft = float(CG.z_sw_top(CG.SW_AFT))
    a_top = math.radians(-CG.ROOF_LINE[1])
    v_hi = ztop_aft - CG.SW_R["top_aft"] * (1 + math.sin(a_top)) / math.cos(a_top)
    mk = K
    mp = mask_point()
    door = door_seam()["x0"]
    return [
        ("pillar edge angle", "32-39 deg", f"{CG.PILLAR_LINE[1]:.1f} deg", "dwg 34.1-34.6"),
        ("A-pillar width, side (horiz.)", "0.05-0.06", f"{2 * CG.PILLAR_HALF:.3f}", "dwg 0.038"),
        ("side-window sill WL", "2.09-2.11", f"{CG.SW_SILL:.3f}", "dwg 2.087 (DV 2.073)"),
        ("side-window aft extreme STA", "~4.34", f"{CG.SW_AFT:.3f}", "dwg 4.356"),
        ("glass height", "0.40-0.45 (a)", f"{H:.3f}", "dwg 0.448"),
        ("sill length / height", "1.98-2.09 (a)", f"{sill_len / H:.2f}", "dwg 1.93"),
        ("top length / height", "0.71-0.85 (a)", f"{top_len / H:.2f}", "dwg 0.66"),
        ("D radius top / bottom", "0.09-0.14 / 0.09-0.17", f"{CG.SW_R['top_aft']:.3f} / {CG.SW_R['bot_aft']:.3f}",
         "dwg 0.12 / 0.21 (b)"),
        ("D straight vertical", "0.15-0.19", f"{max(v_hi - v_lo, 0):.3f}", "dwg 0.06 (b)"),
        ("side-window top rise (fwd)", "2-6 deg (a)", f"{-CG.ROOF_LINE[1]:.1f} deg", "dwg 9-10 deg"),
        ("windshield roof rise (fwd)", "~25 deg (c)", f"{-CG.WS_ROOF_LINE[1]:.1f} deg", "dwg 10.3 deg"),
        ("centre post, glass to glass", "0.08-0.14 (d)", f"{2 * CG.WS_POST:.3f}", "dwg 0.046"),
        ("mask below sill", "0.06-0.08", f"{CG.MASK_LOW:.3f}", "photos only"),
        ("mask ramp angle", "21-27 deg", f"{CG.MASK_RAMP_DEG:.1f} deg", "photos only"),
        ("mask fwd point STA / WL", "3.17 / 2.21", f"{mp[0]:.3f} / {mp[1]:.3f}", "ramp meets crown"),
        ("mask aft edge lean", "7-23 deg", f"{CG.MASK_AFT_LEAN_DEG:.1f} deg", "bottom forward"),
        ("mask aft margin low / top", "0.07 / 0.15-0.20",
         f"{mk['mask_low_aft'][0] - CG.SW_AFT:.3f} / {mk['mask_top_aft'][0] - CG.SW_AFT:.3f}", "from aft extreme"),
        ("mask top margin", "0.055-0.07 (e)", f"{CG.MASK_TOP_MARGIN:.3f}", "normal to top edge"),
        ("mask aft edge to door seam", "<= ~0.05-0.10", f"{door - mk['mask_top_aft'][0]:.3f}",
         f"seam STA {door * 1000:.0f}"),
    ]


def mask_point():
    """Forward point of the mask in side view: the ramp line meets the crown profile."""
    xs = np.linspace(3.0, 3.6, 6001)
    z_ramp = CG.SW_SILL - CG.MASK_LOW + (CG.MASK_RAMP_X - xs) * math.tan(math.radians(CG.MASK_RAMP_DEG))
    k = int(np.argmin(np.abs(F.z_top(xs) - z_ramp)))
    return float(xs[k]), float(z_ramp[k])


@lru_cache(maxsize=1)
def door_seam():
    """Airstair door panel seam (model/fuselage_parts.DOOR_PANELS; drawn door outline), side view."""
    try:
        from model import fuselage_parts as FP
        o = FP.DOOR_PANELS["door_airstair"]
    except Exception:                               # noqa: BLE001
        o = dict(cx=4.970, cz=1.929, hx=0.320, hz=0.700, r=0.100)
    return dict(x0=o["cx"] - o["hx"], x1=o["cx"] + o["hx"], z0=o["cz"] - o["hz"], z1=o["cz"] + o["hz"], r=o["r"])


def E_tip():
    """Forward-most windshield point in side view (sill plane at the post)."""
    xs = np.linspace(3.1, 3.5, 4001)
    zc = F.z_at(xs, np.full_like(xs, CG.WS_POST), upper=True)
    k = int(np.argmin(np.abs(zc - CG.z_ws_sill(xs))))
    return float(xs[k]), float(zc[k])


# =====================================================================================================
# sheet layout (sheet mm; A2 frame 20..584 x 10..410, title block 388..578 x 333..404)
# =====================================================================================================
SIDE_BOX = (3.00, 1.95, 4.80, 2.85)
PLAN_BOX = (3.00, -0.92, 4.80, 0.92)
FRONT_BOX = (-0.95, 1.95, 0.95, 2.85)
ORG_SIDE = (48.0, 44.0)          # sheet position of model (3.00, 2.85)
ORG_PLAN = (48.0, 262.0)         # ... of model (3.00, 0.00)
ORG_FRONT = (392.0, 44.0)        # ... of model (0.00, 2.85)
ORG_STBD = (480.0, 176.0)        # ... of model (3.00, 2.85), nose right
COL_X = (492.0, 580.0)           # right-hand column (tables, notes)


def starboard_view(name, origin, scale, model_origin, box=None):
    """Side view seen from STARBOARD (nose right): (x, z) -> sheet."""
    k = 1000.0 / scale
    A = np.array([[-k, 0.0], [0.0, -k]])
    t = np.asarray(origin, float) - A @ np.asarray(model_origin, float)
    return M.View(name, "xz", A, t, float(scale), box, "seen from starboard, nose right")


def make_views(ds):
    vs = ds.add_view(side_view("side_port", origin=ORG_SIDE, scale=10, model_origin=(3.00, 2.85), box=SIDE_BOX))
    vp = ds.add_view(plan_view("plan", origin=ORG_PLAN, scale=10, model_origin=(3.00, 0.0), box=PLAN_BOX))
    vf = ds.add_view(front_view("front", origin=ORG_FRONT, scale=10, model_origin=(0.0, 2.85), box=FRONT_BOX))
    vb = ds.add_view(starboard_view("side_stbd", origin=ORG_STBD, scale=10, model_origin=(3.00, 2.85),
                                    box=SIDE_BOX))
    return vs, vp, vf, vb


def _runs(mask):
    idx = np.flatnonzero(mask)
    if not len(idx):
        return []
    br = np.flatnonzero(np.diff(idx) > 1)
    starts = np.r_[idx[0], idx[br + 1]]
    ends = np.r_[idx[br], idx[-1]]
    return [np.arange(a, b + 1) for a, b in zip(starts, ends)]


def draw(ds):
    draw_clean(ds)
    try:
        draw_overlay(ds)
    except Exception as e:                      # noqa: BLE001 -- the clean sheet must not depend on refs/cache
        ds.log.append(f"overlay skipped: {e}")


def draw_clean(ds):
    ds.frame_and_title(tb_width=190.0)
    E = glazing_edges()
    vs, vp, vf, vb = make_views(ds)
    draw_side(ds, vs, E, side=-1)
    draw_side(ds, vb, E, side=+1)
    draw_plan(ds, vp, E)
    draw_front(ds, vf, E)
    # view titles
    x0, z0, x1, z1 = SIDE_BOX
    view_title(ds, 0.5 * (vs.pt(x0, z0)[0] + vs.pt(x1, z0)[0]), vs.pt(0, z0)[1] + 13.0, "SIDE VIEW (PORT)",
               "SEEN FROM PORT - SCALE 1:10")
    view_title(ds, 0.5 * (vp.pt(x0, 0)[0] + vp.pt(x1, 0)[0]), vp.pt(0, PLAN_BOX[1])[1] + 11.0, "PLAN",
               "SEEN FROM ABOVE, STARBOARD UP - SCALE 1:10")
    view_title(ds, vf.pt(0.0, 0)[0], vf.pt(0, FRONT_BOX[1])[1] + 13.0, "FRONT VIEW",
               "SEEN FROM AHEAD, STARBOARD LEFT - SCALE 1:10")
    view_title(ds, 0.5 * (vb.pt(x0, z0)[0] + vb.pt(x1, z0)[0]), vb.pt(0, z0)[1] + 13.0, "VIEW B (STARBOARD)",
               "SEEN FROM STARBOARD, NOSE RIGHT - SCALE 1:10")
    draw_tables(ds)
    draw_notes(ds)


# ---------------------------------------------------------------------------------------------- helpers
def _fill_region(ds, v, P, fill, w=0.0, color=None):
    ds.cv.path(v.pts(P), w, None, closed=True, fill=fill, stroke=w > 0, color=color)


def _outline(ds, v, P, w=W_OBJ, dash=None, color=None, closed=True):
    ds.cv.path(v.pts(P), w, dash, closed=closed, color=color)


def _side_mask_region():
    """Mask region in side projection clipped to the fuselage silhouette (crown): the side-projection
    polygon of cockpit_glazing.mask_lines() with the part above the crown replaced by the crown line."""
    from matplotlib.path import Path as MPath
    O = CG.side_outline("mask")
    below = O[:, 1] <= F.z_top(O[:, 0])
    i0 = int(np.argmax(~below)) if (~below).any() else 0
    order = np.r_[np.arange(i0, len(O)), np.arange(0, i0)]
    P = O[order][below[order]]                  # outline below the crown, starting after the part above it
    xs = np.linspace(SIDE_BOX[0], SIDE_BOX[2], 1801)
    zc = F.z_top(xs)
    crown_in = MPath(np.vstack([O, O[:1]])).contains_points(np.c_[xs, zc - 1e-5])
    xa, xb = xs[crown_in].min(), xs[crown_in].max()
    cx = np.linspace(xa, xb, 300)
    C = np.c_[cx, F.z_top(cx)]
    return np.vstack([P, C[::-1] if np.linalg.norm(P[-1] - C[-1]) < np.linalg.norm(P[-1] - C[0]) else C])


def _rounded_rect(x0, z0, x1, z1, r, n=10):
    pts = []
    for cx, cz, a0 in ((x1 - r, z0 + r, -90), (x1 - r, z1 - r, 0), (x0 + r, z1 - r, 90), (x0 + r, z0 + r, 180)):
        for a in np.radians(np.linspace(a0, a0 + 90, n)):
            pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    return np.array(pts)


def _grid_side(ds, v, labels_top=True):
    frames = {k: F.FRAMES[k] for k in ("FR10", "FR12", "FR14", "FR16")}
    x0, z0, x1, z1 = SIDE_BOX
    for name, x in dict(FIREWALL=3.000, **frames).items():
        p, q = v.pt(x, z0), v.pt(x, z1)
        ds.cv.line(p, q, W_GRID, None if name != "FIREWALL" else (5.0, 1.0, 0.8, 1.0), color=GRID)
        e = p if p[1] > q[1] else q                 # bottom end: frame name + station below the view
        dx = 0.0
        if name == "FIREWALL":
            dx = -3.0 if v.A[0, 0] > 0 else 3.0     # FIREWALL / FR10 are 80 mm apart: stagger the labels
        elif name == "FR10":
            dx = 2.4 if v.A[0, 0] > 0 else -2.4
        ds.text(e[0] + dx, e[1] + 3.4, name if name != "FIREWALL" else "FW", 2.1, "label", "middle", weight=600,
                fill=GRID, tag="grid")
        ds.text(e[0] + dx, e[1] + 6.3, f"{x * 1000:.0f}", 1.9, "mono", "middle", fill=GRID, tag="grid")
    for z in (2.0, 2.2, 2.4, 2.6, 2.8):
        p, q = v.pt(x0, z), v.pt(x1, z)
        ds.cv.line(p, q, W_GRID, color=GRID)
        e = p if (p[0] < q[0]) == (v.A[0, 0] > 0) else q        # the nose end
        s = -1.0 if e[0] <= min(p[0], q[0]) + 1e-6 else 1.0
        ds.text(e[0] + s * 1.5, e[1], f"WL {z * 1000:.0f}", 1.9, "mono", "end" if s < 0 else "start",
                vcenter=True, fill=GRID, tag="grid")


def draw_side(ds, v, E, side):
    cv = ds.cv
    _grid_side(ds, v)
    # context: fuselage crown, max-breadth WL, airstair door seam (port)
    xs = np.linspace(SIDE_BOX[0], SIDE_BOX[2], 900)
    ds_ = door_seam()
    if side < 0:
        for P in M.clip_polyline(_rounded_rect(ds_["x0"], ds_["z0"], ds_["x1"], ds_["z1"], ds_["r"]), SIDE_BOX):
            cv.path(v.pts(P), W_FINE, PHANTOM, color=MUTED)
    zm = F.z_mw(xs)
    for r in _runs(zm >= SIDE_BOX[1]):
        cv.path(v.pts(np.c_[xs[r], zm[r]]), W_FINE, CHAIN, color=MUTED)
    # mask (filled), then the panes
    try:
        R = _side_mask_region()
    except Exception as e:                      # noqa: BLE001
        ds.log.append(f"mask region fallback: {e}")
        R = CG.side_outline("mask")
    _fill_region(ds, v, R, MASK_FILL)
    s = "stbd" if side > 0 else "port"
    sw = proj(E[s]["sw"], "side")
    ws = proj(E[s]["ws"], "side")
    for P in (sw, ws):
        _fill_region(ds, v, P, GLASS_FILL)
        _outline(ds, v, P)
    _outline(ds, v, R, w=W_FINE)
    cv.path(v.pts(np.c_[xs, F.z_top(xs)]), W_OBJ)
    _construction_side(ds, v)
    if side < 0:
        X, Y = v.pt(ds_["x0"], 1.975)
        ds.text(X + 1.2, Y, f"AIRSTAIR DOOR SEAM {ds_['x0'] * 1000:.0f}", 1.9, "label", "start", fill=MUTED,
                tag="lbl")
        _dims_side(ds, v)
        _eye_side(ds, v)
    else:
        _labels_stbd(ds, v)


def _construction_side(ds, v):
    """The planes normal to the plane of symmetry (straight lines in side projection), chain-dotted."""
    def seg(pt, deg, xa, xb):
        (px, pz) = pt
        t = math.tan(math.radians(deg))
        return np.array([[xa, pz + (xa - px) * t], [xb, pz + (xb - px) * t]])

    L = [seg(*CG.SILL_LINE, 3.22, 3.70), seg(*CG.ROOF_LINE, 3.98, 4.47), seg(*CG.WS_ROOF_LINE, 3.80, 4.08),
         seg((float(CG.x_pillar(2.3)), 2.3), CG.PILLAR_LINE[1], float(CG.x_pillar(1.97)), float(CG.x_pillar(2.63)))]
    for P in L:
        ds.cv.path(v.pts(P), W_THIN, CHAIN, color=CONSTR)


def _dims_side(ds, v):
    """Dimensions of the port side view: STA ordinates above, WL ordinates to the right, angles, radii."""
    sh = ds.sh
    K = CG.key_points()
    mp = mask_point()
    tip = E_tip()
    # --- station ordinates above the view (datum: STA 0, 3000 mm ahead of the firewall)
    feats = [("MASK PT", mp), ("WS TIP", tip), ("SW FWD", tuple(K["sw_low_front"])),
             ("SW TOP FWD", tuple(K["sw_top_front"])), ("SW AFT", (CG.SW_AFT, 2.30)),
             ("MASK AFT LOW", tuple(K["mask_low_aft"])), ("MASK AFT TOP", tuple(K["mask_top_aft"]))]
    ytop = v.pt(0, SIDE_BOX[3])[1]
    ytxt = ytop - 3.0
    for lab, (x, z) in feats:
        X, Y = v.pt(x, z)
        ds.cv.line((X, Y - 0.8), (X, ytxt + 0.8), W_THIN, (1.2, 0.8), color=INK)
        ds.text(X + 0.8, ytxt, f"{x * 1000:.0f}  {lab}", 2.0, "mono", "start", rot=-90, tag="ord")
    X0 = v.pt(SIDE_BOX[0], 0)[0]
    ds.text(X0 - 2.0, ytxt - 2.0, "STA", 2.3, "label", "end", weight=600, tag="ord")
    # --- WL ordinates at the right of the view
    xr = v.pt(SIDE_BOX[2], 0)[0] + 3.0
    wls = [("SW TOP FWD", K["sw_top_front"][1], K["sw_top_front"][0]),
           ("SW TOP AFT", K["sw_top_aft"][1], CG.SW_AFT - 0.02),
           ("SW SILL", CG.SW_SILL, 4.20), ("MASK LOW EDGE", CG.SW_SILL - CG.MASK_LOW, 4.30)]
    used = []
    for lab, z, xf in sorted(wls, key=lambda t: -t[1]):
        Y = v.pt(0, z)[1]
        Yt = Y
        while any(abs(Yt - u) < 3.0 for u in used):
            Yt += 3.0
        used.append(Yt)
        ds.cv.line(v.pt(xf, z), (xr, Y), W_THIN, (1.2, 0.8), color=INK)
        ds.cv.line((xr, Y), (xr + 2.0, Yt), W_THIN, color=INK)
        ds.text(xr + 3.0, Yt, f"WL {z * 1000:.0f}  {lab}", 2.0, "mono", "start", vcenter=True, tag="ord")
    # --- angles (vertices outside the glass so the arcs sit on bare skin)
    zp = 1.975
    xp = float(CG.x_pillar(zp))
    X, Y = v.pt(xp, zp)
    a = CG.PILLAR_LINE[1]
    ds.cv.line((X, Y), (X + 19.0, Y), W_THIN)
    sh.angle_dim((X, Y), -a, 0.0, 16.0, f"{a:.1f}°", (X + 17.0, Y - 2.4), tag="dim")
    ds.text(X - 1.0, Y + 3.2, "A-PILLAR", 1.9, "label", "middle", fill=CONSTR, tag="lbl")
    # mask ramp: at its upper end (the mask point on the crown), extension forward over the cowl
    X, Y = v.pt(*mp)
    c = CG.MASK_RAMP_DEG
    ds.cv.line((X, Y), (X - 13.0, Y), W_THIN)
    ds.cv.line((X, Y), (X - 13.0 * math.cos(math.radians(c)), Y - 13.0 * math.sin(math.radians(c))), W_THIN,
               CHAIN, color=CONSTR)
    sh.angle_dim((X, Y), 180.0, 180.0 + c, 11.0, f"{c:.0f}°", (X - 15.5, Y - 2.2), tag="dim")
    ds.text(X - 9.0, Y - 9.5, "MASK RAMP", 1.9, "label", "middle", fill=CONSTR, tag="lbl")
    callout(ds, v, tip, f"WS TIP {tip[0] * 1000:.0f} / {tip[1] * 1000:.0f}", offset=(-4.0, -15.0), color=INK,
            size=2.1)

    # --- radii, lean, pillar width, planes (call-outs)
    cb = CG.SW_R["bot_aft"]
    callout(ds, v, (CG.SW_AFT - cb * (1 - math.cos(math.radians(45))), CG.SW_SILL + cb * (1 - math.sin(math.radians(45)))),
            f"R {cb * 1000:.0f}", offset=(9.0, 13.0), color=INK, size=2.2)
    ta = K["sw_top_aft"]
    callout(ds, v, (ta[0] - 0.032, ta[1] - 0.030), f"R {CG.SW_R['top_aft'] * 1000:.0f}", offset=(-2.0, 14.0),
            color=INK, size=2.2)
    ma, ml = K["mask_top_aft"], K["mask_low_aft"]
    callout(ds, v, (0.5 * (ma[0] + ml[0]), 0.5 * (ma[1] + ml[1])), f"MASK AFT EDGE, LEAN {CG.MASK_AFT_LEAN_DEG:.0f}°",
            offset=(9.0, 2.0), color=INK, size=2.2,
            lines=[f"{door_seam()['x0'] - ma[0]:.2f} m AHEAD OF DOOR SEAM"])
    pz = 2.46
    callout(ds, v, (float(CG.x_pillar(pz)), pz), f"A-PILLAR {CG.PILLAR_WIDTH * 1000:.0f} NORMAL",
            offset=(-12.0, -13.0), color=INK, size=2.2, lines=[f"({2 * CG.PILLAR_HALF * 1000:.0f} HORIZONTAL)"])
    callout(ds, v, (3.685, float(CG.z_ws_sill(3.685))), f"SILL PLANE {-CG.SILL_LINE[1]:.1f}°",
            offset=(7.0, 3.0), color=CONSTR, size=2.1, lines=["WS LOWER EDGE + SW LOWER-FRONT EDGE"])
    callout(ds, v, (4.44, float(CG.z_sw_top(4.44))), f"SW TOP PLANE {-CG.ROOF_LINE[1]:.1f}°",
            offset=(-4.0, -16.0), color=CONSTR, size=2.1)
    callout(ds, v, (3.86, float(CG.z_ws_roof(3.86))), f"WS ROOF PLANE {-CG.WS_ROOF_LINE[1]:.1f}°",
            offset=(-10.0, -12.0), color=CONSTR, size=2.1)


def _eye_side(ds, v):
    e = CG.EYE
    X, Y = v.pt(e[0], e[2])
    ds.cv.circle(X, Y, 1.3, w=W_FINE, fill=PAPER)
    ds.cv.line((X - 2.2, Y), (X + 2.2, Y), W_FINE)
    ds.cv.line((X, Y - 2.2), (X, Y + 2.2), W_FINE)
    vis = CG.vision()
    a = math.radians(vis["over_nose_down"])
    xa = SIDE_BOX[0] + 0.02
    P = np.array([[e[0], e[2]], [xa, e[2] - (e[0] - xa) * math.tan(a)]])
    ds.cv.path(v.pts(P), W_THIN, (3.0, 1.0), color=M.ACCENT)
    ds.text(X - 2.4, Y - 5.0, "DESIGN EYE (EST.)", 1.8, "label", "end", fill=M.ACCENT, tag="eye")
    ds.text(X - 2.4, Y - 2.4, f"{e[0] * 1000:.0f} / {abs(e[1]) * 1000:.0f} / {e[2] * 1000:.0f}", 1.8, "mono", "end",
            fill=M.ACCENT, tag="eye")
    Xl, Yl = v.pt(3.335, e[2] - (e[0] - 3.335) * math.tan(a))
    ds.text(Xl, Yl + 2.6, f"OVER NOSE {vis['over_nose_down']:.1f}°", 1.9, "label", "start", fill=M.ACCENT,
            tag="eye", rot=math.degrees(a))


def _labels_stbd(ds, v):
    K = CG.key_points()
    callout(ds, v, (4.10, CG.SW_SILL), f"SILL WL {CG.SW_SILL * 1000:.0f} (HORIZONTAL)", offset=(4.0, -11.0),
            color=INK, size=2.2)
    callout(ds, v, tuple(0.5 * (K["sw_low_front"] + K["sw_sill_front"])), "LOWER-FRONT EDGE ON THE",
            offset=(11.0, -31.0), color=INK, size=2.2, lines=["WINDSHIELD SILL PLANE"])
    callout(ds, v, (4.20, float(CG.z_sw_top(4.20))), "ONE PANE, NO DV WINDOW (PRO)", offset=(10.0, -12.0),
            color=INK, size=2.2, lines=["NGX STARBOARD SHAPE, BOTH SIDES"])
    mp = mask_point()
    callout(ds, v, mp, f"MASK POINT {mp[0] * 1000:.0f} / {mp[1] * 1000:.0f}", offset=(-3.0, 15.0), color=INK,
            size=2.2, lines=["RAMP MEETS THE CROWN"])
    callout(ds, v, (4.36, CG.SW_SILL - CG.MASK_LOW), f"MASK LOWER EDGE {CG.MASK_LOW * 1000:.0f} BELOW SILL",
            offset=(-16.0, 0.0), color=INK, size=2.2)


def draw_plan(ds, v, E):
    cv = ds.cv
    x0, y0, x1, y1 = PLAN_BOX
    frames = {k: F.FRAMES[k] for k in ("FR10", "FR12", "FR14", "FR16")}
    for name, x in dict(FIREWALL=3.000, **frames).items():
        cv.line(v.pt(x, y0), v.pt(x, y1), W_GRID, None if name != "FIREWALL" else (5.0, 1.0, 0.8, 1.0), color=GRID)
        X, Y = v.pt(x, y0)
        dx = -3.0 if name == "FIREWALL" else (2.4 if name == "FR10" else 0.0)
        ds.text(X + dx, Y + 3.2, name if name != "FIREWALL" else "FW", 2.1, "label", "middle", weight=600,
                fill=GRID, tag="grid")
        ds.text(X + dx, Y + 6.0, f"{x * 1000:.0f}", 1.9, "mono", "middle", fill=GRID, tag="grid")
    for y in (-0.8, -0.4, 0.4, 0.8):
        p, q = v.pt(x0, y), v.pt(x1, y)
        cv.line(p, q, W_GRID, color=GRID)
        ds.text(p[0] - 1.5, p[1], f"BL {abs(y) * 1000:.0f} {'S' if y > 0 else 'P'}", 1.9, "mono", "end",
                vcenter=True, fill=GRID, tag="grid")
    cv.line(v.pt(x0 - 0.02, 0.0), v.pt(x1, 0.0), W_FINE, CHAIN, color=MUTED)
    X, Y = v.pt(x0 - 0.02, 0.0)
    ds.text(X - 1.2, Y, "CL", 2.3, "label", "end", vcenter=True, weight=600, tag="cl")
    # mask region projected (fill), then the panes
    for L in E["mask"]:
        _fill_region(ds, v, proj(L, "plan"), MASK_FILL)
    for s in ("stbd", "port"):
        for k in ("ws", "sw"):
            P = proj(E[s][k], "plan")
            _fill_region(ds, v, P, GLASS_FILL)
            _outline(ds, v, P)
    for L in E["mask"]:
        _outline(ds, v, proj(L, "plan"), w=W_FINE)
    # fuselage outline (max half-breadth) and the crown line
    xs = np.linspace(x0, x1, 600)
    for sgn in (1, -1):
        cv.path(v.pts(np.c_[xs, sgn * F.half_w(xs)]), W_OBJ)
    # eye points (pilot port, co-pilot starboard)
    for sgn in (-1, 1):
        X, Y = v.pt(CG.EYE[0], sgn * abs(CG.EYE[1]))
        cv.circle(X, Y, 1.1, w=W_FINE, fill=PAPER)
        cv.line((X - 1.8, Y), (X + 1.8, Y), W_FINE)
        cv.line((X, Y - 1.8), (X, Y + 1.8), W_FINE)
    X, Y = v.pt(CG.EYE[0], -abs(CG.EYE[1]))
    ds.text(X + 2.4, Y + 3.6, f"EYE BL {abs(CG.EYE[1]) * 1000:.0f}", 1.9, "mono", "start", fill=M.ACCENT, tag="eye")
    # post width dimension (ahead of the panes)
    sh = ds.sh
    xa = 3.55
    pa, pb = v.pt(xa, CG.WS_POST), v.pt(xa, -CG.WS_POST)
    Xd = v.pt(3.12, 0)[0]
    sh.dim(pa, pb, Xd, "", orient="v", show_text=False)
    ds.text(Xd - 1.5, v.pt(0, 0.0)[1] - 5.0, f"POST {2 * CG.WS_POST * 1000:.0f}", 2.1, "mono", "end", tag="lbl")
    # extreme stations / butt lines of the panes
    ws = proj(E["stbd"]["ws"], "plan")
    sw = proj(E["stbd"]["sw"], "plan")
    k = int(np.argmin(ws[:, 0]))
    callout(ds, v, tuple(ws[k]), f"WS FWD {ws[k, 0] * 1000:.0f}", offset=(-4.0, -22.0), color=INK, size=2.2)
    k = int(np.argmax(sw[:, 0]))
    callout(ds, v, tuple(sw[k]), f"SW AFT {sw[k, 0] * 1000:.0f}", offset=(12.0, -9.0), color=INK, size=2.2)
    k = int(np.argmax(ws[:, 1]))
    callout(ds, v, tuple(ws[k]), f"WS MAX BL {ws[k, 1] * 1000:.0f}", offset=(-6.0, -14.0), color=INK, size=2.2)
    k = int(np.argmax(ws[:, 0]))
    callout(ds, v, tuple(ws[k]), f"WS AFT {ws[k, 0] * 1000:.0f}", offset=(10.0, 8.0), color=INK, size=2.2)
    callout(ds, v, (3.885, -0.20), "MASK ROOF BAND", offset=(16.0, 6.0), color=INK, size=2.2,
            lines=[f"{CG.MASK_TOP_MARGIN * 1000:.0f} ABOVE THE SW TOP PLANE"])


def draw_front(ds, v, E):
    cv = ds.cv
    y0, z0, y1, z1 = FRONT_BOX
    for y in (-0.8, -0.4, 0.0, 0.4, 0.8):
        p, q = v.pt(y, z0), v.pt(y, z1)
        cv.line(p, q, W_GRID if y else W_FINE, None if y else CHAIN, color=GRID if y else MUTED)
        ds.text(q[0], q[1] - 1.2, "CL" if y == 0 else f"BL {abs(y) * 1000:.0f} {'S' if y > 0 else 'P'}", 1.9,
                "mono", "middle", fill=GRID, tag="grid")
    for z in (2.0, 2.2, 2.4, 2.6, 2.8):
        p, q = v.pt(y0, z), v.pt(y1, z)
        cv.line(p, q, W_GRID, color=GRID)
        e = p if p[0] < q[0] else q                 # labels inside the box, left end (outside the fuselage)
        ds.text(e[0] + 0.8, e[1] - 0.8, f"WL {z * 1000:.0f}", 1.9, "mono", "start", fill=GRID, tag="grid")
    # fuselage silhouette at FR16 (the widest section in the view) and the section at FR10
    t = np.linspace(0, 1, 721)
    for x, w, dash in ((F.FRAMES["FR16"], W_OBJ, None), (F.FRAMES["FR10"], W_FINE, (2.0, 0.8))):
        P = F.section(np.full_like(t, x), t)
        for r in _runs(P[:, 2] >= z0):
            cv.path(v.pts(P[r][:, [1, 2]]), w, dash, color=None if dash is None else MUTED)
    X, Y = v.pt(-0.36, float(F.z_at(F.FRAMES["FR10"], 0.36)) - 0.03)
    ds.text(X, Y, f"FR10 {F.FRAMES['FR10'] * 1000:.0f}", 1.9, "mono", "middle", fill=MUTED, tag="lbl")
    for L in E["mask"]:
        _fill_region(ds, v, proj(L, "front"), MASK_FILL)
    for s in ("stbd", "port"):
        for k in ("ws", "sw"):
            P = proj(E[s][k], "front")
            _fill_region(ds, v, P, GLASS_FILL)
            _outline(ds, v, P)
    for L in E["mask"]:
        _outline(ds, v, proj(L, "front"), w=W_FINE)
    sh = ds.sh
    sh.dim(v.pt(CG.WS_POST, 2.45), v.pt(-CG.WS_POST, 2.45), v.pt(0, 2.70)[1], f"{2 * CG.WS_POST * 1000:.0f}",
           orient="h", text_side="after")
    ws = proj(E["stbd"]["ws"], "front")
    k = int(np.argmax(ws[:, 0]))
    callout(ds, v, tuple(ws[k]), f"WS BL {ws[k, 0] * 1000:.0f}", offset=(-6.0, 12.0), color=INK, size=2.2)
    k = int(np.argmax(ws[:, 1]))
    callout(ds, v, tuple(ws[k]), f"WS TOP WL {ws[k, 1] * 1000:.0f}", offset=(-18.0, -9.0), color=INK, size=2.2)


# ---------------------------------------------------------------------------------------------- tables
def draw_tables(ds):
    x0, x1 = COL_X
    try:
        rows, raw = deviations()
        ds._dev_raw = raw
    except Exception as e:                      # noqa: BLE001
        rows = [("(reference not available)", "", "", "", "", "-", "", str(e)[:60])]
        ds.log.append(f"deviation table: reference not available ({e})")
    cols = [("PANE", 21.0, "l"), ("VIEW", 8.5, "l"), ("REFERENCE", 24.0, "l"), ("RMS", 8.0, "r"),
            ("MAX", 8.0, "r"), ("WORST AT", 18.5, "l")]
    y = table(ds, x0, 16.0, cols, [(r[0], r[1], r[2], r[4], r[5], r[6]) for r in rows],
              title="vs PILATUS 190.10.40.432 SHEET 1 (mm)", size=1.85, row_h=3.0, head_h=4.4, title_h=5.0,
              font="label", zebra=lambda i: i % 2 == 1)
    ds.text(x0, y + 2.8, "Symmetric point-to-outline distance, our OML contours vs the drawn loops. * starboard",
            1.6, "label", "start", fill=MUTED, tag="tnote")
    ds.text(x0, y + 5.0, "pane lifted onto our OML from the plan (sill ill-conditioned; information only).",
            1.6, "label", "start", fill=MUTED, tag="tnote")
    ds.log.append("deviations: " + "; ".join(f"{r[0]}/{r[1]}/{r[2]} max {r[5]}" for r in rows))
    # photos / drawing / ours
    y = table(ds, x0, y + 9.0, [("ITEM", 31.0, "l"), ("PHOTOS", 20.0, "l"), ("OURS", 16.0, "r"),
                                ("DRAWING / NOTE", 21.0, "l")],
              photo_rows(), title="vs PHOTOS (refs/photo_notes.md)", size=1.8, row_h=2.9, head_h=4.4,
              title_h=5.0, font="label", zebra=lambda i: i % 2 == 1)
    y = _footnotes(ds, x0, y + 3.2, x1, [
        "(a) perspective: ground-level cameras sit 10-15° below the window; the tumblehome shortens the glass "
        "height and flattens the top edge (0.448 m -> 0.40-0.41 m; 9.5° -> 2-6°).",
        "(b) drawing vs photos conflict: kept 0.175 (within 15 mm of the drawing) - owner to decide.",
        "(c) the side-projection slope of the windshield's outboard roof corner, not the roof plane.",
        "(d) indicative only (oblique views).",
        "(e) ratio to the glass height on PRO s/n 3010 / 3036 and the long-lens NGX photo (photo_notes: 0-0.05).",
    ], size=1.6, line_h=2.3)
    # vision (design eye, estimated)
    vis = CG.vision()
    vr = [("design eye STA / BL / WL", "{:.0f} / {:.0f} / {:.0f}".format(*(np.abs(CG.EYE) * 1000))),
          ("over the nose (eye BL, ahead)", f"{vis['over_nose_down']:.1f}° down"),
          ("abeam, over the side-window sill", f"{vis['abeam_down_over_sill']:.1f}° down"),
          ("abeam, to the side-window top", f"{vis['abeam_up_to_top']:.1f}° up"),
          ("ahead, to the windshield roof edge", f"{vis['ahead_up_to_roof_edge']:.1f}° up")]
    table(ds, x0, y + 1.5, [("VISION FROM THE DESIGN EYE (ESTIMATED)", 62.0, "l"), ("", 26.0, "r")], vr,
          title=None, size=1.8, row_h=2.9, head_h=4.0, font="label")


def _footnotes(ds, x0, y, x1, items, size=1.6, line_h=2.3):
    """Unnumbered footnotes (each item carries its own '(a)' key); returns the bottom y."""
    from drawing import sheet as S
    for it in items:
        key, _, txt = it.partition(" ")
        ds.text(x0, y, key, size, "label", "start", weight=600, tag="tnote")
        for k, ln in enumerate(S.wrap(txt, x1 - x0 - 5.0, size)):
            ds.text(x0 + 4.0, y + line_h * k, ln, size, "label", "start", tag="tnote")
            last = k
        y += line_h * (last + 1) + 0.6
    return y


def draw_notes(ds):
    x0, x1 = 245.0, 382.0
    y = notes(ds, x0, 283.0, x1, [
        "Drawn from the parameters of model/cockpit_glazing.py: zero contours of the glazing and mask "
        "signed-distance fields on the outer mould line of model/fuselage.py (sheet L1), projected. Never from "
        "the mesh. STA = m aft of the datum (3000 mm ahead of the firewall); WL above the static ground line.",
        "Every edge except the centre post is a plane normal to the plane of symmetry: straight in side "
        "projection (chain-dotted construction lines). Post: |BL| = 23. Corners filleted (side projection).",
        "PC-12 PRO: no direct-vision window; the NGX starboard single pane is used on both sides "
        "(Pilatus PRO release; photos of s/n 3001, 3010, 3036, 3066).",
        "Dark mask (filled): PRO livery item, one continuous area around all four panes - roof band, centre "
        "post, lower band with a ramp to the windshield's forward corner, straight leaning aft edge ahead of "
        "the airstair door. Mask corner radii: low-aft 60, top-aft 40, ramp 100.",
        "Windshield roof edge: its own plane (11.0°, 9 mm above the side-window top plane at STA 4000) - our "
        "crown section at STA 3900 is 5-12 mm fuller than the drawing's, so plan and front cannot both match "
        "a single plane better than ~11 / 7 mm.",
    ], title="NOTES", size=1.85, line_h=2.6)
    # legend
    lx, ly = 245.0, max(y + 2.0, 360.0)
    items = [("glass (pane outline)", dict(fill=GLASS_FILL, w=W_OBJ)), ("dark mask (PRO)", dict(fill=MASK_FILL, w=0.0)),
             ("construction plane (side projection)", dict(dash=CHAIN, color=CONSTR)),
             ("airstair door seam / max-breadth WL", dict(dash=PHANTOM, color=MUTED)),
             ("design eye, sight line", dict(dash=(3.0, 1.0), color=M.ACCENT))]
    ds.text(lx, ly, "LEGEND", 2.6, "label", "start", weight=600, tag="notes")
    for i, (lab, st) in enumerate(items):
        yy = ly + 4.0 + 3.4 * i
        if "fill" in st:
            ds.cv.rect(lx, yy - 1.2, 8.0, 2.4, lw=st["w"], fill=st["fill"], stroke=st["w"] > 0)
        else:
            ds.cv.line((lx, yy), (lx + 8.0, yy), W_FINE, st["dash"], color=st["color"])
        ds.text(lx + 10.0, yy, lab, 1.9, "label", "start", vcenter=True, tag="notes")
    scale_bar(ds, 322.0, ly + 6.0, 10, length_m=0.5, step_m=0.1)


# ---------------------------------------------------------------------------------------------- overlay
def draw_overlay(ds):
    """Private overlay: the registered Pilatus drawing in red, photo marks in blue."""
    d = M.mbp_data()
    G = d["glazing"]
    vs, vp, vf, vb = (ds.views[k] for k in ("side_port", "plan", "front", "side_stbd"))
    red_w = 0.22
    for v in (vs, vb):
        ds.ov_mbp(v, "side", kinds=("outline",), clip=SIDE_BOX, w=0.18)
        ds.ov_polylines(v, [_closed(P) for P in G["side"].values()], w=red_w, clip=SIDE_BOX)
        ds.ov_polylines(v, [_closed(P) for P in d["openings"]["side"].values()], w=0.18, clip=SIDE_BOX)
    ds.ov_mbp(vp, "plan", kinds=("outline",), clip=PLAN_BOX, w=0.18)
    ds.ov_polylines(vp, [_closed(P) for P in G["plan"].values()], w=red_w, clip=PLAN_BOX)
    ds.ov_mbp(vf, "front", kinds=("outline",), clip=FRONT_BOX, w=0.18)
    ds.ov_polylines(vf, [_closed(P) for P in G["front"].values()], w=red_w, clip=FRONT_BOX)
    # photo marks: ngx_kenia_stbd_pilatus is a starboard view -> VIEW B
    pts = np.array([(x, z) for _, x, z in PHOTO_PTS])
    ds.ov_marks(vb, pts, [lab for lab, _, _ in PHOTO_PTS], size=1.7)
    for v, key in ((vs, "side"), (vb, "side"), (vp, "plan"), (vf, "front")):
        x0, z0, x1, z1 = v.box
        X = min(v.pt(x0, z1)[0], v.pt(x1, z1)[0])
        Y = min(v.pt(x0, z1)[1], v.pt(x0, z0)[1])
        ds.ov_text(X + 1.0, Y + 3.2, f"RED: PILATUS NGX {key.upper()} VIEW (SHEET 1)", size=2.0)
    X, Y = vb.pt(3.05, 1.97)
    ds.ov_text(X - 30.0, Y - 1.0, "BLUE: PHOTO MEASUREMENTS (ngx_kenia_stbd_pilatus, +-0.05-0.1 m)", size=1.9,
               color=M.BLUE, anchor="end")
    # deviation call-outs on the overlay (worst points of the table)
    raw = getattr(ds, "_dev_raw", {}) or {}
    for (pane, view, ref), c in raw.items():
        if "*" in ref:
            continue
        v = {"side": vs, "plan": vp, "front": vf}[view]
        if c["max"] > 0.008:
            X, Y = v.pt(*c["worst"])
            ds.ov.path([(X + 1.2 * math.cos(a), Y + 1.2 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 17)],
                       0.2, None, closed=True, color=M.RED)
            ds.ov_text(X + 1.6, Y - 1.4, f"{c['max'] * 1000:.0f}", size=1.8, color=M.RED)


def evaluate(verbose=True):
    rows, raw = deviations()
    if verbose:
        for r in rows:
            print(f"{r[0]:18s} {r[1]:6s} {r[2]:20s} n={r[3]:>5s} rms {r[4]:>5s} max {r[5]:>5s} worst {r[6]:14s} {r[7]}")
        for r in photo_rows():
            print(f"  {r[0]:34s} photo {r[1]:22s} model {r[2]:14s} {r[3]}")
        print("vision", CG.vision())
    return rows, raw


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "eval":
        evaluate()
    else:
        M.main(["L2"] + sys.argv[1:])
