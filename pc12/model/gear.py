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
MAIN_AXLE = np.array([6.43, TRACK / 2, 0.265])
NOSE_AXLE = np.array([MAIN_AXLE[0] - WHEELBASE, 0.0, 0.212])
MAIN_TRUNNION = np.array([6.02, TRACK / 2, 0.990])   # sets the ~1 in retracted tyre protrusion (POH)
NOSE_PIVOT = np.array([3.08, 0.0, 1.12])
MAIN_TYRE = dict(R=0.2795, W=0.216, rim=0.127)      # 22 x 8.50-10
NOSE_TYRE = dict(R=0.2225, W=0.159, rim=0.076)      # 17.5 x 6.25-6

from model.bays import WELL, SLOT, NOSE_BAY, main_opening_sdf, nose_bay_sdf


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
                    axis_origin=center + Wd * 0.43 * axis, axis_dir=axis)
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
    L = np.array([6.02, TRACK / 2, 0.43]) * S          # trailing-link pivot
    yax = np.array([0, 1.0, 0])
    struct = []
    # trunnion + leg
    struct.append(cylinder(T - [0.13, 0, 0], T + [0.13, 0, 0], 0.045, n=20))
    struct.append(revolve([(0, 0.058), (0.60, 0.047), (0.62, 0.0)], n=24, axis_origin=T,
                          axis_dir=(L - T) / np.linalg.norm(L - T)))
    # yoke + fork arms (straddling the wheel)
    fy = 0.14
    struct.append(cylinder(L - sgn * fy * yax, L + sgn * fy * yax, 0.036, n=16))
    for s in (-1, 1):
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
    struct.append(cylinder(A - fy * yax, A + fy * yax, 0.026, n=16))      # axle
    # shock absorber (inboard side so it stows inside the wing)
    s_in = -sgn * 0.19
    S1 = np.array([6.05, T[1] + s_in, 0.95])
    S2 = np.array([6.30, T[1] + s_in * 0.95, 0.37])
    mid = S1 + 0.55 * (S2 - S1)
    shock_body = cylinder(S1, mid, 0.042, n=18)
    shock_rod = cylinder(mid - 0.05 * (S2 - S1), S2, 0.027, n=14)
    lugs = [cylinder(S1 - [0, 0.04 * sgn, 0], S1 + [0, 0.04 * sgn, 0], 0.03, n=12),
            box(S2 + [0.0, -s_in * 0.4, 0.0], (0.06, abs(s_in) * 0.9, 0.04)),
            box(np.array([6.03, T[1] + s_in * 0.5, 0.95]), (0.06, abs(s_in), 0.05))]
    wh = wheel(A, yax, MAIN_TYRE, n=44, brake_side=-sgn)

    # leg door: wing lower-skin patch over the leg slot (retracted position) rotated down with the leg
    ang_retract = np.radians(90.0) * (-sgn)          # about +x
    door = leg_door_patch(sgn)
    Rm = rotation_about((1, 0, 0), -ang_retract, T)
    door_down = door.transformed(Rm)

    gp = Part(f"gear_main_{side}", f"{'Right' if sgn > 0 else 'Left'} main gear (trailing link)", "gear",
              pivot=dict(origin=T.tolist(), axis=[1.0, 0, 0], kind="gear", retract=float(np.degrees(ang_retract))),
              explode=(0, sgn * 0.6, -0.7), group="Landing gear",
              material_note="Trailing link, hydraulic shock strut, electromechanical actuator",
              info={"tyre": "22 x 8.50-10, 55 psi", "track": "4,530 mm",
                    "retraction": "inward; tyre protrudes ~1 in (POH)", "door": "single leg-mounted door"})
    gp.add(Mesh.merge(struct + lugs), "gear_leg").add(Mesh.merge([shock_body]), "gear_leg").add(shock_rod, "chrome")
    for m, mat in wh:
        gp.add(m, mat)
    gp.add(door_down, "paint_white")
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


def leg_door_patch(sgn):
    s = SLOT
    m = wing_lower_patch(s["cx"] - s["hx"] - 0.02, s["cx"] + s["hx"] + 0.02, s["cy"] - s["hy"] - 0.02,
                         s["cy"] + s["hy"] + 0.02, n=16)
    f = lambda mm: sdf2d.rrect(mm.V[:, 0], mm.V[:, 1], s["cx"], s["cy"], s["hx"] - 0.004, s["hy"] - 0.004, s["r"])
    m = trim(m, f(m), "negative")
    m = solidify(m.offset(-0.001), 0.02)
    return m if sgn > 0 else m.mirrored_y()


