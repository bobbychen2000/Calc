"""Exterior fixtures and building parts of the house: roof parts (standing-seam ribs, ridge / hip caps, fascia,
K-style gutters, downspouts, vent stacks, skylights, solar arrays, the chimney shroud), porch parts (columns, beams,
ceiling with down-lights, step lights), awnings on tie rods, the wall lanterns, the louvred pergolas, the cedar
fence and its gates.

Everything is a plain function that ADDS geometry to a Geo you pass in.  Units are metres, world axes X right
along the street, Y into the lot, Z up.  Two mounting frames are used throughout:

  wall frame   origin = a point on the wall's outer face, right = unit vector along the wall (horizontal, to the
               right when you face the wall from outside), out = the wall's outward normal, up = +Z
               (right x up = out).  Local coordinates are written (a along right, b along out, c up).
  roof frame   a point on the roof plane, `right` = unit vector along the eave (horizontal, in the plane),
               `up_slope` = unit vector in the plane pointing up the slope; the plane normal is right x up_slope
               (or the other way round - the builders take whichever points up).

All faces are flat-shaded with UVs in metres like model/kit.py (round parts are smooth round their axis); a few
meshes of this family's own materials (fx_solar_glass, fx_lantern_glass, fx_fence_pickets, fx_heater_face) carry
0..1 UVs of their texture instead - see each docstring.  Sizes were read off the listing photos against the
2.44 m doors and 0.17 m risers; the defaults ARE the house's parts, so a builder normally passes positions only.

Shared surface materials are used by name (trim_white, roof_seam, roof_shingle, gutter_dark, metal_awning,
pergola_metal, fence_wood, chimney_cap); this module registers its own fx_* names below (look:
web/viewer/looks/fixtures.js).
"""
from __future__ import annotations

import math

import numpy as np

from model import materials as _materials
from model.kit import UP, Geo, _newell, _unit

X = np.array([1.0, 0.0, 0.0])
Y = np.array([0.0, 1.0, 0.0])

# ---- materials of this family (GLB fallback factors; the viewer look is looks/fixtures.js) ----------------------
MATS = {
    'fx_lantern_frame': dict(color=(0.010, 0.010, 0.011), roughness=0.42, metallic=0.55),
    'fx_lantern_glass': dict(color=(0.62, 0.70, 0.74), roughness=0.05, alpha=0.22, double=True),
    'fx_lamp_glow': dict(color=(0.90, 0.86, 0.78), roughness=0.5, emissive=(1.0, 0.70, 0.36)),
    'fx_lamp_base': dict(color=(0.02, 0.02, 0.02), roughness=0.5, metallic=0.4),
    'fx_step_plate': dict(color=(0.030, 0.023, 0.019), roughness=0.5, metallic=0.6),
    'fx_step_glow': dict(color=(0.020, 0.018, 0.016), roughness=0.6, emissive=(1.0, 0.74, 0.42)),
    'fx_can_trim': dict(color=(0.72, 0.72, 0.70), roughness=0.6),
    'fx_can_glow': dict(color=(0.09, 0.09, 0.085), roughness=0.5, emissive=(1.0, 0.80, 0.55)),
    'fx_solar_glass': dict(color=(0.006, 0.008, 0.013), roughness=0.12, metallic=0.2),
    'fx_solar_frame': dict(color=(0.008, 0.008, 0.009), roughness=0.45, metallic=0.6),
    'fx_skylight_glass': dict(color=(0.25, 0.36, 0.43), roughness=0.06),
    'fx_skylight_frame': dict(color=(0.74, 0.75, 0.76), roughness=0.5, metallic=0.2),
    'fx_flashing': dict(color=(0.026, 0.028, 0.031), roughness=0.5, metallic=0.6),
    'fx_vent_pipe': dict(color=(0.045, 0.047, 0.052), roughness=0.7),
    'fx_vent_lead': dict(color=(0.27, 0.28, 0.30), roughness=0.6, metallic=0.3),
    'fx_spark_screen': dict(color=(0.36, 0.37, 0.38), roughness=0.4, metallic=0.7),
    'fx_heater_body': dict(color=(0.020, 0.020, 0.022), roughness=0.45, metallic=0.6),
    'fx_heater_face': dict(color=(0.35, 0.35, 0.34), roughness=0.3, metallic=0.8),
    'fx_speaker': dict(color=(0.008, 0.008, 0.009), roughness=0.85),
    'fx_fence_post': dict(color=(0.076, 0.041, 0.032), roughness=0.9),
    'fx_fence_pickets': dict(color=(0.30, 0.16, 0.085), roughness=0.85, double=True),
    'fx_iron': dict(color=(0.007, 0.007, 0.007), roughness=0.6, metallic=0.5),
}
for _k, _v in MATS.items():
    _materials.register(_k, **_v)


# =====================================================================================================================
# low-level helpers
# =====================================================================================================================
def _poly(geo, mat, pts, hint, **kw):
    """Planar polygon wound so that its normal agrees with `hint` (any vector on the visible side)."""
    pts = np.asarray(pts, float)
    if _newell(pts) @ np.asarray(hint, float) < 0:
        pts = pts[::-1]
    geo.poly(mat, pts, **kw)


def _poly_uv(geo, mat, pts, uvs, hint):
    """Convex polygon with explicit texture coordinates (0..1, v up): written so that the GLB's v flip lands them
    in 0..1 with v = 1 at the image top."""
    pts = np.asarray(pts, float)
    uvs = np.asarray(uvs, float)
    n = _newell(pts)
    if n @ np.asarray(hint, float) < 0:
        pts, uvs, n = pts[::-1], uvs[::-1], -n
    F = [[0, i, i + 1] for i in range(1, len(pts) - 1)]
    geo.mesh(mat).add(pts, np.tile(n, (len(pts), 1)), np.stack([uvs[:, 0], uvs[:, 1] - 1.0], -1), F)


def _add_smooth(geo, mat, V, N, UV, F):
    """Indexed mesh with given (smooth) normals; triangles are re-wound to face along their normals."""
    V, N, F = np.asarray(V, float), np.asarray(N, float), np.asarray(F, int)
    g = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    s = np.einsum('ij,ij->i', g, N[F[:, 0]] + N[F[:, 1]] + N[F[:, 2]])
    F = np.where((s < 0)[:, None], F[:, ::-1], F)
    geo.mesh(mat).add(V, N, UV, F)


def _perp(axis):
    ax = _unit(axis)
    ref = X if abs(ax @ X) < 0.9 else Y
    u = _unit(np.cross(ax, ref))
    return ax, u, np.cross(ax, u)


def _revolve(geo, mat, a, axis, prof, n=10, caps=(False, False), cap_mat=None):
    """Surface of revolution about the line through `a` along `axis`: prof = [(z, r), ...] with z along the axis;
    smooth round the axis, a crease at every profile point.  caps: close the first / last ring with a disc."""
    a = np.asarray(a, float)
    ax, u, v = _perp(axis)
    ang = np.linspace(0.0, 2 * np.pi, n + 1)
    rad = np.outer(np.cos(ang), u) + np.outer(np.sin(ang), v)
    for (z0, r0), (z1, r1) in zip(prof[:-1], prof[1:]):
        dz, dr = z1 - z0, r1 - r0
        ln = math.hypot(dz, dr)
        if ln < 1e-9:
            continue
        nrm = (rad * dz - ax * dr) / ln
        A = a + z0 * ax + r0 * rad
        B = a + z1 * ax + r1 * rad
        rm = 0.5 * (r0 + r1)
        UV = np.vstack([np.stack([ang * rm, np.zeros(n + 1)], -1), np.stack([ang * rm, np.full(n + 1, ln)], -1)])
        F = []
        for i in range(n):
            F += [[i, i + 1, n + 2 + i], [i, n + 2 + i, n + 1 + i]]
        _add_smooth(geo, mat, np.vstack([A, B]), np.vstack([nrm, nrm]), UV, F)
    for k, on in enumerate(caps):
        z, r = prof[0] if k == 0 else prof[-1]
        if on and r > 1e-6:
            _poly(geo, cap_mat or mat, a + z * ax + r * rad[:-1], -ax if k == 0 else ax)


def _annulus(geo, mat, c, normal, r0, r1, n=12):
    c = np.asarray(c, float)
    ax, u, v = _perp(normal)
    ang = np.linspace(0.0, 2 * np.pi, n + 1)
    rad = np.outer(np.cos(ang), u) + np.outer(np.sin(ang), v)
    for i in range(n):
        _poly(geo, mat, [c + r0 * rad[i], c + r1 * rad[i], c + r1 * rad[i + 1], c + r0 * rad[i + 1]], ax)


