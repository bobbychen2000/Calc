"""
Interior (flight deck + cabin, for the cutaway view) and primary structure (for the X-ray view).

STAGE 2 (rev C) -- the interior is defined FIRST as the parameter tables below (sheets L6 "INTERIOR ARRANGEMENT",
drawing/interior_sheet.py, and L6B "CHECKS", drawing/interior_checks.py, are drawn from them); the 3-D builder consumes
them in Stage 3, after the owner's review:

  flight deck  FLOOR, CREW_SEAT (seat reference point SRP, travel, IPECO 3A318-type seat body), design_eye(),
               PANEL / GLARESHIELD (Garmin G3000 PRIME: 3 x 14-in PDUs, 2 x 7-in SDUs), YOKE (PC-24 style), PEDALS,
               PEDESTAL (on the nose-wheel tunnel plinth), SIDE_CONSOLE, OVERHEAD, DIVIDER
  cabin        LINING (headliner / sidewall offsets), EXEC_SEAT, COMMUTER_SEAT, SEAT_LAYOUTS (EX-6S-2 = the PRO
               6-seat executive layout, EX-8S, STD-9S; POH weight-and-balance occupant arms), LEDGES, TABLES,
               LAVATORY, CABINETS, BAGGAGE
  criteria     MANIKIN (95th-percentile male) scaled to PCT (50th / 5th male, 5th female), CRITERIA; crew_setting()
               (each occupant's seat notch / crank / height), design_eye() (the 50th-pct eye at the neutral SRP),
               crew_checks() (eye, vision, knees vs the yoke swept over pitch and roll with neutral pedals and with
               full rudder: rudder_checks(), headroom, headrest vs the divider, recline, tunnel plinth, reach (grasp /
               touch), ingress, curtain / extinguisher vs the seats) / cabin_checks() (envelope, aisle, club legs,
               the club table vs the legs: table_leg_clearance() / table_posture(), head vs headrest, recline
               envelopes, exit access, lavatory); crew_sensitivity() (the knee / yoke result against each estimated
               input); cg_crosscheck() (POH occupant arms vs the 50th's CG on the drawn poses, occupant_cg())

Every value carries a one-line source note (P / PT .src): [S] sourced text (Pilatus, POH, Garmin, supplier),
[M] measured from a photo / render (the measurements themselves stay in the gitignored refs/cache), [E] estimated /
ergonomic, [H] hard constraint owned by another module.  The POH datum (3.000 m ahead of the firewall) is the model
datum, so POH arms are STA directly.

STAGE 3: the 3-D interior is built from exactly these tables -- build_flightdeck() (model/flightdeck.py, part
flight_deck, + the crew seats of model/seats.py: seat_pilot / seat_copilot), build_cabin() (model/cabin.py, part
cabin_interior, + one executive seat part per layout seat: seat_pax1 ..) and build_lining() (part interior_lining:
side-wall / headliner lining by the LINING law (lining_offset) with window reveals and door wells, materials lining /
lining_flightdeck).
Structure: fuselage frames at the Pilatus frame stations (fuselage.FRAMES, numbered frames interpolated between them)
interrupted at the openings, stringers, wing spars and ribs (representative, not the certified structural drawing).
"""
from __future__ import annotations
import math
import numpy as np

from cad.mesh import Mesh, sweep_tube, grid_surface, planar_cap, trim
from model.parts import Part
from model import fuselage as F
from model import wing as W


# =====================================================================================================================
# STAGE-2 INTERIOR PARAMETERS (rev C, sheet L6)
# =====================================================================================================================
class P(float):
    """A parameter value carrying its source note: behaves as a float, .src = '[S|M|E|H] note'."""

    def __new__(cls, v, src=""):
        o = super().__new__(cls, v)
        o.src = src
        return o

    def __reduce__(self):
        return P, (float(self), self.src)


class PT(tuple):
    """A tuple parameter (point, range, table) carrying its source note (.src)."""

    def __new__(cls, v, src=""):
        o = super().__new__(cls, v)
        o.src = src
        return o

    def __reduce__(self):
        return PT, (tuple(self), self.src)


def src(v):
    """Source note of a parameter value ('' for plain numbers)."""
    return getattr(v, "src", "")


# ---------------------------------------------------------------------------------------------------- envelope
CABIN = dict(                                # published envelope: L6 checks the layout against these
    length=P(5.16, "[S] NGX JTF 2024: cockpit/cabin partition to aft pressure bulkhead"),
    width=P(1.52, "[S] Pilatus: max cabin width"),
    height=P(1.47, "[S] NGX JTF 'continuous flat floor' (POH 1-4-7 / PRO JTF 2025: 1.45; model D1 uses 1.47)"),
    floor_width=P(1.30, "[S] Pilatus / POH 1-4-7"),
    floor_length=P(4.68, "[S] POH 1-4-7: partition to the baggage net (4.571 + 4.68 = 9.251 = FR34)"),
)
FLOOR = dict(
    wl=P(F.CABIN_FLOOR_WL, "[H] fuselage.CABIN_FLOOR_WL (D1): crown 2.769 - 0.040 - 1.470"),
    fd_wl=P(F.CABIN_FLOOR_WL, "[M] flight deck flush with the cabin: threshold strip, no step (PRO 3001, NGX 2281)"),
    fd_x0=P(3.05, "[M] footwell floor to the pedal pivots (Pilatus plan render: pedals 3.04-3.31)"),
    t=P(0.030, "[E] floor panel + carpet"),
    t_wing=P(0.015, "[H] <= 15 mm over the carry-through (wing.CS_FLOOR_CLEAR, fit_check 3)"),
    wing_x=PT((5.33, 7.554), "[H] carry-through flat top under the floor (interior audit)"),
    edge_bl=P(0.650, "[S] floor width 1.30 (section render floor edge +/-0.647 [M])"),
)
LINING = dict(
    crown=P(F.CABIN_LINING, "[H] 0.040 headliner at the crown (D1: gives the 1.47 cabin height)"),
    side=P(0.085, "[H] OML - 0.085 gives the published 1.52 max width (L1 SIDE_ALLOW; render lining +/-0.755)"),
    blend_p=P(2.0, "[E] offset = crown + (side - crown) |n_y|^p round the section (n = OML normal)"),
    headliner_flat=P(0.40, "[M] flat centre panel with LED coves either side (PRO photos)"),
    psu_bl=P(0.37, "[E] reading light + gasper per seat in the curved side panel (photos)"),
    reveal=P(0.085, "[M] deep white window reveals through the sidewall lining (photos)"),
)
DIVIDER = dict(
    x_aft=P(4.571, "[S] POH seat charts 'divider aft surface' 179.95 in (render 4.571-4.583; FR16 4.590)"),
    t=P(0.025, "[E] veneer partition wall"),
    open_bl=PT((-0.24, 0.26), "[M] 0.50 m open aisle, no door (PRO 3001 P1046406, plan render)"),
    curtain=PT((-1, 0.060, 0.060, 0.850, 0.025, 0.018, 0.006),
               "[S] 'cockpit/cabin bulkhead divider with curtain' (Pilatus tech data), on a track across the "
               "opening at the headliner, on the divider's fwd face. PRO 3001: stowed at the LH edge, orange "
               "(P1046406) [M]; NGX 2281: RH edge, grey [M]. Stow side, bundle width across / depth along x [E], "
               "flared bundle top above the floor [M: P1046406 camera-matched, orange to 0.83-0.87], tuck: the "
               "bundle's width behind the walnut edge (the photo shows 0.03-0.045 of it past the edge) [M], gathered "
               "band width across above the bundle, up the fwd face to the track, and the part of it showing past "
               "the edge [M: a thin sliver above the flare] (review r1 F2: rev C 0.060 wide in full view to 0.90)"),
    extinguisher=PT((4.500, 0.550, 0.300, 0.080, 0.300), "[S] fire extinguisher on the fwd face of the RH divider, "
                                                         "behind the co-pilot (POH 7-28); x (bottle against the face), "
                                                         "BL, centre height, bottle dia, length [E]: between the seat's "
                                                         "outboard plate and the lining"),
)
CLEAR_ZONES = dict(
    entry_bl=P(0.30, "[E] no furniture outboard of this |BL| abeam the airstair door (entry vestibule)"),
    exit_bl=P(0.16, "[E] exit clear zone from this BL to the starboard lining abeam the over-wing exit"),
)
SEAT_TRACKS = dict(
    bl=PT((0.26, 0.58), "[S] POH Fig 6-7-1: 12.6 | 20.47 | 12.6 in -> rails at BL +/-0.26 and +/-0.58"),
    x0=P(4.652, "[S] NGX POH Fig 6-8-1: first locating hole"),
    x1=P(9.25, "[E] to the baggage partition (FR34)"),
    w=P(0.030, "[E] track width"),
    mount="surface",
    h=P(0.012, "[E] cabin tracks surface-mounted (low profile, carpet butted) over the whole floor: over the "
               "carry-through the floor is <= 15 mm [H], too thin for a flush ~20-25 track (L6B); the cabin seat "
               "heights [M] are read from the carpet and include it"),
    crew_h=P(0.018, "[E] crew seat tracks (two per seat at CREW_SEAT rail_dy), surface-mounted on the flight-deck floor "
                    "(no carry-through under it); the crew SRP height is from the floor and includes them"),
)

# ---------------------------------------------------------------------------------------------------- flight deck
CREW_SEAT = dict(
    type="IPECO 3A318-series transport crew seat, 8-way, reclining, flip-up armrests, headrest, 4-point harness "
         "[S: Pilatus tech data, POH 7-7-1.1, supplier part listings]",
    bl=P(0.375, "[M] yoke centres +/-0.372 (Pilatus PRO cockpit key); plan render seat CL +/-0.37-0.39"),
    srp_x=P(4.20, "[E] SRP, centre notch: render cushion front 3.72 / headrest rear 4.47 [M]; the divider bounds it "
                  "aft. POH occupant arm 4.071 = the 50th's CG with the seat full aft (L6B cross-check)"),
    srp_h=P(0.280, "[E] SRP above the flight-deck floor, neutral height (notes: 0.28-0.30); puts the seat-back top "
                   "corner on the cabin photo's 0.86-0.90 above the floor (P1046406)"),
    travel_x=P(0.070, "[S] POH Table 6-5-3: +/-4 holes x 0.69 in (0.018 m)"),
    notch=P(0.018, "[S] POH: 0.69 in per hole, 9 positions"),
    travel_z=P(0.051, "[E] vertical adjustment +/-2 in (POH 7-7-1.1 vertical lever; IPECO travel not found): the "
                      "95th-pct male (full down) and the 5th-pct male (full up) both reach the design eye"),
    back_deg=P(13.0, "[E] upright back angle from vertical: puts the headrest rear (50th position) on the render's "
                     "4.47 at the centre notch (notes: 13-15 deg)"),
    pan_deg=P(7.0, "[E] seat pan, front up"),
    pan_depth=P(0.48, "[M] SRP to cushion front (render 3.72)"),
    cushion_t=P(0.090, "[E] cushion + sheepskin; top 0.025 above the SRP line (undeflected)"),
    sheepskin_t=P(0.034, "[M] grey sheepskin covers (PRO s/n 3001: P1046408 / 10, AOPA), INSIDE the drawn outline: the "
                         "cushion top and the back front (0.02 + lumbar ahead of the back line) are the fleece's "
                         "undeflected crown, the leather cushion / back front lie this far inside them (review r2 M1: "
                         "the 3-D cover sat on top of the drawn cushion, +14 mm / +32 mm)"),
    cushion_w=P(0.46, "[M] face-on photo: two thigh-pad lobes (outboard half 0.23)"),
    cushion_in=P(0.185, "[E] inboard half-width of pan + cushion: trimmed from 0.23 so the seat clears the "
                        "nose-tunnel plinth (gear, hard) by 15 over the whole x / z travel; photos: symmetric"),
    notch_wd=PT((0.10, 0.08), "[S] split thigh pads with a front U-notch (POH, IPECO line art); size [M]"),
    back_len=P(0.680, "[E] backrest top along the back line: inboard top corner 0.86-0.90 above the floor seen from "
                      "the cabin (P1046406, camera 0.73 up); a side-on photo would pin it"),
    back_t=PT((0.120, 0.070), "[E] contoured shell + cushion, lumbar / top (IPECO line art)"),
    back_w=PT((0.40, 0.44), "[M] backrest top (P1046406) / lumbar; shoulder taper (IPECO line art)"),
    head_c=P(0.820, "[E] headrest centre along the back line, 50th-pct position (at the head centre)"),
    head_lock=PT((0.760, 0.880), "[E] lowest / highest of the six lock positions [S: POH 7-7-1.1], along the back"),
    head_hwt=PT((0.18, 0.28, 0.10), "[M] headrest h, w (IPECO line art, photos), t [E]; front face 0.035 ahead of "
                                     "the back line"),
    arm_h=P(0.220, "[E] armrest top above the SRP"),
    arm_lw=PT((0.30, 0.055), "[E] armrest length, width; both flip up / in [S]"),
    arm_pivot=P(-0.030, "[E] armrest hinge on the backrest side, this far behind the back line at the hinge height: "
                        "between the back's front (+0.035) and rear (-0.10) faces (IPECO line art: the armrests hinge "
                        "on the back and flip up along its side); rev B had it 0.16 AHEAD of the back line"),
    width=P(0.54, "[M] plan render, incl. the armrests"),
    rail_dy=P(0.120, "[E] two floor tracks per seat at seat CL +/-"),
    base_w=P(0.30, "[E] side-plate spacing: two plates under the pan down to curved feet on the tracks (IPECO art)"),
    base_feet=PT((-0.190, 0.470), "[E] rear / front foot tips of the side plates from the SRP, + = fwd (IPECO art)"),
    life_vest=PT((0.30, 0.22, 0.10), "[S] life-vest box under the pan (POH 7-7-1.1), low at the front between the "
                                      "side plates (IPECO line art); size [E]"),
    finish="cream leather pan, anthracite shell / headrest back, grey sheepskin covers [M: PRO 3001 photos]",
)
PANEL = dict(
    glass_x=P(3.500, "[M] PDU glass 1.09-1.13 m ahead of the divider camera (PRO 3001 face-on photo, 12 mm lens)"),
    mfd_z=P(2.000, "[M] MFD centre: cabin-camera cross-check 2.01 +/- 0.05 (P1046406, camera 0.73 above the floor, "
                   "MFD 3.5 m away); hood from the windshield frame to the lip 0.24-0.26 above it [M]"),
    tilt_deg=P(12.0, "[E] PDU plane, top forward"),
    pdu_wh=PT((0.330, 0.230), "[M] GDU 1470W face 330 x 228 (14-in, 16:10 [S])"),
    pdu_bl=PT((-0.348, 0.0, 0.348), "[M] PDU centres (cockpit key / face-on photo, touching bezels)"),
    pdu_cant=P(10.0, "[M] side PDUs canted toward their pilot (foreshortening 0.97)"),
    lower_dz=P(-0.275, "[M] lower (yoke / switch) panel bottom below the MFD centre"),
    cheek_bl=P(0.710, "[M] panel face 1.42 wide incl. the side cheeks (cockpit key)"),
    standby=PT((-0.565, -0.047, 0.080), "[S] GI 275 standby left of the PFD: BL, dz vs MFD [M], 3.125-in bezel"),
    ecs_bl=P(0.640, "[M] eyeball ECS outlets at the panel ends"),
    stack_hw=P(0.140, "[M] centre stack 0.28 wide at the SDUs"),
    sdu_wh=PT((0.115, 0.190), "[S] 2 x 7-in GDU 770W touch displays, portrait, side by side; bezel [M]"),
    sdu_bl=P(0.065, "[M] SDU centres +/-"),
    sdu_top_dz=P(-0.130, "[M] SDU bezel top 10-20 below the MFD bezel foot (1.885): JTF p.18 elevation on MFD "
                         "2.00 gives 1.873-1.732, camera-matched P1046406 1.868-1.710, P1046408 agrees (rev B: -0.170)"),
    sdu_recline=P(35.0, "[M] SDU face from vertical: a level camera (P1046406) sees 0.158 of the 0.19 bezel, the "
                        "face-on camera (above the stack) ~0.19 -> ~35 deg (rev B: 20 [E])"),
)
GLARESHIELD = dict(
    lip_x=P(3.630, "[M] lip 0.12-0.15 aft of the PDU glass (face-on photo); plan render ~3.70"),
    lip_dz=PT(((0.00, 0.260), (0.20, 0.255), (0.375, 0.240), (0.50, 0.210), (0.60, 0.150), (0.66, 0.075),
               (0.71, -0.020)), "[M] lip arch (|BL|, height above the MFD centre), cockpit key + face-on photo"),
    frame_drop=P(0.020, "[E] hood meets the windshield inner frame this far below the glass edge"),
    afcs_wh=PT((0.286, 0.062), "[M] GFC 700 on the eyebrow, centre 0.18 above the MFD [S: cockpit key item 10]"),
    finish="grey stitched leather top [M: brochure p.10]",
)
YOKE = dict(
    bl=P(0.375, "[M] +/-0.372 (cockpit key): on the seat centreline"),
    hub_dx=P(0.140, "[M] hub face aft of the PDU glass (face-on photo, depth-corrected)"),
    hub_dz=P(-0.155, "[M] hub centre 0.15-0.17 below the MFD centre"),
    hub_whd=PT((0.140, 0.110, 0.060), "[M] white Y hub: width at the grip roots, height; depth [E]"),
    hub_bot_w=P(0.045, "[M] the Y hub narrows to a stem this wide at its bottom (JTF cockpit key item 15)"),
    span=P(0.285, "[M] grips overall, outer edge to outer edge at their bottoms (JTF cockpit key, P1046408 with the "
                  "0.14 hub for scale); PC-24-style yoke [S]"),
    grip=PT((0.140, 0.0155, 10.0), "[M] grip length tip to tip, radius, cant from vertical with the TOPS INBOARD (JTF "
                                   "key: tops +/-0.10, bottoms +/-0.125 from the hub CL; P1046408 ~8 deg); review r2 F2 "
                                   "(P1046408 pair: slim paddles 55 px against the render's 70 px, rising well above "
                                   "the hub): radius 0.020 -> 0.0155, length 0.125 -> 0.140 (the tops 15 mm higher)"),
    grip_dz=P(-0.040, "[M] grip bottoms 0.04 below the hub centre, near the hub bottom (JTF key: grips WL 1.80-1.93 "
                      "on hub 1.79-1.90; P1046408 -0.05..+0.09); tops ~0.04 above the hub top (P1046408)"),
    grip_head=PT((0.036, 0.020), "[M] swollen grip head: over its top 36 mm the grip swells from the grip radius to "
                                 "0.020, the hat switch on top (P1046408 pair: heads ~45 wide on ~31 grips; brochure "
                                 "p.12), review r3 F2"),
    shield=PT(((0.00, 1.00), (0.12, 0.92), (0.50, 0.37), (0.85, 0.05), (1.00, 0.00)),
              "[M] white shield (the hub's front cover): half-width from its top (t = 0) to the stem (t = 1) as the "
              "fraction between hub_bot_w / 2 and hub_whd width / 2 -- a goblet with concave sides, its top corners "
              "at +/- hub width / 2 (P1046408: ~0.52 of the grip span; review r3 F2: rev C ran them out to the grips)"),
    shield_dip=P(0.004, "[M] the shield's top edge dips this much to the centre under the badge (a shallow V)"),
    body_arm=PT((-0.004, 0.005), "[M] black yoke body behind the shield: its lower edge leaves each grip's inner edge "
                                 "this far above the hub centre and runs down-inboard to the shield foot, rimming it "
                                 "by the second value; its top runs from the grip heads into the shield's top corners "
                                 "(P1046408, review r3 F2)"),
    column_r=P(0.022, "[E] horizontal column into the lower panel"),
    travel=PT((-0.090, 0.090), "[E] pitch travel fwd / aft of neutral"),
    roll=P(70.0, "[E] roll travel each way (PC-12 figure not found): the knee check sweeps it.  OPEN, owner decision "
                 "(review r3 C3): at the L6B design seat setting the 95th-pct knees meet the yoke from ~17.5 deg of "
                 "roll (50th ~25, 5th male ~22.5, 5th female ~87.5; L6B detail F / fit_check 19 compute it); options: "
                 "the seat setting / pedal crank the 95th would use, a smaller roll [E], or the grip cant / span"),
)
PEDALS = dict(
    dy=P(0.125, "[M] pedal-pad centres at seat CL +/- (P1046408 face-on: 0.24-0.26 apart, MFD-bezel scale + depth "
                "correction, the grip span checks it); rev B 0.09 [E]"),
    heel_x=P(3.360, "[M] heel point on the floor (plan render pedal gear 3.04-3.31, neutral crank)"),
    face_deg=P(50.0, "[E] pedal face from horizontal"),
    pad_wh=PT((0.125, 0.210), "[M] pad width 0.12-0.14 (P1046408, as dy; rev B 0.08 [E]), length along the face [E]"),
    crank=P(0.050, "[E] fore/aft adjustment +/- (crank between each pair, POH 7-3-4 [S]); - = forward"),
    travel=P(0.080, "[E] rudder travel at the pad each way: full rudder pushes one pedal 0.08 forward and lets the "
                    "other come 0.08 aft (PC-12 figure not found; typical 3-3.5 in)"),
    toe_brake=P(15.0, "[E] toe brake: the pedal face tips this far forward about the heel under braking [S: toe "
                      "brakes, POH 7-4-7]"),
    pivot=PT((3.080, 0.040), "[E] floor-hinge x, height; toe-brake master cylinders above [S: POH 7-4-7]"),
)
PEDESTAL = dict(
    x=PT((3.730, 4.150), "[M] control quadrant fwd / aft end (plan render 3.73-4.15)"),
    hw=P(0.110, "[M] 0.22 wide (cockpit key, render)"),
    top_h=P(0.300, "[M] aft face ~0.30-0.32 tall above the floor with FUEL / ACS T-handles (P1046406)"),
    stack=PT(((3.525, -0.118), (3.530, -0.130), (3.639, -0.286), (3.719, -0.400)),
             "[M] centre stack side profile at BL 0 (x, dz vs the MFD): MFD bezel foot, SDU top, SDU bottom (the "
             "0.19 face reclined 35 deg), pad; the face runs on at 35 deg to the quadrant (P1046406 / P1046408)"),
    pcl=PT((3.950, -0.050, 0.470), "[M] PCL knob x, BL, height above floor (0.45-0.5)"),
    pcl_grip=PT((0.036, 0.080, 0.072), "[M] PCL grip: a satin pewter paddle, fore-aft, width, height, its top at the "
                                       "PCL height, tipped forward (throttle photo, P1046408-10; review r3 F3: rev C "
                                       "built a 60 x 88 x 48 puck)"),
    flap=PT((3.930, 0.050, 0.420), "[S] flap lever right of the PCL (POH 7-3-6); position [E]"),
    ccd=PT((4.090, 0.000, 0.340), "[S] cursor control device palm grip at the aft end (cockpit key 27)"),
    plinth_pad=PT((0.020, 0.025), "[H] carpeted plinth over gear.NOSE_TUNNEL: wall, top gap (fit_check 11)"),
)
SIDE_CONSOLE = dict(
    x=PT((3.640, 4.420), "[M] armrest console along each sidewall, panel cheek to the seat back (render, photos)"),
    top_h=P(0.500, "[E] above the floor (cup holders, USB, 1-kg pocket placard [M])"),
    inner_bl=P(0.680, "[E] inboard face"),
    cb_panel=PT((3.620, 3.950, 0.480, 0.780), "[M] circuit-breaker panels on the sidewall lining ABOVE the console "
                                              "(rows 1-4, row 4 at the cup holders; P1046409 / P1046410): x0, x1, h0, "
                                              "h1 above the floor, estimated from the photos"),
)
OVERHEAD = dict(
    x=PT((3.950, 4.170), "[M] overhead panel 0.50 x 0.21 on the ceiling at the windshield top (P1046406)"),
    w=P(0.500, "[M]"),
    depth=P(0.035, "[E] below the headliner"),
    autoland=PT((4.230, 0.170, 0.070), "[S] SAFETY AUTOLAND button in a recessed cup aft of the panel; x, BL, size [M]"),
)

