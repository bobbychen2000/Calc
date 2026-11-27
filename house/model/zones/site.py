"""The grounds: street, driveway, front lawn behind its stone planter wall, side yards, rear patio with the louvred
pergola, the lawns, the pool on its terrace, the pool cabana, fences, planting, furniture and a simple backdrop.

Plan positions are read from the registered top-down aerial photo (tools/p30w.py: a 1 m grid drawn through its
camera), heights from the drone point cloud and the registered ground photos (street -0.5, garage slab 0.36, front
lawn 0.4, main floor and rear patio 1.0, rear lawn 0.55 .. 0.95, pool coping 1.25, cabana terrace 1.55).
"""
import numpy as np

from model import fixtures as FX
from model import furniture as FU
from model import openings as OP
from model import plants as PL
from model import pool as pool_kit
from model.kit import Geo, Part
from model.massing_kit import hip_roof, roof_planes
from model.zones.house import roof_details

FENCE_W, FENCE_E, FENCE_N = -2.8, 27.8, 36.9
Z_ST, Z_LAWN_F, Z_PATIO, Z_POOL, Z_CAB = -0.5, 0.38, 1.0, 1.25, 1.55
Z_LAWN_E, Z_LAWN_W = 0.95, 0.55                    # rear lawn: level with the patio at the pergola, lower at the laundry
CURB_Y = 24.3                                      # low wall between the main lawn and the pool terrace
POOL_AT = dict(origin=(0.3, 27.2, Z_POOL), length=16.9, width=5.6)
CAB = dict(x0=21.4, x1=26.0, y0=27.5, y1=34.0, plate=4.05)          # cabana walls (plan) / top of its walls
TERR = dict(x0=17.75, x1=27.6, y0=24.8, y1=35.9)                    # cabana terrace


LAWNS = []          # every lawn outline (world), for cleaning the aerial photograph of the oak's branches


def flat(g, mat, ring, z, holes=()):
    """Ground polygon facing up, whatever the ring's winding; z a height or a function of (x, y)."""
    zf = z if callable(z) else (lambda x, y: z)
    ring = list(ring)
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1]))
    if area < 0:
        ring = ring[::-1]
    g.poly(mat, [(x, y, zf(x, y)) for x, y in ring], holes=[[(x, y, zf(x, y)) for x, y in h] for h in holes],
           uv_u=(1.0, 0.0, 0.0), uv_o=(0.0, 0.0, 0.0))            # textures anchored to the world: no jump between pieces
    if mat == 'lawn':
        LAWNS.append(([(x, y, zf(x, y)) for x, y in ring], [[(x, y, zf(x, y)) for x, y in h] for h in holes]))


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def drive_z(y):
    """Driveway profile: nearly level by the garage, falling to the street."""
    return float(np.interp(y, [-10.2, -9.2, -5.5, 0.55], [Z_ST, -0.38, 0.25, 0.36]))


def rear_lawn_z(x, y=0.0):
    return float(np.interp(x, [0.5, 14.3], [Z_LAWN_W, Z_LAWN_E]))


def wall_y(x):
    """The street wall's outer face: the street runs ~6 deg off the house's front."""
    return -10.1 + (x - 6.1) * 0.1005


def stone_wall(g, a, b, top, base=-0.55, t=0.4):
    a, b = np.array(a, float), np.array(b, float)
    L = float(np.linalg.norm(b - a))
    ex = np.array([(b - a)[0] / L, (b - a)[1] / L, 0.0])
    ey = np.array([-ex[1], ex[0], 0.0])
    o = np.array([a[0], a[1], 0.0])
    g.obox('stone_veneer', o, ex, ey, np.array([0, 0, 1.0]), (0, -t / 2, base), (L, t / 2, top), faces='xXyY')
    g.obox('coping', o, ex, ey, np.array([0, 0, 1.0]), (-0.04, -t / 2 - 0.04, top), (L + 0.04, t / 2 + 0.04, top + 0.06))


WALK = [(9.9, -4.6), (15.0, -4.6), (15.0, -5.0), (14.6, -6.3), (13.4, -7.5), (12.2, -8.2), (11.0, -8.6), (9.0, -8.95),
        (7.8, -8.9), (7.8, -7.4), (8.6, -6.8), (9.3, -6.0), (9.9, -5.0)]


