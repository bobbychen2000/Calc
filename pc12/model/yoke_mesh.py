"""
Stage-3 surface mesh of the yoke's black MOULDING (rev M, sheets L6Y rev E / L6Y2 rev D): the smooth field
moulding_smooth (yoke_geom.moulding without the pads' pockets and the trim face's grooves -- yoke_patch builds those as
explicit crease-exact patches) meshed as a smooth triangle surface.  The cover, the switches and the patches are built
explicitly (yoke_cover, yoke3d, yoke_patch).

ROUTE (the moulding's faces exist only implicitly -- rolling-ball joins, the head zones, the necks -- so they are meshed
from the field, never re-modelled):

  1. ADAPTIVE OCTREE over the part's box: a cell is split while the surface crosses it and the field over its
     3 x 3 x 3 lattice departs from trilinear by more than DC_EPS; 2:1 balanced.
  2. DUAL CONTOURING of the octree (Ju et al. 2002): one vertex per leaf the surface crosses (QEF of the exact tangent
     planes), one polygon per minimal edge with a sign change; non-manifold edges repaired; exact field gradients.
  3. (yoke_patch.cut: the pads and the trim face cut out along their tabled edges, the boundary vertices exact.)
  4. HIGHLIGHT DECIMATION (decimate_interp; decimate2 is its base) by vectorised, independent half-edge collapses
     (2-ring independent sets, lowest QEM cost first): a collapse is refused if a new face turns more than DEC cone from
     its vertices' exact normals, flips, falls below the angle floor, an edge's end normals turn more than DEC turn
     while its PN bow exceeds min_sag (cad.res's interior criterion: the result is a fixed point of cad.refine), the
     QEM distance exceeds dist, an edge exceeds lmax, or the link condition fails; boundary vertices only slide along
     their loop (bnd_tol / bnd_turn / bnd_lmax) -- and, the highlight criterion, when a dense vertex (a sample with its
     exact normal) owned by a face round the removed vertex would lie farther than sdist from the new faces or their
     corner normals interpolated there would miss its normal by more than its tolerance (yoke_patch: FRAME_TOL, scaled
     by visibility and curvature).  interp_errors / highlight_report measure the result.
  5. Every vertex projected exactly onto the zero level with its gradient normal (project_exact); edges that still fail
     the turn / bow criterion split at their projected PN midpoints (refine_split); sliver_cleanup; _fix_normals where
     the field itself kinks.

Everything is in yoke-local millimetres (u outboard -- the co-pilot sense --, h up, a aft; model/yoke_geom.py); the
pilot yoke is the mirror image.  The expensive stages are disk-cached under the design key (out/tmp/yoke_mesh_cache,
git-ignored): a table or code change re-meshes.
"""
from __future__ import annotations

import hashlib
import math
import os
from pathlib import Path

import numpy as np

from model import yoke_geom as G

CACHE_DIR = Path(__file__).resolve().parents[1] / "out" / "tmp" / "yoke_mesh_cache"
GRID_SHIFT = np.array([0.3137, 0.4271, 0.2219])   # the lattice origin offset (fine cells): no table plane / centreline on
#                                                  a lattice plane (two cells would both put a crease vertex on it)
LAM = 1.6                 # Lipschitz bound assumed for the fields (the cover's top land is steeper locally: safe side)


# ============================================================================================ parallel evaluation
_FN = {}
_POOL = [None, None]


def _call(args):
    name, P = args
    return _FN[name](P[:, 0], P[:, 1], P[:, 2])


def evaluate(name, P, chunk=60000):
    """Field `name` at the points P (n, 3) mm: in a fork pool (3 workers) for large sets."""
    P = np.asarray(P, float)
    if len(P) == 0:
        return np.zeros(0)
    if len(P) < 2 * chunk or WORKERS <= 1:
        return _FN[name](P[:, 0], P[:, 1], P[:, 2])
    if _POOL[0] is None or _POOL[1] != name:
        close_pool()
        import multiprocessing as mp
        _FN[name](P[:200, 0], P[:200, 1], P[:200, 2])            # warm the caches before the fork
        _POOL[0] = mp.get_context("fork").Pool(WORKERS)
        _POOL[1] = name
    parts = [(name, P[i:i + chunk]) for i in range(0, len(P), chunk)]
    return np.concatenate(_POOL[0].map(_call, parts))


def close_pool():
    if _POOL[0] is not None:
        _POOL[0].close()
        _POOL[0].join()
        _POOL[0] = None
        _POOL[1] = None


WORKERS = int(os.environ.get("YOKE_MESH_WORKERS", "3"))


def gradient(name, P, e=0.004):
    """Unit gradient of field `name` at P (central differences, e mm)."""
    P = np.asarray(P, float)
    n = len(P)
    if n == 0:
        return np.zeros((0, 3))
    Q = np.concatenate([P + d for d in (np.array([e, 0, 0]), np.array([-e, 0, 0]), np.array([0, e, 0]),
                                         np.array([0, -e, 0]), np.array([0, 0, e]), np.array([0, 0, -e]))])
    v = evaluate(name, Q).reshape(6, n)
    g = np.stack([v[0] - v[1], v[2] - v[3], v[4] - v[5]], -1)
    return g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-12)


def project(name, P, iters=4, e=0.004):
    """Newton projection of P onto the zero level along the field gradient; returns (P, |f| after, unit gradient)."""
    P = np.asarray(P, float).copy()
    for _ in range(iters):
        f = evaluate(name, P)
        g = gradient(name, P, e)
        P = P - f[:, None] * g
    f = evaluate(name, P)
    return P, np.abs(f), gradient(name, P, e)


