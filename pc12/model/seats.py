"""
Crew and cabin seats (Stage 3), built from the approved L6 parameter tables in model/interior.py.

Every dimension comes from those tables or from the side / plan / section outlines that sheet L6 draws from them
(interior.crew_seat_profile, crew_base_profile, exec_back_profile; drawing/interior_sheet.py seat_plan_crew,
front_seat_crew, exec_seat_side, front_seat_exec).  The only numbers added here are upholstery detail below the
drawing's resolution: edge radii, crowning, panel seams, strap paths and small hardware.  Those are tagged [E].

  crew_seat(side)       IPECO 3A318-type transport crew seat (CREW_SEAT) at interior.crew_srp(): two floor tracks,
                        two side plates with curved feet, a life-vest box, a black pan, a cushion with split thigh pads
                        and a front U-notch, a contoured back (anthracite shell), a winged headrest on two stalks, two
                        flip-up armrests hinged on the back, a 4-point harness (shoulder straps, two lap-belt halves, a
                        crotch strap through the notch, rotary buckle on the lap), and optional grey sheepskin covers
                        (default on, as on PRO s/n 3001: one sleeve per thigh pad and a back cover, their crowned faces
                        ON the drawn outline, CREW_SEAT sheepskin_t inside it).  Travel (dx, dz), recline, headrest lock,
                        arms up and the finish (CREW_FINISHES: 'pro3001' anthracite shell, 'light' grey) are
                        parameters; crew_hinges() gives the recline / armrest hinge axes of a pose.
  cabin_seat(seat_id)   PRO executive seat (EXEC_SEAT) at the seat_map() station of a SEAT_LAYOUTS seat: an anthracite
                        base shroud on the tracks, an anthracite skirt under a light-grey leather cushion (side
                        panels; the skirt is dark on s/n 3001, P1046406 [M]), a back shell
                        with the V-stitched front (a flush lumbar trapezoid, two seams running from its top corners
                        straight up and out to the bolster edges at 80 % of the height, the side bolsters tapering to
                        the shoulders; the top corners drawn in) and a dark rear insert with a map pocket, a sliding
                        headrest on two posts, ONE aisle-side armrest with a brushed control, a lap belt across the
                        cushion and a shoulder-belt guide.  Recline and headrest slide are parameters.
  cabin_tracks()        the four surface-mounted cabin seat tracks (SEAT_TRACKS).  cabin_seat() does not include them.
  all_seats(layout), build(parts, layout)   convenience: every seat of a layout / one Part per seat.

Every builder returns [(Mesh, material)], one entry per material, in model coordinates (x = STA, y = BL, z = WL).
New material names are in SEAT_MATERIALS (same tuple format as assemble.MATERIALS).  The seats also use the existing
'leather', 'metal', 'metal_dark' and 'paint_white' (and 'leather_dark' for the crew finish 'light').

Construction: upholstery is made of 'pillows'.  A pillow is a closed 2-D outline extruded to a thickness, with every
edge rounded and the face crowned; seams are panel joints.  Metal parts are crisp extrusions, tubes and boxes.
Every mesh is closed and its normals point outward.
"""
from __future__ import annotations

import math

import numpy as np

from cad import res as _res
from cad import sdf2d
from cad.mesh import Mesh, _ear_clip, box, cylinder
from model import interior as I

# ---------------------------------------------------------------------------------------------------- materials
# the values live in model/assemble.MATERIALS (and render/lookdev.py SPEC); SEAT_MATERIALS = the names this builder
# introduced (a view of that table, kept for the preview scripts)
from model.assemble import MATERIALS as _MAT                        # noqa: E402

SEAT_MATERIALS = {k: _MAT[k] for k in ("leather_crew", "leather_crew_shell", "sheepskin", "seat_base_black", "harness",
                                       "seat_shell_dark", "seat_tab_red", "seat_back_shell")}
SHEEPSKIN = True          # [M] PRO s/n 3001 (P1046408 / 10, AOPA): grey sheepskin on the crew cushion, back and arms
# crew seat finishes: 'pro3001' = CREW_SEAT finish [M] (anthracite back shell / headrest back, P1046406); 'light' =
# light-grey back shell (NGX 2281 photos; the existing 'leather_dark' is the MSN 3008 crew-seat grey read through the
# side window, photo 0517)
CREW_FINISHES = {"pro3001": dict(shell="leather_crew_shell", upholstery="leather_crew"),
                 "light": dict(shell="leather_dark", upholstery="leather_crew")}
CREW_FINISH = "pro3001"

M_CREW, M_SHELL, M_SHEEP, M_BASE, M_HARN = "leather_crew", "leather_crew_shell", "sheepskin", "seat_base_black", \
    "harness"
M_CAB, M_CAB_DARK, M_TAB = "leather", "seat_shell_dark", "seat_tab_red"
M_CAB_SHELL = "seat_back_shell"         # mid-grey rear shell of the executive back (cab_pro_aero25_0405 [M], review r1)
M_METAL, M_RAIL, M_WHITE, M_BLACK = "metal", "metal_dark", "paint_white", "seat_base_black"

# sheepskin pads [E, review r1 F3: the fleece is the PRO crew seat's signature, thick and rolled over the edges]:
# pad thickness at its edge, crown on top of it (seat pad: the two thigh domes; back), edge roll radii top / bottom,
# lumpiness (tufts: a coarse geometric wave + the fine fleece bump of the render material, review r2 F4), run-on wrapped
# round the cushion front and over the back top.  The crowned outer face is the DRAWN outline (CREW_SEAT sheepskin_t
# inside cushion_t and the back's front offset, review r2 M1): the leather cushion / back front lie sheepskin_t inside
# it, the pad's bottom sinks into the leather by whatever the pad's loft exceeds sheepskin_t.
SK_T, SK_CROWN_SEAT, SK_CROWN_BACK = 0.034, 0.016, 0.012
SK_ROLL, SK_ROLL_B, SK_FLUFF, SK_LUMP = 0.017, 0.012, 0.0022, 0.0030
SK_LUMP_K = (48.0, 71.0, 105.0, 150.0)          # tuft waves (rad/m): 4-13 cm lumps, visible at the panel camera
SK_WRAP_SEAT, SK_WRAP_BACK = 0.012, 0.050     # run-on past the cushion front / the back top: ~100 deg of wrap
SK_SPLIT = 0.010                               # gap between the two thigh-pad sleeves along the seat CL
SK_FRONT = 0.022                               # the leather cushion's front sits this far behind the drawn front
SK_TOP = 0.020                                 # the back shell's top sits this far below the drawn top (fleece over it)


# =====================================================================================================================
# 2-D outline helpers
# =====================================================================================================================
def _area(P):
    return 0.5 * float(np.sum(P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1]))


def _ccw(P):
    P = np.asarray(P, float)
    return P if _area(P) > 0 else P[::-1].copy()


def _dedup(P, tol=1e-7):
    P = np.asarray(P, float)
    keep = np.linalg.norm(P - np.roll(P, 1, 0), axis=1) > tol
    return P[keep]


def _subdivide(P, max_len):
    out = []
    n = len(P)
    for i in range(n):
        a, b = P[i], P[(i + 1) % n]
        k = max(1, int(math.ceil(np.linalg.norm(b - a) / max_len)))
        out.extend(a + (b - a) * t for t in np.arange(k) / k)
    return np.array(out)


def _arc_k():
    """Outline-arc refinement at the model's tessellation quality (cad.res.factor): 1 at PC12_RES=1, 1.5 at 2 -- the
    corner arcs of the seat / yoke outlines every 15 deg instead of 22.5 (review r1 RES1-03: the polygonal headrest)."""
    f = _res.factor()
    return 1.0 if f <= 1.0 else 0.75 * f


def _sk_h(h):
    """Grid spacing of a sheepskin pad's top at the model's tessellation quality: h at PC12_RES=1, h / RES above -- the
    pads wrap round the shell's edges (_wrap) and at h the wrap took ~60 deg a grid step: a polygonal headrest
    silhouette (review r1 RES1-03); at h / 2 the refinement smooths the rest."""
    f = _res.factor()
    return h if f <= 1.0 else h / f


def _rounds(n):
    """Rim segments of a pillow's 90 deg roundings at the model's tessellation quality: n at PC12_RES=1, RES x n above
    (3 -> 6: 15 deg a segment; review r1 RES1-01 / 03: at 30 / 45 deg a segment the rims' faces leaned 15-22 deg off
    their vertex normals -- too coarse for the refinement to trust -- and the cushions read faceted)."""
    f = _res.factor()
    return int(n) if f <= 1.0 else int(round(n * f))


def fillet(P, r, seg_deg=22.5, max_len=None):
    """Closed polygon P with each corner rounded by radius r (scalar or per vertex, clipped to half the adjacent
    edges; arcs every seg_deg, finer at PC12_RES > 1: _arc_k).  With max_len, straight runs are split so that no
    segment is longer."""
    seg_deg = seg_deg / _arc_k()
    P = _dedup(P)
    n = len(P)
    rr = np.broadcast_to(np.asarray(r, float), (n,))
    out = []
    for i in range(n):
        a, b, c = P[i - 1], P[i], P[(i + 1) % n]
        d0, d1 = b - a, c - b
        L0, L1 = float(np.linalg.norm(d0)), float(np.linalg.norm(d1))
        d0, d1 = d0 / L0, d1 / L1
        turn = math.acos(float(np.clip(np.dot(d0, d1), -1.0, 1.0)))
        if turn < 1e-4 or rr[i] <= 0:
            out.append(b)
            continue
        t = min(rr[i] * math.tan(0.5 * turn), 0.5 * L0, 0.5 * L1)
        rad = t / math.tan(0.5 * turn)
        sg = 1.0 if d0[0] * d1[1] - d0[1] * d1[0] > 0 else -1.0
        p0 = b - d0 * t
        C = p0 + rad * sg * np.array([-d0[1], d0[0]])
        a0 = math.atan2(p0[1] - C[1], p0[0] - C[0])
        k = max(2, int(math.ceil(math.degrees(turn) / seg_deg)) + 1)
        ang = a0 + sg * turn * np.linspace(0.0, 1.0, k)
        out.extend(np.c_[C[0] + rad * np.cos(ang), C[1] + rad * np.sin(ang)])
    Q = _dedup(np.array(out), 2e-5)          # adjacent arcs clipped to the same edge midpoint: one point (a pair
    return _subdivide(Q, max_len) if max_len else Q      # 1e-6 apart merged in the quantised GLB: non-manifold rims)


def rrect(u0, v0, u1, v1, r, max_len=None):
    """Rounded rectangle outline (CCW)."""
    return fillet([(u0, v0), (u1, v0), (u1, v1), (u0, v1)], r, max_len=max_len)


def _normals2(Q):
    """Outward unit normals of a CCW closed outline (central differences)."""
    T = np.roll(Q, -1, 0) - np.roll(Q, 1, 0)
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-12)
    return np.c_[T[:, 1], -T[:, 0]]


def offset_outline(P, d):
    """Outline moved outward by d (small d, smooth outline)."""
    Q = _ccw(P)
    return Q + d * _normals2(Q)


def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, float) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def dome(h, R):
    """Crown function: a puff of height h reached R inside the face's edge."""
    return lambda a, b, d: h * smoothstep(0.0, R, d)


def _wrap(V, axis, a0, R, c0):
    """Bend a flat pad (pillow coordinates: V[:, axis] along the pad, c = V[:, 2] up from its bottom) round the edge
    it lies on: a cylinder of radius R, axis at V[:, axis] = a0 and c = c0 - R (c0 = the edge surface's top in the
    pad's frame).  Beyond a0 the arc length (a - a0) / R becomes the angle; the pile keeps its thickness."""
    V = V.copy()
    a, c = V[:, axis], V[:, 2]
    s_ = a - a0
    on = s_ > 0
    phi = s_[on] / R
    cax = c0 - R
    rr = c[on] - cax
    V[on, axis] = a0 + rr * np.sin(phi)
    V[on, 2] = cax + rr * np.cos(phi)
    return V