def ground(g):
    # the street (parallel to the wall) and what lies beyond the fences
    g.poly('asphalt', [(-150, -40, Z_ST), (180, -40, Z_ST), (180, wall_y(180) - 1.1, Z_ST), (-150, wall_y(-150) - 1.1, Z_ST)])
    g.poly('concrete', [(-150, wall_y(-150) - 1.1, Z_ST), (180, wall_y(180) - 1.1, Z_ST), (180, wall_y(180) - 0.2, Z_ST + 0.1),
                        (-150, wall_y(-150) - 0.2, Z_ST + 0.1)])
    flat(g, 'ground_far', rect(-260, -260, 290, 300), -0.62)
    flat(g, 'soil', [(FENCE_W, 0.8), (FENCE_E, -1.3), (FENCE_E, FENCE_N), (FENCE_W, FENCE_N)], -0.05)
    # driveway (pavers), in strips along its fall; the bay in front of the right-hand door
    ys = [-11.4, -9.2, -7.4, -5.5, -2.5, 0.55]
    for a, b in zip(ys[:-1], ys[1:]):
        g.poly('paver_drive', [(-1.9, a, drive_z(a)), (6.05, a, drive_z(a)), (6.05, b, drive_z(b)), (-1.9, b, drive_z(b))],
               uv_u=(1.0, 0.0, 0.0), uv_o=(0.0, 0.0, 0.0))
    for a, b in ((-4.2, -2.5), (-2.5, 0.55)):
        g.poly('paver_drive', [(6.05, a, drive_z(a)), (7.6, a, drive_z(a)), (7.6, b, drive_z(b)), (6.05, b, drive_z(b))],
               uv_u=(1.0, 0.0, 0.0), uv_o=(0.0, 0.0, 0.0))
    g.poly('paver_drive', [(6.05, -8.85, -0.15), (7.1, -8.85, -0.15), (7.1, -7.45, -0.15), (6.05, -7.45, -0.15)])   # landing
    for k in range(3):                                 # steps from the walk down to the driveway
        g.box('bluestone', (7.1 + 0.235 * k, -8.85, -0.3), (7.1 + 0.235 * (k + 1), -7.45, 0.44 - 0.148 * (3 - k)), faces='xyYZ')
    flat(g, 'mulch', rect(FENCE_W, -11.4, -1.9, 0.8), lambda x, y: drive_z(y) + 0.04)        # bed along the left fence
    # the front walk, the lawn patch left of it, the main lawn down to the street wall, the planter by the landing
    flat(g, 'bluestone', WALK, 0.44)
    flat(g, 'lawn', [(6.2, -7.25), (7.8, -7.3), (8.6, -6.8), (9.3, -6.0), (9.9, -5.0), (9.9, -4.6), (11.7, -4.6), (11.7, -3.52),
                     (11.15, -3.52), (11.15, -3.28), (7.6, -3.28), (7.6, -4.2), (6.2, -4.2)], Z_LAWN_F)
    flat(g, 'lawn', [(15.0, -5.0), (15.0, -4.6), (13.95, -4.6), (13.95, -3.52), (14.6, -3.52), (14.6, -2.45), (20.1, -2.45),
                     (20.1, -1.85), (24.5, -1.85), (24.5, -1.3), (27.5, -1.3), (27.5, wall_y(27.5) + 0.2),
                     (7.8, wall_y(7.8) + 0.2), (7.8, -8.9), (9.0, -8.95), (11.0, -8.6), (12.2, -8.2), (13.4, -7.5), (14.6, -6.3)],
         Z_LAWN_F)
    flat(g, 'mulch', [(6.3, wall_y(6.3) + 0.2), (7.8, wall_y(7.8) + 0.2), (7.8, -9.05), (6.3, -9.05)], Z_LAWN_F - 0.05)
    stone_wall(g, (6.1, wall_y(6.1)), (27.5, wall_y(27.5)), 0.58)
    stone_wall(g, (6.1, wall_y(6.1)), (6.1, -8.95), 0.58)
    stone_wall(g, (6.1, -8.95), (7.8, -8.95), 0.58, base=-0.3)
    stone_wall(g, (6.1, -7.35), (7.8, -7.35), 0.58, base=-0.3)
    stone_wall(g, (6.1, -7.35), (6.1, -4.5), 0.52, base=-0.3)
    # side yards
    flat(g, 'concrete', rect(FENCE_W, 0.8, 0.5, 12.8), lambda x, y: 0.40 + 0.012 * (y - 0.8))
    flat(g, 'mulch', rect(25.55, -1.26, FENCE_E, 12.66), 0.92)
    # rear patio (bluestone, at floor level) and the fireplace's bed
    flat(g, 'bluestone', [(14.7, 13.95), (20.4, 13.95), (20.4, 12.66), (25.45, 12.66), (25.45, 18.0), (14.7, 18.0)], Z_PATIO)
    g.box('bluestone', (14.7, 17.96, 0.6), (25.45, 18.0, Z_PATIO), faces='Y')
    flat(g, 'mulch', rect(25.45, 12.66, FENCE_E, 18.6), 0.97)
    # main rear lawn, falling toward the laundry end
    flat(g, 'lawn', [(FENCE_W, 12.8), (0.5, 12.8), (0.5, 12.8001), (7.08, 12.8), (7.08, 13.55), (9.97, 13.55), (9.97, 12.8),
                     (10.78, 12.8), (10.78, 16.07), (14.7, 16.07), (14.7, 18.0), (14.3, 18.0), (14.3, CURB_Y),
                     (FENCE_W, CURB_Y)], lambda x, y: rear_lawn_z(x))
    flat(g, 'lawn', [(14.3, 18.0), (25.45, 18.0), (25.45, 18.6), (FENCE_E, 18.6), (FENCE_E, TERR['y0']), (17.75, TERR['y0']),
                     (17.75, CURB_Y), (14.3, CURB_Y)], Z_LAWN_E)
    # the low wall that carries the pool terrace
    g.box('concrete', (-1.7, CURB_Y - 0.12, 0.3), (17.75, CURB_Y + 0.12, Z_POOL + 0.02), faces='xXyYZ')
    return g


