"""
Sheet L6Y2 -- PC-24-STYLE CONTROL YOKE, SECTIONS & DETAILS (PC12-L6Y2), the companion of L6Y (drawing/yoke_sheet.py),
drawn from model/interior.py YOKE_DESIGN (rev K) through the solids of model/yoke_geom.py: every section is an exact
cut of the solids (contours of the signed-distance fields on the cutting plane), the head / switch views and profiles
come from the table.  Nothing comes from a mesh or a photo; the photo-check numbers are the results of
python3 -m drawing.yoke_overlay (git-ignored overlays in refs/cache/overlays/yoke).

    python3 -m drawing.master L6Y2

  SECTION Z-Z (the yoke centreline u = 0, 2:1): white cover, flush inserts, step V, crown crease and top land, lower
  face, the black body's top falling forward, its foot.  SECTION K-K (across the outboard arm, 2:1): top land, R 1 /
  R 2 edges, the cover on the body.  GRIP SECTIONS A1-A4 (outboard) / N1-N4 (inboard) normal to the grip axis at
  h -30 / -10 / 14 / 40 (2:1): frame, recessed leather, edge radii, depth.  GRIP PROFILES P-P / Q-Q (1:1, the axial
  planes through the grips: pad recess, heel lip, heads) with DETAIL L (the heel lip, 3:1).  HEADS F (the round trim face) /
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
                               views, draw_section, section_contours, PART_STYLE, legend_quads, LEGEND, SLOT, NICKEL)
from drawing import yoke_sheet as YS  # noqa: E402
from drawing import master as M  # noqa: E402

SHEET = dict(id="L6Y2", title="CONTROL YOKE - SECTIONS", subtitle="PC-24-STYLE CONTROL YOKE - SECTIONS & DETAILS",
             size="A1", scale="AS SHOWN", rev="G", order=63, sheet_no="2 OF 2", dwg="PC12-L6Y2")
REVISIONS = (
    ("A", "2026-10-05", "first issue with L6Y rev B (judges r1): exact sections of the rev J solids, grip profiles with "
                        "the heel lip, trim face / shield, switch profiles, column surround, corner table, photo check"),
    ("B", "2026-10-05", "rev K (judges r2): exact-field solids; Z-Z / K-K with ordinates; cusp-free grip sections; pad "
                        "groove + bead, heel lip R 4; D / E / G exact switch cuts; J-J; acceptance; photo check on "
                        "curated silhouettes, grip planes fitted to 7 views"),
    ("C", "2026-10-05", "rev L (judges r3): K-K through TCS / AFCS; grip sections cut the moulding; dimensions off the "
                        "solids; head-zone surfaces and rounds tabled; acceptance on heads / necks / web / tops / "
                        "forward faces + one-piece and C2 rows; photo check on 6 views; detail J U recess"),
    ("D", "2026-10-05", "rev M (judges r4): pads exposed as drawn (pocket cut after the join); rolling-ball R 3 joins; "
                        "head zones share walls / forward face; leather hatched apart; detail S, break lines, detail W "
                        "[E] switches; adaptive crease / ridge / pad acceptance, all clean (head top R 3 onto the "
                        "forward face, body sides x top rolling ball, C2 forward-radius cap, tangent inboard "
                        "directrix, 0.05 sampling, C2 fields); photo check re-run"),
    ("E", "2026-10-11", "rev N (3-D judges r1): F rocker slot 2.5 deep (draft 7 deg), letter-block legends in the "
                        "pilot's reading order; G MAP LIGHTS blocks, satin-nickel collar; H raised blank plate; J recess "
                        "to h 27, band 22 wide; OWNER DECISIONS 2026-10-11: J band + recess re-centred on the column axis "
                        "(hub WL 1845; photos 1821), push 65 (was 90 [E])"),
    ("F", "2026-10-11", "rev O (3-D judges r2): G push button = gloss-black legend disc 17.5 + nickel hex 12 A/C + cap "
                        "10.2, MAP LIGHTS on the disc; F rocker ends 9.5, crowned 0.6; H one outline groove, plate 0.2; "
                        "legends 0.35 of the pitch"),
    ("G", "2026-10-11", "rev P (3-D judges r3): F satin charcoal lunes, near-black matte slot; legends 0.22 of the pitch, "
                        "uneven; J the band's hook ends round (tip at 330 deg), the viewer's parked rest 35 forward "
                        "(YOKE rest), column matte near-black"),
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
    v["Pd"] = ds.add_view(mkview("det_L", "xz", 1, -1, (424.0, 240.0), 3.0, "detail L (heel lip), (aft, axis) about "
                                                                           "the pad bottom"))
    return v


def draw(ds):
    v = make_views(ds)
    ds.frame_and_title(fields=dict(date="2026-10-11"))
    draw_secZ(ds, v["Z"])
    draw_secK(ds, v["K"])
    draw_grip_sections(ds)
    draw_profiles(ds, v)
    draw_heads(ds)
    draw_switches(ds)
    draw_column(ds)
    draw_fwd_switches(ds)
    draw_tables(ds)


# ============================================================================================ Z-Z
def draw_secZ(ds, v):
    parts = ("black", "cover")
    S = G.section((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0, 0.0), (-76.0, -66.0, 12.0, 70.0), parts=parts, step=0.2)
    draw_section(ds, v, S, parts=parts)
    X0, Y0 = v.pt(0.0, 0.0)
    ds.cv.line(v.pt(-80.0, 0.0), v.pt(8.0, 0.0), W_THIN, CHAIN)
    ds.cv.line(v.pt(0.0, -70.0), v.pt(0.0, 74.0), W_THIN, CHAIN, color=MUTED)
    fl = np.asarray(D["face_lower"], float)
    T = math.tan(math.radians(float(D["face_tilt"])))
    line(ds, v, [(0.0, float(fl[0, 0])), (-(72.0 - float(fl[0, 0])) * T, 72.0)], W_THIN, CHAIN, color=ACCENT)
    st = np.asarray(D["step"], float)
    il = np.asarray(D["insert_lower_half"], float)
    cr = D["crown"]
    h_top = float(np.asarray(D["shell_half"])[0, 1])
    aF = lambda h: float(G.face_a(h))                                       # noqa: E731
    T_ = X0 + 26.0
    items = [((aF(h_top) - 1.0, h_top - 0.5), (T_, Y0 - 140.0), f"CROWN TOP h {h_top:g}, TOP LAND {float(cr[2]):g} x "
                                                                f"{float(cr[3]):g}", ["C1 chamfer [M low]"]),
             ((aF(float(cr[0])), float(cr[0])), (T_, Y0 - 128.0), f"CROWN SOFT BREAK h {float(cr[0]):g}",
              [f"insert top {float(cr[1]):g}° further fwd, blend R {float(cr[4]):g} [M low / E]"]),
             ((aF(49.65), 49.65), (T_, Y0 - 104.0), f"BADGE: GROOVES {float(D['badge_relief'][1]):g} WIDE x "
                                                    f"{float(D['badge_relief'][0]):g}", ["raised blank plate, no lettering"]),
             ((aF(float(st[0, 1])), float(st[0, 1])), (T_, Y0 - 14.0),
              f"STEP V {D['grooves'][1][0]:g} WIDE x {D['grooves'][1][1]:g} DEEP", ["both inserts FLUSH [M]"]),
             ((aF(-10.0), -10.0), (T_, Y0 + 20.0), f"LOWER INSERT TO h {float(il[:, 1].min()):g}",
              [f"edge groove {D['grooves'][2][0]:g} x {D['grooves'][2][1]:g}"]),
             ((aF(-40.0), -40.0), (T_, Y0 + 60.0), "LOWER FACE: C1 HERMITE", ["tangent to the 17.5° plane"]),
             ((aF(-55.5), -55.5), (T_, Y0 + 96.0), f"FOOT UNDERSIDE R {float(D['edges'][2]):g}",
              [f"cover {float(D['cover_t']):g} on the body [E]"])]
    for P, Tt, t_, more in items:
        leader(ds, v.pt(*P), Tt, t_, more, size=TXT_S, weight=500)
    # ---- dimensions (DR2-06): body depth, cover thickness, crown a, the top-to-front round
    blk = max(S.get("black", []), key=len)
    row = blk[np.abs(blk[:, 1] + 20.0) < 0.6]
    a_f, a_b = float(row[:, 0].min()), float(row[:, 0].max())
    dim(ds, v.pt(a_f, -20.0), v.pt(a_b, -20.0), Y0 + 128.0, f"{a_b - a_f:.1f} BODY DEPTH @ h -20")
    cov = max(S.get("cover", []), key=len)
    rc = cov[np.abs(cov[:, 1] + 30.0) < 0.6]
    dim(ds, v.pt(float(rc[:, 0].min()), -30.0), v.pt(float(rc[:, 0].max()), -30.0), Y0 + 134.0,
        f"{float(rc[:, 0].max() - rc[:, 0].min()):.1f} COVER", outside=True)
    h_ct, a_ct = YS.crown_top()                     # rev L (judges DR3-05): the solid's crown top edge
    dim(ds, v.pt(a_ct, h_ct), v.pt(0.0, h_ct), Y0 - 145.0, f"{-a_ct:.1f} CROWN TOP EDGE FWD OF a 0", outside=True)
    top = blk[blk[:, 1] > 30.0]
    k = int(np.argmin(top[:, 0] + 0.6 * top[:, 1]))
    leader(ds, v.pt(*top[k]), (X0 + 26.0, Y0 - 86.0), f"BODY TOP {float(D['body_form'][1]):g}° FROM HORIZONTAL",
           [f"top-to-front R {float(D['body_form'][6]):g} [E], forward face {float(D['body_form'][0]):g} deep [E]"],
           size=TXT_S, weight=500)
    from drawing.yoke_draw import ordinates
    ords = [(aF(h_top), h_top, None), (aF(float(cr[0])), float(cr[0]), None),
            (aF(53.2), 53.2, None), (aF(46.1), 46.1, None), (0.0, float(st[0, 1]), None),
            (aF(float(il[:, 1].min())), float(il[:, 1].min()), None), (aF(-56.0), -56.0, None),
            (a_f + 25.0, float(blk[:, 1].min()), "BODY FOOT"),
            (float(blk[np.argmax(blk[:, 1]), 0]), float(blk[:, 1].max()), "BODY TOP (BEHIND THE CROWN)")]
    ordinates(ds, v, ords, X0 + 20.0, side=+1, min_gap=3.0)
    for k_, t in enumerate((f"BODY: {float(D['body_form'][0]):g} DEEP [E], ITS TOP A PLANE {float(D['body_form'][1]):g}° "
                            f"FROM THE HORIZONTAL THROUGH THE TOP LINE (h {float(G.top_line(0.0)):.1f} AT u 0); THE R "
                            f"{float(D['body_form'][3]):g} AFT x TOP ROUND LOWERS THE SECTION'S TOP TO "
                            f"{float(blk[:, 1].max()):.1f}",
                            f"rounds in order: aft R {float(D['body_form'][3]):g}, top R {float(D['body_form'][3]):g}, "
                            f"forward R {float(D['body_form'][4]):g}, foot R {float(D['body_form'][5]):g} [E]; one moulding "
                            f"with the grips (R {float(D['neck'][3]):g})",
                            "PLANE u 0 (CUTTING PLANE Z-Z ON L6Y FRONT ELEVATION)")):
        lbl(ds, X0 - 140.0, Y0 + 142.0 + 3.0 * k_, t, TXT_S, color=MUTED)
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
    parts = ("black", "cover", "tcs", "afcs")                 # rev L (judges DR3-03): every solid the plane cuts
    extK = (-80.0, -26.0, 10.0, 26.0)
    S = G.section(p, (0.0, 0.0, 1.0), e1, extK, parts=parts, step=0.15, clip=True)
    draw_section(ds, v, S, parts=parts, clip=(extK, 0.15))
    X0, Y0 = v.pt(0.0, 0.0)
    for nm_, at, txt, more in (("tcs", (X0 + 26.0, Y0 - 24.0), f"TCS BEZEL IN ITS {float(D['tcs_seat']):g} SEAT",
                                 ["(cut 8.8 off its axis)"]),
                                ("afcs", (X0 + 26.0, Y0 + 22.0), "AFCS CAP ON ITS BOSS", ["(cut 3.4 off its axis)"])):
        Cs = [C for p_, C in section_contours(S, (nm_,))]
        if Cs:
            C = max(Cs, key=len)
            k = int(np.argmax(C[:, 0]))
            leader(ds, v.pt(*C[k]), at, txt, more, size=TXT_S, weight=500)
    cr = D["crown"]
    E = D["edges"]
    cov = [C for p_, C in section_contours(S, ("cover",))]
    if cov:
        C = cov[0]
        top = C[np.argmax(C[:, 1])]
        bot = C[np.argmin(C[:, 1])]
        leader(ds, v.pt(*top), (X0 + 26.0, Y0 - 40.0), f"TOP LAND {float(cr[2]):g} x {float(cr[3]):g}",
               ["the arm's top edge, C1 chamfer"], size=TXT_S, weight=500)
        leader(ds, v.pt(*bot), (X0 + 26.0, Y0 + 38.0), f"ARM LOWER EDGE R {float(E[1]):g}",
               [f"cover {float(D['cover_t']):g} [E], perimeter R {float(E[0]):g}"], size=TXT_S, weight=500)
        dim(ds, v.pt(float(C[:, 0].max()), float(top[1])), v.pt(float(C[:, 0].max()), float(bot[1])),
            X0 + 16.0, f"{float(top[1] - bot[1]):.1f} ARM", orient="v")
    blk = [C for p_, C in section_contours(S, ("black",))]
    if blk:
        B = blk[0]
        dim(ds, v.pt(float(B[:, 0].min()), float(B[:, 1].min())), v.pt(float(B[:, 0].max()), float(B[:, 1].min())),
            Y0 + 52.5, f"{float(B[:, 0].max() - B[:, 0].min()):.1f} BODY BEHIND THE ARM")
    lbl(ds, X0 - 98.0, Y0 - 50.0, "UP-INBOARD", TXT_S, color=MUTED, weight=600)
    lbl(ds, X0 - 98.0, Y0 + 57.0, "FWD <-   -> AFT", TXT_S, color=MUTED)
    view_title(ds, X0 - 40.0, Y0 + 62.0, "SECTION K-K", "THROUGH (52, 45) NORMAL TO THE ARM (30° UP OUTBOARD), LOOKING "
                                                       "INBOARD (L6Y FRONT ELEVATION) - 2:1", size=3.4)


# ============================================================================================ grip sections
def draw_grip_sections(ds):
    """Grip sections A1-A4 / N1-N4 at 1:1 (normal to the mean axis, looking down it) + DETAIL S (A3's pad edge and
    frame at 5:1)."""
    x_cells = [272.0 + 66.0 * k for k in range(4)]
    for g, Yc, lets, sx in (("out", 62.0, "A", -1.0), ("in", 136.0, "N", 1.0)):
        pg = "grip_" + g
        ph_any = False
        for k, h in enumerate(GRIP_SECTION_H):
            Xc = x_cells[k]
            vs = ds.add_view(mkview(f"sec_{lets}{k + 1}", "yz", sx, 1, (Xc, Yc), 1.0,
                                    f"grip section {lets}{k + 1} (across, along the aft normal)"))
            ext = (-42.0, -40.0, 36.0, 10.0)
            # rev L (judges DR3-04): the cut of the MOULDING (the grip joined to the web / neck where they meet), the
            # grip prism alone as a phantom where the two differ; cut edges along the frame of the section broken
            p_, e1_, e2_ = G.grip_section_frame(g, h)
            Sb = G.section(G.to_cop(p_, g), G.to_cop(e1_, g), G.to_cop(e2_, g), ext, parts=("black",), step=0.15,
                           clip=True)
            S = G.grip_section(g, h, extent=ext, parts=(pg,), step=0.15)
            draw_section(ds, vs, Sb, parts=("black",), style={"black": ("#E3E6E8", 45.0, 0.8)}, clip=(ext, 0.15))
            # rev M (judges DR4-07): the leather pad hatched as its own material over the moulding's pocket
            Sp = G.section(G.to_cop(p_, g), G.to_cop(e1_, g), G.to_cop(e2_, g), ext, parts=("pad_" + g,), step=0.15)
            draw_section(ds, vs, Sp, parts=("pad_" + g,), min_island=0.5)
            C = [c for _, c in section_contours(S, (pg,))]
            Cb = [c for _, c in section_contours(Sb, ("black",))]
            if C:
                C = C[0]
                diff = Cb and abs(_area(Cb[0]) - _area(C)) > 2.0
                if diff:
                    poly(ds, vs, C, W_THIN, dash=PHANTOM, color=MUTED)
                    ph_any = True
                w = float(C[:, 0].max() - C[:, 0].min())
                dpt = float(C[:, 1].max() - C[:, 1].min())
                d_t = float(G._depth(h, g))                          # rev M (judges DR4-07): the depth read as
                lip = dpt - d_t                                       # the table's + the heel lip / pad crown
                ds.text(Xc, Yc + 9.0, f"GRIP {w:.1f} x {dpt:.1f}" + (f" = {d_t:.1f} + {lip:.1f} LIP" if lip > 0.15
                                                                     else ""), TXT_S, "mono", "middle", tag="dim")
            ds.cv.line((Xc - 28.0, Yc), (Xc + 28.0, Yc), W_THIN, CHAIN, color=MUTED)
            view_title(ds, Xc, Yc + 15.0, f"{lets}{k + 1}-{lets}{k + 1}", f"h {h:g} - 1:1", size=3.0)
        lbl(ds, x_cells[0] - 30.0, Yc - 40.0,
            f"{'OUTBOARD' if g == 'out' else 'INBOARD'} GRIP, NORMAL TO THE AXIS, LOOKING DOWN IT (FWD UP, PAD DOWN; "
            f"{'OUTBOARD LEFT' if g == 'out' else 'INBOARD RIGHT'})", TXT_S, color=MUTED, weight=600)
        if ph_any:
            lbl(ds, x_cells[0] - 30.0, Yc - 36.6, "hatched: the cut of the black moulding; dashed phantom: the grip "
                                                  f"alone where the moulding runs on into the "
                                                  f"{'web' if g == 'out' else 'neck'}", 1.8, color=MUTED)
    ps = D["pad_section"]
    lbl(ds, x_cells[0] - 30.0, 168.0, f"PAD: leather {float(ps[0]):g} below the {float(D['grip_frame']):g} frame, "
                                      f"crowned to {abs(float(ps[1])):g} below over {float(ps[2]):g}; groove "
                                      f"{float(ps[4]):g} x {float(ps[5]):g} + bead {float(ps[3]):g}; frame roll R "
                                      f"{float(D['grip_edges'][0]):g}; forward R {float(D['grip_edges'][1]):g} [E] <= "
                                      f"{float(D['grip_edges'][2]):g} x half-width; depth {float(D['grip_depth'][1][1]):g} (grip_depth) [M]",
        TXT_S, color=MUTED)
    # DETAIL S: A3's outer pad edge / frame at 5:1 -- rev M (judges DR4-04): leader targets and dimensions taken from
    # the drawn contour (the section's outer wall at the frame top, not the grip's widest point further forward)
    p, e1, e2 = G.grip_section_frame("out", GRIP_SECTION_H[2])
    S = G.grip_section("out", GRIP_SECTION_H[2], extent=(-42.0, -40.0, 36.0, 10.0), parts=("grip_out",), step=0.15)
    C = [c for _, c in section_contours(S, ("grip_out",))]
    if C:
        top = C[0][C[0][:, 1] > -0.8]
        x_out = float(top[:, 0].max())                       # outer wall at the frame top
        extS = (x_out - 9.0, -7.0, x_out + 1.0, 2.0)
        args = (G.to_cop(p, "out"), G.to_cop(e1, "out"), G.to_cop(e2, "out"), extS)
        Sd = G.section(*args, parts=("grip_out",), step=0.04, clip=True)
        Sl = G.section(*args, parts=("pad_out",), step=0.04, clip=True)
        vd = ds.add_view(mkview("det_S", "yz", -1, 1, (540.0 + 5.0 * (x_out - 4.0), 118.0), 5.0, "detail S"))
        draw_section(ds, vd, Sd, parts=("grip_out",), style={"grip_out": ("#E3E6E8", 45.0, 1.2)}, clip=(extS, 0.04))
        draw_section(ds, vd, Sl, parts=("pad_out",), style={"pad_out": ("#CFC4B8", 0.0, 0.8)}, clip=(extS, 0.04))
        X0, Y0 = vd.pt(x_out - 4.0, 0.0)
        fr = float(D["grip_frame"])
        rec, gw, gd, bead = (float(ps[i_]) for i_ in (0, 4, 5, 3))
        t_l = float(ps[7])
        Cd = max([c for _, c in section_contours(Sd, ("grip_out",))], key=len)

        def near(q):
            return Cd[int(np.argmin(np.hypot(Cd[:, 0] - q[0], Cd[:, 1] - q[1])))]
        wall = Cd[(Cd[:, 1] < -0.6) & (Cd[:, 1] > -rec + 0.3) & (Cd[:, 0] < x_out - 1.0)]
        x_wall = float(wall[:, 0].max()) if len(wall) else x_out - fr
        P1 = near((x_out - 0.4, -0.3))
        leader(ds, vd.pt(*P1), (X0 - 34.0, Y0 - 26.0), f"FRAME {fr:g}, EDGE R {float(D['grip_edges'][0]):g}", None,
               size=TXT_S, weight=500)
        P2 = near((x_wall - 0.5 * gw, -rec - gd))
        leader(ds, vd.pt(*P2), (X0 + 14.0, Y0 + 46.0), f"GROOVE {gw:g} x {gd:g}, BEAD {bead:g}",
               [f"leather {rec:g} below the frame,", f"crowned to {abs(float(ps[1])):g} over {float(ps[2]):g}"],
               size=TXT_S, weight=500)
        Cl = [c for _, c in section_contours(Sl, ("pad_out",))]
        if Cl:
            L_ = max(Cl, key=len)
            q = L_[int(np.argmin(np.hypot(L_[:, 0] - (x_wall - 5.0), L_[:, 1] + rec + 1.0)))]
            leader(ds, vd.pt(*q), (X0 + 14.0, Y0 + 38.0), f"LEATHER PAD {t_l:g} [E]",
                   ["hatched apart: its own material"], size=TXT_S, weight=500)
        # dimensions: the frame width at the top, the leather's depth below the frame and its layer
        xm_ = 0.5 * (vd.pt(x_out, 0.0)[0] + vd.pt(x_wall, 0.0)[0])          # text above the line, between the
        ds.cv.rect(xm_ - 2.6, Y0 - 19.7, 5.2, 3.1, lw=0, fill="#FFFFFF", stroke=False)   # the hatch knocked out
        dim(ds, vd.pt(x_out, 0.0), vd.pt(x_wall, 0.0), Y0 - 14.0, f"{x_out - x_wall:.1f}", outside=True,
            text_at=(xm_, Y0 - 16.6))
        xd = x_wall - gw - 2.0 * bead - 1.2
        dim(ds, vd.pt(xd, 0.0), vd.pt(xd, -rec), X0 + 30.0, f"{rec:g}", orient="v", outside=True)
        dim(ds, vd.pt(xd - 2.5, -rec), vd.pt(xd - 2.5, -rec - t_l), X0 + 38.0, f"{t_l:g}", orient="v", outside=True)
        view_title(ds, X0 - 22.0, Y0 + 30.0, "DETAIL S", "A3 OUTER PAD EDGE - 5:1", size=3.0)


def _area(C):
    C = np.asarray(C, float)
    return 0.5 * abs(float(np.sum(C[:, 0] * np.roll(C[:, 1], -1) - np.roll(C[:, 0], -1) * C[:, 1])))


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
    leader(ds, vP.pt(-0.5, 20.0), (vP.pt(0, 0)[0] - 46.0, vP.pt(0, 20.0)[1]), "PAD RECESS", ["in the frame"],
           size=TXT_S, weight=500)
    vQ = v["Q"]
    leader(ds, vQ.pt(1.0, 80.0), (vQ.pt(0, 0)[0] + 24.0, vQ.pt(0, 80.0)[1] - 34.0),
           f"SHIELD FACET {float(D['head_in'][2]):g}° UP", [f"head falls {float(D['head_in'][4]):g}° round it"],
           size=TXT_S, weight=500)
    lbl(ds, vP.pt(-38.0, 112.0)[0], vP.pt(0, 112.0)[1] - 2.0, "AXIAL PLANES (AXIS + AFT NORMAL), FWD LEFT", TXT_S,
        color=MUTED, weight=600)
    # DETAIL L: the heel lip of the outboard grip at 3:1, about the axis point at the pad's bottom
    p0, t, e2 = axial_frame("out")
    pb = float(G.pad_outline("out")[:, 1].min())
    pc = p0 + t * (pb - p0[1]) / t[1]
    vd = v["Pd"]
    extL = (-14.0, -20.0, 8.0, 12.0)
    S = G.section(pc, e2, t, extL, parts=("black",), step=0.08, clip=True)
    draw_section(ds, vd, S, parts=("black",), clip=(extL, 0.08))
    X0, Y0 = vd.pt(0.0, 0.0)
    hl = D["heel"]
    ps = D["pad_section"]
    leader(ds, vd.pt(float(hl[1]) - 0.3, -7.0), (X0 + 8.0, Y0 + 56.0), f"HEEL LIP {float(hl[1]):g} PROUD, "
                                                                       f"ROLL R {float(hl[2]):g}",
           [f"rises C1 over {0.6 * float(hl[0]):g} of its {float(hl[0]):g}"], size=TXT_S, weight=500)
    leader(ds, vd.pt(-float(ps[0]) + 0.3, 4.0), (X0 + 4.0, Y0 - 44.0), f"LEATHER {float(ps[0]):g} BELOW THE FRAME",
           [f"groove {float(ps[4]):g} x {float(ps[5]):g}, bead {float(ps[3]):g} (detail S)"], size=TXT_S, weight=500)
    view_title(ds, X0 - 6.0, Y0 + 70.0, "DETAIL L - HEEL LIP", "OUTBOARD GRIP, ON P-P, AFT RIGHT - 3:1", size=3.0)


# ============================================================================================ heads
def _trim_view_sil():
    """The black moulding seen along the trim face's normal round the face (judges DR2-02: detail F from the
    solid), (x along eu, y along ev) mm about the face centre."""
    from drawing.yoke_draw import silhouette_dir
    c, n = G.head_out_face()
    eu, ev = G._facet_frame(c, n)
    return G.disk_cached(("detF_sil2",), lambda: silhouette_dir("black", c, n, eu, ev, (-21.0, -21.0, 21.0, 21.0),
                                                                 depth=(-16.0, 4.0), step=0.25, dstep=0.3))


def _axis_section(part_pairs, c, n, e1, extent, step=0.05):
    """Exact section through a switch axis: plane through c spanned by e1 (across) and n (along the axis)."""
    return G.section(c, e1, n, extent, parts=part_pairs, step=step)


def draw_heads(ds):
    # F: view normal to the round trim face (2:1), the moulding round it from the solid
    vF = ds.add_view(mkview("det_F", "yz_aft", -1, -1, (506.0, 236.0), 2.0, "detail F (trim face), face plane mm"))
    R = 0.5 * float(D["head_out"][2])
    od = float(D["trim"][2])
    lune, r0, r1, sexp = (float(x) for x in D["trim_lunes"][:4])
    c = np.zeros(2)
    for C in sorted(_trim_view_sil(), key=len, reverse=True):
        poly(ds, vF, C, W_FINE, fill="#596166")                          # clipped at +-21 (the frame of the detail)
    circ(ds, vF, c, 2 * R, W_OBJ, fill="#2B3135")
    circ(ds, vF, c, od, W_FINE, fill="#23292D", color="#C9CFD3")
    poly(ds, vF, YS.slot_outline(), W_THIN, fill=SLOT, color="#9AA3A9")          # rev N: the recessed rocker slot
    for k in (2, 3):
        for Q in legend_quads(c, k):
            poly(ds, vF, Q, 0.05, fill=LEGEND, color=LEGEND)
    for half in rocker_halves():
        poly(ds, vF, half, W_FINE, fill=SWITCH, color="#C9CFD3")
    centre_mark(ds, vF, c, R)
    X0, Y0 = vF.pt(0, 0)
    dim(ds, vF.pt(R, 0), vF.pt(-R, 0), Y0 + 2 * R + 10.0, f"{2 * R:.1f} FACE")
    dim(ds, vF.pt(0.5 * od, 0), vF.pt(-0.5 * od, 0), Y0 - 2 * R - 8.0, f"{od:.1f} RING")
    tr = D["trim"]
    tg = D["trim_grooves"]
    leader(ds, vF.pt(10.0, 1.0), (X0 + 44.0, Y0 - 12.0), f"ROCKER {float(tr[3]):g} x {float(tr[4]):g}",
           [f"waist {float(tr[5]):g}, split {float(tr[6]):g}", "two mirrored lobes"], size=TXT_S, weight=500)
    sd_ = D["trim_slot"]
    leader(ds, vF.pt(0.0, 11.5), (X0 + 44.0, Y0 - 30.0), "DN LUNE (FWD), SATIN CHARCOAL",
           ["legend: 2 words of letter", "blocks (no lettering)"], size=TXT_S, weight=500)
    leader(ds, vF.pt(0.0, -11.5), (X0 + 44.0, Y0 + 16.0), "UP LUNE (AFT)",
           [f"ring groove {float(tg[0]):g} x {float(tg[1]):g}; SLOT", f"RECESSED {float(sd_[0]):g}, walls on the",
            f"chords, draft {float(sd_[2]):g}°, ends {float(sd_[1]):g}", "inside the ring; MATTE NEAR-BLACK"],
           size=TXT_S, weight=500)
    from model import yoke_checks as YC
    pr = YC.run_all()["proud"]
    lbl(ds, X0 - 48.0, Y0 + 2 * R + 19.0, "grey: the black moulding seen along the face normal (exact silhouette, "
                                          "clipped +/-21);", TXT_S, color=MUTED)
    lbl(ds, X0 - 48.0, Y0 + 2 * R + 22.0, f"nothing of it stands above the face: max {pr['trim_face']:.2f} mm "
                                          "(yoke_checks)", TXT_S, color=MUTED)
    # rocker saddle profile
    vR = ds.add_view(mkview("det_F2", "xz", 1, -1, (506.0, 310.0), 2.0, "detail F rocker profile"))
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
    yl_, re_, dep_, dr_ = G.trim_slot_dims()                             # rev N: the slot floor under the rocker
    xe_ = math.sqrt(max(re_ ** 2 - yl_ ** 2, 0.0))
    line(ds, vR, [(-re_ + dep_ * math.tan(dr_), -dep_), (re_ - dep_ * math.tan(dr_), -dep_)], W_FINE, dash=HID)
    X1, Y1 = vR.pt(0, 0)
    dim(ds, vR.pt(0.5 * L, he), vR.pt(0.5 * L, 0.0), X1 + L + 7.0, f"{he:g}", orient="v")
    dim(ds, vR.pt(0.0, hm), vR.pt(0.0, 0.0), X1 - L - 9.0, f"{hm:g}", orient="v", outside=True)
    lbl(ds, X1 + 12.0, Y1 + 7.0, f"SADDLE (EXPONENT {sexp:g}) [M low], CROWNED {G.rocker_crown():g} ACROSS, TOP EDGES "
                                  f"R {float(tg[2]):g}", TXT_S, "middle")
    lbl(ds, X1 + 12.0, Y1 + 9.5, f"LOBES FROM THE SLOT FLOOR {dep_:g} BELOW THE FACE (HIDDEN)", TXT_S, "middle")
    cF, nF = G.head_out_face()
    lbl(ds, X1 + 12.0, Y1 + 12.0, "AXIS: the face normal ({3:.2f}, {4:.2f}, {5:.2f}) through ({0:.1f}, {1:.1f}, a "
                                  "{2:.1f})".format(*np.r_[cF, nF]), TXT_S, "middle", color=MUTED)
    view_title(ds, X0, Y1 + 16.0, "DETAIL F - TRIM HEAD", f"VIEW NORMAL TO THE ROUND FACE "
                                                          f"({float(D['head_out'][3]):g}° UP) - 2:1", size=3.0)
    # G: view normal to the shield facet (2:1) + the button profile (an exact section of the solids)
    vG = ds.add_view(mkview("det_G", "yz_aft", 1, -1, (512.0, 365.5), 2.0, "detail G (shield), facet plane mm"))
    S2 = G.shield_outline()
    poly(ds, vG, S2, W_OBJ, fill="#2F363A")
    bp = YS.button_pieces()
    c2 = bp["centre2"]
    b = D["button"]
    bd = G.button_dims()
    circ(ds, vG, c2, bd["disc_d"], W_FINE, fill="#23292D", color="#C9CFD3")          # rev O: the gloss-black disc
    for Q in legend_quads(c2, 4, mirror=True):
        poly(ds, vG, Q, 0.05, fill=LEGEND, color=LEGEND)
    poly(ds, vG, hexagon(bd["hex_c"]) + c2, W_FINE, fill=NICKEL, color="#C9CFD3")
    circ(ds, vG, c2, bd["cap_d"], W_FINE, fill="#3A4247", color="#C9CFD3")
    circ(ds, vG, c2, bd["dimple_d"], W_THIN, color="#C9CFD3")
    X0, Y0 = vG.pt(*c2)
    sc = np.asarray(D["shield"], float)
    dim(ds, vG.pt(sc[0, 0], sc[0, 1]), vG.pt(sc[1, 0], sc[1, 1]), vG.pt(0, sc[0, 1])[1] - 6.0,
        f"{sc[1, 0] - sc[0, 0]:.0f} SHIELD")
    leader(ds, vG.pt(c2[0] - 6.5, c2[1] - 5.5), (X0 - 40.0, Y0 + 14.0), f"GLOSS-BLACK DISC {bd['disc_d']:g}, "
                                                                        f"{bd['disc_z']:g} PROUD",
           [f"nickel hex {bd['hex_c']:g} A/C / {bd['hex_f']:.1f} A/F x {bd['hex_h']:g}; cap {bd['cap_d']:g}, top "
            f"{bd['cap_z']:g} above the facet, dimple {bd['dimple_d']:g}"], size=TXT_S, weight=500)
    leader(ds, vG.pt(c2[0] - 4.5, c2[1] + 5.5), (X0 - 40.0, Y0 - 18.0), "MAP LIGHTS AS LETTER BLOCKS",
           ["on the disc's rim, upper / inboard arc (no lettering)"], size=TXT_S, weight=500)
    lbl(ds, X0 - 22.0, Y0 + 29.0, "INBOARD -> RIGHT (pilot); facet "
                                  f"{float(D['head_in'][2]):g}° up, toe {float(D['head_in'][3]):g}°", TXT_S,
        color=MUTED)
    view_title(ds, X0, Y0 + 35.0, "DETAIL G - INBOARD HEAD", "VIEW NORMAL TO THE SHIELD FACET - 2:1", size=3.0)
    # the push button in section along the facet normal (exact cut of the button + head solids), 3:1
    vB = ds.add_view(mkview("det_G2", "xz", 1, -1, (458.0, 410.0), 3.0, "detail G button profile"))
    cb, nb, eub, evb = G.button_frame()
    m = np.array([-1.0, 1.0, 1.0])
    Sb = _axis_section(("button", "black"), cb * m, nb * m, evb * m, (-13.0, -4.0, 13.0, 10.0), step=0.05)
    draw_section(ds, vB, Sb, parts=("black", "button"))
    X2, Y2 = vB.pt(0, 0)
    af, cd_, ch_, dimple = bd["hex_f"], bd["cap_d"], bd["cap_h"], bd["dimple_d"]
    hz, dz = bd["hex_z"], bd["disc_z"]
    dim(ds, vB.pt(0.5 * cd_, hz + ch_), vB.pt(0.5 * cd_, hz), X2 + 24.0, f"{ch_:g}", orient="v")
    dim(ds, vB.pt(-0.5 * af, hz), vB.pt(-0.5 * af, 0.0), X2 - 26.0, f"{hz:g}", orient="v", outside=True)
    dim(ds, vB.pt(-0.5 * bd["disc_d"], dz), vB.pt(0.5 * bd["disc_d"], dz), Y2 + 6.0, f"DISC {bd['disc_d']:g}")
    lbl(ds, X2 - 12.0, Y2 + 16.0, f"DISC {dz:g} PROUD R {bd['disc_r']:g}; HEX {af:.1f} A/F x {bd['hex_h']:g}; CAP "
                                  f"{cd_:g}, TOP R 1, DIMPLE {dimple:g} x {bd['dimple_t']:g} [E]", TXT_S)
    lbl(ds, X2 - 12.0, Y2 + 19.0, "BUTTON: EXACT CUT ALONG THE FACET NORMAL - 3:1", TXT_S, color=MUTED)
    lbl(ds, X2 - 12.0, Y2 + 22.0, "AXIS: the facet normal through (-{0:.1f}, {1:.1f}, a {2:.1f}); facet point (-{3:g}, "
                                  "{4:g}, a {5:g})".format(*np.r_[cb, float(D['head_in'][0]), float(D['head_in'][1]),
                                                                  float(D['head_in_a'])]), TXT_S, color=MUTED)


# ============================================================================================ switches
def draw_switches(ds):
    # ---- D: TCS (3:1) face + profile (an exact cut of the TCS + cover solids through its axis)
    u, h, od, bd, _ = (float(x) for x in D["tcs"][:5])
    pr = D["tcs_profile"]
    vD = ds.add_view(mkview("det_D", "yz_aft", -1, -1, (300.0, 456.0), 3.0, "detail D (TCS), mm about its centre"))
    YS.draw_tcs(ds, vD, 1.4, c=(0.0, 0.0))
    centre_mark(ds, vD, (0.0, 0.0), 0.5 * od)
    X0, Y0 = vD.pt(0, 0)
    dim(ds, vD.pt(0.5 * od, 0), vD.pt(-0.5 * od, 0), Y0 - 1.5 * od - 5.0, f"{od:g} BEZEL")
    vD2 = ds.add_view(mkview("det_D2", "xz", 1, -1, (300.0, 512.0), 3.0, "detail D profile"))
    c, n = G.tcs_axis()
    extD = (-14.0, -4.0, 14.0, 5.0)
    S = G.section(c, (1.0, 0.0, 0.0), n, extD, parts=("cover", "tcs"), step=0.04, clip=True)
    draw_section(ds, vD2, S, parts=("cover", "tcs"), clip=(extD, 0.04))
    bz_h, rr, dish, dome, below, r_in, r_out = (float(x) for x in pr[:7])
    X1, Y1_ = vD2.pt(0, 0)
    top = bz_h - below
    dim(ds, vD2.pt(0.5 * od, bz_h), vD2.pt(0.5 * od, 0.0), X1 + 1.5 * od + 9.0, f"{bz_h:g}", orient="v", outside=True)
    dim(ds, vD2.pt(-0.5 * bd, top), vD2.pt(-0.5 * bd, bz_h), X1 - 1.5 * od - 9.0, f"{top - bz_h:g}", orient="v",
        outside=True)
    lbl(ds, X1, Y1_ + 15.0, f"bezel {bz_h:g} proud, dish r {r_in:g}-{r_out:g} {dish:g} deep [E]; button dome {dome:g}, "
                            f"its top {top - bz_h:g} ABOVE the bezel [M low]", TXT_S, "middle")
    lbl(ds, X1, Y1_ + 18.0, "AXIS: the 17.5° face's normal through ({0:.1f}, {1:.1f}, a {2:.1f})".format(*c), TXT_S,
        "middle", color=MUTED)
    view_title(ds, X1, Y1_ + 23.0, "DETAIL D - TCS", f"u {u:g} h {h:g} ON THE WHITE ARM; PROFILE = EXACT CUT - 3:1",
               size=3.0)
    # ---- E: AFCS (3:1): the round boss (a solid of the black moulding) + the red cap, exact cut through the axis
    u, h, cd, ch, bdo = (float(x) for x in D["afcs"][:5])
    ab = D["afcs_boss"]
    vE = ds.add_view(mkview("det_E", "yz_aft", -1, -1, (395.0, 460.0), 3.0, "detail E (AFCS), mm"))
    YS.draw_afcs(ds, vE, 1.4, c=(0.0, 0.0))
    centre_mark(ds, vE, (0.0, 0.0), 0.5 * bdo)
    X0, Y0 = vE.pt(0, 0)
    dim(ds, vE.pt(0.5 * bdo, 0), vE.pt(-0.5 * bdo, 0), Y0 - 1.5 * bdo - 5.0, f"{bdo:g} BOSS")
    vE2 = ds.add_view(mkview("det_E2", "xz", 1, -1, (395.0, 522.0), 3.0, "detail E profile"))
    c, n = G.afcs_axis()
    extE = (-14.0, -9.0, 14.0, 7.0)
    S = G.section(c, (1.0, 0.0, 0.0), n, extE, parts=("black", "afcs"), step=0.05, clip=True)
    draw_section(ds, vE2, S, parts=("black", "afcs"), clip=(extE, 0.05), min_island=6.0)
    X1, Y1_ = vE2.pt(0, 0)
    from cad import sdf2d
    for p_, C in section_contours(S, ("black",)):                    # rev L (judges DR3-08): name the other island
        if sdf2d.polygon(np.array([0.0]), np.array([-1.0]), C)[0] > 0 and len(C) > 8 and _area(C) >= 6.0:
            k = int(np.argmax(C[:, 1]))
            leader(ds, vE2.pt(*C[k]), (X1 + 1.5 * bdo + 4.0, Y1_ - 22.0), "NECK (BEHIND), CUT BY THE WINDOW", None,
                   size=1.8, weight=400, color=MUTED)
    dim(ds, vE2.pt(-0.5 * cd, ch), vE2.pt(-0.5 * cd, 0.0), X1 - 1.5 * bdo - 16.0, f"{ch:g}", orient="v")
    dim(ds, vE2.pt(-0.5 * cd, ch), vE2.pt(0.5 * cd, ch), Y1_ - 3 * ch - 6.0, f"{cd:g} CAP")
    dim(ds, vE2.pt(-0.5 * bdo, 0.0), vE2.pt(-0.5 * bdo, -float(ab[1])), X1 - 1.5 * bdo - 6.0, f"{float(ab[1]):g}",
        orient="v", outside=True)
    lbl(ds, X1, Y1_ + 33.0, f"boss {float(ab[0]):g} proud of the body [E], {float(ab[1]):g} deep: its back free over the "
                            f"hand slot; edge R {float(ab[2]):g}, cap top R {float(ab[4]):g}", TXT_S, "middle")
    lbl(ds, X1, Y1_ + 36.0, "AXIS: the 17.5° face's normal through the boss face ({0:.1f}, {1:.1f}, a {2:.1f}) = face "
                            "- cover 3 + 1.5".format(*c), TXT_S, "middle", color=MUTED)
    view_title(ds, X1, Y1_ + 41.0, "DETAIL E - AFCS DISCONNECT", f"u {u:g} h {h:g}; BOSS = A SOLID OF THE MOULDING; "
                                                                 "PROFILE = EXACT CUT - 3:1", size=3.0)
    # ---- H: badge (2:1)
    vH = ds.add_view(mkview("det_H", "yz_aft", -1, -1, (510.0, 452.0), 2.0, "detail H (badge), mm about h 49.65"))
    F = I.yoke_front_mm()
    hc = 49.65
    sub = np.array([0.0, hc])
    poly(ds, vH, F["badge"] - sub, W_OBJ, fill=SILVER)
    if F["badge_border"] is not None:
        poly(ds, vH, F["badge_border"] - sub, W_FINE)
    for Ln in F["badge_lines"]:
        line(ds, vH, Ln - sub, W_FINE)
    poly(ds, vH, F["badge_plate"] - sub, W_FINE, fill="#DDE0E3")       # rev N: the raised blank plate
    X0, Y0 = vH.pt(0, 0)
    (bu0, bh0), (bu1, bh1) = D["badge"]
    dim(ds, vH.pt(bu0, bh0 - hc), vH.pt(-bu0, bh0 - hc), Y0 - 12.0, f"{2 * bu0:.1f}")
    dim(ds, vH.pt(bu1, bh1 - hc), vH.pt(-bu1, bh1 - hc), Y0 + 12.0, f"{2 * bu1:.1f}")
    dim(ds, vH.pt(-bu0, bh0 - hc), vH.pt(-bu1, bh1 - hc), X0 + 52.0, f"{bh0 - bh1:.1f}", orient="v", outside=True)
    bp_ = G.badge_plate_dims()
    lbl(ds, X0, Y0 + 20.0, f"RAISED BLANK PLATE {2 * bp_[0]:.1f} x {bp_[2] - bp_[1]:.1f}, {bp_[3]:g} PROUD, R {bp_[4]:g} "
                           f"/ EDGE R {bp_[5]:g} (NO LETTERING); GROOVES {float(D['badge_relief'][1]):g} x "
                           f"{float(D['badge_relief'][0]):g} CUT IN THE INSERT", TXT_S, "middle")
    view_title(ds, X0, Y0 + 28.0, "DETAIL H - BADGE", f"ABSTRACT WINGED PLATE, TOP AT h {bh0:g} - 2:1", size=3.0)


# ============================================================================================ forward-face switches W
W_ORIGIN = (505.0, 507.0)          # sheet position of detail W (two profiles stacked, under detail H)
W_STEP = 44.0


def draw_fwd_switches(ds):
    """DETAIL W (2:1, rev M judges FID4-08): the [E] forward-face switches -- per grip an exact section along the grip
    axis through the switch (plane spanned by the axis and the forward face's normal), the switch drawn in PHANTOM
    (estimated), with its table sizes and axis."""
    X0, Y0 = W_ORIGIN
    for k, (g, nm) in enumerate((("out", "OUTBOARD: PTT TRIGGER"), ("in", "INBOARD: CHECKLIST ROCKER"))):
        c, t, w, n, row = G.fwd_switch_frame(g)
        hc, L, W_, pr, r_e, sag = row[:6]
        cc, tc, nc = (G.to_cop(x, g) for x in (c, t, n))
        ext = (-16.0, -5.0, 16.0, 8.0)
        S = G.section(cc, tc, nc, ext, parts=("black", "fwd_" + g), step=0.05, clip=True)
        v = ds.add_view(mkview(f"det_W{k + 1}", "xz", 1, -1, (X0, Y0 + W_STEP * k), 2.0,
                               f"detail W{k + 1}: section along the {g}board grip axis through its forward switch"))
        draw_section(ds, v, S, parts=("black",), clip=(ext, 0.05))
        for _, C in section_contours(S, ("fwd_" + g,)):
            poly(ds, v, C, W_FINE, fill="#ECEEF0", dash=PHANTOM)
        Xc, Yc = v.pt(0.0, 0.0)
        dim(ds, v.pt(-0.5 * L, pr), v.pt(0.5 * L, pr), Yc - 2.0 * pr - 5.0, f"{L:g} [E]")
        dim(ds, v.pt(0.5 * L, pr), v.pt(0.5 * L, 0.0), Xc + L + 5.0, f"{pr:g}", orient="v")
        lbl(ds, Xc, Yc + 13.0, f"h {hc:g} ON THE FORWARD FACE, {W_:g} WIDE, TOP R {r_e:g}"
            + (f", SADDLE {sag:g}" if sag > 0 else ", FLAT TOP"), TXT_S, "middle")
        lbl(ds, Xc, Yc + 16.0, "AXIS: THE FORWARD FACE'S NORMAL THROUGH ({0:.1f}, {1:.1f}, {2:.1f})".format(*cc),
            TXT_S, "middle", color=MUTED)
        view_title(ds, Xc, Yc + 21.5, f"DETAIL W{k + 1} - {nm} [E]", "PLACEHOLDER (PHANTOM), NEVER SEEN; FWD UP, "
                                                                      "GRIP AXIS ACROSS - 2:1", size=2.8)


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
    # the dished recess and the band in it (hidden behind the yoke from outboard): recess floor 'dep' forward of the
    # panel face, the band from the floor 'bh' proud (column_band, judges FID2-05)
    hw_r, hb_r, rc_r, dep_r, ht_r = (float(x) for x in D["column_recess"])
    bh_ = float(D["column_band"][1])
    hc_b = float(D["column_band"][4])
    hh = np.linspace(hb_r, ht_r, 25)
    apl = Y1_a_panel(hh)
    poly(ds, vJ, np.r_[np.c_[apl, hh], np.c_[apl - dep_r, hh][::-1]], W_THIN, dash=HID, color=MUTED)
    hb_ = np.linspace(hb_r + 6.0, h_top, 20)
    line(ds, vJ, np.c_[Y1_a_panel(hb_) - dep_r + bh_, hb_], W_THIN, dash=HID, color=ACCENT)
    leader(ds, vJ.pt(float(Y1_a_panel(hc_b)[0]) - dep_r + bh_, hc_b), (X0 - 70.0, Y0 - 62.0),
           f"J BAND {bh_:g} PROUD OF THE RECESS FLOOR", [f"recess {dep_r:g} deep [E], floor to h {hb_r:g} [M, re-centred] (hidden)"],
           size=TXT_S, weight=500)
    dim(ds, vJ.pt(a_p0, -r), vJ.pt(-depth, -r), Y0 + 22.0, f"{-depth - a_p0:.0f}")
    lbl(ds, X0 - 70.0, Y0 + 33.0, f"PHANTOM: FULL PUSH {t0:+.0f} (OWNER 2026-10-11; WAS -90 [E]), leaves "
                                  f"{-depth + t0 - a_p0:.0f} to the panel", TXT_S)
    rest = 1000.0 * float(I.YOKE["rest"])
    col_rest = -depth + rest - a_p0                                      # rev P: the viewer's parked yoke (YOKE rest)
    view_title(ds, X0 - 30.0, Y0 + 38.0, "DETAIL J - COLUMN, SIDE", "AT THE LOWER PANEL, FROM OUTBOARD - 1:2", size=3.0)
    # front view of the surround on the panel (pilot: inboard = right)
    vF = ds.add_view(mkview("det_J2", "yz_aft", -1, -1, (756.0, 384.0), 0.5, "detail J front, (u, h) mm"))
    bw = float(D["column_band"][0])                                       # rev N: 22 (column measured 22-25)
    u_in = -(float(col[0]) * 1000.0 - float(I.YOKE["bl"]) * 1000.0)       # inboard side of the band, u (negative)
    rc = abs(u_in) - 0.5 * bw                                              # band centreline radius about the axis
    hw_, hb2, rcr, dep, ht_ = (float(x) for x in D["column_recess"])
    hc_ = float(D["column_band"][4])
    poly(ds, vF, recess_u(hw_, hb2, rcr, ht_), W_FINE, fill="#E3E6E8")
    # band: vertical leg (inboard) from the top end down to the joint, then an arc about (0, hc_) under the stem
    leg = np.array([(-rc, h_top - 0.5 * bw), (-rc, hc_)])
    # rev P (3-D judges r3 CR3-04): the hook ends ROUND, its tip at fd_detail_a.BAND_HOOK_END (the centreline half a band
    # width short of it)
    from model import fd_detail_a as FDA
    th = np.radians(np.linspace(180.0, FDA.BAND_HOOK_END - math.degrees(0.5 * bw / rc), 40))
    arc = np.c_[rc * np.cos(th), hc_ + rc * np.sin(th)]
    cl = np.vstack([leg, arc[1:]])
    t_ = np.gradient(cl, axis=0)
    n_ = np.c_[-t_[:, 1], t_[:, 0]] / np.linalg.norm(t_, axis=1)[:, None]
    band = np.vstack([cl + 0.5 * bw * n_, (cl - 0.5 * bw * n_)[::-1]])
    poly(ds, vF, band, W_FINE, fill=COLLAR)
    circ(ds, vF, (-rc, h_top - 0.5 * bw), bw, W_FINE, fill=COLLAR)
    circ(ds, vF, tuple(arc[-1]), bw, W_FINE, fill=COLLAR)
    line(ds, vF, [(-rc - 0.5 * bw, h_joint), (-rc + 0.5 * bw, h_joint)], W_FINE, color=INK)
    hs_ = h_screw
    us_ = -math.sqrt(max(rc * rc - (hs_ - hc_) ** 2, 0.0))
    circ(ds, vF, (us_, hs_), 5.0, W_THIN, fill="#9AA1A9")
    circ(ds, vF, (0.0, 0.0), 44.0, W_THIN, dash=HID, color=MUTED)
    poly(ds, vF, G.shell_outline(), W_THIN, dash=PHANTOM, color=MUTED)
    X0, Y0 = vF.pt(0, 0)
    leader(ds, vF.pt(-rc, h_top - 0.5 * bw), (X0 + 26.0, Y0 - 42.0), f"J BAND {bw:g} WIDE [M 22-25]",
           [f"inboard leg |BL| {float(col[0]) * 1000:.0f}, top WL {float(col[1]) * 1000:.0f}",
            f"{abs(u_in) - bw - r:.1f} clear of the column all round"], size=TXT_S, weight=500)
    leader(ds, vF.pt(-rc + 0.5 * bw, h_joint), (X0 + 44.0, Y0 + 6.0), f"JOINT WL {float(col[2]) * 1000:.0f} = AXIS",
           [f"screw WL {float(col[3]) * 1000:.0f}"], size=TXT_S, weight=500)
    # the owner decision of 2026-10-11 (fit_check 30c, 3-D judges r1 CR1-01), above the view
    hub_wl = float(I.yoke_hub(-1)[2]) * 1000.0
    for i, t in enumerate(("OWNER DECISION 2026-10-11 (fit_check 30c):",
                           "THE J BAND AND THE U RECESS RE-CENTRED ON THE",
                           f"COLUMN AXIS = THE HUB (WL {hub_wl:.0f}; ROLL PIVOT AND KNEE",
                           "RESULTS KEPT).  REASON: THE PHOTOS READ THE JOINT",
                           f"LINE, I.E. THE COLUMN AXIS, AT WL 1821 +/-10, {hub_wl - 1821.0:.0f} UNDER",
                           f"THE HUB: BAND AND RECESS DRAWN {hub_wl - 1821.0:.0f} UP WITH THE AXIS")):
        lbl(ds, X0 - 42.0, Y0 - 66.0 + 2.6 * i, t, TXT_S, color=ACCENT if i == 0 else INK)
    Pr = vF.pt(-hw_, hb2 + rcr + 12.0)
    leader(ds, Pr, (Pr[0] + 5.0, Pr[1] + 4.0), f"RECESS: U {2 * hw_:g} WIDE [M]",
           [f"floor h {hb2:g} [M, re-centred], corners R {rcr:g} [M]", f"{dep:g} deep [E]; outboard half", "hidden (symmetric [E]);",
            f"band arc about h {hc_:g} (the axis);", f"top h {ht_:g} [E]: the column {ht_ - r:.0f} clear"],
           size=1.9, weight=500)
    dim(ds, vF.pt(-hw_, hb2), vF.pt(hw_, hb2), Y0 + 44.0, f"{2 * hw_:g}")
    lbl(ds, X0 - 40.0, Y0 + 50.0, "phantom: the shell; hidden: the column dia 44 (matte near-black)", TXT_S,
        color=MUTED)
    lbl(ds, X0 - 40.0, Y0 + 52.6, f"viewer (rev P): the free yokes parked {rest:+.0f} [M: unlocked photos], "
                                  f"{col_rest:.0f} of the column to the panel", TXT_S, color=MUTED)
    view_title(ds, X0, Y0 + 58.0, "DETAIL J - SURROUND, FRONT", "LOOKING FORWARD (PILOT; INBOARD RIGHT) - 1:2",
               size=3.0)
    hJ = 0.5 * (h_top - 0.5 * bw + h_joint)                              # mid-leg (re-centred: h 0 .. 13)
    M.cutting_plane(ds, vF, (-rc - 0.5 * bw - 4.0, hJ), (-rc + 0.5 * bw + 4.0, hJ), "J", look=(0.0, 1.0), ext=3.0,
                    length=4.0)
    # SECTION J-J: the band across its vertical leg (judges FID2-05), 2:1
    bw_, bh_, br_, bf_ = (float(x) for x in D["column_band"][:4])
    vS = ds.add_view(mkview("det_JJ", "xz", 1, -1, (624.0, 452.0), 2.0, "section J-J of the band"))
    prof = np.array([(-0.5 * bw_, 0.0), (0.5 * bw_, 0.0), (0.5 * bw_, bh_ - br_)] +
                    [(0.5 * bw_ - br_ + br_ * math.cos(t), bh_ - br_ + br_ * math.sin(t))
                     for t in np.linspace(0.0, 0.5 * math.pi, 9)[1:]] +
                    [(-0.5 * bw_ + br_ + br_ * math.cos(t), bh_ - br_ + br_ * math.sin(t))
                     for t in np.linspace(0.5 * math.pi, math.pi, 9)[1:]])
    hatch_poly(ds, vS, prof, ang=45.0, step=0.6, fill=COLLAR)
    line(ds, vS, [(-0.5 * bw_ - 8.0, 0.0), (0.5 * bw_ + 8.0, 0.0)], W_OBJ)
    X3, Y3 = vS.pt(0, 0)
    dim(ds, vS.pt(-0.5 * bw_, 0.0), vS.pt(0.5 * bw_, 0.0), Y3 + 5.0, f"{bw_:g}")
    dim(ds, vS.pt(0.5 * bw_, bh_), vS.pt(0.5 * bw_, 0.0), X3 + bw_ + 6.0, f"{bh_:g}", orient="v")
    view_title(ds, X3, Y3 + 11.0, "SECTION J-J - BAND", "ACROSS THE VERTICAL LEG (P1046410 / 09) - 2:1", size=3.0)
    lbl(ds, X3 + bw_ + 14.0, Y3 - 9.0, f"ROLLED EDGES R {br_:g}, FLAT TOP {bf_:g}", TXT_S, color=MUTED)
    lbl(ds, X3 + bw_ + 14.0, Y3 - 6.0, "[M low]; ON THE RECESS FLOOR;", TXT_S, color=MUTED)
    lbl(ds, X3 + bw_ + 14.0, Y3 - 3.0, "J OR FULL COLLAR: OPEN (OWNER)", TXT_S, color=MUTED)


def recess_u(hw, hb, rc, ht, n=12):
    """The column recess's front outline (u, h): a U of half-width hw about the column axis, floor at h hb, bottom
    corners R rc, the straight sides up to h ht (column_recess, rev L judges FID3-02), closed along the top."""
    t = np.linspace(0.0, 0.5 * math.pi, n)
    left = np.c_[-hw + rc - rc * np.cos(t), hb + rc - rc * np.sin(t)]
    right = np.c_[hw - rc + rc * np.sin(t), hb + rc - rc * np.cos(t)]
    return np.vstack([[(-hw, ht)], left, right, [(hw, ht)]])


def Y1_a_panel(h):
    from model import flightdeck as FD
    hub = I.yoke_hub(-1)
    xr = float(hub[0] + I.YOKE["hub_whd"][2])
    return np.array([(FD.face_x(float(hub[1]), float(hub[2]) + hh * 1e-3) - xr) * 1000.0 for hh in np.atleast_1d(h)])


# ============================================================================================ tables
CORNER_KEYS = (("shell_half", "shell (white cover), half"), ("insert_lower_half", "lower insert, half"),
               ("grip_out", "outboard grip aft face"), ("grip_in", "inboard grip aft face"),
               ("pad_out", "outboard pad"), ("pad_in", "inboard pad"), ("shield", "shield facet"),
               ("body_half", "black body, outboard half"), ("body_in", "black body, inboard half"))


def draw_tables(ds):
    x0, x1 = COL_X
    W = x1 - x0
    size = 2.1
    # ---- photo check (results of drawing.yoke_overlay; literal, dated)
    cols = [("PHOTO (CAMERA)", 46.0, "l"), ("COVER LM", 18.0, "c"), ("HEADS", 18.0, "c"),
            ("GRIP OUT: OUTER / SLOT (mean, max)", 52.0, "c"), ("GRIP IN: OUTER / SLOT (mean, max)", 52.0, "c"),
            ("PADS mean (max)", W - 186.0, "c")]
    rows = [tuple(r) for r in PHOTO_TABLE]
    y = table(ds, x0, 15.0, cols, wrap_rows(rows, [c[1] for c in cols], size),
              title="PHOTO CHECK (rev M): THE DRAWN SOLIDS RAY-CAST THROUGH THE PHOTO CAMERAS (mm, + = drawn wider)",
              size=size, row_h=3.3, font="label")
    # per-band signed maxima of the grip sides (judges FID2-02: not means)
    cw = (W - 24.0) / len(BAND_VIEWS)
    cols_b = [("SIDE", 24.0, "l")] + [(v_, cw, "c") for v_ in BAND_VIEWS]
    y = table(ds, x0, y + 2.0, cols_b, [tuple(r) for r in BAND_TABLE],
              title="GRIP SIDES PER BAND OF h: SIGNED MAX mm (h -50..-30 | -30..-10 | -10..10 | 10..30)", size=size,
              row_h=3.3, font="label")
    from drawing import sheet as S_
    for txt, col in ((PLANE_FIT, INK), (NECK, INK), (PHOTO_NOTE, MUTED)):
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
        if not cs:
            txt = ("NO CORNERS: one C2 run joined to the other half at u 0 (rev M, judges DR4-07); its first "
                   f"{int(D['body_top'][0 if key == 'body_half' else 1])} samples are the top edge (body_top)")
        rows.append((nm, f"{len(P)}", txt))
    E = D["edges"]
    rows += [("insert corners", "-", "; ".join(f"{k} R {v:g}" for k, v in D["insert_corners"])),
             ("cover edges", "-", f"perimeter R {float(E[0]):g}; arm lower R {float(E[1]):g}; foot underside R "
                                  f"{float(E[2]):g}; tip facet corners R {float(E[3]):g}"),
             ("grip edges", "-", f"frame roll R {float(D['grip_edges'][0]):g}; forward R {float(D['grip_edges'][1]):g} "
                                 f"[E] capped at {float(D['grip_edges'][2]):g} x the inscribed half-width; heel R "
                                 f"{float(D['heel'][2]):g}; trim face R {float(D['head_out'][6]):g}; pad step crisp, "
                                 f"groove {float(D['pad_section'][4]):g} x {float(D['pad_section'][5]):g}, bead "
                                 f"{float(D['pad_section'][3]):g}"),
             ("body edges", "-", f"rounds in order: sides x aft face R {float(D['body_form'][3]):g}, x top plane R "
                                 f"{float(D['body_form'][3]):g}, x forward face R {float(D['body_form'][4]):g} [E] easing to "
                                 f"R {float(D['body_form'][5]):g} under the foot, R {float(D['body_form'][7]):g} behind the "
                                 f"arms / necks [E]; under the foot the side draft's offset capped at "
                                 f"{float(D['body_form'][8]):g} [E]; AFCS boss aft edge R "
                                 f"{float(D['afcs_boss'][2]):g}, back edge R {float(D['afcs_boss'][5]):g}, blend R "
                                 f"{float(D['afcs_boss'][3]):g}"),
             ("moulding", "-", f"body + grips joined by a ROLLING-BALL round R {float(D['neck'][3]):g} (none where "
                               "their faces run flush); then each pad's pocket, groove and bead (pad_finish); the "
                               f"web's aft face on the trim face's plane {float(D['web'][0]):g} below it, joined to the "
                               f"grip plane over {float(D['web'][1]):g}; the low neck's aft face onto the shield facet's "
                               f"plane {float(D['neck_in'][2]):g} below it over |u| {float(D['neck_in'][0]):g}-"
                               f"{float(D['neck_in'][1]):g}; body top line a C2 cubic"),
             ("head zone out / in", "-", "aft side: prism trimmed {0:g} inside the head above h {1:g} / {2:g}, drafted "
                                        "{3:g} / {4:g} per mm below from a bend of R {5:g}, cut R {6:g}; head chamfer R "
                                        "{7:g}, floor R {8:g} at h {9:g} / {10:g}; head-to-prism R {11:g}; then walls "
                                        "(aft edge R 1.5 -> {12:g}) and forward face (R 11 capped -> {13:g}; over the head's top onto it R {13:g}); shield "
                                        "facet edge R {14:g}, its directrix tangent at the widest points (no corner)".format(
                 *[float(x) for x in (D['head_zone'][0][1], D['head_zone'][0][0], D['head_zone'][1][0],
                                      D['head_zone'][0][2], D['head_zone'][1][2], D['head_zone'][0][10],
                                      D['head_zone'][0][3], D['head_zone'][0][6], D['head_zone'][0][5],
                                      D['head_zone'][0][4], D['head_zone'][1][4], D['head_zone'][0][9],
                                      D['head_zone'][0][8], D['head_zone'][0][7], D['shield_edge'][0])])),
             ("cover features", "-", f"crown soft break R {float(D['crown'][4]):g}; top land C1 chamfer "
                                     f"{float(D['crown'][2]):g} x {float(D['crown'][3]):g}; TCS seat "
                                     f"{float(D['tcs_seat']):g} deep")]
    cols2 = [("OUTLINE", 46.0, "l"), ("N", 9.0, "c"), ("CORNERS: SAMPLE #, (u, h), RADIUS (curve_law)", W - 55.0, "l")]
    y = table(ds, x0, y + 1.0, cols2, wrap_rows(rows, [c[1] for c in cols2], size),
              title="CORNERS & RADII (every other sample is on a C2 spline); NO OTHER EDGE IS SHARP", size=size,
              row_h=3.3, font="label")
    from model import yoke_checks as YC
    acc = YC.summary_lines()
    cap = G.capped_fillets()
    nts = ["CURVE LAW (rev M text, judges DR4-03): each outline split at its corner samples into runs, each run a C2 "
           "cubic spline on centripetal knots ('natural' ends at corners, periodic for a closed outline without "
           f"corners), {float(D['curve_law'][0]):g} sampling (arcs too); corners R 0 sharp, R > 0 a tangent fillet (cubic Bezier arc; tangent length R "
           "tan(th/2) capped at 0.45 of the shorter run -- " + ("capped: " + "; ".join(
               f"{c_[0]} {c_[1]} R {c_[2]:g} -> {c_[3]:.1f}" for c_ in cap) if cap else "none capped") +
           "); YOKE_DESIGN curve_law; the solids use the EXACT distance to these polylines (beyond 0.3 mm a C2 "
           "B-spline of exact node distances, blended C2).",
           "ACCEPTANCE (model/yoke_checks.py, judges DR2-01..04, DR4-01 / 02): " + "; ".join(acc) + ".",
           "SECTIONS: exact contours of the solids (model/yoke_geom.py) on the cutting planes; the black body and the "
           "grips are one moulding (a rolling-ball round R 3), the white cover a separate part, the leather pad "
           "hatched apart (its 3.0 layer [E]); where a section is clipped to its window the cut edge is a thin "
           "phantom break line.",
           "Sources per value: the [M] / [E] / [S] tags of YOKE_DESIGN (printed in model/interior.py)."]
    notes(ds, x0, y + 1.0, x1, nts, title="NOTES", size=size, line_h=2.9)
    from drawing.interior_sheet import revisions_block
    import drawing.interior_sheet as IS
    saved = IS.SHEET
    IS.SHEET = SHEET
    try:
        # rev F: six rows -- 1.9 high (2.1 to rev E) to stay clear of the title block
        revisions_block(ds, x0, 470.0, x1, size=1.9, title_size=2.2, rows=REVISIONS)
    finally:
        IS.SHEET = saved


# rev M photo check, python3 -m drawing.yoke_overlay 2026-10-05 (refs/cache/overlays/yoke/deviations.json): cover
# landmarks mean / max (the pose fit), heads (trim face / push-button cap: checked, not fitted), grip silhouette
# rows per side (mean, signed max; + = drawn wider), pads vs traces mean (max); BAND_TABLE the signed max per band
# of h on the grip axis (judges FID2-02: maxima per band, not means); generated from deviations.json (6 fitted
# views; the AOPA press photo is check-only and not tabled, judges FID3-01)
PHOTO_TABLE = (
    ('P1046408 pilot (panel_408)', '1.4 / 2.7', '2.1 / 1.4', '+0.2, +3.9 / +1.0, +5.0', '+0.4, -5.8 / -1.8, -4.2', 'out 0.7 (2.5); in 0.6 (1.3)'),
    ('P1046408 co-pilot (panel_408)', '1.8 / 3.9', '2.9 / 1.0', '+1.1, +6.6 / +0.7, +2.1', '-0.4, -2.8 / +0.1, +3.3', 'out 1.7 (3.4); in 0.8 (1.9)'),
    ('P1046410 pilot', '0.8 / 1.6', '5.4 / 0.7', '-0.5, -6.9 / +0.2, -6.1', '-0.6, -7.6 / +2.9, +6.2', '-'),
    ('Mexico press, pilot', '1.7 / 3.9', '1.7 / 2.3', '+2.3, +5.5 / +0.7, +1.2', '-1.9, -7.8 / +0.4, +1.3', 'in 1.9 (5.1)'),
    ('Mexico press, co-pilot', '1.9 / 3.1', '0.9 / 0.6', '+0.3, +6.7 / +0.5, +2.6', '+1.7, +4.8 / -3.9, -6.8', 'out 1.1 (2.7)'),
    ('P1046409 co-pilot (two-view camera)', '1.0 / 2.1', '6.8 / 2.7', '-2.1, -7.7 / +0.5, +9.8', '+0.7, +7.8 / -2.9, -7.4', 'out 1.7 (4.3); in 3.4 (6.9)'),
    ('rev L, P1046408 pilot (judges r4)', '1.4 / 2.7', '2.1 / 1.4', '+0.3, +4.6 / +1.1, +6.6', '+0.4, +6.2 / -1.8, -4.2', 'out 0.7; in 0.6'),
)
BAND_TABLE = (   # signed max per band of h (axis), mm: (-50..-30, -30..-10, -10..10, 10..30)
    ('OUT SLOT', '+5.0 +1.9 +1.1 +0.4', '+1.9 +2.1 +0.8 +0.5', '+5.2 +1.9 -1.3 -6.1', '  .   . +1.2 +0.9', '+2.6 +2.3 -1.0 -1.6', '+9.8 +1.6 -0.8 -5.1'),
    ('OUT OUTER', '+2.8 -0.8 -0.3 -0.8', '+3.6 +1.1   .   .', '-4.4 +3.1 -1.5 -0.6', '  .   .   .   .', '-2.1   . -5.5 -0.7', '-7.1 +5.8 -4.7 -7.7'),
    ('IN SLOT', '-2.5 -4.2 -4.1 -1.8', '-0.8 -2.3 +1.8 +3.3', '+2.4 +3.4 +5.4 +6.2', '  . +0.3 +1.3 +1.0', '  . -5.3 -3.2 -6.8', '-7.4 -5.0 -7.3 +1.1'),
    ('IN OUTER', '-5.8 -5.2 -1.1 +0.9', '-2.8 -2.1 -0.9 -1.0', '-5.3 -7.6 -6.5 +1.2', '+6.4 -7.8 -6.5 -7.2', '+4.8 +2.0 +2.5 +2.2', '+7.8 -6.2 -7.0 -6.5'),
)
BAND_VIEWS = ('P408 L', 'P408 R', 'P410 L', 'MEX L', 'MEX R', 'P409 R')
PLANE_FIT = ("GRIP PLANES (rev L, judges FID3-01): rake / toe / a0 / walls / depth fitted per grip to the curated rows and "
             "pad traces of 6 views -- P1046408 L / R, P1046410, Mexico L / R and P1046409 (posed this round: a two-view "
             "camera with panel_408, 25° from inboard) -- with the front outline held: outboard 20.4° / 6.9° / -4.4 / "
             "0.64, depth 30 / 27 / 22 at h -47 / 0 / 45; inboard 21.3° / 16.7° / -6.1 / 0.04 (its depth above h 0 "
             "unconstrained: no view sees the inboard forward face).  Table: 20 / 18 / -3.75, -6.0 / 0.6, 0 / 27.5 at "
             "the bottom, 27 above.  Outboard cost +7 % at rake -2.5°, +8 % at a0 +/-5, +10 % at a bottom depth +/-4; the "
             "TOE is weak (7..22 within +7 %, inboard 0..26 within the noise; open point 2 of L6Y).  The AOPA views are "
             "CHECK ONLY (one radial term; the co-pilot outer -11 / -22, slot "
             "-12 / -15, pad 9.5): not fitted, not tabled.  Rev M (judges FID4-05): that co-pilot camera is EXTRAPOLATED from "
             "the pilot-yoke solution -- not a degenerate pose; its re-calibration on the panel round the co-pilot yoke "
             "is open, the toe / depth law / head depths stay [M weak].")
NECK = ("INBOARD NECK (criterion, P1046408): the drawn moulding's top edge vs the strongest photo edge per pixel column, arm "
        "tip to head -- pilot mean -1.3, |mean| 2.3, max -7.4 mm (against the red placard; the max where the edge turns "
        "vertical under the head, ill-posed per column); co-pilot -4.6, max -7.5: there the search locks onto the PFD's "
        "text rows above the neck (overlay inspected: the drawn edge lies on the photo's neck, dark on dark).  Rev L "
        "raised the last three samples 0.6-2.2 mm (body_in).")
PHOTO_NOTE = ("Pose per photo fitted to the COVER landmarks only (TCS, AFCS, badge, step ends, lower-insert corners, "
              "foot; P1046409 with its own picks); heads, grips, pads, neck and shell are checks.  Grip rows: the "
              "CURATED photo silhouettes -- auto edges per image row in the near views with the panel recesses masked, "
              "the inboard slot sides hand-traced and snapped past the J band / panel seam, P1046409 traced at 4x; "
              "slot rows above h 24 (the arm's underside, not the grip) not scored -- against the ray-cast grip's own "
              "hits (part-labelled), per image row, h on the grip axis.  The band maxima below h -37 are the rows that "
              "cut the grips' rounded bottom ends (1 mm of height reads 3-10 mm of width there); above it the row "
              "medians are 0.5-0.7 (outboard slot), 0.3-2.6 (outer sides), 0.4-3.5 (inboard slot), 90 % of the rows "
              "within 1-6.6.  Overlays: refs/cache/overlays/yoke (private).")
