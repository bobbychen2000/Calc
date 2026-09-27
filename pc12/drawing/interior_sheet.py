"""
Sheet L6 -- INTERIOR ARRANGEMENT (sheet 1 of 2), drawn from the parameter tables of model/interior.py (crew station,
cabin seats, furniture, lining) and the existing fuselage / openings / glazing parameters.  Nothing comes from the mesh.
Sheet L6B (drawing/interior_checks.py) carries the check tables, reach, deviations and the key parameters.

    python3 -m drawing.master L6 L6B      (or: python3 -m drawing.interior_sheet)

Views (A1, first-angle):
  (a) INBOARD PROFILE at the left-seat butt line (1:20), seen from port with the port wall removed; recline envelopes
  (b) PLAN at cushion height (1:20), aligned below it: seats, recline footprints, aisle, tables, ledges, pedestal /
      consoles, door and airstair swing, exit / entry clear zones, club-four feet, lavatory user, windows
  (c) SECTIONS A-A (crew station, at the design eye) and B-B (club row, PAX 3/4 occupant arm), 1:10, looking aft,
      with the 95th- (and 50th-) percentile manikins, headroom, shoulder room, crew ingress
  (d) DETAIL C: the crew station (1:10) -- SRP, seat travel, design eye and the eyes of the 5th-95th occupants, vision
      lines, yoke pitch travel, pedals, knees, headrest vs the divider, CB panel
  (e) DETAIL E: the crew and executive seats (1:10); VIEW D: the panel (1:10); DETAIL F: the yoke's pitch / roll
      sweep against the knees of the 5th-female ... 95th-male occupants, neutral pedals and full rudder (1:5)
  (f) DETAIL G: the deployed club table against the club occupants' legs (1:10)
The notes and the open points for the owner are on L6B (review r2: L6 text >= 2.1 mm, L6B tables 3.4 mm).
The overlay variant adds the Pilatus plan-render footprints (refs/cache/interior_ref_marks.json, git-ignored) in blue.
"""
from __future__ import annotations

import json
import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from drawing import master as M  # noqa: E402
from drawing.master import (INK, GRID, MUTED, PAPER, ACCENT, W_OBJ, W_FINE, W_GRID, W_THIN, CHAIN, PHANTOM,  # noqa
                            table, scale_bar, view_title, side_view, plan_view, front_view)
from drawing.canvas import text_width  # noqa: E402
from model import interior as I  # noqa: E402
from model import fuselage as F  # noqa: E402
from model import fuselage_parts as FP  # noqa: E402
from model import cockpit_glazing as CG  # noqa: E402

SHEET = dict(id="L6", title="INTERIOR ARRANGEMENT", subtitle="INTERIOR ARRANGEMENT - FLIGHT DECK & CABIN",
             size="A1", scale="AS SHOWN", rev="E", order=60, sheet_no="1 OF 2", dwg="PC12-L6", date="2026-09-27")
# revision history of PC12-L6 (both sheets): (rev, date, description)
REVISIONS = (
    ("A", "-", "first issue of the interior (legacy 3-D interior, not drawn from parameters)"),
    ("B", "2026-09-24", "Stage-2 parameter tables (model/interior.py); crew / cabin checks; review r1"),
    ("C", "2026-09-26", "review r2: yoke grips from the measured span, SDUs, one-arm cabin seats, lavatory, full "
                        "rudder, grasp / touch reach, crew armrest hinge; review r3: divider curtain + extinguisher + "
                        "autoland drawn, lav cabinet 350 [M], pedals +/-125 [M] with the crew knees on the hip-pedal "
                        "line, knee / yoke sensitivity and POH-arm CG cross-check (L6B), 5th-female open point, "
                        "section phantoms, seat tracks from parameters"),
    ("D", "2026-09-26", "Stage-3 review r2: crew sheepskin 34 [M] drawn inside the cushion / back outline (the "
                        "3-D cover had stood proud of it), yoke grips r 15.5 x 140 [M] (P1046408), crew tracks end "
                        "15 mm past the rear foot (clear of the stowed curtain, L6B)"),
    ("E", "2026-09-27", "Stage-3 review r3: legrest under the cushion of the forward-facing executive seats [M] "
                        "(P1046402-05); PC-24 yoke face: white goblet shield (top +/-70) on a black body, grip heads "
                        "r 20 [M] (P1046408); PCL paddle grip [M]; armrest vs pedestal row (L6B); yoke-roll knee "
                        "contact recorded as an owner decision"),
)

# ---- fills (clean sheet)
SEAT_FILL = "#ECE7DC"          # cream leather
SHELL_FILL = "#C9CDD0"         # seat shells / plates, panel
BASE_FILL = "#8E969B"          # executive seat base / armrests
MAN_FILL = "#DCE7EF"           # manikin 95th
MAN50_FILL = "#EEF3F7"         # manikin 50th
MAN_LINE = "#44607A"
VENEER = "#D8CCBA"             # divider, lavatory, cabinets, FR34 header
CURTAIN = "#E9B98C"            # pleated curtains, FR34 and divider (PRO 3001: orange)
EXTING = "#C8423B"             # fire extinguisher
LEDGE_FILL = "#D3D6D8"
GLASS_FILL = "#E4EEF3"
FLOOR_FILL = "#B9BEC1"
VEST_FILL = "#E7C8B8"
FLEECE_FILL = "#D8D2D6"         # grey sheepskin covers (crew seats), inside the cushion / back outline
FAR = "#7C8A92"                # far-side / beyond lines
CUT = W_OBJ + 0.1              # section cut lines (OML, floor)
TXT = 2.1                      # minimum text size on the sheet (mm); L3 / L4 use ~1.95-2.3 (review r2: was 1.8)
PCT_TAG = dict(p95m="95", p50m="50", p5m="5M", p5f="5F")

# ---- layout (sheet mm; A1 frame 20..831 x 10..584, title block 575..825 x 507..578)
PROF_BOX = (2.90, 0.90, 9.95, 2.85)
PLAN_BOX = (2.90, -1.15, 9.95, 1.05)
ORG_PROF = (45.0, 60.0)        # sheet position of model (2.90, 2.85)
ORG_PLAN = (45.0, 239.0)       # ... of model (2.90, 0.00)
SEC_BOX = (-0.92, 0.90, 0.92, 2.85)
ORG_SA = (125.0, 342.0)        # ... of model (y 0, z 2.85), section A-A
ORG_SB = (318.0, 342.0)        # ... section B-B
DET_BOX = (2.95, 1.12, 4.66, 2.80)
ORG_DET = (447.0, 40.0)        # ... of model (2.95, 2.80), detail C
COL_X = (629.0, 826.0)         # right-hand column
E1_BOX = (3.60, 1.20, 4.52, 2.47)   # detail E: crew seat (neutral) ...
E2_BOX = (6.70, 1.20, 7.55, 2.47)   # ... and the executive seat PAX 3 (forward-facing)
ORG_E1 = (428.0, 246.0)        # sheet position of model (3.60, 2.47)
ORG_E2 = (535.0, 246.0)        # ... of model (6.70, 2.47)
D_BOX = (-0.78, 1.24, 0.78, 2.32)   # view D: panel elevation (y, z), looking forward
ORG_D = (524.0, 396.0)         # sheet position of model (y 0, z 2.32)
F_BOX = (-0.62, 1.58, -0.13, 2.04)  # detail F: yoke sweep vs knees (y, z), looking forward, left seat
G_BOX = (5.93, 1.22, 7.09, 2.03)   # detail G: club table vs the legs (x, z), at BL 375 P, seen from port
ORG_G = (633.0, 318.0)         # sheet position of model (5.93, 2.03)
ORG_F = (727.0, 86.0)          # sheet position of model (y 0 -> off-sheet; see make_views), z 2.04

SEC_B_X = None                 # set in draw(): PAX 3/4 occupant arm


def mm(v):
    return f"{float(v) * 1000:.0f}"


def sgn_mm(v):
    r = int(round(float(v) * 1000))
    return f"{r:+d}" if r else "0"


# =====================================================================================================================
# small geometry helpers
# =====================================================================================================================
def _arc(c, r, a0, a1, n=12):
    a = np.radians(np.linspace(a0, a1, n))
    return np.c_[c[0] + r * np.cos(a), c[1] + r * np.sin(a)]


def rrect(u0, v0, u1, v1, r, n=6):
    """Closed round-cornered rectangle (N, 2)."""
    r = min(r, 0.5 * abs(u1 - u0), 0.5 * abs(v1 - v0))
    return np.vstack([_arc((u1 - r, v0 + r), r, -90, 0, n), _arc((u1 - r, v1 - r), r, 0, 90, n),
                      _arc((u0 + r, v1 - r), r, 90, 180, n), _arc((u0 + r, v0 + r), r, 180, 270, n)])


def ellipse(c, a, b, n=48):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.c_[c[0] + a * np.cos(t), c[1] + b * np.sin(t)]


hull = I._hull


def capsule(a, b, ra, rb=None, n=16):
    rb = ra if rb is None else rb
    return hull(np.vstack([ellipse(a, ra, ra, n), ellipse(b, rb, rb, n)]))


def local(o, fx, U, V=None):
    """Seat-local (u forward, v up) -> side view (x, z): x = o_x + fx u, z = o_z + v."""
    P = np.asarray(U, float) if V is None else np.c_[U, V]
    return np.c_[o[0] + fx * P[:, 0], o[1] + P[:, 1]]


def clip_poly(P, box):
    """Sutherland-Hodgman: the closed polygon P (N, 2) clipped to the axis-aligned box (a0, b0, a1, b1)."""
    out = [tuple(p) for p in np.asarray(P, float)]
    for ax, lim, keep_ge in ((0, box[0], True), (0, box[2], False), (1, box[1], True), (1, box[3], False)):
        if not out:
            break
        inp, out = out, []
        for i, cur in enumerate(inp):
            prv = inp[i - 1]
            ci = cur[ax] >= lim if keep_ge else cur[ax] <= lim
            pi = prv[ax] >= lim if keep_ge else prv[ax] <= lim
            if ci != pi:
                t = (lim - prv[ax]) / (cur[ax] - prv[ax])
                out.append((prv[0] + t * (cur[0] - prv[0]), prv[1] + t * (cur[1] - prv[1])))
            if ci:
                out.append(cur)
    return np.array(out) if len(out) >= 3 else None


def _runs(mask):
    idx = np.flatnonzero(mask)
    if not len(idx):
        return []
    br = np.flatnonzero(np.diff(idx) > 1)
    return [np.arange(a, b + 1) for a, b in zip(np.r_[idx[0], idx[br + 1]], np.r_[idx[br], idx[-1]])]


# =====================================================================================================================
# drawing primitives on a view
# =====================================================================================================================
def poly(ds, v, P, w=W_FINE, fill=None, dash=None, color=None, closed=True):
    ds.cv.path(v.pts(np.asarray(P, float)), w, dash, closed=closed, fill=fill, stroke=w > 0, color=color)


def line(ds, v, P, w=W_FINE, dash=None, color=None):
    ds.cv.path(v.pts(np.asarray(P, float)), w, dash, color=color)


def arrow_head(ds, tip, d, L=1.8, W=0.65, color=None):
    d = np.asarray(d, float) / np.linalg.norm(d)
    n = np.array([-d[1], d[0]])
    tip = np.asarray(tip, float)
    b = tip - L * d
    ds.cv.polygon([tuple(tip), tuple(b + 0.5 * W * n), tuple(b - 0.5 * W * n)], fill=color or INK)


def dim(ds, p1, p2, pos, text, orient="h", size=TXT, color=INK, text_at=None, ext=True, gap=0.8, tag="dim",
        outside=None):
    """Compact linear dimension between sheet points p1, p2 (dimension line at y=pos for 'h', x=pos for 'v')."""
    p1, p2 = np.asarray(p1, float), np.asarray(p2, float)
    if orient == "h":
        a, b = np.array([p1[0], pos]), np.array([p2[0], pos])
    else:
        a, b = np.array([pos, p1[1]]), np.array([pos, p2[1]])
    if ext:
        for f, e in ((p1, a), (p2, b)):
            vv = e - f
            L = np.linalg.norm(vv)
            if L > gap + 0.2:
                u = vv / L
                ds.cv.line(tuple(f + gap * u), tuple(e + 1.2 * u), W_THIN, color=color)
    L = np.linalg.norm(b - a)
    u = (b - a) / max(L, 1e-9)
    tw = text_width(text, size, "mono")
    out = outside if outside is not None else L < 4.5
    if not out:
        ds.cv.line(tuple(a), tuple(b), W_THIN, color=color)
        arrow_head(ds, a, -u, color=color)
        arrow_head(ds, b, u, color=color)
    else:
        ds.cv.line(tuple(a - 3.5 * u), tuple(b + 3.5 * u), W_THIN, color=color)
        arrow_head(ds, a, u, color=color)
        arrow_head(ds, b, -u, color=color)
    if text_at is not None:
        tx, ty = text_at
    elif not out and L > tw + 4.0:
        tx, ty = 0.5 * (a + b)
    else:
        tx, ty = b + (4.5 + 0.5 * tw) * u
    if orient == "h":
        ds.text(tx, ty - 0.7, text, size, "mono", "middle", fill=color, tag=tag)
    else:
        ds.text(tx - 0.7, ty, text, size, "mono", "middle", rot=-90, fill=color, tag=tag)


def label(ds, X, Y, s, size=TXT, anchor="start", color=INK, weight=400, font="label", tag="lbl", rot=0.0):
    ds.text(X, Y, s, size, font, anchor, fill=color, weight=weight, tag=tag, vcenter=True, rot=rot)


def leader(ds, v, pt, dxy, s, size=TXT, color=INK, lines=None, dot=True, weight=600):
    """Leader from the model point pt to a text at sheet offset dxy (no box)."""
    X, Y = v.pt(*pt)
    tx, ty = X + dxy[0], Y + dxy[1]
    right = dxy[0] >= 0
    ds.cv.line((X, Y), (tx, ty), W_THIN, color=color)
    ds.cv.line((tx, ty), (tx + (2.0 if right else -2.0), ty), W_THIN, color=color)
    if dot:
        ds.cv.circle(X, Y, 0.35, w=0.0, fill=color or INK, stroke=False)
    L = [s] + list(lines or [])
    for i, t in enumerate(L):
        ds.text(tx + (2.6 if right else -2.6), ty + i * 1.25 * size, t, size, "label", "start" if right else "end",
                fill=color, weight=weight if i == 0 else 400, tag="lbl", vcenter=True)


def leader_to(ds, v, pt, tpt, s, anchor="start", size=TXT, color=INK, lines=None, weight=500, dot=True):
    """Leader from the model point pt to a text anchored at the model point tpt (anchor 'start' / 'end')."""
    P, T = v.pt(*pt), v.pt(*tpt)
    ds.cv.line(P, T, W_THIN, color=color)
    if dot:
        ds.cv.circle(P[0], P[1], 0.35, w=0.0, fill=color or INK, stroke=False)
    sg = 1.0 if anchor == "start" else -1.0
    e = (T[0] + sg * 1.5, T[1])
    ds.cv.line(T, e, W_THIN, color=color)
    for i, t in enumerate([s] + list(lines or [])):
        ds.text(e[0] + sg * 0.6, T[1] + i * 1.25 * size, t, size, "label", anchor, vcenter=True, fill=color,
                weight=weight if i == 0 else 400, tag="lbl")


def eye_symbol(ds, X, Y, r=1.1, color=ACCENT):
    ds.cv.circle(X, Y, r, w=W_FINE, fill=PAPER)
    ds.cv.line((X - 1.9 * r, Y), (X + 1.9 * r, Y), W_FINE, color=color)
    ds.cv.line((X, Y - 1.9 * r), (X, Y + 1.9 * r), W_FINE, color=color)


def srp_symbol(ds, X, Y, r=1.0):
    """Seat reference point: quartered circle."""
    ds.cv.circle(X, Y, r, w=W_FINE, fill=PAPER)
    for a0 in (0, 180):
        P = [(X, Y)] + [(X + r * math.cos(math.radians(a)), Y - r * math.sin(math.radians(a)))
                        for a in np.linspace(a0, a0 + 90, 8)]
        ds.cv.polygon(P, fill=INK)


def draw_pieces(ds, v, pcs, w=W_FINE, dash=None, color=None, only=None, fill=True):
    for nm, P, f in pcs:
        if only and nm not in only:
            continue
        poly(ds, v, P, 0.0 if nm == "rail" else w, fill=f if fill else None, dash=dash, color=color)


# =====================================================================================================================
# outlines built from the parameters
# =====================================================================================================================
def crew_seat_side(srp, fl, head_c=None, recline=0.0, arm_up=False):
    """Crew seat pieces in side view [(name, (N,2) x-z polygon, fill)] for an SRP (x, z); fl = floor WL.  The outline
    is interior.crew_seat_profile() / crew_base_profile() (the same geometry the headrest / divider check uses)."""
    o = np.asarray(srp, float)
    fx = -1.0
    pcs, stalks = I.crew_seat_profile(head_c, recline, arm_up)
    base = I.crew_base_profile(fl - o[1])
    out = [("vest", local(o, fx, base["vest"]), VEST_FILL), ("plate", local(o, fx, base["plate"]), SHELL_FILL),
           ("rail", local(o, fx, base["rail"]), INK), ("pan", local(o, fx, pcs["pan"]), SHELL_FILL),
           ("cushion", local(o, fx, pcs["cushion"]), SEAT_FILL), ("back", local(o, fx, pcs["back"]), SEAT_FILL),
           ("fleece_seat", local(o, fx, pcs["fleece_seat"]), FLEECE_FILL),
           ("fleece_back", local(o, fx, pcs["fleece_back"]), FLEECE_FILL),
           ("head", local(o, fx, pcs["head"]), SHELL_FILL), ("arm", local(o, fx, pcs["arm"]), SHELL_FILL)]
    return out, [local(o, fx, s) for s in stalks], local(o, fx, pcs["arm_pivot"][None, :])[0]


def exec_seat_side(rec, fl, raised=False, recline=None):
    """Executive seat pieces in side view [(name, polygon, fill)] for a seat record of interior.seat_map(); raised:
    the sliding headrest at the top of its travel; recline: back angle from vertical (deg), default upright."""
    e = I.EXEC_SEAT
    fx = -float(rec["facing"])
    o = np.array([rec["srp"][0], fl])                                   # local v = height above the floor
    sh, sf, ct, clt = e["srp_h"], e["srp_front"], e["cushion_top"], e["cushion_t"]
    bl_, bh = e["base_wh"]
    bu = e["base_u"]
    pt = ct - clt                                                      # pan top / cushion bottom
    a0, a1 = e["arm_u"]
    at, ah0 = e["arm_top"], e["arm_h0"]
    cl_, ch_ = e["arm_ctrl"]
    th = I.SEAT_TRACKS["h"]                                             # the seat stands on the surface tracks
    out = [("arm", local(o, fx, rrect(a0, ah0, a1, at, 0.02)), BASE_FILL),     # inboard arm panel (the far side)
           ("ctrl", local(o, fx, rrect(a1 - cl_ - 0.008, at - 0.025 - ch_, a1 - 0.008, at - 0.025, 0.008)), "#C3C8CB"),
           ("rail", local(o, fx, np.array([(bu - bl_ - 0.06, 0.0), (bu + 0.04, 0.0), (bu + 0.04, th),
                                           (bu - bl_ - 0.06, th)])), INK),
           ("base", local(o, fx, rrect(bu - bl_, th, bu, bh, 0.01)), BASE_FILL)]
    und = I.exec_under_profile(rec["facing"])                        # skirt; legrest on forward-facing seats (r3)
    out.append(("pan", local(o, fx, und["skirt"]), SHELL_FILL))
    if und["legrest"] is not None:
        out.append(("legrest", local(o, fx, und["legrest"]), SEAT_FILL))
    cush = np.array([(-0.04, pt - 0.01), (sf - 0.02, pt - 0.01), (sf, pt + 0.03), (sf - 0.01, ct - 0.01),
                     (sf - 0.05, ct), (-0.02, sh + 0.025)])
    out.append(("cushion", local(o, fx, cush), SEAT_FILL))
    pr = I.exec_back_profile(raised, recline)
    out.append(("back", local(o, fx, pr["back"]), SEAT_FILL))
    out.append(("head", local(o, fx, pr["head"]), SEAT_FILL))
    return out, [local(o, fx, pr["posts"])]


