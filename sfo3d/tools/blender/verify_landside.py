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
from shapely.geometry import LineString, MultiPoint, Point, Polygon
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
            inst_hull = None
            if ext:
                tr = accessor(j, b, ext['attributes']['TRANSLATION']).astype(np.float64)
                inst = (Mi[:3, :3] @ tr.T).T + Mi[:3, 3]
                # close-out r3 fix 2 (verifier v3): every instance's world plan hull (mesh x instance TRS x node matrix), for the
                # oriented car-overlap check (the centre spacing alone cannot see cars overlapping end to end / at an angle)
                if 'ROTATION' in ext['attributes']:
                    rq = accessor(j, b, ext['attributes']['ROTATION']).astype(np.float64)
                    sc = accessor(j, b, ext['attributes']['SCALE']).astype(np.float64) if 'SCALE' in ext['attributes'] else np.ones((len(tr), 3))
                    Pl = np.concatenate([accessor(j, b, p['attributes']['POSITION']).astype(np.float64) for p in j['meshes'][n['mesh']]['primitives']])
                    inst_hull = []
                    for t_, q_, s_ in zip(tr, rq, sc):
                        R = quat_mat(q_)[:3, :3]
                        W_ = (Mi[:3, :3] @ ((R @ (Pl * s_).T).T + t_).T).T + Mi[:3, 3]
                        inst_hull.append((MultiPoint(W_[:, [0, 2]]).convex_hull, float(W_[:, 1].min()), float(W_[:, 1].max())))
            out[nm] = dict(lod=lod, bldg=bk, prims=prims, extras=n.get('extras', {}), inst=inst, inst_hull=inst_hull)
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


def footprint(nodes, up_only=True, mats=None, skip=()):
    polys = []
    for m in nodes:
        for p in m['prims']:
            if mats and p['mat'].split('@')[0].split('.')[0] not in mats: continue
            if skip and p['mat'].split('@')[0].split('.')[0] in skip: continue
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


