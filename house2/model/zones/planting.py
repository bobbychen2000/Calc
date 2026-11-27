"""Zone 'planting' of house 2: every plant of the lot and the surroundings (white model: low-poly lumpy crowns).

SEASON: the video's (spring, in leaf), not the winter aerial's bare limbs.  Positions come from survey/site.json (aerial
p29 pixels; a crown's pixel is taken at the crown's own height, model/plan.py), crown heights from the aerial rays drawn
into the high oblique p28 (out/tmp/planting/tracks.py) and the spring orbit frames; where neither shows a top the
height is a typical one for the species (marked 'typ' in TREES).

Parts:
  plant_trees     the 21 site trees: the big spreading tree at the motor court's NW corner, two multi-stem white
                  birches by the front porch, the two multi-stem patio trees (crape myrtle type), four Japanese maples,
                  five fruit trees on the orchard terrace, small lawn / bed trees
  plant_shrubs    the 10 round shrubs, the three hedges (a row of clipped balls west of the synthetic lawn, the hedge
                  mass along the gravel path, the tall west boundary screen) and sparse low plants in the planting beds
  plant_belts     the tree belts inside the aerial's footprint: north (dark evergreen oaks, some conifers), east (tall
                  leafy trees), south (the yellow-green street-side screen with a few birches)
  plant_context   beyond the aerial: neighbour buildings seen in p28 (positions = p28 rays on the ground plane, +-2 m:
                  the tile-roofed house south of the lot and the one across its road, the shake-roofed building at the
                  SW corner, the grey-roofed house and the pool + pool house to the west), a scatter of trees around
                  them, three columnar poplars, a far canopy and wooded hills on the horizon.

Crowns are flat-shaded displaced icospheres ("blobs"); trunks 5/6-sided tapered tubes.  Everything is seeded.
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, HERE)
from model import plan  # noqa: E402
from model.kit import Geo, Part  # noqa: E402

MATERIALS = {
    'pl_leaf': dict(color=(0.085, 0.20, 0.035), roughness=0.95),          # fresh mid green
    'pl_leaf_light': dict(color=(0.16, 0.30, 0.05), roughness=0.95),      # spring / yellow-green
    'pl_leaf_dark': dict(color=(0.035, 0.085, 0.025), roughness=0.95),    # evergreen oaks, clipped shrubs
    'pl_leaf_yellow': dict(color=(0.34, 0.38, 0.05), roughness=0.95),     # the street screen's yellow-green shrubs
    'pl_leaf_maple': dict(color=(0.20, 0.25, 0.06), roughness=0.95),      # Japanese maples (green-bronze in spring)
    'pl_leaf_red': dict(color=(0.30, 0.07, 0.04), roughness=0.95),        # the red-leaved maple
    'pl_leaf_conifer': dict(color=(0.022, 0.060, 0.030), roughness=0.95),
    'pl_blossom': dict(color=(0.80, 0.80, 0.72), roughness=0.95),         # the white-flowering porch tree
    'pl_bark': dict(color=(0.11, 0.09, 0.07), roughness=1.0),
    'pl_bark_white': dict(color=(0.74, 0.72, 0.66), roughness=0.9),       # birch
    'pl_bark_tan': dict(color=(0.42, 0.33, 0.24), roughness=0.9),         # crape myrtle
    'pl_nb_stucco': dict(color=(0.72, 0.68, 0.60), roughness=0.9),
    'pl_nb_tile': dict(color=(0.52, 0.25, 0.12), roughness=0.9),          # clay tile roofs
    'pl_nb_shake': dict(color=(0.30, 0.24, 0.17), roughness=0.95),        # weathered wood shakes
    'pl_nb_slate': dict(color=(0.22, 0.23, 0.25), roughness=0.9),
    'pl_nb_stone': dict(color=(0.45, 0.38, 0.30), roughness=0.9),
    'pl_nb_deck': dict(color=(0.62, 0.59, 0.52), roughness=0.9),
    'pl_nb_water': dict(color=(0.05, 0.25, 0.60), roughness=0.1),
    'pl_nb_lawn': dict(color=(0.10, 0.22, 0.04), roughness=1.0),
    'pl_far_canopy': dict(color=(0.045, 0.10, 0.04), roughness=1.0),
    'pl_far_hill': dict(color=(0.10, 0.15, 0.11), roughness=1.0),
}

# ---- the site trees: kind, crown-top height above the ground (m), how the height was found ------------------------
#   kind: big / birch / multi (multi-stem vase) / maple (low layered) / fruit / round
TREES = {
    'tree_big_nw': ('big', 12.0, 'p28 ray: crown 5..11.5 m'),
    'tree_lawn1': ('round', 5.0, 'typ (young ornamental)'),
    'tree_court_recess': ('round', 4.5, 'typ'),
    'tree_porch': ('blossom', 3.6, 'front video frame: just under the porch eave'),
    'birch_a': ('birch', 13.0, 'p28 ray: white limbs to ~13-14 m, above the 8.5 m ridge'),
    'birch_b': ('birch', 12.0, 'p28 ray'),
    'tree_patio_nw': ('round', 5.0, 'p28 ray ~5 m'),
    'tree_patio_a': ('multi', 7.2, 'p28 ray ~7 m (above the two-storey eave 6.4)'),
    'tree_patio_b': ('multi', 7.0, 'p28 ray ~6.5-7 m'),
    'jmaple_upper': ('maple_red', 3.0, 'typ'),
    'jmaple_stairs': ('maple', 4.8, 'p28 ray ~4.5 m; larger in leaf (orbit frame)'),
    'jmaple_planter': ('maple_red', 3.0, 'typ'),
    'jmaple_arbor_se': ('maple', 5.4, 'orbit frame: about the arbor + 1.5 m'),
    'tree_planter_lawn': ('round', 7.5, 'orbit frame 159.5 s: a broad light-green crown'),
    'tree_play_ne': ('light', 5.0, 'p28'),
    'fruit_1': ('fruit', 4.0, 'p28 ray 3.5-4 m'),
    'fruit_2': ('fruit', 3.6, 'p28 ray'),
    'fruit_3': ('fruit', 3.8, 'p28 ray'),
    'fruit_4': ('fruit', 3.6, 'p28 ray'),
    'fruit_5': ('fruit', 3.6, 'p28 ray'),
    'tree_north_yg': ('light', 5.5, 'typ'),
}
LEAFY = 1.12            # crowns in leaf are this much wider than the bare limbs outlined in the winter aerial


# ---- primitives -----------------------------------------------------------------------------------------------------
_ICO = {}


def _ico(level):
    if level in _ICO:
        return _ICO[level]
    t = (1 + 5 ** 0.5) / 2
    V = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
         (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    F = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
         (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7),
         (9, 8, 1)]
    V = [np.array(v, float) / np.linalg.norm(v) for v in V]
    for _ in range(level):
        mid, F2 = {}, []

        def m(a, b):
            k = (min(a, b), max(a, b))
            if k not in mid:
                p = V[a] + V[b]
                V.append(p / np.linalg.norm(p))
                mid[k] = len(V) - 1
            return mid[k]
        for a, b, c in F:
            ab, bc, ca = m(a, b), m(b, c), m(c, a)
            F2 += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        F = F2
    _ICO[level] = (np.array(V), np.array(F))
    return _ICO[level]


def _flat(geo, mat, V, F):
    """Emit triangles flat-shaded (own vertices per face)."""
    P = V[F].reshape(-1, 3)
    a, b, c = P[0::3], P[1::3], P[2::3]
    n = np.cross(b - a, c - a)
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    N = np.repeat(n, 3, axis=0)
    geo.mesh(mat).add(P, N, P[:, :2].copy(), np.arange(len(P)).reshape(-1, 3))


def blob(geo, mat, c, r, rs, level=1, lump=0.22, zmin=None):
    """A lumpy ellipsoid: centre c, radii r (scalar or 3), flat-shaded.  zmin: nothing hangs below this height."""
    U, F = _ico(level)
    r = np.broadcast_to(np.asarray(r, float), (3,))
    d = np.zeros(len(U))
    for f, a in ((1.7, 1.0), (3.3, 0.55)):
        k = rs.normal(size=3)
        k2 = rs.normal(size=3)
        d += a * np.sin(f * (U @ k) + rs.uniform(0, 6.28)) * np.cos(f * 0.7 * (U @ k2) + rs.uniform(0, 6.28))
    V = U * (1.0 + lump * d)[:, None] * r + np.asarray(c, float)
    if zmin is not None:
        V[:, 2] = np.maximum(V[:, 2], zmin)
    _flat(geo, mat, V, F)


def tube(geo, mat, pts, radii, n=6):
    """Tapered tube along a polyline (flat-shaded sides, closed tip)."""
    pts = np.asarray(pts, float)
    radii = np.broadcast_to(np.asarray(radii, float), (len(pts),))
    rings = []
    for i, p in enumerate(pts):
        d = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        d /= np.linalg.norm(d)
        u = np.cross(d, (0.0, 0.0, 1.0))
        u = np.array([1.0, 0, 0]) if np.linalg.norm(u) < 1e-6 else u / np.linalg.norm(u)
        v = np.cross(d, u)
        an = np.arange(n) * 2 * math.pi / n
        rings.append(p + radii[i] * (np.cos(an)[:, None] * u + np.sin(an)[:, None] * v))
    V = np.vstack(rings + [pts[-1][None]])
    F = []
    for i in range(len(pts) - 1):
        for j in range(n):
            a, b = i * n + j, i * n + (j + 1) % n
            F += [(a, a + n, b), (b, a + n, b + n)]         # outward for this ring orientation (checked below)
    top = (len(pts) - 1) * n
    F += [(top + j, len(V) - 1, top + (j + 1) % n) for j in range(n)]
    F = np.array(F)
    # orient outward: compare the first face normal with the direction away from the axis
    a, b, c = V[F[0]]
    if np.dot(np.cross(b - a, c - a), (a + b + c) / 3 - (pts[0] + pts[1]) / 2) < 0:
        F = F[:, ::-1]
    _flat(geo, mat, V, F)


def cone(geo, mat, c, r, z0, z1, rs, n=8):
    an = np.arange(n) * 2 * math.pi / n + rs.uniform(0, 1)
    rr = r * (1 + 0.15 * rs.normal(size=n))
    ring = np.stack([c[0] + rr * np.cos(an), c[1] + rr * np.sin(an), np.full(n, z0)], -1)
    V = np.vstack([ring, [(c[0], c[1], z1)]])
    F = np.array([(j, (j + 1) % n, n) for j in range(n)])
    _flat(geo, mat, V, F)


def _gz(x, y):
    return float(plan.ground_z(x, y))


# ---- tree builders (base = (x, y) on the terrain; h = crown top above the ground; r = crown radius) ----------------
def round_tree(geo, xy, h, r, rs, leaf='pl_leaf', bark='pl_bark', level=2, clear=None, nsat=4, tr=None, lump=0.22):
    x, y = xy
    z = _gz(x, y)
    clear = 0.38 * h if clear is None else clear
    tr = tr or max(0.05, 0.022 * h)
    lean = rs.normal(scale=0.03 * h, size=2)
    top = np.array([x + lean[0], y + lean[1], z + 0.72 * h])
    tube(geo, bark, [(x, y, z - 0.1), (x + lean[0] * 0.4, y + lean[1] * 0.4, z + clear), top], [tr, tr * 0.75, tr * 0.25],
         n=6)
    ch = h - clear                                           # crown depth
    cz = z + clear + 0.52 * ch
    blob(geo, leaf, (top[0], top[1], cz), (0.78 * r, 0.78 * r, 0.50 * ch), rs, level=level, lump=lump)
    for i in range(nsat):
        a = rs.uniform(0, 6.28) if nsat < 3 else (i + rs.uniform(-0.3, 0.3)) * 6.283 / nsat
        k = rs.uniform(0.45, 0.62)
        rr = r * rs.uniform(0.42, 0.55)
        c = (top[0] + k * r * math.cos(a), top[1] + k * r * math.sin(a), cz + rs.uniform(-0.22, 0.12) * ch)
        blob(geo, leaf, c, (rr, rr, rr * rs.uniform(0.65, 0.85)), rs, level=1, lump=lump)
        if i % 2 == 0 and r > 1.8:
            tube(geo, bark, [(x, y, z + clear * 0.9), c], [tr * 0.5, tr * 0.15], n=5)


def multi_tree(geo, xy, h, r, rs, leaf='pl_leaf', bark='pl_bark_tan', stems=4, spread=0.55, level=2, crown=0.42,
               tr=0.07, droop=0.0):
    """Multi-stem vase (crape myrtle, birch clump): stems fan out from the base, each carrying part of the crown."""
    x, y = xy
    z = _gz(x, y)
    a0 = rs.uniform(0, 6.28)
    tops = []
    for i in range(stems):
        a = a0 + i * 6.283 / stems + rs.uniform(-0.3, 0.3)
        k = spread * r * rs.uniform(0.7, 1.0)
        hh = h * rs.uniform(0.80, 0.92)
        b = np.array([x + 0.12 * math.cos(a), y + 0.12 * math.sin(a), z - 0.1])
        m = np.array([x + 0.45 * k * math.cos(a), y + 0.45 * k * math.sin(a), z + 0.45 * hh])
        t = np.array([x + k * math.cos(a), y + k * math.sin(a), z + hh])
        tube(geo, bark, [b, m, t], [tr, tr * 0.7, tr * 0.2], n=5)
        tops.append(t)
    cz = z + h * (1 - crown * 0.55)
    blob(geo, leaf, (x, y, cz), (0.62 * r, 0.62 * r, 0.50 * crown * h * 1.15), rs, level=level)
    for t in tops:
        rr = r * rs.uniform(0.40, 0.52)
        blob(geo, leaf, (t[0], t[1], t[2] - 0.75 * rr - droop * h * 0.1), (rr, rr, rr * (0.9 + droop)), rs, level=1)


def maple(geo, xy, h, r, rs, leaf='pl_leaf_maple'):
    """Japanese maple: low, wide, layered; short forked stems."""
    x, y = xy
    z = _gz(x, y)
    for i in range(3):
        a = rs.uniform(0, 6.28)
        t = (x + 0.35 * r * math.cos(a), y + 0.35 * r * math.sin(a), z + 0.62 * h)
        tube(geo, 'pl_bark', [(x, y, z - 0.1), (x + 0.1 * r * math.cos(a), y + 0.1 * r * math.sin(a), z + 0.3 * h), t],
             [0.07, 0.055, 0.02], n=5)
    blob(geo, leaf, (x, y, z + 0.72 * h), (0.70 * r, 0.70 * r, 0.27 * h), rs, level=2, lump=0.2)
    n = 5
    a0 = rs.uniform(0, 6.28)
    for i in range(n):
        a = a0 + i * 6.283 / n
        rr = r * rs.uniform(0.42, 0.52)
        blob(geo, leaf, (x + 0.55 * r * math.cos(a), y + 0.55 * r * math.sin(a), z + h * rs.uniform(0.52, 0.66)),
             (rr, rr, 0.20 * h), rs, level=1, lump=0.2)


def big_tree(geo, xy, h, r, rs):
    """The very large spreading tree: a 0.5 m trunk forking at ~3 m into heavy limbs, a wide domed crown."""
    x, y = xy
    z = _gz(x, y)
    fork = np.array([x, y, z + 3.0])
    tube(geo, 'pl_bark', [(x, y, z - 0.2), (x, y, z + 1.2), fork], [0.34, 0.26, 0.24], n=8)
    blob(geo, 'pl_leaf', (x, y, z + 0.66 * h), (0.55 * r, 0.55 * r, 0.30 * h), rs, level=2)
    n = 7
    a0 = rs.uniform(0, 6.28)
    for i in range(n):
        a = a0 + i * 6.283 / n + rs.uniform(-0.2, 0.2)
        k = r * rs.uniform(0.55, 0.68)
        rr = r * rs.uniform(0.38, 0.46)
        c = np.array([x + k * math.cos(a), y + k * math.sin(a), z + h * rs.uniform(0.50, 0.62)])
        mid = (fork + c) / 2 + (0, 0, 0.6)
        tube(geo, 'pl_bark', [fork, mid, c], [0.17, 0.11, 0.04], n=5)
        blob(geo, 'pl_leaf' if i % 3 else 'pl_leaf_light', c, (rr, rr, rr * 0.72), rs, level=2)
    for i in range(4):                                                  # the crown's upper tier
        a = a0 + 0.5 + i * 6.283 / 4
        rr = r * 0.36
        blob(geo, 'pl_leaf', (x + 0.3 * r * math.cos(a), y + 0.3 * r * math.sin(a), z + h - rr * 0.78),
             (rr, rr, rr * 0.75), rs, level=1)


def fruit_tree(geo, xy, h, r, rs):
    x, y = xy
    z = _gz(x, y)
    tube(geo, 'pl_bark', [(x, y, z - 0.1), (x, y, z + 0.9)], [0.07, 0.06], n=5)
    n = 4
    a0 = rs.uniform(0, 6.28)
    for i in range(n):
        a = a0 + i * 6.283 / n
        t = (x + 0.5 * r * math.cos(a), y + 0.5 * r * math.sin(a), z + 0.78 * h)
        tube(geo, 'pl_bark', [(x, y, z + 0.85), t], [0.045, 0.015], n=5)
        rr = r * rs.uniform(0.5, 0.6)
        blob(geo, 'pl_leaf', (t[0], t[1], z + h - rr * 0.8), (rr, rr, rr * 0.8), rs, level=1)
    blob(geo, 'pl_leaf', (x, y, z + 0.66 * h), (0.6 * r, 0.6 * r, 0.26 * h), rs, level=1)


def conifer(geo, xy, h, r, rs, z=None, tiers=3):
    x, y = xy
    z = _gz(x, y) if z is None else z
    tube(geo, 'pl_bark', [(x, y, z - 0.2), (x, y, z + 0.3 * h)], [0.02 * h, 0.014 * h], n=5)
    for i in range(tiers):
        f0 = 0.18 + 0.60 * i / tiers
        f1 = min(1.0, f0 + 0.95 / tiers + 0.08)
        cone(geo, 'pl_leaf_conifer', (x, y), r * (1 - 0.62 * i / tiers), z + f0 * h, z + f1 * h, rs, n=7)


def poplar(geo, xy, h, r, rs, z=None):
    x, y = xy
    z = _gz(x, y) if z is None else z
    tube(geo, 'pl_bark', [(x, y, z - 0.2), (x, y, z + 0.3 * h)], [0.2, 0.15], n=5)
    blob(geo, 'pl_leaf', (x, y, z + 0.58 * h), (r, r, 0.43 * h), rs, level=1, lump=0.12)


def belt_tree(geo, xy, h, r, rs, leaf, z=None):
    """A cheap backdrop / belt tree: trunk + 4 small-count blobs."""
    x, y = xy
    z = _gz(x, y) if z is None else z
    tube(geo, 'pl_bark', [(x, y, z - 0.2), (x, y, z + 0.6 * h)], [0.025 * h, 0.012 * h], n=5)
    blob(geo, leaf, (x, y, z + 0.66 * h), (0.72 * r, 0.72 * r, 0.33 * h), rs, level=1, lump=0.25)
    a0 = rs.uniform(0, 6.28)
    for i in range(3):
        a = a0 + i * 2.094
        rr = r * rs.uniform(0.45, 0.58)
        blob(geo, leaf, (x + 0.5 * r * math.cos(a), y + 0.5 * r * math.sin(a), z + h * rs.uniform(0.48, 0.62)),
             (rr, rr, rr * 0.8), rs, level=0 if r < 2.2 else 1, lump=0.25)


# ---- survey access --------------------------------------------------------------------------------------------------
def _crown(eid, h, zc=None):
    """World (x, y) of a tree / shrub and its crown radius: the aerial's crown centre taken at the crown's height."""
    e = plan.site('site.' + eid)
    a = e['attrs']
    uv = np.asarray(a.get('crown_center') or np.mean(a['crown_poly'], 0), float)
    rp = a.get('crown_radius_px') or a.get('radius_px')
    c = np.asarray(plan.aerial_xy(uv, 0.0), float)
    for _ in range(2):
        z = _gz(c[0], c[1]) + (0.65 * h if zc is None else zc)
        c = np.asarray(plan.aerial_xy(uv, z), float)
    e2 = np.asarray(plan.aerial_xy(uv + (rp, 0), z), float)
    return c, float(np.linalg.norm(e2 - c))


def _seed(name):
    return np.random.RandomState(sum(ord(ch) * (i + 7) for i, ch in enumerate(name)) % 100000)


def site_trees():
    geo = Geo()
    for name, (kind, h, _) in TREES.items():
        rs = _seed(name)
        c, r = _crown(name, h, zc=3.0 if kind == 'big' else None)
        r *= LEAFY
        if kind == 'big':
            big_tree(geo, c, h, r, rs)
        elif kind == 'birch':
            # the aerial outline is the spread of the bare limbs of the whole clump; stems rise steeply
            multi_tree(geo, c, h, r * 0.80, rs, leaf='pl_leaf_light', bark='pl_bark_white', stems=4, spread=0.5,
                       crown=0.62, tr=0.10, droop=0.5)
        elif kind == 'multi':
            multi_tree(geo, c, h, r * 0.9, rs, leaf='pl_leaf', bark='pl_bark_tan', stems=5, spread=0.6, crown=0.5)
        elif kind == 'maple':
            maple(geo, c, h, r, rs)
        elif kind == 'maple_red':
            maple(geo, c, h, r, rs, leaf='pl_leaf_red')
        elif kind == 'fruit':
            fruit_tree(geo, c, h, r, rs)
        elif kind == 'blossom':
            round_tree(geo, c, h, r, rs, leaf='pl_blossom', level=1, nsat=3, clear=0.35 * h)
        elif name == 'tree_planter_lawn':
            round_tree(geo, c, h, r * 1.15, rs, leaf='pl_leaf_light', level=2, nsat=5)
        elif kind == 'light':
            round_tree(geo, c, h, r, rs, leaf='pl_leaf_light', level=1)
        else:
            round_tree(geo, c, h, r, rs, level=2 if r > 2.5 else 1)
    return Part('plant_trees', geo, group='trees')


# ---- shrubs, hedges, bed plants -----------------------------------------------------------------------------------
SHRUBS = {   # height / radius; material
    'shrub_north_a': (1.5, 'pl_leaf_dark'), 'shrub_north_b': (1.5, 'pl_leaf_light'), 'shrub_north_c': (1.5, 'pl_leaf'),
    'shrub_north_big': (1.6, 'pl_leaf_light'), 'shrub_orchard_w': (1.6, 'pl_leaf_light'),
    'shrub_orchard_e': (1.5, 'pl_leaf_light'), 'shrub_play_east': (1.6, 'pl_leaf'),
    'shrub_walk_1': (1.5, 'pl_leaf_dark'), 'shrub_walk_2': (1.5, 'pl_leaf_dark'),
    'shrub_front_south': (1.5, 'pl_leaf_yellow'),
}


def _ball(geo, mat, x, y, r, h, rs, level=1, lump=0.12):
    z = _gz(x, y)
    blob(geo, mat, (x, y, z + 0.45 * h), (r, r, 0.56 * h), rs, level=level, lump=lump, zmin=z - 0.05)


def _poly(eid, z=0.8):
    from shapely.geometry import Polygon
    p = Polygon(np.asarray(plan.aerial_ring(plan.site(eid)['poly'], z), float))
    return p if p.is_valid else p.buffer(0)


def _scatter(pg, step, rs, jitter=0.35):
    """Jittered grid points inside a shapely polygon."""
    from shapely.geometry import Point
    from shapely.prepared import prep
    if pg.is_empty:
        return np.zeros((0, 2))
    pp = prep(pg)
    x0, y0, x1, y1 = pg.bounds
    out = []
    for i, x in enumerate(np.arange(x0 + step * 0.5, x1, step)):
        for y in np.arange(y0 + step * (0.5 if i % 2 else 0.25), y1, step * 0.92):
            q = (x + rs.uniform(-jitter, jitter) * step, y + rs.uniform(-jitter, jitter) * step)
            if pp.contains(Point(q)):
                out.append(q)
    return np.array(out).reshape(-1, 2)


def shrubs():
    from shapely.geometry import Point
    from shapely.ops import unary_union
    geo = Geo()
    for name, (k, mat) in SHRUBS.items():
        rs = _seed(name)
        c, r = _crown(name, 1.5, zc=1.0)
        _ball(geo, mat, c[0], c[1], r, k * r, rs, level=2)
    # the row of ~6 clipped balls along the synthetic lawn's west edge
    rs = _seed('hedge_lawn_west')
    pg = _poly('site.hedge_lawn_west', 0.9)
    x0, y0, x1, y1 = pg.bounds
    n = 6
    for i in range(n):
        y = y0 + (i + 0.5) * (y1 - y0) / n
        r = min(0.95, (y1 - y0) / n * 0.52)
        _ball(geo, 'pl_leaf_dark', (x0 + x1) / 2 + rs.uniform(-0.1, 0.1), y, r, 1.35, rs, level=1, lump=0.08)
    # the hedge mass along the gravel path: overlapping mounds over its outline
    rs = _seed('hedge_path')
    pg = _poly('site.hedge_path', 1.0)
    for q in _scatter(pg.buffer(-0.35), 0.95, rs):
        _ball(geo, 'pl_leaf_dark', q[0], q[1], 0.85, rs.uniform(1.1, 1.45), rs, level=0, lump=0.15)
    # the west boundary screen: tall shrubs / small trees beside the driveway
    rs = _seed('hedge_west')
    ring = np.asarray(plan.aerial_ring(plan.site('site.hedge_west_boundary')['poly'], 2.0), float)
    xm = ring[:, 0].mean()
    y = ring[:, 1].min() + 1.0
    while y < ring[:, 1].max():
        h = rs.uniform(3.0, 5.0)
        r = rs.uniform(1.3, 1.9)
        x = xm - 0.6 + rs.uniform(-0.4, 0.4)
        z = _gz(x, y)
        blob(geo, 'pl_leaf_dark' if rs.rand() < 0.6 else 'pl_leaf', (x, y, z + 0.5 * h), (r, r, 0.55 * h), rs, level=1,
             lump=0.2, zmin=z)
        y += r * 1.5
    # sparse low plants in the planting beds (clear of the trees' feet and the surveyed shrubs)
    keep_off = []
    for name in list(TREES) + list(SHRUBS):
        c, r = _crown(name, 2.0, zc=1.0)
        keep_off.append(Point(c).buffer(0.6 if name in TREES else r + 0.2))
    keep_off = unary_union(keep_off + [_poly('site.hedge_path'), _poly('site.hedge_lawn_west')])
    mats = ['pl_leaf_dark', 'pl_leaf', 'pl_leaf_light', 'pl_leaf', 'pl_leaf_maple', 'pl_blossom']
    nb = 0
    for e in plan.SITE.values():
        if e['type'] != 'planting_bed' or 'poly' not in e:
            continue
        rs = _seed(e['id'])
        try:
            ring = np.asarray(plan.site_ring(e['id']), float)[:, :2]
            from shapely.geometry import Polygon
            pg = Polygon(ring).buffer(0)
        except Exception:
            continue
        pg = pg.buffer(-0.45).difference(keep_off)
        for q in _scatter(pg, 1.5, rs, jitter=0.4):
            if rs.rand() < 0.25:
                continue
            r = rs.uniform(0.22, 0.48)
            _ball(geo, mats[rs.randint(len(mats)) if rs.rand() < 0.9 else 5], q[0], q[1], r, r * rs.uniform(1.1, 1.7), rs,
                  level=0, lump=0.18)
            nb += 1
    return Part('plant_shrubs', geo, group='plants', extras=dict(bed_plants=nb))


# ---- tree belts inside the aerial's footprint -----------------------------------------------------------------------
def _belt(geo, pg, step, rs, pick, inner):
    """Trees on a jittered grid inside the belt polygon; a crown may overhang the lot side by 1 m at most."""
    from shapely.geometry import Point
    n = 0
    for q in _scatter(pg.buffer(-0.8), step, rs, jitter=0.3):
        kind, h, r, leaf = pick(q, rs)
        d_in = pg.boundary.distance(Point(q))
        r = min(r, max(1.4, d_in + 1.0)) if _near_lot(q, pg) else r
        if kind == 'conifer':
            conifer(geo, q, h, r, rs)
        elif kind == 'birch':
            multi_tree(geo, q, h, r, rs, leaf='pl_leaf_light', bark='pl_bark_white', stems=3, spread=0.4, crown=0.6,
                       level=1, tr=0.08)
        else:
            belt_tree(geo, q, h, r, rs, leaf)
        n += 1
    return n


def _near_lot(q, pg):
    x0, y0, x1, y1 = plan.EXTENT
    # the polygon's boundary nearest to q is the lot side unless q is closer to the aerial's edge
    return min(q[0] - x0, x1 - q[0], q[1] - y0, y1 - q[1]) > 2.5


def belts():
    from shapely.geometry import box, Polygon
    from shapely.ops import unary_union
    geo = Geo()
    lot = box(-38.0, -30.0, 26.0, 12.0)

    def north(q, rs):
        u = rs.rand()
        if q[0] > 4 and q[0] < 16:                      # the broad dark live-oak canopy NE of the pool / fireplace
            return 'oak', rs.uniform(9.0, 12.0), rs.uniform(3.6, 4.6), 'pl_leaf_dark'
        if u < 0.15 and q[1] > 19:
            return 'conifer', rs.uniform(14, 20), rs.uniform(2.6, 3.4), None
        return 'oak', rs.uniform(7.0, 11.0), rs.uniform(2.8, 4.0), ('pl_leaf_dark', 'pl_leaf', 'pl_leaf_light')[
            rs.randint(3) if u > 0.4 else 0]

    def east(q, rs):
        u = rs.rand()
        return 'oak', rs.uniform(8.0, 12.5), rs.uniform(2.8, 4.0), ('pl_leaf_dark', 'pl_leaf', 'pl_leaf_yellow')[
            0 if u < 0.5 else 1 if u < 0.85 else 2]

    def south(q, rs):
        u = rs.rand()
        if u < 0.08:
            return 'birch', rs.uniform(9, 11), rs.uniform(2.2, 2.8), None
        return 'oak', rs.uniform(5.0, 8.5), rs.uniform(2.4, 3.4), ('pl_leaf_yellow', 'pl_leaf_light', 'pl_leaf')[
            0 if u < 0.5 else 1 if u < 0.8 else 2]

    # the aerial's footprint ends inside the belts: carry each belt on to the edge of plan.EXTENT
    x0, y0, x1, y1 = plan.EXTENT
    img = Polygon(np.asarray(plan.aerial_ring([(0, 0), (2500, 0), (2500, 1875), (0, 1875)], 4.0), float)).buffer(0.01)
    rest = box(x0, y0, x1, y1).difference(img)
    ix0, iy0, ix1, iy1 = img.bounds
    pn = unary_union([_poly('site.trees_north', 5.0), rest.intersection(box(x0, iy1 - 0.5, x1, y1))])
    pe = unary_union([_poly('site.trees_east', 5.0), rest.intersection(box(ix1 - 0.5, y0, x1, iy1 - 0.5))])
    ps = unary_union([_poly('site.trees_south', 4.0), rest.intersection(box(x0, y0, ix1 - 0.5, iy0 + 0.5))])
    pw = rest.intersection(box(x0, iy0 + 0.5, ix0 + 0.5, iy1 - 0.5))
    n = 0
    for pg, step, name, pick in ((pn, 4.2, 'belt_n', north), (pe, 4.0, 'belt_e', east), (ps, 3.7, 'belt_s', south),
                                 (pw, 4.2, 'belt_w', east)):
        for g in getattr(pg, 'geoms', [pg]):
            if g.area > 4.0:
                n += _belt(geo, g, step, _seed(name), pick, lot)
    return Part('plant_belts', geo, group='trees', extras=dict(trees=n))


# ---- context: neighbours, surrounding trees, far canopy, hills -----------------------------------------------------
def _block(geo, c, size, ang, z0, eave, pitch, wall, roof, over=0.5, flat_top=None):
    """An oriented box with a hip roof (ridge along its long side).  flat_top: cut the hip off at this height."""
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    ex, ey = np.array([ca, sa, 0.0]), np.array([-sa, ca, 0.0])
    o = np.array([c[0], c[1], 0.0])
    lx, ly = size[0] / 2, size[1] / 2
    P = lambda x, y, z: o + ex * x + ey * y + np.array([0, 0, z])
    geo.obox(wall, o, ex, ey, np.array([0, 0, 1.0]), (-lx, -ly, z0), (lx, ly, eave), faces='xXyY')
    lx, ly = lx + over, ly + over
    rise = ly * math.tan(math.radians(pitch))
    run = ly
    if flat_top is not None and eave + rise > flat_top:
        k = (flat_top - eave) / rise
        rise, run = flat_top - eave, ly * k
    a, b, c2, d = P(-lx, -ly, eave), P(lx, -ly, eave), P(lx, ly, eave), P(-lx, ly, eave)
    ra, rb, rc, rd = (P(-lx + run, -ly + run, eave + rise), P(lx - run, -ly + run, eave + rise),
                      P(lx - run, ly - run, eave + rise), P(-lx + run, ly - run, eave + rise))
    for q in ([a, b, rb, ra], [b, c2, rc, rb], [c2, d, rd, rc], [d, a, ra, rd]):
        if np.linalg.norm(q[2] - q[3]) < 1e-6:
            geo.poly(roof, q[:3])
        else:
            geo.poly(roof, q)
    if np.linalg.norm(ra - rd) > 1e-6:
        geo.poly(wall if flat_top is not None else roof, [ra, rb, rc, rd])
    geo.poly('pl_nb_stucco', [d, c2, b, a])                 # soffit


# neighbour buildings: (centre x, y), (length, width), angle deg, eave, pitch, wall, roof  -- from p28 ground rays
NEIGHBOURS = [
    dict(c=(5.0, -57.0), size=(22.0, 15.0), ang=-18, eave=6.3, pitch=22, wall='pl_nb_stucco', roof='pl_nb_tile'),   # A
    dict(c=(-9.5, -49.5), size=(12.0, 11.0), ang=-18, eave=3.4, pitch=22, wall='pl_nb_stucco', roof='pl_nb_tile'),  # A wing
    dict(c=(-33.0, -128.0), size=(28.0, 16.0), ang=35, eave=6.0, pitch=22, wall='pl_nb_stucco', roof='pl_nb_tile'),  # B
    dict(c=(-76.0, -31.0), size=(19.0, 13.0), ang=82, eave=6.0, pitch=30, wall='pl_nb_stucco', roof='pl_nb_slate'),  # D
    dict(c=(-73.0, 4.5), size=(12.0, 6.0), ang=70, eave=3.0, pitch=24, wall='pl_nb_stone', roof='pl_nb_slate'),     # E
]
NB_POOL = [(-55.1, -5.2), (-53.9, 8.9), (-58.1, 9.3), (-58.5, -3.8)]
NB_DECK = [(-52.7, -5.8), (-47.8, 9.6), (-61.9, 17.9), (-66.8, -1.8)]
ZFAR = -0.4                 # zone 'ground': level of the far ground


def context():
    from shapely.geometry import Point, Polygon, box
    from shapely.ops import unary_union
    geo = Geo()
    rs = _seed('context')
    for nb in NEIGHBOURS:
        _block(geo, nb['c'], nb['size'], nb['ang'], ZFAR, nb['eave'], nb['pitch'], nb['wall'], nb['roof'])
    # the shake-roofed building at the SW corner (aerial: its roof runs off the bottom edge)
    bb = plan.site('site.structure_south')['bbox']
    p0 = np.asarray(plan.aerial_xy((bb[0], bb[1]), 2.6), float)
    p1 = np.asarray(plan.aerial_xy((bb[2], bb[1]), 2.6), float)
    L = float(np.linalg.norm(p1 - p0))
    W = 7.0
    cs = ((p0[0] + p1[0]) / 2, p0[1] - W / 2 + 0.5)
    _block(geo, cs, (L - 1.0, W - 1.0), math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0])), -1.0, 2.6, 24,
           'pl_nb_stucco', 'pl_nb_shake')
    # the western neighbour's pool, deck and lawn
    z = ZFAR + 0.06
    geo.poly('pl_nb_lawn', [(-47.5, -14, z - 0.02), (-47.5, 20, z - 0.02), (-68, 22, z - 0.02), (-68, -12, z - 0.02)][::-1])
    geo.poly('pl_nb_deck', [(p[0], p[1], z) for p in NB_DECK][::-1] if Polygon(NB_DECK).exterior.is_ccw is False
             else [(p[0], p[1], z) for p in NB_DECK])
    pool = NB_POOL if Polygon(NB_POOL).exterior.is_ccw else NB_POOL[::-1]
    geo.poly('pl_nb_water', [(p[0], p[1], z + 0.03) for p in pool])
    # trees around: none on the buildings, the neighbour's pool lawn, the street band, the aerial's own footprint
    x0, y0, x1, y1 = plan.EXTENT
    keep = [box(x0, y0, x1, y1), Polygon(NB_DECK).buffer(3.0), box(-68, -14, -47.5, 22),
            box(-400, y0 - 9.5, 400, y0 - 1.0),                        # zone ground's street band
            box(-45, -100, 5, -78).buffer(3)]                           # the road in front of house B (p28)
    for nb in NEIGHBOURS:
        keep.append(Point(nb['c']).buffer(max(nb['size']) * 0.62 + 2.5))
    keep.append(Point(cs).buffer(L * 0.6 + 1.5))
    keep = unary_union(keep)
    ring = box(x0 - 105, y0 - 105, x1 + 105, y1 + 105).difference(keep)
    mats = ['pl_leaf_dark', 'pl_leaf', 'pl_leaf', 'pl_leaf_light', 'pl_leaf_yellow']
    n = 0
    lotc = np.array([(x0 + x1) / 2, (y0 + y1) / 2])
    for q in _scatter(ring, 8.5, rs, jitter=0.42):
        d = max(abs(q[0] - lotc[0]) - (x1 - x0) / 2, abs(q[1] - lotc[1]) - (y1 - y0) / 2)
        if rs.rand() < 0.10 + 0.25 * d / 105:           # thinner farther out (the far canopy takes over)
            continue
        u = rs.rand()
        if u < 0.16:
            conifer(geo, q, rs.uniform(15, 24), rs.uniform(2.8, 3.8), rs, z=ZFAR, tiers=2)
        else:
            h, r = rs.uniform(8, 14), rs.uniform(3.4, 5.2)
            x, y = q
            tube(geo, 'pl_bark', [(x, y, ZFAR), (x, y, ZFAR + 0.55 * h)], [0.2, 0.1], n=4)
            m = mats[rs.randint(len(mats))]
            blob(geo, m, (x, y, ZFAR + 0.64 * h), (r, r, 0.36 * h), rs, level=1, lump=0.28)
            if d < 45:
                a = rs.uniform(0, 6.28)
                blob(geo, m, (x + 0.55 * r * math.cos(a), y + 0.55 * r * math.sin(a), ZFAR + 0.5 * h),
                     (0.6 * r, 0.6 * r, 0.25 * h), rs, level=0, lump=0.28)
        n += 1
    # the columnar poplars seen SE of the lot in the spring frames (beyond the south belt; position approximate)
    for q, h in (((14.0, -41.0), 19.0), ((17.5, -42.5), 21.0), ((21.0, -41.5), 18.0), ((-1.0, -40.5), 16.0)):
        if q[1] > y0:
            q = (q[0], y0 - 0.5)
        poplar(geo, q, h, 1.7, rs, z=ZFAR)
    # far canopy: a lumpy green annulus 110 .. 700 m out, tops 9-14 m
    R = [118.0, 170.0, 260.0, 420.0, 700.0]
    na = 56
    c = lotc
    grid = []
    for i, rr in enumerate(R):
        an = np.arange(na) * 2 * math.pi / na + (0.5 * math.pi / na if i % 2 else 0)
        zz = ZFAR + (9.0 + 5.0 * rs.rand(na)) * (1.0 if i else 0.0) + (0 if i else -0.5)
        grid.append(np.stack([c[0] + rr * np.cos(an), c[1] + rr * np.sin(an), zz], -1))
    V = np.vstack(grid)
    F = []
    for i in range(len(R) - 1):
        for j in range(na):
            a, b = i * na + j, i * na + (j + 1) % na
            F += [(a, a + na, b), (b, a + na, b + na)]
    _flat(geo, 'pl_far_canopy', V, np.array(F))
    # wooded hills on the horizon behind p28's camera (world +X +Y: the video's first shot shows them); p28 itself looks
    # toward -X -Y over flat land to a far shore, so the rim stays low there
    R2 = [700.0, 1100.0, 1700.0, 2400.0]
    na = 48
    an = np.arange(na) * 2 * math.pi / na
    az = np.degrees(an)                                         # 0 = +X, 90 = +Y
    w = 0.5 + 0.5 * np.cos(np.radians(az - 45.0))               # 1 toward +X +Y
    prof = (6 + 110 * w ** 2.5) * (0.75 + 0.5 * rs.rand(na))
    grid = []
    for i, rr in enumerate(R2):
        k = (0.0, 0.35, 1.0, 0.8)[i]
        zz = ZFAR + 10.0 + prof * k * (0.85 + 0.3 * rs.rand(na))
        grid.append(np.stack([c[0] + rr * np.cos(an), c[1] + rr * np.sin(an), zz], -1))
    V = np.vstack(grid)
    F = []
    for i in range(len(R2) - 1):
        for j in range(na):
            a, b = i * na + j, i * na + (j + 1) % na
            F += [(a, a + na, b), (b, a + na, b + na)]
    _flat(geo, 'pl_far_hill', V, np.array(F))
    return Part('plant_context', geo, group='backdrop', extras=dict(trees=n))


def build():
    return [site_trees(), shrubs(), belts(), context()]


VIEWS = {
    'aerial': dict(label='Aerial', pos=(-48.0, -62.0, 38.0), target=(-12.0, -8.0, 1.0), fov=42, fit='dolly'),
}

if __name__ == '__main__':
    for p in build():
        print('%-14s %7d' % (p.name, p.ntri), p.extras)
