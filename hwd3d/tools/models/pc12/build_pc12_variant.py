#!/usr/bin/env python3
"""
hwd3d build of the pc12 model with a documented parameter override set (review fix rounds 2 and 3).

pc12/ is read-only for hwd3d (hwd3d/CLAUDE.md).  This script imports pc12's own builders unchanged
(Python run without bytecode, so nothing is written into pc12/), applies the overrides of
OVERRIDES[<set>] to module constants / functions *before* building, and writes the GLB + meta into hwd3d/out/
(gitignored).  tools/models/pc12/import_pc12.mjs --variant=<dir> then copies the result into
js/aircraft/models/ with the provenance (pc12 commit, dirty flag, override set, sha256 of every
pc12 source file used and of this script).

    python3 -B tools/models/pc12/build_pc12_variant.py --set=none   # must reproduce pc12/out/pc12.glb
    python3 -B tools/models/pc12/build_pc12_variant.py --set=fr2    # window / door layout + dihedral (fix round 2)
    python3 -B tools/models/pc12/build_pc12_variant.py --set=fr3    # + fuselage loft, glazing, wing / gear height, fairings,
                                                                    #   dorsal fin, strakes, winglet (fix round 3, default);
                                                                    #   iteration 2: flat 1.30 m cabin floor + layout clear
                                                                    #   of the doors, housing slot / rounded edges, blended
                                                                    #   belly-fairing section, antennas on the skin
Every fitted value below is a model parameter (knot, station, size) with a one-line basis; the drawing readings it was
fitted to are NOT in this repository (owner decision (b), 2026-11-13): they live in the gitignored
refs/cache/local/models/pilatus_pc12_meas.json, which tools/models/test_models.mjs compares the model with (SKIP when
absent).  See docs/phase3_models.md section 4.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
HWD = HERE.parents[2]
REPO = HWD.parent
PC12 = REPO / "pc12"
sys.path.insert(0, str(PC12))

MBP = ("Pilatus 'PC-12 NGX Model Building Plan' "
       "(https://www.pilatus-aircraft.com/assets/files/Model-Building-Plans/PC-12-NGX-Model-Building-Plan.pdf)")
DWG = "Pilatus drawing 190.10.40.432 (MBP sheet 1)"

# --------------------------------------------------------------------------------------------
# fr2 (review fix round 2): window / door stations and the wing dihedral.  Stations measured on DWG (side view from port,
# starboard detail view) and the MBP p.5 livery sheet (starboard windows: the two Pilatus documents disagree; the livery is
# used, docs/phase3_models.md section 4).  fr2 placed the openings relative to pc12's cabin crown (WL 2.630).
# --------------------------------------------------------------------------------------------
CROWN_MODEL = 2.630
FR2_LAYOUT = dict(
    WIN_HX=0.1475, WIN_HZ=0.190, WIN_R=0.065,
    WIN_CZ=round(CROWN_MODEL - 0.583, 3),                   # 2.047
    FIXED_WINDOWS={-1: [5.607, 6.201, 6.980], +1: [5.339, 6.967, 7.716, 8.469]},
    AIRSTAIR=dict(side=-1, cx=4.971, cz=1.775, hx=0.305, hz=0.675, r=0.09),   # 0.61 x 1.35 (sourced size)
    CARGO=dict(side=-1, cx=8.242, cz=1.780, hx=0.675, hz=0.660, r=0.10),      # 1.35 x 1.32 (sourced size)
    EXIT=dict(side=+1, cx=6.195, cz=round(CROWN_MODEL - 0.569, 3), hx=0.240, hz=0.320, r=0.07),
    DOOR_WINDOWS={"door_airstair": None, "door_cargo": 7.961, "exit_hatch": 6.195},
)
# reference-plane dihedral fitted to the shape of DWG's front-view wing outlines, pivoted about the main-gear butt line
FR2_WING = dict(DIHEDRAL_DEG=6.2, PIVOT_BL=2.265)

# --------------------------------------------------------------------------------------------
# fr3 (review fix round 3, findings P1-P3): pc12's fuselage loft re-fitted aft of the nose to DWG (profile, plan and the
# body-plan sections EF2..FR40), the cockpit glazing, openings at the drawing's absolute water lines, wing + main-gear
# trunnion raised with the cabin, a nose-gear housing, the belly fairing derived from the wing, dorsal fin / ventral
# strakes / fin LE / winglet to the drawing.  Stations: FR10 = STA 3.080 (spinner tip at STA 0.39, pc12's anchor).
# --------------------------------------------------------------------------------------------
# Control lines (pchip knots, model axes).  Knots at STA <= 2.80 (2.60 keel) are pc12's own (nose and cowling unchanged);
# the others are least-squares fits to the drawing's side-view profile (crown, keel), plan outline (half-breadth) and the
# super-ellipse fits of its body-plan sections (max-breadth WL, exponents), rounded to the millimetre (fix round 3
# iteration 2; changes the loft by < 0.5 mm).  Fit residuals: docs/phase3_models.md section 4.
FR3_LOFT = dict(
    top=[(0.95, 1.945), (1.20, 1.985), (1.60, 2.035), (2.20, 2.100), (2.80, 2.160),                    # pc12 (nose)
         (3.00, 2.175), (3.20, 2.231), (3.40, 2.338), (3.60, 2.444), (3.80, 2.552), (4.00, 2.659),       # DWG profile fit
         (4.20, 2.741), (4.40, 2.770), (4.60, 2.769), (9.00, 2.771), (9.60, 2.749), (10.2, 2.707),
         (10.8, 2.662), (11.4, 2.602), (12.0, 2.520), (12.5, 2.421), (13.0, 2.369),
         (13.7, 2.300), (14.36, 2.200)],                                         # tail cone end (under the rudder) [inf]
    bot=[(0.95, 1.365), (1.20, 1.315), (1.60, 1.225), (2.00, 1.140), (2.60, 1.020),                    # pc12 (nose)
         (3.00, 0.944), (3.40, 0.944), (5.50, 0.939), (7.00, 0.939), (8.23, 0.939), (8.60, 0.961),       # DWG profile fit
         (9.00, 1.019), (9.40, 1.097), (9.75, 1.179), (10.25, 1.303), (10.75, 1.423), (11.5, 1.560),
         (12.2, 1.684), (12.9, 1.800), (13.57, 1.912),
         (14.36, 2.045)],                                                        # pc12 tail cone end
    hw=[(0.95, 0.290), (1.20, 0.370), (1.60, 0.462), (2.20, 0.580), (2.80, 0.680),                     # pc12 (nose)
        (3.00, 0.726), (3.30, 0.769), (3.60, 0.805), (3.90, 0.829), (4.20, 0.843), (4.60, 0.845),        # DWG plan fit
        (9.00, 0.847), (9.40, 0.822), (9.75, 0.774), (10.3, 0.685), (10.8, 0.605), (11.3, 0.513),
        (11.85, 0.421), (12.3, 0.322), (12.75, 0.210), (13.05, 0.146),
        (13.7, 0.100), (14.36, 0.045)],                                          # tail cone end [inf] / pc12
    # body-plan section fits (frames FR10 3.08, FR12 3.58, FR14 4.08, FR16-30 4.59-8.23, FR33 9.00, FR36 9.75, FR38 10.80);
    # FR40 (11.85) is crowded by the dorsal fin and the strakes: an ellipse between its crown and keel [inf]
    zmw=[(0.95, 1.655), (2.00, 1.662),                                           # pc12 (prop axis / cowling)
         (3.08, 1.579), (3.58, 1.699), (4.08, 1.852), (4.59, 1.873), (8.23, 1.873), (9.00, 1.889), (9.75, 2.007),
         (10.80, 2.039), (11.85, 2.080), (13.00, 2.090), (14.36, 2.120)],
    ntop=[(0.95, 2.0), (2.00, 2.12),
          (3.08, 2.45), (3.58, 2.38), (4.08, 2.22), (4.59, 2.20), (8.23, 2.20), (9.00, 2.17), (9.75, 2.02), (10.80, 2.37),
          (11.85, 2.0), (14.36, 2.0)],
    nbot=[(0.95, 2.0), (2.00, 2.18),
          (3.08, 2.74), (3.58, 2.98), (4.08, 3.24), (4.59, 3.23), (8.23, 3.23), (9.00, 3.74), (9.75, 3.25), (10.80, 2.52),
          (11.85, 2.0), (14.36, 2.0)],
)
# Cockpit glazing (pc12/model/cockpit_glazing.py constants), fitted to DWG's side and plan views.  The PRO deletes the
# pilot's direct-vision window the drawing (NGX) shows, so the side window is the drawing's main side window only.
FR3_GLAZING = dict(
    WS_PLAN=[(3.300, 0.034), (3.315, 0.250), (3.360, 0.450), (3.470, 0.625), (4.005, 0.510), (3.865, 0.034)],  # plan
    PILLAR=((3.430, 2.165), (4.000, 2.550)),                     # windshield lower-rear edge in side view
    SW_CORE=[(3.878, 2.130), (4.228, 2.130), (4.312, 2.214), (4.312, 2.375), (4.205, 2.468), (4.040, 2.493),
             (3.812, 2.322)], SW_R=0.040,                         # side window: rounded polygon (core + radius), side view
    SPLIT_FWD=4.42,                                               # fwd / centre skin joint aft of the side window [inf]
)
# Openings at the drawing's absolute water lines (centres of the drawn outlines); door opening sizes stay the sourced
# 0.61 x 1.35 / 1.35 x 1.32 m; window 0.300 x 0.384 m as drawn; exit centre 0.569 below the crown (starboard detail view)
FR3_LAYOUT = dict(FR2_LAYOUT, WIN_HX=0.150, WIN_HZ=0.192, WIN_CZ=2.187,
                  AIRSTAIR=dict(FR2_LAYOUT["AIRSTAIR"], cz=1.928), CARGO=dict(FR2_LAYOUT["CARGO"], cz=1.892),
                  EXIT=dict(FR2_LAYOUT["EXIT"], cz=round(2.769 - 0.569, 3)))
# Wing: fr2 dihedral, raised by the mean offset of DWG's front-view upper / lower outlines from the fr2 wing (0.117 / 0.126);
# the reference plane is flat inboard of the fuselage side (BL 0.85) so the carry-through stays inside the drawn belly
# fairing [inf].  The main-gear trunnion (in the wing at BL 2.265) rises 0.104 m, 17 mm less than the wing, so the
# retracted tyre still protrudes (11 mm as in fr2; POH ~1 in) [inf]; the wheel well moves inboard by the same
# amount (the longer leg folds the wheel further in)
FR3_WING = dict(FR2_WING, DZ=0.121, KINK_BL=0.85, GEAR_DZ=0.104)
# Nose-gear housing below the keel: the box DWG's side view draws under the cockpit (front station and bottom WL fitted to
# it), needed once the keel is at the drawn height (pc12's retracted nose wheel reaches below it).  Width not drawn: nose bay
# + 0.10 m each side [inf]; rounded lower edges (section exponent 3) [inf]; rear end aft of the drawn one so the whole bay
# opening lies on the flat floor and the housing's end wall clears the bay liner [inf]; a slot for the strut and the taxi
# lamp, which (pc12 gear geometry) pass the floor ahead of the bay with the gear down, through the housing floor and the
# doors' forward inner corners [inf]
FR3_NOSE_HOUSING = dict(x0=2.887, x1=4.300, z_bottom=0.793, half_width=0.240, n=3.0, r_end=0.04,
                        slot=dict(x0=2.905, x1=3.135, hy=0.080, r=0.03))
# Belly fairing: drawn extent STA 5.12-7.50 and centre-line lower outline (side view) [knots fitted to DWG]; plan
# half-width: pc12's table compressed to the drawn extent [inf].  Section (fix round 3 iteration 2, finding F6): the lower
# surface runs from the drawn bottom on the centre line (or 3 mm under the surface it covers, where that is lower; P1) out
# to 3 mm under the surface it covers (wing lower skin, else fuselage underside) at its edge, as (1 - t^p) of the local
# half-width, so it meets the wing at a shallow angle instead of a vertical lip [inf: shape]
FR3_BELLY = dict(
    width=[(5.12, 0.12), (5.30, 0.45), (5.60, 0.66), (6.20, 0.72), (7.00, 0.66), (7.35, 0.40), (7.50, 0.12)],
    bottom=[(5.12, 0.990), (5.35, 0.927), (5.65, 0.880), (5.90, 0.872), (6.40, 0.879), (7.00, 0.910), (7.30, 0.950),
            (7.50, 0.985)],
    margin=0.003, p=2.0, n=3.2)
# Dorsal fin: top edge = DWG side view (from the crown at FR33 to the fin LE), base half-width ~0.10 (FR38 / FR40 sections)
FR3_DORSAL = dict(top=[(9.000, 2.771), (10.000, 2.904), (11.000, 3.038), (12.100, 3.185), (12.360, 3.249), (12.530, 3.390)],
                  tc=0.065)
# Fin leading edge: DWG side view (above the dorsal); pc12 FIN_LE was 0.13-0.15 m further aft
FR3_FIN_LE = ((11.648, 2.35), (13.106, 4.07))
# Ventral strakes: DWG side view (root line on the fuselage side, outer edge, trailing edge); outward offset of the outer
# edge 0.15 m [inf] (FR38 / FR40 sections), thickness 4 % as pc12
FR3_STRAKES = dict(root=((9.77, 1.37), (12.19, 1.95)), outer=((9.83, 1.33), (11.87, 1.53)), out=0.15)
# Winglet: chord / trailing-edge laws, top chord and height (straight part 0.262 m, pc12 0.30) fitted to DWG's side view
# (leading / trailing edge and top chord within 2 cm; top between the side and front views' tops); bend radius and cant
# kept; the planform is re-derived so the span over the winglets stays the published 16.28 m and the area 25.81 m2
FR3_WINGLET = dict(WL_MID_CHORD=0.67, WL_TIP_CHORD=0.40, WL_TE_SWEEP=0.448, P_TE=0.70, P_C=1.17, WL_HEIGHT=0.262, WL_SKIN=0.0155)

# Cabin layout (fix round 3 iteration 2): pc12's interior.build_cabin with its stations moved for fr2's openings at the
# drawn stations - pc12's port side ledge ran across the airstair (STA 4.67-5.28) and cargo doors and its forward club seat
# stood in the airstair doorway.  Seats, club tables and the baggage net 0.40 m aft (the port club seats on the port
# windows), the port ledge between the two doors with 5 cm clear [inf: layout]; floor flat, sourced 1.30 m wide (F2)
FR3_CABIN = dict(rows=[(5.65, -1), (6.95, +1), (8.05, +1)], seat_bl=0.40, table_x=6.30, net_x=8.60, ledge=(4.85, 8.05),
                 door_clear=0.05)

OVERRIDES = {
    "none": {},
    "fr2": {"layout": FR2_LAYOUT, "wing": FR2_WING},
    "fr3": {"loft": FR3_LOFT, "glazing": FR3_GLAZING, "layout": FR3_LAYOUT, "wing": FR3_WING,
            "nose_housing": FR3_NOSE_HOUSING, "belly": FR3_BELLY, "dorsal": FR3_DORSAL, "fin_le": FR3_FIN_LE,
            "strakes": FR3_STRAKES, "winglet": FR3_WINGLET, "cabin": FR3_CABIN},
}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def git(*args) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True).stdout.strip()


def source_hashes():
    files = sorted(list((PC12 / "cad").glob("*.py")) + list((PC12 / "model").glob("*.py")))
    tree = hashlib.sha256()
    out = {}
    for f in files:
        h = sha256_file(f)
        out[str(f.relative_to(REPO))] = h
        tree.update(f"{f.relative_to(REPO)} {h}\n".encode())
    return out, tree.hexdigest()


# --------------------------------------------------------------------------------------------
# fr2 appliers
# --------------------------------------------------------------------------------------------
def apply_layout(o):
    from model import fuselage_parts as FP
    for k, v in o.items():
        if k == "DOOR_WINDOWS":
            continue
        setattr(FP, k, v)
    dw = o["DOOR_WINDOWS"]
    FP.DOOR_WINDOWS = dict(dw)
    # build_glazing() names the cabin-window part "9 fixed" with qty 9: keep its count honest.
    n = sum(len(v) for v in o["FIXED_WINDOWS"].values())
    orig_glazing = FP.build_glazing

    def build_glazing(parts_out):
        orig_glazing(parts_out)
        g = parts_out.get("glazing_cabin")
        if g is not None:
            g.name = f"Cabin windows ({n} fixed, stretched acrylic)"
            g.qty = n
    FP.build_glazing = build_glazing


def apply_wing(o, dihedral_deg):
    from model import wing as W
    d0 = W.DIHEDRAL
    d1 = np.radians(dihedral_deg)
    # same reference-plane height at the pivot butt line: Z_QC0 + y tan(D) unchanged at y = PIVOT_BL
    W.Z_QC0 = float(W.Z_QC0 + o["PIVOT_BL"] * (np.tan(d0) - np.tan(d1)))
    W.DIHEDRAL = float(d1)
    out = {"DIHEDRAL_deg": [float(np.degrees(d0)), dihedral_deg], "Z_QC0": W.Z_QC0}
    if o.get("DZ"):
        W.Z_QC0 = float(W.Z_QC0 + o["DZ"])
        out["Z_QC0"] = W.Z_QC0
    if o.get("KINK_BL"):
        yk = o["KINK_BL"]
        orig = W.section_at

        def section_at(y):
            s = orig(y)
            if y < yk:
                s.le = s.le + np.array([0.0, 0.0, (yk - y) * np.tan(W.DIHEDRAL)])
            return s
        W.section_at = section_at
    return out


# --------------------------------------------------------------------------------------------
# fr3 appliers
# --------------------------------------------------------------------------------------------
LOFT_OLD = {}


def apply_loft(o):
    """Replace pc12's control lines (module pchips) before anything that caches them is imported."""
    from cad.mesh import pchip
    from model import fuselage as F
    for key, fn, ctl in (("top", "z_top", "_top"), ("bot", "z_bot", "_bot"), ("hw", "half_w", "_hw"),
                         ("zmw", "z_mw", "_zmw"), ("ntop", "n_top", "_ntop"), ("nbot", "n_bot", "_nbot")):
        LOFT_OLD[key] = getattr(F, fn)
        knots = sorted(o[key])
        setattr(F, ctl, knots)
        setattr(F, fn, pchip(*zip(*knots)))
    F.CONTROL_LINES = dict(crown=F._top, keel=F._bot, half_breadth=F._hw, max_breadth_wl=F._zmw)


