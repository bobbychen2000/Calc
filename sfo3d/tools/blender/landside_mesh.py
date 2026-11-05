"""Mesh helpers of the 3-D landside asset (tools/blender/build_landside.py): an indexed polygon mesh builder with per-face
material, per-corner tiling UV and a smooth flag, plus the extrusion / facade / cap / tube primitives the building
modules use. Pure numpy / shapely (no bpy).

Local frame of every building node: Blender X = x - ox (east), Y = oz - z (north), Z = height above local grade (m),
with (ox, oz) the building's origin in the app world frame (x east, z south, metres from the ARP; js/geo.js).
Faces are wound so that their normal points out of the solid (single-sided materials; checked by the back-face QA render).
"""
import math

import numpy as np
import shapely
from shapely import affinity
from shapely.geometry import Polygon, MultiPolygon, LineString, Point
from shapely.geometry.polygon import orient


class MB:
    """indexed polygon mesh (Blender local coords) with per-face material, per-corner UV (UV_detail: metres / tile) and
    a smooth flag. Vertices are shared only within a named group (sharp edges between groups)."""

    def __init__(self, name=''):
        self.name = name
        self.V, self.F, self.M, self.UV, self.S = [], [], [], [], []
        self._key = {}

    def v(self, p, grp=None):
        if grp is None:
            self.V.append((float(p[0]), float(p[1]), float(p[2]))); return len(self.V) - 1
        k = (grp, round(p[0], 4), round(p[1], 4), round(p[2], 4))
        i = self._key.get(k)
        if i is None:
            self.V.append((float(p[0]), float(p[1]), float(p[2]))); i = len(self.V) - 1; self._key[k] = i
        return i

    def face(self, pts, mat, uvs, smooth=False, grp=None):
        idx = [self.v(p, grp) for p in pts]
        out, ouv = [], []
        for i, t in zip(idx, uvs):
            if out and out[-1] == i: continue
            out.append(i); ouv.append(t)
        if len(out) > 1 and out[0] == out[-1]: out.pop(); ouv.pop()
        if len(out) < 3: return
        P = np.array([self.V[i] for i in out])
        n = np.zeros(3)
        for a in range(len(P)):
            n += np.cross(P[a], P[(a + 1) % len(P)])
        if np.linalg.norm(n) < 1e-7: return
        self.F.append(out); self.M.append(mat); self.UV.append([(float(t[0]), float(t[1])) for t in ouv]); self.S.append(smooth)

    def quad_wall(self, a, b, z0a, z1a, z0b, z1b, mat, s0=0.0, tile=(3.0, 3.0), grp=None, smooth=False, v0=0.0):
        """vertical quad from plan point a to b; outward normal = right of a->b. UV = (along / tu, (z - v0) / tv)."""
        L = math.hypot(b[0] - a[0], b[1] - a[1]); tu, tv = tile
        if L < 1e-4 or (z1a - z0a < 1e-4 and z1b - z0b < 1e-4): return
        self.face([(a[0], a[1], z0a), (b[0], b[1], z0b), (b[0], b[1], z1b), (a[0], a[1], z1a)], mat,
                  [(s0 / tu, (z0a - v0) / tv), ((s0 + L) / tu, (z0b - v0) / tv), ((s0 + L) / tu, (z1b - v0) / tv), (s0 / tu, (z1a - v0) / tv)],
                  smooth, grp)

    def merge(self, o):
        off = len(self.V)
        self.V += o.V
        self.F += [[i + off for i in f] for f in o.F]
        self.M += o.M; self.UV += o.UV; self.S += o.S

    def tris(self):
        return sum(len(f) - 2 for f in self.F)

    def bbox(self):
        P = np.array(self.V) if self.V else np.zeros((1, 3)); return P.min(0), P.max(0)

    def empty(self):
        return not self.F


# ------------------------------------------------------------------------------------------------ frames
class Frame:
    """building-local frame: world (x, z) <-> Blender local (X, Y)."""

    def __init__(self, ox, oz):
        self.ox, self.oz = float(ox), float(oz)

    def L(self, x, z):
        return (x - self.ox, self.oz - z)

    def W(self, X, Y):
        return (X + self.ox, self.oz - Y)

    def poly(self, P):
        """shapely polygon in world (x, z) -> local XY, CCW exteriors."""
        g = affinity.affine_transform(P, [1, 0, 0, -1, -self.ox, self.oz])
        return orient_all(g)

    def wpoly(self, P):
        g = affinity.affine_transform(P, [1, 0, 0, -1, self.ox, self.oz])
        return orient_all(g)


def orient_all(g):
    if g.is_empty: return g
    if isinstance(g, Polygon): return orient(g, 1.0)
    if isinstance(g, MultiPolygon): return MultiPolygon([orient(p, 1.0) for p in g.geoms])
    if hasattr(g, 'geoms'):
        ps = [orient(p, 1.0) for p in g.geoms if isinstance(p, Polygon) and p.area > 1e-6]
        return MultiPolygon(ps) if ps else Polygon()
    return g


