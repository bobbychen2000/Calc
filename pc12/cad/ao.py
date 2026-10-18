"""
loftkit.ao -- per-vertex ambient occlusion and window-sky visibility baked from the geometry (numpy + scipy only, no
ray tracer).

The viewer lights the closed cabin with the studio's image-based light, which has no occlusion: every seam, the seat
cushion against its back, the floor under the seats, the lining where it meets the ledge -- all lit as if in the open
(review r5 INT8R2-01: the cabin read as flat white clay).  This bakes the missing occlusion into a vertex attribute.

Method: the occluders' surfaces are sampled densely (`spacing`) into a k-d tree, so the distance from any point to the
nearest surface is one query.  From each receiver vertex, K cosine-distributed directions in its normal's hemisphere are
cone-traced (Crassin-style, on the distance instead of a voxel mip chain): at the sample distances `steps` the cone of
half-aperture atan(CONE) is blocked by the fraction 1 - d / (CONE t) of nearby surface, the direction keeps the least
visibility along it, nearer blockers counting fully and farther ones less (`far_weight`).  A flat open surface would
see its own plane at grazing directions (d = t cos(theta) < CONE t): each direction's visibility is divided by that
flat-plane value, so an open flat surface bakes to exactly 1 and only real neighbours occlude.  The mean over the
directions is the cosine-weighted visibility (the directions are cosine-distributed); a light smoothing over the
mesh's own edges takes out the sampling noise.

sky() (flight deck r1 LOOK, L3): the share of each vertex's cosine-weighted hemisphere that sees out of a window -- the
daylight that reaches a surface inside a closed cabin -- and, given a radiance proxy of the interior (bounce), that light
after one bounce off the interior as well.  The walls (interior, skins, frames, doors: never the glass) are
rasterised into a voxel grid; each direction is marched in small steps until it meets a wall voxel (blocked), leaves
the fuselage's outer mould line (outside(): it went out through an opening -- sky), or runs past `reach` (blocked: a long
way down the cabin is no window).  The mean over the directions, smoothed over the mesh's edges like bake().

presplit(): flat midpoint splits of long edges (conforming across the meshes of a part, by position) where the per-vertex
bake would otherwise smear over a large triangle (the flight-deck floor, kick panels, consoles, footwell walls).
"""
from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree

from .mesh import Mesh

CONE = 0.5                                      # cone half-aperture tan (26.6 deg)
STEPS = (0.025, 0.05, 0.09, 0.15, 0.24, 0.36)     # m along each direction
THETA_MAX = 70.0                                # deg: the directions' cap round the normal
K_DIRS = 12


def _dirs(k=K_DIRS, theta_max=THETA_MAX):
    """k cosine-distributed unit directions round +z (Fibonacci spiral on the disc, lifted: Malley's method), within
    theta_max of the axis; and each one's flat-plane visibility (cos(theta) / CONE, clamped to 1)."""
    rmax = np.sin(np.radians(theta_max))
    i = np.arange(k) + 0.5
    r = rmax * np.sqrt(i / k)
    a = i * np.pi * (3.0 - np.sqrt(5.0))
    x, y = r * np.cos(a), r * np.sin(a)
    z = np.sqrt(np.maximum(1.0 - x * x - y * y, 0.0))
    return np.stack([x, y, z], 1), np.minimum(1.0, z / CONE)


def surface_samples(meshes, spacing, density=1.3, seed=0):
    """Points on the triangles of `meshes` (and their vertices), about `spacing` apart: `density` / spacing^2 random
    points per square metre of each triangle, at least one per `spacing` of its longest edge (the slivers along a seam)."""
    rng = np.random.default_rng(seed)
    out = []
    for m in meshes:
        if m is None or len(m.F) == 0:
            continue
        T = m.V[m.F]                                    # (f, 3, 3)
        e = np.max(np.linalg.norm(T - T[:, [1, 2, 0]], axis=2), axis=1)
        A = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
        c = np.maximum(np.ceil(density * A / spacing ** 2), np.ceil(e / spacing) - 1).astype(np.int64)
        out.append(m.V)
        idx = np.repeat(np.arange(len(T)), c)
        if not len(idx):
            continue
        r1, r2 = np.sqrt(rng.random(len(idx))), rng.random(len(idx))
        a, b = 1.0 - r1, r1 * (1.0 - r2)
        tri = T[idx]
        out.append(a[:, None] * tri[:, 0] + b[:, None] * tri[:, 1] + (1.0 - a - b)[:, None] * tri[:, 2])
    return np.vstack(out) if out else np.zeros((0, 3))