# ---------------------------------------------------------------------------------------------------- cabin seats
EXEC_SEAT = dict(
    type="PRO executive seat: leather, swivel, fwd/aft/inboard travel, recline to lay-flat where space allows, "
         "sliding headrest and armrest, 3-point restraint [S: POH 7-7-1.2, Skies 'PC-24-style seats']",
    bl=P(0.400, "[M] plan render seat CL +/-0.40 (fully outboard for TTL [S placard]: outer arm at the ledge)"),
    length=P(0.705, "[M] plan render, upright: back rear to cushion front"),
    width=P(0.500, "[M] plan render footprint: ONE (inboard) armrest + cushion + outboard shell side"),
    front_occ=P(0.235, "[M/S] cushion front to POH occupant arm (render footprints vs POH, <= 8 mm)"),
    srp_front=P(0.415, "[E] cushion front to SRP"),
    srp_h=P(0.360, "[E] SRP above the floor"),
    cushion_top=P(0.420, "[M] section render, front edge"),
    cushion_w=P(0.420, "[M]"),
    cushion_t=P(0.120, "[E]"),
    pan_deg=P(6.0, "[E]"),
    arm_top=P(0.435, "[M] armrest top above the floor"),
    arm_w=P(0.060, "[M] ONE armrest, on the aisle side (sliding [S]); no outboard arm: the 0.61 ledge is the outboard "
                   "armrest (Pilatus plan + front renders, P1046402 / 05 / 06; legacy POH 7-28 'sidewall armrests')"),
    arm_h0=P(0.200, "[M] the arm is a deep side panel from about the base top up to arm_top (P1046404 / 05)"),
    arm_ctrl=PT((0.055, 0.075), "[M] brushed seat control on the arm's forward end: length along the arm, height"),
    arm_u=PT((-0.10, 0.36), "[M] armrest from / to along the seat, from the SRP (+ = forward; plan render)"),
    back_top=P(0.970, "[M] seat-back top above the floor"),
    back_w=PT((0.42, 0.46), "[M] shoulder / lumbar"),
    back_t=P(0.110, "[E]"),
    back_deg=P(15.0, "[E] upright (TTL) back angle"),
    head_top=P(1.110, "[M] headrest top above the floor (on two posts), lowest position"),
    head_slide=P(0.080, "[E] sliding headrest travel up [S: POH 7-7-1.2]; drawn raised for the 95th-pct manikin"),
    head_wh=PT((0.26, 0.19), "[M]"),
    base_wh=PT((0.36, 0.17), "[M] anthracite base shroud, life-vest pictogram"),
    base_u=P(0.380, "[E] base shroud front, from the SRP (+ = forward): under the front of the cushion (P1046405)"),
    legrest=PT((0.360, 0.160, 0.020, 0.070),
               "[M] FORWARD-facing seats only (review r3 F1; P1046402 / 03 / 04 / 05: a light leather block hanging "
               "under the cushion front, about the base-shroud width, its face about as tall as the shroud face below "
               "it, its lower edge over the shroud's top edge; the aft-facing PAX 1 / 2 have none, P1046406): width, "
               "face height down from the cushion underside, face set back from the cushion front, depth [E]; the "
               "cushion's leather drape stops at the legrest top"),
    travel=PT((0.1016, 0.0508, 0.0914), "[S] POH 7-7-1.2: fwd/aft 4 in (fwd-facing), 2 in (aft-facing), inboard 3.6 in"),
    recline_deg=P(45.0, "[E] recline for the drawing envelope (lay-flat where space allows [S])"),
)
COMMUTER_SEAT = dict(
    length=P(0.620, "[E] commuter seat, fwd-facing"),
    width=P(0.460, "[E]"),
    front_occ=P(0.200, "[E]"),
    note="STD-9S / EX-6S-STD-2S only [S: POH 6-8]; not drawn on L6",
)
# seat layouts (NGX POH Report 02406 sec. 6-8; PRO seat maps match EX-6S-2).  occ = POH occupant arm [S];
# 'front' overrides the cushion-front station when a render places the seat differently [M].
SEAT_LAYOUTS = {
    "EX-6S-2": dict(
        title="6 EXECUTIVE SEATS: CLUB 4 + STAGGERED PAIR, FWD RH LAVATORY (PRO STANDARD)",
        seats=(
            dict(id="PAX 1", side=-1, facing=-1, occ=P(5.899, "[S] POH occupant arm"),
                 front=P(6.242, "[M] plan render 5.532-6.242: 0.108 aft of the POH-mirror footprint")),
            dict(id="PAX 2", side=+1, facing=-1, occ=P(5.899, "[S] POH"), front=P(6.242, "[M] plan render")),
            dict(id="PAX 3", side=-1, facing=+1, occ=P(7.011, "[S] POH (render within 5 mm)")),
            dict(id="PAX 4", side=+1, facing=+1, occ=P(7.011, "[S] POH (render within 5 mm)")),
            dict(id="PAX 5", side=-1, facing=+1, occ=P(8.180, "[S] POH (the marketing render has it 0.18 fwd)")),
            dict(id="PAX 6", side=+1, facing=+1, occ=P(8.485, "[S] POH: 0.305 aft of PAX 5 (render within 8 mm)")),
        ),
        lavatory=True, tables=("club_p", "club_s"),
    ),
    "EX-8S": dict(
        title="8 EXECUTIVE SEATS (NO LAVATORY SHOWN)",
        seats=tuple(dict(id=f"PAX {i}", side=s, facing=f, occ=P(o, "[S] POH EX-8S occupant arm"))
                    for i, s, f, o in ((1, -1, -1, 5.899), (2, 1, -1, 5.899), (3, -1, 1, 7.011), (4, 1, 1, 7.011),
                                       (5, -1, 1, 7.824), (6, 1, 1, 7.824), (7, -1, 1, 8.637), (8, 1, 1, 8.637))),
        lavatory=True, tables=("club_p", "club_s"),
    ),
    "STD-9S": dict(
        title="9 COMMUTER SEATS (NO LAVATORY)",
        seats=tuple(dict(id=f"PAX {i}", side=s, facing=1, occ=P(o, "[S] POH STD-9S occupant arm"), kind="commuter")
                    for i, s, o in ((1, -1, 5.343), (2, 1, 5.267), (3, -1, 6.181), (4, 1, 6.105), (5, -1, 7.019),
                                    (6, 1, 6.943), (7, -1, 7.857), (8, 1, 7.781), (9, 1, 8.619))),
        lavatory=False, tables=(),
    ),
}
DEFAULT_LAYOUT = "EX-6S-2"

# ---------------------------------------------------------------------------------------------------- cabin furniture
LEDGES = dict(
    top_h=P(0.610, "[M] section render: ledge top above the floor (cup holders, USB, table slot)"),
    inner_bl=P(0.655, "[M] plan / section render inboard face"),
    fascia=P(0.060, "[E] top fascia depth; kick panel below curves to the floor edge"),
    runs=PT(((-1, 5.450, 9.250), (+1, 5.384, 9.250)), "[M] render: cabinets to the FR34 partition (side, x0, x1)"),
    door_segment=PT((-1, 7.575, 8.905), "[M] port segment carried by the cargo-door lining (render joints 7.62/8.99): "
                                        "inside the clear opening (fuselage_parts.CARGO 7.565-8.915) by 10 mm each end "
                                        "so it swings out through it (review r1 M2: rev C 7.540-8.940 ran 25 mm past "
                                        "the opening, through the jambs and the skin)"),
    door_foot=P(0.075, "[E] the door segment's kick-panel foot above the carpet: clear of the sill jamb (its inboard "
                       "edge 0.04 above the floor) over the whole door swing (fit_check 21; rev C 0.004)"),
    cupholder_dx=P(0.20, "[E] cup-holder pair ahead of each seat back"),
)
TABLES = {
    "club_p": dict(side=-1, x=PT((6.262, 6.762), "[E] between the club seats (0.50 deployed, brochure p.17)"),
                   bl_in=P(0.080, "[E] two-leaf top 0.575 wide from the ledge"),
                   leaf=P(0.290, "[M] the outboard leaf slides out of the ledge first (P1046404 / 05 show it alone); "
                                 "the inboard leaf unfolds over the aisle (brochure p.18)"),
                   top_h=P(0.590, "[M] slides out from under the ledge cap (0.61) and unfolds: top just below "
                                  "the ledge top (brochure p.18, P1046405, P1046406)"),
                   t=P(0.025, "[E]")),
    "club_s": dict(side=+1, x=PT((6.262, 6.762), "[E] as club_p; stowed for TTL -- deployed it blocks the exit"),
                   bl_in=P(0.080, "[E]"), leaf=P(0.290, "[M] as club_p"), top_h=P(0.590, "[M] as club_p"), t=P(0.025, "[E]")),
    "aft_s": dict(side=+1, x=PT((7.700, 8.200), "[E] optional table for PAX 6 (PRO JTF 6-seat plan [M])"),
                  bl_in=P(0.080, "[E]"), top_h=P(0.590, "[M] as club_p"), t=P(0.025, "[E]"), optional=True),
}
LAVATORY = dict(
    x=PT((4.571, 5.195), "[S] fwd wall = the RH divider (POH 7-28); aft wall [M] plan render 5.228, moved 33 mm fwd "
                         "(Stage 3): 14 mm clear of the forward edge of RH cabin window 1 (STA 5.359 - 0.150), which "
                         "the render wall crossed by 19 mm (fit_check 20)"),
    inboard_bl=P(0.260, "[M] plan render +0.25-0.28: in line with the divider opening"),
    bowl_x=P(4.831, "[S] toilet CG arm (POH): bowl centre"),
    cabinet=PT((4.600, 5.165, 0.365, 0.350), "[M] gloss-veneer cabinet wall to wall (P1046411): x0, x1 [M] (x1 = aft "
                                             "wall - 0.030); depth "
                                             "[E] 0.35-0.38 (carpet between its foot and the door jambs); height [M] "
                                             "0.32-0.36, the 0.33 seat ring as scale (P1046411, lav teaser; r2 0.45)"),
    seat_ring=PT((0.330, 0.280), "[M] toilet seat ring under the hinged lid: along x, across (P1046411)"),
    shelf_x=P(5.040, "[M] aft module from here to the aft wall: padded seat / shelf over a drawer (P1046411)"),
    niche=PT((0.440, 0.640), "[M] lit niche in the outboard wall, starting just above the padded shelf: bottom, top "
                             "above the floor (P1046411 + lav teaser, ring as scale; r2: 0.58-0.82 [E])"),
    tp_holder=PT((0.330, 0.600), "[M] toilet-paper holder on the aft wall (P1046411): BL, height above the floor [E]"),
    door=PT((4.650, 5.150), "[M] hard bi-fold doors on the inboard face, into the entry vestibule (evidence, E)"),
    leaf=P(0.125, "[E] two bi-fold doors, each 2 panels x 125 hinged at a jamb: fold out <= 125 into the vestibule"),
    seat_back=P(0.080, "[M] toilet seat back (lid hinge) inboard of the outboard cabinet edge (P1046411)"),
    finish="veneer outside, white inside, lowered lit ceiling [M: PRO photos]",
)
CABINETS = {
    "rh": dict(side=+1, x=PT((5.195, 5.384), "[M] plan render (POH arm 5.366 [S]); fwd face against the lav aft wall "
                                              "[S: POH 'fits against the toilet compartment rear wall']"),
               bl_in=P(0.300, "[M]"), h=P(0.720, "[E] upper + lower drawer [S placard]; top 16 mm under the "
                                                 "cabin-window sill (0.736 above the floor: the RH cabinet stands "
                                                 "under window 5.359; rev C 0.75 crossed it, fit_check 20)")),
    "lh": dict(side=-1, x=PT((5.300, 5.450), "[M] render 5.244-5.389 moved aft to clear the airstair opening "
                                              "(5.275) + jamb; centre 5.375 = POH arm 5.387 [S]"),
               bl_in=P(0.240, "[M]"), h=P(0.720, "[E] upper + lower drawer [S placard]; as RH (a matched pair)")),
}
BAGGAGE = dict(
    partition_x=P(9.250, "[S] FR34: POH floor length 4.68 from the divider; render 9.244"),
    aft_x=P(9.731, "[S] divider + 5.16 cabin length (FR36 9.750, render 9.744)"),
    bar_h=P(1.050, "[M] section render: curtain rod / net bar above the floor"),
    kind="veneer arch header + full-width pleated curtain (PRO: P1046402 / P1046405, brochure p.22, EXEX6 cutaway, "
         "tech-data front render) [M]; luggage net = the non-PRO standard fit / option [S]",
    header_t=P(0.030, "[E] veneer header: arch from the curtain rod to the headliner, depth along x"),
    curtain_t=P(0.060, "[E] pleated curtain depth (pleats)"),
    net_x_opt=P(8.736, "[S] optional extendable net at FR32 (POH: attachments FR32-FR34)"),
    tiedowns=PT((9.47, 9.60), "[M] floor tie-down slots (render)"),
)

