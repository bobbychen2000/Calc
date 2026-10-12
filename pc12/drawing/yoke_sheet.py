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
  notes, open points, revisions.  NO MARKINGS: the badge is an abstract winged plate with a blank raised field,
  legends are plain letter blocks.
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
                               legend_quads, LEGEND, SLOT, NICKEL,
                               trim_frame, shield_frame, on_frame, front_to_plane, VIEWPROJ, tcs_centre3,
                               afcs_centre3, face_normal3, top_land_line, crown_crease, heel_line, views, draw_parts,
                               draw_section, tangent_edges, ordinates, clear_anchor, clear_boxes,
                               vline_gapped, hline_gapped)

SHEET = dict(id="L6Y", title="CONTROL YOKE - VIEWS", subtitle="PC-24-STYLE CONTROL YOKE - VIEWS", size="A1",
             scale="AS SHOWN", rev="I", order=62, sheet_no="1 OF 2", dwg="PC12-L6Y")
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
    ("D", "2026-10-05", "rev L (judges r3): P1046409 posed (two-view camera) -- grip planes re-fitted on 6 views, depth "
                        "27 from its slot wall (no bottom taper), PROVISIONAL removed, the AOPA photo dropped; the web "
                        "runs into the trim head's rim (no fin) on the face's plane; head zone of named surfaces and "
                        "tabled rounds; body top = a plane through the outline's top edge, rounds in order; C2 curve "
                        "law; U column recess [M]; forward-face switches unverified (PTT expected); knee sweep with "
                        "the inboard grip's lowest band restored (rev K re-swept); acceptance clean: the head zone's "
                        "draft starts C1, inboard cut R 1.5, foot R 5 under a 4 mm draft cap, unit-gradient top / aft"),
    ("E", "2026-10-05", "rev M (judges r4; owner: rev D approved as the 3-D basis, the 95th knee accepted as measured): "
                        "pad pocket cut after the body-grip round (the outboard pad's slot-side corner no longer buried); "
                        "the moulding joined by a rolling-ball R 3 (no bulge where flush); head zones: head and prism share "
                        "walls and forward face, joined R 3 (was 1), trim inset 3, draft start R 4, outboard hz 67; body "
                        "top line and heel lip C2; outboard heel corner raised 2.5 (R 9), waist 127.4 at h 66; [E] "
                        "forward-face switches; heads' a and switch axes dimensioned; adaptive crease / field-ridge / "
                        "pad-exposure acceptance, and what it found fixed: the head's top onto the forward face R 3, "
                        "body sides x top a rolling-ball R 2 between pieces rounded onto the forward face (aft face "
                        "cut last), forward-edge radius cap C2, the inboard fall-off's directrix one tangent curve (R 4 "
                        "withdrawn), outlines sampled 0.05, C2 fields"),
    ("F", "2026-10-11", "rev N (3-D judges r1): legends as words of plain letter blocks (the tick rows read as a dial); "
                        "trim rocker in a 2.5 deep slot (7 deg draft), satin dark-grey lobes, gloss lunes; badge: a "
                        "raised blank plate 0.3 proud; push button hex collar satin nickel; column satin black "
                        "(non-metallic); column recess up to h 27 (the column, about the hub, 5 mm clear), J band 22 "
                        "(1 mm clear of the column), the band pewter, the recess charcoal; items 9-14 re-written.  "
                        "OWNER DECISIONS 2026-10-11: the J band and the U recess re-centred on the column axis (hub WL "
                        "1845; the photos read 1821), push travel 65 (was 90 [E]), pull 90; the pilot yoke's legends keep their "
                        "reading order (item 14)"),
    ("G", "2026-10-11", "rev O (3-D judges r2): item 10 -- the push button a GLOSS-BLACK LEGEND DISC 17.5 (0.75 proud) with "
                        "MAP LIGHTS at its rim, a small satin-nickel hex 12 A/C under the 10.2 cap (rev N's 17.3 collar "
                        "read as a big bright nut where every photo shows a dark disc); item 9 -- rocker ends 9.5 proud "
                        "(6.5), lobes crowned 0.6, satin black; legend blocks 0.35 of the pitch, tone 0.45; badge: ONE "
                        "outline groove (the inner border dropped), speed lines into it, plate 0.2 proud; open point 3 "
                        "closed (owner 2026-10-11)"),
    ("H", "2026-10-11", "rev P (3-D judges r3): item 9 -- the legend ring / lunes a SATIN CHARCOAL face and the rocker "
                        "slot a near-black MATTE pocket (rev N / O's gloss lunes over a satin slot read inverted against "
                        "every photo); legend letters 0.22 of the pitch, uneven (+/-35 %), tone 0.40; item 10 hex 12 A/C "
                        "(text); item 11 column matte near-black; item 12 the J band's hook ends round; the viewer's "
                        "parked yokes at the photos' free rest, 35 forward (YOKE rest); item 8 text: the rev O red"),
    ("I", "2026-10-12", "rev Q (3-D judges r4): item 15 (new) -- the cover's groove flanks DARK (yoke_groove: the step's "
                        "down-facing flank and end cones, the parting grooves, the badge outline / speed lines; the "
                        "step's lit lower flank keeps the white), FID4-01; items 2 / 3 the inserts a COOL satin metal "
                        "(FID4-02); item 8 the AFCS boss in the body's satin black (FID4-06); item 11 the column a "
                        "satin dark-grey tube, the parked elevators coupled to the parked yokes (FID4-05, CR4-05); item "
                        "14 the legend letters set with uneven gaps and heights (CR4-06)"),
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
    ds.frame_and_title(fields=dict(date="2026-10-12"))
    ctx = context()
    draw_front(ds, v["front"])
    front_annotations(ds, v["front"])
    draw_side(ds, v["side"])
    draw_top(ds, v["top"])
    draw_secB(ds, v["secB"])
    draw_tables(ds, ctx)
    ds.log.append(f"knee / roll (rev L): {ctx['summary']}")