def fleece(amp, seed=0, k=(26.0, 43.0, 71.0), h_judged=None):
    """Lumpiness for sheepskin faces: a sum of random plane waves (amplitude amp, m; wave numbers k, rad/m).
    h_judged: the pad's grid spacing at PC12_RES=1 -- above it (finer grids, _sk_h) each wave is scaled by
    min(1, (k_c / k)^2), k_c = pi / (2 h_judged): the judged grid could not carry the fine waves (the 37-66 mm fleece
    ripple was sampled every 16-21 mm and smoothed out), the finer one drew them as a twisted rope along the pads' edges
    (review r2 RES2-04); the approved look keeps its band."""
    rng = np.random.default_rng(seed)
    waves = [(rng.normal(size=2), rng.uniform(0, 2 * np.pi), kk) for kk in k]
    kc = np.pi / (2.0 * h_judged) if (h_judged and _res.factor() > 1.0) else None
    gain = [1.0 if kc is None else min(1.0, (kc / kk) ** 2) for _, _, kk in waves]

    def f(a, b):
        out = np.zeros_like(np.asarray(a, float))
        for (dvec, ph, kk), g in zip(waves, gain):
            dvec = dvec / np.linalg.norm(dvec)
            out += g * np.sin(kk * (dvec[0] * a + dvec[1] * b) + ph)
        return amp * out / len(waves)
    return f


_STATS = dict(cap_fallback=0, fold=0)


# =====================================================================================================================
# geometry pieces: vertices, faces, per-face piece id; turned into Meshes at the end (normals after every deformation)
# =====================================================================================================================
class Geo:
    """V (n, 3) seat-local points, F (m, 3) faces, pid (m,) piece id per face, mats {pid: material}; smooth=False
    keeps the vertex normals from the faces of a split-vertex mesh (crisp metal)."""

    def __init__(self, V, F, pid, mats):
        self.V = np.asarray(V, float)
        self.F = np.asarray(F, np.int64)
        self.pid = np.asarray(pid, np.int64)
        self.mats = mats if isinstance(mats, dict) else {int(p): mats for p in np.unique(self.pid)}

    def map(self, fn):
        return Geo(fn(self.V), self.F, self.pid, self.mats)

    def rot(self, axis_pt, deg, plane=(0, 2)):
        """Rotate counter-clockwise by deg in the (plane[0], plane[1]) coordinate plane about axis_pt."""
        if not deg:
            return self
        a = math.radians(deg)
        i, j = plane
        V = self.V.copy()
        p, q = V[:, i] - axis_pt[0], V[:, j] - axis_pt[1]
        V[:, i] = axis_pt[0] + p * math.cos(a) - q * math.sin(a)
        V[:, j] = axis_pt[1] + p * math.sin(a) + q * math.cos(a)
        return Geo(V, self.F, self.pid, self.mats)

    def meshes(self):
        """[(Mesh, material)] with outward orientation (signed volume) and normals from the final positions."""
        V, F, pid = self.V, self.F, self.pid
        v0, v1, v2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
        ok = np.linalg.norm(np.cross(v1 - v0, v2 - v0), axis=1) > 1e-14
        F, pid = F[ok], pid[ok]
        vol = float(np.einsum("ij,ij->i", V[F[:, 0]], np.cross(V[F[:, 1]], V[F[:, 2]])).sum())
        if vol < 0:
            F = F[:, ::-1]
        out = []
        for p, mat in self.mats.items():
            sel = pid == p
            if sel.any():                  # normals per piece: a cap's flat shading is not bent by the rim's
                out.append((Mesh(V, F[sel]).compact(), mat))
        return out


def _cap(B, h, seams=None):
    """Triangulation of a closed CCW outline B (k, 2): with h, interior grid points (spacing h, >= 0.8 h inside) and
    a Delaunay triangulation (a ladder across thin strips when none fit), so a curved mapping or a crown shapes the
    face smoothly; otherwise ear clipping.  Repeated points (a corner arc collapsed by the inset) are merged.  seams:
    closed outlines inside the face along which the triangulation must run (a recess / inlay edge): each adds two
    dense rings 0.5 mm either side and clears the grid round it.
    Returns (triangles CCW: indices < k = boundary points, k.. = interior points G), G.
    A boundary edge lost by the Delaunay triangulation (a sub-millimetre loop where a finely sampled corner arc folds
    in the inset) is retried once with boundary points closer than MERGE_TOL to the previous one merged (the cap then
    skips them; the gap to the rim is that small), before the plain cap."""
    r = _cap_try(B, h, seams, 1e-7)
    if r is None and h:
        r = _cap_try(B, h, seams, min(MERGE_TOL, 0.1 * h))
    if r is None:
        _STATS["cap_fallback"] += 1                                    # a boundary edge was lost: plain cap
        keep = np.linalg.norm(B - np.roll(B, 1, 0), axis=1) > 1e-7
        return np.nonzero(keep)[0][_ear_clip(B[keep])], np.zeros((0, 2))
    return r


MERGE_TOL = 1.0e-3


def _merge_keep(B, tol):
    """Boundary points kept for a cap: each one further than tol from the previous kept point (and from the first)."""
    keep = np.zeros(len(B), bool)
    last = None
    for i, p in enumerate(B):
        if last is None or np.linalg.norm(p - last) > tol:
            keep[i] = True
            last = p
    while tol > 1e-7 and keep.sum() > 3:
        j = np.nonzero(keep)[0][-1]
        if np.linalg.norm(B[j] - B[np.nonzero(keep)[0][0]]) > tol:
            break
        keep[j] = False
    return keep


def _cap_try(B, h, seams, tol):
    n = len(B)
    keep = np.linalg.norm(B - np.roll(B, 1, 0), axis=1) > 1e-7 if tol <= 1e-7 else _merge_keep(B, tol)
    idx = np.nonzero(keep)[0]
    Bu = B[keep]
    nu = len(Bu)
    G = np.zeros((0, 2))
    if h:
        lo, hi = Bu.min(0), Bu.max(0)
        gx = np.arange(lo[0] + 0.5 * h, hi[0], h)
        gy = np.arange(lo[1] + 0.5 * h, hi[1], h)
        if len(gx) and len(gy):
            GX, GY = np.meshgrid(gx, gy, indexing="ij")
            G = np.c_[GX.ravel(), GY.ravel()]
            G = G[-sdf2d.polygon(G[:, 0], G[:, 1], Bu) > 0.8 * h]
        for S_ in (seams or ()):
            S_ = _ccw(np.asarray(S_, float))
            G = G[np.abs(sdf2d.polygon(G[:, 0], G[:, 1], S_)) > 0.55 * h]
            ring = _subdivide(S_, 0.0012)
            Ns = _normals2(ring)
            G = np.vstack([G, ring + 0.0005 * Ns, ring - 0.0005 * Ns])
        from scipy.spatial import Delaunay
        P2 = np.vstack([Bu, G])
        tri = Delaunay(P2).simplices
        cen = P2[tri].mean(1)
        tri = tri[sdf2d.polygon(cen[:, 0], cen[:, 1], Bu) < 0]
        e = P2[tri]
        d1, d2 = e[:, 1] - e[:, 0], e[:, 2] - e[:, 0]
        cr = d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]
        tri[cr < 0] = tri[cr < 0][:, ::-1]
        edges = {tuple(sorted(x)) for tt in tri for x in ((tt[0], tt[1]), (tt[1], tt[2]), (tt[2], tt[0]))}
        if all(tuple(sorted((k, (k + 1) % nu))) in edges for k in range(nu)):
            return np.where(tri < nu, idx[np.minimum(tri, nu - 1)], tri - nu + n), G
        return None
    return idx[_ear_clip(Bu)], np.zeros((0, 2))


def pillow(outline, t, r, rb=None, h=None, crown=None, fluff=None, n_round=3, max_len=None, h_bottom=None,
           seams=None):
    """Upholstered pad: a closed 2-D outline (a, b) extruded along c from 0 to t, every edge rounded (radius r at the
    top c = t, rb at the bottom).  With h, the top face is tessellated at spacing h (grid + Delaunay) so that
    crown(a, b, d) can puff it, where d = depth inside the top face's edge in m, and a curved mapping bends it
    smoothly; h_bottom does the same for the bottom face.  fluff(a, b) adds lumpiness.  Returns a Geo in (a, b, c)
    with piece ids 0 top face, 1 rounded rim, 2 bottom face.  Outline corner radii must be >= r.  n_round: segments
    per 90 deg rounding at PC12_RES=1 (more above: _rounds)."""
    n_round = _rounds(n_round)
    Q = _ccw(outline)
    hs = [x for x in (max_len, h and 1.5 * h, h_bottom and 1.5 * h_bottom) if x]
    if hs:
        Q = _subdivide(Q, min(hs))
    n = len(Q)
    N = _normals2(Q)
    rb = r if rb is None else rb
    if r + rb > t:
        k = t / (r + rb)
        r, rb = r * k, rb * k
    rows = [(Q - rb * N + rb * math.cos(ph) * N, rb + rb * math.sin(ph))
            for ph in np.linspace(-0.5 * np.pi, 0.0, n_round + 1)]
    top = [(Q - r * N + r * math.cos(ph) * N, t - r + r * math.sin(ph)) for ph in np.linspace(0.0, 0.5 * np.pi,
                                                                                           n_round + 1)]
    if abs(top[0][1] - rows[-1][1]) < 1e-9:
        top = top[1:]
    rows += top
    eq = np.roll(Q, -1, 0) - Q
    for P2, _ in (rows[0], rows[-1]):                            # an inset that folds back: corner radius < r
        eb = np.roll(P2, -1, 0) - P2
        lb = np.linalg.norm(eb, axis=1)
        cosang = np.einsum("ij,ij->i", eq, eb) / np.maximum(np.linalg.norm(eq, axis=1) * lb, 1e-15)
        if np.any((lb > 1e-5) & (cosang < -0.5)):
            _STATS["fold"] += 1
    if fluff is not None:                                        # fleece: a wavy outline too
        w = 1.6 * fluff(Q[:, 0], Q[:, 1])
        rows = [(P2 + w[:, None] * N, c) for P2, c in rows]
    R = len(rows)
    V = [np.c_[P2, np.full(n, c)] for P2, c in rows]
    i = np.arange(n)
    j = (i + 1) % n
    Fr = []
    for k in range(R - 1):
        a, b, c, d = k * n + i, k * n + j, (k + 1) * n + j, (k + 1) * n + i
        Fr += [np.c_[a, b, c], np.c_[a, c, d]]
    Fr = np.vstack(Fr)
    B = rows[-1][0]
    base = (R - 1) * n
    tri_t, Gt = _cap(B, h, seams)
    tri_b, Gb = _cap(rows[0][0], h_bottom)
    it0 = R * n                                                  # interior points: top, then bottom
    ib0 = it0 + len(Gt)
    Ft = np.where(tri_t < n, tri_t + base, tri_t - n + it0)
    Fb = np.where(tri_b < n, tri_b, tri_b - n + ib0)[:, ::-1]
    V = np.vstack(V + [np.c_[Gt, np.full(len(Gt), float(rows[-1][1]))], np.c_[Gb, np.zeros(len(Gb))]])
    # crown / fleece on the top face
    top_ids = np.r_[base + np.arange(n), it0 + np.arange(len(Gt))]
    A = V[top_ids, :2]
    if crown is not None:                                        # (a corner arc collapsed by the inset repeats
        d = -sdf2d.polygon(A[:, 0], A[:, 1], _dedup(B, 1e-9))    # points: zero-length edges would give NaN)
        V[top_ids, 2] += crown(A[:, 0], A[:, 1], np.maximum(d, 0.0))
    if fluff is not None:
        V[top_ids, 2] += fluff(A[:, 0], A[:, 1])
    F = np.vstack([Ft, Fr, Fb])
    pid = np.r_[np.zeros(len(Ft)), np.ones(len(Fr)), np.full(len(Fb), 2)]
    return Geo(V, F, pid, {0: None, 1: None, 2: None})


def _mats(g, top, rim=None, bottom=None):
    g.mats = {0: top, 1: rim or top, 2: bottom or rim or top}
    return g


def slab(profile_uv, s0, s1, r, mat, rb=None, n_round=3, max_len=None, width=None, post=None, h=None):
    """A side profile (u, v) extruded across s0..s1 with rounded edges: the seat-local Geo (u, s, v).
    width(u, v) -> scale: optional lateral taper about the slab centre; post(u, v, e) -> (du, dv): optional
    displacement, e = lateral position relative to the half-width (-1 .. 1); h: side faces tessellated (a taper
    bends them)."""
    t = s1 - s0
    g = pillow(profile_uv, t, r, rb, n_round=n_round, max_len=max_len, h=h, h_bottom=h)
    sm = 0.5 * (s0 + s1)

    def fn(V):
        u, v, c = V[:, 0], V[:, 1], V[:, 2]
        k = 1.0 if width is None else width(u, v)
        e = (c - 0.5 * t) / (0.5 * t)
        if post is not None:
            du, dv = post(u, v, e)
            u, v = u + du, v + dv
        return np.c_[u, sm + (c - 0.5 * t) * k, v]
    return _mats(g.map(fn), mat)


