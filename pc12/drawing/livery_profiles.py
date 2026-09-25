"""
Sheet L5 -- LIVERY - MSN 3008 SCHEME: the paint scheme of PC-12 PRO MSN 3008 (N81DW) as flat-colour
profiles, drawn FROM THE PARAMETERS: the livery curves of model/livery.py (the same side-projection strokes /
regions and per-surface colours the 3-D painter uses) on the Stage-2 outlines of model/fuselage.py (OML
control lines), model/cockpit_glazing.py (panes, PRO mask), model/fuselage_parts.py (windows, doors, exit),
model/wing.py, model/empennage.py, model/gear.py + bays.py, model/details.py and model/powerplant.py.

    python3 -m drawing.master L5          (or: python3 -m drawing.livery_profiles)

Views: port side and starboard side (1:30), split plan (1:50: upper surfaces above the centre line, lower
surfaces below, starboard half; the scheme is symmetric), VIEW C front (1:30, wings broken at BL 2600), DETAIL A
blade tip bands (1:5); colour legend (material names, sRGB design colours, PBR values), per-surface colour table,
livery-curve table (with the photo check per stroke), photo-source table and notes.  Every painted area is the
zero-sublevel set of the painter's field evaluated on a 3 mm (side) / 4 mm (plan, front) model grid and contoured
(contourpy): side views use the field at (x, z), plan views at (x, z_OML(x, y)), the front view at the forward-most
OML point of each (y, z).

Private outputs (git-ignored refs/cache/overlays/): the OVERLAY variant (Pilatus drawing 190.10.40.432 in red,
white-stroke centres measured on the rectified photos in blue), and

    python3 -m drawing.livery_profiles marks     measure the white strokes on the camera-matched photos
                                                 -> overlays/livery/measurements.json (+ per-stroke residuals)
    python3 -m drawing.livery_profiles compare   -> overlays/L5_photo_compare.png: each photo next to our scheme
                                                 rendered through the same camera, then the photos rectified onto
                                                 the side projection above the sheet's port view

Camera calibrations (pinhole, fitted to named model points) live in refs/cache/overlays/livery/cams.json.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from drawing import master as M  # noqa: E402
from drawing.master import (INK, GRID, MUTED, W_FINE, W_THIN, W_GRID, PHANTOM, CHAIN,  # noqa: E402
                            table, notes, view_title, scale_bar, side_view, plan_view)
from model import fuselage as F  # noqa: E402
from model import livery as L  # noqa: E402
from model import cockpit_glazing as CG  # noqa: E402
from model import fuselage_parts as FP  # noqa: E402
from model import wing as W  # noqa: E402
from model import empennage as E  # noqa: E402
from model import gear as G  # noqa: E402
from model import bays as BY  # noqa: E402
from model import details as D  # noqa: E402
from model import powerplant as PP  # noqa: E402
from model.lifting import cos_pts  # noqa: E402

SHEET = dict(id="L5", title="LIVERY - MSN 3008 SCHEME", subtitle="LIVERY - MSN 3008 (N81DW) SCHEME", size="A1",
             scale="AS SHOWN", rev="A", order=50)

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "refs" / "cache"
LIV_CACHE = CACHE / "overlays" / "livery"          # private: camera calibrations, photo measurements
EDGE = "#14191D"                                    # outline ink of the coloured profiles
XC = cos_pts(60)
X0_SIDE, X1_SIDE = F.STA["cowl_front"], F.STA["tail_end"]
STEP_SIDE, STEP_PLAN = 0.003, 0.004


def col(name):
    return L.drawing_color(name)


# ================================================================================================ geometry
def _runs(mask):
    idx = np.where(mask)[0]
    if not len(idx):
        return []
    br = np.where(np.diff(idx) > 1)[0]
    return [r for r in np.split(idx, br + 1) if len(r) >= 2]


def dorsal_top(x):
    """Side-view top edge of the dorsal fin (straight edge, then the Bezier blend into the fin LE)."""
    cur = E._dorsal_curve(64)
    x = np.asarray(x, float)
    straight = E.DORSAL_Z0 + E.DORSAL_SLOPE * (x - E.DORSAL_X0)
    return np.where(x <= cur[0, 0], straight, np.interp(x, cur[:, 0], cur[:, 1]))


def ventral_edge(x):
    (x0, z0), (x1, z1) = E.VENTRAL_EDGE
    return z0 + (z1 - z0) * (np.asarray(x, float) - x0) / (x1 - x0)


def strake_side_field(x, z):
    """Side view of the ventral strake plate (root line, tip line, aft edge)."""
    (r0x, r0z), (r1x, r1z) = E.STRAKE_ROOT
    (t0x, t0z), (t1x, t1z) = E.STRAKE_TIP
    zr = r0z + (r1z - r0z) * (x - r0x) / (r1x - r0x)
    zt = np.where(x <= t1x, t0z + (t1z - t0z) * (x - t0x) / (t1x - t0x),
                  t1z + (r1z - t1z) * (x - t1x) / (r1x - t1x))
    return np.maximum.reduce([t0x - x, x - r1x, zt - z, z - zr])


def body_fields(x, z):
    """Side-view silhouette fields (negative inside): fuselage, dorsal, fin + rudder (+ ventral part), strakes."""
    xc = np.clip(x, X0_SIDE, X1_SIDE)
    fus = np.maximum.reduce([F.z_bot(xc) - z, z - F.z_top(xc), X0_SIDE - x, x - X1_SIDE])
    dors = np.maximum.reduce([E.DORSAL_X0 - x, F.z_top(xc) - 0.02 - z, z - dorsal_top(x), x - E.fin_le(z) - 0.02,
                              x - X1_SIDE])
    ahead = x < E.VENTRAL_EDGE[0][0]                 # ahead of the ventral edge the fin stands on the crown
    vent = np.where(ahead, F.z_top(xc) - 0.02, ventral_edge(x))
    fin = np.maximum.reduce([E.fin_le(z) - x, x - E.fin_te(z), vent - z, z - 4.08])
    stk = strake_side_field(x, z)
    return dict(fus=fus, dorsal=dors, fin=fin, strake=stk)


def wing_side_envelope(y0, y1, frac=(0.0, 1.0), ny=60, nx=900):
    """Side projection of the wing panel between butt lines y0..y1 (chord fractions frac): per station the
    min / max WL over the sections -> closed (N, 2) outline, or None."""
    ys = np.linspace(y0, y1, ny)
    secs = [W.section_at(y) for y in ys]
    xs_all = np.array([[s.le[0] + f * s.chord for f in frac] for s in secs])
    xa, xb = xs_all.min(), xs_all.max()
    xg = np.linspace(xa, xb, nx)
    lo = np.full(nx, np.inf)
    hi = np.full(nx, -np.inf)
    t = np.linspace(frac[0], frac[1], 120)
    for s in secs:
        U, Lw = s.upper(t), s.lower(t)
        for P in (U, Lw):
            o = np.argsort(P[:, 0])
            px, pz = P[o, 0], P[o, 2]
            inside = (xg >= px[0]) & (xg <= px[-1])
            if not inside.any():
                continue
            zz = np.interp(xg[inside], px, pz)
            lo[inside] = np.minimum(lo[inside], zz)
            hi[inside] = np.maximum(hi[inside], zz)
        # the section's own LE / TE vertical closures
    ok = np.isfinite(lo) & np.isfinite(hi)
    if ok.sum() < 3:
        return None
    xg, lo, hi = xg[ok], lo[ok], hi[ok]
    return np.r_[np.c_[xg, hi], np.c_[xg[::-1], lo[::-1]]]


def winglet_secs():
    return W.winglet_sections(40, 30)


def winglet_side_outline():
    """Side projection of the winglet: envelope of its sections (x, z)."""
    pts = []
    for s in winglet_secs():
        U, Lw = s.upper(XC), s.lower(XC)
        pts.append(np.vstack([U, Lw]))
    P = np.vstack(pts)[:, [0, 2]]
    return _hull(P)


def _hull(P):
    """Convex hull (monotone chain) of (N, 2) points -> closed ring (counter-clockwise)."""
    P = np.unique(np.round(P, 6), axis=0)
    P = P[np.lexsort((P[:, 1], P[:, 0]))]

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in P:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(tuple(p))
    for p in P[::-1]:
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(tuple(p))
    return np.array(lower[:-1] + upper[:-1])


def winglet_plan(which="le"):
    secs = winglet_secs()
    le = np.array([s.point(np.array(0.0), np.array(0.0)) for s in secs])
    te = np.array([s.point(np.array(1.0), np.array(0.0)) for s in secs])
    return le, te, secs


def section_outline(sec, n=XC):
    return np.vstack([sec.lower(n[::-1]), sec.upper(n[1:])])


def stab_plan_outline(sg=1):
    ys = np.linspace(0.0, E.STAB_TIP_Y - 0.002, 120)
    le = np.array([E.stab_le(y) for y in ys])
    te = np.array([E.stab_te(y) for y in ys])
    return np.r_[np.c_[le, sg * ys], np.c_[te[::-1], sg * ys[::-1]]]


def wing_plan_outline(sg=1, y0=None):
    y0 = float(F.half_w(6.0)) - 0.01 if y0 is None else y0
    ys = np.linspace(y0, W.SEMI, 160)
    return np.r_[np.c_[W.x_le(ys), sg * ys], np.c_[W.x_te(ys)[::-1], sg * ys[::-1]]]


def boot_plan_outline(sg=1, frac=0.10):
    ys = np.linspace(*W.BOOT_Y, 120)
    xl = W.x_le(ys)
    return np.r_[np.c_[xl, sg * ys], np.c_[(xl + frac * W.chord(ys))[::-1], sg * ys[::-1]]]


def stab_boot_outline(sg=1, frac=0.08):
    ys = np.linspace(0.0, E.STAB_TIP_RIB, 80)
    le = np.array([E.stab_le(y) for y in ys])
    te = np.array([E.stab_te(y) for y in ys])
    return np.r_[np.c_[le, sg * ys], np.c_[(le + frac * (te - le))[::-1], sg * ys[::-1]]]


def pod_plan(y_sign=1):
    prof = np.array(D.radar_pod_profile(60))
    body = np.r_[np.c_[prof[:, 0], D.POD_Y + prof[:, 1]], np.c_[prof[::-1, 0], D.POD_Y - prof[::-1, 1]]]
    m = prof[:, 0] <= D.POD_X_JOINT
    rad = np.r_[np.c_[prof[m, 0], D.POD_Y + prof[m, 1]], np.c_[prof[m][::-1, 0], D.POD_Y - prof[m][::-1, 1]]]
    return body * [1, y_sign], rad * [1, y_sign]


def pod_side():
    prof = np.array(D.radar_pod_profile(60))
    body = np.r_[np.c_[prof[:, 0], D.POD_Z + prof[:, 1]], np.c_[prof[::-1, 0], D.POD_Z - prof[::-1, 1]]]
    m = prof[:, 0] <= D.POD_X_JOINT
    rad = np.r_[np.c_[prof[m, 0], D.POD_Z + prof[m, 1]], np.c_[prof[m][::-1, 0], D.POD_Z - prof[m][::-1, 1]]]
    return body, rad


def spinner_outline(axis=F.PROP_AXIS_Z):
    """Side-view spinner outline (x, z) on the tilted thrust axis (powerplant.spinner_silhouette); `axis` shifts
    the WL of the disc centre (default: the fixed prop axis WL 1655)."""
    return PP.spinner_silhouette("side", 80) + [0.0, axis - F.PROP_AXIS_Z]


def tilt_about(P, c, deg):
    """Rotate view points P (N, 2) about c by deg (counter-clockwise in the view's (a, b) axes)."""
    a = np.radians(deg)
    R = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    return (np.asarray(P, float) - c) @ R.T + c


def exhaust_stack(sgn=1, n=24):
    """Stack centre path (n, 3) + plan / vertical half-sizes (model/powerplant.py STACK_PTS / STACK_AB)."""
    return PP.exhaust_stack_path(sgn, n), PP.STACK_AB[0], PP.STACK_AB[1]


def stack_collar_x(sgn=1):
    """Station where the heat-blackened outlet collar (the last PP.STACK_COLLAR of the path) begins."""
    path = PP.exhaust_stack_path(sgn, 200)
    s = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
    return float(np.interp(s[-1] - PP.STACK_COLLAR, s, path[:, 0]))


def stack_front_silhouette(sgn=1, nbin=70):
    """Front-view (y, z) silhouette of the whole swept stack tube (all section rings projected), as a closed
    polygon: upper and lower envelope per BL bin (the tube is BL-monotone)."""
    rings, _ = PP.exhaust_stack_rings(sgn, 160, 72)
    Q = rings.reshape(-1, 3)[:, 1:]
    yb = np.linspace(Q[:, 0].min(), Q[:, 0].max(), nbin + 1)
    k = np.clip(np.digitize(Q[:, 0], yb) - 1, 0, nbin - 1)
    up, lo, yc = [], [], []
    for i in range(nbin):
        m = k == i
        if m.any():
            yc.append(0.5 * (yb[i] + yb[i + 1]))
            up.append(Q[m, 1].max())
            lo.append(Q[m, 1].min())
    yc = np.array(yc)
    yc[0], yc[-1] = Q[:, 0].min(), Q[:, 0].max()
    return np.r_[np.c_[yc, up], np.c_[yc[::-1], np.array(lo)[::-1]]]


# schematic propeller blade (Stage 3: powerplant.blade_geometry should expose its chord law)
BLADE_R = [0.155, 0.214, 0.294, 0.467, 0.734, 1.001, 1.202, 1.295, 1.335]
BLADE_C = [0.085, 0.100, 0.155, 0.200, 0.214, 0.196, 0.160, 0.118, 0.05]


def blade_outline(rmin=0.25, width_scale=0.55):
    """Schematic blade seen normal to the disc (radius r, half-width): used edge-on in the side views."""
    r = np.linspace(rmin, PP.PROP_R, 60)
    c = np.interp(r, BLADE_R, BLADE_C) * width_scale
    return r, c / 2


# ================================================================================================ painting
def contour_fill(ds, view, a, b, Fv, color, simplify=0.0012, keep=None, lw=0.0):
    """Fill the region Fv < 0 of a field sampled on the grid a (na,) x b (nb,) (Fv shape (nb, na)), in the
    view's natural coordinates.  Holes are refilled with keep(ring) -> colour (or left open)."""
    import contourpy
    if not (Fv < 0).any():
        return 0
    gen = contourpy.contour_generator(a, b, Fv, fill_type=contourpy.FillType.OuterOffset, name="serial")
    polys, offs = gen.filled(-1e9, 0.0)
    n = 0
    for P, o in zip(polys, offs):
        rings = [P[o[i]:o[i + 1]] for i in range(len(o) - 1)]
        for k, R in enumerate(rings):
            R = rdp(R, simplify)
            if len(R) < 3:
                continue
            if k == 0:
                ds.cv.polygon(view.pts(R), fill=color, w=lw, stroke=lw > 0, color=color)
                n += 1
            elif keep is not None:
                c2 = keep(R)
                if c2:
                    ds.cv.polygon(view.pts(R), fill=c2)
    return n


def rdp(P, eps):
    """Ramer-Douglas-Peucker simplification of a polyline (N, 2)."""
    P = np.asarray(P, float)
    if len(P) < 4 or eps <= 0:
        return P
    keep = np.zeros(len(P), bool)
    keep[0] = keep[-1] = True
    stack = [(0, len(P) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a, b = P[i], P[j]
        d = b - a
        L2 = d @ d
        seg = P[i + 1:j]
        if L2 < 1e-18:
            dist = np.linalg.norm(seg - a, axis=1)
        else:
            dist = np.abs(d[0] * (seg[:, 1] - a[1]) - d[1] * (seg[:, 0] - a[0])) / math.sqrt(L2)
        k = int(np.argmax(dist))
        if dist[k] > eps:
            m = i + 1 + k
            keep[m] = True
            stack += [(i, m), (m, j)]
    return P[keep]


def hole_color(R, a, b, Fv, below):
    """Colour to refill a hole ring R of a layer: the topmost lower layer at the hole's interior grid points
    (majority vote), None when no lower layer covers it."""
    from matplotlib.path import Path as MPath
    i0, i1 = np.searchsorted(a, [R[:, 0].min(), R[:, 0].max()])
    j0, j1 = np.searchsorted(b, [R[:, 1].min(), R[:, 1].max()])
    if i1 <= i0 or j1 <= j0:
        return None
    A, B = np.meshgrid(a[i0:i1], b[j0:j1])
    ins = MPath(R).contains_points(np.c_[A.ravel(), B.ravel()]).reshape(A.shape) & (Fv[j0:j1, i0:i1] >= 0)
    if not ins.any():
        return None
    votes = {}
    for nm, cc, Fl in reversed(below):
        m = ins & (Fl[j0:j1, i0:i1] < 0)
        if m.any():
            votes[cc] = votes.get(cc, 0) + int(m.sum())
            ins = ins & ~m
    return max(votes, key=votes.get) if votes else None


def poly(ds, view, P, fill, w=0.0, color=None, closed=True):
    ds.cv.path(view.pts(P), w, None, closed=closed, fill=fill, stroke=w > 0, color=color)


def outline(ds, view, P, w=W_FINE, color=EDGE, closed=True, dash=None):
    ds.cv.path(view.pts(P), w, dash, closed=closed, color=color)


def inside_poly(P, A, B):
    from matplotlib.path import Path as MPath
    return MPath(P).contains_points(np.c_[A.ravel(), B.ravel()]).reshape(A.shape)


# ------------------------------------------------------------------------------------------------ side views
_CACHE = {}


def side_grid():
    a = np.arange(X0_SIDE - 0.02, E.FIN_TE[1][0] + 0.12, STEP_SIDE)
    b = np.arange(0.55, 4.30, STEP_SIDE)
    return a, b


def side_layers():
    """Paint layers of the side projection, bottom to top: [(name, colour, field (nb, na))]."""
    if "side" in _CACHE:
        return _CACHE["side"]
    a, b = side_grid()
    A, B = np.meshgrid(a, b)
    S = body_fields(A, B)
    body = np.minimum.reduce([S["fus"], S["dorsal"], S["fin"], S["strake"]])
    F_ = L.side_fields(A, B, fin=False)
    capf = L.fin_cap_field(A, B)
    layers = [("base", col(L.BASE), body)]
    for mat in reversed(L.PAINT_ORDER):
        if mat == "trim_black":
            layers.append((mat, col(mat), np.maximum(F_[mat], S["fus"])))
        elif mat == "paint_white":
            layers.append(("fin_cap", col(mat), np.maximum(capf, S["fin"])))
        else:
            layers.append((mat, col(mat), np.maximum(F_[mat], body)))
    xc = np.clip(A, X0_SIDE, X1_SIDE)
    glass = np.maximum(np.minimum(CG._poly_sdf(A, B, "ws"), CG._poly_sdf(A, B, "sw")), B - F.z_top(xc) + 0.004)
    env = wing_side_envelope(float(F.half_w(6.0)), W.SEMI)
    wing_low = np.where(inside_poly(env, A, B), B - F.z_bot(xc), 1.0)
    _CACHE["side"] = (a, b, layers, glass, wing_low, env)
    return _CACHE["side"]


def draw_side(ds, v, side):
    """Coloured profile seen from port (side=-1, nose left) or starboard (side=+1, nose right).  The near wing
    is drawn in outline where it lies over the fuselage (the livery under it stays visible)."""
    a, b, layers, glass, wing_low, env = side_layers()
    # wing-to-body fairing (details.py tables): the part below the keel is dark wing paint
    xs = np.linspace(L.BELLY_FAIRING_BOT[0][0], L.BELLY_FAIRING_BOT[-1][0], 120)
    bot = D.belly_fairing_bottom(xs)
    below = bot < F.z_bot(xs) - 0.001
    for seg in _runs(below):
        xx = xs[seg]
        bf = np.r_[np.c_[xx, F.z_bot(xx) + 0.02], np.c_[xx[::-1], bot[seg][::-1]]]
        poly(ds, v, bf, col(L.SURFACES["belly_fairing"]))
    stack_below = []
    for name, cc, Fv in layers:
        contour_fill(ds, v, a, b, Fv, cc, keep=lambda R, Fv=Fv: hole_color(R, a, b, Fv, stack_below))
        stack_below.append((name, cc, Fv))
    # glazing: windshield sliver + side window, cabin windows (door windows included)
    contour_fill(ds, v, a, b, glass, col("glass"))
    for o in FP.openings_table():
        if o["side"] == side and o["kind"] == "window":
            poly(ds, v, FP.window_outline(o["cx"]), col("glass"))
            outline(ds, v, FP.window_outline(o["cx"]), W_GRID, "#0B1020")
    # door / hatch seams, hinge lines and the exit marking
    for pid, o in FP.DOOR_PANELS.items():
        if o["side"] != side:
            continue
        outline(ds, v, FP.opening_outline(o), W_THIN, "#0B1020")
        if pid == "exit_hatch":
            m = L.EXIT_MARK
            ring = FP.opening_outline(dict(o, hx=o["hx"] + m["offset"], hz=o["hz"] + m["offset"],
                                           r=o["r"] + m["offset"]))
            ds.cv.path(v.pts(ring), 2 * m["half_width"] * v.k, None, closed=True, color=col("paint_pinstripe"))
    for o in (FP.AIRSTAIR, FP.CARGO):
        h = FP.hinge_line(o) if o["side"] == side else None
        if h:
            ds.cv.line(v.pt(h[0] + 0.04, h[2]), v.pt(h[1] - 0.04, h[2]), W_GRID, color="#0B1020")
    # body outline, fin, rudder, tab, strake
    xs = np.linspace(X0_SIDE, X1_SIDE, 700)
    outline(ds, v, np.c_[xs, F.z_top(xs)], W_FINE, closed=False)
    outline(ds, v, np.c_[xs, F.z_bot(xs)], W_FINE, closed=False)
    cur = E._dorsal_curve(64)
    xd = np.linspace(E.DORSAL_X0, float(cur[-1, 0]), 120)
    outline(ds, v, np.c_[xd, dorsal_top(xd)], W_FINE, closed=False)
    zc = np.linspace(float(cur[-1, 1]), 4.05, 20)
    outline(ds, v, np.c_[E.fin_le(zc), zc], W_FINE, closed=False)
    zt = np.linspace(E.FIN_TE[0][1], 3.93, 20)
    outline(ds, v, np.c_[E.fin_te(zt), zt], W_FINE, closed=False)
    (vx0, _), (vx1, _) = E.VENTRAL_EDGE
    vxs = np.linspace(vx0, vx1, 40)
    vzs = ventral_edge(vxs)
    for seg in _runs(vzs < F.z_bot(np.clip(vxs, X0_SIDE, X1_SIDE)) - 0.002):
        outline(ds, v, np.c_[vxs[seg], vzs[seg]], W_FINE, closed=False)
    # rudder seams: nose / gap line and the sloped top edge (E.rudder_outline; its bottom edge is the ventral edge)
    ro = E.rudder_outline()
    k = len(ro) // 2                                    # nose-bottom, top edge (nose -> TE), bottom edge (TE -> nose)
    outline(ds, v, ro[:k + 1], W_GRID, "#0B1020", closed=False)
    t0, t1, tx = E.RUD_TAB
    tab = [(E.fin_le(z) + tx * (E.fin_te(z) - E.fin_le(z)), z) for z in (t0, t1)]
    outline(ds, v, np.array([(E.fin_te(t0), t0), tab[0], tab[1], (E.fin_te(t1), t1)]), W_GRID, "#0B1020",
            closed=False)
    (r0x, r0z), (r1x, r1z) = E.STRAKE_ROOT
    (s0x, s0z), (s1x, s1z) = E.STRAKE_TIP
    outline(ds, v, np.array([(r0x, r0z), (s0x, s0z), (s1x, s1z), (r1x, r1z)]), W_THIN, closed=False)
    outline(ds, v, np.c_[[X0_SIDE, X0_SIDE], [F.z_bot(X0_SIDE), F.z_top(X0_SIDE)]], W_THIN, closed=False)
    # wing-to-body fairing outline (details.py): lower silhouette, forward upper edge, tail lobe on the side
    xb = np.linspace(L.BELLY_FAIRING_BOT[0][0], L.BELLY_FAIRING_BOT[-1][0], 120)
    outline(ds, v, np.c_[xb, D.belly_fairing_bottom(xb)], W_THIN, closed=False)
    outline(ds, v, np.array(L.BELLY_FAIRING_NOSE_EDGE), W_GRID, "#0B1020", closed=False)
    outline(ds, v, np.array(L.BELLY_FAIRING_TAIL), W_GRID, "#0B1020", closed=False)
    # bullet fairing (white; the tailplane lies inside its side silhouette)
    Bt = np.array(E.BULLET)
    bul = np.r_[Bt[:, [0, 1]], Bt[::-1][:, [0, 2]]]
    poly(ds, v, bul, col(L.SURFACES["bullet"]))
    outline(ds, v, bul, W_FINE)
    # near wing: filled below the keel (wing lower face); over the fuselage a phantom outline (root and tip
    # sections, LE / TE loci, winglet) so the livery under it stays readable
    contour_fill(ds, v, a, b, wing_low, col(L.SURFACES["wing_lower"]))
    for P, cl in wing_phantom():
        outline(ds, v, P, W_THIN, PHANTOM_INK, closed=cl, dash=(1.6, 0.9))
    if side > 0:                                   # radar pod under the starboard tip (in front of the fuselage)
        body, rad = pod_side()
        poly(ds, v, body, col(L.SURFACES["pod_body"]))
        poly(ds, v, rad, col(L.SURFACES["pod_radome"]))
        outline(ds, v, body, W_FINE)
    draw_gear_side(ds, v)
    draw_stack_side(ds, v, side)
    draw_prop_side(ds, v)


PHANTOM_INK = "#C3CFDF"


def wing_phantom():
    """Side-projection phantom lines of the near wing: root section at the fuselage side, tip-rib section,
    LE / TE loci, winglet LE / TE / top section.  [(polyline (N, 2), closed)]"""
    yr = float(F.half_w(6.0))
    out = [(section_outline(W.section_at(yr))[:, [0, 2]], True), (section_outline(W.section_at(W.SEMI))[:, [0, 2]],
                                                                  True)]
    ys = np.linspace(yr, W.SEMI, 40)
    for f in (0.0, 1.0):
        P = np.array([W.section_at(y).point(np.array(f), np.array(0.0)) for y in ys])
        out.append((P[:, [0, 2]], False))
    le, te, secs = winglet_plan()
    out += [(le[:, [0, 2]], False), (te[:, [0, 2]], False), (section_outline(secs[-1])[:, [0, 2]], True)]
    return out


def draw_stack_side(ds, v, side):
    """Stack seen from the side: polished tube (side projection of the swept tube, rounded ends) and the
    heat-blackened outlet collar (the last PP.STACK_COLLAR of the path)."""
    path, ra, rb = exhaust_stack(side)
    x0, x1 = path[0, 0], path[-1, 0] + 0.01
    zc = float(path[:, 2].mean())
    P = FP.opening_outline(dict(cx=0.5 * (x0 + x1), cz=zc, hx=0.5 * (x1 - x0), hz=rb, r=0.07))
    poly(ds, v, P, col(L.SURFACES["exhaust"]))
    xc = stack_collar_x(side)
    m = P[:, 0] >= xc
    if m.sum() > 2:
        C = np.r_[P[m], [[xc, float(P[m][:, 1].min())], [xc, float(P[m][:, 1].max())]]]
        ang = np.arctan2(C[:, 1] - zc, C[:, 0] - 0.5 * (xc + x1))
        poly(ds, v, C[np.argsort(ang)], "#1E1B18")
    hl = FP.opening_outline(dict(cx=0.5 * (x0 + xc) - 0.01, cz=zc + 0.45 * rb, hx=0.5 * (xc - x0) - 0.05,
                                 hz=0.18 * rb, r=0.015))
    poly(ds, v, hl, "#E4DED3")
    outline(ds, v, P, W_THIN)
    ds.cv.line(v.pt(xc, zc - 0.97 * rb), v.pt(xc, zc + 0.97 * rb), W_GRID, color=MUTED)


def draw_gear_side(ds, v):
    T = G.MAIN_TRUNNION
    # leg door (gear.leg_door_outline): outboard of the tyre, so it is drawn over it in both side views
    door = G.leg_door_outline()
    Lp, A = G.MAIN_LINK_PIVOT, G.MAIN_AXLE
    ds.cv.path([v.pt(T[0], T[2]), v.pt(Lp[0], Lp[2]), v.pt(A[0], A[2])], 0.07 * v.k, color=col("gear_leg"))
    tyre(ds, v, A, G.MAIN_TYRE)
    poly(ds, v, door, col(L.SURFACES["main_gear_door"]))
    outline(ds, v, door, W_THIN)
    Np, Nf, Na = G.NOSE_PIVOT, G.NOSE_FORK, G.NOSE_AXLE
    (ax, _, az), (bx, _, bz) = G.NOSE_BRACE
    ds.cv.line(v.pt(ax, az), v.pt(bx, bz), 0.03 * v.k, color="#C9CDD1")
    ds.cv.path([v.pt(Np[0], Np[2]), v.pt(Nf[0], Nf[2]), v.pt(Na[0], Na[2])], 0.06 * v.k, color=col("gear_leg"))
    tyre(ds, v, Na, G.NOSE_TYRE)
    nb = BY.NOSE_BAY                                # clamshell doors, open (hanging below the bay edges)
    xs = np.linspace(nb["cx"] - nb["hx"], nb["cx"] + nb["hx"], 40)
    zk = F.z_bot(xs)
    door_n = np.r_[np.c_[xs, zk + 0.01], np.c_[xs[::-1], (zk - 0.95 * nb["hy"])[::-1]]]
    poly(ds, v, door_n, col(L.SURFACES["nose_gear_door"]))
    outline(ds, v, door_n, W_THIN)


def tyre(ds, v, c, t):
    a = np.linspace(0, 2 * np.pi, 73)
    ring = np.c_[c[0] + t["R"] * np.cos(a), c[2] + t["R"] * np.sin(a)]
    poly(ds, v, ring, col("tire"))
    poly(ds, v, np.c_[c[0] + t["rim"] * np.cos(a), c[2] + t["rim"] * np.sin(a)], col("wheel"))
    outline(ds, v, ring, W_THIN)


def blade_shape(r, hw, axis, x, sg, mats=True):
    """Blade polygon (and its tip bands) along +/- the radial direction in a view's (a, b) coordinates."""
    out = [(np.r_[np.c_[x - hw, axis + sg * r], np.c_[(x + hw)[::-1], axis + sg * r[::-1]]], "prop_blade")]
    if mats:
        for mat, a0, a1 in L.PROP_BANDS:
            if mat == "prop_blade":
                continue
            rr = np.linspace(PP.PROP_R - a1, PP.PROP_R - a0, 10)
            hh = np.interp(rr, r, hw)
            out.append((np.r_[np.c_[x - hh, axis + sg * rr], np.c_[(x + hh)[::-1], axis + sg * rr[::-1]]], mat))
    return out


def draw_prop_side(ds, v):
    """Spinner (polished) and two of the five blades, vertical, edge-on (width = chord x sin(pitch))."""
    r, hw = blade_outline(width_scale=0.40)
    hub = PP.prop_hub()
    c = np.array([hub[0], hub[2]])
    tilt = PP.THRUST_TILT_DEG                 # disc top forward (thrust line nose-down)
    for sg in (1, -1):
        shapes = blade_shape(r, hw, hub[2], hub[0], sg)
        shapes = [(tilt_about(P, c, tilt), mat) for P, mat in shapes]
        for P, mat in shapes:
            poly(ds, v, P, col(mat))
        outline(ds, v, shapes[0][0], W_THIN)
    sp = spinner_outline()
    poly(ds, v, sp, col(L.SURFACES["spinner"]))
    a, b = F.SPINNER_SHAPE
    t = np.linspace(0.08, 1, 50)
    sx = F.STA["spinner_tip"] + (X0_SIDE - F.STA["spinner_tip"]) * t
    sr = F.SPINNER_R * (1 - (1 - t) ** a) ** b
    zc = PP.axis_point(sx)[:, 2]
    hl = np.r_[np.c_[sx, zc + 0.55 * sr], np.c_[sx[::-1], (zc + 0.30 * sr)[::-1]]]
    poly(ds, v, hl, "#EEF1F4")
    outline(ds, v, sp, W_FINE)


# ------------------------------------------------------------------------------------------------ plan view
def plan_layers(upper):
    """Paint layers of the starboard half of the fuselage seen from above (upper) or below: fields on the
    (x, y >= 0) grid, z = the OML surface there."""
    key = ("plan", upper)
    if key in _CACHE:
        return _CACHE[key]
    a = np.arange(X0_SIDE - 0.01, X1_SIDE + 0.01, STEP_PLAN)
    b = np.arange(0.0, 0.90 + 1e-9, STEP_PLAN)
    A, B = np.meshgrid(a, b)
    xc = np.clip(A, X0_SIDE, X1_SIDE)
    hw = F.half_w(xc)
    sil = np.maximum.reduce([B - hw, X0_SIDE - A, A - X1_SIDE, -B - 1e-3])
    Z = F.z_at(xc, np.minimum(B, hw * 0.9999), upper=upper)
    F_ = L.side_fields(A, Z, y=B, fin=False)
    layers = [("base", col(L.BASE), sil)]
    for mat in reversed(L.PAINT_ORDER):
        if mat == "paint_white":
            continue
        layers.append((mat, col(mat), np.maximum(F_[mat], sil)))
    if upper:
        ws = CG.windshield_sdf(A, B, Z, B)
        sw = CG.sidewindow_sdf(A, B, Z)
        layers.append(("glass", col("glass"), np.maximum(np.minimum(ws, sw), sil)))
    _CACHE[key] = (a, b, layers)
    return _CACHE[key]


def half(P_full_upper, x):
    """Closed half-outline from an upper boundary b(x) >= 0 back along the centre line."""
    return np.r_[P_full_upper, np.c_[x[::-1], np.zeros(len(x))]]


def fin_plan_halfwidth(xs):
    """Plan-view half-thickness envelope of the fin above the tail-cone crown."""
    w = np.zeros_like(xs)
    for z in np.linspace(2.3, 4.0, 60):
        s = E.fin_section(z)
        xc = (xs - s.le[0]) / s.chord
        t = 0.5 * s.chord * s.airfoil.thickness(np.clip(xc, 0, 1))
        ok = (xc >= 0) & (xc <= 1) & (F.z_top(np.clip(xs, X0_SIDE, X1_SIDE)) < z) | (xs > X1_SIDE) & (xc >= 0) & (xc <= 1)
        w = np.where(ok, np.maximum(w, t), w)
    return w


def draw_plan(ds, v, upper=True):
    """One half of the split plan: the starboard half of the aircraft seen from above (upper=True, drawn
    above the centre line) or from below (drawn below it).  The scheme is symmetric; the radar pod is on the
    starboard tip, so it appears in both halves."""
    a, b, layers = plan_layers(upper)
    yr = float(F.half_w(6.0))
    tag = "upper" if upper else "lower"

    def fus():
        for name, cc, Fv in layers:
            contour_fill(ds, v, a, b, Fv, cc, simplify=0.0015)
        xs = np.linspace(X0_SIDE, X1_SIDE, 600)
        outline(ds, v, np.c_[xs, F.half_w(xs)], W_FINE, closed=False)

    def fin():
        xs = np.linspace(E.fin_le(2.62), E.fin_te(3.9), 200)
        w = np.maximum(fin_plan_halfwidth(xs), 0.0)
        xd = np.linspace(E.DORSAL_X0, E.fin_te(2.6), 160)
        wd = dorsal_halfwidth(xd)
        for xx, ww in ((xd, wd), (xs, w)):
            P = half(np.c_[xx, ww], xx)
            poly(ds, v, P, col(L.SURFACES["dorsal"]))
            outline(ds, v, np.c_[xx, ww], W_THIN, closed=False)

    def stab():
        P = E.stab_plan_polygon()
        poly(ds, v, P, col(L.SURFACES["stab_upper" if upper else "stab_lower"]))
        poly(ds, v, stab_boot_outline(1, L.STAB_BOOT[tag]), col(L.SURFACES["boot"]))
        outline(ds, v, P, W_FINE)
        hy = np.linspace(E.ELEV_Y[0], E.ELEV_Y[1], 20)
        hx = [E.stab_le(y) + E.ELEV_XH * (E.stab_te(y) - E.stab_le(y)) for y in hy]
        outline(ds, v, np.c_[hx, hy], W_GRID, closed=False)
        tip = E.stab_tip_outline()
        outline(ds, v, tip["horn_root"], W_GRID, closed=False)
        Bt = np.array(E.BULLET)
        bp = half(Bt[:, [0, 3]], Bt[:, 0])
        poly(ds, v, bp, col(L.SURFACES["bullet"]))
        outline(ds, v, Bt[:, [0, 3]], W_FINE, closed=False)

    def wing():
        surf = L.SURFACES["wing_upper" if upper else "wing_lower"]
        P = wing_plan_outline(1, yr)
        poly(ds, v, P, col(surf))
        poly(ds, v, boot_plan_outline(1, 0.10 if upper else 0.065), col(L.SURFACES["boot"]))
        ink = "#0B1020"
        # flap: shroud lip seen from above, lower cove edge from below; aileron: gap line of that skin
        fy = np.linspace(max(W.Y_FLAP[0], yr), W.Y_FLAP[1], 40)
        outline(ds, v, np.c_[W.flap_lines(fy, upper), fy], W_GRID, ink, closed=False)
        y = W.Y_FLAP[1]
        outline(ds, v, np.array([(float(W.flap_lines(y, upper)), y), (W.x_te(y), y)]), W_GRID, ink, closed=False)
        ay = np.linspace(*W.Y_AIL, 20)
        outline(ds, v, np.c_[[W.ail_gap_x(y_, upper) for y_ in ay], ay], W_GRID, ink, closed=False)
        for y in W.Y_AIL:
            outline(ds, v, np.array([(W.ail_gap_x(y, upper), y), (W.x_te(y), y)]), W_GRID, ink, closed=False)
        tb0, tb1 = W.Y_AIL[0] + 0.06, W.Y_AIL[0] + 0.72          # Flettner tab (as sheet L4)
        tp = [(float(W.x_te(tb0)), tb0), (float(W.x_le(tb0) + 0.945 * W.chord(tb0)), tb0),
              (float(W.x_le(tb1) + 0.945 * W.chord(tb1)), tb1), (float(W.x_te(tb1)), tb1)]
        outline(ds, v, np.array(tp), W_GRID, ink, closed=False)
        outline(ds, v, P, W_FINE)
        le, te, secs = winglet_plan()
        wlp = np.r_[le[:, :2], te[::-1, :2]]
        poly(ds, v, wlp, col(L.SURFACES["winglet_inboard" if upper else "winglet_outboard"]))
        if upper:
            ds.cv.path(v.pts(winglet_pin()), 2 * L.WINGLET_PIN["half_width"] * v.k, color=col("paint_pinstripe"))
        outline(ds, v, wlp, W_FINE)

    def pod():
        body, rad = pod_plan(1)
        poly(ds, v, body, col(L.SURFACES["pod_body"]))
        poly(ds, v, rad, col(L.SURFACES["pod_radome"]))
        outline(ds, v, body, W_FINE)

    def belly():
        xs = np.linspace(L.BELLY_FAIRING_HW[0][0], L.BELLY_FAIRING_HW[-1][0], 80)
        w = D.belly_fairing_halfwidth(xs)
        P = half(np.c_[xs, w], xs)
        poly(ds, v, P, col(L.SURFACES["belly_fairing"]))
        outline(ds, v, np.c_[xs, w], W_THIN, closed=False)
        for y in D.FLAP_CANOE_Y:
            sec = W.section_at(y)
            x0 = sec.le[0] + 0.55 * sec.chord
            Lc = 0.60 * sec.chord
            t = np.linspace(0, 1, 30)
            r = 0.05 * (2.2 * np.sqrt(t) * (1 - t) ** 1.25) / 0.61
            P = np.r_[np.c_[x0 + t * Lc, y + r], np.c_[(x0 + t * Lc)[::-1], (y - r)[::-1]]]
            poly(ds, v, P, col(L.SURFACES["flap_fairings"]))
            outline(ds, v, P, W_GRID)

    def gear():
        A = G.MAIN_AXLE
        R, Wt = G.MAIN_TYRE["R"], G.MAIN_TYRE["W"]
        d = G.LEG_DOOR                                  # leg door edge-on (outboard of the tyre)
        P = FP.opening_outline(dict(cx=A[0], cz=A[1], hx=R, hz=Wt / 2, r=0.04))
        poly(ds, v, P, col("tire"))
        outline(ds, v, P, W_THIN)
        door = FP.opening_outline(dict(cx=0.5 * (d["x_fwd"] + d["x_aft"]), cz=float(np.mean(d["bl"])),
                                       hx=0.5 * (d["x_aft"] - d["x_fwd"]), hz=0.012, r=0.005))
        poly(ds, v, door, col(L.SURFACES["main_gear_door"]))
        outline(ds, v, door, W_GRID)
        A = G.NOSE_AXLE
        R, Wt = G.NOSE_TYRE["R"], G.NOSE_TYRE["W"]
        nb = BY.NOSE_BAY
        dn = FP.opening_outline(dict(cx=nb["cx"], cz=nb["hy"] + 0.012, hx=nb["hx"], hz=0.012, r=0.005))
        poly(ds, v, dn, col(L.SURFACES["nose_gear_door"]))
        P = np.array([(A[0] - R, 0.0), (A[0] + R, 0.0), (A[0] + R, Wt / 2), (A[0] - R, Wt / 2)])
        poly(ds, v, P, col("tire"))
        outline(ds, v, P, W_THIN)

    def prop():
        S_ = PP.spinner_silhouette("plan", 60)          # yawed thrust axis: tip at BL +23
        st = S_[:60]                                     # starboard edge, tip -> base
        sp = half(st, st[:, 0])
        poly(ds, v, sp, col(L.SURFACES["spinner"]))
        outline(ds, v, st, W_FINE, closed=False)
        r, hw = blade_outline(rmin=F.SPINNER_R * 0.8, width_scale=0.40)
        hub = PP.prop_hub()
        shapes = blade_shape(r, hw, hub[1], hub[0], 1)
        shapes = [(tilt_about(P, np.array([hub[0], hub[1]]), -PP.THRUST_YAW_DEG), mat) for P, mat in shapes]
        for P, mat in shapes:
            poly(ds, v, P, col(mat))
        outline(ds, v, shapes[0][0], W_THIN)

    def stacks():
        path, ra, rb = exhaust_stack(1, 60)
        d = np.gradient(path[:, :2], axis=0)
        nrm = np.c_[-d[:, 1], d[:, 0]] / np.linalg.norm(d, axis=1)[:, None]
        P = np.r_[path[:, :2] + ra * nrm, (path[:, :2] - ra * nrm)[::-1]]
        poly(ds, v, P, col(L.SURFACES["exhaust"]))
        m = path[:, 0] >= stack_collar_x(1)                    # heat-blackened outlet collar
        if m.sum() >= 2:
            Q = np.r_[path[m, :2] + ra * nrm[m], (path[m, :2] - ra * nrm[m])[::-1]]
            poly(ds, v, Q, "#1E1B18")
        outline(ds, v, P, W_THIN)

    if upper:
        for f in (pod, stacks, wing, fus, fin, stab, prop):
            f()
    else:
        for f in (stab, fus, wing, belly, pod, stacks, gear, prop):
            f()


def dorsal_halfwidth(xs):
    zs = np.linspace(2.45, float(E._dorsal_curve()[-1, 1]) - 0.01, 40)
    w = np.zeros_like(xs)
    for z in zs:
        s = E.dorsal_section(z)
        xc = (xs - s.le[0]) / s.chord
        ok = (xc >= 0) & (xc <= 1) & (F.z_top(np.clip(xs, X0_SIDE, X1_SIDE)) < z)
        w = np.where(ok, np.maximum(w, s.chord * s.airfoil.upper(np.clip(xc, 0, 1))), w)
    return w


def winglet_pin():
    """Plan-view trace of the winglet pinstripe: the upper (inboard) surface of the winglet section at WINGLET_PIN s,
    chord fractions c0..c1."""
    secs = winglet_secs()
    p = L.WINGLET_PIN
    sec = secs[int(round(p["s"] * (len(secs) - 1)))]
    return sec.upper(np.linspace(p["c0"], p["c1"], 30))[:, :2]


# ================================================================================================ sheet layout
PORT = dict(origin=(48.0, 164.0), scale=30)          # sheet mm of (spinner tip STA, WL 0)
STBD = dict(origin=(528.0, 346.0), scale=30)
PLAN = dict(origin=(537.0, 183.0), scale=50)
DET = dict(origin=(40.0, 505.0), scale=5)
COLX, COLX1 = 537.0, 825.0                           # right-hand column (legend, curve table)


def make_views(ds):
    k0 = (F.STA["spinner_tip"], 0.0)
    vp = ds.add_view(side_view("port", PORT["origin"], PORT["scale"], k0, box=(0.2, -0.1, 15.0, 4.4)))
    vs = ds.add_view(M._mk("starboard", "xz", -1, -1, STBD["origin"], k0, STBD["scale"], (0.2, -0.1, 15.0, 4.4),
                           "seen from starboard, nose right"))
    vu = ds.add_view(plan_view("plan_upper", PLAN["origin"], PLAN["scale"], k0, box=(0.2, 0.0, 15.0, 8.3)))
    vl = ds.add_view(M._mk("plan_lower", "xy", 1, 1, PLAN["origin"], k0, PLAN["scale"], (0.2, 0.0, 15.0, 8.3),
                           "starboard half seen from below (mirror of the upper half about the centre line)"))
    return vp, vs, vu, vl


def frame_ruler(ds, v, y_sheet):
    """Station ticks at the Pilatus frames below a side view (sheet y), labelled with name and STA."""
    Xs = {n: v.pt(x, 0.0)[0] for n, x in F.FRAMES.items()}
    ds.cv.line((min(Xs.values()), y_sheet), (max(Xs.values()), y_sheet), W_GRID, color=GRID)
    for n, X in Xs.items():
        ds.cv.line((X, y_sheet), (X, y_sheet + 1.6), W_THIN, color=GRID)
    last = None
    for n in sorted(Xs, key=lambda k: Xs[k] * np.sign(v.A[0, 0])):
        X = Xs[n]
        if last is not None and abs(X - last) < 9.0:
            continue
        ds.text(X, y_sheet + 4.6, n, 2.0, "label", "middle", weight=600, fill=GRID, tag="grid")
        ds.text(X, y_sheet + 7.2, f"{F.FRAMES[n] * 1000:.0f}", 1.8, "mono", "middle", fill=GRID, tag="grid")
        last = X


def wl_ticks(ds, v, x_edge):
    """WL ticks (0 .. 4 m) at the view's left edge."""
    for z in (0.0, 1.0, 2.0, 3.0, 4.0):
        X, Y = v.pt(x_edge, z)
        ds.cv.line((X - 1.5, Y), (X + 1.5, Y), W_THIN, color=GRID)
        ds.text(X - 2.3, Y, f"WL {z * 1000:.0f}", 1.9, "mono", "end", vcenter=True, fill=GRID, tag="grid")


def draw_clean(ds):
    ds.frame_and_title()
    vp, vs, vu, vl = make_views(ds)
    for v, side, xl in ((vp, -1, 0.35), (vs, +1, 14.95)):
        ds.cv.line(v.pt(0.3, 0.0), v.pt(14.95, 0.0), W_FINE, color=MUTED)
        for z in (1.0, 2.0, 3.0, 4.0):
            ds.cv.line(v.pt(0.3, z), v.pt(14.95, z), W_GRID, (1.0, 1.4), color="#C9D0D5")
        draw_side(ds, v, side)
        wl_ticks(ds, v, xl)
    frame_ruler(ds, vp, PORT["origin"][1] + 2.5)
    frame_ruler(ds, vs, STBD["origin"][1] + 2.5)
    view_title(ds, vp.pt(7.59, 0)[0], PORT["origin"][1] + 18.5, "PORT SIDE",
               "SEEN FROM PORT, NOSE LEFT - SCALE 1:30")
    # view references on the port side: VIEW C (from ahead) and DETAIL A (upper blade tip bands)
    X, Y = vp.pt(F.STA["spinner_tip"] - 0.18, F.PROP_AXIS_Z - 0.55)
    M.view_arrow(ds, (X, Y), (1.0, 0.0), "C")
    tip = PP.prop_hub()[[0, 2]] + (PP.PROP_R - 0.06) * np.array([-np.sin(np.radians(PP.THRUST_TILT_DEG)),
                                                                  np.cos(np.radians(PP.THRUST_TILT_DEG))])
    M.detail_circle(ds, vp, float(tip[0]), float(tip[1]), 0.13, "A", at=(1.0, 0.2))
    view_title(ds, vs.pt(7.59, 0)[0], STBD["origin"][1] + 18.5, "STARBOARD SIDE",
               "SEEN FROM STARBOARD, NOSE RIGHT - SCALE 1:30")
    # split plan
    draw_plan(ds, vu, upper=True)
    draw_plan(ds, vl, upper=False)
    X0, Y0 = vu.pt(0.3, 0.0)
    X1, _ = vu.pt(14.95, 0.0)
    ds.cv.line((X0, Y0), (X1, Y0), W_THIN, CHAIN, color=INK)
    for x in F.FRAMES.values():
        h = float(F.half_w(x))
        for v in (vu, vl):
            ds.cv.line(v.pt(x, h + 0.06), v.pt(x, h + 0.16), W_THIN, color=GRID)
    ds.text(X0 - 1.0, Y0, "CL", 2.2, "label", "end", vcenter=True, weight=600, fill=MUTED, tag="cl")
    xa, _ = vu.pt(10.6, 0)
    ds.text(xa, vu.pt(0, 3.3)[1], "UPPER SURFACES", 2.6, "label", "middle", weight=600, fill=MUTED, tag="lbl")
    ds.text(xa, vu.pt(0, 3.3)[1] + 3.2, "starboard half seen from above", 2.0, "label", "middle", fill=MUTED,
            tag="lbl")
    ds.text(xa, vl.pt(0, 3.3)[1] - 2.2, "LOWER SURFACES", 2.6, "label", "middle", weight=600, fill=MUTED, tag="lbl")
    ds.text(xa, vl.pt(0, 3.3)[1] + 1.0, "starboard half seen from below", 2.0, "label", "middle", fill=MUTED,
            tag="lbl")
    view_title(ds, vu.pt(7.59, 0)[0], vl.pt(0, 8.14)[1] + 9.5, "PLAN - UPPER / LOWER",
               "SPLIT VIEW ON THE CENTRE LINE, NOSE LEFT, STARBOARD HALF - SCALE 1:50")
    draw_legend(ds)
    draw_curves(ds)
    draw_left_bottom(ds)


# ================================================================================================ tables
LEGEND_ROWS = [
    ("paint_blue", "base: fuselage, dorsal, fin, rudder, wing upper faces, winglet inboard faces, pod, leg doors"),
    ("paint_blue_light", "lower cowling / lower nose, swoosh band to the lower rudder, nose-gear doors"),
    ("paint_pinstripe", "pinstripes and swooshes (B1 P1 P2 H1 U1 X1-X3 D1), exit marking, winglet line"),
    ("paint_navy", "navy pinstripe N1 (cowl front to the over-wing exit)"),
    ("paint_white", "fin cap (above FIN_CAP), bullet fairing"),
    ("paint_silver", "tailplane and elevators, both faces"),
    ("paint_wing_dark", "wing lower faces, winglet outboard faces, belly fairing, flap-track fairings"),
    ("paint_black", "radar-pod radome (forward of the pod joint)"),
    ("trim_black", "PRO windshield mask (outline: cockpit_glazing.surround_sdf)"),
    ("deice_boot", "wing / tailplane leading-edge de-ice boots (rubber, not paint)"),
    ("chrome", "spinner, polished (the drawing grey stands for chrome)"),
    ("exhaust_polished", "exhaust stacks, polished and heat-tinted"),
    ("prop_blade", "propeller blades (composite, black)"),
    ("prop_tip", "propeller blade tip band"),
    ("prop_band_red", "propeller blade red band"),
    ("glass", "glazing (existing material)"),
]


def draw_legend(ds):
    from model.assemble import MATERIALS
    x0, y0 = COLX, STBD["origin"][1] + 26.0
    cols = [("", 8.0, "c"), ("MATERIAL", 30.0, "l"), ("USED FOR", 142.0, "l"), ("sRGB", 20.0, "l"),
            ("PBR LINEAR RGB", 58.0, "l"), ("M / R", 30.0, "c")]
    rows = []
    for name, use in LEGEND_ROWS:
        c = L.PALETTE[name][0] if name in L.PALETTE else L.linear_to_hex(MATERIALS[name][0])
        rgb, met, rough = MATERIALS[name][:3]
        rows.append(("", name, use, c, " ".join(f"{v:.3f}" for v in rgb[:3]), f"{met:.2f} / {rough:.2f}"))
    yb = table(ds, x0, y0, cols, rows, title="COLOUR LEGEND  (model/livery.PALETTE  ->  model/assemble.MATERIALS)",
               size=1.8, row_h=4.0, head_h=4.2, title_h=5.0, font="label")
    top = y0 + 5.0 + 4.2
    for i, (name, _) in enumerate(LEGEND_ROWS):
        ds.cv.rect(x0 + 1.2, top + i * 4.0 + 0.6, 5.6, 2.8, lw=0.1, fill=col(name), color=INK)
    ds.text(x0, yb + 3.0, "sRGB = design colour (the flat colour drawn; polished metal is drawn grey).  PBR = glTF base "
            "colour, M / R = metallic / roughness.  The viewer primes paint_* and trim_black until its paint step.",
            1.6, "label", "start", fill=MUTED, tag="table")
    _CACHE["legend_bottom"] = yb + 5.0


CURVE_NOTE = {
    "B1": "thick white band: cowl front, under the exhaust, rising aft; crosses the crown aft of the cabin",
    "N1": "navy line above B1, cowl front to under the exit",
    "P1": "thin white line above N1; crosses the crown between the last two cabin windows",
    "P2": "thin white line: lower edge of the light band, under the cockpit to the lower rudder",
    "H1": "upper edge of the light band on the tail cone",
    "U1": "thin line above H1 rising aft to the crown",
    "X1": "diagonal across the light band to the fin root",
    "X2": "steep diagonal to the crown (few photo runs: white on light blue)",
    "X3": "from the crown descending aft to the lower rudder",
    "W1": "deep-blue counter-stroke splitting the light swoosh behind the cockpit",
    "D1": "stroke from the lower fuselage behind the wing into P2",
    "light": "light swoosh: whole lower nose, rising into the band through the window line to the rudder",
    "FIN_CAP": "white fin cap line (the bullet is white all over)",
}


def photo_residuals():
    """Per-stroke photo check (refs/cache/overlays/livery/measurements.json, written by photo_marks()); {} when
    the private cache is absent -- only our numbers (counts, median / rms dz in mm) reach the clean sheet."""
    f = LIV_CACHE / "measurements.json"
    try:
        return json.loads(f.read_text()).get("residuals", {}) if f.exists() else {}
    except Exception:                                   # noqa: BLE001
        return {}


def curve_rows():
    rows = []
    R = photo_residuals()
    for sid, s in L.strokes().items():
        k = s.knots
        r = R.get(sid, {})
        chk = f"{r['n']:d}  {r['median'] * 1000:+.0f} / {r['rms'] * 1000:.0f}" if r.get("n") else "-"
        rows.append((sid, s.mat.replace("paint_", ""), f"{k[0, 0]:.2f} - {k[-1, 0]:.2f}",
                     f"{k[0, 1]:.3f} > {k[-1, 1]:.3f}", f"{2 * k[:, 2].max() * 1000:.0f}", str(len(k)), chk,
                     CURVE_NOTE.get(sid, "")))
    for rid, r in L.regions().items():
        rows.append((rid, r.mat.replace("paint_", ""), f"{r.x0:.2f} - {r.x1:.2f}", "band top / bottom", "-",
                     f"{len(r.top_k)}+{len(r.bot_k)}", "-", CURVE_NOTE.get(rid, "")))
    rows.append(("FIN_CAP", "white", f"{L.FIN_CAP[0][0]:.2f} - {L.FIN_CAP[-1][0]:.2f}",
                 f"{L.FIN_CAP[0][1]:.3f} > {L.FIN_CAP[-1][1]:.3f}", "-", str(len(L.FIN_CAP)), "-",
                 CURVE_NOTE["FIN_CAP"]))
    return rows


def draw_curves(ds):
    y = _CACHE.get("legend_bottom", 440.0) + 1.5
    cols = [("CURVE", 13.0, "l"), ("PAINT", 20.0, "l"), ("STA [m]", 22.0, "c"), ("WL START > END", 29.0, "c"),
            ("MAX W mm", 15.0, "r"), ("KNOTS", 11.0, "r"), ("PHOTO n  dz mm", 26.0, "c"), ("", 152.0, "l")]
    yb = table(ds, COLX, y, cols, curve_rows(),
               title="LIVERY CURVES  (model/livery.py; side projection x, z; stroke = pchip centre line + half-height)",
               size=1.65, row_h=3.05, head_h=3.8, title_h=5.0)
    ds.text(COLX, yb + 3.0, "PHOTO n dz: white-run centres on the rectified photos within 45 mm of the stroke centre "
            "line (count, median / rms of photo - ours, mm; white strokes only).", 1.6, "label", "start", fill=MUTED,
            tag="table")
    _CACHE["curves_bottom"] = yb + 4.0


PHOTO_ROWS = [
    ("starboard 3/4, ground", "pro3008_stbd34_pilatus", "camera-matched (13 points, 7 px rms), rectified onto the side "
                                                        "projection: fuselage strokes, light band, fin cap, tailplane, "
                                                        "leg door"),
    ("starboard, air-to-air", "cand ..._PC-12-PRO-N81DW", "camera-matched (10 points, 5 px rms): tail-cone strokes, "
                                                          "dark wing lower faces, white bullet, pod"),
    ("port 3/4, hangar", "pro3008_port34 (= cand _130), cand _81, _82", "camera-matched _130 (7 points, 8 px rms) and _81 "
                                                                        "(7 points, 11 px): nose band group, light lower "
                                                                        "nose, blade bands, polished spinner / stacks"),
    ("port nose, outdoors", "cand ..._MSN-3008_188", "B1 / N1 / P1 run parallel from the cowl front; the aft port "
                                                     "strokes mirror the starboard ones"),
    ("starboard wing, flight", "cand ..._IMG_0459", "blue wing upper face, black LE boot, blue winglet with a white "
                                                    "line, blue pod with a black radome"),
]


def draw_left_bottom(ds):
    x0 = 30.0
    y = STBD["origin"][1] + 30.0
    cols = [("VIEW", 34.0, "l"), ("PHOTO  (refs/photos.json id;  cand = refs/cache/photos/cand/pn_first-pc12-pro-"
                                  "hando_*)", 104.0, "l"), ("USED FOR", 206.0, "l")]
    y = table(ds, x0, y, cols, PHOTO_ROWS, title="PHOTO SOURCES - MSN 3008 (N81DW), PILATUS NEWS 2025-09-26",
              size=2.0, row_h=4.3, head_h=4.6, title_h=5.5, font="label")
    items = [
        "Drawn from the parameters: every coloured area is the livery painter's field (model/livery.py) evaluated on "
        "the Stage-2 outlines (fuselage OML, glazing, openings, wing, empennage, gear, pod) - never from the mesh.",
        "Fuselage / fin colours are side-projection curves: a surface point (x, y, z) takes the colour of (x, z), so "
        "strokes that reach the crown cross it (plan). Port = mirror of starboard (the photos show the same scheme).",
        "Knots measured on the photos camera-matched to the model and rectified onto the side projection "
        "(+/- 0.03-0.05 m); the lower nose follows the port photos (the starboard nose is in shade).",
        "Near wing drawn as phantom lines over the fuselage so the livery stays visible; propeller: 2 of 5 blades, "
        "schematic width; nose-gear doors open.",
        "Estimated: plan-view crossings, winglet line position, lower-surface colours between photos, blade band "
        "widths (+/- 10 mm). No logos, lettering or registration marks are drawn.",
    ]
    yn = notes(ds, x0, y + 4.0, x0 + 318.0, items, size=2.1, line_h=3.0)
    scale_bar(ds, x0 + 2.0, max(yn + 10.0, 548.0), 30, 3.0, 0.5, "SCALE 1:30 (SIDE VIEWS, VIEW C)")
    scale_bar(ds, x0 + 150.0, max(yn + 10.0, 548.0), 50, 4.0, 1.0, "SCALE 1:50 (PLAN)")
    draw_detail_blade(ds)
    draw_surfaces(ds, x0 + 128.0, 468.0)
    draw_front(ds)


SURFACE_ROWS = [
    ("wing_upper / wing_lower", "wing, flaps, ailerons, tabs: upper / lower face (normal split)"),
    ("winglet_inboard / _outboard", "winglet faces; WINGLET_PIN chordwise white line on the root blend"),
    ("stab_upper / stab_lower", "tailplane + elevators; STAB_BOOT LE band (8 / 6 % chord)"),
    ("boot", "wing BOOT_Y 0.95-7.43 and tailplane leading edges"),
    ("bullet / dorsal / strakes", "bullet fairing white; dorsal + strakes base blue"),
    ("belly_fairing / flap_fairings", "dark wing paint"),
    ("pod_body / pod_radome", "radar pod blue; radome black ahead of POD_X_JOINT"),
    ("main / nose_gear_door", "leg doors blue; nose-gear doors light blue"),
    ("spinner / exhaust / blade_le", "polished chrome / polished stacks / erosion strip"),
]


def draw_surfaces(ds, x0, y0):
    cols = [("", 7.0, "c"), ("livery.SURFACES KEY", 44.0, "l"), ("MATERIAL", 26.0, "l"), ("WHERE", 95.0, "l")]
    rows = []
    swatches = []
    for key, where in SURFACE_ROWS:
        k0 = key.split(" / ")[0].split()[0]
        k0 = {"main": "main_gear_door", "spinner": "spinner", "bullet": "bullet"}.get(k0, k0)
        mat = L.SURFACES.get(k0, L.BASE)
        rows.append(("", key, mat, where))
        swatches.append(mat)
    yb = table(ds, x0, y0, cols, rows, title="PER-SURFACE COLOURS (model/livery.py SURFACES)", size=1.8, row_h=4.0,
               head_h=4.2, title_h=5.0, font="label")
    top = y0 + 5.0 + 4.2
    for i, mat in enumerate(swatches):
        ds.cv.rect(x0 + 1.0, top + i * 4.0 + 0.6, 5.0, 2.8, lw=0.1, fill=col(mat), color=INK)
    return yb


def draw_detail_blade(ds):
    """DETAIL A - propeller blade tip bands (1:5), drawn from PROP_BANDS on the schematic blade."""
    x0, y0 = DET["origin"]
    k = 1000.0 / DET["scale"]
    r, hw = blade_outline(rmin=1.05, width_scale=1.0)

    def pt(rr, u):
        return (x0 + (rr - 1.05) * k, y0 + u * k)
    P = [pt(a, -b) for a, b in zip(r, hw)] + [pt(a, b) for a, b in zip(r[::-1], hw[::-1])]
    ds.cv.polygon(P, fill=col("prop_blade"))
    for mat, a0, a1 in L.PROP_BANDS:
        if mat == "prop_blade":
            continue
        rr = np.linspace(PP.PROP_R - a1, PP.PROP_R - a0, 12)
        hh = np.interp(rr, r, hw)
        Q = [pt(a, -b) for a, b in zip(rr, hh)] + [pt(a, b) for a, b in zip(rr[::-1], hh[::-1])]
        ds.cv.polygon(Q, fill=col(mat))
    ds.cv.path(P, W_FINE, closed=True, color=EDGE)
    yd = y0 + float(hw.max()) * k + 5.0
    edges = sorted({PP.PROP_R - a for _, a, _ in L.PROP_BANDS} | {PP.PROP_R - b for _, _, b in L.PROP_BANDS})
    for e in edges:
        X = pt(e, 0)[0]
        ds.cv.line((X, yd - 1.5), (X, yd + 1.5), W_THIN, color=INK)
    ds.cv.line((pt(edges[0], 0)[0], yd), (pt(edges[-1], 0)[0], yd), W_THIN, color=INK)
    for mat, a0, a1 in L.PROP_BANDS:
        Xa, Xb = pt(PP.PROP_R - a1, 0)[0], pt(PP.PROP_R - a0, 0)[0]
        ds.text(0.5 * (Xa + Xb), yd + 4.0, f"{(a1 - a0) * 1000:.0f}", 2.2, "mono", "middle", tag="dim")
    ds.text(x0, yd + 9.0, "white tip / black / red band, measured inward from the tip (R 1335); blade leading edge: "
            "metal erosion strip", 1.9, "label", "start", fill=MUTED, tag="lbl")
    view_title(ds, x0 + 0.5 * (PP.PROP_R - 1.05) * k, y0 - float(hw.max()) * k - 9.0, "DETAIL A - BLADE TIP",
               "livery.PROP_BANDS - SCALE 1:5", size=3.2)


# ------------------------------------------------------------------------------------------------ front view
FRONT = dict(origin=(444.0, 556.0), scale=30, y_cut=2.60)     # sheet mm of (BL 0, WL 0); wings broken at y_cut


def front_layers(step=0.004):
    """Front projection of the fuselage (seen from ahead): the forward-most OML point at each (y, z) and its paint."""
    if "front" in _CACHE:
        return _CACHE["front"]
    a = np.arange(-0.90, 0.90 + 1e-9, step)
    b = np.arange(0.85, 2.85, step)
    A, B = np.meshgrid(a, b)
    Xs = np.full(A.shape, np.nan)
    for x in np.arange(X0_SIDE, 4.8, 0.004):
        zt, zb = float(F.z_top(x)), float(F.z_bot(x))
        m = np.isnan(Xs) & (B < zt) & (B > zb)
        if not m.any():
            continue
        ins = m & (np.abs(A) < F.side_y(np.full(A.shape, x), np.clip(B, zb, zt)))
        Xs[ins] = x
    sil = np.where(np.isnan(Xs), 1.0, -1.0)
    Xf = np.where(np.isnan(Xs), 6.0, Xs)
    F_ = L.side_fields(Xf, B, y=A)
    layers = [("base", col(L.BASE), sil)]
    for mat in reversed(L.PAINT_ORDER):
        if mat != "paint_white":
            layers.append((mat, col(mat), np.maximum(F_[mat], sil)))
    ws = CG.windshield_sdf(Xf, A, B, A)
    sw = CG.sidewindow_sdf(Xf, A, B)
    layers.append(("glass", col("glass"), np.maximum(np.minimum(ws, sw), sil)))
    _CACHE["front"] = (a, b, layers)
    return _CACHE["front"]


def draw_front(ds):
    """VIEW C - front view (seen from ahead, starboard on the viewer's left), wings broken at BL y_cut."""
    v = ds.add_view(M.front_view("front", FRONT["origin"], FRONT["scale"], (0.0, 0.0), box=(-2.8, -0.1, 2.8, 4.4)))
    yc = FRONT["y_cut"]
    ds.cv.line(v.pt(2.75, 0.0), v.pt(-2.75, 0.0), W_FINE, color=MUTED)
    # tailplane (LE boot faces forward), bullet, fin
    ys = np.linspace(0.0, E.STAB_TIP_Y - 0.002, 60)
    su = np.array([E.stab_section(y).upper(XC)[:, 2].max() for y in ys])
    sl = np.array([E.stab_section(y).lower(XC)[:, 2].min() for y in ys])
    stab = np.r_[np.c_[ys, su], np.c_[ys[::-1], sl[::-1]]]
    for sg in (1, -1):
        P = stab * [sg, 1]
        poly(ds, v, P, col(L.SURFACES["stab_upper"]))
        outline(ds, v, P, W_FINE)
    zf = np.linspace(2.3, 4.05, 40)
    fw = np.array([0.5 * E.fin_section(z).chord * E.fin_section(z).airfoil.thickness(np.linspace(0, 1, 201)).max()
                   for z in zf])
    finP = np.r_[np.c_[fw, zf], np.c_[-fw[::-1], zf[::-1]]]
    poly(ds, v, finP, col(L.BASE))
    zc = zf[zf > L.fin_cap_line(E.fin_le(zf))]
    if len(zc):
        fwc = np.interp(zc, zf, fw)
        poly(ds, v, np.r_[np.c_[fwc, zc], np.c_[-fwc[::-1], zc[::-1]]], col("paint_white"))
    outline(ds, v, finP, W_THIN)
    bx = E.BULLET[int(np.argmax([r[3] for r in E.BULLET]))][0]
    bs = E.bullet_section(bx, 72)[:, 1:]
    poly(ds, v, bs, col(L.SURFACES["bullet"]))
    outline(ds, v, bs, W_FINE)
    # wing stubs to the break line (front face = leading-edge boot), break line zig-zag
    yr = float(F.half_w(6.0))
    yw = np.linspace(yr, yc, 30)
    up = np.array([W.section_at(y).upper(XC)[:, 2].max() for y in yw])
    lo = np.array([W.section_at(y).lower(XC)[:, 2].min() for y in yw])
    for sg in (1, -1):
        P = np.r_[np.c_[sg * yw, up], np.c_[sg * yw[::-1], lo[::-1]]]
        poly(ds, v, P, col(L.SURFACES["boot"]))
        outline(ds, v, P, W_FINE)
        zz = np.linspace(lo[-1] - 0.03, up[-1] + 0.03, 7)
        ds.cv.path(v.pts(np.c_[sg * (yc + 0.03 * (np.arange(7) % 2)), zz]), W_THIN, color=INK)
    # main gear: tyres, legs; nose gear
    for sg in (1, -1):
        A_ = G.MAIN_AXLE
        R, Wt = G.MAIN_TYRE["R"], G.MAIN_TYRE["W"]
        T = G.MAIN_TRUNNION
        ds.cv.line(v.pt(sg * T[1], T[2]), v.pt(sg * A_[1], A_[2]), 0.07 * v.k, color=col("gear_leg"))
        P = FP.opening_outline(dict(cx=sg * A_[1], cz=A_[2], hx=Wt / 2, hz=R, r=0.05))
        poly(ds, v, P, col("tire"))
        outline(ds, v, P, W_THIN)
        d_ = G.LEG_DOOR                                   # leg door edge-on, outboard of the tyre
        dz = G.leg_door_outline()[:, 1]
        ds.cv.line(v.pt(sg * d_["bl"][0], float(dz.max())), v.pt(sg * d_["bl"][1], float(dz.min())), 0.018 * v.k,
                   color=col(L.SURFACES["main_gear_door"]))
    Np, Na = G.NOSE_PIVOT, G.NOSE_AXLE
    ds.cv.line(v.pt(0.0, Np[2]), v.pt(0.0, Na[2]), 0.06 * v.k, color=col("gear_leg"))
    P = FP.opening_outline(dict(cx=0.0, cz=Na[2], hx=G.NOSE_TYRE["W"] / 2, hz=G.NOSE_TYRE["R"], r=0.04))
    poly(ds, v, P, col("tire"))
    outline(ds, v, P, W_THIN)
    # fuselage front projection (painted), exhaust stacks, spinner, propeller disc
    a, b, layers = front_layers()
    for name, cc, Fv in layers:
        contour_fill(ds, v, a, b, Fv, cc, simplify=0.0015)
    th = np.linspace(0, 2 * np.pi, 145)
    env = F.section(np.full_like(th, 4.6), th / (2 * np.pi))[:, 1:]          # max section outline
    outline(ds, v, env, W_FINE)
    for sg in (1, -1):
        # the whole swept tube projected (a horizontal tube from the cowl side to the outlet), with the dark
        # outlet collar seen end-on at its outboard end
        S_ = stack_front_silhouette(sg)
        poly(ds, v, S_, col(L.SURFACES["exhaust"]))
        path, ra, rb = exhaust_stack(sg)
        e = path[-1]
        poly(ds, v, np.c_[e[1] + 0.55 * ra * np.cos(th), e[2] + 0.55 * rb * np.sin(th)], "#1E1B18")
        yb = np.linspace(path[0, 1], e[1], 5)[1:-1]
        hl = np.c_[np.r_[yb[0], yb[-1], yb[-1], yb[0]], e[2] + rb * np.array([0.55, 0.55, 0.30, 0.30])]
        poly(ds, v, hl, "#E4DED3")
        outline(ds, v, S_, W_THIN)
    sp = np.c_[F.SPINNER_R * np.cos(th), F.PROP_AXIS_Z + F.SPINNER_R * np.sin(th)]
    poly(ds, v, sp, col(L.SURFACES["spinner"]))
    poly(ds, v, np.c_[0.35 * F.SPINNER_R * np.cos(th) - 0.06, F.PROP_AXIS_Z + 0.06 + 0.35 * F.SPINNER_R * np.sin(th)],
         "#EEF1F4")
    outline(ds, v, sp, W_FINE)
    ds.cv.path(v.pts(np.c_[PP.PROP_R * np.cos(th), F.PROP_AXIS_Z + PP.PROP_R * np.sin(th)]), W_THIN, PHANTOM,
               closed=True, color=MUTED)
    ds.cv.line(v.pt(0.0, -0.05), v.pt(0.0, 4.35), W_GRID, CHAIN, color=MUTED)
    X, Y = v.pt(0.0, 0.0)
    view_title(ds, X, Y + 9.0, "VIEW C - FRONT", "SEEN FROM AHEAD, STARBOARD LEFT, WINGS BROKEN AT BL 2600 - "
                                                  "SCALE 1:30")


# ================================================================================================ photo tools (private)
# Camera-matched photographs of MSN 3008 (git-ignored cache).  refs/cache/overlays/livery/cams.json holds, per photo,
# a pinhole camera fitted to named model points (spinner tip, wheel axles, window centres, glazing corners, bullet
# nose, tailplane tips): R = rotvec(p[0:3]), t = p[3:6], f = p[6]; Xc = R X + t; u = W/2 + f Xc/Zc, v = H/2 + f Yc/Zc.
# Nothing below is needed for the clean sheet.
def load_cams():
    f = LIV_CACHE / "cams.json"
    return json.loads(f.read_text()) if f.exists() else {}


class Cam:
    def __init__(self, d):
        from scipy.spatial.transform import Rotation
        self.p = np.asarray(d["p"], float)
        self.W, self.H = d["W"], d["H"]
        self.R = Rotation.from_rotvec(self.p[:3]).as_matrix()
        self.t, self.f = self.p[3:6], self.p[6]

    def cam(self, X):
        return np.atleast_2d(np.asarray(X, float)) @ self.R.T + self.t

    def project(self, X):
        Xc = self.cam(X)
        return np.c_[self.W / 2 + self.f * Xc[:, 0] / Xc[:, 2], self.H / 2 + self.f * Xc[:, 1] / Xc[:, 2]], Xc[:, 2]

    def center(self):
        return -self.R.T @ self.t


def photo_image(d):
    from PIL import Image
    return Image.open(CACHE / d["file"]).convert("RGB")


def rectify_side(d, side, x0, x1, z0, z1, ppm):
    """The photo resampled onto the fuselage side projection (x, z) (nose left): (H, W, 3) float array, NaN
    where the OML point is off the fuselage, faces away from the camera or leaves the image."""
    cam, img = Cam(d), np.asarray(photo_image(d), float) / 255.0
    xs = x0 + (np.arange(int((x1 - x0) * ppm)) + 0.5) / ppm
    zs = z1 - (np.arange(int((z1 - z0) * ppm)) + 0.5) / ppm
    X, Z = np.meshgrid(xs, zs)
    xc = np.clip(X, X0_SIDE, X1_SIDE)
    zt, zb = F.z_top(xc), F.z_bot(xc)
    on = (X >= X0_SIDE) & (X <= X1_SIDE) & (Z < zt - 1e-3) & (Z > zb + 1e-3)
    t = F.t_of(xc, np.clip(Z, zb + 1e-4, zt - 1e-4), side).ravel()
    xr = xc.ravel()
    e = 1e-3
    P = F.section(xr, t)
    N = np.cross(F.section(np.clip(xr + e, X0_SIDE, X1_SIDE), t) - F.section(np.clip(xr - e, X0_SIDE, X1_SIDE), t),
                 F.section(xr, (t + e) % 1) - F.section(xr, (t - e) % 1))
    N *= np.sign(np.sum(N * (P - np.c_[xr, np.zeros_like(xr), F.z_mw(xr)]), 1))[:, None]
    vis = np.sum(N * (cam.center() - P), 1) > 0
    uv, depth = cam.project(P)
    Hh, Ww = img.shape[:2]
    ok = on.ravel() & vis & (depth > 0) & (uv[:, 0] >= 0) & (uv[:, 0] < Ww - 1) & (uv[:, 1] >= 0) & (uv[:, 1] < Hh - 1)
    u, v = uv[:, 0], uv[:, 1]
    ui, vi = np.floor(u).astype(int).clip(0, Ww - 2), np.floor(v).astype(int).clip(0, Hh - 2)
    fu, fv = (u - ui)[:, None], (v - vi)[:, None]
    c = (img[vi, ui] * (1 - fu) * (1 - fv) + img[vi, ui + 1] * fu * (1 - fv) + img[vi + 1, ui] * (1 - fu) * fv
         + img[vi + 1, ui + 1] * fu * fv)
    out = np.full((len(xr), 3), np.nan)
    out[ok] = c[ok]
    return out.reshape(len(zs), len(xs), 3), xs, zs


# photos and station ranges used for the white-stroke measurements (port nose: the starboard nose is in shade)
MARK_SOURCES = (("stbd_ground", +1, 3.8, 13.6), ("port_hangar_130", -1, 1.15, 4.5), ("port_hangar_81", -1, 1.15, 4.5))


def photo_marks(step=0.05, ppm=200, write=True):
    """White-stroke centres on the rectified photos: per station column, runs of white pixels (saturation < 0.30,
    max channel > 0.62) 8-150 mm tall -> (x, z, photo).  Written to refs/cache/overlays/livery/measurements.json
    together with per-stroke residuals (photo centre - our centre line) for the clean sheet's curve table."""
    cams = load_cams()
    pts = []
    for key, side, xa, xb in MARK_SOURCES:
        if key not in cams:
            continue
        A, xs, zs = rectify_side(cams[key], side, xa, xb, 0.95, 2.85, ppm)
        for x in np.arange(xa, xb + 1e-9, step):
            j = int(round((x - xa) * ppm))
            if j >= A.shape[1]:
                continue
            col = np.nanmean(A[:, max(j - 1, 0):j + 2], 1)
            mx, mn = np.nanmax(col, 1), np.nanmin(col, 1)
            w = ((mx - mn) / np.maximum(mx, 1e-6) < 0.30) & (mx > 0.62) & np.isfinite(mx)
            k = 0
            while k < len(w):
                if not w[k]:
                    k += 1
                    continue
                m = k
                while m < len(w) and w[m]:
                    m += 1
                h = (m - k) / ppm
                if 0.008 <= h <= 0.15:
                    pts.append((float(x), float(0.5 * (zs[k] + zs[m - 1])), key, float(h)))
                k = m
    res = stroke_residuals(pts)
    if write:
        LIV_CACHE.mkdir(parents=True, exist_ok=True)
        (LIV_CACHE / "measurements.json").write_text(json.dumps(dict(side_white=pts, residuals=res), indent=0))
    return pts, res


def stroke_residuals(pts, tol=0.05):
    """Per white stroke: photo white-run centres within tol of our centre line -> (n, median dz, rms dz, coverage =
    fraction of our stroke's stations with a photo run within tol)."""
    out = {}
    P = np.array([(p[0], p[1]) for p in pts]) if pts else np.zeros((0, 2))
    for sid, s in L.strokes().items():
        if s.mat != "paint_pinstripe" or not len(P):
            continue
        m = (P[:, 0] >= s.x0 + 0.05) & (P[:, 0] <= s.x1 - 0.05)
        if not m.any():
            continue
        dz = P[m, 1] - s.c(P[m, 0])
        near = np.abs(dz) < tol
        if not near.any():
            out[sid] = dict(n=0)
            continue
        xs_ = np.unique(np.round(P[m][near, 0], 3))
        allx = np.unique(np.round(P[m, 0], 3))
        out[sid] = dict(n=int(near.sum()), median=float(np.median(dz[near])), rms=float(np.sqrt(np.mean(dz[near] ** 2))),
                        coverage=float(len(xs_) / max(len(allx), 1)))
    return out


def _surf_quads(G, colors, cam, cull=None):
    """Quads of a sampled surface G (n, m, 3) with per-cell colours (n-1, m-1) -> list of (depth, uv (4, 2), rgb)."""
    uv, z = cam.project(G.reshape(-1, 3))
    uv = uv.reshape(G.shape[0], G.shape[1], 2)
    z = z.reshape(G.shape[:2])
    out = []
    C = cam.center()
    for i in range(G.shape[0] - 1):
        for j in range(G.shape[1] - 1):
            q = (uv[i, j], uv[i + 1, j], uv[i + 1, j + 1], uv[i, j + 1])
            zz = 0.25 * (z[i, j] + z[i + 1, j] + z[i + 1, j + 1] + z[i, j + 1])
            if zz <= 0.1:
                continue
            if cull is not None:
                P = G[i, j]
                if np.dot(cull[i, j], C - P) < 0:
                    continue
            out.append((zz, q, colors[i][j]))
    return out


def _rgb(name):
    h = col(name)
    return tuple(int(h[k:k + 2], 16) for k in (1, 3, 5))


def render_livery(d, scale=0.5):
    """Our scheme (livery curves on the Stage-2 outlines) rendered through the photo's camera: painter's
    algorithm on sampled surfaces (fuselage OML, fin, dorsal, bullet, tailplane, wings, winglets, spinner, pod)."""
    from PIL import Image, ImageDraw
    cam = Cam(d)
    quads = []
    names = list(L.PAINT_ORDER) + [L.BASE]
    pal = [_rgb(n) for n in names]
    glass = _rgb("glass")
    # fuselage
    xs = np.arange(X0_SIDE, X1_SIDE, 0.010)
    ts = np.linspace(0, 1, 361)
    X, T = np.meshgrid(xs, ts, indexing="ij")
    G = F.section(X, T)
    Xm, Tm = 0.5 * (X[1:, 1:] + X[:-1, :-1]), 0.5 * (T[1:, 1:] + T[:-1, :-1])
    Pm = F.section(Xm, Tm)
    idx = L.side_paint(Pm[..., 0], Pm[..., 2])
    cols = np.array(pal)[idx]
    s = np.where(Pm[..., 1] >= 0, 1, -1) * np.abs(Pm[..., 1])
    gl = np.minimum(CG.windshield_sdf(Pm[..., 0], s, Pm[..., 2], Pm[..., 1]), CG.sidewindow_sdf(Pm[..., 0], Pm[..., 1], Pm[..., 2]))
    for o in FP.openings_table():
        if o["kind"] == "window":
            on_side = np.sign(Pm[..., 1]) == o["side"]
            gl = np.minimum(gl, np.where(on_side & (np.abs(Pm[..., 1]) > 0.3), FP.window_sdf(Pm[..., 0], Pm[..., 2], o["cx"]), 1.0))
    cols[gl < 0] = glass
    ex = FP.EXIT
    ring = np.abs(FP.rr((Pm[..., 0], Pm[..., 2]), ex)) - L.EXIT_MARK["half_width"]
    cols[(ring < 0) & (Pm[..., 1] > 0.3)] = _rgb("paint_pinstripe")
    Nrm = np.cross(G[1:, :-1] - G[:-1, :-1], G[:-1, 1:] - G[:-1, :-1])
    Nrm *= np.sign(np.sum(Nrm * (G[:-1, :-1] - np.stack([X[:-1, :-1], 0 * X[:-1, :-1], F.z_mw(X[:-1, :-1])], -1)),
                          -1))[..., None]
    quads += _surf_quads(G, cols, cam, cull=Nrm)
    xc = cos_pts(24)

    def sections(secs, color_fn):
        for face in ("upper", "lower"):
            Gs = np.array([getattr(sec, face)(xc) for sec in secs])
            Mid = 0.5 * (Gs[1:, 1:] + Gs[:-1, :-1])
            cc = [[color_fn(p, face) for p in row] for row in Mid]
            quads.extend(_surf_quads(Gs, cc, cam))
    capc, basec = _rgb("paint_white"), _rgb(L.BASE)
    fin_col = lambda p, f: capc if (p[0] >= L.FIN_CAP_X0 and p[2] > float(L.fin_cap_line(p[0]))) else \
        pal[int(L.side_paint(np.array([p[0]]), np.array([p[2]]), fin=True, mask=False)[0])]   # noqa: E731
    sections([E.fin_section(z) for z in np.linspace(1.85, 4.05, 34)], fin_col)
    top = float(E._dorsal_curve()[-1, 1])
    sections([E.dorsal_section(z) for z in np.linspace(2.5, top - 0.01, 14)], lambda p, f: basec)
    sil = _rgb(L.SURFACES["stab_upper"])
    sections([E.stab_section(y) for y in np.linspace(-E.STAB_TIP_Y + 0.002, E.STAB_TIP_Y - 0.002, 40)],
             lambda p, f: sil)
    B = np.array([E.bullet_section(x, 32) for x in np.linspace(E.BULLET_X[0] + 1e-3, E.BULLET_X[1], 30)])
    quads += _surf_quads(np.concatenate([B, B[:, :1]], 1), [[_rgb("paint_white")] * 32] * 29, cam)
    up, lo = _rgb(L.SURFACES["wing_upper"]), _rgb(L.SURFACES["wing_lower"])
    yr = float(F.half_w(6.0))
    for sg in (1, -1):
        secs = [W.section_at(y) for y in np.linspace(yr, W.SEMI, 30)]
        for face, c_ in (("upper", up), ("lower", lo)):
            Gs = np.array([getattr(sec, face)(xc) for sec in secs]) * [1, sg, 1]
            quads += _surf_quads(Gs, [[c_] * (len(xc) - 1)] * (len(secs) - 1), cam)
        ws = W.winglet_sections(24, 20)
        for face, c_ in (("upper", _rgb(L.SURFACES["winglet_inboard"])), ("lower", _rgb(L.SURFACES["winglet_outboard"]))):
            Gs = np.array([getattr(sec, face)(xc) for sec in ws]) * [1, sg, 1]
            quads += _surf_quads(Gs, [[c_] * (len(xc) - 1)] * (len(ws) - 1), cam)
    # spinner and radar pod (bodies of revolution)
    a_, b_ = F.SPINNER_SHAPE
    tt = np.linspace(0, 1, 30)
    sx = F.STA["spinner_tip"] + (X0_SIDE - F.STA["spinner_tip"]) * tt
    sr = F.SPINNER_R * (1 - (1 - tt) ** a_) ** b_
    ang = np.linspace(0, 2 * np.pi, 37)
    Gs = np.stack([np.repeat(sx[:, None], 37, 1), sr[:, None] * np.cos(ang), F.PROP_AXIS_Z + sr[:, None] * np.sin(ang)], -1)
    quads += _surf_quads(Gs, [[(198, 204, 211)] * 36] * 29, cam)
    prof = np.array(D.radar_pod_profile(30))
    Gs = np.stack([np.repeat(prof[:, :1], 37, 1), D.POD_Y + prof[:, 1:] * np.cos(ang), D.POD_Z + prof[:, 1:] * np.sin(ang)], -1)
    pc = [[_rgb(L.SURFACES["pod_radome"] if prof[i, 0] < D.POD_X_JOINT else L.SURFACES["pod_body"])] * 36
          for i in range(len(prof) - 1)]
    quads += _surf_quads(Gs, pc, cam)
    img = Image.new("RGB", (int(cam.W * scale), int(cam.H * scale)), (236, 238, 240))
    dr = ImageDraw.Draw(img)
    for zz, q, c_ in sorted(quads, key=lambda r: -r[0]):
        dr.polygon([(float(p[0]) * scale, float(p[1]) * scale) for p in q], fill=tuple(int(v) for v in c_))
    return img


def _bbox(d, pad=0.06):
    """Image bbox of the aircraft (projected fuselage, fin, wing tips, spinner) with a margin."""
    cam = Cam(d)
    xs = np.linspace(F.STA["spinner_tip"], X1_SIDE, 60)
    P = [np.c_[xs, np.zeros_like(xs), F.z_top(np.clip(xs, X0_SIDE, X1_SIDE))],
         np.c_[xs, np.zeros_like(xs), F.z_bot(np.clip(xs, X0_SIDE, X1_SIDE))],
         np.array([[E.FIN_TE[1][0], 0, 4.1], [E.BULLET_X[1], 0, 4.2], [W.x_le(W.SEMI), 8.1, 1.9],
                   [W.x_le(W.SEMI), -8.1, 1.9], [PP.PROP_X, 0, F.PROP_AXIS_Z + 1.3], [6.4, 2.27, 0.0],
                   [6.4, -2.27, 0.0]])]
    uv, z = cam.project(np.vstack(P))
    uv = uv[z > 0]
    lo, hi = uv.min(0), uv.max(0)
    m = pad * (hi - lo)
    return (int(max(lo[0] - m[0], 0)), int(max(lo[1] - m[1], 0)), int(min(hi[0] + m[0], cam.W)),
            int(min(hi[1] + m[1], cam.H)))


def sheet_view_image(view, x0, x1, z0, z1, ppm):
    """Crop of the clean sheet PDF (out/drawings/L5.pdf) over the model window x0..x1, z0..z1 of a side view,
    resampled to ppm pixels per metre (views.json gives the view transform)."""
    from PIL import Image
    import pymupdf
    vj, pdf = M.OUT_CLEAN / "L5.views.json", M.OUT_CLEAN / "L5.pdf"
    if not (vj.exists() and pdf.exists()):
        return None
    v = json.loads(vj.read_text())["views"][view]
    A, t = np.array(v["A"]), np.array(v["t"])
    p0, p1 = A @ [x0, z1] + t, A @ [x1, z0] + t
    X0, X1 = sorted((p0[0], p1[0]))
    Y0, Y1 = sorted((p0[1], p1[1]))
    dpi = int(round(2 * ppm / abs(A[0, 0]) * 25.4))            # oversample x2, resized below
    doc = pymupdf.open(str(pdf))
    pix = doc[0].get_pixmap(dpi=dpi, clip=pymupdf.Rect(X0 * 72 / 25.4, Y0 * 72 / 25.4, X1 * 72 / 25.4, Y1 * 72 / 25.4))
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()
    if A[0, 0] < 0:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    return im.resize((int((x1 - x0) * ppm), int((z1 - z0) * ppm)))


def photo_compare(out=None, keys=("port_hangar_130", "stbd_ground", "stbd_air")):
    """Private side-by-side: each photo (crop) next to our scheme rendered through the same camera, then the
    rectified starboard / port photos above our flat port profile colours.  -> refs/cache/overlays/L5_photo_compare.png"""
    from PIL import Image, ImageDraw
    cams = load_cams()
    rows = []
    label_h = 26
    for key in keys:
        if key not in cams:
            continue
        d = cams[key]
        ph = photo_image(d)
        rn = render_livery(d, scale=1.0)
        box = _bbox(d)
        a, b = ph.crop(box), rn.crop(box)
        hgt = 520
        k = hgt / a.height
        a = a.resize((int(a.width * k), hgt))
        b = b.resize((int(b.width * k), hgt))
        row = Image.new("RGB", (a.width + b.width + 12, hgt + label_h), "white")
        row.paste(a, (0, label_h))
        row.paste(b, (a.width + 12, label_h))
        dr = ImageDraw.Draw(row)
        dr.text((4, 6), f"PHOTO {key}: {d['note']}  (camera fit rms {d['rms']:.1f} px, {len(d['pairs'])} points)",
                fill=(0, 0, 0))
        dr.text((a.width + 16, 6), "OURS: model/livery.py on the Stage-2 outlines, same camera", fill=(0, 0, 0))
        rows.append(row)
    # rectified strips vs our flat profile (port view, nose left)
    x0, x1, z0, z1, ppm = 1.0, 13.8, 0.9, 2.9, 90
    strips = []
    for key, side, xa, xb in (("stbd_ground", 1, x0, x1), ("stbd_air", 1, x0, x1), ("port_hangar_130", -1, x0, 4.6)):
        if key not in cams:
            continue
        A, xs, zs = rectify_side(cams[key], side, x0, xb, z0, z1, ppm)
        im = np.where(np.isnan(A), 1.0, A)
        strip = Image.new("RGB", (int((x1 - x0) * ppm), len(zs)), "white")
        strip.paste(Image.fromarray((im * 255).astype(np.uint8)), (0, 0))
        strips.append((f"rectified onto the side projection: {key} ({'starboard' if side > 0 else 'port'})", strip))
    ours = sheet_view_image("port", x0, x1, z0, z1, ppm)
    if ours is not None:
        strips.append(("ours: sheet L5 PORT SIDE view (out/drawings/L5.pdf), same scale and stations", ours))
    for lab, st in strips:
        row = Image.new("RGB", (st.width, st.height + label_h), "white")
        row.paste(st, (0, label_h))
        dr = ImageDraw.Draw(row)
        dr.text((4, 6), lab, fill=(0, 0, 0))
        for x in np.arange(2.0, 13.6, 1.0):
            X = (x - x0) * ppm
            dr.line([(X, label_h), (X, label_h + 6)], fill=(200, 0, 0))
            dr.text((X + 2, label_h), f"{x:.0f}", fill=(200, 0, 0))
        rows.append(row)
    Wt = max(r.width for r in rows)
    Ht = sum(r.height + 8 for r in rows)
    canvas = Image.new("RGB", (Wt, Ht), (250, 250, 248))
    y = 0
    for r in rows:
        canvas.paste(r, (0, y))
        y += r.height + 8
    out = out or (CACHE / "overlays" / "L5_photo_compare.png")
    canvas.save(out)
    return out


# ================================================================================================ overlay (private)
def draw_overlay(ds):
    """Overlay variant: the registered Pilatus drawing in red (outlines), photo-derived stripe measurements
    (blue) from refs/cache/overlays/livery/measurements.json when present."""
    vp, vs, vu, vl = (ds.views[k] for k in ("port", "starboard", "plan_upper", "plan_lower"))
    for v in (vp, vs):
        ds.ov_mbp(v, "side", kinds=("outline",), w=0.14)
    for v in (vu, vl):
        ds.ov_mbp(v, "plan", kinds=("outline",), w=0.14, clip=(0.2, 0.0, 15.0, 8.3))
    mfile = LIV_CACHE / "measurements.json"
    if mfile.exists():
        meas = json.loads(mfile.read_text())
        pts = np.array([p[:2] for p in meas.get("side_white", [])])
        if len(pts):
            for v in (vp, vs):
                ds.ov_marks(v, pts, r=0.35)
        ds.log.append(f"overlay: {len(pts)} photo stripe marks")
    X, Y = vp.pt(0.4, 4.3)
    ds.ov_text(X, Y, "RED: PILATUS DRAWING OUTLINES   BLUE: WHITE-STRIPE EDGES MEASURED ON THE RECTIFIED PHOTOS",
               size=2.2)


def draw(ds):
    draw_clean(ds)
    try:
        draw_overlay(ds)
    except Exception as e:                      # noqa: BLE001 -- the clean sheet must not depend on refs/cache
        ds.log.append(f"overlay skipped: {e}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["marks"]:                 # private: measure the white strokes on the rectified photos
        pts, res = photo_marks()
        print(f"{len(pts)} white-run centres")
        for k, r in res.items():
            print(f"  {k:3s} " + " ".join(f"{a}={b:.3f}" if isinstance(b, float) else f"{a}={b}" for a, b in r.items()))
    elif sys.argv[1:2] == ["compare"]:             # private: photo vs ours side by side
        print(photo_compare())
    else:
        M.main(["L5"] + sys.argv[1:])
