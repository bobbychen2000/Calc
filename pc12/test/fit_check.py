"""Interference / fit checks of the built parts (model axes, metres).  Every x-range comes from fuselage.STA.

 1. interior, engine and inlet duct lie inside the fuselage OML (minus a margin; the lining's window reveals, which
    end on the skin openings, only must not cross it)
 2. the spinner meets the cowl front (base ring on the cowl-front ring, no gap / step) and encloses the gearbox
 3. the wing carry-through stays under the cabin floor (fuselage.CABIN_FLOOR_WL - 15 mm) inside the fuselage
 4. dorsal fin, fin and rudder stay outside the fixed tail cone; the rudder at +/-25 deg clears the fin tip,
    the fixed cove and the tail-cone closure
 5. retracted gear: nose unit above the keel and inside the bay / pedestal tunnel; main tyres 20-30 mm below the
    LOCAL wing lower skin (POH ~1 in; the 8.50-10 Type III, owner decision 2026-09-26; '[open]' only for a trial build
    of the superseded 22 in tyre, ~19 mm), nothing but the wheel below the skin (the hub fairing and rim inside the tyre's depth; the
    fairing, painted in the door colour, is told from the door by lying within the tyre radius of the axle),
    nothing above the upper skin; the stowed leg /
    strut above the closed leg door; the leg door flush with the skin (within 5 mm, decision LD-1 in model/gear.py);
    the skin cut-out closed by the door and the tyre (only the panel gap and the tyre's well ring open)
 6. folding-strut knees over 0-100 % retraction: main knees between the wing skins, nose knee inside the bay
 7. cabin furniture and seats clear of the airstair entry zone (L6 CLEAR_ZONES entry_bl)
 8. the tailplane horn balances (carried by the elevators) clear the fixed tips at full elevator travel
 9. the airstair and cargo doors clear the wing-root fairing (fillet / nose) from closed to fully open
10. main gear + side brace over 0-100 %: every vertex inside the wing box lies in the bay liner (bays.main_bay_sdf),
    no triangle crosses the wing skins, bay liner, ribs / spars, flaps, belly fairing or flap-track canoes; the leg door
    (plate + brackets) clears the wing skin at the cut-out every 0.5 % over 90-100 % (where it rises through it); the
    leg door clears the leg gear down; the stowed tyre is under the liner roof; the bay liner itself crosses no wing
    skin (flap cove), flap, spar / rib or fairing
11. nose gear + drag brace vs the clamshell doors at every state the viewer sequence reaches (doors open with the gear
    down and in transit, closing only once locked up) and vs the flight deck / bay liners
12. flaps 0-40 deg (flap-carried aft canoes included) clear the wing, the fixed canoes, the structure and the fairing
13. rudder / tab at -25 / 0 / +25 deg: no triangle crossing the fin (tip underside, cove, strip), tail cone or strakes
14. each gear unit (leg, lug, wheel, main leg door + brackets) against its OWN folding-strut links over 0-100 % (only
    the lug round B excepted); the upper and lower link against each other (the knee joint excepted)
15. the rotating propeller hub, spinner / skirt and bulkhead against the gearbox and the cowl lip; blades at
    reverse / fine / feather against both; the spinner has exactly one cut-out per blade, round the blade's round
    shank and covered from outside by its rubber boot
16. the wing-root fairing (fillet + nose): no folds (dihedral > 90 deg) or normals against the winding; creases
    over 60 deg are counted; the nose (STA < 5.70): no crease over 30 deg on its face (off the wing junction)
17. every seat inside the side-wall lining and under the headliner (L6 LINING law), standing on the floor
18. crew seats on their two floor tracks (rail_dy, crew_h; fittings on the rails over the fore / aft travel); cabin
    seat base fittings on the cabin tracks (SEAT_TRACKS bl, x0-x1)
19. the 95th-pct male's legs vs the built yokes over pitch travel and roll (report, next to the L6B 2-D value)
20. cabin furniture and seats clear of the windows, the door / exit clear openings and the exit clear zone
21. airstair door (+ folding handrails) and cargo door (+ ledge segment) closed -> open clear of the interior
22. every interior piece seated (within 3 mm of, or crossing, another surface); 22b every lining fitting (O2 doors,
    PULL cover, PSU pods, downlights, sockets, CB panels, overhead) shows >= 95 % of its cabin-facing area > 0.5 mm in
    front of the lining; 22c the stowed divider curtain clear of the crew seat tracks
23. closed interior shells wound outward, directed edges consistent; vertex normals against the face winding on
    <= 1 % of each interior primitive's area
24. crew harness on the seat: no triangle crossing the sheepskin / leather cushion, and every harness vertex over
    the fleece's top (plan inside it, off the side rolls) >= 1 mm above it (review r3 K1)
25. crew armrests, down and stowed, and the rest of the seat vs the pedestal (quadrant, PCL, flap lever, CCD) over the
    whole fore / aft and height travel: >= CRITERIA arm_pedestal (review r3 C2)
26. no coplanar, same-facing, overlapping faces of DIFFERENT materials in the interior (they flicker in the viewer):
    <= 0.5 cm2 per material pair (review r3 K3)
Checks 10-15 are exact triangle-crossing tests (test/isect.py), not vertex tests.
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
FD_KIDS = [k for k, q in parts.items() if q.parent == "flight_deck"]    # yokes, rudder pedals (review r2 M4), consoles,
#                                                                         divider (review r3 C1)
CAB_KIDS = [k for k, q in parts.items() if q.parent == "cabin_interior" or (q.parent and parts[q.parent].parent ==
                                                                              "cabin_interior")]   # floor, tables (r3)
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
    # window reveals of the lining (interior.build_lining) run out to the skin openings by design: they must not
    # cross the OML (checked with a -1 mm margin); everything else keeps MARGIN
    rev = [m.V for m, _ in p.meshes if getattr(m, "_reveal", False)]
    if rev:
        Vr = np.vstack(rev)
        br = outside_oml(Vr, -0.001)
        report(f"{pid} window reveals end on the skin openings (never outside the OML)", not br.any(),
               f"{int(br.sum())}/{len(Vr)} verts outside")
    V = np.vstack([m.V for m, _ in p.meshes if not getattr(m, "_reveal", False)])
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
from model import wheels as WH
DOOR_MAT = ("paint_white", _SURF["main_gear_door"], _SURF["main_gear_door_inner"],    # leg door plate (outer face,
            G.LEG_DOOR_BRACKET_MAT)                                                    # inner face + rim), brackets
PLATE_MAT = DOOR_MAT[:3]                                                               # the plate alone


def wheel_mesh(pid, m):
    """A main-wheel part (the hub fairing is painted in the leg-door colour, the brake discs share the door brackets'
    metal_dark): every vertex within the tyre radius of the axle in side view -- the leg door, scalloped round the
    tyre, and its brackets never are."""
    if not pid.startswith("gear_main_"):
        return False
    A = G.MAIN_AXLE
    return float(np.hypot(m.V[:, 0] - A[0], m.V[:, 2] - A[2]).max()) <= G.MAIN_TYRE["R"] + 0.005


def is_door(pid, m, mm):
    return mm in DOOR_MAT and not wheel_mesh(pid, m)


def gear_meshes(pid, door=None):
    """Meshes of a gear part: door=True only the leg door, False all but the door, None all."""
    out = []
    for m, mm in parts[pid].meshes:
        d = is_door(pid, m, mm)
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
    tyre = verts(f"gear_main_{side}", WH.TYRE_MATS) @ M[:3, :3].T + M[:3, 3]
    proud = float((G.wing_z(tyre[:, 0], tyre[:, 1], False) - tyre[:, 2]).max())   # depth below the LOCAL lower skin
    kind = np.concatenate([np.full(len(m.V), 2 if mm in WH.TYRE_MATS else (1 if wheel_mesh(f"gear_main_{side}", m) else 0))
                           for m, mm in parts[f"gear_main_{side}"].meshes
                           if not is_door(f"gear_main_{side}", m, mm)])[::2]
    low_other = float((zl_ - V_[:, 2])[kind == 0].max())                      # > 0: something else below the skin
    low_wheel = float((zl_ - V_[:, 2])[kind == 1].max())                      # wheel halves, hub fairing, brake
    over = float((V_[:, 2] - zu_).max())
    ok_p = 0.020 <= proud <= 0.030
    # the modelled 8.50-10 Type III (owner decision 2026-09-26) lies ~24 mm deep; the superseded 22x8.50-10 (trial build
    # PC12_MAIN_TYRE=22x8.50-10) would lie ~19 mm deep, reported '[open]'
    open_p = (not ok_p) and (not WH.MAIN_IS_TRA) and 0.015 <= proud < 0.020
    report(f"main gear {side} retracted: tyre protrudes 20-30 mm below the local lower skin (POH ~1 in)",
           ok_p, f"{proud * 1000:.1f} mm ({WH.MAIN_TYRE_ENV['size']})" +
           ("; the 22 in tyre's drawn section, the proposed 8.50-10 Type III reaches the POH ~1 in: owner decision "
            "(wheels.MAIN_TYRE_CHOICE)" if open_p else ""), open_item=open_p)
    report(f"main gear {side} retracted: nothing but the wheel below the skin (hub fairing, rim inside the tyre's "
           "depth), nothing above the upper skin",
           low_other < 0 and low_wheel <= proud + 1e-6 and over < 0,
           f"other parts lowest {-low_other * 1000:+.0f} mm vs the skin (hub fairing / rim / brake "
           f"{-low_wheel * 1000:+.0f} mm, inside the tyre), highest {over * 1000:+.0f} mm vs the upper skin")
    # the stowed leg / strut / trunnion lie above the closed door's inner face (within its plan footprint), M3
    above = V_[covered, 2] - (zl_[covered] + G.LEG_DOOR_T + G.LEG_DOOR_RECESS)
    report(f"main gear {side} retracted: leg, strut and trunnion above the closed leg door",
           bool((above > 0.001).all()), f"closest {above.min() * 1000:.0f} mm above the door's inner face "
                                        f"({int(covered.sum())} verts over the door)")
    # leg door flush with the wing lower skin (LD-1): the analytic face and the posed mesh
    Vd, Fd = merged([m for m, mm in parts[f"gear_main_{side}"].meshes
                     if mm in PLATE_MAT and is_door(f"gear_main_{side}", m, mm)], M)
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
# L6 CLEAR_ZONES entry_bl: no furniture outboard of |BL| entry_bl abeam the airstair door (its panel seam plus the lining's
# door-well margin), from the tops of the surface-mounted tracks (SEAT_TRACKS h) up to the top of the door opening
from model import interior as I
from model import fuselage_parts as FPm
SEAT_IDS = [k for k in parts if k.startswith("seat_")]
V = np.vstack([verts(k) for k in ["cabin_interior", "flight_deck"] + FD_KIDS + CAB_KIDS + SEAT_IDS])
for r in openings_table():
    if r["id"] != "door_airstair":
        continue
    pan, m_ = r["panel"], I.LINING_DOOR_MARGIN
    z0 = I.FLOOR["wl"] + I.SEAT_TRACKS["h"] + 0.002
    hit = (V[:, 1] * r["side"] > I.CLEAR_ZONES["entry_bl"]) & (V[:, 0] > pan["x0"] - m_) & (V[:, 0] < pan["x1"] + m_) & \
          (V[:, 2] > z0) & (V[:, 2] < FPm.AIRSTAIR["cz"] + FPm.AIRSTAIR["hz"])
    report("cabin furniture and seats clear of the airstair entry zone (L6 CLEAR_ZONES entry_bl)", not hit.any(),
           f"{int(hit.sum())} verts in the zone |BL| > {I.CLEAR_ZONES['entry_bl']:.2f}, STA {pan['x0'] - m_:.3f}-"
           f"{pan['x1'] + m_:.3f}")

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
                     posed_mesh(f"flap_{side}", I4), posed_mesh("belly_fairing", I4), posed_mesh("flap_fairings", I4),
                     posed_mesh(f"flap_canoes_{side}", I4)),
                 np.array([5.6, min(sg * 0.8, sg * 3.3), 0.0]), np.array([7.6, max(sg * 0.8, sg * 3.3), 1.45]))
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
    report(f"main gear {side} + side brace 0-100 %: no crossing of the wing skins, bay liner, structure, flap, fairing, "
           "flap-track canoes",
           n_x == 0, f"{n_x} crossings" + (f" ({worst})" if worst else ""))
    report(f"main gear {side} + side brace 0-100 %: everything inside the wing box lies in the bay liner",
           out_bay == 0, f"{out_bay} verts in the wing box outside bays.main_bay_sdf")
    # fine sweep of the last 10 % (owner decision 2026-09-27, leg-door tip rounding): the leg door rises through the
    # skin cut-out there, and between the 10 % samples above its sharp tip / step corner had nicked the skin beside the
    # cut-out by 2.8 / 1.3 mm (96-99.5 %).  Door (plate + brackets) vs the wing skin every 0.5 %; a crossing's nick is
    # its distance from the cut-out edge (the skin's boundary)
    door_ = merged([m for m, mm in parts[gid].meshes if is_door(gid, m, mm)])     # (the brake discs share metal_dark)
    skin_ = crop(posed_mesh(f"wing_{side}", I4), np.array([5.6, min(sg * 0.8, sg * 3.3), 0.8]),
                 np.array([7.0, max(sg * 0.8, sg * 3.3), 1.4]))
    Ek = np.sort(np.vstack([skin_[1][:, [0, 1]], skin_[1][:, [1, 2]], skin_[1][:, [2, 0]]]), 1)
    Eu, Ec = np.unique(Ek, axis=0, return_counts=True)
    Eb = Eu[Ec == 1]                                            # skin boundary edges (cut-out, panel ends)
    Ba, Bb = skin_[0][Eb[:, 0]], skin_[0][Eb[:, 1]]
    nb = np.maximum(1, np.ceil(np.linalg.norm(Bb - Ba, axis=1) / 0.0005).astype(int))
    from scipy.spatial import cKDTree as _KD
    edge_tree = _KD(np.vstack([a_ + (b_ - a_) * (np.arange(k_ + 1) / k_)[:, None] for a_, b_, k_ in zip(Ba, Bb, nb)]))
    n_fine, nick, at = 0, 0.0, ""
    fr = np.round(np.arange(0.90, 1.0 + 1e-9, 0.005), 4)
    for f in fr:
        Mg = rotation_about(g["axis"], np.radians(g["retract"]) * f, g["origin"])
        P = crossings(door_[0] @ Mg[:3, :3].T + Mg[:3, 3], door_[1], *skin_)
        if len(P):
            n_fine += len(P)
            dn = float(edge_tree.query(P)[0].max())
            if dn >= nick:
                nick, at = dn, f"{f * 100:.1f} %"
    report(f"main gear {side} leg door 90-100 % every 0.5 % ({len(fr)} poses): clears the wing skin at the cut-out",
           n_fine == 0, f"{n_fine} crossings" + (f", deepest nick {nick * 1000:.1f} mm into the skin at {at}" if n_fine
                                                 else f" (tip R {G.LEG_DOOR_TIP_R * 1000:.0f}, step / aft-top corners "
                                                      f"R {G.LEG_DOOR_CORNER_R * 1000:.0f})"))
    ms = parts[gid].meshes
    plate = merged([m for m, mm in ms if mm in PLATE_MAT and is_door(gid, m, mm)])
    brk = merged([m for m, mm in ms if mm == G.LEG_DOOR_BRACKET_MAT and is_door(gid, m, mm)])
    P = crossings(*plate, *merged([m for m, mm in ms if not is_door(gid, m, mm)]))
    Q = crossings(*brk, *merged([m for m, mm in ms if wheel_mesh(gid, m)]))
    report(f"main gear {side} down: leg door plate clears the leg, trunnion, wheel (tyre, hub fairing) and arm; its "
           "brackets the wheel", len(P) + len(Q) == 0, f"{len(P)} / {len(Q)} crossings")
    g = parts[gid].pivot
    Mg = rotation_about(g["axis"], np.radians(g["retract"]), g["origin"])
    ty = verts(gid, WH.TYRE_MATS) @ Mg[:3, :3].T + Mg[:3, 3]
    roof = np.array([wing_z(p[0], p[1], True) for p in ty[::4]]) - G.MAIN_BAY_ROOF_GAP
    report(f"main gear {side} up: stowed tyre under the bay liner roof", bool((ty[::4, 2] < roof - 0.002).all()),
           f"min clearance {1000 * (roof - ty[::4, 2]).min():.0f} mm")
# the bay liner (walls round the 8.50-10's well reach past the rear-spar line) clears the wing skins incl. the flap cove
# (recessed over the well, wing.cove_well_recess), the flaps, spars / ribs and the fairings
L_bay = posed_mesh("gear_bays", I4)
bad = {}
for pid in ("wing_R", "wing_L", "flap_R", "flap_L", "structure", "belly_fairing", "flap_fairings"):
    P = crossings(*L_bay, *posed_mesh(pid, I4))
    P = P[np.abs(P[:, 1]) > 0.95] if len(P) else P                 # (the nose bay / tunnel is checked in 11)
    if len(P):
        bad[pid] = len(P)
report("main bay liners clear the wing skins (flap cove), flaps, spars / ribs and fairings", not bad,
       "clear" if not bad else ", ".join(f"{k}: {v}" for k, v in bad.items()))

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
fixed = crop(cat(posed_mesh("flight_deck", I4), *[posed_mesh(k, I4) for k in FD_KIDS], posed_mesh("gear_bays", I4),
                 posed_mesh("fus_fwd", I4), posed_mesh("cowl_lower", I4)), np.array([2.6, -0.4, 0.0]),
             np.array([4.4, 0.4, 1.8]))
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

# 14 ----------------------------------------------------------------------------------------------- own brace links
# fit checks 10 / 11 move gear + brace as ONE mesh, so a leg is never tested against its own links (MV2-01 / MV2-02):
# here each gear unit -- leg, lug, wheel and (main) the LD-1 leg door that retracts with it -- against its upper and
# lower link over 0-100 %, ignoring only the lug round B (BRACE_LUG_SKIP)
BRACE_LUG_SKIP = 0.050
BRACE_KNEE_SKIP = (0.015, 0.160)      # knee pin: radius / half-length round the knee axis
for pid, gear_id, A, B0, T, axis, (f1, ref), name in G.brace_specs():
    g = parts[gear_id].pivot
    worst, n_tot = "", 0
    for f in np.linspace(0.0, 1.0, 21):
        Mg = rotation_about(g["axis"], np.radians(g["retract"]) * f, g["origin"])
        Mu, Ml = brace_pose(pid, f)
        B = Mg[:3, :3] @ B0 + Mg[:3, 3]
        leg = posed_mesh(gear_id, Mg)
        for lk, Ml_ in (("_up", Mu), ("_lo", Ml)):
            P = crossings(*leg, *posed_mesh(pid + lk, Ml_))
            if len(P):
                P = P[np.linalg.norm(P - B, axis=1) > BRACE_LUG_SKIP]
            if len(P):
                n_tot += len(P)
                d = np.linalg.norm(P - B, axis=1)
                worst = worst or f"gear {f:.2f} {lk[1:]} link: {len(P)} at {1000 * d.min():.0f}-{1000 * d.max():.0f} mm from B"
    unit = "leg + wheel" + (" + leg door" if gear_id.startswith("gear_main") else "")
    report(f"{gear_id} {unit} vs its own {pid} links 0-100 % (lug <= {BRACE_LUG_SKIP * 1000:.0f} mm from B excepted)",
           n_tot == 0, "clear" if not n_tot else f"{n_tot} crossings ({worst})")
    # the two links against each other (the knee pin joint excepted): they must pass as the knee closes (MV2-02)
    pv = parts[pid + "_up"].pivot
    n_ll, worst = 0, ""
    for f in np.linspace(0.0, 1.0, 21):
        Mu, Ml = brace_pose(pid, f)
        K = Mu[:3, :3] @ np.array(pv["K0"]) + Mu[:3, 3]
        P = crossings(*posed_mesh(pid + "_up", Mu), *posed_mesh(pid + "_lo", Ml))
        if len(P):                                  # the knee pin itself (a cylinder round the knee axis)
            ka = np.asarray(pv["axis"], float) / np.linalg.norm(pv["axis"])
            w = P - K
            along = w @ ka
            radial = np.linalg.norm(w - np.outer(along, ka), axis=1)
            P = P[~((radial < BRACE_KNEE_SKIP[0]) & (np.abs(along) < BRACE_KNEE_SKIP[1]))]
        if len(P):
            n_ll += len(P)
            worst = worst or f"gear {f:.2f}: {len(P)} up to {1000 * np.linalg.norm(P - K, axis=1).max():.0f} mm from K"
    report(f"{pid}: upper vs lower link 0-100 % (the knee pin, r <= {BRACE_KNEE_SKIP[0] * 1000:.0f} mm round the knee "
           "axis, excepted)", n_ll == 0, "clear" if not n_ll else f"{n_ll} crossings ({worst})")

# 15 ----------------------------------------------------------------------------------------------- propeller / engine
# the rotating hub, spinner (skirt) and spinner bulkhead against the static gearbox and cowl lip (MV2-03), at spin angles
# across one blade pitch; the blades at feather / fine / reverse against the gearbox and the cowl
pp = parts["propeller"].pivot
static = cat(posed_mesh("eng_rgb", I4), posed_mesh("cowl_upper", I4), posed_mesh("cowl_lower", I4),
             posed_mesh("chin_inlet", I4))
bad = {}
for deg in (0.0, 18.0, 36.0, 54.0):
    M = rotation_about(np.asarray(pp["axis"], float), np.radians(deg), pp["origin"])
    n = len(crossings(*posed_mesh("propeller", M), *static))
    if n:
        bad[f"spin {deg:.0f}"] = n
for k in range(1, 6):
    bp = parts[f"blade_{k}"].pivot
    for deg in (bp["reverse"], 0.0, bp["feather"]):
        M = rotation_about(np.asarray(bp["axis"], float), np.radians(deg), bp["origin"])
        n = len(crossings(*posed_mesh(f"blade_{k}", M), *static))
        if n:
            bad[f"blade {k} pitch {deg:+.0f}"] = n
report("propeller hub / spinner / bulkhead (all spin angles) and blades (reverse..feather) clear the gearbox and cowl",
       not bad, "clear" if not bad else ", ".join(f"{a}: {n}" for a, n in bad.items()))

# the spinner shell has exactly one blade-root cut-out per blade (VQA r1 SHP-01: a two-sided cutter had cut 10), each
# round the blade's round shank (BLADE_HOLE_R about the pitch axis, the shank BLADE_SHANK_R inside it) and closed from
# outside by its rubber boot (every cut-out edge point inside the boot's radius at that height)
from cad.mesh import Mesh, boundary_loops  # noqa: E402
shell = merged([m for m, mm in parts["propeller"].meshes if mm in ("chrome", "paint_white")])
sm = Mesh(*shell)
key = np.round(sm.V / 1e-7).astype(np.int64)
_, inv = np.unique(key, axis=0, return_inverse=True)
Vw = np.zeros((inv.max() + 1, 3))
Vw[inv.reshape(-1)] = sm.V
loops = [Vw[lp] for lp in boundary_loops(Mesh(Vw, inv.reshape(-1)[sm.F]))]
hub = PP.prop_hub()
holes, boot_gap = {}, []
small = [L for L in loops if np.ptp(L, 0).max() < 0.2]         # cut-out sized loops (the skirt / step rings are 0.5 m)
for L in small:
    for k in range(PP.N_BLADES):
        d = PP.blade_axis(k)
        w = L - hub
        s_ = w @ d
        r_ = np.linalg.norm(w - np.outer(s_, d), axis=1)
        if (s_ > 0).all() and r_.max() < PP.BLADE_HOLE_R + 0.004:
            holes[k] = holes.get(k, 0) + 1
            boot_gap.append(float(-PP.blade_boot_covers(k, L).min()))       # the seal ring reaches past the edge
n_holes = sum(holes.values())
report(f"spinner: one blade-root cut-out per blade, closed by its boot", len(small) == n_holes == PP.N_BLADES
       and len(holes) == PP.N_BLADES
       and max(boot_gap, default=1.0) < -0.002 and PP.BLADE_SHANK_R < PP.BLADE_HOLE_R,
       f"{len(small)} cut-outs ({n_holes} round a blade shank) for {PP.N_BLADES} blades; cut-out edge "
       f"{-1000 * max(boot_gap, default=0.0):.1f} mm inside the boot at worst; shank R {PP.BLADE_SHANK_R * 1000:.0f} / "
       f"cut-out R {PP.BLADE_HOLE_R * 1000:.0f} mm")

# 16 ----------------------------------------------------------------------------------------------- fairing folds
# the wing-root fairing nose is an offset surface of the OML: no folded (> 60 deg) creases where it wraps the wing LE
# (MQ2-01); welded dihedral angles over the fairing meshes


def fold_count(meshes, lim_deg=60.0, min_alt=3e-5):
    V, F_ = merged(meshes)
    # needle / sliver triangles thinner than min_alt (a livery trim passing within microns of a vertex leaves ~10 um
    # needles; the GLB's 16-bit quantisation drops them as zero-area) are not surface: welded at 20 um they can fold
    ar = 0.5 * np.linalg.norm(np.cross(V[F_[:, 1]] - V[F_[:, 0]], V[F_[:, 2]] - V[F_[:, 0]]), axis=1)
    el = np.stack([np.linalg.norm(V[F_[:, i]] - V[F_[:, (i + 1) % 3]], axis=1) for i in range(3)], 1).max(1)
    F_ = F_[2 * ar / np.maximum(el, 1e-12) >= min_alt]
    key = np.round(V / 2e-5).astype(np.int64)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    Fw = inv.reshape(-1)[F_]
    Fw = Fw[(Fw[:, 0] != Fw[:, 1]) & (Fw[:, 1] != Fw[:, 2]) & (Fw[:, 0] != Fw[:, 2])]
    Vw = np.zeros((inv.max() + 1, 3))
    Vw[inv.reshape(-1)] = V
    n = np.cross(Vw[Fw[:, 1]] - Vw[Fw[:, 0]], Vw[Fw[:, 2]] - Vw[Fw[:, 0]])
    ln = np.linalg.norm(n, axis=1)
    ok = ln > 1e-14
    Fw, n = Fw[ok], n[ok] / ln[ok, None]
    E = np.vstack([Fw[:, [0, 1]], Fw[:, [1, 2]], Fw[:, [2, 0]]])
    fi = np.tile(np.arange(len(Fw)), 3)
    Es = np.sort(E, 1)
    o = np.lexsort((Es[:, 1], Es[:, 0]))
    Es, fi = Es[o], fi[o]
    same = (Es[1:] == Es[:-1]).all(1)
    a, b = fi[:-1][same], fi[1:][same]
    ang = np.degrees(np.arccos(np.clip(np.einsum("ij,ij->i", n[a], n[b]), -1, 1)))
    bad = ang > lim_deg
    P = 0.5 * (Vw[Es[:-1][same][bad, 0]] + Vw[Es[:-1][same][bad, 1]])
    return int(bad.sum()), P


fil = [m for m, mm in parts["belly_fairing"].meshes if mm != _SURF["belly_fairing"]]   # root fillet + nose pieces
from model import details as _D
_Pp = np.array(_D.BELLY_FAIRING_PLAN)


def on_wing_junction(P, tol=0.005):
    """Crease points within tol of the fillet's junction with the wing ahead of STA 5.70 (the foot on the drawn plan
    edge, where the section law's horizontal tangent meets the steep leading-edge nose: sub-mm steps, VQA r3)."""
    if not len(P):
        return np.zeros(0, bool)
    yo = _D.root_fillet_lines()[2](np.clip(P[:, 0], _Pp[0, 0], _Pp[-1, 0]))
    zt = _D.wing_top(P[:, 0], yo)[0]
    return (P[:, 0] < 5.70) & (np.hypot(np.abs(P[:, 1]) - yo, P[:, 2] - zt) < tol)


