"""
Sheet L4 -- GENERAL ARRANGEMENT - LAYOUT: wing, empennage, landing gear, radar pod and propeller positions,
drawn FROM THE PARAMETERS of model/wing.py (planform, dihedral / twist, winglet sections), model/empennage.py
(fin / rudder / dorsal / tailplane / bullet / strake tables), model/gear.py (+ bays.py), model/details.py (radar
pod) and model/fuselage.py (OML control lines) -- never from the mesh.

    python3 -m drawing.master L4          (or: python3 -m drawing.layout_sheet)

Views (first-angle, 1:50): side view seen from port, plan below it, front view to its right.  Key position
dimensions: wing LE / TE at the root and the tip rib, MAC and LEMAC, dihedral, winglet, tail positions, axles,
wheelbase / track, propeller disc.  Tables: layout parameters, deviations of the parameters from the registered
Pilatus drawing (our numbers: OURS, D DWG = ours - drawing, REV A D DWG = the model before this refit), Stage-3
hand-over notes.  The overlay variant (refs/cache/overlays/L4_overlay.*, git-ignored) adds the Pilatus drawing
in red and photo-derived marks in blue.

The drawing measurements (reference()) are made at run time from the git-ignored refs/cache (refs/mbp.py); only
the deviations appear on the clean sheet.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from drawing import master as M  # noqa: E402
from drawing.master import (INK, GRID, MUTED, BLUE, W_OBJ, W_FINE, W_DIM, W_THIN, W_GRID, CHAIN,  # noqa: E402
                            PHANTOM, table, notes, view_title, scale_bar, side_view, plan_view, front_view)
from model import fuselage as F  # noqa: E402
from model import wing as W  # noqa: E402
from model import empennage as E  # noqa: E402
from model import gear as G  # noqa: E402
from model import details as D  # noqa: E402
from model import powerplant as PP  # noqa: E402
from model.lifting import cos_pts  # noqa: E402

SHEET = dict(id="L4", title="GENERAL ARRANGEMENT - LAYOUT",
             subtitle="GENERAL ARRANGEMENT - LAYOUT (WING, TAIL, GEAR)", size="A1", scale="1:50", rev="A", order=40)

K = 20.0                      # sheet mm per model metre at 1:50
HID = (1.6, 0.9)              # hidden-line dash
LIGHT = "#34434B"
XC = cos_pts(90)

# Rev A = the model before this Stage-2 refit (model/wing.py, empennage.py, gear.py, bays.py, details.py at
# commit 5a0702e), for the "REV A D DWG" column.  Values computed from those modules.
REV_A = {
    "wing_le_1.0": 5.2366, "wing_te_1.0": 7.2873, "wing_le_4.0": 5.3412, "wing_te_4.0": 6.9737,
    "wing_le_7.4": 5.4596, "wing_te_7.4": 6.6183, "wing_up_4.0": 1.3649, "wing_lo_4.0": 1.1123,
    "wing_up_7.0": 1.5576, "wing_lo_7.0": 1.3852, "semi": 7.8570, "c_root": 2.1900, "mac": 1.7033, "lemac": 5.3235,
    "dihedral": 4.5, "inc_WR1": 1.64, "inc_WR2": -0.12, "inc_WR3": -0.54, "inc_WR4": -0.82,
    "winglet_top_z": 1.8604, "winglet_y": 8.1407, "winglet_cant": 30.0,
    "stab_le_1.0": 13.6093, "stab_te_1.0": 14.6206, "stab_le_2.27": 13.9312, "stab_te_2.27": 14.6722,
    "elev_hinge_1.0": 14.3172, "stab_z": 4.125, "bullet_x0": 12.95, "bullet_x1": 14.79,
    "fin_le_3.4": 12.6863, "fin_le_3.8": 13.0049, "fin_te_2.609": 14.4775, "fin_te_3.919": 14.6770,
    "rud_hinge_2.609": 13.6059, "rud_hinge_3.919": 14.1092, "fin_t": 0.1022,
    "nose_axle": 2.9500, "main_axle": 6.4300, "track": 4.53, "prop_tilt": 0.0, "prop_clear": 0.32,
    "pod_x0": 4.8777, "pod_y": 3.90, "pod_z": 1.2164, "pod_r": 0.175,
}


# ============================================================================================ parameter geometry
def wing_section_pts(y, n=None):
    """Closed section loop (N, 3) of the starboard wing at butt line y (parameters: wing.section_at)."""
    s = W.section_at(y)
    return np.vstack([s.lower(XC[::-1]), s.upper(XC[1:])])


def wing_front_silhouette(ys):
    """Upper / lower front-view silhouette WL of the wing panel at butt lines ys."""
    up, lo = [], []
    for y in ys:
        s = W.section_at(y)
        up.append(s.upper(XC)[:, 2].max())
        lo.append(s.lower(XC)[:, 2].min())
    return np.array(up), np.array(lo)


def winglet_geom():
    """Winglet sections (wing.winglet_sections) -> plan LE / TE, side LE / TE, front upper / lower outlines."""
    secs = W.winglet_sections(40, 30)
    le = np.array([s.point(np.array(0.0), np.array(0.0)) for s in secs])
    te = np.array([s.point(np.array(1.0), np.array(0.0)) for s in secs])
    up, lo = [], []
    for s in secs:
        U, L = s.upper(XC), s.lower(XC)
        up.append(U[np.argmax(U @ s.e_t)])
        lo.append(L[np.argmin(L @ s.e_t)])
    top = np.vstack([secs[-1].lower(XC[::-1]), secs[-1].upper(XC[1:])])
    return dict(le=le, te=te, up=np.array(up), lo=np.array(lo), top=top, secs=secs)


def wing_root_y():
    return float(F.half_w(6.0))


def fin_crown_z():
    """WL where the fin LE line meets the fuselage crown."""
    zs = np.linspace(2.3, 3.0, 701)
    d = F.z_top(E.fin_le(zs)) - zs
    return float(zs[np.argmin(np.abs(d))])


def fin_keel_x(z):
    """Station aft of which the fin section at WL z lies below the tail-cone keel (the exposed ventral part)."""
    xs = np.linspace(11.0, F.STA["tail_end"], 600)
    below = F.z_bot(xs) > z
    return float(xs[np.argmax(below)]) if below.any() else F.STA["tail_end"]


def strake_polygon():
    """Side-view outline of the strake: root line, tip line, aft edge (x, z)."""
    (r0x, r0z), (r1x, r1z) = E.STRAKE_ROOT
    (t0x, t0z), (t1x, t1z) = E.STRAKE_TIP
    return np.array([(r0x, r0z), (r1x, r1z), (t1x, t1z), (t0x, t0z), (r0x, r0z)])


def mac_numbers():
    m, ym, lemac = W.mac()
    return m, ym, lemac


def dorsal_plan_halfwidth(xs):
    """Plan-view half-width envelope of the dorsal fin (max over its sections)."""
    zs = np.linspace(2.45, float(E._dorsal_curve()[-1, 1]) - 0.01, 40)
    w = np.zeros_like(xs)
    for z in zs:
        s = E.dorsal_section(z)
        xc = (xs - s.le[0]) / s.chord
        ok = (xc >= 0) & (xc <= 1) & (F.z_top(xs) < z)
        w = np.where(ok, np.maximum(w, s.chord * s.airfoil.upper(np.clip(xc, 0, 1))), w)
    return w


# ============================================================================================ reference (private)
def reference():
    """Measurements of the registered Pilatus drawing (git-ignored refs/cache).  Returns a dict of values in model
    metres / degrees keyed like REV_A.  Used for the deviation column and the overlay only."""
    d = M.mbp_data()

    def cross(key, axis, val, lo, hi, kinds=("outline",)):
        out = []
        for it in d[key]:
            if it["kind"] not in kinds:
                continue
            P = it["pts"]
            a = P[:, axis] - val
            k = np.where(np.sign(a[:-1]) * np.sign(a[1:]) <= 0)[0]
            for j in k:
                if a[j] == a[j + 1]:
                    continue
                t = a[j] / (a[j] - a[j + 1])
                o = float((P[j] + t * (P[j + 1] - P[j]))[1 - axis])
                if lo <= o <= hi:
                    out.append(o)
        return sorted(out)

    R = {}
    for y in (1.0, 4.0, 7.4):                                   # plan, both wings averaged
        le = np.mean([min(cross("plan", 1, s * y, 5.0, 6.0)) for s in (1, -1)])
        te = np.mean([max(cross("plan", 1, s * y, 6.5, 7.7)) for s in (1, -1)])
        R[f"wing_le_{y}"], R[f"wing_te_{y}"] = le, te
    for y in (4.0, 7.0):                                        # front, port side (no pod)
        c = cross("front", 0, -y, 0.8, 2.0)
        R[f"wing_lo_{y}"], R[f"wing_up_{y}"] = min(c), max(c)
    ys = np.linspace(1.3, 7.3, 13)
    mids = [np.mean([min(cross("front", 0, -y, 0.8, 2.0)), max(cross("front", 0, -y, 0.8, 2.0))]) for y in ys]
    R["dihedral"] = math.degrees(math.atan(np.polyfit(ys, mids, 1)[0]))
    R["winglet_top_z"] = max(max(cross("front", 0, -y, 1.8, 2.3)) for y in np.linspace(7.95, 8.04, 10))
    R["winglet_y"] = max(abs(v) for y in (-1,) for v in cross("front", 1, 2.10, -8.3, -7.5))
    # winglet mid-line angle (front, port, y 7.85..8.0)
    yy = np.linspace(7.85, 8.0, 6)
    mm = [np.mean(cross("front", 0, -y, 1.75, 2.2)[:2]) for y in yy]
    R["winglet_cant"] = 90.0 - math.degrees(math.atan(np.polyfit(yy, mm, 1)[0]))
    for n, y in (("WR1", 0.935), ("WR2", 5.557), ("WR3", 6.658), ("WR4", 7.395)):
        P = np.vstack([ln["pts"] for ln in d["sections"][n]["lines"] if ln["kind"] == "outline"])
        le, te = P[np.argmin(P[:, 0])], P[np.argmax(P[:, 0])]
        R[f"inc_{n}"] = math.degrees(math.atan2(le[1] - te[1], te[0] - le[0]))
    # tailplane (plan, both halves) and front
    for y in (1.0, 2.27):
        R[f"stab_le_{y}"] = np.mean([min(cross("plan", 1, s * y, 12.9, 13.9)) for s in (1, -1)])
        R[f"stab_te_{y}"] = np.mean([max(cross("plan", 1, s * y, 14.0, 14.6)) for s in (1, -1)])
    c = cross("front", 0, -1.0, 3.9, 4.3)
    R["stab_z"] = 0.5 * (min(c) + max(c))
    R["stab_t_1.0"] = max(c) - min(c)
    hf = [ln["pts"] for ln in d["sections"]["HF1"]["lines"] if ln["kind"] == "centerline"
          and abs(ln["pts"][0, 0] - ln["pts"][-1, 0]) < 1e-3]
    R["elev_hinge_1.0"] = float(np.mean([p[0, 0] for p in hf]))
    R["bullet_x0"] = float(d["sections"]["HF1"]["le_x"])
    R["bullet_x1"] = next(ch["measured"] for ch in d["meta"]["checks"] if ch["name"].startswith("Aft-most station"))
    R["bullet_top"] = max(cross("side", 0, 13.3, 3.8, 4.4))
    # fin (side view)
    for z in (3.4, 3.8):
        R[f"fin_le_{z}"] = min(cross("side", 1, z, 12.2, 13.2))
    for n, z in (("VF1", 2.609), ("VF2", 3.919)):
        lines = [ln["pts"] for ln in d["sections"][n]["lines"] if ln["kind"] == "outline"]
        allp = np.vstack(lines)
        R[f"fin_te_{z}"] = float(allp[:, 0].max())
        R[f"fin_le_sec_{z}"] = float(allp[:, 0].min())
        rud = min(lines, key=lambda P: -P[:, 0].min())           # rudder piece = the one starting furthest aft
        nose = float(rud[:, 0].min())
        r = 0.5 * float(rud[:, 1].max() - rud[:, 1].min())
        R[f"rud_hinge_{z}"] = nose + r
        R[f"fin_t_{z}"] = float(allp[:, 1].max() - allp[:, 1].min()) / (R[f"fin_te_{z}"] - R[f"fin_le_sec_{z}"])
    # dorsal: FR38 / FR40 half-width and top
    for n in ("FR38", "FR40"):
        for ln in d["sections"][n]["lines"]:
            P = ln["pts"]
            if ln["kind"] == "outline" and P[:, 1].max() > 2.6 and np.abs(P[:, 0]).max() < 0.2:
                R[f"dorsal_hw_{n}"] = float(np.abs(P[:, 0]).max())
                R[f"dorsal_top_{n}"] = float(P[:, 1].max())
    # strakes: FR38 / FR40 tip points (lowest outline point with |y| in 0.3..0.7)
    for n in ("FR38", "FR40"):
        best = None
        for ln in d["sections"][n]["lines"]:
            P = ln["pts"]
            if ln["kind"] != "outline":
                continue
            m = (np.abs(P[:, 0]) > 0.3) & (np.abs(P[:, 0]) < 0.7) & (P[:, 1] < 1.95)
            if m.any():
                q = P[m][np.argmin(P[m][:, 1])]
                if best is None or q[1] < best[1]:
                    best = q
        R[f"strake_tip_{n}"] = (abs(float(best[0])), float(best[1]))
    # gear, pod, prop
    chk = {ch["name"]: ch["measured"] for ch in d["meta"]["checks"]}
    R["nose_axle"] = chk["Nose wheel axle station"]
    R["main_axle"] = chk["Main wheel axle station"]
    R["track"] = chk["Track, front (dimension 4530)"]
    R["prop_tilt"] = chk["Propeller disc tilt from vertical (side; + = top forward)"]
    R["prop_clear"] = chk["Prop ground clearance, side"]
    R["span"] = chk["Span, plan (over winglets)"]
    xs = cross("plan", 1, 7.635, 4.9, 5.6)
    R["pod_x0"] = min(xs)
    zs = cross("front", 0, 7.635, 1.5, 2.0)
    R["pod_z"] = 0.5 * (min(zs) + max(zs))
    R["pod_r"] = 0.5 * (max(zs) - min(zs))
    ys_ = cross("front", 1, 1.76, 7.46, 7.9)
    R["pod_y"] = 0.5 * (min(ys_) + max(ys_))
    return R


def ours():
    """Our parameter values keyed like reference()."""
    O = {}
    for y in (1.0, 4.0, 7.4):
        O[f"wing_le_{y}"], O[f"wing_te_{y}"] = float(W.x_le(y)), float(W.x_te(y))
    for y in (4.0, 7.0):
        u, l_ = wing_front_silhouette([y])
        O[f"wing_up_{y}"], O[f"wing_lo_{y}"] = float(u[0]), float(l_[0])
    O["dihedral"] = math.degrees(W.DIHEDRAL)
    wg = winglet_geom()
    O["winglet_top_z"] = float(max(wg["up"][:, 2].max(), wg["top"][:, 2].max()))
    O["winglet_y"] = float(max(wg["lo"][:, 1].max(), wg["top"][:, 1].max()))
    O["winglet_cant"] = math.degrees(W.WL_CANT)
    for n, y in (("WR1", 0.935), ("WR2", 5.557), ("WR3", 6.658), ("WR4", 7.395)):
        O[f"inc_{n}"] = math.degrees(float(W.twist(y)))
    for y in (1.0, 2.27):
        O[f"stab_le_{y}"], O[f"stab_te_{y}"] = float(E.stab_le(y)), float(E.stab_te(y))
    s = E.stab_section(1.0)
    O["stab_z"] = E.STAB_Z
    O["stab_t_1.0"] = float(s.upper(XC)[:, 2].max() - s.lower(XC)[:, 2].min())
    O["elev_hinge_1.0"] = float(s.le[0] + E.ELEV_XH * s.chord)
    O["bullet_x0"], O["bullet_x1"] = E.BULLET_X
    O["bullet_top"] = max(b[1] for b in E.BULLET)
    for z in (3.4, 3.8):
        O[f"fin_le_{z}"] = float(E.fin_le(z))
    for z in (2.609, 3.919):
        O[f"fin_te_{z}"] = float(E.fin_te(z))
        O[f"fin_le_sec_{z}"] = float(E.fin_le(z))
        O[f"rud_hinge_{z}"] = float(E.fin_le(z) + E.RUD_XH * (E.fin_te(z) - E.fin_le(z)))
        O[f"fin_t_{z}"] = float(E.fin_section(z).airfoil.thickness(np.linspace(0, 1, 401)).max())
    for n, x in (("FR38", F.FRAMES["FR38"]), ("FR40", F.FRAMES["FR40"])):
        zs = np.linspace(2.4, 3.4, 400)
        best_w, top = 0.0, 0.0
        for z in zs:
            if z <= float(F.z_top(x)):
                continue
            sec = E.dorsal_section(z)
            xc = (x - sec.le[0]) / sec.chord
            if 0 <= xc <= 1:
                w = sec.chord * float(sec.airfoil.upper(np.array(xc)))
                best_w = max(best_w, w)
                if w > 0.005:
                    top = z
        O[f"dorsal_hw_{n}"], O[f"dorsal_top_{n}"] = best_w, top
        r, t = E.strake_frame(x)
        O[f"strake_tip_{n}"] = (float(t[1]), float(t[2]))
    O["nose_axle"], O["main_axle"] = float(G.NOSE_AXLE[0]), float(G.MAIN_AXLE[0])
    O["track"] = G.TRACK
    O["prop_tilt"] = 0.0
    O["prop_clear"] = F.PROP_AXIS_Z - PP.PROP_R
    O["span"] = W.SPAN_TOTAL
    O["pod_x0"], O["pod_z"], O["pod_r"], O["pod_y"] = D.POD_X_TIP, D.POD_Z, D.POD_R, D.POD_Y
    return O


# ============================================================================================ drawing helpers
def _relax(vals, gap):
    v = np.array(vals, float)
    order = np.argsort(v)
    s = v[order].copy()
    for _ in range(300):
        moved = False
        for i in range(1, len(s)):
            dd = s[i] - s[i - 1]
            if dd < gap - 1e-6:
                sh = 0.5 * (gap - dd)
                s[i - 1] -= sh
                s[i] += sh
                moved = True
        if not moved:
            break
    out = np.empty_like(s)
    out[order] = s
    return out


def ordinates(ds, v, items, row_y, up=True, color=INK, size=2.2, gap=3.0):
    """Station ordinates: items = [(x, b_feature, text)] in the view's (a, b) coordinates; leaders from the
    features to a label row at sheet y = row_y; text reads upward (above) or downward (below)."""
    X = [v.pt(a, b)[0] for a, b, _ in items]
    Xt = _relax(X, gap)
    for (a, b, s), xa, xt in zip(items, X, Xt):
        _, yf = v.pt(a, b)
        if up:
            yj = row_y + 5.0
            ds.cv.path([(xa, yf - 0.8), (xa, yj), (xt, row_y + 2.0), (xt, row_y + 0.8)], W_DIM, color=color)
            ds.text(xt, row_y, s, size, "mono", "start", rot=-90, vcenter=True, fill=color, tag="ordinate")
        else:
            yj = row_y - 5.0
            ds.cv.path([(xa, yf + 0.8), (xa, yj), (xt, row_y - 2.0), (xt, row_y - 0.8)], W_DIM, color=color)
            ds.text(xt, row_y, s, size, "mono", "end", rot=-90, vcenter=True, fill=color, tag="ordinate")


def wl_ticks(ds, v, entries, edge_a, side="left", size=2.2, gap=2.9, color=INK):
    """WL ordinates at the view's edge: entries = [(z, text)] (side view: edge_a = station of the edge)."""
    X, _ = v.pt(edge_a, 0.0)
    Y = [v.pt(edge_a, z)[1] for z, _ in entries]
    Yt = _relax(Y, gap)
    sg = -1 if side == "left" else 1
    for (z, s), ya, yt in zip(entries, Y, Yt):
        ds.cv.path([(X, ya), (X + sg * 3.0, ya), (X + sg * 4.5, yt), (X + sg * 5.5, yt)], W_DIM, color=color)
        ds.text(X + sg * 6.2, yt, s, size, "mono", "end" if side == "left" else "start", vcenter=True, fill=color,
                tag="wl")


