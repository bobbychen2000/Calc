"""
The white COVER of the yoke as an explicit, crease-exact surface mesh (rev M, yoke_geom.cover; yoke-local mm):

  STRIP     the edge all round the shell outline, built as columns at outline samples (resampled by turn / length,
            a column on each insert junction): the aft edge round (rmax of the outline distance and the aft surface,
            radius edges[0..2] varying along the outline) incl. the top land, the side wall, the front edge round R 0.5;
            under the foot, where the R 3 aft round and the front round meet without a wall, their crease.  Rows at
            equal turn of the section's normal, so every row turns the same angle; normals = the gradients of the
            solid's own sub-fields (one-sided at the foot crease).
  TERRAIN   the aft face inside the strip as a height field a = H(u, h): the face (cover_top: face_a, the crown
            bevel's R 20 blend) less the deepest of the V-grooves (parting grooves of both inserts, the step V, the badge
            outline / border / speed lines; yoke_geom.cover's v-fields): every CREASE of that field -- groove edges,
            V bottoms, the concave corners' valleys, the junctions where two grooves meet -- found as the interfaces
            of its pieces on a 0.04 mm label grid, each crease point bisected onto its interface, the crease polylines
            simplified (3 microns) and forced into a constrained Delaunay triangulation; heights exact, normals = the
            gradient of the piece each triangle lies in (split only along those creases).
            The two side grooves run out at the arm junctions' edge round (their width and depth tapered to zero over
            the last 1.5 mm before the strip: the solid cuts them on through the R 1 edge).
  FRONT     the hidden front face (against the body), coarse.
Materials by front-view position (yoke_geom.cover_part): white cover, the upper insert (crown, badge) yoke_silver, the
lower insert yoke_silver_dark; the TCS pocket's floor seen through the bezel's clearance ring black; the grooves' flanks
yoke_groove where they turn away from GROOVE_LIGHT (rev R: groove_faces, directional -- one flank of a groove dark, the
other lit; rev Q had every flank but the step's up-facing one dark).
"""
from __future__ import annotations

import math

import numpy as np

from model import yoke_geom as G
from model import yoke_tri as YT

HC = 0.04                # mm: the crease label grid
TAPER = (1.05, 1.5)      # the side grooves' run-out: depth and width x smoothstep(-d2 - TAPER[0], 0, TAPER[1])
FILL = 2.6               # mm: terrain fill-point spacing away from the creases
FILL_LEVELS = (2.4, 4.0)   # mm: the terrain's graded hexagonal fill spacings by distance from the features, 4 at most
#                          (6 / 9 mm away from them drew the gloss cover's reflections as zig-zags: normals interpolated
#                          linearly over a 9 mm triangle of the lower face); the highlight refinement below adds points
#                          where the interpolation still misses (1.8 / 3.0 without it: 0.9k triangles more, 1.8 % of the
#                          area > 1 deg; 2.4 / 4.0 with it: 0.1 %)
COL_LEN, COL_TURN = 2.6, 10.0  # strip columns: at most this far apart (mm) / this much outline turn (deg; the quads'
#                                 diagonals across the ~18 deg rows that turn past cad.res's 20 deg are split at build);
#                                 rev O (3-D judges r2 CR2-07, the yoke's budget): 2.4 -> 2.6 mm (cover 7,018 -> 6,802
#                                 faces, 7 slivers; at 3.2 the perimeter round's 0.26 mm rows over 3.3 mm columns made 64)
FRONT_FILL = 9.0         # mm: the hidden front face's hexagonal fill spacing (against the body; was a 4 mm square grid)
FRONT_RING = (4.0, 6.5)  # mm: its ring of points this far inside the outline, this far apart
N_AFT, N_FRONT = 5, 1    # strip rows: aft round + land (turn-equalised, ~20 deg a row: cad.res's criterion), front
#                          round (hidden against the body: one row, exact normals at both ends)


def _unit(v):
    v = np.asarray(v, float)
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-15)


# ============================================================================================ fields of the cover
def d2(U, H):
    return G.field("shell", G.shell_outline())(np.asarray(U, float), np.asarray(H, float))


def r_edge(U, H):
    """The aft edge round's radius at (u, h) as yoke_geom.cover: R 1 perimeter, R 2 arms' lower edges, R 3 foot."""
    U, H = np.asarray(U, float), np.asarray(H, float)
    E = G.T()["edges"]
    Fs = G.field("shell", G.shell_outline())
    gh = (Fs(U, H + 0.2) - Fs(U, H - 0.2)) / 0.4
    arm_lower = G.smoothstep(np.abs(U), 36.0, 40.0) * G.smoothstep(-gh, 0.25, 0.55)
    return float(E[0]) + (float(E[1]) - float(E[0])) * arm_lower + (float(E[2]) - float(E[0])) * G.smoothstep(-H, 48.0, 53.0)


def top(U, H):
    return G.cover_top(np.asarray(U, float), np.asarray(H, float))


def fwd_a(U, H):
    U, H = np.asarray(U, float), np.asarray(H, float)
    return G.face_a(H) - G.crown_bevel(U, H) - float(G.T()["cover_t"])


def f_aft(U, H, A):
    """The aft part of the shell (outline x aft surface, round r_edge): yoke_geom.cover without grooves / pocket."""
    return G.rmax(d2(U, H), np.asarray(A, float) - top(U, H), r_edge(U, H))


def f_fwd(U, H, A):
    return G.rmax(d2(U, H), fwd_a(U, H) - np.asarray(A, float), 0.5)


def grad3(fn, P, e=0.003):
    P = np.asarray(P, float)
    g = []
    for k in range(3):
        d = np.zeros(3)
        d[k] = e
        g.append(fn(*(P + d).T) - fn(*(P - d).T))
    return _unit(np.stack(g, -1))


def grad2(fn, X, Y, e=0.004):
    return ((fn(X + e, Y) - fn(X - e, Y)) / (2 * e), (fn(X, Y + e) - fn(X, Y - e)) / (2 * e))


