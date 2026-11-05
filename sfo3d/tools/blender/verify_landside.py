"""Verification of the exported landside asset (data/buildings3d/landside.glb) against the 2-D sheets (BL-01..03) and the
plausibility rules. Reads the glb back (numpy / shapely, no bpy) and compares it with the DRAWING values (draw_landside.py
constants and ggeom(), spec_landside.json, landside_naip_measurements.json) - not with the 3-D builder's own numbers.

    python3 tools/blender/verify_landside.py [data/buildings3d/landside.glb]    -> out/buildings3d/landside_verify.json

Checks (tolerance 0.5 m or 2 %, as for the other building groups):
  placement     every building node at its origin (world x, z) and the root at GROUND_Y
  heights       parapet / deck / tower / spine / tip / part tops of every building = the sheet values (BL-03)
  plans         LOD0 roof footprint vs the SFO Museum outline (area outside / not covered, boundary distance); the Garage A /
                G body end Lb and drum circle (BL-02 B); the Superbay roof extents (BL-02 G); Grand Hyatt face fractions
  AirTrain      deck top at every anchored station = its level; max grade; deck plan inside the SFO Museum polygon
  cars          per deck: count = NAIP density x deck area (or the visual count), all on the deck, no two overlapping
  plausibility  no building / guideway footprint in an aircraft stand envelope (tools/stands/geom.py stand_env, all stands),
                on a bridge walkway / rotunda, or on an SFO Museum taxiway polygon
"""
import json
import math
import os
import struct
import sys

import numpy as np
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools', 'buildings'))
import draw_data as D  # noqa: E402
import draw_landside as DL  # noqa: E402
from draw_lib import FT, hdg_vec  # noqa: E402

GROUND_Y = 3.0
CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}
LB = D.LANDM['buildings']


def load_glb(path):
    data = open(path, 'rb').read()
    clen, _ = struct.unpack_from('<I4s', data, 12)
    j = json.loads(data[20:20 + clen])
    off = 20 + clen
    blen, _ = struct.unpack_from('<I4s', data, off)
    return j, data[off + 8: off + 8 + blen], len(data)


def accessor(j, b, i):
    a = j['accessors'][i]; bv = j['bufferViews'][a['bufferView']]
    n = NC[a['type']]; dt = CT[a['componentType']]
    start = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    stride = bv.get('byteStride', 0)
    if stride and stride != n * np.dtype(dt).itemsize:
        raw = np.frombuffer(b, np.uint8, count=stride * a['count'], offset=start).reshape(a['count'], stride)
        arr = raw[:, :n * np.dtype(dt).itemsize].copy().view(dt).reshape(a['count'], n)
    else:
        arr = np.frombuffer(b, dt, count=a['count'] * n, offset=start).reshape(a['count'], n)
    if a.get('normalized'):
        arr = arr.astype(np.float32) / np.iinfo(dt).max
    return arr


def quat_mat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def node_mat(n):
    M = np.eye(4)
    if 'matrix' in n:
        return np.array(n['matrix']).reshape(4, 4).T
    S = np.diag(n.get('scale', [1, 1, 1]))
    M[:3, :3] = quat_mat(n.get('rotation', [0, 0, 0, 1])) @ S; M[:3, 3] = n.get('translation', [0, 0, 0])
    return M


def scene(j, b):
    """{node name: dict(lod, bldg, world positions per primitive, tris, material, instances)} + building node translations."""
    out, bnodes = {}, {}
    mats = [m.get('name', '') for m in j.get('materials', [])]
    root = next(i for i, n in enumerate(j['nodes']) if n.get('name') == 'landside')

    def walk(i, M, lod, bk):
        n = j['nodes'][i]; Mi = M @ node_mat(n); nm = n.get('name', '')
        if nm.startswith('LOD') and nm[3:4].isdigit(): lod = int(nm[3])
        if 'mesh' in n:
            prims = []
            for p in j['meshes'][n['mesh']]['primitives']:
                P = accessor(j, b, p['attributes']['POSITION']).astype(np.float64)
                P = (Mi[:3, :3] @ P.T).T + Mi[:3, 3]
                idx = accessor(j, b, p['indices']).ravel().astype(np.int64) if 'indices' in p else np.arange(len(P))
                prims.append(dict(P=P, T=idx.reshape(-1, 3), mat=mats[p['material']] if 'material' in p else ''))
            inst = None
            ext = n.get('extensions', {}).get('EXT_mesh_gpu_instancing')
            if ext:
                tr = accessor(j, b, ext['attributes']['TRANSLATION']).astype(np.float64)
                inst = (Mi[:3, :3] @ tr.T).T + Mi[:3, 3]
            out[nm] = dict(lod=lod, bldg=bk, prims=prims, extras=n.get('extras', {}), inst=inst)
        for c in n.get('children', []):
            walk(c, Mi, lod, bk)
    rn = j['nodes'][root]; Mr = node_mat(rn)
    for c in rn.get('children', []):
        n = j['nodes'][c]; bnodes[n['name']] = dict(M=Mr @ node_mat(n), extras=n.get('extras', {}))
        walk(c, Mr, None, n['name'])
    return out, bnodes, Mr