nf60, Pf = fold_count(fil, 60.0)
nf90, P90 = fold_count(fil, 90.0)
j90 = on_wing_junction(P90)
flip = 0
for m in fil:                                   # vertex normals against the triangle winding
    if m.nf and m.N is not None:
        fn = np.cross(m.V[m.F[:, 1]] - m.V[m.F[:, 0]], m.V[m.F[:, 2]] - m.V[m.F[:, 0]])
        flip += int((np.einsum("ij,ij->i", fn, m.N[m.F].sum(1)) < 0).sum())
report("belly_fairing root fillet / fairing nose: no folds (dihedral > 90 deg), no normals against the winding",
       int((~j90).sum()) == 0 and flip == 0,
       f"{int((~j90).sum())} edges > 90 deg ({int(j90.sum())} on the LE junction with the wing), {flip} flipped "
       f"triangles; {nf60} creases > 60 deg"
       + (f" (x {Pf[:, 0].min():.3f}-{Pf[:, 0].max():.3f} |y| {np.abs(Pf[:, 1]).min():.3f}-{np.abs(Pf[:, 1]).max():.3f} "
          f"z {Pf[:, 2].min():.3f}-{Pf[:, 2].max():.3f})" if nf60 else "") + " (rev: 114 edges > 60 deg, max 150)")