def _frames(N):
    """Orthonormal tangent frames (t, b) for unit normals N (n, 3)."""
    a = np.where(np.abs(N[:, 2:3]) < 0.9, np.array([[0.0, 0.0, 1.0]]), np.array([[1.0, 0.0, 0.0]]))
    t = np.cross(a, N)
    t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-12)
    b = np.cross(N, t)
    return t, b


def bake(receivers, occluders, spacing=0.010, steps=STEPS, far=(0.10, 0.36, 0.45), offset=0.003, k=K_DIRS,
         smooth=1, workers=-1, chunk=60000, edt_from=0.08, edt_h=0.016, denoise=None, cell=0.006):
    """Ambient occlusion (n,) in [0, 1] (1 = open) per vertex of each mesh in `receivers` (list), occluded by the
    surfaces of `occluders` (list of meshes, normally including the receivers).  far = (t0, t1, w1): blockers beyond
    t0 count with a weight falling linearly to w1 at t1.  The steps from edt_from on (cone radius >= 40 mm) read the
    distance from a Euclidean distance transform of the samples on an edt_h grid (+-edt_h / 2: the near steps keep the
    exact k-d tree; the far ones were ~3/4 of the k-d tree's time)."""
    pts = surface_samples(occluders, spacing)
    tree = cKDTree(pts)
    edt = None
    if edt_from is not None and len(pts):
        from scipy import ndimage
        Vr = np.vstack([m.V for m in receivers]) if receivers else np.zeros((0, 3))
        reach = float(np.max(steps)) * (1.0 + CONE) + 0.05
        glo, ghi = Vr.min(0) - reach, Vr.max(0) + reach
        shape = tuple(int(np.ceil(v)) for v in (ghi - glo) / edt_h)
        occ = np.ones(shape, bool)                  # True = free (the transform measures to the nearest False)
        ijk = np.floor((pts - glo) / edt_h).astype(np.int64)
        ok = np.all((ijk >= 0) & (ijk < np.array(shape)), 1)
        occ[ijk[ok, 0], ijk[ok, 1], ijk[ok, 2]] = False
        dist = ndimage.distance_transform_edt(occ, sampling=edt_h).astype(np.float32)
        edt = (glo, dist, np.array(shape))
    D, flat = _dirs(k)
    steps = np.asarray(steps, float)
    t0, t1, w1 = far
    wt = np.clip(1.0 - (1.0 - w1) * (steps - t0) / (t1 - t0), w1, 1.0)
    V, N, inv, cuts = _representatives(receivers, cell=cell)
    ao = np.ones(len(V))
    for s in range(0, len(V), chunk):
        v, n = V[s:s + chunk], N[s:s + chunk]
        t, b = _frames(n)
        # world directions (c, k, 3)
        W = D[None, :, 0:1] * t[:, None, :] + D[None, :, 1:2] * b[:, None, :] + D[None, :, 2:3] * n[:, None, :]
        p0 = v + offset * n
        vis = np.ones((len(v), k))
        for j, tj in enumerate(steps):
            q = p0[:, None, :] + tj * W
            if edt is not None and tj >= edt_from:
                glo, dist, shp = edt
                ijk = np.floor((q.reshape(-1, 3) - glo) / edt_h + 0.5).astype(np.int64)    # nearest voxel centre-ish
                inb = np.all((ijk >= 0) & (ijk < shp), 1)
                d = np.full(len(ijk), np.inf)
                d[inb] = dist[ijk[inb, 0], ijk[inb, 1], ijk[inb, 2]]
            else:
                d, _ = tree.query(q.reshape(-1, 3), distance_upper_bound=CONE * tj + spacing, workers=workers)
            d = np.minimum(d.reshape(len(v), k), CONE * tj + spacing)
            # the samples sit up to ~spacing / 2 off the true surface: take that off the gap
            d = np.sqrt(np.maximum(d * d - (0.5 * spacing) ** 2, 0.0))
            c = np.clip(d / (CONE * tj), 0.0, 1.0)
            c = 1.0 - wt[j] * (1.0 - c)
            vis = np.minimum(vis, c)
        vis = np.minimum(1.0, vis / flat[None, :])
        ao[s:s + chunk] = vis.mean(1)
    if denoise is not None:
        ao = _denoise(V, N, ao, *denoise)
    return _scatter(receivers, ao[inv], cuts, smooth)


