"""
The Stage-3 yoke (rev M: sheets L6Y rev E / L6Y2 rev D, interior.YOKE_DESIGN): the 3-D meshes of the solids of
model/yoke_geom.py, in YOKE-LOCAL MILLIMETRES (u outboard -- the co-pilot sense --, h up from the column axis, a aft of
the aft face at the insert step), placed by place() for either seat (the pilot yoke is the mirror image).

  THE COVER (model/yoke_cover.py): the white shell with its inserts, grooves, badge and TCS seat as an explicit strip
  along its outline and a crease-exact terrain (constrained Delaunay, exact heights and piece normals), refined where
  its interpolated normals miss the exact ones by > 1 deg.
  THE MOULDING (model/yoke_mesh.py, yoke_patch.py): body + both grips joined by the rolling-ball round, the heads, the
  AFCS boss -- an adaptive octree dual-contoured on the field, every smooth vertex ON the zero level with the
  field-gradient normal, decimated under the highlight criterion (yoke_mesh.decimate_interp); the pads' pockets
  (groove, bead, leather) and the trim face's grooves as explicit crease-exact patches stitched into its cut loops;
  normals split only along the creases the solids draw.
  PARAMETRIC SWITCHES (here): the TCS bezel and button, the AFCS cap and the push button's cap as REVOLVES of their
  profiles (yoke_geom.tcs_profiles / afcs / button_cap: true arcs for the rounds the solids sample as polygons), the hex
  collar, the split trim rocker's two lobes and the forward-face switches as ROUNDED EXTRUSIONS (outline, top height
  field, the tabled top-edge round as an exact rolling quarter circle), the badge's raised blank plate (rev N); the
  legends (YOKE_DESIGN legends) as words of plain letter BLOCKS (rev N: rev M's radial ticks read as a dial), thin slabs
  0.12 proud of the face they are printed on -- no lettering.
Every piece is a closed (watertight) mesh with per-vertex normals; materials per the L6Y items / finishes table.
"""
from __future__ import annotations

import math

import numpy as np

from model import yoke_geom as G

TICK_W = 0.35                  # mm: legend tick stroke width (drawn 0.20-0.30 at 1:1..2:1) [E]
TICK_PROUD = 0.12              # mm: the ticks' paint layer stands this proud (above fit_check 26's 0.1 mm coplanarity)
ANG_STEP = math.radians(12.0)  # revolve: azimuth step on the outer rings (the cad.res interior turn criterion is 20 deg:
ARC_STEP = math.radians(15.0)  # a quad's diagonal turns ~hypot(azimuth, profile) = 19.2 deg); profile arcs / rounds


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


# ============================================================================================ piece container
class Piece:
    """A closed triangle mesh in yoke-local mm: V (n, 3), F (m, 3), N (n, 3) unit vertex normals, material."""

    def __init__(self, V, F, N, mat, name=""):
        self.V = np.asarray(V, float)
        self.F = np.asarray(F, np.int64)
        self.N = _unit(N)
        self.mat, self.name = mat, name

    def oriented(self):
        """Wind every face so its geometric normal agrees with its corner normals."""
        fn = np.cross(self.V[self.F[:, 1]] - self.V[self.F[:, 0]], self.V[self.F[:, 2]] - self.V[self.F[:, 0]])
        flip = np.sum(fn * self.N[self.F].sum(1), 1) < 0
        F = self.F.copy()
        F[flip] = F[flip][:, ::-1]
        return Piece(self.V, F, self.N, self.mat, self.name)


def merge(pieces, mat=None, name=""):
    V, F, N, o = [], [], [], 0
    for p in pieces:
        V.append(p.V)
        N.append(p.N)
        F.append(p.F + o)
        o += len(p.V)
    return Piece(np.vstack(V), np.vstack(F), np.vstack(N), mat or pieces[0].mat, name)


def in_frame(P2z, N2z, c, ex, ey, ez):
    """(x, y, z) frame coordinates / normals -> yoke-local (u, h, a)."""
    R = np.stack([ex, ey, ez], 0)
    return c + np.asarray(P2z, float) @ R, np.asarray(N2z, float) @ R


# ============================================================================================ revolves
ARC_SAG = 0.015                # mm: a small round's rows may turn more than ARC_STEP while their chord sag stays below
#                                this (cad.res interior: a turn over 20 deg only below 0.02 mm of bow)


def _arc_rows(R, sweep):
    """Rows over an arc of radius R (mm) and the angle sweep: ARC_STEP, or wider steps on small radii whose chord sag
    stays <= ARC_SAG (R 0.3: 30 deg) -- the thin rows of a sub-millimetre round would be slivers."""
    step = ARC_STEP
    if R > 1e-9 and ARC_SAG < R:
        step = max(step, 2.0 * math.acos(1.0 - ARC_SAG / R))
    return max(2, int(math.ceil(sweep / step - 1e-9)))