def label(ds, v, a, b, s, dx=1.0, dy=-1.0, size=2.2, anchor="start", color=MUTED, weight=400, font="label"):
    X, Y = v.pt(a, b)
    ds.text(X + dx, Y + dy, s, size, font, anchor, fill=color, tag="lbl", weight=weight)


def leader_label(ds, v, a, b, s, off=(8.0, -6.0), size=2.2, color=INK, lines=None):
    X, Y = v.pt(a, b)
    tx, ty = X + off[0], Y + off[1]
    ds.cv.line((X, Y), (tx, ty), W_DIM, color=color)
    ds.cv.line((tx, ty), (tx + (2.0 if off[0] >= 0 else -2.0), ty), W_DIM, color=color)
    anc = "start" if off[0] >= 0 else "end"
    x2 = tx + (2.6 if off[0] >= 0 else -2.6)
    for i, t in enumerate([s] + list(lines or [])):
        ds.text(x2, ty + i * 1.3 * size, t, size, "label", anc, vcenter=True, fill=color, tag="leader",
                weight=600 if i == 0 else 400)


def tyre_side(ds, v, c, tyre, dash=None):
    R = tyre["R"]
    a = np.linspace(0, 2 * np.pi, 73)
    ds.cv.path(v.pts(np.c_[c[0] + R * np.cos(a), c[2] + R * np.sin(a)]), W_OBJ, dash, closed=True)
    r = tyre["rim"]
    ds.cv.path(v.pts(np.c_[c[0] + r * np.cos(a), c[2] + r * np.sin(a)]), W_FINE, dash, closed=True)