def manikin_side(p):
    """Side-view manikin pieces [(polygon, fill)] from a pose of interior.seated_pose(), far-to-near order."""
    fx, s = p["fx"], p["scale"]
    H, S = p["H"], p["shoulder"]
    L = np.linalg.norm(S - H)
    t = (S - H) / L
    nf = np.array([t[1], -t[0]]) if fx * t[1] > 0 else np.array([-t[1], t[0]])
    if np.dot(nf, [fx, 0.0]) < 0:
        nf = -nf
    prof = [(-0.05, -0.13), (0.30, -0.125), (0.70, -0.115), (1.00, -0.085), (1.10, -0.02), (1.08, 0.06),
            (0.92, 0.12), (0.62, 0.14), (0.35, 0.12), (0.12, 0.135), (-0.02, 0.10), (-0.10, 0.02), (-0.10, -0.08)]
    torso = np.array([H + a * L * t + b_ * s * nf for a, b_ in prof])
    out = [(capsule(S, p["elbow"], 0.045 * s, 0.040 * s), MAN_FILL, "far arm")]
    out.append((torso, MAN_FILL, "torso"))
    out.append((capsule(H, p["knee"], p["thigh_r"], 0.062 * s), MAN_FILL, "thigh"))
    out.append((capsule(p["knee"], p["ankle"], 0.058 * s, 0.040 * s), MAN_FILL, "shank"))
    heel, ball, toe, ank = p["heel"], p["ball"], p["toe"], p["ankle"]
    d = (toe - heel) / max(np.linalg.norm(toe - heel), 1e-9)
    nn = np.array([-d[1], d[0]]) if d[0] * fx > 0 else np.array([d[1], -d[0]])
    if nn[1] < 0:
        nn = -nn
    foot = np.array([heel, heel + 0.05 * s * nn - 0.02 * s * d, ank + 0.04 * s * nn,
                     ball + 0.06 * s * nn, toe + 0.025 * s * nn, toe, ball - 0.005 * nn, heel])
    out.append((hull(foot), MAN_FILL, "foot"))
    nk_a = S + np.array([fx * 0.03 * s, 0.05 * s])
    nk_b = p["head_c"] + np.array([-fx * 0.02 * s, -0.07 * s])
    out.append((capsule(nk_a, nk_b, 0.055 * s), MAN_FILL, "neck"))
    a, b_ = p["head_ab"]
    out.append((ellipse(p["head_c"], a, b_), MAN_FILL, "head"))
    out.append((capsule(S, p["elbow"], 0.048 * s, 0.042 * s), MAN_FILL, "arm"))
    out.append((capsule(p["elbow"], p["hand"], 0.040 * s, 0.035 * s), MAN_FILL, "forearm"))
    out.append((ellipse(p["hand"], 0.045 * s, 0.040 * s, 20), MAN_FILL, "hand"))
    return out


def manikin_front(yc, p, man=None, crew=False, fill=MAN_FILL, cut_x=None):
    """Front-view manikin pieces [(polygon (y, z), fill, forward)] centred on butt line yc, heights from the pose p:
    body, arm lines (fill None), neck, head, and per leg the knee, the shank (projected: from the knee down to the
    ankle -- for the crew out to the foot on the pedal, interior.crew_leg_y) and the foot; crew: the hands on the yoke
    grips.  cut_x: the station of a section looking aft; 'forward' marks the pieces that lie forward of it (knees,
    shanks, feet, hands), which a section view draws in phantom."""
    m = man or I.MANIKIN
    s = p["scale"]
    zs = p["shoulder"][1]
    seat = p["srp"][1]
    hb = 0.5 * s * m["head_lwh"][1]
    bd = 0.5 * s * m["bideltoid"]
    hp = 0.5 * s * m["hip_br"]

    def fwd(x):
        return cut_x is not None and float(x) < cut_x
    body = np.array([(-bd, zs - 0.07), (-bd + 0.02, zs + 0.02), (-0.16 * s, zs + 0.06), (-0.07 * s, zs + 0.075),
                     (0.07 * s, zs + 0.075), (0.16 * s, zs + 0.06), (bd - 0.02, zs + 0.02), (bd, zs - 0.07),
                     (bd - 0.02, seat + 0.25), (hp + 0.02, seat + 0.06), (hp, seat - 0.005), (-hp, seat - 0.005),
                     (-hp - 0.02, seat + 0.06), (-bd + 0.02, seat + 0.25)])
    out = [(np.c_[yc + body[:, 0], body[:, 1]], fill, False)]
    ze = p["elbow"][1]
    for sg in (-1, 1):                                                   # arm lines (inside the outline)
        out.append((np.c_[yc + sg * np.array([bd - 0.10 * s, bd - 0.10 * s]), [zs - 0.05, ze]], None, False))
    out.append((np.c_[yc + np.array([-0.055, 0.055, 0.055, -0.055]) * s,
                      [zs + 0.07, zs + 0.07, p["head_c"][1] - 0.08, p["head_c"][1] - 0.08]], fill, False))
    out.append((np.c_[yc + ellipse((0, 0), hb, 1, 48)[:, 0], p["head_c"][1] + p["head_ab"][1] *
                      ellipse((0, 0), 1, 1, 48)[:, 1]], fill, False))
    kz, az = p["knee"][1], p["ankle"][1]
    fz0, fz1 = sorted((float(p["heel"][1]), float(p["toe"][1])))
    ky = I.knee_half(p)
    ay = p["leg_y"][2] if "leg_y" in p else ky
    kr = 0.062 * s
    for sg in (-1, 1):
        yk, ya = yc + sg * ky, yc + sg * ay
        out.append((capsule((yk, kz), (ya, az), 0.056 * s, 0.042 * s), fill,
                    fwd(0.5 * (p["knee"][0] + p["ankle"][0]))))
        out.append((np.c_[yk + ellipse((0, 0), kr, 1, 32)[:, 0], kz + kr * ellipse((0, 0), 1, 1, 32)[:, 1]], fill,
                    fwd(p["knee"][0])))
        out.append((rrect(ya - 0.05 * s, fz0 - 0.005, ya + 0.05 * s, max(fz1, fz0 + 0.03) + 0.06 * s, 0.015), fill,
                    fwd(0.5 * (p["heel"][0] + p["toe"][0]))))
    if crew:                                                             # hands on the yoke grips
        hy = abs(I.yoke_grip_y(I.yoke_hand_dz(), 1))
        for sg in (-1, 1):
            out.append((np.c_[yc + sg * hy + ellipse((0, 0), 0.04 * s, 1, 20)[:, 0],
                              p["hand"][1] + 0.04 * s * ellipse((0, 0), 1, 1, 20)[:, 1]], fill, fwd(p["hand"][0])))
    return out


def draw_manikin_side(ds, v, p, fill=MAN_FILL, dash=None, color=MAN_LINE):
    for P, f, nm in manikin_side(p):
        poly(ds, v, P, W_THIN, fill=fill if fill else None, color=color, dash=dash)


def draw_manikin_front(ds, v, yc, p, crew=False, fill=MAN_FILL, cut_x=None):
    """Front-view manikin; with cut_x (a section looking aft) the pieces forward of the cut are drawn in phantom on
    top (outline only)."""
    pcs = manikin_front(yc, p, crew=crew, fill=fill, cut_x=cut_x)
    for P, f, fw in pcs:
        if fw:
            continue
        if f is None:
            line(ds, v, P, W_THIN, None, MAN_LINE)
        else:
            poly(ds, v, P, W_THIN, fill=f, color=MAN_LINE)
    for P, f, fw in pcs:
        if fw:
            poly(ds, v, P, W_THIN, fill=None, dash=PHANTOM, color=MAN_LINE)


# =====================================================================================================================
# section helpers
# =====================================================================================================================
@lru_cache(maxsize=16)
def oml_section(x, n=721):
    t = np.linspace(0, 1, n)
    return F.section(np.full_like(t, x), t)[:, 1:]


@lru_cache(maxsize=16)
def lining_sec(x):
    L = I.lining_section(x)
    return np.vstack([L, L[:1]])


def clip_above(P, z0):
    """Pieces of a closed (y, z) polyline above water line z0."""
    return [P[r] for r in _runs(P[:, 1] >= z0) if len(r) > 1]


def plan_z():
    """Water line of the plan cut: just above the executive cushion."""
    return I.FLOOR["wl"] + I.EXEC_SEAT["cushion_top"] + 0.01


# =====================================================================================================================
# sheet
# =====================================================================================================================
def make_views(ds):
    vp = ds.add_view(side_view("profile", origin=ORG_PROF, scale=20, model_origin=(PROF_BOX[0], PROF_BOX[3]),
                               box=PROF_BOX))
    vn = ds.add_view(plan_view("plan", origin=ORG_PLAN, scale=20, model_origin=(PLAN_BOX[0], 0.0), box=PLAN_BOX))
    va = ds.add_view(front_view("section_A", origin=ORG_SA, scale=10, model_origin=(0.0, SEC_BOX[3]), box=SEC_BOX))
    vb = ds.add_view(front_view("section_B", origin=ORG_SB, scale=10, model_origin=(0.0, SEC_BOX[3]), box=SEC_BOX))
    vd = ds.add_view(side_view("detail_C", origin=ORG_DET, scale=10, model_origin=(DET_BOX[0], DET_BOX[3]),
                               box=DET_BOX))
    ds.add_view(side_view("detail_E1", origin=ORG_E1, scale=10, model_origin=(E1_BOX[0], E1_BOX[3]), box=E1_BOX))
    ds.add_view(side_view("detail_E2", origin=ORG_E2, scale=10, model_origin=(E2_BOX[0], E2_BOX[3]), box=E2_BOX))
    ds.add_view(M.aft_view("view_D", origin=ORG_D, scale=10, model_origin=(0.0, D_BOX[3]), box=D_BOX))
    ds.add_view(M.aft_view("detail_F", origin=ORG_F, scale=5, model_origin=(0.5 * (F_BOX[0] + F_BOX[2]), F_BOX[3]),
                           box=F_BOX))
    ds.add_view(side_view("detail_G", origin=ORG_G, scale=10, model_origin=(G_BOX[0], G_BOX[3]), box=G_BOX))
    return vp, vn, va, vb, vd


def draw(ds):
    global SEC_B_X
    SEC_B_X = float([s for s in I.SEAT_LAYOUTS[I.DEFAULT_LAYOUT]["seats"] if s["id"] == "PAX 3"][0]["occ"])
    draw_clean(ds)
    try:
        draw_overlay(ds)
    except Exception as e:                      # noqa: BLE001 -- the clean sheet must not depend on refs/cache
        ds.log.append(f"overlay skipped: {e}")


def context():
    return dict(crew=I.crew_checks(-1), cabin=I.cabin_checks(), seats=I.seat_map())


def draw_clean(ds):
    ds.frame_and_title(fields=dict(date=SHEET["date"]))
    vp, vn, va, vb, vd = make_views(ds)
    ctx = context()
    ds._ctx = ctx
    draw_profile(ds, vp, ctx)
    draw_plan(ds, vn, ctx)
    draw_section(ds, va, float(I.design_eye()[0]), "A", ctx)
    draw_section(ds, vb, SEC_B_X, "B", ctx)
    draw_detail(ds, vd, ctx)
    draw_seat_details(ds, ds.views["detail_E1"], ds.views["detail_E2"], ctx)
    draw_panel_view(ds, ds.views["view_D"], ctx)
    ev = I.design_eye(-1)
    Xa, Ya = vd.pt(ev[0] - 0.12, 2.47)
    M.view_arrow(ds, (Xa, Ya), (-1.0, 0.0), "D", length=8.0)
    # reference marks on the parent views
    xa, xb = float(I.design_eye()[0]), SEC_B_X
    for x, L in ((xa, "A"), (xb, "B")):
        M.cutting_plane(ds, vn, (x, 0.99), (x, -0.99), L, (1.0, 0.0), ext=1.5, length=6.0)
    M.detail_circle(ds, vp, 3.75, 1.85, 0.62, "C", at=(0.4, -1.0))
    # titles
    bl = abs(I.CREW_SEAT["bl"])
    xm = 0.5 * (vp.pt(PROF_BOX[0], 0)[0] + vp.pt(PROF_BOX[2], 0)[0])
    view_title(ds, xm, vp.pt(0, PROF_BOX[1])[1] + 19.0, f"INBOARD PROFILE AT BL {mm(bl)} P",
               "SEEN FROM PORT, PORT SIDEWALL REMOVED - PHANTOM R n°: RECLINE REACHED - SCALE 1:20")
    view_title(ds, xm, vn.pt(0, PLAN_BOX[1])[1] + 9.0, f"PLAN AT CUSHION HEIGHT (WL {mm(plan_z())})",
               f"SEEN FROM ABOVE, STARBOARD UP - {I.DEFAULT_LAYOUT} LAYOUT - PHANTOM BEHIND EACH SEAT: RECLINED "
               "BACK - SCALE 1:20")
    for v, L, x, extra in ((va, "A", xa, "KNEES, LEGS, HANDS"), (vb, "B", xb, "KNEES, LEGS")):
        view_title(ds, v.pt(0, 0)[0], v.pt(0, SEC_BOX[1])[1] + 9.5, f"SECTION {L}-{L}",
                   f"STA {mm(x)}, LOOKING AFT (STBD LEFT) - SCALE 1:10")
        X, Y = v.pt(0, SEC_BOX[1])
        ds.text(X, Y + 17.0, f"PHANTOM: {extra} FORWARD OF THE CUT" + (" - BROWN: FR34 HEADER + ROD, BEYOND"
                                                                      if L == "B" else ""),
                TXT, "label", "middle", fill=MUTED, tag="lbl")
    view_title(ds, 0.5 * (vd.pt(DET_BOX[0], 0)[0] + vd.pt(DET_BOX[2], 0)[0]), vd.pt(0, DET_BOX[1])[1] + 12.0,
               "DETAIL C - CREW STATION", f"LEFT SEAT, BL {mm(bl)} P, SEEN FROM PORT - SCALE 1:10")
    draw_yoke_sweep(ds, ds.views["detail_F"], ctx)
    draw_table_detail(ds, ds.views["detail_G"], ctx)
    M.detail_circle(ds, vp, 6.52, 1.75, 0.50, "G", at=(-0.2, -1.0))
    draw_tables(ds, ctx)
    draw_notes(ds, ctx)
    revisions_block(ds, COL_X[0] + 4.0, 430.0, COL_X[1])
    M.break_paths_at_text(ds, lambda d: d.get("color") == GRID, pad=0.4)
    M.break_paths_at_text(ds, lambda d: d.get("w") == W_THIN and d.get("color") in (None, INK, MUTED)
                          and not d.get("closed"), pad=0.3)


# ---------------------------------------------------------------------------------------------------- profile
def frames_list(x0=3.0, x1=9.8):
    return [(n, x) for n, x in I.frame_stations() if x0 <= x <= x1]


def headliner_at(xs, bl):
    return np.array([I.lining_crown(x, bl) for x in xs])


def draw_openings_side(ds, v, box, sides=(-1, 1)):
    """Port openings (in the removed port wall: phantom) and starboard openings (the far wall: thin)."""
    tab = FP.openings_table()
    for r in tab:
        if r["side"] not in sides:
            continue
        if r["kind"] == "window":
            P = FP.window_outline(r["cx"], 120)
        else:
            o = {"door_airstair": FP.AIRSTAIR, "door_cargo": FP.CARGO, "exit_hatch": FP.EXIT}[r["id"]]
            P = FP.opening_outline(o)
        if r["side"] < 0:
            for Q in M.clip_polyline(P, box):
                line(ds, v, Q, W_THIN, PHANTOM, MUTED)
        else:
            for Q in M.clip_polyline(P, box):
                line(ds, v, Q, W_THIN, None, FAR)


def glazing_side():
    E = CG.edges(-1, which=("ws", "sw"), dx=0.003)
    return {k: max(E[k], key=len)[:, [0, 2]] for k in ("ws", "sw")}


_GLZ = None


def glz():
    global _GLZ
    if _GLZ is None:
        _GLZ = glazing_side()
    return _GLZ


def draw_fr34_side(ds, v, fl):
    """FR34 partition in side view: veneer arch header from the curtain rod to the headliner, pleated curtain below."""
    bg = I.BAGGAGE
    xp = bg["partition_x"]
    zp = headliner_at([xp], 0.0)[0]
    zr = fl + bg["bar_h"]
    ht, ct = bg["header_t"], bg["curtain_t"]
    poly(ds, v, [(xp - 0.5 * ht, zr), (xp + 0.5 * ht, zr), (xp + 0.5 * ht, zp), (xp - 0.5 * ht, zp)], W_FINE,
         fill=VENEER)
    zz = np.linspace(fl + 0.01, zr - 0.01, 22)
    xx = xp + np.where(np.arange(len(zz)) % 2 == 0, -0.5 * ct, 0.5 * ct)
    poly(ds, v, np.vstack([[(xp - 0.5 * ct, zr), (xp + 0.5 * ct, zr)], np.c_[xx[::-1] * 0 + xp + 0.5 * ct, zz[::-1]],
                           np.c_[np.full(len(zz), xp - 0.5 * ct), zz]]), 0.0, fill=CURTAIN)
    line(ds, v, np.c_[xx, zz], W_THIN, None, "#9A6A3E")
    line(ds, v, [(xp - 0.06, zr), (xp + 0.06, zr)], W_OBJ)


def draw_curtain_side(ds, v, fl, bl):
    """Divider curtain in a side view cut at butt line bl (beyond the cut): the flared stowed bundle from the floor to
    its flare top, the gathered curtain above it running flat to the track at the headliner; the part above the
    cut's headliner line is hidden (dashed)."""
    x0, x1, y0, y1, zt, xt = I.curtain_bundle()
    zh = I.lining_crown(xt, 0.5 * (y0 + y1))
    zv = I.lining_crown(xt, bl) - 0.004                                 # the cut's headliner: hidden above
    xg = xt - 0.009                                                    # gathered curtain, fwd face
    P = np.array([(x0, fl + 0.004), (x1, fl + 0.004), (x1, zv), (xg, zv), (xg, zt + 0.10), (x0, zt)])
    poly(ds, v, P, W_THIN, fill=CURTAIN, color="#9A6A3E")
    for x in np.linspace(x0 + 0.015, x1 - 0.012, 3):
        line(ds, v, [(x, fl + 0.02), (x, zt - 0.02)], W_THIN, None, "#9A6A3E")
    line(ds, v, [(xg, zv), (xg, zh - 0.012)], W_THIN, (1.2, 0.7), "#9A6A3E")
    poly(ds, v, [(xt - 0.012, zh - 0.012), (xt + 0.012, zh - 0.012), (xt + 0.012, zh), (xt - 0.012, zh)], W_THIN,
         fill=None, dash=(1.2, 0.7), color="#9A6A3E")


