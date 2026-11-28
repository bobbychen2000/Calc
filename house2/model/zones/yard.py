"""Zone 'yard' of house 2: the built things in the garden (white model: massing + correct shapes).

  fireplace      fieldstone outdoor fireplace NE of the pool (cap 4.1 m above the deck: tools/epi.py, aerial cap ->
                 frames 125900 / 158300) with its hearth / seat wall, facing SW over the lounge
  lounge         2 teak loveseats facing each other over a coffee table, 2 armchairs, 2 side tables (aerial + frame
                 140500), the closed umbrella on its base block
  arbor          dark timber pergola SE of the pool (45.5 deg, column grid solved on p20): 4 white 0.46 m columns on
                 plinths with stepped caps, double beams with bevelled ends 0.86 m past the columns, rafters every
                 0.6 m with cut tails, slats on top, a flat irregular rose / vine mat on them; a two-tier bar + 6
                 stools on the pool side, the BBQ counter (rounded-lid grill under the middle of the SE beam) with an L
                 return + sink to the bar, lanterns on the columns' inner faces
  porch_furniture   the NC recess's 12-seat teak dining set, the BG patio's two armchairs + table, the PB patio's
                 table with two benches, pots
  play           the play structure in the chip yard (p19 / aerial / frame 140500; heights absolute): roofed tower
                 (ridge N-S, 48 deg) on a base frame round a sand pit, the raised slat-walled bridge south to the
                 two-level fort (swings under the bridge), monkey-bar swing beam west to a ladder-legged A-frame
                 (tyre swing), the stand with its green bar NW of the tower, green slides east / south-west, ramp
  garden         picket fence + gate round the vegetable garden, 4 raised timber beds; the play area's north fence
                 and timber edging; the board fence on the upper terrace (guess: hidden under trees)
  small          outdoor shower (guess), utility boxes, path lights, lawn bench

Positions: survey/site.json through model/plan.py at the real heights; everything stands on plan.ground_z.
Heights not measurable are typical values (see the constants)."""
from __future__ import annotations

import math

import numpy as np

from model import plan
from model import furniture as F
from model import fixtures as X
from model.kit import Geo, Part, UP

STONE, CAP, TIMBER, PLAYWOOD, SLIDE = 'yard_fieldstone', 'yard_stone_cap', 'yard_timber_dark', 'yard_wood_grey', 'yard_slide_green'
WHITE, TEAK, STEEL, PICKET = 'yard_column_white', 'yard_teak_grey', 'yard_stainless', 'yard_picket_wood'
MATERIALS = {
    STONE: dict(color=(0.42, 0.34, 0.25), roughness=0.9),            # tan / rust / grey fieldstone
    CAP: dict(color=(0.30, 0.32, 0.34), roughness=0.8),              # bluestone caps, mantel, counter tops
    TIMBER: dict(color=(0.040, 0.028, 0.020), roughness=0.8),        # dark-stained arbor timber, corbels
    PLAYWOOD: dict(color=(0.26, 0.23, 0.20), roughness=0.9),         # weathered cedar of the play structure
    SLIDE: dict(color=(0.03, 0.20, 0.10), roughness=0.5),
    WHITE: dict(color=(0.86, 0.85, 0.80), roughness=0.6),
    TEAK: dict(color=(0.36, 0.33, 0.29), roughness=0.8),             # weathered teak (dining sets, stools, benches)
    STEEL: dict(color=(0.55, 0.56, 0.57), roughness=0.3, metallic=0.9),
    PICKET: dict(color=(0.20, 0.15, 0.11), roughness=0.9),           # garden / play fences, raised beds
    'yard_umbrella': dict(color=(0.42, 0.39, 0.35), roughness=0.95),
    'yard_tire': dict(color=(0.02, 0.02, 0.02), roughness=0.9),
    'yard_rope': dict(color=(0.55, 0.52, 0.42), roughness=0.9),
    'yard_soil': dict(color=(0.068, 0.045, 0.030), roughness=1.0),
    'yard_firebrick': dict(color=(0.45, 0.30, 0.20), roughness=0.9),
    'yard_soot': dict(color=(0.03, 0.028, 0.026), roughness=1.0),
    'yard_pot_grey': dict(color=(0.20, 0.20, 0.21), roughness=0.8),
    'yard_vine': dict(color=(0.07, 0.16, 0.03), roughness=0.95),
    'yard_cushion_white': dict(color=(0.36, 0.355, 0.34), roughness=1.0),    # mid grey in every photo (name kept)
    'yard_sand': dict(color=(0.38, 0.32, 0.24), roughness=1.0),       # the sand pit under the play tower (p19, shade)
}
CUSH = 'yard_cushion_white'

# ---- measured positions (world metres) ------------------------------------------------------------------------------
# fireplace: the cap's centre (aerial cap polygon at z 4.1), front normal toward the lounge (SW)
FP_CAP_C = (6.56, 6.28)
FP_ANG = math.degrees(math.atan2(-0.69, 0.72))    # local x along the hearth wall (NW -> SE), local +y = back (NE)
FP_TOP = 4.10
# lounge (aerial item centres at z 0.4; the pieces stand at 45 deg like the pool)
LOUNGE = dict(sofa_w=(2.77, 4.32), sofa_s=(4.53, 2.62), chair_n=(4.43, 5.78), chair_e=(5.88, 4.30),
              coffee=(3.72, 3.52), side_wood=(3.62, 5.11), side_dark=(5.26, 3.37))
UMBRELLA = (4.93, 1.43)                # the closed canopy's axis (finial: p22 + p23 + p26, three pairs within 0.1 m)
# arbor: the column grid solved on p20 (rms 4.1 px; checked through p26 / frame 133700): origin = the pool-side SW
# column's centre, x along the pool side toward the NE column (45.5 deg), y toward the pool (NW); BBQ row at y -4.066
AR_O, AR_ANG = (3.125, -11.149), 45.5
AR_COLS = ((0.0, 0.0), (4.414, 0.0), (0.0, -4.066), (4.413, -4.067))     # SWp, NEp (on the bar's pier), SWb, NEb
AR_BX = (-0.85, 5.26)                 # beam ends: ~0.6 m past the column faces (p20, p26: 0.86 m past the centre)
AR_RY = (0.55, -4.37)                 # rafter ends: 0.55 m past the pool-side beam (aerial, p26), 0.30 past the SE one (p20)
AR_BEAM_Z, AR_TOP = 2.26, 2.90        # beam underside: p20 2.28, p26 2.20; beam 0.28 + rafters 0.30 + slats 0.06 (p26)
AR_SHAFT, AR_PLINTH, AR_PLINTH_H = 0.46, 0.55, 0.32    # p26 (square on) / p20: shaft 0.46-0.47, plinth 0.55 x 0.32
# play structure (aligned with the lot axes).  Heights ABSOLUTE (p19 rms 2.9 px, p22, aerial): the chips under the tower
# triangulate at ~2.2 (plan.ground_z there is ~1.97); feet and frames stand on plan.ground_z.
PL_TOWER = (17.72, 0.475)             # roof centre: eave corners NW (16.70, 1.42), SW (16.76, -0.50), NE (18.68, 1.45) (p19)
PL_ROOF_S = 1.96                      # roof square (aerial outline at z 4.85 agrees)
PL_DECK_XY = (16.94, 18.80, -0.305, 1.255)    # deck / corner posts (p19: NW post under the roof's NW eave, NE post
                                              # under its NE corner)
Z_DECK, Z_RAIL, Z_EAVE, Z_RIDGE = 3.65, 4.30, 4.85, 5.90      # p19: eave 4.85, ridge 5.85-5.95 (48 deg); deck / rail
Z_BEAM = 3.87                         # swing beam centre (its end 3.94 at the top, p19)
Z_BRIDGE, Z_BRIDGE_TOP = 4.70, 5.90   # the RAISED bridge: floor under the tower's eave (p22 4.9, p19 swing tops 4.5)
PL_BRIDGE = ((18.10, -0.45), (17.97, -3.59))   # centre line, tower end -> fort end (aerial + frame 140500 at z 4.6)
# fort deck: a ~1.5 m hexagon turned 45 deg (frame 140500 + aerial triangulate the deck at 3.3, 1 px); edge 0-1 = the
# bridge's side (an upper landing at the bridge's level), 3-4 = the long slide's
PL_FORT = [(18.24, -3.60), (19.06, -4.17), (19.13, -4.75), (18.45, -5.46), (17.75, -4.75), (17.70, -4.11)]
Z_FORT, Z_FORT_TOP = 3.30, 4.55
PL_AFRAME = ((13.49, 1.44), (13.59, -0.93), (14.15, 0.40))     # feet N / S, apex (p19: the beam runs on 0.42 m past it)
PL_BEAM_Y = (0.28, 0.52)              # the two rails of the swing beam (monkey bars): aerial 0.37 / 0.62, p19 0.21
PL_TIRE = (15.27, 0.30, 2.44)         # tyre centre, its top face (p19)
# vegetable garden: fence base (aerial, on the ground), beds (aerial boxes at the bed tops)
GARDEN = [(16.76, 7.24), (16.78, 4.67), (24.22, 4.61), (24.18, 12.23), (16.71, 12.32), (16.75, 8.08)]
BEDS = [((17.60, 8.98), (19.49, 10.85)), ((21.04, 9.00), (22.92, 10.98)), ((17.58, 5.49), (19.44, 7.39)),
        ((21.07, 5.54), (22.88, 7.49))]
