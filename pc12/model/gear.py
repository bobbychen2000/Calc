"""
Landing gear: electromechanically actuated tricycle (PC-12 NG MSN 1451+ / NGX / PRO).
  POH 7-4: trailing-link mains with hydraulic shock struts retract INWARD; one door per
  side attached to the gear leg; retracted tyres protrude ~1 in from the wells.
  Nose: hydraulic shock strut, retracts REARWARD, fully enclosed by spring-closed doors.
  All legs locked down by an over-centre two-piece folding strut.
  * Main: trailing-link units on the wing spars, retract INWARD into the wing.
          Tyres 22 x 8.50-10.
  * Nose: steerable oleo strut, retracts REARWARD under the flight deck.
          Tyre 17.5 x 6.25-6, steering +/-60 deg.
Geometry is built in the gear-DOWN position; each unit stores its retraction
axis/angle (and each door its opening angle) for the viewer's gear animation.
Wheel track 4.53 m (Pilatus), wheelbase 3.48 m (POH three-view).
Stage 2 (rev B): axle, pivot and brace positions from the Pilatus NGX drawing (side / front views).
"""
from __future__ import annotations
import numpy as np

from cad.mesh import (Mesh, revolve, cylinder, box, sweep_tube, grid_surface, trim, solidify,
                      rotation_about, superellipsoid)
from cad import sdf2d
from model.parts import Part
from model import wing as W
from model import fuselage as F

TRACK = 4.53
WHEELBASE = 3.48
# Stage 2 (rev B): axles and leg geometry from the Pilatus drawing side / front views.  The drawing's axles are
# 3.515 m apart; the POH 3.48 m is kept and the pair is centred on the drawn axles (each unit moved rigidly by
# GEAR_SHIFT, forward for the main gear, aft for the nose gear).
GEAR_SHIFT = 0.0175
MAIN_TYRE = dict(R=0.2795, W=0.216, rim=0.127)      # 22 x 8.50-10
NOSE_TYRE = dict(R=0.2225, W=0.159, rim=0.076)      # 17.5 x 6.25-6
MAIN_AXLE = np.array([6.428 - GEAR_SHIFT, TRACK / 2, 0.279])        # static, tyre on the ground line
NOSE_AXLE = np.array([MAIN_AXLE[0] - WHEELBASE, 0.0, 0.222])
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
# side brace A, B0: BL / WL as drawn (front view); stations (hidden: behind the door in the side view, inside the wing)
# LD-1: A 5,950 -> 6,058 and B0 6,040 -> 6,056 (drawing frame), so the brace plane lies just behind the door's
# chamfered forward-lower corner: folding, the lower link now passes the skin inside the door's footprint (at 5,950 it
# swept a slot ahead of the corner that nothing could close); B0 sits on the leg axis
MAIN_BRACE = ((6.0575 - GEAR_SHIFT, 1.330, 1.220), (6.0555 - GEAR_SHIFT, 2.250, 0.840))
MAIN_BRACE_DRAWN_X = (5.950 - GEAR_SHIFT, 6.040 - GEAR_SHIFT)
NOSE_PIVOT = np.array([2.970 + GEAR_SHIFT, 0.0, 1.040])
NOSE_FORK = np.array([2.930 + GEAR_SHIFT, 0.0, 0.520])             # fork crown / piston bottom
NOSE_BRACE = ((3.470 + GEAR_SHIFT, 0.0, 1.070), (3.030 + GEAR_SHIFT, 0.0, 0.785))      # drag brace A, B0
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
NOSE_DOOR_OPEN_DEG = 85.0           # nose clamshells: closed -> open (hanging beside the leg; open while the gear is down)
# tunnel x0 3.20 (rev: 3.30): the drag brace's lower link (B at x 3.22-3.25, WL 1.12-1.16 when retracted, rising to the
# knee under the pedestal) passes under the tunnel roof, not the low forward bay roof (M7)
NOSE_TUNNEL = dict(x0=3.200, x1=4.100, hy=0.155, z_top=1.460, z_low=1.200)
NOSE_BRACE_SPLIT = (0.40, (-0.72, 0.0, 0.695))        # (L1 fraction, bend reference)
# main L1 0.19 (LD-1; was 0.15): with the raised trunnion the stowed leg attach point B comes to 0.624 m of A, closer
# than L2 - L1 = 0.70 m of a 0.15 split (the knee could not close the chain); 0.19 leaves 6 mm and folds the knee
# down to ~65 mm above the lower skin, inside BRACE_POCKET (a longer upper link folds deeper and drags the lower link's
# skin crossing inboard of the door's footprint)
MAIN_BRACE_SPLIT = (0.19, (0.0, 0.30, -0.95))         # starboard; the bend reference is mirrored for port


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
#     protruding tyre, so the door is scalloped round the tyre (R 292 about the axle, >= 15 mm clear of the tyre at the door) and the
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
                scallop_r=0.292,                    # LD-1: tyre scallop about MAIN_AXLE (tyre R 279.5 + 12.5)
                tab=(6.070, MAIN_TRUNNION[2] + 0.090))   # LD-1: forward top tab: aft STA, top WL (hidden, in the slot)
