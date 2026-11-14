"""
SF50 landing gear: retractable tricycle, single wheel at each location (EASA TCDS), trailing-link mains (AOPA) that
retract inward into the wing with one leg-mounted door each (AFM walk-around 'MLG Door'), air/oil oleo struts (AFM
8-25), castering nose gear (AFM) retracting forward into the keel bay [inf: bay ahead of the leg in AFM Fig 1-1] with
a nose-gear landing light on the strut (Cirrus: 'nose gear landing light').
Tyres: mains 18 x 5.5, nose 5.00-5 (AFM 8-26).  Track 11.2 ft (AFM Fig 1-1); wheelbase 3.305 m [inf: AFM Fig 1-1].
"""
from __future__ import annotations
import numpy as np

from sf50_kernel import (Mesh, revolve, cylinder, box, superellipsoid, sweep_tube, disk, planar_cap, rotation_about,
                         rotation_matrix, grid_surface, Part)
import sf50_geom as G
from sf50_wing import WELL_C, SLOT, lens_bump


def tyre(center, axis, D, W, n=48, rim_frac=0.56):
    """Tyre (revolved toroidal profile) + wheel hub; axis = wheel axle direction."""
    R, w = D / 2, W / 2
    r_rim = R * rim_frac
    th = np.linspace(-np.pi / 2, np.pi / 2, 15)
    prof = [(-w * 0.80, r_rim)]
    for t in th:
        prof.append((w * np.sin(t), r_rim + (R - r_rim) * (0.55 + 0.45 * np.cos(t)) if abs(t) < np.pi / 2 - 1e-6
                     else r_rim))
    # smooth crown: super-elliptic shoulder
    prof = [(-w * 0.82, r_rim)]
    for t in np.linspace(np.pi, 0, 21):
        c, s = np.cos(t), np.sin(t)
        prof.append((w * np.sign(c) * abs(c) ** 0.7, r_rim + (R - r_rim) * abs(s) ** 0.45))
    prof.append((w * 0.82, r_rim))
    a = np.asarray(axis, float) / np.linalg.norm(axis)
    t = revolve(prof, n=n, axis_origin=center, axis_dir=a)
    hub = revolve([(-w * 0.85, 0.0), (-w * 0.85, r_rim * 0.35), (-w * 0.80, r_rim * 0.95), (w * 0.80, r_rim * 0.95),
                   (w * 0.85, r_rim * 0.35), (w * 0.85, 0.0)], n=32, axis_origin=center, axis_dir=a)
    return t, hub


# ------------------------------------------------------------------------------------------------ main gear
LINK_DY, LINK_R = 0.092, 0.020   # trailing link: inboard offset of its axis from the wheel centre, tube radius [inf]


def main_geometry(sgn):
    """Key points (right gear for sgn=+1; mirrored for -1)."""
    y0 = G.GEAR_BL
    T = np.array([5.085, y0, 0.820 + G.WING_DZ])       # trunnion (inside the wing) = retraction pivot; rides with the wing
    # trailing-link pivot at the strut foot, link inboard of the tyre [inf]. Fix round 3: the link runs 0.092 m inboard of
    # the wheel centre (was 0.100, radius 0.020 was 0.022): stowed, the inboard side faces up, and the old link end stood
    # 3.5-4.5 mm above the wing upper skin at the root (BL 1.02); it now stays below it (test: no gear vertex above the skin)
    L0 = np.array([5.095, y0 - LINK_DY, 0.380])
    A = np.array([G.X_MAIN_AXLE, y0, G.MAIN_TIRE_D / 2])  # axle centre (tyre on the ground)
    m = np.array([1, sgn, 1])
    return T * m, L0 * m, A * m


def _skin_z(bl):
    """Wing lower-skin height across the leg slot (FS 5.1), linear fit of sf50_wing.wing_surface_z [inf]."""
    return 0.775 + G.WING_DZ + 0.106 * (bl - G.GEAR_BL)


