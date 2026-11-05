"""LOD2 against LOD0, per building, on the exported GLBs (integration review round 1, finding 5: phones showed LOD2 at every
distance and no verifier had checked it). The group verifiers (verify_itb / verify_domestic / verify_landside /
tower3d_verify) measure LOD0 against the 2-D sheets; this measures how far each building's LOD2 departs from its own
verified LOD0, so the sheets' tolerances carry over: numpy + shapely, no bpy.

    python3 tools/blender/b3d_lod2_check.py      # -> out/buildings3d/integ/lod2_check.json + a table on stdout

Per unit (tower; ITB hall / BA-A / BA-G; domestic buildings; roadways units; landside buildings), LOD2 triangles from both
the full file and the *_lod2.glb file (the joined LOD2 meshes split per building as tools/blender/b3d_integrate.py does):
  plan       footprint areas, the area of LOD2 outside LOD0 + 0.5 m and its farthest point (beyond_m), the LOD0 area LOD2
             misses (- 0.5 m)
  height     top of each (max y), and the roof surface on a 2-m grid: per cell the highest triangle point, median and 95th
             percentile |LOD2 - LOD0| over the cells both cover
  parts      named LOD0 parts (node names) with no LOD2 counterpart are listed by the groups' manifests (lod rules); not
             re-derived here
Thresholds (FLAG): beyond_m > 1.0, roof median > 1.5 m, top difference > 2.0 m (the sheets' 0.5 m / 2 % tolerance
widened for a far LOD seen beyond 1.2-1.6 km at desktop and ~0.7-0.9 km on phones; the roof p95 is reported, not flagged:
LOD0-only details - parapets, trusses, lettering, masts - dominate it by design)."""
import json, os, sys, time
import numpy as np
import shapely
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
import b3d_integrate as BI  # noqa: E402

LIM = dict(beyond_m=1.0, roof_med_m=1.5, top_m=2.0)


def roof_grid(T, cell=2.0):
    """highest point per 2-m plan cell, sampled at the triangle vertices and centroids (dense enough for these meshes)"""
    P = np.concatenate([T.reshape(-1, 3), T.mean(1)])
    k = np.floor(P[:, [0, 2]] / cell).astype(np.int64)
    key = k[:, 0] * 1000003 + k[:, 1]
    o = np.argsort(key); key, y = key[o], P[o, 1]
    u, i0 = np.unique(key, return_index=True)
    return dict(zip(u.tolist(), np.maximum.reduceat(y, i0).tolist()))


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
        r0, r2 = roof_grid(T0), roof_grid(T)
        both = [k for k in r2 if k in r0]
        d = np.abs(np.array([r2[k] - r0[k] for k in both])) if both else np.zeros(1)
        top = float(T[:, :, 1].max() - T0[:, :, 1].max())
        r = dict(group=g, unit=u, area0_m2=round(a0.area, 1), area2_m2=round(a2.area, 1), outside_m2=round(out.area, 1), beyond_m=round(beyond, 2),
                 missed_m2=round(miss.area, 1), top0=round(float(T0[:, :, 1].max()) - BI.GROUND_Y, 2), top_diff_m=round(top, 2),
                 roof_med_m=round(float(np.median(d)), 2), roof_p95_m=round(float(np.percentile(d, 95)), 2), cells=len(both), tris0=len(T0), tris2=len(T))
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