# ============================================================================================ grooves as pieces
class Run:
    """One smooth run of a groove's centre curve (an open polyline between sharp corners / ends)."""

    def __init__(self, P):
        from scipy.spatial import cKDTree
        self.P = np.asarray(P, float)
        self.A, self.E = self.P[:-1], np.diff(self.P, axis=0)
        self.L2 = np.maximum(np.einsum("ij,ij->i", self.E, self.E), 1e-18)
        self.tree = cKDTree(self.P)

    def query(self, X):
        """(dc, foot (n, 2), seg dir (n, 2), clamped end: 0 none, 1 start, 2 end) for the points X (n, 2)."""
        n = len(self.P)
        k = min(6, n)
        _, vi = self.tree.query(X, k=k)
        vi = np.atleast_2d(vi).reshape(len(X), k)
        cand = np.unique(np.concatenate([np.minimum(vi, n - 2), np.clip(vi - 1, 0, n - 2)], 1), axis=1) \
            if False else np.concatenate([np.minimum(vi, n - 2), np.clip(vi - 1, 0, n - 2)], 1)
        a, e = self.A[cand], self.E[cand]
        w = X[:, None, :] - a
        t = np.clip(np.einsum("ijk,ijk->ij", w, e) / self.L2[cand], 0.0, 1.0)
        dv = w - t[..., None] * e
        d2_ = np.einsum("ijk,ijk->ij", dv, dv)
        j = np.argmin(d2_, 1)
        r = np.arange(len(X))
        seg, tj = cand[r, j], t[r, j]
        foot = self.A[seg] + tj[:, None] * self.E[seg]
        dirn = _unit(self.E[seg])
        clamp = np.where((seg == 0) & (tj <= 1e-9), 1, np.where((seg == n - 2) & (tj >= 1 - 1e-9), 2, 0))
        return np.sqrt(d2_[r, j]), foot, dirn, clamp


class Groove:
    def __init__(self, name, P, w, g, closed=False, corner_deg=15.0):
        P = np.asarray(P, float)
        if closed and np.linalg.norm(P[0] - P[-1]) < 1e-9:
            P = P[:-1]
        keep = np.r_[True, np.linalg.norm(np.diff(P, axis=0), axis=1) > 1e-9]
        P = P[keep]
        self.name, self.w, self.g, self.closed = name, float(w), float(g), closed
        Q = np.vstack([P[-1:], P, P[:1]]) if closed else P
        d = np.diff(Q, axis=0)
        ang = np.arctan2(d[:, 1], d[:, 0])
        turn = np.abs((np.diff(ang) + np.pi) % (2 * np.pi) - np.pi)
        if closed:
            corners = list(np.nonzero(np.degrees(turn) > corner_deg)[0])          # indices into P
        else:
            corners = [i + 1 for i in np.nonzero(np.degrees(turn) > corner_deg)[0]]
        if closed:
            if not corners:
                corners = [0]
            c0 = corners[0]
            P = np.roll(P, -c0, 0)
            corners = sorted((c - c0) % len(P) for c in corners)
            P = np.vstack([P, P[:1]])
            idx = corners + [len(P) - 1]
        else:
            idx = [0] + corners + [len(P) - 1]
        self.runs = [Run(_densify(P[i:j + 1], 0.1)) for i, j in zip(idx[:-1], idx[1:])]
        self.vertices = np.array([P[i] for i in idx])          # run ends (corners / curve ends)

    def query(self, X):
        """Per point: (dc, run index, foot, dir, vertex id of a clamped (cone) point or -1, side) of the nearest run."""
        best = None
        for j, R in enumerate(self.runs):
            dc, foot, dirn, clamp = R.query(X)
            vid = np.where(clamp == 1, j, np.where(clamp == 2, j + 1, -1))
            if self.closed:
                vid = np.where(vid >= 0, vid % len(self.runs), -1)
            if best is None:
                best = [dc, np.zeros(len(X), int), foot, dirn, vid]
            else:
                b = dc < best[0] - 1e-12
                best[0] = np.where(b, dc, best[0])
                best[1] = np.where(b, j, best[1])
                best[2] = np.where(b[:, None], foot, best[2])
                best[3] = np.where(b[:, None], dirn, best[3])
                best[4] = np.where(b, vid, best[4])
        dc, run, foot, dirn, vid = best
        v = X - foot
        side = np.where(dirn[:, 0] * v[:, 1] - dirn[:, 1] * v[:, 0] >= 0.0, 1, -1)
        return dc, run, foot, dirn, vid, side

    def vertex(self, vid):
        return self.vertices[vid]

    def run_ends(self, j):
        n = len(self.runs)
        return (j, (j + 1) % n if self.closed else j + 1)


def _densify(P, step):
    P = np.asarray(P, float)
    out = [P[:1]]
    for a, b in zip(P[:-1], P[1:]):
        n = max(1, int(math.ceil(np.linalg.norm(b - a) / step)))
        out.append(a + (b - a) * np.linspace(0, 1, n + 1)[1:, None])
    return np.vstack(out)


def grooves():
    """The cover's grooves (yoke_geom.cover): [(Groove)] with their (w, g)."""
    D = G.T()
    gw = D["grooves"]
    bg, bw = (float(x) for x in D["badge_relief"][:2])
    gc = G._groove_curves()
    out = []
    for nm, (w, g) in [("side_r", gw[0]), ("side_l", gw[0]), ("step", gw[1]), ("lower", gw[2])] + \
            [(k, (bw, bg)) for k in gc if k.startswith("badge")]:
        P = gc[nm]
        closed = nm in ("lower", "badge", "badge_border")
        out.append(Groove(nm, P, w, g, closed=closed))
    return out


def taper(U, H):
    return G.smoothstep(-d2(U, H) - TAPER[0], 0.0, TAPER[1])


def pieces_at(X, GR):
    """Labels and depths at the front-view points X (n, 2): (label (n,) int64, depth (n,) of the deepest groove (<= 0:
    the face), per-groove query results, taper).  Label 0 = the face; groove k, run j, side s: 1 + 4096 k + 16 j +
    (s > 0); the cone round a run-end vertex v (the nearest point of the groove is that vertex): 1 + 4096 k + 2048 + v."""
    X = np.asarray(X, float)
    tau = taper(X[:, 0], X[:, 1])
    best = np.zeros(len(X))
    lab = np.zeros(len(X), np.int64)
    Q = []
    for k, gr in enumerate(GR):
        dc, run, foot, dirn, vid, side = gr.query(X)
        depth = gr.g * (tau - 2.0 * dc / gr.w)
        Q.append((dc, run, foot, dirn, vid, side, depth))
        b = depth > best
        best = np.where(b, depth, best)
        lk = np.where(vid >= 0, 1 + 4096 * k + 2048 + vid, 1 + 4096 * k + 16 * run + (side > 0))
        lab = np.where(b, lk, lab)
    return lab, best, Q, tau