def loft_map(V, inverse=False):
    """Map points between pc12's original fuselage frame and the re-fitted one (per station: the same fraction of the
    upper / lower half-height about the max-breadth WL, butt line scaled with the half-breadth).  Used for the parts that
    pc12 places at absolute heights inside / on the fuselage (interior, livery lines)."""
    from model import fuselage as F
    if not LOFT_OLD:
        return V
    old = {k: LOFT_OLD[k] for k in ("top", "bot", "hw", "zmw")}
    new = {"top": F.z_top, "bot": F.z_bot, "hw": F.half_w, "zmw": F.z_mw}
    a, b = (new, old) if inverse else (old, new)
    V = np.array(V, float)
    x = np.clip(V[:, 0], 0.95, 14.36)
    z = V[:, 2]
    za, zb = a["zmw"](x), b["zmw"](x)
    up = z >= za
    u = np.where(up, (z - za) / (a["top"](x) - za), (za - z) / (za - a["bot"](x)))
    V[:, 2] = np.where(up, zb + u * (b["top"](x) - zb), zb - u * (zb - b["bot"](x)))
    V[:, 1] = V[:, 1] * b["hw"](x) / a["hw"](x)
    return V


def apply_glazing(o):
    from cad import sdf2d
    from model import cockpit_glazing as CG
    from model import fuselage_parts as FP
    CG.WS_PLAN = list(o["WS_PLAN"])
    CG.PILLAR = tuple(o["PILLAR"])
    core, r = np.array(o["SW_CORE"]), o["SW_R"]

    def sidewindow_sdf(x, y, z):
        d = sdf2d.rounded_polygon(x, z, core, r)
        return np.where(np.abs(y) > 0.30, d, 10.0)
    CG.sidewindow_sdf = sidewindow_sdf
    FP.SPLIT_FWD = o["SPLIT_FWD"]
    # pc12's build_glazing samples the cockpit side window and the windshield on fixed skin patches; same code with
    # patches sized to the new outlines
    from cad.mesh import Mesh, trim, band
    from model.parts import Part
    sw_lo, sw_hi = core.min(0) - r - 0.03, core.max(0) + r + 0.03
    ws = np.array(o["WS_PLAN"])

    def build_glazing(parts_out):
        glass_parts, seals = [], []
        for side, stations in FP.FIXED_WINDOWS.items():
            for cx in stations:
                oo = dict(cx=cx, cz=FP.WIN_CZ, hx=FP.WIN_HX, hz=FP.WIN_HZ, r=FP.WIN_R)
                p = FP.side_patch(oo, side, pad=0.03, d=0.013)
                fn = lambda m, cx=cx: FP.window_sdf(m.V[:, 0], m.V[:, 2], cx)
                glass_parts.append(trim(p, fn(p) - 0.010, "negative").offset(-0.006))
                seals.append(band(p, fn, -0.006, 0.010).offset(0.0015))
        sw_glass, sw_seal = [], []
        for side in (-1, 1):
            oo = dict(cx=0.5 * (sw_lo[0] + sw_hi[0]), cz=0.5 * (sw_lo[1] + sw_hi[1]), hx=0.5 * (sw_hi[0] - sw_lo[0]),
                      hz=0.5 * (sw_hi[1] - sw_lo[1]), r=0.0)
            p = FP.side_patch(oo, side, pad=0.0, d=0.014)
            fn = lambda m: CG.sidewindow_sdf(m.V[:, 0], m.V[:, 1], m.V[:, 2])
            sw_glass.append(trim(p, fn(p) - 0.010, "negative").offset(-0.005))
            sw_seal.append(band(p, fn, -0.006, 0.012).offset(0.0015))
        p = FP.skin_patch(ws[:, 0].min() - 0.06, ws[:, 0].max() + 0.06, -0.22, 0.22, d=0.012)
        fn = lambda m: CG.windshield_sdf(m.V[:, 0], FP.signed_s(m.V[:, 0], m.UV[:, 1]), m.V[:, 2], m.V[:, 1])
        ws_glass = trim(p, fn(p) - 0.012, "negative").offset(-0.004)
        ws_seal = band(p, fn, -0.006, 0.014).offset(0.0015)
        n = sum(len(v) for v in FP.FIXED_WINDOWS.values())
        g = Part("glazing_cabin", f"Cabin windows ({n} fixed, stretched acrylic)", "glazing", explode=(0, 0, 0),
                 group="Glazing", qty=n, material_note="Two-ply laminated stretched acrylic")
        g.add(Mesh.merge(glass_parts), "glass").add(Mesh.merge(seals), "seal")
        parts_out[g.id] = g
        w = Part("glazing_flightdeck", "Windshield (2 heated panes) & side windows (no DV window, PRO)", "glazing",
                 explode=(-0.3, 0, 0.35), group="Glazing", qty=4,
                 material_note="Heated laminated glass windshield, acrylic side windows")
        w.add(ws_glass, "glass_windshield").add(Mesh.merge(sw_glass), "glass").add(Mesh.merge([ws_seal] + sw_seal), "seal")
        parts_out[w.id] = w
    FP.build_glazing = build_glazing


