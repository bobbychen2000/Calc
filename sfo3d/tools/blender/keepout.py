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
  vertical faces   the face's horizontal extent split into equal steps <= DS_V (the whole extent: an uneven last strip
                   was left uncut before); at each step centre the column intervals are EXACT in height, so a cut is a
                   run of rectangles (s-interval x z-interval), merged where the intervals agree;
  other faces      cells <= DS_H covering the face's bounding box, only where it meets the plan footprint of the candidate
                   columns; a cell is marked when its centre or a corner lies strictly inside a column interval; the
                   marked cells are then INTERSECTED with that footprint (mapped into the face frame), so the cut edge is
                   the hull outline itself, not a saw-tooth of cells, and slivers along the face's own edges are cut too.
The marked area (+ nothing else) is subtracted from the face polygon (shapely), the rest re-triangulated (constrained
Delaunay) with the face's own winding, UVs carried by an affine fit of the original corners (planar UV mapping of these
meshes). Faces that do not meet the hull are kept untouched (same indices, shared vertices, smooth groups).
Every constant here is a modelling choice [inf]."""
import math

import numpy as np
import shapely
from shapely import affinity
from shapely.geometry import MultiPoint, Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree

CLEAR = 0.10          # = landside_geom.PORTAL_CLEAR: the guideway's clearance to building faces in plan [inf]
CLEAR_Z = 0.05        # vertical faces: cut this far below / above the solid (a wall stops short of the girder soffit / parapet
                      # top); horizontal and sloped faces are cut only where they lie INSIDE the solid (+-Z_TOL): a roof that
                      # merely meets the deck soffit from below (the BART station) is contact, not a clash [inf]
Z_TOL = 0.02
GAP = 2.0             # column intervals closer than this merge: the 1.6-m deck box (soffit .. top .. parapet) is one solid;
                      # a station roof 3.5-4.5 m above the deck stays separate [inf]
DS_V = 0.05           # vertical faces: sample step along the face [m]
DS_H = 0.10           # other faces: sample grid [m]


class Columns:
    """column hull of a triangle soup T (n, 3, 3) in WORLD coordinates (x, height above the apron, z)."""

    def __init__(self, T, clear=CLEAR, gap=GAP, clear_z=CLEAR_Z, inset=0.0):
        """inset > 0: a CONTACT hull - only plan points at least `inset` inside the (unbuffered) footprint union have intervals
        (a structure built to abut the guideway keeps its touching faces; what lies inside the solid beyond the contact band is
        cut). `clear` still buffers each triangle's own footprint, so a change of interval INSIDE the solid (a parapet, the
        track) is cut from clear before it: clear >= DS_V / 2 keeps the sampled cut ahead of it"""
        T = np.asarray(T, float)
        self.clear, self.gap, self.clear_z, self.inset = clear, gap, clear_z, inset
        fps = []
        for t in T:
            q = Polygon(t[:, [0, 2]])
            if not q.is_valid or q.area < 1e-6:
                q = MultiPoint([tuple(p) for p in t[:, [0, 2]]]).convex_hull
            fps.append(q.buffer(clear, quad_segs=2))
        self.fp = fps
        self.lo = T[:, :, 1].min(1)          # raw heights: vertical faces add clear_z, other faces must lie strictly inside
        self.hi = T[:, :, 1].max(1)
        # close-out r5: a non-vertical triangle contributes its own PLANE height at the query point (clamped to its band), not
        # its whole band - a sloping deck soffit triangle (17.56 .. 18.15 m) had made the solid reach down to 17.56 m over its
        # whole footprint (the CG plinth top at 18.13 m read as inside over 381 m2); vertical triangles keep their band
        P_ = T[:, :, [0, 2]]; d1 = P_[:, 1] - P_[:, 0]; d2 = P_[:, 2] - P_[:, 0]
        det = d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]
        self.planar = np.abs(det) > 1e-4
        dt = np.where(self.planar, det, 1.0); h0 = T[:, 0, 1]; e1h = T[:, 1, 1] - h0; e2h = T[:, 2, 1] - h0
        # h(x, z) = h0 + gx (x - x0) + gz (z - z0)
        self.gx = np.where(self.planar, (e1h * d2[:, 1] - e2h * d1[:, 1]) / dt, 0.0)
        self.gz = np.where(self.planar, (e2h * d1[:, 0] - e1h * d2[:, 0]) / dt, 0.0)
        self.x0, self.z0, self.h0 = P_[:, 0, 0], P_[:, 0, 1], h0
        self.tree = STRtree(fps) if fps else None
        self.bounds = unary_union([f.envelope for f in fps]).bounds if fps else None
        self.core = None
        if inset > 0 and fps:
            self.core = unary_union([f for f in fps if not f.is_empty]).buffer(-(inset + clear)); shapely.prepare(self.core)

    def intervals(self, pts):
        """per plan point (k, 2) world (x, z): merged [(lo, hi)] list."""
        out = [[] for _ in range(len(pts))]
        if self.tree is None or not len(pts): return out
        ip, it = self.tree.query(shapely.points(np.asarray(pts, float)), predicate='intersects')
        if self.core is not None:
            pa = np.asarray(pts, float); inc = shapely.contains_xy(self.core, pa[:, 0], pa[:, 1]); keep = inc[ip]
            ip, it = ip[keep], it[keep]
        pa = np.asarray(pts, float)
        hp = self.h0[it] + self.gx[it] * (pa[ip, 0] - self.x0[it]) + self.gz[it] * (pa[ip, 1] - self.z0[it])
        hp = np.clip(hp, self.lo[it], self.hi[it]); pl = self.planar[it]
        A_ = np.where(pl, hp, self.lo[it]); B_ = np.where(pl, hp, self.hi[it])
        order = np.lexsort((A_, ip))
        ip, it, A_, B_ = ip[order], it[order], A_[order], B_[order]
        for p, t, a, b in zip(ip, it, A_, B_):
            lst = out[p]
            if lst and a <= lst[-1][1] + self.gap:
                if b > lst[-1][1]: lst[-1] = (lst[-1][0], b)
            else:
                lst.append((a, b))
        return out

    def footprint(self, poly_w, z0, z1):
        """union of the column footprints meeting the world plan polygon whose triangle band is within `gap` of [z0, z1]
        (every merged interval that can contain a height in [z0, z1] is made of such triangles)."""
        if self.tree is None: return None
        idx = self.tree.query(poly_w, predicate='intersects')
        idx = idx[(self.lo[idx] - self.gap <= z1) & (self.hi[idx] + self.gap >= z0)]
        if not len(idx): return None
        u = unary_union([self.fp[i] for i in idx])
        return u.intersection(self.core) if self.core is not None else u

    def near(self, poly_w, z0, z1):
        """any triangle column whose footprint meets the world plan polygon and whose band meets [z0, z1]."""
        if self.tree is None: return False
        idx = self.tree.query(poly_w, predicate='intersects')
        return bool(len(idx)) and bool(((self.lo[idx] - self.clear_z <= z1) & (self.hi[idx] + self.clear_z >= z0)).any())


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


def _triangulate(g):
    """triangles of a polygon (holes allowed): GEOS constrained Delaunay; on a GEOS failure (near-degenerate rings) the
    polygon cleaned at 1 mm, else an unconstrained Delaunay kept where the triangle's centroid lies inside."""
    for gg in (g, g.buffer(-1e-4, join_style=2).buffer(1e-4, join_style=2).simplify(1e-3)):
        try:
            if gg.is_empty: return []
            return [t for t in shapely.constrained_delaunay_triangles(gg).geoms]
        except shapely.errors.GEOSException:
            continue
    return [t for t in shapely.delaunay_triangles(g).geoms if g.contains(t.centroid)]


