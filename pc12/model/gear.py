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
                      rotation_about, superellipsoid, planar_cap)
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
# retraction pivot (axis along x): x at the drawn leg top; WL at the wing lower skin, which with the moved wing
# still gives the POH ~1 in tyre protrusion when retracted (see retracted_wheel())
MAIN_TRUNNION = np.array([5.950 - GEAR_SHIFT, TRACK / 2, 1.070])
MAIN_LINK_PIVOT = np.array([6.118 - GEAR_SHIFT, TRACK / 2, 0.517])  # trailing-link pivot on the leg
MAIN_SHOCK = ((6.333 - GEAR_SHIFT, 0.930), (6.380 - GEAR_SHIFT, 0.400))   # shock strut top / bottom (x, z)
MAIN_BRACE = ((5.950 - GEAR_SHIFT, 1.330, 1.220), (6.040 - GEAR_SHIFT, 2.250, 0.840))  # side brace A, B0
NOSE_PIVOT = np.array([2.970 + GEAR_SHIFT, 0.0, 1.040])
NOSE_FORK = np.array([2.930 + GEAR_SHIFT, 0.0, 0.520])             # fork crown / piston bottom
NOSE_BRACE = ((3.470 + GEAR_SHIFT, 0.0, 1.070), (3.030 + GEAR_SHIFT, 0.0, 0.785))      # drag brace A, B0
# Retraction (Stage 3).  Nose: 105 deg aft about NOSE_PIVOT puts the axle at WL ~1.20 and the tyre 33 mm above the
# keel (95 deg left it 108 mm below the keel); the wheel stows in a tunnel under the centre pedestal
# (NOSE_TUNNEL: x-range, half-width, top WL).  Folding struts: two links of unequal length (L1 = upper link A-K as a
# fraction of |A - B0|) and the bend side chosen so the knee stays inside the bay / between the wing skins over the
# whole retraction (fit_check verifies): nose knee folds UP, clear of the stowed tyre and above the keel; main knee
# folds DOWN inside the wing box (rev B: equal links, main knee 177 mm above the upper skin when retracted).
NOSE_RETRACT_DEG = -105.0
MAIN_RETRACT_DEG = 90.0
NOSE_DOOR_OPEN_DEG = 85.0           # nose clamshells: closed -> open (hanging beside the leg; open while the gear is down)
# tunnel x0 3.20 (rev: 3.30): the drag brace's lower link (B at x 3.22-3.25, WL 1.12-1.16 when retracted, rising to the
# knee under the pedestal) passes under the tunnel roof, not the low forward bay roof (M7)
NOSE_TUNNEL = dict(x0=3.200, x1=4.100, hy=0.155, z_top=1.460, z_low=1.200)
NOSE_BRACE_SPLIT = (0.40, (-0.72, 0.0, 0.695))        # (L1 fraction, bend reference)
MAIN_BRACE_SPLIT = (0.15, (0.0, 0.30, -0.95))         # starboard; the bend reference is mirrored for port


