"""
Hidden-line-removal orthographic projector for the PC-12 loftkit model.

    from drawing import hlr
    views, prep = hlr.render_all()          # {'side'|'plan'|'front': ViewResult}
    for weight, P, part_idx in views["side"].lines: ...   # P = (n,2) view-plane metres

Pipeline
  1. Pose (wheel-well and nose-gear doors open by pivot["open"] deg, propeller + 5 blades
     turned 36 deg about the thrust line so one blade points down), drop hidden internals
     and decal-thin seal/seam meshes, merge each part's sub-meshes and weld them by
     position (KD-tree, 2 um) so livery colour boundaries vanish. The three fuselage
     sections are welded together so their production joints do not draw rings.
  2. Candidate edges per weld group: silhouettes (front/back facing change, with an exact
     edge-on dead zone for constant sections and cylinders seen end-on), boundary edges
     (window, door, panel, control-surface outlines) and creases (dihedral > 40 deg).
     Boundary edges lying on a smooth neighbouring loft panel of the same part (T-junction
     panel seams) are dropped.
  3. Depth buffer (2.5 mm/px) by numpy point splatting: every triangle is sampled on a
     barycentric grid whose density (k1 x k2, ~0.45 px spacing) is chosen from its
     projected size, triangles grouped by k and vectorised, np.minimum.at on a packed
     (depth | part id) key so a part-id buffer comes for free.
  4. Edges sampled every 0.7 px; a sample is visible if the buffer at its pixel is not
     nearer than a slope-aware tolerance (non-silhouettes), or either lateral probe at
     +-1.5 px is not nearer (outline side). Short visible runs are noise.
  5. Weight: OBJECT if the depth jumps beside the edge by more than the surface slope
     explains (an outline), else FINE. Window/door/seam lines are always FINE; fine
     feature loops seen at more than ~76 deg obliquity are dropped (slivers).
  6. The outline against empty background is also traced from the coverage mask
     (contourpy) as a low-priority gap filler, near-duplicate parallel lines are
     suppressed sample by sample in priority order, visible pieces are chained through
     shared vertices, collinear fragments bridged, and simplified (RDP, 0.3 px).

View conventions (proper rotations, no mirror images):
  SIDE  -- seen from port (left), nose LEFT : u = x,  v = z,  depth = +y
  PLAN  -- seen from above,       nose LEFT : u = x,  v = y (starboard UP), depth = -z
  FRONT -- seen from ahead                  : u = -y (starboard on the viewer's LEFT), v = z, depth = +x
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field

import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from cad.mesh import rotation_about  # noqa: E402

# ----------------------------------------------------------------------------
# configuration
# ----------------------------------------------------------------------------
EXCLUDE_STEPS = {"interior", "structure"}
EXCLUDE_IDS = {"firewall", "engine_mount", "inlet_duct", "gear_bays"}
# decal-thin surfaces (window seals 1.5 mm proud, door seams 0.8 mm, jamb liners): they only
# double the opening outlines and, seen obliquely, half-hide them -> left out of the HLR
EXCLUDE_MATERIALS = {"seal", "seal_cabin", "seam", "jamb"}
# parts that only occlude: the glazing panes are recessed behind the skin and run 10 mm past
# the openings, so their own boundaries are never visible; the openings in the skin draw
# the window outlines
OCCLUDE_ONLY = ("glazing",)
PROP_ORIGIN = (0.80, 0.0, 1.655)
PROP_TURN_DEG = 36.0            # puts one of the five blades straight down
WELD_GROUPS = {"fuselage": ("fus_fwd", "fus_center", "fus_aft")}   # welded together: no production-joint rings
WELD_TOL = 2e-6                 # m
CREASE_DEG = 40.0
SEAM_TOL = 1.0e-3               # m: boundary edges this close to a smooth neighbouring panel are loft seams

PX = 0.0025                     # m per pixel (2.5 mm)
SPLAT_STEP = 0.45               # px between splat samples
EDGE_STEP = 0.7                 # px between edge samples
SIDE_OFF = 1.5                  # px: lateral probe distance for the visibility / outline tests
TOL0 = 0.003                    # m: base depth tolerance (a 1.5 mm proud seal does not hide the opening edge)
GRAZE = 2e-4                    # |n.d| below this: face seen exactly edge-on (constant sections, cylinders end-on)
SLOPE_CAP = 6.0                 # cap on the surface depth slope used by the centre-pixel tolerance
OUTLINE_JUMP = 0.05             # m: depth jump beside an edge that makes it an outline
FINE_MIN_COS = 0.24             # fine feature loops seen more obliquely than this (|n.d|) are dropped
MIN_RUN_PX = 2.5                # partially visible runs shorter than this are noise
DEDUP_OBJ_PX = 4.0              # px: a weaker parallel line this close to an object line is dropped
DEDUP_FINE_PX = 6.0             # px: same for fine lines (window/seal/door twins merge into one)
RDP_EPS = 0.3                   # px
MIN_LINE_OBJ_PX = 2.0           # drop specks: object polylines shorter than this (5 mm full size)
MIN_LINE_FINE_PX = 8.0          # fine polylines shorter than this (20 mm full size, 0.4 mm at 1:50)

OBJECT, FINE = 0, 1
KIND_CREASE, KIND_SIL, KIND_BND = 0, 1, 2

VIEWS = {
    #            e_u              e_v              e_d (into the scene)
    "side":  np.array([[1.0, 0, 0], [0, 0, 1.0], [0, 1.0, 0]]),
    "plan":  np.array([[1.0, 0, 0], [0, 1.0, 0], [0, 0, -1.0]]),
    "front": np.array([[0, -1.0, 0], [0, 0, 1.0], [1.0, 0, 0]]),
}


def log(msg):
    print(msg, flush=True)


# ----------------------------------------------------------------------------
# posing & grouping
# ----------------------------------------------------------------------------
def drawable_ids(parts):
    return [k for k, p in parts.items()
            if p.step not in EXCLUDE_STEPS and k not in EXCLUDE_IDS and not k.startswith("eng_") and p.meshes]


def pose_parts(parts, prop_deg=PROP_TURN_DEG):
    """Return {part_id: [posed Mesh, ...]} for every drawable part."""
    out = {}
    Mprop = rotation_about((1, 0, 0), np.radians(prop_deg), PROP_ORIGIN)
    for k in drawable_ids(parts):
        p = parts[k]
        M = None
        if p.pivot and p.pivot.get("kind") == "gear_door":
            M = rotation_about(p.pivot["axis"], np.radians(p.pivot["open"]), p.pivot["origin"])
        if k == "propeller" or k.startswith("blade_"):
            M = Mprop
        ms = [m for m, mat in p.meshes if mat not in EXCLUDE_MATERIALS]
        if not ms:
            continue
        if M is not None:
            ms = [m.transformed(M) for m in ms]
        out[k] = ms
    return out


def check_prop_pose(posed):
    zmin = min(m.V[:, 2].min() for k, ms in posed.items() if k.startswith("blade_") for m in ms)
    return zmin


def weld(V, F, tol=WELD_TOL):
    """Merge vertices closer than tol (KD-tree pairs + connected components).
    Returns (V', F', kept_face_mask); faces that collapse are dropped."""
    n = len(V)
    tree = cKDTree(V)
    pairs = tree.query_pairs(tol, output_type="ndarray")
    if len(pairs):
        g = coo_matrix((np.ones(len(pairs), np.int8), (pairs[:, 0], pairs[:, 1])), shape=(n, n))
        _, lab = connected_components(g, directed=False)
    else:
        lab = np.arange(n)
    uniq, first = np.unique(lab, return_index=True)
    remap = np.empty(lab.max() + 1, np.int64)
    remap[uniq] = np.arange(len(uniq))
    V2 = V[first]
    F2 = remap[lab[F]]
    ok = (F2[:, 0] != F2[:, 1]) & (F2[:, 1] != F2[:, 2]) & (F2[:, 0] != F2[:, 2])
    return V2, F2[ok], ok


@dataclass
class Group:
    gid: str
    part_ids: tuple
    V: np.ndarray
    F: np.ndarray
    fpart: np.ndarray                   # part index per face
    fn: np.ndarray = None               # unit face normals (0 for degenerate)
    farea: np.ndarray = None            # face areas
    fcomp: np.ndarray = None            # face-connected component id
    E: np.ndarray = None                # (ne,2) vertex ids
    f1: np.ndarray = None
    f2: np.ndarray = None               # -1 for boundary edges
    etype: np.ndarray = None            # 0 smooth manifold, 1 crease/non-manifold, 2 boundary
    flip2: np.ndarray = None            # +-1: winding correction for face f2
    stats: dict = field(default_factory=dict)
    lines: bool = True                  # False: the group only occludes (depth buffer)


def build_group(gid, part_ids, meshes_per_part, part_index):
    Vs, Fs, fp = [], [], []
    off = 0
    for pid, ms in zip(part_ids, meshes_per_part):
        for m in ms:
            Vs.append(m.V)
            Fs.append(m.F + off)
            fp.append(np.full(len(m.F), part_index[pid], np.int32))
            off += len(m.V)
    V = np.vstack(Vs)
    F = np.vstack(Fs)
    fpart = np.concatenate(fp)
    nv0 = len(V)
    V, F, ok = weld(V, F)
    fpart = fpart[ok]
    g = Group(gid, tuple(part_ids), V, F, fpart)
    g.lines = not all(p.startswith(OCCLUDE_ONLY) for p in part_ids)
    g.stats["welded"] = nv0 - len(V)
    _topology(g)
    return g


def _topology(g: Group):
    V, F = g.V, g.F
    m = len(F)
    v0, v1, v2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    cr = np.cross(v1 - v0, v2 - v0)
    ln = np.linalg.norm(cr, axis=1)
    valid = ln > 1e-12
    g.fn = np.where(valid[:, None], cr / np.where(valid, ln, 1.0)[:, None], 0.0)
    g.farea = 0.5 * ln
    e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    fid = np.concatenate([np.arange(m)] * 3)
    lo = np.minimum(e[:, 0], e[:, 1])
    hi = np.maximum(e[:, 0], e[:, 1])
    key = lo * len(V) + hi
    order = np.argsort(key, kind="stable")
    ks = key[order]
    start = np.flatnonzero(np.r_[True, ks[1:] != ks[:-1]])
    cnt = np.diff(np.r_[start, len(ks)])
    first = order[start]
    second = order[np.minimum(start + 1, len(ks) - 1)]
    g.E = np.stack([lo[first], hi[first]], 1)
    g.f1 = fid[first]
    g.f2 = np.where(cnt >= 2, fid[second], -1)
    consistent = e[first, 0] == e[second, 1]
    g.flip2 = np.where((cnt >= 2) & ~consistent, -1.0, 1.0)
    n1 = g.fn[g.f1]
    n2 = g.fn[np.maximum(g.f2, 0)] * g.flip2[:, None]
    both = (cnt == 2) & valid[g.f1] & valid[np.maximum(g.f2, 0)]
    crease = both & (np.sum(n1 * n2, 1) < np.cos(np.radians(CREASE_DEG)))
    et = np.zeros(len(first), np.int8)
    et[crease | (cnt >= 3)] = 1
    et[cnt == 1] = 2
    g.etype = et
    g.stats.update(edges=len(first), boundary=int((cnt == 1).sum()), crease=int((et == 1).sum()),
                   nonmanifold=int((cnt >= 3).sum()), inconsistent=int(((cnt == 2) & ~consistent).sum()))
    _drop_seams(g)


def _ramp(n):
    """Concatenated 0..1 parameter ramps for segments sampled with n[i] points each."""
    if len(n) == 0:
        return np.zeros(0)
    first = np.r_[0, np.cumsum(n)[:-1]]
    pos = np.arange(n.sum()) - np.repeat(first, n)
    return pos / np.repeat(np.maximum(n - 1, 1), n)


def _drop_seams(g: Group):
    """Boundary edges lying on a smooth neighbouring loft panel of the same group
    (T-junction seams, e.g. wing skin panels split at the flap ends) are not
    real lines: re-type them as hidden (-1)."""
    b = np.flatnonzero(g.etype == 2)
    man = g.f2 >= 0
    m = len(g.F)
    if len(b) < 2:
        adj = coo_matrix((np.ones(man.sum(), np.int8), (g.f1[man], g.f2[man])), shape=(m, m))
        g.fcomp = connected_components(adj, directed=False)[1]
        return
    # face components through manifold edges
    man = g.f2 >= 0
    m = len(g.F)
    adj = coo_matrix((np.ones(man.sum(), np.int8), (g.f1[man], g.f2[man])), shape=(m, m))
    _, comp = connected_components(adj, directed=False)
    g.fcomp = comp
    p0 = g.V[g.E[b, 0]]
    p1 = g.V[g.E[b, 1]]
    d = p1 - p0
    L = np.linalg.norm(d, axis=1)
    dirs = d / np.maximum(L, 1e-12)[:, None]
    mid = 0.5 * (p0 + p1)
    nb = g.fn[g.f1[b]]
    cb = comp[g.f1[b]]
    # dense samples along boundary edges (<= 10 mm apart) for candidate search
    ns = np.maximum(2, np.ceil(L / 0.01).astype(np.int64) + 1)
    eid = np.repeat(np.arange(len(b)), ns)
    t = _ramp(ns)
    S = p0[eid] + t[:, None] * d[eid]
    tree = cKDTree(S)
    cand = tree.query_ball_point(mid, r=SEAM_TOL + 0.0051)
    qi = np.repeat(np.arange(len(b)), [len(c) for c in cand])
    qj = eid[np.concatenate([np.asarray(c, int) for c in cand])] if len(qi) else np.zeros(0, int)
    keep = (qi != qj) & (cb[qi] != cb[qj])
    qi, qj = qi[keep], qj[keep]
    # exact point-segment distance
    w = mid[qi] - p0[qj]
    tt = np.clip(np.sum(w * d[qj], 1) / np.maximum(L[qj] ** 2, 1e-18), 0, 1)
    dist = np.linalg.norm(w - tt[:, None] * d[qj], axis=1)
    par = np.abs(np.sum(dirs[qi] * dirs[qj], 1)) > 0.95
    smooth = np.abs(np.sum(nb[qi] * nb[qj], 1)) > np.cos(np.radians(35))
    hit = (dist < SEAM_TOL) & par & smooth
    seam = np.zeros(len(b), bool)
    seam[np.unique(qi[hit])] = True
    g.etype[b[seam]] = -1
    g.stats["seams_dropped"] = int(seam.sum())


def prepare(parts, verbose=True):
    """View-independent preparation: pose, group, weld, edge topology."""
    t0 = time.time()
    posed = pose_parts(parts)
    zmin = check_prop_pose(posed)
    if abs(zmin - 0.32) > 0.02:
        posed = pose_parts(parts, -PROP_TURN_DEG)
        zmin = check_prop_pose(posed)
    ids = list(posed.keys())
    part_index = {k: i for i, k in enumerate(ids)}
    in_group = {}
    for gname, members in WELD_GROUPS.items():
        for mbr in members:
            in_group[mbr] = gname
    groups, done = [], set()
    for k in ids:
        if k in done:
            continue
        if k in in_group:
            members = [m for m in WELD_GROUPS[in_group[k]] if m in posed]
            gid = in_group[k]
        else:
            members = [k]
            gid = k
        done.update(members)
        groups.append(build_group(gid, members, [posed[m] for m in members], part_index))
    if verbose:
        nf = sum(len(g.F) for g in groups)
        ne = sum(len(g.E) for g in groups)
        sd = sum(g.stats.get("seams_dropped", 0) for g in groups)
        log(f"  prepare: {len(ids)} parts -> {len(groups)} weld groups, {nf:,} tris, {ne:,} edges, "
            f"{sd} seam edges dropped, lowest blade tip z = {zmin:.3f} m  ({time.time() - t0:.1f}s)")
    return dict(groups=groups, part_ids=ids, part_index=part_index, blade_zmin=zmin)


# ----------------------------------------------------------------------------
# depth buffer (point splatting)
# ----------------------------------------------------------------------------
@dataclass
class Frame:
    R: np.ndarray       # 3x3 rows e_u, e_v, e_d
    u0: float
    v0: float
    W: int
    H: int
    px: float
    dmin: float

    def to_px(self, P):
        """world (n,3) -> (u_px, v_px, depth m)."""
        Q = np.asarray(P, float) @ self.R.T
        return np.stack([(Q[:, 0] - self.u0) / self.px, (Q[:, 1] - self.v0) / self.px, Q[:, 2]], 1)

    def px_to_uv(self, U):
        return np.stack([U[:, 0] * self.px + self.u0, U[:, 1] * self.px + self.v0], 1)


DQ = 1e-4                   # depth quantum in the packed key (0.1 mm)
ID_BITS = 12


def splat(tris, pids, fr: Frame, step=SPLAT_STEP):
    """tris: (T,3,3) float (u_px, v_px, depth). Returns packed uint64 key buffer (H*W)."""
    W, H = fr.W, fr.H
    buf = np.full(W * H, np.iinfo(np.uint64).max, np.uint64)
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    lab = np.hypot(*(b - a)[:, :2].T)
    lbc = np.hypot(*(c - b)[:, :2].T)
    lca = np.hypot(*(a - c)[:, :2].T)
    # anchor at the vertex opposite the longest edge -> the two sampled edges are the short ones
    longest = np.argmax(np.stack([lbc, lca, lab], 1), 1)   # 0: bc longest -> anchor a
    A = np.where((longest == 0)[:, None], a, np.where((longest == 1)[:, None], b, c))
    B = np.where((longest == 0)[:, None], b, np.where((longest == 1)[:, None], c, a))
    C = np.where((longest == 0)[:, None], c, np.where((longest == 1)[:, None], a, b))
    k1 = np.maximum(1, np.ceil(np.hypot(*(B - A)[:, :2].T) / step)).astype(np.int64)
    k2 = np.maximum(1, np.ceil(np.hypot(*(C - A)[:, :2].T) / step)).astype(np.int64)
    # bucket k to limit the number of groups
    def bucket(k):
        k = k.copy()
        big = k > 8
        e = np.ceil(np.log2(k[big]) * 4) / 4
        k[big] = np.ceil(2 ** e).astype(np.int64)
        return k
    k1, k2 = bucket(k1), bucket(k2)
    pid_arr = pids.astype(np.uint64)
    total = 0
    keys = k1 * 100000 + k2
    order = np.argsort(keys, kind="stable")
    ks = keys[order]
    starts = np.flatnonzero(np.r_[True, ks[1:] != ks[:-1]])
    ends = np.r_[starts[1:], len(ks)]
    for s, e in zip(starts, ends):
        sel = order[s:e]
        kk1, kk2 = int(k1[sel[0]]), int(k2[sel[0]])
        i, j = np.meshgrid(np.arange(kk1 + 1), np.arange(kk2 + 1), indexing="ij")
        w1 = (i / kk1).ravel()
        w2 = (j / kk2).ravel()
        m = w1 + w2 <= 1 + 1e-9
        w1 = w1[m].astype(np.float32)
        w2 = w2[m].astype(np.float32)
        M = len(w1)
        chunk = max(1, 3_000_000 // M)
        for c0 in range(0, len(sel), chunk):
            ss = sel[c0:c0 + chunk]
            a_ = A[ss].astype(np.float32)
            ab = (B[ss] - A[ss]).astype(np.float32)
            ac = (C[ss] - A[ss]).astype(np.float32)
            P = a_[:, None, :] + w1[None, :, None] * ab[:, None, :] + w2[None, :, None] * ac[:, None, :]
            ix = np.floor(P[..., 0]).astype(np.int64)
            iy = np.floor(P[..., 1]).astype(np.int64)
            ok = (ix >= 0) & (ix < W) & (iy >= 0) & (iy < H)
            dq = np.clip(np.round((P[..., 2] - fr.dmin) / DQ), 0, 2 ** 40).astype(np.uint64)
            key = (dq << np.uint64(ID_BITS)) | pid_arr[ss][:, None]
            np.minimum.at(buf, (iy * W + ix)[ok], key[ok])
            total += int(ok.sum())
    return buf, total


def unpack(buf, fr: Frame):
    empty = buf == np.iinfo(np.uint64).max
    depth = (buf >> np.uint64(ID_BITS)).astype(np.float64) * DQ + fr.dmin
    depth[empty] = np.inf
    pid = (buf & np.uint64((1 << ID_BITS) - 1)).astype(np.int32)
    pid[empty] = -1
    return depth, pid


# ----------------------------------------------------------------------------
# edge visibility
# ----------------------------------------------------------------------------
def _lookup(D, fr, u, v):
    ix = np.floor(u).astype(np.int64)
    iy = np.floor(v).astype(np.int64)
    ok = (ix >= 0) & (ix < fr.W) & (iy >= 0) & (iy < fr.H)
    out = np.full(len(u), np.inf)
    out[ok] = D[iy[ok] * fr.W + ix[ok]]
    return out


def part_rank(pid):
    """Priority of a part's lines when near-coincident lines are merged (lower wins)."""
    if pid in ("door_frames",):
        return 4
    if pid.startswith("glazing"):
        return 3
    if pid in ("lights", "antennas", "pitot") or pid.startswith("gear_door"):
        return 2
    if pid.startswith(("flap", "aileron", "elevator", "rudder", "winglet", "door_", "exit_")):
        return 1
    return 0