# ============================================================================================ node store
class Nodes:
    """Field values at integer lattice nodes (units of the finest step h0, origin O), evaluated on demand."""

    M = 1 << 20

    def __init__(self, name, O, h0):
        self.name, self.O, self.h0 = name, np.asarray(O, float), float(h0)
        self.k = np.zeros(0, np.int64)
        self.v = np.zeros(0)
        self.n_eval = 0

    def enc(self, I):
        I = np.asarray(I, np.int64)
        return (I[..., 0] * self.M + I[..., 1]) * self.M + I[..., 2]

    def dec(self, k):
        return np.stack([k // (self.M * self.M), (k // self.M) % self.M, k % self.M], -1)

    def get(self, I):
        I = np.asarray(I, np.int64)
        shp = I.shape[:-1]
        k = self.enc(I).ravel()
        uk, inv = np.unique(k, return_inverse=True)
        pos = np.searchsorted(self.k, uk)
        pos_c = np.minimum(pos, max(len(self.k) - 1, 0))
        found = (len(self.k) > 0) & (self.k[pos_c] == uk) if len(self.k) else np.zeros(len(uk), bool)
        out = np.empty(len(uk))
        if found.any():
            out[found] = self.v[pos_c[found]]
        miss = uk[~found]
        if len(miss):
            P = self.O + self.dec(miss) * self.h0
            val = evaluate(self.name, P)
            self.n_eval += len(miss)
            out[~found] = val
            allk = np.concatenate([self.k, miss])
            allv = np.concatenate([self.v, val])
            o = np.argsort(allk, kind="stable")
            self.k, self.v = allk[o], allv[o]
        return out[inv].reshape(shp)


# ============================================================================================ octree
CORNERS = np.array([(i, j, k) for k in (0, 1) for j in (0, 1) for i in (0, 1)], np.int64)     # index = i + 2j + 4k
LATTICE = np.array([(i, j, k) for k in (0, 1, 2) for j in (0, 1, 2) for i in (0, 1, 2)], np.int64)
_LC = np.array([(LATTICE == 2 * c).all(1).nonzero()[0][0] for c in CORNERS])        # lattice index of each corner


def _trilinear_weights():
    t = LATTICE / 2.0
    w = np.ones((27, 8))
    for c, (i, j, k) in enumerate(CORNERS):
        w[:, c] = (t[:, 0] if i else 1 - t[:, 0]) * (t[:, 1] if j else 1 - t[:, 1]) * (t[:, 2] if k else 1 - t[:, 2])
    return w


TRI_W = _trilinear_weights()


def _ckey(l, ijk):
    ijk = np.asarray(ijk, np.int64)
    return ((np.int64(l) * (1 << 16) + ijk[..., 0]) * (1 << 16) + ijk[..., 1]) * (1 << 16) + ijk[..., 2]


class Octree:
    """Adaptive narrow-band octree of a field: leaves[l] (n, 3) cell indices at level l (size h0 2^l)."""

    def __init__(self, name, box, h0=0.0625, lmax=6, lleaf=5, eps=0.004, zones=None, lam=LAM):
        self.name, self.h0, self.lmax, self.lam = name, float(h0), int(lmax), float(lam)
        lo = np.asarray(box[:3], float) - 1.0 + GRID_SHIFT * self.h0      # off the tables' round numbers
        hi = np.asarray(box[3:], float) + 1.0
        S = self.h0 * (1 << self.lmax)
        self.O = lo
        n = np.ceil((hi - lo) / S).astype(int)
        self.nodes = Nodes(name, self.O, self.h0)
        g = np.stack(np.meshgrid(*[np.arange(k) for k in n], indexing="ij"), -1).reshape(-1, 3)
        cells = self._active(g, self.lmax)
        self.leaves = {l: np.zeros((0, 3), np.int64) for l in range(self.lmax + 1)}
        self.internal = {l: np.zeros((0, 3), np.int64) for l in range(self.lmax + 1)}
        zones = zones or []
        self.stats = {}
        for l in range(self.lmax, 0, -1):
            if not len(cells):
                break
            s = self.h0 * (1 << l)
            lat = self.lattice_vals(cells, l)                        # (n, 27)
            cor = lat[:, _LC]
            sgn_lat = (lat.min(1) < 0) & (lat.max(1) > 0)
            tri = cor @ TRI_W.T
            nonlin = np.abs(lat - tri).max(1)
            mism = ((lat < 0) != (tri < 0)).any(1)
            sub = sgn_lat & ((nonlin > eps) | mism)
            if l > lleaf:
                sub |= sgn_lat | (np.abs(lat).min(1) < self.lam * 0.87 * s)
            C = self.O + (cells + 0.5) * s
            for zfn, zl in zones:
                if l > zl:
                    sub |= zfn(C, s)
            self.stats[l] = (len(cells), int(sub.sum()))
            self.leaves[l] = cells[~sub]
            par = cells[sub]
            self.internal[l] = par
            if not len(par):
                cells = par
                break
            ch = (2 * par[:, None, :] + CORNERS[None, :, :]).reshape(-1, 3)
            # child corners are the parent's lattice: activity from those values
            latp = lat[sub]                                          # (np, 27)
            sel = (2 * CORNERS)[None, :, None, :] // 2 + CORNERS[None, None, :, :]  # child c, corner k -> lattice ijk
            li = sel[..., 0] + 3 * sel[..., 1] + 9 * sel[..., 2]                       # (1, 8, 8)
            cv = latp[:, li[0]]                                                         # (np, 8 children, 8 corners)
            cv = cv.reshape(-1, 8)
            sc = s / 2.0
            act = ((cv.min(1) < 0) & (cv.max(1) > 0)) | (np.abs(cv).min(1) <= self.lam * 1.74 * sc)
            cells = ch[act]
        if len(cells) and self.lmax > 0 and l == 1:
            self.leaves[0] = cells
        self._balance()
        self._index()

    # ---- lattice values (fine-node indexed)
    def lattice_vals(self, cells, l):
        half = 1 << (l - 1) if l > 0 else None
        I = cells[:, None, :] * (1 << l) + LATTICE[None, :, :] * half
        return self.nodes.get(I)

    def corner_vals(self, cells, l):
        I = (cells[:, None, :] + CORNERS[None, :, :]) * (1 << l)
        return self.nodes.get(I)

    def _active(self, cells, l):
        v = self.corner_vals(cells, l)
        s = self.h0 * (1 << l)
        act = ((v.min(1) < 0) & (v.max(1) > 0)) | (np.abs(v).min(1) <= self.lam * 1.74 * s)
        return cells[act]

    # ---- 2:1 balance (face, edge and corner neighbours)
    def _balance(self):
        nb = np.array([(i, j, k) for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1) if (i, j, k) != (0, 0, 0)])
        for _ in range(12):
            changed = False
            for l in range(0, self.lmax - 1):
                L = self.leaves[l]
                if not len(L):
                    continue
                # a leaf at level l needs every neighbouring region at level l + 1 not to be a leaf at level >= l + 2
                P = np.unique(((L[:, None, :] + nb[None]) >> 1).reshape(-1, 3), axis=0)   # level l+1 positions
                for lc in range(l + 2, self.lmax + 1):
                    Q = np.unique(P >> (lc - l - 1), axis=0)
                    if not len(self.leaves[lc]):
                        continue
                    kl = _ckey(lc, self.leaves[lc])
                    kq = _ckey(lc, Q)
                    hit = np.isin(kl, kq)
                    if hit.any():
                        self._split(lc, self.leaves[lc][hit])
                        self.leaves[lc] = self.leaves[lc][~hit]
                        changed = True
            if not changed:
                break

    def _split(self, l, cells):
        self.internal[l] = np.vstack([self.internal[l], cells])
        ch = (2 * cells[:, None, :] + CORNERS[None, :, :]).reshape(-1, 3)
        ch = self._active(ch, l - 1)
        self.leaves[l - 1] = np.vstack([self.leaves[l - 1], ch])

    def _index(self):
        self.lkeys, self.lid0 = {}, {}
        n = 0
        for l in range(self.lmax + 1):
            L = self.leaves[l]
            k = _ckey(l, L)
            o = np.argsort(k)
            self.leaves[l] = L[o]
            self.lkeys[l] = k[o]
            self.lid0[l] = n
            n += len(L)
        self.n_leaves = n
        self.ikeys = {l: np.sort(_ckey(l, self.internal[l])) for l in range(self.lmax + 1)}

    def leaf_of(self, l, pos):
        """Leaf id containing the level-l cell positions pos (n, 3): -1 if that position is subdivided (internal),
        -2 if no leaf covers it (outside the band)."""
        out = np.full(len(pos), -2, np.int64)
        ik = self.ikeys[l]
        kp = _ckey(l, pos)
        if len(ik):
            i = np.minimum(np.searchsorted(ik, kp), len(ik) - 1)
            out[ik[i] == kp] = -1
        todo = out == -2
        for lc in range(l, self.lmax + 1):
            if not todo.any():
                break
            lk = self.lkeys[lc]
            if not len(lk):
                continue
            q = pos[todo] >> (lc - l)
            kq = _ckey(lc, q)
            i = np.minimum(np.searchsorted(lk, kq), len(lk) - 1)
            ok = lk[i] == kq
            idx = np.nonzero(todo)[0]
            out[idx[ok]] = self.lid0[lc] + i[ok]
            todo[idx[ok]] = False
        return out

    def leaf_cells(self):
        """(ids order) level and ijk of every leaf."""
        lv = np.concatenate([np.full(len(self.leaves[l]), l) for l in range(self.lmax + 1)])
        ijk = np.vstack([self.leaves[l] for l in range(self.lmax + 1)])
        return lv, ijk


# ============================================================================================ dual contouring
AX = ((0, 1, 2), (1, 2, 0), (2, 0, 1))     # axis a, then b, c (right-handed)


def contour(T: Octree, crease_deg=22.0):
    """Dual contouring of the octree T: (V (n, 3) mm, F (m, 3), vertex class (0 smooth, 1 crease, 2 corner))."""
    lv, ijk = T.leaf_cells()
    edges_all = []
    for l in range(T.lmax + 1):
        L = T.leaves[l]
        if not len(L):
            continue
        for a, b, c in AX:
            for p in (0, 1):
                for q in (0, 1):
                    E = L.copy()
                    E[:, b] += p
                    E[:, c] += q
                    edges_all.append((l, a, E))
    # unique minimal edges per (level, axis)
    polys, xs, us, segs = [], [], [], []
    for l in range(T.lmax + 1):
        for a, b, c in AX:
            Es = [E for (ll, aa, E) in edges_all if ll == l and aa == a]
            if not Es:
                continue
            E = np.unique(np.vstack(Es), axis=0)
            # end values
            s0 = E * (1 << l)
            s1 = s0.copy()
            s1[:, a] += 1 << l
            f0 = T.nodes.get(s0)
            f1 = T.nodes.get(s1)
            ch = (f0 < 0) != (f1 < 0)
            if not ch.any():
                continue
            E, f0, f1, s0 = E[ch], f0[ch], f1[ch], s0[ch]
            ids = []
            for (dp, dq) in ((0, 0), (1, 0), (1, 1), (0, 1)):
                pos = E.copy()
                pos[:, b] += dp - 1
                pos[:, c] += dq - 1
                ids.append(T.leaf_of(l, pos))
            ids = np.stack(ids, 1)
            minimal = (ids != -1).all(1)
            ids, E, f0, f1, s0 = ids[minimal], E[minimal], f0[minimal], f1[minimal], s0[minimal]
            miss = (ids == -2).any(1)
            if miss.any():
                T.stats.setdefault("missing", 0)
                T.stats["missing"] += int(miss.sum())
            ids, E, f0, f1, s0 = ids[~miss], E[~miss], f0[~miss], f1[~miss], s0[~miss]
            t = f0 / (f0 - f1)
            x = T.O + s0 * T.h0
            x[:, a] += t * T.h0 * (1 << l)
            # gradient estimate at the crossing: central differences of the level-l nodes round the edge (all of them
            # are corners of the four cells, or lattice nodes of a level l + 1 leaf: no new evaluations)
            eb = np.zeros(3, np.int64)
            ec = np.zeros(3, np.int64)
            ea = np.zeros(3, np.int64)
            eb[b], ec[c], ea[a] = 1, 1, 1
            sc = 1 << l

            def nv(off):
                return T.nodes.get((E + off) * sc)
            ga = f1 - f0
            gb = 0.5 * ((1 - t) * (nv(eb) - nv(-eb)) + t * (nv(ea + eb) - nv(ea - eb)))
            gc = 0.5 * ((1 - t) * (nv(ec) - nv(-ec)) + t * (nv(ea + ec) - nv(ea - ec)))
            g = np.zeros((len(E), 3))
            g[:, a], g[:, b], g[:, c] = ga, gb, gc
            g /= np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-12)
            flip = f0 > 0                                           # outward = +a when f0 < 0
            ids = np.where(flip[:, None], ids[:, ::-1], ids)
            polys.append(ids)
            xs.append(x)
            us.append(g)
            p0 = T.O + s0 * T.h0
            p1 = p0.copy()
            p1[:, a] += T.h0 * (1 << l)
            segs.append(np.c_[p0, p1, f0, f1])
    P = np.vstack(polys)
    X = np.vstack(xs)
    Ng = np.vstack(us)
    T.segs = np.vstack(segs)                     # per crossing: edge end points and their field values
    return P, X, Ng


