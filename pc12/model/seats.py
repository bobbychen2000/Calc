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
M_STITCH = "stitch_thread"              # tone-on-tone top-stitching (exec seats: all-lens review r1 CAB1-02)
M_METAL, M_RAIL, M_WHITE, M_BLACK = "metal", "metal_dark", "paint_white", "seat_base_black"

# sheepskin pads [E, review r1 F3: the fleece is the PRO crew seat's signature, thick and rolled over the edges]:
# pad thickness at its edge, crown on top of it (seat pad: the two thigh domes; back), edge roll radii top / bottom,
# lumpiness (tufts: a coarse geometric wave + the fine fleece bump of the render material, review r2 F4), run-on wrapped
# round the cushion front and over the back top.  The crowned outer face is the DRAWN outline (CREW_SEAT sheepskin_t
# inside cushion_t and the back's front offset, review r2 M1): the leather cushion / back front lie sheepskin_t inside
# it, the pad's bottom sinks into the leather by whatever the pad's loft exceeds sheepskin_t.
# (flight deck fix FDY r2, FDY-O2-01: the pads read as flat-topped slabs with near-vertical sides -- P1046408 / 09 / 10
# show puffy loaves: the crown 16 / 12 -> 24 / 18 mm, reached over SK_CROWN_R 75 mm from the edge, the top roll 17 -> 22
# mm; the apex stays ON the drawn cushion top / back front.  An 85 mm rise put the thigh pads' rear 10 mm under the
# drawn cushion top at consistency_2d3d's pan bins (its 10 mm tolerance): at 75 mm ~6.5 mm)
SK_T, SK_CROWN_SEAT, SK_CROWN_BACK = 0.034, 0.024, 0.018
SK_CROWN_R = (0.075, 0.075)                    # the crown's rise from the edge: seat, back
# the pads keep their bottoms where the 16 / 12 mm crowns had them (the edge 8 / 6 mm thinner): the pad sinks `sink`
# into the leather and is wrapped round its front roll / the back's top about an axis `sink - roll` above its bottom --
# sunk deeper than the roll radius its lowest rows wrapped through the axis (inside out: a coplanar sliver on the
# leather, fit_check 26)
SK_T_SEAT, SK_T_BACK = SK_T - (SK_CROWN_SEAT - 0.016), SK_T - (SK_CROWN_BACK - 0.012)
SK_ROLL, SK_ROLL_B, SK_FLUFF, SK_LUMP = 0.022, 0.012, 0.0022, 0.0030
SK_ROLL_SEAT = SK_ROLL * min(1.0, SK_T_SEAT / (SK_ROLL + SK_ROLL_B))      # pillow() scales both rolls to the thickness
SK_LUMP_K = (48.0, 71.0, 105.0, 150.0)          # tuft waves (rad/m): 4-13 cm lumps, visible at the panel camera
SK_WRAP_SEAT, SK_WRAP_BACK = 0.012, 0.050     # run-on past the cushion front / the back top: ~100 deg of wrap
SK_SPLIT = 0.010                               # gap between the two thigh-pad sleeves along the seat CL
SK_FRONT = 0.022                               # the leather cushion's front sits this far behind the drawn front
SK_TOP = 0.020                                 # the back shell's top sits this far below the drawn top (fleece over it)
# flight deck fix r5 (FDO4-01 / FID-FD4-01: the clumps and the fringe drew a lumpy, chipped outline -- "broken rock"; the
# photos' pile ends in a soft ROLLED edge): the rim bulges SK_ROLL_OUT out (full at its middle rows, half at the top /
# bottom edge rows -- an over-hanging roll of pile) plus a low soft wave of SK_WAVE at 4-8 cm (SK_WAVE_K); the fine
# fringe and the 33-57 mm clumps are gone, the rims sampled every SK_RIM_STEP
SK_ROLL_OUT, SK_WAVE, SK_WAVE_K, SK_RIM_STEP = 0.007, 0.0018, (80.0, 115.0, 150.0), 0.010
# flight deck fix FDY r1 (FDY-O1-01 / FIDY1-02: the rolled rims kept a hard, smooth CAD outline -- the photos' cushions
# end in a soft, irregular edge of locks): a low FRINGE over the roll, SK_FRINGE (0 .. 4.2 mm out) of a lumpy noise at
# 17-27 mm (SK_FRINGE_K rad/m) that also varies round the roll (row phase SK_FRINGE_ROW), so the outline breaks into
# soft locks without the r3 clumps' chipped-rock steps (33-57 mm, up to 12 mm); the rims sampled every SK_RIM_STEP_F
# (7.2 mm: about three samples a lock; 5 / 6.5 mm put the crew seat over its 66.3k triangle cap)
SK_FRINGE, SK_FRINGE_K, SK_FRINGE_ROW, SK_RIM_STEP_F = 0.0042, (230.0, 300.0, 370.0), 0.006, 0.0072
HARN_CROWN = 0.0012                            # the harness webbing's crown across its width (ribbon)


