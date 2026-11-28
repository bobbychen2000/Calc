"""Zone 'ground' of house 2: the terrain and every ground surface.

The lot is PARTITIONED in plan: every surveyed area of survey/site.json (aerial pixels -> world at its own level,
model/plan.py) takes its material, the first one in SURFACES winning where two overlap; what is left inside the
aerial's footprint is mulch, beyond it 'ground_far'.  Every piece is cut by one 1 m grid and its vertices are set on
plan.ground_z, so neighbouring materials share their edges (no cracks, nothing z-fights) and everything the other
zones stand on plan.ground_z sits on this mesh.  Holes: the pool (the coping's outer outline: water, coping and spa
belong to zone 'pool') and the two flights of steps, which are built as solids here.

On the terrain: retaining walls -- dark grey split-face BLOCK with a block cap course (the lawn walls, the raised
planter, the north wall, the upper terrace wall: p18 / p22 / p23 / p26) or buff ledgestone FIELDSTONE veneer with a grey
bluestone cap (the low walls round the pool deck: the lower terrace wall, the fireplace's east wall, the chevron
planter, the patio stairs' cheeks); tops from the photos or the levels either side --, the patio stairs (9 treads,
black handrail on the north side) and the block steps down to the synthetic lawn, the raised planter's stepped walls,
stepping stones, the side slab, the timber step, the stoop at the patio wing's east door, edging, grates / lids, and
the far ground with the street ~50 m south of the lot and the lane that leads to it (STREET: read from p28).

Hard surfaces (flagstone walks, the pool deck, the driveway pavers) stand DIP proud of the soft ones beside them: the
soft surface eases down by DIP within DIP_W of the paving and the paving's edge is a vertical face (a crisp line at
any distance).  The walks' flagstone ('walk_flagstone') carries UVs along the walk (u = metres along its centre line,
v = metres across: WALK_LEGS), so slab textures follow the curves.  The terrain is cut by a STEP grid and shaded with
the ground's own smooth normals (central differences of the refined grid): no facets on the lawns.
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
    # dark grey split-face retaining-wall block and its cap course (p23 sunlit ~(100, 98, 94) sRGB, the cap a shade
    # lighter; p18 / p22 / p26 the same block in shade)
    'wall_block': dict(color=(0.125, 0.12, 0.112), roughness=0.92),
    'block_cap': dict(color=(0.19, 0.185, 0.175), roughness=0.88),
    # the walks' flagstone (= bluestone's colour; its own name so that a slab texture can run along the walk's UVs)
    'walk_flagstone': dict(color=(0.21, 0.25, 0.29), roughness=0.8),
    'handrail_black': dict(color=(0.012, 0.012, 0.013), roughness=0.5, metallic=0.5),
    'grate_metal': dict(color=(0.05, 0.052, 0.055), roughness=0.6, metallic=0.6),
    'lid_green': dict(color=(0.03, 0.16, 0.06), roughness=0.7),
    'timber': dict(color=(0.42, 0.28, 0.13), roughness=0.85),
    'edging_dark': dict(color=(0.06, 0.05, 0.04), roughness=0.8),
}

STEP = 0.5          # the grid every surface is cut by (m); 1 m triangles drew the membrane's bends as facets
RISE = 0.17
NORMAL_H = 0.20     # central-difference step of the terrain's smooth normals (m)
HARD = ('bluestone', 'walk_flagstone', 'paver_drive')     # paving: DIP proud of the soft surfaces round it
DIP, DIP_W = 0.04, 0.35

# surface partition, first wins: (site id, material)
SURFACES = [
    ('site.walk_front', 'walk_flagstone'), ('site.walk_rear_curved', 'walk_flagstone'), ('site.patio_pool', 'bluestone'),
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
    ('turf_synthetic', [(1657, 1205), (2345, 1200), (2345, 1614), (2320, 1614), (2320, 1226), (1657, 1232)], -0.45,
     'site.lawn_synthetic'),
]
GROW = 0.12         # every area is grown by this much before the partition: closes the slivers between neighbours

# retaining walls: id -> (width m, top: number = level, or ('above', dz) = the higher ground beside it + dz)
WALLS = {
    'site.wall_north': (0.55, ('above', 0.10)),         # block (p23); its top climbs ~1.2 at x -8 (p23 rows 827-830)
    'site.wall_terrace_lower': (0.36, 0.50),            # p22 cap rows 1063-1068 = 0.50, p23 881-887 = ~0.45
    'site.wall_terrace_upper': (0.40, 1.50),            # block; p22 rows 960-968 = 1.5
    'site.wall_fireplace_east': (0.36, 0.50),           # p22 cap rows 1060 / 1071 at u 1680 / 1952 = 0.50
    'site.wall_planter_chevron': (0.36, 0.50),          # p22 x p26: the cap's corner at the stairs (8.45, -3.37, 0.50);
                                                        # p26's cap rows 926-912 along it = 0.50 (frame 133400's 0.6 out)
    'site.wall_planter_mid': (0.36, ('above', 0.10)),   # block (p26: the grey band behind the chevron planter)
    'site.wall_lawn_north': (0.40, 0.50),               # cap 0.45-0.5 (aerial ray into frame 144000), 0.95 above the turf
    'site.wall_lawn_east': (0.85, ('above', 0.10)),
}
# (wall material, cap material) per wall; the rest fieldstone / wall_cap
BLOCK = ('wall_block', 'block_cap')
WALL_MATS = {'site.wall_north': BLOCK, 'site.wall_terrace_upper': BLOCK, 'site.wall_planter_mid': BLOCK,
             'site.wall_lawn_north': BLOCK, 'site.wall_lawn_east': BLOCK, 'terrace_upper_east': BLOCK,
             'planter_lawn_s_lo': BLOCK, 'planter_lawn_s_hi': BLOCK, 'planter_lawn_e_lo': BLOCK,
             'planter_lawn_e_hi': BLOCK, 'planter_lawn_w': BLOCK, 'planter_lawn_n': BLOCK,
             'lawn_steps_return_hi': BLOCK, 'lawn_steps_return_lo': BLOCK}
# walls that are not survey elements (aerial pixels; a 5th item 'inset' = the pixel line is the wall's OUTER face, the
# wall stands w / 2 inside it).  The raised planter west of the lawn steps, its outline = the aerial's cap outline
# (west cap u 1655, south 1215, the steps at 1803).  p18 (round 3): its south wall is STEPPED -- a low west part, top
# ~0.20 (rays at u 1133 / 1200: 0.12 / 0.20) with a light end block at the SW corner, the higher part 0.50 only from
# x ~11.95 (u 1773) to the steps --, and its east wall (the steps' west cheek) climbs with the flight: 0.50, then 0.80
# from y ~-17.55 (v 1192; p18 rays 0.78-0.82).  The return wall along the steps' east side holds the orchard bank:
# cap 1.10 (p18 rows 862-868), its south end a block 0.77 high (rows 893, from v ~1177) over the lawn wall's cap.
# The upper terrace wall continued east of the fireplace (the survey: 'continues behind the fireplace, hidden by
# trees'): p22 (u 1640-2050, rows 952-958) and p26 (u 380-850, rows 858-862) see a grey block wall with its top at 1.5
# behind the bed east of the fireplace; the two photos' ends cross at (9.9, 3.8) by the fireplace; its run south to the
# stairs' north cheek is hidden under the maple (aerial u 1718).
EXTRA_WALLS = [
    ('planter_lawn_s_lo', [(1655, 1215), (1773, 1215)], 0.36, 0.20, 'inset'),
    ('planter_lawn_s_hi', [(1773, 1215), (1803, 1215)], 0.36, 0.50, 'inset'),
    ('planter_lawn_e_lo', [(1803, 1215), (1803, 1192)], 0.36, 0.50, 'inset'),
    ('planter_lawn_e_hi', [(1803, 1192), (1803, 1150)], 0.36, 0.80, 'inset'),
    ('planter_lawn_w', [(1655, 1142), (1655, 1215)], 0.36, 0.20, 'inset'),
    ('planter_lawn_n', [(1655, 1142), (1803, 1142)], 0.36, ('above', 0.08), 'inset'),
    ('lawn_steps_return_hi', [(1873, 1105), (1873, 1177)], 0.36, 1.10),
    ('lawn_steps_return_lo', [(1873, 1177), (1873, 1208)], 0.36, 0.77),
    ('terrace_upper_east', [(1719, 452), (1718, 655)], 0.40, 1.50),
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
# the block steps down to the lawn: 8 risers of 0.17 from the turf (-0.45) to the path's south end (0.91): p18's
# nosing rows 977 / 963 / 949 / 934 / 920 / 907 / 893 / 880 (model 976 / 961 / 947 / 933 / 919 / 905 / 892 / 879)
LAWN_STEPS = dict(u=(1803, 1866), v_top=1154, v_bottom=1212, z_top=0.91, treads=7)

# level profiles along a centre line (aerial pixels, level at each vertex): no cross-fall, the level of the nearest
# point of the line.  The gravel path: level beside the play area, up to the garden's level at its gate, down to the
# top of the lawn steps at its south end.  The driveway: the motor court level, then the fall to the gate.
PROFILES = {
    'site.path_gravel': ([(1975, 315), (1880, 318), (1812, 365), (1797, 500), (1796, 880), (1822, 968), (1850, 1045),
                          (1841, 1150)], [2.55, 2.35, 2.00, 1.80, 1.80, 1.37, 0.99, 0.91]),
    # the raised planter west of the lawn steps: its west part behind the low (0.20) front wall, its east part behind
    # the 0.50 / 0.80 walls by the steps
    'site.planter_lawn': ([(1660, 1178), (1766, 1178), (1778, 1178), (1800, 1178)], [0.10, 0.10, 0.45, 0.45]),
    # the hedge strip west of the path: 1.65 beside the level part (SfM 1.6-1.8 incl. the hedge), then down with the
    # path toward the lawn steps (p18: the planter's north-east wall, which holds it, tops at ~1.07)
    'site.hedge_path': ([(1749, 730), (1749, 900), (1790, 990), (1805, 1050), (1790, 1110)], [1.65, 1.65, 1.25, 1.00, 0.98]),
    # the bed east of the fireplace: behind the fieldstone wall (cap 0.50) up to the upper terrace wall at u 1718
    # (top 1.50), then the upper bed rising to the path (1.80)
    'site.bed_maple_stairs': ([(1668, 580), (1712, 580), (1724, 580), (1790, 580)], [0.42, 0.42, 1.40, 1.75]),
    'site.driveway': ([(150, 300), (150, 1000), (150, 1750), (150, 1875)], [-0.30, -0.30, -0.95, -1.05]),
}
# twisted areas: the level over the aerial box (u0, u1) x (v0, v1) -- z_far along v0 (from u0 to u1), z_near along v1
# (level), the bank between them convex (t ** pow, t = 0 at v1): the orchard rises from just under the lawn wall's
# cap (0.50) to the play area's south edge, which itself rises east (p19: 1.65 at its SW corner, ~2.2 at its SE);
# p18 puts the ground at fruit_1 / fruit_2 (v 1105) at 1.0 / 1.13 and shows no shelf behind the cap
TWISTS = {
    'site.orchard': dict(u=(1900, 2300), v=(905, 1210), z_far=(1.75, 2.20), z_near=0.42, pow=0.9),
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


def _inset(line, d):
    """A plan polyline offset sideways by d (left of its direction: + d)."""
    line = np.asarray(line, float)
    out = []
    for k in range(len(line)):
        t = line[min(k + 1, len(line) - 1)] - line[max(k - 1, 0)]
        t = t / max(np.linalg.norm(t), 1e-9)
        out.append(line[k] + np.array([-t[1], t[0]]) * d)
    return np.array(out)


_PLANTER_C = (1729, 1178)           # inside the raised planter: its walls' 'inset' side


def _wall_specs(zf):
    """Every wall as a world polyline (the surveyed line is the cap: placed at the cap's height).  An 'inset' wall's
    pixel line is its outer face (toward the planter's outside): the centre line is w / 2 inside it."""
    out = []
    items = [(eid, plan.site(eid)['polyline'], w, top) for eid, (w, top) in WALLS.items()] + EXTRA_WALLS
    for item in items:
        name, px, w, top = item[:4]
        px = _dense(px)
        if isinstance(top, tuple):
            line = _on(px, zf)
            for _ in range(2):
                tops = _above(line, w, top[1], zf=zf)
                line = _at(px, tops)
        else:
            line = _at(px, top)
        if len(item) > 4 and item[4] == 'inset':
            c = _at([_PLANTER_C], 0.3)[0]
            d = w / 2
            if np.linalg.norm(_inset(line, d).mean(0) - c) > np.linalg.norm(_inset(line, -d).mean(0) - c):
                d = -d
            line = _inset(line, d)
        out.append(dict(name=name, line=line, w=w, top=top, mats=WALL_MATS.get(name, ('fieldstone', 'wall_cap'))))
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
    for eid, tw in TWISTS.items():
        lv = 0.5 * (tw['z_near'] + max(tw['z_far']))
        m = contains_xy(Polygon(plan.aerial_ring(plan.SITE[eid]['poly'], lv)).buffer(0), X, Y)
        Z[m] = _twist(tw, X[m], Y[m])
        fixed |= m
    ep = _entry_pad()                                   # the front steps land on the walk's level (house: zfoot)
    if ep is not None:
        m = contains_xy(ep['poly'].buffer(0.3), X, Y)
        Z[m] = plan.FRONT_WALK
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


def _twist(tw, x, y):
    """A TWISTS area's level at world points (their aerial pixels at the level found, 2 iterations)."""
    z = np.full(len(x), 0.5 * (tw['z_near'] + max(tw['z_far'])))
    (u0, u1), (v0, v1) = tw['u'], tw['v']
    for _ in range(2):
        uv = plan.to_aerial(np.c_[x, y, z])
        su = np.clip((uv[:, 0] - u0) / (u1 - u0), 0, 1)
        t = np.clip((v1 - uv[:, 1]) / (v1 - v0), 0, 1)
        far = tw['z_far'][0] + (tw['z_far'][1] - tw['z_far'][0]) * su
        z = tw['z_near'] + (far - tw['z_near']) * t ** tw['pow']
    return z


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


def _tris(geo, mat, T, N=None, UV=None):
    """Triangles T (n, 3, 3), up-facing; N (n, 3, 3) vertex normals (default: flat), UV (n, 3, 2) (default: world xy in
    metres)."""
    T = np.asarray(T, float).reshape(-1, 3, 3).copy()
    if not len(T):
        return
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    flip = n[:, 2] < 0
    T[flip] = T[flip][:, ::-1]
    n[flip] *= -1
    if N is not None:
        N = np.asarray(N, float).reshape(-1, 3, 3).copy()
        N[flip] = N[flip][:, ::-1]
    if UV is not None:
        UV = np.asarray(UV, float).reshape(-1, 3, 2).copy()
        UV[flip] = UV[flip][:, ::-1]
    ln = np.linalg.norm(n, axis=1)
    ok = ln > 1e-10
    T, n = T[ok], n[ok] / ln[ok, None]
    V = T.reshape(-1, 3)
    NV = np.repeat(n, 3, 0) if N is None else N[ok].reshape(-1, 3)
    UVV = V[:, :2] if UV is None else UV[ok].reshape(-1, 2)
    geo.mesh(mat).add(V, NV, UVV, np.arange(len(V)).reshape(-1, 3))


def _normals(zf, x, y, h=NORMAL_H):
    """Smooth vertex normals of the surface z = zf(x, y) (central differences)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    dx = (zf(x + h, y) - zf(x - h, y)) / (2 * h)
    dy = (zf(x, y + h) - zf(x, y - h)) / (2 * h)
    n = np.stack([-dx, -dy, np.ones_like(dx)], -1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def _surface(geo, mat, pg, zf=None, uvf=None, smooth=True):
    """Mesh a plan polygon (shapely) on the terrain, cut by the STEP grid; smooth normals of zf; uvf(P2) -> UVs."""
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
    N = _normals(zf, P2[..., 0].ravel(), P2[..., 1].ravel()).reshape(P2.shape[:2] + (3,)) if smooth else None
    _tris(geo, mat, np.concatenate([P2, z[..., None]], -1), N=N, UV=uvf(P2) if uvf else None)


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


def _wall(geo, line, w, tops, piece=3.0, mat='fieldstone', cap='wall_cap', level=True, exact=False):
    """A wall along a plan polyline; tops: one level, or one per vertex.  Long segments are cut into pieces of
    ~`piece` m; level=True steps the top (each piece level at its higher end, the way a dry-stacked wall climbs).
    exact: the top is a measured cap -- not lifted where the ground beside the wall is higher (else the wall always
    closes the gap its footprint leaves)."""
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
        if not exact:
            z0, z1 = max(z0, zh), max(z1, zh)           # a wall always closes the gap its footprint leaves
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
# the walks' centre lines (aerial pixels) for their UVs: each triangle of a walk takes the leg nearest its centroid;
# u = metres along that leg (from its first point), v = signed metres across it
WALK_LEGS = {
    'site.walk_front': [
        [(505, 967), (505, 1117), (500, 1160), (480, 1200), (450, 1230)],               # down from the motor court
        [(450, 1235), (400, 1243), (350, 1251), (300, 1253), (229, 1236)],              # the connector to the drive
        [(590, 1268), (647, 1326), (639, 1393), (690, 1450), (745, 1482), (797, 1484), (853, 1480), (941, 1461),
         (1017, 1458), (1187, 1452)],                                                    # past the porch, the birches
        [(565, 1240), (650, 1268), (735, 1272)],                                         # the landing at the front wing
    ],
    'site.walk_rear_curved': [
        [(1180, 1446), (1254, 1438), (1323, 1425), (1370, 1400), (1398, 1361), (1416, 1323), (1433, 1272),
         (1458, 1225), (1456, 1190), (1452, 1140), (1458, 1090), (1470, 1068)],
        [(1458, 1226), (1500, 1226), (1536, 1226)],                                      # the branch toward the lawn
    ],
}
STOOP = dict(x=(-0.60, 0.32), y=(-17.75, -16.55), top=0.08)   # the patio wing's east door (sill 0.25): one riser down


def _entry_pad():
    """The flagstone stem from the front steps' foot to the front walk (hero: the steps land on flagstone that widens
    into the curved walk; the surveyed walk stops ~1.5 m short of the bottom step), in world coordinates, with its
    centre line.  From the house zone's entry frame; None if it is not available."""
    try:
        from model.zones import house as H
        M, t, n, half, eave = H.entry_frame()
        edge = M + n * (H.ENTRY_EDGE - H.FASCIA_T - 0.03)
    except Exception:                                    # noqa: BLE001 -- the house zone is optional here
        return None
    from shapely.geometry import Polygon
    pts = [(-0.90, -1.15), (-0.90, 1.15), (-2.0, 1.25), (-3.0, 1.7), (-3.6, 1.9), (-3.6, -1.9), (-3.0, -1.7),
           (-2.0, -1.25)]
    ring = [edge + n * a + t * b for a, b in pts]
    return dict(poly=Polygon(ring).buffer(0), line=np.array([edge - n * 0.9, edge - n * 3.6]))


def _legs_world():
    if 'legs' not in _G:
        legs = []
        for eid, ls in WALK_LEGS.items():
            for L in ls:
                legs.append(_on(_dense(L, 15), gz))
        ep = _entry_pad()
        if ep is not None:
            legs.append(ep['line'])
        _G['legs'] = legs
    return _G['legs']


def _leg_uv(P2):
    """UVs along the walks (see WALK_LEGS) for triangles P2 (n, 3, 2)."""
    import shapely
    from shapely.geometry import LineString
    legs = [LineString(L) for L in _legs_world()]
    cen = P2.mean(1)
    pc = shapely.points(cen[:, 0], cen[:, 1])
    D = np.stack([shapely.distance(L, pc) for L in legs], 1)
    k = D.argmin(1)
    UV = np.zeros(P2.shape[:2] + (2,))
    for j, L in enumerate(legs):
        m = k == j
        if not m.any():
            continue
        Q = P2[m].reshape(-1, 2)
        C = np.asarray(L.coords)
        best = np.full(len(Q), np.inf)
        u = np.zeros(len(Q))
        v = np.zeros(len(Q))
        s0 = 0.0
        for a, b in zip(C[:-1], C[1:]):
            ab = b - a
            la = np.linalg.norm(ab)
            if la < 1e-9:
                continue
            e = ab / la
            t = (Q - a) @ e
            tc = np.clip(t, 0, la)
            d = np.hypot(*(Q - (a + tc[:, None] * e)).T)
            w = d < best - 1e-9
            best[w] = d[w]
            u[w] = s0 + t[w]                      # beyond a segment's ends: carried on along it
            v[w] = ((Q - a) @ np.array([-e[1], e[0]]))[w]
            s0 += la
        UV[m] = np.stack([u, v], -1).reshape(-1, 3, 2)
    return UV


def _hard_zone():
    """The paving's plan (before the partition): the soft surfaces ease down DIP next to it."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    if 'hard' not in _G:
        pgs = [Polygon(_ring(eid)).buffer(0).buffer(GROW, join_style='mitre') for eid, mat in SURFACES if mat in HARD]
        ep = _entry_pad()
        if ep is not None:
            pgs.append(ep['poly'])
        _G['hard'] = unary_union(pgs)
    return _G['hard']


def _soft_z(hard):
    """The soft surfaces' ground: gz, eased down DIP within DIP_W of the paving."""
    import shapely
    shapely.prepare(hard)
    edge = hard.boundary

    def zf(x, y):
        x, y = np.asarray(x, float), np.asarray(y, float)
        z = gz(x, y)
        near = np.zeros(x.shape, bool)
        x0, y0, x1, y1 = hard.bounds
        box = (x > x0 - DIP_W) & (x < x1 + DIP_W) & (y > y0 - DIP_W) & (y < y1 + DIP_W)
        if box.any():
            pts = shapely.points(x[box], y[box])
            d = shapely.distance(edge, pts)
            d[shapely.contains(hard, pts)] = 0.0
            t = np.clip(d / DIP_W, 0, 1)
            near[box] = True
            zz = z[box] - DIP * (1 - t * t * (3 - 2 * t))
            z = z.copy()
            z[box] = zz
        return z
    return zf


def _skirt(geo, mat, pg, others, zf=None):
    """The vertical edge of a paving piece down to the eased soft ground (not where another hard piece or a hole is
    beside it)."""
    import shapely
    from shapely.geometry import Point
    zf = zf or gz
    T = []
    for p in getattr(pg, 'geoms', [pg]):
        if p.geom_type != 'Polygon' or p.area < 1e-4:
            continue
        for ring in [p.exterior] + list(p.interiors):
            R = np.asarray(ring.coords)
            for a, b in zip(R[:-1], R[1:]):
                L = np.linalg.norm(b - a)
                if L < 1e-4:
                    continue
                e = (b - a) / L
                nrm = np.array([e[1], -e[0]])
                mid = (a + b) / 2
                if p.contains(Point(mid + nrm * 0.01)):
                    nrm = -nrm
                if others.contains(Point(mid + nrm * 0.06)):
                    continue
                k = max(1, int(np.ceil(L / (STEP / 2))))
                Q = a + (b - a) * np.linspace(0, 1, k + 1)[:, None]
                zt = zf(Q[:, 0], Q[:, 1])
                zb = zt - DIP - 0.04
                for i in range(k):
                    A, B = Q[i], Q[i + 1]
                    T.append([(A[0], A[1], zt[i]), (B[0], B[1], zt[i + 1]), (B[0], B[1], zb[i + 1])])
                    T.append([(A[0], A[1], zt[i]), (B[0], B[1], zb[i + 1]), (A[0], A[1], zb[i])])
                    nn = np.r_[nrm, 0.0]
                    T[-2] = (T[-2], nn)
                    T[-1] = (T[-1], nn)
    if T:
        V = np.array([t for t, _ in T], float)
        Nn = np.array([n for _, n in T], float)
        # orient each quad's triangles to face outward
        n = np.cross(V[:, 1] - V[:, 0], V[:, 2] - V[:, 0])
        bad = np.einsum('ij,ij->i', n, Nn) < 0
        V[bad] = V[bad][:, ::-1]
        geo.mesh(mat).add(V.reshape(-1, 3), np.repeat(Nn, 3, 0),
                          np.stack([(V[..., 0] * 0 + V[..., 0] + V[..., 1]).ravel(), V[..., 2].ravel()], -1),
                          np.arange(len(V) * 3).reshape(-1, 3))


def _terrain():
    from shapely.geometry import Polygon, box
    from shapely.ops import unary_union
    geo = Geo()
    ext = box(*plan.EXTENT)
    holes = unary_union([Polygon(_ring('site.pool_coping')).buffer(0)] + [Polygon(f['hole']) for f in _flights()]
                        + [wall_footprints(), _stoop_plan()])
    # the driveway's hidden end: carried on to the lot's south edge (the lane beyond it: _far)
    drv = Polygon(_ring('site.driveway')).buffer(0)
    dr = np.asarray(drv.exterior.coords)
    south = dr[dr[:, 1] < dr[:, 1].min() + 1.5]
    apron = Polygon([(south[:, 0].min(), south[:, 1].max()), (south[:, 0].max(), south[:, 1].max()),
                     (south[:, 0].max() + 0.5, plan.EXTENT[1]), (south[:, 0].min() - 2.0, plan.EXTENT[1])])
    taken = holes
    polys = []
    ep = _entry_pad()
    if ep is not None:
        polys.append(('walk_flagstone', ep['poly']))
    for eid, mat in SURFACES:
        polys.append((mat, Polygon(_ring(eid)).buffer(0).buffer(GROW, join_style='mitre')))
        if eid == 'site.driveway':
            polys.append(('paver_drive', apron))
        for mat2, px, lvl, before in EXTRA_SURF:
            if before == eid:                            # placed before the SURFACES entry `before`
                polys.insert(len(polys) - 1, (mat2, Polygon(_at(px, lvl)).buffer(0)))
    for eid in PADS:                                     # a pad's margin takes its area's material
        k = [i for i, (mat, pg) in enumerate(polys) if mat == dict(SURFACES)[eid]
             and pg.contains(pad_polygon(eid).buffer(-PADS[eid]['pad'] - 0.5))][0]
        polys.insert(k, (dict(SURFACES)[eid], pad_polygon(eid)))
    hard = _hard_zone().union(apron)
    soft = _soft_z(hard)
    pieces = []
    for mat, pg in polys:
        pg = pg.intersection(ext).difference(taken)
        if mat in HARD:
            _surface(geo, mat, pg, uvf=_leg_uv if mat == 'walk_flagstone' else None)
            pieces.append((mat, pg))
        else:
            _surface(geo, mat, pg, zf=soft)
        taken = unary_union([taken, pg])
    # under the house's roofs (walls, and the roofed open floors: covered patios, porches): flagstone, not mulch;
    # the surveyed beds inside the eave line are already taken (the outline is the eave: placed at eave height)
    under = Polygon(_at(plan.site('site.house_eave_outline')['poly'], plan.EAVE_1)).buffer(0)
    pg = under.difference(taken)
    _surface(geo, 'bluestone', pg)
    taken = unary_union([taken, pg])
    # the paving's vertical edges where a soft surface lies beside it
    hard_all = unary_union([q for _, q in pieces] + [holes, pg])
    for mat, q in pieces:
        _skirt(geo, mat, q, unary_union([hard_all.difference(q.buffer(0.02)), holes, under]), zf=gz)
    # the rest: mulch inside the aerial's footprint, far ground outside it
    img = Polygon(plan.aerial_ring([(0, 0), (2500, 0), (2500, 1875), (0, 1875)], 0.0)).buffer(0)
    rest = ext.difference(taken)
    _surface(geo, 'mulch', rest.intersection(img), zf=soft)
    _surface(geo, 'ground_far', rest.difference(img))
    return geo, apron


def _stoop_plan():
    from shapely.geometry import box
    return box(STOOP['x'][0], STOOP['y'][0], STOOP['x'][1], STOOP['y'][1])


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
            rail=None, mat='bluestone', sides='mean', widen=(0.0, 0.0), tread=None):
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
        geo.obox(mat, org, ex, ey, ez, (x0, w0, zb), (x1, w1, top), faces='xXyYZ',     # solid to below the ground
                 mats={'Z': tread} if tread else None)
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
    # p22 x p26 (round 3): the bottom step's nosing ends triangulate to (8.41, -1.93, 0.17) / (8.38, -3.41, 0.15): the
    # north side fits, the south side (the cheek's inner face) is 0.09 m further north than the mean of the aerial edges
    out.append(dict(name='patio_stairs', lo=lo, hi=hi, z_lo=z_lo, z_hi=z_hi, n_treads=len(rx) - 1, landing=land,
                    cheeks=(True, True), rail='a', sides='mean', widen=(0.0, -0.09)))
    # lawn steps: from the path's south end down to the turf at the lawn wall's face (descending south = +v), between
    # the raised planter's east wall and the return wall; black handrail on the east side (p18)
    L = LAWN_STEPS
    z_lo, z_hi = plan.REGIONS['site.lawn_synthetic'], L['z_top']
    lo = _px([(L['u'][0], L['v_bottom']), (L['u'][1], L['v_bottom'])], z_lo)
    hi = _px([(L['u'][0], L['v_top']), (L['u'][1], L['v_top'])], z_hi)
    out.append(dict(name='lawn_steps', lo=lo, hi=hi, z_lo=z_lo, z_hi=z_hi, n_treads=L['treads'], landing=0.0,
                    cheeks=(False, False), rail='b', sides='hi', widen=(0.0, 0.16), mat='wall_block', tread='block_cap'))
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
                landing=f['landing'], cheeks=f['cheeks'], rail=f['rail'], sides=f['sides'], widen=f['widen'],
                mat=f.get('mat', 'bluestone'), tread=f.get('tread'))
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
        else:
            tops = top
        _wall(geo, line, w, tops, mat=sp['mats'][0], cap=sp['mats'][1], exact=not isinstance(top, tuple))
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
    # the stoop at the patio wing's east door (house: sill 0.25, ground ~-0.09): a flagstone block one riser down
    x0, x1 = STOOP['x']
    y0, y1 = STOOP['y']
    zb = float(gz(np.array([x0, x1, x1, x0]), np.array([y0, y0, y1, y1])).min()) - 0.10
    geo.box('bluestone', (x0, y0, zb), (x1, y1, STOOP['top']), faces='XyYZ')
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
