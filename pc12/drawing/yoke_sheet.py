"""
Sheet L6Y -- PC-24-STYLE CONTROL YOKE, VIEWS (PC12-L6Y), drawn from model/interior.py YOKE_DESIGN (rev K) through the
solids of model/yoke_geom.py (drawing/yoke_draw.py): every view is an exact projection of the solids (silhouettes =
contours of the solids' minimum along the view direction), every section an exact cut.  Its companion sheet L6Y2
(drawing/yoke_sheet2.py) carries the centreline / arm / grip sections, the heads, the switches, the column and the photo
check.  Nothing comes from a mesh or a photo: the photo overlays are separate and git-ignored
(python3 -m drawing.yoke_overlay -> refs/cache/overlays/yoke).

    python3 -m drawing.master L6Y L6Y2

A1, first-angle, yoke-local millimetres (u outboard, h up from the hub centre = the column axis, a aft of the aft face
at the insert step).  The PILOT yoke is drawn; the co-pilot yoke is its mirror image (switches outboard on both).
  FRONT ELEVATION (1:1, looking forward, as the pilot sees it), SIDE ELEVATION (1:1, from outboard), VIEW FROM ABOVE
  (1:1), SECTION B-B (h 48), tables: items & finishes, main dimensions, the knee / roll check (L6B) rev H -> I -> J,
  notes, open points, revisions.  NO MARKINGS: the badge is an abstract winged plate, legends are tick strokes.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from drawing import master as M  # noqa: E402
from drawing.yoke_draw import (D, I, G, TXT, TXT_S, WHITE, SILVER, SMOKE, BLACK, BODY, LEATHER, RED, GLOSS,  # noqa
                               SWITCH, HID, W_CREASE, W_TAN, INK, MUTED, PAPER, ACCENT, W_OBJ, W_FINE, W_THIN, CHAIN,
                               PHANTOM, table, view_title, notes, mkview, poly, line, circle, circ, lbl, dim, leader,
                               balloon, centre_mark, hatch_poly, break_line, ticks, wrap_rows, rocker_halves, hexagon,
                               trim_frame, shield_frame, on_frame, front_to_plane, VIEWPROJ, tcs_centre3,
                               afcs_centre3, face_normal3, top_land_line, crown_crease, heel_line, views, draw_parts,
                               draw_section, tangent_edges, ordinates, clear_anchor, clear_boxes,
                               vline_gapped, hline_gapped)

SHEET = dict(id="L6Y", title="CONTROL YOKE - VIEWS", subtitle="PC-24-STYLE CONTROL YOKE - VIEWS", size="A1",
             scale="AS SHOWN", rev="C", order=62, sheet_no="1 OF 2", dwg="PC12-L6Y")
REVISIONS = (
    ("A", "2026-10-05", "first issue (owner 2026-10-05: 'the yoke isn't quite right especially if you look at the "
                        "details'): yoke re-measured on 8 PRO photos; YOKE_DESIGN rev I replaces the rev H outline"),
    ("B", "2026-10-05", "rev J (judges r1): the yoke as solids (model/yoke_geom.py) -- every view / section exact; curve "
                        "law + corner tables; one body with an outboard web and an inboard LOW NECK (open notch under "
                        "the head); pads with diagonal tops in a raised 2 mm frame, rolled heel lip; grips refitted "
                        "per grip (toe 18 / 18) on 4 pad views; ROUND trim face and SHIELD facet heads, triangulated "
                        "switch centres; crown / arm tops 1.7 lower (landmark-pose frame), top land, crown crease; "
                        "body top falling forward 35 deg; inserts flush; AFCS round boss, hex button collar, mirrored "
                        "rocker lobes; sheet L6Y2 added (sections, heads, switches, column, photo check)"),
    ("C", "2026-10-05", "rev K (judges r2): exact 2-D distance fields (no raster), Stage-3 surface route + acceptance "
                        "checks; grip walls fore-aft (outboard 0.6) -- slot-side and heel silhouettes on the curated "
                        "photo data; forward-edge R capped, PCHIP depth, heel lip R 4, pad groove + bead built; body top "
                        "42 deg from horizontal, top-to-front R 8; the web held under the trim face; AFCS boss, TCS, "
                        "rocker, hex button as solids; TCS button proud; crown soft break R 20; grip planes JOINT-FITTED "
                        "to 7 views (5 confirm the table +/-3 deg / +/-3-5 mm; the AOPA photo disagrees: open); "
                        "outboard heel corner pulled in; ordinate dimensions, cutting planes, detail circles, all "
                        "values computed"),
)
TRIM_COL = "#23292D"
FR_O = (202.0, 134.0)       # front elevation: sheet position of the hub centre (1:1)
SD_O = (508.0, 134.0)       # side elevation: (a 0, h 0) (1:1)
TP_O = (202.0, 352.0)       # view from above: (u 0, a 0) (1:1), forward up
BB_O = (500.0, 342.0)       # section B-B: (u 0, a 0), forward up
COL_X = (592.0, 826.0)      # right-hand column (tables)
GRIP_SECTION_H = (-30.0, -10.0, 14.0, 40.0)


def make_views(ds):
    v = {}
    v["front"] = ds.add_view(mkview("front", "yz_aft", -1, -1, FR_O, 1.0,
                                    "front elevation of the PILOT yoke looking forward: (u, h), u outboard = sheet left"))
    v["side"] = ds.add_view(mkview("side", "xz", 1, -1, SD_O, 1.0, "side elevation from outboard (port for the pilot "
                                                                    "yoke), nose left: (a, h)"))
    v["top"] = ds.add_view(mkview("top", "xy", -1, 1, TP_O, 1.0, "from above, forward up: (u, a), u outboard = left"))
    v["secB"] = ds.add_view(mkview("sec_B", "xy", -1, 1, BB_O, 0.5, "section B-B at h 48 from above, (u, a), "
                                                                      "forward up, outboard left"))
    return v


def draw(ds):
    v = make_views(ds)
    ds.frame_and_title(fields=dict(date="2026-10-05"))
    ctx = context()
    draw_front(ds, v["front"])
    front_annotations(ds, v["front"])
    draw_side(ds, v["side"])
    draw_top(ds, v["top"])
    draw_secB(ds, v["secB"])
    draw_tables(ds, ctx)
    ds.log.append(f"knee / roll (rev K): {ctx['summary']}")


# ============================================================================================ knee context
REV_H_KNEES = dict(p95m=(37.6, -18.9, 17.5, 5.0, -10.6, -1.0), p50m=(50.4, -13.1, 25.0, 10.0, 5.2, 0.0),
                   p5m=(50.6, -21.0, 22.5, 10.0, 20.5, 7.5), p5f=(76.1, 4.9, 87.5, 27.5, 55.0, 25.0))
REV_I_KNEES = dict(p95m=(35.3, -18.5, 17.5, 2.5, -12.7, -1.0), p50m=(48.0, -13.7, 25.0, 10.0, 3.0, 0.0),
                   p5m=(47.6, -21.4, 22.5, 10.0, 18.3, 7.5), p5f=(78.0, 0.4, 87.5, 25.0, 52.7, 25.0))
REV_J_KNEES = dict(p95m=(39.5, -19.0, 15.0, 5.0, -9.0, 0.0), p50m=(52.0, -14.0, 22.5, 10.0, 7.0, 0.0),
                   p5m=(51.0, -22.0, 22.5, 10.0, 22.0, 0.0), p5f=(81.0, 0.0, 87.5, 25.0, 56.0, 0.0))
# L6B rev H / rev I / rev J (2026-10-05): legs to the yoke wings level / full roll sweep (mm), roll to contact / keeping 25
# (deg), full rudder wings level (mm), full rudder roll to contact (deg)


def context():
    r = I.crew_checks(-1)
    occ = r["occ"]
    rows = {}
    for k in ("p95m", "p50m", "p5m", "p5f"):
        o = occ[k]
        rows[k] = (1000 * float(o["yoke_pitch"]), 1000 * float(o["yoke_sweep"]), float(o["roll_contact"]),
                   float(o["roll_clear"]), 1000 * float(o["rud_pitch"]), float(o["rud_roll_contact"]))
    o = rows["p95m"]
    return dict(knees=rows, summary=f"95th wings level {o[0]:.1f} mm, contact from {o[2]:.1f} deg, keeping 25 mm to "
                                    f"{o[3]:.1f} deg; full rudder {o[4]:.1f} mm")


# ============================================================================================ head pieces (3-D)
def trim_pieces():
    """3-D (u, h, a) pieces of the trim head's face: face outline, ring, lune slot lines, ticks, rocker lobes."""
    fr = trim_frame()
    R = 0.5 * float(D["head_out"][2])
    od = float(D["trim"][2])
    lune, r0, r1, _ = (float(x) for x in D["trim_lunes"])
    lg = D["legends"][2]
    out = dict(face=on_frame(fr, circle((0, 0), R, 97)[:-1]), ring=on_frame(fr, circle((0, 0), 0.5 * od, 97)[:-1]))
    yl = 0.5 * od - lune
    out["slot"] = [on_frame(fr, [(-0.5 * od + 2.0, s * yl), (0.5 * od - 2.0, s * yl)]) for s in (-1, 1)]
    tk = []
    for a0, a1 in ((lg[2], lg[3]), (lg[2] + 180.0, lg[3] + 180.0)):
        tk += [on_frame(fr, T) for T in ticks((0.0, 0.0), r0, r1, a0, a1, int(lg[4]))]
    out["ticks"] = tk
    out["rocker"] = [on_frame(fr, h) for h in rocker_halves()]
    return out


