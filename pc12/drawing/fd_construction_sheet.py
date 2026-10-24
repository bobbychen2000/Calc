"""
Sheet L6C -- FLIGHT DECK CONSTRUCTION & FINISH (first-principles flight deck, parts A4 / A6), drawn from the
interior tables: interior.FD_CONSTRUCTION (what each flight-deck part is made of, how it is finished, its edges and
its printing), CREW_SEAT sheepskin_hide / sheepskin_pile (the cover as made, section S-S), PEDESTAL rim (the
quadrant's cast rim, section R-R) and PEDESTAL blend (the centre-stack moulding's front-edge radius and its fillet into
the rim, side profile at BL 0).  No Pilatus geometry: the sheet has no overlay content.
"""
from __future__ import annotations

import math

import numpy as np

from drawing.master import (W_OBJ, W_FINE, W_DIM, W_THIN, MUTED, ACCENT, PHANTOM, table, notes)
from model import interior as I

SHEET = dict(id="L6C", title="FLIGHT DECK CONSTRUCTION & FINISH", subtitle="FLIGHT DECK CONSTRUCTION & FINISH",
             size="A2", scale="AS SHOWN", order=63, rev="A")

REVISIONS = (
    ("A", "2026-10-24", "First issue (first-principles flight deck A4 / A6): FD_CONSTRUCTION; the sheepskin cover split "
                        "into hide 4 + pile 30 (sum = CREW_SEAT sheepskin_t 34); PEDESTAL rim (14 x 6, R 20 corners, top "
                        "rolled R 3) and blend (R 12 front edges, R 8 fillet into the rim)."),
)


def _dim_h(ds, x0, x1, y, txt, size=2.4):
    cv = ds.cv
    cv.line((x0, y), (x1, y), W_DIM)
    for x in (x0, x1):
        cv.line((x, y - 1.2), (x, y + 1.2), W_DIM)
    ds.text(0.5 * (x0 + x1), y - 1.0, txt, size, "mono", "middle")


def _dim_v(ds, x, y0, y1, txt, size=2.4, side=1):
    cv = ds.cv
    cv.line((x, y0), (x, y1), W_DIM)
    for y in (y0, y1):
        cv.line((x - 1.2, y), (x + 1.2, y), W_DIM)
    ds.text(x + side * 1.5, 0.5 * (y0 + y1) + 0.8, txt, size, "mono", "start" if side > 0 else "end")


def section_sheepskin(ds, x0, y0):
    """S-S: the crew cushion top as made, 1:1 -- leather, hide, pile (the viewer's shell zone dashed)."""
    c = I.CREW_SEAT
    hide, pile = 1000 * float(c["sheepskin_hide"]), 1000 * float(c["sheepskin_pile"])
    cv = ds.cv
    W = 110.0
    ds.text(x0, y0 - 4, "SECTION S-S  CREW CUSHION COVER AS MADE  1:1", 3.2, "label", "start", weight=600)
    yl = y0 + 50.0                                         # leather surface (cushion top)
    xs = np.linspace(x0, x0 + W, 60)
    crown = 3.0 * np.sin(np.linspace(0, math.pi, 60))       # the cushion's crown, schematic
    leather = np.c_[xs, yl - crown]
    cv.path([tuple(p) for p in leather], W_OBJ)
    cv.polygon([tuple(p) for p in leather] + [(x0 + W, yl + 12), (x0, yl + 12)], fill="#E9E5DF")
    hide_l = leather - [0, hide]
    cv.polygon([tuple(p) for p in leather] + [tuple(p) for p in hide_l[::-1]], fill="#B9A58C")
    cv.path([tuple(p) for p in hide_l], W_FINE)
    pile_l = hide_l - [0, pile]
    rng = np.random.default_rng(3)
    cv.polygon([tuple(p) for p in hide_l] + [tuple(p) for p in pile_l[::-1]], fill="#D8D2D6")
    for x in np.arange(x0 + 2, x0 + W - 2, 2.2):            # wool fibres (schematic)
        i = int((x - x0) / W * 59)
        yb = hide_l[i, 1]
        h = pile * (0.85 + 0.15 * rng.random())
        cv.line((x, yb), (x + 0.8 * rng.standard_normal(), yb - h), W_THIN, color=MUTED)
    cv.path([tuple(p) for p in pile_l], W_OBJ)
    shell = pile_l + [0, 9.0]
    cv.path([tuple(p) for p in shell], W_FINE, dash=PHANTOM)
    xd = x0 + W + 6
    _dim_v(ds, xd, hide_l[-1, 1], leather[-1, 1], f"HIDE {hide:.0f} [E]")
    _dim_v(ds, xd + 22, pile_l[-1, 1], hide_l[-1, 1], f"PILE {pile:.0f} [M]")
    _dim_v(ds, xd + 44, pile_l[-1, 1], leather[-1, 1], f"COVER {hide + pile:.0f} = sheepskin_t")
    ds.text(x0 + 2, pile_l[30, 1] - 6.0, "VIEWER PILE SHELLS: TOP 9 mm OF THE PILE", 2.3, "label", "start",
            fill=ACCENT)
    ds.text(x0 + 2, yl + 7, "CUSHION LEATHER (leather_crew) ON FOAM", 2.4, "label", "start", fill=MUTED)
    return yl + 14