# VQA r3 RQ3-01: the fairing nose must read as one smooth surface -- no crease over 30 deg ahead of STA 5.70 on its
# face (the knotted highlight of the r3 renders: ~90 edges folded 20-60 deg at STA 5.36-5.45 and 60-80 deg at the keel
# corner).  Edges on the junction with the wing are counted apart.
nk30, Pk30 = fold_count(fil, 30.0)
Pn = Pk30[Pk30[:, 0] < 5.70] if nk30 else np.zeros((0, 3))
junction = on_wing_junction(Pn)
face = Pn[~junction]
report("belly_fairing nose (STA < 5.70): no creases over 30 deg on its face", len(face) == 0,
       f"{len(face)} edges > 30 deg off the wing junction" + (f" (x {face[:, 0].min():.3f}-{face[:, 0].max():.3f} z "
                                                              f"{face[:, 2].min():.3f}-{face[:, 2].max():.3f})" if len(face) else "")
       + f"; {int(junction.sum())} on the junction with the wing (foot line)")

# 17 ----------------------------------------------------------------------------------------------- seats: lining, floor
# every seat (Stage 3, model/seats.py) inside the side-wall lining and under the headliner (the L6 LINING law,
# interior.lining_section, tabulated) and standing on the floor (lowest point on the floor WL, nothing below it)
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from model import cabin as CB
LIN = CB._Lining(x0=3.06, x1=9.74, dx=0.02)
FL = float(I.FLOOR["wl"])
for pid in SEAT_IDS:
    V = verts(pid)
    side_cl = float((LIN.hw(V[:, 0], V[:, 2]) - np.abs(V[:, 1])).min())
    head_cl = float((LIN.crown(V[:, 0], V[:, 1]) - V[:, 2]).min())
    low = float(V[:, 2].min() - FL)
    report(f"{pid} inside the lining (side wall, headliner) and standing on the floor",
           side_cl > 0.0 and head_cl > 0.0 and -0.0005 <= low <= 0.0005,
           f"side wall {side_cl * 1000:.0f} mm, headliner {head_cl * 1000:.0f} mm, lowest point {low * 1000:+.1f} mm vs "
           f"the floor WL {FL * 1000:.0f}")