def apply_gear(dz):
    """Main gear: trunnion (in the raised wing) up by dz, the leg longer by dz; the folding side brace's wing attachment and
    leg attachment up by dz; the wheel well (where the longer leg puts the retracted wheel) inboard by dz."""
    from model import gear as G
    from model import bays as BY
    G.MAIN_TRUNNION = G.MAIN_TRUNNION + np.array([0.0, 0.0, dz])
    BY.WELL["cy"] = round(BY.WELL["cy"] - dz, 4)
    from cad.mesh import Mesh, cylinder, superellipsoid
    from model.parts import Part
    from model.brace import solve_knee

    def brace_parts(parts):     # pc12 gear.brace_parts with the main-gear attachment heights + dz
        specs = []
        for side, sgn in (("R", 1), ("L", -1)):
            T = G.MAIN_TRUNNION * [1, sgn, 1]
            A = np.array([6.0, 1.95 * sgn, 1.00 + dz])
            B0 = np.array([6.0, 2.215 * sgn, 0.76 + dz])
            ref = np.array([0, -0.30 * sgn, 0.95])
            specs.append((f"brace_main_{side}", f"gear_main_{side}", A, B0, T, np.array([1.0, 0, 0]), ref,
                          f"{'Right' if sgn > 0 else 'Left'} main-gear folding side brace"))
        specs.append(("brace_nose", "gear_nose", np.array([3.46, 0, 1.16]), np.array([3.033, 0, 0.80]), G.NOSE_PIVOT,
                      np.array([0, 1.0, 0]), np.array([0.72, 0, -0.695]), "Nose-gear folding drag brace"))
        for pid, gear_id, A, B0, T, axis, ref, name in specs:
            L = np.linalg.norm(B0 - A) / 2 * 1.0005
            K0 = solve_knee(A, B0, L, L, axis, ref)
            up = Part(pid + "_up", name + " (upper link)", "gear",
                      pivot=dict(origin=A.tolist(), axis=axis.tolist(), kind="brace", role="upper", gear=gear_id,
                                 A=A.tolist(), B0=B0.tolist(), K0=K0.tolist(), L1=float(L), L2=float(L), bend=ref.tolist()),
                      group="Landing gear", material_note="Over-centre lock, down-lock spring")
            up.add(Mesh.merge([cylinder(A, K0, 0.022, n=12), superellipsoid(A, (0.03, 0.03, 0.03), (1, 1), 8, 12),
                               superellipsoid(K0, (0.028, 0.028, 0.028), (1, 1), 8, 12)]), "gear_leg")
            lo = Part(pid + "_lo", name + " (lower link)", "gear", parent=pid + "_up",
                      pivot=dict(origin=K0.tolist(), axis=axis.tolist(), kind="brace", role="lower", gear=gear_id),
                      group="Landing gear", material_note="Over-centre lock")
            lo.add(Mesh.merge([cylinder(K0, B0, 0.02, n=12), superellipsoid(B0, (0.028, 0.028, 0.028), (1, 1), 8, 12)]),
                   "gear_leg")
            parts[up.id] = up
            parts[lo.id] = lo
    G.brace_parts = brace_parts
    return {"MAIN_TRUNNION": G.MAIN_TRUNNION.tolist(), "WELL_cy": BY.WELL["cy"]}


