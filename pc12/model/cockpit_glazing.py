"""
Flight-deck glazing and the dark windshield surround ("mask") of the PC-12 PRO.

Everything here is a signed-distance constraint (metres, negative inside) evaluated on the fuselage
outer mould line (model/fuselage.py); fuselage_parts trims the skin with it and livery paints the mask.

Construction (Stage 2, sheet L2 = drawing/cockpit_detail.py)
-----------------------------------------------------------
The Pilatus NGX model drawing 190.10.40.432 shows that every edge of the flight-deck glazing except
the centre post is a straight line in SIDE projection, i.e. the trace of a plane normal to the plane
of symmetry.  Measured on sheet 1 (residuals of the shared lines < 3 mm):

  * SILL_LINE    windshield lower edge AND the side window's short lower-front edge (30.1 deg,
                 rising forward) -- one plane;
  * ROOF_LINE    the side window's top edge (rising forward 9.5 deg);
  * WS_ROOF_LINE the windshield roof edge, nearly parallel to ROOF_LINE (11 deg) and ~9 mm above it
                 (the A-pillar top lies between the two);
  * PILLAR_LINE  A-pillar centre line (34 deg); the windshield's outboard edge and the side window's
                 front edge are parallel lines PILLAR_WIDTH apart (photos: 32-39 deg);
  * SW_SILL      horizontal side-window sill; SW_AFT vertical aft edge of the "D";
  * WS_POST      the centre post is the only lateral (butt-line) edge: |y| = WS_POST.

The PRO has no direct-vision (DV) window: the side window is the NGX starboard single pane, used on
both sides (photo_notes (a)).  The D-shaped aft end has radii SW_R['top_aft'] / SW_R['bot_aft'] with
a short straight vertical between them.  Drawing and photos disagree on the bottom radius (drawing
~0.21 m, long-lens NGX photo ~0.10 m, close NGX HB-FXK ~0.15 m): 0.175 is the smallest value that keeps
the outline within 15 mm of the drawing -- flagged for the owner on sheet L2.

Deviations from the drawing are tabulated on sheet L2 (max 6-14 mm per pane and view).  The
windshield roof edge has its own plane (WS_ROOF_LINE): the crown section of model/fuselage.py at
STA 3.9 is 5-12 mm fuller than the drawing's, so a single shared roof plane cannot satisfy the plan
view (28 mm) and the front view at the same time.

The PRO dark mask is ONE side-projection region (photo_notes (d)): lower edge MASK_LOW below the
sill, a ramp rising forward at MASK_RAMP_DEG to the point where it meets the nose crown just ahead of
the windshield, a top edge MASK_TOP_MARGIN above the roof plane (so it becomes the narrow roof band
over the windshield), and a straight aft edge leaning MASK_AFT_LEAN_DEG (bottom forward) that stops
just ahead of the airstair door frame.  Because it is a set of planes normal to the plane of
symmetry, the same definition produces the lower band under the windshield, the dark centre post
and the roof band -- one continuous area around all four panes.

Coordinates: x station aft (m), y butt line (+ starboard), z water line.  s = signed arc length
from the crown (+ starboard; old callers pass it instead of y).

Public API (kept for fuselage_parts / livery): windshield_sdf(x, s, z, y), sidewindow_sdf(x, y, z),
surround_sdf(x, y, z, s, grow), smax, smin, x_pillar, z_sw_top, EYE, and the legacy names PILLAR,
PILLAR_HALF, SW_BOTTOM, SW_REAR, SW_TOP.  New: side_outline(), key_points(), edges(), vision(),
z_ws_roof(), z_ws_sill(), SW_BOX / WS_BOX / KEY_STATIONS (skin-patch extents for the builders).
"""
from __future__ import annotations

import math

import numpy as np

# =====================================================================================================
# parameters  (side projection (x, z) unless noted; angles in degrees above horizontal)
# =====================================================================================================
# -- windshield / side-window construction planes (fitted to drawing 190.10.40.432 sheet 1)
SILL_LINE = ((3.3800, 2.1993), -30.10)      # point, slope: windshield lower edge + side-window lower-front edge
ROOF_LINE = ((4.0000, 2.5471), -9.50)       # side-window top edge
WS_ROOF_LINE = ((4.0000, 2.5563), -11.00)   # windshield roof edge (drawing side view: 2.554 at 4.0, -10.3 deg;
                                            # set 2-3 mm higher to balance plan vs front on our fuller crown)
