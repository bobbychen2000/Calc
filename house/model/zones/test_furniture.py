"""Test zone of the OUTDOOR FURNITURE / YARD OBJECTS family (model/furniture.py, web/viewer/looks/furniture.js).

    python3 -I model/build.py --zones test_furniture --out test_furniture
    node tools/shot.cjs out/tmp/furniture/p25.png "glb=test_furniture.glb&meta=test_furniture_meta.json&view=p25&still=1" 1400

Every group stands where the listing photos show it, in its real position relative to the others (top-down photo
p30 at ~48 px / m); the origin of this scene is the middle of the dining table.  World metres, X right seen from the
street, Y into the lot, Z up: the house's rear wall is the white proxy wall at y = -2.3, the pool cabana the white
block at the top right, its terrace 0.45 m above the lawn.

  rear patio (z = 0)       dining set at (0, 0) between the pergola's posts (an open stand-in frame), in the house's shadow; the teak lounge set
                           beside it (sofa at (5.7, 0.8), armchairs at x = 4.06, coffee table) and the fireplace at
                           (9.3, -0.8) looking back at them
  cabana terrace (z 0.45)  its south-west corner at (1.06, 12.5): fire bowl with two lounge chairs, the loveseat with
                           its coffee table on the rug, door mat; round the corner the two hoop chairs and the drum table
  yard equipment           along the rear wall, x < -4: heat pump, a single-fan unit, utility boxes, the equipment
                           cabinet, planters and pots, a door mat
The walls, slabs, lawn and pergola frame are plain stand-ins (part 'context'): only the furniture is this family's.
"""
import numpy as np

from model import furniture as F
from model.kit import Geo, Part

TC = np.array([1.06, 12.5, 0.45])            # the cabana terrace: pergola's south-west corner, terrace level

BUDGET = {'dining_chair': 1200, 'teak_armchair': 1200, 'lounge_chair': 1200, 'woven_chair': 1200,
          'teak_sofa': 2500, 'lounge_sofa': 2500, 'dining_table': 800, 'teak_coffee_table': 800,
          'lounge_table': 800, 'fireplace': 3000, 'fire_bowl': 500, 'condenser': 600}


def _v(pos, target, fov=40, label=''):
    return dict(label=label, pos=tuple(float(x) for x in pos), target=tuple(float(x) for x in target), fov=fov)


def _close(p, d, h=1.35, th=0.42, dist=2.5, fov=40, label=''):
    """A close view: the camera `dist` m from the ground point p along the plan direction d, h above it."""
    p = np.array([p[0], p[1], p[2] if len(p) > 2 else 0.0])
    d = np.array([d[0], d[1], 0.0])
    d = d / np.linalg.norm(d)
    r = np.sqrt(max(dist ** 2 - (h - th) ** 2, 0.25))
    return _v(p + d * r + [0, 0, h], p + [0, 0, th], fov, label)


