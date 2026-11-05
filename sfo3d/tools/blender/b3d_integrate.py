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
GROUPS = ['tower', 'itb', 'domestic', 'roadways', 'landside']
FILES = {'tower': ['tower.glb', 'tower_f1.glb', 'tower_lod2.glb'], 'itb': ['itb.glb', 'itb_lod2.glb'],  # tower.glb = F2 (default), tower_f1.glb = F1
         'domestic': ['domestic.glb', 'domestic_lod2.glb'], 'roadways': ['roadways.glb', 'roadways_lod2.glb'],  # roadways: tools/blender/build_roadways.py (review r1)
         'landside': ['landside.glb', 'landside_lod2.glb']}
# groups that replace first-pass app buildings (the roadways replace nothing: the app drew no elevated roads)
REPL_GROUPS = ['tower', 'itb', 'domestic', 'landside']
COVER_BUF, EDGE_BUF, COVER_MIN = 2.0, 3.0, 0.5
# review round 1 (finding 3): a ramp-level wall edge not covered within EDGE_BUF but within EDGE_GAP of the group that
# covers the edges next to it (a gap in a run, or the run's continuation in front of a set-back facade: the ITB west wall
# stands 4-6 m behind the SFO Museum ring, which follows the curb) goes to that group too
EDGE_GAP = 8.0
# review round 1 (finding 7): building to taxilane-centreline distance per the lane's design group (FAA AC 150/5300-13A
# Table 4-1, taxilane centreline to fixed or movable object = half the taxilane OFA: ADG II 57.5 ft, III 81, IV 112.5,
# V 138, VI 167.5 ft); a lane's group is the largest of the stands it serves (stands whose envelope is within LANE_SERVE_M),
# by wingspan (ADG II < 79 ft, III < 118, IV < 171, V < 214, VI < 262 ft; AC 150/5300-13A Table 1-1)
ADG_CL_OBJ = {2: 17.5, 3: 24.7, 4: 34.3, 5: 42.1, 6: 51.1}
ADG_SPAN = [(24.0, 2), (36.0, 3), (52.0, 4), (65.0, 5), (80.0, 6)]
LANE_SERVE_M = 45.0
# review round 1 (finding 6): fixed walkway and rotunda drum vs the building they serve, in their own height band (gates.js:
# walkway floor DEPARTURE_LEVEL 5.4 m at the building .. the rotunda floor, WALK_H 3.0 m tall; the drum from grade to the
# walkway roof); the facade crossing allowed: the first WALK_ENTRY_M of the walkway from its start (tools/stands/geom.py walk)
WALK_BAND = (4.2, 8.6); DRUM_BAND = (0.3, 8.6); WALK_ENTRY_M = 2.5
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
            tris = []; mats = []
            for pr in js['meshes'][nd['mesh']]['primitives']:
                if pr.get('mode', 4) != 4: continue
                P = accessor(js, bin_, pr['attributes']['POSITION'])
                I = accessor(js, bin_, pr['indices']).astype(np.int64).reshape(-1, 3) if 'indices' in pr else np.arange(len(P)).reshape(-1, 3)
                Pw = P @ W[:3, :3].T + W[:3, 3]
                tris.append(Pw[I]); mats += [js['materials'][pr['material']].get('name', '') if 'material' in pr else ''] * len(I)
            if tris: out.append(dict(name=nd.get('name', ''), extras=nd.get('extras', {}), chain=ch, tris=np.concatenate(tris), mats=np.array(mats)))
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
        return b if b and b != 'all' else '*'  # the joined LOD2 mesh carries building 'all' (split per building below)
    if group == 'landside':
        # the building node is the root's direct child
        return rec['chain'][1].get('name') if len(rec['chain']) > 1 else '*'
    if group == 'roadways':
        b = rec['extras'].get('building')
        return b if b else '*'
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
SPLIT_MARGIN = 1.0   # m: the joined LOD2 meshes are split by containment in each unit's LOD0 / LOD1 footprint + this