def draw_profile(ds, v, ctx):
    cv = ds.cv
    x0, z0, x1, z1 = PROF_BOX
    fl = I.FLOOR["wl"]
    # station grid: frames (numbered), labels above the crown
    frs = frames_list(3.0, 9.76)
    for n, x in frs:
        line(ds, v, [(x, float(F.z_bot(x))), (x, float(F.z_top(x)))], W_GRID, None, GRID)
    for n, x in frs:
        X, Y = v.pt(x, z1)
        big = n in F.FRAMES or n in ("FR34",)
        ds.text(X, Y - 5.8, n.replace("FR", ""), TXT, "label", "middle", weight=600 if big else 400, fill=GRID,
                tag="grid")
        if big:
            ds.text(X, Y - 2.8, mm(x), TXT, "mono", "middle", fill=GRID, tag="grid")
    X0, Y0 = v.pt(x0, z1)
    ds.text(X0 - 1.5, Y0 - 5.8, "FR", TXT, "label", "end", weight=600, fill=GRID, tag="grid")
    ds.text(X0 - 1.5, Y0 - 2.8, "STA", TXT, "label", "end", fill=GRID, tag="grid")
    for z in (1.0, 1.5, 2.0, 2.5):
        p, q = v.pt(x0, z), v.pt(x1, z)
        cv.line(p, q, W_GRID, (1.0, 1.4), color=GRID)
        ds.text(p[0] - 1.2, p[1], f"WL {mm(z)}", TXT, "mono", "end", vcenter=True, fill=GRID, tag="grid")
    # OML crown / keel on the centreline
    xs = np.linspace(x0, x1, 500)
    line(ds, v, np.c_[xs, F.z_top(xs)], W_OBJ)
    line(ds, v, np.c_[xs, F.z_bot(xs)], W_OBJ)
    # glazing (port, projected) and openings
    G = glz()
    for k in ("ws", "sw"):
        poly(ds, v, G[k], W_THIN, fill=GLASS_FILL, color=FAR)
    draw_openings_side(ds, v, PROF_BOX, sides=(1,))
    # headliner at the seat BL and on the centreline
    bl = abs(I.CREW_SEAT["bl"])
    xl = np.linspace(3.35, I.BAGGAGE["aft_x"], 90)
    line(ds, v, np.c_[xl, headliner_at(xl, bl)], W_FINE)
    line(ds, v, np.c_[xl, headliner_at(xl, 0.0)], W_THIN, (2.0, 1.0), MUTED)
    # floors: flight deck + cabin (flush), baggage floor; carry-through (hidden), nose tunnel (hidden)
    xf0 = I.FLOOR["fd_x0"]
    xa = I.BAGGAGE["aft_x"]
    wx0, wx1 = I.FLOOR["wing_x"]
    for a, b_, t in ((xf0, wx0, I.FLOOR["t"]), (wx0, wx1, I.FLOOR["t_wing"]), (wx1, xa, I.FLOOR["t"])):
        poly(ds, v, [(a, fl), (b_, fl), (b_, fl - t), (a, fl - t)], 0.0, fill=FLOOR_FILL)
    line(ds, v, [(xf0, fl), (xa, fl)], CUT)
    line(ds, v, [(wx0, fl - I.FLOOR["t_wing"]), (wx1, fl - I.FLOOR["t_wing"])], W_THIN, (1.6, 0.8), MUTED)
    from model.gear import NOSE_TUNNEL as TU
    line(ds, v, [(TU["x0"], fl - 0.03), (TU["x0"], TU["z_top"]), (TU["x1"], TU["z_top"]), (TU["x1"], fl - 0.03)],
         W_THIN, (1.6, 0.8), MUTED)
    # divider (port wall cut), lavatory (stbd, beyond), cabinets
    dx1 = I.DIVIDER["x_aft"]
    dx0 = dx1 - I.DIVIDER["t"]
    zc = headliner_at([dx1], bl)[0]
    lz = I.LAVATORY
    lx0, lx1 = lz["x"]
    zl = I.lining_crown(lx1, lz["inboard_bl"])
    poly(ds, v, [(lx0, fl), (lx1, fl), (lx1, zl), (lx0, zl)], W_THIN, fill="#EFEAE0", color=FAR)
    d0, d1 = lz["door"]
    poly(ds, v, rrect(d0 + 0.02, fl + 0.05, d1 - 0.02, fl + 1.35, 0.03), W_THIN, fill=None, color=FAR)
    line(ds, v, [(0.5 * (d0 + d1), fl + 0.05), (0.5 * (d0 + d1), fl + 1.35)], W_THIN, (1.0, 0.8), FAR)
    # behind the doors (hidden): the cabinet wall to wall, the shelf module aft, the lit niche above it, the TP holder
    cx0, cx1, cdep, cht = lz["cabinet"]
    hid = (1.2, 0.7)
    poly(ds, v, [(cx0, fl), (cx1, fl), (cx1, fl + cht), (cx0, fl + cht)], W_THIN, fill=None, dash=hid, color=FAR)
    line(ds, v, [(lz["shelf_x"], fl), (lz["shelf_x"], fl + cht)], W_THIN, hid, FAR)
    n0, n1 = lz["niche"]
    poly(ds, v, rrect(lz["shelf_x"] + 0.015, fl + n0, cx1 - 0.015, fl + n1, 0.02), W_THIN, fill=None, dash=hid,
         color=FAR)
    poly(ds, v, ellipse((lx1 - 0.06, fl + lz["tp_holder"][1]), 0.055, 0.055, 24), W_THIN, fill=None, dash=hid,
         color=FAR)
    cr = I.CABINETS["rh"]
    poly(ds, v, [(cr["x"][0], fl), (cr["x"][1], fl), (cr["x"][1], fl + cr["h"]), (cr["x"][0], fl + cr["h"])],
         W_THIN, fill=VENEER, color=FAR)
    poly(ds, v, [(dx0, fl), (dx1, fl), (dx1, zc), (dx0, zc)], W_FINE, fill=VENEER)
    draw_curtain_side(ds, v, fl, bl)
    cl = I.CABINETS["lh"]
    poly(ds, v, [(cl["x"][0], fl), (cl["x"][1], fl), (cl["x"][1], fl + cl["h"]), (cl["x"][0], fl + cl["h"])],
         W_FINE, fill=VENEER)
    # ledges: port cut (band), stbd beyond (line)
    lg = I.LEDGES
    for side, a, b_ in lg["runs"]:
        zt = fl + lg["top_h"]
        if side < 0:
            poly(ds, v, [(a, zt), (b_, zt), (b_, zt - lg["fascia"]), (a, zt - lg["fascia"])], W_THIN, fill=LEDGE_FILL)
        else:
            line(ds, v, [(a, zt), (b_, zt)], W_THIN, None, FAR)
    draw_openings_side(ds, v, PROF_BOX, sides=(-1,))
    # flight deck (simplified at 1:20): panel + glareshield, pedestal, yoke, pedals
    p95 = ctx["crew"]["occ"]["p95m"]
    draw_fd_side(ds, v, bl, simple=True, crank=p95["crank"])
    # seats: starboard (beyond, muted) first, then port (cut) with manikins and recline envelopes
    seats = [r for r in ctx["seats"] if not r.get("crew")]
    rec = ctx["cabin"]["recline"]
    for r in seats:
        if r["side"] > 0:
            pcs, posts = exec_seat_side(r, fl)
            draw_pieces(ds, v, pcs, W_THIN, dash=(1.2, 0.7), color="#8C979E", fill=False)
    for r in seats:
        if r["side"] < 0:
            ang = rec[r["id"]][0]
            pcs_r, _ = exec_seat_side(r, fl, raised=True, recline=ang)
            draw_pieces(ds, v, pcs_r, W_THIN, dash=PHANTOM, color=MUTED, only=("back", "head"), fill=False)
            pcs, posts = exec_seat_side(r, fl, raised=True)
            draw_pieces(ds, v, pcs)
            for P in posts:
                line(ds, v, P, W_THIN)
            draw_manikin_side(ds, v, I.cabin_pose(r))
            hp = dict((nm, P) for nm, P, f in pcs_r)["head"]            # reclined headrest
            k = int(np.argmax(np.abs(hp[:, 0] - r["srp"][0])))
            X, Y = v.pt(*hp[k])
            ds.text(X + (1.0 if r["facing"] > 0 else -1.0), Y + 2.4, f"R {ang:.0f}°", TXT, "mono",
                    "start" if r["facing"] > 0 else "end", fill=MUTED, tag="lbl")
    # crew seat + manikin (pilot, 95th pct at his setting)
    pt_ = p95["pose"]
    pcs, stalks, _ = crew_seat_side(I.crew_srp(-1, pt_["seat_dx"], pt_["seat_dz"])[[0, 2]], I.FLOOR["fd_wl"],
                                    head_c=pt_["head_lock"])
    draw_pieces(ds, v, pcs)
    for P in stalks:
        line(ds, v, P, W_THIN)
    draw_manikin_side(ds, v, pt_)
    # tables (deployed, phantom)
    for k, t in I.TABLES.items():
        if k not in I.SEAT_LAYOUTS[I.DEFAULT_LAYOUT]["tables"]:
            continue
        zt = fl + t["top_h"]
        poly(ds, v, [(t["x"][0], zt), (t["x"][1], zt), (t["x"][1], zt - t["t"]), (t["x"][0], zt - t["t"])],
             W_THIN, fill=None, dash=PHANTOM)
    # the table vs the club legs (cabin_checks 'table'): the 95th's knees (feet under the knees) run into it; the
    # 50th at PAX 3 with the feet forward (the least shank angle keeping CRITERIA knee_clear), phantom
    tp = ctx["cabin"]["table"]
    for r in seats:
        if r["side"] < 0 and r["id"] in ("PAX 1", "PAX 3"):
            q = I.cabin_pose(r)
            poly(ds, v, ellipse(q["knee"], q["knee_r"] + 0.012, q["knee_r"] + 0.012, 32), W_FINE, fill=None,
                 color=ACCENT)
    po = tp["p50m"]["posture"]
    if po["shank"] is not None:
        r3 = [r for r in seats if r["id"] == "PAX 3"][0]
        q = I.cabin_pose(r3, I.P50_SCALE, po["shank"])
        for P, f, nm in manikin_side(q):
            if nm in ("thigh", "shank", "foot"):
                poly(ds, v, P, W_THIN, fill=None, dash=PHANTOM, color=ACCENT)
    # FR34: veneer header + pleated curtain (PRO), aft wall
    draw_fr34_side(ds, v, fl)
    line(ds, v, [(xa, float(F.z_bot(xa)) + 0.05), (xa, headliner_at([xa], 0.0)[0])], W_OBJ)
    _profile_labels(ds, v, ctx)


def draw_fd_side(ds, v, bl, simple=False, crank=0.0, travel=False):
    """Panel + glareshield, pedestal, yoke (travel: + its pitch travel, phantom) and pedals (at crank) at butt line bl."""
    fl = I.FLOOR["fd_wl"]
    gp = I.glareshield_profile(bl)
    zlo = I.PANEL["mfd_z"] + I.PANEL["lower_dz"]
    ztop_face = gp[2][1] - 0.02
    body = np.vstack([gp, [[float(I.panel_x(ztop_face)), ztop_face], [float(I.panel_x(zlo)), zlo],
                           [3.30, zlo - 0.02], [3.26, gp[0][1] - 0.05]]])
    poly(ds, v, body, W_FINE, fill=SHELL_FILL)
    zp = I.PANEL["mfd_z"]
    h = I.PANEL["pdu_wh"][1]
    line(ds, v, [(float(I.panel_x(zp - 0.5 * h)) + 0.004, zp - 0.5 * h), (float(I.panel_x(zp + 0.5 * h)) + 0.004,
                                                                        zp + 0.5 * h)], W_OBJ + 0.25, None, "#233038")
    pp = I.pedestal_profile()
    poly(ds, v, pp, W_THIN, fill="#D9DCDE", color="#6F7B82")
    px0, px1, phw, pz = I.pedestal_plinth()
    poly(ds, v, [(px0, fl), (px1, fl), (px1, pz), (px0, pz)], W_THIN, fill="#CDD1D3", color="#6F7B82")
    hub = I.yoke_hub(-1)
    hw, hh, hd = I.YOKE["hub_whd"]
    xf = float(I.panel_x(hub[2]))
    if travel:
        for t in I.YOKE["travel"]:
            poly(ds, v, rrect(hub[0] + t, hub[2] - 0.5 * hh, hub[0] + hd + t, hub[2] + 0.5 * hh, 0.015), W_THIN,
                 fill=None, dash=PHANTOM, color=MUTED)
    line(ds, v, [(xf, hub[2]), (hub[0], hub[2])], 2 * I.YOKE["column_r"] * v.k * 0.9, None, "#6F7B82")
    poly(ds, v, rrect(hub[0], hub[2] - 0.5 * hh, hub[0] + hd, hub[2] + 0.5 * hh, 0.015), W_FINE, fill="#F4F4F2")
    p0, p1 = I.yoke_grip_axis(1)                                        # grip axis (y, z) about the hub centre
    gr = I.YOKE["grip"][1]
    g0 = np.array([hub[0] + 0.03, hub[2] + p0[1]])
    poly(ds, v, capsule(g0, g0 + np.array([0.0, p1[1] - p0[1]]), gr), W_THIN, fill="#2B3338")
    pd = I.pedal_points(crank)
    piv = np.array([I.PEDALS["pivot"][0], fl + I.PEDALS["pivot"][1]])
    line(ds, v, [piv, pd["heel"] + 0.06 * pd["dir"] + np.array([0.02, 0.0])], W_FINE)
    line(ds, v, [pd["heel"] + 0.03 * pd["dir"], pd["toe"]], W_OBJ + 0.3, None, "#2B3338")


def _profile_labels(ds, v, ctx):
    fl = I.FLOOR["wl"]
    x0, z0, x1, z1 = PROF_BOX
    Yb = v.pt(0, z0)[1]
    ords = [("EYE", float(I.design_eye()[0])), ("SRP", float(I.crew_srp()[0]))]
    names = {"PAX 1": "P1/2", "PAX 3": "P3/4", "PAX 5": "P5", "PAX 6": "P6"}
    for r in ctx["seats"]:
        if r["id"] in names:
            ords.append((names[r["id"]], r["occ"]))
    for lab, x in sorted(ords, key=lambda t: t[1]):
        X, Y = v.pt(x, fl)
        dx = -1.4 if lab == "EYE" else (1.4 if lab == "SRP" else 0.0)
        ds.cv.path([(X, Y + 0.8), (X, Yb - 0.5), (X + dx, Yb + 1.0)], W_THIN, (0.8, 0.6), color=MUTED)
        ds.text(X + dx + 0.6, Yb + 1.6, f"{mm(x)} {lab}", TXT, "mono", "start", rot=90, fill=MUTED, tag="ord")
    X, Y = v.pt(x0, z0)
    ds.text(X - 1.2, Yb + 3.0, "STA", TXT, "label", "end", weight=600, fill=MUTED, tag="ord")
    ds.text(X - 1.2, Yb + 5.6, "(POH ARMS)", TXT, "label", "end", fill=MUTED, tag="ord")
    # cabin length 5.16 (divider aft face -> baggage aft wall) above the frame labels
    xd, xa = I.DIVIDER["x_aft"], I.BAGGAGE["aft_x"]
    Y = v.pt(0, z1)[1] - 10.5
    dim(ds, v.pt(xd, 2.745), v.pt(xa, 2.745), Y,
        f"CABIN LENGTH {mm(ctx['cabin']['length'])}  ({mm(I.CABIN['length'])} PUBLISHED)",
        text_at=(v.pt(0.5 * (xd + xa), 0)[0], Y - 0.3))
    xp = I.BAGGAGE["partition_x"]
    Yf = v.pt(0, 1.015)[1]
    dim(ds, v.pt(xd, fl - 0.03), v.pt(xp, fl - 0.03), Yf,
        f"FLOOR LENGTH {mm(ctx['cabin']['floor_length'])}  ({mm(I.CABIN['floor_length'])} POH)",
        text_at=(v.pt(7.35, 0)[0], Yf - 0.3))
    X, Y = v.pt(0.5 * sum(I.LAVATORY["x"]), 2.47)
    for i, t in enumerate(("LAVATORY", "(STBD,", "BEYOND)")):
        ds.text(X, Y + 2.5 * i, t, TXT, "label", "middle", weight=600 if i == 0 else 400, fill="#5D6B73", tag="lbl")
    zb = 1.10
    lb = [((I.DIVIDER["x_aft"] - 0.012, fl + 0.30), (4.40, zb), f"DIVIDER {mm(I.DIVIDER['x_aft'])} (AFT FACE)", "end"),
          ((I.CABINETS["lh"]["x"][0] + 0.05, fl + 0.30), (5.18, zb), "CABINETS LH / RH", "start"),
          ((6.10, fl - 0.012), (6.20, 1.165), f"CARRY-THROUGH <= FLOOR - {mm(I.FLOOR['t_wing'])} (HIDDEN)", "start"),
          ((9.05, fl + I.LEDGES["top_h"]), (8.95, 1.12), f"LEDGE {mm(I.LEDGES['top_h'])} (PORT PART ON THE CARGO DOOR)",
           "end"),
          ((3.65, 1.40), (3.95, 1.03), "NOSE-WHEEL TUNNEL (HIDDEN)", "end")]
    for pt, tp, s_, anc in lb:
        P, T = v.pt(*pt), v.pt(*tp)
        ds.cv.line(P, T, W_THIN)
        ds.cv.circle(P[0], P[1], 0.35, w=0.0, fill=INK, stroke=False)
        e = (T[0] + (1.5 if anc == "start" else -1.5), T[1])
        ds.cv.line(T, e, W_THIN)
        ds.text(e[0] + (0.6 if anc == "start" else -0.6), T[1], s_, TXT, "label", anc, vcenter=True, weight=500,
                tag="lbl")
    xp = I.BAGGAGE["partition_x"]
    leader(ds, v, (xp, 2.30), (3.0, -4.0), "CURTAIN + VENEER HEADER FR34 (PRO)", weight=500,
           lines=[f"ROD {mm(I.BAGGAGE['bar_h'])}; NET = OPTION"])
    leader(ds, v, (9.55, fl + 0.02), (1.5, -9.0), "BAGGAGE", weight=500)
    t = I.TABLES["club_p"]
    xt = 0.5 * sum(t["x"]) + 0.10                                       # between the club heads, above the windows
    P, Q = v.pt(xt, fl + t["top_h"]), v.pt(xt, 2.415)
    ds.cv.line(P, Q, W_THIN)
    ds.cv.circle(P[0], P[1], 0.35, w=0.0, fill=INK, stroke=False)
    X, Y = v.pt(0.5 * sum(t["x"]), 2.445)
    ds.text(X, Y, f"CLUB TABLES DEPLOYED, TOP {mm(t['top_h'])} (DETAIL G)", TXT, "label", "middle", weight=500,
            vcenter=True, tag="lbl")
    leader(ds, v, (3.44, 2.30), (-4.0, -9.5), "PANEL + HOOD", weight=500)


# ---------------------------------------------------------------------------------------------------- plan
def seat_plan_exec(rec, recline=None):
    """Plan pieces of an executive seat (x, y); recline: the back / headrest footprint at that back angle."""
    e = I.EXEC_SEAT
    fx = -float(rec["facing"])
    o = np.array([rec["srp"][0], rec["bl"]])
    sf = e["srp_front"]
    cw, W_ = 0.5 * e["cushion_w"], 0.5 * e["width"]
    aw = e["arm_w"]
    pr = I.exec_back_profile(True, recline)
    rear = float(min(pr["back"][:, 0].min(), pr["head"][:, 0].min()))
    hrear = float(pr["head"][:, 0].min())
    hfront = float(pr["head"][:, 0].max())
    out = [("cushion", rrect(-0.03, -cw, sf, cw, 0.05), SEAT_FILL),
           ("back", np.array([(rear + 0.015, -0.5 * e["back_w"][0]), (-0.02, -0.5 * e["back_w"][1]),
                              (-0.02, 0.5 * e["back_w"][1]), (rear + 0.015, 0.5 * e["back_w"][0])]), SEAT_FILL),
           ("head", rrect(hrear, -0.5 * e["head_wh"][0], max(hfront, hrear + 0.06), 0.5 * e["head_wh"][0], 0.03),
            SEAT_FILL)]
    a0, a1 = e["arm_u"]
    si = -float(rec["side"])                                           # one arm, on the aisle (inboard) side
    out.append(("arm", rrect(a0, min(si * W_, si * (W_ - aw)), a1, max(si * W_, si * (W_ - aw)), 0.02), BASE_FILL))
    return [(nm, np.c_[o[0] + fx * P[:, 0], o[1] + P[:, 1]], f) for nm, P, f in out]


