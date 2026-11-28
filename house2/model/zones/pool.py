"""Zone 'pool' of house 2: the 20 x 40 ft pool with its coping, automatic-cover lid, two flights of entry steps,
deep-end ledge, the square spa in its east corner, lights, drains, skimmer lids and the water surfaces (white model).

Plan: survey/site.json through model/plan.py.  The water outline (site.pool_water at z 0) is fitted by a true
rectangle (12.63 x 6.05 m; the four surveyed corners lie within 3 cm of it); the coping's OUTER outline is the surveyed
ring itself, vertex for vertex, because zone 'ground' cuts exactly that hole into the flagstone.

LOCAL FRAME (metres; `_frame()`):
    origin  the water rectangle's WEST corner (the cover end, on the SW long wall), at the coping top = the deck, z 0
    x       along the length, NW (cover / deep end, toward the house) -> SE (shallow end, spa)
    y       across, SW wall (y 0) -> NE wall (y W)
    The spa fills the EAST corner: x in [L - SPA, L], y in [W - SPA, W].

Read from the images:
    spa        2.42 m square outside; its mosaic-topped dam (0.34 m wide) on the two pool sides lies a step BELOW the
               coping, just above the water (its plan outline from the aerial projected into p21 and frame 154700
               fits the outer corner at z -0.14 and the inner at -0.09 in both: DAM_Z -0.11) -- not raised above the
               deck; inside a bench ring ~0.47 m wide round a central foot well (aerial; p21 rays put the SW bench's
               front 0.4-0.5 m from the dam), four floor fittings 0.87 x 0.46 m apart (aerial, frame 022100; p21
               shows the NW pair), a step block in the east corner (aerial; weak)
    steps S    3 treads in the south corner, edges parallel to the SW wall, nested; the top one narrow (p21 and
               frame 154700 rays at refracted depths: outer corners 1.3 / 0.2-0.35, 2.25 / 1.1, 2.65 / 1.35; aerial)
    steps W    narrow steps along the SW wall from 0.5 m past the west corner, descending toward the SE (aerial)
    ledge N    a ledge on the NE wall 0.5-1.75 m from the north corner (frame 022100's light strip; aerial)
    cover      the lid strip 0.28 m wide along the NW end, inside the water outline (aerial: bright double strip)
    light      one on the SW wall 8.15 m from the NW end (p21 ray onto the wall plane; apparent depth 0.37)
    drains     two on the deep floor (the aerial's bright dots: x 2.3, y 2.55 / 3.55)
    deck lids  three round lids read in the aerial (0.6-1.0 m outside the long walls), two more from p21's rays at z 0,
               a small white one on the SE coping beside the spa (p21)
Typical values (not measurable): water 0.14 m under the coping top, depths 2.4 m (NW) -> 1.0 m (SE), tread depths,
spa bench 0.45 m / well 0.95 m under its water, coping 50 mm thick, tile band 0.24 m."""
from __future__ import annotations

import math

import numpy as np

from model import plan
from model.kit import Geo, Part, UP

# the deep end needs no material of its own: the viewer's water look (looks/water.js) absorbs light with the real depth
PLASTER, PLASTER_DEEP, MOSAIC, LID = 'pool_plaster', 'pool_plaster', 'spa_mosaic', 'pool_cover_lid'
MATERIALS = {
    PLASTER: dict(color=(0.42, 0.62, 0.66), roughness=0.9),            # grey-turquoise plaster, treads, benches
    MOSAIC: dict(color=(0.45, 0.43, 0.44), roughness=0.25, metallic=0.2),   # iridescent glass mosaic of the spa dam
    LID: dict(color=(0.60, 0.62, 0.64), roughness=0.35, metallic=0.8),      # automatic-cover lid
    'pool_light': dict(color=(0.85, 0.92, 0.95), roughness=0.3, emissive=(0.25, 0.4, 0.45)),
    'pool_fitting': dict(color=(0.82, 0.83, 0.82), roughness=0.5),
    'pool_gap': dict(color=(0.012, 0.013, 0.015), roughness=0.9),
    'coping_joint': dict(color=(0.42, 0.40, 0.36), roughness=0.95),
    'skimmer_lid': dict(color=(0.62, 0.60, 0.54), roughness=0.7),
    'spa_water': dict(color=(0.041, 0.42, 0.60), roughness=0.05, alpha=0.86),
}