class Loc:
    """A local frame: world = o + a ex + b ey + c ez (+ slope * a added to world z: racked fence panels).
    The triple may be right- or left-handed; faces are wound by their outward hint."""

    def __init__(self, o, ex, ey, ez, slope=0.0):
        self.o = np.asarray(o, float)
        self.ex, self.ey, self.ez = _unit(ex), _unit(ey), _unit(ez)
        self.slope = slope

    def pt(self, a, b, c):
        p = self.o + a * self.ex + b * self.ey + c * self.ez
        if self.slope:
            p = p + np.array([0.0, 0.0, self.slope * a])
        return p

    def vec(self, a, b, c):
        return a * self.ex + b * self.ey + c * self.ez

    def poly(self, geo, mat, pts, n, grain=None, **kw):
        """Polygon from local points, facing local direction n.  grain: local direction the texture's v axis
        (the wood grain / board length) should follow on this face; uv_u: local direction of texture u."""
        nw = self.vec(*n)
        if grain is not None:
            g = self.vec(*grain)
            u = np.cross(g, _unit(nw))
            if np.linalg.norm(u) > 0.3:
                kw['uv_u'] = u
        elif kw.get('uv_u') is not None:
            kw['uv_u'] = self.vec(*kw['uv_u'])
        if kw.get('uv_u') is None:
            kw.pop('uv_u', None)
        _poly(geo, mat, [self.pt(*p) for p in pts], nw, **kw)

    def poly_uv(self, geo, mat, pts, uvs, n):
        _poly_uv(geo, mat, [self.pt(*p) for p in pts], uvs, self.vec(*n))

    def box(self, geo, mat, lo, hi, faces='xXyYzZ', mats=None, grain=None, uv_o=None):
        """Box lo..hi in local coordinates; faces: which of -a +a -b +b -c +c ('xXyYzZ') to emit;
        mats: {face letter: material}; grain: local direction of the texture's v axis (see poly)."""
        (a0, b0, c0), (a1, b1, c1) = np.minimum(lo, hi), np.maximum(lo, hi)
        mats = mats or {}
        q = {
            'x': ([(a0, b0, c0), (a0, b1, c0), (a0, b1, c1), (a0, b0, c1)], (-1, 0, 0)),
            'X': ([(a1, b0, c0), (a1, b1, c0), (a1, b1, c1), (a1, b0, c1)], (1, 0, 0)),
            'y': ([(a0, b0, c0), (a1, b0, c0), (a1, b0, c1), (a0, b0, c1)], (0, -1, 0)),
            'Y': ([(a0, b1, c0), (a1, b1, c0), (a1, b1, c1), (a0, b1, c1)], (0, 1, 0)),
            'z': ([(a0, b0, c0), (a1, b0, c0), (a1, b1, c0), (a0, b1, c0)], (0, 0, -1)),
            'Z': ([(a0, b0, c1), (a1, b0, c1), (a1, b1, c1), (a0, b1, c1)], (0, 0, 1)),
        }
        for f in faces:
            pts, n = q[f]
            self.poly(geo, mats.get(f, mat), pts, n, grain=grain, **({} if uv_o is None else {'uv_o': uv_o}))


def wall_frame(origin, right, out):
    """The wall mounting frame as a Loc with local coordinates (a along right, b along out, c up)."""
    r = _unit(right)
    o = np.asarray(out, float)
    o = _unit(o - (o @ r) * r)
    return Loc(origin, r, o, np.cross(o, r))


def sweep(geo, mat, section, path, c, s_sign=1.0, closed=True, caps=(True, True), mats=None):
    """Sweep a 2-D section along a 3-D polyline with mitred joints.

    section: [(s, t), ...]; at the first path point t runs along `c` (made perpendicular to the first segment)
    and s along cross(direction, c) * s_sign.  A closed section is taken counter-clockwise in (s, t); an open
    profile must be ordered as part of a counter-clockwise outline (its visible side on the right of travel).
    Each segment is a true prism (the ring is projected along the segment onto the bisector plane of the joint).
    mats: optional material per section edge."""
    path = [np.asarray(p, float) for p in path]
    sec = np.asarray(section, float)
    if closed:
        q = np.roll(sec, -1, 0)
        if float((sec[:, 0] * q[:, 1] - q[:, 0] * sec[:, 1]).sum()) < 0:
            sec = sec[::-1]
            mats = None if mats is None else list(mats)[-2::-1] + [list(mats)[-1]]
    dirs = [_unit(path[i + 1] - path[i]) for i in range(len(path) - 1)]
    d0 = dirs[0]
    ca = np.asarray(c, float)
    ca = _unit(ca - (ca @ d0) * d0)
    sa = np.cross(d0, ca) * s_sign
    ring = np.array([path[0] + s * sa + t * ca for s, t in sec])
    rings = [ring]
    for k in range(1, len(path)):
        d = dirs[k - 1]
        m = d if k == len(path) - 1 else _unit(dirs[k - 1] + dirs[k])
        lam = -((ring - path[k]) @ m) / (d @ m)
        ring = ring + lam[:, None] * d
        rings.append(ring)
    ns = len(sec)
    for i, d in enumerate(dirs):
        A, B = rings[i], rings[i + 1]
        for j in (range(ns) if closed else range(ns - 1)):
            j2 = (j + 1) % ns
            e = A[j2] - A[j]
            if np.linalg.norm(e) < 1e-7:
                continue
            _poly(geo, mats[j] if mats else mat, [A[j], B[j], B[j2], A[j2]], -s_sign * np.cross(e, d), uv_u=d)
    if caps[0] and ns > 2:
        _poly(geo, mat, rings[0], -dirs[0])
    if caps[1] and ns > 2:
        _poly(geo, mat, rings[-1], dirs[-1])
    return rings


def _rect(w, t):
    return [(-w / 2, -t / 2), (w / 2, -t / 2), (w / 2, t / 2), (-w / 2, t / 2)]


def poly_normal(poly3d):
    """Upward unit normal of a planar roof polygon."""
    n = _newell(np.asarray(poly3d, float))
    return n if n[2] >= 0 else -n


# =====================================================================================================================
# roof parts
# =====================================================================================================================
PAN = 0.406           # standing-seam pan width (16 in): p30, 24 px between seams at 57 px / m; seg002_043 agrees
RIB_H = 0.035         # seam height
RIB_W = 0.016


def seam_ribs(geo, poly3d, eave_dir, spacing=PAN, h=RIB_H, w=RIB_W, mat='roof_seam', phase=None, top_inset=0.0,
              eave_cap=True):
    """Raise the standing seams on a planar roof polygon.

    poly3d: the roof face (3-D points, any winding); eave_dir: direction of its eave (horizontal).  The ribs run
    up the slope, perpendicular to the eave, every `spacing` m measured along the eave, and are clipped to the
    outline (hips, valleys, cut-outs).  phase: distance of one rib from the middle of the face along the eave
    (default spacing / 2: a pan sits on the centre line).  top_inset shortens the upper ends (under a cap).
    A rib is a w x h fin: 8 triangles whatever its length.  Returns the number of ribs."""
    P = np.asarray(poly3d, float)
    n = poly_normal(P)
    e = np.asarray(eave_dir, float)
    e = _unit(e - (e @ n) * n)
    up = np.cross(n, e)
    if up[2] < 0:
        up = -up
    o = P[0]
    A, B = (P - o) @ e, (P - o) @ up
    mid = 0.5 * (A.min() + A.max())
    ph = spacing / 2 if phase is None else phase
    k0 = math.ceil((A.min() + 0.05 - mid - ph) / spacing)
    k1 = math.floor((A.max() - 0.05 - mid - ph) / spacing)
    count = 0
    for k in range(k0, k1 + 1):
        a = mid + ph + k * spacing
        ys = []
        for i in range(len(P)):
            j = (i + 1) % len(P)
            if (A[i] - a) * (A[j] - a) < 0:
                t = (a - A[i]) / (A[j] - A[i])
                ys.append(B[i] + t * (B[j] - B[i]))
        ys.sort()
        for b0, b1 in zip(ys[0::2], ys[1::2]):
            b1 -= top_inset
            if b1 - b0 < 0.08:
                continue
            base = lambda s, b: o + (a + s) * e + b * up
            p = [base(-w / 2, b0), base(w / 2, b0), base(w / 2, b1), base(-w / 2, b1)]
            q = [x + h * n for x in p]
            _poly(geo, mat, [p[0], p[3], q[3], q[0]], -e, uv_u=up)
            _poly(geo, mat, [p[1], p[2], q[2], q[1]], e, uv_u=up)
            _poly(geo, mat, q, n, uv_u=e)
            if eave_cap:
                _poly(geo, mat, [p[0], p[1], q[1], q[0]], -up)
            count += 1
    return count