# Main-gear leg door (ONE per leg, POH), Stage 2 rev B.1.  The Pilatus drawing shows it in TWO views: edge-on in the
# front view (a plate outboard of the tyre, leaning out from BL 2368 at WL 1052 to BL 2473 at its lowest point WL
# 338) and face-on in the side view (port main gear: a closed outline in front of the tyre, whose arc behind it is
# a hair line).  Its side-view face is fitted here (all stations less GEAR_SHIFT, like the rest of the unit):
#   forward edge   STA 5,950 at the wing -> 5,969 at WL 460 (leans aft 19 mm), then a chamfer to
#   pointed tip    (6,062, 318), 15 mm flat to the
#   lower edge     concave circle arc, centre (6,358, 119), R 348 (fit within 0.2 mm), rising to
#   aft-lower corn (6,404, 464): the narrow lower part's aft edge is vertical at STA 6,404 up to WL 758, then a
#   step           diagonal to (6,615, 939) and the wide upper part's aft edge up to (6,603, 1,088);
#   top edge       straight, WL 1,073 -> 1,088 (about the trunnion WL 1,070): 12-37 mm below the wing lower surface
#                  at the door's BL (leg_door_wing_clearance()), the clearance the door needs to swing up with the leg.
# Photos agree on the shape: ngx_dfbox_port (telephoto, near-broadside, port) shows the pointed tip ~0.4 m ahead of
# the axle, the concave lower edge rising to above the hub, the narrow lower part and the diagonal step to the wide
# upper part; PRO s/n 3036 (3/4 view) the same stepped aft edge.  In ngx_dfbox_port the door sits ~0.1 m lower
# relative to the wheel than drawn, and on s/n 3036 its lower edge comes close to the hub (trailing link compressed
# under load) -- the drawing's static pose is kept.  Details: refs/photo_notes.md (e).
# The drawing's two views differ by 20 mm on the lowest point (side-view tip WL 318, front-view plate end WL 338);
# the side-view face is kept.  Rev B.0 read the face from the oblique photos instead (straight aft edge at 6,520,
# tip 0.14 m ahead of the axle, a hub cut-out R 150 about the axle): 116 mm off the drawn outline.
# The door closes the wing bay when retracted (retracts with the leg, 90 deg inboard about MAIN_TRUNNION):
# leg_door_footprint().  Stage 3: the 3-D door is this outline in the drawn plane (leg_door_mesh, rigid on the leg)
# and the wing-bay leg slot is its footprint (bays.leg_slot_sdf).  OPEN (owner decision): the drawn plane lies 93-207 mm
# outboard of the leg / wheel plane (BL 2265), so after the 90 deg inward retraction the rigid door lies that far BELOW
# the stowed wheel's mid-plane (= the trunnion WL, which is at the wing lower skin and gives the POH 1 in tyre
# protrusion): 105-142 mm below the wing lower skin (leg_door_retracted_drop()).  Raising the trunnion raises the
# stowed wheel by the same amount (tyre recessed, into the upper skin), and a linkage cannot pull the door in past the
# leg (23 mm room) or the tyre (the drawn face overlaps the static tyre by up to 93 mm in side view), so a flush door
# needs a change to LEG_DOOR, the retraction geometry or the POH protrusion (fit_check reports it as '[open]').
LEG_DOOR = dict(x_fwd=5.950 - GEAR_SHIFT, x_fwd_low=5.969 - GEAR_SHIFT, z_fwd_low=0.460,   # forward edge
                tip=(6.062 - GEAR_SHIFT, 0.318), arc_x0=6.0762 - GEAR_SHIFT,               # tip, arc start STA
                arc_c=(6.3582 - GEAR_SHIFT, 0.1187), arc_r=0.3482,                         # concave lower edge
                x_aft_low=6.404 - GEAR_SHIFT, z_step=(0.758, 0.939),                       # narrow part, step WLs
                x_aft=6.615 - GEAR_SHIFT, x_aft_top=6.603 - GEAR_SHIFT,                    # wide part's aft edge
                z_top=(1.073, 1.088),                                                      # top edge WL fwd / aft
                bl=(2.358, 2.472))                                                         # door plane BL


def _door_top_z(xs):
    """WL of the door's (straight) top edge at stations xs."""
    d = LEG_DOOR
    t = (np.asarray(xs, float) - d["x_fwd"]) / (d["x_aft_top"] - d["x_fwd"])
    return d["z_top"][0] + (d["z_top"][1] - d["z_top"][0]) * t


def leg_door_wing_clearance():
    """Smallest clearance (m) between the door's top edge and the wing lower surface at the door's top BL."""
    d = LEG_DOOR
    xs = np.linspace(d["x_fwd"], d["x_aft_top"], 30)
    sec = W.section_at(d["bl"][0])
    xc = np.clip((xs - sec.le[0]) / sec.chord, 0, 1)
    return float(np.min(sec.lower(xc)[:, 2] - _door_top_z(xs)))


def leg_door_outline(n_arc=24):
    """Leg-door outline (N, 2) in side projection (x, z), gear down, closed: forward edge, chamfer to the pointed tip,
    concave lower edge (circle arc), stepped aft edge (narrow lower part, diagonal, wide upper part), straight top
    edge just below the wing."""
    d = LEG_DOOR
    (cx, cz), r = d["arc_c"], d["arc_r"]
    xa = np.linspace(d["arc_x0"], d["x_aft_low"], n_arc)
    arc = np.c_[xa, cz + np.sqrt(np.maximum(r * r - (xa - cx) ** 2, 0.0))]
    xs = np.linspace(d["x_aft_top"], d["x_fwd"], 16)
    top = np.c_[xs, _door_top_z(xs)]
    return np.vstack([[[d["x_fwd_low"], d["z_fwd_low"]], list(d["tip"])], arc,
                      [[d["x_aft_low"], d["z_step"][0]], [d["x_aft"], d["z_step"][1]]], top])


