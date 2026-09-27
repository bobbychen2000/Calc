"""
Landing gear: electromechanically actuated tricycle (PC-12 NG MSN 1451+ / NGX / PRO).
  POH 7-4: trailing-link mains with hydraulic shock struts retract INWARD; one door per
  side attached to the gear leg; retracted tyres protrude ~1 in from the wells.
  Nose: hydraulic shock strut, retracts REARWARD, fully enclosed by spring-closed doors.
  All legs locked down by an over-centre two-piece folding strut.
  * Main: trailing-link units on the wing spars, retract INWARD into the wing.
          Tyres 8.50-10 Type III (owner decision 2026-09-26; model/wheels.py MAIN_TYRE_CHOICE; Jane's 22 x 8.50-10 superseded).
  * Nose: steerable oleo strut, retracts REARWARD under the flight deck.
          Tyre 17.5 x 6.25-6, steering +/-60 deg.
Geometry is built in the gear-DOWN position; each unit stores its retraction
axis/angle (and each door its opening angle) for the viewer's gear animation.
Wheel track 4.53 m (Pilatus), wheelbase 3.48 m (POH three-view).
Stage 2 (rev B): axle, pivot and brace positions from the Pilatus NGX drawing (side / front views).
"""
from __future__ import annotations
import math

import numpy as np

from cad.mesh import (Mesh, revolve, cylinder, box, sweep_tube, grid_surface, trim, solidify,
                      rotation_about, superellipsoid, cap_ring)
from cad import sdf2d
from model.parts import Part
from model import wing as W
from model import fuselage as F
from model import wheels as WH

TRACK = 4.53
WHEELBASE = 3.48
# Stage 2 (rev B): axles and leg geometry from the Pilatus drawing side / front views.  The drawing's axles are
# 3.515 m apart; the POH 3.48 m is kept and the pair is centred on the drawn axles (each unit moved rigidly by
# GEAR_SHIFT, forward for the main gear, aft for the nose gear).
GEAR_SHIFT = 0.0175
# tyre envelopes from the wheel tables (model/wheels.py): main 8.50-10 Type III (R 0.320, owner decision 2026-09-26;
# Jane's 22 x 8.50-10 superseded, wheels.MAIN_TYRE_CHOICE), nose 17.5 x 6.25-6.  The axle WLs are the static LOADED radii
# (the tyres flatten at the ground).  The wheels themselves: wheels.main_wheel / nose_wheel
MAIN_TYRE = {k: float(WH.MAIN_TYRE_ENV[k]) for k in ("R", "W", "rim")}
NOSE_TYRE = {k: float(WH.NOSE_TYRE_ENV[k]) for k in ("R", "W", "rim")}
MAIN_AXLE = np.array([6.428 - GEAR_SHIFT, TRACK / 2, 0.279])        # static, tyre on the ground line
# nose axle WL = the nose tyre's static loaded radius (wheels.NOSE_TYRE_ENV R_loaded 0.207, photos 200-210; the drawn
# circle touching the ground put it at 0.222): the tyre is flattened 15.5 mm at the ground, the fork arms reach 15 mm lower
NOSE_AXLE = np.array([MAIN_AXLE[0] - WHEELBASE, 0.0, float(WH.NOSE_TYRE_ENV["R_loaded"])])
# Main retraction pivot (axis along x).  Stage 3 leg-door decision (LD-1, owner-delegated): the drawn leg top
# (STA 5,950 / WL 1,070 at the wing lower skin, MAIN_TRUNNION_DRAWN) cannot be the pivot of a FLUSH leg door: retracted,
# the door lies in the skin and the leg above it, so the pivot must sit about one leg radius + the door thickness above
# the skin.  The trunnion is hidden inside the wing, so it moves (a) up 85 mm to WL 1,155 (retracted, the leg lies
# ~10 mm above the door's inner face) and (b) aft 45 mm to STA 5,995 (drawing frame), so the leg axis passes the lower
# skin at STA ~5,991 and the leg front (R 50) stays behind the door's forward edge, as drawn (the side view shows the
# leg hidden by the door).  Below the skin the leg keeps its drawn line through the link pivot to the axle; only its
# lean behind the door changes (11.0 deg instead of 16.9).  The visible trailing link, shock and brace are unchanged.
MAIN_TRUNNION_DRAWN = np.array([5.950 - GEAR_SHIFT, TRACK / 2, 1.070])
MAIN_TRUNNION = np.array([5.995 - GEAR_SHIFT, TRACK / 2, 1.155])
MAIN_LEG_R = (0.050, 0.047)          # main leg radius at the trunnion / at the trailing-link pivot
MAIN_LINK_PIVOT = np.array([6.118 - GEAR_SHIFT, TRACK / 2, 0.517])  # trailing-link pivot on the leg
MAIN_SHOCK = ((6.333 - GEAR_SHIFT, 0.930), (6.380 - GEAR_SHIFT, 0.400))   # shock strut top / bottom (x, z)
# side brace A (wing fitting), B0 (lug on the leg).  WL as drawn (front view); A at the drawn BL; stations hidden (behind
# the door in the side view, inside the wing).
# LD-1: A 5,950 -> 6,058 and B0 6,040 -> 6,056 (drawing frame), so the brace plane lies just behind the door's
# chamfered forward-lower corner: folding, the lower link passes the skin inside the door's footprint (at 5,950 it
# swept a slot ahead of the corner that nothing could close); B0 on the leg axis in the side view.
# MV2-02 (re-derived on the LD-1 geometry): at the drawn BL 2,250 -- 15 mm inboard of the leg axis, inside the leg
# tube -- the stowed lower link ran through the stowed leg for up to 0.35 m (86 deg stow: the leg lies inboard-aft of
# B, the link inboard from B at the leg's WL).  B0 sits on a lug MAIN_BRACE_LUG inboard of the drawn BL (= above the
# leg when stowed, gear.main_brace_lug), which lifts the stowed link over the leg (26 mm clear) and keeps its skin
# crossing inside the door footprint (>= 16 mm from the cut-out edge; fit_check 10 / 14)
MAIN_BRACE_DRAWN_X = (5.950 - GEAR_SHIFT, 6.040 - GEAR_SHIFT)
MAIN_BRACE_DRAWN_BL = (1.330, 2.250)
MAIN_BRACE_LUG = 0.080
MAIN_BRACE = ((6.0575 - GEAR_SHIFT, MAIN_BRACE_DRAWN_BL[0], 1.220),
              (6.0555 - GEAR_SHIFT, MAIN_BRACE_DRAWN_BL[1] - MAIN_BRACE_LUG, 0.840))
NOSE_PIVOT = np.array([2.970 + GEAR_SHIFT, 0.0, 1.040])
NOSE_FORK = np.array([2.930 + GEAR_SHIFT, 0.0, 0.520])             # fork crown / piston bottom
NOSE_BRACE = ((3.470 + GEAR_SHIFT, 0.0, 1.070), (3.030 + GEAR_SHIFT, 0.0, 0.785))      # drag brace A, B0
# The drag brace's upper link is a FORK (MV2-01): two arms at BL +/-NOSE_BRACE_FORK['y'] straddle the leg, which in the
# last ~12 deg of its 105 deg swing passes over A (A lies inside the leg's swept disc: 0.50 m from NOSE_PIVOT, the leg
# with its fork crown is 0.54 m long) and stows right above it; the fixed attach is two stub pins on the bay walls, the
# lower link a single tube to the lug B0 on the leg's aft face.  Side view (the drawn A / B0 line) unchanged.
NOSE_BRACE_FORK = dict(y=0.135, r=0.010, stub=(0.125, 0.147), pin_r=0.011, bend=0.60, y_knee=0.095)
NOSE_FORK_CROWN_HW = 0.118          # fork half-width (the yoke arms end at +/-0.118, NOSE_YOKE; clears the brace fork)
# Retraction (Stage 3).  Nose: 105 deg aft about NOSE_PIVOT puts the axle at WL ~1.20 and the tyre 33 mm above the
# keel (95 deg left it 108 mm below the keel); the wheel stows in a tunnel under the centre pedestal
# (NOSE_TUNNEL: x-range, half-width, top WL).  Folding struts: two links of unequal length (L1 = upper link A-K as a
# fraction of |A - B0|) and the bend side chosen so the knee stays inside the bay / between the wing skins over the
# whole retraction (fit_check verifies): nose knee folds UP, clear of the stowed tyre and above the keel; main knee
# folds DOWN inside the wing box (rev B: equal links, main knee 177 mm above the upper skin when retracted).
# Main (LD-1): 86 deg inboard, not 90.  The wing lower skin rises outboard at ~7 deg over the bay (6.23 deg dihedral
# plus the root-to-tip thickness taper), so a 90 deg stow leaves the wheel, 0.88 m inboard of the trunnion, ~45 mm
# further from the skin than the leg; 86 deg lays the stowed leg and wheel roughly along the skin: with the trunnion
# 85 mm above it the tyre protrudes the POH ~1 in (main_tyre_protrusion(): 26 mm) and the shock strut stays under the
# bay-liner roof (the binding pair: leg above the door vs shock under the upper skin, 0.28 m wing depth).
NOSE_RETRACT_DEG = -105.0
MAIN_RETRACT_DEG = 86.0
# nose clamshells: closed -> open (hanging beside the leg; open while the gear is down).  92 deg (was 85): the lower
# edges lean 2 deg out, so the two-arm fork's axle nuts (+-0.130, wheels review r1 F3 / F4) pass the doors' inner faces
# (+-0.136) as the gear retracts; at 85 deg the doors leaned in to +-0.126
NOSE_DOOR_OPEN_DEG = 92.0
# tunnel x0 3.20 (rev: 3.30): the drag brace's lower link (B at x 3.22-3.25, WL 1.12-1.16 when retracted, rising to the
# knee under the pedestal) passes under the tunnel roof, not the low forward bay roof (M7)
NOSE_TUNNEL = dict(x0=3.200, x1=4.100, hy=0.155, z_top=1.460, z_low=1.200)
NOSE_BRACE_SPLIT = (0.40, (-0.72, 0.0, 0.695))        # (L1 fraction, bend reference)
# main L1 0.19 (LD-1; was 0.15): with the raised trunnion the stowed leg attach point B comes to 0.624 m of A, closer
# than L2 - L1 = 0.70 m of a 0.15 split (the knee could not close the chain); 0.19 leaves 6 mm and folds the knee
# down to ~65 mm above the lower skin, inside BRACE_POCKET (a longer upper link folds deeper and drags the lower link's
# skin crossing inboard of the door's footprint)
MAIN_BRACE_SPLIT = (0.19, (0.0, 0.30, -0.95))         # starboard; the bend reference is mirrored for port
# (with the MV2-02 lug the stowed B comes 36 mm further out than L2 - L1: the chain closes at every pose)
# main side brace: the two links are offset along the knee pin (x) by MAIN_BRACE_CLEVIS (signed, from the A-B0 plane)
# so the short upper link and the lower link pass each other as the knee closes (coplanar tubes overlapped, MV2-02).
# LD-1 moved the brace plane aft to STA ~6,040, next to the stowed leg's lower end and trailing-link yoke (x >= 6,064
# when stowed): the lower link runs AHEAD of the plane (clears the yoke by 31 mm), the upper link behind it; both stay
# inside the brace pocket (bays.BRACE_POCKET, x 5.970-6.110)
MAIN_BRACE_CLEVIS = (0.016, -0.024)  # upper link at A.x + 0.016, lower link at A.x - 0.024 (6 mm between the tubes)
MAIN_BRACE_R = (0.016, 0.018)        # upper / lower link half-thickness along the knee pin (x)
# VQA r1 SHP-07: the photo links are heavy forged links (~60 mm deep in the brace plane), not 32 mm rods: elliptic
# sections MAIN_BRACE_R thick along the pin (the clevis spacing is unchanged) and MAIN_BRACE_W half-deep in the brace
# plane (at A / B0 end, tapering to the knee), with a knee lug MAIN_BRACE_KNEE (half-sizes x, in-plane)
MAIN_BRACE_W = ((0.030, 0.024), (0.022, 0.030))   # (upper: at A, at K), (lower: at K, at B0)
MAIN_BRACE_KNEE = (0.036, 0.034)     # (unused x half-size, in-plane half-size of the knee lug)


