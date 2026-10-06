"""
The PC-24-style control yoke as solids (rev K), from interior.YOKE_DESIGN -- the geometry sheets L6Y / L6Y2 draw, the
photo overlays project (drawing/yoke_overlay.py), the L6 / L6B knee checks sweep (interior.yoke_*) and the acceptance
checks measure (model/yoke_checks.py).

YOKE-LOCAL MILLIMETRES (as YOKE_DESIGN): u lateral, + OUTBOARD (the co-pilot yoke's +y; the pilot yoke is the mirror
image), h up from the hub centre (the column axis / roll pivot), a aft (+x) of the aft face at the insert step.  The
grips' own outlines are given in their own sense (u > 0 away from the yoke centreline: the inboard grip is mirrored).

CURVE LAW (YOKE_DESIGN curve_law; judges D4, rev L DR3-07): every outline is a C2 cubic spline on centripetal knots
(alpha 0.5) through its samples, sampled every 0.25 mm -- curvature continuous at every sample that is not a corner;
the samples listed in the outline's corner table are corners -- R 0 a sharp crease, R > 0 a fillet of that radius
tangent to both sides (a cubic Bezier arc).  A run of two samples between corners is straight.

2-D FIELDS (judges DR2-01): the EXACT signed distance to those dense polylines (Field2D: KD-tree + segment projection
near the zero level, exact node values elsewhere) -- the zero level is the polyline itself, the rounds and blends see a
smooth field.

SOLIDS are signed-distance fields (mm, negative inside):
  cover        white Y shell incl. the silver inserts (parting grooves, the step V, the badge grooves, the crown's soft
               break and top land, the TCS seat)
  body         satin black body: rim round the stem, hand-slot tops, arm backing, the two necks (outboard high web held
               under the trim face, inboard low saddle), side draft, top plane falling forward (from the horizontal),
               the top-to-front and foot rounds, the AFCS boss
  grip_out/in  the grips: the aft-face outline G on the raked / toed aft plane, walls along grip_walls (between the
               fore-aft axis and the aft normal), PCHIP depth, frame roll R grip_edges[0] growing to the heel's R,
               forward edges R grip_edges[1] capped by the outline's half-width, the pad pocket with its groove and
               bead, the heel lip; the heads (outboard: the round trim face on a flared dome with its V-grooves;
               inboard: the shield facet), unioned in the head zone only
  tcs, afcs, trim, button   the switches as revolve / extrude solids seated on the cover, the boss and the heads
Views: exact sections (contours of the field on a plane), silhouettes (contour of the field's minimum along the view
direction).

STAGE-3 SURFACE ROUTE (judges DR2-01): patches, not an implicit mesher -- each face a grid_surface over its analytic
parametrisation (the face_a profile, the grip / facet planes) trimmed by cad.mesh.trim with these exact 2-D fields;
each tabled edge round a sweep_profile of its radius along the outline; creases only where a corner table / pad step /
groove says so; vertex normals from the analytic surfaces.  These solids stay the inside / outside oracle for fit_check
and the sheets; acceptance: model/yoke_checks.py.
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
def curve_step():
    """The curve law's sampling step (curve_law[0], mm along each chord / fillet arc)."""
    return float(T()["curve_law"][0])


def _spline_run(P, step=None, alpha=0.5, closed=False):
    """C2 cubic spline through P (m, 2) on centripetal knots (chord length ** alpha): open runs between corners
    'natural' at their ends (the corner fillets join them G1 with their tabled radius), closed corner-free outlines
    periodic; sampled per segment every <= step mm along the chord.  Rev L (judges DR3-07): curvature is continuous
    at every interior sample (rev K's centripetal Catmull-Rom was C1 only -- R 13 / R 3.4 either side of a shell knot).
    A run of two samples is straight."""
    from scipy.interpolate import CubicSpline
    step = curve_step() if step is None else step
    P = np.asarray(P, float)
    Q = np.vstack([P, P[:1]]) if closed else P
    if len(Q) == 2:
        L = float(np.linalg.norm(Q[1] - Q[0]))
        n = max(2, int(math.ceil(L / step)) + 1)
        t = np.linspace(0.0, 1.0, n)[:, None]
        return Q[0] + t * (Q[1] - Q[0])
    t = np.r_[0.0, np.cumsum(np.maximum(np.linalg.norm(np.diff(Q, axis=0), axis=1), 1e-9) ** alpha)]
    cs = CubicSpline(t, Q, bc_type="periodic" if closed else "natural")
    out = [Q[:1]]
    for i in range(len(Q) - 1):
        n = max(2, int(math.ceil(float(np.linalg.norm(Q[i + 1] - Q[i])) / step)) + 1)
        out.append(cs(np.linspace(t[i], t[i + 1], n)[1:]))
    R = np.vstack(out)
    return R[:-1] if closed else R


def spline_of(P, alpha=0.5, closed=False):
    """The CubicSpline object (and its knots) of _spline_run, for the curve-law acceptance (knot curvature)."""
    from scipy.interpolate import CubicSpline
    P = np.asarray(P, float)
    Q = np.vstack([P, P[:1]]) if closed else P
    t = np.r_[0.0, np.cumsum(np.maximum(np.linalg.norm(np.diff(Q, axis=0), axis=1), 1e-9) ** alpha)]
    return CubicSpline(t, Q, bc_type="periodic" if closed else "natural"), t


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


FILLET_CAPPED = []                # (corner (u, h), tabled R, R actually drawn) for every fillet reduced by the cap


def _fillet(A, B, r, step=None):
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
    cap = min(0.45 * _arclen(Ar)[-1], 0.45 * _arclen(B)[-1])
    if t > cap:                    # rev M (judges DR4-03): the tangent length is capped at 0.45 of either run --
        FILLET_CAPPED.append((tuple(np.round(Ar[0], 2)), float(r),       # the fillet then has a smaller radius
                              float(cap / max(math.tan(0.5 * th), 1e-9))))
        t = cap
    pa, ta, ia = _at(Ar, t)
    pb, tb, ib = _at(B, t)
    ta = -ta
    h = 4.0 / 3.0 * math.tan(0.25 * th) * t / max(math.tan(0.5 * th), 1e-9)
    n = max(4, int(math.ceil(r * th / (curve_step() if step is None else step))))
    s = np.linspace(0.0, 1.0, n)[:, None]
    P0, P1, P2, P3 = pa, pa + h * ta, pb - h * tb, pb
    arc = (1 - s) ** 3 * P0 + 3 * (1 - s) ** 2 * s * P1 + 3 * (1 - s) * s ** 2 * P2 + s ** 3 * P3
    A2 = np.vstack([Ar[ia + 1:][::-1], pa[None, :]])
    B2 = np.vstack([pb[None, :], B[ib + 1:]])
    return A2, arc[1:-1], B2


def smooth_outline(pts, corners=None, closed=True, step=None):
    """Dense polyline through pts by the curve law: spline runs between corners, corners {i: R} filleted (R > 0) or
    sharp (R = 0).  Closed outlines without corners are periodic splines."""
    step = curve_step() if step is None else step
    P = np.asarray(pts, float)
    corners = {int(k) % len(P): float(v) for k, v in dict(corners or {}).items()}
    if closed and not corners:
        return _spline_run(P, step, closed=True)
    idx = sorted(corners)
    if not closed:
        idx = sorted(set(idx) | {0, len(P) - 1})
    runs = []
    if closed:
        for k, i in enumerate(idx):
            j = idx[(k + 1) % len(idx)]
            seq = list(range(i, j + 1)) if j > i else list(range(i, len(P))) + list(range(0, j + 1))
            runs.append(_spline_run(P[seq], step))
    else:
        for i, j in zip(idx[:-1], idx[1:]):
            runs.append(_spline_run(P[i:j + 1], step))
    # fillets at the junctions (run k ends at corner idx[k + 1])
    nj = len(runs) if closed else len(runs) - 1
    for k in range(nj):
        c = idx[(k + 1) % len(idx)]
        r = corners.get(c, 0.0)
        if r > 0:
            k2 = (k + 1) % len(runs)
            A2, arc, B2 = _fillet(runs[k], runs[k2], r, step)
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


def capped_fillets():
    """[(outline, corner (u, h), tabled R, drawn R)] of every corner fillet the 0.45-of-run cap reduces (judges DR4-03):
    the outlines rebuilt from the table without the cache."""
    out = []
    for key, mirror in (("shell_half", True), ("insert_lower_half", True), ("grip_out", False), ("grip_in", False),
                        ("pad_out", False), ("pad_in", False), ("shield", False)):
        pts = tv(key)
        cs = {int(i): r for i, r in T().get(key + "_corners", ())}
        if mirror:
            pts, cs = mirror_half(pts, cs)
        del FILLET_CAPPED[:]
        smooth_outline(pts, cs, True)
        out += [(key,) + c for c in FILLET_CAPPED]
    for key, (a, b) in (("body", ("body_half", "body_in")),):
        pts, cs = join_halves(tv(a), tv(b), dict(T().get(a + "_corners", ())), dict(T().get(b + "_corners", ())))
        del FILLET_CAPPED[:]
        smooth_outline(pts, cs)
        out += [(key,) + c for c in FILLET_CAPPED]
    del FILLET_CAPPED[:]
    return out