def footprints(log):
    F = {}  # group -> unit -> lod -> {'geom', 'y'}
    TR = {}  # group -> all triangles (every LOD and file; x, y, z) for the height-aware occupancy tests
    TU = {}  # (group, unit) -> LOD0 / LOD1 triangles (the audit tiers)
    TL = {}  # (group, unit, lod) -> triangles (walkway / drum vs host, per LOD)
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
            # review round 1 (finding 6): the joined LOD2 meshes ('*', what phones showed at every distance) split per
            # building (each triangle to the unit whose LOD0 / LOD1 footprint holds its centroid, else the nearest within
            # 6 m), so the asset-vs-asset and walkway / drum checks see the LOD2 outline of each building
            if ('*', 2) in acc and len([u for (u, l) in acc if u != '*']) or ('*', 2) in acc and F[g]:
                Tj = np.concatenate(acc.pop(('*', 2)))
                near = {u: unary_union([e['geom'] for l, e in L.items() if l < 2]) for u, L in F[g].items() if u != '*'}
                for (u, l), T in list(acc.items()):
                    if u != '*' and l < 2 and u not in near: near[u] = plan_geom(np.concatenate(T))
                if near:
                    # review round 2 (finding 6): by containment, not by centroid-in-first-footprint: a triangle goes to
                    # the unit whose LOD0 / LOD1 footprint + SPLIT_MARGIN holds all three of its vertices (several: the one
                    # whose own footprint holds the centroid, else the smallest); the round-1 rule handed big T1 roof
                    # triangles whose centroid fell in BA-C's footprint to BA-C (its "top +9 m")
                    names = list(near); geoms = [near[u] for u in names]
                    cen = shapely.points(Tj[:, :, [0, 2]].mean(1)); own = np.full(len(Tj), -1)
                    V = Tj[:, :, [0, 2]].reshape(-1, 2); ok = np.zeros((len(Tj), len(geoms)), bool); inc = np.zeros((len(Tj), len(geoms)), bool)
                    for k, gg in enumerate(geoms):
                        gb = gg.buffer(SPLIT_MARGIN); shapely.prepare(gb); shapely.prepare(gg)
                        ok[:, k] = shapely.contains_xy(gb, V[:, 0], V[:, 1]).reshape(-1, 3).all(1); inc[:, k] = shapely.contains(gg, cen)
                    area = np.array([g_.area for g_ in geoms])
                    for i in np.nonzero(ok.any(1))[0]:
                        ks = np.nonzero(ok[i])[0]
                        if len(ks) == 1: own[i] = ks[0]; continue
                        kc = [k for k in ks if inc[i, k]]
                        own[i] = kc[0] if len(kc) == 1 else ks[np.argmin(area[ks])]
                    for k, gg in enumerate(geoms): own[(own < 0) & inc[:, k]] = k   # straddling triangles: by centroid
                    rest = np.nonzero(own < 0)[0]
                    if len(rest):
                        d = np.stack([shapely.distance(gg, cen[rest]) for gg in geoms], 1); k = d.argmin(1)
                        own[rest] = np.where(d[np.arange(len(rest)), k] < 6.0, k, -1)
                    for k, u in enumerate(names):
                        if (own == k).any(): acc.setdefault((u, 2), []).append(Tj[own == k])
                    if (own < 0).any(): acc[('*', 2)] = [Tj[own < 0]]
                else: acc[('*', 2)] = [Tj]
            for (u, l), T in acc.items():
                T = np.concatenate(T); geom = plan_geom(T); TR[g].append((u, T)); TU.setdefault((g, u), []).append(T) if l < 2 else None
                TL.setdefault((g, u, l), []).append(T)
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
    TR['_lods'] = {k: np.concatenate(v) for k, v in TL.items()}
    return F, TR, files


WALL_MIN_M2 = 1.0   # enclosure test: wall triangles at least this large [our choice: the shells' wall quads are 10-500 m2]


def axis_hits(T, P, ax):
    """for each point of P (n, 3), the triangles of T (m, 3, 3) crossed by the line through the point along axis ax
    (0 = x, 1 = y, 2 = z): the number of crossings on the + side and on the - side of the point (axis-aligned rays:
    a 2-D point-in-triangle test in the plane of the other two axes, then the crossing coordinate by barycentrics)"""
    b, c = [k for k in (0, 1, 2) if k != ax]
    A2 = T[:, :, [b, c]]; lo, hi = A2.min(1), A2.max(1)
    plus = np.zeros(len(P), int); minus = np.zeros(len(P), int)
    for i, p in enumerate(P):
        m = (lo[:, 0] <= p[b]) & (hi[:, 0] >= p[b]) & (lo[:, 1] <= p[c]) & (hi[:, 1] >= p[c])
        if not m.any(): continue
        t = T[m]; a0, a1, a2 = t[:, 0], t[:, 1], t[:, 2]
        v0 = a2[:, [b, c]] - a0[:, [b, c]]; v1 = a1[:, [b, c]] - a0[:, [b, c]]; v2 = np.array([p[b], p[c]]) - a0[:, [b, c]]
        d00 = (v0 * v0).sum(1); d01 = (v0 * v1).sum(1); d11 = (v1 * v1).sum(1); d20 = (v2 * v0).sum(1); d21 = (v2 * v1).sum(1)
        den = d00 * d11 - d01 * d01; ok = np.abs(den) > 1e-12
        uu = np.where(ok, (d11 * d20 - d01 * d21) / np.where(ok, den, 1), -1); vv = np.where(ok, (d00 * d21 - d01 * d20) / np.where(ok, den, 1), -1)
        ins = ok & (uu >= 0) & (vv >= 0) & (uu + vv <= 1)
        if not ins.any(): continue
        x = (a0[:, ax] + uu * (a2[:, ax] - a0[:, ax]) + vv * (a1[:, ax] - a0[:, ax]))[ins]
        plus[i] = int((x > p[ax]).sum()); minus[i] = int((x < p[ax]).sum())
    return plus, minus