def leaf_vertices(T: Octree, P, X, Ng, name, crease_deg=22.0, exact_normals=True):
    """Vertex per leaf used by the polygons P (k, 4) with crossings X (k, 3): mass point, or the QEF point of the exact
    tangent planes where the crossings' normals spread more than crease_deg.  Returns (V, cls, used leaf ids)."""
    used = np.unique(P.ravel())
    remap = -np.ones(T.n_leaves, np.int64)
    remap[used] = np.arange(len(used))
    Pi = remap[P]
    nv = len(used)
    # membership pairs (vertex, crossing), unique per polygon (a coarse leaf may appear twice in one polygon)
    rows = np.repeat(np.arange(len(P)), 4)
    vtx = Pi.ravel()
    pair = np.unique(np.c_[vtx, rows], axis=0)
    vtx, rows = pair[:, 0], pair[:, 1]
    cnt = np.bincount(vtx, minlength=nv).astype(float)
    m = np.zeros((nv, 3))
    np.add.at(m, vtx, X[rows])
    m /= np.maximum(cnt, 1)[:, None]
    # estimated normals at the crossings: gradient of the leaf corner trilinear ... use exact gradients only where the
    # crossings of a vertex spread (cheap estimate first: finite differences on the node lattice)
    nsum = np.zeros((nv, 3))
    np.add.at(nsum, vtx, Ng[rows])
    nbar = nsum / np.maximum(np.linalg.norm(nsum, axis=1, keepdims=True), 1e-12)
    dev = np.zeros(nv)
    np.maximum.at(dev, vtx, 1.0 - np.sum(Ng[rows] * nbar[vtx], 1))
    sus = dev > 1.0 - math.cos(math.radians(0.5 * crease_deg))
    cls = np.zeros(nv, np.int8)
    V = m.copy()
    if sus.any() and exact_normals:
        sel = np.isin(vtx, np.nonzero(sus)[0])
        r_need = np.unique(rows[sel])
        X = X.copy()
        X[r_need] = _root(name, T.segs[r_need])
        Nx = np.zeros_like(X)
        Nx[r_need] = gradient(name, X[r_need], e=0.002)
        vv, rr = vtx[sel], rows[sel]
        A = np.zeros((nv, 3, 3))
        bb = np.zeros((nv, 3))
        n_ = Nx[rr]
        np.add.at(A, vv, n_[:, :, None] * n_[:, None, :])
        np.add.at(bb, vv, n_ * np.sum(n_ * X[rr], 1)[:, None])
        ids = np.nonzero(sus)[0]
        lvl = np.concatenate([np.full(len(T.leaves[l]), l) for l in range(T.lmax + 1)])[used[ids]]
        size = T.h0 * (1 << lvl)
        for j, vi in enumerate(ids):
            Aj = A[vi]
            w, U = np.linalg.eigh(Aj)
            w, U = w[::-1], U[:, ::-1]
            if w[0] <= 0:
                continue
            rank = int(np.sum(w > 0.06 * w[0]))
            mp = m[vi]
            rhs = bb[vi] - Aj @ mp
            x = mp.copy()
            for k in range(rank):
                x = x + U[:, k] * (U[:, k] @ rhs) / w[k]
            if np.linalg.norm(x - mp) > 0.9 * size[j]:
                x = mp + (x - mp) * 0.9 * size[j] / np.linalg.norm(x - mp)
            V[vi] = x
            cls[vi] = 0 if rank <= 1 else (1 if rank == 2 else 2)
    # exact normals where the lattice estimate is unreliable: smooth vertices whose crossings' normals spread more than
    # 2 deg (next to a crease, tight rounds) -- the lattice differences straddle the crease there
    fix = (cls == 0) & (dev > 1.0 - math.cos(math.radians(2.0)))
    if fix.any() and exact_normals:
        nbar = nbar.copy()
        nbar[fix] = gradient(name, V[fix], e=0.002)
    return V, cls, Pi, nbar


def _root(name, S, iters=4):
    """Crossings on the edges S (k, 8: p0, p1, f0, f1) by regula falsi (Illinois) with exact field values."""
    p0, p1, f0, f1 = S[:, 0:3], S[:, 3:6], S[:, 6].copy(), S[:, 7].copy()
    a = np.zeros(len(S))
    b = np.ones(len(S))
    fa, fb = f0, f1
    side = np.zeros(len(S))
    for _ in range(iters):
        t = a - fa * (b - a) / (fb - fa)
        t = np.clip(t, a + 1e-6 * (b - a), b - 1e-6 * (b - a))
        ft = evaluate(name, p0 + t[:, None] * (p1 - p0))
        left = (ft < 0) == (fa < 0)
        # Illinois: halve the retained end's value when the same side is replaced twice
        a = np.where(left, t, a)
        fa_new = np.where(left, ft, fa)
        fb = np.where(left & (side == 1), 0.5 * fb, fb)
        b = np.where(~left, t, b)
        fb = np.where(~left, ft, fb)
        fa = np.where(~left & (side == -1), 0.5 * fa_new, fa_new)
        side = np.where(left, 1, -1)
    t = a - fa * (b - a) / (fb - fa)
    return p0 + np.clip(t, 0, 1)[:, None] * (p1 - p0)


def triangulate(Pi, V, cls):
    """Polygons (k, 4 vertex ids; repeated ids = triangles) -> triangles: a quad is split along the diagonal joining
    its two crease / corner vertices if exactly one diagonal does, else along the diagonal giving the better (larger
    minimum) angle."""
    Pi = np.asarray(Pi)
    tris = []
    # triangles: polygons with a repeated vertex (cyclic) -> drop the repeat
    rep = np.zeros(len(Pi), bool)
    for k in range(4):
        rep |= Pi[:, k] == Pi[:, (k + 1) % 4]
    Q = Pi[~rep]
    T3 = Pi[rep]
    for row in T3:
        u = [row[0]]
        for k in range(1, 4):
            if row[k] != u[-1]:
                u.append(row[k])
        if len(u) > 1 and u[-1] == u[0]:
            u.pop()
        if len(u) == 3:
            tris.append(u)
    a, b, c, d = Q[:, 0], Q[:, 1], Q[:, 2], Q[:, 3]
    cr = cls > 0
    d_ac = cr[a] & cr[c]
    d_bd = cr[b] & cr[d]

    def min_ang(i, j, k):
        A, B, C = V[i], V[j], V[k]
        out = np.full(len(i), np.pi)
        for P0, P1, P2 in ((A, B, C), (B, C, A), (C, A, B)):
            u = P1 - P0
            w = P2 - P0
            cs = np.sum(u * w, 1) / np.maximum(np.linalg.norm(u, axis=1) * np.linalg.norm(w, axis=1), 1e-30)
            out = np.minimum(out, np.arccos(np.clip(cs, -1, 1)))
        return out
    q_ac = np.minimum(min_ang(a, b, c), min_ang(a, c, d))
    q_bd = np.minimum(min_ang(a, b, d), min_ang(b, c, d))
    use_ac = np.where(d_ac & ~d_bd, True, np.where(d_bd & ~d_ac, False, q_ac >= q_bd))
    t1 = np.where(use_ac[:, None], np.c_[a, b, c], np.c_[a, b, d])
    t2 = np.where(use_ac[:, None], np.c_[a, c, d], np.c_[b, c, d])
    F = np.vstack([t1, t2] + ([np.array(tris)] if tris else []))
    ok = (F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])
    return F[ok]


def dc_mesh(name, box, h0=0.0625, lmax=6, lleaf=5, eps=0.004, zones=None, crease_deg=22.0, verbose=True):
    """Octree + dual contouring of field `name` over box: (V, F, cls, T)."""
    import time
    t0 = time.time()
    T = Octree(name, box, h0=h0, lmax=lmax, lleaf=lleaf, eps=eps, zones=zones)
    t1 = time.time()
    P, X, Ng = contour(T, crease_deg)
    V, cls, Pi, Nb = leaf_vertices(T, P, X, Ng, name, crease_deg)
    F = triangulate(Pi, V, cls)
    T.vnormals = Nb
    if verbose:
        nl = {l: len(T.leaves[l]) for l in range(T.lmax + 1)}
        print(f"  [{name}] octree {t1 - t0:.1f}s ({T.nodes.n_eval} evals; leaves {nl}; missing "
              f"{T.stats.get('missing', 0)}), contour {time.time() - t1:.1f}s: {len(V)} verts, {len(F)} tris, "
              f"crease {int((cls == 1).sum())}, corner {int((cls == 2).sum())}")
    return V, F, cls, T


def manifold_report(F):
    """(open edges, non-manifold edges) of a triangle set."""
    e = np.sort(np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), 1)
    _, cnt = np.unique(e, axis=0, return_counts=True)
    return int((cnt == 1).sum()), int((cnt > 2).sum())


# ============================================================================================ decimation helpers
def _face_normals(V, F):
    n = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    a = np.linalg.norm(n, axis=1)
    return n / np.maximum(a, 1e-30)[:, None], 0.5 * a


def _quadrics(V, F):
    """Per-vertex area-weighted plane quadrics (n, 4, 4) and area weights."""
    n, area = _face_normals(V, F)
    d = -np.sum(n * V[F[:, 0]], 1)
    p = np.c_[n, d]
    Qf = area[:, None, None] * p[:, :, None] * p[:, None, :]
    Q = np.zeros((len(V), 4, 4))
    W = np.zeros(len(V))
    for k in range(3):
        np.add.at(Q, F[:, k], Qf)
        np.add.at(W, F[:, k], area)
    return Q, W


def _qcost(Q, X):
    h = np.c_[X, np.ones(len(X))]
    return np.einsum("ni,nij,nj->n", h, Q, h)