def button_pieces():
    """3-D pieces of the inboard head: shield facet outline, hex collar, cap, ticks (co-pilot sense, u < 0)."""
    fr = shield_frame()
    b = D["button"]
    c3 = fr[0]
    out = dict(shield=on_frame(fr, G.shield_outline()))
    bc = front_to_plane(fr, [(-float(b[0]), float(b[1]))])[0]
    off2 = np.array([np.dot(bc - c3, fr[2]), np.dot(bc - c3, fr[3])])
    out["centre2"] = off2
    out["hex"] = on_frame(fr, hexagon(float(b[2])) + off2)
    out["cap"] = on_frame(fr, circle(off2, 0.5 * float(b[3]), 61)[:-1])
    lg = D["legends"][3]
    out["ticks"] = [front_to_plane(fr, T) for T in ticks((-float(b[0]), float(b[1])), lg[0], lg[1], lg[2], lg[3],
                                                          int(lg[4]))]
    return out


# ============================================================================================ front elevation
def draw_front(ds, v):
    F = I.yoke_front_mm()
    poly(ds, v, F["body"], W_OBJ, fill=BLACK)
    for S_, pad, g in ((F["grip_out"], F["pad_out"], "out"), (F["grip_in"], F["pad_in"], "in")):
        poly(ds, v, S_, W_OBJ, fill=BLACK)
        for L in tangent_edges(g, 1.0 if g == "out" else -1.0):         # where the frame's R 1.5 roll starts
            line(ds, v, L, W_TAN, color="#8D969C")
        poly(ds, v, pad, W_FINE, fill=LEATHER, color="#1E2326")
    tp = trim_pieces()
    poly(ds, v, VIEWPROJ(tp["face"], "front"), W_CREASE, fill="#2B3135", color="#B9C0C5")
    poly(ds, v, VIEWPROJ(tp["ring"], "front"), W_FINE, fill=TRIM_COL, color="#AEB6BB")
    for L in tp["slot"]:
        line(ds, v, VIEWPROJ(L, "front"), W_TAN, color="#9AA3A9")
    for T in tp["ticks"]:
        line(ds, v, VIEWPROJ(T, "front"), 0.2, color="#E8EAEC")
    for h in tp["rocker"]:
        poly(ds, v, VIEWPROJ(h, "front"), W_THIN, fill=SWITCH, color="#C9CFD3")
    bp = button_pieces()
    poly(ds, v, VIEWPROJ(bp["shield"], "front"), W_CREASE, fill="#2F363A", color="#B9C0C5")
    poly(ds, v, VIEWPROJ(bp["hex"], "front"), W_THIN, fill=TRIM_COL, color="#AEB6BB")
    poly(ds, v, VIEWPROJ(bp["cap"], "front"), W_THIN, fill="#3A4247", color="#C9CFD3")
    for T in bp["ticks"]:
        line(ds, v, VIEWPROJ(T, "front"), 0.2, color="#E8EAEC")
    poly(ds, v, F["shell"], W_OBJ, fill=WHITE)
    poly(ds, v, F["insert_upper"], W_CREASE, fill=SILVER)
    poly(ds, v, F["insert_lower"], W_CREASE, fill=SMOKE)
    line(ds, v, F["step"], W_FINE)
    for L in top_land_line():
        line(ds, v, L, W_TAN, color="#7E878D")
    cc = crown_crease()
    if cc is not None:                                                   # a soft break (blend R crown[4]), phantom
        line(ds, v, cc, W_THIN, dash=PHANTOM, color="#7E878D")
    poly(ds, v, F["badge"], W_THIN)
    poly(ds, v, F["badge_border"], W_THIN)
    for L in F["badge_lines"]:
        line(ds, v, L, W_THIN)
    draw_tcs(ds, v)
    draw_afcs(ds, v)
    from cad import sdf2d
    fp = VIEWPROJ(tp["face"], "front")
    go = F["grip_out"]
    keep = np.r_[True, np.linalg.norm(np.diff(go, axis=0), axis=1) > 1e-6]
    go = go[keep]
    if np.linalg.norm(go[0] - go[-1]) < 1e-6:
        go = go[:-1]
    m = float(np.max(sdf2d.polygon(fp[:, 0], fp[:, 1], go)))
    ds.log.append(f"trim face inside the outboard head's front silhouette: max signed distance {m:+.2f} mm "
                  "(negative = inside; judges D6)")


def draw_tcs(ds, v, k=1.0, c=None):
    u, h, od, bd = (float(x) for x in D["tcs"][:4])
    c = np.array([u, h]) if c is None else np.asarray(c, float)
    r_in, r_out = (float(x) for x in D["tcs_profile"][5:7])
    circ(ds, v, c, od, W_FINE, fill=GLOSS)
    circ(ds, v, c, 2 * r_out, W_THIN, color="#7E878D")
    circ(ds, v, c, 2 * r_in, W_THIN, color="#7E878D")
    circ(ds, v, c, bd, W_THIN, fill="#2B3135", color="#9AA3A9")
    lg = D["legends"][0]
    for T in ticks(c, lg[0], lg[1], lg[2], lg[3], int(lg[4])):
        line(ds, v, T, 0.25 * k, color="#E8EAEC")