def is_feature_part(pid):
    """Parts whose lines are surface features (fine lines), never outlines."""
    return pid.startswith(("glazing", "door_")) or pid in ("exit_hatch",)


def loop_obliquity(g, s):
    """Per edge of group g: mean |n.d| of the boundary loop it belongs to (3-D length
    weighted over ALL boundary edges of the loop, so loops are not split at corners
    that happen to be seen end-on). Non-boundary edges get 1."""
    out = np.ones(len(g.E))
    b = np.flatnonzero(g.etype == 2)
    if len(b) == 0:
        return out
    nv = len(g.V)
    gr = coo_matrix((np.ones(len(b), np.int8), (g.E[b, 0], g.E[b, 1])), shape=(nv, nv))
    _, lab = connected_components(gr, directed=False)
    comp = lab[g.E[b, 0]]
    L3 = np.linalg.norm(g.V[g.E[b, 1]] - g.V[g.E[b, 0]], axis=1)
    f = np.abs(s[g.f1[b]])
    avg = np.bincount(comp, weights=L3 * f) / np.maximum(np.bincount(comp, weights=L3), 1e-12)
    out[b] = avg[comp]
    return out


def visible_samples(groups, fr: Frame, D, ranks, part_ids):
    """Sample every candidate edge, test visibility, classify outline/fine.
    Returns (edges, samples) dicts of flat arrays (only visible samples kept)."""
    ed = fr.R[2]
    feature_part = np.array([is_feature_part(p) for p in part_ids], bool)
    E = {k: [] for k in ("pa", "pb", "va", "vb", "kind", "part", "L", "w")}
    S = {k: [] for k in ("p", "d", "t", "e", "outline")}
    node_off = 0
    e_off = 0
    nsamp_total = 0
    for g in groups:
        if not g.lines:
            node_off += len(g.V)
            continue
        Pv = fr.to_px(g.V)
        s = g.fn @ ed                                   # < 0 : front-facing
        nt = np.linalg.norm(g.fn - s[:, None] * ed[None, :], axis=1)
        slope = np.where(np.abs(s) > 1e-9, nt / np.maximum(np.abs(s), 1e-9), 1e9)
        f1, f2 = g.f1, g.f2
        s1 = s[f1]
        s2 = np.where(f2 >= 0, s[np.maximum(f2, 0)] * g.flip2, 0.0)
        # facing with a dead zone: faces seen (almost) exactly edge-on are 'grazing' (0).
        # A silhouette separates a front-facing face from a grazing or back-facing one,
        # so bodies seen end-on (a cylinder along the view axis, the constant-section
        # cabin in the front view) still get one clean outline instead of noise.
        c1 = np.where(s1 < -GRAZE, -1, np.where(s1 > GRAZE, 1, 0))
        c2 = np.where(s2 < -GRAZE, -1, np.where(s2 > GRAZE, 1, 0))
        flip = (c1 * c2) < 0                                   # ordinary front/back change
        edge_on = ((c1 == -1) & (c2 == 0)) | ((c2 == -1) & (c1 == 0))  # front -> exactly edge-on
        sil = (g.etype == 0) & (f2 >= 0) & (flip | edge_on)
        cand = sil | (g.etype == 1) | (g.etype == 2)
        idx = np.flatnonzero(cand)
        pa = Pv[g.E[idx, 0]]
        pb = Pv[g.E[idx, 1]]
        L = np.hypot(pb[:, 0] - pa[:, 0], pb[:, 1] - pa[:, 1])
        keep = L > 0.05
        idx, pa, pb, L = idx[keep], pa[keep], pb[keep], L[keep]
        if len(idx) == 0:
            node_off += len(g.V)
            continue
        kind = np.where(sil[idx], KIND_SIL, np.where(g.etype[idx] == 1, KIND_CREASE, KIND_BND))
        sl = np.where(f2[idx] >= 0, np.minimum(slope[f1[idx]], slope[np.maximum(f2[idx], 0)]), slope[f1[idx]])
        sl = np.minimum(sl, SLOPE_CAP)
        n = np.maximum(2, np.ceil(L / EDGE_STEP).astype(np.int64) + 1)
        eid = np.repeat(np.arange(len(idx)), n)
        t = _ramp(n)
        P = pa[eid] + t[:, None] * (pb[eid] - pa[eid])
        nsamp_total += len(P)
        du = (pb[:, 0] - pa[:, 0]) / L
        dv = (pb[:, 1] - pa[:, 1]) / L
        ou, ov = -dv[eid] * SIDE_OFF, du[eid] * SIDE_OFF
        dc = _lookup(D, fr, P[:, 0], P[:, 1])
        dp = _lookup(D, fr, P[:, 0] + ou, P[:, 1] + ov)
        dm = _lookup(D, fr, P[:, 0] - ou, P[:, 1] - ov)
        d = P[:, 2]
        tol_c = TOL0 + sl[eid] * 0.75 * fr.px
        center_ok = (kind[eid] != KIND_SIL) & (dc >= d - tol_c)
        side_ok = (dp >= d - TOL0) | (dm >= d - TOL0)
        vis = center_ok | side_ok
        # outline = a depth jump beside the edge larger than the surface's own slope explains
        smax = np.where(f2[idx] >= 0, np.maximum(slope[f1[idx]], slope[np.maximum(f2[idx], 0)]), slope[f1[idx]])
        thr = OUTLINE_JUMP + np.where(kind == KIND_SIL, 0.0, np.minimum(smax, 40.0) * SIDE_OFF * fr.px)
        outline = (np.maximum(dp, dm) - d) > thr[eid]
        # drop short partial runs (visibility noise); fully visible edges always survive
        brk = np.r_[True, (eid[1:] != eid[:-1]) | (vis[1:] != vis[:-1])]
        rs = np.flatnonzero(brk)
        re = np.r_[rs[1:], len(vis)] - 1
        runlen = (t[re] - t[rs]) * L[eid[rs]]
        full = (t[rs] <= 0) & (t[re] >= 1)
        bad = vis[rs] & ~full & (runlen < MIN_RUN_PX)
        if bad.any():
            rl = re - rs + 1
            vis[np.repeat(bad, rl)] = False
        # edge weight: majority of the outline flags of its visible samples
        cnt = np.bincount(eid[vis], minlength=len(idx))
        nout = np.bincount(eid[vis], weights=outline[vis].astype(float), minlength=len(idx))
        wgt = np.where(nout >= 0.5 * np.maximum(cnt, 1), OBJECT, FINE).astype(np.int8)
        # windows, doors, hatches, seams and the openings cut for them are always fine lines
        epart = g.fpart[f1[idx]]
        wgt[(feature_part[epart] & (kind != KIND_SIL)) | ((kind == KIND_BND) & (g.gid == "fuselage"))] = FINE
        # feature loops (fine boundary/crease lines) drawn on a surface seen almost
        # edge-on collapse into slivers along an outline: drop the whole loop
        fore = np.where(f2[idx] >= 0, np.maximum(np.abs(s1[idx]), np.abs(s2[idx])), np.abs(s1[idx]))
        dropped = np.zeros(len(idx), bool)
        # a door / window / hatch slab: judge it by its whole skin, not by a thin rim face
        ca = np.bincount(g.fcomp, weights=g.farea * np.abs(s)) / np.maximum(np.bincount(g.fcomp, weights=g.farea), 1e-12)
        fp = feature_part[epart] & (kind != KIND_SIL)
        dropped |= fp & (wgt == FINE) & (ca[g.fcomp[f1[idx]]] < FINE_MIN_COS)
        # other fine outlines: boundary loops (openings, boots, lips) judged by their mean
        # obliquity over the whole loop (3-D length weighted, independent of occlusion)
        bi = np.flatnonzero((kind == KIND_BND) & ~fp)
        if len(bi) and (wgt[bi] == FINE).any():
            dropped[bi] |= (loop_obliquity(g, s)[idx[bi]] < FINE_MIN_COS) & (wgt[bi] == FINE)
        vis &= ~dropped[eid]
        E["w"].append(wgt)
        E["pa"].append(pa[:, :2])
        E["pb"].append(pb[:, :2])
        E["va"].append(g.E[idx, 0] + node_off)
        E["vb"].append(g.E[idx, 1] + node_off)
        E["kind"].append(kind)
        E["part"].append(g.fpart[f1[idx]])
        E["L"].append(L)
        S["p"].append(P[vis, :2])
        S["d"].append(d[vis])
        S["t"].append(t[vis])
        S["e"].append(eid[vis] + e_off)
        S["outline"].append(outline[vis])
        node_off += len(g.V)
        e_off += len(idx)
    E = {k: np.concatenate(v) if v and v[0].ndim == 1 else np.vstack(v) for k, v in E.items()}
    S = {k: np.concatenate(v) if v and v[0].ndim == 1 else np.vstack(v) for k, v in S.items()}
    ne = len(E["L"])
    E["rank"] = np.array([ranks[p] for p in E["part"]], np.int16) if ne else np.zeros(0, np.int16)
    return E, S, nsamp_total