# Main-gear leg door (ONE per leg, POH), Stage 2 rev B.1.  The Pilatus drawing shows it in TWO views: edge-on in the
# front view (a plate outboard of the tyre, leaning out from BL 2368 at WL 1052 to BL 2473 at its lowest point WL
# 338) and face-on in the side view (port main gear: a closed outline in front of the tyre, whose arc behind it is
# a hair line).  Its side-view face is fitted here (all stations less GEAR_SHIFT, like the rest of the unit):
#   forward edge   STA 5,950 at the wing -> 5,969 at WL 460 (leans aft 19 mm), then a chamfer to
#   pointed tip    (6,062, 318), 15 mm flat to the
#   lower edge     concave circle arc, centre (6,358, 119), R 348 (fit within 0.2 mm), rising to
#   aft-lower corn (6,404, 464): the narrow lower part's aft edge is vertical at STA 6,404 up to WL 758, then a
#   step           diagonal to (6,615, 939) and the wide upper part's aft edge up to (6,603, 1,088);
#   top edge       straight, WL 1,073 -> 1,088 (about the drawn trunnion WL 1,070), just below the wing.
# Photos agree on the shape: ngx_dfbox_port (telephoto, near-broadside, port) shows the pointed tip ~0.4 m ahead of
# the axle, the concave lower edge rising to above the hub, the narrow lower part and the diagonal step to the wide
# upper part; PRO s/n 3036 (3/4 view) the same stepped aft edge.  In ngx_dfbox_port the door sits ~0.1 m lower
# relative to the wheel than drawn, and on s/n 3036 its lower edge comes close to the hub (trailing link compressed
# under load) -- the drawing's static pose is kept.  Details: refs/photo_notes.md (e).
# The drawing's two views differ by 20 mm on the lowest point (side-view tip WL 318, front-view plate end WL 338);
# the side-view face is kept.  Rev B.0 read the face from the oblique photos instead (straight aft edge at 6,520,
# tip 0.14 m ahead of the axle, a hub cut-out R 150 about the axle): 116 mm off the drawn outline.
#
# Stage 3 leg-door decision LD-1 (owner-delegated; replaces the '[open]' item of the verify-fix round).  Priorities:
# (1) photo / POH truth when retracted: the underside is flush (in-flight photos pil_PC12_045, N81DW from below: a
#     smooth wing root with only the tyre showing in its round well), the tyre protrudes ~1 in, ONE leg-mounted door
#     per side, nothing else hangs below the skin; (2) the gear-down stance and the drawn side-view face stay.
# A rigid door that closes flush IS a piece of the wing lower skin carried down by the leg: leg_door_offset() puts
# every point of the door's outer face where the inverse retraction takes the skin, so the retracted door is the skin
# (LEG_DOOR_RECESS inside it, so the skin's cut-out edge never z-fights the door).  Consequences, all from the geometry:
#   * front view: the door stands ~0.08 m outboard of the leg / wheel plane, nearly vertical (BL ~2,34), instead of
#     the drawn plane leaning out from BL 2,358 to 2,472.  The lean cannot be kept: retracted, the door must lie on
#     the skin and the wheel mid-plane ~83 mm above it (1 in protrusion of the 216 mm tyre), so the door is parallel
#     to the wheel plane gear down;
#   * side view: the drawn face overlaps the static tyre by up to 93 mm; retracted, that part would lie UNDER the
#     protruding tyre, so the door is scalloped round the tyre (tyre R + 12.5 about the axle: R 332 with the 8.50-10) and the
#     tyre sits in its own round well (bays.main_opening_sdf), as in the photos from below;
#   * a forward top tab (hidden in the wing slot with the gear down) continues the door up past the trunnion over the
#     leg's skin crossing, so the retracted door also closes the hole the leg passes through (the verify-fix round's
#     uncovered forward slot is gone); the rest of the drawn top edge (12-37 mm below the wing) is kept.
LEG_DOOR = dict(x_fwd=5.950 - GEAR_SHIFT, x_fwd_low=5.969 - GEAR_SHIFT, z_fwd_low=0.460,   # forward edge
                tip=(6.062 - GEAR_SHIFT, 0.318), arc_x0=6.0762 - GEAR_SHIFT,               # tip, arc start STA
                arc_c=(6.3582 - GEAR_SHIFT, 0.1187), arc_r=0.3482,                         # concave lower edge
                x_aft_low=6.404 - GEAR_SHIFT, z_step=(0.758, 0.939),                       # narrow part, step WLs
                x_aft=6.615 - GEAR_SHIFT, x_aft_top=6.603 - GEAR_SHIFT,                    # wide part's aft edge
                z_top=(1.073, 1.088),                                                      # top edge WL fwd / aft
                bl=(2.358, 2.472),                                                         # DRAWN front-view plane
                scallop_r=MAIN_TYRE["R"] + WH.SCALLOP_CLEAR,   # LD-1: tyre scallop about MAIN_AXLE (R + 12.5)
                tab=(6.070, MAIN_TRUNNION[2] + 0.090))   # LD-1: forward top tab: aft STA, top WL (hidden, in the slot)
LEG_DOOR_T = 0.012                  # door plate thickness (inboard of the outer face)
LEG_DOOR_RECESS = 0.001             # retracted, the door's outer face lies this far inside the wing lower surface
LEG_DOOR_OUTER_MAT = "paint_belly"   # builder tag of the leg door's outer face (recoloured by livery.SURFACES)
LEG_DOOR_CORNER_R = 0.020           # radius of the door's aft top corner and of the step's aft corner (leg_door_face)
# Owner decision 2026-09-27 (leg-door tip rounding): the drawn pointed tip (chamfer -> 15 mm flat -> lower-edge arc) is
# one round of this radius, tangent to the forward chamfer and the lower-edge arc (leg_door_face), and the step's aft
# corner (x_aft, z_step[1]) gets LEG_DOOR_CORNER_R.  Sharp, they nicked the wing skin beside the cut-out by 2.8 / 1.3 mm
# at 96-99.5 % retraction (the marching-triangles cut chords a sharp slot corner; the 10 % sweep samples missed it);
# rounded, the slot corners follow them (bays.main_opening_sdf = the stowed face + DOOR_GAP) and fit_check 10 sweeps
# 90-100 % every 0.5 %: 0 crossings (the tip still nicked 0.2 mm at R 10, clear from R 15; the step corner 0.3 mm at
# R 10, clear from R 15).  The lowest point rises from the drawn WL 318 to 325; the drawn outline (leg_door_outline,
# the phantom on L4 detail B) is unchanged, the tyre scallop is not touched.
LEG_DOOR_TIP_R = 0.020
LEG_DOOR_BRACKET_MAT = "metal_dark"  # the door's two standoff brackets from the leg (the door assembly)


def _door_top_z(xs):
    """WL of the door's drawn (straight) top edge at stations xs."""
    d = LEG_DOOR
    t = (np.asarray(xs, float) - d["x_fwd"]) / (d["x_aft_top"] - d["x_fwd"])
    return d["z_top"][0] + (d["z_top"][1] - d["z_top"][0]) * t


def _door_fwd_x(zs):
    """Station of the door's (straight, slightly aft-leaning) forward edge at WL zs, extended above the drawn top."""
    d = LEG_DOOR
    t = (d["z_top"][0] - np.asarray(zs, float)) / (d["z_top"][0] - d["z_fwd_low"])
    return d["x_fwd"] + (d["x_fwd_low"] - d["x_fwd"]) * t


def leg_door_outline(n_arc=24):
    """DRAWN leg-door face (N, 2) in side projection (x, z), gear down, closed: forward edge, chamfer to the pointed
    tip, concave lower edge (circle arc), stepped aft edge (narrow lower part, diagonal, wide upper part), straight
    top edge just below the wing.  The model door is leg_door_face() (this face, scalloped round the tyre, with the
    hidden forward tab)."""
    d = LEG_DOOR
    (cx, cz), r = d["arc_c"], d["arc_r"]
    xa = np.linspace(d["arc_x0"], d["x_aft_low"], n_arc)
    arc = np.c_[xa, cz + np.sqrt(np.maximum(r * r - (xa - cx) ** 2, 0.0))]
    xs = np.linspace(d["x_aft_top"], d["x_fwd"], 16)
    top = np.c_[xs, _door_top_z(xs)]
    return np.vstack([[[d["x_fwd_low"], d["z_fwd_low"]], list(d["tip"])], arc,
                      [[d["x_aft_low"], d["z_step"][0]], [d["x_aft"], d["z_step"][1]]], top])


# ------------------------------------------------------------------------------------------ retraction geometry
def main_retract_matrix(sgn=1, frac=1.0):
    """4x4 pose of a main-gear unit (sgn +1 starboard, -1 port) at retraction fraction frac (0 down .. 1 up): rotation
    about the x axis through MAIN_TRUNNION, MAIN_RETRACT_DEG inboard (the part pivot's 'retract')."""
    T = MAIN_TRUNNION * [1, sgn, 1]
    return rotation_about((1.0, 0.0, 0.0), -sgn * np.radians(MAIN_RETRACT_DEG) * frac, T)


def retracted_wheel(side=1):
    """Main-wheel centre after the retraction (main_retract_matrix)."""
    M = main_retract_matrix(side)
    return M[:3, :3] @ (MAIN_AXLE * [1, side, 1]) + M[:3, 3]


def leg_door_offset(x, z, n_iter=8):
    """Lateral offset u (m, outboard of the leg plane BL MAIN_TRUNNION[1]) of the leg door's OUTER face at side-view
    point (x, z), gear down (starboard; port mirrored).  LD-1: the door is the wing lower skin carried down by the
    inverse retraction, so the retracted door is flush: u solves  z'(u) = wing lower WL(x, y'(u)) + LEG_DOOR_RECESS,
    (y', z') being the retracted point (rotation about x keeps x)."""
    T = MAIN_TRUNNION
    th = np.radians(MAIN_RETRACT_DEG)
    c, s = np.cos(th), np.sin(th)
    x, z = np.broadcast_arrays(np.asarray(x, float), np.asarray(z, float))
    v = z - T[2]
    u = np.full(x.shape, 0.08)
    for _ in range(n_iter):
        yp = T[1] + u * c + v * s
        zp = T[2] - u * s + v * c
        g = zp - (wing_z(x, yp, False) + LEG_DOOR_RECESS)
        u = u + g / (s + 0.12 * c)                  # d(g)/du = -(sin + skin slope * cos), slope ~0.12
    return u


def leg_door_bl(x, z):
    """Butt line of the model leg door's outer face at side-view point (x, z), gear down (starboard)."""
    return MAIN_TRUNNION[1] + leg_door_offset(x, z)


def leg_door_drawn_bl(z):
    """Butt line of the DRAWN front-view door line at WL z (BL 2,358 at the top edge -> 2,472 at the lowest point):
    the reference the model door departs from (LD-1)."""
    d = LEG_DOOR
    P = leg_door_outline()
    zmx, zmn = float(P[:, 1].max()), float(P[:, 1].min())
    return d["bl"][0] + (d["bl"][1] - d["bl"][0]) * (zmx - np.asarray(z, float)) / (zmx - zmn)


def leg_door_stowed(x, z, side=1):
    """Retracted plan point (x, y') and WL z' of the door's outer face at side-view point (x, z)."""
    x, z = np.broadcast_arrays(np.asarray(x, float), np.asarray(z, float))
    P = np.stack([x, MAIN_TRUNNION[1] + leg_door_offset(x, z), z], -1) * [1, side, 1]
    M = main_retract_matrix(side)
    return P @ M[:3, :3].T + M[:3, 3]