def apply_nose_housing(o):
    """A rounded box under the keel around the nose-gear bay (DWG side view) + the nose doors and bay liner moved to its
    bottom (pc12 builds them on the fuselage keel), with a slot for the strut ahead of the bay (finding F5 of fix round 3,
    iteration 2: with the gear down pc12's strut and taxi lamp pass the floor at STA 2.92-3.11)."""
    from cad.mesh import Mesh, grid_surface, trim, solidify
    from cad import sdf2d
    from model import gear as G
    from model import fuselage as F
    from model.parts import Part
    zb, n, re = o["z_bottom"], o["n"], o["r_end"]
    sl = o["slot"]
    keel = F.z_bot    # the (re-fitted) keel line, captured before bay_tubs swaps F.z_bot

    def end_k(x):     # rounded ends (side and plan): 0 at the ends, 1 from r_end inwards
        e = min(x - o["x0"], o["x1"] - x)
        return float(np.sqrt(max(0.0, 1 - max(0.0, 1 - e / re) ** 2))) if e > 0 else 0.0

    def frame(x):     # half-width, rim height (6 cm inside the fuselage above the keel) and depth at station x
        k = end_k(x)
        top = float(keel(x)) + 0.06
        return o["half_width"] * (0.55 + 0.45 * k), top, max((top - zb) * k, 0.002)

    def bottom_z(x, y):   # outer surface of the housing's lower half at (x, |y|): super-ellipse (|y|/w)^n + (dz/h)^n = 1
        w, top, h = frame(float(x))
        t = min(abs(float(y)) / w, 1.0)
        return top - h * (1 - t ** n) ** (1 / n)

    def slot_sdf(x, y):
        return sdf2d.rrect(x, y, 0.5 * (sl["x0"] + sl["x1"]), 0.0, 0.5 * (sl["x1"] - sl["x0"]), sl["hy"], sl["r"])

    def housing_mesh():
        # open-topped U (lower half of a super-ellipse) whose rim sits 6 cm inside the fuselage above the keel
        xs = np.linspace(o["x0"], o["x1"], 72)
        ts = np.linspace(0.25, 0.75, 61)
        rows = []
        for x in xs:
            w, top, h = frame(x)
            a = 2 * np.pi * ts
            y = w * np.sign(np.sin(a)) * np.abs(np.sin(a)) ** (2 / n)
            z = top + h * np.sign(np.cos(a)) * np.abs(np.cos(a)) ** (2 / n)
            rows.append(np.stack([np.full_like(y, x), y, z], 1))
        P = np.array(rows)
        m = grid_surface(P)
        out = (P - np.array([0.0, 0.0, 1.0]) * P[:, :1, 2:3]).reshape(-1, 3) * [0, 1, 1]
        if np.mean(np.sum(out * m.N, 1)) < 0:
            m = m.flipped()
        return m

    def door_mesh(sgn):
        # pc12's clamshell door (gear.build_nose: rounded-rectangle bay outline less 4 mm, split at the centre line, 18 mm
        # solid) on the housing's curved bottom, with the strut slot notched out of its forward inner corner
        b = G.NOSE_BAY
        xs = np.linspace(b["cx"] - b["hx"] - 0.02, b["cx"] + b["hx"] + 0.02, 40)
        ys = sgn * np.linspace(0.0, b["hy"] + 0.02, 12)
        P = np.array([[[x, y, bottom_z(x, y) + 0.001] for y in ys] for x in xs])
        m = grid_surface(P)
        if m.N[:, 2].mean() > 0:
            m = m.flipped()
        f = lambda mm: np.maximum(np.maximum(sdf2d.rrect(mm.V[:, 0], mm.V[:, 1], b["cx"], b["cy"], b["hx"] - 0.004,
                                                         b["hy"] - 0.004, b["r"]), -sgn * mm.V[:, 1] - 0.002),
                                  -(slot_sdf(mm.V[:, 0], mm.V[:, 1]) - 0.004))
        m = trim(m, f(m), "negative")
        return solidify(m.offset(-0.001), 0.018)

    orig_build_nose, orig_tubs = G.build_nose, G.bay_tubs

    def build_nose(parts):
        orig_build_nose(parts)
        # doors: replaced by the same construction on the housing bottom (+ slot); hinge height re-read from the new door
        for side, sgn in (("R", 1), ("L", -1)):
            dp = parts[f"gear_door_N{side}"]
            m = door_mesh(sgn)
            dp.meshes = [(m, mat) for _, mat in dp.meshes[:1]]
            hy = sgn * (G.NOSE_BAY["hy"] - 0.004)
            near = np.abs(m.V[:, 1] - hy) < 0.02
            dp.pivot["origin"][2] = float(np.mean(m.V[near, 2])) if near.any() else dp.pivot["origin"][2]
        hm = housing_mesh()
        b = G.NOSE_BAY
        V = hm.V
        cut = np.minimum(sdf2d.rrect(V[:, 0], V[:, 1], b["cx"], b["cy"], b["hx"], b["hy"], b["r"]), slot_sdf(V[:, 0], V[:, 1]))
        f = np.where(V[:, 2] < keel(V[:, 0]) - 0.01, cut, 1.0)   # open the floor / lower end wall only, not the rim
        hm = trim(hm, f, "positive")
        p = Part("nose_gear_housing", "Nose-gear housing (below the cockpit floor)", "fuselage_fwd", explode=(-0.4, 0, -0.6),
                 group="Fuselage", material_note="Housing for the retracted nose wheel, doors and a strut slot in its floor")
        p.add(hm, "paint_white")
        parts[p.id] = p

    def bay_tubs(parts):
        # pc12 hangs the nose-bay liner from the keel (z_bot + 0.01): hang it from the housing floor instead, 3 mm inside the
        # floor's outer surface at every outline point (fr3 hung it 6 mm below that surface: a lime line under the housing)
        orig_tubs(parts)
        b = G.NOSE_BAY
        for m, _ in parts["gear_bays"].meshes:
            sel = (m.V[:, 0] > b["cx"] - b["hx"] - 0.01) & (m.V[:, 0] < b["cx"] + b["hx"] + 0.01) & (m.V[:, 2] < 1.2)
            for i in np.nonzero(sel)[0]:
                m.V[i, 2] = bottom_z(m.V[i, 0], m.V[i, 1]) + 0.003
            if sel.any():
                m.compute_normals()
    G.build_nose, G.bay_tubs = build_nose, bay_tubs
    from model import livery as LV
    if "nose_gear_housing" not in LV.PAINTED:
        LV.PAINTED.append("nose_gear_housing")