# ============================================================================================ knee context
REV_H_KNEES = dict(p95m=(37.6, -18.9, 17.5, 5.0, -10.6, -1.0), p50m=(50.4, -13.1, 25.0, 10.0, 5.2, 0.0),
                   p5m=(50.6, -21.0, 22.5, 10.0, 20.5, 7.5), p5f=(76.1, 4.9, 87.5, 27.5, 55.0, 25.0))
REV_I_KNEES = dict(p95m=(35.3, -18.5, 17.5, 2.5, -12.7, -1.0), p50m=(48.0, -13.7, 25.0, 10.0, 3.0, 0.0),
                   p5m=(47.6, -21.4, 22.5, 10.0, 18.3, 7.5), p5f=(78.0, 0.4, 87.5, 25.0, 52.7, 25.0))
REV_J_KNEES = dict(p95m=(39.5, -19.0, 15.0, 5.0, -9.0, 0.0), p50m=(52.0, -14.0, 22.5, 10.0, 7.0, 0.0),
                   p5m=(51.0, -22.0, 22.5, 10.0, 22.0, 0.0), p5f=(81.0, 0.0, 87.5, 25.0, 56.0, 0.0))
# FID3-07 (rev L): the knee sweep (interior.crew_checks) re-run with the neutral moved STATION_SHIFT mm forward:
# (95th contact roll now, then; wings-level clearance now, then) -- filled in from the L6B run (drawing/yoke_station.py)
STATION_SHIFT = 45.0
STATION_KNEE = (12.5, 12.5, 23.8, 23.8)     # python3 -m drawing.yoke_station 45 (2026-10-05): the knees lie inside
#                                             the pitch-swept slab (+/-90) either way, so the shift changes nothing
# rev K as issued (37 / 15 deg) had dropped the inboard grip's lowest 12 mm band from the sweep (a doubled vertex in
# interior._clip_band made the exact polygon distance NaN, fixed in rev L); REV_K_KNEES = rev K's solids re-swept with
# the fix (2026-10-05): 95th 25.3 wings level, contact 12.5 deg
REV_K_ISSUED = dict(p95m=(37.0, -19.0, 15.0, 5.0, -11.0, 0.0))
REV_K_KNEES = dict(p95m=(25.3, -18.7, 12.5, 0.0, -22.3, -1.0), p50m=(37.9, -13.9, 22.5, 5.0, -6.7, -1.0),
                   p5m=(36.9, -21.6, 17.5, 5.0, 8.5, 2.5), p5f=(67.2, 0.2, 87.5, 20.0, 41.9, 20.0))
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
    out = dict(face=on_frame(fr, circle((0, 0), R, 97)[:-1]), ring=on_frame(fr, circle((0, 0), 0.5 * od, 97)[:-1]))
    out["slot"] = on_frame(fr, slot_outline())
    out["ticks"] = [on_frame(fr, Q) for k in (2, 3) for Q in legend_quads((0.0, 0.0), k)]
    out["rocker"] = [on_frame(fr, h) for h in rocker_halves()]
    return out


def slot_outline(n=40):
    """The trim rocker's recessed slot at the face (rev N, yoke_geom.trim_slot_dims): the chords |y| = yl closed by the
    end-wall arcs r = r_end, in the face frame, closed."""
    yl, r_end, _, _ = G.trim_slot_dims()
    a = math.asin(yl / r_end)
    t1 = np.linspace(-a, a, n)
    t2 = np.linspace(math.pi - a, math.pi + a, n)
    P = np.vstack([np.c_[r_end * np.cos(t1), r_end * np.sin(t1)], np.c_[r_end * np.cos(t2), r_end * np.sin(t2)]])
    return np.vstack([P, P[:1]])


def button_pieces():
    """3-D pieces of the inboard head: shield facet outline, the gloss-black legend disc (rev O), the nickel hex, the
    cap, ticks (co-pilot sense, u < 0)."""
    fr = shield_frame()
    b = D["button"]
    bd = G.button_dims()
    c3 = fr[0]
    out = dict(shield=on_frame(fr, G.shield_outline()))
    bc = front_to_plane(fr, [(-float(b[0]), float(b[1]))])[0]
    off2 = np.array([np.dot(bc - c3, fr[2]), np.dot(bc - c3, fr[3])])
    out["centre2"] = off2
    out["disc"] = on_frame(fr, circle(off2, 0.5 * bd["disc_d"], 73)[:-1])
    out["hex"] = on_frame(fr, hexagon(bd["hex_c"]) + off2)
    out["cap"] = on_frame(fr, circle(off2, 0.5 * bd["cap_d"], 61)[:-1])
    out["ticks"] = [front_to_plane(fr, Q) for Q in legend_quads((-float(b[0]), float(b[1])), 4)]
    return out


