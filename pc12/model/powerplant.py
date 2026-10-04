"""
Powerplant: Pratt & Whitney Canada PT6E-67XP (reverse-flow free-turbine turboprop,
4 axial + 1 centrifugal compressor stages, 1,200 shp take-off) and the Hartzell
5-blade composite propeller (2.67 m / 105 in, 1,700 rpm; 1,550 rpm low mode).

The engine is modelled as its modules so the exploded view reads like the real
architecture: air enters the rear inlet screen, is compressed forward, burned in
the reverse-flow annular combustor, drives the compressor turbine then the power
turbine, and leaves through the twin exhaust ports just behind the gearbox.
Module envelopes are proportioned estimates, not manufacturer drawings.
"""
from __future__ import annotations
import numpy as np

from cad.mesh import (Mesh, revolve, sweep_profile, sweep_tube, cylinder, box, superellipsoid,
                      grid_surface, cap_ring, rotation_matrix, planar_cap, trim)
from model.airfoil import Airfoil, modified4_thickness, naca4_thickness
from model.lifting import cos_pts
from model.parts import Part
from model import fuselage as F

AX_Z = F.PROP_AXIS_Z   # WL of the thrust axis at the propeller disc (0.32 m clearance + 1.335 m radius)
PROP_R = 1.335
N_BLADES = 5

# ---- thrust line (Stage 2, from the Pilatus drawing 190.10.40.432) -------------------------------------------------
# The drawn propeller disc is an edge-on line tilted 2.00 deg top-forward in the side view and 2.00 deg with the
# starboard end aft in the plan (disc centre STA 925); the drawn spinner centre lines slope +1.93 deg (side) and
# -1.92 deg (plan, BL +22 at the tip, BL 0 at the cowl front).  So the thrust line is tilted 2 deg nose-down and
# yawed 2 deg to starboard (right thrust).  Kept fixed: axis WL 1655 AT THE DISC and the 320 clearance (the tilt adds
# 0.8 mm); the yaw pivots about the cowl front on the centre line (the drawn spinner base is on BL 0 there).
THRUST_TILT_DEG = 2.0   # nose-down: the axis rises aft, the disc top leans forward
THRUST_YAW_DEG = 2.0    # to starboard: the axis points forward-starboard, the spinner tip is on +BL
PROP_X = 0.925          # propeller disc (blade pitch-change axes) on the thrust axis; drawn 925 (rev A 800)
PROP_Y = float((F.STA["cowl_front"] - PROP_X) * np.tan(np.radians(THRUST_YAW_DEG)))   # disc centre BL (+4 mm)
_TT, _TY = np.tan(np.radians(THRUST_TILT_DEG)), np.tan(np.radians(THRUST_YAW_DEG))


def thrust_dir():
    """Unit vector of the thrust (forward along the propeller axis)."""
    d = np.array([-1.0, _TY, -_TT])
    return d / np.linalg.norm(d)


def axis_point(x):
    """Point(s) (x, y, z) on the thrust axis at station(s) x."""
    x = np.asarray(x, float)
    return np.stack([x, PROP_Y - (x - PROP_X) * _TY, AX_Z + (x - PROP_X) * _TT], -1)


def prop_hub():
    """Disc centre (x, y, z) = hub centre / blade pitch-change axes on the thrust axis."""
    return axis_point(PROP_X)


def spinner_profile(n=80):
    """Spinner meridian (t in 0..1 from the tip at STA spinner_tip to the base at the cowl front, radius r) from
    fuselage.SPINNER_R / SPINNER_SHAPE."""
    a, b = F.SPINNER_SHAPE
    t = np.linspace(0, 1, n)
    return t, F.SPINNER_R * (1 - (1 - t) ** a) ** b


def spinner_silhouette(view="side", n=80):
    """Closed spinner outline in a view's coordinates, on the tilted / yawed thrust axis: 'side' -> (x, z) seen
    from port, 'plan' -> (x, y) seen from above.  The spinner is a body of revolution about the thrust axis from its
    tip (STA spinner_tip) to its base plane at the cowl front."""
    t, r = spinner_profile(n)
    x0, x1 = F.STA["spinner_tip"], F.STA["cowl_front"]
    c = axis_point(x0 + (x1 - x0) * t)
    k = 2 if view == "side" else 1
    ax = np.array([1.0, _TT if view == "side" else -_TY])
    ax /= np.linalg.norm(ax)
    nrm = np.array([-ax[1], ax[0]])                  # in-plane normal (up / starboard)
    a = np.c_[c[:, 0], c[:, k]]
    upper = a + r[:, None] * nrm
    lower = a - r[:, None] * nrm
    return np.vstack([upper, lower[::-1]])


def prop_disc_edge(view="side"):
    """End points of the edge-on propeller disc: 'side' -> (x, z) (top first), 'plan' -> (x, y) (starboard first)."""
    h = prop_hub()
    if view == "side":
        ax = np.array([1.0, _TT])
        c = np.array([h[0], h[2]])
    else:
        ax = np.array([1.0, -_TY])
        c = np.array([h[0], h[1]])
    ax /= np.linalg.norm(ax)
    nrm = np.array([-ax[1], ax[0]])
    return np.array([c + PROP_R * nrm, c - PROP_R * nrm])


def prop_clearance():
    """Ground clearance of the lowest blade tip with the tilted disc (m)."""
    n = thrust_dir()
    return float(AX_Z - PROP_R * np.sqrt(1.0 - n[2] ** 2))


def thrust_rotation():
    """3x3 rotation taking the model +x axis onto the thrust axis pointing aft (-thrust_dir())."""
    a = -thrust_dir()
    x = np.array([1.0, 0.0, 0.0])
    v = np.cross(x, a)
    s_, c = np.linalg.norm(v), float(x @ a)
    return rotation_matrix(v / s_, np.arctan2(s_, c)) if s_ > 1e-12 else np.eye(3)


def thrust_matrix():
    """4x4 transform of the engine / propeller (built about the untilted line (x, 0, AX_Z)) onto the thrust line:
    rotation about the disc centre on the drafted line, translated onto prop_hub()."""
    M = np.eye(4)
    R = thrust_rotation()
    M[:3, :3] = R
    M[:3, 3] = prop_hub() - R @ np.array([PROP_X, 0.0, AX_Z])
    return M


# Propeller hub (rotating, estimated): a cylinder PROP_HUB['r'] on the thrust axis from 'fwd' ahead of to 'aft' behind
# the disc (it carries the five blade roots at the pitch-change axes).  The prop-shaft flange (engine STA 0) is bolted
# to its aft face: the engine sits ENG_FLANGE_GAP behind the hub on the thrust line (MV2-03: the rev-A flange at
# STA 0.885 put the reduction gearbox 140 mm into the hub and through the spinner bulkhead).
PROP_HUB = dict(r=0.130, fwd=0.070, aft=0.055)
ENG_FLANGE_GAP = 0.008

# EASA TCDS IM.E.008: PT6E-67XP overall length 1,870.9 mm, overall diameter 481.8 mm.
ENG_FLANGE_X = PROP_X + PROP_HUB["aft"] + ENG_FLANGE_GAP     # prop-shaft flange face (on the drafted, untilted line)
ENG_LENGTH = 1.8709
ENG_DIAM = 0.4818
_DRAFT_FLANGE = 0.885    # the module layout below was drafted from a flange at 0.885 on a 1.915 m envelope
_SX = ENG_LENGTH / (2.80 - _DRAFT_FLANGE)
_SR = 0.222 / 0.270      # case radius so that case + external fuel manifold = TCDS overall diameter


def eng_x(x):
    """Map a drafted station onto the certified engine envelope (flange face at ENG_FLANGE_X)."""
    return ENG_FLANGE_X + (np.asarray(x, float) - _DRAFT_FLANGE) * _SX


def rev(profile, n=40, x0=0.0, ref=None):
    """Revolve a drafted (x, r) profile about the thrust line, scaled to the TCDS envelope."""
    prof = [(float(eng_x(x)) - x0, r * _SR) for x, r in profile]
    return revolve(prof, n=n, axis_origin=(x0, 0, AX_Z), axis_dir=(1, 0, 0), cap_ends=True)


def smooth_profile(pts, n=60):
    from scipy.interpolate import PchipInterpolator
    pts = np.asarray(pts, float)
    f = PchipInterpolator(pts[:, 0], pts[:, 1])
    x = np.linspace(pts[0, 0], pts[-1, 0], n)
    return list(zip(x, f(x)))


# ---------------------------------------------------------------------------
# engine modules
# ---------------------------------------------------------------------------

def build_engine(parts):
    mods = []

    # reduction gearbox (2-stage planetary) + propeller shaft flange
    rgb = rev(smooth_profile([(0.885, 0.0), (0.886, 0.135), (0.93, 0.14), (0.95, 0.10), (0.99, 0.17),
                              (1.06, 0.225), (1.15, 0.245), (1.24, 0.225), (1.285, 0.200)], 50), n=44)
    mods.append(("eng_rgb", "Reduction gearbox (2-stage planetary)", rgb, "metal", (-1.20, 0, 0),
                 "Prop shaft flange = engine STA 0 (TCDS length 1,870.9 mm)"))

    # exhaust duct with two ports
    ex = rev(smooth_profile([(1.285, 0.200), (1.33, 0.235), (1.42, 0.250), (1.52, 0.240), (1.56, 0.215)], 30), n=44)
    ports = []
    for sgn in (1, -1):
        path = np.array([[float(eng_x(1.43)), sgn * 0.10, AX_Z], [float(eng_x(1.44)), sgn * 0.235, AX_Z - 0.005]])
        ports.append(sweep_profile(path, ellipse(0.075, 0.105, 20), True, cap=False))
    mods.append(("eng_exhaust", "Exhaust duct (twin ports)", Mesh.merge([ex] + ports), "exhaust", (-0.85, 0, 0),
                 "Heat-resistant steel"))

    # power turbine (2 stages)
    pt = rev(smooth_profile([(1.56, 0.215), (1.60, 0.225), (1.68, 0.228), (1.73, 0.235)], 20), n=44)
    mods.append(("eng_pt", "Power turbine (2 stages) + compressor turbine (1 stage)", pt, "hot_section", (-0.55, 0, 0),
                 "Free power turbine drives the propeller only"))

    # combustion chamber (reverse-flow annular) with 14 fuel nozzles
    cc = rev(smooth_profile([(1.73, 0.235), (1.78, 0.262), (1.90, 0.270), (2.02, 0.262), (2.08, 0.245)], 36), n=48)
    nozzles = []
    for k in range(14):
        a = 2 * np.pi * k / 14
        d = np.array([0, np.cos(a), np.sin(a)])
        p0 = np.array([float(eng_x(1.84)), 0, AX_Z]) + 0.214 * d
        p1 = np.array([float(eng_x(1.88)), 0, AX_Z]) + 0.2325 * d
        nozzles.append(cylinder(p0, p1, 0.010, n=8))
    manifold = sweep_tube(ring_path(float(eng_x(1.88)), (ENG_DIAM / 2) - 0.0084, 64), 0.0084, n=8, cap=False)
    mods.append(("eng_combustor", "Combustion chamber + 14 fuel nozzles", Mesh.merge([cc] + nozzles + [manifold]),
                 "hot_section", (-0.25, 0, 0), "Folded (reverse-flow) annular liner; nozzle count est."))

    # gas generator: centrifugal diffuser + 4-stage axial compressor case
    gg = rev(smooth_profile([(2.08, 0.245), (2.11, 0.262), (2.17, 0.262), (2.22, 0.225), (2.30, 0.205),
                             (2.42, 0.195), (2.46, 0.200)], 40), n=48)
    mods.append(("eng_compressor", "Compressor (4 axial + 1 centrifugal)", gg, "metal", (0.10, 0, 0),
                 "Gas-generator case"))

    # air inlet screen (plenum)
    scr = rev([(2.46, 0.200), (2.47, 0.232), (2.60, 0.232), (2.61, 0.195)], n=48)
    mods.append(("eng_inlet_screen", "Air inlet screen (plenum)", scr, "metal_dark", (0.40, 0, 0),
                 "Rear-facing inlet, fed from the chin duct"))

    # accessory gearbox + accessories
    agb = rev(smooth_profile([(2.61, 0.195), (2.66, 0.205), (2.73, 0.200), (2.78, 0.170), (2.80, 0.0)], 20), n=40)
    ae = float(eng_x(2.78))
    acc = [cylinder((ae - 0.02, 0.10, AX_Z + 0.06), (ae + 0.12, 0.10, AX_Z + 0.06), 0.06, n=24),   # starter-generator
           cylinder((ae - 0.02, -0.10, AX_Z + 0.05), (ae + 0.08, -0.10, AX_Z + 0.05), 0.045, n=20),  # fuel pump
           box((ae + 0.04, -0.02, AX_Z - 0.10), (0.12, 0.15, 0.07)),                             # fuel metering unit
           box((float(eng_x(2.70)), 0.0, AX_Z + 0.215), (0.12, 0.18, 0.04))]                        # EEC (FADEC)
    mods.append(("eng_agb", "Accessory gearbox, starter-gen, FADEC", Mesh.merge([agb] + acc), "metal_dark",
                 (0.75, 0, 0), "Dual-channel EEC / FADEC"))

    Mt = thrust_matrix()                     # the engine is installed on the thrust line (2 deg down, 2 deg right)
    for pid, name, mesh, mat, exp, note in mods:
        p = Part(pid, name, "powerplant", explode=exp, group="Engine PT6E-67XP", material_note=note,
                 info={"axis": "on the thrust line: 2 deg nose-down, 2 deg right (drawing)"})
        p.add(mesh.transformed(Mt), mat)
        parts[pid] = p

    # engine mount truss (mount ring at the gas generator, on the thrust line -> 4 firewall pick-ups)
    tubes = []
    xf = lambda P: (Mt[:3, :3] @ np.asarray(P, float).T).T + Mt[:3, 3]            # noqa: E731
    xr = float(eng_x(2.235))                 # mount ring round the gas-generator case (centrifugal diffuser)
    ring = xf(ring_path(xr, 0.30, 64))
    tubes.append(sweep_tube(ring, 0.016, n=10, cap=False))
    pads = [xf(np.array([xr, 0, AX_Z]) + 0.30 * np.array([0, np.cos(a), np.sin(a)]))
            for a in np.radians([45, 135, 225, 315])]
    fw = [np.array([2.985, 0.33 * np.sign(np.cos(a)), AX_Z + 0.29 * np.sign(np.sin(a))])
          for a in np.radians([45, 135, 225, 315])]
    for i, p in enumerate(pads):
        for j in (i, (i + 1) % 4):
            tubes.append(cylinder(p, fw[j], 0.017, n=10))
    for q in fw:
        tubes.append(box(q + [0.0, 0, 0], (0.03, 0.08, 0.08)))
    mount = Part("engine_mount", "Engine mount truss", "powerplant", explode=(0.35, 0, -0.55),
                 group="Powerplant installation", material_note="Welded 4130 steel tube")
    mount.add(Mesh.merge(tubes), "black")
    parts[mount.id] = mount

    # firewall (titanium) = fuselage section at STA 3.000, inset, notched round the nose-gear trunnion / bay
    from model.fuselage_parts import bulkhead, nose_trunnion_notch
    fwp = Part("firewall", "Firewall (titanium, frame 10)", "powerplant", explode=(0.0, 0, 0),
               group="Powerplant installation", material_note="Titanium + insulation, STA 3.000")
    fwp.add(bulkhead(F.STA["firewall"] - 0.005, 0.97, notch=nose_trunnion_notch, normal=(-1, 0, 0)), "titanium")
    parts[fwp.id] = fwp


