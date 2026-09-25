"""
PC-12 sections sheet (A2 landscape) -> out/pc12_sections.svg + out/pc12_sections.pdf

  A-A  wing root aerofoil (BL 0)         1:10   model.wing.section_at(0).airfoil
  B-B  wing tip aerofoil (BL SEMI)       1:10   model.wing.section_at(SEMI).airfoil
  C    Fowler flap at BL 3,000           1:5    flap_loop / flap_cove, 0 / 15 / 30 / 40 deg
  D    propeller blade planform + twist  1:10   measured from powerplant.blade_geometry()

    cd <project root> && python3 -m drawing.sections
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from drawing import sheet as G                       # noqa: E402  (shared helpers & styles)
from drawing.canvas import text_width               # noqa: E402

W_SHEET, H_SHEET = 594.0, 420.0
FRAME = (20.0, 10.0, 584.0, 410.0)
FLAP_SETTINGS = (0.0, 15.0, 30.0, 40.0)


def cos_x(n=161):
    return 0.5 * (1 - np.cos(np.linspace(0, np.pi, n)))


def aerofoil_outline(af, n=161):
    """Closed outline in chord units: lower TE -> LE -> upper TE -> (blunt TE) back."""
    x = cos_x(n)
    lo = np.stack([x[::-1], af.lower(x[::-1])], 1)
    up = np.stack([x[1:], af.upper(x[1:])], 1)
    return np.vstack([lo, up, lo[:1]])


def to_sheet(P, x0, y0, k):
    """chord-frame (x aft, z up) metres -> sheet mm; (x0, y0) = sheet position of the origin."""
    P = np.asarray(P, float)
    return np.stack([x0 + k * P[:, 0], y0 - k * P[:, 1]], 1)


def section_title(sh, x, y, title, sub):
    sh.text(x, y, title, 4.4, "label", "start", weight=600, spacing=0.3)
    sh.text(x, y + 4.6, sub, 2.7, "label", "start")


def draw_aerofoil_section(sh, y_bl, label, x0, y0, scale, title_y):
    from model import wing as W
    sec = W.section_at(y_bl)
    af = sec.airfoil
    c = sec.chord
    k = 1000.0 / scale
    name = W.ROOT_AF.name if y_bl <= 0.6 else (W.TIP_AF.name if y_bl >= W.SEMI - 1e-6 else af.name)
    outline = aerofoil_outline(af) * c
    cv = sh.cv
    cv.path(to_sheet(outline, x0, y0, k), G.W_OBJ, closed=True)
    # chord line and mean line
    cv.line((x0 - 6.0, y0), (x0 + k * c + 6.0, y0), G.W_DIM, G.CHAIN)
    xm = cos_x(81)
    mean = np.stack([xm * c, af.camber(xm) * c], 1)
    cv.path(to_sheet(mean, x0, y0, k), G.W_DIM, G.PHANTOM)
    # maximum thickness
    xs = np.linspace(0.05, 0.95, 901)
    th = af.thickness(xs)
    i = int(np.argmax(th))
    xt, t = xs[i], th[i]
    pu = to_sheet([[xt * c, af.upper(xt) * c]], x0, y0, k)[0]
    pl = to_sheet([[xt * c, af.lower(xt) * c]], x0, y0, k)[0]
    zlow = float(np.min(af.lower(xs))) * c
    zup = float(np.max(af.upper(xs))) * c
    # maximum thickness: dimension line at its station, value in a label above the section
    sh.dim(pl, pu, pu[0], "", "v", f1=pl, f2=pu, show_text=False)
    ylab = y0 - k * zup - 5.0
    sh.cv.line((pu[0], pu[1] - 1.0), (pu[0], ylab + 1.2), G.W_DIM)
    sh.text(pu[0] + 1.5, ylab, f"t max {G.thou(t * c * 1000)} ({100 * t:.1f} % c) AT {100 * xt:.0f} % c",
            2.6, "mono", "start", tag="label")
    # chord dimension below
    yd = y0 - k * zlow + 9.0
    sh.dim((x0, y0), (x0 + k * c, y0), yd, G.thou(c * 1000), "h", f1=(x0, y0 + 1.5), f2=(x0 + k * c, y0 + 1.5))
    # labels on the construction lines
    sh.text(x0 + k * c + 7.0, y0 + 0.9, "CHORD LINE", 2.3, "label", "start", tag="label")
    inc = math.degrees(sec.twist)
    section_title(sh, x0, title_y, f"SECTION {label}",
                  f"WING {'ROOT' if y_bl <= 0.6 else 'TIP'} · BL {G.thou(y_bl * 1000)} · {name} · "
                  f"INCIDENCE {inc:+.1f}° · SCALE 1:{scale}")
    return dict(chord=c, t=t, xt=xt, zup=zup, zlow=zlow)


def rot(P, H, deg):
    """rotate chord-frame points about H by -deg (trailing edge down for deg > 0)."""
    a = math.radians(-deg)
    R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    return (np.asarray(P) - H) @ R.T + H


def flap_pose(loop, H, deg, max_deg=40.0):
    from model import wing as W
    f = deg / max_deg
    return rot(loop, H, deg) + np.array([W.FLAP_TRAVEL[0] * f, W.FLAP_TRAVEL[1] * f])


def draw_flap_detail(sh, x0, y0, scale, title_y, y_bl=3.0):
    """Detail C: wing trailing edge at BL y_bl with the Fowler flap at 0/15/30/40 deg.
    (x0, y0) = sheet position of the chord-line point at x/c = 0.73 (the hinge station)."""
    from model import wing as W
    sec = W.section_at(y_bl)
    af = sec.airfoil
    c = sec.chord
    k = 1000.0 / scale
    cv = sh.cv
    xh = 0.73
    H = np.array([xh, float(af.camber(xh))])
    ox = x0 - k * c * xh                      # sheet X of the (virtual) leading edge

    def S(P):
        return to_sheet(np.asarray(P) * c, ox, y0, k)

    # fixed structure aft of the break line at x/c = 0.46
    xb = 0.46
    xu = np.linspace(xb, W.FLAP_X_LIP, 60)
    xl = np.linspace(W.FLAP_X_LO, xb, 60)
    cove = W.flap_cove(sec)
    upper = np.stack([xu, af.upper(xu)], 1)
    lower = np.stack([xl, af.lower(xl)], 1)
    fixed = np.vstack([upper, cove[::-1], lower])            # upper -> lip -> cove -> lower lip -> break
    cv.path(S(fixed), G.W_OBJ)
    # break line (zig-zag) closing the cut at x/c = 0.46
    zb_u, zb_l = float(af.upper(xb)), float(af.lower(xb))
    zz = np.linspace(zb_u, zb_l, 7)
    brk = np.stack([np.full(7, xb) + np.array([0, 0.012, -0.012, 0.012, -0.012, 0.012, 0]), zz], 1)
    cv.path(S(brk), G.W_FINE)
    # chord line
    p0 = S([[xb - 0.03, 0.0]])[0]
    p1 = S([[1.30, 0.0]])[0]
    cv.line(tuple(p0), tuple(p1), G.W_DIM, G.CHAIN)
    # flap positions
    loop = W.flap_loop(sec)
    loop_c = np.vstack([loop, loop[:1]])
    tes = {}
    for deg in FLAP_SETTINGS:
        P = flap_pose(loop_c, H, deg)
        if deg == 0.0:
            cv.path(S(P), G.W_OBJ, closed=True)
        else:
            cv.path(S(P), G.W_FINE, G.PHANTOM, closed=True)
        te = flap_pose(np.array([[1.0, 0.5 * (af.upper(1.0) + af.lower(1.0))]]), H, deg)[0]
        tes[deg] = S([te])[0]
        hp = S(flap_pose(np.array([H]), H, deg))[0]
        cv.line((hp[0] - 1.8, hp[1]), (hp[0] + 1.8, hp[1]), G.W_DIM)
        cv.line((hp[0], hp[1] - 1.8), (hp[0], hp[1] + 1.8), G.W_DIM)
    # hinge-point path (0 -> 40 deg) and labels, leaders from outside the section
    path = [S(flap_pose(np.array([H]), H, d))[0] for d in np.linspace(0, 40, 9)]
    cv.path(path, G.W_DIM, (1.5, 1.0))
    hp0 = S([H])[0]
    ztop = y0 - k * float(af.upper(xh)) * c
    lab = (hp0[0] - 18.0, ztop - 12.0)
    cv.line((lab[0] + 1.0, lab[1] + 1.0), (hp0[0] - 0.5, hp0[1] - 0.5), G.W_DIM)
    cv.circle(hp0[0], hp0[1], 0.5, w=0.0, fill=G.INK, stroke=False)
    sh.text(lab[0], lab[1], f"HINGE {xh:.2f} c ON MEAN LINE", 2.5, "label", "end", tag="label")
    h40 = path[-1]
    lab2 = (h40[0] + 16.0, ztop - 4.0)
    cv.line((lab2[0] - 1.0, lab2[1] + 1.0), (h40[0] + 0.5, h40[1] - 0.5), G.W_DIM)
    sh.text(lab2[0], lab2[1], "HINGE PATH 0° → 40°", 2.5, "label", "start", tag="label")
    for deg, p in tes.items():
        sh.text(p[0] + 2.5, p[1] + 1.0, f"{deg:.0f}°", 3.0, "mono", "start", tag="label")
    section_title(sh, S([[xb, 0]])[0][0], title_y, "DETAIL C  ·  FOWLER FLAP",
                  f"SECTION AT BL {G.thou(y_bl * 1000)} · CHORD {G.thou(c * 1000)} · FLAP 0° SOLID, 15° / 30° / 40° PHANTOM"
                  f" · SCALE 1:{scale}")
    return c


def draw_flap_table(sh, x0, y0, chord):
    cv = sh.cv
    rows = [("SETTING", "ROTATION", "AFT TRAVEL", "DROP")]
    for d in FLAP_SETTINGS:
        f = d / 40.0
        rows.append((f"{d:.0f}°", f"{d:.0f}°", G.thou(0.20 * f * chord * 1000), G.thou(0.035 * f * chord * 1000)))
    ws = [22.0, 22.0, 26.0, 20.0]
    rh = 6.2
    cv.rect(x0, y0, sum(ws), rh * len(rows), lw=G.W_TABLE)
    xs = np.cumsum([x0] + ws)
    for r, row in enumerate(rows):
        yy = y0 + rh * (r + 0.5)
        for i, val in enumerate(row):
            if r == 0:
                sh.text(0.5 * (xs[i] + xs[i + 1]), yy, val, 2.4, "label", "middle", weight=600, vcenter=True)
            else:
                sh.text(0.5 * (xs[i] + xs[i + 1]), yy, val, 2.9, "mono", "middle", vcenter=True)
        if r:
            cv.line((x0, y0 + rh * r), (xs[-1], y0 + rh * r), G.W_TABLE_IN)
    for xx in xs[1:-1]:
        cv.line((xx, y0), (xx, y0 + rh * len(rows)), G.W_TABLE_IN)
    sh.text(x0, y0 - 2.0, "FLAP SETTINGS (mm AT BL 3,000)", 2.6, "label", "start", weight=600)
    return y0 + rh * len(rows)


def blade_stations():
    """Chord, blade angle and t/c measured from the lofted blade (model.powerplant)."""
    from model import powerplant as PP
    _, rs, Pm = PP.blade_geometry()
    n_lo = 40                                       # blade_geometry(): lower surface first, TE -> LE
    out = []
    for r, ring in zip(rs, Pm):
        P = ring[:, :2]
        te, le = P[0], P[n_lo - 1]
        ch = np.linalg.norm(te - le)
        d = (te - le) / ch
        beta = math.degrees(math.atan2(d[0], -d[1]))
        nrm = np.array([-d[1], d[0]])
        thick = (P @ nrm).max() - (P @ nrm).min()
        out.append((r, ch, beta, thick / ch, float(le @ d), float(te @ d)))
    return PP.PROP_R, np.array(out)


def draw_blade(sh, x0, y0, scale, title_y):
    """Planform: radius to the right, pitch axis horizontal, leading edge up."""
    from model import powerplant as PP
    R, st = blade_stations()
    k = 1000.0 / scale
    cv = sh.cv
    r, q_le, q_te = st[:, 0], st[:, 4], st[:, 5]
    le = np.stack([x0 + k * r, y0 + k * q_le], 1)
    te = np.stack([x0 + k * r, y0 + k * q_te], 1)
    outline = np.vstack([le, te[::-1], le[:1]])
    cv.path(outline, G.W_OBJ, closed=True)
    cv.line((x0 - 4.0, y0), (x0 + k * R + 6.0, y0), G.W_DIM, G.CHAIN)      # pitch-change axis
    sh.text(x0 + k * R + 7.0, y0 + 0.9, "PITCH AXIS", 2.3, "label", "start", tag="label")
    # spinner radius and hub
    xs_ = x0 + k * 0.291
    cv.line((xs_, y0 - 14.0), (xs_, y0 + 16.0), G.W_DIM, G.PHANTOM)
    sh.text(xs_ - 1.0, y0 - 15.0, "SPINNER", 2.2, "label", "end", tag="label")
    cv.line((x0, y0 - 5.0), (x0, y0 + 5.0), G.W_DIM)
    sh.text(x0 - 1.0, y0 + 9.0, "℄ HUB", 2.2, "label", "middle", tag="label")
    # radius dimension
    sh.dim((x0, y0), (x0 + k * R, y0), y0 + k * max(q_te) + 11.0, G.thou(R * 1000), "h",
           f1=(x0, y0 + 5.5), f2=(x0 + k * R, y0 + k * q_te[-1] + 1.5))
    section_title(sh, x0 - 4.0, title_y, "DETAIL D  ·  PROPELLER BLADE",
                  f"HARTZELL 5-BLADE · Ø{G.thou(2 * R * 1000)} · PLANFORM ABOUT THE PITCH AXIS, LE UP · SCALE 1:{scale}")
    return R, st


def draw_twist_table(sh, x0, y0, R, st):
    cv = sh.cv
    fr = [0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 1.00]
    r = st[:, 0] / R
    rows = [("r / R", "r", "CHORD", "β", "t / c")]
    for f in fr:
        ff = min(f, r[-1])
        rows.append((f"{f:.2f}", G.thou(ff * R * 1000), G.thou(np.interp(ff, r, st[:, 1]) * 1000),
                     f"{np.interp(ff, r, st[:, 2]):.1f}°", f"{100 * np.interp(ff, r, st[:, 3]):.1f} %"))
    ws = [16.0, 18.0, 18.0, 16.0, 18.0]
    rh = 5.6
    xs = np.cumsum([x0] + ws)
    for i, row in enumerate(rows):
        yy = y0 + rh * (i + 0.5)
        for j, v in enumerate(row):
            if i == 0:
                sh.text(0.5 * (xs[j] + xs[j + 1]), yy, v, 2.4, "label", "middle", weight=600, vcenter=True)
            else:
                sh.text(0.5 * (xs[j] + xs[j + 1]), yy, v, 2.7, "mono", "middle", vcenter=True)
        if i:
            cv.line((x0, y0 + rh * i), (xs[-1], y0 + rh * i), G.W_TABLE_IN)
    for xx in xs[1:-1]:
        cv.line((xx, y0), (xx, y0 + rh * len(rows)), G.W_TABLE_IN)
    cv.rect(x0, y0, xs[-1] - x0, rh * len(rows), lw=G.W_TABLE)
    sh.text(x0, y0 - 2.0, "BLADE STATIONS (β FROM THE PLANE OF ROTATION)", 2.6, "label", "start", weight=600)
    return y0 + rh * len(rows)


def draw_notes(sh, x0, y0, x1):
    notes = [
        "Dimensions in millimetres unless stated. Aerofoils drawn in their chord frame (chord line horizontal).",
        "LS(1)-0417MOD / LS(1)-0313 sections are model reconstructions (CST fits to the sections of the Pilatus "
        "NGX model drawing), not certified ordinates.",
        "Flap kinematics per model: rotation about the hinge at 0.73 c on the mean line, aft travel 0.20 c and "
        "drop 0.035 c, both proportional to deflection (full at 40°).",
        "Blade chord, angle β and t/c measured from the lofted blade at flight-fine pitch (geometric pitch 2.9 m).",
    ]
    size = 2.7
    sh.text(x0, y0 + 3.6, "NOTES", 3.4, "label", "start", weight=600, spacing=0.3)
    y = y0 + 9.0
    for i, n in enumerate(notes):
        lines = G.wrap(n, x1 - x0 - 8.0, size)
        sh.text(x0, y, f"{i + 1}.", size, "label", "start")
        for kk, ln in enumerate(lines):
            sh.text(x0 + 5.5, y + 3.8 * kk, ln, size, "label", "start")
        y += 3.8 * len(lines) + 1.3
    return y


def build(verbose=True):
    from model import wing as W
    sh = G.Sheet()
    sh.cv.W, sh.cv.H = W_SHEET, H_SHEET
    G.draw_frame(sh, FRAME, ncol=12, nrow=8)
    # row 1: root and tip sections at 1:10
    a = draw_aerofoil_section(sh, 0.0, "A–A", 45.0, 62.0, 10, 22.0)
    b = draw_aerofoil_section(sh, W.SEMI, "B–B", 330.0, 62.0, 10, 22.0)
    # row 2: flap detail at 1:5, settings table
    chord = draw_flap_detail(sh, 245.0, 150.0, 5, 99.0)
    draw_flap_table(sh, 462.0, 128.0, chord)
    # row 3: propeller blade + table, notes, title block
    R, st = draw_blade(sh, 52.0, 322.0, 10, 290.0)
    draw_twist_table(sh, 210.0, 300.0, R, st)
    tb = (324.0, FRAME[3] - 6.0 - 71.0, FRAME[2] - 6.0, FRAME[3] - 6.0)
    G.draw_title_block(sh, *tb, fields=dict(subtitle="SECTIONS", dwg="PC12-SEC-002", scale="AS SHOWN",
                                            sheet="A2 · 1 OF 1"))
    probe = G.Sheet()
    nh = draw_notes(probe, tb[0], 0.0, tb[2])
    draw_notes(sh, tb[0], tb[1] - 4.0 - nh, tb[2])
    os.makedirs(G.OUT_DIR, exist_ok=True)
    svg_path = os.path.join(G.OUT_DIR, "pc12_sections.svg")
    pdf_path = os.path.join(G.OUT_DIR, "pc12_sections.pdf")
    with open(svg_path, "w") as f:
        f.write(sh.cv.to_svg(title="PC-12 Sections",
                             desc="PC12-SEC-002 rev A, A2. Reconstruction from published data, not for manufacture.",
                             font_import="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;500;600;"
                                         "700&family=IBM+Plex+Mono:wght@400;500&display=swap"))
    sh.cv.to_pdf(pdf_path, title="PC-12 Sections (PC12-SEC-002 rev A)", author="Claude",
                 subject="Reconstruction from published data - not for manufacture")
    probs = [p for p in check(sh)]
    if verbose:
        print(f"sections sheet: {svg_path} {os.path.getsize(svg_path) / 1e6:.2f} MB, {pdf_path} "
              f"{os.path.getsize(pdf_path) / 1e6:.2f} MB  (root chord {a['chord']*1000:.0f}, t/c {a['t']:.3f}; "
              f"tip chord {b['chord']*1000:.0f}, t/c {b['t']:.3f}; blade stations {len(st)})")
        for p in probs:
            print("  CHECK:", p)
    return sh


def check(sh):
    """Text boxes overlapping each other or leaving the frame."""
    B = [b for b in sh.boxes if b[4] != "zone"]
    x0f, y0f, x1f, y1f = FRAME
    for i, (x0, y0, x1, y1, t) in enumerate(B):
        if x0 < x0f or x1 > x1f or y0 < y0f or y1 > y1f:
            yield f"outside frame: {t} {np.round([x0, y0, x1, y1], 1)}"
        for (a0, b0, a1, b1, u) in B[i + 1:]:
            if x0 < a1 - 0.3 and a0 < x1 - 0.3 and y0 < b1 - 0.3 and b0 < y1 - 0.3 and ("label" in (t, u) or "dim" in (t, u)):
                yield f"overlap: {t} {np.round([x0, y0, x1, y1], 1)} / {u} {np.round([a0, b0, a1, b1], 1)}"


def main():
    build()


if __name__ == "__main__":
    main()
