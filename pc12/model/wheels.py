"""
Wheels, tyres, main-wheel hub fairings and brakes of the PC-12 PRO landing gear: source-tagged PARAMETER TABLES and
the 2-D profiles drawn from them (Stage 2: sheet L4W, drawing/wheel_sheet.py), and the Stage-3 3-D builders
main_wheel() / nose_wheel() that revolve / extrude the same profiles (used by model/gear.py).

Tyre envelopes (MAIN_TYRE_ENV / NOSE_TYRE_ENV): free radius R, section width W, bead-seat radius rim and the static
loaded radius.  The MAIN tyre has two envelopes, selected by MAIN_TYRE_CHOICE (the environment variable PC12_MAIN_TYRE
overrides it for a trial build):
  '8.50-10'     the Type III 8.50-10 that the tyre makers, the parts lists and four photo measurements give for the
                PC-12 (TRA OD 627-652): the MODELLED tyre, OWNER DECISION 2026-09-26.  The axles and the static stance
                are kept: the axle WL is the loaded radius, so the tyre is flattened at the ground (41 mm static
                deflection, contact patch, sidewall bulge);
  '22x8.50-10'  Jane's and the Pilatus drawing circle (OD 559; not a listed tyre size): SUPERSEDED.
gear.MAIN_TYRE, the LD-1 leg-door scallop (gear.LEG_DOOR), the round wheel well (bays.WELL_R) and the flap-cove recess
over the well (wing.cove_well_recess) follow the choice.  The other envelope is MAIN_TYRE_ALT (drawn as a deviation
outline on sheet L4W).  The nose tyre is the 17.5x6.25-6, loaded 15.5 mm (the nose axle WL is its loaded radius).
The section tables refine the shape INSIDE the envelopes: tyre cross-section (bead, sidewall, shoulder, crown,
grooves), the split-hub wheel halves, the main-wheel outboard hub fairing, the six-piston main brake, axle and paint.
Source tags: [S] sourced (NGX POH 02406 7-4, Ground Servicing Guide 02527, Goodyear aviation data book 2018 = TRA
tyre / rim data, parts listings), [M] measured on photographs (PRO s/n 3001, 3005, 3008, 3010, 3036, 3066 and the NGX
broadside; the photos and the measurements' working stay in the git-ignored refs/cache), [E] estimated /
reconstructed (hidden or not resolved in photos), [D] derived from other entries, [G] the gear.py value,
[O] owner decision, [P] proposed (pending the owner's decision).

Local wheel coordinates (m): s along the axle from the tyre mid-plane, positive towards the face seen in the side
view from PORT (main gear: the port unit's OUTBOARD face = the hub-fairing side, the brake on s < 0; nose gear: the
port face); r radial from the axle.  Clock angles th (deg) in the wheel plane as seen from port: 0 = aft (+x),
90 = up (+z).  The starboard units are mirror images.  The wheels turn, so the clocking of screws / valves / lobes
(the brake housing does not turn) is only the drawn pose.  Model coordinates of the port units: x = axle x + dx,
y = axle y - s, z = axle z + dz.
"""
from __future__ import annotations

import math
import os

import numpy as np

from cad.mesh import Mesh, revolve, cylinder, cap_ring

IN = 0.0254


class PTable(dict):
    """Parameter table: name -> value (plain dict access), plus a source tag and a short note per entry."""

    def __init__(self, title, **entries):
        super().__init__({k: v[0] for k, v in entries.items()})
        self.title = title
        self._src = {k: (v[1], v[2] if len(v) > 2 else "") for k, v in entries.items()}

    def tag(self, k):
        return self._src[k][0]

    def note(self, k):
        return self._src[k][1]

    def src(self, k):
        t, n = self._src[k]
        return f"[{t}] {n}".strip()


# ================================================================================================ tyre envelopes
MAIN_TYRE_850 = PTable(
    "Main tyre envelope: 8.50-10 Type III (tyre makers / parts lists / photos; owner decision 2026-09-26)",
    size=("8.50-10 Type III", "O", "tyre makers / parts lists / photos, owner decision 2026-09-26 (Jane's 22x8.50-10 "
                                   "superseded: not a listed size)"),
    part=("Goodyear 850T06-3 / Michelin 025-350-0", "S", "10 PR tubeless (parts listings, Goodyear data book)"),
    R=(0.320, "M", "free radius (OD 640): inside the TRA OD 627-652; four photo methods give OD 620-650"),
    W=(0.216, "S", "section width: TRA 8.2-8.7 in (208-221); photos 214-224"),
    rim=(5.0 * IN, "S", "bead-seat radius (10 in rim)"),
    R_loaded=(0.279, "M", "static loaded radius = the axle WL (gear.MAIN_AXLE, kept); photos 270-280"),
    patch_l=(0.250, "E", "static contact-patch length (the free circle's chord at the ground would be 0.31)"),
    bulge=(0.006, "E", "loaded sidewall bulge per side, at the ground"),
    bulge_l=(0.300, "E", "circumferential extent of the bulge about the contact (plan view)"),
    od_max=(25.65 * IN, "S", "TRA inflated OD max 25.65 in"),
    od_min=(24.70 * IN, "S", "TRA inflated OD min 24.70 in"),
    W_max=(8.7 * IN, "S", "TRA section width max 8.7 in"),
    W_min=(8.2 * IN, "S", "TRA section width min 8.2 in"),
    shoulder_d=(22.79 * IN, "S", "TRA shoulder diameter max 22.79 in (growth / clearance envelope)"),
    shoulder_w=(7.4 * IN, "S", "TRA shoulder width max 7.4 in"),
    slr=(10.19 * IN, "S", "static loaded radius at the rated 5500 lb / 70 psi (850T06-3)"),
    flat_r=(6.90 * IN, "S", "flat-tyre radius (850T06-3)"),
)

MAIN_TYRE_22 = PTable(
    "Main tyre envelope: 22x8.50-10 (Jane's; Pilatus drawing circle; superseded 2026-09-26)",
    size=("22x8.50-10", "S", "Jane's; Pilatus drawing 190.10.40.432 circle 558.8 (refs/mbp.py); superseded by the "
                             "owner decision 2026-09-26"),
    part=("- (not a TRA size)", "S", "no 22 in tyre on a 10 in rim with an 8.5 in section in the Goodyear data book"),
    R=(0.2795, "S", "free radius: 22 in OD (558.8; gear.py rounds to 0.2795)"),
    W=(0.216, "S", "section width 8.50 in"),
    rim=(5.0 * IN, "S", "bead-seat radius (10 in rim)"),
    R_loaded=(0.279, "G", "axle WL (gear.MAIN_AXLE): 0.5 mm static deflection"),
    patch_l=(0.0, "D", "no blend: the free circle cut by the ground"),
    bulge=(0.0, "E", "no bulge at 0.5 mm deflection"),
    bulge_l=(0.0, "E", "-"),
    od_max=(22.0 * IN, "S", "nominal 22 in (no TRA entry)"),
    od_min=(22.0 * IN, "S", "nominal 22 in (no TRA entry)"),
    W_max=(8.5 * IN, "S", "nominal 8.50 in"),
    W_min=(8.5 * IN, "S", "nominal 8.50 in"),
    shoulder_d=(None, "S", "no TRA growth envelope for this size"),
    shoulder_w=(None, "S", "-"),
    slr=(None, "S", "-"),
    flat_r=(None, "S", "-"),
)

MAIN_TYRE_OPTIONS = {"22x8.50-10": MAIN_TYRE_22, "8.50-10": MAIN_TYRE_850}
# the modelled main tyre: the 8.50-10 Type III (OWNER DECISION 2026-09-26: tyre makers, parts lists, four photo methods
# and the main/nose OD ratio agree; Jane's / the Pilatus drawing 22x8.50-10 is kept as the superseded alternative)
MAIN_TYRE_CHOICE = os.environ.get("PC12_MAIN_TYRE", "8.50-10")
if MAIN_TYRE_CHOICE not in MAIN_TYRE_OPTIONS:
    raise ValueError(f"PC12_MAIN_TYRE must be one of {sorted(MAIN_TYRE_OPTIONS)}")
MAIN_TYRE_ENV = MAIN_TYRE_OPTIONS[MAIN_TYRE_CHOICE]
MAIN_TYRE_ALT = MAIN_TYRE_OPTIONS["8.50-10" if MAIN_TYRE_CHOICE == "22x8.50-10" else "22x8.50-10"]
MAIN_TRA = MAIN_TYRE_850                 # the TRA data (growth envelope, loaded radii) of the listed PC-12 main tyre
MAIN_IS_TRA = MAIN_TYRE_ENV is MAIN_TYRE_850
ALT_STATUS = "SUPERSEDED" if MAIN_IS_TRA else "PROPOSED - OWNER DECISION PENDING"
# the scallop the LD-1 leg door leaves round the (static, free) main tyre: tyre R + this (gear.LEG_DOOR, bays.WELL_R)
SCALLOP_CLEAR = 0.0125

NOSE_TYRE_ENV = PTable(
    "Nose tyre envelope: 17.5x6.25-6",
    size=("17.5x6.25-6", "S", "Jane's; parts lists; photos confirm 17.5 in (camera check)"),
    part=("Goodyear 175K88B1 / Michelin 021-327-0", "S", "8 PR tubeless (parts listings)"),
    R=(0.2225, "S", "free radius: 17.5 in OD (444.5); = gear.NOSE_TYRE"),
    W=(0.159, "S", "section width 6.25 in (TRA max; min 5.9 in); = gear.NOSE_TYRE"),
    rim=(0.076, "S", "bead-seat radius (6 in rim); = gear.NOSE_TYRE"),
    R_loaded=(0.207, "M", "static loaded radius = the nose axle WL (gear.NOSE_AXLE): photos 200-210 (3036 R_bottom / "
                          "R_top 0.92); 15.5 mm deflection (the drawn circle's axle was 0.222)"),
    patch_l=(0.130, "E", "static contact-patch length (the free circle's chord at the ground would be 0.163)"),
    bulge=(0.004, "E", "loaded sidewall bulge per side, at the ground"),
    bulge_l=(0.200, "E", "circumferential extent of the bulge about the contact (plan view)"),
    od_max=(17.5 * IN, "S", "TRA OD max 17.5 in"),
    od_min=(16.85 * IN, "S", "TRA OD min 16.85 in"),
    W_max=(6.25 * IN, "S", "TRA section width max 6.25 in"),
    W_min=(5.9 * IN, "S", "TRA section width min 5.9 in"),
    shoulder_d=(15.45 * IN, "S", "TRA shoulder diameter max 15.45 in"),
    shoulder_w=(5.5 * IN, "S", "TRA shoulder width max 5.5 in"),
    slr=(6.9 * IN, "S", "static loaded radius at the rated 2900 lb / 70 psi (175K88B1)"),
    flat_r=(4.80 * IN, "S", "flat-tyre radius"),
)

