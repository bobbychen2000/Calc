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
FP_JS_GROUPS = ['tower', 'itb', 'domestic']   # per-building footprints with height bands in integration.js (close-out r3, integration-5)
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


ENC_RMAX = 150.0   # m: wall rays of enclosed() (the domestic / ITB halls are <= ~200 m across; a point inside sees walls within this)


def axis_hits(T, P, ax, rmax=None):
    """for each point of P (n, 3), the triangles of T (m, 3, 3) crossed by the line through the point along axis ax
    (0 = x, 1 = y, 2 = z): the number of crossings on the + side and on the - side of the point (axis-aligned rays:
    a 2-D point-in-triangle test in the plane of the other two axes, then the crossing coordinate by barycentrics);
    rmax: only crossings within that distance count"""
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
        if rmax is not None: x = x[np.abs(x - p[ax]) <= rmax]
        plus[i] = int((x > p[ax]).sum()); minus[i] = int((x < p[ax]).sum())
    return plus, minus


def enclosed(T, P, max_gap_deg=45.0, TW=None, rmax=ENC_RMAX):
    """review round 2 (finding 3): points of P (world, n x 3) that lie INSIDE the building whose triangles are T: a roof
    (any triangle) above and walls all around (eight horizontal rays, no open sector wider than max_gap_deg). Hits, not
    parity: the exported shells are not closed (door gaps, shared walls, open undersides). A road beside a facade or under
    a curb canopy sees the building over at most ~180 deg: outside; a deck running through the hall sees it all round.
    TW: the triangles the walls are taken from (default T). Callers pass the whole group's LOD0 near the unit: a unit's
    shell is open where it joins the next unit of its group (T2 at the BA-D pier: 102 m2 of deck under the T2 roof, east of
    its west wall, saw no wall to the east and passed as outside). rmax: walls count within this distance only (with the
    group's walls, a point at the ITB plate's end saw its one open sector closed by BA-A, ~600 m across the courtyard)"""
    if not len(P) or not len(T): return np.zeros(len(P), bool)
    up, _ = axis_hits(T, P, 1)
    if TW is not None and len(TW): T = TW
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
        pl, mi = axis_hits(rot(W), rot(P), 0, rmax)
        hit[:, k] = pl > 0; hit[:, k + 4] = mi > 0
    order = [0, 1, 2, 3, 4, 5, 6, 7]   # directions th, th + 45 ... th + 315 (the - rays of k are at th_k + 180)
    gap = np.zeros(len(P), int); run = np.zeros(len(P), int)
    for j in order + order:          # longest run of directions without a hit, cyclic
        run = np.where(hit[:, j], 0, run + 1); gap = np.maximum(gap, run)
    return (up > 0) & (gap * 45.0 <= max_gap_deg)


def group_walls(TR, g, bounds, pad=300.0):
    """the LOD0 triangles of every unit of group g whose bounding box meets bounds (x0, z0, x1, z1) + pad: the wall source
    of enclosed() (see there)"""
    x0, z0, x1, z1 = bounds; out = []
    for (gg, u, l), T in TR['_lods'].items():
        if gg != g or l != 0 or u in ('*', 'all') or T is None or not len(T): continue
        lo, hi = T[:, :, [0, 2]].min(1), T[:, :, [0, 2]].max(1)
        m = (hi[:, 0] > x0 - pad) & (lo[:, 0] < x1 + pad) & (hi[:, 1] > z0 - pad) & (lo[:, 1] < z1 + pad)
        if m.any(): out.append(T[m])
    return np.concatenate(out) if out else None


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
    # close-out round 3 (buildings R3.4): a unit without an SFO Museum outline measured against its own observed wall line
    # (the BART station: NAIP 2024 north wall, landside_r1_measure.BART_NORTH, +-2 m): no nearer than that line - 0.5 m
    # = the real building's position, an existing condition (the ADG of the lane is inferred, AC 150/5300-13A Table 4-1)
    obs_ref = {}
    try:
        import landside_r1_measure as LRM
        obs_ref[('landside', 'bart_station')] = (LineString(LRM.BART_NORTH), 'NAIP 2024 north wall line (landside_r1_measure.BART_NORTH, +-2 m)')
    except Exception as ex: log('  taxilane: observed BART wall line unavailable (%s)' % ex)
    for (g, u), v in dmin.items():
        if v['margin_m'] < 0:
            # a NOTE when the SFO Museum outline is as close (the real building; the asset did not introduce it), else CONFLICT
            if v['museum_outline_m'] <= v['dist_m'] + 0.5: res['notes'].append(dict(check='taxilane OFA (ADG %d)' % v['adg'], group=g, unit=u, **v, note='the surveyed SFO Museum outline is as close: existing condition, not the asset'))
            elif (g, u) in obs_ref and obs_ref[(g, u)][0].distance(lane[[x[0] for x in lane].index(v['lane'])][1]) <= v['dist_m'] + 0.5:
                d_obs = round(obs_ref[(g, u)][0].distance(lane[[x[0] for x in lane].index(v['lane'])][1]), 1)
                res['notes'].append(dict(check='taxilane OFA (ADG %d)' % v['adg'], group=g, unit=u, **v, observed_wall_m=d_obs,
                                         note='the observed wall (%s) is %.1f m from the lane: the real building stands inside the inferred OFA - existing condition, not the asset; the lane ADG is inferred' % (obs_ref[(g, u)][1], d_obs)))
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
            # review round 2 (finding 3): the band test compares SURFACES, so a part inside the other building's hollow shell
            # (or one crossing its wall between two bands) cannot register; as for the road decks, the solid test too: 1-m
            # cells of the plan overlap at every 1 m of the shared height, inside both buildings (enclosed(): a roof above and
            # walls all round) -> m3 shared (the elevated units - guideway, roadways - are not enclosures; their decks are
            # tested in deck_checks)
            sol = None
            if not (elevated(*a) or elevated(*b)):
                TA, TB = TR['_lods'].get((a[0], a[1], 0)), TR['_lods'].get((b[0], b[1], 0))
                if TA is not None and TB is not None and len(TA) and len(TB):
                    xb0, zb0, xb1, zb1 = X.bounds
                    Gc = np.array(np.meshgrid(np.arange(xb0 + 0.5, xb1, 1.0), np.arange(zb0 + 0.5, zb1, 1.0))).reshape(2, -1).T
                    Gc = Gc[shapely.contains_xy(X, Gc[:, 0], Gc[:, 1])] if len(Gc) else Gc
                    ys = np.arange(ya + 0.5, yb, 1.0); sol = 0
                    if len(Gc) and len(ys):
                        Q = np.array([[gx, yy, gz] for gx, gz in Gc for yy in ys])
                        ina = enclosed(TA, Q, TW=group_walls(TR, a[0], X.bounds))
                        if ina.any(): sol = int(enclosed(TB, Q[ina], TW=group_walls(TR, b[0], X.bounds)).sum())
            pairs.append(dict(a='/'.join(a), b='/'.join(b), plan_overlap_m2=round(X.area, 1), band_overlap_m2=round(best[0], 1), band_y=best[1], core_m2=round(best[2], 1), at_xz=best[3], solid_m3=sol))
            if best[2] > 2.0: res['conflicts' if best[2] > 20.0 else 'notes'].append(dict(check='asset vs asset (same height band)', a='/'.join(a), b='/'.join(b), core_m2=round(best[2], 1), band_y=best[1], at_xz=best[3]))
            if sol and sol > 2: res['conflicts' if sol > 20 else 'notes'].append(dict(check='asset vs asset (solid: inside both buildings)', a='/'.join(a), b='/'.join(b), solid_m3=sol, plan_overlap_m2=round(X.area, 1)))
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
    stacked_cut_checks(res, log)
    return res