def seat_plan_crew(side, dx=0.0):
    c = I.CREW_SEAT
    o = I.crew_srp(side, dx)[:2]
    fx = -1.0
    D = c["pan_depth"]
    co = 0.5 * c["cushion_w"]
    ci = c["cushion_in"]
    nw, nd = c["notch_wd"]
    # local v positive = starboard; the inboard side is -side
    vin, vout = (-side) * ci, side * co
    lo, hi = min(vin, vout), max(vin, vout)
    cush = np.array([(-0.02, lo), (D - 0.03, lo), (D, lo + 0.03), (D, -0.5 * nw), (D - nd, -0.5 * nw + 0.01),
                     (D - nd, 0.5 * nw - 0.01), (D, 0.5 * nw), (D, hi - 0.03), (D - 0.03, hi), (-0.02, hi)])
    rear = -I.back_rear_offset()
    hh, hw, ht = c["head_hwt"]
    bw = c["back_w"][1]
    out = [("cushion", cush, SEAT_FILL),
           ("back", np.array([(rear + 0.03, -0.5 * bw + 0.02), (-0.02, -0.5 * bw), (-0.02, 0.5 * bw),
                              (rear + 0.03, 0.5 * bw - 0.02)]), SEAT_FILL),
           ("head", rrect(rear, -0.5 * hw, rear + ht, 0.5 * hw, 0.03), SHELL_FILL)]
    al, aw = c["arm_lw"]
    W_ = 0.5 * c["width"]
    pcs, _ = I.crew_seat_profile()
    u0 = float(pcs["arm_pivot"][0]) - 0.0225
    for sg in (-1, 1):
        out.append(("arm", rrect(u0, sg * W_ - (aw if sg > 0 else 0), u0 + al, sg * W_ + (aw if sg < 0 else 0), 0.02),
                    SHELL_FILL))
    return [(nm, np.c_[o[0] + fx * P[:, 0], o[1] + P[:, 1]], f) for nm, P, f in out]


def draw_plan(ds, v, ctx):
    cv = ds.cv
    x0, y0, x1, y1 = PLAN_BOX
    fl = I.FLOOR["wl"]
    zc = plan_z()
    cc = ctx["cabin"]
    for n, x in frames_list(3.0, 9.76):
        hw = float(F.half_w(x))
        line(ds, v, [(x, -hw), (x, hw)], W_GRID, None, GRID)
    for y in (-0.8, -0.4, 0.4, 0.8):
        p, q = v.pt(x0, y), v.pt(x1, y)
        cv.line(p, q, W_GRID, (1.0, 1.4), color=GRID)
        ds.text(p[0] - 1.2, p[1], f"BL {mm(abs(y))} {'S' if y > 0 else 'P'}", TXT, "mono", "end", vcenter=True,
                fill=GRID, tag="grid")
    cv.line(v.pt(x0 - 0.02, 0.0), v.pt(x1, 0.0), W_FINE, CHAIN, color=MUTED)
    X, Y = v.pt(x0 - 0.02, 0.0)
    ds.text(X - 1.2, Y, "CL", 2.2, "label", "end", vcenter=True, weight=600, tag="cl")
    xs = np.linspace(x0, x1, 400)
    for sg in (1, -1):
        line(ds, v, np.c_[xs, sg * F.half_w(xs)], W_OBJ)
    xl = np.linspace(3.30, I.BAGGAGE["aft_x"], 120)
    hwl = np.array([I.lining_half_width(x, zc) for x in xl])
    for sg in (1, -1):
        line(ds, v, np.c_[xl, sg * hwl], W_FINE)
    st = I.SEAT_TRACKS
    for y in st["bl"]:
        for sg in (-1, 1):
            line(ds, v, [(st["x0"], sg * y), (st["x1"], sg * y)], W_THIN, (3.0, 0.8, 0.6, 0.8), "#8C979E")
    # windows ticked on the sidewall
    for side, lst in I.windows_by_side().items():
        for wid, cx in lst:
            yy = side * (I.lining_half_width(cx, zc) + 0.01)
            line(ds, v, [(cx - FP.WIN_HX, yy), (cx + FP.WIN_HX, yy)], 1.1, None, "#5B89A6")
            name = wid.replace("win_", "").replace("door_cargo_win", "cd").replace("exit_hatch_win", "ex").upper()
            X, Y = v.pt(cx, side * (float(F.half_w(cx)) + 0.02))
            ds.text(X, Y + (-0.6 if side > 0 else 2.2), name, TXT, "label", "middle", fill="#5B89A6", tag="win")
    # CB panels (above the side consoles, above the cut: ticked on the sidewall)
    cb = I.SIDE_CONSOLE["cb_panel"]
    for sg in (-1, 1):
        yy = sg * (I.lining_half_width(0.5 * (cb[0] + cb[1]), fl + cb[2]) - 0.01)
        line(ds, v, [(cb[0], yy), (cb[1], yy)], 0.9, (1.0, 0.5), "#6F7B82")
    # doors: openings on the sidewall + swing zones
    A, C, EX = FP.AIRSTAIR, FP.CARGO, FP.EXIT
    for o, lab, reach in ((A, f"AIRSTAIR DOOR {mm(2 * A['hx'])} CLEAR, OPENS DOWN {A['open_deg']:.0f}°", 1.40),
                          (C, f"CARGO DOOR {mm(2 * C['hx'])} CLEAR, OPENS UP {C['open_deg']:.0f}°", 1.10)):
        xa, xb = o["cx"] - o["hx"], o["cx"] + o["hx"]
        yw = -float(F.half_w(o["cx"]))
        line(ds, v, [(xa, yw - 0.005), (xb, yw - 0.005)], 1.0, None, INK)
        yo = max(yw - reach, y0 + 0.02)
        poly(ds, v, [(xa, yw), (xb, yw), (xb, yo), (xa, yo)], W_THIN, fill=None, dash=PHANTOM, color=MUTED)
        X, Y = v.pt(0.5 * (xa + xb), yo)
        ds.text(X, Y - 2.8, lab, TXT, "label", "middle", fill=MUTED, tag="lbl")
    xa, xb = A["cx"] - A["hx"], A["cx"] + A["hx"]
    yl = -I.lining_half_width(A["cx"], zc)
    eb = I.CLEAR_ZONES["entry_bl"]
    _hatch(ds, v, [(xa, -eb), (xb, -eb), (xb, yl), (xa, yl)], "#8FB3C7")
    ex0, ex1 = EX["cx"] - EX["hx"], EX["cx"] + EX["hx"]
    ylx = I.lining_half_width(EX["cx"], zc)
    xb_ = I.CLEAR_ZONES["exit_bl"]
    _hatch(ds, v, [(ex0, xb_), (ex1, xb_), (ex1, ylx), (ex0, ylx)], "#E3A49C")
    line(ds, v, [(ex0, float(F.half_w(EX["cx"])) + 0.005), (ex1, float(F.half_w(EX["cx"])) + 0.005)], 1.0)
    # flight deck: pedals, pedestal + plinth, consoles, panel (hidden), glareshield (hidden), yokes
    px0, px1, phw, pz = I.pedestal_plinth()
    poly(ds, v, [(px0, -phw), (px1, -phw), (px1, phw), (px0, phw)], W_THIN, fill=None, dash=(1.6, 0.8), color=MUTED)
    pe = I.PEDESTAL
    poly(ds, v, rrect(pe["x"][0], -pe["hw"], pe["x"][1], pe["hw"], 0.02), W_FINE, fill="#D9DCDE")
    poly(ds, v, rrect(3.54, -I.PANEL["stack_hw"], pe["x"][0], I.PANEL["stack_hw"], 0.01), W_THIN, fill="#D9DCDE")
    sc = I.SIDE_CONSOLE
    for sg in (-1, 1):
        xs_ = np.linspace(sc["x"][0], sc["x"][1], 20)
        yo = np.array([I.lining_half_width(x, fl + sc["top_h"]) for x in xs_])
        P = np.vstack([np.c_[xs_, sg * np.full_like(xs_, sc["inner_bl"])], np.c_[xs_[::-1], sg * yo[::-1]]])
        poly(ds, v, P, W_FINE, fill=LEDGE_FILL)
    pd = I.pedal_points()
    for sg in (-1, 1):
        for d in (-1, 1):
            yc = sg * I.CREW_SEAT["bl"] + d * I.PEDALS["dy"]
            w = 0.5 * I.PEDALS["pad_wh"][0]
            poly(ds, v, [(pd["toe"][0], yc - w), (pd["heel"][0] - 0.02, yc - w), (pd["heel"][0] - 0.02, yc + w),
                         (pd["toe"][0], yc + w)], W_FINE, fill="#AAB2B7")
    ys = np.linspace(-0.70, 0.70, 60)
    line(ds, v, np.c_[I.panel_x(np.full_like(ys, I.PANEL["mfd_z"])), ys], W_FINE, (1.6, 0.8))
    lip = np.array([I.glareshield_lip(y) for y in ys])
    line(ds, v, np.c_[lip[:, 0], ys], W_THIN, (1.6, 0.8))
    for sg in (-1, 1):
        hub = I.yoke_hub(sg)
        hw_, hh, hd = I.YOKE["hub_whd"]
        poly(ds, v, rrect(hub[0], hub[1] - 0.5 * I.YOKE["span"], hub[0] + hd, hub[1] + 0.5 * I.YOKE["span"], 0.02),
             W_THIN, fill=None, dash=(1.6, 0.8))
    # crew seats (centre notch) + fore / aft notches (phantom)
    for sg in (-1, 1):
        for dx in (-I.CREW_SEAT["travel_x"], I.CREW_SEAT["travel_x"]):
            for nm, P, f in seat_plan_crew(sg, dx):
                if nm in ("cushion", "head"):
                    poly(ds, v, P, W_THIN, fill=None, dash=PHANTOM, color=MUTED)
        for nm, P, f in seat_plan_crew(sg):
            poly(ds, v, P, W_FINE, fill=f)
        X, Y = v.pt(*I.crew_srp(sg)[:2])
        srp_symbol(ds, X, Y, 0.8)
    # divider, lavatory, cabinets
    d1 = I.DIVIDER["x_aft"]
    d0 = d1 - I.DIVIDER["t"]
    ob0, ob1 = I.DIVIDER["open_bl"]
    hwd = I.lining_half_width(d1, zc)
    poly(ds, v, [(d0, -hwd), (d1, -hwd), (d1, ob0), (d0, ob0)], W_FINE, fill=VENEER)
    poly(ds, v, [(d0, ob1), (d1, ob1), (d1, hwd), (d0, hwd)], W_FINE, fill=VENEER)
    draw_divider_items_plan(ds, v)
    lz = I.LAVATORY
    lx0, lx1 = lz["x"]
    yi = lz["inboard_bl"]
    yo = I.lining_half_width(lx1, zc)
    tw = 0.03
    poly(ds, v, [(d1, yi), (lx1, yi), (lx1, yo), (lx1 - tw, yo), (lx1 - tw, yi + tw), (d1, yi + tw)], W_FINE,
         fill=VENEER)
    # cabinet wall to wall (toilet module fwd, padded shelf over a drawer aft), seat ring, open lid on the wall
    cx0, cx1, cdep, cht = lz["cabinet"]
    bx = lz["bowl_x"]
    xs_ = np.linspace(cx0, cx1, 12)
    yo_ = np.array([I.lining_half_width(x, fl + 0.3) for x in xs_])
    poly(ds, v, np.vstack([np.c_[xs_, yo_ - cdep], np.c_[xs_[::-1], yo_[::-1]]]), W_THIN, fill="#EFE8DC")
    tyo = I.lining_half_width(bx, fl + 0.3)
    sx = lz["shelf_x"]
    ysx = I.lining_half_width(sx, fl + 0.3)
    line(ds, v, [(sx, ysx - cdep), (sx, ysx)], W_THIN)
    poly(ds, v, rrect(sx + 0.015, ysx - cdep + 0.03, cx1 - 0.012, ysx - 0.02, 0.02), W_THIN, fill="#8E969B")
    rl, rw = lz["seat_ring"]
    yr = tyo - lz["seat_back"] - 0.5 * rw
    poly(ds, v, ellipse((bx, yr), 0.5 * rl, 0.5 * rw, 40), W_THIN, fill="#FFFFFF")
    poly(ds, v, ellipse((bx, yr + 0.01), 0.30 * rl, 0.28 * rw, 32), W_THIN, fill=None)
    poly(ds, v, [(bx - 0.5 * rl - 0.02, tyo - 0.035), (bx + 0.5 * rl + 0.02, tyo - 0.035),
                 (bx + 0.5 * rl + 0.02, tyo - 0.012), (bx - 0.5 * rl - 0.02, tyo - 0.012)], W_THIN, fill="#5E676C")
    # bi-fold doors: two doors of two panels each, hinged at the jambs, folded open (solid) and the fold envelope
    da, db_ = lz["door"]
    lf = lz["leaf"]
    for xh, s_ in ((da, 1), (db_, -1)):
        line(ds, v, [(xh, yi), (xh + s_ * 0.5 * lf, yi - 0.85 * lf), (xh + s_ * lf, yi)], W_THIN)
        line(ds, v, _arc((xh + s_ * lf, yi), lf, 180 if s_ > 0 else 270, 270 if s_ > 0 else 360, 12), W_THIN,
             (1.0, 0.8), MUTED)
    poly(ds, v, [(da, yi), (db_, yi), (db_, yi - lf), (da, yi - lf)], W_THIN, fill=None, dash=(0.8, 0.8), color=MUTED)
    # the seated 95th on the toilet, facing inboard (phantom footprint: thighs to the knee front)
    q = cc["lav_pose"]
    ys_ = cc["lav_seat_y"]
    kf = ys_ + (q["knee"][0] - q["knee_r"])
    for sg in (-1, 1):
        xk = bx + sg * I.MANIKIN["knee_y"]
        poly(ds, v, capsule((xk, ys_ - 0.12), (xk, kf + q["knee_r"]), q["knee_r"]), W_THIN, fill=None, dash=PHANTOM,
             color=ACCENT)
    # cabinets
    for k, c in I.CABINETS.items():
        a, b_ = c["x"]
        yo = I.lining_half_width(b_, zc)
        s_ = c["side"]
        poly(ds, v, [(a, s_ * c["bl_in"]), (b_, s_ * c["bl_in"]), (b_, s_ * yo), (a, s_ * yo)], W_FINE, fill=VENEER)
    # ledges (inner edge + lining) and the port segment on the cargo door
    lg = I.LEDGES
    for side, a, b_ in lg["runs"]:
        xs_ = np.linspace(a, b_, 30)
        yo = np.array([I.lining_half_width(x, fl + lg["top_h"] - 0.01) for x in xs_])
        yi_ = np.minimum(np.full_like(xs_, lg["inner_bl"]), yo - 0.02)
        P = np.vstack([np.c_[xs_, side * yi_], np.c_[xs_[::-1], side * yo[::-1]]])
        poly(ds, v, P, W_FINE, fill=LEDGE_FILL)
    s_, a, b_ = lg["door_segment"]
    for x in (a, b_):
        line(ds, v, [(x, s_ * lg["inner_bl"]), (x, s_ * (lg["inner_bl"] + 0.10))], W_THIN)
    # cabin seats: recline footprint (phantom), seat, SRP, number
    rec = cc["recline"]
    for r in ctx["seats"]:
        if r.get("crew"):
            continue
        ang = rec[r["id"]][0]
        for nm, P, f in seat_plan_exec(r, ang):
            if nm in ("back", "head"):
                poly(ds, v, P, W_THIN, fill=None, dash=PHANTOM, color=MUTED)
        for nm, P, f in seat_plan_exec(r):
            poly(ds, v, P, W_FINE, fill=f)
        X, Y = v.pt(r["srp"][0], r["bl"])
        srp_symbol(ds, X, Y, 0.7)
        ds.text(*v.pt(0.5 * (r["front"] + r["srp"][0]), r["bl"]), r["id"].replace("PAX ", ""), 2.2, "label", "middle",
                weight=700, vcenter=True, tag="seatno")
    # club four (port): the 95th feet interleaved -- PAX 3 at the seat CL +/-knee_y, PAX 1 outside them
    by = {r["id"]: r for r in ctx["seats"]}
    fa, fb = cc["club_feet_y"]
    fw = I.MANIKIN["foot_w"]
    for rid, off in (("PAX 3", fa), ("PAX 1", fb)):
        r = by[rid]
        p = I.cabin_pose(r)
        h_, t_ = p["heel"][0], p["toe"][0]
        for sg in (-1, 1):
            yc = r["bl"] + sg * off
            poly(ds, v, rrect(min(h_, t_), yc - 0.5 * fw, max(h_, t_), yc + 0.5 * fw, 0.04), W_THIN, fill=None,
                 dash=PHANTOM, color=ACCENT)
    # tables (deployed, phantom)
    for k in I.SEAT_LAYOUTS[I.DEFAULT_LAYOUT]["tables"]:
        t = I.TABLES[k]
        s_ = t["side"]
        poly(ds, v, rrect(t["x"][0], min(s_ * t["bl_in"], s_ * I.LEDGES["inner_bl"]), t["x"][1],
                          max(s_ * t["bl_in"], s_ * I.LEDGES["inner_bl"]), 0.03), W_FINE, fill=None, dash=PHANTOM)
    # FR34 curtain (pleats) + header, baggage floor end
    bg = I.BAGGAGE
    xp, xa = bg["partition_x"], bg["aft_x"]
    hwp = I.lining_half_width(xp, zc)
    yy = np.linspace(-hwp, hwp, 40)
    line(ds, v, np.c_[xp + np.where(np.arange(len(yy)) % 2 == 0, -0.5, 0.5) * bg["curtain_t"], yy], W_FINE, None,
         "#9A6A3E")
    poly(ds, v, [(xp - 0.5 * bg["header_t"], -hwp), (xp + 0.5 * bg["header_t"], -hwp),
                 (xp + 0.5 * bg["header_t"], hwp), (xp - 0.5 * bg["header_t"], hwp)], W_THIN, fill=None,
         dash=(1.6, 0.8), color=MUTED)
    hwa = I.lining_half_width(xa, fl + 0.05)
    line(ds, v, [(xa, -hwa), (xa, hwa)], W_OBJ)
    for x in bg["tiedowns"]:
        for y in (-0.35, -0.12, 0.12, 0.35):
            poly(ds, v, rrect(x - 0.015, y - 0.04, x + 0.015, y + 0.04, 0.01), W_THIN, fill=INK)
    _plan_dims(ds, v, ctx)


def draw_divider_items_plan(ds, v):
    """Divider curtain (DIVIDER curtain): the stowed bundle against the forward face at the opening edge, cut by the
    plan (pleats), and its track across the opening at the headliner (above the cut: hidden); the fire extinguisher
    on the forward face of the RH divider (DIVIDER extinguisher, cut near its top)."""
    x0, x1, y0, y1, zt, xt = I.curtain_bundle()
    ob0, ob1 = I.DIVIDER["open_bl"]
    line(ds, v, [(xt, ob0), (xt, ob1)], W_THIN, (1.6, 0.8), "#9A6A3E")
    poly(ds, v, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], W_THIN, fill=CURTAIN, color="#9A6A3E")
    yy = np.linspace(y0, y1, 9)
    xx = np.where(np.arange(len(yy)) % 2 == 0, x1 - 0.004, x0 + 0.004)
    line(ds, v, np.c_[xx, yy], W_THIN, None, "#9A6A3E")
    ex, ey, ez, ed, eh = I.DIVIDER["extinguisher"]
    poly(ds, v, ellipse((ex, ey), 0.5 * ed, 0.5 * ed, 24), W_THIN, fill=EXTING)


