"""
2-D / 3-D consistency: the BUILT mesh (out/pc12.glb) is projected / sliced and compared with the PARAMETER outlines
the approved Stage-2 drawing set is drawn from (sheets L1-L5, drawing/*.py -- those never read the mesh):

  L1  lines plan         skin vertices on the OML; profile (crown / keel at BL 0) both ways; half-breadth (plan);
                         body plan at the Pilatus frames (fuselage.FRAMES) both ways, parameter openings excluded
  L2  glazing + mask     side-window / windshield holes vs cockpit_glazing outlines; glass covers the holes;
                         PRO mask colour boundary vs cockpit_glazing.side_outline('mask'); mask extent on the skin
  L3  openings           cabin windows, door-panel seams and the exit in the skins (no missing / extra holes);
                         door slabs and door windows; clear openings (door stops)
  L4  layout             wing sections (LE, TE, front silhouette, section shape, flap lip, aileron gap, tip rib),
                         winglet sections, tailplane planform (plan outline, horn gap), fin sections, tail side
                         silhouette both ways, main-gear leg door, bullet, radar pod, axles / tyres, propeller
                         blades / disc (pitch-axis plane, tip radius) and spinner
  L5  livery             painted sub-mesh colour boundaries vs the livery curves (side projection) both ways,
                         paint regions (sampled per triangle against livery.region_fields), wing boot band, pod
                         radome joint, blade bands, per-surface colours (SURFACES, STAB_BOOT, WINGLET_PIN)

    python3 test/consistency_2d3d.py                  # all sheets
    python3 test/consistency_2d3d.py --only L2,L3     # some sheets
    options: --glb PATH (default out/pc12.glb), --json PATH (default out/tmp/stage3_consistency/report.json),
             --plots (diagnostic PNGs next to the JSON), -v (worst locations of every row)

Tolerances (mm): 5 OML / openings / glazing, 10 livery, 15 planform features.  Prints one PASS / FAIL / INFO row
per check (max and rms deviation, samples, tolerance) and 'CONSISTENCY OK' / 'CONSISTENCY FAIL'; exit code 1 on a
FAIL, 2 when the GLB is missing.  The GLB must be newer than model/*.py and cad/*.py (first row) -- rebuild with
python3 model/build.py.  Model axes throughout: x station aft, y butt line (+ starboard), z water line (m).
"""
from __future__ import annotations

import argparse
import json
import math
import struct
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cad import sdf2d  # noqa: E402
from model import fuselage as F  # noqa: E402
from model import fuselage_parts as FP  # noqa: E402
from model import cockpit_glazing as CG  # noqa: E402
from model import wing as W  # noqa: E402
from model import empennage as E  # noqa: E402
from model import gear as G  # noqa: E402
from model import details as D  # noqa: E402
from model import powerplant as PP  # noqa: E402
from model import livery as L  # noqa: E402
from model import bays as BY  # noqa: E402
from model.lifting import cos_pts  # noqa: E402

TOL = dict(oml=5.0, opening=5.0, glazing=5.0, livery=10.0, planform=15.0)     # mm
X0, X1 = F.STA["cowl_front"], F.STA["tail_end"]
SKIN_PARTS = ("cowl_upper", "cowl_lower", "fus_fwd", "fus_center", "fus_aft")
DOOR_PARTS = ("door_airstair", "door_cargo", "exit_hatch")
SIDE_PAINT = set(L.PAINT_ORDER) | {L.BASE}          # materials the side-projection painter produces
DEFAULT_JSON = ROOT / "out" / "tmp" / "stage3_consistency" / "report.json"


# =====================================================================================================================
# GLB reader (materials kept; node transforms applied; glTF axes -> model axes)
# =====================================================================================================================
@dataclass
class Rec:
    part: str
    name: str
    mat: str
    V: np.ndarray          # (n, 3) model coordinates
    F: np.ndarray          # (m, 3)
    key: np.ndarray        # (n, 3) raw (quantised) positions: equal key = same vertex


def read_glb(path):
    data = Path(path).read_bytes()
    n = struct.unpack("<I", data[12:16])[0]
    js = json.loads(data[20:20 + n])
    binb = data[20 + n + 8:]
    ctype = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
    ncomp = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}
    mats = [m["name"] for m in js["materials"]]

    def acc(i):
        a = js["accessors"][i]
        bv = js["bufferViews"][a["bufferView"]]
        dt = np.dtype(ctype[a["componentType"]])
        nc = ncomp[a["type"]]
        stride = bv.get("byteStride", dt.itemsize * nc)
        off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        raw = np.frombuffer(binb, np.uint8, stride * (a["count"] - 1) + dt.itemsize * nc, off)
        arr = np.lib.stride_tricks.as_strided(raw, (a["count"], nc * dt.itemsize), (stride, 1))
        raw_vals = np.ascontiguousarray(arr).view(dt).reshape(a["count"], nc)
        vals = raw_vals.astype(float)
        if a.get("normalized") and dt.kind in "iu":
            vals = np.maximum(vals / float(np.iinfo(dt).max), -1.0)
        return vals, raw_vals

    def qmat(q):
        x, y, z, w = q
        return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                         [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                         [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])

    def local(nd):
        if "matrix" in nd:
            return np.array(nd["matrix"]).reshape(4, 4).T
        M = np.eye(4)
        M[:3, :3] = qmat(nd.get("rotation", [0, 0, 0, 1])) @ np.diag(nd.get("scale", [1, 1, 1]))
        M[:3, 3] = nd.get("translation", [0, 0, 0])
        return M

    recs, extras = [], {}

    def walk(i, M, part):
        nd = js["nodes"][i]
        M = M @ local(nd)
        ex = nd.get("extras") or {}
        if "part" in ex:
            part = ex["part"]
            extras[part] = ex
        if "mesh" in nd:
            mesh = js["meshes"][nd["mesh"]]
            for prim in mesh["primitives"]:
                V, raw = acc(prim["attributes"]["POSITION"])
                Fi = acc(prim["indices"])[1].astype(np.int64).reshape(-1, 3)
                Vw = V @ M[:3, :3].T + M[:3, 3]
                Vm = np.stack([Vw[:, 2], Vw[:, 0], Vw[:, 1]], -1)
                key = raw.astype(np.int64) if raw.dtype.kind in "iu" else np.round(Vm / 1e-6).astype(np.int64)
                recs.append(Rec(part, mesh["name"], mats[prim["material"]], Vm, Fi, key))
        for c in nd.get("children", []):
            walk(c, M, part)

    for r in js["scenes"][js.get("scene", 0)]["nodes"]:
        walk(r, np.eye(4), None)
    return recs, extras


# =====================================================================================================================
# mesh helpers
# =====================================================================================================================
def weld(V, F, key=None):
    """Merge vertices with equal keys (default: positions rounded to 1 um); drop degenerate triangles."""
    k = np.round(V / 1e-6).astype(np.int64) if key is None else key
    _, idx, inv = np.unique(k, axis=0, return_index=True, return_inverse=True)
    inv = inv.ravel()
    F2 = inv[F]
    ok = (F2[:, 0] != F2[:, 1]) & (F2[:, 1] != F2[:, 2]) & (F2[:, 0] != F2[:, 2])
    return V[idx], F2[ok]


def weld_tol(V, F, tol=2.5e-4):
    """Merge vertices closer than tol (sub-meshes of one part were quantised separately)."""
    if not len(V):
        return V, F
    pairs = cKDTree(V).query_pairs(tol, output_type="ndarray")
    n = len(V)
    G_ = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(n, n))
    _, lab = connected_components(G_, directed=False)
    first = np.full(lab.max() + 1, -1)
    first[lab[::-1]] = np.arange(n)[::-1]
    F2 = lab[F]
    ok = (F2[:, 0] != F2[:, 1]) & (F2[:, 1] != F2[:, 2]) & (F2[:, 0] != F2[:, 2])
    return V[first], F2[ok]


def merged(recs, tol=2.5e-4):
    """One welded mesh from several records."""
    if not recs:
        return np.zeros((0, 3)), np.zeros((0, 3), int)
    Vs, Fs, off = [], [], 0
    for r in recs:
        v, f = weld(r.V, r.F, r.key)
        Vs.append(v)
        Fs.append(f + off)
        off += len(v)
    return weld_tol(np.vstack(Vs), np.vstack(Fs), tol)


def boundary_edges(F):
    """Directed boundary edges (used by one triangle)."""
    if not len(F):
        return np.zeros((0, 2), int)
    e = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    lo, hi = np.minimum(e[:, 0], e[:, 1]), np.maximum(e[:, 0], e[:, 1])
    k = lo * (int(F.max()) + 1) + hi
    _, inv, cnt = np.unique(k, return_inverse=True, return_counts=True)
    return e[cnt[inv] == 1]


def _seam_edges(V, be, tol=3e-4):
    """Boundary edges lying on another boundary edge: T-junction seams where separately sampled patches of one
    surface meet (e.g. the wing skin panels at the flap / aileron ends), not real borders."""
    S = np.stack([V[be[:, 0]], V[be[:, 1]]], 1)
    P = densify_segments(S, 1e-4)
    L_ = np.linalg.norm(S[:, 1] - S[:, 0], axis=1)
    n = np.maximum(1, np.ceil(L_ / 1e-4).astype(int)) + 1
    owner = np.repeat(np.arange(len(be)), n)
    tree = cKDTree(P)
    mid = 0.5 * (S[:, 0] + S[:, 1])
    hits = tree.query_ball_point(mid, tol)
    out = np.zeros(len(be), bool)
    for i, h in enumerate(hits):
        o = owner[h]
        other = o[o != i]
        if len(other):
            # an edge sharing a vertex with edge i meets it only at that vertex, never at its midpoint
            out[i] = bool(np.any(~np.isin(be[other], be[i]).any(1)))
    return out


def boundary_components(V, F, min_area=5e-5, drop=None, seams=False):
    """Boundary edge components with their vector area (about the component centroid); zero-area 'cracks' (left
    where the GLB writer dropped zero-area slivers) are discarded.  drop(P0, P1) -> bool mask removes edges first
    (e.g. the open ends of a skin panel, so a hole touching the panel end stays a hole)."""
    if not len(F):
        return []
    be = boundary_edges(F)
    if drop is not None and len(be):
        be = be[~drop(V[be[:, 0]], V[be[:, 1]])]
    if seams and len(be):
        be = be[~_seam_edges(V, be)]
    if not len(be):
        return []
    n = len(V)
    _, lab = connected_components(coo_matrix((np.ones(len(be)), (be[:, 0], be[:, 1])), shape=(n, n)), directed=False)
    el = lab[be[:, 0]]
    out = []
    order = np.argsort(el, kind="stable")
    el_s, be_s = el[order], be[order]
    cuts = np.r_[0, np.nonzero(np.diff(el_s))[0] + 1, len(el_s)]
    for a, b in zip(cuts[:-1], cuts[1:]):
        Ec = be_s[a:b]
        ids = np.unique(Ec)
        c = V[ids].mean(0)
        A = 0.5 * np.cross(V[Ec[:, 0]] - c, V[Ec[:, 1]] - c).sum(0)
        if np.linalg.norm(A) < min_area:
            continue
        out.append(dict(E=Ec, P=V[ids], area=A))
    return out


PANEL_STATIONS = (X0, F.STA["firewall"], FP.SPLIT_FWD, FP.SPLIT_AFT)


def drop_panel_ends(P0, P1, tol=1e-3):
    """Edges on a skin panel's open end (station planes) or on the tail cut (fuselage skins)."""
    m = np.zeros(len(P0), bool)
    for xs in PANEL_STATIONS:
        m |= (np.abs(P0[:, 0] - xs) < tol) & (np.abs(P1[:, 0] - xs) < tol)
    m |= (np.abs(E.tail_cut_field(P0[:, 0], P0[:, 2])) < 2e-3) & (np.abs(E.tail_cut_field(P1[:, 0], P1[:, 2])) < 2e-3)
    return m