# ---- sizes (metres) -------------------------------------------------------------------------------------------------
WATER_DROP = 0.14            # water surface under the coping top
SPA_DROP = 0.17              # spa water under the coping top (two tile rows under the dam top, p21)
DAM_Z = -0.11                # top of the spa's mosaic dam: a step below the coping (p21, frame 154700), just above the water
COPING_T, OVERHANG, GAP = 0.05, 0.02, 0.01
TILE_BOT = -0.30             # bottom of the waterline tile band
STONE = 0.61                 # coping stone length
JOINT = 0.004
DEPTH = ((0.0, 2.4), (0.30, 2.4), (0.62, 1.1), (1.0, 1.0))     # (fraction of the length from the NW end, water depth)
DEEP_UNTIL = 0.46            # floor strips whose middle lies before this fraction take the darker plaster
SPA, DAM = 2.42, 0.34
SPA_BENCH = dict(sw=0.47, nw=0.47, ne=0.47, se=0.47)      # bench widths; the foot well is what they leave
SPA_BENCH_D, SPA_WELL_D = 0.45, 0.80
SPA_STEP = (0.45, 0.22)      # east-corner step block: (side, depth under the spa water)
SPA_FIT = (0.87, 0.46)       # spacing of the four floor fittings along x, y (aerial; p21 shows the NW pair)
COVER_W = 0.28
STEPS_S = ((1.3, 0.35, 0.20), (2.2, 1.10, 0.45), (2.6, 1.45, 0.70))    # (along the SW wall, out from it, depth)
STEPS_W = dict(x0=0.5, run=0.53, out=0.40, n=4, rise=0.30)
LEDGE_N = dict(x0=0.5, x1=1.75, out=0.48, depth=0.5)
LIGHTS = ((8.15, 0.42),)     # on the SW wall: (x, depth under the coping top)
DRAINS = ((2.3, 2.55), (2.3, 3.55))
DECK_FITTINGS = ((12.75, 4.98, 0.055),)      # small white round lid on the SE coping beside the spa (p21 ray): x, y, r
SKIMMERS = ((10.72, -0.62), (2.29, 6.60), (4.34, 7.07), (7.43, -1.05), (8.69, 6.50))    # deck lids (local x, y)


def _frame():
    """Origin (world x, y), unit axes ex / ey, L, W of the rectangle fitted to the surveyed water corners (W N E S)."""
    r = plan.aerial_ring(plan.site('site.pool_water')['poly'], 0.0)
    w, n, e, s = r
    ex = (s - w) + (e - n)
    ex /= np.linalg.norm(ex)
    ey = np.array([-ex[1], ex[0]])
    if ey @ (n - w) < 0:
        ey = -ey
    c = r.mean(0)
    L = 0.5 * ((s - w) @ ex + (e - n) @ ex)
    W = 0.5 * ((n - w) @ ey + (e - s) @ ey)
    o = c - ex * L / 2 - ey * W / 2
    return o, ex, ey, float(L), float(W)


def spa_well(L, W):
    """The spa's foot well (x0, y0, x1, y1) in the local frame."""
    b = SPA_BENCH
    return L - SPA + DAM + b['nw'], W - SPA + DAM + b['sw'], L - b['se'], W - b['ne']


def _face(g, mat, pts, toward):
    """Planar polygon whose normal points toward `toward`."""
    pts = np.asarray(pts, float)
    q = np.roll(pts, -1, 0)
    n = np.array([((pts[:, 1] - q[:, 1]) * (pts[:, 2] + q[:, 2])).sum(),
                  ((pts[:, 2] - q[:, 2]) * (pts[:, 0] + q[:, 0])).sum(),
                  ((pts[:, 0] - q[:, 0]) * (pts[:, 1] + q[:, 1])).sum()])
    if n @ np.asarray(toward, float) < 0:
        pts = pts[::-1]
    g.poly(mat, pts)


def _top(g, mat, x0, y0, x1, y1, z):
    _face(g, mat, [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], (0, 0, 1))


def _vwall(g, mat, a, b, z0, z1, toward):
    """Vertical rectangle over the plan segment a -> b between heights z0 and z1."""
    if abs(z1 - z0) < 1e-6:
        return
    _face(g, mat, [(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)], toward)


def _disc(g, mat, c, n, r, seg=14):
    c, n = np.asarray(c, float), np.asarray(n, float)
    u = np.cross(n, UP)
    u = u / np.linalg.norm(u) if np.linalg.norm(u) > 1e-6 else np.array([1.0, 0, 0])
    v = np.cross(n, u)
    a = np.linspace(0, 2 * np.pi, seg, endpoint=False)
    _face(g, mat, [c + r * (math.cos(t) * u + math.sin(t) * v) for t in a], n)