PILLAR_LINE = ((3.8000, 2.3794), 34.80)     # A-pillar centre line
PILLAR_WIDTH = 0.025                        # between windshield and side-window glass, normal to the line
WS_POST = 0.023                             # half-width of the centre post (butt line), drawing 46 mm
SW_SILL = 2.087                             # side-window sill WL (horizontal)
SW_AFT = 4.350                              # side-window aft extreme (vertical part of the D)

# -- corner radii
SW_R = dict(bot_aft=0.175, top_aft=0.110, top_front=0.012, pillar_low=0.015, sill_front=0.022)
WS_R = dict(low_aft=0.065, top_aft=0.015, post=0.035)    # 'post': the two corners at the centre post

# -- the PRO dark mask
MASK_LOW = 0.070                 # lower edge below SW_SILL (photos 0.06-0.08)
MASK_RAMP_X = 3.600              # the ramp leaves the lower edge here (photos: from about STA 3.6) ...
MASK_RAMP_DEG = 25.0             # ... and rises forward at this angle (photos 21-27 deg, notes ~23)
MASK_TOP_MARGIN = 0.060          # top edge above ROOF_LINE, normal to it (PRO photos 3010 / 3036 and the kenia
                                 # overlay: 0.055-0.068; photo_notes "0-0.05" was read at the forward end)
MASK_AFT_X = 4.560               # aft edge at the top line (airstair door fwd frame 4.650 - 0.09)
MASK_AFT_LEAN_DEG = 12.0         # aft edge: bottom forward of the top (photos 7-23 deg)
MASK_R = dict(low_aft=0.060, top_aft=0.040, ramp=0.100)
MASK_CAP_X = 3.000               # forward closure of the region (above the nose crown -> not on the skin)

# -- design eye point (pilot, port; mirror for the co-pilot).  Estimated: PRO photos show the seat
#    headrests at the aft end of the side window (~STA 4.25), eye ~0.17 m ahead of the headrest.
EYE = np.array([4.08, -0.335, 2.36])

ARC_STEP_DEG = 2.0               # arc sampling of the rounded outlines (sagitta < 0.03 mm at r 0.175)


# =====================================================================================================
# 2-D construction in side projection
# =====================================================================================================
def _dir(deg):
    a = math.radians(deg)
    return np.array([math.cos(a), math.sin(a)])


def _line(p, deg, offset=0.0):
    """Line through p with slope angle deg, shifted by `offset` along its left normal."""
    d = _dir(deg)
    n = np.array([-d[1], d[0]])
    return np.asarray(p, float) + offset * n, d


def _isect(L1, L2):
    (p1, d1), (p2, d2) = L1, L2
    s = np.linalg.solve(np.array([d1, -d2]).T, p2 - p1)
    return p1 + s[0] * d1


def rounded_convex(lines, radii, step_deg=ARC_STEP_DEG):
    """Closed outline of a convex polygon given as a cyclic list of directed lines (point, unit
    direction) traversed counter-clockwise in (x, z) -- interior on the left -- with a fillet of
    radii[i] at the vertex between lines[i] and lines[i+1].  Returns (N, 2), not repeated."""
    n = len(lines)
    out = []
    for i in range(n):
        (p0, d0), (p1, d1) = lines[i], lines[(i + 1) % n]
        v = _isect((p0, d0), (p1, d1))
        r = radii[i]
        turn = math.atan2(d0[0] * d1[1] - d0[1] * d1[0], d0 @ d1)      # > 0: left turn (convex)
        if r <= 0 or turn <= 1e-9:
            out.append(v)
            continue
        t = r * math.tan(turn / 2)
        a = v - d0 * t
        c = a + r * np.array([-d0[1], d0[0]])
        a0 = math.atan2(a[1] - c[1], a[0] - c[0])
        k = max(2, int(math.ceil(math.degrees(turn) / step_deg)))
        for j in range(k + 1):
            ang = a0 + turn * j / k
            out.append(c + r * np.array([math.cos(ang), math.sin(ang)]))
    return np.array(out)