def stacked_cut_checks(res, log):
    """close-out round 4 (the round-3 verifier: four stacked cuts that leave a carriageway under lanes x 3.0 m stood only in
    the build record): build_roadways' stacked cuts that were made although they narrow the lower deck below lanes x
    MIN_LANE_W (the decks would clash if it were kept whole: the clearance kept < KEEP_CLEAR) are listed as conflicts with
    their way ids; the refused ones (kept whole, a low clearance) are the deck-over-deck clearance conflict above, and
    each refused pair is listed as a note with its ids (out/buildings3d/roadways_build.json#stats.stacked.cuts)"""
    try: cuts = json.load(open(os.path.join(ROOT, 'out', 'buildings3d', 'roadways_build.json')))['stats']['stacked']['cuts']
    except (OSError, ValueError, KeyError): return
    nar = [c for c in cuts if c.get('narrowed')]; ref = [c for c in cuts if c.get('refused')]
    res['stats']['stacked_cuts'] = dict(made=sum(1 for c in cuts if not c.get('refused')), narrowed=len(nar), refused=len(ref))
    for c in nar:
        res['conflicts'].append(dict(check='stacked roadway cut narrows the lower carriageway below lanes x 3.0 m (the decks would clash if kept whole)',
                                     lower=c['lower'], upper=c['upper'], min_width_m=c['min_width_m'], need_m=c['need_m'], clearance_if_kept_m=c['clearance_if_kept_m'],
                                     at=c['at'], why=c['narrowed'], note='a diverge / merge whose branch the level solve takes off the main deck\'s level while their ribbons '
                                     'still overlap (median step >= 1 m): the branch is cut back to where it leaves the main deck'))
    for c in ref:
        res['notes'].append(dict(check='stacked roadway cut refused (lower deck kept whole under the upper one; its clearance is in the deck-over-deck check)',
                                 lower=c['lower'], upper=c['upper'], clearance_if_kept_m=c['clearance_if_kept_m'], at=c['at'], why=c['refused']))
    log('stacked roadway cuts (roadways_build.json): %d made, %d of them narrow the lower carriageway (conflicts: %s); %d refused (notes: %s)'
        % (res['stats']['stacked_cuts']['made'], len(nar), [(c['lower'], c['upper']) for c in nar], len(ref), [(c['lower'], c['upper']) for c in ref]))


ROAD_CLEAR = 4.6   # m, vertical clearance over a road deck (Caltrans HDM 309.2, 15 ft; roadways_net.CLEAR_MIN) [inf]