def clip_mb(mb, to_world, cols, stats=None, ds_v=DS_V, ds_h=DS_H, cols_h=None):
    """clear the faces of mb (a landside_mesh.MB in a building's local frame; to_world(X, Y) -> world (x, z), Z = height)
    out of the column hull `cols` (non-vertical faces: `cols_h` when given - a contact hull without the per-triangle buffer,
    whose cut is intersected with the exact footprint anyway). Returns the cut area (m2)."""
    ch = cols_h if cols_h is not None else cols
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
            # vertical face: equal steps over the WHOLE horizontal extent, exact z intervals
            ns = max(1, int(math.ceil((u1 - u0) / ds_v - 1e-9)))
            stp = (u1 - u0) / ns
            ss = u0 + (np.arange(ns) + 0.5) * stp
            pl = o[None, :] + ss[:, None] * e1[None, :]
            pw = np.array([to_world(x, y) for x, y in pl[:, :2]])
            ivs = cols.intervals(pw)
            run = None
            cz = cols.clear_z
            for s_, iv in zip(ss, ivs):
                key = tuple((round(a - cz - o[2], 2), round(b + cz - o[2], 2)) for a, b in iv if b + cz > o[2] + v0 and a - cz < o[2] + v1)
                if run is not None and run[2] == key:
                    run[1] = s_ + stp / 2
                else:
                    if run is not None and run[2]: marks.append(run)
                    run = [s_ - stp / 2, s_ + stp / 2, key]
            if run is not None and run[2]: marks.append(run)
            rects = [shapely.box(a, lo, b, hi) for a, b, key in marks for lo, hi in key]
            fp_f = None
            if cols.core is not None and rects:
                # contact hull: the cut's ends along the face are the core outline itself (the step's half-width would let a
                # remnant reach up to inset + DS_V / 2 into the solid)
                wA = np.array(to_world(*(o + u0 * e1)[:2]), float); wB = np.array(to_world(*(o + u1 * e1)[:2]), float)
                Ls_ = float(np.linalg.norm(wB - wA))
                if Ls_ > 1e-9:
                    seg = shapely.LineString([wA, wB]).intersection(cols.core)
                    bands = []
                    for piece in getattr(seg, 'geoms', [seg]):
                        if piece.is_empty or piece.geom_type != 'LineString': continue
                        t_ = [float(np.linalg.norm(np.array(c_) - wA)) / Ls_ for c_ in piece.coords]
                        bands.append(shapely.box(u0 + (u1 - u0) * min(t_), v0 - 1.0, u0 + (u1 - u0) * max(t_), v1 + 1.0))
                    fp_f = unary_union(bands) if bands else Polygon()
        else:
            rects, fp_f = [], None
            fp_w = ch.footprint(hull, z.min(), z.max())
            if fp_w is not None:
                # face frame (s, t) -> world plan: w = p0 + M [s, t] (affine; invertible for a non-vertical face)
                p0 = np.array(to_world(*o[:2]), float)
                M = np.c_[np.array(to_world(*(o + e1)[:2])) - p0, np.array(to_world(*(o + e2)[:2])) - p0]
                Mi = np.linalg.inv(M); off = -Mi @ p0
                fp_f = affinity.affine_transform(fp_w, [Mi[0, 0], Mi[0, 1], Mi[1, 0], Mi[1, 1], off[0], off[1]])
                reg = poly.intersection(fp_f)
            if fp_f is not None and not reg.is_empty and reg.area > 1e-6:
                r0, r1, r2, r3 = reg.bounds
                nu = max(1, int(math.ceil((r2 - r0) / ds_h - 1e-9))); nv = max(1, int(math.ceil((r3 - r1) / ds_h - 1e-9)))
                du, dv = (r2 - r0) / nu, (r3 - r1) / nv
                gu, gv = np.meshgrid(r0 + (np.arange(nu) + 0.5) * du, r1 + (np.arange(nv) + 0.5) * dv, indexing='ij')
                G = np.c_[gu.ravel(), gv.ravel()]
                keep = shapely.intersects_xy(reg.buffer(0.75 * max(du, dv)), G[:, 0], G[:, 1])
                G = G[keep]
                if len(G):
                    offs = np.array([(0, 0), (-.5, -.5), (.5, -.5), (.5, .5), (-.5, .5)]) * [du, dv]
                    S5 = (G[:, None, :] + offs[None]).reshape(-1, 2)
                    P3 = o[None, :] + S5[:, :1] * e1[None, :] + S5[:, 1:] * e2[None, :]
                    pw = np.array([to_world(x, y) for x, y in P3[:, :2]])
                    ivs = ch.intervals(pw)
                    hit = np.array([any(a + Z_TOL < p3[2] < b - Z_TOL for a, b in iv) for p3, iv in zip(P3, ivs)]).reshape(-1, 5).any(1)
                    rects = [shapely.box(g[0] - du / 2, g[1] - dv / 2, g[0] + du / 2, g[1] + dv / 2) for g in G[hit]]
        if not rects:
            keepF.append(f); keepM.append(m); keepUV.append(uv); keepS.append(sm); continue
        cut = unary_union(rects)
        if fp_f is not None: cut = cut.intersection(fp_f)
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
            for tri in _triangulate(g):
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