def section_rim(ds, x0, y0):
    """R-R: the quadrant's cast rim, 2:1, and a corner of it in plan."""
    w, h, rc, rr = (1000 * float(v) for v in I.PEDESTAL["rim"])
    k = 2.0
    cv = ds.cv
    ds.text(x0, y0 - 4, "SECTION R-R  QUADRANT RIM  2:1", 3.2, "label", "start", weight=600)
    yb = y0 + 40.0
    # plate (3 mm) to the right, rim to the left of the plate's edge
    xp = x0 + 20.0
    cv.polygon([(xp + k * w, yb), (xp + k * w + 60, yb), (xp + k * w + 60, yb + k * 3), (xp + k * w, yb + k * 3)],
               fill="#2A2C30")
    ds.text(xp + k * w + 30, yb + k * 3 + 5, "PLATE 3, BLACK ANODISED, PRINTED", 2.3, "label", "middle", fill=MUTED)
    # rim profile: outer foot, rise, rolled top R rr, inner wall down to the plate
    a = np.linspace(0, math.pi, 13)
    top = [(xp + k * (w / 2 - (w / 2 - rr) * math.cos(t) if False else 0), 0) for t in a]   # placeholder (unused)
    del top
    prof = [(xp, yb + k * 3)]
    prof.append((xp, yb - k * (h - rr)))
    for t in np.linspace(math.pi, 0.5 * math.pi, 7):
        prof.append((xp + k * rr + k * rr * math.cos(t), yb - k * (h - rr) - k * rr * math.sin(t)))
    for t in np.linspace(0.5 * math.pi, 0.0, 7):
        prof.append((xp + k * (w - rr) + k * rr * math.cos(t), yb - k * (h - rr) - k * rr * math.sin(t)))
    prof.append((xp + k * w, yb))
    prof.append((xp + k * w, yb + k * 3))
    cv.polygon(prof, fill="#8D8E91")
    cv.path(prof, W_OBJ, closed=True)
    _dim_h(ds, xp, xp + k * w, yb + k * 3 + 6, f"{w:.0f}")
    _dim_v(ds, xp - 4, yb - k * h, yb, f"{h:.0f}", side=-1)
    ds.text(xp + k * w * 0.5, yb - k * h - 3, f"TOP ROLLED R {rr:.0f}", 2.4, "mono", "middle")
    ds.text(xp - 2, yb + k * 3 + 12, "RIM: CAST, SATIN GUNMETAL (pedestal_gunmetal)", 2.3, "label", "start",
            fill=MUTED)
    # plan corner, 1:1
    xc, yc = x0 + 120, y0 + 10
    ds.text(xc, yc - 2, "PLAN CORNER 1:1", 2.5, "label", "start", weight=600)
    R = rc
    th = np.linspace(math.pi, 1.5 * math.pi, 12)
    cx, cy = xc + R, yc + 6 + R
    outer = [(cx + R * math.cos(t), cy + R * math.sin(t)) for t in th]
    Ri = max(R - w, 2.0)
    inner = [(cx + Ri * math.cos(t), cy + Ri * math.sin(t)) for t in th]
    cv.path([(xc, cy + 30)] + outer + [(cx + 30, yc + 6)], W_OBJ)
    cv.path([(xc + w, cy + 30)] + inner + [(cx + 30, yc + 6 + w)], W_FINE)
    ds.text(cx + 4, cy - 2, f"R {rc:.0f}", 2.4, "mono", "start")
    return yb + 30


