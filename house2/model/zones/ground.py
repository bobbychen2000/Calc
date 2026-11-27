"""Zone 'ground' of house 2: the terrain and every ground surface.

The lot is PARTITIONED in plan: every surveyed area of survey/site.json (aerial pixels -> world at its own level,
model/plan.py) takes its material, the first one in SURFACES winning where two overlap; what is left inside the
aerial's footprint is mulch, beyond it 'ground_far'.  Every piece is cut by one 1 m grid and its vertices are set on
plan.ground_z, so neighbouring materials share their edges (no cracks, nothing z-fights) and everything the other
zones stand on plan.ground_z sits on this mesh.  Holes: the pool (the coping's outer outline: water, coping and spa
belong to zone 'pool') and the two flights of steps, which are built as solids here.

On the terrain: retaining walls (dry-stacked fieldstone with light caps; tops from the levels either side), the patio
stairs (9 treads, black handrail on the north side) and the path steps down to the synthetic lawn, the raised
planter's walls, stepping stones, the side slab, the timber step, edging, grates / lids, and the far ground + a street
band beyond the lot (the street itself is hidden by the tree screen: its place is a guess).
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, HERE)
from model import plan  # noqa: E402
from model.kit import Geo, Part  # noqa: E402

MATERIALS = {
    'turf_synthetic': dict(color=(0.065, 0.24, 0.035), roughness=0.95),
    'wood_chips': dict(color=(0.55, 0.36, 0.17), roughness=1.0),
    'gravel_path': dict(color=(0.36, 0.39, 0.41), roughness=1.0),
    'crushed_stone': dict(color=(0.30, 0.34, 0.37), roughness=1.0),
    'orchard_soil': dict(color=(0.13, 0.115, 0.075), roughness=1.0),
    'leaf_litter': dict(color=(0.085, 0.065, 0.04), roughness=1.0),
    'fieldstone': dict(color=(0.33, 0.30, 0.25), roughness=0.95),
    'wall_cap': dict(color=(0.52, 0.51, 0.47), roughness=0.85),
    'handrail_black': dict(color=(0.012, 0.012, 0.013), roughness=0.5, metallic=0.5),
    'grate_metal': dict(color=(0.05, 0.052, 0.055), roughness=0.6, metallic=0.6),
    'lid_green': dict(color=(0.03, 0.16, 0.06), roughness=0.7),
    'timber': dict(color=(0.42, 0.28, 0.13), roughness=0.85),
    'edging_dark': dict(color=(0.06, 0.05, 0.04), roughness=0.8),
}

STEP = 1.0          # the grid every surface is cut by (m)
RISE = 0.17

# surface partition, first wins: (site id, material)
SURFACES = [
    ('site.walk_front', 'bluestone'), ('site.walk_rear_curved', 'bluestone'), ('site.patio_pool', 'bluestone'),
    ('site.driveway', 'paver_drive'), ('site.path_gravel', 'gravel_path'),
    ('site.planter_lawn', 'mulch'), ('site.planter_terrace', 'mulch'),
    ('site.lawn_synthetic', 'turf_synthetic'), ('site.lawn_front_upper', 'lawn'), ('site.lawn_front_lower', 'lawn'),
    ('site.lawn_side_north', 'lawn'), ('site.play_area', 'wood_chips'), ('site.garden_enclosure', 'crushed_stone'),
    ('site.side_yard_shade', 'gravel_path'),
    ('site.bed_lounge', 'mulch'), ('site.bed_lawn_terrace', 'mulch'), ('site.bed_patio_tree', 'mulch'),
    ('site.bed_patio_nw', 'mulch'), ('site.bed_rear_courtyard', 'mulch'), ('site.bed_upper_terrace', 'mulch'),
    ('site.bed_lawn_south', 'mulch'), ('site.hedge_lawn_west', 'mulch'), ('site.bed_maple_round', 'mulch'),
    ('site.bed_maple_stairs', 'mulch'), ('site.hedge_path', 'mulch'), ('site.bed_porch', 'mulch'),
    ('site.bed_landing', 'mulch'), ('site.bed_birch', 'mulch'), ('site.bed_garage', 'mulch'),
    ('site.bed_court_recess', 'mulch'), ('site.bed_front_south', 'mulch'), ('site.bed_south_strip', 'mulch'),
    ('site.bed_north_side', 'mulch'), ('site.bed_se_wing', 'mulch'), ('site.bed_lawn1_corner', 'mulch'),
    ('site.bed_drive_corner', 'mulch'), ('site.bed_nw_tree', 'mulch'), ('site.bed_west', 'mulch'),
    ('site.orchard', 'orchard_soil'), ('site.strip_garden_play', 'soil'),
    ('site.trees_north', 'leaf_litter'), ('site.trees_east', 'leaf_litter'), ('site.trees_south', 'leaf_litter'),
]
HOLES = ['site.pool_coping', 'site.stairs_patio_path', 'site.stairs_path_lawn']

# retaining walls: id -> (width m, top: number = level, or ('above', dz) = the higher ground beside it + dz)
WALLS = {
    'site.wall_north': (0.55, ('above', 0.10)),
    'site.wall_terrace_lower': (0.36, 0.58),
    'site.wall_terrace_upper': (0.40, 1.50),
    'site.wall_fireplace_east': (0.36, 0.50),
    'site.wall_planter_chevron': (0.36, None),          # top = the planter's level + 0.10 (see build)
    'site.wall_planter_mid': (0.36, ('above', 0.10)),
    'site.wall_lawn_north': (0.40, ('above', 0.08)),
    'site.wall_lawn_east': (0.85, ('above', 0.10)),
}


# ---- helpers ------------------------------------------------------------------------------------------------
def _ring(eid):
    """A site polygon as a world ring at its level (REGIONS; sloping / unlisted areas: on the terrain)."""
    if eid in plan.REGIONS and eid not in plan.SLOPES:
        return plan.aerial_ring(plan.site(eid)['poly'], plan.REGIONS[eid])
    return plan.ground_ring(plan.site(eid)['poly'])


def _px(pts, z=None):
    """Aerial pixels -> world xy; on the terrain, or at height(s) z."""
    pts = np.atleast_2d(np.asarray(pts, float))
    if z is None:
        return plan.ground_ring(pts)
    return np.atleast_2d(plan.aerial_xy(pts, np.broadcast_to(np.asarray(z, float), (len(pts),))))


def _tris(geo, mat, T):
    """Flat-shaded triangles T (n, 3, 3), normals up-ish, UVs = world xy in metres."""
    T = np.asarray(T, float).reshape(-1, 3, 3)
    if not len(T):
        return
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    flip = n[:, 2] < 0
    T[flip] = T[flip][:, ::-1]
    n[flip] *= -1
    ln = np.linalg.norm(n, axis=1)
    ok = ln > 1e-10
    T, n = T[ok], n[ok] / ln[ok, None]
    V = T.reshape(-1, 3)
    geo.mesh(mat).add(V, np.repeat(n, 3, 0), V[:, :2], np.arange(len(V)).reshape(-1, 3))


def _surface(geo, mat, pg, zf=None):
    """Mesh a plan polygon (shapely) on the terrain, cut by the STEP grid."""
    import mapbox_earcut as earcut
    import shapely
    if pg.is_empty:
        return
    zf = zf or plan.ground_z
    x0, y0, x1, y1 = pg.bounds
    ox, oy = plan.EXTENT[0], plan.EXTENT[1]
    i0, i1 = int(np.floor((x0 - ox) / STEP)), int(np.ceil((x1 - ox) / STEP))
    j0, j1 = int(np.floor((y0 - oy) / STEP)), int(np.ceil((y1 - oy) / STEP))
    I, J = np.meshgrid(np.arange(i0, i1), np.arange(j0, j1))
    cx, cy = ox + I.ravel() * STEP, oy + J.ravel() * STEP
    cells = shapely.box(cx, cy, cx + STEP, cy + STEP)
    shapely.prepare(pg)
    full = shapely.contains(pg, cells)
    part = shapely.intersects(pg, cells) & ~full
    P2 = []
    fx, fy = cx[full], cy[full]
    if len(fx):
        a = np.stack([fx, fy], -1)
        b, c, d = a + (STEP, 0), a + (STEP, STEP), a + (0, STEP)
        P2.append(np.stack([a, b, c], 1))
        P2.append(np.stack([a, c, d], 1))
    for g in shapely.intersection(pg, cells[part]):
        for p in getattr(g, 'geoms', [g]):
            if p.geom_type != 'Polygon' or p.area < 1e-6:
                continue
            rings = [np.asarray(p.exterior.coords)[:-1]] + [np.asarray(h.coords)[:-1] for h in p.interiors]
            allp = np.vstack(rings)
            tri = earcut.triangulate_float64(allp, np.cumsum([len(r) for r in rings]).astype(np.uint32))
            P2.append(allp[tri.reshape(-1, 3)])
    if not P2:
        return
    P2 = np.vstack(P2)
    z = zf(P2[..., 0].ravel(), P2[..., 1].ravel()).reshape(P2.shape[:2])
    _tris(geo, mat, np.concatenate([P2, z[..., None]], -1))


def _hexa(geo, mat, a, b, w, zb, za, zc, cap=None, cap_t=0.06, cap_over=0.03, ext=0.0):
    """A wall piece from plan point a to b, width w, bottom zb, top za at a and zc at b (a sloping top is fine);
    cap: material of a slab on top."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b - a
    L = np.linalg.norm(d)
    if L < 1e-6:
        return
    d /= L
    a, b = a - d * ext, b + d * ext
    s = np.array([-d[1], d[0]])

    def body(m, w2, z0a, z0b, z1a, z1b, e=0.0):
        p = [a - d * e - s * w2, b + d * e - s * w2, b + d * e + s * w2, a - d * e + s * w2]
        zb_ = [z0a, z0b, z0b, z0a]
        zt_ = [z1a, z1b, z1b, z1a]
        B = [np.array([q[0], q[1], z]) for q, z in zip(p, zb_)]
        T = [np.array([q[0], q[1], z]) for q, z in zip(p, zt_)]
        geo.poly(m, [T[0], T[1], T[2], T[3]], uv_u=(d[0], d[1], 0))
        for i in range(4):
            j = (i + 1) % 4
            geo.poly(m, [B[i], B[j], T[j], T[i]])
    top_a, top_c = (za - cap_t, zc - cap_t) if cap else (za, zc)
    body(mat, w / 2, zb, zb, top_a, top_c)
    if cap:
        body(cap, w / 2 + cap_over, top_a, top_c, za, zc, e=cap_over)


