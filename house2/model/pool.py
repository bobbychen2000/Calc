"""Pool family: the long rectangular pool with its coping, waterline tile, entry steps, deep-end bench, attached
flush spa, automatic-cover lid strip, lights, drains, skimmer and the water surfaces.

    info = pool(geo, origin, right, back, length, width, ...)

LOCAL FRAME (everything below is given in it; units are metres):
    origin  world point = the water-rectangle corner at the COVER (deep) end on the HOUSE side, at the level of the
            TOP OF THE COPING (the surveyed landmark "pool_water_SW" + the coping-top height),
    right   unit horizontal vector along the pool's LENGTH, from the cover end to the spa / cabana end  (local x)
    back    unit horizontal vector along the pool's WIDTH, away from the house                          (local y)
    up      +Z                                                                                         (local z)
    The water rectangle (the face of the waterline tile) is x in [0, length], y in [0, width]; z = 0 is the top of
    the coping, the water surface is at z = -water_drop.  right x back may be left-handed (a mirrored pool): the
    builder then flips the triangle winding.

The shell is built to its TRUE depths; the viewer's water look (web/viewer/looks/water.js) refracts it.

Materials (by name):
    coping        (surfaces family)  the limestone coping stones, cover-lid stones and the deck block at the cover end.
                  Every stone is its own slab with a real joint; its UVs are metres local to the stone (u along the
                  pool edge, v across) with a per-stone offset so a tiling stone texture differs from slab to slab:
                  the 'coping' texture should NOT draw joints of its own.
    pool_tile     (surfaces family)  the waterline tile band; u runs along the wall, v = 0 at the TOP edge of the band
                  (a 0.152 m tile module then has a full course under the coping).
    pool_plaster  white plaster of the shell, steps and benches                  } registered here and in water.js;
    spa_tile      the spa's dam-wall tops, outer faces and bench (under water)   } they carry the underwater shading
    pool_light    the light lenses (emissive at dusk)                            } (refraction, absorption, caustics)
    pool_fitting  white plastic: light rings, returns, drain covers, skimmer weir}
    pool_gap      the dark shadow gap / cover track under the coping, open joints of the cover lid, skimmer throat
    coping_joint  mortar in the coping joints
    skimmer_lid   the round lid of the skimmer in the lawn
    pool_water, spa_water   the two water surfaces (kind 'water'): UV = (0, distance to the nearest tiled wall in
                  metres, capped) - the look draws the contact line from it.
"""
from __future__ import annotations

import numpy as np

from model import materials
from model.kit import Geo, UP

materials.register('pool_plaster', color=(0.80, 0.86, 0.86), roughness=0.9)
materials.register('spa_tile', color=(0.030, 0.105, 0.26), roughness=0.3)
materials.register('pool_light', color=(0.85, 0.92, 0.95), roughness=0.3, emissive=(0.25, 0.4, 0.45))
materials.register('pool_fitting', color=(0.82, 0.83, 0.82), roughness=0.5)
materials.register('pool_gap', color=(0.012, 0.013, 0.015), roughness=0.9)
materials.register('coping_joint', color=(0.42, 0.40, 0.36), roughness=0.95)
materials.register('skimmer_lid', color=(0.62, 0.60, 0.54), roughness=0.7)
materials.register('pool_water', color=(0.041, 0.47, 0.67), roughness=0.05, alpha=0.35)
materials.register('spa_water', color=(0.041, 0.42, 0.67), roughness=0.05, alpha=0.35)

TILE_PROUD = 0.006          # the tile face stands this far in front of the plaster wall
EDGE = 0.06                 # width of the water surface's wall strip (its UV v = distance to the wall)
N_REFRACT = 1.333


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def _face(g, mat, pts, toward, **kw):
    """Planar polygon whose normal points toward `toward` (whatever the order of pts)."""
    pts = np.asarray(pts, float)
    q = np.roll(pts, -1, 0)
    n = np.array([((pts[:, 1] - q[:, 1]) * (pts[:, 2] + q[:, 2])).sum(),
                  ((pts[:, 2] - q[:, 2]) * (pts[:, 0] + q[:, 0])).sum(),
                  ((pts[:, 0] - q[:, 0]) * (pts[:, 1] + q[:, 1])).sum()])
    if n @ np.asarray(toward, float) < 0:
        pts = pts[::-1]
        if 'holes' in kw:
            kw['holes'] = [np.asarray(h, float)[::-1] for h in kw['holes']]
    g.poly(mat, pts, **kw)


def _top(g, mat, x0, y0, x1, y1, z, **kw):
    _face(g, mat, [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], (0, 0, 1), **kw)


