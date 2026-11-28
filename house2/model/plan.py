"""The shared plan of house 2: the aerial as a plan, the ground levels, and the survey elements in world metres.

Every zone builder uses this module so that things sit on the same ground and in the same place:

    from model import plan
    plan.aerial_xy((u, v), z)          # aerial p29 pixel -> world (X, Y) where its ray meets height z
    plan.aerial_ring(poly_px, z)       # a whole pixel polygon -> (n, 2) world ring at height z
    plan.ground_z(x, y)                # terrain height (scalar or arrays), metres above the pool deck
    plan.site('site.pool_water')       # a site.json element (dict); plan.site_ring('site.pool_water') its ring
    plan.ground_ring(poly_px)          # ring placed on the terrain (rays meet the ground, 2 iterations)

World frame (survey/frame.json): X = the aerial's image right (the street lies ~50 m south of the lot, behind the
neighbour, reached by a lane from the gate at the image bottom-left),
Y = its image up (into the lot), Z up, metres; origin = the pool water's centre, Z = 0 the pool deck (rear flagstone
patio).  The aerial p29 is near-nadir from 49 m: things above the ground lean outward from the image centre, so a
pixel's world position depends on the height you give it (roof eaves at 3.4 / 6.4 m are 0.5-2 m off their ground
position) - always pass the element's real height.

Ground levels: REGIONS gives each surveyed area a level (from the SfM points inside it; the front from the photos:
the porch is 4 risers (0.72 m) above the front walk), ground_z interpolates smoothly between the areas (a membrane
solved on a 0.25 m grid) and holds each area flat at its level.  The terrain owner (zone 'ground') may refine REGIONS /
SLOPES; everything else reads ground_z at build time, so it follows.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from model import frame  # noqa: E402
from tools import cams as CAMS  # noqa: E402

AERIAL = 'photos/p29_ddf5dc.jpg'
SITE = {e['id']: e for e in json.load(open(os.path.join(HERE, 'survey', 'site.json')))['elements']}

# house datums (metres above the pool deck)
FLOOR = 0.45            # main floor
REAR_PATIO_FLOOR = 0.15  # covered rear patios (BG / PB), a step above the deck
NCP_FLOOR = 0.36        # north porch: 2 risers above the deck
FRONT_PORCH_FLOOR = 0.42
FRONT_WALK = -0.30      # front porch floor - 4 risers
EAVE_1, EAVE_2 = 3.40, 6.40

# area levels: site element id -> level (m).  SfM medians / low percentiles inside each polygon (n points), the front
# from the photos.  Sloping areas: SLOPES (id -> ((pixel, z), (pixel, z), ...)) fit a plane through the given points.
REGIONS = {
    # tree belts first (the areas below override them where they overlap): the ground under the boundary trees
    'site.trees_north': 1.0,            # rises behind the north wall toward the garden corner (SLOPES)
    'site.trees_east': 1.0,             # falls from the play area to the lawn's east curb (SLOPES)
    'site.trees_south': -0.6,           # street-side screen (SLOPES)
    'site.patio_pool': 0.0,             # n 7132
    'site.lawn_side_north': -0.15,      # n 1170 (points -0.1 .. -0.4); flush with the patio's edge (SLOPES)
    'site.bed_lounge': 0.0,
    'site.bed_lawn_terrace': -0.05,
    'site.bed_patio_tree': 0.0,
    'site.bed_patio_nw': 0.0,
    'site.bed_rear_courtyard': 0.05,
    'site.bed_upper_terrace': 0.50,     # between the low stone wall and the grey block wall (points 0.5-0.8 incl. plants)
    # synthetic lawn: the SfM points of the lawn shot tilt from -2.2 (west) to -0.5 (east) over 20 m (the lawn frames'
    # depth is biased: leaves on the turf triangulate 0.5 m inside the wall).  p18 (round 3): the lawn steps' 8 nosings
    # sit on the rows of 0.17 m risers rising from -0.45 (976 / 961 / 947 / 933 / 919 / 905 / 892 / 879 against the
    # photo's 977 / 963 / 949 / 934 / 920 / 907 / 893 / 880; 0.24 m risers from -0.70 put them 13 px apart at the foot),
    # and the wall's courses (5 + cap) give ~0.95 m under its 0.50 cap -> level at -0.45
    'site.lawn_synthetic': -0.45,
    'site.bed_lawn_south': -0.42,
    'site.hedge_lawn_west': -0.42,
    'site.bed_maple_round': -0.35,
    'site.planter_lawn': 0.40,          # raised planter west of the lawn steps, wall top (0.50) level with the lawn wall
    'site.planter_terrace': 0.50,       # lower planter behind the chevron wall (frame 133400: cap ~0.6 above the deck)
    'site.hedge_path': 1.65,            # hedge strip between the planter wall and the gravel path (points 1.6-1.8)
    'site.play_area': 2.00,             # n 6097: 1.8 (west) .. 2.2 (east); p19 bundle points rise north too (SLOPES)
    # site.strip_garden_play has no level of its own: it is the bank between the garden (2.55, carried to its fence
    # line and a margin: ground.PADS), the path (1.9-2.5) and the play area (1.85-2.2) -- the membrane between them
    'site.garden_enclosure': 2.55,      # n 608
    # the gravel path: level with the play area's timber edge (no cross-fall).  Its ends are not level: zone 'ground'
    # (ground.PROFILES) takes it up to ~2.45 at the garden gate and down to 0.50 at the top of the lawn steps
    'site.path_gravel': 1.80,
    'site.bed_maple_stairs': 1.10,      # the bank between the wall east of the patio (0.5 behind its cap) and the path (SLOPES)
    'site.orchard': 1.20,               # 1.9-2.0 along the play area, a bank down to the lawn wall (SLOPES)
    'site.driveway': -0.40,             # n 90, p30 -0.26; level along the garage, falls toward the street (SLOPES)
    'site.walk_front': FRONT_WALK,
    'site.lawn_front_upper': -0.35,
    'site.lawn_front_lower': -0.55,
    'site.bed_porch': -0.25,
    'site.bed_landing': -0.30,
    'site.bed_birch': -0.30,
    'site.bed_garage': -0.30,
    'site.bed_court_recess': -0.30,
    'site.bed_front_south': -0.45,
    'site.bed_south_strip': -0.80,
    'site.bed_north_side': -0.15,
    'site.bed_se_wing': -0.10,
    'site.walk_rear_curved': -0.05,
}
SLOPES = {
    # the driveway falls from the motor court (garage) toward the gate at the image bottom-left
    # one plane, no cross-fall (zone 'ground' meshes it in two pieces: level -0.30 to v 1000, then the fall to the gate)
    'site.driveway': (((100, 540), -0.30), ((500, 540), -0.30), ((120, 1750), -0.95)),
    'site.lawn_side_north': (((1270, 342), -0.05), ((1060, 359), -0.05), ((1120, 177), -0.22)),
    'site.bed_maple_stairs': (((1668, 500), 0.35), ((1668, 660), 0.35), ((1775, 580), 1.70)),
    # the chips: p19's bundle (with frames 125.0 / 139.0 / 140.5 s and the aerial) puts the edging's SW corner at 1.65,
    # the A-frame's north foot 2.08, the stand's feet 2.25 / 2.30, the slide's foot 2.39 (a plane through them within
    # 1 cm: +0.039 / m east, +0.040 / m north); the east corners held near the garden pad (2.55) and the SfM east value
    'site.play_area': (((1815, 896), 1.65), ((1851, 542), 2.08), ((1950, 497), 2.25), ((2006, 495), 2.30),
                       ((2140, 546), 2.39), ((2327, 895), 2.20), ((2336, 450), 2.55)),
    # the lawn wall's cap is at 0.50: the bank rises straight from just under the cap (p18: no shelf) at ~0.15 / m to
    # the play area's edge; p18 puts the ground at the fruit trees (v 1105) at 1.0 (fruit_1) / 1.13 (fruit_2)
    'site.orchard': (((1900, 905), 1.90), ((2300, 905), 2.05), ((1950, 1210), 0.47), ((2300, 1210), 0.50)),
    'site.trees_north': (((400, 60), 0.80), ((1300, 60), 1.20), ((2100, 60), 2.40), ((1300, 140), 1.20)),
    'site.trees_east': (((2420, 500), 2.45), ((2420, 1100), 1.00), ((2420, 1500), -0.20), ((2480, 1100), 1.00)),
    'site.trees_south': (((300, 1750), -1.00), ((1200, 1720), -0.60), ((2300, 1700), -0.55), ((1200, 1850), -0.70)),
}
GRID = 0.25
EXTENT = (-46.0, -42.0, 36.0, 22.0)   # x0, y0, x1, y1: the aerial's ground footprint
_CAM = {}
_DTM = {}


def _cam():
    if not _CAM:
        _CAM['c'] = frame.world_cams()[AERIAL]
    return _CAM['c']


def aerial_xy(uv, z):
    """World (X, Y) of aerial pixel(s) uv at height(s) z."""
    uv = np.atleast_2d(np.asarray(uv, float))
    o, d = CAMS.ray(_cam(), uv)
    t = (np.asarray(z, float) - o[2]) / d[:, 2]
    xy = o[:2] + t[:, None] * d[:, :2]
    return xy[0] if xy.shape[0] == 1 and np.ndim(uv) == 2 and len(uv) == 1 else xy


def aerial_ring(poly_px, z):
    return np.atleast_2d(aerial_xy(np.asarray(poly_px, float), np.full(len(poly_px), z)))


def to_aerial(P):
    """World points -> aerial pixels (checks, overlays)."""
    return CAMS.project(_cam(), np.asarray(P, float))


def site(eid):
    return SITE[eid]


def site_ring(eid, z=None):
    """An element's polygon as a world ring; at its REGIONS level unless z is given (default: on the terrain)."""
    e = SITE[eid]
    if z is None:
        return ground_ring(e['poly'])
    return aerial_ring(e['poly'], z)