def pool_terrace(g):
    info = pool_kit.pool(g, POOL_AT['origin'], (1, 0, 0), (0, 1, 0), length=POOL_AT['length'], width=POOL_AT['width'])
    hole = [tuple(p[:2]) for p in info['footprint']]
    flat(g, 'lawn', [(FENCE_W, CURB_Y), (17.75, CURB_Y), (17.75, 35.7), (FENCE_W, 35.7)], Z_POOL - 0.02, holes=[hole])
    flat(g, 'mulch', rect(FENCE_W, 35.7, 17.75, FENCE_N), Z_POOL)
    return info


def cabana(g):
    """White lap-sided pool house facing the pool, a truncated standing-seam hip roof, its louvred pergola on the
    bluestone terrace (two risers above the pool coping)."""
    t = TERR
    g.box('bluestone', (t['x0'], t['y0'], 0.6), (t['x1'], t['y1'], Z_CAB), faces='xyYZ')
    for k in (1, 2):                                   # steps toward the pool, and down to the lawn on the house side
        g.box('bluestone', (t['x0'] - 0.36 * k, t['y0'] + 0.0, 0.6), (t['x0'] - 0.36 * (k - 1), t['y1'], Z_CAB - 0.15 * k), faces='xyYZ')
    for k in range(1, 4):
        g.box('bluestone', (18.9, t['y0'] - 0.34 * k, 0.5), (20.3, t['y0'] - 0.34 * (k - 1), Z_CAB - 0.15 * k), faces='xXyZ')
    c = CAB
    walls = [((c['x0'], c['y1']), (c['x0'], c['y0']), [(OP.slider, 2.3, 0.0, (), dict(w=2.7, h=2.34, panels=2, lights=3, seed=61))],
              [(1.9, 1.7), (5.4, 1.7)]),
             ((c['x0'], c['y0']), (c['x1'], c['y0']), [(OP.window, 1.4, 1.0, (1.6, 1.3), dict(n=2, lights=2, seed=62))], []),
             ((c['x1'], c['y0']), (c['x1'], c['y1']), [], []),
             ((c['x1'], c['y1']), (c['x0'], c['y1']), [], [])]
    for a, b, ops, lanterns in walls:
        a, b = np.array(a, float), np.array(b, float)
        L = float(np.linalg.norm(b - a))
        right = np.array([(b - a)[0] / L, (b - a)[1] / L, 0.0])
        out = np.array([right[1], -right[0], 0.0])
        f = OP.Facade(g, (a[0], a[1], Z_CAB), right, L, c['plate'] - Z_CAB, mat='siding_lap')
        for builder, x, z, args, kw in ops:
            f.add(builder, x, z, *args, **kw)
        f.finish()
        for x, z in lanterns:
            FX.lantern(g, np.array([a[0], a[1], Z_CAB]) + right * x + np.array([0, 0, z]), right, out)
    bl = {'cabana': hip_roof('cabana', c['x0'] - 0.4, c['y0'] - 0.4, c['x1'] + 0.4, c['y1'] + 0.4, c['plate'] + 0.24, 0.385,
                             'roof_seam', z_cap=5.45, storey=1)}
    roof_planes(g, bl['cabana'])
    roof_details(g, bl)
    FX.pergola(g, (18.0, 34.5, Z_CAB), (0, -1, 0), (1, 0, 0), 7.5, 3.4, h=3.0, angle=0.0, bays=4, heaters=False)
    # terrace furniture (p27): two chairs and the fire bowl on the left, the sofa group on the right
    FU.lounge_chair(g, (19.6, 33.2, Z_CAB), 90)
    FU.lounge_chair(g, (20.3, 31.6, Z_CAB), 90)
    FU.fire_bowl(g, (19.0, 32.2, Z_CAB))
    FU.lounge_sofa(g, (20.3, 28.4, Z_CAB), 90, seats=2)
    FU.lounge_table(g, (19.3, 28.4, Z_CAB), 90)
    FU.woven_chair(g, (22.6, 26.3, Z_CAB), 160)
    FU.woven_chair(g, (24.3, 26.3, Z_CAB), 200)
    FU.drum_table(g, (23.45, 26.2, Z_CAB))