def _sample_profile(segs, max_len=None):
    """Profile pieces in (r, z) -> runs of points with outward normals [(P (k, 2), N (k, 2))], one run per smooth
    stretch: consecutive pieces whose tangents agree within 1 deg share their end point, a crease starts a new run.
    segs: ('L', p0, p1) lines, ('A', centre, R, a0, a1) arcs (a0 -> a1, radians; the outward normal is the radial
    direction for a convex arc (R > 0), toward the centre for a concave one (R < 0)).  Straight pieces are one row
    (flat along the profile) unless max_len is given; arcs at ARC_STEP."""
    pts = []
    for s in segs:
        if s[0] == "C":                                              # explicit points + outward normals
            P, N = np.asarray(s[1], float), _unit(np.asarray(s[2], float))
            T = np.gradient(P, axis=0)
            T = _unit(T)
        elif s[0] == "L":
            p0, p1 = np.asarray(s[1], float), np.asarray(s[2], float)
            n = 1 if max_len is None else max(1, int(math.ceil(np.linalg.norm(p1 - p0) / max_len)))
            t = np.linspace(0.0, 1.0, n + 1)[:, None]
            P = p0 + t * (p1 - p0)
            d = _unit(p1 - p0)
            N = np.repeat(np.array([[d[1], -d[0]]]), len(P), 0)
            T = np.repeat(d[None], len(P), 0)
        else:
            c, R, a0, a1 = np.asarray(s[1], float), float(s[2]), float(s[3]), float(s[4])
            n = max(_arc_rows(abs(R), abs(a1 - a0)),
                    0 if max_len is None else int(math.ceil(abs(R * (a1 - a0)) / max_len)),
                    # rounds of 0.6 mm and up: rows <= ARC_STEP, so the quads' diagonals across the <= 12 deg azimuth
                    # steps turn < 20 deg (cad.res's interior criterion: it had split them at build, 2 faces an edge)
                    int(math.ceil(abs(a1 - a0) / ARC_STEP - 1e-9)) if abs(R) >= 0.6 else 0)
            a = np.linspace(a0, a1, n + 1)
            e = np.c_[np.cos(a), np.sin(a)]
            P = c + abs(R) * e
            N = e if R > 0 else -e
            T = np.c_[-np.sin(a), np.cos(a)] * (1.0 if a1 > a0 else -1.0)
        pts.append((P, N, T))
    runs = []
    curP, curN = [pts[0][0]], [pts[0][1]]
    for (P0, N0, T0), (P1, N1, T1) in zip(pts[:-1], pts[1:]):
        if np.linalg.norm(P0[-1] - P1[0]) > 1e-6:
            raise ValueError("profile pieces do not join")
        if float(np.dot(T0[-1], T1[0])) > math.cos(math.radians(1.0)):          # smooth: share the joint
            curP.append(P1[1:])
            curN.append(N1[1:])
        else:
            runs.append((np.vstack(curP), np.vstack(curN)))
            curP, curN = [P1], [N1]
    runs.append((np.vstack(curP), np.vstack(curN)))
    return runs


def _ring_count(r, n_max):
    if r < 1e-9:
        return 1
    n = int(math.ceil(2.0 * math.pi * r / 0.8))
    return int(np.clip(n, 8, n_max))


def _zip(ia, aa, ib, ab):
    """Triangles between two closed rings (vertex ids ia / ib at ascending angles aa / ab from 0)."""
    na, nb = len(ia), len(ib)
    if na == 1 or nb == 1:
        if na == 1:
            return [(ia[0], ib[(j + 1) % nb], ib[j]) for j in range(nb)]
        return [(ib[0], ia[j], ia[(j + 1) % na]) for j in range(na)]
    aa2 = np.r_[aa, aa[0] + 2 * math.pi]
    ab2 = np.r_[ab, ab[0] + 2 * math.pi]
    i = j = 0
    out = []
    while i < na or j < nb:
        if j >= nb or (i < na and aa2[i + 1] <= ab2[j + 1]):
            out.append((ia[i % na], ia[(i + 1) % na], ib[j % nb]))
            i += 1
        else:
            out.append((ia[i % na], ib[(j + 1) % nb], ib[j % nb]))
            j += 1
    return out


def revolve(segs, c, axis, ref, mat, name="", n_max=64, max_len=None):
    """Closed surface of revolution of the profile pieces segs (r, z) about the axis through c (z along `axis`, r = 0
    there; angle 0 along `ref`): rings of _ring_count vertices (<= n_max, 7.5 deg on the outer rings), zipped where
    the counts change; exact profile normals, split at the profile's creases."""
    axis = _unit(axis)
    e1 = _unit(np.asarray(ref, float) - axis * np.dot(ref, axis))
    e2 = np.cross(axis, e1)
    n_max = max(8, min(n_max, int(math.ceil(2 * math.pi / ANG_STEP))))
    V, N, F = [], [], []
    o = 0
    for P, Nr in _sample_profile(segs, max_len):
        rings = []
        for (r, z), (nr, nz) in zip(P, Nr):
            k = _ring_count(r, n_max)
            ang = np.arange(k) * 2 * math.pi / k
            ca, sa = np.cos(ang), np.sin(ang)
            rad = ca[:, None] * e1 + sa[:, None] * e2
            V.append(c + z * axis + r * rad)
            N.append(nz * axis + nr * rad if r > 1e-9 else np.repeat((nz * axis + nr * e1)[None], k, 0))
            rings.append((np.arange(o, o + k), ang))
            o += k
        for (ia, aa), (ib, ab) in zip(rings[:-1], rings[1:]):
            F += _zip(ia, aa, ib, ab)
    V, N = np.vstack(V), np.vstack(N)
    poles = np.linalg.norm(np.cross(V - c, axis), axis=1) < 1e-9
    N[poles] = _unit(N[poles])
    return Piece(V, np.array(F), N, mat, name).oriented()