def _edges(F):
    """Unique undirected edges (k, 2) (sorted), the two faces of each (k, 2; -1 if open) and the face -> edge map."""
    e = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    fi = np.tile(np.arange(len(F)), 3)
    es = np.sort(e, 1)
    key = es[:, 0].astype(np.int64) * (1 << 31) + es[:, 1]
    o = np.argsort(key, kind="stable")
    key, es, fi = key[o], es[o], fi[o]
    first = np.r_[True, key[1:] != key[:-1]]
    gid = np.cumsum(first) - 1
    E = es[first]
    EF = -np.ones((len(E), 2), np.int64)
    pos = np.r_[0, np.nonzero(np.diff(gid))[0] + 1]
    EF[:, 0] = fi[pos]
    second = ~first
    EF[gid[second], 1] = fi[second]
    return E, EF, key[first]


def _pn_bow(Pa, Pb, Na, Nb):
    e = Pb - Pa
    wab = np.sum(e * Na, 1)
    wba = -np.sum(e * Nb, 1)
    return np.linalg.norm((wab[:, None] * Na + wba[:, None] * Nb) / 8.0, axis=1)


def _min_angle(A, B, C):
    out = np.full(len(A), np.pi)
    for P0, P1, P2 in ((A, B, C), (B, C, A), (C, A, B)):
        u = P1 - P0
        w = P2 - P0
        cs = np.sum(u * w, 1) / np.maximum(np.linalg.norm(u, axis=1) * np.linalg.norm(w, axis=1), 1e-30)
        out = np.minimum(out, np.arccos(np.clip(cs, -1, 1)))
    return out


def _spread_min(x, E):
    m = x.copy()
    np.minimum.at(m, E[:, 0], x[E[:, 1]])
    np.minimum.at(m, E[:, 1], x[E[:, 0]])
    return m


def _spread_any(x, E):
    m = x.copy()
    m[E[:, 0][x[E[:, 1]]]] = True
    m[E[:, 1][x[E[:, 0]]]] = True
    return m


# ============================================================================================ quality report
def quality(name, V, F, N, samples=True):
    """Mesh checks: watertight / manifold (by position), min angle, normals vs the analytic gradient at the vertices
    (smooth ones), deviation of face centroids / edge midpoints from the zero level, PN bow and end-normal turn of the
    edges (cad.res interior criteria)."""
    key = np.round(V * 1e4).astype(np.int64)
    _, w = np.unique(key, axis=0, return_inverse=True)
    w = w.ravel()
    Fw = w[F]
    op, nm = manifold_report(Fw)
    ang = np.degrees(_min_angle(V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]))
    out = dict(tris=len(F), verts=len(V), open_edges=op, nonmanifold=nm, min_angle=float(ang.min()),
               slivers_lt5=int((ang < 5).sum()), angle_p1=float(np.percentile(ang, 1)))
    if samples:
        C = V[F].mean(1)
        fc = np.abs(evaluate(name, C))
        out.update(centroid_dev_p95=float(np.percentile(fc, 95)), centroid_dev_max=float(fc.max()))
    # edges: turn / bow with the corner normals of the faces
    e = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    Pa, Pb = V[e[:, 0]], V[e[:, 1]]
    Na, Nb = N[e[:, 0]], N[e[:, 1]]
    turn = np.degrees(np.arccos(np.clip(np.sum(Na * Nb, 1), -1, 1)))
    bow = _pn_bow(Pa, Pb, Na, Nb)
    bad = (turn > 20.0) & (bow > 0.02)
    out.update(edge_turn_p99=float(np.percentile(turn, 99)), refine_split_edges=int(bad.sum()),
               bow_max=float(bow.max()))
    return out


# ============================================================================================ the smooth moulding
class _NoTrimGrooves:
    """Context: yoke_geom._trim_face_grooves switched off (the trim face's V-grooves are built explicitly)."""

    def __enter__(self):
        self.f = G._trim_face_grooves
        G._trim_face_grooves = lambda U, H, A: np.full(np.shape(np.asarray(U, float)), 1e3)

    def __exit__(self, *a):
        G._trim_face_grooves = self.f


def moulding_smooth(U, H, A):
    """The black moulding of yoke_geom.moulding WITHOUT its sharp cuts: body + both grips joined by the rolling-ball
    round R neck[3] exactly as there, but neither the pads' pockets / grooves / beads (pad_finish) nor the trim face's
    V-grooves -- those are built as explicit crease-exact patches (model/yoke3d.py) and stitched into this surface along
    the frame's inner edge / on the trim face.  Every other face of the moulding is this field's zero level."""
    U, H, A = (np.asarray(x, float) for x in (U, H, A))
    with _NoTrimGrooves():
        r = float(G.T()["neck"][3])
        fb = G.body
        fo = lambda U_, H_, A_: G.grip_solid(U_, H_, A_, "out")           # noqa: E731
        fi = lambda U_, H_, A_: G.grip_solid(-U_, H_, A_, "in")           # noqa: E731
        b, go, gi = fb(U, H, A), fo(U, H, A), fi(U, H, A)
        out = np.minimum(b, np.minimum(go, gi))
        mo, mi = (b < r) & (go < r), (b < r) & (gi < r)
        if mo.any() or mi.any():
            m = mo | mi
            Um, Hm, Am = U[m], H[m], A[m]
            nb = G._unit_grad(fb, Um, Hm, Am, e=G.C_STENCIL)
            vals = out[m].copy()
            for mk, fg, gv in ((mo[m], fo, go[m]), (mi[m], fi, gi[m])):
                if mk.any():
                    ng = G._unit_grad(fg, Um[mk], Hm[mk], Am[mk], e=G.C_STENCIL)
                    ca = np.sum(nb[mk] * ng, -1)
                    vals[mk] = np.minimum(vals[mk], G.rmin_ang(b[m][mk], gv[mk], r, ca))
            out = out.copy()
            out[m] = vals
    return out


_FN["msmooth"] = moulding_smooth


# ============================================================================================ decimation, rev 2
DEC = dict(cone=12.0, turn=20.0, min_sag=0.02, dist=0.05, min_angle=5.0, lmax=10.0, bnd_tol=0.004, bnd_turn=12.0)


def _vf_csr(F, nv):
    fv = F.ravel()
    order = np.argsort(fv, kind="stable")
    start = np.r_[0, np.cumsum(np.bincount(fv, minlength=nv))]
    return start, order // 3


def _gather(start, items, ids):
    deg = start[ids + 1] - start[ids]
    k = np.repeat(np.arange(len(ids)), deg)
    off = np.arange(deg.sum()) - np.repeat(np.cumsum(deg) - deg, deg)
    return k, items[np.repeat(start[ids], deg) + off]


def decimate2(V, F, N, fixed=None, params=None, max_passes=500, verbose=False, reasons=False, flips=True,
              protect=None):
    """Half-edge-collapse simplification of a smooth surface mesh whose vertices lie ON the surface with their exact
    normals N (kept: a collapse a -> b removes a, never moves b).  Open boundaries (the cut edges where explicit patches
    join) are kept: a boundary vertex only slides along its boundary onto the next one, when it lies within bnd_tol of
    the new boundary segment and the boundary turns less than bnd_turn there.  A collapse is refused when a new face
    (1) flips or degenerates, (2) turns more than `cone` from any corner normal, (3) has a smaller angle than
    min(min_angle, the faces it replaces), (4) has an edge whose end normals turn more than `turn` while its PN bow
    exceeds `min_sag` (cad.res's interior refinement criterion: the result is a fixed point of cad.refine), (5) an edge
    longer than lmax; (6) the area-weighted plane distance (QEM) exceeds `dist`; (7) the link condition fails.
    Independent collapses (2-ring) per pass, cheapest first.  Returns (V, F, N, kept vertex ids)."""
    import time
    p = dict(DEC, **(params or {}))
    t0 = time.time()
    nv = len(V)
    V, F, N = np.asarray(V, float), np.asarray(F, np.int64).copy(), _unit(np.asarray(N, float))
    fixed = np.zeros(nv, bool) if fixed is None else np.asarray(fixed, bool).copy()
    Q, W = _quadrics(V, F)
    cc, ct = math.cos(math.radians(p["cone"])), math.cos(math.radians(p["turn"]))
    ma = math.radians(p["min_angle"])
    alive = np.ones(nv, bool)
    n0 = len(F)
    stats = {}
    for it in range(max_passes):
        FN, FA = _face_normals(V, F)
        E, EF, ekey = _edges(F)
        bnd_e = EF[:, 1] < 0
        bv = np.zeros(nv, bool)
        bv[E[bnd_e].ravel()] = True
        A_ = np.r_[E[:, 0], E[:, 1]]
        B_ = np.r_[E[:, 1], E[:, 0]]
        be2 = np.r_[bnd_e, bnd_e]
        ok = alive[A_] & ~fixed[A_] & np.where(bv[A_], be2, True)
        A_, B_, be2 = A_[ok], B_[ok], be2[ok]
        cost = _qcost(Q[A_] + Q[B_], V[B_]) / np.maximum(W[A_] + W[B_], 1e-30)
        cost = cost + 1e-9 * np.linalg.norm(V[A_] - V[B_], axis=1)
        o = np.lexsort((cost, A_))
        A_, B_, cost, be2 = A_[o], B_[o], cost[o], be2[o]
        first = np.r_[True, A_[1:] != A_[:-1]]
        idx = np.arange(len(A_))
        rank = idx - np.maximum.accumulate(np.where(first, idx, 0))
        sel = (rank < 4) & (cost <= p["dist"] ** 2)
        A_, B_, cost, be2, rank = A_[sel], B_[sel], cost[sel], be2[sel], rank[sel]
        if not len(A_):
            break
        best = np.full(nv, np.inf)
        tgt = -np.ones(nv, np.int64)
        for r in range(4):                                  # the cheapest valid target per vertex, rank by rank
            m = (rank == r) & ~np.isfinite(best[A_])
            if not m.any():
                continue
            valid, why = _valid2(V, F, FN, N, bv, A_[m], B_[m], be2[m], E, ekey, p, cc, ct, ma)
            if reasons:
                for kk, v in why.items():
                    stats[kk] = stats.get(kk, 0) + int(np.sum(v))
            a, b, c = A_[m][valid], B_[m][valid], cost[m][valid]
            best[a] = c
            tgt[a] = b
        cand = np.isfinite(best)
        if not cand.any():
            break
        pri0 = np.where(cand, best, np.inf) + 1e-15 * ((np.arange(nv) * 2654435761) % 1000003)
        avail = cand.copy()
        go = np.zeros(nv, bool)
        for _r in range(40):
            if not avail.any():
                break
            pri = np.where(avail, pri0, np.inf)
            pick = avail & (pri <= _spread_min(_spread_min(pri, E), E))
            go |= pick
            avail &= ~_spread_any(_spread_any(pick, E), E)
        a, b = np.nonzero(go)[0], tgt[go]
        remap = np.arange(nv)
        remap[a] = b
        F = remap[F]
        F = F[(F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])]
        Q[b] += Q[a]
        W[b] += W[a]
        alive[a] = False
        if flips:
            F, nfl = flip_pass(V, F, N, p, rounds=2, protect=protect)
        if verbose and it % 10 == 0:
            print(f"    pass {it}: {len(F)} faces (-{len(a)}), {time.time() - t0:.1f}s", flush=True)
        if len(a) < max(2, 0.0002 * alive.sum()):
            break
    used = np.zeros(nv, bool)
    used[F.ravel()] = True
    rm = -np.ones(nv, np.int64)
    rm[used] = np.arange(used.sum())
    if verbose:
        print(f"    decimated {n0} -> {len(F)} faces in {it + 1} passes, {time.time() - t0:.1f}s"
              + (f"; refusals {stats}" if reasons else ""), flush=True)
    return V[used], rm[F], N[used], np.nonzero(used)[0]