def well_door_patch(sgn):
    s = WELL
    m = wing_lower_patch(s["cx"] - s["hx"] - 0.02, s["cx"] + s["hx"] + 0.02, s["cy"] - s["hy"] - 0.02,
                         s["cy"] + s["hy"] + 0.02, n=18)
    f = lambda mm: sdf2d.rrect(mm.V[:, 0], mm.V[:, 1], s["cx"], s["cy"], s["hx"] - 0.004, s["hy"] - 0.004, s["r"])
    m = trim(m, f(m), "negative")
    m = solidify(m.offset(-0.001), 0.02)
    return m if sgn > 0 else m.mirrored_y()


def build_nose(parts):
    P = NOSE_PIVOT
    A = NOSE_AXLE
    yax = np.array([0, 1.0, 0])
    low = np.array([2.975, 0, 0.40])            # piston bottom / fork crown
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
    ang = -95.0
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
        dp = Part(f"gear_door_N{side}", f"Nose gear door ({'right' if sgn > 0 else 'left'})", "gear",
                  pivot=dict(origin=[b["cx"], hy, hz], axis=[1.0, 0, 0], kind="gear_door", open=float(85.0 * sgn)),
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


def bay_tubs(parts):
    """Zinc-chromate wheel-well liners (visible with the doors open)."""
    from cad.mesh import planar_cap
    from cad.sdf2d import rrect_outline
    meshes = []
    for sgn in (1, -1):
        for o in (WELL, SLOT):
            ol = rrect_outline(o["cx"], o["cy"], o["hx"], o["hy"], o["r"], n_corner=8)
            zs = []
            for x, y in ol:
                sec = W.section_at(y)
                xc = np.clip((x - sec.le[0]) / sec.chord, 0, 1)
                zs.append(float(sec.lower(np.array(xc))[2]))
            zs = np.array(zs)
            ztop = zs.min() + 0.20
            lo = np.stack([ol[:, 0], ol[:, 1] * sgn, zs - 0.004], 1)
            hi = np.stack([ol[:, 0], ol[:, 1] * sgn, np.full(len(zs), ztop)], 1)
            n = len(ol)
            V = np.vstack([lo, hi])
            k = np.arange(n)
            Fc = np.vstack([np.stack([k, (k + 1) % n, (k + 1) % n + n], 1), np.stack([k, (k + 1) % n + n, k + n], 1)])
            meshes.append(Mesh(V, Fc))
            meshes.append(planar_cap(hi, (0, 0, -1)))
    b = NOSE_BAY
    ol = rrect_outline(b["cx"], b["cy"], b["hx"], b["hy"], b["r"], n_corner=8)
    zs = np.array([float(F.z_bot(x)) + 0.01 for x, y in ol])
    lo = np.stack([ol[:, 0], ol[:, 1], zs], 1)
    hi = np.stack([ol[:, 0], ol[:, 1], np.full(len(zs), 1.30)], 1)
    n = len(ol)
    V = np.vstack([lo, hi])
    k = np.arange(n)
    Fc = np.vstack([np.stack([k, (k + 1) % n, (k + 1) % n + n], 1), np.stack([k, (k + 1) % n + n, k + n], 1)])
    meshes.append(Mesh(V, Fc))
    meshes.append(planar_cap(hi, (0, 0, -1)))
    p = Part("gear_bays", "Wheel wells (zinc-chromate liners)", "gear", group="Landing gear",
             material_note="Primed aluminium liners")
    p.add(Mesh.merge(meshes), "zinc_chromate")
    parts[p.id] = p



# ---------------------------------------------------------------------------
# over-centre folding struts (POH: "overcenter two piece drag link")
# ---------------------------------------------------------------------------
def brace_parts(parts):
    from model.brace import solve_knee
    specs = []
    for side, sgn in (("R", 1), ("L", -1)):
        T = MAIN_TRUNNION * [1, sgn, 1]
        A = np.array([6.0, 1.95 * sgn, 1.00])
        B0 = np.array([6.0, 2.215 * sgn, 0.76])
        ref = np.array([0, -0.30 * sgn, 0.95])
        specs.append((f"brace_main_{side}", f"gear_main_{side}", A, B0, T, np.array([1.0, 0, 0]), ref,
                      f"{'Right' if sgn > 0 else 'Left'} main-gear folding side brace"))
    specs.append(("brace_nose", "gear_nose", np.array([3.46, 0, 1.16]), np.array([3.033, 0, 0.80]), NOSE_PIVOT,
                  np.array([0, 1.0, 0]), np.array([0.72, 0, -0.695]), "Nose-gear folding drag brace"))
    for pid, gear_id, A, B0, T, axis, ref, name in specs:
        L = np.linalg.norm(B0 - A) / 2 * 1.0005
        K0 = solve_knee(A, B0, L, L, axis, ref)
        up = Part(pid + "_up", name + " (upper link)", "gear",
                  pivot=dict(origin=A.tolist(), axis=axis.tolist(), kind="brace", role="upper", gear=gear_id,
                             A=A.tolist(), B0=B0.tolist(), K0=K0.tolist(), L1=float(L), L2=float(L),
                             bend=ref.tolist()),
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