def draw_afcs(ds, v, k=1.0, c=None):
    u, h, cd, ch, bd = (float(x) for x in D["afcs"][:5])
    c = np.array([u, h]) if c is None else np.asarray(c, float)
    circ(ds, v, c, bd, W_THIN, fill=GLOSS)
    lg = D["legends"][1]
    for T in ticks(c, lg[0], lg[1], lg[2], lg[3], int(lg[4])):
        line(ds, v, T, 0.22 * k, color="#E8EAEC")
    circ(ds, v, c, cd, W_FINE, fill=RED)


ITEMS = (  # item, part, material (render/lookdev name), finish [source]
    (1, "WHITE COVER (Y SHELL)", "yoke_white", "gloss clear-coat white, neutral-cool (0.77 / 0.78 / 0.80), fine "
                                               "pearl; R 1 edges, top land [M]"),
    (2, "UPPER INSERT = CROWN, BADGE", "yoke_silver (new)", "satin aluminium 0.62, metallic 0.85, rough 0.30; flush, "
                                                            "0.6 x 0.5 grooves [M]"),
    (3, "LOWER INSERT", "yoke_silver_dark (new)", "smoke silver 0.30, metallic 0.85, rough 0.34; flush [M]"),
    (4, "BLACK BODY (RIM, WEB, NECK)", "grip_black", "satin black, rough 0.42: crisp edge highlights; R 2 aft edge [M]"),
    (5, "GRIP (2) WITH FRAME, HEEL LIP", "grip_black", "satin black; 2.0 frame R 1.5, heel lip 3 proud R 4 [M]"),
    (6, "LEATHER PAD (2)", "leather_black", "charcoal 0.05, rough 0.58, 1.1 pebble grain, ~1 creases, 2.5 below the "
                                            "frame, groove 1.0 x 0.5 + bead 0.4 at its edge [M / E]"),
    (7, "TCS BUTTON", "gloss_black / black", "gloss black bezel 1 proud [E], satin domed button 2 proud of it "
                                             "[M low]"),
    (8, "AFCS DISCONNECT", "button_red (new) / black", "red cap 0.70 / 0.035 / 0.04, clear coat 0.3, NOT emissive, "
                                                       "on a black boss [M]"),
    (9, "PITCH TRIM ON ROUND FACE", "black / legend_white", "satin black face, ring + rocker, tick legends 0.80 [M]"),
    (10, "PUSH BUTTON ON SHIELD", "black", "satin black hex collar, smooth cap, centre dimple [M]"),
    (11, "COLUMN", "metal_dark", "satin dark metal, dia 44 [E] (never seen)"),
    (12, "COLUMN SURROUND (PANEL)", "pedestal_gunmetal", "satin dark grey J band 23 wide + dished recess [M / E]"),
)


def P_v(v, P):
    return [tuple(q) for q in v(np.asarray(P, float))]