def ridge_cap(geo, a, b, kind='seam', n1=None, n2=None, pitch=26.6, half=None, lift=None, mat=None, expo=0.25,
              ends=True):
    """Cap along a ridge or hip from a to b (points on the line where the two roof faces meet).

    n1, n2: the upward normals of the two faces (use poly_normal); without them the cap folds symmetrically about
    the vertical plane through the line, each wing dropping `pitch` degrees.
    kind 'seam':    a bold folded metal cap, 2 x half (0.125) wide, standing `lift` (0.042) above the faces so it
                    sits over the seam ribs, hemmed down to the roof on both edges.  16 triangles.
    kind 'shingle': a course of cap shingles, 2 x half (0.15) wide, `expo` m exposure, each tab's butt (thick
                    end) toward a - so give a = the LOW end of a hip.  8 triangles per tab."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    L = float(np.linalg.norm(b - a))
    d = (b - a) / L
    if n1 is None or n2 is None:
        hz = np.cross(d, UP)
        hz = _unit(hz) if np.linalg.norm(hz) > 1e-6 else X
        v = np.cross(hz, d)
        if v[2] < 0:
            v = -v
        ph = math.radians(pitch)
        n1, n2 = math.cos(ph) * v + math.sin(ph) * hz, math.cos(ph) * v - math.sin(ph) * hz
    n1, n2 = _unit(n1), _unit(n2)

    def wing(n, other):
        w = _unit(np.cross(d, n))
        return -w if w @ other > 0 else w

    w1, w2 = wing(n1, n2), wing(n2, n1)
    m = _unit(n1 + n2)
    ca = float(n1 @ m)
    if kind == 'seam':
        half = 0.125 if half is None else half
        lift = 0.042 if lift is None else lift
        mat = mat or 'roof_seam'
        off = [half * w1, half * w1 + lift * n1, (lift / ca) * m, half * w2 + lift * n2, half * w2]
        hints = [w1, n1, n2, w2]
        for i in range(4):
            _poly(geo, mat, [a + off[i], b + off[i], b + off[i + 1], a + off[i + 1]], hints[i], uv_u=d)
        if ends:
            _poly(geo, mat, [a + o for o in off], -d)
            _poly(geo, mat, [b + o for o in off], d)
        return 1
    half = 0.15 if half is None else half
    base, th = 0.005, 0.016
    mat = mat or 'roof_shingle'
    npc = max(1, int(round(L / expo)))
    e = L / npc
    E = lambda s, l, w, n: a + s * d + half * w + l * n
    C = lambda s, l: a + s * d + (l / ca) * m
    for i in range(npc):
        s0, s1 = i * e, (i + 1) * e
        l0, l1 = base + th, base
        lp = 0.0 if i == 0 else base
        for w, n in ((w1, n1), (w2, n2)):
            _poly(geo, mat, [E(s0, l0, w, n), E(s1, l1, w, n), C(s1, l1), C(s0, l0)], n, uv_u=d, uv_o=a)
            _poly(geo, mat, [E(s0, lp, w, n), E(s0, l0, w, n), C(s0, l0), C(s0, lp)], -d)
    return npc


hip_cap = ridge_cap


def fascia(geo, a, b, out, h=0.20, t=0.025, step=0.075, step_in=0.02, mat='trim_white', ends=True):
    """Fascia board along an eave.  a, b: the eave line = the TOP OUTER edge of the fascia; out: the horizontal
    outward direction.  The board hangs h below the line, t thick; its lowest `step` m is set back step_in
    (the shadow step under the gutter seen in p02).  10 triangles + ends."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = _unit(b - a)
    s_sign = 1.0 if np.cross(d, UP) @ np.asarray(out, float) > 0 else -1.0
    prof = [(-step_in - t, -h), (-step_in, -h), (-step_in, -h + step), (0.0, -h + step), (0.0, 0.0), (-t, 0.0)]
    sweep(geo, mat, prof, [a, b], UP, s_sign, closed=False, caps=(ends, ends))


# K-style gutter (5 in): back, bottom, the ogee front, the rolled lip, the leaf-guard mesh on top (p02) and the
# drip edge that covers the fascia's top strip behind it
GUTTER = [(0.0, -0.092), (0.072, -0.092), (0.079, -0.070), (0.108, -0.040), (0.127, -0.034), (0.127, -0.005),
          (0.119, 0.0), (0.110, -0.004), (0.110, -0.012), (0.004, -0.012), (0.004, 0.016)]


def gutter(geo, a, b, out=None, drop=0.012, mat='gutter_dark', ends=(True, True)):
    """K-style gutter on a fascia: gutter(geo, a, b, out) along one eave, or gutter(geo, [p0, p1, p2, ...], out)
    along a polyline round the corners, mitred.  a, b / the points: the eave line (top outer edge of the fascia);
    out: horizontal outward direction of the FIRST segment.
    The gutter is 0.127 wide x 0.092 deep and hangs `drop` below the line.  20 triangles per straight run
    (+ 9 per closed end), so <= 40 per metre from 1 m up."""
    if out is None:
        path, out = [np.asarray(p, float) for p in a], b
    else:
        path = [np.asarray(a, float), np.asarray(b, float)]
    d = _unit(path[1] - path[0])
    s_sign = 1.0 if np.cross(d, UP) @ np.asarray(out, float) > 0 else -1.0
    path = [p - np.array([0, 0, drop]) for p in path]
    rings = sweep(geo, mat, GUTTER, path, UP, s_sign, closed=False, caps=(False, False))
    for k, on in ((0, ends[0]), (-1, ends[1])):
        if on:
            dd = _unit(path[1] - path[0]) if k == 0 else _unit(path[-1] - path[-2])
            _poly(geo, mat, rings[k], -dd if k == 0 else dd)
    return rings


def eave(geo, a, b, out, fascia_h=0.20, gutter_on=True, ends=(True, True)):
    """Fascia + gutter along one straight eave (see fascia / gutter)."""
    fascia(geo, a, b, out, h=fascia_h, ends=bool(ends[0] or ends[1]))
    if gutter_on:
        gutter(geo, a, b, out, ends=ends)


def downspout(geo, top, bottom, out, size=(0.076, 0.052), stand=0.012, kick=0.16, straps=2, mat='gutter_dark'):
    """Rectangular downspout (3 x 2 in, dark).  top: the outlet under the gutter (centre of the pipe);
    bottom: the point on the WALL face (or column face) where the pipe ends, at the height of its foot;
    out: outward normal of that wall.  The pipe drops from the outlet, runs back to the wall through two elbows
    (an offset in any horizontal direction), goes down `stand` clear of the wall and ends in a kick-out elbow of
    length `kick` (0 = none).  size = (face width along the wall, depth).  About 60 triangles."""
    top, bottom = np.asarray(top, float), np.asarray(bottom, float)
    o = _unit(np.asarray(out, float) * np.array([1, 1, 0]))
    sw, so = size
    run = bottom + o * (stand + so / 2)
    hz = np.linalg.norm((top - run)[:2])
    path = [top, top - np.array([0, 0, 0.07])]
    if hz > 0.02:
        zb = path[-1][2] - max(0.10, 0.75 * hz)
        path.append(np.array([run[0], run[1], zb]))
    foot = bottom[2] + (0.10 if kick else 0.0)
    path.append(np.array([run[0], run[1], foot]))
    if kick:
        path.append(np.array([run[0], run[1], foot]) + o * kick * 0.92 - np.array([0, 0, kick * 0.42]))
    sweep(geo, mat, _rect(sw, so), path, o, 1.0, closed=True)
    # straps on the vertical run
    z0, z1 = foot, path[-3 if kick else -2][2]
    r = np.cross(UP, o)
    for i in range(straps):
        z = z0 + (z1 - z0) * (i + 0.6) / (straps + 0.2)
        L = Loc(np.array([run[0], run[1], z]) - o * (stand + so / 2), r, o, UP)
        L.box(geo, mat, (-sw / 2 - 0.016, 0, -0.018), (sw / 2 + 0.016, stand + so + 0.004, 0.018), faces='xXYzZ')
    return path