def _wall(geo, line, w, tops, piece=3.0, mat='fieldstone', cap='wall_cap', level=True):
    """A wall along a plan polyline; tops: one level, or one per vertex.  Long segments are cut into pieces of
    ~`piece` m; level=True steps the top (each piece level at its higher end, the way a dry-stacked wall climbs)."""
    line = np.asarray(line, float)
    tops = np.broadcast_to(np.asarray(tops, float), (len(line),))
    for k in range(len(line) - 1):
        a, b = line[k], line[k + 1]
        L = np.linalg.norm(b - a)
        n = max(1, int(round(L / piece)))
        for i in range(n):
            t0, t1 = i / n, (i + 1) / n
            p, q = a + (b - a) * t0, a + (b - a) * t1
            z0, z1 = tops[k] + (tops[k + 1] - tops[k]) * t0, tops[k] + (tops[k + 1] - tops[k]) * t1
            if level:
                z0 = z1 = max(z0, z1)
            ss = np.linspace(0, 1, 5)
            pts = p + (q - p) * ss[:, None]
            s = np.array([-(q - p)[1], (q - p)[0]]) / max(np.linalg.norm(q - p), 1e-9)
            zb = min(float(plan.ground_z(*(pts + s * e).T).min()) for e in (-w / 2 - 0.1, w / 2 + 0.1)) - 0.15
            _hexa(geo, mat, p, q, w, zb, z0, z1, cap=cap, ext=w / 2 if (i in (0, n - 1)) else 0.0)


