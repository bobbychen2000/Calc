"""Review round 1 probes of the domestic asset, re-run on the exported files (no bpy): the reviewer's physics measurements
(out/buildings3d/review_r1_physics: brclash.py, bridgegap2.py, hmap.py) re-implemented on the glb itself.

    python3 tools/blender/verify_domestic_r1.py [full.glb] [lod2.glb]    -> out/buildings3d/domestic_verify_r1.json (+ table)

  walkway gaps      for every B-F bridge of the app's gate system (out/buildings3d/integ/draw/scene2d.json, pose 'current': the
                    walkway hull the app draws): plan distance from the walkway hull to the area the asset occupies at 6.0 and 7.5 m
                    above the apron (mesh section, closed rings filled; the larger of the two; 0 = the walkway meets / enters the
                    building or runs inside a part), per LOD (0 = LOD0 shells +
                    PV, without fins / frames; 2 = domestic_lod2.glb)
  walkway clash     plan overlap of the walkway / rotunda (cyl) hulls with asset triangles inside their height band (+-0.05 m),
                    per LOD: what the brclash.py probe reported (B10 5.65 m2 floor at 6.0 m, D6 / D7 eave and drum overlaps, C4)
  LOD2 vs LOD0      top-height rasters at 1 m (LOD0 shells + PV + units; LOD2): area where they differ by > 0.5 / > 2.5 m, the T3
                    landside strips the reviewer found roofed at LOD2; plan Hausdorff distance of the two footprints
"""
import json
import math
import os
import sys

import numpy as np
from shapely.geometry import LineString, MultiLineString, Polygon, box as sbox
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify_domestic as V  # noqa: E402

ROOT = V.ROOT
OUT = V.OUT
GY = V.GROUND_Y
SCENE = os.path.join(ROOT, 'out', 'buildings3d', 'integ', 'draw', 'scene2d.json')


def world_tris(S, lod, skip=('_detail', '_fins', '_lettering')):
    out = []
    for n, m in S.items():
        if m['lod'] != lod or any(k in n for k in skip): continue
        for p in m['prims']:
            out.append(p['P'][p['T']])
    return np.concatenate(out) if out else np.zeros((0, 3, 3))


def section(T, y):
    """segments (world x, z) where the triangles cross the plane y (world)."""
    a = T[:, :, 1] - y
    s = np.sign(a); m = (s.min(1) < 0) & (s.max(1) > 0)
    T = T[m]; a = a[m]
    segs = []
    for t, av in zip(T, a):
        pts = []
        for i, j in ((0, 1), (1, 2), (2, 0)):
            if (av[i] < 0) != (av[j] < 0):
                f = av[i] / (av[i] - av[j]); p = t[i] + (t[j] - t[i]) * f; pts.append((p[0], p[2]))
        if len(pts) == 2: segs.append(pts)
    return MultiLineString(segs) if segs else MultiLineString()


def plan_overlap(T, hull, y0, y1):
    x0, z0, x1, z1 = hull.bounds
    lo = T[:, :, [0, 2]].min(1); hi = T[:, :, [0, 2]].max(1); ylo = T[:, :, 1].min(1); yhi = T[:, :, 1].max(1)
    m = (hi[:, 0] > x0) & (lo[:, 0] < x1) & (hi[:, 1] > z0) & (lo[:, 1] < z1) & (yhi > y0 + 0.05) & (ylo < y1 - 0.05)
    if not m.any(): return 0.0
    ps = []
    for t in T[m]:
        pg = Polygon(t[:, [0, 2]])
        if pg.area > 1e-4: ps.append(pg)
        else:
            ln = LineString(t[:, [0, 2]])
            if ln.length > 1e-3: ps.append(ln.buffer(0.025, cap_style=2))
    return unary_union(ps).intersection(hull).area if ps else 0.0