# ---------------------------------------------------------------------------------------------------- criteria
# 95th-percentile male (ANSUR II 2012, US Army male survey; approximate, rounded to 5 mm) -- the design manikin
# drawn on L6.  Joint-centre link lengths are derived [E].  Smaller occupants are the same manikin scaled uniformly
# (PCT) [E]: female proportions are not modelled.
MANIKIN = dict(
    name="95TH-PCT MALE (ANSUR II)",
    stature=P(1.870, "[S] ANSUR II male 95th pct (approx.)"),
    sit_h=P(0.975, "[S] sitting height"),
    eye_sit=P(0.850, "[S] eye height, sitting"),
    acromion_sit=P(0.660, "[S] acromial height, sitting"),
    elbow_rest=P(0.290, "[S] elbow rest height"),
    thigh_clear=P(0.195, "[S] thigh clearance"),
    buttock_knee=P(0.665, "[S] buttock-knee length"),
    knee_h=P(0.605, "[S] knee height, sitting"),
    hip_br=P(0.415, "[S] hip breadth, sitting"),
    bideltoid=P(0.560, "[S] bideltoid (shoulder) breadth"),
    reach=P(0.870, "[S] thumbtip reach (from a back wall)"),
    head_lwh=PT((0.210, 0.165, 0.245), "[S] head length, breadth; head height chin-vertex [E]"),
    foot_l=P(0.290, "[S] foot length"),
    foot_w=P(0.110, "[S] foot breadth (approx.)"),
    thigh=P(0.465, "[E] hip - knee joint centres"),
    shank=P(0.470, "[E] knee - ankle joint centres"),
    upper_arm=P(0.360, "[E] shoulder - elbow"),
    forearm=P(0.360, "[E] elbow - grip centre"),
    h_from_srp=PT((0.125, 0.095), "[E] H-point from the SRP along / normal to the pan (SAE J826-type)"),
    eye_from_shoulder=P(0.100, "[E] eye ahead of the shoulder joint"),
    knee_y=P(0.105, "[E] cabin: knee / shank centre from the seat CL, feet flat under the knees (crew: crew_leg_y)"),
    hip_y=P(0.090, "[E] hip joint centre from the body midline (95th; hip breadth 0.415 less the soft tissue)"),
    knee_splay=P(0.015, "[E] crew: knee this far outboard of the hip-to-pedal line (relaxed; rev B knee 0.105 over "
                        "feet at 0.090)"),
    shoulder_y=P(0.200, "[E] shoulder joint from the body midline (biacromial ~0.43 / 2, less 15)"),
    reach_sh=P(0.740, "[E] shoulder joint to thumbtip, arm straight: thumbtip reach 0.870 less ~0.13 from the back "
                      "wall to the shoulder joint"),
    fingertip=P(0.070, "[E] thumbtip (grasp) to index fingertip (touch): push-buttons and the G3000 PRIME touch "
                       "screens are reached ~0.07 further than a grasped lever"),
    lean=P(0.200, "[E] shoulder travel forward, leaning with the inertia reel unlocked"),
)
PCT = dict(
    p95m=P(1.00, "[S] 95th-pct male: the MANIKIN table (seated eye 0.85)"),
    p50m=P(0.94, "[E] 50th-pct male, uniform scale (ANSUR II seated eye ~0.80)"),
    p5m=P(0.88, "[E] 5th-pct male (seated eye ~0.75)"),
    p5f=P(0.82, "[E] 5th-pct female (seated eye ~0.70)"),
)
PCT_NAME = dict(p95m="95TH MALE", p50m="50TH MALE", p5m="5TH MALE", p5f="5TH FEMALE")
P50_SCALE = PCT["p50m"]
CRITERIA = dict(
    knee_clear=P(0.025, "[E] knees / thighs to the yoke over its pitch travel (review R1: 25-30)"),
    knee_angle=P(120.0, "[E] knee angle at neutral pedals each occupant sets with the seat notch and pedal crank"),
    knee_ext=P(165.0, "[E] extended leg at full forward rudder: knee angle <= 160-165 deg (reach limit)"),
    plinth_clear=P(0.015, "[E] seat pan / cushion to the tunnel plinth over the whole seat travel"),
    arm_pedestal=P(0.010, "[E] crew armrests (down or stowed) to the pedestal and its levers over the whole seat "
                          "travel (review r3 C2)"),
    furniture_clear=P(0.010, "[E] reclined seat back to furniture / the next occupant's knees"),
)


# =====================================================================================================================
# derived geometry (the drawing and, in Stage 3, the 3-D builder read these; nothing below adds new numbers)
# =====================================================================================================================
def crew_srp(side=-1, dx=0.0, dz=0.0):
    """Crew seat reference point (x, y, z): centre notch plus dx (fore/aft travel) and dz (vertical adjustment)."""
    c = CREW_SEAT
    return np.array([c["srp_x"] + dx, side * c["bl"], FLOOR["fd_wl"] + c["srp_h"] + dz])


def design_eye_offset():
    """(fwd, up) of the design eye from the neutral SRP: the seated eye of the 50th-pct male (seated_pose at
    P50_SCALE) on the upright seat.  The vertical travel is symmetric about the neutral height, so the 95th-pct male
    (seat full down) and the 5th-pct male (full up) reach the same eye point (crew_checks)."""
    c = CREW_SEAT
    p = seated_pose((0.0, 0.0), 1, c["back_deg"], c["pan_deg"], floor=-float(c["srp_h"]), scale=P50_SCALE)
    return float(-p["eye"][0]), float(p["eye"][1])


def design_eye(side=-1):
    """Design eye point (x, y, z) of the left (side=-1) or right seat: the neutral SRP plus design_eye_offset()."""
    f, u = design_eye_offset()
    return crew_srp(side) + np.array([-f, 0.0, u])


def panel_x(z):
    """Station of the PDU / lower-panel face plane at water line z (tilted, top forward)."""
    return PANEL["glass_x"] - (np.asarray(z, float) - PANEL["mfd_z"]) * math.tan(math.radians(PANEL["tilt_deg"]))


def mfd_centre():
    return np.array([PANEL["glass_x"], 0.0, PANEL["mfd_z"]])


def pdu_centre(side=-1):
    """Centre of the pilot's (side=-1) or co-pilot's PDU glass."""
    return np.array([PANEL["glass_x"], side * PANEL["pdu_bl"][2], PANEL["mfd_z"]])


def sdu_height():
    """Projected (vertical) height of the reclined SDU bezel: h cos(recline), as a view looking forward sees it."""
    return float(PANEL["sdu_wh"][1] * math.cos(math.radians(PANEL["sdu_recline"])))


def sdu_centre(side=-1):
    """Centre (x, y, z) of the left (side=-1) or right 7-in SDU on the centre stack."""
    pn = PANEL
    z = pn["mfd_z"] + pn["sdu_top_dz"] - 0.5 * sdu_height()
    st = np.array([(p[0], pn["mfd_z"] + p[1]) for p in PEDESTAL["stack"]])
    x = float(np.interp(z, st[::-1, 1], st[::-1, 0]))
    return np.array([x, side * pn["sdu_bl"], z])


def glareshield_lip(bl):
    """(x, WL) of the glareshield lip at butt line bl."""
    t = np.array(GLARESHIELD["lip_dz"])
    return GLARESHIELD["lip_x"], PANEL["mfd_z"] + float(np.interp(abs(bl), t[:, 0], t[:, 1]))


def ws_lower_edge(bl, x0=3.15, x1=3.75, n=6001):
    """(x, WL) of the windshield glass lower edge at butt line bl: the OML meets the sill plane (cockpit_glazing)."""
    from model import cockpit_glazing as CG
    xs = np.linspace(x0, x1, n)
    zs = F.z_at(xs, np.full_like(xs, abs(bl)))
    k = int(np.argmin(np.abs(zs - CG.z_ws_sill(xs))))
    return float(xs[k]), float(zs[k])


def glareshield_profile(bl):
    """Side profile of the hood at butt line bl: [(x, WL)] from the windshield inner frame aft to the lip."""
    xw, zw = ws_lower_edge(bl)
    xl, zl = glareshield_lip(bl)
    return np.array([[xw + 0.01, zw - GLARESHIELD["frame_drop"]], [xl, zl], [xl + 0.005, zl - 0.030]])


def yoke_hub(side=-1):
    return np.array([PANEL["glass_x"] + YOKE["hub_dx"], side * YOKE["bl"], PANEL["mfd_z"] + YOKE["hub_dz"]])


def pedal_points(dx=0.0):
    """Pedal foot points at neutral (+dx crank): heel on the floor, ball and toe along the pedal face (x, WL)."""
    a = math.radians(PEDALS["face_deg"])
    d = np.array([-math.cos(a), math.sin(a)])                         # up the face, forward
    heel = np.array([PEDALS["heel_x"] + dx, FLOOR["fd_wl"]])
    return dict(heel=heel, ball=heel + 0.215 * d, toe=heel + PEDALS["pad_wh"][1] * d + 0.06 * d, dir=d)


def pedestal_plinth():
    """Carpeted plinth over the nose-wheel tunnel hump: (x0, x1, half-width, top WL) from gear.NOSE_TUNNEL."""
    from model.gear import NOSE_TUNNEL as TU
    w, g = PEDESTAL["plinth_pad"]
    return TU["x0"] - w, TU["x1"] + w, TU["hy"] + w, TU["z_top"] + g


def pedestal_profile():
    """Side outline (x, WL) of centre stack + control quadrant at BL 0, closed down to the floor."""
    x0, x1 = PEDESTAL["x"]
    zt = FLOOR["fd_wl"] + PEDESTAL["top_h"]
    st = [(p[0], PANEL["mfd_z"] + p[1]) for p in PEDESTAL["stack"]]
    return np.array(st + [(x0, zt), (x1, zt), (x1, FLOOR["fd_wl"]), (st[-1][0], FLOOR["fd_wl"])])


def exec_seat(s, seat=None):
    """Stations of one cabin seat record s (from SEAT_LAYOUTS): front / rear (along x), occupant arm, SRP (x, y, z),
    facing (+1 forward-facing), side, BL."""
    seat = seat or (COMMUTER_SEAT if s.get("kind") == "commuter" else EXEC_SEAT)
    f = s["facing"]
    occ = float(s["occ"])
    front = float(s["front"]) if "front" in s else occ - f * seat["front_occ"]
    rear = front + f * seat["length"]
    srp_front = seat.get("srp_front", 0.40)
    srp = np.array([front + f * srp_front, s["side"] * EXEC_SEAT["bl"], FLOOR["wl"] + EXEC_SEAT["srp_h"]])
    return dict(id=s["id"], side=s["side"], facing=f, occ=occ, front=front, rear=rear, srp=srp,
                bl=s["side"] * EXEC_SEAT["bl"], x0=min(front, rear), x1=max(front, rear),
                occ_render=front + f * seat["front_occ"])


def seat_map(layout=DEFAULT_LAYOUT):
    """[(record dict)] crew + cabin seats of a layout, with the stations of exec_seat()."""
    out = []
    for side, name in ((-1, "PILOT"), (+1, "CO-PILOT")):
        srp = crew_srp(side)
        c = CREW_SEAT
        out.append(dict(id=name, side=side, facing=1, occ=4.071, front=srp[0] - c["pan_depth"], srp=srp,
                        rear=srp[0] + back_rear_offset(), bl=side * c["bl"], x0=srp[0] - c["pan_depth"],
                        x1=srp[0] + back_rear_offset(), crew=True))
    for s in SEAT_LAYOUTS[layout]["seats"]:
        out.append(exec_seat(s))
    return out


def windows_by_side():
    """{side: [(id, cx)]} of every cabin window, fixed and in doors (fuselage_parts.openings_table)."""
    from model.fuselage_parts import openings_table
    out = {-1: [], 1: []}
    for r in openings_table():
        if r["kind"] == "window":
            out[r["side"]].append((r["id"], r["cx"]))
    return out


# ---------------------------------------------------------------------------------------------------- seat outlines
def _arc(c, r, a0, a1, n=8):
    a = np.radians(np.linspace(a0, a1, n))
    return np.c_[c[0] + r * np.cos(a), c[1] + r * np.sin(a)]


def _hull(P):
    """Convex hull (monotone chain) of 2-D points, counter-clockwise."""
    P = sorted(map(tuple, np.asarray(P, float)))
    if len(P) < 3:
        return np.array(P)

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in P:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(P):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return np.array(lo[:-1] + up[:-1])


def _capsule(a, b, r, n=16):
    t = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
    c = np.c_[np.cos(t), np.sin(t)] * r
    return _hull(np.vstack([np.asarray(a, float) + c, np.asarray(b, float) + c]))


