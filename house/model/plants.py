"""Vegetation kit: the great oak, saplings, shrubs, rose bushes, hedges and the backdrop trees.

Every builder is a plain function that ADDS geometry to a Geo you pass in and returns the number of triangles it
added.  All builders are seeded and deterministic (numpy RandomState).

Frame and units (the world of model/kit.py): metres; X right along the street, Y into the lot, Z up.
  base     the point where the stem meets the ground, (x, y, z).
  az       a compass-like heading in degrees, measured CLOCKWISE FROM +Y (into the lot) seen from above, the convention
           of the sun in web/viewer/stage.js: 0 = +Y, 90 = +X (right), 180 = toward the street, 270 = -X.

Materials (looks: web/viewer/looks/plants.js; plain fallbacks registered below):
  bark           furrowed grey-brown bark of the oak and the broadleaf trees   (UV metres, the tile is BARK_TILE)
  bark_young     smooth bark of saplings, shrub stems, rose canes
  bark_redwood   fibrous red-brown conifer bark
  leaf_oak / leaf_green / leaf_gold / leaf_red / leaf_olive / leaf_sapling / leaf_boxwood / leaf_laurel /
  leaf_rose / leaf_conifer      alpha-tested, double-sided foliage CARDS on a 2 x 2 atlas of leaf clusters
  shrub_core     the dark opaque inside of shrubs and hedges (tiling, UV metres)
  stake_wood, plant_tie          the saplings' lodge poles and ties

Foliage cards carry three things in their UVs (decoded by the look module's shaders):
  fract(u), fract(v)   the atlas coordinate (v = 0 at a cell's bottom = the card's ROOT, where it is attached)
  floor(u)             a tint class 0..7 (per-card colour variation)
  floor(v)             a shade class 0..7 (7 = open to the sky, 0 = deep inside the crown)
and their vertex normals are not the cards' own but bent outward from the crown / cluster centre, so a crown is lit
as a volume and the cards do not read as flat crosses.
"""
from __future__ import annotations

import math

import numpy as np

from model import materials as _materials
from model.kit import Geo, UP

BARK_TILE = 1.2          # m: the bark texture repeats every BARK_TILE (plants.js BARK_TILE)
YOUNG_TILE = 0.3         # m: tile of bark_young
ATLAS = (2, 2)           # cells of every foliage atlas (columns, rows); cell k = row-major from the TOP-left
MARGIN = 0.006           # of a cell: cards stay this far inside their cell

for _n, _c, _r in [('bark', (0.115, 0.095, 0.078), 0.95), ('bark_young', (0.13, 0.10, 0.08), 0.85),
                   ('bark_redwood', (0.17, 0.085, 0.055), 0.95), ('shrub_core', (0.012, 0.022, 0.008), 1.0),
                   ('stake_wood', (0.42, 0.31, 0.19), 0.9), ('plant_tie', (0.01, 0.01, 0.01), 0.7)]:
    _materials.register(_n, color=_c, roughness=_r)
for _n, _c in [('leaf_oak', (0.16, 0.14, 0.075)), ('leaf_green', (0.05, 0.11, 0.02)), ('leaf_gold', (0.62, 0.36, 0.03)),
               ('leaf_red', (0.42, 0.03, 0.015)), ('leaf_olive', (0.07, 0.09, 0.035)),
               ('leaf_sapling', (0.07, 0.10, 0.035)), ('leaf_boxwood', (0.03, 0.055, 0.012)),
               ('leaf_laurel', (0.022, 0.04, 0.014)), ('leaf_rose', (0.03, 0.06, 0.02)),
               ('leaf_conifer', (0.02, 0.04, 0.02))]:
    _materials.register(_n, color=_c, roughness=0.8, double=True)

# The oak of the back yard as read from the aerial photo (p30, the provisional scale of survey/frame.json) and p26:
# (az deg, reach m = horizontal distance of the limb's tip from the trunk base, tip height m above the base).
OAK_LIMBS = [
    (-3, 12.4, 10.5),     # north, over the lawn to the pool
    (13, 11.6, 12.0),     # north-north-east, over the pool
    (40, 13.0, 10.0),     # the long north-east limb
    (38, 6.4, 14.5),      # inner, high
    (72, 8.5, 12.5),      # east-north-east, high
    (106, 6.2, 8.5),      # east, over the lawn toward the patio
    (150, 5.0, 13.0),     # south-east, above the roof
    (192, 5.8, 11.0),     # south, over the roof
    (236, 5.4, 9.5),      # south-west
    (262, 8.2, 6.5),      # the low heavy west limbs that leave the lot over the fence
    (288, 8.6, 7.2),
    (322, 10.2, 8.0),     # the heavy north-west limb
    (345, 4.6, 16.0),     # the leader
]


# ---- small maths ----------------------------------------------------------------------------------------------------
def _unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.maximum(n, 1e-12)


def _azv(az, el=0.0):
    """Unit vector of heading az (deg, clockwise from +Y) and elevation el (deg above the horizon)."""
    a, e = math.radians(az), math.radians(el)
    return np.array([math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)])


def _perp(d):
    """A horizontal unit vector perpendicular to d (any, if d is vertical)."""
    h = np.cross(UP, d)
    n = np.linalg.norm(h)
    return h / n if n > 1e-6 else np.array([1.0, 0.0, 0.0])


def _rot(v, axis, ang):
    axis = _unit(axis)
    c, s = math.cos(ang), math.sin(ang)
    return v * c + np.cross(axis, v) * s + axis * (axis @ v) * (1 - c)


def _smooth(x, lo, hi):
    t = np.clip((np.asarray(x, float) - lo) / (hi - lo), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _noise3(rs, t, kink=0.0, octs=((1.2, 1.0), (2.7, 0.5), (5.9, 0.22))):
    """Smooth 3-D wander over t in 0..1 (rows of about unit size): a few sines, plus `kink` x a piecewise-linear
    zigzag (the elbows of old limbs)."""
    t = np.asarray(t, float)
    out = np.zeros((len(t), 3))
    for f, a in octs:
        ph = rs.uniform(0, 2 * math.pi, 3)
        fr = f * rs.uniform(0.75, 1.3, 3)
        out += a * np.sin(2 * math.pi * fr[None] * t[:, None] + ph[None])
    if kink > 0:
        m = max(3, len(t) // 5)
        kn = rs.normal(size=(m + 2, 3))
        x = t * m
        i0 = np.minimum(x.astype(int), m)
        f = (x - i0)[:, None]
        out += kink * (kn[i0] * (1 - f) + kn[i0 + 1] * f)
    return out


# ---- output buffers --------------------------------------------------------------------------------------------------
class _Buf:
    def __init__(self):
        self.V, self.N, self.UV, self.F, self.n = [], [], [], [], 0

    def add(self, V, N, UV, F):
        V = np.asarray(V, float).reshape(-1, 3)
        self.V.append(V)
        self.N.append(np.asarray(N, float).reshape(-1, 3))
        self.UV.append(np.asarray(UV, float).reshape(-1, 2))
        self.F.append(np.asarray(F, int).reshape(-1, 3) + self.n)
        self.n += len(V)

    @property
    def ntri(self):
        return sum(len(f) for f in self.F)


class _Out:
    """Collects the meshes of one plant (per material) and writes them into the Geo in one go."""

    def __init__(self):
        self.b = {}

    def __getitem__(self, mat):
        if mat not in self.b:
            self.b[mat] = _Buf()
        return self.b[mat]

    @property
    def ntri(self):
        return sum(b.ntri for b in self.b.values())

    def flush(self, geo: Geo):
        n = 0
        for mat, b in self.b.items():
            if b.n:
                geo.mesh(mat).add(np.vstack(b.V), np.vstack(b.N), np.vstack(b.UV), np.vstack(b.F))
                n += b.ntri
        return n


# ---- tubes -----------------------------------------------------------------------------------------------------------
class _Ax:
    """One axis of a branching skeleton: a centreline P (n, 3) with radii R (n,), its level and arc lengths S."""

    def __init__(self, P, R, lvl=0):
        self.P = np.asarray(P, float)
        self.R = np.asarray(R, float)
        self.lvl = lvl
        self.S = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(self.P, axis=0), axis=1))])

    @property
    def L(self):
        return float(self.S[-1])

    def at(self, s):
        """Point, unit tangent and radius at arc length s."""
        s = float(np.clip(s, 0.0, self.S[-1]))
        i = int(min(np.searchsorted(self.S, s, side='right') - 1, len(self.P) - 2))
        f = (s - self.S[i]) / max(self.S[i + 1] - self.S[i], 1e-9)
        return (self.P[i] * (1 - f) + self.P[i + 1] * f, _unit(self.P[i + 1] - self.P[i]),
                float(self.R[i] * (1 - f) + self.R[i + 1] * f))