def apply_belly(o):
    from cad.mesh import Mesh, grid_surface, cap_ring, pchip
    from model import details as D
    from model import wing as W
    from model import fuselage as F
    wf, bf = pchip(*zip(*o["width"])), pchip(*zip(*o["bottom"]))
    n, p, mg = o["n"], o["p"], o["margin"]
    stats = {"lowered_mm": 0.0}

    def wing_lower(x, y):
        s = W.section_at(y)
        u = (x - s.le[0]) / s.chord
        if not (0.0 <= u <= 1.0):
            return None
        return float(s.lower(np.array(u))[2])

    def fus_lower(x, y):    # the fuselage OML's lower half at (x, |y|) (pc12's super-ellipse section law)
        zm, zk, hw, nb = float(F.z_mw(x)), float(F.z_bot(x)), float(F.half_w(x)), float(F.n_bot(x))
        r = min(abs(y) / hw, 1.0)
        return zm - (zm - zk) * (1 - r ** nb) ** (1 / nb)

    def base(x, y):         # the lowest surface the fairing covers at (x, |y|)
        zw, zf = wing_lower(x, abs(y)), fus_lower(x, y)
        return zf if zw is None else min(zw, zf)

    def lower_z(x, y):      # the fairing's lower surface
        w = float(wf(x))
        b0 = base(x, 0.0) - mg
        dep = max(0.0, b0 - float(bf(x)))
        t = min(abs(y) / w, 1.0)
        return base(x, y) - mg - dep * (1 - t ** p)

    def belly_fairing():
        # ring per station: upper half (phi 0..pi) a super-ellipse buried in the wing / fuselage, from the edge points up to
        # the keel + 0.15; lower half (phi pi..2 pi) the blended lower surface above
        xs = np.linspace(o["width"][0][0], o["width"][-1][0], 64)
        ts = np.linspace(0, 1, 112, endpoint=False)
        rows = []
        for x in xs:
            w = float(wf(x))
            phi = 2 * np.pi * ts
            yy = w * np.cos(phi)
            ze = lower_z(x, w)
            zt = max(float(F.z_bot(x)) + 0.15, ze + 0.05)
            zz = np.array([ze + (zt - ze) * np.abs(np.sin(f)) ** (2 / n) if f <= np.pi else lower_z(x, y)
                           for f, y in zip(phi, yy)])
            # how far the centre line lies below the visible side-view outline (the drawn bottom, or the fuselage keel where
            # the drawn line runs inside the fuselage) beyond the margin: > 0 only where the wing hangs lower (P1)
            vis = min(float(bf(x)), fus_lower(x, 0.0) - mg)
            stats["lowered_mm"] = max(stats["lowered_mm"], (vis - lower_z(x, 0.0)) * 1000)
            rows.append(np.stack([np.full_like(yy, x), yy, zz], 1))
        P = np.array(rows)
        m = grid_surface(P, close_v=True)
        cen = P.mean(1)
        if np.mean(np.sum((P - cen[:, None]).reshape(-1, 3) * m.N, 1)) < 0:
            m = m.flipped()
        return Mesh.merge([m, cap_ring(P[0], (-1, 0, 0)), cap_ring(P[-1], (1, 0, 0))])
    D.belly_fairing = belly_fairing
    # the lower red beacon sits on the fairing bottom (pc12: WL 0.738 under its own fairing at STA 7.40)
    orig_build = D.build

    def build(parts):
        orig_build(parts)
        lp = parts.get("lights")
        if lp is not None:
            x0, z0 = 7.40, 0.738
            znew = lower_z(x0, 0.0) - 0.012
            for m, mat in lp.meshes:
                if mat == "light_red":
                    sel = (np.abs(m.V[:, 0] - x0) < 0.08) & (np.abs(m.V[:, 1]) < 0.06) & (np.abs(m.V[:, 2] - z0) < 0.05)
                    m.V[sel, 2] += znew - z0
        return parts
    D.build = build
    return stats