def _hatch(ds, v, P, color):
    P = np.asarray(P, float)
    poly(ds, v, P, W_THIN, fill=None, color=color)
    x0, x1 = P[:, 0].min(), P[:, 0].max()
    y0, y1 = P[:, 1].min(), P[:, 1].max()
    for c in np.arange(x0 - (y1 - y0), x1, 0.05):
        a = np.array([c, y0])
        b = np.array([c + (y1 - y0), y1])
        t0 = max(0.0, (x0 - a[0]) / (b[0] - a[0]))
        t1 = min(1.0, (x1 - a[0]) / (b[0] - a[0]))
        if t1 > t0:
            line(ds, v, [a + t0 * (b - a), a + t1 * (b - a)], 0.1, None, color)


def _plan_dims(ds, v, ctx):
    cc = ctx["cabin"]
    seats = {r["id"]: r for r in ctx["seats"]}
    e = I.EXEC_SEAT
    x = seats["PAX 3"]["srp"][0] + 0.10
    ya, yb = -(e["bl"] - 0.5 * e["width"]), e["bl"] - 0.5 * e["width"]
    dim(ds, v.pt(x, ya), v.pt(x, yb), v.pt(x, 0)[0], f"AISLE {mm(cc['aisle_arm'])}", "v",
        text_at=(v.pt(x, 0)[0] + 2.6, v.pt(0, 0)[1]))
    yP = -e["bl"]
    dim(ds, v.pt(seats["PAX 1"]["front"], yP), v.pt(seats["PAX 3"]["front"], yP), v.pt(0, -0.08)[1],
        f"{mm(cc['club_gap'])}")
    dim(ds, v.pt(seats["PAX 3"]["occ"], yP), v.pt(seats["PAX 5"]["occ"], yP), v.pt(0, -0.06)[1],
        f"PITCH {mm(cc['pitch_fwd'])}")
    dim(ds, v.pt(seats["PAX 5"]["occ"], e["bl"]), v.pt(seats["PAX 6"]["occ"], e["bl"]), v.pt(0, 0.06)[1],
        f"STAGGER {mm(cc['stagger'])}")
    X = v.pt(9.05, 0)[0]
    dim(ds, v.pt(9.05, 0.0), v.pt(9.05, e["bl"]), X, mm(e["bl"]), "v")
    X = v.pt(4.52, 0)[0]
    dim(ds, v.pt(4.52, 0.0), v.pt(4.52, I.CREW_SEAT["bl"]), X, mm(I.CREW_SEAT["bl"]), "v")
    x0c, x1c, y0c, y1c, _, _ = I.curtain_bundle()
    side_c = "LH" if I.DIVIDER["curtain"][0] < 0 else "RH"
    leader_to(ds, v, (0.5 * (x0c + x1c), 0.5 * (y0c + y1c)), (4.64, -0.095), f"CURTAIN, STOWED {side_c}", "start",
              lines=["TRACK AT THE HEADLINER"])
    ex_ = I.DIVIDER["extinguisher"]
    leader_to(ds, v, (ex_[0], ex_[1]), (4.33, 1.085), "FIRE EXTINGUISHER (RH DIVIDER, FWD FACE)", "start")
    A = FP.AIRSTAIR
    yl = -I.lining_half_width(A["cx"], plan_z())
    X = v.pt(A["cx"] + 0.12, 0)[0]
    dim(ds, v.pt(A["cx"], yl), v.pt(A["cx"], I.LAVATORY["inboard_bl"]), X, mm(I.LAVATORY["inboard_bl"] - yl), "v")
    yS, yP = 0.985, -0.985
    st = I.SEAT_TRACKS["bl"]
    lz = I.LAVATORY
    L = [((3.95, 0.72), (3.55, yS), "SIDE CONSOLES, CB PANELS ABOVE", "end"),
         ((4.80, 0.55), (4.40, yS + 0.03), "LAVATORY (TOILET OUTBOARD, BI-FOLD DOORS)", "start"),
         ((5.31, 0.46), (5.10, yS - 0.08), "CABINET RH", "end"),
         ((6.30, 0.62), (7.20, yS), "EXIT CLEAR ZONE (HATCH REMOVED INWARD)", "start"),
         ((8.00, 0.70), (8.40, yS), f"LEDGE {mm(I.LEDGES['top_h'])}", "start"),
         ((3.40, 0.0), (3.35, yP + 0.02), "PEDESTAL ON TUNNEL PLINTH", "end"),
         ((4.56, -0.60), (4.20, yP - 0.08), "DIVIDER", "end"),
         ((5.40, -0.50), (5.45, yP), "CABINET LH", "start"),
         ((4.97, -0.62), (5.56, yP - 0.10), f"ENTRY: NO FURNITURE AT |BL| > {mm(I.CLEAR_ZONES['entry_bl'])}", "start"),
         ((6.40, -0.30), (5.80, yP), "TABLES DEPLOYED (STOW FOR TTL)", "start"),
         ((8.95, st[1]), (8.98, yS - 0.05), f"SEAT TRACKS {mm(st[0])} / {mm(st[1])}", "start"),
         ((I.BAGGAGE["partition_x"], 0.35), (9.40, 0.60), "CURTAIN FR34", "start")]
    for pt, tp, s_, anc in L:
        leader_to(ds, v, pt, tp, s_, anc)
    # lavatory user, club feet, recline footprints
    q = cc["lav_pose"]
    kf = cc["lav_seat_y"] + (q["knee"][0] - q["knee_r"])
    leader_to(ds, v, (lz["bowl_x"] + 0.105, kf + 0.05), (5.55, 1.085),
              f"95TH SEATED: KNEES {mm(cc['lav_knee_past_door'])} PAST THE DOOR LINE", "start", color=ACCENT,
              lines=[f"(BI-FOLDS FOLD OUT <= {mm(lz['leaf'])})"])
    r1 = seats["PAX 1"]
    leader_to(ds, v, (r1["front"] + 0.25, r1["bl"] - cc["club_feet_y"][1]), (6.62, -1.085),
              f"95TH FEET INTERLEAVED (TOES PASS {mm(cc['club_toes_pass'])})", "start", color=ACCENT)


# ---------------------------------------------------------------------------------------------------- sections
def front_seat_crew(yc, fl, srp_z, side):
    """Crew seat in the section (looking aft, y = BL): the inboard cushion trimmed over the tunnel plinth."""
    c = I.CREW_SEAT
    co, ci = 0.5 * c["cushion_w"], c["cushion_in"]
    W_ = 0.5 * c["width"]
    b = math.radians(c["back_deg"])
    ztop = srp_z + c["back_len"] * math.cos(b)
    hh, hw, ht = c["head_hwt"]
    zh0 = srp_z + (c["head_c"] - 0.5 * hh) * math.cos(b)
    zh1 = srp_z + (c["head_c"] + 0.5 * hh) * math.cos(b)
    t0 = 0.025
    ctop, cbot = srp_z + t0, srp_z + t0 - c["cushion_t"]
    bw0, bw1 = 0.5 * c["back_w"][0], 0.5 * c["back_w"][1]
    s_in = -side                                                          # +1: the inboard side is +y (local)
    lo, hi = (-co, ci) if s_in > 0 else (-ci, co)
    back = np.vstack([[(-bw1, srp_z)], [(-bw1, srp_z + 0.35)], _arc((-bw0 + 0.06, ztop - 0.06), 0.06, 180, 90, 6),
                      _arc((bw0 - 0.06, ztop - 0.06), 0.06, 90, 0, 6), [(bw1, srp_z + 0.35)], [(bw1, srp_z)]])
    pb = c["base_w"] * 0.5
    pcs = [("back", back, SEAT_FILL),
           ("head", rrect(-0.5 * hw, zh0, 0.5 * hw, zh1, 0.04), SHELL_FILL)]
    for sg in (-1, 1):
        pcs.append(("plate", np.array([(sg * pb - 0.006, fl + 0.018), (sg * pb + 0.006, fl + 0.018),
                                       (sg * pb + 0.006, cbot - 0.035), (sg * pb - 0.006, cbot - 0.035)]), SHELL_FILL))
    lv = c["life_vest"]
    pcs.append(("vest", rrect(-0.5 * lv[1], fl + 0.035, 0.5 * lv[1], fl + 0.035 + lv[2], 0.01), VEST_FILL))
    pcs.append(("pan", rrect(lo + 0.01, cbot - 0.035, hi - 0.01, cbot, 0.005), SHELL_FILL))
    pcs.append(("cushion", rrect(lo, cbot, hi, ctop, 0.03), SEAT_FILL))
    ah = srp_z + c["arm_h"]
    al, aw = c["arm_lw"]
    for sg in (-1, 1):
        pcs.append(("arm", rrect(sg * W_ - (aw if sg > 0 else 0), ah - 0.045, sg * W_ + (aw if sg < 0 else 0), ah,
                                 0.015), SHELL_FILL))
    st = I.SEAT_TRACKS
    for sg in (-1, 1):
        y = sg * c["rail_dy"]
        pcs.append(("rail", rrect(y - 0.5 * st["w"], fl, y + 0.5 * st["w"], fl + st["crew_h"], 0.003), INK))
    return [(nm, np.c_[yc + P[:, 0], P[:, 1]], f) for nm, P, f in pcs]


def front_seat_exec(yc, fl, raised=False):
    """Executive seat seen from the front (looking aft at a forward-facing seat), centred on butt line yc: one arm, a
    deep side panel on the aisle side with the seat control on its forward face."""
    e = I.EXEC_SEAT
    hup = e["head_slide"] if raised else 0.0
    cw = 0.5 * e["cushion_w"]
    W_ = 0.5 * e["width"]
    bw, bh = e["base_wh"]
    pt = e["cushion_top"] - e["cushion_t"]
    zb = e["srp_h"] + 0.02
    pcs = [("back", np.array([(-0.5 * e["back_w"][1], fl + zb), (-0.5 * e["back_w"][0], fl + e["back_top"] - 0.03),
                              (-0.5 * e["back_w"][0] + 0.04, fl + e["back_top"]),
                              (0.5 * e["back_w"][0] - 0.04, fl + e["back_top"]),
                              (0.5 * e["back_w"][0], fl + e["back_top"] - 0.03), (0.5 * e["back_w"][1], fl + zb)]),
            SEAT_FILL),
           ("head", rrect(-0.5 * e["head_wh"][0], fl + e["head_top"] + hup - e["head_wh"][1], 0.5 * e["head_wh"][0],
                          fl + e["head_top"] + hup, 0.04), SEAT_FILL),
           ("base", rrect(-0.5 * bw, fl + I.SEAT_TRACKS["h"], 0.5 * bw, fl + bh, 0.01), BASE_FILL),
           ("pan", rrect(-cw + 0.01, fl + bh, cw - 0.01, fl + pt, 0.01), SHELL_FILL)]
    lg = I.exec_under_profile(1)["legrest"]                             # forward-facing: the legrest (review r3 F1)
    lw = e["legrest"][0]
    pcs.append(("legrest", rrect(-0.5 * lw, fl + lg[:, 1].min(), 0.5 * lw, fl + lg[:, 1].max(), 0.015), SEAT_FILL))
    pcs.append(("cushion", rrect(-cw, fl + pt, cw, fl + e["cushion_top"], 0.03), SEAT_FILL))
    si = -math.copysign(1.0, yc)                                        # the aisle side
    ya, yb = sorted((si * W_, si * (W_ - e["arm_w"])))
    pcs.append(("arm", rrect(ya, fl + e["arm_h0"], yb, fl + e["arm_top"], 0.015), BASE_FILL))
    ch = e["arm_ctrl"][1]
    pcs.append(("ctrl", rrect(ya + 0.012, fl + e["arm_top"] - 0.025 - ch, yb - 0.012, fl + e["arm_top"] - 0.025, 0.006),
                "#C3C8CB"))
    return [(nm, np.c_[yc + P[:, 0], P[:, 1]], f) for nm, P, f in pcs]


def draw_section(ds, v, x, letter, ctx):
    cv = ds.cv
    y0, z0, y1, z1 = SEC_BOX
    fl = I.FLOOR["wl"]
    crew = letter == "A"
    for y in (-0.8, -0.4, 0.4, 0.8):
        p, q = v.pt(y, z0), v.pt(y, z1)
        cv.line(p, q, W_GRID, (1.0, 1.4), color=GRID)
        ds.text(q[0], q[1] - 1.0, f"{mm(abs(y))} {'S' if y > 0 else 'P'}", TXT, "mono", "middle", fill=GRID,
                tag="grid")
    for z in (1.0, 1.5, 2.0, 2.5):
        p, q = v.pt(y1, z), v.pt(y0, z)
        cv.line(p, q, W_GRID, (1.0, 1.4), color=GRID)
        ds.text(p[0] - 1.0, p[1], f"WL {mm(z)}", TXT, "mono", "end", vcenter=True, fill=GRID, tag="grid")
    cv.line(v.pt(0, z0 + 0.02), v.pt(0, z1), W_FINE, CHAIN, color=MUTED)
    O = oml_section(round(x, 4))
    poly(ds, v, O, CUT, fill=None)
    L = lining_sec(round(x, 4))
    for Q in clip_above(L, fl):
        line(ds, v, Q, W_FINE)
    hwf = I.lining_half_width(x, fl + 0.003)
    poly(ds, v, [(-hwf, fl), (hwf, fl), (hwf, fl - I.FLOOR["t"]), (-hwf, fl - I.FLOOR["t"])], 0.0, fill=FLOOR_FILL)
    line(ds, v, [(-hwf, fl), (hwf, fl)], CUT)
    if crew:
        G = glz()["sw"]
        if G[:, 0].min() <= x <= G[:, 0].max():
            zlo, zhi = CG.SW_SILL, float(CG.z_sw_top(x))
            for sg in (-1, 1):
                zz = np.linspace(zlo, zhi, 30)
                P = np.c_[sg * np.array([float(F.side_y(x, z)) for z in zz]), zz]
                line(ds, v, P, 1.2, None, "#5B89A6")
    else:
        for side, lst in I.windows_by_side().items():
            for wid, cx in lst:
                if abs(cx - x) < FP.WIN_HX:
                    zz = np.linspace(FP.WIN_CZ - FP.WIN_HZ, FP.WIN_CZ + FP.WIN_HZ, 30)
                    P = np.c_[side * np.array([float(F.side_y(x, z)) for z in zz]), zz]
                    line(ds, v, P, 1.2, None, "#5B89A6")
    if crew:
        _section_crew(ds, v, x, ctx)
    else:
        _section_cabin(ds, v, x, ctx)


def _section_crew(ds, v, x, ctx):
    fl = I.FLOOR["fd_wl"]
    cc = ctx["crew"]
    c = I.CREW_SEAT
    px0, px1, phw, pz = I.pedestal_plinth()
    poly(ds, v, [(-phw, fl), (phw, fl), (phw, pz), (-phw, pz)], W_FINE, fill="#CDD1D3")
    pe = I.PEDESTAL
    zt = fl + pe["top_h"]
    if pe["x"][0] <= x <= pe["x"][1]:
        poly(ds, v, [(-pe["hw"], pz), (pe["hw"], pz), (pe["hw"], zt), (-pe["hw"], zt)], W_FINE, fill="#D9DCDE")
    sc = I.SIDE_CONSOLE
    if sc["x"][0] <= x <= sc["x"][1]:
        for sg in (-1, 1):
            zz = np.linspace(fl, fl + sc["top_h"], 12)
            yo = np.array([I.lining_half_width(x, z) for z in zz])
            P = np.vstack([np.c_[sg * np.full_like(zz, sc["inner_bl"]), zz], np.c_[sg * yo[::-1], zz[::-1]]])
            poly(ds, v, P, W_FINE, fill=LEDGE_FILL)
    ov = I.OVERHEAD
    if ov["x"][0] - 0.1 <= x <= ov["x"][1] + 0.1:
        zo = I.lining_crown(x, 0.0)
        poly(ds, v, [(-0.5 * ov["w"], zo), (0.5 * ov["w"], zo), (0.5 * ov["w"], zo - ov["depth"]),
                     (-0.5 * ov["w"], zo - ov["depth"])], W_FINE, fill="#5E676C")
    p = cc["occ"]["p95m"]["pose"]
    for sg in (-1, 1):
        srp = I.crew_srp(sg)
        dz = p["seat_dz"] if sg < 0 else 0.0
        for nm, P, f in front_seat_crew(sg * c["bl"], fl, srp[2] + dz, sg):
            poly(ds, v, P, W_FINE if nm != "rail" else 0.0, fill=f)
    yc = -c["bl"]
    draw_manikin_front(ds, v, yc, p, crew=True, cut_x=x)
    for sg in (-1, 1):
        e = I.design_eye(sg)
        X, Y = v.pt(e[1], e[2])
        eye_symbol(ds, X, Y, 0.8)
    zt_ = p["head_top"]
    zl = I.lining_crown(x, yc)
    X = v.pt(yc, 0)[0]
    dim(ds, v.pt(yc, zt_), v.pt(yc, zl), X - 7.0, mm(cc["headroom"]), "v", outside=True,
        text_at=(X - 9.6, v.pt(0, zl)[1] - 5.5))
    zsh = p["shoulder"][1] + 0.02
    ysh = yc - 0.5 * I.MANIKIN["bideltoid"]
    ylin = -I.lining_half_width(x, zsh)
    Y = v.pt(0, zsh)[1]
    dim(ds, v.pt(ysh, zsh), v.pt(ylin, zsh), Y, mm(cc["shoulder_room"]), "h", outside=True,
        text_at=(v.pt(ylin, 0)[0] - 1.0, Y - 2.2))
    e = I.design_eye(1)
    leader_to(ds, v, (e[1], e[2]), (0.60, 2.64), f"DESIGN EYE WL {mm(e[2])}", "end", color=ACCENT,
              lines=[f"NEUTRAL SRP WL {mm(cc['srp'][2])}, FLOOR {mm(fl)}"])
    Yd = v.pt(0, 1.13)[1]
    dim(ds, v.pt(-c["bl"], 1.13), v.pt(c["bl"], 1.13), Yd, f"SEAT CL {mm(2 * c['bl'])}")
    # ingress: between the seat backs at the lumbar (co-pilot side: neutral seat)
    ig = cc["ingress"]
    zb = I.crew_srp(1)[2] + 0.30
    yb0 = c["bl"] - 0.5 * c["back_w"][1]
    dim(ds, v.pt(-yb0, zb), v.pt(yb0, zb), v.pt(0, zb)[1], mm(ig["back_gap"]),
        text_at=(v.pt(0, 0)[0], v.pt(0, zb)[1] - 1.5))
    # plinth vs the trimmed cushion (right seat, neutral)
    zcu = I.crew_srp(1)[2] - 0.02
    yci = c["bl"] - c["cushion_in"]
    leader_to(ds, v, (yci, zcu), (0.60, 1.185), f"INBOARD CUSHION TRIMMED: {mm(cc['plinth_lat'])} TO THE PLINTH",
              "start", color=ACCENT)
    leader(ds, v, (-0.12, fl + 0.12), (-6.0, 14.0), "TUNNEL PLINTH (NOSE WHEEL)", weight=500)
    leader(ds, v, (0.72, fl + 0.30), (6.0, 11.0), "SIDE CONSOLE", weight=500)
    ov = I.OVERHEAD
    X, Y = v.pt(0.0, I.lining_crown(x, 0.0) - 0.5 * ov["depth"])
    ds.text(X, Y, "OVERHEAD PANEL", TXT, "label", "middle", fill=PAPER, weight=600, tag="lbl", vcenter=True)
    ax, ay, asz = ov["autoland"]
    za = I.lining_crown(ax, ay)
    hid = za > I.lining_crown(x, ay) - 0.002                           # above the cut's headliner line: hidden
    poly(ds, v, rrect(ay - 0.5 * asz, za - 0.004, ay + 0.5 * asz, za + 0.022, 0.008), W_THIN, fill=None,
         dash=(1.2, 0.7) if hid else None, color=MUTED if hid else INK)
    leader(ds, v, (ay, za + 0.01), (-5.0, -7.5), f"AUTOLAND CUP, STA {mm(ax)}", weight=500,
           lines=["(BEYOND" + (", HIDDEN)" if hid else ")")])
    leader(ds, v, (-0.73, 2.20), (-3.0, -12.0), "SIDE WINDOW", weight=500)
    X, Y = v.pt(0.0, 1.075)
    for i, s_ in enumerate((f"CREW ENTRY: HIPS BETWEEN THE HEADRESTS ({mm(ig['head_gap'])} vs 95TH {mm(ig['hip'])}), "
                            f"LEGS BETWEEN THE BACKS ({mm(ig['back_gap'])}),",
                            f"THEN OVER THE INBOARD CUSHION, ARMREST UP (IT STOWS ALONG THE BACK, TOP "
                            f"{mm(ig['arm_up_top'])} ABOVE THE FLOOR)")):
        ds.text(X, Y + 1.25 * TXT * i, s_, TXT, "label", "middle", fill=ACCENT, tag="lbl")