def ellipse(a, b, n=24):
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.stack([a * np.cos(th), b * np.sin(th)], 1)


def ring_path(x, r, n):
    th = np.linspace(0, 2 * np.pi, n)
    return np.stack([np.full(n, x), r * np.cos(th), AX_Z + r * np.sin(th)], 1)


# ---------------------------------------------------------------------------
# chin inlet and exhaust stacks (external)
# ---------------------------------------------------------------------------
# Exhaust stack (starboard; mirrored for port).  Stage 3 VQA r2 (SHP2-01) re-read of the Pilatus drawing 190.10.40.432,
# checked on the s/n 3008 photos 81 / 130 / 188 (camera fits) and the Pilatus tech-data side render:
#   * the tube leaves the cowl side square to it (centre STA 1.545, drawn root walls STA 1.43 / 1.665), turns aft in a
#     tight bend (drawn inner wall corner STA 1.68 / BL 0.445) and then runs STRAIGHT aft-outboard at STACK_BEND['az']
#     from the fuselage axis (the drawn plan's straight inner wall STA 1.68 / BL 0.44 -> STA 1.97 / BL 0.655);
#   * the outlet is SCARFED by the vertical plane STACK_SCARF, which runs from the inner lip (aft-most point, STA 1.97 /
#     BL 0.655) forward-outboard to the outer lip (the drawn plan's 'sharp outer corner' STA 1.71 / BL 0.748), so the
#     mouth faces aft-OUTBOARD (normal ~20 deg aft of outboard).  From the forward-outboard cameras (81 / 130) the
#     mouth is seen almost edge-on -- the straight vertical aft lip and the dark trapezoid of the photos -- from 188 it
#     is seen at ~30 deg (the dark opening with the lit inner wall), from the side (drawn side view, tech-data render)
#     face-on, a dark opening STA 1.72-1.96.  (Rev C read the corner as an elbow and turned the tube back inboard,
#     with the mouth facing aft-inboard: from ahead-outboard the outer wall then wrapped round into a rounded dome.)
#   * section: ellipse STACK_AB, 0.22 wide in plan (the drawn walls are 0.229 apart) and 0.188 tall (front view WL
#     1601-1788); centre WL AX_Z + STACK_DZ (drawn 1.69-1.70 less the drawing's 15-18 mm higher nose / prop axis).
# STACK_PTS: the centre line's key points (root inside the cowl, bend start, bend end, straight end beyond the scarf
# plane) -- derived from STACK_ROOT / STACK_BEND, kept for the drawings (STACK_PTS[1] = where the tube leaves the cowl).
STACK_ROOT = (1.545, 0.260)      # centre line start (inside the cowl, below the cut-out bottom), heading outboard
STACK_BEND = dict(y=0.401, r=0.150, az=36.5, out=0.46)   # bend start BL, centre-line radius, heading after the
#                                  bend (deg from the fuselage axis, outboard), straight length after the bend (m)
STACK_DZ = (0.025, 0.031)        # centre WL - AX_Z at the root / at the end (a slight rise)
STACK_AB = (0.110, 0.094)        # section half-sizes: plan (horizontal) / side (vertical)
STACK_N = 2.6                    # section superellipse exponent |u/a|^n + |v/b|^n = 1: a rounded rectangle (drawn front
#                                  view: flat top / bottom and a flat outboard end with ~50 mm corners; photos 81 / 130
#                                  / 188: straight-sided black outlet trapezoid with sharp corners).  VQA r3: 3.4 -> 2.6,
#                                  photos 130 / 3001 show a round-shouldered tube (curved reflection bands); at 3.4 the
#                                  flat sides mirrored the hangar as one slab and the stack read as a box


def stack_section(th, a=None, b=None, n=None):
    """(u, v) of the stack section (superellipse STACK_N, half-sizes STACK_AB) at the parameter angles th, and the
    unnormalised outward normal (nu, nv) there."""
    a = STACK_AB[0] if a is None else a
    b = STACK_AB[1] if b is None else b
    n = STACK_N if n is None else n
    c, s_ = np.cos(th), np.sin(th)
    u = a * np.sign(c) * np.abs(c) ** (2.0 / n)
    v = b * np.sign(s_) * np.abs(s_) ** (2.0 / n)
    nu = np.sign(c) * np.abs(c) ** (2.0 - 2.0 / n) / a
    nv = np.sign(s_) * np.abs(s_) ** (2.0 - 2.0 / n) / b
    return u, v, nu, nv
# VQA r3 SHP3-04: the section is not constant -- photos 130 / 188 / s/n 3001: the tube leaves the cowl ROUND (inside a
# round dark ring) and flattens into the rounded-rectangle outlet, ~15-20 % lower at the mouth than at the root.  The
# section law along the centre line (stack_section_law): a circle of STACK_ROUND['r'] on the root piece, blended over
# the bend (C1 smoothstep in arc length) into the STACK_AB / STACK_N superellipse, whose vertical half-size then falls
# to STACK_ROUND['b_out'] at the end of the outlet straight.
# model judging r1 EXT1-01 (photos 130 / 81 / 188: the outlet a full-height black trapezoid, the tube full-height or
# flaring slightly to the mouth): the outlet's vertical half-size 0.080 -> 0.098, a ~4 % flare over STACK_AB (the
# 15-20 % taper of VQA r3 made the mouth read as a plain cut cylinder)
STACK_ROUND = dict(r=0.095, b_out=0.098)


def stack_section_law(s):
    """(a, b, n) of the stack section at arc length(s) s along the centre line (see STACK_ROUND)."""
    s = np.asarray(s, float)
    L0, La, L1 = _stack_lengths()
    t = np.clip((s - L0) / La, 0.0, 1.0)
    w = t * t * (3.0 - 2.0 * t)
    r = STACK_ROUND["r"]
    a = r + (STACK_AB[0] - r) * w
    b = r + (STACK_AB[1] - r) * w
    tb = np.clip((s - L0 - La) / L1, 0.0, 1.0)
    b = b + (STACK_ROUND["b_out"] - STACK_AB[1]) * tb * tb * (3.0 - 2.0 * tb)
    n = 2.0 + (STACK_N - 2.0) * w
    return a, b, n


def stack_th(m):
    """m section parameter angles spaced uniformly in ARC LENGTH round the superellipse (angle-uniform samples bunch
    at the corners and leave ~22 mm between generators on the flat sides at STACK_N 3.4)."""
    thd = np.linspace(0.0, 2 * np.pi, 4097)
    u, v, _, _ = stack_section(thd)
    sl = np.r_[0.0, np.cumsum(np.hypot(np.diff(u), np.diff(v)))]
    return np.interp(np.arange(m) * sl[-1] / m, sl, thd)


STACK_SCARF = ((1.970, 0.655), (1.721, 0.744))    # outlet plane (vertical), plan (STA, BL): inner lip -> outer lip
# VQA r3 (SHP2-01 re-check on photos 130 / 188 and the PRO s/n 3001 port close-up): there is NO black band on the
# OUTSIDE of the tube -- the polished wall runs right to the scarf lip; the 'black collar' of the photos is the sooted
# INSIDE of the mouth, seen through the aft-outboard-facing scarf (3001, near broadside: the chrome ends in the
# forward-bulging near lip curve '(' at STA ~1.72 and the black runs to the rounded inner lip at ~1.97; 130: a black
# trapezoid over the model mouth's projected STA range; 188: black with a lit polished strip along the far wall).
# rev r2 painted a 65 mm soot band on the outer skin, which read as a black end cap.
STACK_COLLAR = 0.0               # heat-blackened band on the OUTER skin upstream of the scarf cut (none, see above)
STACK_GAP = 0.018                # dark annular cut-out round the tube where it leaves the cowl (radial clearance, rev r2)
STACK_GAP_DEPTH = 0.045          # ... its depth into the cowl (dark liner wall + bottom ring)
# VQA r3: the cut-out is an ELLIPSE, not the tube's rounded rectangle grown by STACK_GAP (photos 130 / 3001: a round
# dark gap, ~12-15 mm above and ahead of the tube, ~30 mm below it): semi-axes STACK_AB + (da, db), exponent n, centre
# dz below the tube's (the tube's superellipse corners keep >= 4 mm clearance)
# (rev r3 fix: n 2.4, da 0.020, db 0.022 about the rounded-rectangle root) -- with the round root (STACK_ROUND) the cut is
# a circle-like ring: ~12 mm above, ~28 mm below the tube
STACK_CUT = dict(n=2.0, da=0.022, db=0.026, dz=-0.012)   # model judging r1 EXT1-01: the photos' dark annulus is
#                                                          larger, deepest below the tube (db 0.020 -> 0.026, dz -0.012)


