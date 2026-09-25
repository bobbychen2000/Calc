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

from cad.mesh import (Mesh, revolve, sweep_profile, sweep_tube, cylinder, box, superellipsoid, disk,
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


# EASA TCDS IM.E.008: PT6E-67XP overall length 1,870.9 mm, overall diameter 481.8 mm.
ENG_FLANGE_X = 0.885
ENG_LENGTH = 1.8709
ENG_DIAM = 0.4818
_SX = ENG_LENGTH / (2.80 - ENG_FLANGE_X)       # module layout was drafted on a 1.915 m envelope
_SR = 0.222 / 0.270      # case radius so that case + external fuel manifold = TCDS overall diameter


def eng_x(x):
    """Map a drafted station onto the certified engine envelope."""
    return ENG_FLANGE_X + (np.asarray(x, float) - ENG_FLANGE_X) * _SX


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

    for pid, name, mesh, mat, exp, note in mods:
        p = Part(pid, name, "powerplant", explode=exp, group="Engine PT6E-67XP", material_note=note)
        p.add(mesh, mat)
        parts[pid] = p

    # engine mount truss (mount ring at the gas generator -> 4 firewall pick-ups)
    tubes = []
    ring = ring_path(2.20, 0.30, 64)
    tubes.append(sweep_tube(ring, 0.016, n=10, cap=False))
    pads = [np.array([2.20, 0, AX_Z]) + 0.30 * np.array([0, np.cos(a), np.sin(a)])
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

    # firewall (titanium) = fuselage section at STA 3.000, inset
    t = np.linspace(0, 1, 96, endpoint=False)
    sec = F.section(np.full_like(t, 2.995), t)
    ctr = np.array([2.995, 0, float(F.z_mw(2.995))])
    sec = ctr + (sec - ctr) * 0.97
    fwp = Part("firewall", "Firewall (titanium, frame 10)", "powerplant", explode=(0.0, 0, 0),
               group="Powerplant installation", material_note="Titanium + insulation, STA 3.000")
    fwp.add(planar_cap(sec, (-1, 0, 0)), "titanium")
    parts[fwp.id] = fwp

    # inlet duct from chin scoop to the plenum
    xs = np.linspace(1.00, 2.52, 24)
    zc = np.interp(xs, [1.00, 1.60, 2.10, 2.52], [1.29, 1.255, 1.27, AX_Z - 0.20])
    path = np.stack([xs, np.zeros_like(xs), zc], 1)
    sc = np.interp(xs, [1.0, 1.8, 2.52], [1.0, 0.95, 1.15])
    duct = sweep_profile(path, ellipse(0.205, 0.070, 32), True, scale=sc, cap=False)
    dp = Part("inlet_duct", "Inlet duct + inertial separator", "powerplant", explode=(0, 0, -0.9),
              group="Powerplant installation", material_note="Composite duct, ice-vane separator")
    dp.add(duct, "composite")
    parts[dp.id] = dp


def ellipse(a, b, n=24):
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.stack([a * np.cos(th), b * np.sin(th)], 1)


def ring_path(x, r, n):
    th = np.linspace(0, 2 * np.pi, n)
    return np.stack([np.full(n, x), r * np.cos(th), AX_Z + r * np.sin(th)], 1)


# ---------------------------------------------------------------------------
# chin inlet and exhaust stacks (external)
# ---------------------------------------------------------------------------
# Exhaust stack centre line (starboard; mirrored for port): (STA, BL, WL - AX_Z).  Stage 2 rev C (review round 3,
# G3-4 / R3-4), re-seated on the Pilatus drawing 190.10.40.432 in all three views and checked on the s/n 3008 photos:
#   * the tube leaves the cowl side at STA ~1.42-1.67 heading outboard, bends aft in a wide elbow (outer skin BL 747 at
#     STA ~1.71 -- front view BL 317-747) and ends in a SCARFED outlet: the mouth is the vertical plane STACK_SCARF
#     (plan line from the inner lip STA 1.736 / BL 0.477 to the outer lip STA 1.971 / BL 0.653), facing aft-inboard;
#     the black heat-tinted collar in the photos is that scarfed end (outer lip ~STA 1.96, mouth centre ~STA 1.85 --
#     the rev B photo value 1.84 was the mouth centre, the drawn 1.96 the outer lip: both agree);
#   * section: ellipse STACK_AB, 0.19 wide in plan (drawn elbow 0.21-0.25) and 0.188 tall (front view WL 1601-1788);
#   * centre WL: drawn 1.69-1.70 (side and front), i.e. 1.675-1.685 once the drawing's 15-18 mm higher nose / prop
#     axis is allowed for (WL 1655 kept, as for the spinner); the photo projection (stbd_ground) had rev B ~30 mm low.
# Fit to the drawn plan outline (outer skin + rear wall, both halves): rms 19 mm (the drawn elbow has a sharp outer
# corner a swept ellipse cannot follow; outer extent BL 0.735 vs 0.747).  The last knot lies beyond the scarf plane.
STACK_PTS = ((1.545, 0.300, 0.025), (1.530, 0.470, 0.025), (1.600, 0.582, 0.026), (1.725, 0.640, 0.028),
             (1.885, 0.570, 0.030), (1.990, 0.515, 0.031))
STACK_AB = (0.095, 0.094)        # section half-sizes: plan (horizontal) / side (vertical); bend radius >= 0.113
STACK_SCARF = ((1.736, 0.477), (1.971, 0.653))    # outlet plane (vertical), plan (STA, BL): inner lip -> outer lip
STACK_COLLAR = 0.085             # heat-blackened outlet collar: this far upstream of the scarf cut, along the tube


def exhaust_stack_path(sgn=1, n=24):
    """Stack centre line (n, 3) for side sgn (+1 starboard), from the cowl side to beyond the outlet plane (the tube
    is cut by STACK_SCARF); natural cubic spline through STACK_PTS."""
    from scipy.interpolate import CubicSpline
    pts = np.array([[x, sgn * y, AX_Z + dz] for x, y, dz in STACK_PTS])
    cs = CubicSpline(np.linspace(0, 1, len(pts)), pts, bc_type="natural")
    return cs(np.linspace(0, 1, n))


def stack_scarf_plane(sgn=1):
    """Outlet (scarf) plane of the stack on side sgn: (point, unit normal) in model axes; the normal points out of
    the tube (aft-inboard).  Signed distance > 0 = cut away."""
    (x0, y0), (x1, y1) = STACK_SCARF
    p = np.array([x0, sgn * y0, AX_Z])
    e = np.array([x1 - x0, sgn * (y1 - y0), 0.0])
    nrm = np.cross(e, [0.0, 0.0, 1.0]) * sgn          # (e_y, -e_x) for starboard: aft-inboard
    return p, nrm / np.linalg.norm(nrm)


def exhaust_stack_rings(sgn=1, n=40, m=28, scarf=False):
    """Section rings (n, m, 3) of the stack tube (ellipse STACK_AB in the plane normal to the centre line; the
    vertical semi-axis stays vertical).  Also returns the arc length along the path (n,).  scarf=True cuts the tube
    at the outlet plane STACK_SCARF: every generator line (fixed ring angle) is clipped where it crosses the plane,
    so the rings beyond the cut collapse onto the mouth curve (for silhouettes / the Stage-3 builder)."""
    path = exhaust_stack_path(sgn, n)
    T = np.gradient(path, axis=0)
    T /= np.linalg.norm(T, axis=1)[:, None]
    th = np.linspace(0, 2 * np.pi, m, endpoint=False)
    rings = []
    for p, t in zip(path, T):
        n1 = np.cross(t, [0.0, 0.0, 1.0])
        n1 /= np.linalg.norm(n1)
        n2 = np.cross(n1, t)
        rings.append(p + np.outer(STACK_AB[0] * np.cos(th), n1) + np.outer(STACK_AB[1] * np.sin(th), n2))
    rings = np.array(rings)
    s = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
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
    R, _ = exhaust_stack_rings(sgn, n, m, scarf=True)
    path = exhaust_stack_path(sgn, n)
    th = np.linspace(0, 2 * np.pi, m, endpoint=False)
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
            nrm = np.cos(th[j]) / STACK_AB[0] * n1 + np.sin(th[j]) / STACK_AB[1] * n2
            if float(nrm @ np.asarray(facing, float)) <= 0.0:
                continue
        for s in np.linspace(sg[-1] - STACK_COLLAR, sg[-1], k):
            out.append([np.interp(s, sg, g[:, i]) for i in range(3)])
    return np.array(out)


def exhaust_stack_collar(sgn=1, m=72, n=200):
    """Forward edge (m + 1, 3) of the heat-blackened collar: STACK_COLLAR upstream of the cut along each generator."""
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
#          1160 / 1340, onto the keel step) and an aft edge ~50 mm behind it (photo port_hangar_130, rectified)
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
          (1.250, 1.201), (1.228, 1.290), (1.206, 1.380), (1.188, 1.460), (1.172, 1.530), (1.150, 1.560)),
)


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

