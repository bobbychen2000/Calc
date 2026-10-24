"""Exact mesh-mesh crossing test for the fit checks: edges of one triangle mesh crossing triangles of the other
(both ways), vectorised Moller-Trumbore on candidate pairs from a uniform-grid broad phase.  Unlike vertex tests it catches
coarse triangles bulging through a surface (M8: the rudder's domed top cap between vertices under the fin tip)."""
from __future__ import annotations

import numpy as np


def edges_of(F):
    E = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    E.sort(1)
    return np.unique(E, axis=0)


def seg_tri(P0, P1, T0, T1, T2, eps=1e-12):
    """Segments P0-P1 vs triangles (row-wise): (hit mask, intersection points)."""
    d = P1 - P0
    e1, e2 = T1 - T0, T2 - T0
    p = np.cross(d, e2)
    det = np.einsum("ij,ij->i", e1, p)
    ok = np.abs(det) > eps
    inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
    s = P0 - T0
    u = np.einsum("ij,ij->i", s, p) * inv
    q = np.cross(s, e1)
    v = np.einsum("ij,ij->i", d, q) * inv
    t = np.einsum("ij,ij->i", e2, q) * inv
    hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t >= 0) & (t <= 1)
    return hit, P0 + d * t[:, None]


def _cells(lo, hi, h):
    """(item index, cell hash) for every grid cell (size h) an item's AABB lo..hi overlaps."""
    a = np.floor(lo / h).astype(np.int64)
    n = np.floor(hi / h).astype(np.int64) - a + 1
    cnt = n.prod(1)
    idx = np.repeat(np.arange(len(lo)), cnt)
    k = np.arange(int(cnt.sum())) - np.repeat(np.cumsum(cnt) - cnt, cnt)
    nx, ny = n[idx, 0], n[idx, 1]
    ix = a[idx, 0] + k % nx
    iy = a[idx, 1] + (k // nx) % ny
    iz = a[idx, 2] + k // (nx * ny)
    return idx, (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791)


def _pairs(elo, ehi, tlo, thi, h):
    """Candidate (edge, triangle) pairs sharing a grid cell, AABB-filtered."""
    ie, ke = _cells(elo, ehi, h)
    it, kt = _cells(tlo, thi, h)
    o = np.argsort(kt, kind="stable")
    kt, it = kt[o], it[o]
    left, right = np.searchsorted(kt, ke, "left"), np.searchsorted(kt, ke, "right")
    cnt = right - left
    if not cnt.sum():
        return np.zeros(0, int), np.zeros(0, int)
    ei = np.repeat(ie, cnt)
    pos = np.repeat(left, cnt) + (np.arange(int(cnt.sum())) - np.repeat(np.cumsum(cnt) - cnt, cnt))
    ti = it[pos]
    key = np.unique(ei.astype(np.int64) * (len(tlo) + 1) + ti)
    ei, ti = key // (len(tlo) + 1), key % (len(tlo) + 1)
    ok = ((ehi[ei] >= tlo[ti]) & (elo[ei] <= thi[ti])).all(1)
    return ei[ok], ti[ok]


def crossings(VA, FA, VB, FB, pad=0.01, chunk=400000):
    """Points where edges of mesh A cross triangles of mesh B or edges of B cross triangles of A ((n, 3)).
    Broad phase: uniform-grid hashing of edge / triangle bounding boxes; narrow phase: Moller-Trumbore."""
    if len(FA) == 0 or len(FB) == 0:
        return np.zeros((0, 3))
    lo = np.maximum(VA.min(0), VB.min(0)) - pad
    hi = np.minimum(VA.max(0), VB.max(0)) + pad
    if (lo > hi).any():
        return np.zeros((0, 3))
    pts = []
    for Va, Fa, Vb, Fb in ((VA, FA, VB, FB), (VB, FB, VA, FA)):
        def inbox(V, F):
            T = V[F]
            return F[((T.max(1) >= lo) & (T.min(1) <= hi)).all(1)]
        fa, fb = inbox(Va, Fa), inbox(Vb, Fb)
        if len(fa) == 0 or len(fb) == 0:
            continue
        E = edges_of(fa)
        P0, P1 = Va[E[:, 0]], Va[E[:, 1]]
        T = Vb[fb]
        tlo, thi = T.min(1), T.max(1)
        elo, ehi = np.minimum(P0, P1), np.maximum(P0, P1)
        ext = np.r_[(thi - tlo).max(1), (ehi - elo).max(1)]
        h = float(np.clip(2.0 * np.median(ext), 0.005, 0.25))
        ii, jj = _pairs(elo, ehi, tlo, thi, h)
        for s in range(0, len(ii), chunk):
            a, b = ii[s:s + chunk], jj[s:s + chunk]
            hit, P = seg_tri(P0[a], P1[a], T[b, 0], T[b, 1], T[b, 2])
            if hit.any():
                pts.append(P[hit])
    return np.vstack(pts) if pts else np.zeros((0, 3))


def merged(meshes, M=None):
    """(V, F) of a list of Mesh objects, optionally transformed by the 4x4 M."""
    Vs, Fs, off = [], [], 0
    for m in meshes:
        V = m.V if M is None else m.V @ M[:3, :3].T + M[:3, 3]
        Vs.append(V)
        Fs.append(m.F + off)
        off += len(V)
    if not Vs:
        return np.zeros((0, 3)), np.zeros((0, 3), int)
    return np.vstack(Vs), np.vstack(Fs)


def pt_tri_k(P, T):
    """Exact distances of points P (n, 3) to the triangles T (n, k, 3, 3) (k candidates per point): (n,) minimum."""
    a, b, c = T[:, :, 0], T[:, :, 1], T[:, :, 2]
    Q = P[:, None, :]
    ab, ac, ap = b - a, c - a, Q - a
    d1, d2 = (ab * ap).sum(-1), (ac * ap).sum(-1)
    bp = Q - b
    d3, d4 = (ab * bp).sum(-1), (ac * bp).sum(-1)
    cp = Q - c
    d5, d6 = (ab * cp).sum(-1), (ac * cp).sum(-1)
    va = d3 * d6 - d5 * d4
    vb = d5 * d2 - d1 * d6
    vc = d1 * d4 - d3 * d2
    den = np.where(np.abs(va + vb + vc) < 1e-30, 1e-30, va + vb + vc)
    v, w = vb / den, vc / den
    X = a + v[..., None] * ab + w[..., None] * ac                                         # interior projection
    # region tests (Ericson): vertices / edges
    X = np.where(((d1 <= 0) & (d2 <= 0))[..., None], a, X)
    X = np.where(((d3 >= 0) & (d4 <= d3))[..., None], b, X)
    X = np.where(((d6 >= 0) & (d5 <= d6))[..., None], c, X)
    vab = (vc <= 0) & (d1 >= 0) & (d3 <= 0)
    tab = d1 / np.where(np.abs(d1 - d3) < 1e-30, 1e-30, d1 - d3)
    X = np.where(vab[..., None], a + tab[..., None] * ab, X)
    vac = (vb <= 0) & (d2 >= 0) & (d6 <= 0)
    tac = d2 / np.where(np.abs(d2 - d6) < 1e-30, 1e-30, d2 - d6)
    X = np.where(vac[..., None], a + tac[..., None] * ac, X)
    vbc = (va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0)
    tbc = (d4 - d3) / np.where(np.abs((d4 - d3) + (d5 - d6)) < 1e-30, 1e-30, (d4 - d3) + (d5 - d6))
    X = np.where(vbc[..., None], b + tbc[..., None] * (c - b), X)
    return np.linalg.norm(Q - X, axis=-1).min(1)
