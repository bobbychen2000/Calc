"""
Cabin fittings (Stage 3): the 3-D build of the APPROVED L6 cabin-furniture tables in model/interior.py -- PC-12 PRO
executive cabin (EX-6S-2), s/n 3001 'AI Orange' finish.  Every dimension that sheet L6 draws is taken from the tables
and the derived functions interior.py gives the drawing (nothing here re-defines a drawn dimension):

  FLOOR       wl, t / t_wing over wing_x (<= 15 mm on the carry-through), carpet from the divider (DIVIDER x_aft) to
              the baggage aft wall (BAGGAGE aft_x), fitted to the lining (interior.lining_section)
  SEAT_TRACKS the four surface-mounted tracks (bl, x0 .. x1, w, h)
  LEDGES      runs (side, x0, x1), top_h, inner_bl, fascia, FLOOR edge_bl (kick panel to the floor edge), the port
              door_segment carried by the cargo door (cargo_door_ledge()), cupholder_dx (cup-holder pair ahead of each
              seat back, interior.seat_map)
  TABLES      club tables of the layout: x, bl_in, leaf, top_h, t -- stowed in the ledge (the edge band in the fascia),
              'leaf' (outboard leaf slid out) or 'deployed' (both leaves); 'aft_s' on request
  LAVATORY    x, inboard_bl, door (bi-fold doors, leaf), cabinet (x0, x1, depth, 350 mm height), bowl_x, seat_ring,
              seat_back, shelf_x, niche, tp_holder -- veneer outside, white inside; forward wall = the RH divider
  CABINETS    LH / RH: x, bl_in, h (upper + lower drawer)
  LINING      headliner_flat (flat centre panel, LED coves either side), psu_bl (reading light + gasper per seat)
  BAGGAGE     partition_x (FR34), bar_h (rod), header_t (veneer arch header), curtain_t (pleats), kind (PRO: header +
              pleated curtain; 'net' = the non-PRO standard fit), tiedowns, aft_x (aft wall)
  DIVIDER     curtain + track + extinguisher: built by model/flightdeck.py (not here)

The interior_lining part (interior.build_lining: side wall / headliner inside the OML by lining_offset, window reveals,
door wells) is the wall everything here stands against: fittings sit on or in front of it (tabulated here from
interior.lining_section, the same section L1 / L6 draw) and stay clear of the windows.  Detail sizes the sheets do
not draw (radii, cup-holder and PSU sizes, handles, pleat pitch, carpet runner) are the DETAIL constants, tagged [M]
(photos in the gitignored refs/cache) or [E]; the carpet runner pattern is procedural (seeded), not traced.

API
  build_cabin_fittings(layout=None, tables='stowed', partition=None, lav_doors='closed', tracks=True, runner=True,
                       o2=True, door_ledge=False, groups=False) -> [(Mesh, material)]  (one mesh per material;
                       groups=True: {group: [(Mesh, material)]} -- floor, runner, tracks, ledges, tables, cabinets,
                       lavatory, headliner, partition, baggage)
  cargo_door_ledge(layout=None) -> [(Mesh, material)]   the port ledge segment on the cargo door (model coordinates,
                       door closed): belongs to the door_cargo part so it swings with the door's pivot
  build(parts, layout=None, **kw) -> Part 'cabin_interior' (drop-in for the rev-A interior.build_cabin) and, when
                       parts holds 'door_cargo', the door ledge added to it
  MATERIALS / EMISSIVE  this builder's palette entries (views of assemble.MATERIALS / EMISSIVE)
  tri_counts(**kw)     {group: triangles}
"""
from __future__ import annotations

import math
from collections import defaultdict

import numpy as np

from cad.mesh import (Mesh, grid_surface, planar_cap, trim, band, boundary_loops, cylinder, disk, superellipsoid)
from model import interior as I
from model import fuselage as F

# =====================================================================================================================
# materials: the values live in model/assemble.MATERIALS / EMISSIVE (and render/lookdev.py SPEC); these are the names
# this builder introduced (views of that table, kept for the preview scripts)
# =====================================================================================================================
from model.assemble import MATERIALS as _MAT, EMISSIVE as _EMI     # noqa: E402

OWN_MATERIALS = ("carpet", "carpet_orange", "carpet_light", "carpet_grey", "floor_panel", "ledge_top", "ledge_panel",
                 "gloss_black", "chrome_trim", "veneer_walnut", "curtain", "psu_panel", "psu_housing", "light_cove", "light_reading",
                 "placard_red", "lav_white", "toilet_white", "toilet_bowl", "lav_grey", "upholstery_grey", "net")
MATERIALS = {k: _MAT[k] for k in OWN_MATERIALS}
EMISSIVE = {k: v for k, v in _EMI.items() if k in OWN_MATERIALS}
# also used, already in assemble.MATERIALS: lining, metal_dark, black
USED_EXISTING = ("lining", "metal_dark", "black")

# =====================================================================================================================
# detail constants (not drawn on L6)
# =====================================================================================================================
DETAIL = dict(
    nose_r=0.006,                     # [E] rounded top edge of the ledge fascia
    kick_in=0.003,                    # [H] kick panel top 3 mm inboard of the fascia (L6 section polygon)
    cup=(0.036, 0.056, 0.070, 0.005),  # [M] figure-8 cup-holder pair: radius, centre spacing along x, depth, rim
    usb=(0.065, 0.028, 0.12),          # [M] switch / USB plate on the ledge: length, width, ahead of the cups
    wall_usb=(0.024, 0.030, 0.14),     # [M] USB socket on the sidewall: width, height, centre above the ledge top
    table_r=0.020,                    # [E] table leaf corner radius
    cab_r=(0.012, 0.008),             # [E] cabinet vertical-edge / top-edge radii
    drawer_split=0.400,               # [E] lower / upper drawer joint above the floor
    lav_wall=0.030,                   # [E] lav wall thickness (as L6 plan draws it)
    lav_door_z=(0.05, 1.35),          # [E] bi-fold door leaves above the floor (as L6 profile draws them)
    lav_door_t=0.020,                 # [E] door panel thickness
    lid=(0.36, 0.023, 0.012),         # [E] open lid: length, thickness, gap to the outboard wall (L6 plan)
    ring_h=0.018,                     # [E] toilet seat ring height
    pad_t=0.050,                      # [E] padded shelf cushion
    niche_rim=(0.015, 0.030),         # [E] lit niche surround: width, depth proud of the lining
    tp=(0.055, 0.090),                # [M] toilet roll radius (L6 profile), length [E]
    cove_h=0.007,                     # [E] LED strip along the top of the soffit step (washes the raised channel)
    psu=(0.200, 0.070, 0.012, 0.30),  # [M] PSU housing along x, across, proud; over the lap: head x - 0.30 x facing
    fit_proud=(0.0012, 0.002),        # [E] flush lining fittings (O2 doors, PULL cover, downlights): dark gap ring /
                                      # bezel face this far proud of the lining, walls this far into it (r2 C2 / C7)
    downlight=(0.60, 0.022, 0.245),   # [M] soffit downlights: pitch, bezel radius (~45 dia, P1046402), |BL| on the band
    o2=(0.100, 0.090, 2.58),          # [M] oxygen-mask flap (optional system): along x, along the wall, WL
    pull=(0.20, 0.13, 0.090),         # [M] exit-release PULL cover above the exit: size, above the hatch top
    pleat=0.060,                      # [E] FR34 curtain pleat pitch (depth = BAGGAGE curtain_t)
    rod_r=0.008,                      # [E] curtain rod radius
    grille=(0.26, 0.06),              # [M] return-air grille ahead of the FR34 header: across, along x
    net=(0.10, 0.0035),               # [E] optional baggage net: mesh, cord radius
    runner=(0.21, 22),                # [M] aisle runner half-width (P1046406: the bands fill the aisle between the
                                      # seat bases), pattern seed (procedural)
)
# aisle runner pattern (final judge r1 I3, P1046402 / 04 / 06) [M]: lanes across the runner, navy gap between lanes,
# band width range, band length range, the navy break between bands along a lane, end cut (x run per unit band width;
# the ends are cut at an angle), step slope (x run per unit sideways step: 45 deg), colour mix (weights: ~35 % of the
# runner orange, cream blocks, a few light-grey ones)
RUNNER = {"lanes": 4, "gap": 0.016, "width": (0.050, 0.085), "length": (0.45, 1.40), "break": (0.03, 0.25),
          "end_cut": (0.4, 1.0), "step_slope": 1.0,
          "mix": (("carpet_orange", 0.60), ("carpet_light", 0.28), ("carpet_grey", 0.12))}

FL = float(I.FLOOR["wl"])
LG = I.LEDGES
ZT = FL + float(LG["top_h"])           # ledge top
YI = float(LG["inner_bl"])             # ledge inner face (fascia)
XA = float(I.DIVIDER["x_aft"])         # cabin floor: divider aft face ..
XB = float(I.BAGGAGE["aft_x"])         # .. baggage aft wall
XP = float(I.BAGGAGE["partition_x"])   # FR34


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