def _frames(P):
    """Tangents and a twist-free pair of normals along a polyline (parallel transport)."""
    n = len(P)
    T = np.zeros((n, 3))
    T[1:-1] = P[2:] - P[:-2]
    T[0], T[-1] = P[1] - P[0], P[-1] - P[-2]
    T = _unit(T)
    U = np.zeros((n, 3))
    U[0] = _perp(T[0])
    for i in range(1, n):
        u = U[i - 1] - T[i] * (U[i - 1] @ T[i])
        k = np.linalg.norm(u)
        U[i] = u / k if k > 1e-9 else _perp(T[i])
    return T, U, np.cross(T, U)


def _nseg(r):
    return 22 if r > 0.42 else 16 if r > 0.24 else 12 if r > 0.13 else 9 if r > 0.07 else 7 if r > 0.035 else \
        5 if r > 0.016 else 4


def _tube(buf, P, R, nseg=None, rs=None, tile=BARK_TILE, lump=0.0, shape=None, tip=True, v0=None):
    """Tapering tube round the centreline P with radii R, smooth normals, bark UVs in metres (u round the stem: a
    whole number of tiles, v along it).  lump: relative size of the stem's lobes and swellings; shape(theta, s):
    extra radius factor (n_rings, n_seg + 1) - the root flare; tip: close the far end with a point."""
    P, R = np.asarray(P, float), np.asarray(R, float)
    m = len(P)
    if m < 2:
        return
    if nseg is None:
        nseg = _nseg(float(R.max()))
    T, U, W = _frames(P)
    S = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    th = np.linspace(0, 2 * math.pi, nseg + 1)
    rad = np.repeat(R[:, None], nseg + 1, 1)
    if lump > 0 and rs is not None:
        g = np.zeros((m, nseg + 1))
        rm = max(float(R.mean()), 1e-3)
        for k, a in ((2, 1.0), (3, 0.7), (5, 0.45)):
            ph, w = rs.uniform(0, 2 * math.pi), rs.uniform(0.25, 0.9) / (3.0 * rm + 0.1)
            g += a * np.sin(k * th[None, :] + ph + np.sin(w * S[:, None] + rs.uniform(0, 6)) * 1.6)
        g += 0.8 * np.sin(S[:, None] * rs.uniform(1.2, 2.2) / (2.0 * rm + 0.12) + rs.uniform(0, 6))   # swellings
        g[:, -1] = g[:, 0]
        rad = rad * (1 + lump * g / 2.2)
    if shape is not None:
        rad = rad * shape(th, S)
    V = P[:, None, :] + rad[:, :, None] * (np.cos(th)[None, :, None] * U[:, None, :] +
                                            np.sin(th)[None, :, None] * W[:, None, :])
    # smooth normals from the grid (wrapping round the stem)
    dth = np.zeros_like(V)
    dth[:, 1:-1] = V[:, 2:] - V[:, :-2]
    dth[:, 0] = dth[:, -1] = V[:, 1] - V[:, -2]
    ds = np.zeros_like(V)
    ds[1:-1] = V[2:] - V[:-2]
    ds[0], ds[-1] = V[1] - V[0], V[-1] - V[-2]
    N = _unit(np.cross(dth, ds))
    radial = _unit(V - P[:, None, :])
    N = np.where((np.einsum('ijk,ijk->ij', N, radial) < 0.2)[:, :, None], radial, N)
    nrep = max(1, int(round(2 * math.pi * float(np.median(R)) / tile)))
    if v0 is None:
        v0 = rs.uniform(0, 7.0) if rs is not None else 0.0
    UV = np.stack([np.repeat((th / (2 * math.pi) * nrep * tile)[None, :], m, 0),
                   np.repeat((v0 + S)[:, None], nseg + 1, 1)], -1)
    i, j = np.meshgrid(np.arange(m - 1), np.arange(nseg), indexing='ij')
    a = (i * (nseg + 1) + j).ravel()
    b, c, d = a + 1, a + nseg + 1, a + nseg + 2
    F = np.concatenate([np.stack([a, b, d], -1), np.stack([a, d, c], -1)])
    V, N, UV = V.reshape(-1, 3), N.reshape(-1, 3), UV.reshape(-1, 2)
    if tip:                                             # a point just beyond the last ring
        apex = P[-1] + T[-1] * R[-1] * 0.8
        o = len(V)
        last = (m - 1) * (nseg + 1) + np.arange(nseg)
        F = np.concatenate([F, np.stack([last, last + 1, np.full(nseg, o)], -1)])
        V = np.vstack([V, apex])
        N = np.vstack([N, T[-1]])
        UV = np.vstack([UV, [nrep * tile * 0.5, v0 + S[-1] + R[-1]]])
    buf.add(V, N, UV, F)


def _path(rs, p0, d0, L, step, wig=0.3, lift=0.0, droop=0.0, kink=0.0, pull=None, pull_k=0.0):
    """A free-growing branch: starts at p0 along d0, wanders (wig, kink), turns up (lift) or sags (droop) along its
    length, optionally toward the unit vector `pull`."""
    n = max(2, int(math.ceil(L / step)))
    t = np.linspace(0, 1, n + 1)[1:]
    D = np.asarray(d0, float)[None] + wig * _noise3(rs, t, kink) * _smooth(t, 0.0, 0.25)[:, None]
    D[:, 2] += lift * t - droop * t * t
    if pull is not None:
        D += pull_k * t[:, None] * np.asarray(pull, float)[None]
    P = np.asarray(p0, float) + np.cumsum(_unit(D), 0) * (L / n)
    return np.vstack([p0, P])


def _limb_path(rs, S0, T1, t0, t1, step, wig=0.06, kink=0.6):
    """A directed limb from S0 to (about) T1: a cubic that leaves along t0 and arrives along t1, with a meander of
    wig x its length and the elbows of an old limb."""
    S0, T1 = np.asarray(S0, float), np.asarray(T1, float)
    L = float(np.linalg.norm(T1 - S0))
    n = max(3, int(math.ceil(L * 1.12 / step)))
    t = np.linspace(0, 1, n + 1)
    c1, c2 = S0 + _unit(t0) * L * 0.36, T1 - _unit(t1) * L * 0.30
    B = ((1 - t) ** 3)[:, None] * S0 + (3 * (1 - t) ** 2 * t)[:, None] * c1 + (3 * (1 - t) * t * t)[:, None] * c2 + \
        (t ** 3)[:, None] * T1
    W = _noise3(rs, t, kink)
    W[:, 2] *= 0.6
    return B + wig * L * W * (_smooth(t, 0.0, 0.18) * (1 - 0.25 * t))[:, None]


def _taper(S, r0, r1, gamma=1.0, collar=0.0):
    """Radii along arc lengths S: r0 at the base to r1 at the tip; collar: the swelling where a branch leaves."""
    L = max(float(S[-1]), 1e-6)
    r = r1 + (r0 - r1) * (1 - S / L) ** gamma
    if collar > 0:
        r = r * (1 + collar * np.exp(-S / max(1.6 * r0, 0.05)))
    return r


