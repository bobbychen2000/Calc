"""Zone 'yard' of house 2: the built things in the garden (white model: massing + correct shapes).

  fireplace      fieldstone outdoor fireplace NE of the pool (cap 4.1 m above the deck: tools/epi.py, aerial cap ->
                 frames 125900 / 158300) with its hearth / seat wall, facing SW over the lounge
  lounge         2 teak loveseats facing each other over a coffee table, 2 armchairs, 2 side tables (aerial + frame
                 140500), the closed umbrella on its base block
  arbor          dark timber pergola SE of the pool (45 deg to the lot like the pool): 4 white columns on stone
                 pedestals, 2 double beams, close rafters with tails, a vine mat on top; bar counter + 6 stools on the
                 pool side, L-shaped BBQ counter with the grill on the back side, lanterns
  porch_furniture   the north porch's 10-seat teak dining set, the BG patio's two armchairs + table, the PB patio's
                 table with two benches, pots
  play           the play structure in the chip yard: roofed tower (ridge N-S), bridge south to the open fort, swing
                 beam west to an A-frame (tire swing), swings under the bridge, green slides east / south-west, ramp
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
    'yard_cushion_white': dict(color=(0.80, 0.79, 0.76), roughness=1.0),
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
UMBRELLA = (4.98, 1.46)
# arbor: west corner of the rafter field (aerial outline at z 3), x along its pool side (toward NE), -y into it (SE)
AR_O, AR_ANG = (2.2, -11.2), 45.0
AR_L, AR_D = 5.7, 5.0                 # rafter field: along the pool side x rafter length
AR_COL_X, AR_COL_Y = (0.55, 5.15), (-1.0, -4.4)
AR_BEAM_Z, AR_TOP = 2.35, 3.00        # under the beams (survey est. column 2.4); rafter top: p26 / frame 134300 (0.65 m of timber)
# play structure (aligned with the lot axes; heights above the chips: typical swing-set values checked on p19)
PL_TOWER = (18.25, 0.45)              # centre of the roofed tower
PL_TOWER_S = 2.0                      # its deck, square
PL_DECK, PL_RAIL, PL_EAVE, PL_RIDGE, PL_BEAM = 1.30, 2.10, 2.30, 3.35, 2.15     # ridge / fort top: p28
PL_BRIDGE_X = 18.55                   # bridge centre line, runs south to the fort
# fort deck: a ~1.5 m hexagon turned 45 deg (frame 140500 corners at deck height); edge 0-1 = the bridge's, 3-4 = the slide's
PL_FORT = [(18.24, -3.60), (19.06, -4.17), (19.13, -4.75), (18.45, -5.46), (17.75, -4.75), (17.70, -4.11)]
PL_FORT_TOP = 2.65
PL_AFRAME_X, PL_BEAM_Y = 13.55, 0.30
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
    hw, dp = 1.35, 1.25                                            # firebox body: half width, depth
    # hearth / seat wall along the front (site.seat_wall_fireplace: 1.9 m left, 2.3 m right of the shaft axis)
    hz = 0.52                                                      # hearth top (p22)
    L.box(geo, STONE, (-2.0, -0.50, -0.3), (2.35, 0.0, hz - 0.06), 'xXyY')
    L.box(geo, CAP, (-2.03, -0.54, hz - 0.06), (2.38, 0.02, hz))
    # body, vertical to 2.45 (p22 proportions on the 4.10 m top and the 2.7 m body width), arched firebox 1.24 wide
    zb = 2.45
    ow, oz0, oz1, rise = 0.62, hz, 0.98, 0.32
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


def umbrella(geo, at, top=3.15):                  # frame 134300: top ~3.15 m, canopy ~0.6 m across, hem ~0.85 m (p22)
    """Closed cantilever umbrella: square base block, offset mast with a short arm, the draped canopy hanging from it."""
    L = Fr(at, 45.0)
    L.box(geo, CAP, (-0.64, -0.42, 0), (0.20, 0.42, 0.14))
    geo.cylinder(TIMBER, L.pt(-0.22, 0, 0.14), L.pt(-0.22, 0, top), 0.04, n=8)
    bar(geo, TIMBER, L.pt(-0.22, 0, top - 0.04), L.pt(0.0, 0, top - 0.04), 0.05, 0.06)
    F._revolve(geo, 'yard_umbrella', [(0.03, 0.85), (0.28, 0.90), (0.31, 1.30), (0.25, 1.95), (0.19, 2.55),
                                      (0.10, top - 0.12), (0.0, top - 0.02)], n=10, centre=tuple(L.pt(0, 0, 0)))


def lounge():
    geo = Geo()
    F.teak_sofa(geo, LOUNGE['sofa_w'], 45.0, length=1.75, pillows=2, seed=1)       # faces SE
    F.teak_sofa(geo, LOUNGE['sofa_s'], -135.0, length=1.75, pillows=2, seed=2)     # faces NW
    F.teak_armchair(geo, LOUNGE['chair_n'], -20.0, seed=3)
    F.teak_armchair(geo, LOUNGE['chair_e'], -70.0, seed=4)
    F.teak_coffee_table(geo, LOUNGE['coffee'], 45.0, length=1.45, width=1.20, height=0.36)
    side_table(geo, LOUNGE['side_wood'], 45.0)
    side_table(geo, LOUNGE['side_dark'], 45.0, mat='furn_black')
    umbrella(geo, (UMBRELLA[0] + 0.11, UMBRELLA[1] + 0.11))   # canopy axis; the mast stands on the base's centre
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


def arbor():
    geo = Geo()
    L = Fr((AR_O[0], AR_O[1], 0.0), AR_ANG)
    # square white columns from the deck to the beams (p26 / p20); only the pool-side NE one stands on the bar's
    # stone pier (rear.arbor_columns)
    cw = 0.18
    for cx in AR_COL_X:
        for cy in AR_COL_Y:
            p = L.pt(cx, cy)
            z0 = min(gz(p[0], p[1]), 0.45)
            if cx == AR_COL_X[1] and cy == AR_COL_Y[0]:
                L.box(geo, STONE, (cx - 0.30, cy - 0.30, z0 - 0.2), (cx + 0.30, cy + 0.30, 1.02), 'xXyY')
                L.box(geo, CAP, (cx - 0.33, cy - 0.33, 1.02), (cx + 0.33, cy + 0.33, 1.08))
                z0 = 1.08
                L.box(geo, WHITE, (cx - cw - 0.03, cy - cw - 0.03, z0), (cx + cw + 0.03, cy + cw + 0.03, z0 + 0.10), 'xXyYZ')
            else:
                L.box(geo, WHITE, (cx - cw - 0.03, cy - cw - 0.03, z0 - 0.2), (cx + cw + 0.03, cy + cw + 0.03, z0 + 0.26), 'xXyYZ')
            L.box(geo, WHITE, (cx - cw, cy - cw, z0), (cx + cw, cy + cw, AR_BEAM_Z - 0.10), 'xXyY')
            L.box(geo, WHITE, (cx - cw - 0.04, cy - cw - 0.04, AR_BEAM_Z - 0.10), (cx + cw + 0.04, cy + cw + 0.04, AR_BEAM_Z))
    # double beams over each column row, rafters across with tails, three purlins on top
    for cy in AR_COL_Y:
        for dy in (-0.13, 0.13):
            L.box(geo, TIMBER, (-0.25, cy + dy - 0.045, AR_BEAM_Z), (AR_L + 0.25, cy + dy + 0.045, AR_BEAM_Z + 0.28))
    nr = int(round(AR_L / 0.30))
    for i in range(nr + 1):
        x = AR_L * i / nr
        L.box(geo, TIMBER, (x - 0.035, -AR_D, AR_BEAM_Z + 0.28), (x + 0.035, 0.0, AR_TOP - 0.04))
    for cy in (-0.6, -AR_D / 2, -AR_D + 0.6):
        L.box(geo, TIMBER, (-0.1, cy - 0.03, AR_TOP - 0.04), (AR_L + 0.1, cy + 0.03, AR_TOP))
    # the vine mat (climbing roses) over the rafters and its old trunk at the north pool-side column
    # a mound 0.6-1.0 m high (p20 / p26), overhanging the rafter ends: low rounded domes (placeholder for planting)
    rng = np.random.default_rng(3)
    domes = [(AR_L * 0.5, -AR_D * 0.5, 2.6, 0.95), (1.3, -1.3, 1.7, 0.75), (AR_L - 1.2, -1.2, 1.8, 0.85),
             (1.4, -AR_D + 1.3, 1.7, 0.70), (AR_L - 1.3, -AR_D + 1.3, 1.8, 0.80), (AR_L * 0.5, -0.6, 1.5, 0.70),
             (AR_L * 0.5, -AR_D + 0.7, 1.5, 0.65), (0.5, -AR_D * 0.5, 1.4, 0.65), (AR_L - 0.4, -AR_D * 0.5, 1.4, 0.70)]
    for x, y, r, h in domes:
        r *= rng.uniform(0.92, 1.08)
        F._revolve(geo, 'yard_vine', [(r, -0.12), (r * 0.97, h * 0.22), (r * 0.80, h * 0.62), (r * 0.48, h * 0.90), (0.0, h)],
                   n=9, centre=tuple(L.pt(x, y, AR_TOP - 0.08)))
    cx, cy = AR_COL_X[1], AR_COL_Y[0]
    geo.cylinder('bark', L.pt(cx + 0.42, cy + 0.10, 0), L.pt(cx + 0.24, cy, AR_TOP), 0.06, n=6, cap=False)
    # bar counter on the pool side from the NE column's pier over ~70 % of the bay (p26), 5 stools outside it: four
    # with backs, the backless one at the SW end (rear.bar_stools)
    bx0, bx1, by0, by1 = 1.90, AR_COL_X[1] - 0.30, -1.55, -0.95
    L.box(geo, STONE, (bx0, by0, 0), (bx1, by1, 1.02), 'xXyY')
    L.box(geo, CAP, (bx0 - 0.05, by0 - 0.05, 1.02), (bx1 + 0.05, by1 + 0.25, 1.08))
    for i, x in enumerate((1.80, 2.32, 3.05, 3.78, 4.50)):
        stool(geo, L, x, -0.42, back=i != 0)
    # BBQ counter along the back row with the grill, an L leg up the NE end to the bar
    gx0, gx1, gy0, gy1 = 0.95, 4.85, -4.75, -4.05
    L.box(geo, STONE, (gx0, gy0, 0), (gx1, gy1, 0.90), 'xXyY')
    L.box(geo, CAP, (gx0 - 0.04, gy0 - 0.04, 0.90), (gx1 + 0.04, gy1 + 0.04, 0.95))
    L.box(geo, STONE, (gx1 - 0.65, gy1, 0), (gx1, by0, 0.90), 'xXyY')
    L.box(geo, CAP, (gx1 - 0.69, gy1 + 0.04, 0.90), (gx1 + 0.04, by0 + 0.04, 0.95))
    L.box(geo, STEEL, (2.15, gy0 + 0.06, 0.95), (3.05, gy1 - 0.08, 1.02))
    L.box(geo, STEEL, (2.17, gy0 + 0.16, 1.02), (3.03, gy1 - 0.10, 1.26))
    L.box(geo, STEEL, (2.15, gy1 - 0.01, 0.30), (3.05, gy1 + 0.015, 0.84), 'xXYzZ')
    L.box(geo, STEEL, (3.9, gy0 + 0.2, 0.951), (4.3, gy1 - 0.15, 0.956), 'Z')            # bar sink
    # lanterns on the columns (p20: on the faces toward the kitchen; p26: toward the pool)
    for cx, cy, sgn in ((AR_COL_X[0], AR_COL_Y[0], 1), (AR_COL_X[1], AR_COL_Y[0], 1), (AR_COL_X[0], AR_COL_Y[1], -1),
                        (AR_COL_X[1], AR_COL_Y[1], -1)):
        X.lantern(geo, L.pt(cx, cy + sgn * 0.18, 1.80), L.ex * sgn, L.ey * sgn, h=0.40, w=0.17, d=0.115)
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
    tw, off = 0.76, 0.50                                  # table width; chair centres from the table's centre line
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


def play():
    geo = Geo()
    cx, cy = PL_TOWER
    g = gz(cx, cy)
    h = PL_TOWER_S / 2
    W = PLAYWOOD
    # ---- roofed tower: 4 posts, deck, lower frame, slat rails, gabled board roof (ridge N-S)
    for sx in (-1, 1):
        for sy in (-1, 1):
            geo.box(W, (cx + sx * h - 0.05, cy + sy * h - 0.05, g - 0.1), (cx + sx * h + 0.05, cy + sy * h + 0.05, g + PL_EAVE))
    geo.box(W, (cx - h, cy - h, g + PL_DECK - 0.10), (cx + h, cy + h, g + PL_DECK))
    geo.box(W, (cx - h, cy - h, g + 0.12), (cx + h, cy + h, g + 0.22), 'xXyYZ')                 # base frame
    for z in (0.55, 0.95):                                                                     # climbing rungs
        bar(geo, SLIDE, (cx - h, cy - h, g + z), (cx + h, cy - h, g + z), 0.035, 0.035)
        bar(geo, SLIDE, (cx - h, cy + h, g + z), (cx + h, cy + h, g + z), 0.035, 0.035)
    z0, z1 = g + PL_DECK, g + PL_RAIL
    slat_wall(geo, (cx - h, cy + h), (cx + h, cy + h), z0, z1)                                 # north
    slat_wall(geo, (cx - h, cy + h), (cx - h, cy + 0.45), z0, z1)                              # west, beam gap
    slat_wall(geo, (cx - h, cy - 0.45), (cx - h, cy - h), z0, z1)
    slat_wall(geo, (cx - h, cy - h), (cx - 0.25, cy - h), z0, z1)                              # south, bridge gap
    slat_wall(geo, (cx + h, cy - 0.35), (cx + h, cy + 0.35), z0, z1)                            # east, between ramp and slide
    ov, t = 0.22, 0.05
    hw = h + ov
    rise = PL_RIDGE - PL_EAVE
    for s in (-1, 1):
        e0 = np.array([cx + s * hw, cy - hw, g + PL_EAVE - ov * rise / h])
        e1 = np.array([cx + s * hw, cy + hw, g + PL_EAVE - ov * rise / h])
        r0, r1 = np.array([cx, cy - hw, g + PL_RIDGE]), np.array([cx, cy + hw, g + PL_RIDGE])
        quad = [e0, e1, r1, r0] if s > 0 else [e1, e0, r0, r1]
        geo.poly(W, quad)
        geo.poly(W, [q - UP * t for q in quad[::-1]])
    for sy in (-1, 1):                                                                         # gable frames
        y = cy + sy * h
        bar(geo, W, (cx - h, y, g + PL_EAVE), (cx + h, y, g + PL_EAVE), 0.05, 0.10)
        bar(geo, W, (cx - h, y, g + PL_EAVE), (cx, y, g + PL_RIDGE - 0.06), 0.05, 0.09)
        bar(geo, W, (cx + h, y, g + PL_EAVE), (cx, y, g + PL_RIDGE - 0.06), 0.05, 0.09)
    for sx in (-1, 1):
        bar(geo, W, (cx + sx * h, cy - h, g + PL_EAVE), (cx + sx * h, cy + h, g + PL_EAVE), 0.05, 0.10)
    # ---- swing beam west to the A-frame: a double beam with rungs (monkey bars), tire swing
    ax, by = PL_AFRAME_X, PL_BEAM_Y
    ga = gz(ax, by)
    zb = g + PL_BEAM
    for dy in (-0.24, 0.24):
        bar(geo, W, (ax - 0.25, by + dy, zb), (cx - h, by + dy, zb), 0.09, 0.14)
    for x in np.arange(ax + 0.3, cx - h - 0.1, 0.32):
        bar(geo, W, (x, by - 0.24, zb), (x, by + 0.24, zb), 0.035, 0.035)
    for sy in (-1, 1):
        bar(geo, W, (ax, by + sy * 0.26, zb + 0.05), (ax - 0.1, by + sy * 1.25, ga - 0.05), 0.09, 0.09)
    bar(geo, W, (ax - 0.05, by - 0.75, ga + 1.05), (ax - 0.05, by + 0.75, ga + 1.05), 0.04, 0.12)
    bar(geo, W, (ax - 0.09, by - 1.15, ga + 0.25), (ax - 0.09, by + 1.15, ga + 0.25), 0.04, 0.12)
    tx = ax + 1.45
    gt = gz(tx, by)
    F._revolve(geo, 'yard_tire', [(0.20, 0.42), (0.30, 0.36), (0.36, 0.46), (0.30, 0.56), (0.20, 0.50)], n=12,
               centre=(tx, by, gt))
    for k in range(3):
        a = 2 * math.pi * k / 3
        bar(geo, 'yard_rope', (tx + 0.28 * math.cos(a), by + 0.28 * math.sin(a), gt + 0.52), (tx, by, zb - 0.07), 0.015, 0.015)
    # ---- a low A-frame stand NW of the tower with a rail to its corner (aerial, p28)
    sx_, sy_ = 16.57, 2.55
    gs = gz(sx_, sy_)
    for dx in (-0.5, 0.5):
        bar(geo, W, (sx_, sy_, gs + 1.2), (sx_ + dx, sy_ + 0.25, gs - 0.05), 0.07, 0.07)
    bar(geo, W, (sx_, sy_, gs + 1.2), (cx - h, cy + h, g + PL_DECK + 0.3), 0.05, 0.05)
    # ---- bridge south to the fort, with slat rails; three swings hang from its west beam
    bx = PL_BRIDGE_X
    y0, y1 = cy - h, -3.90
    geo.box(W, (bx - 0.5, y1, g + PL_DECK - 0.08), (bx + 0.5, y0, g + PL_DECK))
    for sx in (-1, 1):
        slat_wall(geo, (bx + sx * 0.5, y0), (bx + sx * 0.5, y1), z0, z1)
    swx = bx - 0.62
    bar(geo, W, (swx, y0 + 0.1, g + PL_BEAM + 0.1), (swx, y1 - 0.1, g + PL_BEAM + 0.1), 0.09, 0.14)
    for k, y in enumerate(np.linspace(y0 - 0.55, y1 + 0.55, 3)):
        for dy in (-0.2, 0.2):
            bar(geo, 'yard_rope', (swx, y + dy, g + PL_BEAM + 0.03), (swx, y + dy, g + 0.50), 0.012, 0.012)
        geo.box(SLIDE, (swx - 0.08, y - 0.22, g + 0.46), (swx + 0.08, y + 0.22, g + (0.50 if k == 0 else 0.70)))
    # ---- the fort: posts at its corners, deck, tall slat walls
    fort = np.array(PL_FORT)
    gf = gz(*fort.mean(0))
    geo.extrude(W, fort, gf + PL_DECK - 0.10, gf + PL_DECK)
    for i, p in enumerate(fort):
        geo.box(W, (p[0] - 0.05, p[1] - 0.05, gf - 0.1), (p[0] + 0.05, p[1] + 0.05, gf + PL_FORT_TOP + 0.08))
        q = fort[(i + 1) % len(fort)]
        if i == 0:                                         # north side: the bridge's opening
            continue
        elif i == 3:                                       # SW side: the long slide's opening (low rail only)
            slat_wall(geo, p, q, gf + PL_FORT_TOP - 0.6, gf + PL_FORT_TOP)
        else:
            slat_wall(geo, p, q, gf + PL_DECK, gf + PL_FORT_TOP)
    for z in (0.45, 0.85):
        bar(geo, SLIDE, (fort[1][0], fort[1][1], gf + z), (fort[2][0], fort[2][1], gf + z), 0.035, 0.035)
    # ---- slides: short wavy one east off the tower, long one SW off the fort; climbing ramp east of the tower
    e = (cx + h + 1.85, cy + 0.88)                          # frame 140500: its end at (21.6, 1.25)
    slide(geo, (cx + h, cy + 0.65, g + PL_DECK), (e[0], e[1], gz(*e)), wave=0.16)
    m = fort[3] * 0.2 + fort[4] * 0.8
    e = (15.25, -6.75)                                      # frame 140500: the run-out ends at (14.95, -7.0)
    slide(geo, (m[0], m[1], gf + PL_DECK), (e[0], e[1], gz(*e)), w=0.55, wave=0.08, n=10)
    rx0, rx1, ry = cx + h, cx + h + 2.3, cy - 0.72
    for dy in (-0.3, 0.3):
        bar(geo, W, (rx0, ry + dy, g + PL_DECK - 0.05), (rx1, ry + dy, gz(rx1, ry)), 0.04, 0.12)
    for k in range(1, 9):
        t_ = k / 9
        bar(geo, W, (rx0 + (rx1 - rx0) * t_, ry - 0.3, g + (PL_DECK - 0.05) * (1 - t_) + 0.03),
            (rx0 + (rx1 - rx0) * t_, ry + 0.3, g + (PL_DECK - 0.05) * (1 - t_) + 0.03), 0.09, 0.03)
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