def deck_points(step=1.0):
    """the roadways' LOD0 road surfaces (materials deck_* / island / kerb_red / paint_*: not parapets, fascia or columns)
    sampled on a ~step-m barycentric grid: (points (n, 3) world, unit name per point, area per point). Close-out r4 (the
    round-3 verifier: the refused stacked pair's area read 88.6 m2 here against 161 m2 on the mesh): the k x k subdivision
    of a triangle has k(k+1)/2 upright and k(k-1)/2 inverted cells; only the upright ones were sampled, so every area
    summed from these points covered ~half of each large triangle. Both kinds are sampled now (each point a / k^2)."""
    p = os.path.join(D3, 'roadways.glb')
    if not os.path.exists(p): return np.zeros((0, 3)), np.array([]), np.zeros(0)
    pts, units, area = [], [], []
    for r in mesh_nodes(p):
        if lod_of(r) != 0: continue
        sel = np.array([m.startswith('deck') or m in ('island', 'kerb_red') or m.startswith('paint') for m in r['mats']], bool)
        for t in r['tris'][sel]:
            k = int(max(1, math.ceil(max(np.linalg.norm(t[1] - t[0]), np.linalg.norm(t[2] - t[1]), np.linalg.norm(t[0] - t[2])) / step)))
            ij = np.array([(i + 1 / 3, j + 1 / 3) for i in range(k) for j in range(k - i)] + [(i + 2 / 3, j + 2 / 3) for i in range(k - 1) for j in range(k - 1 - i)], float)
            q = t[0] + (ij[:, :1] / k) * (t[1] - t[0]) + (ij[:, 1:] / k) * (t[2] - t[0])   # cell centroids (upright + inverted cells: k^2)
            a = 0.5 * np.linalg.norm(np.cross(t[1] - t[0], t[2] - t[0]))
            pts.append(q); units += [r['extras'].get('building', '?')] * len(q); area.append(np.full(len(q), a / max(1, k * k)))
    if not pts: return np.zeros((0, 3)), np.array([]), np.zeros(0)
    return np.concatenate(pts), np.array(units), np.concatenate(area)