def crown_top():
    """(h, a) of the cover solid's crown TOP EDGE on the centreline (the highest point of its Z-Z section): the crown
    bevel and the top land applied (rev L, judges DR3-05: rev K dimensioned face_a at the crown sample)."""
    S = G.section((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0, 0.0), (-76.0, -66.0, 12.0, 70.0), parts=("black", "cover"),
                  step=0.2)
    C = max(S["cover"], key=len)
    top = C[C[:, 1] > C[:, 1].max() - 0.05]
    k = int(np.argmax(top[:, 0]))
    return float(top[k, 1]), float(top[k, 0])


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
    poly(ds, v, VIEWPROJ(tp["slot"], "front"), W_TAN, fill=SLOT, color="#9AA3A9")
    for T in tp["ticks"]:
        poly(ds, v, VIEWPROJ(T, "front"), 0.05, fill=LEGEND, color=LEGEND)
    for h in tp["rocker"]:
        poly(ds, v, VIEWPROJ(h, "front"), W_THIN, fill=SWITCH, color="#C9CFD3")
    bp = button_pieces()
    poly(ds, v, VIEWPROJ(bp["shield"], "front"), W_CREASE, fill="#2F363A", color="#B9C0C5")
    poly(ds, v, VIEWPROJ(bp["disc"], "front"), W_THIN, fill=TRIM_COL, color="#AEB6BB")     # rev O: gloss-black disc
    poly(ds, v, VIEWPROJ(bp["hex"], "front"), W_THIN, fill=NICKEL, color="#C9CFD3")
    poly(ds, v, VIEWPROJ(bp["cap"], "front"), W_THIN, fill="#3A4247", color="#C9CFD3")
    for T in bp["ticks"]:
        poly(ds, v, VIEWPROJ(T, "front"), 0.05, fill=LEGEND, color=LEGEND)
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
    if F["badge_border"] is not None:
        poly(ds, v, F["badge_border"], W_THIN)
    for L in F["badge_lines"]:
        line(ds, v, L, W_THIN)
    poly(ds, v, F["badge_plate"], W_THIN, fill="#DDE0E3")                # rev N: the raised blank plate
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
    r_e = float(D["head_out"][6])
    ds.log.append(f"trim face (its sharp virtual rim) inside the outboard head's front silhouette: max signed distance "
                  f"{m:+.2f} mm (negative = inside; criterion <= the face edge's R {r_e:g}, which rounds the rim off "
                  f"the silhouette: {'PASS' if m <= r_e else 'FAIL'}; judges D6 / DR3-08)")


def draw_tcs(ds, v, k=1.0, c=None):
    u, h, od, bd = (float(x) for x in D["tcs"][:4])
    c = np.array([u, h]) if c is None else np.asarray(c, float)
    r_in, r_out = (float(x) for x in D["tcs_profile"][5:7])
    circ(ds, v, c, od, W_FINE, fill=GLOSS)
    circ(ds, v, c, 2 * r_out, W_THIN, color="#7E878D")
    circ(ds, v, c, 2 * r_in, W_THIN, color="#7E878D")
    circ(ds, v, c, bd, W_THIN, fill="#2B3135", color="#9AA3A9")
    for Q in legend_quads(c, 0):
        poly(ds, v, Q, 0.05, fill=LEGEND, color=LEGEND)


def draw_afcs(ds, v, k=1.0, c=None):
    u, h, cd, ch, bd = (float(x) for x in D["afcs"][:5])
    c = np.array([u, h]) if c is None else np.asarray(c, float)
    circ(ds, v, c, bd, W_THIN, fill=GLOSS)
    for Q in legend_quads(c, 1):
        poly(ds, v, Q, 0.05, fill=LEGEND, color=LEGEND)
    circ(ds, v, c, cd, W_FINE, fill=RED)