def vent_stack(geo, p, roof_n=UP, h=0.36, r=0.048, n=10):
    """Plumbing vent: a vertical dark pipe with a lead cap, in a cone boot on a flashing plate lying on the roof
    (seg002_043: ~0.10 m pipes standing ~0.35 m).  p: the point on the roof plane where the pipe's axis meets it;
    roof_n: the roof normal.  About 80 triangles."""
    p = np.asarray(p, float)
    rn = _unit(roof_n)
    if rn[2] < 0:
        rn = -rn
    # flashing plate in the roof plane (square, lifted 4 mm)
    e = np.cross(rn, UP)
    e = _unit(e) if np.linalg.norm(e) > 1e-6 else X
    us = np.cross(rn, e)
    if us[2] < 0:
        us = -us
    L = Loc(p + 0.004 * rn, e, us, rn)
    L.poly(geo, 'fx_flashing', [(-0.16, -0.15, 0), (0.16, -0.15, 0), (0.16, 0.20, 0), (-0.16, 0.20, 0)], (0, 0, 1))
    # cone boot: base ring in the roof plane, top ring horizontal
    ang = np.linspace(0.0, 2 * np.pi, n + 1)
    rad = np.outer(np.cos(ang), X) + np.outer(np.sin(ang), Y)
    rb, rt, hb = r * 2.3, r * 1.12, 0.13
    base = p + rb * rad
    base[:, 2] = p[2] - ((base - p)[:, :2] @ rn[:2]) / rn[2] + 0.006
    top = p + rt * rad + np.array([0, 0, hb])
    nrm = _unit(np.array([hb, rb - rt]))
    N = rad * nrm[0] + UP * nrm[1]
    F = []
    for i in range(n):
        F += [[i, i + 1, n + 2 + i], [i, n + 2 + i, n + 1 + i]]
    UV = np.vstack([np.stack([ang * rb, np.zeros(n + 1)], -1), np.stack([ang * rb, np.full(n + 1, hb)], -1)])
    _add_smooth(geo, 'fx_flashing', np.vstack([base, top]), np.vstack([N, N]), UV, F)
    _revolve(geo, 'fx_vent_pipe', p, UP, [(hb - 0.01, r), (h - 0.05, r)], n)
    _revolve(geo, 'fx_vent_lead', p, UP, [(h - 0.05, r * 1.22), (h, r * 1.22), (h, r * 0.8)], n)
    _poly(geo, 'fx_flashing', p + np.array([0, 0, h - 0.004]) + r * 0.8 * rad[:-1], UP)
    _annulus(geo, 'fx_vent_lead', p + np.array([0, 0, h - 0.05]), -UP, r, r * 1.22, n)


def skylight(geo, origin, right, up_slope, w=0.86, l=0.92, curb=0.11, frame=0.075):
    """Curb-mounted skylight (p30: ~0.86 x 0.92 m outside, pale frame, grey-blue glass, a wider head flashing).
    origin: centre of the unit ON the roof plane; right: along the eave; up_slope: up the slope (both in the plane).
    Outside size w (along right) x l (up the slope), standing `curb` above the roof.  30 triangles."""
    r, u = _unit(right), _unit(up_slope)
    n = np.cross(r, u)
    if n[2] < 0:
        n = -n
    L = Loc(origin, r, u, n)
    fl = 0.07
    # apron flashing on the roof and the head flashing (wider, up-slope)
    L.poly(geo, 'fx_flashing', [(-w / 2 - fl, -l / 2 - fl, 0.005), (w / 2 + fl, -l / 2 - fl, 0.005),
                                (w / 2 + fl, l / 2 + fl, 0.005), (-w / 2 - fl, l / 2 + fl, 0.005)], (0, 0, 1))
    L.box(geo, 'fx_skylight_frame', (-w / 2 - 0.10, l / 2, 0.0), (w / 2 + 0.10, l / 2 + 0.10, 0.03), faces='xXyYZ')
    L.box(geo, 'fx_skylight_frame', (-w / 2, -l / 2, 0.0), (w / 2, l / 2, curb), faces='xXyY')
    f = frame
    for lo, hi in (((-w / 2, -l / 2), (w / 2, -l / 2 + f)), ((-w / 2, l / 2 - f), (w / 2, l / 2)),
                   ((-w / 2, -l / 2 + f), (-w / 2 + f, l / 2 - f)), ((w / 2 - f, -l / 2 + f), (w / 2, l / 2 - f))):
        L.poly(geo, 'fx_skylight_frame', [(lo[0], lo[1], curb), (hi[0], lo[1], curb), (hi[0], hi[1], curb),
                                          (lo[0], hi[1], curb)], (0, 0, 1))
    g = curb - 0.012
    L.poly(geo, 'fx_skylight_glass', [(-w / 2 + f, -l / 2 + f, g), (w / 2 - f, -l / 2 + f, g),
                                      (w / 2 - f, l / 2 - f, g), (-w / 2 + f, l / 2 - f, g)], (0, 0, 1))


MODULE = (1.134, 1.722)       # all-black 400 W class module (p30: 67 x 87 px at 60.6 px / m on a 6:12 slope)


def solar_array(geo, origin, right, up_slope, rows, cols, module=MODULE, gap=0.012, standoff=0.085, thick=0.035,
                skirt=True):
    """Black framed PV modules on low rails over a roof plane (p30, seg141_040).
    origin: the array's lower-left corner ON the roof plane (lower = eave side, left when looking up the slope);
    right: along the eave; up_slope: up the slope.  module = (width along the eave, length up the slope): the
    house's are laid portrait.  The module tops stand standoff + thick (0.12) above the roof.
    fx_solar_glass carries 0..1 UVs per module (u across the width, v up the slope); the frame is part of that
    texture.  About 4 + 20 / cols triangles per module.  Returns the array's (width, length)."""
    r, u = _unit(right), _unit(up_slope)
    n = np.cross(r, u)
    if n[2] < 0:
        n = -n
    L = Loc(origin, r, u, n)
    mw, ml = module
    W, H = cols * mw + (cols - 1) * gap, rows * ml + (rows - 1) * gap
    z0, z1 = standoff, standoff + thick
    for j in range(rows):
        for i in range(cols):
            a0, b0 = i * (mw + gap), j * (ml + gap)
            L.poly_uv(geo, 'fx_solar_glass', [(a0, b0, z1), (a0 + mw, b0, z1), (a0 + mw, b0 + ml, z1), (a0, b0 + ml, z1)],
                      [(0, 0), (1, 0), (1, 1), (0, 1)], (0, 0, 1))
            faces = ('x' if i == 0 else '') + ('X' if i == cols - 1 else '') + ('y' if j == 0 else '') + \
                    ('Y' if j == rows - 1 else '')
            if faces:
                L.box(geo, 'fx_solar_frame', (a0, b0, z0), (a0 + mw, b0 + ml, z1), faces=faces)
        for f in (0.22, 0.78):                      # two rails under each row
            b = j * (ml + gap) + f * ml
            L.box(geo, 'fx_solar_frame', (-0.03, b - 0.02, 0.02), (W + 0.03, b + 0.02, z0), faces='xXyY')
    if skirt:
        L.poly(geo, 'fx_solar_frame', [(0, -0.004, 0.0), (W, -0.004, 0.0), (W, -0.004, z0), (0, -0.004, z0)], (0, -1, 0))
    return W, H