def _wall(g, mat, a, b, z_top, z_bot_a, z_bot_b, toward, **kw):
    """Vertical quad over the plan segment a -> b from z_top down to z_bot_a / z_bot_b."""
    _face(g, mat, [(a[0], a[1], z_bot_a), (b[0], b[1], z_bot_b), (b[0], b[1], z_top), (a[0], a[1], z_top)], toward,
          **kw)


def _disc(g, mat, c, n, u, r, seg=12, ring=None, mat_ring=None):
    """Flat disc (and an optional outer ring r .. ring) centred at c with normal n; u = any in-plane direction."""
    c, n, u = np.asarray(c, float), _unit(n), _unit(u)
    v = np.cross(n, u)
    ang = np.linspace(0, 2 * np.pi, seg, endpoint=False)
    p = [c + r * (np.cos(t) * u + np.sin(t) * v) for t in ang]
    _face(g, mat, p, n)
    if ring:
        q = [c + ring * (np.cos(t) * u + np.sin(t) * v) - 0.002 * n for t in ang]
        _face(g, mat_ring or mat, q, n, holes=[[pp - 0.002 * n for pp in p]])


def _rng(i, k=0):
    """Deterministic pseudo-random number in [0, 1) for stone i, stream k."""
    x = np.sin(i * 127.1 + k * 311.7 + 0.5) * 43758.5453
    return float(x - np.floor(x))