def shag(seed):
    """Outward displacement (m) of a sheepskin pad's rim at outline points (a, b) (row r of the rim, 0 .. 1 from the
    bottom edge to the top one): the rolled edge (SK_ROLL_OUT), its soft wave (0 .. SK_WAVE) and the fringe of locks
    (0 .. SK_FRINGE)."""
    f = fleece(1.0, seed, k=SK_WAVE_K)
    g = fleece(1.0, seed + 101, k=SK_FRINGE_K)

    def w(a, b, r=0.5):
        o = SK_FRINGE_ROW * (r - 0.5)
        lock = 0.5 + 0.5 * np.tanh(2.2 * g(np.asarray(a) + o, np.asarray(b) - 0.7 * o))
        return SK_ROLL_OUT + SK_WAVE * (0.5 + 0.5 * np.tanh(1.5 * f(a, b))) + SK_FRINGE * lock ** 1.5
    return w


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

    def __init__(self, V, F, pid, mats, sheet=False):
        self.V = np.asarray(V, float)
        self.F = np.asarray(F, np.int64)
        self.pid = np.asarray(pid, np.int64)
        self.mats = mats if isinstance(mats, dict) else {int(p): mats for p in np.unique(self.pid)}
        self.sheet = sheet          # an open sheet built facing out (stitch dashes): no signed-volume flip in meshes()

    def map(self, fn):
        F = self.F
        if self.sheet and len(self.V):             # a mirroring map turns a sheet's faces inside out: re-wind them
            c = self.V.mean(0)
            X = fn(np.vstack([c, c + [1e-4, 0, 0], c + [0, 1e-4, 0], c + [0, 0, 1e-4]]))
            if np.linalg.det((X[1:] - X[0]).T) < 0:
                F = F[:, ::-1]
        return Geo(fn(self.V), F, self.pid, self.mats, self.sheet)

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
        return Geo(V, self.F, self.pid, self.mats, self.sheet)

    def meshes(self):
        """[(Mesh, material)] with outward orientation (signed volume) and normals from the final positions."""
        V, F, pid = self.V, self.F, self.pid
        v0, v1, v2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
        ok = np.linalg.norm(np.cross(v1 - v0, v2 - v0), axis=1) > 1e-14
        F, pid = F[ok], pid[ok]
        vol = float(np.einsum("ij,ij->i", V[F[:, 0]], np.cross(V[F[:, 1]], V[F[:, 2]])).sum())
        if vol < 0 and not self.sheet:
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
           seams=None, shag=None):
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
    if shag is not None:
        # the pile's edge (flight deck r1 GEOM B, B7; fix r5: a rolled edge, `shag`): full at the rim's outermost
        # rows, half at the top / bottom edge rows -- not band-limited (the judged-grid limit of `fluff` keeps applying
        # to the face's inner waves)
        R_ = len(rows)
        prof = [0.5 + 0.5 * math.sin(math.pi * k / max(R_ - 1, 1)) for k in range(R_)]
        rows = [(P2 + (pk * shag(Q[:, 0], Q[:, 1], k / max(R_ - 1, 1)))[:, None] * N, c)
                for k, ((P2, c), pk) in enumerate(zip(rows, prof))]
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


def ribbon(ctrl, up, width, mat, th=0.0035, n=20, rounded=False, crown=0.0):
    """Webbing strap through the control points ctrl (k, 3) lying flat with its face normal along up (k, 3) (the
    surface under it): a thin closed box section swept along a Catmull-Rom path, crisp edges; rounded: the long edges
    rounded (a six-sided section, each side's two chamfers smooth-shaded: review r3 K1).  crown (m, rounded only): the
    outer face bulges this much at the middle across the width, a parabola over 6 strips (FDY r1 FDY-O1-06: the flat
    ribbons read as hard CAD strips beside the fleece; woven webbing crowns over its edge cords).  n=None: ctrl / up
    are already dense, taken as they are."""
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
        if crown > 0.0:                         # the outer face: 7 points across, a parabolic crown
            xs = np.linspace(-(hw - e), hw - e, 7)
            top_rows = tuple(P + W * x + U * (ht + crown * (1.0 - (x / (hw - e)) ** 2)) for x in xs)
        else:
            top_rows = (C[5], C[0])
        for rows in (top_rows, (C[0], C[1], C[2]), (C[2], C[3]), (C[3], C[4], C[5])):
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


# flight deck fix r3 (FID-FD3-05 / FDO3-06: from the cabin -- fd_cabin, the aisle -- the crew backs read as plain grey
# slabs; P1046406, the IPECO line art: a stitched, panelled leather back with a map pocket): on the shell's rear face a
# map pocket (a padded leather panel `pocket` = (b0, b1, half-width, thickness) along / across the back, its top edge an
# elastic welt), two vertical stitched seams at +-`seam_a` from the pocket up to `seam_top` below the shell top, and a
# stitched seam across the back above the pocket [E]
CREW_BACK_REAR = dict(pocket=(0.16, 0.40, 0.135, 0.0055), welt_r=0.0032, seam_a=0.105, seam_top=0.035, pitch=0.007)


def _ray_hits(geo, O, D):
    """Nearest positive hit distance of rays O + t D (n, 3) on the triangles of geo (Moller-Trumbore); inf for a miss."""
    T = geo.V[geo.F]
    e1, e2 = T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]
    out = np.full(len(O), np.inf)
    for i in range(len(O)):
        p = np.cross(D[i], e2)
        det = np.einsum("ij,ij->i", e1, p)
        ok = np.abs(det) > 1e-14
        inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
        tv = O[i] - T[:, 0]
        u = np.einsum("ij,ij->i", tv, p) * inv
        qv = np.cross(tv, e1)
        v = (qv @ D[i]) * inv
        t = np.einsum("ij,ij->i", e2, qv) * inv
        hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-6)
        if hit.any():
            out[i] = t[hit].min()
    return out