def lowest_above(T, P, min_dy=1.0, cell=8.0):
    """per point of P (n, 3), the lowest point of the triangles T (m, 3, 3) straight above it and more than min_dy up
    (np.inf where none): triangles binned on a cell-m plan grid by their bounding boxes, each point tested against its
    cell's triangles (barycentric height of the triangles that cover it)"""
    out = np.full(len(P), np.inf)
    if not len(T) or not len(P): return out
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); T = T[np.abs(n[:, 1]) > 1e-9]       # vertical faces cover no point
    T = T[T[:, :, 1].max(1) > P[:, 1].min() + min_dy]
    if not len(T): return out
    lo, hi = T[:, :, [0, 2]].min(1), T[:, :, [0, 2]].max(1)
    c0 = np.floor(lo / cell).astype(int); c1 = np.floor(hi / cell).astype(int)
    grid = {}
    for k in range(len(T)):
        for cx in range(c0[k, 0], c1[k, 0] + 1):
            for cz in range(c0[k, 1], c1[k, 1] + 1): grid.setdefault((cx, cz), []).append(k)
    pc = np.floor(P[:, [0, 2]] / cell).astype(int); byc = {}
    for i, key in enumerate(map(tuple, pc)): byc.setdefault(key, []).append(i)
    for key, ii in byc.items():
        kk = grid.get(key)
        if not kk: continue
        t = T[kk]; q = P[ii]; a0, a1, a2 = t[:, 0], t[:, 1], t[:, 2]
        v0 = (a2 - a0)[:, [0, 2]]; v1 = (a1 - a0)[:, [0, 2]]
        d00 = (v0 * v0).sum(1); d01 = (v0 * v1).sum(1); d11 = (v1 * v1).sum(1); den = d00 * d11 - d01 * d01
        v2 = q[:, None, [0, 2]] - a0[None, :, [0, 2]]                      # (points, triangles, 2)
        d20 = (v2 * v0[None]).sum(2); d21 = (v2 * v1[None]).sum(2)
        ok = np.abs(den) > 1e-12; dd = np.where(ok, den, 1.0)
        uu = (d11 * d20 - d01 * d21) / dd; vv = (d00 * d21 - d01 * d20) / dd
        ins = ok[None] & (uu >= 0) & (vv >= 0) & (uu + vv <= 1)
        y = a0[None, :, 1] + uu * (a2 - a0)[None, :, 1] + vv * (a1 - a0)[None, :, 1]
        y = np.where(ins & (y > q[:, 1:2] + min_dy), y, np.inf)
        out[ii] = np.minimum(out[ii], y.min(1))
    return out


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
            e = enclosed(T, Q, TW=None if g == 'landside' else group_walls(TR, g, fp.bounds))
            if e.any():
                ii = np.nonzero(m)[0][e]
                ins['%s/%s' % (g, u)] = dict(area_m2=round(float(A[ii].sum()), 1), units=sorted(set(U[ii].tolist())), at=[round(float(P[ii[0], 0]), 1), round(float(P[ii[0], 2]), 1)])
    st['deck_inside_buildings'] = ins
    for k, v in ins.items():
        res['conflicts' if v['area_m2'] > 1.0 else 'notes'].append(dict(check='road deck inside a building (solid test)', building=k, **v))
    # clearance (the landside guideway split into its deck and its inferred T-piers, LOD0 node names '*_piers')
    gd, gp = [], []
    lp = os.path.join(D3, 'landside.glb')
    if os.path.exists(lp):
        for r in mesh_nodes(lp):
            if lod_of(r) != 0 or len(r['chain']) < 2 or not str(r['chain'][1].get('name', '')).startswith('airtrain'): continue
            (gp if '_piers' in r['name'] else gd).append(r['tris'])
    # the roadways over themselves at LOD0 only (the points are LOD0 deck tops; the simplified LOD2 deck lies off its LOD0
    # on the curved ramps and read as a deck 1.0 m overhead: 117 m2 of deck-over-deck below 4.6 m with every LOD, 92.5 at LOD0)
    R0 = [T for (g, u, l), T in TR['_lods'].items() if g == 'roadways' and l == 0]
    srcs = [(g, (np.concatenate(R0) if g == 'roadways' and R0 else TR[g]['all']['T'])) for g in GROUPS if g in TR and g != 'landside']
    Tl = [T for (g, u), T in TR['_units'].items() if g == 'landside' and not u.startswith('airtrain')]
    if Tl: srcs.append(('landside', np.concatenate(Tl)))   # garages, hotel, stations ...: the guideway is split below
    if gd: srcs.append(('guideway deck', np.concatenate(gd)))
    if gp: srcs.append(('guideway piers', np.concatenate(gp)))
    rows = []
    for g, T in srcs:
        if g == 'roadways':
            # the undersides only (soffits, facing down): what a vehicle meets. Review round 2: with every non-vertical face,
            # the parapet TOPS of a diverging lane 0.26-0.5 m higher stood 1.03-1.36 m over the lower deck's edge at five gores
            # (1.6 m2) and read as decks overhead; a parapet sits on its own deck and has no underside over the other
            n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); T = T[n[:, 1] / (np.linalg.norm(n, axis=1) + 1e-12) < -0.2]
        h = lowest_above(T, P, 1.0)
        for i in np.nonzero(np.isfinite(h))[0]: rows.append((float(h[i] - P[i, 1]), g, U[i], float(A[i]), P[i]))
    def summ(sel):
        if not sel: return None
        sel.sort(key=lambda r: r[0]); r0 = sel[0]
        return dict(points=len(sel), min_m=round(r0[0], 2), at=[round(float(r0[4][0]), 1), round(float(r0[4][2]), 1)], deck_m=round(float(r0[4][1]) - GROUND_Y, 2), unit=r0[2],
                    below_m2=round(sum(r[3] for r in sel if r[0] < ROAD_CLEAR), 1))
    keys = sorted({r[1] for r in rows})
    st['deck_clearance'] = {g: summ([r for r in rows if r[1] == g]) for g in keys}
    for g, v in st['deck_clearance'].items():
        if v and v['below_m2'] > 0:
            # the guideway (deck and piers), other road decks and the landside structures (all of it) are hard limits; a
            # building part over a road (curb canopies, eaves) is its owner's call
            res['conflicts' if g in ('landside', 'roadways', 'guideway deck', 'guideway piers') else 'notes'].append(dict(check='vertical clearance over a road deck (< %.1f m)' % ROAD_CLEAR, over=g, **v))
    # the guideway's inferred pier columns standing in a road deck (the deck is trimmed round them: a hole)
    if gp:
        Tp = np.concatenate(gp); n = np.cross(Tp[:, 1] - Tp[:, 0], Tp[:, 2] - Tp[:, 0])
        col = Tp[(np.abs(n[:, 1]) < 1e-3 * (np.linalg.norm(n, axis=1) + 1e-12)) & (Tp[:, :, 1].min(1) < GROUND_Y + 1.0)]
        cols = plan_geom(col) if len(col) else Polygon()
        D = unary_union([Polygon(t[:, [0, 2]]) for r in mesh_nodes(os.path.join(D3, 'roadways.glb')) if lod_of(r) == 0
                         for t in r['tris'][np.array([m.startswith('deck') for m in r['mats']], bool)] if Polygon(t[:, [0, 2]]).area > 1e-4]) if os.path.exists(os.path.join(D3, 'roadways.glb')) else Polygon()
        # close-out round 3: a column IN a deck (overlap, + 0.05 m) is a conflict; one within 0.6 m of a deck edge is a note
        # (it stands beside the deck, outside its parapet - r17: one straddle-bent column 0.48 m off a ramp edge was listed
        # as "in a road deck" by the old 0.6-m buffer, while verify_landside's foot test found none on a deck)
        pq = [q for q in (getattr(cols, 'geoms', None) or [cols]) if isinstance(q, Polygon) and not q.is_empty]
        hit = [q for q in pq if q.buffer(0.05).intersects(D)]
        near = [q for q in pq if q not in hit and q.buffer(0.6).intersects(D)]
        st['guideway_piers_in_road_decks'] = [[round(q.centroid.x, 1), round(q.centroid.y, 1)] for q in hit]
        st['guideway_piers_beside_road_decks'] = [dict(at=[round(q.centroid.x, 1), round(q.centroid.y, 1)], gap_m=round(q.distance(D), 2)) for q in near]
        if hit: res['conflicts'].append(dict(check='guideway pier column in a road deck (landside pier sites [inf])', count=len(hit), at=st['guideway_piers_in_road_decks'][:10]))
        if near: res['notes'].append(dict(check='guideway pier column beside a road deck (< 0.6 m from its edge, outside it)', count=len(near), at=st['guideway_piers_beside_road_decks'][:10]))
    # close-out round 3 (buildings R3.2): the road decks over the app's at-grade roads (deck soffit above grade)
    st['at_grade_clearance'] = at_grade_clearance(TR, log)
    byu = {}
    for v in st['at_grade_clearance'].get('below', []): byu.setdefault(v['over'], []).append(v)
    for u, L in sorted(byu.items(), key=lambda kv: min(v['min_m'] for v in kv[1])):
        w0 = min(L, key=lambda v: v['min_m'])
        res['conflicts'].append(dict(check='vertical clearance over an at-grade road (< %.1f m)' % ROAD_CLEAR, over=u, roads=len({v['way'] for v in L}), min_m=w0['min_m'], at=w0['at'],
                                     length_m=round(sum(v['length_m'] for v in L), 1), ways=sorted({v['way'] for v in L})[:40],
                                     note=('the anchored domestic departures loop: deck at the curb placeholder (4.73 m [unk]), soffit 3.53 m - by design of the curb level (buildings R3.2); posted clearance unknown (owner)'
                                           if u == 'domestic_departures' else 'solved deck over an at-grade road (the solve holds the clearance at the centreline crossings only)')))
    # the ITB curb
    st['itb_curb_gap'] = itb_curb_gap(P, TR, log)
    if st['itb_curb_gap'] and st['itb_curb_gap']['over_limit'] > 0:
        res['conflicts'].append(dict(check='ITB curb to departures deck void (> 0.3 m)', **st['itb_curb_gap']))
    log('deck checks: %d road-surface points; inside buildings %s; clearance %s; ITB curb %s' % (len(P), {k: v['area_m2'] for k, v in ins.items()} or 'none',
        {g: (v['min_m'], v['below_m2']) for g, v in st['deck_clearance'].items() if v}, st['itb_curb_gap']))