SUPERSEDED_MAIN = MAIN_TYRE_ALT          # (name kept for sheet L4W: the envelope NOT modelled)

TYRE_ENV = dict(main=MAIN_TYRE_ENV, nose=NOSE_TYRE_ENV)


def envelope(which):
    """(R, W, rim, R_loaded) of the modelled tyre envelope ('main' | 'nose')."""
    e = TYRE_ENV[which]
    return dict(R=float(e["R"]), W=float(e["W"]), rim=float(e["rim"]), R_loaded=float(e["R_loaded"]))


def gear_envelope(which):
    """The tyre model/gear.py builds in 3-D (gear.MAIN_TYRE / NOSE_TYRE, taken from these envelopes; imported lazily
    because gear.py imports this module)."""
    from model import gear as G
    t = G.MAIN_TYRE if which == "main" else G.NOSE_TYRE
    return dict(R=float(t["R"]), W=float(t["W"]), rim=float(t["rim"]))


# ================================================================================================ main wheel
MAIN_TYRE_SEC = PTable(
    "Main tyre section (inside MAIN_TYRE_ENV)",
    size=(MAIN_TYRE_ENV["size"], MAIN_TYRE_ENV.tag("size"), "the modelled envelope (MAIN_TYRE_CHOICE)"),
    ply=("10 PR TL", "S", "Goodyear data book PC-12 main: 8.50-10, 10 ply, tubeless"),
    pressure=(60.0, "S", "psi (4.1 bar), NGX / PRO MTOW 4,500 kg: POH placard, GSG 02527 p. 2-1-2"),
    wmax_h=(0.50, "E", "height of the max section width above the bead seat, fraction of the section height"),
    tread_hw=(0.082, "M", "crown arc half-width (to the shoulder round): outer ribs ~35 mm incl. the round"),
    shoulder_R=(0.022, "E", "shoulder radius (rounded, no chine); the upper sidewall radius follows"),
    crown_R=(0.200, "E", "transverse crown radius: flat centre rib, 8 mm drop at the outer grooves (photos: flatter than the TRA growth envelope)"),
    grooves=((0.030, 0.056), "M", "groove centres +-s: TWO PAIRS (+-0.14 W, +-0.26 W), 3036 / 3008 head-on"),
    groove_w=(0.008, "M", "groove width at the rib surface (7-9 mm)"),
    groove_d=(0.007, "E", "groove depth (new tread)"),
    groove_floor=(0.005, "E", "groove floor width (round-bottomed)"),
    bead_leave=(100.0, "E", "angle on the flange tip round where the sidewall leaves the rim flange (deg)"),
    t_crown=(0.017, "E", "rubber + carcass under the tread (section drawing)"),
    t_side=(0.008, "E", "sidewall wall thickness (section drawing)"),
    t_bead=(0.018, "E", "wall thickness at the rim-flange line (bead / apex)"),
    bead_wire=(0.011, "E", "bead bundle size (section drawing)"),
)

MAIN_RIM = PTable(
    "Main wheel: split hub, two halves (Goodrich 3-1543 family)",
    bead_r=(5.0 * IN, "S", "rim (bead-seat) diameter 10 in; = MAIN_TYRE_ENV rim"),
    flange_s=(6.25 * IN / 2, "S", "width between flanges 6.25 in (TRA 8.50-10 rim)"),
    flange_h=(0.81 * IN, "S", "flange height 0.81 in -> flange diameter 0.295 m"),
    ledge=(1.35 * IN, "S", "min ledge (bead-seat) width 1.35 in"),
    flange_t=(0.009, "E", "axial flange thickness; tip rounded with flange_t / 2"),
    barrel_t=(0.009, "E", "rim barrel wall"),
    seat_step=(0.002, "E", "barrel between the bead ledges, below the seat (O-ring land at the split)"),
    web_t=(0.011, "E", "each half's web beside the split plane (both halves cup-shaped, bolted web to web)"),
    hub_r=(0.046, "E", "hub barrel outer radius (inside the brake torque tube)"),
    hub_bore=(0.038, "E", "bearing-cup bore radius (tapered roller bearing each half)"),
    hub_s=((-0.074, 0.074), "E", "hub barrel ends, inboard / outboard"),
    bearing_w=(0.020, "E", "bearing width"),
    tie_n=(8, "E", "tie bolts: hidden (fairing outboard, brake inboard) - count not resolved"),
    tie_r=(0.100, "E", "tie-bolt circle radius"),
    tie_d=(0.0095, "E", "tie-bolt shank (3/8 in); hex heads / nuts AF 0.016"),
    valve_r=(0.077, "M", "inflation valve under the fairing's access hole (brass valve seen through it, 3036)"),
    valve_th=(162.0, "M", "valve clock (drawn pose; = fairing hole)"),
    valve_s=(0.100, "E", "valve cap s (extended stem from the outboard web, just under the fairing face)"),
    plug_th=(342.0, "E", "overinflation safety plug [S: POH] clock, outboard web"),
    fusible_n=(3, "S", "fusible plugs, main wheels only (POH 7-4-11)"),
    fusible_r=(0.108, "E", "fusible plugs: radius on the inboard (brake-side) half, 120 deg apart"),
)

MAIN_FAIRING = PTable(
    "Main wheel outboard hub fairing ('fairings on the outer hubs', POH 7-4-11)",
    r_lip=(0.148, "M", "outer lip radius = rim flange tip (lip dia 0.29-0.30, tyre OD / 2.15-2.21)"),
    lip_w=(0.014, "M", "flat lip ring carrying the screws (10-14 mm)"),
    r_face=(0.122, "M", "flat raised face radius (0.80-0.83 x lip dia)"),
    proud=(0.028, "M", "face stands proud of the lip plane (25-30 mm)"),
    face_R=(0.006, "E", "round at the face edge"),
    t=(0.0016, "E", "spun aluminium sheet"),
    screws=(5, "M", "countersunk screws at 72 deg (5 fits three photos, 6 at 60 deg does not)"),
    screw_r=(0.140, "M", "screw circle radius (0.93-0.95 x lip dia)"),
    screw_d=(0.008, "M", "screw head diameter"),
    screw_th=(54.0, "M", "first screw clock (drawn pose)"),
    hole_d=(0.055, "M", "valve-access hole diameter (50-60 mm)"),
    hole_r=(0.077, "M", "hole centre off the axle (75-80 mm)"),
    hole_th=(162.0, "M", "hole clock (drawn pose, between two screws)"),
    s0=(None, "D", "lip plane = outboard rim-flange face (flange_s + flange_t)"),
    paint=("leg-door colour", "M", "livery.SURFACES['main_gear_door']: MSN 3008 paint_blue (3010 red, 3036 silver)"),
)

MAIN_BRAKE = PTable(
    "Main brake: six-piston, multi-disc, inside the inboard wheel half",
    pistons=(6, "S", "six piston brake assemblies (POH 7-4-10; Cleveland 30-244 'six piston')"),
    retractors=(3, "S", "three retractors (POH 7-4-10)"),
    friction=("steel", "S", "steel friction surfaces (POH 7-4-10)"),
    stators=(2, "S", "overhaul kit 2-1674-1-OSK: 2 stators, 24 wear pads, 48 rivets"),
    rotors=(3, "E", "inferred: 24 pads = 6 lined faces x 4 (pressure plate, 2 stators x 2, back plate)"),
    lobes=(6, "M", "6-lobed housing (piston bosses) in the rim bore, 3036 / 3008 / 3066 / 3010 inboard views"),
    lobe_th=(90.0, "E", "first lobe clock (top lobe carries the inlet fitting)"),
    lobe_c=(0.084, "E", "lobe (piston) centre radius"),
    lobe_R=(0.022, "M", "lobe radius: tips at ~0.72 x the flange radius"),
    body_R=(0.066, "E", "housing body radius between the lobes"),
    lobe_fillet=(0.005, "E", "blend between lobes and body"),
    housing_s=((-0.100, -0.078), "E", "housing outer / inner face (outer face 12 mm beyond the flange face, 8 mm inside the tyre)"),
    piston_d=(0.030, "E", "piston diameter"),
    pressure_plate_t=(0.005, "E", "pressure plate"),
    rotor_t=(0.006, "E", "rotor (keyed to the wheel barrel)"),
    stator_t=(0.004, "E", "stator (keyed to the torque tube)"),
    lining_t=(0.0035, "E", "riveted lining on each lined face"),
    back_plate_t=(0.006, "E", "back plate (end of the torque tube)"),
    rotor_r=((0.070, 0.116), "E", "rotor inner / outer radius (drive keys in the barrel, r 0.118)"),
    stator_r=((0.056, 0.104), "E", "stator / plate inner / outer radius"),
    torque_tube_r=((0.050, 0.056), "E", "torque tube (fixed), round the rotating hub barrel"),
    torque_plate=((-0.106, -0.100, 0.026, 0.062), "E", "torque plate on the axle flange: s0, s1, r0, r1"),
    fitting_d=(0.012, "E", "inlet fitting on the top lobe; bleeder on the lobe opposite"),
    line_d=(0.0064, "E", "brake line 1/4 in, up the trailing arm"),
    material=("housing brake_housing / discs metal_dark", "M", "bright cast-aluminium housing (3036 mx5: p90 ~195 in "
                                                              "the sun), dark steel discs"),
)

MAIN_AXLE = PTable(
    "Main axle and trailing-arm boss (context)",
    r=(0.026, "G", "axle radius (gear.build_main); cantilevered outboard from the arm boss"),
    bore_r=(0.0225, "M", "open axle bore, facing inboard (~45 mm)"),
    boss_r=(0.058, "M", "trailing-arm axle boss radius (dia 0.11-0.12)"),
    boss_s=((-0.158, -0.110), "E", "boss faces: inboard face flush with the arm's (s = -0.14 -/+ 0.0175, "
                                   "gear.build_main; stowed, 12 mm under the wing upper skin)"),
    thread_r=(0.020, "E", "threaded axle end outboard of the outboard bearing"),
    nut_af=(0.046, "E", "axle nut across flats (under the fairing)"),
    nut_s=((0.076, 0.090), "E", "axle nut s range"),
    cap_r=(0.040, "E", "hub (grease) cap radius, on the outboard hub end"),
    cap_s=(0.100, "E", "hub cap outer face s (inside the fairing face)"),
)