def _section_cabin(ds, v, x, ctx):
    fl = I.FLOOR["wl"]
    cc = ctx["cabin"]
    lg = I.LEDGES
    wx0, wx1 = I.FLOOR["wing_x"]
    if wx0 <= x <= wx1:
        line(ds, v, [(-0.70, fl - I.FLOOR["t_wing"]), (0.70, fl - I.FLOOR["t_wing"])], W_THIN, (1.6, 0.8), MUTED)
    # FR34 beyond: curtain rod + veneer header outline (thin)
    xp = I.BAGGAGE["partition_x"]
    Lp = lining_sec(round(xp, 4))
    zr = fl + I.BAGGAGE["bar_h"]
    for Q in clip_above(Lp, zr):
        line(ds, v, Q, W_THIN, None, "#9A8B74")
    hr = I.lining_half_width(xp, zr)
    line(ds, v, [(-hr, zr), (hr, zr)], W_THIN, None, "#9A8B74")
    zt = fl + lg["top_h"]
    for sg in (-1, 1):
        yo = I.lining_half_width(x, zt)
        yf = I.FLOOR["edge_bl"]
        P = np.array([(sg * lg["inner_bl"], zt), (sg * yo, zt), (sg * I.lining_half_width(x, fl + 0.01), fl),
                      (sg * yf, fl), (sg * (lg["inner_bl"] - 0.003), zt - lg["fascia"])])
        poly(ds, v, P, W_FINE, fill=LEDGE_FILL)
    zc = I.lining_crown(x, 0.0)
    hf = 0.5 * I.LINING["headliner_flat"]
    line(ds, v, [(-hf, zc - 0.012), (hf, zc - 0.012)], W_THIN, (1.2, 0.8), MUTED)
    for sg in (-1, 1):
        y = sg * I.LINING["psu_bl"]
        X, Y = v.pt(y, I.lining_crown(x, y))
        ds.cv.circle(X, Y + 0.5, 0.6, w=W_THIN, fill=PAPER)
    st = I.SEAT_TRACKS
    for yb in st["bl"]:
        for sg in (-1, 1):
            poly(ds, v, rrect(sg * yb - 0.5 * st["w"], fl, sg * yb + 0.5 * st["w"], fl + st["h"], 0.003), 0.0,
                 fill=INK)
    for sg in (-1, 1):
        for nm, P, f in front_seat_exec(sg * I.EXEC_SEAT["bl"], fl, raised=True):
            poly(ds, v, P, W_FINE, fill=f)
    p, p50 = cc["pose"], cc["pose50"]
    yc = -I.EXEC_SEAT["bl"]
    draw_manikin_front(ds, v, yc, p, cut_x=x)
    draw_manikin_front(ds, v, -yc, p50, fill=MAN50_FILL, cut_x=x)
    zmw = float(F.z_mw(x))
    hw = I.lining_half_width(x, zmw)
    Y = v.pt(0, 2.80)[1] - 2.0
    dim(ds, v.pt(-hw, zmw), v.pt(hw, zmw), Y, f"WIDTH {mm(2 * hw)} ({mm(I.CABIN['width'])})")
    zcr = I.lining_crown(x, 0.0)
    X = v.pt(0.04, 0)[0]
    dim(ds, v.pt(0.0, fl), v.pt(0.0, zcr), X, f"HEIGHT {mm(cc['height'])} ({mm(I.CABIN['height'])})", "v",
        text_at=(X - 2.6, v.pt(0, 1.62)[1]))
    Yf = v.pt(0, fl - 0.115)[1]
    dim(ds, v.pt(-I.FLOOR["edge_bl"], fl), v.pt(I.FLOOR["edge_bl"], fl), Yf,
        f"FLOOR {mm(cc['floor_width'])} ({mm(I.CABIN['floor_width'])})")
    za = fl + I.EXEC_SEAT["arm_top"] + 0.03
    ya = I.EXEC_SEAT["bl"] - 0.5 * I.EXEC_SEAT["width"]
    dim(ds, v.pt(-ya, za), v.pt(ya, za), v.pt(0, za)[1], f"AISLE {mm(cc['aisle_arm'])}",
        text_at=(v.pt(0.0, 0)[0] + 6.0, v.pt(0, za)[1] - 1.0))
    e = I.EXEC_SEAT
    hr_ = cc["head_rest"]
    hp_ = (-e["bl"] - 0.10, fl + e["head_top"] + e["head_slide"] - 0.03)
    Xh_, Yh_ = v.pt(*hp_)
    leader(ds, v, hp_, (403.0 - Xh_, 385.0 - Yh_), f"HEADREST RAISED {mm(e['head_slide'])}", weight=500,
           lines=[f"95TH HEAD CENTRE {mm(-hr_['p95m'][0])} ABOVE", "ITS TOP; 50TH (STBD) SUPPORTED"])
    zt_ = p["head_top"]
    zl = I.lining_crown(x, yc)
    Xh = v.pt(yc, 0)[0]
    dim(ds, v.pt(yc, zt_), v.pt(yc, zl), Xh + 5.5, mm(cc["headroom"]), "v", outside=True,
        text_at=(Xh + 8.0, v.pt(0, zl)[1] - 6.0))
    zsh = p["shoulder"][1] + 0.02
    ysh = yc - 0.5 * I.MANIKIN["bideltoid"]
    ylin = -I.lining_half_width(x, zsh)
    Y = v.pt(0, zsh)[1]
    dim(ds, v.pt(ysh, zsh), v.pt(ylin, zsh), Y, f"{cc['shoulder_room'] * 1000:+.0f}", "h", outside=True,
        text_at=(v.pt(ylin, 0)[0] - 1.0, Y - 2.2))
    X = v.pt(0.82, 0)[0]
    dim(ds, v.pt(0.66, fl), v.pt(0.66, fl + lg["top_h"]), X, mm(lg["top_h"]), "v")
    Yd = v.pt(0, 1.05)[1]
    dim(ds, v.pt(-I.EXEC_SEAT["bl"], 1.05), v.pt(I.EXEC_SEAT["bl"], 1.05), Yd, f"SEAT CL {mm(2 * I.EXEC_SEAT['bl'])}")
    eye_symbol(ds, *v.pt(yc, p["eye"][1]), 0.7)
    eye_symbol(ds, *v.pt(-yc, p50["eye"][1]), 0.6)
    wb, wt = cc["win"]
    leader(ds, v, (yc, p["eye"][1]), (-16.0, -9.0), f"95TH EYE WL {mm(p['eye'][1])}", weight=500,
           lines=[f"50TH {mm(cc['eye_wl_p50'])}; WINDOW {mm(wb)}-{mm(wt)}"])
    leader(ds, v, (0.74, 2.19), (-8.0, 5.0), "WINDOW S2 / P3", weight=500)
    X, Y = v.pt(0.0, fl - 0.052)
    ds.text(X, Y, f"CARRY-THROUGH TOP {mm(fl - I.FLOOR['t_wing'])} (HIDDEN), FLOOR <= {mm(I.FLOOR['t_wing'])} THICK",
            TXT, "label", "middle", fill=MUTED, tag="lbl", vcenter=True)
    leader(ds, v, (0.37, I.lining_crown(x, 0.37) - 0.01), (5.0, 9.0), "PSU / HEADLINER", weight=500)
    X, Y = v.pt(-yc, 1.30)
    ds.text(X, Y, "50TH PCT", TXT, "label", "middle", fill=MAN_LINE, weight=600, tag="lbl")
    X, Y = v.pt(yc, 1.30)
    ds.text(X, Y, "95TH PCT", TXT, "label", "middle", fill=MAN_LINE, weight=600, tag="lbl")


# ---------------------------------------------------------------------------------------------------- detail C
def draw_detail(ds, v, ctx):
    cv = ds.cv
    x0, z0, x1, z1 = DET_BOX
    fl = I.FLOOR["fd_wl"]
    c = I.CREW_SEAT
    bl = c["bl"]
    cc = ctx["crew"]
    o95 = cc["occ"]["p95m"]
    p = o95["pose"]
    for n, x in [("FW", 3.0)] + frames_list(3.0, 4.66):
        line(ds, v, [(x, z0), (x, z1)], W_GRID, None if n != "FW" else (5.0, 1.0, 0.8, 1.0), GRID)
        X, Y = v.pt(x, z0)
        ds.text(X, Y + 3.0, n, TXT, "label", "middle", weight=600, fill=GRID, tag="grid")
        ds.text(X, Y + 5.8, mm(x), TXT, "mono", "middle", fill=GRID, tag="grid")
    for z in (1.4, 1.6, 1.8, 2.0, 2.2, 2.4, 2.6):
        p_, q = v.pt(x0, z), v.pt(x1, z)
        cv.line(p_, q, W_GRID, (1.0, 1.4), color=GRID)
        ds.text(q[0] + 1.0, q[1], f"WL {mm(z)}", TXT, "mono", "start", vcenter=True, fill=GRID, tag="grid")
    xs = np.linspace(x0, x1, 300)
    zb = F.z_at(xs, np.full_like(xs, bl))
    G = glz()
    for k in ("ws", "sw"):
        for Q in M.clip_polyline(G[k], DET_BOX):
            poly(ds, v, Q, W_THIN, fill=GLASS_FILL, color=FAR)
    line(ds, v, np.c_[xs, F.z_top(xs)], W_THIN, (2.0, 1.0), MUTED)
    line(ds, v, np.c_[xs, zb], CUT)
    xl = np.linspace(3.55, x1, 40)
    line(ds, v, np.c_[xl, headliner_at(xl, bl)], W_FINE)
    poly(ds, v, [(I.FLOOR["fd_x0"], fl), (x1, fl), (x1, fl - I.FLOOR["t"]), (I.FLOOR["fd_x0"], fl - I.FLOOR["t"])],
         0.0, fill=FLOOR_FILL)
    line(ds, v, [(I.FLOOR["fd_x0"], fl), (x1, fl)], CUT)
    d1 = I.DIVIDER["x_aft"]
    d0 = d1 - I.DIVIDER["t"]
    zc = I.lining_crown(d1, bl)
    poly(ds, v, [(d0, fl), (min(d1, x1), fl), (min(d1, x1), zc), (d0, zc)], W_FINE, fill=VENEER)
    ov = I.OVERHEAD
    zo = [I.lining_crown(x, 0.0) for x in ov["x"]]
    line(ds, v, [(ov["x"][0], zo[0] - ov["depth"]), (ov["x"][1], zo[1] - ov["depth"])], W_OBJ + 0.3, None, "#5E676C")
    # CB panel on the removed port sidewall (phantom)
    cb = I.SIDE_CONSOLE["cb_panel"]
    poly(ds, v, [(cb[0], fl + cb[2]), (cb[1], fl + cb[2]), (cb[1], fl + cb[3]), (cb[0], fl + cb[3])], W_THIN,
         fill=None, dash=PHANTOM, color=MUTED)
    draw_fd_side(ds, v, bl, crank=p["crank"], travel=True)
    pd0 = I.pedal_points(0.0)
    line(ds, v, [pd0["heel"] + 0.03 * pd0["dir"], pd0["toe"]], W_THIN, PHANTOM, MUTED)
    # full rudder at the 95th setting: pedals PEDALS travel fore / aft, the toe brake (phantom)
    T = I.PEDALS["travel"]
    for t_ in (-T, T):
        q = I.pedal_points(p["crank"] + t_)
        line(ds, v, [q["heel"] + 0.03 * q["dir"], q["toe"]], W_THIN, PHANTOM, ACCENT)
    q = I.pedal_points(p["crank"])
    tb = math.radians(I.PEDALS["toe_brake"])
    a_ = math.atan2(q["dir"][1], -q["dir"][0]) - tb                  # face angle from horizontal, tipped forward
    d_ = np.array([-math.cos(a_), math.sin(a_)])
    line(ds, v, [q["heel"] + 0.03 * d_, q["heel"] + (np.linalg.norm(q["toe"] - q["heel"])) * d_], W_THIN, (0.8, 0.8),
         MUTED)
    # seat: forward notch and neutral (phantom); the aft notch with the headrest at its top lock (accent phantom)
    for dx, dz in ((-c["travel_x"], 0.0), (0.0, 0.0)):
        pcs, _, _ = crew_seat_side(I.crew_srp(-1, dx, dz)[[0, 2]], fl)
        draw_pieces(ds, v, pcs, W_THIN, dash=PHANTOM, color=MUTED, only=("cushion", "back", "head"), fill=False)
    pcs, _, _ = crew_seat_side(I.crew_srp(-1, c["travel_x"], 0.0)[[0, 2]], fl, head_c=c["head_lock"][1])
    draw_pieces(ds, v, pcs, W_THIN, dash=PHANTOM, color=ACCENT, only=("back", "head"), fill=False)
    # the 95th setting (solid), manikin, headrest at his lock position
    srp = I.crew_srp(-1, p["seat_dx"], p["seat_dz"])
    pcs, stalks, piv = crew_seat_side(srp[[0, 2]], fl, head_c=p["head_lock"])
    draw_pieces(ds, v, pcs)
    for P in stalks:
        line(ds, v, P, W_FINE)
    ds.cv.circle(*v.pt(*piv), 0.5, w=W_THIN, fill=PAPER)
    draw_manikin_side(ds, v, p)
    # full rudder: the 95th's up-leg on the pedal that came aft (phantom)
    pa = o95["rud"]["p_aft"]
    sa = pa["scale"]
    poly(ds, v, capsule(pa["H"], pa["knee"], pa["thigh_r"], 0.062 * sa), W_THIN, fill=None, dash=PHANTOM, color=ACCENT)
    poly(ds, v, capsule(pa["knee"], pa["ankle"], 0.058 * sa, 0.040 * sa), W_THIN, fill=None, dash=PHANTOM,
         color=ACCENT)
    # the 5th-pct female at her setting: knee circle and seat SRP (phantom)
    p5 = cc["occ"]["p5f"]["pose"]
    poly(ds, v, ellipse(p5["knee"], 0.062 * p5["scale"], 0.062 * p5["scale"], 32), W_THIN, fill=None, dash=PHANTOM,
         color=ACCENT)
    s0 = I.crew_srp(-1)
    srp_symbol(ds, *v.pt(s0[0], s0[2]), 1.1)
    srp_symbol(ds, *v.pt(srp[0], srp[2]), 0.7)
    # sight lines from the design eye: over the nose, level, to the pilot's PFD centre
    e = I.design_eye(-1)
    vis = cc["vision"]
    a = math.radians(vis["over_nose_down"])
    xa = x0 + 0.02
    line(ds, v, [(e[0], e[2]), (xa, e[2] - (e[0] - xa) * math.tan(a))], W_THIN, (3.0, 1.0), ACCENT)
    line(ds, v, [(e[0], e[2]), (xa, e[2])], W_THIN, (0.8, 0.8), ACCENT)
    pfd = I.pdu_centre(-1)
    line(ds, v, [(e[0], e[2]), (pfd[0], pfd[2])], W_THIN, (3.0, 1.0), ACCENT)
    ds.cv.circle(*v.pt(pfd[0], pfd[2]), 0.5, w=0.0, fill=ACCENT, stroke=False)
    # the eyes of the four occupants at their settings (circles) and the design eye
    for k, o in cc["occ"].items():
        Xq, Yq = v.pt(*o["pose"]["eye"])
        ds.cv.circle(Xq, Yq, 0.55, w=W_THIN, fill=PAPER)
    eye_symbol(ds, *v.pt(e[0], e[2]), 1.2)
    _detail_dims(ds, v, ctx, e, s0, p)


def _detail_dims(ds, v, ctx, e, s0, p):
    cc = ctx["crew"]
    fl = I.FLOOR["fd_wl"]
    vis = cc["vision"]
    c = I.CREW_SEAT
    f_, u_ = cc["eye_off"]
    X = v.pt(4.53, 0)[0]
    dim(ds, v.pt(s0[0], fl), v.pt(s0[0], s0[2]), X, mm(c["srp_h"]), "v")
    dim(ds, v.pt(s0[0], s0[2]), v.pt(e[0], e[2]), X, mm(u_), "v")
    Y = v.pt(0, 2.765)[1]
    dim(ds, v.pt(e[0], e[2]), v.pt(s0[0], s0[2]), Y, mm(f_), "h", outside=True,
        text_at=(v.pt(e[0], 0)[0] - 6.5, Y - 0.3))
    Yt = v.pt(0, 1.20)[1]
    tx = c["travel_x"]
    dim(ds, v.pt(s0[0] - tx, fl - 0.03), v.pt(s0[0] + tx, fl - 0.03), Yt,
        f"TRAVEL ±{mm(tx)} (9 HOLES x {mm(c['notch'])}), ±{mm(c['travel_z'])} UP / DOWN",
        size=TXT, text_at=(v.pt(s0[0] - tx, 0)[0] - 30.0, Yt + 0.3))
    o95 = cc["occ"]["p95m"]
    kn = p["knee"]
    leader_to(ds, v, (kn[0] - 0.05, kn[1] - 0.03), (3.37, 1.66),
              f"95TH KNEE: PANEL {mm(o95['clear_panel'])}, YOKE ±{mm(I.YOKE['travel'][1])} PITCH "
              f"{sgn_mm(o95['yoke_pitch'])}", "end", color=ACCENT, weight=600,
              lines=[f"FULL RUDDER (PHANTOM LEG, PEDAL {mm(I.PEDALS['travel'])} AFT): {sgn_mm(o95['rud_pitch'])}",
                     f"ROLL: CONTACT FROM {o95['roll_contact']:.0f}° (DETAIL F)", "DASHED CIRCLE: 5TH FEMALE KNEE"])
    pd = I.pedal_points(p["crank"])
    leader_to(ds, v, tuple(pd["ball"]), (3.37, 1.555),
              f"H-PT TO BALL {mm(o95['hip_to_ball'])}, KNEE {o95['knee_angle']:.0f}°", "end", color=ACCENT,
              weight=600, lines=[f"PEDALS {mm(-p['crank'])} FWD"])
    leader_to(ds, v, (e[0], e[2]), (3.62, 2.755), f"DESIGN EYE {mm(e[0])} / {mm(abs(e[1]))} / {mm(e[2])}", "end",
              size=2.2, color=ACCENT, weight=700,
              lines=["= 50TH EYE, NEUTRAL SEAT; O = EYES OF 5F / 5M / 50 / 95",
                     f"L2 EYE {mm(CG.EYE[0])} / {mm(abs(CG.EYE[1]))} / {mm(CG.EYE[2])} (TO BE REPLACED)"])
    leader_to(ds, v, (s0[0], s0[2]), (4.30, 1.19), f"SRP {mm(s0[0])} / WL {mm(s0[2])} (NEUTRAL)", "start",
              weight=700, lines=[f"SOLID SEAT: 95TH {p['seat_dx'] * 1000:+.0f} / {p['seat_dz'] * 1000:+.0f}"])
    pfd = I.pdu_centre(-1)
    t = 0.62
    mid = (1 - t) * e[[0, 2]] + t * pfd[[0, 2]]
    X, Y = v.pt(*mid)
    ang = math.degrees(math.atan2(e[2] - pfd[2], e[0] - pfd[0]))
    ds.text(X - 1.2, Y - 1.4, f"EYE-PFD {mm(cc['eye_to_pfd'])}, {cc['pfd_down_deg']:.0f}° DOWN", TXT, "mono",
            "middle", fill=ACCENT, rot=-ang, tag="eye")
    xa = DET_BOX[0] + 0.04
    a = math.radians(vis["over_nose_down"])
    X, Y = v.pt(xa, e[2] - (e[0] - xa) * math.tan(a))
    ds.text(X, Y - 1.1, f"OVER NOSE {vis['over_nose_down']:.1f}°", TXT, "label", "start", fill=ACCENT,
            rot=-math.degrees(a), tag="eye")
    hx = p["head_c"][0]
    zl = I.lining_crown(hx, e[1])
    Xh = v.pt(hx, 0)[0]
    dim(ds, v.pt(hx, p["head_top"]), v.pt(hx, zl), Xh + 4.0, mm(cc["headroom"]), "v", outside=True,
        text_at=(Xh + 6.3, v.pt(0, zl)[1] - 4.5))
    X, Y = v.pt(I.DIVIDER["x_aft"] - 0.5 * I.DIVIDER["t"], 2.55)
    da = cc["div_aft"]
    ds.text(X, Y, f"DIVIDER {mm(I.DIVIDER['x_aft'])}: AFT NOTCH HEADREST TOP {da[c['head_lock'][1]] * 1000:+.0f} "
            f"(PHANTOM), 95TH {o95['head_div'] * 1000:+.0f}", TXT, "label", "start", rot=90, fill=ACCENT, tag="lbl",
            vcenter=True)
    hub = I.yoke_hub(-1)
    leader_to(ds, v, (hub[0] + 0.05, hub[2] + 0.03), (3.97, 2.095), "YOKE HUB (PC-24 STYLE)", "start",
              lines=[f"{mm(hub[0])} / WL {mm(hub[2])}, BL {mm(I.YOKE['bl'])}",
                     f"PITCH ±{mm(I.YOKE['travel'][1])} (PHANTOM)"])
    xl, zl_ = I.glareshield_lip(e[1])
    leader_to(ds, v, (xl, zl_), (3.02, 2.615), f"GLARESHIELD LIP {mm(zl_)}", "start",
              lines=["HOOD CLOSED ONTO THE WS FRAME"])
    leader_to(ds, v, (float(I.panel_x(I.PANEL["mfd_z"] - 0.06)), I.PANEL["mfd_z"] - 0.06), (3.08, 1.86),
              f"PDU PLANE {mm(I.PANEL['glass_x'])}, TILT {I.PANEL['tilt_deg']:.0f}°", "start",
              lines=[f"MFD WL {mm(I.PANEL['mfd_z'])}"])
    xw, zw = I.ws_lower_edge(e[1])
    leader_to(ds, v, (xw, zw), (3.02, 2.47), f"WS LOWER EDGE {mm(xw)} / {mm(zw)}", "start")
    cb = I.SIDE_CONSOLE["cb_panel"]
    leader_to(ds, v, (cb[0] + 0.01, fl + cb[3] - 0.03), (3.28, 1.785), "CB PANEL, PORT", "end", color=MUTED,
              lines=["WALL (PHANTOM)"])
    px0, px1, phw, pz = I.pedestal_plinth()
    leader_to(ds, v, (px0 + 0.04, fl + 0.04), (3.06, 1.163), "PEDESTAL (BL 0) ON THE NOSE-WHEEL TUNNEL PLINTH",
              "start", weight=400)