def decode(lab):
    """(groove k, 'run' / 'cone', run j or vertex v, side s) of a label (k = -1: the face)."""
    lab = int(lab)
    if lab == 0:
        return -1, "face", -1, 0
    k, r = (lab - 1) // 4096, (lab - 1) % 4096
    if r >= 2048:
        return k, "cone", r - 2048, 0
    return k, "run", r // 16, 1 if r % 16 else -1


def is_crease(la, lb, GR):
    """False only for a run and the cone at one of its own end vertices (the cone is tangent to the run's walls)."""
    ka, ta, ia, _ = decode(la)
    kb, tb, ib, _ = decode(lb)
    if ka < 0 or kb < 0 or ka != kb or ta == tb:
        return True
    j, v = (ia, ib) if ta == "run" else (ib, ia)
    return v not in GR[ka].run_ends(j)


# ============================================================================================ creases (2-D label grid)
def crease_chains(GR, hc=HC, margin=0.7):
    """The crease polylines of the groove field (front view, mm): label changes on a hc grid over the grooves'
    neighbourhood, each crossing bisected onto its interface (label function), one vertex per cell at the mean of its
    crease crossings, the dual edges of the crease crossings chained ([(N, 2) polylines], junction / end points shared
    exactly between chains)."""
    allP = np.vstack([r.P for g in GR for r in g.runs])
    lo = np.floor((allP.min(0) - 2.0) / hc) * hc
    hi = allP.max(0) + 2.0
    nx, ny = int(math.ceil((hi[0] - lo[0]) / hc)) + 1, int(math.ceil((hi[1] - lo[1]) / hc)) + 1
    # active nodes: within margin of some groove's edge (coarse 0.5 mm test, then all nodes of those coarse cells)
    k = int(round(0.5 / hc))
    cs = k * hc
    cx = np.arange(lo[0], hi[0] + cs, cs) + 0.5 * cs
    cy = np.arange(lo[1], hi[1] + cs, cs) + 0.5 * cs
    CX, CY = np.meshgrid(cx, cy, indexing="ij")
    Cc = np.c_[CX.ravel(), CY.ravel()]
    near = np.zeros(len(Cc), bool)
    for g in GR:
        dc = g.query(Cc)[0]
        near |= dc < 0.5 * g.w + margin + 0.71 * cs
    act = np.zeros((nx, ny), bool)
    ii, jj = np.unravel_index(np.nonzero(near)[0], CX.shape)
    for a, b in zip(ii, jj):
        act[a * k:min(nx, (a + 1) * k + 1), b * k:min(ny, (b + 1) * k + 1)] = True
    lab = np.zeros((nx, ny), np.int64)
    I, J = np.nonzero(act)
    X = np.c_[lo[0] + I * hc, lo[1] + J * hc]
    for s in range(0, len(X), 200000):
        lab[I[s:s + 200000], J[s:s + 200000]] = pieces_at(X[s:s + 200000], GR)[0]
    # crossing edges: horizontal (i, j)-(i+1, j), vertical (i, j)-(i, j+1)
    out = []
    for axis in (0, 1):
        if axis == 0:
            a, b = lab[:-1, :], lab[1:, :]
            m = (a != b) & act[:-1, :] & act[1:, :]
        else:
            a, b = lab[:, :-1], lab[:, 1:]
            m = (a != b) & act[:, :-1] & act[:, 1:]
        ei, ej = np.nonzero(m)
        out.append((axis, ei, ej, a[ei, ej], b[ei, ej]))
    # bisect every crossing on the label function
    pts, meta = [], []
    for axis, ei, ej, la, lb in out:
        p0 = np.c_[lo[0] + ei * hc, lo[1] + ej * hc]
        d = np.array([hc, 0.0]) if axis == 0 else np.array([0.0, hc])
        t0, t1 = np.zeros(len(ei)), np.ones(len(ei))
        for _ in range(14):
            tm = 0.5 * (t0 + t1)
            lm = pieces_at(p0 + tm[:, None] * d, GR)[0]
            same = lm == la
            t0 = np.where(same, tm, t0)
            t1 = np.where(same, t1, tm)
        pts.append(p0 + (0.5 * (t0 + t1))[:, None] * d)
        crease = np.array([is_crease(x, y, GR) for x, y in zip(la, lb)], bool)
        # the two cells either side (cell (i, j) = nodes (i..i+1, j..j+1))
        if axis == 0:
            c1, c2 = np.c_[ei, ej - 1], np.c_[ei, ej]
        else:
            c1, c2 = np.c_[ei - 1, ej], np.c_[ei, ej]
        meta.append((c1, c2, crease))
    P = np.vstack(pts)
    C1 = np.vstack([m[0] for m in meta])
    C2 = np.vstack([m[1] for m in meta])
    CR = np.concatenate([m[2] for m in meta])
    P, C1, C2 = P[CR], C1[CR], C2[CR]
    # cell vertices = mean of the crease crossings on the cell's edges
    key1 = C1[:, 0] * (ny + 2) + C1[:, 1]
    key2 = C2[:, 0] * (ny + 2) + C2[:, 1]
    keys = np.r_[key1, key2]
    uk, inv = np.unique(keys, return_inverse=True)
    S = np.zeros((len(uk), 2))
    np.add.at(S, inv, np.r_[P, P])
    cnt = np.bincount(inv, minlength=len(uk)).astype(float)
    Vc = S / cnt[:, None]
    E = np.c_[inv[:len(P)], inv[len(P):]]
    E = np.unique(np.sort(E, 1), axis=0)
    E = E[E[:, 0] != E[:, 1]]
    deg = np.bincount(E.ravel(), minlength=len(Vc))
    crease_chains.stats = dict(nodes=len(Vc), edges=len(E), deg=np.bincount(deg).tolist())
    return [Vc[c] for c in YT.chains([tuple(e) for e in E])]