def rear_patio(g):
    FX.pergola(g, (15.05, 17.87, Z_PATIO), (1, 0, 0), (0, -1, 0), 5.55, 3.6, h=3.07)
    FU.dining_set(g, (17.8, 16.0, Z_PATIO), 0)
    FU.teak_lounge_set(g, (23.0, 16.85, Z_PATIO), 0)
    FU.fireplace(g, (26.25, 15.5, 0.97), 90)
    # laundry door: landing and one long step down to the lawn
    g.box('bluestone', (3.0, 12.8, 0.3), (4.4, 13.28, Z_PATIO - 0.02), faces='xXYZ')
    g.box('bluestone', (2.6, 12.8, 0.3), (4.8, 13.66, Z_PATIO - 0.17), faces='xXYZ')
    FU.condenser(g, (6.45, 13.12, rear_lawn_z(6.4) + 0.02), 0)
    FU.condenser(g, (5.4, 13.12, rear_lawn_z(5.4) + 0.02), 0)
    FU.equipment_cabinet(g, (-2.1, 9.0, 0.5), 90)


def fences(g):
    line = [(FENCE_W, 0.8, 0.40), (FENCE_W, CURB_Y - 0.2, 0.60), (FENCE_W, CURB_Y + 0.6, Z_POOL), (FENCE_W, FENCE_N, Z_POOL),
            (17.6, FENCE_N, Z_POOL), (18.4, FENCE_N, Z_CAB), (FENCE_E, FENCE_N, Z_CAB), (FENCE_E, 24.6, Z_CAB),
            (FENCE_E, 23.8, 0.95), (FENCE_E, -1.26, 0.90)]
    FX.fence(g, line, side=-1)
    # front returns with their gates
    FX.fence(g, [(FENCE_W, 0.8, 0.40), (-1.0, 0.8, 0.40)], side=-1, end_posts=(False, True))
    FX.gate(g, (-0.93, 0.8, 0.40), (0.43, 0.8, 0.40), side=-1)
    FX.fence(g, [(26.8, -1.26, 0.90), (FENCE_E, -1.26, 0.90)], side=-1, end_posts=(True, False))
    FX.gate(g, (25.62, -1.26, 0.90), (26.73, -1.26, 0.90), side=-1)