def at_grade_clearance(TR, log, step=1.0):
    """close-out round 3 (buildings R3.2): the app's at-grade roads (data/sfo_landside.json, not elevated) under the road
    decks: every `step` m along each carriageway at its centre and 0.3 m inside each edge, the lowest roadways LOD0 underside
    (faces facing down: soffits, fill tops excluded) more than 0.5 m above grade, per deck unit. The roads the roadways
    solve lifts into approach ramps (out/buildings3d/roadways_build.json pieces src 'ramp': they ARE the deck there) are
    skipped. Returns {'checked': n points, 'ways': n, 'below': [per way and deck unit: min clearance, where, length under
    ROAD_CLEAR]} - each 'below' entry is a CONFLICT (a deck over an at-grade road needs DECK clearance; the anchored
    domestic loop has its soffit at the curb placeholder level, see manifest.json#roadways)"""
    out = dict(checked=0, ways=0, below=[])
    try:
        L = json.load(open(os.path.join(ROOT, 'data', 'sfo_landside.json')))
        ramps = {p['id'] for p in json.load(open(os.path.join(ROOT, 'out', 'buildings3d', 'roadways_build.json')))['pieces'] if p['src'] == 'ramp'}
    except (OSError, ValueError, KeyError) as ex:
        log('at-grade clearance: inputs missing (%s)' % ex); return out
    units = {u: T for (g, u, l), T in TR['_lods'].items() if g == 'roadways' and l == 0 and u not in ('*', 'all') and T is not None and len(T)}
    soff = {}
    for u, T in units.items():
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); soff[u] = T[n[:, 1] / (np.linalg.norm(n, axis=1) + 1e-12) < -0.2]
    allT = np.concatenate([T for T in soff.values() if len(T)]) if soff else np.zeros((0, 3, 3))
    if not len(allT): return out
    lo, hi = allT[:, :, [0, 2]].min(0).min(0), allT[:, :, [0, 2]].max(0).max(0)
    for r in L['roads']:
        if r['elevated'] or r['osm_id'] in ramps or len(r['pts']) < 2: continue
        ln = LineString(r['pts']); x0, z0, x1, z1 = ln.bounds
        if x1 < lo[0] or x0 > hi[0] or z1 < lo[1] or z0 > hi[1]: continue
        ss = np.arange(0.0, ln.length, step) + step / 2
        if not len(ss): continue
        c = shapely.get_coordinates(shapely.line_interpolate_point(ln, ss))
        c2 = shapely.get_coordinates(shapely.line_interpolate_point(ln, np.minimum(ss + 0.5, ln.length))); c1 = shapely.get_coordinates(shapely.line_interpolate_point(ln, np.maximum(ss - 0.5, 0)))
        t = c2 - c1; t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-9); nrm = np.c_[-t[:, 1], t[:, 0]]
        off = max(0.0, r.get('w', 6.0) / 2 - 0.3)
        Q = np.concatenate([c + nrm * o for o in (-off, 0.0, off)]); S = np.concatenate([ss] * 3)
        P = np.c_[Q[:, 0], np.full(len(Q), GROUND_Y), Q[:, 1]]
        out['checked'] += len(P); out['ways'] += 1
        for u, T in soff.items():
            if not len(T): continue
            h = lowest_above(T, P, 0.5) - GROUND_Y
            bad = np.isfinite(h) & (h < ROAD_CLEAR)
            if not bad.any(): continue
            k = int(np.argmin(np.where(bad, h, np.inf)))
            out['below'].append(dict(way=r['osm_id'], name=r.get('name'), over=u, min_m=round(float(h[k]), 2), at=[round(float(Q[k, 0]), 1), round(float(Q[k, 1]), 1)],
                                     length_m=round(float(len(np.unique(np.round(S[bad] / step)))) * step, 1)))
    out['below'].sort(key=lambda v: v['min_m'])
    log('at-grade roads under the road decks: %d points on %d roads; below %.1f m: %s' % (out['checked'], out['ways'], ROAD_CLEAR,
        [(v['way'], v['over'], v['min_m'], v['length_m']) for v in out['below']] or 'none'))
    return out


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
    try: curb_h = float(man['roadways']['levels']['itb']['curb'])           # spec_itb level3.floor (the roadways' anchor)
    except (KeyError, TypeError, ValueError): curb_h = 11.5
    cs = up[(uvc[:, 1] < -27.0) & (uvc[:, 1] > -36.0) & (np.abs(up[:, :, 1].mean(1) - GROUND_Y - curb_h) < 0.1)]   # the west curb top (not the canopy, bollard caps)
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
def rings_of(geo, tol=0.25, min_area=1.0):
    geo = geo.simplify(tol)
    polys = [geo] if isinstance(geo, Polygon) else list(getattr(geo, 'geoms', []))
    out = []
    for p in polys:
        if not isinstance(p, Polygon) or p.area < min_area: continue
        out.append([[[round(x, 2), round(z, 2)] for x, z in p.exterior.coords[:-1]]] + [[[round(x, 2), round(z, 2)] for x, z in h.coords[:-1]] for h in p.interiors if Polygon(h).area > 1.0])
    return out


