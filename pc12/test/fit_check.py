"""Interference / fit checks of the built parts (model axes, metres).  Every x-range comes from fuselage.STA.

 1. interior, engine and inlet duct lie inside the fuselage OML (minus a margin)
 2. the spinner meets the cowl front (base ring on the cowl-front ring, no gap / step) and encloses the gearbox
 3. the wing carry-through stays under the cabin floor (fuselage.CABIN_FLOOR_WL - 15 mm) inside the fuselage
 4. dorsal fin, fin and rudder stay outside the fixed tail cone; the rudder at +/-25 deg clears the fin tip,
    the fixed cove and the tail-cone closure
 5. retracted gear: nose unit above the keel and inside the bay / pedestal tunnel; main tyres 20-30 mm below the
    LOCAL wing lower skin (POH ~1 in), nothing else below the skin, nothing above the upper skin; the stowed leg /
    strut above the closed leg door; the leg door flush with the skin (within 5 mm, decision LD-1 in model/gear.py);
    the skin cut-out closed by the door and the tyre (only the panel gap and the tyre's well ring open)
 6. folding-strut knees over 0-100 % retraction: main knees between the wing skins, nose knee inside the bay
 7. cabin furniture clear of the airstair entry
 8. the tailplane horn balances (carried by the elevators) clear the fixed tips at full elevator travel
 9. the airstair and cargo doors clear the wing-root fairing (fillet / nose) from closed to fully open
10. main gear + side brace over 0-100 %: every vertex inside the wing box lies in the bay liner (bays.main_bay_sdf),
    no triangle crosses the wing skins, bay liner, ribs / spars, flaps or belly fairing; the leg door clears the leg
    gear down; the stowed tyre is under the liner roof
11. nose gear + drag brace vs the clamshell doors at every state the viewer sequence reaches (doors open with the gear
    down and in transit, closing only once locked up) and vs the flight deck / bay liners
12. flaps 0-40 deg (flap-carried aft canoes included) clear the wing, the fixed canoes, the structure and the fairing
13. rudder / tab at -25 / 0 / +25 deg: no triangle crossing the fin (tip underside, cove, strip), tail cone or strakes
Checks 10-13 are exact triangle-crossing tests (test/isect.py), not vertex tests.
Prints one line per check and 'FIT OK' / 'FIT FAIL' (exit code 1 on failure).
"""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
sys.path.insert(1, str(__import__("pathlib").Path(__file__).resolve().parent))
import numpy as np
from cad.mesh import rotation_about
from model.build import build_parts
from model import fuselage as F, empennage as E, gear as G, wing as W, powerplant as PP
from model.brace import pose
from model.fuselage_parts import openings_table
from model.bays import main_bay_sdf
from isect import crossings, merged

X0, X1 = F.STA["cowl_front"], F.STA["tail_end"]
MARGIN = 0.02
parts = build_parts()
fails = []
opens = []


def report(name, ok, detail="", open_item=False):
    """open_item: a known conflict in the APPROVED parameters that needs an owner decision -- printed, not failed."""
    tag = "open" if open_item else ("ok" if ok else "FAIL")
    print(f"  [{tag}] {name}" + (f": {detail}" if detail else ""))
    if open_item:
        opens.append(name)
    elif not ok:
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
from model.livery import SURFACES as _SURF
DOOR_MAT = ("paint_white", _SURF["main_gear_door"], G.LEG_DOOR_BRACKET_MAT)   # leg door plate + its standoff brackets


def gear_meshes(pid, door=None):
    """Meshes of a gear part: door=True only the leg door, False all but the door, None all."""
    out = []
    for m, mm in parts[pid].meshes:
        d = mm in DOOR_MAT
        if door is None or d == door:
            out.append(m)
    return out


