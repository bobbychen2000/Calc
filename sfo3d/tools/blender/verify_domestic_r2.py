"""Review round 2 probes of the domestic asset (data/buildings3d/domestic.glb + domestic_lod2.glb, read back, no bpy):

    python3 tools/blender/verify_domestic_r2.py [domestic.glb domestic_lod2.glb]   # -> out/buildings3d/domestic_verify_r2.json

  tower   (findings 3 / 6) T2 / BA-D walls along the tower base building (IBF): their lowest bottom edge within 1 m of the IBF
          outline vs the LOWEST family's parapet top (F2 13.83 m) and roof (13.13); the gap between them: vertical rays at
          0.15 m outside the IBF outline (every 0.5 m along the stretches next to the domestic solids) must hit a domestic
          surface at or above the IBF roof of the lower family (else the gap looks down into the asset) - per LOD
  drums   (finding 8) the app's rotunda drums (scene2d.json cyl solids at all four poses AND the largest drum the app can draw
          per bridge, dom_geom.DRUMS) vs every domestic triangle in their height band (the reviewer's / b3d_integrate's test:
          plan area of the triangles clipped to the band, inside the hull; depth from the hull outline) - per LOD
  c3c     (finding 1) the office glass material / height band, the penthouse top and louvre
  bae     (finding 2) the end-wall glazing share of the end wall height; the BA-E plate PV top area
  sign    (finding 4) the lettering node extents
  plaus   (finding 5) BA-C / BA-D deck heights, clear heights over the app's 5.4-m concourse floor, bulkhead tops above the roof
"""
import json
import math
import os
import sys

import numpy as np
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dom_geom as G  # noqa: E402
import verify_domestic as V  # noqa: E402
import verify_domestic_r1 as V1  # noqa: E402

GY = V.GROUND_Y
SCENE = os.path.join(G.ROOT, 'out', 'buildings3d', 'integ', 'draw', 'scene2d.json')


def ray_down(T, x, z, ytop=60.0):
    """highest triangle (world) over (x, z): y or None."""
    lo = T[:, :, [0, 2]].min(1); hi = T[:, :, [0, 2]].max(1)
    m = (lo[:, 0] <= x) & (hi[:, 0] >= x) & (lo[:, 1] <= z) & (hi[:, 1] >= z)
    best = None
    for t in T[m]:
        a, b, c = t
        den = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
        if abs(den) < 1e-9: continue
        l1 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / den
        l2 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / den
        l3 = 1 - l1 - l2
        if min(l1, l2, l3) < -1e-6: continue
        y = l1 * a[1] + l2 * b[1] + l3 * c[1]
        if best is None or y > best: best = y
    return best