def rear_round(nb, depth, n0=-0.01, n1=-0.05):
    """post() for slab: the back's rear face rounded across -- behind the back line (n < n0 .. n1 along nb) the
    sides come forward by depth x e^2, so the centreline silhouette stays on the drawn profile."""
    def f(u, v, e):
        n = u * nb[0] + v * nb[1]
        k = depth * e * e * smoothstep(n0, n1, n)
        return k * nb[0], k * nb[1]
    return f


def plate(poly_uv, s0, s1, mat, smooth_deg=35.0):
    """Crisp extrusion of a polygon (u, v) across s0..s1 (metal plates): flat faces, sharp corners, smooth walls
    where the outline turns by less than smooth_deg (arcs)."""
    Q = _ccw(_dedup(poly_uv))
    n = len(Q)
    tri = _ear_clip(Q)
    V = [np.c_[Q[:, 0], np.full(n, s0), Q[:, 1]], np.c_[Q[:, 0], np.full(n, s1), Q[:, 1]]]
    F = [tri, tri[:, ::-1] + n]
    d_in = Q - np.roll(Q, 1, 0)
    d_out = np.roll(Q, -1, 0) - Q
    cosang = np.einsum("ij,ij->i", d_in, d_out) / np.maximum(
        np.linalg.norm(d_in, axis=1) * np.linalg.norm(d_out, axis=1), 1e-12)
    crease = cosang < math.cos(math.radians(smooth_deg))
    # wall vertices: one copy per vertex (two at creases); edge k uses copy 'out' of k and 'in' of k+1
    idx_in, idx_out, W = np.zeros(n, int), np.zeros(n, int), []
    base = 2 * n
    for k in range(n):
        idx_in[k] = base + len(W) // 2
        W += [(Q[k, 0], s0, Q[k, 1]), (Q[k, 0], s1, Q[k, 1])]
        if crease[k]:
            idx_out[k] = base + len(W) // 2
            W += [(Q[k, 0], s0, Q[k, 1]), (Q[k, 0], s1, Q[k, 1])]
        else:
            idx_out[k] = idx_in[k]
    # W pairs: vertex 2m = bottom (s0), 2m+1 = top (s1); remap pair index -> vertex ids
    Wv = np.array(W)
    pair = lambda p, top: base + 2 * (p - base) + top           # noqa: E731
    Fw = []
    for k in range(n):                          # wound outward like the caps (review r1 C6: the walls were inward)
        a, b = idx_out[k], idx_in[(k + 1) % n]
        Fw += [(pair(a, 0), pair(b, 1), pair(b, 0)), (pair(a, 0), pair(a, 1), pair(b, 1))]
    Vall = np.vstack(V + [Wv])
    Fall = np.vstack(F + [np.array(Fw)])
    return Geo(Vall, Fall, np.zeros(len(Fall)), {0: mat})


def rbox(c, size, r, mat, R=None):
    """Rounded box (pillow of a rounded rectangle), centre c (u, s, v), size (du, ds, dv), optional 3x3 rotation."""
    du, ds, dv = size
    g = pillow(fillet([(-0.5 * du, -0.5 * dv), (0.5 * du, -0.5 * dv), (0.5 * du, 0.5 * dv), (-0.5 * du, 0.5 * dv)],
                      min(r, 0.49 * min(du, dv)), seg_deg=30.0), ds, min(r, 0.49 * min(du, dv, ds)), n_round=2)
    g = g.map(lambda V: np.c_[V[:, 0], V[:, 2] - 0.5 * ds, V[:, 1]])
    if R is not None:
        g = g.map(lambda V: V @ np.asarray(R).T)
    g = g.map(lambda V: V + np.asarray(c, float))
    return _mats(g, mat)


def cbox(c, size, mat, R=None):
    """Crisp box (24 vertices, flat faces) in seat-local coordinates."""
    m = box(c, size, R=R)
    return Geo(m.V, m.F, np.zeros(len(m.F)), {0: mat})


def tube(p0, p1, r, mat, n=10):
    m = cylinder(p0, p1, r, n=n)
    m.F = m.F.copy()
    return Geo(m.V, m.F, np.zeros(len(m.F)), {0: mat})


