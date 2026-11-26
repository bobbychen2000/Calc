"""Outdoor furniture and yard objects (asset family "furniture").

Every piece is a plain function that adds geometry to a Geo you pass in:

    piece(geo, at, heading_deg=0.0, ...)

Units are METRES.  `at` is the ground point under the piece's plan centre: (x, y) -> z = 0, or (x, y, z) for a piece
standing on a raised terrace.  Each piece is built in its own local frame -- x = the piece's width / length (to the
right of somebody who stands in front of it and looks at it), y = depth, +y is the BACK, z = up -- so its FRONT (the
seat front, the firebox opening, the fan grilles) faces local -y.  `heading_deg` then turns it about Z,
counter-clockwise seen from above: 0 = the front faces the street (-Y), 90 = it faces +X, 180 = it faces into the
lot (+Y), -90 = it faces -X.  Wall-mounted items (utility_box) use the kit's wall frame instead: origin = a point on
the wall's outer face, right = unit vector along the wall, out = the wall's outward normal.

Sizes come from the listing photos (dining table 0.75 m high and chair seats 0.45 m as the scale anchors; p25, p26,
p27, p30, video frames seg022 / seg123 / seg141).  Triangle budgets: chair <= 1200, sofa <= 2500, table <= 800,
fireplace <= 3000, fire bowl <= 500, condenser <= 600 (the test zone prints what each piece takes).

Materials (web/viewer/looks/furniture.js gives each one its textures; the plain factors below are the GLB fallback):
    furniture_dark         charcoal powder-coated aluminium (dining set frames)
    furn_black             near-black powder coat (cabana lounge frames, fire-bowl plinth)
    furn_slat_grey         grey wood-look composite slats (dining table top)
    furniture_wood         oiled teak (teak lounge set)
    furn_wood_taupe        weathered teak-look slab (cabana coffee table top, arm caps)
    furn_wood_light        light hardwood (hoop chairs)
    cushion (+ _edge)      pale grey-white upholstery (teak set); *_edge = the cushion's side band with its piping
    furn_fabric_slate (+ _edge)     slate grey upholstery (dining chairs)
    furn_fabric_charcoal (+ _edge)  dark grey upholstery (cabana lounge)
    furn_fabric_white      white throw pillows
    furn_rope              grey woven rope (hoop chairs, seat webbing)
    fireplace_stone        white stacked ledgestone of the outdoor fireplace
    fireplace_firebrick    buff herringbone firebrick lining
    fireplace_soot         the dark throat of the firebox
    furn_bronze            dark bronze sheet (chimney cap)
    firebowl_concrete      white cast concrete of the fire bowl
    firebowl_media         dark lava rock in its pan
    furn_ceramic_white     glazed white ceramic (drum table, table jars)
    furn_plaster_white     matt white plaster planters
    pot_terracotta         plain clay pots
    rug_diamond            the flat-woven outdoor rug (one texture over the whole rug)
    doormat_coir           coir door mats
    condenser_white        off-white painted sheet metal (heat pump, equipment cabinet)
    condenser_fan          the dark fan opening behind its wire guard (one texture per fan)
    utility_grey           grey weatherproof boxes and conduit
"""
from __future__ import annotations

import numpy as np

from model.kit import Geo, UP
from model import materials as _materials

# ---- materials (GLB fallback factors, linear RGB) -------------------------------------------------------------------
_REG = {
    'furniture_dark': dict(color=(0.060, 0.068, 0.078), roughness=0.55, metallic=0.35),
    'furn_black': dict(color=(0.022, 0.024, 0.027), roughness=0.5, metallic=0.35),
    'furn_slat_grey': dict(color=(0.215, 0.205, 0.195), roughness=0.8),
    'furniture_wood': dict(color=(0.270, 0.112, 0.048), roughness=0.62),
    'furn_wood_taupe': dict(color=(0.250, 0.175, 0.118), roughness=0.7),
    'furn_wood_light': dict(color=(0.520, 0.330, 0.170), roughness=0.6),
    'cushion': dict(color=(0.660, 0.670, 0.680), roughness=1.0),
    'cushion_edge': dict(color=(0.660, 0.670, 0.680), roughness=1.0),
    'furn_fabric_slate': dict(color=(0.100, 0.115, 0.130), roughness=1.0),
    'furn_fabric_slate_edge': dict(color=(0.100, 0.115, 0.130), roughness=1.0),
    'furn_fabric_charcoal': dict(color=(0.046, 0.050, 0.056), roughness=1.0),
    'furn_fabric_charcoal_edge': dict(color=(0.046, 0.050, 0.056), roughness=1.0),
    'furn_fabric_white': dict(color=(0.780, 0.770, 0.740), roughness=1.0),
    'furn_rope': dict(color=(0.380, 0.370, 0.350), roughness=1.0),
    'fireplace_stone': dict(color=(0.800, 0.790, 0.770), roughness=0.85),
    'fireplace_firebrick': dict(color=(0.520, 0.400, 0.280), roughness=0.9),
    'fireplace_soot': dict(color=(0.030, 0.028, 0.026), roughness=1.0),
    'furn_bronze': dict(color=(0.050, 0.040, 0.032), roughness=0.45, metallic=0.8),
    'firebowl_concrete': dict(color=(0.760, 0.760, 0.740), roughness=0.75),
    'firebowl_media': dict(color=(0.030, 0.030, 0.032), roughness=0.9),
    'furn_ceramic_white': dict(color=(0.820, 0.820, 0.800), roughness=0.3),
    'furn_plaster_white': dict(color=(0.780, 0.770, 0.740), roughness=0.9),
    'pot_terracotta': dict(color=(0.420, 0.170, 0.085), roughness=0.9),
    'rug_diamond': dict(color=(0.300, 0.270, 0.240), roughness=1.0),
    'doormat_coir': dict(color=(0.230, 0.130, 0.060), roughness=1.0),
    'condenser_white': dict(color=(0.700, 0.690, 0.650), roughness=0.5, metallic=0.1),
    'condenser_fan': dict(color=(0.060, 0.060, 0.060), roughness=0.7),
    'utility_grey': dict(color=(0.250, 0.260, 0.270), roughness=0.6),
}
for _n, _s in _REG.items():
    _materials.register(_n, **_s)

DARK, BLACK = 'furniture_dark', 'furn_black'
TEAK, TAUPE, LIGHTWOOD, SLAT = 'furniture_wood', 'furn_wood_taupe', 'furn_wood_light', 'furn_slat_grey'
EDGE_TILE = 0.10          # the *_edge fabric textures are one tile (0.10 m in v) from piping to piping


# ---- small helpers --------------------------------------------------------------------------------------------------
def _unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def _rz(deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def _rx(deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])


def _p3(at):
    at = np.asarray(at, float).ravel()
    return np.array([at[0], at[1], at[2] if len(at) > 2 else 0.0])


def _place(geo, g, at, heading_deg):
    """Merge the locally built piece g into geo: turned by heading_deg about Z, moved to `at`."""
    geo.merge(g, R=_rz(heading_deg), t=_p3(at))
    return geo


def _add(g, mat, V, N, UV, F):
    """Append triangles, each turned to face the way its vertex normals point; degenerate ones are dropped."""
    V = np.asarray(V, float).reshape(-1, 3)
    N = np.asarray(N, float).reshape(-1, 3)
    F = np.asarray(F, int).reshape(-1, 3)
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    fn = np.cross(b - a, c - a)
    keep = np.linalg.norm(fn, axis=1) > 1e-13
    s = np.einsum('ij,ij->i', fn, N[F[:, 0]] + N[F[:, 1]] + N[F[:, 2]])
    F = np.where((s < 0)[:, None], F[:, ::-1], F)[keep]
    g.mesh(mat).add(V, N, UV, F)


def _quad(g, mat, P, UV):
    """Flat quad (4 points, counter-clockwise seen from outside) with explicit UVs."""
    P = np.asarray(P, float)
    n = _unit(np.cross(P[1] - P[0], P[3] - P[0]) + np.cross(P[2] - P[1], P[0] - P[1]))
    g.mesh(mat).add(P, np.tile(n, (4, 1)), UV, [[0, 1, 2], [0, 2, 3]])


def _board(g, mat, lo, hi, grain=0, faces='xXyYzZ', uvo=(0.0, 0.0)):
    """Axis-aligned board lo..hi whose UVs run with the grain: u (metres) along axis `grain` (0 x, 1 y, 2 z), v across.
    uvo shifts the texture so neighbouring boards do not show the same figure."""
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    for f in faces:
        k = 'xyz'.index(f.lower())
        s = 1.0 if f.isupper() else -1.0
        i, j = [a for a in range(3) if a != k]
        c = [(lo[i], lo[j]), (hi[i], lo[j]), (hi[i], hi[j]), (lo[i], hi[j])]
        if (s > 0) != (k != 1):
            c = c[::-1]
        P = np.zeros((4, 3))
        P[:, i] = [q[0] for q in c]
        P[:, j] = [q[1] for q in c]
        P[:, k] = hi[k] if s > 0 else lo[k]
        if grain == j:
            UV = np.stack([P[:, j], P[:, i]], -1)
        else:
            UV = np.stack([P[:, i], P[:, j]], -1)
        n = np.zeros(3)
        n[k] = s
        g.mesh(mat).add(P, np.tile(n, (4, 1)), UV + np.asarray(uvo, float), [[0, 1, 2], [0, 2, 3]])