# ============================================================================================ the strip
def _outline_ccw():
    O = np.asarray(G.shell_outline(), float)
    area = 0.5 * np.sum(O[:, 0] * np.roll(O[:, 1], -1) - np.roll(O[:, 0], -1) * O[:, 1])
    return O if area > 0 else O[::-1].copy()


def strip_columns():
    """Column stations on the shell outline: (O (k, 2), outward normals (k, 2)) -- resampled by COL_LEN / COL_TURN and
    the change of the edge radius / top-land weight, a column on each insert junction."""
    O = _outline_ccw()
    n = len(O)
    T = np.roll(O, -3, 0) - np.roll(O, 3, 0)
    T = _unit(T)
    Nrm = np.c_[T[:, 1], -T[:, 0]]
    ang = np.unwrap(np.arctan2(T[:, 1], T[:, 0]))
    seg = np.linalg.norm(np.roll(O, -1, 0) - O, axis=1)
    s = np.r_[0.0, np.cumsum(seg[:-1])]
    r = r_edge(O[:, 0] - 0.5 * Nrm[:, 0], O[:, 1] - 0.5 * Nrm[:, 1])
    up = G.smoothstep(Nrm[:, 1], 0.35, 0.6)
    junc = G.tv("insert_side")[0]
    force = set()
    for sg in (1.0, -1.0):
        force.add(int(np.argmin(np.hypot(O[:, 0] - sg * junc[0], O[:, 1] - junc[1]))))
    start = min(force)
    order = np.r_[np.arange(start, n), np.arange(0, start)]
    cols = [start]
    last = start
    for i in order[1:]:
        dl = (s[i] - s[last]) % s[-1] if i != last else 0.0
        if (i in force or dl >= COL_LEN or abs(np.degrees(ang[i] - ang[last])) % 360.0 >= COL_TURN or
                abs(r[i] - r[last]) >= 0.12 or abs(up[i] - up[last]) >= 0.12):
            # don't leave a sliver column before a forced one
            cols.append(i)
            last = i
    cols = np.array(cols)
    # even out: a column closer than 0.35 x COL_LEN to the next forced / kept one is dropped unless forced
    keep = np.ones(len(cols), bool)
    for j in range(len(cols)):
        a, b = cols[j], cols[(j + 1) % len(cols)]
        d = (s[b] - s[a]) % s[-1]
        if d < 0.3 and a not in force:
            keep[j] = False
    cols = cols[keep]
    return O[cols], Nrm[cols], cols, s[cols]


def _aft_profile(Oi, ni, tb, m=240):
    """The aft section of one column: t from tb (the face) to 0 (the wall's top): (t, q (m, 2), A (m,))."""
    t = np.linspace(tb, 0.0, m)
    q = Oi[None, :] - t[:, None] * ni[None, :]
    tp = top(q[:, 0], q[:, 1])
    r = r_edge(q[:, 0], q[:, 1])
    A = np.where(t < r, tp - r + np.sqrt(np.maximum(r * r - (r - t) ** 2, 0.0)), tp)
    return t, q, A


def _front_A(q, t):
    return fwd_a(q[:, 0], q[:, 1]) + 0.5 - np.sqrt(np.maximum(0.25 - (0.5 - t) ** 2, 0.0))


def strip():
    """The strip's vertices: dict(P (k, nrow, 3) positions (u, h, a), Nn (k, nrow, 3) normals, kind (nrow,) 'aft' /
    'front', crease (k,) bool (the foot columns: aft and front meet without a wall), Q2 (k, 2) the terrain boundary
    points (row 0), front2 (k, 2) the front face's boundary (last row))."""
    O, Nrm, idx, s = strip_columns()
    k = len(O)
    rows_a, rows_f = N_AFT + 1, N_FRONT + 1
    P = np.zeros((k, rows_a + rows_f, 3))
    crease = np.zeros(k, bool)
    for i in range(k):
        Oi, ni = O[i], Nrm[i]
        rr = r_edge(*(Oi[None, :] - np.array([0.0, 1.0, 2.0, 3.0])[:, None] * ni[None, :]).T)
        tb = max(1.05, float(rr.max()) + 0.05)
        t, q, A = _aft_profile(Oi, ni, tb)
        qf = Oi[None, :] - np.linspace(0, 0.5, 120)[:, None] * ni[None, :]
        tf = np.linspace(0, 0.5, 120)
        Af = _front_A(qf, tf)
        t_end = 0.0
        if A[-1] - Af[0] < 0.02:                       # no wall: the aft round meets the front round (the foot)
            crease[i] = True

            def gap(tt):
                tt = np.atleast_1d(tt)
                return _aft_section_at(Oi, ni, tt)[2] - _front_A(Oi[None, :] - tt[:, None] * ni[None, :], tt)
            lo, hi = 0.0, 0.5
            for _ in range(50):
                mid = 0.5 * (lo + hi)
                if gap(mid)[0] > 0:
                    hi = mid
                else:
                    lo = mid
            t_end = 0.5 * (lo + hi)
            keepm = t > t_end
            t = np.r_[t[keepm], t_end]
            t, q, A = _aft_section_at(Oi, ni, t)
        # equal-turn rows along the aft profile (+ a little arc length so flat stretches get rows too)
        X = np.c_[t, A]
        d = np.diff(X, axis=0)
        L = np.linalg.norm(d, axis=1)
        psi = np.unwrap(np.arctan2(d[:, 1], d[:, 0]))
        w = np.r_[0.0, np.cumsum(np.abs(np.diff(psi)) + 0.12 * L[1:])]
        w = np.r_[0.0, w]
        targets = np.linspace(0.0, w[-1], rows_a)
        ti = np.interp(targets, w, np.arange(len(t)))
        tt = np.interp(ti, np.arange(len(t)), t)
        tt[0], tt[-1] = t[0], t[-1]
        _, qq, AA = _aft_section_at(Oi, ni, tt)
        P[i, :rows_a, :2], P[i, :rows_a, 2] = qq, AA
        # front rows: phi from phi* to 90 deg on the front round
        phi0 = math.acos(float(np.clip(1.0 - 2.0 * t_end, -1, 1))) if crease[i] else 0.0
        ph = np.linspace(phi0, 0.5 * math.pi, rows_f)
        tfr = 0.5 - 0.5 * np.cos(ph)
        qf = Oi[None, :] - tfr[:, None] * ni[None, :]
        P[i, rows_a:, :2], P[i, rows_a:, 2] = qf, _front_A(qf, tfr)
        if crease[i]:                                   # the crease point exactly shared
            P[i, rows_a] = P[i, rows_a - 1]
    Nn = np.zeros_like(P)
    Pa = P[:, :rows_a].reshape(-1, 3)
    Nn[:, :rows_a] = grad3(f_aft, Pa).reshape(k, rows_a, 3)
    Pf = P[:, rows_a:].reshape(-1, 3)
    Nn[:, rows_a:] = grad3(f_fwd, Pf).reshape(k, rows_f, 3)
    # the wall rows' normals (wall columns: the aft round's last and the front round's first row lie on the wall)
    wall = ~crease
    n3 = np.c_[Nrm, np.zeros(k)]
    Nn[wall, rows_a - 1] = n3[wall]
    Nn[wall, rows_a] = n3[wall]
    return dict(P=P, Nn=Nn, rows_a=rows_a, rows_f=rows_f, crease=crease, O=O, Nrm=Nrm)