def _unit(v):
    v = np.asarray(v, float)
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-15)


def _valid2(V, F, FN, N, bv, a, b, be, E, ekey, p, cc, ct, ma):
    nv = len(V)
    start, items = _vf_csr(F, nv)
    k, fid = _gather(start, items, a)
    Fa = F[fid]
    aa, bb = a[k], b[k]
    has_b = (Fa == bb[:, None]).any(1)
    keep = ~has_b
    Fn = np.where(Fa == aa[:, None], bb[:, None], Fa)
    P0, P1, P2 = V[Fn[:, 0]], V[Fn[:, 1]], V[Fn[:, 2]]
    nn = np.cross(P1 - P0, P2 - P0)
    ar = np.linalg.norm(nn, axis=1)
    nn = nn / np.maximum(ar, 1e-30)[:, None]
    why = {}

    def flag(name, bad):
        bad = bad & keep
        vb = np.zeros(len(a), bool)
        np.logical_or.at(vb, k, bad)
        why[name] = vb
        return vb
    r_flip = flag("flip", (ar < 1e-9) | (np.sum(nn * FN[fid], 1) < 0.2))
    cone = np.zeros(len(k), bool)
    for j in range(3):
        cone |= np.sum(nn * N[Fn[:, j]], 1) < (cc[Fn[:, j]] if np.ndim(cc) else cc)     # cc / ct: scalars or per vertex
    r_cone = flag("cone", cone)
    mn_new = _min_angle(P0, P1, P2)
    mn_old = _min_angle(V[Fa[:, 0]], V[Fa[:, 1]], V[Fa[:, 2]])
    r_ang = flag("angle", mn_new < np.minimum(ma, mn_old - 1e-9))
    bad_e = np.zeros(len(k), bool)
    bad_l = np.zeros(len(k), bool)
    for j in range(3):
        x = Fn[:, j]
        s = x != bb
        Pb, Px = V[bb], V[x]
        L = np.linalg.norm(Px - Pb, axis=1)
        turn = np.sum(N[bb] * N[x], 1)
        bow = _pn_bow(Pb, Px, N[bb], N[x])
        bad_e |= s & (turn < (np.maximum(ct[bb], ct[x]) if np.ndim(ct) else ct)) & (bow > p["min_sag"])
        bad_l |= s & (L > p["lmax"])
    r_turn = flag("turn", bad_e)
    r_len = flag("length", bad_l)
    # link condition: common neighbours of a and b == 2 (interior edge) / 1 (boundary edge)
    E0, E1 = np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]]
    o = np.argsort(E0, kind="stable")
    E0, E1 = E0[o], E1[o]
    est = np.r_[0, np.cumsum(np.bincount(E0, minlength=nv))]
    kk, xn = _gather(est, E1, a)
    bq = b[kk]
    q = np.sort(np.c_[bq, xn], 1)
    qk = q[:, 0].astype(np.int64) * (1 << 31) + q[:, 1]
    i = np.minimum(np.searchsorted(ekey, qk), len(ekey) - 1)
    common = (ekey[i] == qk) & (xn != bq)
    nc = np.bincount(kk, weights=common.astype(float), minlength=len(a))
    r_link = nc != np.where(be, 1, 2)
    # an interior vertex onto a boundary vertex must not create a second boundary path (a and b both on the boundary
    # through a non-boundary edge)
    r_link |= bv[a] & ~be
    why["link"] = r_link
    # boundary slide: a within bnd_tol of the segment b -> c (c = a's other boundary neighbour), small turn at a
    r_bnd = np.zeros(len(a), bool)
    ib = np.nonzero(be)[0]
    if len(ib):
        # a's boundary neighbours
        bn = _boundary_neighbours(F, nv)
        c = np.where(bn[a[ib], 0] == b[ib], bn[a[ib], 1], bn[a[ib], 0])
        Pa, Pb_, Pc = V[a[ib]], V[b[ib]], V[c]
        d = Pc - Pb_
        t = np.clip(np.sum((Pa - Pb_) * d, 1) / np.maximum(np.sum(d * d, 1), 1e-30), 0, 1)
        dist = np.linalg.norm(Pa - (Pb_ + t[:, None] * d), axis=1)
        u1 = _unit(Pa - Pb_)
        u2 = _unit(Pc - Pa)
        r_bnd[ib] = (dist > p["bnd_tol"]) | (np.sum(u1 * u2, 1) < math.cos(math.radians(p["bnd_turn"]))) | (c < 0) | \
            (np.linalg.norm(d, axis=1) > p.get("bnd_lmax", 1e9))
    why["boundary"] = r_bnd
    bad = r_flip | r_cone | r_ang | r_turn | r_len | r_link | r_bnd
    return ~bad, why


def _boundary_neighbours(F, nv):
    """(nv, 2) the two boundary neighbours of each boundary vertex (-1 elsewhere)."""
    E, EF, _ = _edges(F)
    be = E[EF[:, 1] < 0]
    out = -np.ones((nv, 2), np.int64)
    for col in (0, 1):
        v, w = be[:, col], be[:, 1 - col]
        free = out[v, 0] < 0
        out[v[free], 0] = w[free]
        rest = ~free
        out[v[rest], 1] = w[rest]
    return out


def flip_pass(V, F, N, p=None, rounds=3, protect=None):
    """Edge flips that raise the smaller minimum angle of the two faces of an interior edge (a Delaunay-like
    improvement on the surface): flipped only where the two new faces stay within `cone` of their corner normals,
    turn < 60 deg against the old faces, and the new edge passes the turn / bow criterion; independent flips per round
    (no two sharing a face).  protect: (k, 2) edges never flipped (creases / patch seams)."""
    p = dict(DEC, **(p or {}))
    cc, ct = math.cos(math.radians(p["cone"])), math.cos(math.radians(p["turn"]))
    F = F.copy()
    pk = None
    if protect is not None and len(protect):
        ps = np.sort(np.asarray(protect, np.int64), 1)
        pk = np.sort(ps[:, 0] * (1 << 31) + ps[:, 1])
    total = 0
    for _ in range(rounds):
        E, EF, ekey = _edges(F)
        m = EF[:, 1] >= 0
        if pk is not None:
            i = np.minimum(np.searchsorted(pk, ekey), len(pk) - 1)
            m &= pk[i] != ekey
        e = np.nonzero(m)[0]
        a, b = E[e, 0], E[e, 1]
        f1, f2 = EF[e, 0], EF[e, 1]
        c = F[f1][np.arange(len(e)), np.argmax((F[f1] != a[:, None]) & (F[f1] != b[:, None]), 1)]
        d = F[f2][np.arange(len(e)), np.argmax((F[f2] != a[:, None]) & (F[f2] != b[:, None]), 1)]
        ok = c != d
        # the new edge must not exist already
        q = np.sort(np.c_[c, d], 1)
        qk = q[:, 0] * (1 << 31) + q[:, 1]
        j = np.minimum(np.searchsorted(ekey, qk), len(ekey) - 1)
        ok &= ekey[j] != qk
        old = np.minimum(_min_angle(V[F[f1, 0]], V[F[f1, 1]], V[F[f1, 2]]), _min_angle(V[F[f2, 0]], V[F[f2, 1]], V[F[f2, 2]]))
        # orientation of the old faces decides the new ones' winding: f1 = (a, b, c) in some rotation
        t1 = np.c_[c, d, b]
        t2 = np.c_[d, c, a]
        o1 = F[f1]
        # make (a, b) appear in f1's order as a -> b; if not, swap the roles
        pos_a = np.argmax(o1 == a[:, None], 1)
        nxt = o1[np.arange(len(e)), (pos_a + 1) % 3]
        fwd = nxt == b                                       # f1 = (a, b, c)
        t1 = np.where(fwd[:, None], np.c_[a, d, c], np.c_[b, d, c])
        t2 = np.where(fwd[:, None], np.c_[b, c, d], np.c_[a, c, d])
        new = np.minimum(_min_angle(V[t1[:, 0]], V[t1[:, 1]], V[t1[:, 2]]), _min_angle(V[t2[:, 0]], V[t2[:, 1]], V[t2[:, 2]]))
        ok &= new > old + math.radians(2.0)
        fn1, a1 = _face_normals(V, t1)
        fn2, a2 = _face_normals(V, t2)
        on1, _ = _face_normals(V, F[f1])
        on2, _ = _face_normals(V, F[f2])
        ok &= (a1 > 1e-10) & (a2 > 1e-10)
        ok &= (np.sum(fn1 * on1, 1) > 0.5) & (np.sum(fn2 * on2, 1) > 0.5) & (np.sum(fn1 * fn2, 1) > 0.5)
        for T, fn in ((t1, fn1), (t2, fn2)):
            for k in range(3):
                ok &= np.sum(fn * N[T[:, k]], 1) >= cc
        turn = np.sum(N[c] * N[d], 1)
        ok &= ~((turn < ct) & (_pn_bow(V[c], V[d], N[c], N[d]) > p["min_sag"]))
        e, f1, f2, t1, t2 = e[ok], f1[ok], f2[ok], t1[ok], t2[ok]
        if not len(e):
            break
        gain = (new - old)[ok] + 1e-9 * np.arange(len(e)) / max(len(e), 1)
        # independent: no face used twice -- a flip is taken where its gain is the best of both its faces
        take = np.zeros(len(e), bool)
        avail = np.ones(len(e), bool)
        for _r in range(6):
            g = np.where(avail, gain, -np.inf)
            fb = np.full(len(F), -np.inf)
            np.maximum.at(fb, f1, g)
            np.maximum.at(fb, f2, g)
            t = avail & (g >= fb[f1]) & (g >= fb[f2])
            take |= t
            usedf = np.zeros(len(F), bool)
            usedf[f1[take]] = True
            usedf[f2[take]] = True
            avail &= ~usedf[f1] & ~usedf[f2]
            if not avail.any():
                break
        take = np.nonzero(take)[0]
        F[f1[take]] = t1[take]
        F[f2[take]] = t2[take]
        total += len(take)
    return F, total