def _frames(P, closed=False, up=UP):
    """Unit tangents and parallel-transported side / up vectors along a polyline."""
    P = np.asarray(P, float)
    n = len(P)
    T = np.zeros((n, 3))
    for i in range(n):
        if closed:
            a, b = P[(i - 1) % n], P[(i + 1) % n]
            T[i] = _unit(_unit(P[i] - a) + _unit(b - P[i]))
        else:
            d0 = _unit(P[i] - P[i - 1]) if i > 0 else np.zeros(3)
            d1 = _unit(P[i + 1] - P[i]) if i < n - 1 else np.zeros(3)
            T[i] = _unit(d0 + d1)
    ref = np.asarray(up, float) if abs(T[0] @ _unit(up)) < 0.95 else np.array([1.0, 0.0, 0.0])
    side = _unit(np.cross(T[0], ref))
    S = [side]
    for i in range(1, n):
        v = np.cross(T[i - 1], T[i])
        s, c = np.linalg.norm(v), float(T[i - 1] @ T[i])
        if s > 1e-9:
            k = v / s
            side = side * c + np.cross(k, side) * s + k * (k @ side) * (1 - c)
        side = _unit(side - T[i] * (side @ T[i]))
        S.append(side)
    S = np.array(S)
    return T, S, np.cross(S, T)


def _tube(g, mat, P, r, n=8, closed=False, caps=True, sq=0.0, up=UP):
    """Smooth tube along a polyline.  r: radius, or one per point, or (rx, ry) pairs per point (rx sideways, ry up);
    sq > 0 makes the section a superellipse of that exponent (a rounded square for sq = 4)."""
    P = np.asarray(P, float)
    m = len(P)
    T, S, U = _frames(P, closed, up)
    r = np.asarray(r, float)
    if r.ndim == 0:
        r = np.full((m, 2), float(r))
    elif r.ndim == 1:
        r = np.stack([r, r], -1) if len(r) == m else np.tile(r, (m, 1))
    th = np.linspace(0, 2 * np.pi, n + 1)
    c, s = np.cos(th), np.sin(th)
    if sq > 0:
        q = (np.abs(c) ** sq + np.abs(s) ** sq) ** (-1.0 / sq)
        nc = np.sign(c) * np.abs(c * q) ** (sq - 1)
        ns = np.sign(s) * np.abs(s * q) ** (sq - 1)
    else:
        q, nc, ns = np.ones(n + 1), c, s
    seg = np.linalg.norm(np.diff(np.vstack([P, P[:1]]) if closed else P, axis=0), axis=1)
    L = np.concatenate([[0.0], np.cumsum(seg)])
    rings = m + 1 if closed else m
    V, N, UV = [], [], []
    for a in range(rings):
        i = a % m
        V.append(P[i] + np.outer(c * q * r[i, 0], S[i]) + np.outer(s * q * r[i, 1], U[i]))
        nn = np.outer(nc / max(r[i, 0], 1e-9), S[i]) + np.outer(ns / max(r[i, 1], 1e-9), U[i])
        N.append(nn / np.maximum(np.linalg.norm(nn, axis=1, keepdims=True), 1e-12))
        UV.append(np.stack([np.full(n + 1, L[a]), th * r[i].mean()], -1))
    F = []
    for a in range(rings - 1):
        for k in range(n):
            p, q2 = a * (n + 1) + k, (a + 1) * (n + 1) + k
            F += [[p, q2, q2 + 1], [p, q2 + 1, p + 1]]
    _add(g, mat, np.vstack(V), np.vstack(N), np.vstack(UV), F)
    if caps and not closed:
        for i, sgn in ((0, -1.0), (m - 1, 1.0)):
            ring = P[i] + np.outer(c[:-1] * q[:-1] * r[i, 0], S[i]) + np.outer(s[:-1] * q[:-1] * r[i, 1], U[i])
            Vc = np.vstack([P[i], ring])
            Fc = [[0, 1 + k, 1 + (k + 1) % n] for k in range(n)]
            _add(g, mat, Vc, np.tile(sgn * T[i], (n + 1, 1)), (Vc - P[i]) @ np.stack([S[i], U[i]], 1), Fc)


def _sweep(g, mat, P, section, closed=False, caps=True):
    """Sweep a closed 2-D section [(s, t)] (s to the right of travel, t up; counter-clockwise) along a level
    polyline: hard edges across the section, smooth shading along the path (curved bands and rings)."""
    P = np.asarray(P, float)
    m = len(P)
    T = np.zeros((m, 3))
    sc = np.ones(m)
    for i in range(m):
        a = P[(i - 1) % m] if (closed or i > 0) else None
        b = P[(i + 1) % m] if (closed or i < m - 1) else None
        d0 = _unit(P[i] - a) if a is not None else None
        d1 = _unit(b - P[i]) if b is not None else None
        if d0 is None:
            T[i] = d1
        elif d1 is None:
            T[i] = d0
        else:
            T[i] = _unit(d0 + d1)
            sc[i] = 1.0 / max(float(T[i] @ d1), 0.5)
    S = np.array([_unit(np.cross(t, UP)) for t in T])
    seg = np.linalg.norm(np.diff(np.vstack([P, P[:1]]) if closed else P, axis=0), axis=1)
    L = np.concatenate([[0.0], np.cumsum(seg)])
    sec = np.asarray(section, float)
    k = len(sec)
    per = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.roll(sec, -1, 0) - sec, axis=1))])
    rings = m + 1 if closed else m
    for j in range(k):
        a, b = sec[j], sec[(j + 1) % k]
        n2 = _unit([b[1] - a[1], -(b[0] - a[0])])
        V, N, UV, F = [], [], [], []
        for q in range(rings):
            i = q % m
            for e, pe in ((a, per[j]), (b, per[j + 1])):
                V.append(P[i] + e[0] * sc[i] * S[i] + e[1] * UP)
                N.append(n2[0] * S[i] + n2[1] * UP)
                UV.append((L[q], pe))
        for q in range(rings - 1):
            F += [[2 * q, 2 * q + 2, 2 * q + 3], [2 * q, 2 * q + 3, 2 * q + 1]]
        _add(g, mat, V, N, UV, F)
    if caps and not closed:
        for i, sgn in ((0, -1.0), (m - 1, 1.0)):
            Vc = np.array([P[i] + e[0] * sc[i] * S[i] + e[1] * UP for e in sec])
            Fc = [[0, q, q + 1] for q in range(1, k - 1)]
            _add(g, mat, Vc, np.tile(sgn * T[i], (k, 1)), sec, Fc)


def _revolve(g, mat, prof, n=24, centre=(0.0, 0.0, 0.0), crease_deg=38.0):
    """Surface of revolution about the vertical axis through `centre`.  prof = [(r, z), ...] listed with the outside
    on the right of travel (bottom outward, up the outer wall, inward over the top).  Bends sharper than crease_deg
    stay hard edges; level bands get plan (x, y) UVs, the others (arc length round, length along the profile)."""
    prof = np.asarray(prof, float)
    c0 = np.asarray(centre, float)
    d = np.diff(prof, axis=0)
    ln = np.linalg.norm(d, axis=1)
    sn = np.stack([d[:, 1], -d[:, 0]], -1) / np.maximum(ln, 1e-12)[:, None]
    cl = np.concatenate([[0.0], np.cumsum(ln)])
    rmax = prof[:, 0].max()
    ph = np.linspace(0, 2 * np.pi, n + 1)
    cp, sp = np.cos(ph), np.sin(ph)
    cos_c = np.cos(np.radians(crease_deg))

    def nrm(j, end):                         # the normal of band j at its start (end = 0) or its end (1)
        q = j - 1 if end == 0 else j + 1
        if 0 <= q < len(sn) and ln[q] > 1e-9 and sn[j] @ sn[q] > cos_c:
            return _unit(sn[j] + sn[q])
        return sn[j]

    for j in range(len(d)):
        if ln[j] < 1e-9:
            continue
        V, N, UV = [], [], []
        for e in (0, 1):
            r, z = prof[j + e]
            nn = nrm(j, e)
            V.append(np.stack([c0[0] + r * cp, c0[1] + r * sp, np.full(n + 1, c0[2] + z)], -1))
            N.append(np.stack([nn[0] * cp, nn[0] * sp, np.full(n + 1, nn[1])], -1))
            if abs(d[j, 1]) < 1e-6:
                UV.append(np.stack([r * cp, r * sp], -1))
            else:
                UV.append(np.stack([ph * rmax, np.full(n + 1, cl[j + e])], -1))
        F = []
        for k in range(n):
            F += [[k, k + 1, n + 1 + k + 1], [k, n + 1 + k + 1, n + 1 + k]]
        _add(g, mat, np.vstack(V), np.vstack(N), np.vstack(UV), F)


def _rrect(a, b, r, nc=3):
    """Counter-clockwise rounded rectangle, half sizes a (x) and b (y).  r = one radius, or (r_back, r_front)."""
    rb, rf = (r, r) if np.isscalar(r) else r
    out = []
    for (sx, sy, rr, a0) in ((1, 1, rb, 0.0), (-1, 1, rb, 90.0), (-1, -1, rf, 180.0), (1, -1, rf, 270.0)):
        rr = min(rr, a - 1e-4, b - 1e-4)
        for t in np.radians(a0 + np.linspace(0, 90, nc + 1)):
            out.append((sx * (a - rr) + rr * np.cos(t), sy * (b - rr) + rr * np.sin(t)))
    return np.array(out)