ITEMS = (  # item, part, material (render/lookdev name), finish [source]
    (1, "WHITE COVER (Y SHELL)", "yoke_white", "gloss clear-coat white, neutral-cool (0.77 / 0.78 / 0.80), fine "
                                               "pearl; R 1 edges, top land [M]"),
    (2, "UPPER INSERT = CROWN, BADGE", "yoke_silver", "COOL satin aluminium 0.58 / 0.61 / 0.67, metallic 0.85, rough "
                                                      "0.34 (rev Q: cooler and darker than the cover); flush, 0.6 x "
                                                      "0.5 grooves; the badge's blank plate 0.2 proud [M / E]"),
    (3, "LOWER INSERT", "yoke_silver_dark", "cool smoke silver 0.29 / 0.30 / 0.33, metallic 0.85, rough 0.36 (rev Q); "
                                            "flush [M]"),
    (4, "BLACK BODY (RIM, WEB, NECK)", "grip_black", "satin black, rough 0.42: crisp edge highlights; R 2 aft edge [M]"),
    (5, "GRIP (2) WITH FRAME, HEEL LIP", "grip_black", "satin black; 2.0 frame R 1.5, heel lip 3 proud R 4 [M]"),
    (6, "LEATHER PAD (2)", "leather_black", "charcoal 0.05, rough 0.58, 1.1 pebble grain, ~1 creases, 2.5 below the "
                                            "frame, groove 1.0 x 0.5 + bead 0.4 at its edge [M / E]"),
    (7, "TCS BUTTON", "gloss_black / black", "gloss black bezel 1 proud [E], satin domed button 2 proud of it "
                                             "[M low]; legend blocks (legend_grey)"),
    (8, "AFCS DISCONNECT", "button_red / grip_black", "deep red cap 0.50 / 0.004 / 0.012, clear coat 0.15 (rev O), "
                                                      "NOT emissive, on a boss in the body's satin black (rev Q) [M]; "
                                                      "legend blocks"),
    (9, "PITCH TRIM ON ROUND FACE", "yoke_trim_face / yoke_rocker / yoke_slot", "rev P: SATIN CHARCOAL ring + "
                                                                                 "lunes 0.04, rough 0.45 (as light as "
                                                                                 "the body or lighter); rocker near-"
                                                                                 "black satin 0.02, rough 0.30, ends "
                                                                                 "9.5 proud, crowned; 2.5 deep near-"
                                                                                 "black MATTE slot 0.01, rough 0.8 "
                                                                                 "(the darkest part) [M / E]; legends"),
    (10, "PUSH BUTTON ON SHIELD", "gloss_black / yoke_nickel / black", "rev O: GLOSS-BLACK legend disc 17.5, 0.75 "
                                                                       "proud, legend blocks at its rim; small SATIN "
                                                                       "NICKEL hex 12 A/C (warm); smooth black cap, "
                                                                       "centre dimple [M]; function: MAP LIGHTS (no "
                                                                       "lettering)"),
    (11, "COLUMN", "yoke_column (new)", "satin dark grey tube 0.04, metallic 0.5, rough 0.4 (rev Q), dia 44 [E] (never "
                                        "seen in a PRO photo); the viewer parks the free yokes 35 forward (YOKE rest, "
                                        "rev P), the elevators trailing-edge down with them (rev Q)"),
    (12, "COLUMN SURROUND (PANEL)", "pcl_pewter / panel_dark", "satin pewter J band 22 wide, both ends round (rev "
                                                               "P), charcoal dished recess [M / E]"),
    (13, "FORWARD-FACE SWITCHES (2) [E]", "grip_black", "PTT trigger (outboard grip), checklist rocker (inboard): "
                                                        "placeholders, never seen (L6Y2 detail W) [E]"),
    (14, "LEGENDS", "legend_grey (new)", "words of plain letter blocks 0.22 of the pitch, uneven widths (rev P), "
                                         "set with uneven gaps and heights (rev Q), tone ~0.40, 0.12 proud -- NO "
                                         "lettering (rev N); the pilot's in reading order, not mirrored"),
    (15, "COVER GROOVES / STEP", "yoke_groove (new)", "rev Q: the V flanks of the parting grooves, the step's down-"
                                                      "facing flank and end cones, the badge outline / speed lines "
                                                      "dark satin 0.03, rough 0.6 (their cavity shadow: dark lines in "
                                                      "every photo); the step's lower flank keeps the cover white "
                                                      "(the lit line under it) [M]"),
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
    Sa = views("a")                                         # rev L (judges DR3-05): every ordinate read off the solids
    cv_ = max(Sa["cover"], key=len)
    cov_b = cv_[np.argmin(cv_[:, 1] + 1e-3 * np.abs(cv_[:, 0]))]
    bd_ = max(Sa["body"], key=len)
    body_b = bd_[np.argmin(bd_[:, 1] + 1e-3 * np.abs(bd_[:, 0]))] * [-1.0, 1.0]
    bo = go[np.argmin(go[:, 1])]
    bi = gi[np.argmin(gi[:, 1])]
    po, pi = F["pad_out"], F["pad_in"]
    to_, ah = D["tcs"], D["afcs"]
    tr_, bt_ = D["head_out"], D["button"]
    left = [(float(pk_o[0]), float(pk_o[1]), None), (float(tr_[0]), float(tr_[1]), None),
            (float(po[np.argmax(po[:, 1]), 0]), float(po[:, 1].max()), None), (float(sh[22, 0]), float(sh[22, 1]), None),
            (float(to_[0]), float(to_[1]), None), (float(ah[0]), float(ah[1]), None),
            (float(po[np.argmin(po[:, 1]), 0]), float(po[:, 1].min()), None), (float(bo[0]), float(bo[1]), None),
            (float(cov_b[0]), float(cov_b[1]), None)]
    right = [(float(pk_i[0]), float(pk_i[1]), None), (-float(bt_[0]), float(bt_[1]), None),
             (-float(pi[np.argmax(pi[:, 1]), 0]) if pi[:, 0].mean() > 0 else float(pi[np.argmax(pi[:, 1]), 0]),
              float(pi[:, 1].max()), None), (0.0, float(sh[0, 1]), None), (-12.9, float(D["step"][1][1]), None),
             (-8.0, float(np.min(F["insert_lower"][:, 1])), None),
             (float(pi[np.argmin(pi[:, 1]), 0]), float(pi[:, 1].min()), None), (float(bi[0]), float(bi[1]), None),
             (float(body_b[0]), float(body_b[1]), None)]
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
    for C in S.get("fwd_out", []):                                       # [E] PTT trigger: phantom (rev M, FID4-08)
        if len(C) > 8:
            poly(ds, v, C, W_THIN, fill="#5A6268", dash=PHANTOM, color="#C9CFD3")
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
    # rev M: left of the line's top, clear of the head-position dims' extension lines (a -27 / -23.3 / -58.9)
    lbl(ds, X - 1.2, Y - 4.4, f"AFT FACE {float(D['face_tilt']):.1f}°", TXT_S, "end", color=ACCENT, weight=600)
    lbl(ds, X - 1.2, Y - 1.6, "TOP FWD", TXT_S, "end", color=ACCENT, weight=600)
    X, Y = v.pt(a0 + (h0 + 64.0) * R, -64.0)
    lbl(ds, X + 1.2, Y + 1.6, f"GRIP RAKE {G._gsel('grip_rake', 'out'):.0f}° [M +/-2.5]", TXT_S, color=ACCENT,
        weight=600)
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
    h_cr, a_cr = crown_top()                              # rev L (judges DR3-05): the solid's crown top edge
    dim(ds, v.pt(a_cr, h_cr), v.pt(0.0, 2.1), Y0 - 104.0, f"{-a_cr:.1f} CROWN TOP EDGE FWD OF a 0", outside=True)
    gout = max(S["grip_out"], key=len)
    a_hf = float(gout[:, 0].min())
    h_hf = float(gout[np.argmin(gout[:, 0]), 1])
    dim(ds, v.pt(a_hf, h_hf), v.pt(0.0, 2.1), Y0 - 111.0, f"{-a_hf:.1f} OUTBOARD HEAD FWD",
        outside=True)
    c_t, _ = G.head_out_face()                           # rev M (judges DR4-06): the heads' fore-aft positions
    dim(ds, v.pt(float(c_t[2]), float(c_t[1])), v.pt(0.0, 2.1), Y0 - 118.0,
        f"{-float(c_t[2]):.1f} TRIM FACE CENTRE (h {float(c_t[1]):g}) [M weak +/-5]", outside=True)
    # ---- ordinate heights from h 0, named (the centre features; the front view carries the grips') + envelope
    items = [(a_back + 2.0, h_top, "TOP (HEAD)"), (a_cr, h_cr, "CROWN TOP EDGE (SOLID)"),
             (float(G.face_a(56.0)), float(D["crown"][0]), "CROWN BREAK"),
             (0.0, float(D["step"][0][1]), "STEP V"),
             (float(G.face_a(-18.9)), float(np.min(I.yoke_front_mm()["insert_lower"][:, 1])), "LOWER INSERT"),
             (float(G.face_a(-56.0)), float(np.asarray(D["shell_half"])[-1, 1]), "FOOT (COVER)"),
             (a_front + 20.0, h_bot, "BOTTOM (BODY)")]
    from drawing.yoke_draw import ordinates
    ordinates(ds, v, items, X0 + 44.0, side=+1, min_gap=3.2)
    dim(ds, v.pt(a_back, h_top), v.pt(a_back, h_bot), X0 + 36.0, f"{h_top - h_bot:.1f} OVERALL HEIGHT", orient="v",
        outside=False)
    # rev M (DR4-06): both heads' call-outs above the front view's labels (the trim leader above the shield's)
    leader(ds, v.pt(float(tp["face"][:, 2].mean()), float(tp["face"][:, 1].mean())), (X0 - 70.0, Y0 - 114.0),
           f"TRIM FACE {float(D['head_out'][3]):g}° ABOVE AFT, {float(D['head_out'][4]):g}° IN",
           [f"dia {float(D['head_out'][2]):g}, ring flush"], size=TXT_S)
    c_s, _ = G.head_in_face()
    leader(ds, v.pt(float(c_s[2]), float(c_s[1])), (X0 - 70.0, Y0 - 106.0), "SHIELD FACET POINT (HIDDEN)",
           [f"a {float(c_s[2]):g}: {float(D['head_in'][2]):g}° UP, TOE {float(D['head_in'][3]):g}°"], size=TXT_S)
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
    lbl(ds, X0 - 74.0, Y0 + 104.5, "GRIP PLANES [M], 6 VIEWS INCL. P1046409: RAKE 20 +/-2.5, a0 -3.75 +/-3, DEPTH 27 "
                                   "+/-4, WALLS 0.6 / 0; TOE 18 WEAK +/-8 (OPEN POINT 2)", TXT_S, color=ACCENT, weight=600)


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
    for p_ in ("fwd_out", "fwd_in"):                                     # [E] forward-face switches: phantom
        for C in S.get(p_, []):
            if len(C) > 8:
                poly(ds, v, C, W_THIN, fill="#5A6268", dash=PHANTOM, color="#C9CFD3")
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
               f"AFT PLANE @ h 14: TOE-OUT {float(D['grip_toe'][0 if g == 'out' else 1]):g}° [M weak]", size=TXT_S,
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
    view_title(ds, X0, Y0 + 42.0, "VIEW FROM ABOVE", "FORWARD UP, PILOT YOKE - SCALE 1:1; GRIP PLANES ON 6 VIEWS "
                                                     "(L6Y2 PHOTO CHECK); TOE WEAK (OPEN POINT 2)")


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
    lbl(ds, X0 + 14.0, v.pt(0.0, aF + 12.0)[1], f"INSERT GROOVES +/-{u_ins:.1f} (FLUSH)", TXT_S, "start",
        color=ACCENT)
    # rev L (judges DR3-08): the TCS call-out on a leader; the body depth and the cover thickness dimensioned
    Ct = [C for C in S.get("tcs", []) if len(C) > 8]
    if Ct:
        C = max(Ct, key=len)
        k = int(np.argmax(C[:, 1]))
        Pt = v.pt(*C[k])
        leader(ds, Pt, (Pt[0] - 10.0 if Pt[0] < X0 else Pt[0] + 10.0, v.pt(0.0, aF + 30.0)[1]),
               f"TCS: BEZEL {float(D['tcs_profile'][0]):g} PROUD, BUTTON {-float(D['tcs_profile'][4]):g} ABOVE IT",
               [f"seated {float(D['tcs_seat']):g} in the cover"], size=TXT_S, weight=500)
    blk = [C for C in S.get("black", []) if len(C) > 8]
    cov = [C for C in S.get("cover", []) if len(C) > 8]
    if blk and cov:
        B = max(blk, key=len)
        Cc = max(cov, key=len)
        rowB = B[np.abs(B[:, 0]) < 0.6]
        rowC = Cc[np.abs(Cc[:, 0]) < 0.6]
        if len(rowB) and len(rowC):
            a0_, a1_ = float(rowB[:, 1].min()), float(rowB[:, 1].max())
            c0_, c1_ = float(rowC[:, 1].min()), float(rowC[:, 1].max())
            # body: its text beyond the forward face (up); cover: beyond its aft face (down), the labels right of it
            dim(ds, v.pt(0.0, a1_), v.pt(0.0, a0_), X0 - 12.0, f"{a1_ - a0_:.1f} BODY", orient="v", outside=True)
            dim(ds, v.pt(0.0, c0_), v.pt(0.0, c1_), X0 + 10.0, f"{c1_ - c0_:.1f} COVER", orient="v", outside=True)
    lbl(ds, X0 + 14.0, v.pt(0.0, aF + 20.0)[1], "BADGE GROOVES (CUT)", TXT_S, "start", color=MUTED)
    for at, t_ in (((-35.0, -48.0), "BODY + GRIPS: ONE BLACK MOULDING"), ((112.0, -64.0), "OUTBOARD GRIP"),
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
        ("heads top: FRONT SILHOUETTE out / in", f"{go[:, 1].max():.1f} / {gi[:, 1].max():.1f}",
         "[derived: solids from M / E]"),
        ("grip bottoms (front silhouette) out / in", f"{go[:, 1].min():.1f} / {gi[:, 1].min():.1f}",
         "[derived: solids, rake / toe M, depth M / E]"),
        ("grips overall: front silhouette (out + in)", f"{go[:, 0].max() - gi[:, 0].min():.1f} ({go[:, 0].max():.1f} + "
                                                       f"{-gi[:, 0].min():.1f})", "[derived: solids]"),
        ("CONSTRUCTION G (prism directrix): head tops / span",
         f"{ao[:, 1].max():.1f} / {ai[:, 1].max():.1f}; {ao[:, 0].max() - ai[:, 0].min():.1f}",
         "[M] table; NOT the part (head solids trim it)"),
        ("rake / toe-out / a0 @ h 14: out; in", f"{G._gsel('grip_rake', 'out'):g}° / {G._gsel('grip_toe', 'out'):g}° / "
                                                f"{G.grip_a0('out')[1]:g}; {G._gsel('grip_rake', 'in'):g}° / "
                                                f"{G._gsel('grip_toe', 'in'):g}° / {G.grip_a0('in')[1]:g}",
         "[M] 6 views incl. P1046409: +/-2.5° / toe weak / +/-3"),
        ("walls (0 = aft normal, 1 = fore-aft) out / in", f"{G._gsel('grip_walls', 'out'):g} / "
                                                          f"{G._gsel('grip_walls', 'in'):g}", "[M] +/-0.2"),
        ("grip depth (normal) bottom / mid / head, out; in",
         f"{dep[0, 1]:g} / {dep[1, 1]:g} / {dep[2, 1]:g}; {dep[0, 2]:g} / {dep[1, 2]:g} / {dep[2, 2]:g}",
         "[M] P1046409 slot wall +/-4; in = out [E]"),
        ("pad out: top / slot corner / bottom", f"{po[:, 1].max():.1f} / ({D['pad_out'][7][0]:g}, "
                                                f"{D['pad_out'][7][1]:g}) / {po[:, 1].min():.1f}", "[M] diagonal top 31°"),
        ("pad in: top / slot corner / bottom", f"{pi[:, 1].max():.1f} / ({D['pad_in'][7][0]:g}, "
                                               f"{D['pad_in'][7][1]:g}) / {pi[:, 1].min():.1f}", "[M] diagonal top 33°"),
        ("frame / leather below it / heel lip", f"{float(D['grip_frame']):g} / {float(D['pad_section'][0]):g} / "
                                                f"{float(D['heel'][1]):g} proud R {float(D['heel'][2]):g}", "[M]"),
        ("trim face centre (u, h, a) / dia / normal", f"({float(D['head_out'][0]):g}, {float(D['head_out'][1]):g}, "
                                                       f"{float(D['head_out_a']):g}) / {float(D['head_out'][2]):g} / "
                                                       f"{float(D['head_out'][3]):g}° up, {float(D['head_out'][4]):g}° in",
         "[M] (u, h) 7 views; a [M weak +/-5]"),
        ("shield facet point (u, h, a) / normal / size", f"({float(D['head_in'][0]):g}, {float(D['head_in'][1]):g}, "
                                                         f"{float(D['head_in_a']):g}) / {float(D['head_in'][2]):g}° up, "
                                                         f"toe {float(D['head_in'][3]):g}° / "
                                                         f"{np.ptp(np.asarray(D['shield'])[:, 0]):g} x "
                                                         f"{np.ptp(np.asarray(D['shield'])[:, 1]):g}",
         "[M] (inboard: -u)"),
        ("switch axes (u, h, a): button / TCS / AFCS",
         "({0:.1f}, {1:.1f}, {2:.1f}) along the facet normal / ({3:.1f}, {4:.1f}, {5:.1f}) / ({6:.1f}, {7:.1f}, "
         "{8:.1f}) along the 17.5° face's normal".format(*[float(x) for x in np.r_[G.button_frame()[0],
                                                                                     G.tcs_axis()[0],
                                                                                     G.afcs_axis()[0]]]),
         "[M]; TCS on the face, AFCS boss face = face - 3 + 1.5"),
        ("TCS / AFCS cap / boss", f"({float(D['tcs'][0]):g}, {float(D['tcs'][1]):g}) {float(D['tcs'][2]):g} / "
                                  f"{float(D['afcs'][2]):g} x {float(D['afcs'][3]):g} / {float(D['afcs'][4]):g}", "[M]"),
        ("forward-face switches out / in (h, L x W, proud)",
         " / ".join(f"h {r_[0]:g}, {r_[1]:g} x {r_[2]:g}, {r_[3]:g}" for r_ in D["fwd_switch"]), "[E] placeholders"),
        ("column dia / axis", f"{2000 * float(I.YOKE['column_r']):g} [E] / h 0 = WL {1000 * float(I.yoke_hub(-1)[2]):.0f}",
         "kept; surround re-centred on it (owner 2026-10-11)"),
        ("pitch travel push / pull / roll", f"{-1000 * float(I.YOKE['travel'][0]):g} / {1000 * float(I.YOKE['travel'][1]):g}"
                                            f" [E] / +/-{float(I.YOKE['roll']):g} [E]",
         "push: owner 2026-10-11 (was 90 [E])"),
    ]
    cols2 = [("DIMENSION (mm, YOKE-LOCAL)", 86.0, "l"), ("VALUE", 78.0, "l"), ("SOURCE", W - 164.0, "l")]
    rows2 = wrap_rows(dims_, [c[1] for c in cols2], size)
    y = table(ds, x0, y + 3.0, cols2, rows2, title="MAIN DIMENSIONS (read from the table / the solids)", size=size,
              row_h=3.3, font="label")
    K = ctx["knees"]
    nm = dict(p95m="95th male", p50m="50th male", p5m="5th male", p5f="5th female")
    rows3 = []
    for k in ("p95m", "p50m", "p5m", "p5f"):
        revs = (REV_H_KNEES[k], REV_I_KNEES[k], REV_J_KNEES[k], REV_K_KNEES[k], K[k])
        rows3.append((nm[k],) + tuple(" > ".join(f"{r_[c]:.{dd}f}" for r_ in revs)
                                      for c, dd in ((0, 0), (1, 0), (2, 1), (3, 1), (4, 0))))
    cols3 = [("OCCUPANT", 20.0, "l"), ("LEVEL mm", 40.0, "c"), ("ROLL+/-70 mm", 42.0, "c"),
             ("CONTACT deg", 50.0, "c"), ("KEEP 25 deg", 46.0, "c"), ("RUDDER mm", W - 198.0, "c")]
    y = table(ds, x0, y + 3.0, cols3, rows3, title="KNEES vs YOKE (L6B), REV H > I > J > K (RE-SWEPT) > M - CRITERIA UNCHANGED, ACCEPTED AS MEASURED",
              size=size, row_h=3.3, font="label")
    o95 = K["p95m"]
    hz_o, hz_i = (D["head_zone"][k] for k in (0, 1))
    nts = [
        "OWNER 2026-10-05: L6Y rev D / L6Y2 rev C APPROVED as the basis of the 3-D yoke; this rev E carries the "
        "judges' round-4 drawing-stage cleanup (the measured outline unchanged but the outboard grip's heel corner and "
        "waist, FID4-01 / 02).  Signed off with the approval: the rev L hidden estimates foot round R 14 -> R 5 under a "
        "4 mm draft cap and inboard head cut R 3 -> R 1.5.",
        "Yoke-local mm: u outboard (pilot: -y), h up from the hub centre = the column axis / roll pivot (WL 1845, "
        "BL -/+375), a aft of the aft face at the insert step (X 3700 at neutral pitch).  Drawn from "
        "model/interior.py YOKE_DESIGN rev M through the solids of model/yoke_geom.py; L6 / L6B take the same "
        "solids (yoke_outline_yz, yoke_sweep_pieces).",
        "CURVE LAW (table curve_law, rev M text): each outline split at its corner samples into runs, each run a C2 "
        "cubic spline on centripetal knots ('natural' ends at the corners, periodic for a closed outline without "
        f"corners), sampled every {float(D['curve_law'][0]):g} (arcs too); corners R 0 sharp, R > 0 a tangent fillet (cubic Bezier arc, tangent length "
        "R tan(th/2) capped at 0.45 of the shorter run: none capped in rev M); the lower aft face a C1 Hermite tangent "
        "to the 17.5° plane.  The solids use the EXACT distance to those polylines (no raster; beyond 0.3 mm a C2 "
        "B-spline of exact node distances); views are exact silhouettes, sections exact cuts.",
        "SURFACES: the cover's face (the 17.5° plane, the lower Hermite, the crown bevel) trimmed by its outline; the "
        "body: sides / bottom = its outline without the top edge, top = a plane 42° from the horizontal through the "
        "outline's top edge (body_top, a C2 cubic in |u|), forward face, rounds in order R 2 / R 2 / R 8 (R 5 at the "
        "foot, the draft's offset capped at 4 there; the crown's top edge h 65.2 = the outline's 65.3 less its R 1); the web's aft face = the trim face's plane 3.5 below it (web); "
        f"each grip: its AFT SIDE = the prism's aft plane trimmed {hz_o[1]:g} inside the head's shaping surface above "
        f"the plane height {hz_o[0]:g} / {hz_i[0]:g}, drafted outward below it from a bend of R {hz_o[10]:g} (an exact "
        f"2-D distance), cut edge R {hz_o[3]:g}, joined R {hz_o[9]:g} to the HEAD's aft shape (round face on its flared "
        "cylinder / shield facet + fall-off, x chamfer R 3, floor R 3); then the walls (outline G, a construction "
        f"curve) and the forward face cut both, edges R 1.5 easing to R {hz_o[8]:g} / R 11 (capped) easing to R "
        f"{hz_o[7]:g} over the head, the head's top onto the forward face R {hz_o[7]:g}; body + grips one moulding joined by a ROLLING-BALL R 3 (a true round where they "
        "meet at an angle, none where they run flush); the pad pocket, groove and bead cut after that join.  Every "
        "edge is a tabled round or a tabled crease (L6Y2 CORNERS & RADII).",
        "STAGE-3 SURFACE ROUTE: each named surface a grid_surface over its parametrisation (planes, the face "
        "Hermite, the head cylinder about the face normal) trimmed by cad.mesh.trim with these exact 2-D fields; "
        "each tabled round a sweep_profile of its radius; the head-zone trimming surface is a draft from the head "
        "surface's offset curve; vertex normals from the analytic surfaces.  The solids stay the inside / outside "
        "oracle.  Acceptance (model/yoke_checks.py, L6Y2): vertex normals within 2° at the 95th percentile on 9 "
        "patches; NO UNTABLED CREASE in an adaptive scan of 14 views (every pixel pair turning > 4° refined 256x); "
        "the joins read smooth fields (no ridge at their rounds' own surface points); each pad's exposed surface = its drawn "
        "section; no untabled section cusps; one piece per side in every h section above 62; nothing above the trim "
        "face / shield.",
        "White moulding symmetric; the black body and the grips are NOT: an outboard web running into the trim "
        "head's rim (10-11 o'clock), an inboard LOW NECK with an open notch under the inboard head; switches "
        "outboard (TCS, AFCS, trim), the MAP LIGHTS push button on the inboard head; co-pilot yoke = mirror image.",
        "NO MARKINGS: the badge is an abstract winged plate with a blank raised field, every legend plain letter "
        "blocks.",
        "Not modelled: the rev H column bellows (none in 8 photos), the PC-24's grip tab (not on the PRO).  The grips' "
        "FORWARD (finger-side) faces are UNVERIFIED -- no photo shows them; AOPA (2025-03-17) lists push-to-talk and "
        "checklist among the yoke's one-hand functions and only trim, TCS, AFCS DISC and MAP LIGHTS are seen: drawn "
        "as [E] PLACEHOLDERS (rev M, judges FID4-08): a PTT trigger on the outboard grip, a checklist rocker on the "
        "inboard grip (item 13, L6Y2 detail W; open point 7).",
        "GRIPS' 3-D LIE (L6Y2 photo check): rake / toe / a0 / walls / depth fitted per grip to the curated silhouettes "
        "of 6 views -- P1046408 L / R, P1046410, Mexico L / R and P1046409 (posed with a two-view camera, the co-pilot "
        "yoke 25° from inboard) -- with the front outline held: rake 20 +/-2.5, a0 -3.75 +/-3, walls 0.6 / 0 +/-0.2, "
        "depth 27 +/-4 (P1046409's slot wall; no bottom taper); the toe is weakly determined by views from inboard only "
        "(open point 2).  The AOPA photo is not used: its co-pilot camera is EXTRAPOLATED from the pilot-yoke solution "
        "(judges FID4-05; re-calibrating it on the panel round the co-pilot yoke is open) -- until then the toe, the "
        "depth law and the head depths stay [M weak].",
        f"Knee checks on the rev M solids: the 95th clears the yoke by {o95[0]:.1f} mm wings level (criterion 25 kept: "
        + ("passes" if o95[0] >= 25.0 else f"short by {25.0 - o95[0]:.1f}") +
        f"), roll to contact {o95[2]:.1f}°, keeping 25 mm to {max(o95[3], 0.0):.1f}° -- ACCEPTED AS MEASURED (owner "
        f"2026-10-05; L6B open point 1 closed).  K column = rev K re-swept: as issued "
        f"({REV_K_ISSUED['p95m'][0]:.0f} mm, {REV_K_ISSUED['p95m'][2]:.0f}°) the sweep had dropped a band of the "
        "inboard grip (a doubled vertex in the band clip, fixed in rev L).",
    ]
    y = notes(ds, x0, y + 2.0, x1, nts, title="NOTES", size=size, line_h=2.9)
    opn = [
        f"Fore-aft station: EVERY posed photo puts the aft face forward of the drawn neutral -- P1046408 -60 / -55, "
        f"P1046410 -65, P1046409 -37 (s/n 3001, gust lock on: 'CONTROLS LOCKED'), Mexico -38 / -34 and the AOPA "
        f"photo -14 / -26 (no lock placard) [+/-20-30 each along the line of sight].  Unlocked, a parked yoke rests "
        f"forward: the elevator droops trailing-edge down under its weight [E: physics, no PC-12 source].  Option: "
        f"neutral {STATION_SHIFT:.0f} further forward (hub_dx 140 -> {140 - STATION_SHIFT:.0f}): the 95th's contact "
        f"roll {STATION_KNEE[0]:.1f}° -> {STATION_KNEE[1]:.1f}°, wings-level clearance {STATION_KNEE[2]:.1f} -> "
        f"{STATION_KNEE[3]:.1f} mm (L6B sweep: the knees lie inside the +/-90 pitch-swept slab either way, so the "
        f"station does not move the knee rows).  Kept 140 (owner); rev P: the viewer parks the free yokes at the "
        f"unlocked photos' rest, 35 forward (YOKE rest; 3-D judges r3 FID3-02).",
        "Grip toe: all six usable views look from INBOARD (15-27°): the silhouettes prefer 7 (outboard, +5 % at 18) "
        "and 16.7 (inboard), the inboard PAD traces alone ~26 (judges FID4-06: both optima); the one view from "
        "outboard (AOPA, its camera extrapolated from the pilot-yoke solution, FID4-05) favours 18-26, and there the "
        "outboard pad's lower outer edge reaches the drawn grip silhouette (FID4-07: leather wrapping the outer edge "
        "low on the grip, or an outer frame + roll under 2.0 + R 1.5?) -- to decide after that camera's "
        "re-calibration.  Kept 18 / 18.  The trim head's depth is weak too: a -27 vs the judges' fit (110.7, 83.7, "
        "-23.6), P1046409 / 10 agreeing in sign (FID4-04).",
        "Column: CLOSED (owner 2026-10-11) -- the J band and the U recess re-centred on the column axis / roll pivot "
        "(hub WL 1845; the photos' joint line reads 1821 +/-10): recess h -48 .. 27 about it, the band 1.0 off the "
        "column; push travel 65 (was 90 [E]), pull 90 (L6Y2 detail J).  Still open: a J band or a full collar round "
        "the column.",
        "Shell skew (judges FID4-03): ONE left / right pattern in all 8 views of both yokes, each in its own sense "
        "(means of 8, + = photo outside): stem -1.5 / +1.7 (~1.6 inboard), arm tips +1.7 / -1.5 (both ~1.6 "
        "outboard), inboard arm top -1.7 / lower edge +1.7 (~1.7 low); crown, chamfers, foot within 1.2.  Kept "
        "SYMMETRIC: one decision for the stem, both tips and the inboard arm.",
        f"Knees: CLOSED (owner 2026-10-05) -- the 95th's {o95[0]:.1f} mm wings level (criterion 25 kept) and "
        f"contact from {o95[2]:.1f}° are accepted as measured.",
        "Crown soft break (R 20 [E]) vs a crease; hidden: body depth 60, the necks' depth 30, rocker / cap heights.",
        "Forward-face switches (PTT, checklist): drawn as [E] placeholders (item 13, L6Y2 detail W) -- a photo of a "
        "grip's finger side would replace them.",
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