def enclosed(T, P, max_gap_deg=45.0):
    """review round 2 (finding 3): points of P (world, n x 3) that lie INSIDE the building whose triangles are T: a roof
    (any triangle) above and walls all around (eight horizontal rays, no open sector wider than max_gap_deg). Hits, not
    parity: the exported shells are not closed (door gaps, shared walls, open undersides). A road beside a facade or under
    a curb canopy sees the building over at most ~180 deg: outside; a deck running through the hall sees it all round."""
    if not len(P) or not len(T): return np.zeros(len(P), bool)
    up, _ = axis_hits(T, P, 1)
    # walls only for the side tests: near-vertical triangles of >= WALL_MIN_M2 (a curtain wall, a shell band); the slim
    # structure around a roof overhang (the ITB's cantilevered columns, column fans and canopy hangers over its curb)
    # is made of small tube facets and does not enclose anything
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); a = 0.5 * np.linalg.norm(n, axis=1)
    W = T[(np.abs(n[:, 1]) < 0.3 * (2 * a + 1e-12)) & (a >= WALL_MIN_M2)]
    # eight horizontal directions (each rotation gives a ray pair): enclosed = no open sector wider than max_gap_deg
    # (a point beside a straight facade has >= 180 deg open, in a concave corner of two buildings under a canopy 90 deg;
    # inside a shell with a door gap, <= 45 deg)
    hit = np.zeros((len(P), 8), bool)
    for k, th in enumerate(np.radians([0.0, 45.0, 90.0, 135.0])):
        c, s_ = math.cos(th), math.sin(th)
        def rot(A):
            B = A.copy(); B[..., 0] = c * A[..., 0] + s_ * A[..., 2]; B[..., 2] = -s_ * A[..., 0] + c * A[..., 2]; return B
        pl, mi = axis_hits(rot(W), rot(P), 0)
        hit[:, k] = pl > 0; hit[:, k + 4] = mi > 0
    order = [0, 1, 2, 3, 4, 5, 6, 7]   # directions th, th + 45 ... th + 315 (the - rays of k are at th_k + 180)
    gap = np.zeros(len(P), int); run = np.zeros(len(P), int)
    for j in order + order:          # longest run of directions without a hit, cyclic
        run = np.where(hit[:, j], 0, run + 1); gap = np.maximum(gap, run)
    return (up > 0) & (gap * 45.0 <= max_gap_deg)