def _children(rs, ax, s0, s1, spacing, length, angle=(45, 75), rmax=0.72, rk=0.021, rexp=1.15, r_tip=0.012,
              step=0.25, wig=0.45, lift=0.25, droop=0.0, kink=0.5, up_bias=0.6, gamma=1.0, lvl=None):
    """Side branches of an axis between arc lengths s0 and s1: one every `spacing` (m, jittered), each leaving at
    `angle` degrees off the axis, in turn round it but preferring the sides and the top (up_bias);
    length(s, remaining length of the parent) -> the branch's length."""
    out = []
    s = s0 + spacing * rs.uniform(0.2, 0.9)
    phi = rs.uniform(0, 2 * math.pi)
    while s < s1:
        p, t, r = ax.at(s)
        phi += 2.4 + rs.uniform(-0.6, 0.6)                       # the golden angle, loosely
        side = _perp(t)
        upv = np.cross(t, side)
        if upv[2] < 0:
            upv = -upv
        d = math.cos(phi) * side + math.sin(phi) * upv
        if d[2] < -0.25 and rs.uniform() < up_bias:
            d = d - 2 * upv * (d @ upv)                          # flip a downward start to the upper side
        a = math.radians(rs.uniform(*angle))
        d0 = _unit(t * math.cos(a) + d * math.sin(a))
        Lc = float(length(s, ax.L - s))
        if Lc > 0.25:
            P = _path(rs, p, d0, Lc, step, wig=wig, lift=lift, droop=droop, kink=kink)
            ch = _Ax(P, P[:, 0], (ax.lvl + 1) if lvl is None else lvl)
            r0 = min(rmax * r, rk * Lc ** rexp)
            ch.R = _taper(ch.S, max(r0, r_tip * 1.2), r_tip, gamma, collar=0.35)
            out.append(ch)
        s += spacing * rs.uniform(0.6, 1.45)
    return out


# ---- foliage cards ---------------------------------------------------------------------------------------------------
def _card(buf, root, axis, side, L, W, cell, tint, shade, nfn, droop=0.0, rows=1, flip=False, w0=1.0, curl=0.0):
    """One foliage card: from `root` along the unit vector `axis` (length L), W wide along `side`; rows > 1 bends it
    (droop: sag in m per m^2 of length; curl: the same along the card's own normal).  cell: atlas cell 0..3, tint and
    shade: classes 0..7 (see the module docstring); nfn(points) -> their shading normals."""
    nx, ny = ATLAS
    ci, rj = cell % nx, cell // nx
    t = np.linspace(0, 1, rows + 1)
    nrm = _unit(np.cross(axis, side))
    c = root[None] + np.outer(t * L, axis) - np.outer(droop * (t * L) ** 2, UP) + np.outer(curl * (t * L) ** 2, nrm)
    w = W * (w0 + (1 - w0) * np.minimum(t * 3, 1.0)) * 0.5
    V = np.concatenate([c - w[:, None] * side[None], c + w[:, None] * side[None]])
    fu = np.concatenate([np.zeros(rows + 1), np.ones(rows + 1)])
    if flip:
        fu = 1 - fu
    fv = np.concatenate([t, t])
    u = (ci + MARGIN + fu * (1 - 2 * MARGIN)) / nx + int(tint)
    v = 1 - (rj + 1) / ny + (MARGIN + fv * (1 - 2 * MARGIN)) / ny + int(shade)
    k = np.arange(rows)
    a, b = k, k + rows + 1
    F = np.concatenate([np.stack([a, b, b + 1], -1), np.stack([a, b + 1, a + 1], -1)])
    buf.add(V, nfn(V), np.stack([u, v], -1), F)


def _round_normals(centre, squash=1.0, up=0.0):
    """Shading normals of a crown: outward from `centre` (z squashed for flat crowns), lifted by `up`."""
    centre = np.asarray(centre, float)

    def f(V):
        d = V - centre
        d = d * np.array([1.0, 1.0, squash])
        d = _unit(d)
        d[:, 2] += up
        return _unit(d)
    return f


def _blob(buf, centre, radii, rs, nu=9, nv=5, lump=0.18, tile=0.5, zmin=None):
    """A lumpy ellipsoid (the dark inside of a shrub), smooth normals, UV metres; zmin cuts it at the ground."""
    cx, cy, cz = centre
    az = np.linspace(0, 2 * math.pi, nu + 1)
    el = np.linspace(-0.5 * math.pi, 0.5 * math.pi, nv + 1)
    A, E = np.meshgrid(az, el)
    g = 1 + lump * (np.sin(3 * A + rs.uniform(0, 6)) * np.cos(2 * E + rs.uniform(0, 6)) * 0.6 +
                    np.sin(5 * A + rs.uniform(0, 6) + 2 * E) * 0.4)
    g[:, -1] = g[:, 0]
    d = np.stack([np.cos(E) * np.sin(A), np.cos(E) * np.cos(A), np.sin(E)], -1)
    V = np.array(centre, float) + d * np.array(radii, float) * g[..., None]
    if zmin is not None:
        V[..., 2] = np.maximum(V[..., 2], zmin)
    N = _unit(d / np.array(radii, float))
    r = float(max(radii[0], radii[1]))
    UV = np.stack([A * r, (E + 0.5 * math.pi) * radii[2]], -1)
    i, j = np.meshgrid(np.arange(nv), np.arange(nu), indexing='ij')
    a = (i * (nu + 1) + j).ravel()
    b, c, dd = a + 1, a + nu + 1, a + nu + 2
    F = np.concatenate([np.stack([a, b, dd], -1), np.stack([a, dd, c], -1)])
    buf.add(V.reshape(-1, 3), N.reshape(-1, 3), UV.reshape(-1, 2), F)


def _shell_cards(buf, rs, centre, radii, n, size, cells, nfn, tilt=0.9, zmin=0.02, shade=(3, 7), out_bias=0.0,
                 top=1.0, tints=8):
    """n small cards scattered over an ellipsoid shell (centre, radii): each lies loosely on the surface (tilted by up
    to `tilt` rad), random roll.  cells: atlas cells to draw from; shade: class at the bottom .. at the top."""
    centre, radii = np.asarray(centre, float), np.asarray(radii, float)
    k = np.arange(n) + 0.5
    z = 1 - (k / n) * (1 + top)                 # top (1) down to -top
    z = np.clip(z + rs.uniform(-0.06, 0.06, n), -1, 1)
    ph = k * 2.399963 + rs.uniform(0, 6.28) + rs.uniform(-0.3, 0.3, n)
    rr = np.sqrt(np.maximum(1 - z * z, 0))
    D = np.stack([rr * np.cos(ph), rr * np.sin(ph), z], -1)
    for i in range(n):
        d = D[i]
        p = centre + d * radii * (1.0 + out_bias + rs.uniform(-0.12, 0.08))
        s = size * rs.uniform(0.75, 1.3)
        nrm = _unit(d / radii)
        ax = _unit(_rot(np.cross(nrm, _perp(nrm)), nrm, rs.uniform(0, 6.28)))
        # tilt the card out of the tangent plane (about its own width), so its tip sticks out of the shell
        side = np.cross(nrm, ax)
        ax = _unit(_rot(ax, side, -rs.uniform(0.15, tilt)))
        root = p - ax * s * 0.5
        if root[2] < zmin:
            root[2] = zmin
        if (root + ax * s)[2] < zmin:
            continue
        sh = int(round(shade[0] + (shade[1] - shade[0]) * _smooth(d[2], -0.5, 0.7))) + rs.randint(-1, 2)
        _card(buf, root, ax, side, s, s, cells[rs.randint(len(cells))], rs.randint(tints), int(np.clip(sh, 0, 7)),
              nfn, flip=rs.uniform() < 0.5)