def _stack_lengths():
    """Arc lengths of the centre line's three pieces: root straight, bend, outlet straight."""
    b = STACK_BEND
    return b["y"] - STACK_ROOT[1], b["r"] * (np.pi / 2 - np.radians(b["az"])), b["out"]


def _stack_centre(sgn=1, n=24, s=None):
    """(n, 3) centre line, uniform in arc length (or at the arc lengths s): straight outboard from STACK_ROOT, an arc
    of STACK_BEND['r'] to the heading STACK_BEND['az'], then straight for STACK_BEND['out']."""
    x0, y0 = STACK_ROOT
    b = STACK_BEND
    r, az = b["r"], np.radians(b["az"])
    L0, La, L1 = _stack_lengths()
    s = np.linspace(0.0, L0 + La + L1, n) if s is None else np.asarray(s, float)
    n = len(s)
    P = np.zeros((n, 3))
    for i, si in enumerate(s):
        if si <= L0:
            P[i, :2] = x0, y0 + si
        elif si <= L0 + La:
            ph = np.pi / 2 - (si - L0) / r                # heading angle from +x
            P[i, :2] = x0 + r - r * np.sin(ph), b["y"] + r * np.cos(ph)
        else:
            e = np.array([x0 + r - r * np.sin(az), b["y"] + r * np.cos(az)])
            P[i, :2] = e + (si - L0 - La) * np.array([np.cos(az), np.sin(az)])
    P[:, 1] *= sgn
    P[:, 2] = AX_Z + np.interp(s, [0.0, L0 + La + L1], STACK_DZ)
    return P


STACK_PTS = tuple(tuple(float(v) for v in (p[0], p[1], p[2] - AX_Z)) for p in
                  _stack_centre(1, s=np.cumsum([0.0, *_stack_lengths()])))


def exhaust_stack_path(sgn=1, n=24):
    """Stack centre line (n, 3) for side sgn (+1 starboard), from inside the cowl side to beyond the outlet plane (the
    tube is cut by STACK_SCARF): straight - bend - straight (_stack_centre), uniform in arc length."""
    return _stack_centre(sgn, n)


def stack_scarf_plane(sgn=1):
    """Outlet (scarf) plane of the stack on side sgn: (point, unit normal) in model axes; the normal points out of
    the tube (aft-outboard).  Signed distance > 0 = cut away."""
    (x0, y0), (x1, y1) = STACK_SCARF
    p = np.array([x0, sgn * y0, AX_Z])
    e = np.array([x1 - x0, sgn * (y1 - y0), 0.0])
    nrm = np.cross(e, [0.0, 0.0, 1.0]) * sgn          # (e_y, -e_x) for starboard: aft-outboard
    return p, nrm / np.linalg.norm(nrm)


def exhaust_stack_rings(sgn=1, n=40, m=28, scarf=False):
    """Section rings (n, m, 3) of the stack tube (stack_section_law: round root -> superellipse STACK_AB / STACK_N,
    normal to the centre line; the vertical semi-axis stays vertical).  Also returns the arc length along the path (n,).  scarf=True cuts the tube
    at the outlet plane STACK_SCARF: every generator line (fixed ring angle) is clipped where it crosses the plane,
    so the rings beyond the cut collapse onto the mouth curve (for silhouettes / the Stage-3 builder)."""
    path = exhaust_stack_path(sgn, n)
    T = np.gradient(path, axis=0)
    T /= np.linalg.norm(T, axis=1)[:, None]
    th = stack_th(m)
    s = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
    rings = []
    for p, t, (a_, b_, n_) in zip(path, T, zip(*stack_section_law(s))):
        n1 = np.cross(t, [0.0, 0.0, 1.0])
        n1 /= np.linalg.norm(n1)
        n2 = np.cross(n1, t)
        u, v, _, _ = stack_section(th, a_, b_, n_)
        rings.append(p + np.outer(u, n1) + np.outer(v, n2))
    rings = np.array(rings)
    if scarf:
        rings = _clip_generators(rings, *stack_scarf_plane(sgn))
    return rings, s


def _clip_generators(rings, p0, nrm):
    """Clip each generator line rings[:, j] at its LAST crossing of the plane (p0, nrm) (the outlet end; the plane,
    extended inboard, also passes ahead of the tube root): the points beyond are replaced by the crossing."""
    R = rings.copy()
    for j in range(R.shape[1]):
        g = R[:, j]
        d = (g - p0) @ nrm
        inside = np.flatnonzero(d <= 0)
        if len(inside) == 0 or inside[-1] == len(d) - 1:
            continue
        i = inside[-1] + 1
        c = g[i - 1] + (g[i] - g[i - 1]) * (d[i - 1] / (d[i - 1] - d[i]))
        R[i:, j] = c
    return R


def exhaust_stack_mouth(sgn=1, m=72, n=200):
    """Closed mouth curve (m + 1, 3) where the tube meets the scarf plane (the outlet opening)."""
    R, _ = exhaust_stack_rings(sgn, n, m, scarf=True)
    P = R[-1]
    return np.vstack([P, P[:1]])


def exhaust_stack_silhouette(sgn=1, view="front", nbin=90, n=160, m=72):
    """Closed outline of the scarfed stack tube in a view: 'front' (BL, WL), 'side' (STA, WL) or 'plan' (STA, BL).
    front / side: upper and lower envelope of all section rings per BL / STA bin; plan: the two horizontal walls
    (ring angles 0 and pi, the ellipse's plan extremes) closed by the root chord and the scarf line."""
    R, _ = exhaust_stack_rings(sgn, n, m, scarf=True)
    if view == "plan":
        a, b = R[:, 0, :2], R[:, m // 2, :2]
        return np.vstack([a, b[::-1], a[:1]])
    k = 1 if view == "front" else 0
    Q = R.reshape(-1, 3)
    u = Q[:, k]
    ub = np.linspace(u.min(), u.max(), nbin + 1)
    idx = np.clip(np.digitize(u, ub) - 1, 0, nbin - 1)
    up, lo, uc = [], [], []
    for i in range(nbin):
        sel = idx == i
        if sel.any():
            uc.append(0.5 * (ub[i] + ub[i + 1]))
            up.append(Q[sel, 2].max())
            lo.append(Q[sel, 2].min())
    uc = np.array(uc)
    uc[0], uc[-1] = u.min(), u.max()
    P = np.r_[np.c_[uc, up], np.c_[uc[::-1], np.array(lo)[::-1]]]
    return np.vstack([P, P[:1]])


def exhaust_stack_collar_points(sgn=1, m=72, n=200, k=8, facing=None):
    """Surface points (N, 3) of the heat-blackened collar band: the last STACK_COLLAR of every generator line of the
    scarfed tube (for silhouettes / hulls in the drawings).  facing = a view direction (towards the viewer, e.g.
    (0, sgn, 0) from outboard, (0, 0, 1) from above) keeps only the generators whose outward normal faces it."""
    if STACK_COLLAR <= 0.0:
        return np.zeros((0, 3))
    R, _ = exhaust_stack_rings(sgn, n, m, scarf=True)
    path = exhaust_stack_path(sgn, n)
    th = stack_th(m)
    out = []
    for j in range(m):
        g = R[:, j]
        sg = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(g, axis=0), axis=1))]
        if facing is not None:
            i = int(np.searchsorted(sg, sg[-1] - 0.5 * STACK_COLLAR))
            i = min(max(i, 1), n - 1)
            t = path[i] - path[i - 1]
            t /= np.linalg.norm(t)
            n1 = np.cross(t, [0.0, 0.0, 1.0])
            n1 /= np.linalg.norm(n1)
            n2 = np.cross(n1, t)
            _, _, nu, nv = stack_section(th[j])
            nrm = nu * n1 + nv * n2
            if float(nrm @ np.asarray(facing, float)) <= 0.0:
                continue
        for s in np.linspace(sg[-1] - STACK_COLLAR, sg[-1], k):
            out.append([np.interp(s, sg, g[:, i]) for i in range(3)])
    return np.array(out)


def exhaust_stack_collar(sgn=1, m=72, n=200):
    """Forward edge (m + 1, 3) of the heat-blackened collar: STACK_COLLAR upstream of the cut along each generator
    (STACK_COLLAR 0: the outer lip of the mouth, where the polished tube ends)."""
    R, _ = exhaust_stack_rings(sgn, n, m, scarf=True)
    out = []
    for j in range(m):
        g = R[:, j]
        sg = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(g, axis=0), axis=1))]
        out.append([np.interp(sg[-1] - STACK_COLLAR, sg, g[:, k]) for k in range(3)])
    out = np.array(out)
    return np.vstack([out, out[:1]])


# Chin inlet (engine + oil-cooler air), Stage 2 rev C (review round 3, R3-3; decision D2: the fitted OML keel owns the
# lip step STA 1.14 -> 1.20).  Front-view outlines fitted to the two loops of the Pilatus drawing's front view (and
# its section EF1, STA 1.200), starboard half (y >= 0, mirrored), (BL, WL):
#   mouth  the dark crescent under the spinner: lower (outer) edge from the bottom centre to the tip, upper edge from
#          the tip back to the centre (WL 1278-1474, BL +/-274); in the side view the mouth lies in the forward-facing
#          step of the keel between CHIN_INLET['x'] (1.14) and 1.20
#   lip    outer edge of the polished lip ring round the mouth and the lower half of the spinner (WL 1222-1685,
#          BL +/-340; its upper ends run into the exhaust-stack roots at WL ~1.6-1.7)
#   side   the polished lip crescent in side projection (x, z): the drawn lip leading-edge line (STA 1118 WL 1510 ->
#          1160 / 1340, onto the keel step) and an aft edge ~50 mm behind it (photo port_hangar_130, rectified); its
#          aft-bottom corner on the keel moved from (1250, 1201) to (1226, 1216), where the keel leaves the front-view
#          lip outline (lowest point WL 1223): the rev C corner lay 22 mm below the drawn front-view lip (Stage 3,
#          CONS2-01).  The polished arms end at the crescent top (WL 1545-1560): the loop's upper ends above it are the
#          painted cheek line into the stack roots (chin_lip_polished_top)
CHIN_INLET = dict(
    x=1.140, x_step=1.200,
    mouth_lower=((0.000, 1.278), (0.070, 1.284), (0.133, 1.305), (0.177, 1.326), (0.207, 1.347), (0.229, 1.364),
                 (0.250, 1.383), (0.265, 1.401), (0.272, 1.414), (0.274, 1.428)),
    mouth_upper=((0.274, 1.428), (0.272, 1.446), (0.264, 1.459), (0.250, 1.470), (0.230, 1.474), (0.210, 1.469),
                 (0.190, 1.456), (0.160, 1.436), (0.130, 1.419), (0.100, 1.406), (0.060, 1.395), (0.000, 1.389)),
    lip=((0.000, 1.223), (0.075, 1.230), (0.128, 1.243), (0.166, 1.258), (0.202, 1.274), (0.247, 1.300),
         (0.281, 1.330), (0.310, 1.363), (0.330, 1.398), (0.339, 1.430), (0.340, 1.456), (0.336, 1.485),
         (0.325, 1.513), (0.305, 1.540), (0.290, 1.565), (0.285, 1.595), (0.288, 1.630), (0.294, 1.685)),
    side=((1.118, 1.545), (1.125, 1.495), (1.140, 1.430), (1.160, 1.345), (1.180, 1.275), (1.200, 1.233),
          (1.226, 1.216), (1.228, 1.290), (1.206, 1.380), (1.188, 1.460), (1.172, 1.530), (1.150, 1.560)),
)


def chin_lip_polished_top():
    """(WL at the lip face, WL at the aft edge) where the polished lip arms end: the side crescent's top edge."""
    S = CHIN_INLET["side"]
    return float(S[0][1]), float(S[-1][1])