def slice_segments(V, F, normal, c):
    """Segments (k, 2, 3) of the intersection of a triangle mesh with the plane normal . p = c."""
    if not len(F):
        return np.zeros((0, 2, 3))
    d = V @ np.asarray(normal, float) - c
    dT = d[F]
    s = dT >= 0
    mixed = ~(s.all(1) | (~s).all(1))
    T, dT, s = F[mixed], dT[mixed], s[mixed]
    if not len(T):
        return np.zeros((0, 2, 3))
    P = np.zeros((len(T), 3, 3))
    cross = np.zeros((len(T), 3), bool)
    for k, (i, j) in enumerate(((0, 1), (1, 2), (2, 0))):
        cr = s[:, i] != s[:, j]
        den = np.where(cr, dT[:, i] - dT[:, j], 1.0)
        t = np.where(cr, dT[:, i] / den, 0.0)
        P[:, k] = V[T[:, i]] + t[:, None] * (V[T[:, j]] - V[T[:, i]])
        cross[:, k] = cr
    idx = np.argsort(~cross, axis=1, kind="stable")[:, :2]
    return P[np.arange(len(T))[:, None], idx]


def densify_segments(S, step):
    """Points along segments (k, 2, dim) at most `step` apart (end points included)."""
    if not len(S):
        return np.zeros((0, S.shape[-1] if S.ndim == 3 else 3))
    L_ = np.linalg.norm(S[:, 1] - S[:, 0], axis=1)
    n = np.maximum(1, np.ceil(L_ / step).astype(int))
    rep = np.repeat(np.arange(len(S)), n + 1)
    start = np.repeat(np.cumsum(np.r_[0, n[:-1] + 1]), n + 1)
    t = (np.arange(len(rep)) - start) / np.repeat(n, n + 1)
    return S[rep, 0] + t[:, None] * (S[rep, 1] - S[rep, 0])


def densify_poly(P, step=5e-4, closed=False):
    P = np.asarray(P, float)
    if closed:
        P = np.vstack([P, P[:1]])
    if len(P) < 2:
        return P
    seg = np.stack([P[:-1], P[1:]], 1)
    return densify_segments(seg, step)


class Curves:
    """Dense point set of labelled polylines for nearest-distance queries (2-D or 3-D)."""

    def __init__(self, polys, step=5e-4, closed=False):
        pts, lab = [], []
        for i, P in enumerate(polys):
            Q = densify_poly(P, step, closed)
            pts.append(Q)
            lab.append(np.full(len(Q), i))
        self.P = np.vstack(pts)
        self.lab = np.concatenate(lab)
        self.tree = cKDTree(self.P)

    def dist(self, Q):
        if not len(Q):
            return np.zeros(0), np.zeros(0, int)
        d, i = self.tree.query(np.asarray(Q, float))
        return d, self.lab[i]


def tri_samples(V, F):
    """7 sample points per triangle (centroid, 3 towards the vertices, 3 towards the edges) and per-sample area."""
    A, B, C = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    w = np.array([[1 / 3, 1 / 3, 1 / 3], [2 / 3, 1 / 6, 1 / 6], [1 / 6, 2 / 3, 1 / 6], [1 / 6, 1 / 6, 2 / 3],
                  [1 / 6, 5 / 12, 5 / 12], [5 / 12, 1 / 6, 5 / 12], [5 / 12, 5 / 12, 1 / 6]])
    P = w[None, :, 0, None] * A[:, None] + w[None, :, 1, None] * B[:, None] + w[None, :, 2, None] * C[:, None]
    area = 0.5 * np.linalg.norm(np.cross(B - A, C - A), axis=1)
    return P.reshape(-1, 3), np.repeat(area / 7.0, 7), np.repeat(np.arange(len(F)), 7)


# =====================================================================================================================
# report
# =====================================================================================================================
@dataclass
class Row:
    sheet: str
    item: str
    n: int
    max_mm: float | None
    rms_mm: float | None
    tol_mm: float | None
    status: str
    detail: str = ""
    worst: list = field(default_factory=list)


class Report:
    def __init__(self, verbose=False):
        self.rows = []
        self.verbose = verbose

    def add(self, sheet, item, dev_m=None, tol=None, detail="", worst=None, status=None, n=None, max_mm=None):
        """dev_m: deviations (m); tol in mm.  status overrides the comparison (PASS / FAIL / INFO)."""
        mx = rms = None
        if dev_m is not None and len(dev_m):
            d = np.abs(np.asarray(dev_m, float)) * 1000.0
            mx, rms = float(d.max()), float(np.sqrt(np.mean(d ** 2)))
            n = len(d) if n is None else n
        if max_mm is not None:
            mx = max_mm
        if status is None:
            if mx is None:
                status = "FAIL"
                detail = (detail + "; " if detail else "") + "no samples"
            else:
                status = "PASS" if (tol is None or mx <= tol) else "FAIL"
        r = Row(sheet, item, int(n or 0), mx, rms, tol, status, detail, list(worst or []))
        self.rows.append(r)
        mxs = "   -   " if mx is None else f"{mx:7.1f}"
        rms_s = "   -   " if rms is None else f"{rms:7.1f}"
        tol_s = "  - " if tol is None else f"{tol:4.0f}"
        print(f"  {status:4s} {sheet} {item[:58]:58s} {mxs} {rms_s} {tol_s} {r.n:8d}  {detail}", flush=True)
        if self.verbose or status == "FAIL":
            for w in r.worst[:6]:
                print(f"         worst: {w}")
        return r


def worst_list(dev, P, labels=None, k=5, fmt="x {:.3f} y {:+.3f} z {:.3f}"):
    """Descriptions of the k largest |dev| samples."""
    dev = np.abs(np.asarray(dev, float))
    if not len(dev):
        return []
    idx = np.argsort(-dev)[:k]
    out = []
    for i in idx:
        s = f"{dev[i] * 1000:.1f} mm at " + fmt.format(*P[i])
        if labels is not None:
            s += f" ({labels[i]})"
        out.append(s)
    return out


# =====================================================================================================================
# context: records grouped by part / material
# =====================================================================================================================
class Ctx:
    def __init__(self, recs, extras):
        self.recs = recs
        self.extras = extras
        self.by_part = {}
        for r in recs:
            self.by_part.setdefault(r.part, []).append(r)

    def get(self, part, mats=None, exclude=()):
        return [r for r in self.by_part.get(part, []) if (mats is None or r.mat in mats) and r.mat not in exclude]

    def verts(self, part, mats=None, exclude=()):
        rs = self.get(part, mats, exclude)
        return np.vstack([r.V for r in rs]) if rs else np.zeros((0, 3))

    def mesh(self, parts, mats=None, exclude=(), weld_parts=False):
        """(V, F) of all records of the parts (per-record weld; weld_tol across records if weld_parts)."""
        rs = [r for p in parts for r in self.get(p, mats, exclude)]
        if weld_parts:
            return merged(rs)
        Vs, Fs, off = [], [], 0
        for r in rs:
            v, f = weld(r.V, r.F, r.key)
            Vs.append(v)
            Fs.append(f + off)
            off += len(v)
        if not Vs:
            return np.zeros((0, 3)), np.zeros((0, 3), int)
        return np.vstack(Vs), np.vstack(Fs)


def paint_mats():
    return SIDE_PAINT | {"paint_white"}


def skin_mesh(ctx, with_doors=True, with_lip=True):
    """The fuselage OML skin as built: skins (tail-cone closure removed), door slabs (outer), chin-inlet lip."""
    V, Fm = ctx.mesh(SKIN_PARTS, mats=paint_mats())
    fc = E.tail_cut_field(V[:, 0], V[:, 2])
    closure = (np.abs(fc[Fm]) < 5e-4).all(1)
    Fm = Fm[~closure]
    parts = [(V, Fm)]
    if with_doors:
        parts.append(ctx.mesh(DOOR_PARTS, mats=paint_mats()))
    if with_lip:
        parts.append(ctx.mesh(("chin_inlet",), mats=("chrome",)))
    Vs, Fs, off = [], [], 0
    for v, f in parts:
        Vs.append(v)
        Fs.append(f + off)
        off += len(v)
    return np.vstack(Vs), np.vstack(Fs)


def oml_dist(P):
    """Signed normal distance (m, + outside) of points to the OML (section law, first order)."""
    xc = F.clip_x(P[:, 0])
    return F._OML.section_distance(xc, P[:, 1], P[:, 2])


def expected_skin_hole(P, painted=False):
    """True where the parameter OML point P is NOT covered by the built outer skin:
    cabin windows, cockpit glazing, the nose-gear bay, the chin-inlet mouth, the tail cone aft of the rudder cut,
    the door windows and the DOOR_GAP ring round the door slabs (the slabs cover the rest of the seam holes);
    painted=True also excludes the (unpainted) polished chin-inlet lip."""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    hole = np.zeros(len(P), bool)
    for side, stations in FP.FIXED_WINDOWS.items():
        on = y * side > 0.2
        for cx in stations:
            hole |= on & (FP.window_sdf(x, z, cx) < 0)
    hole |= CG.sidewindow_sdf(x, y, z) < 0
    hole |= CG.windshield_sdf(x, None, z, y) < 0
    hole |= (z < 1.1) & (BY.nose_bay_sdf(x, y) < 0)
    fm, fl, fs = PP.chin_fields(P)
    hole |= (fm < 0) & (x <= PP.CHIN_STEP_X_MAX)
    if painted:                                             # the polished chin-inlet lip is skin, but not painted
        hole |= (np.maximum(fl, fs) < 0.0015)
    hole |= E.tail_cut_field(x, z) > 0
    for pid, o in FP.DOORS:
        pan = FP.door_panel(o)
        on = y * o["side"] > 0.2
        rr = FP.rr((x, z), pan)
        hole |= on & (rr > -FP.DOOR_GAP - 0.0015) & (rr < 0.0015)
        wcx = FP.DOOR_WINDOWS.get(pid)
        if wcx is not None:
            hole |= on & (FP.window_sdf(x, z, wcx) < 0.0015)
    return hole


# =====================================================================================================================
# L1  lines plan
# =====================================================================================================================
def check_L1(ctx, rep, plots):
    V, Fm = skin_mesh(ctx)
    used = np.unique(Fm)
    P = V[used]
    out_rng = (P[:, 0] < X0 - 1e-3) | (P[:, 0] > X1 + 1e-3)
    d = oml_dist(P)
    rep.add("L1", "skin vertices on the OML (section law)", d, TOL["oml"],
            f"{len(SKIN_PARTS)} skins + door slabs + inlet lip; {int(out_rng.sum())} outside STA {X0:.3f}-{X1:.3f}",
            worst_list(d, P))

    # ---- profile: crown / keel at BL 0
    S = slice_segments(V, Fm, (0, 1, 0), 0.0)
    Q = densify_segments(S, 0.005)
    xs = np.linspace(X0, X1, 6001)
    up = Q[:, 2] > F.z_mw(F.clip_x(Q[:, 0]))
    crown = Curves([np.c_[xs, F.z_top(xs)]])
    keel = Curves([np.c_[xs, F.z_bot(xs)]])
    dc, _ = crown.dist(Q[up][:, [0, 2]])
    dk, _ = keel.dist(Q[~up][:, [0, 2]])
    rep.add("L1", "profile: crown line at BL 0 (mesh -> z_top)", dc, TOL["oml"], "", worst_list(dc, Q[up]))
    rep.add("L1", "profile: keel line at BL 0 (mesh -> z_bot)", dk, TOL["oml"], "", worst_list(dk, Q[~up]))
    # both ways: every parameter crown / keel point outside the parameter holes has skin within the tolerance
    tree = cKDTree(Q[:, [0, 2]]) if len(Q) else None
    for name, fz, t in (("crown", F.z_top, 0.0), ("keel", F.z_bot, 0.5)):
        xx = np.arange(X0 + 0.002, X1, 0.004)
        Pp = np.c_[xx, np.zeros_like(xx), fz(xx)]
        keep = ~expected_skin_hole(Pp)
        dd = tree.query(Pp[keep][:, [0, 2]])[0] if tree is not None else np.full(keep.sum(), 9.0)
        gaps = xx[keep][dd > TOL["oml"] / 1000]
        rep.add("L1", f"profile: {name} covered by skin (z_{'top' if t == 0 else 'bot'} -> mesh)", dd, TOL["oml"],
                f"parameter holes excluded; uncovered STA {_runs_str(gaps)}" if len(gaps) else
                "parameter holes (nose bay, chin mouth, tail cut) excluded", worst_list(dd, Pp[keep]))

    # ---- half-breadth (plan): max |y| near the max-breadth WL, per side
    devs, locs = [], []
    for x in np.arange(X0 + 0.01, X1 - 0.01, 0.05):
        zm = float(F.z_mw(x))
        if E.tail_cut_field(x, zm) > -0.01:
            continue
        S = slice_segments(V, Fm, (1, 0, 0), x)
        if not len(S):
            devs.append(1.0)
            locs.append((x, 0.0, zm))
            continue
        Qx = densify_segments(S, 0.003)
        for side in (1, -1):
            m = (Qx[:, 1] * side > 0) & (np.abs(Qx[:, 2] - zm) < 0.03)
            if not m.any():
                continue                                    # an opening at the max-breadth line (door gap)
            devs.append(np.abs(Qx[m, 1]).max() - float(F.half_w(x)))
            locs.append((x, side * float(F.half_w(x)), zm))
    rep.add("L1", "half-breadth (plan): max |y| at z_mw vs half_w", np.array(devs), TOL["oml"],
            f"STA {X0:.2f}-{X1:.2f} every 50 mm, both sides", worst_list(devs, np.array(locs)))

    # ---- body plan at the Pilatus frames, both ways
    t = np.linspace(0, 1, 7200, endpoint=False)
    all_m2p, all_p2m, w1, w2 = [], [], [], []
    per = []
    for name, x in F.FRAMES.items():
        sec = F.section(np.full_like(t, x), t)
        S = slice_segments(V, Fm, (1, 0, 0), x)
        Qx = densify_segments(S, 0.002)
        cur = Curves([sec[:, 1:]], closed=True)
        dm, _ = cur.dist(Qx[:, 1:])
        hole = expected_skin_hole(sec)
        tr = cKDTree(Qx[:, 1:]) if len(Qx) else None
        dp = tr.query(sec[~hole][:, 1:])[0] if tr is not None else np.full((~hole).sum(), 9.0)
        all_m2p.append(dm)
        all_p2m.append(dp)
        per.append(f"{name} {1000 * (dm.max() if len(dm) else np.nan):.1f}/{1000 * dp.max():.1f}")
        w1 += worst_list(dm, Qx, [name] * len(Qx), k=2)
        w2 += worst_list(dp, sec[~hole], [name] * int((~hole).sum()), k=2)
    dm, dp = np.concatenate(all_m2p), np.concatenate(all_p2m)
    rep.add("L1", "body plan at FRAMES: mesh section -> parameter section", dm, TOL["oml"],
            f"{len(F.FRAMES)} frames", sorted(w1, key=lambda s: -float(s.split()[0]))[:6])
    rep.add("L1", "body plan at FRAMES: parameter section -> mesh (holes excl.)", dp, TOL["oml"],
            "max mm per frame (mesh->param/param->mesh): " + ", ".join(per[:6]) + " ...",
            sorted(w2, key=lambda s: -float(s.split()[0]))[:6])
    if plots:
        _plot_frames(V, Fm, plots)


