"""Geometry kit for the house model: flat-shaded architectural primitives with world-scale UVs.

World axes (metres): X = along the street, to the right when facing the house from the street;
Y = into the lot (street -> back fence); Z = up, 0 = the house's finished grade at the driveway apron.
A Mesh holds one material; every primitive emits its own vertices per face (crisp edges) with a face normal
and UVs in METRES (u along the face's horizontal / long direction, v up or up-slope), so tiling textures keep
their real size whatever the face.
"""
from __future__ import annotations

import numpy as np

try:
    import mapbox_earcut as earcut
except Exception:  # pragma: no cover
    earcut = None

UP = np.array([0.0, 0.0, 1.0])


def _unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


class Mesh:
    """Triangle soup of one material: V (n, 3), N (n, 3), UV (n, 2), F (m, 3)."""

    def __init__(self, mat, V=None, N=None, UV=None, F=None):
        self.mat = mat
        self.V = np.zeros((0, 3)) if V is None else np.asarray(V, float).reshape(-1, 3)
        self.N = np.zeros((0, 3)) if N is None else np.asarray(N, float).reshape(-1, 3)
        self.UV = np.zeros((0, 2)) if UV is None else np.asarray(UV, float).reshape(-1, 2)
        self.F = np.zeros((0, 3), int) if F is None else np.asarray(F, int).reshape(-1, 3)

    def add(self, V, N, UV, F):
        o = len(self.V)
        self.V = np.vstack([self.V, np.asarray(V, float).reshape(-1, 3)])
        self.N = np.vstack([self.N, np.asarray(N, float).reshape(-1, 3)])
        self.UV = np.vstack([self.UV, np.asarray(UV, float).reshape(-1, 2)])
        self.F = np.vstack([self.F, np.asarray(F, int).reshape(-1, 3) + o])
        return self

    def merge(self, other):
        return self.add(other.V, other.N, other.UV, other.F)

    def transformed(self, R=None, t=None):
        V = self.V if R is None else self.V @ np.asarray(R, float).T
        N = self.N if R is None else self.N @ np.asarray(R, float).T
        if t is not None:
            V = V + np.asarray(t, float)
        return Mesh(self.mat, V, N, self.UV, self.F)

    @property
    def ntri(self):
        return len(self.F)