# ============================================================================================ rounded extrusions
def rounded_extrusion(outline, sharp, frame, z0, top, r_edge, mat, name="", inner_step=1.0):
    """Closed solid: the outline (closed CCW polygon in the frame's (x, y), dense along its curves; sharp[i] marks the
    corners) extruded along z from z0 to the top height field top(x, y) -> (z, dz/dx, dz/dy), its top edge rounded R
    r_edge exactly as yoke_geom.rmax rounds it (rows theta: inward offset r (1 - cos), height top - r (1 - sin));
    at a sharp corner the offsets mitre and the normals split.  frame = (c, ex, ey, ez)."""
    Q = np.asarray(outline, float)
    k = len(Q)
    sharp = np.asarray(sharp, bool)
    e_out = np.roll(Q, -1, 0) - Q                                     # edge i: Q[i] -> Q[i + 1]
    n_edge = _unit(np.c_[e_out[:, 1], -e_out[:, 0]])                   # CCW: outward = right of the edge
    n_in, n_outv = np.roll(n_edge, 1, 0), n_edge                        # incoming / outgoing edge normals at vertex i
    n_s = _unit(n_in + n_outv)
    miter = (n_in + n_outv) / (1.0 + np.sum(n_in * n_outv, 1))[:, None]
    nth = _arc_rows(r_edge, 0.5 * math.pi)
    th = np.linspace(0.0, 0.5 * math.pi, nth + 1)
    V, N, F = [], [], []

    def add(P, Nn):
        V.append(P)
        N.append(Nn)
        return len(V) - 1

    cols = []                                    # per vertex: (incoming-side column ids, outgoing-side column ids)
    for i in range(k):
        copies = [n_in[i], n_outv[i]] if sharp[i] else [n_s[i]]
        mv = miter[i] if sharp[i] else n_s[i]
        ids_c = []
        for nc in copies:
            col = []
            zt, _, _ = top(Q[i, 0], Q[i, 1])
            col.append(add(np.r_[Q[i], z0], np.r_[nc, 0.0]))
            for t in th:
                q = Q[i] - r_edge * (1.0 - math.cos(t)) * mv
                z, zx, zy = top(q[0], q[1])
                nn = math.cos(t) * np.r_[nc, 0.0] + math.sin(t) * _unit(np.r_[-zx, -zy, 1.0])
                col.append(add(np.r_[q, z - r_edge * (1.0 - math.sin(t))], _unit(nn)))
            ids_c.append(col)
        cols.append((ids_c[0], ids_c[-1]))
    for i in range(k):
        a, b = cols[i][1], cols[(i + 1) % k][0]
        for j in range(len(a) - 1):
            F += [(a[j], b[j], b[j + 1]), (a[j], b[j + 1], a[j + 1])]
    # top cap: the last row (offset r) + interior points; bottom cap (hidden in the parent solid) likewise
    ring = [cols[i][1][-1] for i in range(k)]
    B = np.array([V[j][:2] for j in ring])
    tri, Gp = _cap(B, inner_step)
    ids = list(ring)
    for p in Gp:
        z, zx, zy = top(p[0], p[1])
        ids.append(add(np.r_[p, z], _unit(np.r_[-zx, -zy, 1.0])))
    F += [tuple(ids[j] for j in t) for t in tri]
    bot = [cols[i][1][0] for i in range(k)]
    tri, Gp = _cap(Q, 3.0)                                             # hidden in the parent solid
    ids = [add(V[j], np.array([0.0, 0.0, -1.0])) for j in bot]
    ids += [add(np.r_[p, z0], np.array([0.0, 0.0, -1.0])) for p in Gp]
    F += [tuple(ids[j] for j in t) for t in tri]
    V3, N3 = in_frame(np.array(V), np.array(N), *frame)
    return Piece(V3, np.array(F), N3, mat, name).oriented()


def _cap(B, step):
    """Triangles of the convex polygon B (k, 2) with interior points on a grid of `step` (kept >= 0.6 step inside):
    (triangles indexing [B, interior], interior points)."""
    from scipy.spatial import Delaunay
    from cad import sdf2d
    lo, hi = B.min(0), B.max(0)
    gx, gy = np.meshgrid(np.arange(lo[0], hi[0], step) + 0.5 * step, np.arange(lo[1], hi[1], step) + 0.5 * step)
    Gp = np.c_[gx.ravel(), gy.ravel()]
    Gp = Gp[sdf2d.polygon(Gp[:, 0], Gp[:, 1], B) < -0.6 * step]
    allp = np.vstack([B, Gp])
    tri = Delaunay(allp).simplices
    cen = allp[tri].mean(1)
    return tri[sdf2d.polygon(cen[:, 0], cen[:, 1], B) < 0], Gp


def outline_arc(c, R, a0, a1, step=ARC_STEP, max_len=1.0):
    n = max(2, int(math.ceil(abs(a1 - a0) / step)), int(math.ceil(R * abs(a1 - a0) / max_len)))
    a = np.linspace(a0, a1, n + 1)
    return np.c_[c[0] + R * np.cos(a), c[1] + R * np.sin(a)]


def outline_line(p0, p1, max_len=1.0):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    n = max(1, int(math.ceil(np.linalg.norm(p1 - p0) / max_len)))
    return p0 + np.linspace(0.0, 1.0, n + 1)[:, None] * (p1 - p0)


def _closed(parts, corners):
    """Concatenate outline parts (each starting where the previous ended) into a closed CCW polygon; corners: indices
    of the parts whose FIRST point is a sharp corner."""
    pts, sharp = [], []
    for i, P in enumerate(parts):
        P = np.asarray(P, float)
        pts.append(P[:-1])
        s = np.zeros(len(P) - 1, bool)
        s[0] = i in corners
        sharp.append(s)
    P, s = np.vstack(pts), np.concatenate(sharp)
    area = 0.5 * np.sum(P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1])
    if area < 0:
        P, s = P[::-1], s[::-1]
    return P, s