def _runs_str(xs, gap=0.02):
    xs = np.sort(np.asarray(xs))
    if not len(xs):
        return "-"
    br = np.nonzero(np.diff(xs) > gap)[0]
    starts = np.r_[xs[0], xs[br + 1]]
    ends = np.r_[xs[br], xs[-1]]
    return ", ".join(f"{a:.3f}-{b:.3f}" for a, b in zip(starts, ends))


# =====================================================================================================================
# L2  cockpit glazing + PRO mask
# =====================================================================================================================
def check_L2(ctx, rep, plots):
    V, Fm = ctx.mesh(("fus_fwd",), mats=paint_mats(), weld_parts=True)
    holes = boundary_components(V, Fm, drop=drop_panel_ends)
    sw_out = Curves([CG.side_outline("sw")], closed=True)
    ws_edges = {s: CG.edges(s, which=("ws",))["ws"] for s in (1, -1)}
    ws_cur = {s: Curves(ws_edges[s], step=0.001) for s in (1, -1)}
    found = {"sw": [], "ws": []}
    other = []
    for c in holes:
        P = c["P"]
        ya = np.abs(P[:, 1])
        side = 1 if P[:, 1].mean() > 0 else -1
        if P[:, 2].mean() > 2.0 and 3.1 < P[:, 0].mean() < 4.45 and ya.min() > 0.3:
            d, _ = sw_out.dist(P[:, [0, 2]])
            found["sw"].append((side, d, P))
        elif P[:, 2].mean() > 2.0 and 3.1 < P[:, 0].mean() < 4.2 and ya.min() < 0.1:
            d, _ = ws_cur[side].dist(P)
            found["ws"].append((side, d, P))
        elif P[:, 2].max() < 1.1:
            pass                                                # nose-gear bay (L3)
        else:
            other.append(c)
    for key, name, n_exp, how in (("sw", "side-window holes vs side_outline('sw') (side proj.)", 2, "x/z"),
                                  ("ws", "windshield holes vs cockpit_glazing.edges() (3-D)", 2, "3-D")):
        sides = sorted(s for s, _, _ in found[key])
        d = np.concatenate([d for _, d, _ in found[key]]) if found[key] else np.zeros(0)
        P = np.vstack([p for _, _, p in found[key]]) if found[key] else np.zeros((0, 3))
        ok = len(found[key]) == n_exp and sides == [-1, 1]
        rep.add("L2", name, d, TOL["glazing"], f"{len(found[key])} holes (sides {sides})",
                worst_list(d, P), status=None if ok else "FAIL")
    if other:
        rep.add("L2", "unexpected holes in the forward fuselage skin", status="FAIL",
                detail="; ".join(f"x {c['P'][:, 0].mean():.3f} y {c['P'][:, 1].mean():+.3f} z {c['P'][:, 2].mean():.3f}"
                                 for c in other[:5]))

    # ---- glass covers the holes: the glass edge lies outside the pane outline (nominal 10 / 12 mm)
    for mat, name, fld, nom, off in (
            ("glass", "side-window glass edge beyond the pane outline", lambda P: CG.sidewindow_sdf(P[:, 0], P[:, 1], P[:, 2]), 0.010, 0.005),
            ("glass_windshield", "windshield glass edge beyond the pane outline", lambda P: CG.windshield_sdf(P[:, 0], None, P[:, 2], P[:, 1]), 0.012, 0.004)):
        Vg, Fg = ctx.mesh(("glazing_flightdeck",), mats=(mat,))
        comps = boundary_components(Vg, Fg, min_area=1e-4)
        P = np.vstack([c["P"] for c in comps]) if comps else np.zeros((0, 3))
        f = fld(P)
        dev = np.abs(f - nom)
        ok = len(P) and f.min() > 0 and dev.max() <= TOL["glazing"] / 1000 + off
        rep.add("L2", name, dev, TOL["glazing"], f"overlap {1000 * f.min():.1f}..{1000 * f.max():.1f} mm (nominal "
                f"{1000 * nom:.0f}, glass offset {1000 * off:.0f} mm inward; must stay > 0)", worst_list(dev, P),
                status="PASS" if ok else "FAIL")

    # ---- PRO mask: colour boundary of 'trim_black' vs the mask outline (side projection)
    mask_cur = Curves([CG.side_outline("mask")], closed=True)
    Pb = []
    for pid in L.MASK_PARTS:
        cb = colour_boundaries(ctx, pid)
        for P, ma, mb in cb:
            if "trim_black" in (ma, mb):
                Pb.append(P)
    Pb = np.vstack(Pb) if Pb else np.zeros((0, 3))
    d, _ = mask_cur.dist(Pb[:, [0, 2]])
    rep.add("L2", "PRO mask colour boundary vs side_outline('mask')", d, TOL["glazing"],
            f"on {', '.join(L.MASK_PARTS)}", worst_list(d, Pb))
    # the mask reaches its designed aft edge on the skin (continuous across SPLIT_FWD)
    loops = CG.edges(1, which=("mask",))["mask"] + CG.edges(-1, which=("mask",))["mask"]
    xa = max(float(lp[:, 0].max()) for lp in loops)
    Vm = np.vstack([ctx.verts(p, mats=("trim_black",)) for p in L.MASK_PARTS if ctx.get(p, mats=("trim_black",))])
    xm = float(Vm[:, 0].max())
    cen = ctx.verts("fus_center", mats=("trim_black",))
    rep.add("L2", "PRO mask aft extent on the skin (max STA)", np.array([xm - xa]), TOL["glazing"],
            f"mesh {xm:.3f} vs mask on the OML {xa:.3f}; on fus_center: {len(cen)} verts "
            f"(SPLIT_FWD {FP.SPLIT_FWD:.2f})")
    if plots:
        _plot_side(plots / "L2_glazing.png", [(CG.side_outline("sw"), "k"), (CG.side_outline("mask"), "k")],
                   [(np.vstack([p for _, _, p in found["sw"]]) if found["sw"] else np.zeros((0, 3)), "b"),
                    (Pb, "r")], (3.0, 4.8, 1.9, 2.9))


def colour_boundaries(ctx, pid, mats=None, tol=3e-4, segments=False):
    """Colour boundaries of a part: boundary vertices of a painted sub-mesh that coincide with a boundary vertex of a
    sub-mesh of another material -> list of (P (n, 3), material, other material); segments=True returns the boundary
    edges (k, 2, 3) between two such vertices instead of the vertices."""
    mats = SIDE_PAINT | {"paint_white"} if mats is None else mats
    rs = [r for r in ctx.get(pid) if r.mat in mats]
    wel = [weld(r.V, r.F, r.key) for r in rs]
    bes = [boundary_edges(f) if len(f) else np.zeros((0, 2), int) for _, f in wel]
    bps = [v[np.unique(be)] if len(be) else np.zeros((0, 3)) for (v, _), be in zip(wel, bes)]
    trees = [cKDTree(b) if len(b) else None for b in bps]
    out = []
    for i, r in enumerate(rs):
        if not len(bps[i]):
            continue
        v = wel[i][0]
        if segments:                                # both ends on the border of any other-material sub-mesh
            oth = [bps[j] for j, r2 in enumerate(rs) if r2.mat != r.mat and len(bps[j])]
            if not oth:
                continue
            tr = cKDTree(np.vstack(oth))
            be = bes[i]
            d0 = tr.query(v[be[:, 0]], distance_upper_bound=tol)[0]
            d1 = tr.query(v[be[:, 1]], distance_upper_bound=tol)[0]
            m = np.isfinite(d0) & np.isfinite(d1)
            if m.any():
                out.append((np.stack([v[be[m, 0]], v[be[m, 1]]], 1), r.mat, "other"))
            continue
        for j, r2 in enumerate(rs):
            if r2.mat == r.mat or trees[j] is None:
                continue
            d, _ = trees[j].query(bps[i], distance_upper_bound=tol)
            m = np.isfinite(d)
            if m.any():
                out.append((bps[i][m], r.mat, r2.mat))
    return out


