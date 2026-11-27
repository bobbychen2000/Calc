"""Roofs as measured planar polygons, and walls that rise from a base height to whatever roof is above them.

    planes = [RoofPlane('upper_front', pts=[(x, y, z), ...], mat='roof_shingle'), ...]
    roof_planes(geo, planes)                              # top skin, vertical fascia, underside (soffit)
    wall(geo, 'siding_lap', a=(x, y), b=(x, y), z0=0.0, planes=planes, holes=[(s0, z0, s1, z1), ...])
        -> outer face from z0 up to the lowest roof underside above each point of the wall line (gables and
           rakes follow the roof by themselves), with rectangular holes in wall coordinates (s along a->b).
The wall's outward normal is to the RIGHT of a->b seen from above (walk the footprint counter-clockwise... no:
clockwise) - i.e. list a footprint's corners clockwise seen from above and every wall faces out.
"""
from __future__ import annotations

import numpy as np

from model.kit import Geo, _unit

EPS = 1e-6


class RoofPlane:
    def __init__(self, name, pts, mat='roof_shingle', thickness=0.24, fascia='trim_white', soffit='soffit_white',
                 storey=2, eaves=None):
        self.name, self.mat, self.t, self.fascia, self.soffit, self.storey = name, mat, thickness, fascia, soffit, storey
        self.pts = np.asarray(pts, float)
        # least-squares plane z = ax + by + c through the measured corners (they are never exactly coplanar)
        A = np.c_[self.pts[:, 0], self.pts[:, 1], np.ones(len(self.pts))]
        self.abc = np.linalg.lstsq(A, self.pts[:, 2], rcond=None)[0]
        self.pts[:, 2] = A @ self.abc
        self.xy = self.pts[:, :2]
        if _area(self.xy) < 0:                      # keep counter-clockwise in plan (normal up)
            self.pts, self.xy = self.pts[::-1], self.xy[::-1]
        self.eaves = eaves                          # indices of edges that are eaves (get a gutter); None = unknown

    @property
    def pitch(self):
        return float(np.degrees(np.arctan(np.hypot(self.abc[0], self.abc[1]))))

    @property
    def downhill(self):
        """Unit plan vector pointing down the slope (zero vector for a flat roof)."""
        g = -np.array([self.abc[0], self.abc[1]])
        n = np.linalg.norm(g)
        return g / n if n > 1e-9 else np.zeros(2)

    def z(self, x, y):
        return self.abc[0] * x + self.abc[1] * y + self.abc[2]

    def contains(self, x, y, tol=0.0):
        return _inside(self.xy, x, y, tol)


def _area(r):
    q = np.roll(r, -1, 0)
    return float((r[:, 0] * q[:, 1] - q[:, 0] * r[:, 1]).sum()) / 2


def _inside(poly, x, y, tol=0.0):
    """Point in polygon (plan), with the boundary widened by tol (metres)."""
    inside = False
    n = len(poly)
    dmin = 1e9
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0 + 1e-30) + x0:
            inside = not inside
        if tol:
            d = np.array([x1 - x0, y1 - y0])
            t = np.clip(((x - x0) * d[0] + (y - y0) * d[1]) / (d @ d + 1e-30), 0, 1)
            dmin = min(dmin, np.hypot(x - x0 - t * d[0], y - y0 - t * d[1]))
    return inside or dmin <= tol


def roof_planes(geo: Geo, planes):
    """Top skin (u along the eave = across the slope, v up the slope), vertical fascia band, flat-following underside."""
    for p in planes:
        dn = p.downhill
        if np.linalg.norm(dn) < 1e-9:
            u_dir = np.array([1.0, 0.0, 0.0])
        else:
            u_dir = _unit(np.array([-dn[1], dn[0], 0.0]))          # along the eave, horizontal
        top = p.pts
        geo.poly(p.mat, top, uv_u=u_dir, uv_o=top[np.argmin(top[:, 2])])
        bot = top - np.array([0, 0, p.t])
        geo.poly(p.soffit, bot[::-1])
        n = len(top)
        for i in range(n):
            j = (i + 1) % n
            geo.poly(p.fascia, [bot[i], bot[j], top[j], top[i]], flip=False)
    return geo


