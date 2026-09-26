"""
Wheels, tyres, main-wheel hub fairings and brakes of the PC-12 PRO landing gear: source-tagged PARAMETER TABLES and
the 2-D profiles drawn from them.  Stage 2 (drawings first): sheet L4W (drawing/wheel_sheet.py) is drawn from these
tables; the 3-D builder (model/gear.py wheel()) still builds its Stage-3 wheel and will revolve / extrude the same
profiles once the sheet is approved.

Tyre envelopes (MAIN_TYRE_ENV / NOSE_TYRE_ENV): free radius R, section width W, bead-seat radius rim and the static
loaded radius.  OWNER DECISION 2026-09-26: the main tyre is the 8.50-10 Type III that the tyre makers and the parts
lists give for the PC-12 (TRA envelope OD 627-652 mm); the 22x8.50-10 of Jane's / the Pilatus drawing (OD 559, not a
listed tyre size) is superseded (SUPERSEDED_MAIN).  The axles and the static stance are kept: the axle WL is the
loaded radius, so the main tyre is drawn flattened at the ground (41 mm static deflection).  The nose tyre stays the
17.5x6.25-6.  model/gear.py (MAIN_TYRE, the bays, the LD-1 door scallop, fit_check) still carries the 22 in tyre
until the Stage-3 wheel step takes MAIN_TYRE from here (gear_envelope() reads the 3-D value for the comparison).
The section tables refine the shape INSIDE the envelopes: tyre cross-section (bead, sidewall, shoulder, crown,
grooves), the split-hub wheel halves, the main-wheel outboard hub fairing, the six-piston main brake, axle and paint.

Source tags: [S] sourced (NGX POH 02406 7-4, Ground Servicing Guide 02527, Goodyear aviation data book 2018 = TRA
tyre / rim data, parts listings), [M] measured on photographs (PRO s/n 3001, 3005, 3008, 3010, 3036, 3066 and the NGX
broadside; the photos and the measurements' working stay in the git-ignored refs/cache), [E] estimated /
reconstructed (hidden or not resolved in photos), [D] derived from other entries, [G] the current gear.py value,
[O] owner decision.

Local wheel coordinates (m): s along the axle from the tyre mid-plane, positive towards the face seen in the side
view from PORT (main gear: the port unit's OUTBOARD face = the hub-fairing side, the brake on s < 0; nose gear: the
port face); r radial from the axle.  Clock angles th (deg) in the wheel plane as seen from port: 0 = aft (+x),
90 = up (+z).  The starboard units are mirror images.  The wheels turn, so the clocking of screws / valves / lobes
(the brake housing does not turn) is only the drawn pose.  Model coordinates of the port units: x = axle x + dx,
y = axle y - s, z = axle z + dz.
"""
from __future__ import annotations

import math