def section_blend(ds, x0, y0):
    """The centre stack's side profile at BL 0 (PEDESTAL stack) with its front-edge radius and the fillet into the rim,
    1:5."""
    er, fr = (1000 * float(v) for v in I.PEDESTAL["blend"])
    st = [(float(a), float(b)) for a, b in I.PEDESTAL["stack"]]
    k = 0.2 * 1000.0 / 1000.0                    # 1:5 -> sheet mm per model mm
    cv = ds.cv
    ds.text(x0, y0 - 4, "CENTRE STACK PROFILE AT BL 0 WITH ITS BLENDS  1:5", 3.2, "label", "start", weight=600)
    xm, zm = st[0]
    P = [(x0 + 10 + 1000 * (x - xm) * k, y0 + 6 - 1000 * dz * k) for x, dz in st]
    zt = float(I.PEDESTAL["top_h"])
    # the quadrant plate's top relative to the MFD row's reference: drawn through the last profile point
    xq0, xq1 = (float(v) for v in I.PEDESTAL["x"])
    Pq = [P[-1], (x0 + 10 + 1000 * (xq1 - xm) * k, P[-1][1])]
    cv.path(P, W_OBJ)
    cv.path(Pq, W_OBJ)
    # the fillet into the rim (schematic arc of radius fr at the last corner)
    xa, ya = P[-1]
    d0 = np.array(P[-2]) - np.array(P[-1])
    d0 /= np.linalg.norm(d0)
    rs = 6.0 * fr * k                          # the fillet drawn 6x (schematic: R 8 is 1.6 mm at 1:5)
    t0, t1 = np.array([xa, ya]) + rs * d0, np.array([xa + rs, ya])
    arc = [tuple((1 - u) ** 2 * t0 + 2 * u * (1 - u) * np.array([xa, ya]) + u ** 2 * t1) for u in np.linspace(0, 1, 9)]
    cv.path(arc, W_OBJ, color=ACCENT)
    ds.text(xa + 3, ya - fr * k - 2, f"FILLET R {fr:.0f} INTO THE RIM (x6)", 2.4, "mono", "start")
    ds.text(P[1][0] + 3, P[1][1] + 2, f"FRONT EDGES R {er:.0f} (MOULDED)", 2.4, "mono", "start")
    for (x, dz), (X, Y) in zip(st, P):
        cv.circle(X, Y, 0.5, W_FINE)
    ds.text(x0 + 10, max(p[1] for p in P) + 10,
            f"PEDESTAL stack: {len(st)} points (x, dz vs the MFD); quadrant plate STA {xq0:.3f}-{xq1:.3f}, "
            f"{1000 * zt:.0f} above the floor", 2.3, "label", "start", fill=MUTED)
    return max(p[1] for p in P) + 16


def draw(ds):
    ds.frame_and_title()
    FX0, FY0, FX1, FY1 = ds.frame
    x0, y0 = FX0 + 8, FY0 + 12
    rows = []
    for key, v in I.FD_CONSTRUCTION.items():
        cons, fin, edge, prt, mats = v
        rows.append((key.upper(), cons, fin, edge, prt))
    cols = [("PART", 22, "l"), ("CONSTRUCTION", 92, "l"), ("FINISH", 62, "l"), ("EDGES / FASTENERS", 72, "l"),
            ("PRINTING", 70, "l")]
    y = table(ds, x0, y0, cols, rows, title="FD_CONSTRUCTION - WHAT EACH FLIGHT-DECK PART IS MADE OF", size=2.2,
              row_h=4.6, font="label")
    mrows = []
    for key, v in I.FD_CONSTRUCTION.items():
        chunks, line = [], []
        for m in v[4]:
            line.append(m)
            if len(", ".join(line)) > 110:
                chunks.append(", ".join(line))
                line = []
        if line:
            chunks.append(", ".join(line))
        mrows += [(key.upper() if j == 0 else "", c) for j, c in enumerate(chunks)]
    y = table(ds, x0, y + 6, [("PART", 22, "l"), ("MATERIALS (assemble.MATERIALS names; fit_check 36: every flight-deck "
                                                   "material in one row)", 296, "l")], mrows, size=2.0, row_h=4.0,
              font="mono")
    ys = y + 16
    section_sheepskin(ds, x0, ys)
    section_rim(ds, x0 + 190, ys)
    yb = section_blend(ds, x0 + 360, ys)
    notes(ds, FX1 - 200, y0, FX1 - 8, [
        "Drawn from model/interior.py FD_CONSTRUCTION, CREW_SEAT sheepskin_hide / sheepskin_pile and PEDESTAL rim / "
        "blend; the 3-D builders read the same values (fd_pedestal.quadrant's rim, stack_shell's blends; seats.py's "
        "cover).",
        "REVIEW NOTE (rev A): the cover split is a construction fact, not a shape change -- the drawn 34 mm cover and "
        "every L6B check on it are unchanged; the pile depth only sets where the viewer's pile shells sit.",
        "REVIEW NOTE (rev A): the rim and blend tabulate what the builders had as constants (QUAD frame 14 x 6 R 20, "
        "STACK edge_r 12) and add the rolled top R 3 and the R 8 fillet: the rim reads as a cast part.",
        "Printing is pad / silk-screen printing of pseudo-text (no readable markings: owner rule); in 3-D a decal "
        "0.15 mm over its surface (model/fd_print.py; fit_check 34).",
        "Sources: [S] published data, [M] measured on the s/n 3001 photos, [E] engineering estimate.",
    ], title="NOTES")
    ry = max(yb, FY1 - 110)
    ds.text(x0, ry, "REVISIONS - PC12-L6C", 2.8, "label", "start", weight=600)
    for k_, (rev, date, txt) in enumerate(REVISIONS):
        from drawing import sheet as S
        for j, ln in enumerate(S.wrap(f"{rev}  {date}  {txt}", 330, 2.3)):
            ds.text(x0, ry + 5 + 3.4 * j, ln, 2.3, "label", "start")