def chimney_cap(geo, centre, w, d, right=X, hood=0.50, band=0.13, flange=0.07, flare=0.09, taper=0.10, pan=0.20,
                mat='chimney_cap'):
    """The black standing-seam shroud on a chimney (p02, seg002_043): a counter-flashing collar round the shaft
    top, an open band on four corner posts (the bright spark screen shows through it), and a flared hood - a
    truncated pyramid `hood` high, its foot standing `flare` outside the shaft, its top rim `taper` further in -
    with batten seams every ~`pan` m on each face and an open top over the flue.
    centre: centre of the shaft's TOP face; w x d: the shaft's plan size along right / across.  ~420 triangles.
    Returns the height of the hood's rim above the shaft top."""
    r = _unit(np.asarray(right, float) * np.array([1, 1, 0]))
    L = Loc(centre, r, np.cross(UP, r), UP)
    hw, hd = w / 2, d / 2
    # collar and crown
    L.box(geo, mat, (-hw - 0.025, -hd - 0.025, -flange), (hw + 0.025, hd + 0.025, 0.035), faces='xXyYZz')
    # spark screen core and the corner posts of the open band
    z0 = 0.035
    z1 = z0 + band
    L.box(geo, 'fx_spark_screen', (-hw * 0.72, -hd * 0.72, z0), (hw * 0.72, hd * 0.72, z1 + hood * 0.55), faces='xXyY')
    p = 0.04
    for sa in (-1, 1):
        for sb in (-1, 1):
            a0, b0 = sa * (hw - p), sb * (hd - p)
            L.box(geo, mat, (a0, b0, z0), (a0 + sa * p, b0 + sb * p, z1), faces='xXyY')
    # hood: outer and inner skins, hems
    z2 = z1 + hood
    bo = (hw + flare, hd + flare)
    to = (hw + flare - taper, hd + flare - taper)
    ti = 0.02
    corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    ring = lambda hx, hy, z: [np.array([sx * hx, sy * hy, z]) for sx, sy in corners]
    ob, ot = ring(bo[0], bo[1], z1), ring(to[0], to[1], z2)
    ib, it = ring(bo[0] - ti, bo[1] - ti, z1), ring(to[0] - ti, to[1] - ti, z2)
    for i in range(4):
        j = (i + 1) % 4
        mid = 0.5 * (ob[i] + ob[j])
        nout = (mid[0], mid[1], 0.0)
        tilt = taper / hood
        nface = _unit(np.array([nout[0] and math.copysign(1, nout[0]), nout[1] and math.copysign(1, nout[1]), tilt]))
        L.poly(geo, mat, [ob[i], ob[j], ot[j], ot[i]], nface, uv_u=tuple(ob[j] - ob[i]))
        L.poly(geo, mat, [ib[i], ib[j], it[j], it[i]], -nface)
        L.poly(geo, mat, [ob[i], ob[j], ib[j], ib[i]], (0, 0, -1))
        L.poly(geo, mat, [ot[i], ot[j], it[j], it[i]], (0, 0, 1))
        # batten seams on the outer face
        width = np.linalg.norm(ob[j] - ob[i])
        ns = max(2, int(round(width / pan)))
        for k in range(ns):
            f = (k + 0.5) / ns
            pb = L.pt(*(ob[i] + f * (ob[j] - ob[i])))
            pt = L.pt(*(ot[i] + f * (ot[j] - ot[i])))
            nw = L.vec(*nface)
            sweep(geo, mat, [(0.017, 0.0), (0.008, 0.030), (-0.008, 0.030), (-0.017, 0.0)],
                  [pb - 0.012 * UP, pt + 0.004 * UP], nw, closed=False, caps=(True, True))
    # lid inside the hood and the round flue cap
    zl = z2 - 0.10
    L.poly(geo, 'fx_flashing', ring(to[0] - ti + taper * 0.2, to[1] - ti + taper * 0.2, zl), (0, 0, 1))
    rf = min(hw, hd) * 0.36
    _revolve(geo, 'fx_spark_screen', L.pt(0, 0, zl), UP, [(0.0, rf), (0.07, rf), (0.10, rf * 0.55), (0.11, 0.0)], 12)
    return z2


# =====================================================================================================================
# porch parts
# =====================================================================================================================
def column(geo, base, h, size=0.30, right=X, base_h=0.045, base_out=0.018, cap_h=0.10, cap_out=0.020, neck=0.13,
           pair=None, mat='trim_white'):
    """White square porch column (p02): a plain `size` shaft on a low base block, a capital block under the beam
    and a thin neck band `neck` below the capital (0 = none).
    base: centre of the foot on the porch floor; h: floor to the underside of the beam; right: orientation.
    pair: centre-to-centre distance along `right` of a second identical column (the paired columns: 0.45).
    64 triangles per column."""
    r = _unit(np.asarray(right, float) * np.array([1, 1, 0]))
    base = np.asarray(base, float)
    if pair:
        column(geo, base - r * pair / 2, h, size, right, base_h, base_out, cap_h, cap_out, neck, None, mat)
        column(geo, base + r * pair / 2, h, size, right, base_h, base_out, cap_h, cap_out, neck, None, mat)
        return
    L = Loc(base, r, np.cross(UP, r), UP)
    s = size / 2
    L.box(geo, mat, (-s, -s, base_h), (s, s, h - cap_h), faces='xXyY')
    b = s + base_out
    L.box(geo, mat, (-b, -b, 0), (b, b, base_h), faces='xXyYZ')
    c = s + cap_out
    L.box(geo, mat, (-c, -c, h - cap_h), (c, c, h), faces='xXyYz')
    if neck:
        k = s + 0.010
        L.box(geo, mat, (-k, -k, h - cap_h - neck - 0.028), (k, k, h - cap_h - neck), faces='xXyYzZ')


def beam(geo, a, b, depth=0.28, width=0.30, crown=0.06, crown_out=0.014, mat='trim_white', ends=True):
    """Porch beam / frieze from a to b: the centres of its UNDERSIDE at both ends.  A depth x width box with a
    `crown` band standing crown_out proud along the top of both faces (the stepped frieze under the porch eave).
    28 triangles."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    w, co = width / 2, crown_out
    sec = [(-w, 0), (w, 0), (w, depth - crown), (w + co, depth - crown), (w + co, depth), (-w - co, depth),
           (-w - co, depth - crown), (-w, depth - crown)]
    sweep(geo, mat, sec, [a, b], UP, 1.0, closed=True, caps=(ends, ends))


def downlight(geo, p, normal=-UP, r=0.055, trim='fx_can_trim', glow='fx_can_glow', n=10):
    """Recessed down-light: a trim ring flush on the surface and the lit recess.  p: centre on the ceiling
    surface; normal: the direction the light faces (down).  40 triangles.  Returns p."""
    p = np.asarray(p, float)
    nn = _unit(normal)
    _annulus(geo, trim, p + nn * 0.004, nn, r * 0.74, r, n)
    ax, u, v = _perp(nn)
    ang = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
    _poly(geo, glow, [p - nn * 0.012 + r * 0.74 * (math.cos(t) * u + math.sin(t) * v) for t in ang], nn)
    return p


def porch_ceiling(geo, origin, right, back, w, d, lights=(), mat='soffit_white'):
    """Porch ceiling panel (p02: painted boards running along the porch, small recessed down-lights).
    origin: one corner at ceiling height; right: along the porch front; back: toward the house; w x d its size.
    The panel faces down; its boards run along `right` (texture u).  lights: [(a, b), ...] positions from the
    origin along right / back, or (nx, ny) for an even grid.  Returns the lights' world positions."""
    r, bk = _unit(right), _unit(back)
    L = Loc(origin, r, bk, UP)
    L.poly(geo, mat, [(0, 0, 0), (w, 0, 0), (w, d, 0), (0, d, 0)], (0, 0, -1), uv_u=(1, 0, 0), uv_o=tuple(L.o))
    if len(lights) == 2 and all(isinstance(v, int) for v in lights):
        nx, ny = lights
        lights = [((i + 0.5) * w / nx, (j + 0.5) * d / ny) for i in range(nx) for j in range(ny)]
    return [downlight(geo, L.pt(a, b, 0.0)) for a, b in lights]


def step_light(geo, origin, right, out, w=0.125, h=0.078):
    """Louvred step light in a stair riser (p02: dark bronze plate ~125 x 78 mm with a hooded slot).
    origin: centre of the plate on the riser face; right / out: the riser's frame.  26 triangles.
    Returns the light's position."""
    L = wall_frame(origin, right, out)
    L.box(geo, 'fx_step_plate', (-w / 2, 0, -h / 2), (w / 2, 0.004, h / 2), faces='xXYzZ')
    sw, sh = w * 0.56, h * 0.30
    c0 = -h * 0.26
    L.box(geo, 'fx_step_plate', (-sw / 2 - 0.006, 0.004, c0 + sh), (sw / 2 + 0.006, 0.012, c0 + sh + 0.008),
          faces='xXYzZ')
    L.poly(geo, 'fx_step_glow', [(-sw / 2, 0.0045, c0), (sw / 2, 0.0045, c0), (sw / 2, 0.0045, c0 + sh),
                                 (-sw / 2, 0.0045, c0 + sh)], (0, 1, 0))
    return L.pt(0, 0.02, c0)