def _pillar_edge(side):
    """Windshield-side (side=-1, forward) or side-window-side (+1, aft) edge of the A-pillar."""
    (p, deg) = PILLAR_LINE
    return _line(p, deg, -side * 0.5 * PILLAR_WIDTH)        # left normal of an up-aft line points forward


def _rev(L):
    p, d = L
    return p, -d


def sw_lines():
    """Side window (starboard pane shape, both sides), counter-clockwise from the sill."""
    sill = (np.array([SW_AFT, SW_SILL]), np.array([1.0, 0.0]))
    aft = (np.array([SW_AFT, SW_SILL]), np.array([0.0, 1.0]))
    top = _rev(_line(*ROOF_LINE))
    front = _rev(_pillar_edge(+1))
    cham = _line(*SILL_LINE)
    return [sill, aft, top, front, cham], [SW_R["bot_aft"], SW_R["top_aft"], SW_R["top_front"],
                                           SW_R["pillar_low"], SW_R["sill_front"]]


def ws_lines():
    """Windshield in side projection (the post is the lateral constraint |y| >= WS_POST)."""
    sill = _line(*SILL_LINE)
    aft = _pillar_edge(-1)
    top = _rev(_line(*WS_ROOF_LINE))
    return [sill, aft, top], [WS_R["low_aft"], WS_R["top_aft"], 0.0]


def mask_lines():
    z_low = SW_SILL - MASK_LOW
    top = _rev(_line(*ROOF_LINE, offset=MASK_TOP_MARGIN))
    top_pt = _isect(top, (np.array([MASK_AFT_X, 0.0]), np.array([0.0, 1.0])))
    lean = math.radians(MASK_AFT_LEAN_DEG)
    aft = (top_pt, np.array([math.sin(lean), math.cos(lean)]))
    low = (np.array([MASK_RAMP_X, z_low]), np.array([1.0, 0.0]))
    cap = (np.array([MASK_CAP_X, 0.0]), np.array([0.0, -1.0]))
    ramp = (np.array([MASK_RAMP_X, z_low]), -_dir(180.0 - MASK_RAMP_DEG))
    return [low, aft, top, cap, ramp], [MASK_R["low_aft"], MASK_R["top_aft"], 0.0, 0.0, MASK_R["ramp"]]


_OUTLINE_CACHE = {}


def side_outline(name):
    """Closed (N, 2) outline in side projection (x, z): 'sw' side window, 'ws' windshield (its
    projection is additionally cut by the post / crown), 'mask' dark surround region."""
    key = (name, SILL_LINE, ROOF_LINE, WS_ROOF_LINE, PILLAR_LINE, PILLAR_WIDTH, SW_SILL, SW_AFT, tuple(SW_R.values()),
           tuple(WS_R.values()), MASK_LOW, MASK_RAMP_X, MASK_RAMP_DEG, MASK_TOP_MARGIN, MASK_AFT_X,
           MASK_AFT_LEAN_DEG, tuple(MASK_R.values()))
    if key not in _OUTLINE_CACHE:
        lines, radii = {"sw": sw_lines, "ws": ws_lines, "mask": mask_lines}[name]()
        _OUTLINE_CACHE[key] = rounded_convex(lines, radii)
    return _OUTLINE_CACHE[key]


def key_points():
    """Named construction points in side projection (x, z), for dimensions and checks."""
    sill, roof, wroof = _line(*SILL_LINE), _line(*ROOF_LINE), _line(*WS_ROOF_LINE)
    pw, ps = _pillar_edge(-1), _pillar_edge(+1)
    hz = lambda z: (np.array([0.0, z]), np.array([1.0, 0.0]))
    vx = lambda x: (np.array([x, 0.0]), np.array([0.0, 1.0]))
    L = mask_lines()[0]
    return dict(
        sw_top_front=_isect(roof, ps), sw_low_front=_isect(sill, ps), sw_sill_front=_isect(sill, hz(SW_SILL)),
        sw_top_aft=_isect(roof, vx(SW_AFT)), sw_bot_aft=np.array([SW_AFT, SW_SILL]),
        ws_low_aft=_isect(sill, pw), ws_top_aft=_isect(wroof, pw),
        mask_low_aft=_isect(L[0], L[1]), mask_top_aft=_isect(L[1], L[2]), mask_ramp=_isect(L[4], L[0]),
    )


