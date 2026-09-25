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

    Mt = thrust_matrix()                     # the engine is installed on the thrust line (2 deg down, 2 deg right)
    for pid, name, mesh, mat, exp, note in mods:
        p = Part(pid, name, "powerplant", explode=exp, group="Engine PT6E-67XP", material_note=note,
                 info={"axis": "on the thrust line: 2 deg nose-down, 2 deg right (drawing)"})
        p.add(mesh.transformed(Mt), mat)
        parts[pid] = p

    # engine mount truss (mount ring at the gas generator, on the thrust line -> 4 firewall pick-ups)
    tubes = []
    xf = lambda P: (Mt[:3, :3] @ np.asarray(P, float).T).T + Mt[:3, 3]            # noqa: E731
    ring = xf(ring_path(2.20, 0.30, 64))
    tubes.append(sweep_tube(ring, 0.016, n=10, cap=False))
    pads = [xf(np.array([2.20, 0, AX_Z]) + 0.30 * np.array([0, np.cos(a), np.sin(a)]))
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

CHIN_STEP_X_MAX = 1.215       # the mouth is the part of the keel step face (x <= this) inside the drawn mouth outline
_CHIN = {}                    # mouth edge loop of the last cut (fuselage_parts.build -> build_inlet_and_exhaust)


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


def cut_chin_inlet(m):
    """Cut the chin inlet into the lower cowling (decision D2: the OML keel owns the lip step STA 1.14 -> 1.20):
    returns (cowl without mouth and lip, polished lip ring).  The mouth = the step face inside the drawn front-view
    mouth outline; the lip = the skin inside both the front-view lip outline and the side-view lip crescent."""
    from cad.mesh import boundary_loops
    fm = lambda mm: np.maximum(chin_fields(mm.V)[0], mm.V[:, 0] - CHIN_STEP_X_MAX)     # noqa: E731
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
    fl = lambda mm: np.maximum(chin_fields(mm.V)[1], chin_fields(mm.V)[2])              # noqa: E731
    lip = trim(m1, fl(m1), "negative")
    rest = trim(m1, fl(m1), "positive")
    return rest, lip


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


def exhaust_stack_mesh(sgn, n=48, m=36, wall=0.006):
    """Scarfed stack (outer skin, inner wall, lip at the scarf plane); returns (tube, collar, inner)."""
    R, _ = exhaust_stack_rings(sgn, n, m, scarf=True)
    path = exhaust_stack_path(sgn, n)
    cen = path[:, None, :]
    # arc length of every generator from its scarf end (the collar is the last STACK_COLLAR of it)
    seg = np.linalg.norm(np.diff(R, axis=0), axis=2)
    s = np.vstack([np.zeros((1, m)), np.cumsum(seg, 0)])
    to_end = s[-1][None, :] - s
    UV = np.stack([to_end, np.zeros_like(to_end)], -1)
    outer = grid_surface(R, close_v=True, UV=UV)
    if np.mean(np.sum((outer.V[:m] - path[0]) * outer.N[:m], 1)) < 0:
        outer = outer.flipped()
    Ri = cen + (R - cen) * (1 - wall / min(STACK_AB))
    Ri = _clip_generators(Ri, *stack_scarf_plane(sgn))
    inner = grid_surface(Ri, close_v=True)
    if np.mean(np.sum((inner.V[:m] - path[0]) * inner.N[:m], 1)) > 0:
        inner = inner.flipped()
    V = np.vstack([R[-1], Ri[-1]])
    k = np.arange(m)
    lip = Mesh(V, np.vstack([np.stack([k, (k + 1) % m, (k + 1) % m + m], 1), np.stack([k, (k + 1) % m + m, k + m], 1)]))
    if np.dot(lip.face_normals().mean(0), stack_scarf_plane(sgn)[1]) < 0:
        lip = lip.flipped()
    collar = trim(outer, outer.UV[:, 0] - STACK_COLLAR, "negative")
    tube = trim(outer, outer.UV[:, 0] - STACK_COLLAR, "positive")
    return tube, Mesh.merge([collar, lip]), inner


def build_inlet_and_exhaust(parts):
    # chin inlet (D2): the lip was cut from the lower cowling (cut_chin_inlet); the duct lofts from that mouth edge
    mouth = _CHIN.get("mouth")
    if mouth is None:
        raise RuntimeError("chin inlet: the lower cowling was not cut (fuselage_parts.build must run first)")
    rings = chin_duct(mouth)
    entry = grid_surface(rings[:3], close_v=True)                    # mouth -> STA 1.50 (seen through the mouth)
    duct = grid_surface(rings[2:], close_v=True)
    back = cap_ring(rings[-1], (1, 0, 0))
    p = parts.get("chin_inlet") or Part("chin_inlet", "Chin air inlet", "cowling", explode=(-0.4, 0, -0.75),
                                        group="Powerplant installation")
    p.add(entry, "inlet_dark")
    parts[p.id] = p
    dp = Part("inlet_duct", "Inlet duct + inertial separator (to the plenum)", "powerplant", explode=(0, 0, -0.9),
              group="Powerplant installation", material_note="Composite duct, ice-vane separator")
    dp.add(Mesh.merge([duct, back]), "composite")
    parts[dp.id] = dp

    # exhaust stacks: tube along STACK_PTS / STACK_AB, cut by the scarf plane STACK_SCARF, heat-blackened collar
    tubes, collars, inners = [], [], []
    for sgn in (1, -1):
        t, c, i = exhaust_stack_mesh(sgn)
        tubes.append(t)
        collars.append(c)
        inners.append(i)
    ep = Part("exhaust_stacks", "Exhaust stacks (L/R), scarfed outlets", "cowling", explode=(-0.2, 0, 0.0), qty=2,
              group="Powerplant installation", material_note="Inconel stacks, heat-tinted outlet collars")
    ep.add(Mesh.merge(tubes), "exhaust").add(Mesh.merge(collars), "black").add(Mesh.merge(inners), "black")
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


BLADE_HOLE_R = 0.068          # blade-root openings in the spinner (pitch axis radius; clears the cuff at any pitch)
# The spinner base plane is normal to the (2 deg tilted / yawed) thrust axis, the cowl-front ring is vertical: a
# 25 mm cylindrical skirt (R SPINNER_R) behind the base plane tucks into the cowl so no gap opens at the top / port
# side (the skirt stays inside the cowl skin, whose radius grows aft of the cowl front).
SPINNER_SKIRT = 0.025


def spinner_mesh(n_around=160, n_prof=90):
    """Spinner: surface of revolution of spinner_profile() about the thrust axis, tip at STA spinner_tip, base plane
    (normal to the axis) through the axis at the cowl front; blade-root openings; returns (shell, bulkhead)."""
    t, r = spinner_profile(n_prof)
    x0, x1 = F.STA["spinner_tip"], F.STA["cowl_front"]
    a = -thrust_dir()
    L = (x1 - x0) * np.linalg.norm([1.0, _TY, _TT])
    prof = [(L * tt, rr) for tt, rr in zip(t, r)]
    prof[0] = (0.0, 0.0)
    prof += [(L + SPINNER_SKIRT * k / 4, float(r[-1])) for k in range(1, 5)]     # short skirt into the cowl front
    shell = revolve(prof, n=n_around, axis_origin=axis_point(x0), axis_dir=a)
    hub = prop_hub()
    f = np.full(len(shell.V), 1.0)
    for k in range(N_BLADES):
        d = blade_axis(k)
        w = shell.V - hub
        f = np.minimum(f, np.linalg.norm(w - np.outer(w @ d, d), axis=1) - BLADE_HOLE_R)
    shell = trim(shell, f, "positive")
    bulk = disk(axis_point(x0) + (L + SPINNER_SKIRT - 0.002) * a, a, float(r[-1]) - 0.003, n=n_around)
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
    hub = revolve([(0, 0.0), (0.001, 0.13), (0.20, 0.13), (0.201, 0.0)], n=40,
                  axis_origin=axis_point(PROP_X - 0.10), axis_dir=-thrust_dir())
    prop.add(spin, "paint_white").add(Mesh.merge([hub, bulk]), "metal_dark")
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
    build_engine(parts)
    build_inlet_and_exhaust(parts)
    build_propeller(parts)
    return parts