from model.bays import main_opening_sdf, DOOR_GAP, WELL_R, well_centre
from cad import sdf2d
for side in ("R", "L"):
    sg = 1 if side == "R" else -1
    gp = parts[f"gear_main_{side}"].pivot
    M = rotation_about(gp["axis"], np.radians(gp["retract"]), gp["origin"])
    rest_, _ = merged(gear_meshes(f"gear_main_{side}", door=False), M)
    V_ = rest_[::2]
    zl_, zu_ = G.wing_z(V_[:, 0], V_[:, 1], False), G.wing_z(V_[:, 0], V_[:, 1], True)
    fp = G.leg_door_footprint(1)
    covered = sdf2d.polygon(V_[:, 0], np.abs(V_[:, 1]), fp) < 0.0             # over the (stowed) leg door
    tyre = verts(f"gear_main_{side}", ("tire",)) @ M[:3, :3].T + M[:3, 3]
    proud = float((G.wing_z(tyre[:, 0], tyre[:, 1], False) - tyre[:, 2]).max())   # depth below the LOCAL lower skin
    mats = np.concatenate([np.full(len(m.V), mm, dtype=object) for m, mm in parts[f"gear_main_{side}"].meshes
                           if mm not in DOOR_MAT])[::2]
    whl = np.isin(mats, ("tire", "wheel"))
    low_other = float((zl_ - V_[:, 2])[~whl].max())                           # > 0: something else below the skin
    low_wheel = float((zl_ - V_[:, 2])[whl].max())
    over = float((V_[:, 2] - zu_).max())
    report(f"main gear {side} retracted: tyre protrudes 20-30 mm below the local lower skin (POH ~1 in)",
           0.020 <= proud <= 0.030, f"{proud * 1000:.1f} mm")
    report(f"main gear {side} retracted: nothing but the tyre below the skin, nothing above the upper skin",
           low_other < 0 and low_wheel <= proud + 1e-6 and over < 0,
           f"other parts lowest {-low_other * 1000:+.0f} mm vs the skin (rim / hub {-low_wheel * 1000:+.0f} mm, inside "
           f"the tyre bulge), highest {over * 1000:+.0f} mm vs the upper skin")
    # the stowed leg / strut / trunnion lie above the closed door's inner face (within its plan footprint), M3
    above = V_[covered, 2] - (zl_[covered] + G.LEG_DOOR_T + G.LEG_DOOR_RECESS)
    report(f"main gear {side} retracted: leg, strut and trunnion above the closed leg door",
           bool((above > 0.001).all()), f"closest {above.min() * 1000:.0f} mm above the door's inner face "
                                        f"({int(covered.sum())} verts over the door)")
    # leg door flush with the wing lower skin (LD-1): the analytic face and the posed mesh
    Vd, Fd = merged([m for m, mm in parts[f"gear_main_{side}"].meshes if mm in DOOR_MAT[:2]], M)
    dd = Vd[:, 2] - G.wing_z(Vd[:, 0], Vd[:, 1], False)                      # height above the local lower skin
    outer = dd < 0.5 * G.LEG_DOOR_T
    dmin, dmax = G.leg_door_retracted_drop(sg)
    report(f"main gear {side} retracted: leg door flush with the wing lower skin (within 5 mm), nothing below it",
           abs(dmin) <= 0.005 and abs(dmax) <= 0.005 and np.abs(dd[outer]).max() <= 0.005 and dd.min() >= -0.0005,
           f"outer face {dd[outer].min() * 1000:+.1f}..{dd[outer].max() * 1000:+.1f} mm above the skin (mesh), "
           f"{-dmax * 1000:+.1f}..{-dmin * 1000:+.1f} mm (face), lowest door vertex {dd.min() * 1000:+.1f} mm")
    # the underside is closed: every point of the skin cut-out is under the closed door or in the tyre's well; only
    # the door's panel gap (DOOR_GAP) and the ring round the tyre (tread -> well edge) stay open
    xs_, ys_ = np.meshgrid(np.arange(5.85, 6.75, 0.004), np.arange(1.0, 2.5, 0.004))
    xs_, ys_ = xs_.ravel(), sg * ys_.ravel()
    hole = main_opening_sdf(xs_, ys_) < 0
    wc = well_centre()
    ring = np.hypot(xs_ - wc[0], np.abs(ys_) - wc[1]) < WELL_R + 1e-6
    fp_d = sdf2d.polygon(xs_, np.abs(ys_), fp)
    open_ = hole & ~ring & (fp_d > 0)
    report(f"main gear {side} retracted: the skin cut-out is closed by the door (panel gap {DOOR_GAP * 1000:.0f} mm) "
           f"and the tyre in its well", bool((fp_d[open_] <= DOOR_GAP + 0.001).all()),
           f"{int(open_.sum())} cut-out samples outside the door and the well, widest gap "
           f"{(fp_d[open_].max() if open_.any() else 0) * 1000:.1f} mm; well R {WELL_R * 1000:.0f} about the stowed wheel "
           f"({1000 * abs(G.retracted_wheel(sg)[1] - sg * wc[1]):.1f} mm off)")

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