def _aft_section_at(Oi, ni, t):
    t = np.asarray(t, float)
    q = Oi[None, :] - t[:, None] * ni[None, :]
    tp = top(q[:, 0], q[:, 1])
    r = r_edge(q[:, 0], q[:, 1])
    A = np.where(t < r, tp - r + np.sqrt(np.maximum(r * r - (r - t) ** 2, 0.0)), tp)
    return t, q, A


# ============================================================================================ the terrain
def label_normal(lab, X, GR):
    """Unit normals (u, h, a) of the piece `lab` of the aft-face height field at the front-view points X (n, 2)."""
    X = np.atleast_2d(np.asarray(X, float))
    tu, th = grad2(top, X[:, 0], X[:, 1])
    gu, gh = np.zeros(len(X)), np.zeros(len(X))
    k, kind, j, sg = decode(lab)
    if k >= 0:
        gr = GR[k]
        tau_u, tau_h = grad2(taper, X[:, 0], X[:, 1])
        if kind == "run":
            dc, foot, dirn, _ = gr.runs[j].query(X)
            v = X - foot
            # the gradient of dc on the label's own side: the run's side normal (NOT v / dc -- a crease point within
            # rounding of the groove bottom may lie on the other side, which gave it the other wall's normal)
            gd = np.c_[-dirn[:, 1], dirn[:, 0]] * sg
        else:
            v = X - gr.vertices[j]
            dc = np.linalg.norm(v, axis=1)
            gd = v / np.maximum(dc, 1e-12)[:, None]
        gu = gr.g * (tau_u - 2.0 * gd[:, 0] / gr.w)
        gh = gr.g * (tau_h - 2.0 * gd[:, 1] / gr.w)
    Hu, Hh = tu - gu, th - gh
    return _unit(np.c_[-Hu, -Hh, np.ones(len(X))])


def _chain_points(chains, tol=0.01, lo=0.8):
    """Simplified, resampled crease chains: (points (n, 2), edges (m, 2)); shared end points merged.  Each chain is
    simplified (Douglas-Peucker, tol mm) and its segments split to <= 4 x its local feature size (the median distance
    to the nearest other chain: the width of the groove walls beside it), lo .. 3.0 mm."""
    from scipy.spatial import cKDTree
    simp = [np.asarray(C, float)[YT.simplify(np.asarray(C, float), tol)] for C in chains if len(C) >= 2]
    dense_all = [np.asarray(C, float) for C in chains if len(C) >= 2]
    owner = np.concatenate([np.full(len(C), i) for i, C in enumerate(dense_all)])
    allp = np.vstack(dense_all)
    tree = cKDTree(allp)
    pts, edges = [], []
    key = {}

    def pid(p):
        kk = (round(float(p[0]), 6), round(float(p[1]), 6))
        if kk not in key:
            key[kk] = len(pts)
            pts.append(np.array(p, float))
        return key[kk]
    for i, (C, Q) in enumerate(zip(dense_all, simp)):
        d, j = tree.query(C, k=min(40, len(allp)))
        other = owner[j] != i
        dd = np.where(other, d, np.inf).min(1)
        lfs = float(np.median(dd[np.isfinite(dd)])) if np.isfinite(dd).any() else 2.0
        max_len = float(np.clip(6.0 * lfs, lo, 3.0))
        dense = [Q[:1]]
        for a, b in zip(Q[:-1], Q[1:]):
            n = max(1, int(math.ceil(np.linalg.norm(b - a) / max_len)))
            dense.append(a + (b - a) * np.linspace(0, 1, n + 1)[1:, None])
        Qd = np.vstack(dense)
        # no point closer than 0.3 x the spacing to the next (the end points kept)
        keep = [0]
        for m in range(1, len(Qd) - 1):
            if np.linalg.norm(Qd[m] - Qd[keep[-1]]) >= 0.3 * max_len and np.linalg.norm(Qd[-1] - Qd[m]) >= 0.3 * max_len:
                keep.append(m)
        keep.append(len(Qd) - 1)
        Qd = Qd[keep]
        ids = [pid(p) for p in Qd]
        edges += [(a, b) for a, b in zip(ids[:-1], ids[1:]) if a != b]
    return np.array(pts), np.array(edges, np.int64)


def tcs_ring(r=None, n=40):
    """The TCS bezel bore's circle (r = tcs_profile[5]) in the face plane, front-view (u, h) points (closed)."""
    D = G.T()
    c, nrm = G.tcs_axis()
    r = float(D["tcs_profile"][5]) if r is None else r
    e1 = np.array([1.0, 0.0, 0.0])
    e2 = np.cross(nrm, e1)
    a = np.linspace(0, 2 * math.pi, n, endpoint=False)
    P = c + r * (np.cos(a)[:, None] * e1 + np.sin(a)[:, None] * e2)
    return P[:, :2]