def _offset_line(P, d):
    """Open 2-D polyline P moved by d along its left-hand normals (d < 0: to the right), mitred at the vertices."""
    P = np.asarray(P, float)
    T = np.diff(P, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    Ns = np.c_[-T[:, 1], T[:, 0]]                                       # left normal per segment
    Nv = np.vstack([Ns[:1], Ns[:-1] + Ns[1:], Ns[-1:]])
    Nv /= np.linalg.norm(Nv, axis=1, keepdims=True)
    cosh = np.r_[1.0, np.einsum("ij,ij->i", Nv[1:-1], Ns[1:]), 1.0]
    return P + d * Nv / np.maximum(cosh, 0.3)[:, None]


def _rot(P, c, deg):
    """Rotate the points P counter-clockwise by deg about c (2-D)."""
    a = math.radians(deg)
    R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    return (np.asarray(P, float) - c) @ R.T + c


def crew_seat_profile(head_c=None, recline=0.0, arm_up=False):
    """Side outline pieces of the crew seat in seat-local coordinates (u forward, v up, origin = SRP): {name: (N, 2)}
    plus 'stalks' (list of polylines).  IPECO 3A318-type (line art): split cushion on a pan, a contoured back shell
    tapering from the lumbar to rounded shoulders, a headrest on two stalks, armrests hinged on the back sides (arm_up:
    flipped up along the back), a base of two side plates with curved feet on the tracks, the life-vest box low at the
    front between the plates.  recline: extra back angle (deg) about the SRP; head_c: headrest lock position."""
    c = CREW_SEAT
    hc = c["head_c"] if head_c is None else head_c
    p = math.radians(c["pan_deg"])
    b = math.radians(c["back_deg"] + recline)
    dp, npn = np.array([math.cos(p), math.sin(p)]), np.array([-math.sin(p), math.cos(p)])
    db, nb = np.array([-math.sin(b), math.cos(b)]), np.array([math.cos(b), math.sin(b)])
    out = {}
    t0 = 0.025
    t1 = c["cushion_t"] - t0
    D = c["pan_depth"]
    out["cushion"] = np.array([-0.03 * dp + t0 * npn, (D - 0.04) * dp + t0 * npn, D * dp - 0.01 * npn,
                               (D - 0.03) * dp - t1 * npn, -0.05 * dp - t1 * npn])
    out["pan"] = np.array([-0.10 * dp - t1 * npn, 0.44 * dp - t1 * npn, 0.44 * dp - (t1 + 0.035) * npn,
                           -0.10 * dp - (t1 + 0.035) * npn])
    # back: front face 0.02 ahead of the back line (lumbar bulge), rear face tapering lumbar -> top, rounded top
    L = c["back_len"]
    tl, tt = c["back_t"]
    ss = np.linspace(0.03, L - 0.035, 12)
    tk = np.interp(ss, [0.0, 0.30, L], [tl, tl, tt])
    bulge = 0.015 * np.exp(-((ss - 0.22) / 0.10) ** 2)
    front = np.array([s * db + (0.02 + g) * nb for s, g in zip(ss, bulge)])
    rear = np.array([s * db - (t - 0.02) * nb for s, t in zip(ss, tk)])
    r_top = 0.5 * (tt - 0.005)
    ctop = (L - r_top) * db + (0.02 - r_top) * nb
    top = np.array([ctop + r_top * (math.cos(math.radians(a)) * nb + math.sin(math.radians(a)) * db)
                    for a in np.linspace(0.0, 180.0, 9)])
    out["back"] = np.vstack([[0.0 * db + 0.02 * nb], front, top, rear[::-1], [0.0 * db - (tl - 0.02) * nb]])
    # sheepskin covers inside the outline (sheepskin_t): the band under the cushion top + front slope and behind the
    # back's front face; the leather cushion / back front are the bands' inner edges (review r2 M1)
    sk = c["sheepskin_t"]
    seat_top = out["cushion"][:3]
    out["fleece_seat"] = np.vstack([seat_top, _offset_line(seat_top, -sk)[::-1]])
    out["fleece_back"] = np.vstack([front, _offset_line(front, sk)[::-1]])
    # headrest on two stalks
    hh, hw, ht = c["head_hwt"]
    s0, s1 = hc - 0.5 * hh, hc + 0.5 * hh
    rr = 0.03
    hd = []
    for (sa, ka), (a0, a1) in (((s0 + rr, 0.035 - rr), (-90, 0)), ((s1 - rr, 0.035 - rr), (0, 90)),
                               ((s1 - rr, -(ht - 0.035) + rr), (90, 180)), ((s0 + rr, -(ht - 0.035) + rr), (180, 270))):
        cc = sa * db + ka * nb
        for a in np.linspace(a0, a1, 5):
            aa = math.radians(a)
            hd.append(cc + rr * (math.cos(aa) * nb + math.sin(aa) * db))
    out["head"] = np.array(hd)
    stalks = []
    if s0 > L - 0.03:
        for k in (-0.025, -0.045):
            stalks.append(np.array([(L - 0.04) * db + k * nb, (s0 + 0.01) * db + k * nb]))
    # armrest: hinged on the back side at its rear end, the hinge inside the back's thickness (arm_pivot behind the
    # back line at the hinge height); down = level forward, up = rotated about the hinge to lie along the back's side
    ah = c["arm_h"]
    al, aw = c["arm_lw"]
    bb = math.radians(c["back_deg"])
    piv = np.array([-(ah - 0.0225) * math.tan(bb) + c["arm_pivot"], ah - 0.0225])
    piv = _rot(piv[None, :], np.zeros(2), recline)[0] if recline else piv
    arm = np.vstack([_arc((piv[0] + al - 0.02, piv[1]), 0.0225, -90, 90, 7),
                     _arc((piv[0], piv[1]), 0.0225, 90, 270, 7)])
    if arm_up:
        arm = _rot(arm, piv, 90.0 + c["back_deg"] + recline)
    out["arm"] = arm
    out["arm_pivot"] = piv
    return out, stalks


def crew_base_profile(vf):
    """Crew seat base in seat-local coordinates (u fwd, v up, origin SRP): the side plate (with curved feet on the
    track) and the life-vest box; vf = the floor's v (negative)."""
    c = CREW_SEAT
    p = math.radians(c["pan_deg"])
    t1 = c["cushion_t"] - 0.025
    zb = lambda u: u * math.tan(p) - (t1 + 0.035) / math.cos(p)          # noqa: E731 -- pan underside
    web = zb(0.14) - 0.10
    rf = 0.035
    ur, uf = c["base_feet"]
    plate = np.vstack([[(ur + 0.07, zb(ur + 0.07)), (uf - 0.07, zb(uf - 0.07))],
                       [(uf, vf + rf + 0.01)], _arc((uf - rf, vf + rf), rf, 0, -90, 6)[1:],
                       [(uf - 0.14, vf), (uf - 0.17, vf + 0.02), (uf - 0.20, web)],
                       [(ur + 0.20, web), (ur + 0.12, vf + 0.02), (ur + 0.09, vf)],
                       _arc((ur + rf, vf + rf), rf, 270, 180, 6)[1:], [(ur, vf + rf + 0.01)]])
    lv = c["life_vest"]
    u1 = c["pan_depth"] - 0.08
    vest = np.array([(u1 - lv[0], vf + 0.035), (u1, vf + 0.035), (u1, vf + 0.035 + lv[2]),
                     (u1 - lv[0], vf + 0.035 + lv[2])])
    th = SEAT_TRACKS["crew_h"]
    # the tracks are fixed (drawn at the neutral notch): they run 10 mm past the front foot tip and 15 mm past the rear
    # one with the seat at either end of its travel_x (rev C: +0.05 / -0.11 at neutral, the front feet overhung the
    # track end by 20 mm at full forward travel -- Stage 3 fit_check 18; review r2 M2: 40 mm past the rear foot put the
    # track end 14-17 mm into the foot of the stowed divider curtain; 15 mm leaves it 11 mm clear, crew_checks
    # 'curtain_track')
    r0, r1 = ur - c["travel_x"] - 0.015, uf + c["travel_x"] + 0.01
    rail = np.array([(r0, vf), (r1, vf), (r1, vf + th), (r0, vf + th)])
    return dict(plate=plate, vest=vest, rail=rail)


def back_rear_offset(head_c=None, recline=0.0):
    """Crew seat: horizontal distance from the SRP aft to the rearmost point of the back / headrest (the headrest at
    lock position head_c, default the 50th-pct position; back reclined by `recline` deg about the SRP)."""
    pcs, _ = crew_seat_profile(head_c, recline)
    return float(max(-pcs["back"][:, 0].min(), -pcs["head"][:, 0].min()))


def headrest_lock(p):
    """Headrest lock position (along the back line) for a crew pose: the one of the six nearest the head centre."""
    c = CREW_SEAT
    b = math.radians(c["back_deg"])
    s = float(np.dot(np.asarray(p["head_c"]) - np.asarray(p["srp"]), [math.sin(b), math.cos(b)]))
    pos = np.linspace(c["head_lock"][0], c["head_lock"][1], 6)
    return float(pos[int(np.argmin(np.abs(pos - s)))])


def exec_under_profile(facing=1):
    """Under-cushion pieces of the executive seat in seat-local side view (u forward from the SRP, v above the floor):
    {'skirt': the anthracite skirt between the base shroud top and the cushion, 'legrest': the leather legrest block
    (forward-facing seats only, EXEC_SEAT legrest; None for facing -1)}.  With a legrest the skirt stops behind it.
    The block's face runs down over the shroud's top edge as a lip in front of the shroud face (P1046404 / 05)."""
    e = EXEC_SEAT
    sf, bh, bu = e["srp_front"], e["base_wh"][1], e["base_u"]
    pt = e["cushion_top"] - e["cushion_t"]
    out = dict(skirt=np.array([(-0.08, bh), (sf - 0.04, bh), (sf - 0.02, pt), (-0.06, pt)]), legrest=None)
    if facing > 0:
        lw, lh, lset, ld = e["legrest"]
        uf, vt = sf - lset, pt - 0.005                                   # face; top tucked under the cushion
        vb = vt - lh
        ur = uf - ld
        lip = bu + 0.002                                                 # lip rear: just in front of the shroud
        out["legrest"] = (np.array([(ur, max(bh + 0.004, vb)), (lip, bh + 0.004), (lip, vb), (uf, vb), (uf, vt),
                                    (ur, vt)]) if vb < bh else np.array([(ur, vb), (uf, vb), (uf, vt), (ur, vt)]))
        out["skirt"] = np.array([(-0.08, bh), (ur + 0.010, bh), (ur + 0.010, pt), (-0.06, pt)])
    return out


def exec_back_profile(raised=False, recline=None):
    """Back + headrest of the executive seat in seat-local coordinates (u forward from the SRP, v above the floor):
    {'back', 'head', 'posts'}; the headrest lowest (or raised by head_slide), the back at back_deg (or `recline` deg
    from vertical, about the SRP)."""
    e = EXEC_SEAT
    hup = e["head_slide"] if raised else 0.0
    sh = e["srp_h"]
    b = math.radians(e["back_deg"])
    db, nb = np.array([-math.sin(b), math.cos(b)]), np.array([math.cos(b), math.sin(b)])
    s_top = (e["back_top"] - sh) / math.cos(b)
    o = np.array([0.0, sh])
    bt = e["back_t"]
    back = np.array([o + 0.03 * db + 0.02 * nb, o + s_top * db + 0.02 * nb, o + (s_top + 0.012) * db - 0.04 * nb,
                     o + s_top * db - (bt - 0.02) * nb, o - (bt - 0.02) * nb + np.array([0.0, -0.05])])
    hw, hh = e["head_wh"]
    hc = (e["head_top"] + hup - 0.5 * hh - sh) / math.cos(b)
    head = np.array([o + (hc - 0.5 * hh) * db + 0.035 * nb, o + (hc + 0.5 * hh) * db + 0.035 * nb,
                     o + (hc + 0.5 * hh) * db - 0.06 * nb, o + (hc - 0.5 * hh) * db - 0.06 * nb])
    posts = np.array([o + (s_top - 0.02) * db - 0.03 * nb, o + (hc - 0.5 * hh + 0.01) * db - 0.03 * nb])
    out = dict(back=back, head=head, posts=posts)
    if recline is not None:
        out = {k: _rot(v, o, float(recline) - e["back_deg"]) for k, v in out.items()}
    return out


# ---------------------------------------------------------------------------------------------------- lining
def lining_offset(ny):
    """Lining depth inside the OML for a section normal whose |BL| component is ny (the section-plane unit normal):
    crown + (side - crown) |n_y|^p -- LINING, the law L1 / L6 draw and the 3-D lining (build_lining) is built on."""
    return LINING["crown"] + (LINING["side"] - LINING["crown"]) * np.abs(ny) ** LINING["blend_p"]


def lining_section(x, n=1441):
    """Inner lining of the section at station x: (y, z) points round the whole section (t = 0 crown -> 0.25 stbd
    -> 0.5 keel -> 0.75 port), offset inward by crown + (side - crown) |n_y|^p along the OML normal."""
    t = np.linspace(0.0, 1.0, n, endpoint=False)
    Q = F.section(np.full_like(t, x), t)[:, 1:]
    dQ = np.roll(Q, -1, 0) - np.roll(Q, 1, 0)
    nrm = np.c_[dQ[:, 1], -dQ[:, 0]]
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    c = np.array([0.0, float(F.z_mw(x))])
    nrm *= np.sign(np.sum((Q - c) * nrm, 1))[:, None]                 # outward
    d = lining_offset(nrm[:, 0])
    return Q - d[:, None] * nrm


def lining_half_width(x, z):
    """|BL| of the sidewall lining at station x, water line z."""
    L = lining_section(x)
    k = len(L) // 2
    S = L[:k]                                                          # starboard, crown -> keel: z decreasing
    return float(np.interp(z, S[::-1, 1], S[::-1, 0]))


def lining_crown(x, y):
    """Water line of the headliner at station x, butt line y."""
    L = lining_section(x)
    k = len(L) // 4
    S = L[:k]                                                          # crown -> starboard max breadth: y increasing
    return float(np.interp(abs(y), S[:, 0], S[:, 1]))


# ---------------------------------------------------------------------------------------------------- manikin
def two_link(a, b, L1, L2, up=(0.0, 1.0)):
    """2-D two-link joint (knee / elbow) between a and b with link lengths L1 (from a) and L2, on the side of the
    a-b line that `up` points to.  Clamps an over-stretched chain (returns the point on the line)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b - a
    L = float(np.linalg.norm(d))
    u = d / L
    x = (L1 ** 2 - L2 ** 2 + L ** 2) / (2 * L)
    h = math.sqrt(max(L1 ** 2 - x ** 2, 0.0))
    nrm = np.array([-u[1], u[0]])
    if np.dot(nrm, up) < 0:
        nrm = -nrm
    return a + x * u + h * nrm, L <= L1 + L2


def seated_pose(srp_xz, facing=1, back_deg=11.0, pan_deg=7.0, floor=None, pedal=None, hand=None, man=None,
                scale=1.0, shank_deg=10.0):
    """Side-view pose (x, WL) of the seated manikin on a seat with its SRP at srp_xz.  facing +1 = forward (toward
    -x).  pedal: dict of pedal_points() (crew: heel on the heel point, foot on the face); otherwise the feet rest
    flat on the floor with the shank 10 deg forward.  hand: (x, WL) of the grip (crew yoke); otherwise the forearm
    rests level forward.  Returns the joints, the eye and the head ellipse (centre, half-length, half-height)."""
    m = man or MANIKIN
    fx = -float(facing)                                                # +x component of 'forward'
    s = float(scale)
    b, p = math.radians(back_deg), math.radians(pan_deg)
    srp = np.asarray(srp_xz, float)
    d_pan = np.array([fx * math.cos(p), math.sin(p)])
    n_pan = np.array([-fx * math.sin(p), math.cos(p)])
    hf, hu = m["h_from_srp"]
    H = srp + s * hf * d_pan + s * hu * n_pan
    L_t = s * (m["acromion_sit"] - hu)                                  # H-point -> shoulder, along the reclined back
    torso = L_t * np.array([-fx * math.sin(b), math.cos(b)])
    S = H + torso
    eye = S + np.array([fx * s * m["eye_from_shoulder"], s * (m["eye_sit"] - m["acromion_sit"])])
    hl, hb, hh = (s * v for v in m["head_lwh"])
    head_c = eye + np.array([-fx * (0.5 * hl - 0.03 * s), s * (m["sit_h"] - m["eye_sit"]) - 0.5 * hh])
    thigh, shank = s * m["thigh"], s * m["shank"]
    fl = floor if floor is not None else srp[1] - 0.30
    if pedal is not None:
        a = math.atan2(pedal["dir"][1], abs(pedal["dir"][0]))
        dd = np.array([fx * math.cos(a), math.sin(a)])
        nn = np.array([-fx * math.sin(a), math.cos(a)])
        heel = pedal["heel"]
        ankle = heel + 0.05 * s * dd + 0.085 * s * nn
        ball, toe = pedal["ball"], pedal["toe"]
    else:
        c10 = math.cos(math.radians(shank_deg))
        sin_t = (fl + 0.085 * s + shank * c10 - H[1]) / thigh
        th = math.asin(float(np.clip(sin_t, -1.0, 1.0)))
        knee0 = H + thigh * np.array([fx * math.cos(th), math.sin(th)])
        ankle = knee0 + shank * np.array([fx * math.sin(math.radians(shank_deg)), -c10])
        heel = np.array([ankle[0] - fx * 0.05 * s, fl])
        ball = np.array([heel[0] + fx * 0.21 * s, fl])
        toe = np.array([heel[0] + fx * s * m["foot_l"], fl])
    knee, ok = two_link(H, ankle, thigh, shank, up=(fx, 1.0))
    if hand is None:                                                   # forearm resting forward-down on the thigh
        elbow = S + s * m["upper_arm"] * np.array([fx * math.sin(math.radians(5)), -math.cos(math.radians(5))])
        hand = elbow + s * m["forearm"] * np.array([fx * math.cos(math.radians(22)), -math.sin(math.radians(22))])
        arm_ok = True
    else:
        elbow, arm_ok = two_link(S, hand, s * m["upper_arm"], s * m["forearm"], up=(-fx * 0.3, -1.0))
    return dict(srp=srp, H=H, shoulder=S, eye=eye, head_c=head_c, head_ab=(0.5 * hl, 0.5 * hh),
                head_top=head_c[1] + 0.5 * hh, knee=knee, ankle=ankle, heel=heel, ball=ball, toe=toe,
                elbow=elbow, hand=np.asarray(hand, float), leg_ok=ok, arm_ok=arm_ok, facing=facing, fx=fx,
                back_deg=back_deg, scale=s, knee_r=0.060 * s, thigh_r=0.5 * s * m["thigh_clear"])


def _knee_angle(p):
    k = p["knee"]
    v1, v2 = p["H"] - k, p["ankle"] - k
    return math.degrees(math.acos(float(np.clip(np.dot(v1, v2) / np.linalg.norm(v1) / np.linalg.norm(v2), -1, 1))))


def crew_pose(side=-1, dx=0.0, crank=0.0, scale=1.0, dz=None):
    """Pose in the crew seat at fore/aft travel dx and pedal crank (- = forward); dz = vertical adjustment, default:
    toward the design eye as far as the travel allows.  Feet on the pedals, hands on the yoke grips."""
    c = CREW_SEAT
    if dz is None:
        f, u = design_eye_offset()
        dz = float(np.clip(u * (1.0 - float(scale) / float(P50_SCALE)), -c["travel_z"], c["travel_z"]))
    ped = pedal_points(crank)
    srp = crew_srp(side, dx, dz)
    hub = yoke_hub(side)
    p = seated_pose(srp[[0, 2]], 1, c["back_deg"], c["pan_deg"], FLOOR["fd_wl"], ped,
                    hand=(hub[0] + 0.02, hub[2] + yoke_hand_dz()), scale=scale)
    p.update(seat_dx=float(dx), seat_dz=float(dz), crank=float(crank), knee_angle=_knee_angle(p), side=side)
    p["head_lock"] = headrest_lock(p)
    p["leg_y"] = crew_leg_y(p)
    return p


def crew_leg_y(p):
    """(hip, knee, ankle) distance of a crew leg from the seat CL (front view): the hip joint at MANIKIN hip_y x scale,
    the foot on the pedal-pad centre (PEDALS dy, fixed), the knee on the hip-to-ankle line at its fraction along x in
    the side view, plus MANIKIN knee_splay x scale."""
    s = p["scale"]
    hy, fy = MANIKIN["hip_y"] * s, float(PEDALS["dy"])
    H, K, A = p["H"], p["knee"], p["ankle"]
    L = float(H[0] - A[0])
    t = float(np.clip((H[0] - K[0]) / L, 0.0, 1.0)) if abs(L) > 1e-6 else 0.5
    return float(hy), float(hy + t * (fy - hy) + MANIKIN["knee_splay"] * s), fy


def knee_half(p):
    """Knee centre distance from the seat CL of a pose: crew_leg_y for a crew pose, MANIKIN knee_y x scale otherwise."""
    return p["leg_y"][1] if "leg_y" in p else MANIKIN["knee_y"] * p["scale"]


def crew_setting(scale=1.0, side=-1):
    """The pose an occupant of this scale sets up: the seat height toward the design eye, then the notch (9 holes)
    and pedal crank (5 steps) that bring the knee angle at neutral pedals closest to CRITERIA['knee_angle'] with the
    least travel from neutral."""
    c = CREW_SEAT
    n = int(round(c["travel_x"] / c["notch"]))
    cr = PEDALS["crank"]
    best = None
    for k in range(-n, n + 1):
        dx = k * c["travel_x"] / n
        for crank in np.linspace(-cr, cr, 5):
            p = crew_pose(side, dx, float(crank), scale)
            if not p["leg_ok"]:
                continue
            sc = (((p["knee_angle"] - CRITERIA["knee_angle"]) / 10.0) ** 2 + 0.5 * (dx / c["travel_x"]) ** 2
                  + 0.25 * (crank / cr) ** 2)
            if best is None or sc < best[0]:
                best = (sc, p)
    return best[1]


def cabin_pose(rec, scale=1.0, shank_deg=10.0):
    """95th-pct (scale 1) pose in a cabin seat record of seat_map() (feet flat on the floor, the shanks shank_deg
    forward of vertical, forearms level)."""
    return seated_pose(rec["srp"][[0, 2]], rec["facing"], EXEC_SEAT["back_deg"], EXEC_SEAT["pan_deg"], FLOOR["wl"],
                       scale=scale, shank_deg=shank_deg)


# ---------------------------------------------------------------------------------------------------- yoke sweep
def yoke_grip_axis(d=1):
    """(bottom, top) centres (y, z) of the right (d=+1) or left grip's capsule axis about the hub centre: the outer
    edge at the bottom on YOKE span / 2, the outline bottom at grip_dz, length grip[0] tip to tip, the top leaning
    inboard by the cant."""
    gl, gr, gc = YOKE["grip"]
    a = math.radians(gc)
    p0 = np.array([d * (0.5 * YOKE["span"] - gr), YOKE["grip_dz"] + gr])
    return p0, p0 + (gl - 2.0 * gr) * np.array([-d * math.sin(a), math.cos(a)])


def yoke_grip_y(z, d=1):
    """y of the grip axis at height z (about the hub centre)."""
    p0, p1 = yoke_grip_axis(d)
    return float(p0[0] + (z - p0[1]) * (p1[0] - p0[0]) / (p1[1] - p0[1]))


def yoke_grip_outline(d=1, n=10):
    """Front-view outline (y, z) of the right (d=+1) or left grip about the hub centre: the capsule of yoke_grip_axis
    (radius YOKE grip) swelling over its top grip_head[0] to the head radius grip_head[1], the tip where the capsule's
    tip was (review r3 F2)."""
    gl, gr, _ = YOKE["grip"]
    hl, rh = YOKE["grip_head"]
    p0, p1 = yoke_grip_axis(d)
    ax = (p1 - p0) / np.linalg.norm(p1 - p0)
    nrm = np.array([ax[1], -ax[0]])
    tip = p1 + gr * ax
    ch = tip - rh * ax                                                  # head circle centre
    a = np.linspace(0.0, 1.0, 15)
    C = p0[None, :] + a[:, None] * (ch - p0)[None, :]
    along = (C - (p0 - gr * ax)) @ ax                                   # distance from the bottom tip
    t = np.clip((along - (gl - hl - 0.010)) / (gl - rh - (gl - hl - 0.010)), 0.0, 1.0)
    r = gr + (rh - gr) * t * t * (3.0 - 2.0 * t)
    right, left = C + r[:, None] * nrm, C - r[:, None] * nrm
    th0 = math.atan2(nrm[1], nrm[0])
    top = [ch + rh * np.array([math.cos(th0 + u), math.sin(th0 + u)]) for u in np.linspace(0.0, math.pi, n)[1:-1]]
    bot = [p0 + gr * np.array([math.cos(th0 + math.pi + u), math.sin(th0 + math.pi + u)])
           for u in np.linspace(0.0, math.pi, n)[1:-1]]
    return np.vstack([right, top, left[::-1], bot])


def yoke_shield_yz():
    """Front-view outline (y, z) of the white shield about the hub centre: top corners at +/- hub_whd width / 2 on the
    hub top, the top edge dipping shield_dip to the centre, concave sides narrowing to the hub_bot_w stem (YOKE
    shield)."""
    hw, hh, _ = YOKE["hub_whd"]
    bw = YOKE["hub_bot_w"]
    tt, ff = (np.array(v, float) for v in zip(*YOKE["shield"]))
    t = np.linspace(0.0, 1.0, 11)
    w = 0.5 * bw + (0.5 * hw - 0.5 * bw) * np.interp(t, tt, ff)
    z = 0.5 * hh - t * hh
    right = np.c_[w, z]
    left = np.c_[-w, z][::-1]
    return np.vstack([right, left, [(0.0, 0.5 * hh - YOKE["shield_dip"])]])


def yoke_body_yz():
    """Front-view outline (y, z) of the black yoke body about the hub centre: from the shield foot (rimmed by
    body_arm[1]) its lower edge runs up-outboard to each grip's axis at body_arm[0], up the grip to the shoulder
    (5 mm above the hub top) and back inboard under the shield's top corners (YOKE body_arm)."""
    hw, hh, _ = YOKE["hub_whd"]
    bw = YOKE["hub_bot_w"]
    za, rim = YOKE["body_arm"]
    zs = 0.5 * hh + 0.005
    half = [(0.5 * bw + rim, -0.5 * hh - rim)]
    y_a = yoke_grip_y(za, 1)
    for f in (0.35, 0.70):                                              # slightly concave lower edge
        q = np.array(half[0]) + f * (np.array([y_a, za]) - np.array(half[0]))
        half.append((q[0] + 0.004 * f * (1 - f) * 4, q[1] - 0.004 * f * (1 - f) * 4))
    half += [(y_a, za), (yoke_grip_y(zs, 1), zs), (0.5 * hw - 0.004, 0.5 * hh - 0.006)]
    H = np.array(half)
    cen = (0.0, 0.5 * hh - YOKE["shield_dip"] - 0.008)
    return np.vstack([H[::-1] * [-1, 1], H, [cen]])[::-1]


def yoke_outline_yz(roll=0.0):
    """Front-view outline pieces [(N, 2) (y, z)] of one yoke about its column axis (origin = the hub centre): piece 0
    the white shield (yoke_shield_yz), 1 the black body behind it (yoke_body_yz), 2 / 3 the left / right grips with
    their swollen heads (yoke_grip_outline), rolled `roll` deg (counter-clockwise seen from behind).  Drawn in the order
    1, 0, 2, 3 (the shield on the body)."""
    out = [yoke_shield_yz(), yoke_body_yz()] + [yoke_grip_outline(d) for d in (-1, 1)]
    return [_rot(P, np.zeros(2), roll) for P in out] if roll else out


def yoke_hand_dz():
    """Height of the hand (grip centre) above the hub centre: the middle of the grips."""
    p0, p1 = yoke_grip_axis(1)
    return float(0.5 * (p0[1] + p1[1]))


def leg_spheres(p, yc, legs=(-1, 1)):
    """Spheres (x, y, z, r) along the thighs (knee -> hip) and shanks (knee -> ankle) of a side-view pose; legs picks
    the leg(s): -1 = the one at yc - knee, +1 = at yc + knee.  Crew poses (leg_y): the thigh runs from the knee to the
    hip joint and the shank to the foot on the pedal (crew_leg_y); cabin poses: both at MANIKIN knee_y (scaled)."""
    s = p["scale"]
    hy, ky, ay = p["leg_y"] if "leg_y" in p else (MANIKIN["knee_y"] * s,) * 3
    out = []
    for sg in legs:
        for t in np.linspace(0.0, 1.0, 13):
            c = p["knee"] + t * (p["H"] - p["knee"])
            out.append((c[0], yc + sg * (ky + t * (hy - ky)), c[1], 0.062 * s + t * (p["thigh_r"] - 0.062 * s)))
        for t in np.linspace(0.0, 1.0, 9)[1:]:
            c = p["knee"] + t * (p["ankle"] - p["knee"])
            out.append((c[0], yc + sg * (ky + t * (ay - ky)), c[1], 0.058 * s - t * 0.018 * s))
    return out


def _pt_poly_dist(q, P):
    """Distance from the 2-D point q to the polygon P (0 inside)."""
    P = np.asarray(P, float)
    a, b = P, np.roll(P, -1, 0)
    ab = b - a
    t = np.clip(np.einsum("ij,ij->i", q - a, ab) / np.maximum(np.einsum("ij,ij->i", ab, ab), 1e-12), 0.0, 1.0)
    d = float(np.min(np.linalg.norm(q - (a + t[:, None] * ab), axis=1)))
    cross = (a[:, 1] > q[1]) != (b[:, 1] > q[1])
    xi = a[:, 0] + (q[1] - a[:, 1]) * (b[:, 0] - a[:, 0]) / np.where(cross, b[:, 1] - a[:, 1], 1.0)
    inside = int(np.sum(cross & (xi > q[0]))) % 2 == 1
    return 0.0 if inside else d


def rudder_spheres(p_aft, p_fwd, side=-1, up=-1):
    """Leg spheres with full rudder: the leg on the `up` side (-1 = at the seat CL - knee_y) posed on the pedal that
    came aft (p_aft: its knee rises), the other leg on the pedal pushed forward (p_fwd: extended)."""
    yc = side * CREW_SEAT["bl"]
    return leg_spheres(p_aft, yc, (up,)) + leg_spheres(p_fwd, yc, (-up,))


def yoke_roll_clearances(p, side=-1, pitch=True, step=2.5, max_roll=90.0, spheres=None):
    """{roll deg: (clearance, sphere)} of the pose's thighs, knees and shanks to the yoke (hub + grips) rolled +/-roll
    (the worse of the two) and swept over its pitch travel (pitch=True): the x-slab of the travel times the rolled
    front-view outline.  spheres: leg spheres to test instead of the pose's (e.g. rudder_spheres).  Clearance in m,
    < 0 = interference."""
    hub = yoke_hub(side)
    hd = YOKE["hub_whd"][2]
    t0, t1 = YOKE["travel"] if pitch else (0.0, 0.0)
    xa, xb = hub[0] + t0, hub[0] + hd + t1
    sph = [(max(0.0, xa - x, x - xb), np.array([y - hub[1], z - hub[2]]), r, (x, y, z, r))
           for x, y, z, r in (spheres if spheres is not None else leg_spheres(p, side * CREW_SEAT["bl"]))]
    out = {}
    for ang in np.arange(0.0, max_roll + 1e-9, step):
        polys = yoke_outline_yz(ang) + (yoke_outline_yz(-ang) if ang else [])
        best = (np.inf, None)
        for dx, q, r, s_ in sph:
            if dx - r >= best[0]:
                continue
            cl = math.hypot(dx, min(_pt_poly_dist(q, P) for P in polys)) - r
            if cl < best[0]:
                best = (cl, s_)
        out[round(float(ang), 3)] = best
    return out


def yoke_clearance(p, side=-1, roll=None, pitch=True, table=None):
    """Least clearance (m) of the legs to the yoke swept over its pitch travel and roll +/-roll deg (default
    YOKE['roll']; 0 = wings level): the minimum of yoke_roll_clearances() up to that roll.  Returns (clearance,
    sphere (x, y, z, r) where it is least)."""
    roll = float(YOKE["roll"] if roll is None else roll)
    t = table or yoke_roll_clearances(p, side, pitch)
    return min((v for a, v in t.items() if a <= roll + 1e-9), key=lambda v: v[0])


def roll_limit(p, side=-1, need=0.0, table=None):
    """Largest yoke roll (deg, each way, with the full pitch travel) keeping `need` clearance; -1 if even the wings-
    level pitch sweep does not."""
    t = table or yoke_roll_clearances(p, side)
    r = -1.0
    for a in sorted(t):
        if t[a][0] < need:
            break
        r = a
    return r


# ---------------------------------------------------------------------------------------------------- checks
def _seg_dist(p, a, b):
    """Distance from point p to the segment a-b (2-D)."""
    p, a, b = (np.asarray(v, float) for v in (p, a, b))
    t = float(np.clip(np.dot(p - a, b - a) / np.dot(b - a, b - a), 0.0, 1.0))
    return float(np.linalg.norm(p - (a + t * (b - a))))


def reach_targets(side=-1):
    """[(label, (x, y, z), kind)] of the controls the pilot of the seat on `side` reaches (own-side items on his
    sidewall / panel end), from the panel / pedestal / overhead tables.  kind: 'touch' (touch screens, push-buttons,
    switches, breakers: fingertip) or 'grasp' (levers, the CCD palm grip: thumbtip)."""
    pn, pe, ov = PANEL, PEDESTAL, OVERHEAD
    fl = FLOOR["fd_wl"]
    zm = pn["mfd_z"]
    xo = 0.5 * (ov["x"][0] + ov["x"][1])
    cb = SIDE_CONSOLE["cb_panel"]
    xc, zc = 0.5 * (cb[0] + cb[1]), fl + 0.5 * (cb[2] + cb[3])
    al = ov["autoland"]
    sb = pn["standby"]
    return [("own PFD centre", pdu_centre(side), "touch"),
            ("MFD centre", mfd_centre(), "touch"),
            ("SDU, own side", sdu_centre(side), "touch"),
            ("SDU, far side", sdu_centre(-side), "touch"),
            ("GI 275 standby", np.array([pn["glass_x"], side * abs(sb[0]), zm + sb[1]]), "touch"),
            ("PCL knob", np.array([pe["pcl"][0], pe["pcl"][1], fl + pe["pcl"][2]]), "grasp"),
            ("flap lever", np.array([pe["flap"][0], pe["flap"][1], fl + pe["flap"][2]]), "grasp"),
            ("CCD palm grip", np.array([pe["ccd"][0], pe["ccd"][1], fl + pe["ccd"][2]]), "grasp"),
            ("overhead panel, centre", np.array([xo, 0.0, lining_crown(xo, 0.0) - ov["depth"]]), "touch"),
            ("overhead panel, far end", np.array([xo, -side * 0.5 * ov["w"],
                                                  lining_crown(xo, 0.5 * ov["w"]) - ov["depth"]]), "touch"),
            ("autoland button", np.array([al[0], al[1], lining_crown(al[0], al[1]) - 0.02]), "touch"),
            ("CB panel, own side", np.array([xc, side * lining_half_width(xc, zc), zc]), "touch")]


def reach_of(p, target, side=-1, kind="grasp"):
    """(distance from the nearer shoulder joint, class) for a crew pose: 'LOCKED' within the straight-arm reach
    (harness locked: thumbtip for 'grasp', + MANIKIN fingertip for 'touch'), 'LEAN' within that + lean (inertia reel
    unlocked), 'NO' beyond."""
    s = p["scale"]
    yc = side * CREW_SEAT["bl"]
    d = min(float(np.linalg.norm(np.asarray(target) - np.array([p["shoulder"][0], yc + sg * MANIKIN["shoulder_y"] * s,
                                                                p["shoulder"][1]]))) for sg in (-1, 1))
    R = s * (MANIKIN["reach_sh"] + (MANIKIN["fingertip"] if kind == "touch" else 0.0))
    return d, ("LOCKED" if d <= R else "LEAN" if d <= R + MANIKIN["lean"] else "NO")


def rudder_checks(p, side=-1):
    """Full rudder at an occupant's setting (pose p from crew_setting): one pedal PEDALS travel aft (that knee rises:
    the 'up-knee'), the other as far forward (that leg extends).  The yoke is swept over pitch x roll against the legs
    so posed, with the up-knee on either leg (the worse is kept).  Returns dict(pitch, sweep: clearance (m) wings level
    / up to YOKE roll, roll_contact / roll_clear: roll (deg) to contact / keeping CRITERIA knee_clear, knee_top: WL of
    the up-knee top, ext_knee: knee angle (deg) of the extended leg, ext_ok, p_aft / p_fwd poses, up: the worse leg)."""
    T = PEDALS["travel"]
    s = p["scale"]
    pa = crew_pose(side, p["seat_dx"], p["crank"] + T, s, p["seat_dz"])
    pf = crew_pose(side, p["seat_dx"], p["crank"] - T, s, p["seat_dz"])
    tabs = {up: yoke_roll_clearances(p, side, spheres=rudder_spheres(pa, pf, side, up)) for up in (-1, 1)}
    worst = {a: min((tabs[u][a] for u in tabs), key=lambda v: v[0]) for a in tabs[-1]}
    up = min(tabs, key=lambda u: yoke_clearance(p, side, table=tabs[u])[0])
    return dict(pitch=float(worst[0.0][0]), sweep=float(yoke_clearance(p, side, table=worst)[0]),
                roll_contact=roll_limit(p, side, 0.0, worst),
                roll_clear=roll_limit(p, side, CRITERIA["knee_clear"], worst),
                knee_top=float(pa["knee"][1] + pa["knee_r"]), ext_knee=float(pf["knee_angle"]),
                ext_ok=bool(pf["leg_ok"] and pf["knee_angle"] <= CRITERIA["knee_ext"]), p_aft=pa, p_fwd=pf, up=up,
                table=worst)


def crew_recline_room(dx=0.0, head_c=None, step=0.25, max_deg=30.0):
    """Recline (deg beyond back_deg, about the SRP) before the back / headrest reaches the divider's forward face at
    fore/aft travel dx; negative -> already past it upright (the overlap in mm is crew_checks' 'div_*')."""
    xdiv = DIVIDER["x_aft"] - DIVIDER["t"]
    x0 = CREW_SEAT["srp_x"] + dx
    if x0 + back_rear_offset(head_c) > xdiv:
        return -1.0
    r = 0.0
    while r + step <= max_deg and x0 + back_rear_offset(head_c, r + step) <= xdiv:
        r += step
    return r


def crew_checks(side=-1):
    """Ergonomic numbers of the crew station (m / deg): design eye, vision, and per occupant (PCT: 95th / 50th / 5th
    male, 5th female) the seat setting, eye, knee / yoke clearance over the pitch and roll sweep, headroom, headrest vs
    the divider; reach; seat vs the tunnel plinth; ingress."""
    from model import cockpit_glazing as CG
    c = CREW_SEAT
    eye = design_eye(side)
    out = dict(eye=eye, srp=crew_srp(side), eye_off=design_eye_offset())
    pfd = pdu_centre(side)
    out["eye_to_pfd"] = float(np.linalg.norm(pfd - eye))
    out["eye_to_mfd"] = float(np.linalg.norm(mfd_centre() - eye))
    out["pfd_down_deg"] = math.degrees(math.atan2(eye[2] - pfd[2], eye[0] - pfd[0]))
    out["vision"] = CG.vision(eye)
    xl, zl = glareshield_lip(eye[1])
    out["lip_down_deg"] = math.degrees(math.atan2(eye[2] - zl, eye[0] - xl))
    z_lo = PANEL["mfd_z"] + PANEL["lower_dz"]
    face = np.array([[float(panel_x(z_lo)), z_lo], [float(panel_x(PANEL["mfd_z"])), PANEL["mfd_z"]]])
    xdiv = DIVIDER["x_aft"] - DIVIDER["t"]
    occ = {}
    for key, s in PCT.items():
        p = crew_setting(float(s), side)
        k = p["knee"]
        v = CG.vision(np.array([p["eye"][0], eye[1], p["eye"][1]]))
        hx = p["head_c"][0]
        sh_z = p["shoulder"][1] + 0.02
        tab = yoke_roll_clearances(p, side)
        rud = rudder_checks(p, side)
        occ[key] = dict(
            rud=rud, rud_pitch=rud["pitch"], rud_sweep=rud["sweep"], rud_roll_contact=rud["roll_contact"],
            rud_roll_clear=rud["roll_clear"], rud_knee_top=rud["knee_top"], ext_knee=rud["ext_knee"],
            ext_ok=rud["ext_ok"],
            scale=float(s), pose=p, dx=p["seat_dx"], dz=p["seat_dz"], crank=p["crank"], knee_angle=p["knee_angle"],
            eye_dx=float(p["eye"][0] - eye[0]), eye_dz=float(p["eye"][1] - eye[2]), over_nose=v["over_nose_down"],
            knee_top=float(k[1] + p["knee_r"]), clear_panel=float(_seg_dist(k, face[0], face[1]) - p["knee_r"]),
            yoke_pitch=yoke_clearance(p, side, 0.0, table=tab)[0], yoke_sweep=yoke_clearance(p, side, table=tab)[0],
            roll_contact=roll_limit(p, side, 0.0, tab), roll_clear=roll_limit(p, side, CRITERIA["knee_clear"], tab),
            hip_to_ball=float(np.linalg.norm(p["ball"] - p["H"])),
            headroom=float(lining_crown(hx, eye[1]) - p["head_top"]),
            shoulder_room=float(lining_half_width(p["shoulder"][0], sh_z) - (abs(eye[1]) + 0.5 * s
                                                                              * MANIKIN["bideltoid"])),
            head_c=p["head_lock"],
            head_div=float(xdiv - (c["srp_x"] + p["seat_dx"] + back_rear_offset(p["head_lock"]))))
    out["occ"] = occ
    p95 = occ["p95m"]
    out["headroom"] = p95["headroom"]
    out["shoulder_room"] = p95["shoulder_room"]
    # the seat's mechanical corner: aft notch with the headrest at its highest / 50th / lowest lock
    lo, hi = c["head_lock"]
    x_aft = c["srp_x"] + c["travel_x"]
    out["div_aft"] = {h: float(xdiv - (x_aft + back_rear_offset(h))) for h in (lo, c["head_c"], hi)}
    out["recline"] = {dx: crew_recline_room(dx) for dx in (-c["travel_x"], 0.0, c["travel_x"])}
    # seat pan / cushion vs the nose-tunnel plinth (lateral: the trimmed inboard edge)
    x0p, x1p, phw, pz = pedestal_plinth()
    out["plinth_lat"] = float(abs(c["bl"]) - c["cushion_in"] - phw)
    out["plinth_lat_sym"] = float(abs(c["bl"]) - 0.5 * c["cushion_w"] - phw)
    zmin = FLOOR["fd_wl"] + c["srp_h"] - c["travel_z"] + 0.025 + max(0.0, c["srp_x"] - c["travel_x"] - x1p) \
        * math.tan(math.radians(c["pan_deg"]))
    out["plinth_cushion_top"] = float(zmin - pz)                   # lowest cushion top over the plinth, above it
    out["plate_lat"] = float(abs(c["bl"]) - 0.5 * c["base_w"] - phw)
    # armrests vs the pedestal over the seat travel (review r3 C2): the inboard arm (its face at seat CL - width / 2,
    # its bottom arm_h - 45 mm above the SRP, lowest seat) against the PCL grip standing above it (lateral) and the
    # quadrant top with its switch boxes (vertical); stowed, the arm stands above the back's hinge, higher still
    pe = PEDESTAL
    arm_in = abs(c["bl"]) - 0.5 * c["width"]
    zb_arm = FLOOR["fd_wl"] + c["srp_h"] - c["travel_z"] + c["arm_h"] - 0.045
    gaps = [zb_arm - (FLOOR["fd_wl"] + pe["top_h"] + 0.020)]
    pcl_top = FLOOR["fd_wl"] + pe["pcl"][2]
    if pcl_top > zb_arm:
        gaps.append(arm_in - (abs(pe["pcl"][1]) + 0.5 * pe["pcl_grip"][1]))
    out["arm_pedestal"] = float(min(gaps))
    # reach (5th female and 95th male at their settings)
    out["reach"] = [(lab, kind, {k: reach_of(occ[k]["pose"], t, side, kind) for k in ("p5f", "p95m")})
                    for lab, t, kind in reach_targets(side)]
    # ingress: between the seat backs / cushions, and behind the seats
    ob0, ob1 = DIVIDER["open_bl"]
    arm_up, _ = crew_seat_profile(arm_up=True)
    out["ingress"] = dict(back_gap=float(2 * (abs(c["bl"]) - 0.5 * c["back_w"][1])),
                          top_gap=float(2 * (abs(c["bl"]) - 0.5 * c["back_w"][0])),
                          head_gap=float(2 * (abs(c["bl"]) - 0.5 * c["head_hwt"][1])),
                          arm_up_top=float(c["srp_h"] + arm_up["arm"][:, 1].max()),
                          cushion_gap=float(2 * (abs(c["bl"]) - c["cushion_in"])),
                          hip=float(MANIKIN["hip_br"]), opening=float(ob1 - ob0),
                          behind_neutral=float(xdiv - (c["srp_x"] + back_rear_offset())),
                          behind_fwd=float(xdiv - (c["srp_x"] - c["travel_x"] + back_rear_offset())))
    out["leg_ok"] = all(o["pose"]["leg_ok"] for o in occ.values())
    out["arm_ok"] = all(o["pose"]["arm_ok"] for o in occ.values())
    out.update(divider_items_clearance())
    return out


def curtain_bundle():
    """Stowed divider curtain: (x0, x1, y0, y1, flare top WL, track x) -- the bundle against the divider's forward face
    at the opening edge on the stow side, and the track across the opening at the headliner."""
    side, w, d, h, tuck, _, _ = DIVIDER["curtain"]
    xf = DIVIDER["x_aft"] - DIVIDER["t"]
    ob0, ob1 = DIVIDER["open_bl"]
    y0, y1 = (ob0 - tuck, ob0 - tuck + w) if side < 0 else (ob1 + tuck - w, ob1 + tuck)
    return xf - d, xf, y0, y1, FLOOR["fd_wl"] + h, xf - 0.015


def curtain_band():
    """The gathered curtain above the stowed bundle: (y0, y1) across, the band against the divider's forward face at
    the stow-side edge, all but its visible part behind the walnut edge (DIVIDER curtain band width, visible)."""
    side, _, _, _, _, bw, vis = DIVIDER["curtain"]
    ob0, ob1 = DIVIDER["open_bl"]
    return (ob0 + vis - bw, ob0 + vis) if side < 0 else (ob1 - vis, ob1 - vis + bw)


def divider_items_clearance():
    """Clearances (m) at the aft notch: the stowed curtain bundle to the seat back / headrest on its side (below the
    bundle's flare top), and the extinguisher bottle to the co-pilot seat (back, armrest, side plates within the bottle's
    height); both headrest locks tested (the worse kept); 'curtain_track': the fixed crew tracks' aft ends to the
    bundle's forward face (tracks under the bundle only; inf when none)."""
    c = CREW_SEAT
    fl = FLOOR["fd_wl"]
    x0, x1, y0, y1, zt, _ = curtain_bundle()
    ex, ey, ez, ed, eh = DIVIDER["extinguisher"]
    out = {}
    for key, side, xa, zlo, zhi, ylo, yhi in (("curtain_clear", int(DIVIDER["curtain"][0]), x0, fl, zt, y0, y1),
                                               ("ext_clear", 1, ex - 0.5 * ed, fl + ez - 0.5 * eh, fl + ez + 0.5 * eh,
                                                ey - 0.5 * ed, ey + 0.5 * ed)):
        srp = crew_srp(side, c["travel_x"])
        yc = srp[1]
        worst = np.inf
        for hc in c["head_lock"]:
            pcs, _ = crew_seat_profile(hc)
            base = crew_base_profile(fl - srp[2])
            for nm, P, hw in (("back", pcs["back"], 0.5 * c["back_w"][1]), ("head", pcs["head"], 0.5 * c["head_hwt"][1]),
                              ("arm", pcs["arm"], 0.5 * c["width"]), ("plate", base["plate"], 0.5 * c["base_w"] + 0.006)):
                if max(abs(ylo), abs(yhi)) < abs(yc) - hw or min(abs(ylo), abs(yhi)) > abs(yc) + hw:
                    continue                                         # no overlap across
                X, Z = srp[0] - P[:, 0], srp[2] + P[:, 1]
                m = (Z > zlo) & (Z < zhi)
                if m.any():
                    worst = min(worst, float(xa - X[m].max()))
        out[key] = worst
    # the fixed crew tracks (drawn at the neutral notch) vs the foot of the stowed curtain bundle: the aft track end to
    # the bundle's forward face, for every track under the bundle (review r2 M2)
    gap = np.inf
    for side in (-1, 1):
        srp = crew_srp(side)
        rl = crew_base_profile(fl - srp[2])["rail"]
        for sg in (-1, 1):
            yt = srp[1] + sg * c["rail_dy"]
            if yt + 0.5 * SEAT_TRACKS["w"] < y0 or yt - 0.5 * SEAT_TRACKS["w"] > y1:
                continue
            gap = min(gap, float(x0 - (srp[0] - rl[:, 0].min())))
    out["curtain_track"] = gap
    return out


# ---------------------------------------------------------------------------------------------------- W&B cross-check
DEMPSTER = ((0.081, "head"), (0.497, "trunk"), (0.028, "upper arm"), (0.016, "forearm"), (0.006, "hand"),
            (0.100, "thigh"), (0.0465, "shank"), (0.0145, "foot"))


def occupant_cg(p):
    """Side-view centre of mass (x, WL) of a pose: Dempster (1955) segment-mass fractions (as tabulated by Winter) on
    the pose's joints -- head + neck at the head centre, trunk at mid hip-shoulder, upper arm 0.436 / forearm 0.430 /
    thigh and shank 0.433 from the proximal joint, hand at the grip, foot mid heel-toe; both sides alike."""
    H, S, K, A, E, Hd = (np.asarray(p[k], float) for k in ("H", "shoulder", "knee", "ankle", "elbow", "hand"))
    pts = dict(head=np.asarray(p["head_c"], float), trunk=H + 0.5 * (S - H), **{"upper arm": S + 0.436 * (E - S)},
               forearm=E + 0.430 * (Hd - E), hand=Hd, thigh=H + 0.433 * (K - H), shank=K + 0.433 * (A - K),
               foot=0.5 * (np.asarray(p["heel"], float) + np.asarray(p["toe"], float)))
    w = np.array([f * (1 if k in ("head", "trunk") else 2) for f, k in DEMPSTER])
    P = np.array([pts[k] for _, k in DEMPSTER])
    return (w[:, None] * P).sum(0) / w.sum()


def _crank_for(dx, scale, side=-1, dz=None):
    """Crew pose at seat travel dx with the pedal crank (5 steps) whose neutral-pedal knee angle is nearest the
    CRITERIA target."""
    cr = PEDALS["crank"]
    ps = [crew_pose(side, dx, float(k), scale, dz) for k in np.linspace(-cr, cr, 5)]
    ps = [q for q in ps if q["leg_ok"]] or ps
    return min(ps, key=lambda q: abs(q["knee_angle"] - CRITERIA["knee_angle"]))


def cg_crosscheck(layout=DEFAULT_LAYOUT):
    """POH occupant arms against the 50th-pct occupant's CG (occupant_cg) on the sheet's poses: [(seat, POH arm, SRP x,
    CG x, CG - POH)] for the pilot at the centre notch (his setting) and full aft, and for every cabin seat (upright,
    outboard, feet flat)."""
    s = float(P50_SCALE)
    poh = 4.071                                                        # POH NGX pilot / front-passenger arm [S]
    out = []
    p = crew_setting(s)
    q = _crank_for(CREW_SEAT["travel_x"], s, dz=p["seat_dz"])
    for lab, pp in (("PILOT, centre notch", p), ("PILOT, full aft", q)):
        c = occupant_cg(pp)
        out.append((lab, poh, float(pp["srp"][0]), float(c[0]), float(c[0] - poh)))
    for r in seat_map(layout):
        if r.get("crew"):
            continue
        c = occupant_cg(cabin_pose(r, s))
        out.append((f"{r['id']} ({'fwd' if r['facing'] > 0 else 'aft'}-facing)", r["occ"], float(r["srp"][0]),
                    float(c[0]), float(c[0] - r["occ"])))
    return out


# ---------------------------------------------------------------------------------------------------- sensitivity
def _crew_case(side=-1):
    """95th / 50th: seat setting, roll to contact (neutral pedals), full rudder (wings-level clearance, roll to
    contact, extended knee); 5th female: extended knee at full forward rudder; the aft-notch headrest (top lock) to
    the divider."""
    out = {}
    for k in ("p95m", "p50m", "p5f"):
        s = float(PCT[k])
        p = crew_setting(s, side)
        if k == "p5f":
            pf = crew_pose(side, p["seat_dx"], p["crank"] - PEDALS["travel"], s, p["seat_dz"])
            out[k] = dict(dx=p["seat_dx"], crank=p["crank"], ext=float(pf["knee_angle"]))
            continue
        tab = yoke_roll_clearances(p, side)
        r = rudder_checks(p, side)
        out[k] = dict(dx=p["seat_dx"], crank=p["crank"], contact=roll_limit(p, side, 0.0, tab),
                      rud=r["pitch"], rud_contact=r["roll_contact"], ext=r["ext_knee"], knee_y=p["leg_y"][1])
    c = CREW_SEAT
    xdiv = DIVIDER["x_aft"] - DIVIDER["t"]
    out["div"] = float(xdiv - (c["srp_x"] + c["travel_x"] + back_rear_offset(c["head_lock"][1])))
    return out


SENSITIVITY_CASES = (
    ("as set", ()),
    ("pedals +/-90 (rev B [E])", (("PEDALS", "dy", 0.090),)),
    ("knees 30 wider (splay +30)", (("MANIKIN", "knee_splay", +0.030),)),
    ("knee target 130 deg (120)", (("CRITERIA", "knee_angle", +10.0),)),
    ("SRP 35 aft", (("CREW_SEAT", "srp_x", +0.035),)),
    ("SRP 70 aft", (("CREW_SEAT", "srp_x", +0.070),)),
    ("rudder travel +/-60 (80)", (("PEDALS", "travel", -0.020),)),
    ("rudder travel +/-100 (80)", (("PEDALS", "travel", +0.020),)),
    ("yoke hub 50 higher", (("YOKE", "hub_dz", +0.050),)),
)


def crew_sensitivity(cases=SENSITIVITY_CASES, side=-1):
    """The knee / yoke result against its estimated inputs: [(label, _crew_case())] with each case's parameter
    changes applied (absolute for 'PEDALS dy', otherwise added to the current value) and restored afterwards."""
    tabs = dict(PEDALS=PEDALS, MANIKIN=MANIKIN, CRITERIA=CRITERIA, CREW_SEAT=CREW_SEAT, YOKE=YOKE)
    out = []
    for lab, ch in cases:
        saved = [(t, k, tabs[t][k]) for t, k, _ in ch]
        try:
            for t, k, v in ch:
                tabs[t][k] = v if (t, k) == ("PEDALS", "dy") else float(tabs[t][k]) + v
            out.append((lab, _crew_case(side)))
        finally:
            for t, k, v in saved:
                tabs[t][k] = v
    return out


def exec_obstacles(layout=DEFAULT_LAYOUT):
    """Side-view boxes (name, side, x0, x1, h0, h1 above the floor, |BL| range) a reclining cabin seat back may meet:
    divider, lavatory, cabinets, the FR34 partition, and the living space of the 95th-pct occupant of each cabin seat
    (knee front to the SRP, floor to eye height)."""
    fl = FLOOR["wl"]
    ob0, ob1 = DIVIDER["open_bl"]
    lz = LAVATORY
    out = [("divider", -1, 4.0, DIVIDER["x_aft"], 0.0, 2.0, (abs(ob0), 1.0)),
           ("divider", +1, 4.0, DIVIDER["x_aft"], 0.0, 2.0, (abs(ob1), 1.0)),
           ("lavatory", +1, lz["x"][0], lz["x"][1], 0.0, 2.0, (lz["inboard_bl"], 1.0)),
           ("FR34 partition", -1, BAGGAGE["partition_x"], 10.5, 0.0, 2.0, (0.0, 1.0)),
           ("FR34 partition", +1, BAGGAGE["partition_x"], 10.5, 0.0, 2.0, (0.0, 1.0))]
    for k, cb in CABINETS.items():
        out.append((f"cabinet {k.upper()}", cb["side"], cb["x"][0], cb["x"][1], 0.0, float(cb["h"]),
                    (cb["bl_in"], 1.0)))
    for r in seat_map(layout):
        if r.get("crew"):
            continue
        p = cabin_pose(r)
        f = r["facing"]
        kf = p["knee"][0] - f * p["knee_r"]                            # knee front
        out.append((f"{r['id']} occupant", r["side"], min(kf, r["srp"][0]), max(kf, r["srp"][0]), 0.0,
                    float(p["eye"][1] - fl), (abs(r["bl"]) - 0.5 * EXEC_SEAT["width"],
                                              abs(r["bl"]) + 0.5 * EXEC_SEAT["width"])))
    return out


def exec_recline(rec, layout=DEFAULT_LAYOUT, step=1.0):
    """(recline deg from vertical reachable, limiting obstacle) of a cabin seat record: the back + headrest (raised for
    the 95th pct) rotate about the SRP from back_deg toward EXEC_SEAT['recline_deg'] until they come within
    CRITERIA['furniture_clear'] of an obstacle box on the same side (exec_obstacles)."""
    e = EXEC_SEAT
    f = rec["facing"]
    fx = -float(f)
    y_lo, y_hi = abs(rec["bl"]) - 0.5 * e["width"], abs(rec["bl"]) + 0.5 * e["width"]
    obs = [o for o in exec_obstacles(layout) if o[1] == rec["side"] and o[6][0] < y_hi and o[6][1] > y_lo
           and not o[0].startswith(rec["id"] + " ")]
    m = CRITERIA["furniture_clear"]

    def hit(ang):
        pr = exec_back_profile(raised=True, recline=ang)
        P = np.vstack([pr["back"], pr["head"]])
        X = rec["srp"][0] + fx * P[:, 0]
        V = P[:, 1]
        for nm, _, x0, x1, h0, h1, _y in obs:
            if np.any((X > x0 - m) & (X < x1 + m) & (V > h0 - m) & (V < h1 + m)):
                return nm
        return None
    a = float(e["back_deg"])
    lim = None
    while a + step <= e["recline_deg"] + 1e-9:
        lim = hit(a + step)
        if lim:
            break
        a += step
    return a, lim


def cabin_checks(layout=DEFAULT_LAYOUT):
    """Cabin numbers: envelope vs the published figures, aisle, pitch, club knee gap and feet, headroom / shoulder room
    of the 95th-pct male, head vs headrest, recline room, table, exit access, lavatory."""
    from model.fuselage_parts import EXIT
    x6 = 7.0
    crown = float(F.z_top(x6))
    fl = FLOOR["wl"]
    out = dict(length=float(BAGGAGE["aft_x"] - DIVIDER["x_aft"]),
               width=2 * (float(F.half_w(x6)) - LINING["side"]),
               height=float(crown - LINING["crown"] - fl),
               floor_width=2 * FLOOR["edge_bl"],
               floor_width_avail=2 * lining_half_width(x6, fl + 0.005),
               floor_length=float(BAGGAGE["partition_x"] - DIVIDER["x_aft"]))
    seats = [r for r in seat_map(layout) if not r.get("crew")]
    out["aisle_arm"] = 2 * (EXEC_SEAT["bl"] - 0.5 * EXEC_SEAT["width"])
    out["aisle_cushion"] = 2 * (EXEC_SEAT["bl"] - 0.5 * EXEC_SEAT["cushion_w"])
    out["cushion_to_ledge"] = float(LEDGES["inner_bl"] - (EXEC_SEAT["bl"] + 0.5 * EXEC_SEAT["cushion_w"]))
    by = {r["id"]: r for r in seats}
    if layout == "EX-6S-2":
        a, b = by["PAX 1"], by["PAX 3"]
        out["club_gap"] = float(b["front"] - a["front"])
        pa, pb = cabin_pose(a), cabin_pose(b)
        out["club_knee_gap"] = float((pb["knee"][0] - pb["knee_r"]) - (pa["knee"][0] + pa["knee_r"]))
        out["club_toes_pass"] = float(pa["toe"][0] - pb["toe"][0])     # > 0: the facing feet overlap along x
        ky, fw = MANIKIN["knee_y"], MANIKIN["foot_w"]
        out["club_feet_y"] = (float(ky), float(ky + fw + 0.01))        # PAX 3 feet / PAX 1 feet (interleaved) from CL
        out["club_feet_kick"] = float(FLOOR["edge_bl"] - (EXEC_SEAT["bl"] + ky + 1.5 * fw + 0.01))
        out["club_gap_mirror"] = float(b["front"] - (a["occ"] + EXEC_SEAT["front_occ"]))  # POH-mirror PAX 1
        out["stagger"] = float(by["PAX 6"]["occ"] - by["PAX 5"]["occ"])
        out["pitch_fwd"] = float(by["PAX 5"]["occ"] - by["PAX 3"]["occ"])
        ex0, ex1 = EXIT["cx"] - EXIT["hx"], EXIT["cx"] + EXIT["hx"]
        out["exit_clear"] = float(ex1 - max(ex0, by["PAX 2"]["front"]))
        out["exit_x"] = (ex0, ex1)
        out["exit_sill_h"] = float(EXIT["cz"] - EXIT["hz"] - fl)
        out["back_to_partition"] = float(BAGGAGE["partition_x"] - by["PAX 6"]["rear"])
        out["pax1_back_to_cabinet"] = float(a["rear"] - CABINETS["lh"]["x"][1])
    out["recline"] = {r["id"]: exec_recline(r, layout) for r in seats}
    r = by.get("PAX 3") or seats[0]
    p = cabin_pose(r)
    out["pose"] = p
    out["pose50"] = cabin_pose(r, P50_SCALE)
    out["headroom"] = float(lining_crown(p["head_c"][0], r["bl"]) - p["head_top"])
    out["eye_wl"] = float(p["eye"][1])
    out["shoulder_room"] = float(lining_half_width(p["shoulder"][0], p["shoulder"][1] + 0.02)
                                 - (abs(r["bl"]) + 0.5 * MANIKIN["bideltoid"]))
    din = EXEC_SEAT["travel"][2]                                       # the seat slid fully inboard
    out["headroom_in"] = float(lining_crown(p["head_c"][0], abs(r["bl"]) - din) - p["head_top"])
    out["shoulder_room_in"] = out["shoulder_room"] + din
    out["eye_wl_p50"] = float(out["pose50"]["eye"][1])
    out["win"] = (float(FP_WIN()[0]), float(FP_WIN()[1]))
    # head centre vs the raised headrest (top, bottom above the floor + fl)
    e = EXEC_SEAT
    ht = fl + e["head_top"] + e["head_slide"]
    out["head_rest"] = {k: (float(ht - pp["head_c"][1]), float(pp["head_c"][1] - (ht - e["head_wh"][1])))
                        for k, pp in (("p95m", p), ("p50m", out["pose50"]))}
    # club table (deployed) vs the legs of the club occupants: the least clearance of the leg spheres that lie under
    # the top, per percentile, for the two-leaf table and for the outboard leaf alone (TABLES leaf)
    tb = TABLES["club_p"]
    out["table_ledge"] = float(LEDGES["top_h"] - tb["top_h"])
    out["table"] = {k: dict(table_leg_clearance(float(s), layout), posture=table_posture(float(s), layout))
                    for k, s in PCT.items()}
    out["table_thigh"] = out["table"]["p95m"]["full"][0]
    out["table_thigh_p50"] = out["table"]["p50m"]["full"][0]
    # lavatory: a seated 95th facing inboard on the toilet (back at the lid hinge), bi-fold swing vs the entry zone
    lz = LAVATORY
    tx = lz["bowl_x"]
    cx0, cx1, tdep, th = lz["cabinet"]
    yo = lining_half_width(tx, fl + 0.3)
    ys = yo - lz["seat_back"]
    q = seated_pose((0.0, fl + th), 1, 5.0, 0.0, fl)
    out["lav_knee_past_door"] = float(lz["inboard_bl"] - (ys + (q["knee"][0] - q["knee_r"])))
    out["lav_seat_y"] = float(ys)
    out["lav_pose"] = q
    out["lav_depth"] = float(yo - lz["inboard_bl"])
    out["lav_len"] = float(lz["x"][1] - lz["x"][0])
    out["lav_floor"] = float(min(lining_half_width(x, fl + 0.02) for x in (cx0, tx, cx1)) - tdep - lz["inboard_bl"])
    out["lav_swing_clear"] = float(lz["inboard_bl"] - lz["leaf"] + CLEAR_ZONES["entry_bl"])  # to the entry zone
    return out


def table_leg_clearance(scale=1.0, layout=DEFAULT_LAYOUT, table="club_p", shank_deg=10.0):
    """Least clearance (m) of the club occupants' legs (leg_spheres of cabin_pose at `scale` and shank_deg, both
    legs, seated upright and outboard) to the underside of the deployed table: {'full': (clearance, seat id), 'leaf':
    ...} for the two-leaf top (bl_in to the ledge) and the outboard leaf alone.  Only spheres under the top count;
    +inf when no leg is under it."""
    tb = TABLES[table]
    fl = FLOOR["wl"]
    zu = fl + tb["top_h"] - tb["t"]
    x0, x1 = tb["x"]
    yl = LEDGES["inner_bl"]
    out = {}
    for name, y0 in (("full", tb["bl_in"]), ("leaf", yl - tb["leaf"])):
        best = (math.inf, None)
        for r in seat_map(layout):
            if r.get("crew") or r["side"] != tb["side"]:
                continue
            p = cabin_pose(r, scale, shank_deg)
            for x, y, z, rr in leg_spheres(p, r["bl"]):
                if x0 - rr < x < x1 + rr and y0 - rr < abs(y) < yl + rr and zu - (z + rr) < best[0]:
                    best = (float(zu - (z + rr)), r["id"])
        out[name] = best
    return out


def table_posture(scale=1.0, layout=DEFAULT_LAYOUT, table="club_p", max_deg=45.0):
    """How a club occupant of this scale sits at the deployed table: the least shank angle (deg forward of vertical,
    feet flat; 10 = the upright default) that keeps CRITERIA knee_clear under the two-leaf top, and the gap (m) from
    his toes to the front of the facing seat's base shroud at that angle (< 0: the feet would have to go under it).
    Returns dict(shank, clear, toe_gap, seat) (shank None when even max_deg does not clear)."""
    need = CRITERIA["knee_clear"]
    e = EXEC_SEAT
    recs = {r["id"]: r for r in seat_map(layout) if not r.get("crew") and r["side"] == TABLES[table]["side"]}
    by_facing = {r["facing"]: r for r in recs.values() if TABLES[table]["x"][0] - 0.8 < r["front"]
                 < TABLES[table]["x"][1] + 0.8}
    sh = 10.0
    while sh <= max_deg:
        c, sid = table_leg_clearance(scale, layout, table, sh)["full"]
        if c >= need:
            break
        sh += 1.0
    else:
        return dict(shank=None, clear=float(c), toe_gap=None, seat=sid)
    gaps = []
    for f, r in by_facing.items():
        o = by_facing.get(-f)
        if o is None:
            continue
        p = cabin_pose(r, scale, sh)
        base_front = o["srp"][0] - o["facing"] * e["base_u"]
        gaps.append(float(-r["facing"] * (base_front - p["toe"][0])) if r["facing"] < 0 else
                    float(p["toe"][0] - base_front))
    return dict(shank=sh, clear=float(c), toe_gap=min(gaps) if gaps else None, seat=sid)


def FP_WIN():
    """(bottom, top) water line of the cabin windows (fuselage_parts)."""
    from model import fuselage_parts as FP
    return FP.WIN_CZ - FP.WIN_HZ, FP.WIN_CZ + FP.WIN_HZ


# =====================================================================================================================
# STAGE-3 3-D BUILD (the tables above -> meshes): model/flightdeck.py (panel, glareshield, yokes, pedals, pedestal on
# the tunnel plinth, consoles, overhead, divider), model/seats.py (IPECO-type crew seats, PRO executive seats),
# model/cabin.py (floor, tracks, ledges, tables, lavatory, cabinets, headliner, FR34 partition); the lining below
# =====================================================================================================================
def build_flightdeck(parts, seats=True, ceiling=None):
    """Part 'flight_deck' (model/flightdeck.py) and, with seats, the two crew seats seat_pilot / seat_copilot
    (model/seats.py, IPECO 3A318 type at crew_srp(), neutral travel); ceiling: see build()."""
    from model import flightdeck, seats as S
    flightdeck.build(parts, ceiling=ceiling)
    if seats:
        _seat_parts(parts, S, crew=True)
    return parts


def build_cabin(parts, layout=None, seats=True, ceiling=None):
    """Part 'cabin_interior' (model/cabin.py: floor, tracks, ledges, stowed club tables, lavatory, cabinets,
    headliner, FR34 partition; the port ledge segment goes onto door_cargo) and, with seats, one part per cabin seat
    of the layout (seat_pax1 ..; model/seats.py executive seats at seat_map(), TTL); ceiling: see build()."""
    from model import cabin, seats as S
    cabin.build(parts, layout, ceiling=ceiling)
    if seats:
        _seat_parts(parts, S, crew=False, layout=layout)
    return parts


def _seat_parts(parts, S, crew, layout=None):
    layout = layout or DEFAULT_LAYOUT
    for rec in seat_map(layout):
        if bool(rec.get("crew")) != crew or rec.get("kind") == "commuter":
            continue
        sid = rec["id"]
        if crew:
            ms = S.crew_seat(-1 if sid == "PILOT" else 1)
            tab = CREW_SEAT
            name = f"Crew seat, {'pilot (LH)' if sid == 'PILOT' else 'co-pilot (RH)'}"
            note = "IPECO 3A318-type crew seat: 8-way, reclining, flip-up armrests, 4-point harness, sheepskin covers"
            srp = crew_srp(-1 if sid == "PILOT" else 1)
            info = {"seat": f"{tab['type'].split(' [')[0]}", "SRP": f"STA {srp[0] * 1000:,.0f} / BL "
                    f"{srp[1] * 1000:+,.0f} / WL {srp[2] * 1000:,.0f} (neutral notch, +/-{tab['travel_x'] * 1000:.0f} "
                    f"fore/aft, +/-{tab['travel_z'] * 1000:.0f} height)"}
        else:
            ms = S.cabin_seat(sid, layout)
            name = f"Executive seat {sid} ({'aft' if rec['facing'] < 0 else 'forward'}-facing, " \
                   f"{'LH' if rec['side'] < 0 else 'RH'})"
            note = "PRO executive seat: leather, swivel base on the tracks, one aisle armrest, sliding headrest"
            info = {"seat": f"{sid}, layout {layout}", "SRP": f"STA {rec['srp'][0] * 1000:,.0f} / BL "
                    f"{rec['bl'] * 1000:+,.0f} / WL {rec['srp'][2] * 1000:,.0f}",
                    "POH occupant arm": f"STA {rec['occ'] * 1000:,.0f}"}
        p = Part(S.part_id(sid), name, "interior", group="Interior", material_note=note, info=info)
        for m, mat in ms:
            p.add(m, mat)
        parts[p.id] = p
    return parts


# ---------------------------------------------------------------------------
# side-wall / headliner lining (flight deck + cabin)
# ---------------------------------------------------------------------------
LINING_X = (3.05, F.STA["aft_pressure_bulkhead"] - 0.01)   # just aft of the firewall -> aft pressure bulkhead
LINING_Z0 = FLOOR["wl"] - FLOOR["t"]  # lower edge: the floor-panel underside (flight deck and cabin floors are flush)
LINING_DOOR_MARGIN = 0.008          # hole round the door-panel seams: clear of the 45 mm door slabs (jambs fill it)
LINING_DX = 0.030


def _lining_proxy(m):
    """The OML points under the lining vertices (same loft parameters x, t: UV): the opening fields are evaluated
    there, so every hole lines up with its skin opening."""
    return Mesh(F.section(m.UV[:, 0], m.UV[:, 1] % 1.0), m.F, N=m.N, UV=m.UV)


def _oml_normal(P):
    """Outward unit normals of OML points P (n, 3) in their section plane (the gradient of the section law's signed
    distance; the cabin section is prismatic, so the x part is dropped)."""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    e = 1e-4
    gy = (F._OML.section_distance(x, y + e, z) - F._OML.section_distance(x, y - e, z)) / (2 * e)
    gz = (F._OML.section_distance(x, y, z + e) - F._OML.section_distance(x, y, z - e)) / (2 * e)
    n = np.c_[np.zeros(len(P)), gy, gz]
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)


