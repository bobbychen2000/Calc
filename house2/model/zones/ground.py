"""Zone 'ground' of house 2: the terrain and every ground surface.

The lot is PARTITIONED in plan: every surveyed area of survey/site.json (aerial pixels -> world at its own level,
model/plan.py) takes its material, the first one in SURFACES winning where two overlap; what is left inside the
aerial's footprint is mulch, beyond it 'ground_far'.  Every piece is cut by one 1 m grid and its vertices are set on
plan.ground_z, so neighbouring materials share their edges (no cracks, nothing z-fights) and everything the other
zones stand on plan.ground_z sits on this mesh.  Holes: the pool (the coping's outer outline: water, coping and spa
belong to zone 'pool') and the two flights of steps, which are built as solids here.

On the terrain: retaining walls (dry-stacked fieldstone with light caps; tops from the levels either side), the patio
stairs (9 treads, black handrail on the north side) and the path steps down to the synthetic lawn, the raised
planter's walls, stepping stones, the side slab, the timber step, edging, grates / lids, and the far ground with the
street ~50 m south of the lot and the lane that leads to it (STREET: read from p28).
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
# surfaces that are not survey elements: (material, aerial pixels, level), placed before the SURFACES entry `before`
EXTRA_SURF = [
    # the turf runs to the foot of the lawn walls (p18; the surveyed polygon stops ~0.4 m short of them)
    ('turf_synthetic', [(1657, 1205), (2345, 1200), (2345, 1614), (2320, 1614), (2320, 1226), (1657, 1232)], -0.70,
     'site.lawn_synthetic'),
]
GROW = 0.12         # every area is grown by this much before the partition: closes the slivers between neighbours

# retaining walls: id -> (width m, top: number = level, or ('above', dz) = the higher ground beside it + dz)
WALLS = {
    'site.wall_north': (0.55, ('above', 0.10)),
    'site.wall_terrace_lower': (0.36, 0.58),
    'site.wall_terrace_upper': (0.40, 1.50),
    'site.wall_fireplace_east': (0.36, 0.60),
    'site.wall_planter_chevron': (0.36, 0.62),          # frame 133400: the cap ~0.6 above the deck
    'site.wall_planter_mid': (0.36, ('above', 0.10)),
    'site.wall_lawn_north': (0.40, 0.50),               # cap 0.45-0.5 (aerial ray into frame 144000), ~1.2 above the turf
    'site.wall_lawn_east': (0.85, ('above', 0.10)),
}
# walls that are not survey elements (aerial pixels): the raised planter west of the lawn steps (its south, west and
# east walls level with the lawn wall, its north wall holds the hedge strip) and the return wall along the east side
# of the lawn steps / the path's south end, which holds the orchard bank (cap seen in the aerial at u 1866-1880)
PLANTER = (1657, 1142, 1800, 1214)                      # = site.planter_lawn's box
EXTRA_WALLS = [
    ('planter_lawn_swe', [(1800, 1142), (1800, 1214), (1657, 1214), (1657, 1142)], 0.36, 0.50),
    ('planter_lawn_n', [(1657, 1142), (1800, 1142)], 0.36, ('above', 0.08)),
    ('lawn_steps_return', [(1873, 1105), (1873, 1205)], 0.36, 0.55),      # level with the lawn wall (frame 144000)
]
# The street.  It is NOT along the lot's south edge: directly behind the south tree screen stands the tile-roofed
# neighbour (its outbuilding's roof is the aerial's bottom-left "shake roof", x -35..-23, y -35..-45; the house about
# x -20..16, y -41..-67), and the high oblique photo p28 shows the public street beyond that house: asphalt with gate
# pillars and a parked car, its near edge ~50 m south of the lot (p28 rays on z = -1: (1, -105) .. (-29, -95); +-6 m
# for +-2 m of unknown ground height).  The driveway leaves the aerial at its bottom-left heading south (the gate is
# under the trees), so it must reach that street by a lane along the neighbour's west side, hidden by a row of tall
# trees in p28: modelled as a straight lane due south from the driveway's hidden end.  line: two points of the street's
# centre line; w, lane_w: widths; pavers: how far the driveway's pavers run beyond the lot edge (to the gate line).
STREET = dict(line=((0.9, -102.1), (-34.7, -89.9)), w=6.5, lane_w=4.5, pavers=3.0, reach=260.0)
LAWN_STEPS = dict(u=(1803, 1866), v_top=1154, v_bottom=1212, z_top=0.50, treads=6)   # 7 risers (frame 144000, p18)

# level profiles along a centre line (aerial pixels, level at each vertex): no cross-fall, the level of the nearest
# point of the line.  The gravel path: level beside the play area, up to the garden's level at its gate, down to the
# top of the lawn steps at its south end.  The driveway: the motor court level, then the fall to the gate.
PROFILES = {
    'site.path_gravel': ([(1975, 315), (1880, 318), (1812, 365), (1797, 500), (1796, 880), (1822, 968), (1850, 1045),
                          (1841, 1150)], [2.55, 2.35, 2.00, 1.80, 1.80, 1.37, 0.99, 0.50]),
    'site.driveway': ([(150, 300), (150, 1000), (150, 1750), (150, 1875)], [-0.30, -0.30, -0.95, -1.05]),
}
# level pads: a surveyed area whose level is carried `pad` m beyond its outline (the vegetable garden: its fence stands
# on the outline, so the fence line and a margin outside it are on the garden's level), and whose surrounding
# tree-belt ground -- a guessed plane, ~1 m too low beside the measured garden -- is released within `relax` m (also
# round `also`, aerial-pixel boxes of other areas: the path's bend at the gate) and becomes a bank falling away from it
PADS = {
    'site.garden_enclosure': dict(pad=0.40, relax=5.0, also=[('site.path_gravel', (1770, 280, 1990, 420))]),
}
KERB = dict(w=0.10, up=0.08, down=0.25)     # the timber retaining edge round a pad (not across a path): top above
                                            # the pad, foot `down` under the lowest ground within 0.6 m outside it
WALL_R = 1.1        # each side of a wall line keeps its own level this far from the line (the level break)
WALL_D = 0.45       # terrain vertices closer than this to a wall line read the ground this far out on their side


# ---- the refined terrain grid -----------------------------------------------------------------------------------
# plan.ground_z is a membrane between the surveyed areas: across a retaining wall it is a ramp that starts on the
# lower area.  refine_dtm() turns it into the ground this zone meshes: (1) PROFILES, (2) a level BREAK on every wall
# line (the ground keeps its own side's level right up to the wall), (3) the membrane solved again around them.
# Everything in this file stands on gz().  plan._dtm() may call refine_dtm(xs, ys, Z) itself (then plan.ground_z is
# the same ground for every zone: set plan._DTM['refined'] = True); it only uses plan.aerial_xy, never plan.ground_z.
_G = {}


def _bil(g, x, y):
    xs, ys, Z = g
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    st = xs[1] - xs[0]
    fx = np.clip((x - xs[0]) / st, 0, len(xs) - 1.001)
    fy = np.clip((y - ys[0]) / st, 0, len(ys) - 1.001)
    i, j = fy.astype(int), fx.astype(int)
    ty, tx = fy - i, fx - j
    return (Z[i, j] * (1 - tx) * (1 - ty) + Z[i, j + 1] * tx * (1 - ty) + Z[i + 1, j] * (1 - tx) * ty
            + Z[i + 1, j + 1] * tx * ty)


def _on(pts_px, zf, iters=2):
    """Aerial pixels -> world xy where their rays meet the ground zf."""
    pts = np.atleast_2d(np.asarray(pts_px, float))
    z = np.zeros(len(pts))
    for _ in range(iters):
        xy = np.atleast_2d(plan.aerial_xy(pts, z))
        z = np.atleast_1d(zf(xy[:, 0], xy[:, 1]))
    return np.atleast_2d(plan.aerial_xy(pts, z))


def _at(pts_px, z):
    pts = np.atleast_2d(np.asarray(pts_px, float))
    return np.atleast_2d(plan.aerial_xy(pts, np.broadcast_to(np.asarray(z, float), (len(pts),))))


def _wall_specs(zf):
    """Every wall as a world polyline (the surveyed line is the cap: placed at the cap's height)."""
    out = []
    items = [(eid, plan.site(eid)['polyline'], w, top) for eid, (w, top) in WALLS.items()] + EXTRA_WALLS
    for name, px, w, top in items:
        px = _dense(px)
        if isinstance(top, tuple):
            line = _on(px, zf)
            for _ in range(2):
                tops = _above(line, w, top[1], zf=zf)
                line = _at(px, tops)
        else:
            line = _at(px, top)
        out.append(dict(name=name, line=line, w=w, top=top))
    return out


def _profile(c, zs, x, y):
    """Level of the nearest point of the polyline c (levels zs at its vertices)."""
    P = np.stack([x, y], -1)
    best = np.full(len(P), np.inf)
    out = np.zeros(len(P))
    for a, b, za, zb in zip(c[:-1], c[1:], zs[:-1], zs[1:]):
        ab = b - a
        t = np.clip(((P - a) @ ab) / (ab @ ab), 0, 1)
        d2 = ((P - (a + t[:, None] * ab)) ** 2).sum(1)
        m = d2 < best
        best[m] = d2[m]
        out[m] = (za + (zb - za) * t)[m]
    return out


def _membrane(Z, fixed):
    """Laplace membrane over the free cells (natural boundary at the grid's border)."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.linalg import spsolve
    H, W = Z.shape
    free = ~fixed
    n = int(free.sum())
    if not n:
        return Z
    idx = -np.ones(Z.shape, int)
    idx[free] = np.arange(n)
    I, J = np.nonzero(free)
    k = idx[I, J]
    diag = np.zeros(n)
    b = np.zeros(n)
    rows, cols = [], []
    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        p, q = I + di, J + dj
        ok = (p >= 0) & (p < H) & (q >= 0) & (q < W)
        kk, p, q = k[ok], p[ok], q[ok]
        diag[kk] += 1
        pf = fixed[p, q]
        b[kk[pf]] += Z[p[pf], q[pf]]
        rows.append(kk[~pf])
        cols.append(idx[p[~pf], q[~pf]])
    rows, cols = np.concatenate(rows), np.concatenate(cols)
    A = coo_matrix((np.r_[diag, -np.ones(len(rows))], (np.r_[np.arange(n), rows], np.r_[np.arange(n), cols])),
                   shape=(n, n)).tocsc()
    Z = Z.copy()
    Z[free] = spsolve(A, b)
    return Z


def refine_dtm(xs, ys, Zb):
    """The terrain grid of plan._dtm() -> the same grid with profiles and wall breaks (see above)."""
    import shapely
    from shapely import contains_xy
    from shapely.geometry import LineString, Polygon
    g0 = (xs, ys, Zb)
    specs = _wall_specs(lambda x, y: _bil(g0, x, y))
    _G['walls'] = specs
    X, Y = np.meshgrid(xs, ys)
    st = xs[1] - xs[0]
    Z = Zb.copy()
    fixed = np.zeros(Z.shape, bool)
    for eid in plan.REGIONS:
        if eid in plan.SITE and 'poly' in plan.SITE[eid]:
            fixed |= contains_xy(Polygon(plan.aerial_ring(plan.SITE[eid]['poly'], plan.REGIONS[eid])).buffer(0), X, Y)
    for eid, (cl, zs) in PROFILES.items():
        zs = np.asarray(zs, float)
        m = contains_xy(Polygon(plan.aerial_ring(plan.SITE[eid]['poly'], float(np.median(zs)))).buffer(0), X, Y)
        Z[m] = _profile(_at(cl, zs), zs, X[m], Y[m])
        fixed |= m
    if PADS:
        belt = np.zeros(Z.shape, bool)
        other = fixed & False
        for eid in plan.REGIONS:
            if eid in plan.SITE and 'poly' in plan.SITE[eid]:
                m = contains_xy(Polygon(plan.aerial_ring(plan.SITE[eid]['poly'], plan.REGIONS[eid])).buffer(0), X, Y)
                if eid.startswith('site.trees_'):
                    belt |= m
                else:
                    other |= m
        for eid in PROFILES:
            other |= contains_xy(Polygon(plan.aerial_ring(plan.SITE[eid]['poly'],
                                                          float(np.median(PROFILES[eid][1])))).buffer(0), X, Y)
        for eid, pd in PADS.items():
            pg = pad_polygon(eid, more=1.5 * st)
            m = contains_xy(pg, X, Y) & ~contains_xy(_pad_keep(eid), X, Y)
            Z[m] = plan.REGIONS[eid]
            fixed |= m
            other |= m
            src = [pg]
            for oid, (u0, v0, u1, v1) in pd.get('also', ()):
                lv = plan.REGIONS[eid]
                src.append(Polygon(plan.aerial_ring(plan.SITE[oid]['poly'], lv)).buffer(0).intersection(
                    Polygon(plan.aerial_ring([(u0, v0), (u1, v0), (u1, v1), (u0, v1)], lv))))
            src = shapely.union_all(src)
            x0, y0, x1, y1 = src.bounds
            r = pd['relax']
            mb = belt & ~other & (X > x0 - r) & (X < x1 + r) & (Y > y0 - r) & (Y < y1 + r)
            near = np.zeros(Z.shape, bool)
            near[mb] = shapely.distance(src, shapely.points(X[mb], Y[mb])) < r
            fixed &= ~near
    # wall breaks: side of the nearest wall line for every cell near one
    st = xs[1] - xs[0]
    dmin = np.full(Z.shape, np.inf)
    side = np.zeros(Z.shape, np.int8)
    for s in specs:
        L = LineString(s['line'])
        x0, y0, x1, y1 = L.bounds
        mb = (X > x0 - 2.5) & (X < x1 + 2.5) & (Y > y0 - 2.5) & (Y < y1 + 2.5)
        pts = shapely.points(X[mb], Y[mb])
        d = shapely.distance(L, pts)
        t = shapely.line_locate_point(L, pts)
        qa = shapely.get_coordinates(shapely.line_interpolate_point(L, np.maximum(t - 0.05, 0)))
        qb = shapely.get_coordinates(shapely.line_interpolate_point(L, np.minimum(t + 0.05, L.length)))
        q = shapely.get_coordinates(shapely.line_interpolate_point(L, t))
        tg = qb - qa
        sg = np.sign(tg[:, 0] * (Y[mb] - q[:, 1]) - tg[:, 1] * (X[mb] - q[:, 0])).astype(np.int8)
        de = d + 0.6 * ((t < 1e-6) | (t > L.length - 1e-6))      # beyond a wall's end: another wall's flank wins
        upd = de < dmin[mb]
        dm, sd = dmin[mb], side[mb]
        dm[upd], sd[upd] = de[upd], sg[upd]
        dmin[mb], side[mb] = dm, sd
    side[dmin > WALL_R + 2 * st] = 0
    todo = (dmin < WALL_R) & ~fixed
    filled = fixed & ~todo
    fixed2 = fixed.copy()
    H, W = Z.shape
    for _ in range(80):
        if not todo.any():
            break
        acc = np.zeros(Z.shape)
        cnt = np.zeros(Z.shape)
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            src = np.zeros(Z.shape, bool)
            val = np.zeros(Z.shape)
            sds = np.zeros(Z.shape, np.int8)
            a = (slice(max(di, 0), H + min(di, 0)), slice(max(dj, 0), W + min(dj, 0)))       # neighbour
            c = (slice(max(-di, 0), H + min(-di, 0)), slice(max(-dj, 0), W + min(-dj, 0)))   # cell
            src[c], val[c], sds[c] = filled[a], Z[a], side[a]
            ok = todo & src & ((sds == side) | (sds == 0) | (side == 0))
            acc[ok] += val[ok]
            cnt[ok] += 1
        new = cnt > 0
        if not new.any():
            break
        Z[new] = acc[new] / cnt[new]
        filled |= new
        fixed2 |= new
        todo &= ~new
    return _membrane(Z, fixed2)


def pad_polygon(eid, more=0.0):
    """A PADS area with its level margin (plan polygon).  The terrain grid is levelled `more` further out than the
    meshed pad, so the pad's outline vertices read the level and not half-way down to the neighbour."""
    from shapely.geometry import Polygon
    return Polygon(plan.aerial_ring(plan.SITE[eid]['poly'], plan.REGIONS[eid])).buffer(PADS[eid]['pad'] + more,
                                                                                       join_style='mitre')


def _pad_keep(eid):
    """Where a pad's margin gives way: the profiled paths that arrive at it (the path keeps its own profile)."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    return unary_union([Polygon(plan.aerial_ring(plan.SITE[k]['poly'], plan.REGIONS[eid])).buffer(0)
                        for k in PROFILES])


def _grid():
    if 'g' not in _G:
        xs, ys, Zb = plan._dtm()
        if plan._DTM.get('refined'):                     # plan applies refine_dtm itself
            if 'walls' not in _G:
                _G['walls'] = _wall_specs(plan.ground_z)
            _G['g'] = (xs, ys, Zb)
        else:
            _G['g'] = (xs, ys, refine_dtm(xs, ys, Zb))
        from shapely.geometry import LineString, MultiLineString
        _G['wl'] = MultiLineString([LineString(s['line']) for s in _G['walls']])
    return _G['g']


def gz(x, y):
    """The ground of this zone's meshes: the refined grid; next to a wall line, the level of that side."""
    import shapely
    g = _grid()
    x = np.array(x, float)
    y = np.array(y, float)
    shp = x.shape
    x, y = x.ravel().copy(), y.ravel().copy()
    pts = shapely.points(x, y)
    d = shapely.distance(_G['wl'], pts)
    near = (d < WALL_D) & (d > 1e-6)
    if near.any():
        c = shapely.get_coordinates(shapely.shortest_line(_G['wl'], pts[near])).reshape(-1, 2, 2)
        v = c[:, 1] - c[:, 0]
        p = c[:, 0] + v / np.linalg.norm(v, axis=1)[:, None] * WALL_D
        x[near], y[near] = p[:, 0], p[:, 1]
    z = _bil(g, x, y).reshape(shp)
    return z if z.ndim else float(z)


def _wall_pieces(line, piece=3.0):
    """The straight pieces a wall is built of: (p, q, k, t0, t1, first-or-last of its segment)."""
    line = np.asarray(line, float)
    for k in range(len(line) - 1):
        a, b = line[k], line[k + 1]
        n = max(1, int(round(np.linalg.norm(b - a) / piece)))
        for i in range(n):
            t0, t1 = i / n, (i + 1) / n
            yield a + (b - a) * t0, a + (b - a) * t1, k, t0, t1, i in (0, n - 1)


def wall_footprints():
    """The plan footprint of the wall BODIES exactly as _wall() builds them (the rectangles of its pieces, each
    segment's end pieces run on by half a width): the terrain is cut by this, so it meets the walls' faces with no
    gap (a bevelled buffer of the wall line left slivers of open ground at the bends)."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    _grid()
    R = []
    for sp in _G['walls']:
        w = sp['w']
        for p, q, _, _, _, end in _wall_pieces(sp['line']):
            d = q - p
            L = np.linalg.norm(d)
            if L < 1e-6:
                continue
            d = d / L
            s = np.array([-d[1], d[0]]) * w / 2
            e = d * (w / 2 if end else 0.0)
            R.append(Polygon([p - e - s, q + e - s, q + e + s, p - e + s]))
    return unary_union(R)


# ---- helpers ------------------------------------------------------------------------------------------------
def _ring(eid):
    """A site polygon as a world ring at its level (REGIONS; sloping / unlisted areas: on the terrain)."""
    if eid in plan.REGIONS and eid not in plan.SLOPES and eid not in PROFILES:
        return plan.aerial_ring(plan.site(eid)['poly'], plan.REGIONS[eid])
    return _on(plan.site(eid)['poly'], gz)


def _px(pts, z=None):
    """Aerial pixels -> world xy; on the terrain, or at height(s) z."""
    if z is None:
        return _on(pts, gz)
    return _at(pts, z)


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
    zf = zf or gz
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
    for p, q, k, t0, t1, end in _wall_pieces(line, piece):
        if np.linalg.norm(q - p) < 1e-6:
            continue
        z0, z1 = tops[k] + (tops[k + 1] - tops[k]) * t0, tops[k] + (tops[k + 1] - tops[k]) * t1
        if level:
            z0 = z1 = max(z0, z1)
        ss = np.linspace(0, 1, 5)
        pts = p + (q - p) * ss[:, None]
        s = np.array([-(q - p)[1], (q - p)[0]]) / max(np.linalg.norm(q - p), 1e-9)
        if end:                                         # the end pieces run on by half a width
            dd = (q - p) / max(np.linalg.norm(q - p), 1e-9) * (w / 2 + 0.1)
            pts = np.vstack([p - dd, pts, q + dd])
        offs = (-w / 2 - 0.35, -w / 2 - 0.1, 0.0, w / 2 + 0.1, w / 2 + 0.35)
        zb = min(float(gz(*(pts + s * e).T).min()) for e in offs) - 0.15
        zh = max(float(gz(*(pts + s * e).T).max()) for e in offs[1:4]) + 0.06
        z0, z1 = max(z0, zh), max(z1, zh)               # a wall always closes the gap its footprint leaves
        _hexa(geo, mat, p, q, w, zb, z0, z1, cap=cap, ext=w / 2 if end else 0.0)


def _above(line, w, dz, reach=0.9, zf=None):
    """Per-vertex wall tops: the higher ground beside the line (sampled `reach` m off both sides) + dz."""
    line = np.asarray(line, float)
    zf = zf or gz
    tops = []
    for k, p in enumerate(line):
        d = line[min(k + 1, len(line) - 1)] - line[max(k - 1, 0)]
        s = np.array([-d[1], d[0]]) / max(np.linalg.norm(d), 1e-9)
        tops.append(max(float(zf(*(p + s * reach))), float(zf(*(p - s * reach)))) + dz)
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
    holes = unary_union([Polygon(_ring('site.pool_coping')).buffer(0)] + [Polygon(f['hole']) for f in _flights()]
                        + [wall_footprints()])
    # the driveway's hidden end: carried on to the lot's south edge (the lane beyond it: _far)
    drv = Polygon(_ring('site.driveway')).buffer(0)
    dr = np.asarray(drv.exterior.coords)
    south = dr[dr[:, 1] < dr[:, 1].min() + 1.5]
    apron = Polygon([(south[:, 0].min(), south[:, 1].max()), (south[:, 0].max(), south[:, 1].max()),
                     (south[:, 0].max() + 0.5, plan.EXTENT[1]), (south[:, 0].min() - 2.0, plan.EXTENT[1])])
    taken = holes
    polys = [(mat, Polygon(_ring(eid)).buffer(0).buffer(GROW, join_style='mitre')) for eid, mat in SURFACES]
    polys.insert(4, ('paver_drive', apron))
    for mat, px, lvl, before in EXTRA_SURF:
        k = [i for i, (eid, _) in enumerate(SURFACES) if eid == before][0] + 1       # + 1: the apron
        polys.insert(k, (mat, Polygon(_at(px, lvl)).buffer(0)))
    for eid in PADS:                                     # a pad's margin takes its area's material
        k = [i for i, (mat, pg) in enumerate(polys) if mat == dict(SURFACES)[eid]
             and pg.contains(pad_polygon(eid).buffer(-PADS[eid]['pad'] - 0.5))][0]
        polys.insert(k, (dict(SURFACES)[eid], pad_polygon(eid)))
    for mat, pg in polys:
        pg = pg.intersection(ext).difference(taken)
        _surface(geo, mat, pg)
        taken = unary_union([taken, pg])
    # under the house's roofs (walls, and the roofed open floors: covered patios, porches): flagstone, not mulch;
    # the surveyed beds inside the eave line are already taken (the outline is the eave: placed at eave height)
    pg = Polygon(_at(plan.site('site.house_eave_outline')['poly'], plan.EAVE_1)).buffer(0).difference(taken)
    _surface(geo, 'bluestone', pg)
    taken = unary_union([taken, pg])
    # the rest: mulch inside the aerial's footprint, far ground outside it
    img = Polygon(plan.aerial_ring([(0, 0), (2500, 0), (2500, 1875), (0, 1875)], 0.0)).buffer(0)
    rest = ext.difference(taken)
    _surface(geo, 'mulch', rest.intersection(img))
    _surface(geo, 'ground_far', rest.difference(img))
    return geo, apron


def _far(geo, apron):
    """Far ground to the horizon, the street and the lane to it."""
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
    ze = gz(edge[:, 0], edge[:, 1])
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
    # the street and the lane to the gate (see STREET)
    zs = zm + 0.04
    P0, P1 = np.array(STREET['line'][0], float), np.array(STREET['line'][1], float)
    u = (P1 - P0) / np.linalg.norm(P1 - P0)
    nrm = np.array([-u[1], u[0]]) * STREET['w'] / 2
    ax = np.asarray(apron.exterior.coords)
    ax0, ax1 = ax[ax[:, 1] < y0 + 0.01][:, 0].min(), ax[ax[:, 1] < y0 + 0.01][:, 0].max()
    xl = (ax0 + ax1) / 2                                  # the lane: due south from the driveway's hidden end
    J = P0 + u * (xl - P0[0]) / u[0]                      # where it meets the street's centre line
    A, B = J - u * STREET['reach'], J + u * STREET['reach']
    geo.poly('asphalt', [(*(A - nrm), zs), (*(B - nrm), zs), (*(B + nrm), zs), (*(A + nrm), zs)], uv_u=(u[0], u[1], 0),
             uv_o=(0, 0, zs))

    def far_z(x, y):                                      # the 40 m ring's surface (radial from the centre)
        v = np.array([x, y]) - c
        k_in = np.min(np.array([(x1 - x0) / 2, (y1 - y0) / 2]) / np.maximum(np.abs(v), 1e-9))
        k_out = np.min(half / np.maximum(np.abs(v), 1e-9))
        if k_out <= 1:
            return zm
        e = c + v * k_in
        t = (1 - k_in) / (k_out - k_in)
        return float(gz(e[0], e[1])) * (1 - t) + zm * t
    # pavers from the lot's edge to the gate line, then the asphalt lane (5 strips across, 2 m pieces, on the ring)
    hw = STREET['lane_w'] / 2
    yj = J[1] + STREET['w'] / 2 * 0.9
    ys_ = np.r_[np.arange(y0, yj, -2.0), yj]
    xs_ = np.linspace(-1, 1, 6)
    T = {'paver_drive': [], 'asphalt': []}
    for ya, yb in zip(ys_[:-1], ys_[1:]):
        ta, tb = min(1.0, (y0 - ya) / 6.0), min(1.0, (y0 - yb) / 6.0)       # the apron's width -> the lane's
        mat = 'paver_drive' if ya > y0 - STREET['pavers'] + 1e-6 else 'asphalt'
        for sa, sb in zip(xs_[:-1], xs_[1:]):
            def pt(sv, yv, t):
                xa = (ax0 + (xl - hw - ax0) * t) if sv < 0 else (ax1 + (xl + hw - ax1) * t)
                xv = xl + (xa - xl) * abs(sv)
                return (xv, yv, max(far_z(xv, yv), zs if yv < J[1] + STREET['w'] else -9) + 0.03)
            q = [pt(sa, ya, ta), pt(sb, ya, ta), pt(sb, yb, tb), pt(sa, yb, tb)]
            T[mat] += [[q[0], q[1], q[2]], [q[0], q[2], q[3]]]
    for mat, t in T.items():
        _tris(geo, mat, np.array(t))


# ---- steps ----------------------------------------------------------------------------------------------------
def _flight_frame(lo_a, lo_b, hi_a, hi_b, sides='mean', widen=(0.0, 0.0)):
    """The rectangle of a flight: origin o on the bottom edge, run direction d (square to the bottom edge), s across,
    the sides wa / wb (a / b) along s, run L.  The bottom and top edges are surveyed at different heights, and the
    aerial's parallax (0.2-0.4 m per metre of height out here) shifts them sideways against each other: the flight
    is NOT the skewed quad through the four points.  sides: 'mean' of the two edges' extents, or 'hi' / 'lo' (the
    edge whose height the side lines were read at); widen: extra width on the a / b side (into a flanking wall)."""
    lo_a, lo_b, hi_a, hi_b = (np.asarray(p, float) for p in (lo_a, lo_b, hi_a, hi_b))
    o = (lo_a + lo_b) / 2
    s = (lo_b - lo_a) / np.linalg.norm(lo_b - lo_a)
    d = np.array([s[1], -s[0]])
    if ((hi_a + hi_b) / 2 - o) @ d < 0:                  # keep (d, s, up) right-handed: the boxes face outward
        d, s = -d, -s
    L = float(((hi_a + hi_b) / 2 - o) @ d)
    la, lb, ha, hb = ((q - o) @ s for q in (lo_a, lo_b, hi_a, hi_b))
    wa, wb = dict(mean=((la + ha) / 2, (lb + hb) / 2), hi=(ha, hb), lo=(la, lb))[sides]
    sg = 1.0 if wb > wa else -1.0
    return o, d, s, wa - sg * widen[0], wb + sg * widen[1], L


def _flight(geo, lo_a, lo_b, hi_a, hi_b, z_lo, z_hi, n_treads=None, landing=0.0, cheeks=(True, True),
            rail=None, mat='bluestone', sides='mean', widen=(0.0, 0.0)):
    """A straight flight between the bottom edge (lo_a, lo_b) at z_lo and the top edge (hi_a, hi_b) at z_hi (plan
    points; a / b are the two sides).  n risers = n_treads + 1; `landing`: length of the level top part (m)."""
    o, d, s, wa, wb, L = _flight_frame(lo_a, lo_b, hi_a, hi_b, sides, widen)
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
        top = (i + 1) * rise
        if x1 - x0 < 1e-6:                                  # no landing: the top riser, its tread is the ground above
            x1, top = L + 0.30, top - 0.01
        geo.obox(mat, org, ex, ey, ez, (x0, w0, zb), (x1, w1, top), faces='xXyYZ')      # solid to below the ground
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


def _flights():
    """The two flights: plan corners, levels, and the hole each leaves in the terrain."""
    if 'fl' in _G:
        return _G['fl']
    out = []
    # patio stairs: 9 treads between 10 riser lines (aerial x), a landing, rising east; handrail on the north side
    e = plan.site('site.stairs_patio_path')
    rx = e['attrs']['risers_x']
    yn, ysd = 667.0, 720.0
    z_lo = plan.REGIONS['site.patio_pool']
    x_top = max(p[0] for p in e['poly'])
    z_hi = float(gz(*_px([(x_top + 8, (yn + ysd) / 2)])[0]))
    lo = _px([(rx[0], yn), (rx[0], ysd)], z_lo)
    hi = _px([(x_top, yn), (x_top, ysd)], z_hi)
    land = float(np.linalg.norm(_px([(rx[-1], 690)], z_hi)[0] - _px([(x_top, 690)], z_hi)[0]))
    out.append(dict(name='patio_stairs', lo=lo, hi=hi, z_lo=z_lo, z_hi=z_hi, n_treads=len(rx) - 1, landing=land,
                    cheeks=(True, True), rail='a', sides='mean', widen=(0.0, 0.0)))
    # lawn steps: from the path's south end down to the turf at the lawn wall's face (descending south = +v), between
    # the raised planter's east wall and the return wall; black handrail on the east side (p18)
    L = LAWN_STEPS
    z_lo, z_hi = plan.REGIONS['site.lawn_synthetic'], L['z_top']
    lo = _px([(L['u'][0], L['v_bottom']), (L['u'][1], L['v_bottom'])], z_lo)
    hi = _px([(L['u'][0], L['v_top']), (L['u'][1], L['v_top'])], z_hi)
    out.append(dict(name='lawn_steps', lo=lo, hi=hi, z_lo=z_lo, z_hi=z_hi, n_treads=L['treads'], landing=0.0,
                    cheeks=(False, False), rail='b', sides='hi', widen=(0.0, 0.16)))
    for f in out:
        # the hole = the rectangle _flight() builds
        o, d, s, wa, wb, L = _flight_frame(f['lo'][0], f['lo'][1], f['hi'][0], f['hi'][1], f['sides'], f['widen'])
        f['hole'] = [o + s * wa, o + s * wb, o + d * L + s * wb, o + d * L + s * wa]
    _G['fl'] = out
    return out


def _steps():
    geo = Geo()
    info = {}
    for f in _flights():
        _flight(geo, f['lo'][0], f['lo'][1], f['hi'][0], f['hi'][1], f['z_lo'], f['z_hi'], n_treads=f['n_treads'],
                landing=f['landing'], cheeks=f['cheeks'], rail=f['rail'], sides=f['sides'], widen=f['widen'])
        info[f['name']] = dict(z_lo=round(f['z_lo'], 2), z_hi=round(f['z_hi'], 2), risers=f['n_treads'] + 1)
    return geo, info


# ---- walls ----------------------------------------------------------------------------------------------------
def _walls():
    geo = Geo()
    _grid()
    for sp in _G['walls']:
        line, w, top = sp['line'], sp['w'], sp['top']
        if isinstance(top, tuple):
            tops = _above(line, w, top[1])
            if sp['name'] == 'site.wall_lawn_east':      # at least a kerb above the turf
                tops = np.maximum(tops, plan.REGIONS['site.lawn_synthetic'] + 0.35)
            if sp['name'] == 'lawn_steps_return':        # never below the lawn wall it returns from
                tops = np.maximum(tops, WALLS['site.wall_lawn_north'][1])
        else:
            tops = top
        _wall(geo, line, w, tops)
    return geo


# ---- small things on the ground -------------------------------------------------------------------------------
def _slab(geo, mat, c, d, lx, ly, h, sink=0.03):
    """A slab centred on plan point c, long axis along d, standing h above the ground."""
    c, d = np.asarray(c, float), np.asarray(d, float)
    d = d / np.linalg.norm(d)
    z = float(gz(*c))
    geo.obox(mat, (c[0], c[1], z), (d[0], d[1], 0), (-d[1], d[0], 0), (0, 0, 1), (-lx / 2, -ly / 2, -sink),
             (lx / 2, ly / 2, h), faces='xXyYZ')


def _details():
    import shapely.geometry
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
    ring = _px(plan.site('site.path_gravel')['poly'])
    for a, b in zip(ring, np.roll(ring, -1, 0)):
        L = np.linalg.norm(b - a)
        if L > 0.5:
            n = max(1, int(np.ceil(L / 1.0)))               # pieces of <= 1 m: the path's profile bends
            P = a + (b - a) * np.linspace(0, 1, n + 1)[:, None]
            zP = gz(P[:, 0], P[:, 1])
            for k in range(n):
                geo.prism('edging_dark', [(-0.02, -0.10), (0.02, -0.10), (0.02, 0.05), (-0.02, 0.05)],
                          (P[k, 0], P[k, 1], zP[k]), (P[k + 1, 0], P[k + 1, 1], zP[k + 1]), cap=False)
    # the timber retaining edge round the garden's level pad (open where the path arrives at the gate)
    for eid in PADS:
        ring = np.asarray(pad_polygon(eid).exterior.coords)
        keep = _pad_keep(eid).buffer(0.05)
        zl = plan.REGIONS[eid]
        for a, b in zip(ring[:-1], ring[1:]):
            n = max(1, int(np.ceil(np.linalg.norm(b - a) / 0.5)))
            t = (b - a) / np.linalg.norm(b - a)
            out = np.array([t[1], -t[0]])
            if pad_polygon(eid).contains(shapely.geometry.Point((a + b) / 2 + out * 0.05)):
                out = -out
            run = None
            for i in range(n + 1):
                p = a + (b - a) * min(i, n) / n
                mid = a + (b - a) * (i + 0.5) / n
                inside = i < n and not keep.contains(shapely.geometry.Point(mid))
                if inside and run is None:
                    run = p
                if run is not None and (not inside or np.linalg.norm(p - run) > 2.9):
                    q = run + (p - run) * np.linspace(0, 1, 7)[:, None]
                    q = np.vstack([q + out * e for e in (0.1, 0.35, 0.6)])
                    dn = zl - float(gz(q[:, 0], q[:, 1]).min()) + KERB['down']
                    sec = [(-KERB['w'] / 2, -dn), (KERB['w'] / 2, -dn), (KERB['w'] / 2, KERB['up']),
                           (-KERB['w'] / 2, KERB['up'])]
                    d = t * KERB['w'] / 2
                    geo.prism('timber', sec, (run[0] - d[0], run[1] - d[1], zl), (p[0] + d[0], p[1] + d[1], zl))
                    run = p if inside else None
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
    z = float(gz(*c))
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
