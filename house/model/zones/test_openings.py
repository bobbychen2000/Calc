"""Test zone of the openings kit (model/openings.py): a two-storey white box 17 x 8 m carrying one of every opening
type at real size on walls facing all four ways.

    python3 -I model/build.py --zones test_openings --out test_openings
    node tools/shot.cjs out/tmp/openings/NAME.png "glb=test_openings.glb&meta=test_openings_meta.json&view=front&still=1" 1400

Front (faces the street, -Y): garage pair, entry, french doors with a sidelight, the three-part bay; upper floor: the
gable-room window, short wide, single, two-sash, three-part with a fixed centre, small square.
Back (+Y): family-room slider, french pair, tall narrow unit, mahogany dutch door, short wide, bedroom slider; upper
floor: the glass corner (wraps onto the west wall), two windows (one with its shade down).
East (+X): three-part window, cabana slider; west (-X): a single garage door, a window, the corner's other bank.
"""
import numpy as np

from model import openings as O
from model.kit import Geo, Part

W, D, H = 17.0, 8.0, 6.3            # the box: x 0..W, y 0..D, z 0..H; upper floor at Z2
Z2 = 3.25

VIEWS = {
    'front': dict(label='Front 12 m', pos=(8.5, -12.0, 2.0), target=(8.5, 0.0, 3.0), fov=46),
    'oblique': dict(label='Oblique 3 m', pos=(5.9, -3.0, 1.6), target=(11.4, 0.0, 1.55), fov=55),
    'entry': dict(label='Entry 4 m', pos=(7.83, -4.0, 1.6), target=(7.83, 0.0, 1.3), fov=38),
    'french': dict(label='French 4 m', pos=(10.78, -4.0, 1.6), target=(10.78, 0.0, 1.2), fov=38),
    'garage': dict(label='Garage 4.5 m', pos=(3.36, -4.5, 1.6), target=(3.36, 0.0, 1.3), fov=50),
    'bay': dict(label='Bay 6 m', pos=(14.9, -6.0, 1.6), target=(14.43, 0.0, 1.75), fov=30),
    'upper': dict(label='Upper close', pos=(5.2, -4.6, 1.6), target=(3.0, 0.0, 4.85), fov=24),
    'rear': dict(label='Rear 12 m', pos=(8.5, 20.0, 2.0), target=(8.5, 8.0, 3.0), fov=46),
    'slider': dict(label='Slider 4 m', pos=(14.15, 12.0, 1.6), target=(14.15, 8.0, 1.3), fov=48),
    'dutch': dict(label='Dutch 4 m', pos=(5.75, 12.0, 1.6), target=(5.75, 8.0, 1.3), fov=38),
    'corner': dict(label='Corner 8 m', pos=(-5.2, 13.6, 1.8), target=(1.1, 6.9, 4.9), fov=36),
    'east': dict(label='East 10 m', pos=(27.0, 4.6, 1.8), target=(17.0, 4.0, 2.6), fov=44),
    'west': dict(label='West 10 m', pos=(-10.0, 3.4, 1.8), target=(0.0, 4.0, 2.6), fov=44),
    'far': dict(label='Front 30 m', pos=(-6.0, -30.0, 1.7), target=(8.5, 0.0, 3.0), fov=30),
}