def front_annotations(ds, v):
    """Centre lines, ordinate dimensions from h 0, horizontal dimensions, cutting planes (B-B, Z-Z, K-K, P-P, Q-Q,
    A1-A4 / N1-N4), detail circles (D-H, P, S), item balloons in rows above / below, radius call-outs (radii printed
    from the table's corner lists: judges D3 / DR2-06 / DR2-08)."""
    X0, Y0 = v.pt(0.0, 0.0)
    (ub, hb), (ut, ht) = D["grip_axis"]
    for d in (1, -1):
        t0, t1 = -0.07, 1.07
        line(ds, v, [(d * (ub + t0 * (ut - ub)), hb + t0 * (ht - hb)), (d * (ub + t1 * (ut - ub)), hb + t1 * (ht - hb))],
             W_THIN, CHAIN, color=MUTED)
    lbl(ds, X0 + 1.2, Y0 - 110.5, "CL YOKE  BL -375 (CO-PILOT +375)", TXT_S, color=MUTED)
    lbl(ds, X0 - 97.0, Y0 - 1.6, "h 0 = COLUMN AXIS / ROLL PIVOT", TXT_S, color=MUTED)
    lbl(ds, X0 - 97.0, Y0 + 2.0, "WL 1845", TXT_S, color=MUTED)
    F = I.yoke_front_mm()
    sh = np.asarray(D["shell_half"], float)
    go, gi = F["grip_out"], F["grip_in"]
    # ---- horizontal dimensions
    u_tip = float(sh[22, 0])
    dim(ds, v.pt(u_tip, 51.0), v.pt(-u_tip, 51.0), Y0 - 80.0, f"{2 * u_tip:.1f} ARM TIPS")
    uo, ui = float(go[:, 0].max()), float(-gi[:, 0].min())
    ho = float(go[np.argmax(go[:, 0]), 1])
    hi = float(gi[np.argmin(gi[:, 0]), 1])
    dim(ds, v.pt(uo, ho), v.pt(-ui, hi), Y0 + 80.0, f"{uo + ui:.1f} GRIPS OVERALL ({uo:.1f} + {ui:.1f}), FRONT "
                                                  "SILHOUETTE")
    s50 = float(np.interp(-50.0, sh[::-1, 1], sh[::-1, 0]))
    dim(ds, v.pt(s50, -50.0), v.pt(-s50, -50.0), Y0 + 73.0, f"{2 * s50:.1f} STEM @ h -50")
    tb_ = ds.text_bands(pad=0.6)
    vline_gapped(ds, X0, Y0 - 112.0, Y0 + 70.0, W_THIN, CHAIN, tb_)
    hline_gapped(ds, X0 - 150.0, X0 + 150.0, Y0, W_THIN, INK, tb_, dash=CHAIN)
    # ---- item balloons: a row above and a row below the view
    # (co-pilot (u, h) of the feature, sheet x offset of the balloon from X0, row): leaders nearly vertical
    B = [((101.0, 88.0), -96.0, "up", 9), ((80.0, 64.0), -86.0, "up", 4), ((58.5, 58.0), -60.0, "up", 7),
         ((30.0, 45.0), -32.0, "up", 1), ((-16.0, 58.0), 18.0, "up", 2), ((-106.3, 82.0), 112.0, "up", 10),
         ((130.0, -20.0), -132.0, "dn", 6), ((100.0, 5.0), -104.0, "dn", 5), ((60.6, 14.0), -62.0, "dn", 8),
         ((24.0, -45.0), -30.0, "dn", 4), ((-4.0, -12.0), 12.0, "dn", 3), ((-18.0, 0.0), 40.0, "dn", 11),
         ((-100.0, 5.0), 98.0, "dn", 5), ((-125.0, -20.0), 124.0, "dn", 6)]
    for P, dx, row, n in B:
        balloon(ds, v.pt(*P), (X0 + dx, Y0 - 103.0 if row == "up" else Y0 + 58.0), n)
    circ(ds, v, (0.0, 0.0), 44.0, W_THIN, dash=HID, color=MUTED)             # the column behind (hidden)
    # ---- detail circles: D-H (switches, heads, badge), P (heel, on P-P), S (A3's outer pad edge)
    tc = D["head_out"]
    for c, r, let, at in (((58.5, 51.4), 12.5, "D", (-1, -1)), ((60.6, 23.4), 13.0, "E", (-1, 1)),
                          ((float(tc[0]), float(tc[1])), 19.0, "F", (-1, -1)), ((-106.3, 76.0), 16.0, "G", (1, -1)),
                          ((0.0, 49.7), 25.0, "H", (1, -1))):
        X, Y = v.pt(*c)
        ds.cv.path(P_v(v, circle(c, r, 61)), W_THIN, (3.0, 1.0), closed=True)
        u_ = np.array(at, float) / math.hypot(*at)
        lbl(ds, X + (r + 2.6) * u_[0], Y + (r + 2.6) * u_[1], let, 4.0, "middle", weight=700)
    pb = float(G.pad_outline("out")[:, 1].min())
    M.detail_circle(ds, v, float(G.grip_axis_u(pb - 4.0)), pb - 4.0, 0.0105, "L", at=(-1.0, 1.0))
    xS = float(np.max(G.pad_outline("out")[np.abs(G.pad_outline("out")[:, 1] - GRIP_SECTION_H[2]) < 3.0, 0]))
    M.detail_circle(ds, v, xS, GRIP_SECTION_H[2], 0.0045, "S", at=(-1.0, 0.15))
    # ---- cutting planes (DR2-08)
    M.cutting_plane(ds, v, (150.0, 48.0), (-150.0, 48.0), "B", look=(0.0, 1.0), ext=1.5, length=6.0)
    M.cutting_plane(ds, v, (0.0, 70.0), (0.0, -66.5), "Z", look=(1.0, 0.0), ext=1.0, length=6.0)
    ang = math.radians(30.0)
    ea = np.array([-math.sin(ang), math.cos(ang)])
    pK = np.array([52.0, 45.0])
    lk = np.array([math.cos(ang), math.sin(ang)])                          # (u, h) of the arm axis, outboard-up
    M.cutting_plane(ds, v, tuple(pK - 15.0 * ea), tuple(pK + 19.0 * ea), "K", look=(lk[0], lk[1]), ext=1.5,
                    length=5.0)
    ax = np.array([ut - ub, ht - hb]) / math.hypot(ut - ub, ht - hb)
    nrm = np.array([ax[1], -ax[0]])
    for g, sg, let in (("out", 1.0, "P"), ("in", -1.0, "Q")):
        p0 = np.array([sg * ub, hb]) + np.array([sg * ax[0], ax[1]]) * (-6.0)
        p1 = np.array([sg * ut, ht]) + np.array([sg * ax[0], ax[1]]) * 11.5
        M.cutting_plane(ds, v, tuple(p0), tuple(p1), let, look=(1.0, 0.0), ext=1.0, length=5.0)
    for g, sg, lets in (("out", 1.0, "A"), ("in", -1.0, "N")):
        dvec = -np.array([sg * ax[0], ax[1]])                                # looking DOWN the axis
        dsheet = np.array([-dvec[0], -dvec[1]])
        for k, h in enumerate(GRIP_SECTION_H):
            cA = np.array([sg * float(G.grip_axis_u(h)), h])
            n_ = nrm * [sg, 1.0]
            ln_ = 28.0 if g == "out" else 25.0                         # N labels clear of the ladder
            p0, p1 = cA - ln_ * n_, cA + ln_ * n_
            P0, P1 = np.array(v.pt(*p0)), np.array(v.pt(*p1))
            ds.cv.line(tuple(P0), tuple(P1), W_THIN, CHAIN, color=MUTED)
            for E_ in (P0, P1):
                ds.cv.line(tuple(E_), tuple(E_ + 3.0 * (P1 - P0) / np.linalg.norm(P1 - P0) *
                                            (1 if E_ is P0 else -1)), 0.45)
                M._big_arrow(ds, E_ + 2.6 * dsheet / np.linalg.norm(dsheet), dsheet, length=3.2, head=(1.8, 1.0))
            X, Y = v.pt(*(p1 + 3.4 * n_))
            lbl(ds, X, Y, f"{lets}{k + 1}", 2.6, "middle", weight=700)
    # ---- ordinate dimensions from h 0 (DR2-06): outboard features left, inboard features right
    pk_o = go[np.argmax(go[:, 1])]
    pk_i = gi[np.argmax(gi[:, 1])]
    bo = go[np.argmin(go[:, 1])]
    bi = gi[np.argmin(gi[:, 1])]
    po, pi = F["pad_out"], F["pad_in"]
    to_, ah = D["tcs"], D["afcs"]
    tr_, bt_ = D["head_out"], D["button"]
    left = [(float(pk_o[0]), float(pk_o[1]), None), (float(tr_[0]), float(tr_[1]), None),
            (float(po[np.argmax(po[:, 1]), 0]), float(po[:, 1].max()), None), (float(sh[22, 0]), float(sh[22, 1]), None),
            (float(to_[0]), float(to_[1]), None), (float(ah[0]), float(ah[1]), None),
            (float(po[np.argmin(po[:, 1]), 0]), float(po[:, 1].min()), None), (float(bo[0]), float(bo[1]), None),
            (14.0, float(sh[-2, 1]), None)]
    right = [(float(pk_i[0]), float(pk_i[1]), None), (-float(bt_[0]), float(bt_[1]), None),
             (-float(pi[np.argmax(pi[:, 1]), 0]) if pi[:, 0].mean() > 0 else float(pi[np.argmax(pi[:, 1]), 0]),
              float(pi[:, 1].max()), None), (0.0, float(sh[0, 1]), None), (-12.9, float(D["step"][1][1]), None),
             (-8.0, float(np.min(F["insert_lower"][:, 1])), None),
             (float(pi[np.argmin(pi[:, 1]), 0]), float(pi[:, 1].min()), None), (float(bi[0]), float(bi[1]), None),
             (-10.0, float(np.min(F["body"][:, 1])), None)]
    ordinates(ds, v, left, X0 - 165.0, side=-1)
    bands_r = ordinates(ds, v, right, X0 + 160.0, side=+1)
    lbl(ds, X0 - 165.0, Y0 - 104.0, "h FROM THE", TXT_S, "middle", color=MUTED)
    lbl(ds, X0 - 165.0, Y0 - 101.0, "COLUMN AXIS", TXT_S, "middle", color=MUTED)
    # ---- radius call-outs (from the corner tables)
    cs = dict((int(a), b) for a, b in D["shell_half_corners"])
    E = D["edges"]
    cr = D["crown"]
    RN = [((-u_tip, 51.0), (X0 + 172.0, Y0 - 96.0), f"ARM TIP: {sh[22, 1] - sh[23, 1]:.1f} END + 45° FACETS",
           [f"corners R {cs[22]:g}"]),
          ((-50.0, 59.3), (X0 + 172.0, Y0 - 86.0), f"TOP LAND {float(cr[2]):g} x {float(cr[3]):g} (C1 CHAMFER)",
           ["crown + arm tops"]),
          ((-12.0, float(cr[0])), (X0 + 172.0, Y0 - 76.0), f"CROWN SOFT BREAK h {float(cr[0]):g}",
           [f"top {float(cr[1]):g}° fwd, blend R {float(cr[4]):g} [M low]"]),
          ((-33.7, 52.0), (X0 + 172.0, Y0 - 66.0), f"ARM JUNCTION R {cs[10]:g}", [f"crown chamfer R {cs[4]:g}"]),
          ((-55.0, 32.6), (X0 + 172.0, Y0 - 56.0), f"ARM LOWER EDGE R {float(E[1]):g}", None),
          ((-35.3, 10.0), (X0 + 172.0, Y0 - 48.0), f"SHELL PERIMETER R {float(E[0]):g}", ["0.45-0.95 blur [M]"]),
          ((-12.0, 3.6), (X0 + 172.0, Y0 + 8.0), f"STEP V {D['grooves'][1][0]:g} x {D['grooves'][1][1]:g}",
           ["inserts FLUSH"]),
          ((-136.4, 30.0), (X0 + 172.0, Y0 + 26.0), f"FRAME {float(D['grip_frame']):g}, ROLL R "
                                                    f"{float(D['grip_edges'][0]):g} (thin: its tangent edge)",
           [f"forward edges R {float(D['grip_edges'][1]):g} [E], <= {float(D['grip_edges'][2]):g} x half-width"]),
          ((-20.0, -55.3), (X0 + 172.0, Y0 + 44.0), f"FOOT CORNERS R {cs[45]:g}", [f"underside R {float(E[2]):g}"])]
    for P, T, t_, more in RN:
        T2 = tuple(clear_boxes(v.pt(*P), T, ds.text_bands(pad=0.3), reach=6.0))   # letters + ladder labels
        leader(ds, v.pt(*P), T2, t_, more, size=TXT_S, weight=500)
    view_title(ds, X0, Y0 + 90.0, "FRONT ELEVATION - PILOT YOKE",
               "LOOKING FORWARD, AS THE PILOT SEES IT (CO-PILOT YOKE = MIRROR IMAGE) - SCALE 1:1")
    lbl(ds, X0 - 150.0, Y0 + 84.0, "SECTIONS Z-Z, K-K, A1-A4 / N1-N4, PROFILES P-P / Q-Q, DETAILS D-H, J, L, S: SHEET "
                                   "L6Y2", TXT_S, color=MUTED)


