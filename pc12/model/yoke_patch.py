"""
Explicit, crease-exact patches stitched into the yoke's smooth moulding mesh (model/yoke_mesh.py):

  cut()          cut a region out of a mesh that lies on a field's zero level: every vertex near the cut snapped onto
                 the cut curve first (no slivers), the crossing edges split, every new boundary vertex projected
                 exactly onto the curve {field = 0, cut = 0} (two-constraint Newton); returns the kept mesh and its
                 boundary loops.
  pad_pocket()   a grip's pad pocket (yoke_geom.pad_finish: the frame's inner wall, the groove floor 1.0 x 0.5, the
                 bead R 0.4 on the leather's edge, the crowned leather) as a structured strip of columns at the cut
                 loop's vertices (the frame's inner edge, a tabled crease) + the leather inside it.
Coordinates: yoke-local mm (co-pilot sense); the grips' own sense (u > 0 away from the yoke centreline) inside.
"""
from __future__ import annotations

import math

import numpy as np

from model import yoke_geom as G
from model import yoke_mesh as YM


def _unit(v):
    v = np.asarray(v, float)
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-15)


def num_grad(fn, P, e=0.003):
    P = np.asarray(P, float)
    g = []
    for k in range(3):
        d = np.zeros(3)
        d[k] = e
        g.append((fn(P + d) - fn(P - d)) / (2 * e))
    return np.stack(g, -1)


def project2(name, cfun, P, iters=8):
    """Points P onto the curve {field `name` = 0, cfun = 0}: minimal-norm Newton steps."""
    P = np.asarray(P, float).copy()
    for _ in range(iters):
        f = YM.evaluate(name, P)
        gf = YM._grad_raw(name, P, 0.003)
        c = cfun(P)
        gc = num_grad(cfun, P)
        J = np.stack([gf, gc], 1)                                   # (n, 2, 3)
        JJ = np.einsum("nij,nkj->nik", J, J)
        det = JJ[:, 0, 0] * JJ[:, 1, 1] - JJ[:, 0, 1] * JJ[:, 1, 0]
        det = np.where(np.abs(det) < 1e-12, 1e-12, det)
        inv = np.stack([np.stack([JJ[:, 1, 1], -JJ[:, 0, 1]], -1), np.stack([-JJ[:, 1, 0], JJ[:, 0, 0]], -1)], 1) / \
            det[:, None, None]
        r = np.stack([f, c], -1)
        step = np.einsum("nij,ni->nj", J, np.einsum("nij,nj->ni", inv, r))
        P = P - step
    return P


def cut(V, F, N, name, cfun, snap=0.3):
    """Remove the part of the closed mesh (V, F, N) on the field `name`'s zero level where cfun < 0: (V, F, N, loops)
    -- loops = the boundary loops (vertex ids, the kept side on the left), every boundary vertex exactly on
    {field = 0, cfun = 0} with the field's normal."""
    V, F, N = np.asarray(V, float).copy(), np.asarray(F, np.int64), np.asarray(N, float).copy()
    c = cfun(V)
    E, EF, _ = YM._edges(F)
    L = np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1)
    lmin = np.full(len(V), np.inf)
    np.minimum.at(lmin, E[:, 0], L)
    np.minimum.at(lmin, E[:, 1], L)
    # snap the vertices near the cut onto it (their c := 0), only where a neighbour lies on the other side
    sgn = np.sign(c)
    opp = np.zeros(len(V), bool)
    cross = sgn[E[:, 0]] * sgn[E[:, 1]] < 0
    opp[E[cross].ravel()] = True
    near = opp & (np.abs(c) < snap * lmin)
    if near.any():
        V[near] = project2(name, cfun, V[near])
        c[near] = 0.0
    # split: vertex classes +1 (keep), -1 (drop), 0 (on the cut)
    cls = np.where(np.abs(c) < 1e-12, 0, np.sign(c)).astype(int)
    newV, cache = [], {}
    base = len(V)

    def mid(i, j):
        k = (min(i, j), max(i, j))
        if k not in cache:
            t = c[i] / (c[i] - c[j])
            newV.append(V[i] + t * (V[j] - V[i]))
            cache[k] = base + len(newV) - 1
        return cache[k]
    S = cls[F]
    keep_all = (S >= 0).all(1)
    mixed = ~keep_all & ~(S <= 0).all(1)
    out = []
    for tri in F[mixed]:
        s = cls[tri]
        r = int(np.argmax(s > 0))
        a, b, cc = tri[r], tri[(r + 1) % 3], tri[(r + 2) % 3]
        sa, sb, sc = s[r], s[(r + 1) % 3], s[(r + 2) % 3]
        poly = []                                           # the kept vertices and cut points round the triangle
        for (p_, sp), (q, sq) in (((a, sa), (b, sb)), ((b, sb), (cc, sc)), ((cc, sc), (a, sa))):
            if sp >= 0:
                poly.append(p_)
            if sp * sq < 0:
                poly.append(mid(p_, q))
        for k in range(1, len(poly) - 1):
            out.append((poly[0], poly[k], poly[k + 1]))
    F2 = np.vstack([F[keep_all], np.array(out, np.int64).reshape(-1, 3)])
    if newV:
        Pn = project2(name, cfun, np.array(newV))
        V = np.vstack([V, Pn])
        N = np.vstack([N, np.zeros((len(Pn), 3))])
    F2 = F2[(F2[:, 0] != F2[:, 1]) & (F2[:, 1] != F2[:, 2]) & (F2[:, 0] != F2[:, 2])]
    used = np.zeros(len(V), bool)
    used[F2.ravel()] = True
    rm = -np.ones(len(V), np.int64)
    rm[used] = np.arange(used.sum())
    V, N, F2 = V[used], N[used], rm[F2]
    # exact normals on the boundary
    E2, EF2, _ = YM._edges(F2)
    bnd = np.unique(E2[EF2[:, 1] < 0].ravel())
    N[bnd] = _unit(YM._grad_raw(name, V[bnd], 0.003))
    return V, F2, N, boundary_loops(F2)


def boundary_loops(F):
    """Directed boundary loops of F (each a vertex-id array; the faces on the left of the loop's direction)."""
    e = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    key = np.sort(e, 1)
    _, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    b = e[cnt[inv.ravel()] == 1]
    nxt = {int(a): int(c) for a, c in b}
    loops, seen = [], set()
    for s in list(nxt):
        if s in seen:
            continue
        loop, cur = [], s
        while cur not in seen and cur in nxt:
            seen.add(cur)
            loop.append(cur)
            cur = nxt[cur]
        if len(loop) > 2:
            loops.append(np.array(loop))
    return loops


# ============================================================================================ the pad pockets
BEAD_ROWS = 5            # rows over the bead's half round R 0.4 (36 deg each: chord sag 0.0196 mm < cad.res interior 0.02)
LEATHER_FILL = ((3.2, 0.0, 8.0), (6.0, 8.0, 1e9))   # the leather's fill points: spacing (mm) by depth inside the bead
#                                                    (the crown rises over the first 8; flat beyond)
LEATHER_TOL, LEATHER_MIN, LEATHER_ROUNDS = 3.2, 0.5, 4     # the leather's highlight criterion (deg: satin, under
#                                                          the viewer's pebble bump), point spacing (mm), rounds -- rev O
#                                                          (3-D judges r2 CR2-03: at 4 deg a ring of 4-8 deg blobs 5-10 mm
#                                                          inside each outline drew a sawtooth in the zebra / at grazing
#                                                          light; rev N 4.0 / 0.6 / 3: 4,993 leather faces a yoke; 3.0:
#                                                          5,471; the judges' 2.0: 6,341, over build.YOKE_BUDGET; 3.2)


def _plane_maps(g):
    """Grip g's plane coordinates (own sense): to_plane(P) -> (uf, hf, z), from_plane(uf, hf, z) -> P, and the
    Jacobian M (3 x 3, columns d P / d(uf, hf, z)) for the normals (n3 ~ M^-T grad)."""
    f = G.grip_frame(g)
    n = f["n"]
    w = G._gsel("grip_walls", g)
    e = (1.0 - w) * n + w * np.array([0.0, 0.0, 1.0])
    e /= np.linalg.norm(e)
    ne = float(n @ e)

    def from_plane(uf, hf, z):
        uf, hf, z = (np.asarray(x, float) for x in (uf, hf, z))
        a = G.grip_plane_a(uf, hf, g)
        return np.stack([uf, hf, a], -1) + (z / ne)[..., None] * e
    M = np.stack([np.array([1.0, 0.0, -f["tt"]]), np.array([0.0, 1.0, -f["tr"]]), e / ne], 1)
    Minv_T = np.linalg.inv(M).T

    def to_plane(P):
        P = np.asarray(P, float)
        z, uf, hf = G._to_plane(P[..., 0], P[..., 1], P[..., 2], g)
        return uf, hf, z
    return to_plane, from_plane, Minv_T