def _circle(r, n=16, c=(0.0, 0.0)):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.stack([c[0] + r * np.cos(t), c[1] + r * np.sin(t)], -1)


def _inset(O, d):
    """Offset a counter-clockwise outline inward by d."""
    if d == 0:
        return O.copy()
    e = np.roll(O, -1, 0) - O
    en = np.stack([e[:, 1], -e[:, 0]], -1)
    en /= np.maximum(np.linalg.norm(en, axis=1, keepdims=True), 1e-12)
    vn = en + np.roll(en, 1, 0)
    vn /= np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)
    k = 1.0 / np.maximum(np.einsum('ij,ij->i', vn, en), 0.6)
    return O - d * vn * k[:, None]


def _smooth_normals(V, F):
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    N = np.zeros_like(V)
    for k in range(3):
        np.add.at(N, F[:, k], fn)
    return N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)


def _cushion(g, mat, outline, z0, h, r=0.03, crown=0.012, edge_mat=None, bottom=False, seg=2, uvo=(0.0, 0.0),
             R=None, t=None):
    """A box cushion: plan `outline` (counter-clockwise (x, y)), from z0 up h, edges rounded with radius r, the top
    panel puffed up by `crown`.  The upright side band takes edge_mat (a *_edge fabric: piping top and bottom) when
    given.  R / t (rotation matrix, translation) place it afterwards, e.g. a back cushion leaning on a frame."""
    O = np.asarray(outline, float)
    n = len(O)
    r = min(r, h / 2 - 1e-4)
    a = [np.radians(45.0)] if seg >= 2 else []
    st = ([(r, 0.0)] + [(r * (1 - np.sin(x)), r * (1 - np.cos(x))) for x in a] + [(0.0, r), (0.0, h - r)]
          + [(r * (1 - np.cos(x)), h - r + r * np.sin(x)) for x in a] + [(r, h)])
    ks = 1 + len(a)                                    # the band ks .. ks + 1 is the upright side
    rings = [np.column_stack([_inset(O, d), np.full(n, z0 + z)]) for d, z in st]
    c = rings[-1][:, :2].mean(0)
    for s in (0.6,):
        rings.append(np.column_stack([c + s * (rings[len(st) - 1][:, :2] - c), np.full(n, z0 + h + crown * (1 - s * s))]))
    K = len(rings)
    V = np.vstack(rings + [[[c[0], c[1], z0 + h + crown]], [[c[0], c[1], z0]]])
    top, bot = K * n, K * n + 1
    F, band = [], []
    for k in range(K - 1):
        for i in range(n):
            j = (i + 1) % n
            F += [[k * n + i, k * n + j, (k + 1) * n + j], [k * n + i, (k + 1) * n + j, (k + 1) * n + i]]
            band += [k, k]
    for i in range(n):
        F.append([(K - 1) * n + i, (K - 1) * n + (i + 1) % n, top])
        band.append(K)
    if bottom:
        for i in range(n):
            F.append([(i + 1) % n, i, bot])
            band.append(-1)
    F, band = np.array(F), np.array(band)
    N = _smooth_normals(V, F)
    uvo = np.asarray(uvo, float)
    per = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.roll(O, -1, 0) - O, axis=1))])
    tmp = Geo()
    # the side band, unrolled
    idx = np.concatenate([np.arange(n), [0]])
    Vs = np.vstack([V[ks * n + idx], V[(ks + 1) * n + idx]])
    Ns = np.vstack([N[ks * n + idx], N[(ks + 1) * n + idx]])
    v1 = EDGE_TILE if edge_mat else (h - 2 * r)
    UVs = np.vstack([np.stack([per + uvo[0], np.zeros(n + 1)], -1), np.stack([per + uvo[0], np.full(n + 1, v1)], -1)])
    Fs = []
    for i in range(n):
        Fs += [[i, i + 1, n + 1 + i + 1], [i, n + 1 + i + 1, n + 1 + i]]
    _add(tmp, edge_mat or mat, Vs, Ns, UVs, Fs)
    # the panels, plan-mapped
    sel = band != ks
    _add(tmp, mat, V, N, V[:, :2] + uvo, F[sel])
    g.merge(tmp, R=R, t=t)


def _pillow(g, mat, w, h, t, n=5, pinch=0.07, R=None, at=None, uvo=(0.0, 0.0)):
    """A knife-edge throw pillow: w x h (local x, y), t thick at the middle (local z), corners left as 'ears'."""
    a = np.sin(np.linspace(-1, 1, n + 1) * np.pi / 2)
    A, B = np.meshgrid(a, a, indexing='ij')
    X = w / 2 * A * (1 - pinch * (1 - B ** 2))
    Y = h / 2 * B * (1 - pinch * (1 - A ** 2))
    Z = t / 2 * ((1 - A ** 2) * (1 - B ** 2)) ** 0.42
    V = np.stack([X, Y, Z], -1).reshape(-1, 3)
    F = []
    for i in range(n):
        for j in range(n):
            p = i * (n + 1) + j
            F += [[p, p + n + 1, p + n + 2], [p, p + n + 2, p + 1]]
    F = np.array(F)
    N = _smooth_normals(V, F)
    rim = (np.abs(A) > 0.999) | (np.abs(B) > 0.999)
    rim = rim.reshape(-1)
    flat = N[rim] * [1, 1, 0]
    out = V[rim] * [1, 1, 0]
    bad = np.linalg.norm(flat, axis=1) < 0.05
    flat[bad] = out[bad]
    N[rim] = flat / np.maximum(np.linalg.norm(flat, axis=1, keepdims=True), 1e-12)
    tmp = Geo()
    UV = V[:, :2] + np.asarray(uvo, float)
    _add(tmp, mat, V, N, UV, F)
    _add(tmp, mat, V * [1, 1, -1], N * [1, 1, -1], UV + 0.37, F)
    g.merge(tmp, R=R, t=at)


def _lean(tilt_deg=0.0, yaw_deg=0.0, roll_deg=0.0):
    """Rotation that stands a flat-built cushion / pillow up: its local x stays the width, local y becomes 'up',
    local +z (the puffed face) looks at the front (-y); then it is tilted back by tilt_deg (top toward +y), rolled
    about its own normal and turned by yaw_deg about Z."""
    up = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]])
    return _rz(yaw_deg) @ _rx(-tilt_deg) @ up @ _rz(roll_deg)


def _bar(g, mat, a, b, w, h, up=UP):
    """Straight rectangular bar (w sideways x h along `up`) from a to b, centred on the line."""
    g.prism(mat, [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)], a, b, up=up)


# =====================================================================================================================
# REAR PATIO: dining set (p25, seg022)
# =====================================================================================================================
def dining_table(geo, at, heading_deg=0.0, length=2.07, width=0.96, height=0.75, seed=1):
    """The long slat-top dining table under the pergola (p25): 2.07 x 0.96 m, 0.75 m high; a top of grey wood-look
    slats laid ACROSS the table (14 of 148 mm with 6 mm joints) on a charcoal frame with staggered double-blade legs
    at the corners.  Local x = the long axis.  ~300 triangles."""
    g = Geo()
    rng = np.random.default_rng(seed)
    L, W, H = length, width, height
    n = max(4, int(round(L / 0.148)))
    pitch, gap, th = L / n, 0.006, 0.022
    for i in range(n):
        x0 = -L / 2 + i * pitch + gap / 2
        _board(g, SLAT, (x0, -W / 2, H - th), (x0 + pitch - gap, W / 2, H), grain=1, faces='xXyYZ',
               uvo=rng.random(2) * 3.0)
    ins, at_, ah = 0.014, 0.03, 0.06
    z1 = H - th
    z0 = z1 - ah
    g.box(DARK, (-L / 2 + ins, -W / 2 + ins, z1 - 0.004), (L / 2 - ins, W / 2 - ins, z1 - 0.001), faces='zZ')
    for s in (-1, 1):                                               # long aprons
        y0, y1 = sorted((s * (W / 2 - ins), s * (W / 2 - ins - at_)))
        g.box(DARK, (-L / 2 + ins, y0, z0), (L / 2 - ins, y1, z1), faces='xXyYz')
    for s in (-1, 1):
        x0, x1 = sorted((s * (L / 2 - ins), s * (L / 2 - ins - 0.07)))          # the corner blades' end rail
        g.box(DARK, (x0, -W / 2 + ins, z0), (x1, W / 2 - ins, z1), faces='xXz')
        xb0, xb1 = sorted((s * (L / 2 - ins - 0.10), s * (L / 2 - ins - 0.155)))  # the inner blades' rail
        g.box(DARK, (xb0, -W / 2 + ins, z0), (xb1, W / 2 - ins, z1), faces='xXz')
        for t in (-1, 1):
            ya0, ya1 = sorted((t * (W / 2 - ins), t * (W / 2 - ins - 0.19)))
            g.box(DARK, (x0, ya0, 0.0), (x1, ya1, z0), faces='xXyYz')
            yb0, yb1 = sorted((t * (W / 2 - ins - 0.16), t * (W / 2 - ins - 0.35)))
            g.box(DARK, (xb0, yb0, 0.0), (xb1, yb1, z0), faces='xXyYz')
    return _place(geo, g, at, heading_deg)


