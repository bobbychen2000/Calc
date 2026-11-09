"""Keep-out clipping of building faces against another structure's solid volume (close-out round 5, buildings track).

Why: the round-4 verifier found landside facades crossing the AirTrain guideway and its stations - the Garage A station
block's deck-1 opening on the stepped face (a precast spandrel through the girder), its far wall across both decks' parapets,
the Garage G spandrels / screen piers against the station vault's posts and eaves, the LTP garage 2 body against the deck and
the LTP station roof, the Grand Hyatt glass and the RCC canted louvres against the deck. Each was a facade style that did not
know where the guideway passes. This module makes that a property of the build: every face of a building part is cleared out
of the AirTrain's COLUMN HULL plus a clearance (the guideway keeps PORTAL_CLEAR 0.10 m all round, as the portal holes since
close-out round 4).

Column hull: at a plan point p, the z-intervals [lo - clear, hi + clear] of the AirTrain triangles whose plan footprint
(buffered by `clear`) covers p, intervals closer than `gap` merged - a closed deck box (soffit, sides, top, parapets, rails)
becomes one solid interval from its soffit to its parapet top; a station roof 3-4 m above it stays a separate interval.

Clipping (per planar face of a building mesh, in the face's own 2-D frame):
  vertical faces   samples every DS_V along the face's horizontal axis; at each sample the column intervals are EXACT in
                   height, so a cut is a run of rectangles (s-interval x z-interval), merged where the intervals agree;
  other faces      a grid of DS_H in the face plane; each sample point inside a column interval marks a square.
The marked area (+ nothing else) is subtracted from the face polygon (shapely), the rest re-triangulated (constrained
Delaunay) with the face's own winding, UVs carried by an affine fit of the original corners (planar UV mapping of these
meshes). Faces that do not meet the hull are kept untouched (same indices, shared vertices, smooth groups).
Every constant here is a modelling choice [inf]."""
import math

import numpy as np
import shapely
from shapely.geometry import MultiPoint, Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree

CLEAR = 0.10          # = landside_geom.PORTAL_CLEAR: the guideway's clearance to building faces [inf]
GAP = 0.6             # column intervals closer than this merge (deck soffit .. parapet top = one solid) [inf]
DS_V = 0.05           # vertical faces: sample step along the face [m]
DS_H = 0.10           # other faces: sample grid [m]


class Columns:
    """column hull of a triangle soup T (n, 3, 3) in WORLD coordinates (x, height above the apron, z)."""

    def __init__(self, T, clear=CLEAR, gap=GAP):
        T = np.asarray(T, float)
        self.clear, self.gap = clear, gap
        fps = []
        for t in T:
            q = Polygon(t[:, [0, 2]])
            if not q.is_valid or q.area < 1e-6:
                q = MultiPoint([tuple(p) for p in t[:, [0, 2]]]).convex_hull
            fps.append(q.buffer(clear, quad_segs=2))
        self.fp = fps
        self.lo = T[:, :, 1].min(1) - clear
        self.hi = T[:, :, 1].max(1) + clear
        self.tree = STRtree(fps) if fps else None
        self.bounds = unary_union([f.envelope for f in fps]).bounds if fps else None

    def intervals(self, pts):
        """per plan point (k, 2) world (x, z): merged [(lo, hi)] list."""
        out = [[] for _ in range(len(pts))]
        if self.tree is None or not len(pts): return out
        ip, it = self.tree.query(shapely.points(np.asarray(pts, float)), predicate='intersects')
        order = np.lexsort((self.lo[it], ip))
        ip, it = ip[order], it[order]
        for p, t in zip(ip, it):
            lst = out[p]
            a, b = self.lo[t], self.hi[t]
            if lst and a <= lst[-1][1] + self.gap:
                if b > lst[-1][1]: lst[-1] = (lst[-1][0], b)
            else:
                lst.append((a, b))
        return out

    def near(self, poly_w, z0, z1):
        """any triangle column whose footprint meets the world plan polygon and whose band meets [z0, z1]."""
        if self.tree is None: return False
        idx = self.tree.query(poly_w, predicate='intersects')
        return bool(len(idx)) and bool(((self.lo[idx] <= z1) & (self.hi[idx] >= z0)).any())


