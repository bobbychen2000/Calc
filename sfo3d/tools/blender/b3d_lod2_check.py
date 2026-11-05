"""LOD2 against LOD0, per building, on the exported GLBs (integration review round 1, finding 5: phones showed LOD2 at every
distance and no verifier had checked it). The group verifiers (verify_itb / verify_domestic / verify_landside /
tower3d_verify) measure LOD0 against the 2-D sheets; this measures how far each building's LOD2 departs from its own
verified LOD0, so the sheets' tolerances carry over: numpy + shapely, no bpy.

    python3 tools/blender/b3d_lod2_check.py      # -> out/buildings3d/integ/lod2_check.json + a table on stdout

Per unit (tower; ITB hall / BA-A / BA-G; domestic buildings; roadways units; landside buildings), LOD2 triangles from both
the full file and the *_lod2.glb file (the joined LOD2 meshes split per building as tools/blender/b3d_integrate.py does:
review round 2, by containment of all three vertices in the unit's LOD0 / LOD1 footprint + 1 m, no longer the first
footprint holding the centroid):
  plan       footprint areas, the area of LOD2 outside LOD0 + 0.5 m and its farthest point (beyond_m), the LOD0 area LOD2
             misses (- 0.5 m)
  height     top of each (the highest roof cell below), and the roof surface rasterised on a 1-m
             grid inside the LOD0 footprint (- 0.5 m): per cell the highest triangle over its centre, the same cell rule for
             LOD0 and LOD2 (review round 2, finding 6: round 1 sampled vertices and centroids, so a coarse LOD2 roof had
             few samples where LOD0 had many, and its parapet tops read as roof); median / 95th percentile of |LOD2 - LOD0|
             over the cells both cover, the signed median and the share of cells beyond 1.5 m
  parts      named LOD0 parts (node names) with no LOD2 counterpart are listed by the groups' manifests (lod rules); not
             re-derived here
Thresholds (FLAG): beyond_m > 1.0, roof median > 1.5 m, top difference > 2.0 m (the sheets' 0.5 m / 2 % tolerance
widened for a far LOD seen beyond 1.2-1.6 km at desktop and ~0.7-0.9 km on phones; the roof p95 is reported, not flagged:
LOD0-only details - parapets, trusses, lettering, masts - dominate it by design)."""
import json, math, os, sys, time
import numpy as np
import shapely
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
import b3d_integrate as BI  # noqa: E402

LIM = dict(beyond_m=1.0, roof_med_m=1.5, top_m=2.0)
CELL = 1.0       # m, roof grid (review round 2: 1 m as the reviewer's independent grid)


def roof_grid(T, fp, cell=CELL):
    """review round 2 (finding 6): the roof surface rasterised on a CELL grid - per cell centre inside the LOD0 footprint
    fp (less 0.5 m, so the facade line is not a cell), the highest triangle over it (barycentric height) - the SAME cell
    definition for LOD0 and LOD2 (round 1 sampled the vertices and centroids only, so a big LOD2 roof triangle had a few
    samples and a detailed LOD0 roof many, and parapet tops counted as roof)"""
    g = fp.buffer(-0.5)
    if g.is_empty: return {}
    x0, z0, x1, z1 = g.bounds
    xs = np.arange(math.floor(x0 / cell) * cell + cell / 2, x1, cell); zs = np.arange(math.floor(z0 / cell) * cell + cell / 2, z1, cell)
    if not len(xs) or not len(zs): return {}
    X, Z = np.meshgrid(xs, zs); X, Z = X.ravel(), Z.ravel(); m = shapely.contains_xy(g, X, Z); X, Z = X[m], Z[m]
    H = np.full(len(X), -1e9)
    lo, hi = T[:, :, [0, 2]].min(1), T[:, :, [0, 2]].max(1)
    for t, a, b in zip(T, lo, hi):
        sel = np.nonzero((X >= a[0]) & (X <= b[0]) & (Z >= a[1]) & (Z <= b[1]))[0]
        if not len(sel): continue
        p0, p1, p2 = t[0], t[1], t[2]
        v0 = p2[[0, 2]] - p0[[0, 2]]; v1 = p1[[0, 2]] - p0[[0, 2]]; v2 = np.c_[X[sel] - p0[0], Z[sel] - p0[2]]
        d00 = v0 @ v0; d01 = v0 @ v1; d11 = v1 @ v1; den = d00 * d11 - d01 * d01
        if abs(den) < 1e-12: continue
        d20 = v2 @ v0; d21 = v2 @ v1; u = (d11 * d20 - d01 * d21) / den; v = (d00 * d21 - d01 * d20) / den
        ins = (u >= -1e-6) & (v >= -1e-6) & (u + v <= 1 + 1e-6)
        if not ins.any(): continue
        y = p0[1] + u[ins] * (p2[1] - p0[1]) + v[ins] * (p1[1] - p0[1])
        H[sel[ins]] = np.maximum(H[sel[ins]], y)
    ok = H > -1e8
    return dict(zip(zip(np.round(X[ok] / cell).astype(int).tolist(), np.round(Z[ok] / cell).astype(int).tolist()), H[ok].tolist()))