# =====================================================================================================================
# L3  openings
# =====================================================================================================================
def check_L3(ctx, rep, plots):
    comps = []
    for pid in ("fus_fwd", "fus_center", "fus_aft"):
        V, Fm = ctx.mesh((pid,), mats=paint_mats(), weld_parts=True)
        h = boundary_components(V, Fm, drop=drop_panel_ends)
        comps += [(pid, c) for c in h]
    table = FP.openings_table()
    rows = [r for r in table if r["host"] is None]          # windows in doors are cut in the door slabs
    expected = []
    for r in rows:
        if r["kind"] == "window":
            outline = FP.window_outline(r["cx"], 2000)
        else:
            outline = FP.opening_outline(FP.DOOR_PANELS[r["id"]], 64)
        expected.append((r, outline))
    matched = {r["id"]: [] for r, _ in expected}
    unexpected = []
    for pid, c in comps:
        P = c["P"]
        side = 1 if P[:, 1].mean() > 0 else -1
        xc, zc = 0.5 * (P[:, 0].min() + P[:, 0].max()), 0.5 * (P[:, 2].min() + P[:, 2].max())
        hit = None
        for r, outline in expected:
            if r["side"] != side:
                continue
            if outline[:, 0].min() - 0.02 < xc < outline[:, 0].max() + 0.02 and \
                    outline[:, 1].min() - 0.02 < zc < outline[:, 1].max() + 0.02:
                hit = r["id"]
        if hit is not None:
            matched[hit].append(P)
            continue
        if P[:, 2].max() < 1.1 and BY.nose_bay_sdf(P[:, 0], P[:, 1]).max() < 0.01:
            continue                                            # nose-gear bay
        if 3.0 < P[:, 0].mean() < 4.45 and P[:, 2].mean() > 2.0:
            continue                                            # cockpit glazing (L2)
        unexpected.append((pid, P))
    groups = {"cabin windows (Lame 300 x 385)": [], "airstair door-panel seam": [], "cargo door-panel seam": [],
              "over-wing exit seam": []}
    missing = []
    for r, outline in expected:
        Ps = matched[r["id"]]
        if len(Ps) != 1:
            missing.append(f"{r['id']} ({len(Ps)} holes)")
            continue
        P = Ps[0]
        d, _ = Curves([outline]).dist(P[:, [0, 2]])
        key = {"door_airstair": "airstair door-panel seam", "door_cargo": "cargo door-panel seam",
               "exit_hatch": "over-wing exit seam"}.get(r["id"], "cabin windows (Lame 300 x 385)")
        groups[key].append((r["id"], d, P))
    for key, lst in groups.items():
        if not lst:
            rep.add("L3", f"skin hole: {key}", status="FAIL", detail="not found")
            continue
        d = np.concatenate([x[1] for x in lst])
        P = np.vstack([x[2] for x in lst])
        ids = sum([[x[0]] * len(x[1]) for x in lst], [])
        rep.add("L3", f"skin holes: {key} (side proj.)", d, TOL["opening"], f"{len(lst)} openings",
                worst_list(d, P, ids))
    rep.add("L3", "every parameter opening cut once, no extra holes", status="FAIL" if (missing or unexpected) else "PASS",
            n=len(comps), detail=("missing/duplicate: " + ", ".join(missing) if missing else "") +
            ("; unexpected: " + "; ".join(f"{pid} x {P[:, 0].mean():.3f} y {P[:, 1].mean():+.3f} z {P[:, 2].mean():.3f}"
                                          for pid, P in unexpected[:6]) if unexpected else "") or
            f"{len(expected)} openings (openings_table, host None)")

    # ---- door slabs: outer edge DOOR_GAP inside the panel seam, door windows
    dev_s, P_s, dev_w, P_w = [], [], [], []
    for pid, o in FP.DOORS:
        pan = FP.door_panel(o)
        V, Fm = ctx.mesh((pid,), mats=paint_mats(), weld_parts=True)
        comps = boundary_components(V, Fm)
        wcx = FP.DOOR_WINDOWS.get(pid)
        for c in comps:
            P = c["P"]
            rr = FP.rr((P[:, 0], P[:, 2]), pan)
            if wcx is not None and np.abs(FP.window_sdf(P[:, 0], P[:, 2], wcx)).mean() < np.abs(rr).mean():
                dw = FP.window_sdf(P[:, 0], P[:, 2], wcx)
                dev_w.append(dw)
                P_w.append(P)
            else:
                dev_s.append(rr + FP.DOOR_GAP)
                P_s.append(P)
    rep.add("L3", "door / exit slab edge vs panel seam - DOOR_GAP", np.concatenate(dev_s) if dev_s else None,
            TOL["opening"], "airstair, cargo, exit (DOOR_PANELS)", worst_list(np.concatenate(dev_s), np.vstack(P_s))
            if dev_s else [])
    rep.add("L3", "door windows (cargo 7.958, exit 6.205) in the slabs", np.concatenate(dev_w) if dev_w else None,
            TOL["opening"], f"{len(dev_w)} windows", worst_list(np.concatenate(dev_w), np.vstack(P_w)) if dev_w else [])

    # ---- clear openings: the door stops (door_frames, last 'jamb' mesh) inner edge, projected back onto the OML
    recs = [r for r in ctx.get("door_frames") if r.mat == "jamb"]
    stops = recs[-1] if recs else None
    if stops is not None:
        v, f = weld(stops.V, stops.F, stops.key)
        depth = -oml_dist(v)
        comps = boundary_components(v, f)
        devs, Ps, labs = [], [], []
        for c in comps:
            P = c["P"]
            Pb = _to_oml(P)
            for pid, o in FP.DOORS:
                if FP.door_panel(o) is o:
                    continue
                on = P[:, 1].mean() * o["side"] > 0
                rr_o = FP.rr((Pb[:, 0], Pb[:, 2]), o)
                rr_p = FP.rr((Pb[:, 0], Pb[:, 2]), FP.door_panel(o)) + 0.002       # outer loop: 2 mm inside the seam
                if on and np.abs(rr_o).mean() < min(0.03, np.abs(rr_p).mean()):
                    devs.append(rr_o)
                    Ps.append(Pb)
                    labs += [pid] * len(P)
        d = np.concatenate(devs) if devs else None
        rep.add("L3", "clear openings (door stops, back on the OML) vs AIRSTAIR / CARGO", d, TOL["opening"],
                f"stop depth {1000 * np.median(depth):.0f} mm inside the OML; {len(devs)} loops",
                worst_list(d, np.vstack(Ps), labs) if devs else [], status=None if len(devs) == 2 else "FAIL")

    # ---- cabin-window glass covers the holes (edge 10 mm beyond the Lame outline, glass 6 mm inward)
    Vg, Fg = ctx.mesh(("glazing_cabin",), mats=("glass",))
    comps = boundary_components(Vg, Fg, min_area=1e-4)
    f_all, P_all = [], []
    for c in comps:
        P = c["P"]
        side = 1 if P[:, 1].mean() > 0 else -1
        cxs = np.array(FP.FIXED_WINDOWS[side])
        cx = cxs[np.argmin(np.abs(cxs - P[:, 0].mean()))]
        f_all.append(FP.window_sdf(P[:, 0], P[:, 2], cx))
        P_all.append(P)
    f = np.concatenate(f_all) if f_all else np.zeros(0)
    dev = np.abs(f - 0.010)
    ok = len(f) and f.min() > 0 and dev.max() <= TOL["opening"] / 1000 + 0.006
    n_fixed = sum(len(v) for v in FP.FIXED_WINDOWS.values())
    rep.add("L3", "cabin-window glass edge beyond the Lame outline", dev, TOL["opening"],
            f"{len(comps)}/{n_fixed} panes; overlap {1000 * f.min():.1f}..{1000 * f.max():.1f} mm (nominal 10)"
            if len(f) else "no glass", worst_list(dev, np.vstack(P_all)) if P_all else [],
            status="PASS" if ok and len(comps) == n_fixed else "FAIL")
    if plots:
        outl = [(o, "k") for _, o in expected]
        _plot_side(plots / "L3_openings.png", outl, [(np.vstack([P for p in matched.values() for P in p]), "b")],
                   (4.3, 9.1, 1.1, 2.8))


def _to_oml(P, iters=3):
    """Project points onto the OML along the numerical gradient of the section-law distance."""
    Q = P.copy()
    h = 1e-4
    for _ in range(iters):
        d = oml_dist(Q)
        g = np.zeros_like(Q)
        for k in range(3):
            e = np.zeros(3)
            e[k] = h
            g[:, k] = (oml_dist(Q + e) - oml_dist(Q - e)) / (2 * h)
        g /= np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-12)
        Q = Q - d[:, None] * g
    return Q


# =====================================================================================================================
# L4  layout
# =====================================================================================================================
XC = cos_pts(600)


def _rot_x(ang):
    c, s_ = math.cos(ang), math.sin(ang)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s_], [0.0, s_, c]])


def sec_loop(sec, xc=XC):
    return np.vstack([sec.lower(xc[::-1]), sec.upper(xc[1:])])


def loop_compare(Q, loop, hole=None):
    """Two-way comparison of mesh section points Q (k, 2) with a closed parameter section loop (n, 2): parameter ->
    mesh for the loop points outside `hole` (bool mask), mesh -> parameter for the mesh points OUTSIDE the loop
    (points inside are coves, ribs, control-surface noses and other interior surfaces).  Returns (d_p2m, d_m2p)."""
    from matplotlib.path import Path as MPath
    keep = np.ones(len(loop), bool) if hole is None else ~hole
    d_p2m = cKDTree(Q).query(loop[keep])[0] if len(Q) else np.full(int(keep.sum()), 9.0)
    outside = ~MPath(loop).contains_points(Q)
    d_m2p = Curves([loop], closed=True).dist(Q[outside])[0] if outside.any() else np.zeros(1)
    return d_p2m, d_m2p


def plan_silhouette(V, Fm, box, res=0.001, close_r=0.008, axes=(0, 1)):
    """Boundary points (k, 2) of the view projection (axes) of a mesh inside box (a0, b0, a1, b1): triangles
    rasterised at `res`, gaps narrower than 2 close_r closed (spanwise control-surface gaps)."""
    from PIL import Image, ImageDraw
    from scipy import ndimage
    a0, b0, a1, b1 = box
    W_, H_ = int(math.ceil((a1 - a0) / res)) + 1, int(math.ceil((b1 - b0) / res)) + 1
    img = Image.new("1", (W_, H_), 0)
    dr = ImageDraw.Draw(img)
    T = V[Fm][:, :, list(axes)]
    T = (T - [a0, b0]) / res
    for t in T:
        dr.polygon([tuple(p) for p in t], fill=1, outline=1)
    m = np.array(img, bool)
    k = int(round(close_r / res))
    yy, xx = np.mgrid[-k:k + 1, -k:k + 1]
    disk = xx ** 2 + yy ** 2 <= k * k
    m = ndimage.binary_closing(np.pad(m, k + 1), structure=disk)[k + 1:-k - 1, k + 1:-k - 1]
    edge = m & ~ndimage.binary_erosion(m)
    r, c = np.nonzero(edge)
    return np.c_[a0 + (c + 0.5) * res, b0 + (r + 0.5) * res]


