"""
The PC-24-style control yoke as solids (rev J), from interior.YOKE_DESIGN -- the geometry sheet L6Y / L6Y2 draws, the
photo overlays project (drawing/yoke_overlay.py) and the L6 / L6B knee checks sweep (interior.yoke_*); the Stage-3
builder meshes the same solids.

YOKE-LOCAL MILLIMETRES (as YOKE_DESIGN): u lateral, + OUTBOARD (the co-pilot yoke's +y; the pilot yoke is the mirror
image), h up from the hub centre (the column axis / roll pivot), a aft (+x) of the aft face at the insert step.  The
grips' own outlines are given in their own sense (u > 0 away from the yoke centreline: the inboard grip is mirrored).

CURVE LAW (YOKE_DESIGN curve_law; judges D4): every outline is a centripetal Catmull-Rom spline (alpha 0.5, C1)
through its samples, sampled every 0.25 mm; the samples listed in the outline's corner table are corners -- R 0 a
sharp crease, R > 0 a fillet of that radius tangent to both sides (a cubic Bezier arc).  A run of two samples between
corners is straight.

SOLIDS are signed-distance fields (mm, negative inside; exact to ~0.1 mm at the surface, approximate away from it):
  cover        white Y shell incl. the silver inserts (parting grooves, the step V, the crown bevel and top land)
  body         satin black body: rim round the stem, hand-slot tops, arm backing, the two necks (outboard high web,
               inboard low saddle), side draft, top falling away forward, the foot radius
  grip_out/in  the grips: the aft-face outline G extruded along the aft-face normal (rake + toe) by the depth law,
               R 5 aft / R 11 forward edges, the leather pad recessed in its raised frame, the rolled heel lip, the
               heads (outboard: the round trim face on a flared dome; inboard: the shield facet)
Views: exact sections (contours of the field on a plane), silhouettes (contour of the field's minimum along the view
direction), visibility of feature curves by marching the field toward the viewer.
"""
from __future__ import annotations

import math

import numpy as np

_CACHE = {}


def T():
    from model import interior as I
    return I.YOKE_DESIGN


def tv(key):
    return np.asarray(T()[key], float)


# ============================================================================================ curves (D4)
def _cr_run(P, step=0.25, alpha=0.5):
    """Open centripetal Catmull-Rom curve through P (m, 2), m >= 2; ends extrapolated linearly (natural)."""
    P = np.asarray(P, float)
    if len(P) == 2:
        L = float(np.linalg.norm(P[1] - P[0]))
        n = max(2, int(math.ceil(L / step)) + 1)
        t = np.linspace(0.0, 1.0, n)[:, None]
        return P[0] + t * (P[1] - P[0])
    Q = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = [P[:1]]
    for i in range(1, len(Q) - 2):
        p0, p1, p2, p3 = Q[i - 1], Q[i], Q[i + 1], Q[i + 2]

        def tj(ti, a, b):
            return ti + max(float(np.linalg.norm(b - a)), 1e-9) ** alpha
        t0 = 0.0
        t1 = tj(t0, p0, p1)
        t2 = tj(t1, p1, p2)
        t3 = tj(t2, p2, p3)
        L = float(np.linalg.norm(p2 - p1))
        n = max(2, int(math.ceil(L / step)) + 1)
        t = np.linspace(t1, t2, n)[1:, None]
        A1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
        A2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
        A3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
        B1 = (t2 - t) / (t2 - t0) * A1 + (t - t0) / (t2 - t0) * A2
        B2 = (t3 - t) / (t3 - t1) * A2 + (t - t1) / (t3 - t1) * A3
        out.append((t2 - t) / (t2 - t1) * B1 + (t - t1) / (t2 - t1) * B2)
    return np.vstack(out)


def _cr_closed(P, step=0.25, alpha=0.5):
    P = np.asarray(P, float)
    n = len(P)
    Q = np.vstack([P[-1:], P, P[:2]])
    out = []
    for i in range(1, n + 1):
        seg = _cr_run(Q[i - 1:i + 3], step, alpha)
        # _cr_run on 4 points with phantom ends: take its middle segment only
        p1, p2 = Q[i], Q[i + 1]
        k0 = int(np.argmin(np.linalg.norm(seg - p1, axis=1)))
        k1 = int(np.argmin(np.linalg.norm(seg - p2, axis=1)))
        out.append(seg[k0:k1])
    return np.vstack(out)


def _arclen(Q):
    return np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))]


def _at(Q, s):
    """Point and unit tangent of the open polyline Q at arclength s."""
    L = _arclen(Q)
    s = float(np.clip(s, 0.0, L[-1]))
    i = int(np.clip(np.searchsorted(L, s) - 1, 0, len(Q) - 2))
    f = (s - L[i]) / max(L[i + 1] - L[i], 1e-12)
    p = Q[i] + f * (Q[i + 1] - Q[i])
    j0, j1 = max(0, i - 2), min(len(Q) - 1, i + 3)
    d = Q[j1] - Q[j0]
    return p, d / max(float(np.linalg.norm(d)), 1e-12), i


