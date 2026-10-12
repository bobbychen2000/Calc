"""Flight deck r1, track A fit checks (28-29), run by test/fit_check.py after its own checks (or standalone:
python3 test/fit_fd_a.py builds the flight deck alone).

28. the rudder pedals over their travel (+/- PEDALS travel at the pad) and the 95th-pct male's shoes on them clear the
    footwell walls (fd_detail_a.footwell_walls: tunnel sides, outboard walls, the panel's underside, the cubby) by
    >= 10 mm; the 95th-pct legs (thighs, knees, shanks: interior.leg_spheres at his L6B seat setting) clear the walls and
    the cubby too
29. the yokes over their whole pitch travel (YOKE travel: push 65 mm -- OWNER DECISION 2026-10-11, the [E] 90 brought
    the grips within ~8 mm of the bare panel face wings level and into it from ~45 deg of roll -- and pull 90) and +/-
    YOKE roll every 10 deg clear the panel around them -- the lower panel's plates, switch blocks, handles and knobs, the
    glareshield items, the stack -- by >= 3 mm (the column runs through its well by design: column excepted); 29b the
    full push at every 5 deg of roll, >= 3 mm too
"""
from __future__ import annotations

import math
import sys

import numpy as np

if "parts" not in globals():                                     # standalone: the flight deck alone
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
    from model import interior as _I0
    parts = {}
    _I0.build_flightdeck(parts, seats=False, ceiling=[])
    fails, opens = [], []

    def report(name, ok, detail="", open_item=False):
        tag = "open" if open_item else ("ok" if ok else "FAIL")
        print(f"  [{tag}] {name}" + (f": {detail}" if detail else ""))
        if open_item:
            opens.append(name)
        elif not ok:
            fails.append(name)
    _STANDALONE = True
else:
    _STANDALONE = False

from scipy.spatial import cKDTree  # noqa: E402
from model import interior as IA, flightdeck as FDA  # noqa: E402


def _rot(V, origin, axis, deg):
    a = math.radians(deg)
    k = np.asarray(axis, float) / np.linalg.norm(axis)
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    R = np.eye(3) + math.sin(a) * K + (1 - math.cos(a)) * K @ K
    return (np.asarray(V, float) - origin) @ R.T + origin


def _tri_samples(T, step=0.004):
    """Points on triangles T (n, 3, 3): vertices, edge midpoints, centroids, plus a grid on the large ones."""
    out = [T.reshape(-1, 3), T.mean(1), 0.5 * (T + np.roll(T, 1, 1)).reshape(-1, 3)]
    big = np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1) * 0.5 > step * step
    if big.any():
        Tb = T[big]
        n = 6
        uv = np.array([(i / n, j / n) for i in range(n + 1) for j in range(n + 1 - i)])
        P = Tb[:, None, 0] + uv[None, :, 0, None] * (Tb[:, None, 1] - Tb[:, None, 0]) + \
            uv[None, :, 1, None] * (Tb[:, None, 2] - Tb[:, None, 0])
        out.append(P.reshape(-1, 3))
    return np.unique(np.round(np.vstack(out), 6), axis=0)          # duplicates make cKDTree queries crawl


_groups = FDA.build_flightdeck(groups=True)
WALL_T = np.vstack([m.V[m.F] for m, _ in _groups["footwell"]])
WALL_P = _tri_samples(WALL_T)
wall_tree = cKDTree(WALL_P)

# 28 ---------------------------------------------------------------------------- pedals, shoes, legs vs the footwell
piv = FDA.control_pivots()
PD = IA.PEDALS
worst_ped = (np.inf, None)
for pid, pv in piv.items():
    if pv["kind"] != "pedal" or pid not in parts:
        continue
    V = np.vstack([m.V for m, _ in parts[pid].meshes])
    for yaw in (-1.0, 0.0, 1.0):
        ang = -pv["gearing"] * yaw * pv["travel_deg"]
        d, _ = wall_tree.query(_rot(V, np.asarray(pv["origin"]), pv["axis"], ang), distance_upper_bound=0.10)
        if d.min() < worst_ped[0]:
            worst_ped = (float(d.min()), f"{pid} yaw {yaw:+.0f}")
SHOE_R = 0.045                                                  # shoe half-width (a 95th-pct shoe ~ 0.10 wide)
worst_shoe = (np.inf, None)
worst_leg = (np.inf, None)
for side in (-1, 1):
    p95 = IA.crew_setting(1.0, side)
    pp = IA.pedal_points(0.0)
    hx, hz = (float(v) for v in PD["pivot"])
    for dd in (-1, 1):
        yc = side * float(IA.CREW_SEAT["bl"]) + dd * float(PD["dy"])
        pv = piv["pedal_" + ("L" if side < 0 else "R") + ("L" if dd < 0 else "R")]
        foot = [np.array([p95["ankle"][0], yc, p95["ankle"][1]]), np.array([p95["ball"][0], yc, p95["ball"][1]]),
                np.array([pp["toe"][0], yc, pp["toe"][1]])]
        S = np.array([a + t * (b - a) for a, b in zip(foot[:-1], foot[1:]) for t in np.linspace(0, 1, 6)])
        for yaw in (-1.0, 0.0, 1.0):
            ang = -pv["gearing"] * yaw * pv["travel_deg"]
            Sr = _rot(S, np.asarray(pv["origin"]), pv["axis"], ang)
            d, _ = wall_tree.query(Sr, distance_upper_bound=0.20)
            c = float((d - SHOE_R).min())
            if c < worst_shoe[0]:
                worst_shoe = (c, f"{'P' if side < 0 else 'CP'} {'L' if dd < 0 else 'R'} foot, yaw {yaw:+.0f}")
    sph = np.array(IA.leg_spheres(p95, side * IA.CREW_SEAT["bl"]))
    d, _ = wall_tree.query(sph[:, :3], distance_upper_bound=0.30)
    c = float((d - sph[:, 3]).min())
    if c < worst_leg[0]:
        worst_leg = (c, "P" if side < 0 else "CP")