def check_L4(ctx, rep, plots):
    tolp = TOL["planform"]
    # ---------------------------------------------------------------- wing sections (both wings)
    ys = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.4, 5.9, 6.3, 6.7, 7.0, 7.3]
    acc = {k: ([], []) for k in ("le", "te", "up", "lo", "p2m", "m2p", "lip", "ail", "tip")}

    def put(k, d, loc):
        acc[k][0].append(d)
        acc[k][1].append(loc)
    for side, sg in (("R", 1), ("L", -1)):
        Va, Fa = ctx.mesh((f"wing_{side}", f"flap_{side}", f"aileron_{side}", f"ail_tab_{side}"), exclude=("black",))
        Vw, Fw = ctx.mesh((f"wing_{side}",), exclude=("black", "deice_boot"))
        for y in ys:
            sec = W.section_at(y)
            loop = sec_loop(sec) * [1, sg, 1]
            S = slice_segments(Va, Fa, (0, 1, 0), sg * y)
            Q = densify_segments(S, 0.001)
            if not len(Q):
                put("le", 1.0, (float(W.x_le(y)), sg * y, 0))
                continue
            put("le", Q[:, 0].min() - loop[:, 0].min(), (loop[:, 0].min(), sg * y, float(sec.le[2])))
            put("te", Q[:, 0].max() - loop[:, 0].max(), (loop[:, 0].max(), sg * y, float(sec.le[2])))
            put("up", Q[:, 2].max() - loop[:, 2].max(), (sec.le[0], sg * y, loop[:, 2].max()))
            put("lo", Q[:, 2].min() - loop[:, 2].min(), (sec.le[0], sg * y, loop[:, 2].min()))
            n_lo = len(XC)                                      # the loop's first n_lo points: lower surface
            well = np.zeros(len(loop), bool)
            well[:n_lo] = BY.main_opening_sdf(loop[:n_lo, 0], loop[:n_lo, 1]) < 0.002    # wheel well + leg slot
            dp, dm = loop_compare(Q[:, [0, 2]], loop[:, [0, 2]], well)
            put("p2m", dp.max(), (y * sg, float(dp.max())))
            put("m2p", dm.max(), (y * sg, float(dm.max())))
            # flap lip / aileron gap line: aft end of the wing part's upper skin
            Sw = slice_segments(Vw, Fw, (0, 1, 0), sg * y)
            Qw = densify_segments(Sw, 0.001)
            le_p, te_p = sec.point(np.array(0.0), np.array(0.0)), sec.point(np.array(1.0), np.array(0.0))
            zc = le_p[2] + (Qw[:, 0] - le_p[0]) * (te_p[2] - le_p[2]) / (te_p[0] - le_p[0])
            upq = Qw[Qw[:, 2] > zc]
            if W.Y_FLAP[0] + 0.3 < y < W.Y_FLAP[1] - 0.2 and len(upq):
                put("lip", upq[:, 0].max() - float(W.flap_lines(y, True)), (float(W.flap_lines(y, True)), sg * y, 0))
            if W.Y_AIL[0] + 0.15 < y < W.Y_AIL[1] - 0.05 and len(upq):
                put("ail", upq[:, 0].max() - float(W.ail_gap_x(y, True)), (float(W.ail_gap_x(y, True)), sg * y, 0))
        put("tip", np.abs(Vw[:, 1]).max() - W.SEMI, (float(W.x_le(W.SEMI)), sg * W.SEMI, 0))
    names = {"le": "wing LE (plan, min STA of the section) vs section_at LE",
             "te": "wing TE (plan, max STA) incl. flap / aileron / tab",
             "up": "wing front silhouette: upper WL vs section", "lo": "wing front silhouette: lower WL vs section",
             "p2m": "wing sections: parameter loop -> mesh (side proj.)",
             "m2p": "wing sections: mesh -> parameter loop (side proj.)",
             "lip": "flap shroud lip (plan) vs wing.flap_lines(upper)",
             "ail": "aileron upper gap line (plan) vs wing.ail_gap_x", "tip": "tip rib BL (max |y| of wing skin) vs SEMI"}
    for k, nm in names.items():
        d, loc = acc[k]
        if k in ("p2m", "m2p"):
            rep.add("L4", nm, np.array(d), tolp, f"BL {ys[0]}-{ys[-1]}, both wings",
                    [f"{1000 * v:.1f} mm at BL {l[0]:+.2f}" for v, l in sorted(zip(d, loc), key=lambda t: -t[0])[:4]])
        else:
            rep.add("L4", nm, np.array(d), tolp, "both wings", worst_list(d, np.array(loc)))

    # ---------------------------------------------------------------- winglets: sections along the path
    secs = W.winglet_sections(40, 30)
    dP, dM, dLE, dTE, locs = [], [], [], [], []
    for side, sg in (("R", 1), ("L", -1)):
        Vl, Fl = ctx.mesh((f"winglet_{side}",), exclude=("black",))
        for sec in secs[1:-1]:
            M = np.diag([1.0, sg, 1.0])
            e_s = np.cross(sec.e_c, sec.e_t)
            n = M @ e_s
            p0 = M @ sec.le
            loop = sec_loop(sec) @ M
            S = slice_segments(Vl, Fl, n, float(n @ p0))
            Q = densify_segments(S, 0.001)
            Q = Q[np.linalg.norm(Q - p0, axis=1) < 1.5 * sec.chord + 0.1]
            if not len(Q):
                dP.append(1.0)
                continue
            tq = cKDTree(Q)
            dP.append(tq.query(loop)[0].max())
            dM.append(Curves([loop], closed=True).dist(Q)[0].max())
            dLE.append(tq.query(M @ sec.point(np.array(0.0), np.array(0.0)))[0])
            dTE.append(tq.query(M @ sec.point(np.array(1.0), np.array(0.0)))[0])
            locs.append(M @ sec.le)
    locs = np.array(locs)
    rep.add("L4", "winglet sections: parameter loop -> mesh (3-D)", np.array(dP), tolp,
            f"{len(secs) - 2} sections x 2 (winglet_sections(40, 30))", worst_list(dP, locs))
    rep.add("L4", "winglet sections: mesh -> parameter loop (3-D)", np.array(dM), tolp, "", worst_list(dM, locs))
    rep.add("L4", "winglet LE / TE points (plan + front outline) -> mesh", np.r_[dLE, dTE], tolp,
            "", worst_list(np.r_[dLE, dTE], np.r_[locs, locs]))
    wg_top = max(max(float(s.upper(XC)[:, 2].max()) for s in secs), float(sec_loop(secs[-1])[:, 2].max()))
    wg_y = max(max(float(s.lower(XC)[:, 1].max()) for s in secs), float(sec_loop(secs[-1])[:, 1].max()))
    Vr = ctx.verts("winglet_R", exclude=("black",))
    rep.add("L4", "winglet top WL / outer BL (front view) vs parameters",
            np.array([Vr[:, 2].max() - wg_top, Vr[:, 1].max() - wg_y]), tolp,
            f"mesh top {Vr[:, 2].max():.4f} / BL {Vr[:, 1].max():.4f} vs {wg_top:.4f} / {wg_y:.4f} "
            f"(span {2 * Vr[:, 1].max():.3f})")

    # ---------------------------------------------------------------- tailplane (plan) + horn gap
    Vs, Fs = ctx.mesh(("stabilizer", "elevator_R", "elevator_L"), exclude=("black",))
    Vf, Ff = ctx.mesh(("stabilizer",))
    Ve, Fe = ctx.mesh(("elevator_R", "elevator_L"), exclude=("black",))
    yt = [0.3, 0.6, 1.0, 1.4, 1.8, 2.1, 2.2, 2.30, 2.36, 2.42, 2.46, 2.50, 2.54, 2.57]
    le_d, te_d, p2m, m2p, gap_d, locs, plocs = [], [], [], [], [], [], []
    for sg in (1, -1):
        for y in yt:
            sec = E.stab_section(y)
            loop = sec_loop(sec) * [1, sg, 1]
            S = slice_segments(Vs, Fs, (0, 1, 0), sg * y)
            Q = densify_segments(S, 0.001)
            if not len(Q):
                le_d.append(1.0)
                locs.append((E.stab_le(y), sg * y, E.STAB_Z))
                continue
            le_d.append(Q[:, 0].min() - E.stab_le(y))
            te_d.append(Q[:, 0].max() - E.stab_te(y))
            locs.append((E.stab_le(y), sg * y, E.STAB_Z))
            in_gap = E.ELEV_HORN[0] < y < E.STAB_NOTCH_Y
            if in_gap:
                g0, g1 = float(E.horn_gap_x(y)), float(E.horn_front_x(y))
                keep = ~((loop[:, 0] > g0 - 0.002) & (loop[:, 0] < g1 + 0.002))
                Sf = densify_segments(slice_segments(Vf, Ff, (0, 1, 0), sg * y), 0.001)
                Se = densify_segments(slice_segments(Ve, Fe, (0, 1, 0), sg * y), 0.001)
                if len(Sf):
                    gap_d.append(Sf[:, 0].max() - g0)
                if len(Se):
                    gap_d.append(Se[:, 0].min() - g1)
            else:
                keep = np.ones(len(loop), bool)
            a_, b_ = loop_compare(Q[:, [0, 2]], loop[:, [0, 2]], ~keep)
            p2m.append(a_.max())
            m2p.append(b_.max())
            plocs.append((sg * y, 1000 * a_.max(), 1000 * b_.max()))
    locs = np.array(locs)
    rep.add("L4", "tailplane LE (plan) vs empennage.stab_le", np.array(le_d), tolp, f"BL {yt[0]}-{yt[-1]}, both halves",
            worst_list(le_d, locs))
    rep.add("L4", "tailplane TE (plan, incl. raked tip) vs stab_te", np.array(te_d), tolp, "", worst_list(te_d, locs))
    rep.add("L4", "tailplane sections: parameter loop <-> mesh (side proj.)", np.r_[p2m, m2p], tolp,
            "horn-gap slot excluded from the loop; mesh points inside the loop (coves) ignored",
            [f"BL {b:+.2f}: {c:.1f} / {d:.1f} mm (param->mesh / mesh->param)" for b, c, d in
             sorted(plocs, key=lambda t: -max(t[1], t[2]))[:4]])
    rep.add("L4", "horn gap: fixed-tip aft face / horn front vs parameters", np.array(gap_d), tolp,
            f"BL {E.ELEV_HORN[0]:.3f}-{E.STAB_NOTCH_Y:.3f} (horn_gap_x / horn_front_x)")
    # plan outline (normal distance) against stab_plan_polygon (both halves): the LE / TE rows above measure along
    # x, which exaggerates the raked tip edges (dx/dy 2.1 and 12.5)
    B_ = cKDTree(plan_silhouette(Vs, Fs, (12.95, -2.65, 14.45, 2.65)))
    Pp = E.stab_plan_polygon(200)
    out_d, out_p = [], []
    for sg in (1, -1):
        poly = Pp * [1, sg]
        cur = Curves([poly], closed=True)
        Bp = B_.data[B_.data[:, 1] * sg > 0.25]           # outboard of the bullet / centre section
        dm = cur.dist(Bp)[0]
        pp = densify_poly(poly, 0.002, closed=True)
        pp = pp[np.abs(pp[:, 1]) > 0.25]
        dp = B_.query(pp)[0]
        out_d += [dm, dp]
        out_p += [np.c_[Bp, np.full(len(Bp), E.STAB_Z)], np.c_[pp, np.full(len(pp), E.STAB_Z)]]
    d = np.concatenate(out_d)
    rep.add("L4", "tailplane plan outline vs stab_plan_polygon (normal dist.)", d, tolp,
            "both halves, |BL| > 0.25, raster 1 mm, gaps < 16 mm closed", worst_list(d, np.vstack(out_p)))
    Vst = np.vstack([Vs])
    rep.add("L4", "tailplane span (max |y|) vs STAB_TIP_Y", np.array([np.abs(Vst[:, 1]).max() - E.STAB_TIP_Y]), tolp,
            f"mesh {np.abs(Vst[:, 1]).max():.4f}")

    # ---------------------------------------------------------------- fin + rudder (side view)
    Vn, Fn = ctx.mesh(("fin", "rudder", "rudder_tab"), mats=paint_mats())
    zs = [2.0, 2.2, 2.4, 2.6, 2.8, 3.0, 3.2, 3.4, 3.45, 3.5, 3.55, 3.6, 3.65, 3.7, 3.75]
    le_d, te_d, p2m, m2p, locs, locs2, flocs = [], [], [], [], [], [], []
    for z in zs:
        sec = E.fin_section(z)
        loop = sec_loop(sec)
        S = slice_segments(Vn, Fn, (0, 0, 1), z)
        Q = densify_segments(S, 0.001)
        if not len(Q):
            te_d.append(1.0)
            locs2.append((E.fin_te(z), 0, z))
            continue
        te_d.append(Q[:, 0].max() - E.fin_te(z))
        locs2.append((E.fin_te(z), 0, z))
        # the fin LE is visible (and the fin section complete) above the dorsal blend and the tail-cone crown
        if z > E.DORSAL_ZTOP:
            le_d.append(Q[:, 0].min() - E.fin_le(z))
            locs.append((E.fin_le(z), 0, z))
            a_, b_ = loop_compare(Q[:, :2], loop[:, :2])
            p2m.append(a_.max())
            m2p.append(b_.max())
            flocs.append((z, 1000 * a_.max(), 1000 * b_.max()))
    rep.add("L4", "fin LE (side, above the dorsal) vs empennage.fin_le", np.array(le_d), tolp,
            f"WL {E.DORSAL_ZTOP:.2f}-{zs[-1]:.2f}", worst_list(le_d, np.array(locs)))
    rep.add("L4", "rudder TE (side) vs empennage.fin_te", np.array(te_d), tolp, f"WL {zs[0]}-{zs[-1]}",
            worst_list(te_d, np.array(locs2)))
    rep.add("L4", "fin sections (NACA 0018): parameter <-> mesh (plan proj.)", np.r_[p2m, m2p], tolp,
            f"WL {E.DORSAL_ZTOP:.2f}-{zs[-1]:.2f}",
            [f"WL {b:.2f}: {c:.1f} / {d:.1f} mm (param->mesh / mesh->param)" for b, c, d in
             sorted(flocs, key=lambda t: -max(t[1], t[2]))[:4]])

    # ---------------------------------------------------------------- tail side view (L4 side): silhouette of the tail
    # cone, dorsal, fin, rudder, strakes, bullet and tailplane vs the drawn outline curves
    tail_parts = ("fus_center", "fus_aft", "dorsal_fin", "fin", "rudder", "rudder_tab", "strakes", "tail_bullet", "stabilizer",
                  "elevator_R", "elevator_L")
    Vt, Ft = ctx.mesh(tail_parts, exclude=("black", "lining"))
    box = (9.40, 1.10, 14.86, 4.32)
    sil = plan_silhouette(Vt, Ft, box, res=0.002, axes=(0, 2))
    sil = sil[(sil[:, 0] > box[0] + 0.02) & (sil[:, 0] < box[2] - 0.004)]
    Bt = np.array(E.BULLET)
    zj = float(E._dorsal_curve()[-1, 1])
    zt_b = float(np.interp(E.fin_le(4.0), Bt[:, 0], Bt[:, 2]))
    xk = np.linspace(9.3, X1, 800)
    (vx0, vz0), (vx1, vz1) = E.VENTRAL_EDGE
    vx = np.linspace(vx0, vx1, 200)
    curves = dict(
        crown=np.c_[xk, F.z_top(xk)], keel=np.c_[xk, F.z_bot(xk)],
        dorsal=np.r_[[[E.DORSAL_X0, E.DORSAL_Z0]], E._dorsal_curve(200)],
        fin_le=np.array([[E.fin_le(zj), zj], [E.fin_le(4.3), 4.3]]),
        rudder_te=np.array([E.FIN_TE[0], [E.fin_te(4.3), 4.3]]),
        ventral=np.c_[vx, vz0 + (vz1 - vz0) * (vx - vx0) / (vx1 - vx0)],
        bullet_top=Bt[:, [0, 1]], bullet_bot=Bt[:, [0, 2]], bullet_end=Bt[-1:, [0, 1, 0, 2]].reshape(2, 2),
        strake=np.array([E.STRAKE_ROOT[0], E.STRAKE_TIP[0], E.STRAKE_TIP[1], E.STRAKE_ROOT[1]]),
        # the sloped rudder top edge (E.rudder_outline, drawn on L4): the rudder / fin-tip gap (RUD_EDGE_GAP each side
        # of it) is a see-through slit in the side view
        rudder_top=np.c_[np.linspace(E.rudder_edge_point(E.RUD_NOSE_XC, "top")[0], E.fin_te(3.77), 120),
                         E.rudder_top_z(np.linspace(E.rudder_edge_point(E.RUD_NOSE_XC, "top")[0], E.fin_te(3.77), 120))],
    )
    cur = Curves(list(curves.values()), step=0.001)
    d, lab = cur.dist(sil)
    names_ = list(curves)
    rep.add("L4", "tail side silhouette -> drawn outline curves (side view)", d, tolp,
            "tail cone, dorsal, fin, rudder, strakes, bullet, tailplane; raster 2 mm",
            worst_list(d, np.c_[sil[:, 0], np.zeros(len(sil)), sil[:, 1]], [names_[i] for i in lab]))
    tr = cKDTree(sil)
    dd, P_, lab2 = [], [], []
    for nm, (lo, hi) in (("dorsal", (9.3, 20)), ("fin_le", (0, 20)), ("rudder_te", (0, 20)), ("bullet_top", (0, 20)),
                         ("ventral", (E.VENTRAL_EDGE[0][0] + 0.25, E.VENTRAL_EDGE[1][0] - 0.02))):
        Q = densify_poly(curves[nm], 0.004)
        Q = Q[(Q[:, 0] > max(lo, box[0] + 0.05)) & (Q[:, 0] < hi) & (Q[:, 1] < box[3] - 0.02)]
        if nm == "fin_le":
            Q = Q[Q[:, 1] < zt_b - 0.01]
        if nm == "rudder_te":
            Q = Q[Q[:, 1] < float(E.rudder_top_z(E.fin_te(3.77))) - 0.01]
        if nm == "ventral":
            Q = Q[Q[:, 1] < F.z_bot(F.clip_x(Q[:, 0])) - 0.01]    # visible below the keel only
        dd.append(tr.query(Q)[0])
        P_.append(Q)
        lab2 += [nm] * len(Q)
    d = np.concatenate(dd)
    P_ = np.vstack(P_)
    rep.add("L4", "drawn tail outline (dorsal, fin LE, rudder TE, bullet, ventral) -> silhouette", d, tolp, "",
            worst_list(d, np.c_[P_[:, 0], np.zeros(len(P_)), P_[:, 1]], lab2))

    # ---------------------------------------------------------------- main-gear leg door (L4 side / front / detail)
    # LD-1: the built door is gear.leg_door_face() (the drawn face scalloped round the tyre, plus the tab hidden in
    # the wing slot) with its outer face on gear.leg_door_bl(x, z) (the wing skin carried down by the leg); L4 draws
    # its visible part and the edge-on line gear.leg_door_front_line()
    Pd = G.leg_door_face()
    zmx, zmn = Pd[:, 1].max(), Pd[:, 1].min()
    for side, sg in (("L", -1), ("R", 1)):
        Vd, Fd = ctx.mesh((f"gear_main_{side}",), mats=(L.SURFACES["main_gear_door"],))
        if not len(Fd):
            rep.add("L4", f"main-gear leg door {side}: face vs gear.leg_door_face()", status="FAIL",
                    detail="no leg-door mesh")
            continue
        silh = plan_silhouette(Vd, Fd, (5.7, 0.1, 6.8, 1.3), res=0.002, close_r=0.004, axes=(0, 2))
        d1 = Curves([Pd], closed=True).dist(silh)[0]
        d2 = cKDTree(silh).query(densify_poly(Pd, 0.004, closed=True))[0]
        bl_out = G.leg_door_bl(Vd[:, 0], Vd[:, 2])
        dbl = np.abs(Vd[:, 1]) - bl_out                     # 0 on the outer face, -LEG_DOOR_T on the inner face
        rep.add("L4", f"main-gear leg door {side}: side-view face <-> gear.leg_door_face() (LD-1)", np.r_[d1, d2], tolp,
                f"mesh face STA {Vd[:, 0].min():.3f}-{Vd[:, 0].max():.3f} WL {Vd[:, 2].min():.3f}-{Vd[:, 2].max():.3f} "
                f"vs parameters STA {Pd[:, 0].min():.3f}-{Pd[:, 0].max():.3f} WL {zmn:.3f}-{zmx:.3f}; outer face BL "
                f"{np.abs(Vd[:, 1]).min():.3f}-{np.abs(Vd[:, 1]).max():.3f} vs gear.leg_door_bl (max "
                f"{1000 * dbl.max():+.1f} / min {1000 * dbl.min():+.1f} mm; drawn plane {G.LEG_DOOR['bl'][0]:.3f}-"
                f"{G.LEG_DOOR['bl'][1]:.3f})",
                worst_list(np.r_[d1, d2], np.r_[np.c_[silh[:, 0], np.zeros(len(silh)), silh[:, 1]],
                                               np.c_[densify_poly(Pd, 0.004, closed=True)[:, 0], np.zeros(len(d2)),
                                                     densify_poly(Pd, 0.004, closed=True)[:, 1]]]))
        # front view (L4 edge-on line): the mesh's outboard-most BL per WL band vs gear.leg_door_front_line()
        fl = G.leg_door_front_line(visible=False)
        zb = np.linspace(fl[:, 1].min(), fl[:, 1].max(), 30)
        dfr = []
        for za, zc in zip(zb[:-1], zb[1:]):
            k = (Vd[:, 2] >= za) & (Vd[:, 2] < zc)
            if k.any():
                m_ = (fl[:, 1] >= za) & (fl[:, 1] <= zc)
                ref = fl[m_, 0].max() if m_.any() else float(np.interp(0.5 * (za + zc), fl[:, 1], fl[:, 0]))
                dfr.append(np.abs(Vd[k, 1]).max() - ref)
        rep.add("L4", f"main-gear leg door {side}: edge-on BL <-> gear.leg_door_front_line() (LD-1)", np.array(dfr),
                TOL["opening"], f"outer face on gear.leg_door_bl within {1000 * np.abs(dbl).min():.1f} mm (outboard-most "
                                f"vertex {1000 * dbl.max():+.1f} mm); edge-on BL {fl[:, 0].min():.3f}-{fl[:, 0].max():.3f}")

    # ---------------------------------------------------------------- bullet
    Vb, Fb = ctx.mesh(("tail_bullet",))
    B = np.array(E.BULLET)
    d_all = []
    for x in np.linspace(B[1, 0], B[-2, 0], 12):
        ring = np.asarray(E.bullet_section(x, 720))
        S = slice_segments(Vb, Fb, (1, 0, 0), x)
        Q = densify_segments(S, 0.001)
        if not len(Q):
            d_all.append(1.0)
            continue
        d_all.append(cKDTree(Q[:, 1:]).query(ring[:, 1:])[0].max())
        d_all.append(Curves([ring[:, 1:]], closed=True).dist(Q[:, 1:])[0].max())
    rep.add("L4", "bullet fairing sections vs empennage.bullet_section", np.array(d_all), tolp,
            f"STA {B[1, 0]:.3f}-{B[-2, 0]:.3f}; aft end {Vb[:, 0].max():.3f} vs {E.BULLET_X[1]:.3f}")

    # ---------------------------------------------------------------- radar pod
    Vp = ctx.verts("radar_pod")
    prof = np.array(D.radar_pod_profile(400))
    r_mesh = np.hypot(Vp[:, 1] - D.POD_Y, Vp[:, 2] - D.POD_Z)
    r_par = np.interp(Vp[:, 0], prof[:, 0], prof[:, 1])
    dev = np.r_[r_mesh - r_par, [Vp[:, 0].min() - D.POD_X_TIP, Vp[:, 0].max() - D.POD_X_END]]
    rep.add("L4", "radar pod: radius about (POD_Y, POD_Z) vs profile, tip / end", dev, tolp,
            f"x {Vp[:, 0].min():.3f}-{Vp[:, 0].max():.3f}, max r {r_mesh.max():.4f} (POD_R {D.POD_R})",
            worst_list(dev[:-2], Vp))

    # ---------------------------------------------------------------- axles / tyres
    dev, lab = [], []
    for pid, A, T in (("gear_main_R", G.MAIN_AXLE, G.MAIN_TYRE), ("gear_main_L", G.MAIN_AXLE * [1, -1, 1], G.MAIN_TYRE),
                      ("gear_nose", G.NOSE_AXLE, G.NOSE_TYRE)):
        Vt = ctx.verts(pid, mats=("tire",))
        if not len(Vt):
            dev.append(1.0)
            lab.append(f"{pid}: no tyre")
            continue
        c = np.array([0.5 * (Vt[:, 0].min() + Vt[:, 0].max()), 0.5 * (Vt[:, 1].min() + Vt[:, 1].max()),
                      0.5 * (Vt[:, 2].min() + Vt[:, 2].max())])
        R = 0.25 * (np.ptp(Vt[:, 0]) + np.ptp(Vt[:, 2]))
        Wd = np.ptp(Vt[:, 1])
        dev += list(c - A) + [R - T["R"], Wd - T["W"]]
        lab.append(f"{pid}: centre {np.round(c, 4).tolist()} vs {np.round(A, 4).tolist()}, R {R:.4f}/{T['R']}, "
                   f"W {Wd:.4f}/{T['W']}")
    rep.add("L4", "axles (tyre centres) and tyre R / width vs gear parameters", np.array(dev), tolp,
            f"track {2 * G.MAIN_AXLE[1]:.3f}, wheelbase {G.MAIN_AXLE[0] - G.NOSE_AXLE[0]:.3f}", lab,
            )

    # ---------------------------------------------------------------- propeller disc + spinner
    a = -PP.thrust_dir()                                   # aft along the thrust axis
    hub = PP.prop_hub()
    tips, rad, d_sec, off, locs = [], [], [], [], []
    _, rs_, Pm = PP.blade_geometry()                       # the parameter blade (pitch axis = local z, at flight fine)
    Rt = PP.thrust_rotation()
    rows = [i for i, r_ in enumerate(rs_) if 0.2 <= r_ <= 1.2][::3]
    for k in range(PP.N_BLADES):
        Vb_, Fb_ = ctx.mesh((f"blade_{k + 1}",))
        w = Vb_ - hub
        s = w @ a
        r = np.linalg.norm(w - np.outer(s, a), axis=1)
        i = np.argmax(r)
        tips.append(Vb_[i])
        rad.append(r[i] - PP.PROP_R)
        R = Rt @ _rot_x(2 * np.pi * k / PP.N_BLADES)
        ax_k = PP.blade_axis(k)
        for i_r in rows:
            loop = Pm[i_r] @ R.T + hub                     # parameter section about blade k's pitch axis
            S = slice_segments(Vb_, Fb_, ax_k, float(ax_k @ hub) + rs_[i_r])
            Q = densify_segments(S, 0.0005)
            if not len(Q):
                d_sec.append(1.0)
                continue
            dq, iq = cKDTree(Q).query(loop)
            d_sec.append(max(dq.max(), Curves([loop], closed=True).dist(Q)[0].max()))
            off.append(float(((Q[iq] - loop) @ a).mean()))           # mean axial displacement of the section
            locs.append(loop.mean(0))
    rep.add("L4", "propeller tip radius vs PROP_R (5 blades)", np.array(rad), tolp,
            f"PROP_R {PP.PROP_R}; tips {', '.join(f'{PP.PROP_R + v:.4f}' for v in rad)}")
    rep.add("L4", "blade sections vs powerplant.blade_geometry on the pitch axes", np.array(d_sec), tolp,
            f"{len(rows)} radii x {PP.N_BLADES} blades, R {rs_[rows[0]]:.2f}-{rs_[rows[-1]]:.2f}",
            worst_list(d_sec, np.array(locs)))
    rep.add("L4", "propeller disc (pitch-axis plane): axial offset from PROP_X", np.array(off), tolp,
            f"disc centre {np.round(hub, 4).tolist()} on the 2 deg tilted / yawed thrust line")
    tips = np.array(tips)
    c0 = tips.mean(0)
    _, _, vt = np.linalg.svd(tips - c0)
    nrm = vt[-1] * np.sign(vt[-1] @ a)
    ang = math.degrees(math.acos(min(1.0, abs(float(nrm @ a)))))
    s_tip = (tips - hub) @ a
    rep.add("L4", "blade tips vs the drawn disc line (prop_disc_edge)", np.r_[s_tip, [PP.PROP_R * math.radians(ang)]],
            None, f"tip plane normal {ang:.2f} deg off the thrust axis; outermost tip vertices "
            f"{1000 * s_tip.min():.0f}..{1000 * s_tip.max():.0f} mm aft of the disc: the scimitar tip sweep "
            "(blade_geometry) -- the sheets draw the disc at the pitch-change axes", status="INFO")
    Vsp = ctx.get("propeller", mats=("chrome",))
    Vsp = Vsp[0].V if Vsp else np.zeros((0, 3))
    t0 = PP.axis_point(F.STA["spinner_tip"])
    Lsp = (F.STA["cowl_front"] - F.STA["spinner_tip"]) * np.linalg.norm([1.0, math.tan(math.radians(PP.THRUST_YAW_DEG)),
                                                                           math.tan(math.radians(PP.THRUST_TILT_DEG))])
    w = Vsp - t0
    s = w @ a
    r = np.linalg.norm(w - np.outer(s, a), axis=1)
    tt, rp = PP.spinner_profile(4001)
    r_par = np.interp(s / Lsp, tt, rp, right=rp[-1])
    on = s <= Lsp + PP.SPINNER_SKIRT + 1e-4
    dev = r[on] - r_par[on]
    # radial error overstates the normal error near the tip where the meridian is steep: use normal distance
    mer = np.c_[np.r_[tt * Lsp, Lsp + PP.SPINNER_SKIRT], np.r_[rp, rp[-1]]]
    dn = Curves([mer]).dist(np.c_[s[on], r[on]])[0]
    rep.add("L4", "spinner meridian about the thrust axis vs spinner_profile", dn, TOL["oml"],
            f"SPINNER_R {F.SPINNER_R}, SHAPE {F.SPINNER_SHAPE}; base plane at the cowl front", worst_list(dn, Vsp[on]))