MAIN_PAINT = PTable(
    "Main wheel materials (model/assemble.py MATERIALS names)",
    tyre=("tire", "M", "black satin rubber; NO lettering (owner decision: no markings)"),
    fairing=("livery:main_gear_door", "M", "gloss paint in the leg-door colour (MSN 3008 paint_blue)"),
    wheel=("wheel", "M", "inboard half / flanges gloss light grey-white"),
    brake=("brake_housing", "M", "housing bright cast aluminium (satin), piston caps"),
    discs=("metal_dark", "M", "heat-darkened steel disc edges"),
    fasteners=("metal", "M", "tie bolts, screws: cadmium; valve brass"),
    axle=("steel", "E", "axle nut, hub cap"),
    arm=("gear_leg", "M", "trailing arm, axle boss"),
)

# ================================================================================================ nose wheel
NOSE_TYRE_SEC = PTable(
    "Nose tyre section (inside NOSE_TYRE_ENV)",
    size=("17.5x6.25-6", "S", "Jane's; parts lists (Goodyear 175K88B1, Michelin 021-327-0); photos confirm 17.5 in"),
    ply=("8 PR TL", "S", "Goodyear data book / Michelin 021-327-0"),
    pressure=(60.0, "S", "psi (4.1 bar), POH placard / GSG 02527"),
    wmax_h=(0.50, "E", "height of the max section width, fraction of the section height"),
    tread_hw=(0.058, "M", "crown arc half-width (5 ribs, outer ribs ~14 mm to the shoulder round)"),
    shoulder_R=(0.016, "E", "shoulder radius; the upper sidewall radius follows"),
    crown_R=(0.120, "M", "crown radius: ~8 mm drop at the outer grooves (3001 head-on)"),
    grooves=((0.015, 0.044), "M", "groove centres +-s: EVENLY spaced (+-0.09 W, +-0.28 W), 3001 / 3036 head-on"),
    groove_w=(0.006, "M", "groove width (~6 mm)"),
    groove_d=(0.005, "E", "groove depth"),
    groove_floor=(0.004, "E", "groove floor width"),
    bead_leave=(100.0, "E", "sidewall leaves the flange round at this angle (deg)"),
    t_crown=(0.013, "E", "tread + carcass (section drawing)"),
    t_side=(0.007, "E", "sidewall wall"),
    t_bead=(0.014, "E", "wall at the rim-flange line"),
    bead_wire=(0.008, "E", "bead bundle size"),
)

NOSE_RIM = PTable(
    "Nose wheel: split hub, two halves (Goodrich 3-1501 family)",
    bead_r=(0.076, "S", "rim diameter 6 in (152.4); = NOSE_TYRE_ENV rim"),
    flange_s=(5.00 * IN / 2, "S", "width between flanges 5.00 in (data book, 6.00-6 rim, as printed)"),
    flange_h=(0.75 * IN, "S", "flange height 0.75 in -> flange diameter 0.19 m"),
    ledge=(0.90 * IN, "S", "min ledge width 0.90 in"),
    flange_t=(0.007, "E", "axial flange thickness"),
    barrel_t=(0.007, "E", "rim barrel wall"),
    seat_step=(0.0015, "E", "barrel below the seat between the ledges"),
    web_t=(0.009, "E", "web of each half"),
    web_s=(0.032, "M", "outer face of each half's web: a dish 38 mm inside the flange face, so the tie-bolt heads and "
                       "the hub ring show (3036 nose-hub zoom: bolt circle ~45 mm behind the flange, parallax)"),
    hub_r=(0.031, "M", "raised hub boss (dia ~0.3 x flange dia)"),
    hub_bore=(0.026, "E", "bearing-cup bore radius"),
    hub_s=((-0.081, 0.081), "M", "hub ends at the fork arms' inner faces (+-0.083)"),
    bearing_w=(0.016, "E", "bearing width"),
    tie_n=(4, "E", "tie bolts: 3 visible per face beside the fork arm, the 4th assumed behind it"),
    tie_r=(0.055, "M", "tie-bolt circle radius: ~0.58 x the flange RADIUS (3036 nose-hub zoom, parallax-corrected fit)"),
    tie_d=(0.008, "E", "tie-bolt shank; heads / nuts AF 0.013, cadmium-gold"),
    tie_th=(0.0, "M", "first tie bolt clock (+-20 deg)"),
    valve_r=(0.066, "M", "brass valve stem at ~0.7 x the flange radius, port face (3036)"),
    valve_th=(30.0, "M", "valve clock (drawn pose)"),
    valve_s=(0.058, "E", "valve cap s (inside the flange face)"),
    plug_th=(210.0, "E", "overinflation safety plug [S: POH] clock, starboard face"),
    paint=("wheel", "M", "gloss white, open on both faces (no fairing)"),
)

NOSE_AXLE = PTable(
    "Nose axle, fork arms (context)",
    r=(0.020, "G", "axle radius (gear.build_nose)"),
    fork_in=(0.083, "M", "fork arms' inner faces +-s: TWO arms (3001 / 3036 head-on, 3008 0517, 188)"),
    fork_out=(0.118, "M", "fork arms' outer faces +-s (arm ~35 mm thick)"),
    thread_r=(0.014, "E", "threaded axle ends outboard of the fork arms"),
    boss_r=(0.031, "G", "fork-arm axle boss radius (gear.NOSE_FORK_SEC)"),
    arch=(0.025, "M", "yoke arch inner edge above the tyre crown (arch ~45-50 mm deep)"),
    nut_af=(0.032, "E", "hex axle nut across flats (steel), with a tear-drop lock plate"),
    nut_s=((0.118, 0.130), "E", "lock plate + nut s range, outboard of each fork arm (the open nose doors' inner faces "
                                 "pass at +-0.136)"),
    lock_plate=(0.050, "M", "tear-drop lock plate length along the arm (3036)"),
    lock_t=(0.003, "E", "lock plate thickness (on the arm's outer face, under the nut)"),
    cap_r=((0.021, 0.028), "M", "chrome bearing cap / seal ring at each hub end, inner / outer radius (3036 nose hub)"),
)

NOSE_PAINT = PTable(
    "Nose wheel materials",
    tyre=("tire", "M", "black satin rubber, no lettering"),
    wheel=("wheel", "M", "gloss white halves, open both faces (photos read a touch whiter than 'wheel')"),
    fasteners=("metal", "M", "tie bolts cadmium-gold, valve brass"),
    axle=("steel_dark", "M", "dark steel hex axle nut + tear-drop lock plate, threaded axle end with its bore"),
    fork=("gear_leg", "M", "two-arm fork yoke, crown block (cadmium bolts), chrome bearing caps at the hub ends"),
)

MAIN = dict(tyre=MAIN_TYRE_SEC, rim=MAIN_RIM, fairing=MAIN_FAIRING, brake=MAIN_BRAKE, axle=MAIN_AXLE,
            paint=MAIN_PAINT, which="main")
NOSE = dict(tyre=NOSE_TYRE_SEC, rim=NOSE_RIM, axle=NOSE_AXLE, paint=NOSE_PAINT, which="nose")

# ------------------------------------------------------------------------------------------------ photo checks
# [M] photo measurements the tables are checked against on L4W (the photos and their working stay in refs/cache):
# (item, photographs, short source)
PHOTO = dict(
    main_od=((0.62, 0.65), "4 methods: 3008 photo 130 (fitted camera), 3036 head-on, NGX broadside, fairing ratio"),
    main_w=((0.214, 0.224), "3036 head-on (350 px/m from the track)"),
    main_loaded_r=((0.27, 0.28), "3036: R_bottom / R_top 0.87"),
    main_fairing_ratio=((2.15, 2.21), "tyre radius / fairing lip radius, 3036 and NGX"),
    main_grooves=((0.14, 0.26), "groove centres / W (two pairs), 3036 8192 px, 3008 188"),
    nose_od=((0.435, 0.445), "photo 130 camera: 112 px vs 109 px predicted for 17.5 in"),
    nose_loaded_r=((0.200, 0.210), "3036: R_bottom / R_top 0.92"),
    nose_grooves=((0.09, 0.28), "groove centres / W (even), 3001 / 3036 head-on"),
    nose_fork_arms=(2, "3001 / 3036 head-on, 3008 0517 starboard arm"),
    fairing_d=((0.29, 0.30), "3036 mx4 / mx5, NGX, 3005, 3010"),
    fairing_proud=((0.025, 0.030), "face-centre displacement at 49 deg obliquity (3036 mx5)"),
    render_grooves=((0.062, 0.186), "render/lookdev.py groove shader: +-0.1 / +-0.3 of the tread width"),
)


# ================================================================================================ 2-D geometry
def _arc(c, r, a0, a1, n):
    t = np.radians(np.linspace(a0, a1, max(int(n), 2)))
    return np.c_[c[0] + r * np.cos(t), c[1] + r * np.sin(t)]


def _ang(v):
    return math.degrees(math.atan2(v[1], v[0]))


def flange_round(rim):
    """(centre, radius) of the rim flange's tip round in (s, r), s > 0 half."""
    rho = rim["flange_t"] / 2
    return np.array([rim["flange_s"] + rho, rim["bead_r"] + rim["flange_h"] - rho]), rho


def tyre_frame(asm, R=None):
    """Key construction of the tyre half-section (s >= 0) inside the envelope (R overrides the envelope radius, e.g.
    SUPERSEDED_MAIN['R'] for the phantom): circle centres, radii and tangent points.  Composite of tangent arcs: crown (crown_R, centre
    on the mid-plane) out to tread_hw (T1), shoulder round (shoulder_R), upper sidewall (radius solved so that it is
    tangent to the shoulder round and reaches the max width W/2 at wmax_h of the section height), lower sidewall
    circle from the max width to the point B where the sidewall leaves the rim flange's tip round (bead_leave)."""
    env = envelope(asm["which"])
    t, rim = asm["tyre"], asm["rim"]
    R = env["R"] if R is None else float(R)
    hw = env["W"] / 2
    H = R - rim["bead_r"]
    rw = rim["bead_r"] + t["wmax_h"] * H
    Rc, Rs = t["crown_R"], t["shoulder_R"]
    Cc = np.array([0.0, R - Rc])
    st = t["tread_hw"]
    T1 = np.array([st, float(Cc[1] + math.sqrt(Rc * Rc - st * st))])
    Q = Cc + (T1 - Cc) * (Rc - Rs) / Rc
    dx, dz = Q[0] - hw, Q[1] - rw
    if Q[0] + Rs >= hw or dx * dx + dz * dz <= Rs * Rs:
        raise ValueError("tyre section: the shoulder round does not fit inside the section width")
    Ru = (Rs * Rs - dx * dx - dz * dz) / (2.0 * (dx + Rs))
    Cu = np.array([hw - Ru, rw])
    T2 = Cu + (Q - Cu) / np.linalg.norm(Q - Cu) * Ru
    Cf, rho = flange_round(rim)
    a = math.radians(t["bead_leave"])
    B = Cf + rho * np.array([math.cos(a), math.sin(a)])
    Rl = ((B[0] - hw) ** 2 + (B[1] - rw) ** 2) / (2 * (hw - B[0]))
    Cl = np.array([hw - Rl, rw])
    return dict(R=R, hw=hw, H=H, rw=rw, Cc=Cc, Rc=Rc, Q=Q, Rs=Rs, Cu=Cu, Ru=Ru, Cl=Cl, Rl=Rl, T1=T1, T2=T2, B=B,
                Cf=Cf, rho=rho, W=env["W"])