TIER_TOL = 0.1    # m: tier ring simplification; each region is grown by it first, so the simplified ring stays outside every vertex
TIER_MIN = 0.02   # m2: the smallest tier piece kept. Close-out round 3 fix 2 (verifier v3): with rings under 1 m2 and over-bins under 0.25 m2
                  # dropped, a free-standing T1 / BA_C junction wall (a 0.8 m2 strip from grade to 8.9 m) lay 3.9 m outside every tier,
                  # vestibule / door-surround panels 0.5-1.3 m and the ITB hall outrigger tips 1.6 m; 0.1-2.5 % of each unit's vertices


def tier_rings(reg):
    return rings_of(reg.buffer(TIER_TOL, join_style='mitre', mitre_limit=2.0), TIER_TOL, min_area=TIER_MIN)


def tier_coverage(T, tl, y0, tol=0.3):
    """self-check (fix 2, verifier v3): every LOD0 / LOD1 vertex of a unit above the ground plate (y0 + 0.5) must lie within
    `tol` of a tier that admits it (body: any height; over: its lower y <= the vertex y + 0.15). Returns (vertices, outside,
    max distance m, worst vertex)"""
    V = np.unique(np.round(T.reshape(-1, 3), 2), axis=0); V = V[V[:, 1] > y0 + 0.5]
    if not len(V): return 0, 0, 0.0, None
    P_ = shapely.points(V[:, 0], V[:, 2]); d = np.full(len(V), 1e9)
    for t in tl:
        P = unary_union([Polygon(r[0], r[1:]).buffer(0) for r in t['rings']])
        adm = np.ones(len(V), bool) if t['part'] == 'body' else (V[:, 1] >= t['y'][0] - 0.15)
        d = np.where(adm, np.minimum(d, shapely.distance(P, P_)), d)
    b = d > tol
    return int(len(V)), int(b.sum()), round(float(d[b].max()), 2) if b.any() else 0.0, (np.round(V[b][np.argmax(d[b])], 1).tolist() if b.any() else None)


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
    if not body.is_empty and body.area > TIER_MIN: out.append(dict(part='body', y=[round(y[0], 2), round(y[1], 2)], rings=tier_rings(body)))
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
        reg = unary_union([q for q in (getattr(reg, 'geoms', None) or [reg]) if isinstance(q, Polygon) and q.area > TIER_MIN])
        if reg.is_empty: continue
        claimed = unary_union([claimed, reg])
        rr = tier_rings(reg)
        if rr: out.append(dict(part='over', y=[round(float(sel[:, :, 1].min()), 2), round(y[1], 2)], rings=rr))
    return out


def _rw_cut():
    """deck area build_roadways.py cut where it ran inside a building (out/buildings3d/roadways_build.json)"""
    try: return json.load(open(os.path.join(ROOT, 'out', 'buildings3d', 'roadways_build.json')))['stats'].get('deck_cut_inside_buildings_m2', {})
    except (OSError, ValueError, KeyError): return 'see roadways_build.json'