def _horseshoe(a, b, y_front, y0, n_arc=12):
    """Plan path of a round-back chair: from the front-left corner back along the side, round the back (half an
    ellipse a x b about (0, y0)) and forward to the front-right corner."""
    pts = [(-a, y_front)]
    for t in np.radians(np.linspace(180, 0, n_arc + 1)):
        pts.append((a * np.cos(t), y0 + b * np.sin(t)))
    pts.append((a, y_front))
    return np.array(pts)


def dining_chair(geo, at, heading_deg=0.0, pillow=True, seed=0):
    """Round-back dining armchair (p25, seg022): four slim charcoal legs, a flat band wrapping from front leg to
    front leg at arm height (0.575 .. 0.705 m), a seat ring at 0.41 m with webbing, a slate-grey seat cushion (top
    0.50 m) and a loose back pillow.  0.63 m wide, 0.58 m deep, 0.705 m to the top of the band (pillow to ~0.83).
    The sitter faces local -y.  ~800 triangles."""
    g = Geo()
    rng = np.random.default_rng(1000 + seed)
    yf, y0 = -0.225, 0.05
    band = _horseshoe(0.305, 0.285, yf - 0.018, y0)
    ring = _horseshoe(0.280, 0.262, yf, y0)
    zb0, zb1 = 0.575, 0.705
    _sweep(g, DARK, np.column_stack([band, np.zeros(len(band))]),
           [(-0.007, zb0), (0.007, zb0), (0.007, zb1), (-0.007, zb1)])
    _sweep(g, DARK, np.column_stack([ring, np.zeros(len(ring))]),
           [(-0.014, 0.365), (0.014, 0.365), (0.014, 0.41), (-0.014, 0.41)], caps=False)
    g.box(DARK, (-0.28, yf - 0.014, 0.365), (0.28, yf + 0.014, 0.41), faces='yYzZ')
    for x, y, zt in ((-0.28, yf, zb1 - 0.004), (0.28, yf, zb1 - 0.004), (-0.205, 0.228, zb0 + 0.03),
                     (0.205, 0.228, zb0 + 0.03)):
        _tube(g, DARK, [(x, y, 0.0), (x, y, zt)], [0.0155, 0.0185], n=8, sq=4.0)
    for x in (-0.15, 0.0, 0.15):                                    # webbing under the cushion
        g.box('furn_rope', (x - 0.024, yf, 0.409), (x + 0.024, 0.29 if x == 0 else 0.25, 0.412), faces='zZ')
    o = _rrect(0.262, 0.25, (0.20, 0.05), nc=4) + [0.0, 0.012]
    _cushion(g, 'furn_fabric_slate', o, 0.412, 0.082, r=0.034, crown=0.012, edge_mat='furn_fabric_slate_edge',
             uvo=rng.random(2))
    if pillow:
        R = _lean(13.0 + rng.uniform(-3, 5), rng.uniform(-9, 9), rng.uniform(-7, 7))
        _pillow(g, 'furn_fabric_slate', 0.41, 0.34, 0.125, R=R,
                at=(rng.uniform(-0.02, 0.02), 0.225, 0.665 + rng.uniform(-0.008, 0.012)), uvo=rng.random(2))
    return _place(geo, g, at, heading_deg)


def table_jars(geo, at, heading_deg=0.0):
    """The centrepiece on the dining table (p25): a ribbed white cylinder vase, a low bowl and a lidded jar, all
    glazed white.  `at` = the point on the TABLE TOP (give z = 0.75) under the group's middle.  ~330 triangles."""
    g = Geo()
    m = 'furn_ceramic_white'
    _revolve(g, m, [(0.0, 0.0), (0.062, 0.0), (0.065, 0.006), (0.065, 0.20), (0.058, 0.205), (0.052, 0.20),
                    (0.052, 0.19)], n=14, centre=(-0.13, 0.02, 0.0))
    _revolve(g, m, [(0.0, 0.0), (0.035, 0.0), (0.062, 0.035), (0.058, 0.065), (0.048, 0.06)], n=12,
             centre=(0.0, -0.05, 0.0))
    _revolve(g, m, [(0.0, 0.0), (0.05, 0.0), (0.054, 0.006), (0.054, 0.13), (0.057, 0.132), (0.057, 0.142),
                    (0.02, 0.15), (0.018, 0.165), (0.0, 0.168)], n=14, centre=(0.13, 0.0, 0.0))
    return _place(geo, g, at, heading_deg)


def dining_set(geo, at, heading_deg=0.0, seed=3):
    """The whole dining group as in p25 / p30: the table (long axis = local x), two chairs on each long side and one
    at each end, and the white jars on the top."""
    R, o = _rz(heading_deg), _p3(at)
    rng = np.random.default_rng(seed)
    dining_table(geo, o, heading_deg, seed=seed)
    spots = [(-0.50, -0.70, 0.0), (0.50, -0.72, 0.0), (-0.52, 0.71, 180.0), (0.50, 0.70, 180.0),
             (-1.36, 0.0, -90.0), (1.36, 0.02, 90.0)]
    for i, (x, y, h) in enumerate(spots):
        p = o + R @ np.array([x + rng.uniform(-0.03, 0.03), y + rng.uniform(-0.03, 0.03), 0.0])
        dining_chair(geo, p, heading_deg + h + 180.0 + rng.uniform(-5, 5), seed=seed * 10 + i)
    table_jars(geo, o + R @ np.array([0.08, 0.05, 0.75]), heading_deg)
    return geo


# =====================================================================================================================
# REAR PATIO: teak lounge set (p25 left edge, p26, p30, seg123)
# =====================================================================================================================
def _teak_back(g, rng, x0, x1, yb, top=0.63):
    """One slatted back bay between two stiles: top rail, two slats and the apron board (p25 crop)."""
    y0, y1 = yb - 0.045, yb - 0.008
    for z0, z1 in ((top - 0.07, top), (0.385, 0.525), (0.205, 0.345), (0.02, 0.17)):
        _board(g, TEAK, (x0, y0, z0), (x1, y1, z1), grain=0, faces='yYzZ', uvo=rng.random(2) * 3)


def _teak_frame(g, rng, W, D, bays, top=0.63):
    """Boxy teak frame of the lounge pieces: slatted back, open sides under flat arm boards, base rails all round."""
    hw, hd = W / 2, D / 2
    stile = 0.10
    # back: stiles + bays
    xs = np.linspace(-hw, hw - stile, bays + 1)
    for i, x in enumerate(xs):
        w = stile if i in (0, bays) else 0.085
        xo = x if i in (0, bays) else x + (stile - w) / 2
        _board(g, TEAK, (xo, hd - 0.06, 0.0), (xo + w, hd, top), grain=2, faces='xXyYZ', uvo=rng.random(2) * 3)
    for i in range(bays):
        xa = xs[i] + (stile if i == 0 else (stile + 0.085) / 2)
        xb = xs[i + 1] + (0.0 if i + 1 == bays else (stile - 0.085) / 2)
        _teak_back(g, rng, xa, xb, hd, top)
    for s in (-1, 1):
        xa, xb = sorted((s * hw, s * (hw - stile)))
        # front post, arm board, side base rail
        _board(g, TEAK, (xa, -hd, 0.0), (xb, -hd + 0.07, top - 0.05), grain=2, faces='xXyY', uvo=rng.random(2) * 3)
        _board(g, TEAK, (xa, -hd, top - 0.05), (xb, hd - 0.06, top), grain=1, faces='xXyzZ', uvo=rng.random(2) * 3)
        xr0, xr1 = sorted((s * (hw - 0.012), s * (hw - 0.05)))
        _board(g, TEAK, (xr0, -hd + 0.07, 0.02), (xr1, hd - 0.06, 0.17), grain=1, faces='xXzZ', uvo=rng.random(2) * 3)
    _board(g, TEAK, (-hw + stile, -hd + 0.012, 0.02), (hw - stile, -hd + 0.05, 0.17), grain=0, faces='yYzZ',
           uvo=rng.random(2) * 3)
    _board(g, TEAK, (-hw + 0.05, -hd + 0.05, 0.15), (hw - 0.05, hd - 0.045, 0.18), grain=0, faces='zZ',
           uvo=rng.random(2) * 3)                                    # the seat deck


