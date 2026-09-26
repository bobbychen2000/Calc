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
  verify round 2 adds    L3 door / exit handles (DOOR_DETAILS), hinge lines vs the door pivots;
                         L4 wing-to-body fairing (lower silhouette, front sections, root-fillet plan edge, fillet on its
                         law, upper edge), chin inlet (mouth + lip ring front view, lip crescent side view), exhaust
                         stacks (3 views), flap / aileron / tab ends and tab line, hinge lines vs pivots (aileron,
                         elevator, rudder, rudder tab), rudder gap line, rudder tab, dorsal-fillet foot (plan), fin
                         (front), strakes (front), gear pivots / brace ends, retracted main wheel;
                         L5 STAB_BOOT / WINGLET_PIN / BLADE_LE_STRIP / exhaust-collar edges, flap-track canoes, nose bay

    python3 test/consistency_2d3d.py                  # all sheets
    python3 test/consistency_2d3d.py --only L2,L3     # some sheets
    options: --glb PATH (default out/pc12.glb), --json PATH (default out/tmp/stage3_consistency/report.json),
             --plots (diagnostic PNGs next to the JSON), -v (worst locations of every row)

Tolerances (mm): 5 OML / openings / glazing, 10 livery, 15 planform features (L4 outlines).  Prints one PASS / FAIL /
INFO / OPEN row per check (max and rms deviation, samples, tolerance) and 'CONSISTENCY OK' / 'CONSISTENCY FAIL'; OPEN =
a known deviation waiting for an owner decision (CLAUDE.md open items; listed, not failing); exit code 1 on a FAIL, 2
when the GLB is missing.  The GLB must be newer than model/*.py and cad/*.py (first row) -- rebuild with
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


def comp_edge_points(V, comps, step=0.002):
    """Boundary-edge points of boundary components, densified to `step` (edges can be long on coarse grids)."""
    if not comps:
        return np.zeros((0, 3))
    E_ = np.vstack([c["E"] for c in comps])
    return densify_segments(np.stack([V[E_[:, 0]], V[E_[:, 1]]], 1), step)


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
        if self.verbose or status in ("FAIL", "OPEN"):
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
    hole |= PP.chin_mouth_field(P) < 0
    hole |= (x < X0 + 0.03) & (PP.cowl_front_field(P) < 0.0015)   # cowl lip cut behind the spinner base plane
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
    ch = P[:, 0] < PP.CHIN_CHEEK_AFT[1] + 0.05          # the cowl front: OML + the chin lip / cheek raise
    if ch.any():
        d[ch] = PP.chin_raised_dist(P[ch])
    rep.add("L1", "skin vertices on the OML (section law)", d, TOL["oml"],
            f"{len(SKIN_PARTS)} skins + door slabs + inlet lip (cowl front: OML + chin lip raise, "
            f"powerplant.cowl_section); {int(out_rng.sum())} outside STA {X0:.3f}-{X1:.3f}",
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
        sec = PP.cowl_section(np.full_like(t, x), t) if x < 1.8 else F.section(np.full_like(t, x), t)
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
    _l3_handles_hinges(ctx, rep)
    if plots:
        outl = [(o, "k") for _, o in expected]
        _plot_side(plots / "L3_openings.png", outl, [(np.vstack([P for p in matched.values() for P in p]), "b")],
                   (4.3, 9.1, 1.1, 2.8))


def _l3_handles_hinges(ctx, rep):
    """Door / exit handles (DOOR_DETAILS, side projection) and the door hinge lines (hinge_line) vs the pivots."""
    dev, P_, lab = [], [], []
    for pid, o in FP.DOORS:
        h = FP.DOOR_DETAILS[FP.DOOR_HANDLE[pid]]
        rs = [r for r in ctx.get(pid, mats=("metal_dark",))
              if np.all(np.abs(FP.rr((r.V[:, 0], r.V[:, 2]), h)) < 0.04)]
        if not rs:
            dev.append(np.array([1.0]))
            P_.append(np.array([[h["cx"], 0.0, h["cz"]]]))
            lab.append(f"{pid}: no handle")
            continue
        V, Fm = merged(rs)
        comps = boundary_components(V, Fm, min_area=1e-6)
        B = comp_edge_points(V, comps)
        O = densify_poly(FP.opening_outline(h, 32), 0.002)
        d1 = np.abs(FP.rr((B[:, 0], B[:, 2]), h))
        d2 = cKDTree(B[:, [0, 2]]).query(O)[0]
        dev += [d1, d2]
        P_ += [B, _xz(O)]
        lab.append(f"{pid} {1000 * max(d1.max(), d2.max()):.1f}")
    d = np.concatenate(dev)
    rep.add("L3", "door / exit handles vs DOOR_DETAILS (side proj.)", d, TOL["opening"], "max mm: " + ", ".join(lab),
            worst_list(d, np.vstack(P_)))
    dev, lab = [], []
    for pid, o in FP.DOORS:
        hl = FP.hinge_line(o)
        if hl is None:
            continue
        pv = (ctx.extras.get(pid) or {}).get("pivot")
        if not pv:
            dev.append(1.0)
            lab.append(f"{pid}: no pivot")
            continue
        org, ax = _pivot(ctx, pid)
        x0, x1, zh = hl
        ang = math.degrees(math.acos(min(1.0, abs(float(ax[0])))))
        yexp = float(F.side_y(0.5 * (x0 + x1), zh))
        dev += [org[2] - zh, abs(org[1]) - yexp, math.radians(ang) * (x1 - x0)]
        lab.append(f"{pid}: pivot WL {org[2]:.4f} vs hinge_line {zh:.4f}, BL {abs(org[1]):.4f} vs skin {yexp:.4f}, axis "
                   f"{ang:.2f} deg off the drawn (horizontal) line, open {pv.get('open_deg')} vs {o.get('open_deg')}")
        if pv.get("open_deg") != o.get("open_deg"):
            dev.append(1.0)
    rep.add("L3", "door hinge lines (hinge_line, open_deg) vs door pivots", np.array(dev), TOL["opening"],
            "airstair (bottom), cargo (top)", lab)


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


def plan_silhouette(V, Fm, box, res=0.001, close_r=0.008, axes=(0, 1), extra=(), area=None):
    """Boundary points (k, 2) of the view projection (axes) of a mesh inside box (a0, b0, a1, b1): triangles
    rasterised at `res`, gaps narrower than 2 close_r closed (spanwise control-surface gaps).  extra: closed 2-D
    polygons filled into the same raster; area: a dict that receives the projected area (m^2) under 'm2'."""
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
    for P in extra:
        dr.polygon([tuple(p) for p in (np.asarray(P, float) - [a0, b0]) / res], fill=1, outline=1)
    m = np.array(img, bool)
    if area is not None:
        area["m2"] = float(m.sum()) * res * res
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
    Pd = G.leg_door_outline()
    zmx, zmn = Pd[:, 1].max(), Pd[:, 1].min()
    bl0, bl1 = G.LEG_DOOR["bl"]
    for side, sg in (("L", -1), ("R", 1)):
        Vd, Fd = ctx.mesh((f"gear_main_{side}",), mats=(L.SURFACES["main_gear_door"],))
        if not len(Fd):
            rep.add("L4", f"main-gear leg door {side}: face vs gear.leg_door_outline()", status="FAIL",
                    detail="no leg-door mesh")
            continue
        silh = plan_silhouette(Vd, Fd, (5.7, 0.1, 6.8, 1.3), res=0.002, close_r=0.004, axes=(0, 2))
        d1 = Curves([Pd], closed=True).dist(silh)[0]
        d2 = cKDTree(silh).query(densify_poly(Pd, 0.004, closed=True))[0]
        bl_exp = bl0 + (bl1 - bl0) * (zmx - Vd[:, 2]) / (zmx - zmn)
        dbl = np.abs(np.abs(Vd[:, 1]) - bl_exp)
        rep.add("L4", f"main-gear leg door {side}: side-view face <-> gear.leg_door_outline()", np.r_[d1, d2], tolp,
                f"mesh face STA {Vd[:, 0].min():.3f}-{Vd[:, 0].max():.3f} WL {Vd[:, 2].min():.3f}-{Vd[:, 2].max():.3f} "
                f"vs drawn STA {Pd[:, 0].min():.3f}-{Pd[:, 0].max():.3f} WL {zmn:.3f}-{zmx:.3f}; plate BL "
                f"{np.abs(Vd[:, 1]).min():.3f}-{np.abs(Vd[:, 1]).max():.3f} vs drawn {bl0:.3f}-{bl1:.3f} "
                f"(max {1000 * dbl.max():.0f} mm off)",
                worst_list(np.r_[d1, d2], np.r_[np.c_[silh[:, 0], np.zeros(len(silh)), silh[:, 1]],
                                               np.c_[densify_poly(Pd, 0.004, closed=True)[:, 0], np.zeros(len(d2)),
                                                     densify_poly(Pd, 0.004, closed=True)[:, 1]]]))

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
    # radial error overstates the normal error near the tip where the meridian is steep: use normal distance; behind
    # the base plane the skirt steps in to spinner_skirt_r() (inside the cowl lip, MV2-03)
    rs_ = PP.spinner_skirt_r()
    mer = np.c_[np.r_[tt * Lsp, Lsp, Lsp + PP.SPINNER_SKIRT], np.r_[rp, rs_, rs_]]
    dn = Curves([mer]).dist(np.c_[s[on], r[on]])[0]
    rep.add("L4", "spinner meridian about the thrust axis vs spinner_profile", dn, TOL["oml"],
            f"SPINNER_R {F.SPINNER_R}, SHAPE {F.SPINNER_SHAPE}; base plane at the cowl front", worst_list(dn, Vsp[on]))

    # ---------------------------------------------------------------- verify round 2: the rest of the drawn L4 items
    for fn in (_l4_fairing, _l4_chin_inlet, _l4_exhaust_stacks, _l4_controls, _l4_tail_details, _l4_gear):
        try:
            fn(ctx, rep)
        except Exception as ex:                             # one crashing group must not hide the others
            import traceback
            traceback.print_exc()
            rep.add("L4", f"{fn.__name__} crashed", status="FAIL", detail=f"{type(ex).__name__}: {ex}")


# =====================================================================================================================
# L4 (cont.)  verify round 2: the items sheet L4 draws from the parameters that round 1 did not measure -- wing-to-body
# fairing (side / plan / front), chin inlet (front + side), exhaust stacks (3 views), control-surface ends, hinges and
# tabs, rudder gap line, dorsal-fillet foot (plan), fin (front), strakes (front, FR40), gear pivots / brace ends
# =====================================================================================================================
def _xz(P):
    """3-D points for worst_list from 2-D (x, z) side-view points."""
    P = np.asarray(P, float)
    return np.c_[P[:, 0], np.zeros(len(P)), P[:, 1]]


def _two_way(sil, polys, dense=None, step=0.002):
    """(mesh -> parameter, parameter -> mesh) distances between 2-D silhouette points and parameter polylines
    (dense: the parameter points to test the other way; default all polylines densified)."""
    d_m2p = Curves(polys, step=5e-4).dist(sil)[0] if len(sil) else np.zeros(0)
    if dense is None:
        dense = np.vstack([densify_poly(P, step) for P in polys])
    d_p2m = cKDTree(sil).query(dense)[0] if len(sil) else np.full(len(dense), 9.0)
    return d_m2p, d_p2m, dense


def _raster_mask(box, polys=(), tris=None, res=0.001):
    """Boolean raster (rows = second axis) of filled 2-D polygons and / or triangles (m, 3, 2) inside box."""
    from PIL import Image, ImageDraw
    a0, b0, a1, b1 = box
    img = Image.new("1", (int(math.ceil((a1 - a0) / res)) + 1, int(math.ceil((b1 - b0) / res)) + 1), 0)
    dr = ImageDraw.Draw(img)
    for P in polys:
        dr.polygon([tuple(p) for p in (np.asarray(P, float) - [a0, b0]) / res], fill=1)
    if tris is not None:
        for t in (np.asarray(tris, float) - [a0, b0]) / res:
            dr.polygon([tuple(p) for p in t], fill=1)
    return np.array(img, bool)


def _l4_fairing(ctx, rep):
    """Wing-to-body fairing (details.py tables BELLY_FAIRING_*, root_fillet_*): lower silhouette (side), flat-bottomed
    sections (front), root-fillet plan edge on the wing, fillet surface on its parameter law, fillet upper edge."""
    tolp = TOL["planform"]
    dark = L.SURFACES["belly_fairing"]
    Vb, Fb = ctx.mesh(("belly_fairing",))
    Vl, Fl = ctx.mesh(("belly_fairing",), mats=(dark,))              # lower (belly) fairing
    Vf, Ff = ctx.mesh(("belly_fairing",), exclude=(dark,))           # upper root fillet + fairing nose (livery)
    if not len(Fb) or not len(Fl) or not len(Ff):
        rep.add("L4", "wing-to-body fairing: belly / root-fillet sub-meshes", status="FAIL",
                detail=f"belly_fairing faces {len(Fb)}, lower {len(Fl)}, fillet {len(Ff)}")
        return
    # (a) side view: lower silhouette (drawn solid to STA 6465, dashed behind the main gear to 7450, then the keel);
    # normal distance both ways (the nose tip is steep)
    Bt = np.array(D.BELLY_FAIRING_BOT)
    Es = []
    for x in np.arange(Bt[0, 0], Bt[-1, 0] + 1e-9, 0.005):
        S = slice_segments(Vb, Fb, (1, 0, 0), x)
        if len(S):
            Es.append((x, float(densify_segments(S, 0.002)[:, 2].min())))
    Es = np.array(Es)
    Bd = densify_poly(Bt, 0.002)
    # the drawn nose tip on the fuselage side: where the law's standoff just above the line is below ROOT_FILLET_MIN_D
    # the fairing is left to the skin (tangent), so those drawn points have no mesh edge
    thin = (Bd[:, 1] > F.z_bot(F.clip_x(Bd[:, 0])) + 0.002) & \
        (D.root_fillet_standoff(Bd[:, 0], Bd[:, 1] + 0.004) < D.ROOT_FILLET_MIN_D)
    dm, dp, Bd = _two_way(Es, [Bt], dense=Bd[~thin])
    rep.add("L4", "fairing lower silhouette (side) <-> BELLY_FAIRING_BOT", np.r_[dm, dp], tolp,
            f"STA {Bt[0, 0]:.3f}-{Bt[-1, 0]:.3f} (incl. the stretch drawn dashed behind the gear); mesh nose tip STA "
            f"{Es[0, 0]:.3f} WL {Es[0, 1]:.3f} vs drawn {Bt[0, 0]:.3f} / {Bt[0, 1]:.3f} ({int(thin.sum())} drawn points "
            f"at the tip thinner than {1000 * D.ROOT_FILLET_MIN_D:.1f} mm skipped)",
            worst_list(np.r_[dm, dp], _xz(np.r_[Es, Bd])))
    # (b) front view: flat bottom WL + corner radius + vertical walls (belly_fairing_section), both ways
    dm_all, dp_all, per = [], [], []
    rr_ = D.BELLY_FAIRING_FLAT["r"]
    for x in np.arange(5.45, 7.41, 0.15):
        Q = densify_segments(slice_segments(Vl, Fl, (1, 0, 0), x), 0.002)
        ring = D.belly_fairing_section(x, n=1440, z_top=1.30)[:, 1:]
        if not len(Q):
            dm_all.append(np.array([1.0]))
            continue
        dm = Curves([ring], closed=True).dist(Q[:, 1:])[0]
        R = densify_poly(ring, 0.002, closed=True)
        zb = float(D.belly_fairing_bottom(x))
        P3 = np.c_[np.full(len(R), x), R]
        keep = (R[:, 1] < zb + rr_ + 0.002) & (oml_dist(P3) > 0.004)
        zl = D.wing_lower_z(P3[keep, 0], P3[keep, 1])
        k2 = np.isnan(zl) | (P3[keep, 2] < zl - 0.004)
        Pk = P3[keep][k2]
        dp = cKDTree(Q[:, 1:]).query(Pk[:, 1:])[0] if len(Pk) else np.zeros(0)
        dm_all.append(dm)
        dp_all.append(dp)
        per.append((x, 1000 * dm.max(), 1000 * (dp.max() if len(dp) else 0.0)))
    d = np.r_[np.concatenate(dm_all), np.concatenate(dp_all) if dp_all else np.zeros(0)]
    rep.add("L4", "fairing sections (front) <-> belly_fairing_section (flat, r 70)", d, tolp,
            f"STA 5.45-7.40 every 150 mm; flat bottom BL +/-{D.BELLY_FAIRING_FLAT['hw']:.3f}, walls at the footprint "
            "half-width", [f"STA {a:.2f}: {b:.1f} / {c:.1f} mm (mesh->param / param->mesh)"
                           for a, b, c in sorted(per, key=lambda t: -max(t[1], t[2]))[:4]])
    # (c) plan view: the root fillet's outer edge on the wing (BELLY_FAIRING_PLAN), both ways; aft of
    # ROOT_FILLET_TAPER the fillet fades out ahead of the cargo-door (D2) seam -- open item, reported apart
    Pp = np.array(D.BELLY_FAIRING_PLAN)
    xt = D.ROOT_FILLET_TAPER
    xs = np.arange(Pp[0, 0] - 0.04, Pp[-1, 0] + 0.03, 0.002)
    d_in, d_open, P_in, P_open = [], [], [], []
    for sg in (1, -1):
        E_ = []
        for x in xs:
            Q = densify_segments(slice_segments(Vb, Fb, (1, 0, 0), x), 0.002)
            Q = Q[Q[:, 1] * sg > 0]
            if len(Q):
                E_.append((x, float(np.abs(Q[:, 1]).max())))
        E_ = np.array(E_)
        a = E_[(E_[:, 0] <= xt) & (E_[:, 0] >= Pp[0, 0]) & (E_[:, 1] >= Pp[0, 1])]   # outboard of the drawn start
        pp = densify_poly(Pp, 0.002)
        d1 = Curves([Pp]).dist(a)[0]
        d2 = cKDTree(E_).query(pp[pp[:, 0] <= xt])[0]
        d3 = cKDTree(E_).query(pp[pp[:, 0] > xt])[0]
        d_in += [d1, d2]
        P_in += [np.c_[a[:, 0], sg * a[:, 1], np.full(len(a), 1.3)],
                 np.c_[pp[pp[:, 0] <= xt, 0], sg * pp[pp[:, 0] <= xt, 1], np.full(int((pp[:, 0] <= xt).sum()), 1.3)]]
        d_open.append(d3)
        P_open.append(np.c_[pp[pp[:, 0] > xt, 0], sg * pp[pp[:, 0] > xt, 1], np.full(int((pp[:, 0] > xt).sum()), 1.3)])
    d = np.concatenate(d_in)
    rep.add("L4", "root-fillet plan edge on the wing <-> BELLY_FAIRING_PLAN", d, tolp,
            f"STA {Pp[0, 0]:.3f}-{xt:.3f} (to ROOT_FILLET_TAPER), both sides, normal distance",
            worst_list(d, np.vstack(P_in)))
    d = np.concatenate(d_open)
    Po = np.vstack(P_open)
    far = Po[d * 1000 > tolp, 0] if (d * 1000 > tolp).any() else np.zeros(0)
    rep.add("L4", "root-fillet plan edge aft of ROOT_FILLET_TAPER (fade-out) vs drawn", d, tolp,
            f"OPEN (CLAUDE.md: fillet fades out ahead of the D2 seam instead of the drawn tail lobe); drawn edge STA "
            f"{xt:.3f}-{Pp[-1, 0]:.3f} is > {tolp:.0f} mm from the mesh over STA "
            f"{far.min() if len(far) else 0:.3f}-{far.max() if len(far) else 0:.3f}", worst_list(d, Po),
            status="OPEN" if d.max() * 1000 > tolp else None)
    # (d) the fillet / fairing-nose surface lies on its parameter law y = side_y(x, z) + root_fillet_standoff(x, z)
    used = np.unique(Ff)
    P = Vf[used]

    def g(x, z):
        return F.side_y(F.clip_x(x), z) + D.root_fillet_standoff(x, z)
    h = 1e-4
    x, z = P[:, 0], P[:, 2]
    f = np.abs(P[:, 1]) - g(x, z)
    gx = (g(x + h, z) - g(x - h, z)) / (2 * h)
    gz = (g(x, z + h) - g(x, z - h)) / (2 * h)
    dn = f / np.sqrt(1.0 + gx ** 2 + gz ** 2)
    rep.add("L4", "root fillet / fairing nose on its law (side_y + standoff)", dn, TOL["oml"],
            f"{len(P)} vertices; normal distance (first order)", worst_list(dn, P))
    # (e) the fillet's upper edge (side view): mesh vs the parameter edge (standoff = ROOT_FILLET_MIN_D), 2-D both ways;
    # and how far below the drawn line (BELLY_FAIRING_NOSE_EDGE + TAIL) that tangent edge lies
    z_up, z_lo, y_out, (x0, x1) = D.root_fillet_lines()
    Ep, Em = [], {1: [], -1: []}
    for x in np.arange(x0 + 0.002, x1 - 0.002, 0.004):
        zj, S, zu, zl, _ = (float(v) for v in D._fillet_frame(np.array(x)))
        zz = np.linspace(zl, zu, 2400)
        ok = zz[D.root_fillet_standoff(np.full_like(zz, x), zz) >= D.ROOT_FILLET_MIN_D]
        if len(ok):
            Ep.append((x, float(ok.max())))
        Q = densify_segments(slice_segments(Vf, Ff, (1, 0, 0), x), 0.002)
        for sg in (1, -1):
            q = Q[Q[:, 1] * sg > 0] if len(Q) else Q
            if len(q):
                Em[sg].append((x, float(q[:, 2].max())))
    Ep = np.array(Ep)
    d_all, P_all = [], []
    for sg in (1, -1):
        M_ = np.array(Em[sg])
        dm, dp, _ = _two_way(M_, [Ep], dense=Ep)
        d_all += [dm, dp]
        P_all += [np.c_[M_[:, 0], np.full(len(M_), sg * 0.8), M_[:, 1]], np.c_[Ep[:, 0], np.full(len(Ep), sg * 0.8), Ep[:, 1]]]
    d = np.concatenate(d_all)
    rep.add("L4", "root-fillet upper edge (side) <-> its parameter edge", d, tolp,
            f"STA {x0:.3f}-{x1:.3f}, 2-D normal distance; parameter edge = standoff {1000 * D.ROOT_FILLET_MIN_D:.1f} mm "
            "(thinner is left to the skin)", worst_list(d, np.vstack(P_all)))
    off = np.array([(x, float(z_up(x)) - z) for x, z in Ep if x <= D.ROOT_FILLET_TAPER])
    nose = off[off[:, 0] < 5.51]
    i = int(np.argmax(nose[:, 1]))
    aft = off[off[:, 0] >= 5.51]
    rep.add("L4", "drawn fairing upper edge (NOSE_EDGE / TAIL) -> fillet edge", off[:, 1], None,
            f"tangent blend (standoff < {1000 * D.ROOT_FILLET_MIN_D:.1f} mm above): the parameter edge lies "
            f"{1000 * aft[:, 1].min():.0f}-{1000 * aft[:, 1].max():.0f} mm below the drawn line over STA 5.51-"
            f"{D.ROOT_FILLET_TAPER:.2f}, up to {1000 * nose[i, 1]:.0f} mm under NOSE_EDGE (STA {nose[i, 0]:.3f}; the nose edge is "
            "drawn clear of the open airstair door's swept wedge, so its door limit no longer cuts the bump)", status="INFO")


def _l4_chin_inlet(ctx, rep):
    """Chin inlet (powerplant.CHIN_INLET): the mouth (front view) and the polished lip ring (front view + side
    crescent), as sheets L4 / L5 draw them.  The lip is the lower-cowl skin raised to the drawn lip outline
    (powerplant.chin_cheek_offset); its polished part = the raised skin inside the front-view lip outline AND the side
    crescent, so the polished arms end at the crescent top (WL ~1.56); the drawn loop's upper ends (to WL 1.685, into
    the stack roots) are the painted cheek line.  Above the mouth tips the ring's inner edge is behind the spinner."""
    lip_m = L.SURFACES["inlet_lip"]
    mouth = PP.chin_inlet_outline("mouth")
    lipO = PP.chin_inlet_outline("lip")[:-1]               # open at its top ends (they run into the stack roots)
    side = PP.chin_inlet_outline("side")
    z_top = float(side[:, 1].max())
    V, Fm = merged(ctx.get("cowl_lower") + ctx.get("chin_inlet", mats=(lip_m,)))
    comps = [c for c in boundary_components(V, Fm, min_area=1e-6) if c["P"][:, 0].max() < 1.3]
    if not comps:
        rep.add("L4", "chin-inlet mouth (front view) <-> CHIN_INLET mouth", status="FAIL", detail="no mouth hole")
        return
    P = comp_edge_points(V, comps)
    d1, d2, Om = _two_way(P[:, 1:], [mouth])
    rep.add("L4", "chin-inlet mouth (front view) <-> CHIN_INLET mouth outline", np.r_[d1, d2], TOL["opening"],
            f"mesh mouth BL +/-{np.abs(P[:, 1]).max():.3f} WL {P[:, 2].min():.3f}-{P[:, 2].max():.3f} vs drawn BL "
            f"+/-{np.abs(mouth[:, 0]).max():.3f} WL {mouth[:, 1].min():.3f}-{mouth[:, 1].max():.3f}; mouth edge STA "
            f"{P[:, 0].min():.3f}-{P[:, 0].max():.3f} (in the raised lip face)",
            worst_list(np.r_[d1, d2], np.r_[P, np.c_[np.full(len(Om), PP.CHIN_INLET['x']), Om]]))
    Vl, Fl = ctx.mesh(("chin_inlet",), mats=(lip_m,))
    sil = plan_silhouette(Vl, Fl, (-0.45, 1.12, 0.45, 1.78), res=0.001, close_r=0.002, axes=(1, 2))
    sb = PP.axis_point(F.STA["cowl_front"])
    th = np.linspace(0.0, 2.0 * np.pi, 400)
    spin = np.c_[sb[1] + F.SPINNER_R * np.cos(th), sb[2] + F.SPINNER_R * np.sin(th)]
    lipC = lipO[lipO[:, 1] <= z_top]                         # the polished part of the drawn outer edge
    # the polished arms' top ends (the side crescent's top, PP.chin_lip_polished_top): L5 clips the chrome fill at its
    # mean WL, from the spinner disc out to the loop
    za, zb_ = PP.chin_lip_polished_top()
    zt_ = 0.5 * (za + zb_)
    ends = []
    for sg in (1.0, -1.0):
        H_ = lipO[lipO[:, 0] * sg > 0]
        H_ = H_[np.argsort(H_[:, 1])]
        yo = float(np.interp(zt_, H_[:, 1], np.abs(H_[:, 0])))
        yi = float(np.sqrt(max(F.SPINNER_R ** 2 - (zt_ - sb[2]) ** 2, 0.0)))
        ends.append(np.array([[sg * yi, zt_], [sg * yo, zt_]]))
    dm, dp, Ol = _two_way(sil, [lipO, mouth, spin] + ends, dense=densify_poly(lipC, 0.002))
    # visible (front view) areas: the drawn ring = lip outline - mouth - spinner disc (below the crescent top); the mesh
    # chrome - spinner disc
    box = (-0.45, 1.12, 0.45, 1.95)
    S_ = _raster_mask(box, polys=[spin])
    rows = np.arange(S_.shape[0]) * 0.001 + box[1]
    below = (rows <= z_top)[:, None]
    ring = _raster_mask(box, polys=[PP.chin_inlet_outline("lip")]) & ~_raster_mask(box, polys=[mouth]) & ~S_ & below
    chrome = _raster_mask(box, tris=Vl[Fl][:, :, 1:]) & ~S_
    px = 1e-6
    rep.add("L4", "chin-inlet lip ring (front view) <-> CHIN_INLET lip outline", np.r_[dm, dp], TOL["livery"],
            f"chrome lip BL +/-{np.abs(Vl[:, 1]).max():.3f} WL {Vl[:, 2].min():.3f}-{Vl[:, 2].max():.3f} vs drawn ring "
            f"BL +/-{np.abs(lipO[:, 0]).max():.3f} WL {lipO[:, 1].min():.3f}-{lipO[:, 1].max():.3f} (polished to the side "
            f"crescent top WL {z_top:.3f}; inner edge = mouth / spinner disc); visible area {chrome.sum() * px:.3f} vs "
            f"{ring.sum() * px:.3f} m^2 ({100.0 * (ring & chrome).sum() / max(ring.sum(), 1):.0f} % of the drawn ring "
            "is chrome)",
            worst_list(np.r_[dm, dp], np.r_[np.c_[np.full(len(sil), 1.15), sil],
                                              np.c_[np.full(len(Ol), 1.15), Ol]], fmt="x {:.2f} y {:+.3f} z {:.3f}"))
    # the loop's upper ends above the crescent: the painted cheek -- front-view silhouette of the raised lower cowl
    Vc, Fc = merged(ctx.get("cowl_lower") + ctx.get("chin_inlet"))
    keep = Vc[Fc][:, :, 0].max(1) < 1.80
    silc = plan_silhouette(Vc, Fc[keep], (-0.45, 1.12, 0.45, 1.78), res=0.001, close_r=0.002, axes=(1, 2))
    up = lipO[lipO[:, 1] > z_top]
    if len(up) and len(silc):
        d_up = cKDTree(silc).query(densify_poly(up, 0.002))[0]
        rep.add("L4", "chin-inlet cheek line (lip loop above the crescent top) vs raised cowl", d_up, None,
                f"drawn loop WL {z_top:.3f}-{lipO[:, 1].max():.3f} (painted cheek into the stack roots, faded "
                f"CHIN_CHEEK_TOP {PP.CHIN_CHEEK_TOP}) vs the front-view silhouette of the raised lower cowl",
                status="INFO")
    silS = plan_silhouette(Vl, Fl, (1.05, 1.12, 1.35, 1.66), res=0.001, close_r=0.002, axes=(0, 2))
    dm, dp, Os = _two_way(silS, [side])
    Vw, Fw = weld(Vl, Fl)
    _, lab = connected_components(coo_matrix((np.ones(3 * len(Fw)), (np.r_[Fw[:, 0], Fw[:, 1], Fw[:, 2]],
                                                                      np.r_[Fw[:, 1], Fw[:, 2], Fw[:, 0]])),
                                             shape=(len(Vw), len(Vw))), directed=False)
    pieces = sorted((float(Vw[lab == k, 2].min()), float(Vw[lab == k, 2].max())) for k in np.unique(lab[np.unique(Fw)]))
    rep.add("L4", "chin-inlet lip (side view) <-> CHIN_INLET side crescent", np.r_[dm, dp], TOL["livery"],
            f"chrome silhouette, both halves; {len(pieces)} chrome piece(s) at WL "
            + ", ".join(f"{a:.3f}-{b:.3f}" for a, b in pieces[:6]) + (" ..." if len(pieces) > 6 else ""),
            worst_list(np.r_[dm, dp], _xz(np.r_[silS, Os])))


def _l4_exhaust_stacks(ctx, rep):
    """Exhaust stacks: side / plan / front silhouettes of each scarfed tube vs powerplant.exhaust_stack_silhouette."""
    V, Fm = ctx.mesh(("exhaust_stacks",))
    d_all, P_all, per = [], [], []
    for view, axes in (("side", (0, 2)), ("plan", (0, 1)), ("front", (1, 2))):
        for sg in (1, -1):
            keep = V[Fm][:, :, 1].mean(1) * sg > 0
            S = PP.exhaust_stack_silhouette(sg, view)
            box = (S[:, 0].min() - 0.03, S[:, 1].min() - 0.03, S[:, 0].max() + 0.03, S[:, 1].max() + 0.03)
            sil = plan_silhouette(V, Fm[keep], box, res=0.001, close_r=0.002, axes=axes)
            dm, dp, Sd = _two_way(sil, [S])
            d_all += [dm, dp]
            emb = lambda Q, ax=axes: np.array([[q[ax.index(k)] if k in ax else np.nan for k in range(3)] for q in Q])  # noqa: E731
            P_all += [emb(sil), emb(Sd)]
            per.append(f"{view} {'S' if sg > 0 else 'P'} {1000 * max(dm.max(), dp.max()):.1f}")
    d = np.concatenate(d_all)
    rep.add("L4", "exhaust stacks: side / plan / front silhouettes <-> parameters", d, TOL["planform"],
            "max mm per view: " + ", ".join(per), worst_list(d, np.vstack(P_all)))


def _pivot(ctx, pid):
    """(origin, unit axis) of a part's pivot in model axes (extras are in glTF axes: X = y, Y = z, Z = x)."""
    pv = (ctx.extras.get(pid) or {}).get("pivot")
    if not pv:
        return None, None
    o, a = np.asarray(pv["origin"], float), np.asarray(pv["axis"], float)
    return np.array([o[2], o[0], o[1]]), np.array([a[2], a[0], a[1]]) / np.linalg.norm(a)


def _line_dist(o, a, P):
    """Distances of points P from the line o + t a."""
    w = np.atleast_2d(P) - o
    return np.linalg.norm(w - np.outer(w @ a, a), axis=1)


def _l4_controls(ctx, rep):
    """Control-surface ends, hinge lines and tabs as sheet L4 draws them (plan: flap / aileron ends, aileron hinge and
    Flettner tab, elevator hinge; side: rudder hinge, gap line and trim tab)."""
    tolp = TOL["planform"]
    # ---- wing: flap / aileron / tab span ends (plan), aileron + tab hinge (plan)
    dev, lab = [], []
    for side, sg in (("R", 1), ("L", -1)):
        Vf_ = ctx.verts(f"flap_{side}")
        Va = ctx.verts(f"aileron_{side}", exclude=("black",))
        Vt = ctx.verts(f"ail_tab_{side}")
        for nm, got, exp in (("flap outboard end", np.abs(Vf_[:, 1]).max(), W.Y_FLAP[1] - W.GAP),
                             ("aileron inboard end", np.abs(Va[:, 1]).min(), W.Y_AIL[0] + W.GAP),
                             ("aileron outboard end", np.abs(Va[:, 1]).max(), W.Y_AIL[1] - W.GAP),
                             ("tab inboard end", np.abs(Vt[:, 1]).min(), W.Y_AIL[0] + 0.06 + 0.008),
                             ("tab outboard end", np.abs(Vt[:, 1]).max(), W.Y_AIL[0] + 0.72 - 0.008)):
            dev.append(got - exp)
            lab.append(f"{side} {nm}: BL {got:.4f} vs {exp:.4f}")
        # the tab's gap line (plan): its forward edge at the drawn 94.5 % chord line
        for y in np.linspace(W.Y_AIL[0] + 0.12, W.Y_AIL[0] + 0.66, 5):
            Q = densify_segments(slice_segments(*ctx.mesh((f"ail_tab_{side}",)), (0, 1, 0), sg * y), 0.001)
            if len(Q):
                exp = float(W.x_le(y) + 0.945 * W.chord(y))
                dev.append(Q[:, 0].min() - exp)
                lab.append(f"{side} tab front at BL {y:.2f}: STA {Q[:, 0].min():.4f} vs {exp:.4f}")
    dev = np.array(dev)
    i = np.argsort(-np.abs(dev))
    rep.add("L4", "flap / aileron / Flettner-tab ends and tab line (plan)", dev, tolp,
            f"Y_FLAP[1] {W.Y_FLAP[1]}, Y_AIL {W.Y_AIL}, tab BL +0.06..+0.72 at 94.5 % chord, spanwise gaps "
            f"{1000 * W.GAP:.0f} / 8 mm", [lab[k] for k in i[:5]])
    Vfl = ctx.verts("flap_R")
    rep.add("L4", "flap inboard end: 3-D body vs drawn (hidden) Y_FLAP[0]", np.array([np.abs(Vfl[:, 1]).min() - W.Y_FLAP[0]]),
            None, f"3-D flap body from BL {np.abs(Vfl[:, 1]).min():.3f} (FLAP_BODY_Y0 {W.FLAP_BODY_Y0}: outboard of the belly "
            f"fairing) vs the drawn end BL {W.Y_FLAP[0]} dashed under the fairing (CLAUDE.md)", status="INFO")
    (hy0, hx0), (hy1, hx1) = W.AIL_HINGE
    dh, lab = [], []
    for side, sg in (("R", 1), ("L", -1)):
        o, a = _pivot(ctx, f"aileron_{side}")
        if o is None:
            dh.append(1.0)
            lab.append(f"aileron_{side}: no pivot")
            continue
        for y, x in ((hy0, hx0), (hy1, hx1)):
            t = (sg * y - o[1]) / a[1]
            p = o + t * a
            dh.append(p[0] - x)
            lab.append(f"aileron_{side} hinge at BL {y:.2f}: STA {p[0]:.4f} vs AIL_HINGE {x:.4f}")
    # elevator hinge (plan chain line: ELEV_XH of the local chord = STA ~14.000) and rudder hinge (side chain line)
    for side, sg in (("R", 1), ("L", -1)):
        o, a = _pivot(ctx, f"elevator_{side}")
        for y in E.ELEV_Y:
            x_exp = E.stab_le(y) + E.ELEV_XH * (E.stab_te(y) - E.stab_le(y))
            t = (sg * y - o[1]) / a[1]
            p = o + t * a
            dh.append(math.hypot(p[0] - x_exp, p[2] - E.STAB_Z))
            lab.append(f"elevator_{side} hinge at BL {y:.2f}: STA {p[0]:.4f} WL {p[2]:.4f} vs {x_exp:.4f} / {E.STAB_Z}")
    o, a = _pivot(ctx, "rudder")
    for e in ("bottom", "top"):
        q = np.array(E.rudder_edge_point(E.RUD_XH, e))
        dh.append(float(_line_dist(o, a, np.array([q[0], 0.0, q[1]]))[0]))
        lab.append(f"rudder hinge {e} point ({q[0]:.4f}, {q[1]:.4f}) off the pivot line")
    t0, t1, tx = E.RUD_TAB
    o, a = _pivot(ctx, "rudder_tab")
    for z in (t0, t1):
        q = np.array([E.fin_le(z) + tx * (E.fin_te(z) - E.fin_le(z)), 0.0, z])
        dh.append(float(_line_dist(o, a, q)[0]))
        lab.append(f"rudder-tab hinge at WL {z:.2f}: drawn STA {q[0]:.4f} off the pivot line")
    dh = np.array(dh)
    i = np.argsort(-np.abs(dh))
    rep.add("L4", "hinge lines: aileron / elevator / rudder / rudder tab vs pivots", dh, tolp,
            "pivot extras (glTF) vs AIL_HINGE, ELEV_XH, RUD_XH (rudder_edge_point), RUD_TAB", [lab[k] for k in i[:5]])
    # rudder gap line (side: E.rudder_outline's gap line at E.rudder_gap_xc(), drawn solid): the visible seam of the 3-D
    # rudder is the fixed fin skin's aft edge (the cove lip, wing.x_end_of_plain); the rudder nose (RUD_NOSE_XC, drawn
    # hidden) lies inside the cove
    Vn, Fn = ctx.mesh(("fin",), mats=paint_mats())
    Vru, Fru = ctx.mesh(("rudder",), mats=paint_mats())
    dev, loc, xcs, noses = [], [], [], []
    zb, ztp = E.RUD_Z
    for z in np.arange(zb + 0.05, ztp - 0.05, 0.05):
        Q = densify_segments(slice_segments(Vn, Fn, (0, 0, 1), z), 0.001)
        R_ = densify_segments(slice_segments(Vru, Fru, (0, 0, 1), z), 0.001)
        if not len(Q):
            continue
        le, te = E.fin_le(z), E.fin_te(z)
        xg = float(E.fin_chord_x(E.rudder_gap_xc(), z))
        dev.append(Q[:, 0].max() - xg)
        loc.append((xg, 0.0, z))
        xcs.append((Q[:, 0].max() - le) / (te - le))
        if len(R_):
            noses.append((R_[:, 0].min() - le) / (te - le))
    lip = W.x_end_of_plain(E.fin_section(3.0), E.RUD_XH, E.RUD_COVE_GAP)[1]
    rep.add("L4", "rudder gap line (side): fin-skin lip vs drawn gap line (rudder_gap_xc)", np.array(dev), tolp,
            f"visible seam (fin skin aft edge) at {min(xcs):.4f}-{max(xcs):.4f} c (x_end_of_plain {lip:.4f}) vs the drawn "
            f"gap line {E.rudder_gap_xc():.4f} c; the 3-D rudder nose ({min(noses):.3f}-{max(noses):.3f} c, drawn "
            f"hidden at RUD_NOSE_XC {E.RUD_NOSE_XC:.3f}) is in the cove", worst_list(dev, np.array(loc)))
    Vr, Fr = ctx.mesh(("rudder_tab",))
    dev, loc = [], []
    for z in np.linspace(t0 + 0.05, t1 - 0.05, 8):
        Q = densify_segments(slice_segments(Vr, Fr, (0, 0, 1), z), 0.001)
        xg = E.fin_le(z) + tx * (E.fin_te(z) - E.fin_le(z))
        dev.append(Q[:, 0].min() - xg if len(Q) else 1.0)
        loc.append((xg, 0.0, z))
    Vt_ = ctx.verts("rudder_tab")
    dev += [Vt_[:, 2].min() - t0, Vt_[:, 2].max() - t1]
    loc += [(0, 0, t0), (0, 0, t1)]
    rep.add("L4", "rudder trim tab (side) vs RUD_TAB", np.array(dev), tolp,
            f"tab front vs {tx} chord; tab WL {Vt_[:, 2].min():.3f}-{Vt_[:, 2].max():.3f} vs {t0}-{t1}",
            worst_list(dev, np.array(loc)))


def _l4_tail_details(ctx, rep):
    """Dorsal / fin root-fillet foot (plan: dorsal_fillet_hw), fin thickness (front view), strakes (front view at
    FR40, strake_frame)."""
    tolp = TOL["planform"]
    V, Fm = ctx.mesh(("dorsal_fin", "fin"), mats=paint_mats())
    T = np.array(E.DORSAL_FILLET)
    dev, loc = [], []
    for x in np.arange(T[0, 0] + 0.03, T[-1, 0] - 0.01, 0.05):
        Q = densify_segments(slice_segments(V, Fm, (1, 0, 0), x), 0.002)
        hw = float(E.dorsal_fillet_hw(x))
        for sg in (1, -1):
            q = Q[Q[:, 1] * sg > 0] if len(Q) else Q
            dev.append(np.abs(q[:, 1]).max() - hw if len(q) else 1.0)
            loc.append((x, sg * hw, float(F.z_at(x, hw))))
    rep.add("L4", "dorsal / fin root-fillet foot (plan) vs dorsal_fillet_hw", np.array(dev), tolp,
            f"STA {T[0, 0] + 0.03:.2f}-{T[-1, 0] - 0.01:.2f} every 50 mm, both sides (max |BL| of dorsal + fin)",
            worst_list(dev, np.array(loc)))
    # fin (front view): half-thickness per WL from the fin / crown junction to the bullet bottom
    zc = float(np.linspace(2.3, 3.0, 701)[np.argmin(np.abs(F.z_top(E.fin_le(np.linspace(2.3, 3.0, 701)))
                                                          - np.linspace(2.3, 3.0, 701)))])
    Vn, Fn = ctx.mesh(("fin", "rudder", "rudder_tab"), mats=paint_mats())
    dev, loc = [], []
    for z in np.arange(zc + 0.10, E.BULLET[8][2] - 0.02, 0.05):
        s = E.fin_section(z)
        fw = 0.5 * s.chord * float(s.airfoil.thickness(np.linspace(0, 1, 401)).max())
        Q = densify_segments(slice_segments(Vn, Fn, (0, 0, 1), z), 0.001)
        dev.append(np.abs(Q[:, 1]).max() - fw if len(Q) else 1.0)
        loc.append((float(E.fin_le(z)), fw, z))
    rep.add("L4", "fin half-thickness (front view) vs fin_section", np.array(dev), tolp,
            f"WL {zc + 0.1:.2f}-{E.BULLET[8][2] - 0.02:.2f} every 50 mm", worst_list(dev, np.array(loc)))
    # strakes (front view at FR40): the plate's centre line root -> tip, canted STRAKE_CANT
    Vs, Fs = ctx.mesh(("strakes",))
    x = F.FRAMES["FR40"]
    dev, loc = [], []
    for xx in (x, x - 0.6, x - 1.2):
        fr = E.strake_frame(xx)
        if fr is None:
            continue
        r, t = fr
        Q = densify_segments(slice_segments(Vs, Fs, (1, 0, 0), xx), 0.001)
        for sg in (1, -1):
            q = Q[Q[:, 1] * sg > 0]
            if not len(q):
                dev.append(1.0)
                loc.append(tuple(t * [1, sg, 1]))
                continue
            rs, ts = r * [1, sg, 1], t * [1, sg, 1]
            u = (ts - rs) / np.linalg.norm(ts - rs)
            dl = _line_dist(rs, u, q) - 0.5 * E.STRAKE_T               # off the plate (beyond its half-thickness)
            dev.append(max(0.0, float(dl.max())))
            loc.append(tuple(ts))
            tip = q[np.argmax((q - rs) @ u)]
            dev.append(float((tip - rs) @ u - np.linalg.norm(ts - rs)))
            loc.append(tuple(ts))
    rep.add("L4", "strakes (front view, FR40 and 0.6 / 1.2 m ahead) vs strake_frame", np.array(dev), tolp,
            f"plate centre line root -> tip (cant {math.degrees(E.STRAKE_CANT):.0f} deg) and tip reach",
            worst_list(dev, np.array(loc)))


def _l4_gear(ctx, rep):
    """Gear pivots and brace ends (the drawn trunnion / pivot circles and brace lines) vs the pivot extras."""
    dev, lab = [], []
    for pid, P_exp, ax_exp in (("gear_main_R", G.MAIN_TRUNNION, (1, 0, 0)),
                               ("gear_main_L", G.MAIN_TRUNNION * [1, -1, 1], (1, 0, 0)),
                               ("gear_nose", G.NOSE_PIVOT, (0, 1, 0))):
        o, a = _pivot(ctx, pid)
        if o is None:
            dev.append(1.0)
            lab.append(f"{pid}: no pivot")
            continue
        dev += list(o - P_exp) + [math.sqrt(max(0.0, 1.0 - float(abs(a @ np.array(ax_exp))) ** 2))]
        lab.append(f"{pid}: origin {np.round(o, 4).tolist()} vs {np.round(P_exp, 4).tolist()}, axis {np.round(a, 3).tolist()}")
    for pid, (A, B) in (("brace_main_R_up", G.MAIN_BRACE), ("brace_main_L_up", tuple(np.array(p) * [1, -1, 1] for p in G.MAIN_BRACE)),
                        ("brace_nose_up", G.NOSE_BRACE)):
        pv = (ctx.extras.get(pid) or {}).get("pivot") or {}
        if "A" not in pv:
            dev.append(1.0)
            lab.append(f"{pid}: no brace data")
            continue
        dev += list(np.array(pv["A"]) - np.array(A)) + list(np.array(pv["B0"]) - np.array(B))
        lab.append(f"{pid}: A {np.round(pv['A'], 4).tolist()} B0 {np.round(pv['B0'], 4).tolist()} vs {np.round(A, 4).tolist()} "
                   f"/ {np.round(B, 4).tolist()}")
    dev = np.array(dev)
    rep.add("L4", "gear trunnion / nose pivot / brace ends vs gear parameters", dev, TOL["planform"],
            "pivot extras (MAIN_TRUNNION, NOSE_PIVOT, MAIN_BRACE, NOSE_BRACE)", lab)
    # the retracted main wheel (L4 gear detail, phantom: gear.retracted_wheel) = the built tyre turned by the pivot's
    # own retract angle (right-handed about the glTF axis, as web/viewer/kinematics.js poses it)
    dev, lab = [], []
    for pid, sg in (("gear_main_R", 1), ("gear_main_L", -1)):
        o, a = _pivot(ctx, pid)
        pv = (ctx.extras.get(pid) or {}).get("pivot") or {}
        Vt = ctx.verts(pid, mats=("tire",))
        if o is None or not len(Vt):
            dev.append(1.0)
            lab.append(f"{pid}: no pivot / tyre")
            continue
        th = math.radians(float(pv.get("retract", 0.0)))
        K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
        Rm = np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * K @ K
        c = 0.5 * (Vt.min(0) + Vt.max(0))
        cr = o + Rm @ (c - o)
        exp = G.retracted_wheel(sg)
        dev += list(cr - exp)
        lab.append(f"{pid}: retracted tyre centre {np.round(cr, 4).tolist()} vs retracted_wheel {np.round(exp, 4).tolist()}")
    rep.add("L4", "retracted main wheel (phantom) vs pivot kinematics", np.array(dev), TOL["planform"],
            "tyre centre turned by the pivot's retract angle", lab)


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
        # inboard end: BL 0.95, or the root fillet's foot line where the fillet covers it (details.boot_under_fillet:
        # the boot ends in its own step on the foot line, MQ2-01)
        Pp_ = np.array(D.BELLY_FAIRING_PLAN)
        y_ft = D.root_fillet_lines()[2](np.clip(P[:, 0], Pp_[0, 0], Pp_[-1, 0]))
        y0 = np.maximum(W.BOOT_Y[0], y_ft)
        dy = np.minimum(np.abs(y - y0), np.abs(y - W.BOOT_Y[1]))
        dev.append(np.minimum(np.abs(dx), dy))
        Ps.append(P)
    d = np.concatenate(dev)
    rep.add("L5", "wing boot band edges (10 % up / 6.5 % low, BL 0.95-7.43)", d, tol, "deice_boot boundary, both wings; "
            "upper band from the root fillet's foot line where it covers BL 0.95-1.0",
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
    for fn in (_l5_bands, _l5_details):
        try:
            fn(ctx, rep)
        except Exception as ex:
            import traceback
            traceback.print_exc()
            rep.add("L5", f"{fn.__name__} crashed", status="FAIL", detail=f"{type(ex).__name__}: {ex}")
    if plots and plot_pts:
        P = np.vstack([p for p, _ in plot_pts])
        dd = np.concatenate([d for _, d in plot_pts])
        _plot_livery(plots / "L5_boundaries.png", P, dd)


def _l5_bands(ctx, rep):
    """Colour bands whose edges round 1 only checked for presence: tailplane LE boot (STAB_BOOT), winglet pinstripe
    (WINGLET_PIN), blade erosion strip (BLADE_LE_STRIP), exhaust-stack collar (STACK_COLLAR)."""
    tol = TOL["livery"]
    # ---- STAB_BOOT: chordwise edge 8 % (upper) / 6 % (lower) of the plan chord, span end at STAB_TIP_RIB
    Vb, Fb = ctx.mesh(("stabilizer",), mats=(L.SURFACES["boot"],))
    comps = boundary_components(Vb, Fb, min_area=1e-6, seams=True)
    P = np.vstack([c["P"] for c in comps]) if comps else np.zeros((0, 3))
    if len(P):
        y = np.abs(P[:, 1])
        le = np.array([E.stab_le(v) for v in y])
        te = np.array([E.stab_te(v) for v in y])
        frac = np.where(P[:, 2] >= E.STAB_Z, L.STAB_BOOT["upper"], L.STAB_BOOT["lower"])
        dx = P[:, 0] - (le + frac * (te - le))
        Bt = np.array(E.BULLET)
        in_bullet = y <= np.interp(P[:, 0], Bt[:, 0], Bt[:, 3]) + 0.005     # the inboard end is inside the bullet
        dy = np.where(in_bullet, 0.0, np.abs(y - E.STAB_TIP_RIB))           # span end at the tip rib
        d = np.minimum(np.abs(dx), dy)
        w = np.array([(P[i, 0] - le[i]) / (te[i] - le[i]) for i in range(len(P))])
        rep.add("L5", "tailplane LE boot edges (STAB_BOOT 8 / 6 %, to STAB_TIP_RIB)", d, tol,
                f"boot BL {y.min():.3f} (inside the bullet) - {y.max():.3f} (rib {E.STAB_TIP_RIB}); chord fraction of "
                f"the edge {w[(dy > 0.01) & (P[:, 2] >= E.STAB_Z)].max():.4f} up / "
                f"{w[(dy > 0.01) & (P[:, 2] < E.STAB_Z)].max():.4f} low",
                worst_list(d, P))
    else:
        rep.add("L5", "tailplane LE boot edges (STAB_BOOT)", status="FAIL", detail="no boot sub-mesh")
    # ---- WINGLET_PIN: |d| = half_width about the plane of winglet section s, chord c0..c1
    p = L.WINGLET_PIN
    secs = W.winglet_sections(40, 30)
    sec = secs[int(round(p["s"] * (len(secs) - 1)))]
    dev, P_, wid = [], [], []
    for side, sg in (("R", 1), ("L", -1)):
        V, Fm = ctx.mesh((f"winglet_{side}",), mats=("paint_pinstripe",))
        comps = boundary_components(V, Fm, min_area=1e-7)
        if not comps:
            dev.append(np.array([1.0]))
            P_.append(np.zeros((1, 3)))
            continue
        B = np.vstack([c["P"] for c in comps])
        le = sec.le * [1, sg, 1]
        e_c = sec.e_c * [1, sg, 1]
        e_t = np.asarray(sec.e_t, float) * [1, sg, 1]
        n = np.cross(e_c, e_t)
        n /= np.linalg.norm(n)
        dd = (B - le) @ n
        xc = ((B - le) @ e_c) / sec.chord
        d = np.minimum(np.abs(np.abs(dd) - p["half_width"]),
                       np.minimum(np.abs(xc - p["c0"]), np.abs(xc - p["c1"])) * sec.chord)
        dev.append(d)
        P_.append(B)
        mid = (xc > 0.2) & (xc < 0.8)
        wid.append(1000 * (dd[mid].max() - dd[mid].min()) if mid.any() else np.nan)
    d = np.concatenate(dev)
    rep.add("L5", "winglet pinstripe edges (WINGLET_PIN, inboard face)", d, tol,
            f"band width {', '.join(f'{w_:.1f}' for w_ in wid)} mm (R, L) vs {2000 * p['half_width']:.0f}; chord "
            f"{p['c0']}-{p['c1']} of winglet section s {p['s']}", worst_list(d, np.vstack(P_)))
    # ---- BLADE_LE_STRIP: erosion shield r0 .. red-band inner edge, width from the LE line
    r_out = PP.PROP_R - L.PROP_BANDS[-1][2]
    q = L.BLADE_LE_STRIP
    dev, P_ = [], []
    for k in range(PP.N_BLADES):
        V, Fm = ctx.mesh((f"blade_{k + 1}",), mats=(L.SURFACES["blade_le"],))
        comps = boundary_components(V, Fm, min_area=1e-7)
        if not comps:
            dev.append(np.array([1.0]))
            P_.append(np.zeros((1, 3)))
            continue
        B = np.vstack([c["P"] for c in comps])
        r, dl = L.blade_le_distance(B, k)
        d = np.minimum(np.minimum(np.abs(r - q["r0"]), np.abs(r - r_out)), np.abs(dl - q["width"]))
        dev.append(d)
        P_.append(B)
    d = np.concatenate(dev)
    rep.add("L5", "blade erosion-strip edges (BLADE_LE_STRIP)", d, tol,
            f"r {q['r0']}-{r_out:.3f}, {1000 * q['width']:.0f} mm from the LE line, 5 blades", worst_list(d, np.vstack(P_)))
    # ---- exhaust-stack collar: polished / black boundary vs powerplant.exhaust_stack_collar
    cb = colour_boundaries(ctx, "exhaust_stacks", mats={L.SURFACES["exhaust"], "black"})
    B = np.vstack([P for P, ma, mb in cb if {ma, mb} == {L.SURFACES["exhaust"], "black"}]) if cb else np.zeros((0, 3))
    if len(B):
        C = [PP.exhaust_stack_collar(sg) for sg in (1, -1)]
        d1 = Curves(C, step=5e-4).dist(B)[0]
        d2 = cKDTree(B).query(np.vstack([densify_poly(c, 0.003) for c in C]))[0]
        rep.add("L5", "exhaust-stack collar edge (STACK_COLLAR) <-> exhaust_stack_collar", np.r_[d1, d2], tol,
                f"{PP.STACK_COLLAR * 1000:.0f} mm band at the scarfed outlets, both stacks",
                worst_list(np.r_[d1, d2], np.r_[B, np.vstack([densify_poly(c, 0.003) for c in C])]))
    else:
        rep.add("L5", "exhaust-stack collar edge (STACK_COLLAR)", status="FAIL", detail="no polished / black boundary")


def _l5_details(ctx, rep):
    """Plan / side features L5 draws from the parameters: flap-track canoes (FLAP_CANOE_Y), nose-gear bay (NOSE_BAY)."""
    # ---- canoes: the fixed fairings (and the flap-carried aft parts) at FLAP_CANOE_Y
    V = np.vstack([ctx.verts("flap_fairings")] + [ctx.verts(f"flap_canoes_{s}") for s in ("R", "L")])
    dev, lab = [], []
    for sg in (1, -1):
        for y in D.FLAP_CANOE_Y:
            m = (V[:, 1] * sg > 0) & (np.abs(np.abs(V[:, 1]) - y) < 0.2)
            if not m.any():
                dev.append(1.0)
                lab.append(f"BL {sg * y:+.3f}: no canoe")
                continue
            yc = 0.5 * (np.abs(V[m, 1]).min() + np.abs(V[m, 1]).max())
            dev.append(yc - y)
            lab.append(f"BL {sg * y:+.3f}: canoe centre {sg * yc:+.4f}")
    rep.add("L5", "flap-track canoes: plan BL vs FLAP_CANOE_Y", np.array(dev), TOL["planform"], "; ".join(lab[:3]), lab)
    # ---- nose-gear bay: the hole in the lower skins vs bays.NOSE_BAY (plan), both ways
    V, Fm = merged(ctx.get("cowl_lower") + ctx.get("fus_fwd", mats=paint_mats()))
    comps = [c for c in boundary_components(V, Fm, min_area=1e-5, drop=drop_panel_ends)
             if c["P"][:, 2].max() < 1.15 and np.abs(BY.nose_bay_sdf(c["P"][:, 0], c["P"][:, 1])).mean() < 0.03]
    if not comps:
        rep.add("L5", "nose-gear bay opening vs NOSE_BAY (plan)", status="FAIL", detail="no bay hole found")
        return
    B = comp_edge_points(V, comps)
    nb = BY.NOSE_BAY
    O = densify_poly(sdf2d.rrect_outline(nb["cx"], nb["cy"], nb["hx"], nb["hy"], nb["r"], 32), 0.002, closed=True)
    d1 = np.abs(BY.nose_bay_sdf(B[:, 0], B[:, 1]))
    d2 = cKDTree(B[:, :2]).query(O)[0]
    d = np.r_[d1, d2]
    rep.add("L5", "nose-gear bay opening (plan) <-> NOSE_BAY", d, TOL["opening"],
            f"hole STA {B[:, 0].min():.3f}-{B[:, 0].max():.3f} BL +/-{np.abs(B[:, 1]).max():.3f} vs NOSE_BAY "
            f"{nb['cx'] - nb['hx']:.3f}-{nb['cx'] + nb['hx']:.3f} +/-{nb['hy']:.3f}; {len(comps)} loop(s)",
            worst_list(d, np.r_[B, np.c_[O, np.full(len(O), 0.95)]]))


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
    n_open = sum(r.status == "OPEN" for r in rep.rows)
    js = Path(a.json)
    js.parent.mkdir(parents=True, exist_ok=True)
    js.write_text(json.dumps(dict(glb=str(glb), tol_mm=TOL, seconds=round(time.time() - t0, 1),
                                  rows=[r.__dict__ for r in rep.rows]), indent=1))
    print(f"{'CONSISTENCY OK' if n_fail == 0 else 'CONSISTENCY FAIL'}: {len(rep.rows) - n_fail}/{len(rep.rows)} rows "
          f"pass, info or open ({n_open} open owner items), {n_fail} fail ({time.time() - t0:.0f} s; report {js.relative_to(ROOT) if js.is_relative_to(ROOT) else js})")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