def _above(line, w, dz, reach=0.9):
    """Per-vertex wall tops: the higher ground beside the line (sampled `reach` m off both sides) + dz."""
    line = np.asarray(line, float)
    tops = []
    for k, p in enumerate(line):
        d = line[min(k + 1, len(line) - 1)] - line[max(k - 1, 0)]
        s = np.array([-d[1], d[0]]) / max(np.linalg.norm(d), 1e-9)
        tops.append(max(plan.ground_z(*(p + s * reach)), plan.ground_z(*(p - s * reach))) + dz)
    return np.array(tops)


def _dense(line_px, step_px=60):
    """Subdivide a pixel polyline (so sloping walls can follow the ground)."""
    line_px = np.asarray(line_px, float)
    out = [line_px[0]]
    for a, b in zip(line_px[:-1], line_px[1:]):
        n = max(1, int(np.ceil(np.linalg.norm(b - a) / step_px)))
        out += [a + (b - a) * (i + 1) / n for i in range(n)]
    return np.array(out)


# ---- the terrain ----------------------------------------------------------------------------------------------
def _terrain():
    import shapely
    from shapely.geometry import Polygon, box
    from shapely.ops import unary_union
    geo = Geo()
    ext = box(*plan.EXTENT)
    holes = unary_union([Polygon(_ring(h)).buffer(0) for h in HOLES])
    # the driveway's hidden end: carried on to the street band at the lot's south edge (a guess)
    drv = Polygon(_ring('site.driveway')).buffer(0)
    dr = np.asarray(drv.exterior.coords)
    south = dr[dr[:, 1] < dr[:, 1].min() + 1.5]
    apron = Polygon([(south[:, 0].min(), south[:, 1].max()), (south[:, 0].max(), south[:, 1].max()),
                     (south[:, 0].max() + 0.5, plan.EXTENT[1]), (south[:, 0].min() - 2.0, plan.EXTENT[1])])
    taken = holes
    polys = [(mat, Polygon(_ring(eid)).buffer(0)) for eid, mat in SURFACES]
    polys.insert(4, ('paver_drive', apron))
    for mat, pg in polys:
        pg = pg.intersection(ext).difference(taken)
        _surface(geo, mat, pg)
        taken = unary_union([taken, pg])
    # the rest: mulch inside the aerial's footprint, far ground outside it
    img = Polygon(plan.aerial_ring([(0, 0), (2500, 0), (2500, 1875), (0, 1875)], 0.0)).buffer(0)
    rest = ext.difference(taken)
    _surface(geo, 'mulch', rest.intersection(img))
    _surface(geo, 'ground_far', rest.difference(img))
    return geo, apron