def _scallop_hits():
    """(x, z) where the tyre scallop meets the drawn lower-edge arc and the narrow part's aft edge."""
    d = LEG_DOOR
    A, rs = MAIN_AXLE[[0, 2]], d["scallop_r"]
    (cx, cz), r = d["arc_c"], d["arc_r"]
    arc_z = lambda x: cz + np.sqrt(max(r * r - (x - cx) ** 2, 0.0))       # noqa: E731
    f = lambda x: np.hypot(x - A[0], arc_z(x) - A[1]) - rs                # noqa: E731
    a, b = d["arc_x0"], d["x_aft_low"]
    if f(a) <= 0 or f(b) >= 0:
        raise ValueError("leg-door scallop does not cross the drawn lower edge once")
    for _ in range(60):
        m = 0.5 * (a + b)
        a, b = (m, b) if f(m) > 0 else (a, m)
    xi = 0.5 * (a + b)
    xj = d["x_aft_low"]
    zj = A[1] + np.sqrt(rs * rs - (xj - A[0]) ** 2)
    if zj >= d["z_step"][0]:
        raise ValueError("leg-door scallop reaches the step")
    return np.array([xi, arc_z(xi)]), np.array([xj, zj])


def _door_wing_line(xs):
    """WL of the wing lower surface at the door's plane (where the door passes the skin gear down), at stations xs."""
    xs = np.asarray(xs, float)
    z = np.full(xs.shape, 1.09)
    for _ in range(3):
        z = wing_z(xs, leg_door_bl(xs, z), False)
    return z


def leg_door_face(visible=False, n_arc=24, n_sc=28):
    """Model leg-door face (N, 2) in side projection (x, z), gear down, counter-clockwise: the drawn face
    (leg_door_outline) with LD-1's tyre scallop (the part inside LEG_DOOR['scallop_r'] about MAIN_AXLE cut away) and
    forward top tab (from the forward edge to STA tab[0] the door continues up through the skin slot to WL tab[1],
    hidden inside the wing with the gear down).  visible=True clips the tab at the wing lower surface: the face the
    side view shows."""
    d = LEG_DOOR
    A, rs = MAIN_AXLE[[0, 2]], d["scallop_r"]
    (cx, cz), r = d["arc_c"], d["arc_r"]
    Pi, Pj = _scallop_hits()
    tipf = _tip_fillet(LEG_DOOR_TIP_R)                   # the rounded tip (owner decision 2026-09-27)
    xa = np.linspace(tipf[-1, 0], Pi[0], n_arc)[1:]
    arc = np.c_[xa, cz + np.sqrt(np.maximum(r * r - (xa - cx) ** 2, 0.0))]
    ai = np.arctan2(Pi[1] - A[1], Pi[0] - A[0])
    aj = np.arctan2(Pj[1] - A[1], Pj[0] - A[0])
    ang = np.linspace(ai, aj, n_sc)[1:]
    sc = np.c_[A[0] + rs * np.cos(ang), A[1] + rs * np.sin(ang)]
    x_tab, z_tab = d["tab"]
    xs = np.linspace(d["x_aft_top"], x_tab, 14)
    top = np.c_[xs, _door_top_z(xs)]
    # aft top corner rounded (R LEG_DOOR_CORNER_R): the corner nearest the retraction axis swings into the skin
    # cut-out at ~45 deg, where a square corner would clip the cut-out's (mesh-chamfered) corner
    step_hi = np.array([d["x_aft"], d["z_step"][1]])
    fil = _fillet(step_hi, top[0], top[1], LEG_DOOR_CORNER_R)
    top = np.vstack([fil, top[1:]])
    # the step's aft corner rounded too (R LEG_DOOR_CORNER_R, owner decision 2026-09-27): sharp, it nicked the cut-out
    # by 1.3 mm at 96-98.5 % retraction
    step_lo = np.array([d["x_aft_low"], d["z_step"][0]])
    stepc = _fillet(step_lo, step_hi, fil[0], LEG_DOOR_CORNER_R)
    if visible:
        xw = np.linspace(x_tab, float(_door_fwd_x(1.09)), 8)
        zw = _door_wing_line(xw)
        for _ in range(3):                           # forward end on the forward edge
            xw[-1] = float(_door_fwd_x(zw[-1]))
            zw = _door_wing_line(xw)
        tab = np.c_[xw, zw]
    else:
        tab = np.array([[x_tab, z_tab], [float(_door_fwd_x(z_tab)), z_tab]])
    return np.vstack([[[d["x_fwd_low"], d["z_fwd_low"]]], tipf, arc, sc, [step_lo], stepc, top, tab])


def _tip_fillet(R, n=9):
    """Points (n, 2) of the rounded door tip: a circle of radius R tangent to the forward chamfer (fwd-low corner ->
    drawn tip) and externally to the concave lower-edge arc (LEG_DOOR arc_c / arc_r; the door lies outside that
    circle), from the chamfer tangent point to the arc tangent point.  It replaces the drawn pointed tip and the 15 mm
    flat after it (owner decision 2026-09-27)."""
    d = LEG_DOOR
    A0, B0 = np.array([d["x_fwd_low"], d["z_fwd_low"]]), np.array(d["tip"], float)
    C, rc = np.array(d["arc_c"], float), d["arc_r"]
    u = (B0 - A0) / np.linalg.norm(B0 - A0)
    nl = np.array([-u[1], u[0]])                          # left of the counter-clockwise outline = inside the door
    # centre O = A0 + s u + R nl with |O - C| = rc + R: s^2 + 2 s (w.u) + |w|^2 - (rc + R)^2 = 0, w = A0 + R nl - C
    w = A0 + R * nl - C
    bq, cq = float(w @ u), float(w @ w - (rc + R) ** 2)
    disc = bq * bq - cq
    if disc <= 0.0:
        raise ValueError("leg-door tip fillet: no circle tangent to the chamfer and the lower edge")
    s = min((-bq - np.sqrt(disc), -bq + np.sqrt(disc)), key=lambda t: abs(t - np.linalg.norm(B0 - A0)))
    if not 0.0 < s < np.linalg.norm(B0 - A0) + 0.05:
        raise ValueError("leg-door tip fillet: tangent point off the chamfer")
    O = A0 + s * u + R * nl
    T1, T2 = A0 + s * u, C + (O - C) * rc / (rc + R)
    a1, a2 = np.arctan2(*(T1 - O)[::-1]), np.arctan2(*(T2 - O)[::-1])
    a2 = a1 + (a2 - a1) % (2.0 * np.pi)                   # counter-clockwise about O (a convex corner)
    ang = np.linspace(a1, a2, n)
    return np.c_[O[0] + R * np.cos(ang), O[1] + R * np.sin(ang)]


def _fillet(a, c, b, r, n=7):
    """Points (n, 2) of a circular fillet of radius r replacing the corner c of the polyline a -> c -> b."""
    d1 = (c - a) / np.linalg.norm(c - a)
    d2 = (b - c) / np.linalg.norm(b - c)
    turn = np.arccos(np.clip(d1 @ d2, -1.0, 1.0))
    t = r * np.tan(0.5 * turn)
    p1, p2 = c - t * d1, c + t * d2
    nrm = np.array([-d1[1], d1[0]]) * np.sign(d1[0] * d2[1] - d1[1] * d2[0])     # towards the turn
    o = p1 + r * nrm
    a1, a2 = np.arctan2(*(p1 - o)[::-1]), np.arctan2(*(p2 - o)[::-1])
    a2 = a1 + (a2 - a1 + np.pi) % (2 * np.pi) - np.pi
    ang = np.linspace(a1, a2, n)
    return np.c_[o[0] + r * np.cos(ang), o[1] + r * np.sin(ang)]


def leg_door_front_line(visible=True, n=48):
    """Edge-on (front-view) line of the model leg door's outer face, starboard: (BL, WL) of its outermost point at each
    WL from the lowest point to the top of the (visible) face.  LD-1: ~BL 2,33-2,38, where the drawing has a plane
    leaning out from BL 2,358 to 2,472 (leg_door_drawn_bl)."""
    from cad import sdf2d
    P = leg_door_face(visible)
    xs = np.linspace(P[:, 0].min(), P[:, 0].max(), 240)
    out = []
    for z in np.linspace(P[:, 1].min(), P[:, 1].max(), n):
        k = sdf2d.polygon(xs, np.full(len(xs), z), P) <= 1e-4
        if k.any():
            out.append((float(leg_door_bl(xs[k], np.full(int(k.sum()), z)).max()), float(z)))
    return np.array(out)


def main_leg_skin_z(side=1):
    """WL where the main leg's axis passes the wing lower skin, gear down (the leg above it is hidden in the wing)."""
    T, L = MAIN_TRUNNION, MAIN_LINK_PIVOT
    z = T[2]
    for _ in range(6):
        x = T[0] + (L[0] - T[0]) * (T[2] - z) / (T[2] - L[2])
        z = float(wing_z(np.array([x]), np.array([T[1]]), False)[0])
    return z


def _densify(P, step):
    """Closed polygon P (N, 2) resampled so that no edge is longer than step (the vertices are kept)."""
    out = []
    for a, b in zip(P, np.roll(P, -1, 0)):
        n = max(1, int(np.ceil(np.linalg.norm(b - a) / step)))
        out.append(a + (b - a) * (np.arange(n) / n)[:, None])
    Q = np.vstack(out)
    keep = np.r_[True, np.linalg.norm(np.diff(Q, axis=0), axis=1) > 1e-9]
    return Q[keep]


def leg_door_footprint(side=1, step=0.010):
    """Plan footprint (x, y) of the retracted leg door (outer face): the skin area it closes (bays.leg_slot_sdf)."""
    P = _densify(leg_door_face(), step)
    S = leg_door_stowed(P[:, 0], P[:, 1], side)
    return S[:, :2]


def leg_door_retracted_drop(side=1):
    """(min, max) of wing lower WL - retracted door outer-face WL (m) over the door (sampled on its face): the flushness
    (LD-1: = LEG_DOOR_RECESS by construction, up to the Newton residual)."""
    from cad import sdf2d
    P = leg_door_face()
    X, Z = np.meshgrid(np.linspace(P[:, 0].min(), P[:, 0].max(), 40), np.linspace(P[:, 1].min(), P[:, 1].max(), 60))
    k = sdf2d.polygon(X.ravel(), Z.ravel(), P) < 0
    S = leg_door_stowed(X.ravel()[k], Z.ravel()[k], side)
    dz = wing_z(S[:, 0], S[:, 1], False) - S[:, 2]
    return float(dz.min()), float(dz.max())


def main_tyre_protrusion(side=1, mats=WH.TYRE_MATS):
    """Largest depth (m) of the retracted main tyre (mats: or other wheel parts, e.g. the hub fairing
    'hub_fairing') below the local wing lower surface (POH: ~1 in)."""
    M = main_retract_matrix(side)
    V = np.vstack([m.V for m, mat in WH.main_wheel(MAIN_AXLE * [1, side, 1], (0.0, 1.0, 0.0), side, parts=mats)])
    V = V @ M[:3, :3].T + M[:3, 3]
    return float((wing_z(V[:, 0], V[:, 1], False) - V[:, 2]).max())


from model.bays import NOSE_BAY, main_opening_sdf, main_bay_sdf, nose_bay_sdf


# ---------------------------------------------------------------------------
def wheel(center, axis, tyre, n=None, brake_side=0):
    """Wheel assembly about `axis` through `center` (kept for older callers): the model/wheels.py builders -- the main
    wheel (tyre MAIN_TYRE; brake_side = the inboard side, -1 for the starboard unit, +1 for port) or the nose wheel."""
    if tyre is MAIN_TYRE or float(tyre["R"]) == MAIN_TYRE["R"]:
        return WH.main_wheel(center, axis, -brake_side if brake_side else (1 if center[1] >= 0 else -1))
    return WH.nose_wheel(center, axis)