def rect_pts(a0, b0, a1, b1):
    return np.array([(a0, b0), (a1, b0), (a1, b1), (a0, b1)])


# ============================================================================================ views
def draw_side(ds, v):
    cv = ds.cv
    x0, x1 = F.STA["cowl_front"], F.STA["tail_end"]
    xs = np.linspace(x0, x1, 900)
    # ground and reference lines
    cv.line(v.pt(-0.1, 0.0), v.pt(15.1, 0.0), W_FINE)
    for xg in np.arange(-0.1, 15.1, 0.25):
        cv.line(v.pt(xg, 0.0), v.pt(xg - 0.12, -0.12), W_GRID, color=MUTED)
    cv.line(v.pt(0.2, F.PROP_AXIS_Z), v.pt(3.2, F.PROP_AXIS_Z), W_GRID, CHAIN, color=MUTED)
    # fuselage
    cv.path(v.pts(np.c_[xs, F.z_top(xs)]), W_OBJ)
    cv.path(v.pts(np.c_[xs, F.z_bot(xs)]), W_OBJ)
    cv.line(v.pt(x0, float(F.z_bot(x0))), v.pt(x0, float(F.z_top(x0))), W_FINE)
    a, b = F.SPINNER_SHAPE
    t = np.linspace(0, 1, 60)
    sx = F.STA["spinner_tip"] + (x0 - F.STA["spinner_tip"]) * t
    sr = F.SPINNER_R * (1 - (1 - t) ** a) ** b
    cv.path(v.pts(np.c_[np.r_[sx, sx[::-1]], np.r_[F.PROP_AXIS_Z + sr, (F.PROP_AXIS_Z - sr)[::-1]]]), W_OBJ)
    # propeller disc (edge-on) at the pitch-change plane
    cv.line(v.pt(PP.PROP_X, F.PROP_AXIS_Z - PP.PROP_R), v.pt(PP.PROP_X, F.PROP_AXIS_Z + PP.PROP_R), W_FINE, PHANTOM)
    # wing (port, near side): root section at the fuselage side, tip rib section, LE / TE loci, winglet
    yr = wing_root_y()
    root = wing_section_pts(yr)
    tip = wing_section_pts(W.SEMI)
    cv.path(v.pts(root[:, [0, 2]]), W_OBJ, closed=True)
    cv.path(v.pts(tip[:, [0, 2]]), W_FINE, closed=True)
    ys = np.linspace(yr, W.SEMI, 40)
    le = np.array([W.section_at(y).point(np.array(0.0), np.array(0.0)) for y in ys])
    te = np.array([W.section_at(y).point(np.array(1.0), np.array(0.0)) for y in ys])
    cv.path(v.pts(le[:, [0, 2]]), W_FINE)
    cv.path(v.pts(te[:, [0, 2]]), W_FINE)
    wg = winglet_geom()
    cv.path(v.pts(wg["le"][:, [0, 2]]), W_OBJ)
    cv.path(v.pts(wg["te"][:, [0, 2]]), W_OBJ)
    cv.path(v.pts(wg["top"][:, [0, 2]]), W_OBJ, closed=True)
    # radar pod (starboard tip, behind the fuselage -> hidden)
    prof = np.array(D.radar_pod_profile())
    pod = np.r_[np.c_[prof[:, 0], D.POD_Z + prof[:, 1]], np.c_[prof[::-1, 0], D.POD_Z - prof[::-1, 1]]]
    cv.path(v.pts(pod), W_FINE, HID, closed=True)
    # empennage: fin + rudder + tab, dorsal, bullet, tailplane root section, strakes
    zc = fin_crown_z()
    zt = E.BULLET[8][2]                                     # bullet bottom
    cv.line(v.pt(E.fin_le(zc), zc), v.pt(E.fin_le(zt), zt), W_OBJ)
    cv.line(v.pt(*E.FIN_TE[0]), v.pt(E.fin_te(zt + 0.02), zt + 0.02), W_OBJ)
    (vx0, vz0), (vx1, vz1) = E.VENTRAL_EDGE
    vxs = np.linspace(vx0, vx1, 60)
    vzs = vz0 + (vz1 - vz0) * (vxs - vx0) / (vx1 - vx0)
    vis = vzs < F.z_bot(vxs)
    for seg in _runs(vis):
        cv.path(v.pts(np.c_[vxs[seg], vzs[seg]]), W_OBJ)
    for z in E.RUD_Z:                                       # rudder top / bottom edges (hinge line -> TE)
        s = E.fin_section(z)
        cv.line(v.pt(s.le[0] + (E.RUD_XH - 0.05) * s.chord, z), v.pt(s.le[0] + s.chord, z), W_FINE)
    hz = np.array(E.RUD_Z)
    hx = [E.fin_le(z) + E.RUD_XH * (E.fin_te(z) - E.fin_le(z)) for z in hz]
    cv.line(v.pt(hx[0], hz[0] - 0.08), v.pt(hx[1], hz[1] + 0.08), W_THIN, CHAIN)
    gx = [E.fin_le(z) + (E.RUD_XH - 0.05) * (E.fin_te(z) - E.fin_le(z)) for z in hz]
    cv.line(v.pt(gx[0], hz[0]), v.pt(gx[1], hz[1]), W_FINE)
    t0, t1, tx = E.RUD_TAB
    tab = [(E.fin_le(z) + tx * (E.fin_te(z) - E.fin_le(z)), z) for z in (t0, t1)]
    cv.path(v.pts([(E.fin_te(t0), t0), tab[0], tab[1], (E.fin_te(t1), t1)]), W_FINE)
    dc = E._dorsal_curve()
    dl = np.r_[[[E.DORSAL_X0, E.DORSAL_Z0]], dc]
    cv.path(v.pts(dl), W_OBJ)
    B = np.array(E.BULLET)
    cv.path(v.pts(np.r_[B[:, [0, 1]], B[::-1][:, [0, 2]]]), W_OBJ, closed=True)
    s0 = E.stab_section(0.15)
    stab = np.vstack([s0.lower(XC[::-1]), s0.upper(XC[1:])])
    cv.path(v.pts(stab[:, [0, 2]]), W_FINE, closed=True)
    xh = s0.le[0] + E.ELEV_XH * s0.chord
    cv.line(v.pt(xh, E.STAB_Z - 0.07), v.pt(xh, E.STAB_Z + 0.07), W_THIN)
    cv.path(v.pts(strake_polygon()), W_OBJ)
    # gear
    tyre_side(ds, v, G.MAIN_AXLE, G.MAIN_TYRE)
    tyre_side(ds, v, G.NOSE_AXLE, G.NOSE_TYRE)
    T, L, A = G.MAIN_TRUNNION, G.MAIN_LINK_PIVOT, G.MAIN_AXLE
    cv.path(v.pts([(T[0], T[2]), (L[0], L[2]), (A[0], A[2])]), W_OBJ)
    (s1x, s1z), (s2x, s2z) = G.MAIN_SHOCK
    cv.path(v.pts([(s1x, s1z), (s2x, s2z)]), W_FINE)
    cv.path(v.pts([(G.NOSE_PIVOT[0], G.NOSE_PIVOT[2]), (G.NOSE_FORK[0], G.NOSE_FORK[2]),
                   (G.NOSE_AXLE[0], G.NOSE_AXLE[2])]), W_OBJ)
    a_, b_ = G.NOSE_BRACE
    cv.path(v.pts([(a_[0], a_[2]), (b_[0], b_[2])]), W_FINE)
    for p in (T, L, A, G.NOSE_PIVOT, G.NOSE_AXLE):
        X, Y = v.pt(p[0], p[2])
        cv.circle(X, Y, 0.6, w=W_FINE)