def _far(geo, apron):
    """Far ground to the horizon + a street band along the south edge."""
    x0, y0, x1, y1 = plan.EXTENT
    zm = -0.4
    edge = []
    xs, ys = np.arange(x0, x1 + 1e-6, STEP), np.arange(y0, y1 + 1e-6, STEP)
    edge += [(x, y0) for x in xs] + [(x1, y) for y in ys[1:]] + [(x, y1) for x in xs[::-1][1:]] + \
            [(x0, y) for y in ys[::-1][1:]]
    edge = np.array(edge)
    c = np.array([(x0 + x1) / 2, (y0 + y1) / 2])
    R1 = 40.0
    half = np.array([(x1 - x0) / 2 + R1, (y1 - y0) / 2 + R1])
    v = edge - c
    k = np.min(half / np.maximum(np.abs(v), 1e-9), axis=1)
    outer = c + v * k[:, None]
    ze = plan.ground_z(edge[:, 0], edge[:, 1])
    T = []
    n = len(edge) - 1                                   # the ring is closed (last = first)
    for i in range(n):
        a, b = np.r_[edge[i], ze[i]], np.r_[edge[i + 1], ze[i + 1]]
        A, B = np.r_[outer[i], zm], np.r_[outer[i + 1], zm]
        T += [[a, b, B], [a, B, A]]
    _tris(geo, 'ground_far', np.array(T))
    # flat to the horizon: a frame of 4 quads round the 40 m ring
    X0, Y0, X1, Y1 = c[0] - half[0], c[1] - half[1], c[0] + half[0], c[1] + half[1]
    F = 900.0
    for lo, hi in (((X0 - F, Y0 - F), (X1 + F, Y0)), ((X0 - F, Y1), (X1 + F, Y1 + F)), ((X0 - F, Y0), (X0, Y1)),
                   ((X1, Y0), (X1 + F, Y1))):
        geo.poly('ground_far', [(lo[0], lo[1], zm), (hi[0], lo[1], zm), (hi[0], hi[1], zm), (lo[0], hi[1], zm)],
                 uv_u=(1, 0, 0), uv_o=(0, 0, zm))
    # street band (asphalt) just beyond the south tree screen, 6.5 m wide, a few cm above the far ground
    ys0, ys1 = y0 - 8.5, y0 - 2.0
    zs = zm + 0.04
    geo.poly('asphalt', [(X0 - 200, ys0, zs), (X1 + 200, ys0, zs), (X1 + 200, ys1, zs), (X0 - 200, ys1, zs)],
             uv_u=(1, 0, 0), uv_o=(0, 0, zs))
    ax = np.asarray(apron.exterior.coords)
    ax0, ax1 = ax[ax[:, 1] < y0 + 0.01][:, 0].min(), ax[ax[:, 1] < y0 + 0.01][:, 0].max()
    za, zb = plan.ground_z(ax0, y0), plan.ground_z(ax1, y0)
    geo.poly('paver_drive', [(ax0 - 1.0, ys1, zs + 0.01), (ax1 + 1.0, ys1, zs + 0.01), (ax1, y0, zb + 0.02),
                             (ax0, y0, za + 0.02)], uv_u=(1, 0, 0))