def _denoise(V, N, a, radius, select=None, ndot=0.75):
    """Normal-aware spatial filter of per-representative values `a` (flight deck fix r1, FDO1-03 / FID-FD1-05): each
    selected representative becomes the Gaussian-weighted mean (sigma radius / 2) of the representatives within
    `radius` whose normals lie within acos(ndot) of its own.  The per-vertex estimates are a dozen or two rays each --
    noise that the viewer's window-light gain (x18 at a low sky share) turned into blotches on the long triangles of the
    glareshield and the posts; edge smoothing (_smooth) averages over the mesh's own spacing only, which is centimetres
    there.  Unselected representatives keep their values (and still feed their neighbours)."""
    if not len(V):
        return a
    sel = np.ones(len(V), bool) if select is None else np.asarray(select(V), bool)
    if not sel.any():
        return a
    tree = cKDTree(V)
    idx = np.nonzero(sel)[0]
    out = a.copy()
    sig2 = (0.5 * radius) ** 2
    for s0 in range(0, len(idx), 50000):
        ii = idx[s0:s0 + 50000]
        d, j = tree.query(V[ii], k=48, distance_upper_bound=radius)
        ok = np.isfinite(d)
        j = np.where(ok, j, 0)
        w = np.exp(-0.5 * np.where(ok, d, 0.0) ** 2 / sig2) * ok
        w *= np.sum(N[j] * N[ii][:, None, :], axis=2) >= ndot
        sw = w.sum(1)
        out[ii] = np.where(sw > 0, (w * a[j]).sum(1) / np.maximum(sw, 1e-12), a[ii])
    return out


def _representatives(meshes, cell=0.006, nq=2.0):
    """The vertices of all `meshes`, deduplicated: one representative per (cell-sized voxel, quantised normal) -- the
    refined meshes carry many vertices a few mm apart that bake to the same value (RES 2: ~2.5x fewer to trace).
    Returns (V, N) of the representatives, the inverse index of every vertex, the meshes' offsets."""
    Vs = [m.V for m in meshes]
    Ns = [m.N / np.maximum(np.linalg.norm(m.N, axis=1, keepdims=True), 1e-12) for m in meshes]
    cuts = np.cumsum([0] + [len(v) for v in Vs])
    V = np.vstack(Vs) if Vs else np.zeros((0, 3))
    N = np.vstack(Ns) if Ns else np.zeros((0, 3))
    key = np.hstack([np.floor(V / cell), np.round(N * nq)]).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    return V[first], N[first], inv.ravel(), cuts


def _scatter(meshes, values, cuts, smooth):
    out = []
    for i, m in enumerate(meshes):
        a = values[cuts[i]:cuts[i + 1]].astype(float)
        if smooth and len(m.F):
            a = _smooth(m, a, smooth)
        out.append(a)
    return out


def _smooth(m, a, it):
    """Average each vertex with its edge neighbours (it passes, half weight on itself)."""
    F = m.F
    i = np.concatenate([F[:, 0], F[:, 1], F[:, 2], F[:, 1], F[:, 2], F[:, 0]])
    j = np.concatenate([F[:, 1], F[:, 2], F[:, 0], F[:, 0], F[:, 1], F[:, 2]])
    deg = np.bincount(i, minlength=len(a)).astype(float)
    for _ in range(it):
        s = np.bincount(i, weights=a[j], minlength=len(a))
        nb = np.where(deg > 0, s / np.maximum(deg, 1), a)
        a = 0.5 * a + 0.5 * nb
    return a


