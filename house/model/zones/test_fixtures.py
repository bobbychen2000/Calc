"""Test zone of the EXTERIOR FIXTURES family (model/fixtures.py, web/viewer/looks/fixtures.js).

    python3 -I model/build.py --zones test_fixtures --out test_fixtures
    node tools/shot.cjs out/tmp/fixtures/porch.png "glb=test_fixtures.glb&meta=test_fixtures_meta.json&view=porch&still=1" 1400
    python3 -I model/zones/test_fixtures.py          # triangle count of every asset against its budget

A small white test building, lit like the house (sun az 205, el 40: the faces toward -Y are sunlit):

  left wing   x 0..7, y 0..6: one storey under a hipped STANDING-SEAM roof (ribs, folded hip / ridge caps, fascia,
              K gutters round the corner, downspouts).  Its front 2.4 m is an open porch: single and paired
              columns, beam, board ceiling with down-lights, bluestone steps with step lights, lanterns on the
              wall and on the columns.  The slatted garage canopy on four rods hangs on its left wall.
  right wing  x 7..13, y 0.6..6.6: two storeys under a SHINGLE roof, hipped on the left and gabled on the right
              (cap shingles on ridge and hips, vents, a skylight, a 3-module solar array), the tall white chimney
              with its black shroud at the gable, the closed bay-window canopy on three rods over an upper window.
  pergola     x 7.15..12.85, y -3.1..0.6, in front of the right wing: the house's louvred pergola with heaters,
              speakers, lanterns either side of a slider.
  fence       along y = 9.5 from x = -13.5 to -1.3: a 2.13 m yard run with a gate, stepping up to the 3.4 m
              privacy run; a return along x = -13.5.
"""
import math
import os
import sys

import numpy as np

if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from model import fixtures as F
from model.kit import Geo, Part

X, Y, Z = np.eye(3)

VIEWS = {
    'porch': dict(label='Porch (p02)', pos=(-1.6, -3.4, 1.65), target=(4.2, 1.9, 2.35), fov=52),
    'roofs': dict(label='Roofs (seg002_043)', pos=(-4.5, -12.5, 8.6), target=(6.2, 2.0, 4.0), fov=44),
    'top': dict(label='Top (p30)', pos=(6.5, 2.4, 33.0), target=(6.5, 3.0, 0.0), fov=30),
    'pergola': dict(label='Pergola (p25)', pos=(10.0, -7.8, 1.5), target=(10.0, 0.6, 2.0), fov=60),
    'fence': dict(label='Fence (p27)', pos=(-6.8, -5.0, 1.6), target=(-6.8, 9.5, 1.75), fov=36),
    'lantern': dict(label='Lantern 1.5 m', pos=(0.75, 1.05, 2.4), target=(1.45, 2.4, 2.48), fov=38),
    'steps': dict(label='Step lights', pos=(3.5, -2.9, 1.25), target=(3.5, -0.3, 0.3), fov=42),
    'awning': dict(label='Garage canopy', pos=(-7.5, 0.6, 5.2), target=(0.0, 4.2, 2.6), fov=32),
    'chimney': dict(label='Chimney cap', pos=(8.5, -6.5, 7.6), target=(13.4, 1.7, 8.7), fov=22),
    'upper': dict(label='Shingle roof', pos=(4.0, -9.0, 10.5), target=(10.2, 2.4, 6.4), fov=36),
}

PITCH_M = 4.5 / 12          # metal roof
PITCH_S = 6.0 / 12          # shingle roof
FLOOR = 0.51                # porch floor: three 0.17 m risers


def P(g, mat, pts, hint, **kw):
    F._poly(g, mat, pts, hint, **kw)


def rect_wall(g, mat, a, b, z0, z1, out):
    P(g, mat, [(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)], out, uv_o=(a[0], a[1], 0.0))