FENCE_H = 1.05


def gz(x, y):
    return float(plan.ground_z(x, y))


class Fr:
    """Local frame: origin (x, y, z), heading (deg) of the local x axis about Z."""

    def __init__(self, o, deg=0.0):
        a = math.radians(deg)
        self.o = np.array([o[0], o[1], o[2] if len(o) > 2 else 0.0], float)
        self.ex = np.array([math.cos(a), math.sin(a), 0.0])
        self.ey = np.array([-math.sin(a), math.cos(a), 0.0])

    def pt(self, x, y, z=0.0):
        return self.o + x * self.ex + y * self.ey + z * UP

    def box(self, geo, mat, lo, hi, faces='xXyYzZ'):
        lo, hi = np.minimum(lo, hi), np.maximum(lo, hi)
        geo.obox(mat, self.o, self.ex, self.ey, UP, lo, hi, faces)

    def poly(self, geo, mat, pts, holes=()):
        geo.poly(mat, [self.pt(*p) for p in pts], holes=[[self.pt(*p) for p in h] for h in holes])

    def frustum(self, geo, mat, r0, z0, r1, z1):
        """Tapered block between two rectangles (x0, y0, x1, y1) at z0 and z1 (sides only + top)."""
        c0 = [(r0[0], r0[1], z0), (r0[2], r0[1], z0), (r0[2], r0[3], z0), (r0[0], r0[3], z0)]
        c1 = [(r1[0], r1[1], z1), (r1[2], r1[1], z1), (r1[2], r1[3], z1), (r1[0], r1[3], z1)]
        for i in range(4):
            j = (i + 1) % 4
            self.poly(geo, mat, [c0[i], c0[j], c1[j], c1[i]])
        self.poly(geo, mat, c1)