class Geo:
    """A bag of meshes keyed by material; the primitives below append to it."""

    def __init__(self):
        self.m = {}

    def mesh(self, mat):
        if mat not in self.m:
            self.m[mat] = Mesh(mat)
        return self.m[mat]

    def meshes(self):
        return [m for m in self.m.values() if m.ntri]

    def merge(self, other, R=None, t=None):
        for m in other.meshes():
            self.mesh(m.mat).merge(m.transformed(R, t) if (R is not None or t is not None) else m)
        return self

    @property
    def ntri(self):
        return sum(m.ntri for m in self.m.values())

    # ---- polygons -------------------------------------------------------------------------------------------
    def poly(self, mat, pts, holes=(), uv_u=None, uv_o=None, flip=False):
        """Planar polygon (3-D points, counter-clockwise seen from the side its normal points to) with optional
        holes (lists of 3-D points in the same plane).  uv_u: the in-plane direction of u (default: horizontal)."""
        pts = np.asarray(pts, float)
        n = _newell(pts)
        if flip:
            n = -n
        if uv_u is None:
            h = np.cross(UP, n)
            uv_u = _unit(h) if np.linalg.norm(h) > 1e-6 else np.array([1.0, 0.0, 0.0])
        uv_u = _unit(uv_u)
        uv_v = np.cross(n, uv_u)
        o = pts[0] if uv_o is None else np.asarray(uv_o, float)
        rings = [pts] + [np.asarray(h, float) for h in holes]
        allp = np.vstack(rings)
        uv = np.stack([(allp - o) @ uv_u, (allp - o) @ uv_v], -1)
        if len(rings) == 1 and len(pts) == 3:
            tri = np.array([[0, 1, 2]])
        elif len(rings) == 1 and len(pts) == 4 and _convex(uv):
            tri = np.array([[0, 1, 2], [0, 2, 3]])
        else:
            ends = np.cumsum([len(r) for r in rings]).astype(np.uint32)
            tri = earcut.triangulate_float64(uv, ends).reshape(-1, 3)
        # orient the triangles with the normal
        a, b, c = allp[tri[:, 0]], allp[tri[:, 1]], allp[tri[:, 2]]
        s = np.einsum('ij,j->i', np.cross(b - a, c - a), n)
        tri = np.where((s < 0)[:, None], tri[:, ::-1], tri)
        self.mesh(mat).add(allp, np.tile(n, (len(allp), 1)), uv, tri)
        return self

    def quad(self, mat, p0, p1, p2, p3, **kw):
        return self.poly(mat, [p0, p1, p2, p3], **kw)

    # ---- solids ---------------------------------------------------------------------------------------------
    def box(self, mat, lo, hi, faces='xXyYzZ', mats=None):
        """Axis-aligned box.  faces: which of -x +x -y +y -z +z to emit; mats: {face letter: material}."""
        x0, y0, z0 = lo
        x1, y1, z1 = hi
        mats = mats or {}
        P = lambda *p: np.array(p, float)
        quads = {
            'x': [P(x0, y1, z0), P(x0, y0, z0), P(x0, y0, z1), P(x0, y1, z1)],
            'X': [P(x1, y0, z0), P(x1, y1, z0), P(x1, y1, z1), P(x1, y0, z1)],
            'y': [P(x0, y0, z0), P(x1, y0, z0), P(x1, y0, z1), P(x0, y0, z1)],
            'Y': [P(x1, y1, z0), P(x0, y1, z0), P(x0, y1, z1), P(x1, y1, z1)],
            'z': [P(x0, y1, z0), P(x1, y1, z0), P(x1, y0, z0), P(x0, y0, z0)],
            'Z': [P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1)],
        }
        for f in faces:
            self.poly(mats.get(f, mat), quads[f])
        return self

    def obox(self, mat, origin, ex, ey, ez, lo, hi, faces='xXyYzZ', mats=None):
        """Box in a local frame (origin + unit axes ex, ey, ez): lo / hi are local coordinates."""
        g = Geo().box(mat, lo, hi, faces, mats)
        R = np.stack([_unit(ex), _unit(ey), _unit(ez)], 1)
        return self.merge(g, R=R, t=np.asarray(origin, float))

    def extrude(self, mat, ring_xy, z0, z1, cap_bottom=True, cap_top=True, holes=(), mat_top=None, mat_bottom=None,
                side=True):
        """Vertical prism over a plan polygon (counter-clockwise ring of (x, y)) from z0 to z1."""
        ring = np.asarray(ring_xy, float)
        if _area2(ring) < 0:
            ring = ring[::-1]
        if side:
            for r, rev in [(ring, False)] + [(np.asarray(h, float), True) for h in holes]:
                if (_area2(r) < 0) != rev:
                    r = r[::-1]
                for i in range(len(r)):
                    a, b = r[i], r[(i + 1) % len(r)]
                    self.poly(mat, [(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)])
        h3 = lambda r, z: [[(p[0], p[1], z) for p in np.asarray(h, float)] for h in r]
        if cap_top:
            self.poly(mat_top or mat, [(p[0], p[1], z1) for p in ring], holes=h3(holes, z1), uv_u=(1, 0, 0),
                      uv_o=(0, 0, z1))
        if cap_bottom:
            self.poly(mat_bottom or mat, [(p[0], p[1], z0) for p in ring[::-1]], holes=h3(holes, z0), uv_u=(1, 0, 0),
                      uv_o=(0, 0, z0))
        return self

    def prism(self, mat, section, a, b, up=UP, cap=True):
        """Sweep a closed 2-D section (list of (s, t): s sideways, t along `up`) from point a to point b."""
        a, b = np.asarray(a, float), np.asarray(b, float)
        d = _unit(b - a)
        side = _unit(np.cross(d, up))
        upv = np.cross(side, d)
        sec = np.asarray(section, float)
        if _area2(sec) < 0:
            sec = sec[::-1]
        ra = [a + s * side + t * upv for s, t in sec]
        rb = [b + s * side + t * upv for s, t in sec]
        n = len(sec)
        for i in range(n):
            j = (i + 1) % n
            self.poly(mat, [ra[i], rb[i], rb[j], ra[j]], uv_u=d)
        if cap:
            self.poly(mat, ra)
            self.poly(mat, rb[::-1])
        return self

    def cylinder(self, mat, a, b, r, n=16, cap=True):
        ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
        return self.prism_smooth(mat, [(r * np.cos(t), r * np.sin(t)) for t in ang], a, b, cap=cap)

    def prism_smooth(self, mat, section, a, b, up=UP, cap=True):
        """Like prism() but with smooth normals round the section (tubes, round posts)."""
        a, b = np.asarray(a, float), np.asarray(b, float)
        d = _unit(b - a)
        if abs(d @ _unit(up)) > 0.99:
            up = np.array([1.0, 0.0, 0.0])
        side = _unit(np.cross(d, up))
        upv = np.cross(side, d)
        sec = np.asarray(section, float)
        if _area2(sec) < 0:
            sec = sec[::-1]
        n = len(sec)
        c = sec.mean(0)
        ra = np.array([a + s * side + t * upv for s, t in sec])
        rb = np.array([b + s * side + t * upv for s, t in sec])
        nr = np.array([_unit((s - c[0]) * side + (t - c[1]) * upv) for s, t in sec])
        per = np.concatenate([[0], np.cumsum(np.linalg.norm(np.roll(sec, -1, 0) - sec, axis=1))])
        L = np.linalg.norm(b - a)
        V = np.vstack([ra, ra[:1], rb, rb[:1]])
        N = np.vstack([nr, nr[:1], nr, nr[:1]])
        UV = np.vstack([np.stack([np.zeros(n + 1), per], -1), np.stack([np.full(n + 1, L), per], -1)])
        F = []
        for i in range(n):
            F += [[i, n + 1 + i, n + 2 + i], [i, n + 2 + i, i + 1]]
        self.mesh(mat).add(V, N, UV, F)
        if cap:
            self.poly(mat, ra)
            self.poly(mat, rb[::-1])
        return self


def _newell(p):
    q = np.roll(p, -1, 0)
    n = np.array([((p[:, 1] - q[:, 1]) * (p[:, 2] + q[:, 2])).sum(),
                  ((p[:, 2] - q[:, 2]) * (p[:, 0] + q[:, 0])).sum(),
                  ((p[:, 0] - q[:, 0]) * (p[:, 1] + q[:, 1])).sum()])
    return _unit(n)


def _area2(r):
    r = np.asarray(r, float)
    q = np.roll(r, -1, 0)
    return float((r[:, 0] * q[:, 1] - q[:, 0] * r[:, 1]).sum())


def _convex(uv):
    q, r = np.roll(uv, -1, 0), np.roll(uv, -2, 0)
    c = (q[:, 0] - uv[:, 0]) * (r[:, 1] - q[:, 1]) - (q[:, 1] - uv[:, 1]) * (r[:, 0] - q[:, 0])
    return bool((c > 0).all() or (c < 0).all())


class Part:
    """A named node of the model: meshes + free-form extras (written into the glTF node)."""

    def __init__(self, name, geo: Geo, group='house', extras=None):
        self.name, self.geo, self.group, self.extras = name, geo, group, dict(extras or {})

    @property
    def ntri(self):
        return self.geo.ntri