def _catmull(P, n_seg=6):
    """Catmull-Rom curve through the points P (m, 3), n_seg samples per span."""
    P = np.asarray(P, float)
    Q = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(1, len(Q) - 2):
        p0, p1, p2, p3 = Q[i - 1], Q[i], Q[i + 1], Q[i + 2]
        for t in np.linspace(0.0, 1.0, n_seg, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-1])
    return np.array(out)


def main_brake_line(sgn, C, aa, fy_s):
    """Brake line (flexible hose, wheels.MAIN_BRAKE line_d) from the radial inlet fitting on the brake's top lobe:
    out of the fitting, inboard clear of the rim flange, then up along the trailing arm's upper edge to the yoke;
    C: the arm's centre line from the link pivot to the axle (on its mid-plane s = fy_s), aa its half-depth there."""
    A = MAIN_AXLE * [1, sgn, 1]
    Mf = WH._frame(A, np.array([0.0, sgn, 0.0]))
    p0, u = WH.brake_fitting_local()
    loc = [p0, p0 + u * 0.004 + [0.0, -0.008, 0.0], p0 + u * 0.006 + [0.0, -0.022, 0.0]]
    pts = [Mf[:3, :3] @ q + Mf[:3, 3] for q in loc]
    L_ = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(C, axis=0), axis=1))]
    T_ = np.gradient(C, axis=0)
    T_ /= np.linalg.norm(T_, axis=1)[:, None]
    for t in (0.30, 0.58, 0.88):                        # fraction of the arm from the axle end
        i = int(np.argmin(np.abs(L_ - (1.0 - t) * L_[-1])))
        up = np.array([0.0, 0.0, 1.0]) - T_[i] * T_[i][2]
        q = C[i] + up / np.linalg.norm(up) * (aa[i] + 0.008)
        q[1] = A[1] + sgn * fy_s
        pts.append(q)
    return sweep_tube(_catmull(pts, 7), WH.MAIN_BRAKE["line_d"] / 2, n=8)


# main trailing arm (wheels review r1 F6: photos 3036 mx4 / mx5, 3008 130 inboard show a tubular swan-neck casting from
# the link-pivot yoke to the big axle boss, not a flat bar): a swept oval tube on the arm plane (s = -fy inboard of the
# wheel), bowed up by `bow` (fractions along the pivot -> axle chord, offsets normal to it) and tapering in depth
# (half-depth `a`, half-thickness `b`, pivot end -> axle end); the shock strut's chrome rod MAIN_SHOCK_ROD_R
MAIN_ARM = dict(fy=0.14, bow=((0.30, 0.022), (0.66, 0.014)), a=(0.031, 0.026), b=(0.021, 0.019), p=2.6)
MAIN_SHOCK_ROD_R = 0.0175


def main_arm_centre(sgn):
    """Centre line (m, 3) of the main trailing arm, side sgn, from the link-pivot yoke to the axle boss, and its
    half-depths aa (m,)."""
    A, L = MAIN_AXLE * [1, sgn, 1], MAIN_LINK_PIVOT * [1, sgn, 1]
    s = -sgn * MAIN_ARM["fy"]
    a, b = L + [0.0, s, 0.0], A + [0.0, s, 0.0]
    d = b - a
    ez = np.array([0.0, 0.0, 1.0]) - d / np.linalg.norm(d) * (d[2] / np.linalg.norm(d))
    ez /= np.linalg.norm(ez)
    pts = [a] + [a + f * d + h * ez for f, h in MAIN_ARM["bow"]] + [b]
    C = catmull_path(pts, 30)
    u = np.linspace(0.0, 1.0, len(C))
    return C, MAIN_ARM["a"][0] + (MAIN_ARM["a"][1] - MAIN_ARM["a"][0]) * u


def build_main(parts, side):
    sgn = 1 if side == "R" else -1
    S = np.array([1, sgn, 1.0])
    T = MAIN_TRUNNION * S
    A = MAIN_AXLE * S
    L = MAIN_LINK_PIVOT * S                            # trailing-link pivot
    yax = np.array([0, 1.0, 0])
    struct = []
    # trunnion + leg
    struct.append(cylinder(T - [0.07, 0, 0], T + [0.07, 0, 0], 0.045, n=20))        # trunnion pin (in the wing)
    ll = float(np.linalg.norm(L - T)) + 0.042                                        # leg: trunnion -> past the link pivot
    struct.append(revolve([(0, MAIN_LEG_R[0]), (ll - 0.02, MAIN_LEG_R[1]), (ll, 0.0)], n=24, axis_origin=T,
                          axis_dir=(L - T) / np.linalg.norm(L - T)))
    # yoke + trailing arm on the INBOARD side of the wheel only (it lies above the wheel when retracted inward;
    # an outboard arm would hang ~0.1 m below the wing), axle cantilevered from it
    fy = MAIN_ARM["fy"]
    struct.append(cylinder(L - sgn * fy * yax, L - sgn * 0.03 * yax, 0.036, n=16))
    struct.append(superellipsoid(L - sgn * fy * yax, (0.036, 0.036, 0.036), (1, 1), 10, 16))   # yoke end round the arm
    C, aa = main_arm_centre(sgn)                                # swan-neck tube, pivot yoke -> axle boss
    u = np.linspace(0.0, 1.0, len(C))
    bb = MAIN_ARM["b"][0] + (MAIN_ARM["b"][1] - MAIN_ARM["b"][0]) * u
    struct.append(sweep_section(C, aa, bb, n_sec=18, fore=(0.0, 0.0, 1.0), p=MAIN_ARM["p"]))
    brake_line = main_brake_line(sgn, C, aa, -fy)
    struct.append(cylinder(A - sgn * fy * yax, A + sgn * 0.05 * yax, 0.026, n=16))      # axle
    struct.append(WH.main_axle_boss(A, yax, sgn))              # the arm's axle boss, open bore inboard (L4W)
    # shock absorber on the inboard side, over the trailing arm (fy), so it stows inside the wing above the leg
    s_in = -sgn * 0.15
    S1 = np.array([MAIN_SHOCK[0][0], T[1] + s_in, MAIN_SHOCK[0][1]])
    S2 = np.array([MAIN_SHOCK[1][0], T[1] + s_in * 0.95, MAIN_SHOCK[1][1]])
    mid = S1 + 0.55 * (S2 - S1)
    shock_body = cylinder(S1, mid, 0.036, n=18)
    shock_rod = cylinder(mid - 0.05 * (S2 - S1), S2, MAIN_SHOCK_ROD_R, n=14)
    # the shock's lower eye sits on the trailing arm just above the axle boss (photos 3036 / 3008 inboard): a lug from
    # the rod end down onto the arm, within the arm's thickness (the rev-A bracket ran 0.135 m outboard into the wheel)
    z_arm = float(np.interp(S2[0], C[:, 0], C[:, 2]))           # arm centre line under S2 (C runs aft)
    lugs = [cylinder(S1 - [0, 0.03 * sgn, 0], S1 + [0, 0.03 * sgn, 0], 0.03, n=12),
            box(np.array([S2[0], S2[1], 0.5 * (S2[2] + 0.012 + z_arm)]), (0.040, 0.030, S2[2] + 0.012 - z_arm)),
            cylinder(S2 - [0, 0.019, 0], S2 + [0, 0.019, 0], 0.019, n=14),
            box(np.array([MAIN_SHOCK[0][0], T[1] + s_in * 0.5, MAIN_SHOCK[0][1]]), (0.06, abs(s_in), 0.05))]
    wh = WH.main_wheel(A, yax, sgn)          # tyre, wheel halves, hub fairing, brake (model/wheels.py, sheet L4W)

    # leg door (LEG_DOOR / leg_door_face, sheet L4, LD-1): a piece of the wing lower skin carried by the leg (flush
    # when retracted), scalloped round the tyre, on two standoff brackets from the leg; it retracts rigidly with the leg
    ang_retract = np.radians(MAIN_RETRACT_DEG) * (-sgn)          # about +x
    door_out, door_in = leg_door_mesh(sgn, split=True)     # outer face / inner face + rim
    brackets = []
    for zb in (0.98, 0.62):
        a = T + (L - T) * (T[2] - zb) / (T[2] - L[2])
        b = np.array([a[0], sgn * (float(leg_door_bl(a[0], zb)) - LEG_DOOR_T - 0.001), zb])
        brackets.append(cylinder(a, b, 0.012, n=10))

    gp = Part(f"gear_main_{side}", f"{'Right' if sgn > 0 else 'Left'} main gear (trailing link)", "gear",
              pivot=dict(origin=T.tolist(), axis=[1.0, 0, 0], kind="gear", retract=float(np.degrees(ang_retract))),
              explode=(0, sgn * 0.6, -0.7), group="Landing gear",
              material_note="Trailing link, hydraulic shock strut, electromechanical actuator",
              info={"tyre": f"{WH.MAIN_TYRE_ENV['size'].replace('x', ' x ')}, "
                            f"{WH.MAIN_TYRE_SEC['pressure']:.0f} psi", "track": "4,530 mm",
                    "retraction": f"{MAIN_RETRACT_DEG:.0f} deg inward; tyre protrudes ~1 in (POH)",
                    "door": "single leg-mounted door, flush with the wing skin when retracted"})
    lugs.append(main_brace_lug(sgn))                                             # side-brace lug B0 (MV2-02)
    lamp_body, lamp_face = main_leg_lamp(sgn)
    lugs.append(lamp_body)
    gp.add(Mesh.merge(struct + lugs), "gear_leg").add(Mesh.merge([shock_body]), "gear_leg").add(shock_rod, "chrome")
    for m, mat in wh:
        gp.add(m, mat)
    gp.add(brake_line, "black")
    # the outer face carries the wing's lower-surface paint (LD-1: it IS the lower skin, flush when retracted), the
    # inner face and the rim the leg door's own paint (livery.SURFACES main_gear_door / main_gear_door_inner)
    gp.add(door_out, LEG_DOOR_OUTER_MAT).add(door_in, "paint_white").add(Mesh.merge(brackets), LEG_DOOR_BRACKET_MAT)
    for m, mat in lamp_face:
        gp.add(m, mat)
    parts[gp.id] = gp


# landing / taxi lamp on each main leg (VQA r1 SHP-07: photos 130 / 188, a round ~0.12 m LED lamp on the forward face of
# the port main leg at about the brace-lug height; the starboard leg carries its twin): a short housing on a bracket
# ahead of the leg axis at WL MAIN_LAMP['z'], lens facing forward; it is part of the gear node, so it retracts with it
MAIN_LAMP = dict(z=0.80, r=0.055, depth=0.024, standoff=0.004)   # (a deeper housing crosses the bay front edge stowing)


def led_lamp_face(front, d, r, n_ring=6):
    """Front of a round LED lamp at `front` facing unit direction d, outer radius r (VQA r2 SHP2-05: photos 130 / 188
    show a bright bezel round a dark face with a ring of LED reflectors, not a plain lens): returns
    [(mesh, material)] -- polished bezel ring, black face, LED reflector domes (a centre one + n_ring round it), a thin
    clear lens in front."""
    d = np.asarray(d, float) / np.linalg.norm(d)
    e1 = np.cross(d, [0.0, 0.0, 1.0])
    if np.linalg.norm(e1) < 1e-6:
        e1 = np.cross(d, [0.0, 1.0, 0.0])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(d, e1)
    rb = 0.16 * r                                           # bezel width
    bezel = revolve([(0.0, r), (0.004, r), (0.006, r - 0.35 * rb), (0.004, r - rb), (0.0, r - rb)], n=36,
                    axis_origin=front, axis_dir=d)
    face = revolve([(0.0015, 0.0), (0.0015, r - rb + 0.001)], n=36, axis_origin=front, axis_dir=d)
    rl = 0.20 * r
    cen = [np.zeros(2)] + [0.52 * (r - rb) * np.array([np.cos(a), np.sin(a)])
                           for a in np.linspace(0, 2 * np.pi, n_ring, endpoint=False)]
    leds = Mesh.merge([superellipsoid(front + d * 0.002 + c[0] * e1 + c[1] * e2, (0.004, rl, rl), (1, 1), 6, 14,
                                      R=np.stack([d, e1, e2], 1)) for c in cen])
    lens = revolve([(0.0065, 0.0), (0.0065, r - rb)], n=36, axis_origin=front, axis_dir=d)
    return [(bezel, "chrome"), (face, "black"), (leds, "chrome"), (lens, "lens")]