def _fillet(A, B, r):
    """Join the open polyline A (ending at the corner) and B (starting at it) with a fillet of radius r: returns
    (A trimmed, arc, B trimmed)."""
    Ar = A[::-1]
    _, tin, _ = _at(Ar, min(0.6, 0.3 * _arclen(Ar)[-1]))
    _, tout, _ = _at(B, min(0.6, 0.3 * _arclen(B)[-1]))
    tin = -tin
    c = float(np.clip(np.dot(tin, tout), -1.0, 1.0))
    th = math.acos(c)
    if th < math.radians(1.0) or r <= 0:
        return A, np.zeros((0, 2)), B
    t = r * math.tan(0.5 * th)
    t = min(t, 0.45 * _arclen(Ar)[-1], 0.45 * _arclen(B)[-1])
    pa, ta, ia = _at(Ar, t)
    pb, tb, ib = _at(B, t)
    ta = -ta
    h = 4.0 / 3.0 * math.tan(0.25 * th) * t / max(math.tan(0.5 * th), 1e-9)
    n = max(4, int(math.ceil(r * th / 0.2)))
    s = np.linspace(0.0, 1.0, n)[:, None]
    P0, P1, P2, P3 = pa, pa + h * ta, pb - h * tb, pb
    arc = (1 - s) ** 3 * P0 + 3 * (1 - s) ** 2 * s * P1 + 3 * (1 - s) * s ** 2 * P2 + s ** 3 * P3
    A2 = np.vstack([Ar[ia + 1:][::-1], pa[None, :]])
    B2 = np.vstack([pb[None, :], B[ib + 1:]])
    return A2, arc[1:-1], B2


def smooth_outline(pts, corners=None, closed=True, step=0.25):
    """Dense polyline through pts by the curve law: spline runs between corners, corners {i: R} filleted (R > 0) or
    sharp (R = 0).  Closed outlines without corners are periodic splines."""
    P = np.asarray(pts, float)
    corners = {int(k) % len(P): float(v) for k, v in dict(corners or {}).items()}
    if closed and not corners:
        return _cr_closed(P, step)
    idx = sorted(corners)
    if not closed:
        idx = sorted(set(idx) | {0, len(P) - 1})
    runs = []
    if closed:
        for k, i in enumerate(idx):
            j = idx[(k + 1) % len(idx)]
            seq = list(range(i, j + 1)) if j > i else list(range(i, len(P))) + list(range(0, j + 1))
            runs.append(_cr_run(P[seq], step))
    else:
        for i, j in zip(idx[:-1], idx[1:]):
            runs.append(_cr_run(P[i:j + 1], step))
    # fillets at the junctions (run k ends at corner idx[k + 1])
    nj = len(runs) if closed else len(runs) - 1
    for k in range(nj):
        c = idx[(k + 1) % len(idx)]
        r = corners.get(c, 0.0)
        if r > 0:
            k2 = (k + 1) % len(runs)
            A2, arc, B2 = _fillet(runs[k], runs[k2], r)
            runs[k] = np.vstack([A2, arc]) if len(arc) else A2
            runs[k2] = B2
    out = np.vstack([R[:-1] if (closed or i < len(runs) - 1) else R for i, R in enumerate(runs)])
    return out


def mirror_half(half, corners=None):
    """Closed symmetric outline (points + corner dict) from a half running from the top centre (u = 0) round the +u
    side to the bottom centre (u = 0); the centre points are smooth (not corners)."""
    H = np.asarray(half, float)
    n = len(H)
    M = H[::-1].copy()
    M[:, 0] *= -1.0
    full = np.vstack([H, M[1:-1]])
    cs = {}
    for i, r in dict(corners or {}).items():
        i = int(i)
        cs[i] = r                                  # the centre samples (0, n - 1) map onto themselves
        if 0 < i < n - 1:
            cs[2 * (n - 1) - i] = r
    return full, cs


def join_halves(right, left, rc=None, lc=None):
    """Closed outline from two halves in |u| sense (both from the top centre to the bottom centre): `right` drawn at
    u > 0, `left` mirrored to u < 0 (asymmetric parts: the body with its two necks)."""
    R = np.asarray(right, float)
    L = np.asarray(left, float)[::-1].copy()
    L[:, 0] *= -1.0
    nR = len(R)
    full = np.vstack([R, L[1:-1]])
    cs = {int(i): r for i, r in dict(rc or {}).items()}
    nL = len(L)
    for i, r in dict(lc or {}).items():
        j = nL - 1 - int(i)                       # index in the reversed left half
        if 0 < j < nL - 1:
            cs[nR - 1 + j] = r
    return full, cs


