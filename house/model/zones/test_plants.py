"""Test zone of the vegetation kit (model/plants.py):  python3 -I model/build.py --zones test_plants --out test_plants

The back yard turned by 180 degrees about the oak, so that the build's sun (az 205) lights it as in the listing
photos: the oak at the origin, a white two-storey wall behind it (the house's rear in p26, it catches the limb
shadows), the "pool side" toward -Y.  South-west: a front-planter group (stone wall, three staked saplings, boxwood,
roses).  West: a cedar fence with the laurel hedge of p27.  East: one of each backdrop tree against the sky.
"""
from model import plants
from model.kit import Geo, Part

OAK = (0.0, 0.0, 0.0)


def build():
    parts = []
    g = Geo()
    g.box('lawn', (-60, -60, -0.3), (60, 60, 0.0), faces='Z')
    parts.append(Part('ground', g, group='site'))

    # props for scale and shadows (not part of the kit): a 6.5 m wall with an 8 ft door, the planter wall, a fence
    g = Geo()
    g.box('siding_lap', (-9.0, 4.4, 0.0), (7.0, 4.7, 6.5))
    g.box('door_wood', (2.2, 4.37, 0.0), (3.15, 4.4, 2.44), faces='xXyZ')
    parts.append(Part('wall', g, group='house'))
    g = Geo()
    g.box('stone_veneer', (-31.0, -21.0, 0.0), (-13.0, -20.6, 0.9))
    g.box('mulch', (-31.0, -20.6, 0.0), (-13.0, -18.2, 0.86), faces='XxZ')
    g.box('mulch', (-31.0, -22.3, 0.0), (-13.0, -21.0, 0.03), faces='Z')
    g.box('siding_lap', (-31.0, -16.0, 0.0), (-13.0, -15.7, 3.2))
    g.box('fence_wood', (-34.2, -9.0, 0.0), (-34.05, 9.0, 2.1))
    g.box('mulch', (-34.05, -9.0, 0.0), (-32.3, 9.0, 0.04), faces='Z')
    ring = [(1.9 * __import__('math').cos(a * 0.2618), 1.9 * __import__('math').sin(a * 0.2618)) for a in range(24)]
    g.extrude('mulch', ring, 0.0, 0.03, cap_bottom=False)
    parts.append(Part('props', g, group='site'))

    # the oak: the limb list of the real tree, turned by 180 degrees with the yard
    g = Geo()
    limbs = [(a + 180.0,) + tuple(rest) for a, *rest in plants.OAK_LIMBS]
    n = plants.oak(g, OAK, lean_az=300.0 + 180.0, limbs=limbs)
    parts.append(Part('oak', g, group='plants', extras=dict(triangles=n)))

    # the front planter: saplings in the strip before the wall, boxwood on it, roses along the "porch"
    for i, x in enumerate((-28.0, -22.0, -16.0)):
        g = Geo()
        n = plants.sapling(g, (x, -21.6, 0.0), h=(4.2, 3.8, 4.4)[i], seed=11 + i, lean_az=40 * i, stake=True)
        parts.append(Part('sapling_%d' % i, g, group='plants', extras=dict(triangles=n)))
    g = Geo()
    for i in range(12):
        plants.boxwood(g, (-30.2 + i * 1.5, -19.9 + 0.12 * ((i * 7) % 3 - 1), 0.86), r=0.40 + 0.04 * ((i * 5) % 3),
                       h=0.66 + 0.06 * ((i * 3) % 4), seed=40 + i)
    for i in range(5):
        plants.boxwood(g, (-29.5 + i * 3.8, -21.75, 0.03), r=0.34, h=0.5, seed=70 + i, loose=0.6)
    parts.append(Part('boxwood', g, group='plants'))
    g = Geo()
    for i in range(5):
        plants.rose_bush(g, (-29.0 + i * 3.4, -17.0 + 0.2 * (i % 2), 0.0), h=1.0 + 0.12 * (i % 3), r=0.5,
                         seed=90 + i)
    parts.append(Part('roses', g, group='plants'))

    # the laurel hedge along the fence (p27)
    g = Geo()
    n = plants.hedge(g, [(-33.2, -8.5), (-33.2, 8.5)], h=1.75, w=1.2, seed=5)
    parts.append(Part('hedge', g, group='plants', extras=dict(triangles=n)))
    g = Geo()
    plants.hedge(g, [(-31.4, -9.0), (-28.0, -9.0), (-26.0, -7.5)], h=0.9, w=0.7, seed=6, loose=0.0, kind='boxwood')
    parts.append(Part('hedge_clipped', g, group='plants'))

    # backdrop trees along the east side
    row = [
        ('conifer_a', lambda g: plants.conifer(g, (30.0, 30.0, 0.0), h=22.0, r=3.4, seed=3, tops=2)),
        ('conifer_b', lambda g: plants.conifer(g, (33.0, 23.0, 0.0), h=18.0, r=2.9, seed=4)),
        ('tree_green', lambda g: plants.broadleaf(g, (29.0, 13.0, 0.0), h=10.0, crown_r=4.0, palette='green',
                                                  shape='spreading', seed=21)),
        ('tree_gold', lambda g: plants.broadleaf(g, (28.0, 4.0, 0.0), h=7.0, crown_r=2.2, palette='gold',
                                                 shape='upright', seed=22, trunk_h=1.2, bark='bark_young')),
        ('tree_red', lambda g: plants.broadleaf(g, (30.0, -5.0, 0.0), h=8.5, crown_r=3.6, palette='red',
                                                shape='round', seed=23, density=1.2)),
        ('tree_olive', lambda g: plants.broadleaf(g, (29.0, -15.0, 0.0), h=9.0, crown_r=4.2, palette='olive',
                                                  shape='oval', seed=24)),
    ]
    for name, fn in row:
        g = Geo()
        n = fn(g)
        parts.append(Part(name, g, group='plants', extras=dict(triangles=n)))
    return parts


VIEWS = {
    'oak_p26': dict(label='Oak (as p26)', pos=(2.3, -17.3, 1.6), target=(-2.0, 0.0, 6.6), fov=56),
    'oak_25m': dict(label='Oak 25 m', pos=(7.0, -24.0, 1.7), target=(0.0, 0.0, 7.2), fov=44),
    'oak_top': dict(label='Oak from above', pos=(0.5, -3.6, 47.0), target=(0.5, -3.0, 0.0), fov=36),
    'oak_under': dict(label='Under the oak', pos=(1.6, -4.2, 1.6), target=(0.2, -7.5, 9.5), fov=62),
    'planter': dict(label='Planter 8 m', pos=(-22.0, -29.5, 1.6), target=(-22.0, -20.5, 1.7), fov=44),
    'backdrop': dict(label='Backdrop 40 m', pos=(-10.0, 12.0, 1.7), target=(30.0, 8.0, 8.5), fov=44),
    'hedge': dict(label='Hedge', pos=(-25.0, -6.5, 1.5), target=(-33.2, 1.0, 1.0), fov=44),
    'close_bark': dict(label='Bark 2 m', pos=(1.5, -1.9, 1.5), target=(0.0, 0.0, 1.45), fov=40),
    'close_leaves': dict(label='Leaves 2 m', pos=(-31.3, -1.2, 1.4), target=(-33.0, 0.2, 1.25), fov=40),
    'close_rose': dict(label='Rose 1.5 m', pos=(-25.6, -18.6, 1.3), target=(-25.6, -17.0, 0.7), fov=40),
}