def _to_seam(P, pan, depth):
    """OML points P near a door-panel seam (side projection just outside it) moved onto the seam (rr = 0) and depth
    inside the skin."""
    from model import fuselage_parts as FP
    x, z = P[:, 0].copy(), P[:, 2].copy()
    for _ in range(3):
        f = FP.rr((x, z), pan)
        e = 1e-4
        gx = (FP.rr((x + e, z), pan) - FP.rr((x - e, z), pan)) / (2 * e)
        gz = (FP.rr((x, z + e), pan) - FP.rr((x, z - e), pan)) / (2 * e)
        g2 = np.maximum(gx * gx + gz * gz, 1e-12)
        x, z = x - f * gx / g2, z - f * gz / g2
    Q = np.c_[x, np.sign(P[:, 1]) * F.side_y(x, z), z]
    return Q - depth * _oml_normal(Q)


def build_lining(parts):
    """Side-wall and headliner lining inside the OML by the L6 LINING law (lining_offset: 40 mm at the crown, D1's
    1.47 m cabin height, blending to 85 mm at the sides, the published 1.52 m width -- the section lining_section()
    draws on L1 / L6), from the firewall to the aft pressure bulkhead, down to the floors: the skins are single-sided
    and wound outward, so without it the glazing showed the back faces of the paint (blue / white) -- through the
    windshield, the side and cabin windows and the open doors (lookdev round 1).  Holes: the windshield, cockpit side
    windows and cabin windows (the skin's own fields, evaluated on the OML under each lining vertex) and the door-panel
    seams (+ LINING_DOOR_MARGIN), each with a reveal back to the skin (window reveals; door wells round the 60 mm
    jambs).  Flight deck (x < STA cockpit_aft) mid grey 'lining_flightdeck', the cabin 'lining'."""
    from cad.mesh import grid_normals, boundary_loops
    from model import fuselage_parts as FP
    from model import cockpit_glazing as CG
    x0, x1 = LINING_X
    extra = [F.STA["cockpit_aft"]] + [cx + s * FP.WIN_HX for xs in FP.FIXED_WINDOWS.values() for cx in xs
                                      for s in (-1, 1)]
    xs = np.unique(np.r_[np.arange(x0, x1, LINING_DX), x1, [e for e in extra if x0 < e < x1]])
    xs = xs[np.r_[True, np.diff(xs) > 2e-3]]
    ts = np.linspace(0.5, 1.5, FP.N_AROUND, endpoint=False)       # seam at the keel (t unwrapped across the crown)
    X, T = np.meshgrid(xs, ts, indexing="ij")
    P = F.section(X, T % 1.0)
    N = grid_normals(P, close_v=True)
    N[..., 0] = 0.0                     # section-plane normal (the yz part of dP/dx x dP/dt is the 2-D section normal)
    N /= np.maximum(np.linalg.norm(N, axis=-1, keepdims=True), 1e-12)
    m = grid_surface(P - lining_offset(N[..., 1])[..., None] * N, close_v=True, UV=np.stack([X, T], -1))
    side_of = lambda q: np.sign(q.V[:, 1])                                           # noqa: E731

    exit_cx = FP.DOOR_WINDOWS["exit_hatch"]
    stations_of = {sd: list(st) + ([exit_cx] if sd == FP.EXIT["side"] else []) for sd, st in FP.FIXED_WINDOWS.items()}

    def cabin_windows(q):
        """The fixed cabin windows and the over-wing exit's window: the lining runs on flush over the plug hatch,
        whose window gets the standard reveal (P1046406 / 02: review r1 F7)."""
        d = np.full(q.nv, 10.0)
        for side, stations in stations_of.items():
            on = side_of(q) * side > 0
            for cx in stations:
                d = np.where(on, np.minimum(d, FP.window_sdf(q.V[:, 0], q.V[:, 2], cx)), d)
        return d
    # glazing holes (sequential single-sided trims, fields re-evaluated on the OML under the trimmed lining)
    glazing = [cabin_windows, lambda q: CG.sidewindow_sdf(q.V[:, 0], q.V[:, 1], q.V[:, 2]),
               lambda q: CG.windshield_sdf(q.V[:, 0], FP.signed_s(q.V[:, 0], q.UV[:, 1]), q.V[:, 2], q.V[:, 1])]
    for f in glazing:
        v = f(_lining_proxy(m))
        if (v < 0).any():
            m = trim(m, v, "positive")
    # door-panel seams (+ margin) of the two hinged doors (the exit hatch is covered: see cabin_windows)
    for o in (FP.AIRSTAIR, FP.CARGO):
        pan = FP.door_panel(o)
        q = _lining_proxy(m)
        v = np.where(side_of(q) * o["side"] > 0, FP.rr((q.V[:, 0], q.V[:, 2]), pan) - LINING_DOOR_MARGIN, 10.0)
        if (v < 0).any():
            m = trim(m, v, "positive")
    # reveals: every hole loop (windows and doors; the tube's end rings excluded) joined to the same loop on the OML
    # -- the exit window's to the hatch's inner face (DOOR_T: the hatch's own window rim runs on from there), the door
    # wells' to the door-panel seam at the door-stop depth (DOOR_T + 4 mm), so no skin edge, painted lip or skin back
    # face shows from the cabin round a closed door (review r1 C1 / F8)
    reveals = []
    for loop in boundary_loops(m):
        Lv = m.V[loop]
        if Lv[:, 0].min() < x0 + 1e-3 or Lv[:, 0].max() > x1 - 1e-3:
            continue
        Ov = F.section(m.UV[loop, 0], m.UV[loop, 1] % 1.0)
        c = Lv.mean(0)
        door = next((FP.door_panel(o) for o in (FP.AIRSTAIR, FP.CARGO)
                     if c[1] * o["side"] > 0 and FP.rr((np.array([c[0]]), np.array([c[2]])), FP.door_panel(o))[0] < 0),
                    None)
        if door is not None:
            Ov = _to_seam(Ov, door, FP.DOOR_T + 0.004)
        elif c[1] * FP.EXIT["side"] > 0 and abs(c[0] - exit_cx) < 0.2:
            Ov = Ov - FP.DOOR_T * _oml_normal(Ov)
        n = len(loop)
        i = np.arange(n)
        j = (i + 1) % n
        r = Mesh(np.vstack([Lv, Ov]), np.vstack([np.stack([i, j, n + j], 1), np.stack([i, n + j, n + i], 1)]))
        c = Ov.mean(0)
        if np.mean(np.sum((r.V[r.F].mean(1) - c) * r.face_normals(), 1)) > 0:
            r = r.flipped()                                                           # facing into the opening
        reveals.append(r)
    # the floors (the airstair and cargo door holes run below them)
    m = trim(m, m.V[:, 2] - LINING_Z0, "positive")
    rv = Mesh.merge(reveals)
    rv = trim(rv, rv.V[:, 2] - LINING_Z0, "positive")
    m = m.flipped()                                                                   # front faces toward the cabin
    xa = F.STA["cockpit_aft"]
    p = Part("interior_lining", "Side-wall & headliner lining (flight deck, cabin), window reveals, door wells",
             "interior", group="Interior", material_note="Moulded composite lining panels",
             info={"lining": f"{LINING['crown'] * 1000:.0f} mm (crown) - {LINING['side'] * 1000:.0f} mm (sides) inside "
                             f"the OML (L6 LINING: cabin {CABIN['height']:.2f} m high, {CABIN['width']:.2f} m wide)",
                   "extent": f"STA {x0 * 1000:,.0f} - {x1 * 1000:,.0f}, flight deck to STA {xa * 1000:,.0f}"})
    for piece, keep, mat in ((m, "negative", "lining_flightdeck"), (rv, "negative", "lining_flightdeck"),
                             (m, "positive", "lining"), (rv, "positive", "lining")):
        q = trim(piece, piece.V[:, 0] - xa, keep).compact()
        q._reveal = piece is rv          # reveals end ON the skin openings (test/fit_check.py checks them apart)
        p.add(q, mat)
    parts[p.id] = p