# ============================================================================================ 2-D fields (judges DR2-01)
class Field2D:
    """EXACT signed distance (mm, negative inside) to a closed dense outline, or the unsigned distance to an open
    curve -- the outline being the curve-law polyline (0.05 mm chords: <= 0.0003 mm off the spline at R 1, <= 2.9 deg
    between neighbouring chords; rev M acceptance -- at 0.25 mm the chords' turns of 3-7 deg round the R 2-5 corners
    read as creases on the walls).

    Evaluation: a query point within EXACT_BAND (0.3 mm) of the outline gets the exact distance to the polyline's
    nearest segment (KD-tree over the vertices, the segments next to the k nearest vertices) with the sign of that
    segment's (or vertex's pseudo-) normal -- so the zero level IS the polyline, corners included.  Elsewhere the
    field is the C2 cubic B-spline of a `res` grid (rev M: bilinear before -- its gradient jumped at every cell edge,
    up to ~10 deg where a round read a tight corner's field) whose NODE values are the same exact distances (within
    NODE_BAND mm of the outline, which covers every blend / round radius the solids use; beyond it the nearest-vertex
    distance) -- the rounds and blends see a smooth field (rev J rasterised the outline and took a pixel distance
    transform: a 0.1 mm staircase, judges DR2-01); the two blended C2 over |d| EXACT_BAND - BLEND .. EXACT_BAND.  Node
    grids are disk-cached by the polyline's hash."""
    EXACT_BAND = 0.3
    BLEND = 0.1
    NODE_BAND = 16.0

    def __init__(self, P, res=0.1, margin=30.0, closed=True):
        from scipy.spatial import cKDTree
        P = np.asarray(P, float)
        if closed and np.linalg.norm(P[0] - P[-1]) < 1e-9:
            P = P[:-1]
        keep = np.r_[True, np.linalg.norm(np.diff(P, axis=0), axis=1) > 1e-7]
        P = P[keep]
        if closed and np.linalg.norm(P[0] - P[-1]) < 1e-7:
            P = P[:-1]
        self.P, self.closed = P, closed
        A = P
        B = np.roll(P, -1, 0) if closed else P[1:]
        if not closed:
            A = P[:-1]
        self.A, self.E = A, B - A
        self.L2 = np.maximum(np.einsum("ij,ij->i", self.E, self.E), 1e-18)
        nseg = len(A)
        if closed:
            area = 0.5 * float(np.sum(P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1]))
            o = 1.0 if area > 0 else -1.0                 # CCW: the outward normal is (dy, -dx)
            nrm = o * np.c_[self.E[:, 1], -self.E[:, 0]] / np.sqrt(self.L2)[:, None]
            self.Nseg = nrm
            vn = nrm + np.roll(nrm, 1, 0)                 # vertex i: segments i - 1 and i
            self.Nvtx = vn / np.maximum(np.linalg.norm(vn, axis=1), 1e-12)[:, None]
        self.nseg = nseg
        self.tree = cKDTree(P)
        self.res = res
        self.band = min(self.NODE_BAND, margin)
        self.lo = P.min(0) - margin
        hi = P.max(0) + margin
        W = int(math.ceil((hi[0] - self.lo[0]) / res)) + 1
        H = int(math.ceil((hi[1] - self.lo[1]) / res)) + 1
        from scipy import ndimage as ndi
        g = _node_grid(self, W, H)
        self.shape = g.shape
        self.c = ndi.spline_filter(g, order=3, mode="nearest")    # rev M: C2 cubic B-spline of the node values

    # ---- exact distance (vectorised)
    def exact(self, X, Y, k=6):
        Q = np.c_[np.ravel(X), np.ravel(Y)]
        if not len(Q):
            return np.zeros(np.shape(X))
        k = min(k, len(self.P))
        _, vi = self.tree.query(Q, k=k, workers=2)
        vi = np.atleast_2d(vi).reshape(len(Q), k)
        n = len(self.P)
        if self.closed:
            cand = np.concatenate([vi, (vi - 1) % n], axis=1)
        else:
            cand = np.concatenate([np.minimum(vi, self.nseg - 1), np.clip(vi - 1, 0, self.nseg - 1)], axis=1)
        a = self.A[cand]                                   # (N, 2k, 2)
        e = self.E[cand]
        w = Q[:, None, :] - a
        t = np.clip(np.einsum("ijk,ijk->ij", w, e) / self.L2[cand], 0.0, 1.0)
        dvec = w - t[..., None] * e
        d2 = np.einsum("ijk,ijk->ij", dvec, dvec)
        j = np.argmin(d2, axis=1)
        r = np.arange(len(Q))
        d = np.sqrt(d2[r, j])
        if not self.closed:
            return d.reshape(np.shape(X))
        seg = cand[r, j]
        tj = t[r, j]
        nn = self.Nseg[seg].copy()
        at0 = tj <= 1e-9
        at1 = tj >= 1.0 - 1e-9
        nn[at0] = self.Nvtx[seg[at0]]
        nn[at1] = self.Nvtx[(seg[at1] + 1) % n]
        s = np.sign(np.einsum("ij,ij->i", dvec[r, j], nn))
        s[s == 0] = 1.0
        return (s * d).reshape(np.shape(X))

    def __call__(self, U, V):
        from scipy import ndimage as ndi
        U, V = np.asarray(U, float), np.asarray(V, float)
        x = (U - self.lo[0]) / self.res
        y = (V - self.lo[1]) / self.res
        xc = np.clip(x, 0, self.shape[1] - 1)
        yc = np.clip(y, 0, self.shape[0] - 1)
        g = ndi.map_coordinates(self.c, [yc.ravel(), xc.ravel()], order=3, mode="nearest",
                                prefilter=False).reshape(U.shape)
        out = np.hypot(x - xc, y - yc) * self.res
        g = g + out
        near = np.abs(g) < self.EXACT_BAND
        if near.any():
            g = g.copy()
            gn = g[near]
            w = smootherstep(np.abs(gn), self.EXACT_BAND - self.BLEND, self.EXACT_BAND)
            g[near] = (1.0 - w) * self.exact(U[near], V[near]) + w * gn
        return g


def _node_grid(F, W, H):
    """The exact node values of Field2D F (W x H nodes from F.lo every F.res), disk-cached by the polyline."""
    import hashlib
    from pathlib import Path
    from scipy import ndimage as ndi
    from PIL import Image, ImageDraw
    h = hashlib.sha1(np.ascontiguousarray(F.P).tobytes())
    h.update(repr((F.closed, F.res, W, H, tuple(np.round(F.lo, 9)), F.band, "exact-v1")).encode())
    f = Path(__file__).resolve().parents[1] / "out" / "tmp" / "yoke_geom_cache" / "fields" / (h.hexdigest()[:24] + ".npy")
    if f.exists():
        try:
            return np.load(f).astype(float)
        except Exception:                                    # noqa: BLE001
            pass
    res = F.res
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    q = [((x - F.lo[0]) / res, (y - F.lo[1]) / res) for x, y in F.P]
    if F.closed:
        d.polygon(q, fill=255)
    else:
        d.line(q, fill=255, width=1)
    m = np.asarray(img) > 127
    if F.closed:
        approx = np.where(m, -ndi.distance_transform_edt(m), ndi.distance_transform_edt(~m)) * res
    else:
        approx = ndi.distance_transform_edt(~m) * res
    g = approx.copy()
    band = np.abs(approx) < F.band
    jj, ii = np.nonzero(band)
    X = F.lo[0] + ii * res
    Y = F.lo[1] + jj * res
    for s in range(0, len(X), 400000):
        g[jj[s:s + 400000], ii[s:s + 400000]] = F.exact(X[s:s + 400000], Y[s:s + 400000])
    far = ~band
    if far.any():                                            # nearest-vertex distance, raster sign
        jf, i_f = np.nonzero(far)
        dv, _ = F.tree.query(np.c_[F.lo[0] + i_f * res, F.lo[1] + jf * res], k=1, workers=2)
        g[jf, i_f] = np.sign(approx[jf, i_f]) * dv if F.closed else dv
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_name(f.stem + ".tmp.npy")
        np.save(tmp, g.astype(np.float32))
        tmp.replace(f)
    except OSError:
        pass
    return g


def field(name, P=None, closed=True, res=0.1, margin=30.0):
    """Cached Field2D of a named outline (P given the first time, or the table entry of that name)."""
    if P is None:
        P = outline(name)
    P = np.asarray(P, float)
    import hashlib
    key = ("field", name, res, closed, margin, hashlib.sha1(np.ascontiguousarray(P).tobytes()).hexdigest()[:16])
    if key not in _CACHE:
        _CACHE[key] = Field2D(P, res=res, closed=closed, margin=margin)
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


def rmin(a, b, r):
    """Union of two fields, the concave edge filled with a true round of radius r (the dual of rmax)."""
    return -rmax(-np.asarray(a, float), -np.asarray(b, float), r)