def apply_empennage(dorsal, fin_le, strakes):
    from cad.mesh import Mesh, cap_ring
    from model import empennage as E
    from model.airfoil import naca00
    from model.lifting import Section, skin, strip, cos_pts
    from model import fuselage as F
    if fin_le:
        E.FIN_LE = tuple(tuple(p) for p in fin_le)
    if strakes:
        (ra, rb), (oa, ob), out = strakes["root"], strakes["outer"], strakes["out"]

        def build_strakes():
            ms = []
            for sgn in (1, -1):
                def pt(x, z, extra=0.0):
                    return np.array([x, sgn * (float(F.side_y(x, z)) - 0.01 + extra), z])
                rl, rt = pt(*ra), pt(*rb)
                ol, ot = pt(*oa, extra=out), pt(*ob, extra=out)

                def sec(s, sgn=sgn):
                    le = rl + s * (ol - rl)
                    te = rt + s * (ot - rt)
                    c = te - le
                    L = float(np.linalg.norm(c))
                    e_c = c / L
                    span = (ol + ot - rl - rt) / 2
                    e_t = np.cross(np.cross(e_c, span), e_c)
                    e_t = e_t / np.linalg.norm(e_t)
                    return Section(le=le, chord=L, e_c=e_c, e_t=np.cross(e_t, e_c) * sgn, twist=0.0, airfoil=naca00(0.04))
                ss = np.linspace(0, 1, 6)
                m = Mesh.merge([skin(sec, ss, n=24), strip(sec, ss, 1.0, 1.0)])
                last = sec(1.0)
                xx = cos_pts(24)
                loop = np.vstack([last.lower(xx[::-1]), last.upper(xx[1:-1])])
                m = Mesh.merge([m, cap_ring(loop, (ol + ot - rl - rt) / 2)])
                ms.append(m)
            from model.parts import Part
            p = Part("strakes", "Ventral strakes (2)", "empennage_v", explode=(0.6, 0, -0.8), group="Empennage",
                     qty=2, material_note="Kevlar / honeycomb sandwich")
            p.add(Mesh.merge(ms), "paint_white")
            return p
        E.build_strakes = build_strakes
    if dorsal:
        tx, tz = np.array([p[0] for p in dorsal["top"]]), np.array([p[1] for p in dorsal["top"]])
        from cad.mesh import pchip
        top = pchip(tx, tz)
        xs = np.linspace(tx[0], tx[-1], 400)
        zs = top(xs)
        z0, z1 = float(zs[0]), float(zs[-1])

        def dorsal_section(z):
            # LE on the drawn top edge; below its start height the section begins at the start station (inside the crown)
            x_le = float(np.interp(z, zs, xs)) if z > z0 else float(tx[0])
            x_end = E._lin(*E.FIN_LE, z) + 0.45
            return Section(le=np.array([x_le, 0.0, z]), chord=x_end - x_le, e_c=np.array([1.0, 0, 0]),
                           e_t=np.array([0, 1.0, 0]), twist=0.0, airfoil=naca00(dorsal["tc"]))
        E.dorsal_section = dorsal_section
        orig_build = E.build

        def build(parts):
            orig_build(parts)
            from model.wing import span_stations
            zd = np.concatenate([span_stations(2.36, z0, 0.06), span_stations(z0, z1 - 0.004, 0.04)[1:]])
            dm = Mesh.merge([skin(dorsal_section, zd, n=48), strip(dorsal_section, zd, 1.0, 1.0)])
            last = dorsal_section(zd[-1])
            xx = cos_pts(48)
            loop = np.vstack([last.lower(xx[::-1]), last.upper(xx[1:-1])])
            dm = Mesh.merge([dm, cap_ring(loop, (0, 0, 1))])
            parts["dorsal_fin"].meshes = [(dm, "paint_white")]
            return parts
        E.build = build


def apply_winglet(o):
    """pc12's winglet with its chord / trailing-edge laws bent toward the drawn side view: the trailing edge moves aft as
    (s/L)**P_TE of the arc length (pc12: linear), the chord falls from the blend to the top as ((s-s1)/(L-s1))**P_C."""
    from model import wing as W
    from cad.mesh import Mesh, grid_surface, cap_ring
    from model.airfoil import naca00
    from model.lifting import Section, cos_pts
    for k, v in o.items():
        if k.startswith("WL_"):
            setattr(W, k, v)
    p_te, p_c = o.get("P_TE", 1.0), o.get("P_C", 1.0)

    def build_winglet():
        arr, seg = W.winglet_path()
        L = seg[-1]
        s1 = W.WL_BEND_R * (np.pi / 2 - W.WL_CANT)
        sec0 = W.section_at(W.SEMI)
        te0 = sec0.le[0] + sec0.chord
        tipaf = naca00(0.09)
        rows = []
        for (y, z, a), s in zip(arr, seg):
            u = min(s / s1, 1.0)
            blend = u * u * (3 - 2 * u)
            if s <= s1:
                c = W.C_TIP + (W.WL_MID_CHORD - W.C_TIP) * blend
            else:
                c = W.WL_MID_CHORD + (W.WL_TIP_CHORD - W.WL_MID_CHORD) * ((s - s1) / (L - s1)) ** p_c
            te = te0 + W.WL_TE_SWEEP * (s / L) ** p_te
            sec = Section(le=np.array([te - c, y, z]), chord=c, e_c=np.array([1.0, 0, 0]),
                          e_t=np.array([0.0, -np.sin(a), np.cos(a)]), twist=W.INC_TIP * (1 - blend),
                          airfoil=sec0.airfoil.blend(tipaf, min(1.0, s / s1)))
            n = 60
            rows.append(np.vstack([sec.lower(cos_pts(n)[::-1]), sec.upper(cos_pts(n)[1:])]))
        P = np.array(rows)
        m = grid_surface(P)
        i = P.shape[1] // 2 + 20
        if np.dot(m.N[i], np.array([0, 0, 1.0])) < 0:
            m = m.flipped()
        te = grid_surface(np.stack([P[:, 0], P[:, -1]], 1))
        if np.dot(te.N.mean(0), [1, 0, 0]) < 0:
            te = te.flipped()
        cap = cap_ring(P[-1], P[-1].mean(0) - P[-2].mean(0))
        return Mesh.merge([m, te, cap]), P
    W.build_winglet = build_winglet
    # pc12 derives the planform's winglet-root butt line from the winglet's outer skin at the top (WL_SKIN, thickness of a
    # 9 % section of the top chord): a longer top chord thickens it, so SEMI and the planform constants are re-derived to
    # keep the published 16.28 m span over the winglets and the 25.81 m2 reference area
    if "WL_HEIGHT" in o:
        a_end = np.pi / 2 - W.WL_CANT
        W.WL_LATERAL = W.WL_BEND_R * np.sin(a_end) + W.WL_HEIGHT * np.cos(a_end)
    if "WL_SKIN" in o or "WL_HEIGHT" in o:
        W.SEMI = W.SPAN_TOTAL / 2 - W.WL_LATERAL - W.WL_SKIN
        W.C_ROOT = W.AREA_REF / W.SEMI / (1 + W.TAPER)
        W.C_TIP = W.TAPER * W.C_ROOT
        W.MAC = 2 / 3 * W.C_ROOT * (1 + W.TAPER + W.TAPER ** 2) / (1 + W.TAPER)
        W.LEMAC = W.AFT_CG - W.AFT_CG_MAC * W.MAC
        W.X_QC = W.LEMAC + 0.25 * W.MAC