def chin_inlet_outline(part):
    """Closed front-view outline (N, 2) (BL, WL) of the chin inlet 'mouth' or 'lip' (the lip ring's outer edge, closed
    across its top ends), both halves; or the closed side-view crescent 'side' (x, z)."""
    if part == "side":
        P = np.array(CHIN_INLET["side"], float)
        return np.vstack([P, P[:1]])
    if part == "mouth":
        H = np.vstack([CHIN_INLET["mouth_lower"], CHIN_INLET["mouth_upper"][1:]])
    else:
        H = np.array(CHIN_INLET["lip"], float)
    H = np.asarray(H, float)
    M = H[::-1] * [-1.0, 1.0]
    P = np.vstack([H, M[1:]]) if part == "mouth" else np.vstack([M, H[1:]])
    return np.vstack([P, P[:1]])

# Stage 3 (CONS2-01 / CONS2-02): the proud lip ring.  The fitted OML carries the keel step (the lip's leading edge at
# BL 0) but not the lip's width: at the step its half-width is <= 0.25 where the drawn ring reaches BL 0.34 and the
# mouth tips BL 0.274 (the drawing's plan view shows the same bulge, a cheek line outside the cowl from STA 1.12 to the
# stack roots).  So the lower-cowl skin is pushed out radially (about the spinner axis at the cowl front, front view)
# to the drawn lip outline behind the drawn lip leading-edge line: chin_cheek_offset().  At each polar angle the skin
# aft of x_le(z_L) (the side-view LE line at the lip's outer WL z_L) is raised to the lip radius over a rounded nose
# CHIN_LIP_NOSE long -- a forward-facing face (in which the mouth is cut) plus the outer lip surface -- and held there
# (the painted cheek) until the OML catches up; it fades out aft (CHIN_CHEEK_AFT) and above the side crescent's top
# (CHIN_CHEEK_TOP: the drawn loop's upper ends are the cheek line into the stack roots, painted -- the polished arms
# end at the crescent top, as on the s/n 3001 / 3008 photos).  The polished lip = the raised skin inside the front-view
# lip outline and the side-view crescent; the mouth = the lip face inside the drawn mouth outline.
CHIN_LIP_NOSE = 0.008          # m (along x): rounded lip nose, from the LE face to the full lip radius
CHIN_CHEEK_AFT = (1.50, 1.70)  # STA range over which the cheek fades into the cowl
CHIN_CHEEK_TOP = (1.52, 1.60)  # lip-outline WL range over which the cheek fades out above the side crescent
CHIN_CHEEK_SOFT = 0.004        # m: soft maximum of the raise (no crease where the OML catches up)
CHIN_MOUTH_DX = 0.004          # m: the mouth is cut in the lip face, x <= x_le(z_L) + nose + this
CHIN_LIP_TOL = 0.006           # m: polished band outside the front-view lip outline (the cheek's soft-max overshoot)
CHIN_NOSE_S = (0.85, 0.89, 0.925, 0.95, 0.97, 0.985, 0.995)   # extra iso-lines of s at the lip nose's top
_CHIN = {}                    # mouth edge loop of the last cut (fuselage_parts.build -> build_inlet_and_exhaust)
_CHIN_POLAR = {}


def _chin_centre_z():
    return float(axis_point(F.STA["cowl_front"])[2])


def chin_lip_polar():
    """(theta, rho) of the drawn lip outline (starboard half) about the spinner axis at the cowl front, front view:
    theta from the downward vertical towards +BL (rad), rho the radius (m); monotone in theta."""
    if not _CHIN_POLAR:
        H = np.array(CHIN_INLET["lip"], float)
        zc = _chin_centre_z()
        th = np.arctan2(H[:, 0], zc - H[:, 1])
        _CHIN_POLAR["lip"] = (th, np.hypot(H[:, 0], zc - H[:, 1]))
    return _CHIN_POLAR["lip"]


# The raised lip / cheek follow the drawn knots through a C1 shape-preserving curve (PCHIP; mirrored about BL 0, so
# the bottom centre is level), not the knots' polyline: linear interpolation creased the cheek along every knot's polar
# angle and the face foot along every LE-line knot, which kinked the studio's reflected streaks on the cowl above the
# inlet and the shading round the lip (review r2 RES2-01).  The curves stay within 2 mm of the polylines the sheets draw.
def _pchip_held(xk, yk):
    from scipy.interpolate import PchipInterpolator
    f = PchipInterpolator(xk, yk, extrapolate=True)
    lo, hi = float(xk[0]), float(xk[-1])
    return lambda x: f(np.clip(np.asarray(x, float), lo, hi))


def chin_lip_rho(th):
    """Radius (m) of the drawn lip outline at front-view polar angle th (rad, |th| used; held beyond the arms' ends):
    the C1 curve through the knots (chin_lip_polar)."""
    if "rho_fn" not in _CHIN_POLAR:
        thL, rL = chin_lip_polar()
        _CHIN_POLAR["rho_fn"] = _pchip_held(np.r_[-thL[:0:-1], thL], np.r_[rL[:0:-1], rL])
    return _CHIN_POLAR["rho_fn"](np.abs(np.asarray(th, float)))


def chin_lip_x(z, edge="fwd"):
    """Station of the drawn side-view lip crescent's forward (LE line) or aft edge at WL z (held beyond its ends): the
    C1 curve through the drawn knots (see chin_lip_rho)."""
    key = "x_" + edge
    if key not in _CHIN_POLAR:
        S = np.array(CHIN_INLET["side"], float)
        E_ = S[:6] if edge == "fwd" else S[6:][::-1]
        o = np.argsort(E_[:, 1])
        _CHIN_POLAR[key] = _pchip_held(E_[o, 1], E_[o, 0])
    return _CHIN_POLAR[key](z)


def chin_cheek_offset(P):
    """Radial raise (m, >= 0, front view about the spinner axis) of cowl-skin points P (N, 3) for the proud lip and
    cheek (see above), and the unit radial directions (N, 3)."""
    P = np.asarray(P, float)
    zc = _chin_centre_z()
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    dz = zc - z
    rho = np.hypot(y, dz)
    th = np.arctan2(np.abs(y), dz)
    thL, rL = chin_lip_polar()
    ok = (th <= thL[-1]) & (x < CHIN_CHEEK_AFT[1] + 0.05)
    rho_L = chin_lip_rho(th)
    zL = zc - rho_L * np.cos(th)
    xf = _chin_face_x(th, zL)
    s = np.clip((x - xf) / CHIN_LIP_NOSE, 0.0, 1.0)
    g = 1.0 - (1.0 - s) ** 2                                         # lip face -> rounded leading edge
    k = CHIN_CHEEK_SOFT
    base = k * np.logaddexp(0.0, (rho_L - rho) / k)
    t = lambda a, r: np.clip((a - r[0]) / (r[1] - r[0]), 0.0, 1.0)  # noqa: E731
    sm = lambda u: u * u * (3.0 - 2.0 * u)                          # noqa: E731
    d = base * g * (1.0 - sm(t(x, CHIN_CHEEK_AFT))) * (1.0 - sm(t(zL, CHIN_CHEEK_TOP)))
    d = np.where(ok & (x > xf), d, 0.0)
    rh = np.maximum(rho, 1e-9)
    u = np.stack([np.zeros_like(x), y / rh, (z - zc) / rh], 1)
    return d, u


CHIN_SHEAR_REF = 1.150         # grid column the lip face / nose is sheared onto (per around-line), see chin_shear_x
CHIN_SHEAR_TAPER = 0.080       # m: the shear tapers to zero over this station distance either side
CHIN_SHEAR_TH = (26.0, 36.0, 84.0, 96.0)   # deg: polar range of the shear (full between the middle two; review r2
#   RES2-01: (.., 72, 84) left the columns oblique to the face's iso-lines at the arms' top, ~17k sub-millimetre
#   triangles there whose quantised normals scrambled -- the 'cowl front ring' bad normals)


def chin_shear_x(xs, ts):
    """Station grid (len(xs), len(ts)) of the cowl skin with its columns sheared round the chin lip: along each
    around-line t the columns at CHIN_SHEAR_REF .. + CHIN_LIP_NOSE move onto the lip face / nose at that polar angle
    (_chin_face_x), tapering off over CHIN_SHEAR_TAPER -- so the steep face lies on whole columns and its leading edge
    does not zig-zag across the fixed stations (the face's station changes by ~80 mm round the arms)."""
    xs = np.asarray(xs, float)
    ts = np.asarray(ts, float)
    zc = _chin_centre_z()
    Q = F.section(np.full_like(ts, CHIN_SHEAR_REF), ts)
    th = np.arctan2(np.abs(Q[:, 1]), zc - Q[:, 2])
    thL, rL = chin_lip_polar()
    zL = zc - chin_lip_rho(th) * np.cos(th)
    a0, a1, a2, a3 = np.radians(CHIN_SHEAR_TH)
    sm = lambda u: np.clip(u, 0, 1) ** 2 * (3.0 - 2.0 * np.clip(u, 0, 1))          # noqa: E731
    w = sm((th - a0) / (a1 - a0)) * (1.0 - sm((th - a2) / (a3 - a2)))
    d = (_chin_face_x(th, zL) - CHIN_SHEAR_REF) * w
    lo, hi = CHIN_SHEAR_REF - 0.004, CHIN_SHEAR_REF + CHIN_LIP_NOSE + 0.004
    B = np.where(xs < lo, 1.0 - sm((lo - xs) / CHIN_SHEAR_TAPER), np.where(xs > hi, 1.0 - sm((xs - hi) / CHIN_SHEAR_TAPER),
                                                                         1.0))
    return xs[:, None] + B[:, None] * d[None, :]


def cowl_section(x, t):
    """Point(s) of the built cowl skin: the OML section (fuselage.section) with the chin lip / cheek raise applied."""
    return chin_cheek_displace(F.section(x, t))


def cowl_project(V, UV, iters=10, h=2e-4, k=2e-4):
    """Closest points of the raised cowl skin S(X, t) = cowl_section to the points V (n, 3), by Gauss-Newton from their
    surface parameters UV (n, 2) = (station, around-line t): (distance (n,), unit normals (n, 3) at the closest points,
    unoriented, the closest points (n, 3)).  Trimmed / split / refined vertices carry UV interpolated linearly, which on
    the steep chin-lip face can lie centimetres up the face from the vertex, hence the projection."""
    V = np.asarray(V, float)
    x0 = F.STA["cowl_front"]
    S = lambda X, T: cowl_section(np.maximum(X, x0), T % 1.0)          # noqa: E731
    X, T = np.array(UV[:, 0], float), np.array(UV[:, 1], float)
    for _ in range(iters):
        Xa = np.maximum(X - h, x0)
        Xb = Xa + 2 * h
        P = S(X, T)
        SX = (S(Xb, T) - S(Xa, T)) / (Xb - Xa)[:, None]
        ST = (S(X, T + k) - S(X, T - k)) / (2 * k)
        r = V - P
        a, b, c = (SX * SX).sum(1), (SX * ST).sum(1), (ST * ST).sum(1)
        p, q = (SX * r).sum(1), (ST * r).sum(1)
        det = np.maximum(a * c - b * b, 1e-30)
        X = np.maximum(X + np.clip((c * p - b * q) / det, -0.004, 0.004), x0)
        T = T + np.clip((a * q - b * p) / det, -0.004, 0.004)
    Xa = np.maximum(X - h, x0)
    Xb = Xa + 2 * h
    N = np.cross(S(Xb, T) - S(Xa, T), S(X, T + k) - S(X, T - k))
    N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-30)
    P = S(X, T)
    return np.linalg.norm(P - V, axis=1), N, P


CHIN_SNAP = dict(x_max=1.40, z_max=1.62, d_min=0.2e-3, d_max=8e-3)   # cut_chin_inlet's snap of chord vertices