def draw_plan(ds, v):
    cv = ds.cv
    x0, x1 = F.STA["cowl_front"], F.STA["tail_end"]
    xs = np.linspace(x0, x1, 900)
    cv.line(v.pt(0.1, 0.0), v.pt(15.1, 0.0), W_THIN, CHAIN)
    X, Y = v.pt(0.1, 0.0)
    ds.text(X - 1.2, Y, "CL", 2.4, "label", "end", vcenter=True, weight=600, tag="cl")
    hw = F.half_w(xs)
    B = np.array(E.BULLET)
    under = (xs >= E.BULLET_X[0]) & (hw <= np.interp(xs, B[:, 0], B[:, 3]) + 1e-3) | \
        (xs >= np.array([E.stab_le(h) for h in hw]))
    for sg in (1, -1):
        for seg in _runs(~under):
            cv.path(v.pts(np.c_[xs[seg], sg * hw[seg]]), W_OBJ)
        for seg in _runs(under):
            cv.path(v.pts(np.c_[xs[seg], sg * hw[seg]]), W_FINE, HID)
    cv.line(v.pt(x0, -F.SPINNER_R), v.pt(x0, F.SPINNER_R), W_FINE)
    cv.line(v.pt(x1, -float(F.half_w(x1))), v.pt(x1, float(F.half_w(x1))), W_FINE, HID)
    a, b = F.SPINNER_SHAPE
    t = np.linspace(0, 1, 60)
    sx = F.STA["spinner_tip"] + (x0 - F.STA["spinner_tip"]) * t
    sr = F.SPINNER_R * (1 - (1 - t) ** a) ** b
    cv.path(v.pts(np.c_[np.r_[sx, sx[::-1]], np.r_[sr, -sr[::-1]]]), W_OBJ)
    cv.line(v.pt(PP.PROP_X, -PP.PROP_R), v.pt(PP.PROP_X, PP.PROP_R), W_FINE, PHANTOM)
    # wing planform (both halves)
    yr = wing_root_y()
    ys = np.linspace(yr, W.SEMI, 120)
    wg = winglet_geom()
    for sg in (1, -1):
        cv.path(v.pts(np.c_[W.x_le(ys), sg * ys]), W_OBJ)
        cv.path(v.pts(np.c_[W.x_te(ys), sg * ys]), W_OBJ)
        cv.line(v.pt(float(W.x_le(W.SEMI)), sg * W.SEMI), v.pt(float(W.x_te(W.SEMI)), sg * W.SEMI), W_FINE)
        # flap (LE hidden under the shroud) / aileron / tab
        fy = np.linspace(*W.Y_FLAP, 40)
        fl = W.x_le(fy) + W.FLAP_X_LO * W.chord(fy)
        cv.path(v.pts(np.c_[fl, sg * fy]), W_FINE, HID)
        for y in W.Y_FLAP:
            cv.line(v.pt(float(W.x_le(y) + W.FLAP_X_LO * W.chord(y)), sg * y), v.pt(float(W.x_te(y)), sg * y), W_FINE,
                    HID if y < yr else None)
        ay = np.linspace(*W.Y_AIL, 20)
        cv.path(v.pts(np.c_[W.x_le(ay) + (W.AIL_XH - 0.04) * W.chord(ay), sg * ay]), W_FINE)
        for y in W.Y_AIL:
            cv.line(v.pt(float(W.x_le(y) + (W.AIL_XH - 0.04) * W.chord(y)), sg * y), v.pt(float(W.x_te(y)), sg * y),
                    W_FINE)
        tb0, tb1 = W.Y_AIL[0] + 0.06, W.Y_AIL[0] + 0.72
        tp = [(float(W.x_te(y)), y) for y in (tb0,)] + [(float(W.x_le(y) + 0.945 * W.chord(y)), y) for y in (tb0, tb1)] \
            + [(float(W.x_te(tb1)), tb1)]
        cv.path(v.pts([(p[0], sg * p[1]) for p in tp]), W_THIN)
        # winglet
        cv.path(v.pts(np.c_[wg["le"][:, 0], sg * wg["le"][:, 1]]), W_OBJ)
        cv.path(v.pts(np.c_[wg["te"][:, 0], sg * wg["te"][:, 1]]), W_OBJ)
        cv.line(v.pt(wg["le"][-1, 0], sg * wg["le"][-1, 1]), v.pt(wg["te"][-1, 0], sg * wg["te"][-1, 1]), W_OBJ)
    # radar pod (starboard)
    prof = np.array(D.radar_pod_profile())
    cv.path(v.pts(np.r_[np.c_[prof[:, 0], D.POD_Y + prof[:, 1]], np.c_[prof[::-1, 0], D.POD_Y - prof[::-1, 1]]]),
            W_OBJ, closed=True)
    rj = float(np.interp(D.POD_X_JOINT, prof[:, 0], prof[:, 1]))
    cv.line(v.pt(D.POD_X_JOINT, D.POD_Y - rj), v.pt(D.POD_X_JOINT, D.POD_Y + rj), W_FINE)
    # MAC
    m, ym, lemac = mac_numbers()
    cv.line(v.pt(lemac, -ym), v.pt(lemac + m, -ym), 0.5)
    for xx in (lemac, lemac + m):
        cv.line(v.pt(xx, -ym - 0.12), v.pt(xx, -ym + 0.12), 0.3)
    xq = lemac + 0.25 * m
    for sg in (1, -1):
        cv.line(v.pt(xq, sg * 0.9), v.pt(xq, sg * (W.SEMI + 0.2)), W_THIN, CHAIN, color=MUTED)
    # tailplane (both halves), elevator hinge, horn, bullet
    ys = np.linspace(0.0, E.STAB_TIP_Y - 0.002, 120)
    B = np.array(E.BULLET)
    for sg in (1, -1):
        bw = np.interp(E.stab_le(ys), B[:, 0], B[:, 3])
        out = ys >= bw - 1e-3
        cv.path(v.pts(np.c_[[E.stab_le(y) for y in ys[out]], sg * ys[out]]), W_OBJ)
        cv.path(v.pts(np.c_[[E.stab_te(y) for y in ys[out]], sg * ys[out]]), W_OBJ)
        yt = E.STAB_TIP_Y - 0.002
        cv.line(v.pt(E.stab_le(yt), sg * yt), v.pt(E.stab_te(yt), sg * yt), W_OBJ)
        hy = np.linspace(E.ELEV_Y[0], E.ELEV_Y[1], 20)
        cv.path(v.pts(np.c_[[E.stab_le(y) + E.ELEV_XH * (E.stab_te(y) - E.stab_le(y)) for y in hy], sg * hy]),
                W_THIN, CHAIN)
        y0, y1, xh = E.ELEV_HORN
        cv.path(v.pts([(E.stab_te(y0), sg * y0), (xh, sg * y0), (xh, sg * (y0 + 0.12))]), W_FINE)
    cv.path(v.pts(np.r_[B[:, [0, 3]], (B[::-1][:, [0, 3]] * [1, -1])]), W_OBJ, closed=True)
    # dorsal fin (plan envelope) and strake tips where they show beyond the fuselage
    xd = np.linspace(E.DORSAL_X0, 12.6, 120)
    wd = dorsal_plan_halfwidth(xd)
    for sg in (1, -1):
        cv.path(v.pts(np.c_[xd, sg * wd]), W_FINE)
    sx = np.linspace(E.STRAKE_ROOT[0][0] + 0.01, E.STRAKE_ROOT[1][0] - 0.01, 80)
    tips = np.array([E.strake_frame(x)[1] for x in sx])
    vis = tips[:, 1] > F.half_w(sx)
    for sg in (1, -1):
        for seg in _runs(vis):
            cv.path(v.pts(np.c_[tips[seg, 0], sg * tips[seg, 1]]), W_FINE)
    # gear (hidden under the wing / fuselage)
    for sg in (1, -1):
        A = G.MAIN_AXLE
        R, Wt = G.MAIN_TYRE["R"], G.MAIN_TYRE["W"]
        cv.path(v.pts(rect_pts(A[0] - R, sg * A[1] - Wt / 2, A[0] + R, sg * A[1] + Wt / 2)), W_FINE, HID, closed=True)
    A = G.NOSE_AXLE
    R, Wt = G.NOSE_TYRE["R"], G.NOSE_TYRE["W"]
    cv.path(v.pts(rect_pts(A[0] - R, -Wt / 2, A[0] + R, Wt / 2)), W_FINE, HID, closed=True)


def _runs(mask):
    idx = np.where(mask)[0]
    if not len(idx):
        return []
    br = np.where(np.diff(idx) > 1)[0]
    return [r for r in np.split(idx, br + 1) if len(r) >= 2]


def draw_front(ds, v):
    cv = ds.cv
    cv.line(v.pt(8.6, 0.0), v.pt(-8.6, 0.0), W_FINE)
    for yg in np.arange(-8.6, 8.6, 0.25):
        cv.line(v.pt(yg, 0.0), v.pt(yg - 0.12, -0.12), W_GRID, color=MUTED)
    cv.line(v.pt(0.0, -0.1), v.pt(0.0, 4.45), W_THIN, CHAIN)
    # fuselage max section + spinner + prop disc
    t = np.linspace(0, 1, 721)
    P = F.section(np.full_like(t, 6.0), t)
    cv.path(v.pts(P[:, 1:]), W_OBJ, closed=True)
    a = np.linspace(0, 2 * np.pi, 145)
    cv.path(v.pts(np.c_[F.SPINNER_R * np.cos(a), F.PROP_AXIS_Z + F.SPINNER_R * np.sin(a)]), W_OBJ, closed=True)
    cv.path(v.pts(np.c_[PP.PROP_R * np.cos(a), F.PROP_AXIS_Z + PP.PROP_R * np.sin(a)]), W_FINE, PHANTOM, closed=True)
    # wing silhouettes, winglets, pod
    yr = wing_root_y()
    ys = np.linspace(yr, W.SEMI, 80)
    up, lo = wing_front_silhouette(ys)
    wg = winglet_geom()
    for sg in (1, -1):
        cv.path(v.pts(np.c_[sg * ys, up]), W_OBJ)
        cv.path(v.pts(np.c_[sg * ys, lo]), W_OBJ)
        cv.path(v.pts(np.c_[sg * wg["up"][:, 1], wg["up"][:, 2]]), W_OBJ)
        cv.path(v.pts(np.c_[sg * wg["lo"][:, 1], wg["lo"][:, 2]]), W_OBJ)
        cv.line(v.pt(sg * wg["up"][-1, 1], wg["up"][-1, 2]), v.pt(sg * wg["lo"][-1, 1], wg["lo"][-1, 2]), W_OBJ)
        cv.line(v.pt(sg * W.SEMI, lo[-1]), v.pt(sg * W.SEMI, up[-1]), W_FINE)
    cv.path(v.pts(np.c_[D.POD_Y + D.POD_R * np.cos(a), D.POD_Z + D.POD_R * np.sin(a)]), W_OBJ, closed=True)
    # tailplane, bullet, fin, dorsal
    ys = np.linspace(0.0, E.STAB_TIP_Y - 0.002, 60)
    su = np.array([E.stab_section(y).upper(XC)[:, 2].max() for y in ys])
    sl = np.array([E.stab_section(y).lower(XC)[:, 2].min() for y in ys])
    for sg in (1, -1):
        cv.path(v.pts(np.c_[sg * ys, su]), W_OBJ)
        cv.path(v.pts(np.c_[sg * ys, sl]), W_OBJ)
        cv.line(v.pt(sg * ys[-1], sl[-1]), v.pt(sg * ys[-1], su[-1]), W_OBJ)
    xb = 13.35
    cv.path(v.pts(E.bullet_section(xb, 96)[:, 1:]), W_OBJ, closed=True)
    zf = np.linspace(fin_crown_z(), E.BULLET[8][2], 30)
    fw = np.array([0.5 * E.fin_section(z).chord * E.fin_section(z).airfoil.thickness(np.linspace(0, 1, 201)).max()
                   for z in zf])
    for sg in (1, -1):
        cv.path(v.pts(np.c_[sg * fw, zf]), W_OBJ)
    # strakes (FR40 frame) and gear
    r, tp = E.strake_frame(F.FRAMES["FR40"])
    for sg in (1, -1):
        cv.line(v.pt(sg * r[1], r[2]), v.pt(sg * tp[1], tp[2]), W_FINE, HID)
        A = G.MAIN_AXLE
        R, Wt = G.MAIN_TYRE["R"], G.MAIN_TYRE["W"]
        cv.path(v.pts(rect_pts(sg * A[1] - Wt / 2, 0.0, sg * A[1] + Wt / 2, 2 * R)), W_OBJ, closed=True)
        T = G.MAIN_TRUNNION
        cv.line(v.pt(sg * T[1], T[2]), v.pt(sg * T[1], 2 * R), W_OBJ)
        (ax, ay, az), (bx, by, bz) = G.MAIN_BRACE
        cv.line(v.pt(sg * ay, az), v.pt(sg * by, bz), W_FINE)
    A = G.NOSE_AXLE
    R, Wt = G.NOSE_TYRE["R"], G.NOSE_TYRE["W"]
    cv.path(v.pts(rect_pts(-Wt / 2, 0.0, Wt / 2, 2 * R)), W_OBJ, closed=True)
    cv.line(v.pt(0.0, 2 * R), v.pt(0.0, float(F.z_bot(G.NOSE_PIVOT[0]))), W_OBJ)