CABIN_FLOOR_W = 1.30   # sourced cabin floor width (pc12/CLAUDE.md "Sourced facts": cabin floor 1.30 m)


def apply_interior_livery(cab):
    """pc12 places the interior and the livery lines at absolute water lines: carry them with the re-fitted loft.
    Flight deck: per-vertex loft map (it follows the re-fitted windshield / cockpit section; its floor plate is sloped by the
    map, ~7 deg [inf]).  Cabin (fix round 3 iteration 2, finding F2): pc12's construction at one floor height, the loft
    map's at STA 6.0 (constant over the cabin, STA 4.46-8.23), with FR3_CABIN's stations, and the floor one flat panel as
    wide as the sourced 1.30 m where the section allows.  (fr3 had loft-mapped pc12's cabin vertex by vertex: its floor
    panel, fitted to the NEW section at pc12's old floor WL and warped by the station-wise map, was 1.257 m wide, rose aft to
    WL 1.37 and buried the seat rails and side ledges by up to 65 mm.)"""
    from cad.mesh import Mesh, planar_cap
    from model import interior as I
    from model import livery as LV
    from model import cockpit_glazing as CG
    from model import fuselage as F
    from model.fuselage_parts import signed_s
    orig_fd, orig_cabin = I.build_flightdeck, I.build_cabin

    def flightdeck(parts):
        before = set(parts)
        orig_fd(parts)
        for pid in set(parts) - before:
            for m, _ in parts[pid].meshes:
                m.V = loft_map(m.V)
                m.compute_normals()
        return parts

    def cabin(parts):
        # pc12's build_cabin construction (seats, ledges with wood caps, club tables, baggage net) at the loft-mapped floor
        # height zf (one rigid lift: the map is constant over the cabin) with FR3_CABIN's stations, and one flat floor panel
        from cad.mesh import box, cylinder
        from model import fuselage_parts as FP
        from model.parts import Part
        o = cab
        zf = float(loft_map(np.array([[6.0, 0.0, I.FLOOR_Z]]))[0, 2])
        leather, frame, wood, lin = [], [], [], []
        xs = np.linspace(4.46, 9.52, 24)          # pc12's floor extent and sampling (interior.build_cabin)
        hw = np.minimum(CABIN_FLOOR_W / 2, [min(I.section_limit(x, zf, 0.055), I.section_limit(x, zf - 0.03, 0.055)) for x in xs])
        top = np.vstack([np.stack([xs, hw, np.full(len(xs), zf)], 1), np.stack([xs[::-1], -hw[::-1], np.full(len(xs), zf)], 1)])
        floor = Mesh.merge([planar_cap(top, (0, 0, 1)), planar_cap(top - [0, 0, 0.03], (0, 0, -1))])
        for sgn in (-1, 1):
            x0, x1 = o["ledge"]
            for d in (FP.AIRSTAIR, FP.CARGO):      # keep each side's ledge clear of the doors on that side
                if d["side"] != sgn:
                    continue
                lo, hi = d["cx"] - d["hx"] - o["door_clear"], d["cx"] + d["hx"] + o["door_clear"]
                if lo <= x0 < hi:
                    x0 = hi
                if lo < x1 <= hi:
                    x1 = lo
            xc, L = 0.5 * (x0 + x1), x1 - x0
            lin.append(I.rbox((xc, sgn * 0.615, zf + 0.21), (L, 0.08, 0.42), e=0.3))
            wood.append(box((xc, sgn * 0.60, zf + 0.425), (L, 0.12, 0.02)))
        for x, f in o["rows"]:
            for y in (-o["seat_bl"], o["seat_bl"]):
                a_, b_ = I.seat(x, y, f, floor=zf)
                leather.append(a_)
                frame.append(b_)
        for y in (-o["seat_bl"], o["seat_bl"]):
            wood.append(I.rbox((o["table_x"], y * 1.2, zf + 0.68), (0.46, 0.34, 0.03), e=0.4))
        for sg in (-1, 1):
            frame.append(cylinder((o["net_x"], sg * 0.55, zf), (o["net_x"], sg * 0.55, zf + 1.18), 0.012, n=8))
        frame.append(cylinder((o["net_x"], -0.55, zf + 1.18), (o["net_x"], 0.55, zf + 1.18), 0.012, n=8))
        p = Part("cabin_interior", "Cabin: executive 6-seat interior", "interior", group="Interior",
                 material_note="Leather seats, wood veneer ledges",
                 info={"cabin": "5.16 x 1.52 x 1.47 m", "floor width": "1.30 m", "seats": "6 executive (up to 9)",
                       "floor": f"flat, WL {zf:.3f} (pc12 {I.FLOOR_Z:.3f} carried by the loft map), {2 * float(np.max(hw)):.2f} m wide (sourced 1.30)",
                       "layout": "pc12's, 0.40 m aft, port ledge clear of the airstair and cargo doors (hwd3d fr3) [inf]"})
        p.add(Mesh.merge(leather), "leather").add(Mesh.merge(frame), "metal_dark")
        p.add(floor, "carpet").add(Mesh.merge(wood), "wood").add(Mesh.merge(lin), "lining")
        parts[p.id] = p
        return parts
    I.build_flightdeck, I.build_cabin = flightdeck, cabin
    orig_fields = LV.fields

    def fields(V, UV=None):
        out = orig_fields(loft_map(V, inverse=True), None)
        if UV is not None:
            s = signed_s(V[:, 0], UV[:, 1])
            out["trim_black"] = CG.surround_sdf(V[:, 0], V[:, 1], V[:, 2], s)
        return out
    LV.fields = fields


def apply_antennas():
    """pc12 sets each centre-line blade antenna's root flat at the skin height of its leading-edge station; on the re-fitted
    aft belly, which slopes up there, the VHF 2 root floated up to 28 mm under the skin at its trailing edge (finding F7 of
    fix round 3 iteration 2).  Each centre-line blade is turned about its root leading edge to the mean skin slope along its
    root chord (mounted normal to the skin [inf]) and the root's residual to the skin line (curvature) added, faded out
    toward the tip.  Wing-mounted blades (pc12's pitot masts) are unchanged."""
    from model import details as D
    from model import fuselage as F
    orig = D.blade_antenna

    def blade_antenna(base, height, chord, sweep_deg=35, down=False, thick=0.10):
        m = orig(base, height, chord, sweep_deg, down, thick)
        if abs(float(base[1])) > 1e-9:
            return m
        skin = (lambda x: np.asarray(F.z_bot(x)) + 0.004) if down else (lambda x: np.asarray(F.z_top(x)) - 0.004)
        x0, z0 = float(base[0]), float(base[2])
        k = float((skin(x0 + chord) - skin(x0)) / chord)
        a = np.arctan(k)
        V = m.V.copy()
        dx, dz = V[:, 0] - x0, V[:, 2] - z0
        V[:, 0] = x0 + dx * np.cos(a) - dz * np.sin(a)
        V[:, 2] = z0 + dx * np.sin(a) + dz * np.cos(a)
        xc = np.clip(V[:, 0], x0, x0 + chord)
        V[:, 2] += (skin(xc) - (z0 + k * (xc - x0))) * (1 - np.clip(np.abs(dz) / height, 0, 1))
        m.V = V
        m.compute_normals()
        return m
    D.blade_antenna = blade_antenna