# 18 ----------------------------------------------------------------------------------------------- seats on the tracks
def components(m, tol=1e-6):
    """Connected pieces of a mesh, vertices welded by position (crisp boxes have split corners): [vertex arrays]."""
    _, inv = np.unique(np.round(m.V / tol).astype(np.int64), axis=0, return_inverse=True)
    inv = inv.reshape(-1)
    n = int(inv.max()) + 1
    Fw = inv[m.F]
    E = np.vstack([Fw[:, [0, 1]], Fw[:, [1, 2]]])
    A = coo_matrix((np.ones(len(E)), (E[:, 0], E[:, 1])), shape=(n, n))
    _, lab = connected_components(A, directed=False)
    lv = lab[inv]
    used = np.zeros(len(m.V), bool)
    used[m.F.ravel()] = True
    return [m.V[(lv == i) & used] for i in np.unique(lv[used])]


CS, ST_ = I.CREW_SEAT, I.SEAT_TRACKS
for pid, side in (("seat_pilot", -1), ("seat_copilot", 1)):
    rail = [m for m, mm in parts[pid].meshes if mm == "metal_dark"]
    pcs = [c for m in rail for c in components(m)]
    tracks = [c for c in pcs if np.ptp(c[:, 0]) > 0.4 and c[:, 2].min() < FL + 1e-4]
    fits = [c for c in pcs if np.ptp(c[:, 0]) < 0.08 and c[:, 2].min() < FL + 1e-4]
    srp = I.crew_srp(side)
    ok = len(tracks) == 2 and len(fits) == 4
    det = f"{len(tracks)} tracks, {len(fits)} fittings"
    if ok:
        ty = sorted(float(0.5 * (c[:, 1].min() + c[:, 1].max())) for c in tracks)
        dy = max(abs(ty[0] - (srp[1] - CS["rail_dy"])), abs(ty[1] - (srp[1] + CS["rail_dy"])))
        th = max(abs(float(c[:, 2].max() - (FL + ST_["crew_h"]))) for c in tracks)
        tx0, tx1 = max(float(c[:, 0].min()) for c in tracks), min(float(c[:, 0].max()) for c in tracks)
        over = -np.inf
        on_rail = True
        for c in fits:
            yc = float(0.5 * (c[:, 1].min() + c[:, 1].max()))
            tr = min(tracks, key=lambda t: abs(float(t[:, 1].mean()) - yc))
            on_rail &= bool(c[:, 1].min() < tr[:, 1].max() and c[:, 1].max() > tr[:, 1].min())
            for d in (-CS["travel_x"], CS["travel_x"]):
                over = max(over, tx0 - float(c[:, 0].min() + d), float(c[:, 0].max() + d) - tx1)
        ok = dy < 0.002 and th < 0.001 and on_rail and over <= 0.0
        det += (f": track CLs {ty[0]:+.3f} / {ty[1]:+.3f} (seat BL {srp[1]:+.3f} +/- rail_dy {CS['rail_dy']:.3f}, "
                f"{dy * 1000:.1f} mm), tops {th * 1000:.1f} mm off floor + crew_h, fittings on the rails "
                f"{'yes' if on_rail else 'NO'}, over the +/-{CS['travel_x'] * 1000:.0f} mm travel the fittings stay "
                f"{-over * 1000:.0f} mm inside the track ends (STA {tx0:.3f}-{tx1:.3f})")
    report(f"{pid} on its two floor tracks (CREW_SEAT rail_dy, SEAT_TRACKS crew_h) over the fore / aft travel", ok, det)