# ============================================================================================ dimensions
def dims_side(ds, v):
    sh = ds.sh
    # overall length
    p1, p2 = v.pt(F.STA["spinner_tip"], F.PROP_AXIS_Z), v.pt(E.BULLET_X[1], E.BULLET[-1][1])
    _, yg = v.pt(0, 0)
    sh.dim(p1, p2, yg + 13.0, "14 400", "h")
    # wheelbase
    a, b = v.pt(G.NOSE_AXLE[0], G.NOSE_AXLE[2]), v.pt(G.MAIN_AXLE[0], G.MAIN_AXLE[2])
    sh.dim(a, b, yg + 6.0, f"{G.WHEELBASE * 1000:,.0f}".replace(",", " "), "h")
    # height
    X, Y = v.pt(E.BULLET[8][0], E.BULLET[8][1])
    sh.dim((X, Y), v.pt(E.BULLET[8][0], 0.0), v.pt(15.05, 0)[0], "4 260", "v", f1=(X, Y), f2=v.pt(E.BULLET_X[1], 0))
    # prop clearance
    Xp, Yp = v.pt(PP.PROP_X, F.PROP_AXIS_Z - PP.PROP_R)
    sh.dim((Xp, Yp), v.pt(PP.PROP_X, 0.0), Xp - 6.0, f"{(F.PROP_AXIS_Z - PP.PROP_R) * 1000:.0f}", "v",
           text_side="before")
    # station ordinates (above)
    m, ym, lemac = mac_numbers()
    zc = fin_crown_z()
    items = [(F.STA["spinner_tip"], F.PROP_AXIS_Z, "390 SPINNER TIP"),
             (PP.PROP_X, F.PROP_AXIS_Z + PP.PROP_R, f"{PP.PROP_X * 1000:.0f} PROP"),
             (G.NOSE_AXLE[0], 2 * G.NOSE_TYRE["R"], f"{G.NOSE_AXLE[0] * 1000:.0f} NOSE AXLE"),
             (F.STA["firewall"], float(F.z_top(3.0)), "3000 FIREWALL"),
             (float(W.x_le(1.0)), 1.30, f"{W.x_le(1.0) * 1000:.0f} WING LE BL1000"),
             (lemac, 1.30, f"{lemac * 1000:.0f} LEMAC"),
             (lemac + 0.25 * m, 1.30, f"{(lemac + 0.25 * m) * 1000:.0f} 25% MAC"),
             (G.MAIN_AXLE[0], 2 * G.MAIN_TYRE["R"], f"{G.MAIN_AXLE[0] * 1000:.0f} MAIN AXLE"),
             (float(W.x_te(1.0)), 1.33, f"{W.x_te(1.0) * 1000:.0f} WING TE BL1000"),
             (E.DORSAL_X0, E.DORSAL_Z0, f"{E.DORSAL_X0 * 1000:.0f} DORSAL"),
             (E.fin_le(zc), zc, f"{E.fin_le(zc) * 1000:.0f} FIN LE (CROWN)"),
             (E.BULLET_X[0], E.BULLET[0][1], f"{E.BULLET_X[0] * 1000:.0f} BULLET"),
             (float(E.stab_le(0.0)), E.STAB_Z, f"{E.stab_le(0.0) * 1000:.0f} STAB LE BL0"),
             (float(E.stab_le(0.0) + E.ELEV_XH * E.STAB_ROOT_C), E.STAB_Z + 0.08,
              f"{(E.stab_le(0.0) + E.ELEV_XH * E.STAB_ROOT_C) * 1000:.0f} ELEV HINGE"),
             (E.FIN_TE[0][0], E.FIN_TE[0][1], f"{E.FIN_TE[0][0] * 1000:.0f} RUDDER TE LOW"),
             (E.BULLET_X[1], E.BULLET[-1][1], f"{E.BULLET_X[1] * 1000:.0f} AFT-MOST")]
    _, ytop = v.pt(0, 4.40)
    ordinates(ds, v, items, ytop - 3.0, up=True)
    # WL ordinates on the right edge
    wg = winglet_geom()
    entries = [(F.PROP_AXIS_Z, "1655 PROP AXIS"), (E.STAB_Z, f"{E.STAB_Z * 1000:.0f} STAB CHORD PLANE"),
               (4.26, "4260 TOP"), (float(wg["up"][:, 2].max()), f"{wg['up'][:, 2].max() * 1000:.0f} WINGLET TOP"),
               (W.Z_QC0, f"{W.Z_QC0 * 1000:.0f} WING QC BL0"), (E.FIN_TE[0][1], f"{E.FIN_TE[0][1] * 1000:.0f} RUDDER LOW")]
    wl_ticks(ds, v, entries, 15.15, side="right", gap=3.0)


def dims_plan(ds, v):
    sh = ds.sh
    wg = winglet_geom()
    ymax = float(wg["lo"][:, 1].max())
    # span
    Xs = v.pt(3.0, 0)[0]
    sh.dim(v.pt(float(wg["lo"][-1, 0]), ymax), v.pt(float(wg["lo"][-1, 0]), -ymax), Xs, "16 280", "v",
           text_at=(Xs, v.pt(0.0, 4.6)[1]))
    # tail span
    Xt = v.pt(15.05, 0)[0]
    yt = E.STAB_TIP_Y
    sh.dim(v.pt(E.stab_le(yt), yt), v.pt(E.stab_le(yt), -yt), Xt, "5 200", "v")
    # call-outs: wing LE / TE at BL 1000 and tip rib, MAC, flap / aileron, pod
    m, ym, lemac = mac_numbers()
    leader_label(ds, v, lemac + 0.5 * m, -ym, f"MAC {m * 1000:.0f} AT BL {ym * 1000:.0f}", off=(10.0, 7.0),
                 lines=[f"LEMAC STA {lemac * 1000:.0f}", f"25% MAC STA {(lemac + 0.25 * m) * 1000:.0f}"])
    leader_label(ds, v, float(W.x_te(W.SEMI)), -W.SEMI, f"TIP RIB BL {W.SEMI * 1000:.0f}", off=(12.0, 4.0),
                 lines=[f"LE {W.x_le(W.SEMI) * 1000:.0f} / TE {W.x_te(W.SEMI) * 1000:.0f}",
                        f"CHORD {W.C_TIP * 1000:.0f}"])
    leader_label(ds, v, float(W.x_le(1.0)), -1.0, f"BL 1000: LE {W.x_le(1.0) * 1000:.0f}", off=(-6.0, 22.0),
                 lines=[f"TE {W.x_te(1.0) * 1000:.0f}, CHORD {W.chord(1.0) * 1000:.0f}",
                        f"ROOT CHORD (BL 0) {W.C_ROOT * 1000:.0f}"])
    leader_label(ds, v, D.POD_X_TIP, D.POD_Y, "WEATHER-RADAR POD", off=(-6.0, 7.0),
                 lines=[f"BL {D.POD_Y * 1000:.0f} WL {D.POD_Z * 1000:.0f} R {D.POD_R * 1000:.0f}",
                        f"NOSE STA {D.POD_X_TIP * 1000:.0f}"])
    leader_label(ds, v, float(W.x_te(3.9)), 3.9, "FOWLER FLAP", off=(10.0, -6.0),
                 lines=[f"BL {W.Y_FLAP[0] * 1000:.0f} - {W.Y_FLAP[1] * 1000:.0f}"])
    leader_label(ds, v, float(W.x_te(6.6)), 6.6, "AILERON + FLETTNER TAB", off=(10.0, -4.0),
                 lines=[f"BL {W.Y_AIL[0] * 1000:.0f} - {W.Y_AIL[1] * 1000:.0f}, HINGE {W.AIL_XH * 100:.1f}% c"])
    leader_label(ds, v, float(E.stab_le(1.0)), 1.0, f"STAB LE BL1000 {E.stab_le(1.0) * 1000:.0f}", off=(-12.0, -12.0),
                 lines=[f"TE {E.stab_te(1.0) * 1000:.0f}; SWEEP {math.degrees(E.STAB_SWEEP):.1f} DEG",
                        f"ELEVATOR HINGE STA {(E.stab_le(1.0) + E.ELEV_XH * (E.stab_te(1.0) - E.stab_le(1.0))) * 1000:.0f}"])
    leader_label(ds, v, E.ELEV_HORN[2], -2.40, "HORN BALANCE", off=(-8.0, 8.0),
                 lines=[f"BL {E.ELEV_HORN[0] * 1000:.0f} - {E.ELEV_HORN[1] * 1000:.0f}"])
    xs = E.STRAKE_TIP[1][0]
    leader_label(ds, v, xs, -float(E.strake_frame(xs)[1][1]), "VENTRAL STRAKE TIP", off=(-6.0, 10.0),
                 lines=[f"CANT {math.degrees(E.STRAKE_CANT):.0f} DEG"])