def patch_verify():
    """pc12's floor-width check is 'OML width at WL 1.12 (its floor) - 2 x 45 mm lining'.  The re-fitted section has a flatter,
    wider bottom, so that proxy no longer holds; the check measures the cabin floor panel as built (apply_interior_livery:
    flat, at the loft-mapped floor height, sized to the sourced 1.30 m) and records a 2 % tolerance and its result
    (tools/models/test_models.mjs fails the model beyond it)."""
    from model import build as B
    orig = B.verify

    def verify(parts):
        out = orig(parts)
        cab = parts.get("cabin_interior")
        V = np.vstack([m.V for m, mat in cab.meshes if mat == "carpet"]) if cab is not None else None
        if V is None or not len(V):
            return out
        sel = np.abs(V[:, 0] - 6.0) < 0.15
        got, zf = float(np.ptp(V[sel, 1])), float(V[sel, 2].max())
        for c in out:
            if c["check"].startswith("Cabin floor width"):
                c["check"] = f"Cabin floor width (floor panel as built, WL {zf:.3f})"
                c["model"] = round(got, 3)
                c["delta_mm"] = round(1000 * (got - c["official"]), 1)
                c["tolerance_mm"] = round(0.02 * 1000 * c["official"], 1)
                c["pass"] = bool(abs(c["delta_mm"]) <= c["tolerance_mm"])
        return out
    B.verify = verify


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="fr3", choices=sorted(OVERRIDES))
    ap.add_argument("--dihedral", type=float, default=None, help="reference-plane dihedral, deg (sets fr2 / fr3)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--parts-only", action="store_true", help="build parts, print checks, write nothing")
    a = ap.parse_args()
    out_dir = Path(a.out) if a.out else HWD / "out" / f"pc12_{a.set}"
    ov = OVERRIDES[a.set]
    applied = {}
    # the loft first: fuselage_parts tabulates the perimeter at import time
    if "loft" in ov:
        apply_loft(ov["loft"])
        applied["loft"] = {k: [list(p) for p in v] for k, v in ov["loft"].items()}
    if "layout" in ov:
        apply_layout(ov["layout"])
        applied["layout"] = {k: v for k, v in ov["layout"].items()}
    if "glazing" in ov:
        apply_glazing(ov["glazing"])
        applied["glazing"] = ov["glazing"]
    if "wing" in ov:
        dih = a.dihedral if a.dihedral is not None else ov["wing"]["DIHEDRAL_DEG"]
        if dih is not None:
            applied["wing"] = dict(ov["wing"], **apply_wing(ov["wing"], dih))
        if ov["wing"].get("GEAR_DZ"):
            applied["gear"] = apply_gear(ov["wing"]["GEAR_DZ"])
    if "winglet" in ov:
        apply_winglet(ov["winglet"])
        applied["winglet"] = ov["winglet"]
    if "nose_housing" in ov:
        apply_nose_housing(ov["nose_housing"])
        applied["nose_housing"] = ov["nose_housing"]
    if "belly" in ov:
        belly_stats = apply_belly(ov["belly"])
        applied["belly"] = ov["belly"]
    if any(k in ov for k in ("dorsal", "fin_le", "strakes")):
        apply_empennage(ov.get("dorsal"), ov.get("fin_le"), ov.get("strakes"))
        for k in ("dorsal", "fin_le", "strakes"):
            if k in ov:
                applied[k] = ov[k]
    if "loft" in ov:
        apply_interior_livery(ov["cabin"])
        applied["cabin"] = ov["cabin"]
        apply_antennas()
        patch_verify()
    from model import build as B
    from model import wing as W
    from model.assemble import write_glb
    t0 = time.time()
    parts = B.build_parts()
    if "wing" in ov:
        for side in ("L", "R"):
            if f"wing_{side}" in parts and parts[f"wing_{side}"].info:
                parts[f"wing_{side}"].info["dihedral"] = (f"{np.degrees(W.DIHEDRAL):.1f} deg (fitted to {DWG} front view)"
                                                          + (f", flat inboard of BL {ov['wing']['KINK_BL']} [inf]" if ov["wing"].get("KINK_BL") else ""))
    checks = B.verify(parts)
    for c in checks:
        print(f"  {c['check']:52s} official {c['official']:7.3f}  model {c['model']:7.3f}  delta {c['delta_mm']:+7.1f} mm")
    if "belly" in ov:
        print(f"  belly fairing lowered below its drawn outline by up to {belly_stats['lowered_mm']:.1f} mm to cover the wing")
        applied["belly"] = dict(ov["belly"], lowered_below_outline_mm=round(belly_stats["lowered_mm"], 1))
    if a.parts_only:
        return parts
    out = out_dir
    out.mkdir(parents=True, exist_ok=True)
    size, stats = write_glb(parts, str(out / "pc12.glb"),
                            meta={"model": "Pilatus PC-12 PRO", "units": "m", "datum": "STA 0 = 3.000 m fwd of firewall"})
    ids = list(parts.keys())
    bom = [{"id": k, "name": p.name, "step": p.step, "group": p.group, "qty": p.qty, "note": p.material_note,
            "tris": p.tri_count(), "info": p.info, "materials": sorted(set(m for _, m in p.meshes))}
           for k, p in parts.items()]
    files, tree = source_hashes()
    dirty = git("status", "--porcelain", "--", "pc12/cad", "pc12/model")
    meta = {
        "steps": [{"key": k, "title": t, "text": d, "parts": [p for p in ids if parts[p].step == k]} for k, t, d in B.STEPS],
        "bom": bom, "construction": B.construction(), "checks": checks,
        "stats": {"triangles": stats["triangles"], "vertices": stats["vertices"], "glb_bytes": size, "parts": len(parts)},
        "wing": {"semi_span": W.SEMI, "root_chord": W.C_ROOT, "tip_chord": W.C_TIP, "mac": W.MAC,
                 "lemac": W.LEMAC, "x_qc": W.X_QC, "dihedral_deg": float(np.degrees(W.DIHEDRAL)),
                 "z_qc0": W.Z_QC0},
        "_variant": {
            "set": a.set, "overrides": json.loads(json.dumps(applied, default=lambda v: v.tolist() if hasattr(v, "tolist") else str(v))),
            "builder": "hwd3d/tools/models/pc12/build_pc12_variant.py",
            "builder_sha256": sha256_file(Path(__file__)),
            "pc12_commit": git("rev-parse", "HEAD"), "pc12_sources_dirty": bool(dirty),
            "pc12_sources_tree_sha256": tree, "pc12_sources": files,
            "built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "seconds": round(time.time() - t0, 1),
        },
    }
    (out / "pc12_meta.json").write_text(json.dumps(meta, separators=(",", ":")))
    print(f"parts {len(parts)}  triangles {stats['triangles']:,}  GLB {size/1e6:.2f} MB  ({time.time()-t0:.1f}s) -> {out}")
    return parts


if __name__ == "__main__":
    main()