VIEWS = {
    # the listing photos' viewpoints
    'p25': _v((0.32, 8.9, 1.75), (0.32, -2.3, 1.40), 35.4, 'p25 patio'),
    'p25_left': _v((0.32, 8.9, 1.75), (4.6, -2.3, 0.75), 16, 'p25 teak'),
    'p25_table': _v((0.32, 8.9, 1.75), (0.0, 0.0, 0.62), 13.5, 'p25 dining'),
    'p30': _v((3.4, -0.75, 27.0), (3.4, -0.3, 0.0), 26, 'p30 top'),
    'p30_cabana': _v((4.6, 15.4, 27.5), (4.6, 15.9, 0.45), 26, 'p30 cabana'),
    'seg123': _v((-0.55, 16.3, 1.80), (5.2, 3.0, 0.75), 46, 'seg123 terrace'),
    'seg123_fp': _v((-0.55, 16.3, 1.80), (9.2, -0.8, 1.9), 14, 'seg123 fireplace'),
    'p27': _v((-13.5, 16.9, 1.55), (4.0, 16.9, 1.05), 17, 'p27 cabana'),
    'p26': _v((-21.0, 21.0, 1.7), (5.0, -0.6, 1.3), 11, 'p26 patio'),
    'seg141': _v((5.6, -6.0, 13.0), (6.4, 12.0, 0.6), 22, 'seg141 hoop'),
    # 2.5 m close-ups
    'c_dining_chair': _close((0.5, 0.72), (0.5, 1.0), label='chair'),
    'c_dining_table': _close((0.0, 0.0), (0.75, 1.0), h=1.5, th=0.6, dist=3.0, label='table'),
    'c_teak_sofa': _close((5.71, 0.83), (-0.35, -1.0), h=1.45, dist=3.3, label='teak sofa'),
    'c_teak_back': _close((5.71, 0.83), (-0.6, 1.0), h=1.3, dist=3.2, label='teak back'),
    'c_teak_chair': _close((4.06, -0.15), (-0.75, 1.0), label='teak chair'),
    'c_teak_table': _close((6.29, -0.85), (0.5, -1.0), h=1.3, th=0.2, label='teak table'),
    'c_fireplace': _close((9.3, -0.8), (-1.0, 0.35), h=1.5, th=1.0, dist=2.6, fov=50, label='firebox'),
    'fireplace': _close((9.3, -0.8), (-1.0, 0.55), h=1.6, th=1.9, dist=7.0, fov=40, label='fireplace'),
    'c_fire_bowl': _close(TC + [1.46, 6.38, 0], (-1.0, -0.5), label='fire bowl'),
    'c_lounge_sofa': _close(TC + [2.53, 0.88, 0], (-1.0, 0.45), h=1.4, label='loveseat'),
    'c_lounge_chair': _close(TC + [2.26, 5.20, 0], (-1.0, -0.2), label='lounge chair'),
    'c_lounge_table': _close(TC + [1.30, 0.76, 0], (-1.0, -0.7), h=1.3, th=0.3, label='lounge table'),
    'c_woven': _close(TC + [5.7, -0.95, 0], (0.25, -1.0), h=1.3, dist=2.9, label='hoop chairs'),
    'c_woven_back': _close(TC + [4.94, -0.93, 0], (-0.8, 1.0), h=1.5, dist=2.4, label='hoop back'),
    'c_condenser': _close((-6.0, -2.0), (0.45, 1.0), h=1.4, th=0.7, dist=3.0, label='heat pump'),
    'c_utility': _close((-4.4, -2.3), (0.3, 1.0), h=1.3, th=0.9, dist=2.2, label='utility'),
    'c_pots': _close((-9.6, -1.2), (0.6, 1.0), h=1.3, th=0.4, dist=3.0, label='pots'),
}


def _context():
    g = Geo()
    g.box('lawn', (-40, -30, -0.3), (40, 45, -0.05), faces='Z')
    g.box('bluestone', (-11.5, -2.3, -0.2), (8.8, 2.05, 0.0), faces='xXYZ')            # rear patio
    g.box('siding_lap', (-12.0, -2.6, -0.2), (3.7, -2.3, 5.6))                         # the house's rear wall (tall part)
    g.box('siding_lap', (3.7, -2.6, -0.2), (10.5, -2.3, 2.7))                          # ... and its low wing
    g.box('glass', (-1.6, -2.31, 0.05), (2.3, -2.295, 2.44), faces='Y')                # the slider behind the table
    # the pergola over the dining table: posts and an open frame (stand-in; the louvres are left out)
    for x in (-3.1, 3.55):
        for y in (-2.2, 1.8):
            g.box('pergola_metal', (x - 0.09, y - 0.09, 0.0), (x + 0.09, y + 0.09, 2.75))
        g.box('pergola_metal', (x - 0.09, -2.29, 2.75), (x + 0.09, 1.89, 3.0))
    for y in (-2.2, 1.8):
        g.box('pergola_metal', (-3.19, y - 0.09, 2.75), (3.64, y + 0.09, 3.0))
    # cabana: terrace slab, building
    x0, y0, zt = TC
    g.box('bluestone', (x0 - 1.3, y0 - 2.1, -0.2), (x0 + 9.6, y0 + 8.9, zt), faces='xXyYZ')
    g.box('siding_lap', (x0 + 3.45, y0 - 0.25, zt), (x0 + 9.3, y0 + 8.7, zt + 2.9))
    g.box('roof_seam', (x0 + 3.15, y0 - 0.55, zt + 2.9), (x0 + 9.6, y0 + 9.0, zt + 3.05))
    g.box('glass', (x0 + 3.44, y0 + 3.2, zt + 0.05), (x0 + 3.455, y0 + 5.6, zt + 2.44), faces='x')
    return Part('context', g, group='house')