def _crew_back_rear(shell, db, nb, L_s):
    """[Geo] on the crew back shell's rear face (CREW_BACK_REAR), seat-local, upright (the caller reclines them)."""
    q = CREW_BACK_REAR
    D3 = np.array([nb[0], 0.0, nb[1]])

    def on_rear(a, b, lift):
        """Rear-face points at lateral a, along-back b (arrays, same shape), lifted `lift` off it (outward, -nb)."""
        a, b = np.broadcast_arrays(np.asarray(a, float), np.asarray(b, float))
        O = np.stack([b.ravel() * db[0] - 0.25 * nb[0], a.ravel(), b.ravel() * db[1] - 0.25 * nb[1]], 1)
        t = _ray_hits(shell, O, np.repeat(D3[None], len(O), 0))
        P = O + np.where(np.isfinite(t), t, 0.25)[:, None] * D3
        lift = np.broadcast_to(np.asarray(lift, float), a.shape).ravel()
        return (P - lift[:, None] * D3).reshape(a.shape + (3,))
    out = []
    # the map pocket: a padded panel (top: thickness x a smooth rise over its first 12 mm from the edge; bottom 1 mm in
    # the shell), closed by a wall strip
    b0, b1, hw, th = q["pocket"]
    na, nbb = 15, 11
    A, Bb = np.meshgrid(np.linspace(-hw, hw, na), np.linspace(b0, b1, nbb), indexing="ij")
    de = np.minimum.reduce([A + hw, hw - A, Bb - b0, b1 - Bb])
    top = on_rear(A, Bb, 0.0005 + (th - 0.0005) * smoothstep(0.0, 0.012, de))
    bot = on_rear(A, Bb, -0.001)
    n1, n2 = top.shape[:2]
    idx = lambda i, j, k: k * n1 * n2 + i * n2 + j                  # noqa: E731
    F = []
    for i in range(n1 - 1):
        for j in range(n2 - 1):
            for k, flip in ((0, False), (1, True)):
                a_, b_, c_, d_ = idx(i, j, k), idx(i + 1, j, k), idx(i + 1, j + 1, k), idx(i, j + 1, k)
                F += [(a_, c_, b_), (a_, d_, c_)] if flip else [(a_, b_, c_), (a_, c_, d_)]
    ring = [(i, 0) for i in range(n1 - 1)] + [(n1 - 1, j) for j in range(n2 - 1)] + \
        [(i, n2 - 1) for i in range(n1 - 1, 0, -1)] + [(0, j) for j in range(n2 - 1, 0, -1)]
    for k_ in range(len(ring)):
        (i0, j0), (i1, j1) = ring[k_], ring[(k_ + 1) % len(ring)]
        F += [(idx(i0, j0, 0), idx(i0, j0, 1), idx(i1, j1, 1)), (idx(i0, j0, 0), idx(i1, j1, 1), idx(i1, j1, 0))]
    V = np.vstack([top.reshape(-1, 3), bot.reshape(-1, 3)])
    out.append(Geo(V, np.array(F), np.zeros(len(F)), {0: "leather_black"}))     # a shade darker: two-tone
    # the elastic welt along the pocket's top edge (a dark webbing tube, half in the panel)
    aw = np.linspace(-hw + 0.004, hw - 0.004, 24)
    Pw = on_rear(aw, np.full(len(aw), b1 - 0.004), th - 0.0005)
    out.append(_tube_path(Pw, q["welt_r"], M_HARN))
    # stitched seams (closed boxes, 3.6 x 1.0 x 1.2 mm every `pitch`): two up the back from the pocket, one across
    st = []
    for a0 in (-q["seam_a"], q["seam_a"]):
        bs_ = np.arange(b1 + 0.02, L_s - q["seam_top"], q["pitch"])
        st.append((on_rear(np.full(len(bs_), a0), bs_, 0.0003), "b"))
    as_ = np.arange(-q["seam_a"], q["seam_a"], q["pitch"])
    st.append((on_rear(as_, np.full(len(as_), b1 + 0.02), 0.0003), "a"))
    bx = np.array([[0, 1, 2], [0, 2, 3], [4, 6, 5], [4, 7, 6], [0, 4, 5], [0, 5, 1], [1, 5, 6], [1, 6, 2],
                   [2, 6, 7], [2, 7, 3], [3, 7, 4], [3, 4, 0]])
    Vs, Fs = [], []
    dd3 = np.array([db[0], 0.0, db[1]])
    for P, kind in st:
        along = dd3 if kind == "b" else np.array([0.0, 1.0, 0.0])
        side = np.array([0.0, 1.0, 0.0]) if kind == "b" else -dd3       # (the same handedness: every box outward)
        for p_ in P:
            k_ = len(Vs)
            for c_ in (-0.0006, 0.0006):
                for e_ in ((0, -1), (1, -1), (1, 1), (0, 1)):
                    Vs.append(p_ + e_[0] * 0.0036 * along + e_[1] * 0.0005 * side - c_ * D3)
            Fs += (bx + k_).tolist()
    out.append(Geo(np.array(Vs), np.array(Fs), np.zeros(len(Fs)), {0: "stitch_thread"}))
    return out