def coverage_outline(D, fr: Frame, sigma=0.8, min_len=8.0):
    """Outline of everything against the empty background, from the depth buffer's
    coverage mask (1-px closing, light Gaussian blur, contourpy iso-line at 0.5).
    Returns a list of (n,2) polylines in px coordinates."""
    import contourpy
    from scipy.ndimage import binary_closing, gaussian_filter
    m = np.isfinite(D).reshape(fr.H, fr.W)
    m = binary_closing(m, structure=np.ones((3, 3), bool), iterations=1)
    f = gaussian_filter(m.astype(np.float32), sigma)
    lines = contourpy.contour_generator(z=f, name="serial", line_type="Separate").lines(0.5)
    out = []
    for L in lines:
        L = np.asarray(L, float) + 0.5          # array index -> pixel-centre coordinates
        if len(L) >= 3 and np.hypot(*np.diff(L, axis=0).T).sum() >= min_len:
            out.append(smooth_polyline(L))
    return out


def smooth_polyline(L, passes=2):
    """Light [1 2 1] smoothing to take the pixel stair-steps out of a contour
    (closed loops wrap around; open ends are kept fixed)."""
    closed = np.hypot(*(L[-1] - L[0])) < 1e-6
    P = L[:-1].copy() if closed else L.copy()
    if len(P) < 5:
        return L
    for _ in range(passes):
        if closed:
            P = 0.25 * np.roll(P, 1, 0) + 0.5 * P + 0.25 * np.roll(P, -1, 0)
        else:
            Q = P.copy()
            Q[1:-1] = 0.25 * P[:-2] + 0.5 * P[1:-1] + 0.25 * P[2:]
            P = Q
    return np.vstack([P, P[:1]]) if closed else P