def crown_r(fr, s):
    """Radius of the (ungrooved) crown arc at axial position s."""
    s = np.asarray(s, float)
    return fr["Cc"][1] + np.sqrt(np.maximum(fr["Rc"] ** 2 - s * s, 0.0))


def tyre_outer_half(asm, R=None, grooves=True, n=12):
    """Outer surface of the tyre, half-section s >= 0, from the crown top (s = 0) to B (where it leaves the rim
    flange): (N, 2) (s, r).  Grooves cut into the crown arc as round-bottomed channels."""
    fr = tyre_frame(asm, R)
    t = asm["tyre"]
    pts = []
    # crown with grooves (s from 0 to T1)
    s_end = fr["T1"][0]
    cuts = []
    if grooves:
        w, d, fw = t["groove_w"], t["groove_d"], t["groove_floor"]
        for g in t["grooves"]:
            cuts.append((g - w / 2, g + w / 2, g, w, d, fw))
    s_marks = [0.0] + [c for cut in cuts for c in cut[:2]] + [s_end]
    s_marks = sorted(set(s_marks))
    for s0, s1 in zip(s_marks[:-1], s_marks[1:]):
        cut = next((c for c in cuts if abs(c[0] - s0) < 1e-12 and abs(c[1] - s1) < 1e-12), None)
        if cut is None:
            ss = np.linspace(s0, s1, max(3, int(n * (s1 - s0) / 0.01) + 2))
            pts.append(np.c_[ss, crown_r(fr, ss)])
        else:
            a, b, g, w, d, fw = cut
            rg = float(crown_r(fr, g))
            fl = rg - d + fw / 2                                   # floor round centre r
            pts.append(np.array([[a, float(crown_r(fr, a))], [g - fw / 2, fl]]))
            pts.append(_arc((g, fl), fw / 2, 180.0, 360.0, 9)[1:-1])
            pts.append(np.array([[g + fw / 2, fl], [b, float(crown_r(fr, b))]]))
    # shoulder, upper sidewall to the max width, lower sidewall to B
    Q, Cu, Cl = fr["Q"], fr["Cu"], fr["Cl"]
    pts.append(_arc(Q, fr["Rs"], _ang(fr["T1"] - Q), _ang(fr["T2"] - Q), n)[1:])
    pts.append(_arc(Cu, fr["Ru"], _ang(fr["T2"] - Cu), 0.0, n)[1:])
    pts.append(_arc(Cl, fr["Rl"], 0.0, _ang(fr["B"] - Cl), n)[1:])
    P = np.vstack(pts)
    keep = np.r_[True, np.linalg.norm(np.diff(P, axis=0), axis=1) > 1e-7]
    return P[keep]


def tyre_bead_half(asm):
    """Hidden part of the tyre's outer contour inside the rim, s >= 0: from B round the flange tip, down the flange's
    inner face to the bead heel and along the ledge to the bead toe."""
    fr = tyre_frame(asm)
    rim = asm["rim"]
    Cf, rho = fr["Cf"], fr["rho"]
    a = asm["tyre"]["bead_leave"]
    fs, br = rim["flange_s"], rim["bead_r"]
    P = [_arc(Cf, rho, a, 180.0, 8)[1:],
         np.array([[fs, br + 0.003]]), _arc((fs - 0.003, br + 0.003), 0.003, 0.0, -90.0, 5)[1:],
         np.array([[fs - rim["ledge"], br]])]
    return np.vstack(P)


def tyre_section(asm, R=None):
    """Closed tyre cross-section (upper half-plane, both sides), (N, 2) (s, r): outer surface with grooves bead toe
    to bead toe, then the inner liner back (wall thickness t_crown on the tread, t_side on the sidewalls, t_bead at
    the flange line).  For the section views; the 3-D surface is tyre_outer_half() revolved."""
    fr = tyre_frame(asm, R)
    t, rim = asm["tyre"], asm["rim"]
    outer = tyre_outer_half(asm, R)
    bead = tyre_bead_half(asm)
    half = np.vstack([outer, bead])
    full_outer = np.vstack([half[::-1] * [-1, 1], half[1:]])          # toe (-s) -> crown -> toe (+s)
    # inner liner: offset of the UNGROOVED outer curve by a thickness blended along it
    sm = tyre_outer_half(asm, R, grooves=False, n=24)
    seg = np.linalg.norm(np.diff(sm, axis=0), axis=1)
    u = np.r_[0.0, np.cumsum(seg)]
    tang = np.gradient(sm, u, axis=0)
    tang /= np.linalg.norm(tang, axis=1)[:, None]
    nin = np.c_[tang[:, 1], -tang[:, 0]]                              # inward normal (curve runs crown -> bead)
    k1 = int(np.argmin(np.abs(sm[:, 0] - fr["T1"][0]) + np.abs(sm[:, 1] - fr["T1"][1])))
    k2 = int(np.argmin(np.abs(sm[:, 0] - fr["hw"]) + np.abs(sm[:, 1] - fr["rw"])))
    th = np.interp(u, [0.0, u[k1], u[k1] + 0.6 * (u[k2] - u[k1]), u[k2], u[-1]],
                   [t["t_crown"], t["t_crown"], t["t_side"], t["t_side"], t["t_bead"]])
    inner = sm + nin * th[:, None]
    toe = np.array([rim["flange_s"] - rim["ledge"], rim["bead_r"]])
    k = inner[-1]
    tail = np.array([k + 0.5 * (toe - k) + [-0.004, 0.004], toe + [0.0, 0.0005]])
    ih = np.vstack([inner, tail])                                     # crown -> toe (+s)
    full_inner = np.vstack([ih[::-1], (ih * [-1, 1])[1:]])            # toe (+s) -> crown -> toe (-s)
    return np.vstack([full_outer, full_inner[1:-1]])


def bead_bundles(asm):
    """Bead wire bundle centres (s, r) (both sides) and size, for the section views."""
    rim, t = asm["rim"], asm["tyre"]
    s = rim["flange_s"] - 0.45 * rim["ledge"]
    r = rim["bead_r"] + 0.55 * t["bead_wire"] + 0.002
    return [(-s, r), (s, r)], t["bead_wire"]


def web_face(rim):
    """s of the outer face of each wheel half's web: web_s where the table gives it (nose: a shallow dish, the tie-bolt
    heads visible), else the web lies beside the split plane (web_t; main: covered by the hub fairing / the brake)."""
    ws = rim.get("web_s")
    return float(rim["web_t"] if ws is None else ws)


def rim_half(asm, side=1):
    """Closed cross-section (s, r) of ONE wheel half (side +1: s > 0 half, -1: s < 0 half), upper half-plane: rim
    barrel with the bead ledge and flange (tip round), web (beside the split plane, or its outer face at web_s with the
    hollow between the two webs outside the section), hub barrel with the bearing bore.  Features at discrete clock
    angles (tie bolts, valve) are separate (drawn revolved into the section plane)."""
    rim = asm["rim"]
    fs, br, ft = rim["flange_s"], rim["bead_r"], rim["flange_t"]
    rho = ft / 2
    rf = br + rim["flange_h"]
    bt, st, wt = rim["barrel_t"], rim["seat_step"], rim["web_t"]
    hub_end = rim["hub_s"][1] if side > 0 else -rim["hub_s"][0]
    f = 0.004
    ri = br - bt
    ws = web_face(rim)
    P = [np.array([[0.0, br - st], [fs - rim["ledge"] - 0.004, br - st], [fs - rim["ledge"], br],
                   [fs - 0.003, br]]),
         _arc((fs - 0.003, br + 0.003), 0.003, -90.0, 0.0, 5)[1:],
         np.array([[fs, rf - rho]]),
         _arc((fs + rho, rf - rho), rho, 180.0, 0.0, 9)[1:],
         np.array([[fs + ft, ri]]),
         np.array([[ws + f, ri]]), _arc((ws + f, ri - f), f, 90.0, 180.0, 5)[1:],
         np.array([[ws, rim["hub_r"] + f]]), _arc((ws + f, rim["hub_r"] + f), f, 180.0, 270.0, 5)[1:],
         np.array([[hub_end, rim["hub_r"]], [hub_end, rim["hub_bore"]]])]
    if ws > wt + 1e-9:                                   # web set out: its inner face, then the barrel back to s = 0
        wi = ws - wt
        P += [np.array([[wi, rim["hub_bore"]], [wi, ri], [0.0, ri]])]
    else:
        P += [np.array([[0.0, rim["hub_bore"]]])]
    P = np.vstack(P)
    return P * [side, 1]


def bearing_boxes(asm):
    """Tapered roller bearings (simplified: rectangles s0, s1, r0, r1), one at each hub end."""
    rim, ax = asm["rim"], asm["axle"]
    out = []
    for e in rim["hub_s"]:
        sg = 1 if e > 0 else -1
        s1 = e - sg * 0.002
        s0 = s1 - sg * rim["bearing_w"]
        out.append((min(s0, s1), max(s0, s1), ax["r"], rim["hub_bore"]))
    return out


def tie_bolt_section(asm):
    """Tie bolt revolved into the section plane (s0, s1, r, shank dia, head AF): through both webs, head on the
    -s web, nut on the +s web."""
    rim = asm["rim"]
    af = 0.016 if asm["which"] == "main" else 0.013
    h = 0.5 * af
    ws = web_face(rim)
    return dict(s0=-ws - h, s1=ws + h + 0.004, r=rim["tie_r"], d=rim["tie_d"], af=af, h=h, web=ws)