cab_rails = [(sg * b) for b in ST_["bl"] for sg in (-1, 1)]
for pid in [k for k in SEAT_IDS if k.startswith("seat_pax")]:
    fits = [c for m, mm in parts[pid].meshes if mm == "metal_dark" for c in components(m) if c[:, 2].min() < FL + 1e-4]
    worst = 0.0
    for c in fits:
        yc = float(0.5 * (c[:, 1].min() + c[:, 1].max()))
        rl = min(cab_rails, key=lambda y: abs(y - yc))
        worst = max(worst, abs(yc - rl), float(ST_["x0"] - c[:, 0].min()), float(c[:, 0].max() - ST_["x1"]))
    report(f"{pid} base fittings on the cabin tracks (SEAT_TRACKS bl, x0-x1)", len(fits) >= 2 and worst < 0.003,
           f"{len(fits)} fittings, worst {worst * 1000:.1f} mm off a track centre line / outside the track run")

# 19 ----------------------------------------------------------------------------------------------- knees vs yokes
# the 95th-pct male at his seat setting (interior.crew_setting: L6B) -- leg spheres (thighs, knees, shanks) against the
# BUILT yoke (hub + grips of flight_deck) swept over the pitch travel and rolled +/- YOKE roll about the column axis;
# reported next to the L6B 2-D value (front-view outline x pitch slab), not failed: the criterion is L6B's
Y = I.YOKE
for side in (-1, 1):
    hub = I.yoke_hub(side)
    Vy = np.vstack([m.V for k in ["flight_deck"] + FD_KIDS for m, mm in parts[k].meshes
                    if mm in ("yoke_white", "grip_black", "black", "light_red", "panel_grey")])
    Vy = Vy[(np.abs(Vy[:, 1] - hub[1]) < 0.20) & (Vy[:, 0] > hub[0] - 0.05) & (Vy[:, 0] < hub[0] + 0.12) &
            (np.abs(Vy[:, 2] - hub[2]) < 0.15)]
    p95 = I.crew_setting(1.0, side)
    sph = np.array(I.leg_spheres(p95, side * CS["bl"]))
    tab = I.yoke_roll_clearances(p95, side)
    l6b_lvl = I.yoke_clearance(p95, side, 0.0, table=tab)[0]
    l6b_rol = I.yoke_clearance(p95, side, table=tab)[0]
    res = {}
    for roll in np.arange(-Y["roll"], Y["roll"] + 1e-9, 10.0):
        a = np.radians(roll)
        R = np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])
        Vr = (Vy - hub) @ R.T + hub
        best = np.inf
        for t in np.linspace(Y["travel"][0], Y["travel"][1], 9):
            d, _ = cKDTree(Vr + [t, 0, 0]).query(sph[:, :3])
            best = min(best, float((d - sph[:, 3]).min()))
        res[round(float(roll))] = best
    lvl = res[0]
    rol = min(res.values())
    report(f"95th-pct knees / legs vs the {'pilot' if side < 0 else 'co-pilot'} yoke (3-D mesh, pitch travel "
           f"{Y['travel'][0] * 1000:+.0f}/{Y['travel'][1] * 1000:+.0f} mm, roll +/-{Y['roll']:.0f} deg)",
           True, f"wings level {lvl * 1000:.0f} mm (L6B {l6b_lvl * 1000:.0f}), full roll sweep {rol * 1000:.0f} mm (L6B "
                 f"{l6b_rol * 1000:.0f}); criterion {I.CRITERIA['knee_clear'] * 1000:.0f} mm (report)")

# 20 ----------------------------------------------------------------------------------------------- furniture vs openings
# the fixed cabin furniture (cabinets, ledges, lavatory, headliner fittings) (a) never in front of a cabin / door window
# (inside the window outline, within 0.12 m of the side-wall lining), (b) never in a door's clear opening near the wall
# above the floor (the cargo-door ledge segment belongs to door_cargo and swings with it; seats stand in front of the
# windows and the cargo door by the POH layout), (c) furniture AND seats never in the over-wing exit's clear zone (L6
# CLEAR_ZONES exit_bl .. the starboard lining, abeam the hatch, from its sill to its top)
from model import fuselage_parts as FP
fur = {"cabin_interior": np.vstack([verts(k) for k in ["cabin_interior"] + CAB_KIDS])}
wins = [(side, cx) for side, xs in FP.FIXED_WINDOWS.items() for cx in xs] + \
       [(o["side"], FP.DOOR_WINDOWS[pid]) for pid, o in FP.DOORS if FP.DOOR_WINDOWS.get(pid) is not None]
nw = {}
for k, V in fur.items():
    near = LIN.hw(V[:, 0], V[:, 2]) - np.abs(V[:, 1]) < 0.12
    for side, cx in wins:
        h = near & (V[:, 1] * side > 0) & (FP.window_sdf(V[:, 0], V[:, 2], cx) < -0.005)
        if h.any():
            nw[f"{k} @ {'RH' if side > 0 else 'LH'} window STA {cx:.3f}"] = int(h.sum())
report("cabin furniture clear of every cabin / door window (inside the outline, within 0.12 m of the lining)",
       not nw, "clear" if not nw else "; ".join(f"{a}: {n}" for a, n in nw.items()))
nd = {}
for pid, o in FP.DOORS:
    for k, V in fur.items():
        near = LIN.hw(V[:, 0], V[:, 2]) - np.abs(V[:, 1]) < 0.15
        h = near & (V[:, 1] * o["side"] > 0) & (FP.rr((V[:, 0], V[:, 2]), o) < 0.0)
        h &= V[:, 2] > FL + ST_["h"] + 0.002                # floor, carpet and tracks: the sills are below the floor
        if h.any():
            nd[f"{k} in {pid}"] = int(h.sum())
report("cabin furniture clear of the airstair / cargo door and exit clear openings (near the wall)", not nd,
       "clear" if not nd else "; ".join(f"{a}: {n}" for a, n in nd.items()))
EXo = FP.EXIT
ne = {}
for k, V in dict(fur, **{k: verts(k) for k in SEAT_IDS}).items():
    h = (V[:, 1] > I.CLEAR_ZONES["exit_bl"]) & (np.abs(V[:, 0] - EXo["cx"]) < EXo["hx"]) & \
        (V[:, 2] > EXo["cz"] - EXo["hz"]) & (V[:, 2] < EXo["cz"] + EXo["hz"])
    if h.any():
        ne[k] = int(h.sum())
report(f"over-wing exit clear zone (BL > {I.CLEAR_ZONES['exit_bl']:.2f} abeam the hatch, sill to top) free of "
       "furniture and seats", not ne, "clear" if not ne else "; ".join(f"{a}: {n}" for a, n in ne.items()))

# 21 ----------------------------------------------------------------------------------------------- door swings
# the airstair door (with its folding handrails at their unfold fraction) and the cargo door (with its ledge segment)
# from closed to fully open: no triangle crossing the cabin furniture, the seats, the flight deck, the lining, the door
# frames (jambs, stops, lips), the fuselage skins or the belly fairing.  Door travel sampled every 0.02 and every
# 0.005 inside each handrail's unfold window (review r1 M1: 11 samples missed the rail sweeping through the skin);
# at full travel the handrail fittings bear on the jambs by design (door_frames excluded there).
from model import airstair as AS
swing_targets = ["cabin_interior", "flight_deck", "interior_lining", "door_frames", "fus_center", "fus_fwd",
                 "belly_fairing"] + FD_KIDS + CAB_KIDS + SEAT_IDS
fixed_all = {k: posed_mesh(k, I4) for k in swing_targets if k in parts}
for pid in ("door_airstair", "door_cargo"):
    dp = parts[pid].pivot
    kids = [k for k, q in parts.items() if q.parent == pid]
    o = [o for k_, o in FP.DOORS if k_ == pid][0]
    lo = np.array([o["cx"] - o["hx"] - 0.40, -2.6 if o["side"] < 0 else 0.0, -0.2])
    hi = np.array([o["cx"] + o["hx"] + 0.40, 0.0 if o["side"] < 0 else 2.6, 2.9])
    fixed = {k: crop(v, lo, hi) for k, v in fixed_all.items()}
    fracs = set(np.round(np.linspace(0.0, 1.0, 51), 4))
    for k in kids:
        w0, w1 = parts[k].pivot.get("window", (0.0, 1.0))
        fracs |= set(np.round(np.arange(w0, w1 + 1e-9, 0.005), 4))
    bad = {}
    for f in sorted(fracs):
        M = rotation_about(np.asarray(dp["axis"], float), dp["open"] * f, dp["origin"])
        mv = [posed_mesh(pid, M)]
        for k in kids:
            cp = parts[k].pivot
            Mk = M @ rotation_about(cp["axis"], cp["open"] * AS.fold_fraction(cp, f), cp["origin"]) \
                if cp and cp.get("kind") == "fold" else M
            mv.append(posed_mesh(k, Mk))
        mvc = cat(*mv)
        for k, fm in fixed.items():
            if k == "door_frames" and f > 0.999:
                continue
            if not len(fm[1]):
                continue
            n = len(crossings(*mvc, *fm))
            if n:
                bad.setdefault(k, []).append((round(float(f), 3), n))
    detail = "; ".join(f"{k}: " + ", ".join(f"{a:.3f} ({n})" for a, n in v[:6]) + (" .." if len(v) > 6 else "")
                       for k, v in bad.items())
    report(f"{pid}{' + handrails' if kids else ''} closed -> open ({len(fracs)} poses) clear of the cabin furniture, "
           "seats, flight deck, lining, door frames, skins and belly fairing", not bad,
           "clear" if not bad else detail)