# ---------------------------------------------------------------------------------------------------- detail E / D / F
def _ordinates(ds, v, x_text, items, x_feat, size=TXT):
    """Height ordinates in a side view: a thin dashed line from each feature (x_feat[i], z) forward to x_text and the
    label above it.  items: [(label, z)]."""
    for (lab, z), xf in zip(items, x_feat):
        P, Q = v.pt(xf, z), v.pt(x_text, z)
        ds.cv.line(P, Q, W_THIN, (1.0, 0.7), color=MUTED)
        ds.text(Q[0] + 0.3, Q[1] - 0.7, lab, size, "mono", "start", fill=INK, tag="ord")


def draw_seat_details(ds, v1, v2, ctx):
    fl = I.FLOOR["wl"]
    c = I.CREW_SEAT
    s0 = I.crew_srp(-1)
    for vv, box in ((v1, E1_BOX), (v2, E2_BOX)):
        x0, z0, x1, z1 = box
        line(ds, vv, [(x0, fl), (x1, fl)], CUT)
        poly(ds, vv, [(x0, fl), (x1, fl), (x1, fl - 0.025), (x0, fl - 0.025)], 0.0, fill=FLOOR_FILL)
    # E1: crew seat, neutral; the armrest flipped up (dashed alternate)
    pcs_up, _, _ = crew_seat_side(s0[[0, 2]], fl, arm_up=True)
    pcs, stalks, piv = crew_seat_side(s0[[0, 2]], fl)
    draw_pieces(ds, v1, pcs)
    for P in stalks:
        line(ds, v1, P, W_FINE)
    draw_pieces(ds, v1, pcs_up, W_THIN, dash=PHANTOM, color=ACCENT, only=("arm",), fill=False)
    ds.cv.circle(*v1.pt(*piv), 0.5, w=W_THIN, fill=PAPER)
    srp_symbol(ds, *v1.pt(s0[0], s0[2]), 0.9)
    prof, _ = I.crew_seat_profile()
    top_h = s0[2] + float(prof["head"][:, 1].max())
    top_b = s0[2] + float(prof["back"][:, 1].max())
    arm = s0[2] + c["arm_h"]
    rear = s0[0] + I.back_rear_offset()
    front = s0[0] - c["pan_depth"]
    _ordinates(ds, v1, E1_BOX[0] + 0.01,
               [(f"HEADREST {mm(top_h - fl)} [E]", top_h), (f"BACK {mm(top_b - fl)} [E]", top_b),
                (f"ARMREST {mm(arm - fl)}", arm), (f"SRP {mm(c['srp_h'])}", s0[2])],
               [rear - 0.10, rear - 0.12, s0[0] - 0.05, s0[0]])
    Y = v1.pt(0, fl - 0.07)[1]
    dim(ds, v1.pt(front, fl), v1.pt(s0[0], fl), Y, mm(c["pan_depth"]))
    dim(ds, v1.pt(s0[0], fl), v1.pt(rear, fl), Y, mm(rear - s0[0]), outside=True,
        text_at=(v1.pt(rear, 0)[0] + 4.5, Y - 0.7))
    X, Y = v1.pt(s0[0] + 0.10, s0[2] + 0.55)
    ds.text(X + 1.0, Y, f"{c['back_deg']:.0f}°", TXT, "mono", "start", fill=INK, tag="lbl")
    leader_to(ds, v1, tuple(piv), (4.33, 1.465), "ARMREST HINGE (IN THE BACK)", "start", color=MUTED,
              lines=["UP: ALONG THE BACK, PHANTOM"])
    fb = local(s0[[0, 2]], -1.0, prof["fleece_back"])
    leader_to(ds, v1, tuple(fb[len(fb) // 4 + 2]), (4.05, 2.335), f"SHEEPSKIN {mm(c['sheepskin_t'])} [M]", "end",
              color=MUTED, lines=["INSIDE THE CUSHION / BACK", "OUTLINE (LEATHER BEHIND)"])
    X, Y = v1.pt(E1_BOX[0], E1_BOX[1])
    ds.text(X, Y + 7.4, f"CREW (IPECO 3A318 TYPE), WIDTH {mm(c['width'])}, CUSHION {mm(c['cushion_w'])} "
            f"(INBOARD {mm(c['cushion_in'])} + {mm(0.5 * c['cushion_w'])})", TXT, "label", "start", fill=MUTED,
            tag="lbl")
    # E2: executive seat PAX 3 (forward-facing), headrest lowest (solid) and raised (phantom)
    e = I.EXEC_SEAT
    r = [q for q in ctx["seats"] if q["id"] == "PAX 3"][0]
    pcs, posts = exec_seat_side(r, fl)
    draw_pieces(ds, v2, pcs)
    for P in posts:
        line(ds, v2, P, W_FINE)
    pcs_r, _ = exec_seat_side(r, fl, raised=True)
    draw_pieces(ds, v2, pcs_r, W_THIN, dash=PHANTOM, color=MUTED, only=("head",), fill=False)
    draw_pieces(ds, v2, pcs, W_THIN, dash=(1.2, 0.7), color=INK, only=("arm", "ctrl"), fill=False)
    a1 = r["srp"][0] - e["arm_u"][1]
    leader_to(ds, v2, (a1 + 0.035, fl + e["arm_top"] - 0.07), (7.26, 1.45), "INBOARD ARM ONLY", "start",
              color=MUTED, lines=["(FAR SIDE, HIDDEN):", f"PANEL {mm(e['arm_h0'])}-{mm(e['arm_top'])},",
                                  "CONTROL AT ITS FWD END"])
    srp_symbol(ds, *v2.pt(r["srp"][0], r["srp"][2]), 0.9)
    xr = r["rear"]
    _ordinates(ds, v2, E2_BOX[0] + 0.01,
               [(f"HEADREST {mm(e['head_top'])} (+{mm(e['head_slide'])})", fl + e["head_top"]),
                (f"BACK {mm(e['back_top'])}", fl + e["back_top"]),
                (f"ARM {mm(e['arm_top'])} / CUSHION {mm(e['cushion_top'])}", fl + e["arm_top"]),
                (f"SRP {mm(e['srp_h'])}", r["srp"][2])],
               [xr - 0.03, xr - 0.02, r["front"] + 0.05, r["srp"][0]])
    Y = v2.pt(0, fl - 0.07)[1]
    dim(ds, v2.pt(r["front"], fl), v2.pt(r["srp"][0], fl), Y, mm(e["srp_front"]))
    dim(ds, v2.pt(r["front"], fl), v2.pt(r["rear"], fl), Y + 4.4, mm(e["length"]))
    X, Y = v2.pt(r["srp"][0] + 0.10, r["srp"][2] + 0.45)
    ds.text(X + 1.0, Y, f"{e['back_deg']:.0f}° TTL", TXT, "mono", "start", fill=INK, tag="lbl")
    X, Y = v2.pt(E2_BOX[0], E2_BOX[1])
    ds.text(X, Y + 11.2, f"EXECUTIVE (PAX 3), WIDTH {mm(e['width'])}, CUSHION {mm(e['cushion_w'])}", TXT, "label",
            "start", fill=MUTED, tag="lbl")
    xm = 0.5 * (v1.pt(E1_BOX[0], 0)[0] + v2.pt(E2_BOX[2], 0)[0])
    view_title(ds, xm, v1.pt(0, E1_BOX[1])[1] + 17.0, "DETAIL E - SEATS",
               "CREW (NEUTRAL) / EXECUTIVE (UPRIGHT), SEEN FROM PORT - HEIGHTS ABOVE THE FLOOR - SCALE 1:10")


def yoke_front(yc, zc, roll=0.0):
    """Yoke pieces in a front view (y, z) about the hub centre (yc, zc) at roll deg (interior.yoke_outline_yz)."""
    return [P + np.array([yc, zc]) for P in I.yoke_outline_yz(roll)]


def draw_panel_view(ds, v, ctx):
    """VIEW D: instrument panel, glareshield, centre stack, pedestal, yokes and pedals, looking forward."""
    y0, z0, y1, z1 = D_BOX
    fl = I.FLOOR["fd_wl"]
    pn = I.PANEL
    zm = pn["mfd_z"]
    xg = pn["glass_x"]
    O = oml_section(round(xg, 4))
    for Q in M.clip_polyline(O, D_BOX):
        line(ds, v, Q, CUT)
    try:
        E = CG.edges(-1, which=("ws",), dx=0.004)["ws"]
        E2 = CG.edges(1, which=("ws",), dx=0.004)["ws"]
        for L in (max(E, key=len), max(E2, key=len)):
            for Q in M.clip_polyline(L[:, [1, 2]], D_BOX):
                poly(ds, v, Q, W_THIN, fill=GLASS_FILL, color=FAR)
    except Exception as ex:                    # noqa: BLE001
        ds.log.append(f"view D windshield skipped: {ex}")
    ys = np.linspace(-pn["cheek_bl"], pn["cheek_bl"], 61)
    lip = np.array([I.glareshield_lip(y)[1] for y in ys])
    wse = np.array([I.ws_lower_edge(min(abs(y), 0.62))[1] - I.GLARESHIELD["frame_drop"] for y in ys])
    poly(ds, v, np.vstack([np.c_[ys, lip], np.c_[ys[::-1], np.maximum(wse, lip + 0.005)[::-1]]]), W_THIN,
         fill="#9AA3A8")
    zlo = zm + pn["lower_dz"]
    zs = zm + pn["sdu_top_dz"] - I.sdu_height() - 0.03                # centre stack bottom in this view
    face = np.vstack([np.c_[ys, lip], [[pn["cheek_bl"], zlo], [pn["stack_hw"], zlo], [pn["stack_hw"], zs],
                                       [-pn["stack_hw"], zs], [-pn["stack_hw"], zlo], [-pn["cheek_bl"], zlo]]])
    poly(ds, v, face, W_FINE, fill=SHELL_FILL)
    line(ds, v, np.c_[ys, lip], W_OBJ)
    w, h = pn["pdu_wh"]
    for yc in pn["pdu_bl"]:
        ww = w * (math.cos(math.radians(pn["pdu_cant"])) if yc else 1.0)
        poly(ds, v, rrect(yc - 0.5 * ww, zm - 0.5 * h, yc + 0.5 * ww, zm + 0.5 * h, 0.01), W_FINE, fill="#26323A")
        poly(ds, v, rrect(yc - 0.5 * ww + 0.014, zm - 0.5 * h + 0.022, yc + 0.5 * ww - 0.014, zm + 0.5 * h - 0.018,
                          0.004), 0.0, fill="#3E5566")
    aw, ah = I.GLARESHIELD["afcs_wh"]
    poly(ds, v, rrect(-0.5 * aw, zm + 0.18 - 0.5 * ah, 0.5 * aw, zm + 0.18 + 0.5 * ah, 0.006), W_THIN, fill="#26323A")
    sb = pn["standby"]
    ds.cv.circle(*v.pt(sb[0], zm + sb[1]), 0.5 * sb[2] * v.k, w=W_THIN, fill="#26323A")
    for sg in (-1, 1):
        ds.cv.circle(*v.pt(sg * pn["ecs_bl"], zm - 0.063), 0.024 * v.k, w=W_THIN, fill=BASE_FILL)
    sw = pn["sdu_wh"][0]
    sh = I.sdu_height()                                                # reclined: projected height h cos(recline)
    zt = zm + pn["sdu_top_dz"]
    for sg in (-1, 1):
        yc = sg * pn["sdu_bl"]
        poly(ds, v, rrect(yc - 0.5 * sw, zt - sh, yc + 0.5 * sw, zt, 0.008), W_THIN, fill="#26323A")
        poly(ds, v, rrect(yc - 0.5 * sw + 0.008, zt - sh + 0.014, yc + 0.5 * sw - 0.008, zt - 0.010, 0.003), 0.0,
             fill="#3E5566")
    pe = I.PEDESTAL
    px0, px1, phw, pz = I.pedestal_plinth()
    poly(ds, v, [(-phw, fl), (phw, fl), (phw, pz), (-phw, pz)], W_THIN, fill="#CDD1D3")
    poly(ds, v, [(-pe["hw"], pz), (pe["hw"], pz), (pe["hw"], zs), (-pe["hw"], zs)], W_THIN, fill="#D9DCDE")
    hwf = I.lining_half_width(xg, fl + 0.005)
    line(ds, v, [(-hwf, fl), (hwf, fl)], CUT)
    pw = I.PEDALS["pad_wh"][0]
    ph = I.PEDALS["pad_wh"][1] * math.sin(math.radians(I.PEDALS["face_deg"]))
    for sg in (-1, 1):
        for d in (-1, 1):
            yc = sg * I.CREW_SEAT["bl"] + d * I.PEDALS["dy"]
            poly(ds, v, [(yc - 0.5 * pw, fl + 0.03), (yc + 0.5 * pw, fl + 0.03), (yc + 0.5 * pw, fl + 0.03 + ph),
                         (yc - 0.5 * pw, fl + 0.03 + ph)], W_THIN, fill="#AAB2B7")
    for sg in (-1, 1):
        hub = I.yoke_hub(sg)
        P = yoke_front(hub[1], hub[2])
        poly(ds, v, P[1], W_THIN, fill="#2B3338")                      # black yoke body
        poly(ds, v, P[0], W_FINE, fill="#F4F4F2")                      # white shield on it
        for Q in P[2:]:
            poly(ds, v, Q, W_THIN, fill="#2B3338")                     # grips, swollen heads
    zc = I.yoke_hub(-1)[2]
    dim(ds, v.pt(-pn["pdu_bl"][2], zm), v.pt(0.0, zm), v.pt(0, zm + 0.125)[1], mm(pn["pdu_bl"][2]), ext=False)
    dim(ds, v.pt(0.0, zm), v.pt(pn["pdu_bl"][2], zm), v.pt(0, zm + 0.125)[1], mm(pn["pdu_bl"][2]), ext=False)
    Yd = v.pt(0, 1.30)[1]
    dim(ds, v.pt(-I.YOKE["bl"], zc), v.pt(I.YOKE["bl"], zc), Yd, f"YOKES / SEATS {mm(2 * I.YOKE['bl'])}")
    xr = v.pt(y1, 0)[0] + 1.0
    for lab, z in ((f"LIP {mm(I.glareshield_lip(0.0)[1])}", I.glareshield_lip(0.0)[1]),
                   (f"MFD {mm(zm)}", zm), (f"HUB {mm(zc)}", zc),
                   (f"LOWER {mm(zlo)}", zlo), (f"FLOOR {mm(fl)}", fl)):
        X, Y = v.pt(0.72, z)
        ds.cv.line((X, Y), (xr, Y), W_THIN, (0.8, 0.6), color=MUTED)
        ds.text(xr + 0.5, Y, lab, TXT, "mono", "start", vcenter=True, fill=INK, tag="ord")
    leader(ds, v, (sb[0], zm + sb[1]), (-7.0, 9.0), "GI 275", weight=500)
    leader(ds, v, (0.0, zm + 0.18), (9.0, -6.0), "GFC 700", weight=500)
    leader(ds, v, (pn["sdu_bl"], zt - 0.10), (12.0, 4.0), "2 x 7-IN SDU", weight=500)
    ds.text(*v.pt(0.0, zm - 0.02), "MFD", 2.2, "label", "middle", fill=PAPER, weight=600, tag="lbl")
    for sg, nm in ((-1, "PFD P"), (1, "PFD S")):
        ds.text(*v.pt(sg * pn["pdu_bl"][2], zm - 0.02), nm, 2.2, "label", "middle", fill=PAPER, weight=600, tag="lbl")
    view_title(ds, v.pt(0.0, 0)[0], v.pt(0, z0)[1] + 8.5, "VIEW D - PANEL",
               f"LOOKING FORWARD (STBD RIGHT) AT STA {mm(xg)} - SCALE 1:10")


def draw_yoke_sweep(ds, v, ctx):
    """DETAIL F: the left yoke swept over its roll travel (phantom outlines) against the knees of the four occupants
    at their seat settings (circles: the knee spheres, which sit inside the pitch-travel slab), looking forward."""
    y0, z0, y1, z1 = F_BOX
    cc = ctx["crew"]
    pn = I.PANEL
    hub = I.yoke_hub(-1)
    yc, zc = hub[1], hub[2]
    for z in (1.6, 1.7, 1.8, 1.9, 2.0):
        p, q = v.pt(y0, z), v.pt(y1, z)
        ds.cv.line(p, q, W_GRID, (1.0, 1.4), color=GRID)
        ds.text(q[0] + 1.0, q[1], f"WL {mm(z)}", TXT, "mono", "start", vcenter=True, fill=GRID, tag="grid")
    for y in (-0.5, -0.375, -0.25):
        p, q = v.pt(y, z0), v.pt(y, z1)
        ds.cv.line(p, q, W_GRID, (1.0, 1.4) if y != -0.375 else CHAIN, color=GRID)
        ds.text(q[0], q[1] - 1.2, f"BL {mm(abs(y))} P", TXT, "mono", "middle", fill=GRID, tag="grid")
    # lower panel edge and the column
    zlo = pn["mfd_z"] + pn["lower_dz"]
    line(ds, v, [(y0 + 0.01, zlo), (-pn["stack_hw"], zlo)], W_FINE, (1.6, 0.8), MUTED)
    # roll sweep (phantom) and the yoke at neutral (solid)
    R = float(I.YOKE["roll"])
    for r in (-R, R):
        for Q in yoke_front(yc, zc, r):
            poly(ds, v, Q, W_THIN, fill=None, dash=PHANTOM, color=MUTED)
    P = yoke_front(yc, zc)
    poly(ds, v, P[1], W_THIN, fill="#2B3338")
    poly(ds, v, P[0], W_FINE, fill="#F4F4F2")
    for Q in P[2:]:
        poly(ds, v, Q, W_THIN, fill="#2B3338")
    ds.cv.circle(*v.pt(yc, zc), I.YOKE["column_r"] * v.k, w=W_THIN, fill=SHELL_FILL)
    # knees (sphere sections) of the four occupants
    cols = dict(p95m=MAN_LINE, p50m="#6D8AA3", p5m="#8FA6B8", p5f=ACCENT)
    for k, o in cc["occ"].items():
        p = o["pose"]
        s = p["scale"]
        for sg in (-1, 1):
            yk = yc + sg * I.knee_half(p)
            poly(ds, v, ellipse((yk, p["knee"][1]), 0.062 * s, 0.062 * s, 40), W_THIN if k != "p95m" else W_FINE,
                 fill=MAN_FILL if k == "p95m" else None, color=cols[k], dash=None if k in ("p95m", "p5f") else (1.2, 0.6))
        # full rudder: the up-knee (pedal PEDALS travel aft) on the worse leg, phantom
        rd = o["rud"]
        pa = rd["p_aft"]
        yk = yc + rd["up"] * I.knee_half(pa)
        poly(ds, v, ellipse((yk, pa["knee"][1]), 0.062 * s, 0.062 * s, 40), W_THIN, fill=None, color=cols[k],
             dash=PHANTOM)
        dzt = dict(p95m=0.035, p50m=0.0, p5m=-0.035, p5f=-0.03)[k]
        X, Y = v.pt(yc + I.knee_half(cc["occ"]["p95m"]["pose"]) + 0.062 + 0.012, p["knee"][1] + dzt)
        ds.text(X, Y, PCT_TAG[k], TXT, "label", "start", vcenter=True, fill=cols[k], weight=600, tag="lbl")
    o95, o50 = cc["occ"]["p95m"], cc["occ"]["p50m"]
    X, Y = v.pt(yc, z0)
    L = [(f"ROLL ±{R:.0f}° [E] PHANTOM; SOLID CIRCLES: KNEES AT EACH SETTING, NEUTRAL PEDALS;", MUTED, 400),
         (f"PHANTOM CIRCLES: THE UP-KNEE AT FULL RUDDER (PEDAL {mm(I.PEDALS['travel'])} AFT)", MUTED, 400),
         (f"95TH: NEUTRAL PEDALS {sgn_mm(o95['yoke_pitch'])} WINGS LEVEL, CONTACT FROM {o95['roll_contact']:.0f}° "
          f"ROLL; FULL RUDDER {sgn_mm(o95['rud_pitch'])}", ACCENT, 600),
         (f"50TH: {sgn_mm(o50['yoke_pitch'])}, CONTACT FROM {o50['roll_contact']:.0f}°; FULL RUDDER "
          f"{sgn_mm(o50['rud_pitch'])}, CONTACT FROM {max(o50['rud_roll_contact'], 0):.0f}° (OPEN POINT, L6B)",
          ACCENT, 600)]
    for i, (t, col, wt) in enumerate(L):
        ds.text(X, Y + 3.8 + 2.7 * i, t, TXT, "label", "middle", fill=col, tag="lbl", weight=wt)
    Y += 2.7 * (len(L) - 2)
    view_title(ds, X, Y + 13.5, "DETAIL F - YOKE SWEEP vs KNEES",
               f"LEFT SEAT, LOOKING FORWARD AT THE KNEES (STA {mm(o95['pose']['knee'][0])}) - SCALE 1:5")


# ---------------------------------------------------------------------------------------------------- detail G
def draw_table_detail(ds, v, ctx):
    """DETAIL G: the club table deployed between PAX 1 (aft-facing) and PAX 3, at the port seat BL, seen from port:
    the 95th at PAX 1 upright (knees ringed where they run into the top) and the 50th at PAX 3 with the feet forward
    (table_posture), the facing seat bases, ledge, heights."""
    x0, z0, x1, z1 = box = G_BOX
    fl = I.FLOOR["wl"]
    cc = ctx["cabin"]
    tp = cc["table"]
    t = I.TABLES["club_p"]
    lg = I.LEDGES
    by = {r["id"]: r for r in ctx["seats"]}

    def cpoly(P, w=W_FINE, fill=None, dash=None, color=None):
        Q = clip_poly(P, box)
        if Q is not None:
            poly(ds, v, Q, w, fill=fill, dash=dash, color=color)
    for z in (1.4, 1.6, 1.8, 2.0):
        p_, q_ = v.pt(x0, z), v.pt(x1, z)
        ds.cv.line(p_, q_, W_GRID, (1.0, 1.4), color=GRID)
    poly(ds, v, [(x0, fl), (x1, fl), (x1, fl - 0.025), (x0, fl - 0.025)], 0.0, fill=FLOOR_FILL)
    line(ds, v, [(x0, fl), (x1, fl)], CUT)
    zt = fl + lg["top_h"]
    line(ds, v, [(x0, zt), (x1, zt)], W_THIN, None, FAR)                  # ledge top (port wall, removed)
    # seats (upright), PAX 1 with the 95th, PAX 3 with the 50th feet forward
    po = tp["p50m"]["posture"]
    for rid in ("PAX 1", "PAX 3"):
        r = by[rid]
        pcs, posts = exec_seat_side(r, fl)
        for nm, P, f in pcs:
            cpoly(P, W_FINE, fill=f)
    q95 = I.cabin_pose(by["PAX 1"])
    q50 = I.cabin_pose(by["PAX 3"], I.P50_SCALE, po["shank"] if po["shank"] is not None else 10.0)
    for q, fill in ((q95, MAN_FILL), (q50, MAN50_FILL)):
        for P, f, nm in manikin_side(q):
            if nm in ("thigh", "shank", "foot", "torso"):
                cpoly(P, W_THIN, fill=fill, color=MAN_LINE)
    # the table: cut at this BL (both leaves span it), deployed
    ztt = fl + t["top_h"]
    poly(ds, v, [(t["x"][0], ztt), (t["x"][1], ztt), (t["x"][1], ztt - t["t"]), (t["x"][0], ztt - t["t"])], W_FINE,
         fill=VENEER)
    # the 95th's knee ring, and the 95th upright at PAX 3 (phantom knee) for comparison
    for q in (q95, I.cabin_pose(by["PAX 3"])):
        poly(ds, v, ellipse(q["knee"], q["knee_r"] + 0.012, q["knee_r"] + 0.012, 40), W_FINE, fill=None, color=ACCENT,
             dash=None if q is q95 else PHANTOM)
    # facing seat base front (PAX 1's shroud) vs the 50th's toes
    e = I.EXEC_SEAT
    bf = by["PAX 1"]["srp"][0] + e["base_u"]
    line(ds, v, [(bf, fl), (bf, fl + e["base_wh"][1] + 0.05)], W_THIN, (1.0, 0.7), ACCENT)
    # heights (ordinates at the right)
    X, Y = v.pt(x1, 0)
    Yk = v.pt(0, q95["knee"][1] + q95["knee_r"])[1]
    ds.cv.line(v.pt(q95["knee"][0], q95["knee"][1] + q95["knee_r"]), (X + 1.0, Yk), W_THIN, (0.8, 0.6), color=MUTED)
    ds.text(X + 1.5, Yk - 0.6, f"95TH KNEE {mm(q95['knee'][1] + q95['knee_r'] - fl)}", TXT, "mono", "start",
            vcenter=True, tag="ord")
    Yf = v.pt(0, fl)[1]
    ds.text(X + 1.5, Yf, f"FLOOR WL {mm(fl)}", TXT, "mono", "start", vcenter=True, tag="ord", fill=MUTED)
    Yu = v.pt(0, ztt - t["t"])[1]
    ds.cv.line(v.pt(t["x"][1], ztt - t["t"]), (X + 1.0, Yu), W_THIN, (0.8, 0.6), color=MUTED)
    ds.text(X + 1.5, Yu + 2.2, f"TABLE {mm(t['top_h'] - t['t'])}-{mm(t['top_h'])}", TXT, "mono", "start",
            vcenter=True, tag="ord")
    # labels
    leader_to(ds, v, (q95["knee"][0] + 0.03, q95["knee"][1] + q95["knee_r"] + 0.008), (6.47, 2.115),
              f"95TH AT PAX 1, FEET UNDER THE KNEES: {sgn_mm(tp['p95m']['full'][0])} INTO THE TABLE", "start",
              color=ACCENT, weight=600,
              lines=[f"(TO CLEAR IT HIS SHANKS NEED {tp['p95m']['posture']['shank']:.0f}°: FEET "
                     f"{mm(-tp['p95m']['posture']['toe_gap'])} UNDER THE FACING BASE)"])
    q = q50
    leader_to(ds, v, tuple(q["ankle"] + np.array([0.0, 0.06])), (7.12, 1.47),
              "50TH AT PAX 3,", "start", color=ACCENT, weight=600,
              lines=[f"FEET {po['shank']:.0f}° FWD: {sgn_mm(po['clear'])}", f"TOES {mm(po['toe_gap'])} SHORT OF",
                     "THE FACING BASE (DASHED)", "PHANTOM O: A 95TH HERE"])
    X, Y = v.pt(x0, z0)
    Xm = v.pt(0.5 * (x0 + x1), 0)[0]
    view_title(ds, Xm, Y + 9.0, "DETAIL G - CLUB TABLE vs LEGS",
               f"PAX 1 (95TH) / PAX 3 (50TH), BL {mm(abs(by['PAX 1']['bl']))} P, SEEN FROM PORT - SCALE 1:10")


# ---------------------------------------------------------------------------------------------------- tables / notes
def _win_near(r):
    best = None
    for side, lst in I.windows_by_side().items():
        if side != r["side"]:
            continue
        for wid, cx in lst:
            d = cx - r["occ"]
            if best is None or abs(d) < abs(best[1]):
                best = (wid.replace("win_", "").replace("door_cargo_win", "cd").replace("exit_hatch_win", "ex").upper(),
                        d)
    return f"{best[0]} {best[1] * 1000:+.0f}" if best else "-"


def draw_tables(ds, ctx):
    x0, x1 = COL_X
    rows = []
    rec = ctx["cabin"]["recline"]
    for r in ctx["seats"]:
        crew = r.get("crew")
        rows.append((r["id"], "FWD" if r["facing"] > 0 else "AFT", f"{r['bl'] * 1000:+.0f}", mm(r["front"]),
                     mm(r["occ"]), mm(r["srp"][0]), mm(r["rear"]),
                     "-" if crew else f"{rec[r['id']][0]:.0f}°", "-" if crew else _win_near(r)))
    cols = [("SEAT", 21.0, "l"), ("FACING", 15.0, "c"), ("BL", 14.0, "r"), ("CUSH. FRONT", 26.0, "r"),
            ("OCCUP. (POH)", 27.0, "r"), ("SRP STA", 20.0, "r"), ("BACK REAR", 22.0, "r"), ("RECLINE", 20.0, "r"),
            ("WINDOW", 30.0, "l")]
    y = table(ds, x0, 16.0, cols, rows, title=f"SEAT MAP - {I.DEFAULT_LAYOUT} (STA / BL mm)", size=2.2, row_h=3.7,
              head_h=4.6, title_h=5.6, font="mono", zebra=lambda i: i % 2 == 1)
    for i, t in enumerate(("Occupant = POH NGX Report 02406 W&B arm (datum = model datum). Crew: centre notch,",
                           f"±{mm(I.CREW_SEAT['travel_x'])}. Recline: reached, raised headrest (limit on L6B). "
                           "Window: nearest, offset.")):
        ds.text(x0, y + 3.2 + 2.7 * i, t, TXT, "label", "start", fill=MUTED, tag="tnote")
    ds._tables_bottom = y + 7.0


def draw_notes(ds, ctx, y0=None):
    """Legend, symbols and scale bars in the right-hand column (the notes and open points are on L6B)."""
    x0, x1 = COL_X
    lx = x0
    ly = y0 if y0 is not None else getattr(ds, "_legend_y", 222.0)
    ds.text(lx, ly, "LEGEND", 3.0, "label", "start", weight=600, tag="notes")
    items = [("section cut (OML, floor)", dict(w=CUT)), ("headliner / sidewall lining", dict(w=W_FINE)),
             ("port wall item (removed)", dict(dash=PHANTOM, color=MUTED)),
             ("hidden (carry-through, tunnel, lav)", dict(dash=(1.6, 0.8), color=MUTED)),
             ("sight line from the design eye", dict(dash=(3.0, 1.0), color=ACCENT)),
             ("travel / recline / deployed", dict(dash=PHANTOM, color=INK)),
             ("full rudder, table posture, 5F knee", dict(dash=PHANTOM, color=ACCENT)),
             ("95th-pct male manikin", dict(fill=MAN_FILL, w=W_THIN)),
             ("50th-pct male manikin", dict(fill=MAN50_FILL, w=W_THIN)),
             ("seat (leather)", dict(fill=SEAT_FILL, w=W_THIN)),
             ("veneer: divider, lav, cabinets, header", dict(fill=VENEER, w=W_THIN)),
             ("pleated curtain: FR34, divider", dict(fill=CURTAIN, w=W_THIN)),
             ("ledge / console", dict(fill=LEDGE_FILL, w=W_THIN))]
    M.legend_rows(ds, lx, ly + 5.0, [(lab, dict(st, w=st.get("w", W_FINE))) for lab, st in items], dy=3.9, size=TXT,
                  tag="notes", sample=16.0)
    lx2 = x0 + 108.0
    ds.text(lx2, ly, "SYMBOLS", 3.0, "label", "start", weight=600, tag="notes")
    srp_symbol(ds, lx2 + 2.0, ly + 5.0, 1.1)
    ds.text(lx2 + 5.5, ly + 5.0, "seat reference point (SRP)", TXT, "label", "start", vcenter=True, tag="notes")
    eye_symbol(ds, lx2 + 2.0, ly + 8.9, 1.0)
    ds.text(lx2 + 5.5, ly + 8.9, "design eye / seated eye", TXT, "label", "start", vcenter=True, tag="notes")
    ds.cv.line((lx2 - 0.5, ly + 12.8), (lx2 + 4.5, ly + 12.8), 1.1, color="#5B89A6")
    ds.text(lx2 + 5.5, ly + 12.8, "window (plan: on the sidewall)", TXT, "label", "start", vcenter=True, tag="notes")
    _hatch_legend(ds, lx2 - 1.0, ly + 15.6, "#E3A49C")
    ds.text(lx2 + 5.5, ly + 16.7, "exit / entry clear zone", TXT, "label", "start", vcenter=True, tag="notes")
    scale_bar(ds, lx2, ly + 27.0, 20, length_m=1.5, step_m=0.5)
    scale_bar(ds, lx2, ly + 38.5, 10, length_m=0.8, step_m=0.2)
    scale_bar(ds, lx2, ly + 50.0, 5, length_m=0.4, step_m=0.1)
    y = ly + 5.0 + 3.9 * len(items) + 4.0
    for i, t in enumerate(("NOTES, CHECK TABLES, REACH, DEVIATIONS & DECISIONS, KEY PARAMETERS",
                           "AND THE OPEN POINTS FOR THE OWNER: SHEET L6B (PC12-L6 SHEET 2 OF 2).")):
        ds.text(lx, y + 3.2 * i, t, 2.4, "label", "start", weight=600, fill=ACCENT, tag="notes")
    return y + 6.4


def revisions_block(ds, x0, y0, x1, size=TXT, title_size=2.6, rows=None):
    """REVISIONS table (rev, date, wrapped description; default REVISIONS) for both PC12-L6 sheets; returns the
    bottom y."""
    from drawing import sheet as S_
    from drawing.master import W_TABLE, W_TABLE_IN
    cv = ds.cv
    lh = 1.32 * size
    th = 1.9 * title_size
    cols = (x0, x0 + 3.2 * size, x0 + 11.0 * size, x1)
    cv.rect(x0, y0, x1 - x0, th, lw=W_TABLE, fill=INK)
    ds.text(x0 + 1.5, y0 + 0.5 * th, f"REVISIONS - {SHEET['dwg']}", title_size, "label", "start", weight=600,
            fill=PAPER, vcenter=True, tag="table")
    y = y0 + th
    for i, h in enumerate(("REV", "DATE", "DESCRIPTION")):
        ds.text(0.5 * (cols[i] + cols[i + 1]), y + 0.5 * lh + 0.3, h, size, "label", "middle", weight=600,
                vcenter=True, tag="table")
    y += lh + 0.6
    cv.line((x0, y), (x1, y), W_TABLE)
    top = y
    for rev, date, desc in rows or REVISIONS:
        L = S_.wrap(desc, cols[3] - cols[2] - 2.0, size)
        for k, t in enumerate(L):
            ds.text(cols[2] + 1.0, y + 0.3 + lh * (k + 0.5), t, size, "label", "start", vcenter=True, tag="table")
        ds.text(0.5 * (cols[0] + cols[1]), y + 0.3 + 0.5 * lh, rev, size, "mono", "middle", vcenter=True, tag="table",
                weight=600)
        ds.text(0.5 * (cols[1] + cols[2]), y + 0.3 + 0.5 * lh, date, size, "mono", "middle", vcenter=True, tag="table")
        y += lh * len(L) + 0.6
        cv.line((x0, y), (x1, y), W_TABLE_IN)
    for xx in cols[1:-1]:
        cv.line((xx, top - lh - 0.6), (xx, y), W_TABLE_IN)
    cv.rect(x0, y0, x1 - x0, y - y0, lw=W_TABLE)
    return y


def _hatch_legend(ds, x, y, color):
    ds.cv.rect(x, y, 6.0, 2.2, lw=W_THIN, color=color)
    for k in range(5):
        ds.cv.line((x + k * 1.4, y + 2.2), (x + k * 1.4 + 1.2, y), 0.1, color=color)


# ---------------------------------------------------------------------------------------------------- overlay
REF_MARKS = M.ROOT / "refs" / "cache" / "interior_ref_marks.json"


def draw_overlay(ds):
    """Private overlay: the Pilatus plan-render footprints (refs/cache, git-ignored) in blue on the plan."""
    d = json.loads(REF_MARKS.read_text())
    vn = ds.views["plan"]
    for it in d.get("plan_boxes", []):
        x0, x1, y0, y1 = it["x0"], it["x1"], it["y0"], it["y1"]
        ds.ov_polylines(vn, [np.array([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)])], color=M.BLUE, w=0.22,
                        dash=(1.2, 0.6))
        X, Y = vn.pt(x0, y1)
        ds.ov_text(X + 0.5, Y - 0.6, it["name"], size=1.8, color=M.BLUE)
    X, Y = vn.pt(PLAN_BOX[0] + 0.02, PLAN_BOX[1] + 0.02)
    ds.ov_text(X, Y, "BLUE: PILATUS TECH-DATA PLAN RENDER, CALIBRATED (refs/cache/interior_notes_cabin.md)",
               size=1.8, color=M.BLUE)


if __name__ == "__main__":
    M.main(["L6", "L6B"] + sys.argv[1:])