def raster_top(T, x0, z0, nx, nz, res=1.0):
    H = np.full((nz, nx), -np.inf)
    for t in T:
        xs, zs = t[:, 0], t[:, 2]
        i0 = max(int(np.floor((xs.min() - x0) / res)), 0); i1 = min(int(np.ceil((xs.max() - x0) / res)), nx - 1)
        j0 = max(int(np.floor((zs.min() - z0) / res)), 0); j1 = min(int(np.ceil((zs.max() - z0) / res)), nz - 1)
        if i1 < i0 or j1 < j0: continue
        a, b, c = t
        den = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
        if abs(den) < 1e-9: continue
        X, Z = np.meshgrid(x0 + (np.arange(i0, i1 + 1) + 0.5) * res, z0 + (np.arange(j0, j1 + 1) + 0.5) * res)
        l1 = ((b[2] - c[2]) * (X - c[0]) + (c[0] - b[0]) * (Z - c[2])) / den
        l2 = ((c[2] - a[2]) * (X - c[0]) + (a[0] - c[0]) * (Z - c[2])) / den
        l3 = 1 - l1 - l2
        m = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
        if not m.any(): continue
        y = l1 * a[1] + l2 * b[1] + l3 * c[1]
        sub = H[j0:j1 + 1, i0:i1 + 1]
        sub[m] = np.maximum(sub[m], y[m])
    return H