def _unit3(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def _catmull(P, n=24):
    """Centripetal-free uniform Catmull-Rom through the control points P (k, d) -> (n, d)."""
    P = np.asarray(P, float)
    k = len(P)
    if k < 3:
        return np.linspace(P[0], P[-1], n)
    Pe = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    s = np.linspace(0.0, k - 1, n)
    out = []
    for x in s:
        i = min(int(x), k - 2)
        t = x - i
        p0, p1, p2, p3 = Pe[i], Pe[i + 1], Pe[i + 2], Pe[i + 3]
        out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                          + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    return np.array(out)


def ribbon(ctrl, up, width, mat, th=0.0035, n=20, rounded=False):
    """Webbing strap through the control points ctrl (k, 3) lying flat with its face normal along up (k, 3) (the
    surface under it): a thin closed box section swept along a Catmull-Rom path, crisp edges; rounded: the long edges
    rounded (a six-sided section, each side's two chamfers smooth-shaded: review r3 K1).  n=None: ctrl / up are
    already dense, taken as they are."""
    if n is None:
        P, U = np.asarray(ctrl, float).copy(), np.asarray(up, float).copy()
        n = len(P)
    else:
        P = _catmull(ctrl, n)
        U = _catmull(up, n)
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    # the up hint made normal to the path, its sign kept continuous along it (review r2 N1: where a hint ran nearly
    # along the path the frame flipped by 180 deg and the strap folded, its normals against the winding)
    U = U - T * np.einsum("ij,ij->i", U, T)[:, None]
    for i in range(n):
        if np.linalg.norm(U[i]) < 1e-6:
            U[i] = U[i - 1] if i else np.cross(T[i], [0.0, 1.0, 0.0])
        U[i] /= np.linalg.norm(U[i])
        if i and np.dot(U[i], U[i - 1]) < 0.0:
            U[i] = -U[i]
    W = np.cross(T, U)
    W /= np.maximum(np.linalg.norm(W, axis=1, keepdims=True), 1e-12)
    U = np.cross(W, T)
    hw, ht = 0.5 * width, 0.5 * th
    if rounded:
        e = min(0.9 * ht, 0.2 * hw)
        C = [P + W * (hw - e) + U * ht, P + W * hw, P + W * (hw - e) - U * ht, P - W * (hw - e) - U * ht, P - W * hw,
             P - W * (hw - e) + U * ht]
        V, F = [], []
        ii = np.arange(n - 1)
        for rows in ((C[5], C[0]), (C[0], C[1], C[2]), (C[2], C[3]), (C[3], C[4], C[5])):
            o = sum(len(x) for x in V)
            V.append(np.vstack(rows))
            for r_ in range(len(rows) - 1):
                a_, b_ = o + r_ * n, o + (r_ + 1) * n
                F += [np.c_[a_ + ii, a_ + ii + 1, b_ + ii + 1], np.c_[a_ + ii, b_ + ii + 1, b_ + ii]]
        for e_ in (0, n - 1):
            o = sum(len(x) for x in V)
            V.append(np.array([C[k][e_] for k in range(6)]))
            cap = np.array([[o, o + 1, o + 2], [o, o + 2, o + 3], [o, o + 3, o + 4], [o, o + 4, o + 5]])
            F.append(cap if e_ == 0 else cap[:, ::-1])
        Vv, Ff = np.vstack(V), np.vstack(F)
        return Geo(Vv, Ff, np.zeros(len(Ff)), {0: mat})
    C = [P + W * hw + U * ht, P - W * hw + U * ht, P - W * hw - U * ht, P + W * hw - U * ht]
    V, F = [], []
    for k in range(4):
        A, B = C[k], C[(k + 1) % 4]
        o = len(V) * 0 + sum(len(x) for x in V)
        V.append(np.vstack([A, B]))
        ii = np.arange(n - 1)
        F += [np.c_[o + ii, o + ii + 1, o + n + ii + 1], np.c_[o + ii, o + n + ii + 1, o + n + ii]]
    for e in (0, n - 1):                        # end caps, each wound outward (review r1 C6)
        o = sum(len(x) for x in V)
        V.append(np.array([C[k][e] for k in range(4)]))
        cap = np.array([[o, o + 1, o + 2], [o, o + 2, o + 3]])
        F.append(cap if e == 0 else cap[:, ::-1])
    Vv = np.vstack(V)
    Ff = np.vstack(F)
    g = Geo(Vv, Ff, np.zeros(len(Ff)), {0: mat})
    return g


def to_meshes(geos):
    """[(Mesh, material)] with one merged Mesh per material (each Geo oriented and shaded separately)."""
    by = {}
    for g in geos:
        if g is None:
            continue
        for m, mat in g.meshes():
            by.setdefault(mat, []).append(m)
    return [(Mesh.merge(ms), mat) for mat, ms in by.items()]


# =====================================================================================================================
# crew seat: IPECO 3A318 type (CREW_SEAT)
# =====================================================================================================================
def _crew_front(b):
    """Front face of the crew back ahead of the back line at along-back position b: the profile's 0.02 plus the
    lumbar bulge (interior.crew_seat_profile)."""
    return 0.02 + 0.015 * np.exp(-((np.asarray(b, float) - 0.22) / 0.10) ** 2)


def _crew_back_hw(b, extra=0.0):
    """Half-width of the crew back at along-back position b (front view, sheet L6 section A-A: back_w lumbar up to
    0.35 above the SRP, tapering to the top width, top corners rounded r 0.06)."""
    c = I.CREW_SEAT
    L = float(c["back_len"])
    bw0, bw1 = 0.5 * c["back_w"][0], 0.5 * c["back_w"][1]
    cb = math.cos(math.radians(c["back_deg"]))
    rr = 0.06
    b = np.asarray(b, float)
    hw = np.interp(b, [0.0, 0.35 / cb, L - rr], [bw1, bw1, bw0])
    corner = (bw0 - rr) + np.sqrt(np.maximum(rr * rr - (b - (L - rr)) ** 2, 0.0))
    return np.where(b > L - rr, corner, hw) + extra


def _back_frame(deg):
    b = math.radians(deg)
    return np.array([-math.sin(b), math.cos(b)]), np.array([math.cos(b), math.sin(b)])   # db, nb in (u, v)


def _back_map(db, nb, o=(0.0, 0.0), front=None):
    """Map back-plane pillows (a = lateral s, b = along the back line, c = along the back normal, above front(b))
    into seat-local (u, s, v)."""
    o = np.asarray(o, float)

    def fn(V):
        a, b, c = V[:, 0], V[:, 1], V[:, 2]
        cc = c + (front(b) if front is not None else 0.0)
        return np.c_[o[0] + b * db[0] + cc * nb[0], a, o[1] + b * db[1] + cc * nb[1]]
    return fn


def _outline_from_hw(b0, b1, hw_fn, r, nb=10, a_shift=0.0):
    """Outline (a, b) of a symmetric panel between b0 and b1 whose half-width is hw_fn(b), corners filleted r (nb side
    samples at PC12_RES=1, RES x as many above)."""
    nb = _rounds(nb)
    m = 2.2 * r                                                  # keep the side samples clear of the corners
    bs = np.r_[b0, np.linspace(b0 + m, b1 - m, max(nb - 2, 1)), b1] if b1 - b0 > 3 * m else np.array([b0, b1])
    hw = hw_fn(bs)
    P = np.vstack([np.c_[hw + a_shift, bs], np.c_[(-hw + a_shift)[::-1], bs[::-1]]])
    return fillet(P, r)


def _upper_hull(P):
    """Upper convex hull (monotone chain) of 2-D points P, left to right."""
    P = P[np.lexsort((P[:, 1], P[:, 0]))]
    up = []
    for p in P:
        while len(up) >= 2 and ((up[-1][0] - up[-2][0]) * (p[1] - up[-2][1])
                                - (up[-1][1] - up[-2][1]) * (p[0] - up[-2][0])) >= 0:
            up.pop()
        up.append(p)
    return np.array(up)


def _strap_frame(P, U):
    """Path tangents T and the up hints U made normal to them (sign kept continuous), as ribbon() does."""
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    U = U - T * np.einsum("ij,ij->i", U, T)[:, None]
    for i in range(len(P)):
        if np.linalg.norm(U[i]) < 1e-6:
            U[i] = U[i - 1] if i else np.cross(T[i], [0.0, 1.0, 0.0])
        U[i] /= np.linalg.norm(U[i])
        if i and np.dot(U[i], U[i - 1]) < 0.0:
            U[i] = -U[i]
    W = np.cross(T, U)
    W /= np.maximum(np.linalg.norm(W, axis=1, keepdims=True), 1e-12)
    return T, np.cross(W, T), W


def strap_clear(P, U, obst, width, th, clear=0.0015, depth=0.04, iters=5):
    """Lift a dense strap path (P, up U) along its up vectors until its underside is `clear` above the obstacle Geos
    (review r3 K1): from five points across the underside a ray is cast up the strap normal from `depth` below; the
    highest obstacle hit sets the lift; lifts are dilated by one sample (no kinks) and the pass repeated.  Returns the
    lifted (P, U)."""
    T_ = np.vstack([g.V[g.F] for g in obst])
    P, U = np.asarray(P, float).copy(), np.asarray(U, float).copy()
    lo, hi = P.min(0) - depth - width, P.max(0) + depth + width
    T_ = T_[((T_.max(1) > lo) & (T_.min(1) < hi)).all(1)]
    if not len(T_):
        return P, U
    e1, e2 = T_[:, 1] - T_[:, 0], T_[:, 2] - T_[:, 0]
    ws = np.linspace(-0.5, 0.5, 5) * width
    for _ in range(iters):
        _, Un, W = _strap_frame(P, U)
        # rays at the samples and at the segment midpoints (a lump between two samples must not poke through)
        Pm = np.vstack([P, 0.5 * (P[1:] + P[:-1])])
        Um = np.vstack([Un, 0.5 * (Un[1:] + Un[:-1])])
        Wm = np.vstack([W, 0.5 * (W[1:] + W[:-1])])
        O = (Pm[:, None, :] + ws[None, :, None] * Wm[:, None, :] - (0.5 * th + depth) * Um[:, None, :]).reshape(-1, 3)
        D = np.repeat(Um, len(ws), axis=0)
        tmax = np.full(len(O), -np.inf)
        for i0 in range(0, len(O), 64):
            o, d = O[i0:i0 + 64, None, :], D[i0:i0 + 64, None, :]
            pv = np.cross(d, e2[None])
            det = (e1[None] * pv).sum(-1)
            det = np.where(np.abs(det) < 1e-14, 1e-14, det)
            tv = o - T_[None, :, 0]
            u_ = (tv * pv).sum(-1) / det
            qv = np.cross(tv, e1[None])
            v_ = (d * qv).sum(-1) / det
            t_ = (e2[None] * qv).sum(-1) / det
            hit = (u_ >= 0) & (v_ >= 0) & (u_ + v_ <= 1) & (t_ >= 0) & (t_ <= depth + 0.03)
            tmax[i0:i0 + 64] = np.where(hit, t_, -np.inf).max(1)
        lm = np.maximum(tmax.reshape(len(Pm), len(ws)).max(1) - depth + clear, 0.0)
        lift, mid = lm[:len(P)].copy(), lm[len(P):]
        lift[:-1] = np.maximum(lift[:-1], mid)
        lift[1:] = np.maximum(lift[1:], mid)
        if not (lift > 1e-5).any():
            break
        lift = np.maximum(lift, np.maximum(np.r_[0.0, lift[:-1]], np.r_[lift[1:], 0.0]))
        P = P + lift[:, None] * Un
        U = Un
    return P, U


def draped_strap(obst, plan, A_c, B_c, dp, npn, width=0.046, th=0.002, clear=0.0015, step=0.025):
    """Lap belt draped under tension over the seat (review r3 K1): plan = (k, 2) pan-plane path (a along the pan, b =
    s) from the anchor side to the belt end; A_c / B_c = the pan-normal heights c of the anchor (at plan[0]) and the
    end (at plan[-1]); obst = seat-local Geos the belt lies on (cushion, fleece sleeves, pan).  Every obstacle vertex
    under the belt's width is unrolled onto the path (l along it, c along the pan normal); the belt follows the upper
    convex hull of those points from the anchor to the end (a strap under tension wraps the hull: up the cushion side,
    over the roll, bridging the fleece's troughs and resting on its crowns), offset clear + th / 2 outward.
    Returns (points (n, 3), up vectors (n, 3)) seat-local."""
    Pp = _catmull(plan, 48)
    seg = np.diff(Pp, axis=0)
    sl = np.linalg.norm(seg, axis=1)
    L = np.r_[0.0, np.cumsum(sl)]
    T = seg / sl[:, None]
    Vs = np.vstack([g.V for g in obst])
    a = Vs[:, 0] * dp[0] + Vs[:, 2] * dp[1]
    c = Vs[:, 0] * npn[0] + Vs[:, 2] * npn[1]
    q = np.c_[a, Vs[:, 1]]
    # project onto the polyline (the first / last segments extended)
    best_d = np.full(len(q), np.inf)
    best_l = np.zeros(len(q))
    for k in range(len(seg)):
        t = (q - Pp[k]) @ T[k]
        tc = np.clip(t, -np.inf if k == 0 else 0.0, np.inf if k == len(seg) - 1 else sl[k])
        foot = Pp[k] + tc[:, None] * T[k]
        d = np.abs((q - foot) @ np.array([-T[k, 1], T[k, 0]]))
        d = np.where(np.linalg.norm(q - foot, axis=1) <= d + 1e-9, d, np.inf)
        m = d < best_d
        best_d[m], best_l[m] = d[m], L[k] + tc[m]
    band = (best_d <= 0.5 * width + 0.002) & (best_l > 0.001) & (best_l < L[-1] - 0.001)
    pts = np.vstack([[0.0, A_c], np.c_[best_l[band], c[band]], [L[-1], B_c]])
    H = _upper_hull(pts)
    # densify and offset outward (normal of the chain, pointing up / outboard)
    dense = [H[0]]
    for p0, p1 in zip(H[:-1], H[1:]):
        k = max(1, int(np.ceil(np.linalg.norm(p1 - p0) / step)))
        dense += [p0 + (p1 - p0) * t for t in np.linspace(0.0, 1.0, k + 1)[1:]]
    D = np.array(dense)
    tg = np.gradient(D, axis=0)
    tg /= np.linalg.norm(tg, axis=1, keepdims=True)
    nl = np.c_[-tg[:, 1], tg[:, 0]]                                   # left normal of a left-to-right chain: up
    D = D + (clear + 0.5 * th) * nl
    # back to 3-D: plan position at l (extended beyond the ends), c along the pan normal
    li = np.clip(D[:, 0], 0.0, L[-1])
    ab = np.c_[np.interp(li, L, Pp[:, 0]), np.interp(li, L, Pp[:, 1])]
    kseg = np.clip(np.searchsorted(L, li, side="right") - 1, 0, len(seg) - 1)
    ab += (D[:, 0] - li)[:, None] * T[kseg]
    tan3 = np.c_[T[kseg, 0] * dp[0], T[kseg, 1], T[kseg, 0] * dp[1]]
    N3 = np.array([npn[0], 0.0, npn[1]])
    P3 = np.c_[ab[:, 0] * dp[0] + D[:, 1] * npn[0], ab[:, 1], ab[:, 0] * dp[1] + D[:, 1] * npn[1]]
    U3 = nl[:, :1] * tan3 + nl[:, 1:] * N3[None, :]
    return P3, U3


def crew_seat(side=-1, dx=0.0, dz=0.0, recline=0.0, head_c=None, arm_up=(False, False), sheepskin=None,
              tracks=True, harness=True, finish=None):
    """IPECO 3A318-type crew seat of the pilot (side=-1) or co-pilot (+1) at interior.crew_srp(side, dx, dz): dx fore
    / aft travel (+ aft), dz height adjustment, recline (deg beyond back_deg, about the SRP), head_c (headrest lock
    position along the back, default CREW_SEAT head_c), arm_up = (inboard, outboard) armrests flipped up along the
    back, sheepskin covers (default SHEEPSKIN), tracks: the two floor tracks (fixed, drawn at the neutral SRP),
    finish: a CREW_FINISHES key (default CREW_FINISH).  Returns [(Mesh, material)] in model coordinates."""
    c = I.CREW_SEAT
    fin = CREW_FINISHES[finish or CREW_FINISH]
    M_SHELL, M_CREW = fin["shell"], fin["upholstery"]                  # noqa: N806
    sk = SHEEPSKIN if sheepskin is None else bool(sheepskin)
    srp = I.crew_srp(side, dx, dz)
    fl = float(I.FLOOR["fd_wl"])
    vf = fl - srp[2]
    si = -side                                        # inboard lateral sign (seat-local s = model y offset)
    hc = float(c["head_c"] if head_c is None else head_c)
    p = math.radians(c["pan_deg"])
    dp, npn = np.array([math.cos(p), math.sin(p)]), np.array([-math.sin(p), math.cos(p)])
    D = float(c["pan_depth"])
    t0 = 0.025                                        # cushion top above the SRP line (interior.crew_seat_profile)
    ct = float(c["cushion_t"])
    t1 = ct - t0
    co, ci = 0.5 * float(c["cushion_w"]), float(c["cushion_in"])
    lo, hi = sorted((si * ci, -si * co))
    nw, nd = c["notch_wd"]
    L = float(c["back_len"])
    tl, tt = c["back_t"]
    geos = []

    # ---- cushion: split thigh pads, front U-notch (plan: drawing seat_plan_crew), along the pan (7 deg front up)
    plan = [(-0.045, lo), (D - 0.03, lo), (D, lo + 0.03), (D, -0.5 * nw), (D - nd, -0.5 * nw + 0.01),
            (D - nd, 0.5 * nw - 0.01), (D, 0.5 * nw), (D, hi - 0.03), (D - 0.03, hi), (-0.045, hi)]
    plan = fillet(plan, [0.03, 0.035, 0.035, 0.03, 0.035, 0.035, 0.03, 0.035, 0.035, 0.03], max_len=0.05)

    def pan_map(c_top):
        """(a along the pan, b = s, c up from the pad bottom) -> seat-local; c_top = the pad's top, above the SRP."""
        def fn(V, tpad):
            a, b, cc = V[:, 0], V[:, 1], V[:, 2] - tpad + c_top
            return np.c_[a * dp[0] + cc * npn[0], b, a * dp[1] + cc * npn[1]]
        return fn

    def thighs(h, R):
        """Crown of the seat: puffed, the two thigh pads split by a valley running aft from the notch [E: photos]."""
        def f(a, b, d):
            return h * smoothstep(0.0, R, d) - 0.9 * h * np.exp(-(b / 0.035) ** 2) * smoothstep(0.06, 0.26, a)
        return f

    # the drawn outline is cushion + sheepskin (CREW_SEAT cushion_t, sheepskin_t): with the cover the leather is 8 mm
    # inside it at the sides, SK_FRONT behind the drawn front and its top sheepskin_t below the drawn top; the fleece pad
    # (crowned thigh domes + tufts, the crown's top ON the drawn cushion top) rolls over the leather's front edge and
    # hangs down its front face, its outer face ending on the drawn front (review r2 M1)
    sk_t = float(c["sheepskin_t"])
    sk_in = sk_t if sk else 0.0                                      # leather top below the drawn cushion top
    tl_c = ct - sk_in
    rl = 0.020                                                       # leather front-top roll radius
    lp = plan
    if sk:
        lp = offset_outline(plan, -0.008)
        lp[:, 0] -= (SK_FRONT - 0.008) * smoothstep(D - 0.10, D - 0.03, lp[:, 0])
    g = pillow(lp, tl_c, rl if sk else 0.028, 0.012, h=None if sk else 0.024,
               crown=None if sk else thighs(0.012, 0.07), n_round=2 if sk else 3)
    geos.append(_mats(g.map(lambda V: pan_map(t0 - sk_in)(V, tl_c)), M_CREW))
    obst = [geos[-1]]                                                # what the lap belts drape over (review r3 K1)
    if sk:
        # pad plan: the thigh-pad fronts run on SK_WRAP_SEAT past the leather front and are wrapped round its front
        # roll (radius rl, 2 mm clear); the pad's flat top SK_CROWN_SEAT + SK_LUMP below the drawn top, so the crowned,
        # lumpy face stays on it; the pad bottom sinks `sink` into the leather
        # two sleeves, one over each thigh pad, split along the seat CL and at the U-notch (P1046408 / 10: two puffy
        # lumps per seat, the fleece wrapped round each pad's front)
        top_c = t0 - SK_CROWN_SEAT - SK_LUMP
        sink = SK_T - (top_c - (t0 - sk_t))
        g2 = 0.5 * SK_SPLIT
        ai = np.linspace(-0.045 + 0.04, D - 0.035, 14)                   # the inner edge: the split, then the notch
        bi = g2 + (0.5 * nw - 0.01 - g2) * smoothstep(D - nd - 0.07, D - nd, ai) + 0.01 * smoothstep(D - nd, D, ai)
        lump, fine = fleece(SK_LUMP, 11, k=SK_LUMP_K), fleece(SK_FLUFF, 1, k=(95.0, 120.0, 170.0), h_judged=0.016)
        sleeves = []
        for sg_, edge in ((-1, lo), (1, hi)):
            P_ = np.vstack([[(-0.045, sg_ * g2)], np.c_[ai, sg_ * bi], [(D, sg_ * 0.5 * nw), (D, edge - sg_ * 0.03),
                                                                         (D - 0.03, edge), (-0.045, edge)]])
            rr_ = np.r_[0.03, np.zeros(len(ai)), 0.03, 0.035, 0.035, 0.035]
            pp = fillet(P_, rr_, max_len=0.05)
            pp[:, 0] -= SK_FRONT * smoothstep(D - 0.10, D - 0.03, pp[:, 0])
            pp[:, 0] += SK_WRAP_SEAT * smoothstep(D - 0.07, D - 0.015, pp[:, 0])
            sleeves.append(_ccw(pp))
            g = pillow(pp, SK_T, SK_ROLL, SK_ROLL_B, h=_sk_h(0.016), crown=dome(SK_CROWN_SEAT, 0.075),
                       fluff=lambda a, b: lump(a, b) + fine(a, b))
            g = g.map(lambda V: _wrap(V, 0, D - SK_FRONT - rl, rl + 0.002, sink + 0.002))
            geos.append(_mats(g.map(lambda V: pan_map(top_c)(V, SK_T)), M_SHEEP))
            obst.append(geos[-1])

    # ---- pan shell under the cushion (black), side plates, life-vest box, cross tubes, tracks, fittings
    pcs0, _ = I.crew_seat_profile(hc, 0.0)
    geos.append(slab(fillet(pcs0["pan"], 0.012), lo + 0.01, hi - 0.01, 0.010, M_BASE))
    obst.append(geos[-1])
    base = I.crew_base_profile(vf)
    pw = 0.5 * float(c["base_w"])
    for sg in (-1, 1):
        geos.append(plate(base["plate"], sg * pw - 0.006, sg * pw + 0.006, M_BASE))
    lv = c["life_vest"]
    geos.append(slab(fillet(base["vest"], 0.012), -0.5 * lv[1], 0.5 * lv[1], 0.012, M_BASE))
    # the box hangs on two brackets per side from the side plates (review r1 C5: it floated 17 mm clear) [E]
    vu0, vv0 = np.asarray(base["vest"]).min(0)
    vu1, vv1 = np.asarray(base["vest"]).max(0)
    for sg in (-1, 1):
        for u in (vu0 + 0.06, vu1 - 0.06):
            s_a, s_b = sg * (0.5 * float(lv[1]) - 0.004), sg * (pw - 0.005)
            geos.append(cbox((u, 0.5 * (s_a + s_b), vv1 - 0.022), (0.032, abs(s_b - s_a), 0.020), M_BASE))
    zb = lambda u: u * math.tan(p) - (t1 + 0.035) / math.cos(p)     # noqa: E731 -- pan underside (crew_base_profile)
    for u in (-0.08, 0.34):
        geos.append(tube((u, -pw, zb(u) - 0.035), (u, pw, zb(u) - 0.035), 0.011, M_RAIL, n=10))
    # recline brackets: from the side plates' rear up to the back's lower sides [E] (IPECO line art)
    brk = fillet([(-0.135, zb(-0.135) - 0.05), (-0.02, zb(-0.02) - 0.05), (-0.02, zb(-0.02) + 0.02),
                  (-0.07, 0.035), (-0.125, 0.035)], 0.012)
    for sg in (-1, 1):
        geos.append(plate(brk, sg * (pw + 0.006), sg * (pw + 0.016), M_BASE))
    ur, uf = c["base_feet"]
    th = float(I.SEAT_TRACKS["crew_h"])
    tw = float(I.SEAT_TRACKS["w"])
    ry = float(c["rail_dy"])
    for sg in (-1, 1):
        for u in (ur + 0.035, uf - 0.035):
            s_a, s_b = sg * (ry - 0.5 * tw), sg * (pw + 0.0055)       # 0.5 mm inside the plate's outer face (r3 K3)
            geos.append(cbox((u, 0.5 * (s_a + s_b), vf + 0.5 * (th + 0.012)), (0.05, abs(s_b - s_a), th + 0.012),
                             M_RAIL))

    # ---- levers: recline (rear inboard, beside the cushion: above the tunnel plinth top over the whole travel),
    # fore / aft (on the inboard plate, >= 15 mm from the plinth), height (cushion front); thigh wheel
    for p0, p1 in (((-0.085, si * 0.200, 0.042), (0.020, si * 0.206, 0.032)),
                   ((0.30, si * (pw + 0.010), vf + 0.10), (0.37, si * (pw + 0.016), vf + 0.20)),
                   ((0.36, si * 0.10, zb(0.36) - 0.01), (0.47, si * 0.10, zb(0.47) - 0.02))):
        geos.append(tube(p0, p1, 0.0065, M_METAL, n=8))
        geos.append(rbox(p1, (0.030, 0.022, 0.022), 0.009, M_BLACK))
    geos.append(tube((0.44, -0.009, zb(0.44) - 0.012), (0.44, 0.009, zb(0.44) - 0.012), 0.024, M_BLACK, n=14))

    # ---- back group, built upright and reclined about the SRP
    db, nb = _back_frame(c["back_deg"])
    back = []
    # the drawn back outline (interior.crew_seat_profile), its top arc replaced by two corners filleted r 0.032 and
    # the samples next to the corners dropped, so every corner radius exceeds the edge rounding (<= 5 mm change)
    bp = np.asarray(pcs0["back"])
    bb = bp @ db
    keep = np.ones(len(bp), bool)
    keep[1:-1] = (bb[1:-1] > 0.075) & (bb[1:-1] < L - 0.075)
    # with the cover the shell's front lies sheepskin_t behind the drawn front and its top SK_TOP below the drawn top
    # (the fleece wraps over it onto the drawn top: review r2 M1); the top then a half-round (r 0.018)
    sk_b, L_s = (sk_t, L - SK_TOP) if sk else (0.0, L)
    fr = np.array([L_s * db + (0.02 - sk_b) * nb, L_s * db - (tt - 0.02) * nb])
    kp = bp[keep]
    split = int(np.argmax(kp @ nb < -0.03))                   # first point of the rear face: insert the top there
    kp[:split] -= sk_b * nb                                   # the front face (the first point and the front samples)
    rads = np.full(len(kp) + 2, 0.032)
    if sk:
        rads[split] = rads[split + 1] = 0.016                   # the 36 mm top: nearly a half-round
    bprof = fillet(np.vstack([kp[:split], fr, kp[split:]]), rads)
    bw1 = 0.5 * float(c["back_w"][1])
    back.append(slab(bprof, -bw1, bw1, 0.012 if sk else 0.028, M_SHELL, max_len=0.05, h=0.045,
                     width=lambda u, v: _crew_back_hw(u * db[0] + v * db[1]) / bw1, post=rear_round(nb, 0.030)))
    bmap = _back_map(db, nb, front=_crew_front)
    if sk:
        # back cover: down the whole front and wrapped over the top edge toward the rear (AOPA, P1046408 / 10), the
        # shell's front-top roll (r 0.018) as the roll; the crowned, lumpy face on the drawn front (review r2 M1)
        apex = SK_T + SK_CROWN_BACK + SK_LUMP
        sink_b = apex - sk_t                                  # the pad bottom into the shell front
        Rb = 0.018 + 0.002
        ol = _outline_from_hw(0.035, L_s - 0.018 + 1.9 * Rb,
                              lambda b: _crew_back_hw(np.minimum(b, L_s - 0.004), 0.004), 0.03)
        lump = fleece(SK_LUMP, 12, k=SK_LUMP_K)
        fine = fleece(SK_FLUFF, 2, k=(95.0, 120.0, 170.0), h_judged=0.021)
        g = pillow(ol, SK_T, SK_ROLL, SK_ROLL_B, h=_sk_h(0.021), crown=dome(SK_CROWN_BACK, 0.06),
                   fluff=lambda a, b: lump(a, b) + fine(a, b))
        g = g.map(lambda V: _wrap(V, 1, L_s - 0.018, Rb, sink_b + 0.002))
        back.append(_mats(g.map(lambda V: bmap(V - [0, 0, apex])), M_SHEEP))
    else:
        # cream leather front: centre panel between two raised side bolsters (IPECO line art)
        ci_hw = lambda b: _crew_back_hw(b) - 0.075             # noqa: E731
        g = pillow(_outline_from_hw(0.05, L - 0.07, ci_hw, 0.03), 0.022, 0.010, 0.006, h=0.035,
                   crown=dome(0.004, 0.05), n_round=2)
        back.append(_mats(g.map(lambda V: bmap(V - [0, 0, 0.014])), M_CREW))
        for sg in (-1, 1):
            bs = np.linspace(0.04, L - 0.04, 9)
            inner, outer = ci_hw(bs) + 0.004, _crew_back_hw(bs, -0.004)
            P = np.vstack([np.c_[sg * inner, bs], np.c_[sg * outer[::-1], bs[::-1]]])
            g = pillow(fillet(P, 0.02), 0.026, 0.012, 0.006, h=0.018, crown=dome(0.008, 0.02), n_round=2)
            back.append(_mats(g.map(lambda V: bmap(V - [0, 0, 0.014])), M_CREW))

    # headrest: winged, on two stalks, lock position hc; cream front, anthracite rim and back
    hh, hwid, ht = c["head_hwt"]
    hol = rrect(-0.5 * hwid, hc - 0.5 * hh, 0.5 * hwid, hc + 0.5 * hh, 0.05, max_len=0.05)
    g = pillow(hol, ht, 0.03, 0.03, h=0.035, crown=dome(0.006, 0.05))
    wing = lambda a: 0.025 * (np.abs(a) / (0.5 * hwid)) ** 3   # noqa: E731 -- winged sides, [E] (IPECO line art)
    hmap = _back_map(db, nb)
    back.append(_mats(g.map(lambda V: hmap(np.c_[V[:, 0], V[:, 1], V[:, 2] - (ht - 0.035) + wing(V[:, 0])])),
                      M_CREW, M_SHELL, M_SHELL))
    for a in (-0.065, 0.065):
        p0 = (L - 0.045) * db - 0.035 * nb
        p1 = (hc - 0.5 * hh + 0.03) * db - 0.035 * nb
        back.append(tube((p0[0], a, p0[1]), (p1[0], a, p1[1]), 0.0085, M_METAL, n=10))

    # harness (4-point, IPECO line art; review r2 F9): shoulder straps from the inertia reel over the back top down the
    # front to the rotary buckle on the lap, the two lap-belt halves from the anchors at the pan's rear corners over the
    # sleeves to the buckle, the crotch strap from the pan front up through the U-notch along the split between the
    # thigh sleeves.  Straps are laid on the fleece's modelled top (fleece_pt) so they neither float nor sink into it.
    pad_top = 0.0045 if sk else 0.018          # strap centre above front(b): on the fleece's crown / the leather [E]

    def fleece_pt(a, b, lift=0.0035):
        """Seat-local (u, s, v) of the seat's top (fleece or leather) at pan position a, lateral b, + lift along the
        pan normal (a strap's half-thickness and a hair)."""
        if sk:
            ol_ = sleeves[1] if b > 0 else sleeves[0]
            d = -float(sdf2d.polygon(np.array([a]), np.array([b]), ol_)[0])
            if d > 0:
                cc = top_c + SK_T + float(dome(SK_CROWN_SEAT, 0.075)(a, b, d)) + float(lump(a, b) + fine(a, b))
                cc -= SK_ROLL - math.sqrt(max(SK_ROLL ** 2 - max(SK_ROLL - d, 0.0) ** 2, 0.0))
            else:
                cc = t0 - sk_t
            cc -= SK_T
        else:
            cc = t0
        cc += lift
        return np.array([a * dp[0] + cc * npn[0], b, a * dp[1] + cc * npn[1]])
    ub = 0.115                                                     # buckle on the lap, 115 mm ahead of the SRP
    bq = 0.5 * (fleece_pt(ub, -0.035) + fleece_pt(ub, 0.035))
    buckle = bq + [0.0, 0.0, 0.012]
    straps = []
    if harness:
        for sg in (-1, 1):
            n_s = 0.02 - (sk_t if sk else 0.0) - 0.5 * (tt - 0.02 - (sk_t if sk else 0.0))   # the reel slot [E]
            n_f = float(_crew_front(L - 0.06)) + pad_top
            rh, nh = 0.5 * (n_f - n_s), 0.5 * (n_f + n_s)                    # over the top: a half-round
            ta = np.radians([-180.0, -135.0, -90.0, -45.0, 0.0])
            b_dn = np.array([L - 0.10, 0.46, 0.33, 0.19])                       # down the front, evenly spaced
            bs = np.r_[L - 0.050, L + 0.004 - rh + rh * np.sin(-ta), b_dn]
            cc = np.r_[n_s, nh - rh * np.cos(ta + np.pi), _crew_front(b_dn) + pad_top]
            aa = sg * np.array([0.060, 0.060, 0.060, 0.060, 0.060, 0.060, 0.059, 0.053, 0.046, 0.040])
            pts = np.array([[(b_ * db + c_ * nb)[0], a_, (b_ * db + c_ * nb)[1]] for b_, c_, a_ in zip(bs, cc, aa)])
            ups = np.array([[-nb[0], 0, -nb[1]]] + [[math.sin(t_) * db[0] - math.cos(t_) * nb[0], 0,
                                                     math.sin(t_) * db[1] - math.cos(t_) * nb[1]] for t_ in ta + np.pi]
                           + [[nb[0], 0.0, nb[1]]] * 4)
            straps.append((pts, ups))
            q = 0.47 * db + (_crew_front(0.47) + pad_top + 0.0065) * nb        # adjuster clear of the strap
            back.append(rbox((q[0], sg * 0.049, q[1]), (0.012, 0.056, 0.030), 0.004, M_METAL,
                             R=np.array([[nb[0], 0, db[0]], [0, 1, 0], [nb[1], 0, db[1]]])))

    backg = [g_.rot((0.0, 0.0), recline) for g_ in back]
    geos += backg
    if harness:
        # everything a strap may rest on (cushion, fleece, pan, back shell / cover, headrest): strap_clear lifts each
        # strap clear of it (review r3 K1: straps laid on the analytic fleece crown sank between its lumps)
        rest_on = obst + [g_ for g_ in backg if set(g_.mats.values()) & {M_SHEEP, M_SHELL, M_CREW}]
        rr_ = math.radians(recline)
        Rr = np.array([[math.cos(rr_), 0, -math.sin(rr_)], [0, 1, 0], [math.sin(rr_), 0, math.cos(rr_)]])
        for pts, ups in straps:
            pts, ups = pts @ Rr.T, ups @ Rr.T
            end = buckle + [-0.022, np.sign(pts[0, 1]) * 0.018, 0.004]
            mid = 0.55 * pts[-1] + 0.45 * end + [0.010, 0.0, 0.004]
            Ps, Us = _catmull(np.vstack([pts, mid, end]), 30), _catmull(np.vstack([ups, [[0.6, 0, 0.8]] * 2]), 30)
            Ps, Us = strap_clear(Ps, Us, rest_on, 0.046, 0.0035)
            geos.append(ribbon(Ps, Us, 0.046, M_HARN, n=None))
        # lap-belt halves (review r3 K1): from a bracket on the pan's side at its rear, up the cushion side, over the
        # sleeve's roll and across it to the buckle, draped under tension over the modelled fleece (draped_strap: the
        # upper hull of the fleece / cushion under the belt, 1.5 mm clear), 2 mm webbing with rounded edges
        for s_side in (lo, hi):
            sg = float(np.sign(s_side))
            s_pan = s_side - sg * 0.010                                 # the pan shell's side face
            ua, ca = 0.050, -(t1 + 0.0175)                             # anchor: pan side, ahead of the back's
            #                                                              fleece, mid-depth of the pan
            bend = buckle + [-0.004, sg * 0.036, -0.008]
            a_b = float(bend[0] * dp[0] + bend[2] * dp[1])
            c_b = float(bend[0] * npn[0] + bend[2] * npn[1])
            plan = np.array([(ua, s_side + sg * 0.030), (ua, s_side - sg * 0.010), (ua + 0.022, s_side - sg * 0.065),
                             (0.5 * (ua + a_b) + 0.012, sg * 0.080), (a_b, float(bend[1]))])
            Pb, Ub = draped_strap(obst, plan, ca, c_b, dp, npn)
            Pb, Ub = strap_clear(Pb, Ub, rest_on, 0.046, 0.002)
            geos.append(ribbon(Pb, Ub, 0.046, M_HARN, th=0.002, n=None, rounded=True))
            # the anchor bracket on the pan side (the belt end inside it)
            s_out = float(Pb[0, 1])
            geos.append(cbox((ua + 0.002, 0.5 * (s_pan + s_out), ca), (0.030, abs(s_out - s_pan) + 0.006, 0.026),
                             M_BASE))
        # crotch strap: from the pan front under the notch, up through it and back along the split to the buckle
        a_n = D - nd
        z_split = lambda a: 0.5 * (fleece_pt(a, -0.021, 0.0) + fleece_pt(a, 0.021, 0.0))   # noqa: E731
        ctrl = np.array([[a_n + 0.02, 0.0, (t0 - ct) * 1.0 + 0.012], [a_n + 0.016, 0.0, t0 - sk_t + 0.014],
                         z_split(a_n - 0.03), z_split(0.30), z_split(0.21), buckle + [0.030, 0.0, -0.006]])
        ups = np.array([[1, 0, 0], [0.7, 0, 0.7], [0, 0, 1], [0, 0, 1], [0, 0, 1], [-0.2, 0, 1]])
        Pc, Uc = strap_clear(_catmull(ctrl, 20), _catmull(ups, 20), rest_on, 0.040, 0.0035)
        geos.append(ribbon(Pc, Uc, 0.040, M_HARN, n=None))
        nrm = _unit3([0.25, 0.0, 0.97])
        geos.append(tube(buckle - 0.008 * nrm, buckle + 0.008 * nrm, 0.036, M_METAL, n=20))
        geos.append(tube(buckle + 0.007 * nrm, buckle + 0.012 * nrm, 0.020, M_BLACK, n=16))

    # ---- armrests: hinged on the back sides at arm_pivot; level (down) or flipped up along the back
    ah = float(c["arm_h"])
    al, aw = c["arm_lw"]
    W_ = 0.5 * float(c["width"])
    ar = 0.0225
    piv = np.array([-(ah - ar) * math.tan(math.radians(c["back_deg"])) + c["arm_pivot"], ah - ar])
    if recline:
        a_ = math.radians(recline)
        piv = np.array([piv[0] * math.cos(a_) - piv[1] * math.sin(a_), piv[0] * math.sin(a_) + piv[1] * math.cos(a_)])
    cap = np.vstack([np.c_[piv[0] + al - 0.02 + ar * np.cos(t), piv[1] + ar * np.sin(t)]
                     for t in [np.radians(np.linspace(-90, 90, 9))]] +
                    [np.c_[piv[0] + ar * np.cos(t), piv[1] + ar * np.sin(t)]
                     for t in [np.radians(np.linspace(90, 270, 9))]])
    # the drawn arm (CREW_SEAT arm_h / arm_lw, L6 detail E1: a 45-mm capsule) is the WHOLE arm, fleece included
    # (review r3 C2: rev C's sleeves stood 15 mm above it and 4-6 mm outside it in plan): with the cover the shell is
    # a slimmer capsule (top 12 mm down, 4 mm in each side) and the sleeve over it ends on the drawn top and sides
    sk_top, sk_side = (0.012, 0.004) if sk else (0.0, 0.0)
    ar_s = ar - 0.5 * sk_top
    cap_s = np.vstack([np.c_[piv[0] + al - 0.02 + ar_s * np.cos(t), piv[1] - 0.5 * sk_top + ar_s * np.sin(t)]
                       for t in [np.radians(np.linspace(-90, 90, 9))]] +
                      [np.c_[piv[0] + ar_s * np.cos(t), piv[1] - 0.5 * sk_top + ar_s * np.sin(t)]
                       for t in [np.radians(np.linspace(90, 270, 9))]])
    for sg in (-1, 1):
        s0, s1 = (sg * W_ - aw, sg * W_) if sg > 0 else (sg * W_, sg * W_ + aw)
        arm = [slab(_subdivide(cap_s, 0.06), s0 + sk_side, s1 - sk_side, 0.012 if not sk else 0.010, M_SHELL)]
        if sk:
            f_amp = 0.0012                                   # fleece lumps: the outline wiggles 1.6 x this
            pl = rrect(piv[0] - 0.012, s0 + 0.0025, piv[0] + al - 0.028, s1 - 0.0025, 0.02)
            g = pillow(pl, 0.0095, 0.0045, 0.003, h=_sk_h(0.03), crown=dome(0.0025, 0.02), fluff=fleece(f_amp, 3))
            z0 = piv[1] + ar - sk_top - 0.001                            # 1 mm into the shell's top
        else:
            pl = rrect(piv[0] - 0.012, s0 - 0.004, piv[0] + al - 0.028, s1 + 0.004, 0.02)
            g = pillow(pl, 0.014, 0.008, 0.004)
            z0 = piv[1] + ar - 0.010
        arm.append(_mats(g.map(lambda V, z=z0: np.c_[V[:, 0], V[:, 1], z + V[:, 2]]), M_SHEEP if sk else M_CREW))
        inner = sg * (_crew_back_hw(float(np.dot(piv, db))) - 0.02)
        arm.append(tube((piv[0], inner, piv[1]), (piv[0], s0 if sg > 0 else s1, piv[1]), 0.016, M_BASE, n=12))
        up = arm_up[0] if sg == si else arm_up[1]
        if up:
            arm = [g_.rot(tuple(piv), 90.0 + c["back_deg"] + recline) for g_ in arm]
        geos += arm

    # ---- place: seat-local (u fwd, s, v up from the SRP) -> model
    out = [g_.map(lambda V: np.c_[srp[0] - V[:, 0], srp[1] + V[:, 1], srp[2] + V[:, 2]]) for g_ in geos]
    if tracks:
        srp0 = I.crew_srp(side)
        rl = I.crew_base_profile(fl - srp0[2])["rail"]                 # fixed, drawn at the neutral notch (L6)
        for sg in (-1, 1):
            u0, u1 = float(rl[:, 0].min()), float(rl[:, 0].max())
            out.append(cbox((srp0[0] - 0.5 * (u0 + u1), srp0[1] + sg * ry, fl + 0.5 * th), (u1 - u0, tw, th), M_RAIL))
            out.append(cbox((srp0[0] - 0.5 * (u0 + u1), srp0[1] + sg * ry, fl + th + 0.0004),
                            (u1 - u0 - 0.02, 0.35 * tw, 0.001), M_BLACK))
    return to_meshes(out)


# =====================================================================================================================
# executive seat (EXEC_SEAT)
# =====================================================================================================================
REAR_ROUND = 0.025       # [E] executive back: rear face rounded across, sides this far forward of the centreline


EXEC_TOP = (0.80, 0.018, 0.085)   # [M] P1046406: the sides draw in over the top ~20 % by 18 mm, corners r 0.085 (r2 F1)


def _exec_hw(b, s_top, extra=0.0):
    """Half-width of the executive back at along-back position b: lumbar back_w[1] up to 0.22, widening to the
    shoulder width back_w[0] at 85 % of the height, then drawing in by EXEC_TOP toward the top on a smoothstep from
    EXEC_TOP[0] of the height (review r3 K2: rev C drew in on a kink), the top corners rounded r EXEC_TOP[2] by
    subtracting the circle's deficit from that curve (value and slope continuous) [E/M: photos] (inside the L6 front
    view's chamfered top corners)."""
    e = I.EXEC_SEAT
    bw0, bw1 = 0.5 * e["back_w"][0], 0.5 * e["back_w"][1]
    f0, taper, rr = EXEC_TOP
    b = np.asarray(b, float)
    hw = bw1 + (bw0 - bw1) * smoothstep(0.22, 0.85 * s_top, b) - taper * smoothstep(f0 * s_top, s_top, b)
    d = np.clip(b - (s_top - rr), 0.0, rr)
    return hw - (rr - np.sqrt(np.maximum(rr * rr - d * d, 0.0))) + extra


def _densify_top(P, o, db, b0, step):
    """Profile polygon P (u, v) with extra points (every `step`) on its edges beyond b0 along the back (o, db): the
    lateral taper of the top band is then sampled finely (review r3 K2)."""
    out = []
    P = np.asarray(P, float)
    for k in range(len(P)):
        a, c = P[k], P[(k + 1) % len(P)]
        out.append(a)
        ba, bc = float((a - o) @ db), float((c - o) @ db)
        if max(ba, bc) > b0:
            n = int(np.ceil(np.linalg.norm(c - a) / step))
            for t in np.linspace(0.0, 1.0, n + 1)[1:-1]:
                out.append(a + t * (c - a))
    return np.array(out)


def seat_record(seat_id, layout=None):
    layout = layout or I.DEFAULT_LAYOUT
    for r in I.seat_map(layout):
        if r["id"] == seat_id:
            return r
    raise KeyError(f"no seat {seat_id!r} in layout {layout}")


def cabin_seat(seat_id, layout=None, recline=None, raised=False, belts=True):
    """PRO executive seat `seat_id` ('PAX 1' ..) of a SEAT_LAYOUTS layout (default DEFAULT_LAYOUT) at its seat_map()
    station: recline = back angle from vertical in deg (default EXEC_SEAT back_deg, the TTL upright), raised = the
    sliding headrest at the top of its travel.  Returns [(Mesh, material)] in model coordinates."""
    e = I.EXEC_SEAT
    rec = seat_record(seat_id, layout)
    if rec.get("crew"):
        raise ValueError(f"{seat_id} is a crew seat: use crew_seat()")
    s_rec = next(s for s in I.SEAT_LAYOUTS[layout or I.DEFAULT_LAYOUT]["seats"] if s["id"] == seat_id)
    if s_rec.get("kind") == "commuter":
        raise NotImplementedError("commuter seats (STD-9S) are not drawn on L6: no table geometry to build from")
    fx = -float(rec["facing"])
    side = int(rec["side"])
    si = -side                                        # the aisle side (the one armrest)
    fl = float(I.FLOOR["wl"])
    sh, sf, ctop, clt = (float(e[k]) for k in ("srp_h", "srp_front", "cushion_top", "cushion_t"))
    bl_, bh = (float(v) for v in e["base_wh"])
    bu = float(e["base_u"])
    pt = ctop - clt
    cw = 0.5 * float(e["cushion_w"])
    W_ = 0.5 * float(e["width"])
    aw = float(e["arm_w"])
    th = float(I.SEAT_TRACKS["h"])
    geos = []

    # ---- base shroud on the tracks (anthracite), life-vest placard and red pull tab on its front face, fittings
    bw = 0.5 * bl_
    geos.append(slab(rrect(bu - bl_, th, bu, bh, 0.015), -bw, bw, 0.015, M_CAB_DARK))
    geos.append(cbox((bu + 0.0012, -si * 0.075, th + 0.085), (0.003, 0.042, 0.042), M_WHITE))
    geos.append(cbox((bu + 0.0020, -si * 0.075, th + 0.083), (0.003, 0.022, 0.026), M_TAB))
    geos.append(rbox((bu + 0.005, 0.0, th + 0.024), (0.012, 0.030, 0.016), 0.004, M_TAB))
    for rail_bl in I.SEAT_TRACKS["bl"]:
        s = side * float(rail_bl) - float(rec["bl"])
        if abs(s) <= bw + 0.02:
            for u in (bu - bl_ + 0.035, bu - 0.035):
                geos.append(cbox((u, s, 0.5 * (th + 0.01)), (0.06, 0.038, th + 0.01), M_RAIL))

    # ---- skirt under the cushion (anthracite, like the shroud: P1046406 [M]) and the light-grey leather cushion
    #      (drawing exec_seat_side)
    und = I.exec_under_profile(rec["facing"])
    lrest = und["legrest"]
    skirt = und["skirt"].copy()
    if lrest is not None:                         # the skirt stops 1 mm behind the legrest's rear face
        skirt[1:3, 0] = float(lrest[:, 0].min()) - 0.001
    geos.append(slab(fillet(skirt, 0.02), -(cw - 0.01), cw - 0.01, 0.018, M_CAB_DARK))
    if lrest is not None:
        # legrest (forward-facing seats, EXEC_SEAT legrest; review r3 F1): a crowned leather pad seen from the front
        # (the drawn width x face height), its depth mapped onto the drawn side profile -- the full depth above the
        # shroud, a lip only in front of the shroud face below its top edge; the front 10 mm (the rounded face edge)
        # is kept undistorted
        lw, lh, lset, ld = (float(v) for v in e["legrest"])
        uf = float(lrest[:, 0].max())
        vb, vt = float(lrest[:, 1].min()), float(lrest[:, 1].max())
        lip = uf - float(lrest[2, 0])                                  # lip depth in front of the shroud
        r_f = 0.010
        ol = rrect(-0.5 * lw, vb, 0.5 * lw, vt, 0.024, max_len=0.04)
        ins = []                                                       # outline points where the depth changes
        for k in range(len(ol)):
            p0_, p1_ = ol[k], ol[(k + 1) % len(ol)]
            ins.append(p0_)
            for vv in sorted(bh + np.array([0.001, 0.004, 0.008, 0.011]), reverse=bool(p1_[1] < p0_[1])):
                if (p0_[1] - vv) * (p1_[1] - vv) < 0:
                    ins.append(p0_ + (vv - p0_[1]) / (p1_[1] - p0_[1]) * (p1_ - p0_))
        g = pillow(np.array(ins), ld, r_f, 0.004, h=0.03, crown=dome(0.004, 0.05))

        def lr_map(V):
            a, b, c = V[:, 0], V[:, 1], V[:, 2]
            cr = np.maximum(ld - c, 0.0)                                # depth behind the face
            T = lip + (ld - lip) * smoothstep(bh + 0.001, bh + 0.011, b)
            k = (T - r_f) / (ld - r_f)
            u = np.where(cr <= r_f, uf - cr, uf - r_f - (cr - r_f) * k)
            u = u + np.maximum(c - ld, 0.0)                               # the crown bulges forward
            return np.c_[u, a, b]
        geos.append(_mats(g.map(lr_map), M_CAB))
    u_r, u_f = -0.02, sf - 0.05
    slope = (ctop - (sh + 0.025)) / (u_f - u_r)

    def cush_map(tpad, z0=pt - 0.01, extra=0.0):
        def fn(V):
            u, s, c = V[:, 0], V[:, 1], V[:, 2]
            ztop = (sh + 0.025) + slope * (u - u_r) + extra
            return np.c_[u, s, z0 + c / tpad * (ztop - z0)]
        return fn
    cush = rrect(-0.05, -cw, sf, cw, 0.05, max_len=0.05)
    tc = ctop - (pt - 0.01)
    g = pillow(cush, tc, 0.035, 0.010, h=0.04, crown=dome(0.008, 0.08))
    geos.append(_mats(g.map(cush_map(tc)), M_CAB))
    # raised side panels of the cushion (the V-stitch lines run on down the seat, photos)
    for sg in (-1, 1):
        a0, a1 = (0.125, cw + 0.003) if sg > 0 else (-cw - 0.003, -0.125)
        g = pillow(rrect(-0.045, a0, sf + 0.002, a1, 0.035, max_len=0.05), tc, 0.033, 0.010, h=0.04,
                   crown=dome(0.006, 0.03))
        geos.append(_mats(g.map(cush_map(tc, extra=0.004)), M_CAB))
    # soft front drape: the leather rolls over the cushion's front edge down onto the skirt (P1046402 / 03 [M], review
    # r1 F10), inside the drawn cushion front
    d_lo = (0.004, 0.003) if lrest is not None else (0.052, 0.040)    # with a legrest it stops at its top (r3 F1)
    drape = fillet([(sf - 0.055, pt - d_lo[0]), (sf - 0.006, pt - d_lo[1]), (sf - 0.002, pt + 0.030),
                    (sf - 0.055, pt + 0.030)], [0.012, 0.012, 0.020, 0.012] if lrest is not None else
                   [0.016, 0.022, 0.020, 0.016], max_len=0.03)
    geos.append(slab(drape, -(cw - 0.014), cw - 0.014, 0.012, M_CAB))

    # ---- back group (upright, then reclined about the SRP): shell, V-stitched front panels, rear insert + pocket,
    # headrest on two posts, shoulder-belt guide
    db, nb = _back_frame(e["back_deg"])
    cb = math.cos(math.radians(e["back_deg"]))
    s_top = (float(e["back_top"]) - sh) / cb
    o = np.array([0.0, sh])
    pr = I.exec_back_profile(False)
    bw1 = 0.5 * float(e["back_w"][1])
    back = [slab(_densify_top(fillet(pr["back"], 0.03), o, db, 0.74 * s_top, 0.019), -bw1, bw1, 0.03, M_CAB,
                 max_len=0.035, h=0.05,
                 width=lambda u, v: _exec_hw((u - o[0]) * db[0] + (v - o[1]) * db[1], s_top) / bw1,
                 post=lambda u, v, e: rear_round(nb, REAR_ROUND)(u - o[0], v - o[1], e))]
    fmap = _back_map(db, nb, o=o, front=lambda b: 0.02 + 0.0 * b)
    hwf = lambda b, x=0.0: _exec_hw(b, s_top, x)                # noqa: E731
    # V-stitched front (P1046406 / 02 / 03, review r2 F1): a flush lumbar trapezoid low on the back, two seams leaving
    # its top corners and running straight up and out to the bolster edge at ~80 % of the height (a clear V), the
    # side bolsters tapering to nothing at the shoulders, the centre panel spanning the back above them
    b0_, b_lum = 0.05, 0.185                                      # lumbar panel foot / top along the back [M]
    lum_bot, lum_top = 0.064, 0.078                               # its half-widths (a trapezoid) [M]
    b80 = 0.80 * s_top
    v80 = float(hwf(b80)) - 0.020
    b_v = s_top - 0.040

    def vin(b):
        """Half-width of the centre panel (the V seams): lum_top at the lumbar top, linear to hw - 0.02 at 80 %."""
        b = np.asarray(b, float)
        t = np.clip((b - b_lum) / (b80 - b_lum), 0.0, 1.0)
        return np.minimum(lum_top + (v80 - lum_top) * t, hwf(b) - 0.020)
    # lumbar panel: flush, no crown (the seam round it is the joint)
    g = pillow(fillet([(-lum_bot, b0_ + 0.004), (lum_bot, b0_ + 0.004), (lum_top, b_lum - 0.004),
                       (-lum_top, b_lum - 0.004)], [0.03, 0.03, 0.014, 0.014], max_len=0.04), 0.024, 0.010, 0.006,
               h=0.045, crown=dome(0.0015, 0.04), n_round=2)
    back.append(_mats(g.map(lambda V: fmap(V - [0, 0, 0.018])), M_CAB))
    # centre panel: the V from the lumbar top, then the full width over the shoulders
    bs = np.r_[np.linspace(b_lum + 0.004, b80, 9), np.linspace(b80 + 0.03, b_v, 4)]
    P = np.vstack([np.c_[vin(bs), bs], np.c_[-vin(bs[::-1]), bs[::-1]]])
    g = pillow(fillet(P, np.r_[0.014, np.zeros(len(bs) - 2), 0.04, 0.04, np.zeros(len(bs) - 2), 0.014], max_len=0.05),
               0.026, 0.012, 0.006, h=0.045, crown=dome(0.004, 0.05), n_round=2)
    back.append(_mats(g.map(lambda V: fmap(V - [0, 0, 0.018])), M_CAB))
    # side bolsters: raised, from beside the lumbar panel up along the V seam, tapering to a rounded tip at the shoulder
    for sg in (-1, 1):
        bb_ = np.linspace(b0_ + 0.004, b80, 40)
        inner = np.where(bb_ < b_lum, np.interp(bb_, [b0_, b_lum], [lum_bot, lum_top]) + 0.006, vin(bb_) + 0.006)
        outer = hwf(bb_, -0.010)
        ok = outer - inner > 0.030
        bb_, inner, outer = bb_[ok], inner[ok], outer[ok]
        bs = np.r_[bb_[0], bb_[4:-1][::3]]
        bs = np.r_[bs[bs < bb_[-1] - 0.025], bb_[-1]]                  # no two samples closer than 25 mm at the tip
        inner, outer = np.interp(bs, bb_, inner), np.interp(bs, bb_, outer)
        rt = 0.5 * (outer[-1] - inner[-1])                            # a round tip (>= 15 mm) at the shoulder
        ang = np.radians(np.linspace(170.0, 10.0, 7))
        tip = np.c_[sg * (inner[-1] + rt + rt * np.cos(ang)), bs[-1] + 1.3 * rt * np.sin(ang)]
        Pb = np.vstack([np.c_[sg * inner[:-1], bs[:-1]], tip, np.c_[sg * outer[-2::-1], bs[-2::-1]]])
        rb_ = np.r_[0.016, np.full(len(bs) - 2, 0.014), np.zeros(len(tip)), np.full(len(bs) - 2, 0.014), 0.016]
        g = pillow(fillet(Pb, rb_), 0.032, 0.012, 0.006, h=0.045, crown=dome(0.008, 0.03), n_round=2)
        back.append(_mats(g.map(lambda V: fmap(V - [0, 0, 0.018])), M_CAB))
    # rear: dark insert with an arched top over the lower two thirds and a map pocket, following the rounded rear
    # face (photos: seat backs seen from behind)
    b_bot = float(np.dot(pr["back"][-1] - o, db))               # the profile's rear line: bottom -> top
    n_bot, n_top = float(np.dot(pr["back"][-1] - o, nb)), float(np.dot(pr["back"][3] - o, nb))

    def rmap(sink):
        def fn(V):
            a, b, c = V[:, 0], V[:, 1], V[:, 2]
            n = np.interp(b, [b_bot, s_top], [n_bot, n_top]) + REAR_ROUND * (a / hwf(b)) ** 2 - (c - sink)
            p_ = o[None, :] + b[:, None] * db[None, :] + n[:, None] * nb[None, :]
            return np.c_[p_[:, 0], a, p_[:, 1]]
        return fn
    # final judge r1 I5 (cab_pro_aero25_0405_seatbacks): the shell's top edge runs nearly HORIZONTAL at ~45 % of the
    # back height (round corners), not an arch up to the shoulders; the map pocket is black mesh under a grey leather
    # flap (the flap 4 mm proud of the mesh); the photo's round fitting at the lower outboard corner is left out (the
    # seat is at its 12k triangle budget)
    g = pillow(_outline_from_hw(-0.02, 0.42, lambda b: hwf(b, -0.035), 0.06, nb=8), 0.012, 0.005, 0.003, h=0.05)
    back.append(_mats(g.map(rmap(0.008)), M_CAB_SHELL))
    g = pillow(_outline_from_hw(0.03, 0.235, lambda b: hwf(b, -0.07), 0.03, nb=6), 0.012, 0.005, 0.003, h=0.06)
    back.append(_mats(g.map(rmap(0.004 - 0.006)), M_BLACK))
    g = pillow(_outline_from_hw(0.205, 0.30, lambda b: hwf(b, -0.066), 0.025, nb=4), 0.010, 0.004, 0.003, h=0.06)
    back.append(_mats(g.map(rmap(-0.008)), M_CAB_SHELL))
    # headrest (lowest position or raised by head_slide), front centre panel, dark rear insert, two posts
    hw_, hh_ = (float(v) for v in e["head_wh"])
    hup = float(e["head_slide"]) if raised else 0.0
    hcen = (float(e["head_top"]) + hup - 0.5 * hh_ - sh) / cb
    hmap = _back_map(db, nb, o=o)
    g = pillow(rrect(-0.5 * hw_, hcen - 0.5 * hh_, 0.5 * hw_, hcen + 0.5 * hh_, 0.055, max_len=0.05), 0.095, 0.03,
               0.03, h=0.035, crown=dome(0.006, 0.05))
    back.append(_mats(g.map(lambda V: hmap(V - [0, 0, 0.06])), M_CAB))
    hp = np.array([(-0.052, hcen - 0.5 * hh_ + 0.03), (0.052, hcen - 0.5 * hh_ + 0.03),
                   (0.078, hcen + 0.5 * hh_ - 0.03), (-0.078, hcen + 0.5 * hh_ - 0.03)])
    g = pillow(fillet(hp, 0.025), 0.016, 0.007, 0.004, h=0.03, crown=dome(0.003, 0.03))
    back.append(_mats(g.map(lambda V: hmap(V + [0, 0, 0.035 - 0.012 + 0.004])), M_CAB))
    g = pillow(rrect(-0.075, hcen - 0.5 * hh_ + 0.03, 0.075, hcen + 0.01, 0.03), 0.010, 0.004, 0.003)
    hrmap = _back_map(db, -nb, o=o)
    back.append(_mats(g.map(lambda V: hrmap(np.c_[-V[:, 0], V[:, 1], V[:, 2] + 0.06 - 0.006])), M_CAB_SHELL))
    for a in (-0.07, 0.07):                     # posts from inside the back up into the headrest (review r1 C5)
        p0 = o + (s_top - 0.07) * db - 0.03 * nb
        p1 = o + hcen * db - 0.03 * nb
        back.append(tube((p0[0], a, p0[1]), (p1[0], a, p1[1]), 0.008, M_METAL, n=10))
    # shoulder-belt guide at the top outboard corner (3-point restraint)
    gp = o + (s_top - 0.035) * db - 0.02 * nb
    back.append(rbox((gp[0], -si * (hwf(s_top - 0.035) - 0.01), gp[1]), (0.045, 0.026, 0.05), 0.008, M_BLACK,
                     R=np.array([[nb[0], 0, db[0]], [0, 1, 0], [nb[1], 0, db[1]]])))
    rec_deg = float(e["back_deg"] if recline is None else recline)
    geos += [g_.rot(tuple(o), rec_deg - float(e["back_deg"])) for g_ in back]

    # ---- the one armrest (aisle side): deep anthracite side panel, brushed seat control on its forward end
    a0, a1 = e["arm_u"]
    at, ah0 = float(e["arm_top"]), float(e["arm_h0"])
    s0, s1 = sorted((si * (W_ - aw), si * W_))
    geos.append(slab(rrect(a0, ah0, a1, at, 0.025, max_len=0.08), s0, s1, 0.016, M_CAB_DARK))
    cl, ch = e["arm_ctrl"]
    sa, sb = sorted((si * W_ - si * 0.004, si * W_ + si * 0.007))
    geos.append(slab(rrect(a1 - cl - 0.008, at - 0.025 - ch, a1 - 0.008, at - 0.025, 0.010), sa, sb, 0.003, M_METAL))

    # ---- lap belt: halves from the anchors at the cushion's rear corners, over the side panels and ACROSS the cushion
    #      (a third of its depth from the back, on its crown) to the buckle (P1046406 / 03: review r2 F9)
    if belts:
        z_at = lambda u, y: ((sh + 0.025) + slope * (u - u_r) + 0.008 * smoothstep(0.0, 0.08, cw - np.abs(y))  # noqa
                             + (0.010 * smoothstep(0.0, 0.03, cw - np.abs(y)) if abs(y) > 0.125 else 0.0))
        ub = 0.125
        buck = np.array([ub, si * 0.03, z_at(ub, 0.0) + 0.006])
        for sg in (-1, 1):
            ctrl = np.array([[-0.045, sg * (cw + 0.008), pt + 0.03], [0.00, sg * (cw + 0.006), z_at(0.0, cw) - 0.012],
                             [0.05, sg * (cw - 0.012), z_at(0.05, cw - 0.012) + 0.0025],
                             [0.10, sg * 0.15, z_at(0.10, 0.15) + 0.0025],
                             [ub - 0.004, sg * 0.07 + si * 0.02, z_at(ub, 0.07) + 0.0025], buck + [0, sg * 0.03, -0.003]])
            ups = np.array([[-0.2, sg * 0.9, 0.3], [-0.1, sg * 0.8, 0.6], [0, sg * 0.2, 1], [0, 0, 1], [0, 0, 1],
                            [0, 0, 1]])
            geos.append(ribbon(ctrl, ups, 0.046, M_HARN))
        geos.append(rbox(buck + [0, 0, 0.001], (0.050, 0.068, 0.010), 0.004, M_METAL))

    # ---- place: seat-local (u fwd, s = y offset, v above the floor) -> model
    srp = rec["srp"]
    out = [g_.map(lambda V: np.c_[srp[0] + fx * V[:, 0], float(rec["bl"]) + V[:, 1], fl + V[:, 2]]) for g_ in geos]
    return to_meshes(out)


def cabin_tracks(x0=None, x1=None):
    """The four surface-mounted cabin seat tracks (SEAT_TRACKS: BL +/-bl, width w, height h) from x0 to x1 (default
    the table's x0 .. x1), with the dark slot of locating holes along their tops.  Not part of cabin_seat()."""
    st = I.SEAT_TRACKS
    x0 = float(st["x0"] if x0 is None else x0)
    x1 = float(st["x1"] if x1 is None else x1)
    fl = float(I.FLOOR["wl"])
    h, w = float(st["h"]), float(st["w"])
    gs = []
    for b in st["bl"]:
        for sg in (-1, 1):
            gs.append(cbox((0.5 * (x0 + x1), sg * float(b), fl + 0.5 * h), (x1 - x0, w, h), M_RAIL))
            gs.append(cbox((0.5 * (x0 + x1), sg * float(b), fl + h + 0.0004), (x1 - x0 - 0.02, 0.35 * w, 0.001),
                           M_BLACK))
    return to_meshes(gs)


# =====================================================================================================================
# hinges (for kinematic parts: the builders above bake the pose in)
# =====================================================================================================================
def crew_hinges(side=-1, dx=0.0, dz=0.0, recline=0.0):
    """Model-coordinate hinge axes of a crew seat pose: {'recline': back about the SRP, 'arm_in' / 'arm_out': armrest
    hinges on the back sides (positive rotation flips the arm up), 'travel': fore / aft track direction}; each
    (origin (3,), axis (3,)) with the axis unit vector."""
    c = I.CREW_SEAT
    srp = I.crew_srp(side, dx, dz)
    ah, ar = float(c["arm_h"]), 0.0225
    piv = np.array([-(ah - ar) * math.tan(math.radians(c["back_deg"])) + c["arm_pivot"], ah - ar])
    a = math.radians(recline)
    piv = np.array([piv[0] * math.cos(a) - piv[1] * math.sin(a), piv[0] * math.sin(a) + piv[1] * math.cos(a)])
    W_ = 0.5 * float(c["width"])
    axis = np.array([0.0, 1.0, 0.0])            # seat-local CCW in (u, v) = back / arm going aft-up: +y in model
    out = {"recline": (srp.copy(), axis), "travel": (srp.copy(), np.array([1.0, 0.0, 0.0]))}
    for key, sg in (("arm_in", -side), ("arm_out", side)):
        out[key] = (np.array([srp[0] - piv[0], srp[1] + sg * W_, srp[2] + piv[1]]), axis)
    return out


# =====================================================================================================================
# convenience
# =====================================================================================================================
def all_seats(layout=None, **kw):
    """{seat id: [(Mesh, material)]}: both crew seats (neutral) and every cabin seat of the layout (TTL)."""
    layout = layout or I.DEFAULT_LAYOUT
    out = {"PILOT": crew_seat(-1, **kw), "CO-PILOT": crew_seat(+1, **kw)}
    for s in I.SEAT_LAYOUTS[layout]["seats"]:
        if s.get("kind") != "commuter":
            out[s["id"]] = cabin_seat(s["id"], layout)
    return out


def tri_count(meshes):
    return int(sum(m.nf for m, _ in meshes))


def part_id(seat_id):
    return "seat_" + seat_id.lower().replace(" ", "").replace("-", "")


def build(parts, layout=None):
    """Optional: one Part per seat (ids seat_pilot, seat_copilot, seat_pax1 ..), group Interior."""
    from model.parts import Part
    layout = layout or I.DEFAULT_LAYOUT
    for sid, ms in all_seats(layout).items():
        crew = sid in ("PILOT", "CO-PILOT")
        p = Part(part_id(sid), f"{'Crew' if crew else 'Executive'} seat {sid}", "interior", group="Interior",
                 material_note=("IPECO 3A318-type crew seat, 4-point harness, sheepskin covers" if crew else
                                "PRO executive seat: leather, swivel base on the tracks, one aisle armrest"),
                 info={"seat": sid, "layout": layout, "table": "interior.CREW_SEAT" if crew else "interior.EXEC_SEAT"})
        for m, mat in ms:
            p.add(m, mat)
        parts[p.id] = p
    return parts