def build():
    parts = [_context()]
    count = {}

    def add(kind, fn, *a, **k):
        g = Geo()
        fn(g, *a, **k)
        count[kind] = count.get(kind, 0) + 1
        parts.append(Part('%s_%d' % (kind, count[kind]), g, group='furniture'))
        return g

    # ---- rear patio: dining set (the pieces one by one, as dining_set() lays them out) ------------------------------
    add('dining_table', F.dining_table, (0, 0), 0.0, seed=3)
    rng = np.random.default_rng(3)
    for i, (x, y, h) in enumerate([(-0.50, -0.70, 0.0), (0.50, -0.72, 0.0), (-0.52, 0.71, 180.0), (0.50, 0.70, 180.0),
                                   (-1.36, 0.0, -90.0), (1.36, 0.02, 90.0)]):
        add('dining_chair', F.dining_chair, (x + rng.uniform(-0.03, 0.03), y + rng.uniform(-0.03, 0.03)),
            h + 180.0 + rng.uniform(-5, 5), seed=30 + i)
    add('table_jars', F.table_jars, (0.08, 0.05, 0.75), 0.0)
    # ---- teak lounge set + fireplace -----------------------------------------------------------------------------
    add('teak_sofa', F.teak_sofa, (5.71, 0.83), 0.0, seed=5)
    add('teak_armchair', F.teak_armchair, (4.06, -0.15), 90.0, seed=5)
    add('teak_armchair', F.teak_armchair, (4.06, -1.31), 90.0, pillow=False, seed=6)
    add('teak_coffee_table', F.teak_coffee_table, (6.29, -0.85), 0.0, seed=5)
    add('fireplace', F.fireplace, (9.3, -0.8), -90.0)
    # ---- cabana terrace -----------------------------------------------------------------------------------------
    add('fire_bowl', F.fire_bowl, TC + [1.46, 6.38, 0])
    add('lounge_chair', F.lounge_chair, TC + [2.61, 7.67, 0], -42.0, seed=1)
    add('lounge_chair', F.lounge_chair, TC + [2.26, 5.20, 0], -112.0, seed=2)
    add('outdoor_rug', F.outdoor_rug, TC + [1.45, 0.80, 0], 90.0)
    add('lounge_sofa', F.lounge_sofa, TC + [2.53, 0.88, 0], -90.0, seed=1)
    add('lounge_table', F.lounge_table, TC + [1.30, 0.76, 0], 90.0)
    add('door_mat', F.door_mat, TC + [3.12, 4.4, 0], 90.0)
    add('woven_chair', F.woven_chair, TC + [4.94, -0.93, 0], 12.0, seed=1)
    add('woven_chair', F.woven_chair, TC + [6.48, -0.93, 0], -10.0, seed=2)
    add('drum_table', F.drum_table, TC + [5.71, -0.97, 0])
    # ---- yard equipment along the rear wall ----------------------------------------------------------------------
    add('condenser', F.condenser, (-6.0, -2.3 + 0.30), 180.0)
    add('condenser1', F.condenser, (-7.25, -2.3 + 0.30), 180.0, fans=1, width=0.85)
    add('equipment_cabinet', F.equipment_cabinet, (-10.4, -1.80), 180.0)
    g = add('utility_box', F.utility_box, (-4.55, -2.3, 1.25), (-1, 0, 0), (0, 1, 0))
    F.utility_box(g, (-4.25, -2.3, 1.25), (-1, 0, 0), (0, 1, 0), conduit=1.25)
    add('door_mat', F.door_mat, (-2.55, -1.93), 0.0)
    add('planter', F.planter, (-9.0, -1.35))
    add('planter', F.planter, (-9.75, -0.75), 0.42, 0.38)
    add('garden_pot', F.garden_pot, (-9.9, -1.6))
    add('garden_pot', F.garden_pot, (-8.5, -0.55), 0.26, 0.22)
    add('planter', F.planter, (8.3, 1.55), 0.62, 0.55)

    worst = {}
    for p in parts[1:]:
        k = p.name.rsplit('_', 1)[0]
        worst[k] = max(worst.get(k, 0), p.ntri)
    print('furniture triangles per piece:')
    for k, n in worst.items():
        b = BUDGET.get(k)
        print('  %-20s %5d%s' % (k, n, '' if b is None else '  / %d%s' % (b, '' if n <= b else '   OVER')))
    return parts