def smoothstep(x, e0, e1):
    t = np.clip((np.asarray(x, float) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def smootherstep(x, e0, e1):
    """C2 step (6t^5 - 15t^4 + 10t^3)."""
    t = np.clip((np.asarray(x, float) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * t * (t * (6.0 * t - 15.0) + 10.0)


def rmin_ang(a, b, r, ca):
    """Union of two fields with a ROLLING-BALL round of radius r for surfaces meeting at any angle (rev M, judges DR4-01
    / 02): ca = cos of the angle between the two fields' outward normals at the point.  The ball (centre where a = b =
    r) touches both surfaces; inside the wedge it spans -- (a - r, b - r) mapped through the inverse Gram matrix of the
    two normals -- the field is r - |P - C|, elsewhere min(a, b).  For orthogonal normals (ca = 0) this is rmin; for
    nearly tangent / flush surfaces (ca -> 1) the wedge closes and the union is min(a, b) -- rmin's circular blend
    stood r (1 - 1/sqrt 2) proud there (0.9 mm at R 3: the flush web over the outboard grip's frame, rev L)."""
    a, b, ca = (np.asarray(x, float) for x in (a, b, ca))
    r = np.asarray(r, float)
    c = _ang_map(ca)                     # acute corners (ca < 0) as orthogonal: the wedge then stays inside a, b < r
    da, db = a - r, b - r
    s = 1.0 - c * c
    alpha = -(da - c * db) / s
    beta = -(db - c * da) / s
    q = np.maximum((da * da + db * db - 2.0 * c * da * db) / s, 0.0)
    inside = (alpha >= 0.0) & (beta >= 0.0)
    return np.where(inside, r - np.sqrt(q), np.minimum(a, b))


ANG_EASE = 0.2


def _ang_map(ca):
    """The cosine rmin_ang works with: ca itself above ANG_EASE, 0 below -ANG_EASE (an acute corner is rounded as a
    right angle, so the ball's wedge stays inside a, b < r), a C2 quartic between (x0 psi((x + x0) / 2 x0), psi = 2t^3 -
    t^4); kept below 1 only against the division (two flush surfaces: the wedge closes, the union is min(a, b);
    a cap at 0.995 left a 0.003 mm ridge there, a blend to min() over 0.98-0.995 an 11 deg crease where two rounds
    meet at a shallow angle).  Rev M acceptance: a plain clip at 0 put a crease in the round wherever the two
    normals passed through 90 deg (the outboard head's join to its prism at h ~68: 18 deg)."""
    x0 = ANG_EASE
    x = np.asarray(ca, float)
    t = np.clip((x + x0) / (2.0 * x0), 0.0, 1.0)
    c = np.where(x >= x0, x, x0 * t ** 3 * (2.0 - t))
    return np.minimum(c, 1.0 - 1e-9)


def _unit_grad(fn, U, H, A, e=0.01):
    """Unit gradient (u, h, a) of fn at the points by central differences."""
    g = np.stack([fn(U + e, H, A) - fn(U - e, H, A), fn(U, H + e, A) - fn(U, H - e, A),
                  fn(U, H, A + e) - fn(U, H, A - e)], -1)
    return g / np.maximum(np.linalg.norm(g, axis=-1, keepdims=True), 1e-12)


def join(fa, fb, U, H, A, r):
    """Union of the solids fa, fb (field functions of (U, H, A)) with the rolling-ball round rmin_ang of radius r: the
    normals (central differences) only where both fields are within r -- elsewhere it is min(a, b)."""
    U, H, A = (np.asarray(x, float) for x in (U, H, A))
    a, b = fa(U, H, A), fb(U, H, A)
    m = (a < r) & (b < r)
    out = np.minimum(a, b)
    if m.any():
        Um, Hm, Am = U[m], H[m], A[m]
        ca = np.sum(_unit_grad(fa, Um, Hm, Am) * _unit_grad(fb, Um, Hm, Am), -1)
        out = out.copy()
        out[m] = rmin_ang(a[m], b[m], r, ca)
    return out


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
    return field(name, np.asarray(P, float), closed=False, res=0.1, margin=4.0)


def _groove_curves():
    """Open curves of the cover's parting grooves: the upper insert's sides (both), the step, the lower insert."""
    key = ("grooves", id(T()["insert_side"]), id(T()["step"]), id(T()["insert_lower_half"]))
    if key in _CACHE:
        return _CACHE[key]
    side = _spline_run(tv("insert_side"))
    st = tv("step")
    step = np.vstack([st[1] * [-1, 1], st[0], st[1]])
    out = dict(side_r=side, side_l=side * [-1, 1], step=step, lower=np.vstack([insert_lower_outline(),
                                                                                insert_lower_outline()[:1]]))
    for k, P in badge_curves().items():
        out[k] = P
    _CACHE[key] = out
    return out


def badge_curves():
    """The badge's groove curves (front view): 'badge' its outline (closed), 'badge_border' the inner border,
    'badge_l0'.. the speed lines (three per wing) -- the same geometry interior.yoke_front_mm draws (H detail)."""
    D = T()
    (bu0, bh0), (bu1, bh1) = D["badge"]
    z1, z2, z3, u0, off = (float(x) for x in D["badge_lines"])
    ang = math.atan2(bu0 - bu1, bh0 - bh1)
    du = off / math.cos(ang)
    bt, bb = bh0 - off, bh1 + off

    def end_u(z):
        return bu1 + (z - bh1) * (bu0 - bu1) / (bh0 - bh1) - du
    badge = np.array([(-bu0, bh0), (bu0, bh0), (bu1, bh1), (-bu1, bh1), (-bu0, bh0)])
    border = np.array([(-end_u(bt), bt), (end_u(bt), bt), (end_u(bb), bb), (-end_u(bb), bb), (-end_u(bt), bt)])
    out = dict(badge=_densify(badge), badge_border=_densify(border))
    k = 0
    for z in (z1, z2, z3):
        for sg in (-1, 1):
            out[f"badge_l{k}"] = _densify(np.array([(sg * u0, z), (sg * end_u(z), z)]))
            k += 1
    return out


def _densify(P, step=0.2):
    P = np.asarray(P, float)
    out = [P[:1]]
    for a, b in zip(P[:-1], P[1:]):
        n = max(1, int(math.ceil(np.linalg.norm(b - a) / step)))
        out.append(a + (b - a) * np.linspace(0, 1, n + 1)[1:, None])
    return np.vstack(out)


def crown_bevel(U, H, soft=0.0):
    """How far (mm) the insert's top leans forward of the face above the crown's soft break (crown: h, angle,
    blend R): 0 below, a C1 blend of radius crown[4] into the bevel (judges FID2-10); the cover's back and the
    body's aft surface follow it (the cover stays cover_t thick).  The bevel stops at the insert's groove (0.5 outside
    its outline); soft > 0 fades it out smoothly over that many mm instead -- for the body's TOP PLANE, anchored on the
    aft surface along the top line (rev M acceptance: the step, ~0.02 mm where the top line crosses the groove at
    |u| ~29, creased the top-to-front R 8 on the body's forward face)."""
    U, H = np.asarray(U, float), np.asarray(H, float)
    hc, beta, _, _, rb = (float(x) for x in T()["crown"][:5])
    ins = field("insert_upper", insert_upper_outline())(U, H)
    k = math.tan(math.radians(beta))
    w = max(rb * math.tan(0.5 * math.radians(beta)), 1e-6)      # the blend's tangent length
    x = H - hc
    ramp = np.where(x <= -w, 0.0, np.where(x >= w, x, (x + w) ** 2 / (4.0 * w)))
    if soft > 0.0:
        return ramp * k * (1.0 - smootherstep(ins, 0.5, 0.5 + soft))
    return np.where(ins < 0.5, ramp * k, 0.0)


def cover_top(U, H):
    """a of the cover's aft surface at (u, h): the face, the crown bevel above its soft break (insert only) and the
    top land along the top edges (YOKE_DESIGN crown)."""
    U, H = np.asarray(U, float), np.asarray(H, float)
    hc, beta, land_d, land_w, rb = (float(x) for x in T()["crown"][:5])
    a = face_a(H)
    bev = crown_bevel(U, H)
    d2 = field("shell", shell_outline())(U, H)
    gh = (field("shell", shell_outline())(U, H + 0.2) - field("shell", shell_outline())(U, H - 0.2)) / 0.4
    up = smoothstep(gh, 0.35, 0.6)                                   # top edges: outward normal pointing up
    land = up * land_d * smoothstep(d2, -land_w, 0.0)                 # C1 at both edges (DR2-05)
    return a - bev - land


def cover(U, H, A):
    """Signed distance of the white cover + inserts (mm)."""
    U, H, A = (np.asarray(x, float) for x in (U, H, A))
    E = T()["edges"]
    d2 = field("shell", shell_outline())(U, H)
    top = cover_top(U, H)
    aft = A - top
    fwd = (face_a(H) - crown_bevel(U, H) - float(T()["cover_t"])) - A
    # edge radius: R 1 perimeter, R 2 along the arms' lower edges, R 3 under the foot
    Fs = field("shell", shell_outline())
    gh = (Fs(U, H + 0.2) - Fs(U, H - 0.2)) / 0.4                       # the outline's normal: down = lower edges
    arm_lower = smoothstep(np.abs(U), 36.0, 40.0) * smoothstep(-gh, 0.25, 0.55)   # C1 (rev J: a boolean switch)
    r = float(E[0]) + (float(E[1]) - float(E[0])) * arm_lower + (float(E[2]) - float(E[0])) * smoothstep(-H, 48.0, 53.0)
    s = np.maximum(rmax(d2, aft, r), rmax(d2, fwd, 0.5))
    # parting grooves (V, width w, depth g) cut from the aft surface
    gw = T()["grooves"]
    z = top - A                                                       # depth below the aft surface
    bg, bw = (float(x) for x in T()["badge_relief"][:2])
    gc = _groove_curves()
    for nm, (w, g) in [("side_r", gw[0]), ("side_l", gw[0]), ("step", gw[1]), ("lower", gw[2])] + \
            [(k, (bw, bg)) for k in gc if k.startswith("badge")]:
        dc = _curve_dist("groove_" + nm, gc[nm])(U, H)
        v = (dc - 0.5 * w * (1.0 - z / g)) * (g / math.hypot(g, 0.5 * w))
        s = np.maximum(s, -v)
    # the TCS bezel's seat: a pocket of the bezel's outer radius, tcs_seat deep (the bezel fills it)
    c, nrm = tcs_axis()
    P = np.stack([U, H, A], -1) - c
    zt = P @ nrm
    rt = np.linalg.norm(P - zt[..., None] * nrm, axis=-1)
    pocket = np.maximum(rt - 0.5 * float(T()["tcs"][2]), -float(T()["tcs_seat"]) - zt)
    return np.maximum(s, -pocket)


def cover_part(U, H):
    """'insert_up' / 'insert_lo' / 'cover' for points of the cover by their front-view position."""
    iu = field("insert_upper", insert_upper_outline())(U, H) < 0
    il = field("insert_lower", insert_lower_outline())(U, H) < 0
    return np.where(iu, 1, np.where(il, 2, 0))


# ============================================================================================ grips
def grip_axis_u(h):
    (ub, hb), (ut, ht) = T()["grip_axis"]
    return ub + (np.asarray(h, float) - hb) * (ut - ub) / (ht - hb)


def _gsel(key, g):
    """Per-grip value of a table entry: one value for both grips, or (outboard, inboard)."""
    v = np.atleast_1d(np.asarray(T()[key], float))
    return float(v[0] if (g == "out" or len(v) == 1) else v[1])


def grip_a0(g):
    """(h0, a0): grip g's aft plane passes a = a0 at height h0 on the grip axis (grip_a0 = (h0, outboard, inboard))."""
    v = np.asarray(T()["grip_a0"], float)
    return float(v[0]), float(v[1] if (g == "out" or len(v) == 2) else v[2])


def grip_frame(g):
    """Aft-face plane of grip g ('out' / 'in', own sense): dict(p0 (u, h, a), n unit normal (u, h, a) pointing aft-out,
    tt = tan toe, tr = tan rake) -- rake, toe and a0 per grip (rev K)."""
    h0, a0 = grip_a0(g)
    tt = math.tan(math.radians(_gsel("grip_toe", g)))
    tr = math.tan(math.radians(_gsel("grip_rake", g)))
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
    """Grip depth normal to the aft face at plane height h: a monotone C1 PCHIP through the grip_depth rows (judges
    DR2-03: rev J interpolated linearly -- 2-5 deg kinks in both forward faces)."""
    from scipy.interpolate import PchipInterpolator
    k = tv("grip_depth")
    key = ("depth", g, k.tobytes())
    if key not in _CACHE:
        _CACHE[key] = (PchipInterpolator(k[:, 0], k[:, 1 if g == "out" else 2]), float(k[0, 0]), float(k[-1, 0]))
    sp, h0, h1 = _CACHE[key]
    return sp(np.clip(np.asarray(h, float), h0, h1))


def grip_halfwidth(g):
    """(hs, m): the inscribed half-width of grip g's aft-face outline per plane height (max of -d over the row),
    floored at the bottom corners' radius: the forward-edge radius is capped at grip_edges[2] x m (DR2-03)."""
    Q = grip_outline(g)
    key = ("ghw", g, Q.tobytes())
    if key not in _CACHE:
        F = field("grip_" + g, Q)
        hs = np.arange(Q[:, 1].min() - 2.0, Q[:, 1].max() + 2.01, 0.5)
        us = np.arange(Q[:, 0].min() - 1.0, Q[:, 0].max() + 1.01, 0.1)
        UU, HH = np.meshgrid(us, hs)
        m = np.maximum(-F(UU, HH).min(axis=1), 0.0)
        cs = [r for _, r in T().get("grip_" + g + "_corners", ())]
        _CACHE[key] = (hs, np.maximum(m, min(cs) if cs else 2.0))
    return _CACHE[key]


def smin3(a, b, k):
    """C2 smooth minimum (cubic): min(a, b) less k/6 x max(k - |a - b|, 0)^3 / k^3."""
    m = np.maximum(k - np.abs(np.asarray(a, float) - b), 0.0) / k
    return np.minimum(a, b) - m ** 3 * k / 6.0


def fwd_radius(hf, g):
    """Forward-edge radius of grip g at plane height hf: grip_edges[1], capped at grip_edges[2] x the outline's
    inscribed half-width there, so the rounds of the two forward edges never meet in a ridge (DR2-03).  Rev M
    acceptance: the cap is C2 -- the half-width table (0.5 mm rows, a max over each row, floored) Gaussian-smoothed
    over 1 mm and read through a cubic spline, then a cubic soft minimum with R grip_edges[1] over 2 mm (the
    piecewise-linear table and the hard minimum put a 5-7 deg crease into the forward round above the heel)."""
    E = T()["grip_edges"]
    rf, frac = float(E[1]), float(E[2])
    key = ("fwdr", g, id(T()["grip_edges"]))
    if key not in _CACHE:
        from scipy.interpolate import CubicSpline
        from scipy.ndimage import gaussian_filter1d
        hs, m = grip_halfwidth(g)
        _CACHE[key] = CubicSpline(hs, gaussian_filter1d(np.asarray(m, float), 2.0, mode="nearest"))
    cap = frac * _CACHE[key](np.clip(np.asarray(hf, float), *_hs_range(g)))
    return smin3(rf, cap, 2.0)


def _hs_range(g):
    hs = grip_halfwidth(g)[0]
    return float(hs[0]), float(hs[-1])


def _to_plane(U, H, A, g):
    """(z, uf, hf): signed distance of the points from grip g's aft plane (+ aft), and the front-view coordinates of
    their foot on the plane along the grip's WALL direction (grip_walls: rev K -- the walls run fore-aft, along the
    column / pull axis, so the foot is the point's own (u, h); rev J extruded them along the toed aft normal, which put
    the forward face 6-8 mm into the hand slot in the face-on photos, judges FID2-02)."""
    f = grip_frame(g)
    n = f["n"]
    P = np.stack([U, H, A], -1)
    z = (P - f["p0"]) @ n
    w = _gsel("grip_walls", g)
    if w >= 1.0:
        return z, P[..., 0], P[..., 1]
    e = (1.0 - w) * n + w * np.array([0.0, 0.0, 1.0])
    e /= np.linalg.norm(e)
    F = P - (z / float(np.dot(n, e)))[..., None] * e
    return z, F[..., 0], F[..., 1]


def heel_lift(hf, g):
    """The heel lip's height above the frame plane at plane height hf: 0 at the pad's bottom, rising C2 (smootherstep;
    rev M, judges DR4-07: the C1 smoothstep left a curvature step along the pad's bottom) over the upper 60 % of the
    heel to heel[1] proud, held to the grip's bottom edge (rolled R heel[2] there)."""
    hl, proud = (float(x) for x in T()["heel"][:2])
    pb = float(np.min(pad_outline(g)[:, 1]))
    t = np.clip((pb - np.asarray(hf, float)) / hl, 0.0, 1.0)
    return proud * smootherstep(t, 0.0, 0.6)


class SoftInside:
    """A smoothed inward distance of a closed outline (pad crowns, judges DR2-03): the exact inside distance on a
    0.2 mm grid, Gaussian-blurred (sigma pad_section[6] mm) so the crown has no crease along the medial axis (the exact
    distance's ridge from every corner), interpolated bilinearly; disk-cached with the node grids."""

    def __init__(self, P, sigma, res=0.2, margin=4.0):
        from scipy import ndimage as ndi
        F = field("soft_src", P, res=0.1)
        lo = P.min(0) - margin
        hi = P.max(0) + margin
        xs = np.arange(lo[0], hi[0] + res, res)
        ys = np.arange(lo[1], hi[1] + res, res)
        X, Y = np.meshgrid(xs, ys)
        d = np.maximum(-F(X, Y), 0.0)
        self.g = ndi.gaussian_filter(d, sigma / res, mode="nearest")
        self.lo, self.res = lo, res

    def __call__(self, U, V):
        from scipy import ndimage as ndi
        U, V = np.asarray(U, float), np.asarray(V, float)
        x = np.clip((U - self.lo[0]) / self.res, 0, self.g.shape[1] - 1)
        y = np.clip((V - self.lo[1]) / self.res, 0, self.g.shape[0] - 1)
        return ndi.map_coordinates(self.g, [y.ravel(), x.ravel()], order=1, mode="nearest").reshape(U.shape)


def pad_soft(g):
    P = pad_outline(g)
    sig = float(T()["pad_section"][6])
    key = ("padsoft", g, sig, P.tobytes())
    if key not in _CACHE:
        _CACHE[key] = SoftInside(P, sig)
    return _CACHE[key]


def _leather(uf, hf, g):
    """The leather's height (along the aft normal) inside the pad: -rec at its edge, crowned to cen over wc, from the
    smoothed inward distance (no medial-axis creases)."""
    rec, cen, wc, bead, gw = (float(x) for x in T()["pad_section"][:5])
    s0 = gw + 2.0 * bead
    return -rec + (rec + cen) * smoothstep(pad_soft(g)(uf, hf), s0, s0 + wc)


def grip_surface_z(uf, hf, g):
    """Offset (mm, along the aft normal) of the grip's aft surface from its plane at the plane point (uf, hf), for
    drawing: 0 on the frame, the leather (pad_section) inside the pad outline, the heel lip below the pad."""
    rec, cen, wc, bead, gw, gd = (float(x) for x in T()["pad_section"][:6])
    dp = field("pad_" + g, pad_outline(g))(uf, hf)
    s = -dp
    s0 = gw + 2.0 * bead
    leather = _leather(uf, hf, g)
    beadz = -rec + bead * np.sqrt(np.clip(1.0 - ((s - gw - bead) / bead) ** 2, 0.0, 1.0))
    z = np.where(s < gw, -rec - gd, np.where(s < s0, beadz, leather))
    return np.where(dp < 0.0, z, 0.0) + heel_lift(hf, g)


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


def face_plane_a(U, H):
    """a of the outboard head's round-face plane at the front-view point (u, h)."""
    c, n = head_out_face()
    return c[2] - (n[0] * (np.asarray(U, float) - c[0]) + n[1] * (np.asarray(H, float) - c[1])) / n[2]


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
    """The inboard head's shaping field: the shield facet plane and, round the shield's top and sides, a fall-off
    surface at head_in[4] deg to it (its directrix: shield_directrix, the shield outline continued straight down from
    its widest points); the facet edge rounded R shield_edge[0] (rev L)."""
    c, n = head_in_face()
    eu, ev = _facet_frame(c, n)
    P = np.stack([U, H, A], -1) - c
    zf = P @ n
    x, y = P @ eu, P @ ev
    r_fo = float(T()["shield_edge"][0])
    ds = field("shield_dir", shield_directrix())(x, y)
    chi = math.radians(float(T()["head_in"][4]))
    return rmax(zf, zf * math.cos(chi) + ds * math.sin(chi), r_fo)


def shield_directrix():
    """The fall-off's DIRECTRIX in the facet plane (rev M): ONE closed curve -- the shield outline over its top between
    its widest points, continued straight down from them (their tangents are vertical: G1, no corner) to y -80.  Rev L
    took the union of the shield and a rectangle up to y 0, whose top corners stood 1.5 outside the shield's converging
    sides (a 25 deg crease down the fall-off at |x| 15.3) beside a notch blended R 4."""
    key = ("shield_dir", id(T()["shield"]))
    if key not in _CACHE:
        S = shield_outline()
        i0, i1 = int(np.argmin(S[:, 0])), int(np.argmax(S[:, 0]))
        n = len(S)
        fw = [S[(i1 + k) % n] for k in range((i0 - i1) % n + 1)]          # i1 -> i0 one way round
        bw = [S[(i0 + k) % n] for k in range((i1 - i0) % n + 1)][::-1]    # i1 -> i0 the other way
        top = np.array(fw if np.mean([p[1] for p in fw]) > np.mean([p[1] for p in bw]) else bw)
        P = np.vstack([top, [(S[i0, 0], -80.0), (S[i1, 0], -80.0)], top[:1]])
        _CACHE[key] = smooth_dense(P, curve_step())[:-1]     # dense straight runs too: the node grid's far values
    return _CACHE[key]                                         # are nearest-VERTEX distances (judges' ridge row)


def _head_chamfer(U, H, A):
    """Field of the region forward of / above the outboard head's lower chamfer: a plane through the round face's
    lower edge falling back to the grip's aft plane at head_out[8] deg (negative = inside)."""
    c, n = head_out_face()
    eu, ev = _facet_frame(c, n)
    R = 0.5 * float(T()["head_out"][2])
    le = c - R * ev                                                   # the face's lowest point
    ang = math.radians(float(T()["head_chamfer"]))
    nn = np.array([0.0, -math.sin(ang), math.cos(ang)])
    P = np.stack([U, H, A], -1) - le
    return P @ nn


def _trim_face_grooves(U, H, A):
    """V-grooves cut into the round trim face (trim_grooves): the legend ring's outer edge (a circle at trim[2] / 2)
    and the two chords bounding the rocker slot between the lunes; negative = inside the groove."""
    c, n = head_out_face()
    eu, ev = _facet_frame(c, n)
    w, g = (float(x) for x in T()["trim_grooves"][:2])
    od = float(T()["trim"][2])
    lune = float(T()["trim_lunes"][0])
    P = np.stack([U, H, A], -1) - c
    zf, x, y = P @ n, P @ eu, P @ ev
    rho = np.hypot(x, y)
    yl = 0.5 * od - lune
    ring = np.abs(rho - 0.5 * od)
    chord = np.where(rho < 0.5 * od - 0.6, np.abs(np.abs(y) - yl), 1e3)
    dc = np.minimum(ring, chord)
    return (dc - 0.5 * w * (1.0 + zf / g)) * (g / math.hypot(g, 0.5 * w))


def grip(U, H, A, g):
    """Signed distance of grip g (own sense), its pad pocket, groove and bead cut / added (pad_finish)."""
    U, H, A = (np.asarray(x, float) for x in (U, H, A))
    return pad_finish(grip_solid(U, H, A, g), U, H, A, g)


def pad_finish(f, U, H, A, g):
    """Cut grip g's pad pocket (the pad outline down to the leather) and the groove along the frame's inner wall out of
    the field f, and add the bead on the leather's edge (pad_section).  Rev M (judges DR4-01): applied to the joined
    MOULDING (body + grips) after the body-grip round, so neither the body nor the round can fill the pocket -- rev L
    cut the pocket into the grip alone and the body's flush web over the pad's slot-side upper corner filled it."""
    rec, cen, wc, bead, gw, gd = (float(x) for x in T()["pad_section"][:6])
    z, uf, hf = _to_plane(U, H, A, g)
    dp = field("pad_" + g, pad_outline(g))(uf, hf)
    s = -dp
    leather = _leather(uf, hf, g)
    pocket = np.maximum(dp, leather - z)                              # inside the pad, above the leather
    groove = np.maximum(np.maximum(dp, -gw - dp), (-rec - gd) - z)    # 0 < s < gw, above the groove floor
    f = np.maximum(f, np.maximum(-pocket, -groove))
    tube = np.hypot(s - (gw + bead), np.maximum(z + rec, 0.0)) - bead  # the bead: a half-round on the leather edge
    tube = np.where(z >= -rec - 0.5, tube, np.maximum(tube, -rec - 0.5 - z))
    return np.minimum(f, np.where(dp < 0.0, tube, 1e3))


def grip_solid(U, H, A, g):
    """Signed distance of grip g (own sense: u > 0 away from the yoke centreline), incl. its head and heel, WITHOUT the
    pad pocket (pad_finish cuts it).  Rev M (judges DR4-02): the head and the prism SHARE the walls (outline G) and the
    forward face -- the AFT SIDE is built first (the prism's trimmed aft side joined to the head's aft shape by the
    concave round R r_u: _grip_parts), then cut by the walls and the forward face with their edge rounds (aft edge R
    grip_edges[0] -> the heel's R, in the head zone R r_w; forward edge fwd_radius -> R r_hf over the head).  Rev L
    joined two complete solids that shared their walls and forward face: the circular round stood r_u (1 - 1/sqrt 2)
    proud along every shared face and its exterior field had a ridge 1 mm out -- read by the body-grip R 3 as the crease
    under the trim head."""
    U, H, A = (np.asarray(x, float) for x in (U, H, A))
    aft, d2, fwd, ra, rf = _grip_parts(U, H, A, g)
    # the aft side and the forward face meet only where the head's aft shape wraps forward over its top: there R r_hf
    # (rev M acceptance: a plain max() of the two cut pieces left that edge sharp across the outboard head's front);
    # elsewhere they lie the grip's depth apart and the round is inactive.  The walls' edge radius follows whichever
    # face is nearer (aft R ra / forward R rf), blended C2 where the two are within 10 mm of each other -- only there.
    r_hf = float(T()["head_zone"][0 if g == "out" else 1][7])
    side = rmax(aft, fwd, r_hf)
    wf = smootherstep(aft - fwd, 10.0, -10.0)
    return rmax(d2, side, ra + (rf - ra) * wf)


def trim_field(g):
    """Field2D of the head zone's TRIMMING CURVE of grip g in the plane (s, y): s = the head's shaping field (+ outside
    the head), y = (hz - hf) x the plane-height scale (mm below hz).  Kept (negative) side: s < s_b(y), s_b = -kh above
    hz, bending C1 over y in [-wr, wr] (a parabola, its tightest radius rb at the start, wr = rb x draft / 2) into the
    draft line s_b = -kh + draft y below.  Rev M (judges DR4-02): the EXACT 2-D distance to that curve -- rev L divided
    the offset by a piecewise-linear gradient length (a kink in every level but zero, which the R 1.5 cut round read)
    and bent it over R 1.5 only."""
    hz, kh, draft = (float(x) for x in T()["head_zone"][0 if g == "out" else 1][:3])
    rb = float(T()["head_zone"][0 if g == "out" else 1][10])
    wr = 0.5 * rb * draft
    Y = wr + 25.0
    y = np.r_[np.linspace(-Y, -wr, 60), np.linspace(-wr, wr, max(40, int(2 * wr / 0.05)))[1:-1], np.linspace(wr, Y, 60)]
    sb = -kh + draft * np.where(y <= -wr, 0.0, np.where(y >= wr, y, (y + wr) ** 2 / (4.0 * wr)))
    P = np.r_[np.c_[sb, y][::-1], [(-40.0, -Y), (-40.0, Y)]]
    P = smooth_dense(P)
    return field("trim_" + g, P, res=0.05, margin=12.0), (hz, kh, draft, wr, Y)


def smooth_dense(P, step=0.1):
    """Densify a polyline to <= step chords (the curve's own samples kept)."""
    return _densify(np.asarray(P, float), step)


def _trim_value(cut, hf, g, sc):
    """The trimming field (+ = cut away) at shaping-field value `cut` and plane height hf (trim_field; outside its grid
    the analytic distance to the vertical / draft line)."""
    F, (hz, kh, draft, wr, Y) = trim_field(g)
    y = (hz - hf) * sc
    v = F(cut, y)
    above = y < -Y + 2.0
    below = y > Y - 2.0
    v = np.where(above, cut + kh, v)
    v = np.where(below, (cut + kh - draft * y) / math.sqrt(1.0 + draft * draft), v)
    return v


def _trim3(U, H, A, g):
    """The head zone's trimming field of grip g at 3-D points (own sense), as composed: trim_field at (shaping field,
    plane height)."""
    cut = (_head_out if g == "out" else _head_in)(U, H, A)
    hf = _to_plane(U, H, A, g)[2]
    return _trim_value(cut, hf, g, _hf_scale(g))


def _grip_parts(U, H, A, g, split=False):
    """(aft, d2, fwd, r_aft, r_fwd) of grip g (own sense) -- split: (prism aft side, head) instead -- the AFT-SIDE field, the walls (outline G), the forward face
    and the two edge radii (grip_solid intersects them).
    PRISM aft side: the raked / toed aft plane + heel lip, trimmed in the HEAD ZONE (head_zone; rev L judges DR3-01 /
    02, rev M DR4-02): above the plane height hz the prism is cut kh inside the head's shaping surface (outboard: the
    round face on its flared near-cylinder; inboard: the shield facet with its 45 deg fall-off), that trimming surface
    drafted outward `draft` mm per mm below hz, its start bent C1 with the tightest radius rb (trim_field, an exact 2-D
    distance), the cut edge R r_t.  HEAD aft shape: the shaping surface x the lower chamfer (outboard, R r_ch), its floor
    the plane height h_hb (R r_hb); the trim face's grooves cut in it.  Aft side = prism aft side + head, joined R r_u
    (kh >= r_u: the round never reaches the face / facet).  Edge radii: aft R grip_edges[0] growing to the heel's R,
    easing to the head's R r_w over hz -+ 3; forward fwd_radius easing to R r_hf above h_hb (smoothstep over 6)."""
    U, H, A = (np.asarray(x, float) for x in (U, H, A))
    z, uf, hf = _to_plane(U, H, A, g)
    d2 = field("grip_" + g, grip_outline(g))(uf, hf)
    ra = float(T()["grip_edges"][0])
    r_heel = float(T()["heel"][2])
    pb = float(np.min(pad_outline(g)[:, 1]))
    hz, kh, draft, r_t, h_hb, r_hb, r_ch, r_hf, r_w, r_u = (float(x) for x in T()["head_zone"][0 if g == "out" else 1][:10])
    ra_h = ra + (r_heel - ra) * smoothstep((pb - hf) / float(T()["heel"][0]), 0.3, 0.8)
    ra_h = ra_h + (r_w - ra_h) * smoothstep(hf, hz - 3.0, hz + 3.0)
    rf = fwd_radius(hf, g)
    rf = rf + (r_hf - rf) * smoothstep(hf, h_hb, h_hb + 6.0)
    fwd = -z - _depth(hf, g)
    sc = _hf_scale(g)
    if g == "out":
        cut = _head_out(U, H, A)
        head = rmax(cut, _head_chamfer(U, H, A), r_ch)
    else:
        cut = _head_in(U, H, A)
        head = cut
    prism_aft = rmax(z - heel_lift(hf, g), _trim_value(cut, hf, g, sc), r_t)
    head = rmax(head, (h_hb - hf) * sc, r_hb)
    if g == "out":
        head = np.maximum(head, -_trim_face_grooves(U, H, A))
    if split:
        return prism_aft, head
    return _aft_join(prism_aft, head, r_u, U, H, A, g), d2, fwd, ra_h, rf


def _aft_join(pa, hd, r_u, U, H, A, g):
    """The prism's aft side and the head joined by the rolling-ball round R r_u (rmin_ang; rev M): where the head's
    aft shape runs nearly parallel to the frame inside its reach (the inboard facet 1-3 below the frame plane under the
    shield) a circular round stood ~0.5 proud of the frame; the angle from the two fields' normals over C_STENCIL."""
    out = np.minimum(pa, hd)
    m = (pa < r_u) & (hd < r_u)
    if not m.any():
        return out
    Um, Hm, Am = U[m], H[m], A[m]
    gp, gh = [], []
    e = C_STENCIL
    for k in range(3):
        dv = np.zeros(3)
        dv[k] = e
        p1, h1 = _grip_parts(Um + dv[0], Hm + dv[1], Am + dv[2], g, split=True)
        p0, h0 = _grip_parts(Um - dv[0], Hm - dv[1], Am - dv[2], g, split=True)
        gp.append(p1 - p0)
        gh.append(h1 - h0)
    gp, gh = np.stack(gp, -1), np.stack(gh, -1)
    ca = np.sum(gp * gh, -1) / np.maximum(np.linalg.norm(gp, axis=-1) * np.linalg.norm(gh, axis=-1), 1e-12)
    out = out.copy()
    out[m] = rmin_ang(pa[m], hd[m], r_u, ca)
    return out


def _hf_scale(g):
    """1 / |grad hf| of grip g's plane-height coordinate (hf varies ~1.0-1.1 per mm of h): the head zone's plane-height
    terms are scaled to millimetres of distance."""
    f = grip_frame(g)
    n = f["n"]
    w = _gsel("grip_walls", g)
    e = (1.0 - w) * n + w * np.array([0.0, 0.0, 1.0])
    e /= np.linalg.norm(e)
    grad = np.array([0.0, 1.0, 0.0]) - (e[1] / float(np.dot(n, e))) * n
    return 1.0 / float(np.linalg.norm(grad))


def pad_layer(U, H, A, g):
    """The LEATHER PAD as its own material (own sense; rev M judges DR4-07): the part of the moulding inside the
    groove's inner wall (pad outline offset gw inward) within pad_section[7] below the leather surface (bead
    included) -- for the sections' hatching; the solids' outer surface is unchanged."""
    rec, cen, wc, bead, gw, gd = (float(x) for x in T()["pad_section"][:6])
    t = float(T()["pad_section"][7])
    U, H, A = (np.asarray(x, float) for x in (U, H, A))
    z, uf, hf = _to_plane(U, H, A, g)
    dp = field("pad_" + g, pad_outline(g))(uf, hf)
    under = (_leather(uf, hf, g) - t) - z
    under = np.minimum(under, (-rec - t) - z)               # under the bead too (its base at the leather edge)
    return np.maximum(np.maximum(dp + gw, under), grip(U, H, A, g))


def grip_part(U, H, A, g):
    """1 where a surface point of grip g is leather (inside the pad outline, within 1.5 of the leather surface)."""
    z, uf, hf = _to_plane(U, H, A, g)
    dp = field("pad_" + g, pad_outline(g))(uf, hf)
    gw, bead = float(T()["pad_section"][4]), float(T()["pad_section"][3])
    return (dp < -(gw + 2.0 * bead)) & (z > grip_surface_z(uf, hf, g) - 1.5)


# ============================================================================================ body
def body_outline():
    """Front outline of the black body: the outboard half (body_half) at u > 0, the inboard half (body_in) at u < 0."""
    key = ("bodyol", id(T()["body_half"]), id(T()["body_in"]))
    if key not in _CACHE:
        pts, cs = join_halves(tv("body_half"), tv("body_in"), dict(T().get("body_half_corners", ())),
                              dict(T().get("body_in_corners", ())))
        _CACHE[key] = smooth_outline(pts, cs)
    return _CACHE[key]


def top_line(U):
    """h of the body's TOP LINE at |u| per side (rev L, body_top): the body outline's own top edge (its first
    body_top samples, the dense curve-law polyline) as a C2 cubic in |u| through those samples, continued beyond its
    end along its end tangent (rev M, judges DR4-02: rev L interpolated the 0.25 mm polyline linearly -- the top
    plane faceted every 0.25 mm, stripes under the R 2 / R 3 rounds -- and held the end height, a crease in the top
    plane along the inboard neck's end at |u| 90.7)."""
    key = ("topline2", id(T()["body_half"]), id(T()["body_in"]), id(T()["body_top"]))
    if key not in _CACHE:
        from scipy.interpolate import CubicSpline
        Q = body_outline()
        nt = [int(x) for x in T()["body_top"]]
        out = {}
        for sgn, src, n in ((1, T()["body_half"], nt[0]), (-1, T()["body_in"], nt[1])):
            end = np.array([sgn * src[n - 1][0], src[n - 1][1]])
            k = int(np.argmin(np.hypot(Q[:, 0] - end[0], Q[:, 1] - end[1])))
            P = Q[:k + 1] if sgn > 0 else np.vstack([Q[k:][::-1], Q[:1]])
            uu = np.abs(P[:, 0])
            o = np.argsort(uu)
            uu, hh = uu[o], P[o, 1]
            keep = np.r_[True, np.diff(uu) > 1e-6]
            cs = CubicSpline(uu[keep], hh[keep], bc_type=((1, 0.0), (2, 0.0)))   # dh/du 0 at u 0 (the halves meet smoothly)
            out[sgn] = (cs, float(uu[keep][-1]), float(cs(uu[keep][-1])), float(cs(uu[keep][-1], 1)))
        _CACHE[key] = out
    d = _CACHE[key]
    U = np.asarray(U, float)

    def ev(side, au):
        cs, ue, he, se = d[side]
        return np.where(au <= ue, cs(np.minimum(au, ue)), he + se * (au - ue))
    au = np.abs(U)
    return np.where(U >= 0, ev(1, au), ev(-1, au))


TOP_LIFT = 40.0


def body_side_outline():
    """The body outline with its top-edge samples lifted TOP_LIFT mm: the field of the body's SIDES and BOTTOM only
    (rev L: the top surface is the top plane through the top line; rev K's outline top and plane met in a crease)."""
    key = ("sideol", id(T()["body_half"]), id(T()["body_in"]), id(T()["body_top"]))
    if key not in _CACHE:
        nt = [int(x) for x in T()["body_top"]]
        bh = np.array(T()["body_half"], float)
        bi = np.array(T()["body_in"], float)
        bh[:nt[0], 1] += TOP_LIFT
        bi[:nt[1], 1] += TOP_LIFT
        pts, cs = join_halves(bh, bi, dict(T().get("body_half_corners", ())), dict(T().get("body_in_corners", ())))
        _CACHE[key] = smooth_outline(pts, cs)
    return _CACHE[key]


def body_aft(U, H, soft=0.0):
    """a of the body's aft surface: cover_t ahead of the face in the core, blending (smoothstep over the neck zone)
    onto the necks' aft surface -- outboard the WEB's: the trim face's plane web[0] forward of it where that lies forward
    of the grip's aft plane, joined to it by a smooth minimum web[1] wide (rev L, judges DR3-01: rev K held the web under
    the face's disc only and it stood as a fin beside the head); inboard the grip's aft plane, blending (smoothstep over
    |u| neck_in[0] -> neck_in[1]) onto the shield facet's plane neck_in[2] forward of it where the low neck meets the
    head (the facet is recessed 1.5-5 below the grip plane: rev L)."""
    U, H = np.asarray(U, float), np.asarray(H, float)
    u0, u1 = (float(x) for x in T()["neck"][:2])
    core = face_a(H) - crown_bevel(U, H, soft) - float(T()["cover_t"])
    w = smoothstep(np.abs(U), u0, u1)
    gap, kw = (float(x) for x in T()["web"][:2])
    web = smin(grip_plane_a(np.abs(U), H, "out"), face_plane_a(U, H) - gap, kw)
    v0, v1, gi = (float(x) for x in T()["neck_in"][:3])
    s_in = smoothstep(np.abs(U), v0, v1)
    neck_in = (1.0 - s_in) * grip_plane_a(np.abs(U), H, "in") + s_in * (facet_plane_a(np.abs(U), H) - gi)
    gp = np.where(U >= 0, web, neck_in)
    return (1.0 - w) * core + w * gp


def facet_plane_a(U, H):
    """a of the inboard head's shield-facet plane at the front-view point (u, h), own sense (u > 0)."""
    c, n = head_in_face()
    return c[2] - (n[0] * (np.asarray(U, float) - c[0]) + n[1] * (np.asarray(H, float) - c[1])) / n[2]


def afcs_boss(U, H, A):
    """The AFCS disconnect's round black boss (afcs[4] dia): a disc about the aft-face normal through the AFCS centre,
    its aft face afcs_boss[0] proud of the body's aft surface, afcs_boss[1] deep (its back face free where it hangs
    below the body's lower edge over the hand slot; judges DR2-04), aft edge R afcs_boss[2]."""
    c, nrm = afcs_axis()
    proud, depth, r_e = (float(x) for x in T()["afcs_boss"][:3])
    r_b = float(T()["afcs_boss"][5])
    R = 0.5 * float(T()["afcs"][4])
    P = np.stack([U, H, A], -1) - c
    z = P @ nrm
    r = np.linalg.norm(P - z[..., None] * nrm, axis=-1)
    return rmax(rmax(r - R, z, r_e), -z - depth, r_b)


def afcs_axis():
    """(c, n): the AFCS boss's aft-face centre (u, h, a) and its axis (the aft face's normal)."""
    D = T()
    u, h = float(D["afcs"][0]), float(D["afcs"][1])
    t = math.radians(float(D["face_tilt"]))
    nrm = np.array([0.0, math.sin(t), math.cos(t)])
    a = float(face_a(h)) - float(D["cover_t"]) + float(D["afcs_boss"][0])
    return np.array([u, h, a]), nrm


CROWN_SOFT = 2.0                  # mm: the crown bevel's fade at the insert groove, for the body's top plane only


def body(U, H, A):
    """Signed distance of the black body (mm), rev L (judges DR3-01 / 02): the SIDES and BOTTOM are the front outline
    without its top edge (body_side_outline) extruded forward from the aft surface (body_aft) with a side draft
    behind the stem; the TOP is a plane falling forward at body_form[1] deg FROM THE HORIZONTAL from the top line
    (top_line) at the aft surface; the FORWARD FACE body_form[0] ahead of the aft surface behind the stem, tapering
    (smoothstep over |u| 35 -> 62) to the necks' neck[2]; rounds: sides x aft and top x aft R body_form[3], sides x
    forward face and top x forward face R body_form[4] easing to R body_form[5] under the foot, reduced to R
    body_form[7] over |u| 40 -> 62 (the thin arm / neck region), sides x top R body_form[3] -- rev M: that edge a
    ROLLING-BALL round between the side piece and the top piece, each already rounded onto the forward face, the aft
    face cut last
    (rev L rounded the forward face last, onto max(sides, top): its R 8 read that max's internal ridge -- the medial
    line of the sides-top edge, 2-4 mm deep -- and creased the forward round where the top plane meets the drafted
    sides, at |u| 32-35 and 53); the top plane and the aft surface divided by their gradients' lengths (true radii);
    the AFCS boss blended on."""
    U, H, A = (np.asarray(x, float) for x in (U, H, A))
    X1, X2, r, f_aft = _body_pieces(U, H, A)
    core = isect_ang(X1, X2, r, U, H, A, lambda u_, h_, a_: _body_pieces(u_, h_, a_)[:2])
    core = rmax(core, f_aft, r)
    return smin(core, afcs_boss(U, H, A), float(T()["afcs_boss"][3]))


def _body_pieces(U, H, A):
    """(side piece, top piece, R sides x top, aft field) of body(): the sides (resp. the top plane) x the forward face R
    rf (>= 3 > R 2 everywhere: the rolling ball leaves a piece's own round onto the shared forward face alone); the aft
    face is cut last (rounding it into both pieces made them share the aft face, and where the top piece's R 2 left it
    tangentially -- radius = the ball's -- the ball dented the inboard neck's top, cusps of 25-37 deg)."""
    bf = T()["body_form"]
    depth, top_deg, draft, r_aft, r_fwd, r_foot, r_tf = (float(x) for x in bf[:7])
    u0, u1, nd = (float(x) for x in T()["neck"][:3])
    side = field("body_side", body_side_outline())(U, H)
    ab = body_aft(U, H)
    w = smoothstep(np.abs(U), u0, u1)
    # rev L: under the foot the draft's inward offset is capped at body_form[8] (smoothly, released over h -45 -> -30)
    # so offset + forward round stay inside the foot corners' R ~11 (an R 14 round over the full 10 deg draft reached
    # the outline's medial axis there and creased the corners)
    cap = float(bf[8]) + (20.0 - float(bf[8])) * smoothstep(H, -45.0, -30.0)
    off = (1.0 - w) * np.maximum(ab - A, 0.0) * math.tan(math.radians(draft))
    side = side + smin(off, cap, 2.0)
    htu = top_line(U)
    th = math.radians(top_deg)

    def ftop(Uq):
        hq = top_line(Uq)
        return (H - hq) * math.cos(th) + (body_aft(Uq, hq, CROWN_SOFT) - A) * math.sin(th)
    du = 0.25                     # rev L: the top plane and the aft surface divided by their gradients' lengths
    gU = (ftop(U + du) - ftop(U - du)) / (2.0 * du)   # (the top line rises ~1:1 at the necks: |grad| 1.5 had made
    f_top = ((H - htu) * math.cos(th) + (body_aft(U, htu, CROWN_SOFT) - A) * math.sin(th)) / np.sqrt(1.0 + gU ** 2)
    aU = (body_aft(U + du, H) - body_aft(U - du, H)) / (2.0 * du)                    # R 2 ~R 1)
    aH = (body_aft(U, H + du) - body_aft(U, H - du)) / (2.0 * du)
    f_aft = (A - ab) / np.sqrt(1.0 + aU ** 2 + aH ** 2)
    D_ = depth - (depth - nd) * smoothstep(np.abs(U), 35.0, u0)
    f_front = (ab - D_) - A
    r_nf = float(bf[7])
    rf = r_fwd + (r_nf - r_fwd) * smoothstep(np.abs(U), 40.0, u0) + (r_foot - r_fwd) * smoothstep(-H, 40.0, 55.0)
    X1 = rmax(side, f_front, rf)
    X2 = rmax(f_top, f_front, rf)
    return X1, X2, r_aft, f_aft


def rmax_ang(a, b, r, ca):
    """Intersection of two fields with a ROLLING-BALL round of radius r (the dual of rmin_ang; ca = cos of the angle
    between their outward normals): a true round where the surfaces meet at an angle, none where they run flush or
    one is already rounded onto the other with a radius >= r."""
    return -rmin_ang(-np.asarray(a, float), -np.asarray(b, float), r, ca)


def isect_ang(a, b, r, U, H, A, fn, e=0.05):
    """rmax_ang of the fields a, b (= fn(U, H, A)) with their normals' angle by central differences e, evaluated
    only where both are within r and differ -- elsewhere max(a, b)."""
    out = np.maximum(a, b)
    m = (a > -r) & (b > -r) & (np.abs(a - b) > 1e-9)
    if not m.any():
        return out
    Um, Hm, Am = U[m], H[m], A[m]
    ga, gb = [], []
    for k in range(3):
        dv = np.zeros(3)
        dv[k] = e
        a1, b1 = fn(Um + dv[0], Hm + dv[1], Am + dv[2])
        a0, b0 = fn(Um - dv[0], Hm - dv[1], Am - dv[2])
        ga.append(a1 - a0)
        gb.append(b1 - b0)
    ga, gb = np.stack(ga, -1), np.stack(gb, -1)
    ca = np.sum(ga * gb, -1) / np.maximum(np.linalg.norm(ga, axis=-1) * np.linalg.norm(gb, axis=-1), 1e-12)
    out = out.copy()
    out[m] = rmax_ang(a[m], b[m], r, ca)
    return out


# ============================================================================================ switches (DR2-04)
def _revolve(U, H, A, c, nrm, prof, r_bound):
    """Exact signed distance of the solid of revolution of the closed (r, z) profile `prof` (r may run negative:
    profiles across the axis are mirrored) about the axis through c along nrm; points further than r_bound from c get
    the bounding-sphere distance (cheap culling)."""
    from cad import sdf2d
    P = np.stack([U, H, A], -1) - c
    dist = np.linalg.norm(P, axis=-1)
    out = dist - r_bound
    m = out < 1.5
    if m.any():
        Q = P[m]
        z = Q @ nrm
        r = np.linalg.norm(Q - z[:, None] * nrm, axis=-1)
        out = out.copy()
        out[m] = sdf2d.polygon(r, z, prof)
    return out


def _rounded_profile(pts, rad, n=6):
    """Closed polygon through pts with the corners {index: radius} rounded (circular arcs)."""
    P = np.asarray(pts, float)
    out = []
    N = len(P)
    for i in range(N):
        r = rad.get(i, 0.0)
        if r <= 0:
            out.append(P[i])
            continue
        a, b, c = P[i - 1], P[i], P[(i + 1) % N]
        u1, u2 = (a - b) / np.linalg.norm(a - b), (c - b) / np.linalg.norm(c - b)
        th = math.acos(float(np.clip(np.dot(u1, u2), -1, 1)))
        t = r / math.tan(0.5 * th)
        p1, p2 = b + t * u1, b + t * u2
        bis = (u1 + u2) / np.linalg.norm(u1 + u2)
        cc = b + bis * r / math.sin(0.5 * th)
        a1, a2 = math.atan2(*(p1 - cc)[::-1]), math.atan2(*(p2 - cc)[::-1])
        da = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
        for s in np.linspace(0.0, 1.0, n):
            out.append(cc + r * np.array([math.cos(a1 + s * da), math.sin(a1 + s * da)]))
    return np.array(out)


def tcs_axis():
    D = T()
    u, h = float(D["tcs"][0]), float(D["tcs"][1])
    t = math.radians(float(D["face_tilt"]))
    return np.array([u, h, float(face_a(h))]), np.array([0.0, math.sin(t), math.cos(t)])


def tcs_profiles():
    """(bezel, button) closed (r, z) profiles of the TCS (z from the white face, + aft): the bezel ring tcs_profile
    [0] proud, its outer edge rolled, the dish from r tcs_profile[5] to [6], the bore; the domed button (tcs[3] dia)
    whose top stands tcs_profile[4] below the bezel top (+ = recessed), seated tcs_seat deep."""
    D = T()
    od, bd = float(D["tcs"][2]), float(D["tcs"][3])
    bz, rr, dish, dome, below, r_in, r_out = (float(x) for x in D["tcs_profile"][:7])
    seat = float(D["tcs_seat"])
    Rb = 0.5 * od
    re = min(rr, bz)
    bez = _rounded_profile([(r_in, -seat), (Rb, -seat), (Rb, bz), (r_out, bz), (r_in, bz - dish)], {2: re})
    top = bz - below
    rb = 0.5 * bd
    xs = np.linspace(-rb, rb, 25)
    dome_pts = [(x, top - dome * (x / rb) ** 2) for x in xs[::-1]]
    btn = np.array([(-rb, -seat)] + [(rb, -seat)] + dome_pts)
    return bez, btn


def tcs(U, H, A):
    c, nrm = tcs_axis()
    bez, btn = tcs_profiles()
    R = 0.5 * float(T()["tcs"][2]) + 3.0
    return np.minimum(_revolve(U, H, A, c, nrm, bez, R), _revolve(U, H, A, c, nrm, btn, R))


def afcs(U, H, A):
    """The red AFCS cap: a cylinder afcs[2] dia, afcs[3] high on the boss face, top edge R afcs_boss[4]."""
    c, nrm = afcs_axis()
    D = T()
    r = 0.5 * float(D["afcs"][2])
    hh = float(D["afcs"][3])
    re = float(D["afcs_boss"][4])
    prof = _rounded_profile([(-r, -1.0), (r, -1.0), (r, hh), (-r, hh)], {2: re, 3: re})
    return _revolve(U, H, A, c, nrm, prof, math.hypot(r, hh) + 2.0)


def trim_rocker(U, H, A):
    """The split bow-tie pitch-trim rocker on the round face: the two mirrored lobes (yoke_draw.rocker_halves'
    outline) extruded along the face normal from 1 below the face to the saddle top z = hm + (he - hm) (|x| / (L /
    2))^sexp; top edges R trim_grooves[2]."""
    from cad import sdf2d
    c, n = head_out_face()
    eu, ev = _facet_frame(c, n)
    tr = T()["trim"]
    L, we, ww, gap, he, hm = (float(tr[i]) for i in (3, 4, 5, 6, 7, 8))
    sexp = float(T()["trim_lunes"][3])
    r_e = float(T()["trim_grooves"][2])
    P = np.stack([U, H, A], -1) - c
    out = np.linalg.norm(P, axis=-1) - (0.5 * L + 9.0)
    m = out < 1.5
    if m.any():
        Q = P[m]
        z, x, y = Q @ n, Q @ eu, Q @ ev
        lobe = rocker_lobe()
        d = np.minimum(sdf2d.polygon(x, y, lobe), sdf2d.polygon(-x, y, lobe))
        top = hm + (he - hm) * (np.abs(x) / (0.5 * L)) ** sexp
        out = out.copy()
        out[m] = np.maximum(rmax(d, z - top, r_e), -1.0 - z)
    return out


def rocker_lobe(n=12):
    """One lobe of the split rocker in the face frame (x across the head, y along the face): from the split (x =
    gap / 2, waist width) to a round end (width trim[4])."""
    tr = T()["trim"]
    L, we, ww, gap = (float(tr[i]) for i in (3, 4, 5, 6))
    r = 0.5 * we
    xc = 0.5 * L - r
    arc = [(xc + r * math.cos(t), r * math.sin(t)) for t in np.linspace(-0.5 * math.pi, 0.5 * math.pi, n)]
    return np.array([(0.5 * gap, -0.5 * ww)] + arc + [(0.5 * gap, 0.5 * ww)], float)


def button_frame():
    """(c, n, eu, ev): the push button's axis on the inboard shield facet, own sense (u > 0 away from the yoke
    centreline): the collar centre button[0:2] lifted along a onto the facet plane."""
    ci, ni = head_in_face()
    eu, ev = _facet_frame(ci, ni)
    b = T()["button"]
    u, h = float(b[0]), float(b[1])
    a = ci[2] - (ni[0] * (u - ci[0]) + ni[1] * (h - ci[1])) / ni[2]
    return np.array([u, h, a]), ni, eu, ev


def hex_collar(U, H, A):
    """The black hex collar (button[2] across the corners, button[6] across the flats) button[5] proud of the shield
    facet, seated 1 below it; own sense."""
    from cad import sdf2d
    c, n, eu, ev = button_frame()
    b = T()["button"]
    rc, hp = 0.5 * float(b[2]), float(b[5])
    a = np.radians(np.arange(6) * 60.0 + 30.0)
    hexa = np.c_[rc * np.cos(a), rc * np.sin(a)]
    P = np.stack([U, H, A], -1) - c
    out = np.linalg.norm(P, axis=-1) - (rc + hp + 3.0)
    m = out < 1.5
    if m.any():
        Q = P[m]
        z, x, y = Q @ n, Q @ eu, Q @ ev
        out = out.copy()
        out[m] = np.maximum(rmax(sdf2d.polygon(x, y, hexa), z - hp, 0.3), -1.0 - z)
    return out


def button_cap(U, H, A):
    """The push button's cap: a cylinder button[3] dia standing button[4] above the collar, top edge R 1, a centre
    dimple button[7] dia, button[8] deep (spherical); own sense."""
    c, n, _, _ = button_frame()
    b = T()["button"]
    r, hh, hp, dd, ddep = 0.5 * float(b[3]), float(b[4]), float(b[5]), float(b[7]), float(b[8])
    ztop = hp + hh
    rs = (0.25 * dd * dd + ddep * ddep) / (2.0 * ddep)                # dimple sphere radius
    prof = _rounded_profile([(-r, 0.0), (r, 0.0), (r, ztop), (-r, ztop)], {2: 1.0, 3: 1.0})
    cyl = _revolve(U, H, A, c, n, prof, math.hypot(r, ztop) + 2.0)
    sph = np.linalg.norm(np.stack([U, H, A], -1) - (c + (ztop + rs - ddep) * n), axis=-1) - rs
    return np.maximum(cyl, -sph)


def button(U, H, A):
    """Hex collar + cap of the inboard head's push button (own sense)."""
    return np.minimum(hex_collar(U, H, A), button_cap(U, H, A))


def fwd_switch_frame(g):
    """(c, t, w, n, row) of grip g's forward-face switch (fwd_switch, rev M judges FID4-08, [E] placeholders): c the
    centre ON the forward face (own sense (u, h, a)), t the unit direction along the grip (up the grip axis, in the
    face), w across it (+ away from the yoke centreline), n the face's outward normal (forward, = -aft normal); row =
    the table row (h, length, width, proud, top edge R, saddle)."""
    row = [float(x) for x in T()["fwd_switch"][0 if g == "out" else 1]]
    hc = row[0]
    Q = grip_outline(g)
    F = field("grip_" + g, Q)
    us = np.linspace(Q[:, 0].min(), Q[:, 0].max(), 801)
    uc = float(us[np.argmin(F(us, np.full_like(us, hc)))])         # mid-width of G on that plane row
    f = grip_frame(g)
    n = f["n"]
    wv = _gsel("grip_walls", g)
    e = (1.0 - wv) * n + wv * np.array([0.0, 0.0, 1.0])
    e /= np.linalg.norm(e)
    depth = float(_depth(hc, g))
    p_plane = np.array([uc, hc, float(grip_plane_a(uc, hc, g))])
    c = p_plane - (depth / float(np.dot(n, e))) * e                   # along the walls to the forward face
    (ub, hb), (ut, ht) = T()["grip_axis"]
    t = np.array([ut - ub, ht - hb, 0.0])
    t[2] = -t[1] * f["tr"] - t[0] * f["tt"]                           # in the (aft) plane: forward face parallel
    t /= np.linalg.norm(t)
    w = np.cross(t, -n)
    if w[0] < 0:
        w = -w
    w /= np.linalg.norm(w)
    return c, t, w, -n, row


def fwd_switch(U, H, A, g):
    """Grip g's forward-face (finger-side) switch [E] (own sense): a stadium `length` along the grip x `width` across
    on the forward face, standing `proud` of it (seated 1 below), its top edge R `r`, its top dipped `saddle` at the
    centre (the inboard rocker; the outboard PTT trigger flat)."""
    c, t, w, n, row = fwd_switch_frame(g)
    _, L, W, proud, r_e, sag = row[:6]
    P = np.stack([np.asarray(U, float), np.asarray(H, float), np.asarray(A, float)], -1) - c
    out = np.linalg.norm(P, axis=-1) - (0.5 * L + proud + 3.0)
    m = out < 1.5
    if m.any():
        Q = P[m]
        x, y, z = Q @ t, Q @ w, Q @ n
        hl = max(0.5 * (L - W), 0.0)
        d2 = np.hypot(np.maximum(np.abs(x) - hl, 0.0), y) - 0.5 * W
        top = proud - sag * (1.0 - np.clip(np.abs(x) / (0.5 * L), 0.0, 1.0) ** 2)
        out = out.copy()
        out[m] = np.maximum(rmax(d2, z - top, r_e), -1.0 - z)
    return out


# ============================================================================================ the assembly
PARTS = ("body", "cover", "grip_out", "grip_in")
SWITCHES = ("tcs", "afcs", "trim", "button", "fwd_out", "fwd_in")   # small solids seated on the cover / boss / heads
#                                                       (DR2-04) and the grips' forward faces ([E] placeholders, FID4-08)


C_STENCIL = 0.15                   # mm: the normals that set the rolling ball's angle are central differences over
#                                    1.5 cells of the 2-D fields' 0.1 grid (a 0.01 stencil read the bilinear cells' kinks)


def moulding(U, H, A):
    """The black MOULDING: body + both grips joined by the rolling-ball round R neck[3] (rmin_ang: a true round where
    the surfaces meet at an angle, none where they run flush -- the web on the outboard grip's frame, the neck on the
    inboard grip), then each grip's pad pocket, groove and bead cut / added (pad_finish, rev M judges DR4-01)."""
    U, H, A = (np.asarray(x, float) for x in (U, H, A))
    r = float(T()["neck"][3])
    fb = body
    fo = lambda U_, H_, A_: grip_solid(U_, H_, A_, "out")           # noqa: E731
    fi = lambda U_, H_, A_: grip_solid(-U_, H_, A_, "in")           # noqa: E731
    b, go, gi = fb(U, H, A), fo(U, H, A), fi(U, H, A)
    out = np.minimum(b, np.minimum(go, gi))
    mo, mi = (b < r) & (go < r), (b < r) & (gi < r)
    if mo.any() or mi.any():
        m = mo | mi
        Um, Hm, Am = U[m], H[m], A[m]
        nb = _unit_grad(fb, Um, Hm, Am, e=C_STENCIL)
        vals = out[m].copy()
        for mk, fg, gv in ((mo[m], fo, go[m]), (mi[m], fi, gi[m])):
            if mk.any():
                ng = _unit_grad(fg, Um[mk], Hm[mk], Am[mk], e=C_STENCIL)
                ca = np.sum(nb[mk] * ng, -1)
                vals[mk] = np.minimum(vals[mk], rmin_ang(b[m][mk], gv[mk], r, ca))
        out = out.copy()
        out[m] = vals
    out = pad_finish(out, U, H, A, "out")
    return pad_finish(out, -U, H, A, "in")


def part_sdf(name, U, H, A):
    if name == "black":
        return moulding(U, H, A)
    if name == "cover":
        return cover(U, H, A)
    if name == "body":
        return body(U, H, A)
    if name == "grip_out":
        return grip(U, H, A, "out")
    if name == "grip_in":
        return grip(-U, H, A, "in")
    if name == "tcs":
        return tcs(U, H, A)
    if name == "afcs":
        return afcs(U, H, A)
    if name == "trim":
        return trim_rocker(U, H, A)
    if name == "button":
        return button(-np.asarray(U, float), H, A)
    if name == "pad_out":
        return pad_layer(U, H, A, "out")
    if name == "pad_in":
        return pad_layer(-np.asarray(U, float), H, A, "in")
    if name == "fwd_out":
        return fwd_switch(U, H, A, "out")
    if name == "fwd_in":
        return fwd_switch(-np.asarray(U, float), H, A, "in")
    if name == "switches":
        return np.minimum.reduce([part_sdf(p, U, H, A) for p in SWITCHES])
    raise KeyError(name)


def union_sdf(U, H, A, parts=PARTS):
    s = None
    for p in parts:
        v = part_sdf(p, U, H, A)
        s = v if s is None else np.minimum(s, v)
    return s


BOX = dict(black=(-154, -68, -78, 154, 104, 26), body=(-108, -68, -78, 108, 100, 6), cover=(-77, -61, -34, 77, 71, 6),
           grip_out=(76, -62, -66, 154, 104, 26), grip_in=(-154, -62, -66, -76, 104, 26),
           tcs=(46, 39, -22, 71, 64, -6), afcs=(47, 10, -18, 74, 37, 4), trim=(92, 62, -40, 131, 102, -10),
           button=(-125, 58, -32, -87, 95, -8), fwd_out=(96, 36, -55, 118, 68, -33), fwd_in=(-110, 27, -50, -89, 55, -30),
           pad_out=(84, -36, -10, 146, 66, 6), pad_in=(-146, -42, -10, -84, 60, 6))


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
    h.update(_SRC_HASH)
    return h.hexdigest()[:16]


def _src_hash():
    import hashlib
    from pathlib import Path
    return hashlib.sha1(Path(__file__).read_bytes()).digest()


_SRC_HASH = _src_hash()           # the source THIS process imported (a file edited mid-run must not re-key its cache)


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
