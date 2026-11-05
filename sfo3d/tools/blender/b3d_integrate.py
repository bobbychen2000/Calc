"""Integration of the Blender building assets (data/buildings3d/*.glb) into the app: plan footprints measured on the
exported meshes, the table of first-pass app buildings each asset replaces, and the combined physical-plausibility
check of all four groups against the surveyed stands, bridges, taxiways and aircraft envelopes. numpy + shapely, no bpy.

    python3 tools/blender/b3d_integrate.py            # -> data/buildings3d/integration.json + integration.js,
                                                      #    out/buildings3d/integ/integration_report.txt
    python3 tools/blender/b3d_integrate.py --check    # checks only (no files written), exit 1 on a physical conflict

What it measures (everything from the exported GLBs, read back with the reader below: what the app draws):
  footprints   plan projection of every triangle of every LOD (LOD0..2 and the *_lod2.glb phone files), per asset unit
               (tower; ITB hall / BA-A / BA-G; domestic extras.building; landside top-level building nodes), unioned
               and simplified by 0.02 m (after a +0.02 m buffer that closes the seams). Vertical faces count as
               0.05 m strips, so free-standing walls / screens are included. Instanced cars (EXT_mesh_gpu_instancing)
               stand on the decks inside the footprints and are skipped.
  replacement  every first-pass app building (js/live/terminals.js buildTerminals parts of data/sfo_buildings.json,
               its terminal-complex ramp-level wall edges, js/live/airport.js data/sfo_airport.json structures, the
               tower and the AirTrain guideway slab) is assigned to the asset group whose footprint (+2 m: SFO Museum
               outline accuracy is +-5 m, data/sfo_buildings.json footprint_accuracy) covers >= 50 % of its plan area
               (wall edges: of its length, +3 m). Below that it stays (e.g. the courtyard links and guideway-crossing
               connectors the domestic asset does not model, manifest.json#domestic.integration.keep).
  plausibility (the owner's rule: no building intersecting stands, bridges, aircraft envelopes or taxilanes), each LOD
               separately and the max-extent union:
                 a. aircraft envelope of every accepted type at every stand (tools/stands/geom.py stand_env, the
                    envelope tools/stands/check_stands.py tests) vs every footprint: overlap > 0.5 m2 or closer than
                    2.0 m -> CONFLICT, closer than 3.5 m -> NOTE (check_stands.py thresholds);
                 b. jet bridges: docked / parked tunnel + cab (geom.bridge_parts at `cab`, and at the stow pose) vs
                    every footprint other than the building the bridge serves, and vs that building beyond 3 m of the
                    bridge's own fixed walkway end / rotunda; fixed walkway + rotunda vs other buildings;
                 c. SFO Museum taxiway polygons (data/sfo_airport.json taxiways) and taxiway centrelines
                    (data/sfo_details.json centerlines): no footprint inside a taxiway polygon; centreline distance
                    reported (and compared with the first-pass outlines at the same place);
                 d. the asset groups against each other (overlap where height ranges overlap: NOTE; the groups'
                    own --neighbours checks measured slivers of ~1 cm along shared walls).
Outputs (integration.js is what the app imports; it holds only what the renderer needs):
  replace      {parts: [[i, name, group]], complexEdges: {ring: [[i0, i1, group], ...]}, structures: [[i, name, group]],
                atc: group, rail: group}   (names are checked by the app before routing: a renamed part stays drawn)
  physics      (integration.json only) blocking footprints for the ground physics' building grid (js/live/ground.js
               buildingGrid; not wired yet: tools/live/*.mjs import ground.js from repository copies); hangars (Superbay,
               the MOC block with its barrel hangars) are left out as the app leaves its hangars out (aircraft may stand
               inside hangars), and the elevated guideway as the app leaves its rail out
  tower        cab eye / axis for the app's tower camera (manifest.json#tower.integration.tower_camera)
Sources: data/buildings3d/manifest.json (each group's verified entry), data/sfo_stands.json, data/sfo_airport.json,
data/sfo_buildings.json, data/sfo_details.json; tools/stands/geom.py for the envelopes and bridge parts.
"""
import hashlib
import json
import math
import os
import struct
import sys
import time

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon, MultiPolygon
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
D3 = os.path.join(ROOT, 'data', 'buildings3d')
OUTD = os.path.join(ROOT, 'out', 'buildings3d', 'integ')
GROUND_Y = 3.0
GROUPS = ['tower', 'itb', 'domestic', 'landside']
FILES = {'tower': ['tower.glb', 'tower_f1.glb', 'tower_lod2.glb'], 'itb': ['itb.glb', 'itb_lod2.glb'],  # tower.glb = F2 (default), tower_f1.glb = F1
         'domestic': ['domestic.glb', 'domestic_lod2.glb'], 'landside': ['landside.glb', 'landside_lod2.glb']}
COVER_BUF, EDGE_BUF, COVER_MIN = 2.0, 3.0, 0.5
# landside nodes that are hangars (aircraft may stand inside: js/live/ground.js buildingGrid skips kind 'hangar')
HANGARS = {'superbay', 'united_moc'}  # the MOC node holds the large hangar block + barrel-vault hangars (manifest)
CT = {5126: ('f', 4), 5125: ('I', 4), 5123: ('H', 2), 5121: ('B', 1), 5122: ('h', 2), 5120: ('b', 1)}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


