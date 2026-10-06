"""
Acceptance checks of the yoke solids (model/yoke_geom.py, YOKE_DESIGN rev L) -- printed by sheets L6Y / L6Y2 and
summarised on L6Y2 (judges r2 DR2-01..04, r3 DR3-01 / 02 / 07 / 10):

  exactness   the 2-D fields' zero level against the curve-law polylines (shell, grips, pads, body, shield): the
              zero crossings along rows / columns vs the dense outline, max mm, and the crossing direction noise
  proud       nothing of the moulding stands above the outboard head's round trim face or the inboard shield facet
              inside their outlines (max height, mm; the switches that sit on them excluded)
  curve law   every interior sample of every outline (not a corner): the curvature either side of it from the run's
              spline (rev L: C2 cubic, judges DR3-07) -- max relative jump
  cusps       exact sections of the black MOULDING (body + grips, judges DR3-04) normal to each grip axis every
              2.5 mm from its bottom to the top of its head, planes u = const through the necks / web / heads and
              horizontal planes h = const, and the cover at the centreline / across the arm: contour corners turning
              more than CUSP_DEG within +-CUSP_CHORD that are not a tabled crease (the pad pocket's step, groove and
              bead; the cover's parting grooves / step V; the trim face's grooves)
  connected   every horizontal section h 62..94 cuts the black moulding in ONE piece per side (no free fin, DR3-01)
  normals     0.25 mm depth-map meshes seen from aft (cover, both grips' pads and frames, both heads, the web) and from
              the front (the body's and grips' forward faces, the body's top): facet-averaged vertex normals against
              the solids' analytic normals away from silhouettes; the tabled creases (grooves, step V, pad steps, the
              face / facet rims) reported apart -- the Stage-3 acceptance metric (95th percentile within 2 deg)

    python3 -m model.yoke_checks          (prints; disk-cached per design in out/tmp/yoke_geom_cache)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from model import yoke_geom as G  # noqa: E402

CUSP_DEG = 25.0             # turning within +-CUSP_CHORD along the contour: a local radius under ~0.7 mm
CUSP_CHORD = 0.15


# ============================================================================================ exactness
def exactness():
    """Max distance of the fields' zero crossings (rows and columns every 0.37 mm) from the dense outlines."""
    out = {}
    for nm, P in (("shell", G.shell_outline()), ("grip_out", G.grip_outline("out")), ("grip_in", G.grip_outline("in")),
                  ("pad_out", G.pad_outline("out")), ("pad_in", G.pad_outline("in")), ("body", G.body_outline())):
        F = G.field(nm, P) if nm in ("shell", "body") else G.field(nm if nm.startswith("grip") else nm, P)
        from scipy.spatial import cKDTree
        Q = np.vstack([P, P[:1]])
        dense = np.vstack([a + np.linspace(0, 1, 6, endpoint=False)[:, None] * (b - a) for a, b in zip(Q[:-1], Q[1:])])
        tr = cKDTree(dense)
        lo, hi = P.min(0) - 1.0, P.max(0) + 1.0
        devs = []
        for ax in (0, 1):
            for c in np.arange(lo[1 - ax], hi[1 - ax], 0.37):
                t = np.arange(lo[ax], hi[ax], 0.02)
                X, Y = (t, np.full_like(t, c)) if ax == 0 else (np.full_like(t, c), t)
                v = F(X, Y)
                i = np.where(np.sign(v[:-1]) != np.sign(v[1:]))[0]
                if not len(i):
                    continue
                f = v[i] / (v[i] - v[i + 1])
                pts = np.c_[X[i] + f * (X[i + 1] - X[i]), Y[i] + f * (Y[i + 1] - Y[i])]
                d, _ = tr.query(pts)
                devs.append(d)
        d = np.concatenate(devs)
        out[nm] = dict(n=int(len(d)), max=float(d.max()), mean=float(d.mean()))
    return out


# ============================================================================================ curve law (DR3-07)
CURVE_KEYS = (("shell_half", True), ("insert_side", False), ("insert_lower_half", True), ("grip_out", False),
              ("grip_in", False), ("pad_out", False), ("pad_in", False), ("body_half", False), ("body_in", False),
              ("shield", False))


def _kappa(cs, t):
    d1, d2 = cs(t, 1), cs(t, 2)
    return (d1[..., 0] * d2[..., 1] - d1[..., 1] * d2[..., 0]) / np.maximum(np.hypot(d1[..., 0], d1[..., 1]), 1e-12) ** 3


def curve_law():
    """Max relative curvature jump at the interior samples of every outline's spline runs (corners excluded: they are
    tabled fillets / creases), from the run splines' left / right limits."""
    out = {}
    T = G.T()
    for key, mirror in CURVE_KEYS:
        P = np.asarray(T[key], float)
        corners = {int(i) for i, _ in T.get(key + "_corners", ())}
        closed = key not in ("insert_side",)
        if mirror:
            P, cs = G.mirror_half(P, {i: 0.0 for i in corners})
            corners = set(cs)
        n = len(P)
        idx = sorted(corners)
        runs = []
        if not idx and closed:
            runs.append((P, True))
        elif closed:
            for k, i in enumerate(idx):
                j = idx[(k + 1) % len(idx)]
                seq = list(range(i, j + 1)) if j > i else list(range(i, n)) + list(range(0, j + 1))
                runs.append((P[seq], False))
        else:
            runs.append((P, False))
        worst = 0.0
        nk = 0
        for R, per in runs:
            if len(R) < 3:
                continue
            spl, t = G.spline_of(R, closed=per)
            inner = t[:-1] if per else t[1:-1]
            for tk in inner:
                ka, kb = _kappa(spl, np.array([tk - 1e-7, tk + 1e-7]))
                den = max(abs(ka), abs(kb), 1e-6)
                if den > 1.0 / 200.0:
                    worst = max(worst, abs(ka - kb) / den)
                nk += 1
        out[key] = dict(knots=nk, jump=float(worst))
    return out


