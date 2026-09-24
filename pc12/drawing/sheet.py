"""
PC-12 general-arrangement sheet (A1 landscape, 1:50) -> out/pc12_ga.svg + out/pc12_ga.pdf

    cd <project root> && python3 -m drawing.sheet        (or: python3 -m drawing)

Layout: side view (from port, nose left) top-left; plan view (from above, starboard wing
UP) below it and aligned with it in x; front view (from ahead, starboard on the viewer's
LEFT) to the right of the side view, sharing its ground line; parts list, leading
particulars, scale bar, notes and title block in the right-hand column.

Projection note: this placement (plan below the side view, front view to its right) is
the first-angle arrangement for those viewing directions. The title block carries the
third-angle symbol as specified; every view is titled with its viewing direction, and
PROJECTION = "first" switches the symbol.

All dimension values are read from the model modules (wing, gear, empennage, fuselage,
powerplant) or from the posed geometry, never typed in.
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from drawing import hlr  # noqa: E402
from drawing.canvas import Canvas, text_width  # noqa: E402

OUT_DIR = str(__import__("pathlib").Path(__file__).resolve().parents[1]) + "/out"
SHEET_W, SHEET_H = 841.0, 594.0
SCALE = 50
K = 1000.0 / SCALE                     # sheet mm per model metre (1:50 -> 20)
INK, PAPER = "#1B2429", "#FCFCFA"

# line weights (mm)
W_OBJ, W_FINE, W_DIM = 0.35, 0.18, 0.13
W_FRAME, W_TABLE, W_TABLE_IN = 0.5, 0.35, 0.18
CHAIN = (12.0, 1.5, 1.2, 1.5)          # thin long-dash-dot (centre / thrust / ground lines)
PHANTOM = (10.0, 1.2, 1.2, 1.2, 1.2, 1.2)  # long-dash-double-dot (prop disc, reference lines)

# frame (ISO 5457: 20 mm filing margin left, 10 mm elsewhere)
FX0, FY0, FX1, FY1 = 20.0, 10.0, 831.0, 584.0

# view placement: side & plan share X(x); side & front share the ground line
X0 = 60.0                              # sheet X of fuselage station 0 (datum)
YG = 127.0                             # ground line (side and front views)
YC = 347.0                             # plan-view centreline
XF = 606.0                             # front-view centreline

TXT_DIM = 3.2                          # dimension text height
ARROW_L, ARROW_W = 3.0, 1.0

PROJECTION = "first"                   # plan below side view, front view to the right = first-angle layout


def side_xy(x, z):
    return X0 + K * x, YG - K * z


def plan_xy(x, y):
    return X0 + K * x, YC - K * y


def front_uv(u, v):                    # front view in HLR view coordinates (u = -y, v = z)
    return XF + K * u, YG - K * v


def front_xy(y, z):                    # model coordinates: starboard (+y) on the viewer's LEFT
    return front_uv(-y, z)


def thou(v_mm):
    """Integer millimetres with thousands separators: 14400 -> '14,400'."""
    return f"{int(round(v_mm)):,}"


# ============================================================================ drawing helpers
class Sheet:
    def __init__(self):
        self.cv = Canvas(SHEET_W, SHEET_H, PAPER, INK)
        self.boxes = []                # (x0, y0, x1, y1, tag) of text & balloons, for overlap checks
        self.geom = {}                 # view -> list of sheet-mm polylines (object + fine)
        self.leaders = []              # (start, end, item) of balloon leaders

    # --- low level
    def arrow(self, tip, direction):
        """Filled arrowhead with its tip at `tip`, pointing along `direction`."""
        d = np.asarray(direction, float)
        d = d / np.linalg.norm(d)
        n = np.array([-d[1], d[0]])
        tip = np.asarray(tip, float)
        base = tip - ARROW_L * d
        self.cv.polygon([tuple(tip), tuple(base + 0.5 * ARROW_W * n), tuple(base - 0.5 * ARROW_W * n)])

    def text(self, x, y, s, size=3.5, font="label", anchor="start", rot=0.0, weight=400, tag="text", fill=None,
             vcenter=False, box=True, spacing=0.0):
        self.cv.text(x, y, s, size, font, anchor, rot, weight, fill=fill, vcenter=vcenter, spacing=spacing)
        if box:
            w = text_width(s, size, font, weight) + spacing * max(len(s) - 1, 0)
            h = 0.72 * size
            ox = {"start": 0.0, "middle": -w / 2, "end": -w}[anchor]
            a = math.radians(rot)
            bx, by = x, y
            if vcenter:                          # same shift as Canvas.text
                bx, by = x - 0.35 * size * math.sin(a), y + 0.35 * size * math.cos(a)
            # corners in text space relative to the baseline point (y down, glyphs above)
            corners = np.array([[ox, 0.15 * size], [ox + w, 0.15 * size], [ox + w, -h], [ox, -h]])
            R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
            px = corners @ R.T + [bx, by]
            self.boxes.append((px[:, 0].min(), px[:, 1].min(), px[:, 0].max(), px[:, 1].max(), tag))

    # --- dimensions
    def dim(self, p1, p2, pos, text, orient="h", f1=None, f2=None, text_side=None, text_at=None,
            gap=1.2, over=2.0, tag="dim", font="mono", show_text=True):
        """Linear dimension between p1 and p2 (sheet mm).
        orient 'h': dimension line horizontal at y=pos; 'v': vertical at x=pos.
        f1/f2: feature points the extension lines start from (default p1/p2); None -> no extension line
        if the feature point lies on the dimension line already."""
        cv = self.cv
        p1 = np.asarray(p1, float)
        p2 = np.asarray(p2, float)
        f1 = p1 if f1 is None else np.asarray(f1, float)
        f2 = p2 if f2 is None else np.asarray(f2, float)
        if orient == "h":
            a = np.array([p1[0], pos])
            b = np.array([p2[0], pos])
            axis = 0
        else:
            a = np.array([pos, p1[1]])
            b = np.array([pos, p2[1]])
            axis = 1
        # extension lines
        for f, e in ((f1, a), (f2, b)):
            v = e - f
            L = np.linalg.norm(v)
            if L > gap + 0.3:
                u = v / L
                cv.line(tuple(f + gap * u), tuple(e + over * u), W_DIM)
        if a[axis] > b[axis]:
            a, b = b, a
        L = b[axis] - a[axis]
        tw = text_width(text, TXT_DIM, font)
        u = (b - a) / max(L, 1e-9)
        inside = L >= 2 * ARROW_L + tw + 3.0
        if L >= 2 * ARROW_L + 1.5:
            cv.line(tuple(a), tuple(b), W_DIM)
            self.arrow(a, -u)
            self.arrow(b, u)
        else:                                            # arrows outside, pointing in
            cv.line(tuple(a - (ARROW_L + 3.0) * u), tuple(b + (ARROW_L + 3.0) * u), W_DIM)
            self.arrow(a, u)
            self.arrow(b, -u)
        # text
        if text_at is not None:
            tx, ty = text_at
        elif inside:
            tx, ty = (a + b) / 2
        else:
            side = text_side or "after"
            if side == "after":
                tx, ty = b + (ARROW_L + 4.0 + tw / 2) * u
            else:
                tx, ty = a - (ARROW_L + 4.0 + tw / 2) * u
        if not show_text:
            return
        if orient == "h":
            self.text(tx, ty - 1.0, text, TXT_DIM, font, "middle", tag=tag)
        else:
            self.text(tx - 1.0, ty, text, TXT_DIM, font, "middle", rot=-90, tag=tag)

    def angle_dim(self, vertex, a_from, a_to, radius, text, text_pos, tag="dim"):
        """Angular dimension: arc of `radius` about `vertex` between directions a_from -> a_to
        (degrees, sheet coordinates with y down); arrows drawn outside when the arc is short."""
        vx, vy = vertex
        t = np.radians(np.linspace(a_from, a_to, 24))
        arc = [(vx + radius * math.cos(q), vy + radius * math.sin(q)) for q in t]
        chord = radius * abs(math.radians(a_to - a_from))
        cv = self.cv
        if chord > 2 * ARROW_L + 2:
            cv.path(arc, W_DIM)
            for q, s in ((t[0], -1), (t[-1], 1)):
                tip = (vx + radius * math.cos(q), vy + radius * math.sin(q))
                tang = np.array([-math.sin(q), math.cos(q)]) * s * np.sign(a_to - a_from)
                self.arrow(tip, tang)
        else:
            ext = math.degrees((ARROW_L + 3.0) / radius)
            sgn = np.sign(a_to - a_from)
            t2 = np.radians(np.linspace(a_from - sgn * ext, a_to + sgn * ext, 40))
            cv.path([(vx + radius * math.cos(q), vy + radius * math.sin(q)) for q in t2], W_DIM)
            for q, s in ((math.radians(a_from), 1), (math.radians(a_to), -1)):
                tip = (vx + radius * math.cos(q), vy + radius * math.sin(q))
                tang = np.array([-math.sin(q), math.cos(q)]) * s * sgn
                self.arrow(tip, tang)
        self.text(text_pos[0], text_pos[1], text, TXT_DIM, "mono", "start", tag=tag)

    # --- balloons
    def balloon(self, center, anchor, num, r=4.0):
        cx, cy = center
        ax, ay = anchor
        v = np.array([ax - cx, ay - cy])
        L = np.linalg.norm(v)
        u = v / max(L, 1e-9)
        self.cv.line((cx + r * u[0], cy + r * u[1]), (ax, ay), W_DIM)
        self.leaders.append(((cx + r * u[0], cy + r * u[1]), (ax, ay), num))
        self.cv.circle(ax, ay, 0.55, w=0.0, fill=INK, stroke=False)
        self.cv.circle(cx, cy, r, w=0.25, fill=PAPER)
        self.cv.text(cx, cy, str(num), 3.6, "mono", "middle", weight=500, vcenter=True)
        self.boxes.append((cx - r, cy - r, cx + r, cy + r, f"balloon {num}"))


# ============================================================================ geometry from the model
def model_numbers():
    from model import wing as W, gear as G, empennage as E, fuselage as F, powerplant as PP
    m, ym, lemac = W.mac()
    return dict(
        span=W.SPAN_TOTAL, c_root=W.C_ROOT, c_tip=W.C_TIP, mac=m, y_mac=ym, lemac=lemac, x_qc=W.X_QC,
        semi=W.SEMI, dihedral_deg=math.degrees(W.DIHEDRAL), z_qc0=W.Z_QC0, area=W.AREA_REF,
        track=G.TRACK, wheelbase=G.WHEELBASE, main_axle=G.MAIN_AXLE, nose_axle=G.NOSE_AXLE,
        main_R=G.MAIN_TYRE["R"], nose_R=G.NOSE_TYRE["R"],
        stab_span=2 * E.STAB_TIP_Y, stab_tip_y=E.STAB_TIP_Y,
        prop_d=2 * PP.PROP_R, prop_r=PP.PROP_R, prop_x=PP.PROP_X, prop_z=F.PROP_AXIS_Z,
        prop_clear=F.PROP_AXIS_Z - PP.PROP_R,
        sta_firewall=F.STA["firewall"], sta_apb=F.STA["aft_pressure_bulkhead"],
        spinner_tip=F.STA["spinner_tip"],
    )


def extreme_points(prep):
    """Overall extents of the drawn (posed) airframe."""
    V = np.vstack([g.V for g in prep["groups"]])
    i_xmin, i_xmax = np.argmin(V[:, 0]), np.argmax(V[:, 0])
    i_ymin, i_ymax = np.argmin(V[:, 1]), np.argmax(V[:, 1])
    i_zmax = np.argmax(V[:, 2])
    return dict(xmin=V[i_xmin], xmax=V[i_xmax], ymin=V[i_ymin], ymax=V[i_ymax], zmax=V[i_zmax])


# ============================================================================ sheet parts
def draw_frame(sh: Sheet, frame=None, ncol=16, nrow=12):
    """Frame + grid-reference zones (numbers along top/bottom, letters A.. without I along
    the sides) + centring marks. Defaults: A1 with 16 x 12 zones."""
    cv = sh.cv
    FX0, FY0, FX1, FY1 = frame or (globals()["FX0"], globals()["FY0"], globals()["FX1"], globals()["FY1"])
    SW, SH = cv.W, cv.H
    cv.rect(FX0, FY0, FX1 - FX0, FY1 - FY0, lw=W_FRAME)
    letters = [c for c in "ABCDEFGHJKLMNP"][:nrow]
    xs = np.linspace(FX0, FX1, ncol + 1)
    ys = np.linspace(FY0, FY1, nrow + 1)
    for x in xs[1:-1]:
        cv.line((x, FY0), (x, FY0 - 5.0), W_FINE)
        cv.line((x, FY1), (x, FY1 + 5.0), W_FINE)
    for y in ys[1:-1]:
        cv.line((FX0, y), (FX0 - 5.0, y), W_FINE)
        cv.line((FX1, y), (FX1 + 5.0, y), W_FINE)
    for i in range(ncol):
        xm = 0.5 * (xs[i] + xs[i + 1])
        sh.text(xm, FY0 - 5.0, str(i + 1), 3.0, "mono", "middle", vcenter=True, tag="zone")
        sh.text(xm, FY1 + 5.0, str(i + 1), 3.0, "mono", "middle", vcenter=True, tag="zone")
    for j in range(nrow):
        ym = 0.5 * (ys[j] + ys[j + 1])
        sh.text(FX0 - 10.0, ym, letters[j], 3.0, "label", "middle", vcenter=True, weight=600, tag="zone")
        sh.text(FX1 + 5.0, ym, letters[j], 3.0, "label", "middle", vcenter=True, weight=600, tag="zone")
    # centring marks
    for (x, y, dx, dy) in ((SW / 2, 0, 0, 1), (SW / 2, SH, 0, -1), (0, SH / 2, 1, 0), (SW, SH / 2, -1, 0)):
        L = 15.0 if (dx == 1) else 10.0
        cv.line((x, y), (x + dx * (L + 5), y + dy * (L + 5)), W_FRAME)


def draw_view_lines(sh: Sheet, view, mapfn, name):
    cv = sh.cv
    polys = []
    for w, P, _ in view.lines:
        Q = [mapfn(u, v) for u, v in P]
        polys.append((w, Q))
    for w, Q in polys:                     # fine first, object lines on top
        if w == hlr.FINE:
            cv.path(Q, W_FINE)
    for w, Q in polys:
        if w == hlr.OBJECT:
            cv.path(Q, W_OBJ)
    sh.geom[name] = [np.array(Q) for _, Q in polys]


def view_title(sh: Sheet, x, y, title, sub):
    sh.text(x, y, title, 5.0, "label", "middle", weight=600, spacing=0.4)
    sh.text(x, y + 4.8, sub, 2.8, "label", "middle")
    w = text_width(title, 5.0, "label", 600) + 0.4 * (len(title) - 1)
    sh.cv.line((x - w / 2, y + 1.3), (x + w / 2, y + 1.3), W_FINE)


def draw_side(sh: Sheet, view, N, ext):
    cv = sh.cv
    draw_view_lines(sh, view, side_xy, "side")
    # ground line (thin chain) with short ground hatching under the wheels
    gx0, gx1 = side_xy(-1.35, 0)[0], side_xy(16.35, 0)[0]
    xh_side = side_xy(16.0, 0)[0]
    cv.line((gx0, YG), (gx1, YG), W_DIM, CHAIN)
    sh.text(xh_side - 3.0, YG - 1.2, "GROUND LINE", 2.5, "label", "end", tag="label")
    for xw in (N["nose_axle"][0], N["main_axle"][0]):
        X = side_xy(xw, 0)[0]
        for k in range(-3, 4):
            cv.line((X + 2.2 * k - 1.2, YG + 2.2), (X + 2.2 * k + 1.0, YG), W_DIM)
    # wheel centre marks
    for (xa, za) in ((N["nose_axle"][0], N["nose_axle"][2]), (N["main_axle"][0], N["main_axle"][2])):
        X, Y = side_xy(xa, za)
        cv.line((X - 3, Y), (X + 3, Y), W_DIM)
        cv.line((X, Y - 3), (X, Y + 3), W_DIM)
    # thrust line ahead of the spinner, prop disc trace
    tx0, ty = side_xy(-1.30, N["prop_z"])
    tx1 = side_xy(N["spinner_tip"] - 0.05, 0)[0]
    cv.line((tx0, ty), (tx1, ty), W_DIM, CHAIN)
    sh.text(tx0, ty - 1.2, "THRUST LINE", 2.3, "label", "start", tag="label")
    px_, pz0 = side_xy(N["prop_x"], N["prop_z"] - N["prop_r"])
    pz1 = side_xy(N["prop_x"], N["prop_z"] + N["prop_r"])[1]
    cv.line((px_, pz0), (px_, pz1), W_DIM, PHANTOM)

    # --- dimensions
    # overall length: spinner tip -> aft-most point
    a = side_xy(ext["xmin"][0], ext["xmin"][2])
    b = side_xy(ext["xmax"][0], ext["xmax"][2])
    length = (ext["xmax"][0] - ext["xmin"][0]) * 1000
    sh.dim(a, b, YG - K * 4.26 - 13.0, thou(length), "h")
    # overall height (aft of the tail): ground -> top of the bullet fairing
    top = side_xy(ext["zmax"][0], ext["zmax"][2])
    xh = side_xy(16.0, 0)[0]
    sh.dim((top[0], YG), top, xh, thou(ext["zmax"][2] * 1000), "v", f1=(xh, YG), f2=top)
    # propeller diameter + ground clearance, chained forward of the spinner
    xd = side_xy(-0.45, 0)[0]
    p_lo = side_xy(N["prop_x"], N["prop_z"] - N["prop_r"])
    p_hi = side_xy(N["prop_x"], N["prop_z"] + N["prop_r"])
    sh.dim(p_lo, p_hi, xd, "Ø" + thou(N["prop_d"] * 1000), "v", text_at=(xd, side_xy(0, 2.42)[1]))
    sh.dim((p_lo[0], YG), p_lo, xd, thou(N["prop_clear"] * 1000), "v", f1=(xd, YG), text_side="after")
    # wheelbase (below the ground line, from the axle centre lines)
    na = side_xy(N["nose_axle"][0], N["nose_axle"][2])
    ma = side_xy(N["main_axle"][0], N["main_axle"][2])
    sh.dim(na, ma, YG + 10.0, thou(N["wheelbase"] * 1000), "h", f1=(na[0], na[1] + 3.5), f2=(ma[0], ma[1] + 3.5))

    # --- station line
    ys = YG + 22.0
    xa_, xb_ = side_xy(0.0, 0)[0], side_xy(15.0, 0)[0]
    cv.line((xa_, ys), (xb_, ys), W_FINE)
    for s in range(0, 16):
        X = side_xy(s, 0)[0]
        cv.line((X, ys), (X, ys - 1.6), W_DIM)
    stations = [(0.0, "DATUM"), (N["sta_firewall"], "FIREWALL"), (N["lemac"], "LEMAC"),
                (N["sta_apb"], "AFT PRESS. BHD")]
    for s, lab in stations:
        X = side_xy(s, 0)[0]
        cv.line((X, ys - 4.0), (X, ys + 2.0), W_FINE)
        sh.text(X, ys + 5.6, "STA " + thou(s * 1000), 2.7, "mono", "middle", tag="sta")
        sh.text(X, ys + 9.2, lab, 2.4, "label", "middle", tag="sta")
    sh.text(xb_ + 2.0, ys + 0.9, "STATIONS, mm AFT OF DATUM", 2.3, "label", "start", tag="sta")


def draw_plan(sh: Sheet, view, N, ext):
    from model import wing as W
    cv = sh.cv
    draw_view_lines(sh, view, plan_xy, "plan")
    # aircraft centre line
    cv.line(plan_xy(-0.5, 0), plan_xy(15.3, 0), W_DIM, CHAIN)
    sh.text(plan_xy(15.3, 0)[0] + 1.0, YC, "℄", 3.4, "label", "start", vcenter=True, tag="label")
    # reference planform (LE / TE of the trapezoid) through the fuselage, port side
    s0, sb = W.section_at(0.0), W.section_at(0.86)
    for xf in (0.0, 1.0):
        p0 = plan_xy(s0.le[0] + xf * s0.chord, -0.0)
        p1 = plan_xy(sb.le[0] + xf * sb.chord, -0.86)
        cv.line(p0, p1, W_DIM, PHANTOM)
    # MAC chord drawn on the starboard wing
    m, ym, lemac = N["mac"], N["y_mac"], N["lemac"]
    a, b = plan_xy(lemac, ym), plan_xy(lemac + m, ym)
    cv.line(a, b, 0.25, (6.0, 1.2))
    for p in (a, b):
        cv.line((p[0], p[1] - 2.0), (p[0], p[1] + 2.0), 0.25)
    sh.text(0.5 * (a[0] + b[0]), a[1] - 1.4, "MAC " + thou(m * 1000), 2.8, "mono", "middle", tag="dim")
    # spanwise position of the MAC from the centre line
    xpos = plan_xy(N["lemac"] - 0.75, 0)[0]
    sh.dim(plan_xy(lemac, 0), a, xpos, thou(ym * 1000), "v", f1=(xpos, YC), f2=a)
    # wing span over the winglets
    xs_ = plan_xy(-0.95, 0)[0]
    pt_hi = plan_xy(ext["ymax"][0], ext["ymax"][1])
    pt_lo = plan_xy(ext["ymin"][0], ext["ymin"][1])
    sh.dim(pt_lo, pt_hi, xs_, thou(N["span"] * 1000), "v")
    # tailplane span
    from model import empennage as E
    ty = N["stab_tip_y"]
    tip_hi = plan_xy(E.stab_te(ty), ty)
    tip_lo = plan_xy(E.stab_te(ty), -ty)
    sh.dim(tip_lo, tip_hi, plan_xy(16.0, 0)[0], thou(N["stab_span"] * 1000), "v")
    # root chord (reference trapezoid at the centre line), dimension line inside the fuselage outline
    r_le = plan_xy(s0.le[0], 0.0)
    r_te = plan_xy(s0.le[0] + s0.chord, 0.0)
    sh.dim(r_le, r_te, YC + K * 0.42, thou(N["c_root"] * 1000), "h", text_at=(0.5 * (r_le[0] + r_te[0]), YC + K * 0.42 + 4.4))
    # tip chord (port wing, winglet root)
    st = W.section_at(W.SEMI)
    t_le = plan_xy(st.le[0], -W.SEMI)
    t_te = plan_xy(st.le[0] + st.chord, -W.SEMI)
    sh.dim(t_le, t_te, plan_xy(0, -8.62)[1], thou(N["c_tip"] * 1000), "h")


def draw_front(sh: Sheet, view, N, ext):
    cv = sh.cv
    draw_view_lines(sh, view, front_uv, "front")
    # centre line, ground line, prop disc
    cv.line(front_xy(0, -0.25), front_xy(0, 4.55), W_DIM, CHAIN)
    g0, g1 = front_xy(8.8, 0)[0], front_xy(-9.2, 0)[0]
    cv.line((g0, YG), (g1, YG), W_DIM, CHAIN)
    sh.text(front_xy(-8.95, 0)[0] - 3.0, YG - 1.2, "GROUND LINE", 2.5, "label", "end", tag="label")
    th = np.linspace(0, 2 * np.pi, 145)
    disc = [front_xy(N["prop_r"] * math.cos(q), N["prop_z"] + N["prop_r"] * math.sin(q)) for q in th]
    cv.path(disc, W_DIM, PHANTOM)
    for yw in (N["track"] / 2, -N["track"] / 2, 0.0):          # ground hatching under the wheels
        X = front_xy(yw, 0)[0]
        for k in range(-2, 3):
            cv.line((X + 2.2 * k - 1.2, YG + 2.2), (X + 2.2 * k + 1.0, YG), W_DIM)
    # wheel track (between the main-wheel centre planes)
    l_ = front_xy(N["track"] / 2, 0)
    r_ = front_xy(-N["track"] / 2, 0)
    wl = front_xy(N["track"] / 2, N["main_axle"][2])
    wr = front_xy(-N["track"] / 2, N["main_axle"][2])
    for p in (wl, wr):
        cv.line((p[0], p[1] - 3.0), (p[0], p[1] + 3.0), W_DIM)
        cv.line((p[0] - 3.0, p[1]), (p[0] + 3.0, p[1]), W_DIM)
    sh.dim(l_, r_, YG + 10.0, thou(N["track"] * 1000), "h", f1=(wl[0], wl[1] + 3.5), f2=(wr[0], wr[1] + 3.5))
    # height
    top = front_xy(0.0, ext["zmax"][2])                      # top of the fin/tailplane bullet
    xh = front_xy(-8.95, 0)[0]
    sh.dim((top[0], YG), top, xh, thou(ext["zmax"][2] * 1000), "v", f1=(xh, YG), f2=top)
    # dihedral: angle between the wing reference plane (its trace extended beyond the
    # starboard tip) and the horizontal; vertex on the trace just outboard of the winglet
    dih = N["dihedral_deg"]
    yv = 8.36
    zv = N["z_qc0"] + yv * math.tan(math.radians(dih))
    V = front_xy(yv, zv)
    L, R = 44.0, 36.0
    ang = math.radians(dih)
    end_ref = (V[0] - L * math.cos(ang), V[1] - L * math.sin(ang))
    cv.line((V[0] + 4.0 * math.cos(ang), V[1] + 4.0 * math.sin(ang)), end_ref, W_DIM, PHANTOM)
    cv.line((V[0] + 1.5, V[1]), (V[0] - L, V[1]), W_DIM)
    txt = f"{dih:.1f}°"
    sh.angle_dim(V, 180.0, 180.0 + dih, R, txt,
                 (V[0] - L - 1.5 - text_width(txt, TXT_DIM, "mono"), V[1] - 0.3))
    sh.text(V[0] - L - 1.5, V[1] + 4.0, "DIHEDRAL", 2.5, "label", "end", tag="label")
    xr = V[0] - R + 4.5
    sh.text(xr, V[1] - (V[0] - xr) * math.tan(ang) - 1.3, "WING REF. PLANE", 2.2, "label", "start", tag="label")


# ---------------------------------------------------------------------------- balloons / BOM
ITEMS = [
    # item, part ids, view, anchor (model xyz), balloon position (view u, v in metres)
    (1, ["fus_fwd", "fus_center", "fus_aft"], "side", (7.40, -0.84, 2.42), (7.00, 3.35)),
    (2, ["wing_R", "wing_L"], "plan", (5.80, 5.00, 1.40), (4.15, 5.55)),
    (3, ["winglet_R", "winglet_L"], "plan", (5.95, 7.98, 1.60), (4.55, 7.70)),
    (4, ["flap_R", "flap_L"], "plan", (6.85, 3.00, 1.20), (8.55, 3.30)),
    (5, ["aileron_R", "aileron_L"], "plan", (6.55, 6.80, 1.45), (8.20, 6.95)),
    (6, ["fin"], "side", (13.20, -0.06, 3.40), (12.10, 3.95)),
    (7, ["rudder"], "side", (14.30, -0.04, 3.00), (15.35, 3.02)),
    (8, ["dorsal_fin"], "side", (11.95, -0.03, 2.75), (10.90, 3.45)),
    (9, ["stabilizer"], "plan", (14.05, 1.80, 4.17), (12.60, 2.90)),
    (10, ["elevator_R", "elevator_L"], "plan", (14.50, 1.20, 4.15), (15.30, 1.90)),
    (11, ["tail_bullet"], "side", (14.25, -0.13, 4.18), (15.35, 3.78)),
    (12, ["strakes"], "side", (13.10, -0.21, 1.75), (13.30, 0.85)),
    (13, ["propeller", "blade_1", "blade_2", "blade_3", "blade_4", "blade_5"], "side", (0.80, -0.30, 2.10), (0.95, 3.35)),
    (14, ["cowl_upper", "cowl_lower"], "side", (2.20, -0.50, 1.95), (2.40, 3.35)),
    (15, ["chin_inlet"], "side", (1.40, -0.10, 1.22), (1.40, 0.70)),
    (16, ["exhaust_stacks"], "side", (1.62, -0.55, 1.64), (1.68, 3.35)),
    (17, ["gear_main_R", "gear_main_L"], "side", (6.43, -2.38, 0.42), (7.45, 0.35)),
    (18, ["gear_nose"], "side", (2.95, -0.08, 0.32), (2.05, 0.30)),
    (19, ["door_airstair"], "side", (4.72, -0.80, 1.30), (4.20, 0.35)),
    (20, ["door_cargo"], "side", (9.30, -0.80, 1.30), (9.90, 0.35)),
    (21, ["exit_hatch"], "plan", (5.52, 0.76, 2.25), (3.70, 1.25)),
    (22, ["radar_pod"], "plan", (5.10, 3.95, 1.20), (4.20, 4.60)),
]


def bom_rows(parts):
    rows = []
    for num, ids, *_ in ITEMS:
        ps = [parts[i] for i in ids]
        names = [p.name for p in ps]
        notes = []
        for p in ps:
            if p.id.startswith("blade_"):
                continue
            if p.material_note and p.material_note not in notes:
                notes.append(p.material_note)
        qty = sum(p.qty for p in ps if not p.id.startswith("blade_"))
        if len(ps) == 2 and names[0].startswith(("Right ", "Upper ")) and names[1].startswith(("Left ", "Lower ")):
            base = names[0].split(" ", 1)[1]
            pair = "L & R" if names[0].startswith("Right") else "upper & lower"
            desc = f"{base[0].upper() + base[1:]}, {pair}"
        elif ids[0] == "propeller":
            desc = names[0] + ", incl. spinner & hub"
        else:
            desc = " · ".join(names)
        rows.append((str(num), desc, str(qty), "; ".join(notes)))
    return rows


def wrap(s, width, size, font="label"):
    words = s.split(" ")
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if text_width(t, size, font) <= width or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_bom(sh: Sheet, rows, x0, y0, x1):
    cv = sh.cv
    size = 3.0
    cols = [("ITEM", 13.0), ("DESCRIPTION", 158.0), ("QTY", 12.0), ("MATERIAL / NOTE", None)]
    widths = [c[1] for c in cols]
    widths[-1] = (x1 - x0) - sum(widths[:-1])
    xs = np.cumsum([x0] + widths)
    # title bar
    th = 7.5
    cv.rect(x0, y0, x1 - x0, th, lw=W_TABLE, fill=INK)
    sh.text(x0 + 3.0, y0 + th / 2, "PARTS LIST", 3.6, "label", "start", weight=600, fill=PAPER, vcenter=True,
            spacing=0.3)
    sh.text(x1 - 3.0, y0 + th / 2, "MAJOR ITEMS · BALLOON NUMBERS REFER TO THE SIDE AND PLAN VIEWS", 2.3,
            "label", "end", fill=PAPER, vcenter=True)
    y = y0 + th
    hh = 6.5
    for i, (name, _) in enumerate(cols):
        align = "middle" if i in (0, 2) else "start"
        tx = 0.5 * (xs[i] + xs[i + 1]) if align == "middle" else xs[i] + 2.0
        sh.text(tx, y + hh / 2, name, 2.8, "label", align, weight=600, vcenter=True)
    cv.line((x0, y + hh), (x1, y + hh), W_TABLE)
    y += hh
    row_tops = [y]
    line_h = 4.1
    for r in rows:
        cells = []
        for i, s in enumerate(r):
            wmax = widths[i] - 4.0
            cells.append(wrap(s, wmax, size, "mono" if i in (0, 2) else "label"))
        nl = max(len(c) for c in cells)
        h = 3.9 + line_h * nl
        for i, lines in enumerate(cells):
            for k, ln in enumerate(lines):
                yy = y + 1.95 + line_h * (k + 0.5) + 0.05
                if i in (0, 2):
                    sh.text(0.5 * (xs[i] + xs[i + 1]), yy, ln, 3.1, "mono", "middle", vcenter=True)
                else:
                    sh.text(xs[i] + 2.0, yy, ln, size, "label", "start", vcenter=True)
        y += h
        row_tops.append(y)
    # rules
    for yy in row_tops[1:-1]:
        cv.line((x0, yy), (x1, yy), W_TABLE_IN)
    for xx in xs[1:-1]:
        cv.line((xx, y0 + th), (xx, y), W_TABLE_IN)
    cv.rect(x0, y0, x1 - x0, y - y0, lw=W_TABLE)
    return y


def draw_notes(sh: Sheet, x0, y0, x1):
    notes = [
        "Dimensions in millimetres unless stated.",
        "Datum STA 0 is 3,000 mm forward of the firewall (frame 10).",
        "Aircraft shown static on gear, flaps up, doors closed, one blade vertical down.",
        "Principal dimensions per Pilatus published data (span 16,280; length 14,400; height 4,260; "
        "wing area 25.81 m²; tail span 5,200; track 4,530) and the PC-12 NGX POH three-view (wheelbase 3,480).",
        "Engine envelope per EASA TCDS IM.E.008 (PT6E-67XP: 1,870.9 long, Ø481.8). Gear per POH 7-4.",
        "Contours between these anchors are reconstructed estimates (glazing, winglets cross-checked).",
        "Plan view seen from above with the starboard wing at the top; front view seen from ahead, "
        "starboard on the viewer's left. Hidden detail not shown.",
    ]
    cv = sh.cv
    size = 3.0
    sh.text(x0, y0 + 3.8, "NOTES", 3.8, "label", "start", weight=600, spacing=0.3)
    y = y0 + 10.0
    for i, n in enumerate(notes):
        lines = wrap(n, x1 - x0 - 9.0, size)
        sh.text(x0, y, f"{i + 1}.", size, "label", "start")
        for k, ln in enumerate(lines):
            sh.text(x0 + 6.5, y + 4.3 * k, ln, size, "label", "start")
        y += 4.3 * len(lines) + 1.5
    return y


def projection_symbol(sh: Sheet, cx, cy, kind="first", scale=1.0):
    """ISO 5456-2 projection symbol: frustum elevation + end view (two concentric circles).
    In both symbols the frustum's narrow end faces the circles:
      first angle  -> frustum on the left (large end left), circles on the RIGHT
      third angle  -> circles on the LEFT, frustum on the right (large end right)"""
    cv = sh.cv
    D, d, L, gapc = 9.0 * scale, 4.5 * scale, 9.0 * scale, 5.0 * scale
    total = L + gapc + D
    xl = cx - total / 2
    if kind == "first":
        xt0, xc = xl, xl + L + gapc + D / 2
        trap = [(xt0, cy - D / 2), (xt0 + L, cy - d / 2), (xt0 + L, cy + d / 2), (xt0, cy + D / 2)]
    else:
        xc, xt0 = xl + D / 2, xl + D + gapc
        trap = [(xt0, cy - d / 2), (xt0 + L, cy - D / 2), (xt0 + L, cy + D / 2), (xt0, cy + d / 2)]
    cv.path(trap, W_OBJ, closed=True)
    cv.circle(xc, cy, D / 2, w=W_OBJ)
    cv.circle(xc, cy, d / 2, w=W_OBJ)
    cv.line((xl - 1.5, cy), (xl + total + 1.5, cy), W_DIM, (3.0, 0.8, 0.6, 0.8))
    cv.line((xc, cy - D / 2 - 1.5), (xc, cy + D / 2 + 1.5), W_DIM, (3.0, 0.8, 0.6, 0.8))


GA_TITLE = dict(title="PILATUS PC-12 PRO", subtitle="GENERAL ARRANGEMENT", dwg="PC12-GA-001", rev="B",
                scale="1:50", sheet="A1 · 1 OF 1", units="mm", drawn="Claude · loftkit parametric model",
                date="2026-09-24", warning="RECONSTRUCTION FROM PUBLISHED DATA — NOT FOR MANUFACTURE")


def draw_title_block(sh: Sheet, x0, y0, x1, y1, fields=None):
    f = dict(GA_TITLE, **(fields or {}))
    cv = sh.cv
    W_ = x1 - x0
    cv.rect(x0, y0, W_, y1 - y0, lw=W_TABLE)
    # row heights
    hA, hB, hC = 24.0, 14.0, 13.0
    yA, yB, yC, yD = y0, y0 + hA, y0 + hA + hB, y0 + hA + hB + hC
    for yy in (yB, yC, yD):
        cv.line((x0, yy), (x1, yy), W_TABLE_IN)
    # row A: title + projection
    xp = x1 - min(70.0, 0.3 * W_)
    cv.line((xp, yA), (xp, yB), W_TABLE_IN)
    sh.text(x0 + 4.0, yA + 10.5, f["title"], 8.0, "label", "start", weight=700, spacing=0.4)
    sh.text(x0 + 4.0, yA + 19.0, f["subtitle"], 5.0, "label", "start", weight=500, spacing=0.6)
    xpc = 0.5 * (xp + x1)
    projection_symbol(sh, xpc, yA + 9.5, PROJECTION)
    sh.text(xpc, yA + 20.5, ("THIRD" if PROJECTION == "third" else "FIRST") + " ANGLE PROJECTION", 2.5,
            "label", "middle", weight=500)

    def cell(xa, xb, ya, yb, label, value, vsize=4.6, font="mono", weight=500):
        if xa > x0 + 0.1:
            cv.line((xa, ya), (xa, yb), W_TABLE_IN)
        sh.text(xa + 2.0, ya + 3.2, label, 2.2, "label", "start", weight=500)
        sh.text(xa + 2.0, yb - 2.6, value, vsize, font, "start", weight=weight)

    # row B
    k = W_ / 362.0                                   # cell widths designed for the A1 block
    xs = [x0, x0 + 86.0 * k, x0 + 116.0 * k, x0 + 158.0 * k, x0 + 238.0 * k, x1]
    cell(xs[0], xs[1], yB, yC, "DWG NO", f["dwg"], 5.0)
    cell(xs[1], xs[2], yB, yC, "REV", f["rev"], 5.0)
    cell(xs[2], xs[3], yB, yC, "SCALE", f["scale"], 5.0 if len(f["scale"]) <= 5 else 4.2)
    cell(xs[3], xs[4], yB, yC, "SHEET", f["sheet"], 4.6)
    cell(xs[4], xs[5], yB, yC, "UNITS", f["units"], 5.0)
    # row C
    xs2 = [x0, xs[4], x1]
    cell(xs2[0], xs2[1], yC, yD, "DRAWN", f["drawn"], 4.4, "label", 500)
    cell(xs2[1], xs2[2], yC, yD, "DATE", f["date"], 4.6)
    # row D: warning band
    cv.rect(x0, yD, W_, y1 - yD, lw=W_TABLE, fill=INK)
    wsize = 5.0 if W_ > 300 else 3.6
    sh.text(0.5 * (x0 + x1), 0.5 * (yD + y1), f["warning"], wsize,
            "label", "middle", weight=700, fill=PAPER, vcenter=True, spacing=0.5 if W_ > 300 else 0.25)


def draw_scale_bar(sh: Sheet, x0, y0):
    """Graphic scale: 0-5 m at 1:50."""
    cv = sh.cv
    seg = K                                    # 1 m
    for i in range(5):
        fill = INK if i % 2 == 0 else PAPER
        cv.rect(x0 + i * seg, y0, seg, 2.0, lw=W_FINE, fill=fill)
    for i in range(6):
        sh.text(x0 + i * seg, y0 + 6.0, str(i), 2.6, "mono", "middle", tag="scalebar")
    sh.text(x0 + 5 * seg + 3.0, y0 + 6.0, "m", 2.6, "mono", "start", tag="scalebar")
    sh.text(x0, y0 - 2.0, "SCALE 1:50", 2.6, "label", "start", weight=600, tag="scalebar")


def snap_anchor(view, uv, want_ids, radius_m=0.30, margin_px=3):
    """Move a leader anchor onto a visible pixel of the item's parts (nearest to the
    requested point, at least margin_px inside the part's visible region)."""
    from scipy.ndimage import binary_erosion
    fr = view.frame
    idx = [view.part_ids.index(p) for p in want_ids if p in view.part_ids]
    U = view.uv_to_px(np.asarray(uv, float))
    r = int(radius_m / fr.px)
    cx, cy = int(U[0]), int(U[1])
    x0, x1 = max(cx - r, 0), min(cx + r + 1, fr.W)
    y0, y1 = max(cy - r, 0), min(cy + r + 1, fr.H)
    pid = view.pid.reshape(fr.H, fr.W)[y0:y1, x0:x1]
    mask = np.isin(pid, idx)
    if not mask.any():
        return np.asarray(uv, float), None
    er = binary_erosion(mask, iterations=margin_px)
    if er.any():
        mask = er
    yy, xx = np.nonzero(mask)
    d2 = (xx + x0 + 0.5 - U[0]) ** 2 + (yy + y0 + 0.5 - U[1]) ** 2
    k = int(np.argmin(d2))
    P = np.array([[xx[k] + x0 + 0.5, yy[k] + y0 + 0.5]])
    uv2 = fr.px_to_uv(P)[0]
    return uv2, float(np.sqrt(d2[k]) * fr.px)