# =====================================================================================================================
# L5  livery
# =====================================================================================================================
def livery_curves(side, cockpit, fin, n=6000):
    """Side-projection (x, z) boundary curves of the scheme that can bound paint on a part."""
    polys = []
    for st in L.strokes().values():
        xs = np.linspace(st.x0, st.x1, n)
        c, h = st.c(xs), np.maximum(st.h(xs), 0.0)
        polys += [np.c_[xs, c + h], np.c_[xs, c - h]]
        for xe, ce, he in ((xs[0], c[0], h[0]), (xs[-1], c[-1], h[-1])):
            if he > 1e-4:
                polys.append(np.array([[xe, ce - he], [xe, ce + he]]))
    for rg in L.regions().values():
        xs = np.linspace(rg.x0, rg.x1, n)
        polys += [np.c_[xs, rg.top(xs)], np.c_[xs, rg.bot(xs)]]
        for xe in (rg.x0, rg.x1):
            polys.append(np.array([[xe, float(rg.bot(xe))], [xe, float(rg.top(xe))]]))
    if fin:
        xs = np.linspace(L.FIN_CAP_X0, 15.0, 2000)
        polys.append(np.c_[xs, L.fin_cap_line(xs)])
        polys.append(np.array([[L.FIN_CAP_X0, float(L.fin_cap_line(L.FIN_CAP_X0))], [L.FIN_CAP_X0, 5.0]]))
    if cockpit:
        O = CG.side_outline("mask")
        polys.append(np.vstack([O, O[:1]]))
    if side * FP.EXIT["side"] > 0:
        o, w = L.EXIT_MARK["offset"], L.EXIT_MARK["half_width"]
        ex = FP.EXIT
        for dlt in (o - w, o + w):
            P = sdf2d.rrect_outline(ex["cx"], ex["cz"], ex["hx"] + dlt, ex["hz"] + dlt, max(ex["r"] + dlt, 1e-4), 64)
            polys.append(np.vstack([P, P[:1]]))
    return Curves(polys, step=5e-4)


