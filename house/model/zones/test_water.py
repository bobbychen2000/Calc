"""Test zone of the POOL + WATER family (model/pool.py, web/viewer/looks/water.js).

    python3 -I model/build.py --zones test_water --out test_water
    node tools/shot.cjs out/tmp/water/p27.png "glb=test_water.glb&meta=test_water_meta.json&view=p27&still=1" 1400

The pool with its surveyed size (16.57 x 5.5 m) in a lawn.  The layout is the real one turned by 180 degrees so that
the sun of build.py (az 205, el 40: it stands toward -Y, -X) comes from the BACK of the lot as in the listing photos:
    +X  the cover / deep end            -X  the spa end, bluestone terrace, cabana wall + pergola stand-in
    +Y  the house side (a white block)   -Y  the back fence with a hedge
A tree stand-in on the sunny side lays its branch shadows across the water; a few coloured boxes and a white
"house" give the water things to reflect.  Z = 0 is the top of the coping (= the lawn).
"""
import numpy as np

from model import pool as POOL
from model.kit import Geo, Part

L, W = 16.57, 5.5
ORIGIN = (L / 2, W / 2, 0.0)                 # local (0, 0): the cover-end / house-side water corner
RIGHT, BACK = (-1.0, 0.0, 0.0), (0.0, -1.0, 0.0)

VIEWS = {
    # photos/p27: low, from the cover end along the pool to the cabana
    'p27': dict(label='p27 along', pos=(9.85, -0.15, 1.13), target=(-10.0, -0.65, 2.1), fov=36.5),
    # photos/p26: standing at the back coping near the deep end, across the corner to the house
    'p26': dict(label='p26 across', pos=(4.6, -3.45, 1.5), target=(-4.5, 7.0, 1.2), fov=48),
    # frames/seg141_009: low and grazing from the back corner toward the cabana and the house
    'graze': dict(label='grazing', pos=(9.9, -4.4, 0.95), target=(-5.0, 2.0, 0.9), fov=47),
    # photos/p30: straight down
    'top': dict(label='p30 top', pos=(0.0, -1.2, 27.0), target=(0.0, 0.0, 0.0), fov=40),
    # frames/seg123_039: from the cabana terrace down onto the spa corner
    'spa': dict(label='spa close', pos=(-10.6, -1.3, 1.95), target=(-6.4, 1.9, -0.35), fov=45),
    # the entry steps from the house-side coping
    'steps': dict(label='steps', pos=(-3.2, 4.3, 1.75), target=(-5.3, 1.9, -0.5), fov=45),
    # the deep-end bench, skimmer and coping at 1.5 m
    'coping': dict(label='coping close', pos=(4.2, 3.9, 1.3), target=(5.4, 2.6, -0.2), fov=45),
    'three': dict(label='3/4', pos=(16.0, -15.0, 9.5), target=(-1.0, 0.5, 0.0), fov=40),
}


def _tree(g, x, y):
    """A bare-branched tree stand-in: trunk + a few thick limbs (boxes swept between points)."""
    def limb(a, b, r):
        g.prism('bark', [(-r, -r), (r, -r), (r, r), (-r, r)], a, b)
    top = (x + 0.4, y + 0.3, 4.2)
    limb((x, y, 0.0), top, 0.32)
    ends = [(x + 4.5, y + 3.0, 7.5), (x - 3.5, y + 2.0, 8.2), (x + 1.0, y - 3.5, 8.0), (x + 6.5, y - 0.5, 6.0),
            (x - 1.5, y + 4.5, 6.6)]
    for e in ends:
        mid = tuple(np.add(top, e) / 2 + np.array([0.3, -0.2, 0.9]))
        limb(top, mid, 0.15)
        limb(mid, e, 0.09)
        for k, d in enumerate(((1.6, 0.9, 0.8), (-1.0, 1.5, 1.0), (0.6, -1.4, 0.6))):
            limb(e, tuple(np.add(e, d)), 0.05)
            limb(mid, tuple(np.add(mid, np.multiply(d, 1.3))), 0.07)