def awning(geo, origin, right, out, w, proj=0.95, t=0.13, rods=4, rod_rise=0.80, rod_reach=0.88, slats=4,
           mat='metal_awning'):
    """Flat dark metal canopy hung on tie rods.
    origin: point on the wall at the middle of the canopy's back edge, at its UNDERSIDE; right / out: wall frame;
    w: length along the wall; proj: projection; t: depth of the fascia frame.
    slats > 0: the garage canopy (p01, seg002_043, seg141_040) - an open frame carrying `slats` flat bars
    lengthwise with gaps between them and a cross member under every rod.  slats = 0: the bay-window canopy
    (p02) - a closed deck recessed in the frame, panelled soffit.
    rods: number of tie rods, from square wall plates rod_rise above the underside down to the canopy at
    rod_reach x proj.  About 200 - 300 triangles.  Returns the rod anchor points on the wall."""
    L = wall_frame(origin, right, out)
    f = 0.045                                   # frame member thickness
    L.box(geo, mat, (-w / 2, proj - f, 0), (w / 2, proj, t))
    for sg in (-1, 1):
        a0, a1 = sorted((sg * w / 2, sg * (w / 2 - f)))
        L.box(geo, mat, (a0, 0, 0), (a1, proj - f, t), faces='xXzZ')
    L.box(geo, mat, (-w / 2 + f, 0, 0), (w / 2 - f, 0.03, t), faces='YzZ')
    inset = 0.06
    xs = [0.0] if rods == 1 else [(-w / 2 + inset) + i * (w - 2 * inset) / (rods - 1) for i in range(rods)]
    if slats:
        clear = proj - f - 0.03
        sb = min(0.11, clear / slats * 0.62)
        for i in range(slats):
            b = 0.03 + (i + 0.5) * clear / slats
            L.box(geo, mat, (-w / 2 + f, b - sb / 2, t - 0.040), (w / 2 - f, b + sb / 2, t - 0.012), faces='yYzZ')
        for a in xs:
            a = min(max(a, -w / 2 + f + 0.03), w / 2 - f - 0.03)
            L.box(geo, mat, (a - 0.028, 0.03, 0.02), (a + 0.028, proj - f, t - 0.040), faces='xXz')
    else:
        L.poly(geo, mat, [(-w / 2 + f, 0.03, t - 0.025), (w / 2 - f, 0.03, t - 0.025), (w / 2 - f, proj - f, t - 0.025),
                          (-w / 2 + f, proj - f, t - 0.025)], (0, 0, 1))
        L.poly(geo, mat, [(-w / 2 + f, 0.03, 0.03), (w / 2 - f, 0.03, 0.03), (w / 2 - f, proj - f, 0.03),
                          (-w / 2 + f, proj - f, 0.03)], (0, 0, -1))
        for a in xs[1:-1]:
            L.box(geo, mat, (a - 0.025, 0.03, 0.0), (a + 0.025, proj - f, 0.03), faces='xXz')
    anchors = []
    for a in xs:
        L.box(geo, mat, (a - 0.06, 0, rod_rise - 0.06), (a + 0.06, 0.012, rod_rise + 0.06), faces='xXYzZ')
        L.box(geo, mat, (a - 0.014, 0.012, rod_rise - 0.02), (a + 0.014, 0.045, rod_rise + 0.02), faces='xXYzZ')
        p0, p1 = L.pt(a, 0.035, rod_rise), L.pt(a, proj * rod_reach, t - 0.005)
        geo.cylinder(mat, p0, p1, 0.011, n=6, cap=False)
        L.box(geo, mat, (a - 0.014, proj * rod_reach - 0.03, t - 0.012), (a + 0.014, proj * rod_reach + 0.03, t + 0.022),
              faces='xXyYZ')
        anchors.append(L.pt(a, 0, rod_rise))
    return anchors


def lantern(geo, origin, right, out, h=0.66, w=0.17, d=0.115):
    """THE wall light: a tall rectangular black lantern, clear bevelled glass on three sides, a slender candle
    lamp inside (p02 porch wall and columns, p25 rear wall, p27 cabana: 0.66 high x 0.17 wide x 0.115 deep,
    read against the 2.44 m slider of p25).
    origin: centre of the back plate on the wall (the house's hang with their centre ~2.0 m above the floor);
    right / out: wall frame.  Materials: fx_lantern_frame, fx_lantern_glass (0..1 UVs per pane: the dusk glow),
    fx_lamp_glow (emissive: day ~0, dusk bright), fx_lamp_base.  About 130 triangles.
    Returns the lamp's world position (centre of the candle) for a real light."""
    L = wall_frame(origin, right, out)
    fr, gl = 'fx_lantern_frame', 'fx_lantern_glass'
    t, cap, bp = 0.016, 0.028, 0.012
    hh, hw = h / 2, w / 2
    L.box(geo, fr, (-hw, 0, -hh), (hw, bp, hh), faces='xXYzZ')
    L.box(geo, fr, (-hw, bp, hh - cap), (hw, d, hh), faces='xXYzZ')
    L.box(geo, fr, (-hw, bp, -hh), (hw, d, -hh + cap), faces='xXYzZ')
    c0, c1 = -hh + cap, hh - cap
    for sg in (-1, 1):
        a0, a1 = sorted((sg * hw, sg * (hw - t)))
        L.box(geo, fr, (a0, d - t, c0), (a1, d, c1), faces='xXyY')
    # front pane with a bevelled border: a centre field and four tilted facets
    gb = d - t * 0.5
    a0, a1 = -hw + t, hw - t
    bw, lift = 0.016, 0.004
    uv = lambda a, c: ((a + hw) / w, (c + hh) / h)
    out_r = [(a0, gb, c0), (a1, gb, c0), (a1, gb, c1), (a0, gb, c1)]
    in_r = [(a0 + bw, gb + lift, c0 + bw), (a1 - bw, gb + lift, c0 + bw), (a1 - bw, gb + lift, c1 - bw),
            (a0 + bw, gb + lift, c1 - bw)]
    L.poly_uv(geo, gl, in_r, [uv(p[0], p[2]) for p in in_r], (0, 1, 0))
    for i in range(4):
        j = (i + 1) % 4
        q = [out_r[i], out_r[j], in_r[j], in_r[i]]
        L.poly_uv(geo, gl, q, [uv(p[0], p[2]) for p in q], (0, 1, 0))
    # side panes
    for sg in (-1, 1):
        a = sg * (hw - t * 0.5)
        q = [(a, bp, c0), (a, d - t, c0), (a, d - t, c1), (a, bp, c1)]
        L.poly_uv(geo, gl, q, [(0.5 + 0.30 * sg, (p[2] + hh) / h) for p in q], (sg, 0, 0))
    # the candle: socket, sleeve, flame tip
    lb = bp + (d - bp) * 0.5
    z0 = c0
    _revolve(geo, 'fx_lamp_base', L.pt(0, lb, z0), L.ez, [(0.0, 0.016), (0.045, 0.016), (0.045, 0.0)], 8)
    zt = z0 + 0.045 + 0.62 * (c1 - c0 - 0.045)
    _revolve(geo, 'fx_lamp_glow', L.pt(0, lb, z0 + 0.045), L.ez,
             [(0.0, 0.0085), (zt - z0 - 0.045, 0.0085), (zt - z0 - 0.045 + 0.007, 0.006), (zt - z0 - 0.045 + 0.011, 0.0)], 6)
    return L.pt(0, lb, 0.5 * (z0 + zt))


def speaker(geo, origin, right, out, w=0.31, h=0.21, d=0.17, mat='fx_speaker'):
    """Outdoor wall speaker: a black rounded box on a short bracket (p25 under the pergola's rear beam, p27 on
    the cabana wall: ~0.31 x 0.21 m).  origin: centre of its bracket on the wall.  52 triangles."""
    L = wall_frame(origin, right, out)
    L.box(geo, mat, (-0.035, 0, -0.035), (0.035, 0.05, 0.035), faces='xXzZ')
    k = 0.055

    def ring(sw, sh, kk, b):
        return [(-sw + kk, b, -sh), (sw - kk, b, -sh), (sw, b, -sh + kk), (sw, b, sh - kk), (sw - kk, b, sh),
                (-sw + kk, b, sh), (-sw, b, sh - kk), (-sw, b, -sh + kk)]

    r0, r1, r2 = ring(w / 2, h / 2, k, 0.045), ring(w / 2, h / 2, k, d - 0.03), ring(w / 2 - 0.03, h / 2 - 0.03, k * 0.8, d)
    for A, B in ((r0, r1), (r1, r2)):
        for i in range(8):
            j = (i + 1) % 8
            mid = np.array(A[i]) + np.array(A[j])
            L.poly(geo, mat, [A[i], A[j], B[j], B[i]], (mid[0], 0.3 if A is r1 else 0.0, mid[2]))
    L.poly(geo, mat, r2, (0, 1, 0))
    L.poly(geo, mat, r0, (0, -1, 0))
    return L.pt(0, d, 0)


def heater(geo, centre, axis, facing, length=1.45, w=0.19, t=0.07, drop=0.0, hang=UP):
    """Infrared bar heater (p25: the long slim units hung under the pergola beams, tilted toward the table).
    centre: centre of its glowing FACE; axis: its long direction; facing: the direction the face points.
    fx_heater_face carries 0..1 UVs (u along the length).  drop > 0 adds two hanger stems of that length from
    its back along `hang`.  36 triangles."""
    ax = _unit(axis)
    fc = np.asarray(facing, float)
    fc = _unit(fc - (fc @ ax) * ax)
    L = Loc(centre, ax, np.cross(fc, ax), fc)
    L.box(geo, 'fx_heater_body', (-length / 2, -w / 2, -t), (length / 2, w / 2, 0.0), faces='xXyYz')
    q = [(-length / 2, -w / 2, 0), (length / 2, -w / 2, 0), (length / 2, w / 2, 0), (-length / 2, w / 2, 0)]
    L.poly_uv(geo, 'fx_heater_face', q, [(0, 0), (1, 0), (1, 1), (0, 1)], (0, 0, 1))
    if drop > 0:
        hg = _unit(hang)
        for sa in (-0.3, 0.3):
            p = L.pt(sa * length, 0, -t * 0.5)
            sweep(geo, 'fx_heater_body', _rect(0.03, 0.03), [p, p + hg * (drop + t)], ax, closed=True, caps=(False, False))