def dims_front(ds, v):
    sh = ds.sh
    wg = winglet_geom()
    ymax = float(wg["lo"][:, 1].max())
    _, yg = v.pt(0, 0)
    sh.dim(v.pt(ymax, float(wg["lo"][-1, 2])), v.pt(-ymax, float(wg["lo"][-1, 2])), yg + 16.0, "16 280", "h")
    A = G.MAIN_AXLE
    sh.dim(v.pt(A[1], 0.0), v.pt(-A[1], 0.0), yg + 8.0, f"{G.TRACK * 1000:,.0f}".replace(",", " "), "h")
    sh.dim(v.pt(E.STAB_TIP_Y, E.STAB_Z), v.pt(-E.STAB_TIP_Y, E.STAB_Z), v.pt(0, 4.26)[1] - 5.0, "5 200", "h")
    # dihedral angle on the port wing (viewer's right)
    yq = 2.0
    zq = float(W.z_ref(yq))
    Xa, Ya = v.pt(-yq, zq)
    ang = math.degrees(W.DIHEDRAL)
    sh.cv.line((Xa, Ya), (Xa + 70.0, Ya), W_DIM, (2.0, 1.0))
    Xb, Yb = v.pt(-(yq + 3.5), float(W.z_ref(yq + 3.5)))
    sh.cv.line((Xa, Ya), (Xb, Yb), W_DIM, CHAIN)
    sh.angle_dim((Xa, Ya), 0.0, -ang, 60.0, f"{ang:.2f}°", (Xa + 66.0, Ya + 5.0))
    label(ds, v, -(yq + 3.5), float(W.z_ref(yq + 3.5)) + 0.25, "WING QC REFERENCE LINE", size=2.0)
    # winglet cant
    label(ds, v, -8.05, 2.35, f"WINGLET CANT {math.degrees(W.WL_CANT):.0f}° FROM VERTICAL", size=2.0, anchor="middle")
    # prop
    leader_label(ds, v, -PP.PROP_R * 0.7071, F.PROP_AXIS_Z + PP.PROP_R * 0.7071, f"PROP DISC Ø{2 * PP.PROP_R * 1000:.0f}",
                 off=(12.0, -8.0), lines=[f"AXIS WL {F.PROP_AXIS_Z * 1000:.0f}, CLEARANCE {(F.PROP_AXIS_Z - PP.PROP_R) * 1000:.0f}"])


# ============================================================================================ details
def draw_detail_tip(ds):
    """Detail A: starboard wing tip, winglet and radar pod seen from ahead, 1:10."""
    v = ds.add_view(front_view("detail_tip", origin=(428.0, 431.0), scale=10, model_origin=(7.70, 1.90),
                               box=(7.15, 1.50, 8.30, 2.32)))
    cv = ds.cv
    ys = np.linspace(7.18, W.SEMI, 30)
    up, lo = wing_front_silhouette(ys)
    wg = winglet_geom()
    cv.path(v.pts(np.c_[ys, up]), W_OBJ)
    cv.path(v.pts(np.c_[ys, lo]), W_OBJ)
    cv.path(v.pts(wg["up"][:, 1:]), W_OBJ)
    cv.path(v.pts(wg["lo"][:, 1:]), W_OBJ)
    cv.path(v.pts(wg["top"][:, 1:]), W_FINE, closed=True)
    cv.line(v.pt(W.SEMI, lo[-1]), v.pt(W.SEMI, up[-1]), W_FINE)
    a = np.linspace(0, 2 * np.pi, 97)
    cv.path(v.pts(np.c_[D.POD_Y + D.POD_R * np.cos(a), D.POD_Z + D.POD_R * np.sin(a)]), W_OBJ, closed=True)
    for d0, d1 in (((D.POD_Y - D.POD_R - 0.03, D.POD_Z), (D.POD_Y + D.POD_R + 0.03, D.POD_Z)),
                   ((D.POD_Y, D.POD_Z - D.POD_R - 0.03), (D.POD_Y, D.POD_Z + D.POD_R + 0.03))):
        cv.line(v.pt(*d0), v.pt(*d1), W_GRID, CHAIN, color=MUTED)
    # chord path (quarter-chord line) of the winglet + dihedral reference
    arr, _ = W.winglet_path(30, 20)
    cv.path(v.pts(arr[:, :2]), W_THIN, CHAIN)
    cv.path(v.pts(np.c_[ys, W.z_ref(ys)]), W_THIN, CHAIN)
    # dims: tip rib BL, outer BL (span / 2), top WL, cant, bend radius, pod
    sh = ds.sh
    ymax = float(max(wg["lo"][:, 1].max(), wg["top"][:, 1].max()))
    ztop = float(max(wg["up"][:, 2].max(), wg["top"][:, 2].max()))
    Xr, _ = v.pt(W.SEMI, 0)
    Xo, _ = v.pt(ymax, 0)
    _, Yb = v.pt(0, 1.50)
    sh.dim(v.pt(W.SEMI, lo[-1]), v.pt(ymax, float(wg["lo"][-1, 2])), Yb + 4.0, f"{(ymax - W.SEMI) * 1000:.0f}", "h")
    ds.text(Xr, Yb + 11.0, f"TIP RIB BL {W.SEMI * 1000:.0f}", 2.0, "mono", "middle", tag="dtl")
    ds.text(Xo, Yb + 11.0, f"BL {ymax * 1000:.0f}", 2.0, "mono", "middle", tag="dtl")
    Xt, Yt = v.pt(float(wg["up"][-1, 1]), ztop)
    ds.cv.line((Xt, Yt), (Xt + 16.0, Yt), W_DIM)
    ds.text(Xt + 17.0, Yt, f"WL {ztop * 1000:.0f} WINGLET TOP", 2.0, "mono", "start", vcenter=True, tag="dtl")
    ang = math.degrees(W.WL_CANT)
    X0, Y0 = v.pt(*arr[13, :2])
    cv.line((X0, Y0), (X0, Y0 - 30.0), W_DIM, (2.0, 1.0))
    sh.angle_dim((X0, Y0), -90.0, -90.0 - ang, 22.0, f"{ang:.0f}°", (X0 - 17.0, Y0 - 25.0))
    leader_label(ds, v, float(arr[6, 0]), float(arr[6, 1]), f"BEND R {W.WL_BEND_R * 1000:.0f}", off=(-4.0, 14.0),
                 size=2.0, lines=["(QUARTER-CHORD PATH)"])
    leader_label(ds, v, D.POD_Y - D.POD_R * 0.7, D.POD_Z - D.POD_R * 0.7, f"RADAR POD R {D.POD_R * 1000:.0f}",
                 off=(18.0, 10.0), size=2.0, lines=[f"AXIS BL {D.POD_Y * 1000:.0f} WL {D.POD_Z * 1000:.0f}"])
    leader_label(ds, v, 7.30, float(W.z_ref(7.30)), f"DIHEDRAL {math.degrees(W.DIHEDRAL):.2f}°", off=(6.0, 12.0),
                 size=2.0, lines=["QC REFERENCE LINE"])
    M.view_title(ds, 428.0, 496.0, "DETAIL A - STARBOARD WING TIP", "WINGLET + RADAR POD, SEEN FROM AHEAD · 1:10",
                 size=3.4)


def draw_detail_gear(ds):
    """Detail B: port main gear seen from port, 1:20 (gear down; retracted wheel phantom)."""
    v = ds.add_view(side_view("detail_gear", origin=(530.0, 432.0), scale=20, model_origin=(6.20, 0.60),
                              box=(5.70, -0.05, 6.85, 1.40)))
    cv = ds.cv
    cv.line(v.pt(5.70, 0.0), v.pt(6.85, 0.0), W_FINE)
    for xg in np.arange(5.70, 6.85, 0.05):
        cv.line(v.pt(xg, 0.0), v.pt(xg - 0.03, -0.03), W_GRID, color=MUTED)
    s = W.section_at(G.MAIN_AXLE[1])
    P = np.vstack([s.lower(XC[::-1]), s.upper(XC[1:])])
    m = (P[:, 0] > 5.72) & (P[:, 0] < 6.83)
    for seg in _runs(m):
        cv.path(v.pts(P[seg][:, [0, 2]]), W_FINE)
    tyre_side(ds, v, G.MAIN_AXLE, G.MAIN_TYRE)
    T, L, A = G.MAIN_TRUNNION, G.MAIN_LINK_PIVOT, G.MAIN_AXLE
    cv.path(v.pts([(T[0], T[2]), (L[0], L[2]), (A[0], A[2])]), W_OBJ)
    (s1x, s1z), (s2x, s2z) = G.MAIN_SHOCK
    cv.path(v.pts([(s1x, s1z), (s2x, s2z)]), W_FINE)
    (ax, ay, az), (bx, by, bz) = G.MAIN_BRACE
    cv.path(v.pts([(ax, az), (bx, bz)]), W_FINE, HID)
    c = G.retracted_wheel()
    R, Wt = G.MAIN_TYRE["R"], G.MAIN_TYRE["W"]
    cv.path(v.pts(rect_pts(c[0] - R, c[2] - Wt / 2, c[0] + R, c[2] + Wt / 2)), W_FINE, PHANTOM, closed=True)
    for p_, t_, off in ((T, "TRUNNION", (-10.0, -8.0)), (L, "LINK PIVOT", (-10.0, 4.0)),
                        (A, "AXLE", (12.0, 10.0)), ((s1x, 0, s1z), "SHOCK", (14.0, -4.0))):
        X, Y = v.pt(p_[0], p_[2])
        cv.circle(X, Y, 0.8, w=W_FINE)
        leader_label(ds, v, p_[0], p_[2], t_, off=off, size=1.9,
                     lines=[f"{p_[0] * 1000:.0f} / WL {p_[2] * 1000:.0f}"])
    leader_label(ds, v, c[0] + 0.5 * R, c[2] + Wt / 2, "RETRACTED (PHANTOM)", off=(4.0, -10.0), size=1.9,
                 lines=[f"BL {c[1] * 1000:.0f}, PROTRUDES {retract_protrusion() * 1000:.0f}"])
    M.view_title(ds, 530.0, 496.0, "DETAIL B - MAIN GEAR", "PORT UNIT, SEEN FROM PORT · 1:20", size=3.4)


# ============================================================================================ tables
def f_mm(v):
    return f"{v * 1000:,.0f}".replace(",", " ")


def dev(a, b, deg=False):
    if a is None or b is None:
        return "-"
    v = round(a - b, 2) if deg else round((a - b) * 1000)
    if v == 0:
        return "0.00" if deg else "0"
    return f"{v:+.2f}" if deg else f"{v:+.0f}"