def elevated(g, u):
    # decks on columns, open below: occupied only where their triangles are (the guideway; the roadways, review r1)
    return (g == 'landside' and u.startswith('airtrain')) or g == 'roadways'


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
    GROUPS = REPL_GROUPS
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
    gap_log = []
    for ri, r in enumerate(B['complex']):
        runs = []; n = len(r); ring = LineString(list(r) + [r[0]]); gap_from = set()
        O = occ_all(ring, G, G + 5.0); OE = {k: O[k].buffer(EDGE_BUF) for k in GROUPS}
        for k in GROUPS: shapely.prepare(OE[k])
        Lg = {k: 0.0 for k in GROUPS}; L = 0.0; eg = [None] * n; segs = []
        for i in range(n):
            a, b = r[i], r[(i + 1) % n]; seg = LineString([a, b]); L += seg.length; segs.append(seg)
            if seg.length < 0.05: continue
            fr = {k: seg.intersection(OE[k]).length / seg.length for k in GROUPS}; g = max(fr, key=fr.get)
            eg[i] = g if fr[g] >= COVER_MIN else None
        # gap rule (EDGE_GAP, review r1 finding 3): uncovered edges next to a group's edges, within EDGE_GAP of it
        OG = {k: O[k].buffer(EDGE_GAP) for k in GROUPS}
        for k in GROUPS: shapely.prepare(OG[k])
        gap_added = 0
        for _ in range(n):
            ch = False
            for i in range(n):
                if eg[i] is not None or segs[i].length < 0.05: continue
                for j in ((i - 1) % n, (i + 1) % n):
                    g = eg[j]
                    if g and segs[i].intersection(OG[g]).length / segs[i].length >= COVER_MIN: eg[i] = g; gap_from.add(i); gap_added += 1; ch = True; break
            if not ch: break
        for i in range(n):
            g = eg[i]
            if not g: continue
            Lg[g] += segs[i].length
            if runs and runs[-1][2] == g and runs[-1][1] == i - 1: runs[-1][1] = i
            else: runs.append([i, i, g])
        if gap_added: gap_log.append((ri, sorted(gap_from), gap_added))
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
    for ri, ix, k in gap_log: log('  ramp-level ring %d: %d edge(s) %s routed by the gap rule (within %.0f m of the group covering their neighbours)' % (ri, k, ix, EDGE_GAP))
    rep['gap_edges'] = {str(ri): ix for ri, ix, k in gap_log}
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
    # b'. (review round 1, finding 6) the fixed walkway and the rotunda drum against the building they serve (the units
    #     whose footprint is within 4 m of the bridge's attach point), at every LOD (LOD2 split per building): the plan area
    #     of that building's surfaces inside each part's volume (its triangles clipped to the part's height band, vertical
    #     ones as 5-cm strips, intersected with the part's plan). The facade crossing is allowed: the first WALK_ENTRY_M
    #     around the attach point (vestibules / door surrounds). Parts: the app's own bridge solids at every pose
    #     (out/buildings3d/integ/draw/scene2d.json, jobs/extract2d.mjs: walkway tube and slabs, pedestal and rotunda drum),
    #     else tools/stands/geom.py bridge_parts (walkway 2.6 m wide, drum r 2.45 m) in WALK_BAND / DRUM_BAND
    scene = None
    for cand in (os.environ.get('SCENE2D'), os.path.join(ROOT, 'out', 'draw', 'scene2d.json'), os.path.join(OUTD, 'draw', 'scene2d.json')):
        if cand and os.path.exists(cand): scene = cand; break
    parts_of = {}
    if scene:
        SC = json.load(open(scene))
        for b in SC['bridges']:
            L = []
            for pk, P_ in b['poses'].items():
                rc = P_['pose'].get('rc') or b.get('rc'); att = P_['pose'].get('attach') or b['attach']
                wline = LineString([att, rc]) if rc and math.dist(att, rc) > 0.5 else None
                for pr in P_['parts']:
                    hull = Polygon(pr['hull']); c = hull.centroid
                    if pr['part'] in ('walkway', 'box') and wline is not None and wline.distance(c) < 2.5: L.append((pk, 'walkway', hull, pr['y']))
                    elif pr['part'] == 'pedestal' or (pr['part'] == 'cyl' and rc and math.dist([c.x, c.y], rc) < 0.6): L.append((pk, 'drum', hull, pr['y']))
            parts_of[(b['stand'], b['gate'], str(b['door']))] = (L, b['attach'])
        res['stats']['bridge_solids'] = os.path.relpath(scene, ROOT) + ' (generated %s, %s)' % (SC['meta'].get('generated'), SC['meta'].get('git'))
    else: res['stats']['bridge_solids'] = 'tools/stands/geom.py bridge_parts (no scene2d.json)'
    def clip_plan(T, y0, y1):
        """plan polygons of the triangles T clipped to y0 <= y <= y1 (vertical pieces as 5-cm strips)"""
        out = []
        for t in T:
            poly = [tuple(v) for v in t]
            for lim, keep in ((y0, lambda v: v[1] >= y0), (y1, lambda v: v[1] <= y1)):
                if not poly: break
                res_ = []
                for k in range(len(poly)):
                    a, b_ = poly[k], poly[(k + 1) % len(poly)]
                    ia, ib = keep(a), keep(b_)
                    if ia: res_.append(a)
                    if ia != ib:
                        f = (lim - a[1]) / (b_[1] - a[1]); res_.append(tuple(a[q] + f * (b_[q] - a[q]) for q in range(3)))
                poly = res_
            if len(poly) < 3: continue
            xz = [(v[0], v[2]) for v in poly]; P_ = Polygon(xz)
            if P_.is_valid and P_.area > 1e-4: out.append(P_)
            else:
                xs = np.array(xz); d = np.linalg.norm(xs[:, None] - xs[None], axis=2); a, b_ = np.unravel_index(d.argmax(), d.shape)
                if d[a, b_] > 0.02: out.append(LineString([xz[a], xz[b_]]).buffer(0.025, cap_style='flat'))
        return unary_union(out) if out else Polygon()
    hosts_of = {}
    for g, u, l, fp, y in units:
        if g in REPL_GROUPS: hosts_of.setdefault((g, u), {})[l] = fp
    wd = []
    for s in S:
        for b in s['bridges'] + s.get('bridges_upper', []):
            key = (s['name'], b['gate'], str(b['door']))
            if key in parts_of: PL, att = parts_of[key]
            else:
                wl, rot, tc = GM.bridge_parts(b, b['cab']); att = b['attach']
                PL = [('model', 'walkway', wl, [GROUND_Y + WALK_BAND[0], GROUND_Y + WALK_BAND[1]])] + ([('model', 'drum', rot, [GROUND_Y + DRUM_BAND[0], GROUND_Y + DRUM_BAND[1]])] if b.get('rotunda') else [])
            at = Point(att); allow = at.buffer(WALK_ENTRY_M)
            host = [(g, u) for (g, u), L in hosts_of.items() if any(fp.distance(at) < 4.0 for fp in L.values())]
            for g, u in host:
                for l in sorted(hosts_of[(g, u)]):
                    T = TR['_lods'].get((g, u, l))
                    if T is None or not len(T): continue
                    lo, hi = T[:, :, [0, 2]].min(1), T[:, :, [0, 2]].max(1); ylo, yhi = T[:, :, 1].min(1), T[:, :, 1].max(1)
                    worst = {'walkway': (0.0, None, 0.0), 'drum': (0.0, None, 0.0)}
                    for pk, kind, hull, (y0, y1) in PL:
                        x0, z0, x1, z1 = hull.bounds
                        m = (hi[:, 0] > x0) & (lo[:, 0] < x1) & (hi[:, 1] > z0) & (lo[:, 1] < z1) & (yhi > y0 + 0.02) & (ylo < y1 - 0.02)
                        if not m.any(): continue
                        o = clip_plan(T[m], y0 + 0.02, y1 - 0.02).intersection(hull)
                        if kind == 'walkway': o = o.difference(allow)
                        a = o.area
                        if a > 0.05:
                            # penetration depth: the farthest point of the overlap from the part's outline
                            pts = shapely.get_coordinates(o); dep = float(shapely.distance(hull.exterior, shapely.points(pts)).max()) if len(pts) else 0.0
                        else: dep = 0.0
                        if a > worst[kind][0]: worst[kind] = (a, pk, dep)
                    rec = dict(stand=s['name'], gate=b['gate'], door=b['door'], group=g, unit=u, lod=l, walkway_m2=round(worst['walkway'][0], 2), walkway_pose=worst['walkway'][1], walkway_depth_m=round(worst['walkway'][2], 2),
                               drum_m2=round(worst['drum'][0], 2), drum_pose=worst['drum'][1], drum_depth_m=round(worst['drum'][2], 2))
                    wd.append(rec)
                    # CONFLICT: > 0.3 m2 of surface inside and deeper than 0.10 m (a wall that only touches the outline is a
                    # contact, e.g. the domestic door surrounds meet the drums by design); NOTE: > 0.3 m2 at <= 0.10 m
                    for kind, lab in (('walkway', 'fixed walkway: host building surfaces inside it (beyond the facade crossing)'), ('drum', 'rotunda drum: host building surfaces inside it')):
                        a, pk, dep = worst[kind]
                        if a > 0.3: res['conflicts' if dep > 0.10 else 'notes'].append(dict(check=lab, stand=s['name'], gate=b['gate'], door=b['door'], group=g, unit=u, lod=l, pose=pk, overlap_m2=round(a, 2), depth_m=round(dep, 2)))
    res['stats']['walkway_drum_vs_host'] = sorted([w for w in wd if w['walkway_m2'] > 0.05 or w['drum_m2'] > 0.05], key=lambda w: -(w['walkway_m2'] + w['drum_m2']))[:60]
    res['stats']['walkway_drum_tests'] = len(wd)
    # c. taxiways
    tw = unary_union([ring_poly(pp) for t in A['taxiways'] for pp in t['polys']]); shapely.prepare(tw)
    for g, u, l, fp, y in units:
        ov = fp.intersection(tw).area
        if ov > 0.5: res['conflicts'].append(dict(check='taxiway polygon', group=g, unit=u, lod=l, overlap_m2=round(ov, 1)))
    # taxilane centreline to building per the lane's design group (ADG_CL_OBJ; review round 1, finding 7: the old 12.3 m
    # was half of 81 ft, itself already the centreline-to-object distance). A lane's ADG = the largest wingspan among the
    # stands it serves (stand envelope within LANE_SERVE_M of the lane), else ADG III (the smallest jet group at SFO)
    CLs = [(i, LineString(c), (DT['centerlineMeta'][i] or {}).get('ref') if i < len(DT.get('centerlineMeta', [])) else None) for i, c in enumerate(DT['centerlines']) if len(c) >= 2]
    def span_of(st):
        t = st.get('largest_type'); r = GM.APP.get(t) if t else None
        return (r or {}).get('span') or 0.0
    lane = []
    for i, ln, ref in CLs:
        spans = [span_of(st) for st in S if env[st['name']].distance(ln) < LANE_SERVE_M]
        sp = max(spans, default=0.0); adg = next((a for lim, a in ADG_SPAN if sp < lim), 6) if sp else 3
        lane.append((i, ln, ref, max(adg, 3), sp))
    # the same place in the SFO Museum geometry: terminal complex, boarding areas and the structures (garages, the AirTrain
    # rail slab, stations, hangars) - what the asset was modelled on
    oldo = unary_union([old] + [ring_poly(pp) for st in A['structures'] for pp in st['polys']])
    dmin = {}
    for g, u, l, fp, y in units:
        if g == 'roadways': continue
        for i, ln, ref, adg, sp in lane:
            d = fp.distance(ln)
            if d > 60: continue
            k = (g, u); need = ADG_CL_OBJ[adg]
            if k not in dmin or d - need < dmin[k]['margin_m']:
                dmin[k] = dict(dist_m=round(d, 1), lane=i, ref=ref, adg=adg, span_m=round(sp, 1), need_m=need, margin_m=round(d - need, 1), museum_outline_m=round(oldo.distance(ln), 1))
    res['stats']['taxilane_clearance'] = {f'{g}/{u}': v for (g, u), v in sorted(dmin.items(), key=lambda kv: kv[1]['margin_m'])}
    res['stats']['taxiway_centreline_min_m'] = {f'{g}/{u}': v['dist_m'] for (g, u), v in sorted(dmin.items(), key=lambda kv: kv[1]['dist_m'])}
    for (g, u), v in dmin.items():
        if v['margin_m'] < 0:
            # a NOTE when the SFO Museum outline is as close (the real building; the asset did not introduce it), else CONFLICT
            if v['museum_outline_m'] <= v['dist_m'] + 0.5: res['notes'].append(dict(check='taxilane OFA (ADG %d)' % v['adg'], group=g, unit=u, **v, note='the surveyed SFO Museum outline is as close: existing condition, not the asset'))
            else: res['conflicts'].append(dict(check='taxilane OFA (ADG %d)' % v['adg'], group=g, unit=u, **v))
    # d. groups against each other, height-aware: in the plan overlap of two units of different groups, the plan
    #    occupancy of each group per 2-m height band (triangles meeting the band); the largest band overlap counts.
    #    Strips narrower than 0.6 m are coplanar shared walls (no volume shared)
    ext = {}
    for g, u, l, fp, y in units:
        if u in ('*', 'all'): continue  # '*' = LOD2 triangles no building claims (split above)
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
    deck_checks(F, TR, res, log)
    return res