def fairing_section(asm):
    """Main hub fairing, (s, r) centre line of the sheet from the lip edge to the axis, upper half: flat lip ring on
    the outboard rim-flange face (s0), straight conical wall, round face_R at the face edge, flat face at s1 = s0 +
    proud.  Returns (P, s0, s1); thickness MAIN_FAIRING['t']."""
    fa, rim = asm["fairing"], asm["rim"]
    s0 = rim["flange_s"] + rim["flange_t"]
    r_lip, r_in = fa["r_lip"], fa["r_lip"] - fa["lip_w"]
    s1, rf, q = s0 + fa["proud"], fa["r_face"], fa["face_R"]
    p0 = np.array([s0, r_in])
    u = np.array([s1 - s0, rf - r_in])
    u /= np.linalg.norm(u)
    n = np.array([-u[1], u[0]])                          # wall normal pointing away from the axis
    t = (s1 - q - s0 + q * n[0]) / u[0]                  # round centre q below the wall line and q inside the face
    c = p0 + t * u - q * n
    P = np.vstack([[[s0, r_lip], [s0, r_in]], [p0 + t * u], _arc(c, q, _ang(n), 0.0, 7)[1:], [[s1, 0.0]]])
    return P, s0, s1


def brake_lobe_outline(asm, n=360):
    """Six-lobed housing outline in the wheel plane: (N, 2) (dx, dz) about the axle, clock-true for the view from
    port (a view from starboard mirrors dx).  Star-shaped: r(th) = soft max of the body circle and the lobe circles
    (lobe_c, lobe_R) along each ray."""
    b = asm["brake"]
    th = np.radians(np.linspace(0.0, 360.0, n, endpoint=False))
    k = int(b["lobes"])
    c, a, rb, fil = b["lobe_c"], b["lobe_R"], b["body_R"], b["lobe_fillet"]
    lob = np.radians(b["lobe_th"] + 360.0 / k * np.arange(k))
    rr = np.full_like(th, rb)
    for L in lob:
        phi = np.angle(np.exp(1j * (th - L)))
        cs = c * np.sin(phi)
        ok = np.abs(cs) <= a
        rl = np.where(ok, c * np.cos(phi) + np.sqrt(np.maximum(a * a - cs * cs, 0.0)), 0.0)
        rr = fil * np.logaddexp(rr / fil, rl / fil)
    return np.c_[rr * np.cos(th), rr * np.sin(th)]


def brake_stack(asm):
    """Disc stack from the housing's inner face towards the split plane: [(kind, s0, s1, r0, r1)] with kind
    'pressure_plate' | 'lining' | 'rotor' | 'stator' | 'back_plate'."""
    b = asm["brake"]
    s = b["housing_s"][1]
    out = []

    def put(kind, t, rr):
        nonlocal s
        out.append((kind, s, s + t, rr[0], rr[1]))
        s += t

    sr, rr = b["stator_r"], b["rotor_r"]
    put("pressure_plate", b["pressure_plate_t"], sr)
    for i in range(int(b["rotors"])):
        put("lining", b["lining_t"], sr)
        put("rotor", b["rotor_t"], rr)
        put("lining", b["lining_t"], sr)
        put("stator" if i < int(b["rotors"]) - 1 else "back_plate",
            b["stator_t"] if i < int(b["rotors"]) - 1 else b["back_plate_t"], sr)
    return out


def clock_points(n, r, th0):
    """(dx, dz) of n equally spaced features on radius r from clock th0 (deg, view from port)."""
    a = np.radians(th0 + 360.0 / n * np.arange(n))
    return np.c_[r * np.cos(a), r * np.sin(a)]


def hexagon(c, af, rot=0.0):
    """Hexagon (6, 2) across flats af about c (flats at rot deg)."""
    R = af / math.sqrt(3.0)
    a = np.radians(rot + 30.0 + 60.0 * np.arange(6))
    return np.c_[c[0] + R * np.cos(a), c[1] + R * np.sin(a)]


# ================================================================================================ checks / numbers
def key_numbers(asm, R=None):
    """Derived numbers for the tables / call-outs."""
    fr = tyre_frame(asm, R)
    t, rim = asm["tyre"], asm["rim"]
    g_out = max(t["grooves"]) + t["groove_w"] / 2
    return dict(
        R=fr["R"], W=fr["W"], H=fr["H"], aspect=fr["H"] / fr["W"], rw=fr["rw"], hw=fr["hw"], Ru=fr["Ru"],
        tread_hw=float(fr["T1"][0]), drop_outer_groove=fr["R"] - float(crown_r(fr, max(t["grooves"]))),
        crown_drop_at_tread_edge=fr["R"] - float(fr["T1"][1]),
        Rl=fr["Rl"], B=fr["B"].tolist(), r_flange=rim["bead_r"] + rim["flange_h"],
        groove_frac=[g / fr["W"] for g in t["grooves"]], outer_rib=float(fr["T1"][0]) - g_out,
        centre_rib=2 * min(t["grooves"]) - t["groove_w"],
        mid_rib=(max(t["grooves"]) - min(t["grooves"])) - t["groove_w"],
    )


def tra_envelope_check(which="main"):
    """The modelled free section against the TRA envelope: OD and W inside the min / max range, and the section's
    radius at the TRA max shoulder half-width against the TRA max shoulder radius (the tyre must lie inside that
    growth / clearance envelope)."""
    asm = MAIN if which == "main" else NOSE
    e, env = TYRE_ENV[which], envelope(which)
    tol = 0.001                                           # gear.NOSE_TYRE rounds 444.5 / 158.75 to 445 / 159
    out = dict(od=2 * env["R"], od_ok=e["od_min"] - tol <= 2 * env["R"] <= e["od_max"] + tol, W=env["W"],
               W_ok=e["W_min"] - tol <= env["W"] <= e["W_max"] + tol, s=None, r_model=None, r_tra_max=None,
               shoulder_ok=None, tra=e["shoulder_d"] is not None)
    if e["shoulder_d"] is None:                           # 22x8.50-10: not a TRA size, no growth envelope
        return out
    fr = tyre_frame(asm)
    P = tyre_outer_half(asm, grooves=False, n=40)
    P = P[P[:, 1] >= fr["rw"]]                             # crown -> max width: s increases monotonically
    s = e["shoulder_w"] / 2
    r_model = float(np.interp(s, P[:, 0], P[:, 1]))
    out.update(s=s, r_model=r_model, r_tra_max=e["shoulder_d"] / 2, shoulder_ok=r_model <= e["shoulder_d"] / 2)
    return out


def fairing_beyond_tyre(asm=None):
    """How far (m) the main hub fairing's face stands outboard of the tyre's max section width (> 0: the fairing is
    the outermost point of the wheel; retracted, the lowest)."""
    asm = asm or MAIN
    _, s0, s1 = fairing_section(asm)
    return s1 + asm["fairing"]["t"] / 2 - envelope("main")["W"] / 2


# ================================================================================================ loaded tyre
def loaded_blend(which):
    """Side-view construction of the statically loaded tyre: (R, h = loaded radius, a = contact half-length, rb =
    radius of the two blend arcs joining the flat contact to the free circle, or None when the deflection is too small
    for a blend (the free circle is then simply cut by the ground))."""
    e = TYRE_ENV[which]
    R, h = float(e["R"]), float(e["R_loaded"])
    d = R - h
    if d < 0.002 or e["patch_l"] <= 0.0:
        return R, h, math.sqrt(max(R * R - h * h, 0.0)), None
    a = float(e["patch_l"]) / 2
    if a * a >= R * R - h * h:
        raise ValueError("loaded tyre: contact patch longer than the free circle's chord at the ground")
    rb = (R * R - h * h - a * a) / (2.0 * d)               # tangent to the flat and internally to the free circle
    return R, h, a, rb


def loaded_side_outline(which, n=240):
    """Side-view outline (dx, dz) about the axle of the statically loaded tyre, closed, counter-clockwise: the free
    circle R, flattened onto the ground at dz = -R_loaded over the contact patch, joined by two blend arcs tangent to
    the flat and to the free circle."""
    R, h, a, rb = loaded_blend(which)
    nf = max(3, int(math.ceil(2 * a / 0.004)) + 1)          # the flat carries its own points (every <= 4 mm): the 3-D
    flat = np.c_[np.linspace(-a, a, nf), np.full(nf, -h)]    # deformation interpolates this outline by clock angle
    if rb is None:
        t0 = math.degrees(math.atan2(-h, a))
        P = _arc((0.0, 0.0), R, t0, -180.0 - t0 + 360.0, n)
        return np.vstack([P, flat[1:]])
    cr = np.array([a, -h + rb])
    tr = _ang(cr)
    tl = -180.0 - tr
    big = _arc((0.0, 0.0), R, tr, tl + 360.0, n)
    left = _arc((-a, -h + rb), rb, tl + 360.0, 270.0, 16)[1:]
    right = _arc((a, -h + rb), rb, 270.0, tr + 360.0, 16)[1:-1]
    return np.vstack([big, left, flat[1:], right])


def free_below_ground(which, n=60):
    """The free circle's arc below the ground line (dx, dz about the axle): the static deflection, for the phantom."""
    R, h, _, _ = loaded_blend(which)
    t0 = math.degrees(math.atan2(-h, math.sqrt(max(R * R - h * h, 0.0))))
    return _arc((0.0, 0.0), R, -180.0 - t0, t0, n)


def loaded_headon_half(asm, n=16):
    """Head-on silhouette of the loaded tyre below the axle, s >= 0 half, as (s, r_down), r_down = distance below the
    axle: the side line at W/2 from the axle to the max-width radius rw, then the upper sidewall and shoulder
    compressed so that the tread edge lands on the ground (the tread flat across its width on the ground, the sidewall
    bulged by bulge), then the flat contact to the mid-plane.  Small deflections (the tread edge above the ground
    line): the free profile cut by the ground."""
    which = asm["which"]
    e = TYRE_ENV[which]
    fr = tyre_frame(asm)
    h, bulge = float(e["R_loaded"]), float(e["bulge"])
    P = tyre_outer_half(asm, grooves=False, n=n)
    k = int(np.argmin(np.abs(P[:, 0] - fr["hw"]) + np.abs(P[:, 1] - fr["rw"])))
    arc = P[:k + 1][::-1]                                           # max width -> crown top
    st, rt = float(fr["T1"][0]), float(fr["T1"][1])
    if h < rt:
        seg = arc[arc[:, 0] > st + 1e-9]
        seg = np.vstack([seg, [[st, rt]]])
        u = (seg[:, 1] - fr["rw"]) / (rt - fr["rw"])
        out = np.c_[seg[:, 0] + bulge * np.sin(np.pi * u), fr["rw"] + u * (h - fr["rw"])]
        return np.vstack([[[fr["hw"], 0.0]], out, [[0.0, h]]])
    out = arc.copy()
    out[:, 1] = np.minimum(out[:, 1], h)
    return np.vstack([[[fr["hw"], 0.0]], out])