def build_inlet_and_exhaust(parts):
    # chin scoop: lofted super-elliptic sections that fair into the lower cowling
    xs = np.linspace(0.985, 1.95, 26)
    rows = []
    zc = np.interp(xs, [0.985, 1.3, 1.95], [1.290, 1.275, 1.24])
    hw = np.interp(xs, [0.985, 1.25, 1.95], [0.225, 0.245, 0.20])
    hh = np.interp(xs, [0.985, 1.25, 1.6, 1.95], [0.078, 0.090, 0.075, 0.05])
    ts = np.linspace(0, 1, 56, endpoint=False)
    for x, z, w, h in zip(xs, zc, hw, hh):
        a = 2 * np.pi * ts
        n = 2.6
        y = w * np.sign(np.sin(a)) * np.abs(np.sin(a)) ** (2 / n)
        zz = z + h * np.sign(np.cos(a)) * np.abs(np.cos(a)) ** (2 / n)
        rows.append(np.stack([np.full_like(y, x), y, zz], 1))
    P = np.array(rows)
    outer = grid_surface(P, close_v=True)
    if np.mean(np.sum((outer.V - [0, 0, 1.28]) * outer.N * [0, 1, 1], 1)) < 0:
        outer = outer.flipped()
    # keep only the part below the cowling (upper part is buried anyway)
    # lip: tube around the mouth
    mouth = P[0]
    lip_mesh = sweep_tube(np.vstack([mouth, mouth[:1]]) + [-0.004, 0, 0], 0.016, n=10, cap=False)
    # duct interior (dark) and back wall
    inner_rows = []
    for k, x in enumerate(np.linspace(0.99, 1.35, 8)):
        c = np.array([x, 0, np.interp(x, [0.985, 1.35], [1.29, 1.28])])
        inner_rows.append(c + (mouth - [0.985, 0, 1.29]) * [0, 0.9, 0.85] + [0, 0, 0])
    inner = grid_surface(np.array(inner_rows), close_v=True).flipped()
    back = cap_ring(inner_rows[-1], (-1, 0, 0))
    p = Part("chin_inlet", "Chin air inlet (engine + oil cooler)", "cowling", explode=(-0.4, 0, -0.75),
             group="Powerplant installation", material_note="Composite lip, electrically de-iced")
    p.add(outer, "paint_white").add(lip_mesh, "metal").add(Mesh.merge([inner, back]), "inlet_dark")
    parts[p.id] = p

    # exhaust stacks
    stacks, inner_s = [], []
    for sgn in (1, -1):
        path = exhaust_stack_path(sgn, 20)             # table STACK_PTS (Stage 3: black outlet collar STACK_COLLAR)
        prof = ellipse(*STACK_AB, 28)
        o = sweep_profile(path, prof, True, cap=False)
        i = sweep_profile(path, prof * 0.84, True, cap=False).flipped()
        # rim at exit
        rim_o = path[-1]
        stacks.append(o)
        inner_s.append(i)
        # annulus at the exit
        T = path[-1] - path[-2]
        T /= np.linalg.norm(T)
        from cad.mesh import parallel_transport_frames
        Tt, Nn, B = parallel_transport_frames(path)
        ring_o = path[-1] + prof[:, 0, None] * Nn[-1] + prof[:, 1, None] * B[-1]
        ring_i = path[-1] + 0.84 * (prof[:, 0, None] * Nn[-1] + prof[:, 1, None] * B[-1])
        n = len(prof)
        V = np.vstack([ring_o, ring_i])
        k = np.arange(n)
        Fc = np.vstack([np.stack([k, (k + 1) % n, (k + 1) % n + n], 1), np.stack([k, (k + 1) % n + n, k + n], 1)])
        an = Mesh(V, Fc)
        if np.dot(an.face_normals().mean(0), T) < 0:
            an = an.flipped()
        stacks.append(an)
    ep = Part("exhaust_stacks", "Exhaust stacks (L/R)", "cowling", explode=(-0.2, 0, 0.0), qty=2,
              group="Powerplant installation", material_note="Inconel stacks")
    ep.add(Mesh.merge(stacks), "exhaust").add(Mesh.merge(inner_s), "black")
    parts[ep.id] = ep


