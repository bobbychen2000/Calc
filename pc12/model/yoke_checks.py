"""
Acceptance checks of the yoke solids (model/yoke_geom.py, YOKE_DESIGN rev K) -- printed by sheets L6Y / L6Y2 and
summarised on L6Y2 (judges r2 DR2-01..04):

  exactness   the 2-D fields' zero level against the curve-law polylines (shell, grips, pads, body, shield): the
              zero crossings along rows / columns vs the dense outline, max mm, and the crossing direction noise
  proud       nothing of the moulding stands above the outboard head's round trim face or the inboard shield facet
              inside their outlines (max height, mm; the switches that sit on them excluded)
  cusps       exact sections of the grips (every 2.5 mm of the axis, normal to it) and of the body / cover at the
              centreline and across the arm: contour corners turning more than CUSP_DEG over a 0.6 mm chord that are
              not a tabled crease (the pad pocket's step, groove and bead; the cover's parting grooves / step V)
  normals     a 0.25 mm depth-map mesh of the cover and the grips seen from aft (patches): the facet-averaged vertex
              normals against the solids' analytic normals (the distance fields' gradient) away from silhouettes and
              tabled creases -- the Stage-3 acceptance metric (vertex normals within 2 deg at the 95th percentile)

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


def cusps():
    """Untabled sharp corners in the grip sections (every 2.5 mm, normal to the axis) and the body / cover sections
    at the centreline (Z-Z) and across the arm (K-K): {name: [(h or label, turn deg, (x, y))]}."""
    T = G.T()
    out = {}
    for g in ("out", "in"):
        pg = "grip_" + g
        Q = G.grip_outline(g)
        hz = float(T["head_out"][7] if g == "out" else T["head_in"][5])
        bad = []
        n_sec = 0
        ext = (-42.0, -48.0, 36.0, 10.0)
        for h in np.arange(Q[:, 1].min() + 2.5, hz - 4.5, 2.5):        # below the heads' transition zone
            p, e1, e2 = G.grip_section_frame(g, h)
            S = G.grip_section(g, h, extent=ext, parts=(pg,), step=0.1)
            for C in S.get(pg, []):
                if len(C) < 20:
                    continue
                n_sec += 1
                tn = _turns(C)
                k = np.where(tn > CUSP_DEG)[0]
                k = k[np.minimum.reduce([C[k, 0] - ext[0], ext[2] - C[k, 0], C[k, 1] - ext[1], ext[3] - C[k, 1]]) > 0.6]
                if not len(k):
                    continue
                # 3-D points -> plane coordinates: tabled creases = within 0.8 mm (in the plane) of the pad outline
                X = p[None, :] + C[k, :1] * e1[None, :] + C[k, 1:2] * e2[None, :]
                z, uf, hf = G._to_plane(X[:, 0], X[:, 1], X[:, 2], g)
                dp = G.field("pad_" + g, G.pad_outline(g))(uf, hf)
                gw, bead = float(T["pad_section"][4]), float(T["pad_section"][3])
                tabled = (dp > -(gw + 2 * bead) - 0.8) & (dp < 0.8)
                for j, kk in enumerate(k):
                    if not tabled[j]:
                        bad.append((round(float(h), 1), round(float(tn[kk]), 1), tuple(np.round(C[kk], 2))))
        out[pg] = dict(sections=n_sec, cusps=bad)
    # Z-Z (u = 0) and K-K (across the outboard arm at (52, 45), 30 deg up outboard)
    for nm, pt, e1, e2, ext in (("Z-Z", (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0, 0.0), (-76.0, -66.0, 12.0, 70.0)),
                                ("K-K", (52.0, 45.0, 0.0), (0.0, 0.0, 1.0),
                                 (-math.sin(math.radians(30.0)), math.cos(math.radians(30.0)), 0.0),
                                 (-80.0, -26.0, 10.0, 26.0))):
        S = G.section(pt, e1, e2, ext, parts=("black", "cover"), step=0.1)
        bad = []
        for part, Cs in S.items():
            for C in Cs:
                if len(C) < 20:
                    continue
                tn = _turns(C)
                for kk in np.where(tn > CUSP_DEG)[0]:
                    if min(C[kk, 0] - ext[0], ext[2] - C[kk, 0], C[kk, 1] - ext[1], ext[3] - C[kk, 1]) < 0.6:
                        continue                                       # the cut's own boundary
                    X = np.asarray(pt) + C[kk, 0] * np.asarray(e1) + C[kk, 1] * np.asarray(e2)
                    if part == "cover" and _cover_tabled(X):
                        continue
                    if part == "black" and _black_tabled(X):
                        continue
                    bad.append((part, round(float(tn[kk]), 1), tuple(np.round(C[kk], 2))))
        out[nm] = dict(cusps=bad)
    return out


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
PATCHES = {"cover stem / inserts": (-20.0, -50.0, 20.0, 10.0), "cover arm + TCS": (36.0, 24.0, 70.0, 62.0),
           "outboard grip pad / frame": (102.0, -40.0, 142.0, 40.0),
           "inboard grip pad / frame": (-144.0, -46.0, -96.0, 34.0)}


def _depth_patch(box, px=0.25, parts=("black", "cover")):
    u = np.arange(box[0], box[2], px)
    h = np.arange(box[1], box[3], px)
    UU, HH = np.meshgrid(u, h)
    f = lambda U, H_, A: np.minimum.reduce([G.part_sdf(p, U, H_, A) for p in parts])  # noqa: E731
    A = np.full(UU.shape, 30.0)
    alive = np.ones(UU.shape, bool)
    hit = np.zeros(UU.shape, bool)
    for _ in range(400):
        if not alive.any():
            break
        v = f(UU[alive], HH[alive], A[alive])
        st = np.maximum(0.8 * v, 0.02)
        idx = np.where(alive)
        done = v < 0.02
        hit[idx[0][done], idx[1][done]] = True
        A[idx[0][~done], idx[1][~done]] -= st[~done]
        alive[idx] = ~done & (A[idx] > -90.0)
    # refine by bisection along a in [A - 0.1, A + 0.1]
    lo, hi = A - 0.12, A + 0.12
    for _ in range(18):
        mid = 0.5 * (lo + hi)
        v = np.where(hit, f(UU, HH, mid), 1.0)
        inside = v < 0
        lo = np.where(hit & inside, mid, lo)
        hi = np.where(hit & ~inside, mid, hi)
    return UU, HH, np.where(hit, 0.5 * (lo + hi), np.nan), f


def normals(px=0.25):
    out = {}
    for nm, box in PATCHES.items():
        UU, HH, A, f = _depth_patch(box, px)
        hit = ~np.isnan(A)
        P = np.stack([UU, HH, A], -1)
        e = 0.01
        Pf = P[hit]
        gx = f(Pf[:, 0] + e, Pf[:, 1], Pf[:, 2]) - f(Pf[:, 0] - e, Pf[:, 1], Pf[:, 2])
        gy = f(Pf[:, 0], Pf[:, 1] + e, Pf[:, 2]) - f(Pf[:, 0], Pf[:, 1] - e, Pf[:, 2])
        gz = f(Pf[:, 0], Pf[:, 1], Pf[:, 2] + e) - f(Pf[:, 0], Pf[:, 1], Pf[:, 2] - e)
        na = np.full(P.shape, np.nan)
        na[hit] = np.c_[gx, gy, gz] / np.linalg.norm(np.c_[gx, gy, gz], axis=1)[:, None]
        # facet normals of the depth-map mesh, averaged per vertex (4 triangles)
        nm_ = np.zeros(P.shape)
        for (di, dj), (dk, dl) in (((0, 1), (1, 0)), ((1, 0), (0, -1)), ((0, -1), (-1, 0)), ((-1, 0), (0, 1))):
            a = np.roll(P, (-di, -dj), (0, 1)) - P
            b = np.roll(P, (-dk, -dl), (0, 1)) - P
            c = np.cross(b, a)
            nm_ += np.nan_to_num(c)
        nm_ /= np.maximum(np.linalg.norm(nm_, axis=-1, keepdims=True), 1e-12)
        nm_ *= np.sign(np.sum(nm_ * np.nan_to_num(na), axis=-1, keepdims=True) + 1e-12)
        dev = np.degrees(np.arccos(np.clip(np.sum(nm_ * na, -1), -1, 1)))
        # exclusions: borders, silhouettes / occlusions (depth jumps), grazing faces, creases (analytic normals of
        # neighbours more than 25 deg apart: the tabled grooves, steps, frame edges)
        ok = hit.copy()
        ok[:2, :] = ok[-2:, :] = ok[:, :2] = ok[:, -2:] = False
        Af = np.nan_to_num(A, nan=-500.0)
        for s in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            nb = np.roll(Af, s, (0, 1))
            ok &= np.abs(nb - Af) < 3.0 * px
            nn = np.roll(np.nan_to_num(na), s, (0, 1))
            ok &= np.sum(nn * np.nan_to_num(na), -1) > math.cos(math.radians(25.0))
        ok &= np.abs(np.nan_to_num(na)[..., 2]) > math.cos(math.radians(70.0))
        d = dev[ok]
        crease = hit & ~ok
        out[nm] = dict(n=int(ok.sum()), p50=float(np.percentile(d, 50)), p95=float(np.percentile(d, 95)),
                       p99=float(np.percentile(d, 99)), max=float(d.max()), excluded=float(crease.sum() / hit.sum()))
    return out


def run_all():
    return G.disk_cached(("acceptance", "v2"), lambda: dict(exactness=exactness(), proud=proud(), cusps=cusps(),
                                                           normals=normals()))


def summary_lines(r=None):
    r = r or run_all()
    ex = r["exactness"]
    lines = ["fields: zero level vs the curve-law polylines, max " +
             ", ".join(f"{k} {v['max']:.4f}" for k, v in ex.items()) + " mm"]
    pr = r["proud"]
    lines.append(f"nothing above the trim face: max {pr['trim_face']:.2f} mm; above the shield facet: max "
                 f"{pr['shield']:.2f} mm")
    cu = r["cusps"]
    lines.append("untabled cusps (> %g deg within +-%g mm): " % (CUSP_DEG, CUSP_CHORD) +
                 ", ".join(f"{k} {len(v['cusps'])}" + (f" / {v['sections']} sections" if 'sections' in v else "")
                           for k, v in cu.items()))
    nr = r["normals"]
    lines.append("vertex normals vs analytic (0.25 mm depth-map mesh, 95th / 99th / max deg): " +
                 "; ".join(f"{k} {v['p95']:.2f} / {v['p99']:.2f} / {v['max']:.1f}" for k, v in nr.items()))
    return lines


if __name__ == "__main__":
    import json
    r = run_all()
    for ln in summary_lines(r):
        print(ln)
    print(json.dumps({k: v for k, v in r["cusps"].items()}, indent=0)[:3000])