def build_main(parts, side, sgn):
    T, L0, A = main_geometry(sgn)
    ys = np.array([0, sgn, 0.0])
    st = []
    # oleo strut in the plane of the trunnion (stows inside the wing), chrome piston
    st.append(cylinder(T + [0, 0, 0.02], T + [0.005, 0, -0.30], 0.040, n=20))
    piston = cylinder(T + [0.005, 0, -0.26], [L0[0], T[1], L0[2] + 0.03], 0.027, n=16)
    foot = np.array([L0[0], T[1], L0[2]])
    st.append(cylinder(T + [-0.10, 0, 0], T + [0.10, 0, 0], 0.030, n=16))              # trunnion tube (retraction axis)
    st.append(sweep_tube(np.array([foot + [0, sgn * 0.02, 0.02], L0]), 0.030, n=12))    # foot fitting -> link pivot
    # trailing link arm (inboard of the tyre) L0 -> axle end, axle stub to the hub
    arm_end = A + [0, -sgn * LINK_DY, 0]
    st.append(sweep_tube(np.array([L0, arm_end]), LINK_R, n=14))
    st.append(cylinder(arm_end, A - [0, sgn * 0.040, 0], 0.020, n=14))
    # shock absorber: strut collar -> link mid-point (inboard)
    s1 = T + [0.07, -sgn * 0.045, -0.10]
    s2 = 0.5 * (L0 + arm_end) + [0.0, 0.0, 0.03]
    shock = [cylinder(s1, s1 + 0.6 * (s2 - s1), 0.022, n=12)]
    shock_rod = cylinder(s1 + 0.55 * (s2 - s1), s2, 0.013, n=10)
    tyre_m, hub = tyre(A, ys, G.MAIN_TIRE_D, G.MAIN_TIRE_W)
    # brake disc + caliper on the inboard side of the wheel
    disc = cylinder(A - [0, sgn * 0.074, 0], A - [0, sgn * 0.082, 0], 0.105, n=32)
    cal = box(A - [0.0, sgn * 0.085, -0.085], (0.07, 0.025, 0.045))
    # leg door, outboard of the strut; its plane leans so that it lies along the sloping lower skin when retracted
    # (retraction maps an offset (dy, dz) from the trunnion to (BL = T_y + dz, z = T_z - dy) on the right side)
    def door_pt(x, z):
        dz = z - abs(T[2])
        dy = abs(T[2]) - _skin_z(G.GEAR_BL + dz) + 0.003
        return [x, sgn * (G.GEAR_BL + dy), z]
    outline = [(4.905, 0.765 + G.WING_DZ), (5.330, 0.765 + G.WING_DZ), (5.255, 0.390), (5.120, 0.335), (4.985, 0.385)]
    dp = np.array([door_pt(x, z) for x, z in outline])
    door = planar_cap(dp, (0, sgn, 0))
    door2 = door.translated([0, -sgn * 0.008, 0]).flipped()
    ang = -sgn * 90.0      # inward: about +x, right gear -90 deg, left +90 deg
    gp = Part(f"gear_main_{side}", f"{'Right' if sgn > 0 else 'Left'} main gear (trailing link)", "gear",
              pivot=dict(origin=T.tolist(), axis=[1.0, 0.0, 0.0], kind="gear", retract=float(ang)),
              group="Landing gear", material_note="Trailing link, air/oil oleo (AFM 8-25), retracts inward into the wing",
              info={"tyre": "18 x 5.5, 8-ply, 105 psi (AFM 8-26)", "track": f"{G.TRACK:.3f} m (AFM Fig 1-1, 11.2 ft)",
                    "door": "one leg-mounted door (AFM walk-around 'MLG Door')",
                    "retraction": "inward, tyre stowed flat in the wing [inf]"})
    gp.add(Mesh.merge(st), "gear_leg").add(piston, "chrome").add(Mesh.merge(shock), "gear_leg").add(shock_rod, "chrome")
    gp.add(tyre_m, "tire").add(hub, "wheel").add(disc, "metal_dark").add(cal, "black")
    gp.add(Mesh.merge([door, door2]), "paint_white")
    parts[gp.id] = gp
    return gp