# 22 ---------------------------------------------------------------------------------- interior fittings seated
# every connected piece of the interior (flight deck, cabin, lining, seats) touches something: its nearest other
# surface (interior, skins, glazing) within 3 mm, or it crosses / is embedded in one (review r1 C5: knobs, placards,
# boxes floated 10-17 mm clear).  Broad phase: box overlap (3 mm pad); narrow: exact point-triangle distance both ways
# (vertices, edge midpoints, centroids), then triangle crossings for the pieces still apart.
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from isect import _pairs


def _components(V, F_, tol=2e-5):
    key = np.round(V / tol).astype(np.int64)
    _, wi = np.unique(key, axis=0, return_inverse=True)
    wi = wi.ravel()
    Fw = wi[F_]
    E = np.vstack([Fw[:, [0, 1]], Fw[:, [1, 2]], Fw[:, [2, 0]]])
    nv = int(wi.max()) + 1
    _, lab = connected_components(coo_matrix((np.ones(len(E)), (E[:, 0], E[:, 1])), shape=(nv, nv)), directed=False)
    return lab[Fw[:, 0]]


def _pt_tri(P, T):
    """Distance of each point P (n, 3) to the nearest triangle of T (m, 3, 3)."""
    out = np.full(len(P), np.inf)
    a, b, c = T[:, 0], T[:, 1], T[:, 2]
    ab, ac = b - a, c - a
    n = np.cross(ab, ac)
    nn = (n * n).sum(-1) + 1e-30
    d00, d01, d11 = (ab * ab).sum(-1), (ab * ac).sum(-1), (ac * ac).sum(-1)
    den = d00 * d11 - d01 * d01 + 1e-30

    def seg(p, s0, s1):
        d = s1 - s0
        t = np.clip(((p - s0) * d).sum(-1) / ((d * d).sum(-1) + 1e-30), 0, 1)
        return np.linalg.norm(p - (s0 + t[..., None] * d), axis=-1)
    for i0 in range(0, len(P), 32):
        p = P[i0:i0 + 32, None, :]
        t = ((p - a) * n).sum(-1) / nn
        q = p - t[..., None] * n
        v2 = q - a
        d20, d21 = (v2 * ab).sum(-1), (v2 * ac).sum(-1)
        v = (d11 * d20 - d01 * d21) / den
        w = (d00 * d21 - d01 * d20) / den
        inside = (v >= 0) & (w >= 0) & (v + w <= 1)
        de = np.minimum(np.minimum(seg(p, a, b), seg(p, b, c)), seg(p, c, a))
        out[i0:i0 + 32] = np.where(inside, np.abs(t) * np.sqrt(nn), de).min(1)
    return out


INT_IDS = ["flight_deck", "cabin_interior", "interior_lining"] + FD_KIDS + CAB_KIDS + SEAT_IDS
others = ["fus_fwd", "fus_center", "glazing_cabin", "glazing_flightdeck", "door_cargo", "door_frames", "exit_hatch"]
pieces, allT, allC = [], [], []
for pid in INT_IDS + [k for k in others if k in parts]:
    for m, mat in parts[pid].meshes:
        if not len(m.F):
            continue
        T = m.V[m.F]
        if pid not in INT_IDS:
            ok = ((T.max(1) > [2.9, -1.0, 1.1]) & (T.min(1) < [10.0, 1.0, 2.9])).all(1)
            T = T[ok]
            if len(T):
                allT.append(T)
                allC.append(np.full(len(T), -1))
            continue
        lab = _components(m.V, m.F)
        for c in np.unique(lab):
            Tc = T[lab == c]
            k = len(pieces)
            pieces.append((pid, mat, Tc))
            allT.append(Tc)
            allC.append(np.full(len(Tc), k))
allT, allC = np.vstack(allT), np.concatenate(allC)
tlo, thi = allT.min(1), allT.max(1)
plo = np.array([t.reshape(-1, 3).min(0) for _, _, t in pieces]) - 0.003
phi = np.array([t.reshape(-1, 3).max(0) for _, _, t in pieces]) + 0.003
pi_, ti_ = _pairs(plo, phi, tlo, thi, 0.05)
keep = allC[ti_] != pi_
pi_, ti_ = pi_[keep], ti_[keep]
order = np.argsort(pi_, kind="stable")
pi_, ti_ = pi_[order], ti_[order]
starts = np.searchsorted(pi_, np.arange(len(pieces)))
ends = np.searchsorted(pi_, np.arange(len(pieces)), "right")
floating = []
for k, (pid, mat, T) in enumerate(pieces):
    O = allT[ti_[starts[k]:ends[k]]]
    if not len(O):
        floating.append((np.inf, pid, mat, T))
        continue
    S = np.vstack([T.reshape(-1, 3), T.mean(1), 0.5 * (T + np.roll(T, 1, 1)).reshape(-1, 3)])
    S = np.unique(np.round(S, 7), axis=0)
    if len(S) > 300:
        S = S[np.random.default_rng(0).choice(len(S), 300, replace=False)]
    d = _pt_tri(S, O).min()
    if d > 0.003:
        SO = np.unique(np.round(O.reshape(-1, 3), 7), axis=0)
        SO = SO[((SO >= plo[k]) & (SO <= phi[k])).all(1)]
        if len(SO):
            d = min(d, _pt_tri(SO[:600], T).min())
    if d > 0.003:
        VT, VO = T.reshape(-1, 3), O.reshape(-1, 3)
        if len(crossings(VT, np.arange(len(VT)).reshape(-1, 3), VO, np.arange(len(VO)).reshape(-1, 3))):
            continue
        floating.append((d, pid, mat, T))
floating.sort(key=lambda r: -r[0])
report(f"interior fittings seated: every piece ({len(pieces)}) within 3 mm of another surface or crossing it", not floating,
       "all seated" if not floating else "; ".join(
           f"{p_}/{m_} {'> 30' if not np.isfinite(d_) else f'{d_ * 1000:.1f}'} mm at STA {T_[..., 0].mean():.3f} BL "
           f"{T_[..., 1].mean():+.3f} WL {T_[..., 2].mean():.3f}" for d_, p_, m_, T_ in floating[:8]))

# 22b -------------------------------------------------------------------------- lining fittings stand proud
# every small fitting on the lining / headliner (oxygen-mask doors and their dark gap plates, the exit PULL cover, the
# PSU pods, reading lights, downlights, sockets, CB panels, overhead panel: interior_lining pieces other than the lining
# shell itself) shows >= 95 % of its cabin-facing area more than 0.5 mm in front of the surface it sits on (review r2
# C2 / C7: the O2 gap plates were 92-100 % within 0.3 mm of the lining or behind it, the flat downlights half buried).
# Parent surface: the large lining-coloured pieces of interior_lining (side walls, headliner panels, soffits), faces
# wound toward the cabin; distances exact (point-triangle) over the 12 nearest parent triangles.
LIN_MATS = ("lining", "lining_flightdeck", "carpet_flightdeck")     # + the flight deck's carpeted kick panels
par_T, fit_pc = [], []
for m, mat in parts["interior_lining"].meshes:
    T = m.V[m.F]
    lab = _components(m.V, m.F)
    for c in np.unique(lab):
        Tc = T[lab == c]
        A = 0.5 * np.linalg.norm(np.cross(Tc[:, 1] - Tc[:, 0], Tc[:, 2] - Tc[:, 0]), axis=1).sum()
        if mat in LIN_MATS and A > 0.05:
            if not getattr(m, "_reveal", False):          # window / door reveals face into their openings
                par_T.append(Tc)
        else:
            fit_pc.append((mat, Tc))
par_T = np.vstack(par_T)
par_N = np.cross(par_T[:, 1] - par_T[:, 0], par_T[:, 2] - par_T[:, 0])
par_N /= np.maximum(np.linalg.norm(par_N, axis=1, keepdims=True), 1e-15)
par_tree = cKDTree(par_T.mean(1))


