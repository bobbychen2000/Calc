"""Test zone of the SURFACE MATERIALS family (web/viewer/looks/surfaces.js): swatches of every wall, roof, paving
and ground finish at their real scale, lit like the house.

    python3 -I model/build.py --zones test_surfaces --out test_surfaces
    node tools/shot.cjs out/tmp/surfaces/all.png "glb=test_surfaces.glb&meta=test_surfaces_meta.json&view=all&still=1" 1400

World metres, X right, Y away from the viewer, Z up; the sun of build.py (az 205, el 40) stands in front-left, so
the faces toward -Y are sunlit and the faces toward +X are in shade.

Layout (plan):
  y  0..12   ground squares, 6 x 6 m: bluestone, paver_drive, concrete / asphalt, a pool corner (coping, pool_tile,
             pool_plaster), paving_pale, mulch / soil; the lawn is the 60 x 60 m base under everything
  y 14..15   the wall row, 3 x 3 m panels toward -Y with one outside and one inside corner between them:
             siding_lap + door_navy | siding_lap (recessed) + door_wood | siding_bb with battens | chimney_white +
             door_garage under a metal_awning; a porch slab (soffit_white, trim_white, gutter_dark) over the first two;
             a stone_veneer plinth with a bluestone cap in front of the first panel
  x 26..40   roofs: a 4 m gable of roof_shingle, one of roof_seam (with seam ribs), a roof_flat deck with a
             chimney (chimney_white + chimney_cap) and a pergola_metal frame
  y 24       a 12 m fence_wood run
"""
import math

import numpy as np

from model import materials
from model.kit import Geo, Part

# names this family adds to the brief's list
materials.register('pool_plaster', color=(0.72, 0.80, 0.82), roughness=0.7)
materials.register('paving_pale', color=(0.60, 0.58, 0.52), roughness=0.8)

LAP = 0.122            # siding exposure (m): 20 courses per 2.44 m door
BATTEN = 0.406         # board-and-batten spacing
PAN = 0.406            # standing-seam pan width
PITCH = math.radians(30.0)