# ============================================================================================ proud
def proud():
    """Max height (mm) of the black moulding above the round trim face's plane inside its disc (less its R edge), and
    above the shield facet inside its outline (inboard head, own sense -> co-pilot u < 0)."""
    out = {}
    c, n = G.head_out_face()
    eu, ev = G._facet_frame(c, n)
    T = G.T()
    R = 0.5 * float(T["head_out"][2]) - float(T["head_out"][6])
    rs, ts = np.meshgrid(np.linspace(0.0, R, 40), np.linspace(0.0, 2 * np.pi, 145))
    P = c + (rs * np.cos(ts))[..., None] * eu + (rs * np.sin(ts))[..., None] * ev
    out["trim_face"] = _height_above(P.reshape(-1, 3), n, lambda Q: G.part_sdf("black", Q[:, 0], Q[:, 1], Q[:, 2]))
    ci, ni = G.head_in_face()
    eui, evi = G._facet_frame(ci, ni)
    S = G.shield_outline()
    from cad import sdf2d
    xs, ys = np.meshgrid(np.arange(S[:, 0].min(), S[:, 0].max(), 0.4), np.arange(S[:, 1].min(), S[:, 1].max(), 0.4))
    m = sdf2d.polygon(xs, ys, S) < -1.0
    Q = ci + xs[m][:, None] * eui + ys[m][:, None] * evi
    Q = Q * [-1.0, 1.0, 1.0]
    nc = ni * [-1.0, 1.0, 1.0]
    out["shield"] = _height_above(Q, nc, lambda X: G.part_sdf("black", X[:, 0], X[:, 1], X[:, 2]))
    return out


def _height_above(P, n, f, top=12.0, step=0.05):
    """Max t in (0, top] such that P + t n is inside f, over the points P (0 if none)."""
    best = 0.0
    for t in np.arange(step, top, step):
        v = f(P + t * n)
        if (v < 0).any():
            best = t
    return float(best)


# ============================================================================================ cusps
def _turns(C, chord=CUSP_CHORD):
    """Turning angle (deg) of the closed contour C over a +-chord window at every vertex."""
    C = np.asarray(C, float)
    if np.allclose(C[0], C[-1]):
        C = C[:-1]
    L = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(np.vstack([C, C[:1]]), axis=0), axis=1))]
    tot = L[-1]
    s = L[:-1]
    n = len(C)
    out = np.zeros(n)
    Cc = np.vstack([C, C[:1]])
    for k in range(n):
        sa, sb = (s[k] - chord) % tot, (s[k] + chord) % tot
        pa = np.array([np.interp(sa, L, Cc[:, 0]), np.interp(sa, L, Cc[:, 1])])
        pb = np.array([np.interp(sb, L, Cc[:, 0]), np.interp(sb, L, Cc[:, 1])])
        a, b = C[k] - pa, pb - C[k]
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na < 1e-9 or nb < 1e-9:
            continue
        out[k] = math.degrees(math.acos(float(np.clip(np.dot(a, b) / (na * nb), -1, 1))))
    return out


def _scan(pt, e1, e2, ext, parts, step=0.1, thr=None):
    """Untabled corners of the exact section of `parts` on the plane (pt; e1, e2) over ext: [(part, turn, X)] and the
    number of closed contours per part."""
    thr = thr or CUSP_DEG
    T = G.T()
    gw, bead = float(T["pad_section"][4]), float(T["pad_section"][3])
    S = G.section(pt, e1, e2, ext, parts=parts, step=step)
    found = []
    grazing = 0
    for part, Cs in S.items():
        for C in Cs:
            if len(C) < 20:
                continue
            tn = _turns(C)
            k = np.where(tn > thr)[0]
            k = k[np.minimum.reduce([C[k, 0] - ext[0], ext[2] - C[k, 0], C[k, 1] - ext[1], ext[3] - C[k, 1]]) > 0.6]
            if not len(k):
                continue
            X = np.asarray(pt)[None] + C[k, :1] * np.asarray(e1)[None] + C[k, 1:2] * np.asarray(e2)[None]
            # confirm in 3-D: the surface normals CUSP_CHORD either side of the corner along the contour must turn more
            # than CUSP_DEG too -- a plane grazing a tabled round (an R 2 ridge cut at ~10-20 deg) shows a sharp-looking
            # contour tip although the surface turns smoothly (rev L)
            keep3 = _normal_turn(part, C, k, pt, e1, e2) > thr
            grazing += int((~keep3).sum())
            k, X = k[keep3], X[keep3]
            if not len(k):
                continue
            tab = np.zeros(len(k), bool)
            if part != "cover":
                for g in ("out", "in"):
                    Xg = X * ([-1.0, 1.0, 1.0] if g == "in" else [1.0, 1.0, 1.0])
                    z, uf, hf = G._to_plane(Xg[:, 0], Xg[:, 1], Xg[:, 2], g)
                    dp = G.field("pad_" + g, G.pad_outline(g))(uf, hf)
                    tab |= (dp > -(gw + 2 * bead) - 0.8) & (dp < 0.8) & (np.abs(z) < 4.0)
                tab |= _trim_face_tabled(X)
            for j, kk in enumerate(k):
                if tab[j]:
                    continue
                if part == "cover" and _cover_tabled(X[j]):
                    continue
                if part != "cover" and _black_tabled(X[j]):
                    continue
                found.append((part, round(float(tn[kk]), 1), tuple(np.round(X[j], 1))))
    cl = []
    for f in found:                                                    # one per 1 mm cluster
        if all(np.linalg.norm(np.subtract(f[2], c_[2])) > 1.0 for c_ in cl):
            cl.append(f)
    _scan.grazing = getattr(_scan, "grazing", 0) + grazing
    return cl, {p_: len([C for C in Cs if len(C) >= 20]) for p_, Cs in S.items()}


def _normal_turn(part, C, k, pt, e1, e2, chord=None):
    """Angle (deg) between the solid's surface normals at the contour points `chord` before / after each index k."""
    chord = chord or CUSP_CHORD
    C = np.asarray(C, float)
    closed = np.allclose(C[0], C[-1])
    Cc = C[:-1] if closed else C
    L = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(np.vstack([Cc, Cc[:1]]), axis=0), axis=1))]
    tot = L[-1]
    s0 = L[np.minimum(k, len(Cc) - 1)]
    Q = np.vstack([Cc, Cc[:1]])

    def at(sv):
        sv = sv % tot
        return np.c_[np.interp(sv, L, Q[:, 0]), np.interp(sv, L, Q[:, 1])]
    out = []
    for sa, sb in zip(s0 - chord, s0 + chord):
        P2 = np.vstack([at(np.array([sa])), at(np.array([sb]))])
        X = np.asarray(pt)[None] + P2[:, :1] * np.asarray(e1)[None] + P2[:, 1:2] * np.asarray(e2)[None]
        e = 0.005
        off = np.vstack([np.eye(3) * e, -np.eye(3) * e])
        Y = (X[:, None, :] + off[None, :, :]).reshape(-1, 3)
        f = np.asarray(G.part_sdf(part, Y[:, 0], Y[:, 1], Y[:, 2]), float).reshape(len(X), 6)
        g = []
        for r in f:
            v = r[:3] - r[3:]
            g.append(v / max(np.linalg.norm(v), 1e-12))
        out.append(math.degrees(math.acos(float(np.clip(np.dot(g[0], g[1]), -1.0, 1.0)))))
    return np.array(out)