LEG_DOOR_T = 0.012                  # door plate thickness (inboard of the outer face)
LEG_DOOR_RECESS = 0.001             # retracted, the door's outer face lies this far inside the wing lower surface
LEG_DOOR_CORNER_R = 0.020           # radius of the door's aft top corner (leg_door_face)
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
    xa = np.linspace(d["arc_x0"], Pi[0], n_arc)
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
    fil = _fillet(np.array([d["x_aft"], d["z_step"][1]]), top[0], top[1], LEG_DOOR_CORNER_R)
    top = np.vstack([fil, top[1:]])
    if visible:
        xw = np.linspace(x_tab, float(_door_fwd_x(1.09)), 8)
        zw = _door_wing_line(xw)
        for _ in range(3):                           # forward end on the forward edge
            xw[-1] = float(_door_fwd_x(zw[-1]))
            zw = _door_wing_line(xw)
        tab = np.c_[xw, zw]
    else:
        tab = np.array([[x_tab, z_tab], [float(_door_fwd_x(z_tab)), z_tab]])
    return np.vstack([[[d["x_fwd_low"], d["z_fwd_low"]], list(d["tip"])], arc, sc,
                      [[d["x_aft_low"], d["z_step"][0]], [d["x_aft"], d["z_step"][1]]], top, tab])


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


def main_tyre_protrusion(side=1):
    """Largest depth (m) of the retracted main tyre below the local wing lower surface (POH: ~1 in)."""
    M = main_retract_matrix(side)
    tyre = [m for m, mat in wheel(MAIN_AXLE * [1, side, 1], np.array([0, 1.0, 0]), MAIN_TYRE, n=44) if mat == "tire"][0]
    V = tyre.V @ M[:3, :3].T + M[:3, 3]
    return float((wing_z(V[:, 0], V[:, 1], False) - V[:, 2]).max())


from model.bays import NOSE_BAY, main_opening_sdf, main_bay_sdf, nose_bay_sdf