def loaded_crown_r(asm, s):
    """Distance below the axle of the loaded tread at axial position s (grooves seen head-on end there)."""
    H = loaded_headon_half(asm, n=24)
    H = H[1:]                                                       # drop the axle-level start of the side line
    order = np.argsort(H[:, 0])
    return float(np.interp(abs(s), H[order, 0], H[order, 1]))


def plan_bulge(which, n=41):
    """Plan-view (from above) outer edge of the loaded sidewall bulge: (dx, s) for s >= 0, s = W/2 + bulge x
    (1 - (dx / (bulge_l / 2))^2)^2 about the contact (none when bulge = 0)."""
    e = TYRE_ENV[which]
    b, L = float(e["bulge"]), float(e["bulge_l"]) / 2
    if b <= 0.0 or L <= 0.0:
        return None
    x = np.linspace(-L, L, n)
    return np.c_[x, e["W"] / 2 + b * (1 - (x / L) ** 2) ** 2]


def tyre_plan_half(asm, R=None):
    """Plan-view (from above) silhouette of the free tyre, s >= 0 half, as (s, r): the crown / shoulder / upper
    sidewall profile from the crown top (s = 0, r = R) to the max width (W/2, rw); seen from above a point (s, r) of
    the profile is the outline at dx = +-r (the wheel's outline at the axle height)."""
    fr = tyre_frame(asm, R)
    P = tyre_outer_half(asm, R, grooves=False, n=16)
    k = int(np.argmin(np.abs(P[:, 0] - fr["hw"]) + np.abs(P[:, 1] - fr["rw"])))
    return P[:k + 1]


def fairing_plan(asm):
    """Main hub fairing from above: (s, r) of its outer surface from the lip plane to the face (radius at each s);
    the part at s > W/2 stands outboard of the tyre and is visible."""
    P, s0, s1 = fairing_section(asm)
    fa = asm["fairing"]
    t = fa["t"] / 2
    Q = P[1:-1] + [t, t]                                            # skin outer surface (approx.)
    Q = np.vstack([[[s0, fa["r_lip"]]], Q, [[s1 + t, 0.0]]])
    return Q[Q[:, 0] >= s0 - 1e-12]


# ================================================================================================ 3-D builders
# Stage 3: the wheels as meshes, revolved / extruded from the SAME profiles the sheet draws (tyre_outer_half's
# construction, rim_half, fairing_section, brake_lobe_outline, brake_stack, clock_points).  Local frame of one wheel:
# X = dx (aft, clock 0), Y = s (the tables' s: main = the outboard / hub-fairing face, nose = the port face),
# Z = dz (up); _frame() maps it into the model (the port main unit and the nose wheel's +s = -y are mirror frames).
# Segments round the axle: tyre silhouette chord sag 0.11 (main) / 0.19 mm (nose), rims <= 0.2 mm (4K close-ups).
SEGS = dict(main_tyre=112, nose_tyre=76, rim=64, nose_rim=48, rim_hidden=40, fairing=96, brake=40, small=12)
TRI_BUDGET = dict(main=30000, nose=18000)          # triangles per wheel assembly
GROOVE_EDGE = 0.0008                               # rib-edge round at the tread grooves (catches the satin highlight)
WHEEL_MATS = ("tire", "wheel", "paint_white", "metal", "metal_dark", "steel", "cadmium", "black", "brake_housing",
              "chrome")


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def _frame(center, e_s, aft=(1.0, 0.0, 0.0), up=(0.0, 0.0, 1.0)):
    """4x4 matrix local (X = dx aft, Y = s, Z = dz up) -> model; a mirror frame when e_s points to port."""
    e_s = _unit(e_s)
    ex = _unit(np.asarray(aft, float) - e_s * (e_s @ aft))
    ez = np.asarray(up, float) - e_s * (e_s @ up)
    ez = _unit(ez - ex * (ex @ ez))
    M = np.eye(4)
    M[:3, 0], M[:3, 1], M[:3, 2], M[:3, 3] = ex, e_s, ez, np.asarray(center, float)
    return M


def _split_creases(P, closed=False, deg=35.0):
    """Split a (s, r) polyline at the vertices where it turns by more than deg: [segment (N_i, 2)], consecutive
    segments sharing their end point (duplicated vertices -> crisp normals there).  closed: P is a loop."""
    P = np.asarray(P, float)
    keep = np.r_[True, np.linalg.norm(np.diff(P, axis=0), axis=1) > 1e-9]
    P = P[keep]
    if closed and np.linalg.norm(P[0] - P[-1]) < 1e-9:
        P = P[:-1]
    n = len(P)
    idx = range(n) if closed else range(1, n - 1)
    cos_lim = math.cos(math.radians(deg))
    crease = []
    for i in idx:
        a = P[i] - P[i - 1]
        b = P[(i + 1) % n] - P[i]
        if (a @ b) / (np.linalg.norm(a) * np.linalg.norm(b)) < cos_lim:
            crease.append(i)
    if closed:
        if not crease:
            return [np.vstack([P, P[:1]])]
        P = np.roll(P, -crease[0], axis=0)
        crease = [(c - crease[0]) % n for c in crease] + [n]
        P = np.vstack([P, P[:1]])
        return [P[a:b + 1] for a, b in zip(crease[:-1], crease[1:])]
    cuts = [0] + crease + [n - 1]
    return [P[a:b + 1] for a, b in zip(cuts[:-1], cuts[1:])]


def _rev(segs, n, th0=0.0):
    """Revolve smooth (s, r) segments about the local Y axis (n segments, first at clock th0 deg): smooth normals
    along each segment (chord tangents), crisp between segments.  Normals point to the left of the direction of
    travel in (s, r) (outward, away from the axis, for a profile running +s)."""
    th = math.radians(th0) + np.linspace(0.0, 2 * np.pi, n, endpoint=False)
    c, sn = np.cos(th), np.sin(th)
    out = []
    for P in segs:
        P = np.asarray(P, float)
        m = len(P)
        if m < 2:
            continue
        T = np.empty_like(P)
        T[1:-1] = P[2:] - P[:-2]
        T[0], T[-1] = P[1] - P[0], P[-1] - P[-2]
        T /= np.maximum(np.linalg.norm(T, axis=1), 1e-15)[:, None]
        ns, nr = -T[:, 1], T[:, 0]
        V = np.stack([P[:, 1, None] * c, np.repeat(P[:, 0, None], n, 1), P[:, 1, None] * sn], -1)
        N = np.stack([nr[:, None] * c, np.repeat(ns[:, None], n, 1), nr[:, None] * sn], -1)
        i, j = np.meshgrid(np.arange(m - 1), np.arange(n), indexing="ij")
        a, b = i * n + j, (i + 1) * n + j
        cc, d = (i + 1) * n + (j + 1) % n, i * n + (j + 1) % n
        F = np.vstack([np.stack([a, b, cc], -1).reshape(-1, 3), np.stack([a, cc, d], -1).reshape(-1, 3)])
        mesh = Mesh(V.reshape(-1, 3), F, N.reshape(-1, 3))
        mesh.remove_degenerate()
        out.append(mesh)
    return Mesh.merge(out)


def _rev_closed(P, n, side=1, th0=0.0, deg=35.0):
    """Revolve a closed section (s, r) (e.g. rim_half), mirrored to s < 0 for side -1 (order reversed so that the
    normals still point out of the material)."""
    P = np.asarray(P, float)
    return _rev(_split_creases(P if side > 0 else P[::-1], closed=True, deg=deg), n, th0)


def _prism(poly_xz, s0, s1, cap0=True, cap1=True):
    """Straight prism along local Y from s0 to s1 over the (convex / star-shaped) polygon poly_xz (N, 2) in (X, Z):
    flat-shaded sides, fan caps."""
    Q = np.asarray(poly_xz, float)
    k = len(Q)
    j = np.arange(k)
    j1 = (j + 1) % k
    A0 = np.c_[Q[:, 0], np.full(k, s0), Q[:, 1]]
    A1 = np.c_[Q[:, 0], np.full(k, s1), Q[:, 1]]
    quads = np.stack([A0[j], A0[j1], A1[j1], A1[j]], 1)                    # (k, 4, 3)
    nrm = np.cross(quads[:, 1] - quads[:, 0], quads[:, 3] - quads[:, 0])
    ctr = np.r_[Q.mean(0)[0], 0.0, Q.mean(0)[1]]
    out_dir = quads.mean(1) - ctr
    out_dir[:, 1] = 0.0
    flip = np.sum(nrm * out_dir, 1) < 0
    nrm = nrm / np.maximum(np.linalg.norm(nrm, axis=1), 1e-15)[:, None]
    nrm[flip] *= -1
    F = np.array([[0, 1, 2], [0, 2, 3]])
    FF = (F[None] + 4 * j[:, None, None]).reshape(-1, 3)
    FF = np.where(np.repeat(flip, 2)[:, None], FF[:, ::-1], FF)
    parts = [Mesh(quads.reshape(-1, 3), FF, np.repeat(nrm, 4, 0))]
    sg = 1.0 if s1 > s0 else -1.0
    for A, on, d in ((A0, cap0, -sg), (A1, cap1, sg)):
        if on:
            parts.append(cap_ring(A, (0.0, d, 0.0)))
    return Mesh.merge(parts)


def _stud(c_xz, s0, s1, r, n=10, cap=True):
    """Round boss / stem along local Y at (X, Z) = c_xz from s0 to s1."""
    return cylinder(np.array([c_xz[0], s0, c_xz[1]]), np.array([c_xz[0], s1, c_xz[1]]), r, n=n, cap=cap)


def _dome(c_xz, s0, r, h, n=10):
    """Low domed head (countersunk screw, rivet) on the plane s0, rising h towards +s (h < 0: towards -s)."""
    sg = 1.0 if h > 0 else -1.0
    prof = [(0.0, r), (0.55 * abs(h), 0.78 * r), (abs(h), 0.0)]
    return revolve(prof, n=n, axis_origin=(c_xz[0], s0, c_xz[1]), axis_dir=(0.0, sg, 0.0))