def _block(g, mat, x0, y0, x1, y1, z_top, z_bot, faces='xXyY'):
    """Underwater block (tread, bench): top + the listed side faces down to z_bot (scalar or f(x))."""
    zb = z_bot if callable(z_bot) else (lambda x: z_bot)
    _top(g, mat, x0, y0, x1, y1, z_top)
    if 'x' in faces:
        _vwall(g, mat, (x0, y0), (x0, y1), zb(x0), z_top, (-1, 0, 0))
    if 'X' in faces:
        _vwall(g, mat, (x1, y0), (x1, y1), zb(x1), z_top, (1, 0, 0))
    for f, y, nrm in (('y', y0, (0, -1, 0)), ('Y', y1, (0, 1, 0))):
        if f in faces:
            _face(g, mat, [(x0, y, zb(x0)), (x1, y, zb(x1)), (x1, y, z_top), (x0, y, z_top)], nrm)


def build():
    o, ex, ey, L, W = _frame()
    g = Geo()                                    # local coordinates
    wl = -WATER_DROP
    xs, ys = L - SPA, W - SPA                    # the spa's outer faces toward the pool
    xi, yi = xs + DAM, ys + DAM                  # its inner faces
    prof = [(f * L, d) for f, d in DEPTH]

    def fz(x):
        return wl - float(np.interp(x, [p[0] for p in prof], [p[1] for p in prof]))

    # ---- floor (strips along the length; the deep ones darker) and the plaster walls ------------------------------
    xk = sorted(set([0.0, L, xs] + [p[0] for p in prof]))
    cuts = []
    for a, b in zip(xk[:-1], xk[1:]):
        n = max(1, int(math.ceil((b - a) / 1.0)))
        cuts += list(np.linspace(a, b, n + 1)[:-1])
    cuts.append(L)
    for x0, x1 in zip(cuts[:-1], cuts[1:]):
        mat = PLASTER_DEEP if (x0 + x1) / 2 < DEEP_UNTIL * L else PLASTER
        y1 = ys if x0 >= xs - 1e-9 else W
        _face(g, mat, [(x0, 0, fz(x0)), (x1, 0, fz(x1)), (x1, y1, fz(x1)), (x0, y1, fz(x0))], (0, 0, 1))
        for y, nrm, on in ((0.0, (0, 1, 0), True), (W, (0, -1, 0), x0 < xs - 1e-9)):
            if on:
                _face(g, mat, [(x0, y, fz(x0)), (x1, y, fz(x1)), (x1, y, TILE_BOT), (x0, y, TILE_BOT)], nrm)
        if x0 >= xs - 1e-9:                      # the spa's outer wall along the pool (below its mosaic band)
            _face(g, mat, [(x0, ys, fz(x0)), (x1, ys, fz(x1)), (x1, ys, TILE_BOT), (x0, ys, TILE_BOT)], (0, -1, 0))
    _vwall(g, PLASTER_DEEP, (0, 0), (0, W), fz(0), TILE_BOT, (1, 0, 0))             # NW end
    _vwall(g, PLASTER, (L, 0), (L, ys), fz(L), TILE_BOT, (-1, 0, 0))                # SE end
    _vwall(g, PLASTER, (xs, ys), (xs, W), fz(xs), TILE_BOT, (-1, 0, 0))             # spa wall toward the NW

    # ---- waterline tile, shadow gap, coping -----------------------------------------------------------------------
    zt = -(COPING_T + GAP)
    for a, b, nrm in (((0, 0), (L, 0), (0, 1, 0)), ((L, 0), (L, ys), (-1, 0, 0)), ((0, W), (xs, W), (0, -1, 0)),
                      ((0, 0), (0, W), (1, 0, 0))):
        _vwall(g, 'pool_tile', a, b, TILE_BOT, zt, nrm)
        _vwall(g, 'pool_gap', a, b, zt, -COPING_T, nrm)
    # coping: inner edge = the water rectangle moved OVERHANG into the pool, outer edge = the surveyed ring
    cop = plan.aerial_ring(plan.site('site.pool_coping')['poly'], 0.0)
    outer = np.stack([(cop - o) @ ex, (cop - o) @ ey], 1)                 # local; order W N E S like the water
    inner = np.array([(OVERHANG, OVERHANG), (OVERHANG, W - OVERHANG), (L - OVERHANG, W - OVERHANG),
                      (L - OVERHANG, OVERHANG)])
    g.poly('coping_joint', [(p[0], p[1], -JOINT) for p in outer[::-1]],
           holes=[[(p[0], p[1], -JOINT) for p in inner[::-1]]])
    for i in range(4):
        j = (i + 1) % 4
        a, b, A, B = inner[i], inner[j], outer[i], outer[j]
        n = max(1, int(round(np.linalg.norm(B - A) / STONE)))
        for k in range(n):
            t0, t1 = k / n, (k + 1) / n
            q = np.array([a + (b - a) * t0, a + (b - a) * t1, B + (A - B) * (1 - t1), A + (B - A) * t0])
            c = q.mean(0)
            d = q - c
            q = c + d * (1 - JOINT / np.maximum(np.linalg.norm(d, axis=1), 1e-6))[:, None]
            _face(g, 'coping', [(p[0], p[1], 0.0) for p in q], (0, 0, 1))
        nrm = np.array([L / 2, W / 2]) - (a + b) / 2                      # inner face, looking into the pool
        _vwall(g, 'coping', a, b, -COPING_T, 0.0, (nrm[0], nrm[1], 0))
    # the underside of the overhang (seen from low across the water)
    g.poly('pool_gap', [(p[0], p[1], -COPING_T) for p in [(0, 0), (0, W), (L, W), (L, 0)]],
           holes=[[(p[0], p[1], -COPING_T) for p in inner]])

    # ---- automatic cover: lid strip along the NW end, just under the coping, its fascia down into the water -------
    z_lid = -0.035
    _top(g, LID, OVERHANG, OVERHANG, COVER_W, W - OVERHANG, z_lid)
    _top(g, 'pool_gap', OVERHANG + 0.13, OVERHANG, OVERHANG + 0.14, W - OVERHANG, z_lid + 0.001)    # the lid's joint
    _vwall(g, LID, (COVER_W, OVERHANG), (COVER_W, W - OVERHANG), z_lid - 0.03, z_lid, (1, 0, 0))
    _vwall(g, 'pool_gap', (COVER_W, 0), (COVER_W, W), wl - 0.10, z_lid - 0.03, (1, 0, 0))

    # ---- steps and ledges ------------------------------------------------------------------------------------------
    for along, out, dep in reversed(STEPS_S):                             # south corner, nested from the corner
        _block(g, PLASTER, L - along, 0.0, L, out, wl - dep, fz, faces='xY')
    s = STEPS_W
    for k in range(s['n']):                                               # west corner, along the SW wall
        x0 = s['x0'] + k * s['run']
        _block(g, PLASTER, x0, 0.0, x0 + s['run'], s['out'], wl - (k + 1) * s['rise'], fz(0),
               faces='xXY' if k == 0 else 'XY')
    e = LEDGE_N
    _block(g, PLASTER, e['x0'], W - e['out'], e['x1'], W, wl - e['depth'], fz(0), faces='xXy')

    # ---- spa -------------------------------------------------------------------------------------------------------
    # dam top (mosaic, a step below the coping): an L along the two pool sides
    zd = DAM_Z
    _top(g, MOSAIC, xs, ys, L, yi, zd)
    _top(g, MOSAIC, xs, yi, xi, W, zd)
    _vwall(g, MOSAIC, (xs, ys), (L, ys), TILE_BOT, zd, (0, -1, 0))        # outer faces, mosaic to under the water
    _vwall(g, MOSAIC, (xs, ys), (xs, W), TILE_BOT, zd, (-1, 0, 0))
    _vwall(g, 'pool_gap', (L - OVERHANG, ys), (L - OVERHANG, yi), zd, -COPING_T, (-1, 0, 0))   # under the coping at
    _vwall(g, 'pool_gap', (xs, W - OVERHANG), (xi, W - OVERHANG), zd, -COPING_T, (0, -1, 0))   # the dam's two ends
    sw = -SPA_DROP
    zb, zw = sw - SPA_BENCH_D, sw - SPA_WELL_D
    for a, b, nrm, dam in (((xi, yi), (L, yi), (0, 1, 0), True), ((xi, yi), (xi, W), (1, 0, 0), True),
                           ((xi, W), (L, W), (0, -1, 0), False), ((L, yi), (L, W), (-1, 0, 0), False)):
        top = zd if dam else zt
        _vwall(g, MOSAIC if dam else 'pool_tile', a, b, TILE_BOT, top, nrm)
        if not dam:
            _vwall(g, 'pool_gap', a, b, zt, -COPING_T, nrm)
        _vwall(g, PLASTER, a, b, zb, TILE_BOT, nrm)
    wx0, wy0, wx1, wy1 = spa_well(L, W)                                   # the central foot well
    g.poly(PLASTER, [(xi, yi, zb), (L, yi, zb), (L, W, zb), (xi, W, zb)],  # the bench ring round it
           holes=[[(wx0, wy0, zb), (wx0, wy1, zb), (wx1, wy1, zb), (wx1, wy0, zb)]])
    for a, b, nrm in (((wx0, wy0), (wx1, wy0), (0, 1, 0)), ((wx0, wy1), (wx1, wy1), (0, -1, 0)),
                      ((wx0, wy0), (wx0, wy1), (1, 0, 0)), ((wx1, wy0), (wx1, wy1), (-1, 0, 0))):
        _vwall(g, PLASTER, a, b, zw, zb, nrm)
    _top(g, PLASTER, wx0, wy0, wx1, wy1, zw)
    st = SPA_STEP                                                         # entry step block in the east corner
    _block(g, PLASTER, L - st[0], W - st[0], L, W, sw - st[1], zb, faces='xy')
    cx, cy, hx, hy = (wx0 + wx1) / 2, (wy0 + wy1) / 2, SPA_FIT[0] / 2, SPA_FIT[1] / 2
    for dx, dy in ((-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)):                   # four round floor fittings (aerial, 022100)
        _disc(g, 'pool_light', (cx + dx, cy + dy, zw + 0.004), (0, 0, 1), 0.10)
    for fx in (0.3, 0.7):                                                 # jets in the SW bench's back wall
        _disc(g, 'pool_fitting', (xi + (L - xi) * fx, yi + 0.004, sw - 0.25), (0, 1, 0), 0.035, seg=8)

    # ---- fittings --------------------------------------------------------------------------------------------------
    for x, dep in LIGHTS:
        _disc(g, 'pool_fitting', (x, 0.004, -dep), (0, 1, 0), 0.13)
        _disc(g, 'pool_light', (x, 0.008, -dep), (0, 1, 0), 0.10)
    for x, y in DRAINS:
        _disc(g, 'pool_fitting', (x, y, fz(x) + 0.006), (0, 0, 1), 0.16)
    for x, y in SKIMMERS:                                                 # round lids in the deck
        _disc(g, 'skimmer_lid', (x, y, 0.006), (0, 0, 1), 0.14)
        _disc(g, 'pool_gap', (x, y, 0.004), (0, 0, 1), 0.155)
    for x, y, r in DECK_FITTINGS:
        _disc(g, 'pool_fitting', (x, y, 0.005), (0, 0, 1), r, seg=10)

    # ---- water -----------------------------------------------------------------------------------------------------
    water = Geo()
    pool_rects = [(0.0, 0.0, xs, W), (xs, 0.0, L, ys)]
    for r in pool_rects:
        _top(water, 'pool_water', r[0], r[1], r[2], r[3], wl)
    spa_rect = (xi, yi, L, W)
    _top(water, 'spa_water', *spa_rect, sw)

    R = np.array([[ex[0], ey[0], 0.0], [ex[1], ey[1], 0.0], [0.0, 0.0, 1.0]])
    t = np.array([o[0], o[1], 0.0])
    shell, wat = Geo().merge(g, R=R, t=t), Geo().merge(water, R=R, t=t)

    def world(x, y, z=0.0):
        return [round(float(v), 3) for v in (t + R @ np.array([x, y, z]))]

    info = dict(origin=world(0, 0), ex=[round(float(v), 4) for v in ex], ey=[round(float(v), 4) for v in ey],
                length=round(L, 3), width=round(W, 3), water_z=wl, spa_water_z=sw, coping_z=0.0,
                depth=[[round(a, 2), d] for a, d in prof],
                pool_water=[[world(r[0], r[1], wl), world(r[2], r[1], wl), world(r[2], r[3], wl),
                             world(r[0], r[3], wl)] for r in pool_rects],
                spa_water=[world(spa_rect[0], spa_rect[1], sw), world(spa_rect[2], spa_rect[1], sw),
                           world(spa_rect[2], spa_rect[3], sw), world(spa_rect[0], spa_rect[3], sw)],
                lights=[world(x, 0, -d) for x, d in LIGHTS], spa=[world(xs, ys), world(L, ys), world(L, W), world(xs, W)])
    return [Part('pool_shell', shell, group='site', extras=info),
            Part('pool_water', wat, group='site', extras=dict(kind='water', water_z=wl))]


if __name__ == '__main__':
    o, ex, ey, L, W = _frame()
    print('pool: origin %s  ex %s  L %.2f  W %.2f' % (np.round(o, 2), np.round(ex, 3), L, W))
    r = plan.aerial_ring(plan.site('site.pool_water')['poly'], 0.0)
    for name, p, q in zip('WNES', r, [(0, 0), (0, W), (L, W), (L, 0)]):
        print('  corner %s: survey %s  fitted %s' % (name, np.round(p, 2), np.round(o + ex * q[0] + ey * q[1], 2)))
    print('triangles', sum(p.ntri for p in build()))
