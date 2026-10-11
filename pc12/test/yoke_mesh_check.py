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
     exact normal there (yoke_mesh.highlight_report) over the faces seen from the aft hemisphere (yoke_patch.vis_tol_k:
     z-buffered visibility classes, rev N);
  6. what cad.res's interior refinement adds at build (PN bow / turn criterion; counted in 1): nothing on the cover (a
     fixed point, yoke3d.res_fixed_point), <= 1 % on the moulding;
  7. folds: no face wound against its own corner normals or the solid's gradient (rev N).
  8. the pilot yoke's legends in reading order (rev N): built as the co-pilot's mirror image, its printed words must
     still read in the table's order (yoke3d.reading_blocks / side_pieces).
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
    info("cad.res's interior refinement at build (counted in the GLB part above)", ", ".join(
        f"{n}/{m} +{v}" for (n, m), v in grow.items()) or "nothing")
    # rev N (judges CR1-04: rev M demoted this row to [info] while it failed): the cover a fixed point (its splits made
    # in the mesher, on the solid: yoke3d.res_fixed_point), the moulding within 1 % of its triangles
    g_cov = sum(v for (n, m), v in grow.items() if n == "cover")
    g_mou = sum(v for (n, m), v in grow.items() if n == "moulding")
    n_mou = sum(a for (n, m), (a, b) in rows.items() if n == "moulding")
    report("cad.res adds nothing to the cover (a fixed point of the interior turn / bow criterion: the mesher splits "
           "there, on the solid) and <= 1 % to the moulding", g_cov == 0 and g_mou <= 0.01 * n_mou,
           f"cover +{g_cov}, moulding +{g_mou} on {n_mou}")
    # 2 ------------------------------------------------------------------------------------------------ watertight
    bad, same_way = [], 0
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
        same_way += int((d > 1).sum())
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
    # rev O: and no edge traversed twice the same way inside a material (a doubled / flipped face: one isolated micro-
    # triangle had been doubled at the inboard web; yoke3d._debris_keep)
    report("watertight: every piece group welded by position closes with the others (each edge twice), no same-way "
           "edge inside a material", int((cnt == 1).sum()) == 0 and same_way == 0,
           f"{int((cnt == 1).sum())} open edges, {int((cnt > 2).sum())} shared by > 2 faces over {len(Fw)} faces, "
           f"{same_way} same-way" + (f"; per material: {'; '.join(bad)}" if bad else ""))
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
    # 3b ----------------------------------------------------------------------------------------------- folds
    # rev N (judges CR1-05): no face wound against one of its own corner normals (a fold: a pinhole under FrontSide
    # culling), and on the cover / moulding none against the solid's gradient at its centroid (outside the switches: the
    # cover's face runs on under the TCS bezel over its seat pocket, whose wall sets the gradient there)
    nfold, where = 0, []
    for p in ps:
        b = Y.fold_faces(p)
        if p.name in ("cover", "moulding") and len(p.F):
            fn_ = G.cover if p.name == "cover" else G.moulding
            P = p.V[p.F]
            C = P.mean(1)
            fnr = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
            ar = np.linalg.norm(fnr, axis=1)
            near = (ar > 1e-12) & (np.abs(fn_(*C.T)) < 0.05)
            near[near] &= G.part_sdf("switches", *C[near].T) > 0.05       # not under a switch (the TCS seat pocket)
            g = _grad(fn_, C[near])
            gn = np.linalg.norm(g, axis=1)
            opp = np.zeros(len(p.F), bool)
            opp[np.nonzero(near)[0]] = (np.sum(fnr[near] * g, 1) <= 0) & (gn > 0.3)
            b = np.union1d(b, np.nonzero(opp)[0])
        if len(b):
            nfold += len(b)
            c = p.V[p.F[b[0]]].mean(0)
            where.append(f"{p.name}/{p.mat} {len(b)} (e.g. u {c[0]:.1f} h {c[1]:.1f} a {c[2]:.1f})")
    report("no folded faces: face normal . each corner normal > 0, and . the solid's gradient > 0 on the cover / "
           "moulding", nfold == 0, f"{nfold}" + (": " + "; ".join(where) if where else ""))
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
    _, vcls = YP.visibility()
    info("visibility classes of the dense moulding (rev N, judges CR1-03: z-buffered from "
         f"{len(YP.VIS_AFT)} aft-hemisphere / {len(YP.VIS_FWD)} forward cameras, not rev M's 'under the cover' proxy)",
         "seen from aft {}, only from forward {}, never {} vertices".format(*np.bincount(vcls, minlength=3)))
    hr = YM.highlight_report("msmooth", frame.V, frame.F, frame.N, tol_k=YP.vis_tol_k)
    report(f"frame highlights (faces seen from the aft hemisphere): corner normals interpolated vs exact at edge "
           f"midpoints / centroids, 95th percentile (area) <= {YP.FRAME_TOL:g} deg (FRAME_TOL)", hr["p95"] <= YP.FRAME_TOL,
           f"p50 {hr['p50']:.2f}, p95 {hr['p95']:.2f} deg; area > 2 deg {hr['over2']:.1f} %, > 4 deg {hr['over4']:.1f} % "
           f"({hr['faces']} faces; rev M at 3.5 deg / the proxy: p50 0.86, p95 2.97, 16 % / 1.2 %; the first "
           f"QEM-decimated mesh: p50 1.40, p95 8.0, 43 % / 29 %)")
    # rev O (3-D judges r2 CR2-01): the small rounds alone, and per face (not by area) -- the area-weighted row averages
    # the R 0.8 - 4 rounds of the heads' necks away; a face is on a round where its corner normals turn faster than
    # 1 / CURV_R0 per mm along its edges
    Fr = frame.F
    turn = np.zeros(len(Fr))
    for a_, b_ in ((0, 1), (1, 2), (2, 0)):
        na, nb = frame.N[Fr[:, a_]], frame.N[Fr[:, b_]]
        ang = np.arccos(np.clip(np.sum(na * nb, 1), -1.0, 1.0))
        turn = np.maximum(turn, ang / np.maximum(np.linalg.norm(frame.V[Fr[:, a_]] - frame.V[Fr[:, b_]], axis=1), 1e-3))
    rnd = turn * YP.CURV_R0 > 1.0
    hr3 = YM.highlight_report("msmooth", frame.V, frame.F, frame.N, tol_k=YP.vis_tol_k, face_mask=rnd)
    Cf = frame.V[Fr].mean(1)
    hd = (np.abs(Cf[:, 0]) > YP.HEADS_BOX[0]) & (Cf[:, 1] > YP.HEADS_BOX[1])
    hr5 = YM.highlight_report("msmooth", frame.V, frame.F, frame.N, tol_k=YP.vis_tol_k, face_mask=hd)
    report(f"frame highlights on the HEADS and their necks (|u| > {YP.HEADS_BOX[0]:g}, h > {YP.HEADS_BOX[1]:g}: no "
           f"curvature relaxation, rev O judges CR2-01), 95th percentile PER FACE <= 2 x FRAME_TOL", hr5["fp95"] <= 2.0 *
           YP.FRAME_TOL, f"per face p95 {hr5['fp95']:.2f} deg, > 4 deg {hr5['fover4']:.1f} % of {hr5['faces']} faces; "
                         f"by area p95 {hr5['p95']:.2f}, > 4 deg {hr5['over4']:.2f} %")
    info(f"frame highlights on every visible ROUND (faces turning > 1 / {YP.CURV_R0:g} mm; the relaxation capped at "
         f"{YP.CURV_KMAX_VIS:g} x there)", f"by area p95 {hr3['p95']:.2f} deg, > 4 deg {hr3['over4']:.2f} %; per face p95 "
         f"{hr3['fp95']:.2f}, > 4 deg {hr3['fover4']:.1f} % of {hr3['faces']} faces; all visible faces per face: p95 "
         f"{hr['fp95']:.2f}, > 4 deg {hr['fover4']:.1f} %")
    # rev O (3-D judges r2 CR2-02): the gloss-black lunes of the trim face (outside its ring groove and slot), the
    # glossiest black on the yoke -- refined to the cover's 1 deg (yoke_patch.TRIM_INTERP)
    lun = [q for q in ps if q.name == "moulding" and q.mat == "gloss_black"]
    if lun:
        q = lun[0]
        c_, n_ = G.head_out_face()
        eu_, ev_ = G._facet_frame(c_, n_)
        C_ = q.V[q.F].mean(1) - c_
        rr = np.hypot(C_ @ eu_, C_ @ ev_)
        R0 = 0.5 * float(G.T()["trim"][2])
        w_ = float(G.T()["trim_grooves"][0])
        yl_ = G.trim_slot_dims()[0]
        keep = (np.abs(rr - R0) > 0.5 * w_ + 0.1) & (np.abs(C_ @ ev_) > yl_ + 0.1)
        hr4 = YM.highlight_report("msmooth", q.V, q.F, q.N, face_mask=keep)
        report("trim-face lunes (gloss black, outside the ring groove / slot): interpolated vs exact normal, 95th "
               "percentile by area <= 1 deg and > 4 deg on <= 1 % of the area (rev N: 5 % of their pixels > 4 deg)",
               hr4["p95"] <= 1.0 and hr4["over4"] <= 1.0,
               f"per face p95 {hr4['fp95']:.2f}, > 4 deg {hr4['fover4']:.1f} %; by area p95 {hr4['p95']:.2f} deg, "
               f"> 4 deg {hr4['over4']:.1f} % ({hr4['faces']} of {len(q.F)} faces)")
    hr2 = YM.highlight_report("msmooth", frame.V, frame.F, frame.N, tol_k=YP.frame_tol_k)
    info("the same over rev M's proxy class (for comparison)", f"p50 {hr2['p50']:.2f}, p95 {hr2['p95']:.2f} deg; "
         f"> 2 deg {hr2['over2']:.1f} %, > 4 deg {hr2['over4']:.1f} % ({hr2['faces']} faces)")
    # 8 ------------------------------------------------------------------------------------------------ legends
    import math
    bad, rows8 = [], []
    for k, (_, _, words) in enumerate(G.T()["legends"]):
        if len(words) < 2:
            continue
        wid = np.repeat(np.arange(len(words)), [int(w[2]) for w in words])
        for side, blk, sg in (("co-pilot", G.legend_blocks(k), 1), ("pilot", Y.reading_blocks(k), -1)):
            aw = np.array([math.degrees(math.atan2(P0[1], P0[0])) for P0, _, _ in blk])
            aw = aw if sg > 0 else 180.0 - aw                                   # front view (world): the pilot mirrored
            c = math.degrees(math.atan2(np.sin(np.radians(aw)).sum(), np.cos(np.radians(aw)).sum()))
            rel = (aw - c + 180.0) % 360.0 - 180.0
            cw = 0.0 < c % 360.0 < 180.0                                       # upper arc: read clockwise
            order = wid[np.argsort(-rel if cw else rel)]
            if np.any(np.diff(order) < 0):
                bad.append(f"{side} row {k}")
        rows8.append(k)
    pl = Y.side_pieces(-1, ps)
    swapped = sum(p is Y.pilot_legends() for p in pl) == 1 and all(p.name != "legends" or p is Y.pilot_legends()
                                                                   for p in pl)
    report("the pilot yoke's legends read in the table's word order (built mirrored, each block reflected about its "
           "row's centre first: yoke3d.reading_blocks / side_pieces); the co-pilot's likewise", not bad and swapped,
           f"rows {rows8} in order on both yokes" if not bad and swapped else
           ("out of order: " + ", ".join(bad) if bad else "the pilot's pieces do not carry pilot_legends"))
    YM.close_pool()
    print(f"YOKE MESH {'OK' if not fails else 'FAIL'}" + (f" ({len(fails)}): " + "; ".join(fails) if fails else "")
          + f"  ({time.time() - t0:.0f} s)")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