def _signed_to_parent(P, k=12):
    """Signed distance of the points P to the parent lining surface (+ = on the cabin side), exact over k candidates."""
    _, idx = par_tree.query(P, k=k)
    best = np.full(len(P), np.inf)
    sgn = np.ones(len(P))
    for j in range(k):
        T = par_T[idx[:, j]]
        a, b, c = T[:, 0], T[:, 1], T[:, 2]
        n = np.cross(b - a, c - a)
        nn = (n * n).sum(1) + 1e-30
        t = ((P - a) * n).sum(1) / nn
        q = P - t[:, None] * n
        d00, d01, d11 = ((b - a) ** 2).sum(1), ((b - a) * (c - a)).sum(1), ((c - a) ** 2).sum(1)
        d20, d21 = ((q - a) * (b - a)).sum(1), ((q - a) * (c - a)).sum(1)
        den = d00 * d11 - d01 * d01 + 1e-30
        v = (d11 * d20 - d01 * d21) / den
        w = (d00 * d21 - d01 * d20) / den
        inside = (v >= 0) & (w >= 0) & (v + w <= 1)
        dist = np.where(inside, np.abs(t) * np.sqrt(nn), np.inf)
        for e0, e1 in ((a, b), (b, c), (c, a)):
            dd = e1 - e0
            tt = np.clip(((P - e0) * dd).sum(1) / ((dd * dd).sum(1) + 1e-30), 0, 1)
            dist = np.minimum(dist, np.linalg.norm(P - (e0 + tt[:, None] * dd), axis=1))
        s_ = np.sign(((P - a) * par_N[idx[:, j]]).sum(1))
        better = dist < best
        best = np.where(better, dist, best)
        sgn = np.where(better, s_, sgn)
    return sgn * best


sunk = []
n_fit = 0
for mat, T in fit_pc:
    C = T.mean(1)
    fn = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    A = 0.5 * np.linalg.norm(fn, axis=1)
    _, idx = par_tree.query(C)
    near = np.linalg.norm(C - par_T[idx].mean(1), axis=1) < 0.06
    if not near.any():
        continue
    face = ((fn / np.maximum(2 * A, 1e-18)[:, None]) * par_N[idx]).sum(1) > 0.3        # cabin-facing faces
    face &= near
    if A[face].sum() < 1e-6:
        continue
    n_fit += 1
    d = _signed_to_parent(C[face])
    frac = float(A[face][d > 0.0005].sum() / A[face].sum())
    if frac < 0.95:
        sunk.append((frac, mat, C.mean(0), float(np.median(d))))
sunk.sort(key=lambda r: r[0])
report(f"lining fittings stand proud: >= 95 % of each piece's cabin-facing area > 0.5 mm in front of the lining "
       f"({n_fit} pieces)", not sunk,
       "all proud" if not sunk else "; ".join(f"{m_} {100 * f_:.0f} % at STA {c_[0]:.3f} BL {c_[1]:+.3f} WL {c_[2]:.3f} "
                                               f"(median {1000 * d_:+.1f} mm)" for f_, m_, c_, d_ in sunk[:8]))

# 22c ------------------------------------------------------------------ divider curtain vs the crew tracks
# the stowed curtain bundle (flight_deck 'curtain', down to the carpet) against the crew seat tracks (review r2 M2: the
# pilot's inboard track end ran 14-17 mm into its foot): no crossing, and the gap along x to every track under it
Vc = np.vstack([m.V for k in ["flight_deck"] + FD_KIDS for m, mm in parts[k].meshes if mm == "curtain"])
Vc = Vc[Vc[:, 2] < FL + 0.10]
gap_ct, x_cr = np.inf, 0
for pid in ("seat_pilot", "seat_copilot"):
    for m, mm in parts[pid].meshes:
        if mm != "metal_dark":
            continue
        for cV in components(m):
            if np.ptp(cV[:, 0]) < 0.4:
                continue                                                # fittings: the tracks are the long pieces
            under = (Vc[:, 1] > cV[:, 1].min() - 0.002) & (Vc[:, 1] < cV[:, 1].max() + 0.002)
            if under.any():
                gap_ct = min(gap_ct, float(Vc[under, 0].min() - cV[:, 0].max()))
cm_ = [m for k in ["flight_deck"] + FD_KIDS for m, mm in parts[k].meshes if mm == "curtain"]
tm_ = [m for pid in ("seat_pilot", "seat_copilot") for m, mm in parts[pid].meshes if mm in ("metal_dark", "seat_base_black")]
x_cr = len(crossings(*cat(*[(m.V, m.F) for m in cm_]), *cat(*[(m.V, m.F) for m in tm_])))
report("divider curtain bundle clear of the crew seat tracks (L6B curtain_track)", x_cr == 0 and gap_ct > 0.0,
       f"{x_cr} crossings, gap {gap_ct * 1000:.0f} mm (L6B {I.divider_items_clearance()['curtain_track'] * 1000:.0f})")

# 23 ----------------------------------------------------------------------------------------- shell orientation
# closed interior shells wound outward (positive signed volume) and consistently (no directed edge used twice); the
# viewer / renders show both sides, but a single-sided view or a normal map must see the outside (review r1 C6)
inward, incons = [], []
for pid in INT_IDS:
    for m, mat in parts[pid].meshes:
        if not len(m.F):
            continue
        key = np.round(m.V / 2e-5).astype(np.int64)
        _, wi = np.unique(key, axis=0, return_inverse=True)
        wi = wi.ravel()
        T0 = m.V[m.F]
        okf = (np.linalg.norm(np.cross(T0[:, 1] - T0[:, 0], T0[:, 2] - T0[:, 0]), axis=1) > 1e-12)
        Fw = wi[m.F]
        okf &= (Fw[:, 0] != Fw[:, 1]) & (Fw[:, 1] != Fw[:, 2]) & (Fw[:, 0] != Fw[:, 2])   # poles, collapsed rims
        Fw, F_ok = Fw[okf], m.F[okf]
        lab = _components(m.V, F_ok)
        E = np.vstack([Fw[:, [0, 1]], Fw[:, [1, 2]], Fw[:, [2, 0]]])
        El = np.tile(lab, 3)
        _, cd = np.unique(np.c_[E, El], axis=0, return_counts=True)
        if (cd > 1).sum():
            incons.append(f"{pid}/{mat}: {int((cd > 1).sum())}")
        Es = np.sort(E, 1)
        u, cnt = np.unique(np.c_[Es, El], axis=0, return_counts=True)
        open_c = set(u[cnt == 1][:, 2])
        T = m.V[F_ok]
        vol = np.bincount(lab, weights=np.einsum("ij,ij->i", T[:, 0], np.cross(T[:, 1], T[:, 2])) / 6.0)
        for c in range(len(vol)):
            if c not in open_c and vol[c] < -1e-10:
                inward.append(f"{pid}/{mat} at STA {T[lab == c][..., 0].mean():.3f}")
report("interior closed shells wound outward, directed edges consistent", not inward and not incons,
       "ok" if not inward and not incons else
       f"{len(inward)} inward closed shells ({'; '.join(inward[:5])}); inconsistent: {'; '.join(incons[:6])}")
# per primitive: vertex normals against the face winding (review r2 N1: strap ends and curtain folds had cos = -1
# normals, dark in a single-sided renderer): flag a part / material with > 1 % of its area where a corner normal points
# against its face's normal
bad_n = []
for pid in INT_IDS:
    for m, mat in parts[pid].meshes:
        if not len(m.F) or m.N is None or len(m.N) != len(m.V):
            continue
        T = m.V[m.F]
        fn = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        A = 0.5 * np.linalg.norm(fn, axis=1)
        ok_ = A > 1e-12
        cosv = np.einsum("fij,fj->fi", m.N[m.F], fn / np.maximum(2 * A, 1e-18)[:, None])
        frac = float(A[ok_ & (cosv < 0).any(1)].sum() / max(A.sum(), 1e-18))
        if frac > 0.01:
            bad_n.append(f"{pid}/{mat} {100 * frac:.1f} %")
report("interior vertex normals agree with the face winding (<= 1 % of each primitive's area against it)", not bad_n,
       "ok" if not bad_n else "; ".join(bad_n[:8]))