def opening(g, c, right, out, w, h, frame='frame_black', fill='glass', bar=0.06, depth=0.02):
    """A framed panel on a wall (stand-in for a door / window): c = bottom centre on the wall face."""
    L = F.wall_frame(c, right, out)
    L.box(g, frame, (-w / 2, 0, 0), (w / 2, depth, h), faces='xXYzZ')
    L.poly(g, fill, [(-w / 2 + bar, depth + 0.002, bar), (w / 2 - bar, depth + 0.002, bar),
                     (w / 2 - bar, depth + 0.002, h - bar), (-w / 2 + bar, depth + 0.002, h - bar)], (0, 1, 0))


def shell():
    g = Geo()
    P(g, 'lawn', [(-20, -16, 0), (24, -16, 0), (24, 18, 0), (-20, 18, 0)], Z)
    lo = F.Loc((0, 0, 0), X, Y, Z)
    # ---- left wing: platform, steps, walls ----
    lo.box(g, 'stone_veneer', (0, 0, 0.002), (7, 6, FLOOR), faces='xyY', mats={})
    P(g, 'bluestone', [(0, 0, FLOOR), (7, 0, FLOOR), (7, 6, FLOOR), (0, 6, FLOOR)], Z)
    lo.box(g, 'bluestone', (2.5, -0.72, 0.002), (4.5, 0.0, 0.17), faces='xXyZ')
    lo.box(g, 'bluestone', (2.5, -0.36, 0.17), (4.5, 0.0, 0.34), faces='xXyZ')
    rect_wall(g, 'siding_lap', (0, 2.4), (7, 2.4), FLOOR, 3.36, -Y)
    rect_wall(g, 'siding_lap', (0, 2.4), (0, 6), FLOOR, 3.36, -X)
    rect_wall(g, 'siding_lap', (0, 6), (7, 6), FLOOR, 3.36, Y)
    opening(g, (2.4, 2.4, FLOOR), X, -Y, 1.0, 2.44, fill='door_navy')
    opening(g, (5.2, 2.4, FLOOR), X, -Y, 2.0, 2.44)
    opening(g, (0, 4.2, 0.02), -Y, -X, 3.0, 2.2, frame='trim_white', fill='door_garage', bar=0.09)
    P(g, 'soffit_white', [(-0.40, -0.37, 3.35), (7, -0.37, 3.35), (7, 6.4, 3.35), (-0.40, 6.4, 3.35)], -Z)
    # ---- right wing ----
    for a, b, o in (((7, 0.6), (13, 0.6), -Y), ((13, 6.6), (7, 6.6), Y), ((7, 6.6), (7, 0.6), -X)):
        rect_wall(g, 'siding_lap', a, b, 0, 6.0, o)
    P(g, 'siding_bb', [(13, 0.6, 0), (13, 6.6, 0), (13, 6.6, 6.2), (13, 3.6, 7.7), (13, 0.6, 6.2)], X,
      uv_o=(13, 0.6, 0))
    P(g, 'soffit_white', [(6.6, 0.2, 6.0), (13.4, 0.2, 6.0), (13.4, 7.0, 6.0), (6.6, 7.0, 6.0)], -Z)
    opening(g, (10.0, 0.6, 0.15), X, -Y, 2.8, 2.44)
    opening(g, (10.0, 0.6, 3.6), X, -Y, 2.0, 1.4)
    lo.box(g, 'bluestone', (6.9, -3.5, 0.002), (13.1, 0.6, 0.15), faces='xXyZ')
    lo.box(g, 'chimney_white', (13.0, 1.2, 0), (13.8, 2.2, 8.6), faces='xXyY')
    return g