def terrain(B, GR, chains):
    """Triangulate the aft face inside the boundary loop B (k, 2) (the strip's row 0, CCW): returns (X (n, 2) front-view
    points -- the first k are B --, T (m, 3) triangles, tri labels (m,), crease vertex mask (n,))."""
    from matplotlib.path import Path
    kB = len(B)
    CP, CE = _chain_points(chains)
    inside = Path(np.vstack([B, B[:1]])).contains_points(CP)
    dd = -d2(CP[:, 0], CP[:, 1])
    okp = inside & (dd > 1.15)
    keep_e = okp[CE[:, 0]] & okp[CE[:, 1]]
    CE = CE[keep_e]
    used = np.unique(CE.ravel())
    remap = -np.ones(len(CP), np.int64)
    remap[used] = np.arange(len(used))
    CP, CE = CP[used], remap[CE]
    R = tcs_ring()
    # graded fill: hexagonal grids of the FILL_LEVELS spacings in bands of distance from the features
    # (boundary, creases, ring); 3 at most over the crown's R 20 blend
    from scipy.spatial import cKDTree
    feat = cKDTree(np.vstack([B, CP, R]))
    path = Path(np.vstack([B, B[:1]]))
    lo, hi = B.min(0), B.max(0)
    hc_ = float(G.T()["crown"][0])
    levels = list(FILL_LEVELS)
    Fp = []
    for li, hx in enumerate(levels):
        ys = np.arange(lo[1], hi[1], hx * math.sqrt(3) / 2)
        pts = [np.c_[xs, np.full_like(xs, y)] for j, y in enumerate(ys)
               for xs in [np.arange(lo[0] + (0.5 * hx if j % 2 else 0.0), hi[0], hx)]]
        Q = np.vstack(pts)
        Q = Q[path.contains_points(Q)]
        Q = Q[-d2(Q[:, 0], Q[:, 1]) > 1.05 + 0.5 * hx]
        dd, _ = feat.query(Q)
        smax = np.where(np.abs(Q[:, 1] - hc_) < 5.0, 3.0, 99.0)
        nxt = levels[li + 1] if li + 1 < len(levels) else 1e9
        ok = (dd >= 0.6 * hx) & (hx <= smax) & ((dd < 0.6 * nxt) | (nxt > smax))
        Fp.append(Q[ok])
    Fp = np.vstack(Fp)
    # thin out fill points closer than 0.5 x their own spacing to each other (band edges)
    t = cKDTree(Fp)
    pairs = t.query_pairs(0.55)
    drop = {j for i, j in pairs}
    Fp = Fp[[i for i in range(len(Fp)) if i not in drop]]
    oC, oR = kB, kB + len(CP)
    cons = [(i, (i + 1) % kB) for i in range(kB)]
    cons += [(oC + a, oC + b) for a, b in CE]
    cons += [(oR + i, oR + (i + 1) % len(R)) for i in range(len(R))]
    crease_v = None
    dense_ch = [np.asarray(C, float) for C in chains if len(C) >= 2]
    feat_dense = cKDTree(np.vstack([_densify(np.vstack([B, B[:1]]), 0.1), _densify(np.vstack([R, R[:1]]), 0.1)] +
                                   [_densify(C, 0.1) for C in dense_ch]))
    for rd in range(INTERP_ROUNDS + 1):
        X = np.vstack([B, CP, R, Fp])
        T = YT.cdt(X, cons)
        T = YT.inside(T, X, [np.arange(kB)])
        cen = X[T].mean(1)
        lab = pieces_at(cen, GR)[0]
        crease_v = np.zeros(len(X), bool)
        crease_v[oC:oR] = True
        if rd == INTERP_ROUNDS:
            break
        # the HIGHLIGHT criterion (yoke_mesh.interp_errors): where the corner normals interpolated over a face miss its piece's
        # exact normal by more than INTERP_TOL at the centroid / an edge midpoint, the centroid becomes a fill point
        err = terrain_interp_error(X, T, lab, crease_v, GR)
        bad = err > INTERP_TOL
        if not bad.any():
            break
        newp = cen[bad]
        d_old, _ = cKDTree(X).query(newp)
        d_feat, _ = feat_dense.query(newp)                # clear of the creases / boundary / ring too (no slivers)
        newp = newp[(d_old > INTERP_MIN) & (d_feat > INTERP_MIN)]
        if len(newp):
            keep = np.ones(len(newp), bool)
            for i, j in cKDTree(newp).query_pairs(INTERP_MIN):
                keep[j] = False
            newp = newp[keep]
        if not len(newp):
            break
        Fp = np.vstack([Fp, newp])
    return X, T, lab, crease_v, (oC, oR)


INTERP_TOL = 1.0         # deg: the gloss cover's highlight criterion (yoke_mesh.interp_errors: interpolated vs exact normal)
INTERP_MIN = 0.45        # mm: no refinement point closer than this to another point
INTERP_ROUNDS = 4


def terrain_interp_error(X, T, lab, crease_v, GR):
    """Per terrain triangle: the largest angle (deg) between its corner normals interpolated (then normalised) and its
    piece's exact normal, at the centroid and the three edge midpoints (front-view samples; the heights are exact)."""
    labi = pieces_at(X, GR)[0]
    Lc = np.where(crease_v[T], lab[:, None], labi[T])                  # each corner's piece (a crease point: the face's)
    Nc = np.zeros(T.shape + (3,))
    for L in np.unique(Lc):
        m = Lc == L
        Nc[m] = label_normal(int(L), X[T[m]], GR)
    W = np.array([[1 / 3, 1 / 3, 1 / 3], [0.5, 0.5, 0.0], [0.0, 0.5, 0.5], [0.5, 0.0, 0.5]])
    err = np.zeros(len(T))
    for w in W:
        S = np.einsum("k,fkd->fd", w, X[T])
        Ni = _unit(np.einsum("k,fkd->fd", w, Nc))
        Ne = np.zeros_like(Ni)
        for L in np.unique(lab):
            m = lab == L
            Ne[m] = label_normal(int(L), S[m], GR)
        err = np.maximum(err, np.degrees(np.arccos(np.clip(np.sum(Ni * Ne, 1), -1.0, 1.0))))
    return err