# =====================================================================================================
# helpers kept from the first model (public API)
# =====================================================================================================
def smax(*vals, k=0.05):
    """Smooth maximum (rounded intersection)."""
    out = vals[0]
    for b in vals[1:]:
        h = np.maximum(k - np.abs(out - b), 0.0) / k
        out = np.maximum(out, b) + h * h * k * 0.25
    return out


def smin(a, b, k=0.06):
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * k * 0.25


def round_intersection(a, b, r):
    """Intersection of two SDFs with a circular fillet of radius r at their corner."""
    return np.minimum(np.maximum(a, b), -r) + np.hypot(np.maximum(a + r, 0.0), np.maximum(b + r, 0.0))


def x_pillar(z):
    """A-pillar centre line: station at water line z."""
    (x0, z0), deg = PILLAR_LINE
    return x0 + (np.asarray(z, float) - z0) / math.tan(math.radians(deg))


def z_sw_top(x):
    """Side-window top edge (the roof plane) at station x."""
    (x0, z0), deg = ROOF_LINE
    return z0 + (np.asarray(x, float) - x0) * math.tan(math.radians(deg))


def z_ws_roof(x):
    """Windshield roof edge plane at station x."""
    (x0, z0), deg = WS_ROOF_LINE
    return z0 + (np.asarray(x, float) - x0) * math.tan(math.radians(deg))


def z_ws_sill(x):
    """Windshield lower edge plane at station x."""
    (x0, z0), deg = SILL_LINE
    return z0 + (np.asarray(x, float) - x0) * math.tan(math.radians(deg))


# old names, derived from the new parameters (two points on the lines; PILLAR_HALF horizontal)
PILLAR = tuple((float(x_pillar(z)), z) for z in (2.10, 2.55))
PILLAR_HALF = 0.5 * PILLAR_WIDTH / math.sin(math.radians(PILLAR_LINE[1]))
SW_BOTTOM = SW_SILL
SW_REAR = SW_AFT
SW_TOP = tuple((x, float(z_sw_top(x))) for x in (4.04, SW_AFT))

# skin-patch extents for the builders (fuselage_parts.build_glazing / build_skin), with margin:
# side window (x, z) box, windshield (x0, x1, |y|max), stations worth a mesh line
def _box(name, pad=0.02):
    O = side_outline(name)
    lo, hi = O.min(0) - pad, O.max(0) + pad
    return dict(cx=float(0.5 * (lo[0] + hi[0])), cz=float(0.5 * (lo[1] + hi[1])), hx=float(0.5 * (hi[0] - lo[0])),
                hz=float(0.5 * (hi[1] - lo[1])), r=0.0)


SW_BOX = _box("sw")                                 # x 3.47-4.37, z 2.067-2.558 (rev A values)
WS_BOX = dict(x0=3.24, x1=4.06, ymax=0.66)


def _key_stations():
    """Stations worth a skin-mesh line: glazing / mask corners and where the sill plane and the mask
    ramp meet the crown (windshield tip, mask point)."""
    from model import fuselage as F
    K = key_points()
    xs = np.linspace(3.0, 3.6, 1201)
    zc = F.z_top(xs)
    tip = xs[np.argmin(np.abs(zc - z_ws_sill(xs)))]
    ramp = (SW_SILL - MASK_LOW) + (MASK_RAMP_X - xs) * math.tan(math.radians(MASK_RAMP_DEG))
    mpt = xs[np.argmin(np.abs(zc - ramp))]
    v = [tip, mpt] + [K[k][0] for k in ("sw_low_front", "sw_sill_front", "mask_ramp", "ws_low_aft", "ws_top_aft",
                                        "sw_top_front", "sw_bot_aft", "mask_low_aft", "mask_top_aft")]
    return tuple(sorted({round(float(x), 3) for x in v}))


KEY_STATIONS = _key_stations()         # rev A: 3.175 3.267 3.456 3.48 3.574 3.6 4.025 4.051 4.35 4.454 4.56