def _dirs_cos(k, theta_max):
    """k cosine-distributed unit directions round +z within theta_max (Malley; Fibonacci spiral on the disc)."""
    rmax = np.sin(np.radians(theta_max))
    i = np.arange(k) + 0.5
    r = rmax * np.sqrt(i / k)
    a = i * np.pi * (3.0 - np.sqrt(5.0))
    x, y = r * np.cos(a), r * np.sin(a)
    return np.stack([x, y, np.sqrt(np.maximum(1.0 - x * x - y * y, 0.0))], 1)


def voxelize(meshes, lo, h, shape, spacing=None, dilate=1):
    """Boolean grid (shape) of the voxels (size h, origin lo) the surfaces of `meshes` cross, grown by `dilate` steps of
    the 6-neighbourhood (so a ray marched in steps of h / 2 cannot slip through a wall)."""
    from scipy import ndimage
    g = np.zeros(shape, bool)
    pts = surface_samples(meshes, spacing or 0.45 * h, density=1.5)
    ijk = np.floor((pts - lo) / h).astype(np.int64)
    ok = np.all((ijk >= 0) & (ijk < np.array(shape)), 1)
    ijk = ijk[ok]
    g[ijk[:, 0], ijk[:, 1], ijk[:, 2]] = True
    if dilate:
        g = ndimage.binary_dilation(g, iterations=int(dilate))
    return g


def sky(receivers, walls, outside, box, h=0.02, reach=2.5, k=16, theta_max=85.0, offset=0.02, step=None,
        smooth=2, chunk=40000, bounce=None, denoise=None):
    """Window-sky visibility (n,) in [0, 1] per vertex of each mesh in `receivers`.  walls: the blocking meshes (no
    glass); outside(P) -> bool: points outside the fuselage (a ray that gets there before a wall saw out); box = (lo, hi)
    of the voxel grid (model axes).  The grid holds 0 free / 1 wall / 2 outside (evaluated once at the voxel centres).
    bounce = (meshes, values): a radiance proxy per vertex of those meshes (e.g. albedo x (sky + glow)); a ray that meets
    a wall then brings that wall's value instead of nothing -- the window light seen directly or after one bounce."""
    lo, hi = (np.asarray(b, float) for b in box)
    shape = tuple(int(np.ceil(v)) for v in (hi - lo) / h)
    occ = voxelize(walls, lo, h, shape).astype(np.int8)
    # the outside, voxel centres slice by slice along x (walls win: a wall voxel stays a wall)
    yc = lo[1] + (np.arange(shape[1]) + 0.5) * h
    zc = lo[2] + (np.arange(shape[2]) + 0.5) * h
    Y, Z = np.meshgrid(yc, zc, indexing="ij")
    for i in range(shape[0]):
        x = lo[0] + (i + 0.5) * h
        P = np.stack([np.full(Y.size, x), Y.ravel(), Z.ravel()], 1)
        o = outside(P).reshape(Y.shape)
        sl = occ[i]
        sl[(sl == 0) & o] = 2
    rad = None
    if bounce is not None:
        rad = _radiance_grid(bounce[0], bounce[1], lo, h, shape)
    return _march(receivers, occ, lo, h, reach, k, theta_max, offset, step or 0.5 * h, smooth, chunk, rad, denoise)