# ---------------------------------------------------------------------------
# structure
# ---------------------------------------------------------------------------

def frame_ring(x, depth=0.055, n=144):
    t = np.linspace(0, 1, n, endpoint=False)
    outer = F.section(np.full(n, x), t)
    c = np.array([x, 0, float(F.z_mw(x))])
    d = outer - c
    dn = d / np.linalg.norm(d, axis=1, keepdims=True)
    o = outer - dn * 0.004
    i = outer - dn * (0.004 + depth)
    V = np.vstack([o, i])
    k = np.arange(n)
    Fc = np.vstack([np.stack([k, (k + 1) % n, (k + 1) % n + n], 1), np.stack([k, (k + 1) % n + n, k + n], 1)])
    UV = np.vstack([np.stack([np.full(n, x), t], 1)] * 2)
    return Mesh(V, Fc, UV=UV)


def cut_openings(m, margin=0.03):
    """Interrupt structure at door / window / windshield cut-outs."""
    from model.fuselage_parts import openings_field
    from cad.mesh import trim
    f = openings_field(m) - margin
    return trim(m, f, "positive") if (f < 0).any() else m


def frame_stations():
    """Numbered fuselage frames: the labelled Pilatus frames (fuselage.FRAMES FR10 ... FR40) with the frames between
    them interpolated at equal pitch, plus FR41 ... ahead of the tail-cone closure.  Returns [(name, STA)]."""
    import re
    lab = sorted((int(re.sub(r"\D", "", k)), v) for k, v in F.FRAMES.items() if k.startswith("FR"))
    out = []
    for (n0, x0), (n1, x1) in zip(lab[:-1], lab[1:]):
        for k in range(n0, n1):
            out.append((f"FR{k}", x0 + (x1 - x0) * (k - n0) / (n1 - n0)))
    n, x = lab[-1]
    pitch = (lab[-1][1] - lab[-2][1]) / (lab[-1][0] - lab[-2][0])
    from model import empennage as E
    while x < float(E.tail_cut_x(F.z_bot(min(x, F.STA["tail_end"])))) - 0.05:
        out.append((f"FR{n}", x))
        n, x = n + 1, x + pitch
    return out