def _snap_to_skin(meshes, keep):
    """Move the vertices of the cut lip / cowl (UV ahead of CHIN_SNAP x_max, below z_max) that lie d_min .. d_max off
    the raised skin onto it (cowl_project), except the mouth loop `keep` (the duct entry is built on it) and the face /
    nose: the trim cuts put their vertices on chords -- on the lip outline where it crosses the cheek's soft maximum up
    to ~5 mm inside it (review r2 RES2-01; the L1 skin-on-OML row).  The same position and UV give the same point, so
    the boundaries the meshes share stay closed."""
    kset = set(map(tuple, np.round(np.asarray(keep, float), 9))) if keep is not None else set()
    c = CHIN_SNAP
    for m in meshes:
        if m.UV is None or not len(m.V):
            continue
        sel = np.nonzero((m.UV[:, 0] < c["x_max"]) & (m.V[:, 2] < c["z_max"]))[0]
        if kset:
            sel = sel[[tuple(v) not in kset for v in np.round(m.V[sel], 9)]]
        if not len(sel):
            continue
        d, _, P = cowl_project(m.V[sel], m.UV[sel])
        sv = chin_face_s(m.V[sel])
        # not on the face / nose (s -0.2 .. 1.2): moved onto the ~1 mm nose radius, its iso-line rows folded over
        ok = (d > c["d_min"]) & (d < c["d_max"]) & ((sv < -0.2) | (sv > 1.2))
        m.V[sel[ok]] = P[ok]


def _oml_ray_radius(x, th, zc, lo=0.05, hi=0.9, iters=34):
    """Radius along the front-view ray at polar angle th (from the downward vertical, +BL) from (BL 0, WL zc) where it
    meets the OML section at station x (bisection on the section law)."""
    x, th = np.broadcast_arrays(np.asarray(x, float), np.asarray(th, float))
    a, b = np.full(x.shape, lo), np.full(x.shape, hi)
    s_, c_ = np.sin(th), np.cos(th)
    for _ in range(iters):
        m = 0.5 * (a + b)
        d = F._OML.section_distance(F.clip_x(x), m * s_, zc - m * c_)
        a, b = np.where(d < 0, m, a), np.where(d < 0, b, m)
    return 0.5 * (a + b)


def chin_raised_dist(P, half=0.03, n=61):
    """Distance (m) of points P (N, 3) from the built (raised) cowl skin, measured in the point's front-view polar
    half-plane (station, radius) against the raised profile over +/-half of its station (robust on the steep lip face)."""
    P = np.asarray(P, float)
    zc = _chin_centre_z()
    rho = np.hypot(P[:, 1], zc - P[:, 2])
    th = np.arctan2(np.abs(P[:, 1]), zc - P[:, 2])
    dx = np.linspace(-half, half, n)
    X = P[:, 0][:, None] + dx[None, :]
    TH = np.broadcast_to(th[:, None], X.shape)
    R0 = _oml_ray_radius(X, TH, zc)
    Q = np.stack([X, R0 * np.sin(TH), zc - R0 * np.cos(TH)], -1).reshape(-1, 3)
    d, _ = chin_cheek_offset(Q)
    R = R0 + d.reshape(X.shape)
    # distance to the (station, radius) polyline through the samples (the lip face is nearly radial: point samples
    # 1 mm apart are up to 40 mm apart in radius there)
    ax_, ar = dx[None, :-1], R[:, :-1]
    bx_, br = dx[None, 1:], R[:, 1:]
    px, pr = 0.0, rho[:, None]
    ex, er = bx_ - ax_, br - ar
    u = np.clip(((px - ax_) * ex + (pr - ar) * er) / np.maximum(ex * ex + er * er, 1e-18), 0.0, 1.0)
    dist = np.sqrt((ax_ + u * ex - px) ** 2 + (ar + u * er - pr) ** 2).min(1)
    return dist * np.sign(rho - R[:, n // 2])


def chin_cheek_displace(P):
    """Cowl-skin grid points (..., 3) with the proud lip / cheek raise applied (chin_cheek_offset)."""
    Q = np.asarray(P, float).reshape(-1, 3)
    d, u = chin_cheek_offset(Q)
    return (Q + d[:, None] * u).reshape(np.shape(P))


def chin_fields(V):
    """(mouth, lip, side) signed distances (m, negative inside) of points V: front-view mouth / lip outlines (y, z)
    and the side-view lip crescent (x, z) of CHIN_INLET."""
    from cad import sdf2d

    def poly(name):
        P = chin_inlet_outline(name)[:-1]
        keep = np.linalg.norm(P - np.roll(P, 1, 0), axis=1) > 1e-9       # drop repeated points (closing seam)
        return P[keep]
    fm = sdf2d.polygon(V[:, 1], V[:, 2], poly("mouth"))
    fl = sdf2d.polygon(V[:, 1], V[:, 2], poly("lip"))
    fs = sdf2d.polygon(V[:, 0], V[:, 2], poly("side"))
    return fm, fl, fs


CHIN_ARM_TH = (20.0, 35.0)      # deg: over this polar range the lip face moves from the OML keel step (bottom, the
#                                 face's foot on the drawn LE line) to one nose length ahead of it (arms: the lip's
#                                 outermost point -- its side-view leading edge -- on the drawn LE line)


def _chin_face_x(th, zL):
    """Station of the lip face's foot at polar angle th (rad) for the lip's outer WL zL."""
    a0, a1 = np.radians(CHIN_ARM_TH)
    w = np.clip((np.abs(th) - a0) / (a1 - a0), 0.0, 1.0)
    w = w * w * (3.0 - 2.0 * w)
    return chin_lip_x(zL, "fwd") - w * CHIN_LIP_NOSE


def chin_face_s(V):
    """Lip-face parameter of (raised) cowl-skin points: 0 at the face's foot on the cowl (x = x_le(z_L)) -> 1 at the full
    lip radius (CHIN_LIP_NOSE aft); the raise is radial, so x and the polar angle are those of the OML point."""
    V = np.asarray(V, float)
    zc = _chin_centre_z()
    th = np.arctan2(np.abs(V[:, 1]), zc - V[:, 2])
    thL, rL = chin_lip_polar()
    zL = zc - chin_lip_rho(th) * np.cos(th)
    return (V[:, 0] - _chin_face_x(th, zL)) / CHIN_LIP_NOSE


def _weld(m, tol=1e-9):
    """Merge coincident vertices (exact duplicates from split trims)."""
    key = np.round(m.V / tol).astype(np.int64)
    _, idx, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.reshape(-1)
    F_ = inv[m.F]
    F_ = F_[(F_[:, 0] != F_[:, 1]) & (F_[:, 1] != F_[:, 2]) & (F_[:, 0] != F_[:, 2])]
    return Mesh(m.V[idx], F_, None if m.N is None else m.N[idx], None if m.UV is None else m.UV[idx])


def _split_levels(m, f, levels, eps=0.02):
    """Insert the iso-lines f = level into mesh m (split trims, re-welded): refines the lip face radially so the mouth
    cut follows the drawn outline (the face stands almost normal to the skin columns)."""
    for c in levels:
        v = f(m.V) - c
        v = np.where(np.abs(v) < eps, np.where(v < 0, -eps, eps), v)   # no cut within ~eps of a vertex (slivers)
        if (v < 0).any() and (v > 0).any():
            m = _weld(Mesh.merge([trim(m, v, "positive"), trim(m, v, "negative")]))
    return m


def chin_mouth_field(V):
    """Mouth hole field (negative = hole) on the raised lower cowl: inside the drawn front-view mouth outline and on the
    lip face / keel step (x <= x_le(z_L) + CHIN_LIP_NOSE + CHIN_MOUTH_DX at the point's polar angle)."""
    V = np.asarray(V, float)
    zc = _chin_centre_z()
    th = np.arctan2(np.abs(V[:, 1]), zc - V[:, 2])
    thL, rL = chin_lip_polar()
    zL = zc - chin_lip_rho(th) * np.cos(th)
    xf = _chin_face_x(th, zL) + CHIN_LIP_NOSE + CHIN_MOUTH_DX
    return np.maximum(chin_fields(V)[0], V[:, 0] - xf)


def _chin_side_lip(V):
    """Side-crescent field for the polished-lip classification: the crescent with its forward (LE) edge moved
    CHIN_LIP_TOL ahead -- the keel step (fitted to that very line) lies on it and fell either side (a painted island
    in the lower lip)."""
    from cad import sdf2d
    S = np.array(CHIN_INLET["side"], float)
    S[:6, 0] -= CHIN_LIP_TOL
    return sdf2d.polygon(np.asarray(V)[:, 0], np.asarray(V)[:, 2], S)


def cut_chin_inlet(m):
    """Cut the chin inlet into the lower cowling (decision D2: the OML keel owns the lip step STA 1.14 -> 1.20; the
    skin is raised to the drawn lip, chin_cheek_offset): returns (cowl without mouth and lip, polished lip ring).  The
    mouth = the lip face inside the drawn front-view mouth outline; the lip = the skin inside both the front-view lip
    outline and the side-view lip crescent."""
    from cad.mesh import boundary_loops
    zc = _chin_centre_z()
    def face(V):                        # the raise fraction g on the lip face (uniform radial steps)
        sv = np.clip(chin_face_s(V), -0.5, 1.5)
        g = np.where(sv < 0, sv, np.where(sv > 1, sv, 1.0 - (1.0 - np.clip(sv, 0, 1)) ** 2))
        return np.where(np.arctan2(np.abs(V[:, 1]), zc - V[:, 2]) < chin_lip_polar()[0][-1], g, -1.0)
    m = _split_levels(m, face, np.arange(0.04, 0.99, 0.04), eps=0.008)
    # ... and iso-lines of s itself near the nose top: the levels uniform in g end at s = 0.8, where the face's normal
    # still leans ~55 deg forward of the lip's (the raise g = 1 - (1 - s)^2 rolls over within the last millimetre of
    # station, a ~1 mm radius); the remaining turn lay across one row of large triangles whose corners zig-zag
    # between s 0.8 and 1.25, which drew a sawtooth light / dark line along the lip (review r2 RES2-01)
    def face_s(V):
        sv = np.clip(chin_face_s(V), -0.5, 1.5)
        return np.where(np.arctan2(np.abs(V[:, 1]), zc - V[:, 2]) < chin_lip_polar()[0][-1], sv, -1.0)
    m = _split_levels(m, face_s, CHIN_NOSE_S, eps=0.004)
    fm = lambda mm: chin_mouth_field(mm.V)                                              # noqa: E731
    m1 = trim(m, fm(m), "positive")
    best = None
    for lp in boundary_loops(m1):
        P = m1.V[lp]
        if P[:, 0].mean() > 1.3:
            continue
        e = np.abs(chin_fields(P)[0]).mean()
        if best is None or e < best[0]:
            best = (e, P)
    _CHIN["mouth"] = best[1] if best is not None else None
    # the raised cheek sits CHIN_CHEEK_SOFT ln2 (~3 mm) outside the drawn lip outline: polished up to the crescent's aft
    # edge (a CHIN_LIP_TOL band outside the front-view outline counts as the lip)
    # two single-sided trims, not one max() field (review r3 RES3-02: at the lip's top outboard corners, where the
    # front-view outline meets the side-view crescent, the max() field's crease zig-zagged the cut across the sheared
    # columns -- a sawtooth lip / cheek edge and a jagged highlight beside it)
    # (both pieces of the first cut take the second, so its crossings with the first are inserted on both sides of
    # that seam: no T-junctions)
    f_front = lambda mm: chin_fields(mm.V)[1] - CHIN_LIP_TOL                               # noqa: E731
    pieces = []
    for keep in ("negative", "positive"):
        q = trim(m1, f_front(m1), keep)
        fs = _chin_side_lip(q.V)
        pieces.append((trim(q, fs, "negative"), trim(q, fs, "positive")))
    lip = pieces[0][0]
    rest = Mesh.merge([m_ for m_ in (pieces[0][1], pieces[1][0], pieces[1][1]) if m_.nf])
    rest, lip = _refine_cheek_corners([rest, lip])
    _snap_to_skin([lip, rest], _CHIN["mouth"])
    return rest, lip


# review r3 RES3-02: over the cheek beside the lip's top outboard corners the sheared columns (CHIN_SHEAR_TH taper)
# leave fans of long slivers; their analytic vertex normals, interpolated linearly along edges up to a few cm long,
# drew the studio's streak there as a zig-zag.  The cowl's and the lip's edges longer than 2 x CHIN_CORNER_EDGE in
# CHIN_CORNER_BOX (off the lip face / nose, which the snap leaves alone) are split CHIN_CORNER_PASSES times, both
# meshes in one call (their seam split alike; open boundaries -- the mouth the duct is built on -- kept), before the
# snap, which puts the new vertices on the skin; they get the analytic normal with the rest
CHIN_CORNER_BOX = dict(x=(1.10, 1.30), z=(1.47, 1.64), ay=(0.16, 0.38))
CHIN_CORNER_EDGE = 0.0015
CHIN_CORNER_PASSES = 2


def _refine_cheek_corners(meshes):
    from cad.refine import refine
    b = CHIN_CORNER_BOX

    def field(V):
        sv = chin_face_s(V)
        inside = ((V[:, 0] > b["x"][0]) & (V[:, 0] < b["x"][1]) & (V[:, 2] > b["z"][0]) & (V[:, 2] < b["z"][1])
                  & (np.abs(V[:, 1]) > b["ay"][0]) & (np.abs(V[:, 1]) < b["ay"][1]) & ((sv < -0.2) | (sv > 1.2)))
        return np.where(inside, CHIN_CORNER_EDGE, 1.0)[:, None]
    return refine(list(meshes), levels=0, field=field, field_levels=CHIN_CORNER_PASSES, field_near=0.5, min_len=0.0015,
                  keep_boundary=True)


# duct stations aft of the mouth: (STA, centre WL, half-width, half-height); a flattened duct under the engine that
# rises into the plenum round the rear inlet screen
CHIN_DUCT = ((1.30, 1.335, 0.215, 0.085), (1.50, 1.305, 0.205, 0.075), (1.80, 1.295, 0.200, 0.072),
             (2.10, 1.310, 0.200, 0.075), (2.35, 1.380, 0.200, 0.090), (2.52, 1.450, 0.200, 0.100))


def _mouth_samples(mouth, ph):
    """Points of the mouth edge loop at the duct angles ph (front view: -pi/2 = bottom centre, 0 = starboard tip,
    pi/2 = top centre, pi = port tip).  The mouth is a crescent, not star-shaped about any point, so it is split at its
    four key points (the two BL-0 crossings and the two tips) and each quarter is resampled by arc length."""
    P = np.asarray(mouth, float)
    if np.linalg.norm(P[0] - P[-1]) < 1e-9:
        P = P[:-1]
    y, z = P[:, 1], P[:, 2]
    if 0.5 * np.sum(y * np.roll(z, -1) - np.roll(y, -1) * z) < 0:        # counter-clockwise seen from ahead (y right)
        P = P[::-1]
        y, z = P[:, 1], P[:, 2]
    cross = np.nonzero(np.sign(y) != np.sign(np.roll(y, -1)))[0]
    zc = np.array([z[i] for i in cross])
    ib = int(cross[np.argmin(zc)])                                        # bottom centre
    P = np.roll(P, -ib, axis=0)
    y, z = P[:, 1], P[:, 2]
    cross = np.nonzero(np.sign(y) != np.sign(np.roll(y, -1)))[0]
    it = int(cross[np.argmax(z[cross])])                                   # top centre
    ir = int(np.argmax(np.where(np.arange(len(P)) < it, y, -np.inf)))       # starboard tip (bottom -> top)
    il = int(np.argmin(np.where(np.arange(len(P)) > it, y, np.inf)))        # port tip (top -> bottom)
    Q = np.vstack([P, P[:1]])
    keys = [0, ir, it, il, len(P)]
    out = np.empty((len(ph), 3))
    q = np.clip(np.floor((ph + np.pi / 2) / (np.pi / 2)).astype(int), 0, 3)
    f = (ph + np.pi / 2) / (np.pi / 2) - q
    for k in range(4):
        seg = Q[keys[k]:keys[k + 1] + 1]
        s = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(seg, axis=0), axis=1))]
        sel = q == k
        for j in range(3):
            out[sel, j] = np.interp(f[sel] * s[-1], s, seg[:, j])
    return out