def _radiance_grid(meshes, values, lo, h, shape, spacing=None):
    """Per voxel the largest radiance proxy of the surface samples in it (vertices: their own value, points on a
    triangle: the mean of its corners'), grown by one voxel (a ray stops in the dilated wall band, next to the samples)."""
    from scipy import ndimage
    g = np.zeros(shape, np.float32)
    rng = np.random.default_rng(1)
    sp = spacing or 0.45 * h
    dims = np.array(shape)
    for m, val in zip(meshes, values):
        if m is None or len(m.F) == 0:
            continue
        val = np.asarray(val, float)
        T = m.V[m.F]
        A = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
        c = np.ceil(1.5 * A / sp ** 2).astype(np.int64)
        idx = np.repeat(np.arange(len(T)), c)
        r1, r2 = np.sqrt(rng.random(len(idx))), rng.random(len(idx))
        a, b = 1.0 - r1, r1 * (1.0 - r2)
        tri = T[idx]
        P = np.vstack([m.V, a[:, None] * tri[:, 0] + b[:, None] * tri[:, 1] + (1.0 - a - b)[:, None] * tri[:, 2]])
        L = np.concatenate([val, val[m.F].mean(1)[idx]])
        ijk = np.floor((P - lo) / h).astype(np.int64)
        ok = np.all((ijk >= 0) & (ijk < dims), 1)
        ijk, L = ijk[ok], L[ok]
        np.maximum.at(g, (ijk[:, 0], ijk[:, 1], ijk[:, 2]), L.astype(np.float32))
    return ndimage.maximum_filter(g, size=3)


def _march(receivers, occ, lo, h, reach, k, theta_max, offset, step, smooth, chunk, rad=None, denoise=None):
    ts = np.arange(offset, reach + 1e-9, step)
    D = _dirs_cos(k, theta_max)
    dims = np.array(occ.shape)
    flat = occ.ravel()
    rflat = None if rad is None else rad.ravel()
    strides = np.array([occ.shape[1] * occ.shape[2], occ.shape[2], 1], np.int64)
    V, N, inv, cuts = _representatives(receivers)
    if True:
        res = np.zeros(len(V))
        for s0 in range(0, len(V), chunk):
            v, n = V[s0:s0 + chunk], N[s0:s0 + chunk]
            t, b = _frames(n)
            W = (D[None, :, 0:1] * t[:, None, :] + D[None, :, 1:2] * b[:, None, :] + D[None, :, 2:3] * n[:, None, :]).reshape(-1, 3)
            P0 = (np.repeat(v, k, axis=0) - lo) / h
            W = W / h
            state = np.zeros(len(P0), np.int8)          # 0 marching, 1 sky, -1 blocked
            freed = np.zeros(len(P0), bool)             # the ray has left the walls round its own surface
            got = np.zeros(len(P0))                     # what the ray brings back: 1 (sky) / the wall's radiance proxy
            act = np.arange(len(P0))
            for tj in ts:
                if not len(act):
                    break
                ijk = np.floor(P0[act] + tj * W[act]).astype(np.int64)
                inb = np.all((ijk >= 0) & (ijk < dims), 1)
                c = np.full(len(act), 2, np.int8)       # off the grid: outside
                lin = ijk[inb] @ strides
                c[inb] = flat[lin]
                hit = c == 1
                # the voxels round the vertex's own surface (and whatever touches it within ~2 voxels) do not block:
                # a wall counts once the ray has been in free space (the near field is bake()'s)
                fr = freed[act]
                freed[act[~hit]] = True
                hit &= fr
                state[act[hit]] = -1
                if rflat is not None and hit.any():
                    rv = np.zeros(len(act))
                    rv[inb] = rflat[lin]
                    got[act[hit]] = rv[hit]
                # out of the fuselage: sky if the ray went through free space on the way, else it passed through the walls
                # round its start (a lining 40 mm under the skin: their voxel bands touch)
                gone = c == 2
                state[act[gone & fr]] = 1
                state[act[gone & ~fr]] = -1
                act = act[state[act] == 0]
            got[state == 1] = 1.0
            res[s0:s0 + chunk] = (got if rflat is not None else (state == 1)).reshape(-1, k).mean(1)
    if denoise is not None:
        res = _denoise(V, N, res, *denoise)
    return [np.clip(a, 0.0, 1.0) for a in _scatter(receivers, res[inv], cuts, smooth)]