crit = 0.010
report("footwell walls clear of the rudder pedals over their travel, the 95th-pct shoes on them and his legs "
       f"(>= {crit * 1000:.0f} mm)", min(worst_ped[0], worst_shoe[0], worst_leg[0]) >= crit,
       f"pedals {worst_ped[0] * 1000:.1f} mm ({worst_ped[1]}), shoes {worst_shoe[0] * 1000:.1f} mm ({worst_shoe[1]}, r "
       f"{SHOE_R * 1000:.0f}), legs {worst_leg[0] * 1000:.1f} mm ({worst_leg[1]})")

# 29 ---------------------------------------------------------------------------- yokes over their travel vs the panel
Y = IA.YOKE
PANEL_T = np.vstack([m.V[m.F] for g in ("panel", "glareshield", "pedestal", "displays") for m, mat in _groups[g]
                     if mat not in ("rubber_black",)])
_hubs = np.array([IA.yoke_hub(s_) for s_ in (-1, 1)])
_near = np.zeros(len(PANEL_T), bool)
for _h in _hubs:                                                 # only what the yokes can reach (+/- 0.3 / 0.25 m)
    _near |= ((np.abs(PANEL_T[:, :, 1] - _h[1]) < 0.30) & (np.abs(PANEL_T[:, :, 2] - _h[2]) < 0.25) &
              (PANEL_T[:, :, 0] > _h[0] - 0.20)).any(1)
PANEL_P = _tri_samples(PANEL_T[_near])
def _yoke_sweep(pushes, roll_step=10.0):
    worst = (np.inf, None)
    for side in (-1, 1):
        pid = "yoke_" + ("L" if side < 0 else "R")
        if pid not in parts:
            continue
        hub = IA.yoke_hub(side)
        col_r = float(Y["column_r"])
        V = np.vstack([m.V for m, mat in parts[pid].meshes if mat != "rubber_black"])
        # the column (anything within its radius + 2 mm of its axis, forward of the hub face) and its bellows (rubber)
        # run through the well by design
        rad = np.hypot(V[:, 1] - hub[1], V[:, 2] - hub[2])
        V = V[~((rad < col_r + 0.002) & (V[:, 0] < hub[0] + 0.012))]
        near_P = PANEL_P[(np.abs(PANEL_P[:, 1] - hub[1]) < 0.30) & (np.abs(PANEL_P[:, 2] - hub[2]) < 0.25)]
        tree = cKDTree(near_P)
        for t in pushes:
            for roll in np.arange(-float(Y["roll"]), float(Y["roll"]) + 1e-9, roll_step):
                Vr = _rot(V, hub, [-1.0, 0.0, 0.0], roll) + [t, 0.0, 0.0]
                d, k = tree.query(Vr, distance_upper_bound=0.05)          # (far queries crawl in a planar cloud)
                if not np.isfinite(d).any():
                    continue
                i = int(np.argmin(d))
                if d[i] < worst[0]:
                    worst = (float(d[i]), f"{pid} pitch {t * 1000:+.0f} mm roll {roll:+.0f} deg near STA "
                                          f"{near_P[k[i], 0]:.3f} BL {near_P[k[i], 1]:+.3f} WL {near_P[k[i], 2]:.3f}")
    return worst


t0, t1 = (float(v) for v in Y["travel"])
w_hard = _yoke_sweep(np.r_[np.linspace(t0, 0.0, 5), np.linspace(0.0, t1, 4)[1:]])
report(f"yokes over the whole pitch travel ({t0 * 1000:+.0f} .. {t1 * 1000:+.0f} mm, YOKE travel: the push owner "
       f"2026-10-11), roll +/-{Y['roll']:.0f} deg every 10, clear the panel, glareshield and stack detail (>= 3 mm; "
       "column excepted)", w_hard[0] >= 0.003, f"{w_hard[0] * 1000:.1f} mm ({w_hard[1]})")
# 29b: the full push at every 5 deg of roll.  With the measured hub (hub_dx) and the panel face's [E] 12 deg tilt the
# [E] 90 mm of push brought the grips within ~8 mm of the bare lower-panel face wings level and across it from ~45 deg
# of roll (reported as an open owner decision); OWNER DECISION 2026-10-11: the push shortened to 65 mm, the pull kept
w_full = _yoke_sweep([t0], roll_step=5.0)
report(f"yokes at full push ({t0 * 1000:+.0f} mm, YOKE travel: owner 2026-10-11), roll every 5 deg, vs the lower panel "
       "(>= 3 mm)", w_full[0] >= 0.003, f"{w_full[0] * 1000:.1f} mm ({w_full[1]})")

if _STANDALONE:
    print("FIT FD-A OK" if not fails else "FIT FD-A FAIL: " + "; ".join(fails))
    sys.exit(1 if fails else 0)