# ============================================================================================ repair / project / refine
def fix_nonmanifold(V, F, rounds=4):
    """Remove the faces round every non-manifold edge (and vertex fans that touch them) and close each hole by a fan
    from its centroid (projected later): DC's rare octree-transition polygons that share an edge twice."""
    V = np.asarray(V, float)
    F = np.asarray(F, np.int64)
    for _ in range(rounds):
        e = np.sort(np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), 1)
        key = e[:, 0] * (1 << 31) + e[:, 1]
        u, inv, cnt = np.unique(key, return_inverse=True, return_counts=True)
        bad_e = cnt[inv] != 2
        bad_v = np.unique(e[bad_e].ravel())
        if not len(bad_v):
            break
        ring = np.isin(F, bad_v).any(1)
        rv = np.unique(F[ring].ravel())
        drop = np.isin(F, rv).any(1)                    # the 1-ring of the bad vertices: room for a clean hole
        F = F[~drop]
        from cad.mesh import Mesh, boundary_loops
        loops = boundary_loops(Mesh(V, F, N=np.zeros_like(V)))
        newV, newF = [V], [F]
        o = len(V)
        for L in loops:
            c = V[L].mean(0)
            newV.append(c[None])
            k = len(L)
            newF.append(np.c_[L, np.roll(L, -1), np.full(k, o)])
            o += 1
        V = np.vstack(newV)
        F = np.vstack(newF)
    return V, F


def project_exact(name, P, iters=5, e=0.003):
    """Newton projection onto the zero level of field `name` + the unit gradient there: (P, N, |f|)."""
    P = np.asarray(P, float).copy()
    for _ in range(iters):
        f = evaluate(name, P)
        g = _grad_raw(name, P, e)
        gg = np.maximum(np.sum(g * g, 1), 1e-12)
        P = P - (f / gg)[:, None] * g
    f = evaluate(name, P)
    return P, _unit(_grad_raw(name, P, e)), np.abs(f)


def _grad_raw(name, P, e):
    n = len(P)
    if n == 0:
        return np.zeros((0, 3))
    Q = np.concatenate([P + d for d in (np.array([e, 0, 0]), np.array([-e, 0, 0]), np.array([0, e, 0]),
                                         np.array([0, -e, 0]), np.array([0, 0, e]), np.array([0, 0, -e]))])
    v = evaluate(name, Q).reshape(6, n)
    return np.stack([v[0] - v[1], v[2] - v[3], v[4] - v[5]], -1) / (2 * e)


def refine_split(name, V, F, N, p=None, max_rounds=8, protect=None, verbose=False):
    """Split every interior edge that fails the turn / bow criterion (cad.res interior: end normals turn > `turn` while
    the PN bow > `min_sag`, or bow > 0.3) at its PN midpoint projected exactly onto the field (exact normal); one
    independent set of edges per round (1 -> 2 splits of both faces).  Returns (V, F, N)."""
    from cad.refine import pn_midpoint_bow
    p = dict(DEC, **(p or {}))
    ct = math.cos(math.radians(p["turn"]))
    V, F, N = V.copy(), F.copy(), N.copy()
    for rd in range(max_rounds):
        E, EF, ekey = _edges(F)
        Pa, Pb, Na, Nb = V[E[:, 0]], V[E[:, 1]], N[E[:, 0]], N[E[:, 1]]
        bow = _pn_bow(Pa, Pb, Na, Nb)
        bad = (((np.sum(Na * Nb, 1) < ct) & (bow > p["min_sag"])) | (bow > 0.3)) & (EF[:, 1] >= 0)
        if protect is not None:
            bad &= ~protect(E)
        idx = np.nonzero(bad)[0]
        if not len(idx):
            break
        # independent: no face in two splits, longest first
        L = np.linalg.norm(Pa[idx] - Pb[idx], axis=1)
        o = idx[np.argsort(-L)]
        used = np.zeros(len(F), bool)
        take = []
        for i in o:
            f1, f2 = EF[i]
            if not used[f1] and not used[f2]:
                used[f1] = used[f2] = True
                take.append(i)
        take = np.array(take, int)
        a, b = E[take, 0], E[take, 1]
        mid = 0.5 * (V[a] + V[b]) + pn_midpoint_bow(V[a], V[b], N[a], N[b])
        Pm, Nm, _ = project_exact(name, mid, iters=4)
        nid = len(V) + np.arange(len(take))
        V = np.vstack([V, Pm])
        N = np.vstack([N, Nm])
        newF = []
        keepF = np.ones(len(F), bool)
        for t, (i, m) in enumerate(zip(take, nid)):
            for f in EF[i]:
                tri = F[f]
                j = int(np.nonzero((tri != a[t]) & (tri != b[t]))[0][0])
                c = tri[j]
                # the face as (x, y, c) with x -> y the split edge in face order
                x, y = tri[(j + 1) % 3], tri[(j + 2) % 3]
                newF += [(x, m, c), (m, y, c)]
                keepF[f] = False
        F = np.vstack([F[keepF], np.array(newF, np.int64)])
        if verbose:
            print(f"    refine round {rd}: {len(take)} splits -> {len(F)} faces", flush=True)
    return V, F, N


# ============================================================================================ decimation, rev 3: highlights
def _group_pairs(cs, cf):
    """All pairs (i, j) with cs[i] == cf[j] (group ids of the samples / of the faces): index arrays (i, j)."""
    o_s = np.argsort(cs, kind="stable")
    o_f = np.argsort(cf, kind="stable")
    g = np.union1d(cs, cf)
    nf = np.bincount(np.searchsorted(g, cf), minlength=len(g))
    f0 = np.r_[0, np.cumsum(nf)[:-1]]
    gi = np.searchsorted(g, cs[o_s])
    rep = nf[gi]
    si = np.repeat(o_s, rep)
    off = np.arange(int(rep.sum())) - np.repeat(np.cumsum(rep) - rep, rep)
    fj = o_f[np.repeat(f0[gi], rep) + off]
    return si, fj


def _pt_tri(P, A, B, C):
    """Barycentrics (n, 3) of the closest points of the triangles (A, B, C) to the points P (all (n, 3))."""
    ab, ac, ap = B - A, C - A, P - A
    d1, d2 = np.sum(ab * ap, 1), np.sum(ac * ap, 1)
    bp = P - B
    d3, d4 = np.sum(ab * bp, 1), np.sum(ac * bp, 1)
    cp = P - C
    d5, d6 = np.sum(ab * cp, 1), np.sum(ac * cp, 1)
    va, vb, vc = d3 * d6 - d5 * d4, d5 * d2 - d1 * d6, d1 * d4 - d3 * d2
    den = va + vb + vc
    den = np.where(np.abs(den) < 1e-30, 1e-30, den)
    W = np.c_[np.zeros(len(P)), vb / den, vc / den]
    W[:, 0] = 1.0 - W[:, 1] - W[:, 2]
    out = W.min(1) < 0.0
    if out.any():                                           # outside the triangle: the nearest point of its edges
        best = np.full(len(P), np.inf)
        Wo = np.zeros((len(P), 3))
        T = (A, B, C)
        for i, j in ((0, 1), (1, 2), (2, 0)):
            d = T[j] - T[i]
            t = np.clip(np.sum((P - T[i]) * d, 1) / np.maximum(np.sum(d * d, 1), 1e-30), 0.0, 1.0)
            dd = np.sum((P - T[i] - t[:, None] * d) ** 2, 1)
            b = dd < best
            best = np.where(b, dd, best)
            w = np.zeros((len(P), 3))
            w[:, i], w[:, j] = 1.0 - t, t
            Wo = np.where(b[:, None], w, Wo)
        W = np.where(out[:, None], Wo, W)
    return W