# ============================================================================================ groove finish
GROOVE_MAT = "yoke_groove"   # rev Q (3-D judges r4 FID4-01): the grooves' flanks as their cavity shadow -- every photo shows
#                              the step V, the badge outline / speed lines and the insert parting grooves as DARK lines
#                              (the darkest pixel across the step 0.00-0.18 of the insert in the s/n 3001 views); the yoke
#                              carries no baked occlusion, so the 0.4-2 mm V flanks took the face's full light and their
#                              up-facing flanks read as bright bevels (0.80-0.89, a 1.10-1.14 ridge).  L6Y item 15.
GROOVE_INSERT_DARK = ("side_r", "side_l", "lower")
GROOVE_LIGHT = (0.0, 1.0)
GROOVE_END_LIT = ("step",)
#                            rev R (yoke judge r5 FID5-01 / 07: rev Q's every flank dark drew the side grooves, the lower
#                            insert's outline and the badge as a uniform near-black INK line on both flanks, from every
#                            direction; in every photo only ONE flank of a groove is dark and the other reads as a lit
#                            rim): the flanks are DIRECTIONAL.  The parting grooves between the white cover and an insert
#                            (GROOVE_INSERT_DARK): the flank on the INSERT's side -- the insert's cut edge in the gap's
#                            shadow -- takes GROOVE_MAT, the cover's side keeps the white (its rolled gloss edge catching
#                            the light).  Seen from aside, a groove shows mostly the flank facing the camera, which is the
#                            insert's on the NEAR groove and the cover's on the FAR one: from the centreline cameras
#                            (P1046408 / 09 / 10, Mexico) the inboard groove reads dark and the outboard one lit, from the
#                            aft-outboard AOPA camera the other way round -- the photos' darkest pixel across the upper
#                            insert's sides (judge r5: 0.28-0.70 near / 0.79-0.96 far of the reference; AOPA 0.02 / 0.86).
#                            The step and the badge outline / speed lines (both sides an insert) by the light from ABOVE
#                            (GROOVE_LIGHT, front view (u, h)): the down-facing flank dark, the up-facing one keeps the
#                            face's finish -- the step's dark upper flank over its lit lower one as rev Q, the badge a
#                            relief shadowed along its lower edges.  The step's round end cones (GROOVE_END_LIT: ~1 mm past
#                            the side grooves, CR4-07) keep the face's finish -- dark, they read as black faceted nubs
#                            (FID5-07); the step's dark line now ends on the side groove's line, as in Mexico / AOPA


def flank_facing(lab, X, GR):
    """Unit front-view (u, h) direction a groove flank / end cone of label `lab` faces at the points X (n, 2): toward the
    groove's bottom line (the in-plane part of the flank's normal, the face's own slope aside)."""
    X = np.atleast_2d(np.asarray(X, float))
    k, kind, j, sg = decode(lab)
    gr = GR[k]
    if kind == "run":
        _, foot, dirn, _ = gr.runs[j].query(X)
        gd = np.c_[-dirn[:, 1], dirn[:, 0]] * sg            # away from the bottom line, on the label's own side
    else:
        v = X - gr.vertices[j]
        gd = v / np.maximum(np.linalg.norm(v, axis=1), 1e-12)[:, None]
    return -gd


def groove_faces(lab, C, GR):
    """Per terrain triangle (labels lab, front-view centroids C (n, 2)): True where it lies on a groove flank / end cone
    that takes GROOVE_MAT (rev R, directional): on a GROOVE_INSERT_DARK groove the flank on the insert's side (the face
    just beyond it, on its own side, an insert: yoke_geom.cover_part > 0), on the others the flank turned away from
    GROOVE_LIGHT (the end cones of a GROOVE_END_LIT groove never); the other flank keeps the face's finish."""
    lab = np.asarray(lab)
    C = np.asarray(C, float)[:, :2]
    out = np.zeros(len(lab), bool)
    Ld = np.asarray(GROOVE_LIGHT, float)
    for L in np.unique(lab[lab != 0]):
        m = np.nonzero(lab == L)[0]
        k, kind, _, _ = decode(int(L))
        gr = GR[k]
        if kind == "cone" and gr.name in GROOVE_END_LIT:
            continue
        f = flank_facing(int(L), C[m], GR)
        if gr.name in GROOVE_INSERT_DARK:
            Q = C[m] - f * (0.5 * gr.w + 0.15)                  # just beyond the groove's edge on the flank's own side
            out[m[G.cover_part(Q[:, 0], Q[:, 1]) > 0]] = True
        else:
            out[m[f @ Ld < 0.0]] = True
    return out