RIB_BAY_CLEAR = 0.012          # ribs stop this far outside the main-gear bay liner (plan)
REAR_SPAR = 0.66               # rear-spar chord fraction


def rib_chord_end(y):
    """Aft end (chord fraction) of the wing box at BL y: the rear spar inside the flap / aileron bays (10 mm ahead of
    the cove where the cove reaches further forward), otherwise the trailing-edge rib end (97 %)."""
    if W.Y_FLAP[0] <= y <= W.Y_FLAP[1]:
        return min(REAR_SPAR, float(W.flap_cove(W.section_at(y))[:, 0].min()) - 0.01)
    if W.Y_AIL[0] <= y <= W.Y_AIL[1]:
        return min(REAR_SPAR, min(W.x_end_of_plain(W.section_at(y), float(W.ail_xh(y)))) - 0.01)
    return 0.97


def rib_chord_spans(y, x0=0.02, x1=0.97, min_len=0.02):
    """Chord-fraction spans [(xa, xb)] of the wing rib at BL y (M5): 2-97 % chord, ending at the rear spar (66 %,
    or just ahead of the cove) inside the flap and aileron bays, and cut round the main-gear bay liner
    (bays.main_bay_sdf + RIB_BAY_CLEAR) so no rib crosses the wheel well, leg slot or brace pocket."""
    from model.bays import main_bay_sdf
    x1 = min(x1, rib_chord_end(y))
    s = W.section_at(y)
    xc = np.linspace(x0, x1, 400)
    xs = s.lower(xc)[:, 0]
    ok = main_bay_sdf(xs, np.full_like(xs, y)) > RIB_BAY_CLEAR
    spans, i = [], 0
    while i < len(xc):
        if ok[i]:
            j = i
            while j + 1 < len(xc) and ok[j + 1]:
                j += 1
            if xc[j] - xc[i] >= min_len:
                spans.append((float(xc[i]), float(xc[j])))
            i = j + 1
        else:
            i += 1
    return spans