def add_virtual_edges(E, S, polylines, rank=-1):
    """Append known-visible OBJECT polylines (the coverage outline) as edges + samples."""
    if not polylines:
        return E, S
    node0 = int(max(E["va"].max(), E["vb"].max())) + 1 if len(E["va"]) else 0
    e0 = len(E["L"])
    pa, pb, va, vb = [], [], [], []
    for L in polylines:
        n = len(L)
        ids = node0 + np.arange(n)
        if np.hypot(*(L[-1] - L[0])) < 1e-6:        # closed loop: last point == first
            ids[-1] = ids[0]
        pa.append(L[:-1]); pb.append(L[1:]); va.append(ids[:-1]); vb.append(ids[1:])
        node0 += n
    pa = np.vstack(pa); pb = np.vstack(pb); va = np.concatenate(va); vb = np.concatenate(vb)
    L = np.hypot(*(pb - pa).T)
    ok = L > 1e-6
    pa, pb, va, vb, L = pa[ok], pb[ok], va[ok], vb[ok], L[ok]
    ne = len(L)
    n = np.maximum(2, np.ceil(L / EDGE_STEP).astype(np.int64) + 1)
    eid = np.repeat(np.arange(ne), n)
    t = _ramp(n)
    P = pa[eid] + t[:, None] * (pb[eid] - pa[eid])
    add = dict(pa=pa, pb=pb, va=va, vb=vb, kind=np.full(ne, KIND_SIL), part=np.full(ne, -1),
               L=L, w=np.full(ne, OBJECT, np.int8), rank=np.full(ne, rank, np.int16))
    for k, v in add.items():
        E[k] = np.concatenate([E[k], v.astype(E[k].dtype)]) if E[k].ndim == 1 else np.vstack([E[k], v])
    for k, v in dict(p=P, d=np.zeros(len(P)), t=t, e=eid + e0, outline=np.ones(len(P), bool)).items():
        S[k] = np.concatenate([S[k], v.astype(S[k].dtype)]) if S[k].ndim == 1 else np.vstack([S[k], v])
    return E, S