def polys(g):
    if g is None or g.is_empty: return []
    if isinstance(g, Polygon): return [g]
    return [p for p in getattr(g, 'geoms', []) if isinstance(p, Polygon) and p.area > 1e-4]


def rings_of(poly):
    """exterior (CCW) + interiors (CW after orient): walking a->b, outward is on the right for both."""
    return [list(poly.exterior.coords)[:-1]] + [list(r.coords)[:-1] for r in poly.interiors]


def clean(poly, tol=0.05):
    g = poly.buffer(0).simplify(tol, preserve_topology=True)
    return orient_all(g)


# ------------------------------------------------------------------------------------------------ triangulation / caps
def tri_poly(poly):
    out = []
    for p in polys(poly):
        for t in shapely.constrained_delaunay_triangles(p).geoms:
            c = list(t.exterior.coords)[:3]
            A = (c[1][0] - c[0][0]) * (c[2][1] - c[0][1]) - (c[2][0] - c[0][0]) * (c[1][1] - c[0][1])
            if abs(A) < 1e-8: continue
            out.append(c if A > 0 else c[::-1])
    return out


def cap(mb, poly, z, mat, tile=(6.0, 6.0), down=False, grp=None, uvf=None, zf=None):
    """horizontal cap of a polygon at height z (or zf(x, y)); UV planar / tile, or uvf(x, y) -> (u, v)."""
    tu, tv = (tile, tile) if not isinstance(tile, (tuple, list)) else tile
    for t in tri_poly(poly):
        pts = t[::-1] if down else t
        P = [(p[0], p[1], zf(p[0], p[1]) if zf else z) for p in pts]
        uv = [uvf(p[0], p[1]) for p in pts] if uvf else [(p[0] / tu, p[1] / tv) for p in pts]
        mb.face(P, mat, uv, False, grp)


def walls(mb, poly, z0, z1, mat, tile=(3.0, 3.0), edge_filter=None, offset=0.0):
    """vertical walls of every ring of a polygon from z0 to z1, outward (offset > 0: pushed outward)."""
    for p in polys(poly):
        for ring in rings_of(p):
            s = 0.0
            n = len(ring)
            for i in range(n):
                a, b = ring[i], ring[(i + 1) % n]
                L = math.hypot(b[0] - a[0], b[1] - a[1])
                if L < 1e-4: continue
                if edge_filter is None or edge_filter(a, b):
                    if offset:
                        nx, ny = (b[1] - a[1]) / L, -(b[0] - a[0]) / L
                        a2, b2 = (a[0] + nx * offset, a[1] + ny * offset), (b[0] + nx * offset, b[1] + ny * offset)
                    else:
                        a2, b2 = a, b
                    mb.quad_wall(a2, b2, z0, z1, z0, z1, mat, s, tile)
                s += L


def prism(mb, poly, z0, z1, wall_mat, top_mat=None, bottom_mat=None, tile=(3.0, 3.0), top_tile=6.0):
    walls(mb, poly, z0, z1, wall_mat, tile)
    if top_mat: cap(mb, poly, z1, top_mat, top_tile)
    if bottom_mat: cap(mb, poly, z0, bottom_mat, top_tile, down=True)


def ring_band(poly, w):
    """ring of width w inside the outline (parapet / coping)."""
    inner = poly.buffer(-w, join_style=2)
    return orient_all(poly.difference(inner)), orient_all(inner)


def parapet(mb, poly, z_deck, z_top, mat, thk=0.25, deck_mat=None, deck_uv=None, deck_tile=6.0):
    """parapet around a roof outline: the outer face is drawn by the facade; here the inner face, the coping and the deck."""
    ring, inner = ring_band(poly, thk)
    cap(mb, ring, z_top, mat, 1.0)
    for q in polys(inner):
        for r in rings_of(q):
            n = len(r)
            for i in range(n):
                a, b = r[i], r[(i + 1) % n]
                mb.quad_wall(b, a, z_deck, z_top, z_deck, z_top, mat, 0.0, (3.0, 3.0))   # facing inward (onto the deck)
        if deck_mat:
            cap(mb, q, z_deck, deck_mat, deck_tile, uvf=deck_uv)
    return inner


# ------------------------------------------------------------------------------------------------ primitives
def boxm(mb, c, d, w, h, z, mat, tile=(3.0, 3.0), top=True, bottom=False, top_mat=None):
    """oriented box: plan centre c, unit direction d (length w along d, width h across), z = (z0, z1)."""
    d = np.asarray(d, float); d = d / np.linalg.norm(d); n = np.array([d[1], -d[0]])
    c = np.asarray(c, float); za, zb = z
    pts = [c - d * w / 2 - n * h / 2, c + d * w / 2 - n * h / 2, c + d * w / 2 + n * h / 2, c - d * w / 2 + n * h / 2]
    pts = [tuple(p) for p in pts]
    A = sum(pts[i][0] * pts[(i + 1) % 4][1] - pts[(i + 1) % 4][0] * pts[i][1] for i in range(4))
    ring = pts if A > 0 else pts[::-1]
    s = 0.0
    for i in range(4):
        a, b = ring[i], ring[(i + 1) % 4]
        mb.quad_wall(a, b, za, zb, za, zb, mat, s, tile)
        s += math.hypot(b[0] - a[0], b[1] - a[1])
    if top: mb.face([(p[0], p[1], zb) for p in ring], top_mat or mat, [(p[0] / tile[0], p[1] / tile[1]) for p in ring])
    if bottom: mb.face([(p[0], p[1], za) for p in ring[::-1]], mat, [(p[0] / tile[0], p[1] / tile[1]) for p in ring[::-1]])