# 10 ----------------------------------------------------------------------------------------------- main gear sweep
def brace_pose(pid, frac):
    """Posed (upper, lower) link transforms of folding strut pid at gear fraction frac (model/brace.py, as the viewer:
    upper link about A, lower link rigid from K0-B0 onto K-B)."""
    from model.brace import solve_knee
    pv = parts[pid + "_up"].pivot
    g = parts[pv["gear"]].pivot
    A, B0, K0 = (np.array(pv[k], float) for k in ("A", "B0", "K0"))
    ax = np.array(pv["axis"], float)
    ax /= np.linalg.norm(ax)
    Mg = rotation_about(g["axis"], np.radians(g["retract"]) * frac, g["origin"])
    B = Mg[:3, :3] @ B0 + Mg[:3, 3]
    K = solve_knee(A, B, pv["L1"], pv["L2"], ax, np.array(pv["bend"], float))

    def sang(u, v):
        u = u - ax * u.dot(ax)
        v = v - ax * v.dot(ax)
        return np.arctan2(ax.dot(np.cross(u, v)), u.dot(v))
    Mu = rotation_about(ax, sang(K0 - A, K - A), A)
    Ml = rotation_about(ax, sang(B0 - K0, B - K), K0)
    Ml[:3, 3] += K - K0
    return Mu, Ml


def posed_mesh(pid, M, mats=None):
    return merged([m for m, mm in parts[pid].meshes if mats is None or mm in mats], M)


def cat(*vf):
    Vs, Fs, off = [], [], 0
    for V, F_ in vf:
        Vs.append(V)
        Fs.append(F_ + off)
        off += len(V)
    return np.vstack(Vs), np.vstack(Fs)


def _wing_grid(x0=5.20, x1=7.30, y0=0.80, y1=3.00, dx=0.004, dy=0.01):
    """Lower / upper wing-surface WL tabulated over the main-gear region (plan grid), for fast point tests."""
    from scipy.interpolate import RegularGridInterpolator
    xs, ys = np.arange(x0, x1 + 1e-9, dx), np.arange(y0, y1 + 1e-9, dy)
    lo = np.full((len(xs), len(ys)), np.nan)
    up = np.full((len(xs), len(ys)), np.nan)
    for j, y in enumerate(ys):
        sct = W.section_at(y)
        xc = (xs - sct.le[0]) / sct.chord
        ok = (xc > 0) & (xc < 1)
        lo[ok, j] = sct.lower(xc[ok])[:, 2]
        up[ok, j] = sct.upper(xc[ok])[:, 2]
    f = lambda T: RegularGridInterpolator((xs, ys), T, bounds_error=False, fill_value=np.nan)   # noqa: E731
    return f(lo), f(up)


_WLO, _WUP = _wing_grid()


def wing_box_inside(V):
    """Points inside the wing box (between the skins, outboard of the fuselage side) over the main-gear region."""
    q = np.c_[V[:, 0], np.abs(V[:, 1])]
    lo, up = _WLO(q), _WUP(q)
    side = np.abs(V[:, 1]) > F.side_y(np.clip(V[:, 0], X0, X1), V[:, 2])
    with np.errstate(invalid="ignore"):
        return side & (V[:, 2] > lo + 0.002) & (V[:, 2] < up - 0.002)


def crop(VF, lo, hi):
    """Triangles of (V, F) whose boxes meet the box lo..hi."""
    V, F_ = VF
    T = V[F_]
    return V, F_[((T.max(1) >= lo) & (T.min(1) <= hi)).all(1)]