ROAD_CLEAR = 4.6   # m, vertical clearance over a road deck (Caltrans HDM 309.2, 15 ft; roadways_net.CLEAR_MIN) [inf]


def deck_points(step=1.0):
    """the roadways' LOD0 road surfaces (materials deck_* / island / kerb_red / paint_*: not parapets, fascia or columns)
    sampled on a ~step-m barycentric grid: (points (n, 3) world, unit name per point, area per point)"""
    p = os.path.join(D3, 'roadways.glb')
    if not os.path.exists(p): return np.zeros((0, 3)), np.array([]), np.zeros(0)
    pts, units, area = [], [], []
    for r in mesh_nodes(p):
        if lod_of(r) != 0: continue
        sel = np.array([m.startswith('deck') or m in ('island', 'kerb_red') or m.startswith('paint') for m in r['mats']], bool)
        for t in r['tris'][sel]:
            k = int(max(1, math.ceil(max(np.linalg.norm(t[1] - t[0]), np.linalg.norm(t[2] - t[1]), np.linalg.norm(t[0] - t[2])) / step)))
            ij = np.array([(i, j) for i in range(k) for j in range(k - i)], float)
            q = t[0] + ((ij[:, :1] + 1 / 3) / k) * (t[1] - t[0]) + ((ij[:, 1:] + 1 / 3) / k) * (t[2] - t[0])   # cell centroids (upright cells)
            a = 0.5 * np.linalg.norm(np.cross(t[1] - t[0], t[2] - t[0]))
            pts.append(q); units += [r['extras'].get('building', '?')] * len(q); area.append(np.full(len(q), a / max(1, k * k)))
    if not pts: return np.zeros((0, 3)), np.array([]), np.zeros(0)
    return np.concatenate(pts), np.array(units), np.concatenate(area)