def roof_underside(planes, x, y, above, tol=0.05):
    """Height of the lowest roof underside above `above` at plan point (x, y); None if no roof is over it."""
    best = None
    for p in planes:
        if p.contains(x, y, tol):
            z = p.z(x, y) - p.t
            if z > above + 0.05 and (best is None or z < best):
                best = z
    return best


def wall_top(planes, a, b, z0, step=0.05, default=None):
    """Top profile of a wall from a to b: [(s, z)] simplified to its corners."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    L = float(np.linalg.norm(b - a))
    n = max(2, int(np.ceil(L / step)) + 1)
    ss = np.linspace(0, L, n)
    zz = []
    for s in ss:
        s_in = min(max(s, 0.02), L - 0.02)            # sample just inside the ends (corners sit on plane edges)
        x, y = a + (b - a) * s_in / L
        z = roof_underside(planes, x, y, z0)
        zz.append(default if z is None else z)
    if any(z is None for z in zz):
        known = [z for z in zz if z is not None]
        fill = max(known) if known else z0 + 2.7
        zz = [fill if z is None else z for z in zz]
    zz = np.array(zz)
    keep = [0]
    for i in range(1, n - 1):                          # drop collinear samples
        s0, s1, s2 = ss[keep[-1]], ss[i], ss[i + 1]
        z_lin = zz[keep[-1]] + (zz[i + 1] - zz[keep[-1]]) * (s1 - s0) / (s2 - s0)
        if abs(z_lin - zz[i]) > 0.004:
            keep.append(i)
    keep.append(n - 1)
    return [(float(ss[i]), float(zz[i])) for i in keep]


def wall(geo: Geo, mat, a, b, z0, planes=(), z1=None, holes=(), thickness=0.0, reveal_mat=None, reveal=0.10):
    """Outer wall face from plan point a to b, base z0; top = z1 if given, else the roof above (wall_top).
    holes: (s0, zb, s1, zt) rectangles in wall coordinates; their reveals (depth `reveal`, inward) are added.
    Returns the wall frame dict(origin, right, out, length) for mounting things on it."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    L = float(np.linalg.norm(b - a))
    right = np.array([(b - a)[0] / L, (b - a)[1] / L, 0.0])
    out = np.array([right[1], -right[0], 0.0])        # to the right of a->b seen from above
    top = [(0.0, z1), (L, z1)] if z1 is not None else wall_top(planes, a, b, z0)
    P = lambda s, z: np.array([a[0], a[1], 0.0]) + right * s + np.array([0, 0, z])
    ring = [P(0, z0), P(L, z0)] + [P(s, z) for s, z in reversed(top)]
    hs = []
    for (s0, zb, s1, zt) in holes:
        hs.append([P(s0, zb), P(s1, zb), P(s1, zt), P(s0, zt)])
        if reveal > 0:
            rm = reveal_mat or mat
            inn = -out * reveal
            for p, q in ((P(s0, zb), P(s1, zb)), (P(s1, zb), P(s1, zt)), (P(s1, zt), P(s0, zt)), (P(s0, zt), P(s0, zb))):
                geo.poly(rm, [p, p + inn, q + inn, q])
    geo.poly(mat, ring, holes=hs, uv_u=right, uv_o=P(0, 0.0))
    # make sure the face points outward
    return dict(origin=np.array([a[0], a[1], z0]), right=right, out=out, length=L, top=top)


def footprint_walls(geo: Geo, mat, corners, z0, planes=(), z1=None, skip=()):
    """Walls round a footprint polygon (list of (x, y)); any winding: every wall faces away from the inside.
    skip: indices of edges to leave out.  Returns the list of wall frames (None for skipped edges)."""
    c = np.asarray(corners, float)
    if _area(c) > 0:
        c = c[::-1]                                    # clockwise seen from above -> wall() normals point out
    frames = []
    for i in range(len(c)):
        if i in skip:
            frames.append(None)
            continue
        frames.append(wall(geo, mat, c[i], c[(i + 1) % len(c)], z0, planes, z1))
    return frames