# ------------------------------------------------------------------------------------------------ nose gear
NOSE_P = np.array([2.165, 0.0, 0.790])        # retraction pivot (top of the strut, in the bay)
NOSE_A = np.array([G.X_NOSE_AXLE, 0.0, G.NOSE_TIRE_D / 2])


def build_nose(parts):
    P, A = NOSE_P, NOSE_A
    st = []
    foot = np.array([2.105, 0.0, 0.40])
    st.append(cylinder(P + [0, 0, 0.02], foot + [0, 0, 0.14], 0.036, n=18))
    piston = cylinder(foot + [0, 0, 0.18], foot, 0.024, n=14)
    st.append(cylinder(P + [0, -0.12, 0], P + [0, 0.12, 0], 0.028, n=14))      # trunnion (lateral axis)
    # fork: two plates from the foot to the axle ends
    for s in (-1, 1):
        a = foot + [0, s * 0.082, -0.01]
        b = A + [0, s * 0.082, 0]
        st.append(sweep_tube(np.array([foot + [0, s * 0.03, 0.02], a, b]), 0.016, n=10))
    st.append(cylinder(A + [0, -0.09, 0], A + [0, 0.09, 0], 0.015, n=12))
    # torque links [inf]
    tl = [sweep_tube(np.array([foot + [-0.035, 0, 0.17], foot + [-0.10, 0, 0.09], foot + [-0.035, 0, 0.0]]), 0.010, n=8)]
    # drag brace from the strut to the trunnion fitting [inf]
    db = sweep_tube(np.array([foot + [0.02, 0, 0.22], P + [0.06, 0, -0.05]]), 0.016, n=10)
    tyre_m, hub = tyre(A, (0, 1, 0), G.NOSE_TIRE_D, G.NOSE_TIRE_W, n=40)
    # landing light on the strut, facing forward (Cirrus: 'nose gear landing light')
    lamp_c = foot + [-0.075, 0.0, 0.22]
    lamp_body = cylinder(lamp_c + [0.04, 0, 0], lamp_c, 0.045, n=20)
    lamp_lens = lens_bump(lamp_c + [-0.002, 0, 0], (-1, 0, 0), 0.042, 0.012)
    lamp_em = disk(lamp_c + [-0.001, 0, 0], (-1, 0, 0), 0.034, n=20)
    gp = Part("gear_nose", "Nose gear (castering, retracts forward)", "gear",
              pivot=dict(origin=P.tolist(), axis=[0.0, 1.0, 0.0], kind="gear", retract=100.0),
              group="Landing gear", material_note="Castering nose wheel (AFM 8-26), air/oil oleo, landing light on the strut",
              info={"tyre": "5.00-5, 10-ply, 88 psi (AFM 8-26)", "retraction": "forward into the keel bay [inf]",
                    "wheelbase": f"{G.WHEELBASE:.3f} m [inf: AFM Fig 1-1 side view]"})
    gp.add(Mesh.merge(st), "gear_leg").add(piston, "chrome").add(Mesh.merge(tl + [db]), "gear_leg")
    gp.add(tyre_m, "tire").add(hub, "wheel").add(lamp_body, "metal_dark").add(lamp_em, "light_white").add(lamp_lens, "lens")
    gp.info["light_anchors"] = {"taxi": {"p": (lamp_c + [-0.01, 0, 0]).tolist(), "colour": "white",
                                         "src": "Cirrus Vision Jet page: 'new nose gear landing light'; AFM 'NOSE LAND LIGHT' [inf: position]"}}
    parts[gp.id] = gp


def build(parts):
    build_main(parts, "L", -1)
    build_main(parts, "R", 1)
    build_nose(parts)


def retracted_points():
    """For checks: where the axles end up when retracted (model coords)."""
    out = {}
    for side, sgn in (("L", -1), ("R", 1)):
        T, L0, A = main_geometry(sgn)
        M = rotation_about((1, 0, 0), np.radians(-sgn * 90.0), T)
        out[f"main_{side}"] = (M[:3, :3] @ A + M[:3, 3]).tolist()
    M = rotation_about((0, 1, 0), np.radians(100.0), NOSE_P)
    out["nose"] = (M[:3, :3] @ NOSE_A + M[:3, 3]).tolist()
    return out