def pad_pocket(V, N, loop, g):
    """The pad pocket of grip g as [(V, F, N, material)] (co-pilot sense) stitched to the cut loop `loop` (vertex ids
    of the frame mesh V / N, running with the frame on its left).  yoke_geom.pad_finish: the wall along the pad outline
    (the frame's inner edge: a crease) down to the groove floor -rec - gd, the floor gw wide, the bead's inner wall
    and half round (R bead) on the leather's edge, the leather crowned inside (yoke_geom._leather)."""
    D = G.T()
    rec, cen, wc, bead, gw, gd = (float(x) for x in D["pad_section"][:6])
    sg = 1.0 if g == "out" else -1.0
    m3 = np.array([sg, 1.0, 1.0])
    to_plane, from_plane, MiT = _plane_maps(g)
    P0 = V[loop] * m3
    uf, hf, z0 = to_plane(P0)
    Fp = G.field("pad_" + g, G.pad_outline(g))
    e = 0.01
    gx = (Fp(uf + e, hf) - Fp(uf - e, hf)) / (2 * e)
    gy = (Fp(uf, hf + e) - Fp(uf, hf - e)) / (2 * e)
    m = -_unit(np.c_[gx, gy])                                   # inward (into the pad)
    k = len(loop)
    zf = -rec - gd
    sb = gw + bead                                               # bead centre

    def lea(u_, h_):
        return G._leather(u_, h_, g)
    # junction angle per column: the bead meets the leather
    lo, hi = np.zeros(k), np.full(k, 0.5 * math.pi)
    for _ in range(30):
        th = 0.5 * (lo + hi)
        s_ = sb + bead * np.cos(th)
        zb = -rec + bead * np.sin(th)
        fv = zb - lea(uf + s_ * m[:, 0], hf + s_ * m[:, 1])
        lo = np.where(fv > 0, lo, th)
        hi = np.where(fv > 0, th, hi)
    th_star = 0.5 * (lo + hi)
    rows = []                         # (s, z, normal (plane coords: along m, z)) per row, per column arrays
    rows.append((np.zeros(k), z0, ("wall",)))
    rows.append((np.zeros(k), np.full(k, zf), ("wall",)))
    rows.append((np.zeros(k), np.full(k, zf), ("floor",)))
    rows.append((np.full(k, gw), np.full(k, zf), ("floor",)))
    rows.append((np.full(k, gw), np.full(k, zf), ("iwall",)))
    for j in range(BEAD_ROWS + 1):
        th = math.pi + (th_star - math.pi) * j / BEAD_ROWS
        rows.append((sb + bead * np.cos(th), -rec + bead * np.sin(th), ("bead", th)))
    rows.append((sb + bead * np.cos(th_star), -rec + bead * np.sin(th_star), ("leather",)))
    VV, NN = [], []
    for s_, zz, kind in rows:
        u_, h_ = uf + s_ * m[:, 0], hf + s_ * m[:, 1]
        VV.append(from_plane(u_, h_, zz))
        if kind[0] == "wall":
            ng = np.c_[m, np.zeros(k)]
        elif kind[0] == "floor":
            ng = np.tile([0.0, 0.0, 1.0], (k, 1))
        elif kind[0] == "iwall":
            ng = np.c_[-m, np.zeros(k)]
        elif kind[0] == "bead":
            th = np.asarray(kind[1])
            ng = np.c_[np.cos(th)[..., None] * m, np.broadcast_to(np.sin(th), (k,))[:, None]]
        else:
            lu = (lea(u_ + e, h_) - lea(u_ - e, h_)) / (2 * e)
            lh = (lea(u_, h_ + e) - lea(u_, h_ - e)) / (2 * e)
            ng = np.c_[-lu, -lh, np.ones(k)]
        NN.append(_unit(ng @ MiT.T))
    VV, NN = np.array(VV), np.array(NN)                         # (rows, k, 3)
    nr = len(rows)
    # the strip: quads between rows r, r + 1 of columns i, i + 1, skipping the zero-length crease rows
    ids = np.arange(nr * k).reshape(nr, k)
    F = []
    crease_pairs = {(0, 1): False, (1, 2): True, (2, 3): False, (3, 4): True, (4, 5): False}
    for r in range(nr - 1):
        if crease_pairs.get((r, r + 1), False):
            continue                                            # same positions, different normals
        if r == nr - 2:
            continue                                            # bead's last row -> leather row: the crease (same pos)
        for i in range(k):
            j = (i + 1) % k
            F += [(ids[r, i], ids[r, j], ids[r + 1, j]), (ids[r, i], ids[r + 1, j], ids[r + 1, i])]
    Vs = VV.reshape(-1, 3)
    Ns = NN.reshape(-1, 3)
    pieces = []
    # strip pieces by material: rows 0..4 frame / groove (grip_black), the bead and leather rows (leather_black)
    F = np.array(F, np.int64)
    row_of = (F // k).min(1)
    mat = np.where(row_of >= 4, "leather_black", "grip_black")
    # the leather inside the junction loop
    Lr = rows[-1]
    ul, hl = uf + Lr[0] * m[:, 0], hf + Lr[0] * m[:, 1]
    B = np.c_[ul, hl]
    from model import yoke_tri as YT
    from scipy.spatial import cKDTree
    from matplotlib.path import Path
    lo2, hi2 = B.min(0), B.max(0)
    path = Path(np.vstack([B, B[:1]]))
    pts = []
    for hx, smin, smax in LEATHER_FILL:
        ys = np.arange(lo2[1], hi2[1], hx * math.sqrt(3) / 2)
        for jj, y in enumerate(ys):
            xs = np.arange(lo2[0] + (0.5 * hx if jj % 2 else 0.0), hi2[0], hx)
            Q = np.c_[xs, np.full_like(xs, y)]
            Q = Q[path.contains_points(Q)]
            if not len(Q):
                continue
            dd = -Fp(Q[:, 0], Q[:, 1]) - Lr[0].mean()
            d2b, _ = cKDTree(B).query(Q)
            Q = Q[(dd >= smin) & (dd < smax) & (d2b > 0.6 * hx)]
            pts.append(Q)
    Gp = np.vstack(pts) if pts else np.zeros((0, 2))

    def lnorm(Q):
        lu_ = (lea(Q[:, 0] + e, Q[:, 1]) - lea(Q[:, 0] - e, Q[:, 1])) / (2 * e)
        lh_ = (lea(Q[:, 0], Q[:, 1] + e) - lea(Q[:, 0], Q[:, 1] - e)) / (2 * e)
        return _unit(np.c_[-lu_, -lh_, np.ones(len(Q))] @ MiT.T)
    cons = [(i, (i + 1) % k) for i in range(k)]
    for rd in range(LEATHER_ROUNDS + 1):
        X = np.vstack([B, Gp])
        T = YT.cdt(X, cons)
        T = YT.inside(T, X, [np.arange(k)])
        if rd == LEATHER_ROUNDS:
            break
        # the highlight criterion (yoke_mesh.interp_errors): corner normals interpolated over a face vs the leather's exact
        # normal at its centroid / edge midpoints; failing faces' centroids become fill points
        Nx = lnorm(X)
        err = np.zeros(len(T))
        for w in ((1 / 3, 1 / 3, 1 / 3), (0.5, 0.5, 0.0), (0.0, 0.5, 0.5), (0.5, 0.0, 0.5)):
            w = np.asarray(w)
            S = np.einsum("k,fkd->fd", w, X[T])
            Ni = _unit(np.einsum("k,fkd->fd", w, Nx[T]))
            err = np.maximum(err, np.degrees(np.arccos(np.clip(np.sum(Ni * lnorm(S), 1), -1.0, 1.0))))
        newp = X[T[err > LEATHER_TOL]].mean(1)
        if len(newp):                                   # clear of every point and of the junction loop (no slivers)
            from cad import sdf2d
            newp = newp[(cKDTree(X).query(newp)[0] > LEATHER_MIN) &
                        (sdf2d.polygon(newp[:, 0], newp[:, 1], B) < -LEATHER_MIN)]
        if not len(newp):
            break
        keep = np.ones(len(newp), bool)
        for i, j in cKDTree(newp).query_pairs(LEATHER_MIN):
            keep[j] = False
        Gp = np.vstack([Gp, newp[keep]])
    zl = lea(Gp[:, 0], Gp[:, 1]) if len(Gp) else np.zeros(0)
    Vl = from_plane(Gp[:, 0], Gp[:, 1], zl) if len(Gp) else np.zeros((0, 3))
    Nl = lnorm(Gp) if len(Gp) else np.zeros((0, 3))
    base = len(Vs)
    Tl = np.where(T < k, ids[nr - 1, np.minimum(T, k - 1)], base + T - k)
    Vs = np.vstack([Vs, Vl])
    Ns = np.vstack([Ns, Nl])
    F = np.vstack([F, Tl])
    mat = np.r_[mat, np.full(len(Tl), "leather_black")]
    # back to the co-pilot sense, faces wound by their normals
    Vs, Ns = Vs * m3, Ns * m3
    fn = np.cross(Vs[F[:, 1]] - Vs[F[:, 0]], Vs[F[:, 2]] - Vs[F[:, 0]])
    flip = np.sum(fn * Ns[F].sum(1), 1) < 0
    F[flip] = F[flip][:, ::-1]
    # the wall's top row IS the loop: positions from the frame mesh exactly
    Vs[:k] = V[loop]
    for mt in np.unique(mat):
        Fm = F[mat == mt]
        u, inv = np.unique(Fm.ravel(), return_inverse=True)
        pieces.append((Vs[u], inv.reshape(-1, 3), Ns[u], str(mt)))
    return pieces


# ============================================================================================ a terrain with grooves
SLOT_FLOOR, SLOT_WALL, SLOT_END = 1 << 40, (1 << 40) + 2, (1 << 40) + 4    # labels of a Terrain's slot pieces (above
#                                                                              every groove label)


class Terrain:
    """A height field z = H(x, y) in a frame (c, ex, ey, ez): the base surface (base(X) -> z, base_normal(X) -> unit
    normals in the frame) cut by V-grooves (yoke_cover.Groove: depth g (1 - 2 dc / w) below the reference height
    ref(X)); H = min(base, ref - depth_k).  Labels: 0 the base, else the groove pieces of yoke_cover (run / side, end
    cones) and, optionally, a recessed SLOT with drafted walls (slot_at: the trim face's rocker slot, rev N).  Its creases
    come from the label grid (yoke_cover's method), forced into a constrained Delaunay triangulation; heights exact,
    normals per piece (split only along the creases)."""

    def __init__(self, grooves, base, base_normal, ref=None, slot=None):
        self.GR, self.base, self.base_normal = grooves, base, base_normal
        self.ref = ref if ref is not None else (lambda X: np.zeros(len(X)))
        self.slot = slot              # (yl, r_end, depth, draft rad): a recessed slot |y| < yl, r < r_end (the trim face)

    def slot_at(self, X):
        """The slot's (label, height) at X (label 0 / height +inf outside it): drafted walls z = -m / tan(draft) for
        m = min(yl - |y|, r_end - r) (the side walls SLOT_WALL + (y > 0), the end walls SLOT_END), its floor SLOT_FLOOR
        at -depth."""
        X = np.atleast_2d(np.asarray(X, float))
        lab = np.zeros(len(X), np.int64)
        z = np.full(len(X), np.inf)
        if self.slot is None:
            return lab, z
        yl, r_end, dep, dr = self.slot
        my = yl - np.abs(X[:, 1])
        mr = r_end - np.hypot(X[:, 0], X[:, 1])
        m = np.minimum(my, mr)
        ins = m > 0.0
        t = math.tan(dr)
        zw = -m / t
        floor = ins & (zw <= -dep)
        wall = ins & ~floor
        z[ins] = np.maximum(zw[ins], -dep)
        lab[floor] = SLOT_FLOOR
        lab[wall & (my <= mr)] = SLOT_WALL + (X[wall & (my <= mr), 1] > 0)
        lab[wall & (my > mr)] = SLOT_END
        return lab, z

    def pieces_at(self, X):
        X = np.asarray(X, float)
        hb = self.base(X)
        rf = self.ref(X)
        best = hb.copy()
        lab = np.zeros(len(X), np.int64)
        for k, gr in enumerate(self.GR):
            dc, run, foot, dirn, vid, side = gr.query(X)
            h = rf - gr.g * (1.0 - 2.0 * dc / gr.w)
            b = h < best
            best = np.where(b, h, best)
            lk = np.where(vid >= 0, 1 + 4096 * k + 2048 + vid, 1 + 4096 * k + 16 * run + (side > 0))
            lab = np.where(b, lk, lab)
        ls, zs = self.slot_at(X)
        b = zs < best
        return np.where(b, ls, lab), np.where(b, zs, best)

    def is_crease(self, la, lb):
        if la >= SLOT_FLOOR or lb >= SLOT_FLOOR:
            return la != lb
        from model import yoke_cover as YC
        return YC.is_crease(la, lb, self.GR)

    def normal(self, lab, X):
        from model import yoke_cover as YC
        X = np.atleast_2d(np.asarray(X, float))
        if lab >= SLOT_FLOOR:
            t = math.tan(self.slot[3])
            if lab == SLOT_FLOOR:
                return np.repeat(np.array([[0.0, 0.0, 1.0]]), len(X), 0)
            if lab == SLOT_END:
                r = np.maximum(np.hypot(X[:, 0], X[:, 1]), 1e-9)
                return _unit(np.c_[-X[:, 0] / r / t, -X[:, 1] / r / t, np.ones(len(X))])
            sy = 1.0 if lab == SLOT_WALL + 1 else -1.0
            return _unit(np.c_[np.zeros(len(X)), np.full(len(X), -sy / t), np.ones(len(X))])
        k, kind, j, sg = YC.decode(lab)
        if k < 0:
            return self.base_normal(X)
        gr = self.GR[k]
        if kind == "run":
            dc, foot, dirn, _ = gr.runs[j].query(X)
            gd = np.c_[-dirn[:, 1], dirn[:, 0]] * sg            # the label's own side (yoke_cover.label_normal)
        else:
            v = X - gr.vertices[j]
            gd = v / np.maximum(np.linalg.norm(v, axis=1), 1e-12)[:, None]
        e = 0.004
        ru = (self.ref(X + [e, 0]) - self.ref(X - [e, 0])) / (2 * e)
        rv = (self.ref(X + [0, e]) - self.ref(X - [0, e])) / (2 * e)
        hx = ru + 2.0 * gr.g / gr.w * gd[:, 0]
        hy = rv + 2.0 * gr.g / gr.w * gd[:, 1]
        return _unit(np.c_[-hx, -hy, np.ones(len(X))])

    def crease_chains(self, hc=0.03, margin=0.6):
        """As yoke_cover.crease_chains for this terrain's label function."""
        from model import yoke_cover as YC
        from model import yoke_tri as YT
        GR = self.GR
        allP = np.vstack([r.P for g in GR for r in g.runs])
        lo = np.floor((allP.min(0) - 2.0) / hc) * hc
        hi = allP.max(0) + 2.0
        nx, ny = int(math.ceil((hi[0] - lo[0]) / hc)) + 1, int(math.ceil((hi[1] - lo[1]) / hc)) + 1
        k = int(round(0.5 / hc))
        cs = k * hc
        cx = np.arange(lo[0], hi[0] + cs, cs) + 0.5 * cs
        cy = np.arange(lo[1], hi[1] + cs, cs) + 0.5 * cs
        CX, CY = np.meshgrid(cx, cy, indexing="ij")
        Cc = np.c_[CX.ravel(), CY.ravel()]
        near = np.zeros(len(Cc), bool)
        for g in GR:
            near |= g.query(Cc)[0] < 0.5 * g.w + margin + 0.71 * cs
        if self.slot is not None:                                   # the slot's edges (walls m < depth x tan + margin)
            yl, r_end, dep, dr = self.slot
            m = np.minimum(yl - np.abs(Cc[:, 1]), r_end - np.hypot(Cc[:, 0], Cc[:, 1]))
            near |= (m > -(margin + 0.71 * cs)) & (m < dep * math.tan(dr) + margin + 0.71 * cs)
        act = np.zeros((nx, ny), bool)
        ii, jj = np.unravel_index(np.nonzero(near)[0], CX.shape)
        for a, b in zip(ii, jj):
            act[a * k:min(nx, (a + 1) * k + 1), b * k:min(ny, (b + 1) * k + 1)] = True
        lab = np.zeros((nx, ny), np.int64)
        I, J = np.nonzero(act)
        X = np.c_[lo[0] + I * hc, lo[1] + J * hc]
        lab[I, J] = self.pieces_at(X)[0]
        pts, C1, C2 = [], [], []
        for axis in (0, 1):
            if axis == 0:
                a, b = lab[:-1, :], lab[1:, :]
                mm = (a != b) & act[:-1, :] & act[1:, :]
            else:
                a, b = lab[:, :-1], lab[:, 1:]
                mm = (a != b) & act[:, :-1] & act[:, 1:]
            ei, ej = np.nonzero(mm)
            la, lb = a[ei, ej], b[ei, ej]
            p0 = np.c_[lo[0] + ei * hc, lo[1] + ej * hc]
            d = np.array([hc, 0.0]) if axis == 0 else np.array([0.0, hc])
            t0, t1 = np.zeros(len(ei)), np.ones(len(ei))
            for _ in range(14):
                tm = 0.5 * (t0 + t1)
                same = self.pieces_at(p0 + tm[:, None] * d)[0] == la
                t0 = np.where(same, tm, t0)
                t1 = np.where(same, t1, tm)
            crease = np.array([self.is_crease(x, y) for x, y in zip(la, lb)], bool)
            P = (p0 + (0.5 * (t0 + t1))[:, None] * d)[crease]
            ei, ej = ei[crease], ej[crease]
            pts.append(P)
            if axis == 0:
                C1.append(np.c_[ei, ej - 1])
                C2.append(np.c_[ei, ej])
            else:
                C1.append(np.c_[ei - 1, ej])
                C2.append(np.c_[ei, ej])
        P, C1, C2 = np.vstack(pts), np.vstack(C1), np.vstack(C2)
        keys = np.r_[C1[:, 0] * (ny + 2) + C1[:, 1], C2[:, 0] * (ny + 2) + C2[:, 1]]
        uk, inv = np.unique(keys, return_inverse=True)
        S = np.zeros((len(uk), 2))
        np.add.at(S, inv, np.r_[P, P])
        Vc = S / np.bincount(inv, minlength=len(uk))[:, None]
        E = np.unique(np.sort(np.c_[inv[:len(P)], inv[len(P):]], 1), axis=0)
        E = E[E[:, 0] != E[:, 1]]
        return [Vc[c] for c in YT.chains([tuple(e) for e in E])]

    def interp_error(self, X, T, lab, crease_v, kB=0):
        """Per triangle: the largest angle (deg) between its corner normals interpolated (then normalised) and its
        piece's exact normal, at the centroid and the three edge midpoints (yoke_cover.terrain_interp_error for this
        terrain; the boundary loop's first kB points carry their own piece's normal)."""
        labi = self.pieces_at(X)[0]
        Lc = np.where(crease_v[T], lab[:, None], labi[T])
        Nc = np.zeros(T.shape + (3,))
        for L in np.unique(Lc):
            m = Lc == L
            Nc[m] = self.normal(int(L), X[T[m]])
        err = np.zeros(len(T))
        for w in ((1 / 3, 1 / 3, 1 / 3), (0.5, 0.5, 0.0), (0.0, 0.5, 0.5), (0.5, 0.0, 0.5)):
            w = np.asarray(w)
            S = np.einsum("k,fkd->fd", w, X[T])
            Ni = _unit(np.einsum("k,fkd->fd", w, Nc))
            Ne = np.zeros_like(Ni)
            for L in np.unique(lab):
                m = lab == L
                Ne[m] = self.normal(int(L), S[m])
            err = np.maximum(err, np.degrees(np.arccos(np.clip(np.sum(Ni * Ne, 1), -1.0, 1.0))))
        return err

    def triangulate(self, B, fill=(1.2, 2.4), chain_tol=0.005, chain_lo=0.8, interp=None):
        """Triangles of the terrain inside the boundary loop B (k, 2): (X points (first k = B), T, labels per
        triangle, crease-vertex mask).  interp = (tol deg, min spacing mm, rounds): the HIGHLIGHT refinement (rev O,
        3-D judges r2 CR2-02) -- where a triangle's interpolated corner normals miss its piece's exact normal by more
        than tol at its centroid / an edge midpoint, the centroid becomes a fill point (clear of every point, the
        creases and the boundary by the min spacing), as the cover's terrain."""
        from model import yoke_cover as YC
        from model import yoke_tri as YT
        from matplotlib.path import Path
        from scipy.spatial import cKDTree
        kB = len(B)
        CP, CE = YC._chain_points(self.crease_chains(), tol=chain_tol, lo=chain_lo)
        path = Path(np.vstack([B, B[:1]]))
        dB, _ = cKDTree(B).query(CP)
        okp = path.contains_points(CP) & (dB > 0.15)
        keep_e = okp[CE[:, 0]] & okp[CE[:, 1]]
        CE = CE[keep_e]
        used = np.unique(CE.ravel())
        remap = -np.ones(len(CP), np.int64)
        remap[used] = np.arange(len(used))
        CP, CE = CP[used], remap[CE]
        feat = cKDTree(np.vstack([B, CP]))
        lo, hi = B.min(0), B.max(0)
        pts = []
        for li, hx in enumerate(fill):
            nxt = fill[li + 1] if li + 1 < len(fill) else 1e9
            ys = np.arange(lo[1], hi[1], hx * math.sqrt(3) / 2)
            for jj, y in enumerate(ys):
                xs = np.arange(lo[0] + (0.5 * hx if jj % 2 else 0.0), hi[0], hx)
                Q = np.c_[xs, np.full_like(xs, y)]
                Q = Q[path.contains_points(Q)]
                if not len(Q):
                    continue
                dd, _ = feat.query(Q)
                pts.append(Q[(dd >= 0.6 * hx) & (dd < 0.6 * nxt)])
        Fp = np.vstack(pts) if pts else np.zeros((0, 2))
        cons = [(i, (i + 1) % kB) for i in range(kB)] + [(kB + a, kB + b) for a, b in CE]
        tol, dmin, rounds = interp if interp else (None, 0.0, 0)
        if interp:
            def _dens(P, step=0.1):
                out = [P[:1]]
                for a, b in zip(P[:-1], P[1:]):
                    n = max(1, int(math.ceil(np.linalg.norm(b - a) / step)))
                    out.append(a + (b - a) * np.linspace(0, 1, n + 1)[1:, None])
                return np.vstack(out)
            feat_dense = cKDTree(np.vstack([_dens(np.vstack([B, B[:1]]))] +
                                           [_dens(CP[e]) for e in CE] if len(CE) else [_dens(np.vstack([B, B[:1]]))]))
        for rd in range(rounds + 1):
            X = np.vstack([B, CP, Fp])
            T = YT.cdt(X, cons)
            T = YT.inside(T, X, [np.arange(kB)])
            lab = self.pieces_at(X[T].mean(1))[0]
            crease_v = np.zeros(len(X), bool)
            crease_v[kB:kB + len(CP)] = True
            if rd == rounds:
                break
            err = self.interp_error(X, T, lab, crease_v, kB)
            newp = X[T[err > tol]].mean(1)
            if len(newp):
                newp = newp[(cKDTree(X).query(newp)[0] > dmin) & (feat_dense.query(newp)[0] > dmin) &
                            path.contains_points(newp)]
            if not len(newp):
                break
            keep = np.ones(len(newp), bool)
            for i, j in cKDTree(newp).query_pairs(dmin):
                keep[j] = False
            Fp = np.vstack([Fp, newp[keep]])
        return X, T, lab, crease_v


# ============================================================================================ the trim face
def trim_frame():
    """The outboard head's round face: centre c and the frame (eu across, ev up, n out of the face)."""
    c, n = G.head_out_face()
    eu, ev = G._facet_frame(c, n)
    return c, eu, ev, n


def trim_cfun(P):
    """Negative on the trim face inside TRIM_CUT_R (and within TRIM_CUT_DEPTH of its plane): the region the trim-face
    terrain replaces."""
    P = np.atleast_2d(np.asarray(P, float))
    c, eu, ev, n = trim_frame()
    Q = P - c
    zf = Q @ n
    rho = np.hypot(Q @ eu, Q @ ev)
    out = np.maximum(rho - TRIM_CUT_R, -(zf + TRIM_CUT_DEPTH))
    return np.where(P[:, 0] > 40.0, out, 50.0)


def pad_cfun(g):
    """Negative inside grip g's pad outline within PAD_CUT_DEPTH of its plane (co-pilot sense points)."""
    sg = 1.0 if g == "out" else -1.0
    Fp = G.field("pad_" + g, G.pad_outline(g))

    def f(P):
        P = np.atleast_2d(np.asarray(P, float))
        U = sg * P[:, 0]
        out = np.full(len(P), 50.0)
        m = U > 40.0
        if m.any():
            z, uf, hf = G._to_plane(U[m], P[m, 1], P[m, 2], g)
            out[m] = np.maximum(Fp(uf, hf), -(z + PAD_CUT_DEPTH))
        return out
    return f


def _face_height(P2, c, eu, ev, n, z0=None, iters=6):
    """Height z along n of the smooth moulding over the face-frame points P2 (m, 2) (Newton on moulding_smooth)."""
    z = np.zeros(len(P2)) if z0 is None else np.asarray(z0, float).copy()
    e = 0.003
    for _ in range(iters):
        P = c + P2[:, :1] * eu + P2[:, 1:2] * ev + z[:, None] * n
        f = YM.evaluate("msmooth", P)
        fp = YM.evaluate("msmooth", np.vstack([P + e * n, P - e * n])).reshape(2, -1)
        d = (fp[0] - fp[1]) / (2 * e)
        z = z - f / np.where(np.abs(d) < 0.2, 0.2 * np.sign(d + 1e-30), d)
    return z


def trim_terrain():
    """The trim face's Terrain (face frame, mm): base = the smooth moulding's height over the face plane (0 inside the
    flat face, the R head_out[6] edge round / lower chamfer beyond), the legend ring's V-groove (circle trim[2] / 2,
    w x g = trim_grooves, cut from the face plane (ref 0) -- it fades out where the chamfer drops the face more than g
    below the plane, as in the solid) and, rev N, the recessed rocker SLOT between the chords (yoke_geom.trim_slot_dims:
    drafted walls, a flat floor trim_slot[0] deep; rev M's chord V-grooves are its top edges)."""
    from scipy.interpolate import RegularGridInterpolator
    from model import yoke_cover as YC
    D = G.T()
    w, g = (float(x) for x in D["trim_grooves"][:2])
    R0 = 0.5 * float(D["trim"][2])
    th = np.linspace(0.0, 2 * math.pi, 721)[:-1]
    GR = [YC.Groove("ring", np.c_[R0 * np.cos(th), R0 * np.sin(th)], w, g, closed=True)]
    c, eu, ev, n = trim_frame()
    rr = np.arange(12.0, TRIM_CUT_R + 0.2501, 0.05)
    ph = np.linspace(-math.pi, math.pi, 361)
    RR, PH = np.meshgrid(rr, ph, indexing="ij")
    P2 = np.c_[(RR * np.cos(PH)).ravel(), (RR * np.sin(PH)).ravel()]
    Z = _face_height(P2, c, eu, ev, n).reshape(RR.shape)
    Z[rr < 12.5 + 1e-9] = np.minimum(Z[rr < 12.5 + 1e-9], 0.0)
    itp = RegularGridInterpolator((rr, ph), Z, bounds_error=False, fill_value=None)

    def base(X):
        X = np.atleast_2d(X)
        r = np.hypot(X[:, 0], X[:, 1])
        out = np.zeros(len(X))
        m = r > 12.0
        if m.any():
            out[m] = itp(np.c_[r[m], np.arctan2(X[m, 1], X[m, 0])])
        return out

    def base_normal(X):
        X = np.atleast_2d(X)
        z = _face_height(X, c, eu, ev, n, base(X), iters=3)
        P = c + X[:, :1] * eu + X[:, 1:2] * ev + z[:, None] * n
        g3 = _unit(YM._grad_raw("msmooth", P, 0.003))
        return np.c_[g3 @ eu, g3 @ ev, g3 @ n]
    return Terrain(GR, base, base_normal, slot=G.trim_slot_dims())


def trim_patch(V, N, loop, verbose=False):
    """The trim face inside the cut loop (frame mesh V / N vertex ids) as [(V, F, N, material)]: inside the legend
    ring's groove bottom the lunes 'gloss_black' (the bezel ring, rev N) and the recessed slot 'black', 'grip_black'
    outside; heights exact (Newton on the
    smooth field / the grooves' planes), normals split along the creases only.  The loop is no crease: its vertices
    keep the frame mesh's normals."""
    c, eu, ev, n = trim_frame()
    Tr = trim_terrain()
    Q = V[loop] - c
    B = np.c_[Q @ eu, Q @ ev]
    X, T, lab, crease_v = Tr.triangulate(B, fill=TRIM_FILL, chain_tol=0.02, chain_lo=1.6, interp=TRIM_INTERP)
    kB = len(B)
    # heights: the exact smooth surface, the grooves' planes below it
    Xi = X[kB:]
    labi, best = Tr.pieces_at(Xi)
    zb = _face_height(Xi, c, eu, ev, n, Tr.base(Xi), iters=4)
    zg = np.full(len(Xi), np.inf)
    for gr in Tr.GR:
        dc = gr.query(Xi)[0]
        zg = np.minimum(zg, -gr.g * (1.0 - 2.0 * dc / gr.w))
    Zi = np.minimum(np.minimum(zb, zg), Tr.slot_at(Xi)[1])
    Pi = c + Xi[:, :1] * eu + Xi[:, 1:2] * ev + Zi[:, None] * n
    # one vertex per (point, piece) on the creases
    keymap, newP, newL, newX = {}, [], [], []
    Fo = np.zeros_like(T)
    for t_i, tri in enumerate(T):
        for c_i, v in enumerate(tri):
            if v < kB:
                key = (int(v), -1)
            else:
                key = (int(v), int(lab[t_i]) if crease_v[v] else int(labi[v - kB]))
            if key not in keymap:
                keymap[key] = len(newP)
                newP.append(V[loop[v]] if v < kB else Pi[v - kB])
                newL.append(key[1])
                newX.append(X[v])
            Fo[t_i, c_i] = keymap[key]
    P3, L3, X3 = np.array(newP), np.array(newL), np.array(newX)
    N3 = np.zeros_like(P3)
    for (v, L), i in keymap.items():
        if L == -1:
            N3[i] = N[loop[v]]
    for L in np.unique(L3[L3 >= 0]):
        mm = L3 == L
        nl = Tr.normal(L, X3[mm])
        N3[mm] = nl[:, :1] * eu + nl[:, 1:2] * ev + nl[:, 2:3] * n
    # winding by the normals
    fn = np.cross(P3[Fo[:, 1]] - P3[Fo[:, 0]], P3[Fo[:, 2]] - P3[Fo[:, 0]])
    flip = np.sum(fn * N3[Fo].sum(1), 1) < 0
    Fo[flip] = Fo[flip][:, ::-1]
    R0 = 0.5 * float(G.T()["trim"][2])
    cen = X[T].mean(1)
    mat = np.where(np.hypot(cen[:, 0], cen[:, 1]) < R0, "gloss_black", "grip_black").astype(object)
    mat[lab >= SLOT_FLOOR] = "black"                                    # the recessed slot: satin black
    out = []
    for mt in np.unique(mat):
        Fm = Fo[mat == mt]
        u, iv = np.unique(Fm.ravel(), return_inverse=True)
        out.append((P3[u], iv.reshape(-1, 3), N3[u], str(mt)))
    if verbose:
        print(f"  trim face: {len(T)} triangles, {int(crease_v.sum())} crease points", flush=True)
    return out


# ============================================================================================ the moulding, end to end
PAD_CUT_DEPTH = 8.0      # mm: the pad cut reaches this far below the grip's plane (the pocket is 3.0 deep)
TRIM_CUT_R = 15.3        # mm: the trim-face patch's radius (head_out R 16.3 - edge round 1.5 = the flat face's 14.8)
TRIM_CUT_DEPTH = 2.5
TRIM_FILL = (2.5, 5.0)
TRIM_INTERP = (1.0, 0.45, 4)   # rev O (3-D judges r2 CR2-02: the gloss-black lunes p95 4.2 deg, 5 % of their pixels > 4 deg
#                               off the solid's normals -- the face's fall-off into its edge round / the chamfer at the
#                               bottom held by 2.5 / 5 mm fill): the highlight refinement as the gloss cover's (1 deg,
#                               points >= 0.45 mm apart, 4 rounds; yoke_cover INTERP_*)
# the frame's decimation: QEM distance 0.15 mm, edges <= 14 mm (exact normals: the flat faces need no more); the cut loops
# slide within 0.02 mm of their exact curve, their segments <= 2.4 mm (the pockets' 0.25 mm bead rows stay >= 5.9 deg)
PATCH_DEC = dict(dist=0.15, lmax=14.0, bnd_tol=0.02, bnd_turn=15.0, bnd_lmax=2.4)
CUT_VERSION = "cut1"


# the frame's HIGHLIGHT decimation (yoke_mesh.decimate_interp, 2026-10-10): every dense DC vertex a sample its coarse face
# must reproduce -- corner normals interpolated within FRAME_TOL of its exact normal, the face within its sdist --; the
# faces no crew or cabin camera sees are held to less: the forward faces (toward the panel) FWD_TOL_K x the tolerance and
# FRAME_SDIST[1], the body's aft face under the cover HIDDEN_TOL and FRAME_SDIST[2] (their QEM bounds likewise)
FRAME_TOL = 2.5          # deg (satin black, roughness 0.42; 1.5: 26.4k frame faces, visible area > 2 deg 0.8 %;
#                          2.0: 24.2k, 3.1 %; 2.5 with the curvature factor: 20.5k, 8.3 %, p95 2.2; rev M shipped 3.5
#                          -- 3-D judges r1 FID1-07: blotches on the frame band beside the pads and the heads)
FWD_TOL_K = 4.0
HIDDEN_TOL = 20.0        # deg
FRAME_SDIST = (0.15, 0.40, 0.50)   # mm: visible, forward, hidden
HIDDEN_CONE_TURN = (30.0, 40.0)    # deg: the hidden region's cone / turn bounds (cad.res bows no edge turning > 32 deg)
DECI_VERSION = "deci2"


CURV_R0, CURV_KMAX = 4.0, 6.0   # the tolerance grows as R0 / radius on rounds tighter than R0 mm, at most KMAX x
CURV_KMAX_VIS, CURV_KMAX_HEADS = 2.0, 1.0   # ... at most VIS x on the faces seen from the aft hemisphere and none on
#                                 the heads and their necks (|u| > HEADS_BOX[0], h > HEADS_BOX[1]) -- rev O, 3-D judges r2
#                                 CR2-01: the R 0.8-4 rounds of the heads' necks, where L6Y item 4's crisp edge highlights
#                                 run, reached 6 x FRAME_TOL = 15 deg and drew chevron kinks in the close-up zebra
#                                 (decimated on the cached rev N stages: rev N 23.66k faces, the visible rounds > 4 deg on
#                                 2.3 % of their area; 2 / 1: 24.31k, heads' faces p95 per face 3.9 -> ~2.8 deg; 1 / 1:
#                                 25.40k)
HEADS_BOX = (85.0, 50.0)


def curvature_tol_k(V, F, N):
    """Per vertex of a dense mesh with exact normals: max(1, min(CURV_KMAX, CURV_R0 x its curvature)) -- the curvature
    the largest turn of its normal per mm along its edges.  A round of a few millimetres is a few pixels across at the
    viewer's closest look (~2.7 px/mm): its profile is held by the turn / bow rows, the interpolation within it is not
    seen (at the full tolerance the R 0.8 - 3 rounds and the AFCS boss's 1.5 mm blend kept 10k sub-2 mm faces)."""
    E, _, _ = YM._edges(F)
    ang = np.arccos(np.clip(np.sum(N[E[:, 0]] * N[E[:, 1]], 1), -1.0, 1.0))
    rate = ang / np.maximum(np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1), 1e-3)
    kap = np.zeros(len(V))
    np.maximum.at(kap, E[:, 0], rate)
    np.maximum.at(kap, E[:, 1], rate)
    return np.clip(CURV_R0 * kap, 1.0, CURV_KMAX)