def ground_ring(poly_px, iters=2):
    poly_px = np.asarray(poly_px, float)
    z = np.zeros(len(poly_px))
    for _ in range(iters):
        xy = np.atleast_2d(aerial_xy(poly_px, z))
        z = ground_z(xy[:, 0], xy[:, 1])
    return np.atleast_2d(aerial_xy(poly_px, z))


def _region_level(eid, xy):
    lvl = REGIONS[eid]
    if eid in SLOPES:
        pts = SLOPES[eid]
        A, b = [], []
        for uv, z in pts:
            x, y = aerial_xy(uv, z)
            A.append([x, y, 1.0])
            b.append(z)
        coef = np.linalg.lstsq(np.array(A), np.array(b), rcond=None)[0]
        return xy @ coef[:2] + coef[2]
    return np.full(len(xy), lvl)


def _dtm():
    """Terrain grid: area cells fixed at their levels, the rest a membrane (Laplace) between them."""
    if _DTM:
        return _DTM['g']
    from shapely import contains_xy
    from shapely.geometry import Polygon
    from scipy.sparse import lil_matrix
    from scipy.sparse.linalg import spsolve
    x0, y0, x1, y1 = EXTENT
    xs = np.arange(x0, x1 + 1e-9, GRID)
    ys = np.arange(y0, y1 + 1e-9, GRID)
    X, Y = np.meshgrid(xs, ys)
    Z = np.full(X.shape, np.nan)
    for eid in REGIONS:
        if eid not in SITE or 'poly' not in SITE[eid]:
            continue
        lvl0 = REGIONS[eid]
        ring = aerial_ring(SITE[eid]['poly'], lvl0)
        pg = Polygon(ring).buffer(0)
        m = contains_xy(pg, X, Y)
        Z[m] = _region_level(eid, np.c_[X[m], Y[m]])
    fixed = np.isfinite(Z)
    # membrane over the free cells; the grid's border is free too (natural boundary)
    H, W = Z.shape
    idx = -np.ones(Z.shape, int)
    free = np.argwhere(~fixed)
    idx[~fixed] = np.arange(len(free))
    A = lil_matrix((len(free), len(free)))
    b = np.zeros(len(free))
    for k, (i, j) in enumerate(free):
        nb = [(i + di, j + dj) for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)) if 0 <= i + di < H and 0 <= j + dj < W]
        A[k, k] = len(nb)
        for p, q in nb:
            if fixed[p, q]:
                b[k] += Z[p, q]
            else:
                A[k, idx[p, q]] = -1
    if len(free):
        A[0, 0] += 1e-9
        Z[~fixed] = spsolve(A.tocsr(), b)
    # the ground zone's refinement (wall breaks, the path's profile, the level motor court): every zone stands on it
    _DTM['refined'] = True
    from model.zones import ground
    Z = ground.refine_dtm(xs, ys, Z)
    _DTM['g'] = (xs, ys, Z)
    return _DTM['g']


def ground_z(x, y):
    """Terrain height at world (x, y) (bilinear on the grid; arrays welcome)."""
    xs, ys, Z = _dtm()
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    fx = np.clip((x - xs[0]) / GRID, 0, len(xs) - 1.001)
    fy = np.clip((y - ys[0]) / GRID, 0, len(ys) - 1.001)
    i, j = fy.astype(int), fx.astype(int)
    ty, tx = fy - i, fx - j
    z = (Z[i, j] * (1 - tx) * (1 - ty) + Z[i, j + 1] * tx * (1 - ty) + Z[i + 1, j] * (1 - tx) * ty
         + Z[i + 1, j + 1] * tx * ty)
    return z if z.ndim else float(z)


if __name__ == '__main__':
    xs, ys, Z = _dtm()
    print('terrain grid %d x %d, z %.2f .. %.2f' % (len(xs), len(ys), np.nanmin(Z), np.nanmax(Z)))
    for eid in ('site.pool_water', 'site.play_area', 'site.lawn_synthetic', 'site.lawn_front_lower'):
        r = site_ring(eid)
        print('%-22s centre %s  ground %.2f' % (eid, np.round(r.mean(0), 2), ground_z(*r.mean(0))))