def build():
    g = Geo()
    info = POOL.pool(g, ORIGIN, RIGHT, BACK, L, W)
    parts = [Part('pool', g, group='site', extras=dict(water_z=info['water_z']))]

    s = Geo()
    fp = [(x, y, 0.0) for x, y in info['footprint']]
    x_t = -L / 2 - 0.45                                    # outer edge of the spa-end coping: the terrace starts here
    # lawn with the pool's footprint cut out (the terrace covers the strip beyond the spa end)
    s.poly('lawn', [(x_t - 0.6, -9.0, 0.0), (22.0, -9.0, 0.0), (22.0, 22.0, 0.0), (x_t - 0.6, 22.0, 0.0)],
           holes=[fp[::-1]], uv_u=(1, 0, 0), uv_o=(0, 0, 0))
    s.box('lawn', (-22.0, -9.0, -0.3), (x_t - 0.6, 22.0, 0.0), faces='Z')
    # bluestone terrace with three risers toward the pool, cabana wall and a dark pergola
    for k in range(3):
        x0 = x_t - 0.25 - 0.38 * k
        s.box('bluestone', (-17.0, -5.2, 0.15 * k), (x0, 5.2, 0.15 * (k + 1)), faces='XyYZ')
    s.box('bluestone', (-17.0, -5.2, 0.0), (x_t, 5.2, 0.02), faces='Z')
    zt = 0.45
    s.box('siding_lap', (-17.0, -3.4, zt), (-13.3, 3.4, zt + 2.85))
    s.box('frame_black', (-13.3, -1.25, zt), (-13.24, 1.25, zt + 2.44))          # the slider
    s.box('roof_seam', (-17.3, -3.7, zt + 2.85), (-13.0, 3.7, zt + 3.05))
    for y in (-3.55, 3.55):
        s.box('pergola_metal', (-9.75, y - 0.09, zt), (-9.57, y + 0.09, zt + 2.75))
    s.box('pergola_metal', (-13.3, -3.64, zt + 2.75), (-9.57, 3.64, zt + 2.99))
    s.box('furniture_dark', (-12.9, 1.6, zt), (-11.9, 3.1, zt + 0.7))            # a sofa block
    s.box('cushion', (-12.8, 1.7, zt + 0.7), (-12.3, 3.0, zt + 0.95))
    # the back fence with a hedge, the fence behind the cabana
    s.box('fence_wood', (-18.0, -7.6, 0.0), (20.0, -7.5, 2.3))
    s.box('fence_wood', (-18.0, -7.5, 0.0), (-17.9, 20.0, 2.3))
    for k in range(7):
        s.box('foliage_dark', (-7.0 + 2.6 * k, -7.3, 0.0), (-4.9 + 2.6 * k, -6.3, 1.5 + 0.25 * (k % 3)))
    # the "house": a white block with dark windows, a red tree and a gold tree behind the fences
    s.box('siding_lap', (-7.0, 10.5, 0.0), (11.0, 19.0, 6.2))
    s.box('roof_seam', (-7.4, 10.1, 6.2), (11.4, 19.4, 6.5))
    for x in (-5.0, -1.0, 3.0, 7.0):
        s.box('frame_black', (x, 10.44, 0.9), (x + 2.2, 10.5, 2.9))
        s.box('frame_black', (x + 0.3, 10.44, 3.9), (x + 1.9, 10.5, 5.4))
    s.box('foliage_red', (-23.0, 4.0, 2.0), (-19.0, 9.0, 9.0))
    s.box('foliage_gold', (13.0, 14.0, 1.5), (17.0, 18.0, 8.0))
    s.box('foliage_dark', (-21.0, -13.0, 0.0), (-13.0, -9.0, 12.0))               # tall conifers behind the cabana
    # things to reflect close to the water
    s.box('door_wood', (2.0, 3.6, 0.0), (2.5, 4.1, 1.0))
    s.box('trim_white', (-2.0, -4.2, 0.0), (-1.6, -3.8, 1.2))
    s.box('foliage_red', (6.0, 3.5, 0.0), (6.6, 4.1, 0.6))
    parts.append(Part('surround', s, group='site'))

    t = Geo()
    _tree(t, 3.0, -6.4)
    parts.append(Part('tree', t, group='site'))
    print('pool: shell %d triangles, water %d' % (info['triangles']['shell'], info['triangles']['water']))
    return parts