def outline(key, mirror=False, closed=True):
    """Dense outline of the table entry `key` with its corner table `key + '_corners'` (mirror: a *_half entry)."""
    ck = ("ol", key, mirror, id(T()[key]))
    if ck in _CACHE:
        return _CACHE[ck]
    pts = tv(key)
    cs = {int(i): r for i, r in T().get(key + "_corners", ())}
    if mirror:
        pts, cs = mirror_half(pts, cs)
    Q = smooth_outline(pts, cs, closed)
    _CACHE[ck] = Q
    return Q


# ============================================================================================ 2-D fields
class Field2D:
    """Signed distance (mm, negative inside) to a closed dense outline, or the unsigned distance to an open curve,
    rasterised at `res` mm and interpolated bilinearly (exact to ~res / 2)."""

    def __init__(self, P, res=0.1, margin=30.0, closed=True):
        from PIL import Image, ImageDraw
        from scipy import ndimage as ndi
        P = np.asarray(P, float)
        lo = P.min(0) - margin
        hi = P.max(0) + margin
        W = int(math.ceil((hi[0] - lo[0]) / res)) + 1
        H = int(math.ceil((hi[1] - lo[1]) / res)) + 1
        img = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(img)
        q = [((x - lo[0]) / res, (y - lo[1]) / res) for x, y in P]
        if closed:
            d.polygon(q, fill=255)
            m = np.asarray(img) > 127
            din = ndi.distance_transform_edt(m) * res
            dout = ndi.distance_transform_edt(~m) * res
            self.g = np.where(m, -(din - 0.5 * res), dout - 0.5 * res)
        else:
            d.line(q, fill=255, width=1)
            m = np.asarray(img) > 127
            self.g = ndi.distance_transform_edt(~m) * res
        self.lo, self.res, self.closed = lo, res, closed
        self.shape = self.g.shape

    def __call__(self, U, V):
        from scipy import ndimage as ndi
        U, V = np.asarray(U, float), np.asarray(V, float)
        x = (U - self.lo[0]) / self.res
        y = (V - self.lo[1]) / self.res
        xc = np.clip(x, 0, self.shape[1] - 1)
        yc = np.clip(y, 0, self.shape[0] - 1)
        g = ndi.map_coordinates(self.g, [yc.ravel(), xc.ravel()], order=1, mode="nearest").reshape(U.shape)
        out = np.hypot(x - xc, y - yc) * self.res
        return g + out


def field(name, P=None, closed=True, res=0.1):
    """Cached Field2D of a named outline (P given the first time, or the table entry of that name)."""
    key = ("field", name, res) if P is None else ("field", name, res, P.shape, float(np.sum(P)))
    if key not in _CACHE:
        if P is None:
            P = outline(name)
        _CACHE[key] = Field2D(P, res=res, closed=closed)
    return _CACHE[key]


# ============================================================================================ smooth booleans
def rmax(a, b, r):
    """Intersection of two fields, the edge rounded by r (r may be an array)."""
    r = np.asarray(r, float)
    return np.minimum(-r, np.maximum(a, b)) + np.hypot(np.maximum(r + a, 0.0), np.maximum(r + b, 0.0))