# ============================================================================================ the switches
def tcs_pieces():
    """TCS: gloss-black bezel (outer edge rolled, the dish, the bore) and the satin domed button standing proud of it,
    seated tcs_seat in the cover (yoke_geom.tcs_profiles, true arcs)."""
    D = G.T()
    c, nrm = G.tcs_axis()
    od, bd = float(D["tcs"][2]), float(D["tcs"][3])
    bz, rr, dish, dome, below, r_in, r_out = (float(x) for x in D["tcs_profile"][:7])
    seat = float(D["tcs_seat"])
    Rb, re = 0.5 * od, min(rr, bz)
    bez = [("L", (r_in, -seat), (Rb, -seat)), ("L", (Rb, -seat), (Rb, bz - re)),
           ("A", (Rb - re, bz - re), re, 0.0, 0.5 * math.pi), ("L", (Rb - re, bz), (r_in, bz - dish)),
           ("L", (r_in, bz - dish), (r_in, -seat))]
    top = bz - below
    rb = 0.5 * bd
    rs = np.linspace(rb, 0.0, 9)
    btn = [("L", (0.0, -seat), (rb, -seat)), ("L", (rb, -seat), (rb, top - dome)),
           ("C", np.c_[rs, top - dome * (rs / rb) ** 2], np.c_[2.0 * dome * rs / rb ** 2, np.ones_like(rs)])]
    ref = np.array([1.0, 0.0, 0.0])
    return [revolve(bez, c, nrm, ref, "gloss_black", "tcs_bezel"), revolve(btn, c, nrm, ref, "black", "tcs_button")]


def afcs_pieces():
    """The red AFCS cap (afcs[2] dia x afcs[3], top edge R afcs_boss[4]) on the boss face, seated 1 mm."""
    D = G.T()
    c, nrm = G.afcs_axis()
    r, hh, re = 0.5 * float(D["afcs"][2]), float(D["afcs"][3]), float(D["afcs_boss"][4])
    prof = [("L", (0.0, -1.0), (r, -1.0)), ("L", (r, -1.0), (r, hh - re)), ("A", (r - re, hh - re), re, 0.0, 0.5 * math.pi),
            ("L", (r - re, hh), (0.0, hh))]
    return [revolve(prof, c, nrm, np.array([1.0, 0.0, 0.0]), "button_red", "afcs_cap")]


def _mirror_u(p):
    """Own sense of the inboard grip -> the yoke's (co-pilot) sense."""
    m = np.array([-1.0, 1.0, 1.0])
    return Piece(p.V * m, p.F, p.N * m, p.mat, p.name).oriented()


def button_pieces():
    """The inboard head's push button (MAP LIGHTS): the satin-nickel hex collar (rev N, judges FID1-04; rounded
    extrusion, top edges R 0.3) and the
    smooth cap (revolve: top R 1, the spherical centre dimple) on the shield facet; built in the inboard grip's own sense
    and mirrored."""
    D = G.T()
    c, n, eu, ev = G.button_frame()
    b = D["button"]
    rc, hp = 0.5 * float(b[2]), float(b[5])
    ang = np.radians(np.arange(6) * 60.0 + 30.0)
    hexa = np.c_[rc * np.cos(ang), rc * np.sin(ang)]
    parts = [outline_line(hexa[i], hexa[(i + 1) % 6], 1.5) for i in range(6)]
    P, sh = _closed(parts, set(range(6)))
    collar = rounded_extrusion(P, sh, (c, eu, ev, n), -1.0, lambda x, y: (hp, 0.0, 0.0), 0.3, "yoke_nickel",
                               "button_collar", inner_step=2.5)
    r, hh, dd, ddep = 0.5 * float(b[3]), float(b[4]), float(b[7]), float(b[8])
    zt = hp + hh
    rs = (0.25 * dd * dd + ddep * ddep) / (2.0 * ddep)
    zc = zt + rs - ddep
    a0 = math.atan2(zt - zc, 0.5 * dd)
    prof = [("L", (0.0, 0.0), (r, 0.0)), ("L", (r, 0.0), (r, zt - 1.0)), ("A", (r - 1.0, zt - 1.0), 1.0, 0.0, 0.5 * math.pi),
            ("L", (r - 1.0, zt), (0.5 * dd, zt)), ("A", (0.0, zc), -rs, a0, -0.5 * math.pi)]
    cap = revolve(prof, c, n, eu, "black", "button_cap")
    return [_mirror_u(collar), _mirror_u(cap)]


def trim_pieces():
    """The split bow-tie pitch-trim rocker across the outboard head's round face: two mirrored lobes (yoke_geom
    rocker_lobe: from the split to the round end), extruded from 1 below the slot floor (rev N: the slot is recessed
    trim_slot[0]) to the saddle top z = hm + (he - hm) (|x| / (L / 2)) ^ sexp, top edges R trim_grooves[2]; satin dark
    grey yoke_rocker (rev N, judges FID1-05: lighter than the gloss-black lunes, as every photo)."""
    D = G.T()
    c, n = G.head_out_face()
    eu, ev = G._facet_frame(c, n)
    tr = D["trim"]
    L, we, ww, gap, he, hm = (float(tr[i]) for i in (3, 4, 5, 6, 7, 8))
    sexp = float(D["trim_lunes"][3])
    r_e = float(D["trim_grooves"][2])
    r = 0.5 * we
    xc = 0.5 * L - r
    out = []
    for sg in (1.0, -1.0):
        parts = [outline_line((0.5 * gap, -0.5 * ww), (xc, -r), 1.2), outline_arc((xc, 0.0), r, -0.5 * math.pi,
                                                                               0.5 * math.pi),
                 outline_line((xc, r), (0.5 * gap, 0.5 * ww), 1.2), outline_line((0.5 * gap, 0.5 * ww),
                                                                                (0.5 * gap, -0.5 * ww), 1.2)]
        P, sh = _closed(parts, {0, 1, 2, 3})

        def top(x, y, he=he, hm=hm):
            ax = max(abs(x), 1e-9)
            t = ax / (0.5 * L)
            z = hm + (he - hm) * t ** sexp
            dz = (he - hm) * sexp * t ** (sexp - 1.0) / (0.5 * L)
            return z, dz * math.copysign(1.0, x), 0.0
        Pm = P * [sg, 1.0]
        if sg < 0:
            Pm, sh = Pm[::-1], sh[::-1]
        out.append(rounded_extrusion(Pm, sh, (c, eu, ev, n), -1.0 - G.trim_slot_dims()[2], top, r_e, "yoke_rocker",
                                     f"trim_lobe_{'r' if sg > 0 else 'l'}", inner_step=1.5))
    return out