def expected_paint(P, cockpit, fin):
    """Material the livery parameters give at points P (replicates livery.paint_mesh's priority)."""
    order = list(L.PAINT_ORDER)
    lab = np.full(len(P), -1)
    for i, mat in enumerate(order):
        ins = np.zeros(len(P), bool)
        for reg in L.region_fields(mat, cockpit=cockpit, fin=fin):
            m = np.ones(len(P), bool)
            for f in reg:
                m &= f(P) < 0
            ins |= m
        lab = np.where((lab < 0) & ins, i, lab)
    names = np.array(order + [L.BASE])
    lab[lab < 0] = len(order)
    return names[lab]


LIVERY_GROUPS = {
    "fuselage skins": ("cowl_upper", "cowl_lower", "fus_fwd", "fus_center", "fus_aft"),
    "doors / exit": DOOR_PARTS,
    "fin / rudder / tab": L.FIN_PARTS,
    "dorsal, strakes, root fillet, gear doors": ("dorsal_fin", "strakes", "belly_fairing", "gear_door_NR",
                                                 "gear_door_NL"),
}


def livery_coverage(ctx, rep, tol, step=0.004, delta=0.003):
    polys = []
    for st in L.strokes().values():
        xs = np.arange(st.x0, st.x1 + 1e-9, step / 4)
        c, h = st.c(xs), np.maximum(st.h(xs), 0.0)
        polys += [(f"{st.id} upper", np.c_[xs, c + h]), (f"{st.id} lower", np.c_[xs, c - h])]
    for rg in L.regions().values():
        xs = np.arange(rg.x0, rg.x1 + 1e-9, step / 4)
        polys += [(f"{rg.id} top", np.c_[xs, rg.top(xs)]), (f"{rg.id} bottom", np.c_[xs, rg.bot(xs)])]
    O = CG.side_outline("mask")
    polys.append(("PRO mask", np.vstack([O, O[:1]])))
    ex, w = FP.EXIT, L.EXIT_MARK["half_width"]
    for dl in (-w, w):
        R_ = sdf2d.rrect_outline(ex["cx"], ex["cz"], ex["hx"] + dl, ex["hz"] + dl, ex["r"] + dl, 64)
        polys.append((f"exit ring {'in' if dl < 0 else 'out'}", np.vstack([R_, R_[:1]])))
    pts, nrm, lab = [], [], []
    for name, P in polys:
        Q = densify_poly(P, step)[::max(1, int(round(step / 0.001)))] if len(P) > 2 and \
            np.median(np.linalg.norm(np.diff(P, axis=0), axis=1)) < step else densify_poly(P, step)
        t_ = np.gradient(Q, axis=0)
        t_ /= np.maximum(np.linalg.norm(t_, axis=1, keepdims=True), 1e-12)
        pts.append(Q)
        nrm.append(np.c_[-t_[:, 1], t_[:, 0]])
        lab += [name] * len(Q)
    Q, N_, lab = np.vstack(pts), np.vstack(nrm), np.array(lab)
    x, z = Q[:, 0], Q[:, 1]
    xc = F.clip_x(x)
    ok = (x > X0 + 0.01) & (x < X1 - 0.01) & (E.tail_cut_field(x, z) < -0.01) & \
        (z > F.z_bot(xc) + 0.006) & (z < F.z_top(xc) - 0.006)
    dev, locs, labs = [], [], []
    for side in (1, -1):
        Pm = []
        for pid in SKIN_PARTS + DOOR_PARTS:
            for S, ma, mb in colour_boundaries(ctx, pid, segments=True):
                S = S[S[:, :, 1].mean(1) * side > 0]
                Pm.append(densify_segments(S, 0.002))
        Pm = np.vstack(Pm)
        tree = cKDTree(Pm[:, [0, 2]])
        q, n_, lb = Q[ok], N_[ok], lab[ok]

        def surf(xz):
            xx = F.clip_x(xz[:, 0])
            return np.c_[xz[:, 0], side * F.side_y(xx, xz[:, 1]), xz[:, 1]]
        P0 = surf(q)
        vis = ~expected_skin_hole(P0, painted=True)
        a_ = expected_paint(surf(q + delta * n_), True, False)
        b_ = expected_paint(surf(q - delta * n_), True, False)
        vis &= a_ != b_                                     # the parameter paint really changes across the curve here
        d, _ = tree.query(q[vis])
        dev.append(d)
        locs.append(P0[vis])
        labs += list(lb[vis])
    d = np.concatenate(dev)
    rep.add("L5", "livery curves -> mesh colour boundaries: fuselage + doors", d, tol,
            "every visible stroke / band / mask / exit-ring edge, both sides", worst_list(d, np.vstack(locs), labs))