def deck_checks(F, TR, res, log):
    """review round 2 (findings 3 and 5): the road decks against the buildings as SOLIDS and against everything over them.
      inside   every road-surface point 2 m above the deck tested against each domestic / ITB / tower / landside building
               unit whose footprint holds it (enclosed(): a roof above and walls all round) - the per-2-m-band surface
               test cannot see a deck inside a hollow shell or one crossing a wall; CONFLICT above 1 m2
      clear    the lowest triangle of any other group (and of the roadways themselves, the deck's own parapets and kerbs
               excluded: > 1.0 m up) over each point: CONFLICT below ROAD_CLEAR under the AirTrain guideway or another deck,
               NOTE below it under a building part (curb canopies, eaves: their owner's call)
      curb     along the ITB departures curb (ITB roof frame), the void between the curb top (ITB asset) and the deck top
               (roadways), outward from the kerb, per 0.5 m: CONFLICT above 0.3 m"""
    P, U, A = deck_points()
    st = res['stats']; st['deck_points'] = int(len(P))
    if not len(P): return
    # inside
    ins = {}
    for g in ('domestic', 'itb', 'tower', 'landside'):
        for u, L in F.get(g, {}).items():
            if u in ('*', 'all') or (g == 'landside' and u.startswith('airtrain')): continue
            T = TR['_lods'].get((g, u, 0))
            if T is None: continue
            fp = unary_union([e['geom'] for l, e in L.items() if l < 2] or [e['geom'] for e in L.values()])
            m = shapely.contains_xy(fp, P[:, 0], P[:, 2])
            if not m.any(): continue
            Q = P[m].copy(); Q[:, 1] += 2.0
            e = enclosed(T, Q)
            if e.any():
                ii = np.nonzero(m)[0][e]
                ins['%s/%s' % (g, u)] = dict(area_m2=round(float(A[ii].sum()), 1), units=sorted(set(U[ii].tolist())), at=[round(float(P[ii[0], 0]), 1), round(float(P[ii[0], 2]), 1)])
    st['deck_inside_buildings'] = ins
    for k, v in ins.items():
        res['conflicts' if v['area_m2'] > 1.0 else 'notes'].append(dict(check='road deck inside a building (solid test)', building=k, **v))
    # clearance
    rows = []
    for g in GROUPS:
        if g not in TR: continue
        T = TR[g]['all']['T']
        if g == 'roadways':
            n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); T = T[np.abs(n[:, 1]) > 1e-6]   # decks / soffits, not walls
        xz = T[:, :, [0, 2]]; lo, hi = xz.min(1), xz.max(1)
        cand = (P[:, 0] > lo[:, 0].min()) & (P[:, 0] < hi[:, 0].max()) & (P[:, 2] > lo[:, 1].min()) & (P[:, 2] < hi[:, 1].max())
        for i in np.nonzero(cand)[0]:
            q = P[i]
            mm = (lo[:, 0] <= q[0]) & (hi[:, 0] >= q[0]) & (lo[:, 1] <= q[2]) & (hi[:, 1] >= q[2]) & (T[:, :, 1].max(1) > q[1] + 1.0)
            if not mm.any(): continue
            pl, _ = axis_hits(T[mm], q[None], 1)
            if not pl[0]: continue
            t = T[mm]; a0, a1, a2 = t[:, 0], t[:, 1], t[:, 2]
            v0 = a2[:, [0, 2]] - a0[:, [0, 2]]; v1 = a1[:, [0, 2]] - a0[:, [0, 2]]; v2 = q[[0, 2]] - a0[:, [0, 2]]
            d00 = (v0 * v0).sum(1); d01 = (v0 * v1).sum(1); d11 = (v1 * v1).sum(1); d20 = (v2 * v0).sum(1); d21 = (v2 * v1).sum(1)
            den = d00 * d11 - d01 * d01; ok = np.abs(den) > 1e-12
            uu = np.where(ok, (d11 * d20 - d01 * d21) / np.where(ok, den, 1), -1); vv = np.where(ok, (d00 * d21 - d01 * d20) / np.where(ok, den, 1), -1)
            insd = ok & (uu >= 0) & (vv >= 0) & (uu + vv <= 1)
            y = (a0[:, 1] + uu * (a2[:, 1] - a0[:, 1]) + vv * (a1[:, 1] - a0[:, 1]))[insd]; y = y[y > q[1] + 1.0]
            if len(y): rows.append((float(y.min() - q[1]), g, U[i], float(A[i]), q))
    def summ(sel):
        if not sel: return None
        sel.sort(key=lambda r: r[0]); r0 = sel[0]
        return dict(points=len(sel), min_m=round(r0[0], 2), at=[round(float(r0[4][0]), 1), round(float(r0[4][2]), 1)], deck_m=round(float(r0[4][1]) - GROUND_Y, 2), unit=r0[2],
                    below_m2=round(sum(r[3] for r in sel if r[0] < ROAD_CLEAR), 1))
    guide = [r for r in rows if r[1] == 'landside']   # the AirTrain guideway is the only elevated landside structure over the decks
    st['deck_clearance'] = {g: summ([r for r in rows if r[1] == g]) for g in GROUPS if any(r[1] == g for r in rows)}
    for g, v in st['deck_clearance'].items():
        if v and v['below_m2'] > 0:
            res['conflicts' if g in ('landside', 'roadways') else 'notes'].append(dict(check='vertical clearance over a road deck (< %.1f m)' % ROAD_CLEAR, over=g, **v))
    # the ITB curb
    st['itb_curb_gap'] = itb_curb_gap(P, TR, log)
    if st['itb_curb_gap'] and st['itb_curb_gap']['over_limit'] > 0:
        res['conflicts'].append(dict(check='ITB curb to departures deck void (> 0.3 m)', **st['itb_curb_gap']))
    log('deck checks: %d road-surface points; inside buildings %s; clearance %s; ITB curb %s' % (len(P), {k: v['area_m2'] for k, v in ins.items()} or 'none',
        {g: (v['min_m'], v['below_m2']) for g, v in st['deck_clearance'].items() if v}, st['itb_curb_gap']))