DECI = dict(sdist=0.15)   # the highlight decimation's sample distance bound (mm: the moulding's QEM bound)


def decimate_interp(V, F, N, tol_s, fixed=None, params=None, max_passes=500, verbose=False):
    """decimate2 with the HIGHLIGHT criterion built in (2026-10-10: decimating to QEM / cone bounds first and refining
    after spent the budget on the wrong faces -- 43 % of the frame's area had its interpolated normals > 2 deg off).
    Every input vertex is a SAMPLE (position, exact normal, tolerance tol_s deg) owned by the face it lies on; a
    collapse a -> b passing decimate2's tests (flip, cone, angle, turn / bow, length, link, boundary slide) is also
    refused when a sample owned by a face round a -- the only faces it changes -- would lie farther than sdist (DECI, or
    params: a scalar or one bound per sample) from the new faces, or the new faces' corner normals interpolated at its nearest point would miss its exact normal by
    more than its tolerance.  cone / turn / dist / sdist may be given per vertex.  An accepted collapse hands those samples to the nearest new face.  No flips (they would
    move faces over samples unchecked).  Returns (V, F, N, kept vertex ids)."""
    import time
    p = dict(DEC, **DECI)
    p.update(params or {})
    t0 = time.time()
    nv = len(V)
    V, F, N = np.asarray(V, float), np.asarray(F, np.int64).copy(), _unit(np.asarray(N, float))
    fixed = np.zeros(nv, bool) if fixed is None else np.asarray(fixed, bool).copy()
    SP, SN = V.copy(), N.copy()
    ctol = np.cos(np.radians(np.minimum(np.broadcast_to(np.asarray(tol_s, float), (nv,)), 179.0)))
    sd2 = np.broadcast_to(np.asarray(p["sdist"], float), (nv,)) ** 2      # a scalar or one bound per sample
    qd2 = np.broadcast_to(np.asarray(p["dist"], float), (nv,)) ** 2       # the QEM bound: likewise per vertex
    start, items = _vf_csr(F, nv)
    owner = items[start[:-1]].copy()                         # each vertex's own sample: on its first face
    Q, W = _quadrics(V, F)
    cc = np.cos(np.radians(np.broadcast_to(np.asarray(p["cone"], float), (nv,))))      # per vertex (or one value)
    ct = np.cos(np.radians(np.broadcast_to(np.asarray(p["turn"], float), (nv,))))
    ma = math.radians(p["min_angle"])
    alive = np.ones(nv, bool)
    n0 = len(F)
    it = 0
    for it in range(max_passes):
        FN, FA = _face_normals(V, F)
        E, EF, ekey = _edges(F)
        bnd_e = EF[:, 1] < 0
        bv = np.zeros(nv, bool)
        bv[E[bnd_e].ravel()] = True
        A_ = np.r_[E[:, 0], E[:, 1]]
        B_ = np.r_[E[:, 1], E[:, 0]]
        be2 = np.r_[bnd_e, bnd_e]
        ok = alive[A_] & ~fixed[A_] & np.where(bv[A_], be2, True)
        A_, B_, be2 = A_[ok], B_[ok], be2[ok]
        cost = _qcost(Q[A_] + Q[B_], V[B_]) / np.maximum(W[A_] + W[B_], 1e-30)
        cost = cost + 1e-9 * np.linalg.norm(V[A_] - V[B_], axis=1)
        o = np.lexsort((cost, A_))
        A_, B_, cost, be2 = A_[o], B_[o], cost[o], be2[o]
        first = np.r_[True, A_[1:] != A_[:-1]]
        idx = np.arange(len(A_))
        rank = idx - np.maximum.accumulate(np.where(first, idx, 0))
        sel = (rank < 4) & (cost <= qd2[A_])
        A_, B_, cost, be2, rank = A_[sel], B_[sel], cost[sel], be2[sel], rank[sel]
        if not len(A_):
            break
        fstart, fitems = _vf_csr(F, nv)
        so = np.argsort(owner, kind="stable")                # samples by owner face
        sstart = np.r_[0, np.cumsum(np.bincount(owner, minlength=len(F)))]
        best = np.full(nv, np.inf)
        tgt = -np.ones(nv, np.int64)
        AV, AS, AF = [], [], []                               # sample hand-over of the valid candidates
        for r in range(4):
            m = (rank == r) & ~np.isfinite(best[A_])
            if not m.any():
                continue
            a, b, c, be = A_[m], B_[m], cost[m], be2[m]
            valid, _ = _valid2(V, F, FN, N, bv, a, b, be, E, ekey, p, cc, ct, ma)
            a, b, c = a[valid], b[valid], c[valid]
            if not len(a):
                continue
            k, fid = _gather(fstart, fitems, a)               # the faces round a (candidate k) and their new form
            Fa = F[fid]
            Fn = np.where(Fa == a[k][:, None], b[k][:, None], Fa)
            live = np.nonzero(~(Fa == b[k][:, None]).any(1))[0]
            ke, sid = _gather(sstart, so, fid)                # the samples those faces own
            ks = k[ke]
            si, fj = _group_pairs(ks, k[live])
            fl = live[fj]
            Tn = Fn[fl]
            S = sid[si]
            Wb = _pt_tri(SP[S], V[Tn[:, 0]], V[Tn[:, 1]], V[Tn[:, 2]])
            d2 = np.sum((SP[S] - np.einsum("nk,nkd->nd", Wb, V[Tn])) ** 2, 1)
            ordr = np.lexsort((d2, si))                       # per sample entry its nearest new face
            firstp = np.r_[True, si[ordr][1:] != si[ordr][:-1]] if len(ordr) else np.zeros(0, bool)
            bp = ordr[firstp]
            bs = si[bp]
            Ni = _unit(np.einsum("nk,nkd->nd", Wb[bp], N[Tn[bp]]))
            okv = (d2[bp] <= sd2[S[bp]]) & (np.sum(Ni * SN[S[bp]], 1) >= ctol[S[bp]])
            bad = np.zeros(len(a), bool)
            np.logical_or.at(bad, ks[bs], ~okv)
            has = np.zeros(len(ks), bool)
            has[bs] = True
            bad[np.unique(ks[~has])] = True                   # a sample with no surviving face round a
            good = ~bad
            best[a[good]] = c[good]
            tgt[a[good]] = b[good]
            kp = good[ks[bs]]
            AV.append(a[ks[bs][kp]])
            AS.append(S[bp][kp])
            AF.append(fid[fl[bp]][kp])
        cand = np.isfinite(best)
        if not cand.any():
            break
        pri0 = np.where(cand, best, np.inf) + 1e-15 * ((np.arange(nv) * 2654435761) % 1000003)
        avail = cand.copy()
        go = np.zeros(nv, bool)
        for _r in range(40):
            if not avail.any():
                break
            pri = np.where(avail, pri0, np.inf)
            pick = avail & (pri <= _spread_min(_spread_min(pri, E), E))
            go |= pick
            avail &= ~_spread_any(_spread_any(pick, E), E)
        a, b = np.nonzero(go)[0], tgt[go]
        if AV:                                                # re-home the samples of the accepted collapses
            av, as_, af = np.concatenate(AV), np.concatenate(AS), np.concatenate(AF)
            mm = go[av]
            owner[as_[mm]] = af[mm]
        remap = np.arange(nv)
        remap[a] = b
        F = remap[F]
        keepf = (F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])
        if not keepf[owner].all():
            raise RuntimeError("decimate_interp: a sample left on a vanished face")
        owner = (np.cumsum(keepf) - 1)[owner]
        F = F[keepf]
        Q[b] += Q[a]
        W[b] += W[a]
        alive[a] = False
        if verbose and it % 10 == 0:
            print(f"    pass {it}: {len(F)} faces (-{len(a)}), {time.time() - t0:.1f}s", flush=True)
        if len(a) < max(2, 0.0002 * alive.sum()):
            break
    used = np.zeros(nv, bool)
    used[F.ravel()] = True
    rm = -np.ones(nv, np.int64)
    rm[used] = np.arange(used.sum())
    if verbose:
        print(f"    decimated {n0} -> {len(F)} faces in {it + 1} passes, {time.time() - t0:.1f}s", flush=True)
    return V[used], rm[F], N[used], np.nonzero(used)[0]


# ============================================================================================ shading refinement
# the HIGHLIGHT criterion: a viewer shades a triangle with its vertex normals interpolated linearly (then normalised); where
# that interpolation departs from the exact normal of the surface under it -- at an edge's midpoint or a face's centroid
# --, the highlights on the satin black wobble into triangle-sized blotches (zebra 2026-10-10 of the frame decimated to
# QEM / cone bounds alone: 43 % of its area over 2 deg, 29 % over 4, in 8-14 mm faces).  decimate_interp keeps it within
# a tolerance; interp_errors / highlight_report measure it.


def _angle_deg(a, b):
    return np.degrees(np.arccos(np.clip(np.sum(_unit(a) * _unit(b), -1), -1.0, 1.0)))