# VISIBILITY (rev N, 3-D judges r1 CR1-03: rev M's proxy -- inside the cover's front-view outline and forward of its
# front face = 'under the cover' -- held the body's top behind the cover's upper edge, which the crew eye looks down
# onto at ~45 deg, to the hidden faces' 20 deg): every dense DC vertex classed by z-buffer visibility of the moulding
# + cover from VIS_AFT cameras over the aft hemisphere (the crew / cabin / viewer side; rolling the yoke turns a view
# about a, within it) and VIS_FWD ones over the rest of the sphere -- 0 seen from the aft hemisphere (FRAME_TOL), 1 only
# from forward (FWD_TOL_K), 2 never (HIDDEN_TOL)
VIS_DIST, VIS_FOV, VIS_PX = 600.0, 34.0, 900           # mm from the yoke centre (0, 15, -20), deg, pixels (0.41 mm)
VIS_AFT = [(az, el) for el in (-50.0, -25.0, 0.0, 25.0, 50.0, 75.0) for az in np.arange(-75.0, 75.1, 15.0)] + [(0.0, 88.0)]
VIS_FWD = [(az, el) for el in (-50.0, -10.0, 30.0, 70.0) for az in np.arange(105.0, 255.1, 30.0)] + [(0.0, -88.0)]
VIS_VERSION = "vis1"