def fwd_pieces():
    """The grips' forward-face switches [E] (fwd_switch, L6Y2 detail W1 / W2): stadiums along the grip, standing
    `proud`, the inboard rocker's top dipped `saddle`, top edges R r (rounded extrusions), satin black (grip_black)."""
    out = []
    for g in ("out", "in"):
        c, t, w, nf, row = G.fwd_switch_frame(g)
        _, L, W, proud, r_e, sag = row[:6]
        hl = max(0.5 * (L - W), 0.0)
        rw = 0.5 * W
        parts = [outline_line((-hl, -rw), (hl, -rw), 2.4), outline_arc((hl, 0.0), rw, -0.5 * math.pi, 0.5 * math.pi,
                                                                         max_len=1.6),
                 outline_line((hl, rw), (-hl, rw), 2.4), outline_arc((-hl, 0.0), rw, 0.5 * math.pi, 1.5 * math.pi,
                                                                       max_len=1.6)]
        P, sh = _closed(parts, set())

        def top(x, y, L=L, proud=proud, sag=sag):
            q = min(abs(x) / (0.5 * L), 1.0)
            return proud - sag * (1.0 - q * q), (sag * 2.0 * x / (0.5 * L) ** 2 if q < 1.0 else 0.0), 0.0
        p = rounded_extrusion(P, sh, (c, t, w, nf), -1.0, top, r_e, "grip_black", f"fwd_{g}", inner_step=2.4)
        out.append(p if g == "out" else _mirror_u(p))
    return out


# ============================================================================================ legend ticks
def _slab(P0, P1, z0, z1, frame, width=TICK_W, proud=TICK_PROUD, sink=0.15, seg=2.4):
    """A thin closed slab along the frame-plane segment P0 -> P1 (x, y) whose top lies `proud` above the surface heights
    z0, z1 at its ends (and its bottom `sink` below): its rectangular section swept in stations <= seg mm apart (a long
    stroke's 0.27 x 4 mm side faces would be slivers), the two ends capped; flat faces, split normals at its edges."""
    c, ex, ey, ez = frame
    P0, P1 = np.asarray(P0, float), np.asarray(P1, float)
    L = max(float(np.linalg.norm(P1 - P0)), 1e-9)
    d = (P1 - P0) / L
    s = 0.5 * width * np.array([-d[1], d[0]])
    n = max(1, int(math.ceil(L / seg)))
    t = np.linspace(0.0, 1.0, n + 1)
    C = P0 + t[:, None] * (P1 - P0)
    zc = z0 + t * (z1 - z0)
    nt = _unit(np.r_[-(z1 - z0) / L * d, 1.0])
    # section corners: 0 bottom-left, 1 bottom-right, 2 top-right, 3 top-left (left = -s)
    sec = [(-1.0, -sink), (1.0, -sink), (1.0, proud), (-1.0, proud)]
    side_n = [-nt, _unit(np.r_[s, 0.0]), nt, _unit(np.r_[-s, 0.0])]   # bottom, right, top, left faces
    V, N, F = [], [], []
    for k in range(4):                                  # face k between section corners k and k + 1
        j = (k + 1) % 4
        o = len(V)
        for i in range(n + 1):
            for cc in (k, j):
                sg, h = sec[cc]
                V.append(np.r_[C[i] + sg * s, zc[i] + h])
                N.append(side_n[k])
        for i in range(n):
            a0, b0, a1, b1 = o + 2 * i, o + 2 * i + 1, o + 2 * i + 2, o + 2 * i + 3
            F += [(a0, b0, b1), (a0, b1, a1)]
    for i, nd in ((0, -np.r_[d, 0.0]), (n, np.r_[d, 0.0])):     # end caps
        o = len(V)
        for sg, h in sec:
            V.append(np.r_[C[i] + sg * s, zc[i] + h])
            N.append(nd)
        F += [(o, o + 1, o + 2), (o, o + 2, o + 3)]
    V3, N3 = in_frame(np.array(V), np.array(N), *frame)
    return Piece(V3, np.array(F), N3, "legend_white").oriented()


