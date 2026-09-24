"""
loftkit.mesh -- a small parametric surface-modelling kernel.

Everything in the PC-12 model is built from parametric surfaces that are
evaluated on (u, v) grids and tessellated here.  The kernel provides:

  * Mesh             -- triangle mesh with smooth normals and optional (u, v) params
  * grid_surface     -- tessellate a sampled parametric surface P[u, v]
  * trim             -- implicit trimming (marching triangles on a signed field)
  * boundary_loops   -- ordered boundary loops of an open mesh
  * solidify         -- give a skin patch real thickness (doors, panels)
  * revolve / sweep_tube / loft / superellipsoid / box  -- primitive generators

Coordinates are aircraft structural axes:
  x = fuselage station (m, aft of datum), y = butt line (m, +starboard), z = water line (m, up, ground = 0)
"""
from __future__ import annotations
import numpy as np

EPS = 1e-12


def _normalize(a, fallback=None):
    n = np.linalg.norm(a, axis=-1, keepdims=True)
    bad = (n[..., 0] < 1e-14)
    out = a / np.where(n < 1e-14, 1.0, n)
    if fallback is not None and bad.any():
        out[bad] = fallback
    return out, bad


class Mesh:
    """Indexed triangle mesh.  V (n,3), F (m,3), N (n,3), UV (n,2) optional."""

    def __init__(self, V, F, N=None, UV=None):
        self.V = np.asarray(V, dtype=np.float64).reshape(-1, 3)
        self.F = np.asarray(F, dtype=np.int64).reshape(-1, 3)
        self.UV = None if UV is None else np.asarray(UV, dtype=np.float64).reshape(-1, 2)
        if N is None:
            self.N = np.zeros_like(self.V)
            self.compute_normals()
        else:
            self.N = np.asarray(N, dtype=np.float64).reshape(-1, 3)

    # ------------------------------------------------------------------ basics
    def copy(self):
        return Mesh(self.V.copy(), self.F.copy(), self.N.copy(),
                    None if self.UV is None else self.UV.copy())

    @property
    def nv(self):
        return len(self.V)

    @property
    def nf(self):
        return len(self.F)

    def compute_normals(self):
        if len(self.F) == 0:
            return self
        v0, v1, v2 = (self.V[self.F[:, k]] for k in range(3))
        fn = np.cross(v1 - v0, v2 - v0)
        N = np.zeros_like(self.V)
        for k in range(3):
            np.add.at(N, self.F[:, k], fn)
        self.N, _ = _normalize(N, fallback=np.array([0, 0, 1.0]))
        return self

    def face_normals(self):
        v0, v1, v2 = (self.V[self.F[:, k]] for k in range(3))
        fn = np.cross(v1 - v0, v2 - v0)
        return _normalize(fn, fallback=np.array([0, 0, 1.0]))[0]

    def area(self):
        v0, v1, v2 = (self.V[self.F[:, k]] for k in range(3))
        return 0.5 * np.linalg.norm(np.cross(v1 - v0, v2 - v0), axis=1).sum()

    def bounds(self):
        return self.V.min(0), self.V.max(0)

    def flipped(self):
        m = self.copy()
        m.F = m.F[:, ::-1].copy()
        m.N = -m.N
        return m

    def remove_degenerate(self, tol=1e-14):
        v0, v1, v2 = (self.V[self.F[:, k]] for k in range(3))
        a = np.linalg.norm(np.cross(v1 - v0, v2 - v0), axis=1)
        idx_ok = (a > tol) & (self.F[:, 0] != self.F[:, 1]) & (self.F[:, 1] != self.F[:, 2]) & (self.F[:, 0] != self.F[:, 2])
        self.F = self.F[idx_ok]
        return self.compact()

    def compact(self):
        used = np.zeros(len(self.V), bool)
        used[self.F.ravel()] = True
        remap = -np.ones(len(self.V), np.int64)
        remap[used] = np.arange(used.sum())
        self.V = self.V[used]
        self.N = self.N[used]
        if self.UV is not None:
            self.UV = self.UV[used]
        self.F = remap[self.F]
        return self

    # ------------------------------------------------------------- transforms
    def transformed(self, M):
        M = np.asarray(M, float)
        R, t = M[:3, :3], M[:3, 3]
        m = self.copy()
        m.V = self.V @ R.T + t
        Ninv = np.linalg.inv(R).T
        m.N, _ = _normalize(self.N @ Ninv.T, fallback=np.array([0, 0, 1.0]))
        if np.linalg.det(R) < 0:
            m.F = m.F[:, ::-1].copy()
        return m

    def translated(self, d):
        m = self.copy()
        m.V = m.V + np.asarray(d, float)
        return m

    def rotated(self, axis, angle, origin=(0, 0, 0)):
        return self.transformed(rotation_about(axis, angle, origin))

    def scaled(self, s, origin=(0, 0, 0)):
        s = np.broadcast_to(np.asarray(s, float), (3,))
        o = np.asarray(origin, float)
        M = np.eye(4)
        M[:3, :3] = np.diag(s)
        M[:3, 3] = o - s * o
        return self.transformed(M)

    def mirrored_y(self):
        """Mirror across the aircraft plane of symmetry (y -> -y)."""
        M = np.diag([1.0, -1.0, 1.0, 1.0])
        return self.transformed(M)

    def offset(self, d):
        """Displace every vertex along its normal (d > 0 = outward)."""
        m = self.copy()
        m.V = m.V + d * m.N
        return m

    @staticmethod
    def merge(meshes):
        meshes = [m for m in meshes if m is not None and len(m.F) > 0]
        if not meshes:
            return Mesh(np.zeros((0, 3)), np.zeros((0, 3), np.int64), np.zeros((0, 3)))
        V, F, N, UV = [], [], [], []
        off = 0
        has_uv = all(m.UV is not None for m in meshes)
        for m in meshes:
            V.append(m.V)
            N.append(m.N)
            F.append(m.F + off)
            if has_uv:
                UV.append(m.UV)
            off += len(m.V)
        return Mesh(np.vstack(V), np.vstack(F), np.vstack(N), np.vstack(UV) if has_uv else None)