def main():
    t0 = time.time()
    F, TR, files = BI.footprints(lambda s: None)
    rows = []
    for (g, u, l), T in sorted(TR['_lods'].items(), key=lambda kv: kv[0]):
        if l != 2 or u == '*': continue
        T0 = TR['_lods'].get((g, u, 0))
        if T0 is None: continue
        a0, a2 = BI.plan_geom(T0), BI.plan_geom(T)
        out = a2.difference(a0.buffer(0.5)); miss = a0.buffer(-0.5).difference(a2) if not a0.buffer(-0.5).is_empty else a0.buffer(-0.5)
        beyond = 0.0
        if not out.is_empty and out.area > 0.05:
            pts = shapely.get_coordinates(out)
            beyond = float(shapely.distance(a0, shapely.points(pts)).max())
        r0, r2 = roof_grid(T0, a0), roof_grid(T, a0)
        both = [k for k in r2 if k in r0]
        d = np.array([r2[k] - r0[k] for k in both]) if both else np.zeros(1)
        # the top on the same cells (the highest roof cell of each inside the LOD0 footprint): a neighbour's roof triangle
        # reaching over the shared wall (T1 over BA-C) is not this unit's top
        top = float(max(r2.values()) - max(r0.values())) if r0 and r2 else float(T[:, :, 1].max() - T0[:, :, 1].max())
        r = dict(group=g, unit=u, area0_m2=round(a0.area, 1), area2_m2=round(a2.area, 1), outside_m2=round(out.area, 1), beyond_m=round(beyond, 2),
                 missed_m2=round(miss.area, 1), top0=round(float(T0[:, :, 1].max()) - BI.GROUND_Y, 2), top_diff_m=round(top, 2),
                 roof_med_m=round(float(np.median(np.abs(d))), 2), roof_p95_m=round(float(np.percentile(np.abs(d), 95)), 2), roof_signed_med_m=round(float(np.median(d)), 2),
                 roof_over_1_5m_pct=round(100.0 * float((np.abs(d) > 1.5).mean()), 1), cells=len(both), tris0=len(T0), tris2=len(T))
        r['flag'] = [k for k, lim in (('beyond_m', LIM['beyond_m']), ('roof_med_m', LIM['roof_med_m'])) if r[k] > lim] + (['top_m'] if abs(top) > LIM['top_m'] else [])
        rows.append(r)
    os.makedirs(os.path.join(BI.OUTD), exist_ok=True)
    out = dict(about='LOD2 vs LOD0 per building (tools/blender/b3d_lod2_check.py)', generated=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), limits=LIM, files=files, units=rows,
               flagged=[f"{r['group']}/{r['unit']}: {', '.join(r['flag'])}" for r in rows if r['flag']])
    json.dump(out, open(os.path.join(BI.OUTD, 'lod2_check.json'), 'w'), indent=1)
    print('%-9s %-28s %9s %9s %8s %7s %8s %6s %7s %7s  %s' % ('group', 'unit', 'area0', 'area2', 'outside', 'beyond', 'missed', 'top', 'roofMed', 'roofP95', 'flag'))
    for r in rows:
        print('%-9s %-28s %9.0f %9.0f %8.1f %7.2f %8.1f %6.2f %7.2f %7.2f  %s' % (r['group'], r['unit'][:28], r['area0_m2'], r['area2_m2'], r['outside_m2'], r['beyond_m'], r['missed_m2'], r['top_diff_m'], r['roof_med_m'], r['roof_p95_m'], ','.join(r['flag'])))
    print('%d units, %d flagged, %.0f s' % (len(rows), len(out['flagged']), time.time() - t0))
    return 0


if __name__ == '__main__':
    sys.exit(main())
