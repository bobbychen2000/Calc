"""
Mesh quality of the Stage-3 yoke (model/yoke3d.py, rev M; yoke-local mm, the co-pilot sense -- the pilot's is its mirror):

  1. triangles per piece and the yoke as built in the GLB (cad.res's interior refinement + the column) against
     build.YOKE_BUDGET;
  2. watertight: every material group's welded surface (by position, 1e-4 mm) closed -- each edge used twice, once each
     way (the part merges a material's pieces; fit_check 23 tests the same on the built part);
  3. slivers: triangles with a corner under 5 deg, per piece (reported with their places);
  4. vertex normals vs the analytic ones: the cover / moulding solids' gradients (yoke_geom.cover / moulding) sampled
     0.03 mm inside each face from each corner (so a crease vertex is compared with its own side), 95th percentile
     per group (<= 2 deg wanted);
  5. HIGHLIGHTS: the frame's corner normals interpolated (then normalised) at its edge midpoints / centroids against the
     exact normal there (yoke_mesh.highlight_report, the faces any crew / cabin camera sees); the cover terrain the same
     against its pieces' normals (yoke_cover.terrain_interp_error);
  6. what cad.res's interior refinement adds at build (PN bow / turn criterion; counted in 1).
Prints one row per check and 'YOKE MESH OK' / 'YOKE MESH FAIL'.  ~3-5 min (the cached pieces; the highlight report
projects ~60k points).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from model import yoke3d as Y          # noqa: E402
from model import yoke_geom as G       # noqa: E402
from model import yoke_mesh as YM      # noqa: E402
from model import yoke_patch as YP     # noqa: E402

fails = []


def report(name, ok, detail=""):
    print(f"  [{'ok' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""), flush=True)
    if not ok:
        fails.append(name)


def info(name, detail):
    print(f"  [info] {name}: {detail}", flush=True)


def _grad(fn, P, e=0.002):
    g = np.zeros_like(P)
    for k in range(3):
        d = np.zeros(3)
        d[k] = e
        g[:, k] = (fn(*(P + d).T) - fn(*(P - d).T)) / (2 * e)
    return g


def main():
    t0 = time.time()
    ps = Y.yoke_pieces()
    from model import build as B
    from cad import res
    from cad.refine import refine
    # 1 ------------------------------------------------------------------------------------------------ triangles
    n_mesh = sum(len(p.F) for p in ps)
    with res.override(2.0):
        placed = Y.place(1, ps)
        refined = refine([m for m, _ in placed], **res._kw("interior"))
        from cad.mesh import cylinder
        from model import interior as I
        col = len(cylinder([0, 0, 0], [0.15, 0, 0], float(I.YOKE["column_r"]), n=32).F)
    n_glb = sum(len(m.F) for m in refined) + col
    rows = {}
    for p, m in zip(ps, refined):
        k = (p.name, p.mat)
        a, b = rows.get(k, (0, 0))
        rows[k] = (a + len(p.F), b + len(m.F))
    info("pieces (meshed -> after cad.res)", ", ".join(f"{n}/{m} {a}" + (f"->{b}" if b != a else "")
                                                       for (n, m), (a, b) in rows.items()))
    report(f"triangles: {n_mesh} meshed, {n_glb} in the GLB part (cad.res's interior refinement + the column {col}) "
           f"<= build.YOKE_BUDGET", n_glb <= B.YOKE_BUDGET, f"{n_glb} / {B.YOKE_BUDGET}")
    # 6 ------------------------------------------------------------------------------------------------ cad.res fixed point
    grow = {k: b - a for k, (a, b) in rows.items() if b != a}
    info("cad.res's interior refinement at build (counted in the GLB part above; it splits the cover strip's and the "
         "rounded extrusions' quad diagonals that turn past 20 deg)", ", ".join(f"{n}/{m} +{v}" for (n, m), v in
                                                                                grow.items()) or "nothing")
    # 2 ------------------------------------------------------------------------------------------------ watertight
    bad = []
    for mat in sorted({p.mat for p in ps}):
        grp = [p for p in ps if p.mat == mat]
        V = np.vstack([p.V for p in grp])
        off = np.cumsum([0] + [len(p.V) for p in grp])
        F = np.vstack([p.F + o for p, o in zip(grp, off)])
        _, w = np.unique(np.round(V * 1e4).astype(np.int64), axis=0, return_inverse=True)
        Fw = w.ravel()[F]
        Fw = Fw[(Fw[:, 0] != Fw[:, 1]) & (Fw[:, 1] != Fw[:, 2]) & (Fw[:, 0] != Fw[:, 2])]
        e = np.vstack([Fw[:, [0, 1]], Fw[:, [1, 2]], Fw[:, [2, 0]]])
        key = np.sort(e, 1)
        _, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True)
        d = np.unique(e, axis=0, return_counts=True)[1]
        if (cnt != 2).any() or (d > 1).any():
            bad.append(f"{mat}: {int((cnt == 1).sum())} open, {int((cnt > 2).sum())} non-manifold, "
                       f"{int((d > 1).sum())} same-way edges")
    # the material groups meet one another along seams (cover / inserts / badge, frame / pads, switch seats): the yoke
    # as a whole is the closed surface
    V = np.vstack([p.V for p in ps])
    off = np.cumsum([0] + [len(p.V) for p in ps])
    F = np.vstack([p.F + o for p, o in zip(ps, off)])
    _, w = np.unique(np.round(V * 1e4).astype(np.int64), axis=0, return_inverse=True)
    Fw = w.ravel()[F]
    Fw = Fw[(Fw[:, 0] != Fw[:, 1]) & (Fw[:, 1] != Fw[:, 2]) & (Fw[:, 0] != Fw[:, 2])]
    key = np.sort(np.vstack([Fw[:, [0, 1]], Fw[:, [1, 2]], Fw[:, [2, 0]]]), 1)
    cnt = np.unique(key, axis=0, return_counts=True)[1]
    report("watertight: every piece group welded by position closes with the others (each edge twice)",
           int((cnt == 1).sum()) == 0, f"{int((cnt == 1).sum())} open edges, {int((cnt > 2).sum())} shared by > 2 "
                                      f"faces over {len(Fw)} faces" + (f"; per material: {'; '.join(bad)}" if bad
                                                                       else ""))
    # 3 ------------------------------------------------------------------------------------------------ slivers
    sl = []
    for p in ps:
        a = YM._min_angles_deg(p.V, p.F)
        b = np.nonzero(a < 5.0)[0]
        if len(b):
            c = p.V[p.F[b]].mean(1)
            sl.append(f"{p.name}/{p.mat} {len(b)} (min {a.min():.1f} deg, e.g. u {c[0, 0]:.1f} h {c[0, 1]:.1f} "
                      f"a {c[0, 2]:.1f})")
    nsl = sum(int((YM._min_angles_deg(p.V, p.F) < 5.0).sum()) for p in ps)
    info("sliver triangles (a corner < 5 deg)", f"{nsl}" + (": " + "; ".join(sl) if sl else ""))
    # 4 ------------------------------------------------------------------------------------------------ vertex normals
    per = {}
    for p in ps:
        if p.name not in ("cover", "moulding") or len(p.F) < 60:
            continue
        fn = G.cover if p.name == "cover" else G.moulding
        P = p.V[p.F]
        C = P.mean(1)
        d = C[:, None] - P
        dl = np.linalg.norm(d, axis=2, keepdims=True)
        Q = (P + d / np.maximum(dl, 1e-9) * np.minimum(0.03, 0.5 * dl)).reshape(-1, 3)
        g = _grad(fn, Q)
        gn = np.linalg.norm(g, axis=1)
        ok = (gn > 0.3) & (np.abs(fn(*Q.T)) < 0.05)
        Nc = p.N[p.F].reshape(-1, 3)
        ang = np.degrees(np.arccos(np.clip(np.sum(Nc[ok] * g[ok] / gn[ok, None], 1), -1, 1)))
        per.setdefault(p.name, []).append(ang)
    for k, v in per.items():
        a = np.concatenate(v)
        report(f"{k}: corner normals vs the solid's gradient (0.03 mm inside each face), 95th percentile <= 2 deg",
               float(np.percentile(a, 95)) <= 2.0, f"p50 {np.percentile(a, 50):.2f}, p95 {np.percentile(a, 95):.2f}, "
                                                   f"p99 {np.percentile(a, 99):.2f} deg over {len(a)} corners")
    # 5 ------------------------------------------------------------------------------------------------ highlights
    frame = max((p for p in ps if p.name == "moulding" and p.mat == "grip_black"), key=lambda p: len(p.F))
    hr = YM.highlight_report("msmooth", frame.V, frame.F, frame.N, tol_k=YP.frame_tol_k)
    report(f"frame highlights (visible faces): corner normals interpolated vs exact at edge midpoints / centroids, "
           f"95th percentile (area) <= {YP.FRAME_TOL:g} deg (FRAME_TOL)", hr["p95"] <= YP.FRAME_TOL,
           f"p50 {hr['p50']:.2f}, p95 {hr['p95']:.2f} deg; area > 2 deg {hr['over2']:.1f} %, > 4 deg {hr['over4']:.1f} % "
           f"({hr['faces']} faces; the first QEM-decimated mesh: p50 1.40, p95 8.0, 43 % / 29 %)")
    YM.close_pool()
    print(f"YOKE MESH {'OK' if not fails else 'FAIL'}" + (f" ({len(fails)}): " + "; ".join(fails) if fails else "")
          + f"  ({time.time() - t0:.0f} s)")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