# ---- the great oak -----------------------------------------------------------------------------------------------------
def _kmeans_az(az, w, k, iters=12):
    """Group headings (deg) into k clusters on the circle, weighted by w."""
    az, w = np.asarray(az, float), np.asarray(w, float)
    order = np.argsort(-w)
    cen = [az[order[0]]]
    while len(cen) < k:                                   # farthest-point start
        d = np.min([np.abs((az - c + 180) % 360 - 180) for c in cen], 0)
        cen.append(az[int(np.argmax(d * (0.5 + w / w.max())))])
    cen = np.array(cen)
    lab = np.zeros(len(az), int)
    for _ in range(iters):
        d = np.abs((az[:, None] - cen[None] + 180) % 360 - 180)
        lab = d.argmin(1)
        for j in range(k):
            m = lab == j
            if m.any():
                a = np.radians(az[m])
                cen[j] = math.degrees(math.atan2((w[m] * np.sin(a)).sum(), (w[m] * np.cos(a)).sum())) % 360
    return lab, cen


def oak(geo, base=(0.0, 0.0, 0.0), lean_az=300.0, lean=7.0, limbs=None, height=None, crown_radius=None,
        trunk_d=1.35, fork_h=2.9, scaffolds=3, seed=7, leaf_density=0.3, twig_density=1.0, detail=1.0):
    """The great oak: a massive leaning trunk, heavy sinuous limbs, a haze of twigs with sparse late-autumn leaves.

    base          the centre of the trunk at the ground (world m).
    lean_az, lean heading (deg clockwise from +Y) and angle (deg from vertical) of the trunk's lean.
    limbs         the main limbs, a list of (az deg, reach m, tip height m[, base radius m]): az = heading of the limb's
                  tip seen from the trunk base, reach = horizontal distance of the tip from the base, tip height above
                  the base.  Default OAK_LIMBS = this specimen as read from the aerial photo.  The limbs are gathered
                  into `scaffolds` heavy stems that leave the trunk at the fork (fork_h m above the base).
    height        if given, the tip heights are rescaled so the highest twigs reach it (m; this specimen ~17).
    crown_radius  if given, the reaches are rescaled so the longest limb's twigs reach it (m; this specimen ~14).
    trunk_d       trunk diameter at breast height (m); the root flare is about 1.6 x wider.
    leaf_density  0 = bare .. 1 = every twig spray carries leaves (late autumn here: 0.3).
    twig_density  scales the number of twig sprays;  detail: scales the amount of fine branching (triangles).
    Triangles: about 95k at the defaults (budget 120k).  Returns the number of triangles added."""
    rs = np.random.RandomState(seed)
    out = _Out()
    base = np.asarray(base, float)
    L0 = [tuple(float(x) for x in l) for l in (limbs if limbs is not None else OAK_LIMBS)]
    if height:
        k = (height - 1.2) / max(l[2] for l in L0)
        L0 = [(l[0], l[1], l[2] * k) + l[3:] for l in L0]
    if crown_radius:
        k = (crown_radius - 1.0) / max(l[1] for l in L0)
        L0 = [(l[0], l[1] * k, l[2]) + l[3:] for l in L0]
    rt = trunk_d / 2
    ldir = _azv(lean_az)
    tl = math.tan(math.radians(lean))
    fork = base + UP * fork_h + ldir * fork_h * tl
    tdir = _unit(UP + ldir * tl)
    tips = [base + _azv(a) * r + UP * h for a, r, h, *_ in L0]
    lens = np.array([np.linalg.norm(t - fork) for t in tips])
    lab, cen = _kmeans_az([l[0] for l in L0], lens, max(1, min(scaffolds, len(L0))))
    crown_c = base + UP * (fork_h + 0.45 * (max(l[2] for l in L0) - fork_h))
    axes = []                                                # every axis of the skeleton
    mains = []                                               # the main limbs (level 1)
    groups = sorted(range(len(cen)), key=lambda j: -lens[lab == j].sum() if (lab == j).any() else 0)
    total = lens.sum()
    for gi, j in enumerate(groups):
        idx = [i for i in range(len(L0)) if lab[i] == j]
        if not idx:
            continue
        lead = max(idx, key=lambda i: lens[i])
        share = lens[idx].sum() / total
        rsc = rt * 0.86 * share ** 0.36                      # radius of this scaffold stem at the fork
        el = math.degrees(math.atan2(np.mean([L0[i][2] for i in idx]) - fork_h, np.mean([L0[i][1] for i in idx])))
        sdir = _azv(cen[j], float(np.clip(el + 22, 38, 68)))
        tip = tips[lead]
        hd = _unit((tip - fork) * np.array([1, 1, 0]))
        t1 = _unit(hd + UP * rs.uniform(0.0, 0.25))
        if gi == 0:
            # the trunk runs on into the heaviest scaffold and its leading limb: one tube, no joint
            zs = np.arange(-0.35, fork_h - 0.2, 0.22)
            sway = np.outer(np.sin(zs * 1.3 + rs.uniform(0, 6)) * 0.07 * _smooth(zs, 0.2, 1.5), _perp(ldir))
            Pt = base[None] + np.outer(zs, UP) + np.outer(zs * tl, ldir) + sway
            Pl = _limb_path(rs, fork, tip, 0.55 * tdir + 0.45 * sdir, t1, 0.3, wig=0.05, kink=0.5)
            P = np.vstack([Pt, Pl[1:]])
            ax = _Ax(P, P[:, 0], 0)
            sf = ax.S[len(Pt) - 1]                           # arc length of the fork
            Ll = ax.L - sf
            r_l = np.where(ax.S <= sf, rt,
                           0.02 + (rsc - 0.02) * np.clip(1 - (ax.S - sf) / Ll, 0, 1) ** 1.15)
            blend = _smooth(ax.S, sf - 0.9, sf + 1.3)
            ax.R = rt * (1 - blend) + r_l * blend
            ax.R = np.where(ax.S > sf, np.minimum(ax.R, r_l * (1 + 0.6 * np.exp(-(ax.S - sf) / 0.9))), ax.R)
            ax.fork_s = sf
            trunk_ax = ax
        else:
            S0 = fork - tdir * 0.55 + _azv(cen[j]) * rt * 0.25
            P = _limb_path(rs, S0, tip, 0.35 * tdir + 0.65 * sdir, t1, 0.3, wig=0.05, kink=0.5)
            ax = _Ax(P, P[:, 0], 1)
            ax.R = _taper(ax.S, rsc, 0.02, 1.15, collar=0.3)
            ax.fork_s = 0.55
        axes.append(ax)
        mains.append(ax)
        # the other limbs of the group leave this stem one after the other, the low ones first
        others = sorted([i for i in idx if i != lead], key=lambda i: L0[i][2] - 0.15 * L0[i][1])
        for n, i in enumerate(others):
            sb = ax.fork_s + 0.9 + (n + rs.uniform(0.1, 0.6)) * min(1.25, 4.6 / max(len(others), 1))
            p, t, r = ax.at(sb)
            hd = _unit((tips[i] - p) * np.array([1, 1, 0]))
            rise = (tips[i] - p)[2] / max(np.linalg.norm((tips[i] - p)[:2]), 0.5)
            t0 = _unit(0.35 * t + 0.65 * hd + UP * float(np.clip(0.25 + 0.5 * rise, 0.1, 1.2)))
            Pl = _limb_path(rs, p, tips[i], t0, _unit(hd + UP * rs.uniform(-0.05, 0.3)), 0.3, wig=0.065, kink=0.6)
            li = _Ax(Pl, Pl[:, 0], 1)
            r0 = L0[i][3] if len(L0[i]) > 3 else min(0.74 * r, 0.021 * li.L ** 1.02 + 0.02)
            li.R = _taper(li.S, r0, 0.02, 1.1, collar=0.4)
            axes.append(li)
            mains.append(li)

    # ---- the finer branching: sub-limbs, branches, twiglets ----
    lvl2, lvl3, lvl4 = [], [], []
    for ax in mains:
        s_from = (ax.fork_s + 2.2) if hasattr(ax, 'fork_s') else 0.22 * ax.L
        lvl2 += _children(rs, ax, min(s_from, 0.5 * ax.L), 0.97 * ax.L, 1.35 / detail ** 0.5,
                          lambda s, rem: min(5.5, 0.9 + rem * rs.uniform(0.3, 0.62)) * rs.uniform(0.7, 1.1),
                          angle=(42, 78), rmax=0.66, rk=0.023, rexp=1.12, r_tip=0.014, step=0.26, wig=0.5,
                          lift=0.35, droop=0.25, kink=0.7, lvl=2)
    for ax in lvl2:
        lvl3 += _children(rs, ax, 0.22 * ax.L, 0.98 * ax.L, 0.72 / detail ** 0.5,
                          lambda s, rem: min(2.4, 0.55 + rem * rs.uniform(0.3, 0.6)),
                          angle=(40, 80), rmax=0.6, rk=0.02, rexp=1.1, r_tip=0.009, step=0.22, wig=0.6, lift=0.3,
                          droop=0.3, kink=0.8, lvl=3)
    for ax in mains:                                          # spurs straight off the outer limbs
        lvl3 += _children(rs, ax, 0.55 * ax.L, 0.99 * ax.L, 0.9 / detail ** 0.5,
                          lambda s, rem: min(2.0, 0.5 + rem * rs.uniform(0.2, 0.5)),
                          angle=(40, 80), rmax=0.5, rk=0.02, rexp=1.1, r_tip=0.009, step=0.22, wig=0.6, lift=0.3,
                          droop=0.3, kink=0.8, lvl=3)
    for ax in lvl3:
        lvl4 += _children(rs, ax, 0.3 * ax.L, 0.97 * ax.L, 0.5 / detail ** 0.5,
                          lambda s, rem: rs.uniform(0.35, 0.95),
                          angle=(35, 75), rmax=0.6, rk=0.016, rexp=1.0, r_tip=0.006, step=0.24, wig=0.7, lift=0.2,
                          droop=0.2, kink=0.8, lvl=4)
    axes += lvl2 + lvl3 + lvl4

    # ---- bark tubes ----
    bark = out['bark']

    def flare(th, S):
        z = S - 0.35                                          # height above the ground along the trunk
        lob = (np.sin(3 * th + 0.7) + 0.7 * np.sin(5 * th + 2.1) + 0.5 * np.sin(2 * th + 4.0)) / 2.2
        k = np.exp(-np.maximum(z, -0.2) / 0.42)[:, None]
        return 1 + 0.5 * k * (1 + 0.55 * lob[None, :]) + 0.06 * _smooth(z, 0.4, 1.6)[:, None] * lob[None, :]

    for ax in axes:
        if ax is trunk_ax:
            # in sections, so the texture keeps a sensible scale from the 4 m girth down to a twig
            cuts = [0] + [int(np.argmax(ax.R < r)) for r in (0.42, 0.24, 0.13, 0.07) if (ax.R < r).any()] + \
                   [len(ax.P) - 1]
            cuts = sorted(set(c for c in cuts if 0 <= c <= len(ax.P) - 1))
            for a, b in zip(cuts[:-1], cuts[1:]):
                if b - a < 1:
                    continue
                sh = (lambda th, S, o=ax.S[a]: flare(th, S + o)) if ax.S[a] < 3.0 else None
                _tube(bark, ax.P[a:b + 1], ax.R[a:b + 1], rs=rs, lump=0.1, shape=sh, tip=(b == len(ax.P) - 1))
        elif ax.lvl <= 1:
            cuts = [0] + [int(np.argmax(ax.R < r)) for r in (0.13, 0.07) if (ax.R < r).any() and ax.R[0] > r * 1.4] + \
                   [len(ax.P) - 1]
            cuts = sorted(set(cuts))
            for a, b in zip(cuts[:-1], cuts[1:]):
                if b - a >= 1:
                    _tube(bark, ax.P[a:b + 1], ax.R[a:b + 1], rs=rs, lump=0.09, tip=(b == len(ax.P) - 1))
        else:
            _tube(bark, ax.P, ax.R, rs=rs, lump=0.07 if ax.lvl == 2 else 0.0)

    # ---- twig sprays and leaf remnants (cards of the leaf_oak atlas: 0, 1 bare sprays, 2 a few leaves, 3 leafy) ----
    leaf = out['leaf_oak']
    nfn = _round_normals(crown_c, squash=0.8, up=0.55)
    rmax = max(l[1] for l in L0)

    def spray(p, d, L, lv):
        """One twig spray rooted at p, growing along d."""
        d = _unit(d + rs.normal(size=3) * 0.28 + UP * 0.12)
        side = _unit(_rot(_perp(d), d, rs.uniform(-1.1, 1.1) if rs.uniform() < 0.65 else rs.uniform(0, 6.28)))
        # leaves gather toward the south-west and the outside of the crown, in clumps
        rel = p - base
        clump = 0.5 + 0.5 * math.sin(rel[0] * 0.9 + 1.3) * math.sin(rel[1] * 0.8 + 0.4) + 0.25 * (rel[2] < 9.0)
        pl = leaf_density * (0.55 + 0.9 * clump)
        u = rs.uniform()
        cell = (3 if u < 0.4 * pl else 2) if u < pl else rs.randint(2)
        shade = int(np.clip(4 + 3 * np.linalg.norm(rel[:2]) / rmax + rs.randint(0, 2), 0, 7))
        _card(leaf, p, d, side, L, L * rs.uniform(0.72, 0.95), cell, rs.randint(8), shade, nfn,
              droop=rs.uniform(0.0, 0.16) / max(L, 0.5), rows=2, flip=rs.uniform() < 0.5,
              curl=rs.uniform(-0.12, 0.12) / max(L, 0.5))

    kd = twig_density
    for ax in lvl4:
        p, t, _ = ax.at(ax.L)
        for _ in range(1 + (rs.uniform() < 0.45 * kd)):
            spray(p - t * 0.1, t, rs.uniform(0.75, 1.35), 4)
        if rs.uniform() < 0.5 * kd:
            p, t, _ = ax.at(ax.L * rs.uniform(0.3, 0.7))
            spray(p, _unit(t + rs.normal(size=3) * 0.7), rs.uniform(0.55, 0.95), 4)
    for ax in lvl3:
        p, t, _ = ax.at(ax.L)
        for _ in range(2):
            spray(p - t * 0.12, t, rs.uniform(1.0, 1.7), 3)
        s = 0.35
        while s < ax.L - 0.2:
            if rs.uniform() < 0.55 * kd:
                p, t, _ = ax.at(s)
                spray(p, _unit(t * 0.5 + rs.normal(size=3) * 0.8 + UP * 0.3), rs.uniform(0.6, 1.1), 3)
            s += 0.45
    for ax in lvl2 + mains:
        p, t, _ = ax.at(ax.L)
        for _ in range(3):
            spray(p - t * 0.15, t, rs.uniform(1.2, 2.0), 2)
    for ax in lvl2:                                            # short spurs along the sub-limbs
        s = 0.5
        while s < ax.L - 0.3:
            if rs.uniform() < 0.3 * kd:
                p, t, r = ax.at(s)
                d = _unit(np.cross(t, rs.normal(size=3)) + UP * 0.5)
                spray(p + d * r * 0.5, d, rs.uniform(0.5, 0.9), 2)
            s += 0.5
    return out.flush(geo)