# ------------------------------------------------------------------------------------------------ GLB reader
def read_glb(path):
    b = open(path, 'rb').read()
    n = struct.unpack_from('<I', b, 12)[0]
    js = json.loads(b[20:20 + n])
    off = 20 + n; bin_ = b''
    if off < len(b):
        ln = struct.unpack_from('<I', b, off)[0]; bin_ = b[off + 8: off + 8 + ln]
    return js, bin_


def accessor(js, bin_, i):
    a = js['accessors'][i]; bv = js['bufferViews'][a['bufferView']]
    fmt, sz = CT[a['componentType']]; nc = NC[a['type']]
    start = bv.get('byteOffset', 0) + a.get('byteOffset', 0); stride = bv.get('byteStride') or sz * nc
    if stride == sz * nc:
        arr = np.frombuffer(bin_, dtype=np.dtype('<' + fmt), count=a['count'] * nc, offset=start).reshape(a['count'], nc)
    else:
        arr = np.stack([np.frombuffer(bin_, dtype=np.dtype('<' + fmt), count=nc, offset=start + k * stride) for k in range(a['count'])])
    arr = arr.astype(np.float64)
    if a.get('normalized'):
        arr = arr / {5121: 255.0, 5123: 65535.0, 5120: 127.0, 5122: 32767.0}[a['componentType']]
    return arr