def deviation_rows(O, R):
    """(item, ours, d_dwg, revA_d_dwg, note)."""
    rows = []

    def add(item, key, note="", deg=False, fmt=None, rev_key=None):
        o = O.get(key)
        r = R.get(key) if R else None
        ra = REV_A.get(rev_key or key)
        s = fmt(o) if fmt else (f"{o:.2f}" if deg else f_mm(o))
        rows.append((item, s, dev(o, r, deg) if r is not None else "-",
                     dev(ra, r, deg) if (ra is not None and r is not None) else "-", note))

    add("Wing LE, BL 1000 (plan)", "wing_le_1.0", "straight LE x = 5.3302 + 0.040 y")
    add("Wing TE, BL 1000 (plan)", "wing_te_1.0", "root chord solved for 25.81 m2 total plan area")
    add("Wing LE, BL 4000", "wing_le_4.0")
    add("Wing TE, BL 4000", "wing_te_4.0")
    add("Wing LE, BL 7400 (tip rib 7430)", "wing_le_7.4")
    add("Wing TE, BL 7400 (aileron)", "wing_te_7.4", "TE kink at BL 5680 (constant-chord aileron)")
    add("Wing upper WL, BL 4000 (front)", "wing_up_4.0", "airfoil fuller aft than the drawn WR sections")
    add("Wing lower WL, BL 4000 (front)", "wing_lo_4.0")
    add("Wing upper WL, BL 7000 (front)", "wing_up_7.0")
    add("Wing lower WL, BL 7000 (front)", "wing_lo_7.0")
    add("Dihedral (front, mean line) deg", "dihedral", "drawing's WR dimension line reads 5.0", deg=True)
    for n in ("WR1", "WR2", "WR3", "WR4"):
        add(f"Incidence {n} deg", f"inc_{n}", "twist table (BL 0 / 5560 / tip)" if n == "WR1" else "", deg=True)
    add("Winglet top WL (front)", "winglet_top_z", "straight part lengthened for the 16.28 m span")
    add("Winglet outer BL (span / 2)", "winglet_y", "drawn span 16.137 (label 16.114); 16.28 kept")
    add("Winglet cant from vertical deg", "winglet_cant", "", deg=True)
    add("Stab LE, BL 1000 (plan)", "stab_le_1.0", "LE sweep 7.2 deg")
    add("Stab TE, BL 1000 (plan)", "stab_te_1.0")
    add("Stab LE, BL 2270 (tip rib)", "stab_le_2.27")
    add("Stab TE, BL 2270", "stab_te_2.27")
    add("Elevator hinge STA (HF1)", "elev_hinge_1.0", "70 % chord = constant STA 14000")
    add("Stab chord plane WL (front)", "stab_z")
    add("Bullet nose STA", "bullet_x0")
    add("Bullet end STA (aft-most)", "bullet_x1", "14.40 m overall length kept (drawn 14.421)")
    add("Fin LE STA at WL 3400 (side)", "fin_le_3.4", "LE 40.3 deg")
    add("Fin LE STA at WL 3800", "fin_le_3.8")
    add("Rudder TE STA at WL 2609 (VF1)", "fin_te_2.609", "TE 22.2 deg", rev_key="fin_te_2.609")
    add("Rudder TE STA at WL 3919 (VF2)", "fin_te_3.919")
    add("Rudder hinge STA, WL 2609", "rud_hinge_2.609", "nose-circle centre of the drawn rudder")
    add("Rudder hinge STA, WL 3919", "rud_hinge_3.919")
    add("Fin t/c at VF2 (%)", "fin_t_3.919", "NACA 0018", fmt=lambda v: f"{v * 100:.1f}")
    rows[-1] = (rows[-1][0], rows[-1][1], f"{(O['fin_t_3.919'] - R['fin_t_3.919']) * 100:+.1f}" if R else "-",
                f"{(REV_A['fin_t'] - R['fin_t_3.919']) * 100:+.1f}" if R else "-", rows[-1][4])
    for n in ("FR38", "FR40"):
        add(f"Dorsal half-width {n}", f"dorsal_hw_{n}", "straight top edge from FR33, 0.134 m/m" if n == "FR38" else "")
    for n in ("FR38", "FR40"):
        o, r = O[f"strake_tip_{n}"], (R or {}).get(f"strake_tip_{n}")
        rows.append((f"Strake tip {n} (BL / WL)", f"{f_mm(o[0])} / {f_mm(o[1])}",
                     f"{dev(o[0], r[0])} / {dev(o[1], r[1])}" if r else "-",
                     "not on FR38/40" if r else "-", "rev A strakes STA 12350-13750"))
    add("Nose axle STA", "nose_axle", "wheelbase 3480 (POH) centred on the drawn axles")
    add("Main axle STA", "main_axle", "")
    add("Track (front)", "track", "Pilatus 4530")
    add("Radar pod nose STA (plan)", "pod_x0", "starboard wing tip; rev A at BL 3900")
    add("Radar pod axis BL (front)", "pod_y")
    add("Radar pod axis WL (front)", "pod_z")
    add("Radar pod radius", "pod_r", "PRO: enlarged for the 12-in GWX 8000")
    add("Prop disc tilt deg (top fwd)", "prop_tilt", "not modelled: Stage 3 (thrust line 2 deg down)", deg=True)
    add("Prop clearance (side)", "prop_clear", "Pilatus 320 kept")
    return rows


def param_rows():
    m, ym, lemac = mac_numbers()
    return [
        ("WING  span over winglets / plan area", f"16 280 / {W.planform_area():.2f} m2 (total projected)"),
        ("      root chord BL 0 / tip rib BL 7430", f"{W.C_ROOT * 1000:.0f} / {W.C_TIP * 1000:.0f} ({W.C_TIP_TRAP * 1000:.0f} str. TE)"),
        ("      LE sweep / taper (straight TE)", f"{math.degrees(W.LE_SWEEP):.2f} deg / {W.TAPER:.3f}"),
        ("      MAC / its BL / LEMAC / 25% MAC", f"{m * 1000:.0f} / {ym * 1000:.0f} / {lemac * 1000:.0f} / {(lemac + 0.25 * m) * 1000:.0f}"),
        ("      POH aft CG 6107 in % MAC", f"{100 * (W.AFT_CG - lemac) / m:.1f} % (rev A assumed 46 %)"),
        ("      dihedral / flat centre to BL", f"{math.degrees(W.DIHEDRAL):.2f} deg / {W.Y_DIH0 * 1000:.0f}"),
        ("      QC WL at BL 0 / incidence root / tip", f"{W.Z_QC0 * 1000:.0f} / {W.TWIST[0][1]:+.2f} / {W.TWIST[-1][1]:+.2f} deg"),
        ("      flap / aileron BL", f"{W.Y_FLAP[0] * 1000:.0f}-{W.Y_FLAP[1] * 1000:.0f} / {W.Y_AIL[0] * 1000:.0f}-{W.Y_AIL[1] * 1000:.0f}"),
        ("      winglet cant / bend R / top chord", f"{math.degrees(W.WL_CANT):.0f} deg / {W.WL_BEND_R * 1000:.0f} / {W.WL_TIP_CHORD * 1000:.0f}"),
        ("FIN   LE / rudder TE sweep", f"{math.degrees(math.atan((E.FIN_LE[1][0] - E.FIN_LE[0][0]) / (E.FIN_LE[1][1] - E.FIN_LE[0][1]))):.1f} / "
                                     f"{math.degrees(math.atan((E.FIN_TE[1][0] - E.FIN_TE[0][0]) / (E.FIN_TE[1][1] - E.FIN_TE[0][1]))):.1f} deg"),
        ("      section / rudder hinge / tab", f"NACA 0018 / {E.RUD_XH * 100:.1f}% c / WL {E.RUD_TAB[0] * 1000:.0f}-{E.RUD_TAB[1] * 1000:.0f}"),
        ("STAB  LE / TE at BL 0, chord plane WL", f"{E.STAB_ROOT_LE * 1000:.0f} / {(E.STAB_ROOT_LE + E.STAB_ROOT_C) * 1000:.0f}, {E.STAB_Z * 1000:.0f}"),
        ("      tip rib / horn / elevator hinge", f"BL {E.STAB_TIP_RIB * 1000:.0f} / {E.ELEV_HORN[0] * 1000:.0f}-{E.ELEV_HORN[1] * 1000:.0f} / STA 14000"),
        ("      bullet / aft-most", f"STA {E.BULLET_X[0] * 1000:.0f} - {E.BULLET_X[1] * 1000:.0f}"),
        ("GEAR  nose / main axle, wheelbase", f"{G.NOSE_AXLE[0] * 1000:.0f} / {G.MAIN_AXLE[0] * 1000:.0f}, 3 480"),
        ("      main trunnion / link pivot (STA, WL)", f"{G.MAIN_TRUNNION[0] * 1000:.0f},{G.MAIN_TRUNNION[2] * 1000:.0f} / "
                                                     f"{G.MAIN_LINK_PIVOT[0] * 1000:.0f},{G.MAIN_LINK_PIVOT[2] * 1000:.0f}"),
        ("      retracted wheel (BL) / tyre protrusion", f"{G.retracted_wheel()[1] * 1000:.0f} / {retract_protrusion() * 1000:.0f} (POH ~25)"),
        ("POD   radar pod axis BL / WL / R", f"{D.POD_Y * 1000:.0f} / {D.POD_Z * 1000:.0f} / {D.POD_R * 1000:.0f}"),
    ]


def retract_protrusion():
    c = G.retracted_wheel()
    s = W.section_at(c[1])
    xc = (c[0] - s.le[0]) / s.chord
    return float(s.lower(np.array(xc))[2]) - (c[2] - G.MAIN_TYRE["W"] / 2)