# ---- sapling ---------------------------------------------------------------------------------------------------------
def sapling(geo, base=(0.0, 0.0, 0.0), h=4.0, crown_r=0.65, clear=1.9, seed=1, stake=True, lean_az=0.0, lean=2.0,
            trunk_d=0.05, density=1.0):
    """A slender young street tree: a thin, slightly crooked stem, bare for `clear` m, and a small sparse, upright
    crown (radius crown_r m) of small olive-green leaves; total height h m (3.5-4.5 here).  stake: two lodge poles with
    a tie, as the nursery leaves them.  About 2-3k triangles (budget 6k)."""
    rs = np.random.RandomState(seed)
    out = _Out()
    base = np.asarray(base, float)
    d0 = _unit(UP + _azv(lean_az) * math.tan(math.radians(lean)))
    P = _path(rs, base - UP * 0.1, d0, h * 0.93 + 0.1, 0.25, wig=0.06, lift=0.05, kink=0.25)
    tr = _Ax(P, P[:, 0], 0)
    tr.R = _taper(tr.S, trunk_d / 2, 0.006, 0.85)
    _tube(out['bark_young'], tr.P, tr.R, nseg=7, rs=rs, tile=YOUNG_TILE, lump=0.05)
    br = _children(rs, tr, clear + 0.1, tr.L * 0.97, 0.26 / density,
                   lambda s, rem: (0.35 + 0.55 * min(rem, 1.6)) * rs.uniform(0.7, 1.15) * crown_r / 0.65,
                   angle=(28, 55), rmax=0.6, rk=0.011, rexp=1.0, r_tip=0.003, step=0.2, wig=0.25, lift=0.75,
                   kink=0.3, up_bias=1.0)
    tw = []
    for b in br:
        _tube(out['bark_young'], b.P, b.R, nseg=4, rs=rs, tile=YOUNG_TILE)
        tw += _children(rs, b, 0.3 * b.L, 0.95 * b.L, 0.3 / density, lambda s, rem: rs.uniform(0.2, 0.45),
                        angle=(30, 60), rmax=0.6, rk=0.008, r_tip=0.002, step=0.2, wig=0.3, lift=0.5, kink=0.2)
    for b in tw:
        _tube(out['bark_young'], b.P, b.R, nseg=3, rs=rs, tile=YOUNG_TILE, tip=False)
    cc = base + UP * (clear + 0.55 * (h - clear))
    nfn = _round_normals(cc, squash=0.7, up=0.35)
    leaf = out['leaf_sapling']

    def sprig(ax, s, L):
        p, t, _ = ax.at(s)
        d = _unit(t + rs.normal(size=3) * 0.35 + UP * 0.25)
        side = _unit(_rot(_perp(d), d, rs.uniform(0, 6.28)))
        rel = np.linalg.norm((p - cc)[:2]) / max(crown_r, 0.1)
        _card(leaf, p, d, side, L, L * rs.uniform(0.6, 0.85), rs.randint(4), rs.randint(8),
              int(np.clip(4 + 3 * rel + rs.randint(0, 2), 0, 7)), nfn, droop=0.25, rows=2, flip=rs.uniform() < 0.5)

    for b in br + tw + [tr]:
        sprig(b, b.L, rs.uniform(0.34, 0.5))
        if b is not tr:
            n = 2 if b in br else 1
            for k in range(n):
                sprig(b, b.L * rs.uniform(0.35, 0.9), rs.uniform(0.28, 0.42))
    if stake:
        sd = _perp(_azv(lean_az + rs.uniform(-20, 20)))
        for sgn in (-1, 1):
            q = base + sd * sgn * 0.22
            Geo.cylinder(_GeoProxy(out['stake_wood']), 'stake_wood', q - UP * 0.1, q + UP * 1.75, 0.028, n=7)
        zt = 1.45
        pt, _, r = tr.at(zt + 0.1)
        for sgn in (-1, 1):
            q = base + sd * sgn * 0.22 + UP * zt
            Geo.prism(_GeoProxy(out['plant_tie']), 'plant_tie', [(-0.012, -0.002), (0.012, -0.002), (0.012, 0.002),
                                                                   (-0.012, 0.002)], q, pt, cap=False)
    return out.flush(geo)