def itb_curb_gap(P, TR, log):
    """the void between the ITB departures curb top and the road deck top, per 0.5 m along the curb (ITB roof frame,
    manifest.json#itb.frame.roof_frame), outward from the kerb face to 12 m: plan polygons of the curb's top triangles
    (ITB LOD0) and of the roadways' LOD0 road-surface triangles within 0.6 m of the curb level"""
    man = json.load(open(os.path.join(D3, 'manifest.json')))
    rf = man['itb']['frame']['roof_frame']; C = np.array(rf['centre_xz'], float); du = np.array(rf['u_axis_xz'], float); du /= np.linalg.norm(du); dv = np.array([du[1], -du[0]])
    T = TR['_lods'].get(('itb', 'hall', 0))
    if T is None or not os.path.exists(os.path.join(D3, 'roadways.glb')): return None
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    flat = (n[:, 1] > 0.95) & (np.ptp(T[:, :, 1], axis=1) < 0.02)
    up = T[flat]; c = up.mean(1)[:, [0, 2]] - C; uvc = np.c_[c @ du, c @ dv]
    cs = up[(uvc[:, 1] < -27.0) & (uvc[:, 1] > -36.0)]                       # the west curb sidewalk tops
    if not len(cs): return None
    hc = float(np.median(cs[:, :, 1])); cs = cs[np.abs(cs[:, :, 1] - hc).max(1) < 0.05]
    curb = unary_union([Polygon(t[:, [0, 2]]).buffer(0.005) for t in cs if Polygon(t[:, [0, 2]]).area > 1e-5])
    D = []
    for r in mesh_nodes(os.path.join(D3, 'roadways.glb')):
        if lod_of(r) != 0: continue
        sel = np.array([m.startswith('deck') or m in ('island', 'kerb_red') for m in r['mats']], bool)
        t = r['tris'][sel]; t = t[np.abs(t[:, :, 1].mean(1) - hc) < 0.6]
        D += [Polygon(x[:, [0, 2]]).buffer(0.005) for x in t if Polygon(x[:, [0, 2]]).area > 1e-5]
    if not D: return None
    both = unary_union([curb] + D)
    cuv = np.c_[(cs.reshape(-1, 3)[:, [0, 2]] - C) @ du, (cs.reshape(-1, 3)[:, [0, 2]] - C) @ dv]
    u0, u1 = cuv[:, 0].min() + 0.5, cuv[:, 0].max() - 0.5; vk = float(cuv[:, 1].min())
    gaps = []
    for u in np.arange(u0, u1, 0.5):
        ln = LineString([tuple(C + du * u + dv * (vk + 0.8)), tuple(C + du * u + dv * (vk - 12.0))])
        cov = ln.intersection(both); segs = [g for g in (getattr(cov, 'geoms', None) or [cov]) if not g.is_empty and g.length > 0]
        ivs = sorted([sorted(float(np.dot(np.array(cc) - C, dv)) for cc in g.coords) for g in segs], key=lambda x: -x[1])
        gap = None
        if ivs:
            lo = ivs[0][0]
            for a, b in ivs[1:]:
                if b < lo - 1e-3: gap = lo - b; break
                lo = min(lo, a)
            if gap is None: gap = max(0.0, min(a for a, b in ivs) - (vk - 12.0))
        else: gap = 12.8
        gaps.append((round(float(u), 1), round(gap, 3)))
    g = np.array([x[1] for x in gaps]); w = max(gaps, key=lambda x: x[1])
    return dict(stations=len(gaps), kerb_v=round(vk, 2), curb_top_m=round(hc - GROUND_Y, 2), max_void_m=float(w[1]), at_u=w[0], over_limit=int((g > 0.3).sum()), limit_m=0.3)


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


