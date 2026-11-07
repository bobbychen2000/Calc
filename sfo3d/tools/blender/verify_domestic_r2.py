"""Review round 2 probes of the domestic asset (data/buildings3d/domestic.glb + domestic_lod2.glb, read back, no bpy):

    python3 tools/blender/verify_domestic_r2.py [domestic.glb domestic_lod2.glb]   # -> out/buildings3d/domestic_verify_r2.json

  tower   (findings 3 / 6) T2 / BA-D walls along the tower base building (IBF): their lowest bottom edge within 1 m of the IBF
          outline vs the LOWEST family's parapet top (F2 13.83 m) and roof (13.13); the gap between them: vertical rays at
          0.15 m outside the IBF outline (every 0.5 m along the stretches next to the domestic solids) must hit a domestic
          surface at or above the IBF roof of the lower family (else the gap looks down into the asset) - per LOD
  drums   (finding 8) the app's rotunda drums (scene2d.json cyl solids at all four poses AND the largest drum the app can draw
          per bridge, dom_geom.DRUMS, in its own band from the bridge's rotunda floor Hr) vs every domestic triangle in their
          height band (the reviewer's / b3d_integrate's test: plan area of the triangles clipped to the band, inside the hull;
          depth from the hull outline) - per LOD. scene2d.json: $SCENE2D, else the newer of out/draw/ (the drawing pipeline's
          extraction) and out/buildings3d/integ/draw/; a scene whose js/live/gates.js hash differs from the working tree is
          reported as stale (close-out r3 fix 2: the 5 Nov scene still had the one 5.4-m level)
  walk    (close-out r3 fix 2) the app's fixed-walkway solids (tools/blender/app_bridges.json, gates.js DEPARTURE_LEVELS per
          pier) vs every domestic triangle in their own height band, per bridge (the verifier's brsolids test)
  c3c     (finding 1) the office glass material / height band, the penthouse top and louvre
  bae     (finding 2) the end-wall glazing share of the end wall height; the BA-E plate PV top area
  sign    (finding 4) the lettering node extents
  plaus   (finding 5) BA-C / BA-D deck heights, clear heights over the pier's bridge level (gates.js DEPARTURE_LEVELS C 3.2 /
          D 3.65 since close-out r3), the walkway tops at the doors, bulkheads (none expected)
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
import app_bridges as AB  # noqa: E402


def pick_scene():
    """(path, info) of the scene2d.json to use: $SCENE2D, else the newest of the drawing pipeline's out/draw/scene2d.json and
    out/buildings3d/integ/draw/scene2d.json; info = generated time, git, and whether its js/live/gates.js hash matches the
    working tree (meta.inputs: sha256 prefix)."""
    import hashlib
    cands = [os.environ.get('SCENE2D')] if os.environ.get('SCENE2D') else \
        [os.path.join(G.ROOT, 'out', 'draw', 'scene2d.json'), os.path.join(G.ROOT, 'out', 'buildings3d', 'integ', 'draw', 'scene2d.json')]
    cands = [c for c in cands if c and os.path.exists(c)]
    if not cands: return None, dict(scene=None)
    pth = max(cands, key=os.path.getmtime)
    meta = json.load(open(pth)).get('meta', {})
    h = (meta.get('inputs') or {}).get('js/live/gates.js')
    cur = hashlib.sha256(open(os.path.join(G.ROOT, 'js', 'live', 'gates.js'), 'rb').read()).hexdigest()
    return pth, dict(scene=os.path.relpath(pth, G.ROOT), generated=meta.get('generated'), git=meta.get('git'),
                     gates_js_current=bool(h) and cur.startswith(h))


SCENE, SCENE_INFO = pick_scene()


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
    if SCENE and os.path.exists(SCENE):
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
        # (close-out r3 fix 2: the drum's own band, gates.js Hr - 0.3 .. Hr + 3.3 from app_bridges.json; was DRUM_BAND at 5.4)
        hulls.append(('max_r', d['stand'], d['door'], 'any', Point(x, z).buffer(d['r'], 48), GY + d['Hr'] - 0.3, GY + d['Hr'] + 3.3))
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


def drum_overhead(S, lod):
    """close-out r3 (buildings-4): the integration footprint rings (plan) put the F7 / F8 L1 drums ~1.05 m inside BA_F - the
    roof overhang over them. Per drum (largest the app can draw, G.DRUMS): the lowest domestic surface over the drum disc and its
    clearance over the drum top (the app's Hr + 3.3 of that bridge, app_bridges.json); a roof above is allowed, a negative value
    is not. Close-out r3 fix 2 (verifier v9): every triangle that reaches above the drum top and covers the disc counts, with its
    height evaluated over the disc (a sloped / vertical face dipping below the top gives a negative clearance; it used to be
    left out when its lowest vertex was below the top)."""
    from shapely.geometry import LineString
    import shapely
    T = V1.world_tris(S, lod, skip=('_fins', '_lettering'))
    lo = T[:, :, [0, 2]].min(1); hi = T[:, :, [0, 2]].max(1); ylo = T[:, :, 1].min(1); yhi = T[:, :, 1].max(1)
    rows = []
    for d in G.DRUMS:
        top = GY + d['Hr'] + 3.3
        x, z = G.Wp(*d['c']); H = Point(x, z).buffer(d['r'], 48); x0, z0, x1, z1 = H.bounds
        m = (hi[:, 0] > x0) & (lo[:, 0] < x1) & (hi[:, 1] > z0) & (lo[:, 1] < z1) & (yhi >= top - 0.02) & (ylo < top + 40.0)
        ys = []
        for t in T[m]:
            xz = [(v[0], v[2]) for v in t]
            q = Polygon(xz)
            if q.is_valid and q.area > 1e-4:
                o = q.intersection(H)
                if o.area <= 0.01: continue
                # the triangle's plane height at the vertices of its part over the disc
                A = np.c_[t[:, 0], t[:, 2], np.ones(3)]
                try: cf = np.linalg.solve(A, t[:, 1])
                except np.linalg.LinAlgError: ys.append(float(t[:, 1].min())); continue
                P_ = shapely.get_coordinates(o)
                ys.append(float((P_[:, 0] * cf[0] + P_[:, 1] * cf[1] + cf[2]).min()))
            else:
                ln = LineString(xz).buffer(0.025, cap_style=2)
                if ln.intersects(H) and ln.intersection(H).area > 0.002: ys.append(float(t[:, 1].min()))   # a vertical face over the disc
        if ys: rows.append(dict(stand=d['stand'], door=d['door'], r=round(d['r'], 2), Hr=round(d['Hr'], 3), drum_top_m=round(top - GY, 2),
                                overhead_m=round(min(ys) - GY, 2), clear_m=round(min(ys) - top, 2)))
    rows.sort(key=lambda r: r['clear_m'])
    return dict(drums_under_roof=len(rows), min_clear_m=rows[0]['clear_m'] if rows else None, rows=rows[:12],
                ok=all(r['clear_m'] >= 0.0 for r in rows))


def walk_probe(S, lod):
    """close-out r3 fix 2 (verifier v1): every fixed-walkway solid of the app at rest (gates.js solidsQ, app_bridges.json:
    per-pier DEPARTURE_LEVELS) vs the domestic triangles clipped to the solid's own height band (+-0.03 m), per bridge: plan
    area of the HORIZONTAL faces (slab / vestibule / bulkhead tops and undersides cutting through the walkway: a conflict) and of
    the VERTICAL faces as 5-cm strips (the facade / door frame the walkway docks into: expected, listed). The walkway solids are
    cut into 1-m slices, each with its local floor band (a segment's min-max band would reach below the floor of its high end)."""
    from shapely.geometry import LineString
    T = V1.world_tris(S, lod, skip=('_lettering',))
    lo = T[:, :, [0, 2]].min(1); hi = T[:, :, [0, 2]].max(1); ylo = T[:, :, 1].min(1); yhi = T[:, :, 1].max(1)
    rows = []
    for b in AB.bridges('BCDEF', upper=False):
        hz = vt = 0.0
        for P_, lo_, hi_ in AB.walkway_slices(b, 1.0):      # (1-m slices: the band of the sloping walkway where it is)
            g = Polygon(P_).buffer(-0.02)
            y0, y1 = GY + lo_ + 0.03, GY + hi_ - 0.03
            x0, z0, x1, z1 = g.bounds
            m = (hi[:, 0] > x0) & (lo[:, 0] < x1) & (hi[:, 1] > z0) & (lo[:, 1] < z1) & (yhi > y0) & (ylo < y1)
            for t in T[m]:
                q = clip_plan(t[None], y0, y1)
                if q.is_empty or not q.intersects(g): continue
                a = q.intersection(g).area
                nrm = np.cross(t[1] - t[0], t[2] - t[0]); nl = np.linalg.norm(nrm)
                if nl > 1e-9 and abs(nrm[1]) / nl > 0.2: hz += a
                else: vt += a
        if hz > 0.01 or vt > 0.01:
            rows.append(dict(bridge=b['stand'] + ' L%s' % b['door'], level=b['Hb'], horizontal_m2=round(hz, 3), vertical_m2=round(vt, 3)))
    bad = [r for r in rows if r['horizontal_m2'] > 0.05]
    by = {}
    for r in rows: by[r['bridge'][0]] = round(by.get(r['bridge'][0], 0.0) + r['horizontal_m2'] + r['vertical_m2'], 2)
    return dict(bridges=len(AB.bridges('BCDEF', upper=False)), contacts=len(rows), total_m2=round(sum(r['horizontal_m2'] + r['vertical_m2'] for r in rows), 2),
                horizontal_m2=round(sum(r['horizontal_m2'] for r in rows), 3), by_pier_m2=by, conflicts=len(bad),
                worst=sorted(rows, key=lambda r: -(r['horizontal_m2'] + r['vertical_m2']))[:8], conflict_rows=bad[:10], ok=not bad)


def t2_curb_probe(S, lod):
    """close-out r3 (buildings-2): the departures roadway along T2 vs the moved T2 face. Deck = the OSM Departures ways along
    T2 (G.T2_DEP_WAYS, carriageway half-widths) at the curb level; any T2 / connector triangle inside that plan between the deck
    and 4.6 m above it is a hit (the connector is allowed above 4.6 m); the lean-free roof edge line (G.T2_EDGE_LINE) vs the T2
    roof-edge probes; the sidewalk and canopy levels; the connector soffit over the deck."""
    from shapely.geometry import LineString
    T = V1.world_tris(S, lod, skip=('_fins', '_lettering'))
    deck_top = G.CURB - 0.15
    deck = unary_union([LineString(p).buffer(w, cap_style=2) for w, p in G.T2_DEP_WAYS.values()])
    # the T2 stretch only: way 256787747 runs on past the T3 East curb (its 1-3 m deck overlap is the integration's T3E cut,
    # not this probe's subject) - clip to the z range of the T2 departures sidewalk
    sb = G.T2_SIDEWALK_POLY.bounds
    deck = deck.intersection(Polygon([(-2000.0, sb[1]), (0.0, sb[1]), (0.0, sb[3]), (-2000.0, sb[3])]))
    x0, z0, x1, z1 = deck.bounds
    lo = T[:, :, [0, 2]].min(1); hi = T[:, :, [0, 2]].max(1); ylo = T[:, :, 1].min(1); yhi = T[:, :, 1].max(1)
    m = (hi[:, 0] > x0) & (lo[:, 0] < x1) & (hi[:, 1] > z0) & (lo[:, 1] < z1) & (yhi > GY + deck_top + 0.02) & (ylo < GY + deck_top + 4.6)
    o = clip_plan(T[m], GY + deck_top + 0.02, GY + deck_top + 4.6).intersection(deck.buffer(-0.35)) if m.any() else Polygon()
    # connector soffit over the deck: lowest triangle above deck + 4.6 inside the deck plan
    mm = (hi[:, 0] > x0) & (lo[:, 0] < x1) & (hi[:, 1] > z0) & (lo[:, 1] < z1) & (ylo >= GY + deck_top + 4.6 - 0.02)
    soff = [float(t[:, 1].min()) - GY for t in T[mm] if Polygon([(v[0], v[2]) for v in t]).buffer(0).intersection(deck).area > 0.05]
    # roof edge vs the measured line: at z = 180..245 the westmost point of the T2 roof-level (> 15 m) triangles cut by the
    # plane z = zz, near the line (a section, not the triangles' vertices: the fascia triangles run 10-25 m along the slanted line)
    a, k = G.T2_EDGE_LINE
    roof = T[(ylo > GY + 15.0)]
    dev = []
    for zz in np.arange(180.0, 246.0, 5.0):
        sel = roof[(roof[:, :, 2].min(1) < zz) & (roof[:, :, 2].max(1) > zz)]
        xs = []
        for t in sel:
            for i, j in ((0, 1), (1, 2), (2, 0)):
                za, zb = t[i, 2] - zz, t[j, 2] - zz
                if (za < 0) != (zb < 0):
                    xs.append(float(t[i, 0] + (t[j, 0] - t[i, 0]) * za / (za - zb)))
        xs = [x for x in xs if abs(x - (a + k * zz)) < 6]
        if xs: dev.append(round(min(xs) - (a + k * zz), 2))
    return dict(deck_plan_m2=round(deck.area, 1), solid_inside_deck_band_m2=round(o.area, 3), connector_soffit_over_deck_m=round(min(soff) - deck_top, 2) if soff else None,
                roof_edge_minus_line_m=dict(n=len(dev), median=float(np.median(dev)) if dev else None, max_abs=float(np.max(np.abs(dev))) if dev else None),
                ok=bool(o.area < 0.3 and (not soff or min(soff) - deck_top >= 4.6) and dev and np.max(np.abs(dev)) < 0.6))


def run(full, lod2):
    j, b, size = V.load_glb(full); S = V.scene_meshes(j, b)
    j2, b2, _ = V.load_glb(lod2); S2 = V.scene_meshes(j2, b2)
    out = dict(glb=os.path.relpath(full, G.ROOT))
    out['tower'] = {'lod0': tower_probe(S, 0), 'lod2': tower_probe(S2, 2)}
    out['drums'] = {'lod0': drum_probe(S, 0), 'lod2': drum_probe(S2, 2)}
    out['drum_overhead'] = {'lod0': drum_overhead(S, 0), 'lod2': drum_overhead(S2, 2)}
    out['t2_curb'] = {'lod0': t2_curb_probe(S, 0), 'lod2': t2_curb_probe(S2, 2)}
    out['walk'] = {'lod0': walk_probe(S, 0), 'lod2': walk_probe(S2, 2)}
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
    for key, bld, pier in (('BA_C_body', 'BA_C', 'C'), ('BA_D_body', 'BA_D', 'D')):
        s = next(o for o in W.S if o.key == key)
        lvl = G.PIER_LEVEL[pier]                         # gates.js DEPARTURE_LEVELS (close-out r3 fix 2; was the one 5.4)
        alld = [d for d in info['doors'] if d['host'] == key]
        doors = [d for d in alld if d['low']]
        tops = [max(d['vz1'], d['h_host'] + 1.0) for d in doors]
        wtop = max([d['wtop'] for d in alld] or [lvl + 3.0])
        pl[bld] = dict(roof_edge_m=s.h, deck_m=round(s.deck, 2), slab_underside_m=round(s.h - s.thk, 2), app_floor_m=lvl,
                       app_floor_tag=G.PIER_LEVEL_TAG[pier], clear_to_deck_m=round(s.deck - lvl, 2),
                       clear_under_0p8m_roof_structure_m=round(s.deck - 0.8 - lvl, 2),
                       app_walkway_top_m=round(wtop, 2), walkway_top_below_slab_underside_m=round(s.h - s.thk - wtop, 2),
                       doors=len(alld), bulkheads=len(doors),
                       bulkhead_top_m=round(max(tops), 2) if tops else None,
                       bulkhead_above_roof_edge_m=round(max(tops) - s.h, 2) if tops else None,
                       ok=bool(len(doors) == 0 and s.h - s.thk - wtop >= 0.0))
    out['plausibility_bac_bad'] = pl
    out['scene2d'] = SCENE_INFO
    out['app_bridges'] = dict(generated=AB.load()['generated'], stale_inputs=AB.stale())
    out['n_fail'] = sum(1 for k in ('c3c', 'bae') if not out[k].get('ok')) + sum(1 for k in ('tower', 'drums', 'drum_overhead', 't2_curb', 'walk') for l in ('lod0', 'lod2') if not out[k][l]['ok']) + \
        sum(1 for v in pl.values() if not v['ok']) + (1 if AB.stale() else 0)
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
        print(k, json.dumps(o.get(k), default=float))
    for l in ('lod0', 'lod2'):
        print('drum_overhead', l, json.dumps(o['drum_overhead'][l]))
    for l in ('lod0', 'lod2'):
        print('t2_curb', l, json.dumps(o['t2_curb'][l]))
    for l in ('lod0', 'lod2'):
        print('walk', l, json.dumps({k: v for k, v in o['walk'][l].items() if k != 'worst'}), '\n   worst', o['walk'][l]['worst'][:5])
    print('scene2d', json.dumps(o['scene2d']), 'app_bridges', json.dumps(o['app_bridges']))
    print('n_fail', o['n_fail'], '->', p)