def tyre_profile_3d(asm, R=None, edge=GROOVE_EDGE):
    """Full outer tyre section for the 3-D revolve, (N, 2) (s, r) from the -s bead to the +s bead: the tangent-arc
    construction of tyre_frame() (crown, shoulder round, upper / lower sidewall to the rim-flange contact B), the
    tread grooves as drawn (tapered walls, the round floor as 3 points, rib edges rounded by `edge`), and a
    short tuck from B into the rim flange (hidden) so that the tyre meets the rim without a gap."""
    fr = tyre_frame(asm, R)
    t, rim = asm["tyre"], asm["rim"]
    w, d, fw = t["groove_w"], t["groove_d"], t["groove_floor"]
    cr = lambda x: float(crown_r(fr, x))                                  # noqa: E731
    pts = [(0.0, cr(0.0))]
    last = 0.0
    for g in sorted(t["grooves"]):
        a, b = g - w / 2, g + w / 2
        fl = cr(g) - d
        if a - edge - last > 0.012:                                       # long rib: an intermediate point
            m = 0.5 * (last + a - edge)
            pts.append((m, cr(m)))
        fc = fl + fw / 2                                                  # floor round centre (tyre_outer_half)
        pts += [(a - edge, cr(a - edge)), (a + 0.25 * edge, cr(a) - edge), (g - fw / 2, fc), (g, fl),
                (g + fw / 2, fc), (b - 0.25 * edge, cr(b) - edge), (b + edge, cr(b + edge))]
        last = b + edge
    T1 = fr["T1"]
    m = 0.5 * (last + T1[0])
    pts += [(m, cr(m))]
    Q, Cu, Cl = fr["Q"], fr["Cu"], fr["Cl"]
    pts += [tuple(p) for p in _arc(Q, fr["Rs"], _ang(T1 - Q), _ang(fr["T2"] - Q), 7)]
    pts += [tuple(p) for p in _arc(Cu, fr["Ru"], _ang(fr["T2"] - Cu), 0.0, 6)[1:]]
    pts += [tuple(p) for p in _arc(Cl, fr["Rl"], 0.0, _ang(fr["B"] - Cl), 6)[1:]]
    pts.append((rim["flange_s"] - 0.0015, fr["Cf"][1] - 0.004))            # tuck (inside the flange tip)
    half = np.array(pts)
    keep = np.r_[True, np.linalg.norm(np.diff(half, axis=0), axis=1) > 1e-7]
    half = half[keep]
    return np.vstack([half[:0:-1] * [-1, 1], half])


def _loaded_tyre(V, which):
    """Statically loaded tyre (only where R_loaded is > 2 mm below R, loaded_blend): in the wheel plane each point's
    height above the rim flange is scaled so that the free circle becomes loaded_side_outline() (flat contact patch,
    blend arcs); the sidewalls bulge by up to `bulge` at the ground.  V: local vertices (X, s, Z)."""
    R, h, a, rb = loaded_blend(which)
    if rb is None:
        return V, False
    e = TYRE_ENV[which]
    asm = MAIN if which == "main" else NOSE
    r0 = asm["rim"]["bead_r"] + asm["rim"]["flange_h"]
    O = loaded_side_outline(which, n=720)
    phi_o = np.arctan2(O[:, 1], O[:, 0])
    rho_o = np.hypot(O[:, 0], O[:, 1])
    k = np.argsort(phi_o)
    phi = np.arctan2(V[:, 2], V[:, 0])
    rho = np.interp(phi, phi_o[k], rho_o[k], period=2 * np.pi)
    r = np.hypot(V[:, 0], V[:, 2])
    f = np.clip((rho - r0) / (R - r0), 0.0, 1.0)
    rn = np.where(r > r0, r0 + (r - r0) * f, r)
    c = np.clip((1.0 - f) / max(1.0 - (h - r0) / (R - r0), 1e-9), 0.0, 1.0)     # 1 at the contact centre
    W = e["W"]
    out = V.copy()
    sc = np.where(r > r0, rn / np.maximum(r, 1e-12), 1.0)
    out[:, 0] *= sc
    out[:, 2] *= sc
    out[:, 1] *= 1.0 + np.where(r > r0, 2.0 * float(e["bulge"]) / W * c, 0.0)
    return out, True


def tyre_mesh(asm, n=None, R=None):
    """The tyre (local frame): tyre_profile_3d() revolved, loaded at the ground where the envelope says so."""
    which = asm["which"]
    n = n or SEGS[f"{which}_tyre"]
    m = _rev([tyre_profile_3d(asm, R)], n, th0=0.0)
    if R is None:
        V, changed = _loaded_tyre(m.V, which)
        if changed:
            m.V = V
            m.compute_normals()
    return m


def _fairing_meshes(asm):
    """Main hub fairing (local frame): the lip ring on the outboard rim-flange face, conical wall and face round
    revolved from fairing_section() (sheet thickness t: outer skin), the flat face with the off-axis valve-access
    hole (Delaunay, exact outline) and the hole's wall; 5 countersunk screw heads on the lip.
    [(mesh, material)]; the paint is the builders' unpainted 'paint_white' (livery: the leg-door colour)."""
    from scipy.spatial import Delaunay
    fa = asm["fairing"]
    n = SEGS["fairing"]
    P, s0, s1 = fairing_section(asm)
    t = fa["t"]
    C = P[1:-1]                                              # centre line: lip inner edge -> wall -> face round
    T = np.gradient(C, axis=0)
    T /= np.linalg.norm(T, axis=1)[:, None]
    Nn = np.c_[-T[:, 1], T[:, 0]]                            # left of travel = away from the axis / towards +s
    Nn[0] = (1.0, 0.0)                                       # lip ring: +s
    O = C + 0.5 * t * Nn
    O[0] = (s0 + t, C[0][1])
    r_face = float(O[-1][1])
    s_face = float(O[-1][0])
    lip = np.array([[s0, fa["r_lip"]], [s0 + t, fa["r_lip"]], [s0 + t, C[0][1]]])
    prof = np.vstack([lip, O[1:]])
    shell = _rev(_split_creases(prof), n)
    # flat face with the valve-access hole
    th = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
    outer = np.c_[r_face * np.cos(th), r_face * np.sin(th)]
    hc = clock_points(1, fa["hole_r"], fa["hole_th"])[0]
    hr = fa["hole_d"] / 2
    nh = 40
    ah = np.linspace(0.0, 2 * np.pi, nh, endpoint=False)
    hole = np.c_[hc[0] + hr * np.cos(ah), hc[1] + hr * np.sin(ah)]
    g = np.arange(-r_face, r_face + 1e-9, 0.009)
    GX, GZ = np.meshgrid(g, g)
    G = np.c_[GX.ravel(), GZ.ravel()]
    G = G[(np.hypot(G[:, 0], G[:, 1]) < r_face - 0.005) & (np.hypot(G[:, 0] - hc[0], G[:, 1] - hc[1]) > hr + 0.004)]
    pts = np.vstack([outer, hole, G])
    tri = Delaunay(pts).simplices
    cen = pts[tri].mean(1)
    ok = (np.hypot(cen[:, 0], cen[:, 1]) < r_face) & (np.hypot(cen[:, 0] - hc[0], cen[:, 1] - hc[1]) > hr)
    tri = tri[ok]
    V = np.c_[pts[:, 0], np.full(len(pts), s_face), pts[:, 1]]
    face = Mesh(V, tri, np.tile((0.0, 1.0, 0.0), (len(V), 1)))
    if face.face_normals()[:, 1].mean() < 0:
        face.F = face.F[:, ::-1].copy()
    face.remove_degenerate()
    wall = cylinder(np.array([hc[0], s_face - t, hc[1]]), np.array([hc[0], s_face, hc[1]]), hr, n=nh,
                    cap=False).flipped()
    screws = Mesh.merge([_dome(c, s0 + t, fa["screw_d"] / 2, 0.0008, n=10)
                         for c in clock_points(int(fa["screws"]), fa["screw_r"], fa["screw_th"])])
    return [(Mesh.merge([shell, face, wall]), "paint_white"), (screws, "metal")]


def _tie_bolts(asm, th0):
    """Tie bolts through both webs on the bolt circle: hex heads on the -s web, nuts + bolt ends on the +s web."""
    rim = asm["rim"]
    b = tie_bolt_section(asm)
    af, h, web = b["af"], b["h"], b["web"]
    out = []
    for c in clock_points(int(rim["tie_n"]), rim["tie_r"], th0):
        rot = math.degrees(math.atan2(c[1], c[0]))
        out.append(_prism(hexagon(c, af, rot), -web, -web - h))
        out.append(_prism(hexagon(c, af, rot + 15.0), web, web + h))
        out.append(_stud(c, web + h, b["s1"], b["d"] / 2, n=8))
    return Mesh.merge(out)


def _valve(c_xz, s0, s1, sign=1.0):
    """Tyre valve: brass stem from the web (s0) to the cap, black rubber-sealed cap on the last 9 mm (to s1)."""
    sc = s1 - sign * 0.009
    return [(Mesh.merge([_stud(c_xz, s0, sc, 0.0032, n=10), _stud(c_xz, s0, s0 + sign * 0.004, 0.0055, n=10)]),
             "cadmium"), (_stud(c_xz, sc, s1, 0.0043, n=10), "black")]