def main_leg_lamp(sgn):
    """(housing + bracket mesh, [(face mesh, material)]) of the leg lamp on main gear side sgn (gear down)."""
    T, Lp = MAIN_TRUNNION * [1, sgn, 1], MAIN_LINK_PIVOT * [1, sgn, 1]
    q = MAIN_LAMP
    c = T + (Lp - T) * (T[2] - q["z"]) / (T[2] - Lp[2])                 # leg axis at the lamp height
    rl = MAIN_LEG_R[0] + (MAIN_LEG_R[1] - MAIN_LEG_R[0]) * (T[2] - q["z"]) / (T[2] - Lp[2])
    back = c - [rl + q["standoff"], 0.0, 0.0]
    front = back - [q["depth"] - 0.008, 0.0, 0.0]
    body = Mesh.merge([cylinder(back, front, q["r"], n=28),
                       cylinder(c - [rl - 0.005, 0, 0], back, 0.016, n=10)])       # housing + bracket
    return body, led_lamp_face(front, (-1.0, 0.0, 0.0), q["r"])



def wing_lower_patch(x0, x1, y0, y1, n=18):
    """Sample the (right) wing lower surface over a plan-view rectangle."""
    ys = np.linspace(y0, y1, n)
    rows = []
    xs_all = np.linspace(x0, x1, n)
    for y in ys:
        sec = W.section_at(y)
        xc = (xs_all - sec.le[0]) / sec.chord
        rows.append(sec.lower(np.clip(xc, 0, 1)))
    P = np.array(rows)
    m = grid_surface(P)
    if m.N[:, 2].mean() > 0:
        m = m.flipped()
    return m


def leg_door_mesh(sgn, step=0.015, split=False):
    """Leg door, gear down (LD-1): the model face leg_door_face() (side view) with its outer face on the flush surface
    leg_door_bl(x, z) (the wing lower skin carried down by the inverse retraction), LEG_DOOR_T thick inboard (towards
    the leg; up into the wing when retracted); starboard for sgn = +1.  The face is triangulated with its exact outline
    (boundary resampled at 0.8 step, interior grid points at least 0.5 step inside, Delaunay, triangles kept by
    centroid) so the pointed tip and the corners stay sharp."""
    from scipy.spatial import Delaunay
    from cad import sdf2d
    from cad.mesh import boundary_loops
    P = leg_door_face()
    B = _densify(P, 0.8 * step)
    X, Z = np.meshgrid(np.arange(P[:, 0].min(), P[:, 0].max(), step), np.arange(P[:, 1].min(), P[:, 1].max(), step))
    Q = np.c_[X.ravel(), Z.ravel()]
    Q = Q[sdf2d.polygon(Q[:, 0], Q[:, 1], P) < -0.5 * step]
    pts = np.vstack([B, Q])
    tri = Delaunay(pts).simplices
    T3 = pts[tri]
    area = 0.5 * np.abs((T3[:, 1, 0] - T3[:, 0, 0]) * (T3[:, 2, 1] - T3[:, 0, 1]) -
                        (T3[:, 1, 1] - T3[:, 0, 1]) * (T3[:, 2, 0] - T3[:, 0, 0]))
    cen = T3.mean(1)
    tri = tri[(sdf2d.polygon(cen[:, 0], cen[:, 1], P) < 0) & (area > 1e-10)]   # inside, no collinear slivers
    V = np.c_[pts[:, 0], leg_door_bl(pts[:, 0], pts[:, 1]), pts[:, 1]]
    outer = Mesh(V, tri)
    if outer.face_normals()[:, 1].mean() < 0:              # outer face points outboard (+y)
        outer = outer.flipped()
    outer.compute_normals()
    loops = boundary_loops(outer)
    if len(loops) != 1:
        raise RuntimeError("leg door face triangulation is not a single patch")
    # inner face LEG_DOOR_T inboard, bevelled along the swing: below the trunnion each point's inner partner is the
    # point rotated further along the retraction (by alpha = T / its depth below the trunnion, <= 0.25 rad), so the
    # door's edges that rise into the skin cut-out from below (above all the top edge near the trunnion, which
    # arrives at ~45 deg) follow their own arc instead of sweeping a square edge through the skin beside the cut-out;
    # the rest of the thickness (points near / above the trunnion, which arrive from inside the wing) is a normal offset
    T = MAIN_TRUNNION
    v = V[:, 2] - T[2]
    alpha = np.where(v < 0, np.minimum(LEG_DOOR_T / np.maximum(-v, 1e-9), 0.25), 0.0)
    ca, sa = np.cos(alpha), np.sin(alpha)
    dy, dz = V[:, 1] - T[1], v
    Vr = np.c_[V[:, 0], T[1] + dy * ca + dz * sa, T[2] - dy * sa + dz * ca]      # rotated by -alpha about +x
    depth = np.einsum("ij,ij->i", V - Vr, outer.N)
    Vin = Vr - np.maximum(LEG_DOOR_T - depth, 0.0)[:, None] * outer.N
    inner = Mesh(Vin, outer.F[:, ::-1].copy())
    lp = loops[0]
    nv = len(V)
    a, b = lp, np.roll(lp, -1)
    rim = Mesh(np.vstack([V, Vin]), np.vstack([np.stack([a, b, b + nv], 1), np.stack([a, b + nv, a + nv], 1)]))
    c = 0.5 * (V[lp].mean(0) + Vin[lp].mean(0))
    rim = rim.compact() if hasattr(rim, "compact") else rim
    if np.mean(np.sum((rim.V[rim.F].mean(1) - c) * rim.face_normals(), 1)) < 0:
        rim = rim.flipped()
    fn = rim.face_normals()                                  # crisp rim normals
    N = np.zeros_like(rim.V)
    for k in range(3):
        np.add.at(N, rim.F[:, k], fn)
    rim.N = N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)
    if split:                   # (outer face, inner face + rim): VQA r3 RQ3-07, the outer face is the wing lower skin
        pieces = (outer, Mesh.merge([inner, rim]))
        return tuple(m if sgn > 0 else m.mirrored_y() for m in pieces)
    door = Mesh.merge([outer, inner, rim])
    return door if sgn > 0 else door.mirrored_y()