# 24 ------------------------------------------------------------------------ crew harness on the fleece
# lap belts / straps must lie ON the sheepskin (review r3 K1: 66 % of the lap-belt vertices were below the local fleece
# top, 417 crossings per seat): exact triangle crossings harness x (sheepskin + leather cushion), and over the seat's
# fleece top (upward faces, normal z > 0.8, forward of the back) every harness vertex >= 1 mm above that surface
for pid in ("seat_pilot", "seat_copilot"):
    Hm = [m for m, mm in parts[pid].meshes if mm == "harness"]
    Sm = [m for m, mm in parts[pid].meshes if mm in ("sheepskin", "leather_crew")]
    nx = len(crossings(*cat(*[(m.V, m.F) for m in Hm]), *cat(*[(m.V, m.F) for m in Sm])))
    srp = I.crew_srp(-1 if pid == "seat_pilot" else 1)
    Hv = np.vstack([m.V for m in Hm])
    Hv = Hv[(Hv[:, 0] < srp[0] - 0.02) & (Hv[:, 2] < srp[2] + 0.08)]
    T = np.vstack([m.V[m.F] for m, mm in parts[pid].meshes if mm == "sheepskin"])
    nz = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    nz = nz[:, 2] / np.maximum(np.linalg.norm(nz, axis=1), 1e-18)
    T = T[(nz > 0.8) & (T[:, :, 0].max(1) < srp[0] - 0.02) & (T[:, :, 2].min(1) < srp[2] + 0.08)]
    worst, n_on = np.inf, 0
    for i0 in range(0, len(Hv), 256):
        P = Hv[i0:i0 + 256]
        a, b, c = T[:, 0][None], T[:, 1][None], T[:, 2][None]
        det = (b[..., 1] - c[..., 1]) * (a[..., 0] - c[..., 0]) + (c[..., 0] - b[..., 0]) * (a[..., 1] - c[..., 1])
        det = np.where(np.abs(det) < 1e-14, 1e-14, det)
        l0 = ((b[..., 1] - c[..., 1]) * (P[:, None, 0] - c[..., 0]) + (c[..., 0] - b[..., 0]) *
              (P[:, None, 1] - c[..., 1])) / det
        l1 = ((c[..., 1] - a[..., 1]) * (P[:, None, 0] - c[..., 0]) + (a[..., 0] - c[..., 0]) *
              (P[:, None, 1] - c[..., 1])) / det
        l2 = 1.0 - l0 - l1
        inside = (l0 >= 0) & (l1 >= 0) & (l2 >= 0)
        zs = np.where(inside, l0 * a[..., 2] + l1 * b[..., 2] + l2 * c[..., 2], -np.inf).max(1)
        on = np.isfinite(zs)
        n_on += int(on.sum())
        if on.any():
            worst = min(worst, float((P[on, 2] - zs[on]).min()))
    report(f"{pid} harness on the fleece: no crossing, >= 1 mm above its top", nx == 0 and worst >= 0.001,
           f"{nx} crossings with the sheepskin / cushion; {n_on} harness vertices over the fleece top, least height "
           f"{worst * 1000:+.1f} mm")

# 25 ------------------------------------------------------------------------ crew seats vs the pedestal
# the seat (armrests down and stowed) translated over its fore / aft and height travel against the pedestal group of
# model/flightdeck.py (quadrant, rails, PCL paddle, flap lever, CCD, T-handles): exact point-triangle distances from
# the seat's vertices near the pedestal (review r3 C2: the full-forward, full-down inboard sleeve came within 6 mm)
from model import flightdeck as FDK, seats as SEATS
Tp = np.vstack([m.V[m.F] for m, _ in FDK.build_flightdeck(groups=True)["pedestal"]])
Tp = Tp[Tp[:, :, 0].max(1) > 3.70]
crit = float(I.CRITERIA["arm_pedestal"])
res_ = []
for side in (-1, 1):
    for up in (False, True):
        Vs0 = np.vstack([m.V for m, _ in SEATS.crew_seat(side, arm_up=(up, up), tracks=False, harness=False)])
        Vs0 = Vs0[np.abs(Vs0[:, 1]) < 0.20]
        best = (np.inf, None)
        for dx in (-CS["travel_x"], 0.0, CS["travel_x"]):
            for dz in (-CS["travel_z"], 0.0, CS["travel_z"]):
                Vs = Vs0 + [dx, 0.0, dz]
                near = Vs[(Vs[:, 0] < Tp[:, :, 0].max() + 0.03) & (Vs[:, 2] < Tp[:, :, 2].max() + 0.03)]
                if not len(near):
                    continue
                d = _pt_tri(near, Tp)
                k = int(np.argmin(d))
                if d[k] < best[0]:
                    best = (float(d[k]), (dx, dz, near[k]))
        res_.append((side, up, best))
worst_ = min(res_, key=lambda r: r[2][0])
report(f"crew seats (armrests down / stowed) clear of the pedestal over the travel (>= {crit * 1000:.0f} mm, CRITERIA "
       f"arm_pedestal)", worst_[2][0] >= crit,
       "; ".join(f"{'P' if s_ < 0 else 'CP'} arms {'up' if u_ else 'down'} {b_[0] * 1000:.1f} mm" for s_, u_, b_ in res_)
       + f" (worst at dx {worst_[2][1][0] * 1000:+.0f} / dz {worst_[2][1][1] * 1000:+.0f} mm, "
         f"STA {worst_[2][1][2][0]:.3f} BL {worst_[2][1][2][1]:+.3f} WL {worst_[2][1][2][2]:.3f}; L6B "
         f"{I.crew_checks(-1)['arm_pedestal'] * 1000:.0f})")

# 26 ------------------------------------------------------------------------ coplanar faces (z-fighting)
# two faces of different materials in the same plane (within 0.1 mm), facing the same way and overlapping flicker in
# the viewer at grazing angles (review r3 K3: crew-seat track brackets in the side plates' outer faces, the glareshield
# end cap on a panel_dark triangle); same-material overlaps are invisible and ignored
from isect import _pairs
zf_T, zf_key = [], []
for pid in INT_IDS:
    for m, mat in parts[pid].meshes:
        if len(m.F):
            zf_T.append(m.V[m.F])
            zf_key += [(pid, mat)] * len(m.F)
zf_T = np.vstack(zf_T)
zf_key = np.array([f"{p_}/{m_}" for p_, m_ in zf_key])
zf_mat = np.array([k.split("/")[1] for k in zf_key])
zn = np.cross(zf_T[:, 1] - zf_T[:, 0], zf_T[:, 2] - zf_T[:, 0])
zA = 0.5 * np.linalg.norm(zn, axis=1)
ok_ = zA > 1e-9
zn = zn / np.maximum(2 * zA, 1e-18)[:, None]
zC = zf_T.mean(1)
lo_, hi_ = zf_T.min(1) - 0.0005, zf_T.max(1) + 0.0005
h_ = float(np.clip(2 * np.median((hi_ - lo_).max(1)), 0.005, 0.1))
ii, jj = _pairs(lo_, hi_, lo_, hi_, h_)
m_ = (ii < jj) & ok_[ii] & ok_[jj] & (zf_mat[ii] != zf_mat[jj])
ii, jj = ii[m_], jj[m_]
m_ = ((zn[ii] * zn[jj]).sum(1) > 0.995) & (np.abs(((zC[ii] - zf_T[jj, 0]) * zn[jj]).sum(1)) < 1e-4)
ii, jj = ii[m_], jj[m_]


def _in_tri(P, Tr):
    e1, e2, s_ = Tr[:, 1] - Tr[:, 0], Tr[:, 2] - Tr[:, 0], P - Tr[:, 0]
    d00, d01, d11 = (e1 * e1).sum(1), (e1 * e2).sum(1), (e2 * e2).sum(1)
    d20, d21 = (s_ * e1).sum(1), (s_ * e2).sum(1)
    den = np.maximum(d00 * d11 - d01 * d01, 1e-30)
    v_, w_ = (d11 * d20 - d01 * d21) / den, (d00 * d21 - d01 * d20) / den
    return (v_ > -1e-6) & (w_ > -1e-6) & (v_ + w_ < 1 + 1e-6)


m_ = _in_tri(zC[ii], zf_T[jj]) | _in_tri(zC[jj], zf_T[ii])
ii, jj = ii[m_], jj[m_]
zf = {}
for a_, b_ in zip(ii, jj):
    k_ = tuple(sorted((zf_key[a_], zf_key[b_])))
    r_ = zf.setdefault(k_, [0.0, zC[a_]])
    r_[0] += min(zA[a_], zA[b_])
bad_zf = sorted(((a_, k_, c_) for k_, (a_, c_) in zf.items() if a_ > 0.5e-4), key=lambda r: -r[0])
report("interior: no coplanar same-facing overlaps of different materials (<= 0.5 cm2 per pair)", not bad_zf,
       "none" if not bad_zf else "; ".join(f"{k_[0]} vs {k_[1]} {a_ * 1e4:.1f} cm2 at STA {c_[0]:.3f} BL {c_[1]:+.3f} "
                                           f"WL {c_[2]:.3f}" for a_, k_, c_ in bad_zf[:8]))

tail = f" ({len(opens)} open owner decision{'s' if len(opens) != 1 else ''}: {'; '.join(opens)})" if opens else ""
print(("FIT OK" + tail) if not fails else f"FIT FAIL ({len(fails)}): " + "; ".join(fails) + tail)
sys.exit(1 if fails else 0)
