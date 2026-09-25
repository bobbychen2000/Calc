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