class _GeoProxy(Geo):
    """Lets the kit's primitives write into one of this module's buffers."""

    def __init__(self, buf):
        super().__init__()
        self._buf = buf

    def mesh(self, mat):
        return self._buf


# ---- shrubs ----------------------------------------------------------------------------------------------------------
def shrub(geo, base=(0.0, 0.0, 0.0), r=0.42, h=0.75, seed=1, kind='boxwood', loose=0.35):
    """A rounded low shrub: a dark core and a shell of small leaf cards.  r: radius (m), h: height (m);
    kind: 'boxwood' (tiny dark leaves), 'laurel' (large glossy leaves) or 'green'; loose: 0 = clipped ball ..
    1 = shaggy with shoots sticking out.  About 600-750 triangles (budget 800)."""
    rs = np.random.RandomState(seed)
    out = _Out()
    base = np.asarray(base, float)
    mat = {'boxwood': 'leaf_boxwood', 'laurel': 'leaf_laurel', 'green': 'leaf_green'}[kind]
    size = {'boxwood': 0.27, 'laurel': 0.42, 'green': 0.4}[kind]
    c = base + UP * h * 0.52
    radii = np.array([r * rs.uniform(0.92, 1.08), r * rs.uniform(0.92, 1.08), h * 0.5])
    _blob(out['shrub_core'], c - UP * 0.02, radii * 0.8, rs, nu=8, nv=4, zmin=base[2] + 0.01)
    nfn = _round_normals(c - UP * h * 0.15, squash=0.85, up=0.3)
    n = int(250 * min(1.0, (r / 0.42) ** 1.2 * (0.27 / size) ** 2 * 1.0 + 0.25))
    n = int(np.clip(n, 120, 300))
    _shell_cards(out[mat], rs, c, radii * 0.93, n, size, (0, 1, 2), nfn, tilt=0.5 + 0.6 * loose, zmin=base[2] + 0.02,
                 shade=(2, 7), top=0.72)
    for _ in range(int(4 + 14 * loose)):                              # shoots breaking the outline
        d = _unit(np.array([rs.normal(), rs.normal(), abs(rs.normal()) + 0.6]))
        p = c + d * radii * 0.8
        _card(out[mat], p, _unit(d + UP * 0.4), _perp(d) if rs.uniform() < 0.5 else np.cross(d, _perp(d)),
              size * rs.uniform(0.9, 1.3), size * 0.7, 3, rs.randint(8), 7, nfn, rows=1, flip=rs.uniform() < 0.5)
    return out.flush(geo)


def boxwood(geo, base=(0.0, 0.0, 0.0), r=0.4, h=0.7, seed=1, loose=0.3):
    """The low rounded shrubs of the front planter and the beds (see shrub)."""
    return shrub(geo, base, r=r, h=h, seed=seed, kind='boxwood', loose=loose)


def rose_bush(geo, base=(0.0, 0.0, 0.0), h=1.1, r=0.55, seed=1, blooms=14, canes=7):
    """A loose white-flowering shrub rose: arching canes, leaf sprays along them, `blooms` white flowers at the cane
    ends and over the top.  h: height, r: radius (m).  About 1.1-1.4k triangles (budget 1.5k)."""
    rs = np.random.RandomState(seed)
    out = _Out()
    base = np.asarray(base, float)
    c = base + UP * h * 0.55
    nfn = _round_normals(c - UP * h * 0.2, squash=0.8, up=0.35)
    leaf = out['leaf_rose']
    ends = []
    for k in range(canes):
        az = 360.0 * (k + rs.uniform(-0.3, 0.3)) / canes
        el = rs.uniform(52, 82)
        L = h * rs.uniform(0.85, 1.2) / math.sin(math.radians(el)) * 0.9
        P = _path(rs, base + _azv(az) * rs.uniform(0.0, 0.08), _azv(az, el), L, 0.18, wig=0.25, droop=0.9, kink=0.25)
        P[:, 2] = np.maximum(P[:, 2], base[2] + 0.05)
        ax = _Ax(P, P[:, 0], 0)
        ax.R = _taper(ax.S, 0.008, 0.003, 1.0)
        _tube(out['bark_young'], ax.P, ax.R, nseg=3, rs=rs, tile=YOUNG_TILE, tip=False)
        s = 0.18
        while s < ax.L:
            p, t, _ = ax.at(s)
            d = _unit(np.cross(t, rs.normal(size=3)) + t * 0.5 + UP * 0.25)
            side = _unit(_rot(_perp(d), d, rs.uniform(-0.8, 0.8)))
            Lc = rs.uniform(0.24, 0.36)
            _card(leaf, p, d, side, Lc, Lc, rs.randint(2), rs.randint(8),
                  int(np.clip(2 + 5 * (p[2] - base[2]) / h + rs.randint(0, 2), 0, 7)), nfn, droop=0.5, rows=1,
                  flip=rs.uniform() < 0.5)
            s += rs.uniform(0.09, 0.16)
        ends.append(ax.at(ax.L))
    # blooms: a spray with flowers at the cane ends, single open flowers facing up and out
    for k in range(blooms):
        if k < len(ends):
            p, t, _ = ends[k]
        else:
            d = _unit(np.array([rs.normal(), rs.normal(), abs(rs.normal()) + 0.3]))
            p, t = c + d * np.array([r, r, h * 0.45]) * rs.uniform(0.75, 1.0), d
        d = _unit(t + UP * 0.6 + rs.normal(size=3) * 0.3)
        side = _unit(_rot(_perp(d), d, rs.uniform(0, 6.28)))
        if rs.uniform() < 0.45:
            Lc = rs.uniform(0.22, 0.3)
            _card(leaf, p - d * Lc * 0.4, d, side, Lc, Lc, 2, rs.randint(8), 7, nfn, rows=1)
        else:                                                  # one open flower, across the stalk
            s = rs.uniform(0.085, 0.12)
            fn = _unit(d + rs.normal(size=3) * 0.25)
            a1 = _perp(fn)
            _card(leaf, p + fn * 0.02 - a1 * s * 0.5, a1, np.cross(fn, a1), s, s, 3, rs.randint(3), 7, nfn, rows=1)
    # filler foliage low in the bush
    _shell_cards(leaf, rs, c - UP * h * 0.12, np.array([r * 0.8, r * 0.8, h * 0.42]), 70, 0.3, (0, 1), nfn, tilt=1.0,
                 zmin=base[2] + 0.03, shade=(1, 6), top=0.6)
    return out.flush(geo)