def _vis_dir(az, el):
    a, e = math.radians(az), math.radians(el)
    return np.array([math.sin(a) * math.cos(e), math.sin(e), math.cos(a) * math.cos(e)])


def visibility_classes(Vd, Nd, occluders, verbose=False):
    """Per point Vd (normals Nd, yoke-local mm): 0 visible from a VIS_AFT camera, 1 only from a VIS_FWD one, 2 never --
    z-buffered against the occluder meshes [(V, F)] (the dense moulding + the cover): front-facing and within
    0.15 mm + 1.5 px x tan(view angle) of the nearest surface at its pixel (or its 3 x 3 neighbourhood's farthest)."""
    import sys
    import time
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "test"))
    import yoke_raster as YR
    t0 = time.time()
    OV = np.vstack([v for v, _ in occluders])
    OF = np.vstack([f + o for (v, f), o in zip(occluders, np.cumsum([0] + [len(v) for v, _ in occluders])[:-1])])
    ctr = np.array([0.0, 15.0, -20.0])
    seen_aft = np.zeros(len(Vd), bool)
    seen_any = np.zeros(len(Vd), bool)
    W = VIS_PX
    pxk = 2.0 * math.tan(math.radians(0.5 * VIS_FOV)) / W
    for kind, cams in (("aft", VIS_AFT), ("fwd", VIS_FWD)):
        for az, el in cams:
            d = _vis_dir(az, el)
            up = (0.0, 1.0, 0.0) if abs(d[1]) < 0.95 else (0.0, 0.0, 1.0)
            cam = YR.look_at(ctr + VIS_DIST * d, ctr, up=up, fov=VIS_FOV, W=W, H=W)
            px, z = cam(OV)
            _, _, zb = YR.raster(px[OF], z[OF], W, W)
            zf_ = np.where(np.isfinite(zb), zb, -np.inf)                  # the neighbourhood's farthest surface
            zp = np.pad(zf_, 1, constant_values=-np.inf)
            zmax = np.max(np.stack([zp[1 + dy:W + 1 + dy, 1 + dx:W + 1 + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1)]),
                          0)
            pv, zv = cam(Vd)
            ix, iy = np.floor(pv[:, 0]).astype(int), np.floor(pv[:, 1]).astype(int)
            ok = (ix >= 0) & (iy >= 0) & (ix < W) & (iy < W)
            view = cam.eye - Vd
            view /= np.linalg.norm(view, axis=1, keepdims=True)
            cs = np.sum(Nd * view, 1)
            ok &= cs > 0.02
            tn = np.sqrt(np.maximum(1.0 - cs * cs, 0.0)) / np.maximum(cs, 1e-3)
            tol = 0.15 + 1.5 * zv * pxk * np.minimum(tn, 8.0)
            vis = np.zeros(len(Vd), bool)
            i = np.nonzero(ok)[0]
            zr = np.maximum(np.where(np.isfinite(zb[iy[i], ix[i]]), zb[iy[i], ix[i]], -np.inf), zmax[iy[i], ix[i]])
            vis[i] = zv[i] <= zr + tol[i]
            seen_any |= vis
            if kind == "aft":
                seen_aft |= vis
    cls = np.where(seen_aft, 0, np.where(seen_any, 1, 2)).astype(np.int8)
    if verbose:
        print(f"  visibility: {len(VIS_AFT)} aft + {len(VIS_FWD)} forward cameras, {np.bincount(cls, minlength=3)} "
              f"(aft / forward only / never), {time.time() - t0:.0f}s", flush=True)
    return cls