# ---------------------------------------------------------------------------
def wheel(center, axis, tyre, n=40, brake_side=0):
    """Tyre + rim + hub (+ brake disc) about `axis` (unit) through `center`."""
    R, Wd, rim = tyre["R"], tyre["W"], tyre["rim"]
    h = Wd / 2
    # tyre cross-section (bulged) as revolve profile in (s along axis, r)
    th = np.linspace(-np.pi / 2, np.pi / 2, 21)
    prof = [(-h * 0.80, rim + 0.005)]
    bead_r = rim + 0.012
    for t in th:
        s = h * np.sin(t)
        r = bead_r + (R - bead_r) * (0.5 + 0.5 * np.cos(t)) ** 0.35 * 1.0
        prof.append((s * 1.0, r))
    prof.append((h * 0.80, rim + 0.005))
    prof = [(s, r) for s, r in prof]
    # re-sort monotone in s for a clean revolve (profile runs -s -> +s over the crown)
    tyre_m = revolve([(s + h, r) for s, r in prof], n=n, axis_origin=center - h * axis, axis_dir=axis)
    rim_m = revolve([(0.0, rim * 0.55), (0.012, rim), (Wd * 0.84, rim), (Wd * 0.84 + 0.012, rim * 0.55),
                     (Wd * 0.84 + 0.013, 0.0)], n=n, axis_origin=center - Wd * 0.42 * axis, axis_dir=axis)
    hub_m = revolve([(0.0, 0.0), (0.001, rim * 0.55), (0.03, rim * 0.40), (0.031, 0.0)], n=24,
                    axis_origin=center + Wd * 0.30 * axis, axis_dir=axis)   # hub cap inside the tyre width
    parts = [(tyre_m, "tire"), (Mesh.merge([rim_m, hub_m]), "wheel")]
    if brake_side:
        d = revolve([(0, 0.05), (0.001, 0.115), (0.012, 0.115), (0.013, 0.05)], n=36,
                    axis_origin=center + brake_side * (h + 0.012) * axis, axis_dir=axis)
        parts.append((d, "steel"))
    return parts


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
    fy = 0.14
    struct.append(cylinder(L - sgn * fy * yax, L - sgn * 0.03 * yax, 0.036, n=16))
    for s in (-sgn,):
        a = L + s * fy * yax
        b = A + s * fy * yax
        d = b - a
        Ln = np.linalg.norm(d)
        # flattened arm: box aligned with d
        ex = d / Ln
        ez = np.array([0, 0, 1.0]) - ex * ex[2]
        ez /= np.linalg.norm(ez)
        ey = np.cross(ez, ex)
        R = np.stack([ex, ey, ez], 1)
        struct.append(box((a + b) / 2, (Ln, 0.035, 0.07), R=R))
    struct.append(cylinder(A - sgn * fy * yax, A + sgn * 0.05 * yax, 0.026, n=16))      # axle
    # shock absorber on the inboard side, over the trailing arm (fy), so it stows inside the wing above the leg
    s_in = -sgn * 0.15
    S1 = np.array([MAIN_SHOCK[0][0], T[1] + s_in, MAIN_SHOCK[0][1]])
    S2 = np.array([MAIN_SHOCK[1][0], T[1] + s_in * 0.95, MAIN_SHOCK[1][1]])
    mid = S1 + 0.55 * (S2 - S1)
    shock_body = cylinder(S1, mid, 0.036, n=18)
    shock_rod = cylinder(mid - 0.05 * (S2 - S1), S2, 0.027, n=14)
    lugs = [cylinder(S1 - [0, 0.03 * sgn, 0], S1 + [0, 0.03 * sgn, 0], 0.03, n=12),
            box(S2 + [0.0, -s_in * 0.4, 0.0], (0.06, abs(s_in) * 0.9, 0.04)),
            box(np.array([MAIN_SHOCK[0][0], T[1] + s_in * 0.5, MAIN_SHOCK[0][1]]), (0.06, abs(s_in), 0.05))]
    wh = wheel(A, yax, MAIN_TYRE, n=44, brake_side=-sgn)

    # leg door (LEG_DOOR / leg_door_face, sheet L4, LD-1): a piece of the wing lower skin carried by the leg (flush
    # when retracted), scalloped round the tyre, on two standoff brackets from the leg; it retracts rigidly with the leg
    ang_retract = np.radians(MAIN_RETRACT_DEG) * (-sgn)          # about +x
    door_down = leg_door_mesh(sgn)
    brackets = []
    for zb in (0.98, 0.62):
        a = T + (L - T) * (T[2] - zb) / (T[2] - L[2])
        b = np.array([a[0], sgn * (float(leg_door_bl(a[0], zb)) - LEG_DOOR_T - 0.001), zb])
        brackets.append(cylinder(a, b, 0.012, n=10))

    gp = Part(f"gear_main_{side}", f"{'Right' if sgn > 0 else 'Left'} main gear (trailing link)", "gear",
              pivot=dict(origin=T.tolist(), axis=[1.0, 0, 0], kind="gear", retract=float(np.degrees(ang_retract))),
              explode=(0, sgn * 0.6, -0.7), group="Landing gear",
              material_note="Trailing link, hydraulic shock strut, electromechanical actuator",
              info={"tyre": "22 x 8.50-10, 55 psi", "track": "4,530 mm",
                    "retraction": f"{MAIN_RETRACT_DEG:.0f} deg inward; tyre protrudes ~1 in (POH)",
                    "door": "single leg-mounted door, flush with the wing skin when retracted"})
    gp.add(Mesh.merge(struct + lugs), "gear_leg").add(Mesh.merge([shock_body]), "gear_leg").add(shock_rod, "chrome")
    for m, mat in wh:
        gp.add(m, mat)
    gp.add(door_down, "paint_white").add(Mesh.merge(brackets), LEG_DOOR_BRACKET_MAT)
    parts[gp.id] = gp



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