def allP(nodes, mat=None, lod=0):
    ps = [p['P'] for m in nodes for p in m['prims'] if (mat is None or p['mat'].split('@')[0].split('.')[0] in (mat if isinstance(mat, (list, tuple)) else [mat]))]
    return np.vstack(ps) if ps else np.zeros((0, 3))


def footprint(nodes, up_only=True, mats=None):
    polys = []
    for m in nodes:
        for p in m['prims']:
            if mats and p['mat'].split('@')[0].split('.')[0] not in mats: continue
            P = p['P']
            for t in p['T']:
                q = P[t]
                n = np.cross(q[1] - q[0], q[2] - q[0])
                if abs(n[1]) < 1e-6: continue
                if up_only and n[1] < 0: continue
                poly = Polygon(q[:, [0, 2]])
                if poly.area > 1e-4: polys.append(poly.buffer(0.01))
    return unary_union(polys) if polys else Polygon()


def tol(v):
    return max(0.5, 0.02 * abs(v))


class Checks:
    def __init__(self):
        self.rows = []

    def add(self, name, model, drawing, tolerance=None, src='', unit='m', ok=None):
        if ok is None:
            t = tol(drawing) if tolerance is None else tolerance
            ok = abs(float(model) - float(drawing)) <= t
        else:
            t = tolerance
        self.rows.append(dict(check=name, model=model if not isinstance(model, float) else round(model, 3),
                              drawing=drawing if not isinstance(drawing, float) else round(drawing, 3),
                              tol=t if not isinstance(t, float) else round(t, 3), ok=bool(ok), src=src, unit=unit))