def bar(geo, mat, a, b, w=0.09, h=0.09):
    """Rectangular timber from a to b (centre line)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    up = UP if abs((b - a)[2]) < 0.98 * np.linalg.norm(b - a) else np.array([1.0, 0, 0])
    geo.prism(mat, [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)], a, b, up=up)


def picket_run(geo, a, b, h=FENCE_H, z_of=gz, mat=PICKET, step=0.14, pw=0.07, rails=(0.25, 0.85), posts=True,
               bay=2.4):
    """Picket fence from a to b (x, y) following the ground: posts, two rails, pickets."""
    a, b = np.asarray(a, float)[:2], np.asarray(b, float)[:2]
    L = float(np.linalg.norm(b - a))
    d = (b - a) / L
    deg = math.degrees(math.atan2(d[1], d[0]))
    nb = max(1, int(math.ceil(L / bay)))
    for k in range(nb):
        s0, s1 = L * k / nb, L * (k + 1) / nb
        p0, p1 = a + d * s0, a + d * s1
        z0, z1 = z_of(*p0), z_of(*p1)
        for r in rails:
            bar(geo, mat, (p0[0], p0[1], z0 + r), (p1[0], p1[1], z1 + r), 0.04, 0.09)
        if posts:
            Fr((p0[0], p0[1], z0), deg).box(geo, mat, (-0.05, -0.05, -0.1), (0.05, 0.05, h + 0.08))
        n = max(1, int((s1 - s0) / step))
        for i in range(n):
            s = s0 + (i + 0.5) * (s1 - s0) / n
            p = a + d * s
            z = z0 + (z1 - z0) * (i + 0.5) / n
            Fr((p[0], p[1], z), deg).box(geo, mat, (-pw / 2, 0.02, 0.06), (pw / 2, 0.04, h), 'xXyYZ')
    if posts:
        Fr((b[0], b[1], z_of(*b)), deg).box(geo, mat, (-0.05, -0.05, -0.1), (0.05, 0.05, h + 0.08))


# =====================================================================================================================
# fireplace + hearth / seat wall
# =====================================================================================================================
def fireplace():
    geo = Geo()
    a = math.radians(FP_ANG)
    n = np.array([-math.sin(a), math.cos(a)])                     # back (NE)
    o = np.array(FP_CAP_C) - 0.47 * n                             # the front plane under the shaft's centre
    L = Fr((o[0], o[1], 0.0), FP_ANG)
    hw, dp = 1.32, 1.25                                            # body: half width (p22 frontal 2.65-2.70), depth
    # hearth / seat wall along the front (site.seat_wall_fireplace: 1.9 m left, 2.3 m right of the shaft axis)
    hz = 0.52                                                      # hearth top (p22)
    L.box(geo, STONE, (-2.0, -0.50, -0.3), (2.35, 0.0, hz - 0.06), 'xXyY')
    L.box(geo, CAP, (-2.03, -0.54, hz - 0.06), (2.38, 0.02, hz))
    # body, vertical to 2.45 (p22 proportions on the 4.10 m top and the 2.65 m body width), firebox 1.28 wide under a
    # flat segmental arch: springing 1.12, crown 1.33 (p22: 61 / 72 px above the hearth; p23 alike)
    zb = 2.45
    ow, oz0, oz1, rise = 0.64, hz, 1.12, 0.21
    arch = [(-ow, 0, oz0), (ow, 0, oz0), (ow, 0, oz1)] + [
        (ow * math.cos(t), 0, oz1 + rise * math.sin(t)) for t in np.linspace(0, math.pi, 9)[1:-1]] + [(-ow, 0, oz1)]
    L.poly(geo, STONE, [(-hw, 0, hz), (hw, 0, hz), (hw, 0, zb), (-hw, 0, zb)], holes=[arch])
    L.box(geo, STONE, (-hw, 0, -0.3), (hw, dp, zb), 'xXY')
    fd = 0.55                                                      # firebox depth
    L.poly(geo, 'yard_firebrick', [(-ow, fd, oz0), (ow, fd, oz0), (ow, fd, oz1 + rise), (-ow, fd, oz1 + rise)])
    L.poly(geo, 'yard_firebrick', [(-ow, 0, oz0), (-ow, fd, oz0), (-ow, fd, oz1 + rise), (-ow, 0, oz1 + rise)])
    L.poly(geo, 'yard_firebrick', [(ow, fd, oz0), (ow, 0, oz0), (ow, 0, oz1 + rise), (ow, fd, oz1 + rise)])
    L.poly(geo, 'yard_soot', [(-ow, 0, oz1 + rise), (-ow, fd, oz1 + rise), (ow, fd, oz1 + rise), (ow, 0, oz1 + rise)][::-1])
    L.poly(geo, CAP, [(-ow, 0, oz0 + 0.001), (ow, 0, oz0 + 0.001), (ow, fd, oz0 + 0.001), (-ow, fd, oz0 + 0.001)])
    # mantel shelf (2.3 m, narrower than the body) on two dark corbels, bluestone panel above it
    L.box(geo, CAP, (-1.16, -0.28, 1.72), (1.16, 0.0, 1.80))
    for x in (-0.88, 0.88):
        L.box(geo, TIMBER, (x - 0.07, -0.22, 1.42), (x + 0.07, 0.0, 1.72))
    L.box(geo, CAP, (-0.42, -0.012, 2.00), (0.42, 0.0, 3.15), 'xXyzZ')
    # shoulders straight into the crown (no separate shaft), crown slab, flue box, flat cap
    sw, sd, zs = 0.80, 0.98, 3.65
    L.frustum(geo, STONE, (-hw, 0, hw, dp), zb, (-sw, 0, sw, sd), zs)
    L.box(geo, CAP, (-sw - 0.04, -0.05, zs), (sw + 0.04, sd + 0.05, zs + 0.08))
    L.box(geo, STONE, (-0.68, 0.08, zs + 0.08), (0.68, sd - 0.08, FP_TOP - 0.08), 'xXyY')
    L.box(geo, 'yard_soot', (-0.22, 0.075, zs + 0.13), (0.22, 0.08, FP_TOP - 0.13), 'y')      # flue opening (front)
    L.box(geo, CAP, (-0.78, -0.11, FP_TOP - 0.08), (0.78, sd + 0.11, FP_TOP))
    return Part('yard_fireplace', geo, group='yard')


# =====================================================================================================================
# lounge
# =====================================================================================================================
def side_table(geo, at, deg, s=0.62, h=0.45, mat=TEAK):
    L = Fr(at, deg)
    L.box(geo, mat, (-s / 2, -s / 2, h - 0.05), (s / 2, s / 2, h))
    for sx in (-1, 1):
        for sy in (-1, 1):
            L.box(geo, mat, (sx * (s / 2 - 0.06), sy * (s / 2 - 0.06), 0), (sx * s / 2, sy * s / 2, h - 0.05), 'xXyY')


def umbrella(geo, at, top=3.28, mast=(0.106, 0.106)):
    """Closed cantilever umbrella: the canopy's axis at `at` (its finial triangulated on p22 / p23 / p26 at z ~3.25-3.3),
    the dark mast 0.15 m NE of it (p26: left of the canopy) on a square base slab, a short arm to the canopy."""
    L = Fr(at, 45.0)
    m = np.array(at[:2]) + np.array(mast)
    Fr((m[0], m[1], 0.0), 45.0).box(geo, CAP, (-0.45, -0.45, 0), (0.45, 0.45, 0.20))           # p22: 0.2 m slab
    geo.cylinder(TIMBER, (m[0], m[1], 0.20), (m[0], m[1], top + 0.05), 0.05, n=8)
    bar(geo, TIMBER, (m[0], m[1], top), L.pt(0, 0, top), 0.06, 0.07)
    F._revolve(geo, 'yard_umbrella', [(0.03, 0.95), (0.30, 1.00), (0.33, 1.40), (0.27, 2.05), (0.20, 2.62),
                                      (0.10, top - 0.10), (0.0, top - 0.01)], n=10, centre=tuple(L.pt(0, 0, 0)))


def lounge():
    geo = Geo()
    F.teak_sofa(geo, LOUNGE['sofa_w'], 45.0, length=1.75, pillows=2, seed=1)       # faces SE
    F.teak_sofa(geo, LOUNGE['sofa_s'], -135.0, length=1.75, pillows=2, seed=2)     # faces NW
    F.teak_armchair(geo, LOUNGE['chair_n'], -20.0, seed=3)
    F.teak_armchair(geo, LOUNGE['chair_e'], -70.0, seed=4)
    F.teak_coffee_table(geo, LOUNGE['coffee'], 45.0, length=1.45, width=1.20, height=0.36)
    side_table(geo, LOUNGE['side_wood'], 45.0)
    side_table(geo, LOUNGE['side_dark'], 45.0, mat='furn_black')
    umbrella(geo, UMBRELLA)
    # square planters at the hearth wall's ends (rear.planters_fireplace)
    for p in ((4.35, 6.95), (8.35, 3.85)):
        Fr(p, FP_ANG).box(geo, 'yard_pot_grey', (-0.28, -0.28, 0), (0.28, 0.28, 0.55), 'xXyYZ')
    return Part('yard_lounge', geo, group='yard')


# =====================================================================================================================
# arbor, bar, BBQ kitchen
# =====================================================================================================================
def stool(geo, L, x, y, back=True):
    s, h = 0.38, 0.74
    L.box(geo, TEAK, (x - s / 2, y - s / 2, h - 0.04), (x + s / 2, y + s / 2, h))
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = x + sx * (s / 2 - 0.025), y + sy * (s / 2 - 0.025)
            top = h + 0.36 if (back and sy > 0) else h - 0.04
            L.box(geo, TEAK, (cx - 0.022, cy - 0.022, 0), (cx + 0.022, cy + 0.022, top), 'xXyYZ')
    L.box(geo, TEAK, (x - s / 2, y - s / 2 + 0.01, 0.25), (x + s / 2, y - s / 2 + 0.04, 0.29))
    if back:
        for z in (h + 0.14, h + 0.27):
            L.box(geo, TEAK, (x - s / 2, y + s / 2 - 0.04, z), (x + s / 2, y + s / 2 - 0.015, z + 0.07))


def _beam_side(geo, L, mat, x0, x1, y, w, z0, h, cut0=0.15, cut1=0.15):
    """A timber along local x from x0 to x1 (centre line at y, width w, underside z0, depth h) whose ends are cut back
    at the bottom (the arbor's bevelled beam / rafter ends, p26)."""
    sec = [(x0 + cut0, z0), (x1 - cut1, z0), (x1, z0 + h * 0.45), (x1, z0 + h), (x0, z0 + h), (x0, z0 + h * 0.45)]
    a, b = L.pt(0.0, y - w / 2, 0.0), L.pt(0.0, y + w / 2, 0.0)
    # prism(): the section's s runs along cross(d, UP) = +L.ex for d = L.ey, t along UP
    geo.prism(mat, sec, a, b, up=UP)


def _rafter(geo, L, mat, x, y0, y1, w, z0, h, cut=0.12):
    """A timber along local y (rafter) from y0 > y1, bottom cut back at both ends (the rafter tails)."""
    sec = [(y1 + cut, z0), (y0 - cut, z0), (y0, z0 + h * 0.5), (y0, z0 + h), (y1, z0 + h), (y1, z0 + h * 0.5)]
    a, b = L.pt(x - w / 2, 0.0, 0.0), L.pt(x + w / 2, 0.0, 0.0)
    # d = L.ex: cross(d, UP) = -L.ey
    geo.prism(mat, [(-sy, sz) for sy, sz in sec], a, b, up=UP)


def _in_poly(P, ring):
    """Even-odd point-in-polygon for many points (P (n, 2), ring (m, 2))."""
    x, y = P[:, 0], P[:, 1]
    out = np.zeros(len(P), bool)
    for (x1, y1), (x2, y2) in zip(ring, np.roll(ring, -1, 0)):
        c = (y1 > y) != (y2 > y)
        xi = x1 + (y - y1) * (x2 - x1) / np.where(abs(y2 - y1) < 1e-12, 1e-12, y2 - y1)
        out ^= c & (x < xi)
    return out


def vine_mat(geo, L, poly, z0, h_of, seed=5, step=0.22, mat='yard_vine'):
    """The rose / vine mat lying on the arbor: a flat, irregular leaf slab over a plan polygon (local x, y), its top a
    noisy height field h_of(x, y) above z0 that rounds over at the ragged edges, a skirt hanging below the edge."""
    rs = np.random.default_rng(seed)
    poly = np.asarray(poly, float)
    # ragged outline: resample the polygon every ~0.25 m and push each point in / out
    pts = []
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        n = max(2, int(np.linalg.norm(q - p) / 0.25))
        for k in range(n):
            pts.append(p + (q - p) * k / n)
    pts = np.array(pts)
    c = pts.mean(0)
    rad = pts - c
    jit = 1.0 + 0.06 * np.sin(np.arange(len(pts)) * 1.7 + 0.5) + rs.uniform(-0.05, 0.05, len(pts))
    ring = c + rad * jit[:, None]
    x0, y0 = ring.min(0) - step
    x1, y1 = ring.max(0) + step
    xs = np.arange(x0, x1 + step, step)
    ys = np.arange(y0, y1 + step, step)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    P = np.stack([X.ravel(), Y.ravel()], 1)
    inside = _in_poly(P, ring).reshape(X.shape)
    # distance to the outline (for the rounded edge)
    segs = np.stack([ring, np.roll(ring, -1, 0)], 1)
    d = np.full(len(P), 1e9)
    for a_, b_ in segs:
        ab = b_ - a_
        t = np.clip(((P - a_) @ ab) / max(ab @ ab, 1e-9), 0, 1)
        d = np.minimum(d, np.linalg.norm(P - (a_ + t[:, None] * ab), axis=1))
    d = d.reshape(X.shape)
    noise = sum(A * np.sin(fx * X + fy * Y + ph) for A, fx, fy, ph in
                [(0.06, 2.1, 1.3, 0.3), (0.05, -1.7, 2.6, 1.1), (0.04, 3.9, -2.2, 2.0), (0.03, 5.3, 4.1, 0.7)])
    bumps = np.zeros_like(X)                                       # leafy clumps (p20: rounded masses, not a sheet)
    for _ in range(int(len(ring) * 1.6)):
        bx, by = rs.uniform(x0, x1), rs.uniform(y0, y1)
        br, bh = rs.uniform(0.20, 0.45), rs.uniform(-0.12, 0.12)
        bumps += bh * np.exp(-((X - bx) ** 2 + (Y - by) ** 2) / (2 * br * br))
    H = h_of(X, Y) + np.clip(noise + bumps, -0.25, 0.18) + rs.uniform(-0.03, 0.03, X.shape)
    H *= np.clip(d / 0.45, 0.0, 1.0) ** 0.5 * 0.85 + 0.15
    Z = z0 + np.where(inside, H, 0.0)
    W = np.stack([L.pt(x, y, z) for x, y, z in zip(X.ravel(), Y.ravel(), Z.ravel())]).reshape(X.shape + (3,))
    # top: the grid cells whose four corners are inside
    gx, gy = np.gradient(Z, step, step)
    Nl = np.stack([-gx, -gy, np.ones_like(Z)], -1)
    Nl /= np.linalg.norm(Nl, axis=-1, keepdims=True)
    Nw = Nl[..., 0:1] * L.ex + Nl[..., 1:2] * L.ey + Nl[..., 2:3] * UP
    V, N, UVs, F = [], [], [], []
    idx = -np.ones(X.shape, int)
    nx, ny = X.shape
    for i in range(nx):
        for j in range(ny):
            if inside[max(i - 1, 0):i + 2, max(j - 1, 0):j + 2].any():
                idx[i, j] = len(V)
                V.append(W[i, j]); N.append(Nw[i, j]); UVs.append((X[i, j], Y[i, j]))
    for i in range(nx - 1):
        for j in range(ny - 1):
            q = [idx[i, j], idx[i + 1, j], idx[i + 1, j + 1], idx[i, j + 1]]
            if min(q) < 0 or not inside[i:i + 2, j:j + 2].any():
                continue
            F.append((q[0], q[1], q[2])); F.append((q[0], q[2], q[3]))
    geo.mesh(mat).add(V, N, UVs, F)
    # a ragged skirt hanging below the outline (the leaves draped over the rafter ends)
    hang = rs.uniform(0.05, 0.28, len(ring))
    out = (ring - c) / np.linalg.norm(ring - c, axis=1, keepdims=True) * 0.06
    for i in range(len(ring)):
        j = (i + 1) % len(ring)
        p, q = ring[i], ring[j]
        geo.poly(mat, [L.pt(*(p + out[i]), z0 - hang[i]), L.pt(*(q + out[j]), z0 - hang[j]), L.pt(q[0], q[1], z0 + 0.04),
                       L.pt(p[0], p[1], z0 + 0.04)])


def arbor():
    geo = Geo()
    L = Fr((AR_O[0], AR_O[1], 0.0), AR_ANG)
    hs, hp = AR_SHAFT / 2, AR_PLINTH / 2
    # square white columns (p20 / p26): a 0.32 m plinth, the 0.46 m shaft, a stepped cap (0.52 / 0.58) under the beams.
    # The pool-side NE one stands on the bar's stone pier (rear.arbor_columns); NE BBQ-row one at a bed edge: its
    # plinth is set on the deck level and runs down past the lowest terrain
    for k, (cx, cy) in enumerate(AR_COLS):
        zs = [gz(*L.pt(cx + sx * hp, cy + sy * hp)[:2]) for sx in (-1, 0, 1) for sy in (-1, 0, 1)]
        z0, zlo = min(zs, key=abs), min(zs) - 0.2
        ph = AR_PLINTH_H
        if k == 1:
            z0, ph = 1.08, 0.10                                    # on the bar's pier: a low base band only (p26)
            zlo = z0 - 0.02
        L.box(geo, WHITE, (cx - hp, cy - hp, zlo), (cx + hp, cy + hp, z0 + ph), 'xXyYZ')
        L.box(geo, WHITE, (cx - hp - 0.012, cy - hp - 0.012, z0 + ph - 0.05),
              (cx + hp + 0.012, cy + hp + 0.012, z0 + ph), 'xXyYZ')                              # plinth cap
        L.box(geo, WHITE, (cx - hs, cy - hs, z0 + ph), (cx + hs, cy + hs, AR_BEAM_Z - 0.18), 'xXyY')
        L.box(geo, WHITE, (cx - 0.26, cy - 0.26, AR_BEAM_Z - 0.18), (cx + 0.26, cy + 0.26, AR_BEAM_Z - 0.06), 'xXyYz')
        L.box(geo, WHITE, (cx - 0.29, cy - 0.29, AR_BEAM_Z - 0.06), (cx + 0.29, cy + 0.29, AR_BEAM_Z))
    # double beams on each column row (0.09 x 0.28 each side of the column line), bevelled ends 0.86 m past the columns
    zb, hb = AR_BEAM_Z, 0.28
    for cy in (0.0, -4.066):
        for dy in (-0.13, 0.13):
            _beam_side(geo, L, TIMBER, AR_BX[0], AR_BX[1], cy + dy, 0.09, zb, hb, cut0=0.18, cut1=0.18)
    # rafters across the beams every ~0.6 m (p20 / p26: tails at 0.64-0.69 m) with cut tails, slats along x on top
    zr, hr = zb + hb, 0.30
    nr = 10
    for i in range(nr + 1):
        x = AR_BX[0] + 0.10 + (AR_BX[1] - AR_BX[0] - 0.20) * i / nr
        _rafter(geo, L, TIMBER, x, AR_RY[0], AR_RY[1], 0.07, zr, hr, cut=0.16)
    ns = int(round((AR_RY[0] - AR_RY[1] - 0.2) / 0.26))
    for j in range(ns + 1):
        y = AR_RY[0] - 0.10 - (AR_RY[0] - AR_RY[1] - 0.20) * j / ns
        L.box(geo, TIMBER, (AR_BX[0] + 0.05, y - 0.025, zr + hr), (AR_BX[1] - 0.05, y + 0.025, AR_TOP))
    # the rose / vine mat: a flat irregular leaf slab on the slats (aerial: it leaves the pool-side rafter tails and the
    # SW end bare, overhangs the SE beam / NE end), lumpy, ~0.6-0.7 m above the slats along both long edges (p20's and
    # p26's silhouettes; i.e. ~1.0 above the rafters' underside), fuller in the middle
    mat_poly = [(-0.35, 0.05), (1.6, 0.18), (3.4, 0.35), (5.05, 0.40), (5.45, -1.2), (5.55, -3.4), (5.40, -4.90),
                (3.0, -4.95), (0.6, -4.90), (-0.70, -4.80), (-0.75, -2.6), (-0.55, -1.0)]
    h_of = lambda x, y: 0.58 + 0.25 * np.exp(-((y + 2.1) / 1.6) ** 2) + 0.06 * np.clip(x / 5.0, 0, 1)
    vine_mat(geo, L, mat_poly, AR_TOP - 0.02, h_of, seed=5)
    # the old twisted trunk(s) climbing beside the NE BBQ-row column (p20: two stems right of that column)
    cx, cy = AR_COLS[3]
    for dx, dy, r in ((0.42, 0.30, 0.07), (0.55, 0.12, 0.05)):
        geo.cylinder('bark', L.pt(cx + dx, cy + dy, gz(*L.pt(cx + dx, cy + dy)[:2]) - 0.1),
                     L.pt(cx + dx - 0.25, cy + dy + 0.15, AR_TOP), r, n=7, cap=False)
    # bar on the pool row (p20 / p26): stone body from 1.35 m NE of the SW column (p26: its SW end) to the NE column's
    # pier; a raised bar top (1.02-1.08) on the pool side with the stools beyond it, a lower work counter (0.90) on the
    # kitchen side (p20: its edge at y -0.9 .. -1.07) with a dark fridge niche and open shelves under it
    bx0, bx1 = 1.35, 4.414 + 0.32
    L.box(geo, STONE, (bx0, -0.92, -0.45), (bx1, -0.20, 0.90), 'xXyY')
    L.box(geo, STONE, (bx0, -0.20, -0.45), (bx1, 0.15, 1.02), 'xXyY')
    L.box(geo, STONE, (bx0, -0.23, 0.90), (bx1, -0.20, 1.02), 'y')
    L.box(geo, STONE, (4.414 - 0.33, -0.33, -0.45), (bx1, 0.33, 1.02), 'xXyY')                 # the column's pier
    L.box(geo, CAP, (bx0 - 0.04, -0.96, 0.90), (bx1 + 0.04, -0.20, 0.95))                    # work counter
    L.box(geo, CAP, (bx0 - 0.05, -0.23, 1.02), (bx1 + 0.05, 0.40, 1.08))                     # raised bar top
    L.box(geo, 'yard_soot', (2.10, -0.925, 0.10), (2.66, -0.92, 0.84), 'y')                  # fridge niche
    L.box(geo, 'furn_black', (2.14, -0.94, 0.12), (2.62, -0.925, 0.82), 'xXyzZ')             # its door
    L.box(geo, 'yard_soot', (2.72, -0.925, 0.10), (3.50, -0.92, 0.84), 'y')                  # open shelves
    for z in (0.10, 0.45, 0.80):
        L.box(geo, CAP, (2.72, -0.92, z - 0.03), (3.50, -0.70, z))
    for x, back in ((1.00, False), (1.50, False), (2.20, True), (2.80, True), (3.40, True), (4.00, True)):
        stool(geo, L, x, 0.65, back=back)
    # BBQ counter inside the back row (p20: its back face just NW of the SE columns), the grill under the middle of
    # the SE beam (a ~1.15 m built-in grill with a rounded lid), an L return with the sink from its NE end toward the
    # bar, inside the NE column
    gx0, gx1, gy0, gy1 = 0.30, 3.85, -3.80, -3.15
    L.box(geo, STONE, (gx0, gy0, -0.45), (gx1, gy1, 0.90), 'xXyY')     # down into the ground at the bed edge
    L.box(geo, CAP, (gx0 - 0.03, gy0 - 0.04, 0.90), (gx1 + 0.04, gy1 + 0.04, 0.95))
    lx0 = gx1 - 0.70
    L.box(geo, STONE, (lx0, gy1, -0.45), (gx1, -0.96, 0.90), 'xXyY')
    L.box(geo, CAP, (lx0 - 0.04, gy1 + 0.04, 0.90), (gx1 + 0.04, -0.96, 0.95))
    xg, yg = 2.25, (gy0 + gy1) / 2
    L.box(geo, STEEL, (xg - 0.58, gy0 + 0.05, 0.95), (xg + 0.58, gy1 - 0.05, 1.12))
    a_, b_ = L.pt(xg - 0.57, yg - 0.03, 1.12), L.pt(xg + 0.57, yg - 0.03, 1.12)
    geo.prism_smooth(STEEL, [(0.25 * math.cos(t), 0.22 * math.sin(t)) for t in np.linspace(0, math.pi, 9)] +
                     [(-0.25, 0.0)], a_, b_)                                                   # the rounded lid
    L.box(geo, STEEL, (xg - 0.55, gy1 - 0.01, 0.30), (xg + 0.55, gy1 + 0.015, 0.84), 'xXYzZ')   # doors
    L.box(geo, STEEL, (lx0 + 0.15, -3.10, 0.951), (gx1 - 0.15, -2.65, 0.956), 'Z')           # sink (p20)
    geo.cylinder(STEEL, L.pt(gx1 - 0.12, -2.88, 0.95), L.pt(gx1 - 0.12, -2.88, 1.25), 0.012, n=6)
    # lanterns (p20 / p26): on each column's face toward the bay's middle along its row, top ~2.05
    for k, (cx, cy) in enumerate(AR_COLS):
        sg = 1 if cx < 2 else -1
        X.lantern(geo, L.pt(cx + sg * hs, cy, 1.85), L.ey * sg, L.ex * sg, h=0.40, w=0.17, d=0.115)
    return Part('yard_arbor', geo, group='yard')


# =====================================================================================================================
# porch furniture
# =====================================================================================================================
def slat_chair(geo, at, deg, cushion=True):
    """Teak slat-back dining chair; front toward local -y."""
    L = Fr(at, deg)
    w, d, h = 0.50, 0.50, 0.44
    L.box(geo, TEAK, (-w / 2, -d / 2, h - 0.04), (w / 2, d / 2, h))
    if cushion:
        L.box(geo, CUSH, (-w / 2 + 0.03, -d / 2 + 0.03, h), (w / 2 - 0.03, d / 2 - 0.05, h + 0.05), 'xXyYZ')
    for sx in (-1, 1):
        x = sx * (w / 2 - 0.025)
        L.box(geo, TEAK, (x - 0.025, -d / 2, 0), (x + 0.025, -d / 2 + 0.05, h - 0.04), 'xXyY')
        L.box(geo, TEAK, (x - 0.025, d / 2 - 0.05, 0), (x + 0.025, d / 2, 0.92), 'xXyYZ')
        L.box(geo, TEAK, (x - 0.025, -d / 2, 0.62), (x + 0.025, d / 2, 0.66))            # arm
    L.box(geo, TEAK, (-w / 2, d / 2 - 0.04, 0.86), (w / 2, d / 2 - 0.01, 0.92))
    for i in range(4):
        x = -w / 2 + 0.09 + i * (w - 0.18) / 3
        L.box(geo, TEAK, (x - 0.025, d / 2 - 0.035, h), (x + 0.025, d / 2 - 0.015, 0.86), 'xXyY')


def plank_table(geo, at, deg, length, width, h=0.75):
    L = Fr(at, deg)
    L.box(geo, TEAK, (-length / 2, -width / 2, h - 0.05), (length / 2, width / 2, h))
    L.box(geo, TEAK, (-length / 2 + 0.12, -width / 2 + 0.10, h - 0.14), (length / 2 - 0.12, width / 2 - 0.10, h - 0.05), 'xXyY')
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (length / 2 - 0.14), sy * (width / 2 - 0.12)
            L.box(geo, TEAK, (x - 0.045, y - 0.045, 0), (x + 0.045, y + 0.045, h - 0.05), 'xXyY')
    return L


def bench(geo, at, deg, length=1.8, back=False):
    L = Fr(at, deg)
    L.box(geo, TEAK, (-length / 2, -0.19, 0.40), (length / 2, 0.19, 0.45))
    for sx in (-1, 1):
        L.box(geo, TEAK, (sx * (length / 2 - 0.12) - 0.035, -0.17, 0), (sx * (length / 2 - 0.12) + 0.035, 0.17, 0.40), 'xXyY')
        if back:
            L.box(geo, TEAK, (sx * (length / 2 - 0.03) - 0.03, 0.15, 0), (sx * (length / 2 - 0.03) + 0.03, 0.21, 0.88), 'xXyYZ')
    if back:
        L.box(geo, TEAK, (-length / 2, 0.16, 0.55), (length / 2, 0.20, 0.88))


def adirondack(geo, at, deg):
    """Adirondack chair, front toward local -y: sloped seat, tall raked slat back, wide flat arms."""
    L = Fr(at, deg)
    w = 0.56
    for i in range(5):                                                       # seat slats, falling to the back
        y = -0.36 + i * 0.13
        z = 0.36 - (i + 0.5) * 0.028
        L.box(geo, TEAK, (-w / 2, y, z - 0.02), (w / 2, y + 0.11, z))
    e0, e1 = np.array([0.0, 0.26, 0.20]), np.array([0.0, 0.52, 0.98])        # the back's centre line
    for i in range(5):
        x = (i - 2) * 0.115
        top = e1 - np.array([0, 0, 0.05 * abs(i - 2)])
        bar(geo, TEAK, L.pt(x, e0[1], e0[2]), L.pt(x, top[1], top[2]), 0.10, 0.02)
    for sx in (-1, 1):
        x = sx * (w / 2 + 0.04)
        L.box(geo, TEAK, (x - 0.07, -0.42, 0.54), (x + 0.07, 0.36, 0.565))             # arm
        L.box(geo, TEAK, (x - 0.02, -0.40, 0), (x + 0.02, -0.30, 0.54), 'xXyY')       # front leg
        bar(geo, TEAK, L.pt(sx * w / 2, -0.36, 0.34), L.pt(sx * w / 2, 0.50, 0.02), 0.025, 0.10)   # side rail / back leg


def pot(geo, at, s=0.45, h=0.55, top=None):
    t = top or s
    L = Fr(at, 0.0)
    L.frustum(geo, 'yard_pot_grey', (-s / 2, -s / 2, s / 2, s / 2), 0.0, (-t / 2, -t / 2, t / 2, t / 2), h)
    L.poly(geo, 'yard_soil', [(-t / 2 + 0.03, -t / 2 + 0.03, h + 0.002), (t / 2 - 0.03, -t / 2 + 0.03, h + 0.002),
                              (t / 2 - 0.03, t / 2 - 0.03, h + 0.002), (-t / 2 + 0.03, t / 2 - 0.03, h + 0.002)])


DINING_EAST_BACKS = -11.95      # p21 + frame 137200: the east chairs' back legs
DINING_Y = 3.27


def _recess_slab():
    """The house's recess floor north of the balcony gable (read from the house zone, so the set follows it)."""
    try:
        from model.zones import house as H
        return dict(x0=H.REAR_X_GROUND, x1=H.BG_X_WALL + 0.15, y0=H.BG_Y[1], y1=H.NC_Y_N, z=H.PATIO_FLOOR)
    except Exception:
        return dict(x0=-12.4, x1=-10.85, y0=0.35, y1=5.6, z=plan.REAR_PATIO_FLOOR)


def porch_furniture():
    geo = Geo()
    # dining set: it stands IN the recess under NC (the two-storey block north of the balcony gable), in front of the
    # 4-panel doors -- not on the north porch.  Triangulated on p21 + frame 137200 (residuals <= 2 px): the east row's
    # chair backs at x -11.95, y 1.9 .. 4.65 (5 chairs a side, 0.55 m apart, + one at each end), the floor under them
    # at ~0.25.  The set is placed as far in as the house's recess wall allows and every piece stands on the surface
    # under it: the recess slab (house.patio_bg at PATIO_FLOOR) or the terrain.
    slab = _recess_slab()
    tw, off = 1.00, 0.72                                  # table width (p21 / p23 ~1.0); chair centres off its centre line
    half = off + 0.25
    cx = max(DINING_EAST_BACKS - half, slab['x0'] + half + 0.03)
    c = (cx, DINING_Y)

    def zat(x, y, r=0.25):
        return slab['z'] if (slab['x0'] <= x - r and x + r <= slab['x1'] and slab['y0'] <= y - r and y + r <= slab['y1']) \
            else gz(x, y)

    zt = zat(c[0], c[1], 0.0)
    plank_table(geo, (c[0], c[1], zt), 90.0, 3.0, tw)
    for i in range(5):
        y = c[1] - 1.10 + i * 0.55
        slat_chair(geo, (c[0] + off, y, zat(c[0] + off, y)), -90.0)        # east side, facing the house
        slat_chair(geo, (c[0] - off, y, zat(c[0] - off, y)), 90.0)
    for sy, deg in ((-1, 180.0), (1, 0.0)):
        y = c[1] + sy * 1.72
        slat_chair(geo, (c[0], y, zat(c[0], y)), deg)
    Fr((c[0], c[1], zt + 0.75), 90.0).box(geo, 'furn_black', (-0.2, -0.12, 0), (0.2, 0.12, 0.3))     # lantern box
    pot(geo, (-10.0, 5.7, gz(-10.0, 5.7)), 0.5, 0.5)                                   # rear.ncp_pot
    # BG patio: two wicker armchairs with a small table between, facing the pool; pots at the posts
    zp = plan.REAR_PATIO_FLOOR
    F.lounge_chair(geo, (-11.45, -2.35, zp), 90.0, seed=1)
    F.lounge_chair(geo, (-11.45, -0.45, zp), 90.0, seed=2)
    side_table(geo, (-11.55, -1.40, zp), 0.0, s=0.5, h=0.42, mat='furn_black')
    for y in (-4.15, -0.25):                               # between the BG corner posts (house: y -4.7 / 0.3), clear of their bases
        pot(geo, (-9.20, y, zp), 0.36, 0.75, top=0.46)
    # PB patio: plank table with two benches (p21 / p28 rays), tall planter at its NE column
    t = (-5.5, -13.0)
    plank_table(geo, (t[0], t[1], zp), 0.0, 2.2, 0.95)
    bench(geo, (t[0], t[1] - 0.72, zp), 0.0)
    bench(geo, (t[0], t[1] + 0.72, zp), 0.0)
    pot(geo, (-1.9, -11.4, gz(-1.9, -11.4)), 0.34, 0.95, top=0.50)
    return Part('yard_porch_furniture', geo, group='yard')


# =====================================================================================================================
# play structure
# =====================================================================================================================
def slat_wall(geo, a, b, z0, z1, mat=PLAYWOOD, step=0.15, pw=0.09):
    a, b = np.asarray(a, float), np.asarray(b, float)
    Lh = float(np.linalg.norm(b - a))
    if Lh < 0.2:
        return
    d = (b - a) / Lh
    L = Fr((a[0], a[1], 0.0), math.degrees(math.atan2(d[1], d[0])))
    for z in (z0 + 0.08, z1 - 0.12):
        L.box(geo, mat, (0, -0.02, z), (Lh, 0.02, z + 0.09))
    n = max(1, int(Lh / step))
    for i in range(n):
        x = (i + 0.5) * Lh / n
        L.box(geo, mat, (x - pw / 2, 0.02, z0), (x + pw / 2, 0.04, z1), 'xXyYZ')


def slide(geo, top, end, w=0.50, wave=0.0, n=8):
    """Open green slide from the deck edge `top` (x, y, z) down to `end` (x, y, z on the ground)."""
    top, end = np.asarray(top, float), np.asarray(end, float)
    run = end - top
    side = np.cross(UP, run)
    side /= np.linalg.norm(side)
    hd = np.array([run[0], run[1], 0.0]) / np.linalg.norm(run[:2])
    tip = end + hd * 0.45                                  # the level run-out beyond `end`
    z_end, z_tip = gz(end[0], end[1]) + 0.09, gz(tip[0], tip[1]) + 0.05
    pts = []
    for i in range(n + 1):
        t = i / n
        p = top + run * t
        p[2] = top[2] + (z_end - top[2]) * (t ** 0.85) + wave * math.sin(2 * math.pi * t) * (1 - t)
        p[2] = max(p[2], gz(p[0], p[1]) + 0.05)
        pts.append(p)
    pts.append(np.array([tip[0], tip[1], z_tip]))
    for p, q in zip(pts[:-1], pts[1:]):
        geo.poly(SLIDE, [p - side * w / 2, q - side * w / 2, q + side * w / 2, p + side * w / 2])
        geo.poly(SLIDE, [p + side * w / 2, q + side * w / 2, q - side * w / 2, p - side * w / 2])
        for s in (-1, 1):
            e = side * s * w / 2
            geo.poly(SLIDE, [p + e, q + e, q + e + UP * 0.14, p + e + UP * 0.14])
            geo.poly(SLIDE, [q + e, p + e, p + e + UP * 0.14, q + e + UP * 0.14])


def ladder(geo, a, b, w=0.30, mat=PLAYWOOD, rung=SLIDE, step=0.30, board=(0.04, 0.14)):
    """A ladder-like leg: two boards from a to b (bottom -> top), `w` apart across, green rungs between them."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b - a
    side = np.cross(d, UP)
    side = side / np.linalg.norm(side) if np.linalg.norm(side) > 1e-6 else np.array([1.0, 0, 0])
    for sg in (-1, 1):
        bar(geo, mat, a + side * sg * w / 2, b + side * sg * w / 2, board[0], board[1])
    n = int(np.linalg.norm(d) / step)
    for k in range(1, n):
        p = a + d * k / n
        bar(geo, rung, p - side * w / 2, p + side * w / 2, 0.03, 0.03)


def play():
    geo = Geo()
    cx, cy = PL_TOWER
    tx0, tx1, ty0, ty1 = PL_DECK_XY
    g = gz((tx0 + tx1) / 2, (ty0 + ty1) / 2)
    W = PLAYWOOD
    # ---- roofed tower (p19): 4 corner posts + 2 on the north face flanking its opening, deck, slat rails, a heavy
    # base frame (two stacked boards, 0.25 m) round a sand pit, green rungs on the north and west sides, the gabled
    # board roof (ridge N-S, 48 deg)
    for x in (tx0, tx1):
        for y in (ty0, ty1):
            geo.box(W, (x - 0.05, y - 0.05, gz(x, y) - 0.1), (x + 0.05, y + 0.05, Z_EAVE))
    for x in (18.31, 17.62):                                                                   # north face (p19)
        geo.box(W, (x - 0.045, ty1 - 0.045, gz(x, ty1) - 0.1), (x + 0.045, ty1 + 0.045, Z_EAVE + 0.35))
    geo.box(W, (tx0, ty0, Z_DECK - 0.10), (tx1, ty1, Z_DECK))
    b0x, b1x, b0y, b1y = tx0 - 0.06, tx1 + 0.06, ty0 - 0.06, ty1 + 0.06
    for z, t in ((0.0, 0.12), (0.13, 0.12)):                                                   # base frame
        for p, q in (((b0x, b0y), (b1x, b0y)), ((b1x, b0y), (b1x, b1y)), ((b1x, b1y), (b0x, b1y)), ((b0x, b1y), (b0x, b0y))):
            bar(geo, W, (p[0], p[1], gz(*p) + z + t / 2), (q[0], q[1], gz(*q) + z + t / 2), 0.10, t)
    geo.poly('yard_sand', [(b0x + 0.05, b0y + 0.05, g + 0.10), (b1x - 0.05, b0y + 0.05, g + 0.10),
                           (b1x - 0.05, b1y - 0.05, g + 0.10), (b0x + 0.05, b1y - 0.05, g + 0.10)])
    for z in (0.45, 0.75, 1.05, 1.35):                                                         # climbing rungs N, W
        if g + z < Z_DECK - 0.15:
            bar(geo, SLIDE, (tx0, ty1, g + z), (tx1, ty1, g + z), 0.035, 0.035)
            bar(geo, SLIDE, (tx0, ty0, g + z), (tx0, ty1, g + z), 0.035, 0.035)
    z0, z1 = Z_DECK, Z_RAIL
    slat_wall(geo, (tx1, ty1), (17.62, ty1), z0, z1)                                           # north, opening W
    slat_wall(geo, (tx0, ty1), (tx0, ty0), z0, z1)                                             # west
    slat_wall(geo, (tx0, ty0), (tx1, ty0), z0, z1)                                             # south
    slat_wall(geo, (tx1, ty0), (tx1, ty1 - 0.55), z0, z1)                                      # east, up to the slide
    hw = PL_ROOF_S / 2
    rise = Z_RIDGE - Z_EAVE
    t = 0.05
    for s_ in (-1, 1):
        e0 = np.array([cx + s_ * hw, cy - hw, Z_EAVE])
        e1 = np.array([cx + s_ * hw, cy + hw, Z_EAVE])
        r0, r1 = np.array([cx, cy - hw, Z_RIDGE]), np.array([cx, cy + hw, Z_RIDGE])
        quad = [e0, e1, r1, r0] if s_ > 0 else [e1, e0, r0, r1]
        geo.poly(W, quad)
        geo.poly(W, [q - UP * t for q in quad[::-1]])
        for a_, b_ in ((e0, e1), (e0, r0), (e1, r1)):                                          # board edges
            geo.poly(W, [a_, b_, b_ - UP * t, a_ - UP * t] if s_ > 0 else [b_, a_, a_ - UP * t, b_ - UP * t])
    zroof = lambda x: Z_RIDGE - abs(x - cx) * rise / hw                                         # under side at x
    for y in (ty0, ty1):                                                                       # gable frames
        bar(geo, W, (tx0, y, Z_EAVE - 0.06), (tx1, y, Z_EAVE - 0.06), 0.05, 0.10)
        bar(geo, W, (tx0, y, zroof(tx0) - t), (cx, y, Z_RIDGE - 0.08), 0.05, 0.09)
        bar(geo, W, (tx1, y, zroof(tx1) - t), (cx, y, Z_RIDGE - 0.08), 0.05, 0.09)
    for x in (tx0, tx1):
        bar(geo, W, (x, ty0, Z_EAVE - 0.06), (x, ty1, Z_EAVE - 0.06), 0.05, 0.10)
    bar(geo, W, (tx1, ty1, Z_EAVE - 0.12), (tx1, ty1 + 0.95, Z_EAVE - 0.12), 0.07, 0.12)       # arm north (aerial, p19)
    h = 0.0
    # ---- swing beam west to the A-frame: two rails with rungs (monkey bars, aerial / frame 140500), the A-frame's
    # legs two-board ladders (p19) on a bottom rail, the tyre swing on three chains and a swivel
    (fn, fs, ap) = PL_AFRAME
    apex = np.array([ap[0], ap[1], Z_BEAM - 0.05])
    for y in PL_BEAM_Y:
        bar(geo, W, (13.73, y, Z_BEAM), (tx0, y, Z_BEAM), 0.09, 0.14)                            # end: p19
    for x in np.arange(ap[0] + 0.35, tx0 - 0.1, 0.32):
        bar(geo, W, (x, PL_BEAM_Y[0], Z_BEAM + 0.03), (x, PL_BEAM_Y[1], Z_BEAM + 0.03), 0.035, 0.035)
    bar(geo, W, (ap[0], PL_BEAM_Y[0] - 0.10, Z_BEAM - 0.10), (ap[0], PL_BEAM_Y[1] + 0.10, Z_BEAM - 0.10), 0.09, 0.09)
    for f in (fn, fs):
        foot = np.array([f[0], f[1], gz(*f) - 0.05])
        ladder(geo, foot, apex + np.sign(f[1] - ap[1]) * np.array([0, 0.12, 0]), w=0.30)
    bar(geo, W, (fn[0], fn[1], gz(*fn) + 0.07), (fs[0], fs[1], gz(*fs) + 0.07), 0.09, 0.14)      # bottom rail
    for y in PL_BEAM_Y:                                                                        # braces to the tower
        bar(geo, W, (tx0 - 0.75, y, Z_BEAM - 0.05), (tx0, y, Z_DECK - 0.35), 0.04, 0.12)
    tx, ty, ttop = PL_TIRE
    zt = ttop - 0.20
    F._revolve(geo, 'yard_tire', [(0.20, 0.0), (0.30, -0.06), (0.36, 0.04), (0.30, 0.14), (0.20, 0.08)], n=12,
               centre=(tx, ty, zt))
    sw = np.array([tx, PL_BEAM_Y[0], Z_BEAM - 0.55])
    bar(geo, 'yard_rope', sw, (tx, PL_BEAM_Y[0], Z_BEAM - 0.08), 0.015, 0.015)
    for k in range(3):
        a_ = 2 * math.pi * k / 3
        bar(geo, 'yard_rope', (tx + 0.28 * math.cos(a_), ty + 0.28 * math.sin(a_), zt + 0.10), sw, 0.012, 0.012)
    # ---- the small stand NW of the tower (p19): a base board on the chips, an A-frame with a centre post leaning
    # toward the tower, a green bar from its apex into the tower's north-west corner
    b0, b1 = np.array([16.20, 2.66]), np.array([17.75, 2.70])
    z0_, z1_ = gz(*b0), gz(*b1)
    bar(geo, W, (b0[0], b0[1], z0_ + 0.06), (b1[0], b1[1], z1_ + 0.06), 0.09, 0.14)
    m = (b0 + b1) / 2
    gs = gz(*m)
    ap2 = np.array([m[0], m[1] - 0.45, 3.52])                  # p19: the bar enters the tower just under its deck
    for p_ in (b0, b1, m):
        bar(geo, W, (p_[0], p_[1], gz(*p_) + 0.12), ap2, 0.05, 0.12)
    bar(geo, SLIDE, ap2 + np.array([0.0, 0.0, -0.02]), (tx0 + 0.05, ty1, ap2[2] - 0.02), 0.04, 0.04)
    # ---- the RAISED bridge south to the fort (p22: its floor at the tower's eave level, tall slat walls to the
    # ridge level; p19: the swings hang from its underside): deck, joists, posts at both ends, three swings
    (bx0, by0), (bx1, by1) = PL_BRIDGE
    a2, b2 = np.array([bx0, by0]), np.array([bx1, by1])
    dirb = (b2 - a2) / np.linalg.norm(b2 - a2)
    nb = np.array([-dirb[1], dirb[0]])
    hwb = 0.43
    corners = [a2 + nb * hwb, b2 + nb * hwb, b2 - nb * hwb, a2 - nb * hwb]
    geo.extrude(W, corners, Z_BRIDGE - 0.10, Z_BRIDGE)
    for sg in (-1, 1):
        slat_wall(geo, a2 + nb * sg * hwb, b2 + nb * sg * hwb, Z_BRIDGE, Z_BRIDGE_TOP)
        bar(geo, W, (*(a2 + nb * sg * hwb), Z_BRIDGE - 0.20), (*(b2 + nb * sg * hwb), Z_BRIDGE - 0.20), 0.06, 0.20)
        for e_ in (a2, b2):
            q = e_ + nb * sg * hwb
            geo.box(W, (q[0] - 0.05, q[1] - 0.05, gz(*q) - 0.1), (q[0] + 0.05, q[1] + 0.05, Z_BRIDGE_TOP + 0.05))
    for k in range(1, 5):                                                                      # ladder up at the fort end
        q0, q1 = b2 + nb * hwb, b2 - nb * hwb
        zz = gz(*b2) + 0.45 * k
        if zz < Z_BRIDGE - 0.3:
            bar(geo, SLIDE, (q0[0], q0[1], zz), (q1[0], q1[1], zz), 0.035, 0.035)
    swx = 17.85                                                                                # aerial: the seats
    for y in (-1.43, -2.20, -2.95):
        p0 = a2 + dirb * ((y - by0) / dirb[1])
        zb_ = Z_BRIDGE - 0.30
        gs_ = gz(swx, y)
        for dy in (-0.2, 0.2):
            bar(geo, 'yard_rope', (swx, y + dy, zb_), (swx, y + dy, gs_ + 0.55), 0.012, 0.012)
        geo.box(SLIDE, (swx - 0.10, y - 0.21, gs_ + 0.42), (swx + 0.10, y + 0.21, gs_ + 0.58))
    # ---- the fort: the hexagonal deck at 3.3 (slide deck) with slat walls, an upper landing at the bridge's level on
    # its north side with tall walls
    fort = np.array(PL_FORT)
    gf = gz(*fort.mean(0))
    geo.extrude(W, fort, Z_FORT - 0.10, Z_FORT)
    for i, p_ in enumerate(fort):
        top = Z_BRIDGE_TOP + 0.05 if i in (0, 1, 5) else Z_FORT_TOP + 0.08
        geo.box(W, (p_[0] - 0.05, p_[1] - 0.05, gz(*p_) - 0.1), (p_[0] + 0.05, p_[1] + 0.05, top))
        q = fort[(i + 1) % len(fort)]
        if i == 3:                                         # SW side: the long slide's opening (low rail only)
            slat_wall(geo, p_, q, Z_FORT_TOP - 0.45, Z_FORT_TOP)
        elif i == 0:                                       # north: under the landing
            continue
        else:
            slat_wall(geo, p_, q, Z_FORT, Z_FORT_TOP)
    land = [fort[5], fort[0], fort[1], fort[1] * 0.55 + fort[2] * 0.45, fort[5] * 0.55 + fort[4] * 0.45]
    land = [np.asarray(p_) for p_ in land]
    lc = np.array([land[3], land[4]])
    geo.extrude(W, [tuple(p_) for p_ in land], Z_BRIDGE - 0.10, Z_BRIDGE)
    for p_, q in ((land[4], land[0]), (land[1], land[2]), (land[2], land[3])):
        slat_wall(geo, p_, q, Z_BRIDGE, Z_BRIDGE_TOP)
    slat_wall(geo, lc[1], lc[0], Z_BRIDGE, Z_BRIDGE + 0.65)
    for z in (0.45, 0.85):
        bar(geo, SLIDE, (fort[1][0], fort[1][1], gf + z), (fort[2][0], fort[2][1], gf + z), 0.035, 0.035)
    # ---- slides: short wavy one east off the tower deck (aerial: its tip at (21.58, 1.24)), long one SW off the fort
    # deck (p19 its run-out end at (15.26, -7.07)); climbing ramp east of the tower (aerial: its foot at (21.08, 0.11))
    tip = np.array([21.58, 1.24])
    st = np.array([tx1, ty1 - 0.28])
    e = tip - (tip - st) / np.linalg.norm(tip - st) * 0.45
    slide(geo, (st[0], st[1], Z_DECK), (e[0], e[1], gz(*e)), wave=0.16)
    m = fort[3] * 0.2 + fort[4] * 0.8
    tip = np.array([15.26, -7.07])
    e = tip - (tip - m) / np.linalg.norm(tip - m) * 0.45
    slide(geo, (m[0], m[1], Z_FORT), (e[0], e[1], gz(*e)), w=0.55, wave=0.08, n=12)
    rx0, rx1, ry = tx1, 21.08, 0.11
    for dy in (-0.3, 0.3):
        bar(geo, W, (rx0, ry + dy, Z_DECK - 0.05), (rx1, ry + dy, gz(rx1, ry + dy)), 0.04, 0.12)
    for k in range(1, 9):
        t_ = k / 9
        x = rx0 + (rx1 - rx0) * t_
        zz = (Z_DECK - 0.05) * (1 - t_) + gz(rx1, ry) * t_ + 0.03
        bar(geo, W, (x, ry - 0.3, zz), (x, ry + 0.3, zz), 0.09, 0.03)
    return Part('yard_play_structure', geo, group='yard')


# =====================================================================================================================
# vegetable garden, fences
# =====================================================================================================================
def garden():
    geo = Geo()
    pts = GARDEN
    # every post / rail / picket bottom from the terrain (plan.ground_z: the ground zone carries the 2.55 level out to
    # the fence line; short bays so the fence follows what is left of the bank)
    for a, b in zip(pts[:-1], pts[1:]):
        picket_run(geo, a, b, bay=1.2)
    # the gate in the west fence where the gravel path arrives: a leaf swung open to the north-west
    a, b = np.array(pts[-1]), np.array(pts[0])
    Lg = Fr((a[0], a[1], 0.0), 100.0 + 55.0)
    w = float(np.linalg.norm(b - a)) - 0.08
    zl = lambda x: gz(*Lg.pt(x, 0.0)[:2])
    for z in (0.22, 0.85):
        bar(geo, PICKET, Lg.pt(0.04, 0.0, zl(0.04) + z + 0.045), Lg.pt(0.04 + w, 0.0, zl(0.04 + w) + z + 0.045), 0.04, 0.09)
    for i in range(int(w / 0.14)):
        x = 0.04 + (i + 0.5) * 0.14
        g = zl(x)
        Lg.box(geo, PICKET, (x - 0.035, 0.02, g + 0.06), (x + 0.035, 0.04, g + FENCE_H), 'xXyYZ')
    # raised beds: timber boxes ~0.35 m high with soil, on the terrain under them
    for (x0, y0), (x1, y1) in BEDS:
        cs = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
        zc = [gz(*q) for q in cs]
        g = max(zc)
        t, hb = 0.06, 0.38
        geo.extrude(PICKET, list(cs), min(zc) - 0.1, g + hb, cap_bottom=False,
                    holes=[[(x0 + t, y0 + t), (x1 - t, y0 + t), (x1 - t, y1 - t), (x0 + t, y1 - t)]])
        geo.poly('yard_soil', [(x0 + t, y0 + t, g + hb - 0.06), (x1 - t, y0 + t, g + hb - 0.06),
                               (x1 - t, y1 - t, g + hb - 0.06), (x0 + t, y1 - t, g + hb - 0.06)])
        for (px, py), zq in zip(cs, zc):
            geo.box(PICKET, (px - 0.05, py - 0.05, zq - 0.1), (px + 0.05, py + 0.05, g + hb + 0.04))
    return Part('yard_garden', geo, group='yard')


def fences():
    geo = Geo()
    # a low timber edge round the chips.  site.fence_play_north is NOT built: the picket shadows on the chips are the
    # garden's south fence's (they span exactly the garden's width; frame 139300 shows no fence at the play edge)
    ring = plan.site_ring('site.play_area')
    for a, b in zip(ring, np.roll(ring, -1, 0)):
        bar(geo, PICKET, (a[0], a[1], gz(*a) + 0.06), (b[0], b[1], gz(*b) + 0.06), 0.10, 0.16)
    # board fence on the upper terrace behind the fireplace: p22 shows weathered VERTICAL boards with gaps to the
    # right (SE) of the fireplace only, so only that stretch of the survey's guessed line is built (hidden in the aerial)
    a, b = plan.ground_ring(plan.site('site.fence_upper_terrace')['polyline'])
    L = float(np.linalg.norm(b - a))
    d = (b - a) / L
    a, b = a + d * 3.6, b - d * 0.5                        # (its SE end stops short of the gravel path)
    L = float(np.linalg.norm(b - a))
    deg = math.degrees(math.atan2(d[1], d[0]))
    nb = int(math.ceil(L / 2.4))
    for k in range(nb + 1):
        q = a + d * L * k / nb
        Fr((q[0], q[1], gz(*q)), deg).box(geo, 'fence_wood', (-0.05, -0.05, -0.2), (0.05, 0.05, 1.50))
    for k in range(nb):
        p, q = a + d * L * k / nb, a + d * L * (k + 1) / nb
        zp, zq = gz(*p), gz(*q)
        for r in (0.30, 1.20):
            bar(geo, 'fence_wood', (p[0], p[1], zp + r), (q[0], q[1], zq + r), 0.04, 0.09)
        n = int(np.linalg.norm(q - p) / 0.16)
        for i in range(n):
            t = (i + 0.5) / n
            c = p + (q - p) * t
            Fr((c[0], c[1], zp + (zq - zp) * t), deg).box(geo, 'fence_wood', (-0.07, 0.02, 0.05), (0.07, 0.04, 1.50), 'xXyYZ')
    return Part('yard_fences', geo, group='yard')


# =====================================================================================================================
# small things
# =====================================================================================================================
def path_light(geo, p, h=0.30):                 # frame 134300: cap ~0.3 m above the bed
    z = gz(*p)
    geo.cylinder('light_fixture', (p[0], p[1], z), (p[0], p[1], z + h), 0.012, n=6, cap=False)
    F._revolve(geo, 'light_fixture', [(0.0, h + 0.08), (0.09, h), (0.085, h - 0.015), (0.0, h - 0.01)], n=8,
               centre=(p[0], p[1], z))


def small():
    geo = Geo()
    # outdoor shower: not seen in any photo; the survey's guess (side yard against the SE wing): post + head + mat
    sx, sy = plan.ground_ring([plan.site('site.outdoor_shower')['point']])[0]
    z = gz(sx, sy)
    geo.box(PLAYWOOD, (sx - 0.45, sy - 0.45, z), (sx + 0.45, sy + 0.45, z + 0.04))
    geo.cylinder(STEEL, (sx, sy + 0.40, z), (sx, sy + 0.40, z + 2.15), 0.02, n=8)
    bar(geo, STEEL, (sx, sy + 0.40, z + 2.12), (sx, sy + 0.12, z + 2.12), 0.03, 0.03)
    geo.cylinder(STEEL, (sx, sy + 0.12, z + 2.12), (sx, sy + 0.12, z + 2.06), 0.07, n=10)
    # utility boxes
    for eid, size, mat in (('site.box_side_yard', (0.5, 0.5, 0.7), 'condenser_white'),
                           ('site.box_nw', (0.75, 0.75, 0.35), 'utility_grey'),
                           ('site.box_patio_bed', (0.4, 0.3, 0.12), 'foliage_dark')):
        x, y = plan.ground_ring([plan.site(eid)['point']])[0]
        z = gz(x, y)
        geo.box(mat, (x - size[0] / 2, y - size[1] / 2, z), (x + size[0] / 2, y + size[1] / 2, z + size[2]), 'xXyYZ')
    # garden lights: the globe light at the lawn corner (site.light_lawn), low path lights in the lounge beds
    x, y = plan.ground_ring([plan.site('site.light_lawn')['point']])[0]
    z = gz(x, y)
    geo.cylinder('light_fixture', (x, y, z), (x, y, z + 0.45), 0.012, n=6, cap=False)
    F._revolve(geo, 'light_glow', [(0.0, 0.45), (0.07, 0.48), (0.10, 0.55), (0.07, 0.62), (0.0, 0.65)], n=10, centre=(x, y, z))
    # frame 134300: one in the bed at the lounge's north corner; p22: one in the bed behind the umbrella's base
    for p in ((-0.42, 8.03), (5.8, 1.9)):
        path_light(geo, p)
    # frame 158300: a backless teak bench on the synthetic lawn's south edge near its SW corner, facing the lawn,
    # and two Adirondack chairs at the corner
    bench(geo, (8.5, -30.95, gz(8.5, -30.95)), 171.0, length=1.5)
    for (x, y), deg in (((5.90, -30.96), 172.0), ((5.18, -30.94), 190.0)):
        adirondack(geo, (x, y, gz(x, y)), deg)
    return Part('yard_small', geo, group='yard')


def build():
    return [fireplace(), lounge(), arbor(), porch_furniture(), play(), garden(), fences(), small()]