def hedge(geo, polyline, h=1.7, w=1.1, seed=1, loose=0.7, kind='laurel', spacing=None):
    """A hedge along a polyline [(x, y) or (x, y, z), ...] (its centre line at the ground), h high and w wide (m).
    loose: 0 = sheared flat .. 1 = a row of individual shrubs with shoots (the laurels along the pool fence: 0.7).
    kind: 'laurel' (large glossy leaves) | 'boxwood' | 'green'.  About 330 triangles per metre (budget 400)."""
    rs = np.random.RandomState(seed)
    out = _Out()
    pts = np.array([(p[0], p[1], p[2] if len(p) > 2 else 0.0) for p in polyline], float)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    S = np.concatenate([[0.0], np.cumsum(seg)])
    total = float(S[-1])
    mat = {'boxwood': 'leaf_boxwood', 'laurel': 'leaf_laurel', 'green': 'leaf_green'}[kind]
    size = {'boxwood': 0.28, 'laurel': 0.46, 'green': 0.42}[kind]
    sp = spacing or max(0.75, 0.85 * w)
    n = max(1, int(round(total / sp)))

    def at(s):
        i = int(min(np.searchsorted(S, s, side='right') - 1, len(seg) - 1))
        f = (s - S[i]) / max(seg[i], 1e-9)
        return pts[i] * (1 - f) + pts[i + 1] * f, _unit(pts[i + 1] - pts[i])

    for k in range(n):
        s = (k + 0.5) * total / n + rs.uniform(-0.12, 0.12) * sp * loose
        p, t = at(float(np.clip(s, 0, total)))
        side = np.cross(UP, t)
        hk = h * (1 + loose * rs.uniform(-0.16, 0.1))
        wk = w * (1 + loose * rs.uniform(-0.12, 0.1))
        lk = total / n * (0.62 + 0.12 * (1 - loose))             # half-length along the row: the lumps overlap
        c = p + UP * hk * 0.5 + side * rs.uniform(-0.06, 0.06) * loose
        # the ellipsoid is aligned with the row
        R = np.stack([t, side, UP], 1)
        radii = np.array([lk, wk * 0.5, hk * 0.5])
        core, cards = _Buf(), _Buf()
        _blob(core, (0, 0, 0), radii * 0.82, rs, nu=8, nv=4, tile=0.5)
        nfn_l = _round_normals((0, 0, -hk * 0.12), squash=0.8, up=0.3)
        ncard = int(np.clip(150 * (total / n) * (0.46 / size) ** 1.6, 60, 170 * total / n))
        _shell_cards(cards, rs, (0, 0, 0), radii * 0.92, ncard, size, (0, 1, 2), nfn_l, tilt=0.5 + 0.6 * loose,
                     zmin=-hk * 0.5 + 0.03, shade=(2, 7), top=0.8)
        for _ in range(int(2 + 7 * loose)):                         # upright shoots on top
            d = _unit(np.array([rs.normal() * 0.5, rs.normal() * 0.35, 1.0]))
            q = d * radii * 0.82
            _card(cards, q, _unit(d + UP * 0.8), np.array([1.0, 0, 0]) if rs.uniform() < 0.5 else
                  np.array([0, 1.0, 0]), size * rs.uniform(1.0, 1.5), size * 0.75, 3, rs.randint(8), 7, nfn_l,
                  rows=1, flip=rs.uniform() < 0.5)
        for b, m in ((core, 'shrub_core'), (cards, mat)):
            V = np.vstack(b.V) @ R.T + c
            V[:, 2] = np.maximum(V[:, 2], p[2] + 0.01)
            out[m].add(V, np.vstack(b.N) @ R.T, np.vstack(b.UV), np.vstack(b.F))
    return out.flush(geo)


# ---- backdrop trees ----------------------------------------------------------------------------------------------------
_SHAPES = {                     # crown radii as (horizontal x crown_r, vertical x crown height / 2), top-heaviness
    'round': (1.0, 1.0, 0.0), 'oval': (0.8, 1.0, 0.1), 'upright': (0.55, 1.0, 0.25), 'spreading': (1.25, 0.8, -0.1),
}