# ---- steps ----------------------------------------------------------------------------------------------------
def _flight(geo, lo_a, lo_b, hi_a, hi_b, z_lo, z_hi, n_treads=None, landing=0.0, cheeks=(True, True),
            rail=None, mat='bluestone'):
    """A straight flight between the bottom edge (lo_a, lo_b) at z_lo and the top edge (hi_a, hi_b) at z_hi (plan
    points; a / b are the two sides).  n risers = n_treads + 1; `landing`: length of the level top part (m)."""
    lo_a, lo_b, hi_a, hi_b = (np.asarray(p, float) for p in (lo_a, lo_b, hi_a, hi_b))
    o = (lo_a + lo_b) / 2
    top = (hi_a + hi_b) / 2
    d = top - o
    L = np.linalg.norm(d)
    d /= L
    s = np.array([-d[1], d[0]])
    wa, wb = (lo_a - o) @ s, (lo_b - o) @ s
    w0, w1 = min(wa, wb), max(wa, wb)
    H = z_hi - z_lo
    nr = (n_treads + 1) if n_treads else max(2, int(round(H / RISE)))
    rise = H / nr
    run = (L - landing) / (nr - 1) if nr > 1 else L
    ex, ey, ez = np.r_[d, 0], np.r_[s, 0], np.array([0, 0, 1.0])
    org = np.r_[o, z_lo]
    zb = -0.35
    for i in range(nr):
        x0 = i * run
        x1 = L if i == nr - 1 else (i + 1) * run
        geo.obox(mat, org, ex, ey, ez, (x0, w0, zb if i == 0 else (i - 1) * rise), (x1, w1, (i + 1) * rise),
                 faces='xXyYZ')
    ct = 0.32
    for on, wy, sg in ((cheeks[0], w0, -1), (cheeks[1], w1, 1)):
        if not on:
            continue
        # a stone cheek wall: sloping top 0.25 above the nosings, level along the landing
        y0_, y1_ = (wy - ct, wy) if sg < 0 else (wy, wy + ct)
        xs = [(-0.3, 0.25), (L - landing, H + 0.25), (L + 0.15, H + 0.25)] if landing > 0.05 else \
             [(-0.3, 0.25), (L + 0.15, H + 0.25)]
        for (xa, za), (xb, zc) in zip(xs[:-1], xs[1:]):
            pa, pb = o + d * xa + s * (y0_ + y1_) / 2, o + d * xb + s * (y0_ + y1_) / 2
            _hexa(geo, 'fieldstone', pa, pb, ct, z_lo - 0.4, z_lo + za, z_lo + zc, cap='wall_cap')
    if rail:
        side = (w1 - 0.10) if ((wa > wb) == (rail == 'a')) else (w0 + 0.10)
        hr = 0.90
        pts = [(0.15, rise + hr), (L - landing, H + hr)] + ([(L - 0.1, H + hr)] if landing > 0.3 else [])
        P = [org + ex * x + ey * side + ez * z for x, z in pts]
        for a, b in zip(P[:-1], P[1:]):
            geo.cylinder('handrail_black', a, b, 0.022, n=8)
        npost = 4
        for t in np.linspace(0, 1, npost):
            x = 0.15 + (L - landing - 0.15) * t
            z = rise + (H - rise) * t
            foot = org + ex * x + ey * side + ez * (z - rise * 0.5 - 0.1)
            geo.cylinder('handrail_black', foot, org + ex * x + ey * side + ez * (z + hr), 0.018, n=6, cap=False)
        if landing > 0.3:
            x = L - 0.1
            geo.cylinder('handrail_black', org + ex * x + ey * side + ez * H, org + ex * x + ey * side + ez * (H + hr),
                         0.018, n=6, cap=False)


