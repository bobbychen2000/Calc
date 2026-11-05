"""Mesh helpers of the 3-D domestic terminals asset (tools/blender/build_domestic.py): an indexed polygon mesh builder
with per-face material, per-corner tiling UV (UV_detail, metres / tile) and a smooth flag, plus the extrusion / cap / box /
tube primitives the part builders of tools/blender/dom_geom.py use. Pure numpy / shapely (no bpy).

Coordinates are Blender local: X = x - OX (east), Y = OZ - z (north), Z = height above the local apron (m). Faces are wound
so that their normal points out of the solid (single-sided materials, checked by the back-face QA render).
(Same conventions as tools/blender/itb_geom.py; kept as a separate module so that the domestic build does not depend on the
ITB / landside modules.)
"""
import math

import numpy as np
import shapely
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.polygon import orient


class MB:
    """indexed polygon mesh with per-face material, per-corner UV and a smooth flag. Vertices are de-duplicated only within
    a named group (grp), so edges between groups stay sharp."""

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
            if out and (out[-1] == i or self.V[out[-1]] == self.V[i]): continue
            out.append(i); ouv.append(t)
        while len(out) > 1 and (out[0] == out[-1] or self.V[out[0]] == self.V[out[-1]]): out.pop(); ouv.pop()
        if len(out) < 3: return
        P = np.array([self.V[i] for i in out])
        n = np.zeros(3)
        for a in range(len(P)):
            n += np.cross(P[a], P[(a + 1) % len(P)])
        if np.linalg.norm(n) < 1e-6: return
        self.F.append(out); self.M.append(mat); self.UV.append([(float(t[0]), float(t[1])) for t in ouv]); self.S.append(smooth)

    def quad_wall(self, a, b, z0a, z1a, z0b, z1b, mat, s0=0.0, tile=(3.0, 3.0), grp=None, smooth=False, v0=0.0):
        """vertical quad from plan point a to b; outward normal = right of a->b. UV = (along / tu, (z - v0) / tv)."""
        L = math.hypot(b[0] - a[0], b[1] - a[1]); tu, tv = tile
        if L < 1e-4 or (z1a - z0a < 1e-4 and z1b - z0b < 1e-4): return
        self.face([(a[0], a[1], z0a), (b[0], b[1], z0b), (b[0], b[1], z1b), (a[0], a[1], z1a)], mat,
                  [(s0 / tu, (z0a - v0) / tv), ((s0 + L) / tu, (z0b - v0) / tv), ((s0 + L) / tu, (z1b - v0) / tv),
                   (s0 / tu, (z1a - v0) / tv)], smooth, grp)

    def merge(self, o):
        off = len(self.V)
        self.V += o.V
        self.F += [[i + off for i in f] for f in o.F]
        self.M += o.M; self.UV += o.UV; self.S += o.S
        return self

    def tris(self):
        return sum(len(f) - 2 for f in self.F)

    def bbox(self):
        P = np.array(self.V) if self.V else np.zeros((1, 3)); return P.min(0), P.max(0)

    def empty(self):
        return not self.F


# ------------------------------------------------------------------------------------------------ shapely helpers
def orient_all(g):
    if g is None or g.is_empty: return Polygon()
    if isinstance(g, Polygon): return orient(g, 1.0)
    ps = [orient(p, 1.0) for p in getattr(g, 'geoms', []) if isinstance(p, Polygon) and p.area > 1e-6]
    return MultiPolygon(ps) if ps else Polygon()


def polys(g, a_min=1e-4):
    if g is None or g.is_empty: return []
    if isinstance(g, Polygon): return [g] if g.area > a_min else []
    out = []
    for p in getattr(g, 'geoms', []):
        out += polys(p, a_min)
    return out


def rings_of(poly):
    """exterior (CCW) + interiors (CW after orient): walking a->b, outward is on the right for both."""
    p = orient(poly, 1.0)
    return [list(p.exterior.coords)[:-1]] + [list(r.coords)[:-1] for r in p.interiors]


def tri_poly(poly):
    """constrained Delaunay triangulation of a polygon (holes allowed) -> CCW triangles."""
    out = []
    for p in polys(poly):
        for t in shapely.constrained_delaunay_triangles(p).geoms:
            c = list(t.exterior.coords)[:3]
            A = (c[1][0] - c[0][0]) * (c[2][1] - c[0][1]) - (c[2][0] - c[0][0]) * (c[1][1] - c[0][1])
            if abs(A) < 1e-8: continue
            out.append(c if A > 0 else c[::-1])
    return out


def cap(mb, poly, z, mat, tile=6.0, down=False, grp=None, zf=None, uvf=None):
    """horizontal cap of a polygon at height z (or zf(x, y)); planar UV in metres / tile (or uvf(x, y))."""
    tu, tv = (tile, tile) if not isinstance(tile, (tuple, list)) else tile
    for t in tri_poly(poly):
        pts = t[::-1] if down else t
        P = [(p[0], p[1], zf(p[0], p[1]) if zf else z) for p in pts]
        uv = [uvf(p[0], p[1]) for p in pts] if uvf else [(p[0] / tu, p[1] / tv) for p in pts]
        mb.face(P, mat, uv, False, grp)