def node_matrix(nd):
    if 'matrix' in nd: return np.array(nd['matrix'], float).reshape(4, 4).T
    M = np.eye(4)
    if 'scale' in nd: M = np.diag(list(nd['scale']) + [1.0]) @ M
    if 'rotation' in nd:
        x, y, z, w = nd['rotation']
        R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                      [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                      [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        R4 = np.eye(4); R4[:3, :3] = R; M = R4 @ M
    if 'translation' in nd: T = np.eye(4); T[:3, 3] = nd['translation']; M = T @ M
    return M


def mesh_nodes(path):
    """every mesh node with its world matrix, ancestor chain and triangles in world coordinates (x, y, z)"""
    js, bin_ = read_glb(path); out = []
    sc = js['scenes'][js.get('scene', 0)]
    def walk(i, M, chain):
        nd = js['nodes'][i]; W = M @ node_matrix(nd); ch = chain + [nd]
        if 'mesh' in nd and 'EXT_mesh_gpu_instancing' not in nd.get('extensions', {}):
            tris = []
            for pr in js['meshes'][nd['mesh']]['primitives']:
                if pr.get('mode', 4) != 4: continue
                P = accessor(js, bin_, pr['attributes']['POSITION'])
                I = accessor(js, bin_, pr['indices']).astype(np.int64).reshape(-1, 3) if 'indices' in pr else np.arange(len(P)).reshape(-1, 3)
                Pw = P @ W[:3, :3].T + W[:3, 3]
                tris.append(Pw[I])
            if tris: out.append(dict(name=nd.get('name', ''), extras=nd.get('extras', {}), chain=ch, tris=np.concatenate(tris)))
        for c in nd.get('children', []): walk(c, W, ch)
    for r in sc['nodes']: walk(r, np.eye(4), [])
    return out


def lod_of(rec):
    import re
    for nd in reversed(rec['chain']):
        ex = nd.get('extras') or {}
        if isinstance(ex.get('lod'), int): return ex['lod']
        m = re.match(r'^LOD(\d)', nd.get('name', '')) or re.match(r'^L(\d)_', nd.get('name', ''))
        if m: return int(m.group(1))
    return 0


def unit_of(group, rec):
    import re
    nm = re.sub(r'^L\d_', '', rec['name'])
    if group == 'tower': return 'tower'
    if group == 'itb':
        if rec['name'].startswith('L2_'): return '*'
        return 'BA-A' if nm.startswith('ba_a') else 'BA-G' if nm.startswith('ba_g') else 'hall'
    if group == 'domestic':
        b = rec['extras'].get('building')
        return b if b else '*'
    if group == 'landside':
        # the building node is the root's direct child
        return rec['chain'][1].get('name') if len(rec['chain']) > 1 else '*'
    return '*'


def plan_geom(tris):
    """union of the plan (x, z) projections of the triangles; degenerate (vertical) ones as 0.05 m strips"""
    xz = tris[:, :, [0, 2]]
    a = 0.5 * np.abs((xz[:, 1, 0] - xz[:, 0, 0]) * (xz[:, 2, 1] - xz[:, 0, 1]) - (xz[:, 2, 0] - xz[:, 0, 0]) * (xz[:, 1, 1] - xz[:, 0, 1]))
    big = a > 1e-4
    polys = list(shapely.polygons(xz[big])) if big.any() else []
    flat = xz[~big]
    if len(flat):
        # longest edge of each degenerate triangle
        d = [np.linalg.norm(flat[:, i] - flat[:, j], axis=1) for i, j in ((0, 1), (1, 2), (0, 2))]
        k = np.argmax(np.stack(d, 1), 1)
        ij = np.array([(0, 1), (1, 2), (0, 2)])[k]
        segs = np.stack([flat[np.arange(len(flat)), ij[:, 0]], flat[np.arange(len(flat)), ij[:, 1]]], 1)
        L = np.linalg.norm(segs[:, 1] - segs[:, 0], axis=1); segs = segs[L > 0.02]
        if len(segs): polys += list(shapely.buffer(shapely.linestrings(segs), 0.025, cap_style='flat'))
    if not polys: return Polygon()
    g = shapely.union_all(shapely.make_valid(np.array(polys, dtype=object)), grid_size=0.01)
    return g.buffer(0.02, join_style='mitre').simplify(0.02)


# ------------------------------------------------------------------------------------------------ footprints
def footprints(log):
    F = {}  # group -> unit -> lod -> {'geom', 'y'}
    TR = {}  # group -> all triangles (every LOD and file; x, y, z) for the height-aware occupancy tests
    TU = {}  # (group, unit) -> LOD0 / LOD1 triangles (the audit tiers)
    files = {}
    for g in GROUPS:
        F[g] = {}; TR[g] = []
        for fn in FILES[g]:
            p = os.path.join(D3, fn)
            if not os.path.exists(p): continue
            files[fn] = dict(bytes=os.path.getsize(p), sha1=hashlib.sha1(open(p, 'rb').read()).hexdigest()[:12])
            t0 = time.time(); recs = mesh_nodes(p)
            # per (unit, lod): stack the triangles; LOD0 / LOD1 share shell meshes, the union absorbs the duplicates
            acc = {}
            for r in recs:
                key = (unit_of(g, r), lod_of(r)); acc.setdefault(key, []).append(r['tris'])
            for (u, l), T in acc.items():
                T = np.concatenate(T); geom = plan_geom(T); TR[g].append((u, T)); TU.setdefault((g, u), []).append(T) if l < 2 else None
                ent = F[g].setdefault(u, {}).setdefault(l, dict(geom=Polygon(), y=[1e9, -1e9], files=[]))
                ent['geom'] = unary_union([ent['geom'], geom]) if not ent['geom'].is_empty else geom
                ent['y'] = [min(ent['y'][0], float(T[:, :, 1].min())), max(ent['y'][1], float(T[:, :, 1].max()))]
                if fn not in ent['files']: ent['files'].append(fn)
            log(f'  {fn}: {len(recs)} mesh nodes, {sum(len(r["tris"]) for r in recs)} tris, {time.time() - t0:.1f} s')
        # solid units (buildings stand on grade: everything under their roofs is occupied) -> max-extent footprint;
        # elevated units (the AirTrain guideway tiles: deck on T-piers, open below) -> triangles for the band test
        TA = np.concatenate([T for u, T in TR[g]])
        el = [T for u, T in TR[g] if elevated(g, u)]
        solid = [unary_union([e['geom'] for e in L.values()]) for u, L in F[g].items() if not elevated(g, u)]
        T = np.concatenate(el) if el else np.zeros((0, 3, 3))
        TR[g] = dict(solid=unary_union(solid) if solid else Polygon(), T=T, lo=T[:, :, [0, 2]].min(1) if len(T) else np.zeros((0, 2)), hi=T[:, :, [0, 2]].max(1) if len(T) else np.zeros((0, 2)), ylo=T[:, :, 1].min(1) if len(T) else np.zeros(0), yhi=T[:, :, 1].max(1) if len(T) else np.zeros(0))
        TR[g]['all'] = dict(T=TA, lo=TA[:, :, [0, 2]].min(1), hi=TA[:, :, [0, 2]].max(1), ylo=TA[:, :, 1].min(1), yhi=TA[:, :, 1].max(1))
        shapely.prepare(TR[g]['solid'])
    TR['_units'] = {k: np.concatenate(v) for k, v in TU.items()}
    return F, TR, files


def elevated(g, u):
    return g == 'landside' and u.startswith('airtrain')


def occupancy(TR, g, bounds, y0, y1, pad=6.0, tri_only=False):
    """plan region where asset group g occupies the height band (y0, y1) (world y), within bounds + pad: the footprints
    of its solid units (a building is occupied from grade to its roof) plus the elevated units' triangles that meet the
    band (the guideway deck and trough walls; a skybridge passing under or over the deck is not occupied).
    tri_only: every unit by its triangles meeting the band (surfaces only, for asset-vs-asset contact)"""
    R = TR[g]['all'] if tri_only else TR[g]; x0, z0, x1, z1 = bounds
    box = shapely.box(x0 - pad, z0 - pad, x1 + pad, z1 + pad)
    out = [R['solid'].intersection(box)] if not tri_only and not R['solid'].is_empty else []
    if len(R['T']):
        m = (R['hi'][:, 0] > x0 - pad) & (R['lo'][:, 0] < x1 + pad) & (R['hi'][:, 1] > z0 - pad) & (R['lo'][:, 1] < z1 + pad) & (R['yhi'] > y0 + 0.05) & (R['ylo'] < y1 - 0.05)
        if m.any(): out.append(plan_geom(R['T'][m]))
    out = [o for o in out if not o.is_empty]
    return unary_union(out) if out else Polygon()


# ------------------------------------------------------------------------------------------------ replacement table
def ring_poly(rings):
    p = Polygon(rings[0], rings[1:] if len(rings) > 1 else None)
    return p if p.is_valid else p.buffer(0)


def replacement(F, TR, log):
    """which first-pass app building each asset replaces. Coverage is height-aware: the asset's triangles whose height
    range meets the old element's own band (walkways G+6..G+10.5, ramp-level walls G..G+5, parts / structures from
    grade to their top), projected to plan and buffered by COVER_BUF (EDGE_BUF for wall edges). Piers, halls and
    structures (garages, stations, hotel, hangar, tower, guideway) go wholly to the group covering >= COVER_MIN of them.
    Elevated walkways are clipped instead: the part goes to the group (hidden once the asset is shown) and the piece
    outside the asset's occupancy (- 0.3 m, slivers < 3 m wide dropped) stays as `rest` rings, so a skybridge that
    enters a garage or crosses the guideway at another height keeps its open span."""
    B = json.load(open(os.path.join(ROOT, 'data', 'sfo_buildings.json')))
    A = json.load(open(os.path.join(ROOT, 'data', 'sfo_airport.json')))
    G = GROUND_Y
    GP = {g: unary_union([e['geom'] for L in F[g].values() for e in L.values()]).buffer(COVER_BUF) for g in GROUPS}
    for g in GROUPS: shapely.prepare(GP[g])
    def occ_all(geo, y0, y1):
        return {g: occupancy(TR, g, geo.bounds, y0, y1) for g in GROUPS}
    def cover(geo, y0, y1, buf=COVER_BUF):
        if geo.is_empty or geo.area < 1e-6: return None, 0.0, {}, {}
        O = occ_all(geo, y0, y1)
        fr = {g: geo.intersection(O[g].buffer(buf)).area / geo.area if not O[g].is_empty else 0.0 for g in GROUPS}
        g = max(fr, key=fr.get); return (g if fr[g] >= COVER_MIN else None), fr[g], fr, O
    rep = dict(parts=[], structures=[], complexEdges={}, atc=None, rail=None)
    table = []
    for i, p in enumerate(B['parts']):
        geo = ring_poly(p['rings'])
        y0, y1 = (G + (p.get('y0') or 6), G + p['h']) if p['kind'] == 'walkway' else (G, G + p['h'] + 0.6)
        g, f, fr, O = cover(geo, y0, y1, COVER_BUF if p['kind'] != 'walkway' else 0.3)
        rest = None
        if p['kind'] == 'walkway':
            occ = unary_union([O[k] for k in GROUPS if not O[k].is_empty])
            fw = geo.intersection(occ.buffer(0.3)).area / geo.area if not occ.is_empty else 0.0
            if fw < 0.02: g = None
            else:
                g = max(fr, key=fr.get)
                r = geo.difference(occ.buffer(0.3)) if not occ.is_empty else geo
                keep = [q for q in (getattr(r, 'geoms', None) or [r]) if isinstance(q, Polygon) and q.area > 2.0 and not q.buffer(-1.5).is_empty]
                rest = [rings_of(q, 0.05)[0] for q in keep if rings_of(q, 0.05)]
                f = fw
        table.append(('part', i, p['kind'], p['name'], g, round(f, 3), {k: round(v, 3) for k, v in fr.items() if v > 0.01}, len(rest) if rest is not None else None))
        if g: rep['parts'].append([i, p['name'], g] + ([rest] if rest else []))
    for ri, r in enumerate(B['complex']):
        runs = []; n = len(r); ring = LineString(list(r) + [r[0]])
        O = occ_all(ring, G, G + 5.0); OE = {k: O[k].buffer(EDGE_BUF) for k in GROUPS}
        for k in GROUPS: shapely.prepare(OE[k])
        Lg = {k: 0.0 for k in GROUPS}; L = 0.0
        for i in range(n):
            a, b = r[i], r[(i + 1) % n]; seg = LineString([a, b]); L += seg.length
            if seg.length < 0.05: continue
            fr = {k: seg.intersection(OE[k]).length / seg.length for k in GROUPS}; g = max(fr, key=fr.get)
            g = g if fr[g] >= COVER_MIN else None
            if g:
                Lg[g] += seg.length
                if runs and runs[-1][2] == g and runs[-1][1] == i - 1: runs[-1][1] = i
                else: runs.append([i, i, g])
        rep['complexEdges'][str(ri)] = runs
        table.append(('complex-ring', ri, 'apron-level', 'Terminal complex ramp level (walls G..G+5)', None, round(sum(Lg.values()) / L, 3), {k: round(v / L, 3) for k, v in Lg.items() if v > 0}, None))
    for i, s in enumerate(A['structures']):
        geo = unary_union([ring_poly(pp) for pp in s['polys']])
        if s['kind'] in ('rail', 'airtrain'):
            # the AirTrain guideway slab and the station boxes are the same structures the landside / ITB assets model
            # (elevated: their deck height differs from the first-pass slab), so plan coverage by any unit decides
            fr = {g: geo.intersection(GP[g]).area / geo.area for g in GROUPS}; g = max(fr, key=fr.get); f = fr[g]
            g = g if f >= COVER_MIN else None
        else:
            g, f, fr, O = cover(geo, G, G + 10.0)
        if s['kind'] in ('atc', 'rail'):
            want = 'tower' if s['kind'] == 'atc' else 'landside'; g = g if g == want else None
            if g: rep['atc' if s['kind'] == 'atc' else 'rail'] = g
        elif g: rep['structures'].append([i, s['name'], g])
        table.append(('structure', i, s['kind'], s['name'], g, round(f, 3), {k: round(v, 3) for k, v in fr.items() if v > 0.01}, None))
    log('replacement table (element, index, kind, name, -> group, coverage, coverage by group, kept walkway pieces):')
    for t in table: log('  %-12s %3d %-10s %-44s -> %-9s %.3f %s%s' % (t[0], t[1], t[2], t[3][:44], t[4] or 'KEEP', t[5], t[6], '' if t[7] is None else '  rest %d' % t[7]))
    return rep, table


# ------------------------------------------------------------------------------------------------ plausibility
def plausibility(F, TR, rep, log):
    sys.path.insert(0, os.path.join(ROOT, 'tools', 'stands'))
    import geom as GM
    S = json.load(open(os.path.join(ROOT, 'data', 'sfo_stands.json')))['stands']
    A = json.load(open(os.path.join(ROOT, 'data', 'sfo_airport.json')))
    DT = json.load(open(os.path.join(ROOT, 'data', 'sfo_details.json')))
    # units (group, unit) with all LODs (max extent) and per LOD
    units = []
    for g in GROUPS:
        for u, L in F[g].items():
            for l, e in L.items():
                if not e['geom'].is_empty: units.append((g, u, l, e['geom'], e['y']))
    allu = unary_union([x[3] for x in units]); shapely.prepare(allu)
    res = dict(conflicts=[], notes=[], stats={})
    # a. aircraft envelopes
    env = {s['name']: GM.stand_env(s) for s in S}
    worst = []
    old = unary_union([ring_poly(p) for p in list(A['terminalComplex']) + [q for b in A['boardingAreas'] for q in b['polys']]])
    for s in S:
        e = env[s['name']]; best = (1e9, None)
        for g, u, l, geo, y in units:
            if e.distance(geo) > 40: continue
            ov = e.intersection(geo).area; d = e.distance(geo)
            if ov > 0.5 or d < 2.0: res['conflicts'].append(dict(check='envelope', stand=s['name'], group=g, unit=u, lod=l, overlap_m2=round(ov, 2), dist_m=round(d, 2)))
            elif d < 3.5: res['notes'].append(dict(check='envelope', stand=s['name'], group=g, unit=u, lod=l, dist_m=round(d, 2), old_outline_dist_m=round(e.distance(old), 2)))
            if d < best[0]: best = (d, f'{g}/{u}/LOD{l}')
        worst.append((best[0], s['name'], best[1], round(e.distance(old), 2)))
    worst.sort()
    res['stats']['nearest_envelopes'] = [dict(stand=n, dist_m=round(d, 2), unit=w, old_outline_dist_m=o) for d, n, w, o in worst[:8]]
    # b. bridges
    nb = 0
    for s in S:
        for b in s['bridges'] + s.get('bridges_upper', []):
            nb += 1
            wl, rot, tc = GM.bridge_parts(b, b['cab'])
            pv = b.get('rotunda') or b['attach']
            parts = [('docked tunnel+cab', tc)]
            if b.get('stow'): parts.append(('stow tunnel+cab', GM.bridge_parts(b, b['stow'])[2]))
            near = Point(pv).buffer(3.0 + (b.get('rotunda_max_r') or 2.5))
            for tag, geo in parts:
                g2 = geo.difference(near)
                for g, u, l, fp, y in units:
                    if g2.distance(fp) > 5: continue
                    ov = g2.intersection(fp).area
                    # the bridge's own building: the tunnel leaves it from the rotunda; anything inside beyond 3 m of the
                    # rotunda / fixed-walkway end is a clash. Height: tunnels run 3.5-7 m above the apron (gates.js),
                    # footprint y ranges start at grade, so every overlap counts (conservative)
                    if ov > 0.3: res['conflicts'].append(dict(check='bridge', stand=s['name'], gate=b['gate'], door=b['door'], part=tag, group=g, unit=u, lod=l, overlap_m2=round(ov, 2)))
            # fixed walkway + rotunda vs units other than the ones it enters (it starts inside its building)
            fw = unary_union([wl, rot])
            for g, u, l, fp, y in units:
                if fw.distance(fp) > 1: continue
                if fp.contains(Point(b['attach'])) or fp.buffer(3.0).contains(Point(b['attach'])): continue
                ov = fw.intersection(fp).area
                if ov > 0.3: res['notes'].append(dict(check='fixed walkway', stand=s['name'], gate=b['gate'], group=g, unit=u, lod=l, overlap_m2=round(ov, 2)))
    res['stats']['bridges_checked'] = nb
    # c. taxiways
    tw = unary_union([ring_poly(pp) for t in A['taxiways'] for pp in t['polys']]); shapely.prepare(tw)
    for g, u, l, fp, y in units:
        ov = fp.intersection(tw).area
        if ov > 0.5: res['conflicts'].append(dict(check='taxiway polygon', group=g, unit=u, lod=l, overlap_m2=round(ov, 1)))
    cl = unary_union([LineString(c) for c in DT['centerlines'] if len(c) >= 2])
    dmin = {}
    for g, u, l, fp, y in units:
        d = fp.distance(cl); k = (g, u)
        if k not in dmin or d < dmin[k]: dmin[k] = d
    res['stats']['taxiway_centreline_min_m'] = {f'{g}/{u}': round(d, 1) for (g, u), d in sorted(dmin.items(), key=lambda kv: kv[1])}
    for (g, u), d in dmin.items():
        # FAA AC 150/5300-13B Table 4-1 / 4-2 (taxilane object free area, ADG III: 81 ft = 24.7 m wide -> 12.3 m from the
        # centreline): a building closer than that to a centreline the app's traffic uses is reported (only the apron
        # taxilanes between piers come close; the stand checks above are the binding ones)
        if d < 12.3: res['notes'].append(dict(check='taxiway centreline', group=g, unit=u, dist_m=round(d, 1), note='< 12.3 m (ADG III taxilane OFA half-width)'))
    # d. groups against each other, height-aware: in the plan overlap of two units of different groups, the plan
    #    occupancy of each group per 2-m height band (triangles meeting the band); the largest band overlap counts.
    #    Strips narrower than 0.6 m are coplanar shared walls (no volume shared)
    ext = {}
    for g, u, l, fp, y in units:
        if u in ('*', 'all'): continue
        k = (g, u); e = ext.setdefault(k, [Polygon(), [1e9, -1e9]]); e[0] = unary_union([e[0], fp]); e[1] = [min(e[1][0], y[0]), max(e[1][1], y[1])]
    ks = list(ext); pairs = []
    for i, a in enumerate(ks):
        for b in ks[i + 1:]:
            if a[0] == b[0]: continue
            A_, B_ = ext[a], ext[b]
            if A_[1][1] < B_[1][0] or B_[1][1] < A_[1][0]: continue
            X = A_[0].intersection(B_[0])
            if X.area < 1.0: continue
            ya, yb = max(A_[1][0], B_[1][0]), min(A_[1][1], B_[1][1]); best = (0.0, None, 0.0, None)
            for y in np.arange(ya, yb, 2.0):
                oa = occupancy(TR, a[0], X.bounds, y, y + 2.0, pad=1.0, tri_only=True).intersection(X)
                if oa.is_empty: continue
                ob = occupancy(TR, b[0], X.bounds, y, y + 2.0, pad=1.0, tri_only=True).intersection(X)
                ov = oa.intersection(ob)
                core = ov.buffer(-0.3).area if not ov.is_empty else 0.0
                if core > best[2]: best = (ov.area, round(float(y), 1), core, [round(c, 1) for c in ov.buffer(-0.3).representative_point().coords[0]] if core > 0 else None)
            pairs.append(dict(a='/'.join(a), b='/'.join(b), plan_overlap_m2=round(X.area, 1), band_overlap_m2=round(best[0], 1), band_y=best[1], core_m2=round(best[2], 1), at_xz=best[3]))
            if best[2] > 2.0: res['conflicts' if best[2] > 20.0 else 'notes'].append(dict(check='asset vs asset (same height band)', a='/'.join(a), b='/'.join(b), core_m2=round(best[2], 1), band_y=best[1], at_xz=best[3]))
    res['stats']['asset_pairs'] = pairs
    # e. what stays of the first-pass buildings (kept parts, walkway rests, kept ramp-level edges, kept structures)
    #    against the assets in their own height band
    B = json.load(open(os.path.join(ROOT, 'data', 'sfo_buildings.json')))
    repd = {r[0]: r for r in rep['parts']}; kept = []
    for i, p in enumerate(B['parts']):
        if i in repd and len(repd[i]) < 4: continue
        geo = unary_union([ring_poly(q) for q in repd[i][3]]) if i in repd else ring_poly(p['rings'])
        y0, y1 = (GROUND_Y + (p.get('y0') or 6), GROUND_Y + p['h']) if p['kind'] == 'walkway' else (GROUND_Y, GROUND_Y + p['h'])
        for g in GROUPS:
            o = occupancy(TR, g, geo.bounds, y0, y1).intersection(geo); core = o.buffer(-0.3).area if not o.is_empty else 0.0
            if core > 0.5: kept.append(dict(part=i, name=p['name'], rest=i in repd, group=g, core_m2=round(core, 1)))
    res['stats']['kept_vs_assets'] = kept
    for k in kept:
        res['notes'].append(dict(check='kept first-pass part vs asset', **k))
    return res


# ------------------------------------------------------------------------------------------------ outputs
def rings_of(geo, tol=0.25):
    geo = geo.simplify(tol)
    polys = [geo] if isinstance(geo, Polygon) else list(getattr(geo, 'geoms', []))
    out = []
    for p in polys:
        if not isinstance(p, Polygon) or p.area < 1.0: continue
        out.append([[[round(x, 2), round(z, 2)] for x, z in p.exterior.coords[:-1]]] + [[[round(x, 2), round(z, 2)] for x, z in h.coords[:-1]] for h in p.interiors if Polygon(h).area > 1.0])
    return out


def tiers(T, geo, y):
    """the unit as two prisms for the 2-D audit (tools/drawing/common.py), which models buildings as footprint x height
    range: `body` = the plan area enclosed by what stands on the ground (triangles within 0.5-3 m above grade: walls,
    columns; their rings filled), from grade to the top; `over` = the rest of the footprint (roof eaves, canopies, the
    flare of the tower, skybridge vestibules), from the lowest triangle over it to the top. Without the split a bridge
    rotunda under a roof eave reads as inside the building."""
    g0 = y[0]
    m = (T[:, :, 1].min(1) < g0 + 3.0) & (T[:, :, 1].max(1) > g0 + 0.5)
    body = Polygon()
    if m.any():
        occ = plan_geom(T[m])
        body = unary_union([Polygon(p.exterior) for p in (getattr(occ, 'geoms', None) or [occ]) if isinstance(p, Polygon) and not p.is_empty])
    body = body.intersection(geo) if not body.is_empty else body
    over = geo.difference(body.buffer(0.05)) if not body.is_empty else geo
    out = []
    if not body.is_empty and body.area > 1.0: out.append(dict(part='body', y=[round(y[0], 2), round(y[1], 2)], rings=rings_of(body, 0.1)))
    # the overhang as height bands of its undersides: every triangle over the overhang is binned by its lowest point
    # (1-m bins, lowest first); a bin claims the part of the overhang its triangles cover that no lower bin claimed, as a
    # prism from the bin's lowest point to the top (an eave over a rotunda is not the vestibule beside it)
    if over.is_empty or over.area < 0.5: return out
    lo, hi = T[:, :, [0, 2]].min(1), T[:, :, [0, 2]].max(1); x0, z0, x1, z1 = over.bounds
    mm = (hi[:, 0] > x0) & (lo[:, 0] < x1) & (hi[:, 1] > z0) & (lo[:, 1] < z1) & (T[:, :, 1].min(1) > g0 + 0.5)
    Tm = T[mm]; yl = Tm[:, :, 1].min(1); claimed = Polygon()
    for b0 in np.unique(np.floor(yl)):
        sel = Tm[(yl >= b0) & (yl < b0 + 1)]
        reg = plan_geom(sel).intersection(over)
        if not claimed.is_empty: reg = reg.difference(claimed)
        reg = unary_union([q for q in (getattr(reg, 'geoms', None) or [reg]) if isinstance(q, Polygon) and q.area > 0.25])
        if reg.is_empty: continue
        claimed = unary_union([claimed, reg])
        rr = rings_of(reg, 0.1)
        if rr: out.append(dict(part='over', y=[round(float(sel[:, :, 1].min()), 2), round(y[1], 2)], rings=rr))
    return out


def merge_manifest(entry, key='integration'):
    """manifest.json#integration under the manifest's file lock (the asset groups own their keys)"""
    import fcntl
    path = os.path.join(D3, 'manifest.json')
    with open(path + '.lock', 'a') as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        cur = json.load(open(path)); cur[key] = entry
        tmp = path + '.' + key + '.tmp'
        with open(tmp, 'w') as f: json.dump(cur, f, indent=1)
        os.replace(tmp, path)
        fcntl.flock(lf, fcntl.LOCK_UN)
    try: os.remove(path + '.lock')  # as tools/blender/dom_manifest.py merge()
    except OSError: pass


def main(argv):
    check_only = '--check' in argv
    os.makedirs(OUTD, exist_ok=True); lines = []
    def log(s): print(s); lines.append(s)
    t0 = time.time()
    log('footprints from the exported GLBs:')
    F, TR, files = footprints(log)
    rep, table = replacement(F, TR, log)
    res = plausibility(F, TR, rep, log)
    log('plausibility: %d conflicts, %d notes' % (len(res['conflicts']), len(res['notes'])))
    for c in res['conflicts']: log('  CONFLICT ' + json.dumps(c))
    for n in res['notes']: log('  note ' + json.dumps(n))
    log('  nearest aircraft envelopes: ' + json.dumps(res['stats']['nearest_envelopes']))
    log('  nearest taxiway centrelines: ' + json.dumps(dict(list(res['stats']['taxiway_centreline_min_m'].items())[:8])))
    if check_only:
        open(os.path.join(OUTD, 'integration_check.txt'), 'w').write('\n'.join(lines) + '\n')
        return 1 if res['conflicts'] else 0
    man = json.load(open(os.path.join(D3, 'manifest.json')))
    T = man['tower']; an = T.get('anchors', {})
    tw = T.get('integration', {}).get('tower_camera', {})
    # footprints per unit (max extent over the LODs) with height ranges, and the physics set
    fps = {}; phys = []
    for g in GROUPS:
        fps[g] = {}
        for u, L in F[g].items():
            # LOD0 / LOD1 (what is drawn within 1.2-1.6 km); LOD2 (simplified 1-m outlines, drawn beyond that) is checked
            # in the plausibility pass above but not stored: the stand / audit checks work at the near LODs
            Ln = {l: e for l, e in L.items() if l < 2} or L
            geo = unary_union([e['geom'] for e in Ln.values()]); y = [min(e['y'][0] for e in Ln.values()), max(e['y'][1] for e in Ln.values())]
            lods = sorted(Ln)
            fps[g][u] = dict(y=[round(y[0], 2), round(y[1], 2)], lods=lods, area_m2=round(geo.area, 1), rings=rings_of(geo, 0.1))
            TT = TR['_units'].get((g, u))
            if TT is not None and u not in ('*', 'all'): fps[g][u]['tiers'] = tiers(TT, geo, y)
            if u == '*': continue  # joined LOD2 nodes: their extent is inside the per-unit footprints (checked above)
            if g == 'landside' and u in HANGARS: continue
            if g == 'landside' and u.startswith('airtrain'): continue  # elevated guideway: aircraft never reach it (landside)
            phys += rings_of(geo, 0.5)
    out = dict(
        about='Integration of data/buildings3d/*.glb into the app (tools/blender/b3d_integrate.py; docs/research/buildings3d.md, integration section)',
        generated=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), files=files,
        rules=dict(cover_buffer_m=COVER_BUF, edge_buffer_m=EDGE_BUF, cover_min=COVER_MIN, hangars_not_blocking=sorted(HANGARS)),
        replace=rep,
        tower=dict(axis_world_xz=T['placement']['root_translation'][0::2], eye_world=tw.get('eye_world'), cab_eye_h=an.get('cab_eye_h'), cab_floor_h=an.get('cab_floor_h'),
                   glass_h=[an.get('glass_sill_h'), an.get('glass_head_h')], glass_head_r=an.get('glass_head_r'), cab_centre_world_xz=an.get('cab_centre_world_xz'), family=T.get('default'), family_decided=T.get('family_decided'),
                   note='fallback (default family); the loader takes the eye and the in-cab bounds from the loaded tower file\'s root extras.anchors and sets world.towerPos (x, z) and towerPos.eyeY (js/live/app.js tower view)'),
        table=[dict(el=t[0], i=t[1], kind=t[2], name=t[3], group=t[4], cover=t[5], by=t[6], rest=t[7]) for t in table],
        footprints=fps, plausibility=res)
    out['physics'] = dict(rings=phys, note='blocking footprints for js/live/ground.js buildingGrid (not wired: the realtime tools import ground.js; hangars and the elevated guideway excluded as the app excludes hangars and rail)')
    json.dump(out, open(os.path.join(D3, 'integration.json'), 'w'), indent=None, separators=(',', ':'))
    js = dict(replace=rep, tower=out['tower'])
    with open(os.path.join(D3, 'integration.js'), 'w') as f:
        f.write('// Generated by tools/blender/b3d_integrate.py from data/buildings3d/*.glb + manifest.json (do not edit). The\n'
                '// first-pass app buildings each Blender asset replaces (routed into their own items by js/live/world.js so the\n'
                '// three.js renderer can hide them once the asset is shown, js/three/buildings3d.js) and the tower camera anchor.\n'
                '// Footprints, the physics set and the plausibility results are in integration.json.\n')
        f.write('export const B3D_INTEGRATION = ' + json.dumps(js, separators=(',', ':')) + ';\n')
    open(os.path.join(OUTD, 'integration_report.txt'), 'w').write('\n'.join(lines) + '\n')
    nrest = sum(len(e[3]) for e in rep['parts'] if len(e) > 3)
    merge_manifest(dict(
        loader='js/three/buildings3d.js (GLTFLoader from vendor/three/three.module.js, tools/build3/three-entry.js); hooks: js/three/renderer3.js, js/live/world.js, js/live/airport.js, js/live/terminals.js',
        files=dict(full=['data/buildings3d/' + f + '.glb' for f in ('tower', 'itb', 'domestic', 'landside')], phone_lod2=['data/buildings3d/' + f + '_lod2.glb' for f in ('tower', 'itb', 'domestic', 'landside')],
                   tower_f1='data/buildings3d/tower_f1.glb (?b3dtower=f1; tower.glb is F2)', table='data/buildings3d/integration.js (app) / integration.json (footprints, plausibility)'),
        replaces=dict(parts=len(rep['parts']), walkway_rest_pieces=nrest, structures=len(rep['structures']), atc=rep['atc'], rail=rep['rail'],
                      complex_edge_runs=sum(len(v) for v in rep['complexEdges'].values())),
        plausibility=dict(conflicts=len(res['conflicts']), notes=len(res['notes']), nearest_envelopes=res['stats']['nearest_envelopes'][:3], bridges_checked=res['stats']['bridges_checked']),
        generated=out['generated'], tool='tools/blender/b3d_integrate.py', doc='docs/research/buildings3d.md (integration section)'))
    log('wrote data/buildings3d/integration.json (%.0f kB), integration.js (%.0f kB) in %.0f s' % (os.path.getsize(os.path.join(D3, 'integration.json')) / 1e3, os.path.getsize(os.path.join(D3, 'integration.js')) / 1e3, time.time() - t0))
    return 1 if res['conflicts'] else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