def teak_armchair(geo, at, heading_deg=0.0, width=1.04, depth=0.92, pillow=True, seed=0):
    """Deep-seat teak club chair (p25 left edge, p30): a boxy oiled-teak frame 1.04 x 0.92 m, 0.63 m high all round
    (slatted back, open sides under flat arm boards), a thick pale seat cushion (top ~0.40 m) and a loose back
    cushion rising to ~0.86 m.  The sitter faces local -y.  ~800 triangles."""
    g = Geo()
    rng = np.random.default_rng(2000 + seed)
    _teak_frame(g, rng, width, depth, 1)
    sw, sd = width - 0.22, depth - 0.115
    _cushion(g, 'cushion', _rrect(sw / 2, sd / 2, 0.05) + [0.0, -0.012], 0.18, 0.20, r=0.05, crown=0.022,
             edge_mat='cushion_edge', uvo=rng.random(2))
    _cushion(g, 'cushion', _rrect(sw / 2 - 0.01, 0.245, 0.07), 0.0, 0.19, r=0.06, crown=0.03,
             edge_mat='cushion_edge', bottom=True, uvo=rng.random(2),
             R=_lean(12.0), t=(0.0, depth / 2 - 0.075, 0.385 + 0.245))
    if pillow:
        _pillow(g, 'furn_fabric_white', 0.46, 0.46, 0.15, R=_lean(22.0, rng.uniform(-25, 25), rng.uniform(-12, 12)),
                at=(rng.uniform(-0.12, 0.12), depth / 2 - 0.30, 0.61), uvo=rng.random(2))
    return _place(geo, g, at, heading_deg)


def teak_sofa(geo, at, heading_deg=0.0, length=2.74, depth=0.96, pillows=3, seed=0):
    """Deep-seat teak sofa (p30, seg123, p26): 2.74 x 0.96 m, frame 0.63 m high with a three-bay slatted back and
    flat arm boards, three pale seat cushions, three back cushions (to ~0.86 m) and white throw pillows.
    The sitters face local -y.  ~2300 triangles."""
    g = Geo()
    rng = np.random.default_rng(3000 + seed)
    _teak_frame(g, rng, length, depth, 3)
    sw = (length - 0.215) / 3
    sd = depth - 0.115
    for i in range(3):
        x = (i - 1) * sw
        _cushion(g, 'cushion', _rrect(sw / 2 - 0.004, sd / 2, 0.05) + [x, -0.012], 0.18, 0.20, r=0.05, crown=0.022,
                 edge_mat='cushion_edge', uvo=rng.random(2))
        _cushion(g, 'cushion', _rrect(sw / 2 - 0.012, 0.245, 0.07), 0.0, 0.19, r=0.06, crown=0.03,
                 edge_mat='cushion_edge', bottom=True, uvo=rng.random(2),
                 R=_lean(12.0 + rng.uniform(-2, 2), rng.uniform(-2, 2)),
                 t=(x, depth / 2 - 0.075, 0.385 + 0.245))
    for k in range(pillows):
        x = (k - (pillows - 1) / 2) * 0.52 + rng.uniform(-0.08, 0.08)
        _pillow(g, 'furn_fabric_white', 0.46, 0.46, 0.15,
                R=_lean(24.0 + rng.uniform(-5, 8), rng.uniform(-28, 28), rng.uniform(-18, 18)),
                at=(x, depth / 2 - 0.31 - 0.03 * (k % 2), 0.615), uvo=rng.random(2))
    return _place(geo, g, at, heading_deg)


def teak_coffee_table(geo, at, heading_deg=0.0, length=1.42, width=0.71, height=0.31, seed=0):
    """Low teak coffee table of the lounge set (p30): 1.42 x 0.71 m, 0.31 m high, a top of ten boards laid across
    on square corner posts and aprons.  Local x = the long axis.  ~200 triangles."""
    g = Geo()
    rng = np.random.default_rng(4000 + seed)
    L, W, H = length, width, height
    n = max(3, int(round(L / 0.142)))
    pitch = L / n
    for i in range(n):
        x0 = -L / 2 + i * pitch + 0.0025
        _board(g, TEAK, (x0, -W / 2, H - 0.03), (x0 + pitch - 0.005, W / 2, H), grain=1, faces='xXyYZ',
               uvo=rng.random(2) * 3)
    g.box(BLACK, (-L / 2 + 0.03, -W / 2 + 0.03, H - 0.034), (L / 2 - 0.03, W / 2 - 0.03, H - 0.031), faces='zZ')
    for sx in (-1, 1):
        for sy in (-1, 1):
            x0, x1 = sorted((sx * (L / 2 - 0.02), sx * (L / 2 - 0.105)))
            y0, y1 = sorted((sy * (W / 2 - 0.02), sy * (W / 2 - 0.105)))
            _board(g, TEAK, (x0, y0, 0.0), (x1, y1, H - 0.03), grain=2, faces='xXyY', uvo=rng.random(2) * 3)
    for s in (-1, 1):
        y0, y1 = sorted((s * (W / 2 - 0.035), s * (W / 2 - 0.07)))
        _board(g, TEAK, (-L / 2 + 0.105, y0, H - 0.10), (L / 2 - 0.105, y1, H - 0.03), grain=0, faces='yYz',
               uvo=rng.random(2) * 3)
        x0, x1 = sorted((s * (L / 2 - 0.035), s * (L / 2 - 0.07)))
        _board(g, TEAK, (x0, -W / 2 + 0.105, H - 0.10), (x1, W / 2 - 0.105, H - 0.03), grain=1, faces='xXz',
               uvo=rng.random(2) * 3)
    return _place(geo, g, at, heading_deg)


def teak_lounge_set(geo, at, heading_deg=0.0, seed=5):
    """The teak group as it stands beside the pergola (p30): `at` = the middle of the SOFA's footprint, the sofa's
    back toward local +y; two armchairs on its right-hand end (local -x side) facing along +x, the coffee table in
    front.  With heading 0 the sofa faces the house (-Y) as on the lot."""
    R, o = _rz(heading_deg), _p3(at)
    teak_sofa(geo, o, heading_deg, seed=seed)
    teak_armchair(geo, o + R @ np.array([-1.65, -0.98, 0.0]), heading_deg + 90.0, seed=seed)
    teak_armchair(geo, o + R @ np.array([-1.65, -2.14, 0.0]), heading_deg + 90.0, pillow=False, seed=seed + 1)
    teak_coffee_table(geo, o + R @ np.array([0.58, -1.68, 0.0]), heading_deg, seed=seed)
    return geo


# =====================================================================================================================
# OUTDOOR FIREPLACE (p26, seg123_039 / 059, p30)
# =====================================================================================================================
def _stone_wall(g, a, b, z0, z1, u0, a1=None, b1=None):
    """Upright (or battered) stone face from plan point a to b (left to right seen from outside), z0 .. z1; a1 / b1 =
    the top edge's plan points when the face leans.  u runs along the wall from u0, v = height: the stone courses of
    all faces line up.  Returns the u at b."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    a1 = a if a1 is None else np.asarray(a1, float)
    b1 = b if b1 is None else np.asarray(b1, float)
    w = np.linalg.norm(b - a)
    sl = float(np.hypot(z1 - z0, np.linalg.norm((a1 + b1) / 2 - (a + b) / 2)))
    P = [(a[0], a[1], z0), (b[0], b[1], z0), (b1[0], b1[1], z1), (a1[0], a1[1], z1)]
    w1 = np.linalg.norm(b1 - a1)
    UV = [(u0, z0), (u0 + w, z0), (u0 + (w + w1) / 2, z0 + sl), (u0 + (w - w1) / 2, z0 + sl)]
    _quad(g, 'fireplace_stone', P, UV)
    return u0 + w


def _stones(g, rng, a, b, z0, z1, u0, count, skip=None):
    """Scatter proud ledgestone strips over the upright face a -> b (z0 .. z1): thin boxes on the 40 mm course grid,
    8 .. 20 mm proud, textured as the wall behind them.  skip = (s0, s1, za, zb): keep clear of an opening."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    w = np.linalg.norm(b - a)
    ex = np.array([(b - a)[0] / w, (b - a)[1] / w, 0.0])
    out = np.cross(ex, UP)
    o = np.array([a[0], a[1], 0.0])
    course = 0.04
    k0, k1 = int(np.ceil(z0 / course)), int(np.floor(z1 / course))
    made = tries = 0
    while made < count and tries < count * 8:
        tries += 1
        ln = rng.uniform(0.12, 0.36)
        if ln > w - 0.02:
            continue
        s0 = rng.uniform(0.0, w - ln)
        if rng.random() < 0.22:                       # quoins: let some run to a corner
            s0 = 0.0 if rng.random() < 0.5 else w - ln
        rows = 1 if rng.random() < 0.7 else 2
        k = rng.integers(k0, max(k0 + 1, k1 - rows + 1))
        za, zb = k * course + 0.002, (k + rows) * course - 0.002
        if zb > z1 or za < z0:
            continue
        if skip and s0 < skip[1] + 0.01 and s0 + ln > skip[0] - 0.01 and za < skip[3] + 0.01 and zb > skip[2] - 0.01:
            continue
        p = rng.uniform(0.008, 0.02)
        c = [o + ex * s0, o + ex * (s0 + ln)]
        f = [q + out * p for q in c]
        za3, zb3 = np.array([0, 0, za]), np.array([0, 0, zb])
        _quad(g, 'fireplace_stone', [f[0] + za3, f[1] + za3, f[1] + zb3, f[0] + zb3],
              [(u0 + s0, za), (u0 + s0 + ln, za), (u0 + s0 + ln, zb), (u0 + s0, zb)])
        _quad(g, 'fireplace_stone', [f[0] + zb3, f[1] + zb3, c[1] + zb3, c[0] + zb3],
              [(u0 + s0, zb), (u0 + s0 + ln, zb), (u0 + s0 + ln, zb + p), (u0 + s0, zb + p)])
        _quad(g, 'fireplace_stone', [c[0] + za3, c[1] + za3, f[1] + za3, f[0] + za3],
              [(u0 + s0, za - p), (u0 + s0 + ln, za - p), (u0 + s0 + ln, za), (u0 + s0, za)])
        _quad(g, 'fireplace_stone', [c[0] + za3, f[0] + za3, f[0] + zb3, c[0] + zb3],
              [(u0 + s0 - p, za), (u0 + s0, za), (u0 + s0, zb), (u0 + s0 - p, zb)])
        _quad(g, 'fireplace_stone', [f[1] + za3, c[1] + za3, c[1] + zb3, f[1] + zb3],
              [(u0 + s0 + ln, za), (u0 + s0 + ln + p, za), (u0 + s0 + ln + p, zb), (u0 + s0 + ln, zb)])
        made += 1