def roofs():
    """The roof planes of both wings: [(material, polygon, eave direction)]."""
    e, r = 3.55, 3.55 + 3.385 * PITCH_M
    metal = [
        ('roof_seam', [(-0.40, -0.37, e), (7, -0.37, e), (7, 3.015, r), (2.985, 3.015, r)], X),
        ('roof_seam', [(-0.40, 6.4, e), (-0.40, -0.37, e), (2.985, 3.015, r)], Y),
        ('roof_seam', [(7, 6.4, e), (-0.40, 6.4, e), (2.985, 3.015, r), (7, 3.015, r)], X),
    ]
    e2, r2 = 6.0, 6.0 + 3.4 * PITCH_S
    shingle = [
        ('roof_shingle', [(6.6, 0.2, e2), (13.4, 0.2, e2), (13.4, 3.6, r2), (10.0, 3.6, r2)], X),
        ('roof_shingle', [(6.6, 7.0, e2), (6.6, 0.2, e2), (10.0, 3.6, r2)], Y),
        ('roof_shingle', [(13.4, 7.0, e2), (6.6, 7.0, e2), (10.0, 3.6, r2), (13.4, 3.6, r2)], X),
    ]
    return metal, shingle


def build():
    parts = [Part('test_shell', shell())]
    metal, shingle = roofs()
    g = Geo()
    for mat, poly, ed in metal + shingle:
        up = np.cross(F.poly_normal(poly), ed)
        P(g, mat, poly, Z, uv_u=ed if up[2] > 0 else -np.asarray(ed, float))
    parts.append(Part('test_roof_planes', g))

    # ---- metal roof: ribs, caps ----
    g = Geo()
    nm = [F.poly_normal(p) for _, p, _ in metal]
    for _, poly, ed in metal:
        F.seam_ribs(g, poly, ed, top_inset=0.05)
    e, r = 3.55, 3.55 + 3.385 * PITCH_M
    apex = (2.985, 3.015, r)
    F.hip_cap(g, (-0.40, -0.37, e), apex, 'seam', nm[0], nm[1])
    F.hip_cap(g, (-0.40, 6.4, e), apex, 'seam', nm[1], nm[2])
    F.ridge_cap(g, apex, (7, 3.015, r), 'seam', nm[0], nm[2])
    parts.append(Part('fx_seam_roof', g))

    # ---- shingle roof: caps, vents, skylight, solar ----
    g = Geo()
    ns = [F.poly_normal(p) for _, p, _ in shingle]
    e2, r2 = 6.0, 6.0 + 3.4 * PITCH_S
    apex2 = (10.0, 3.6, r2)
    F.hip_cap(g, (6.6, 0.2, e2), apex2, 'shingle', ns[0], ns[1])
    F.hip_cap(g, (6.6, 7.0, e2), apex2, 'shingle', ns[1], ns[2])
    F.ridge_cap(g, apex2, (13.4, 3.6, r2), 'shingle', ns[0], ns[2])
    for x, y in ((7.6, 3.0), (7.95, 4.4), (7.5, 5.2)):
        F.vent_stack(g, (x, y, e2 + (x - 6.6) * PITCH_S), ns[1])
    F.vent_stack(g, (7.75, 0.8, e2 + 0.6 * PITCH_S), ns[0])
    us = np.array([0.0, 1.0, PITCH_S]) / math.hypot(1.0, PITCH_S)
    on = lambda x, s: np.array([x, 0.2, e2]) + s * us            # point of the front face: x, slope distance
    F.skylight(g, on(8.62, 0.93), X, us)
    F.solar_array(g, on(9.78, 0.35), X, us, rows=1, cols=3)
    parts.append(Part('fx_shingle_roof', g))

    # ---- eaves: fascia, gutters, downspouts ----
    g = Geo()
    F.fascia(g, (7, -0.37, e), (-0.40, -0.37, e), -Y)
    F.fascia(g, (-0.40, -0.37, e), (-0.40, 6.4, e), -X)
    F.fascia(g, (-0.40, 6.4, e), (7, 6.4, e), Y)
    F.gutter(g, [(7, -0.37, e), (-0.40, -0.37, e), (-0.40, 6.4, e), (7, 6.4, e)], -Y)
    zg = e - 0.012 - 0.092
    F.downspout(g, (-0.46, 0.18, zg), (0.05, 0.18, FLOOR), -X)                  # down the corner column
    F.downspout(g, (-0.46, 5.6, zg), (0.0, 5.6, 0.0), -X)
    F.fascia(g, (13.4, 0.2, e2), (6.6, 0.2, e2), -Y)
    F.fascia(g, (6.6, 0.2, e2), (6.6, 7.0, e2), -X)
    F.fascia(g, (6.6, 7.0, e2), (13.4, 7.0, e2), Y)
    F.fascia(g, (13.4, 0.2, e2), (13.4, 3.6, r2), X, h=0.16)                    # rake boards
    F.fascia(g, (13.4, 3.6, r2), (13.4, 7.0, e2), X, h=0.16)
    F.gutter(g, [(13.4, 0.2, e2), (6.6, 0.2, e2), (6.6, 7.0, e2), (13.4, 7.0, e2)], -Y)
    zg2 = e2 - 0.104
    F.downspout(g, (7.12, 0.14, zg2), (7.12, 0.6, 0.15), -Y)
    F.downspout(g, (12.7, 0.14, zg2), (12.7, 0.6, 0.0), -Y)
    parts.append(Part('fx_eaves', g))

    g = Geo()
    F.chimney_cap(g, (13.4, 1.7, 8.6), 0.8, 1.0)
    parts.append(Part('fx_chimney_cap', g))

    # ---- porch ----
    g = Geo()
    top = FLOOR + 2.70
    F.column(g, (0.20, 0.18, FLOOR), 2.70)
    F.column(g, (2.25, 0.18, FLOOR), 2.70)
    F.column(g, (4.75, 0.18, FLOOR), 2.70, pair=0.45)
    F.beam(g, (0.05, 0.18, top), (7.0, 0.18, top))
    F.beam(g, (0.20, 0.33, top), (0.20, 2.4, top))
    cans = F.porch_ceiling(g, (0.35, 0.33, 3.34), X, Y, 6.65, 2.07, lights=(4, 1))
    steps = [F.step_light(g, (x, y, z), X, -Y) for x, y, z in
             ((3.0, -0.72, 0.085), (4.0, -0.72, 0.085), (3.5, -0.36, 0.255), (3.0, 0.0, 0.425), (4.0, 0.0, 0.425))]
    parts.append(Part('fx_porch', g, extras=dict(lights=[list(map(float, p)) for p in cans + steps])))

    # ---- lanterns ----
    g = Geo()
    lamps = [F.lantern(g, o, r, out) for o, r, out in (
        ((1.45, 2.4, FLOOR + 1.97), X, -Y), ((3.45, 2.4, FLOOR + 1.97), X, -Y),
        ((0.20, 0.03, FLOOR + 1.97), X, -Y), ((4.975, 0.03, FLOOR + 1.97), X, -Y),
        ((8.27, 0.6, 2.15), X, -Y), ((11.73, 0.6, 2.15), X, -Y))]
    parts.append(Part('fx_lanterns', g, extras=dict(lamps=[list(map(float, p)) for p in lamps])))

    # ---- awnings ----
    g = Geo()
    F.awning(g, (0.0, 4.2, 2.42), -Y, -X, 3.3, rods=4, slats=4)
    F.awning(g, (10.0, 0.6, 5.12), X, -Y, 2.5, proj=0.80, rods=3, slats=0, rod_rise=0.62, rod_reach=0.62)
    parts.append(Part('fx_awnings', g))

    # ---- pergola ----
    g = Geo()
    info = F.pergola(g, (7.15, -3.1, 0.15), X, Y, 5.7, 3.7, 3.07, speakers=((1.27, 2.60), (4.43, 2.60)))
    parts.append(Part('fx_pergola', g, extras=dict(lights=[list(map(float, p)) for p in info['lights']])))

    # ---- fence ----
    g = Geo()
    F.fence(g, [(-13.5, 2.18), (-13.5, 9.5), (-11.06, 9.5)], h=2.13, side=-1, end_posts=(True, False))
    F.gate(g, (-11.06, 9.5), (-9.84, 9.5), h=2.13, side=-1)
    F.fence(g, [(-9.84, 9.5), (-8.62, 9.5)], h=2.13, side=-1, end_posts=(False, False))
    F.fence(g, [(-8.62, 9.5), (-1.3, 9.5), (-1.3, 12.0)], h=3.4, side=-1)
    parts.append(Part('fx_fence', g))
    return parts