# ============================================================================================ side elevation
def draw_side(ds, v):
    X0, Y0 = v.pt(0.0, 0.0)
    r = 1000.0 * float(I.YOKE["column_r"])
    depth = float(D["body_form"][0])
    a_brk = -depth - 26.0
    poly(ds, v, [(a_brk, r), (-depth + 4.0, r), (-depth + 4.0, -r), (a_brk, -r)], W_FINE, fill="#D9DCDF")
    break_line(ds, v, (a_brk, r + 3), (a_brk, -r - 3))
    S = views("u")
    draw_parts(ds, v, S, ("grip_in",), {"grip_in": "#6A7277"})
    draw_parts(ds, v, S, ("body",), {"body": BODY})
    draw_parts(ds, v, S, ("button",), {"button": "#4A5257"})            # on the far (inboard) head
    draw_parts(ds, v, S, ("cover",), {"cover": WHITE})
    draw_parts(ds, v, S, ("grip_out",), {"grip_out": BLACK})
    draw_parts(ds, v, S, ("trim",), {"trim": SWITCH})                    # on the near (outboard) head
    for p_ in ("cover", "body"):
        for C in S[p_]:
            if len(C) > 8:
                poly(ds, v, C, W_THIN, dash=HID, color="#AEB6BB")
    tp = trim_pieces()
    poly(ds, v, VIEWPROJ(tp["face"], "side"), W_FINE, color="#B9C0C5")
    bp = button_pieces()
    poly(ds, v, VIEWPROJ(bp["shield"], "side"), W_THIN, dash=HID, color=MUTED)
    T = math.tan(math.radians(float(D["face_tilt"])))
    fl = np.asarray(D["face_lower"], float)
    line(ds, v, [(0.0, float(fl[0, 0])), (-(104.0 - float(fl[0, 0])) * T, 104.0)], W_THIN, CHAIN, color=ACCENT)
    line(ds, v, [(0.0, -72.0), (0.0, 104.0)], W_THIN, CHAIN, color=MUTED)
    ds.cv.line(v.pt(a_brk - 4.0, 0.0), v.pt(34.0, 0.0), W_THIN, CHAIN)
    h0, a0 = G.grip_a0("out")
    R = math.tan(math.radians(G._gsel("grip_rake", "out")))
    line(ds, v, [(a0 + (h0 + 64.0) * R, -64.0), (a0 - (104.0 - h0) * R, 104.0)], W_THIN, CHAIN, color=ACCENT)
    X, Y = v.pt(-(104.0 - float(fl[0, 0])) * T, 104.0)
    lbl(ds, X + 1.0, Y - 1.6, f"AFT FACE {float(D['face_tilt']):.1f}° TOP FWD", TXT_S, color=ACCENT, weight=600)
    X, Y = v.pt(a0 + (h0 + 64.0) * R, -64.0)
    lbl(ds, X + 1.2, Y + 1.6, f"GRIP RAKE {G._gsel('grip_rake', 'out'):.0f}° [M +/-3]", TXT_S, color=ACCENT, weight=600)
    lbl(ds, X0 + 1.0, Y0 + 74.0, "a 0", TXT_S, color=MUTED)
    # ---- envelope from ALL parts (DR2-06)
    allc = [C for p_ in S for C in S[p_] if len(C) > 8]
    a_front = min(float(C[:, 0].min()) for C in S["body"])
    a_back = max(float(C[:, 0].max()) for C in allc)
    h_top = max(float(C[:, 1].max()) for C in allc)
    h_bot = min(float(C[:, 1].min()) for C in allc)
    who = max(((p_, float(C[:, 0].max())) for p_ in S for C in S[p_] if len(C) > 8), key=lambda r_: r_[1])[0]
    yb = Y0 + 84.0
    dim(ds, v.pt(a_front, -40.0), v.pt(0.0, -40.0), yb, f"{-a_front:.1f} BODY FWD")
    dim(ds, v.pt(0.0, -30.0), v.pt(a_back, -40.0), yb, f"{a_back:.1f} ({who.upper().replace('_', ' ')})", outside=True)
    dim(ds, v.pt(a_front, -40.0), v.pt(a_back, -40.0), yb + 7.0, f"{a_back - a_front:.1f} OVERALL DEPTH")
    h_cr = float(np.asarray(D["shell_half"])[0, 1])
    a_cr = float(G.face_a(h_cr))
    dim(ds, v.pt(a_cr, h_cr), v.pt(0.0, 2.1), Y0 - 104.0, f"{-a_cr:.1f} CROWN FWD OF a 0", outside=True)
    gout = max(S["grip_out"], key=len)
    a_hf = float(gout[:, 0].min())
    h_hf = float(gout[np.argmin(gout[:, 0]), 1])
    dim(ds, v.pt(a_hf, h_hf), v.pt(0.0, 2.1), Y0 - 111.0, f"{-a_hf:.1f} OUTBOARD HEAD FWD",
        outside=True)
    # ---- ordinate heights from h 0, named (the centre features; the front view carries the grips') + envelope
    items = [(a_back + 2.0, h_top, "TOP (HEAD)"), (a_cr, h_cr, "CROWN"),
             (float(G.face_a(56.0)), float(D["crown"][0]), "CROWN BREAK"),
             (0.0, float(D["step"][0][1]), "STEP V"),
             (float(G.face_a(-18.9)), float(np.min(I.yoke_front_mm()["insert_lower"][:, 1])), "LOWER INSERT"),
             (float(G.face_a(-56.0)), float(np.asarray(D["shell_half"])[-1, 1]), "FOOT (COVER)"),
             (a_front + 20.0, h_bot, "BOTTOM (BODY)")]
    from drawing.yoke_draw import ordinates
    ordinates(ds, v, items, X0 + 44.0, side=+1, min_gap=3.2)
    dim(ds, v.pt(a_back, h_top), v.pt(a_back, h_bot), X0 + 36.0, f"{h_top - h_bot:.1f} OVERALL HEIGHT", orient="v",
        outside=False)
    leader(ds, v.pt(float(tp["face"][:, 2].mean()), float(tp["face"][:, 1].mean())), (X0 - 70.0, Y0 - 100.0),
           f"TRIM FACE {float(D['head_out'][3]):g}° ABOVE AFT", [f"dia {float(D['head_out'][2]):g}, ring flush"],
           size=TXT_S)
    leader(ds, v.pt(3.5, -22.0), (X0 - 96.0, Y0 + 54.0), "CONVEX LOWER FACE", ["C1, tangent at the step"],
           size=TXT_S)
    gl = gout[gout[:, 1] < -25.0]
    if len(gl):
        k = int(np.argmax(gl[:, 0]))
        leader(ds, v.pt(float(gl[k, 0]), float(gl[k, 1])), (X0 - 96.0, Y0 + 66.0),
               f"HEEL LIP {float(D['heel'][1]):g} PROUD, R {float(D['heel'][2]):g}", ["(outboard grip)"], size=TXT_S)
    view_title(ds, X0 - 22.0, Y0 + 98.0, "SIDE ELEVATION", "FROM OUTBOARD, NOSE LEFT, NEUTRAL PITCH; a 0 = X 3700; "
                                                           "COLUMN BROKEN (L6Y2 DETAIL J) - 1:1")
    lbl(ds, X0 - 74.0, Y0 + 108.0, f"BODY (HIDDEN): TOP {float(D['body_form'][1]):g}° FROM THE HORIZONTAL, TOP-TO-FRONT "
                                   f"R {float(D['body_form'][6]):g}, DEPTH {depth:g} [E], FOOT R "
                                   f"{float(D['body_form'][5]):g} [E] (L6Y2 Z-Z)", TXT_S, color=MUTED)
    lbl(ds, X0 - 74.0, Y0 + 104.5, "GRIPS PROVISIONAL: RAKE / TOE / a0 FITTED TO 5 VIEWS [M +/-3° / +/-4° / +/-3-5]; "
                                   "THE AOPA PHOTO DISAGREES (OPEN POINT 2)", TXT_S, color=ACCENT, weight=600)