def fireplace(geo, at, heading_deg=0.0, seed=7, relief=110):
    """The tall outdoor fireplace at the edge of the rear patio (p26, seg123_039, p30): white stacked ledgestone,
    1.60 m wide x 0.82 m deep; a firebox block to 1.62 m (opening 1.15 x 1.00 m over a 0.30 m hearth, lined with buff
    herringbone firebrick), battered shoulders to 2.20 m, then a 0.75 m square chimney (flush with the back) to
    3.55 m under a low pyramidal bronze cap (top 3.78 m).  The opening faces local -y.  `relief` = the number of
    proud stones that break up the faces.  ~1500 triangles."""
    g = Geo()
    rng = np.random.default_rng(seed)
    st = 'fireplace_stone'
    hw, hd = 0.80, 0.41
    z1, z2, z3 = 1.62, 2.20, 3.55
    ow, oz0, oz1, od = 0.575, 0.30, 1.30, 0.50
    A, B, C, D = (-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)
    # tier 1: front in four pieces round the opening, then right, back, left
    u = 0.0
    _quad(g, st, [(-hw, -hd, 0), (-ow, -hd, 0), (-ow, -hd, z1), (-hw, -hd, z1)],
          [(0, 0), (hw - ow, 0), (hw - ow, z1), (0, z1)])
    _quad(g, st, [(ow, -hd, 0), (hw, -hd, 0), (hw, -hd, z1), (ow, -hd, z1)],
          [(hw + ow, 0), (2 * hw, 0), (2 * hw, z1), (hw + ow, z1)])
    _quad(g, st, [(-ow, -hd, 0), (ow, -hd, 0), (ow, -hd, oz0), (-ow, -hd, oz0)],
          [(hw - ow, 0), (hw + ow, 0), (hw + ow, oz0), (hw - ow, oz0)])
    _quad(g, st, [(-ow, -hd, oz1), (ow, -hd, oz1), (ow, -hd, z1), (-ow, -hd, z1)],
          [(hw - ow, oz1), (hw + ow, oz1), (hw + ow, z1), (hw - ow, z1)])
    u = 2 * hw
    for p, q in ((B, C), (C, D), (D, A)):
        u = _stone_wall(g, p, q, 0.0, z1, u)
    # the firebox: stone reveal (60 mm), then firebrick; a dark throat above
    rv = 0.06
    yb = -hd + od
    fb = 'fireplace_firebrick'
    for sx in (-1, 1):
        x = sx * ow
        pr = [(x, -hd, oz0), (x, -hd + rv, oz0), (x, -hd + rv, oz1), (x, -hd, oz1)]
        pb = [(x, -hd + rv, oz0), (x, yb, oz0), (x, yb, oz1), (x, -hd + rv, oz1)]
        if sx > 0:
            pr, pb = pr[::-1], pb[::-1]
        _quad(g, st, pr, [(p[1], p[2]) for p in pr])
        _quad(g, fb, pb, [(p[1], p[2]) for p in pb])
    _quad(g, st, [(-ow, -hd, oz1), (-ow, -hd + rv, oz1), (ow, -hd + rv, oz1), (ow, -hd, oz1)],
          [(-ow, 0), (-ow, rv), (ow, rv), (ow, 0)])
    _quad(g, 'fireplace_soot', [(-ow, -hd + rv, oz1), (-ow, yb, oz1), (ow, yb, oz1), (ow, -hd + rv, oz1)],
          [(-ow, rv), (-ow, od), (ow, od), (ow, rv)])
    _quad(g, fb, [(-ow, yb, oz0), (ow, yb, oz0), (ow, yb, oz1), (-ow, yb, oz1)],
          [(-ow, oz0), (ow, oz0), (ow, oz1), (-ow, oz1)])
    _quad(g, fb, [(-ow, -hd + rv, oz0), (ow, -hd + rv, oz0), (ow, yb, oz0), (-ow, yb, oz0)],
          [(-ow, rv), (ow, rv), (ow, od), (-ow, od)])
    _quad(g, st, [(-ow, -hd, oz0), (ow, -hd, oz0), (ow, -hd + rv, oz0), (-ow, -hd + rv, oz0)],
          [(-ow, 0), (ow, 0), (ow, rv), (-ow, rv)])
    # tier 2: battered shoulders up to a ledge round the chimney
    tw, tf = 0.55, -hd + 0.035
    A2, B2, C2, D2 = (-tw, tf), (tw, tf), (tw, hd), (-tw, hd)
    u = 0.0
    for (p, q), (p2, q2) in zip(((A, B), (B, C), (C, D), (D, A)), ((A2, B2), (B2, C2), (C2, D2), (D2, A2))):
        u = _stone_wall(g, p, q, z1, z2, u, p2, q2)
    cw, cf = 0.375, hd - 0.75
    g.poly(st, [(-tw, tf, z2), (tw, tf, z2), (tw, hd, z2), (-tw, hd, z2)])
    # chimney
    A3, B3, C3, D3 = (-cw, cf), (cw, cf), (cw, hd), (-cw, hd)
    u = hw - cw
    for p, q in ((A3, B3), (B3, C3), (C3, D3), (D3, A3)):
        u = _stone_wall(g, p, q, z2, z3, u)
    g.poly(st, [(-cw, cf, z3), (cw, cf, z3), (cw, hd, z3), (-cw, hd, z3)])
    # proud stones
    if relief:
        fr = int(relief * 0.26)
        _stones(g, rng, A, B, 0.0, z1, 0.0, fr, skip=(hw - ow, hw + ow, oz0, oz1))
        _stones(g, rng, B, C, 0.0, z1, 2 * hw, int(relief * 0.14))
        _stones(g, rng, D, A, 0.0, z1, 4 * hw + 2 * hd, int(relief * 0.14))
        _stones(g, rng, C, D, 0.0, z1, 2 * hw + 2 * hd, int(relief * 0.10))
        per = hw - cw
        _stones(g, rng, A3, B3, z2, z3, per, int(relief * 0.10))
        _stones(g, rng, B3, C3, z2, z3, per + 2 * cw, int(relief * 0.10))
        _stones(g, rng, D3, A3, z2, z3, per + 4 * cw + 0.75, int(relief * 0.10))
        _stones(g, rng, C3, D3, z2, z3, per + 2 * cw + 0.75, int(relief * 0.06))
    # cap: a dark screen box and a low pyramidal lid
    cy = (cf + hd) / 2
    g.box('furn_bronze', (-0.27, cy - 0.27, z3), (0.27, cy + 0.27, z3 + 0.13), faces='xXyY')
    e, zl = 0.40, z3 + 0.13
    g.box('furn_bronze', (-e, cy - e, zl), (e, cy + e, zl + 0.022), faces='xXyYz')
    apex = (0.0, cy, zl + 0.022 + 0.08)
    c4 = [(-e, cy - e, zl + 0.022), (e, cy - e, zl + 0.022), (e, cy + e, zl + 0.022), (-e, cy + e, zl + 0.022)]
    for i in range(4):
        g.poly('furn_bronze', [c4[i], c4[(i + 1) % 4], apex])
    return _place(geo, g, at, heading_deg)


# =====================================================================================================================
# CABANA TERRACE (p27, seg123, seg141, p30)
# =====================================================================================================================
def fire_bowl(geo, at, diameter=1.18, height=0.33):
    """The round white fire table on the cabana terrace (p27): a low cast-concrete drum 1.18 m across and 0.28 m
    deep, floating 50 mm above the paving on a recessed dark plinth, with a dark lava-rock pan sunk in its top.
    ~430 triangles."""
    g = Geo()
    R, H, e = diameter / 2, height, 0.035
    zb = 0.05
    _revolve(g, 'firebowl_concrete', [(0.38, zb), (R - e, zb), (R - 0.01, zb + 0.012), (R, zb + e), (R, H - e),
                                      (R - 0.01, H - 0.012), (R - e, H), (R - 0.115, H), (R - 0.115, H - 0.035)], n=28)
    _revolve(g, 'firebowl_media', [(R - 0.115, H - 0.035), (0.0, H - 0.03)], n=28)
    _revolve(g, BLACK, [(0.40, 0.0), (0.40, zb)], n=20)
    return _place(geo, g, at, 0.0)