def leg_door_footprint(side=1):
    """Plan footprint (x, y) of the leg door when retracted (rotated 90 deg inboard about MAIN_TRUNNION with the
    leg): the wing-bay opening it must close (Stage 3)."""
    T = MAIN_TRUNNION
    P = leg_door_outline()
    y = T[1] - (T[2] - P[:, 1])
    return np.c_[P[:, 0], side * y]


def retracted_wheel(side=1):
    """Main-wheel centre after the 90 deg inward retraction about MAIN_TRUNNION (x-axis)."""
    T, A = MAIN_TRUNNION, MAIN_AXLE
    return np.array([A[0], side * (T[1] - (T[2] - A[2])), T[2] + (A[1] - T[1])])


def leg_door_bl(z):
    """Butt line of the leg door's outer face at WL z (starboard): the drawn edge-on line, BL 2,358 at the top edge
    -> 2,472 at the lowest point."""
    d = LEG_DOOR
    P = leg_door_outline()
    zmx, zmn = float(P[:, 1].max()), float(P[:, 1].min())
    return d["bl"][0] + (d["bl"][1] - d["bl"][0]) * (zmx - np.asarray(z, float)) / (zmx - zmn)


LEG_DOOR_T = 0.012                  # door plate thickness (inboard of the drawn outer face)
LEG_DOOR_BRACKET_MAT = "metal_dark"  # the door's two standoff brackets from the leg (the door assembly)


def leg_door_retracted_drop(side=1):
    """(min, max) height (m) of the retracted door's outer face BELOW the wing lower skin over the door (rigid door
    turned 90 deg inboard about MAIN_TRUNNION with the leg)."""
    T = MAIN_TRUNNION
    P = leg_door_outline()
    drops = []
    for x, z in P:
        y_up = T[1] - (T[2] - z)                 # footprint (the z -> y map)
        z_up = T[2] - (float(leg_door_bl(z)) - T[1])
        s = W.section_at(y_up)
        xc = np.clip((x - s.le[0]) / s.chord, 0, 1)
        drops.append(float(s.lower(np.array(xc))[2]) - z_up)
    return float(min(drops)), float(max(drops))