def _clip_below(pts, z_cap):
    """Clip a 3-D polygon to z <= z_cap (Sutherland-Hodgman against the horizontal plane)."""
    out = []
    n = len(pts)
    for i in range(n):
        a, b = np.asarray(pts[i], float), np.asarray(pts[(i + 1) % n], float)
        ia, ib = a[2] <= z_cap + 1e-9, b[2] <= z_cap + 1e-9
        if ia:
            out.append(a)
        if ia != ib:
            t = (z_cap - a[2]) / (b[2] - a[2])
            out.append(a + t * (b - a))
    return out


def hip_roof(name, x0, y0, x1, y1, z_eave, slope, mat='roof_shingle', gable=(), z_cap=None, cap_mat='roof_flat',
             ridge=None, **kw):
    """Planes of a hip roof over the eave rectangle; slope = rise / run.  gable = subset of ('x0', 'x1', 'y0', 'y1'):
    ends that are gables (the ridge runs to that end).  The ridge runs along the longer side unless ridge='x' / 'y'.
    z_cap: cut the roof flat at that height (a hipped skirt round a flat roof) - the flat part gets cap_mat."""
    w, d = x1 - x0, y1 - y0
    planes = []
    along_x = (w >= d) if ridge is None else (ridge == 'x')
    if along_x:                                         # ridge along x
        h = d / 2 * slope
        ym, zr = (y0 + y1) / 2, z_eave + h
        ra = x0 if 'x0' in gable else x0 + d / 2
        rb = x1 if 'x1' in gable else x1 - d / 2
        if ra > rb:                                     # a square-ish block hipped at both ends: a pyramid
            ra = rb = (x0 + x1) / 2
            zr = z_eave + w / 2 * slope
        polys = [('_y0', [(x0, y0, z_eave), (x1, y0, z_eave), (rb, ym, zr), (ra, ym, zr)]),
                 ('_y1', [(x1, y1, z_eave), (x0, y1, z_eave), (ra, ym, zr), (rb, ym, zr)])]
        if 'x0' not in gable:
            polys.append(('_x0', [(x0, y1, z_eave), (x0, y0, z_eave), (ra, ym, zr)]))
        if 'x1' not in gable:
            polys.append(('_x1', [(x1, y0, z_eave), (x1, y1, z_eave), (rb, ym, zr)]))
    else:                                               # ridge along y
        h = w / 2 * slope
        xm, zr = (x0 + x1) / 2, z_eave + h
        ra = y0 if 'y0' in gable else y0 + w / 2
        rb = y1 if 'y1' in gable else y1 - w / 2
        if ra > rb:
            ra = rb = (y0 + y1) / 2
            zr = z_eave + d / 2 * slope
        polys = [('_x0', [(x0, y1, z_eave), (x0, y0, z_eave), (xm, ra, zr), (xm, rb, zr)]),
                 ('_x1', [(x1, y0, z_eave), (x1, y1, z_eave), (xm, rb, zr), (xm, ra, zr)])]
        if 'y0' not in gable:
            polys.append(('_y0', [(x0, y0, z_eave), (x1, y0, z_eave), (xm, ra, zr)]))
        if 'y1' not in gable:
            polys.append(('_y1', [(x1, y1, z_eave), (x0, y1, z_eave), (xm, rb, zr)]))
    for suffix, pts in polys:
        pts = [q for i, q in enumerate(pts) if i == 0 or np.linalg.norm(np.subtract(q, pts[i - 1])) > 1e-6]
        if z_cap is not None and z_cap < zr:
            pts = _clip_below(pts, z_cap)
        if len(pts) >= 3:
            planes.append(RoofPlane(name + suffix, pts, mat, **kw))
    if z_cap is not None and z_cap < zr:
        r = (z_cap - z_eave) / slope                   # the cap is the eave rectangle inset by this run (gables: none)
        cx0 = x0 if 'x0' in gable else x0 + r
        cx1 = x1 if 'x1' in gable else x1 - r
        cy0 = y0 if 'y0' in gable else y0 + r
        cy1 = y1 if 'y1' in gable else y1 - r
        if cx1 - cx0 > 0.02 and cy1 - cy0 > 0.02:
            planes.append(RoofPlane(name + '_cap', [(cx0, cy0, z_cap), (cx1, cy0, z_cap), (cx1, cy1, z_cap), (cx0, cy1, z_cap)], cap_mat, **kw))
    return planes
