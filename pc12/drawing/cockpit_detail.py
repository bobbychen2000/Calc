"""
Sheet L2 -- COCKPIT GLAZING & PRO MASK, drawn from the parameters of model/cockpit_glazing.py.

    python3 -m drawing.master L2          (or: python3 -m drawing.cockpit_detail)
    python3 -m drawing.cockpit_detail eval    deviation table only (needs refs/cache)

The panes and the mask are the zero contours of the glazing signed-distance fields evaluated ON the
outer mould line of model/fuselage.py (OML.section grid, contourpy), projected into the side, plan and
front views -- the same fields the 3-D builder trims the skin with; nothing comes from the mesh.  In
side projection every edge except the centre post is a straight construction line (a plane normal to
the plane of symmetry), drawn chain-dotted with its angle.

Views (A2, 1:10, first-angle): side view from port (principal view) top left; plan below it; front
view (seen from ahead) to the right of the side view; the starboard side is shown as VIEW B (seen from
starboard, nose right) below the front view.  The overlay variant adds the registered Pilatus drawing
in red and photo-derived marks (refs/photo_notes.md) in blue.
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
        raw[(pane, view)] = c
        w = c["worst"]
        rows.append((pane, view, refname, str(c["n"]), f"{c['rms'] * 1e3:.1f}", f"{c['max'] * 1e3:.1f}",
                     f"{w[0] * 1e3:.0f} / {w[1] * 1e3:.0f}", remark))

    # side view (both panes of a side project onto the same place; the drawing shows the port side)
    add("windshield", "side", "ws_port", proj(p_ws, "side"), G["side"]["ws_port"],
        "post edge = OML at BL 23")
    add("side window", "side", "NGX port opening", proj(p_sw, "side"), ngx_opening("side"),
        "DV + main pane, post filled")
    add("side window", "side", "sw_stbd plan->OML", proj(s_sw, "side"), stbd_side_from_plan(),
        "starboard pane lifted from plan; sill ill-cond.")
    # plan
    add("windshield stbd", "plan", "ws_stbd", proj(s_ws, "plan"), G["plan"]["ws_stbd"])
    add("windshield port", "plan", "ws_port", proj(p_ws, "plan"), G["plan"]["ws_port"])
    add("side window stbd", "plan", "sw_stbd", proj(s_sw, "plan"), G["plan"]["sw_stbd"], "the PRO pane shape")
    add("side window port", "plan", "NGX port opening", proj(p_sw, "plan"), ngx_opening("plan"))
    # front
    add("windshield stbd", "front", "ws_stbd", proj(s_ws, "front"), G["front"]["ws_stbd"])
    add("windshield port", "front", "ws_port", proj(p_ws, "front"), G["front"]["ws_port"])
    add("side window stbd", "front", "sw_stbd", proj(s_sw, "front"), G["front"]["sw_stbd"])
    add("side window port", "front", "NGX port opening", proj(p_sw, "front"), ngx_opening("front"))
    return rows, raw


def photo_rows():
    """Our numbers vs the photo measurements of refs/photo_notes.md."""
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
    mask_lean = CG.MASK_AFT_LEAN_DEG
    rows = [
        ("pillar edge angle", "32-39 deg", f"{CG.PILLAR_LINE[1]:.1f} deg", "drawing 34.1-34.6"),
        ("A-pillar width (side view, horiz.)", "0.05-0.06", f"{2 * CG.PILLAR_HALF:.3f}", "drawing 0.038"),
        ("side-window sill WL", "2.09-2.11", f"{CG.SW_SILL:.3f}", "drawing 2.087 (DV 2.073)"),
        ("side-window aft extreme STA", "~4.34", f"{CG.SW_AFT:.3f}", "drawing 4.356"),
        ("glass height", "0.40 (+-6 %)", f"{H:.3f}", "drawing 0.448"),
        ("sill length / height", "1.98-2.09", f"{sill_len / H:.2f}", "front-bottom corner to aft extreme"),
        ("top length / height", "0.71-0.85", f"{top_len / H:.2f}", "top-front corner to aft extreme"),
        ("D radii top / bottom", "0.11-0.14", f"{CG.SW_R['top_aft']:.3f} / {CG.SW_R['bot_aft']:.3f}",
         "drawing ~0.12 / 0.21"),
        ("D straight vertical", "~0.15-0.19", f"{max(v_hi - v_lo, 0):.3f}", "drawing 0.06"),
        ("top edge rise (fwd)", "<= ~3 deg", f"{-CG.ROOF_LINE[1]:.1f} deg", "drawing 9-11 deg (one plane)"),
        ("centre post (glass to glass)", "0.08-0.14 (indic.)", f"{2 * CG.WS_POST:.3f}", "drawing 0.046"),
        ("mask below sill", "0.06-0.08", f"{CG.MASK_LOW:.3f}", ""),
        ("mask ramp angle", "~23 (21-27) deg", f"{CG.MASK_RAMP_DEG:.1f} deg", ""),
        ("mask forward point STA / WL", "3.17 / 2.21", "{:.3f} / {:.3f}".format(*mask_point()), "ramp meets crown"),
        ("mask aft edge lean", "7-23 deg", f"{mask_lean:.1f} deg", "bottom forward"),
        ("mask aft margin bottom / top", "0.07 / 0.15-0.20",
         f"{mk['mask_low_aft'][0] - CG.SW_AFT:.3f} / {mk['mask_top_aft'][0] - CG.SW_AFT:.3f}", "from the aft extreme"),
        ("mask top margin", "0-0.05", f"{CG.MASK_TOP_MARGIN:.3f}", "normal to the top edge"),
        ("mask aft edge to airstair frame", "~0.05-0.10", f"{4.650 - mk['mask_top_aft'][0]:.3f}",
         "door fwd edge STA 4650 (drawing)"),
    ]
    return rows


def mask_point():
    """Forward point of the mask in side view: the ramp line meets the crown profile."""
    xs = np.linspace(3.0, 3.6, 6001)
    z_ramp = CG.SW_SILL - CG.MASK_LOW + (CG.MASK_RAMP_X - xs) * math.tan(math.radians(CG.MASK_RAMP_DEG))
    k = int(np.argmin(np.abs(F.z_top(xs) - z_ramp)))
    return float(xs[k]), float(z_ramp[k])


# =====================================================================================================
# sheet
# =====================================================================================================
def starboard_view(name, origin, scale, model_origin, box=None):
    """Side view seen from STARBOARD (nose right): (x, z) -> sheet."""
    k = 1000.0 / scale
    A = np.array([[-k, 0.0], [0.0, -k]])
    t = np.asarray(origin, float) - A @ np.asarray(model_origin, float)
    return M.View(name, "xz", A, t, float(scale), box, "seen from starboard, nose right")


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


# view boxes (model units)
SIDE_BOX = (3.00, 1.90, 4.80, 2.85)
PLAN_BOX = (3.00, -0.92, 4.80, 0.92)
FRONT_BOX = (-0.95, 1.90, 0.95, 2.85)


def draw_clean(ds):
    ds.frame_and_title(tb_width=190.0)
    E = glazing_edges()
    vs = ds.add_view(side_view("side_port", origin=(40.0, 42.0), scale=10, model_origin=(3.00, 2.85),
                               box=SIDE_BOX))
    vp = ds.add_view(plan_view("plan", origin=(40.0, 190.0), scale=10, model_origin=(3.00, 0.0), box=PLAN_BOX))
    vf = ds.add_view(front_view("front", origin=(345.0, 42.0), scale=10, model_origin=(0.0, 2.85),
                                box=FRONT_BOX))
    vb = ds.add_view(starboard_view("side_stbd", origin=(435.0, 175.0), scale=10, model_origin=(3.00, 2.85),
                                    box=SIDE_BOX))
    draw_side(ds, vs, E, side=-1)
    draw_side(ds, vb, E, side=+1)
    draw_plan(ds, vp, E)
    draw_front(ds, vf, E)
    draw_tables(ds)


# ---------------------------------------------------------------------------------------------- helpers
def _fill_region(ds, v, P, fill, w=0.0, color=None):
    ds.cv.path(v.pts(P), w, None, closed=True, fill=fill, stroke=w > 0, color=color)


def _outline(ds, v, P, w=W_OBJ, dash=None, color=None, closed=True):
    ds.cv.path(v.pts(P), w, dash, closed=closed, color=color)


def _side_mask_region():
    """Mask region in side projection clipped to the fuselage silhouette (crown)."""
    O = CG.side_outline("mask")
    xs = np.linspace(SIDE_BOX[0], SIDE_BOX[2], 1801)
    zc = F.z_top(xs)
    # polygon clip: keep outline points below the crown, replace the rest by the crown line
    from matplotlib.path import Path as MPath
    inside = MPath(np.vstack([O, O[:1]]))
    crown_in = inside.contains_points(np.c_[xs, zc - 1e-5])
    below = O[:, 1] <= F.z_top(O[:, 0])
    # walk the outline, splice the crown where the outline leaves the skin
    out = []
    n = len(O)
    i0 = int(np.argmax(~below)) if (~below).any() else 0
    order = np.r_[np.arange(i0, n), np.arange(0, i0)]
    prev_below = False
    for i in order:
        if below[i]:
            out.append(O[i])
        elif prev_below:
            pass
        prev_below = below[i]
    P = np.array(out)
    # crown segment between the two crossing stations
    xa, xb = xs[crown_in].min(), xs[crown_in].max()
    cx = np.linspace(xa, xb, 300)
    C = np.c_[cx, F.z_top(cx)]
    # P runs counter-clockwise starting after the region above the crown (aft end of the crown piece)
    return np.vstack([P, C[::-1] if np.linalg.norm(P[-1] - C[-1]) < np.linalg.norm(P[-1] - C[0]) else C])


def _silhouette_side(ds, v, side):
    """Fuselage lines in the side view: crown silhouette, max-breadth WL, cowl joint, airstair door."""
    xs = np.linspace(SIDE_BOX[0], SIDE_BOX[2], 900)
    ds.cv.path(v.pts(np.c_[xs, F.z_top(xs)]), W_OBJ)
    zm = F.z_mw(xs)
    ok = zm >= SIDE_BOX[1]
    for r in _runs(ok):
        ds.cv.path(v.pts(np.c_[xs[r], zm[r]]), W_FINE, CHAIN, color=MUTED)
    X, Y = v.pt(4.72, float(F.z_mw(4.72)) + 0.012)
    ds.text(X, Y, "MAX-BREADTH WL", 2.0, "label", "middle", fill=MUTED, tag="lbl")


def _grid_side(ds, v, labels=True):
    frames = {k: F.FRAMES[k] for k in ("FR10", "FR12", "FR14", "FR16")}
    x0, z0, x1, z1 = SIDE_BOX
    for name, x in dict(FIREWALL=3.000, **frames).items():
        p, q = v.pt(x, z0), v.pt(x, z1)
        ds.cv.line(p, q, W_GRID, None if name != "FIREWALL" else (5.0, 1.0, 0.8, 1.0), color=GRID)
        if labels:
            ds.text(q[0], q[1] - 4.2, name, 2.2, "label", "middle", weight=600, fill=GRID, tag="grid")
            ds.text(q[0], q[1] - 1.2, f"{x * 1000:.0f}", 2.0, "mono", "middle", fill=GRID, tag="grid")
    for z in (2.0, 2.2, 2.4, 2.6, 2.8):
        p, q = v.pt(x0, z), v.pt(x1, z)
        ds.cv.line(p, q, W_GRID, color=GRID)
        if labels:
            e = p if p[0] < q[0] else q
            ds.text(e[0] - 1.5, e[1], f"WL {z * 1000:.0f}", 2.0, "mono", "end", vcenter=True, fill=GRID,
                    tag="grid")


def draw_side(ds, v, E, side):
    cv = ds.cv
    _grid_side(ds, v, labels=True)
    # mask (filled) and panes
    try:
        R = _side_mask_region()
    except Exception as e:                      # noqa: BLE001
        ds.log.append(f"mask region fallback: {e}")
        R = CG.side_outline("mask")
    _fill_region(ds, v, R, MASK_FILL)
    s = "stbd" if side > 0 else "port"
    sw = proj(E[s]["sw"], "side")
    ws = proj(E[s]["ws"], "side")
    _fill_region(ds, v, sw, GLASS_FILL)
    _fill_region(ds, v, ws, GLASS_FILL)
    _outline(ds, v, sw)
    _outline(ds, v, ws)
    _outline(ds, v, R, w=W_FINE)
    _silhouette_side(ds, v, side)
    _construction_side(ds, v)
    if side < 0:
        # airstair door forward frame (port only; drawn door outline STA 4650, reference)
        p, q = v.pt(4.650, 1.90), v.pt(4.650, 2.629)
        cv.line(p, q, W_FINE, PHANTOM, color=MUTED)
        X, Y = v.pt(4.655, 1.935)
        ds.text(X + 1.0, Y, "AIRSTAIR DOOR FWD EDGE 4650", 2.0, "label", "start", fill=MUTED, tag="lbl")
        _dims_side(ds, v)
        _eye_side(ds, v)
    else:
        _labels_stbd(ds, v)


def _construction_side(ds, v):
    """The planes normal to the plane of symmetry (straight lines in side projection), chain-dotted."""
    x0, z0, x1, z1 = SIDE_BOX

    def seg(pt, deg, xa, xb):
        (px, pz) = pt
        t = math.tan(math.radians(deg))
        return np.array([[xa, pz + (xa - px) * t], [xb, pz + (xb - px) * t]])

    L = [seg(*CG.SILL_LINE, 3.20, 3.66), seg(*CG.ROOF_LINE, 3.78, 4.45),
         seg((CG.x_pillar(2.3), 2.3), CG.PILLAR_LINE[1], CG.x_pillar(2.06), CG.x_pillar(2.62))]
    for P in L:
        ds.cv.path(v.pts(P), W_THIN, CHAIN, color=CONSTR)


def _dims_side(ds, v):
    """Dimensions on the port side view (ordinates from the firewall STA 3000 and WL grid)."""
    sh = ds.sh
    K = CG.key_points()
    mp = mask_point()
    # --- station ordinates above the view (baseline FIREWALL)
    feats = [("WS TIP", (float(E_tip()[0]), float(E_tip()[1]))),
             ("MASK", mp), ("SW FWD", tuple(K["sw_low_front"])), ("SW TOP FWD", tuple(K["sw_top_front"])),
             ("SW AFT", (CG.SW_AFT, 2.36)), ("MASK AFT", tuple(K["mask_top_aft"]))]
    ytxt = v.pt(0, 2.85)[1] - 12.0
    for lab, (x, z) in feats:
        X, Y = v.pt(x, z)
        ds.cv.line((X, Y - 0.8), (X, ytxt + 1.5), W_THIN, (1.2, 0.8), color=INK)
        ds.text(X + 0.9, ytxt, f"{x * 1000:.0f}", 2.3, "mono", "start", rot=-90, tag="ord")
    X0 = v.pt(3.0, 2.85)[0]
    ds.text(X0 - 1.0, ytxt - 3.0, "STA", 2.2, "label", "end", weight=600, tag="ord")
    # --- WL ordinates at the right of the view
    xr = v.pt(4.80, 0)[0] + 3.0
    wls = [("SW TOP FWD", K["sw_top_front"][1]), ("SW SILL", CG.SW_SILL), ("MASK LOWER EDGE", CG.SW_SILL - CG.MASK_LOW),
           ("WS LOW AFT", K["ws_low_aft"][1])]
    used = []
    for lab, z in sorted(wls, key=lambda t: -t[1]):
        Y = v.pt(0, z)[1]
        Yt = Y
        while any(abs(Yt - u) < 3.2 for u in used):
            Yt += 3.2
        used.append(Yt)
        ds.cv.line(v.pt(4.62, z), (xr, Y), W_THIN, (1.2, 0.8), color=INK)
        ds.text(xr + 1.0, Yt, f"WL {z * 1000:.0f}  {lab}", 2.2, "mono", "start", vcenter=True, tag="ord")
    # --- angles
    pl = (float(CG.x_pillar(2.20)), 2.20)
    X, Y = v.pt(*pl)
    a = CG.PILLAR_LINE[1]
    sh.angle_dim((X, Y), 180.0, 180.0 + a, 14.0, f"{a:.1f}°", (X - 22.0, Y - 5.5), tag="dim")
    ds.cv.line((X - 16.0, Y), (X, Y), W_THIN)
    # sill plane angle
    sp = (3.30, float(CG.z_ws_sill(3.30)))
    X, Y = v.pt(*sp)
    b = -CG.SILL_LINE[1]
    ds.cv.line((X, Y), (X + 16.0, Y), W_THIN)
    sh.angle_dim((X, Y), 0.0, b, 13.0, f"{b:.1f}°", (X + 13.5, Y + 5.2), tag="dim")
    # mask ramp angle
    rp = (3.40, CG.SW_SILL - CG.MASK_LOW + (CG.MASK_RAMP_X - 3.40) * math.tan(math.radians(CG.MASK_RAMP_DEG)))
    X, Y = v.pt(*rp)
    c = CG.MASK_RAMP_DEG
    ds.cv.line((X, Y), (X + 18.0, Y), W_THIN)
    sh.angle_dim((X, Y), 0.0, c, 16.0, f"{c:.0f}°", (X + 16.5, Y + 8.0), tag="dim")
    # radii / lean / widths as call-outs
    cx = CG.SW_AFT - CG.SW_R["bot_aft"] * (1 - math.cos(math.radians(45)))
    cz = CG.SW_SILL + CG.SW_R["bot_aft"] * (1 - math.sin(math.radians(45)))
    callout(ds, v, (cx, cz), f"R {CG.SW_R['bot_aft'] * 1000:.0f}", offset=(10.0, 16.0), color=INK, size=2.3)
    ta = CG.key_points()["sw_top_aft"]
    callout(ds, v, (ta[0] - 0.035, ta[1] - 0.012), f"R {CG.SW_R['top_aft'] * 1000:.0f}", offset=(12.0, -14.0),
            color=INK, size=2.3)
    ma = K["mask_top_aft"]
    callout(ds, v, (0.5 * (ma[0] + K["mask_low_aft"][0]), 0.5 * (ma[1] + K["mask_low_aft"][1])),
            f"MASK AFT EDGE LEAN {CG.MASK_AFT_LEAN_DEG:.0f}°", offset=(10.0, -18.0), color=INK, size=2.3,
            lines=[f"STA {K['mask_low_aft'][0] * 1000:.0f} (LOW) - {ma[0] * 1000:.0f} (TOP)"])
    pz = 2.43
    callout(ds, v, (float(CG.x_pillar(pz)), pz), f"A-PILLAR {CG.PILLAR_WIDTH * 1000:.0f} NORMAL",
            offset=(-14.0, -16.0), color=INK, size=2.3, lines=[f"({2 * CG.PILLAR_HALF * 1000:.0f} HORIZ.)"])


def E_tip():
    """Forward-most windshield point in side view (sill plane at the post)."""
    xs = np.linspace(3.1, 3.5, 4001)
    zc = F.z_at(xs, np.full_like(xs, CG.WS_POST), upper=True)
    k = int(np.argmin(np.abs(zc - CG.z_ws_sill(xs))))
    return xs[k], float(zc[k])


def _eye_side(ds, v):
    e = CG.EYE
    X, Y = v.pt(e[0], e[2])
    ds.cv.circle(X, Y, 1.4, w=W_FINE, fill=PAPER)
    ds.cv.line((X - 2.2, Y), (X + 2.2, Y), W_FINE)
    ds.cv.line((X, Y - 2.2), (X, Y + 2.2), W_FINE)
    vis = CG.vision()
    a = math.radians(vis["over_nose_down"])
    L = 1.05
    P = np.array([[e[0], e[2]], [e[0] - L * math.cos(a), e[2] - L * math.sin(a)]])
    P[1] = [max(P[1][0], SIDE_BOX[0]), e[2] - (e[0] - max(P[1][0], SIDE_BOX[0])) * math.tan(a)]
    ds.cv.path(v.pts(P), W_THIN, (3.0, 1.0), color=M.ACCENT)
    ds.text(X + 2.6, Y + 3.8, f"EYE {e[0] * 1000:.0f} / BL {abs(e[1]) * 1000:.0f} / WL {e[2] * 1000:.0f}", 2.0,
            "mono", "start", fill=M.ACCENT, tag="eye")
    Xl, Yl = v.pt(3.25, e[2] - (e[0] - 3.25) * math.tan(a))
    ds.text(Xl, Yl - 1.2, f"OVER-NOSE {vis['over_nose_down']:.1f}° DOWN", 2.0, "label", "start",
            fill=M.ACCENT, tag="eye", rot=math.degrees(a))


def _labels_stbd(ds, v):
    K = CG.key_points()
    callout(ds, v, (3.95, CG.SW_SILL), f"SILL WL {CG.SW_SILL * 1000:.0f}", offset=(-10.0, 16.0), color=INK,
            size=2.3)
    callout(ds, v, tuple(K["sw_low_front"]), "LOWER-FRONT EDGE ON THE", offset=(-14.0, 12.0), color=INK,
            size=2.3, lines=["WINDSHIELD SILL PLANE"])
    callout(ds, v, (4.20, float(CG.z_sw_top(4.20))), "TOP EDGE ON THE", offset=(12.0, -12.0), color=INK,
            size=2.3, lines=["WINDSHIELD ROOF PLANE"])
    mp = mask_point()
    callout(ds, v, mp, f"MASK POINT {mp[0] * 1000:.0f} / {mp[1] * 1000:.0f}", offset=(-8.0, 12.0), color=INK,
            size=2.3, lines=["RAMP MEETS THE CROWN"])


def draw_plan(ds, v, E):
    cv = ds.cv
    x0, y0, x1, y1 = PLAN_BOX
    frames = {k: F.FRAMES[k] for k in ("FR10", "FR12", "FR14", "FR16")}
    for name, x in dict(FIREWALL=3.000, **frames).items():
        cv.line(v.pt(x, y0), v.pt(x, y1), W_GRID, None if name != "FIREWALL" else (5.0, 1.0, 0.8, 1.0), color=GRID)
        X, Y = v.pt(x, y0)
        ds.text(X, Y + 3.4, f"{x * 1000:.0f}", 2.0, "mono", "middle", fill=GRID, tag="grid")
    for y in (-0.8, -0.4, 0.4, 0.8):
        p, q = v.pt(x0, y), v.pt(x1, y)
        cv.line(p, q, W_GRID, color=GRID)
        ds.text(p[0] - 1.5, p[1], f"BL {abs(y) * 1000:.0f} {'S' if y > 0 else 'P'}", 2.0, "mono", "end",
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
    # fuselage outline (max half-breadth) in plan
    xs = np.linspace(x0, x1, 600)
    for sgn in (1, -1):
        cv.path(v.pts(np.c_[xs, sgn * F.half_w(xs)]), W_OBJ)
    # post width dimension
    sh = ds.sh
    xa = 3.62
    pa, pb = v.pt(xa, CG.WS_POST), v.pt(xa, -CG.WS_POST)
    X = v.pt(3.10, 0)[0]
    sh.dim(pa, pb, X, f"{2 * CG.WS_POST * 1000:.0f}", orient="v", text_side="after")
    ds.text(X - 6.0, v.pt(0, 0.12)[1], "POST", 2.2, "label", "middle", tag="lbl")
    # extreme stations of the panes
    ws = proj(E["stbd"]["ws"], "plan")
    sw = proj(E["stbd"]["sw"], "plan")
    callout(ds, v, (ws[:, 0].min(), ws[np.argmin(ws[:, 0]), 1]), f"WS FWD {ws[:, 0].min() * 1000:.0f}",
            offset=(-2.0, -22.0), color=INK, size=2.3)
    callout(ds, v, (sw[:, 0].max(), sw[np.argmax(sw[:, 0]), 1]), f"SW AFT {sw[:, 0].max() * 1000:.0f}",
            offset=(14.0, -8.0), color=INK, size=2.3)
    k = int(np.argmax(ws[:, 1]))
    callout(ds, v, tuple(ws[k]), f"WS MAX BL {ws[k, 1] * 1000:.0f}", offset=(-12.0, -10.0), color=INK, size=2.3)


def draw_front(ds, v, E):
    cv = ds.cv
    y0, z0, y1, z1 = FRONT_BOX
    for y in (-0.8, -0.4, 0.0, 0.4, 0.8):
        p, q = v.pt(y, z0), v.pt(y, z1)
        cv.line(p, q, W_GRID if y else W_FINE, None if y else CHAIN, color=GRID if y else MUTED)
        ds.text(q[0], q[1] - 1.2, "CL" if y == 0 else f"BL {abs(y) * 1000:.0f} {'S' if y > 0 else 'P'}", 2.0,
                "mono", "middle", fill=GRID, tag="grid")
    for z in (2.0, 2.2, 2.4, 2.6, 2.8):
        p, q = v.pt(y0, z), v.pt(y1, z)
        cv.line(p, q, W_GRID, color=GRID)
        ds.text(q[0] + 1.5, q[1], f"WL {z * 1000:.0f}", 2.0, "mono", "start", vcenter=True, fill=GRID, tag="grid")
    # fuselage silhouette at the widest station of the view box (FR16) and the section at FR10
    t = np.linspace(0, 1, 721)
    for x, w, dash in ((4.59, W_OBJ, None), (3.08, W_FINE, (2.0, 0.8))):
        P = F.section(np.full_like(t, x), t)
        ok = P[:, 2] >= z0
        for r in _runs(ok):
            cv.path(v.pts(P[r][:, [1, 2]]), w, dash, color=None if dash is None else MUTED)
    X, Y = v.pt(-0.42, float(F.z_at(3.08, 0.42)) - 0.02)
    ds.text(X, Y, "FR10 3080", 2.0, "mono", "middle", fill=MUTED, tag="lbl")
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
    zt = 2.45
    sh.dim(v.pt(CG.WS_POST, zt), v.pt(-CG.WS_POST, zt), v.pt(0, 2.72)[1], f"{2 * CG.WS_POST * 1000:.0f}",
           orient="h", text_side="after")


def draw_tables(ds):
    # deviation table (our numbers) -- right of the front view
    try:
        rows, raw = deviations()
        ds._dev_raw = raw
    except Exception as e:                      # noqa: BLE001
        rows = [("(reference not available)", "", "", "", "", "-", "", str(e)[:60])]
        ds.log.append(f"deviation table: reference not available ({e})")
    cols = [("PANE", 25.0, "l"), ("VIEW", 10.0, "l"), ("REFERENCE", 27.0, "l"), ("N", 8.0, "r"),
            ("RMS", 9.0, "r"), ("MAX", 9.0, "r"), ("WORST AT", 20.0, "l")]
    y = table(ds, 395.0 + 145.0 - 108.0 - 0.0 + 0.0, 250.0, cols, [r[:7] for r in rows],
              title="GLAZING vs PILATUS 190.10.40.432 SHEET 1 (mm)", size=2.0, row_h=3.2, font="label",
              zebra=lambda i: i % 2 == 1)
    ds.log.append("deviations: " + "; ".join(f"{r[0]}/{r[1]} max {r[5]}" for r in rows))


def evaluate(verbose=True):
    rows, raw = deviations()
    if verbose:
        for r in rows:
            print(f"{r[0]:18s} {r[1]:6s} {r[2]:20s} n={r[3]:>5s} rms {r[4]:>5s} max {r[5]:>5s} worst {r[6]:14s} {r[7]}")
        for r in photo_rows():
            print(f"  {r[0]:36s} photo {r[1]:18s} model {r[2]:14s} {r[3]}")
        print("vision", CG.vision())
    return rows, raw


def draw_overlay(ds):
    pass


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "eval":
        evaluate()
    else:
        M.main(["L2"] + sys.argv[1:])
