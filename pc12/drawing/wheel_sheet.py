"""
Sheet L4W -- WHEELS & TYRES: the main and nose wheel assemblies, drawn FROM THE PARAMETER TABLES of model/wheels.py
(tyre envelopes and sections, split-hub wheel halves, main hub fairing, six-piston main brake, axles) -- never from
the mesh.  Gear context (trailing arm, leg, nose fork) from model/gear.py positions, drawn as adjacent parts.

    python3 -m drawing.master L4W          (or: python3 -m drawing.wheel_sheet)

First-angle projection, each assembly as a three-view at 1:3 on a common ground line:
  MAIN (port unit)  SIDE view from port (outboard face, hub fairing; the principal view), FRONT view from ahead to its
                    right with the upper half in section A-A through the axle, view C from starboard (the inboard /
                    brake face, the rear view) at the far right, and the TOP view from above below the side view;
  NOSE              SIDE view from port, FRONT view with half section B-B to its right, TOP view below.
Details at 1:2: H (main hub, brake and hub fairing in section), D / F (tyre sections with the groove pattern and the
TRA growth envelope).  Tables: key dimensions with source tags, the photo check (deviation call-outs), materials.
Main tyre: the MODELLED envelope wheels.MAIN_TYRE_ENV (MAIN_TYRE_CHOICE: the 22x8.50-10 of Jane's / the Pilatus
drawing, pc12/CLAUDE.md's sourced size, until the owner decides) is drawn in full; the other candidate
(wheels.MAIN_TYRE_ALT: the proposed 8.50-10 Type III of the tyre makers / parts lists / photos) as a deviation outline in
the accent colour, its TRA growth envelope in detail D.  The 3-D wheels (model/wheels.py main_wheel / nose_wheel) are
built from these tables.  The overlay
variant (refs/cache/overlays/L4W_overlay.*, git-ignored) adds the registered Pilatus drawing's wheel circles in red
and the photo-measured tyre / fairing sizes and groove positions in blue.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from drawing import master as M  # noqa: E402
from drawing.master import (INK, MUTED, PAPER, ACCENT, BLUE, W_OBJ, W_FINE, W_DIM, W_THIN,  # noqa: E402
                            CHAIN, PHANTOM, table, notes, view_title, side_view, plan_view, legend_rows, scale_bar,
                            view_arrow, detail_circle)
from drawing.canvas import text_width  # noqa: E402
from model import wheels as WH  # noqa: E402
from model import gear as G  # noqa: E402

SHEET = dict(id="L4W", title="WHEELS & TYRES", subtitle="WHEELS & TYRES - MAIN AND NOSE WHEEL ASSEMBLIES",
             size="A0", scale="1:3 / 1:2", rev="A", order=45)

MOD, ALT = WH.MAIN_TYRE_ENV, WH.MAIN_TYRE_ALT          # modelled main tyre / the other candidate
LOADED_MAIN = WH.loaded_blend("main")[3] is not None     # the modelled main tyre is drawn flattened at the ground


def tyre_name(e):
    return "8.50-10 TYPE III" if e is WH.MAIN_TYRE_850 else str(e["size"]).upper()


HID = (1.6, 0.9)
SUP = (3.0, 1.0)               # superseded 22 in tyre (accent colour)
TYRE_FILL = "#C9CFD2"          # rubber in section
ROTOR_FILL = "#39434A"         # brake rotors (steel)
PLATE_FILL = "#8E989E"         # stators, pressure / back plate
LINING_FILL = "#EFE9DA"        # riveted linings
W_HATCH = 0.10
TXT = 2.4                      # leader text
TXT_S = 2.2                    # secondary leader lines

# ---- layout (sheet mm).  Each group's side / front / rear views stand on one ground line, its top view below the
# side view (first angle).  Main group across the top, nose group below it, details in the middle, tables at the right.
SC = 3                         # three-view scale 1:SC
K = 1000.0 / SC                # sheet mm per model metre in the three-views
GY_M, GY_N = 250.0, 650.0      # ground lines of the main / nose groups
MAIN_X = dict(side=182.0, front=470.0, rear=722.0)
NOSE_X = dict(side=182.0, front=425.0)
TOP_M, TOP_N = 362.0, 742.0    # axle lines of the top views
DET_H0 = (650.0, 415.0)        # detail H (1:2): sheet of (s, r) = (0, 0)
DET_TOP = dict(main=484.0, nose=662.0)   # sheet y of the crown in details D / F
DET_X = dict(main=745.0, nose=745.0)
X_TAB = 895.0                  # right-hand column: tables, legend, notes
PORT_Y = -G.TRACK / 2          # the port main unit's axle BL


# ============================================================================================ views / helpers
def sec_view(name, origin, scale, box=None, note="local (s, r) about the axle, seen from ahead: s + to port "
                                                  "(right), model y = axle y - s, z = axle z + r"):
    """Local wheel-section view: (s, r) -> sheet, +s (the port face: main outboard, nose port) to the RIGHT, as
    seen from ahead for the port unit; r up."""
    return M._mk(name, "yz", 1, -1, origin, (0.0, 0.0), scale, box, note)


def stbd_view(name, origin, scale, model_origin, box=None):
    """Side view seen from STARBOARD (nose right): (x, z) -> sheet."""
    return M._mk(name, "xz", -1, -1, origin, model_origin, scale, box, "seen from starboard, nose right")


def mirror(P):
    return np.asarray(P, float) * [-1, 1]


def circle_pts(c, r, n=145, a0=0.0, a1=360.0):
    a = np.radians(np.linspace(a0, a1, n))
    return np.c_[c[0] + r * np.cos(a), c[1] + r * np.sin(a)]


def hatch(ds, P, ang=45.0, step=1.1, w=W_HATCH, color=INK):
    """Section hatching of the closed sheet polygon P: parallel lines at `ang` deg (sheet, y down), `step` mm apart,
    phased on a global grid (adjacent parts with the same angle continue each other's lines)."""
    P = np.asarray(P, float)
    a = math.radians(ang)
    Rm = np.array([[math.cos(a), math.sin(a)], [-math.sin(a), math.cos(a)]])
    Q = P @ Rm.T
    E0, E1 = Q, np.roll(Q, -1, axis=0)
    y0, y1 = Q[:, 1].min(), Q[:, 1].max()
    for y in np.arange(math.floor(y0 / step) * step + 0.5 * step, y1, step):
        m = ((E0[:, 1] <= y) & (E1[:, 1] > y)) | ((E1[:, 1] <= y) & (E0[:, 1] > y))
        if not m.any():
            continue
        t = (y - E0[m, 1]) / (E1[m, 1] - E0[m, 1])
        xs = np.sort(E0[m, 0] + t * (E1[m, 0] - E0[m, 0]))
        for xa, xb in zip(xs[0::2], xs[1::2]):
            seg = np.array([[xa, y], [xb, y]]) @ Rm
            ds.cv.line(tuple(seg[0]), tuple(seg[1]), w, color=color)


def section_part(ds, v, P, ang=45.0, step=1.1, w=W_OBJ, fill=PAPER):
    """Sectioned metal part: paper fill (hides what is behind), hatch, outline."""
    S_ = v(P)
    ds.cv.path([tuple(q) for q in S_], 0.0, closed=True, fill=fill, stroke=False)
    hatch(ds, S_, ang, step)
    ds.cv.path([tuple(q) for q in S_], w, closed=True)


def rect(s0, s1, r0, r1):
    return np.array([[s0, r0], [s1, r0], [s1, r1], [s0, r1]])


def leader(ds, P, text, off, lines=None, size=TXT, color=INK, dot=True, arrow=False, weight=600, shoulder=2.0):
    """Leader from the sheet point P to P + off, a short horizontal shoulder, then the text (first line bold)."""
    X, Y = P
    tx, ty = X + off[0], Y + off[1]
    right = off[0] >= 0
    ds.cv.line((X, Y), (tx, ty), W_DIM, color=color)
    ds.cv.line((tx, ty), (tx + (shoulder if right else -shoulder), ty), W_DIM, color=color)
    if arrow:
        ds.sh.arrow((X, Y), (X - tx, Y - ty))
    elif dot:
        ds.cv.circle(X, Y, 0.5, w=0.0, fill=color, stroke=False)
    x2 = tx + (shoulder + 0.7 if right else -shoulder - 0.7)
    for i, t in enumerate([text] + list(lines or [])):
        ds.text(x2, ty + i * 1.32 * size, t, size if i == 0 else min(size, TXT_S), "label",
                "start" if right else "end", vcenter=True, fill=color, tag="leader", weight=weight if i == 0 else 400)


def leader_to(ds, P, T, text, lines=None, size=2.3, color=INK, weight=600, dot=True):
    """Leader from the sheet point P to the text anchor T (absolute sheet mm); text on the side away from P."""
    leader(ds, P, text, (T[0] - P[0], T[1] - P[1]), lines=lines, size=size, color=color, weight=weight, dot=dot)


def dia_leader(ds, c, r, ang, text, L=10.0, lines=None, size=TXT, color=INK):
    """Diameter / radius call-out: arrow onto the circle (sheet centre c, radius r mm) at sheet angle `ang` (deg, y
    down), leader outwards, a shoulder, and the text stacked ABOVE the shoulder (the last line next to it)."""
    a = math.radians(ang)
    u = np.array([math.cos(a), math.sin(a)])
    tip = np.asarray(c, float) + r * u
    el = tip + L * u
    ds.cv.line(tuple(tip), tuple(el), W_DIM, color=color)
    ds.sh.arrow(tuple(tip), tuple(-u))
    right = u[0] >= 0
    T = [text] + list(lines or [])
    w_ = max(text_width(t, size, "mono") for t in T)
    x_end = el[0] + (w_ + 1.6 if right else -w_ - 1.6)
    ds.cv.line(tuple(el), (x_end, el[1]), W_DIM, color=color)
    for i, t in enumerate(T):
        ds.text(el[0] + (0.8 if right else -0.8), el[1] - 0.9 - (len(T) - 1 - i) * 1.3 * size, t, size, "mono",
                "start" if right else "end", fill=color, tag="dim")


def centre_cross(ds, v, a, b, ra, rb=None, ext=3.0):
    """Centre lines through (a, b): horizontal and vertical chain lines of half-length ra (+ ext mm)."""
    rb = ra if rb is None else rb
    X, Y = v.pt(a, b)
    ka, kb = abs(ra * v.k) + ext, abs(rb * v.k) + ext
    ds.cv.line((X - ka, Y), (X + ka, Y), W_THIN, CHAIN)
    ds.cv.line((X, Y - kb), (X, Y + kb), W_THIN, CHAIN)


def ground(ds, v, a0, a1, b=0.0, label=None, at="left"):
    """Ground line (model b = const) with short hatch ticks below; optional label above the line at one end."""
    p, q = v.pt(a0, b), v.pt(a1, b)
    x0, x1 = min(p[0], q[0]), max(p[0], q[0])
    ds.cv.line((x0, p[1]), (x1, p[1]), W_FINE)
    for x in np.arange(x0 + 1.0, x1, 2.2):
        ds.cv.line((x, p[1]), (x - 1.4, p[1] + 1.4), W_THIN, color=MUTED)
    if label:
        if at == "left":
            ds.text(x0 + 0.5, p[1] - 1.3, label, 2.0, "label", "start", fill=MUTED, tag="grid")
        else:
            ds.text(x1 - 0.5, p[1] - 1.3, label, 2.0, "label", "end", fill=MUTED, tag="grid")


def wheel_circle(ds, v, c, r, w=W_OBJ, dash=None, fill=None, color=None):
    P = circle_pts(c, r)
    ds.cv.path(v.pts(P), w, dash, closed=True, fill=fill, stroke=w > 0, color=color)


def clip_half(P, axis, value, keep="le"):
    """Sutherland-Hodgman clip of the closed polygon P to P[:, axis] <= value (keep='le') or >= value ('ge')."""
    P = np.asarray(P, float)
    sg = 1.0 if keep == "le" else -1.0
    out = []
    n = len(P)
    for i in range(n):
        a, b = P[i], P[(i + 1) % n]
        ia, ib = sg * (a[axis] - value) <= 0, sg * (b[axis] - value) <= 0
        if ia:
            out.append(a)
        if ia != ib:
            t = (value - a[axis]) / (b[axis] - a[axis])
            out.append(a + t * (b - a))
    return np.array(out)


def clipped_part(ds, v, P, box, ang=None, step=1.1, fill=PAPER, w=W_OBJ, cut_w=W_THIN):
    """A closed part polygon P (model) shown inside box (a0, b0, a1, b1): filled (+ hatched) clip, the original
    outline clipped to the box, and the cut edges as thin dashed break lines."""
    a0, b0, a1, b1 = box
    Q = np.asarray(P, float)
    for ax_, val, kp in ((0, a0, "ge"), (0, a1, "le"), (1, b0, "ge"), (1, b1, "le")):
        if len(Q):
            Q = clip_half(Q, ax_, val, kp)
    if len(Q) < 3:
        return
    S_ = v(Q)
    ds.cv.path([tuple(q) for q in S_], 0.0, closed=True, fill=fill, stroke=False)
    if ang is not None:
        hatch(ds, S_, ang, step)
    for seg in M.clip_polyline(np.vstack([P, P[:1]]), box):
        ds.cv.path(v.pts(seg), w)
    for i in range(len(Q)):                                   # cut edges lie on the box
        a, b = Q[i], Q[(i + 1) % len(Q)]
        for ax_, val in ((0, a0), (0, a1), (1, b0), (1, b1)):
            if abs(a[ax_] - val) < 1e-9 and abs(b[ax_] - val) < 1e-9:
                ds.cv.path(v.pts([a, b]), cut_w, (0.8, 0.6))


def outside_circle(P, c, r, n_sub=6):
    """Pieces of the polyline P that lie outside the circle (c, r): an adjacent part behind the tyre shows only
    where it clears the tyre's outline."""
    P = np.asarray(P, float)
    pts = [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        pts += list(a + (b - a) * (np.arange(1, n_sub + 1) / n_sub)[:, None])
    out, cur = [], []
    for q in pts:
        if np.hypot(q[0] - c[0], q[1] - c[1]) > r:
            cur.append(q)
        else:
            if len(cur) > 1:
                out.append(np.array(cur))
            cur = []
    if len(cur) > 1:
        out.append(np.array(cur))
    return out


def half_plane(ds, v, p_axis, p_end, letter, look, ext=6.0, length=8.0):
    """Cutting plane of a HALF section on the parent view: chain line from the axle (p_axis) to beyond the part
    (p_end), one thick end and one reference arrow (pointing along the sheet vector `look`) with the letter."""
    P0, P1 = np.array(v.pt(*p_axis)), np.array(v.pt(*p_end))
    t = (P1 - P0) / np.linalg.norm(P1 - P0)
    E1 = P1 + ext * t
    ds.cv.line(tuple(P0), tuple(E1), W_THIN, CHAIN)
    ds.cv.line(tuple(E1), tuple(E1 - 6.0 * t), 0.5)
    look = np.asarray(look, float) / np.linalg.norm(look)
    tail = M._big_arrow(ds, E1 - 3.0 * t, look, length=length)
    lp = tail - 3.0 * look
    ds.text(float(lp[0]), float(lp[1]), letter, M.REF_SIZE, "label", "middle", weight=700, vcenter=True, tag="ref")


def fmt(v, d=0):
    return f"{v * 1000:.{d}f}"


def band(p, q, hw):
    """Closed outline of a straight bar from p to q with half-width hw (2-D)."""
    p, q = np.asarray(p, float), np.asarray(q, float)
    d = (q - p) / np.linalg.norm(q - p)
    n = np.array([-d[1], d[0]]) * hw
    return np.array([p + n, q + n, q - n, p - n])


# ============================================================================================ main wheel
def main_axle():
    return float(G.MAIN_AXLE[0]), float(G.MAIN_AXLE[2])


ARM = dict(s=-0.14, t=0.0175, depth=0.035, yoke=(-0.14, -0.03), yoke_r=0.036)   # gear.build_main (port: s < 0 inboard)


def arm_pts():
    """Trailing arm context in the wheel plane (dx, dz about the axle): pivot, the bar outline (gear.build_main: a
    70 mm deep bar from the link pivot to the axle boss), leg direction."""
    ax, az = main_axle()
    L = np.array([G.MAIN_LINK_PIVOT[0] - ax, G.MAIN_LINK_PIVOT[2] - az])
    T = np.array([G.MAIN_TRUNNION[0] - ax, G.MAIN_TRUNNION[2] - az])
    return L, band((0.0, 0.0), L, ARM["depth"]), (T - L) / np.linalg.norm(T - L)


def draw_main_side(ds):
    """SIDE view of the port main wheel from port (its outboard face): loaded tyre, hub fairing with 5 screws and
    the valve hole; the trailing arm and leg behind it as adjacent parts."""
    ax, az = main_axle()
    v = ds.add_view(side_view("main_side", (MAIN_X["side"], GY_M - az * K), SC, model_origin=(ax, az),
                              box=(ax - 0.37, -0.06, ax + 0.37, az + 0.37)))
    fa = WH.MAIN_FAIRING
    env = WH.envelope("main")
    R, h = env["R"], env["R_loaded"]
    c = np.array([ax, az])
    C = np.array(v.pt(ax, az))
    k = v.k
    ground(ds, v, ax - 0.37, ax + 0.37, 0.0, "GROUND (STATIC)", at="left")
    # adjacent parts (phantom), visible only outside the tyre: trailing arm, link pivot / yoke, leg
    L, arm, u_leg = arm_pts()
    for P in (np.vstack([arm, arm[:1]]), circle_pts(L, ARM["yoke_r"], 49),
              band(L, L + u_leg * 0.13, G.MAIN_LEG_R[1])[[1, 0, 3, 2]]):
        for seg in outside_circle(P, (0.0, 0.0), R + 0.001):
            ds.cv.path(v.pts(seg + c), W_FINE, PHANTOM)
    # the other candidate main tyre (accent) and the free tyre below the ground (static deflection, phantom)
    wheel_circle(ds, v, c, ALT["R"], W_FINE, SUP, color=ACCENT)
    if LOADED_MAIN:
        ds.cv.path(v.pts(WH.free_below_ground("main") + c), W_FINE, PHANTOM)
    ds.cv.path(v.pts(WH.loaded_side_outline("main") + c), W_OBJ, closed=True)
    # hub fairing: lip (= rim flange tip, where the tyre leaves the flange), lip ring, raised face, screws, hole
    wheel_circle(ds, v, c, fa["r_lip"])
    wheel_circle(ds, v, c, fa["r_lip"] - fa["lip_w"], W_FINE)
    wheel_circle(ds, v, c, fa["r_face"] + fa["face_R"], W_THIN)
    wheel_circle(ds, v, c, fa["r_face"])
    wheel_circle(ds, v, c, fa["screw_r"], W_THIN, CHAIN)
    for dx, dz in WH.clock_points(fa["screws"], fa["screw_r"], fa["screw_th"]):
        X, Y = v.pt(ax + dx, az + dz)
        rr = fa["screw_d"] / 2 * k
        ds.cv.circle(X, Y, rr, w=W_FINE)
        ds.cv.line((X - rr * 0.7, Y), (X + rr * 0.7, Y), W_THIN)
    th = math.radians(fa["hole_th"])
    hc = np.array([fa["hole_r"] * math.cos(th), fa["hole_r"] * math.sin(th)])
    wheel_circle(ds, v, c + hc, fa["hole_d"] / 2)
    wheel_circle(ds, v, c + hc, 0.006, W_FINE)                                # valve cap seen through the hole
    centre_cross(ds, v, ax, az, R + 0.01, R + 0.01)
    ds.cv.line(tuple(C), v.pt(*(c + hc)), W_THIN, CHAIN)
    # section plane A-A (upper half, through the axle), seen from ahead: arrows point aft (+x = right)
    half_plane(ds, v, (ax, az), (ax, az + R + 0.004), "A", (1.0, 0.0))
    # ---- dimensions: axle WL (= loaded radius) and the loaded height on the right, the contact patch below
    Xg = C[0] + R * k + 12.0
    Yg = v.pt(ax, 0.0)[1]
    ds.sh.dim((Xg, C[1]), (Xg, Yg), Xg, f"{fmt(h)}", "v", f1=(C[0] + 3.0, C[1]), f2=(Xg, Yg))
    ds.sh.dim((Xg + 11.0, C[1] - R * k), (Xg + 11.0, Yg), Xg + 11.0, f"{fmt(h + R)}", "v",
              f1=(C[0] + 2.0, C[1] - R * k), f2=(Xg + 11.0, Yg))
    ds.text(Xg + 14.0, C[1] - 1.8, "AXLE WL = LOADED RADIUS", 2.1, "label", "start", fill=MUTED, tag="dim")
    _, _, a, rb = WH.loaded_blend("main")
    ab = math.radians(-100.0)
    if LOADED_MAIN:
        yp = Yg + 17.0
        ds.sh.dim(v.pt(ax - a, 0.0), v.pt(ax + a, 0.0), yp, f"{fmt(2 * a)}", "h", f1=v.pt(ax - a, 0.0),
                  f2=v.pt(ax + a, 0.0))
        ds.text(C[0] + a * k + 5.0, yp + 0.9, "CONTACT PATCH [E]", 2.1, "label", "start", fill=MUTED, tag="dim")
        leader(ds, v.pt(ax + R * math.cos(ab), az + R * math.sin(ab)), f"STATIC DEFLECTION {fmt(R - h)}",
               (-46.0, 16.0), lines=["FREE TYRE BELOW GROUND (PHANTOM)", f"BLEND R {fmt(rb)} TO THE FLAT [E]"],
               size=2.3, weight=500)
    else:
        leader(ds, v.pt(ax + R * math.cos(ab), az + R * math.sin(ab)), f"STATIC DEFLECTION {fmt(R - h, 1)}",
               (-46.0, 16.0), lines=["FREE CIRCLE CUT BY THE GROUND"], size=2.3, weight=500)
    # ---- call-outs: fairing and screws above the tyre, the rest outside it on the left / right
    dia_leader(ds, C, R * k, 158.0, f"Ø{fmt(2 * R)} FREE", L=14.0, lines=None)
    Ytop = C[1] - R * k
    alip = math.radians(58.0)
    leader(ds, v.pt(ax + fa["r_lip"] * math.cos(alip), az + fa["r_lip"] * math.sin(alip)),
           f"Ø{fmt(2 * fa['r_lip'])} HUB FAIRING LIP = RIM FLANGE",
           (C[0] + 62.0 - v.pt(ax + fa["r_lip"] * math.cos(alip), 0)[0], Ytop - 26.0 - v.pt(0, az + fa["r_lip"] * math.sin(alip))[1]),
           lines=[f"FACE Ø{fmt(2 * fa['r_face'])}, {fmt(fa['proud'])} PROUD [M]; LEG-DOOR COLOUR"], arrow=True)
    s0 = WH.clock_points(fa["screws"], fa["screw_r"], fa["screw_th"])[0]
    leader_to(ds, v.pt(ax + s0[0], az + s0[1]), (C[0] + 62.0, Ytop - 10.0),
              f"{fa['screws']} CSK SCREWS, 72° EQ SP, PCD {fmt(2 * fa['screw_r'])} [M]")
    leader_to(ds, v.pt(*(c + hc + [-0.02, 0.012])), (C[0] - R * k - 10.0, C[1] + 22.0),
              f"VALVE-ACCESS HOLE Ø{fmt(fa['hole_d'])} [M]", lines=[f"ON R {fmt(fa['hole_r'])}, VALVE BEHIND"])
    a22 = math.radians(232.0)
    Ra = ALT["R"]
    alt_src = ("TYRE MAKERS / PARTS LISTS / PHOTOS" if ALT is WH.MAIN_TYRE_850 else "JANE'S / PILATUS DWG")
    leader_to(ds, v.pt(ax + Ra * math.cos(a22), az + Ra * math.sin(a22)), (C[0] - R * k - 10.0, C[1] + 58.0),
              f"{tyre_name(ALT)} Ø{fmt(2 * Ra)}", lines=[WH.ALT_STATUS, alt_src], color=ACCENT)
    a_t = math.radians(-24.0)
    leader_to(ds, v.pt(ax + R * math.cos(a_t), az + R * math.sin(a_t)), (Xg + 26.0, C[1] + 50.0),
              f"TYRE {tyre_name(MOD)} (MODELLED)",
              lines=(["JANE'S / PILATUS DWG 190.10.40.432", "APPROVED SIZE, SHEETS L1-L5"] if MOD is WH.MAIN_TYRE_22
                     else ["10 PR TL, TYRE MAKERS / PHOTOS", "wheels.MAIN_TYRE_CHOICE"]))
    P_leg = v.pt(*(c + L + u_leg * 0.09 + np.array([-u_leg[1], u_leg[0]]) * -G.MAIN_LEG_R[1]))
    leader_to(ds, P_leg, (P_leg[0] + 22.0, Ytop - 20.0), "TRAILING ARM + LEG (INBOARD, ADJACENT)", size=2.3,
              dot=False, weight=500)
    view_title(ds, MAIN_X["side"], GY_M + 32.0, "MAIN WHEEL - SIDE VIEW",
               f"PORT UNIT SEEN FROM PORT (OUTBOARD FACE) · 1:{SC}", size=4.2)
    return v


def rim_parts(asm):
    return WH.rim_half(asm, +1), WH.rim_half(asm, -1)


def draw_bearings(ds, v, asm):
    for s0, s1, r0, r1 in WH.bearing_boxes(asm):
        P = v(rect(s0, s1, r0, r1))
        ds.cv.path([tuple(q) for q in P], W_FINE, closed=True, fill=PAPER)
        ds.cv.line(tuple(P[0]), tuple(P[2]), W_THIN)
        ds.cv.line(tuple(P[1]), tuple(P[3]), W_THIN)


def draw_tie_bolt(ds, v, asm):
    tb = WH.tie_bolt_section(asm)
    r, d, af, h, wt = tb["r"], tb["d"], tb["af"], tb["h"], tb["web"]
    ds.cv.path(v.pts(rect(-wt, wt, r - d / 2, r + d / 2)), W_FINE, closed=True, fill=PAPER)
    ds.cv.path(v.pts(rect(-wt - h, -wt, r - af / 2, r + af / 2)), W_FINE, closed=True, fill=PAPER)     # head
    ds.cv.path(v.pts(rect(wt, wt + h, r - af / 2, r + af / 2)), W_FINE, closed=True, fill=PAPER)       # nut
    ds.cv.line(v.pt(-wt - h - 0.004, r), v.pt(wt + h + 0.004, r), W_THIN, CHAIN)


def tyre_section_draw(ds, v, asm, R=None, fill=TYRE_FILL, w=W_OBJ, bead=True, box=None):
    S_ = WH.tyre_section(asm, R)
    if box is None:
        ds.cv.path(v.pts(S_), w, closed=True, fill=fill)
    else:
        clipped_part(ds, v, S_, box, None, fill=fill, w=w)
    if bead:
        pts, sz = WH.bead_bundles(asm)
        for p in pts:
            X, Y = v.pt(*p)
            h = sz / 2 * v.k
            ds.cv.path([(X - h, Y - h), (X + h, Y - h), (X + h, Y + h), (X - h, Y + h)], 0.0, closed=True, fill=INK,
                       stroke=False)


def tyre_headon_loaded(ds, v, asm, w=W_OBJ):
    """Lower half of a half section: the loaded tyre seen head-on (silhouette + groove lines), r measured DOWN."""
    H = WH.loaded_headon_half(asm)
    for sg in (-1, 1):
        ds.cv.path(v.pts(np.c_[sg * H[:, 0], -H[:, 1]]), w)
    t = asm["tyre"]
    for g in t["grooves"]:
        for e in (g - t["groove_w"] / 2, g + t["groove_w"] / 2):
            rd = WH.loaded_crown_r(asm, e)
            for sg in (-1, 1):
                ds.cv.line(v.pt(sg * e, 0.0), v.pt(sg * e, -rd), W_FINE)


def main_hub_section(ds, v, asm, detail=False):
    """Upper half, in section through the axle: rim halves, tie bolt, brake (torque plate, torque tube, housing with
    the top lobe's piston, disc stack), axle with the threaded end, nut and hub cap, bearings, hub fairing, valve."""
    rim, fa, br, axl = asm["rim"], asm["fairing"], asm["brake"], asm["axle"]
    Po, Pi = rim_parts(asm)
    step = 1.4 if detail else 1.1
    section_part(ds, v, Po, 45.0, step)
    section_part(ds, v, Pi, -45.0, step)
    draw_tie_bolt(ds, v, asm)
    tp = br["torque_plate"]
    hs0, hs1 = br["housing_s"]
    tt0, tt1 = br["torque_tube_r"]
    st = WH.brake_stack(asm)
    s_end = st[-1][2]
    section_part(ds, v, rect(tp[0], tp[1], tp[2], tp[3]), 45.0, step)
    section_part(ds, v, np.array([[hs1, tt0], [s_end, tt0], [s_end, tt1], [hs1, tt1]]), 45.0, step)
    top = br["lobe_c"] + br["lobe_R"]
    pr0, pr1 = br["lobe_c"] - br["piston_d"] / 2, br["lobe_c"] + br["piston_d"] / 2
    pb = hs0 + 0.006
    housing = np.array([[hs0, tt0], [hs1, tt0], [hs1, pr0 - 0.001], [pb, pr0 - 0.001], [pb, pr1 + 0.001],
                        [hs1, pr1 + 0.001], [hs1, top], [hs0, top]])
    section_part(ds, v, housing, 45.0, step)
    section_part(ds, v, rect(pb + 0.001, hs1, pr0, pr1), -45.0, 0.8 if not detail else 1.0)          # piston
    fit = br["fitting_d"]
    ds.cv.path(v.pts(rect(0.5 * (hs0 + hs1) - fit / 2, 0.5 * (hs0 + hs1) + fit / 2, top, top + 0.008)), W_FINE,
               closed=True, fill=PAPER)
    fills = dict(rotor=ROTOR_FILL, stator=PLATE_FILL, pressure_plate=PLATE_FILL, back_plate=PLATE_FILL,
                 lining=LINING_FILL)
    for kind, a, b, r0, r1 in st:
        ds.cv.path(v.pts(rect(a, b, r0, r1)), W_THIN, closed=True, fill=fills[kind])
    # axle (not sectioned: a solid shaft on the axis), open bore hidden, threaded end, nut, hub cap; bearings
    ar, tr = axl["r"], axl["thread_r"]
    bs0, bs1 = axl["boss_s"]
    ns0, ns1 = axl["nut_s"]
    ax_out = np.array([[bs0, 0.0], [bs0, ar], [rim["hub_s"][1], ar], [rim["hub_s"][1], tr], [ns1 + 0.004, tr],
                       [ns1 + 0.004, 0.0]])
    ds.cv.path(v.pts(ax_out), W_OBJ, fill=PAPER, closed=False)
    ds.cv.path(v.pts([[bs0, axl["bore_r"]], [-0.02, axl["bore_r"]]]), W_FINE, HID)
    ds.cv.path(v.pts(rect(ns0, ns1, tr, axl["nut_af"] / 2)), W_FINE, closed=True, fill=PAPER)
    cap = np.array([[rim["hub_s"][1], rim["hub_r"]], [rim["hub_s"][1], axl["cap_r"]], [axl["cap_s"], axl["cap_r"]],
                    [axl["cap_s"], 0.0]])
    ds.cv.path(v.pts(cap), W_FINE)
    draw_bearings(ds, v, asm)
    # trailing-arm axle boss: adjacent part (phantom), with the open bore
    ds.cv.path(v.pts(rect(bs0, bs1, axl["bore_r"], axl["boss_r"])), W_FINE, PHANTOM, closed=True)
    Pf, s0, s1 = WH.fairing_section(asm)
    ds.cv.path(v.pts(Pf), max(fa["t"] * v.k, 0.5))                              # hub fairing (thin section)
    vr, vs = rim["valve_r"], rim["valve_s"]
    ds.cv.path(v.pts([[rim["web_t"], vr], [vs, vr]]), 0.5)
    return Pf, s0, s1


def draw_main_front(ds):
    """FRONT view of the port main wheel seen from ahead (outboard = right), upper half in section A-A through the
    axle, lower half the loaded tyre head-on on the ground."""
    ax, az = main_axle()
    v = ds.add_view(sec_view("main_front", (MAIN_X["front"], GY_M - az * K), SC, box=(-0.20, -0.30, 0.16, 0.37)))
    asm, fa, axl = WH.MAIN, WH.MAIN_FAIRING, WH.MAIN_AXLE
    env = WH.envelope("main")
    R, h = env["R"], env["R_loaded"]
    fr = WH.tyre_frame(asm)
    hw = env["W"] / 2
    # ---- lower half: head-on (loaded)
    ground(ds, v, -0.20, 0.16, -az)
    tyre_headon_loaded(ds, v, asm)
    Fp = WH.fairing_plan(asm)
    vis = Fp[Fp[:, 0] >= hw]
    if len(vis) >= 2:
        r_hw = float(np.interp(hw, Fp[:, 0], Fp[:, 1]))
        ds.cv.path(v.pts(np.vstack([[[hw, -r_hw]], np.c_[vis[:, 0], -vis[:, 1]]])), W_OBJ)
    bs0, bs1 = axl["boss_s"]
    ds.cv.path(v.pts(rect(bs0, bs1, -axl["boss_r"], 0.0)), W_FINE, PHANTOM)
    # ---- upper half: section
    tyre_section_draw(ds, v, asm)
    Pf, s0, s1 = main_hub_section(ds, v, asm)
    ds.cv.line(v.pt(-0.195, 0.0), v.pt(0.155, 0.0), W_THIN, CHAIN)
    ds.cv.line(v.pt(0.0, -az - 0.012), v.pt(0.0, R + 0.014), W_THIN, CHAIN)
    detail_circle(ds, v, -0.02, 0.075, 0.105, "H", at=(-0.8, -0.8))
    view_arrow(ds, v.pt(-0.175, 0.30), (1.0, 0.0), "C", length=11.0)
    # ---- dimensions
    yt = v.pt(0.0, R)[1] - 9.0
    ds.sh.dim(v.pt(-hw, fr["rw"]), v.pt(hw, fr["rw"]), yt, fmt(env["W"]), "h", f1=v.pt(-hw, fr["rw"] + 0.006),
              f2=v.pt(hw, fr["rw"] + 0.006))
    t1 = float(fr["T1"][0])
    yb = v.pt(0.0, -az)[1] + 9.0
    if LOADED_MAIN:
        ds.sh.dim(v.pt(-t1, -h), v.pt(t1, -h), yb, fmt(2 * t1), "h")
        ds.text(v.pt(t1, 0)[0] + 5.0, yb + 0.9, "CONTACT WIDTH (TREAD) [E]", 2.1, "label", "start", fill=MUTED,
                tag="dim")
    p_t, p_f = retracted_depths()
    leader(ds, v.pt(s1, -fa["r_face"] * 0.6), f"HUB FAIRING FACE {fmt(WH.fairing_beyond_tyre())} OUTBOARD OF W",
           (12.0, 34.0), lines=[f"RETRACTED: {fmt(p_f, 1)} BELOW THE SKIN (TYRE {fmt(p_t, 1)})"], size=2.3)
    if WH.MAIN_TYRE_ENV["bulge"] > 0:
        Hh = WH.loaded_headon_half(asm)
        ib = int(np.argmax(Hh[:, 0]))
        leader(ds, v.pt(-Hh[ib, 0], -Hh[ib, 1]), f"LOADED SIDEWALL BULGE {fmt(WH.MAIN_TYRE_ENV['bulge'])} [E]",
               (-16.0, 6.0), size=2.3, weight=500)
    leader(ds, v.pt(0.07, R - 0.004), "SPLIT HUB, 2 HALVES, TUBELESS [S]", (40.0, -16.0),
           lines=[f"TYRE {tyre_name(MOD)}, 10 PR, 60 psi"], size=2.2)
    leader(ds, v.pt(axl["boss_s"][0], -axl["boss_r"] * 0.6), "TRAILING-ARM BOSS", (-14.0, 14.0),
           lines=["(ADJACENT, INBOARD)"], size=2.3, dot=False, weight=500)
    view_title(ds, MAIN_X["front"], GY_M + 32.0, "SECTION A-A (HALF)",
               f"FRONT VIEW FROM AHEAD, UPPER HALF CUT THROUGH THE AXLE · 1:{SC}", size=4.2)
    return v


def draw_main_rear(ds):
    """View C: the port main wheel seen from starboard (inboard face): brake housing, trailing arm and shock."""
    ax, az = main_axle()
    v = ds.add_view(stbd_view("main_rear", (MAIN_X["rear"], GY_M - az * K), SC, (ax, az),
                              box=(ax - 0.37, -0.06, ax + 0.37, az + 0.37)))
    asm, rim, br, axl = WH.MAIN, WH.MAIN_RIM, WH.MAIN_BRAKE, WH.MAIN_AXLE
    env = WH.envelope("main")
    R = env["R"]
    fr = WH.tyre_frame(asm)
    c = np.array([ax, az])
    C = np.array(v.pt(ax, az))
    k = v.k
    ground(ds, v, ax - 0.37, ax + 0.37, 0.0)
    ds.cv.path(v.pts(WH.loaded_side_outline("main") + c), W_OBJ, closed=True)
    wheel_circle(ds, v, c, float(fr["B"][1]))                                   # tyre leaves the inboard flange
    wheel_circle(ds, v, c, rim["bead_r"] - rim["barrel_t"], W_FINE)             # barrel inner edge
    wheel_circle(ds, v, c, br["rotor_r"][1], W_THIN)                            # rotor rim behind the housing
    for dx, dz in WH.clock_points(rim["fusible_n"], rim["fusible_r"], 30.0):     # fusible plugs, hidden
        X, Y = v.pt(ax + dx, az + dz)
        ds.cv.circle(X, Y, 0.004 * k, w=W_THIN)
    lob = WH.brake_lobe_outline(asm) + c
    ds.cv.path(v.pts(lob), W_OBJ, closed=True, fill=PAPER)
    k6 = int(br["lobes"])
    for i, (dx, dz) in enumerate(WH.clock_points(k6, br["lobe_c"], br["lobe_th"])):
        X, Y = v.pt(ax + dx, az + dz)
        ds.cv.circle(X, Y, br["piston_d"] / 2 * k, w=W_THIN)
        if i == 0:                                                              # inlet fitting on the top lobe
            q = WH.hexagon((ax + dx, az + dz + br["lobe_R"] + 0.004), br["fitting_d"], 0.0)
            ds.cv.path(v.pts(q), W_FINE, closed=True, fill=PAPER)
    for dx, dz in WH.clock_points(int(br["retractors"]), 0.058, br["lobe_th"] + 30.0):
        X, Y = v.pt(ax + dx, az + dz)
        ds.cv.circle(X, Y, 0.005 * k, w=W_FINE)
    wheel_circle(ds, v, c, br["lobe_c"], W_THIN, CHAIN)
    # adjacent parts (nearest the viewer): trailing arm bar + boss with the open bore, yoke, leg, shock strut
    L, arm, u_leg = arm_pts()
    ds.cv.path(v.pts(arm + c), W_FINE, PHANTOM, closed=True, fill=None)
    wheel_circle(ds, v, c + L, ARM["yoke_r"], W_FINE, PHANTOM)
    ds.cv.path(v.pts(band(L, L + u_leg * 0.20, G.MAIN_LEG_R[1])[[1, 0, 3, 2]] + c), W_FINE, PHANTOM)
    s_top, s_bot = np.array(G.MAIN_SHOCK[0]) - c, np.array(G.MAIN_SHOCK[1]) - c
    ds.cv.path(v.pts(band(s_bot, s_bot + (s_top - s_bot) * 0.45, 0.027)[[1, 0, 3, 2]] + c), W_FINE, PHANTOM)
    wheel_circle(ds, v, c + s_bot, 0.030, W_FINE, PHANTOM)
    wheel_circle(ds, v, c, axl["boss_r"], W_FINE, PHANTOM, fill=PAPER)
    wheel_circle(ds, v, c, axl["bore_r"], W_OBJ)
    centre_cross(ds, v, ax, az, R + 0.01, R + 0.01)
    # ---- call-outs, outside the tyre: left column (anchor end) and right column
    xl, xr = C[0] - R * k - 10.0, C[0] + R * k + 10.0
    rr = br["lobe_c"] + br["lobe_R"]
    th = math.radians(br["lobe_th"] - 60.0)                     # the upper aft lobe: left, seen from starboard
    leader_to(ds, v.pt(ax + rr * math.cos(th), az + rr * math.sin(th)), (xl, C[1] - 72.0),
              f"6-LOBE BRAKE HOUSING Ø{fmt(2 * rr)} [M]",
              lines=[f"6 PISTONS Ø{fmt(br['piston_d'])} ON PCD {fmt(2 * br['lobe_c'])} [S / E]"])
    fp = WH.clock_points(rim["fusible_n"], rim["fusible_r"], 30.0)[2]
    leader_to(ds, v.pt(ax + fp[0], az + fp[1]), (xl, C[1] + 72.0), "3 FUSIBLE PLUGS [S] (HIDDEN)", weight=500)
    leader_to(ds, v.pt(ax + axl["bore_r"] * 0.7, az - axl["bore_r"] * 0.7), (xl, C[1] + 40.0),
              f"OPEN AXLE BORE Ø{fmt(2 * axl['bore_r'])}", lines=[f"ARM BOSS Ø{fmt(2 * axl['boss_r'])} [M], ADJACENT"])
    top = v.pt(ax, az + rr + 0.008)
    leader_to(ds, top, (xr, C[1] - 96.0), "INLET FITTING [E]", lines=["BRAKE LINE UP THE ARM"])
    leader_to(ds, v.pt(ax + L[0] * 0.62, az + L[1] * 0.62 - ARM["depth"]), (xr, C[1] - 30.0), "TRAILING ARM,",
              lines=["SHOCK, LEG (ADJACENT)"], dot=False, weight=500)
    thr = math.radians(br["lobe_th"] + 30.0 + 120.0)
    leader_to(ds, v.pt(ax + 0.058 * math.cos(thr), az + 0.058 * math.sin(thr)), (xr, C[1] + 50.0),
              "3 RETRACTORS [S]")
    view_title(ds, MAIN_X["rear"], GY_M + 32.0, "VIEW C - MAIN WHEEL INBOARD FACE",
               f"SEEN FROM STARBOARD (BRAKE SIDE), REAR VIEW · 1:{SC}", size=4.2)
    return v


def to_xy(P, ax, ay):
    """Local (dx, s) -> model (x, y) of a port-side unit (s + to port = -y)."""
    P = np.asarray(P, float)
    return np.c_[ax + P[:, 0], ay - P[:, 1]]


def tyre_plan_outline(asm, bulge=None):
    """Closed plan outline (dx, s) of the tyre seen from above: the crown profile at both ends, the side lines at
    s = +-W/2; the loaded bulge about the contact shows on the inboard side (s < 0) only -- outboard it lies under
    the main hub fairing (4-6 mm bulge within the fairing's +-126 mm, < 0.6 mm beyond)."""
    fr = WH.tyre_frame(asm)
    Hf = WH.tyre_plan_half(asm)                                            # (s, r) crown -> max width
    right = np.vstack([np.c_[Hf[::-1, 1], -Hf[::-1, 0]], np.c_[Hf[1:, 1], Hf[1:, 0]]])   # s: -hw -> +hw
    rw, hw = fr["rw"], fr["hw"]
    xs = np.linspace(rw, -rw, 121)
    sb = np.full_like(xs, hw)
    if bulge is not None:
        sb = np.maximum(sb, np.interp(xs, bulge[:, 0], bulge[:, 1], left=hw, right=hw))
    top = np.c_[xs, np.full_like(xs, hw)]                                  # s = +hw side (port), dx: rw -> -rw
    bot = np.c_[xs[::-1], -sb[::-1]]                                       # s = -hw side (inboard), with the bulge
    left = right[::-1] * [-1, 1]
    return np.vstack([right, top[1:-1], left, bot[1:-1]])


def draw_main_top(ds):
    """TOP view of the port main wheel from above (below the side view, first angle): tyre plan with the grooves,
    the hub fairing outboard, hidden rim flanges and brake housing, trailing arm / yoke / leg adjacent."""
    ax, az = main_axle()
    ay = PORT_Y
    v = ds.add_view(plan_view("main_top", (MAIN_X["side"], TOP_M), SC, model_origin=(ax, ay),
                              box=(ax - 0.37, ay - 0.16, ax + 0.37, ay + 0.20)))
    asm, rim, fa, br, axl = WH.MAIN, WH.MAIN_RIM, WH.MAIN_FAIRING, WH.MAIN_BRAKE, WH.MAIN_AXLE
    env = WH.envelope("main")
    R = env["R"]
    fr = WH.tyre_frame(asm)
    hw = fr["hw"]
    t = asm["tyre"]

    def P_(Q):
        return v.pts(to_xy(Q, ax, ay))

    # adjacent parts (phantom): arm bar, boss, yoke at the link pivot, leg
    L, _, u_leg = arm_pts()
    ds.cv.path(P_(np.array([[0.0, ARM["s"] - ARM["t"]], [L[0], ARM["s"] - ARM["t"]], [L[0], ARM["s"] + ARM["t"]],
                            [0.0, ARM["s"] + ARM["t"]]])), W_FINE, PHANTOM, closed=True)
    bs0, bs1 = axl["boss_s"]
    ds.cv.path(P_(np.array([[-axl["boss_r"], bs0], [axl["boss_r"], bs0], [axl["boss_r"], bs1],
                            [-axl["boss_r"], bs1]])), W_FINE, PHANTOM, closed=True)
    ds.cv.path(P_(np.array([[L[0] - ARM["yoke_r"], ARM["yoke"][0]], [L[0] + ARM["yoke_r"], ARM["yoke"][0]],
                            [L[0] + ARM["yoke_r"], ARM["yoke"][1]], [L[0] - ARM["yoke_r"], ARM["yoke"][1]]])),
               W_FINE, PHANTOM, closed=True)
    lr = G.MAIN_LEG_R[1]
    x_end = -0.37
    ds.cv.path(P_(np.array([[x_end, -lr], [L[0], -lr], [L[0], lr], [x_end, lr]])), W_FINE, PHANTOM)
    # hidden: rim flange outer faces, brake housing (inside the tyre, seen from above)
    rf = rim["bead_r"] + rim["flange_h"]
    for sg in (-1, 1):
        sf = sg * (rim["flange_s"] + rim["flange_t"])
        ds.cv.path(P_(np.array([[-rf, sf], [rf, sf]])), W_FINE, HID)
    rr = br["lobe_c"] + br["lobe_R"]
    hs0, hs1 = br["housing_s"]
    ds.cv.path(P_(np.array([[-rr, hs0], [rr, hs0], [rr, hs1], [-rr, hs1]])), W_FINE, HID, closed=True)
    # tyre plan (with the loaded bulge about the contact), grooves; hub fairing outboard of W/2
    out = tyre_plan_outline(asm, WH.plan_bulge("main"))
    ds.cv.path(P_(out), W_OBJ, closed=True)
    for g in t["grooves"]:
        for e in (g - t["groove_w"] / 2, g + t["groove_w"] / 2):
            re_ = float(WH.crown_r(fr, e))
            for sg in (-1, 1):
                ds.cv.path(P_(np.array([[-re_, sg * e], [re_, sg * e]])), W_FINE)
    Fp = WH.fairing_plan(asm)
    vis = Fp[Fp[:, 0] > hw]
    r_hw = float(np.interp(hw, Fp[:, 0], Fp[:, 1]))
    fp = np.vstack([[[r_hw, hw]], np.c_[vis[:, 1], vis[:, 0]]])
    fp = np.vstack([fp, (fp * [-1, 1])[::-1]])
    ds.cv.path(P_(fp), W_OBJ)
    # centre lines: wheel mid-plane (along x), axle axis (along y)
    ds.cv.path(P_(np.array([[-R - 0.012, 0.0], [R + 0.012, 0.0]])), W_THIN, CHAIN)
    ds.cv.path(P_(np.array([[0.0, -0.18], [0.0, fa["proud"] + 0.1]])), W_THIN, CHAIN)
    # ---- dimensions / call-outs
    Y1 = v.pt(ax, ay - 0.13)[1]
    yb = Y1 + 6.0
    ds.sh.dim(v.pt(ax - R, ay), v.pt(ax + R, ay), yb, f"Ø{fmt(2 * R)}", "h", f1=v.pt(ax - R, ay - 0.004),
              f2=v.pt(ax + R, ay - 0.004))
    xr = v.pt(ax + R, ay)[0] + 12.0
    ds.sh.dim(v.pt(ax + fr["rw"], ay + hw), v.pt(ax + fr["rw"], ay - hw), xr, fmt(env["W"]), "v",
              f1=v.pt(ax + fr["rw"] + 0.004, ay + hw), f2=v.pt(ax + fr["rw"] + 0.004, ay - hw))
    Pf, s0, s1 = WH.fairing_section(asm)
    s_face = s1 + fa["t"] / 2
    ds.sh.dim(v.pt(ax, ay - hw), v.pt(ax, ay - s_face), xr + 11.0, fmt(s_face - hw), "v",
              f1=v.pt(ax + fr["rw"] + 0.004, ay - hw), f2=v.pt(ax + fa["r_face"], ay - s_face), text_side="after")
    leader(ds, v.pt(ax - 0.06, ay - s_face), "HUB FAIRING (OUTBOARD)", (-30.0, 13.0), size=2.2)
    g = max(t["grooves"])
    Pg = v.pt(ax + 0.20, ay - g)
    leader_to(ds, Pg, (v.pt(ax + R, 0)[0] + 30.0, Pg[1] + 4.0), "4 GROOVES IN 2 PAIRS [M]", lines=["CENTRES +-30, +-56"])
    if WH.MAIN_TYRE_ENV["bulge"] > 0:
        leader_to(ds, v.pt(ax + 0.10, ay + hw + WH.MAIN_TYRE_ENV["bulge"] * 0.55), (v.pt(ax + R, 0)[0] + 30.0,
                  v.pt(0, ay + hw)[1] - 26.0), "LOADED SIDEWALL BULGE [E]", lines=["(UNDER THE FAIRING OUTBOARD)"],
                  weight=500)
    leader_to(ds, v.pt(ax + rr * 0.8, ay - hs0), (v.pt(ax + R, 0)[0] + 30.0, v.pt(0, ay + hw)[1] - 10.0),
              "BRAKE HOUSING, RIM FLANGES (HIDDEN)", weight=500)
    leader(ds, v.pt(ax + L[0] * 0.5, ay - ARM["s"] + ARM["t"]), "TRAILING ARM, YOKE, LEG (ADJACENT)", (-6.0, -12.0),
           size=2.2, dot=False, weight=500)
    Xl = v.pt(ax - 0.37, ay)[0] - 3.0
    ds.text(Xl, v.pt(ax, ay + 0.10)[1], "INBOARD (STBD)", 2.1, "label", "end", fill=MUTED, tag="lbl")
    ds.text(Xl, v.pt(ax, ay - 0.10)[1], "OUTBOARD (PORT)", 2.1, "label", "end", fill=MUTED, tag="lbl")
    view_title(ds, MAIN_X["side"], v.pt(ax, ay - 0.13)[1] + 24.0, "MAIN WHEEL - TOP VIEW",
               f"SEEN FROM ABOVE, STARBOARD UP · 1:{SC}", size=4.2)
    return v


def draw_main_hub_detail(ds):
    """DETAIL H (1:2): the main hub in section -- rim halves, tie bolt, brake stack, axle, bearings, fairing."""
    v = ds.add_view(sec_view("main_hub_detail", DET_H0, 2, box=(-0.18, 0.0, 0.135, 0.165)))
    asm, rim, fa, br, axl = WH.MAIN, WH.MAIN_RIM, WH.MAIN_FAIRING, WH.MAIN_BRAKE, WH.MAIN_AXLE
    box = (-0.185, 0.0, 0.14, 0.160)
    tyre_section_draw(ds, v, asm, box=(-0.2, 0.0, 0.2, 0.160))
    Pf, s0, s1 = main_hub_section(ds, v, asm, detail=True)
    ds.cv.line(v.pt(-0.185, 0.0), v.pt(0.14, 0.0), W_THIN, CHAIN)
    ds.cv.line(v.pt(0.0, -0.006), v.pt(0.0, 0.166), W_THIN, CHAIN)
    del box
    st = WH.brake_stack(asm)
    # ---- dimensions
    fs, ft = rim["flange_s"], rim["flange_t"]
    rf = rim["bead_r"] + rim["flange_h"]
    yt = v.pt(0, 0.165)[1] - 4.0
    ds.sh.dim(v.pt(-fs, rf), v.pt(fs, rf), yt, f"{fmt(2 * fs)}", "h", f1=v.pt(-fs, rim["bead_r"] + 0.004),
              f2=v.pt(fs, rim["bead_r"] + 0.004))
    xr = v.pt(0.14, 0)[0] + 6.0
    ds.sh.dim(v.pt(0.14, rf), v.pt(0.14, 0.0), xr, f"R {fmt(rf, 1)}", "v", f1=v.pt(fs + ft, rf), f2=v.pt(0.135, 0.0))
    ds.sh.dim(v.pt(0.14, rim["bead_r"]), v.pt(0.14, 0.0), xr + 9.0, f"R {fmt(rim['bead_r'], 1)}", "v",
              f1=v.pt(fs - 0.004, rim["bead_r"]), f2=v.pt(0.135, 0.0))
    yb = v.pt(0, 0.0)[1] + 7.0
    ds.sh.dim(v.pt(s0, fa["r_face"]), v.pt(s1, fa["r_face"]), yb, fmt(fa["proud"]), "h",
              f1=v.pt(s0, 0.004), f2=v.pt(s1, 0.004), text_side="after")
    # ---- call-outs: brake on the left, hub / fairing on the right, each column ordered by height (no crossings)
    hs0, hs1 = br["housing_s"]
    top = br["lobe_c"] + br["lobe_R"]
    tb = WH.tie_bolt_section(asm)
    left = [
        ((0.5 * (hs0 + hs1), top + 0.008), "INLET FITTING [E]", None),
        ((st[2][1] + 0.003, st[2][4] - 0.003), f"{int(br['rotors'])} ROTORS, KEYED TO THE WHEEL [E]",
         [f"Ø{fmt(2 * br['rotor_r'][1])} / {fmt(2 * br['rotor_r'][0])} x {fmt(br['rotor_t'])}"]),
        ((hs0 + 0.003, br["lobe_c"]), "HOUSING, 6 PISTONS Ø30 [S / E]", ["3 RETRACTORS, STEEL FRICTION [S]"]),
        ((st[4][1] + 0.002, st[4][3] + 0.006), f"{int(br['stators'])} STATORS, PRESSURE + BACK PLATE",
         ["RIVETED LININGS [S kit 2-1674-1]"]),
        ((br["torque_plate"][0] + 0.002, br["torque_plate"][3] - 0.004), "TORQUE PLATE ON THE AXLE FLANGE [E]", None),
        ((st[-1][1] - 0.001, br["torque_tube_r"][0] + 0.002), "TORQUE TUBE (FIXED) [E]", None),
        ((axl["boss_s"][0] + 0.006, axl["bore_r"] + 0.012), "ARM BOSS (ADJACENT)", ["OPEN AXLE BORE Ø45 [M]"]),
    ]
    xl = v.pt(-0.185, 0)[0] - 14.0
    for i, (p, txt, lines) in enumerate(left):
        leader_to(ds, v.pt(*p), (xl, DET_H0[1] - 84.0 + 12.5 * i), txt, lines)
    right = [
        ((fs + ft * 0.5, rf - 0.001), f"FLANGE Ø{fmt(2 * rf, 1)} [S TRA]", None),
        ((0.5 * (s0 + s1) + 0.006, fa["r_face"] + 0.008), "HUB FAIRING t 1.6 [M / E]", ["LEG-DOOR COLOUR"]),
        ((0.004, rim["tie_r"] + tb["af"] / 2), f"TIE BOLT, {rim['tie_n']} ON PCD {fmt(2 * rim['tie_r'])} [E]",
         ["HIDDEN BY FAIRING / BRAKE"]),
        ((rim["valve_s"] - 0.004, rim["valve_r"]), "VALVE UNDER THE ACCESS HOLE", None),
        ((rim["hub_s"][1] - 0.01, rim["hub_bore"] - 0.004), "TAPER ROLLER BEARINGS [E]", None),
        ((axl["nut_s"][1] - 0.002, axl["nut_af"] / 2), "AXLE NUT, HUB CAP [E]", None),
    ]
    xr2 = v.pt(0.14, 0)[0] + 26.0
    for i, (p, txt, lines) in enumerate(right):
        leader_to(ds, v.pt(*p), (xr2, DET_H0[1] - 84.0 + 12.5 * i), txt, lines)
    view_title(ds, DET_H0[0] - 10.0, DET_H0[1] + 22.0, "DETAIL H - MAIN HUB AND BRAKE",
               "HALF SECTION A-A, SCALE 1:2", size=4.0)
    return v


# ============================================================================================ nose wheel
NOSE_ARM_W = (0.046, 0.034)     # fork plate half-width fore-aft at the crown / at the axle (gear.NOSE_FORK_PLATE)


def nose_fork_side():
    """Port fork arm in the side view (dx, dz about the axle): a plate from the crown casting to the axle boss."""
    ax, az = float(G.NOSE_AXLE[0]), float(G.NOSE_AXLE[2])
    cr = np.array([G.NOSE_FORK[0] - ax, G.NOSE_FORK[2] - az])
    d = cr / np.linalg.norm(cr)
    n = np.array([-d[1], d[0]])
    return cr, np.array([n * NOSE_ARM_W[1], cr + n * NOSE_ARM_W[0], cr - n * NOSE_ARM_W[0], -n * NOSE_ARM_W[1]])


def draw_nose_side(ds):
    A = G.NOSE_AXLE
    ax, az = float(A[0]), float(A[2])
    v = ds.add_view(side_view("nose_side", (NOSE_X["side"], GY_N - az * K), SC, model_origin=(ax, az),
                              box=(ax - 0.30, -0.03, ax + 0.30, az + 0.40)))
    asm, rim, axl = WH.NOSE, WH.NOSE_RIM, WH.NOSE_AXLE
    env = WH.envelope("nose")
    R = env["R"]
    fr = WH.tyre_frame(asm)
    c = np.array([ax, az])
    C = np.array(v.pt(ax, az))
    k = v.k
    ground(ds, v, ax - 0.30, ax + 0.30, 0.0, "GROUND (STATIC)", at="right")
    ds.cv.path(v.pts(WH.loaded_side_outline("nose") + c), W_OBJ, closed=True)
    wheel_circle(ds, v, c, float(fr["B"][1]))                                   # tyre / flange line
    wheel_circle(ds, v, c, rim["bead_r"] - rim["barrel_t"], W_FINE)             # flange ring inner edge
    wheel_circle(ds, v, c, rim["hub_r"], W_OBJ)                                 # raised hub boss
    wheel_circle(ds, v, c, rim["tie_r"], W_THIN, CHAIN)
    for dx, dz in WH.clock_points(rim["tie_n"], rim["tie_r"], rim["tie_th"]):
        ds.cv.path(v.pts(WH.hexagon((ax + dx, az + dz), 0.013)), W_FINE, closed=True)
    th = math.radians(rim["valve_th"])
    vc = (ax + rim["valve_r"] * math.cos(th), az + rim["valve_r"] * math.sin(th))
    wheel_circle(ds, v, vc, 0.0045, W_FINE)
    # port fork arm (adjacent part, nearest the viewer), crown casting, piston; axle nut + lock plate on the arm
    cr, arm = nose_fork_side()
    ds.cv.path(v.pts(arm + c), W_FINE, PHANTOM, closed=True)
    ds.cv.path(v.pts(np.array([[cr[0] - 0.050, cr[1] - 0.022], [cr[0] + 0.050, cr[1] - 0.022],
                               [cr[0] + 0.050, cr[1] + 0.028], [cr[0] - 0.050, cr[1] + 0.028]]) + c), W_FINE, PHANTOM,
               closed=True)
    ds.cv.path(v.pts(np.array([[cr[0] - 0.036, cr[1] + 0.028], [cr[0] - 0.036, 0.40], [cr[0] + 0.036, 0.40],
                               [cr[0] + 0.036, cr[1] + 0.028]]) + c), W_FINE, PHANTOM)
    wheel_circle(ds, v, c, axl["boss_r"], W_FINE, PHANTOM)
    ud = cr / np.linalg.norm(cr)                                  # tear-drop lock plate: along the arm, tip up
    ad = math.degrees(math.atan2(ud[1], ud[0]))
    nd = np.array([-ud[1], ud[0]])
    lp_ = np.vstack([circle_pts((0.0, 0.0), axl["nut_af"] / 2 + 0.004, 25, ad + 90.0, ad + 270.0),
                     [ud * axl["lock_plate"] - nd * 0.008, ud * axl["lock_plate"] + nd * 0.008]])
    ds.cv.path(v.pts(lp_ + c), W_FINE, closed=True, fill=PAPER)
    ds.cv.path(v.pts(WH.hexagon(c, axl["nut_af"], 0.0)), W_OBJ, closed=True, fill=PAPER)
    wheel_circle(ds, v, c, axl["thread_r"] * 0.45, W_FINE)
    centre_cross(ds, v, ax, az, R + 0.01, R + 0.01)
    half_plane(ds, v, (ax, az), (ax, az + R + 0.006), "B", (1.0, 0.0))
    # ---- dimensions (left): axle WL, overall loaded height = OD
    Yg = v.pt(ax, 0.0)[1]
    xd = C[0] - R * k - 10.0
    ds.sh.dim((xd, C[1]), (xd, Yg), xd, f"{fmt(env['R_loaded'])}", "v", f1=(C[0] - 3.0, C[1]), f2=(xd, Yg))
    ds.sh.dim((xd - 11.0, C[1] - R * k), (xd - 11.0, Yg), xd - 11.0, f"Ø{fmt(2 * R)}", "v",
              f1=(C[0] - 2.0, C[1] - R * k), f2=(xd - 11.0, Yg))
    ds.text(xd - 17.0, C[1] - 1.8, "AXLE WL", 2.1, "label", "end", fill=MUTED, tag="dim")
    # ---- call-outs (right), ordered by height
    rf = rim["bead_r"] + rim["flange_h"]
    b0 = WH.clock_points(rim["tie_n"], rim["tie_r"], rim["tie_th"])[0]
    xt = C[0] + R * k + 18.0
    ca = [
        (v.pt(ax + cr[0] * 0.55 + NOSE_ARM_W[0] * 0.9, az + cr[1] * 0.55), "PORT FORK ARM (ADJACENT)",
         ["STARBOARD ARM BEHIND (MIRROR)"], dict(dot=False, weight=500)),
        (v.pt(ax + rf * math.cos(math.radians(40.0)), az + rf * math.sin(math.radians(40.0))),
         f"FLANGE Ø{fmt(2 * rf)} [S TRA]", ["WHEEL GLOSS WHITE, OPEN FACES [M]"], {}),
        (v.pt(*vc), "VALVE STEM [M]", [f"R {fmt(rim['valve_r'])}, PORT FACE"], {}),
        (v.pt(ax + b0[0] + 0.006, az + b0[1]), f"{rim['tie_n']} TIE BOLTS ON PCD {fmt(2 * rim['tie_r'])}",
         ["3 SEEN PER FACE [M], 4TH [E]"], {}),
        (v.pt(ax + axl["nut_af"] / 2 * 0.9, az - 0.006), f"HEX AXLE NUT AF {fmt(axl['nut_af'])}",
         ["TEAR-DROP LOCK PLATE [M]"], {}),
    ]
    for i, (P, txt, lines, kw) in enumerate(ca):
        leader_to(ds, P, (xt, C[1] - 58.0 + 15.0 * i), txt, lines, **kw)
    view_title(ds, NOSE_X["side"], GY_N + 32.0, "NOSE WHEEL - SIDE VIEW", f"SEEN FROM PORT · 1:{SC}", size=4.2)
    return v


def nose_yoke(asm):
    """Front-view outline of the two-arm fork yoke (s, r about the axle): inner and outer contours."""
    axl = asm["axle"]
    R = WH.envelope("nose")["R"]
    fi, fo = axl["fork_in"], axl["fork_out"]
    top_in = R + axl["arch"]
    ri, ro = 0.020, 0.035

    def contour(sf, top, rc):
        q = [(sf, -axl["boss_r"]), (sf, top - rc)] + [
            (sf - rc + rc * math.cos(a), top - rc + rc * math.sin(a)) for a in np.radians(np.linspace(0, 90, 9))[1:]]
        q = np.array(q)
        return np.vstack([mirror(q[::-1]), q])
    return contour(fi, top_in, ri), contour(fo, top_in + 0.048, ro), top_in


def draw_nose_front(ds):
    az = float(G.NOSE_AXLE[2])
    v = ds.add_view(sec_view("nose_front", (NOSE_X["front"], GY_N - az * K), SC, box=(-0.16, -0.24, 0.16, 0.40)))
    asm, rim, axl = WH.NOSE, WH.NOSE_RIM, WH.NOSE_AXLE
    env = WH.envelope("nose")
    R = env["R"]
    fr = WH.tyre_frame(asm)
    ground(ds, v, -0.16, 0.16, -az)
    tyre_headon_loaded(ds, v, asm)
    fi, fo = axl["fork_in"], axl["fork_out"]
    ns0, ns1 = axl["nut_s"]
    for sg in (-1, 1):
        ds.cv.path(v.pts(rect(sg * rim["hub_s"][1], sg * fi, -rim["hub_r"], 0.0)), W_FINE)      # spacer / hub end
        ds.cv.path(v.pts(rect(sg * ns0, sg * ns1, -axl["nut_af"] / 2, 0.0)), W_OBJ)
    yin, yout, top_in = nose_yoke(asm)
    for Y_ in (yin, yout):
        ds.cv.path(v.pts(Y_), W_FINE, PHANTOM)
    for sg in (-1, 1):
        ds.cv.path(v.pts([[sg * fi, -axl["boss_r"]], [sg * fo, -axl["boss_r"]]]), W_FINE, PHANTOM)
    ds.cv.path(v.pts(np.array([[-0.036, 0.40], [-0.036, top_in + 0.048], [0.036, top_in + 0.048], [0.036, 0.40]])),
               W_FINE, PHANTOM)                                                           # piston (adjacent)
    tyre_section_draw(ds, v, asm)
    Pp, Ps = rim_parts(asm)
    section_part(ds, v, Pp, 45.0)
    section_part(ds, v, Ps, -45.0)
    draw_tie_bolt(ds, v, asm)
    ar, tr = axl["r"], axl["thread_r"]
    ax_out = np.array([[-ns1 - 0.004, 0.0], [-ns1 - 0.004, tr], [-fo, tr], [-fo, ar], [fo, ar], [fo, tr],
                       [ns1 + 0.004, tr], [ns1 + 0.004, 0.0]])
    ds.cv.path(v.pts(ax_out), W_OBJ, fill=PAPER)
    for sg in (-1, 1):
        ds.cv.path(v.pts(rect(sg * ns0, sg * ns1, tr, axl["nut_af"] / 2)), W_FINE, closed=True, fill=PAPER)
        ds.cv.path(v.pts(rect(sg * rim["hub_s"][1], sg * fi, ar, rim["hub_r"])), W_FINE, closed=True, fill=PAPER)
    draw_bearings(ds, v, asm)
    ds.cv.line(v.pt(-0.155, 0.0), v.pt(0.155, 0.0), W_THIN, CHAIN)
    ds.cv.line(v.pt(0.0, -az - 0.012), v.pt(0.0, top_in + 0.075), W_THIN, CHAIN)
    hw = env["W"] / 2
    yt = v.pt(0.0, top_in + 0.048)[1] - 7.0
    ds.sh.dim(v.pt(-fi, top_in), v.pt(fi, top_in), yt, fmt(2 * fi), "h")
    ds.sh.dim(v.pt(-fo, top_in), v.pt(fo, top_in), yt - 8.0, fmt(2 * fo), "h", f1=v.pt(-fo, top_in + 0.02),
              f2=v.pt(fo, top_in + 0.02))
    yb = v.pt(0.0, -az)[1] + 9.0
    ds.sh.dim(v.pt(-hw, -fr["rw"]), v.pt(hw, -fr["rw"]), yb, fmt(env["W"]), "h", f1=v.pt(-hw, -fr["rw"]),
              f2=v.pt(hw, -fr["rw"]))
    leader(ds, v.pt(fo - 0.004, top_in + 0.03), "FORK YOKE: TWO ARMS [M]", (22.0, -14.0),
           lines=["ADJACENT; gear.py HAS ONE (STAGE 3)"], size=2.2, color=ACCENT)
    leader(ds, v.pt(0.004, rim["tie_r"]), f"TIE BOLT {rim['tie_n']}x [E]", (44.0, -20.0), size=2.2)
    leader(ds, v.pt(ns1 - 0.004, -axl["nut_af"] / 2), "AXLE NUTS OUTSIDE THE ARMS", (18.0, 20.0), size=2.2)
    leader(ds, v.pt(0.05, R - 0.004), "SPLIT HUB, TUBELESS [S]", (36.0, -44.0), lines=["17.5x6.25-6, 8 PR, 60 psi"],
           size=2.2)
    view_title(ds, NOSE_X["front"], GY_N + 32.0, "SECTION B-B (HALF)",
               f"FRONT VIEW FROM AHEAD, UPPER HALF CUT · 1:{SC}", size=4.2)
    return v


def draw_nose_top(ds):
    A = G.NOSE_AXLE
    ax, ay = float(A[0]), float(A[1])
    v = ds.add_view(plan_view("nose_top", (NOSE_X["side"], TOP_N), SC, model_origin=(ax, ay),
                              box=(ax - 0.30, ay - 0.15, ax + 0.30, ay + 0.15)))
    asm, rim, axl = WH.NOSE, WH.NOSE_RIM, WH.NOSE_AXLE
    env = WH.envelope("nose")
    R = env["R"]
    fr = WH.tyre_frame(asm)
    hw = fr["hw"]
    t = asm["tyre"]

    def P_(Q):
        return v.pts(to_xy(Q, ax, ay))

    rf = rim["bead_r"] + rim["flange_h"]
    for sg in (-1, 1):
        sf = sg * (rim["flange_s"] + rim["flange_t"])
        ds.cv.path(P_(np.array([[-rf, sf], [rf, sf]])), W_FINE, HID)
    ds.cv.path(P_(tyre_plan_outline(asm)), W_OBJ, closed=True)
    for g in t["grooves"]:
        for e in (g - t["groove_w"] / 2, g + t["groove_w"] / 2):
            re_ = float(WH.crown_r(fr, e))
            for sg in (-1, 1):
                ds.cv.path(P_(np.array([[-re_, sg * e], [re_, sg * e]])), W_FINE)
    # adjacent: fork yoke over the tyre (arms + crown), piston; axle nuts and axle ends (ours, visible)
    fi, fo = axl["fork_in"], axl["fork_out"]
    cr, _ = nose_fork_side()
    wa = NOSE_ARM_W[0]
    for sg in (-1, 1):
        ds.cv.path(P_(np.array([[-wa, sg * fi], [wa, sg * fi], [wa, sg * fo], [-wa, sg * fo]]) + [cr[0] * 0.5, 0]),
                   W_FINE, PHANTOM, closed=True)
    ds.cv.path(P_(np.array([[cr[0] - 0.050, -fo], [cr[0] + 0.050, -fo], [cr[0] + 0.050, fo], [cr[0] - 0.050, fo]])),
               W_FINE, PHANTOM, closed=True)
    ds.cv.path(P_(circle_pts((cr[0], 0.0), 0.036, 49)), W_FINE, PHANTOM)
    ns0, ns1 = axl["nut_s"]
    hx = axl["nut_af"] / math.sqrt(3.0)
    for sg in (-1, 1):
        ds.cv.path(P_(np.array([[-hx, sg * ns0], [hx, sg * ns0], [hx, sg * ns1], [-hx, sg * ns1]])), W_OBJ, closed=True)
        ds.cv.path(P_(np.array([[-hx / 2, sg * ns0], [-hx / 2, sg * ns1]])), W_THIN)
        ds.cv.path(P_(np.array([[hx / 2, sg * ns0], [hx / 2, sg * ns1]])), W_THIN)
        ds.cv.path(P_(np.array([[-axl["thread_r"], sg * ns1], [-axl["thread_r"], sg * (ns1 + 0.004)],
                                [axl["thread_r"], sg * (ns1 + 0.004)], [axl["thread_r"], sg * ns1]])), W_FINE)
    ds.cv.path(P_(np.array([[-R - 0.012, 0.0], [R + 0.012, 0.0]])), W_THIN, CHAIN)
    ds.cv.path(P_(np.array([[0.0, -0.15], [0.0, 0.15]])), W_THIN, CHAIN)
    Y1 = v.pt(ax, ay - 0.14)[1]
    ds.sh.dim(v.pt(ax - R, ay), v.pt(ax + R, ay), Y1 + 5.0, f"Ø{fmt(2 * R)}", "h", f1=v.pt(ax - R, ay - 0.004),
              f2=v.pt(ax + R, ay - 0.004))
    xr = v.pt(ax + R, ay)[0] + 10.0
    ds.sh.dim(v.pt(ax + fr["rw"], ay + hw), v.pt(ax + fr["rw"], ay - hw), xr, fmt(env["W"]), "v",
              f1=v.pt(ax + fr["rw"] + 0.004, ay + hw), f2=v.pt(ax + fr["rw"] + 0.004, ay - hw))
    leader(ds, v.pt(ax + 0.16, ay - max(t["grooves"])), "4 GROOVES EVENLY SPACED [M]", (34.0, 20.0), size=2.2)
    leader(ds, v.pt(ax + cr[0] + 0.05, ay + fo - 0.01), "FORK YOKE, PISTON (ADJACENT)", (36.0, -14.0), size=2.2,
           dot=False, weight=500)
    leader(ds, v.pt(ax - hx, ay - ns1 + 0.004), "AXLE NUT", (-40.0, -2.0), size=2.2)
    ds.text(v.pt(ax - 0.30, ay)[0] + 1.0, v.pt(ax, ay + 0.12)[1], "STARBOARD", 2.0, "label", "start", fill=MUTED,
            tag="lbl")
    ds.text(v.pt(ax - 0.30, ay)[0] + 1.0, v.pt(ax, ay - 0.12)[1] + 2.0, "PORT", 2.0, "label", "start", fill=MUTED,
            tag="lbl")
    view_title(ds, NOSE_X["side"], Y1 + 23.0, "NOSE WHEEL - TOP VIEW", f"SEEN FROM ABOVE, STARBOARD UP · 1:{SC}", size=4.2)
    return v


# ============================================================================================ tyre details 1:2
def tra_table(which):
    """The TRA data drawn in the tyre detail: the modelled envelope when it is a TRA size, else the proposed main
    tyre's (8.50-10 Type III)."""
    e = WH.TYRE_ENV[which]
    return e if e["shoulder_d"] is not None else WH.MAIN_TRA


_DEPTHS = {}


def retracted_depths():
    """(tyre, hub fairing) depth (m) below the local wing lower skin with the gear retracted (gear.py kinematics, the
    wheel built from these tables)."""
    if not _DEPTHS:
        _DEPTHS["v"] = (G.main_tyre_protrusion(1), G.main_tyre_protrusion(1, ("paint_white",)))
    return _DEPTHS["v"]


def draw_tra_envelope(ds, v, which):
    """TRA growth / clearance envelope (phantom): the max OD across the crown, chamfered to the max shoulder points
    (marked x) and down the max section width."""
    e = tra_table(which)
    fr = WH.tyre_frame(WH.MAIN if which == "main" else WH.NOSE, None if e is WH.TYRE_ENV[which] else e["R"])
    ro, rs, ss, sw = e["od_max"] / 2, e["shoulder_d"] / 2, e["shoulder_w"] / 2, e["W_max"] / 2
    a = math.degrees(math.asin(0.6 * ss / ro))
    top = circle_pts((0.0, 0.0), ro, 21, 90.0 + a, 90.0 - a)             # left -> right
    right = np.array([[ss, rs], [sw, fr["rw"] + 0.012], [sw, fr["rw"] - 0.03]])
    ds.cv.path(v.pts(np.vstack([mirror(right)[::-1], top, right])), W_FINE, PHANTOM)
    for sg in (-1, 1):
        X, Y = v.pt(sg * ss, rs)
        ds.cv.line((X - 1.2, Y - 1.2), (X + 1.2, Y + 1.2), W_THIN)
        ds.cv.line((X - 1.2, Y + 1.2), (X + 1.2, Y - 1.2), W_THIN)


def draw_tyre_detail(ds, asm, x0, letter):
    """Tyre section at 1:2 (upper half, rim flanges clipped) with the construction, groove pattern, rib widths and
    the TRA growth envelope (phantom)."""
    which = asm["which"]
    env = WH.envelope(which)
    R, W = env["R"], env["W"]
    y0 = DET_TOP[which] + R * 500.0
    v = ds.add_view(sec_view(f"detail_{which}", (x0, y0), 2, box=(-0.14, 0.05, 0.14, 0.34)))
    t, rim = asm["tyre"], asm["rim"]
    fr = WH.tyre_frame(asm)
    kn = WH.key_numbers(asm)
    r_clip = rim["bead_r"] - rim["barrel_t"] - 0.004
    for side, ang in ((1, 45.0), (-1, -45.0)):
        Q = WH.rim_half(asm, side)
        Qk = Q[Q[:, 1] >= r_clip]
        Qc = np.vstack([Qk, [[Qk[-1, 0], r_clip], [Qk[0, 0], r_clip]]])
        section_part(ds, v, Qc, ang, step=1.4)
    draw_tra_envelope(ds, v, which)
    tyre_section_draw(ds, v, asm)
    for key in ("Cc", "Q", "Cu", "Cl"):
        X, Y = v.pt(*fr[key])
        ds.cv.line((X - 1.2, Y), (X + 1.2, Y), W_THIN, color=MUTED)
        ds.cv.line((X, Y - 1.2), (X, Y + 1.2), W_THIN, color=MUTED)
    hw = W / 2
    ds.cv.line(v.pt(-hw - 0.012, fr["rw"]), v.pt(hw + 0.012, fr["rw"]), W_THIN, CHAIN)          # max-width line
    ds.cv.line(v.pt(0.0, r_clip - 0.004), v.pt(0.0, R + 0.012), W_THIN, CHAIN)

    x_dims = v.pt(hw, 0)[0] + 20.0                                           # the H dimension line (below)

    def rad(key, rk, ang, text, off, right=False):
        c = fr[key]
        r = fr[rk]
        p = v.pt(c[0] + r * math.cos(math.radians(ang)), c[1] + r * math.sin(math.radians(ang)))
        if right:                                                            # text beyond the height dimensions
            off = (x_dims + 5.0 - p[0], off[1])
        leader(ds, p, text, off, size=2.2, arrow=True, weight=500)

    gs = sorted(t["grooves"])
    ac = 90.0 - math.degrees(math.asin(min(0.5 * (gs[0] + gs[1]) / fr["Rc"], 1.0)))
    rad("Cc", "Rc", 180.0 - ac, f"CROWN R {fmt(fr['Rc'])}", (-16.0, -6.0) if tra_table(which) is WH.TYRE_ENV[which]
        else (-44.0, 8.0))
    aQ = math.degrees(math.atan2(*(fr["T1"] - fr["Q"])[::-1])) - 20.0
    rad("Q", "Rs", aQ, f"SHOULDER R {fmt(fr['Rs'])}", (22.0, -6.0), right=True)
    rad("Cu", "Ru", 14.0, f"R {fmt(fr['Ru'])} (SOLVED)", (18.0, -1.0), right=True)
    rad("Cl", "Rl", -20.0, f"R {fmt(fr['Rl'])}", (16.0, 4.0), right=True)
    # dimensions: section width at the max-width line, groove centres, rib widths, section height
    ds.sh.dim(v.pt(-hw, fr["rw"]), v.pt(hw, fr["rw"]), v.pt(0, r_clip)[1] + 9.0, f"W {fmt(W)}", "h",
              f1=v.pt(-hw, fr["rw"]), f2=v.pt(hw, fr["rw"]))
    ytop = v.pt(0.0, max(tra_table(which)["od_max"] / 2, R))[1] - 9.0
    ds.sh.dim(v.pt(-gs[0], R), v.pt(gs[0], R), ytop, fmt(2 * gs[0]), "h", f1=v.pt(-gs[0], R - 0.004),
              f2=v.pt(gs[0], R - 0.004))
    ds.sh.dim(v.pt(-gs[1], R), v.pt(gs[1], R), ytop - 8.0, fmt(2 * gs[1]), "h", f1=v.pt(-gs[1], R - 0.004),
              f2=v.pt(gs[1], R - 0.004))
    # rib widths along the crown (between the groove edges, to the shoulder tangent point)
    t1 = float(fr["T1"][0])
    edges = sorted([-t1, t1] + [sg * g + e * t["groove_w"] / 2 for g in gs for sg in (-1, 1) for e in (-1, 1)])
    yr = ytop - 16.0
    X_ = [v.pt(e, 0)[0] for e in edges]
    for i in range(0, len(X_) - 1, 2):
        a, b = X_[i], X_[i + 1]
        ds.cv.line((a, yr), (b, yr), W_THIN)
        for xx in (a, b):
            ds.cv.line((xx, yr - 1.2), (xx, yr + 1.2), W_THIN)
        ds.text(0.5 * (a + b), yr - 1.2, f"{(b - a) / 0.5:.0f}", 2.2, "mono", "middle", tag="dim")
    ds.text(v.pt(-t1, 0)[0] - 2.0, yr + 0.8, "RIBS", 2.0, "label", "end", fill=MUTED, tag="dim")
    xr = v.pt(hw, 0)[0] + 20.0
    ds.sh.dim(v.pt(hw, R), v.pt(hw, rim["bead_r"]), xr, f"H {fmt(kn['H'], 1)}", "v", f1=v.pt(0.004, R),
              f2=v.pt(rim["flange_s"], rim["bead_r"]))
    ds.sh.dim(v.pt(hw, fr["rw"]), v.pt(hw, rim["bead_r"]), xr - 9.0, fmt(fr["rw"] - rim["bead_r"], 1), "v",
              f1=v.pt(hw, fr["rw"]), f2=v.pt(rim["flange_s"] + 0.01, rim["bead_r"]))
    g1 = gs[1]
    rg = float(WH.crown_r(fr, g1))
    leader(ds, v.pt(g1 + t["groove_w"] / 2 - 0.001, rg - t["groove_d"] * 0.5), f"GROOVE {fmt(t['groove_w'])} WIDE",
           (22.0, -12.0), lines=[f"{fmt(t['groove_d'])} DEEP, ROUND FLOOR [M/E]"], size=2.2, weight=500)
    lbl = ("4 GROOVES IN 2 PAIRS [M]" if which == "main" else "4 GROOVES EVENLY SPACED [M]")
    ds.text(x0, yr - 7.0, lbl, 2.4, "label", "middle", weight=600, tag="lbl")
    pts, sz = WH.bead_bundles(asm)
    Pb = v.pt(-pts[1][0] - sz / 2, pts[1][1])
    leader_to(ds, Pb, (v.pt(-hw, 0)[0] - 4.0, Pb[1] - 6.0), "BEAD WIRES", size=2.2, weight=500)
    fl = rim["bead_r"] + rim["flange_h"]
    leader(ds, v.pt(-rim["flange_s"] - rim["flange_t"], fl - 0.006), f"FLANGE Ø{fmt(2 * fl)} [S]", (-14.0, 14.0),
           lines=[f"SEAT Ø{fmt(2 * rim['bead_r'])}, {fmt(2 * rim['flange_s'])} BETWEEN"], size=2.2, weight=500)
    chk = WH.tra_envelope_check(which)
    e = tra_table(which)
    ss = e["shoulder_w"] / 2
    if chk["tra"]:
        l2 = f"MODEL AT {fmt(2 * ss)}: Ø{fmt(2 * chk['r_model'], 1)} (INSIDE)"
        l0 = "TRA MAX ENVELOPE (PHANTOM)"
    else:
        l2 = "PROPOSED MAIN TYRE: OWNER DECISION PENDING"
        l0 = f"{tyre_name(e)} TRA MAX ENVELOPE (PHANTOM)"
    leader(ds, v.pt(-ss, e["shoulder_d"] / 2), l0, (-16.0, -20.0),
           lines=[f"OD {fmt(e['od_max'])}, W {fmt(e['W_max'], 1)}, SHOULDER Ø{fmt(e['shoulder_d'], 1)} AT {fmt(2 * ss)}",
                  l2], size=2.2, color=ACCENT)
    sub = (f"MAIN TYRE {tyre_name(MOD)} (MODELLED), SCALE 1:2" if which == "main"
           else "NOSE TYRE 17.5x6.25-6, SCALE 1:2")
    view_title(ds, x0, v.pt(0, r_clip)[1] + 24.0, f"DETAIL {letter} - TYRE SECTION", sub, size=4.0)
    return v


# ============================================================================================ tables / notes
def draw_tables(ds, x0, y0):
    Mt, Mr, Mf, Mb, Ma = WH.MAIN_TYRE_SEC, WH.MAIN_RIM, WH.MAIN_FAIRING, WH.MAIN_BRAKE, WH.MAIN_AXLE
    Nt, Nr, Na = WH.NOSE_TYRE_SEC, WH.NOSE_RIM, WH.NOSE_AXLE
    Me, Ne = WH.MAIN_TYRE_ENV, WH.NOSE_TYRE_ENV
    km, kn = WH.key_numbers(WH.MAIN), WH.key_numbers(WH.NOSE)
    frm, frn = WH.tyre_frame(WH.MAIN), WH.tyre_frame(WH.NOSE)
    stk = WH.brake_stack(WH.MAIN)
    _, _, am, rbm = WH.loaded_blend("main")
    tra_m = MOD is WH.MAIN_TYRE_850
    rows = [
        ("Tyre (modelled)", str(Me["size"]), "17.5x6.25-6",
         ("P proposed 8.50-10 (MAIN_TYRE_CHOICE); S parts lists" if tra_m else
          "S Jane's / Pilatus dwg (approved); P 8.50-10 proposed")),
        ("Part numbers", "850T06-3 / 025-350-0" if tra_m else "- (not a TRA size)", "175K88B1 / 021-327-0",
         "S Goodyear / Michelin (parts listings)"),
        ("Ply / type / pressure", "10 PR TL, 60 psi", "8 PR TL, 60 psi", "S data book; POH placard, GSG 02527"),
        ("Free OD / section W", f"{fmt(2 * Me['R'])} / {fmt(Me['W'])}", f"{fmt(2 * Ne['R'])} / {fmt(Ne['W'])}",
         "S TRA 627-652 / 208-221; M photos 620-650" if tra_m else "S 22 in / 8.50 in (TRA 8.50-10: 627-652)"),
        ("Axle WL = loaded R / defl.", f"{fmt(Me['R_loaded'])} / {fmt(Me['R'] - Me['R_loaded'], 0 if rbm else 1)}",
         f"{fmt(Ne['R_loaded'])} / {fmt(Ne['R'] - Ne['R_loaded'], 1)}", "G axles kept; M main 270-280"),
        ("Contact patch / blend R", f"{fmt(2 * am)} / {fmt(rbm)}" if rbm is not None else f"{fmt(2 * am)} (chord)",
         "-", "E (free chord 313)" if rbm is not None else "D free circle cut by the ground"),
        ("Section H / aspect", f"{fmt(km['H'], 1)} / {km['aspect']:.2f}", f"{fmt(kn['H'], 1)} / {kn['aspect']:.2f}",
         "D (TRA 0.90 / 0.92)"),
        ("Bead seat / flange dia", f"{fmt(2 * Mr['bead_r'])} / {fmt(2 * km['r_flange'], 1)}",
         f"{fmt(2 * Nr['bead_r'])} / {fmt(2 * kn['r_flange'])}", "S TRA rim 10 / 6 in, flange .81 / .75 in"),
        ("Between flanges / ledge", f"{fmt(2 * Mr['flange_s'], 1)} / {fmt(Mr['ledge'], 1)}",
         f"{fmt(2 * Nr['flange_s'])} / {fmt(Nr['ledge'], 1)}", "S TRA 6.25 / 5.00 in; 1.35 / 0.90 in"),
        ("Crown R / tread width", f"{fmt(Mt['crown_R'])} / {fmt(2 * Mt['tread_hw'])}",
         f"{fmt(Nt['crown_R'])} / {fmt(2 * Nt['tread_hw'])}", "E main, M nose / M"),
        ("Shoulder R / sidewall R", f"{fmt(Mt['shoulder_R'])} / {fmt(frm['Ru'])}",
         f"{fmt(Nt['shoulder_R'])} / {fmt(frn['Ru'])}", "E / D (solved tangent)"),
        ("Grooves: centres +-", "30, 56 (2 pairs)", "15, 44 (even)", "M head-on photos 3036, 3008, 3001"),
        ("Groove width x depth", f"{fmt(Mt['groove_w'])} x {fmt(Mt['groove_d'])}",
         f"{fmt(Nt['groove_w'])} x {fmt(Nt['groove_d'])}", "M width / E depth"),
        ("Ribs centre / mid / outer", f"{fmt(km['centre_rib'])} / {fmt(km['mid_rib'])} / {fmt(km['outer_rib'])}",
         f"{fmt(kn['centre_rib'])} / {fmt(kn['mid_rib'])} / {fmt(kn['outer_rib'])}", "D outer rib to the shoulder"),
        ("Wheel", "split hub, 2 halves", "split hub, 2 halves", "S POH 7-4-11; Goodrich 3-1543 / 3-1501"),
        ("Tie bolts n on PCD", f"{Mr['tie_n']} on {fmt(2 * Mr['tie_r'])}", f"{Nr['tie_n']} on {fmt(2 * Nr['tie_r'])}",
         "E hidden (main); M PCD, E count (nose)"),
        ("Valve / safety plug", f"R {fmt(Mr['valve_r'])} / 1", f"R {fmt(Nr['valve_r'])} / 1", "M position; S POH"),
        ("Fusible plugs", f"{Mr['fusible_n']} (inboard half)", "-", "S POH 7-4-11; E position"),
        ("Hub fairing lip / face / proud", f"{fmt(2 * Mf['r_lip'])} / {fmt(2 * Mf['r_face'])} / {fmt(Mf['proud'])}",
         "-", "M 3036, 3005, 3010, 3008, NGX"),
        ("Fairing screws / hole", f"{Mf['screws']} on {fmt(2 * Mf['screw_r'])} / Ø{fmt(Mf['hole_d'])} @R{fmt(Mf['hole_r'])}",
         "-", "M 5 at 72 deg"),
        ("Brake", "6 pist., 3 retr., steel", "-", "S POH 7-4-10; kit 2-1674-1"),
        ("Brake discs", f"{Mb['rotors']} rotors / {Mb['stators']} stators", "-", "S stators / E rotors"),
        ("Housing lobes / rotor dia", f"{fmt(2 * (Mb['lobe_c'] + Mb['lobe_R']))} / {fmt(2 * Mb['rotor_r'][1])}", "-",
         "M lobe tips / E"),
        ("Brake stack s", f"{fmt(Mb['housing_s'][0])} .. {fmt(stk[-1][2])}", "-", "E (s < 0 inboard)"),
        ("Axle dia / bore", f"{fmt(2 * Ma['r'])} / {fmt(2 * Ma['bore_r'])}", f"{fmt(2 * Na['r'])}",
         "G gear.py / M open bore"),
        ("Fork arms (faces)", "-", f"+-{fmt(Na['fork_in'])}..{fmt(Na['fork_out'])}", "M two arms (head-on photos)"),
    ]
    cols = [("ITEM (mm)", 58.0, "l"), ("MAIN", 56.0, "l"), ("NOSE", 50.0, "l"), ("SOURCE", 110.0, "l")]
    y = table(ds, x0, y0, cols, rows, title="KEY DIMENSIONS - model/wheels.py TABLES", size=2.5, row_h=4.1,
              zebra=lambda i: i % 2 == 1)
    ds.text(x0, y + 3.6, "O owner decision · P proposed · S sourced · M photo-measured · E estimated · D derived · "
            "G gear.py. "
            "s < 0 = main inboard (brake) side.", 2.1, "label", "start", fill=MUTED, tag="table")
    return y + 5.0


def draw_check_tables(ds, x0, y0):
    fbt = WH.fairing_beyond_tyre()
    em, en = WH.envelope("main"), WH.envelope("nose")
    gm = WH.gear_envelope("main")
    km, kn = WH.key_numbers(WH.MAIN), WH.key_numbers(WH.NOSE)
    Mf = WH.MAIN_FAIRING
    d_od = 2 * em["R"] - 0.62 if em["R"] < 0.31 else 0.0
    p_t, _ = retracted_depths()
    rows2 = [
        ("Main tyre OD (modelled)", "620-650", fmt(2 * em["R"]), fmt(d_od) if d_od else "0",
         "owner decision pending" if d_od else "-"),
        (f"  {ALT['size']} ({'proposed' if ALT is WH.MAIN_TYRE_850 else 'superseded'})", "-", fmt(2 * ALT["R"]),
         fmt(2 * ALT["R"] - 0.62) if ALT["R"] < 0.31 else "0", "MAIN_TYRE_CHOICE"),
        ("  3-D gear.MAIN_TYRE", "-", fmt(2 * gm["R"]), f"{fmt(2 * gm['R'] - 2 * em['R'])}", "from wheels.py"),
        ("Main section width", "214-224", fmt(em["W"]), "0", "-"),
        ("Main loaded radius", "270-280", f"axle {fmt(G.MAIN_AXLE[2])}", "0",
         "41 flat drawn" if LOADED_MAIN else "free circle"),
        ("Tyre R / fairing lip R", "2.15-2.21", f"{em['R'] / Mf['r_lip']:.2f}",
         f"{em['R'] / Mf['r_lip'] - 2.15:+.2f}" if em["R"] / Mf["r_lip"] < 2.15 else "0", "-"),
        ("Retracted tyre depth", "~25 (POH 1 in)", fmt(p_t, 1), f"{fmt(p_t - 0.0254, 1)}",
         "20-30 (fit_check 5)"),
        ("Main grooves / W", "0.14, 0.26", f"{km['groove_frac'][0]:.2f}, {km['groove_frac'][1]:.2f}", "0",
         "3-D geometry"),
        ("Render groove shader", "-", "off (geometry)", "-", "done"),
        ("Nose tyre OD", "17.5 in", fmt(2 * en["R"]), "0", "-"),
        ("Nose loaded radius", "200-210", f"axle {fmt(G.NOSE_AXLE[2])}", "+12..22", "axle kept"),
        ("Nose grooves / W", "0.09, 0.28", f"{kn['groove_frac'][0]:.2f}, {kn['groove_frac'][1]:.2f}", "0", "-"),
        ("Nose fork arms", "2", f"gear.py {len(G.NOSE_FORK_SIDES)}", "-1", "Stage 3"),
        ("Hub fairing dia / proud", "290-300 / 25-30", f"{fmt(2 * Mf['r_lip'])} / {fmt(Mf['proud'])}", "0",
         f"face {fmt(fbt)} > W/2"),
        ("Main pressure", "60 psi placard", f"gear.py info {WH.MAIN_TYRE_SEC['pressure']:.0f}", "0", "-"),
        ("Main brake", "6-lobe, in wheel", "3-D: wheels.py", "0", "-"),
    ]
    cols2 = [("ITEM", 64.0, "l"), ("PHOTOS [M]", 48.0, "l"), ("TABLE / MODEL", 54.0, "l"), ("Δ", 24.0, "r"),
             ("ACTION", 84.0, "l")]
    y2 = table(ds, x0, y0, cols2, rows2, title="PHOTO CHECK - DEVIATION CALL-OUTS (mm)", size=2.5, row_h=4.1,
               zebra=lambda i: i % 2 == 1)
    rows3 = [
        ("Tyre", "tire", "tire", "black satin; NO lettering"),
        ("Wheel halves", "wheel", "wheel", "gloss light grey / white"),
        ("Hub fairing", "main_gear_door", "-", "leg-door colour (3008 blue)"),
        ("Brake housing / discs", "metal / metal_dark", "-", "dull alu / dark steel"),
        ("Bolts, valve stem", "cadmium", "cadmium", "yellow-chromate cadmium / brass"),
        ("Fairing screws, valve cap", "metal / black", "- / black", "rubber-sealed cap"),
        ("Axle nut, hub cap", "steel", "steel", "lock plate (nose)"),
        ("Arm / fork", "gear_leg", "gear_leg", "adjacent"),
    ]
    cols3 = [("PART", 64.0, "l"), ("MAIN", 60.0, "l"), ("NOSE", 40.0, "l"), ("NOTE", 110.0, "l")]
    y3 = table(ds, x0, y2 + 6.0, cols3, rows3, title="MATERIALS (model/assemble.py NAMES)", size=2.5, row_h=4.1)
    return y3


def draw_notes(ds, x0, y0, x1):
    fbt = WH.fairing_beyond_tyre()
    chk = WH.tra_envelope_check("main")
    gm = WH.gear_envelope("main")
    items = [
        "Drawn from the parameter tables of model/wheels.py (PTable: value + source tag + note): tyre envelopes "
        "MAIN_TYRE_ENV / NOSE_TYRE_ENV, sections, rims, fairing, brake, axles; never from the mesh. Axle positions and "
        "the gear context (trailing arm, leg, shock, nose fork) from model/gear.py, drawn as adjacent parts (phantom). "
        "Photos and their measurement working stay in the git-ignored refs/cache.",
        "First-angle projection. Each assembly: SIDE view from port (principal), FRONT view from ahead to its right "
        "(upper half in section through the axle), TOP view from above below it; for the main wheel also view C from "
        "starboard (inboard / brake face) at the far right. Each group's side / front views stand on one ground line.",
        (f"MAIN TYRE - modelled {MOD['size']} (Jane's / Pilatus drawing 190.10.40.432: the size of pc12/CLAUDE.md's "
         f"sourced facts and the approved sheets L1-L5, OD {fmt(2 * MOD['R'])}). PROPOSED, OWNER DECISION PENDING: the "
         "8.50-10 Type III of the tyre makers, parts lists and four photo methods (TRA OD 627-652, drawn free OD "
         f"{fmt(2 * WH.MAIN_TRA['R'])}; 22x8.50-10 is not a listed tyre size), shown in the accent colour. One line "
         "switches it (wheels.MAIN_TYRE_CHOICE; PC12_MAIN_TYRE=8.50-10 for a trial build): axles and static stance "
         "kept (axle WL 279 = its loaded radius, flat on the ground over a 250 mm patch, 41 mm deflection)."
         if MOD is WH.MAIN_TYRE_22 else
         f"MAIN TYRE - modelled 8.50-10 Type III (tyre makers, parts lists, four photo methods; TRA OD 627-652, drawn "
         f"free OD {fmt(2 * MOD['R'])}); Jane's / Pilatus drawing 22x8.50-10 (OD 559) shown in the accent colour. "
         "Axles and static stance kept: axle WL 279 = the loaded radius, the tyre flat on the ground over a 250 mm "
         "patch (41 mm deflection) with a 6 mm sidewall bulge."),
        f"3-D model: gear.MAIN_TYRE = this envelope (R {fmt(gm['R'], 1)}); the LD-1 leg-door scallop (R + 12.5 = "
        f"{fmt(G.LEG_DOOR['scallop_r'], 1)}) and the round well (bays.WELL_R) follow it. model/wheels.py main_wheel / "
        "nose_wheel revolve / extrude the profiles of this sheet (tyre with the grooves, wheel halves, hub fairing, "
        "brake, valve, tie bolts); test/consistency_2d3d.py (L4W) compares the mesh with them.",
        "Tyre section: tangent arcs - crown R to the tread half-width, shoulder round, upper sidewall (radius solved: "
        "tangent to the shoulder, max width W/2 at 0.50 H), lower sidewall to where the tyre leaves the rim-flange tip "
        + (f"round. At the TRA max shoulder width the modelled section is Ø{fmt(2 * chk['r_model'], 1)}, inside the TRA "
           f"max Ø{fmt(2 * chk['r_tra_max'], 1)}." if chk["tra"] else
           "round. The 22 in size has no TRA entry; detail D shows the proposed 8.50-10's TRA growth envelope."),
        f"Main hub fairing (POH: fairings on the outer hubs), painted in the leg-door colour; its face stands "
        f"{fbt * 1000:.0f} mm outboard of the tyre's max width; retracted (wheel tilted with the skin) it lies "
        f"{retracted_depths()[1] * 1000:.1f} mm below the skin, inside the tyre's {retracted_depths()[0] * 1000:.1f} mm "
        "(POH ~1 in; fit_check 5).",
        "Main brake: six pistons, three retractors, steel friction surfaces, bolted to the axle (POH 7-4-10); 3 rotors "
        "/ 2 stators inferred from the overhaul kit (24 pads, 2 stators, 48 rivets). Housing, stack and torque tube "
        "sized inside the inboard wheel half [E]; one piston lobe is shown in section.",
        "No markings (owner decision): no sidewall lettering, brand names or placards on wheels or tyres. The tread "
        "grooves are geometry (the render-time groove shader is off). Screw, valve and tie-bolt "
        "clocking is the drawn pose (the wheels turn); starboard units are mirror images. The main leg door (LD-1) "
        "is not shown.",
    ]
    return notes(ds, x0, y0, x1, items, size=2.5, line_h=3.6)


def draw_legend(ds, x0, y0):
    ds.text(x0, y0, "LEGEND", 3.2, "label", "start", weight=600, spacing=0.3, tag="legend")
    items = [("tyre (rubber) in section", dict(fill=TYRE_FILL, w=W_FINE)),
             ("metal in section (hatched)", dict(fill=PAPER, w=W_FINE)),
             ("brake rotor / stator, lining", dict(fill=ROTOR_FILL, w=0.0)),
             ("adjacent parts, free tyre, TRA env.", dict(w=W_FINE, dash=PHANTOM)),
             ("hidden", dict(w=W_FINE, dash=HID)),
             ("centre line, pitch circle", dict(w=W_THIN, dash=CHAIN)),
             (f"{ALT['size']} tyre ({'proposed' if ALT is WH.MAIN_TYRE_850 else 'superseded'})",
              dict(w=W_FINE, dash=SUP, color=ACCENT))]
    y = legend_rows(ds, x0, y0 + 7.0, items, dy=4.6, size=2.3)
    yh = y0 + 7.0 + 4.6
    hatch(ds, np.array([[x0, yh - 1.2], [x0 + 8.0, yh - 1.2], [x0 + 8.0, yh + 1.2], [x0, yh + 1.2]]), 45.0, 1.0)
    yb = y0 + 7.0 + 9.2
    ds.cv.rect(x0 + 2.7, yb - 1.2, 2.7, 2.4, lw=0.0, fill=PLATE_FILL, stroke=False)
    ds.cv.rect(x0 + 5.4, yb - 1.2, 2.6, 2.4, lw=0.0, fill=LINING_FILL, stroke=False)
    return y


# ============================================================================================ overlay (private)
def draw_overlay(ds):
    """Pilatus drawing (red) round the wheels in the side views, photo-measured sizes (blue)."""
    vm, vn = ds.views["main_side"], ds.views["nose_side"]
    ax, az = main_axle()
    n = ds.ov_mbp(vm, "side", clip=(ax - 0.37, -0.03, ax + 0.37, az + 0.37), mapfn=lambda P: P - [G.GEAR_SHIFT, 0.0])
    A = G.NOSE_AXLE
    n += ds.ov_mbp(vn, "side", clip=(A[0] - 0.30, -0.03, A[0] + 0.30, A[2] + 0.40),
                   mapfn=lambda P: P + [G.GEAR_SHIFT, 0.0])
    for d in WH.PHOTO["main_od"][0]:
        ds.ov_polylines(vm, [circle_pts((ax, az), d / 2, 181)], color=BLUE, w=0.2, dash=(1.2, 0.8),
                        clip=(-99, 0.0, 99, 99))
    for d in WH.PHOTO["fairing_d"][0]:
        ds.ov_polylines(vm, [circle_pts((ax, az), d / 2, 121)], color=BLUE, w=0.16, dash=(0.8, 0.8))
    ds.ov_text(vm.pt(ax + 0.39, 0.0)[0], GY_M + 12.0, "BLUE: PHOTO OD 620-650, FAIRING 290-300", 2.4, BLUE)
    ds.ov_text(vm.pt(ax + 0.39, 0.0)[0], GY_M + 15.5, "RED: PILATUS DRAWING (22 IN TYRE CIRCLE)", 2.4, BLUE)
    for view, which in (("main_front", "main"), ("nose_front", "nose")):
        g = WH.PHOTO[f"{which}_grooves"][0]
        W = WH.envelope(which)["W"]
        ds.ov_marks(ds.views[view], [(sg * f * W, WH.envelope(which)["R"] + 0.006) for f in g for sg in (-1, 1)])
    ds.log.append(f"overlay: {n} Pilatus polylines round the wheels")


# ============================================================================================ sheet
def draw(ds):
    ds.frame_and_title()
    draw_main_side(ds)
    draw_main_front(ds)
    draw_main_rear(ds)
    draw_main_top(ds)
    draw_main_hub_detail(ds)
    draw_nose_side(ds)
    draw_nose_front(ds)
    draw_nose_top(ds)
    draw_tyre_detail(ds, WH.MAIN, DET_X["main"], "D")
    draw_tyre_detail(ds, WH.NOSE, DET_X["nose"], "F")
    y = draw_tables(ds, X_TAB, 22.0)
    y = draw_check_tables(ds, X_TAB, y + 6.0)
    yl = draw_legend(ds, X_TAB, y + 12.0)
    scale_bar(ds, X_TAB + 170.0, y + 22.0, SC, length_m=0.3, step_m=0.05, label=f"SCALE 1:{SC}")
    scale_bar(ds, X_TAB + 170.0, y + 42.0, 2, length_m=0.15, step_m=0.025, label="SCALE 1:2")
    draw_notes(ds, X_TAB, yl + 10.0, 1172.0)
    M.break_paths_at_text(ds, lambda d: d.get("dash") in (CHAIN, PHANTOM, SUP) or d.get("color") == MUTED, pad=0.6)
    try:
        draw_overlay(ds)
    except Exception as e:                      # noqa: BLE001 -- the clean sheet must not depend on refs/cache
        ds.log.append(f"overlay skipped: {e}")


if __name__ == "__main__":
    M.main(["L4W"] + sys.argv[1:])