def draw_particulars(sh: Sheet, N, ext, x0, y0, x1):
    """Leading particulars read from the model (two columns)."""
    cv = sh.cv
    rows = [
        ("Wing span (over winglets)", thou(N["span"] * 1000)),
        ("Length overall", thou((ext["xmax"][0] - ext["xmin"][0]) * 1000)),
        ("Height overall (static)", thou(ext["zmax"][2] * 1000)),
        ("Wing reference area", f"{N['area']:.2f} m²"),
        ("Wing root / tip chord", f"{thou(N['c_root'] * 1000)} / {thou(N['c_tip'] * 1000)}"),
        ("MAC / at butt line", f"{thou(N['mac'] * 1000)} / {thou(N['y_mac'] * 1000)}"),
        ("LEMAC", "STA " + thou(N["lemac"] * 1000)),
        ("Dihedral (reference plane)", f"{N['dihedral_deg']:.1f}°"),
        ("Tailplane span", thou(N["stab_span"] * 1000)),
        ("Wheel track / wheelbase", f"{thou(N['track'] * 1000)} / {thou(N['wheelbase'] * 1000)}"),
        ("Propeller diameter", thou(N["prop_d"] * 1000)),
        ("Propeller ground clearance", thou(N["prop_clear"] * 1000)),
    ]
    th = 7.5
    cv.rect(x0, y0, x1 - x0, th, lw=W_TABLE, fill=INK)
    sh.text(x0 + 3.0, y0 + th / 2, "LEADING PARTICULARS", 3.6, "label", "start", weight=600, fill=PAPER,
            vcenter=True, spacing=0.3)
    sh.text(x1 - 3.0, y0 + th / 2, "mm UNLESS STATED · VALUES READ FROM THE MODEL", 2.3, "label", "end",
            fill=PAPER, vcenter=True)
    half = (len(rows) + 1) // 2
    rh = 7.0
    colw = (x1 - x0) / 2
    y = y0 + th
    for i, (lab, val) in enumerate(rows):
        c = i // half
        r = i % half
        xa = x0 + c * colw
        yy = y + r * rh
        sh.text(xa + 2.5, yy + rh / 2, lab, 3.0, "label", "start", vcenter=True)
        sh.text(xa + colw - 3.0, yy + rh / 2, val, 3.1, "mono", "end", vcenter=True)
    yb = y + half * rh
    for r in range(1, half):
        cv.line((x0, y + r * rh), (x1, y + r * rh), W_TABLE_IN)
    cv.line((x0 + colw, y), (x0 + colw, yb), W_TABLE_IN)
    cv.rect(x0, y0, x1 - x0, yb - y0, lw=W_TABLE)
    return yb