def pool(geo, origin, right, back, length=16.57, width=5.5, *,
         # coping (z = 0 is its top)
         coping_w=0.45, coping_t=0.05, coping_overhang=0.02, coping_len=0.61, coping_joint=0.005, coping_ease=0.006,
         coping_gap=0.012, outer_skirt=0.0,
         # water line and tile band
         water_drop=0.165, tile_below=0.125,
         # floor: (fraction of the length from the cover end, water depth), linear in between
         depth=((0.0, 2.05), (0.28, 2.05), (0.60, 1.30), (1.0, 1.15)),
         # spa (flush with the pool, in the house-side corner of the far end): outer size along x, along y
         spa=(2.78, 2.27), spa_dam=0.33, spa_dam_sub=0.03, spa_bench_depth=0.45, spa_well_depth=0.95,
         spa_bench=(0.42, 0.47, 0.20, 0.59),      # bench widths: toward the pool (-x), +x wall, house wall, +y dam
         # entry steps on the house-side wall beside the spa
         steps=3, step_run=0.30, step_rise=0.30, step_w=1.45, step_top_len=2.7,
         # swim-out bench in the house-side corner of the deep end: (length along x, width, depth below the water)
         bench=(1.4, 0.45, 0.45),
         # automatic-cover lid strip beyond the coping of the cover end, and how far the deck block runs past
         # the far-side coping
         cover_lid=0.48, cover_ext=0.32, lid_len=1.12,
         # fittings: fractions of the length along the house-side wall
         skimmers=(0.565,), lights=(0.20, 0.47), light_depth=0.55, drains=True):
    """Build the pool into `geo` (see the module docstring for the frame and the material names).

    All sizes in metres.  Returns a dict:
      water_z, coping_z      world heights of the water surface and of the coping top
      water                  {'pool_water': [...], 'spa_water': [...]}: lists of world rectangles (4 corners each,
                             counter-clockwise seen from above) that make up each surface
      water_local            the same rectangles as (x0, y0, x1, y1) in the local frame
      depth(wx, wy)          water depth (m, > 0) under a world plan point; 0 outside the water
      depth_local(x, y)      the same in local coordinates
      to_world(x, y, z=0)    local -> world
      footprint              plan outline (world x, y; counter-clockwise) of everything built at grade: coping, cover
                             lid and deck block - cut this out of the lawn / paving
      spa, steps, bench      local plan rectangles (x0, y0, x1, y1) of those features (None when absent)
      lights, skimmer_lids, drains   world points
      triangles              {'shell': n, 'water': n}
    """
    origin = np.asarray(origin, float)
    ex, ey = _unit(right), _unit(back)
    R = np.stack([ex, ey, UP], 1)
    hand = np.sign(np.cross(ex, ey) @ UP) or 1.0
    L, W = float(length), float(width)
    g = Geo()                                   # local coordinates
    cw, ct, ov = coping_w, coping_t, coping_overhang
    wl = -water_drop                             # water level
    z_tt = -(ct + coping_gap)                    # top of the tile band
    z_tb = wl - tile_below                       # bottom of the tile band
    tp = TILE_PROUD

    prof = sorted((float(f) * L, float(d)) for f, d in depth)

    def floor_depth(x):
        return float(np.interp(x, [p[0] for p in prof], [p[1] for p in prof]))

    def fz(x):
        return wl - floor_depth(x)

    has_spa = bool(spa)
    sl, sw = (spa if has_spa else (0.0, 0.0))
    xs = L - sl                                  # outer face of the spa's dam toward the pool
    xi, yi = xs + spa_dam, sw - spa_dam          # inner faces of the two dam walls
    z_dam = wl - spa_dam_sub

    # ---------------------------------------------------------------------------------------- floor and walls
    xk = sorted(set([0.0, L] + [p[0] for p in prof if 0 < p[0] < L] + ([xs] if has_spa else [])))
    xcuts = []
    for a, b in zip(xk[:-1], xk[1:]):
        n = max(1, int(np.ceil((b - a) / 1.05)))
        xcuts += list(np.linspace(a, b, n + 1)[:-1])
    xcuts.append(L)
    yk = sorted(set([0.0, W] + ([sw] if has_spa else [])))
    ycuts = []
    for a, b in zip(yk[:-1], yk[1:]):
        n = max(1, int(np.ceil((b - a) / 1.15)))
        ycuts += list(np.linspace(a, b, n + 1)[:-1])
    ycuts.append(W)
    for x0, x1 in zip(xcuts[:-1], xcuts[1:]):
        for y0, y1 in zip(ycuts[:-1], ycuts[1:]):
            if has_spa and x0 >= xs - 1e-9 and y1 <= sw + 1e-9:
                continue                         # under the spa
            _face(g, 'pool_plaster', [(x0, y0, fz(x0)), (x1, y0, fz(x1)), (x1, y1, fz(x1)), (x0, y1, fz(x0))],
                  (0, 0, 1))

    def plaster_wall(a, b, toward, z_top=z_tb):
        """Plaster wall over the plan segment a -> b (split along its length and once in height)."""
        a, b = np.asarray(a, float), np.asarray(b, float)
        n = max(1, int(np.ceil(np.linalg.norm(b - a) / 1.05)))
        for i in range(n):
            p, q = a + (b - a) * i / n, a + (b - a) * (i + 1) / n
            zp, zq = fz(p[0]), fz(q[0])
            mp, mq = (z_top + zp) / 2, (z_top + zq) / 2
            _face(g, 'pool_plaster', [(p[0], p[1], mp), (q[0], q[1], mq), (q[0], q[1], z_top), (p[0], p[1], z_top)],
                  toward)
            _face(g, 'pool_plaster', [(p[0], p[1], zp), (q[0], q[1], zq), (q[0], q[1], mq), (p[0], p[1], mp)], toward)

    x_s_end = xs if has_spa else L
    y_e_start = sw if has_spa else 0.0
    plaster_wall((0, -tp), (x_s_end, -tp), (0, 1, 0))                    # house side
    plaster_wall((0, W + tp), (L, W + tp), (0, -1, 0))                   # far side
    plaster_wall((-tp, 0), (-tp, W), (1, 0, 0))                          # cover end
    plaster_wall((L + tp, y_e_start), (L + tp, W), (-1, 0, 0))           # spa / cabana end

    # ---------------------------------------------------------------------------------------- waterline tile
    sk_w, sk_top, sk_bot, sk_deep = 0.34, wl + 0.07, wl - 0.055, 0.22
    sk_x = [float(f) * L for f in skimmers]

    def tile_band(a, b, toward, holes=()):
        a, b = np.asarray(a, float), np.asarray(b, float)
        d = _unit(b - a)
        hs = [[(a[0] + d[0] * s0, a[1] + d[1] * s0, z0), (a[0] + d[0] * s1, a[1] + d[1] * s1, z0),
               (a[0] + d[0] * s1, a[1] + d[1] * s1, z1), (a[0] + d[0] * s0, a[1] + d[1] * s0, z1)]
              for s0, s1, z0, z1 in holes]
        _face(g, 'pool_tile', [(a[0], a[1], z_tb), (b[0], b[1], z_tb), (b[0], b[1], z_tt), (a[0], a[1], z_tt)],
              toward, holes=hs, uv_u=(d[0], d[1], 0.0), uv_o=(a[0], a[1], z_tt))
        # the underside of the band (it stands proud of the plaster)
        o = -np.asarray(toward, float)[:2] * tp
        _face(g, 'pool_tile', [(a[0], a[1], z_tb), (b[0], b[1], z_tb), (b[0] + o[0], b[1] + o[1], z_tb),
                               (a[0] + o[0], a[1] + o[1], z_tb)], (0, 0, -1))

    tile_band((0, 0), (L, 0), (0, 1, 0), holes=[(x - sk_w / 2, x + sk_w / 2, sk_bot, sk_top) for x in sk_x])
    tile_band((L, W), (0, W), (0, -1, 0))
    tile_band((0, W), (0, 0), (1, 0, 0))
    tile_band((L, 0), (L, W), (-1, 0, 0))
    for x in sk_x:                               # skimmer throat: a dark box behind the opening, a pale weir flap
        x0, x1 = x - sk_w / 2, x + sk_w / 2
        _face(g, 'pool_gap', [(x0, -sk_deep, sk_bot), (x1, -sk_deep, sk_bot), (x1, -sk_deep, sk_top),
                              (x0, -sk_deep, sk_top)], (0, 1, 0))
        _face(g, 'pool_gap', [(x0, 0, sk_bot), (x0, -sk_deep, sk_bot), (x0, -sk_deep, sk_top), (x0, 0, sk_top)],
              (1, 0, 0))
        _face(g, 'pool_gap', [(x1, 0, sk_bot), (x1, -sk_deep, sk_bot), (x1, -sk_deep, sk_top), (x1, 0, sk_top)],
              (-1, 0, 0))
        _face(g, 'pool_gap', [(x0, 0, sk_top), (x1, 0, sk_top), (x1, -sk_deep, sk_top), (x0, -sk_deep, sk_top)],
              (0, 0, -1))
        _face(g, 'pool_gap', [(x0, 0, sk_bot), (x1, 0, sk_bot), (x1, -sk_deep, sk_bot), (x0, -sk_deep, sk_bot)],
              (0, 0, 1))
        _face(g, 'pool_fitting', [(x0 + 0.02, -0.035, sk_bot + 0.004), (x1 - 0.02, -0.035, sk_bot + 0.004),
                                  (x1 - 0.02, -0.075, wl - 0.006), (x0 + 0.02, -0.075, wl - 0.006)], (0, 0.5, 1))

    # ---------------------------------------------------------------------------------------- coping
    stone = [0]

    def slab(p0, along, inward, ln, wd, pool_edge=True, joint_start=True, inner_edge=True):
        """One coping stone: plan corner p0 (outer, start), unit vectors along / inward, length, width."""
        p0, along, inward = np.asarray(p0, float), np.asarray(along, float), np.asarray(inward, float)
        i = stone[0]
        stone[0] += 1
        j = coping_joint / 2
        a3, i3 = np.array([along[0], along[1], 0.0]), np.array([inward[0], inward[1], 0.0])
        o = np.array([p0[0], p0[1], 0.0])
        e = coping_ease if pool_edge else 0.0
        s0, s1 = j, ln - j
        uvo = o - a3 * (_rng(i, 1) * 7.0 + 0.3) - i3 * (_rng(i, 2) * 5.0 + 0.3)
        P = lambda s, t, z=0.0: o + a3 * s + i3 * t + np.array([0, 0, z])
        _face(g, 'coping', [P(s0, 0), P(s1, 0), P(s1, wd - e), P(s0, wd - e)], (0, 0, 1), uv_u=a3, uv_o=uvo)
        if pool_edge:
            _face(g, 'coping', [P(s0, wd - e), P(s1, wd - e), P(s1, wd, -e), P(s0, wd, -e)], i3 + UP, uv_u=a3,
                  uv_o=uvo)
            _face(g, 'coping', [P(s0, wd, -ct), P(s1, wd, -ct), P(s1, wd, -e), P(s0, wd, -e)], i3, uv_u=a3,
                  uv_o=uvo + i3 * wd)
            _face(g, 'coping', [P(s0, wd - ov - tp, -ct), P(s1, wd - ov - tp, -ct), P(s1, wd, -ct), P(s0, wd, -ct)],
                  (0, 0, -1), uv_u=a3, uv_o=uvo)
        elif inner_edge:
            _face(g, 'coping', [P(s0, wd, -ct), P(s1, wd, -ct), P(s1, wd), P(s0, wd)], i3, uv_u=a3, uv_o=uvo)
        if outer_skirt > 0:
            _face(g, 'coping', [P(s0, 0, -outer_skirt), P(s1, 0, -outer_skirt), P(s1, 0), P(s0, 0)], -i3, uv_u=a3,
                  uv_o=uvo)
        if joint_start:                           # the mortar joint at the stone's start
            _face(g, 'coping_joint', [P(-j, 0, -0.003), P(j, 0, -0.003), P(j, wd - e, -0.003), P(-j, wd - e, -0.003)],
                  (0, 0, 1))
            if pool_edge:
                _face(g, 'coping_joint', [P(-j, wd - 0.003, -ct), P(j, wd - 0.003, -ct), P(j, wd - 0.003, -0.003),
                                          P(-j, wd - 0.003, -0.003)], i3)

    def course(p0, along, inward, total, wd, **kw):
        n = max(1, int(round(total / coping_len)))
        ln = total / n
        p0 = np.asarray(p0, float)
        for k in range(n):
            slab(p0 + np.asarray(along, float) * ln * k, along, inward, ln, wd, joint_start=k > 0, **kw)

    full = cw + ov
    course((-cw, -cw), (1, 0), (0, 1), L + 2 * cw, full)                         # house side (incl. both corners)
    course((L + cw, W + cw), (-1, 0), (0, -1), L + 2 * cw, full)                 # far side
    course((-cw, W - ov), (0, -1), (1, 0), W - 2 * ov, full)                     # cover end, between the long sides
    course((L + cw, ov), (0, 1), (-1, 0), W - 2 * ov, full)                      # spa end
    for (a, b, t) in (((-cw, ov), (-cw, -cw + full), (1, 0)), ((-cw, W - ov), (-cw + full, W - ov), (0, -1)),
                      ((L + cw, ov), (L + cw - full, ov), (0, 1)), ((L + cw, W - ov), (L + cw - full, W - ov), (0, -1))):
        pass                                     # (butt joints at the corners are the courses' own ends)
    for x, y, dx, dy in ((-cw, ov, 1, 0), (-cw, W - ov, 1, 0), (L - ov, ov, 1, 0), (L - ov, W - ov, 1, 0)):
        # the joint between an end course and a long course
        j = coping_joint / 2
        _face(g, 'coping_joint', [(x, y - j, -0.003), (x + full, y - j, -0.003), (x + full, y + j, -0.003),
                                  (x, y + j, -0.003)], (0, 0, 1))

    # the dark gap between the coping's underside and the tile (the automatic cover's track on the long sides)
    if coping_gap > 0:
        for a, b, n in (((0, 0), (L, 0), (0, 1, 0)), ((L, W), (0, W), (0, -1, 0)), ((0, W), (0, 0), (1, 0, 0)),
                        ((L, 0), (L, W), (-1, 0, 0))):
            o = -np.asarray(n, float)[:2] * tp
            _face(g, 'pool_gap', [(a[0] + o[0], a[1] + o[1], z_tt), (b[0] + o[0], b[1] + o[1], z_tt),
                                  (b[0] + o[0], b[1] + o[1], -ct), (a[0] + o[0], a[1] + o[1], -ct)], n)
            _face(g, 'pool_tile', [(a[0], a[1], z_tt), (b[0], b[1], z_tt), (b[0] + o[0], b[1] + o[1], z_tt),
                                   (a[0] + o[0], a[1] + o[1], z_tt)], (0, 0, 1))

    # ---------------------------------------------------------------------------------------- cover lid + deck block
    foot = [(-cw, -cw), (L + cw, -cw), (L + cw, W + cw), (-cw, W + cw)]
    if cover_lid > 0:
        x0, x1 = -(cw + cover_lid), -cw
        y0, y1 = -cw, W + cw + cover_ext
        n = max(1, int(round((y1 - y0) / lid_len)))
        ln = (y1 - y0) / n
        gp = 0.004
        for k in range(n):                       # removable lid stones: open joints over a dark tray
            i = stone[0]
            stone[0] += 1
            a, b = y0 + ln * k + gp, y0 + ln * (k + 1) - gp
            uvo = (x0 - _rng(i, 1) * 6 - 0.2, a - _rng(i, 2) * 6 - 0.2, 0.0)
            _top(g, 'coping', x0 + gp, a, x1 - gp, b, 0.0, uv_u=(0, 1, 0), uv_o=uvo)
            if outer_skirt > 0:
                _face(g, 'coping', [(x0 + gp, a, -outer_skirt), (x0 + gp, b, -outer_skirt), (x0 + gp, b, 0),
                                    (x0 + gp, a, 0)], (-1, 0, 0))
        _top(g, 'pool_gap', x0, y0, x1, y1, -0.012)
        if cover_ext > 0:                        # the deck block that continues the coping past the far side
            i = stone[0]
            stone[0] += 1
            _top(g, 'coping', x1 + coping_joint / 2, W + cw + coping_joint / 2, 0.0, y1, 0.0, uv_u=(0, 1, 0),
                 uv_o=(x1 - _rng(i, 1) * 6, W - _rng(i, 2) * 6, 0.0))
            _top(g, 'coping_joint', x1, W + cw - coping_joint / 2, 0.0, W + cw + coping_joint / 2, -0.003)
            _face(g, 'coping', [(0.0, W + cw, -ct), (0.0, y1, -ct), (0.0, y1, 0), (0.0, W + cw, 0)], (1, 0, 0))
        foot = [(x0, y0), (L + cw, -cw), (L + cw, W + cw), (0.0, W + cw), (0.0, y1), (x0, y1)] if cover_ext > 0 \
            else [(x0, -cw), (L + cw, -cw), (L + cw, W + cw), (x0, W + cw)]

    # ---------------------------------------------------------------------------------------- entry steps
    steps_rect = None
    if steps:
        x1 = x_s_end
        x0 = x1 - step_w
        xa = x1 - max(step_top_len, step_w)
        steps_rect = (xa, 0.0, x1, steps * step_run)
        for k in range(steps):
            zt = wl - step_rise * (k + 1)
            y0, y1 = step_run * k, step_run * (k + 1)
            xl = xa if k == 0 else x0
            _top(g, 'pool_plaster', xl, y0 - tp, x1, y1, zt)
            for a, b in ((xl, x0), (x0, x1)) if (k == 0 and xa < x0) else ((xl, x1),):
                last = k == steps - 1 or (b <= x0 + 1e-9)
                zb_a, zb_b = (fz(a), fz(b)) if last else (wl - step_rise * (k + 2),) * 2
                _wall(g, 'pool_plaster', (a, y1), (b, y1), zt, zb_a, zb_b, (0, 1, 0))
            _wall(g, 'pool_plaster', (xl, y0 - tp), (xl, y1), zt, fz(xl), fz(xl), (-1, 0, 0))
            if not has_spa:
                _wall(g, 'pool_plaster', (x1, y0), (x1, y1), zt, fz(x1), fz(x1), (1, 0, 0))

    # ---------------------------------------------------------------------------------------- deep-end bench
    bench_rect = None
    if bench:
        bl, bw, bd = bench
        zt = wl - bd
        bench_rect = (0.0, 0.0, bl, bw)
        _top(g, 'pool_plaster', -tp, -tp, bl, bw, zt)
        _wall(g, 'pool_plaster', (-tp, bw), (bl, bw), zt, fz(0), fz(bl), (0, 1, 0))
        _wall(g, 'pool_plaster', (bl, -tp), (bl, bw), zt, fz(bl), fz(bl), (1, 0, 0))

    # ---------------------------------------------------------------------------------------- spa
    spa_rect = None
    lights_local = []
    if has_spa:
        spa_rect = (xs, 0.0, L, sw)
        b_pool, b_x, b_house, b_y = spa_bench
        zb, zw = wl - spa_bench_depth, wl - spa_well_depth
        band = 0.305                              # tiled band on the dam's outer faces
        # dam tops (an L), just under the water
        _top(g, 'spa_tile', xs, 0.0, xi, sw, z_dam, uv_u=(0, 1, 0), uv_o=(xs, 0.0, z_dam))
        _top(g, 'spa_tile', xi, yi, L, sw, z_dam, uv_u=(1, 0, 0), uv_o=(xi, sw, z_dam))
        # outer faces: tile band, plaster below
        for a, b, n in (((xs, sw), (xs, 0.0), (-1, 0, 0)), ((L, sw), (xs, sw), (0, 1, 0))):
            d = _unit(np.asarray(b, float) - np.asarray(a, float))
            _face(g, 'spa_tile', [(a[0], a[1], z_dam - band), (b[0], b[1], z_dam - band), (b[0], b[1], z_dam),
                                  (a[0], a[1], z_dam)], n, uv_u=(d[0], d[1], 0), uv_o=(a[0], a[1], z_dam))
            o = -np.asarray(n, float)[:2] * tp
            pa, pb = (a[0] + o[0], a[1] + o[1]), (b[0] + o[0], b[1] + o[1])
            _wall(g, 'pool_plaster', pa, pb, z_dam - band, fz(pa[0]), fz(pb[0]), n)
            _face(g, 'spa_tile', [(a[0], a[1], z_dam - band), (b[0], b[1], z_dam - band),
                                  (pb[0], pb[1], z_dam - band), (pa[0], pa[1], z_dam - band)], (0, 0, -1))
        # inner faces down to the bench: plaster (the dam's two, then the two tiled outer walls below their band)
        _wall(g, 'pool_plaster', (xi, 0.0), (xi, yi), z_dam, zb, zb, (1, 0, 0))
        _wall(g, 'pool_plaster', (xi, yi), (L, yi), z_dam, zb, zb, (0, -1, 0))
        _wall(g, 'pool_plaster', (xi, -tp), (L, -tp), z_tb, zb, zb, (0, 1, 0))
        _wall(g, 'pool_plaster', (L + tp, 0.0), (L + tp, yi), z_tb, zb, zb, (-1, 0, 0))
        # bench (tiled top with the foot well cut out), well walls and floor
        wx0, wx1, wy0, wy1 = xi + b_pool, L - b_x, b_house, yi - b_y
        _face(g, 'spa_tile', [(xi, -tp, zb), (L + tp, -tp, zb), (L + tp, yi, zb), (xi, yi, zb)], (0, 0, 1),
              holes=[[(wx0, wy0, zb), (wx1, wy0, zb), (wx1, wy1, zb), (wx0, wy1, zb)]], uv_u=(1, 0, 0),
              uv_o=(xi, yi, zb))
        _wall(g, 'pool_plaster', (wx0, wy0), (wx0, wy1), zb, zw, zw, (1, 0, 0))
        _wall(g, 'pool_plaster', (wx1, wy0), (wx1, wy1), zb, zw, zw, (-1, 0, 0))
        _wall(g, 'pool_plaster', (wx0, wy0), (wx1, wy0), zb, zw, zw, (0, 1, 0))
        _wall(g, 'pool_plaster', (wx0, wy1), (wx1, wy1), zb, zw, zw, (0, -1, 0))
        _top(g, 'pool_plaster', wx0, wy0, wx1, wy1, zw)
        # the pale entry step in the corner beside the pool steps
        sx, sy, sz = 0.40, 0.26, wl - 0.24
        _top(g, 'pool_plaster', xi, -tp, xi + sx, sy, sz)
        _wall(g, 'pool_plaster', (xi, sy), (xi + sx, sy), sz, zb, zb, (0, 1, 0))
        _wall(g, 'pool_plaster', (xi + sx, -tp), (xi + sx, sy), sz, zb, zb, (1, 0, 0))
        if drains:
            for fx in (0.3, 0.7):
                _disc(g, 'pool_fitting', (wx0 + (wx1 - wx0) * fx, (wy0 + wy1) / 2, zw + 0.004), (0, 0, 1), (1, 0, 0),
                      0.085, seg=10)
        # jets on the walls above the bench, a small light under the tile of the house-side wall
        zj = wl - 0.27
        for c, n, u in [((xi + 0.75, yi - 0.004, zj), (0, -1, 0), (1, 0, 0)),
                        ((L - 0.75, yi - 0.004, zj), (0, -1, 0), (1, 0, 0)),
                        ((L + tp - 0.004, 0.55, zj), (-1, 0, 0), (0, 1, 0)),
                        ((L + tp - 0.004, yi - 0.55, zj), (-1, 0, 0), (0, 1, 0)),
                        ((xi + 0.004, yi - 0.6, zj), (1, 0, 0), (0, 1, 0))]:
            _disc(g, 'pool_fitting', c, n, u, 0.03, seg=8)
        c = ((xi + L) / 2 + 0.3, -tp + 0.005, wl - 0.30)
        _disc(g, 'pool_light', c, (0, 1, 0), (1, 0, 0), 0.045, seg=10, ring=0.062, mat_ring='pool_fitting')
        lights_local.append(c)

    # ---------------------------------------------------------------------------------------- lights, returns, drains
    for f in lights:
        c = (float(f) * L, -tp + 0.006, wl - light_depth)
        _disc(g, 'pool_light', c, (0, 1, 0), (1, 0, 0), 0.10, seg=14, ring=0.128, mat_ring='pool_fitting')
        lights_local.append(c)
    for f in (0.12, 0.38, 0.64, 0.88):           # return fittings on the far wall
        _disc(g, 'pool_fitting', (f * L, W + tp - 0.004, wl - 0.33), (0, -1, 0), (1, 0, 0), 0.032, seg=8)
    drains_local = []
    if drains:
        for dy in (-0.45, 0.45):
            c = (prof[0][0] + 0.11 * L, W / 2 + dy, fz(0.11 * L) + 0.005)
            _disc(g, 'pool_fitting', c, (0, 0, 1), (1, 0, 0), 0.115, seg=12)
            drains_local.append(c)
    lids_local = []
    for x in sk_x:
        c = (x, -(cw + 0.30), 0.006)
        _disc(g, 'skimmer_lid', c, (0, 0, 1), (1, 0, 0), 0.14, seg=16)
        lids_local.append(c)
    n_shell = g.ntri

    # ---------------------------------------------------------------------------------------- water surfaces
    def water_rect(mat, x0, y0, x1, y1, walls):
        """Rectangle at the water level with EDGE-wide strips along the sides in `walls` ('x', 'X', 'y', 'Y'):
        UV = (0, distance to that wall); the interior carries UV v = 1."""
        e = EDGE
        ix0, ix1 = x0 + (e if 'x' in walls else 0), x1 - (e if 'X' in walls else 0)
        iy0, iy1 = y0 + (e if 'y' in walls else 0), y1 - (e if 'Y' in walls else 0)
        m = g.mesh(mat)

        def add(pts, vs):
            V = [(p[0], p[1], wl) for p in pts]
            F = [[0, 1, 2], [0, 2, 3]] if len(pts) == 4 else [[0, 1, 2]]
            m.add(V, np.tile(UP, (len(V), 1)), [(0.0, v) for v in vs], F)

        add([(ix0, iy0), (ix1, iy0), (ix1, iy1), (ix0, iy1)], [1.0] * 4)
        if 'y' in walls:
            add([(x0, y0), (x1, y0), (ix1, iy0), (ix0, iy0)], [0, 0, e, e])
        if 'Y' in walls:
            add([(x1, y1), (x0, y1), (ix0, iy1), (ix1, iy1)], [0, 0, e, e])
        if 'x' in walls:
            add([(x0, y1), (x0, y0), (ix0, iy0), (ix0, iy1)], [0, 0, e, e])
        if 'X' in walls:
            add([(x1, y0), (x1, y1), (ix1, iy1), (ix1, iy0)], [0, 0, e, e])
        return (x0, y0, x1, y1)

    water_local = {'pool_water': [], 'spa_water': []}
    if has_spa:
        water_local['pool_water'].append(water_rect('pool_water', 0.0, 0.0, xi, W, 'xyY'))
        water_local['pool_water'].append(water_rect('pool_water', xi, yi, L, W, 'XY'))
        water_local['spa_water'].append(water_rect('spa_water', xi, 0.0, L, yi, 'yX'))
    else:
        water_local['pool_water'].append(water_rect('pool_water', 0.0, 0.0, L, W, 'xXyY'))
    n_water = g.ntri - n_shell

    # ---------------------------------------------------------------------------------------- into the world
    for m in g.meshes():
        t = m.transformed(R, origin)
        if hand < 0:
            t.F = t.F[:, ::-1].copy()
        geo.mesh(m.mat).merge(t)

    def to_world(x, y, z=0.0):
        return origin + ex * x + ey * y + UP * z

    def depth_local(x, y):
        if not (0 <= x <= L and 0 <= y <= W):
            return 0.0
        if has_spa and x >= xs and y <= sw:
            if x < xi or y > yi:
                return spa_dam_sub
            b_pool, b_x, b_house, b_y = spa_bench
            inside = xi + b_pool <= x <= L - b_x and b_house <= y <= yi - b_y
            return spa_well_depth if inside else spa_bench_depth
        if steps_rect and steps_rect[0] <= x <= steps_rect[2] and y <= steps_rect[3]:
            k = int(y // step_run)
            if k == 0 or x >= x_s_end - step_w:
                return step_rise * (k + 1)
        if bench_rect and x <= bench_rect[2] and y <= bench_rect[3]:
            return bench[2]
        return floor_depth(x)

    def depth_world(wx, wy):
        d = np.array([wx, wy, 0.0]) - origin
        return depth_local(float(d @ ex), float(d @ ey))

    def rect_world(r):
        x0, y0, x1, y1 = r
        pts = [to_world(x0, y0, wl), to_world(x1, y0, wl), to_world(x1, y1, wl), to_world(x0, y1, wl)]
        return pts if hand > 0 else pts[::-1]

    fw = [tuple(to_world(x, y)[:2]) for x, y in foot]
    return dict(
        water_z=float(origin[2] + wl), coping_z=float(origin[2]),
        water={k: [rect_world(r) for r in v] for k, v in water_local.items()}, water_local=water_local,
        depth=depth_world, depth_local=depth_local, to_world=to_world,
        footprint=fw if hand > 0 else fw[::-1], footprint_local=foot,
        spa=spa_rect, steps=steps_rect, bench=bench_rect,
        lights=[to_world(*c) for c in lights_local], skimmer_lids=[to_world(*c) for c in lids_local],
        drains=[to_world(*c) for c in drains_local],
        length=L, width=W, triangles=dict(shell=n_shell, water=n_water))