def cyl(mb, c, r, z0, z1, n, mat, tile=(3.0, 3.0), top=None, bottom=False, smooth=True, v0=0.0, uv_scale_u=None):
    """vertical cylinder; UV u = arc length / tile (or uv_scale_u turns per texture), v = (z - v0) / tile."""
    ang = np.linspace(0, 2 * math.pi, n + 1)
    pts = [(c[0] + r * math.cos(a), c[1] + r * math.sin(a)) for a in ang]
    g = ('cyl', id(pts))
    circ = 2 * math.pi * r
    for i in range(n):
        a, b = pts[i], pts[i + 1]
        u0 = (circ * i / n) / tile[0]; u1 = (circ * (i + 1) / n) / tile[0]
        mb.face([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)], mat,
                [(u0, (z0 - v0) / tile[1]), (u1, (z0 - v0) / tile[1]), (u1, (z1 - v0) / tile[1]), (u0, (z1 - v0) / tile[1])], smooth, g if smooth else None)
    if top:
        mb.face([(p[0], p[1], z1) for p in pts[:-1]], top, [(p[0] / 6.0, p[1] / 6.0) for p in pts[:-1]])
    if bottom:
        mb.face([(p[0], p[1], z0) for p in pts[:-1][::-1]], mat, [(p[0] / 6.0, p[1] / 6.0) for p in pts[:-1][::-1]])


def tube(mb, pts, r, sides, mat, tile=4.0, cap_ends=False):
    """tube along a polyline, parallel-transport frames, smooth shading."""
    P = np.asarray(pts, float)
    if len(P) < 2: return
    keep = np.r_[True, np.linalg.norm(np.diff(P, axis=0), axis=1) > 1e-6]; P = P[keep]
    if len(P) < 2: return
    T = np.diff(P, axis=0); T /= np.linalg.norm(T, axis=1)[:, None]
    tang = np.vstack([T[0], (T[:-1] + T[1:]), T[-1]]); tang /= np.linalg.norm(tang, axis=1)[:, None]
    ref = np.array([0, 0, 1.0]) if abs(tang[0][2]) < 0.9 else np.array([1.0, 0, 0])
    n = np.cross(tang[0], ref); n /= np.linalg.norm(n)
    frames = []
    for t in tang:
        n = n - t * np.dot(n, t); n /= np.linalg.norm(n)
        frames.append((n, np.cross(t, n)))
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    ang = np.linspace(0, 2 * math.pi, sides + 1)
    rings = [[P[i] + r * (math.cos(a) * frames[i][0] + math.sin(a) * frames[i][1]) for a in ang[:-1]] for i in range(len(P))]
    g = ('tube', id(rings))
    for i in range(len(P) - 1):
        for j in range(sides):
            j2 = (j + 1) % sides
            a0, a1 = j / sides, (j + 1) / sides
            mb.face([rings[i][j], rings[i][j2], rings[i + 1][j2], rings[i + 1][j]], mat,
                    [(s[i] / tile, a0), (s[i] / tile, a1), (s[i + 1] / tile, a1), (s[i + 1] / tile, a0)], True, g)
    if cap_ends:
        for i, sg in ((0, -1), (len(P) - 1, 1)):
            ring = rings[i] if sg > 0 else rings[i][::-1]
            mb.face(ring, mat, [(0.5, 0.5)] * len(ring))


def inset_ring(ring, d, closed=True):
    """mitred inward offset of a ring (outward = right of a->b), clamped at 2.5 d (for the dark interiors behind open
    garage levels: small self-overlaps at tight corners stay inside the building)."""
    P = np.asarray(ring, float); n = len(P)
    out = []
    for i in range(n):
        a, b, c = P[i - 1], P[i], P[(i + 1) % n]
        e1 = b - a; e2 = c - b
        l1, l2 = np.linalg.norm(e1), np.linalg.norm(e2)
        n1 = np.array([e1[1], -e1[0]]) / (l1 or 1); n2 = np.array([e2[1], -e2[0]]) / (l2 or 1)
        m = n1 + n2; mm = np.linalg.norm(m)
        if mm < 1e-6:
            off = n2
        else:
            m /= mm; cosh = max(0.4, float(np.dot(m, n2))); off = m / cosh
        out.append(tuple(b - off * d))
    return out