def catmull_path(pts, n_path=28):
    """Catmull-Rom curve through pts, about n_path samples in all."""
    P = np.asarray(pts, float)
    Q = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    seg = []
    for i in range(1, len(Q) - 2):
        p0, p1, p2, p3 = Q[i - 1], Q[i], Q[i + 1], Q[i + 2]
        for t in np.linspace(0.0, 1.0, max(3, n_path // (len(P) - 1)), endpoint=False):
            t2, t3 = t * t, t * t * t
            seg.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    seg.append(P[-1])
    return np.array(seg)


def sweep_section(C, aa, bb, n_sec=16, fore=(1.0, 0.0, 0.0), p=2.0, caps=True):
    """Solid swept along the centre line C (m, 3): a superellipse section (exponent p: 2 = ellipse, larger = a rounded
    rectangle, as a casting) with half-axis aa along the fore-aft direction `fore` (projected normal to the curve) and
    bb across it; aa / bb scalars or one value per point of C; capped ends."""
    C = np.asarray(C, float)
    T = np.gradient(C, axis=0)
    T /= np.linalg.norm(T, axis=1)[:, None]
    aa = np.broadcast_to(np.asarray(aa, float), (len(C),))
    bb = np.broadcast_to(np.asarray(bb, float), (len(C),))
    ph = np.linspace(0, 2 * np.pi, n_sec, endpoint=False)
    ce, se = np.cos(ph), np.sin(ph)
    ce, se = np.sign(ce) * np.abs(ce) ** (2.0 / p), np.sign(se) * np.abs(se) ** (2.0 / p)
    rows = []
    f = np.asarray(fore, float)
    for c, t, ai, bi in zip(C, T, aa, bb):
        ea = f - t * (f @ t)
        ea /= np.linalg.norm(ea)
        eb = np.cross(t, ea)
        rows.append(c + ai * ce[:, None] * ea + bi * se[:, None] * eb)
    R = np.array(rows)
    m = grid_surface(R, close_v=True)
    cen = R.mean(1)
    if np.mean(np.sum((m.V - np.repeat(cen, n_sec, 0)) * m.N, 1)) < 0:
        m = m.flipped()
    if not caps:
        return m
    return Mesh.merge([m, cap_ring(R[0], -T[0]), cap_ring(R[-1], T[-1])])


def swept_arm(pts, a, b, n_path=28, n_sec=16, fore=(1.0, 0.0, 0.0), p=2.0):
    """Smooth tapered arm: a Catmull-Rom curve through pts with a superellipse section (sweep_section), half-axis a(t)
    along the fore-aft direction `fore` and b(t) across it (a, b: (start, end), linear in t); capped."""
    C = catmull_path(pts, n_path)
    u = np.linspace(0.0, 1.0, len(C))
    return sweep_section(C, a[0] + (a[1] - a[0]) * u, b[0] + (b[1] - b[0]) * u, n_sec, fore, p)


# nose-gear fork (wheels review r1 F3; r2 F1 / F2; photos 3001 / 3036 head-on, 3036 mx4, 3008 188 / 130 / 0517): an
# inverted-U YOKE of two slim arms, one each side of the tyre, whose inner edge is ONE round arch over the tyre crown
# (apex wheels.NOSE_AXLE `arch` above the free crown; the r1 yoke was a square portal: a flat beam on 40 mm corners), the
# band thickening outward toward the crown (the arms flare into it), under a tapered crown SADDLE on the piston bottom
# whose front is chamfered down to the band and carries the lower torque-link lug (r1: a rectangular block on a
# rectangular bridge).
# Front view (s across, r up from the axle), sheet L4W: arms' inner / outer faces +-fork_in / fork_out above the axle
# bosses (the bosses step in to boss_in at the hub ends), straight up to the springing r_c; above it both edges are
# superellipse quarter-arcs |s / a|^p + |(r - r_c) / h|^p = 1: the inner one with a = fork_in, h = arch_h (3001 head-on
# zoom, 2296 px/m: arch height 0.076 = 0.85 x the half-span, the edge fits p 3.1 -- a semicircle is 2, the r1 portal ~8),
# the outer one with a = fork_out, h = arch_h + 2 top_t, arch_po (boxier: the arms' outer faces stay vertical longer and
# the band is ~37 mm deep on the diagonals, 30 on the arms, 28 at the apex).  Fore-aft half-width arm_w at the axle / at
# the crown (3036 mx4 side view: a 42-48 mm strap; r1's 58-92 mm read as a paddle); rounded-rectangle section (a
# casting), the arms leaning with the axle -> crown line.
# Saddle: sections (r above the axle, x of its front face / back face from the piston axis, half-width across) lofted
# bottom -> waist -> top: the bottom buried in the band, the front chamfered 34 deg from the band up to the waist (3008
# 188 / 3036 mx4), near-vertical above; 2 cadmium bolts on each sloped side face.  Torque-link lug (a clevis boss along
# y) at NOSE_TORQUE_LUG from the piston bottom, where the lower torque link ends.  Dark marks on each arm's outer face
# (3036 mx4 / 188; plain, no lettering): a small round hole, a slot and a placard (kind, r above the axle, fore-aft
# half-size, half-height).
NOSE_YOKE = dict(arm_w=(0.021, 0.026), arch_h=0.076, arch_p=3.1, top_t=0.014, arch_po=3.6, sec_p=5.0, boss_r=0.031,
                 saddle=((0.262, -0.024, 0.024, 0.074), (0.292, -0.044, 0.036, 0.061), (0.341, -0.046, 0.040, 0.046)),
                 saddle_p=4.0, crown_bolts=((-0.022, 0.318), (0.022, 0.318)),
                 marks=(("hole", 0.212, 0.0045, 0.0045), ("slot", 0.165, 0.0035, 0.008),
                        ("plate", 0.100, 0.0085, 0.013)))
NOSE_TORQUE_LUG = (-0.050, 0.030)            # lower torque-link pin from the piston bottom NOSE_FORK: (x, z)
NOSE_FORK_SIDES = (-1, 1)                    # both arms (sheet L4W check table)
# VQA r3: the lamp is ~0.11 m across in 188 / 130 (60 px on the 250 px tyre of 188): r 0.045 -> 0.055
NOSE_LAMP = dict(frac=0.45, fwd=(0.060, 0.098), r=0.055)     # on the strut: fraction P -> fork, housing x offsets, radius


def nose_yoke_frame():
    """(fork_in, fork_out, r_c, arch_h): the arms' inner / outer faces, the springing height above the axle (the inner
    arch's apex r_c + arch_h = free tyre R + arch) and the inner arch height."""
    ax = WH.NOSE_AXLE
    h = float(NOSE_YOKE["arch_h"])
    r_c = float(WH.NOSE_TYRE_ENV["R"]) + ax["arch"] - h
    return float(ax["fork_in"]), float(ax["fork_out"]), r_c, h


def _sarc(a, h, p, r_c, n):
    """Superellipse half-arc from (-a, r_c) over (0, r_c + h) to (a, r_c), n points (the parameter angle phi from
    180 to 0 deg): s = a sgn(cos) |cos|^(2/p), r = r_c + h |sin|^(2/p)."""
    ph = np.radians(np.linspace(180.0, 0.0, n))
    c, s_ = np.cos(ph), np.sin(ph)
    return np.c_[a * np.sign(c) * np.abs(c) ** (2.0 / p), r_c + h * np.abs(s_) ** (2.0 / p)]


def nose_yoke_contours(n_arc=48):
    """Exact front-view contours of the yoke band (s, r about the axle), port axle end -> starboard axle end: inner
    (the arms' inner faces and the round arch over the tyre) and outer (arms' outer faces flaring into the crown)."""
    fi, fo, r_c, h = nose_yoke_frame()
    yk = NOSE_YOKE
    inner = np.vstack([[[-fi, 0.0]], _sarc(fi, h, yk["arch_p"], r_c, n_arc), [[fi, 0.0]]])
    outer = np.vstack([[[-fo, 0.0]], _sarc(fo, h + 2 * yk["top_t"], yk["arch_po"], r_c, n_arc), [[fo, 0.0]]])
    return inner, outer


def nose_yoke_centre(n_arm=10, n_arc=28):
    """Centre line of the nose-fork yoke in the front view: (s, r, t_half) from the port arm's axle end up, over the
    tyre and down to the starboard axle end (s across, r above the axle; the midpoints of the inner / outer contours at
    the same superellipse parameter, t_half = half their distance), and the line's top r."""
    fi, fo, r_c, h = nose_yoke_frame()
    yk = NOSE_YOKE
    I = _sarc(fi, h, yk["arch_p"], r_c, n_arc + 2)[1:-1]
    O = _sarc(fo, h + 2 * yk["top_t"], yk["arch_po"], r_c, n_arc + 2)[1:-1]
    sm, ta = 0.5 * (fi + fo), 0.5 * (fo - fi)
    arm = np.c_[np.full(n_arm, -sm), np.linspace(0.0, r_c, n_arm)]
    P = np.vstack([arm, 0.5 * (I + O), (arm * [-1, 1])[::-1]])
    t = np.r_[np.full(n_arm, ta), 0.5 * np.linalg.norm(O - I, axis=1), np.full(n_arm, ta)]
    return P, t, float(P[:, 1].max())


def nose_saddle_sections():
    """Saddle sections (r above the axle, x front, x back relative to the piston axis at that height, half-width
    across), bottom -> top (NOSE_YOKE saddle)."""
    return [tuple(map(float, q)) for q in NOSE_YOKE["saddle"]]


def _saddle_ring(A, lean, r, xf, xb, hy, p, n=32):
    """One saddle section at r above the axle A: a superellipse (exponent p) from x = xf to xb about the leaning piston
    axis (A.x + lean r) and +-hy across."""
    th = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
    c, s_ = np.cos(th), np.sin(th)
    ce, se = np.sign(c) * np.abs(c) ** (2.0 / p), np.sign(s_) * np.abs(s_) ** (2.0 / p)
    xc, a = 0.5 * (xf + xb), 0.5 * (xb - xf)
    return np.c_[A[0] + lean * r + xc + a * ce, A[1] + hy * se, np.full(n, A[2] + r)]


def nose_saddle_meshes():
    """Crown saddle (model coordinates, gear down): the NOSE_YOKE sections lofted in two ruled bands (the chamfer
    band's edge crisp), capped; the torque-link lug; the crown-bolt heads on the sloped side faces.
    (saddle + lug mesh, bolt heads)."""
    A = NOSE_AXLE
    cr = NOSE_FORK - A
    lean = cr[0] / cr[2]
    p = NOSE_YOKE["saddle_p"]
    S = nose_saddle_sections()
    rings = [_saddle_ring(A, lean, *q, p) for q in S]
    out = []
    for r0, r1 in zip(rings[:-1], rings[1:]):
        m = grid_surface(np.stack([r0, r1]), close_v=True)
        c = 0.5 * (r0.mean(0) + r1.mean(0))
        if np.mean(np.sum((m.V - c) * m.N, 1)) < 0:
            m = m.flipped()
        out.append(m)
    out += [cap_ring(rings[0], (0.0, 0.0, -1.0)), cap_ring(rings[-1], (0.0, 0.0, 1.0))]
    # torque-link lug: a clevis boss along y at the lower torque link's pin, on a tab from the saddle's front top
    lx, lz = NOSE_TORQUE_LUG
    k2 = NOSE_FORK + [lx, 0.0, lz]
    out.append(cylinder(k2 - [0, 0.015, 0], k2 + [0, 0.015, 0], 0.013, n=14))
    out.append(superellipsoid(k2 + [0.010, 0.0, -0.008], (0.016, 0.011, 0.012), (0.3, 0.3), 8, 16))
    # crown bolts on the side faces (the section's s at the bolt's x, interpolated between the sections)
    bolts = []
    rs = np.array([q[0] for q in S])
    for dx, rz in NOSE_YOKE["crown_bolts"]:
        xf, xb, hy = (float(np.interp(rz, rs, [q[k] for q in S])) for k in (1, 2, 3))
        a = 0.5 * (xb - xf)
        u = abs((dx - 0.5 * (xf + xb)) / a)
        sy = hy * max(1.0 - u ** p, 0.0) ** (1.0 / p) - 0.001
        x = A[0] + rz * lean + dx
        for sg in (-1.0, 1.0):
            c = np.array([x, sg * sy, A[2] + rz])
            bolts.append(cylinder(c, c + [0, sg * 0.0065, 0], 0.0075, n=6))
    return Mesh.merge(out), Mesh.merge(bolts)


def nose_arm_marks():
    """Dark marks on each fork arm's outer face (NOSE_YOKE marks, photos 3036 mx4 / 188): a round hole, a slot and a
    placard, 0.4 mm proud of the face, following the arm's lean.  Mesh (material 'black')."""
    A = NOSE_AXLE
    cr = NOSE_FORK - A
    lean = cr[0] / cr[2]
    d = np.array([lean, 0.0, 1.0]) / np.hypot(lean, 1.0)             # up the arm (x, z)
    fwd = np.array([d[2], 0.0, -d[0]])
    so = WH.NOSE_AXLE["fork_out"] + 0.0004
    out = []
    for kind, r, hw, hh in NOSE_YOKE["marks"]:
        c0 = A + np.array([r * lean, 0.0, r])
        for sg in (-1.0, 1.0):
            c = c0 + [0.0, sg * so, 0.0]
            if kind == "hole":
                ring = np.array([c + hw * (math.cos(a) * fwd + math.sin(a) * d) for a in np.linspace(0, 2 * np.pi, 14,
                                                                                                 endpoint=False)])
            else:
                ring = np.array([c + hw * fwd * i + hh * d * j for i, j in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
            out.append(cap_ring(ring, (0.0, sg, 0.0)))
    return Mesh.merge(out)


def nose_yoke_meshes():
    """Two-arm nose-fork yoke (gear down, model coordinates): the swept band of nose_yoke_centre() (rounded-rectangle
    section, fore-aft half-width NOSE_YOKE arm_w tapering from the crown to the axle, the arms leaning with the axle ->
    crown line), the axle bosses (boss_in .. fork_out) and the crown saddle with the torque-link lug.
    (meshes, crown-bolt heads, arm marks)."""
    A, yk = NOSE_AXLE, NOSE_YOKE
    cr = NOSE_FORK - A                                          # crown (piston bottom) from the axle
    P, t, r_top = nose_yoke_centre()
    lean = cr[0] / cr[2]
    C = np.c_[A[0] + P[:, 1] * lean, A[1] + P[:, 0], A[2] + P[:, 1]]
    w0, w1 = yk["arm_w"]
    aa = w0 + (w1 - w0) * np.clip(P[:, 1] / r_top, 0.0, 1.0)
    out = [sweep_section(C, aa, t, n_sec=20, p=yk["sec_p"])]
    ax = WH.NOSE_AXLE
    for sg in (-1.0, 1.0):                                      # axle bosses round the arm ends
        out.append(cylinder(A + [0, sg * ax["boss_in"], 0], A + [0, sg * ax["fork_out"], 0], yk["boss_r"], n=20))
    saddle, bolts = nose_saddle_meshes()
    out.append(saddle)
    return out, bolts, nose_arm_marks()


def nose_axle_meshes():
    """Nose axle through both fork arms, and on each arm's outer face a tear-drop lock plate (tip up the arm) under a
    hex axle nut, the threaded axle end with its dark bore (wheels.NOSE_AXLE nut_af / nut_s / lock_plate; photos
    3036 mx4 nose-hub zoom, 3008 188): ([axle], [nuts, plates])."""
    A, ax = NOSE_AXLE, WH.NOSE_AXLE
    fo, (n0, n1) = ax["fork_out"], ax["nut_s"]
    lt = ax["lock_t"]
    axle = [cylinder(A - [0, fo, 0], A + [0, fo, 0], ax["r"], n=14)]
    cr = NOSE_FORK - A
    ud = np.array([cr[0], cr[2]]) / np.hypot(cr[0], cr[2])     # up the arm (x, z)
    rc = ax["nut_af"] / 2 + 0.004
    th = np.linspace(0.0, 2 * np.pi, 33)[:-1]
    ring = np.c_[rc * np.cos(th), rc * np.sin(th)]
    tip = ud * ax["lock_plate"]
    from scipy.spatial import ConvexHull
    Q = np.vstack([ring, tip])
    Q = Q[ConvexHull(Q).vertices] + [A[0], A[2]]
    dark = []
    for sg in (-1.0, 1.0):
        dark.append(WH._prism(Q, sg * n0, sg * (n0 + lt)))                         # lock plate
        dark.append(WH._prism(WH.hexagon((A[0], A[2]), ax["nut_af"], 90.0), sg * (n0 + lt), sg * n1))   # nut
        e0, e1 = sg * n1, sg * (n1 + 0.003)
        dark.append(cylinder(A + [0, e0, 0], A + [0, e1, 0], ax["thread_r"], n=12, cap=False))    # threaded end
        dark.append(revolve([(0.0, ax["thread_r"]), (0.0, 0.0065)], n=12, axis_origin=A + [0, e1, 0],
                            axis_dir=(0.0, sg, 0.0)))                                            # end face ring
        dark.append(revolve([(0.0, 0.0065), (-0.006, 0.0065), (-0.006, 0.0)], n=12, axis_origin=A + [0, e1, 0],
                            axis_dir=(0.0, sg, 0.0)))                                            # bore
    return axle, dark


def build_nose(parts):
    P = NOSE_PIVOT
    A = NOSE_AXLE
    yax = np.array([0, 1.0, 0])
    low = NOSE_FORK.copy()                      # piston bottom / fork crown
    u = (low - P) / np.linalg.norm(low - P)
    struct = []
    struct.append(cylinder(P - 0.12 * yax, P + 0.12 * yax, 0.035, n=16))           # trunnion
    upper_end = P + 0.62 * (low - P)
    struct.append(cylinder(P, upper_end, 0.052, n=24))                              # oleo cylinder
    collar = cylinder(P + 0.30 * (low - P), P + 0.34 * (low - P), 0.066, n=24)      # steering collar
    piston = cylinder(upper_end - 0.04 * u, low, 0.036, n=20)
    yoke, crown_bolts, holes = nose_yoke_meshes()           # two-arm yoke + crown saddle (NOSE_YOKE, sheet L4W)
    struct += yoke
    ax_parts, ax_dark = nose_axle_meshes()                  # axle, hex nuts + tear-drop lock plates outside the arms
    struct += ax_parts
    # torque links (scissor) in front of the strut
    k1 = P + 0.56 * (low - P) + [-0.055, 0, 0]
    k2 = low + [NOSE_TORQUE_LUG[0], 0, NOSE_TORQUE_LUG[1]]      # the saddle's torque-link lug
    knee = 0.5 * (k1 + k2) + [-0.09, 0, 0]
    for a, b in ((k1, knee), (knee, k2)):
        struct.append(cylinder(a, b, 0.014, n=10))
    # taxi / landing light on the strut: housing + LED face (led_lamp_face; the rev r1 lamp was a plain lens puck)
    q = NOSE_LAMP
    lc = P + q["frac"] * (low - P)
    lamp_house = cylinder(lc - [q["fwd"][0], 0, 0], lc - [q["fwd"][1], 0, 0], q["r"], n=24)
    lamp_face = led_lamp_face(lc - [q["fwd"][1], 0, 0], (-1.0, 0.0, 0.0), q["r"])
    wh = WH.nose_wheel(A, yax)               # tyre, white split-hub wheel, tie bolts, valve (model/wheels.py)
    ang = NOSE_RETRACT_DEG
    gp = Part("gear_nose", "Nose gear (steerable, retracts aft)", "gear",
              pivot=dict(origin=P.tolist(), axis=[0, 1.0, 0], kind="gear", retract=ang),
              explode=(-0.4, 0, -0.8), group="Landing gear",
              material_note="Hydraulic shock strut, 17.5x6.25-6 tyre, +/-60 deg steering",
              info={"tyre": "17.5 x 6.25-6, 60 psi", "wheelbase": "3,480 mm",
                    "retraction": "aft, enclosed by doors", "steering": "+/-60 deg (Jane's)"})
    gp.add(Mesh.merge(struct + [collar, lamp_house]), "gear_leg").add(piston, "chrome")
    gp.add(Mesh.merge(ax_dark), "steel_dark").add(crown_bolts, "cadmium").add(holes, "black")
    for m, mat in lamp_face:
        gp.add(m, mat)
    for m, mat in wh:
        gp.add(m, mat)
    parts[gp.id] = gp

    # nose doors (clamshell, hinged at the outer edges)
    for side, sgn in (("R", 1), ("L", -1)):
        b = NOSE_BAY
        xs = np.linspace(b["cx"] - b["hx"] - 0.02, b["cx"] + b["hx"] + 0.02, 30)
        ts = np.linspace(0.5 - sgn * 0.0, 0.5 - sgn * 0.045, 8)
        X, Tt = np.meshgrid(xs, ts, indexing="ij")
        Pp = F.section(X, Tt)
        m = grid_surface(Pp)
        if m.N[:, 2].mean() > 0:
            m = m.flipped()
        f = lambda mm: np.maximum(sdf2d.rrect(mm.V[:, 0], mm.V[:, 1], b["cx"], b["cy"], b["hx"] - 0.004,
                                              b["hy"] - 0.004, b["r"]), -sgn * mm.V[:, 1] - 0.002)
        m = trim(m, f(m), "negative")
        m = solidify(m.offset(-0.001), 0.018)
        hy = sgn * (b["hy"] - 0.004)
        hz = float(np.mean(m.V[np.abs(m.V[:, 1] - hy) < 0.02, 2])) if np.any(np.abs(m.V[:, 1] - hy) < 0.02) else 0.83
        # built OPEN (the gear-down pose): the doors hang open beside the leg whenever the gear is down (photo s/n
        # 3001, wm_c087: door hanging vertically with the tyre-pressure placard) and close only once the gear is locked
        # up.  pivot: 'open' = closed -> open rotation (deg), 'rest' = door fraction the geometry is built at (1 = open)
        o = np.array([b["cx"], hy, hz])
        m = m.transformed(rotation_about((1.0, 0.0, 0.0), np.radians(NOSE_DOOR_OPEN_DEG * sgn), o))
        dp = Part(f"gear_door_N{side}", f"Nose gear door ({'right' if sgn > 0 else 'left'})", "gear",
                  pivot=dict(origin=o.tolist(), axis=[1.0, 0, 0], kind="gear_door", open=float(NOSE_DOOR_OPEN_DEG * sgn),
                             rest=1.0),
                  explode=(0, sgn * 0.25, -0.35), group="Landing gear", material_note="Composite door")
        dp.add(m, "paint_white")
        parts[dp.id] = dp


def build(parts):
    build_main(parts, "R")
    build_main(parts, "L")
    build_nose(parts)
    bay_tubs(parts)
    brace_parts(parts)
    return parts


MAIN_BAY_ROOF_GAP = 0.004           # main-bay liner roof under the wing upper skin (m; LD-1: 6 -> 4 mm)
# LD-1: the lowest MAIN_BAY_SEAL_H of the main-bay liner walls (the cut-out's jamb) is a black rubber seal: with the
# gear up only the door's 3 mm panel gap and the ring round the protruding tyre show into the bay, and there the
# photos from below (N81DW, pil_PC12_045) show black, not the zinc-chromate liner higher up
MAIN_BAY_SEAL_H = 0.060
# liner wall foot above the wing lower surface, per outline segment: on the cut-out edge (the jamb; LD-1: flush, no lip
# below the skin, the seal band shows black in the door's panel gap and round the tyre) and where the liner runs over
# INTACT skin (the liner-only brace / trunnion pockets and the blends into them, MQ2-02: the pocket outline must never
# be drawn on the wing underside; at 2 mm the headless (SwiftShader) viewer still showed it through the skin as a
# dotted line).  The seal band runs all round, as in LD-1: about a quarter of the cut-out edge (the door's forward edge
# and tab) lies inside the pockets, and through the panel gap there the pocket walls must show black too
MAIN_BAY_WALL_FLUSH = 0.0005
MAIN_BAY_WALL_UP = 0.010
MAIN_BAY_JAMB_TOL = 0.0005          # outline points this close to the cut-out edge are on the jamb (the rest: intact skin)

_WZ_TAB = {}
_WZ_BOX = (5.45, 7.05, 0.75, 2.95)   # tabulated region (x0, x1, |y|0, |y|1): the main-gear bay and around it


def _wing_z_exact(x, y, upper):
    """Wing upper / lower surface WL at plan points (x, y) (|y| used): the section point whose STATION is x (chord
    fraction solved with the twist included, a few Newton steps), per distinct butt line."""
    x, y = np.broadcast_arrays(np.asarray(x, float), np.abs(np.asarray(y, float)))
    out = np.empty(x.shape)
    for yy in np.unique(y):
        k = y == yy
        s = W.section_at(float(yy))
        f = s.upper if upper else s.lower
        xc = np.clip((x[k] - s.le[0]) / s.chord, 0, 1)
        for _ in range(4):
            xc = np.clip(xc + (x[k] - f(xc)[..., 0]) / s.chord, 0, 1)
        out[k] = f(xc)[..., 2]
    return out


def wing_z(x, y, upper=False):
    """Wing upper / lower surface WL at plan points (x, y) (arrays, |y| used): exact section geometry (twist included),
    over the main-gear region from a bicubic table (4 x 10 mm, < 0.01 mm), elsewhere per point."""
    from scipy.interpolate import RectBivariateSpline
    x, y = np.broadcast_arrays(np.asarray(x, float), np.abs(np.asarray(y, float)))
    if upper not in _WZ_TAB:
        x0, x1, y0, y1 = _WZ_BOX
        xs, ys = np.arange(x0, x1 + 1e-9, 0.004), np.arange(y0, y1 + 1e-9, 0.010)
        Z = np.stack([_wing_z_exact(xs, np.full(len(xs), yy), upper) for yy in ys], 1)
        _WZ_TAB[upper] = RectBivariateSpline(xs, ys, Z, kx=3, ky=3)
    x0, x1, y0, y1 = _WZ_BOX
    ins = (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)
    out = np.empty(x.shape)
    if ins.any():
        out[ins] = _WZ_TAB[upper].ev(x[ins], y[ins])
    if (~ins).any():
        out[~ins] = _wing_z_exact(x[~ins], y[~ins], upper)
    return out



def main_bay_outline(res=0.002):
    """Starboard plan outline (N, 2) of the main-gear bay liner: the zero contour of bays.main_bay_sdf."""
    import contourpy
    xs = np.arange(5.75, 6.85, res)
    ys = np.arange(1.00, 2.50, res)
    X, Y = np.meshgrid(xs, ys)
    lines = contourpy.contour_generator(X, Y, main_bay_sdf(X, Y)).lines(0.0)
    P = max(lines, key=len)
    if np.linalg.norm(P[0] - P[-1]) < 1e-9:
        P = P[:-1]
    return _simplify_closed(P, 0.0005)


def _rdp(P, tol):
    """Douglas-Peucker simplification of an open polyline (N, 2) (end points kept)."""
    if len(P) < 3:
        return P
    a, b = P[0], P[-1]
    d = b - a
    n = np.linalg.norm(d)
    if n < 1e-12:
        dist = np.linalg.norm(P - a, axis=1)
    else:
        dist = np.abs(d[0] * (P[:, 1] - a[1]) - d[1] * (P[:, 0] - a[0])) / n
    i = int(np.argmax(dist))
    if dist[i] <= tol:
        return np.vstack([a, b])
    return np.vstack([_rdp(P[:i + 1], tol)[:-1], _rdp(P[i:], tol)])


def _simplify_closed(P, tol):
    """Douglas-Peucker on a closed outline, split at its two mutually farthest points."""
    i = 0
    j = int(np.argmax(np.linalg.norm(P - P[i], axis=1)))
    i = int(np.argmax(np.linalg.norm(P - P[j], axis=1)))
    i, j = min(i, j), max(i, j)
    A = _rdp(P[i:j + 1], tol)
    B = _rdp(np.vstack([P[j:], P[:i + 1]]), tol)
    return np.vstack([A[:-1], B[:-1]])


def bay_tubs(parts):
    """Zinc-chromate wheel-well liners (visible with the doors open).  Main bays: walls round bays.main_bay_sdf (wheel
    well + leg slot + brace slot / pocket) from the lower skin up to a roof MAIN_BAY_ROOF_GAP under the wing upper
    skin, so the stowed tyre, leg, shock strut and folded side brace lie inside the liner (M1 / M4 / M6)."""
    from cad.mesh import planar_cap
    from cad.sdf2d import rrect_outline
    meshes = []
    ol = main_bay_outline()
    # wall foot per outline segment (MAIN_BAY_WALL_FLUSH / _UP): flush on the jamb of the real opening (LD-1), clear
    # above the intact skin round the liner-only pockets (MQ2-02); the lowest MAIN_BAY_SEAL_H (black seal) is a band of
    # per-segment quads, so the foot steps at a jamb end instead of sloping down onto the intact skin
    on_hole = main_opening_sdf(ol[:, 0], ol[:, 1]) < MAIN_BAY_JAMB_TOL
    jamb = on_hole & np.roll(on_hole, -1)               # outline segment k -> k+1 lies on the cut-out edge
    zsk = wing_z(ol[:, 0], ol[:, 1], False)
    zmid = zsk + MAIN_BAY_WALL_FLUSH + MAIN_BAY_SEAL_H  # top of the seal band
    zhi = wing_z(ol[:, 0], ol[:, 1], True) - MAIN_BAY_ROOF_GAP
    n = len(ol)
    k = np.arange(n)
    Fc = np.vstack([np.stack([k, (k + 1) % n, (k + 1) % n + n], 1), np.stack([k, (k + 1) % n + n, k + n], 1)])
    xs = np.linspace(ol[:, 0].min() - 0.01, ol[:, 0].max() + 0.01, 90)
    ys = np.linspace(ol[:, 1].min() - 0.01, ol[:, 1].max() + 0.01, 120)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    roof = grid_surface(np.stack([X, Y, wing_z(X, Y, True) - MAIN_BAY_ROOF_GAP], -1))
    roof = trim(roof, main_bay_sdf(roof.V[:, 0], roof.V[:, 1]), "negative")
    if roof.N[:, 2].mean() > 0:
        roof = roof.flipped()
    k1 = (k + 1) % n
    off = np.where(jamb, MAIN_BAY_WALL_FLUSH, MAIN_BAY_WALL_UP)                   # foot above the skin, per segment
    quad = np.stack([np.c_[ol, zsk + off], np.c_[ol[k1], zsk[k1] + off], np.c_[ol[k1], zmid[k1]], np.c_[ol, zmid]], 1)
    qf = np.array([[0, 1, 2], [0, 2, 3]])                                          # quads a, b, b', a' (as Fc)
    seals = []
    for sgn in (1, -1):
        wall = Mesh(np.vstack([np.c_[ol[:, 0], sgn * ol[:, 1], zmid], np.c_[ol[:, 0], sgn * ol[:, 1], zhi]]), Fc)
        meshes.append(wall)
        Q = quad * [1, sgn, 1]
        seals.append(Mesh(Q.reshape(-1, 3), (qf[None] + 4 * np.arange(n)[:, None, None]).reshape(-1, 3)))
        meshes.append(roof if sgn > 0 else roof.mirrored_y())
    b, tu = NOSE_BAY, NOSE_TUNNEL
    ol = rrect_outline(b["cx"], b["cy"], b["hx"], b["hy"], b["r"], n_corner=8)
    zs = np.array([float(F.z_bot(x)) + 0.01 for x, y in ol])
    lo = np.stack([ol[:, 0], ol[:, 1], zs], 1)
    hi = np.stack([ol[:, 0], ol[:, 1], np.full(len(zs), tu["z_low"])], 1)
    n = len(ol)
    V = np.vstack([lo, hi])
    k = np.arange(n)
    Fc = np.vstack([np.stack([k, (k + 1) % n, (k + 1) % n + n], 1), np.stack([k, (k + 1) % n + n, k + n], 1)])
    meshes.append(Mesh(V, Fc))
    # bay roof: low ahead of / behind the tunnel under the centre pedestal, where the stowed wheel sits
    for xa, xb in ((b["cx"] - b["hx"], tu["x0"]), (tu["x1"], b["cx"] + b["hx"])):
        meshes.append(box((0.5 * (xa + xb), 0.0, tu["z_low"]), (xb - xa, 2 * b["hy"], 0.004)))
    tv = rrect_outline(0.5 * (tu["x0"] + tu["x1"]), 0.0, 0.5 * (tu["x1"] - tu["x0"]), tu["hy"], 0.04, n_corner=6)
    lo = np.c_[tv, np.full(len(tv), tu["z_low"])]
    hi = np.c_[tv, np.full(len(tv), tu["z_top"])]
    n = len(tv)
    k = np.arange(n)
    Fc = np.vstack([np.stack([k, (k + 1) % n, (k + 1) % n + n], 1), np.stack([k, (k + 1) % n + n, k + n], 1)])
    meshes.append(Mesh(np.vstack([lo, hi]), Fc))
    meshes.append(planar_cap(hi, (0, 0, -1)))
    p = Part("gear_bays", "Wheel wells (grey liners)", "gear", group="Landing gear",
             material_note="Painted aluminium liners, black rubber seal band at the cut-out")
    p.add(Mesh.merge(meshes), "gear_bay").add(Mesh.merge(seals), "seal")   # grey (no MSN 3008 photo shows primer: F12)
    parts[p.id] = p



# ---------------------------------------------------------------------------
# over-centre folding struts (POH: "overcenter two piece drag link")
# ---------------------------------------------------------------------------
def brace_lengths(A, B0, f1):
    D = float(np.linalg.norm(np.asarray(B0) - np.asarray(A))) * 1.0005     # straight (just over centre) gear-down
    return f1 * D, (1.0 - f1) * D


def brace_specs():
    """(part id, gear id, A, B0, gear origin, knee axis, (L1 fraction, bend ref), name) of the three folding struts."""
    out = []
    for side, sgn in (("R", 1), ("L", -1)):
        f1, ref = MAIN_BRACE_SPLIT
        out.append((f"brace_main_{side}", f"gear_main_{side}", np.array(MAIN_BRACE[0]) * [1, sgn, 1],
                    np.array(MAIN_BRACE[1]) * [1, sgn, 1], MAIN_TRUNNION * [1, sgn, 1], np.array([1.0, 0, 0]),
                    (f1, np.array(ref) * [1, sgn, 1]), f"{'Right' if sgn > 0 else 'Left'} main-gear folding side brace"))
    f1, ref = NOSE_BRACE_SPLIT
    out.append(("brace_nose", "gear_nose", np.array(NOSE_BRACE[0]), np.array(NOSE_BRACE[1]), NOSE_PIVOT,
                np.array([0, 1.0, 0]), (f1, np.array(ref)), "Nose-gear folding drag brace"))
    return out


def _brace_meshes(pid, A, B0, K0, axis):
    """(upper-link mesh, lower-link mesh) of folding strut pid, gear down.  Nose: fork upper link straddling the leg
    (NOSE_BRACE_FORK), single lower link to the lug on the leg.  Main: links offset along the knee pin by
    MAIN_BRACE_CLEVIS, the lower link's lug B0 carried on a bracket from the leg (in the gear part)."""
    if pid == "brace_nose":
        fk = NOSE_BRACE_FORK
        ey = np.array([0.0, 1.0, 0.0])
        up = []
        for sg in (-1.0, 1.0):          # V-fork: straight past the stowed leg, then in to the knee (the knee sits
            a = A + sg * fk["y"] * ey    # beside the open clamshell hinges when the gear is down)
            m = A + fk["bend"] * (K0 - A) + sg * fk["y"] * ey
            k = K0 + sg * fk["y_knee"] * ey
            up += [cylinder(a, m, fk["r"], n=12), cylinder(m, k, fk["r"], n=12),
                   superellipsoid(m, (fk["r"],) * 3, (1, 1), 6, 8)]
            up.append(cylinder(A + sg * fk["stub"][0] * ey, A + sg * fk["stub"][1] * ey, 0.014, n=12))  # wall pin
        up.append(cylinder(K0 - (fk["y_knee"] + 0.010) * ey, K0 + (fk["y_knee"] + 0.010) * ey, fk["pin_r"], n=12))
        lo = [cylinder(K0, B0, 0.020, n=12), superellipsoid(B0, (0.024, 0.024, 0.024), (1, 1), 8, 12)]
        return Mesh.merge(up), Mesh.merge(lo)
    ax = np.asarray(axis, float) / np.linalg.norm(axis)
    c1, c2 = MAIN_BRACE_CLEVIS
    r1, r2 = MAIN_BRACE_R
    p0, p1 = min(c1 - r1, c2 - r2), max(c1 + r1, c2 + r2)       # knee pin spans both link eyes
    (w1a, w1k), (w2k, w2b) = MAIN_BRACE_W
    kr = MAIN_BRACE_KNEE[1]
    up = [swept_arm([A + c1 * ax, K0 + c1 * ax], (r1, r1), (w1a, w1k), n_path=6, fore=ax),
          superellipsoid(A + c1 * ax, (r1 + 0.002, w1a + 0.004, w1a + 0.004), (1, 1), 8, 12),
          superellipsoid(K0 + c1 * ax, (r1, kr, kr), (1, 1), 8, 14),                               # knee lug
          cylinder(K0 + p0 * ax, K0 + p1 * ax, 0.010, n=12)]                                        # knee pin
    lo = [swept_arm([K0 + c2 * ax, B0 + c2 * ax], (r2, r2), (w2k, w2b), n_path=6, fore=ax),
          superellipsoid(K0 + c2 * ax, (r2, kr * 0.85, kr * 0.85), (1, 1), 8, 14),
          superellipsoid(B0 + c2 * ax, (0.022, w2b + 0.002, w2b + 0.002), (1, 1), 8, 12)]
    return Mesh.merge(up), Mesh.merge(lo)


def main_brace_lug(sgn):
    """Bracket on the main leg carrying the side-brace lug B0 (gear down, side sgn): from the leg axis abreast of B0
    inboard to B0 (MAIN_BRACE_LUG, MV2-02), with the pin the lower link's eye turns on (moves with the leg)."""
    T, Lp = MAIN_TRUNNION * [1, sgn, 1], MAIN_LINK_PIVOT * [1, sgn, 1]
    B0 = np.array(MAIN_BRACE[1]) * [1, sgn, 1]
    u = (Lp - T) / np.linalg.norm(Lp - T)
    p = T + u * ((B0 - T) @ u)                              # leg-axis point abreast of the lug
    c = np.array([MAIN_BRACE_CLEVIS[1], 0.0, 0.0])          # the lower link's eye sits on the pin at B0 + clevis
    return Mesh.merge([cylinder(p, B0, 0.016, n=12), cylinder(B0 + c - [0.03, 0, 0], B0 + c + [0.03, 0, 0], 0.012, n=10)])


def brace_parts(parts):
    from model.brace import solve_knee
    for pid, gear_id, A, B0, T, axis, (f1, ref), name in brace_specs():
        L1, L2 = brace_lengths(A, B0, f1)
        K0 = solve_knee(A, B0, L1, L2, axis, ref)
        m_up, m_lo = _brace_meshes(pid, A, B0, K0, axis)
        up = Part(pid + "_up", name + " (upper link)", "gear",
                  pivot=dict(origin=A.tolist(), axis=axis.tolist(), kind="brace", role="upper", gear=gear_id,
                             A=A.tolist(), B0=B0.tolist(), K0=K0.tolist(), L1=float(L1), L2=float(L2),
                             bend=ref.tolist()),
                  group="Landing gear", material_note="Over-centre lock, down-lock spring")
        up.add(m_up, "gear_leg")
        lo = Part(pid + "_lo", name + " (lower link)", "gear", parent=pid + "_up",
                  pivot=dict(origin=K0.tolist(), axis=axis.tolist(), kind="brace", role="lower", gear=gear_id),
                  group="Landing gear", material_note="Over-centre lock")
        lo.add(m_lo, "gear_leg")
        parts[up.id] = up
        parts[lo.id] = lo