def presplit(meshes, max_len, select=None, levels=3, tol=1e-7, min_area=0.0, only=None):
    """Split (flat midpoints, in place) every edge longer than max_len of the triangles `select(centroids)` keeps, over
    the meshes of one part together: an edge two meshes share (by position) is split in both, so they stay conforming.
    1 -> 2 / 3 / 4 by the pattern of a triangle's split edges; normals averaged, UVs interpolated.  only: a bool per
    mesh -- only those meshes' triangles are selected (the others are still split along shared edges).  Returns the
    number of triangles added."""
    added = 0
    for _ in range(levels):
        keyed = []
        for m in meshes:
            q = np.round(m.V / tol).astype(np.int64)
            keyed.append(q)
        # long edges of the selected triangles, by position key
        marks = set()
        for mi, (m, q) in enumerate(zip(meshes, keyed)):
            if only is not None and not only[mi]:
                continue
            T = m.V[m.F]
            sel = np.ones(len(m.F), bool) if select is None else select(T.mean(1))
            if min_area > 0:                       # only the broad triangles (the contact pass: not every sliver)
                sel = sel & (0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1) >= min_area)
            for a, b in ((0, 1), (1, 2), (2, 0)):
                L = np.linalg.norm(T[:, b] - T[:, a], axis=1)
                for f in np.nonzero(sel & (L > max_len))[0]:
                    ka, kb = tuple(q[m.F[f, a]]), tuple(q[m.F[f, b]])
                    marks.add((ka, kb) if ka < kb else (kb, ka))
        if not marks:
            break
        for mi, (m, q) in enumerate(zip(meshes, keyed)):
            F = m.F
            V, N = list(m.V), list(m.N)
            UV = None if m.UV is None else list(m.UV)
            mid = {}

            def midpoint(i, j):
                key = (min(i, j), max(i, j))
                if key not in mid:
                    V.append(0.5 * (m.V[i] + m.V[j]))
                    nn = m.N[i] + m.N[j]
                    ln = np.linalg.norm(nn)
                    N.append(nn / ln if ln > 1e-12 else m.N[i])
                    if UV is not None:
                        UV.append(0.5 * (m.UV[i] + m.UV[j]))
                    mid[key] = len(V) - 1
                return mid[key]
            newF = []
            changed = False
            for f in range(len(F)):
                i0, i1, i2 = (int(x) for x in F[f])
                def split(a, b):
                    ka, kb = tuple(q[a]), tuple(q[b])
                    return ((ka, kb) if ka < kb else (kb, ka)) in marks
                s01, s12, s20 = split(i0, i1), split(i1, i2), split(i2, i0)
                n = s01 + s12 + s20
                if n == 0:
                    newF.append((i0, i1, i2)); continue
                changed = True
                if n == 3:
                    a, b, c = midpoint(i0, i1), midpoint(i1, i2), midpoint(i2, i0)
                    newF += [(i0, a, c), (a, i1, b), (c, b, i2), (a, b, c)]
                    continue
                # rotate so the pattern starts at a split edge
                vs = [i0, i1, i2]; sp = [s01, s12, s20]
                r = sp.index(True) if n == 1 else [k for k in range(3) if sp[k] and not sp[(k + 2) % 3]][0]
                vs = vs[r:] + vs[:r]; sp = sp[r:] + sp[:r]
                A, B, C = vs
                if n == 1:
                    a = midpoint(A, B)
                    newF += [(A, a, C), (a, B, C)]
                else:                                  # sp[0] and sp[1]: edges AB and BC
                    a, b = midpoint(A, B), midpoint(B, C)
                    newF += [(A, a, C), (a, B, b), (a, b, C)]
            if changed:
                added += len(newF) - len(F)
                m.V = np.asarray(V, float); m.N = np.asarray(N, float)
                m.F = np.asarray(newF, np.int64)
                if UV is not None:
                    m.UV = np.asarray(UV, float)
    return added


def two_sided(fn, meshes, *args, **kw):
    """fn(meshes, ...) per vertex for the normals' side and the opposite one, the larger of the two: a single-sided sheet
    (a lining panel, a seat cover drawn as one skin) is seen from its open side whichever way its normals point, a
    closed shell's inside (its other side) bakes to ~0 and never wins."""
    a = fn(meshes, *args, **kw)
    flip = []
    for m in meshes:
        f = Mesh(m.V, m.F, -m.N)
        flip.append(f)
    b = fn(flip, *args, **kw)
    return [np.maximum(x, y) for x, y in zip(a, b)]