def legend_pieces():
    """The legends (YOKE_DESIGN legends: words of plain letter BLOCKS, rev N -- no lettering; yoke_geom.legend_blocks):
    TCS on its bezel's dish, AFCS DISC on the boss's aft face, TRIM DN / TRIM UP on the trim face's two lunes, MAP LIGHTS
    on the shield facet round the push button's hex collar; each block a thin slab legend_style[1] proud, legend_grey."""
    D = G.T()
    proud = float(D["legend_style"][1])
    out = []

    def slab(P0, P1, z0, z1, fr, w):
        p_ = _slab(P0, P1, z0, z1, fr, width=w, proud=proud)
        return Piece(p_.V, p_.F, p_.N, "legend_grey").oriented()
    # TCS dish (the bezel's straight dish line from the rolled edge's top to the bore)
    c, nrm = G.tcs_axis()
    bz, rr, dish, _, _, r_in, _ = (float(x) for x in D["tcs_profile"][:7])
    Rb, re = 0.5 * float(D["tcs"][2]), min(rr, bz)
    e1 = np.array([1.0, 0.0, 0.0])
    fr = (c, e1, np.cross(nrm, e1), nrm)

    def zd(r):
        return bz - dish + dish * (r - r_in) / (Rb - re - r_in)
    for P0, P1, w in G.legend_blocks(0):
        out.append(slab(P0, P1, zd(np.linalg.norm(P0)), zd(np.linalg.norm(P1)), fr, w))
    # AFCS boss face (flat)
    c, nrm = G.afcs_axis()
    fr = (c, e1, np.cross(nrm, e1), nrm)
    for P0, P1, w in G.legend_blocks(1):
        out.append(slab(P0, P1, 0.0, 0.0, fr, w))
    # the trim face's lunes (the flat round face outside the slot)
    c, n = G.head_out_face()
    eu, ev = G._facet_frame(c, n)
    fr = (c, eu, ev, n)
    for k in (2, 3):
        for P0, P1, w in G.legend_blocks(k):
            out.append(slab(P0, P1, 0.0, 0.0, fr, w))
    # the shield facet round the hex collar: front-view blocks about the button (co-pilot sense) lifted along a onto the
    # facet plane (as the sheet's button_pieces), then expressed in the facet frame
    ci, ni = G.head_in_face()
    eui, evi = G._facet_frame(ci, ni)
    m = np.array([-1.0, 1.0, 1.0])
    ci, ni, eui, evi = ci * m, ni * m, eui * m, evi * m
    b = D["button"]
    bc = np.array([-float(b[0]), float(b[1])])
    fr = (ci, eui, evi, ni)
    for P0, P1, w in G.legend_blocks(4):
        Q = np.array([bc + P0, bc + P1])
        aa = ci[2] - ((Q[:, 0] - ci[0]) * ni[0] + (Q[:, 1] - ci[1]) * ni[1]) / ni[2]
        Q3 = np.c_[Q, aa] - ci
        q2 = np.c_[Q3 @ eui, Q3 @ evi]
        out.append(slab(q2[0], q2[1], 0.0, 0.0, fr, w))
    return out


def badge_pieces():
    """The badge's raised blank plate (rev N, yoke_geom.badge_plate): its rounded rectangle extruded along a from below
    the insert's face to badge_field[3] above it (the face plane's slope carried by the top), top edge R badge_field[5];
    yoke_silver."""
    hw, h0, h1, proud, rc, rt = G.badge_plate_dims()
    hc, hh = 0.5 * (h0 + h1), 0.5 * (h1 - h0)
    fa_c = float(G.face_a(hc))
    slope = float(G.face_a(hc + 1.0) - G.face_a(hc - 1.0)) / 2.0           # da / dh of the face plane
    xs, ys = hw - rc, hh - rc
    parts = [outline_line((-xs, -hh), (xs, -hh), 4.0), outline_arc((xs, -ys), rc, -0.5 * math.pi, 0.0),
             outline_line((hw, -ys), (hw, ys), 4.0), outline_arc((xs, ys), rc, 0.0, 0.5 * math.pi),
             outline_line((xs, hh), (-xs, hh), 4.0), outline_arc((-xs, ys), rc, 0.5 * math.pi, math.pi),
             outline_line((-hw, ys), (-hw, -ys), 4.0), outline_arc((-xs, -ys), rc, math.pi, 1.5 * math.pi)]
    P, sh = _closed(parts, set())
    z0 = -abs(slope) * hh - 1.0

    def top(x, y):
        return slope * y + proud, 0.0, slope
    frame = (np.array([0.0, hc, fa_c]), np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0]), np.array([0.0, 0.0, 1.0]))
    return [rounded_extrusion(P, sh, frame, z0, top, rt, "yoke_silver", "badge_plate", inner_step=3.0)]


# ============================================================================================ the moulding's materials
def moulding_materials(V, F):
    """Per face of the moulding's frame mesh (yoke_patch.moulding_parts' 'frame'): 'grip_black' (body, grips, heads),
    'black' on the AFCS boss (its satin face under the red cap).  The pads (leather_black inside the groove's inner
    wall) and the trim face (black inside its legend ring) are their own patches."""
    C = V[F].mean(1)
    D = G.T()
    mat = np.full(len(F), "grip_black", dtype=object)
    ca, na = G.afcs_axis()
    Q = C - ca
    z = Q @ na
    r = np.linalg.norm(Q - z[:, None] * na, axis=1)
    mat[(r < 0.5 * float(D["afcs"][4]) + 0.05) & (z > -float(D["afcs_boss"][1]) - 0.2)] = "black"
    return mat


# ============================================================================================ the whole yoke (cached)
MESH_VERSION = "m3"


def _src_key():
    import hashlib
    from pathlib import Path
    h = hashlib.sha1((G.design_key() + G.table_key()).encode())          # the solids + every table value
    for f in ("yoke_mesh.py", "yoke_cover.py", "yoke3d.py", "yoke_tri.py", "yoke_patch.py"):
        h.update((Path(__file__).resolve().parent / f).read_bytes())
    h.update(MESH_VERSION.encode())
    return h.hexdigest()[:16]


_MEM = {}


def yoke_pieces(verbose=False):
    """Every piece of the yoke (co-pilot sense, yoke-local mm): [Piece], disk-cached under the design key + the mesher
    sources (out/tmp/yoke_mesh_cache, git-ignored; a lock keeps two build processes from meshing it twice)."""
    import fcntl
    import pickle
    from pathlib import Path
    key = _src_key()
    if key in _MEM:
        return _MEM[key]
    d = Path(__file__).resolve().parents[1] / "out" / "tmp" / "yoke_mesh_cache"
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"yoke_{key}.pkl"
    with open(d / "lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            if f.exists():
                out = pickle.loads(f.read_bytes())
            else:
                out = _build_pieces(verbose)
                tmp = f.with_suffix(".tmp")
                tmp.write_bytes(pickle.dumps(out))
                tmp.replace(f)
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)
    _MEM[key] = out
    return out