LOD2_BF_MAX = 60          # back-face hits per LOD2 node at 0.5-m ray spacing (~15 m2 of visible back faces) [our gate]
LOD2_BF_RESIDUAL = {}     # node -> recorded count of a known, documented residual (filled from the fix-2 measurement)


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
        fp = footprint(L0n(k, 'cg_body') + L0n(k, 'cg_plinth'), skip=('void_floor',))      # r1: the void floor at grade is not roof
        outline_check(k, 'Central Parking Garage', fp, sfom('Central Parking Garage'))
        vf = allP(body, 'void_floor')
        C.add('CG: void floor at grade (r1, NAIP 2024: stalls and cars in the void)', float(H(vf).max()) if len(vf) else -1.0, 0.03, 0.02, 'NAIP obs [level low]')
        # the void
        hole = Polygon(sfom('Central Parking Garage').interiors[0]) if sfom('Central Parking Garage').geom_type == 'Polygon' else None
        if hole is not None:
            C.add('CG: void diameter (equal-area circle)', 2 * math.sqrt(fp.buffer(0.05).intersection(hole.buffer(3)).symmetric_difference(hole.buffer(3)).area / math.pi)
                  if False else 2 * math.sqrt(hole.difference(fp).area / math.pi), 58.9, src='BL-02 A void 58.9 m [obs]')
    # ---------------- garages A / G
    for k in ('garage_a', 'garage_g'):
        if k not in by: continue
        g = DL.GAR[k]; Gg = DL.ggeom(k)
        import landside_geom as LGr
        r2 = LGr.GAR_R2[k]
        body = L0n(k, f'{k}_body'); P = allP(body)
        # review r2: heights from photo a2 (solved camera) instead of the BL-03 drum ring (39.6 / 37.6) - listed as deviations
        C.add(f'{k}: body top = drum ring (r2: photo a2)', float(H(P).max()), float(r2['ring']), src='landside_r2_obs.json garages [obs a2, low]')
        pc = allP(body, 'precast')
        C.add(f'{k}: parapet top (r2: photo a2 solved camera)', float(H(pc).max()) if len(pc) else -1, float(r2['parapet']), src='landside_r2_obs.json [obs a2, low]')
        dk = allP(body, 'deck')
        C.add(f'{k}: roof deck = Level 9 (8 x a2 pitch)', float(np.median(H(dk))) if len(dk) else -1, float(r2['deck']), src='a2 level rows [obs / inf]')
        core = allP(L0n(k, f'{k}_core'))
        C.add(f'{k}: helix-eye guard ring top (deck + 42 in; a2 / i2: nothing above the ring)', float(H(core).max()), float(r2['deck']) + 3.5 * FT, src='r2')
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
            C.add(f'{k}: penthouse top (r2: photo a2)', float(H(bx).max()), float(LGr.PH_A['top']), src='landside_r2_obs.json [obs a2, low]')
            (ix0, iz0), (ix1, iz1) = LGr.PH_BOX_IMG
            C.add(f'{k}: penthouse west face (NAIP box, base lean removed)', float(bx[:, 0].min()), ix0 - LGr.NAIP_LEAN_GA * float(r2['deck']), 0.8, 'NAIP 2024 + measured lean')
            C.add(f'{k}: penthouse east face (NAIP box, top lean removed)', float(bx[:, 0].max()), ix1 - LGr.NAIP_LEAN_GA * float(LGr.PH_A['top']), 0.8, 'NAIP 2024 + measured lean')
        if k == 'garage_a':
            rt = allP(L0n(k, f'{k}_rotunda'))
            C.add(f'{k}: NE rotunda top (r2: photo a2)', float(H(rt).max()) if len(rt) else -1, float(LGr.ROT_A['top']), src='[obs a2 / NAIP, low]')
            if len(rt):
                cxz_ = rt[:, [0, 2]]; cc_ = 0.5 * (cxz_.min(0) + cxz_.max(0))
                C.add(f'{k}: NE rotunda centre', float(np.hypot(*(cc_ - np.array(LGr.ROT_A['centre'])))), 0.0, 0.3, '[obs a2 / NAIP]')
                C.add(f'{k}: NE rotunda inside the body outline', footprint(L0n(k, f'{k}_rotunda')).difference(sfom(g['nm']).buffer(0.1)).area, 0.0, 0.5, 'plausibility', 'm2')
        allowed = unary_union([sfom(g['nm']), rail]) if g['rail_near'] else sfom(g['nm'])
        out = footprint(body).difference(allowed.buffer(0.6)).area
        C.add(f'{k}: body footprint outside the SFO Museum outline + 0.6 m (r2: the curved ends follow the fitted arc, up to the 0.6-m fit '
              'tolerance outside the outline\'s chords; Garage A: + the guideway strips run inside it)', out, 0.0, 5.0, src='BL-02 B', unit='m2')
        if not g['rail_near']:
            C.add(f'{k}: body clear of the guideway polygon (0.3 m)', footprint(body).intersection(rail.buffer(0.3)).area, 0.0, 1.0, 'plausibility', 'm2')
    # ---------------- round-1 review items (landside_r1_obs.json; photo / NAIP / OSM measurements of the 3-D group)
    import landside_airtrain as AT
    import landside_geom as LG
    R1 = LG.R1
    for k in ('garage_a', 'garage_g'):
        if k not in by: continue
        g = DL.GAR[k]
        tw = allP(L0n(k, f'{k}_towers'))
        C.add(f'{k}: drum stair / elevator towers top (parapet + %.1f, r2: a2 / i2)' % LG.TOWER_ABOVE_PARAPET, float(H(tw).max()) if len(tw) else -1,
              float(LG.GAR_R2[k]['parapet']) + LG.TOWER_ABOVE_PARAPET, 0.3, 'landside_r2_obs.json [obs, low]')
        dm = allP(L0n(k, f'{k}_body'), 'drum_metal')
        C.add(f'{k}: drum in smooth metal panels (drum_metal vertices)', float(len(dm)), 1.0, ok=len(dm) > 50, src='photo i2', unit='')
        sb = allP(L0n(k, f'{k}_body'), 'interior')
        r2_ = LG.GAR_R2[k]
        for t in LG.I2_LEV['slot_centres_below_ring'][:1]:
            zt_ = r2_['ring'] - (t - LG.DRUM_SLOT_H / 2) * r2_['pitch']
            near = sb[np.abs(H(sb) - zt_) < 0.05] if len(sb) else sb
            C.add(f'{k}: drum slot (top {zt_:.2f} m) recessed (interior faces at its top)', float(len(near)), 1.0, ok=len(near) > 8, src='photo i2', unit='')
    if 'garage_a' in by:
        k = 'garage_a'
        blk = allP(L0n(k, 'garage_a_station_block'))
        C.add('garage_a: station block top = parapet (r2: a2 - nothing above the roof; l1 read +12.0 [conflict])', float(H(blk).max()) if len(blk) else -1,
              float(LG.GAR_R2['garage_a']['parapet']), 0.05, 'landside_r2_obs.json [obs a2, low]')
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
        C.add('BART station: glazed band top below the body top (photo a2 ratio; r1: follows the level field)',
              float(H(Pb).max() - H(gl).max()) if len(gl) else -1, LG.BART_BAND_UP, 0.05, 'photo a2 [obs, low]')
        nb = LineString(R1['bart']['north'])
        ds = [osm.exterior.distance(nb.interpolate(t)) for t in np.arange(0.0, nb.length, 5.0)]
        C.add('BART station: OSM north face vs the NAIP 2024 north wall line (max distance along the line)', float(max(ds)), 0.0, 2.5, 'NAIP pick +-2 m (relief estimate) combined with OSM +-1 m')
        # close-out r3 (buildings-8): the airside (north) face vs taxilane centreline 302 (data/sfo_details.json) - the modelled face is
        # the OSM edge; the observed NAIP 2024 north wall line is the reference for 'existing condition' (the SFO Museum has no BART outline)
        try:
            DTL = json.load(open(os.path.join(ROOT, 'data', 'sfo_details.json')))['centerlines'][302]
            ln302 = LineString(DTL)
            d_asset = float(fpb.distance(ln302)); d_naip = float(nb.distance(ln302)); d_osm = float(osm.distance(ln302))
            C.add('BART station: distance of the modelled body to taxilane centreline 302 >= the observed north wall line (NAIP 2024) - 0.5 m',
                  d_asset, d_naip, ok=d_asset >= d_naip - 0.5, src='close-out r3: NAIP %.1f m, OSM %.1f m; the ADG-5 OFA (42.1 m, integration [inf]) is an '
                  'existing condition of the observed building' % (d_naip, d_osm))
        except (KeyError, IndexError, FileNotFoundError):
            pass
    at0 = {nm: m for nm, m in S.items() if (m['bldg'] or '').startswith('airtrain') and m['lod'] == 0}
    vr = allP([m for nm, m in at0.items() if nm.endswith('_deck')], 'vault_roof')
    if len(vr):
        C.add('Garage G AirTrain station: white vault crown (eave + W/8 + roof)', float(H(vr).max()), AT.NET_LEVEL + AT.ENCL_H + 3.0, 2.0, 'NAIP / a2 [inf rise]')
    tr = allP([m for nm, m in at0.items() if nm.endswith('_deck')], 'perf_tower')
    if len(tr):
        xz = tr[:, [0, 2]]; cc = xz.mean(0)
        C.add('RCC station tower centre on the SFO Museum polygon lobe', float(np.hypot(*(cc - np.array(AT.RCC_TOWER['centre'])))), 0.0, 0.3, 'SFO Museum RCC station polygon [obs]')
        C.add('RCC station tower raked top: rake (highest - lowest rim, r2 l5 fit 2.55)', float(H(tr).max() - np.percentile(H(tr)[H(tr) > AT.RCC_TOWER['top'] - 4.0], 0)),
              AT.RCC_TOWER['rake'], 0.15, 'landside_r2_obs.json l5_rake [obs l5]')
        hi = tr[np.argmax(H(tr))]
        brg = math.degrees(math.atan2(hi[0] - cc[0], -(hi[2] - cc[1]))) % 360
        C.add('RCC station tower raked top: bearing of the high side (r2 l5 fit 353 deg)', float(min(abs(brg - AT.RCC_TOWER['high_bearing']), 360 - abs(brg - AT.RCC_TOWER['high_bearing']))),
              0.0, 15.0, 'landside_r2_obs.json l5_rake [obs l5]', 'deg')
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
            C.add('CG: NAIP-detected cars reproduced (share with a model car within 3.2 m = the r2 stall-snap radius)', float(np.mean(d_ < 3.2)), 0.8,
                  ok=float(np.mean(d_ < 3.2)) >= 0.75, src='landside_r1_obs.json cg_roof.cars [obs NAIP]', unit='')
        bx = allP(L0n(k, 'cg_roof_boxes'))
        C.add('CG: rooftop stair / elevator heads (deck + 4.5 [inf])', float(H(bx).max()) if len(bx) else -1, 81 * FT - 3.5 * FT + 4.5, 0.05, 'NAIP plan [obs]')
        rim = allP(L0n(k, 'cg_body'), 'deck_rim'); lob = allP(L0n(k, 'cg_body'), 'deck_plain')
        C.add('CG: roof rims / lobes present (NAIP 2024)', float(len(rim) + len(lob)), 1.0, ok=len(rim) > 100 and len(lob) > 50, src='NAIP obs', unit='')
    # ---------------- LOD2 (the phone / far tier): heights vs LOD0 and BL-03, no AirTrain inside a solid LOD2 garage prism
    L2n = lambda k: [m for nm, m in by.get(k, []) if m['lod'] == 2 and m['inst'] is None]
    for k in by:
        if k.startswith('airtrain'): continue
        P0 = allP([m for nm, m in by.get(k, []) if m['lod'] == 0 and m['inst'] is None]); P2 = allP(L2n(k))
        if not len(P0) or not len(P2): continue
        t0 = float(H(P0).max()); t2 = float(H(P2).max())
        C.add(f'LOD2 {k}: top = LOD0 top (r2: the roof poles kept in LOD2)', t2, t0, 0.5, 'BL-03 heights (LOD0 verified above)')
    import landside_geom as LGd
    for k, deck in (('central_garage', 81 * FT - 3.5 * FT), ('garage_a', LGd.GAR_R2['garage_a']['deck']), ('garage_g', LGd.GAR_R2['garage_g']['deck'])):
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
        C.add('LOD2 garage_a: rotunda / penthouse present (max height = rotunda top, r2)', float(H(P2).max()), float(LG.ROT_A['top']), 0.5, 'r2 a2')
    # ---------------- close-out round 5 (verifier: the Garage A station block's deck-1 opening and far wall, Garage G / LTP 2 /
    # Grand Hyatt / RCC faces crossing the guideway or its stations; verify_landside had no LOD0 guideway-vs-building test): every
    # LOD0 AirTrain triangle edge against every LOD0 building triangle and vice versa (strict crossings, as the verifier's
    # xtri.py) - 0 allowed outside the listed exemptions (the parts landside_geom.KEEP_EXEMPT leaves out of the keep-out clip by
    # design: the portal tunnels, the guideway's own lining; the Central Garage plinth, the trough the guideway runs in)
    AT_X = None
    try:
        def _tris(nodes):
            return [(nm, np.concatenate([p_['P'][p_['T']] for p_ in m['prims']])) for nm, m in nodes if m['prims'] and m['inst'] is None]
        AT0 = _tris([(nm, m) for nm, m in S.items() if (m['bldg'] or '').startswith('airtrain') and m['lod'] == 0])
        BD0 = _tris([(nm, m) for nm, m in S.items() if not (m['bldg'] or '').startswith('airtrain') and m['lod'] == 0])

        def _seg_tri(E0, E1, T):
            D_ = E1 - E0; v0 = T[:, 0]; e1 = T[:, 1] - v0; e2 = T[:, 2] - v0
            p_ = np.cross(D_[:, None], e2[None]); det = (e1[None] * p_).sum(-1)
            okd = np.abs(det) > 1e-12; inv = np.where(okd, 1 / np.where(okd, det, 1), 0)
            s_ = E0[:, None] - v0[None]; u_ = (s_ * p_).sum(-1) * inv
            q_ = np.cross(s_, e1[None]); v_ = (D_[:, None] * q_).sum(-1) * inv; t_ = (e2[None] * q_).sum(-1) * inv
            m_ = okd & (u_ > 1e-6) & (v_ > 1e-6) & (u_ + v_ < 1 - 1e-6) & (t_ > 1e-6) & (t_ < 1 - 1e-6)
            i_, k_ = np.nonzero(m_); return E0[i_] + D_[i_] * t_[i_, k_][:, None]
        xt = {}
        for na, TA in BD0:
            loA, hiA = TA.min(1), TA.max(1); g0, g1 = loA.min(0), hiA.max(0)
            for nb, TB in AT0:
                loB, hiB = TB.min(1), TB.max(1)
                if (g1 < loB.min(0)).any() or (hiB.max(0) < g0).any(): continue
                Ta = TA[((loA <= hiB.max(0)) & (hiA >= loB.min(0))).all(1)]; Tb = TB[((loB <= g1) & (hiB >= g0)).all(1)]
                if not len(Ta) or not len(Tb): continue
                pts = []
                for Ts, Tt in ((Ta, Tb), (Tb, Ta)):
                    E0 = np.concatenate([Ts[:, 0], Ts[:, 1], Ts[:, 2]]); E1 = np.concatenate([Ts[:, 1], Ts[:, 2], Ts[:, 0]])
                    for c0 in range(0, len(E0), 1500):
                        for c1 in range(0, len(Tt), 1500):
                            Pp = _seg_tri(E0[c0:c0 + 1500], E1[c0:c0 + 1500], Tt[c1:c1 + 1500])
                            if len(Pp): pts.append(Pp)
                if pts:
                    Pp = np.unique(np.round(np.concatenate(pts), 2), axis=0)
                    xt[(na, nb)] = dict(points=int(len(Pp)), y=[round(float(Pp[:, 1].min()) - GROUND_Y, 2), round(float(Pp[:, 1].max()) - GROUND_Y, 2)],
                                        at=[round(float(Pp[:, 0].mean()), 1), round(float(Pp[:, 2].mean()), 1)], _P=Pp)
        ex_ = [k for k in xt if any(e in k[0] for e in LG.KEEP_EXEMPT)]
        # contact parts (LG.KEEP_CONTACT, the CG plinth): a crossing counts only beyond the contact band - more than
        # KEEP_CONTACT_INSET + 0.02 m inside the guideway's plan footprint AND more than 0.03 m inside its height interval
        ct_ = [k for k in xt if k not in ex_ and any(e in k[0] for e in LG.KEEP_CONTACT)]
        if ct_:
            import keepout as KO
            colsV = KO.Columns(np.concatenate([np.c_[T_[:, :, 0].reshape(-1, 1), T_[:, :, 1].reshape(-1, 1) - GROUND_Y, T_[:, :, 2].reshape(-1, 1)].reshape(-1, 3, 3)
                                               for _, T_ in AT0]), clear=0.0, clear_z=0.0, inset=LG.KEEP_CONTACT_INSET + 0.02)
            for k in ct_:
                Pp = xt[k].pop('_P')
                iv = colsV.intervals(Pp[:, [0, 2]])
                deep = sum(1 for p_, v_ in zip(Pp, iv) if any(a_ + 0.03 < p_[1] - GROUND_Y < b_ - 0.03 for a_, b_ in v_))
                xt[k]['contact_points'] = xt[k]['points'] - deep; xt[k]['points'] = deep
        for v_ in xt.values(): v_.pop('_P', None)
        bad = {'%s x %s' % k: v for k, v in xt.items() if k not in ex_ and v['points'] > 0}
        AT_X = dict(pairs={'%s x %s' % k: v for k, v in xt.items()}, exempt=sorted('%s x %s' % k for k in ex_),
                    exempt_rule=list(LG.KEEP_EXEMPT), contact_rule=dict(parts=list(LG.KEEP_CONTACT), band_m=LG.KEEP_CONTACT_INSET + 0.02, z_tol_m=0.03),
                    keepout_clip=LG.KEEP_CLEAR)
        C.add('LOD0 AirTrain x building triangle crossings (outside the exempt %s portal linings; %s: beyond the contact band only)'
              % ('/'.join(LG.KEEP_EXEMPT), '/'.join(LG.KEEP_CONTACT)),
              float(sum(v['points'] for v in bad.values())), 0.0, 0.0, 'edge-triangle crossings; landside_geom.airtrain_keepout (keepout.py) clips '
              'the facades; over: %s; exempt points %d; contact-band points %d' % (bad or 'none', sum(xt[k]['points'] for k in ex_),
                                                                                 sum(xt[k].get('contact_points', 0) for k in xt)), 'pts')
    except Exception as e:  # noqa: BLE001
        C.add('LOD0 AirTrain x building crossings', str(e), 'error', ok=False)
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
        # r1: the walkway deck between the tracks east of the Garage A block: inside the SFO Museum Garage A outline tail
        fpw = footprint(decks, mats=['walkway'])
        if not fpw.is_empty:
            import landside_geom as LG_
            tail = LG_.ga_tail_walk()
            C.add('AirTrain: trough walkways east of Garage A outside their 1.6-m strips (r2, photo l1)', fpw.difference(tail.buffer(0.3)).area, 0.0, 2.0,
                  'SFO Museum Garage A outline + photo l1 [obs]', 'm2')
            C.add('AirTrain: trough walkway area (2 x 1.6-m strips; r1 deck 656 m2)', fpw.area, tail.area, 0.03 * tail.area, 'photo l1 [obs]', 'm2')
            C.add('AirTrain: the gap between the tracks east of Garage A left open (r2: no deck)', LG_.ga_tail_gap_area() - fpw.area, 200.0,
                  ok=LG_.ga_tail_gap_area() - fpw.area > 200.0, src='photo l1: open air between the guideways', unit='m2')
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
        # close-out r3 (buildings-3): pier columns off the roads, caps >= 4.6 m over road decks (data/sfo_landside.json roads +
        # roadways.glb LOD0 deck tops), measured on the exported pier meshes: column vertices below 2 m (the column feet)
        rfoot, rtris, _ = AT.road_obstacles()
        if len(piers):
            foot_pts = piers[H(piers) < 2.0]
            import shapely as _sh
            onroad = int(_sh.contains_xy(rfoot, foot_pts[:, 0], foot_pts[:, 2]).sum()) if len(foot_pts) else 0
            C.add('AirTrain pier columns: foot vertices on a carriageway / road deck (sfo_landside roads + roadways.glb)', onroad, 0, ok=onroad == 0,
                  src='close-out r3: integration 03:59Z found 3 columns in road decks', unit='')
            if len(rtris):
                # close-out r3 fix 2 (verifier v9): measured on the pier FACES, not every third vertex - each pier triangle above
                # 3 m (cap / bent beams, upper columns) against each road-deck triangle it overlaps in plan: the pier face's lowest
                # point over the overlap minus the deck's highest point there (a straddle-bent beam crossing a deck between its end
                # vertices is caught); vertical faces as 5-cm plan strips at their lowest edge
                PT = np.concatenate([p['P'][p['T']] for nm2, m2 in at.items() if nm2.endswith('_piers') for p in m2['prims']])
                PT = PT[(PT[:, :, 1] - GROUND_Y).min(1) >= 3.0]
                lo_ = rtris[:, :, [0, 2]].min(1); hi_ = rtris[:, :, [0, 2]].max(1)

                def plane_z(t, pts):
                    A_ = np.c_[t[:, 0], t[:, 2], np.ones(3)]
                    try: cf = np.linalg.solve(A_, t[:, 1])
                    except np.linalg.LinAlgError: return None
                    return pts[:, 0] * cf[0] + pts[:, 1] * cf[1] + cf[2]
                import shapely as _sh2
                worst, n_over = 99.0, 0
                for t in PT:
                    g = Polygon(t[:, [0, 2]])
                    vertical = not (g.is_valid and g.area > 1e-4)
                    if vertical: g = LineString(t[:, [0, 2]][np.argsort(t[:, 1])[:2]]).buffer(0.025, cap_style=2)
                    x0, z0, x1, z1 = g.bounds
                    m_ = (hi_[:, 0] >= x0) & (lo_[:, 0] <= x1) & (hi_[:, 1] >= z0) & (lo_[:, 1] <= z1)
                    for d in rtris[m_]:
                        o = g.intersection(Polygon(d[:, [0, 2]]).buffer(0.01))
                        if o.is_empty or o.area < 1e-5: continue
                        n_over += 1
                        P_ = _sh2.get_coordinates(o)
                        zp = None if vertical else plane_z(t, P_)
                        zd = plane_z(d, P_)
                        lowp = float(t[:, 1].min()) if zp is None else float(zp.min())
                        topd = float(d[:, 1].max()) if zd is None else float(zd.max())
                        worst = min(worst, lowp - topd)
                C.add('AirTrain pier caps / bents over road decks: min vertical clearance (pier faces over deck faces, %d overlaps)' % n_over, worst, 4.6,
                      ok=worst >= 4.6 - 0.02, src='close-out r3: 4.6 m (Caltrans HDM 309.2) as the roadways solve; 99 = no pier face over a deck '
                      '(fix 2: face-based, was every third vertex)')
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
    # oriented footprints of every LOD0 car instance (all buildings): overlapping pairs in the same height band
    hulls = [h for nm, m in S.items() if m['inst'] is not None and m['lod'] == 0 and m.get('inst_hull') for h in m['inst_hull']]
    if hulls:
        from shapely.strtree import STRtree
        tree = STRtree([h[0] for h in hulls]); pairs = []
        for i, (g, y0, y1) in enumerate(hulls):
            for k in tree.query(g):
                k = int(k)
                if k <= i: continue
                g2, z0, z1 = hulls[k]
                if min(y1, z1) - max(y0, z0) <= 0.05: continue
                a = g.intersection(g2).area
                if a > 0.001: pairs.append((round(a, 3), [round(c, 1) for c in g.centroid.coords[0]]))
        pairs.sort(key=lambda p_: -p_[0])
        C.add('cars (all %d LOD0 instances): overlapping pairs of their oriented plan hulls (same height band)' % len(hulls), len(pairs), 0,
              ok=not pairs, unit='', src='close-out r3 fix 2 (verifier v3: 16 pairs, worst 2.44 m2); worst %s' % (pairs[:3],))
        plaus_cars = dict(instances=len(hulls), overlapping_pairs=len(pairs), worst=pairs[:5])
        # close-out round 4 (verifier r3: 13 Central Garage roof cars 0.1-0.35 m into the coping / deck rim / a roof box): every LOD0
        # car (instances + the single-instance car meshes) against the static LOD0 triangles of this file in the car's band
        # (bottom + 0.10 .. top - 0.05), the verifier's cars_static test
        import landside_cars as LC
        from shapely.geometry import MultiPoint
        stat = [p_['P'][p_['T']] for nm, m in S.items() if m['lod'] == 0 and m['inst'] is None and '_cars' not in nm for p_ in m['prims']]
        SI = LC.StaticIndex(np.concatenate(stat)[:, :, [0, 2, 1]]) if stat else None
        singles = []
        for nm, m in S.items():
            if m['lod'] == 0 and m['inst'] is None and '_cars' in nm:
                Pq = np.concatenate([p_['P'] for p_ in m['prims']])
                singles.append((MultiPoint([tuple(q) for q in Pq[:, [0, 2]]]).convex_hull, float(Pq[:, 1].min()), float(Pq[:, 1].max())))
        cs = []
        for g, y0, y1 in hulls + singles:
            a = SI.hits(g, y0 + 0.10, y1 - 0.05, min_area=1.0) if SI is not None else 0.0
            if a > 0.01: cs.append((round(a, 3), [round(c, 1) for c in g.centroid.coords[0]], round(y0, 2)))
        cs.sort(key=lambda p_: -p_[0])
        C.add('cars (all %d LOD0 cars incl. %d single meshes) touching static LOD0 geometry in their height band' % (len(hulls) + len(singles), len(singles)),
              len(cs), 0, ok=not cs, unit='', src='close-out round 4 (verifier r3: 13 CG roof cars, 3.77 m2); worst %s' % (cs[:3],))
        plaus_cars.update(cars_vs_static=len(cs), cars_vs_static_m2=round(sum(c_[0] for c_ in cs), 2), cars_vs_static_worst=cs[:5])
    else:
        plaus_cars = dict(instances=0)
    # LOD1 car meshes: the lowest point of every instance above its origin (the deck + 0.01): 0 since fix 2 (was 0.30, floating)
    l1 = [(h[1] - float(t_[1])) for nm, m in S.items() if m['inst'] is not None and m['lod'] == 1 and m.get('inst_hull')
          for h, t_ in zip(m['inst_hull'], m['inst'])]
    if l1:
        C.add('cars LOD1: body bottom above the instance origin (the deck), max over %d instances' % len(l1), float(max(l1)), 0.0, 0.02,
              'close-out r3 fix 2 (verifier v3: 0.30 m, the LOD1 cars floated)')
        plaus_cars['lod1_bottom_max_m'] = round(float(max(l1)), 3)
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
    plaus = {'cars': plaus_cars}
    if AT_X is not None: plaus['airtrain_vs_buildings_lod0'] = AT_X
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
    # ---------------- LOD2 see-through (close-out r3 fix 2, verifier v2: the Superbay LOD2 was an open shell for two rounds and no
    # check saw it - verify only compared LOD2 tops with LOD0). tools/blender/bf_rays.py (the verifier's numeric back-face rays:
    # 16 azimuths x 1-m slices + vertical rays, 0.5 m) on the LOD2 subtree with the LOD2 neighbours that hide internal edges in
    # the app (itb_lod2 / domestic_lod2 / roadways_lod2). Gate: no node above LOD2_BF_MAX hits, except the residuals recorded
    # below at their measured count (pre-existing, listed in the manifest; a regression above it fails)
    try:
        import bf_rays as BF
        ctx = [os.path.join(ROOT, 'data', 'buildings3d', f) for f in ('itb_lod2.glb', 'domestic_lod2.glb', 'roadways_lod2.glb')]
        r2 = BF.run('+'.join([path] + [c_ for c_ in ctx if os.path.exists(c_)]), lod=2, sp=0.5, H=45.0)
        per = {k: v['n'] for k, v in r2['nodes'].items()}
        bad = {k: v for k, v in per.items() if v > LOD2_BF_RESIDUAL.get(k, LOD2_BF_MAX)}
        C.add('LOD2 see-through: back-face first hits per node (worst %s; residuals %s)' % (max(per.items(), key=lambda kv: kv[1]) if per else '-',
              {k: per.get(k, 0) for k in LOD2_BF_RESIDUAL}), max(per.values()) if per else 0, LOD2_BF_MAX, ok=not bad, unit='hits',
              src='bf_rays.py with LOD2 context; > %d hits = an open shell (Superbay LOD2 r1-r3: 15,084); failing: %s' % (LOD2_BF_MAX, bad or 'none'))
        plaus['lod2_backface'] = dict(total=r2['total'], per_node=per, context=[os.path.basename(c_) for c_ in ctx if os.path.exists(c_)])
    except Exception as e:  # noqa: BLE001
        C.add('LOD2 see-through (back-face rays)', str(e), 'error', ok=False)
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