def _trim_face_tabled(X):
    """On the trim face's grooves (ring, slot chords) or its rim's R 1.5 edge band."""
    T = G.T()
    c, n = G.head_out_face()
    eu, ev = G._facet_frame(c, n)
    Q = np.atleast_2d(X) - c
    return (np.abs(Q @ n) < 1.0) & (np.hypot(Q @ eu, Q @ ev) < 0.5 * float(T["head_out"][2]) + 0.5)


CUSP_PLANES_U = (-96.3, -92.3, -88.3, -84.3, -80.3, -76.3, -72.7, -68.3, -64.3, 64.3, 68.3, 72.7, 76.3, 80.3, 84.3,
                 88.3, 92.3, 96.3, 100.3)
CUSP_PLANES_H = (-50.0, -20.0, 10.0, 30.0, 40.0, 50.0, 58.0, 62.0, 66.0, 70.0, 74.0, 78.0, 82.0, 86.0, 90.0, 93.0)


def cusps():
    """Untabled sharp corners in exact sections of the black moulding and the cover: {name: dict(cusps, sections)}
    -- grip-normal sections from each grip's bottom to its head top (every 2.5 mm), planes u = const through the necks /
    web / heads, horizontal planes, Z-Z and K-K (rev L, judges DR3-02 / 04)."""
    out = {}
    _scan.grazing = 0
    for g in ("out", "in"):
        Q = G.grip_outline(g)
        h_top = float(G.T()["head_out"][1] + 0.5 * G.T()["head_out"][2]) if g == "out" else float(Q[:, 1].max())
        bad, n_sec = [], 0
        for h in np.arange(Q[:, 1].min() + 2.5, h_top + 0.1, 2.5):
            p, e1, e2 = G.grip_section_frame(g, h)
            cl, nc = _scan(G.to_cop(p, g), G.to_cop(e1, g), G.to_cop(e2, g), (-42.0, -48.0, 36.0, 14.0), ("black",))
            n_sec += 1
            bad += [(round(float(h), 1),) + c_[1:] for c_ in cl]
        out["grip_" + g] = dict(sections=n_sec, cusps=bad)
    bad, n_sec = [], 0
    for u in CUSP_PLANES_U:
        cl, nc = _scan((u, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0, 0.0), (-80.0, -10.0, 22.0, 100.0), ("black", "cover"))
        n_sec += 1
        bad += [("u", u) + c_[1:] for c_ in cl]
    out["necks / web / heads (u planes)"] = dict(sections=n_sec, cusps=bad)
    bad, n_sec = [], 0
    for h in CUSP_PLANES_H:
        cl, nc = _scan((0.0, h, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (-150.0, -80.0, 150.0, 22.0), ("black",),
                       step=0.15)
        n_sec += 1
        bad += [("h", h) + c_[1:] for c_ in cl]
    out["horizontal (h planes)"] = dict(sections=n_sec, cusps=bad)
    # Z-Z (u = 0) and K-K (across the outboard arm at (52, 45), 30 deg up outboard)
    for nm, pt, e1, e2, ext in (("Z-Z", (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0, 0.0), (-76.0, -66.0, 12.0, 70.0)),
                                ("K-K", (52.0, 45.0, 0.0), (0.0, 0.0, 1.0),
                                 (-math.sin(math.radians(30.0)), math.cos(math.radians(30.0)), 0.0),
                                 (-80.0, -26.0, 10.0, 26.0))):
        cl, nc = _scan(pt, e1, e2, ext, ("black", "cover"))
        out[nm] = dict(cusps=[c_ for c_ in cl])
    out["_grazing"] = int(_scan.grazing)
    return out


def connected(hs=np.arange(62.0, 94.1, 2.0)):
    """Islands of the black moulding per side in horizontal sections h 62..94 (judges DR3-01: the rev K web stood as a
    free fin beside the trim head at h 85-93)."""
    rows = []
    for h in hs:
        S = G.section((0.0, float(h), 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (-160.0, -90.0, 160.0, 24.0),
                      parts=("black",), step=0.2)
        Cs = [C for C in S.get("black", []) if len(C) > 12 and abs(_area2(C)) > 1.0]
        n_out = sum(1 for C in Cs if C[:, 0].mean() > 0)
        n_in = sum(1 for C in Cs if C[:, 0].mean() < 0)
        rows.append((float(h), n_out, n_in))
    return rows


def _area2(C):
    return 0.5 * float(np.sum(C[:, 0] * np.roll(C[:, 1], -1) - np.roll(C[:, 0], -1) * C[:, 1]))


def _cover_tabled(X):
    """A cover section corner that IS tabled: on a parting groove / the step V / the badge grooves, at the cover's
    back edges (R 0.5 / sharp: the back of a 3 mm shell meeting the body), the TCS pocket, the top land."""
    U, Hh, A = (np.array([float(v)]) for v in X)
    T = G.T()
    for nm, P in G._groove_curves().items():
        if G._curve_dist("groove_" + nm, P)(U, Hh)[0] < 1.6:
            return True
    back = float(G.face_a(Hh)[0] - G.crown_bevel(U, Hh)[0]) - float(T["cover_t"])
    if abs(float(A[0]) - back) < 1.0:
        return True
    c, n = G.tcs_axis()                                          # the TCS seat pocket's rim
    P = np.array([float(v) for v in X]) - c
    z = float(P @ n)
    r = float(np.linalg.norm(P - z * n))
    if abs(r - 0.5 * float(T["tcs"][2])) < 0.8 and z > -float(T["tcs_seat"]) - 0.8:
        return True
    d2 = float(G.field("shell", G.shell_outline())(U, Hh)[0])      # the top land (C1 chamfer 2.0 x 0.8) at top edges
    if d2 > -float(T["crown"][3]) - 0.6:
        gh = float((G.field("shell", G.shell_outline())(U, Hh + 0.2) - G.field("shell", G.shell_outline())(U, Hh - 0.2))[0])
        if gh > 0.0:
            return True
    return False


def _black_tabled(X):
    """A black-moulding section corner that is tabled: where the moulding meets the cover's back (a contact line, not a
    surface corner) or the AFCS boss's back face edge."""
    U, Hh, A = (np.array([float(v)]) for v in X)
    T = G.T()
    back = float(G.face_a(Hh)[0]) - float(T["cover_t"])
    if abs(float(A[0]) - back) < 1.2 and abs(float(U[0])) < 80:
        return True
    return False


# ============================================================================================ normals
PATCHES = {"cover stem / inserts": ((-20.0, -50.0, 20.0, 10.0), 1), "cover arm + TCS": ((36.0, 24.0, 70.0, 62.0), 1),
           "outboard grip pad / frame": ((102.0, -40.0, 142.0, 40.0), 1),
           "inboard grip pad / frame": ((-144.0, -46.0, -96.0, 34.0), 1),
           "outboard head + face": ((92.0, 60.0, 134.0, 98.0), 1), "inboard head + shield": ((-128.0, 50.0, -84.0, 92.0), 1),
           "web (aft)": ((58.0, 30.0, 98.0, 92.0), 1),
           "body top + web top (from above-aft)": ((-60.0, 40.0, 90.0, 92.0), 3),
           "forward faces (from the front)": ((-140.0, -50.0, 140.0, 90.0), -1)}


def _depth_patch(box, px=0.25, parts=("black", "cover"), view=1):
    """Depth map of the solids over the front-view box: view 1 = seen from aft (rays along -a), -1 = from the front
    (rays along +a), 3 = from above-aft (rays 40 deg below the horizontal, forward-down: the tops)."""
    u = np.arange(box[0], box[2], px)
    h = np.arange(box[1], box[3], px)
    UU, HH = np.meshgrid(u, h)
    f = lambda U, H_, A: np.minimum.reduce([G.part_sdf(p, U, H_, A) for p in parts])  # noqa: E731
    if view == 3:
        d = np.array([0.0, -math.sin(math.radians(40.0)), -math.cos(math.radians(40.0))])
    else:
        d = np.array([0.0, 0.0, -1.0 if view == 1 else 1.0])
    O = np.stack([UU, HH, np.full(UU.shape, 0.0)], -1) - 120.0 * d
    t = np.zeros(UU.shape)
    tp = np.zeros(UU.shape)                    # the last position known OUTSIDE (rev L: the bisection brackets
    alive = np.ones(UU.shape, bool)            # [tp, t]; the top land's field is up to ~4-Lipschitz, the march could
    hit = np.zeros(UU.shape, bool)             # overshoot it by more than the old +-0.12 bracket)
    for _ in range(800):
        if not alive.any():
            break
        idx = np.where(alive)
        P = O[idx] + t[idx][:, None] * d
        v = f(P[:, 0], P[:, 1], P[:, 2])
        done = v < 0.02
        hit[idx[0][done], idx[1][done]] = True
        go = ~done
        tp[idx[0][go & (v > 0)], idx[1][go & (v > 0)]] = t[idx[0][go & (v > 0)], idx[1][go & (v > 0)]]
        t[idx[0][go], idx[1][go]] += np.maximum(0.7 * v[go], 0.02)
        alive[idx] = ~done & (t[idx] < 260.0)
    lo, hi = np.where(hit, np.minimum(tp, t - 0.02), t - 0.12), t + 0.12
    for _ in range(24):
        mid = 0.5 * (lo + hi)
        P = O + mid[..., None] * d
        v = np.where(hit, f(P[..., 0], P[..., 1], P[..., 2]), 1.0)
        inside = v < 0
        hi = np.where(hit & inside, mid, hi)
        lo = np.where(hit & ~inside, mid, lo)
    tt = np.where(hit, 0.5 * (lo + hi), np.nan)
    P = O + np.nan_to_num(tt)[..., None] * d
    P[~hit] = np.nan
    return P, hit, f, d


def _tabled_crease_curves():
    """Front-view (u, h) curves of the tabled creases (co-pilot sense): grooves, step V, lower insert, badge, pads,
    the trim face rim, the shield outline, TCS / AFCS rings."""
    F = []
    for nm, P in G._groove_curves().items():
        F.append(np.asarray(P, float))
    for g, sg in (("out", 1.0), ("in", -1.0)):
        F.append(G.pad_outline(g) * [sg, 1.0])
    c, n = G.head_out_face()
    eu, ev = G._facet_frame(c, n)
    t = np.linspace(0, 2 * np.pi, 145)
    for R in (0.5 * float(G.T()["head_out"][2]), 0.5 * float(G.T()["trim"][2])):
        F.append((c + R * (np.cos(t)[:, None] * eu + np.sin(t)[:, None] * ev))[:, :2])
    od, lune = float(G.T()["trim"][2]), float(G.T()["trim_lunes"][0])
    xs = np.linspace(-0.5 * od, 0.5 * od, 60)
    for sg in (-1.0, 1.0):                                       # the trim face's slot chords (grooves, rev M)
        F.append((c + xs[:, None] * eu + sg * (0.5 * od - lune) * ev)[:, :2])
    ci, ni = G.head_in_face()
    e1, e2 = G._facet_frame(ci, ni)
    S = G.shield_outline()
    F.append((ci + S[:, :1] * e1 + S[:, 1:2] * e2)[:, :2] * [-1.0, 1.0])
    for key, k in (("tcs", 2), ("afcs", 4), ("afcs", 2)):
        cc = np.asarray(G.T()[key][:2], float)
        F.append(cc + 0.5 * float(G.T()[key][k]) * np.c_[np.cos(t), np.sin(t)])
    # the cover's TOP LAND (crown[2] x crown[3]: 2.0 fore-aft over 0.8, its normal turning ~75 deg inside 0.8 mm,
    # finer than the 0.4 mm above-aft sampling) along the outline's upward-facing edges, with the R 1 perimeter round
    S = G.shell_outline()
    Fs = G.field("shell", S)
    gh = (Fs(S[:, 0], S[:, 1] + 0.2) - Fs(S[:, 0], S[:, 1] - 0.2)) / 0.4
    gu = (Fs(S[:, 0] + 0.2, S[:, 1]) - Fs(S[:, 0] - 0.2, S[:, 1])) / 0.4
    n = np.c_[gu, gh] / np.maximum(np.hypot(gu, gh), 1e-9)[:, None]
    top = gh > 0.3
    F.append(S[top])
    F.append(S[top] - 0.8 * n[top])            # its inner C1 edge: the 0.4 mm mesh stencil reaches across it
    return np.vstack(F)


# side / below views (rev M, judges DR4-02): the grips' walls, the necks' undersides, the heels -- (centre (u, h, a),
# azimuth from aft toward +u (outboard), elevation, half width, half height)
SIDE_PATCHES = {"outboard grip slot side + web (from aft-inboard)": ((100.0, 30.0, -10.0), -50.0, 10.0, 26.0, 70.0),
                "outboard grip outer side (from aft-outboard)": ((128.0, 25.0, -10.0), 55.0, 5.0, 22.0, 72.0),
                "inboard grip slot side + neck (from aft-outboard)": ((-98.0, 25.0, -10.0), 50.0, 10.0, 26.0, 68.0),
                "inboard grip outer side (from aft-inboard)": ((-128.0, 20.0, -10.0), -55.0, 5.0, 22.0, 70.0),
                "heels, foot, slot tops (from below-aft)": ((0.0, -20.0, -15.0), 0.0, -40.0, 150.0, 40.0)}


def _view_frame(az, el):
    """(d ray direction, right, up) of an orthographic view: az from aft (+a) toward +u, el up."""
    a, e = math.radians(az), math.radians(el)
    eye = np.array([math.sin(a) * math.cos(e), math.sin(e), math.cos(a) * math.cos(e)])
    right = np.cross([0.0, 1.0, 0.0], eye)
    right /= np.linalg.norm(right)
    return -eye, right, np.cross(eye, right)


def _depth_view(c, az, el, hw, hh, px, parts=("black", "cover")):
    """Depth map of the solids in an arbitrary orthographic view (as _depth_patch): P (ny, nx, 3), hit, f, d."""
    d, right, up = _view_frame(az, el)
    xs = np.arange(-hw, hw, px)
    ys = np.arange(-hh, hh, px)
    X, Y = np.meshgrid(xs, ys)
    f = lambda U, H_, A: np.minimum.reduce([G.part_sdf(p, U, H_, A) for p in parts])  # noqa: E731
    O = np.asarray(c, float) + X[..., None] * right + Y[..., None] * up - 160.0 * d
    return _march(O, d, f) + (f, d)


def _march(O, d, f, tmax=330.0):
    t = np.zeros(O.shape[:2])
    tp = np.zeros(O.shape[:2])
    alive = np.ones(O.shape[:2], bool)
    hit = np.zeros(O.shape[:2], bool)
    for _ in range(900):
        if not alive.any():
            break
        idx = np.where(alive)
        P = O[idx] + t[idx][:, None] * d
        v = f(P[:, 0], P[:, 1], P[:, 2])
        done = v < 0.02
        hit[idx[0][done], idx[1][done]] = True
        go = ~done
        tp[idx[0][go & (v > 0)], idx[1][go & (v > 0)]] = t[idx[0][go & (v > 0)], idx[1][go & (v > 0)]]
        t[idx[0][go], idx[1][go]] += np.maximum(0.7 * v[go], 0.02)
        alive[idx] = ~done & (t[idx] < tmax)
    lo, hi = np.where(hit, np.minimum(tp, t - 0.02), t - 0.12), t + 0.12
    for _ in range(24):
        mid = 0.5 * (lo + hi)
        P = O + mid[..., None] * d
        v = np.where(hit, f(P[..., 0], P[..., 1], P[..., 2]), 1.0)
        inside = v < 0
        hi = np.where(hit & inside, mid, hi)
        lo = np.where(hit & ~inside, mid, lo)
    tt = np.where(hit, 0.5 * (lo + hi), np.nan)
    P = O + np.nan_to_num(tt)[..., None] * d
    P[~hit] = np.nan
    return P, hit


_PATCH_CACHE = {}


def _patch(nm, px=0.25):
    """Shared depth map + analytic normals + part labels of a named patch (PATCHES or SIDE_PATCHES)."""
    key = (nm, px)
    if key in _PATCH_CACHE:
        return _PATCH_CACHE[key]
    if nm in PATCHES:
        box, view = PATCHES[nm]
        pxx = px if view == 1 else 0.4
        P, hit, f, d = _depth_patch(box, pxx, view=view)
    else:
        c, az, el, hw, hh = SIDE_PATCHES[nm]
        pxx = 0.3 if hw < 40 else 0.4
        P, hit, f, d = _depth_view(c, az, el, hw, hh, pxx)
    na = np.full(P.shape, np.nan)
    Pf = P[hit]
    na[hit] = _normals_at(f, Pf)
    lab = np.full(hit.shape, -1)
    lab[hit] = np.argmin(np.stack([G.part_sdf(p_, Pf[:, 0], Pf[:, 1], Pf[:, 2]) for p_ in ("black", "cover")]), 0)
    _PATCH_CACHE[key] = (P, hit, f, d, na, lab, pxx)
    return _PATCH_CACHE[key]


def _normals_at(f, Q, e=0.005):
    g = np.stack([f(Q[:, 0] + e, Q[:, 1], Q[:, 2]) - f(Q[:, 0] - e, Q[:, 1], Q[:, 2]),
                  f(Q[:, 0], Q[:, 1] + e, Q[:, 2]) - f(Q[:, 0], Q[:, 1] - e, Q[:, 2]),
                  f(Q[:, 0], Q[:, 1], Q[:, 2] + e) - f(Q[:, 0], Q[:, 1], Q[:, 2] - e)], -1)
    return g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-12)


def normals(px=0.25):
    from scipy.spatial import cKDTree
    tree = cKDTree(_tabled_crease_curves())
    out = {}
    for nm in PATCHES:
        P, hit, f, d, na, lab, pxx = _patch(nm, px)
        Pz = np.nan_to_num(P)
        nm_ = np.zeros(P.shape)
        for (di, dj), (dk, dl) in (((0, 1), (1, 0)), ((1, 0), (0, -1)), ((0, -1), (-1, 0)), ((-1, 0), (0, 1))):
            a = np.roll(Pz, (-di, -dj), (0, 1)) - Pz
            b = np.roll(Pz, (-dk, -dl), (0, 1)) - Pz
            nm_ += np.cross(b, a)
        nm_ /= np.maximum(np.linalg.norm(nm_, axis=-1, keepdims=True), 1e-12)
        nm_ *= np.sign(np.sum(nm_ * np.nan_to_num(na), axis=-1, keepdims=True) + 1e-12)
        dev = np.degrees(np.arccos(np.clip(np.sum(nm_ * np.nan_to_num(na), -1), -1, 1)))
        ok = hit.copy()
        ok[:2, :] = ok[-2:, :] = ok[:, :2] = ok[:, -2:] = False
        depth = np.where(hit, np.einsum("ijk,k->ij", Pz, d), 1e3)
        for sft in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            nb = np.roll(depth, sft, (0, 1))
            ok &= np.abs(nb - depth) < 3.0 * pxx
            nn = np.roll(np.nan_to_num(na), sft, (0, 1))
            ok &= np.sum(nn * np.nan_to_num(na), -1) > math.cos(math.radians(25.0))
        ok &= np.abs(np.einsum("ijk,k->ij", np.nan_to_num(na), d)) > math.cos(math.radians(70.0))
        # part boundaries (the white cover's top edge seen against the black body's top behind it from above-aft: a
        # depth step under the 3-pixel test) are not surfaces: pixels whose neighbours belong to the other part apart
        for sft in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            ok &= np.roll(lab, sft, (0, 1)) == lab
        dc, _ = tree.query(Pz[..., :2].reshape(-1, 2))
        near = (dc.reshape(hit.shape) < 1.0) & hit
        d_all = dev[ok & ~near]
        d_cr = dev[ok & near]
        out[nm] = dict(n=int((ok & ~near).sum()), p50=float(np.percentile(d_all, 50)),
                       p95=float(np.percentile(d_all, 95)), p99=float(np.percentile(d_all, 99)), max=float(d_all.max()),
                       crease_max=float(d_cr.max()) if len(d_cr) else 0.0,
                       excluded=float((hit & ~ok).sum() / hit.sum()))
    return out


# ============================================================================================ creases (rev M, DR4-02)
CREASE_SEED = 4.0          # deg between adjacent pixels: a candidate (R < ~3.6 mm at 0.25 px)
CREASE_SUB = 16            # sub-samples per refinement level


def _resample(f, d, Oa, Ob, k):
    """(N, k + 1, 3) surface points on the sub-rays between the ray origins Oa, Ob (N, 3) (origins 1.5 mm before the
    surface along d), marched and bisected -- vectorised over the N pairs."""
    w = np.linspace(0.0, 1.0, k + 1)[None, :, None]
    O = (Oa[:, None, :] + w * (Ob - Oa)[:, None, :]).reshape(-1, 3)
    t = np.zeros(len(O))
    alive = np.ones(len(O), bool)
    for _ in range(300):
        if not alive.any():
            break
        ia = np.where(alive)[0]
        v = f(*(O[ia] + t[ia, None] * d).T)
        done = v < 2e-5
        t[ia[~done]] += np.maximum(0.8 * v[~done], 2e-5)
        alive[ia[done]] = False
        alive &= t < 6.0
    lo, hi = t - 1e-4, t + 1e-4
    for _ in range(16):
        m = 0.5 * (lo + hi)
        ins = f(*(O + m[:, None] * d).T) < 0
        hi, lo = np.where(ins, m, hi), np.where(ins, lo, m)
    return (O + (0.5 * (lo + hi))[:, None] * d).reshape(-1, k + 1, 3)


def _concentrated(f, d, Pa, Pb, levels=2, min_turn=2.0):
    """For N pixel pairs (surface points Pa, Pb): True where the normal turn between them stays CONCENTRATED in one
    sub-step (>= half of the level's total and >= min_turn deg) through `levels` 16x refinements -- a normal
    discontinuity (crease) -- False where it spreads (a round); and the first level's total turn."""
    N = len(Pa)
    Oa, Ob = Pa - 1.5 * d, Pb - 1.5 * d
    keep = np.ones(N, bool)
    tot0 = np.zeros(N)
    idx = np.arange(N)
    for lev in range(levels):
        if not len(idx):
            break
        Q = _resample(f, d, Oa[idx], Ob[idx], CREASE_SUB)
        step = float(np.median(np.linalg.norm(Q[:, 1] - Q[:, 0], axis=1))) if len(Q) else 0.01
        n = _normals_at(f, Q.reshape(-1, 3), e=max(min(0.005, 0.25 * step), 2e-5)).reshape(Q.shape)
        turn = np.degrees(np.arccos(np.clip(np.sum(n[:, 1:] * n[:, :-1], -1), -1.0, 1.0)))
        tot = turn.sum(1)
        k = np.argmax(turn, 1)
        mx = turn[np.arange(len(idx)), k]
        if lev == 0:
            tot0[idx] = tot
        ok = (mx >= 0.5 * tot) & (mx >= min_turn)
        keep[idx[~ok]] = False
        idx, k, Q = idx[ok], k[ok], Q[ok]
        # the worst sub-step's two surface points become the next level's pair
        Oa[idx] = Q[np.arange(len(idx)), k] - 1.5 * d
        Ob[idx] = Q[np.arange(len(idx)), k + 1] - 1.5 * d
    return keep, tot0


def creases(px=0.25):
    """Untabled CREASES on the visible surfaces (rev M, judges DR4-02 -- rev L's section scan sampled the contours every
    0.1-0.25 mm and missed a crease along a line between its planes): every patch of normals() plus side / below views;
    a candidate is a pair of adjacent pixels whose analytic normals turn > CREASE_SEED, same part, no depth step,
    facing the view within 75 deg, more than 1.0 mm (front view) from a tabled crease curve; it is CONFIRMED when the
    turn stays concentrated in one sub-step through two 16x refinements along the pair (a normal discontinuity at <=
    1 micron), and set aside as a round otherwise.  {patch: dict(candidates, rounds, creases [(u, h, a, turn)])}."""
    from scipy.spatial import cKDTree
    tree = cKDTree(_tabled_crease_curves())
    out = {}
    for nm in list(PATCHES) + list(SIDE_PATCHES):
        P, hit, f, d, na, lab, pxx = _patch(nm, px)
        Pz = np.nan_to_num(P)
        nz = np.nan_to_num(na)
        depth = np.where(hit, np.einsum("ijk,k->ij", Pz, d), 1e3)
        dc, _ = tree.query(Pz[..., :2].reshape(-1, 2))
        free = hit & (dc.reshape(hit.shape) > 1.0) & (np.abs(np.einsum("ijk,k->ij", nz, d)) > math.cos(math.radians(75.0)))
        cands = []
        for sft in ((0, 1), (1, 0)):
            nn = np.roll(nz, (-sft[0], -sft[1]), (0, 1))
            ang = np.degrees(np.arccos(np.clip(np.sum(nn * nz, -1), -1.0, 1.0)))
            ok = (free & np.roll(free, (-sft[0], -sft[1]), (0, 1)) &
                  (np.abs(np.roll(depth, (-sft[0], -sft[1]), (0, 1)) - depth) < 3.0 * pxx) &
                  (np.roll(lab, (-sft[0], -sft[1]), (0, 1)) == lab) & (ang > CREASE_SEED))
            ok[-1, :] = ok[:, -1] = False
            for i, j in zip(*np.where(ok)):
                cands.append(((i, j), (i + sft[0], j + sft[1])))
        found, rounds, tabled = [], 0, 0
        if cands:
            A_ = np.array([Pz[a] for a, _ in cands])
            B_ = np.array([Pz[b] for _, b in cands])
            ok_, tot = _concentrated(f, d, A_, B_)
            rounds = int((~ok_).sum())
            labs = [lab[a] for a, _ in cands]
            for i in np.where(ok_)[0]:
                X = 0.5 * (A_[i] + B_[i])
                if _tabled_3d(X, "cover" if labs[i] == 1 else "black"):
                    tabled += 1
                    continue
                found.append(tuple(np.round(X, 2)) + (round(float(tot[i]), 1),))
        cl = []
        for q in found:                                                   # one per 1 mm cluster
            if all(np.linalg.norm(np.subtract(q[:3], c_[:3])) > 1.0 for c_ in cl):
                cl.append(q)
        out[nm] = dict(candidates=len(cands), rounds=rounds, tabled=tabled, creases=cl, n_crease_px=len(found))
    return out


def _tabled_3d(X, part=None):
    """A confirmed crease that IS tabled, tested in 3-D (the front-view distance to the tabled curves misses the pad
    pocket's floor corners, which lie up to ~1.3 mm (front view) off the outline on the toed planes): the pad pocket's
    step, groove and bead (plane coordinates of the point itself), the trim face's rim / grooves, the shield facet's
    edge, the cover's tabled features (_cover_tabled) and the cover / moulding contact (_black_tabled)."""
    T_ = G.T()
    gw, bead = float(T_["pad_section"][4]), float(T_["pad_section"][3])
    Xa = np.atleast_2d(np.asarray(X, float))
    for g, sg in (("out", 1.0), ("in", -1.0)):
        Xg = Xa * [sg, 1.0, 1.0]
        z, uf, hf = G._to_plane(Xg[:, 0], Xg[:, 1], Xg[:, 2], g)
        dp = G.field("pad_" + g, G.pad_outline(g))(uf, hf)
        if bool(((dp > -(gw + 2 * bead) - 0.8) & (dp < 0.8) & (np.abs(z) < 4.0)).any()):
            return True
    if bool(_trim_face_tabled(Xa).any()):
        return True
    ci, ni = G.head_in_face()
    e1, e2 = G._facet_frame(ci, ni)
    Q = Xa * [-1.0, 1.0, 1.0] - ci
    from cad import sdf2d
    ds_ = sdf2d.polygon(Q @ e1, Q @ e2, G.shield_outline())
    if bool(((np.abs(ds_) < 1.2) & (np.abs(Q @ ni) < 1.2)).any()):
        return True
    x = Xa[0]
    if part == "cover":
        return bool(_cover_tabled(x))
    return bool(_black_tabled(x))


# ============================================================================================ field ridges (DR4-02)
RIDGE_DEG = 20.0


def _unit(fn, Q, e=0.004):
    return _normals_at(fn, Q, e)


def ridges(px=0.25):
    """Do the joins' rounds read smooth fields?  (rev M, judges DR4-02: rev L's body-grip R 3 read grip_out 1.3 mm out
    where its field had a ridge -- gradient norm 0.68, the normal flipping > 70 deg within 0.015 mm.)  The ROUNDS' OWN
    SURFACE POINTS: the moulding's surface points (head / web / neck / pad / forward-face patches) where both fields of a
    join lie between 0.02 and its radius -- the points whose position and normal the round takes from both fields:
    the body vs either grip (R neck[3]) and, inside each grip, the prism vs the head (R r_u); a RIDGE where a field's
    unit gradient turns > RIDGE_DEG within 0.01 mm (any axis).  gmin = the smallest gradient norm met (a field that
    is not a true distance there draws its round larger than tabled: 1 / gmin x at worst).  {join: dict(points,
    ridges, gmin, worst [(u, h, a, field, turn, |grad|)])}."""
    r = float(G.T()["neck"][3])
    pts = []
    for nm in ("outboard head + face", "inboard head + shield", "web (aft)", "outboard grip pad / frame",
               "inboard grip pad / frame", "forward faces (from the front)", "body top + web top (from above-aft)",
               "outboard grip slot side + web (from aft-inboard)", "inboard grip slot side + neck (from aft-outboard)"):
        P, hit, f, d, na, lab, pxx = _patch(nm, px)
        pts.append(P[hit & (lab != 1)])
    X = np.vstack(pts)
    out = {}
    fo = lambda U, H_, A: G.grip_solid(U, H_, A, "out")                       # noqa: E731
    fi = lambda U, H_, A: G.grip_solid(-U, H_, A, "in")                       # noqa: E731
    b = G.body(X[:, 0], X[:, 1], X[:, 2])
    for jn, fg, rr in (("body x outboard grip (R %g)" % r, fo, r), ("body x inboard grip (R %g)" % r, fi, r)):
        gv = fg(X[:, 0], X[:, 1], X[:, 2])
        m = (b > 0.02) & (gv > 0.02) & (b < rr) & (gv < rr)
        out[jn] = _ridge_rows(X[m], (("body", G.body), ("grip", fg)))
    for g, sg in (("out", 1.0), ("in", -1.0)):
        r_u = float(G.T()["head_zone"][0 if g == "out" else 1][9])
        Xg = X * [sg, 1.0, 1.0]
        pr, hd = G._grip_parts(Xg[:, 0], Xg[:, 1], Xg[:, 2], g, split=True)
        m = (pr > 0.02) & (hd > 0.02) & (pr < r_u) & (hd < r_u)
        fp = lambda U, H_, A, g=g: G._grip_parts(U, H_, A, g, split=True)[0]    # noqa: E731
        fh = lambda U, H_, A, g=g: G._grip_parts(U, H_, A, g, split=True)[1]    # noqa: E731
        out[f"{g}board prism aft side x head (R {r_u:g})"] = _ridge_rows(Xg[m], (("prism", fp), ("head", fh)))
    return out


def _ridge_rows(Q, fns, e=0.01):
    if not len(Q):
        return dict(points=0, ridges=0, worst=[])
    if len(Q) > 60000:
        Q = Q[np.linspace(0, len(Q) - 1, 60000).astype(int)]
    worst = []
    gmin = 9.0
    bad = np.zeros(len(Q), bool)
    for nm, fn in fns:
        n0 = _unit(fn, Q)
        g0 = np.stack([fn(Q[:, 0] + 0.002, Q[:, 1], Q[:, 2]) - fn(Q[:, 0] - 0.002, Q[:, 1], Q[:, 2]),
                       fn(Q[:, 0], Q[:, 1] + 0.002, Q[:, 2]) - fn(Q[:, 0], Q[:, 1] - 0.002, Q[:, 2]),
                       fn(Q[:, 0], Q[:, 1], Q[:, 2] + 0.002) - fn(Q[:, 0], Q[:, 1], Q[:, 2] - 0.002)], -1) / 0.004
        gn = np.linalg.norm(g0, axis=1)
        tmax = np.zeros(len(Q))
        for k in range(3):
            dv = np.zeros(3)
            dv[k] = e
            n1 = _unit(fn, Q + dv)
            tmax = np.maximum(tmax, np.degrees(np.arccos(np.clip(np.sum(n0 * n1, -1), -1.0, 1.0))))
        r_ = tmax > RIDGE_DEG
        gmin = min(gmin, float(gn.min())) if len(gn) else gmin
        bad |= r_
        for i in np.argsort(-tmax)[:3]:
            if r_[i]:
                worst.append(tuple(np.round(Q[i], 2)) + (nm, round(float(tmax[i]), 1), round(float(gn[i]), 2)))
    return dict(points=int(len(Q)), ridges=int(bad.sum()), worst=worst[:6], gmin=round(gmin, 2))


# ============================================================================================ pads exposed (DR4-01)
def pads_exposed(px=0.2):
    """Each pad's EXPOSED surface vs its drawn section (rev M, judges DR4-01: the rev L body buried the outboard pad's
    slot-side upper corner): the moulding ray-cast from aft over the pad; at every hit inside the drawn pad outline
    (dp < -0.15, away from the groove / bead steps) the hit's height above the grip plane vs grip_surface_z (leather,
    groove, bead as drawn).  {grip: dict(px, area_mm2 of mismatch > 0.05, max |dz|, buried_mm2 (hit > 0.3 above))}."""
    out = {}
    T_ = G.T()
    gw, bead = float(T_["pad_section"][4]), float(T_["pad_section"][3])
    for g, sg in (("out", 1.0), ("in", -1.0)):
        Pd = G.pad_outline(g)
        box = (Pd[:, 0].min() - 2.0, Pd[:, 1].min() - 2.0, Pd[:, 0].max() + 2.0, Pd[:, 1].max() + 2.0)
        if sg < 0:
            box = (-box[2], box[1], -box[0], box[3])
        P, hit, f, d = _depth_patch(box, px, view=1, parts=("black",))
        Q = P[hit] * [sg, 1.0, 1.0]
        z, uf, hf = G._to_plane(Q[:, 0], Q[:, 1], Q[:, 2], g)
        dp = G.field("pad_" + g, Pd)(uf, hf)
        s_ = -dp
        zs = G.grip_surface_z(uf, hf, g)
        m = (dp < -0.15) & (np.abs(s_ - gw) > 0.12) & (np.abs(s_ - gw - 2.0 * bead) > 0.12)
        dz = z[m] - zs[m]
        out[g] = dict(px=int(m.sum()), area_mm2=float((np.abs(dz) > 0.05).sum() * px * px),
                      max_dz=float(np.abs(dz).max()) if m.any() else 0.0,
                      buried_mm2=float((dz > 0.3).sum() * px * px))
    return out


def run_all():
    return G.disk_cached(("acceptance", "v7"), lambda: dict(exactness=exactness(), curve_law=curve_law(), proud=proud(),
                                                           cusps=cusps(), connected=connected(), normals=normals(),
                                                           creases=creases(), ridges=ridges(),
                                                           pads=pads_exposed(), capped=G.capped_fillets()))


def summary_lines(r=None):
    r = r or run_all()
    ex = r["exactness"]
    lines = ["fields: zero level vs the curve-law polylines, max " +
             ", ".join(f"{k} {v['max']:.4f}" for k, v in ex.items()) + " mm"]
    cl = r["curve_law"]
    lines.append("curve law (C2): max relative curvature jump at the interior samples %.1e over %d samples of %d outlines"
                 % (max(v["jump"] for v in cl.values()), sum(v["knots"] for v in cl.values()), len(cl)))
    pr = r["proud"]
    lines.append(f"nothing above the trim face: max {pr['trim_face']:.2f} mm; above the shield facet: max "
                 f"{pr['shield']:.2f} mm")
    cu = dict(r["cusps"])
    gz = cu.pop("_grazing", 0)
    lines.append("untabled cusps (contour turning > %g deg within +-%g mm AND the surface normals turning as much): "
                 % (CUSP_DEG, CUSP_CHORD) +
                 ", ".join(f"{k} {len(v['cusps'])}" + (f" / {v['sections']} sections" if 'sections' in v else "")
                           for k, v in cu.items()) +
                 f" ({gz} contour tips set aside: planes grazing a tabled round, the normals turning less)")
    cn = r["connected"]
    bad = [(h, a, b) for h, a, b in cn if a > 1 or b > 1]
    lines.append(f"black moulding one piece per side in every horizontal section h {cn[0][0]:g}..{cn[-1][0]:g} (step "
                 f"{cn[1][0] - cn[0][0]:g}; none above a head's top): "
                 + ("yes" if not bad else "NO at " + ", ".join(f"h {h:g} ({a} / {b})" for h, a, b in bad)))
    cr = r.get("creases")
    if cr:
        n_un = sum(len(v["creases"]) for v in cr.values())
        worst = sorted([q for v in cr.values() for q in v["creases"]], key=lambda q: -q[3])[:3]
        lines.append(f"CREASES (rev M, judges DR4-02; adaptive scan of {len(cr)} views incl. sides / below: every pixel "
                     f"pair turning > {CREASE_SEED:g} deg refined 2 x {CREASE_SUB}x, a crease when the turn stays in one "
                     f"sub-step): untabled {n_un}" +
                     (" at " + ", ".join(f"({q[0]:.1f}, {q[1]:.1f}, {q[2]:.1f}) {q[3]:.0f} deg" for q in worst)
                      if worst else "") +
                     f"; {sum(v['tabled'] for v in cr.values())} tabled crease pixels set aside, "
                     f"{sum(v['rounds'] for v in cr.values())} candidate pairs resolved as rounds")
    rg = r.get("ridges")
    if rg:
        lines.append("joins read smooth fields at the rounds' own surface points (a ridge = a unit gradient turning "
                     "> %g deg within 0.01 mm; min |grad| in brackets): " % RIDGE_DEG +
                     ", ".join(f"{k} {v['ridges']} / {v['points']} points (|grad| >= {v.get('gmin', 0):.2f})"
                               for k, v in rg.items()))
    pdx = r.get("pads")
    if pdx:
        lines.append("pads EXPOSED as drawn (judges DR4-01; the moulding ray-cast from aft vs the drawn leather / groove "
                     "/ bead heights inside each pad outline): " +
                     ", ".join(f"{g} {v['area_mm2']:.1f} mm2 off by > 0.05 (max {v['max_dz']:.2f}), buried "
                               f"{v['buried_mm2']:.1f} mm2" for g, v in pdx.items()))
    if "capped" in r:
        lines.append("fillets reduced by the 0.45-of-run cap (judges DR4-03): " +
                     ("none" if not r["capped"] else "; ".join(f"{c[0]} at {c[1]} R {c[2]:g} -> {c[3]:.2f}"
                                                               for c in r["capped"])))
    nr = r["normals"]
    lines.append("vertex normals vs analytic (depth-map meshes 0.25 mm from aft, 0.4 from above-aft / the front; 95th / "
                 "99th / max deg; tabled creases, the cover's 0.8 mm top land and part boundaries apart): " +
                 "; ".join(f"{k} {v['p95']:.2f} / {v['p99']:.2f} / {v['max']:.1f} (creases {v['crease_max']:.0f})"
                           for k, v in nr.items()))
    return lines


if __name__ == "__main__":
    import json
    r = run_all()
    for ln in summary_lines(r):
        print(ln)
    print(json.dumps({k: v for k, v in r["cusps"].items()}, indent=0)[:3000])