def _cut_key():
    return YM.dc_key() + (CUT_VERSION, PAD_CUT_DEPTH, TRIM_CUT_R, TRIM_CUT_DEPTH)


def _cut_stage(verbose=False):
    """The dense moulding with the pads and the trim face cut out (stage 'cut'): (V, F, N)."""
    V, F, N = YM.dense_moulding(verbose=verbose)
    cfs = {"pad_out": pad_cfun("out"), "pad_in": pad_cfun("in"), "trim": trim_cfun}

    def cutstage():
        V1, F1, N1 = V, F, N
        for nm, cf in cfs.items():
            V1, F1, N1, lp = cut(V1, F1, N1, "msmooth", cf)
            if verbose:
                print(f"  cut {nm}: {len(F1)} faces, loops {[len(x) for x in lp]}", flush=True)
        return V1, F1, N1
    return YM.stage_cached("cut", _cut_key(), cutstage)


def _vis_key():
    import hashlib
    from pathlib import Path
    h = hashlib.sha1()
    for f in ("yoke_cover.py", "yoke_tri.py"):                      # the cover occluder's mesher
        h.update((Path(__file__).resolve().parent / f).read_bytes())
    return _cut_key() + (h.hexdigest()[:12], VIS_VERSION, VIS_DIST, VIS_FOV, VIS_PX, tuple(VIS_AFT), tuple(VIS_FWD))