def wall(g, mat, a, b, z0, z1, openings=()):
    """Vertical wall from plan point a to b (the outside is on the right of a -> b ... i.e. the normal is
    (dy, -dx)); openings = [(s0, s1, z0, z1)] along the wall (m from a).  UV: u from a, v = height above z = 0."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    L = float(np.linalg.norm(b - a))
    d = (b - a) / L
    P = lambda s, z: (a[0] + d[0] * s, a[1] + d[1] * s, z)
    o = (a[0], a[1], 0.0)
    cuts = sorted(openings)
    s = 0.0
    for s0, s1, oz0, oz1 in cuts:
        if s0 > s:
            g.quad(mat, P(s, z0), P(s0, z0), P(s0, z1), P(s, z1), uv_o=o)
        if oz0 > z0:
            g.quad(mat, P(s0, z0), P(s1, z0), P(s1, oz0), P(s0, oz0), uv_o=o)
        if oz1 < z1:
            g.quad(mat, P(s0, oz1), P(s1, oz1), P(s1, z1), P(s0, z1), uv_o=o)
        s = s1
    if s < L:
        g.quad(mat, P(s, z0), P(L, z0), P(L, z1), P(s, z1), uv_o=o)


def door(g, mat, x0, x1, y, z0, z1, depth=0.09, frame='trim_white', planks=False):
    """A door leaf set back `depth` in a wall toward -Y at y, with a 0.09 m painted casing and jambs."""
    g.quad(mat, (x0, y + depth, z0), (x1, y + depth, z0), (x1, y + depth, z1), (x0, y + depth, z1),
           uv_o=(x0, y, z0))
    c = 0.09
    for lo, hi in (((x0 - c, y - 0.02, z0), (x0, y + depth, z1 + c)), ((x1, y - 0.02, z0), (x1 + c, y + depth, z1 + c)),
                   ((x0, y - 0.02, z1), (x1, y + depth, z1 + c))):
        g.box(frame, lo, hi, faces='xXyzZ')
    if planks is False and mat != 'door_garage':
        # two raised panels and a rail, so the finish catches light like a door
        for pz0, pz1 in ((z0 + 0.18, z0 + 0.95), (z0 + 1.12, z1 - 0.18)):
            g.box(mat, (x0 + 0.16, y + depth - 0.012, pz0), (x1 - 0.16, y + depth, pz1), faces='xXyzZ')


def slope(g, mat, x0, x1, y0, z0, length, pitch=PITCH, toward=+1, ribs=None):
    """A roof plane x0..x1 from the eave (y0, z0) rising `length` m up the slope toward +Y (toward = +1) or -Y."""
    dy, dz = math.cos(pitch) * length * toward, math.sin(pitch) * length
    p = [(x0, y0, z0), (x1, y0, z0), (x1, y0 + dy, z0 + dz), (x0, y0 + dy, z0 + dz)]
    if toward < 0:
        p = [p[1], p[0], p[3], p[2]]
    g.quad(mat, *p)
    if ribs:
        up = np.array([0.0, math.cos(pitch) * toward, math.sin(pitch)])
        nrm = np.array([0.0, -math.sin(pitch) * toward, math.cos(pitch)])
        n = int(round((x1 - x0) / ribs))
        for i in range(n + 1):
            x = x0 + i * (x1 - x0) / n
            g.obox(mat, (x, y0, z0), (toward, 0, 0), up, nrm, (-0.007, 0.0, 0.0), (0.007, length, 0.032), faces='xXyYZ')
    return dy, dz


def gable(g, mat, x0, y0, z0, w=4.0, length=4.0, ribs=None, wall_mat='siding_bb'):
    """A little gabled shed: two w x length slopes over walls of wall_mat (eave at z0)."""
    run = math.cos(PITCH) * length
    rise = math.sin(PITCH) * length
    slope(g, mat, x0, x0 + w, y0, z0, length, toward=+1, ribs=ribs)
    slope(g, mat, x0, x0 + w, y0 + 2 * run, z0, length, toward=-1, ribs=ribs)
    e = 0.25                                                      # eave / rake overhang
    xa, xb, ya, yb = x0 + e, x0 + w - e, y0 + e, y0 + 2 * run - e
    wall(g, wall_mat, (xa, ya), (xb, ya), 0.0, z0 + e * math.tan(PITCH))
    wall(g, wall_mat, (xb, yb), (xa, yb), 0.0, z0 + e * math.tan(PITCH))
    for x, flip in ((xa, True), (xb, False)):                     # gable ends
        zt = z0 + rise
        pts = [(x, ya, 0.0), (x, yb, 0.0), (x, yb, z0 + e * math.tan(PITCH)), (x, y0 + run, zt - 0.001),
               (x, ya, z0 + e * math.tan(PITCH))]
        g.poly(wall_mat, pts[::-1] if flip else pts, uv_o=(x, ya, 0.0))
    # fascia + gutter along the sunny eave, a ridge cap
    g.box('trim_white', (x0, y0 - 0.02, z0 - 0.16), (x0 + w, y0 + 0.0, z0 + 0.0), faces='xXyzZ')
    g.box('gutter_dark', (x0, y0 - 0.14, z0 - 0.13), (x0 + w, y0 - 0.02, z0 - 0.01), faces='xXyzZ')
    g.prism(mat, [(-0.11, -0.03), (0.0, 0.035), (0.11, -0.03)], (x0, y0 + run, z0 + rise), (x0 + w, y0 + run, z0 + rise))


def build():
    parts = []

    # ---------------------------------------------------------------- ground
    g = Geo()
    g.poly('lawn', [(-18, -22, 0), (46, -22, 0), (46, 40, 0), (-18, 40, 0)],
           holes=[[(0.9, 7.5, 0), (5.1, 7.5, 0), (5.1, 11.7, 0), (0.9, 11.7, 0)]])
    parts.append(Part('lawn', g, group='site'))

    g = Geo()
    t = 0.04                                                      # paving stands 4 cm over the lawn
    g.box('bluestone', (0, 0, -0.1), (6, 6, t), faces='xXyYZ')
    g.box('paver_drive', (6.4, 0, -0.1), (12.4, 6, t), faces='xXyYZ')
    g.box('concrete', (12.8, 3.1, -0.1), (18.8, 6, t), faces='xXyYZ')
    g.box('asphalt', (12.8, 0, -0.1), (18.8, 2.9, 0.02), faces='xXyYZ')
    g.box('paving_pale', (6.4, 6.6, -0.1), (12.4, 12.6, t), faces='xXyYZ')
    g.box('mulch', (12.8, 6.6, -0.1), (15.7, 12.6, 0.03), faces='xXyYZ')
    g.box('soil', (15.9, 6.6, -0.1), (18.8, 12.6, 0.02), faces='xXyYZ')
    # three bluestone steps (risers 0.17) up to a landing, like the porch
    for i in range(3):
        g.box('bluestone', (19.6, 0.0 + 0.36 * i, 0.0), (23.2, 3.0, 0.17 * (i + 1)), faces='xXyYZ')
    parts.append(Part('paving', g, group='site'))

    # a pool corner: coping ring, tile band, plaster shell, water of the water family
    g = Geo()
    x0, y0, x1, y1, c = 0.9, 7.5, 5.1, 11.7, 0.36
    g.extrude('coping', [(x0 - c, y0 - c), (x1 + c, y0 - c), (x1 + c, y1 + c), (x0 - c, y1 + c)], 0.0, 0.05,
              holes=[[(x0, y0), (x1, y0), (x1, y1), (x0, y1)]], cap_bottom=False)
    for a, b in (((x0, y0), (x0, y1)), ((x0, y1), (x1, y1)), ((x1, y1), (x1, y0)), ((x1, y0), (x0, y0))):
        wall(g, 'pool_tile', a, b, -0.15, 0.0)
        wall(g, 'pool_plaster', a, b, -1.3, -0.15)
    g.box('pool_plaster', (x0, y0, -1.5), (x1, y1, -1.3), faces='Z')
    g.box('pool_tile', (x0 + 2.6, y0 + 2.6, -1.3), (x1, y1, -0.45), faces='xyZ')      # a tiled bench (the spa step)
    parts.append(Part('pool', g, group='site'))
    g = Geo()
    g.box('pool_water', (x0, y0, -0.3), (x1, y1, -0.07), faces='Z')
    parts.append(Part('pool_water', g, group='site'))

    # ---------------------------------------------------------------- walls
    g = Geo()
    H = 3.0
    wall(g, 'siding_lap', (0, 14), (3, 14), 0, H, [(1.0, 2.0, 0.0, 2.44)])
    wall(g, 'siding_lap', (3, 14), (3, 15), 0, H)                              # outside corner, the face toward +X
    wall(g, 'siding_lap', (3, 15), (6, 15), 0, H, [(1.0, 2.0, 0.0, 2.44)])     # recessed: inside corners at both ends
    wall(g, 'siding_lap', (6, 15), (6, 14), 0, H)
    wall(g, 'siding_bb', (6, 14), (9, 14), 0, H)
    wall(g, 'chimney_white', (9, 14), (12.6, 14), 0, H, [(0.5, 3.1, 0.0, 2.3)])
    wall(g, 'siding_lap', (12.6, 14), (12.6, 15), 0, H)
    wall(g, 'siding_lap', (0, 15), (0, 14), 0, H)
    door(g, 'door_navy', 1.0, 2.0, 14, 0.0, 2.44)
    door(g, 'door_wood', 4.0, 5.0, 15, 0.0, 2.44)
    door(g, 'door_garage', 9.5, 12.1, 14, 0.0, 2.3)
    for x, y in ((3, 14), (6, 14), (0, 14), (12.6, 14)):                     # corner boards
        g.box('trim_white', (x - 0.09, y - 0.02, 0), (x + 0.09, y + 0.09, H), faces='xXyzZ')
    n = int(round(3 / BATTEN))
    for i in range(1, n):                                                     # battens 64 x 19 mm
        x = 6 + i * 3.0 / n
        g.box('trim_white', (x - 0.032, 14 - 0.019, 0), (x + 0.032, 14, H), faces='xXyZ')
    # porch slab over the first two panels: soffit, fascia, gutter
    g.box('trim_white', (-0.3, 12.8, H), (6.3, 15, H + 0.24), faces='xXyYZ')
    g.box('soffit_white', (-0.3, 12.8, H), (6.3, 15, H + 0.24), faces='z')
    g.box('gutter_dark', (-0.3, 12.68, H + 0.10), (6.3, 12.8, H + 0.23), faces='xXyzZ')
    g.box('trim_white', (0.1, 12.95, 0.0), (0.4, 13.25, H), faces='xXyY')      # a 0.3 m square column
    # the awning over the garage door: a dark metal tray on two rods
    g.obox('metal_awning', (12.3, 14.0, 2.62), (-1, 0, 0), (0, -math.cos(0.2), -math.sin(0.2)),
           (0, -math.sin(0.2), math.cos(0.2)), (0, 0, 0), (3.0, 0.9, 0.05))
    g.box('metal_awning', (9.3, 13.1, 2.36), (12.3, 13.14, 2.5), faces='xXyYzZ')
    for x in (9.5, 12.1):
        g.cylinder('metal_awning', (x, 13.2, 2.5), (x, 14.0, 2.95), 0.008, n=6)
    parts.append(Part('walls', g, group='house'))

    # stone plinth + planter wall with caps
    g = Geo()
    g.box('stone_veneer', (0.0, 13.1, 0.0), (0.9, 14.0, 0.5), faces='xXy')
    g.box('bluestone', (-0.03, 13.07, 0.5), (0.93, 14.0, 0.55), faces='xXyZ')
    g.extrude('stone_veneer', [(13.6, 10.0), (18.4, 10.0), (18.4, 10.5), (15.2, 10.5), (15.2, 11.6), (13.6, 11.6)],
              0.0, 0.92, cap_top=False, cap_bottom=False)
    g.extrude('coping', [(13.57, 9.97), (18.43, 9.97), (18.43, 10.53), (15.23, 10.53), (15.23, 11.63), (13.57, 11.63)],
              0.92, 0.97, cap_bottom=False)
    parts.append(Part('stone', g, group='house'))

    # ---------------------------------------------------------------- roofs
    g = Geo()
    gable(g, 'roof_shingle', 26.0, 2.0, 1.4)
    parts.append(Part('roof_shingle', g, group='house'))
    g = Geo()
    gable(g, 'roof_seam', 31.0, 2.0, 1.4, ribs=PAN, wall_mat='siding_lap')
    parts.append(Part('roof_seam', g, group='house'))
    g = Geo()
    g.box('siding_lap', (36.2, 2.2, 0.0), (39.8, 5.8, 1.5), faces='xXyY')
    g.box('roof_flat', (36.0, 2.0, 1.5), (40.0, 6.0, 1.56), faces='xXyYZ')
    g.box('chimney_white', (38.4, 4.4, 1.56), (39.2, 5.2, 3.0), faces='xXyY')
    g.box('chimney_cap', (38.33, 4.33, 3.0), (39.27, 5.27, 3.08), faces='xXyYzZ')
    for i in range(5):                                                        # the cap's standing-seam hood
        x = 38.45 + i * 0.175
        g.box('chimney_cap', (x, 4.45, 3.08), (x + 0.012, 5.15, 3.42), faces='xXyYZ')
    g.box('chimney_cap', (38.45, 4.45, 3.38), (39.15, 5.15, 3.42), faces='xXyYzZ')
    for x, y in ((36.1, 7.2), (39.9, 7.2), (36.1, 10.4), (39.9, 10.4)):       # a louvred pergola frame
        g.box('pergola_metal', (x - 0.075, y - 0.075, 0.0), (x + 0.075, y + 0.075, 2.6), faces='xXyY')
    g.box('pergola_metal', (36.0, 7.1, 2.6), (40.0, 7.3, 2.85), faces='xXyYzZ')
    g.box('pergola_metal', (36.0, 10.3, 2.6), (40.0, 10.5, 2.85), faces='xXyYzZ')
    for i in range(20):
        y = 7.42 + i * 0.148
        g.obox('pergola_metal', (36.0, y, 2.72), (1, 0, 0), (0, math.cos(0.6), math.sin(0.6)), (0, -math.sin(0.6), math.cos(0.6)),
               (0, -0.06, -0.008), (4.0, 0.06, 0.008))
    g.box('bluestone', (35.6, 6.8, -0.1), (40.4, 10.9, 0.04), faces='xXyYZ')
    parts.append(Part('roof_flat', g, group='house'))

    # ---------------------------------------------------------------- fence
    g = Geo()
    fx0, fx1, fy, fh = 12.0, 24.0, 24.0, 1.83
    wall(g, 'fence_wood', (fx0, fy), (fx1, fy), 0.05, fh)
    wall(g, 'fence_wood', (fx1, fy + 0.02), (fx0, fy + 0.02), 0.05, fh)
    for i in range(6):                                                        # posts every 2.4 m, cap rail
        x = fx0 + i * 2.4
        g.box('fence_wood', (x - 0.07, fy - 0.06, 0.0), (x + 0.07, fy + 0.08, fh + 0.32), faces='xXyYZ')
    g.box('fence_wood', (fx0, fy - 0.045, fh), (fx1, fy + 0.065, fh + 0.04), faces='xXyYzZ')
    g.box('fence_wood', (fx0, fy - 0.045, fh + 0.28), (fx1, fy + 0.065, fh + 0.32), faces='xXyYzZ')
    for z in (0.35, 1.05):
        g.box('fence_wood', (fx0, fy - 0.04, z), (fx1, fy, z + 0.09), faces='xXyzZ')
    parts.append(Part('fence', g, group='site'))
    return parts


VIEWS = {
    'all': dict(label='Everything', pos=(-9.0, -20.0, 11.0), target=(17.0, 10.0, 0.5), fov=42),
    'walls_6m': dict(label='Walls 6 m', pos=(4.2, 7.6, 1.65), target=(4.6, 14.5, 1.55), fov=48),
    'siding_1p5m': dict(label='Siding 1.5 m', pos=(2.55, 12.5, 1.6), target=(2.75, 14.0, 1.45), fov=45),
    'doors_3m': dict(label='Doors 3 m', pos=(3.2, 11.2, 1.6), target=(3.3, 14.5, 1.3), fov=50),
    'bb_garage_6m': dict(label='Board & batten, garage 6 m', pos=(9.2, 8.0, 1.65), target=(9.4, 14.0, 1.5), fov=48),
    'stone_1p5m': dict(label='Stone 1.5 m', pos=(-0.35, 11.75, 1.25), target=(0.45, 13.1, 0.3), fov=45),
    'stone_6m': dict(label='Planter wall 6 m', pos=(15.6, 4.2, 1.6), target=(16.0, 10.0, 0.5), fov=40),
    'paving_1p5m': dict(label='Paving 1.5 m', pos=(6.2, -1.0, 1.6), target=(6.2, 1.2, 0.0), fov=50),
    'paving_6m': dict(label='Paving 6 m', pos=(9.5, -6.5, 2.2), target=(9.5, 4.0, 0.0), fov=50),
    'steps_3m': dict(label='Bluestone steps 3 m', pos=(18.2, -2.4, 1.5), target=(21.2, 1.0, 0.3), fov=45),
    'pool_3m': dict(label='Pool corner 3 m', pos=(-1.3, 5.2, 1.7), target=(2.6, 9.4, -0.3), fov=50),
    'ground_3m': dict(label='Mulch, soil, pale paving 3 m', pos=(12.6, 4.6, 1.7), target=(13.4, 9.0, 0.0), fov=55),
    'lawn_1p5m': dict(label='Lawn 1.5 m', pos=(-4.0, -4.0, 1.5), target=(-3.2, -2.0, 0.0), fov=50),
    'lawn_30m': dict(label='Lawn 30 m', pos=(-14.0, -18.0, 1.7), target=(8.0, -2.0, 0.0), fov=40),
    'roofs_6m': dict(label='Roofs 6 m', pos=(30.6, -4.6, 3.6), target=(30.8, 3.6, 2.2), fov=50),
    'roofs_top': dict(label='Roofs from above', pos=(33.0, 4.4, 30.0), target=(33.0, 5.2, 0.0), fov=30),
    'roofs_30m': dict(label='Roofs 30 m', pos=(22.0, -26.0, 9.0), target=(33.0, 5.0, 1.5), fov=30),
    'roof_shingle_2m': dict(label='Shingles 2 m', pos=(27.6, 0.4, 2.6), target=(28.0, 3.2, 2.1), fov=45),
    'roof_seam_2m': dict(label='Standing seam 2 m', pos=(32.6, 0.4, 2.6), target=(33.0, 3.2, 2.1), fov=45),
    'pergola_6m': dict(label='Pergola, flat roof 6 m', pos=(34.0, 0.5, 4.4), target=(38.2, 7.0, 1.8), fov=50),
    'fence_1p5m': dict(label='Fence 1.5 m', pos=(16.6, 22.5, 1.55), target=(16.9, 24.0, 1.2), fov=45),
    'fence_6m': dict(label='Fence 6 m', pos=(17.0, 18.0, 1.65), target=(18.0, 24.0, 1.0), fov=48),
    'far_30m': dict(label='Walls 30 m', pos=(2.0, -16.0, 1.7), target=(8.0, 14.0, 1.6), fov=30),
}