def chin_duct(mouth, m=96):
    """Rings (k, m, 3): the mouth edge loop (resampled quarter by quarter, _mouth_samples) blending into the
    CHIN_DUCT ellipses (the first station half-way, the others fully)."""
    ph = np.linspace(-np.pi / 2, 1.5 * np.pi, m, endpoint=False)
    M = _mouth_samples(mouth, ph)
    rings = [M]
    for k, (x, zc, a, b) in enumerate(CHIN_DUCT):
        w = 0.6 if k == 0 else 1.0
        ey, ez = a * np.cos(ph), zc + b * np.sin(ph)
        rings.append(np.c_[np.full(m, x), (1 - w) * M[:, 1] + w * ey, (1 - w) * M[:, 2] + w * ez])
    return np.array(rings)


def _densify_rings(rings, upto):
    """rings[:upto + 1] with rings inserted between them at PC12_RES > 1 (cad.res.factor: 3 per gap at RES 2), on the
    natural cubic spline through every ring (by the rings' mean spacing), the given rings kept exactly: the duct entry
    behind the mouth had three rings over a turn from the vertical crescent into the flat duct (review r1 RES1-04)."""
    from cad import res
    from scipy.interpolate import CubicSpline
    k = int(round(1.5 * res.factor())) if res.on() else 1
    R = np.asarray(rings, float)
    if k <= 1:
        return R[:upto + 1]
    s = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(R, axis=0), axis=2).mean(1))]
    cs = CubicSpline(s, R, axis=0, bc_type="natural")
    ss = np.concatenate([np.linspace(s[i], s[i + 1], k + 1)[:-1] for i in range(upto)] + [[s[upto]]])
    out = cs(ss)
    out[::k] = R[:upto + 1]
    return out


def _stack_normals(sgn, n, m):
    """Analytic outward normals (n, m, 3) of the elliptic stack section rings (exhaust_stack_rings frames): the
    polished stack mirrors the room, so the vertex normals must be smooth (VQA r1 R1-07: the mesh-derived normals
    of the scarf-clipped grid gave wavy, 'crumpled foil' highlights)."""
    path = exhaust_stack_path(sgn, n)
    T = np.gradient(path, axis=0)
    T /= np.linalg.norm(T, axis=1)[:, None]
    th = stack_th(m)
    s = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
    N = []
    for t, (a_, b_, n_) in zip(T, zip(*stack_section_law(s))):
        n1 = np.cross(t, [0.0, 0.0, 1.0])
        n1 /= np.linalg.norm(n1)
        n2 = np.cross(n1, t)
        _, _, nu, nv = stack_section(th, a_, b_, n_)
        v = np.outer(nu, n1) + np.outer(nv, n2)
        N.append(v / np.linalg.norm(v, axis=1)[:, None])
    return np.array(N)


STACK_INNER_POLISH = 0.003      # the inside of the outlet is polished this far in from the scarf cut (photo 188: the
#                                  far inner wall mirrors the apron through the opening), soot deeper in (VQA r3: 0.05
#                                  -> 0.02, photos 130 / 3001 show the mouth black to the lip; model judging r1 EXT1-01:
#                                  0.02 -> 0.003, the polished ring inside the rim still read as a lit oval mouth)


def exhaust_stack_mesh(sgn, n=96, m=72, wall=0.006):
    """Scarfed stack (outer skin, inner wall, lip at the scarf plane); returns (tube, collar, inner soot, inner polish)."""
    R, _ = exhaust_stack_rings(sgn, n, m, scarf=True)
    path = exhaust_stack_path(sgn, n)
    cen = path[:, None, :]

    def to_end(Q):                   # arc length of every generator from its scarf end
        seg = np.linalg.norm(np.diff(Q, axis=0), axis=2)
        s = np.vstack([np.zeros((1, m)), np.cumsum(seg, 0)])
        d = s[-1][None, :] - s
        return np.stack([d, np.zeros_like(d)], -1)

    Nout = _stack_normals(sgn, n, m)
    outer = grid_surface(R, close_v=True, UV=to_end(R), N=Nout)
    if np.mean(np.sum((outer.V[:m] - path[0]) * outer.N[:m], 1)) < 0:
        outer = outer.flipped()
    Ri = cen + (R - cen) * (1 - wall / min(STACK_AB))
    Ri = _clip_generators(Ri, *stack_scarf_plane(sgn))
    inner = grid_surface(Ri, close_v=True, UV=to_end(Ri), N=-Nout)        # smooth analytic normals (polished lip)
    C = inner.V[inner.F].mean(1)                                             # wound to face the axis
    near = path[np.argmin(np.linalg.norm(C[:, None, :] - path[None, :, :], axis=2), 1)]
    if np.mean(np.sum((C - near) * inner.face_normals(), 1)) > 0:
        inner.F = inner.F[:, ::-1].copy()
    V = np.vstack([R[-1], Ri[-1]])
    k = np.arange(m)
    lip = Mesh(V, np.vstack([np.stack([k, (k + 1) % m, (k + 1) % m + m], 1), np.stack([k, (k + 1) % m + m, k + m], 1)]))
    if np.dot(lip.face_normals().mean(0), stack_scarf_plane(sgn)[1]) < 0:
        lip = lip.flipped()
    if STACK_COLLAR > 0.0:
        collar = trim(outer, outer.UV[:, 0] - STACK_COLLAR, "negative")
        tube = trim(outer, outer.UV[:, 0] - STACK_COLLAR, "positive")
    else:                            # polished to the lip (VQA r3): the soot is inside only
        collar, tube = Mesh(np.zeros((0, 3)), np.zeros((0, 3), int)), outer
    polish = trim(inner, inner.UV[:, 0] - STACK_INNER_POLISH, "negative")
    soot = trim(inner, inner.UV[:, 0] - STACK_INNER_POLISH, "positive")
    return tube, Mesh.merge([collar, lip]), soot, polish


def _stack_root_frame():
    """(x0, zc, a, b, n) of the tube's straight root piece, which runs square to the cowl side (along +-y): the round
    root section (stack_section_law)."""
    s0 = STACK_BEND["y"] - STACK_ROOT[1]
    zc = AX_Z + STACK_DZ[0] + (STACK_DZ[1] - STACK_DZ[0]) * s0 / sum(_stack_lengths())
    a, b, n = (float(v) for v in stack_section_law(s0))
    return STACK_ROOT[0], zc, a, b, n


def stack_cut_outline():
    """(x0, zc, A, B, n) of the elliptic cut-out round the stack root (STACK_CUT about the root piece's section)."""
    x0, zc, a, b, _ = _stack_root_frame()
    q = STACK_CUT
    return x0, zc + q["dz"], a + q["da"], b + q["db"], q["n"]


def stack_root_field(V):
    """Dark annular cut-out round each stack root in the cowl skin (negative = hole): the superellipse STACK_CUT round
    the tube's section, projected along the root piece (square to the cowl side, so it is the exact footprint)."""
    V = np.asarray(V, float)
    x0, zc, A, B, n = stack_cut_outline()
    rho = (np.abs((V[:, 0] - x0) / A) ** n + np.abs((V[:, 2] - zc) / B) ** n) ** (1.0 / n)
    f = (rho - 1.0) * min(A, B)
    return np.where(np.abs(V[:, 1]) > 0.15, f, 1.0)


def stack_root_liner(sgn, m=96):
    """The cut-out's dark liner: a wall from the cowl skin (the hole edge) STACK_GAP_DEPTH into the cowl and a bottom
    ring closing the gap to the tube."""
    x0, zc, a, b, n0 = _stack_root_frame()
    _, zo_c, A, B, n = stack_cut_outline()
    th = stack_th(m)
    uo, vo, _, _ = stack_section(th, A, B, n)
    ui, vi, _, _ = stack_section(th, a, b, n0)
    xo, zo = x0 + uo, zo_c + vo
    ys = np.array([float(F.side_y(x, z)) for x, z in zip(xo, zo)]) + 0.0005
    rows = [np.c_[xo, sgn * (ys - d), zo] for d in np.linspace(0.0, STACK_GAP_DEPTH, 4)]
    wall = grid_surface(np.array(rows), close_v=True)
    c = np.array([x0, sgn * float(ys.mean()), zc])
    if np.mean(np.sum((c - wall.V) * wall.N * [1, 0, 1], 1)) < 0:          # the wall faces the tube
        wall = wall.flipped()
    yb = ys - STACK_GAP_DEPTH
    ring = np.array([np.c_[xo, sgn * yb, zo], np.c_[x0 + ui, sgn * yb, zc + vi]])
    bot = grid_surface(ring, close_v=True)
    if np.mean(bot.N[:, 1]) * sgn < 0:                                      # the bottom faces outboard
        bot = bot.flipped()
    return Mesh.merge([wall, bot])