def visibility(cover=None, verbose=False):
    """(V, cls): the cut-stage dense moulding's vertices and their visibility classes (visibility_classes; stage
    'vis'); cover: the cover's meshes [(V, F, ...)] as occluder (default yoke_cover.cover_meshes())."""
    V, F, N = _cut_stage(verbose=verbose)

    def comp():
        from model import yoke_cover as YC
        cv = cover if cover is not None else YC.cover_meshes()
        return visibility_classes(V, N, [(V, F)] + [(c[0], c[1]) for c in cv], verbose=verbose)
    return V, YM.stage_cached("vis", _vis_key(), comp)


_VIS_TREE = {}


def vis_tol_k(C, fn=None):
    """The frame's highlight-tolerance factor per point (yoke-local mm), by the visibility class of the nearest dense
    vertex (visibility(): needs its stage cached): 1 seen from the aft hemisphere, FWD_TOL_K only from forward, inf
    never."""
    from scipy.spatial import cKDTree
    key = _vis_key()
    if key not in _VIS_TREE:
        V, cls = visibility()
        _VIS_TREE.clear()
        _VIS_TREE[key] = (cKDTree(V), cls)
    tree, cls = _VIS_TREE[key]
    _, i = tree.query(np.asarray(C, float))
    return np.array([1.0, FWD_TOL_K, np.inf])[cls[i]]