def requests_of(res):
    """requests to the other groups, from this run's results (review round 2: the list was hard-coded and kept items the
    groups had closed, and two LOD2 items that were checker artefacts)"""
    out = []
    for c in res['conflicts']:
        if 'drum' in c.get('check', '') or 'walkway' in c.get('check', ''):
            out.append('%s: %s' % (c.get('group', 'domestic'), json.dumps(c)[:300]))
    ins = res['stats'].get('deck_inside_buildings', {})
    cut = _rw_cut()
    if isinstance(cut, dict) and cut.get('domestic/T2'):
        out.append('domestic: Terminal 2 landside face (integration review r2, finding 3): roadways.glb is still cut where its deck ran inside the T2 shell '
                   '(cut %s m2 of deck, left inside after the cut %s m2); please move the T2 landside face to the measured roof edge' % (cut, {k: v['area_m2'] for k, v in ins.items()} or 0))
    # (close-out round 3: done by the domestic group on 6-7 Nov - the T2 face stands on the NAIP 2024 roof edge; the roadways
    # rebuild no longer cuts the deck at T2. The T1 / T3 cuts are the departures parapets straddling those facades by 1-3 m.)
    pc = [c for c in res['conflicts'] if 'pier' in c.get('check', '') or c.get('over') == 'guideway piers']
    if pc:
        out.append('landside: AirTrain T-piers placed on the road decks / with caps over them (landside_airtrain.py: sites every ~30 m along the '
                   'skeleton, random order, no road test [inf]): %s. Real piers stand clear of the carriageways; please keep pier sites off '
                   'roadways.glb deck_* surfaces and data/sfo_landside.json carriageways (+0.5 m), caps >= 4.6 m above any deck under them'
                   % '; '.join(json.dumps({k: v for k, v in c.items() if k in ('count', 'at', 'min_m', 'below_m2', 'unit')}) for c in pc))
    out.append('bridges: the per-building footprints with height bands are now in data/buildings3d/integration.js (B3D_INTEGRATION.footprints.units[group][unit].tiers: '
               'body = grade to top, over = underside to top; close-out round 3, integration-5): gates.js can test drums / tunnels against them instead of the SFO Museum proxy and '
               'the own-strip rule (bridges-6, buildings R3.3: a drum under a roof overhang is clear when its top is below the over tier\'s underside)')
    ag = [v for v in res['stats'].get('at_grade_clearance', {}).get('below', []) if v['over'] == 'domestic_departures']
    if ag:
        out.append('owner / domestic: the anchored domestic departures loop (deck top 4.73 m at the curb placeholder [unk], soffit 3.53 m with the generic 1.2-m deck) is '
                   'below 4.6 m over %d at-grade roads (min %.2f m; conflict "vertical clearance over an at-grade road"); kept as built: the curb level is the published '
                   'T3 L1 -> L2 16 ft [pub at T3], so the real stacked arrivals level is below 4.6 m by design. A posted-clearance photo of the domestic arrivals level '
                   'would settle it (buildings R3.2)' % (len({v['way'] for v in ag}), min(v['min_m'] for v in ag)))
    rr = [c for c in res['conflicts'] if c.get('check', '').startswith('vertical clearance over a road deck') and c.get('over') == 'roadways']
    if rr:
        # close-out r3 fix 2 (verifier v1): the stacked cut is refused where it would split the lower deck, so the ITB loop's
        # lower roadway passes whole under its anchored departures legs with the clearance the level pair leaves
        # close-out r4 (the round-3 verifier): a three-level stack - at the conflict point the lower roadway is not at LOWER_H
        # but floored by the at-grade roads under it (deck_m of the record)
        out.append('owner / buildings (ITB group): roads under roads below %.1f m: %s. At the ITB loop this is a three-level stack: the at-grade roads '
                   '(data/sfo_landside.json, e.g. OSM 256787736 / 93671776 beside the conflict point), the lower (arrivals) roadway 41015123 over them (held at LOWER_H '
                   '5.80 m on the straight; past it the level solve keeps it >= 4.6 m + the 1.2-m deck above the at-grade roads under it [inf]: deck %s m at the '
                   'conflict point), and its departures legs (OSM 38853121 / 38853045), which leave the L3 plate at 11.35 m (spec_itb level3.floor 11.5 [inf] - kerb) '
                   'and need 5.8 m deck to deck above it. Photo i1 reads the L3-to-lower-level step ~6.7 m (L3 ~1 m higher than modelled); please review level3.floor '
                   'against i1 (buildings R3.2) - the roadways follow the ITB curb on the next build_roadways.py run (L3 +0.8 m lifts the conflict)'
                   % (ROAD_CLEAR, '; '.join(json.dumps({k: v for k, v in c.items() if k in ('unit', 'min_m', 'at', 'below_m2', 'area_m2', 'deck_m')}) for c in rr),
                      '/'.join('%.2f' % c['deck_m'] for c in rr if 'deck_m' in c) or '?'))
    tl = [c for c in res['conflicts'] if c.get('check', '').startswith('taxilane')]
    for c in tl: out.append('%s: %s %.1f m from taxilane centreline %s (ADG %s inferred: %.1f m); SFO Museum outline %.1f m' % (c['group'], c['unit'], c['dist_m'], c['lane'], c['adg'], c['need_m'], c['museum_outline_m']))
    try:
        L2 = json.load(open(os.path.join(OUTD, 'lod2_check.json')))
        if L2.get('flagged'): out.append('LOD2 vs LOD0 (tools/blender/b3d_lod2_check.py, %s): %s' % (L2.get('generated'), '; '.join(L2['flagged'])))
    except (OSError, ValueError): pass
    return out