I4 = np.eye(4)
for side in ("R", "L"):
    gid, bid = f"gear_main_{side}", f"brace_main_{side}"
    sg = 1 if side == "R" else -1
    fixed = crop(cat(posed_mesh(f"wing_{side}", I4), posed_mesh("gear_bays", I4), posed_mesh("structure", I4),
                     posed_mesh(f"flap_{side}", I4), posed_mesh("belly_fairing", I4)),
                 np.array([5.6, min(sg * 0.8, sg * 2.8), 0.0]), np.array([7.0, max(sg * 0.8, sg * 2.8), 1.45]))
    n_x, out_bay, worst = 0, 0, ""
    for f in np.linspace(0.0, 1.0, 11):
        g = parts[gid].pivot
        Mg = rotation_about(g["axis"], np.radians(g["retract"]) * f, g["origin"])
        Mu, Ml = brace_pose(bid, f)
        mov = cat(posed_mesh(gid, Mg), posed_mesh(bid + "_up", Mu), posed_mesh(bid + "_lo", Ml))
        P = crossings(*mov, *fixed)
        if len(P):
            n_x += len(P)
            worst = worst or f"gear {f:.1f}: {len(P)} at x {P[:, 0].min():.3f}-{P[:, 0].max():.3f} |y| " \
                              f"{np.abs(P[:, 1]).min():.3f}-{np.abs(P[:, 1]).max():.3f} z {P[:, 2].min():.3f}-{P[:, 2].max():.3f}"
        Vs = mov[0][::2]
        ins = wing_box_inside(Vs)
        out_bay += int((ins & (main_bay_sdf(Vs[:, 0], Vs[:, 1]) > 0.002)).sum())
    report(f"main gear {side} + side brace 0-100 %: no crossing of the wing skins, bay liner, structure, flap, fairing",
           n_x == 0, f"{n_x} crossings" + (f" ({worst})" if worst else ""))
    report(f"main gear {side} + side brace 0-100 %: everything inside the wing box lies in the bay liner",
           out_bay == 0, f"{out_bay} verts in the wing box outside bays.main_bay_sdf")
    ms = parts[gid].meshes
    plate = merged([m for m, mm in ms if mm in DOOR_MAT[:2]])
    brk = merged([m for m, mm in ms if mm == G.LEG_DOOR_BRACKET_MAT])
    P = crossings(*plate, *merged([m for m, mm in ms if mm not in DOOR_MAT]))
    Q = crossings(*brk, *merged([m for m, mm in ms if mm in ("tire", "wheel", "steel")]))
    report(f"main gear {side} down: leg door plate clears the leg, trunnion, tyre and arm; its brackets the wheel",
           len(P) + len(Q) == 0, f"{len(P)} / {len(Q)} crossings")
    g = parts[gid].pivot
    Mg = rotation_about(g["axis"], np.radians(g["retract"]), g["origin"])
    ty = verts(gid, ("tire",)) @ Mg[:3, :3].T + Mg[:3, 3]
    roof = np.array([wing_z(p[0], p[1], True) for p in ty[::4]]) - G.MAIN_BAY_ROOF_GAP
    report(f"main gear {side} up: stowed tyre under the bay liner roof", bool((ty[::4, 2] < roof - 0.002).all()),
           f"min clearance {1000 * (roof - ty[::4, 2]).min():.0f} mm")

# 11 ----------------------------------------------------------------------------------------------- nose gear / doors
def door_M(did, v):
    pv = parts[did].pivot
    return rotation_about(pv["axis"], np.radians(pv["open"] * (v - pv.get("rest", 0.0))), pv["origin"])


g = parts["gear_nose"].pivot
doors_n = {}
for f, v in [(f, 1.0) for f in np.linspace(0, 1, 11)] + [(1.0, v) for v in (0.75, 0.5, 0.25, 0.0)]:
    Mg = rotation_about(g["axis"], np.radians(g["retract"]) * f, g["origin"])
    Mu, Ml = brace_pose("brace_nose", f)
    mov = cat(posed_mesh("gear_nose", Mg), posed_mesh("brace_nose_up", Mu), posed_mesh("brace_nose_lo", Ml))
    dr = cat(posed_mesh("gear_door_NR", door_M("gear_door_NR", v)), posed_mesh("gear_door_NL", door_M("gear_door_NL", v)))
    n = len(crossings(*mov, *dr))
    if n:
        doors_n[(round(f, 2), v)] = n