def _steps():
    geo = Geo()
    # patio stairs: 9 treads between 10 riser lines (aerial x), a landing, rising east; handrail on the north side
    e = plan.site('site.stairs_patio_path')
    rx = e['attrs']['risers_x']
    ys = sorted({p[1] for p in e['poly']})
    yn, ysd = 667.0, 720.0
    z_lo = plan.REGIONS['site.patio_pool']
    x_top = max(p[0] for p in e['poly'])
    top_mid = _px([(x_top + 6, (yn + ysd) / 2)])[0]
    z_hi = float(plan.ground_z(*top_mid))
    lo = _px([(rx[0], yn), (rx[0], ysd)], z_lo)
    hi = _px([(x_top, yn), (x_top, ysd)], z_hi)
    land = float(np.linalg.norm(_px([(rx[-1], 690)], z_hi)[0] - _px([(x_top, 690)], z_hi)[0]))
    _flight(geo, lo[0], lo[1], hi[0], hi[1], z_lo, z_hi, n_treads=len(rx) - 1, landing=land, rail='a')
    # path steps down to the synthetic lawn (descending south = +v in the aerial)
    e = plan.site('site.stairs_path_lawn')
    P = np.asarray(e['poly'], float)
    x0, x1, y0, y1 = P[:, 0].min(), P[:, 0].max(), P[:, 1].min(), P[:, 1].max()
    z_lo = plan.REGIONS['site.lawn_synthetic']
    z_hi = float(plan.ground_z(*_px([((x0 + x1) / 2, y0 - 8)])[0]))
    lo = _px([(x0 + 2, y1), (x1, y1)], z_lo)
    hi = _px([(x0 + 2, y0), (x1, y0)], z_hi)
    _flight(geo, lo[0], lo[1], hi[0], hi[1], z_lo, z_hi, cheeks=(True, True))
    info = dict(patio_stairs=dict(z_lo=plan.REGIONS['site.patio_pool'], z_hi=round(float(plan.ground_z(*top_mid)), 2)),
                lawn_steps=dict(z_lo=z_lo, z_hi=round(z_hi, 2)))
    return geo, info


# ---- walls ----------------------------------------------------------------------------------------------------
def _walls():
    geo = Geo()
    planter = plan.REGIONS.get('site.planter_terrace', 0.8)
    for eid, (w, top) in WALLS.items():
        px = _dense(plan.site(eid)['polyline'])
        if top is None:
            top = planter + 0.12
        if isinstance(top, tuple):
            line = _px(px)
            for _ in range(2):                           # the surveyed line is the cap: place it at its height
                tops = _above(line, w, top[1])
                line = _px(px, tops)
            if eid == 'site.wall_lawn_east':             # at least a kerb above the turf
                tops = np.maximum(tops, plan.REGIONS['site.lawn_synthetic'] + 0.35)
        else:
            line, tops = _px(px, top), top
        _wall(geo, line, w, tops)
    # raised planter by the lawn steps: walls on its south and west sides (its north / east run into the hedge
    # strip and the steps' cheek), tops level with the lawn wall
    soil = plan.REGIONS['site.planter_lawn']
    top = soil + 0.12
    P = np.asarray(plan.site('site.planter_lawn')['poly'], float)
    x0, x1, y0, y1 = P[:, 0].min(), P[:, 0].max(), P[:, 1].min(), P[:, 1].max()
    ring = _px([(x1, y1), (x0, y1), (x0, y0), (x1, y0)], top)
    _wall(geo, ring, 0.36, top)
    return geo


# ---- small things on the ground -------------------------------------------------------------------------------
def _slab(geo, mat, c, d, lx, ly, h, sink=0.03):
    """A slab centred on plan point c, long axis along d, standing h above the ground."""
    c, d = np.asarray(c, float), np.asarray(d, float)
    d = d / np.linalg.norm(d)
    z = float(plan.ground_z(*c))
    geo.obox(mat, (c[0], c[1], z), (d[0], d[1], 0), (-d[1], d[0], 0), (0, 0, 1), (-lx / 2, -ly / 2, -sink),
             (lx / 2, ly / 2, h), faces='xXyYZ')