def planting(g, trees):
    PL.oak(trees, (5.3, 17.3, rear_lawn_z(5.3)))
    flat(g, 'mulch', [(5.3 + 1.6 * np.cos(a), 17.3 + 1.6 * np.sin(a)) for a in np.linspace(0, 2 * np.pi, 20, endpoint=False)],
         rear_lawn_z(5.3) + 0.03)
    PL.hedge(g, [(-1.6, 36.25, Z_POOL), (17.2, 36.25, Z_POOL)], h=1.7, w=1.1, kind='laurel', seed=3)
    PL.hedge(g, [(FENCE_W + 0.7, 25.2, Z_POOL), (FENCE_W + 0.7, 35.3, Z_POOL)], h=1.5, w=1.0, kind='laurel', seed=4)
    for i, x in enumerate(np.linspace(11.2, 14.3, 5)):                      # roses along the nook bay
        PL.rose_bush(g, (x, 16.65, rear_lawn_z(x)), h=0.8, r=0.42, seed=10 + i, blooms=12)
    for i, x in enumerate((7.5, 8.5, 9.5)):
        PL.boxwood(g, (x, 14.05, rear_lawn_z(x)), r=0.38, h=0.6, seed=20 + i)
    for i, y in enumerate((13.4, 14.4, 17.2, 18.1)):                        # bed by the fireplace
        PL.rose_bush(g, (26.9, y, 0.97), h=1.0, r=0.5, seed=30 + i)
    for i, y in enumerate(np.linspace(0.2, 11.6, 7)):                       # along the right side yard
        PL.shrub(g, (27.0, y, 0.92), r=0.55, h=1.3, kind='green', loose=0.6, seed=40 + i)
    for i, x in enumerate(np.linspace(18.4, 27.0, 5)):                      # planter along the terrace's house side
        PL.rose_bush(g, (x if x < 18.8 or x > 20.4 else 20.8, 24.45, Z_LAWN_E), h=0.9, r=0.45, seed=50 + i)
    # front: clipped shrubs along the porch and the wing, the row behind the planter wall, the bed at the street
    i = 0
    for x in list(np.arange(7.9, 11.0, 0.95)) + list(np.arange(15.2, 19.6, 0.95)):
        y = -3.75 if x < 11.2 else -2.9
        PL.boxwood(g, (x, y, Z_LAWN_F), r=0.42, h=0.72, seed=60 + i)
        i += 1
    for x in np.arange(20.4, 24.6, 0.95):
        PL.boxwood(g, (x, -2.3, Z_LAWN_F), r=0.42, h=0.75, seed=60 + i)
        i += 1
    for x in np.arange(8.6, 27.2, 1.2):
        PL.boxwood(g, (x, wall_y(x) + 0.85, Z_LAWN_F), r=0.46, h=0.8, seed=60 + i, loose=0.45)
        i += 1
    for x in np.arange(8.5, 27.5, 2.6):
        PL.shrub(g, (x, wall_y(x) - 0.55, Z_ST + 0.08), r=0.42, h=0.6, kind='green', loose=0.7, seed=60 + i)
        i += 1
    for k, (x, y) in enumerate(((9.2, -4.9), (15.9, -4.9), (22.3, -4.6))):
        PL.sapling(trees, (x, y, Z_LAWN_F), h=4.0, seed=70 + k)
    for k, y in enumerate((-9.5, -5.0, -1.2)):
        PL.shrub(g, (-2.35, y, drive_z(y) + 0.04), r=0.5, h=1.1, kind='laurel', loose=0.6, seed=80 + k)


def backdrop(g, trees):
    """Neighbouring houses as plain masses and a few big trees beyond the fences (for context only)."""
    for x0, y0, x1, y1, h in ((32.5, 2.0, 44.0, 19.0, 5.4), (-19.0, 0.0, -7.5, 15.0, 5.4), (2.0, 44.0, 17.0, 54.0, 3.2),
                              (34.0, 30.0, 45.0, 41.0, 3.2), (-21.0, 25.0, -9.0, 38.0, 3.2)):
        g.box('neighbor_wall', (x0, y0, -0.6), (x1, y1, h), faces='xXyY')
        roof_planes(g, hip_roof('nb', x0 - 0.5, y0 - 0.5, x1 + 0.5, y1 + 0.5, h + 0.2, 0.42, 'neighbor_roof'))
    for k, (x, y, h, r) in enumerate(((36.0, 26.0, 21, 3.2), (38.5, 35.0, 24, 3.4), (30.0, 45.0, 19, 3.0), (-12.0, 44.0, 22, 3.2),
                                      (21.0, 47.0, 18, 2.8))):
        PL.conifer(trees, (x, y, -0.5), h=h, r=r, seed=90 + k)
    for k, (x, y, h, r, pal) in enumerate(((-11.0, 21.0, 10, 4.0, 'olive'), (35.5, 22.5, 9, 3.6, 'gold'), (33.5, -6.5, 8, 3.2, 'gold'),
                                           (10.0, 46.0, 10, 4.0, 'gold'), (-9.0, -7.5, 8, 3.4, 'green'), (-4.0, 44.0, 9, 3.6, 'red'))):
        PL.broadleaf(trees, (x, y, -0.5), h=h, crown_r=r, palette=pal, seed=100 + k)


def build():
    LAWNS.clear()
    gnd, site, cab, plants, trees, back = Geo(), Geo(), Geo(), Geo(), Geo(), Geo()
    ground(gnd)
    pool_terrace(gnd)
    cabana(cab)
    rear_patio(site)
    fences(site)
    planting(plants, trees)
    backdrop(back, trees)
    return [Part('ground', gnd, group='site'), Part('site', site, group='site'), Part('cabana', cab, group='site'),
            Part('plants', plants, group='site'), Part('trees', trees, group='site'), Part('backdrop', back, group='site')]