# =====================================================================================================
# signed distance fields
# =====================================================================================================
def _fillets(lines, radii):
    """Per corner: (vertex, tangent point on the incoming line, on the outgoing line, centre, r)."""
    out = []
    n = len(lines)
    for i in range(n):
        (p0, d0), (p1, d1) = lines[i], lines[(i + 1) % n]
        v = _isect((p0, d0), (p1, d1))
        turn = math.atan2(d0[0] * d1[1] - d0[1] * d1[0], d0 @ d1)
        r = radii[i] if turn > 1e-9 else 0.0
        t = r * math.tan(turn / 2)
        a, b = v - d0 * t, v + d1 * t
        out.append((v, a, b, a + r * np.array([-d0[1], d0[0]]), r))
    return out


def convex_rounded_sdf(px, pz, lines, radii):
    """Exact signed distance to the convex, corner-filleted polygon of rounded_convex() (negative
    inside), from its straight pieces and arcs."""
    px, pz = np.broadcast_arrays(np.asarray(px, float), np.asarray(pz, float))
    F_ = _fillets(lines, radii)
    n = len(lines)
    dist = np.full(px.shape, np.inf)
    inside = np.ones(px.shape, bool)
    for i in range(n):
        p0, d0 = lines[i]
        inside &= (-d0[1] * (px - p0[0]) + d0[0] * (pz - p0[1])) >= 0.0      # left of the directed line
        s0, s1 = F_[i - 1][2], F_[i][1]                                   # straight piece of line i
        e = s1 - s0
        L2 = max(float(e @ e), 1e-18)
        t = np.clip(((px - s0[0]) * e[0] + (pz - s0[1]) * e[1]) / L2, 0.0, 1.0)
        dist = np.minimum(dist, np.hypot(px - s0[0] - t * e[0], pz - s0[1] - t * e[1]))
    for v, a, b, c, r in F_:
        if r <= 0:
            continue
        wx, wz = px - c[0], pz - c[1]
        ua, ub = a - c, b - c
        sector = (ua[0] * wz - ua[1] * wx >= 0.0) & (wx * ub[1] - wz * ub[0] >= 0.0)
        rho = np.hypot(wx, wz)
        dist = np.where(sector, np.minimum(dist, np.abs(rho - r)), dist)
        inside &= ~(sector & (rho > r))
    return np.where(inside, -dist, dist)


_LINES = {"sw": sw_lines, "ws": ws_lines, "mask": mask_lines}


def _poly_sdf(px, pz, name):
    lines, radii = _LINES[name]()
    return convex_rounded_sdf(px, pz, lines, radii)


def windshield_sdf(x, s, z, y=None):
    """Two panes: side-projection region (sill, pillar, roof planes) outside the centre post."""
    x, z = np.asarray(x, float), np.asarray(z, float)
    ya = np.abs(y) if y is not None else np.abs(s)
    a = _poly_sdf(x, z, "ws")
    b = WS_POST - ya
    d = round_intersection(a, b, WS_R["post"])
    return np.where((z > 1.95) & (x > 3.0) & (x < 4.3), d, 10.0)


def sidewindow_sdf(x, y, z):
    """Side window (one pane per side, the NGX starboard pane shape; PRO has no DV window)."""
    x, z = np.asarray(x, float), np.asarray(z, float)
    d = _poly_sdf(x, z, "sw")
    return np.where((np.abs(y) > 0.30) & (x > 3.3) & (x < 4.6), d, 10.0)


def surround_sdf(x, y, z, s=None, grow=None):
    """PRO dark mask: one side-projection region (see module docstring).  `grow` (old argument, a
    uniform margin round the panes) is ignored unless given: then it widens the whole outline by
    (grow - 0.034) m, 0.034 being the old default."""
    x, z = np.asarray(x, float), np.asarray(z, float)
    d = _poly_sdf(x, z, "mask")
    if grow is not None:
        d = d - (grow - 0.034)
    return np.where((x > 2.9) & (x < 4.8) & (z > 1.8), d, 10.0)