# ============================================================================================ view from above
def draw_top(ds, v):
    X0, Y0 = v.pt(0.0, 0.0)
    r = 1000.0 * float(I.YOKE["column_r"])
    depth = float(D["body_form"][0])
    a_brk = -depth - 24.0
    poly(ds, v, [(r, -depth + 4.0), (r, a_brk), (-r, a_brk), (-r, -depth + 4.0)], W_FINE, fill="#D9DCDF")
    break_line(ds, v, (-r - 3, a_brk), (r + 3, a_brk))
    S = views("h")
    draw_parts(ds, v, S, ("body",), {"body": BODY})
    draw_parts(ds, v, S, ("cover",), {"cover": WHITE})
    draw_parts(ds, v, S, ("grip_in", "grip_out"), {"grip_in": BLACK, "grip_out": BLACK})
    draw_parts(ds, v, S, ("trim", "button"), {"trim": SWITCH, "button": "#4A5257"})
    tp = trim_pieces()
    poly(ds, v, VIEWPROJ(tp["face"], "plan"), W_FINE, fill="#2B3135", color="#B9C0C5")
    poly(ds, v, VIEWPROJ(tp["ring"], "plan"), W_THIN, color="#AEB6BB")
    for h in tp["rocker"]:
        poly(ds, v, VIEWPROJ(h, "plan"), W_THIN, fill=SWITCH, color="#C9CFD3")
    bp = button_pieces()
    poly(ds, v, VIEWPROJ(bp["shield"], "plan"), W_THIN, color="#B9C0C5")
    for g, sg in (("out", 1.0), ("in", -1.0)):
        uu = np.array([float(G.grip_axis_u(14.0)) - 18.0, float(G.grip_axis_u(14.0)) + 18.0])
        aa = G.grip_plane_a(uu, 14.0, g) * 1.0
        line(ds, v, np.c_[sg * uu, aa], W_FINE, color=ACCENT)
        X, Y = v.pt(sg * uu.mean(), float(aa.mean()))
        leader(ds, (X, Y), (X + (-8.0 if sg > 0 else 8.0), v.pt(0, 34.0)[1]),
               f"AFT PLANE @ h 14: TOE-OUT {float(D['grip_toe'][0 if g == 'out' else 1]):g}° [M +/-4]", size=TXT_S,
               color=ACCENT)
    ds.cv.line((X0, Y0 - 96.0), (X0, Y0 + 19.0), W_THIN, CHAIN)
    ds.cv.line((X0 - 158.0, Y0), (X0 + 158.0, Y0), W_THIN, CHAIN, color=MUTED)
    lbl(ds, X0 + 159.0, Y0 - 1.6, "a 0", TXT_S, color=MUTED)
    lbl(ds, X0 + 2.0, Y0 - 94.0, "FWD", TXT_S, color=MUTED, weight=600)
    lbl(ds, X0 - 154.0, Y0 - 64.0, "OUTBOARD", TXT_S, color=MUTED, weight=600)
    lbl(ds, X0 + 154.0, Y0 - 64.0, "INBOARD", TXT_S, "end", color=MUTED, weight=600)
    body = max(S["body"], key=len)
    allc = [C for p_ in S for C in S[p_] if len(C) > 8]
    u0_, u1_ = min(float(C[:, 0].min()) for C in allc), max(float(C[:, 0].max()) for C in allc)
    a0_, a1_ = min(float(C[:, 1].min()) for C in allc), max(float(C[:, 1].max()) for C in allc)
    dim(ds, v.pt(float(body[:, 0].max()), 0.0), v.pt(float(body[:, 0].min()), 0.0), Y0 + 24.0,
        f"{float(body[:, 0].max() - body[:, 0].min()):.1f} BODY (NECKS)")
    dim(ds, v.pt(u1_, 0.0), v.pt(u0_, 0.0), Y0 + 31.0, f"{u1_ - u0_:.1f} OVERALL WIDTH (GRIP HEADS / SIDES)")
    dim(ds, v.pt(u0_, a0_), v.pt(u0_, a1_), X0 + 168.0, f"{a1_ - a0_:.1f} OVERALL DEPTH", orient="v")
    view_title(ds, X0, Y0 + 42.0, "VIEW FROM ABOVE", "FORWARD UP, PILOT YOKE - SCALE 1:1; GRIPS' FORE-AFT LIE "
                                                     "PROVISIONAL (OPEN POINT 2, L6Y2 PHOTO CHECK)")