# --------------------------------------------------------------------------
# transforms
# --------------------------------------------------------------------------

def rotation_matrix(axis, angle):
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    x, y, z = a
    c, s = np.cos(angle), np.sin(angle)
    C = 1 - c
    return np.array([[c + x * x * C, x * y * C - z * s, x * z * C + y * s],
                     [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
                     [z * x * C - y * s, z * y * C + x * s, c + z * z * C]])


def rotation_about(axis, angle, origin=(0, 0, 0)):
    R = rotation_matrix(axis, angle)
    o = np.asarray(origin, float)
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = o - R @ o
    return M


def frame_matrix(origin, ex, ey, ez):
    M = np.eye(4)
    M[:3, 0], M[:3, 1], M[:3, 2] = ex, ey, ez
    M[:3, 3] = origin
    return M


# --------------------------------------------------------------------------
# grid surfaces
# --------------------------------------------------------------------------

def grid_normals(P, close_u=False, close_v=False):
    """Smooth normals of a sampled parametric surface: dP/du x dP/dv."""
    if close_u:
        dPu = np.roll(P, -1, 0) - np.roll(P, 1, 0)
    else:
        dPu = np.gradient(P, axis=0)
    if close_v:
        dPv = np.roll(P, -1, 1) - np.roll(P, 1, 1)
    else:
        dPv = np.gradient(P, axis=1)
    N = np.cross(dPu, dPv)
    N, bad = _normalize(N)
    if bad.any():
        # poles / collapsed rows: use the mean normal of the neighbouring row(s)
        nu, nv = P.shape[:2]
        for i, j in zip(*np.nonzero(bad)):
            acc = np.zeros(3)
            for di in (-1, 1):
                ii = i + di
                if close_u:
                    ii %= nu
                if 0 <= ii < nu:
                    acc += N[ii].sum(0)
            for dj in (-1, 1):
                jj = j + dj
                if close_v:
                    jj %= nv
                if 0 <= jj < nv:
                    acc += N[:, jj].sum(0)
            n = np.linalg.norm(acc)
            N[i, j] = acc / n if n > 1e-12 else np.array([0, 0, 1.0])
    return N


def grid_surface(P, close_u=False, close_v=False, N=None, UV=None, flip=False):
    """Tessellate a (nu, nv, 3) grid of surface points.

    Orientation: the face normal is dP/du x dP/dv (flip=True reverses it).
    Quads are split along their shorter diagonal.
    """
    P = np.asarray(P, float)
    nu, nv = P.shape[:2]
    if N is None:
        N = grid_normals(P, close_u, close_v)
    iu = np.arange(nu if close_u else nu - 1)
    jv = np.arange(nv if close_v else nv - 1)
    I, J = np.meshgrid(iu, jv, indexing="ij")
    I, J = I.ravel(), J.ravel()
    a = (I % nu) * nv + (J % nv)
    b = ((I + 1) % nu) * nv + (J % nv)
    c = ((I + 1) % nu) * nv + ((J + 1) % nv)
    d = (I % nu) * nv + ((J + 1) % nv)
    V = P.reshape(-1, 3)
    dac = np.linalg.norm(V[a] - V[c], axis=1)
    dbd = np.linalg.norm(V[b] - V[d], axis=1)
    use_ac = dac <= dbd
    F1 = np.where(use_ac[:, None], np.stack([a, b, c], 1), np.stack([a, b, d], 1))
    F2 = np.where(use_ac[:, None], np.stack([a, c, d], 1), np.stack([b, c, d], 1))
    F = np.vstack([F1, F2])
    if UV is None:
        uu, vv = np.meshgrid(np.linspace(0, 1, nu), np.linspace(0, 1, nv), indexing="ij")
        UV = np.stack([uu, vv], -1)
    m = Mesh(V.copy(), F, N.reshape(-1, 3).copy(), np.asarray(UV, float).reshape(-1, 2).copy())
    m.remove_degenerate()
    if flip:
        m = m.flipped()
    return m


# --------------------------------------------------------------------------
# implicit trimming (marching triangles)
# --------------------------------------------------------------------------

def trim(mesh: Mesh, field, keep="positive"):
    """Cut a mesh along the zero set of a per-vertex scalar field.

    keep='positive' keeps the region field >= 0, 'negative' keeps field < 0.
    Cut vertices are interpolated linearly (position, normal, uv) and shared
    between neighbouring triangles so the new boundary is watertight.
    """
    s = np.asarray(field, float).copy()
    if keep == "negative":
        s = -s
    s[np.abs(s) < 1e-9] = 1e-9  # avoid exact zeros (degenerate cuts)
    inside = s > 0
    F = mesh.F
    cnt = inside[F].sum(1)
    keepF = [F[cnt == 3]]
    part = F[(cnt == 1) | (cnt == 2)]
    V, N = [mesh.V], [mesh.N]
    UV = [mesh.UV] if mesh.UV is not None else None
    base = len(mesh.V)
    cache = {}
    newV, newN, newUV = [], [], []

    def cut(i, j):
        key = (i, j) if i < j else (j, i)
        if key in cache:
            return cache[key]
        t = s[i] / (s[i] - s[j])
        p = mesh.V[i] + t * (mesh.V[j] - mesh.V[i])
        n = mesh.N[i] + t * (mesh.N[j] - mesh.N[i])
        n = n / max(np.linalg.norm(n), 1e-12)
        newV.append(p)
        newN.append(n)
        if UV is not None:
            newUV.append(mesh.UV[i] + t * (mesh.UV[j] - mesh.UV[i]))
        idx = base + len(newV) - 1
        cache[key] = idx
        return idx

    tris = []
    for tri in part:
        ins = inside[tri]
        k = int(ins.sum())
        # rotate so the odd vertex comes first
        if k == 1:
            r = int(np.argmax(ins))
        else:
            r = int(np.argmin(ins))
        a, b, c = tri[r], tri[(r + 1) % 3], tri[(r + 2) % 3]
        if k == 1:        # a inside, b c outside
            tris.append((a, cut(a, b), cut(a, c)))
        else:             # a outside, b c inside
            eab, eac = cut(a, b), cut(a, c)
            tris.append((eab, b, c))
            tris.append((eab, c, eac))
    if tris:
        keepF.append(np.array(tris, np.int64))
    if newV:
        V.append(np.array(newV))
        N.append(np.array(newN))
        if UV is not None:
            UV.append(np.array(newUV))
    out = Mesh(np.vstack(V), np.vstack(keepF), np.vstack(N), np.vstack(UV) if UV is not None else None)
    out.compact()
    return out


def trim_fn(mesh: Mesh, fn, keep="positive"):
    """Trim with a field function evaluated on the mesh (fn(mesh) -> per-vertex values)."""
    return trim(mesh, fn(mesh), keep)


def band(mesh: Mesh, fn, lo, hi):
    """Keep the region lo <= fn(mesh) <= hi (field re-evaluated after each cut)."""
    a = trim(mesh, fn(mesh) - hi, "negative")
    return trim(a, fn(a) - lo, "positive")


def boundary_loops(mesh: Mesh):
    """Return the list of directed boundary loops (arrays of vertex ids)."""
    F = mesh.F
    e = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    key = np.sort(e, 1)
    _, inv, counts = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    b = e[counts[inv.ravel()] == 1]
    nxt = {}
    for a, c in b:
        nxt[int(a)] = int(c)
    loops, seen = [], set()
    for start in list(nxt.keys()):
        if start in seen:
            continue
        loop, cur = [], start
        while cur not in seen and cur in nxt:
            seen.add(cur)
            loop.append(cur)
            cur = nxt[cur]
        if len(loop) > 2:
            loops.append(np.array(loop))
    return loops


def solidify(skin: Mesh, thickness, rim=True, separate=False):
    """Turn an open skin patch into a closed slab: outer skin + inner skin + rim.
    separate=True returns (outer, inner_and_rims) instead of one merged mesh."""
    outer = skin.copy()
    inner = skin.offset(-thickness).flipped()
    parts = [outer, inner]
    if rim:
        for loop in boundary_loops(skin):
            a = skin.V[loop]
            b = skin.V[np.roll(loop, -1)]
            na = skin.N[loop]
            ai = a - thickness * na
            bi = b - thickness * skin.N[np.roll(loop, -1)]
            n = len(loop)
            V = np.vstack([a, b, bi, ai])
            idx = np.arange(n)
            F = np.vstack([np.stack([idx, idx + n, idx + 2 * n], 1),
                           np.stack([idx, idx + 2 * n, idx + 3 * n], 1)])
            m = Mesh(V, F)
            # flat, crisp normals for the rim
            fn = m.face_normals()
            Nr = np.zeros_like(V)
            for k in range(3):
                np.add.at(Nr, F[:, k], fn)
            m.N, _ = _normalize(Nr, fallback=np.array([0, 0, 1.0]))
            parts.append(m)
    if separate:
        return outer, Mesh.merge(parts[1:])
    return Mesh.merge(parts)


# --------------------------------------------------------------------------
# primitive generators
# --------------------------------------------------------------------------

def revolve(profile, n=48, axis_origin=(0, 0, 0), axis_dir=(1, 0, 0), ref_dir=None,
            a0=0.0, a1=2 * np.pi, cap_ends=False):
    """Surface of revolution.  profile = [(s, r), ...] with s along the axis.

    Normals point away from the axis when the profile runs in +s with r > 0.
    """
    prof = np.asarray(profile, float)
    o = np.asarray(axis_origin, float)
    ax = np.asarray(axis_dir, float)
    ax = ax / np.linalg.norm(ax)
    if ref_dir is None:
        ref = np.array([0, 0, 1.0]) if abs(ax[2]) < 0.9 else np.array([0, 1.0, 0])
    else:
        ref = np.asarray(ref_dir, float)
    e1 = ref - ax * np.dot(ref, ax)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(ax, e1)
    full = abs((a1 - a0) - 2 * np.pi) < 1e-9
    th = np.linspace(a0, a1, n, endpoint=not full)
    th = -th  # orientation so that normals point outward
    c, s = np.cos(th), np.sin(th)
    P = (o[None, None, :] + prof[:, 0, None, None] * ax[None, None, :]
         + prof[:, 1, None, None] * (c[None, :, None] * e1[None, None, :] + s[None, :, None] * e2[None, None, :]))
    m = grid_surface(P, close_u=False, close_v=full)
    if cap_ends:
        caps = []
        for k, sign in ((0, -1), (-1, 1)):
            r = prof[k, 1]
            if r > 1e-6:
                caps.append(disk(o + prof[k, 0] * ax, sign * ax, r, n=n, ref=e1))
        m = Mesh.merge([m] + caps)
    return m


def disk(center, normal, r, n=32, ref=None, r_inner=0.0):
    nrm = np.asarray(normal, float)
    nrm = nrm / np.linalg.norm(nrm)
    if ref is None:
        ref = np.array([0, 0, 1.0]) if abs(nrm[2]) < 0.9 else np.array([1.0, 0, 0])
    e1 = np.asarray(ref, float) - nrm * np.dot(ref, nrm)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(nrm, e1)
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    ring = np.asarray(center)[None] + r * (np.cos(th)[:, None] * e1 + np.sin(th)[:, None] * e2)
    if r_inner > 0:
        ring2 = np.asarray(center)[None] + r_inner * (np.cos(th)[:, None] * e1 + np.sin(th)[:, None] * e2)
        V = np.vstack([ring, ring2])
        i = np.arange(n)
        j = (i + 1) % n
        F = np.vstack([np.stack([i, j, j + n], 1), np.stack([i, j + n, i + n], 1)])
    else:
        V = np.vstack([ring, np.asarray(center)[None]])
        i = np.arange(n)
        F = np.stack([i, (i + 1) % n, np.full(n, n)], 1)
    N = np.tile(nrm, (len(V), 1))
    m = Mesh(V, F, N)
    # make winding agree with the normal
    fn = m.face_normals()
    if np.dot(fn.mean(0), nrm) < 0:
        m.F = m.F[:, ::-1].copy()
    return m


def parallel_transport_frames(path):
    path = np.asarray(path, float)
    T = np.gradient(path, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    ref = np.array([0, 0, 1.0]) if abs(T[0, 2]) < 0.9 else np.array([0, 1.0, 0])
    Nn = np.cross(T[0], ref)
    Nn /= np.linalg.norm(Nn)
    Ns = [Nn]
    for i in range(1, len(path)):
        v = np.cross(T[i - 1], T[i])
        sv = np.linalg.norm(v)
        n = Ns[-1]
        if sv > 1e-9:
            ang = np.arctan2(sv, np.dot(T[i - 1], T[i]))
            n = rotation_matrix(v / sv, ang) @ n
        n = n - T[i] * np.dot(n, T[i])
        n /= np.linalg.norm(n)
        Ns.append(n)
    Ns = np.array(Ns)
    Bs = np.cross(T, Ns)
    return T, Ns, Bs


def sweep_profile(path, profile2d, closed_profile=True, scale=None, twist=None, cap=True):
    """Sweep a 2-D profile (in the path's normal/binormal plane) along a 3-D path."""
    path = np.asarray(path, float)
    prof = np.asarray(profile2d, float)
    T, Nn, B = parallel_transport_frames(path)
    ns = len(path)
    sc = np.ones(ns) if scale is None else np.broadcast_to(np.asarray(scale, float), (ns,))
    tw = np.zeros(ns) if twist is None else np.broadcast_to(np.asarray(twist, float), (ns,))
    P = np.zeros((ns, len(prof), 3))
    for i in range(ns):
        c, s = np.cos(tw[i]), np.sin(tw[i])
        pu = prof[:, 0] * c - prof[:, 1] * s
        pv = prof[:, 0] * s + prof[:, 1] * c
        P[i] = path[i] + sc[i] * (pu[:, None] * Nn[i] + pv[:, None] * B[i])
    m = grid_surface(P, close_u=False, close_v=closed_profile)
    # make the side wall's normals point away from the path
    radial = (P - path[:, None, :]).reshape(-1, 3)
    if len(m.V) == len(radial) and np.mean(np.sum(radial * m.N, axis=1)) < 0:
        m = m.flipped()
    elif len(m.V) != len(radial):
        d = np.linalg.norm(m.V[:, None, :] - path[None, :, :], axis=2)
        rr = m.V - path[np.argmin(d, axis=1)]
        if np.mean(np.sum(rr * m.N, axis=1)) < 0:
            m = m.flipped()
    parts = [m]
    if cap and closed_profile:
        for k in (0, -1):
            ring = P[k]
            c = ring.mean(0)
            V = np.vstack([ring, c[None]])
            n = len(ring)
            i = np.arange(n)
            F = np.stack([i, (i + 1) % n, np.full(n, n)], 1)
            nrm = -T[0] if k == 0 else T[-1]
            cm = Mesh(V, F, np.tile(nrm, (n + 1, 1)))
            if np.dot(cm.face_normals().mean(0), nrm) < 0:
                cm.F = cm.F[:, ::-1].copy()
            parts.append(cm)
    out = Mesh.merge(parts)
    return out


def circle2d(r, n=16, rx=None):
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.stack([(rx if rx is not None else r) * np.cos(th), r * np.sin(th)], 1)


def sweep_tube(path, radius, n=16, cap=True, scale=None):
    return sweep_profile(path, circle2d(radius, n), True, scale=scale, cap=cap)


def fix_outward(m: Mesh, center=None, path=None):
    """Heuristic: flip the side wall if normals point toward the sweep path."""
    if path is not None:
        path = np.asarray(path, float)
        # distance from each vertex to nearest path point
        d = np.linalg.norm(m.V[:, None, :] - path[None, :, :], axis=2)
        nearest = path[np.argmin(d, axis=1)]
        out = m.V - nearest
        sgn = np.sum(out * m.N, axis=1)
        if np.mean(sgn) < 0:
            return m.flipped()
        return m
    c = np.asarray(center, float)
    if np.mean(np.sum((m.V - c) * m.N, axis=1)) < 0:
        return m.flipped()
    return m


def cylinder(p0, p1, r, n=24, cap=True):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    L = np.linalg.norm(p1 - p0)
    return revolve([(0, r), (L, r)], n=n, axis_origin=p0, axis_dir=(p1 - p0) / L, cap_ends=cap)


def superellipsoid(center, radii, e=(0.25, 0.25), nu=24, nv=32, R=None):
    """Rounded box / pillow shape: |x/a|^(2/e2)+... ; e close to 0 = boxy, 1 = ellipsoid."""
    a, b, c = radii
    e1, e2 = e
    u = np.linspace(-np.pi / 2, np.pi / 2, nu)
    v = np.linspace(-np.pi, np.pi, nv, endpoint=False)
    U, Vv = np.meshgrid(u, v, indexing="ij")

    def sp(w, m):
        return np.sign(np.sin(w)) * np.abs(np.sin(w)) ** m

    def cp(w, m):
        return np.sign(np.cos(w)) * np.abs(np.cos(w)) ** m

    X = a * cp(U, e1) * cp(Vv, e2)
    Y = b * cp(U, e1) * sp(Vv, e2)
    Z = c * sp(U, e1)
    P = np.stack([X, Y, Z], -1)
    m = grid_surface(P, close_u=False, close_v=True)
    # outward check
    if np.mean(np.sum(m.V * m.N, axis=1)) < 0:
        m = m.flipped()
    if R is not None:
        M = np.eye(4)
        M[:3, :3] = R
        m = m.transformed(M)
    return m.translated(center)


def box(center, size, R=None):
    """Flat-shaded box (24 vertices)."""
    sx, sy, sz = np.asarray(size, float) / 2
    faces = []
    dirs = [((1, 0, 0), (0, 1, 0), (0, 0, 1)), ((-1, 0, 0), (0, 0, 1), (0, 1, 0)),
            ((0, 1, 0), (0, 0, 1), (1, 0, 0)), ((0, -1, 0), (1, 0, 0), (0, 0, 1)),
            ((0, 0, 1), (1, 0, 0), (0, 1, 0)), ((0, 0, -1), (0, 1, 0), (1, 0, 0))]
    V, F, N = [], [], []
    h = np.array([sx, sy, sz])
    for n, t1, t2 in dirs:
        n, t1, t2 = map(np.array, (n, t1, t2))
        c = n * h
        e1 = t1 * h
        e2 = t2 * h
        base = len(V)
        for s1, s2 in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            V.append(c + s1 * e1 + s2 * e2)
            N.append(n)
        # orientation
        q = [base, base + 1, base + 2, base + 3]
        tri1 = (q[0], q[1], q[2])
        vv = np.array(V)
        fn = np.cross(vv[q[1]] - vv[q[0]], vv[q[2]] - vv[q[0]])
        if np.dot(fn, n) < 0:
            F += [(q[0], q[2], q[1]), (q[0], q[3], q[2])]
        else:
            F += [(q[0], q[1], q[2]), (q[0], q[2], q[3])]
    m = Mesh(np.array(V, float), np.array(F), np.array(N, float))
    if R is not None:
        M = np.eye(4)
        M[:3, :3] = R
        m = m.transformed(M)
    return m.translated(center)


def loft(sections, close_v=True, smooth=True, n_interp=0):
    """Loft through a list of (nv,3) point rings/curves (same nv).

    smooth=True inserts n_interp Catmull-Rom interpolated sections between
    the given ones for a C1 skin.
    """
    S = np.asarray(sections, float)
    if smooth and n_interp > 0 and len(S) >= 3:
        out = []
        ns = len(S)
        for i in range(ns - 1):
            p0 = S[max(i - 1, 0)]
            p1 = S[i]
            p2 = S[i + 1]
            p3 = S[min(i + 2, ns - 1)]
            for k in range(n_interp + 1):
                t = k / (n_interp + 1)
                t2, t3 = t * t, t * t * t
                out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                                  + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
        out.append(S[-1])
        S = np.array(out)
    return grid_surface(S, close_u=False, close_v=close_v)


def cap_ring(ring, normal_hint):
    """Fan-triangulate a planar-ish closed ring (convex or star-shaped)."""
    ring = np.asarray(ring, float)
    c = ring.mean(0)
    n = len(ring)
    V = np.vstack([ring, c[None]])
    i = np.arange(n)
    F = np.stack([i, (i + 1) % n, np.full(n, n)], 1)
    nh = np.asarray(normal_hint, float)
    nh = nh / np.linalg.norm(nh)
    m = Mesh(V, F, np.tile(nh, (n + 1, 1)))
    if np.dot(m.face_normals().mean(0), nh) < 0:
        m.F = m.F[:, ::-1].copy()
    return m


# --------------------------------------------------------------------------
# curves
# --------------------------------------------------------------------------

def pchip(xk, yk):
    """Monotone piecewise-cubic Hermite interpolant (no overshoot) -> callable."""
    from scipy.interpolate import PchipInterpolator
    f = PchipInterpolator(np.asarray(xk, float), np.asarray(yk, float), extrapolate=True)
    return f


def cspline(xk, yk, bc="natural"):
    from scipy.interpolate import CubicSpline
    return CubicSpline(np.asarray(xk, float), np.asarray(yk, float), bc_type=bc)


def cosine_spacing(n, a=0.0, b=1.0):
    t = 0.5 * (1 - np.cos(np.linspace(0, np.pi, n)))
    return a + (b - a) * t


def densify(stations, max_step):
    """Insert points so no gap exceeds max_step (keeps the given stations)."""
    st = np.unique(np.asarray(stations, float))
    out = [st[0]]
    for a, b in zip(st[:-1], st[1:]):
        k = int(np.ceil((b - a) / max_step))
        out += list(np.linspace(a, b, k + 1)[1:])
    return np.array(out)


# --------------------------------------------------------------------------
# planar polygon triangulation (ear clipping)
# --------------------------------------------------------------------------

def _ear_clip(P2):
    n = len(P2)
    idx = list(range(n))
    # orientation (make CCW)
    area = 0.5 * np.sum(P2[:, 0] * np.roll(P2[:, 1], -1) - np.roll(P2[:, 0], -1) * P2[:, 1])
    if area < 0:
        idx = idx[::-1]
    tris = []

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    guard = 0
    while len(idx) > 3 and guard < 10 * n * n:
        guard += 1
        m = len(idx)
        found = False
        for k in range(m):
            i0, i1, i2 = idx[(k - 1) % m], idx[k], idx[(k + 1) % m]
            a, b, c = P2[i0], P2[i1], P2[i2]
            if cross(a, b, c) <= 1e-14:
                continue
            ok = True
            for j in idx:
                if j in (i0, i1, i2):
                    continue
                p = P2[j]
                if cross(a, b, p) >= -1e-14 and cross(b, c, p) >= -1e-14 and cross(c, a, p) >= -1e-14:
                    ok = False
                    break
            if ok:
                tris.append((i0, i1, i2))
                idx.pop(k)
                found = True
                break
        if not found:
            # degenerate: fall back to fan
            for k in range(1, len(idx) - 1):
                tris.append((idx[0], idx[k], idx[k + 1]))
            idx = idx[:3] if len(idx) >= 3 else idx
            break
    if len(idx) == 3:
        tris.append(tuple(idx))
    return np.array(tris, np.int64)


def planar_cap(pts, normal):
    """Triangulate a (non-convex) planar-ish polygon; normal sets the facing side."""
    pts = np.asarray(pts, float)
    # drop duplicate consecutive points
    keep = np.ones(len(pts), bool)
    d = np.linalg.norm(pts - np.roll(pts, 1, 0), axis=1)
    keep[d < 1e-9] = False
    pts = pts[keep]
    nrm = np.asarray(normal, float)
    nrm = nrm / np.linalg.norm(nrm)
    ref = np.array([1.0, 0, 0]) if abs(nrm[0]) < 0.9 else np.array([0, 1.0, 0])
    e1 = ref - nrm * np.dot(ref, nrm)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(nrm, e1)
    P2 = np.stack([pts @ e1, pts @ e2], 1)
    Fc = _ear_clip(P2)
    m = Mesh(pts, Fc, np.tile(nrm, (len(pts), 1)))
    fn = m.face_normals()
    if len(fn) and np.dot(fn.mean(0), nrm) < 0:
        m.F = m.F[:, ::-1].copy()
    return m