def dedupe_samples(E, S):
    """Drop samples that run alongside (and parallel to) a higher-priority line.
    Priority: OBJECT before FINE, then part rank, then crease/silhouette before
    boundary, then edge index. A sample is only suppressed where the stronger
    line actually runs beside it (|along-offset| <= 0.75 px), so a gap in one
    line is filled by its weaker twin instead of leaving a hole."""
    n_all = len(S["e"])
    if n_all == 0:
        return np.zeros(0, bool)
    e_all = S["e"]
    w_all = E["w"][e_all].astype(np.int64)
    prio_all = (w_all * 1000 + E["rank"][e_all].astype(np.int64) * 10 + E["kind"][e_all].astype(np.int64)) * 10_000_000 + e_all
    d = E["pb"] - E["pa"]
    dirs = d / np.maximum(np.hypot(d[:, 0], d[:, 1]), 1e-12)[:, None]
    # pre-pass: of several samples in the same 0.5 px cell with the same direction
    # bin, only the strongest can matter
    ang = np.mod(np.arctan2(dirs[e_all, 1], dirs[e_all, 0]), np.pi)
    cell = np.floor(S["p"] / 0.5).astype(np.int64)
    key = (cell[:, 0] * 40000 + cell[:, 1]) * 8 + (np.floor(ang / (np.pi / 8)).astype(np.int64) % 8)
    order = np.lexsort((prio_all, key))
    ko = key[order]
    first = np.r_[True, ko[1:] != ko[:-1]]
    winner = order[np.maximum.accumulate(np.where(first, np.arange(len(order)), 0))]
    t_o = S["t"][order]
    drop = ~first & (e_all[order] != e_all[winner]) & (t_o > 0) & (t_o < 1)
    sub = np.sort(order[~drop])
    e = e_all[sub]
    w = w_all[sub]
    prio = prio_all[sub]
    P = S["p"][sub]
    n = len(sub)
    dr = dirs[e]
    rmax = max(DEDUP_OBJ_PX, DEDUP_FINE_PX)
    pairs = cKDTree(P).query_pairs(rmax, output_type="ndarray")
    i, j = pairs[:, 0], pairs[:, 1]
    ei, ej = e[i], e[j]
    ok = ei != ej
    # edges that continue each other through a shared vertex never suppress each
    # other (they are one line); edges that leave a shared vertex the SAME way are
    # twins and may.
    va, vb = E["va"], E["vb"]
    pa_, pb_ = E["pa"], E["pb"]
    shared_a = (va[ei] == va[ej]) | (va[ei] == vb[ej])        # ei's a-end is shared
    shared_b = (vb[ei] == va[ej]) | (vb[ei] == vb[ej])
    adj = shared_a | shared_b
    # outgoing directions from the shared vertex
    vi_sh = np.where(shared_a, va[ei], vb[ei])
    out_i = np.where(shared_a[:, None], pb_[ei] - pa_[ei], pa_[ei] - pb_[ei])
    out_j = np.where((va[ej] == vi_sh)[:, None], pb_[ej] - pa_[ej], pa_[ej] - pb_[ej])
    continuing = adj & (np.sum(out_i * out_j, 1) <= 0)
    ok &= ~continuing
    ok &= np.abs(np.sum(dr[i] * dr[j], 1)) > np.cos(np.radians(30))
    i, j = i[ok], j[ok]
    # orient pairs: s (stronger) -> k (weaker)
    swap = prio[i] > prio[j]
    s_ = np.where(swap, j, i)
    k_ = np.where(swap, i, j)
    off = P[s_] - P[k_]
    along = np.abs(np.sum(off * dr[k_], 1))
    perp = np.abs(off[:, 0] * dr[k_, 1] - off[:, 1] * dr[k_, 0])
    rk = np.where(w[k_] == OBJECT, DEDUP_OBJ_PX, DEDUP_FINE_PX)
    # the weaker sample must lie beside the stronger sample's own edge segment:
    # neighbours further along the same chain are then never mistaken for twins
    es = e[s_]
    A_ = E["pa"][es]
    AB = E["pb"][es] - A_
    LL = np.maximum(np.sum(AB * AB, 1), 1e-12)
    tt = np.sum((P[k_] - A_) * AB, 1) / LL
    # slack grows with the offset: on a curve, a parallel twin 'fans out' past the ends of
    # the stronger line's short segments (window and door corners)
    slack = (0.25 + 0.6 * perp) / np.sqrt(LL)
    ok = (along <= 0.75) & (perp <= rk) & (tt >= -slack) & (tt <= 1 + slack)
    s_, k_ = s_[ok], k_[ok]
    # resolve in priority order: a sample is dropped only by a KEPT stronger sample
    state = np.zeros(n, np.int8)           # 0 undecided, 1 kept, 2 dropped
    for _ in range(50):
        und = state == 0
        if not und.any():
            break
        live = state[s_] != 2
        has_kept = np.zeros(n, bool)
        np.logical_or.at(has_kept, k_[live & (state[s_] == 1)], True)
        has_und = np.zeros(n, bool)
        np.logical_or.at(has_und, k_[live & (state[s_] == 0)], True)
        drop = und & has_kept
        keep = und & ~has_kept & ~has_und
        if not drop.any() and not keep.any():
            state[und] = 1
            break
        state[drop] = 2
        state[keep] = 1
    state[state == 0] = 1
    out = np.zeros(n_all, bool)
    out[sub[state == 1]] = True
    return out


