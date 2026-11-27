"""The shared plan of house 2: the aerial as a plan, the ground levels, and the survey elements in world metres.

Every zone builder uses this module so that things sit on the same ground and in the same place:

    from model import plan
    plan.aerial_xy((u, v), z)          # aerial p29 pixel -> world (X, Y) where its ray meets height z
    plan.aerial_ring(poly_px, z)       # a whole pixel polygon -> (n, 2) world ring at height z
    plan.ground_z(x, y)                # terrain height (scalar or arrays), metres above the pool deck
    plan.site('site.pool_water')       # a site.json element (dict); plan.site_ring('site.pool_water') its ring
    plan.ground_ring(poly_px)          # ring placed on the terrain (rays meet the ground, 2 iterations)

World frame (survey/frame.json): X = the aerial's image right (along the street, which runs along the image bottom),
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
    'site.patio_pool': 0.0,             # n 7132
    'site.lawn_side_north': -0.15,      # n 1170
    'site.bed_lounge': 0.0,
    'site.bed_lawn_terrace': -0.05,
    'site.bed_patio_tree': 0.0,
    'site.bed_rear_courtyard': 0.05,
    'site.bed_upper_terrace': 0.75,     # above the lower terrace wall
    'site.lawn_synthetic': -1.80,       # n 1191
    'site.bed_lawn_south': -1.75,
    'site.play_area': 2.10,             # n 6097
    'site.strip_garden_play': 2.25,
    'site.garden_enclosure': 2.55,      # n 608
    'site.path_gravel': 1.90,           # n 1159
    'site.orchard': 1.60,               # n 5321 (trees above)
    'site.driveway': -0.40,             # n 90, p30 -0.26; falls toward the street (SLOPES)
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
    'site.driveway': (((300, 760), -0.30), ((150, 1100), -0.40), ((120, 1800), -1.10)),
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
