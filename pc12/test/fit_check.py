"""Interference / fit checks of the built parts (model axes, metres).  Every x-range comes from fuselage.STA.

 1. interior, engine and inlet duct lie inside the fuselage OML (minus a margin)
 2. the spinner meets the cowl front (base ring on the cowl-front ring, no gap / step) and encloses the gearbox
 3. the wing carry-through stays under the cabin floor (fuselage.CABIN_FLOOR_WL - 15 mm) inside the fuselage
 4. dorsal fin, fin and rudder stay outside the fixed tail cone; the rudder at +/-25 deg clears the fin tip,
    the fixed cove and the tail-cone closure
 5. retracted gear: nose unit above the keel and inside the bay / pedestal tunnel, main tyres at most ~1 in proud
    of the wing lower skin, nothing above the upper skin
 6. folding-strut knees over 0-100 % retraction: main knees between the wing skins, nose knee inside the bay
 7. cabin furniture clear of the airstair entry
 8. the tailplane horn balances (carried by the elevators) clear the fixed tips at full elevator travel
 9. the airstair and cargo doors clear the wing-root fairing (fillet / nose) from closed to fully open
Prints one line per check and 'FIT OK' / 'FIT FAIL' (exit code 1 on failure).
"""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
import numpy as np
from cad.mesh import rotation_about
from model.build import build_parts
from model import fuselage as F, empennage as E, gear as G, wing as W, powerplant as PP
from model.brace import pose
from model.fuselage_parts import openings_table

X0, X1 = F.STA["cowl_front"], F.STA["tail_end"]
MARGIN = 0.02
parts = build_parts()
fails = []