CHIN_MOUTH_SKIRT = 0.008      # m: the dark strip from the exact mouth edge aft into the duct (RES3-02)


def chin_mouth_skirt(mouth, entry):
    """A dark strip from the mouth edge loop -- the lip's own boundary vertices -- CHIN_MOUTH_SKIRT aft into the duct
    entry.  The entry's first ring resamples that loop (96 points by arc length, chin_duct), so between the two hairline
    gaps (up to ~0.7 mm) showed the dark cowl interior as specks along the lip's inner edge (review r3 RES3-02); the
    strip shares the loop with the lip and lies over the entry, facing the way it does."""
    P = np.asarray(mouth, float)
    if np.linalg.norm(P[0] - P[-1]) < 1e-12:
        P = P[:-1]
    sk = grid_surface(np.stack([P, P + np.array([CHIN_MOUTH_SKIRT, 0.0, 0.0])]), close_v=True)
    c = P.mean(0)
    side = lambda m_: float(np.mean(np.sum((m_.V - c)[:, 1:] * m_.N[:, 1:], 1)))       # noqa: E731
    return sk.flipped() if side(sk) * side(entry) < 0 else sk


def build_inlet_and_exhaust(parts):
    # chin inlet (D2): the lip was cut from the lower cowling (cut_chin_inlet); the duct lofts from that mouth edge
    mouth = _CHIN.get("mouth")
    if mouth is None:
        raise RuntimeError("chin inlet: the lower cowling was not cut (fuselage_parts.build must run first)")
    rings = chin_duct(mouth)
    entry = grid_surface(_densify_rings(rings, 2), close_v=True)     # mouth -> STA 1.50 (seen through the mouth)
    duct = grid_surface(rings[2:], close_v=True)
    back = cap_ring(rings[-1], (1, 0, 0))
    p = parts.get("chin_inlet") or Part("chin_inlet", "Chin air inlet", "cowling", explode=(-0.4, 0, -0.75),
                                        group="Powerplant installation")
    p.add(entry, "inlet_dark").add(chin_mouth_skirt(mouth, entry), "inlet_dark")
    parts[p.id] = p
    dp = Part("inlet_duct", "Inlet duct + inertial separator (to the plenum)", "powerplant", explode=(0, 0, -0.9),
              group="Powerplant installation", material_note="Composite duct, ice-vane separator")
    dp.add(Mesh.merge([duct, back]), "composite")
    parts[dp.id] = dp

    # exhaust stacks: tube along STACK_PTS / STACK_AB, cut by the scarf plane STACK_SCARF, heat-blackened collar
    # (inside polished near the outlet); the dark annular cut-out round each root is the cowl's (stack_root_field /
    # stack_root_liner, added to the cowl halves by fuselage_parts)
    tubes, collars, inners = [], [], []
    for sgn in (1, -1):
        t, c, i, pol = exhaust_stack_mesh(sgn)
        tubes += [t, pol]
        collars.append(c)
        inners.append(i)
    ep = Part("exhaust_stacks", "Exhaust stacks (L/R), scarfed outlets", "cowling", explode=(-0.2, 0, 0.0), qty=2,
              group="Powerplant installation", material_note="Inconel stacks, heat-tinted outlet collars")
    ep.add(Mesh.merge(tubes), "exhaust").add(Mesh.merge(collars + inners), "exhaust_soot")
    parts[ep.id] = ep


# ---------------------------------------------------------------------------
# propeller
# ---------------------------------------------------------------------------

# Blade root (VQA r1 SHP-01 / R1-02 / LIV-06): the Hartzell composite blade passes through the spinner on a ROUND
# shank (radius BLADE_SHANK_R about the pitch-change axis, so the fit is the same at any pitch) that flares into the
# airfoil outside the spinner (BLADE_SHANK_BLEND: radii along the pitch axis where the blend starts / ends); a black
# rubber boot (BLADE_BOOT) round each shank closes the spinner cut-out (photos 81 / 130: round black cuffs in tight
# round cut-outs, no open holes).
BLADE_SHANK_R = 0.047            # VQA r2 SHP2-04: photo 130 / 188 shanks are slim (~0.09-0.10 m across; rev 0.055)
BLADE_SHANK_BLEND = (0.272, 0.360)


def blade_geometry(n_r=34, n_c=40):
    """One blade along +z (radial), pitch axis = z axis through the hub centre,
    chord in the x-y plane at blade angle beta (0 = chord in the rotation plane).  Inboard of BLADE_SHANK_BLEND[0]
    the section is the round shank (radius BLADE_SHANK_R about the pitch axis); it blends into the airfoil by
    BLADE_SHANK_BLEND[1]."""
    b0, b1 = BLADE_SHANK_BLEND
    rs = np.concatenate([np.linspace(0.155, b0, 5), np.linspace(b0, b1, 7)[1:], np.linspace(b1, PROP_R - 0.03,
                         n_r - 10)[1:], PROP_R - np.array([0.02, 0.01, 0.004])])
    r_rel = rs / PROP_R
    # chord distribution (paddle blade, rounded tip)
    c = np.interp(r_rel, [0.116, 0.16, 0.22, 0.35, 0.55, 0.75, 0.90, 0.97, 1.0],
                  [0.085, 0.10, 0.155, 0.200, 0.214, 0.196, 0.160, 0.118, 0.05])
    tc = np.interp(r_rel, [0.116, 0.16, 0.25, 0.40, 1.0], [0.95, 0.60, 0.22, 0.13, 0.065])
    P = 2.9  # geometric pitch at flight fine (m)
    beta = np.arctan2(P, 2 * np.pi * np.maximum(rs, 0.25))
    sweep = 0.06 * np.clip((r_rel - 0.6) / 0.4, 0, 1) ** 2   # scimitar tip, positive toward trailing edge
    xc = cos_pts(n_c)
    rows = []
    for r, ch, t, b, sw in zip(rs, c, tc, beta, sweep):
        cam = 0.02 * np.clip((0.95 - t) / 0.8, 0, 1)
        yt = naca4_thickness(xc, t, closed_te=True)
        zc_ = np.where(xc < 0.4, cam / 0.16 * (0.8 * xc - xc ** 2), cam / 0.36 * (0.2 + 0.8 * xc - xc ** 2))
        lower = np.stack([xc[::-1], (zc_ - yt)[::-1]], 1)
        upper = np.stack([xc[1:-1], (zc_ + yt)[1:-1]], 1)
        loop = np.vstack([lower, upper])
        # section in local (chord u, thickness v); pitch axis at 35 % chord
        u = (loop[:, 0] - 0.35 + sw / max(ch, 1e-3)) * ch
        v = loop[:, 1] * ch
        # round shank inboard: the same loop parameter on a circle about the pitch axis (lower surface TE -> LE on
        # v < 0, upper LE -> TE on v > 0), blended in over BLADE_SHANK_BLEND (smoothstep)
        wb = float(np.clip((r - b0) / (b1 - b0), 0.0, 1.0))
        wb = wb * wb * (3.0 - 2.0 * wb)
        if wb < 1.0:
            ph = np.arccos(np.clip(2.0 * loop[:, 0] - 1.0, -1.0, 1.0)) * np.r_[-np.ones(len(lower)), np.ones(len(upper))]
            uc, vc = BLADE_SHANK_R * np.cos(ph), BLADE_SHANK_R * np.sin(ph)
            u = wb * u + (1.0 - wb) * uc
            v = wb * v + (1.0 - wb) * vc
        # rotate by blade angle: chord makes angle beta with the rotation plane.
        # rotation plane directions: tangential = +y, axial = -x (forward)
        tang = np.array([0, 1.0, 0])
        axial = np.array([-1.0, 0, 0])
        # chord LE->TE and thickness (suction side, forward at flat pitch)
        e_u = np.array([np.sin(b), -np.cos(b), 0.0])
        e_v = np.array([-np.cos(b), -np.sin(b), 0.0])
        pts = np.array([0, 0, r]) + u[:, None] * e_u + v[:, None] * e_v
        rows.append(pts)
    Pm = np.array(rows)
    m = grid_surface(Pm, close_v=True)
    cen = Pm.mean(1)
    rad = (Pm - cen[:, None, :]).reshape(-1, 3)
    if np.mean(np.sum(rad * m.N, 1)) < 0:
        m = m.flipped()
    tip = cap_ring(Pm[-1], (0, 0, 1))
    root = cap_ring(Pm[0], (0, 0, -1))
    return Mesh.merge([m, tip, root]), rs, Pm


BLADE_HOLE_R = BLADE_SHANK_R + 0.006   # blade-root cut-outs in the spinner: the round shank + 6 mm (any pitch)
# rubber boot round each shank on the spinner (rotates with the spinner; round, so blade pitch does not move it):
# profile (distance along the blade's pitch axis from the hub, radius about that axis) -- a collar buried in the
# spinner shell below 'rho0', standing 'r_out' proud of the axis up to 'rho1', then rolling in (quarter ellipse) to
# 'r_in' (shank + 2.5 mm) at 'rho2'; its base covers the cut-out edge all round (the shell slopes ~10 deg there)
# VQA r2 SHP2-04: no collar bulge -- the boot is a slim cuff only 5 mm over the cut-out (r_out 0.072 -> hole + 5 mm),
# standing just above the highest cut-out edge (the shell reaches rho 0.247 there) and rolling in over 12 mm
# VQA r3 (SHP2-04 re-check, hangar 130 at 2.5x): the shell slopes ~10 deg across the cut-out (edge rho 0.225-0.244),
# so any collar of revolution about the pitch axis stood 20-25 mm proud on the low side -- the black 'collar ring' of
# the renders.  Photo 130: the upper blade enters the chrome with no visible collar, the lower one shows a flush black
# ring ~20 mm wide round the shank.  The boot is now a SEAL RING lying on the spinner: an annulus r_in..r_out about the
# pitch axis draped on the shell 'lift' above it (blade_boot_surface_s), a skirt 'skirt' under its outer edge and a
# sleeve down the shank to rho0 inside the spinner.
BLADE_BOOT = dict(rho0=0.205, r_in=BLADE_SHANK_R + 0.0015, r_out=BLADE_HOLE_R + 0.013, lift=0.0015, skirt=0.004)
# review r3 RES3-01: the seal ring's edges are rolled (a moulded rubber ring), not cut: its outer edge rounds from the
# skirt over a quarter circle of radius 'lift' onto the top, the inner edge over BOOT_INNER_ROUND down into the sleeve
# (one smooth surface; the skirt below the shell keeps its crisp fold)
BOOT_INNER_ROUND = 0.0015
BOOT_ROUND_N = 6                 # rows per rolled edge
# Spinner / cowl joint (MV2-03).  The spinner base plane is normal to the (2 deg tilted / yawed) thrust axis, the
# cowl-front ring is vertical and not round about that axis (its radius about it is 0.246-0.254): so
#   * the cowl skin ahead of the plane SPINNER_GAP behind the base plane is cut away (cowl_front_field) -- the fixed lip
#     never reaches into the rotating spinner, which ends in a constant SPINNER_GAP ahead of the cowl;
#   * a short cylindrical skirt (SPINNER_SKIRT long) behind the base plane tucks into the cowl, its radius
#     spinner_skirt_r() = the smallest cowl radius over its length less SPINNER_GAP, so it hides the (up to 15 mm)
#     wedge-shaped gap at the top / port side without ever touching the cowl;
#   * the spinner bulkhead at the skirt end is an annulus (SPINNER_BULK_R_IN inside) round the reduction gearbox.
SPINNER_SKIRT = 0.025
SPINNER_GAP = 0.003
SPINNER_BULK_R_IN = 0.160
# review r3 RES3-01: the spinner's base edge (the cone running tangent into the r = SPINNER_R cylinder, then a sharp 90 deg
# turn into the flat step in to the skirt) is a rolled edge of radius SPINNER_BASE_ROUND, the step's outer part in one
# smooth surface with the cone (the spun shell's rim); <= 0.9 mm off the drawn corner (L4 spinner meridian row)
SPINNER_BASE_ROUND = 0.003
_SKIRT_R = []