def frame_tol_k(C, fn):
    """REV M's positional proxy (kept for comparison; rev N decimates by vis_tol_k): the frame's highlight-tolerance
    factor per point / face (positions C, normals fn; yoke-local mm): inf under the cover (inside its shell outline by
    1.5 mm, behind its front face), FWD_TOL_K on the forward faces (normal a < -0.6), 1 elsewhere."""
    from model import yoke_cover as YC
    C = np.asarray(C, float)
    k = np.ones(len(C))
    k[np.asarray(fn)[:, 2] < -0.6] = FWD_TOL_K
    inside = YC.d2(C[:, 0], C[:, 1]) < -1.5
    if inside.any():
        hid = np.zeros(len(C), bool)
        hid[inside] = C[inside, 2] < YC.fwd_a(C[inside, 0], C[inside, 1]) + 0.5
        k[hid] = np.inf
    return k


def moulding_parts(verbose=False, cover=None):
    """The black moulding as pieces [(V, F, N, material)] (co-pilot sense, yoke-local mm): the smooth moulding's
    dense DC mesh with the pads and the trim face cut out along their tabled edges (cut: exact boundary vertices),
    decimated under the highlight criterion (yoke_mesh.decimate_interp: FRAME_TOL / FRAME_SDIST, the cut loops sliding
    within PATCH_DEC), projected exactly, split where cad.res's turn / bow criterion fails, slivers cleaned; then the
    pad pockets and the trim face stitched into the loops (shared positions)."""
    import time
    t0 = time.time()
    cfs = {"pad_out": pad_cfun("out"), "pad_in": pad_cfun("in"), "trim": trim_cfun}
    V, F, N = _cut_stage(verbose=verbose)
    _, vcls = visibility(cover=cover, verbose=verbose)
    key = _vis_key()

    def dec():
        vis = np.array([1.0, FWD_TOL_K, np.inf])[vcls]
        ck = curvature_tol_k(V, F, N)
        heads = (np.abs(V[:, 0]) > HEADS_BOX[0]) & (V[:, 1] > HEADS_BOX[1])
        ck = np.where(vcls == 0, np.minimum(ck, np.where(heads, CURV_KMAX_HEADS, CURV_KMAX_VIS)), ck)     # rev O
        ts = FRAME_TOL * np.minimum(vis * ck, HIDDEN_TOL / FRAME_TOL)
        sd = np.where(np.isfinite(vis), np.where(vis > 1.0, FRAME_SDIST[1], FRAME_SDIST[0]), FRAME_SDIST[2])
        hid = ~np.isfinite(vis)
        prm = dict(PATCH_DEC, sdist=sd, dist=np.maximum(sd, 0.15), cone=np.where(hid, HIDDEN_CONE_TURN[0], YM.DEC["cone"]),
                   turn=np.where(hid, HIDDEN_CONE_TURN[1], YM.DEC["turn"]))
        V2, F2, N2, _ = YM.decimate_interp(V, F, N, ts, params=prm, verbose=verbose)
        E, EF, _ = YM._edges(F2)
        bnd = np.zeros(len(V2), bool)
        bnd[E[EF[:, 1] < 0].ravel()] = True
        P, Nn, res = YM.project_exact("msmooth", V2[~bnd])
        V2, N2 = V2.copy(), N2.copy()
        V2[~bnd], N2[~bnd] = P, Nn
        return V2, F2, N2
    V, F, N = YM.stage_cached("deci", key + (tuple(sorted(dict(YM.DEC, **PATCH_DEC).items())), FRAME_TOL, FWD_TOL_K,
                                             HIDDEN_TOL, FRAME_SDIST, HIDDEN_CONE_TURN, CURV_R0, CURV_KMAX, CURV_KMAX_VIS,
                                             CURV_KMAX_HEADS, HEADS_BOX, DECI_VERSION), dec)
    fn_, _ = YM._face_normals(V, F)
    hid_f = ~np.isfinite(vis_tol_k(V[F].mean(1), fn_))
    hid_v = np.ones(len(V), bool)
    for j in range(3):
        hid_v[F[~hid_f, j]] = False                    # a vertex is hidden when all its faces are
    V, F, N = YM.refine_split("msmooth", V, F, N, p=PATCH_DEC, verbose=verbose,
                              protect=lambda E: hid_v[np.minimum(E[:, 0], len(hid_v) - 1)] &
                              hid_v[np.minimum(E[:, 1], len(hid_v) - 1)] & (E.max(1) < len(hid_v)))
    V, F, N = YM.sliver_cleanup("msmooth", V, F, N, verbose=verbose)
    N = YM._fix_normals(V, F, N)
    if verbose:
        hr = YM.highlight_report("msmooth", V, F, N, tol_k=vis_tol_k)
        print(f"  moulding frame: {len(F)} triangles, {time.time() - t0:.0f}s; highlights (visible faces, interpolated "
              f"vs exact normal): p50 {hr['p50']:.2f} p95 {hr['p95']:.2f} deg, area > 2 deg {hr['over2']:.1f} %, "
              f"> 4 deg {hr['over4']:.1f} %", flush=True)
    loops = boundary_loops(F)
    out = [(V, F, N, "frame")]
    for lp in loops:
        P = V[lp]
        which = min(cfs, key=lambda k: float(np.abs(cfs[k](P)).max()))
        err = float(np.abs(cfs[which](P)).max())
        if err > 1e-3:
            raise RuntimeError(f"moulding cut loop off every cut ({which}: {err:.2e})")
        if which == "trim":
            out += collapse_needles(trim_patch(V, N, lp, verbose=verbose), verbose=verbose, tag=" (trim face)")
        else:
            out += collapse_needles(pad_pocket(V, N, lp, which[4:]), verbose=verbose, tag=f" ({which})")
    YM.close_pool()
    if verbose:
        print(f"  moulding: {sum(len(x[1]) for x in out)} triangles ({len(loops)} loops), {time.time() - t0:.0f}s",
              flush=True)
    return out