def segments_from_samples(E, S, keep):
    """Runs of kept samples per edge -> segments with chainable end nodes."""
    e = S["e"][keep]
    t = S["t"][keep]
    if len(e) == 0:
        return None
    order = np.lexsort((t, e))
    e, t = e[order], t[order]
    ne = len(E["L"])
    # a run continues while the edge is the same and the parameter step is ~one sample
    step = EDGE_STEP / np.maximum(E["L"][e], 1e-9)
    brk = np.r_[True, (e[1:] != e[:-1]) | (t[1:] - t[:-1] > 1.6 * step[1:])]
    rs = np.flatnonzero(brk)
    re = np.r_[rs[1:], len(e)] - 1
    eo = e[rs]
    t0, t1 = t[rs], t[re]
    good = (re > rs)
    eo, t0, t1 = eo[good], t0[good], t1[good]
    pa, pb = E["pa"][eo], E["pb"][eo]
    A = pa + t0[:, None] * (pb - pa)
    B = pa + t1[:, None] * (pb - pa)
    na = np.where(t0 <= 1e-9, E["va"][eo], -1)
    nb = np.where(t1 >= 1 - 1e-9, E["vb"][eo], -1)
    base = 10 ** 12
    fa = na < 0
    na[fa] = base + np.arange(fa.sum())
    fb = nb < 0
    nb[fb] = base + fa.sum() + np.arange(fb.sum())
    return dict(a=A, b=B, na=na, nb=nb, w=E["w"][eo], kind=E["kind"][eo], part=E["part"][eo])