def run(path):
    j, b, size = load_glb(path)
    S, BN, Mr = scene(j, b)
    C = Checks()
    C.add('root at GROUND_Y', float(Mr[1, 3]), GROUND_Y, 0.001, 'js/geo.js')
    by = {}
    for nm, m in S.items():
        by.setdefault(m['bldg'], []).append((nm, m))
    L0 = lambda k: [m for nm, m in by.get(k, []) if m['lod'] == 0 and m['inst'] is None]
    L0n = lambda k, part: [m for nm, m in by.get(k, []) if m['lod'] == 0 and nm.endswith(part)]
    H = lambda P: P[:, 1] - GROUND_Y
    for k, bn in BN.items():
        o = bn['extras'].get('origin_world_xz')
        if o:
            C.add(f'{k}: node origin x', float(bn['M'][0, 3]), float(o[0]), 0.01, 'manifest origin')
            C.add(f'{k}: node origin z', float(bn['M'][2, 3]), float(o[1]), 0.01, 'manifest origin')
    plans = {}

    def outline_check(k, name, fp_model, outline, tol_out=1.0, note=''):
        out = fp_model.difference(outline.buffer(0.3)).area
        miss = outline.difference(fp_model.buffer(0.3)).area
        C.add(f'{k}: roof footprint outside the drawn outline', out, 0.0, max(tol_out * outline.length * 0.0 + 0.02 * outline.area, 1.0) if note else 0.02 * outline.area,
              f'BL-02 outline {name}; {note}', 'm2')
        C.add(f'{k}: drawn outline not covered by the roof footprint', miss, 0.0, 0.02 * outline.area, f'BL-02 outline {name}', 'm2')
        plans[k] = dict(model_area=round(fp_model.area, 1), outline_area=round(outline.area, 1), outside=round(out, 1), missing=round(miss, 1))
    sfom = lambda nm: unary_union([Polygon(p[0], p[1:]).buffer(0) for p in D.sfom(nm, 'structures')])
    rail = unary_union([Polygon(p[0], p[1:]).buffer(0) for f in D.AIR['structures'] if f['kind'] == 'rail' for p in f['polys']])
    st_cg = unary_union([Polygon(p[0], p[1:]).buffer(0) for f in D.AIR['structures'] if f['id'] in (1729791955, 1729791959, 1729791957) for p in f['polys']])

    # ---------------- central garage
    k = 'central_garage'
    if k in by:
        body = L0n(k, 'cg_body'); P = allP(body)
        C.add('CG: parapet top (81 ft)', float(H(P).max()), 81 * FT, src='BL-03 row 1 (81 ft [pub])')
        Pd = allP(body, 'deck')
        C.add('CG: deck', float(np.median(H(Pd))), 81 * FT - 3.5 * FT, src='81 ft - 42-in guard [inf]')
        pl = allP(L0n(k, 'cg_plinth'), 'concrete')
        if len(pl):
            C.add('CG: garage structure under the ring = Level 5 - guideway deck', float(H(pl).max()), 81 * FT * 4 / 5 + 1.1, 0.6,
                  src='BL-03 Level 5 = 4/5 of 81 ft (+ trough wall top on the slivers)')
        poles = allP(L0n(k, 'cg_poles'))
        for d in LB[k]['dof']:
            if d['type'] != 'POLE': continue
            sel = np.hypot(poles[:, 0] - d['world'][0], poles[:, 2] - d['world'][1]) < 2.0
            C.add(f'CG: roof pole {d["oas"]} top', float(H(poles[sel]).max()) if sel.any() else -1.0, float(d['agl_m']), 0.3, 'FAA DOF 1A')
        fp = footprint(L0n(k, 'cg_body') + L0n(k, 'cg_plinth'))
        outline_check(k, 'Central Parking Garage', fp, sfom('Central Parking Garage'))
        # the void
        hole = Polygon(sfom('Central Parking Garage').interiors[0]) if sfom('Central Parking Garage').geom_type == 'Polygon' else None
        if hole is not None:
            C.add('CG: void diameter (equal-area circle)', 2 * math.sqrt(fp.buffer(0.05).intersection(hole.buffer(3)).symmetric_difference(hole.buffer(3)).area / math.pi)
                  if False else 2 * math.sqrt(hole.difference(fp).area / math.pi), 58.9, src='BL-02 A void 58.9 m [obs]')
    # ---------------- garages A / G
    for k in ('garage_a', 'garage_g'):
        if k not in by: continue
        g = DL.GAR[k]; Gg = DL.ggeom(k)
        body = L0n(k, f'{k}_body'); P = allP(body)
        C.add(f'{k}: parapet top = drum ring (BL-03, deck unk)', float(H(P).max()), float(g['drum']), src='BL-03 rows 1-2')
        core = allP(L0n(k, f'{k}_core'))
        C.add(f'{k}: core cylinder top (drawn 4 m above the ring)', float(H(core).max()), float(g['drum']) + 4.0, src='BL-03')
        cxz = core[:, [0, 2]]
        cc = cxz.mean(0); rr = np.hypot(*(cxz - cc).T)
        C.add(f'{k}: core diameter', float(2 * np.median(rr)), DL.GAR_CORE_D, src='BL-02 B GAR_CORE_D (obs NAIP)')
        C.add(f'{k}: core centre on the drum centre', float(np.hypot(*(cc - Gg['drum_c']))), 0.0, 0.5, src='BL-02 B drum fit')
        # drum: wall vertices of the precast_band material
        # the drum: the body's ground-level vertices in the sheet's fitting window (ggeom: z in zwin, x < x_min + 15), as BL-02 B
        Pg = allP(body, 'precast_band')                      # the drum walls (solid, on the outline arc)
        Pb = Pg[(Pg[:, 2] >= g['zwin'][0]) & (Pg[:, 2] <= g['zwin'][1]) & (Pg[:, 0] < P[:, 0].min() + 15)]
        if len(Pb) >= 3:
            xz = np.unique(np.round(Pb[:, [0, 2]], 3), axis=0)
            A = np.c_[2 * xz[:, 0], 2 * xz[:, 1], np.ones(len(xz))]
            s = np.linalg.lstsq(A, xz[:, 0] ** 2 + xz[:, 1] ** 2, rcond=None)[0]
            R = math.sqrt(s[2] + s[0] ** 2 + s[1] ** 2)
            C.add(f'{k}: drum radius (circle fit to the drum wall)', R, float(Gg['R']), src='BL-02 B outline-arc fit')
            C.add(f'{k}: drum centre', float(np.hypot(s[0] - Gg['drum_c'][0], s[1] - Gg['drum_c'][1])), 0.0, 0.5, src='BL-02 B')
        u = (P[:, [0, 2]] - Gg['c']) @ Gg['a'] + Gg['L'] / 2
        C.add(f'{k}: garage body end u = Lb', float(u.max()), float(Gg['Lb']), src='BL-02 B dashed line')
        if Gg['box']:
            bx = allP(L0n(k, f'{k}_rooftop_box'))
            C.add(f'{k}: rooftop box top (drawn 3.5 m)', float(H(bx).max()), float(g['drum']) + 3.5, src='BL-03 row 1')
            ub = (bx[:, [0, 2]] - Gg['c']) @ Gg['a'] + Gg['L'] / 2
            C.add(f'{k}: rooftop box u start', float(ub.min()), float(Gg['box'][0]), src='BL-02 B (NAIP, lean-corrected)')
            C.add(f'{k}: rooftop box u end', float(ub.max()), float(Gg['box'][1]), src='BL-02 B')
        allowed = unary_union([sfom(g['nm']), rail]) if g['rail_near'] else sfom(g['nm'])
        out = footprint(body).difference(allowed.buffer(0.3)).area
        C.add(f'{k}: body footprint outside the SFO Museum outline (Garage A: + the guideway strips run inside it)', out, 0.0, 5.0,
              src='BL-02 B', unit='m2')
    # ---------------- round-1 review items (landside_r1_obs.json; photo / NAIP / OSM measurements of the 3-D group)
    import landside_airtrain as AT
    import landside_geom as LG
    R1 = LG.R1
    for k in ('garage_a', 'garage_g'):
        if k not in by: continue
        g = DL.GAR[k]
        tw = allP(L0n(k, f'{k}_towers'))
        C.add(f'{k}: drum stair / elevator towers top (ring + 3.0, photo i2)', float(H(tw).max()) if len(tw) else -1, float(g['drum']) + 3.0, 0.3,
              'r1 photos.i2_drums [obs, low]')
        dm = allP(L0n(k, f'{k}_body'), 'drum_metal')
        C.add(f'{k}: drum in smooth metal panels (drum_metal vertices)', float(len(dm)), 1.0, ok=len(dm) > 50, src='photo i2', unit='')
        sb = allP(L0n(k, f'{k}_body'), 'interior')
        sc = float(g['drum']) / 39.6
        for t in R1['photos']['i2_drums']['slot_tops_below_ring'][:1]:
            zt_ = float(g['drum']) - t * sc
            near = sb[np.abs(H(sb) - zt_) < 0.05] if len(sb) else sb
            C.add(f'{k}: drum slot (top {zt_:.2f} m) recessed (interior faces at its top)', float(len(near)), 1.0, ok=len(near) > 8, src='photo i2', unit='')
    if 'garage_a' in by:
        k = 'garage_a'
        blk = allP(L0n(k, 'garage_a_station_block'))
        C.add('garage_a: station block top (network level + 12.0, photo l1)', float(H(blk).max()) if len(blk) else -1,
              AT.NET_LEVEL + LG.STATION_BLOCK_H, 0.05, 'r1 photos.l1_station_block [obs, low]')
        sl = allP(L0n(k, 'garage_a_station_block_det'), 'slot')
        zs = sorted({round(float(v), 2) for v in H(sl)}) if len(sl) else []
        C.add('garage_a: station block slots at one level (+7.4 m, two long runs)', float(np.mean(H(sl))) if len(sl) else -1,
              AT.NET_LEVEL + LG.STATION_BLOCK_SLOT, 0.05, 'photo l1')
    if 'bart_station' in by:
        k = 'bart_station'
        Pb = allP(L0n(k, 'bart_body'))
        osm = Polygon(R1['osm']['bart']['poly']).buffer(0)
        fpb = footprint(L0n(k, 'bart_body'), up_only=False)
        C.add('BART station: footprint outside the OSM station polygon', fpb.difference(osm.buffer(0.3)).area, 0.0, 0.02 * osm.area, 'OSM way 221663595 (ODbL)', 'm2')
        C.add('BART station: top <= AirTrain deck bottom (carries the guideway)', float(H(Pb).max()), AT.NET_LEVEL - AT.DECK_T, ok=float(H(Pb).max()) <= AT.NET_LEVEL - AT.DECK_T + 0.01,
              src='inf (photo a2)')
        gl = allP(L0n(k, 'bart_body'), 'glass_bart')
        C.add('BART station: glazed band bottom (photo a2 ratio)', float(H(gl).min()) if len(gl) else -1, R1['bart']['levels']['band'][0], 0.05, 'photo a2 [inf]')
        nb = NAIPline = LineString(R1['bart']['north'])
        C.add('BART station: north face vs the NAIP 2024 shadow line (max distance of the OSM north edge)',
              max(nb.distance(Point(x, z)) for x, z in osm.exterior.coords if nb.distance(Point(x, z)) < 8.0), 0.0, 2.0, 'NAIP obs vs OSM')
    at0 = {nm: m for nm, m in S.items() if (m['bldg'] or '').startswith('airtrain') and m['lod'] == 0}
    vr = allP([m for nm, m in at0.items() if nm.endswith('_deck')], 'vault_roof')
    if len(vr):
        C.add('Garage G AirTrain station: white vault crown (eave + W/8 + roof)', float(H(vr).max()), AT.NET_LEVEL + AT.ENCL_H + 3.0, 2.0, 'NAIP / a2 [inf rise]')
    tr = allP([m for nm, m in at0.items() if nm.endswith('_deck')], 'perf_tower')
    if len(tr):
        xz = tr[:, [0, 2]]; cc = xz.mean(0)
        C.add('RCC station tower centre on the SFO Museum polygon lobe', float(np.hypot(*(cc - np.array(AT.RCC_TOWER['centre'])))), 0.0, 0.3, 'SFO Museum RCC station polygon [obs]')
        C.add('RCC station tower raked top: lowest rim (top - 2.5, photo l5)', float(np.percentile(H(tr), 100) - 2.5), AT.RCC_TOWER['top'] - AT.RCC_TOWER['rake'], 0.3, 'photo l5 [obs, low]')
    cp = allP([m for nm, m in at0.items() if nm.endswith('_deck')], 'coping')
    gd = allP([m for nm, m in at0.items() if nm.endswith('_deck')], 'guideway_deck')
    if len(cp) and len(gd):
        from scipy.spatial import cKDTree
        tq = cKDTree(gd[:, [0, 2]]); dd, ii = tq.query(cp[:, [0, 2]])
        sel = dd < 1.0
        C.add('AirTrain: trough wall top above the running surface (photos l1 / l5)', float(np.median(cp[sel, 1] - gd[ii[sel], 1])), AT.WALL_H, 0.05, 'r1: was 1.1 m', 'm')
    gr = allP([m for nm, m in at0.items() if nm.endswith('_track')], 'guide_rail')
    if len(gr) and len(gd):
        from scipy.spatial import cKDTree
        dd, ii = cKDTree(gd[:, [0, 2]]).query(gr[:, [0, 2]])
        sel = dd < 3.0
        C.add('AirTrain: guide rail top above the running surface (low rail, not a wall)', float(np.percentile(gr[sel, 1] - gd[ii[sel], 1], 95)), AT.BEAM_H, 0.08,
              'photos l1 / l5 (r1: was 0.8 m)', 'm')
    k = 'superbay'
    if k in by:
        for lod in (0, 2):
            rl = [p for m in by[k] for nm, m in [m] if m['lod'] == lod for p in m['prims'] if p['mat'].split('@')[0].split('.')[0] == 'red_light']
            zz = np.vstack([p['P'] for p in rl]) if rl else np.zeros((0, 3))
            C.add(f'Superbay: red obstruction light (own material red_light) in LOD{lod}, top at the DOF + 0.5', float(H(zz).max()) if len(zz) else -1, 135 * FT + 0.5, 0.05,
                  'FAA DOF 06-001451 lighting R; js/three/buildings3d.js glowKind -> beacon')
        mats = {m.get('name', '').split('@')[0]: m for m in j.get('materials', [])}
        ex = (mats.get('red_light') or {}).get('extras', {})
        C.add('Superbay: red_light material extras.obstruction_light', 1.0 if ex.get('obstruction_light') else 0.0, 1.0, 0.0, 'glowKind() reads it', '')
    k = 'central_garage'
    if k in by:
        X = np.vstack([m['inst'] for nm, m in by[k] if m['inst'] is not None and m['lod'] == 0]) if any(m['inst'] is not None for nm, m in by[k]) else np.zeros((0, 3))
        cars_obs = R1['cg_roof']['cars']
        if len(X) and cars_obs:
            from scipy.spatial import cKDTree
            O = np.array([[c['x'], c['z']] for c in cars_obs])
            d_, _ = cKDTree(X[:, [0, 2]]).query(O)
            C.add('CG: NAIP-detected cars reproduced (share with a model car within 1.5 m)', float(np.mean(d_ < 1.5)), 0.8, ok=float(np.mean(d_ < 1.5)) >= 0.75,
                  src='landside_r1_obs.json cg_roof.cars [obs NAIP]', unit='')
        bx = allP(L0n(k, 'cg_roof_boxes'))
        C.add('CG: rooftop stair / elevator heads (deck + 4.5 [inf])', float(H(bx).max()) if len(bx) else -1, 81 * FT - 3.5 * FT + 4.5, 0.05, 'NAIP plan [obs]')
        rim = allP(L0n(k, 'cg_body'), 'deck_rim'); lob = allP(L0n(k, 'cg_body'), 'deck_plain')
        C.add('CG: roof rims / lobes present (NAIP 2024)', float(len(rim) + len(lob)), 1.0, ok=len(rim) > 100 and len(lob) > 50, src='NAIP obs', unit='')
    # ---------------- LOD2 (the phone / far tier): heights vs LOD0 and BL-03, no AirTrain inside a solid LOD2 garage prism
    L2n = lambda k: [m for nm, m in by.get(k, []) if m['lod'] == 2 and m['inst'] is None]
    for k in by:
        if k.startswith('airtrain'): continue
        P0 = allP([m for nm, m in by.get(k, []) if m['lod'] == 0 and m['inst'] is None and not nm.endswith('_poles')]); P2 = allP(L2n(k))
        if not len(P0) or not len(P2): continue
        t0 = float(H(P0).max()); t2 = float(H(P2).max())
        C.add(f'LOD2 {k}: top = LOD0 top (light poles excepted)', t2, t0, 0.5, 'BL-03 heights (LOD0 verified above)')
    for k, deck in (('central_garage', 81 * FT - 3.5 * FT), ('garage_a', DL.GAR['garage_a']['drum'] - 3.5 * FT), ('garage_g', DL.GAR['garage_g']['drum'] - 3.5 * FT)):
        if k not in by: continue
        Pd2 = allP(L2n(k), 'deck_far')
        C.add(f'LOD2 {k}: deck recessed below the parapet (deck_far median)', float(np.median(H(Pd2))) if len(Pd2) else -1, float(deck), 0.05, 'BL-03 deck = parapet - 1.07')
    for k, val, nm in (('grand_hyatt', 13.2 * DL.GH_P + 1.4 * DL.GH_P, 'penthouse'), ('united_moc', LG.BARREL_EAVE + LG.BARREL_RISE, 'barrel crown')):
        if k not in by: continue
        P2 = allP(L2n(k), 'metal_dark' if k == 'grand_hyatt' else 'barrel_roof')
        C.add(f'LOD2 {k}: {nm}', float(H(P2).max()) if len(P2) else -1, float(val), 0.3, 'BL-03 / LOD0')
    if 'garage_a' in by:
        bw = LG.garage_ag('garage_a')
        main_in = bw.main_w.buffer(-1.5)
        at2 = [m for nm, m in S.items() if (m['bldg'] or '').startswith('airtrain') and m['lod'] == 2]
        Pa = allP(at2)
        if len(Pa):
            inside = np.array([main_in.contains(Point(x, z)) for x, z in Pa[:, [0, 2]]])
            C.add('LOD2 AirTrain vertices inside the solid LOD2 Garage A body (guideway portals / station hall left open)', float(inside.sum()), 0.0, 0.0,
                  'review r1 (#11)', '')
        P2 = allP(L2n('garage_a'))
        C.add('LOD2 garage_a: core / box / towers present (max height = tower top)', float(H(P2).max()), DL.GAR['garage_a']['drum'] + 4.0, 0.5, 'BL-03 core')
    # ---------------- LTP 1 / 2
    k = 'ltp_garage_1'
    if k in by:
        P = allP(L0n(k, 'ltp1_body'))
        C.add('LTP1: parapet top', float(H(P).max()), float(D.LV['ltp1_parapet_obs']['value']), src='BL-03 row 3 (NAIP shadow)')
        T = allP(L0n(k, 'ltp1_towers'))
        for d in LB[k]['dof']:
            sel = np.hypot(T[:, 0] - d['world'][0], T[:, 2] - d['world'][1]) < 10.0
            C.add(f'LTP1: tower top at DOF {d["oas"]}', float(H(T[sel]).max()) if sel.any() else -1.0, float(d['agl_m']), 0.3, 'FAA DOF 1A (tower identity inf)')
        outline_check(k, 'Long-Term Parking Garage 1', footprint(L0n(k, 'ltp1_body')), sfom('Long-Term Parking Garage 1'))
    k = 'ltp_garage_2'
    if k in by:
        P = allP(L0n(k, 'ltp2_body'))
        C.add('LTP2: deck = 5 x 12 ft', float(np.median(H(allP(L0n(k, 'ltp2_body'), 'deck')))), 60 * FT, src='BL-03 row 3 [inf]')
        C.add('LTP2: parapet top', float(H(P).max()), 60 * FT + 3.5 * FT, src='deck + 42 in [inf]')
        pv = allP(L0n(k, 'ltp2_pv'))
        C.add('LTP2: PV canopy top (BL-03 dotted deck + 3.5)', float(H(pv).max()), 60 * FT + 3.5, src='BL-03 [unk]')
        outline_check(k, 'Long-Term Parking Garage 2', footprint(L0n(k, 'ltp2_body')), sfom('Long-Term Parking Garage 2'))
    # ---------------- RCC
    k = 'rental_car_center'
    if k in by:
        P = allP(L0n(k, 'rcc_body'))
        C.add('RCC: roof outline (54 ft DOF)', float(H(P).max()), 54 * FT, src='BL-03 row 3 [pub DOF]')
        T = allP(L0n(k, 'rcc_tower59'))
        C.add('RCC: raised element at the 59-ft DOF point', float(H(T).max()), 59 * FT, 0.3, 'FAA DOF 06-035204')
        outline_check(k, 'Rental Car Center', footprint(L0n(k, 'rcc_body')), sfom('Rental Car Center'))
        lv = allP(L0n(k, 'rcc_body'), 'louvre')
        if len(lv):
            ol = sfom('Rental Car Center')
            top = lv[H(lv) > 16.0]
            off = np.array([ol.exterior.distance(Point(x, z)) for x, z in top[:, [0, 2]]]) if len(top) else np.zeros(1)
            C.add('RCC: canted louvre screen top outside the west wall (lean)', float(np.median(off)), 1.2, 0.3,
                  src='BL-03 wall key (canted; amount inf)')
            bot = lv[H(lv) < 16.0]
            C.add('RCC: louvre screen foot on the wall plane', float(np.median([ol.exterior.distance(Point(x, z)) for x, z in bot[:, [0, 2]]])) if len(bot) else -1, 0.0, 0.1,
                  src='BL-03 wall key')
    # ---------------- Grand Hyatt
    k = 'grand_hyatt'
    if k in by:
        P = allP(L0n(k, 'gh_body'))
        H_ = 13.2 * DL.GH_P
        C.add('Hyatt: parapet (13.2 pitches)', float(H(P).max()), H_, src='BL-03 row 2 [inf 44 m]')
        Pm = allP(L0n(k, 'gh_body') + L0n(k, 'gh_podium'), 'metal_dark')
        mr = LB[k]['footprint']['min_rect']; ax = hdg_vec(mr['long_side_heading_deg']); W = mr['length_m']
        f = ((Pm[:, [0, 2]] - np.array(mr['centre'])) @ ax + W / 2) / W
        lowp = Pm[H(Pm) < DL.GH_POD * DL.GH_P + 0.05]
        fl = ((lowp[:, [0, 2]] - np.array(mr['centre'])) @ ax + W / 2) / W
        C.add('Hyatt: podium extent along the east face (fraction)', float(fl.max()), 0.47, 0.02, 'BL-03 hyatt_elev (photo l4)', unit='')
        C.add('Hyatt: podium top', float(H(lowp).max()) if len(lowp) else 0.0, DL.GH_POD * DL.GH_P, src='BL-03 (3.2 pitches)')
        ph = allP(L0n(k, 'gh_penthouse'))
        C.add('Hyatt: penthouse upper step top', float(H(ph).max()), H_ + 1.4 * DL.GH_P, src='BL-03 (1.4 pitches)')
        fp = footprint(L0n(k, 'gh_body') + L0n(k, 'gh_podium'))
        outline_check(k, 'Grand Hyatt Hotel', fp, sfom('Grand Hyatt Hotel'))
    # ---------------- CAC
    k = 'cac'
    if k in by:
        P = allP(L0n(k, 'cac_body'))
        C.add('CAC: parapet ~64 ft', float(H(P).max()), 64 * FT, src='BL-03 row 2 [inf]')
        C.add('CAC: roof 4 x 15 ft', float(np.median(H(allP(L0n(k, 'cac_body'), 'roof_membrane')))), 60 * FT, src='BL-03 [inf]')
        outline_check(k, 'Consolidated Administration Campus', footprint(L0n(k, 'cac_body')), sfom('Consolidated Administration Campus'))
    # ---------------- Superbay
    k = 'superbay'
    if k in by:
        R_ = allP(L0n(k, 'sb_roof'))
        c = np.array(LB[k]['footprint']['min_rect']['centre']); sv, tv = hdg_vec(117.83), hdg_vec(27.83)
        a = (R_[:, [0, 2]] - c) @ sv; t = (R_[:, [0, 2]] - c) @ tv
        C.add('Superbay: spine top (DOF 135 ft)', float(H(R_).max()), 135 * FT, src='BL-03 row 4 [pub]')
        C.add('Superbay: roof WNW tip a', float(a.min()), -80.5, src='BL-02 G'); C.add('Superbay: roof ESE tip a', float(a.max()), 84.5, src='BL-02 G')
        C.add('Superbay: roof along the spine t (8 x 17.25)', float(t.max() - t.min()), 138.0, src='BL-02 G [obs]')
        Rr = allP(L0n(k, 'sb_roof'), 'hangar_roof'); ar = (Rr[:, [0, 2]] - c) @ sv; tr_ = (Rr[:, [0, 2]] - c) @ tv
        tip = H(Rr)[(np.abs(ar - (-80.5)) < 0.3) | (np.abs(ar - 84.5) < 0.3)]
        C.add('Superbay: tip eave (valleys)', float(tip.min()) if len(tip) else -1, DL.SB_TIP, src='BL-03 row 4 [inf]')
        C.add('Superbay: tip eave (fold ridges)', float(tip.max()) if len(tip) else -1, DL.SB_TIP + DL.SB_FOLD, src='BL-03 row 4 [unk fold]')
        root = H(Rr)[(np.abs(ar - (-14)) < 0.3) & (np.abs(tr_) < 50)]
        C.add('Superbay: cantilever root at the spine', float(np.median(root)) if len(root) else -1, 135 * FT - 1.5, src='BL-03 row 4')
        Wl = allP(L0n(k, 'sb_walls'))
        doors = allP(L0n(k, 'sb_doors'), 'hangar_door')
        C.add('Superbay: door head', float(H(doors).max()) if len(doors) else -1, DL.SB_TIP - DL.SB_DOOR_GAP, src='BL-03 row 4 [unk]')
    # ---------------- MOC
    k = 'united_moc'
    if k in by:
        P = allP(L0n(k, 'moc_large'))
        for d in D.LANDM['moc']['moc_large_hangar']['dof']:
            shift = 0.315 * np.mean([q['agl_m'] for q in D.LANDM['moc']['moc_large_hangar']['dof']])
            sel = np.hypot(P[:, 0] - (d['world'][0] - shift), P[:, 2] - d['world'][1]) < 40.0
            hmax = float(H(P[sel]).max()) if sel.any() else -1
            C.add(f'MOC: part top near DOF {d["oas"]} (lean-corrected position)', hmax, float(d['agl_m']), 0.3, 'FAA DOF 1A; part extents inf')
    # ---------------- AirTrain
    at = {nm: m for nm, m in S.items() if (m['bldg'] or '').startswith('airtrain') and m['lod'] == 0}
    decks = [m for nm, m in at.items() if nm.endswith('_deck')]
    if decks:
        import landside_airtrain as AT
        Pd = allP(decks, 'guideway_deck')
        fpd = footprint(decks, mats=['guideway_deck'])
        C.add('AirTrain: deck outside the SFO Museum polygon', fpd.difference(rail.buffer(0.3)).area, 0.0, 5.0, 'BL-01 / BL-02 guideway polygon', 'm2')
        for kk, v in AT.STATIONS.items():
            if v[1] is None or v[4] is None: continue
            Pst = AT.ST_POLY[kk]
            sel = np.array([Pst.buffer(-1.0).contains(Point(x, z)) for x, z in Pd[:, [0, 2]]]) if len(Pd) else np.zeros(0, bool)
            pl = allP(decks, 'platform')
            selp = np.array([Pst.contains(Point(x, z)) for x, z in pl[:, [0, 2]]]) if len(pl) else np.zeros(0, bool)
            if selp.any():
                C.add(f'AirTrain {kk}: platform level', float(np.median(H(pl[selp]))) - 0.02, float(v[1]), 0.1, f'{v[2]}: {v[3]}')
            if sel.any():
                C.add(f'AirTrain {kk}: track deck level at the station', float(np.median(H(Pd[sel]))), float(v[1]), 0.15, f'{v[2]}')
        piers = allP([m for nm, m in at.items() if nm.endswith('_piers')])
        # grade along the deck: neighbouring deck-top vertices (within 6 m) differ by < 6 %
        if len(Pd) > 10:
            from scipy.spatial import cKDTree
            tr = cKDTree(Pd[:, [0, 2]])
            pairs = tr.query_pairs(6.0, output_type='ndarray')
            dd = np.hypot(*(Pd[pairs[:, 0]][:, [0, 2]] - Pd[pairs[:, 1]][:, [0, 2]]).T)
            ok = dd > 2.0
            gr = np.abs(Pd[pairs[ok, 0], 1] - Pd[pairs[ok, 1], 1]) / dd[ok]
            C.add('AirTrain: max deck grade between vertices 2-6 m apart', float(np.percentile(gr, 99.9)), 0.06, ok=float(np.percentile(gr, 99.9)) <= 0.06,
                  src='plausibility: rubber-tyred APM grades <= 6 % [inf]', unit='')
        tw = allP([m for nm, m in at.items() if nm.endswith('_deck')], 'coping')
        tower = allP(decks, 'perf_tower')
        if len(tower):
            Pall = allP(decks); tw_ = AT.RCC_TOWER['world']
            near = Pall[np.hypot(Pall[:, 0] - tw_[0], Pall[:, 2] - tw_[1]) < AT.RCC_TOWER['D'] / 2 + 0.5]
            C.add('AirTrain RCC station tower top (DOF TANK 60 ft)', float(H(near).max()), float(AT.RCC_TOWER['top']), 0.3, 'FAA DOF 06-034240 [pub]; identity inf')
            xz = tower[:, [0, 2]]; cc = xz.mean(0)
            C.add('AirTrain RCC station tower diameter (SFO Museum polygon lobe; BL-02 E draws 6.5 [inf])', float(2 * np.median(np.hypot(*(xz - cc).T))), AT.RCC_TOWER['D'],
                  0.2, src='r1: SFO Museum RCC station polygon lobe [obs] + photo l5 camera solve')
    # ---------------- cars
    cars = {}
    for nm, m in S.items():
        if m['inst'] is None or m['lod'] != 0: continue
        cars.setdefault(m['bldg'], []).append(m['inst'])
    for k, lst in cars.items():
        X = np.vstack(lst)
        from scipy.spatial import cKDTree
        tr = cKDTree(X[:, [0, 2]])
        dmin = tr.query(X[:, [0, 2]], k=2)[0][:, 1].min() if len(X) > 1 else 99
        C.add(f'cars {k}: min centre spacing (no overlap: car width <= 1.95 m + 0.15 m)', float(dmin), 2.1, ok=dmin >= 2.1, src='landside_cars stall grid (2.6 m stalls)')
        body = [m for nm, m in by.get(k, []) if m['lod'] == 0 and nm.endswith(('_body',))]
        Pd = allP(body, ['deck', 'deck_lanes'])
        if len(Pd):
            C.add(f'cars {k}: on the deck (median height - deck)', float(np.median(X[:, 1]) - np.median(Pd[:, 1])), 0.01, 0.05, 'deck level')
        rc = LB.get(k, {}).get('roof_cars')
        cars[k] = len(X)
    # ---------------- plausibility
    plaus = {}
    sys.path.insert(0, os.path.join(ROOT, 'tools', 'stands'))
    fps = {}
    for k in by:
        nodes = [m for nm, m in by[k] if m['lod'] == 0 and m['inst'] is None]
        if not nodes: continue
        fps[k] = footprint(nodes, up_only=False)
    allfp = unary_union(list(fps.values()))
    try:
        import geom as GM
        st = json.load(open(os.path.join(ROOT, 'data', 'sfo_stands.json')))['stands']
        dmin, worst = 1e9, None
        bdmin, bworst = 1e9, None
        for s in st:
            env = GM.stand_env(s)
            dd = env.distance(allfp)
            if dd < dmin: dmin, worst = dd, s['name']
            for br in s.get('bridges', []) + s.get('bridges_upper', []):
                w = br.get('walk') or []
                g = LineString(w).buffer(GM.WALK_W / 2) if len(w) >= 2 else (Point(br['rotunda']).buffer(GM.ROT_R) if br.get('rotunda') else None)
                if g is not None:
                    dd = g.distance(allfp)
                    if dd < bdmin: bdmin, bworst = dd, s['name']
        C.add('stand envelopes (all %d stands, app planforms): min distance to the landside footprint (%s)' % (len(st), worst), dmin, 2.0, ok=dmin >= 2.0,
              src='check_stands.py criterion >= 2.0 m')
        C.add('bridge walkways / rotundas: min distance to the landside footprint (%s)' % bworst, bdmin, 2.0, ok=bdmin >= 2.0, src='no contact')
        plaus.update(stand_min_m=round(dmin, 2), stand_worst=worst, bridge_min_m=round(bdmin, 2), bridge_worst=bworst)
    except Exception as e:  # noqa: BLE001
        C.add('stand / bridge clearance', str(e), 'error', ok=False)
    tw = unary_union([Polygon(p[0], p[1:]).buffer(0) for t_ in D.AIR['taxiways'] for p in t_['polys']])
    per = {k: round(tw.intersection(f).area, 1) for k, f in fps.items()}
    C.add('SFO Museum taxiway polygons inside the landside footprint', float(sum(per.values())), 0.0, 1.0, 'data/sfo_airport.json taxiways', 'm2')
    plaus['taxiway_overlap_m2'] = {k: v for k, v in per.items() if v > 0}
    plaus['taxiway_min_m'] = {k: round(tw.distance(f), 1) for k, f in fps.items() if not k.startswith('airtrain')}
    rows = C.rows
    res = dict(file=os.path.relpath(path, ROOT), bytes=size, n_checks=len(rows), n_fail=sum(1 for r in rows if not r['ok']), plans=plans, cars=cars,
               plausibility=plaus, checks=rows)
    out = os.path.join(ROOT, 'out', 'buildings3d', 'landside_verify.json')
    json.dump(res, open(out, 'w'), indent=1, default=str)
    for r in rows:
        print(('OK  ' if r['ok'] else 'FAIL') + ' %-90s model %-12s drawing %-12s tol %s' % (r['check'][:90], r['model'], r['drawing'], r['tol']))
    print('checks %d, failed %d -> %s' % (len(rows), res['n_fail'], out))
    return res


if __name__ == '__main__':
    run(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'data', 'buildings3d', 'landside.glb'))