def interp_errors(name, V, F, N, iters=3, cache=None):
    """Per edge (E order of _edges) the angle (deg) between the normalised mean of its end normals and the exact normal at
    its projected PN midpoint (+ that point and normal); per face the same at its projected centroid against the mean of
    its three normals.  Returns (E, EF, e_err, Pm, Nm, f_err).  cache: a dict kept between calls on a growing mesh
    (vertex ids never change): edges / faces measured before are not projected again."""
    from cad.refine import pn_midpoint_bow
    E, EF, ekey = _edges(F)
    a, b = E[:, 0], E[:, 1]
    fs = np.sort(F, 1).astype(np.int64)
    fkey = (fs[:, 0] * (1 << 21) + fs[:, 1]) * (1 << 21) + fs[:, 2]
    cache = {} if cache is None else cache
    ce = cache.setdefault("e", {})
    cf = cache.setdefault("f", {})
    new_e = np.array([k not in ce for k in ekey.tolist()], bool)
    new_f = np.array([k not in cf for k in fkey.tolist()], bool)
    ie, jf = np.nonzero(new_e)[0], np.nonzero(new_f)[0]
    if len(ie) or len(jf):
        mid = 0.5 * (V[a[ie]] + V[b[ie]]) + pn_midpoint_bow(V[a[ie]], V[b[ie]], N[a[ie]], N[b[ie]])
        C = V[F[jf]].mean(1)
        P, Ng, _ = project_exact(name, np.vstack([mid, C]), iters=iters)
        Pm_, Nm_ = P[:len(ie)], Ng[:len(ie)]
        ee = _angle_deg(Nm_, N[a[ie]] + N[b[ie]])
        fe = _angle_deg(Ng[len(ie):], N[F[jf]].sum(1))
        # a projection that jumped (another sheet / a kink of the field) is no measurement
        L = np.linalg.norm(V[a[ie]] - V[b[ie]], axis=1)
        ee = np.where(np.linalg.norm(Pm_ - mid, axis=1) < 0.25 + 0.1 * L, ee, 0.0)
        fe = np.where(np.linalg.norm(P[len(ie):] - C, axis=1) < 0.4, fe, 0.0)
        for k, x, p_, n_ in zip(ekey[ie].tolist(), ee, Pm_, Nm_):
            ce[k] = (x, p_, n_)
        for k, x in zip(fkey[jf].tolist(), fe):
            cf[k] = x
    rec = [ce[k] for k in ekey.tolist()]
    e_err = np.array([r[0] for r in rec])
    Pm = np.array([r[1] for r in rec])
    Nm = np.array([r[2] for r in rec])
    f_err = np.array([cf[k] for k in fkey.tolist()])
    return E, EF, e_err, Pm, Nm, f_err


def highlight_report(name, V, F, N, tol_k=None, face_mask=None):
    """Area-weighted percentiles of the highlight error (deg; interp_errors: an edge's midpoint / a face's centroid,
    each face its worst) over the faces with tol_k(centroids, face normals) == 1 (all faces without tol_k) and in
    face_mask (optional): dict(p50, p95, over2, over4 (% of the area), faces, and unweighted -- rev O, 3-D judges r2
    CR2-01: small rounds averaged away by area -- fp95 (deg), fover4 (% of the faces))."""
    E, EF, e_err, _, _, f_err = interp_errors(name, V, F, N)
    ef = f_err.copy()
    for col in (0, 1):
        f = EF[:, col]
        ok = f >= 0
        np.maximum.at(ef, f[ok], e_err[ok])
    fn, A = _face_normals(V, F)
    m = np.ones(len(F), bool) if tol_k is None else np.asarray(tol_k(V[F].mean(1), fn)) == 1.0
    if face_mask is not None:
        m &= np.asarray(face_mask, bool)
    x, w = ef[m], A[m] / max(A[m].sum(), 1e-30)
    o = np.argsort(x)
    cw = np.cumsum(w[o])
    pick = lambda q: float(x[o][min(np.searchsorted(cw, q), len(x) - 1)]) if len(x) else 0.0      # noqa: E731
    return dict(p50=pick(0.5), p95=pick(0.95), over2=float(100 * w[x > 2].sum()), over4=float(100 * w[x > 4].sum()),
                faces=int(m.sum()), fp95=float(np.percentile(x, 95)) if len(x) else 0.0,
                fover4=float(100 * (x > 4).mean()) if len(x) else 0.0)


# ============================================================================================ the moulding, end to end
DC_EPS = 0.02           # octree split: the field over a cell's 3 x 3 x 3 lattice departs from trilinear by > this (mm)
DC_VERSION = "dc1"       # bump when the octree / dual contouring code changes (the stage caches are keyed by it)
DEC_VERSION = "dec1"     # ... the decimation code


def stage_cached(stage, key, fn):
    """fn() cached on disk (out/tmp/yoke_mesh_cache/<stage>_<hash>.pkl) under `key` (the design key + the stage's
    parameters and code version): the expensive dual contouring and decimation of the moulding are not redone when
    only later stages change."""
    import pickle
    k = hashlib.sha1(repr(key).encode()).hexdigest()[:16]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    f = CACHE_DIR / f"{stage}_{k}.pkl"
    if f.exists():
        try:
            return pickle.loads(f.read_bytes())
        except Exception:                                    # noqa: BLE001
            pass
    val = fn()
    tmp = f.with_suffix(".tmp")
    tmp.write_bytes(pickle.dumps(val))
    tmp.replace(f)
    return val


def dense_moulding(verbose=False):
    """The moulding_smooth zero level by octree dual contouring (DC_EPS), non-manifold edges repaired, the exact field
    gradients at its points: (V, F, N), disk-cached (stage 'dc')."""
    def dc():
        V, F, cls, T = dc_mesh("msmooth", G.BOX["black"], eps=DC_EPS, verbose=verbose)
        V, F = fix_nonmanifold(V, F)
        N = _unit(_grad_raw("msmooth", V, 0.003))                  # exact gradients at the DC points (cone tests)
        return V, F, N
    return stage_cached("dc", dc_key(), dc)


def dc_key():
    return (G.design_key(), DC_EPS, DC_VERSION)


def _fix_normals(V, F, N, lim=0.2):
    """Where the solid's field itself kinks (a crease of the field the zero level crosses: the inboard grip's forward
    face, the AFCS boss's back-face corner), a face can stand against its vertices' gradients: those vertices take the
    area-weighted normal of their faces instead (no dark facets)."""
    fn, ar = _face_normals(V, F)
    bad = np.einsum("ij,ikj->ik", fn, N[F]).min(1) < lim
    if not bad.any():
        return N
    vb = np.unique(F[bad].ravel())
    acc = np.zeros_like(V)
    for k in range(3):
        np.add.at(acc, F[:, k], fn * ar[:, None])
    N = N.copy()
    N[vb] = _unit(acc[vb])
    return N


# ============================================================================================ slivers
def _min_angles_deg(V, F):
    return np.degrees(_min_angle(V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]))


def sliver_cleanup(name, V, F, N, min_angle=5.0, zone=2.5, rounds=3, verbose=False):
    """Remove the sliver triangles (< min_angle) left where the field itself kinks (a fold of tiny DC triangles: the
    inboard grip's forward face, hidden): (1) relaxed collapses (cone / turn 90 deg) of the vertices within `zone` mm of
    a sliver, (2) what is left -- folded clusters of sub-0.4 mm triangles -- merged into one vertex each (edges shorter
    than 0.4 mm there), projected exactly; the link condition checked by the manifold test after each merge.
    Returns (V, F, N)."""
    from scipy.spatial import cKDTree
    V, F, N = V.copy(), F.copy(), N.copy()
    for _ in range(rounds):
        bad = _min_angles_deg(V, F) < min_angle
        if not bad.any():
            break
        d, _ = cKDTree(V[F[bad]].mean(1)).query(V)
        p = dict(DEC, dist=0.3, cone=90.0, turn=90.0, min_angle=min_angle, bnd_tol=0.0)
        fixed = d >= zone
        V, F, N, kept = decimate2(V, F, N, fixed=fixed, params=p, max_passes=20, flips=False)
        fixed = fixed[kept]
        E, _, _ = _edges(F)                                   # flips inside the zone only (relaxed there)
        F, _ = flip_pass(V, F, N, p, rounds=2, protect=E[fixed[E[:, 0]] & fixed[E[:, 1]]])
    bad = _min_angles_deg(V, F) < min_angle
    if bad.any():
        d, _ = cKDTree(V[F[bad]].mean(1)).query(V)
        E, EF, _ = _edges(F)
        bv = np.zeros(len(V), bool)
        bv[E[EF[:, 1] < 0].ravel()] = True
        L = np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1)
        sel = (L < 0.4) & (d[E[:, 0]] < 1.0) & (d[E[:, 1]] < 1.0) & ~bv[E[:, 0]] & ~bv[E[:, 1]]
        from scipy.sparse import coo_matrix
        from scipy.sparse.csgraph import connected_components
        Es = E[sel]
        _, lab = connected_components(coo_matrix((np.ones(len(Es)), (Es[:, 0], Es[:, 1])), shape=(len(V), len(V))),
                                      directed=False)
        cnt = np.bincount(lab)
        grp = np.nonzero(cnt > 1)[0]
        rep = np.arange(len(V))
        for g in grp:
            ids = np.nonzero(lab == g)[0]
            P, Nn, _ = project_exact(name, V[ids].mean(0)[None])
            V[ids[0]], N[ids[0]] = P[0], Nn[0]
            rep[ids] = ids[0]
        F2 = rep[F]
        F2 = F2[(F2[:, 0] != F2[:, 1]) & (F2[:, 1] != F2[:, 2]) & (F2[:, 0] != F2[:, 2])]
        op0, _ = manifold_report(F)
        op, nm = manifold_report(F2)
        if op == op0 and nm == 0:
            F = F2
        elif verbose:
            print(f"    sliver merge refused (open {op}, non-manifold {nm})")
    used = np.zeros(len(V), bool)
    used[F.ravel()] = True
    rm = -np.ones(len(V), np.int64)
    rm[used] = np.arange(used.sum())
    V, N, F = V[used], N[used], rm[F]
    if verbose:
        a = _min_angles_deg(V, F)
        print(f"    slivers: {int((a < min_angle).sum())} left (min {a.min():.2f} deg), {len(F)} faces", flush=True)
    return V, F, N