# =====================================================================================================
# drawn from the parameters: contour the fields on the outer mould line
# =====================================================================================================
def contour_on_oml(field, x0, x1, t0, t1, dx=0.002, ds=0.002, oml=None):
    """Zero contour(s) of field(x, y, z, s) on the OML patch x0..x1, t0..t1 (section parameter, may
    run past 1 / below 0).  Returns a list of (N, 3) polylines on the surface (closed loops repeat
    their first point)."""
    import contourpy
    from model import fuselage as F
    oml = oml or F._OML
    per = float(np.mean([np.linalg.norm(np.diff(oml.section(np.full(401, xx), np.linspace(0, 1, 401)), axis=0),
                                        axis=1).sum() for xx in (x0, x1)]))
    xs = np.linspace(x0, x1, int(math.ceil((x1 - x0) / dx)) + 1)
    ts = np.linspace(t0, t1, int(math.ceil(abs(t1 - t0) * per / ds)) + 1)
    X, T = np.meshgrid(xs, ts, indexing="ij")
    P = oml.section(X, T % 1.0)
    S = np.where((T % 1.0) > 0.5, (T % 1.0) - 1.0, T % 1.0) * per
    Fv = field(P[..., 0], P[..., 1], P[..., 2], S)
    gen = contourpy.contour_generator(z=Fv)
    out = []
    for L in gen.lines(0.0):
        # contourpy returns (column, row) = (t index, x index) for z indexed [x, t]
        xx = np.interp(L[:, 1], np.arange(len(xs)), xs)
        tt = np.interp(L[:, 0], np.arange(len(ts)), ts)
        out.append(oml.section(xx, tt % 1.0))
    return out


def edges(side=+1, which=("ws", "sw", "mask"), dx=0.002):
    """3-D edges on the OML (list of (N, 3) loops per item) of one side (+1 starboard, -1 port)."""
    t0, t1 = (0.0, 0.40) if side > 0 else (0.60, 1.0)
    span = {k: (t0, t1) for k in which}
    if "mask" in which:
        span["mask"] = (-0.42, 0.42)                    # the mask crosses the crown: both sides at once
    fields = {
        "ws": lambda x, y, z, s: windshield_sdf(x, s, z, y),
        "sw": lambda x, y, z, s: sidewindow_sdf(x, y, z),
        "mask": lambda x, y, z, s: surround_sdf(x, y, z, s),
    }
    box = {"ws": (3.15, 4.15), "sw": (3.40, 4.45), "mask": (3.02, 4.75)}
    return {k: contour_on_oml(fields[k], *box[k], *span[k], dx=dx, ds=dx) for k in which}


def vision(eye=None, n=721):
    """Vision angles from the design eye (deg): over the nose straight ahead (in the eye's butt
    plane), down over the side-window sill abeam, and up through the windshield / side window."""
    from model import fuselage as F
    e = np.asarray(EYE if eye is None else eye, float)
    side = np.sign(e[1]) or -1.0
    yb = abs(e[1])
    # over the nose: the lowest ray ahead in the plane y = eye_y grazes the skin (cowling, nose, windshield
    # sill frame) forward of the glass; everything from the glass lower edge aft is transparent or above
    xs = np.linspace(1.10, e[0] - 0.05, n)
    z_skin = F.z_at(xs, np.full_like(xs, yb), upper=True)
    glass = windshield_sdf(xs, None, z_skin, np.full_like(xs, side * yb)) < 0
    x_glass = float(xs[np.argmax(glass)]) if glass.any() else float(xs[-1])
    fwd = xs < x_glass
    down_nose = float(np.degrees(np.max(np.arctan2(z_skin[fwd] - e[2], e[0] - xs[fwd]))))
    # abeam: down over the side-window sill and up to its top (at the eye station)
    ys = float(F.side_y(e[0], SW_SILL))
    down_side = float(np.degrees(np.arctan2(e[2] - SW_SILL, ys - yb)))
    zt = float(z_sw_top(e[0]))
    up_side = float(np.degrees(np.arctan2(zt - e[2], float(F.side_y(e[0], zt)) - yb)))
    # straight ahead up: the roof edge in the eye's butt plane
    xr = np.linspace(3.5, 4.3, 801)
    zr = F.z_at(xr, np.full_like(xr, yb), upper=True)
    k = np.argmin(np.abs(zr - z_ws_roof(xr)))
    up_fwd = float(np.degrees(np.arctan2(zr[k] - e[2], e[0] - xr[k])))
    return dict(eye=e.tolist(), over_nose_down=-down_nose, glass_sill_x=x_glass, abeam_down_over_sill=down_side,
                abeam_up_to_top=up_side, ahead_up_to_roof_edge=up_fwd, roof_edge_x=float(xr[k]))