# ============================================================================================ needle triangles
def collapse_needles(pieces, min_angle=5.0, ratio=0.35, rounds=6, verbose=False, tag=""):
    """Remove the needle triangles (min angle < min_angle, shortest edge < ratio x the middle one) of a group of
    explicit pieces [(V, F, N, material)] -- where a strip's rows converge (a round meeting a crease, an offset row at a
    tight corner) or crease chains meet: the short edge collapses onto one end in POSITION space (every split-normal
    copy of that point moves, so creases and material seams stay welded); the group's open boundary (its seam with the
    moulding / the frame loop) never moves; a collapse that would flip a face, open or pinch the welded surface is
    skipped.  Positions stay those of the kept end (no new geometry).  Returns the pieces."""
    Vs = [np.asarray(p[0], float).copy() for p in pieces]
    Fs = [np.asarray(p[1], np.int64).copy() for p in pieces]
    off = np.cumsum([0] + [len(v) for v in Vs])
    V = np.vstack(Vs)
    key = np.round(V * 1e6).astype(np.int64)
    _, pid = np.unique(key, axis=0, return_inverse=True)
    pid = pid.ravel()
    Fall = np.vstack([f + o for f, o in zip(Fs, off)])
    owner = np.repeat(np.arange(len(pieces)), [len(f) for f in Fs])
    P = np.zeros((pid.max() + 1, 3))
    P[pid] = V
    done = 0
    for _ in range(rounds):
        Fp = pid[Fall]
        live = (Fp[:, 0] != Fp[:, 1]) & (Fp[:, 1] != Fp[:, 2]) & (Fp[:, 0] != Fp[:, 2])
        Fall, owner, Fp = Fall[live], owner[live], Fp[live]
        op, nm = YM.manifold_report(Fp)
        e = np.sort(np.vstack([Fp[:, [0, 1]], Fp[:, [1, 2]], Fp[:, [2, 0]]]), 1)
        ue, cnt = np.unique(e, axis=0, return_counts=True)
        fixed = np.zeros(len(P), bool)
        fixed[ue[cnt == 1].ravel()] = True
        A = np.degrees(YM._min_angle(P[Fp[:, 0]], P[Fp[:, 1]], P[Fp[:, 2]]))
        L = np.stack([np.linalg.norm(P[Fp[:, (j + 1) % 3]] - P[Fp[:, j]], axis=1) for j in range(3)], 1)
        Ls = np.sort(L, 1)
        cand = np.nonzero((A < min_angle) & (Ls[:, 0] < ratio * Ls[:, 1]))[0]
        if not len(cand):
            break
        used = np.zeros(len(P), bool)
        moved = 0
        fn0 = np.cross(P[Fp[:, 1]] - P[Fp[:, 0]], P[Fp[:, 2]] - P[Fp[:, 0]])
        for f in cand[np.argsort(A[cand])]:
            j = int(np.argmin(L[f]))
            a, b = Fp[f, j], Fp[f, (j + 1) % 3]
            if fixed[a] and fixed[b]:
                continue
            keep, go = (a, b) if (fixed[a] or not fixed[b]) else (b, a)
            if used[keep] or used[go]:
                continue
            # faces round `go`: after the move, none may flip / degenerate (other than the ones that vanish)
            ring = np.nonzero((Fp == go).any(1))[0]
            Fn = np.where(Fp[ring] == go, keep, Fp[ring])
            alive = (Fn[:, 0] != Fn[:, 1]) & (Fn[:, 1] != Fn[:, 2]) & (Fn[:, 0] != Fn[:, 2])
            Pn = P[Fn[alive]]
            nn = np.cross(Pn[:, 1] - Pn[:, 0], Pn[:, 2] - Pn[:, 0])
            o = fn0[ring[alive]]
            cosv = np.sum(nn * o, 1) / np.maximum(np.linalg.norm(nn, axis=1) * np.linalg.norm(o, axis=1), 1e-30)
            if alive.any() and cosv.min() < 0.3:
                continue
            # link condition: common neighbours of keep / go == the faces that vanish (2 interior, 1 on a boundary)
            nb = lambda v: set(Fp[(Fp == v).any(1)].ravel()) - {v}            # noqa: E731
            if len(nb(keep) & nb(go)) != int((~alive).sum()):
                continue
            Fp[ring] = Fn
            pid[pid == go] = keep
            used[keep] = used[go] = True
            used[list(nb(keep))] = True
            moved += 1
        if not moved:
            break
        done += moved
        Fp2 = pid[Fall]
        live2 = (Fp2[:, 0] != Fp2[:, 1]) & (Fp2[:, 1] != Fp2[:, 2]) & (Fp2[:, 0] != Fp2[:, 2])
        op2, nm2 = YM.manifold_report(Fp2[live2])
        if nm2 > nm or op2 > op:
            raise RuntimeError(f"collapse_needles{tag}: the welded surface opened ({op} -> {op2}, {nm} -> {nm2})")
    # back to the pieces: every vertex at its point's (possibly moved) position; degenerate faces dropped
    V = P[pid]
    Nall = np.vstack([np.asarray(p[2], float) for p in pieces])
    out = []
    for i, (_, _, N, mat) in enumerate(pieces):
        Fi = Fall[owner == i]
        Fp = pid[Fi]
        Fi = Fi[(Fp[:, 0] != Fp[:, 1]) & (Fp[:, 1] != Fp[:, 2]) & (Fp[:, 0] != Fp[:, 2])]
        Fi = _flip_caps(V, Fi, Nall, min_angle)
        u, inv = np.unique(Fi.ravel(), return_inverse=True)
        out.append((V[u], inv.reshape(-1, 3), Nall[u], mat))
    if verbose:
        a = [YM._min_angles_deg(p[0], p[1]) for p in out if len(p[1])]
        a = np.concatenate(a) if a else np.zeros(0)
        print(f"  needles{tag}: {done} collapsed, {int((a < min_angle).sum())} slivers left", flush=True)
    return [p for p in out if len(p[1])]


def _flip_caps(V, F, N, min_angle=5.0, rounds=3):
    """Flip the longest edge of each cap triangle (an angle near 180 deg, < min_angle at another corner) where it is
    shared by vertex ids with a neighbour of the same piece (a smooth edge, not a crease / seam): taken when the two new
    faces' smaller angle grows and their normals stay with the old faces' and the corner normals."""
    F = F.copy()
    for _ in range(rounds):
        if not len(F):
            break
        A = np.degrees(YM._min_angle(V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]))
        caps = np.nonzero(A < min_angle)[0]
        if not len(caps):
            break
        E, EF, _ = YM._edges(F)
        emap = {(int(a), int(b)): k for k, (a, b) in enumerate(E)}
        used = np.zeros(len(F), bool)
        n = 0
        for f in caps:
            if used[f]:
                continue
            t = F[f]
            L = [np.linalg.norm(V[t[(j + 1) % 3]] - V[t[j]]) for j in range(3)]
            j = int(np.argmax(L))
            a, b, c = t[j], t[(j + 1) % 3], t[(j + 2) % 3]
            k = emap.get((min(a, b), max(a, b)))
            if k is None or EF[k, 1] < 0:
                continue
            g = EF[k, 0] if EF[k, 0] != f else EF[k, 1]
            if used[g]:
                continue
            d = [v for v in F[g] if v != a and v != b]
            if len(d) != 1:
                continue
            d = d[0]
            t1, t2 = np.array([a, d, c]), np.array([d, b, c])
            old = min(A[f], A[g])
            new = min(np.degrees(YM._min_angle(*[V[t1[i]][None] for i in range(3)]))[0],
                      np.degrees(YM._min_angle(*[V[t2[i]][None] for i in range(3)]))[0])
            if new <= old:
                continue
            on = np.cross(V[F[g, 1]] - V[F[g, 0]], V[F[g, 2]] - V[F[g, 0]])
            on /= max(np.linalg.norm(on), 1e-30)
            ok = True
            for tt in (t1, t2):
                nn = np.cross(V[tt[1]] - V[tt[0]], V[tt[2]] - V[tt[0]])
                ln = np.linalg.norm(nn)
                if ln < 1e-12 or float(nn @ on) / ln < 0.5 or (N[tt] @ (nn / ln)).min() < 0.5:
                    ok = False
            if not ok:
                continue
            F[f], F[g] = t1, t2
            used[f] = used[g] = True
            n += 1
        if not n:
            break
    return F