def requests_of(res):
    """requests to the other groups, from this run's results (review round 2: the list was hard-coded and kept items the
    groups had closed, and two LOD2 items that were checker artefacts)"""
    out = []
    for c in res['conflicts']:
        if 'drum' in c.get('check', '') or 'walkway' in c.get('check', ''):
            out.append('%s: %s' % (c.get('group', 'domestic'), json.dumps(c)[:300]))
    ins = res['stats'].get('deck_inside_buildings', {})
    out.append('domestic: Terminal 2 landside face (integration review r2, finding 3). NAIP 2024 shows the departures roadway open to the sky, with '
               'traffic, between the modelled T2 west wall and the glass curb canopy, and the T2 roof edge (NAIP relief-corrected for 16.3 m, frame model '
               'draw_data.lean_frame) 17-18 m east of that wall: x -750.5 at z 200, -745 at z 220, -739 at z 240 (+-1 m; the dark line just west of it is the '
               'canopy edge), against the modelled wall at x -768 (z 200) / -756 (z 240): the T2 shell follows the SFO Museum outline over '
               'the curb roadway, as T1 Center did before the domestic round-1 move of its face (manifest.json#domestic.conflicts "T1 Center landside face"). '
               'Please move the T2 landside face to the measured roof edge (the canopy in front of it); roadways.glb is cut where its deck ran inside '
               'the shell (enclosure test, %s m2 of deck) and the cut lifts by itself on the next build_roadways run'
               % ({k: v['area_m2'] for k, v in ins.items()} or 'see build_roadways.json'))
    out.append('landside: parked cars - wheels / skirt at LOD0 and a third shape (review r1 finding 4; landside_cars.py is the landside group\'s)')
    out.append('bridges / realtime: gates.js prepGeom walkway start and drum limits from the 3-D facades (integration.json footprints / tiers), then the domestic vestibules can go (review r1 finding 8)')
    tl = [c for c in res['conflicts'] if c.get('check', '').startswith('taxilane')]
    for c in tl: out.append('%s: %s %.1f m from taxilane centreline %s (ADG %s inferred: %.1f m); SFO Museum outline %.1f m' % (c['group'], c['unit'], c['dist_m'], c['lane'], c['adg'], c['need_m'], c['museum_outline_m']))
    try:
        L2 = json.load(open(os.path.join(OUTD, 'lod2_check.json')))
        if L2.get('flagged'): out.append('LOD2 vs LOD0 (tools/blender/b3d_lod2_check.py, %s): %s' % (L2.get('generated'), '; '.join(L2['flagged'])))
    except (OSError, ValueError): pass
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
            if g == 'roadways': continue  # landside roadways: aircraft never reach them
            phys += rings_of(geo, 0.25)
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
    # physics (review round 1, finding 8): the blocking footprints also go to the app (js/live/app.js buildingGrid extra),
    # simplified to 0.25 m and rounded to 0.1 m (the grid is 2 m)
    phys_js = [[[[round(x, 1), round(z, 1)] for x, z in r] for r in poly] for poly in phys]
    # landside per building (review round 2, finding 4): the unit files and their boxes for js/three/buildings3d.js
    units = {}
    try:
        import b3d_split
        idx = b3d_split.split(log=log); ul = []
        for e in idx:
            L = F['landside'].get(e['unit'])
            if not L: continue
            Ln = {l: v for l, v in L.items() if l < 2} or L
            x0, z0, x1, z1 = unary_union([v['geom'] for v in Ln.values()]).bounds
            y0, y1 = min(v['y'][0] for v in Ln.values()), max(v['y'][1] for v in Ln.values())
            ul.append(dict(unit=e['unit'], file=e['file'], bytes=e['bytes'], switch1_m=e['switch1_m'], switch2_m=e['switch2_m'], box=[round(v, 1) for v in (x0, y0, z0, x1, y1, z1)]))
        units['landside'] = ul
    except Exception as ex:  # the loader falls back to landside.glb when the index is missing
        log('landside split failed (%s): the app loads landside.glb whole' % ex)
    out['units'] = units
    json.dump(out, open(os.path.join(D3, 'integration.json'), 'w'), indent=None, separators=(',', ':'))
    js = dict(replace=rep, tower=out['tower'], units=units, physics=dict(rings=phys_js, note='3-D asset footprints for js/live/ground.js buildingGrid (hangars, guideway, roadways excluded)'))
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
        files=dict(full=['data/buildings3d/' + f + '.glb' for f in ('tower', 'itb', 'domestic', 'roadways', 'landside')], lod2=['data/buildings3d/' + f + '_lod2.glb' for f in ('tower', 'itb', 'domestic', 'roadways', 'landside')],
                   modes='high / ultra: full files; low (phones) and medium: ?b3d=near - the lod2 files first, then each group\'s full file when the camera comes within its LOD2 switch distance (review r1 finding 5)',
                   tower_f1='data/buildings3d/tower_f1.glb (?b3dtower=f1; tower.glb is F2)', table='data/buildings3d/integration.js (app) / integration.json (footprints, plausibility)'),
        replaces=dict(parts=len(rep['parts']), walkway_rest_pieces=nrest, structures=len(rep['structures']), atc=rep['atc'], rail=rep['rail'],
                      complex_edge_runs=sum(len(v) for v in rep['complexEdges'].values())),
        plausibility=dict(conflicts=len(res['conflicts']), notes=len(res['notes']), nearest_envelopes=res['stats']['nearest_envelopes'][:3], bridges_checked=res['stats']['bridges_checked'],
                          conflict_list=res['conflicts'][:20], walkway_drum_tests=res['stats'].get('walkway_drum_tests'), bridge_solids=res['stats'].get('bridge_solids'),
                          taxilane=list(res['stats'].get('taxilane_clearance', {}).items())[:5],
                          deck_inside_buildings=res['stats'].get('deck_inside_buildings'), deck_clearance=res['stats'].get('deck_clearance'), itb_curb_gap=res['stats'].get('itb_curb_gap')),
        requests=requests_of(res),
        generated=out['generated'], tool='tools/blender/b3d_integrate.py', doc='docs/research/buildings3d.md (integration section)'))
    log('wrote data/buildings3d/integration.json (%.0f kB), integration.js (%.0f kB) in %.0f s' % (os.path.getsize(os.path.join(D3, 'integration.json')) / 1e3, os.path.getsize(os.path.join(D3, 'integration.js')) / 1e3, time.time() - t0))
    return 1 if res['conflicts'] else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