def build():
    g = Geo()
    # ---- front: faces the street (-Y) ----------------------------------------------------------------------------
    f = O.Facade(g, (0.0, 0.0, 0.0), (1, 0, 0), W, H)
    f.add(O.garage_pair, 0.8, 0.0, 2.44, 2.44, seed=1)
    f.add(O.entry_door, 6.9, 0.0, seed=2)
    f.add(O.french_doors, 9.6, 0.0, 2.35, 2.2, side_r=0.42, seed=3)
    f.add(O.bay_window, 13.0, 0.75, seed=4, floor=0.75)
    f.add(O.window, 2.2, Z2 + 0.85, 1.65, 1.5, n=2, seed=5, floor=0.85)
    f.add(O.window, 5.4, Z2 + 1.65, 0.95, 0.5, n=1, lights=0, seed=6, floor=1.65)
    f.add(O.window, 7.4, Z2 + 0.95, 0.75, 1.3, n=1, seed=7, floor=0.95)
    f.add(O.window, 9.2, Z2 + 1.0, 1.4, 1.25, n=2, seed=8, floor=1.0)
    f.add(O.window, 11.6, Z2 + 0.85, 2.4, 1.5, n=3, fixed=(1,), widths=(1, 1.5, 1), lights=(2, 3, 2), seed=9,
          floor=0.85)
    f.add(O.window, 15.2, Z2 + 1.6, 0.65, 0.62, n=1, lights=0, seed=10, floor=1.6)
    f.finish()
    # ---- back (+Y): right runs toward -X ---------------------------------------------------------------------------
    f = O.Facade(g, (W, D, 0.0), (-1, 0, 0), W, H)
    f.add(O.slider, 1.0, 0.0, 3.7, 2.44, lights=5, seed=11)
    f.add(O.french_doors, 5.8, 0.0, 2.10, 2.42, seed=12)
    f.add(O.window, 8.9, 0.1, 0.9, 2.3, n=1, seed=13, floor=0.1, casing=0.07)
    f.add(O.dutch_door_wood, 10.8, 0.0, seed=14)
    f.add(O.window, 12.4, 1.75, 1.1, 0.48, n=1, lights=0, seed=15, floor=1.75, ears=0.03)
    f.add(O.window, 1.6, Z2 + 0.85, 1.65, 1.5, n=2, seed=17, floor=0.85)
    f.add(O.window, 5.0, Z2 + 0.85, 1.65, 1.5, n=2, seed=18, floor=0.85, shade=0.55)
    f.add(O.window, 8.4, Z2 + 1.65, 0.95, 0.5, n=1, lights=0, seed=19, floor=1.65)
    cz = Z2 + 0.75
    wa, wb, ch = 4.0, 3.0, 1.9
    O.corner_glazing(g, (0.0, D, cz), (1, 0, 0), (0, -1, 0), wa, wb, ch, na=4, nb=3, seed=20, floor=0.75)
    f.holes.append((W - wa, cz, W, cz + ch))
    f.finish()
    # ---- east (+X): right runs toward +Y -------------------------------------------------------------------------
    f = O.Facade(g, (W, 0.0, 0.0), (0, 1, 0), D, H)
    f.add(O.window, 0.9, 0.9, 2.4, 1.5, n=3, fixed=(1,), seed=21)
    f.add(O.slider, 4.3, 0.0, 2.9, 2.44, lights=3, seed=22)
    f.add(O.window, 1.2, Z2 + 0.85, 1.65, 1.5, n=2, seed=23, floor=0.85, room=O.ROOM_DARK)
    f.add(O.window, 4.6, Z2 + 0.85, 2.4, 1.5, n=3, seed=24, floor=0.85, shade=1.0)
    f.finish()
    # ---- west (-X): right runs toward -Y; the glass corner's second bank at its left end -------------------------
    f = O.Facade(g, (0.0, D, 0.0), (0, -1, 0), D, H)
    f.add(O.garage_door, 3.4, 0.0, 2.44, 2.44, seed=25)
    f.add(O.window, 0.9, 0.9, 1.65, 1.5, n=2, seed=26)
    f.add(O.window, 5.0, Z2 + 0.95, 0.75, 1.3, n=1, seed=27, floor=0.95)
    f.holes.append((0.0, cz, wb, cz + ch))
    f.finish()
    house = Part('test_openings', g)

    s = Geo()
    s.box('roof_seam', (-0.45, -0.45, H), (W + 0.45, D + 0.45, H + 0.22), mats={'z': 'soffit_white'})
    s.box('trim_white', (-0.03, -0.03, Z2 - 0.14), (W + 0.03, D + 0.03, Z2 + 0.02), faces='xXyY')     # belt board
    s.poly('bluestone', [(-9, -9, 0.0), (W + 9, -9, 0.0), (W + 9, D + 9, 0.0), (-9, D + 9, 0.0)])
    s.poly('lawn', [(-60, -60, -0.02), (W + 60, -60, -0.02), (W + 60, D + 60, -0.02), (-60, D + 60, -0.02)])
    shell = Part('test_shell', s)

    for name, n in (('window 2 sashes', O.count(O.window, 1.65, 1.5, n=2)),
                    ('window 3 sashes', O.count(O.window, 2.4, 1.5, n=3)),
                    ('short wide', O.count(O.window, 0.95, 0.5, n=1, lights=0)),
                    ('bay', O.count(O.bay_window)), ('entry', O.count(O.entry_door)),
                    ('french + sidelight', O.count(O.french_doors, 2.35, 2.2, side_r=0.42)),
                    ('slider', O.count(O.slider)), ('dutch wood', O.count(O.dutch_door_wood)),
                    ('garage door', O.count(O.garage_door)), ('garage pair', O.count(O.garage_pair))):
        print('  %-20s %5d triangles' % (name, n))
    return [house, shell]