def _frame(P):
    """orthonormal in-plane axes (e1, e2) and unit normal of a planar polygon P (k, 3)."""
    n = np.zeros(3)
    for i in range(len(P)): n += np.cross(P[i], P[(i + 1) % len(P)])
    L = np.linalg.norm(n)
    if L < 1e-12: return None
    n = n / L
    if abs(n[2]) < 0.02:                         # vertical: e1 horizontal, e2 = +z
        e1 = np.array([-n[1], n[0], 0.0]); e1 /= np.linalg.norm(e1); e2 = np.array([0.0, 0.0, 1.0])
    else:
        ref = np.array([1.0, 0.0, 0.0]) if abs(n[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        e1 = ref - n * (ref @ n); e1 /= np.linalg.norm(e1); e2 = np.cross(n, e1)
    return e1, e2, n


def clip_mb(mb, to_world, cols, stats=None, ds_v=DS_V, ds_h=DS_H):
    """clear the faces of mb (a landside_mesh.MB in a building's local frame; to_world(X, Y) -> world (x, z), Z = height)
    out of the column hull `cols`. Returns the cut area (m2)."""
    if cols.tree is None or not mb.F: return 0.0
    bx = cols.bounds
    V = np.asarray(mb.V, float)
    W = np.array([to_world(x, y) for x, y in V[:, :2]]) if len(V) else np.zeros((0, 2))
    keepF, keepM, keepUV, keepS = [], [], [], []
    newfaces = []
    cut_area = 0.0
    for f, m, uv, sm in zip(mb.F, mb.M, mb.UV, mb.S):
        Pw = W[f]
        if (Pw[:, 0].max() < bx[0] or Pw[:, 0].min() > bx[2] or Pw[:, 1].max() < bx[1] or Pw[:, 1].min() > bx[3]):
            keepF.append(f); keepM.append(m); keepUV.append(uv); keepS.append(sm); continue
        z = V[f][:, 2]
        hull = MultiPoint([tuple(p) for p in Pw]).convex_hull.buffer(0.01)
        if not cols.near(hull, z.min(), z.max()):
            keepF.append(f); keepM.append(m); keepUV.append(uv); keepS.append(sm); continue
        P = V[f]
        fr = _frame(P)
        if fr is None:
            keepF.append(f); keepM.append(m); keepUV.append(uv); keepS.append(sm); continue
        e1, e2, n = fr
        o = P[0]
        Q = np.c_[(P - o) @ e1, (P - o) @ e2]
        poly = Polygon(Q)
        if not poly.is_valid: poly = poly.buffer(0)
        if poly.is_empty or poly.area < 1e-6:
            keepF.append(f); keepM.append(m); keepUV.append(uv); keepS.append(sm); continue
        u0, v0, u1, v1 = poly.bounds
        marks = []
        if abs(n[2]) < 0.02:
            # vertical face: samples along e1 (horizontal), exact z intervals
            ss = np.arange(u0 + ds_v / 2, u1, ds_v) if u1 - u0 > ds_v else np.array([(u0 + u1) / 2])
            pl = o[None, :] + ss[:, None] * e1[None, :]
            pw = np.array([to_world(x, y) for x, y in pl[:, :2]])
            ivs = cols.intervals(pw)
            run = None
            for s_, iv in zip(ss, ivs):
                key = tuple((round(a - o[2], 2), round(b - o[2], 2)) for a, b in iv if b > o[2] + v0 and a < o[2] + v1)
                if run is not None and run[2] == key:
                    run[1] = s_ + ds_v / 2
                else:
                    if run is not None and run[2]: marks.append(run)
                    run = [s_ - ds_v / 2, s_ + ds_v / 2, key]
            if run is not None and run[2]: marks.append(run)
            rects = [shapely.box(a, lo, b, hi) for a, b, key in marks for lo, hi in key]
        else:
            us = np.arange(u0 + ds_h / 2, u1, ds_h) if u1 - u0 > ds_h else np.array([(u0 + u1) / 2])
            vs = np.arange(v0 + ds_h / 2, v1, ds_h) if v1 - v0 > ds_h else np.array([(v0 + v1) / 2])
            G = np.array([(a, b) for a in us for b in vs])
            inside = shapely.contains_xy(poly, G[:, 0], G[:, 1]) if len(G) else np.zeros(0, bool)
            G = G[inside]
            rects = []
            if len(G):
                P3 = o[None, :] + G[:, :1] * e1[None, :] + G[:, 1:] * e2[None, :]
                pw = np.array([to_world(x, y) for x, y in P3[:, :2]])
                ivs = cols.intervals(pw)
                for g, p3, iv in zip(G, P3, ivs):
                    if any(a <= p3[2] <= b for a, b in iv):
                        rects.append(shapely.box(g[0] - ds_h / 2, g[1] - ds_h / 2, g[0] + ds_h / 2, g[1] + ds_h / 2))
        if not rects:
            keepF.append(f); keepM.append(m); keepUV.append(uv); keepS.append(sm); continue
        cut = unary_union(rects)
        rest = poly.difference(cut)
        dA = poly.area - rest.area
        if dA < 1e-4:
            keepF.append(f); keepM.append(m); keepUV.append(uv); keepS.append(sm); continue
        cut_area += dA
        # affine UV fit (u, v) = A [s, t, 1] from the original corners
        Aq = np.c_[Q, np.ones(len(Q))]
        coef, *_ = np.linalg.lstsq(Aq, np.asarray(uv, float), rcond=None)
        for g in getattr(rest, 'geoms', [rest]):
            if g.geom_type != 'Polygon' or g.area < 1e-4: continue
            g = g.simplify(1e-4)
            for tri in shapely.constrained_delaunay_triangles(g).geoms:
                c = np.array(tri.exterior.coords)[:3]
                if abs((c[1, 0] - c[0, 0]) * (c[2, 1] - c[0, 1]) - (c[2, 0] - c[0, 0]) * (c[1, 1] - c[0, 1])) < 1e-9: continue
                p3 = o[None, :] + c[:, :1] * e1[None, :] + c[:, 1:] * e2[None, :]
                if np.cross(p3[1] - p3[0], p3[2] - p3[0]) @ n < 0: p3 = p3[::-1]; c = c[::-1]
                newfaces.append((p3, m, [tuple(x) for x in (np.c_[c, np.ones(3)] @ coef)], sm))
    if stats is not None:
        stats['faces_cut'] = stats.get('faces_cut', 0) + (len(mb.F) - len(keepF))
        stats['area_m2'] = stats.get('area_m2', 0.0) + cut_area
    if len(keepF) == len(mb.F): return 0.0
    mb.F, mb.M, mb.UV, mb.S = keepF, keepM, keepUV, keepS
    for p3, m, uvs, sm in newfaces:
        idx = [len(mb.V) + i for i in range(3)]
        mb.V.extend(tuple(float(c) for c in p) for p in p3)
        mb.F.append(idx); mb.M.append(m); mb.UV.append([(float(a), float(b)) for a, b in uvs]); mb.S.append(sm)
    return cut_area


def tris_world(mb, to_world):
    """triangles (n, 3, 3) world (x, height, z) of an MB."""
    V = np.asarray(mb.V, float)
    out = []
    for f in mb.F:
        for k in range(1, len(f) - 1):
            out.append([V[f[0]], V[f[k]], V[f[k + 1]]])
    if not out: return np.zeros((0, 3, 3))
    T = np.array(out)
    xz = np.array([to_world(x, y) for x, y in T.reshape(-1, 3)[:, :2]]).reshape(len(T), 3, 2)
    return np.stack([xz[:, :, 0], T[:, :, 2], xz[:, :, 1]], 2)