def report(name, ok, detail=""):
    print(f"  [{'ok' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))
    if not ok:
        fails.append(name)


def verts(pid, mats=None):
    return np.vstack([m.V for m, mm in parts[pid].meshes if mats is None or mm in mats])


def posed(pid, M):
    V = verts(pid)
    return V @ M[:3, :3].T + M[:3, 3]


def outside_oml(V, margin):
    x, y, z = V[:, 0], V[:, 1], V[:, 2]
    inx = (x > X0) & (x < X1)
    xc = np.clip(x, X0, X1)
    ylim = F.side_y(xc, z) - margin
    return inx & ((np.abs(y) > ylim) | (z > F.z_top(xc) - margin) | (z < F.z_bot(xc) + margin))


# 1 ------------------------------------------------------------------------------------------------ inside the OML
for pid, p in parts.items():
    if p.step not in ("interior",) and not pid.startswith("eng_") and pid not in ("engine_mount", "inlet_duct"):
        continue
    V = verts(pid)
    bad = outside_oml(V, MARGIN)
    n = int(bad.sum())
    det = f"{n}/{len(V)} verts outside" + (f"; x {V[bad, 0].min():.2f}-{V[bad, 0].max():.2f}, z {V[bad, 2].min():.2f}-"
                                            f"{V[bad, 2].max():.2f}" if n else "")
    report(f"{pid} inside the OML", n == 0, det)

# 2 ------------------------------------------------------------------------------------------------ spinner / cowl
sp = parts["propeller"].meshes[0][0].V                     # spinner shell (first mesh)
a = -PP.thrust_dir()
tip = PP.axis_point(F.STA["spinner_tip"])
s_max = float(((sp - tip) @ a).max())
t_ = np.linspace(0, 1, 721, endpoint=False)
cf = F.section(np.full_like(t_, X0), t_)                   # cowl-front ring
s_c = (cf - tip) @ a
r_c = np.linalg.norm((cf - tip) - np.outer(s_c, a), axis=1)
report("spinner meets the cowl front (ring covered by the spinner / skirt, radial step)",
       bool((s_c < s_max - 0.003).all() and np.abs(r_c - F.SPINNER_R).max() < 0.006),
       f"cowl-front ring {1000 * (s_max - s_c).min():.0f}-{1000 * (s_max - s_c).max():.0f} mm ahead of the skirt end, "
       f"radial step max {1000 * np.abs(r_c - F.SPINNER_R).max():.1f} mm")
rgb = verts("eng_rgb")
ahead = rgb[rgb[:, 0] < X0]
if len(ahead):
    t, rr = PP.spinner_profile(400)
    sa = (ahead - tip) @ a
    ra = np.linalg.norm((ahead - tip) - np.outer(sa, a), axis=1)
    L = (X0 - F.STA["spinner_tip"]) * np.linalg.norm([1.0, PP._TY, PP._TT])
    rs = np.interp(sa / L, t, rr)
    report("gearbox ahead of the cowl front inside the spinner", bool((ra < rs - 0.005).all()),
           f"min clearance {1000 * (rs - ra).min():.0f} mm")

# 3 ------------------------------------------------------------------------------------------------ carry-through
lim = F.CABIN_FLOOR_WL - W.CS_FLOOR_CLEAR + 1e-6
for pid in ("wing_R", "wing_L", "structure"):
    V = verts(pid, None if pid != "structure" else ("interior_green",))
    ins = (np.abs(V[:, 1]) < F.side_y(np.clip(V[:, 0], X0, X1), V[:, 2]) - 0.01) & (V[:, 0] > 4.4) & (V[:, 0] < 9.85)
    hi = ins & (V[:, 2] > lim)
    report(f"{pid}: carry-through under the cabin floor (WL <= {lim * 1000:.0f})", not hi.any(),
           f"max WL inside the fuselage {V[ins, 2].max() * 1000:.1f}")


# 4 ------------------------------------------------------------------------------------------------ tail
def in_fixed_cone(V, margin=0.005):
    return (E.oml_field(V) < -margin) & (E.tail_cut_field(V[:, 0], V[:, 2]) < -margin)


for pid in ("dorsal_fin", "fin", "rudder"):
    V = verts(pid)
    if pid == "fin":                                        # the ventral fairing is buried in the keel by design
        V = V[V[:, 2] > F.z_mw(np.clip(V[:, 0], X0, X1)) - 0.1]
    bad = in_fixed_cone(V, 0.008)
    report(f"{pid} outside the fixed tail cone", not bad.any(), f"{int(bad.sum())} verts inside")
rp = parts["rudder"].pivot
ax = np.asarray(rp["axis"], float)
xc_cove = E.RUD_XH - 0.5 * float(E.FIN_AF_ROOT.thickness(E.RUD_XH)) - E.RUD_COVE_GAP
for deg in (-25.0, 25.0):
    M = rotation_about(ax, np.radians(deg), rp["origin"])
    V = np.vstack([posed("rudder", M), posed("rudder_tab", M)])
    hw = E.fin_halfwidth(V[:, 0], V[:, 2])
    tipi = (V[:, 2] > E.rudder_split_z(V[:, 0]) + E.RUD_EDGE_GAP + 0.002) & (np.abs(V[:, 1]) < hw - 0.002)
    xc = (V[:, 0] - E.fin_le(V[:, 2])) / (E.fin_te(V[:, 2]) - E.fin_le(V[:, 2]))
    cove = (xc < xc_cove - 0.002) & (np.abs(V[:, 1]) < hw - 0.002) & (V[:, 2] > F.z_bot(np.clip(V[:, 0], X0, X1)) + 0.003)
    cone = in_fixed_cone(V, 0.002)
    report(f"rudder {deg:+.0f} deg clears fin tip / cove / tail cone", not (tipi.any() or cove.any() or cone.any()),
           f"tip {int(tipi.sum())}, cove {int(cove.sum())}, cone {int(cone.sum())} verts")


# 5 ------------------------------------------------------------------------------------------------ retracted gear
def wing_z(x, y, upper):
    s = W.section_at(min(abs(y), W.SEMI))
    xc = np.clip((x - s.le[0]) / s.chord, 0, 1)
    return float((s.upper if upper else s.lower)(np.array(xc))[2])


TU = G.NOSE_TUNNEL
gp = parts["gear_nose"].pivot
M = rotation_about(gp["axis"], np.radians(gp["retract"]), gp["origin"])
V = posed("gear_nose", M)
keel = F.z_bot(np.clip(V[:, 0], X0, X1))
ceiling = np.where((V[:, 0] > TU["x0"]) & (V[:, 0] < TU["x1"]), TU["z_top"], TU["z_low"])
report("nose gear retracted: above the keel, inside the bay / tunnel",
       bool((V[:, 2] > keel + 0.003).all() and (V[:, 2] < ceiling).all()),
       f"lowest {1000 * (V[:, 2] - keel).min():+.0f} mm vs the keel, {int((V[:, 2] >= ceiling).sum())} verts above the roof")
for side in ("R", "L"):
    gp = parts[f"gear_main_{side}"].pivot
    M = rotation_about(gp["axis"], np.radians(gp["retract"]), gp["origin"])
    samp = posed(f"gear_main_{side}", M)[::3]
    wc = G.retracted_wheel(1 if side == "R" else -1)
    z_skin = wing_z(wc[0], wc[1], False)                    # lower skin at the stowed wheel centre
    tyre = verts(f"gear_main_{side}", ("tire",)) @ M[:3, :3].T + M[:3, 3]
    proud = z_skin - tyre[:, 2].min()
    low = z_skin - samp[:, 2].min()
    up = np.array([wing_z(p[0], p[1], True) for p in samp])
    over = (samp[:, 2] - up).max()
    report(f"main gear {side} retracted: tyre ~1 in proud, nothing lower, nothing above the upper skin",
           proud < 0.035 and low <= proud + 0.002 and over < 0,
           f"tyre {proud * 1000:.0f} mm below the skin at the wheel centre, lowest part {low * 1000:.0f} mm, "
           f"{over * 1000:+.0f} mm vs the upper skin")

# 6 ------------------------------------------------------------------------------------------------ brace knees
for pid, gear_id, A, B0, T, axis, (f1, ref), name in G.brace_specs():
    pv = parts[pid + "_up"].pivot
    g = parts[gear_id].pivot
    worst = []
    for t in np.linspace(0, 1, 21):
        B, K = pose(A, B0, np.array(pv["K0"]), np.array(g["origin"]), np.array(g["axis"]),
                    np.radians(g["retract"]) * t, pv["L1"], pv["L2"], axis, ref)
        if gear_id == "gear_nose":
            ceil = TU["z_top"] if TU["x0"] < K[0] < TU["x1"] else TU["z_low"]
            worst.append(min(K[2] - float(F.z_bot(K[0])), ceil - K[2]))
        else:
            worst.append(min(wing_z(K[0], K[1], True) - K[2], K[2] - wing_z(K[0], K[1], False)))
    report(f"{pid} knee inside {'the bay' if gear_id == 'gear_nose' else 'the wing skins'} over 0-100 %",
           min(worst) >= 0.02, f"min clearance {1000 * min(worst):.0f} mm")

# 7 ------------------------------------------------------------------------------------------------ airstair entry
V = verts("cabin_interior")
for r in openings_table():
    if r["id"] != "door_airstair":
        continue
    pan = r["panel"]
    hit = (V[:, 1] * r["side"] > 0.30) & (V[:, 0] > pan["x0"] - 0.02) & (V[:, 0] < pan["x1"] + 0.02) & \
          (V[:, 2] > F.CABIN_FLOOR_WL + 0.005)
    report("cabin furniture clear of the airstair entry", not hit.any(), f"{int(hit.sum())} verts in the entry")

# 8 ------------------------------------------------------------------------------------------------ horn balances
for side in ("R", "L"):
    ep = parts[f"elevator_{side}"].pivot
    for deg in (ep["range"][0], ep["range"][1]):
        M = rotation_about(np.asarray(ep["axis"], float), np.radians(deg), ep["origin"])
        V = posed(f"elevator_{side}", M)
        V = V[np.abs(V[:, 1]) > E.ELEV_Y[1]]                  # the horn (outboard of the fixed part's BL 2270 face)
        sec_in = np.zeros(len(V), bool)
        for i, (x, yy, z) in enumerate(V):
            s_ = E.stab_section(min(yy, E.STAB_TIP_Y))
            xc = (x - s_.le[0]) / s_.chord
            if 0 <= xc <= 1 and x < E.horn_gap_x(yy) + 0.002 and yy < E.STAB_NOTCH_Y:
                sec_in[i] = float(s_.lower(np.array(xc))[2]) < z < float(s_.upper(np.array(xc))[2])
        report(f"elevator_{side} horn at {deg:+.0f} deg clears the fixed tip", not sec_in.any(),
               f"{int(sec_in.sum())} of {len(V)} horn verts inside the fixed tip")

# 9 ------------------------------------------------------------------------------------------------ doors vs fairing
from model import details as D
for pid in ("door_airstair", "door_cargo"):
    dp = parts[pid].pivot
    worst = 1.0
    for f in np.linspace(0.0, 1.0, 11):
        M = rotation_about(np.asarray(dp["axis"], float), dp["open"] * f, dp["origin"])
        V = posed(pid, M)
        xc = np.clip(V[:, 0], X0, X1)
        ys = F.side_y(xc, V[:, 2])
        gap = np.abs(V[:, 1]) - (ys + D.root_fillet_standoff(V[:, 0], V[:, 2]))
        inside = (D.root_fillet_standoff(V[:, 0], V[:, 2]) > D.ROOT_FILLET_MIN_D) & (np.abs(V[:, 1]) > ys + 0.002)
        if inside.any():
            worst = min(worst, float(gap[inside].min()))
    report(f"{pid} clears the wing-root fairing over its whole opening", worst > -0.002,
           f"closest {worst * 1000:+.0f} mm outside the fairing surface" if worst < 1.0 else "never over the fairing")

print("FIT OK" if not fails else f"FIT FAIL ({len(fails)}): " + "; ".join(fails))
sys.exit(1 if fails else 0)