def _tube_path(P, r, mat, n=8):
    """Closed round tube Geo along the polyline P (k, 3), capped."""
    P = np.asarray(P, float)
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    a = np.array([0.0, 0.0, 1.0]) if abs(T[0, 2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    U = np.cross(T, a)
    U /= np.linalg.norm(U, axis=1, keepdims=True)
    W = np.cross(T, U)
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
    R = P[:, None, :] + r * (np.cos(ang)[None, :, None] * U[:, None, :] + np.sin(ang)[None, :, None] * W[:, None, :])
    k, m = R.shape[:2]
    V = np.vstack([R.reshape(-1, 3), P[0], P[-1]])
    F = []
    for i in range(k - 1):
        for j in range(m):
            a_, b_ = i * m + j, i * m + (j + 1) % m
            F += [(a_, b_, b_ + m), (a_, b_ + m, a_ + m)]
    c0, c1 = k * m, k * m + 1
    for j in range(m):
        F += [(c0, (j + 1) % m, j), (c1, (k - 1) * m + j, (k - 1) * m + (j + 1) % m)]
    return Geo(V, np.array(F), np.zeros(len(F)), {0: mat})


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
        sink = SK_T_SEAT - (top_c - (t0 - sk_t))
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
            g = pillow(pp, SK_T_SEAT, SK_ROLL, SK_ROLL_B, h=_sk_h(0.016), crown=dome(SK_CROWN_SEAT, SK_CROWN_R[0]),
                       fluff=lambda a, b: lump(a, b) + fine(a, b), shag=shag(21 + sg_), max_len=SK_RIM_STEP_F)
            g = g.map(lambda V: _wrap(V, 0, D - SK_FRONT - rl, rl + 0.002, sink + 0.002))
            geos.append(_mats(g.map(lambda V: pan_map(top_c)(V, SK_T_SEAT)), M_SHEEP))
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
    back += _crew_back_rear(back[-1], db, nb, L_s)
    bmap = _back_map(db, nb, front=_crew_front)
    if sk:
        # back cover: down the whole front and wrapped over the top edge toward the rear (AOPA, P1046408 / 10), the
        # shell's front-top roll (r 0.018) as the roll; the crowned, lumpy face on the drawn front (review r2 M1)
        apex = SK_T_BACK + SK_CROWN_BACK + SK_LUMP
        sink_b = apex - sk_t                                  # the pad bottom into the shell front
        Rb = 0.018 + 0.002
        ol = _outline_from_hw(0.035, L_s - 0.018 + 1.9 * Rb,
                              lambda b: _crew_back_hw(np.minimum(b, L_s - 0.004), 0.004), 0.03)
        lump = fleece(SK_LUMP, 12, k=SK_LUMP_K)
        fine = fleece(SK_FLUFF, 2, k=(95.0, 120.0, 170.0), h_judged=0.021)
        g = pillow(ol, SK_T_BACK, SK_ROLL, SK_ROLL_B, h=_sk_h(0.021), crown=dome(SK_CROWN_BACK, SK_CROWN_R[1]),
                   fluff=lambda a, b: lump(a, b) + fine(a, b), shag=shag(25), max_len=SK_RIM_STEP_F)
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
    hfn = lambda V: hmap(np.c_[V[:, 0], V[:, 1], V[:, 2] - (ht - 0.035) + wing(V[:, 0])])   # noqa: E731
    back.append(_mats(g.map(hfn), M_CREW, M_SHELL, M_SHELL))
    # flight deck fix r2 (FDO2-09: plain off-white slabs): the front's perimeter piping -- an anthracite welt (r 2.2 mm)
    # along the crest where the face rolls into the rim -- and a horizontal stitch seam across the face at 40 % of its
    # height (IPECO line art; P1046406 / 10: a piped front panel) [E]
    Qh = _ccw(_subdivide(np.asarray(hol, float), 0.010))
    Bh = Qh - 0.03 * _normals2(Qh)
    Nh = _normals2(Qh)
    th_ = np.linspace(0.0, 2 * np.pi, 8, endpoint=False)
    Vp = np.vstack([np.c_[Bh + 0.0022 * math.cos(t_) * Nh, np.full(len(Bh), ht - 0.0004 + 0.0022 * math.sin(t_))]
                    for t_ in th_])
    nq, mq = len(Bh), len(th_)
    ii, jj = np.meshgrid(np.arange(nq), np.arange(mq), indexing="ij")
    a_, b_ = jj * nq + ii, jj * nq + (ii + 1) % nq
    c_, d_ = ((jj + 1) % mq) * nq + (ii + 1) % nq, ((jj + 1) % mq) * nq + ii
    Fp = np.vstack([np.c_[a_.ravel(), b_.ravel(), c_.ravel()], np.c_[a_.ravel(), c_.ravel(), d_.ravel()]])
    back.append(Geo(Vp, Fp, np.zeros(len(Fp)), {0: M_SHELL}).map(hfn))
    bs_ = hc - 0.5 * hh + 0.40 * hh
    us_ = np.arange(-0.5 * hwid + 0.045, 0.5 * hwid - 0.045, 0.006)
    ds_ = -sdf2d.polygon(us_, np.full(len(us_), bs_), Bh)
    zs_ = ht + dome(0.006, 0.05)(us_, bs_, np.maximum(ds_, 0.0)) + 0.0004
    Vs, Fs = [], []
    bx = np.array([[0, 1, 2], [0, 2, 3], [4, 6, 5], [4, 7, 6], [0, 4, 5], [0, 5, 1], [1, 5, 6], [1, 6, 2],
                   [2, 6, 7], [2, 7, 3], [3, 7, 4], [3, 4, 0]])        # a closed box (Geo.meshes orients by volume)
    for u_, z_ in zip(us_, zs_):
        k_ = len(Vs)
        Vs += [(u_, bs_ - 0.0005, z_ - 0.0006), (u_ + 0.0036, bs_ - 0.0005, z_ - 0.0006),
               (u_ + 0.0036, bs_ + 0.0005, z_ - 0.0006), (u_, bs_ + 0.0005, z_ - 0.0006),
               (u_, bs_ - 0.0005, z_ + 0.0006), (u_ + 0.0036, bs_ - 0.0005, z_ + 0.0006),
               (u_ + 0.0036, bs_ + 0.0005, z_ + 0.0006), (u_, bs_ + 0.0005, z_ + 0.0006)]
        Fs += (bx + k_).tolist()
    back.append(Geo(np.array(Vs), np.array(Fs), np.zeros(len(Fs)), {0: "stitch_thread"}).map(hfn))
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
                cc = top_c + SK_T_SEAT + float(dome(SK_CROWN_SEAT, SK_CROWN_R[0])(a, b, d)) + float(lump(a, b) + fine(a, b))
                cc -= SK_ROLL_SEAT - math.sqrt(max(SK_ROLL_SEAT ** 2 - max(SK_ROLL_SEAT - d, 0.0) ** 2, 0.0))
            else:
                cc = t0 - sk_t
            cc -= SK_T_SEAT
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
            Rq = np.array([[nb[0], 0, db[0]], [0, 1, 0], [nb[1], 0, db[1]]])
            # cam-lock adjuster (flight deck r1 GEOM B, B7): a black moulded frame, its satin cam bar across
            back.append(rbox((q[0], sg * 0.049, q[1]), (0.012, 0.058, 0.032), 0.004, M_BLACK, R=Rq))
            # (flight deck fix r2 FDO2-09: plain block buckles) a chrome face plate on the frame's front
            qf = q + 0.0060 * nb - 0.003 * db
            back.append(rbox((qf[0], sg * 0.049, qf[1]), (0.0016, 0.046, 0.020), 0.0007, "chrome_trim", R=Rq))
            qb = q + 0.0065 * nb + 0.004 * db
            back.append(tube((qb[0], sg * 0.049 - 0.024, qb[1]), (qb[0], sg * 0.049 + 0.024, qb[1]), 0.0028, M_METAL,
                             n=8))
            # shoulder-strap guide on the back top (the straps leave the reel slot through it)
            qg = (L_s - 0.030) * db + (n_s + 0.004) * nb
            back.append(rbox((qg[0], sg * 0.060, qg[1]), (0.020, 0.064, 0.016), 0.005, M_BLACK, R=Rq))

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
            geos.append(ribbon(Ps, Us, 0.046, M_HARN, n=None, rounded=True, crown=HARN_CROWN))
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
            geos.append(ribbon(Pb, Ub, 0.046, M_HARN, th=0.002, n=None, rounded=True, crown=HARN_CROWN))
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
        geos.append(ribbon(Pc, Uc, 0.040, M_HARN, n=None, rounded=True, crown=HARN_CROWN))
        nrm = _unit3([0.25, 0.0, 0.97])
        # rotary buckle (flight deck r1 GEOM B, B7): black body, thin satin rim, a ridged black turn knob, the four
        # strap tongues entering it
        geos.append(tube(buckle - 0.008 * nrm, buckle + 0.007 * nrm, 0.034, M_BLACK, n=24))
        geos.append(tube(buckle + 0.0055 * nrm, buckle + 0.0085 * nrm, 0.0355, M_METAL, n=24))
        geos.append(tube(buckle + 0.007 * nrm, buckle + 0.015 * nrm, 0.021, M_BLACK, n=16))
        t1_ = _unit3(np.cross(nrm, [0.0, 1.0, 0.0]))
        t2_ = _unit3(np.cross(nrm, t1_))
        for k in range(8):                                          # grip ridges round the knob
            a_ = 2 * math.pi * k / 8
            d_ = math.cos(a_) * t1_ + math.sin(a_) * t2_
            geos.append(cbox(buckle + 0.0115 * nrm + 0.020 * d_, (0.004, 0.004, 0.008), M_BLACK,
                             R=np.stack([d_, np.cross(nrm, d_), nrm], 1)))
        geos.append(tube(buckle + 0.0148 * nrm, buckle + 0.0152 * nrm, 0.006, M_METAL, n=12))
        for a_ in (math.radians(35), math.radians(145), math.radians(215), math.radians(325)):
            d_ = math.cos(a_) * t2_ + math.sin(a_) * t1_
            c_ = buckle + 0.037 * d_ - 0.001 * nrm
            geos.append(cbox(c_, (0.016, 0.022, 0.003), M_METAL, R=np.stack([d_, np.cross(nrm, d_), nrm], 1)))

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
                            (u1 - u0 - 0.02, 0.12 * tw, 0.001), M_BLACK))
            # locating holes at the POH 0.69-in notch pitch along the slot (flight deck r1 GEOM B, B7)
            for xh in np.arange(srp0[0] - u1 + 0.018, srp0[0] - u0 - 0.012, float(c["notch"])):
                out.append(cbox((xh, srp0[1] + sg * ry, fl + th + 0.0006), (0.009, 0.42 * tw, 0.0012), M_BLACK))
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