def pergola(geo, origin, right, back, w, d, h=3.07, post=0.15, beam_w=0.10, upper=0.24, gap=0.20, lower=0.15,
            bays=4, blade=0.163, angle=70.0, chord=0.19, lights=2, heaters=True, lower_rear=False, rear_posts=True,
            speakers=(), mat='pergola_metal'):
    """Dark-bronze louvred pergola (p25 / p30 / seg123_039: the house's is 5.7 x 3.7 m, 3.07 m high; the
    cabana's the same system with closed blades, p27).

    origin: the FRONT-LEFT outer corner of its footprint on the floor (front = the open side away from the
    house, left as seen from outside looking at the front); right: along the front; back: toward the house
    (horizontal); w x d: outer footprint; h: top of the upper beams above the origin.
    Build-up, front elevation top-down: an upper perimeter beam `upper` deep carrying the louvres, an open band
    `gap`, a lower tie beam `lower` deep between the posts (front and sides; lower_rear adds it at the back),
    square posts `post` to the upper beam, bolted plates at the post heads and mid-span struts.
    bays - 1 rafters run front to back (the middle beam of bays = 2, three of them on the house's) with `lights`
    recessed down-lights each; the blades run front to back between them every `blade` m (chord `chord`),
    turned `angle` degrees from flat (0 = closed, 70 = the open setting of p25 / p30).
    heaters: two infrared bars under the side beams, tilted inward.  speakers: [(a, c), ...] positions on the
    REAR plane (a along right from the origin, c above the floor) for wall speakers facing the front.
    About 1.6k triangles for the house's.  Returns dict(lights=[...], heaters=[...], speakers=[...]) of world
    positions."""
    L = Loc(origin, right, back, UP)
    bw = beam_w
    z_up0, z_lo1 = h - upper, h - upper - gap
    z_lo0 = z_lo1 - lower
    # posts
    corners = [(0, 0), (w - post, 0)] + ([(0, d - post), (w - post, d - post)] if rear_posts else [])
    for a, b in corners:
        L.box(geo, mat, (a, b, 0), (a + post, b + post, z_up0), faces='xXyY')
    # upper perimeter beams (the front and rear run over the post heads to the outer corners)
    L.box(geo, mat, (0, 0, z_up0), (w, bw, h))
    L.box(geo, mat, (0, d - bw, z_up0), (w, d, h))
    L.box(geo, mat, (0, bw, z_up0), (bw, d - bw, h), faces='xXzZ')
    L.box(geo, mat, (w - bw, bw, z_up0), (w, d - bw, h), faces='xXzZ')
    # lower tie beams between the posts
    L.box(geo, mat, (post, 0, z_lo0), (w - post, bw, z_lo1), faces='yYzZ')
    for a0 in (0, w - bw):
        L.box(geo, mat, (a0, post, z_lo0), (a0 + bw, d - (post if rear_posts else 0), z_lo1), faces='xXzZ')
    if lower_rear:
        L.box(geo, mat, (post, d - bw, z_lo0), (w - post, d, z_lo1), faces='yYzZ')

    # bolted plates: on the post heads (front face, in the open band) and on the beam ends, mid-span struts
    def plate(a, c0, c1, width, face_b=0.0, sgn=-1):
        L.box(geo, mat, (a - width / 2, face_b + sgn * 0.008, c0), (a + width / 2, face_b, c1),
              faces='xXzZ' + ('y' if sgn < 0 else 'Y'))
        for da in (-width / 2 + 0.022, width / 2 - 0.022):
            for c in (c0 + 0.03, c1 - 0.03):
                L.box(geo, mat, (a + da - 0.008, face_b + sgn * 0.016, c - 0.008), (a + da + 0.008, face_b + sgn * 0.008, c + 0.008),
                      faces='xXzZ' + ('y' if sgn < 0 else 'Y'))

    for a in (post * 0.62, w - post * 0.62):
        plate(a, z_lo1 + 0.005, z_up0 - 0.005, 0.085)
    for a in (post * 0.5, w - post * 0.5):
        plate(a, z_up0 + 0.03, h - 0.03, 0.10)
    nb = max(1, bays)
    raf_w = 0.12
    raf_a = [w * k / nb for k in range(1, nb)]
    for a in raf_a:                               # struts in the open band under every rafter, bolted
        L.box(geo, mat, (a - 0.05, 0.0, z_lo1), (a + 0.05, bw, z_up0), faces='xXyY')
        plate(a, z_lo1 + 0.02, z_up0 - 0.02, 0.10)
    for b0 in ((post + (d - 2 * post) * 0.5),):   # one strut at mid depth on each side
        for a0 in (0, w - bw):
            L.box(geo, mat, (a0, b0 - 0.05, z_lo1), (a0 + bw, b0 + 0.05, z_up0), faces='xXyY')
    # rafters with down-lights
    out = dict(lights=[], heaters=[], speakers=[])
    zr0 = z_up0 + 0.02
    for a in raf_a:
        L.box(geo, mat, (a - raf_w / 2, bw, zr0), (a + raf_w / 2, d - bw, h - 0.01), faces='xXzZ')
        for i in range(lights):
            b = bw + (d - 2 * bw) * (i + 0.5) / lights
            out['lights'].append(downlight(geo, L.pt(a, b, zr0), -UP, r=0.042, trim=mat, n=8))
    # louvre blades: a lens section with a rolled lip, turned about its long axis
    th = math.radians(angle)
    cs, sn = math.cos(th), math.sin(th)
    c2, t2 = chord / 2, 0.013
    sec0 = [(-c2, 0.0), (-c2 + 0.03, -t2), (c2 - 0.03, -t2), (c2, -0.004), (c2, 0.018), (c2 - 0.012, 0.018),
            (c2 - 0.03, t2), (-c2 + 0.03, t2)]
    sec = [(x * cs - z * sn, x * sn + z * cs) for x, z in sec0]
    zc = h - upper * 0.5
    edges = [bw] + raf_a + [w - bw]
    nblade = 0
    for i in range(len(edges) - 1):
        lo = edges[i] + (raf_w / 2 if i > 0 else 0.0)
        hi = edges[i + 1] - (raf_w / 2 if i < len(edges) - 2 else 0.0)
        nbl = max(1, int((hi - lo) / blade))
        pitch = (hi - lo) / nbl
        for k in range(nbl):
            a = lo + (k + 0.5) * pitch
            sweep(geo, mat, sec, [L.pt(a, bw, zc), L.pt(a, d - bw, zc)], UP, 1.0, closed=True, caps=(False, False))
            nblade += 1
    out['blades'] = nblade
    # heaters under the side beams, tilted inward
    if heaters:
        hl = min(1.45, d * 0.42)
        for sg, a, ab in ((1, bw + 0.19, bw / 2), (-1, w - bw - 0.19, w - bw / 2)):
            fc = L.vec(sg * math.sin(math.radians(40)), 0, -math.cos(math.radians(40)))
            c = L.pt(a, d * 0.58, z_lo0 - 0.17)
            v = L.pt(ab, d * 0.58, z_lo0) - (c - 0.035 * fc)       # from the heater's back to the beam soffit
            heater(geo, c, L.ey, fc, length=hl, drop=float(np.linalg.norm(v)) - 0.07, hang=v)
            out['heaters'].append(c)
    for a, c in speakers:
        out['speakers'].append(speaker(geo, L.pt(a, d, c), -L.ex, -L.ey))
    return out


# =====================================================================================================================
# fence and gate
# =====================================================================================================================
BAY = 2.44            # post spacing (8 ft): p27, 200 px at 82 px / m
BOARD = 0.140         # board module = the fence_wood texture's (looks/surfaces.js): joints at u = k * 0.140
PICKET = 0.094        # picket spacing of the top band (2 x 2 pickets)