def _lounge_frame(g, W, D, s=0.035, arm=0.60):
    """Square-tube sled frame of the cabana lounge pieces: two closed side loops with wood-capped arms, seat rails
    and a raked back frame."""
    hw, hd = W / 2, D / 2
    for sx in (-1, 1):
        x0, x1 = sorted((sx * hw, sx * (hw - s)))
        g.box(BLACK, (x0, -hd, 0.0), (x1, -hd + s, arm), faces='xXyY')
        g.box(BLACK, (x0, hd - s, 0.0), (x1, hd, arm), faces='xXyY')
        g.box(BLACK, (x0, -hd + s, 0.0), (x1, hd - s, s), faces='xXZ')
        g.box(BLACK, (x0, -hd, arm - s), (x1, hd, arm), faces='xXyYz')
        xc = sx * (hw - s / 2)
        _board(g, TAUPE, (xc - 0.027, -hd - 0.004, arm), (xc + 0.027, hd - 0.17, arm + 0.018), grain=1,
               faces='xXyYZ', uvo=(sx * 0.4, 0.1))
        # raked back upright
        xu = sx * (hw - s - s / 2)
        _bar(g, BLACK, (xu, 0.235, 0.30), (xu, 0.385, 0.75), s, s, up=(0, 1, 0))
    g.box(BLACK, (-hw + s, -hd + 0.035, 0.265), (hw - s, -hd + 0.035 + s, 0.30), faces='yYzZ')
    g.box(BLACK, (-hw + s, 0.215, 0.265), (hw - s, 0.215 + s, 0.30), faces='yYzZ')
    g.box(BLACK, (-hw + s, -hd + 0.07, 0.285), (hw - s, 0.215, 0.295), faces='zZ')
    _bar(g, BLACK, (-hw + s, 0.385, 0.75), (hw - s, 0.385, 0.75), s, s)


def lounge_sofa(geo, at, heading_deg=0.0, seats=2, seed=0, pillows=True):
    """Dark-framed lounge seat of the cabana terrace (p27, seg123): a near-black square-tube sled frame with
    wood-capped arms at 0.60 m, dark-grey seat cushions (top 0.44 m), big back cushions to ~0.88 m and white throw
    pillows.  seats = 2 -> the 1.44 m loveseat, 1 -> the 0.78 m armchair; 0.80 m deep.  Faces local -y.
    ~1500 triangles for the loveseat, ~850 for the chair."""
    g = Geo()
    rng = np.random.default_rng(5000 + seed + seats)
    W = 0.78 if seats == 1 else 0.12 + 0.66 * seats
    D, s = 0.80, 0.035
    _lounge_frame(g, W, D, s)
    sw = (W - 2 * s - 0.012) / seats
    fm, fe = 'furn_fabric_charcoal', 'furn_fabric_charcoal_edge'
    for i in range(seats):
        x = (i - (seats - 1) / 2) * sw
        _cushion(g, fm, _rrect(sw / 2 - 0.004, 0.325, 0.045) + [x, -0.05], 0.295, 0.13, r=0.04, crown=0.016,
                 edge_mat=fe, uvo=rng.random(2))
        _cushion(g, fm, _rrect(sw / 2 - 0.012, 0.245, 0.06), 0.0, 0.17, r=0.055, crown=0.035, edge_mat=fe,
                 bottom=True, uvo=rng.random(2), R=_lean(17.0 + rng.uniform(-2, 2), rng.uniform(-2, 2)),
                 t=(x, 0.305, 0.415 + 0.235))
        if pillows:
            _pillow(g, 'furn_fabric_white', 0.44, 0.44, 0.14,
                    R=_lean(26.0 + rng.uniform(-4, 6), rng.uniform(-22, 22), rng.uniform(-14, 14)),
                    at=(x + rng.uniform(-0.08, 0.08), 0.10, 0.64), uvo=rng.random(2))
    return _place(geo, g, at, heading_deg)


def lounge_chair(geo, at, heading_deg=0.0, seed=0, pillows=True):
    """The single armchair of the cabana lounge set (see lounge_sofa): 0.78 x 0.80 m."""
    return lounge_sofa(geo, at, heading_deg, seats=1, seed=seed, pillows=pillows)


def lounge_table(geo, at, heading_deg=0.0, length=1.14, width=0.60, height=0.43):
    """Coffee table of the cabana lounge set (p27, seg123): 1.14 x 0.60 m, 0.43 m high; a weathered teak-look slab
    on a near-black square-tube frame with closed sled loops at both ends.  Local x = the long axis.
    ~130 triangles."""
    g = Geo()
    L, W, H, s = length, width, height, 0.035
    zt = H - 0.026
    for sx in (-1, 1):
        x0, x1 = sorted((sx * L / 2, sx * (L / 2 - s)))
        for sy in (-1, 1):
            y0, y1 = sorted((sy * W / 2, sy * (W / 2 - s)))
            g.box(BLACK, (x0, y0, 0.0), (x1, y1, zt), faces='xXyY')
        g.box(BLACK, (x0, -W / 2 + s, 0.0), (x1, W / 2 - s, s), faces='xXZ')
        g.box(BLACK, (x0, -W / 2 + s, zt - s), (x1, W / 2 - s, zt), faces='xXz')
    for sy in (-1, 1):
        y0, y1 = sorted((sy * W / 2, sy * (W / 2 - s)))
        g.box(BLACK, (-L / 2 + s, y0, zt - s), (L / 2 - s, y1, zt), faces='yYz')
    _board(g, TAUPE, (-L / 2 - 0.004, -W / 2 - 0.004, zt), (L / 2 + 0.004, W / 2 + 0.004, H), grain=0,
           faces='xXyYzZ', uvo=(0.3, 0.7))
    return _place(geo, g, at, heading_deg)


def woven_chair(geo, at, heading_deg=0.0, seed=0):
    """Round rope 'hoop' chair of the cabana's side terrace (p27 right, seg141): a light-hardwood seat ring (0.66 m
    across, 0.37 m up) on four splayed tapered legs, a big reclined wooden hoop (0.88 x 0.56 m, top 0.78 m) filled
    with a fan of grey rope as the back, wooden arms sweeping down to the front legs and a round pale seat pad.
    Footprint ~0.92 x 1.02 m.  Faces local -y.  ~1050 triangles."""
    g = Geo()
    rng = np.random.default_rng(6000 + seed)
    zs, rs, ys = 0.37, 0.33, -0.08
    ring = np.column_stack([_circle(rs, 16, (0.0, ys)), np.full(16, zs)])
    _tube(g, LIGHTWOOD, ring, 0.017, n=6, closed=True)
    tau = np.radians(48.0)
    v = np.array([0.0, np.sin(tau), np.cos(tau)])
    A_, B_ = 0.44, 0.28
    Cc = np.array([0.0, 0.19, 0.405]) + B_ * v
    th = np.linspace(0, 2 * np.pi, 18, endpoint=False)
    hoop = np.array([Cc + A_ * np.cos(t) * np.array([1.0, 0, 0]) + B_ * np.sin(t) * v for t in th])
    _tube(g, LIGHTWOOD, hoop, 0.018, n=6, closed=True)
    # the rope fan: a slightly dished surface inside the hoop, both faces
    nrm = np.cross([1.0, 0, 0], v)                       # points to the back / down
    ctr = Cc + 0.05 * nrm - 0.10 * v
    V = np.vstack([hoop, hoop[:1], [ctr] * 19])
    rad = np.linalg.norm(hoop - ctr, axis=1).mean()
    UVw = np.vstack([np.stack([np.linspace(0, 1.6, 19), np.full(19, rad)], -1),
                     np.stack([np.linspace(0, 1.6, 19), np.zeros(19)], -1)])
    Fw = [[i, i + 1, 19 + i] for i in range(18)]
    for sgn in (-1.0, 1.0):
        _add(g, 'furn_rope', V + sgn * 0.002 * nrm, np.tile(sgn * nrm, (len(V), 1)), UVw, Fw)
    # legs and arms
    for sx in (-1, 1):
        _tube(g, LIGHTWOOD, [(sx * 0.27, ys - 0.20, zs + 0.01), (sx * 0.315, ys - 0.30, 0.0)], [0.02, 0.0135], n=6)
        _tube(g, LIGHTWOOD, [(sx * 0.24, ys + 0.23, zs + 0.01), (sx * 0.29, ys + 0.40, 0.0)], [0.02, 0.0135], n=6)
        side = Cc + sx * A_ * 0.985 * np.array([1.0, 0, 0]) + 0.05 * v
        mid = (side + np.array([sx * 0.30, ys - 0.21, zs + 0.02])) / 2 + np.array([sx * 0.06, -0.02, 0.07])
        _tube(g, LIGHTWOOD, [side, mid, (sx * 0.275, ys - 0.215, zs + 0.01)], [0.016, 0.017, 0.018], n=5, caps=False)
    g.poly('furn_rope', [(p[0], p[1], zs + 0.012) for p in _circle(rs - 0.01, 12, (0.0, ys))])
    _cushion(g, 'cushion', _circle(0.30, 16, (0.0, ys)), zs + 0.014, 0.065, r=0.03, crown=0.015,
             edge_mat='cushion_edge', uvo=rng.random(2))
    return _place(geo, g, at, heading_deg)


def drum_table(geo, at, diameter=0.38, height=0.46):
    """Small glazed white drum side table / garden stool between the hoop chairs (p27, seg141).  ~200 triangles."""
    g = Geo()
    R, H = diameter / 2, height
    _revolve(g, 'furn_ceramic_white', [(0.0, 0.0), (R * 0.74, 0.0), (R * 0.93, H * 0.10), (R, H * 0.32),
                                       (R, H * 0.68), (R * 0.93, H * 0.90), (R * 0.74, H), (0.0, H)], n=16,
             crease_deg=50.0)
    return _place(geo, g, at, 0.0)