# executive-seat upholstery detail (all-lens review r1 CAB1-02, P1046403 / 04 / 05 / 06: a plump crowned cushion with a
# rolled front edge whose leather apron hangs over the recessed legrest top -- a shadow line between them --, piping
# along the cushion's top edge and the back's front edge, double top-stitching beside the V seams; the r4 cushion,
# drape and legrest read as one tall white box with a flat top).  All inside the drawn L6 outlines.
#   EXEC_CUSH  crown (m, reached crown_r inside the top face's edge; the crown's top stays where the 8 mm crown had it,
#              the rim drops by crown - 0.008), roll / roll_b the top / bottom edge radii, apron (how far the front
#              apron hangs below the cushion bottom over the legrest's face, forward-facing seats) and its thickness
#   EXEC_WELT  piping welt radius;  EXEC_STITCH pitch, dash length, dash width, inset from a panel's top-face edge
EXEC_CUSH = dict(crown=0.022, crown_r=0.14, roll=0.055, roll_b=0.030, apron=0.024, apron_t=0.011)
EXEC_WELT = 0.003
EXEC_STITCH = (0.0065, 0.0038, 0.0009, 0.0045)
# all-lens review r2 CAB2-01 (P1046402 / 03 / 04 / 06 / 0405): the r1 seams were 8 mm gaps between panels rounded r 12
# -- wide grey channels -- and the stitching a dark dotted line; the photos show thin tone-on-tone creases, a plump
# separate headrest, shoulder wings and a cushion roll overhanging a set-back legrest.
#   EXEC_SEAM   the gap between two back / cushion panels (a crease), the panels' top-edge radii along it (back
#               centre, lumbar, bolster / wing, cushion side panel) and how deep the back's panels sink into the slab
#               (centre, bolsters, lumbar: their edges 2 / 6 / 3 mm proud of its front -- flush, the lumbar panel's rim
#               z-fought the slab's face)
#   EXEC_WING   the side bolsters run on up to the back's top as shoulder WINGS: their width at and above the V's end
#               (80 % of the back), the extra crown they gain over the upper back (standing that much prouder of the
#               centre panel at the shoulders), the band (fractions of the back length) over which it rises
#   EXEC_HEAD   the headrest a separate plump pillow: front / rear edge radii, crown and its reach, the horizontal seam
#               (welt radius, its height from the top as a fraction of the headrest)
#   EXEC_GAP    the forward-facing seats' shadow gap under the cushion roll (EXEC_SEAT legrest_gap): the dark strip
#               in it, its set-back behind the legrest face and its depth (the face sits EXEC_SEAT legrest[2] behind
#               the cushion front)
EXEC_SEAM = dict(gap=0.0010, r_centre=0.011, r_lumbar=0.009, r_bolster=0.013, r_side=0.018, sink=0.014, sink_b=0.017,
                 sink_l=0.013)
EXEC_WING = dict(w=0.046, crown=0.012, crown0=0.010, rise=(0.50, 0.80))
EXEC_HEAD = dict(r=0.036, rb=0.040, crown=0.020, crown_r=0.080, seam_r=0.0022, seam_at=0.34)
EXEC_GAP = dict(back=0.010, depth=0.040)
# all-lens review r3 CAB3-01 (P1046402 / 03 / 04 / 06): from 0.5-1.5 m the r2 back still read as a flat sheet with its
# panels drawn on (bolsters 6 mm, centre 2 mm proud of the slab, crowned 7-8 mm, edge radii 6-8 mm) and the cushion as a
# tray framed by welts: the photos' backs are sculpted -- the side bolsters / shoulder wings stand ~20 mm proud of the
# centre panel and roll over on 14 mm radii, the centre and lumbar panels puffed --, the cushion a plump loaf.  The panels'
# crowns: (rise, reach inside the panel's edge) for the back's centre / lumbar panel, the bolsters' rise reach
EXEC_PANEL_CROWN = dict(centre=(0.013, 0.09), lumbar=(0.012, 0.05), bolster_r=0.045)
M_STITCH_EXEC = "stitch_light"          # tone-on-tone thread on the exec leather (CAB2-01; stitch_thread read black)