def spinner_length():
    """Spinner length along the thrust axis: tip (STA spinner_tip) to the base plane through the axis at the cowl front."""
    return float((F.STA["cowl_front"] - F.STA["spinner_tip"]) * np.linalg.norm([1.0, _TY, _TT]))


def thrust_coords(V):
    """(s, r) of points V: s along the thrust axis aft of the spinner tip, r = distance from the axis."""
    a = -thrust_dir()
    w = np.asarray(V, float) - axis_point(F.STA["spinner_tip"])
    s = w @ a
    return s, np.linalg.norm(w - np.outer(s, a), axis=1)


def cowl_front_field(V):
    """Signed field (m, negative = cut away) of the cowl skin: the plane SPINNER_GAP behind the spinner base plane."""
    return thrust_coords(V)[0] - (spinner_length() + SPINNER_GAP)


def spinner_skirt_r():
    """Skirt radius: the smallest radius (about the thrust axis) of the cowl skin left by cowl_front_field over the
    skirt's length, less SPINNER_GAP (cached)."""
    if not _SKIRT_R:
        L = spinner_length()
        x0 = F.STA["cowl_front"]
        X, T = np.meshgrid(np.linspace(x0, x0 + 0.09, 46), np.linspace(0, 1, 721)[:-1], indexing="ij")
        P = F.section(X, T).reshape(-1, 3)
        s, r = thrust_coords(P)
        on = (s >= L + SPINNER_GAP - 1e-4) & (s <= L + SPINNER_SKIRT + 0.004)
        _SKIRT_R.append(float(r[on].min()) - SPINNER_GAP)
    return _SKIRT_R[0]


def _boot_frame(k):
    d = blade_axis(k)
    e1 = np.cross(d, -thrust_dir())
    e1 /= np.linalg.norm(e1)
    return d, e1, np.cross(d, e1)


def blade_boot_surface_s(k, r, phi):
    """Height s along blade k's pitch axis (from the hub) where the line at radius r / angle phi about that axis meets
    the spinner shell (spinner_profile about the thrust axis); vectorised bisection."""
    d, e1, e2 = _boot_frame(k)
    r, phi = np.broadcast_arrays(np.asarray(r, float), np.asarray(phi, float))
    P0 = prop_hub() + r[..., None] * (np.cos(phi)[..., None] * e1 + np.sin(phi)[..., None] * e2)
    t, R = spinner_profile(400)
    L = spinner_length()
    lo, hi = np.full(r.shape, 0.10), np.full(r.shape, 0.32)
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        sa, ra = thrust_coords((P0 + mid[..., None] * d).reshape(-1, 3))
        outside = (ra - np.interp(sa / L, t, R)).reshape(r.shape) > 0
        hi = np.where(outside, mid, hi)
        lo = np.where(outside, lo, mid)
    return 0.5 * (lo + hi)


def blade_boot(k, n=48, n_ring=5):
    """Rubber seal round blade k's shank where it passes through the spinner (BLADE_BOOT): a ring draped on the shell
    (r_in..r_out about the pitch axis, 'lift' above the shell) with a skirt under its outer edge and a sleeve down the
    shank to rho0, closed inside."""
    from cad import res
    b = BLADE_BOOT
    d, e1, e2 = _boot_frame(k)
    n = res.seg(n, b["r_out"])                  # round outline: finer at PC12_RES > 1 (the close-ups' seal ring)
    phi = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
    hub = prop_hub()
    rows = []

    def row(r, s):
        return hub + np.outer(s, d) + r * (np.outer(np.cos(phi), e1) + np.outer(np.sin(phi), e2))

    so = blade_boot_surface_s(k, np.full(n, b["r_out"]), phi)
    rows.append(row(b["r_out"], so - b["skirt"]))
    # the ring's cross-section (radius about the pitch axis, height over the shell): rolled outer edge, the draped top,
    # rolled inner edge down to the sleeve (RES3-01; review r1 RES1-01 had made the edges crisp folds between three grids
    # because one smooth grid averaged the skirt's and the sleeve's normals over a single row -- the rolls now carry the
    # turn over BOOT_ROUND_N rows each)
    lf, ci = b["lift"], min(BOOT_INNER_ROUND, b["lift"])
    ph = np.linspace(0.0, 0.5 * np.pi, BOOT_ROUND_N)
    sec = [(b["r_out"] - lf + lf * np.cos(a), lf * np.sin(a)) for a in ph]
    sec += [(r, lf) for r in np.linspace(b["r_out"] - lf, b["r_in"] + ci, n_ring)[1:-1]]
    sec += [(b["r_in"] + ci - ci * np.sin(a), lf - ci + ci * np.cos(a)) for a in ph]
    for r, h in sec:
        rows.append(row(r, blade_boot_surface_s(k, np.full(n, r), phi) + h))
    si = rows[-1] - hub
    top = si @ d
    for f in (0.15, 0.4, 0.8, 1.0):
        rows.append(row(b["r_in"], top + f * (b["rho0"] - top)))
    R = np.array(rows)
    # skirt (below the shell: a crisp fold, hidden) | rolled ring + sleeve (one smooth surface)
    ring = grid_surface(R[1:], close_v=True)
    flip = float(np.mean(grid_surface(R[1 + BOOT_ROUND_N:1 + BOOT_ROUND_N + 2], close_v=True).N @ d)) < 0
    ms = [grid_surface(R[:2], close_v=True), ring]
    ms = [x.flipped() if flip else x for x in ms]
    cap = cap_ring(rows[-1], -d)
    return Mesh.merge(ms + [cap])


def blade_boot_covers(k, P):
    """Radius margin (m, > 0 = covered) of points P (e.g. the cut-out edge) under blade k's seal ring: r_out minus
    their radius about the pitch axis (the ring spans r_in..r_out right over the shell)."""
    d, _, _ = _boot_frame(k)
    w = np.asarray(P, float) - prop_hub()
    s_ = w @ d
    return BLADE_BOOT["r_out"] - np.linalg.norm(w - np.outer(s_, d), axis=1)


def spinner_mesh(n_around=240, n_prof=110):
    """Spinner: surface of revolution of spinner_profile() about the thrust axis, tip at STA spinner_tip, base plane
    (normal to the axis) through the axis at the cowl front, a skirt of spinner_skirt_r() behind it; blade-root
    openings; returns (shell, bulkhead annulus)."""
    from cad import res
    # the chrome mirrors the studio's strip lights as long streaks along the meridian: with rows 6 mm apart their edges
    # zig-zagged once per row in the close-ups (the triangles' linear normals); 3x the rows at PC12_RES 2 (RES3-01)
    n_prof = int(round(n_prof * (1.5 * res.factor() if res.on() else 1.0)))
    t, r = spinner_profile(n_prof)
    x0 = F.STA["spinner_tip"]
    a = -thrust_dir()
    L = spinner_length()
    rs = spinner_skirt_r()
    rb = SPINNER_BASE_ROUND
    prof = [(L * tt, rr) for tt, rr in zip(t, r) if L * tt < L - rb - 1e-4]
    prof[0] = (0.0, 0.0)
    # the rolled base edge: a quarter round from the cylinder (r = SPINNER_R) onto the base plane, then the step's
    # outer part on that plane (one smooth surface with the cone; the profile runs tangent into the cylinder there)
    R0 = float(r[-1])
    for ph in np.linspace(0.0, 0.5 * np.pi, 9):
        prof.append((L - rb + rb * np.sin(ph), R0 - rb + rb * np.cos(ph)))
    prof.append((L, 0.5 * (rs + R0 - rb)))
    o = axis_point(x0)
    cone = revolve(prof, n=n_around, axis_origin=o, axis_dir=a)
    # base step's inner edge: into the skirt cylinder (separate grids: a hard edge, inside the cowl lip)
    step = revolve([(L, rs), (L, 0.5 * (rs + R0 - rb))], n=n_around, axis_origin=o, axis_dir=a)
    if float(np.mean(step.N @ a)) < 0:
        step = step.flipped()
    skirt = revolve([(L + SPINNER_SKIRT * k / 4, rs) for k in range(5)], n=n_around, axis_origin=o, axis_dir=a)
    shell = Mesh.merge([cone, step, skirt])
    hub = prop_hub()
    f = np.full(len(shell.V), 1.0)
    for k in range(N_BLADES):
        d = blade_axis(k)
        w = shell.V - hub
        s = w @ d                    # one-sided (SHP-01: a cutter on the whole line also cut an empty hole opposite)
        f = np.minimum(f, np.where(s > 0.0, np.linalg.norm(w - np.outer(s, d), axis=1) - BLADE_HOLE_R, 1.0))
    shell = trim(shell, f, "positive")
    c = axis_point(x0) + (L + SPINNER_SKIRT - 0.002) * a
    bulk = revolve([(0.0, SPINNER_BULK_R_IN), (0.0005, rs - 0.003)], n=n_around, axis_origin=c, axis_dir=a)
    bulk = Mesh.merge([bulk, bulk.flipped()])                      # thin plate: visible from both sides
    return shell, bulk


def blade_axis(k):
    """Unit pitch-change axis of blade k (radial, in the tilted propeller disc)."""
    return thrust_rotation() @ (rotation_matrix((1, 0, 0), 2 * np.pi * k / N_BLADES) @ np.array([0, 0, 1.0]))


def build_propeller(parts):
    blade, rs, Pm = blade_geometry()
    # split tip band and leading-edge erosion shield by trimming on radius
    z = blade.V[:, 2]
    tipband = trim(blade, (PROP_R - 0.11) - z, "negative")
    body = trim(blade, (PROP_R - 0.11) - z, "positive")
    hub_c = prop_hub()
    Rt = thrust_rotation()
    prop = Part("propeller", "Hartzell 5-blade composite propeller (2.67 m)", "propeller",
                pivot=dict(origin=hub_c.tolist(), axis=thrust_dir().tolist(), kind="spin", rpm=1700),
                explode=(-1.8, 0, 0), group="Propeller",
                material_note="Carbon composite blades, nickel erosion shields, full-feathering, reversible",
                info={"diameter": "2,670 mm (105 in)", "blades": "5", "rpm": "1,700 (1,550 low-speed mode)",
                      "ground clearance": "320 mm", "thrust line": "2 deg nose-down, 2 deg right"})
    # spinner + hub (spin with the propeller) on the tilted / yawed thrust axis
    spin, bulk = spinner_mesh()
    h = PROP_HUB                                             # ends at the prop-shaft flange (ENG_FLANGE_X)
    hl = (h["fwd"] + h["aft"]) * np.linalg.norm([1.0, _TY, _TT])
    hub = revolve([(0, 0.0), (0.001, h["r"]), (hl - 0.001, h["r"]), (hl, 0.0)], n=40,
                  axis_origin=axis_point(PROP_X - h["fwd"]), axis_dir=-thrust_dir())
    prop.add(spin, "paint_white").add(Mesh.merge([hub, bulk]), "metal_dark")
    prop.add(Mesh.merge([blade_boot(k) for k in range(N_BLADES)]), "deice_boot")
    parts[prop.id] = prop
    for k in range(N_BLADES):
        R = Rt @ rotation_matrix((1, 0, 0), 2 * np.pi * k / N_BLADES)
        M = np.eye(4)
        M[:3, :3] = R
        M[:3, 3] = hub_c
        bb = body.transformed(M)
        bt = tipband.transformed(M)
        radial = blade_axis(k)
        bp = Part(f"blade_{k+1}", f"Blade {k+1}", "propeller", parent="propeller",
                  pivot=dict(origin=hub_c.tolist(), axis=radial.tolist(), kind="pitch", feather=62.0, reverse=-38.0),
                  explode=tuple((radial * 0.45).tolist()), group="Propeller", material_note="Composite blade")
        bp.add(bb, "prop_blade").add(bt, "prop_tip")
        parts[bp.id] = bp


def build(parts):
    from cad import res
    with res.coarse():                  # the engine modules, mount and firewall are seen only through the cutaway /
        build_engine(parts)             # X-ray: the builders' own grids at every PC12_RES (review r1 RES1-05)
    build_inlet_and_exhaust(parts)
    build_propeller(parts)
    return parts