def ring_walls(mb, poly, z0, z1, mat, tile=(3.0, 3.0), inward=False):
    """vertical walls of every ring of a polygon from z0 to z1, facing out (or into the polygon when inward=True)."""
    for p in polys(poly):
        for ring in rings_of(p):
            s = 0.0
            n = len(ring)
            for i in range(n):
                a, b = ring[i], ring[(i + 1) % n]
                L = math.hypot(b[0] - a[0], b[1] - a[1])
                if L < 1e-4: continue
                if inward: mb.quad_wall(b, a, z0, z1, z0, z1, mat, s, tile)
                else: mb.quad_wall(a, b, z0, z1, z0, z1, mat, s, tile)
                s += L


def prism(mb, poly, z0, z1, wall_mat, top_mat=None, bottom_mat=None, tile=(3.0, 3.0), top_tile=6.0):
    ring_walls(mb, poly, z0, z1, wall_mat, tile)
    if top_mat: cap(mb, poly, z1, top_mat, top_tile)
    if bottom_mat: cap(mb, poly, z0, bottom_mat, top_tile, down=True)


def boxm(mb, c, d, w, h, z, mat, tile=(3.0, 3.0), top=True, bottom=False, top_mat=None, sides=(1, 1, 1, 1)):
    """oriented box: plan centre c, unit direction d (length w along d, width h across), z = (z0, z1); sides = which of
    the four walls to emit (along -n, +d end, +n, -d end in CCW order)."""
    d = np.asarray(d, float); d = d / np.linalg.norm(d); n = np.array([d[1], -d[0]])
    c = np.asarray(c, float); za, zb = z
    pts = [c - d * w / 2 - n * h / 2, c + d * w / 2 - n * h / 2, c + d * w / 2 + n * h / 2, c - d * w / 2 + n * h / 2]
    pts = [tuple(p) for p in pts]
    A = sum(pts[i][0] * pts[(i + 1) % 4][1] - pts[(i + 1) % 4][0] * pts[i][1] for i in range(4))
    ring = pts if A > 0 else pts[::-1]
    sd = sides if A > 0 else (sides[2], sides[1], sides[0], sides[3])
    s = 0.0
    for i in range(4):
        a, b = ring[i], ring[(i + 1) % 4]
        if sd[i]: mb.quad_wall(a, b, za, zb, za, zb, mat, s, tile)
        s += math.hypot(b[0] - a[0], b[1] - a[1])
    if top: mb.face([(p[0], p[1], zb) for p in ring], top_mat or mat, [(p[0] / tile[0], p[1] / tile[1]) for p in ring])
    if bottom: mb.face([(p[0], p[1], za) for p in ring[::-1]], mat, [(p[0] / tile[0], p[1] / tile[1]) for p in ring[::-1]])


def box3(mb, P0, P1, w, h, mat, tile=(3.0, 3.0), up=(0, 0, 1.0), caps=True):
    """box along the 3-D segment P0 -> P1 with cross-section w (horizontal) x h (along 'up' projected), faces outward."""
    P0, P1 = np.asarray(P0, float), np.asarray(P1, float)
    t = P1 - P0; L = np.linalg.norm(t)
    if L < 1e-6: return
    t /= L
    u = np.asarray(up, float); u = u - t * np.dot(u, t)
    if np.linalg.norm(u) < 1e-6: u = np.array([1.0, 0, 0]) - t * t[0]
    u /= np.linalg.norm(u); s = np.cross(t, u)
    c = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    R0 = [P0 + s * a + u * b for a, b in c]; R1 = [P1 + s * a + u * b for a, b in c]
    for i in range(4):
        j = (i + 1) % 4
        mb.face([R0[i], R0[j], R1[j], R1[i]], mat, [(0, 0), (w / tile[0], 0), (w / tile[0], L / tile[1]), (0, L / tile[1])])
    if caps:
        mb.face(R0[::-1], mat, [(0, 0), (0, 1), (1, 1), (1, 0)])
        mb.face(R1, mat, [(0, 0), (1, 0), (1, 1), (0, 1)])


def cyl(mb, c, r, z0, z1, n, mat, tile=(3.0, 3.0), top=None, bottom=False, smooth=True, inward=False, a0=0.0):
    """vertical cylinder (n facets); UV u = arc length / tile, v = z / tile."""
    ang = a0 + np.linspace(0, 2 * math.pi, n + 1)
    pts = [(c[0] + r * math.cos(a), c[1] + r * math.sin(a)) for a in ang]
    g = ('cyl', id(pts)) if smooth else None
    circ = 2 * math.pi * r
    for i in range(n):
        a, b = pts[i], pts[i + 1]
        u0 = (circ * i / n) / tile[0]; u1 = (circ * (i + 1) / n) / tile[0]
        q = [(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)]
        uv = [(u0, z0 / tile[1]), (u1, z0 / tile[1]), (u1, z1 / tile[1]), (u0, z1 / tile[1])]
        if inward: q, uv = q[::-1], uv[::-1]
        mb.face(q, mat, uv, smooth, g)
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