def _round_path(Q, t, r, ang_deg=45.0, out=0.0):
    """Points (n, 3) in pillow coordinates (a, b, c) on a pillow's top round (outline Q CCW, thickness t, top radius r)
    at ang_deg up from its side, `out` along the round's normal; and the normals (n, 3)."""
    N = _normals2(Q)
    ph = math.radians(ang_deg)
    P = np.c_[Q - r * N + (r + out) * math.cos(ph) * N, np.full(len(Q), t - r + (r + out) * math.sin(ph))]
    return P, np.c_[math.cos(ph) * N, np.full(len(Q), math.sin(ph))]


def _open_run(Q, keep):
    """The longest cyclic run of outline points where keep is True, as an open polyline index array."""
    k = np.asarray(keep, bool)
    if k.all():
        return np.r_[np.arange(len(k)), 0]
    s0 = int(np.argmin(k))                                       # start after a False
    idx = (np.arange(len(k)) + s0) % len(k)
    runs, cur = [], []
    for i in idx:
        if k[i]:
            cur.append(i)
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    return np.array(max(runs, key=len)) if runs else np.zeros(0, int)


def _welt(P3, mat, r=None, n=6):
    """Piping welt: a round tube along the open polyline P3 (seat-local, after mapping)."""
    r = EXEC_WELT if r is None else r
    if len(P3) < 2:
        return None
    return _tube_path(P3, r, mat, n=n)


def _stitches(P, D, Nrm, mat):
    """Stitch dashes: flat quads at points P (k, 3) along unit directions D, lying on normals Nrm, EXEC_STITCH sized,
    as one Geo (seat-local)."""
    _, ln, w, _ = EXEC_STITCH
    S = np.cross(Nrm, D)
    S /= np.maximum(np.linalg.norm(S, axis=1, keepdims=True), 1e-12)
    V, F = [], []
    for i in range(len(P)):
        c = P[i] + 0.0004 * Nrm[i]
        a, b = 0.5 * ln * D[i], 0.5 * w * S[i]
        k = len(V)
        V += [c - a - b, c + a - b, c + a + b, c - a + b]
        F += [(k, k + 1, k + 2), (k, k + 2, k + 3)]
    if not F:
        return None
    # (all-lens review r2 CAB2-01: an open set of dashes has no signed volume -- Geo.meshes flipped ~2/3 of them inward,
    # and the interior bake then traced their occlusion / window light into the seat: dark dots on the light leather)
    return Geo(np.array(V), np.array(F), np.zeros(len(F)), {0: mat}, sheet=True)


def _edge_samples(Q, pitch):
    """Points every `pitch` along the closed outline Q, their unit tangents and their running index (float)."""
    Q2 = np.vstack([Q, Q[:1]])
    seg = np.linalg.norm(np.diff(Q2, axis=0), axis=1)
    s = np.r_[0.0, np.cumsum(seg)]
    t = np.arange(0.5 * pitch, s[-1], pitch)
    P = np.c_[np.interp(t, s, Q2[:, 0]), np.interp(t, s, Q2[:, 1])]
    T = np.c_[np.interp(t + 1e-4, s, Q2[:, 0]) - np.interp(t - 1e-4, s, Q2[:, 0]),
              np.interp(t + 1e-4, s, Q2[:, 1]) - np.interp(t - 1e-4, s, Q2[:, 1])]
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-12)
    return P, T