def outdoor_rug(geo, at, heading_deg=0.0, size=(2.40, 1.70)):
    """Flat-woven outdoor rug under the cabana loveseat and table (seg123): size = (local x, local y), 8 mm thick.
    The 'rug_diamond' texture (border + diamond lattice) is laid ONCE over the rug, whatever its size."""
    g = Geo()
    a, b = size[0] / 2, size[1] / 2
    P = [(-a, -b, 0.008), (a, -b, 0.008), (a, b, 0.008), (-a, b, 0.008)]
    _quad(g, 'rug_diamond', P, [(0, 0), (2.4, 0), (2.4, 1.7), (0, 1.7)])
    g.box('rug_diamond', (-a, -b, 0.0), (a, b, 0.008), faces='xXyY')
    return _place(geo, g, at, heading_deg)


def door_mat(geo, at, heading_deg=0.0, size=(0.90, 0.55)):
    """Coir door mat, 18 mm thick: size = (along the door, depth)."""
    g = Geo()
    a, b = size[0] / 2, size[1] / 2
    g.box('doormat_coir', (-a, -b, 0.0), (a, b, 0.018), faces='xXyYZ')
    return _place(geo, g, at, heading_deg)


# =====================================================================================================================
# YARD EQUIPMENT, POTS
# =====================================================================================================================
def _fan_panel(g, x0, x1, z0, z1, y, r, n=16):
    """A front-panel cell (plane y, looking at -y) with a round fan opening: the sheet round it, the opening's wall
    (30 mm deep) and the fan disc behind (texture 'condenser_fan' laid once over the disc's square)."""
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    a, b = (x1 - x0) / 2, (z1 - z0) / 2
    ca = np.arctan2(b, a)
    base = [ca, np.pi - ca, np.pi + ca, 2 * np.pi - ca]
    ang = []
    for i in range(4):
        a0, a1 = base[i], base[(i + 1) % 4] + (2 * np.pi if i == 3 else 0.0)
        ang += list(a0 + (a1 - a0) * np.arange(n // 4) / (n // 4))
    ang = np.array(ang)
    c, s = np.cos(ang), np.sin(ang)
    k = np.minimum(a / np.maximum(np.abs(c), 1e-9), b / np.maximum(np.abs(s), 1e-9))
    outer = np.stack([cx + c * k, np.full(n, y), cz + s * k], -1)
    inner = np.stack([cx + c * r, np.full(n, y), cz + s * r], -1)
    back = inner + [0.0, 0.03, 0.0]
    nf = np.array([0.0, -1.0, 0.0])
    m = 'condenser_white'
    V = np.vstack([outer, inner])
    F = []
    for i in range(n):
        j = (i + 1) % n
        F += [[i, j, n + j], [i, n + j, n + i]]
    _add(g, m, V, np.tile(nf, (2 * n, 1)), V[:, [0, 2]], F)
    Vw = np.vstack([inner, back])
    Nw = np.tile(np.stack([-c, np.zeros(n), -s], -1), (2, 1))
    _add(g, m, Vw, Nw, np.stack([np.tile(ang * r, 2), np.repeat([0.0, 0.03], n)], -1), F)
    Vd = np.vstack([[[cx, y + 0.03, cz]], back])
    UVd = np.stack([(Vd[:, 0] - cx) / (2 * r) + 0.5, (Vd[:, 2] - cz) / (2 * r) + 0.5], -1)
    _add(g, 'condenser_fan', Vd, np.tile(nf, (n + 1, 1)), UVd, [[0, 1 + i, 1 + (i + 1) % n] for i in range(n)])


def condenser(geo, at, heading_deg=0.0, fans=2, width=0.95, depth=0.36, height=None):
    """Side-discharge heat-pump / AC condenser (p26, right of the rear wall): an off-white sheet-metal cabinet with
    `fans` round fan openings stacked on its front (2 -> 0.95 x 0.36 x 1.34 m, 1 -> 0.70 m high), a service cover
    down its right side, on two rails over a concrete pad.  The grilles face local -y; `at` = the footprint's
    middle.  ~330 triangles with two fans."""
    g = Geo()
    m = 'condenser_white'
    W, D = width, depth
    H = height or (0.67 * fans)
    zf = 0.09
    hw, hd = W / 2, D / 2
    cell = (W - 0.16)                                    # the fans sit left of the service cover
    for i in range(fans):
        _fan_panel(g, -hw, -hw + cell, zf + i * H / fans, zf + (i + 1) * H / fans, -hd, min(cell, H / fans) / 2 - 0.045)
    g.box(m, (-hw + cell + 0.004, -hd - 0.006, zf + 0.01), (hw, -hd, zf + H - 0.01), faces='xyzZX')
    g.box(m, (-hw + cell, -hd, zf), (hw, -hd + 0.001, zf + H), faces='y')
    g.box(m, (-hw, -hd, zf), (hw, hd, zf + H), faces='xXYZz')
    g.box(m, (-hw - 0.004, -hd - 0.004, zf + H), (hw + 0.004, hd + 0.004, zf + H + 0.012), faces='xXyYZ')
    for sx in (-1, 1):
        x0, x1 = sorted((sx * (hw - 0.05), sx * (hw - 0.11)))
        g.box('utility_grey', (x0, -hd - 0.03, 0.04), (x1, hd + 0.03, zf), faces='xXyY')
    g.box('concrete', (-hw - 0.08, -hd - 0.10, 0.0), (hw + 0.08, hd + 0.10, 0.04), faces='xXyYZ')
    return _place(geo, g, at, heading_deg)


def equipment_cabinet(geo, at, heading_deg=0.0, size=(1.20, 0.75, 1.15)):
    """Plain off-white equipment enclosure (the pool-equipment cabinet by the left side fence, seg141_040):
    size = (width, depth, height); a lid with a lip, a door seam down the front and a dark plinth.  ~90 triangles."""
    g = Geo()
    w, d, h = size[0] / 2, size[1] / 2, size[2]
    m = 'condenser_white'
    g.box('utility_grey', (-w + 0.02, -d + 0.02, 0.0), (w - 0.02, d - 0.02, 0.06), faces='xXyY')
    g.box(m, (-w, -d, 0.06), (w, d, h - 0.05), faces='xXyYz')
    g.box(m, (-w - 0.015, -d - 0.015, h - 0.05), (w + 0.015, d + 0.015, h), faces='xXyYzZ')
    g.box('utility_grey', (-0.004, -d - 0.002, 0.10), (0.004, -d, h - 0.09), faces='xXy')
    g.box('utility_grey', (0.03, -d - 0.02, h * 0.52), (0.05, -d, h * 0.52 + 0.12), faces='xXyzZ')
    return _place(geo, g, at, heading_deg)


def utility_box(geo, origin, right, out, w=0.13, h=0.17, d=0.075, conduit=0.9, conduit_r=0.011):
    """Grey weatherproof outlet / junction box on a wall (the pair right of the side door in p26).
    Wall frame: origin = the point on the wall's outer face under the box's CENTRE, right = unit vector along the
    wall, out = the wall's outward normal; w x h x d = width, height, projection (m).  A conduit of radius
    conduit_r runs `conduit` metres down from the box (0 = none).  ~80 triangles."""
    o = np.asarray(origin, float)
    ex, ey = _unit(right), _unit(out)
    m = 'utility_grey'
    geo.obox(m, o, ex, ey, UP, (-w / 2, 0.0, -h / 2), (w / 2, d * 0.7, h / 2), faces='xXYzZ')
    geo.obox(m, o, ex, ey, UP, (-w / 2 - 0.006, d * 0.7, -h / 2 - 0.006), (w / 2 + 0.006, d, h / 2 + 0.006),
             faces='xXyYzZ')
    if conduit > 0:
        a = o + ey * (conduit_r + 0.004) - UP * (h / 2)
        _tube(geo, m, [a, a - UP * conduit], conduit_r, n=6, caps=False)
    return geo


def planter(geo, at, diameter=0.55, height=0.50, foot=0.72, mat='furn_plaster_white', soil=True):
    """Round tapered planter / pot: `diameter` at the rim, foot = the base's diameter as a share of it, a 25 mm rim
    and the soil 50 mm below it ('soil').  mat = 'furn_plaster_white' (the white plaster planters) or
    'pot_terracotta' (plain clay pots).  Put the plant in with the plants family.  ~200 triangles."""
    g = Geo()
    R, H = diameter / 2, height
    rb = R * foot
    _revolve(g, mat, [(0.0, 0.0), (rb - 0.01, 0.0), (rb, 0.01), (R, H - 0.02), (R, H), (R - 0.025, H),
                      (R - 0.03, H - 0.05)], n=20)
    if soil:
        _revolve(g, 'soil', [(R - 0.03, H - 0.05), (0.0, H - 0.045)], n=20)
    return _place(geo, g, at, 0.0)


def garden_pot(geo, at, diameter=0.32, height=0.28):
    """A plain terracotta garden pot (see planter)."""
    return planter(geo, at, diameter, height, foot=0.66, mat='pot_terracotta')