# ============================================================================ checks
def check_layout(sh: Sheet, views):
    """Balloon/label/text overlap and frame checks; returns a list of problems."""
    probs = []
    B = sh.boxes
    for i in range(len(B)):
        x0, y0, x1, y1, t = B[i]
        if t != "zone" and (x0 < FX0 + 0.5 or x1 > FX1 - 0.5 or y0 < FY0 + 0.5 or y1 > FY1 - 0.5):
            probs.append(f"outside frame: {t} {B[i][:4]}")
        for j in range(i + 1, len(B)):
            a0, b0, a1, b1, u = B[j]
            if "zone" in (t, u) or t == u == "table":
                continue
            if x0 < a1 - 0.2 and a0 < x1 - 0.2 and y0 < b1 - 0.2 and b0 < y1 - 0.2:
                if t.startswith("balloon") or u.startswith("balloon") or t in ("dim", "sta", "label") or u in ("dim", "sta", "label"):
                    probs.append(f"overlap: {t} {np.round(B[i][:4], 1)} / {u} {np.round(B[j][:4], 1)}")
    # balloons & dimension text vs geometry lines
    allg = [P for name in sh.geom for P in sh.geom[name]]
    segs = np.vstack([np.hstack([P[:-1], P[1:]]) for P in allg if len(P) > 1])
    for x0, y0, x1, y1, t in B:
        if not (t.startswith("balloon") or t in ("dim", "sta", "label")):
            continue
        if t.startswith("balloon"):
            c = np.array([(x0 + x1) / 2, (y0 + y1) / 2])
            d = seg_dist(c, segs)
            if d.min() < (x1 - x0) / 2 + 0.3:
                probs.append(f"{t} touches geometry (clearance {d.min() - (x1 - x0) / 2:.2f} mm)")
        else:
            # text box vs geometry: sample points inside the box
            xs_ = np.linspace(x0, x1, 6)
            ys_ = np.linspace(y0, y1, 3)
            pts = np.array([(a, b) for a in xs_ for b in ys_])
            dmin = min(seg_dist(p, segs).min() for p in pts)
            if dmin < 0.25:
                probs.append(f"{t} text over geometry at {np.round([x0, y0, x1, y1], 1)}")
    # leaders must not cross each other or pass through another balloon
    L = sh.leaders
    for i in range(len(L)):
        for j in range(i + 1, len(L)):
            if seg_intersect(L[i][0], L[i][1], L[j][0], L[j][1]):
                probs.append(f"leaders {L[i][2]} and {L[j][2]} cross")
    for a, b, n in L:
        for x0, y0, x1, y1, t in B:
            if t.startswith("balloon") and t != f"balloon {n}":
                c = np.array([(x0 + x1) / 2, (y0 + y1) / 2])
                if seg_dist(c, np.array([[*a, *b]])).min() < (x1 - x0) / 2 + 0.5:
                    probs.append(f"leader {n} passes through {t}")
    return probs