def leg_door_mesh(sgn, step=0.015):
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
    door = Mesh.merge([outer, inner, rim])
    return door if sgn > 0 else door.mirrored_y()


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
    struct.append(box(low + [0, 0, 0.0], (0.08, 0.25, 0.045)))                      # fork crown
    for s in (-1, 1):
        a = low + s * 0.105 * yax
        b = A + s * 0.105 * yax
        d = b - a
        Ln = np.linalg.norm(d)
        ex = d / Ln
        ez = np.array([1.0, 0, 0]) - ex * ex[0]
        ez /= np.linalg.norm(ez)
        ey = np.cross(ez, ex)
        struct.append(box((a + b) / 2, (Ln, 0.022, 0.07), R=np.stack([ex, ey, ez], 1)))
    struct.append(cylinder(A - 0.115 * yax, A + 0.115 * yax, 0.02, n=14))          # axle
    # torque links (scissor) in front of the strut
    k1 = P + 0.56 * (low - P) + [-0.055, 0, 0]
    k2 = low + [-0.05, 0, 0.03]
    knee = 0.5 * (k1 + k2) + [-0.09, 0, 0]
    for a, b in ((k1, knee), (knee, k2)):
        struct.append(cylinder(a, b, 0.014, n=10))
    # taxi / landing light on the strut
    lamp = cylinder(P + 0.45 * (low - P) + [-0.06, 0, 0], P + 0.45 * (low - P) + [-0.11, 0, 0], 0.045, n=20)
    wh = wheel(A, yax, NOSE_TYRE, n=36)
    ang = NOSE_RETRACT_DEG
    gp = Part("gear_nose", "Nose gear (steerable, retracts aft)", "gear",
              pivot=dict(origin=P.tolist(), axis=[0, 1.0, 0], kind="gear", retract=ang),
              explode=(-0.4, 0, -0.8), group="Landing gear",
              material_note="Hydraulic shock strut, 17.5x6.25-6 tyre, +/-60 deg steering",
              info={"tyre": "17.5 x 6.25-6, 60 psi", "wheelbase": "3,480 mm",
                    "retraction": "aft, enclosed by doors", "steering": "+/-60 deg (Jane's)"})
    gp.add(Mesh.merge(struct + [collar]), "gear_leg").add(piston, "chrome").add(lamp, "lens")
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
    zlo = wing_z(ol[:, 0], ol[:, 1], False) + 0.0005    # LD-1: flush underside, no lip below the skin at the cut-out
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
    zmid = zlo + MAIN_BAY_SEAL_H                        # LD-1: black seal band round the cut-out (below)
    seals = []
    for sgn in (1, -1):
        wall = Mesh(np.vstack([np.c_[ol[:, 0], sgn * ol[:, 1], zmid], np.c_[ol[:, 0], sgn * ol[:, 1], zhi]]), Fc)
        seal = Mesh(np.vstack([np.c_[ol[:, 0], sgn * ol[:, 1], zlo], np.c_[ol[:, 0], sgn * ol[:, 1], zmid]]), Fc)
        meshes.append(wall)
        seals.append(seal)
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
    p = Part("gear_bays", "Wheel wells (zinc-chromate liners)", "gear", group="Landing gear",
             material_note="Primed aluminium liners")
    p.add(Mesh.merge(meshes), "zinc_chromate").add(Mesh.merge(seals), "seal")
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


def brace_parts(parts):
    from model.brace import solve_knee
    for pid, gear_id, A, B0, T, axis, (f1, ref), name in brace_specs():
        L1, L2 = brace_lengths(A, B0, f1)
        K0 = solve_knee(A, B0, L1, L2, axis, ref)
        up = Part(pid + "_up", name + " (upper link)", "gear",
                  pivot=dict(origin=A.tolist(), axis=axis.tolist(), kind="brace", role="upper", gear=gear_id,
                             A=A.tolist(), B0=B0.tolist(), K0=K0.tolist(), L1=float(L1), L2=float(L2),
                             bend=ref.tolist()),
                  group="Landing gear", material_note="Over-centre lock, down-lock spring")
        up.add(Mesh.merge([cylinder(A, K0, 0.022, n=12), superellipsoid(A, (0.03, 0.03, 0.03), (1, 1), 8, 12),
                           superellipsoid(K0, (0.02, 0.02, 0.02), (1, 1), 8, 12)]), "gear_leg")
        lo = Part(pid + "_lo", name + " (lower link)", "gear", parent=pid + "_up",
                  pivot=dict(origin=K0.tolist(), axis=axis.tolist(), kind="brace", role="lower", gear=gear_id),
                  group="Landing gear", material_note="Over-centre lock")
        lo.add(Mesh.merge([cylinder(K0, B0, 0.02, n=12), superellipsoid(B0, (0.024, 0.024, 0.024), (1, 1), 8, 12)]),
               "gear_leg")
        parts[up.id] = up
        parts[lo.id] = lo