# ============================================================================================ assembly
def cover_meshes(verbose=False):
    """The cover as [(V (n, 3), F (m, 3), N (n, 3), material)] in yoke-local mm (welded by position across materials)."""
    import time
    t0 = time.time()
    GR = grooves()
    S = strip()
    P, Nn, ra = S["P"], S["Nn"], S["rows_a"]
    k, nr = P.shape[:2]
    if verbose:
        print(f"  cover strip: {k} columns x {nr} rows ({int(S['crease'].sum())} without a wall), {time.time() - t0:.1f}s")
    chains = crease_chains(GR)
    B = P[:, 0, :2]
    X, T, lab, crease_v, (oC, oR) = terrain(B, GR, chains)
    if verbose:
        print(f"  cover terrain: {len(X)} points, {len(T)} triangles, {len(chains)} crease chains, {time.time() - t0:.1f}s")
    # ---- vertices: the strip's (k x nr) first, then the terrain's own points (one copy per crease piece)
    VV = [P.reshape(-1, 3)]
    NN = [Nn.reshape(-1, 3)]
    FF = []
    sid = np.arange(k * nr).reshape(k, nr)
    # strip quads
    for i in range(k):
        j = (i + 1) % k
        for r_ in range(nr - 1):
            if r_ == ra - 1 and (S["crease"][i] and S["crease"][j]):
                continue                                           # the foot crease: no wall band
            a, b, c, d = sid[i, r_], sid[j, r_], sid[j, r_ + 1], sid[i, r_ + 1]
            for tri in ((a, b, c), (a, c, d)):
                p3 = P.reshape(-1, 3)[list(tri)]
                if np.linalg.norm(np.cross(p3[1] - p3[0], p3[2] - p3[0])) > 1e-9:
                    FF.append(tri)
    FF = np.array(FF, np.int64)
    # terrain: point heights / own labels
    Xi = X[k:]
    labi, depth, _, _ = pieces_at(Xi, GR)
    Hi = top(Xi[:, 0], Xi[:, 1]) - np.maximum(depth, 0.0)
    base = k * nr
    corner_ids = np.zeros_like(T)
    nv = base
    newV, newN = [], []
    keymap = {}
    for t_i, tri in enumerate(T):
        for c_i, v in enumerate(tri):
            if v < k:                                              # a strip boundary vertex
                corner_ids[t_i, c_i] = sid[v, 0]
                continue
            L = int(lab[t_i]) if crease_v[v] else int(labi[v - k])
            key = (int(v), L)
            if key not in keymap:
                keymap[key] = nv
                newV.append(np.r_[X[v], Hi[v - k]])
                newN.append((L, v))
                nv += 1
            corner_ids[t_i, c_i] = keymap[key]
    # normals by label, batched
    NL = np.zeros((len(newN), 3))
    labs = np.array([L for L, _ in newN])
    vs = np.array([v for _, v in newN])
    for L in np.unique(labs):
        m = labs == L
        NL[m] = label_normal(L, X[vs[m]], GR)
    VV.append(np.array(newV))
    NN.append(NL)
    V = np.vstack(VV)
    N = np.vstack(NN)
    FT = corner_ids
    # ---- front face (hidden, against the body): the last front row + a coarse fill
    fr = P[:, nr - 1]
    from matplotlib.path import Path
    B2 = fr[:, :2]
    lo, hi = B2.min(0), B2.max(0)
    hx = FRONT_FILL
    ys = np.arange(lo[1] + 0.5 * hx, hi[1], hx * math.sqrt(3) / 2)
    Gp = np.vstack([np.c_[xs, np.full_like(xs, y)] for j, y in enumerate(ys)
                    for xs in [np.arange(lo[0] + (0.5 * hx if j % 2 else 0.0), hi[0], hx)]])
    Gp = Gp[Path(np.vstack([B2, B2[:1]])).contains_points(Gp)]
    Gp = Gp[-d2(Gp[:, 0], Gp[:, 1]) > 0.6 * hx]
    # an inner ring FRONT_RING[0] inside the boundary, FRONT_RING[1] apart: the coarse fill never fans out to the dense
    # strip columns directly (slivers)
    seg = np.linalg.norm(np.roll(B2, -1, 0) - B2, axis=1)
    sarc = np.r_[0.0, np.cumsum(seg)]
    nr_ = max(8, int(sarc[-1] / FRONT_RING[1]))
    t_ = np.linspace(0.0, sarc[-1], nr_, endpoint=False)
    Bc = np.vstack([B2, B2[:1]])
    Rq = np.c_[np.interp(t_, sarc, Bc[:, 0]), np.interp(t_, sarc, Bc[:, 1])]
    for _ in range(3):                                   # walk each point inward to d2 = -FRONT_RING along the gradient
        dq = d2(Rq[:, 0], Rq[:, 1])
        e = 1e-3
        g = np.c_[d2(Rq[:, 0] + e, Rq[:, 1]) - d2(Rq[:, 0] - e, Rq[:, 1]),
                  d2(Rq[:, 0], Rq[:, 1] + e) - d2(Rq[:, 0], Rq[:, 1] - e)] / (2 * e)
        g /= np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-9)
        Rq = Rq - (dq + FRONT_RING[0])[:, None] * g
    from scipy.spatial import cKDTree
    keep = np.ones(len(Rq), bool)                        # concave corners: ring points closer than 0.7 x spacing
    for i in range(len(Rq)):
        if keep[i]:
            near = cKDTree(Rq[i + 1:]).query_ball_point(Rq[i], 0.7 * FRONT_RING[1]) if i + 1 < len(Rq) else []
            for j in near:
                keep[i + 1 + j] = False
    Rq = Rq[keep & Path(Bc).contains_points(Rq)]
    if len(Gp):
        Gp = Gp[cKDTree(Rq).query(Gp)[0] > 0.6 * hx]
    Gp = np.vstack([Rq, Gp])
    Xf = np.vstack([B2, Gp])
    Tf = YT.cdt(Xf, [(i, (i + 1) % k) for i in range(k)])
    Tf = YT.inside(Tf, Xf, [np.arange(k)])
    Af = fwd_a(Gp[:, 0], Gp[:, 1])
    Vf = np.c_[Gp, Af]
    Nf = grad3(f_fwd, Vf) if len(Vf) else np.zeros((0, 3))
    of = len(V)
    V = np.vstack([V, Vf])
    N = np.vstack([N, Nf])
    FFr = np.where(Tf < k, sid[np.minimum(Tf, k - 1), nr - 1], of + Tf - k)
    # ---- materials by front-view position; orientation by the corner normals
    allF = np.vstack([FF, FT, FFr])
    C2 = V[allF].mean(1)[:, :2]
    part = G.cover_part(C2[:, 0], C2[:, 1])
    mats = np.array(["yoke_white", "yoke_silver", "yoke_silver_dark"])[part]
    ring = tcs_ring()
    in_ring = Path(np.vstack([ring, ring[:1]])).contains_points(C2)
    in_ring[:len(FF)] = False
    in_ring[len(FF) + len(FT):] = False
    mats = np.where(in_ring, "black", mats)
    gf = np.zeros(len(allF), bool)
    gf[len(FF):len(FF) + len(FT)] = groove_faces(lab, X[T].mean(1), GR)
    mats = np.where(gf & ~in_ring, GROOVE_MAT, mats)
    fn = np.cross(V[allF[:, 1]] - V[allF[:, 0]], V[allF[:, 2]] - V[allF[:, 0]])
    flip = np.sum(fn * N[allF].sum(1), 1) < 0
    allF[flip] = allF[flip][:, ::-1]
    out = []
    for m in np.unique(mats):
        sel = mats == m
        Fm = allF[sel]
        u, inv = np.unique(Fm.ravel(), return_inverse=True)
        out.append((V[u], inv.reshape(-1, 3), _unit(N[u]), str(m)))
    if verbose:
        print(f"  cover: {len(allF)} triangles ({', '.join(f'{m} {len(f)}' for _, f, _, m in out)}), "
              f"{time.time() - t0:.1f}s")
    return out