def _details():
    geo = Geo()
    # stepping stones in the side-yard mulch (11, ~0.5 x 0.7 m), across the run
    line = _px(plan.site('site.stepping_stones_side')['polyline'])
    for k, c in enumerate(line):
        d = line[min(k + 1, len(line) - 1)] - line[max(k - 1, 0)]
        _slab(geo, 'bluestone', c, (-d[1], d[0]), 0.68, 0.46, 0.035)
    # the grey slab against the SE wing (role unknown: a low platform)
    x0, y0, x1, y1 = plan.site('site.side_slab')['bbox']
    a, b = _px([(x0, (y0 + y1) / 2), (x1, (y0 + y1) / 2)])
    wd = np.linalg.norm(_px([(x0, y0)])[0] - _px([(x0, y1)])[0])
    _slab(geo, 'concrete', (a + b) / 2, b - a, np.linalg.norm(b - a), wd, 0.10)
    # timber step against the SE wing's east wall
    x0, y0, x1, y1 = plan.site('site.wood_step_se')['bbox']
    a, b = _px([((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1)])
    wd = np.linalg.norm(_px([(x0, y0)])[0] - _px([(x1, y0)])[0])
    _slab(geo, 'timber', (a + b) / 2, b - a, np.linalg.norm(b - a), wd, 0.17)
    # white header board on the synthetic lawn's south edge
    line = _px(plan.site('site.edging_lawn_south')['polyline'])
    _slab(geo, 'trim_white', line.mean(0), line[1] - line[0], np.linalg.norm(line[1] - line[0]), 0.06, 0.14)
    # dark edging along the gravel path
    ring = plan.ground_ring(plan.site('site.path_gravel')['poly'])
    for a, b in zip(ring, np.roll(ring, -1, 0)):
        L = np.linalg.norm(b - a)
        if L > 0.5:
            za, zb = plan.ground_z(*a), plan.ground_z(*b)
            geo.prism('edging_dark', [(-0.02, -0.03), (0.02, -0.03), (0.02, 0.05), (-0.02, 0.05)],
                      (a[0], a[1], za), (b[0], b[1], zb), cap=False)
    # grates and lids (flush, 1.5 cm proud so they read)
    x0, y0, x1, y1 = plan.site('site.grate_lawn')['bbox']
    c = _px([((x0 + x1) / 2, (y0 + y1) / 2)])[0]
    sz = np.linalg.norm(_px([(x0, y0)])[0] - _px([(x1, y0)])[0])
    _slab(geo, 'grate_metal', c, (1, 0), sz, sz, 0.015)
    x0, y0, x1, y1 = plan.site('site.lid_patio')['attrs']['grate_bbox']
    c = _px([((x0 + x1) / 2, (y0 + y1) / 2)])[0]
    _slab(geo, 'grate_metal', c, (1, 1), 0.45, 0.30, 0.012)
    e = plan.site('site.lid_green')
    c = _px([e['point']])[0]
    z = float(plan.ground_z(*c))
    geo.cylinder('lid_green', (c[0], c[1], z - 0.02), (c[0], c[1], z + 0.03), 0.45, n=16)
    x0, y0, x1, y1 = plan.site('site.box_nw')['attrs']['bbox_px']
    c = _px([((x0 + x1) / 2, (y0 + y1) / 2)])[0]
    _slab(geo, 'concrete', c, (1, 0), 0.7, 0.65, 0.12)
    c = _px([plan.site('site.box_patio_bed')['point']])[0]
    _slab(geo, 'lid_green', c, (1, 0), 0.45, 0.32, 0.06)
    return geo


def build():
    terrain, apron = _terrain()
    far = Geo()
    _far(far, apron)
    steps, info = _steps()
    return [
        Part('ground_terrain', terrain, group='site', extras=dict(grid=STEP)),
        Part('ground_far', far, group='backdrop'),
        Part('ground_steps', steps, group='site', extras=info),
        Part('ground_walls', _walls(), group='site'),
        Part('ground_details', _details(), group='site'),
    ]


if __name__ == '__main__':
    for p in build():
        print('%-16s %7d' % (p.name, p.ntri), {m.mat: m.ntri for m in p.geo.meshes()})