import numpy as np

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
MAIN_TYRE_ENV = PTable(
    "Main tyre envelope: 8.50-10 Type III (owner decision 2026-09-26)",
    size=("8.50-10 Type III", "O", "tyre makers / parts lists; supersedes Jane's 22x8.50-10 (not a listed size)"),
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

NOSE_TYRE_ENV = PTable(
    "Nose tyre envelope: 17.5x6.25-6",
    size=("17.5x6.25-6", "S", "Jane's; parts lists; photos confirm 17.5 in (camera check)"),
    part=("Goodyear 175K88B1 / Michelin 021-327-0", "S", "8 PR tubeless (parts listings)"),
    R=(0.2225, "S", "free radius: 17.5 in OD (444.5); = gear.NOSE_TYRE"),
    W=(0.159, "S", "section width 6.25 in (TRA max; min 5.9 in); = gear.NOSE_TYRE"),
    rim=(0.076, "S", "bead-seat radius (6 in rim); = gear.NOSE_TYRE"),
    R_loaded=(0.222, "G", "axle WL kept (gear.NOSE_AXLE); photos read ~205 (not modelled)"),
    patch_l=(0.0, "D", "no blend: the free circle cut by the ground (0.5 mm static deflection)"),
    bulge=(0.0, "E", "no bulge at 0.5 mm deflection"),
    bulge_l=(0.0, "E", "-"),
    od_max=(17.5 * IN, "S", "TRA OD max 17.5 in"),
    od_min=(16.85 * IN, "S", "TRA OD min 16.85 in"),
    W_max=(6.25 * IN, "S", "TRA section width max 6.25 in"),
    W_min=(5.9 * IN, "S", "TRA section width min 5.9 in"),
    shoulder_d=(15.45 * IN, "S", "TRA shoulder diameter max 15.45 in"),
    shoulder_w=(5.5 * IN, "S", "TRA shoulder width max 5.5 in"),
    slr=(6.9 * IN, "S", "static loaded radius at the rated 2900 lb / 70 psi (175K88B1)"),
    flat_r=(4.80 * IN, "S", "flat-tyre radius"),
)

SUPERSEDED_MAIN = PTable(
    "Superseded main tyre: 22x8.50-10 (Jane's; Pilatus drawing circle)",
    R=(0.2794, "S", "Jane's 22x8.50-10; Pilatus drawing 190.10.40.432 circle 558.8 (refs/mbp.py)"),
    status=("superseded", "O", "owner decision 2026-09-26; gear.MAIN_TYRE keeps R 0.2795 until the Stage-3 wheel step"),
)

TYRE_ENV = dict(main=MAIN_TYRE_ENV, nose=NOSE_TYRE_ENV)


def envelope(which):
    """(R, W, rim, R_loaded) of the modelled tyre envelope ('main' | 'nose')."""
    e = TYRE_ENV[which]
    return dict(R=float(e["R"]), W=float(e["W"]), rim=float(e["rim"]), R_loaded=float(e["R_loaded"]))


def gear_envelope(which):
    """The tyre model/gear.py builds in 3-D today (gear.MAIN_TYRE / NOSE_TYRE; imported lazily so that gear.py can
    import this module in Stage 3)."""
    from model import gear as G
    t = G.MAIN_TYRE if which == "main" else G.NOSE_TYRE
    return dict(R=float(t["R"]), W=float(t["W"]), rim=float(t["rim"]))


# ================================================================================================ main wheel
MAIN_TYRE_SEC = PTable(
    "Main tyre section (inside MAIN_TYRE_ENV, 8.50-10 Type III)",
    size=("8.50-10 Type III", "O", "owner decision 2026-09-26 (MAIN_TYRE_ENV)"),
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
    material=("housing metal / discs metal_dark", "M", "dull aluminium housing, dark steel discs"),
)

MAIN_AXLE = PTable(
    "Main axle and trailing-arm boss (context)",
    r=(0.026, "G", "axle radius (gear.build_main); cantilevered outboard from the arm boss"),
    bore_r=(0.0225, "M", "open axle bore, facing inboard (~45 mm)"),
    boss_r=(0.058, "M", "trailing-arm axle boss radius (dia 0.11-0.12)"),
    boss_s=((-0.165, -0.110), "E", "boss faces (arm at s = -0.14, gear.build_main)"),
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
    brake=("metal", "M", "housing dull aluminium / cadmium grey"),
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
    web_t=(0.009, "E", "web of each half beside the split plane"),
    hub_r=(0.031, "M", "raised hub boss (dia ~0.3 x flange dia)"),
    hub_bore=(0.026, "E", "bearing-cup bore radius"),
    hub_s=((-0.081, 0.081), "M", "hub ends at the fork arms' inner faces (+-0.083)"),
    bearing_w=(0.016, "E", "bearing width"),
    tie_n=(4, "E", "tie bolts: 3 visible per face beside the fork arm, the 4th assumed behind it"),
    tie_r=(0.048, "M", "tie-bolt circle radius (~0.5 x flange dia)"),
    tie_d=(0.008, "E", "tie-bolt shank; heads / nuts AF 0.013, cadmium-gold"),
    tie_th=(0.0, "M", "first tie bolt clock (+-20 deg)"),
    valve_r=(0.066, "M", "brass valve stem at ~0.7 x the flange radius, port face (3036)"),
    valve_th=(30.0, "M", "valve clock (drawn pose)"),
    valve_s=(0.052, "E", "valve cap s (inside the flange face)"),
    plug_th=(210.0, "E", "overinflation safety plug [S: POH] clock, starboard face"),
    paint=("wheel", "M", "gloss white, open on both faces (no fairing)"),
)

NOSE_AXLE = PTable(
    "Nose axle, fork arms (context)",
    r=(0.020, "G", "axle radius (gear.build_nose)"),
    fork_in=(0.083, "M", "fork arms' inner faces +-s: TWO arms (3001 / 3036 head-on, 3008 0517); gear.py has one"),
    fork_out=(0.118, "M", "fork arms' outer faces +-s (arm ~35 mm thick)"),
    thread_r=(0.014, "E", "threaded axle ends outboard of the fork arms"),
    boss_r=(0.031, "G", "fork-arm axle boss radius (gear.NOSE_FORK_SEC)"),
    arch=(0.025, "M", "yoke arch inner edge above the tyre crown (arch ~45-50 mm deep)"),
    nut_af=(0.032, "E", "hex axle nut across flats (steel), with a tear-drop lock plate"),
    nut_s=((0.118, 0.134), "E", "nut s range, outboard of each fork arm"),
    lock_plate=(0.050, "M", "tear-drop lock plate length along the arm (3036)"),
)

NOSE_PAINT = PTable(
    "Nose wheel materials",
    tyre=("tire", "M", "black satin rubber, no lettering"),
    wheel=("wheel", "M", "gloss white halves, open both faces (photos read a touch whiter than 'wheel')"),
    fasteners=("metal", "M", "tie bolts cadmium-gold, valve brass"),
    axle=("steel", "M", "hex axle nut + tear-drop lock plate"),
    fork=("gear_leg", "M", "two-arm fork yoke"),
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


def rim_half(asm, side=1):
    """Closed cross-section (s, r) of ONE wheel half (side +1: s > 0 half, -1: s < 0 half), upper half-plane: rim
    barrel with the bead ledge and flange (tip round), web beside the split plane, hub barrel with the bearing bore.
    Features at discrete clock angles (tie bolts, valve) are separate (drawn revolved into the section plane)."""
    rim = asm["rim"]
    fs, br, ft = rim["flange_s"], rim["bead_r"], rim["flange_t"]
    rho = ft / 2
    rf = br + rim["flange_h"]
    bt, st, wt = rim["barrel_t"], rim["seat_step"], rim["web_t"]
    hub_end = rim["hub_s"][1] if side > 0 else -rim["hub_s"][0]
    f = 0.004
    ri = br - bt
    P = [np.array([[0.0, br - st], [fs - rim["ledge"] - 0.004, br - st], [fs - rim["ledge"], br],
                   [fs - 0.003, br]]),
         _arc((fs - 0.003, br + 0.003), 0.003, -90.0, 0.0, 5)[1:],
         np.array([[fs, rf - rho]]),
         _arc((fs + rho, rf - rho), rho, 180.0, 0.0, 9)[1:],
         np.array([[fs + ft, ri]]),
         np.array([[wt + f, ri]]), _arc((wt + f, ri - f), f, 90.0, 180.0, 5)[1:],
         np.array([[wt, rim["hub_r"] + f]]), _arc((wt + f, rim["hub_r"] + f), f, 180.0, 270.0, 5)[1:],
         np.array([[hub_end, rim["hub_r"]], [hub_end, rim["hub_bore"]], [0.0, rim["hub_bore"]]])]
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
    return dict(s0=-rim["web_t"] - h, s1=rim["web_t"] + h + 0.004, r=rim["tie_r"], d=rim["tie_d"], af=af, h=h,
                web=rim["web_t"])


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
    fr = tyre_frame(asm)
    P = tyre_outer_half(asm, grooves=False, n=40)
    P = P[P[:, 1] >= fr["rw"]]                             # crown -> max width: s increases monotonically
    s = e["shoulder_w"] / 2
    r_model = float(np.interp(s, P[:, 0], P[:, 1]))
    tol = 0.001                                           # gear.NOSE_TYRE rounds 444.5 / 158.75 to 445 / 159
    return dict(od=2 * env["R"], od_ok=e["od_min"] - tol <= 2 * env["R"] <= e["od_max"] + tol, W=env["W"],
                W_ok=e["W_min"] - tol <= env["W"] <= e["W_max"] + tol, s=s, r_model=r_model,
                r_tra_max=e["shoulder_d"] / 2, shoulder_ok=r_model <= e["shoulder_d"] / 2)


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
    if rb is None:
        t0 = math.degrees(math.atan2(-h, a))
        P = _arc((0.0, 0.0), R, t0, -180.0 - t0 + 360.0, n)
        return np.vstack([P, [[a, -h]]])
    cr = np.array([a, -h + rb])
    tr = _ang(cr)
    tl = -180.0 - tr
    big = _arc((0.0, 0.0), R, tr, tl + 360.0, n)
    left = _arc((-a, -h + rb), rb, tl + 360.0, 270.0, 16)[1:]
    right = _arc((a, -h + rb), rb, 270.0, tr + 360.0, 16)[:-1]
    return np.vstack([big, left, right])


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