def build_structure(parts):
    from model import empennage as E
    from model.fuselage_parts import bulkhead, nose_trunnion_notch
    rings = []
    frames = frame_stations()
    for name, x in frames:
        r = frame_ring(x, depth=0.065 if x < 10 else 0.045)
        r = cut_openings(r)
        if (E.tail_cut_field(r.V[:, 0], r.V[:, 2]) > 0).any():
            r = trim(r, E.tail_cut_field(r.V[:, 0], r.V[:, 2]), "negative")
        rings.append(r)
    # stringers: kept above and below the window belt (belt WL 1.995-2.380 -> gap 1.95-2.43), to the tail closure
    strs = []
    x_end = float(E.tail_cut_x(2.2)) - 0.02
    for t in np.linspace(0, 1, 28, endpoint=False):
        z6 = float(F.section(np.array(6.0), np.array(t))[2])
        if 1.95 < z6 < 2.43:
            continue
        xs = np.linspace(3.05, x_end, 110)
        P = F.section(xs, np.full_like(xs, t))
        c = np.stack([xs, np.zeros_like(xs), F.z_mw(xs)], 1)
        d = P - c
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        tube = sweep_tube(P - d * 0.015, 0.008, n=6, cap=False)
        tube.UV = np.stack([tube.V[:, 0], np.full(len(tube.V), t)], 1)
        tube = trim(tube, E.tail_cut_field(tube.V[:, 0], tube.V[:, 2]) + 0.02, "negative")
        strs.append(cut_openings(tube, margin=0.02))
    # pressure bulkheads (forward one notched round the nose-gear trunnion, like the firewall)
    bh = [bulkhead(F.STA["firewall"] + 0.01, 0.97, notch=nose_trunnion_notch, normal=(1, 0, 0)),
          bulkhead(F.STA["aft_pressure_bulkhead"] + 0.01, 0.97, normal=(1, 0, 0))]
    # wing spars (front ~15 %, rear ~66 %) and ribs; the carry-through flattened under the cabin floor (wing.py)
    sp = []
    for frac in (0.15, 0.66):
        rows = []
        ys = np.linspace(-W.SEMI + 0.05, W.SEMI - 0.05, 60)
        for y in ys:
            s = W.section_at(abs(y))
            fr = frac if frac < 0.5 else min(frac, rib_chord_end(abs(y)))     # rear spar ahead of the aileron cove
            lo = s.lower(np.array(fr)) * [1, np.sign(y) if y != 0 else 1, 1]
            up = s.upper(np.array(fr)) * [1, np.sign(y) if y != 0 else 1, 1]
            lo = np.array([lo[0], y, lo[2] + 0.004])
            up = np.array([up[0], y, up[2] - 0.004])
            rows.append(np.linspace(lo, up, 4))
        m = grid_surface(np.array(rows))
        m.V = W.centre_section_clamp(m.V, margin=0.004)
        sp.append(m)
    ribs = []
    for y in list(np.arange(0.9, W.SEMI - 0.2, 0.55)):
        for xa, xb in rib_chord_spans(y):
            s = W.section_at(y)
            xx = np.linspace(xa, xb, max(4, int(np.ceil((xb - xa) / 0.03)) + 1))
            loop = np.vstack([s.lower(xx[::-1]) + [0, 0, 0.004], s.upper(xx[1:]) - [0, 0, 0.004]])
            for sg in (1, -1):
                ribs.append(planar_cap(loop * [1, sg, 1], (0, sg, 0)))
    p = Part("structure", "Primary structure: frames, stringers, spars, ribs", "structure", group="Structure",
             material_note="2024-T3 / 7075-T6, zinc-chromate primed",
             info={"frames": f"{len(frames)}: {frames[0][0]} (STA {frames[0][1] * 1000:.0f}) - {frames[-1][0]} "
                             f"(STA {frames[-1][1] * 1000:.0f}), labelled frames per the Pilatus drawing",
                   "wing": "2-spar box, ribs @ 550 mm"})
    p.add(Mesh.merge(rings + bh), "zinc_chromate").add(Mesh.merge(strs), "zinc_chromate")
    p.add(Mesh.merge(sp + ribs), "interior_green")
    parts[p.id] = p


def build(parts):
    build_interior(parts)
    build_structure(parts)
    return parts


def build_interior(parts):
    """Flight deck + crew seats, cabin + executive seats, lining.  The fittings fixed to the headliner -- the cabin
    headliner group (flat centre panel, soffits, LED coves, PSUs / reading lights, downlights, placards) and the
    flight-deck overhead panel -- go onto the interior_lining part rather than cabin_interior / flight_deck: the
    viewer's cutaway (web/viewer CUT_PARTS) clips the lining and they would float over the open cabin otherwise."""
    ceiling = []
    build_flightdeck(parts, ceiling=ceiling)
    build_cabin(parts, ceiling=ceiling)
    build_lining(parts)
    by_mat = {}
    for m, mat in ceiling:
        by_mat.setdefault(mat, []).append(m)
    for mat, ms in by_mat.items():
        parts["interior_lining"].add(Mesh.merge(ms), mat)
    parts["interior_lining"].name += "; headliner fittings (PSUs, LED coves), flight-deck overhead panel"
    return parts