def budgets():
    """Triangles of each asset alone, against the brief's budgets."""
    rows = []

    def one(name, budget, fn, per=1.0, unit=''):
        g = Geo()
        fn(g)
        rows.append((name, g.ntri / per, budget, unit))

    one('lantern', 300, lambda g: F.lantern(g, (0, 0, 2), X, -Y))
    one('column', 150, lambda g: F.column(g, (0, 0, 0), 2.7))
    one('gutter / m (6 m run)', 40, lambda g: F.gutter(g, (0, 0, 3), (6, 0, 3), -Y), 6.0, '/m')
    one('gutter + fascia / m (6 m)', 40, lambda g: F.eave(g, (0, 0, 3), (6, 0, 3), -Y), 6.0, '/m')
    poly = [(0, 0, 3), (8, 0, 3), (8, 3, 4.2), (0, 3, 4.2)]
    g = Geo()
    n = F.seam_ribs(g, poly, X)
    rows.append(('seam ribs / rib-m', g.ntri / (n * math.hypot(3, 1.2)), 12, '/m'))
    one('fence / m (12.2 m, h 2.13)', 80, lambda g: F.fence(g, [(0, 0), (12.2, 0)]), 12.2, '/m')
    one('fence / m (12.2 m, h 3.4)', 80, lambda g: F.fence(g, [(0, 0), (12.2, 0)], h=3.4), 12.2, '/m')
    one('gate', 400, lambda g: F.gate(g, (0, 0), (1.22, 0)))
    one('pergola 5.7 x 3.7', 8000, lambda g: F.pergola(g, (0, 0, 0), X, Y, 5.7, 3.7, speakers=((1.3, 2.6), (4.4, 2.6))))
    one('solar array / module (2 x 4)', 30, lambda g: F.solar_array(g, (0, 0, 3), X, Y, 2, 4), 8.0, '/mod')
    one('solar array / module (1 x 1)', 30, lambda g: F.solar_array(g, (0, 0, 3), X, Y, 1, 1), 1.0, '/mod')
    one('chimney cap 1.0 x 1.0', 600, lambda g: F.chimney_cap(g, (0, 0, 8), 1.0, 1.0))
    one('awning (garage, 6.6 m, 4 rods)', 400, lambda g: F.awning(g, (0, 0, 2.5), X, -Y, 6.6))
    one('awning (bay, 3 rods)', 400, lambda g: F.awning(g, (0, 0, 2.5), X, -Y, 2.5, rods=3, slats=0))
    one('skylight', 60, lambda g: F.skylight(g, (0, 0, 3), X, Y))
    one('vent stack', 120, lambda g: F.vent_stack(g, (0, 0, 3)))
    one('downspout', 120, lambda g: F.downspout(g, (0, -0.4, 3), (0, 0, 0), -Y))
    one('step light', 60, lambda g: F.step_light(g, (0, 0, 0.1), X, -Y))
    one('down-light', 60, lambda g: F.downlight(g, (0, 0, 3)))
    one('speaker', 80, lambda g: F.speaker(g, (0, 0, 2), X, -Y))
    one('heater', 80, lambda g: F.heater(g, (0, 0, 2), X, -Z, drop=0.1))
    one('ridge cap seam (4 m)', 40, lambda g: F.ridge_cap(g, (0, 0, 4), (4, 0, 4)))
    one('ridge cap shingle / m (4 m)', 40, lambda g: F.ridge_cap(g, (0, 0, 4), (4, 0, 4), 'shingle'), 4.0, '/m')
    for name, n, b, u in rows:
        print('%-34s %7.1f %-5s budget %5d  %s' % (name, n, u, b, 'ok' if n <= b else 'OVER'))


if __name__ == '__main__':
    budgets()