def run(full, lod2):
    j, b, _ = V.load_glb(full); S = V.scene_meshes(j, b)
    j2, b2, _ = V.load_glb(lod2); S2 = V.scene_meshes(j2, b2)
    T0 = world_tris(S, 0)
    T2 = world_tris(S2, 2)
    sc = json.load(open(SCENE))
    res = dict(full=os.path.relpath(full, ROOT), lod2=os.path.relpath(lod2, ROOT), scene=os.path.relpath(SCENE, ROOT))
    # ---------------- walkway gaps and clashes
    def filled(ml):
        """the occupied plan area at a section height: the section lines as 0.12-m strips, each closed ring filled."""
        if ml.is_empty: return ml
        st = ml.buffer(0.12, cap_style=2)
        return unary_union([Polygon(g.exterior) for g in getattr(st, 'geoms', [st])])
    secs = {(lod, h): filled(section(T, GY + h)) for lod, T in ((0, T0), (2, T2)) for h in (6.0, 7.5)}
    rows = []
    # second doors of one stand whose fixed walkway branches off the first bridge (data/sfo_stands.json: door 2's walk starts on
    # door 1's walkway / rotunda, e.g. F11 / F13 / F15 / F22): attached to that bridge, not to the building -> not a facade gap
    own = {}
    for br in sc['bridges']:
        P = br['poses']['current']['parts']
        own.setdefault(br['stand'], []).append((br.get('door'), unary_union([Polygon(p['hull']).buffer(0) for p in P if p['part'] in ('walkway', 'cyl', 'box')])))
    for br in sc['bridges']:
        if br['stand'][0] not in 'BCDEF': continue
        P = br['poses']['current']['parts']
        W = unary_union([Polygon(p['hull']).buffer(0) for p in P if p['part'] == 'walkway'])
        if W.is_empty: continue
        wy = [p['y'] for p in P if p['part'] == 'walkway']
        r = dict(stand=br['stand'], gate=br.get('gate'), door=br.get('door'))
        r['branch'] = bool(br.get('door', 1) != 1 and any(d_ != br.get('door') and g.distance(W) < 4.0 for d_, g in own[br['stand']]))
        for lod, T in ((0, T0), (2, T2)):
            gap = max(W.distance(secs[(lod, h)]) if not secs[(lod, h)].is_empty else 99.0 for h in (6.0, 7.5))
            r[f'gap_lod{lod}'] = round(gap, 2)
            ov = sum(plan_overlap(T, Polygon(p['hull']).buffer(0), p['y'][0], p['y'][1]) for p in P if p['part'] in ('walkway', 'cyl'))
            r[f'clash_lod{lod}'] = round(ov, 2)
        rows.append(r)
    res['walkways'] = rows
    for lod in (0, 2):
        g = np.array([r[f'gap_lod{lod}'] for r in rows if not r['branch']]); c = np.array([r[f'clash_lod{lod}'] for r in rows])
        res[f'summary_lod{lod}'] = dict(n=len(rows), branches=[r['stand'] for r in rows if r['branch']], gap_gt_0_5=int((g > 0.5).sum()), gap_gt_1_0=int((g > 1.0).sum()), gap_max=round(float(g.max()), 2),
                                        worst_gap=sorted(((r['stand'], r[f'gap_lod{lod}']) for r in rows if not r['branch']), key=lambda x: -x[1])[:8],
                                        clash_gt_0_5=int((c > 0.5).sum()), clash_max=round(float(c.max()), 2),
                                        worst_clash=sorted(((r['stand'], r[f'clash_lod{lod}']) for r in rows), key=lambda x: -x[1])[:8])
    # ---------------- LOD2 vs LOD0 top heights
    allT = np.concatenate([T0, T2])
    x0 = allT[:, :, 0].min() - 2; z0 = allT[:, :, 2].min() - 2; x1 = allT[:, :, 0].max() + 2; z1 = allT[:, :, 2].max() + 2
    nx, nz = int((x1 - x0)) + 1, int((z1 - z0)) + 1
    H0 = raster_top(T0, x0, z0, nx, nz); H2 = raster_top(T2, x0, z0, nx, nz)
    both = np.isfinite(H0) & np.isfinite(H2)
    d = np.where(both, H2 - H0, 0.0)
    only0 = np.isfinite(H0) & ~np.isfinite(H2); only2 = np.isfinite(H2) & ~np.isfinite(H0)
    res['lod2_vs_lod0'] = dict(raster_m=1.0, area_both=int(both.sum()), dz_gt_0_5_m2=int((np.abs(d) > 0.5).sum()), dz_gt_2_5_m2=int((np.abs(d) > 2.5).sum()),
                               dz_pos_gt_0_5_m2=int((d > 0.5).sum()), dz_neg_gt_0_5_m2=int((d < -0.5).sum()),
                               only_lod0_m2=int(only0.sum()), only_lod2_m2=int(only2.sum()))
    # the reviewer's T3 strips (open at LOD0, roofed at PV height at LOD2): around (-910.8, 100.0) and (-1049.2, 128.7)
    for nm, (px, pz) in (('T3E strip', (-910.8, 100.0)), ('T3W strip', (-1049.2, 128.7))):
        i, k = int((px - x0)), int((pz - z0))
        win = (slice(max(k - 6, 0), k + 7), slice(max(i - 6, 0), i + 7))
        res['lod2_vs_lod0'][nm] = dict(lod0_top=None if not np.isfinite(H0[win]).any() else round(float(np.nanmax(np.where(np.isfinite(H0[win]), H0[win], np.nan)) - GY), 2),
                                       lod2_top=None if not np.isfinite(H2[win]).any() else round(float(np.nanmax(np.where(np.isfinite(H2[win]), H2[win], np.nan)) - GY), 2),
                                       only_lod2_cells=int(only2[win].sum()))
    fp0 = V.footprint(S, 0, names=[n for n in S if S[n]['lod'] == 0 and '_shell' in n])
    fp2 = V.footprint(S2, 2)
    res['lod2_vs_lod0']['plan_hausdorff_m'] = round(fp0.boundary.hausdorff_distance(fp2.boundary), 2)
    res['lod2_vs_lod0']['plan_sym_diff_m2'] = round(fp0.symmetric_difference(fp2).area, 1)
    os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(os.path.join(OUT, 'domestic_verify_r1.json'), 'w'), indent=1)
    for lod in (0, 2):
        print(f'LOD{lod}:', json.dumps(res[f'summary_lod{lod}']))
    print('LOD2 vs LOD0:', json.dumps(res['lod2_vs_lod0']))
    return res


if __name__ == '__main__':
    a = sys.argv[1:]
    full = a[0] if a else os.path.join(ROOT, 'data', 'buildings3d', 'domestic.glb')
    l2 = a[1] if len(a) > 1 else os.path.join(os.path.dirname(full), 'domestic_lod2.glb')
    run(full, l2)
