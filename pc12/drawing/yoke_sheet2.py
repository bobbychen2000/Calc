"""
Sheet L6Y2 -- PC-24-STYLE CONTROL YOKE, SECTIONS & DETAILS (PC12-L6Y2), the companion of L6Y (drawing/yoke_sheet.py),
drawn from model/interior.py YOKE_DESIGN (rev J) through the solids of model/yoke_geom.py: every section is an exact
cut of the solids (contours of the signed-distance fields on the cutting plane), the head / switch views and profiles
come from the table.  Nothing comes from a mesh or a photo; the photo-check numbers are the results of
python3 -m drawing.yoke_overlay (git-ignored overlays in refs/cache/overlays/yoke).

    python3 -m drawing.master L6Y2

  SECTION Z-Z (the yoke centreline u = 0, 2:1): white cover, flush inserts, step V, crown crease and top land, lower
  face, the black body's top falling forward, its foot.  SECTION K-K (across the outboard arm, 2:1): top land, R 1 /
  R 2 edges, the cover on the body.  GRIP SECTIONS A1-A4 (outboard) / N1-N4 (inboard) normal to the grip axis at
  h -30 / -10 / 14 / 40 (2:1): frame, recessed leather, edge radii, depth.  GRIP PROFILES P-P / Q-Q (1:1, the axial
  planes through the grips: pad recess, heel lip, heads) with DETAIL P (heel, 3:1).  HEADS F (the round trim face) /
  G (the shield facet), SWITCHES D (TCS), E (AFCS) with profiles, H (badge), J (column + surround, side and front).
  Tables: corners & radii (the curve law's corner lists), photo check (landmarks, grip silhouettes per row, pads,
  the inboard neck), revisions.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from drawing.yoke_draw import (D, I, G, TXT, TXT_S, WHITE, SILVER, SMOKE, BLACK, BODY, LEATHER, RED, GLOSS,  # noqa
                               SWITCH, HID, W_CREASE, W_TAN, INK, MUTED, PAPER, ACCENT, W_OBJ, W_FINE, W_THIN, CHAIN,
                               PHANTOM, COLLAR, table, view_title, notes, mkview, poly, line, circle, circ, lbl, dim,
                               leader, centre_mark, hatch_poly, break_line, ticks, wrap_rows, rocker_halves, hexagon,
                               views, draw_section, section_contours, PART_STYLE)
from drawing import yoke_sheet as YS  # noqa: E402

SHEET = dict(id="L6Y2", title="CONTROL YOKE - SECTIONS", subtitle="PC-24-STYLE CONTROL YOKE - SECTIONS & DETAILS",
             size="A1", scale="AS SHOWN", rev="A", order=63, sheet_no="2 OF 2", dwg="PC12-L6Y2")
REVISIONS = (
    ("A", "2026-10-05", "first issue with L6Y rev B (judges r1 D1 / D2 / D5 / D10, FID1-04..06 / 09..12): exact "
                        "sections of the rev J solids -- centreline, arm, 8 grip sections, the grips' axial profiles "
                        "with the heel lip; the round trim face and the shield facet; switch profiles; the column "
                        "surround in front view; corner / radius table; photo check per grip row and the inboard "
                        "neck"),
)
COL_X = (588.0, 826.0)
GRIP_SECTION_H = YS.GRIP_SECTION_H

# python3 -m drawing.yoke_overlay (refs/cache/overlays/yoke/deviations.json, 2026-10-05, rev J): per photo -- cover
# landmarks mean / max (the pose fit), heads (trim, button: checked, not fitted), grip silhouette rows outer / slot
# side mean (rms) per grip (+ = drawn wider), pads vs traces mean (max)


# ============================================================================================ views
def make_views(ds):
    v = {}
    v["Z"] = ds.add_view(mkview("sec_Z", "xz", 1, -1, (168.0, 160.0), 2.0, "section Z-Z at u 0 from outboard, (a, h)"))
    v["K"] = ds.add_view(mkview("sec_K", "xz", 1, -1, (186.0, 400.0), 2.0, "section K-K across the outboard arm, "
                                                                          "(a, across)"))
    v["P"] = ds.add_view(mkview("prof_P", "xz", 1, -1, (288.0, 304.0), 1.0, "grip profile P-P (outboard), (aft, axis)"))
    v["Q"] = ds.add_view(mkview("prof_Q", "xz", 1, -1, (352.0, 304.0), 1.0, "grip profile Q-Q (inboard), (aft, axis)"))
    v["Pd"] = ds.add_view(mkview("det_P", "xz", 1, -1, (424.0, 240.0), 3.0, "detail P (heel), (aft, axis) about the "
                                                                           "pad bottom"))
    return v


def draw(ds):
    v = make_views(ds)
    ds.frame_and_title(fields=dict(date="2026-10-05"))
    draw_secZ(ds, v["Z"])
    draw_secK(ds, v["K"])
    draw_grip_sections(ds)
    draw_profiles(ds, v)
    draw_heads(ds)
    draw_switches(ds)
    draw_column(ds)
    draw_tables(ds)


# ============================================================================================ Z-Z
def draw_secZ(ds, v):
    S = G.section((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0, 0.0), (-76.0, -66.0, 12.0, 70.0),
                  parts=("black", "cover"), step=0.2)
    draw_section(ds, v, S, parts=("black", "cover"))
    X0, Y0 = v.pt(0.0, 0.0)
    ds.cv.line(v.pt(-80.0, 0.0), v.pt(16.0, 0.0), W_THIN, CHAIN)
    ds.cv.line(v.pt(0.0, -70.0), v.pt(0.0, 74.0), W_THIN, CHAIN, color=MUTED)
    fl = np.asarray(D["face_lower"], float)
    T = math.tan(math.radians(float(D["face_tilt"])))
    line(ds, v, [(0.0, float(fl[0, 0])), (-(72.0 - float(fl[0, 0])) * T, 72.0)], W_THIN, CHAIN, color=ACCENT)
    # call-outs from the table
    st = np.asarray(D["step"], float)
    il = np.asarray(D["insert_lower_half"], float)
    cr = D["crown"]
    h_top = float(np.asarray(D["shell_half"])[0, 1])
    aF = lambda h: float(G.face_a(h))                                       # noqa: E731
    T_ = X0 + 26.0
    items = [((aF(h_top), h_top - 0.5), (T_, Y0 - 140.0), f"CROWN TOP h {h_top:g}, TOP LAND {float(cr[2]):g} x "
                                                          f"{float(cr[3]):g}", ["chamfer, R 0.5 [M low]"]),
             ((aF(float(cr[0])), float(cr[0])), (T_, Y0 - 122.0), f"CROWN CREASE h {float(cr[0]):g}",
              [f"insert top {float(cr[1]):g}° further forward [M low / E]"]),
             ((aF(49.65), 49.65), (T_, Y0 - 104.0), f"BADGE: GROOVES {float(D['badge_relief'][1]):g} WIDE x "
                                                    f"{float(D['badge_relief'][0]):g}", ["plain field, no lettering"]),
             ((aF(float(st[0, 1])), float(st[0, 1])), (T_, Y0 - 14.0),
              f"STEP V {D['grooves'][1][0]:g} WIDE x {D['grooves'][1][1]:g} DEEP", ["both inserts FLUSH [M]"]),
             ((aF(-10.0), -10.0), (T_, Y0 + 20.0), f"LOWER INSERT TO h {float(il[:, 1].min()):g}",
              [f"edge groove {D['grooves'][2][0]:g} x {D['grooves'][2][1]:g}"]),
             ((aF(-40.0), -40.0), (T_, Y0 + 60.0), "LOWER FACE: C1 HERMITE", ["tangent to the 17.5° plane"]),
             ((aF(-55.5), -55.5), (T_, Y0 + 96.0), f"FOOT UNDERSIDE R {float(D['edges'][2]):g}",
              [f"cover {float(D['cover_t']):g} on the body [E]"]),
]
    for P, Tt, t_, more in items:
        leader(ds, v.pt(*P), Tt, t_, more, size=TXT_S, weight=500)
    for k, t in enumerate((f"BODY: {float(D['body_form'][0]):g} DEEP [E], ITS TOP FALLING {float(D['body_form'][1]):g}° "
                           f"FORWARD FROM THE TOP LINE (h {float(D['body_top'][0][1]):g} AT u 0)",
                           f"forward edges R {float(D['body_form'][4]):g}, foot R {float(D['body_form'][5]):g} [E]; "
                           "black body and grips one moulding")):
        lbl(ds, X0 - 140.0, Y0 + 142.0 + 3.0 * k, t, TXT_S, color=MUTED)
    lbl(ds, *v.pt(-70.0, 74.0), f"AFT FACE {float(D['face_tilt']):g}° TOP FWD", TXT_S, color=ACCENT, weight=600)
    lbl(ds, X0 + 1.0, Y0 + 138.0, "a 0", TXT_S, color=MUTED)
    lbl(ds, *v.pt(-78.0, -2.5), "h 0", TXT_S, color=MUTED)
    view_title(ds, X0 - 50.0, Y0 + 156.0, "SECTION Z-Z", "YOKE CENTRELINE u 0, FROM OUTBOARD, NOSE LEFT - 2:1",
               size=3.4)


# ============================================================================================ K-K
def arm_frame():
    """Section K-K: the plane through the arm point (52, 45) normal to the arm axis (front view 30° up outboard)."""
    ang = math.radians(30.0)
    p = np.array([52.0, 45.0, 0.0])
    e_across = np.array([-math.sin(ang), math.cos(ang), 0.0])            # up-inboard
    return p, e_across


def draw_secK(ds, v):
    p, e1 = arm_frame()
    S = G.section(p, (0.0, 0.0, 1.0), e1, (-80.0, -26.0, 10.0, 26.0), parts=("black", "cover"), step=0.15)
    draw_section(ds, v, S, parts=("black", "cover"))
    X0, Y0 = v.pt(0.0, 0.0)
    cr = D["crown"]
    E = D["edges"]
    # find the cover contour to place the call-outs
    cov = [C for p_, C in section_contours(S, ("cover",))]
    if cov:
        C = cov[0]
        top = C[np.argmax(C[:, 1])]
        bot = C[np.argmin(C[:, 1])]
        leader(ds, v.pt(*top), (X0 + 26.0, Y0 - 40.0), f"TOP LAND {float(cr[2]):g} DEEP x {float(cr[3]):g}",
               ["the arm's top edge (crease)"], size=TXT_S, weight=500)
        leader(ds, v.pt(*bot), (X0 + 26.0, Y0 + 38.0), f"ARM LOWER EDGE R {float(E[1]):g}",
               [f"cover {float(D['cover_t']):g} [E], perimeter R {float(E[0]):g}"], size=TXT_S, weight=500)
    lbl(ds, X0 - 98.0, Y0 - 50.0, "UP-INBOARD", TXT_S, color=MUTED, weight=600)
    lbl(ds, X0 - 98.0, Y0 + 54.0, "FWD <-   -> AFT", TXT_S, color=MUTED)
    view_title(ds, X0 - 40.0, Y0 + 62.0, "SECTION K-K", "ACROSS THE OUTBOARD ARM AT (52, 45), LOOKING INBOARD - 2:1",
               size=3.4)


# ============================================================================================ grip sections
def draw_grip_sections(ds):
    """Grip sections A1-A4 / N1-N4 at 1:1 (normal to the mean axis, looking down it) + DETAIL S (A3's pad edge and
    frame at 5:1)."""
    x_cells = [272.0 + 66.0 * k for k in range(4)]
    for g, Yc, lets, sx in (("out", 62.0, "A", -1.0), ("in", 136.0, "N", 1.0)):
        pg = "grip_" + g
        for k, h in enumerate(GRIP_SECTION_H):
            Xc = x_cells[k]
            vs = ds.add_view(mkview(f"sec_{lets}{k + 1}", "yz", sx, 1, (Xc, Yc), 1.0,
                                    f"grip section {lets}{k + 1} (across, along the aft normal)"))
            S = G.grip_section(g, h, extent=(-42.0, -40.0, 36.0, 10.0), parts=(pg,), step=0.15)
            draw_section(ds, vs, S, parts=(pg,), style={pg: ("#E3E6E8", 45.0, 0.8)})
            C = [c for _, c in section_contours(S, (pg,))]
            if C:
                C = C[0]
                w = float(C[:, 0].max() - C[:, 0].min())
                dpt = float(C[:, 1].max() - C[:, 1].min())
                ds.text(Xc, Yc + 9.0, f"{w:.1f} x {dpt:.1f}", TXT_S, "mono", "middle", tag="dim")
            ds.cv.line((Xc - 28.0, Yc), (Xc + 28.0, Yc), W_THIN, CHAIN, color=MUTED)
            view_title(ds, Xc, Yc + 15.0, f"{lets}{k + 1}-{lets}{k + 1}", f"h {h:g} - 1:1", size=3.0)
        lbl(ds, x_cells[0] - 30.0, Yc - 40.0,
            f"{'OUTBOARD' if g == 'out' else 'INBOARD'} GRIP, NORMAL TO THE AXIS, LOOKING DOWN IT (FWD UP, PAD DOWN; "
            f"{'OUTBOARD LEFT' if g == 'out' else 'INBOARD RIGHT'})", TXT_S, color=MUTED, weight=600)
    ps = D["pad_section"]
    lbl(ds, x_cells[0] - 30.0, 162.0, f"PAD: leather {float(ps[0]):g} below the {float(D['grip_frame']):g} frame, "
                                      f"crowned to {abs(float(ps[1])):g} below over {float(ps[2]):g}; frame edge R "
                                      f"{float(D['grip_edges'][0]):g}, forward R {float(D['grip_edges'][1]):g} [E]; "
                                      "depth: grip_depth", TXT_S, color=MUTED)
    # DETAIL S: A3's outer pad edge / frame at 5:1
    p, e1, e2 = G.grip_section_frame("out", GRIP_SECTION_H[2])
    S = G.grip_section("out", GRIP_SECTION_H[2], extent=(-42.0, -40.0, 36.0, 10.0), parts=("grip_out",), step=0.15)
    C = [c for _, c in section_contours(S, ("grip_out",))]
    if C:
        x_out = float(C[0][:, 0].max())
        Sd = G.section(G.to_cop(p, "out"), G.to_cop(e1, "out"), G.to_cop(e2, "out"),
                       (x_out - 9.0, -7.0, x_out + 1.0, 2.0), parts=("grip_out",), step=0.04, clip=True)
        vd = ds.add_view(mkview("det_S", "yz", -1, 1, (552.0 + 5.0 * (x_out - 4.0), 118.0), 5.0, "detail S"))
        draw_section(ds, vd, Sd, parts=("grip_out",), style={"grip_out": ("#E3E6E8", 45.0, 1.2)})
        X0, Y0 = vd.pt(x_out - 4.0, 0.0)
        fr = float(D["grip_frame"])
        leader(ds, vd.pt(x_out - 0.6, -0.3), (X0 - 26.0, Y0 - 22.0), f"FRAME {fr:g}, EDGE R "
                                                                      f"{float(D['grip_edges'][0]):g}",
               None, size=TXT_S, weight=500)
        leader(ds, vd.pt(x_out - fr - 1.5, float(ps[0]) - 0.2), (X0 - 26.0, Y0 + 20.0),
               f"LEATHER {float(ps[0]):g} BELOW, CROWN", [f"to {abs(float(ps[1])):g} over {float(ps[2]):g}"],
               size=TXT_S, weight=500)
        view_title(ds, X0, Y0 + 30.0, "DETAIL S", "A3 OUTER PAD EDGE - 5:1", size=3.0)


# ============================================================================================ grip profiles P-P / Q-Q
def axial_frame(g):
    p0, t = G.grip_axis_3d(g)
    n = G.grip_frame(g)["n"]
    e2 = n - t * float(np.dot(n, t))
    e2 /= np.linalg.norm(e2)
    return G.to_cop(p0, g), G.to_cop(t, g), G.to_cop(e2, g)


def draw_profiles(ds, v):
    for g, key, let in (("out", "P", "P"), ("in", "Q", "Q")):
        p0, t, e2 = axial_frame(g)
        # section coords (s1 = aft along e2, s2 = up the axis)
        S = G.section(p0, e2, t, (-38.0, -56.0, 10.0, 108.0), parts=("black",), step=0.2)
        vv = v[key]
        draw_section(ds, vv, S, parts=("black",))
        X0, Y0 = vv.pt(0.0, 0.0)
        ds.cv.line(vv.pt(0.0, -60.0), vv.pt(0.0, 112.0), W_THIN, CHAIN, color=MUTED)
        view_title(ds, X0 - 10.0, Y0 + 66.0, f"{let}-{let}", ("OUTBOARD" if g == "out" else "INBOARD") +
                   " GRIP - 1:1", size=3.0)
    vP = v["P"]
    leader(ds, vP.pt(2.0, 75.0), (vP.pt(0, 0)[0] + 24.0, vP.pt(0, 75.0)[1] - 30.0),
           f"TRIM FACE {float(D['head_out'][3]):g}° UP", [f"lower edge chamfer {float(D['head_chamfer']):g}°"],
           size=TXT_S, weight=500)
    leader(ds, vP.pt(-0.5, 20.0), (vP.pt(0, 0)[0] + 24.0, vP.pt(0, 20.0)[1]), "PAD RECESS", ["in the frame"],
           size=TXT_S, weight=500)
    vQ = v["Q"]
    leader(ds, vQ.pt(1.0, 80.0), (vQ.pt(0, 0)[0] + 24.0, vQ.pt(0, 80.0)[1] - 34.0),
           f"SHIELD FACET {float(D['head_in'][2]):g}° UP", [f"head falls {float(D['head_in'][4]):g}° round it"],
           size=TXT_S, weight=500)
    lbl(ds, vP.pt(-38.0, 112.0)[0], vP.pt(0, 112.0)[1] - 2.0, "AXIAL PLANES (AXIS + AFT NORMAL), FWD LEFT", TXT_S,
        color=MUTED, weight=600)
    # DETAIL P: the heel of the outboard grip at 3:1, about the axis point at the pad's bottom
    p0, t, e2 = axial_frame("out")
    pb = float(G.pad_outline("out")[:, 1].min())
    pc = p0 + t * (pb - p0[1]) / t[1]
    vd = v["Pd"]
    S = G.section(pc, e2, t, (-14.0, -20.0, 8.0, 12.0), parts=("black",), step=0.08, clip=True)
    draw_section(ds, vd, S, parts=("black",))
    X0, Y0 = vd.pt(0.0, 0.0)
    hl = D["heel"]
    ps = D["pad_section"]
    leader(ds, vd.pt(float(hl[1]) - 0.3, -5.0), (X0 + 30.0, Y0 + 18.0), f"HEEL LIP {float(hl[1]):g} PROUD, R "
                                                                        f"{float(hl[2]):g}",
           [f"{float(hl[0]):g} tall under the pad"], size=TXT_S, weight=500)
    leader(ds, vd.pt(-float(ps[0]) + 0.3, 4.0), (X0 + 30.0, Y0 - 16.0), f"LEATHER {float(ps[0]):g} BELOW THE FRAME",
           [f"crowned to {abs(float(ps[1])):g} below, bead {float(ps[3]):g}"], size=TXT_S, weight=500)
    view_title(ds, X0 - 6.0, Y0 + 70.0, "DETAIL P - HEEL", "OUTBOARD GRIP, ON P-P, AFT RIGHT - 3:1", size=3.0)


# ============================================================================================ heads
def draw_heads(ds):
    # F: view normal to the round trim face (2:1)
    vF = ds.add_view(mkview("det_F", "yz_aft", -1, -1, (506.0, 236.0), 2.0, "detail F (trim face), face plane mm"))
    R = 0.5 * float(D["head_out"][2])
    od = float(D["trim"][2])
    lune, r0, r1, sexp = (float(x) for x in D["trim_lunes"])
    c = np.zeros(2)
    circ(ds, vF, c, 2 * R, W_OBJ, fill="#2B3135")
    circ(ds, vF, c, 2 * (R + 3.0), W_THIN, dash=HID, color=MUTED)
    circ(ds, vF, c, od, W_FINE, fill="#23292D", color="#C9CFD3")
    for s_ in (-1, 1):
        line(ds, vF, [(-0.5 * od + 2.0, s_ * (0.5 * od - lune)), (0.5 * od - 2.0, s_ * (0.5 * od - lune))], W_THIN,
             color="#9AA3A9")
    lg = D["legends"][2]
    for a0, a1 in ((lg[2], lg[3]), (lg[2] + 180.0, lg[3] + 180.0)):
        for T in ticks(c, r0, r1, a0, a1, int(lg[4])):
            line(ds, vF, T, 0.3, color="#E8EAEC")
    for half in rocker_halves():
        poly(ds, vF, half, W_FINE, fill=SWITCH, color="#C9CFD3")
    centre_mark(ds, vF, c, R)
    X0, Y0 = vF.pt(0, 0)
    dim(ds, vF.pt(R, 0), vF.pt(-R, 0), Y0 + 2 * R + 6.0, f"{2 * R:.1f} FACE")
    dim(ds, vF.pt(0.5 * od, 0), vF.pt(-0.5 * od, 0), Y0 - 2 * R - 5.0, f"{od:.1f} RING")
    tr = D["trim"]
    leader(ds, vF.pt(10.0, 1.0), (X0 + 42.0, Y0 - 10.0), f"ROCKER {float(tr[3]):g} x {float(tr[4]):g}",
           [f"waist {float(tr[5]):g}, split {float(tr[6]):g}", "two mirrored lobes"], size=TXT_S, weight=500)
    leader(ds, vF.pt(0.0, 11.5), (X0 + 42.0, Y0 - 30.0), "DN LUNE (FWD)", [f"{int(lg[4])} ticks / 84°"], size=TXT_S,
           weight=500)
    leader(ds, vF.pt(0.0, -11.5), (X0 + 42.0, Y0 + 18.0), "UP LUNE (AFT)", [f"{int(lg[4])} ticks"], size=TXT_S,
           weight=500)
    lbl(ds, X0 - 44.0, Y0 + 2 * R + 13.0, f"dashed: the head under the face (R {R:g}, flare "
                                          f"{float(D['head_out'][5]):g}°)", TXT_S, color=MUTED)
    # rocker saddle profile
    vR = ds.add_view(mkview("det_F2", "xz", 1, -1, (506.0, 300.0), 2.0, "detail F rocker profile"))
    L = float(tr[3])
    xs = np.linspace(-0.5 * L, 0.5 * L, 41)
    he, hm = float(tr[7]), float(tr[8])
    prof = hm + (he - hm) * (np.abs(xs) / (0.5 * L)) ** sexp
    split = float(tr[6])
    for sg in (-1, 1):
        sel = sg * xs >= 0.5 * split
        P = np.vstack([[(sg * 0.5 * split, 0.0)], np.c_[xs[sel], prof[sel]][::sg], [(sg * 0.5 * L, 0.0)]])
        poly(ds, vR, P, W_FINE, fill=SWITCH)
    line(ds, vR, [(-0.5 * od, 0.0), (0.5 * od, 0.0)], W_OBJ)
    X1, Y1 = vR.pt(0, 0)
    dim(ds, vR.pt(0.5 * L, he), vR.pt(0.5 * L, 0.0), X1 + L + 7.0, f"{he:g}", orient="v")
    dim(ds, vR.pt(0.0, hm), vR.pt(0.0, 0.0), X1 - L - 9.0, f"{hm:g}", orient="v", outside=True)
    lbl(ds, X1, Y1 + 4.5, f"SADDLE (EXPONENT {sexp:g}) [E +/-2], RING FLUSH", TXT_S, "middle")
    view_title(ds, X0, Y1 + 12.0, "DETAIL F - TRIM HEAD", f"VIEW NORMAL TO THE ROUND FACE "
                                                          f"({float(D['head_out'][3]):g}° UP) - 2:1", size=3.0)
    # G: view normal to the shield facet (2:1) + the button profile
    vG = ds.add_view(mkview("det_G", "yz_aft", 1, -1, (506.0, 362.0), 2.0, "detail G (shield), facet plane mm"))
    S2 = G.shield_outline()
    poly(ds, vG, S2, W_OBJ, fill="#2F363A")
    bp = YS.button_pieces()
    c2 = bp["centre2"]
    b = D["button"]
    poly(ds, vG, hexagon(float(b[2])) + c2, W_FINE, fill="#23292D", color="#C9CFD3")
    circ(ds, vG, c2, float(b[3]), W_FINE, fill="#3A4247", color="#C9CFD3")
    circ(ds, vG, c2, float(b[5]), W_THIN, color="#C9CFD3")
    lg = D["legends"][3]
    for T in ticks(c2, lg[0], lg[1], 180.0 - lg[3], 180.0 - lg[2], int(lg[4])):
        line(ds, vG, T, 0.3, color="#E8EAEC")
    X0, Y0 = vG.pt(*c2)
    sc = np.asarray(D["shield"], float)
    dim(ds, vG.pt(sc[0, 0], sc[0, 1]), vG.pt(sc[1, 0], sc[1, 1]), vG.pt(0, sc[0, 1])[1] - 6.0,
        f"{sc[1, 0] - sc[0, 0]:.0f} SHIELD")
    leader(ds, vG.pt(c2[0] + 6.0, c2[1] - 6.0), (X0 + 40.0, Y0 + 14.0), f"HEX COLLAR {float(b[2]):g} / "
                                                                        f"{float(b[6]):g} A/F",
           [f"cap {float(b[3]):g}, {float(b[4]):g} proud, dimple {float(b[5]):g}"], size=TXT_S, weight=500)
    leader(ds, vG.pt(c2[0] - 7.0, c2[1] + 7.5), (X0 + 40.0, Y0 - 16.0), f"{int(lg[4])} TICKS ON THE UPPER /",
           [f"INBOARD ARC {lg[2]:g}-{lg[3]:g}° (no lettering)"], size=TXT_S, weight=500)
    lbl(ds, X0 - 40.0, Y0 + 24.0, "INBOARD -> RIGHT (pilot); facet "
                                  f"{float(D['head_in'][2]):g}° up, toe {float(D['head_in'][3]):g}°", TXT_S,
        color=MUTED)
    view_title(ds, X0, Y0 + 32.0, "DETAIL G - INBOARD HEAD", "VIEW NORMAL TO THE SHIELD FACET - 2:1", size=3.0)
    # the push button in section (along the facet normal), 3:1
    vB = ds.add_view(mkview("det_G2", "xz", 1, -1, (432.0, 418.0), 3.0, "detail G button profile"))
    af, cd_, ch_, dimple = float(b[6]), float(b[3]), float(b[4]), float(b[5])
    col_h = 2.0
    poly(ds, vB, [(-0.5 * af, 0.0), (-0.5 * af, col_h), (0.5 * af, col_h), (0.5 * af, 0.0)], W_FINE, fill="#23292D")
    cap = np.array([(-0.5 * cd_, col_h), (-0.5 * cd_, col_h + ch_ - 1.0), (-0.5 * cd_ + 1.0, col_h + ch_),
                    (-0.5 * dimple, col_h + ch_), (0.0, col_h + ch_ - 0.4), (0.5 * dimple, col_h + ch_),
                    (0.5 * cd_ - 1.0, col_h + ch_), (0.5 * cd_, col_h + ch_ - 1.0), (0.5 * cd_, col_h)])
    poly(ds, vB, cap, W_FINE, fill="#3A4247")
    line(ds, vB, [(-11.0, 0.0), (11.0, 0.0)], W_THIN, color=MUTED)
    X2, Y2 = vB.pt(0, 0)
    dim(ds, vB.pt(0.5 * cd_, col_h + ch_), vB.pt(0.5 * cd_, col_h), X2 + 22.0, f"{ch_:g}", orient="v")
    dim(ds, vB.pt(-0.5 * af, col_h), vB.pt(-0.5 * af, 0.0), X2 - 24.0, f"{col_h:g}", orient="v", outside=True)
    lbl(ds, X2, Y2 + 5.0, f"HEX {af:g} A/F, CAP {cd_:g}, R 1, DIMPLE {dimple:g}", TXT_S, "middle")
    lbl(ds, X2, Y2 + 8.0, "PROFILE ON THE FACET NORMAL - 3:1", TXT_S, "middle", color=MUTED)


# ============================================================================================ switches
def draw_switches(ds):
    # ---- D: TCS (3:1) face + profile
    u, h, od, bd, _ = (float(x) for x in D["tcs"][:5])
    pr = D["tcs_profile"]
    vD = ds.add_view(mkview("det_D", "yz_aft", -1, -1, (300.0, 456.0), 3.0, "detail D (TCS), mm about its centre"))
    YS.draw_tcs(ds, vD, 1.4, c=(0.0, 0.0))
    centre_mark(ds, vD, (0.0, 0.0), 0.5 * od)
    X0, Y0 = vD.pt(0, 0)
    dim(ds, vD.pt(0.5 * od, 0), vD.pt(-0.5 * od, 0), Y0 - 1.5 * od - 5.0, f"{od:g} BEZEL")
    vD2 = ds.add_view(mkview("det_D2", "xz", 1, -1, (300.0, 510.0), 3.0, "detail D profile"))
    bz_h, rr, dish, dome, below, r_in, r_out = (float(x) for x in pr[:7])
    top = bz_h
    prof = np.array([(-0.5 * od - rr * 0.6, 0.0), (-0.5 * od, top - 0.4), (-0.5 * od + 0.6, top), (-r_out, top),
                     (-r_in, top - dish), (r_in, top - dish), (r_out, top), (0.5 * od - 0.6, top),
                     (0.5 * od, top - 0.4), (0.5 * od + rr * 0.6, 0.0)])
    poly(ds, vD2, np.vstack([prof, [(0.5 * od + rr * 0.6, -1.5), (-0.5 * od - rr * 0.6, -1.5)]]), W_FINE, fill=GLOSS)
    xb = np.linspace(-0.5 * bd, 0.5 * bd, 25)
    btop = top - below
    poly(ds, vD2, np.vstack([np.c_[xb, btop - dome * (2 * xb / bd) ** 2], [(0.5 * bd, btop - dome - 1.0),
                                                                          (-0.5 * bd, btop - dome - 1.0)]]),
         W_FINE, fill=SWITCH)
    line(ds, vD2, [(-16.0, 0.0), (16.0, 0.0)], W_THIN, color=MUTED)
    X1, Y1_ = vD2.pt(0, 0)
    dim(ds, vD2.pt(0.5 * od, top), vD2.pt(0.5 * od, 0.0), X1 + 1.5 * od + 9.0, f"{bz_h:g}", orient="v", outside=True)
    lbl(ds, X1, Y1_ + 9.0, f"bezel {bz_h:g} proud R {rr:g}, dish r {r_in:g}-{r_out:g} {dish:g} deep, button dome "
                           f"{dome:g}, top {below:g} below the bezel [E]", TXT_S, "middle")
    view_title(ds, X1, Y1_ + 15.0, "DETAIL D - TCS", f"u {u:g} h {h:g} ON THE WHITE ARM - 3:1", size=3.0)
    # ---- E: AFCS (3:1)
    u, h, cd, ch, bdo = (float(x) for x in D["afcs"][:5])
    vE = ds.add_view(mkview("det_E", "yz_aft", -1, -1, (410.0, 456.0), 3.0, "detail E (AFCS), mm"))
    YS.draw_afcs(ds, vE, 1.4, c=(0.0, 0.0))
    centre_mark(ds, vE, (0.0, 0.0), 0.5 * bdo)
    X0, Y0 = vE.pt(0, 0)
    dim(ds, vE.pt(0.5 * bdo, 0), vE.pt(-0.5 * bdo, 0), Y0 - 1.5 * bdo - 5.0, f"{bdo:g} BOSS")
    vE2 = ds.add_view(mkview("det_E2", "xz", 1, -1, (410.0, 516.0), 3.0, "detail E profile"))
    poly(ds, vE2, [(-0.5 * bdo, 0.0), (-0.5 * bdo + 0.8, 1.5), (0.5 * bdo - 0.8, 1.5), (0.5 * bdo, 0.0)], W_FINE,
         fill=GLOSS)
    cap = np.array([(-0.5 * cd, 1.5), (-0.5 * cd, 1.5 + ch - 1.0), (-0.5 * cd + 1.0, 1.5 + ch), (0.5 * cd - 1.0, 1.5 + ch),
                    (0.5 * cd, 1.5 + ch - 1.0), (0.5 * cd, 1.5)])
    poly(ds, vE2, cap, W_FINE, fill=RED)
    line(ds, vE2, [(-14.0, 0.0), (14.0, 0.0)], W_THIN, color=MUTED)
    X1, Y1_ = vE2.pt(0, 0)
    dim(ds, vE2.pt(0.5 * cd, 1.5 + ch), vE2.pt(0.5 * cd, 1.5), X1 + 1.5 * bdo + 6.0, f"{ch:g}", orient="v")
    dim(ds, vE2.pt(-0.5 * cd, 1.5 + ch), vE2.pt(0.5 * cd, 1.5 + ch), Y1_ - 3 * (1.5 + ch) - 4.0, f"{cd:g} CAP")
    lbl(ds, X1, Y1_ + 6.0, "boss 1.5 proud [E] on the black body's lower edge; cap top R 1", TXT_S, "middle")
    view_title(ds, X1, Y1_ + 12.0, "DETAIL E - AFCS DISCONNECT", f"u {u:g} h {h:g}; ROUND BOSS, LEGEND ON ITS UPPER "
                                                                 "HALF - 3:1", size=3.0)
    # ---- H: badge (2:1)
    vH = ds.add_view(mkview("det_H", "yz_aft", -1, -1, (510.0, 450.0), 2.0, "detail H (badge), mm about h 49.65"))
    F = I.yoke_front_mm()
    hc = 49.65
    sub = np.array([0.0, hc])
    poly(ds, vH, F["badge"] - sub, W_OBJ, fill=SILVER)
    poly(ds, vH, F["badge_border"] - sub, W_FINE)
    for Ln in F["badge_lines"]:
        line(ds, vH, Ln - sub, W_FINE)
    poly(ds, vH, F["badge_field"] - sub, W_THIN, dash=(1.0, 0.8), color=MUTED)
    X0, Y0 = vH.pt(0, 0)
    (bu0, bh0), (bu1, bh1) = D["badge"]
    dim(ds, vH.pt(bu0, bh0 - hc), vH.pt(-bu0, bh0 - hc), Y0 - 12.0, f"{2 * bu0:.1f}")
    dim(ds, vH.pt(bu1, bh1 - hc), vH.pt(-bu1, bh1 - hc), Y0 + 12.0, f"{2 * bu1:.1f}")
    dim(ds, vH.pt(-bu0, bh0 - hc), vH.pt(-bu1, bh1 - hc), X0 + 52.0, f"{bh0 - bh1:.1f}", orient="v", outside=True)
    lbl(ds, X0, Y0 + 20.0, "PLAIN FIELD (NO LETTERING); 3 SPEED-LINE GROOVES EACH WING", TXT_S, "middle")
    view_title(ds, X0, Y0 + 28.0, "DETAIL H - BADGE", f"ABSTRACT WINGED PLATE, TOP AT h {bh0:g} - 2:1", size=3.0)


# ============================================================================================ column J
def draw_column(ds):
    """DETAIL J (1:2): the column and the lower panel -- side view (the yoke at neutral, phantom at full push) and the
    FRONT view of the surround: the J band (vertical leg inboard, curving under the stem), the joint line, the screw,
    the dished round recess (judges FID1-10)."""
    vJ = ds.add_view(mkview("det_J", "xz", 1, -1, (672.0, 390.0), 0.5, "detail J side, (a, h) mm"))
    hs = np.linspace(-100.0, 80.0, 30)
    ap = Y1_a_panel(hs)
    poly(ds, vJ, np.vstack([np.c_[ap, hs], [(ap[-1] - 30.0, hs[-1]), (ap[0] - 30.0, hs[0])]]), W_FINE, fill="#E7E9EB")
    a_p0 = float(Y1_a_panel(0.0)[0])
    r = 1000.0 * float(I.YOKE["column_r"])
    depth = float(D["body_form"][0])
    poly(ds, vJ, [(a_p0 - 25.0, r), (-depth + 4.0, r), (-depth + 4.0, -r), (a_p0 - 25.0, -r)], W_FINE, fill="#D9DCDF")
    t0, _ = (1000.0 * float(x) for x in I.YOKE["travel"])
    S = views("u")
    for p_, fill in (("black", None),):
        pass
    for p_, fill in (("body", BODY), ("cover", WHITE), ("grip_out", BLACK)):
        for C in S[p_]:
            if len(C) > 8:
                poly(ds, vJ, C, W_FINE, fill=fill)
                poly(ds, vJ, C + [t0, 0.0], W_THIN, dash=PHANTOM, color=MUTED)
    col = D["column"]
    hub = I.yoke_hub(-1)
    h_top, h_joint, h_screw = ((float(col[i]) - float(hub[2])) * 1000.0 for i in (1, 2, 3))
    for h_ in (h_top, h_joint, h_screw):
        X, Y = vJ.pt(float(Y1_a_panel(h_)[0]), h_)
        ds.cv.line((X - 1.8, Y), (X + 1.8, Y), 0.35, color=ACCENT)
    X0, Y0 = vJ.pt(0, 0)
    dim(ds, vJ.pt(a_p0, -r), vJ.pt(-depth, -r), Y0 + 22.0, f"{-depth - a_p0:.0f}")
    lbl(ds, X0 - 70.0, Y0 + 30.0, f"PHANTOM: FULL PUSH {t0:+.0f} [E], leaves {-depth + t0 - a_p0:.0f} to the panel",
        TXT_S)
    view_title(ds, X0 - 30.0, Y0 + 38.0, "DETAIL J - COLUMN, SIDE", "AT THE LOWER PANEL, FROM OUTBOARD - 1:2", size=3.0)
    # front view of the surround on the panel (pilot: inboard = right)
    vF = ds.add_view(mkview("det_J2", "yz_aft", -1, -1, (756.0, 384.0), 0.5, "detail J front, (u, h) mm"))
    bw = float(col[4])
    u_in = -(float(col[0]) * 1000.0 - float(I.YOKE["bl"]) * 1000.0)       # inboard side of the band, u (negative)
    rc = abs(u_in) - 0.5 * bw                                              # band centreline radius about the axis
    hc_, R_rec, dep = (float(x) for x in D["column_recess"])
    circ(ds, vF, (0.0, hc_), 2 * R_rec, W_FINE, fill="#E3E6E8")
    # band: vertical leg (inboard) from the top end down to the joint, then an arc about (0, hc_) under the stem
    leg = np.array([(-rc, h_top - 0.5 * bw), (-rc, hc_)])
    th = np.radians(np.linspace(180.0, 330.0, 40))
    arc = np.c_[rc * np.cos(th), hc_ + rc * np.sin(th)]
    cl = np.vstack([leg, arc[1:]])
    t_ = np.gradient(cl, axis=0)
    n_ = np.c_[-t_[:, 1], t_[:, 0]] / np.linalg.norm(t_, axis=1)[:, None]
    band = np.vstack([cl + 0.5 * bw * n_, (cl - 0.5 * bw * n_)[::-1]])
    poly(ds, vF, band, W_FINE, fill=COLLAR)
    circ(ds, vF, (-rc, h_top - 0.5 * bw), bw, W_FINE, fill=COLLAR)
    line(ds, vF, [(-rc - 0.5 * bw, h_joint), (-rc + 0.5 * bw, h_joint)], W_FINE, color=INK)
    hs_ = h_screw
    us_ = -math.sqrt(max(rc * rc - (hs_ - hc_) ** 2, 0.0))
    circ(ds, vF, (us_, hs_), 5.0, W_THIN, fill="#9AA1A9")
    circ(ds, vF, (0.0, 0.0), 44.0, W_THIN, dash=HID, color=MUTED)
    poly(ds, vF, G.shell_outline(), W_THIN, dash=PHANTOM, color=MUTED)
    X0, Y0 = vF.pt(0, 0)
    leader(ds, vF.pt(-rc, h_top - 0.5 * bw), (X0 + 26.0, Y0 - 42.0), f"J BAND {bw:g} WIDE [M]",
           [f"inboard leg |BL| {float(col[0]) * 1000:.0f}, top WL {float(col[1]) * 1000:.0f}"], size=TXT_S,
           weight=500)
    leader(ds, vF.pt(-rc + 0.5 * bw, h_joint), (X0 + 26.0, Y0 - 28.0), f"JOINT WL {float(col[2]) * 1000:.0f} [M]",
           [f"screw WL {float(col[3]) * 1000:.0f} [M]"], size=TXT_S, weight=500)
    leader(ds, vF.pt(-R_rec * 0.7, hc_ - R_rec * 0.7), (X0 + 26.0, Y0 + 30.0), f"DISHED RECESS R {R_rec:g}, "
                                                                              f"{dep:g} DEEP [E]",
           ["the band's arc curves under the stem [E]"], size=TXT_S, weight=500)
    lbl(ds, X0 - 40.0, Y0 + 50.0, "phantom: the shell; hidden: the column dia 44", TXT_S, color=MUTED)
    view_title(ds, X0, Y0 + 58.0, "DETAIL J - SURROUND, FRONT", "LOOKING FORWARD (PILOT; INBOARD RIGHT) - 1:2",
               size=3.0)


def Y1_a_panel(h):
    from model import flightdeck as FD
    hub = I.yoke_hub(-1)
    xr = float(hub[0] + I.YOKE["hub_whd"][2])
    return np.array([(FD.face_x(float(hub[1]), float(hub[2]) + hh * 1e-3) - xr) * 1000.0 for hh in np.atleast_1d(h)])


# ============================================================================================ tables
CORNER_KEYS = (("shell_half", "shell (white cover), half"), ("insert_lower_half", "lower insert, half"),
               ("grip_out", "outboard grip aft face"), ("grip_in", "inboard grip aft face"),
               ("pad_out", "outboard pad"), ("pad_in", "inboard pad"), ("shield", "shield facet"))


def draw_tables(ds):
    x0, x1 = COL_X
    W = x1 - x0
    size = 2.1
    # ---- photo check (results of drawing.yoke_overlay; literal, dated)
    cols = [("PHOTO (CAMERA)", 44.0, "l"), ("COVER LM", 22.0, "c"), ("HEADS", 22.0, "c"),
            ("GRIP OUT: OUTER / SLOT", 52.0, "c"), ("GRIP IN: OUTER / SLOT", 52.0, "c"), ("PADS", W - 192.0, "c")]
    rows = [tuple(r) for r in PHOTO_TABLE]
    y = table(ds, x0, 15.0, cols, wrap_rows(rows, [c[1] for c in cols], size),
              title="PHOTO CHECK: THE DRAWN SOLIDS RAY-CAST THROUGH THE PHOTO CAMERAS (mm)", size=size, row_h=3.3,
              font="label")
    from drawing import sheet as S_
    for txt, col in ((NECK, INK), (PHOTO_NOTE, MUTED)):
        L = S_.wrap(txt, W, TXT_S)
        for k, t in enumerate(L):
            ds.text(x0, y + 3.0 + 2.8 * k, t, TXT_S, "label", "start", fill=col, tag="lbl", vcenter=True)
        y += 2.8 * len(L) + 1.0
    y += 3.0
    # ---- corners & radii
    rows = []
    for key, nm in CORNER_KEYS:
        P = np.asarray(D[key], float)
        cs = D.get(key + "_corners", ())
        txt = "; ".join(f"#{int(i)} ({P[int(i), 0]:g}, {P[int(i), 1]:g}) R {r:g}" for i, r in cs)
        rows.append((nm, f"{len(P)}", txt))
    E = D["edges"]
    rows += [("insert corners", "-", "; ".join(f"{k} R {v:g}" for k, v in D["insert_corners"])),
             ("cover edges", "-", f"perimeter R {float(E[0]):g}; arm lower R {float(E[1]):g}; foot underside R "
                                  f"{float(E[2]):g}; tip facet corners R {float(E[3]):g}"),
             ("grip edges", "-", f"frame R {float(D['grip_edges'][0]):g}; forward R {float(D['grip_edges'][1]):g} "
                                 f"[E]; heel lip R {float(D['heel'][2]):g}; trim face R {float(D['head_out'][6]):g}"),
             ("body edges", "-", f"aft R {float(D['body_form'][3]):g}; forward R {float(D['body_form'][4]):g} [E]; "
                                 f"foot R {float(D['body_form'][5]):g} [E]; neck-to-head blend R "
                                 f"{float(D['neck'][3]):g}")]
    cols2 = [("OUTLINE", 46.0, "l"), ("N", 9.0, "c"), ("CORNERS: SAMPLE #, (u, h), RADIUS (curve_law)", W - 55.0, "l")]
    y = table(ds, x0, y + 1.0, cols2, wrap_rows(rows, [c[1] for c in cols2], size),
              title="CORNERS & RADII (every other sample is on a C1 spline)", size=size, row_h=3.3, font="label")
    nts = ["CURVE LAW: centripetal Catmull-Rom (alpha 0.5) through the table samples, 0.25 sampling; corners as "
           "listed (R 0 sharp, R > 0 tangent fillet); YOKE_DESIGN curve_law.",
           "SECTIONS: exact contours of the solids (model/yoke_geom.py) on the cutting planes; the black body and the "
           "grips are one moulding (smooth union R 3), the white cover a separate part; hatching per part.",
           "Sources per value: the [M] / [E] / [S] tags of YOKE_DESIGN (printed in model/interior.py)."]
    notes(ds, x0, y + 1.0, x1, nts, title="NOTES", size=size, line_h=2.9)
    from drawing.interior_sheet import revisions_block
    import drawing.interior_sheet as IS
    saved = IS.SHEET
    IS.SHEET = SHEET
    try:
        revisions_block(ds, x0, 470.0, x1, size=2.1, title_size=2.4, rows=REVISIONS)
    finally:
        IS.SHEET = saved


# rev J photo check, python3 -m drawing.yoke_overlay 2026-10-05 (deviations.json): cover landmarks mean / max, heads
# (trim / button cap, NOT fitted), grip silhouette rows mean (rms) per side (+ = drawn wider), pads mean (max)
PHOTO_TABLE = (
    ('P1046408 pilot (panel_408)', '1.5 / 3.0', '1.2 / 1.8', '+0.1 (2.4) / +1.5 (2.7)', '-0.4 (2.4) / -2.6 (3.8)', 'out 1.0 (2.7); in 0.5 (1.3)'),
    ('P1046408 co-pilot (panel_408)', '1.7 / 4.3', '2.3 / 0.8', '-1.1 (3.5) / +1.3 (2.6)', '-0.2 (2.0) / -0.3 (1.6)', 'out 1.1 (2.6); in 0.5 (1.1)'),
    ('Mexico press, pilot', '1.9 / 3.9', '1.7 / 1.7', '- / -', '-2.5 (3.2) / +1.6 (1.6)', 'in 2.2 (5.6)'),
    ('Mexico press, co-pilot', '2.0 / 3.1', '1.4 / 1.3', '+0.6 (2.7) / +3.1 (3.4)', '+1.2 (1.7) / -3.2 (3.8)', '-'),
    ('AOPA press, pilot (from outboard)', '1.8 / 3.5', '2.5 / 0.5', '+5.0 (5.7) / +1.1 (5.5)', '+3.4 (4.4) / -1.5 (4.8)', 'out 5.8 (16.2); in 2.9 (9.0)'),
    ('P1046410 pilot', '0.8 / 2.1', '5.0 / 1.8', '+0.7 (2.5) / +0.7 (1.8)', '-0.2 (2.3) / -1.3 (3.7)', '-'),
    ('rev I, P1046408 L (judges r1)', '2.0 / 4.0', '-', 'rows 65-85 %: +9 / +12', 'slot: -6..-8', 'in 6.6 (11.0)'),
)
NECK = ("INBOARD NECK (criterion, P1046408): the drawn moulding's top edge vs the photo per pixel column, arm tip "
        "to head -- pilot mean +0.2, |mean| 2.4, max +7.0 mm (against the red placard; rev I 'neck in' 14.2 / 20.7); "
        "co-pilot -4.4 / max -7.5 (drawn LOW near the head; against the dark PFD, low contrast; pose roll -1.3 deg)")
PHOTO_NOTE = ("Pose per photo fitted to the COVER landmarks only (TCS, AFCS, badge, step ends, lower insert, foot); "
              "heads, grips, pads and the neck are checks.  Grip rows: the photo's silhouette edge per image row vs "
              "the ray-cast drawing, outer side h -38..68, slot side h -38..14, mean (rms).  Neck (P1046408): the "
              "inboard neck's top edge per pixel column, arm tip to head.  Overlays: refs/cache/overlays/yoke "
              "(private).")