# ----------------------------------------------------------------------------
# chaining and simplification
# ----------------------------------------------------------------------------
def merge_nodes(a, b, na, nb, r=0.4):
    """Unify segment end nodes: same topological id OR within r px of each other."""
    n = len(a)
    ends = np.vstack([a, b])
    ids = np.concatenate([na, nb])
    _, tid = np.unique(ids, return_inverse=True)
    m = len(ends)
    rows, cols = [np.arange(m)], [m + tid]              # element <-> topological node
    pairs = cKDTree(ends).query_pairs(r, output_type="ndarray")
    if len(pairs):
        rows.append(pairs[:, 0])
        cols.append(pairs[:, 1])
    rows = np.concatenate(rows)
    cols = np.concatenate(cols)
    N = m + tid.max() + 1
    g = coo_matrix((np.ones(len(rows), np.int8), (rows, cols)), shape=(N, N))
    _, lab = connected_components(g, directed=False)
    return lab[:n], lab[n:m]


def chain_segments(a, b, na, nb):
    """Chain segments through shared node ids.
    Returns list of ((n,2) array, index of the chain's first segment)."""
    nseg = len(a)
    if nseg == 0:
        return []
    na, nb = merge_nodes(a, b, na, nb)
    adj = {}
    for i in range(nseg):
        adj.setdefault(int(na[i]), []).append(i)
        adj.setdefault(int(nb[i]), []).append(i)
    used = np.zeros(nseg, bool)
    chains = []

    def walk(start_node, i):
        pts = []
        i0 = i
        node = start_node
        while True:
            used[i] = True
            if int(na[i]) == node:
                if not pts:
                    pts.append(a[i])
                pts.append(b[i])
                node = int(nb[i])
            else:
                if not pts:
                    pts.append(b[i])
                pts.append(a[i])
                node = int(na[i])
            lst = adj[node]
            if len(lst) != 2:
                break
            j = lst[0] if lst[1] == i else lst[1]
            if used[j]:
                break
            i = j
        return np.array(pts), i0

    for node, lst in adj.items():
        if len(lst) != 2:
            for i in lst:
                if not used[i]:
                    chains.append(walk(node, i))
    for i in range(nseg):
        if not used[i]:
            chains.append(walk(int(na[i]), i))
    return chains