def _grad_mm(fn, P, e=0.002):
    g = np.zeros_like(P)
    for k in range(3):
        d = np.zeros(3)
        d[k] = e
        g[:, k] = (fn(*(P + d).T) - fn(*(P - d).T)) / (2 * e)
    return g


def res_fixed_point(pieces, fn, rounds=4, verbose=False, tag=""):
    """Make the pieces (one surface of the solid fn, yoke-local mm) a fixed point of the build's interior refinement
    (cad.res at RES 2: PN bow / turn criterion -- rev N, judges CR1-04: it split the cover strip's quad diagonals at build,
    +391 vertices on PN cubics, not on the solid): split here exactly as cad.res would, every new vertex that came from
    a smooth (bowed) edge projected onto fn's zero level with its exact normal, until cad.res adds nothing."""
    from cad import res
    from cad.mesh import Mesh
    from cad.refine import refine
    pieces = list(pieces)
    added = 0
    for rnd in range(rounds):
        with res.override(2.0):
            ms = refine([Mesh(p.V * 1e-3, p.F, p.N) for p in pieces], **res._kw("interior"))
        n_new = sum(len(m.V) - len(p.V) for m, p in zip(ms, pieces))
        if n_new == 0:
            break
        added += n_new
        out = []
        for m, p in zip(ms, pieces):
            V, N = m.V * 1e3, _unit(m.N)
            k = len(p.V)
            if len(V) > k:
                Q = V[k:].copy()
                for _ in range(3):
                    f = fn(*Q.T)
                    g = _grad_mm(fn, Q)
                    Q = Q - (f / np.maximum(np.sum(g * g, 1), 1e-9))[:, None] * g
                g = _grad_mm(fn, Q)
                gn = _unit(g)
                ok = (np.linalg.norm(Q - V[k:], axis=1) < 0.02) & (np.sum(gn * N[k:], 1) > math.cos(math.radians(15.0)))
                V[k:][ok] = Q[ok]
                N[k:][ok] = gn[ok]
            out.append(Piece(V, m.F, N, p.mat, p.name))
        pieces = out
    if verbose:
        print(f"  cad.res fixed point{tag}: +{added} vertices in {rnd + 1} rounds", flush=True)
    return pieces


def fold_faces(p):
    """Faces of piece p whose geometric normal opposes one of its corner normals (or is degenerate) -- a fold."""
    fn = np.cross(p.V[p.F[:, 1]] - p.V[p.F[:, 0]], p.V[p.F[:, 2]] - p.V[p.F[:, 0]])
    a = np.linalg.norm(fn, axis=1)
    fn = fn / np.maximum(a, 1e-30)[:, None]
    bad = np.zeros(len(p.F), bool)
    for k in range(3):
        bad |= np.sum(fn * p.N[p.F[:, k]], 1) <= 0.0
    return np.nonzero(bad & (a > 1e-12))[0]


def repair_folds(p, rounds=4):
    """Collapse the folded faces of piece p (fold_faces) away: each one's shortest edge whose moving end is inside the
    piece (its open boundary is shared with the next piece: kept), accepted only where no face round it folds or
    flips.  Returns (piece, folds left)."""
    V, F, N = p.V.copy(), p.F.copy(), p.N.copy()
    for _ in range(rounds):
        q = Piece(V, F, N, p.mat, p.name)
        bad = fold_faces(q)
        if not len(bad):
            break
        e = np.sort(np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), 1)
        ue, cnt = np.unique(e, axis=0, return_counts=True)
        bnd = np.zeros(len(V), bool)
        bnd[ue[cnt == 1].ravel()] = True
        alive = np.ones(len(F), bool)
        moved = set()
        for f in bad:
            if not alive[f]:
                continue
            tri = F[f]
            cand = sorted(((np.linalg.norm(V[tri[i]] - V[tri[(i + 1) % 3]]), tri[i], tri[(i + 1) % 3])
                           for i in range(3)), key=lambda t: t[0])
            for _, a, b in cand:
                for src, dst in ((a, b), (b, a)):
                    if bnd[src] or src in moved or dst in moved:
                        continue
                    ring = np.nonzero(alive & (F == src).any(1))[0]
                    keep = [r for r in ring if dst not in F[r]]
                    F2 = F[keep].copy()
                    F2[F2 == src] = dst
                    fn0 = np.cross(V[F[keep, 1]] - V[F[keep, 0]], V[F[keep, 2]] - V[F[keep, 0]])
                    fn1 = np.cross(V[F2[:, 1]] - V[F2[:, 0]], V[F2[:, 2]] - V[F2[:, 0]])
                    a1 = np.linalg.norm(fn1, axis=1)
                    if (a1 < 1e-12).any() or (np.sum(fn0 * fn1, 1) <= 0).any():
                        continue
                    u1 = fn1 / a1[:, None]
                    if any((np.sum(u1 * N[F2[:, k]], 1) <= 0).any() for k in range(3)):
                        continue
                    gone = [r for r in ring if dst in F[r]]               # the collapsed edge's faces
                    F[keep] = F2
                    alive[gone] = False
                    moved.update((src, dst))
                    break
                else:
                    continue
                break
        F = F[alive]
    u, inv = np.unique(F.ravel(), return_inverse=True)
    q = Piece(V[u], inv.reshape(-1, 3), N[u], p.mat, p.name)
    return q, len(fold_faces(q))