# ============================================================================================ section B-B
def draw_secB(ds, v):
    hB = 48.0
    S = G.section((0.0, hB, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (-156.0, -80.0, 156.0, 22.0),
                  parts=("black", "cover", "tcs"), step=0.2)
    draw_section(ds, v, S, parts=("black", "cover", "tcs"))
    X0, Y0 = v.pt(0.0, 0.0)
    aF = float(G.face_a(hB))
    ins = np.asarray(D["insert_side"], float)
    u_ins = float(np.interp(hB, ins[::-1, 1], ins[::-1, 0]))
    for s_ in (1, -1):
        line(ds, v, [(s_ * u_ins, aF + 3.0), (s_ * u_ins, aF + 7.0)], W_THIN, color=ACCENT)
    lbl(ds, *v.pt(0.0, aF + 12.0), f"INSERT GROOVES +/-{u_ins:.1f} (FLUSH)", TXT_S, "middle", color=ACCENT)
    tcs = D["tcs"]
    lbl(ds, *v.pt(float(tcs[0]) + 10.0, aF + 28.0), f"TCS BEZEL {float(D['tcs_profile'][0]):g} PROUD, BUTTON "
                                                    f"{-float(D['tcs_profile'][4]):g} ABOVE IT", TXT_S, "middle")
    lbl(ds, *v.pt(0.0, aF + 20.0), "BADGE GROOVES (CUT)", TXT_S, "middle", color=MUTED)
    for at, t_ in (((35.0, -48.0), "BODY + GRIPS: ONE BLACK MOULDING"), ((112.0, -64.0), "OUTBOARD GRIP"),
                   ((-114.0, -64.0), "INBOARD GRIP")):
        lbl(ds, *v.pt(*at), t_, TXT_S, "middle", color=MUTED)
    view_title(ds, X0, Y0 + 26.0, "SECTION B-B", f"h {hB:.0f} (BADGE / TCS), EXACT CUT OF THE SOLIDS, FROM ABOVE - "
                                                 "SCALE 1:2", size=3.4)

    vline_gapped(ds, X0, Y0 - 52.0, Y0 + 12.0, W_THIN, CHAIN, ds.text_bands(pad=0.6))


# ============================================================================================ tables


def draw_tables(ds, ctx):
    x0, x1 = COL_X
    W = x1 - x0
    size = 2.1
    cols = [("#", 7.0, "c"), ("PART", 50.0, "l"), ("MATERIAL", 38.0, "l"), ("FINISH / COLOUR [SOURCE]", W - 95.0, "l")]
    rows = wrap_rows([(str(n), p, m, f) for n, p, m, f in ITEMS], [c[1] for c in cols], size)
    y = table(ds, x0, 15.0, cols, rows, title="ITEMS & FINISHES (render/lookdev names; 'new' = to add)", size=size,
              row_h=3.3, font="label")
    F = I.yoke_front_mm()
    go, gi = F["grip_out"], F["grip_in"]                 # FRONT SILHOUETTES of the grip solids (heads included)
    ao, ai = F["aft_out"], F["aft_in"]                   # AFT-FACE OUTLINES (table grip_out / grip_in)
    sh = F["shell"]
    po, pi = F["pad_out"], F["pad_in"]
    shh = np.asarray(D["shell_half"], float)
    bo = F["body"]

    def half_at(P, h, side=1.0):
        h = h + 1e-4
        Q = np.vstack([P, P[:1]])
        xs = [a[0] + (h - a[1]) * (b[0] - a[0]) / (b[1] - a[1]) for a, b in zip(Q[:-1], Q[1:])
              if (a[1] - h) * (b[1] - h) < 0]
        return max(xs) if side > 0 else -min(xs)
    rim = [half_at(bo, h) - half_at(sh, h) for h in (10.0, 0.0, -50.0)]
    foot = float(sh[:, 1].min() - bo[:, 1].min())
    dep = np.asarray(D["grip_depth"], float)
    dims_ = [
        ("shell height / about h 0", f"{sh[:, 1].max() - sh[:, 1].min():.1f} / {sh[:, 1].min():.1f}..+"
                                     f"{sh[:, 1].max():.1f}", "[M] rev J landmark-pose frame"),
        ("arm tips / stem at h 0 / at h -50", f"{2 * shh[22, 0]:.1f} / {2 * half_at(sh, 0.0):.1f} / "
                                              f"{2 * half_at(sh, -50.0):.1f}", "[M] sigma 1.5"),
        ("crown above the arm junctions", f"{sh[:, 1].max() - 52.0:.1f}", "[M] parting grooves"),
        ("step / lower insert bottom", f"h {float(D['step'][0][1]):g} (V) / {float(np.min(F['insert_lower'][:, 1])):.1f}",
         "[M]"),
        ("black rim outboard of the stem at h 10 / 0 / -50 / under the foot",
         " / ".join(f"{x:.1f}" for x in rim) + f" / {foot:.1f}", "[M] body - shell outlines"),
        ("aft face above the step", f"{float(D['face_tilt']):.1f}° top fwd", "[M] bundle adj., +/-4"),
        ("body depth / top / cover", f"{float(D['body_form'][0]):g} / {float(D['body_form'][1]):g}° from horiz. / "
                                     f"{float(D['cover_t']):g}", "[E] / [M lower bound] / [E]"),
        ("heads top: FRONT SILHOUETTE out / in", f"{go[:, 1].max():.1f} / {gi[:, 1].max():.1f}", "[M] solids"),
        ("heads top: AFT-FACE OUTLINE out / in", f"{ao[:, 1].max():.1f} / {ai[:, 1].max():.1f}", "[M] table"),
        ("grip bottoms (front silhouette) out / in", f"{go[:, 1].min():.1f} / {gi[:, 1].min():.1f}", "[M]"),
        ("grips overall: front silhouette (out + in)", f"{go[:, 0].max() - gi[:, 0].min():.1f} ({go[:, 0].max():.1f} + "
                                                       f"{-gi[:, 0].min():.1f})", "[M] solids"),
        ("grips overall: aft-face outlines (out + in)", f"{ao[:, 0].max() - ai[:, 0].min():.1f} ({ao[:, 0].max():.1f} + "
                                                        f"{-ai[:, 0].min():.1f})", "[M] table"),
        ("rake / toe-out / a0 @ h 14: out; in", f"{G._gsel('grip_rake', 'out'):g}° / {G._gsel('grip_toe', 'out'):g}° / "
                                                f"{G.grip_a0('out')[1]:g}; {G._gsel('grip_rake', 'in'):g}° / "
                                                f"{G._gsel('grip_toe', 'in'):g}° / {G.grip_a0('in')[1]:g}",
         "[M] 5-view joint fit, +/-3-5"),
        ("walls (0 = aft normal, 1 = fore-aft) out / in", f"{G._gsel('grip_walls', 'out'):g} / "
                                                          f"{G._gsel('grip_walls', 'in'):g}", "[M] face-on silhouettes"),
        ("grip depth (normal) bottom / mid / head, out; in",
         f"{dep[0, 1]:g} / {dep[1, 1]:g} / {dep[2, 1]:g}; {dep[0, 2]:g} / {dep[1, 2]:g} / {dep[2, 2]:g}",
         "[M] / [M] / [E], PCHIP"),
        ("pad out: top / slot corner / bottom", f"{po[:, 1].max():.1f} / ({D['pad_out'][7][0]:g}, "
                                                f"{D['pad_out'][7][1]:g}) / {po[:, 1].min():.1f}", "[M] diagonal top 31°"),
        ("pad in: top / slot corner / bottom", f"{pi[:, 1].max():.1f} / ({D['pad_in'][7][0]:g}, "
                                               f"{D['pad_in'][7][1]:g}) / {pi[:, 1].min():.1f}", "[M] diagonal top 33°"),
        ("frame / leather below it / heel lip", f"{float(D['grip_frame']):g} / {float(D['pad_section'][0]):g} / "
                                                f"{float(D['heel'][1]):g} proud R {float(D['heel'][2]):g}", "[M]"),
        ("trim face centre / dia / up, turn", f"({float(D['head_out'][0]):g}, {float(D['head_out'][1]):g}) / "
                                              f"{float(D['head_out'][2]):g} / {float(D['head_out'][3]):g}°, "
                                              f"{float(D['head_out'][4]):g}°", "[M] triangulated, 7 views"),
        ("shield facet / button centre", f"{np.ptp(np.asarray(D['shield'])[:, 0]):g} x "
                                         f"{np.ptp(np.asarray(D['shield'])[:, 1]):g} / ({float(D['button'][0]):g}, "
                                         f"{float(D['button'][1]):g})",
         "[M] (inboard: -u)"),
        ("TCS / AFCS cap / boss", f"({float(D['tcs'][0]):g}, {float(D['tcs'][1]):g}) {float(D['tcs'][2]):g} / "
                                  f"{float(D['afcs'][2]):g} x {float(D['afcs'][3]):g} / {float(D['afcs'][4]):g}", "[M]"),
        ("column dia / axis", f"{2000 * float(I.YOKE['column_r']):g} [E] / h 0 = WL {1000 * float(I.yoke_hub(-1)[2]):.0f}",
         "kept; surround reads 1821"),
        ("pitch travel / roll", f"+/-{1000 * float(I.YOKE['travel'][1]):g} [E] / +/-{float(I.YOKE['roll']):g} [E]",
         "unchanged (YOKE)"),
    ]
    cols2 = [("DIMENSION (mm, YOKE-LOCAL)", 86.0, "l"), ("VALUE", 78.0, "l"), ("SOURCE", W - 164.0, "l")]
    rows2 = wrap_rows(dims_, [c[1] for c in cols2], size)
    y = table(ds, x0, y + 3.0, cols2, rows2, title="MAIN DIMENSIONS (read from the table / the solids)", size=size,
              row_h=3.3, font="label")
    K = ctx["knees"]
    nm = dict(p95m="95th male", p50m="50th male", p5m="5th male", p5f="5th female")
    rows3 = []
    for k in ("p95m", "p50m", "p5m", "p5f"):
        h_, i_, j_, k_ = REV_H_KNEES[k], REV_I_KNEES[k], REV_J_KNEES[k], K[k]
        rows3.append((nm[k], f"{h_[0]:.0f} > {i_[0]:.0f} > {j_[0]:.0f} > {k_[0]:.0f}",
                      f"{h_[1]:.0f} > {i_[1]:.0f} > {j_[1]:.0f} > {k_[1]:.0f}",
                      f"{h_[2]:.1f} > {i_[2]:.1f} > {j_[2]:.1f} > {k_[2]:.1f}",
                      f"{h_[3]:.1f} > {i_[3]:.1f} > {j_[3]:.1f} > {k_[3]:.1f}",
                      f"{h_[4]:.0f} > {i_[4]:.0f} > {j_[4]:.0f} > {k_[4]:.0f}"))
    cols3 = [("OCCUPANT", 22.0, "l"), ("LEVEL mm", 38.0, "c"), ("ROLL+/-70 mm", 40.0, "c"),
             ("CONTACT deg", 48.0, "c"), ("KEEP 25 deg", 44.0, "c"), ("RUDDER mm", W - 192.0, "c")]
    y = table(ds, x0, y + 3.0, cols3, rows3, title="KNEES vs YOKE (L6B), REV H > I > J > K - CRITERIA UNCHANGED",
              size=size, row_h=3.3, font="label")
    o95 = K["p95m"]
    nts = [
        "Yoke-local mm: u outboard (pilot: -y), h up from the hub centre = the column axis / roll pivot (WL 1845, "
        "BL -/+375), a aft of the aft face at the insert step (X 3700 at neutral pitch).  Drawn from "
        "model/interior.py YOKE_DESIGN rev K through the solids of model/yoke_geom.py; L6 / L6B take the same "
        "solids (yoke_outline_yz, yoke_sweep_pieces).",
        "CURVE LAW (table curve_law): every outline is a centripetal Catmull-Rom spline through its samples, "
        "sampled every 0.25; the samples in the *_corners tables are corners (R 0 sharp, R > 0 a tangent fillet); "
        "the lower aft face is a C1 Hermite tangent to the 17.5° plane.  The solids use the EXACT distance to those "
        "polylines (no raster); views are exact silhouettes, sections exact cuts.",
        "STAGE-3 SURFACE ROUTE: patches, not an implicit mesher -- each face (cover face and inserts, grip aft plane "
        "with its pad pocket, body faces) a grid_surface over its analytic parametrisation trimmed by cad.mesh.trim "
        "with these exact 2-D fields; each tabled edge round a sweep_profile of its radius along the outline; creases "
        "only where tabled; vertex normals from the analytic surfaces.  The SDF solids stay the inside / outside "
        "oracle for fit_check and these sheets.  Acceptance (model/yoke_checks.py, L6Y2): vertex normals within 2° of "
        "the analytic at the 95th percentile, no untabled section cusps, nothing above the trim face / shield.",
        "White moulding symmetric; the black body and the grips are NOT: an outboard web up to the trim head, an "
        "inboard LOW NECK with an open notch under the inboard head; switches outboard (TCS, AFCS, trim), the push "
        "button on the inboard head; the co-pilot yoke is the mirror image.",
        "NO MARKINGS: the badge is an abstract winged plate, every legend a row of ticks.",
        "Not modelled / unsupported: the rev H column bellows (none in 8 photos), a PTT trigger (none seen), the "
        "PC-24's extra grip tab.",
        "GRIPS' 3-D LIE: rake / toe / a0 / walls fitted jointly per grip to the curated silhouettes and pad traces "
        "of 7 views (L6Y2 photo check): the 5 views from inboard (23-27° off aft, Mexico 15-20° from above) land "
        "within 0.7° / 1.4° / 1.2 mm of the table (rake +/-3° out / +/-5° in, a0 +/-3 / +/-5 for a 10 % cost rise); "
        "the AOPA photo (one camera) disagrees by 5-15 mm and no plane the others allow meets it -- open point 2.",
        f"Knee checks on the rev K solids: the 95th clears the yoke by {o95[0]:.0f} mm wings level (criterion 25: "
        f"passes); roll to contact {o95[2]:.1f}° (rev J {REV_J_KNEES['p95m'][2]:.1f}°), keeping 25 mm to "
        f"{o95[3]:.1f}° -- owner decision (open point 1 of L6B; criteria not loosened).",
    ]
    y = notes(ds, x0, y + 2.0, x1, nts, title="NOTES", size=size, line_h=2.9)
    opn = [
        "Absolute fore-aft station: the locked photos put the aft face 60 +/-30 forward of the drawn neutral "
        "(hub_dx kept: the gust-lock pose?).",
        "Grips' fore-aft lie: the AOPA photo wants the aft faces 5-15 further aft below h 0 (and puts the inboard "
        "button 13 off); 5 other views agree with the table -- a true side photo of a PRO / PC-24 yoke would settle it.",
        "Column: the surround's joint line reads WL 1821 +/-10 (25 under the pivot, kept); J band or a full collar "
        "round the column (L6Y2 detail J); push travel 90 [E].",
        "Shell skew: posed on the symmetric landmarks the stem sits ~1.6 inboard and the arm tips ~1.5 outboard of "
        "the inserts' centreline in all 7 views (TCS / AFCS u fit within 0.7): carry the <= 2 mm skew or keep it "
        "symmetric (kept).",
        f"Knees: the 95th meets a grip from {o95[2]:.1f}° of roll (rev I {REV_I_KNEES['p95m'][2]:.1f}°): owner "
        "decision, criteria unchanged.",
        "Crown soft break (R 20 [E]) vs a crease; hidden: body depth 60, the necks' depth, rocker / cap heights.",
    ]
    y = notes(ds, x0, y + 1.0, x1, opn, title="OPEN POINTS FOR THE OWNER", size=size, line_h=2.9)
    ds.log.append(f"right column (tables) ends at y {y:.1f}")
    from drawing.interior_sheet import revisions_block
    import drawing.interior_sheet as IS
    saved = IS.SHEET
    IS.SHEET = SHEET
    try:
        revisions_block(ds, 25.0, 472.0, 562.0, size=2.1, title_size=2.4, rows=REVISIONS)
    finally:
        IS.SHEET = saved