def tower_probe(S, lod):
    T = V1.world_tris(S, lod, skip=('_fins', '_lettering'))
    ex = G.TOWER_EXCL
    # stretches of the IBF outline next to a domestic solid: points 0.15 m outside the outline, every 0.5 m
    ring = ex.exterior
    pts = []
    near = []
    for k in range(int(ring.length / 0.5)):
        p = ring.interpolate(k * 0.5)
        q = ring.interpolate(k * 0.5 + 0.01)
        dx, dz = q.x - p.x, q.y - p.y; L = math.hypot(dx, dz)
        n = np.array([dz / L, -dx / L])
        if ex.contains(Point(np.array([p.x, p.y]) + n * 0.15)): n = -n
        # the probe point lies in the flashing band (between the 0.15-m joint at the IBF wall and the domestic wall 0.3 m off)
        pts.append((np.array([p.x, p.y]) + n * (0.5 * (G.TOWER_JOINT + G.TOWER_GAP)), np.array([p.x, p.y]) + n * (G.TOWER_GAP + 0.25)))
    # triangles of walls close to the IBF: lowest bottom edge
    cen = T.mean(1)
    dist = np.array([ex.exterior.distance(Point(c[0], c[2])) for c in cen])
    vert = np.abs(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])[:, 1]) < 1e-6
    wm = vert & (dist < 1.0) & (T[:, :, 1].max(1) - GY > 13.0)
    low_wall = float(T[wm][:, :, 1].min() - GY) if wm.any() else None
    f_lo = min(G.TOWER_IBF_ROOFS) if G.TOWER_IBF_ROOFS else G.TOWER_IBF_ROOF
    open_n, cover, total = 0, 0, 0
    worst = []
    # only the stretches where a domestic surface stands within 1 m (the rest faces open apron)
    lo = T[:, :, [0, 2]].min(1); hi = T[:, :, [0, 2]].max(1)
    for c, cout in pts:
        m = (lo[:, 0] <= c[0] + 1.0) & (hi[:, 0] >= c[0] - 1.0) & (lo[:, 1] <= c[1] + 1.0) & (hi[:, 1] >= c[1] - 1.0) & (T[:, :, 1].max(1) - GY > 6.0)
        if not m.any(): continue
        yo = ray_down(T[m], cout[0], cout[1])
        if yo is None or yo - GY < 6.0: continue          # no domestic solid beyond the gap there (open apron / corner)
        total += 1
        y = ray_down(T[m], c[0], c[1])
        if y is not None and y - GY >= min(f_lo, G.TOWER_Z1) - 0.05: cover += 1
        elif y is not None and y - GY >= 6.0: cover += 1          # a lower domestic roof edge (BA-D) closes it at its own top
        else:
            open_n += 1; worst.append([round(float(c[0]), 2), round(float(c[1]), 2), None if y is None else round(y - GY, 2)])
    return dict(lowest_wall_bottom_near_ibf_m=None if low_wall is None else round(low_wall, 3), ibf_roofs_m=G.TOWER_IBF_ROOFS,
                ibf_parapet_f2_m=13.83, flashing_top_m=round(G.TOWER_Z1, 3), joint_m=G.TOWER_JOINT, gap_points=total, gap_points_closed=cover,
                gap_points_open=open_n, open_examples=worst[:8],
                note='walls facing the IBF: lowest bottom edge within 1 m of the IBF outline (0 = full height); gap points: rays in the '
                     'flashing band between the 0.15-m joint and the domestic wall must hit a domestic surface at >= min(top, flashing)',
                ok=bool(low_wall is not None and low_wall <= f_lo + 1e-3 and open_n == 0))


def clip_plan(T, y0, y1):
    from shapely.geometry import LineString
    out = []
    for t in T:
        poly = [tuple(v) for v in t]
        for lim, keep in ((y0, lambda v: v[1] >= y0), (y1, lambda v: v[1] <= y1)):
            if not poly: break
            res = []
            for k in range(len(poly)):
                a, b_ = poly[k], poly[(k + 1) % len(poly)]
                ia, ib = keep(a), keep(b_)
                if ia: res.append(a)
                if ia != ib:
                    f = (lim - a[1]) / (b_[1] - a[1]); res.append(tuple(a[q] + f * (b_[q] - a[q]) for q in range(3)))
            poly = res
        if len(poly) < 3: continue
        xz = [(v[0], v[2]) for v in poly]; P = Polygon(xz)
        if P.is_valid and P.area > 1e-4: out.append(P)
        else:
            xs = np.array(xz); d = np.linalg.norm(xs[:, None] - xs[None], axis=2); a, b_ = np.unravel_index(d.argmax(), d.shape)
            if d[a, b_] > 0.02: out.append(LineString([xz[a], xz[b_]]).buffer(0.025, cap_style=2))
    return unary_union(out) if out else Polygon()