report("nose gear + drag brace vs the clamshell doors (open with the gear down / in transit, closing when up)",
       not doors_n, "clear at every state" if not doors_n else "; ".join(f"gear {a:.1f} door {b:.2f}: {n}"
                                                                        for (a, b), n in doors_n.items()))
fixed = crop(cat(posed_mesh("flight_deck", I4), posed_mesh("gear_bays", I4), posed_mesh("fus_fwd", I4),
                 posed_mesh("cowl_lower", I4)), np.array([2.6, -0.4, 0.0]), np.array([4.4, 0.4, 1.8]))
n_fd = {}
for f in np.linspace(0, 1, 11):
    Mg = rotation_about(g["axis"], np.radians(g["retract"]) * f, g["origin"])
    Mu, Ml = brace_pose("brace_nose", f)
    mov = cat(posed_mesh("gear_nose", Mg), posed_mesh("brace_nose_up", Mu), posed_mesh("brace_nose_lo", Ml))
    n = len(crossings(*mov, *fixed))
    if n:
        n_fd[round(f, 1)] = n
report("nose gear + drag brace 0-100 % clear the flight deck (tunnel hump), bay liners and skins", not n_fd,
       "clear" if not n_fd else ", ".join(f"gear {a:.1f}: {n}" for a, n in n_fd.items()))

# 12 ----------------------------------------------------------------------------------------------- flaps + canoes
for side in ("R", "L"):
    fp = parts[f"flap_{side}"].pivot
    sg = 1 if side == "R" else -1
    fixed = crop(cat(posed_mesh(f"wing_{side}", I4), posed_mesh("flap_fairings", I4), posed_mesh("structure", I4),
                     posed_mesh("belly_fairing", I4), posed_mesh("fus_center", I4)),
                 np.array([5.5, min(0.0, sg * 6.0), 0.3]), np.array([8.2, max(0.0, sg * 6.0), 1.9]))
    bad = {}
    for deg in (0.0, 10.0, 15.0, 20.0, 30.0, 40.0):
        M = rotation_about(fp["axis"], np.radians(deg), fp["origin"])
        M[:3, 3] += np.asarray(fp["travel"], float) * deg / fp["max"]
        mov = cat(posed_mesh(f"flap_{side}", M), posed_mesh(f"flap_canoes_{side}", M))
        n = len(crossings(*mov, *fixed))
        if n:
            bad[deg] = n
    report(f"flap_{side} + aft canoes 0-40 deg clear the wing, fixed canoes, structure and fairing", not bad,
           "clear" if not bad else ", ".join(f"{a:.0f} deg: {n}" for a, n in bad.items()))

# 13 ----------------------------------------------------------------------------------------------- rudder crossings
rp = parts["rudder"].pivot
fixed = crop(cat(posed_mesh("fin", I4), posed_mesh("fus_aft", I4), posed_mesh("strakes", I4), posed_mesh("dorsal_fin", I4)),
             np.array([12.3, -0.6, 1.6]), np.array([14.9, 0.6, 4.2]))
bad = {}
for deg in (-25.0, 0.0, 25.0):
    M = rotation_about(np.asarray(rp["axis"], float), np.radians(deg), rp["origin"])
    mov = cat(posed_mesh("rudder", M), posed_mesh("rudder_tab", M))
    n = len(crossings(*mov, *fixed))
    if n:
        bad[deg] = n
report("rudder + tab at -25 / 0 / +25 deg: no triangle crossing the fin, tail cone, strakes or dorsal", not bad,
       "clear" if not bad else ", ".join(f"{a:+.0f} deg: {n}" for a, n in bad.items()))

tail = f" ({len(opens)} open owner decision{'s' if len(opens) != 1 else ''}: {'; '.join(opens)})" if opens else ""
print(("FIT OK" + tail) if not fails else f"FIT FAIL ({len(fails)}): " + "; ".join(fails) + tail)
sys.exit(1 if fails else 0)