from model.bays import WELL, NOSE_BAY, main_opening_sdf, main_bay_sdf, nose_bay_sdf


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
    struct.append(cylinder(T - [0.07, 0, 0], T + [0.07, 0, 0], 0.045, n=20))        # trunnion pin (in the fwd slot)
    struct.append(revolve([(0, 0.058), (0.60, 0.047), (0.62, 0.0)], n=24, axis_origin=T,
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
    lugs = [cylinder(S1 - [0, 0.04 * sgn, 0], S1 + [0, 0.04 * sgn, 0], 0.03, n=12),
            box(S2 + [0.0, -s_in * 0.4, 0.0], (0.06, abs(s_in) * 0.9, 0.04)),
            box(np.array([MAIN_SHOCK[0][0], T[1] + s_in * 0.5, MAIN_SHOCK[0][1]]), (0.06, abs(s_in), 0.05))]
    wh = wheel(A, yax, MAIN_TYRE, n=44, brake_side=-sgn)

    # leg door (LEG_DOOR, sheet L4): the drawn face in the drawn plane, outboard of the tyre, on two standoff
    # brackets from the leg; it retracts rigidly with the leg
    ang_retract = np.radians(MAIN_RETRACT_DEG) * (-sgn)          # about +x
    door_down = leg_door_mesh(sgn)
    brackets = []
    for zb in (0.98, 0.62):
        a = T + (L - T) * (T[2] - zb) / (T[2] - L[2])
        b = np.array([a[0], sgn * (float(leg_door_bl(zb)) - LEG_DOOR_T), zb])
        brackets.append(cylinder(a, b, 0.012, n=10))

    gp = Part(f"gear_main_{side}", f"{'Right' if sgn > 0 else 'Left'} main gear (trailing link)", "gear",
              pivot=dict(origin=T.tolist(), axis=[1.0, 0, 0], kind="gear", retract=float(np.degrees(ang_retract))),
              explode=(0, sgn * 0.6, -0.7), group="Landing gear",
              material_note="Trailing link, hydraulic shock strut, electromechanical actuator",
              info={"tyre": "22 x 8.50-10, 55 psi", "track": "4,530 mm",
                    "retraction": "inward; tyre protrudes ~1 in (POH)", "door": "single leg-mounted door"})
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


def leg_door_mesh(sgn):
    """Leg door plate, gear down: leg_door_outline() (side view) on the drawn edge-on plane (outer face at
    leg_door_bl(z)), LEG_DOOR_T thick inboard; starboard for sgn = +1."""
    P = leg_door_outline()
    keep = np.r_[True, np.linalg.norm(np.diff(P, axis=0), axis=1) > 1e-6]
    P = P[keep]
    if np.linalg.norm(P[0] - P[-1]) < 1e-6:
        P = P[:-1]
    ys = np.asarray(leg_door_bl(P[:, 1]), float)
    outer = np.c_[P[:, 0], ys, P[:, 1]]
    inner = outer - [0.0, LEG_DOOR_T, 0.0]
    k = (LEG_DOOR["bl"][1] - LEG_DOOR["bl"][0]) / (P[:, 1].max() - P[:, 1].min())
    nrm = np.array([0.0, 1.0, k]) / np.hypot(1.0, k)
    f_out = planar_cap(outer, nrm)
    f_in = planar_cap(inner, -nrm)
    n = len(P)
    i = np.arange(n)
    V = np.vstack([outer, inner])
    Fc = np.vstack([np.stack([i, (i + 1) % n, (i + 1) % n + n], 1), np.stack([i, (i + 1) % n + n, i + n], 1)])
    rim = Mesh(V, Fc)
    c = outer.mean(0) - [0.0, 0.5 * LEG_DOOR_T, 0.0]
    if np.mean(np.sum((rim.V[rim.F].mean(1) - c) * rim.face_normals(), 1)) < 0:
        rim = rim.flipped()
    m = Mesh.merge([f_out, f_in, rim])
    return m if sgn > 0 else m.mirrored_y()


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


MAIN_BAY_ROOF_GAP = 0.006           # main-bay liner roof under the wing upper skin (m)


def _wing_z(x, y, upper):
    """Wing upper / lower surface WL at plan points (x, y) (arrays, |y| used)."""
    x, y = np.broadcast_arrays(np.asarray(x, float), np.abs(np.asarray(y, float)))
    out = np.empty(x.shape)
    for yy in np.unique(np.round(y, 6)):
        k = np.abs(y - yy) < 5e-7
        s = W.section_at(float(yy))
        xc = np.clip((x[k] - s.le[0]) / s.chord, 0, 1)
        out[k] = (s.upper if upper else s.lower)(xc)[..., 2]
    return out


def main_bay_outline(res=0.004):
    """Starboard plan outline (N, 2) of the main-gear bay liner: the zero contour of bays.main_bay_sdf."""
    import contourpy
    xs = np.arange(5.75, 6.85, res)
    ys = np.arange(1.00, 2.50, res)
    X, Y = np.meshgrid(xs, ys)
    lines = contourpy.contour_generator(X, Y, main_bay_sdf(X, Y)).lines(0.0)
    P = max(lines, key=len)
    if np.linalg.norm(P[0] - P[-1]) < 1e-9:
        P = P[:-1]
    return P


def bay_tubs(parts):
    """Zinc-chromate wheel-well liners (visible with the doors open).  Main bays: walls round bays.main_bay_sdf (wheel
    well + leg slot + brace slot / pocket) from the lower skin up to a roof MAIN_BAY_ROOF_GAP under the wing upper
    skin, so the stowed tyre, leg, shock strut and folded side brace lie inside the liner (M1 / M4 / M6)."""
    from cad.mesh import planar_cap
    from cad.sdf2d import rrect_outline
    meshes = []
    ol = main_bay_outline()
    zlo = _wing_z(ol[:, 0], ol[:, 1], False) - 0.004
    zhi = _wing_z(ol[:, 0], ol[:, 1], True) - MAIN_BAY_ROOF_GAP
    n = len(ol)
    k = np.arange(n)
    Fc = np.vstack([np.stack([k, (k + 1) % n, (k + 1) % n + n], 1), np.stack([k, (k + 1) % n + n, k + n], 1)])
    xs = np.linspace(ol[:, 0].min() - 0.01, ol[:, 0].max() + 0.01, 90)
    ys = np.linspace(ol[:, 1].min() - 0.01, ol[:, 1].max() + 0.01, 120)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    roof = grid_surface(np.stack([X, Y, _wing_z(X, Y, True) - MAIN_BAY_ROOF_GAP], -1))
    roof = trim(roof, main_bay_sdf(roof.V[:, 0], roof.V[:, 1]), "negative")
    if roof.N[:, 2].mean() > 0:
        roof = roof.flipped()
    for sgn in (1, -1):
        wall = Mesh(np.vstack([np.c_[ol[:, 0], sgn * ol[:, 1], zlo], np.c_[ol[:, 0], sgn * ol[:, 1], zhi]]), Fc)
        meshes.append(wall)
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
    p.add(Mesh.merge(meshes), "zinc_chromate")
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