def drum_probe(S, lod):
    T = V1.world_tris(S, lod, skip=('_fins', '_lettering'))
    lo = T[:, :, [0, 2]].min(1); hi = T[:, :, [0, 2]].max(1); ylo = T[:, :, 1].min(1); yhi = T[:, :, 1].max(1)
    hulls = []
    if os.path.exists(SCENE):
        SC = json.load(open(SCENE))
        for b in SC['bridges']:
            if b['stand'][0] not in 'BCDEF': continue
            for pk, P_ in b['poses'].items():
                rc = P_['pose'].get('rc') or b.get('rc')
                for pr in P_['parts']:
                    if pr['part'] != 'cyl': continue
                    H = Polygon(pr['hull']); c = H.centroid
                    if rc and math.dist([c.x, c.y], [rc[0], rc[-1]]) < 0.6:
                        hulls.append(('scene2d', b['stand'], b['door'], pk, H, pr['y'][0], pr['y'][1]))
    for d in G.DRUMS:
        x, z = G.Wp(*d['c'])
        hulls.append(('max_r', d['stand'], d['door'], 'any', Point(x, z).buffer(d['r'], 48), GY + G.DRUM_BAND[0] + 0.15, GY + G.DRUM_BAND[1] - 0.15))
    res = []
    for src, st, door, pk, H, y0, y1 in hulls:
        x0, z0, x1, z1 = H.bounds
        m = (hi[:, 0] > x0) & (lo[:, 0] < x1) & (hi[:, 1] > z0) & (lo[:, 1] < z1) & (yhi > y0 + 0.02) & (ylo < y1 - 0.02)
        if not m.any(): continue
        o = clip_plan(T[m], y0 + 0.02, y1 - 0.02).intersection(H)
        if o.area <= 0.05: continue
        import shapely
        pts = shapely.get_coordinates(o)
        dep = float(shapely.distance(H.exterior, shapely.points(pts)).max()) if len(pts) else 0.0
        res.append(dict(src=src, stand=st, door=door, pose=pk, overlap_m2=round(o.area, 3), depth_m=round(dep, 3)))
    conf = [r for r in res if r['overlap_m2'] > 0.3 and r['depth_m'] > 0.10]
    out = dict(hulls=len(hulls), contacts=len(res), conflicts=len(conf), ok=len(conf) == 0)
    for src in ('scene2d', 'max_r'):
        rs = sorted([r for r in res if r['src'] == src], key=lambda r: -r['overlap_m2'])
        best = {}
        for r in rs:                       # worst pose per bridge
            best.setdefault((r['stand'], r['door']), r)
        out['contacts_' + src] = len(rs); out['conflicts_' + src] = sum(1 for r in conf if r['src'] == src)
        out['worst_' + src] = list(best.values())[:10]
    out['worst'] = out['worst_scene2d'][:3] + out['worst_max_r'][:3]
    return out