# ---------------------------------------------------------------------------
# propeller
# ---------------------------------------------------------------------------

def blade_geometry(n_r=34, n_c=40):
    """One blade along +z (radial), pitch axis = z axis through the hub centre,
    chord in the x-y plane at blade angle beta (0 = chord in the rotation plane)."""
    rs = np.concatenate([np.linspace(0.155, 0.30, 8), np.linspace(0.30, PROP_R - 0.03, n_r - 8)[1:],
                         PROP_R - np.array([0.02, 0.01, 0.004])])
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


def build_propeller(parts):
    blade, rs, Pm = blade_geometry()
    # split tip band and leading-edge erosion shield by trimming on radius
    z = blade.V[:, 2]
    tipband = trim(blade, (PROP_R - 0.11) - z, "negative")
    body = trim(blade, (PROP_R - 0.11) - z, "positive")
    hub_c = np.array([PROP_X, 0, AX_Z])
    prop = Part("propeller", "Hartzell 5-blade composite propeller (2.67 m)", "propeller",
                pivot=dict(origin=hub_c.tolist(), axis=[-1.0, 0, 0], kind="spin", rpm=1700),
                explode=(-1.8, 0, 0), group="Propeller",
                material_note="Carbon composite blades, nickel erosion shields, full-feathering, reversible",
                info={"diameter": "2,670 mm (105 in)", "blades": "5", "rpm": "1,700 (1,550 low-speed mode)",
                      "ground clearance": "320 mm"})
    # spinner + hub (spin with the propeller)
    prof = []
    L = 0.935 - 0.39
    for t in np.linspace(0, 1, 44):
        r = 0.291 * (1 - (1 - t) ** 2.1) ** 0.55
        prof.append((L * t, r))
    prof[0] = (0.0, 0.0)
    prof.append((L + 0.001, 0.0))
    spin = revolve(prof, n=64, axis_origin=(0.39, 0, AX_Z), axis_dir=(1, 0, 0))
    hub = revolve([(0, 0.0), (0.001, 0.13), (0.20, 0.13), (0.201, 0.0)], n=40,
                  axis_origin=(0.70, 0, AX_Z), axis_dir=(1, 0, 0))
    prop.add(spin, "paint_white").add(hub, "metal_dark")
    parts[prop.id] = prop
    for k in range(N_BLADES):
        ang = 2 * np.pi * k / N_BLADES
        R = rotation_matrix((1, 0, 0), ang)
        M = np.eye(4)
        M[:3, :3] = R
        M[:3, 3] = hub_c
        bb = body.transformed(M)
        bt = tipband.transformed(M)
        radial = R @ np.array([0, 0, 1.0])
        bp = Part(f"blade_{k+1}", f"Blade {k+1}", "propeller", parent="propeller",
                  pivot=dict(origin=hub_c.tolist(), axis=radial.tolist(), kind="pitch", feather=62.0, reverse=-38.0),
                  explode=tuple((radial * 0.45).tolist()), group="Propeller", material_note="Composite blade")
        bp.add(bb, "prop_blade").add(bt, "prop_tip")
        parts[bp.id] = bp


def build(parts):
    build_engine(parts)
    build_inlet_and_exhaust(parts)
    build_propeller(parts)
    return parts