def bridge_chains(chains, r=3.0, min_cos=0.8):
    """Join chain ends that are within r px and continue each other (collinear, facing),
    so a line fragmented by visibility / de-duplication does not read as a dashed
    (hidden) line. chains: list of ((n,2) array, tag). Returns the same structure."""
    if len(chains) < 2:
        return chains

    def end_info(P, at_start):
        Q = P if at_start else P[::-1]
        d = np.hypot(*(Q - Q[0]).T)
        k = int(np.searchsorted(d, 1.5))
        k = min(max(k, 1), len(Q) - 1)
        t = Q[0] - Q[k]
        n = np.hypot(*t)
        return Q[0], (t / n if n > 1e-9 else np.zeros(2))

    pos, tan, ref = [], [], []
    for i, (P, _) in enumerate(chains):
        for e in (0, 1):
            p, t = end_info(P, e == 0)
            pos.append(p)
            tan.append(t)
            ref.append((i, e))
    pos = np.array(pos)
    tan = np.array(tan)
    pairs = cKDTree(pos).query_pairs(r, output_type="ndarray")
    if len(pairs) == 0:
        return chains
    a, b = pairs[:, 0], pairs[:, 1]
    g = pos[b] - pos[a]
    dist = np.hypot(g[:, 0], g[:, 1])
    gu = g / np.maximum(dist, 1e-9)[:, None]
    far = dist > 0.3
    ok = np.where(far, (np.sum(tan[a] * gu, 1) > min_cos) & (np.sum(tan[b] * -gu, 1) > min_cos),
                  np.sum(tan[a] * -tan[b], 1) > min_cos)
    ok &= (a // 2) != (b // 2)
    a, b, dist = a[ok], b[ok], dist[ok]
    order = np.argsort(dist)
    used = np.zeros(len(pos), bool)
    link = {}
    for k in order:
        i, j = a[k], b[k]
        if used[i] or used[j]:
            continue
        used[i] = used[j] = True
        link[i] = j
        link[j] = i
    if not link:
        return chains
    # walk: every chain has end slots 2c (start) and 2c+1 (end)
    seen = np.zeros(len(chains), bool)
    out = []
    for c in range(len(chains)):
        if seen[c]:
            continue
        # go to one extremity of the linked sequence
        cur, cur_end = c, 0                      # leave chain c through its start
        steps = 0
        while (2 * cur + cur_end) in link and steps < len(chains):
            nxt = link[2 * cur + cur_end]
            cur, cur_end = nxt // 2, 1 - (nxt % 2)
            steps += 1
            if cur == c:
                break
        # now walk forward from (cur, entering at cur_end)
        start_c, start_e = cur, cur_end
        seq = []
        cur, enter = start_c, start_e
        while True:
            if seen[cur]:
                break
            seen[cur] = True
            P, tag = chains[cur]
            seq.append((P if enter == 0 else P[::-1], tag))
            exit_slot = 2 * cur + (1 - enter)
            if exit_slot not in link:
                break
            nxt = link[exit_slot]
            cur, enter = nxt // 2, nxt % 2
        pts = np.vstack([q for q, _ in seq])
        out.append((pts, seq[0][1]))
    return out


def split_folds(P, max_turn_deg=150.0):
    """Split a polyline where it doubles back on itself (turn > max_turn_deg),
    so simplification cannot erase an out-and-back excursion."""
    if len(P) < 3:
        return [P]
    d = np.diff(P, axis=0)
    n = np.hypot(d[:, 0], d[:, 1])
    good = n > 1e-9
    if not good.all():
        P = np.vstack([P[:1], P[1:][good]])
        if len(P) < 3:
            return [P]
        d = np.diff(P, axis=0)
        n = np.hypot(d[:, 0], d[:, 1])
    u = d / n[:, None]
    cosang = np.sum(u[:-1] * u[1:], 1)
    cut = np.flatnonzero(cosang < np.cos(np.radians(180 - max_turn_deg))) + 1
    if len(cut) == 0:
        return [P]
    out, s = [], 0
    for c in cut:
        out.append(P[s:c + 1])
        s = c
    out.append(P[s:])
    return [q for q in out if len(q) >= 2]


def rdp(P, eps):
    n = len(P)
    if n < 3:
        return P
    keep = np.zeros(n, bool)
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a, b = P[i], P[j]
        seg = P[i + 1:j]
        ab = b - a
        L = np.hypot(ab[0], ab[1])
        if L < 1e-12:
            d = np.hypot(seg[:, 0] - a[0], seg[:, 1] - a[1])
        else:
            d = np.abs(ab[0] * (seg[:, 1] - a[1]) - ab[1] * (seg[:, 0] - a[0])) / L
        k = int(np.argmax(d))
        if d[k] > eps:
            m = i + 1 + k
            keep[m] = True
            stack.append((i, m))
            stack.append((m, j))
    return P[keep]


# ----------------------------------------------------------------------------
# view rendering
# ----------------------------------------------------------------------------
@dataclass
class ViewResult:
    name: str
    frame: Frame
    lines: list                 # [(weight, (n,2) array in view-plane metres, part index)]
    depth: np.ndarray           # (H*W) depth buffer (m), inf = empty
    pid: np.ndarray             # (H*W) part index buffer, -1 = empty
    part_ids: list
    bounds: tuple               # (umin, umax, vmin, vmax) of the geometry, m
    timings: dict

    def uv_to_px(self, uv):
        uv = np.asarray(uv, float)
        return np.stack([(uv[..., 0] - self.frame.u0) / self.frame.px, (uv[..., 1] - self.frame.v0) / self.frame.px], -1)

    def project(self, P):
        """world points -> (u, v, depth)."""
        return np.asarray(P, float) @ self.frame.R.T

    def is_visible(self, P, tol=0.01):
        """True where world point P is not hidden (depth test at its pixel, 3x3 lenient)."""
        Q = self.project(np.atleast_2d(P))
        U = self.uv_to_px(Q[:, :2])
        best = np.full(len(Q), -np.inf)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                D = _lookup(self.depth, self.frame, U[:, 0] + dx, U[:, 1] + dy)
                best = np.maximum(best, D - Q[:, 2])
        return best >= -tol

    def part_at(self, uv):
        U = self.uv_to_px(np.atleast_2d(uv))
        ix = np.floor(U[:, 0]).astype(int)
        iy = np.floor(U[:, 1]).astype(int)
        ok = (ix >= 0) & (ix < self.frame.W) & (iy >= 0) & (iy < self.frame.H)
        out = np.full(len(U), -1)
        out[ok] = self.pid[iy[ok] * self.frame.W + ix[ok]]
        return out


def render_view(prep, name, px=PX, verbose=True):
    t = {}
    t0 = time.time()
    R = VIEWS[name]
    groups = prep["groups"]
    allV = np.vstack([g.V for g in groups])
    Q = allV @ R.T
    umin, vmin, dmin = Q.min(0)
    umax, vmax, dmax = Q.max(0)
    pad = 12 * px
    fr = Frame(R=R, u0=umin - pad, v0=vmin - pad, W=int(np.ceil((umax - umin + 2 * pad) / px)) + 1,
               H=int(np.ceil((vmax - vmin + 2 * pad) / px)) + 1, px=px, dmin=dmin - 0.01)
    tris, pids = [], []
    for g in groups:
        Pv = fr.to_px(g.V)
        tris.append(Pv[g.F])
        pids.append(g.fpart)
    tris = np.concatenate(tris)
    pids = np.concatenate(pids)
    buf, nsplat = splat(tris, pids, fr)
    D, PID = unpack(buf, fr)
    del buf
    t["splat"] = time.time() - t0
    t1 = time.time()
    ranks = [part_rank(p) for p in prep["part_ids"]]
    E, S, nsamp = visible_samples(groups, fr, D, ranks, prep["part_ids"])
    outline = coverage_outline(D, fr)
    E, S = add_virtual_edges(E, S, outline, rank=9)     # gap-filler behind the exact silhouettes
    t["visibility"] = time.time() - t1
    t2 = time.time()
    keep = dedupe_samples(E, S)
    t["dedupe"] = time.time() - t2
    t3 = time.time()
    seg = segments_from_samples(E, S, keep)
    lines = []
    if seg is not None:
        for w in (OBJECT, FINE):
            m = seg["w"] == w
            mi = np.flatnonzero(m)
            chains = [(C, int(seg["part"][mi[i0]]))
                      for C, i0 in chain_segments(seg["a"][m], seg["b"][m], seg["na"][m], seg["nb"][m])]
            for C, pidx in bridge_chains(chains):
                for P in split_folds(C):
                    if np.hypot(*np.diff(P, axis=0).T).sum() > (MIN_LINE_FINE_PX if w == FINE else MIN_LINE_OBJ_PX):
                        lines.append((w, fr.px_to_uv(rdp(P, RDP_EPS)), pidx))
    t["chain+rdp"] = time.time() - t3
    t["total"] = time.time() - t0
    if verbose:
        npts = sum(len(P) for _, P, _ in lines)
        log(f"  {name:5s}: buffer {fr.W}x{fr.H} @ {px*1000:.1f} mm/px, {len(tris):,} tris -> {nsplat/1e6:.1f} M splats; "
            f"{nsamp/1e6:.2f} M edge samples ({len(keep):,} visible, {int(keep.sum()):,} kept); "
            f"{len(lines):,} polylines / {npts:,} pts  " + "  ".join(f"{k} {v:.1f}s" for k, v in t.items()))
    return ViewResult(name, fr, lines, D, PID, prep["part_ids"], (umin, umax, vmin, vmax), t)


def render_all(parts=None, views=("side", "plan", "front"), px=PX, verbose=True):
    t0 = time.time()
    if parts is None:
        from model.build import build_parts
        parts = build_parts()
        if verbose:
            log(f"  model built ({time.time() - t0:.1f}s)")
    prep = prepare(parts, verbose)
    out = {name: render_view(prep, name, px, verbose) for name in views}
    if verbose:
        log(f"  HLR total {time.time() - t0:.1f}s")
    return out, prep


if __name__ == "__main__":
    res, _ = render_all()