def check_L5(ctx, rep, plots):
    tol = TOL["livery"]
    curves = {}
    plot_pts = []
    for gname, pids in LIVERY_GROUPS.items():
        dev, Ps, labs = [], [], []
        mis_d, mis_P, mis_area, mis_lab = [], [], 0.0, []
        n_samp = 0
        for pid in pids:
            if pid not in ctx.by_part:
                continue
            cockpit, fin = pid in L.MASK_PARTS, pid in L.FIN_PARTS
            for side in (1, -1):
                key = (side, cockpit, fin)
                if key not in curves:
                    curves[key] = livery_curves(side, cockpit, fin)
            # colour boundaries
            for P, ma, mb in colour_boundaries(ctx, pid, mats=SIDE_PAINT | {"paint_white"}):
                if not (ma in SIDE_PAINT | {"paint_white"} and mb in SIDE_PAINT | {"paint_white"}):
                    continue
                for side in (1, -1):
                    m = P[:, 1] * side >= 0
                    if not m.any():
                        continue
                    d, _ = curves[(side, cockpit, fin)].dist(P[m][:, [0, 2]])
                    dev.append(d)
                    Ps.append(P[m])
                    labs += [f"{pid} {ma}/{mb}"] * int(m.sum())
            # regions: sampled labels vs the parameter painter
            for r in ctx.get(pid):
                if r.mat not in SIDE_PAINT | {"paint_white"}:
                    continue
                v, f = weld(r.V, r.F, r.key)
                if not len(f):
                    continue
                S, A, _ = tri_samples(v, f)
                exp = expected_paint(S, cockpit, fin)
                bad = exp != r.mat
                n_samp += len(S)
                if bad.any():
                    Sb = S[bad]
                    db = np.full(len(Sb), np.inf)
                    for side in (1, -1):
                        m = Sb[:, 1] * side >= 0
                        if m.any():
                            db[m] = curves[(side, cockpit, fin)].dist(Sb[m][:, [0, 2]])[0]
                    far = db > tol / 1000
                    if far.any():
                        mis_d.append(db[far])
                        mis_P.append(Sb[far])
                        mis_area += float(A[bad][far].sum())
                        mis_lab += [f"{pid}: {r.mat} painted, {e} expected" for e in exp[bad][far]]
        if dev:
            d = np.concatenate(dev)
            P = np.vstack(Ps)
            rep.add("L5", f"colour boundaries vs livery curves: {gname}", d, tol, f"{', '.join(pids)}",
                    worst_list(d, P, labs))
            plot_pts.append((P, d))
        else:
            rep.add("L5", f"colour boundaries vs livery curves: {gname}", status="INFO", detail="no colour boundaries")
        if mis_d:
            d = np.concatenate(mis_d)
            rep.add("L5", f"paint regions (sampled) vs livery fields: {gname}", status="FAIL", n=n_samp,
                    max_mm=float(1000 * d.max()), detail=f"{mis_area * 1e4:.0f} cm^2 painted wrong > {tol:.0f} mm from "
                    "any boundary", worst=worst_list(d, np.vstack(mis_P), mis_lab))
        else:
            rep.add("L5", f"paint regions (sampled) vs livery fields: {gname}", status="PASS", n=n_samp, max_mm=0.0,
                    detail=f"no sample painted wrong beyond {tol:.0f} mm of a boundary")

    # ---- both ways on the fuselage: every livery-curve point where the parameter paint changes on the skin has a mesh
    # colour boundary within the tolerance (catches strokes the painter lost -- narrower than 2 x tol they would pass
    # the sampled-region check above)
    livery_coverage(ctx, rep, tol)

    # ---- wing leading-edge boot band (L5 plan: upper 10 %, lower 6.5 % chord, BL 0.95-7.43)
    yg = np.linspace(W.BOOT_Y[0] - 0.05, W.BOOT_Y[1] + 0.01, 400)
    up_x, lo_x, le_x, le_z, te_x, te_z = [], [], [], [], [], []
    for y in yg:
        s = W.section_at(y)
        up_x.append(float(s.upper(np.array(0.10))[0]))
        lo_x.append(float(s.lower(np.array(0.065))[0]))
        p0, p1 = s.point(np.array(0.0), np.array(0.0)), s.point(np.array(1.0), np.array(0.0))
        le_x.append(p0[0]); le_z.append(p0[2]); te_x.append(p1[0]); te_z.append(p1[2])
    dev, Ps = [], []
    for side in ("R", "L"):
        Vb, Fb = ctx.mesh((f"wing_{side}",), mats=("deice_boot",))
        comps = boundary_components(Vb, Fb, min_area=1e-5, seams=True)
        P = np.vstack([c["P"] for c in comps]) if comps else np.zeros((0, 3))
        y = np.abs(P[:, 1])
        zc = np.interp(y, yg, le_z) + (P[:, 0] - np.interp(y, yg, le_x)) * \
            (np.interp(y, yg, te_z) - np.interp(y, yg, le_z)) / (np.interp(y, yg, te_x) - np.interp(y, yg, le_x))
        upper = P[:, 2] > zc
        dx = np.where(upper, P[:, 0] - np.interp(y, yg, up_x), P[:, 0] - np.interp(y, yg, lo_x))
        dy = np.minimum(np.abs(y - W.BOOT_Y[0]), np.abs(y - W.BOOT_Y[1]))
        dev.append(np.minimum(np.abs(dx), dy))
        Ps.append(P)
    d = np.concatenate(dev)
    rep.add("L5", "wing boot band edges (10 % up / 6.5 % low, BL 0.95-7.43)", d, tol, "deice_boot boundary, both wings",
            worst_list(d, np.vstack(Ps)))

    # ---- radar-pod radome joint, blade bands
    cb = colour_boundaries(ctx, "radar_pod", mats={"paint_black", "paint_blue"})
    P = np.vstack([p for p, _, _ in cb]) if cb else np.zeros((0, 3))
    rep.add("L5", "radar-pod radome joint (black / blue) vs POD_X_JOINT", P[:, 0] - D.POD_X_JOINT if len(P) else None,
            tol, f"POD_X_JOINT {D.POD_X_JOINT}")
    # band edges per material pair (PROP_BANDS: consecutive bands share an edge), radius about the thrust axis
    edges = {}
    for (m1, a1, b1), (m2, a2, b2) in zip(L.PROP_BANDS[:-1], L.PROP_BANDS[1:]):
        edges.setdefault(frozenset((m1, m2)), set()).add(PP.PROP_R - b1)
    edges.setdefault(frozenset(("prop_blade", L.PROP_BANDS[-1][0])), set()).add(PP.PROP_R - L.PROP_BANDS[-1][2])
    a = -PP.thrust_dir()
    hub = PP.prop_hub()
    dev, Ps, labs = [], [], []
    for k in range(PP.N_BLADES):
        for P, ma, mb in colour_boundaries(ctx, f"blade_{k + 1}", mats={m for m, _, _ in L.PROP_BANDS}):
            w = P - hub
            r = np.linalg.norm(w - np.outer(w @ a, a), axis=1)
            exp_r = np.array(sorted(edges.get(frozenset((ma, mb)), {np.inf})))
            dev.append(np.abs(r[:, None] - exp_r[None]).min(1))
            Ps.append(P)
            labs += [f"blade_{k + 1} {ma}/{mb} at R {v:.4f}" for v in r]
    all_r = sorted({v for e in edges.values() for v in e})
    rep.add("L5", "propeller blade band edges vs PROP_BANDS (R about the thrust axis)",
            np.concatenate(dev) if dev else None, tol, f"band edges at R {', '.join(f'{v:.3f}' for v in all_r)}",
            worst_list(np.concatenate(dev), np.vstack(Ps), labs) if dev else [])

    # ---- per-surface colours of the L5 surface table (SURFACES, STAB_BOOT, WINGLET_PIN)
    S_ = L.SURFACES
    blades = [f"blade_{k + 1}" for k in range(PP.N_BLADES)]
    expect = [
        ("wing upper / lower (+ flaps, ailerons)", [(p, m) for p in ("wing_R", "wing_L", "flap_R", "flap_L", "aileron_R",
                                                                    "aileron_L") for m in (S_["wing_upper"], S_["wing_lower"])]),
        ("wing LE boot", [(p, S_["boot"]) for p in ("wing_R", "wing_L")]),
        ("winglet inboard / outboard faces", [(p, m) for p in ("winglet_R", "winglet_L")
                                              for m in (S_["winglet_inboard"], S_["winglet_outboard"])]),
        ("WINGLET_PIN chordwise white line (L5 plan)", [(p, "paint_pinstripe") for p in ("winglet_R", "winglet_L")]),
        ("tailplane + elevators silver", [(p, S_["stab_upper"]) for p in ("stabilizer", "elevator_R", "elevator_L")]),
        ("STAB_BOOT tailplane LE boot 8 % / 6 % (L5 plan)", [("stabilizer", S_["boot"])]),
        ("bullet fairing white", [("tail_bullet", S_["bullet"])]),
        ("belly / flap-track fairings", [("belly_fairing", S_["belly_fairing"]), ("flap_fairings", S_["flap_fairings"])]),
        ("radar pod body / radome", [("radar_pod", S_["pod_body"]), ("radar_pod", S_["pod_radome"])]),
        ("main-gear leg doors", [(p, S_["main_gear_door"]) for p in ("gear_main_R", "gear_main_L")]),
        ("spinner / exhaust stacks", [("propeller", S_["spinner"]), ("exhaust_stacks", S_["exhaust"])]),
        ("chin inlet lip / mouth", [("chin_inlet", S_["inlet_lip"]), ("chin_inlet", S_["inlet_mouth"])]),
        ("blade bands (PROP_BANDS)", [(p, m) for p in blades for m, _, _ in L.PROP_BANDS]),
        ("blade LE erosion strip (SURFACES blade_le)", [(p, S_["blade_le"]) for p in blades]),
    ]
    for name, pairs in expect:
        miss = sorted({f"{p}:{m}" for p, m in pairs if m not in {r.mat for r in ctx.get(p)}})
        rep.add("L5", f"surface colour: {name}", status="FAIL" if miss else "PASS", n=len(pairs),
                detail=("missing " + ", ".join(miss[:6]) + (" ..." if len(miss) > 6 else "")) if miss else
                " + ".join(sorted({m for _, m in pairs})))
    if plots and plot_pts:
        P = np.vstack([p for p, _ in plot_pts])
        dd = np.concatenate([d for _, d in plot_pts])
        _plot_livery(plots / "L5_boundaries.png", P, dd)


# =====================================================================================================================
# plots (diagnostics, --plots)
# =====================================================================================================================
def _plot_side(path, outlines, points, box):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(14, 6))
    for O, c in outlines:
        O = np.asarray(O)
        ax.plot(np.r_[O[:, 0], O[:1, 0]], np.r_[O[:, 1], O[:1, 1]], c, lw=0.6)
    for P, c in points:
        if len(P):
            ax.plot(P[:, 0], P[:, 2], ".", color=c, ms=1)
    ax.set_xlim(box[0], box[1])
    ax.set_ylim(box[2], box[3])
    ax.set_aspect("equal")
    ax.grid(lw=0.2)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def _plot_frames(V, Fm, plots):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(3, 6, figsize=(18, 9))
    t = np.linspace(0, 1, 1440)
    for ax, (name, x) in zip(axs.ravel(), F.FRAMES.items()):
        sec = F.section(np.full_like(t, x), t)
        ax.plot(sec[:, 1], sec[:, 2], "k", lw=0.5)
        Q = densify_segments(slice_segments(V, Fm, (1, 0, 0), x), 0.003)
        ax.plot(Q[:, 1], Q[:, 2], "r.", ms=0.6)
        ax.set_title(f"{name} {x:.3f}", fontsize=8)
        ax.set_aspect("equal")
    fig.tight_layout()
    fig.savefig(plots / "L1_frames.png", dpi=110)
    plt.close(fig)


def _plot_livery(path, P, d):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(2, 1, figsize=(18, 8))
    for ax, side in zip(axs, (-1, 1)):
        for st in L.strokes().values():
            O = st.outline(400)
            ax.plot(O[:, 0], O[:, 1], "k", lw=0.3)
        for rg in L.regions().values():
            xs = np.linspace(rg.x0, rg.x1, 400)
            ax.plot(xs, rg.top(xs), "k", lw=0.3)
            ax.plot(xs, rg.bot(xs), "k", lw=0.3)
        O = CG.side_outline("mask")
        ax.plot(O[:, 0], O[:, 1], "k", lw=0.3)
        m = P[:, 1] * side >= 0
        sc = ax.scatter(P[m, 0], P[m, 2], c=1000 * d[m], s=0.6, cmap="plasma", vmin=0, vmax=TOL["livery"])
        ax.set_xlim(0.9, 14.9)
        ax.set_ylim(0.8, 4.3)
        ax.set_aspect("equal")
        ax.set_title("starboard" if side > 0 else "port", fontsize=9)
    fig.colorbar(sc, ax=axs, shrink=0.6, label="mm")
    fig.savefig(path, dpi=120)
    plt.close(fig)


# =====================================================================================================================
def stale_sources(glb):
    t = glb.stat().st_mtime
    src = [p for d in ("model", "cad") for p in (ROOT / d).glob("*.py")]
    return sorted(p.relative_to(ROOT).as_posix() for p in src if p.stat().st_mtime > t)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--glb", default=str(ROOT / "out" / "pc12.glb"))
    ap.add_argument("--only", default="L1,L2,L3,L4,L5")
    ap.add_argument("--json", default=str(DEFAULT_JSON))
    ap.add_argument("--plots", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    glb = Path(a.glb)
    if not glb.exists():
        print(f"no {glb}: run python3 model/build.py first")
        return 2
    t0 = time.time()
    rep = Report(a.verbose)
    print(f"2-D / 3-D consistency: {glb.relative_to(ROOT) if glb.is_relative_to(ROOT) else glb} vs the parameter "
          f"outlines (sheets {a.only})")
    print(f"  {'':4s} {'':2s} {'check':58s} {'max mm':>7s} {'rms mm':>7s} {'tol':>4s} {'samples':>8s}")
    stale = stale_sources(glb)
    rep.add("--", "GLB newer than model/*.py and cad/*.py", status="FAIL" if stale else "PASS",
            detail=("stale vs " + ", ".join(stale) + " (python3 model/build.py)") if stale else
            time.strftime("built %Y-%m-%d %H:%M", time.localtime(glb.stat().st_mtime)))
    recs, extras = read_glb(glb)
    ctx = Ctx(recs, extras)
    plots = None
    if a.plots:
        plots = Path(a.json).parent
        plots.mkdir(parents=True, exist_ok=True)
    for sheet, fn in (("L1", check_L1), ("L2", check_L2), ("L3", check_L3), ("L4", check_L4), ("L5", check_L5)):
        if sheet in a.only.split(","):
            try:
                fn(ctx, rep, plots)
            except Exception as ex:                        # a crashing check is a failing check
                import traceback
                traceback.print_exc()
                rep.add(sheet, f"{fn.__name__} crashed", status="FAIL", detail=f"{type(ex).__name__}: {ex}")
    n_fail = sum(r.status == "FAIL" for r in rep.rows)
    js = Path(a.json)
    js.parent.mkdir(parents=True, exist_ok=True)
    js.write_text(json.dumps(dict(glb=str(glb), tol_mm=TOL, seconds=round(time.time() - t0, 1),
                                  rows=[r.__dict__ for r in rep.rows]), indent=1))
    print(f"{'CONSISTENCY OK' if n_fail == 0 else 'CONSISTENCY FAIL'}: {len(rep.rows) - n_fail}/{len(rep.rows)} rows "
          f"pass or info, {n_fail} fail ({time.time() - t0:.0f} s; report {js.relative_to(ROOT) if js.is_relative_to(ROOT) else js})")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