def broadleaf(geo, base=(0.0, 0.0, 0.0), h=9.0, crown_r=3.4, palette='green', shape='round', trunk_h=None, seed=1,
              density=1.0, trunk_d=None, bark='bark', lean_az=0.0, lean=3.0):
    """A medium garden / street tree for the surroundings.  h: height (m), crown_r: crown radius (m),
    palette: 'green' | 'gold' | 'red' | 'olive' (leaf_<palette>), shape: 'round' | 'oval' | 'upright' | 'spreading',
    trunk_h: clear trunk (m, default 0.28 h), density: 0.5 = open crown .. 1.3 = dense, bark: 'bark' | 'bark_young'.
    The crown is a cloud of leaf-cluster cards gathered round the ends of a real branch skeleton, irregular in outline.
    About 4.5k triangles (budget 5k)."""
    rs = np.random.RandomState(seed)
    out = _Out()
    base = np.asarray(base, float)
    kx, kz, topk = _SHAPES[shape]
    th = trunk_h if trunk_h is not None else 0.28 * h
    td = trunk_d if trunk_d is not None else 0.035 * h
    ch = h - th                                                # crown height
    cc = base + UP * (th + ch * (0.5 + 0.08 * topk))
    rad = np.array([crown_r * kx, crown_r * kx, ch * 0.5 * kz])
    tile = BARK_TILE if bark != 'bark_young' else YOUNG_TILE
    d0 = _unit(UP + _azv(lean_az) * math.tan(math.radians(lean)))
    P = _path(rs, base - UP * 0.15, d0, th + ch * 0.45, 0.45, wig=0.08, kink=0.3)
    tr = _Ax(P, P[:, 0], 0)
    tr.R = _taper(tr.S, td / 2, td * 0.12, 0.8) * (1 + 0.35 * np.exp(-tr.S / 0.35))
    _tube(out[bark], tr.P, tr.R, nseg=9, rs=rs, tile=tile, lump=0.06)
    # puffs: lumps of foliage on the crown's shell and inside it
    npuff = int(np.clip(26 * density * (crown_r * kx / 3.4) ** 0.6, 12, 40))
    puffs = []
    for k in range(npuff):
        z = 1 - 1.75 * (k + 0.5) / npuff                      # top .. below the equator
        ph = k * 2.399963 + rs.uniform(-0.4, 0.4)
        rr = math.sqrt(max(1 - z * z, 0))
        d = np.array([rr * math.cos(ph), rr * math.sin(ph), z])
        dist = rs.uniform(0.62, 0.9) if k % 4 else rs.uniform(0.25, 0.5)
        puffs.append(cc + d * rad * dist * (1 + 0.12 * rs.normal()))
    puffs = np.array(puffs)
    # scaffold branches from the upper trunk to the far puffs, twigs to the rest
    far = np.argsort(-np.linalg.norm((puffs - cc) / rad, axis=1))
    nmain = int(np.clip(5 + crown_r * 0.4, 5, 8))
    mains, used = [], set()
    for i in far:
        if len(mains) >= nmain:
            break
        if any(np.linalg.norm(puffs[i] - puffs[j]) < 0.7 * crown_r * kx for j in used):
            continue
        s0 = tr.L * rs.uniform(0.5, 0.95)
        p, t, r = tr.at(s0)
        hd = _unit(puffs[i] - p)
        Pb = _limb_path(rs, p, puffs[i], _unit(0.5 * t + 0.5 * hd), _unit(hd + UP * 0.3), 0.55, wig=0.05, kink=0.4)
        b = _Ax(Pb, Pb[:, 0], 1)
        b.R = _taper(b.S, min(0.6 * r, 0.02 * b.L + 0.02), 0.012, 1.0, collar=0.3)
        _tube(out[bark], b.P, b.R, nseg=6, rs=rs, tile=tile)
        mains.append(b)
        used.add(i)
    allax = mains + [tr]
    for i in range(npuff):
        if i in used:
            continue
        # from the nearest point of a main branch
        best = None
        for b in allax:
            dd = np.linalg.norm(b.P - puffs[i], axis=1)
            j = int(np.argmin(dd))
            if best is None or dd[j] < best[0]:
                best = (dd[j], b, j)
        _, b, j = best
        j = max(1, min(j, len(b.P) - 2))
        hd = _unit(puffs[i] - b.P[j])
        Pb = _limb_path(rs, b.P[j], puffs[i], _unit(hd + UP * 0.2), hd, 0.6, wig=0.06, kink=0.4)
        c = _Ax(Pb, Pb[:, 0], 2)
        c.R = _taper(c.S, min(0.55 * b.R[j], 0.014 * c.L + 0.012), 0.008, 1.0)
        _tube(out[bark], c.P, c.R, nseg=4, rs=rs, tile=tile, tip=False)
    # foliage cards
    left = 4850 - out.ntri
    ncard = max(200, int(left / 2))
    per = max(6, int(ncard * min(1.0, density) / npuff))
    leaf = out['leaf_' + palette]
    nfn = _round_normals(cc - UP * ch * 0.1, squash=0.9, up=0.3)
    psz = 0.36 * crown_r * kx * (26.0 / npuff) ** 0.33
    for i in range(npuff):
        rel = (puffs[i] - cc) / rad
        depth = float(np.clip(np.linalg.norm(rel), 0, 1))
        sh = (int(1 + 3 * depth + 2 * _smooth(rel[2], -0.6, 0.6)), 7 if depth > 0.5 else 5)
        pr = psz * rs.uniform(0.8, 1.2) * np.array([1.0, 1.0, 0.8])
        _shell_cards(leaf, rs, puffs[i], pr, per, psz * 1.15, (0, 1, 2, 3), nfn, tilt=1.2, zmin=base[2] + 0.4,
                     shade=sh, top=0.95)
    return out.flush(geo)


def conifer(geo, base=(0.0, 0.0, 0.0), h=20.0, r=3.2, seed=1, clear=None, tops=1):
    """A tall dark redwood / cedar for the backdrop: a straight red-brown trunk and whorls of drooping boughs in a
    narrow, ragged cone.  h: height (15-25 m), r: radius of the lowest boughs (m), clear: bare trunk (m, default
    0.14 h), tops: > 1 adds lesser leaders beside the main one (the multi-topped trees behind the cabana).
    About 4.5k triangles (budget 5k)."""
    rs = np.random.RandomState(seed)
    out = _Out()
    base = np.asarray(base, float)
    clear = 0.14 * h if clear is None else clear
    leaf = out['leaf_conifer']
    leaders = [(base, h, r, clear)]
    for k in range(1, tops):
        a = rs.uniform(0, 360)
        leaders.append((base + _azv(a) * r * rs.uniform(0.35, 0.6), h * rs.uniform(0.72, 0.92), r * 0.7,
                        clear + h * rs.uniform(0.15, 0.3)))
    budget = 4800 // len(leaders)
    for li, (b0, hh, rr, cl) in enumerate(leaders):
        P = _path(rs, b0 - UP * 0.2, UP, hh + 0.2, hh / 9.0, wig=0.012)
        tr = _Ax(P, P[:, 0], 0)
        tr.R = _taper(tr.S, 0.021 * hh, 0.02, 0.9) * (1 + 0.5 * np.exp(-tr.S / 0.6))
        _tube(out['bark_redwood'], tr.P, tr.R, nseg=8 if li == 0 else 6, rs=rs, lump=0.04)
        ntier = int((budget - 200) / (12 * 5.5))
        zs = cl + (hh - cl) * (np.arange(ntier) + rs.uniform(0.1, 0.9, ntier)) / ntier
        for z in zs:
            f = (z - cl) / (hh - cl)                              # 0 at the lowest boughs .. 1 at the tip
            reach = rr * (1 - f) ** 0.8 * (0.82 + 0.22 * math.sin(f * 21.0 + li)) + 0.35
            nb = 5 if f < 0.75 else 4
            a0 = rs.uniform(0, 360)
            for k in range(nb):
                az = a0 + 360.0 * k / nb + rs.uniform(-22, 22)
                Lb = reach * rs.uniform(0.7, 1.12)
                if rs.uniform() < 0.07:
                    continue                                       # a gap
                el = 12 - 30 * (1 - f) + rs.uniform(-8, 8)         # low boughs hang, high ones reach up
                d = _azv(az, el)
                p = tr.at(z - b0[2] + 0.2)[0]
                side = _perp(d)
                upn = np.cross(side, d)
                sh = int(np.clip(3 + 4 * f + rs.randint(0, 2), 0, 7))
                cfn = _round_normals(p - UP * 0.3 * Lb, squash=0.6, up=0.45)
                # the bough seen from the side: a hanging frond in the vertical plane through it
                _card(leaf, p, d, upn, Lb, Lb * rs.uniform(0.42, 0.6), rs.randint(2), rs.randint(8), sh, cfn,
                      droop=0.2 / max(Lb, 1.0), rows=2, flip=rs.uniform() < 0.5)
                # seen from above and below: the flat spray
                _card(leaf, p, d, side, Lb, Lb * rs.uniform(0.55, 0.75), 2, rs.randint(8), min(7, sh + 1), cfn,
                      droop=0.2 / max(Lb, 1.0), rows=2, flip=rs.uniform() < 0.5)
                # seen end-on: curtains across the bough
                for q in (0.45, 0.82):
                    c = p + d * Lb * q - UP * 0.2 * q * q * Lb
                    wq = Lb * (0.75 - 0.3 * q)
                    _card(leaf, c + UP * wq * 0.25, -UP, side, wq * 0.9, wq, 3 if q < 0.6 else rs.randint(2),
                          rs.randint(8), max(0, sh - (2 if q < 0.6 else 0)), cfn, rows=1, flip=rs.uniform() < 0.5)
        # the tip
        cfn = _round_normals(tr.P[-1] - UP * 1.5, squash=0.5, up=0.3)
        for k in range(3):
            _card(leaf, tr.P[-1] - UP * 1.6, UP, _azv(60 * k + rs.uniform(0, 30)), 2.4, 1.2, rs.randint(2),
                  rs.randint(8), 7, cfn, rows=1)
    return out.flush(geo)
