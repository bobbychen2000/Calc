"""
2-D triangulation helpers for the yoke's explicit (crease-exact) patches (model/yoke_cover.py, model/yoke3d.py):

  cdt(P, C)           constrained Delaunay triangulation of the points P with the constraint edges C -- scipy's Delaunay,
                      then every missing constraint edge forced in by edge flips (Sloan 1993), then Lawson flips of the
                      unconstrained edges back to the constrained-Delaunay condition; triangles outside the constraint
                      loops dropped by the caller (inside()).
  chains(E)           the polylines of an edge graph between its nodes of degree != 2 (crease graphs).
  simplify(P, tol)    Douglas-Peucker with the end points kept.
  resample(P, ...)    a polyline resampled by arc length and turn.
"""
from __future__ import annotations

import math
from collections import defaultdict, deque

import numpy as np


def _orient(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _incircle(a, b, c, d):
    """> 0 when d lies inside the circumcircle of the CCW triangle a, b, c."""
    ax, ay = a[0] - d[0], a[1] - d[1]
    bx, by = b[0] - d[0], b[1] - d[1]
    cx, cy = c[0] - d[0], c[1] - d[1]
    return ((ax * ax + ay * ay) * (bx * cy - cx * by) - (bx * bx + by * by) * (ax * cy - cx * ay)
            + (cx * cx + cy * cy) * (ax * by - bx * ay))


def _cross_proper(p, q, a, b, eps=1e-12):
    """Segments pq and ab cross at a point interior to both."""
    d1, d2 = _orient(a, b, p), _orient(a, b, q)
    d3, d4 = _orient(p, q, a), _orient(p, q, b)
    return (d1 * d2 < -eps) and (d3 * d4 < -eps)


class _Mesh2:
    def __init__(self, P, T):
        self.P = P
        self.T = [list(t) for t in T]
        self.alive = [True] * len(self.T)
        self.E = defaultdict(set)                     # (i, j) i < j -> triangle ids
        self.VT = defaultdict(set)
        for k, t in enumerate(self.T):
            if _orient(P[t[0]], P[t[1]], P[t[2]]) < 0:
                t[1], t[2] = t[2], t[1]
            self._reg(k)

    def _reg(self, k):
        t = self.T[k]
        for i in range(3):
            a, b = t[i], t[(i + 1) % 3]
            self.E[(a, b) if a < b else (b, a)].add(k)
            self.VT[t[i]].add(k)

    def _unreg(self, k):
        t = self.T[k]
        for i in range(3):
            a, b = t[i], t[(i + 1) % 3]
            e = (a, b) if a < b else (b, a)
            self.E[e].discard(k)
            if not self.E[e]:
                del self.E[e]
            self.VT[t[i]].discard(k)

    def has(self, a, b):
        return ((a, b) if a < b else (b, a)) in self.E

    def flip(self, a, b):
        """Flip the edge (a, b) shared by two triangles; returns the new edge (p, q) or None if not flippable."""
        e = (a, b) if a < b else (b, a)
        ts = list(self.E.get(e, ()))
        if len(ts) != 2:
            return None
        t1, t2 = ts
        p = [v for v in self.T[t1] if v not in e][0]
        q = [v for v in self.T[t2] if v not in e][0]
        P = self.P
        if not _cross_proper(P[p], P[q], P[a], P[b], 0.0):
            return None
        self._unreg(t1)
        self._unreg(t2)
        n1, n2 = [p, q, a], [q, p, b]
        if _orient(P[n1[0]], P[n1[1]], P[n1[2]]) < 0:
            n1[1], n1[2] = n1[2], n1[1]
        if _orient(P[n2[0]], P[n2[1]], P[n2[2]]) < 0:
            n2[1], n2[2] = n2[2], n2[1]
        self.T[t1], self.T[t2] = n1, n2
        self._reg(t1)
        self._reg(t2)
        return (p, q)

    def crossing_edges(self, a, b):
        """Edges crossed by the segment a -> b (walk from a); raises if the segment runs through a vertex."""
        P = self.P
        pa, pb = P[a], P[b]
        start = None
        for k in self.VT[a]:
            t = self.T[k]
            i = t.index(a)
            u, v = t[(i + 1) % 3], t[(i + 2) % 3]
            if b in (u, v):
                return []
            ou, ov = _orient(pa, pb, P[u]), _orient(pa, pb, P[v])
            if ou < 0 < ov:
                start = (k, u, v)
                break
            if (ou == 0 and _orient(pa, P[u], pb) == 0 and np.dot(P[u] - pa, pb - pa) > 0) or \
                    (ov == 0 and _orient(pa, P[v], pb) == 0 and np.dot(P[v] - pa, pb - pa) > 0):
                raise ValueError("collinear")
        if start is None:
            raise ValueError("walk start")
        k, u, v = start
        out = [(u, v)]
        for _ in range(100000):
            e = (u, v) if u < v else (v, u)
            nb = [t for t in self.E[e] if t != k]
            if not nb:
                raise ValueError("walk left the mesh")
            k = nb[0]
            w = [x for x in self.T[k] if x not in e][0]
            if w == b:
                return out
            ow = _orient(pa, pb, P[w])
            if abs(ow) < 1e-14:
                raise ValueError("collinear")
            if ow < 0:
                u = w
            else:
                v = w
            out.append((u, v))
        raise ValueError("walk too long")


def cdt(P, C, lawson=True):
    """Constrained Delaunay triangulation: points P (n, 2), constraint edges C (m, 2) -> triangles (k, 3) CCW, over the
    convex hull.  Constraint edges through other points are split at them."""
    from scipy.spatial import Delaunay
    P = np.asarray(P, float)
    M = _Mesh2(P, Delaunay(P).simplices)
    cons = set()
    todo = deque((int(a), int(b)) for a, b in C if a != b)
    guard = 0
    while todo:
        guard += 1
        if guard > 50 * len(C) + 1000:
            raise RuntimeError("cdt: constraint insertion does not terminate")
        a, b = todo.popleft()
        if M.has(a, b):
            cons.add((min(a, b), max(a, b)))
            continue
        try:
            cr = M.crossing_edges(a, b)
        except ValueError:
            # a vertex on the segment: split the constraint there
            pa, pb = P[a], P[b]
            d = pb - pa
            L2 = float(d @ d)
            t = ((P - pa) @ d) / L2
            off = np.abs((P[:, 0] - pa[0]) * d[1] - (P[:, 1] - pa[1]) * d[0]) / math.sqrt(L2)
            on = np.nonzero((t > 1e-9) & (t < 1 - 1e-9) & (off < 1e-9 * math.sqrt(L2) + 1e-12))[0]
            if not len(on):
                raise
            w = int(on[np.argmin(t[on])])
            todo.appendleft((w, b))
            todo.appendleft((a, w))
            continue
        q = deque(cr)
        n_iter = 0
        while q:
            n_iter += 1
            if n_iter > 100000:
                raise RuntimeError("cdt: flips do not terminate")
            u, v = q.popleft()
            if not M.has(u, v):
                continue
            ne = M.flip(u, v)
            if ne is None:
                q.append((u, v))
                continue
            p_, q_ = ne
            if p_ not in (a, b) and q_ not in (a, b) and _cross_proper(P[p_], P[q_], P[a], P[b]):
                q.append(ne)
        cons.add((min(a, b), max(a, b)))
    if lawson:
        stack = [e for e in list(M.E.keys()) if e not in cons]
        n = 0
        while stack and n < 20 * len(M.T) + 1000:
            n += 1
            e = stack.pop()
            if e in cons or e not in M.E or len(M.E[e]) != 2:
                continue
            t1, t2 = list(M.E[e])
            a, b = e
            p = [v for v in M.T[t1] if v not in e][0]
            q_ = [v for v in M.T[t2] if v not in e][0]
            T1 = M.T[t1]
            if _incircle(P[T1[0]], P[T1[1]], P[T1[2]], P[q_]) > 1e-18 and _cross_proper(P[p], P[q_], P[a], P[b]):
                ne = M.flip(a, b)
                if ne is not None:
                    for x, y in ((a, p), (p, b), (b, q_), (q_, a)):
                        stack.append((min(x, y), max(x, y)))
    return np.array(M.T, np.int64)


def inside(T, P, loops):
    """Triangles of T whose centroid lies inside the closed loops (even-odd over all loops; loops = [index arrays])."""
    from matplotlib.path import Path
    C = P[T].mean(1)
    k = np.zeros(len(T), int)
    for L in loops:
        k += Path(P[np.r_[L, L[:1]]]).contains_points(C)
    return T[k % 2 == 1]


def chains(E):
    """Polylines (lists of node ids) of the undirected edge list E between nodes of degree != 2 (closed loops of degree-2
    nodes come out closed: first == last)."""
    adj = defaultdict(list)
    for a, b in E:
        adj[a].append(b)
        adj[b].append(a)
    seen = set()
    out = []
    ends = [v for v in adj if len(adj[v]) != 2]
    for s in ends:
        for n in adj[s]:
            e = (min(s, n), max(s, n))
            if e in seen:
                continue
            path = [s, n]
            seen.add(e)
            prev, cur = s, n
            while len(adj[cur]) == 2:
                nxt = adj[cur][0] if adj[cur][1] == prev else adj[cur][1]
                e = (min(cur, nxt), max(cur, nxt))
                if e in seen:
                    break
                seen.add(e)
                path.append(nxt)
                prev, cur = cur, nxt
            out.append(path)
    for s in adj:                                                     # pure loops
        for n in adj[s]:
            e = (min(s, n), max(s, n))
            if e in seen:
                continue
            path = [s, n]
            seen.add(e)
            prev, cur = s, n
            while True:
                nxt = adj[cur][0] if adj[cur][1] == prev else adj[cur][1]
                e = (min(cur, nxt), max(cur, nxt))
                if e in seen:
                    break
                seen.add(e)
                path.append(nxt)
                prev, cur = cur, nxt
            out.append(path)
    return out


def simplify(P, tol):
    """Douglas-Peucker indices of the polyline P (ends kept)."""
    P = np.asarray(P, float)
    keep = np.zeros(len(P), bool)
    keep[0] = keep[-1] = True
    st = [(0, len(P) - 1)]
    while st:
        i, j = st.pop()
        if j <= i + 1:
            continue
        a, b = P[i], P[j]
        d = b - a
        L = float(np.hypot(*d))
        Q = P[i + 1:j] - a
        dist = np.abs(Q[:, 0] * d[1] - Q[:, 1] * d[0]) / L if L > 1e-12 else np.hypot(Q[:, 0], Q[:, 1])
        k = int(np.argmax(dist))
        if dist[k] > tol:
            keep[i + 1 + k] = True
            st += [(i, i + 1 + k), (i + 1 + k, j)]
    return np.nonzero(keep)[0]


def resample(P, max_len, max_turn_deg=8.0, closed=False):
    """Arc-length resampling of the dense polyline P: a sample every <= max_len and every max_turn_deg of tangent
    turn; the ends kept (closed: P[0] kept, no repeat)."""
    P = np.asarray(P, float)
    Q = np.vstack([P, P[:1]]) if closed else P
    seg = np.diff(Q, axis=0)
    L = np.hypot(seg[:, 0], seg[:, 1])
    ang = np.arctan2(seg[:, 1], seg[:, 0])
    dt = np.abs((np.diff(ang) + np.pi) % (2 * np.pi) - np.pi)
    out = [0]
    acc_l, acc_t = 0.0, 0.0
    for i in range(1, len(Q) - 1):
        acc_l += L[i - 1]
        acc_t += math.degrees(dt[i - 1])
        if acc_l >= max_len or acc_t >= max_turn_deg:
            out.append(i)
            acc_l, acc_t = 0.0, 0.0
    if not closed:
        if out[-1] != len(Q) - 1:
            if acc_l + L[-1] < 0.35 * max_len and len(out) > 1:
                out[-1] = len(Q) - 1
            else:
                out.append(len(Q) - 1)
    return np.array(out)


def orient_group(meshes, tol):
    """Consistent winding over a group of meshes [(V, F)] that share positions (welded within tol): faces are flipped
    so that every manifold edge is traversed once each way (breadth-first over the welded surface), and each connected
    component keeps the winding the majority (by area) of its faces had -- a face built facing its own corner normals
    across a fold or a crease no longer contradicts its neighbours.  Returns the new face arrays."""
    from collections import deque
    Vs = [np.asarray(V, float) for V, _ in meshes]
    Fs = [np.asarray(F, np.int64).copy() for _, F in meshes]
    off = np.cumsum([0] + [len(v) for v in Vs])
    V = np.vstack(Vs)
    _, w = np.unique(np.round(V / tol).astype(np.int64), axis=0, return_inverse=True)
    w = w.ravel()
    F = np.vstack([f + o for f, o in zip(Fs, off)])
    Fw = w[F]
    ok = (Fw[:, 0] != Fw[:, 1]) & (Fw[:, 1] != Fw[:, 2]) & (Fw[:, 0] != Fw[:, 2])
    nf = len(F)
    area = 0.5 * np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1)
    edges = {}
    for f in np.nonzero(ok)[0]:
        a, b, c = Fw[f]
        for x, y in ((a, b), (b, c), (c, a)):
            edges.setdefault((min(x, y), max(x, y)), []).append(f)
    flip = np.zeros(nf, bool)
    seen = np.zeros(nf, bool)

    def directed(f, x, y):
        """+1 if face f (with its flip) runs x -> y."""
        a, b, c = Fw[f]
        fwd = (a, b) == (x, y) or (b, c) == (x, y) or (c, a) == (x, y)
        return (1 if fwd else -1) * (-1 if flip[f] else 1)
    for s in np.nonzero(ok)[0]:
        if seen[s]:
            continue
        comp = [s]
        seen[s] = True
        q = deque([s])
        while q:
            f = q.popleft()
            a, b, c = Fw[f]
            for x, y in ((a, b), (b, c), (c, a)):
                adj = edges[(min(x, y), max(x, y))]
                if len(adj) != 2:
                    continue
                g = adj[0] if adj[1] == f else adj[1]
                if seen[g]:
                    continue
                if directed(g, x, y) == directed(f, x, y):
                    flip[g] = not flip[g]
                seen[g] = True
                comp.append(g)
                q.append(g)
        comp = np.array(comp)
        if area[comp[flip[comp]]].sum() > area[comp[~flip[comp]]].sum():
            flip[comp] = ~flip[comp]
    F[flip] = F[flip][:, ::-1]
    fo = np.cumsum([0] + [len(f) for f in Fs])
    return [F[fo[i]:fo[i + 1]] - off[i] for i in range(len(Fs))]