def seg_intersect(p1, p2, p3, p4):
    def orient(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    d1, d2 = orient(p3, p4, p1), orient(p3, p4, p2)
    d3, d4 = orient(p1, p2, p3), orient(p1, p2, p4)
    return (d1 * d2 < 0) and (d3 * d4 < 0)


def seg_dist(p, segs):
    a = segs[:, :2]
    b = segs[:, 2:]
    ab = b - a
    t = np.clip(np.sum((p - a) * ab, 1) / np.maximum(np.sum(ab * ab, 1), 1e-12), 0, 1)
    q = a + t[:, None] * ab
    return np.hypot(*(p - q).T)


# ============================================================================ main
def build(parts=None, verbose=True):
    t0 = time.time()
    if parts is None:
        from model.build import build_parts
        parts = build_parts()
        if verbose:
            print(f"model built ({time.time() - t0:.1f}s)", flush=True)
    views, prep = hlr.render_all(parts, verbose=verbose)
    t1 = time.time()
    N = model_numbers()
    ext = extreme_points(prep)
    sh = Sheet()
    draw_frame(sh)
    draw_side(sh, views["side"], N, ext)
    draw_plan(sh, views["plan"], N, ext)
    draw_front(sh, views["front"], N, ext)
    # view titles
    view_title(sh, side_xy(7.6, 0)[0], YG + 39.0, "SIDE VIEW", "SEEN FROM PORT · NOSE LEFT")
    view_title(sh, plan_xy(7.6, 0)[0], YC + K * 8.14 + 22.5, "PLAN VIEW", "SEEN FROM ABOVE · STARBOARD WING UP")
    view_title(sh, XF, YG + 21.5, "FRONT VIEW", "SEEN FROM AHEAD · STARBOARD ON THE LEFT")
    # balloons (anchors snapped onto a visible pixel of the item's parts)
    maps = {"side": side_xy, "plan": plan_xy, "front": front_uv}
    snaps = []
    for num, ids, vname, anc, bpos in ITEMS:
        v = views[vname]
        uv = v.project(np.array([anc]))[0][:2]
        uv2, moved = snap_anchor(v, uv, ids)
        snaps.append((num, moved))
        a = maps[vname](uv2[0], uv2[1])
        c = maps[vname](*bpos)
        sh.balloon(c, a, num)
    # right-hand column: parts list, leading particulars, scale bar, notes, title block
    rx0, rx1 = 463.0, FX1 - 6.0
    rows = bom_rows(parts)
    ybom = draw_bom(sh, rows, rx0, 166.0, rx1)
    ypart = draw_particulars(sh, N, ext, rx0, ybom + 8.0, rx1)
    t_top = FY1 - 6.0 - 71.0
    draw_title_block(sh, rx0, t_top, rx1, FY1 - 6.0)
    probe = Sheet()
    notes_h = draw_notes(probe, rx0, 0.0, rx1)
    yn0 = t_top - 5.0 - notes_h
    draw_notes(sh, rx0, yn0, rx1)
    draw_scale_bar(sh, rx0 + 2.0, 0.5 * (ypart + yn0) + 1.0)
    t2 = time.time()
    probs = check_layout(sh, views)
    os.makedirs(OUT_DIR, exist_ok=True)
    svg = sh.cv.to_svg(title="PC-12 General Arrangement",
                       desc="PC12-GA-001 rev A, 1:50, A1. Reconstruction from published data, not for manufacture.",
                       font_import="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;500;600;700"
                                   "&family=IBM+Plex+Mono:wght@400;500&display=swap")
    svg_path = os.path.join(OUT_DIR, "pc12_ga.svg")
    with open(svg_path, "w") as f:
        f.write(svg)
    pdf_path = os.path.join(OUT_DIR, "pc12_ga.pdf")
    sh.cv.to_pdf(pdf_path, title="PC-12 General Arrangement (PC12-GA-001 rev A)", author="Claude",
                 subject="Reconstruction from published data - not for manufacture")
    t3 = time.time()
    if verbose:
        print(f"sheet composed ({t2 - t1:.1f}s), written ({t3 - t2:.1f}s): {svg_path} "
              f"{os.path.getsize(svg_path) / 1e6:.2f} MB, {pdf_path} {os.path.getsize(pdf_path) / 1e6:.2f} MB")
        for num, moved in snaps:
            if moved is None:
                print(f"  balloon {num}: NO visible pixel of the item near its anchor")
            elif moved > 0.05:
                print(f"  balloon {num}: anchor snapped {moved * 1000:.0f} mm onto the part")
        for p in probs:
            print("  CHECK:", p)
        print(f"total {time.time() - t0:.1f}s")
    return dict(sheet=sh, views=views, prep=prep, numbers=N, ext=ext, problems=probs)


def main():
    """Regenerate every sheet: the A1 general arrangement and the A2 sections sheet."""
    t0 = time.time()
    build()
    from drawing import sections
    sections.build()
    print(f"all sheets regenerated in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