def run(full, lod2):
    j, b, size = V.load_glb(full); S = V.scene_meshes(j, b)
    j2, b2, _ = V.load_glb(lod2); S2 = V.scene_meshes(j2, b2)
    out = dict(glb=os.path.relpath(full, G.ROOT))
    out['tower'] = {'lod0': tower_probe(S, 0), 'lod2': tower_probe(S2, 2)}
    out['drums'] = {'lod0': drum_probe(S, 0), 'lod2': drum_probe(S2, 2)}
    # C3C
    c3 = {}
    for n, m in S.items():
        if m['lod'] != 0 or not n.startswith('L0_C3C'): continue
        for p in m['prims']:
            mat = p['mat'].split('@')[0]
            y = p['P'][:, 1] - GY
            c3.setdefault(mat, [float(y.min()), float(y.max())])
            c3[mat] = [min(c3[mat][0], float(y.min())), max(c3[mat][1], float(y.max()))]
    out['c3c'] = dict(materials={k: [round(v[0], 2), round(v[1], 2)] for k, v in sorted(c3.items())},
                      office_glass_from_m=round(c3.get('glass_c3c', [None])[0], 2) if 'glass_c3c' in c3 else None,
                      top_m=round(c3['coping'][1], 2) if 'coping' in c3 else None, louvre='louvre' in c3,
                      ok=bool('glass_c3c' in c3 and 'louvre' in c3 and 'coping' in c3 and abs(c3['coping'][1] - G.C3C_PENT_TOP) < 0.05))
    # BA-E end wall: the end bay's NNE face (normal within 35 deg of 27.8, on the end bay outline)
    W, feats, info = G.build_world(0)
    eb = G.wld(info['E_endbay']).exterior
    gl = []; tot = []
    for n, m in S.items():
        if m['lod'] != 0 or not n.startswith('L0_BA_E_shell'): continue
        for p in m['prims']:
            mat = p['mat'].split('@')[0]
            for t in p['P'][p['T']]:
                nrm = np.cross(t[1] - t[0], t[2] - t[0])
                if abs(nrm[1]) > 1e-6 * np.linalg.norm(nrm): continue
                hd = math.degrees(math.atan2(nrm[0], -nrm[2])) % 360
                if abs((hd - 27.83 + 180) % 360 - 180) > 35: continue
                c = t.mean(0)
                if eb.distance(Point(c[0], c[2])) > 0.3: continue
                if mat in ('glass_clear', 'panel_dark', 'service'):
                    (gl if mat == 'glass_clear' else tot).append(t[:, 1] - GY)
    gz = np.concatenate(gl) if gl else np.zeros(0)
    out['bae'] = dict(end_glass_z=[round(float(gz.min()), 2), round(float(gz.max()), 2)] if len(gz) else None,
                      end_wall_head=round(G.H['E'] - 0.8, 2),
                      glass_share=round(float((gz.max() - gz.min()) / (G.H['E'] - 0.8)), 3) if len(gz) else None)
    pv = 0.0
    for n, m in S.items():
        if m['lod'] != 1 or n != 'L1_BA_E_pv': continue
        for p in m['prims']:
            for t in p['P'][p['T']]:
                nrm = np.cross(t[1] - t[0], t[2] - t[0])
                if nrm[1] > 0: pv += 0.5 * abs(nrm[1])
    out['bae']['plate_pv_top_m2'] = round(pv, 1)
    out['bae']['ok'] = bool(out['bae']['glass_share'] and out['bae']['glass_share'] > 0.8 and pv > 600)
    # sign
    sg = S.get('L0_T1_lettering')
    if sg:
        P = np.concatenate([p['P'] for p in sg['prims']])
        out['sign'] = dict(z=[round(float(P[:, 1].min() - GY), 2), round(float(P[:, 1].max() - GY), 2)],
                           extent_xz=round(float(np.hypot(*(P[:, [0, 2]].max(0) - P[:, [0, 2]].min(0)))), 2),
                           materials=sorted({p['mat'] for p in sg['prims']}))
    # plausibility numbers (BA-C / BA-D)
    pl = {}
    for key, bld in (('BA_C_body', 'BA_C'), ('BA_D_body', 'BA_D')):
        s = next(o for o in W.S if o.key == key)
        doors = [d for d in info['doors'] if d['host'] == key and d['low']]
        tops = [max(G.VEST['z1'], d['h_host'] + 1.0) for d in doors]
        pl[bld] = dict(roof_edge_m=s.h, deck_m=round(s.deck, 2), slab_underside_m=round(s.h - s.thk, 2), app_floor_m=G.FLOOR2,
                       clear_to_deck_m=round(s.deck - G.FLOOR2, 2), clear_under_0p8m_roof_structure_m=round(s.deck - 0.8 - G.FLOOR2, 2),
                       app_walkway_top_m=round(G.WALK_TOP + 0.05, 2), bulkheads=len(doors),
                       bulkhead_top_m=round(max(tops), 2) if tops else None,
                       bulkhead_above_roof_edge_m=round(max(tops) - s.h, 2) if tops else None)
    out['plausibility_bac_bad'] = pl
    out['n_fail'] = sum(1 for k in ('c3c', 'bae') if not out[k].get('ok')) + sum(1 for k in ('tower', 'drums') for l in ('lod0', 'lod2') if not out[k][l]['ok'])
    p = os.path.join(V.OUT, 'domestic_verify_r2.json')
    json.dump(out, open(p, 'w'), indent=1, default=float)
    return out, p


if __name__ == '__main__':
    a = sys.argv[1:] or [os.path.join(G.ROOT, 'data', 'buildings3d', 'domestic.glb'), os.path.join(G.ROOT, 'data', 'buildings3d', 'domestic_lod2.glb')]
    o, p = run(a[0], a[1])
    for k in ('tower', 'drums'):
        for l in ('lod0', 'lod2'):
            print(k, l, json.dumps({kk: vv for kk, vv in o[k][l].items() if kk not in ('worst', 'open_examples')}))
            if o[k][l].get('worst'): print('   worst', o[k][l]['worst'][:4])
            if o[k][l].get('open_examples'): print('   open', o[k][l]['open_examples'][:4])
    for k in ('c3c', 'bae', 'sign', 'plausibility_bac_bad'):
        print(k, json.dumps(o.get(k)))
    print('n_fail', o['n_fail'], '->', p)