def _fence_panel(geo, L, x0, x1, h, band, kick, rail_step, board=BOARD, wood='fence_wood', frame=None):
    """One panel between two post faces in the bay frame L (a along the run, b toward the rail side, c up):
    cap, picket band between two rails, board-on-board boards, the horizontal rails."""
    span = x1 - x0
    if span < 0.05:
        return
    A = (1, 0, 0)                                       # grain of the horizontal members: along the run
    cap_t, tr, br = 0.038, 0.07, 0.09
    z_cap = h - cap_t
    z_tr = z_cap - tr
    z_br1 = z_tr - band
    z_br0 = z_br1 - br
    # band rails (texture u along the rail: grain along it)
    L.box(geo, wood, (x0, -0.019, z_tr), (x1, 0.019, z_cap), faces='yYz', grain=A)
    L.box(geo, wood, (x0, -0.026, z_br0), (x1, 0.026, z_br1), faces='yYzZ', grain=A)
    # pickets: three cut-out layers through the band's depth (front face, middle, back face)
    npk = max(1, int(round(span / PICKET)))
    for b in (-0.019, 0.0, 0.019):
        L.poly_uv(geo, 'fx_fence_pickets', [(x0, b, z_br1), (x1, b, z_br1), (x1, b, z_tr), (x0, b, z_tr)],
                  [(0, 0), (npk, 0), (npk, 1), (0, 1)], (0, 1, 0))
    # boards: a continuous inner layer and every other board standing proud on the rail side (board-on-board);
    # the far side is flat.  The texture's board joints (u = k * board from the panel's start) are the edges.
    b_in, b_out, b_far = -0.027, -0.008, -0.046
    o = L.pt(x0, 0, 0)
    L.poly(geo, wood, [(x0, b_in, kick), (x1, b_in, kick), (x1, b_in, z_br0), (x0, b_in, z_br0)], (0, 1, 0), uv_o=o)
    L.poly(geo, wood, [(x0, b_far, kick), (x1, b_far, kick), (x1, b_far, z_br0), (x0, b_far, z_br0)], (0, -1, 0), uv_o=o)
    k = 1
    while x0 + k * board < x1 - 0.03:
        a0, a1 = x0 + k * board, min(x0 + (k + 1) * board, x1)
        L.box(geo, wood, (a0, b_in, kick), (a1, b_out, z_br0), faces='xXY', uv_o=o)
        k += 2
    # horizontal rails on the rail side
    nr = max(2, int(round((z_br0 - kick) / rail_step)))
    for k in range(nr):
        z = kick + 0.10 + (z_br0 - kick - 0.10) * k / nr
        L.box(geo, frame or wood, (x0, b_out, z), (x1, b_out + 0.038, z + 0.089), faces='YzZ', grain=A)


def fence(geo, polyline, h=2.13, band=0.25, bay=BAY, post=0.14, side=1, kick=0.04, rail_step=1.0, cap=True,
          end_posts=(True, True), wood='fence_wood', post_mat='fx_fence_post'):
    """Cedar board fence with a picket-lattice top band (p27, p26).

    polyline: ground points [(x, y) or (x, y, z), ...]; every straight leg is divided into equal bays of at most
    `bay` m (2.44: the 8 ft post spacing of p27) with a dark-stained `post` square post at every division and
    corner.  h: top of the cap above the ground (the yard fence ~2.1 m; the tall privacy run behind the cabana
    ~3.4 m, with a rail every ~1.0 m); band: clear height of the square-picket band under the cap.
    side: +1 puts the RAIL side (posts proud, horizontal rails, the side seen from the yard in p27) on the LEFT
    of the polyline's direction of travel seen from above, -1 on the right; the other side shows flat boards.
    Boards are board-on-board on the 0.140 m module of the fence_wood texture, pickets every 0.094 m (fx_fence_pickets: a cut-out texture,
    one picket per unit of u).  Panels follow sloping ground (racked).  About 56 triangles per metre.
    Returns the post positions."""
    pts = [np.array([p[0], p[1], p[2] if len(p) > 2 else 0.0], float) for p in polyline]
    posts = []
    for s in range(len(pts) - 1):
        a, b = pts[s], pts[s + 1]
        hd = (b - a) * np.array([1, 1, 0])
        Lh = float(np.linalg.norm(hd))
        ex = hd / Lh
        ey = np.cross(UP, ex) * side
        nb = max(1, int(math.ceil(Lh / bay - 1e-6)))
        slope = (b[2] - a[2]) / Lh
        Lc = Loc(a, ex, ey, UP, slope=slope)
        for k in range(nb + 1):
            x = Lh * k / nb
            first, last = (s == 0 and k == 0), (s == len(pts) - 2 and k == nb)
            if k == 0 and s > 0:
                continue                                # the corner post was set by the previous leg
            if (first and not end_posts[0]) or (last and not end_posts[1]):
                continue
            Lp = Loc(Lc.pt(x, 0, 0), ex, ey, UP)
            Lp.box(geo, post_mat, (-post / 2, -post / 2, 0), (post / 2, post / 2, h - 0.038), faces='xXyY')
            posts.append(Lc.pt(x, 0, 0))
        for k in range(nb):
            x0, x1 = Lh * k / nb + post / 2, Lh * (k + 1) / nb - post / 2
            _fence_panel(geo, Lc, x0, x1, h, band, kick, rail_step, wood=wood)
        if cap:                                         # the cap runs through over the posts
            Lc.box(geo, wood, (-post / 2 - 0.01, -0.075, h - 0.038), (Lh + post / 2 + 0.01, 0.075, h),
                   faces='xXyYzZ', grain=(1, 0, 0))
    return posts


def gate(geo, a, b, h=2.13, band=0.25, post=0.14, side=1, open_deg=0.0, wood='fence_wood', frame_mat='fx_fence_post',
         posts=(True, True)):
    """Board gate matching the fence: one leaf between two posts, framed on the rail side with dark-stained
    2 x 4s and a diagonal brace, the same picket band and cap, black strap hinges and a latch.
    a: ground point of the hinge post, b: of the latch post (post centres); h: top of the cap; side as fence();
    open_deg swings the leaf about the hinge toward the rail side.  About 190 triangles."""
    a = np.array([a[0], a[1], a[2] if len(a) > 2 else 0.0], float)
    b = np.array([b[0], b[1], b[2] if len(b) > 2 else 0.0], float)
    hd = (b - a) * np.array([1, 1, 0])
    Lh = float(np.linalg.norm(hd))
    ex = hd / Lh
    ey = np.cross(UP, ex) * side
    for on, p in zip(posts, (a, b)):
        if on:
            Loc(p, ex, ey, UP).box(geo, frame_mat, (-post / 2, -post / 2, 0), (post / 2, post / 2, h + 0.06),
                                   faces='xXyYZ')
    # the leaf in its own frame, hinged at the first post's inner face
    th = math.radians(open_deg)
    lx = math.cos(th) * ex + math.sin(th) * ey
    ly = np.cross(UP, lx) * side
    hinge = a + ex * (post / 2 + 0.012)
    Lg = Loc(hinge, lx, ly, UP)
    wl = Lh - post - 0.024
    g = Geo()
    _fence_panel(g, Lg, 0.0, wl, h - 0.02, band, 0.07, 1.0, wood=wood, frame=frame_mat)
    geo.merge(g)
    Lg.box(geo, wood, (0, -0.06, h - 0.058), (wl, 0.06, h - 0.02), faces='xXyYzZ', grain=(1, 0, 0))
    # frame stiles and the brace on the rail side
    z1 = h - 0.058 - 0.07 - band - 0.09
    for x0 in (0.0, wl - 0.089):
        Lg.box(geo, frame_mat, (x0, -0.008, 0.07), (x0 + 0.089, 0.030, z1), faces='xXY')
    p0, p1 = Lg.pt(0.10, 0.011, 0.07 + 0.15), Lg.pt(wl - 0.10, 0.011, z1 - 0.15)
    sweep(geo, frame_mat, _rect(0.089, 0.038), [p0, p1], Lg.ey, closed=True, caps=(False, False))
    # hardware: strap hinges and a thumb latch
    for z in (0.35, z1 * 0.5 + 0.1, z1 - 0.15):
        Lg.box(geo, 'fx_iron', (-0.03, 0.030, z - 0.022), (0.36, 0.036, z + 0.022), faces='xXYzZ')
        Loc(a, ex, ey, UP).box(geo, 'fx_iron', (-0.02, post / 2, z - 0.04), (post / 2 + 0.01, post / 2 + 0.006, z + 0.04),
                               faces='xXYzZ')
    Lg.box(geo, 'fx_iron', (wl - 0.16, 0.030, 1.02), (wl + 0.03, 0.040, 1.07), faces='xXYzZ')
    Lg.box(geo, 'fx_iron', (wl - 0.14, 0.040, 0.98), (wl - 0.10, 0.075, 1.11), faces='xXYzZ')
    return dict(hinge=hinge, width=wl)