# =====================================================================================================================
# lining lookup (interior.lining_section tabulated: half-width at (x, z), headliner at (x, |y|))
# =====================================================================================================================
class _Lining:
    def __init__(self, x0=4.50, x1=9.88, dx=0.02):
        from scipy.interpolate import RegularGridInterpolator as RGI
        self.xs = np.arange(x0, x1 + 1e-9, dx)
        self.zs = np.linspace(0.95, 2.85, 381)
        self.ys = np.linspace(0.0, 0.85, 171)
        HW, CR = [], []
        for x in self.xs:
            L = I.lining_section(float(x), n=1441)
            k = len(L)
            S = L[:k // 2]                                           # starboard, crown -> keel
            HW.append(np.interp(self.zs, S[::-1, 1], S[::-1, 0]))
            S4 = L[:k // 4]                                          # crown -> max breadth
            CR.append(np.interp(self.ys, S4[:, 0], S4[:, 1]))
        kw = dict(bounds_error=False, fill_value=None)
        self._hw = RGI((self.xs, self.zs), np.array(HW), **kw)
        self._cr = RGI((self.xs, self.ys), np.array(CR), **kw)

    def hw(self, x, z):
        """|BL| of the sidewall lining at station x, water line z."""
        x, z = np.broadcast_arrays(np.asarray(x, float), np.asarray(z, float))
        return self._hw(np.stack([x.ravel(), z.ravel()], 1)).reshape(x.shape)

    def crown(self, x, y):
        """Water line of the headliner at station x, butt line y."""
        x, y = np.broadcast_arrays(np.asarray(x, float), np.abs(np.asarray(y, float)))
        return self._cr(np.stack([x.ravel(), y.ravel()], 1)).reshape(x.shape)

    def head_normal(self, x, y, h=0.004):
        """Unit normal of the headliner at (x, y), pointing into the cabin (down / inboard)."""
        dz = float(self.crown(x, y + h) - self.crown(x, y - h)) / (2 * h)
        return _unit([0.0, dz, -1.0])

    def wall_normal(self, x, z, side, h=0.004):
        """Unit normal of the side wall at (x, z) on `side`, pointing into the cabin."""
        dy = float(self.hw(x, z + h) - self.hw(x, z - h)) / (2 * h)
        return _unit([0.0, -side, dy])


def _conform(m, fr, side):
    """Bend a small flat wall fitting built in frame fr (w = the wall normal into the cabin, c = 0 on the wall at the
    frame origin) onto the curved side-wall lining: every vertex keeps its offset c along w, measured from the lining
    instead of from the tangent plane (a 0.1 m panel on the ~0.8 m wall radius is ~1.5 mm off its tangent plane at the
    edges: review r1 C2 z-fighting).  m: a Mesh or a slab() list [(Mesh, material)] (returned in kind)."""
    if isinstance(m, list):
        return [(_conform(mm, fr, side), mat) for mm, mat in m]
    L = lining()
    V = m.V.copy()
    c = (V - fr.o) @ fr.w
    q = V - c[:, None] * fr.w
    t = np.zeros(len(V))
    for _ in range(4):                                  # Newton on g(t) = |y| - hw(x, z) along w
        P = q + t[:, None] * fr.w
        g = np.abs(P[:, 1]) - L.hw(P[:, 0], P[:, 2])
        e = 1e-4
        P2 = P + e * fr.w
        g2 = np.abs(P2[:, 1]) - L.hw(P2[:, 0], P2[:, 2])
        t = t - g * e / np.where(np.abs(g2 - g) > 1e-12, g2 - g, -1e-12)
    out = Mesh(q + (t + c)[:, None] * fr.w, m.F)
    return out


_LIN = None


def lining():
    global _LIN
    if _LIN is None:
        _LIN = _Lining()
    return _LIN


def soffit_band(x, y):
    """WL of the soffit band (interior.headliner_z, LINING soffit) at (x, |y|) for |y| in the band, vectorised on the
    tabulated lining: the straight band from LINING soffit[0] below the lining at the channel edge (|BL|
    headliner_flat / 2) to the lining at |BL| soffit[1]."""
    L = lining()
    a = np.abs(np.asarray(y, float))
    y0 = 0.5 * float(I.LINING["headliner_flat"])
    d, y2 = (float(v) for v in I.LINING["soffit"])
    z0, z2 = L.crown(x, y0) - d, L.crown(x, y2)
    return np.minimum(z0 + (z2 - z0) * (a - y0) / (y2 - y0), L.crown(x, a))


def band_normal(x, side):
    """Unit normal of the soffit band on `side` (pointing into the cabin: down and inboard)."""
    y0 = 0.5 * float(I.LINING["headliner_flat"])
    y2 = float(I.LINING["soffit"][1])
    m = float((soffit_band(x, y2) - soffit_band(x, y0)) / (y2 - y0))
    return _unit([0.0, side * m, -1.0])


def ceiling(x, y):
    """Underside of the headliner (lining or soffit band) at (x, y): what full-height walls end against."""
    L = lining()
    a = np.abs(np.asarray(y, float))
    y0 = 0.5 * float(I.LINING["headliner_flat"])
    y2 = float(I.LINING["soffit"][1])
    c = L.crown(x, a)
    return np.where((a >= y0) & (a <= y2), soffit_band(x, a), c)


# =====================================================================================================================
# small geometry helpers
# =====================================================================================================================
class Fr:
    """Local frame: p(a, b, c) = o + a u + b v + c w (w = u x v unless given)."""

    def __init__(self, o, u, v, w=None):
        self.o = np.asarray(o, float)
        self.u = _unit(u)
        v = np.asarray(v, float)
        self.v = _unit(v - self.u * np.dot(v, self.u))
        self.w = _unit(np.cross(self.u, self.v)) if w is None else _unit(w)

    def p(self, a, b, c=0.0):
        a, b, c = np.broadcast_arrays(np.asarray(a, float), np.asarray(b, float), np.asarray(c, float))
        return self.o + a[..., None] * self.u + b[..., None] * self.v + c[..., None] * self.w

    @property
    def R(self):
        return np.stack([self.u, self.v, self.w], 1)

    def se(self, a, b, c, radii, e=(0.25, 0.25), n=(8, 12)):
        return superellipsoid(self.p(a, b, c), radii, e, nu=n[0], nv=n[1], R=self.R)

    def cyl(self, a0, b0, c0, a1, b1, c1, r, n=12, cap=True):
        return cylinder(self.p(a0, b0, c0), self.p(a1, b1, c1), r, n=n, cap=cap)

    def disk(self, a, b, r, c=0.0, n=24, r_inner=0.0):
        return disk(self.p(a, b, c), self.w, r, n=n, ref=self.u, r_inner=r_inner)

    def poly(self, P2, c=0.0):
        P2 = np.asarray(P2, float)
        return _oriented(planar_cap(self.p(P2[:, 0], P2[:, 1], c), self.w), self.w)


def _oriented(m, direction):
    """Flip m if its mean face normal points against `direction` (a vector or a function of the face centres)."""
    if m is None or not len(m.F):
        return m
    fn = m.face_normals()
    C = m.V[m.F].mean(1)
    d = direction(C) if callable(direction) else np.broadcast_to(np.asarray(direction, float), fn.shape)
    return m.flipped() if np.mean(np.sum(fn * d, 1)) < 0 else m


def _strip(A, B, closed=False):
    """Quad strip between two polylines / loops of equal length (flat-ish: normals from the faces)."""
    A, B = np.asarray(A, float), np.asarray(B, float)
    n = len(A)
    i = np.arange(n if closed else n - 1)
    j = (i + 1) % n
    V = np.vstack([A, B])
    Fc = np.vstack([np.stack([i, j, n + j], 1), np.stack([i, n + j, n + i], 1)])
    return Mesh(V, Fc).remove_degenerate(1e-14)


def rrect2(a0, b0, a1, b1, r, n=4):
    """Counter-clockwise rounded rectangle outline (n segments per corner; r = 0: plain rectangle)."""
    if r <= 1e-9:
        return np.array([(a0, b0), (a1, b0), (a1, b1), (a0, b1)], float)
    pts = []
    for (ca, cb, t0) in ((a1 - r, b0 + r, -90.0), (a1 - r, b1 - r, 0.0), (a0 + r, b1 - r, 90.0),
                         (a0 + r, b0 + r, 180.0)):
        for t in np.radians(np.linspace(t0, t0 + 90.0, n + 1)):
            pts.append((ca + r * math.cos(t), cb + r * math.sin(t)))
    P = np.array(pts)
    keep = np.r_[True, np.linalg.norm(np.diff(P, axis=0), axis=1) > 1e-9]
    return P[keep]


def ellipse2(ca, cb, ra, rb, n=40):
    t = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
    return np.c_[ca + ra * np.cos(t), cb + rb * np.sin(t)]


def _normals2(Q):
    """Outward vertex normals of a closed CCW 2-D polygon (mitred: an offset d * N moves the edges by d)."""
    e0 = Q - np.roll(Q, 1, 0)
    e1 = np.roll(Q, -1, 0) - Q
    n0 = np.c_[e0[:, 1], -e0[:, 0]]
    n1 = np.c_[e1[:, 1], -e1[:, 0]]
    n0 /= np.maximum(np.linalg.norm(n0, axis=1, keepdims=True), 1e-12)
    n1 /= np.maximum(np.linalg.norm(n1, axis=1, keepdims=True), 1e-12)
    m = n0 + n1
    m /= np.maximum(np.linalg.norm(m, axis=1, keepdims=True), 1e-12)
    c = np.maximum(np.sum(m * n1, 1), 0.35)
    return m / c[:, None]


def _ccw(Q):
    Q = np.asarray(Q, float)
    a = 0.5 * np.sum(Q[:, 0] * np.roll(Q[:, 1], -1) - np.roll(Q[:, 0], -1) * Q[:, 1])
    return Q if a > 0 else Q[::-1]


def slab(fr, Q, c0, c1, r, top, rim=None, bottom=None, nr=2):
    """Rounded plate: the 2-D outline Q (frame u, v) extruded along w from c0 to c1 with every edge rounded (radius r;
    outline corner radii must be >= r).  Returns [(Mesh, material)]: top cap (+w), rim, bottom cap (-w)."""
    Q = _ccw(Q)
    N = _normals2(Q)
    t = c1 - c0
    r = min(r, 0.49 * t)
    if r > 1e-6:
        rows = [(Q - r * N + r * math.cos(ph) * N, c0 + r + r * math.sin(ph)) for ph in np.linspace(-0.5 * np.pi, 0.0,
                                                                                                  nr + 1)]
        rows += [(Q - r * N + r * math.cos(ph) * N, c1 - r + r * math.sin(ph)) for ph in np.linspace(0.0, 0.5 * np.pi,
                                                                                                   nr + 1)]
    else:
        rows = [(Q, c0), (Q, c1)]
    P = np.array([fr.p(R2[:, 0], R2[:, 1], c) for R2, c in rows])
    rm = grid_surface(P, close_v=True)
    cen = fr.p(Q[:, 0].mean(), Q[:, 1].mean(), 0.5 * (c0 + c1))
    rm = _oriented(rm, lambda C: C - cen)
    out = [(rm, rim or top)]
    R2, c = rows[-1]
    out.append((fr.poly(R2, c), top))
    if bottom is not False:
        R2, c = rows[0]
        m = planar_cap(fr.p(R2[:, 0], R2[:, 1], c), -fr.w)
        out.append((_oriented(m, -fr.w), bottom or rim or top))
    return out


def prism(fr, Q, c0, c1, mat, caps=True):
    """Crisp (flat-shaded) extrusion of the closed outline Q (frame u, v) along w from c0 to c1."""
    Q = _ccw(Q)
    out = []
    n = len(Q)
    for i in range(n):
        a, b = Q[i], Q[(i + 1) % n]
        V = np.array([fr.p(a[0], a[1], c0), fr.p(b[0], b[1], c0), fr.p(b[0], b[1], c1), fr.p(a[0], a[1], c1)])
        m = Mesh(V, np.array([[0, 1, 2], [0, 2, 3]]))
        nrm = (b[1] - a[1]) * fr.u - (b[0] - a[0]) * fr.v
        out.append((_oriented(m, nrm), mat))
    if caps:
        out.append((fr.poly(Q, c1), mat))
        out.append((_oriented(planar_cap(fr.p(Q[:, 0], Q[:, 1], c0), -fr.w), -fr.w), mat))
    return out


def ring_face(fr, Qo, Qi, c):
    """Flat annulus between two outlines with the same point count (frame u, v) at w = c, facing +w."""
    A = fr.p(Qo[:, 0], Qo[:, 1], c)
    B = fr.p(Qi[:, 0], Qi[:, 1], c)
    return _oriented(_strip(A, B, closed=True), fr.w)


class _Acc:
    """Mesh accumulator keyed by (group, material)."""

    def __init__(self):
        self.d = defaultdict(list)
        self.group = "misc"

    def add(self, m, mat=None):
        if m is None:
            return
        if isinstance(m, list):
            for item in m:
                if isinstance(item, tuple):
                    self.add(item[0], item[1] if mat is None else mat)
                else:
                    self.add(item, mat)
            return
        if len(m.F):
            self.d[(self.group, mat)].append(m)


def _seats(layout):
    return [r for r in I.seat_map(layout) if not r.get("crew")]


def _head_x(rec):
    """Head-centre station of the (95th-pct) occupant of a cabin seat record."""
    return float(I.cabin_pose(rec)["head_c"][0])


# =====================================================================================================================
# floor: carpet + panel edges, aisle runner, seat tracks
# =====================================================================================================================
def _floor_stations(x0, x1, dx=0.05, extra=()):
    xs = np.r_[np.arange(x0, x1, dx), x1, [e for e in extra if x0 < e < x1]]
    xs = np.unique(np.round(xs, 6))
    return xs[np.r_[True, np.diff(xs) > 1e-4]]


def _floor(acc):
    acc.group = "floor"
    L = lining()
    wx0, wx1 = (float(v) for v in I.FLOOR["wing_x"])
    t_std, t_wing = float(I.FLOOR["t"]), float(I.FLOOR["t_wing"])
    xs = np.unique(np.r_[_floor_stations(XA, 8.95, 0.25, (wx0, wx1)), _floor_stations(8.95, XB, 0.05, (9.0, XP))])
    w = L.hw(xs, FL + 0.002) - 0.001
    ny = 17
    u = np.linspace(-1.0, 1.0, ny)
    top = np.stack([np.repeat(xs[:, None], ny, 1), w[:, None] * u[None, :], np.full((len(xs), ny), FL)], -1)
    acc.add(_oriented(grid_surface(top), [0, 0, 1.0]), "carpet")
    # underside (steps to t_wing over the carry-through: the carry-through top is <= floor - 15 mm) and edges
    xu = np.unique(np.r_[xs, wx0 - 1e-4, wx1 + 1e-4])
    wu = L.hw(xu, FL + 0.002) - 0.001
    tu = np.where((xu >= wx0) & (xu <= wx1), t_wing, t_std)
    bot = np.stack([np.repeat(xu[:, None], ny, 1), wu[:, None] * u[None, :], np.repeat((FL - tu)[:, None], ny, 1)], -1)
    acc.add(_oriented(grid_surface(bot), [0, 0, -1.0]), "floor_panel")
    for sg in (-1, 1):
        A = np.c_[xu, sg * wu, np.full(len(xu), FL)]
        B = np.c_[xu, sg * wu, FL - tu]
        acc.add(_oriented(_strip(A, B), [0, sg, 0]), "carpet")
    for x, t_, nx in ((XA, t_std, -1.0), (XB, t_std, 1.0)):
        ww = float(L.hw(x, FL + 0.002)) - 0.001
        A = np.c_[np.full(ny, x), ww * u, np.full(ny, FL)]
        B = np.c_[np.full(ny, x), ww * u, np.full(ny, FL - t_)]
        acc.add(_oriented(_strip(A, B), [nx, 0, 0]), "carpet")


def _runner(acc):
    """Aisle runner: broad angular bands in lanes along the aisle (AI Orange runner [M]: P1046402 / 04 / 06 -- orange
    and cream blocks 50-85 mm wide that fill most of the runner, their edges stepping in and out on short 45-deg
    diagonals, the ends cut at an angle, on the navy striped carpet; final judge r1 I3: the old 18-42 mm lines on
    black read as thin pinstripes); the pattern is procedural (seeded random widths / steps / lengths per lane, RUNNER),
    not traced from a photo.  Every band stays inside its own lane (less half the navy gap), and inside a lane both
    edges stay within a lane narrower than two minimum widths, so the edges never cross and no two bands overlap
    (fit_check 26: no coplanar overlaps of different materials)."""
    acc.group = "runner"
    hw, seed = DETAIL["runner"]
    q = RUNNER
    rng = np.random.default_rng(seed)
    n = int(q["lanes"])
    edges = np.linspace(-hw, hw, n + 1)
    z = FL + 0.0008
    x_end = XP - 0.04
    mats = [m for m, _ in q["mix"]]
    wts = np.array([w for _, w in q["mix"]], float)
    wts /= wts.sum()
    w0, w1 = q["width"]
    for k in range(n):
        a, b = edges[k] + 0.5 * q["gap"], edges[k + 1] - 0.5 * q["gap"]      # the lane, less half the navy gap
        assert b - a < 2.0 * w0, "RUNNER: lane too wide for crossing-free steps"
        x = XA + 0.03 + rng.uniform(0.0, 0.20)
        while x < x_end - 0.30:
            x1 = min(x + rng.uniform(*q["length"]), x_end)
            mat = mats[int(rng.choice(len(mats), p=wts))]
            ns = int(rng.integers(1, 4)) if x1 - x > 0.6 else 0              # steps along the band
            xs = []
            for xx in np.sort(rng.uniform(x + 0.20, x1 - 0.25, ns)) if ns else ():
                if not xs or xx - xs[-1] > 0.15:
                    xs.append(float(xx))
            yl, yr = [], []
            for _ in range(len(xs) + 1):
                w = min(rng.uniform(w0, w1), b - a)
                c = rng.uniform(a + 0.5 * w, b - 0.5 * w)
                yl.append(c - 0.5 * w)
                yr.append(c + 0.5 * w)
            lo, hi = [], []
            c0 = rng.uniform(*q["end_cut"]) * rng.choice([-1.0, 1.0])            # angled ends
            lo.append((x - min(c0, 0.0) * (yr[0] - yl[0]), yl[0]))
            hi.append((x + max(c0, 0.0) * (yr[0] - yl[0]), yr[0]))
            for j, xx in enumerate(xs):
                for ys, lst in ((yl, lo), (yr, hi)):
                    d = abs(ys[j + 1] - ys[j]) * q["step_slope"]
                    if d > 1e-4:
                        lst.append((xx, ys[j]))
                        lst.append((xx + d, ys[j + 1]))
            c1 = rng.uniform(*q["end_cut"]) * rng.choice([-1.0, 1.0])
            lo.append((x1 - max(c1, 0.0) * (yr[-1] - yl[-1]), yl[-1]))
            hi.append((x1 + min(c1, 0.0) * (yr[-1] - yl[-1]), yr[-1]))
            P = np.array(lo + hi[::-1])
            acc.add(_oriented(planar_cap(np.c_[P, np.full(len(P), z)], [0, 0, 1.0]), [0, 0, 1.0]), mat)
            x = x1 + rng.uniform(*q["break"])


def _tracks(acc):
    """The four surface-mounted seat tracks (SEAT_TRACKS): a low channel with the locating-slot lips."""
    acc.group = "tracks"
    st = I.SEAT_TRACKS
    x0, x1 = float(st["x0"]), float(st["x1"])
    w, h = float(st["w"]), float(st["h"])
    a, s = 0.5 * w, 0.005
    prof = np.array([(-a, 0.0), (a, 0.0), (a, h - 0.003), (a - 0.002, h), (s, h), (s, h - 0.006), (-s, h - 0.006),
                     (-s, h), (-a + 0.002, h), (-a, h - 0.003)])
    for b in st["bl"]:
        for sg in (-1, 1):
            fr = Fr([0.0, sg * float(b), FL], [0, 1.0, 0], [0, 0, 1.0], [1.0, 0, 0])
            acc.add(prism(fr, prof, x0, x1, "metal_dark"))
            yb, zs = sg * float(b), FL + h - 0.006 + 0.0004              # dark slot floor (locating holes)
            slot = np.array([(x0 + 0.005, yb - s, zs), (x1 - 0.005, yb - s, zs), (x1 - 0.005, yb + s, zs),
                             (x0 + 0.005, yb + s, zs)])
            acc.add(_oriented(planar_cap(slot, [0, 0, 1.0]), [0, 0, 1.0]), "black")


# =====================================================================================================================
# side ledges (+ cup holders, switch / USB plates), club tables
# =====================================================================================================================
def _cups_for(side, layout, x0, x1):
    """Cup-holder pair stations on this ledge run: LEDGES cupholder_dx ahead of each seat back on the side."""
    out = []
    for r in _seats(layout):
        if r["side"] != side:
            continue
        xc = float(r["rear"]) - r["facing"] * float(LG["cupholder_dx"])
        if x0 + 0.09 < xc < x1 - 0.09:
            out.append((xc, r["facing"]))
    return out


def _ledge_section(x, yo_top, yo_bot, z_bot=None):
    """Ledge section at station x (outboard-positive y, z): segments [(points, material)] fascia (+ rounded nose),
    lip under the fascia, kick panel to the floor edge, back against the lining; closed outline for the end caps.
    z_bot: the kick panel / back foot (default the floor FL; the cargo-door segment stands LEDGES door_foot above it)."""
    zb = FL if z_bot is None else float(z_bot)
    rn = DETAIL["nose_r"]
    fz = float(LG["fascia"])
    ki = DETAIL["kick_in"]
    yf = float(I.FLOOR["edge_bl"])
    arc = [(YI + rn + rn * math.cos(t), ZT - rn + rn * math.sin(t)) for t in np.radians(np.linspace(180, 90, 5))]
    fascia = np.array([(YI, ZT - fz), (YI, ZT - fz + 0.5 * (fz - rn))] + arc)
    lip = np.array([(YI - ki, ZT - fz), (YI, ZT - fz)])
    kick = np.array([(yf, zb), (0.5 * (yf + YI - ki), 0.5 * (zb + ZT - fz)), (YI - ki, ZT - fz)])
    back = np.array([(yo_top, ZT), (yo_bot, zb)])
    outline = np.vstack([lip, fascia[1:], back, kick[:-1]])
    return dict(fascia=fascia, lip=lip, kick=kick, back=back), outline


def _ledge_body(acc, side, xa, xb, yo_fn, dx=0.10):
    """Loft of the ledge section along x (the top face is built by _ledge_top)."""
    xs = _floor_stations(xa, xb, dx)
    secs = [_ledge_section(x, *yo_fn(x)) for x in xs]
    mats = dict(fascia=("gloss_black", (0, -side, 0.3)), lip=("ledge_panel", (0, 0, 1.0)),    # the kick panel
    #                                                        stands 3 mm proud of the fascia: its top faces up
                kick=("ledge_panel", (0, -side, 0)), back=("ledge_panel", (0, side, 0)))
    for key, (mat, d) in mats.items():
        P = np.array([[(x, side * p[0], p[1]) for p in s[0][key]] for x, s in zip(xs, secs)])
        acc.add(_oriented(grid_surface(P), d), mat)
    for x, (s, ol), nx in ((xs[0], secs[0], -1.0), (xs[-1], secs[-1], 1.0)):
        acc.add(_oriented(planar_cap(np.c_[np.full(len(ol), x), side * ol[:, 0], ol[:, 1]], [nx, 0, 0]), [nx, 0, 0]),
                "ledge_panel")


def _ledge_top(acc, side, xa, xb, yo_fn, cups):
    """Flat ledge top (ZT) from the fascia nose to the lining, with the figure-8 cup-holder recesses (brushed rims)
    and a switch / USB plate beside each pair."""
    rn = DETAIL["nose_r"]
    cr, cdx, cdep, crim = DETAIL["cup"]
    y0 = YI + rn
    # x pieces: coarse between the cup zones, fine (6 mm) round each cup pair
    zones = [(max(xc - 0.10, xa), min(xc + 0.10, xb), xc) for xc, _ in cups]
    cuts = [xa]
    for a, b, _ in zones:
        cuts += [a, b]
    cuts.append(xb)
    pieces = []
    for k in range(len(cuts) - 1):
        a, b = cuts[k], cuts[k + 1]
        if b - a < 1e-4:
            continue
        pieces.append((a, b, k % 2 == 1))
    for a, b, fine in pieces:
        if fine:
            xs = np.linspace(a, b, int(round((b - a) / 0.006)) + 1)
            nyp = 17
        else:
            xs = _floor_stations(a, b, 0.10)
            nyp = 3
        yo = np.array([yo_fn(x)[0] for x in xs])
        s = np.linspace(0.0, 1.0, nyp)
        Y = y0 + s[None, :] * (yo[:, None] - y0)
        P = np.stack([np.repeat(xs[:, None], nyp, 1), side * Y, np.full(Y.shape, ZT)], -1)
        m = _oriented(grid_surface(P), [0, 0, 1.0])
        if not fine:
            acc.add(m, "ledge_top")
            continue
        xc = 0.5 * (a + b)
        yc = side * 0.5 * (y0 + yo_fn(xc)[0])
        cen = [(xc - 0.5 * cdx, yc), (xc + 0.5 * cdx, yc)]

        def f(q, cen=cen):
            return np.min([np.hypot(q.V[:, 0] - cx, q.V[:, 1] - cy) for cx, cy in cen], axis=0) - cr
        mt = trim(m, f(m), "positive")
        acc.add(mt, "ledge_top")
        acc.add(band(mt, f, 0.0, crim).translated([0, 0, 0.0008]), "chrome_trim")
        for loop in boundary_loops(mt):
            Lv = mt.V[loop]
            if np.hypot(Lv[:, 0] - xc, Lv[:, 1] - yc).max() > 0.5 * cdx + cr + 0.012:
                continue                                             # the piece's outer boundary
            Bv = Lv - [0, 0, cdep]
            wall = _oriented(_strip(Lv - [0, 0, 0.004], Bv, closed=True),   # below the brushed lip (no overlap)
                             lambda C: np.c_[xc - C[:, 0], yc - C[:, 1], np.zeros(len(C))])
            acc.add(wall, "black")
            acc.add(_oriented(planar_cap(Bv, [0, 0, 1.0]), [0, 0, 1.0]), "black")
            # brushed rim lip down the recess wall
            acc.add(_oriented(_strip(Lv + [0, 0, 0.0008], Lv - [0, 0, 0.004], closed=True),
                              lambda C: np.c_[xc - C[:, 0], yc - C[:, 1], np.zeros(len(C))]), "chrome_trim")


def _ledge_fittings(acc, side, cups, yo_fn, wall_fn):
    """Switch / USB plate on the ledge top ahead of each cup pair, USB socket on the sidewall above (wall_fn(x, z):
    |BL| of the wall face: the lining, or the cargo door's inner face)."""
    ul, uw, ua = DETAIL["usb"]
    sw, sh, sz = DETAIL["wall_usb"]
    y0 = YI + DETAIL["nose_r"]
    for xc, facing in cups:
        xu = xc - facing * ua
        yu = 0.5 * (y0 + yo_fn(xu)[0])
        fr = Fr([xu, side * yu, ZT], [1.0, 0, 0], [0, 1.0, 0])
        acc.add(slab(fr, rrect2(-0.5 * ul, -0.5 * uw, 0.5 * ul, 0.5 * uw, 0.004), 0.0, 0.0018, 0.0008,
                     "chrome_trim", bottom=False))
        acc.add(fr.poly(rrect2(-0.5 * ul + 0.006, -0.5 * uw + 0.005, 0.5 * ul - 0.006, 0.5 * uw - 0.005, 0.002),
                        0.0021), "black")
        # USB socket on the sidewall lining above the ledge, by the seat (never over a window / door opening)
        xw = xc - facing * 0.05
        zw = ZT + sz
        if wall_fn is _wall_fixed and _over_opening(xw, zw, side, 0.5 * sw + 0.008):
            continue
        yw = wall_fn(xw, zw)
        dy = (wall_fn(xw, zw + 0.004) - wall_fn(xw, zw - 0.004)) / 0.008
        n = _unit([0.0, -side, dy])
        fw = Fr([xw, side * yw, zw] + 0.0005 * n, [1.0, 0, 0], np.cross(n, [1.0, 0, 0]), n)
        g0 = acc.group
        if wall_fn is _wall_fixed:                   # on the side-wall lining: goes with it (viewer cutaway, M3)
            acc.group = "wall_fittings"
        acc.add(slab(fw, rrect2(-0.5 * sw, -0.5 * sh, 0.5 * sw, 0.5 * sh, 0.004), 0.0, 0.004, 0.0015, "psu_panel",
                     bottom=False))
        acc.add(fw.poly(rrect2(-0.006, -0.004, 0.006, 0.004, 0.001), 0.0042), "black")
        acc.group = g0


def _ledge_run(acc, side, xa, xb, layout, tables, yo_fn, wall_fn):
    acc.group = "ledges"
    cups = _cups_for(side, layout, xa, xb)
    _ledge_body(acc, side, xa, xb, yo_fn)
    _ledge_top(acc, side, xa, xb, yo_fn, cups)
    _ledge_fittings(acc, side, cups, yo_fn, wall_fn)
    # stowed tables: the edge band in the fascia; deployed: the dark slot it came out of
    for key, state in tables.items():
        t = I.TABLES[key]
        if t["side"] != side:
            continue
        x0, x1 = (float(v) for v in t["x"])
        if not (xa <= x0 and x1 <= xb):
            continue
        z1 = FL + float(t["top_h"])
        z0 = z1 - float(t["t"])
        fr = Fr([0.5 * (x0 + x1), side * (YI - 0.0004), 0.5 * (z0 + z1)], [1.0, 0, 0], [0, 0, 1.0], [0, -side, 0])
        hx = 0.5 * (x1 - x0)
        # (final judge r1 R8: the inclined brushed strip on the kick panel under the table read as a loose rod hanging
        # in the ledge shadow, unattached at both ends in cabin_club -- dropped; the table's slide rails
        # (table_parts) show what carries it)
        if state == "stowed":
            # (0.5 mm inside the leaf's thickness: with the movable table out the band is inside it, review r3 K3)
            acc.add(slab(fr, rrect2(-hx + 0.003, -0.5 * (z1 - z0) + 0.0005, hx - 0.003, 0.5 * (z1 - z0) - 0.0005,
                                    0.002), 0.0, 0.0012, 0.0005, "veneer_walnut", bottom=False))
            acc.add(fr.poly(rrect2(-0.030, -0.004, 0.030, 0.004, 0.003), 0.0014), "black")     # finger pull
        else:
            acc.add(fr.poly(rrect2(-hx - 0.003, -0.5 * (z1 - z0) - 0.003, hx + 0.003, 0.5 * (z1 - z0) + 0.003,
                                   0.003), 0.0004), "black")


def _yo_fixed(x):
    L = lining()
    return float(L.hw(x, ZT)) - 0.0015, float(L.hw(x, FL + 0.003)) - 0.0015


def _wall_fixed(x, z):
    return float(lining().hw(x, z))


def _door_face_depth():
    """Depth of the cargo door's cabin face inside the skin: the slab (fuselage_parts DOOR_T) + its inner lining panel
    (INNER_BODY)."""
    from model.fuselage_parts import DOOR_T, INNER_BODY
    return DOOR_T + INNER_BODY["t"]


def _wall_door(x, z):
    return float(F.side_y(x, z)) - _door_face_depth() - 0.001


def _yo_door(x):
    """Cargo-door ledge: the outboard face on the door's inner lining panel; its kick-panel foot LEDGES door_foot above
    the carpet, clear of the sill jamb as the door swings open (fit_check 21)."""
    g = _door_face_depth() + 0.002
    zb = FL + float(LG["door_foot"])
    return float(F.side_y(x, ZT)) - g, float(F.side_y(x, zb)) - g, zb


def _ledges(acc, layout, tables, door_ledge):
    ds, da, db = LG["door_segment"]
    for side, xa, xb in LG["runs"]:
        xa, xb = float(xa), float(xb)
        if side == ds:
            # the fixed runs stop at the cargo door's clear opening (the door segment swings out through it, 10 mm
            # inside each edge: LEDGES door_segment)
            from model.fuselage_parts import CARGO
            spans = [(xa, CARGO["cx"] - CARGO["hx"] - 0.002), (CARGO["cx"] + CARGO["hx"] + 0.002, xb)]
            for a, b in spans:
                if b - a > 0.02:
                    _ledge_run(acc, side, a, b, layout, tables, _yo_fixed, _wall_fixed)
            if door_ledge:
                _ledge_run(acc, side, float(da), float(db), layout, tables, _yo_door, _wall_door)
        else:
            _ledge_run(acc, side, xa, xb, layout, tables, _yo_fixed, _wall_fixed)


def _table(acc, key, state):
    """Club table deployed (TABLES): the outboard leaf slid out of the ledge fascia below the cap ('leaf'), and the
    inboard leaf unfolded over the aisle ('deployed'): anthracite leaves with a thin wood edge round the gloss-black
    top, the carriage tray under the outboard leaf, the brushed hinge line and a folding bracket under the hinge."""
    acc.group = "tables"
    t = I.TABLES[key]
    s = int(t["side"])
    x0, x1 = (float(v) for v in t["x"])
    z1 = FL + float(t["top_h"])
    th = float(t["t"])
    z0 = z1 - th
    leaf = float(t.get("leaf", 0.5 * (YI - float(t["bl_in"]))))
    yh = YI - leaf                                                     # hinge line (outboard leaf's inner edge)
    r = DETAIL["table_r"]
    fr = Fr([0.0, 0.0, 0.0], [1.0, 0, 0], [0, 1.0, 0])
    leaves = [(yh + 0.0015, YI + 0.015)]                               # into the slot by 15 mm
    if state == "deployed":
        leaves.append((float(t["bl_in"]), yh - 0.0015))
    ro = r
    for ya, yb in leaves:
        a0, a1 = sorted((s * ya, s * yb))
        Q = rrect2(x0, a0, x1, a1, ro, 4)
        # anthracite leaf, the whole top dark smoked walnut under a gloss coat inside a thin dark-grey edge band
        # (P1046404 / 06; model judging r1 INT-m3: the rev F gloss-black inlay read as a black glass top)
        acc.add(slab(fr, Q, z0, z1, 0.004, "ledge_panel"))
        e0, e1 = sorted((s * (ya + 0.004), s * (min(yb, YI) - 0.004)))
        acc.add(fr.poly(rrect2(x0 + 0.004, e0, x1 - 0.004, e1, max(ro - 0.004, 0.004)), z1 + 0.0004),
                "veneer_walnut")
    # carriage tray under the outboard leaf, slid out of the fascia slot with it (anthracite [M]), hinge, bracket
    ya, yb = yh + 0.030, YI + 0.015
    a0, a1 = sorted((s * ya, s * yb))
    acc.add(slab(fr, rrect2(x0 + 0.012, a0, x1 - 0.012, a1, 0.008), z0 - 0.014, z0 - 0.0005, 0.003, "ledge_panel"))
    if state == "deployed":
        acc.add(cylinder([x0 + 0.03, s * yh, z0 + 0.004], [x1 - 0.03, s * yh, z0 + 0.004], 0.0045, n=10),
                "chrome_trim")
        xm = 0.5 * (x0 + x1)
        acc.add(prism(Fr([xm, s * (yh + 0.02), z0], [0, 1.0, 0], [0, 0, 1.0], [1.0, 0, 0]),
                      np.array([(-0.045, -0.050), (0.045, -0.050), (0.045, 0.0), (-0.045, 0.0)]), -0.009, 0.009,
                      "black"))


def table_parts(key):
    """Movable club table `key` (TABLES) for the viewer / renders (review r3 F5): (outboard [(Mesh, material)], leaf
    [(Mesh, material)], pivot, leaf_pivot), model coordinates.  The outboard leaf is built slid out of the ledge fascia
    (the 'leaf' state of P1046404 / 05 / 06) with the inboard leaf folded face-down under it about the hinge line at
    the leaf's underside (its unfolded 'deployed' place, brochure p.18, is 180 deg round that hinge).  Pivots (origin /
    axis model axes, written as glTF by assemble): 'table' -- open 0 stowed (slid outboard by `slide`, model axes, into
    the ledge: the viewer clips it at the fascia plane |BL| = fascia_bl, so it vanishes), 0.5 the leaf out (= the built
    rest), 1 deployed; 'table_leaf' -- the inboard leaf unfolds by `fold` rad about its axis over open 0.5 .. 1."""
    t = I.TABLES[key]
    s = int(t["side"])
    x0, x1 = (float(v) for v in t["x"])
    z1 = FL + float(t["top_h"])
    th = float(t["t"])
    z0 = z1 - th
    leaf = float(t.get("leaf", 0.5 * (YI - float(t["bl_in"]))))
    yh = YI - leaf                                                     # hinge line (outboard leaf's inner edge)
    r = DETAIL["table_r"]
    fr = Fr([0.0, 0.0, 0.0], [1.0, 0, 0], [0, 1.0, 0])

    def leaf_meshes(ya, yb, yin_b):
        acc = _Acc()
        a0, a1 = sorted((s * ya, s * yb))
        acc.add(slab(fr, rrect2(x0, a0, x1, a1, r, 4), z0, z1, 0.004, "ledge_panel"))
        e0, e1 = sorted((s * (ya + 0.004), s * (yin_b - 0.004)))
        acc.add(fr.poly(rrect2(x0 + 0.004, e0, x1 - 0.004, e1, max(r - 0.004, 0.004)), z1 + 0.0004), "veneer_walnut")
        return acc
    out = leaf_meshes(yh + 0.0015, YI + 0.015, YI)                     # into the slot by 15 mm
    out.add(cylinder([x0 + 0.03, s * yh, z0 + 0.0045], [x1 - 0.03, s * yh, z0 + 0.0045], 0.0045, n=10), "chrome_trim")
    lf = leaf_meshes(float(t["bl_in"]), yh - 0.0015, yh - 0.0015)
    hinge = np.array([0.5 * (x0 + x1), s * yh, z0 - 0.00025])          # folded: 0.5 mm under the outboard leaf
    # final judge r1 R8: the slide rails the table runs out of the ledge on (it had looked glued to the fascia edge):
    # two brushed rails under the folded leaf, from 30 mm inside the hinge line into the ledge slot
    rr_ = 0.0045
    zr = z0 - 0.00025 - th - rr_ + 0.0002
    for xr in (x0 + 0.055, x1 - 0.055):
        out.add(cylinder([xr, s * (yh + 0.030), zr], [xr, s * (YI + 0.015), zr], rr_, n=10), "chrome_trim")
        out.add(superellipsoid(np.array([xr, s * (yh + 0.036), zr]), (0.008, 0.006, 0.0055), (0.3, 0.3), nu=6, nv=10),
                "chrome_trim")                                          # rail stop
    axis = np.array([-s, 0.0, 0.0])

    def folded(ms):                                                    # 180 deg about the hinge: under the outboard leaf
        res = []
        for m, mat in ms:
            V = m.V - hinge
            V = np.c_[V[:, 0], -V[:, 1], -V[:, 2]] + hinge
            res.append((Mesh(V, m.F.copy()), mat))
        return res
    col = lambda a: _collect(a, False)                                 # noqa: E731
    pv = dict(kind="table", origin=tuple(hinge), axis=(1.0, 0.0, 0.0), slide=(0.0, -s * (leaf + 0.03), 0.0),
              fascia_bl=float(s * YI), rest=0.5, table=key,
              note="open 0 stowed (slid outboard into the ledge by slide, model axes; clipped at |BL| = fascia_bl), "
                   "0.5 leaf out (built), 1 deployed; the child table_leaf unfolds over 0.5 .. 1")
    lpv = dict(kind="table_leaf", origin=tuple(hinge), axis=tuple(axis), fold=math.pi, rest=0.0, table=key,
               note="the inboard leaf: built folded under the outboard leaf, unfolds by fold rad about axis")
    return col(out), folded(col(lf)), pv, lpv


# =====================================================================================================================
# cabinets LH / RH (veneer, upper + lower drawer on the aisle face)# =====================================================================================================================
# cabinets LH / RH (veneer, upper + lower drawer on the aisle face)
# =====================================================================================================================
def _vertical_block(xa, xb, y_in, side, z0, z1, r, rt, outboard, nz=10):
    """Veneer block standing on the floor: plan outline (xa .. xb) x (y_in .. lining) with the aisle corners rounded
    (r) and the top edge rounded (rt); the outboard side follows outboard(x, z) (the lining).  Returns (side mesh,
    top ring points (N, 3))."""
    zs = list(np.linspace(z0, z1 - rt, nz))
    es = [0.0] * nz
    for ph in np.linspace(0.0, 0.5 * np.pi, 5)[1:]:
        zs.append(z1 - rt + rt * math.sin(ph))
        es.append(rt * (1.0 - math.cos(ph)))
    rings = []
    nb = 6
    for z, e in zip(zs, es):
        pts = []
        xo = np.linspace(xa + e, xb - e, nb)
        yo = outboard(xo, z) - e
        pts += [(x, y) for x, y in zip(xo[::-1], yo[::-1])]           # outboard edge, aft -> fwd
        ce = max(r - e, 0.002)
        for (cx, cy, t0) in ((xa + r, y_in + r, 180.0), (xb - r, y_in + r, 270.0)):
            for tt in np.radians(np.linspace(t0, t0 + 90.0, 5)):
                pts.append((cx + ce * math.cos(tt), cy + ce * math.sin(tt)))
        P = np.array(pts)
        rings.append(np.c_[P[:, 0], side * P[:, 1], np.full(len(P), z)])
    G = np.array(rings)
    c = np.array([0.5 * (xa + xb), side * (y_in + 0.1), 0.5 * (z0 + z1)])
    m = _oriented(grid_surface(G, close_v=True), lambda C: np.c_[C[:, 0] - c[0], C[:, 1] - c[1], np.zeros(len(C))])
    return m, G[-1]


def _cabinet(acc, key):
    acc.group = "cabinets"
    L = lining()
    c = I.CABINETS[key]
    s = int(c["side"])
    xa, xb = (float(v) for v in c["x"])
    yin = float(c["bl_in"])
    zt = FL + float(c["h"])
    r, rt = DETAIL["cab_r"]
    m, top = _vertical_block(xa, xb, yin, s, FL, zt, r, rt, lambda x, z: L.hw(x, z) - 0.001)
    acc.add(m, "veneer_walnut")
    acc.add(_oriented(planar_cap(top, [0, 0, 1.0]), [0, 0, 1.0]), "veneer_walnut")
    # two drawer fronts on the aisle face, brushed latches; oval brushed rim + dark insert on the top
    fa = Fr([0.5 * (xa + xb), s * yin, FL], [1.0, 0, 0], [0, 0, 1.0], [0, -s, 0])
    hx = 0.5 * (xb - xa) - r - 0.004
    ds = DETAIL["drawer_split"]
    for b0, b1 in ((0.030, ds - 0.004), (ds + 0.004, float(c["h"]) - rt - 0.025)):
        acc.add(slab(fa, rrect2(-hx, b0, hx, b1, 0.004), -0.0005, 0.0022, 0.0012, "veneer_walnut", bottom=False))
        acc.add(slab(fa, rrect2(-0.022, b1 - 0.040, 0.022, b1 - 0.028, 0.004), 0.0022, 0.0062, 0.0015, "chrome_trim",
                     bottom=False))
    ft = Fr([0.5 * (xa + xb), s * 0.5 * (yin + float(L.hw(0.5 * (xa + xb), zt))), zt], [1.0, 0, 0], [0, 1.0, 0])
    Qo = ellipse2(0.0, 0.0, 0.055, 0.032, 32)
    Qi = ellipse2(0.0, 0.0, 0.048, 0.026, 32)
    acc.add(ring_face(ft, Qo, Qi, 0.0012), "chrome_trim")
    acc.add(ft.poly(Qi, 0.0006), "black")


# =====================================================================================================================
# lavatory (forward RH): inboard + aft walls, bi-fold doors, toilet cabinet (350), seat ring + open lid, padded shelf,
# lit niche, toilet-roll holder, white lining on the divider's aft face inside
# =====================================================================================================================
def _wall_yz_outline(x, y_in):
    """(y, z) outline of a full-height transverse wall at station x from |BL| y_in out to the lining, floor to the
    headliner / soffit (outboard-positive y; the outline runs floor-inboard -> floor-outboard -> up the lining ->
    across the ceiling -> down the inboard edge)."""
    S = I.lining_section(x, n=1441)
    k = len(S)
    st = S[:k // 2]                                                    # starboard, crown -> keel
    m = (st[:, 0] >= y_in + 0.002) & (st[:, 1] >= FL + 0.002)
    Q = st[m][::-1]                                                     # floor -> up the wall -> over to y_in
    Q = Q[::6] if len(Q) > 120 else Q
    Q = np.c_[Q[:, 0] - 0.001, np.minimum(Q[:, 1], ceiling(x, Q[:, 0]) - 0.001)]
    yb = float(lining().hw(x, FL + 0.002)) - 0.001
    zc = float(ceiling(x, y_in)) - 0.001
    return np.vstack([[(y_in, FL), (yb, FL)], Q, [(y_in, zc)]])


def _lavatory(acc, doors="closed"):
    acc.group = "lavatory"
    L = lining()
    lz = I.LAVATORY
    x0, x1 = (float(v) for v in lz["x"])
    yi = float(lz["inboard_bl"])
    tw = DETAIL["lav_wall"]
    d0, d1 = (float(v) for v in lz["door"])
    hz0, hz1 = DETAIL["lav_door_z"]
    zd = FL + hz1 + 0.003
    # ---- inboard wall (x0 .. x1 at BL yi .. yi + tw) with the door opening d0 .. d1, floor to zd
    xs_top = np.linspace(x1, x0, 14)
    ztop = ceiling(xs_top, yi) - 0.001
    out = np.vstack([[(x0, FL), (d0, FL), (d0, zd), (d1, zd), (d1, FL), (x1, FL)], np.c_[xs_top, ztop]])
    # the white inside face stops at the aft wall's inner face (x1 - tw): no white edge on the veneer corner (review
    # r1 C4)
    xs_w = np.linspace(x1 - tw, x0, 14)
    out_w = np.vstack([[(x0, FL), (d0, FL), (d0, zd), (d1, zd), (d1, FL), (x1 - tw, FL)],
                       np.c_[xs_w, ceiling(xs_w, yi + tw) - 0.001]])
    for y, nrm, mat, ol in ((yi, -1.0, "veneer_walnut", out), (yi + tw, 1.0, "lav_white", out_w)):
        acc.add(_oriented(planar_cap(np.c_[ol[:, 0], np.full(len(ol), y), ol[:, 1]], [0, nrm, 0]), [0, nrm, 0]),
                mat)
    n = len(out)
    for i in range(n):                          # edges: out is counter-clockwise in (x, z): outward = (dz, -dx)
        a, b = out[i], out[(i + 1) % n]
        if abs(a[1] - FL) < 1e-6 and abs(b[1] - FL) < 1e-6:
            continue                                                    # on the floor
        if abs(a[0] - x1) < 1e-6 and abs(b[0] - x1) < 1e-6:
            continue                                                    # under the aft wall's veneer face
        A = np.array([[a[0], yi, a[1]], [b[0], yi, b[1]]])
        acc.add(_oriented(_strip(A, A + [0, tw, 0]), [b[1] - a[1], 0.0, -(b[0] - a[0])]), "veneer_walnut")
    # ---- aft wall (x1 - tw .. x1, BL yi .. lining): white inside, veneer outside; white lav lining on the divider
    W = _wall_yz_outline(x1, yi)
    Ww = _wall_yz_outline(x1 - tw, yi + tw)                          # white inside face from the inboard wall's
    for x, nx, mat, ol in ((x1 - tw, -1.0, "lav_white", Ww), (x1, 1.0, "veneer_walnut", W)):   # inner face out
        acc.add(_oriented(planar_cap(np.c_[np.full(len(ol), x), ol[:, 0], ol[:, 1]], [nx, 0, 0]), [nx, 0, 0]), mat)
    # (its inboard edge lies in the inboard wall's veneer face, which runs on to x1: no separate edge strip)
    Wd = _wall_yz_outline(x0 + 0.001, yi + tw)
    acc.add(_oriented(planar_cap(np.c_[np.full(len(Wd), x0 + 0.001), Wd[:, 0], Wd[:, 1]], [1.0, 0, 0]),
                      [1.0, 0, 0]), "lav_white")
    # ---- bi-fold doors (two doors of two leaves each, hinged at the jambs)
    lf = float(lz["leaf"])
    dt = DETAIL["lav_door_t"]
    yc = yi + 0.5 * tw
    for xh, s_ in ((d0, 1.0), (d1, -1.0)):
        if doors == "ajar":                                           # the part-folded V drawn on the L6 plan
            p0 = np.array([xh, yc])
            ap = np.array([xh + s_ * 0.5 * lf, yi - 0.85 * lf])
            p2 = np.array([xh + s_ * lf, yc])
            segs = [(p0, ap), (ap, p2)]
        elif doors == "open":                                         # folded flat, standing out lf into the entry
            e = s_ * (dt + 0.003)
            segs = [(np.array([xh + 0.5 * e, yc]), np.array([xh + 0.5 * e, yc - lf])),
                    (np.array([xh + 1.5 * e, yc - lf]), np.array([xh + 1.5 * e, yc]))]
        else:
            segs = [(np.array([xh, yc]), np.array([xh + s_ * lf, yc])),
                    (np.array([xh + s_ * lf, yc]), np.array([xh + s_ * 2 * lf, yc]))]
        for k, (pa, pb) in enumerate(segs):
            d = pb - pa
            Lp = float(np.linalg.norm(d))
            u = np.array([d[0], d[1], 0.0]) / Lp
            w = s_ * np.cross(u, [0, 0, 1.0])                          # the aisle (veneer) face
            c = np.array([0.5 * (pa[0] + pb[0]), 0.5 * (pa[1] + pb[1]), FL])
            fr = Fr(c, u, [0, 0, 1.0], w)
            g = 0.0015
            Q = rrect2(-0.5 * Lp + g, hz0, 0.5 * Lp - g, hz1, 0.004)
            acc.add(slab(fr, Q, -0.5 * dt, 0.5 * dt, 0.003, "veneer_walnut", bottom="lav_white"))
            if k == 1:                                  # vertical pull on the aisle face, by the meeting edge
                a_ = 0.5 * Lp - 0.035
                for zz in (0.80, 1.05):
                    acc.add(cylinder(fr.p(a_, zz, 0.5 * dt), fr.p(a_, zz, 0.5 * dt + 0.022), 0.004, n=8),
                            "chrome_trim")
                acc.add(cylinder(fr.p(a_, 0.78, 0.5 * dt + 0.022), fr.p(a_, 1.07, 0.5 * dt + 0.022), 0.0065, n=12),
                        "chrome_trim")
    # ---- toilet cabinet along the outboard wall (cabinet x0 .. x1, depth, 350 height)
    cx0, cx1, cdep, cht = (float(v) for v in lz["cabinet"])
    bx = float(lz["bowl_x"])
    yo = float(L.hw(bx, FL + 0.3))
    yf = yo - cdep
    zc = FL + cht
    rr = 0.006
    ytop = float(L.hw(bx, zc)) - 0.001
    ybot = float(L.hw(bx, FL + 0.002)) - 0.001
    arc = [(yf + rr + rr * math.cos(t), zc - rr + rr * math.sin(t)) for t in np.radians(np.linspace(180, 90, 4))]
    sec = dict(front=(np.array([(yf, FL), (yf, zc - rr - 0.03)] + arc), "veneer_walnut"),
               top=(np.array([(yf + rr, zc), (ytop, zc)]), "lav_white"),
               back=(np.array([(ytop, zc), (ybot, FL)]), "lav_white"))
    cen = np.array([0.0, 0.5 * (yf + yo), 0.5 * (FL + zc)])
    for key, (pts, mat) in sec.items():
        P = np.array([[(x, p[0], p[1]) for p in pts] for x in (cx0, cx1)])
        acc.add(_oriented(grid_surface(P), lambda C: np.c_[np.zeros(len(C)), C[:, 1] - cen[1], C[:, 2] - cen[2]]),
                mat)
    ol = np.vstack([sec["front"][0], sec["top"][0][1:], sec["back"][0][1:]])
    for x, nx, mat in ((cx0, -1.0, "veneer_walnut"), (cx1, 1.0, "lav_white")):
        acc.add(_oriented(planar_cap(np.c_[np.full(len(ol), x), ol], [nx, 0, 0]), [nx, 0, 0]), mat)
    # front: drawer low on the toilet module, door on the shelf module, brushed latch / pull
    sx = float(lz["shelf_x"])
    ff = Fr([0.0, yf, FL], [1.0, 0, 0], [0, 0, 1.0], [0, -1.0, 0])
    acc.add(slab(ff, rrect2(cx0 + 0.09, 0.025, sx - 0.09, 0.115, 0.004), -0.0005, 0.0022, 0.0012, "veneer_walnut",
                 bottom=False))
    acc.add(slab(ff, rrect2(0.5 * (cx0 + sx) - 0.016, 0.085, 0.5 * (cx0 + sx) + 0.016, 0.105, 0.004), 0.0022,
                 0.0060, 0.0015, "chrome_trim", bottom=False))
    acc.add(slab(ff, rrect2(sx + 0.006, 0.020, cx1 - 0.006, cht - 0.035, 0.004), -0.0005, 0.0022, 0.0012,
                 "veneer_walnut", bottom=False))
    acc.add(slab(ff, rrect2(sx + 0.030, cht - 0.070, cx1 - 0.030, cht - 0.058, 0.005), 0.0022, 0.0062, 0.0015,
                 "chrome_trim", bottom=False))
    # seat ring (white, rounded section) with the bowl opening; open lid standing against the outboard wall
    rl, rw = (float(v) for v in lz["seat_ring"])
    tyo = float(L.hw(bx, FL + 0.3))
    yr = tyo - float(lz["seat_back"]) - 0.5 * rw
    rh = DETAIL["ring_h"]
    phi = np.linspace(0.0, 2 * np.pi, 48, endpoint=False)
    so = np.linspace(0.0, 1.0, 7)
    oi = np.c_[bx + 0.30 * rl * np.cos(phi), yr + 0.01 + 0.28 * rw * np.sin(phi)]
    oo = np.c_[bx + 0.5 * rl * np.cos(phi), yr + 0.5 * rw * np.sin(phi)]
    G = np.array([[np.r_[oi[j] + s * (oo[j] - oi[j]), zc + 0.0005 + rh * math.sin(math.pi * s) ** 0.6]
                   for s in so] for j in range(len(phi))])
    acc.add(_oriented(grid_surface(G, close_u=True), [0, 0, 1.0]), "toilet_white")
    acc.add(_oriented(planar_cap(np.c_[oi, np.full(len(oi), zc + 0.0006)], [0, 0, 1.0]), [0, 0, 1.0]), "toilet_bowl")
    ll, lt, lg_ = DETAIL["lid"]
    fl_ = Fr([bx, tyo - lg_ - 0.5 * lt, zc], [1.0, 0, 0], [0, 0, 1.0], [0, -1.0, 0])
    Ql = rrect2(-0.5 * rl - 0.02, 0.004, 0.5 * rl + 0.02, ll, 0.03)
    acc.add(slab(fl_, Ql, -0.5 * lt, 0.5 * lt, 0.006, "lav_grey"))
    acc.add(fl_.poly(rrect2(-0.5 * rl + 0.004, 0.030, 0.5 * rl - 0.004, ll - 0.024, 0.012), 0.5 * lt + 0.0006),
            "toilet_white")
    acc.add(cylinder(fl_.p(-0.5 * rl, 0.008, 0.5 * lt + 0.004), fl_.p(0.5 * rl, 0.008, 0.5 * lt + 0.004), 0.004, n=8),
            "chrome_trim")
    # padded shelf on the aft module (L6 plan rectangle)
    ysx = float(L.hw(sx, FL + 0.3))
    Qp = rrect2(sx + 0.015, ysx - cdep + 0.03, cx1 - 0.012, ysx - 0.02, 0.02)
    acc.add(slab(Fr([0, 0, 0], [1.0, 0, 0], [0, 1.0, 0]), Qp, zc, zc + DETAIL["pad_t"], 0.012, "upholstery_grey"))
    # lit niche in the outboard wall above the shelf: white surround proud of the lining, light along its top
    n0, n1 = (float(v) for v in lz["niche"])
    xn0, xn1 = sx + 0.015, cx1 - 0.015
    zn0, zn1 = FL + n0, FL + n1
    xm, zm = 0.5 * (xn0 + xn1), 0.5 * (zn0 + zn1)
    yn = float(min(L.hw(x, z) for x in (xn0, xn1) for z in (zn0, zn1))) - 0.0015
    fn = Fr([xm, yn, zm], [1.0, 0, 0], [0, 0, 1.0], [0, -1.0, 0])
    rim, dep = DETAIL["niche_rim"]
    hxn, hzn = 0.5 * (xn1 - xn0), 0.5 * (zn1 - zn0)
    Qi = rrect2(-hxn, -hzn, hxn, hzn, 0.02, 5)
    Qo = rrect2(-hxn - rim, -hzn - rim, hxn + rim, hzn + rim, 0.02 + rim, 5)
    acc.add(ring_face(fn, Qo, Qi, dep), "lav_white")
    for Q, sgn in ((Qo, 1.0), (Qi, -1.0)):
        A, B = fn.p(Q[:, 0], Q[:, 1], 0.0), fn.p(Q[:, 0], Q[:, 1], dep)
        cq = fn.p(0.0, 0.0, 0.5 * dep)
        acc.add(_oriented(_strip(A, B, closed=True), lambda C, s=sgn: s * (C - cq)), "lav_white")
    acc.add(fn.poly(Qi, 0.0005), "lav_white")
    lb = Fr(fn.p(0.0, hzn - 0.003, 0.5 * dep), fn.u, fn.w, -fn.v)     # light bar under the niche top, facing down
    acc.add(lb.poly(rrect2(-hxn + 0.010, -0.5 * dep + 0.002, hxn - 0.010, 0.5 * dep - 0.002, 0.002), 0.0),
            "light_cove")
    # toilet-roll holder on the aft wall (inside face): back plate, spindle, roll, cover flap
    tr, tlen = DETAIL["tp"]
    ytp = max(float(lz["tp_holder"][0]), yi + tw + 0.004 + 0.5 * tlen)
    ztp = FL + float(lz["tp_holder"][1])
    xw = x1 - tw
    xr = xw - 0.012 - tr
    fb = Fr([xw, ytp, ztp], [0, 1.0, 0], [0, 0, 1.0], [-1.0, 0, 0])
    acc.add(slab(fb, rrect2(-0.5 * tlen - 0.012, -0.030, 0.5 * tlen + 0.012, 0.080, 0.008), 0.0, 0.006, 0.002,
                 "lav_grey", bottom=False))
    acc.add(cylinder([xr, ytp - 0.5 * tlen, ztp], [xr, ytp + 0.5 * tlen, ztp], tr, n=24), "toilet_white")
    for sg in (-1, 1):
        acc.add(disk([xr, ytp + sg * (0.5 * tlen + 0.0005), ztp], [0, sg, 0], 0.020, n=16), "lav_grey")
    ya_ = ytp - 0.5 * tlen - 0.006
    acc.add(cylinder([xw - 0.004, ya_, ztp], [xr, ya_, ztp], 0.006, n=10), "lav_grey")            # arm
    acc.add(cylinder([xr, ya_, ztp], [xr, ytp + 0.5 * tlen - 0.004, ztp], 0.005, n=8), "lav_grey")  # spindle
    p0 = np.array([xw - 0.006, ytp, ztp + 0.078])                      # cover flap: wall -> over the roll front
    p1 = np.array([xr - tr - 0.012, ytp, ztp + tr + 0.016])
    fc = Fr(p0, [0, 1.0, 0], p1 - p0)
    fl_len = float(np.linalg.norm(p1 - p0))
    acc.add(slab(fc, rrect2(-0.5 * tlen - 0.012, 0.0, 0.5 * tlen + 0.012, fl_len, 0.010), -0.002, 0.002, 0.0015,
                 "lav_grey"))
    # downlight on the headliner inside the lav
    xl, yl = 0.5 * (x0 + x1), 0.45
    zl = float(L.crown(xl, yl))
    nl = L.head_normal(xl, yl)
    _downlight(acc, np.array([xl, yl, zl]), nl, 0.026, *DETAIL["fit_proud"])


# =====================================================================================================================
# headliner: flat centre panel, soffits with the LED coves and downlights, PSUs, oxygen flaps, exit PULL cover
# =====================================================================================================================
def _headliner(acc, layout, o2=True):
    acc.group = "headliner"
    L = lining()
    y0s = 0.5 * float(I.LINING["headliner_flat"])
    dd, y2s = (float(v) for v in I.LINING["soffit"])
    xe = XP - 0.5 * float(I.BAGGAGE["header_t"])
    xs = _floor_stations(XA, xe, 0.25, (9.0, 9.1, 9.2))
    # flat centre panel (flush with the lining where the lining is lower)
    ny = 25
    ys = np.linspace(-y0s, y0s, ny)
    zf = L.crown(xs, 0.0) - float(I.LINING["flat_drop"])
    Z = np.minimum(zf[:, None], L.crown(xs[:, None], ys[None, :]) - 0.002)
    P = np.stack([np.repeat(xs[:, None], ny, 1), np.repeat(ys[None, :], len(xs), 0), Z], -1)
    acc.add(_oriented(grid_surface(P), [0, 0, -1.0]), "lining")
    for i, nx in ((0, -1.0), (-1, 1.0)):
        A = P[i]
        B = np.c_[A[:, 0], A[:, 1], L.crown(A[:, 0], A[:, 1]) + 0.004]
        acc.add(_oriented(_strip(A, B), [nx, 0, 0]), "lining")
    # soffit bands (model judging r1 INT-M2, LINING soffit; P1046402 / 04 / 06): the step down from the raised channel
    # (lining white, an LED strip along its top washing the channel) and the straight band from the step's foot to
    # the curved side lining; downlights and PSU pods on the band
    ch = DETAIL["cove_h"]
    nb = 9
    for sg in (-1, 1):
        yb = np.linspace(y0s, y2s, nb)
        Zb = soffit_band(xs[:, None], yb[None, :])
        band = np.stack([np.repeat(xs[:, None], nb, 1), sg * np.repeat(yb[None, :], len(xs), 0), Zb], -1)
        zt = L.crown(xs, y0s)
        zs0 = Zb[:, 0]
        step = np.stack([np.stack([xs, np.full_like(xs, sg * y0s), zt + 0.004], -1),
                         np.stack([xs, np.full_like(xs, sg * y0s), zt - ch], -1),
                         np.stack([xs, np.full_like(xs, sg * y0s), zs0], -1)], 1)
        led = np.stack([np.stack([xs, np.full_like(xs, sg * (y0s - 0.0006)), zt - 0.0005], -1),
                        np.stack([xs, np.full_like(xs, sg * (y0s - 0.0006)), zt - ch], -1)], 1)
        acc.add(_oriented(grid_surface(step), [0, -sg, 0]), "lining")
        acc.add(_oriented(grid_surface(led), [0, -sg, 0]), "light_cove")
        acc.add(_oriented(grid_surface(band), [0, 0, -1.0]), "lining")
        for i, nx in ((0, -1.0), (-1, 1.0)):                 # end caps: step + band below, the lining above
            yl = np.linspace(y2s, y0s, nb)
            top = np.c_[np.full(nb, xs[i]), sg * yl, L.crown(xs[i], yl) + 0.004]
            ring = np.vstack([step[i][2:3], band[i][1:], top])
            acc.add(_oriented(planar_cap(ring, [nx, 0, 0]), [nx, 0, 0]), "lining")
        # downlights along the band: a short chrome bezel set into the band along its normal, and the lens
        pitch, rdl, yd = DETAIL["downlight"]
        pr, sk = DETAIL["fit_proud"]
        for x in np.arange(XA + 0.30, xe - 0.10, pitch):
            _downlight(acc, np.array([x, sg * yd, float(soffit_band(x, yd))]), band_normal(x, sg), rdl, pr, sk)
    # PSU per seat (reading light + gasper pod on the soffit band at psu_bl, over the lap)
    pl, pw, ph, pdx = DETAIL["psu"]
    ybl = float(I.LINING["psu_bl"])
    o2l, o2w, o2z = DETAIL["o2"]
    for r in _seats(layout):
        s = r["side"]
        f_ = r["facing"]
        x = _head_x(r) - f_ * pdx
        y = s * ybl
        z = float(soffit_band(x, ybl))
        n = band_normal(x, s)
        fr = Fr([x, y, z] - 0.003 * n, [1.0, 0, 0], np.cross(n, [1.0, 0, 0]), n)
        # light satin silver-white pod (P1046402 / 06; model judging r1 INT-m4: the metallic 'panel_silver' read as a
        # black box under the cabin light)
        acc.add(slab(fr, rrect2(-0.5 * pl, -0.5 * pw, 0.5 * pl, 0.5 * pw, 0.022, 5), 0.0, ph + 0.003, 0.004,
                     "psu_housing"))
        top = ph + 0.003
        a_read = -f_ * 0.05                                              # reading light toward the seat front
        acc.add(fr.disk(a_read, 0.0, 0.022, top + 0.0004, 24, r_inner=0.017), "chrome_trim")
        acc.add(fr.se(a_read, 0.0, top, (0.017, 0.017, 0.004), (0.6, 0.6), (6, 16)), "light_reading")
        acc.add(fr.disk(-a_read, 0.0, 0.022, top + 0.0004, 24, r_inner=0.017), "chrome_trim")
        acc.add(fr.se(-a_read, 0.0, top + 0.002, (0.014, 0.014, 0.010), (0.8, 0.8), (6, 16)), "metal_dark")
        acc.add(fr.disk(-a_read, 0.0, 0.005, top + 0.0121, 12), "black")          # gasper nozzle, on the ball
        # oxygen-mask flap on the upper sidewall above the seat (optional system [S: AFMS]); not over an opening
        if o2 and not _over_opening(x, o2z, s, 0.5 * o2l + 0.05):
            yw = float(L.hw(x, o2z))
            nw = L.wall_normal(x, o2z, s)
            fw = Fr([x, s * yw, o2z], [1.0, 0, 0], np.cross(nw, [1.0, 0, 0]), nw)
            _flush_door(acc, fw, s, o2l, o2w, 0.012, notch=True)
    # exit-release PULL cover above the over-wing exit (starboard) with its red label
    from model.fuselage_parts import EXIT
    wl_, hl_, dz_ = DETAIL["pull"]
    s = int(EXIT["side"])
    xe_ = float(EXIT["cx"])
    zp = float(EXIT["cz"] + EXIT["hz"]) + dz_
    yw = float(L.hw(xe_, zp))
    nw = L.wall_normal(xe_, zp, s)
    fw = Fr([xe_, s * yw, zp], [1.0, 0, 0], np.cross(nw, [1.0, 0, 0]), nw)
    top = _flush_door(acc, fw, s, wl_, hl_, 0.014, lift=0.0035)
    acc.add(_conform(fw.poly(rrect2(-0.5 * wl_ + 0.015, 0.5 * hl_ - 0.040, -0.5 * wl_ + 0.055, 0.5 * hl_ - 0.020,
                                    0.003), top + 0.0004), fw, s), "placard_red")


def _flush_door(acc, fw, s, lx, ly, r, lift=0.0006, notch=False):
    """A closed lining door (oxygen-mask door, exit-release cover) on the side-wall lining in frame fw (w = the wall
    normal): a dark gap RING (psu_panel, GAP wide) standing DETAIL fit_proud in front of the lining with walls down into
    it, and inside it the lining-coloured door, its face `inset` below the ring's top (a shallow-inset square: from any
    angle the ring's near edge is not hidden by the door, so the dark outline shows on all four sides) -- or, with
    lift > 0 and no inset, a raised cover lift above the ring; (notch) its finger notch; everything bent onto the curved
    wall (_conform).  Review r2 C2 / F5: the old frame sat 1.5 mm proud UNDER a door 2-5 mm proud, so only its far edge
    showed.  Returns the door's face height (c)."""
    gap, inset = 0.0025, 0.0004
    pr, sk = DETAIL["fit_proud"]
    top = pr + 0.0002
    Qo = _ccw(rrect2(-0.5 * lx - gap, -0.5 * ly - gap, 0.5 * lx + gap, 0.5 * ly + gap, r + gap, 4))
    Qi = _ccw(rrect2(-0.5 * lx, -0.5 * ly, 0.5 * lx, 0.5 * ly, r, 4))
    ring = [(ring_face(fw, Qo, Qi, top), "psu_panel"),
            (_oriented(_strip(fw.p(Qo[:, 0], Qo[:, 1], -sk), fw.p(Qo[:, 0], Qo[:, 1], top), closed=True),
                       lambda C: C - fw.o), "psu_panel"),
            (_oriented(_strip(fw.p(Qi[:, 0], Qi[:, 1], top), fw.p(Qi[:, 0], Qi[:, 1], -sk), closed=True),
                       lambda C: fw.o - C), "psu_panel")]
    acc.add(_conform(ring, fw, s))
    face = top - inset if lift <= 0.001 else top + lift
    Qd = rrect2(-0.5 * lx + 0.0003, -0.5 * ly + 0.0003, 0.5 * lx - 0.0003, 0.5 * ly - 0.0003, r - 0.0003, 4)
    acc.add(_conform(slab(fw, Qd, -sk, face, min(0.0003, 0.3 * (face + sk)), "lining", bottom=False), fw, s))
    if notch:
        acc.add(_conform(fw.poly(rrect2(-0.015, -0.5 * ly + 0.004, 0.015, -0.5 * ly + 0.012, 0.003), face + 0.0010),
                         fw, s), "psu_panel")          # 1 mm: the door's flat face chords sag ~0.3 mm (r3 check)
    return face


def _downlight(acc, p, n, r, pr, sk):
    """Round downlight at the lining / soffit point p with the into-cabin normal n: a chrome bezel cylinder from sk
    inside the surface to pr in front of it, its lens 0.2 mm proud of the bezel face."""
    n = np.asarray(n, float) / np.linalg.norm(n)
    acc.add(cylinder(p - sk * n, p + pr * n, r, n=20), "chrome_trim")
    acc.add(disk(p + (pr + 0.0002) * n, n, 0.75 * r, n=16), "light_reading")


def _over_opening(x, z, side, margin):
    """True when (x, z) on `side` lies over (or within margin of) a door / exit / window opening."""
    from model import fuselage_parts as FP
    for r in FP.openings_table():
        if r["side"] != side:
            continue
        if r["kind"] == "window":
            if abs(x - r["cx"]) < FP.WIN_HX + margin and abs(z - FP.WIN_CZ) < FP.WIN_HZ + margin:
                return True
        else:
            pan = r.get("panel")
            if pan and pan["x0"] - margin < x < pan["x1"] + margin and pan["z0"] - margin < z < pan["z1"] + margin:
                return True
    return False


# =====================================================================================================================
# FR34 partition: veneer arch header, curtain rod, pleated curtain (PRO) or luggage net; return-air grille
# =====================================================================================================================
def _arch(x, zr):
    """Lining section at x above WL zr as one polyline from the port wall over the crown to the starboard wall."""
    S = I.lining_section(x, n=1441)
    k = len(S)
    st = S[:k // 2]
    st = st[st[:, 1] >= zr]                                            # crown -> down to zr (y increasing)
    yz = float(np.interp(zr, S[:k // 2][::-1, 1], S[:k // 2][::-1, 0]))
    st = np.vstack([st[::4], [(yz, zr)]])
    port = st[::-1] * [-1.0, 1.0]
    return np.vstack([port, st[1:]])


def _partition(acc, kind):
    acc.group = "partition"
    L = lining()
    bg = I.BAGGAGE
    ht = float(bg["header_t"])
    zr = FL + float(bg["bar_h"])
    xa, xb = XP - 0.5 * ht, XP + 0.5 * ht
    # veneer arch header: the section above the rod, straight lower edge
    A = _arch(XP, zr)
    A = np.c_[A[:, 0] * 0.999, np.minimum(A[:, 1], ceiling(XP, A[:, 0]) - 0.001)]
    for x, nx in ((xa, -1.0), (xb, 1.0)):
        acc.add(_oriented(planar_cap(np.c_[np.full(len(A), x), A], [nx, 0, 0]), [nx, 0, 0]), "veneer_walnut")
    E = np.array([[xa, A[0, 0], zr], [xa, A[-1, 0], zr]])
    acc.add(_oriented(_strip(E, E + [ht, 0, 0]), [0, 0, -1.0]), "veneer_walnut")
    # rod just under the header, wall to wall
    zrod = zr - 0.010
    hr = float(L.hw(XP, zrod + DETAIL["rod_r"] + 0.004)) - 0.002          # wall brackets clear of the lining
    acc.add(cylinder([XP, -hr, zrod], [XP, hr, zrod], DETAIL["rod_r"], n=14), "chrome_trim")
    for sg in (-1, 1):
        acc.add(cylinder([XP, sg * (hr - 0.012), zrod], [XP, sg * (hr + 0.001), zrod], DETAIL["rod_r"] + 0.004,
                         n=14), "chrome_trim")
    # return-air grille on the flat panel just ahead of the header
    gw, gl = DETAIL["grille"]
    xg = xa - 0.5 * gl - 0.03
    zg = float(L.crown(xg, 0.0)) - float(I.LINING["flat_drop"])
    fg = Fr([xg, 0.0, zg], [0, 1.0, 0], [1.0, 0, 0], [0, 0, -1.0])
    acc.add(slab(fg, rrect2(-0.5 * gw, -0.5 * gl, 0.5 * gw, 0.5 * gl, 0.010), -0.003, 0.010, 0.003, "psu_panel"))
    for k in range(6):
        b = -0.5 * gl + 0.010 + k * (gl - 0.020) / 5
        acc.add(prism(fg, rrect2(-0.5 * gw + 0.015, b - 0.0015, 0.5 * gw - 0.015, b + 0.0015, 0.0), 0.010, 0.0125,
                      "metal_dark"))
    if kind == "open":
        return
    zb, zt_ = FL + 0.010, zrod - 0.012

    def half_w(z):
        w = L.hw(XP, z) - 0.004
        return np.where(z < ZT + 0.002, np.minimum(w, YI - 0.004), w)
    if kind == "net":
        mesh_, cr_ = DETAIL["net"]
        zs = np.arange(zb, zt_ + 1e-9, mesh_)
        wmax = float(np.max(half_w(zs)))
        for z in zs:
            w = float(half_w(z))
            acc.add(cylinder([XP, -w, z], [XP, w, z], cr_, n=6), "net")
        for y in np.arange(-wmax, wmax + 1e-9, mesh_):
            zz = zs[half_w(zs) >= abs(y)]
            if len(zz) > 1:
                acc.add(cylinder([XP, y, zz[0]], [XP, y, zz[-1]], cr_, n=6), "net")
        for sg in (-1, 1):                                             # side straps down the walls
            zz = np.linspace(zb, zt_, 12)
            path = np.c_[np.full(12, XP), sg * half_w(zz), zz]
            for i in range(11):
                acc.add(cylinder(path[i], path[i + 1], 0.006, n=6), "net")
        return
    # pleated curtain, full width (inboard of the ledge ends below the ledge top), hung from the rod
    pitch = DETAIL["pleat"]
    amp = 0.5 * float(bg["curtain_t"])
    wmax = float(L.hw(XP, FL + 0.4))
    ny = int(round(2 * wmax / pitch)) * 8 + 1
    y = np.linspace(-wmax, wmax, ny)
    zs = np.r_[np.linspace(zb, ZT - 0.02, 5), ZT - 0.002, ZT + 0.006, np.linspace(ZT + 0.05, zt_, 7)]
    X = XP + amp * np.sin(2 * np.pi * y / pitch)
    P = np.stack([np.repeat(X[None, :], len(zs), 0), np.repeat(y[None, :], len(zs), 0),
                  np.repeat(zs[:, None], ny, 1)], -1)
    P[0, :, 2] += 0.004 * np.cos(2 * np.pi * y / pitch)                  # hem
    m = grid_surface(P)
    m = trim(m, half_w(m.V[:, 2]) - np.abs(m.V[:, 1]), "positive")
    acc.add(_oriented(m, [-1.0, 0, 0]), "curtain")
    for yy in np.arange(-wmax + pitch, wmax, 2 * pitch):                # gliders on the rod
        if abs(yy) < float(half_w(zt_)):
            acc.add(cylinder([XP, yy, zt_], [XP, yy, zrod - DETAIL["rod_r"]], 0.003, n=6), "chrome_trim")


# =====================================================================================================================
# baggage bay: tie-down slots, aft wall
# =====================================================================================================================
def _baggage(acc):
    acc.group = "baggage"
    fr = Fr([0, 0, FL], [1.0, 0, 0], [0, 1.0, 0])
    for x in I.BAGGAGE["tiedowns"]:
        for y in (-0.35, -0.12, 0.12, 0.35):                           # as L6 plan draws them
            acc.add(slab(fr, rrect2(x - 0.015, y - 0.04, x + 0.015, y + 0.04, 0.008, 2), 0.0, 0.0018, 0.0008,
                         "metal_dark", bottom=False, nr=1))
            acc.add(fr.poly(rrect2(x - 0.005, y - 0.030, x + 0.005, y + 0.030, 0.004), 0.0020), "black")
    S = I.lining_section(XB, n=1441)
    S = S[S[:, 1] >= FL]
    k = np.argsort(np.arctan2(S[:, 0], S[:, 1] - FL - 0.4))
    ring = np.c_[np.full(len(S), XB), 0.999 * S[k, 0], S[k, 1]]
    acc.add(_oriented(planar_cap(ring[::3], [-1.0, 0, 0]), [-1.0, 0, 0]), "lining")


# =====================================================================================================================
# assembly
# =====================================================================================================================
def _table_states(layout, tables):
    keys = list(I.SEAT_LAYOUTS[layout]["tables"])
    if isinstance(tables, dict):
        st = dict(tables)
        for k in keys:
            st.setdefault(k, "stowed")
        return st
    return {k: tables for k in keys}


def build_cabin_fittings(layout=None, tables="stowed", partition=None, lav_doors="closed", tracks=True, runner=True,
                         o2=True, door_ledge=False, groups=False):
    """All cabin fittings of a layout (crew / cabin seats, the divider and its curtain excluded: model/seats.py and
    model/flightdeck.py build those).  tables: 'stowed' (TTL, default) | 'leaf' | 'deployed' | {table id: state}
    (adds e.g. 'aft_s'); partition: 'curtain' (PRO, BAGGAGE kind) | 'net' | 'open' (header + rod only);
    lav_doors: 'closed' | 'open' (bi-folds folded flat, standing out one leaf into the entry vestibule) | 'ajar' (the
    part-folded V drawn on the L6 plan); door_ledge: include the cargo-door ledge
    segment (static previews; in the model it belongs to the door, cargo_door_ledge()).  groups=False: [(Mesh,
    material)], one merged mesh per material; groups=True: {group: [(Mesh, material)]}."""
    layout = layout or I.DEFAULT_LAYOUT
    lay = I.SEAT_LAYOUTS[layout]
    partition = partition or ("curtain" if str(I.BAGGAGE["kind"]).startswith("veneer") else "net")
    st = _table_states(layout, tables)
    acc = _Acc()
    _floor(acc)
    if runner:
        _runner(acc)
    if tracks:
        _tracks(acc)
    _ledges(acc, layout, st, door_ledge)
    for k, s in st.items():
        if s in ("leaf", "deployed"):
            _table(acc, k, s)
    if lay.get("lavatory", False):
        _lavatory(acc, lav_doors)
    for k in I.CABINETS:
        _cabinet(acc, k)
    _headliner(acc, layout, o2)
    _partition(acc, partition)
    _baggage(acc)
    return _collect(acc, groups)


def cargo_door_ledge(layout=None, tables="stowed"):
    """The port ledge segment carried by the cargo door (LEDGES door_segment), model coordinates with the door closed:
    add it to the door_cargo part so it swings with the door's pivot.  Its outboard face sits on the door's inner
    face (DOOR_T inside the skin)."""
    layout = layout or I.DEFAULT_LAYOUT
    acc = _Acc()
    ds, da, db = LG["door_segment"]
    _ledge_run(acc, int(ds), float(da), float(db), layout, _table_states(layout, tables), _yo_door, _wall_door)
    return _collect(acc, False)


def _collect(acc, groups):
    def clean(ms):
        return Mesh.merge(ms).remove_degenerate(1e-12)
    if groups:
        out = defaultdict(list)
        for (g, mat), ms in acc.d.items():
            out[g].append((clean(ms), mat))
        return dict(out)
    by_mat = defaultdict(list)
    for (g, mat), ms in acc.d.items():
        by_mat[mat] += ms
    return [(clean(ms), mat) for mat, ms in by_mat.items()]


def tri_counts(**kw):
    g = build_cabin_fittings(groups=True, **kw)
    return {k: int(sum(m.nf for m, _ in v)) for k, v in g.items()}


def build(parts, layout=None, ceiling=None, **kw):
    """Part 'cabin_interior' (drop-in for the rev-A interior.build_cabin: the seats are separate parts, model/seats.py);
    the cargo-door ledge segment is added to parts['door_cargo'] when that part exists.  ceiling: a list that takes the
    'headliner' group [(Mesh, material)] instead of the part (interior.build hangs it on the interior_lining part, so
    the viewer's cutaway clips the headliner fittings with the lining they are fixed to), and the 'wall_fittings'
    group (the side-wall USB sockets) likewise."""
    from model.parts import Part
    layout = layout or I.DEFAULT_LAYOUT
    p = Part("cabin_interior", "Cabin: ledges, club tables, lavatory, cabinets, headliner PSUs, FR34 partition, carpet",
             "interior", group="Interior",
             material_note="Walnut veneer, anthracite ledges, carpet with the aisle runner, orange pleated curtain",
             info={"cabin": f"{I.CABIN['length']:.2f} x {I.CABIN['width']:.2f} x {I.CABIN['height']:.2f} m (L6)",
                   "layout": f"{layout}: {I.SEAT_LAYOUTS[layout]['title']}",
                   "floor": f"WL {FL * 1000:,.0f}, carpet STA {XA * 1000:,.0f} - {XB * 1000:,.0f}",
                   "partition": f"FR34 STA {XP * 1000:,.0f}: veneer header + pleated curtain (PRO)"})
    by_mat = defaultdict(list)
    floor = defaultdict(list)
    for grp, ms in build_cabin_fittings(layout, groups=True, **kw).items():
        for m, mat in ms:
            if ceiling is not None and grp in ("headliner", "wall_fittings"):
                ceiling.append((m, mat))
            elif grp in ("floor", "runner", "tracks"):
                floor[mat].append(m)
            else:
                by_mat[mat].append(m)
    for mat, ms in by_mat.items():
        p.add(Mesh.merge(ms), mat)
    parts[p.id] = p
    # the floor, carpet + aisle runner and the seat tracks: their own part, never clipped by the viewer's cutaway (the
    # seats stand on them; review r3 F4)
    fp = Part("cabin_floor", "Cabin floor: carpet with the aisle runner, surface-mounted seat tracks", "interior",
              parent="cabin_interior", group="Interior", material_note="anthracite / navy carpet, AI Orange runner",
              info={"floor": f"WL {FL * 1000:,.0f}, STA {XA * 1000:,.0f} - {XB * 1000:,.0f}",
                    "tracks": f"BL +/-{', '.join(f'{b * 1000:.0f}' for b in I.SEAT_TRACKS['bl'])}"})
    for mat, ms in floor.items():
        fp.add(Mesh.merge(ms), mat)
    parts[fp.id] = fp
    # movable club tables (review r3 F5): built with the outboard leaf out, the inboard leaf folded under it; the
    # viewer / renders start them stowed (pivot 'table' open 0)
    for key in I.SEAT_LAYOUTS[layout]["tables"]:
        ob, lf, pv, lpv = table_parts(key)
        side = "port" if int(I.TABLES[key]["side"]) < 0 else "starboard"
        tp = Part(f"table_{key}", f"Club table, {side} (slides out of the ledge, inboard leaf unfolds)", "interior",
                  parent="cabin_interior", pivot=pv, group="Interior",
                  material_note="anthracite leaves, walnut edge, gloss-black top",
                  info={"table": f"interior.TABLES['{key}']", "states": "stowed / leaf out / deployed"})
        for m, mat in ob:
            tp.add(m, mat)
        parts[tp.id] = tp
        lp = Part(f"table_{key}_leaf", f"Club table inboard leaf, {side}", "interior", parent=tp.id, pivot=lpv,
                  group="Interior", material_note="anthracite leaf, walnut edge, gloss-black top")
        for m, mat in lf:
            lp.add(m, mat)
        parts[lp.id] = lp
    if "door_cargo" in parts:
        for m, mat in cargo_door_ledge(layout):
            parts["door_cargo"].add(m, mat)
    return p