def stage3_items():
    return [
        "build.py verify(): 'Wing reference area' must use wing.planform_area() (total projected area incl. the "
        "aileron kink and the winglets' plan projection = 25.81); the trapezoid formula now reads 25.08.",
        "Wing moved 130-160 mm aft and up (flat centre section WL 1036 at the QC, 6.15 deg dihedral from BL 700): "
        "details.belly_fairing (drawn wing-root fairing STA ~5200-8550, bottom WL ~870) must enclose the centre "
        "section (lower surface WL 869 at BL 0); interior.build_structure spar frames / carry-through and the "
        "cabin floor (L1: WL 1259) vs the wing upper surface at BL 0 (WL 1251, 8 mm clearance) - check fit_check.",
        "Flap inboard end now BL 450 (drawn dashed under the fuselage): the fuselage / belly fairing needs a flap "
        "well, or keep the 3-D flap from BL 800. Drawn flap shroud lip at ~93 % chord, flap LE ~70 % "
        "(FLAP_X_LIP 0.745 in the cove geometry); aileron chord is a constant 440 mm in the drawing (AIL_XH fixed "
        "at 68.5 %, +/-30 mm).",
        "Airfoil reconstructions (model/airfoil.py) are fuller aft than the drawn WR sections (max thickness at "
        "~30-35 % c): retune; outboard sections read ~1-2 % too thick in the front view.",
        "Winglet: new sections (wing.winglet_sections); nav / strobe lights belong in the winglet tip (drawn light "
        "box at the winglet top), details.py still places them at the tip rib (inside the pod on starboard).",
        "Gear: main trunnion WL 1070 keeps the ~1 in retracted tyre protrusion with the moved wing (well centre "
        "bays.WELL at BL 1474); re-check retraction clearances to the spars, the leg door (drawn 690 x 760) and "
        "brace kinematics (MAIN_BRACE / NOSE_BRACE); nose bay = drawn nose-door rectangle.",
        "Empennage: fin NACA 0018 down to WL 1760 (the ventral part below the tail cone is the drawn ventral fin); "
        "trim the fuselage tail cone at the fin / rudder, model the ventral fairing (FR40 bump) and the elevator "
        "horn balance (E.ELEV_HORN, now part of the fixed tip in 3-D); bullet is table-driven (E.BULLET).",
        "Propeller: the drawing's disc is tilted 2.0 deg top-forward (thrust line 2 deg nose-down) and drawn at STA "
        "925 (PROP_X 800): not modelled - it needs the engine, mount, inlet and cowl joint re-aligned together.",
        "CLAUDE.md: update the wing facts (planform from the drawing, LEMAC 5462 / MAC 1724, dihedral 6.15 deg, "
        "radar pod at the starboard wing tip, gear axles 2930.5 / 6410.5).",
    ]


# ============================================================================================ sheet
def draw(ds):
    draw_clean(ds)
    try:
        draw_overlay(ds)
    except Exception as e:                      # noqa: BLE001 -- the clean sheet must not depend on refs/cache
        ds.log.append(f"overlay skipped: {e}")


def draw_clean(ds):
    ds.frame_and_title(tb_width=250.0)
    vs = ds.add_view(side_view("side", origin=(34.0, 150.0), scale=50, box=(-0.2, -0.3, 15.3, 4.5)))
    vp = ds.add_view(plan_view("plan", origin=(34.0, 352.0), scale=50, box=(-0.2, -8.4, 15.3, 8.4)))
    vf = ds.add_view(front_view("front", origin=(548.0, 150.0), scale=50, box=(-8.4, -0.3, 8.4, 4.5)))
    # station grid at the frames: ticks on the side view's ground line, labels below the dimensions
    frames = {n: F.FRAMES[n] for n in ("EF1", "EF2", "FR10", "FR14", "FR19", "FR23", "FR27", "FR31", "FR33",
                                        "FR36", "FR38", "FR40")}
    _, yg = vs.pt(0, 0)
    for n, x in frames.items():
        X, _ = vs.pt(x, 0)
        ds.cv.line((X, yg), (X, yg + 16.5), W_GRID, color=GRID)
        ds.text(X, yg + 19.0, n, 1.9, "label", "middle", fill=GRID, tag="grid")
        ds.text(X, yg + 21.4, f"{x * 1000:.0f}", 1.8, "mono", "middle", fill=GRID, tag="grid")
    # BL grid at the plan's left edge
    for yb in (-8.0, -6.0, -4.0, -2.0, 2.0, 4.0, 6.0, 8.0):
        X, Y = vp.pt(0.15, yb)
        ds.cv.line((X, Y), (X + 4.0, Y), W_GRID, color=GRID)
        ds.text(X - 1.0, Y, f"BL {abs(yb) * 1000:.0f}{' S' if yb > 0 else ' P'}", 1.9, "mono", "end", vcenter=True,
                fill=GRID, tag="grid")
    draw_side(ds, vs)
    draw_plan(ds, vp)
    draw_front(ds, vf)
    dims_side(ds, vs)
    dims_plan(ds, vp)
    dims_front(ds, vf)
    view_title(ds, 292.0, 190.0, "SIDE VIEW", "SEEN FROM PORT · SCALE 1:50")
    view_title(ds, 292.0, 452.0, "PLAN", "SEEN FROM ABOVE · STARBOARD UP · SCALE 1:50")
    view_title(ds, 548.0, 192.0, "FRONT VIEW", "SEEN FROM AHEAD · STARBOARD LEFT · SCALE 1:50")
    scale_bar(ds, 250.0, 478.0, 50, length_m=4.0, step_m=0.5)
    draw_detail_tip(ds)
    draw_detail_gear(ds)
    legend(ds, 735.0, 26.0)

    O = ours()
    try:
        R = reference()
    except Exception as e:                      # noqa: BLE001
        R = None
        ds.log.append(f"deviation table: reference not available ({e})")
    rows = deviation_rows(O, R)
    cols = [("ITEM", 58.0, "l"), ("OURS", 22.0, "r"), ("D DWG", 15.0, "r"), ("REV A D DWG", 20.0, "r"),
            ("NOTE", 76.0, "l")]
    ytab = table(ds, 368.0, 212.0, cols, rows, title="DEVIATIONS FROM THE PILATUS DRAWING (mm / deg; D = ours - dwg)",
                 size=2.05, row_h=3.05, head_h=4.6, zebra=lambda i: i % 2 == 1, font="label")
    ds.text(368.0, ytab + 3.4, "D DWG vs the registered drawing 190.10.40.432 (sheet 1; x +/-21, z +/-2); REV A = "
            "the model before this refit.", 2.0, "label", "start", fill=MUTED, tag="tnote")
    prow = param_rows()
    yp = table(ds, 566.0, 212.0, [("LAYOUT PARAMETER", 60.0, "l"), ("VALUE (mm)", 60.0, "l")], prow,
               title="LAYOUT PARAMETERS (model/*.py)", size=2.05, row_h=3.05, head_h=4.6,
               zebra=lambda i: i % 2 == 1, font="label")
    notes(ds, 692.0, 212.0, 830.0, stage3_items(), title="STAGE 3 - WHAT MUST FOLLOW", size=2.0, line_h=2.75)
    notes(ds, 566.0, yp + 4.0, 688.0, notes_items(), title="NOTES", size=2.0, line_h=2.75)
    table(ds, 587.0, 385.0, [("PHOTO / RENDER (refs/photos.json)", 62.0, "l"), ("WHAT IT SHOWS FOR THE LAYOUT", 180.0, "l")],
          evidence_rows(), title="PHOTO / RENDER EVIDENCE", size=2.0, row_h=3.1, head_h=4.6,
          zebra=lambda i: i % 2 == 1, font="label")
    if R:
        worst = [(r[0], r[2]) for r in rows if r[2] not in ("-",) and "/" not in r[2]]
        ds.log.append("deviations: " + "; ".join(f"{a} {b}" for a, b in worst))


def evidence_rows():
    return [
        ("ngx_kenia_stbd_pilatus (NGX)", "radar pod on the STARBOARD WING TIP leading edge, black radome, body faired into the winglet root"),
        ("pro3008_stbd34_pilatus (PRO s/n 3008)", "PRO pod at the starboard tip; radome slightly larger (12-in GWX 8000) -> R 165 (drawn NGX 155)"),
        ("pil_techdata_front_5000 (render)", "pod at the starboard tip; LE band slopes 5.7 / 6.6 deg (mean ~6.1 = drawn wing, not the 5.0 dim line)"),
        ("pil_techdata_front_5000 (render)", "winglet straight part ~39 deg above horizontal (cant ~51 deg), rise ~0.33 m above the tip"),
        ("ngx_kenia_stbd_pilatus crop", "large single leg door on the main leg, trailing link, three flap-track canoes per wing"),
    ]


def notes_items():
    return [
        "Drawn from the parameters of model/wing.py, empennage.py, gear.py, bays.py, details.py and fuselage.py "
        "(section functions and knot tables), never from the mesh. STA = mm aft of the datum (3000 ahead of the "
        "firewall); WL above the static ground line; BL + starboard.",
        "Positions fitted to the registered Pilatus NGX model drawing 190.10.40.432 (plan, side, front, sections "
        "WR1-4, VF1-2, HF1-2, FR38 / FR40); photos confirm the radar pod at the starboard wing tip.",
        "Official values kept where the drawing differs: span 16.28 (drawn 16.137), wheelbase 3.48 (drawn 3.515), "
        "prop clearance 0.32 (drawn 0.336), overall length 14.40 (drawn 14.421).",
        "Wing area 25.81 m2 = total projected plan area (both halves through the fuselage, incl. the aileron kink "
        "and the winglets' plan projection): the drawing's planform gives it within 0.1 %.",
    ]


def legend(ds, x0, y0):
    cv = ds.cv
    items = [("visible outline (parameters)", dict(w=W_OBJ)), ("section / edge / hinge line", dict(w=W_FINE)),
             ("hidden (gear under wing, pod)", dict(w=W_FINE, dash=HID)),
             ("hinge / reference axis", dict(w=W_THIN, dash=CHAIN)), ("propeller disc", dict(w=W_FINE, dash=PHANTOM))]
    for i, (lab, st) in enumerate(items):
        y = y0 + 4.2 * i
        cv.line((x0, y), (x0 + 10.0, y), st["w"], st.get("dash"), color=st.get("color"))
        ds.text(x0 + 12.5, y, lab, 2.2, "label", "start", vcenter=True, tag="legend")


# ============================================================================================ overlay
def draw_overlay(ds):
    vs, vp, vf = (ds.views[k] for k in ("side", "plan", "front"))
    n = ds.ov_mbp(vs, "side")
    n += ds.ov_mbp(vp, "plan")
    n += ds.ov_mbp(vf, "front")
    n += ds.ov_mbp(ds.views["detail_tip"], "front")
    n += ds.ov_mbp(ds.views["detail_gear"], "side")
    # photo-derived marks: radar pod at the starboard tip (ngx_kenia_stbd / pro3008_stbd34 / tech-data render)
    ds.ov_marks(vp, [(D.POD_X_TIP, D.POD_Y)], ["POD (PHOTOS: STBD WING TIP)"])
    ds.ov_text(735.0, 50.0, "RED: PILATUS 190.10.40.432 (REGISTERED, SHEET 1)", 2.4)
    ds.ov_text(735.0, 53.6, "BLUE: PHOTO-DERIVED MARKS", 2.4, color=BLUE)
    ds.log.append(f"overlay: {n} Pilatus polylines")


if __name__ == "__main__":
    M.main(["L4"] + sys.argv[1:])