def smin(a, b, k):
    """Smooth union (polynomial, blend width k)."""
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def smoothstep(x, e0, e1):
    t = np.clip((np.asarray(x, float) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


# ============================================================================================ the shell / cover
def face_a(h):
    """a (mm) of the shell's aft face on the centreline at height h: the face_tilt plane above the step, below it a
    C1 cubic Hermite through face_lower whose first slope is the plane's (tangent at the step, judges D4)."""
    from scipy.interpolate import CubicHermiteSpline, PchipInterpolator
    key = ("face", id(T()["face_lower"]), float(T()["face_tilt"]))
    if key not in _CACHE:
        fl = tv("face_lower")
        hh, aa = fl[::-1, 0], fl[::-1, 1]                       # increasing h
        dd = PchipInterpolator(hh, aa).derivative()(hh)
        dd[-1] = -math.tan(math.radians(T()["face_tilt"]))
        _CACHE[key] = (CubicHermiteSpline(hh, aa, dd), float(fl[0, 0]), float(fl[-1, 0]))
    sp, h_s, h_lo = _CACHE[key]
    h = np.asarray(h, float)
    up = -(h - h_s) * math.tan(math.radians(T()["face_tilt"]))
    lo = sp(np.clip(h, h_lo - 20.0, h_s))
    return np.where(h >= h_s, up, lo)


def shell_outline():
    return outline("shell_half", mirror=True)


def insert_upper_outline():
    """Upper insert: the shell's top edge between the arm junctions, the parting grooves and the step."""
    key = ("insup", id(T()["insert_side"]), id(T()["shell_half"]), id(T()["step"]))
    if key in _CACHE:
        return _CACHE[key]
    sh = tv("shell_half")
    j = int(np.argmin(np.hypot(sh[:, 0] - tv("insert_side")[0, 0], sh[:, 1] - tv("insert_side")[0, 1])))
    side = tv("insert_side")
    st = tv("step")
    half = np.vstack([sh[:j + 1], side[1:], st[:1]])
    cs = {int(i): r for i, r in T().get("shell_half_corners", ()) if int(i) < j}
    ic = dict(T().get("insert_corners", ()))
    cs[j] = float(ic.get("junction", 0.0))
    cs[len(half) - 2] = float(ic.get("step_end", 0.0))
    cs[len(half) - 1] = 0.0                                          # the step's V apex
    pts, cs2 = mirror_half(half, cs)
    Q = smooth_outline(pts, cs2)
    _CACHE[key] = Q
    return Q


def insert_lower_outline():
    return outline("insert_lower_half", mirror=True)


def _curve_dist(name, P):
    return field(name, np.asarray(P, float), closed=False, res=0.1)


def _groove_curves():
    """Open curves of the cover's parting grooves: the upper insert's sides (both), the step, the lower insert."""
    key = ("grooves", id(T()["insert_side"]), id(T()["step"]), id(T()["insert_lower_half"]))
    if key in _CACHE:
        return _CACHE[key]
    side = _cr_run(tv("insert_side"))
    st = tv("step")
    step = np.vstack([st[1] * [-1, 1], st[0], st[1]])
    out = dict(side_r=side, side_l=side * [-1, 1], step=step, lower=np.vstack([insert_lower_outline(),
                                                                                insert_lower_outline()[:1]]))
    _CACHE[key] = out
    return out


def cover_top(U, H):
    """a of the cover's aft surface at (u, h): the face, the crown bevel above its crease (insert only) and the top
    land along the top edges (YOKE_DESIGN crown)."""
    U, H = np.asarray(U, float), np.asarray(H, float)
    hc, beta, land_d, land_w = (float(x) for x in T()["crown"][:4])
    a = face_a(H)
    ins = field("insert_upper", insert_upper_outline())(U, H)
    bev = np.where(ins < 0.0, np.maximum(H - hc, 0.0) * math.tan(math.radians(beta)), 0.0)
    d2 = field("shell", shell_outline())(U, H)
    gh = (field("shell", shell_outline())(U, H + 0.2) - field("shell", shell_outline())(U, H - 0.2)) / 0.4
    up = smoothstep(gh, 0.35, 0.6)                                   # top edges: outward normal pointing up
    land = up * land_d * np.clip((d2 + land_w) / land_w, 0.0, 1.0)
    return a - bev - land


def cover(U, H, A):
    """Signed distance of the white cover + inserts (mm)."""
    U, H, A = (np.asarray(x, float) for x in (U, H, A))
    E = T()["edges"]
    d2 = field("shell", shell_outline())(U, H)
    top = cover_top(U, H)
    aft = A - top
    fwd = (face_a(H) - float(T()["cover_t"])) - A
    # edge radius: R 1 perimeter, R 2 along the arms' lower edges, R 3 under the foot
    arm_lower = smoothstep(np.abs(U), 36.0, 40.0) * (H < 20.0 + (np.abs(U) - 36.0) * 0.78).astype(float)
    r = float(E[0]) + (float(E[1]) - float(E[0])) * arm_lower + (float(E[2]) - float(E[0])) * smoothstep(-H, 48.0, 53.0)
    s = np.maximum(rmax(d2, aft, r), rmax(d2, fwd, 0.5))
    # parting grooves (V, width w, depth g) cut from the aft surface
    gw = T()["grooves"]
    z = top - A                                                       # depth below the aft surface
    for nm, (w, g) in (("side_r", gw[0]), ("side_l", gw[0]), ("step", gw[1]), ("lower", gw[2])):
        dc = _curve_dist("groove_" + nm, _groove_curves()[nm])(U, H)
        v = (dc - 0.5 * w * (1.0 - z / g)) * (g / math.hypot(g, 0.5 * w))
        s = np.maximum(s, -v)
    return s


def cover_part(U, H):
    """'insert_up' / 'insert_lo' / 'cover' for points of the cover by their front-view position."""
    iu = field("insert_upper", insert_upper_outline())(U, H) < 0
    il = field("insert_lower", insert_lower_outline())(U, H) < 0
    return np.where(iu, 1, np.where(il, 2, 0))


# ============================================================================================ grips
def grip_axis_u(h):
    (ub, hb), (ut, ht) = T()["grip_axis"]
    return ub + (np.asarray(h, float) - hb) * (ut - ub) / (ht - hb)


def grip_frame(g):
    """Aft-face plane of grip g ('out' / 'in', own sense): dict(p0 (u, h, a), n unit normal (u, h, a) pointing aft-out,
    tan_toe, tan_rake)."""
    h0, a0 = (float(x) for x in T()["grip_a0"])
    rake = math.radians(float(T()["grip_rake"]))
    toe = math.radians(float(T()["grip_toe"][0 if g == "out" else 1]))
    tt, tr = math.tan(toe), math.tan(rake)
    n = np.array([tt, tr, 1.0])
    n /= np.linalg.norm(n)
    return dict(p0=np.array([float(grip_axis_u(h0)), h0, a0]), n=n, tt=tt, tr=tr)


def grip_plane_a(U, H, g):
    """a of grip g's aft-face plane at the front-view point (u, h) (own sense)."""
    f = grip_frame(g)
    return f["p0"][2] - (np.asarray(H, float) - f["p0"][1]) * f["tr"] - (np.asarray(U, float) - f["p0"][0]) * f["tt"]


def grip_outline(g):
    """Aft-face outline G of grip g (front view, own sense; table grip_out / grip_in)."""
    return outline("grip_" + g)


def pad_outline(g):
    return outline("pad_" + g)


def _depth(h, g):
    k = tv("grip_depth")
    return np.interp(h, k[:, 0], k[:, 1 if g == "out" else 2])


def _to_plane(U, H, A, g):
    """(z, uf, hf): signed distance of the points from grip g's aft plane (+ aft), and the front-view coordinates of
    their foot on the plane (own sense)."""
    f = grip_frame(g)
    n = f["n"]
    P = np.stack([U, H, A], -1)
    z = (P - f["p0"]) @ n
    F = P - z[..., None] * n
    return z, F[..., 0], F[..., 1]


def grip_surface_z(uf, hf, g):
    """Offset (mm, along the aft normal) of the grip's aft surface from its plane at the plane point (uf, hf): 0 on
    the frame, the leather pad recessed and crowned inside the pad outline, the heel lip proud below the pad."""
    ps = T()["pad_section"]
    rec, cen, wc = float(ps[0]), float(ps[1]), float(ps[2])
    dp = field("pad_" + g, pad_outline(g))(uf, hf)
    leather = -rec + (rec + cen) * smoothstep(-dp, 0.0, wc)
    z = np.where(dp < 0.0, leather, 0.0)
    # heel lip: between the pad bottom and the outline's bottom, proud by `proud`, rolled
    hl, proud = (float(x) for x in T()["heel"][:2])
    pb = float(np.min(pad_outline(g)[:, 1]))
    t = np.clip((pb - hf) / hl, 0.0, 1.0)
    lip = proud * np.sin(np.pi * np.clip(t, 0.0, 1.0)) ** 0.6 * (hf < pb)
    return z + lip


def _head_out(U, H, A):
    """The outboard (trim) head's shaping field (negative inside): a flared round dome whose flat round face carries
    the trim ring (head_out)."""
    c, n = head_out_face()
    ho = T()["head_out"]
    R, flare, r_e = 0.5 * float(ho[2]), math.radians(float(ho[5])), float(ho[6])
    P = np.stack([U, H, A], -1) - c
    zf = P @ n                                                        # + above (aft-up of) the face
    rho = np.linalg.norm(P - zf[..., None] * n, axis=-1)
    side = (rho - R - np.maximum(-zf, 0.0) * math.tan(flare)) * math.cos(flare)
    return rmax(side, zf, r_e)


def head_out_face():
    """Centre (u, h, a) and unit normal (u, h, a) of the outboard head's round face (head_out: the trim centre, up
    angle above aft, turned toward the yoke centreline)."""
    ho = T()["head_out"]
    up, turn = math.radians(float(ho[3])), math.radians(float(ho[4]))
    n = np.array([-math.cos(up) * math.sin(turn), math.sin(up), math.cos(up) * math.cos(turn)])
    return np.array([float(ho[0]), float(ho[1]), float(T()["head_out_a"])]), n


def head_in_face():
    """Point (u, h, a) and unit normal of the inboard head's shield facet (head_in), own sense."""
    hi = T()["head_in"]
    up, toe = math.radians(float(hi[2])), math.radians(float(hi[3]))
    n = np.array([math.cos(up) * math.sin(toe), math.sin(up), math.cos(up) * math.cos(toe)])
    return np.array([float(hi[0]), float(hi[1]), float(T()["head_in_a"])]), n


def _facet_frame(c, n):
    eu = np.cross([0.0, 1.0, 0.0], n)
    eu /= np.linalg.norm(eu)
    ev = np.cross(n, eu)
    return eu, ev


def shield_outline():
    """The inboard head's shield facet outline in its own plane (x across +outboard-of-grip, y up), dense."""
    return outline("shield")


def _head_in(U, H, A):
    """The inboard head's shaping field: the shield facet plane, the head's top surfaces falling forward from the
    shield outline at the chamfer angle (head_in)."""
    c, n = head_in_face()
    eu, ev = _facet_frame(c, n)
    P = np.stack([U, H, A], -1) - c
    zf = P @ n
    x, y = P @ eu, P @ ev
    S = shield_outline()
    # the fall-off runs round the shield's top and sides only: below it the head runs on into the grip's aft face
    rect = np.array([(S[:, 0].min(), -80.0), (S[:, 0].max(), -80.0), (S[:, 0].max(), 0.0), (S[:, 0].min(), 0.0)])
    ds = np.minimum(field("shield", S)(x, y), field("shield_below", rect, closed=True)(x, y))
    chi = math.radians(float(T()["head_in"][4]))
    return zf + np.maximum(ds, 0.0) * math.tan(chi)


def _head_chamfer(U, H, A):
    """Field of the region forward of / above the outboard head's lower chamfer: a plane through the round face's
    lower edge falling back to the grip's aft plane at head_out[8] deg (negative = inside)."""
    c, n = head_out_face()
    eu, ev = _facet_frame(c, n)
    R = 0.5 * float(T()["head_out"][2])
    le = c - R * ev                                                   # the face's lowest point
    ang = math.radians(float(T()["head_chamfer"]))
    # plane through le containing eu, rising aft at ang from the h axis: normal (0, -sin, cos) in (u, h, a)
    nn = np.array([0.0, -math.sin(ang), math.cos(ang)])
    P = np.stack([U, H, A], -1) - le
    return P @ nn


def grip(U, H, A, g):
    """Signed distance of grip g (own sense: u > 0 away from the yoke centreline), incl. its head, pad and heel.
    The grip prism (aft-face outline G on the raked / toed aft plane, the pad recess and heel lip, depth law, edge
    radii) is trimmed above the head zone by the head's shape; the head itself is a second solid unioned with it:
    outboard the round trim face on a near-cylinder about the face normal, its lower edge chamfered back to the aft
    plane (it stands proud of the aft plane below the face centre); inboard the shield facet, the head falling forward
    at head_in[4] deg round it."""
    U, H, A = (np.asarray(x, float) for x in (U, H, A))
    z, uf, hf = _to_plane(U, H, A, g)
    d2 = field("grip_" + g, grip_outline(g))(uf, hf)
    zs = grip_surface_z(uf, hf, g)
    ra, rf = (float(x) for x in T()["grip_edges"][:2])
    aft = z - zs
    fwd = -z - _depth(hf, g)
    prism = np.maximum(rmax(d2, aft, ra), rmax(d2, fwd, rf))
    if g == "out":
        hz = float(T()["head_out"][7])
        cut = _head_out(U, H, A)
        prism = np.maximum(prism, cut - 3.0 * np.maximum(hz - hf, 0.0))
        head = np.maximum.reduce([cut, _head_chamfer(U, H, A), rmax(d2, fwd, rf)])
    else:
        hz = float(T()["head_in"][5])
        cut = _head_in(U, H, A)
        prism = np.maximum(prism, cut - 3.0 * np.maximum(hz - hf, 0.0))
        head = np.maximum.reduce([cut, rmax(d2, fwd, rf), z - zs - 4.0])
    return smin(prism, head, 1.0)


def grip_part(U, H, A, g):
    """1 where a surface point of grip g is leather (inside the pad outline, within 1.5 of the leather surface)."""
    z, uf, hf = _to_plane(U, H, A, g)
    dp = field("pad_" + g, pad_outline(g))(uf, hf)
    return (dp < -0.2) & (z > grip_surface_z(uf, hf, g) - 1.5)


# ============================================================================================ body
def body_outline():
    """Front outline of the black body: the outboard half (body_half) at u > 0, the inboard half (body_in) at u < 0."""
    key = ("bodyol", id(T()["body_half"]), id(T()["body_in"]))
    if key not in _CACHE:
        pts, cs = join_halves(tv("body_half"), tv("body_in"), dict(T().get("body_half_corners", ())),
                              dict(T().get("body_in_corners", ())))
        _CACHE[key] = smooth_outline(pts, cs)
    return _CACHE[key]


def body_top_h(u):
    """h of the body's top line at its aft face (table body_top, symmetric in u): a smooth C1 curve."""
    from scipy.interpolate import PchipInterpolator
    key = ("bodytop", id(T()["body_top"]))
    if key not in _CACHE:
        bt = tv("body_top")
        _CACHE[key] = PchipInterpolator(bt[:, 0], bt[:, 1], extrapolate=True)
    u0 = float(T()["neck"][0])
    return _CACHE[key](np.clip(np.abs(np.asarray(u, float)), 0.0, u0))


def body_aft(U, H):
    """a of the body's aft surface: cover_t ahead of the face in the core, blending over the neck zone onto the grip's
    aft plane (necks), own grip by the sign of u."""
    U, H = np.asarray(U, float), np.asarray(H, float)
    u0, u1 = (float(x) for x in T()["neck"][:2])
    core = face_a(H) - float(T()["cover_t"])
    w = smoothstep(np.abs(U), u0, u1)
    gp = np.where(U >= 0, grip_plane_a(np.abs(U), H, "out"), grip_plane_a(np.abs(U), H, "in"))
    return (1.0 - w) * core + w * gp


def body(U, H, A):
    """Signed distance of the black body (mm)."""
    U, H, A = (np.asarray(x, float) for x in (U, H, A))
    bf = T()["body_form"]
    depth, top_deg, draft, r_aft, r_fwd, r_foot = (float(x) for x in bf[:6])
    u0, u1, nd = (float(x) for x in T()["neck"][:3])
    d2 = field("body", body_outline())(U, H)
    ab = body_aft(U, H)
    s_in = ab - A                                                     # depth below the aft surface
    w = smoothstep(np.abs(U), u0, u1)
    d2e = d2 + (1.0 - w) * np.maximum(s_in, 0.0) * math.tan(math.radians(draft))
    htu = body_top_h(U)
    a_core = np.maximum(ab - depth, ab - np.maximum(htu - H, 0.0) / math.tan(math.radians(top_deg)))
    a_f = (1.0 - w) * a_core + w * (ab - nd)
    aft = A - ab
    fwd = a_f - A
    rf = r_fwd + (r_foot - r_fwd) * smoothstep(-H, 40.0, 55.0)
    return np.maximum(rmax(d2e, aft, r_aft), rmax(d2e, fwd, rf))


# ============================================================================================ the assembly
PARTS = ("body", "cover", "grip_out", "grip_in")


def part_sdf(name, U, H, A):
    if name == "black":
        k = float(T()["neck"][3])
        return smin(smin(body(U, H, A), grip(U, H, A, "out"), k), grip(-U, H, A, "in"), k)
    if name == "cover":
        return cover(U, H, A)
    if name == "body":
        return body(U, H, A)
    if name == "grip_out":
        return grip(U, H, A, "out")
    if name == "grip_in":
        return grip(-U, H, A, "in")
    raise KeyError(name)


def union_sdf(U, H, A, parts=PARTS):
    s = None
    for p in parts:
        v = part_sdf(p, U, H, A)
        s = v if s is None else np.minimum(s, v)
    return s


BOX = dict(black=(-154, -68, -78, 154, 104, 26), body=(-108, -68, -78, 108, 100, 6), cover=(-77, -61, -34, 77, 71, 6),
           grip_out=(76, -54, -66, 154, 104, 26), grip_in=(-154, -54, -66, -76, 104, 26))


def section(plane_pt, e1, e2, extent, parts=PARTS, step=0.25, clip=False):
    """Exact section of the parts on the plane through plane_pt spanned by the unit vectors e1, e2 (u, h, a):
    {part: [closed (N, 2) contours in (s1, s2)]} over extent (s1_0, s2_0, s1_1, s2_1); clip=True cuts the section
    to the extent (a detail of a larger cut: closed contours along the extent's edges).  Disk-cached."""
    key = ("section", tuple(np.round(np.asarray(plane_pt, float), 6)), tuple(np.round(np.asarray(e1, float), 9)),
           tuple(np.round(np.asarray(e2, float), 9)), tuple(extent), tuple(parts), step, clip)
    return disk_cached(key, lambda: _section(plane_pt, e1, e2, extent, parts, step, clip))


def _section(plane_pt, e1, e2, extent, parts, step, clip=False):
    import contourpy
    s1 = np.arange(extent[0], extent[2] + 0.5 * step, step)
    s2 = np.arange(extent[1], extent[3] + 0.5 * step, step)
    S1, S2 = np.meshgrid(s1, s2)
    p = np.asarray(plane_pt, float)
    P = p + S1[..., None] * np.asarray(e1, float) + S2[..., None] * np.asarray(e2, float)
    out = {}
    inner = np.minimum.reduce([S1 - extent[0], extent[2] - S1, S2 - extent[1], extent[3] - S2]) - 2.0 * step
    for nm in parts:
        F = part_sdf(nm, P[..., 0], P[..., 1], P[..., 2])
        if clip:
            F = np.maximum(F, -inner)
        if F.min() > 0:
            continue
        lines = contourpy.contour_generator(s1, s2, F).lines(0.0)
        out[nm] = [np.asarray(L, float) for L in lines if len(L) > 3]
    return out


def silhouette(name, axis, step=0.4, depth_step=0.5, extent=None):
    """Silhouette of part `name` projected along `axis` ('u', 'h' or 'a'): contours of min_axis F over the view
    plane's grid (x, y = the two remaining axes in u, h, a order; extent (x0, y0, x1, y1), default the part's BOX):
    returns ([closed (N, 2) (x, y) contours], (x, y, field))."""
    import contourpy
    b = BOX[name]
    ax = "uha".index(axis)
    rest = [i for i in range(3) if i != ax]
    if extent is None:
        extent = (b[rest[0]], b[rest[1]], b[rest[0] + 3], b[rest[1] + 3])
    x = np.arange(extent[0], extent[2] + 0.5 * step, step)
    y = np.arange(extent[1], extent[3] + 0.5 * step, step)
    X, Y = np.meshgrid(x, y)
    zs = np.arange(b[ax], b[ax + 3] + 0.5 * depth_step, depth_step)
    best = np.full(X.shape, np.inf)
    for z in zs:
        C = [None, None, None]
        C[rest[0]], C[rest[1]], C[ax] = X, Y, np.full(X.shape, z)
        best = np.minimum(best, part_sdf(name, C[0], C[1], C[2]))
    lines = contourpy.contour_generator(x, y, best).lines(0.0)
    return [np.asarray(L, float) for L in lines if len(L) > 3], (x, y, best)


def grip_axis_3d(g):
    """(p, t): a point on grip g's axis on its aft plane at h 0 and the unit axis direction (u, h, a), own sense."""
    (ub, hb), (ut, ht) = T()["grip_axis"]
    d2 = np.array([ut - ub, ht - hb])
    f = grip_frame(g)
    da = -d2[1] * f["tr"] - d2[0] * f["tt"]
    t = np.array([d2[0], d2[1], da])
    t /= np.linalg.norm(t)
    u0 = float(grip_axis_u(0.0))
    p = np.array([u0, 0.0, float(grip_plane_a(u0, 0.0, g))])
    return p, t


def grip_section_frame(g, h):
    """Section plane of grip g normal to its axis through the axis point at height h: (p, e1 across (+ away from
    the yoke centreline), e2 along the aft normal (+ aft)), own sense."""
    p0, t = grip_axis_3d(g)
    p = p0 + t * (h - p0[1]) / t[1]
    n = grip_frame(g)["n"]
    e2 = n - t * float(np.dot(n, t))
    e2 /= np.linalg.norm(e2)
    e1 = np.cross(e2, t)
    if e1[0] < 0:
        e1 = -e1
    return p, e1, e2


def to_cop(v, g, vec=False):
    """Own-sense (u, h, a) point / vector of grip g -> the yoke's (co-pilot) sense (the inboard grip mirrored)."""
    v = np.asarray(v, float).copy()
    if g == "in":
        v[..., 0] *= -1.0
    return v


def grip_section(g, h, extent=(-40.0, -45.0, 40.0, 12.0), step=0.2, parts=None):
    """Section of grip g normal to its axis at height h: {part: contours (x across + away from the centreline, y along
    the aft normal + aft)}."""
    p, e1, e2 = grip_section_frame(g, h)
    return section(to_cop(p, g), to_cop(e1, g), to_cop(e2, g), extent, parts=parts or ("grip_" + g, "body"), step=step)


def view_silhouettes(axis, step=0.4, depth_step=1.0, parts=PARTS):
    """{part: [closed contours]} of every part seen along `axis` ('u' side, 'h' plan, 'a' front), in the view's
    natural coordinates: 'u' -> (a, h), 'h' -> (u, a), 'a' -> (u, h).  The minimum of a distance field over depth
    samples 1.0 apart is within 0.13 mm of the true one at a silhouette whose radius is >= 1 mm.  Cached."""
    def fn():
        out = {}
        for p in parts:
            lines, _ = silhouette(p, axis, step=step, depth_step=depth_step)
            out[p] = [L[:, ::-1] if axis == "u" else L for L in lines]
        return out
    return disk_cached(("views", axis, step, depth_step, tuple(parts)), fn)


def design_key():
    """Hash of everything the solids depend on: the YOKE_DESIGN table (values) and this module's source."""
    import hashlib
    from pathlib import Path
    h = hashlib.sha1(repr(sorted((k, tuple(map(repr, np.ravel(np.asarray(v, dtype=object)))) if not isinstance(v, str)
                                  else v) for k, v in T().items())).encode())
    h.update(Path(__file__).read_bytes())
    return h.hexdigest()[:16]


def disk_cached(key, fn):
    """fn() cached in memory and on disk (out/tmp/yoke_geom_cache, git-ignored) under key + design_key(): the sheets
    and checks of one design share the expensive views / sections; any table or code change makes a new key."""
    import hashlib
    import pickle
    from pathlib import Path
    full = (design_key(),) + tuple(key)
    if full in _CACHE:
        return _CACHE[full]
    d = Path(__file__).resolve().parents[1] / "out" / "tmp" / "yoke_geom_cache"
    f = d / (hashlib.sha1(repr(full).encode()).hexdigest()[:20] + ".pkl")
    if f.exists():
        try:
            _CACHE[full] = pickle.loads(f.read_bytes())
            return _CACHE[full]
        except Exception:                                    # noqa: BLE001
            pass
    val = fn()
    try:
        d.mkdir(parents=True, exist_ok=True)
        tmp = f.with_suffix(".tmp")
        tmp.write_bytes(pickle.dumps(val))
        tmp.replace(f)
    except OSError:
        pass
    _CACHE[full] = val
    return val