def fix_fold_normals(pieces):
    """Normals of the folded corners (fold_faces) after repair_folds: (1) a vertex whose normal opposes the area-weighted
    mean of the faces round its POSITION (every piece's: the AFCS boss / body seam, where the field's gradient
    turned over) takes that mean, in every piece that shares the position; (2) a corner still opposing its own face (the
    badge grooves' sub-0.1 mm2 end faces, every corner on the piece's seams) gets its own copy of the vertex with the
    face's normal -- a crease at a point, positions unchanged (watertight by position)."""
    pieces = list(pieces)
    V = np.vstack([p.V for p in pieces])
    off = np.cumsum([0] + [len(p.V) for p in pieces])
    key = np.round(V * 1e4).astype(np.int64)
    _, g = np.unique(key, axis=0, return_inverse=True)
    g = g.ravel()
    acc = np.zeros((g.max() + 1, 3))
    for p, o in zip(pieces, off):
        fn = np.cross(p.V[p.F[:, 1]] - p.V[p.F[:, 0]], p.V[p.F[:, 2]] - p.V[p.F[:, 0]])     # area-weighted
        for k in range(3):
            np.add.at(acc, g[o + p.F[:, k]], fn)
    out = []
    for p, o in zip(pieces, off):
        N = p.N.copy()
        bad_v = np.zeros(len(p.V), bool)
        bf = fold_faces(p)
        if len(bf):
            bad_v[np.unique(p.F[bf])] = True
        m = acc[g[o:o + len(p.V)]]
        flip = bad_v & (np.sum(N * m, 1) < 0) & (np.linalg.norm(m, axis=1) > 1e-12)
        N[flip] = _unit(m[flip])
        q = Piece(p.V, p.F, N, p.mat, p.name)
        bf = fold_faces(q)
        if len(bf):
            V2, N2, F2 = list(q.V), list(q.N), q.F.copy()
            for f in bf:
                P = q.V[q.F[f]]
                fn = _unit(np.cross(P[1] - P[0], P[2] - P[0]))
                for k in range(3):
                    if float(np.dot(fn, q.N[q.F[f, k]])) <= 0.0:
                        V2.append(q.V[q.F[f, k]])
                        N2.append(fn)
                        F2[f, k] = len(V2) - 1
            q = Piece(np.array(V2), F2, np.array(N2), p.mat, p.name)
        out.append(q)
    return out


def _build_pieces(verbose=False):
    import time
    from model import yoke_cover as YC
    t0 = time.time()
    if verbose:
        print("  yoke (rev N solids): meshing -- cached afterwards", flush=True)
    out = []
    from model import yoke_patch as YP
    cov = [Piece(V, F, N, m, "cover") for V, F, N, m in YP.collapse_needles(YC.cover_meshes(verbose=verbose),
                                                                              verbose=verbose, tag=" (cover)")]
    out += res_fixed_point(cov, G.cover, verbose=verbose, tag=" (cover)")
    for V, F, N, m in YP.moulding_parts(verbose=verbose, cover=[(p.V, p.F) for p in cov]):
        if m != "frame":
            out.append(Piece(V, F, N, m, "moulding"))
            continue
        mats = moulding_materials(V, F)
        for mt in np.unique(mats):
            Fm = F[mats == mt]
            u, inv = np.unique(Fm.ravel(), return_inverse=True)
            out.append(Piece(V[u], inv.reshape(-1, 3), N[u], str(mt), "moulding"))
    out += tcs_pieces() + afcs_pieces() + button_pieces() + trim_pieces() + fwd_pieces() + badge_pieces()
    out.append(merge(legend_pieces(), "legend_grey", "legends"))
    # one consistent winding per material (the part merges a material's pieces; fit_check 23): pieces that share
    # positions -- the frame and its pockets, the folds at the AFCS boss / badge corners -- traverse every edge once
    # each way, each component keeping its majority winding
    from model import yoke_tri as YT
    for mat in sorted({p.mat for p in out}):
        idx = [i for i, p in enumerate(out) if p.mat == mat]
        for i, Fi in zip(idx, YT.orient_group([(out[i].V, out[i].F) for i in idx], 0.02)):
            out[i] = Piece(out[i].V, Fi, out[i].N, out[i].mat, out[i].name)
    # folds (rev N, judges CR1-05: faces wound against their own corner normals -- pinholes under FrontSide culling, or
    # a dark corner): collapsed inside each piece where they are geometric, else their normals repaired
    n0 = sum(len(fold_faces(p)) for p in out)
    for i, p in enumerate(out):
        if len(fold_faces(p)):
            out[i], _ = repair_folds(p)
    out = fix_fold_normals(out)
    if verbose:
        print(f"  folds: {n0} -> {sum(len(fold_faces(p)) for p in out)}", flush=True)
    if verbose:
        print(f"  yoke: {sum(len(p.F) for p in out)} triangles in {len(out)} pieces, {time.time() - t0:.0f}s", flush=True)
    return out


def place(side, pieces=None):
    """The yoke on `side` (-1 pilot, +1 co-pilot) in model axes (m): [(cad.mesh.Mesh, material)] -- (u, h, a) mm ->
    x = hub x + hub depth + a, y = hub y + side u, z = hub z + h (drawing.yoke_overlay.to_model at the drawn neutral);
    the pilot yoke mirrored (winding flipped)."""
    from cad.mesh import Mesh
    from model import interior as I
    hub = I.yoke_hub(side)
    x_ref = float(hub[0] + I.YOKE["hub_whd"][2])
    out = []
    for p in (pieces if pieces is not None else yoke_pieces()):
        V = np.c_[x_ref + p.V[:, 2] * 1e-3, hub[1] + side * p.V[:, 0] * 1e-3, hub[2] + p.V[:, 1] * 1e-3]
        N = np.c_[p.N[:, 2], side * p.N[:, 0], p.N[:, 1]]
        # (u, h, a) -> (x, y, z) is a cyclic permutation (det +1) for side +1; the pilot's mirror flips the winding
        out.append((Mesh(V, p.F if side > 0 else p.F[:, ::-1], N), p.mat))
    return out