def glow_def():
    """the loader's night-glow table (js/three/buildings3d.js GLOW_DEF: kind -> [linear RGB, level in lamp units x nightE])
    for manifest.json#integration.glow (close-out round 3, integration-6: listed as inferred, configurable values)"""
    import re
    try:
        src = open(os.path.join(ROOT, 'js', 'three', 'buildings3d.js')).read()
        body = re.search(r'GLOW_DEF = \{(.*?)\n\};', src, re.S).group(1)
        out = {}
        for k, c, v in re.findall(r'(\w+): \[\[([-\d.,\s]+)\],\s*([-\d.]+)\]', body): out[k] = dict(color_linear=[float(x) for x in c.split(',')], k=float(v))
        cap = re.search(r'GLOW_CAP = ([\d.]+)', src)
        return dict(kinds=out, cap=float(cap.group(1)) if cap else None, tag='inf', source='js/three/buildings3d.js GLOW_DEF (no measured SFO night luminances)',
                    configurable='SFO.R.b3d.setGlow(kind, {color, k, cap}) at run time; the defaults are the values here',
                    notes=dict(cab='0 (off) since close-out round 3: the only dusk / night tower photo (t5, refs/cache/buildings/review_likeness/t5.jpg, CC BY-SA) shows the cab glass dark; was teal 0.25 [inf]'))
    except (OSError, AttributeError, ValueError) as ex:
        return dict(error=str(ex))


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
    fps = {}; phys = []; tcov = {}
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
            if TT is not None and u not in ('*', 'all'):
                fps[g][u]['tiers'] = tiers(TT, geo, y)
                if g in FP_JS_GROUPS: tcov[(g, u)] = tier_coverage(TT, fps[g][u]['tiers'], y[0])
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
    log('footprint tiers self-check (LOD0 / LOD1 vertices above the ground plate within 0.3 m of an admissible tier of their unit): %d vertices, %d outside (max %.2f m)%s'
        % (sum(v[0] for v in tcov.values()), sum(v[1] for v in tcov.values()), max((v[2] for v in tcov.values()), default=0.0),
           ''.join(' %s/%s %d (%.2f m at %s)' % (k[0], k[1], v[1], v[2], v[3]) for k, v in tcov.items() if v[1])))
    json.dump(out, open(os.path.join(D3, 'integration.json'), 'w'), indent=None, separators=(',', ':'))
    # close-out round 3 (integration-5, bridges R2b.3 / buildings R3.3): the per-building LOD0 / LOD1 footprints with their
    # height bands for the app (js/live/gates.js tests the bridges against the real asset outlines instead of the SFO Museum
    # proxy): per unit the max-extent ring set and its tiers - `body` (what stands on the ground: grade to top) and `over`
    # (roof eaves, canopies, vestibules: from the lowest underside over that region to the top), so a rotunda drum under a
    # roof overhang is not read as inside the building. Heights are world y (GROUND_Y = 3.0 at grade); rings [x, z] in
    # metres, simplified 0.1 m. the landside units (garages, hotel, stations, hangars), the guideway and the roadways are not
    # (bridges and aircraft never reach them; physics.rings stays the ground-physics set). Only the groups the bridges and
    # stands meet go to the app (FP_JS_GROUPS: +134 kB of the bundled integration.js; the landside garages, +120 kB, stay
    # in integration.json#footprints).
    fps_js = {}
    for g in FP_JS_GROUPS:
        for u, e in fps.get(g, {}).items():
            if u in ('*', 'all') or not e.get('tiers'): continue
            fps_js.setdefault(g, {})[u] = dict(y=e['y'], lods=e['lods'], tiers=[dict(part=t['part'], y=t['y'], rings=t['rings']) for t in e['tiers']], **({'hangar': True} if g == 'landside' and u in HANGARS else {}))
    js = dict(replace=rep, tower=out['tower'], units=units, physics=dict(rings=phys_js, note='3-D asset footprints for js/live/ground.js buildingGrid (hangars, guideway, roadways excluded)'),
              footprints=dict(units=fps_js, ground_y=GROUND_Y, note='per asset unit (LOD0 / LOD1 max extent): tiers body (grade to top) and over (underside to top), world y, rings [x, z] (b3d_integrate.py tiers)'))
    with open(os.path.join(D3, 'integration.js'), 'w') as f:
        f.write('// Generated by tools/blender/b3d_integrate.py from data/buildings3d/*.glb + manifest.json (do not edit). The\n'
                '// first-pass app buildings each Blender asset replaces (routed into their own items by js/live/world.js so the\n'
                '// three.js renderer can hide them once the asset is shown, js/three/buildings3d.js), the tower camera anchor, the\n'
                '// landside unit index, the ground-physics rings and (close-out round 3) the per-building footprints with height bands\n'
                '// (footprints.units[group][unit].tiers: body / over prisms) for js/live/gates.js. The plausibility results are in\n'
                '// integration.json.\n')
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
                          deck_inside_buildings=res['stats'].get('deck_inside_buildings'), deck_clearance=res['stats'].get('deck_clearance'), itb_curb_gap=res['stats'].get('itb_curb_gap'),
                          at_grade_clearance=res['stats'].get('at_grade_clearance')),
        requests=requests_of(res), glow=glow_def(),
        footprints_js=dict(units=sum(len(v) for v in fps_js.values()), bytes_js=os.path.getsize(os.path.join(D3, 'integration.js')), note='B3D_INTEGRATION.footprints (close-out round 3, integration-5)',
                           tier_tol_m=TIER_TOL, tier_min_m2=TIER_MIN, self_check=dict(rule='every LOD0 / LOD1 vertex above y0 + 0.5 within 0.3 m of an admissible tier of its own unit (fix 2, verifier v3)',
                           vertices=sum(v[0] for v in tcov.values()), outside=sum(v[1] for v in tcov.values()), max_m=max((v[2] for v in tcov.values()), default=0.0),
                           per_unit={'%s/%s' % k: dict(vertices=v[0], outside=v[1], max_m=v[2], worst=v[3]) for k, v in tcov.items() if v[1]})),
        requests_withdrawn=['domestic: BA_C LOD2 top +9.08 m (review r1) - a checker artefact: the joined LOD2 mesh was split by plan distance and C3C '
                            'triangles went to BA_C; split by LOD0-footprint containment (+1 m) since review r2: top 0.0 m (lod2_check.json)',
                            'landside: rental car center LOD2 roof median 4.58 m (review r1) - a checker artefact: the roof cells sampled the open deck '
                            'beyond the roof edge; one roof-cell definition for both LODs since review r2 (1-m cells inside the LOD0 footprint - 0.5 m): 0.00 m'],
        generated=out['generated'], tool='tools/blender/b3d_integrate.py', doc='docs/research/buildings3d.md (integration section)'))
    log('wrote data/buildings3d/integration.json (%.0f kB), integration.js (%.0f kB) in %.0f s' % (os.path.getsize(os.path.join(D3, 'integration.json')) / 1e3, os.path.getsize(os.path.join(D3, 'integration.js')) / 1e3, time.time() - t0))
    return 1 if res['conflicts'] else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