def _brake_meshes(asm):
    """Main brake inside the inboard (s < 0) wheel half, local frame: six-lobed housing (outer face, lobe walls),
    a piston cap and a bolt on every lobe, the inlet fitting on the top lobe and the bleeder opposite, the disc stack
    (brake_stack: rotor / stator / plate edges) and the torque plate."""
    b = asm["brake"]
    so, si = b["housing_s"]                                  # outer (inboard-most) / inner face
    out = []
    ol = brake_lobe_outline(asm, n=144)
    k = len(ol)
    th = np.arctan2(ol[:, 1], ol[:, 0])
    r_in = b["torque_tube_r"][1]
    inner = np.c_[r_in * np.cos(th), r_in * np.sin(th)]
    # outer face: annulus between the bore and the lobed outline (normal -s), small bevel ring on the edge
    bev = 0.002
    rr = np.hypot(ol[:, 0], ol[:, 1])
    ol_in = ol * ((rr - bev) / rr)[:, None]
    rings = [np.c_[inner[:, 0], np.full(k, so), inner[:, 1]], np.c_[ol_in[:, 0], np.full(k, so), ol_in[:, 1]],
             np.c_[ol[:, 0], np.full(k, so + bev), ol[:, 1]]]
    j = np.arange(k)
    j1 = (j + 1) % k
    face = []
    for q in range(2):
        A, B = rings[q], rings[q + 1]
        V = np.vstack([A, B])
        F = np.vstack([np.stack([j, j1, j1 + k], 1), np.stack([j, j1 + k, j + k], 1)])
        mm = Mesh(V, F)
        if mm.face_normals()[:, 1].mean() > 0:
            mm = mm.flipped()
        face.append(mm)
    # lobe side wall (smooth, outward)
    T = np.roll(ol, -1, 0) - np.roll(ol, 1, 0)
    T /= np.linalg.norm(T, axis=1)[:, None]
    nw = np.c_[T[:, 1], -T[:, 0]]
    if np.mean(np.sum(nw * ol, 1)) < 0:
        nw = -nw
    A0 = np.c_[ol[:, 0], np.full(k, so + bev), ol[:, 1]]
    A1 = np.c_[ol[:, 0], np.full(k, si), ol[:, 1]]
    Nw = np.c_[nw[:, 0], np.zeros(k), nw[:, 1]]
    side = Mesh(np.vstack([A0, A1]), np.vstack([np.stack([j, j1, j1 + k], 1), np.stack([j, j1 + k, j + k], 1)]),
                np.vstack([Nw, Nw]))
    if np.mean(np.sum(side.face_normals() * np.c_[side.V[side.F].mean(1)[:, 0], np.zeros(len(side.F)),
                                                     side.V[side.F].mean(1)[:, 2]], 1)) < 0:
        side.F = side.F[:, ::-1].copy()
    out.append((Mesh.merge(face + [side]), "brake_housing"))
    # piston caps + bolts on the lobes; inlet fitting (top lobe) and bleeder (opposite)
    caps, bolts = [], []
    lobes = clock_points(int(b["lobes"]), b["lobe_c"], b["lobe_th"])
    for i, c in enumerate(lobes):
        caps.append(_stud(c, so, so - 0.004, 0.7 * b["lobe_R"], n=14))
        rot = math.degrees(math.atan2(c[1], c[0]))
        bolts.append(_prism(hexagon(c, 0.011, rot), so - 0.004, so - 0.0095))
    fit = [_radial_stud(b["lobe_th"], r0, r1, FITTING_S, rr, n) for r0, r1, rr, n in _fitting_parts(b)]
    bleed = [_radial_stud(b["lobe_th"] + 180.0, r0, r1, FITTING_S, 0.7 * rr, n) for r0, r1, rr, n in _fitting_parts(b)]
    out += [(Mesh.merge(caps + fit + bleed), "brake_housing"), (Mesh.merge(bolts), "steel")]
    # disc stack: outer edges stepping rotor (keyed to the wheel) / stator / plates; bore along the torque tube
    st = brake_stack(asm)
    prof = [(st[0][1], r_in)]
    for kind, a, c2, r0_, r1_ in st:
        prof += [(a, r1_), (c2, r1_)]
    prof.append((st[-1][2], r_in))
    prof = np.array(prof)
    keep = np.r_[True, np.linalg.norm(np.diff(prof, axis=0), axis=1) > 1e-9]
    prof = prof[keep]
    # drop the collinear middle points (equal radii of consecutive items)
    Pm = [prof[0]]
    for q in range(1, len(prof) - 1):
        if not (abs(prof[q - 1][1] - prof[q][1]) < 1e-9 and abs(prof[q][1] - prof[q + 1][1]) < 1e-9):
            Pm.append(prof[q])
    Pm.append(prof[-1])
    Pm = np.array(Pm)
    stack = _rev(_split_creases(np.vstack([Pm, [Pm[0]]]), closed=True, deg=30.0), SEGS["brake"])
    # the section runs -> +s along the outer edge: outward already; torque plate on the axle flange
    tp = b["torque_plate"]
    plate = _rev_closed(np.array([[tp[0], tp[2]], [tp[1], tp[2]], [tp[1], tp[3]], [tp[0], tp[3]]])[::-1],
                        SEGS["brake"])
    out.append((Mesh.merge([stack, plate]), "metal_dark"))
    return out


FITTING_S = -0.093          # s of the brake inlet fitting / bleeder axis (in the housing, clear of the rim flange face)


def _fitting_parts(b):
    """Radial inlet fitting on the top lobe's tip (sheet L4W view C / detail H): (r0, r1, radius, segments) of the
    boss, the hex (6 segments) and the hose nipple."""
    top = b["lobe_c"] + b["lobe_R"]
    return ((top - 0.003, top + 0.003, b["fitting_d"] / 2, 12), (top + 0.003, top + 0.008, 0.0075, 6),
            (top + 0.008, top + 0.012, 0.0035, 10))


def _radial_stud(th_deg, r0, r1, s, rr, n):
    th = math.radians(th_deg)
    u = np.array([math.cos(th), 0.0, math.sin(th)])
    return cylinder(u * r0 + [0.0, s, 0.0], u * r1 + [0.0, s, 0.0], rr, n=n)


def brake_fitting_local(asm=None):
    """Local (X, s, Z) of the brake inlet fitting's nipple end (the brake line starts here) and its direction."""
    asm = asm or MAIN
    b = asm["brake"]
    th = math.radians(b["lobe_th"])
    u = np.array([math.cos(th), 0.0, math.sin(th)])
    return u * _fitting_parts(b)[-1][1] + [0.0, FITTING_S, 0.0], u


def _main_local():
    """Main wheel assembly in the local frame: [(mesh, material)]."""
    asm = MAIN
    rim = asm["rim"]
    out = [(tyre_mesh(asm), "tire")]
    # wheel halves: the inboard (brake) half in full, the outboard half under the fairing coarser
    out.append((Mesh.merge([_rev_closed(rim_half(asm, -1), SEGS["rim"], -1),
                            _rev_closed(rim_half(asm, 1), SEGS["rim_hidden"], 1)]), "wheel"))
    out += _fairing_meshes(asm)
    out.append((_tie_bolts(asm, 180.0 / rim["tie_n"]), "cadmium"))
    out += _valve(clock_points(1, rim["valve_r"], rim["valve_th"])[0], web_face(rim), rim["valve_s"], 1.0)
    out += _brake_meshes(asm)
    return out


def _nose_local():
    """Nose wheel assembly in the local frame (+s = the port face): [(mesh, material)]."""
    asm = NOSE
    rim = asm["rim"]
    out = [(tyre_mesh(asm), "tire")]
    out.append((Mesh.merge([_rev_closed(rim_half(asm, -1), SEGS["nose_rim"], -1),
                            _rev_closed(rim_half(asm, 1), SEGS["nose_rim"], 1)]), "wheel"))
    out.append((_tie_bolts(asm, rim["tie_th"]), "cadmium"))
    out += _valve(clock_points(1, rim["valve_r"], rim["valve_th"])[0], web_face(rim), rim["valve_s"], 1.0)
    # chrome bearing cap / seal rings at the hub ends (NOSE_AXLE cap_r: between the axle and the white hub boss,
    # 1.5 mm proud of the hub end -- the fork arm's inner face is 2 mm beyond it --, rounded outer edge)
    ax = asm["axle"]
    c0, c1 = ax["cap_r"]
    rings = []
    for e in rim["hub_s"]:
        sg = 1.0 if e > 0 else -1.0
        prof = np.vstack([[[e - sg * 0.004, c1]], [[e + sg * 0.0005, c1]],
                          _arc((e + sg * 0.0005, c1 - 0.001), 0.001, 90.0, 90.0 - sg * 90.0, 4)[1:],
                          [[e + sg * 0.0015, c0]], [[e - sg * 0.004, c0]]])
        rings.append(_rev([prof if sg > 0 else prof[::-1]], SEGS["small"] * 2))
    out.append((Mesh.merge(rings), "chrome"))
    return out


def _merge_by_material(items):
    acc = {}
    for m, mat in items:
        acc.setdefault(mat, []).append(m)
    return [(Mesh.merge(v), k) for k, v in acc.items()]


_LOCAL = {}


def _local(which):
    """Cached local assembly (the tables are module constants)."""
    if which not in _LOCAL:
        _LOCAL[which] = _merge_by_material(_main_local() if which == "main" else _nose_local())
    return _LOCAL[which]


def main_wheel(center, axis=(0.0, 1.0, 0.0), side=1, parts=None):
    """Main wheel assembly at the axle point `center` (tyre mid-plane) about `axis` (unit, +y gear down) for the
    starboard (side +1) or port (-1) unit: tyre (geometric grooves), both wheel halves, the outboard hub fairing (5
    screws, valve-access hole), valve, tie bolts, the six-piston brake with its disc stack and torque plate inside the
    inboard half.  The outboard face (+s) is side * axis.  [(mesh, material)]; parts: a subset of materials."""
    M = _frame(center, np.asarray(axis, float) * side)
    return [(m.transformed(M), mat) for m, mat in _local("main") if parts is None or mat in parts]


def nose_wheel(center, axis=(0.0, 1.0, 0.0), parts=None):
    """Nose wheel assembly at `center` about `axis`: tyre, both white wheel halves, tie bolts (heads starboard, nuts
    port), valve on the port face, bearing seals.  Local +s (the port face) is -axis.  [(mesh, material)]."""
    M = _frame(center, -np.asarray(axis, float))
    return [(m.transformed(M), mat) for m, mat in _local("nose") if parts is None or mat in parts]


def main_axle_boss(center, axis=(0.0, 1.0, 0.0), side=1):
    """Trailing-arm axle boss (gear context, MAIN_AXLE): a round boss round the axle root on the inboard side
    (boss_s), its open bore (bore_r, 30 mm deep) facing inboard -- the axle is cantilevered outboard from it; edges
    rounded.  Model coordinates (mesh)."""
    ax = MAIN_AXLE
    s0, s1 = ax["boss_s"]
    R, rb, q = ax["boss_r"], ax["bore_r"], 0.004
    P = np.vstack([[[s0 + 0.030, 0.0], [s0 + 0.030, rb], [s0, rb]],
                   _arc((s0 + q, R - q), q, 180.0, 90.0, 4),
                   _arc((s1 - q, R - q), q, 90.0, 0.0, 4),
                   [[s1, ax["r"]]]])
    m = _rev(_split_creases(P, deg=35.0), 40)
    return m.transformed(_frame(center, np.asarray(axis, float) * side))


def tri_count(which):
    return sum(m.nf for m, _ in _local(which))


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    for asm in (MAIN, NOSE):
        k = key_numbers(asm)
        print(asm["which"], {a: (round(b, 4) if isinstance(b, float) else b) for a, b in k.items()})
        print("  TRA check", tra_envelope_check(asm["which"]))
        print("  loaded blend", [round(v, 4) if v is not None else None for v in loaded_blend(asm["which"])])
        print("  3-D gear.py tyre", gear_envelope(asm["which"]))
    print("fairing beyond the tyre width", round(fairing_beyond_tyre(), 4))
    print("brake stack", [(k, round(a, 4), round(b, 4)) for k, a, b, _, _ in brake_stack(MAIN)])