def _pillow_stitches(outline, t, r, crown, mapfn, keep, mat, eps=1e-4):
    """Top-stitching on a pillow's top face, EXEC_STITCH[3] inside its edge (outline CCW, top radius r, crown fn),
    where keep(a, b) -- mapped by mapfn (pillow -> seat-local); the dashes follow the mapped surface (finite
    differences of mapfn for the direction / normal)."""
    pitch, _, _, inset = EXEC_STITCH
    Q = _ccw(np.asarray(outline, float))
    Qi = Q - (r + inset) * _normals2(Q)
    P2, T2 = _edge_samples(Qi, pitch)
    ok = keep(P2[:, 0], P2[:, 1])
    if not ok.any():
        return None
    P2, T2 = P2[ok], T2[ok]
    c = t + (crown(P2[:, 0], P2[:, 1], np.full(len(P2), inset)) if crown is not None else 0.0)
    A = np.c_[P2, c]
    X = mapfn(A)
    Xa = mapfn(A + np.c_[eps * T2, np.zeros(len(A))])
    Xn = mapfn(A + np.c_[np.zeros((len(A), 2)), np.full(len(A), eps)])
    D = Xa - X
    D /= np.maximum(np.linalg.norm(D, axis=1, keepdims=True), 1e-12)
    Nr = Xn - X
    Nr /= np.maximum(np.linalg.norm(Nr, axis=1, keepdims=True), 1e-12)
    return _stitches(X, D, Nr, mat)


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
    cush = rrect(-0.05, -cw, sf, cw, 0.06, max_len=0.05)      # (CAB3-01: corners r 50 -> 60 for the 55 roll)
    tc = ctop - (pt - 0.01)
    kc = EXEC_CUSH
    t_c = tc - (kc["crown"] - 0.008)                  # the crown's top where the 8 mm crown had it (CAB1-02)
    crown_c = dome(kc["crown"], kc["crown_r"])
    g = pillow(cush, t_c, kc["roll"], kc["roll_b"], h=0.04, crown=crown_c)
    geos.append(_mats(g.map(cush_map(tc)), M_CAB))
    # piping along the cushion's top edge between the side panels (front) (CAB1-02)
    # (CAB3-01: dropped -- between the side panels it ended as a loose tube at both corners; the 55 mm roll carries the
    # edge)
    # raised side panels of the cushion (the V-stitch lines run on down the seat, photos), piped along their top edge
    # and top-stitched beside the seam to the centre (CAB1-02)
    for sg in (-1, 1):
        a0, a1 = (0.125, cw + 0.003) if sg > 0 else (-cw - 0.003, -0.125)
        ol = rrect(-0.045, a0, sf + 0.002, a1, 0.035, max_len=0.05)
        crown_s = dome(0.012, 0.04)                     # (CAB3-01: 8 mm over 30)
        # (CAB2-01: the top round r 33 -> EXEC_SEAM r_side: the joint with the centre a crease, not a channel)
        rsd = EXEC_SEAM["r_side"]
        g = pillow(ol, tc - 0.002, rsd, 0.012, h=0.04, crown=crown_s)
        geos.append(_mats(g.map(cush_map(tc, extra=0.004)), M_CAB))
        # (CAB3-01: no welt along the side panels' top edge -- with the front welt it framed the cushion as a tray)
        st = _pillow_stitches(ol, tc - 0.002, rsd, crown_s, cush_map(tc, extra=0.004),
                              lambda a, b, sg=sg: (np.abs(b) < 0.168) & (a > -0.01), M_STITCH_EXEC)
        if st is not None:
            geos.append(st)
    # soft front drape: the leather rolls over the cushion's front edge down onto the skirt (P1046402 / 03 [M], review
    # r1 F10), inside the drawn cushion front -- aft-facing seats.  Forward-facing seats (all-lens review r2 CAB2-01; r1
    # CAB1-02 hung an apron in front of the legrest top: cushion, apron and legrest read as one tall white box at the
    # P1046403 / 04 poses): the cushion's own rolled front (EXEC_CUSH roll_b 30) overhangs the legrest face, which sits
    # EXEC_SEAT legrest[2] = 28 behind the cushion front, and a dark strip lies in the crease between them (EXEC_GAP) --
    # the photos' shadow line under the cushion roll
    if lrest is not None:
        lw_ = float(e["legrest"][0])
        uf_ = float(lrest[:, 0].max())
        vt_ = float(lrest[:, 1].max())
        kg = EXEC_GAP                          # from inside the legrest's top up to 1 mm under the cushion bottom
        z_lo, z_hi = vt_ - 0.003, pt - 0.011
        geos.append(cbox((uf_ - 0.5 * (kg["depth"] + kg["back"]), 0.0, 0.5 * (z_lo + z_hi)),
                         (kg["depth"] - kg["back"], lw_ - 0.030, z_hi - z_lo), M_CAB_DARK))
    else:
        drape = fillet([(sf - 0.055, pt - 0.052), (sf - 0.006, pt - 0.040), (sf - 0.002, pt + 0.030),
                        (sf - 0.055, pt + 0.030)], [0.016, 0.022, 0.020, 0.016], max_len=0.03)
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
    # V-stitched front (P1046406 / 02 / 03, review r2 F1): a lumbar trapezoid low on the back, two seams leaving its top
    # corners and running straight up and out to ~80 % of the height (a clear V), the centre panel above.  All-lens review
    # r2 CAB2-01 (P1046402 / 03 / 04): the side bolsters run on up to the back's top as SHOULDER WINGS (EXEC_WING: W wide
    # from the V's end, crowned up to EXEC_WING crown prouder over the upper back), the panels meet in thin creases
    # (EXEC_SEAM gap 2.5, top radii 6-10: r1's 8 mm gaps between r 12 rounds read as grey channels), the lumbar panel and
    # the centre panel crowned (a lumbar bulge; the r1 back read as a flat shield), the stitching tone-on-tone
    ks, kw = EXEC_SEAM, EXEC_WING
    gap = ks["gap"]
    b0_, b_lum = 0.05, 0.185                                      # lumbar panel foot / top along the back [M]
    lum_bot, lum_top = 0.064, 0.078                               # its half-widths (a trapezoid) [M]
    b80 = 0.80 * s_top
    b_v = s_top - 0.040
    W_w = kw["w"]
    v80 = float(hwf(b80)) - 0.010 - W_w - gap

    def vin(b):
        """Half-width of the centre panel (the V seams): lum_top at the lumbar top, linear to the wing's inner edge at
        80 %, then along it (hw - 0.010 - W - gap) to the top."""
        b = np.asarray(b, float)
        t = np.clip((b - b_lum) / (b80 - b_lum), 0.0, 1.0)
        return np.minimum(lum_top + (v80 - lum_top) * t, hwf(b) - 0.010 - W_w - gap)
    # piping along the back's front edge (CAB1-02): on the slab's lateral round (r 0.03) at 45 deg, up both sides and
    # across the top (the outline a = +-hw(b) with its rounded top corners)
    rs_ = 0.03
    b_w = s_top - rs_ * (1.0 - math.sin(math.radians(45.0)))     # the top run: on the profile's front-top fillet (r 0.03)
    bq = np.linspace(0.06, b_w, 60)
    hq = hwf(bq) - rs_ * (1.0 - math.cos(math.radians(45.0))) + 0.4 * EXEC_WELT * math.cos(math.radians(45.0))
    cq = 0.02 - rs_ * (1.0 - math.sin(math.radians(45.0))) + 0.4 * EXEC_WELT * math.sin(math.radians(45.0))
    top_a = np.linspace(-0.6, 0.6, 9) * float(hq[-1])
    PwA = np.vstack([np.c_[-hq, bq][::-1], np.c_[top_a[1:-1], np.full(7, b_w)], np.c_[hq, bq]])
    bmap = _back_map(db, nb, o=o)
    back.append(_welt(bmap(np.c_[PwA, np.full(len(PwA), cq)])[:, [0, 1, 2]], M_CAB))
    # (the panels sink EXEC_SEAM sink into the slab: their edges 2 / 6 mm proud of its front face, so a seam is a shallow
    # crease, not a slot -- r1 stood them 8-14 mm proud, and the 2.5 mm gaps between them read as black lines)
    pmap = lambda V: fmap(V - [0, 0, ks["sink"]])                # noqa: E731
    pmap_b = lambda V: fmap(V - [0, 0, ks["sink_b"]])            # noqa: E731
    pmap_l = lambda V: fmap(V - [0, 0, ks["sink_l"]])            # noqa: E731
    # lumbar panel: a soft lumbar bulge (CAB2-01)
    g = pillow(fillet([(-lum_bot, b0_ + 0.004), (lum_bot, b0_ + 0.004), (lum_top, b_lum - 0.5 * gap),
                       (-lum_top, b_lum - 0.5 * gap)], [0.03, 0.03, 0.014, 0.014], max_len=0.04), 0.024,
               ks["r_lumbar"], 0.006, h=0.045, crown=dome(EXEC_PANEL_CROWN["lumbar"][0], EXEC_PANEL_CROWN["lumbar"][1]),
               n_round=2)
    back.append(_mats(g.map(pmap_l), M_CAB))
    # centre panel: the V from the lumbar top, then between the wings to the top
    bs = np.r_[np.linspace(b_lum + 0.5 * gap, b80, 9), np.linspace(b80 + 0.03, b_v, 4)]
    P = np.vstack([np.c_[vin(bs), bs], np.c_[-vin(bs[::-1]), bs[::-1]]])
    olc = fillet(P, np.r_[0.014, np.zeros(len(bs) - 2), 0.03, 0.03, np.zeros(len(bs) - 2), 0.014], max_len=0.05)
    crc = dome(*EXEC_PANEL_CROWN["centre"])
    g = pillow(olc, 0.026, ks["r_centre"], 0.006, h=0.045, crown=crc, n_round=2)
    back.append(_mats(g.map(pmap), M_CAB))
    st = _pillow_stitches(olc, 0.026, ks["r_centre"], crc, pmap,
                          lambda a, b: (b > b_lum + 0.01) & (b < b80 + 0.01), M_STITCH_EXEC)     # beside the V seams
    if st is not None:
        back.append(st)
    # side bolsters: raised, from beside the lumbar panel up along the V seam and on to the top as the shoulder wings,
    # their crown rising by EXEC_WING crown over the upper back (rise band)
    s_r0, s_r1 = kw["rise"][0] * s_top, kw["rise"][1] * s_top
    crb = lambda a, b, d: ((kw["crown0"] + kw["crown"] * smoothstep(s_r0, s_r1, b))   # noqa: E731
                           * smoothstep(0.0, EXEC_PANEL_CROWN["bolster_r"], d))
    vin_b = lambda b: np.where(b < b_lum, np.interp(b, [b0_, b_lum], [lum_bot, lum_top]), vin(b))   # noqa: E731
    for sg in (-1, 1):
        bs = np.r_[np.linspace(b0_ + 0.004, b80, 12), np.linspace(b80 + 0.035, b_v, 2)]
        inner, outer = vin_b(bs) + gap, hwf(bs, -0.010)
        Pb = np.vstack([np.c_[sg * inner, bs], np.c_[sg * outer[::-1], bs[::-1]]])
        rb_ = np.r_[0.016, np.full(len(bs) - 2, 0.0), 0.016, 0.016, np.full(len(bs) - 2, 0.0), 0.016]
        olb = fillet(Pb, rb_, max_len=0.05)
        g = pillow(olb, 0.032, ks["r_bolster"], 0.006, h=0.04, crown=crb, n_round=2)
        back.append(_mats(g.map(pmap_b), M_CAB))
        st = _pillow_stitches(olb, 0.032, ks["r_bolster"], crb, pmap_b,
                              lambda a, b: (np.abs(a) < vin_b(b) + 0.030) & (b > b0_ + 0.02) & (b < b80 + 0.01),
                              M_STITCH_EXEC)
        if st is not None:
            back.append(st)
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
    # headrest (lowest position or raised by head_slide), dark rear insert, two posts.  All-lens review r2 CAB2-01
    # (P1046402 / 03 / 0405): a separate PLUMP pillow -- front / rear edges rounded r 36 / 40, the face crowned 12 mm,
    # standing proud of the back's top -- with a horizontal seam a third down its face (a welt); r1's flat block with a
    # trapezoid inset read as a panel let into the back's top
    hw_, hh_ = (float(v) for v in e["head_wh"])
    hup = float(e["head_slide"]) if raised else 0.0
    hcen = (float(e["head_top"]) + hup - 0.5 * hh_ - sh) / cb
    hmap = _back_map(db, nb, o=o)
    kh = EXEC_HEAD
    th_, rr_ = 0.095, 0.055
    crh = dome(kh["crown"], kh["crown_r"])
    g = pillow(rrect(-0.5 * hw_, hcen - 0.5 * hh_, 0.5 * hw_, hcen + 0.5 * hh_, rr_, max_len=0.05), th_, kh["r"],
               kh["rb"], h=0.03, crown=crh)
    back.append(_mats(g.map(lambda V: hmap(V - [0, 0, 0.06])), M_CAB))
    # the seam: across the crowned face at seam_at of the height from the top, round the side rolls to 20 deg
    bseam = hcen + 0.5 * hh_ - kh["seam_at"] * hh_
    ax = 0.5 * hw_ - kh["r"]                                      # the face's flat half-width
    aa = np.linspace(-ax, ax, 25)
    dd = np.minimum(ax - np.abs(aa), (0.5 * hh_ - kh["r"]) - abs(bseam - hcen))
    out_ = 0.45 * kh["seam_r"]
    cc = th_ + crh(aa, np.full_like(aa, bseam), np.maximum(dd, 0.0)) + out_
    sideL, sideR = [], []
    for ph in np.radians(np.linspace(80.0, 20.0, 5)):
        c_ = th_ - kh["r"] + (kh["r"] + out_) * math.sin(ph)
        da = (kh["r"] + out_) * math.cos(ph)
        sideL.append((-ax - da, bseam, c_))
        sideR.append((ax + da, bseam, c_))
    Ps = np.vstack([np.array(sideL)[::-1], np.c_[aa, np.full_like(aa, bseam), cc], np.array(sideR)])
    back.append(_welt(hmap(Ps - [0, 0, 0.06]), M_CAB, r=kh["seam_r"], n=6))
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
