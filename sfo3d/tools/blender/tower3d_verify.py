"""Verification and packaging helpers of the tower asset (no bpy): GLB read / rewrite, post-processing of the Blender
export, measurement of the exported geometry against the 2-D sheets (tools/buildings/draw_tower.py), plausibility checks
against the surveyed stands / bridges / taxiway centrelines, and the manifest entry.

    python3 tools/blender/tower3d_verify.py [data/buildings3d/tower.glb [1|2]]     # re-measure an exported GLB (tower.glb = F2)

Tolerance (owner, 2026-11-04): the model matches the drawings within 0.5 m or 2 % (the larger), per dimension.
"""
import io
import json
import math
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tower_geom as G  # noqa: E402

DT = G.DT
ROOT = G.ROOT
GROUND_Y = 3.0
# Default height family (3-D review round 1, 2026-11-05): F2 (D 14.5, rim 64.0) lies within the observations (cab-roof D 14.3
# +-1.0 measured, 14.75 +-0.5 EXIF; rim 63.3-64.1 m for D 14.3 and 65 +-2 m for D 14.75 in the h_roof_top test); F1 (D 15.2,
# rim 67.36) needs D >= 15.1 and rests on the CTBUH classification of 221 ft (a database class, not a survey): it is kept as
# the published-height hypothesis. The owner decides (family_decided false).
DEFAULT_FAM = 2
FILE = {2: 'tower.glb', 1: 'tower_f1.glb'}
LOD2_FILE = 'tower_lod2.glb'                 # LOD2 of the default family (phones / far)
FAM_ROLE = {2: 'default: anchored on the observed cab-roof diameter', 1: 'published-height hypothesis (221 ft = rim; CTBUH class)'}


# ------------------------------------------------------------------------------------------------ GLB io
def read_glb(path):
    data = open(path, 'rb').read()
    magic, ver, length = struct.unpack_from('<4sII', data, 0)
    assert magic == b'glTF', path
    off = 12; js = None; bin_ = b''
    while off < len(data):
        clen, ctype = struct.unpack_from('<I4s', data, off)
        chunk = data[off + 8: off + 8 + clen]
        if ctype == b'JSON': js = json.loads(chunk)
        elif ctype == b'BIN\x00': bin_ = chunk
        off += 8 + clen
    return js, bytearray(bin_)


def write_glb(path, js, bin_):
    j = json.dumps(js, separators=(',', ':')).encode()
    j += b' ' * ((4 - len(j) % 4) % 4)
    b = bytes(bin_) + b'\x00' * ((4 - len(bin_) % 4) % 4)
    js['buffers'][0]['byteLength'] = len(bin_)
    j = json.dumps(js, separators=(',', ':')).encode(); j += b' ' * ((4 - len(j) % 4) % 4)
    total = 12 + 8 + len(j) + 8 + len(b)
    with open(path, 'wb') as f:
        f.write(struct.pack('<4sII', b'glTF', 2, total))
        f.write(struct.pack('<I4s', len(j), b'JSON')); f.write(j)
        f.write(struct.pack('<I4s', len(b), b'BIN\x00')); f.write(b)


def repack(js, bin_, replace):
    """rebuild the binary chunk; replace = {bufferView index: new bytes}."""
    out = bytearray(); views = js['bufferViews']
    for i, v in enumerate(views):
        src = replace.get(i)
        if src is None:
            o = v.get('byteOffset', 0); src = bytes(bin_[o:o + v['byteLength']])
        while len(out) % 4: out.append(0)
        v['byteOffset'] = len(out); v['byteLength'] = len(src)
        out += src
    return out


CT = {5126: ('f', 4), 5125: ('I', 4), 5123: ('H', 2), 5121: ('B', 1), 5122: ('h', 2), 5120: ('b', 1)}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


def accessor(js, bin_, i):
    a = js['accessors'][i]; v = js['bufferViews'][a['bufferView']]
    fmt, sz = CT[a['componentType']]; n = NC[a['type']]
    off = v.get('byteOffset', 0) + a.get('byteOffset', 0)
    stride = v.get('byteStride', sz * n)
    arr = np.frombuffer(bytes(bin_[off: off + stride * (a['count'] - 1) + sz * n]), dtype=np.dtype(fmt).newbyteorder('<'))
    if stride == sz * n:
        return arr[: a['count'] * n].reshape(a['count'], n).astype(np.float64 if fmt == 'f' else np.int64)
    out = np.lib.stride_tricks.as_strided(arr, (a['count'], n), (stride, sz))
    return np.array(out, np.float64 if fmt == 'f' else np.int64)


def quat_mat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def node_mats(js):
    """world 4x4 matrix of every node."""
    M = {}
    parent = {}
    for i, n in enumerate(js['nodes']):
        for c in n.get('children', []): parent[c] = i

    def local(n):
        if 'matrix' in n: return np.array(n['matrix']).reshape(4, 4).T
        m = np.eye(4)
        R = quat_mat(n.get('rotation', [0, 0, 0, 1])) * np.array(n.get('scale', [1, 1, 1]))
        m[:3, :3] = R; m[:3, 3] = n.get('translation', [0, 0, 0])
        return m

    def world(i):
        if i in M: return M[i]
        m = local(js['nodes'][i])
        if i in parent: m = world(parent[i]) @ m
        M[i] = m
        return m
    for i in range(len(js['nodes'])): world(i)
    return M, parent


def load_meshes(path):
    """{lod: {node name: [(material name, Nx3 local positions (rel. axis, ground), tris Mx3)]}} in the app frame."""
    js, bin_ = read_glb(path)
    M, parent = node_mats(js)
    org = np.array([G.AXIS[0], GROUND_Y, G.AXIS[1]])
    out = {}
    names = {i: n.get('name', '') for i, n in enumerate(js['nodes'])}
    for i, n in enumerate(js['nodes']):
        if 'mesh' not in n: continue
        lod = None; p = i
        while p in parent:
            p = parent[p]
            if names[p].startswith('LOD'): lod = int(names[p][3:])
        nm = n['name'].split('_', 1)[1] if '_' in n['name'] else n['name']
        for prim in js['meshes'][n['mesh']]['primitives']:
            P = accessor(js, bin_, prim['attributes']['POSITION'])
            P = (M[i][:3, :3] @ P.T).T + M[i][:3, 3] - org
            idx = accessor(js, bin_, prim['indices']).reshape(-1, 3) if 'indices' in prim else np.arange(len(P)).reshape(-1, 3)
            mat = js['materials'][prim['material']]['name'] if 'material' in prim else ''
            out.setdefault(lod, {}).setdefault(nm, []).append((mat.split('.')[0], P, idx))
    return out, js


# ------------------------------------------------------------------------------------------------ anchors, post-process
def anchors(TW):
    c = TW.cab
    return dict(
        axis_world_xz=[float(G.AXIS[0]), float(G.AXIS[1])], cab_centre_world_xz=[float(G.CAB_W[0]), float(G.CAB_W[1])],
        cab_floor_h=round(TW.floor_h, 3), cab_eye_h=round(TW.floor_h + 1.6, 3), glass_sill_h=round(c['glass_bottom'][1], 3),
        glass_head_h=round(c['glass_top'][1], 3), glass_sill_r=round(c['glass_bottom'][0], 3), glass_head_r=round(c['glass_top'][0], 3),
        roof_rim_h=round(TW.rim_h, 3), flare_widest_h=round(TW.h_top, 3), family=f'F{TW.fam}',
        ibf_roof_h=round(TW.ibf, 3), ibf_parapet_h=round(TW.par, 3),
        mast_tip_max_h=round(TW.rim_h + max(h for b, h in DT.MASTS) * TW.k, 3),
        red_light=dict(bearing_from_cab=G.RED_LIGHT_BRG, h=round(TW.rim_h + 0.3, 3)),
        note='heights in m above grade (GROUND_Y); app tower camera: put the eye at cab_eye_h inside the glass ring')


def postprocess(glb, fam, TW, stats, ao_info, mats=None):
    """grey-scale AO PNGs, glass alpha mode, asset extras; returns file info."""
    from PIL import Image
    js, bin_ = read_glb(glb)
    rep = {}
    imgs = []
    for im in js.get('images', []):
        bv = im.get('bufferView')
        if bv is None: continue
        v = js['bufferViews'][bv]; o = v.get('byteOffset', 0)
        raw = bytes(bin_[o:o + v['byteLength']])
        pil = Image.open(io.BytesIO(raw))
        if im.get('name', '').startswith('tower_ao'):
            pil = pil.convert('L')
        else:
            pil = pil.convert('RGB')
        b = io.BytesIO(); pil.save(b, 'PNG', optimize=True); nb = b.getvalue()
        rep[bv] = nb; im['mimeType'] = 'image/png'
        imgs.append(dict(name=im.get('name'), size=list(pil.size), mode=pil.mode, bytes=len(nb)))
    for m in js.get('materials', []):
        key = m['name'].split('.')[0]
        spec = (mats or {}).get(key)
        m['doubleSided'] = False                 # every surface is wound outwards (audited); only the glass is seen from both sides
        if key == 'cab_glass':
            m['alphaMode'] = 'BLEND'; m['doubleSided'] = True
            al = float(spec.get('alpha', 0.5)) if spec else 0.5
            m.setdefault('pbrMetallicRoughness', {})['baseColorFactor'] = list(m.get('pbrMetallicRoughness', {}).get(
                'baseColorFactor', [0.04, 0.06, 0.07, al]))[:3] + [al]
        ex = m.setdefault('extras', {})
        if spec:
            ex['src'] = spec['src']
            if spec.get('led'): ex['led'] = True
            if spec.get('led_color'): ex['led_color'] = [round(float(c), 4) for c in spec['led_color']]
            if spec.get('led_color_obs'): ex['led_color_obs'] = spec['led_color_obs']
            if spec.get('light'): ex['obstruction_light'] = True
            if spec.get('ambient_only'): ex['ambient_only'] = True
        if 'occlusionTexture' in m:
            assert m['occlusionTexture'].get('texCoord', 0) == 1, (m['name'], m['occlusionTexture'])
    # tangents only where a normal map is used (the exporter writes them for every primitive), then drop what is unused
    n_tan = 0
    for mesh in js['meshes']:
        for prim in mesh['primitives']:
            mat = js['materials'][prim['material']] if 'material' in prim else {}
            if 'normalTexture' not in mat and 'TANGENT' in prim['attributes']:
                del prim['attributes']['TANGENT']; n_tan += 1
    # texture coordinate sets no texture of the primitive's material reads (TEXCOORD_1 first; TEXCOORD_0 only when alone)
    n_uv = 0
    for mesh in js['meshes']:
        for prim in mesh['primitives']:
            mat = js['materials'][prim['material']] if 'material' in prim else {}
            texs = [mat.get(k) for k in ('normalTexture', 'occlusionTexture', 'emissiveTexture')]
            texs += [mat.get('pbrMetallicRoughness', {}).get(k) for k in ('baseColorTexture', 'metallicRoughnessTexture')]
            sets = {t.get('texCoord', 0) for t in texs if t}
            if 1 not in sets and 'TEXCOORD_1' in prim['attributes']:
                del prim['attributes']['TEXCOORD_1']; n_uv += 1
            if not sets and 'TEXCOORD_0' in prim['attributes'] and 'TEXCOORD_1' not in prim['attributes']:
                del prim['attributes']['TEXCOORD_0']; n_uv += 1
    used = set()
    for mesh in js['meshes']:
        for prim in mesh['primitives']:
            used |= set(prim['attributes'].values())
            if 'indices' in prim: used.add(prim['indices'])
    amap = {}; acc = []
    for i, a in enumerate(js['accessors']):
        if i in used: amap[i] = len(acc); acc.append(a)
    for mesh in js['meshes']:
        for prim in mesh['primitives']:
            prim['attributes'] = {k: amap[v] for k, v in prim['attributes'].items()}
            if 'indices' in prim: prim['indices'] = amap[prim['indices']]
    js['accessors'] = acc
    used_bv = {a['bufferView'] for a in acc if 'bufferView' in a} | {im['bufferView'] for im in js.get('images', []) if 'bufferView' in im}
    bmap = {}; views = []
    for i, v in enumerate(js['bufferViews']):
        if i in used_bv: bmap[i] = len(views); views.append(v)
    for a in acc:
        if 'bufferView' in a: a['bufferView'] = bmap[a['bufferView']]
    for im in js.get('images', []):
        if 'bufferView' in im: im['bufferView'] = bmap[im['bufferView']]
    js['bufferViews'] = views
    rep = {bmap[k]: v for k, v in rep.items()}
    bin_ = repack(js, bin_, rep)
    js['asset'].setdefault('extras', {}).update(dict(
        asset='SFO ATCT (2016) + base building', family=f'F{fam}', family_decided=False, built_by='tools/blender/build_tower.py',
        reference='docs/drawings/buildings/BT-01..03 (tools/buildings/draw_tower.py, spec_tower.json)',
        manifest='data/buildings3d/manifest.json#tower', licence_note='our own geometry and procedural textures; no imagery'))
    write_glb(glb, js, bin_)
    return dict(bytes=os.path.getsize(glb), images=imgs, tangents_dropped=n_tan, uv_sets_dropped=n_uv)


# ------------------------------------------------------------------------------------------------ measurements
def _pts(meshes, lod, nodes, mats=None):
    P = []
    for nm in nodes:
        for mat, p, idx in meshes[lod].get(nm, []):
            if mats is None or mat in mats: P.append(p)
    return np.concatenate(P) if P else np.zeros((0, 3))


def _brg(P, c=(0.0, 0.0)):
    """bearing (deg) of points P (app frame local: x east, z south) seen from c (local x, z)."""
    return np.degrees(np.arctan2(P[:, 0] - c[0], -(P[:, 2] - c[1]))) % 360


def _circle_fit(xy):
    A = np.c_[2 * xy[:, 0], 2 * xy[:, 1], np.ones(len(xy))]
    b = (xy ** 2).sum(1)
    cx, cy, k = np.linalg.lstsq(A, b, rcond=None)[0]
    return np.array([cx, cy]), math.sqrt(k + cx * cx + cy * cy)


def chk(name, model, drawing, tag, tol=None, unit='m', note=''):
    tol_ = tol if tol is not None else max(0.5, 0.02 * abs(drawing))
    dev = model - drawing
    return dict(item=name, model=round(float(model), 3), drawing=round(float(drawing), 3), dev=round(float(dev), 3),
                tol=round(tol_, 3), ok=bool(abs(dev) <= tol_), tag=tag, unit=unit, note=note)


def verify(glb, fam):
    meshes, js = load_meshes(glb)
    TW = G.Tower(fam); f = TW.f
    res = []
    L0 = 0
    shaft = _pts(meshes, L0, ['shaft'], ['clad'])
    cabC = np.array([G.CAB[0], -G.CAB[1]])          # local ENU (east, north) -> app frame local (x, z)
    # 1. round-body radius at the drawn stations (airside sector 40-220 deg, outside the slots)
    for r_d, h_d in TW.body_pts:
        sel = shaft[(np.abs(shaft[:, 1] - h_d) < 0.02)]
        b = _brg(sel); sel = sel[(b > 40) & (b < 220)]
        if len(sel) == 0: continue
        r = np.hypot(sel[:, 0], sel[:, 2]).max()
        res.append(chk(f'shaft radius at h {h_d:.2f}', r, r_d, 'inf', note='BT-02 shaft_outline (A380 ratios / 1.015 x D)'))
    # 2. silhouettes in the BT-02 views (whole tower LOD0), at the drawn stations
    allp = _pts(meshes, L0, ['shaft', 'landside', 'ribbon', 'flare_deck'])
    for view, right in (('A', G.RIGHT_A), ('B', G.RIGHT_B)):
        u = allp[:, 0] * right[0] + allp[:, 2] * right[1]
        for r_d, h_d in TW.body_pts[1::3] + [TW.body_pts[-1]]:
            m_ = np.abs(allp[:, 1] - h_d) < 0.02
            if not m_.any(): continue
            res.append(chk(f'view {view} silhouette left at h {h_d:.2f}', -u[m_].min(), r_d, 'inf', note='BT-02 outline'))
            res.append(chk(f'view {view} silhouette right at h {h_d:.2f}', u[m_].max(), r_d, 'inf', note='BT-02 outline'))
    # 3. cab
    cab = meshes[L0]['cab']; glass = _pts(meshes, L0, ['cab_glass'])
    cop = np.concatenate([p for m, p, i in cab if m == 'coping'])
    top = cop[np.abs(cop[:, 1] - cop[:, 1].max()) < 0.01]
    c2, _ = _circle_fit(top[:, [0, 2]])
    r2 = float(np.hypot(top[:, 0] - c2[0], top[:, 2] - c2[1]).max())
    res.append(chk('cab roof rim height', cop[:, 1].max(), TW.rim_h, 'inf'))
    res.append(chk('cab roof diameter D', 2 * r2, f['D'], 'inf', note='family D (measured 14.3 +-1.0, EXIF 14.75 +-0.5 obs)'))
    res.append(chk('cab centre x (world)', c2[0] + G.AXIS[0], G.CAB_W[0], 'inf'))
    res.append(chk('cab centre z (world)', c2[1] + G.AXIS[1], G.CAB_W[1], 'inf'))
    gr = np.hypot(glass[:, 0] - cabC[0], glass[:, 2] - cabC[1])
    res.append(chk('glass sill height', glass[:, 1].min(), TW.cab['glass_bottom'][1], 'inf'))
    res.append(chk('glass head height', glass[:, 1].max(), TW.cab['glass_top'][1], 'inf'))
    res.append(chk('glass sill diameter (pane corners)', 2 * gr[glass[:, 1] < glass[:, 1].min() + 0.01].max(), 2 * TW.cab['glass_bottom'][0], 'inf'))
    res.append(chk('glass head diameter (pane corners)', 2 * gr[glass[:, 1] > glass[:, 1].max() - 0.01].max(), 2 * TW.cab['glass_top'][0], 'inf'))
    pl = np.concatenate([p for m, p, i in cab if m == 'plinth'])
    res.append(chk('plinth diameter', 2 * np.hypot(pl[:, 0] - cabC[0], pl[:, 2] - cabC[1]).max(), 2 * TW.plinth_r, 'obs'))
    res.append(chk('plinth top (= glass sill)', pl[:, 1].max(), TW.sill_h, 'inf'))
    fl = np.concatenate([p for m, p, i in meshes[L0].get('cab_interior', cab) if m == 'cab_floor'])
    res.append(chk('cab floor', fl[:, 1].min(), TW.floor_h, 'inf'))
    # 4. flare widest, shoulder top, NE tip
    sh = _pts(meshes, L0, ['shaft'])
    rr_ = np.hypot(sh[:, 0], sh[:, 2])
    res.append(chk('flare widest radius', rr_.max(), TW.r_top, 'inf', note='1.58 D'))
    res.append(chk('flare widest height', sh[np.argmax(rr_), 1], TW.h_top, 'inf'))
    deck = _pts(meshes, L0, ['flare_deck'], ['clad_deck'])
    dr = np.hypot(deck[:, 0] - cabC[0], deck[:, 2] - cabC[1])
    inner = deck[dr < TW.plinth_r + 0.05]
    res.append(chk('flare deck at the plinth foot', inner[:, 1].min() if len(inner) else np.nan, TW.deck_h, 'inf'))
    # NE prow: the outermost deck vertex in the NE blade sector (bearing 315-360), and the highest deck vertex within 0.6 m
    # (plan) of it: the blade top, flush with the flare corner (the shoulder starts rising from there)
    bd = _brg(deck); ne = deck[(bd > 315) & (bd < 360)]
    tipv = ne[np.argmax(np.hypot(ne[:, 0], ne[:, 2]))]
    near = ne[np.hypot(ne[:, 0] - tipv[0], ne[:, 2] - tipv[2]) < 0.6]
    res.append(chk('NE blade top (prow) height', near[:, 1].max(), TW.tip_h, 'obs',
                   note='photos t3 / t4 / t5: flush with the flare corner (draw_tower.NE_TIP); max within 0.6 m of the prow tip'))
    res.append(chk('NE prow tip height', tipv[1], TW.h_top, 'obs', note='the prow corner lies on the flare corner'))
    # 5. ribbon
    rib = _pts(meshes, L0, ['ribbon'], ['ribbon_glass'])
    e = DT.hdg_vec(DT.RIB_BRG + 90.0)                      # world (x, z) unit vector along the ribbon (towards 40 deg)
    for lab, hh, wd in (('foot', rib[:, 1].min(), G.RIB_W0), ('head', rib[:, 1].max(), G.RIB_W1)):
        s = rib[np.abs(rib[:, 1] - hh) < 0.02]
        y = s[:, 0] * e[0] + s[:, 2] * e[1]
        res.append(chk(f'ribbon width at its {lab}', y.max() - y.min(), wd, 'obs'))
    res.append(chk('ribbon foot height (= IBF roof)', rib[:, 1].min(), TW.hb, 'inf'))
    res.append(chk('ribbon height (147 ft)', rib[:, 1].max() - rib[:, 1].min(), min(G.RIB_H, TW.ht - TW.hb), 'pub',
                   note='F2: capped at the flare corner' if TW.rib_capped else ''))
    s = rib[np.abs(rib[:, 1] - rib[:, 1].max()) < 0.02]
    mid = s.mean(0)
    u_mid = mid[0] * G.RIGHT_B[0] + mid[2] * G.RIGHT_B[1]
    res.append(chk('ribbon centre offset at its head, view B (u)', u_mid, DT.rib_shift(TW.ht, f, G.RIGHT_B), 'inf', note='BT-02 B -2.3 m'))
    # 6. SW wing tip (plan) at the flare level
    land = _pts(meshes, L0, ['landside'], ['louvre'])
    bl = _brg(land); land = land[(bl > 180) & (bl < DT.RIB_BRG)]      # the SW wing (the louvred NE channel wall is NE of the ribbon)
    tl = land[land[:, 1] > TW.h_top - 0.02]
    rl = np.hypot(tl[:, 0], tl[:, 2]); k = int(np.argmax(rl))
    res.append(chk('SW wing tip radius (plan)', rl[k], DT.WING_TIP[1] * f['D'] / 15.2, 'inf', note='BT-01 254 deg / 14.0 m'))
    res.append(chk('SW wing tip bearing (plan)', _brg(tl[k:k + 1])[0], DT.WING_TIP[0], 'inf', tol=2.0, unit='deg'))
    ub = (land[:, 0] * G.RIGHT_B[0] + land[:, 2] * G.RIGHT_B[1])
    rl_all = np.hypot(land[:, 0], land[:, 2])
    for hh in (TW.hb + 5, (TW.hb + TW.h_w1) / 2, TW.h_w1):
        hsel = land[np.argmin(np.abs(land[:, 1] - hh)), 1]
        m2 = np.abs(land[:, 1] - hsel) < 0.01
        tw = min(max((hsel - TW.hb) / (TW.h_w1 - TW.hb), 0), 1)
        kk = np.argmax(np.where(m2, rl_all, -1))          # the wing tip at this height (largest radius)
        res.append(chk(f'SW wing tip in view B at h {hsel:.1f} (u)', ub[kk], TW.x0 + (TW.wt - TW.x0) * tw ** 1.8, 'inf',
                       note='BT-02 B draw_blades outer line = projection of the wing tip; the rounded edge beyond the tip '
                       f'reaches u {ub[m2].max():.2f}, inside the round-body silhouette {TW.R(hsel):.2f}'))
    # 7. slots: centre bearings at mid-band (drawn: bm) and the long slot ends
    sl = _pts(meshes, L0, ['shaft'], ['slot_pocket', 'slot_reveal'])
    rs = np.hypot(sl[:, 0], sl[:, 2])
    a, b_ = TW.slot_band; hm_ = sl[np.argmin(np.abs(sl[:, 1] - (a + b_) / 2)), 1]
    mm = (np.abs(sl[:, 1] - hm_) < 0.02)
    bb = _brg(sl[mm])
    for bm in TW.upper:
        d = (bb - (bm + 0.0 + (DT.SLOT_SWEEP / 2 - DT.SLOT_SWEEP * (hm_ - a) / (b_ - a))) + 180) % 360 - 180
        near = d[np.abs(d) < 8]
        if len(near):
            res.append(chk(f'upper slot {bm:.1f}: centre bearing at h {hm_:.1f}', float(np.mean([near.min(), near.max()])), 0.0, 'inf',
                           tol=1.0, unit='deg', note='offset from the drawn helix'))
            rmid = TW.R(hm_)
            res.append(chk(f'upper slot {bm:.1f}: width', math.radians(near.max() - near.min()) * rmid, DT.SLOT_W, 'obs', tol=0.3,
                           note='clipped at the NE blade root' if bm > 330 else ''))
    a2, b2 = TW.long_band
    for lab, hh, bd in (('foot', a2, DT.LONG_SLOT[0]), ('head', b2, DT.LONG_SLOT[1])):
        m_ = np.abs(sl[:, 1] - hh) < 0.02
        bl = _brg(sl[m_]); bl = bl[(bl > 60) & (bl < 170)]
        res.append(chk(f'long slot {lab} bearing', float(np.mean([bl.min(), bl.max()])), bd, 'inf', tol=1.0, unit='deg'))
    # 8. masts
    ms = meshes[L0].get('roof_masts', [])
    mp = np.concatenate([p for m, p, i in ms if m == 'mast']) if ms else np.zeros((0, 3))
    if len(mp):
        dev_h, dev_b = [], []
        for b0, hm in DT.MASTS:
            d = DT.MAST_K * TW.cab['roof_rim'][0]
            px = cabC + d * np.array([math.sin(math.radians(b0)), -math.cos(math.radians(b0))])
            near = mp[np.hypot(mp[:, 0] - px[0], mp[:, 2] - px[1]) < 0.2]
            dev_h.append(near[:, 1].max() - (TW.rim_h + hm * TW.k))
        res.append(chk('mast tips: max |height dev| (15 whips)', max(abs(x) for x in dev_h), 0.0, 'inf', tol=0.3))
        res.append(chk('highest mast tip', mp[:, 1].max(), TW.rim_h + max(h for b0, h in DT.MASTS) * TW.k, 'inf'))
    # 9. base building
    ibf = meshes[L0]['ibf']
    allb = np.concatenate([p for m, p, i in ibf])
    res.append(chk('IBF parapet top', allb[:, 1].max(), TW.par, 'inf', note='rim - 3.46 D'))
    rd = np.concatenate([p for m, p, i in ibf if m == 'roof_deck'])
    res.append(chk('IBF roof', np.median(rd[:, 1]), TW.ibf, 'inf'))
    gd = np.concatenate([p for m, p, i in ibf if m == 'garden'])
    res.append(chk('roof garden level', gd[:, 1].mean(), TW.ibf - G.GARDEN_DROP, 'inf'))
    res.append(chk('roof garden area (m2)', _area(gd), 185.8, 'pub', tol=0.25 * 185.8, unit='m2',
                   note='NAIP outline (obs) vs 2,000 sq ft (pub); +-25 %'))
    ring = np.asarray(DT.D.sfom('Air Traffic Control Tower')[0][0], float)
    foot = allb[allb[:, 1] < 0.01]
    devs = []
    for p in ring:
        q = p - G.AXIS
        devs.append(np.hypot(foot[:, 0] - q[0], foot[:, 2] - q[1]).min())
    res.append(chk('IBF footprint corners vs SFO Museum ring (max)', max(devs), 0.0, 'obs', tol=0.05))
    gl = np.concatenate([p for m, p, i in ibf if m == 'ibf_glass_dark'])
    res.append(chk('airside glazing band top', gl[:, 1].max(), TW.par - DT.IBF_AIR_BAND[0], 'obs', note='photo t2'))
    res.append(chk('airside glazing band height', gl[:, 1].max() - gl[:, 1].min(), DT.IBF_AIR_BAND[1], 'obs'))
    ua = gl[:, 0] * G.RIGHT_A[0] + gl[:, 2] * G.RIGHT_A[1]
    res.append(chk('airside glazing band SW end, view A (u)', ua.min(), DT.IBF_AIR_BAND[2], 'obs'))
    cw = np.concatenate([p for m, p, i in ibf if m == 'ibf_curtain'])
    ub2 = cw[:, 0] * G.RIGHT_B[0] + cw[:, 2] * G.RIGHT_B[1]
    s0, s1 = sorted((DT.ibf_face_u(DT.IBF_CW[0], DT.hdg_vec(207.7)), DT.ibf_face_u(DT.IBF_CW[1], DT.hdg_vec(207.7))))
    res.append(chk('landside curtain wall, view B u min', ub2.min(), s0, 'obs'))
    res.append(chk('landside curtain wall, view B u max', ub2.max(), s1, 'obs'))
    res.append(chk('landside curtain wall height seen', cw[:, 1].max() - cw[:, 1].min(), DT.IBF_CW[2], 'obs'))
    # 10. overall
    allL0 = np.concatenate([p for nm, lst in meshes[L0].items() for m, p, i in lst])
    res.append(chk('highest point (mast tip)', allL0[:, 1].max(), TW.rim_h + max(h for b0, h in DT.MASTS) * TW.k, 'inf'))
    # LOD1 / LOD2: silhouettes against the drawing (coarser tessellation)
    for lod in (1, 2):
        if lod not in meshes: continue
        P = _pts(meshes, lod, ['shaft'])
        worst = 0.0
        for r_d, h_d in TW.body_pts:
            m_ = np.abs(P[:, 1] - h_d) < 0.02
            if not m_.any(): continue
            b = _brg(P[m_]); s = P[m_][(b > 40) & (b < 220)]
            if len(s): worst = max(worst, abs(np.hypot(s[:, 0], s[:, 2]).max() - r_d))
        res.append(chk(f'LOD{lod}: worst shaft radius dev at the drawn stations', worst, 0.0, 'inf', tol=0.5))
        Pc = _pts(meshes, lod, ['cab'])
        res.append(chk(f'LOD{lod}: rim height', Pc[:, 1].max(), TW.rim_h, 'inf'))
    plaus = plausibility(meshes)
    tris = {lod: int(sum(len(i) for nm, lst in m.items() for _, _, i in lst)) for lod, m in meshes.items()}
    n_bad = sum(1 for r in res if not r['ok'])
    return dict(family=f'F{fam}', glb=os.path.relpath(glb, ROOT), checks=res, n_checks=len(res), n_fail=n_bad,
                worst=sorted(res, key=lambda r: -abs(r['dev']) / max(r['tol'], 1e-9))[:5], tris=tris, plausibility=plaus,
                summary=f'{len(res) - n_bad}/{len(res)} checks within tolerance; tris {tris}; plausibility {plaus["verdict"]}')


def _area(P):
    """plan area of the convex hull of points P (app frame local)."""
    from scipy.spatial import ConvexHull
    return float(ConvexHull(P[:, [0, 2]]).volume)


def plausibility(meshes):
    """clearances of the asset's plan footprint (all LOD0 geometry, incl. the flare overhang) to the surveyed stands,
    jet bridges, taxiway centrelines and the other SFO Museum buildings."""
    from shapely.geometry import MultiPoint, Point, LineString, Polygon
    P = np.concatenate([p for nm, lst in meshes[0].items() for m, p, i in lst])
    W = P[:, [0, 2]] + G.AXIS
    hull = MultiPoint([tuple(x) for x in W]).convex_hull
    low = P[P[:, 1] < 20.0][:, [0, 2]] + G.AXIS
    hull_low = MultiPoint([tuple(x) for x in low]).convex_hull
    st = json.load(open(os.path.join(ROOT, 'data', 'sfo_stands.json')))
    d_nose = min(hull.distance(Point(s['nose'])) for s in st['stands'])
    d_bridge = min(hull.distance(LineString(b['walk'])) for s in st['stands'] for b in s.get('bridges', []) if len(b.get('walk', [])) > 1)
    # aircraft envelopes: nose-in rectangles (length back from the nose x max span of the stand's largest class; published
    # manufacturer dimensions: E175, 737-800 / A320, A321, 767-300ER (winglets), 787-10, 777-300ER, 747-8)
    CLS = {'B': (31.7, 28.7), 'C': (39.5, 35.9), 'CL': (44.5, 35.9), 'D': (54.9, 50.9), 'E': (68.3, 60.3), 'EL': (73.9, 64.8),
           'F': (76.3, 68.4)}
    d_ac = 1e9; who = None
    for s in st['stands']:
        Lc, Sc = CLS.get(s.get('cls'), (76.3, 68.4))
        h = math.radians(s['hdg']); fwd = np.array([math.sin(h), -math.cos(h)]); side = np.array([-fwd[1], fwd[0]])
        n0 = np.array(s['nose'])
        rect = Polygon([tuple(n0 + side * Sc / 2), tuple(n0 - side * Sc / 2), tuple(n0 - fwd * Lc - side * Sc / 2),
                        tuple(n0 - fwd * Lc + side * Sc / 2)])
        d = rect.distance(hull_low)
        if d < d_ac: d_ac, who = d, s['name']
    det = json.load(open(os.path.join(ROOT, 'data', 'sfo_details.json')))
    d_cl = min(hull.distance(LineString(c)) for c in det['centerlines'] if len(c) > 1)
    air = json.load(open(os.path.join(ROOT, 'data', 'sfo_airport.json')))
    overlaps = []
    for key in ('terminals', 'boardingAreas', 'structures'):
        for ft in air[key]:
            if ft['name'] == 'Air Traffic Control Tower': continue
            for poly in ft['polys']:
                pg = Polygon(poly[0]).buffer(0)
                inter = pg.intersection(hull_low).area
                if inter > 1.0: overlaps.append(dict(name=ft['name'], kind=key, overlap_m2=round(inter, 1)))
    # the app's own building parts (data/sfo_buildings.json) over the base-building footprint (integration)
    B = json.load(open(os.path.join(ROOT, 'data', 'sfo_buildings.json')))
    app_over = []
    for p in B['parts']:
        pg = Polygon(p['rings'][0], p['rings'][1:]).buffer(0)
        a = pg.intersection(hull_low).area
        if a > 1.0: app_over.append(dict(part=p['name'], kind=p['kind'], h=p['h'], overlap_m2=round(a, 1)))
    ok = d_ac > 5 and d_bridge > 10 and d_cl > 30
    return dict(nearest_aircraft_envelope_m=round(d_ac, 1), nearest_aircraft_stand=who, nearest_stand_nose_m=round(d_nose, 1),
                nearest_bridge_m=round(d_bridge, 1), nearest_taxi_centreline_m=round(d_cl, 1),
                sfo_museum_overlaps_below_20m=overlaps, app_parts_over_footprint=app_over, plan_hull_area_m2=round(hull.area, 1),
                verdict=('clear of aircraft envelopes, bridges and taxilanes' if ok else 'CHECK clearances') +
                ('; the app\'s T2 hall / BA-D walkway parts overlap the base-building footprint (integration: cut them)' if app_over else ''))


# ------------------------------------------------------------------------------------------------ render comparisons
def compare_images(renders, TW):
    """(1) the BT-02 outlines of the family drawn over the orthographic renders A / B (our own images, kept);
    (2) photo | render side by side for the photo-matched views (LOCAL ONLY: the photos are third-party, reference only)."""
    from PIL import Image, ImageDraw
    out = {}
    f = TW.f
    for nm, right in (('A', G.RIGHT_A), ('B', G.RIGHT_B)):
        r = renders.get(nm)
        if not r: continue
        im = Image.open(os.path.join(ROOT, r['path'])).convert('RGB'); Wd, Hd = im.size
        s = r['m_per_px']; uc, hc = r['centre_u'], r['centre_h']
        P = lambda u, h: ((u - uc) / s + Wd / 2, Hd / 2 - (h - hc) / s)
        dr = ImageDraw.Draw(im)
        sh = DT.shaft_outline(f)
        for sg in (-1, 1):
            dr.line([P(sg * rr, hh) for rr, hh in sh], fill=(220, 40, 40), width=1)
        uo = DT.cab_offset(right); c = DT.cab_outline(f)
        for sg in (-1, 1):
            dr.line([P(uo + sg * c[k][0], c[k][1]) for k in ('glass_bottom', 'glass_top', 'roof_rim')], fill=(220, 40, 40), width=1)
        dr.line([P(uo - c['roof_rim'][0], c['roof_rim'][1]), P(uo + c['roof_rim'][0], c['roof_rim'][1])], fill=(220, 40, 40))
        u0, u1 = DT.ibf_u_extent(right)
        dr.line([P(u0, 0), P(u0, TW.par), P(u1, TW.par), P(u1, 0)], fill=(220, 40, 40))
        if nm == 'B':
            for sg in (-1, 1):
                dr.line([P(DT.rib_shift(hh, f, right) + sg * (G.RIB_W0 + (G.RIB_W1 - G.RIB_W0) * (hh - TW.hb) / (TW.ht - TW.hb)) / 2, hh)
                         for hh in np.linspace(TW.hb, TW.ht, 20)], fill=(40, 90, 220), width=1)
            out_line = [P(TW.x0 + (TW.wt - TW.x0) * t ** 1.8, TW.hb + (TW.h_w1 - TW.hb) * t) for t in np.linspace(0, 1, 13)]
            dr.line(out_line, fill=(230, 140, 0), width=1)
        for hh in (TW.rim_h, TW.cab['glass_top'][1], TW.cab['glass_bottom'][1], TW.h_top, TW.ibf):
            x0_, y0_ = P(14.5, hh); dr.line([(x0_, y0_), (x0_ + 12, y0_)], fill=(220, 40, 40))
        p = os.path.join(os.environ.get('TOWER_OUT_DIR') or os.path.join(ROOT, 'out', 'buildings3d'), f'tower_overlay_{nm}.png')
        im.save(p); out[f'overlay_{nm}'] = os.path.relpath(p, ROOT)
    for nm in ('t2', 't3', 't4'):
        r = renders.get(nm)
        if not r or not os.path.exists(os.path.join(ROOT, r['photo'])): continue
        a = Image.open(os.path.join(ROOT, r['photo'])).convert('RGB'); b = Image.open(os.path.join(ROOT, r['path'])).convert('RGB')
        a = a.resize(b.size)
        c = Image.new('RGB', (a.width * 2 + 8, a.height), (255, 255, 255)); c.paste(a, (0, 0)); c.paste(b, (a.width + 8, 0))
        p = os.path.join(os.environ.get('TOWER_OUT_DIR') or os.path.join(ROOT, 'out', 'buildings3d'), f'tower_compare_{nm}.jpg')
        c.save(p, quality=88); out[f'compare_{nm}'] = os.path.relpath(p, ROOT) + ' (local only: contains a third-party photo)'
    return out


# ------------------------------------------------------------------------------------------------ manifest
def _night_glow(glb):
    """the app's night-glow inputs as exported (material extras): the LED ribbon colour and the obstruction light."""
    js, _ = read_glb(glb)
    out = dict(note='js/three/buildings3d.js glowKind / GLOW_DEF: the LED ribbon glows in its material colour extras.led_color '
                    '(linear RGB, x GLOW_DEF.led colour / level); the cab glass glows as kind "cab" (GLOW_DEF.cab, inf); '
                    'red_light is the steady red obstruction light (beacon kind)')
    for m in js.get('materials', []):
        ex = m.get('extras') or {}
        if ex.get('led_color'):
            out['led'] = dict(material=m['name'].split('.')[0], led_color_linear=ex['led_color'], obs=ex.get('led_color_obs'),
                              tag='obs photo t5 (Varnum 2018-04, dusk: the ribbon lit saturated blue) as the default; the array is '
                                  'programmable (pub: LED-backlit), so the colour on any other night is unknown: an inferred, '
                                  'configurable value (material extras.led_color; GLOW_DEF.led tints / scales it)')
    return out


def manifest_entry(results, ver, renders, args, rev, secs):
    D_ = DEFAULT_FAM; A_ = 3 - D_
    rD = results[D_]; TW = rD['tower']; f = TW.f
    rA = results.get(A_)
    vD = ver[D_]
    T = DT.T

    def dim(key, value, unit, tag, source, drawing='BT-02', note=''):
        return dict(key=key, value=round(value, 3) if isinstance(value, float) else value, unit=unit, tag=tag, source=source,
                    drawing=drawing, note=note)
    dims = [
        dim('h_roof_top (rim)', TW.rim_h, 'm', 'inf', f'F{D_} (default): rim on the h_roof_top consistency line for D {f["D"]}; '
            'h_top_published 221 ft [pub] = the 2015 mast station in F2',
            note='F1 (tower_f1.glb, published-height hypothesis): 67.36 m = 221 ft at the rim; family NOT decided'),
        dim('d_cab_roof', f['D'], 'm', 'inf', f'family F{D_} (measured 14.3 +-1.0 obs, EXIF 14.75 +-0.5 obs)', 'BT-01/02'),
        dim('d_cab_glass_top / bottom', [round(2 * TW.cab['glass_top'][0], 3), round(2 * TW.cab['glass_bottom'][0], 3)], 'm', 'inf',
            'spec 12.3 / 10.0 obs at D 14.3, scaled by D_f / 14.3'),
        dim('h_cab_glass_top / bottom', [round(TW.cab['glass_top'][1], 3), round(TW.cab['glass_bottom'][1], 3)], 'm', 'inf', 'rim - k D'),
        dim('h_cab_floor', TW.floor_h, 'm', 'inf', 'rim - k D (spec 61.0 at the spec anchor)', 'BT-03'),
        dim('plinth ring D / height', [round(2 * TW.plinth_r, 3), round(TW.sill_h - TW.deck_h, 3)], 'm', 'obs', 'photo t1 (590 of 830 px)'),
        dim('d_flare_max', 2 * TW.r_top, 'm', 'inf', 'A380 ratio 1.605 / 1.015 x D = 1.58 D (spec 22.6 +-1.5 obs at D 14.3)'),
        dim('h_flare_max', TW.h_top, 'm', 'inf', 'rim - k D'),
        dim('flare top shoulder', 'rounded, rising to the plinth foot', '', 'obs', 'photo t1 profile fractions (stations inf)', 'BT-02/03'),
        dim('d_shaft_waist', 2 * TW.R(DT.hf(T['h_narrowest']['value'], f)), 'm', 'inf', 'A380 ratio x D'),
        dim('d_shaft_at_ibf_roof', 2 * TW.R(TW.ibf), 'm', 'inf', 'Famartin base width ratio x D'),
        dim('h_ibf_roof / parapet', [round(TW.ibf, 3), round(TW.par, 3)], 'm', 'inf', 'rim - (3.46 D + 0.7) [photo span obs, ratio]'),
        dim('ibf_footprint', '44.95 x 27.20 m, long axis 27.7 deg', '', 'obs', 'SFO Museum atc ring (CDLA-Permissive-1.0)', 'BT-01'),
        dim('ribbon height / widths', [round(TW.ht - TW.hb, 3), G.RIB_W0, G.RIB_W1], 'm', 'pub / obs low', '147 ft [pub]; widths T2 AirTrain photo',
            note='F2: capped at the flare corner' if TW.rib_capped else ''),
        dim('ribbon facing bearing', DT.RIB_BRG, 'deg', 'inf', 'middle of the 300-320 photo range', 'BT-01/02 B'),
        dim('upper slots', f'{len(TW.upper)} slots, {DT.SLOT_W} m wide (horizontal), phase {DT.SLOT_PHASE} deg, sweep {DT.SLOT_SWEEP} deg, '
            f'band {TW.slot_band[0]:.2f}-{TW.slot_band[1]:.2f} m', '', 'obs width / phase (t1 + t2), count inf',
            'photos t1 + t2 re-read 2026-11-05 (round 3: 1.4 m / 124 deg from t1 alone)'),
        dim('long helical slot', f'bearing {DT.LONG_SLOT[0]} -> {DT.LONG_SLOT[1]}, {DT.LONG_W} m wide, {TW.long_band[0]:.2f}-'
            f'{TW.long_band[1]:.2f} m', '', 'inf', 'photos t1/t2 (checked on the t2 render: u/R within 0.05 at three rows)'),
        dim('SW wing tip (plan)', f'{DT.WING_TIP[0]} deg, {DT.WING_TIP[1] * f["D"] / 15.2:.2f} m from the axis', '', 'inf',
            'the point reproducing photos t3/t4', 'BT-01'),
        dim('NE blade top', TW.tip_h, 'm', 'obs', 'photos t3 / t4 / t5: flush with the flare corner and the ribbon head (round 3: deck + 1.2, '
            'withdrawn)'),
        dim('roof masts', f'{len(DT.MASTS)} whips (tips up to {TW.rim_h + max(h for b, h in DT.MASTS) * TW.k:.2f} m) + '
            f'{len(DT.POLES)} poles; red obstruction light in every LOD', '', 'obs count / inf positions',
            'photos t2/t3 (2025); spec h_antenna_tips 71.8 spec m (2025, obs ratio) / station_2015 70.7'),
        dim('cladding joints', f'{DT.N_JOINTS} helical joints + panel rows as dark lines (base-colour tile), 2 dark seam bands {G.SEAM_W} m',
            '', 'obs look (t2 / t4) / inf widths', 'tools/blender/tower_tex.py clad_color'),
        dim('cab panes', f'{G.CAB_PANES} flat panes, full ring, tinted see-through (alpha 0.5), light joints', '', 'pub count (ENR) / inf arc',
            'ENR 24 x 6 x 11 ft; look obs t1 / t2'),
        dim('roof garden', f'{G.GARDEN_DROP} m below the IBF roof, s >= {G.GARDEN[0]} m / t >= {G.GARDEN[1]} m', '', 'obs outline / inf level',
            'NAIP 2024 vegetated pixels, lean-corrected; 2,000 sq ft [pub]', 'BT-01 (note only)'),
    ]
    inferred = [
        f'height family: F{D_} is the default file (tower.glb: anchored on the observed cab-roof diameter); F{A_} '
        f'({FILE[A_]}) is the published-height hypothesis (221 ft = rim, CTBUH class); the owner decides (buildings_tower.md 12.3)',
        'every vertical station (rim - k x D), the base-building roof (rim - 3.46 D - 0.7) and the cab floor',
        'shaft axis (-740.5, 324.5) and cab centre (-739, 323.5) +-5 m in x: NAIP lean; not surveyed',
        'radius profile: A380-photo width ratios / 1.015 x D (PCHIP between the drawn stations)',
        'slot count (13 positions every 27.7 deg, none in 230-335), slot recess depth 0.25 m, helical joint count (68) and '
        'twist (2.6 deg per spec m)',
        'landside plan: ribbon 1 m inside the round body, facing 310; NE blade root / tip widths; SW wing lobe shape between the '
        'BT-01 plan points; wing protrusion 0.5 m at the foot',
        'cab glass ring 360 deg (photos show glass on both sides; the published 220 / 235 / 270 deg are view / column-free angles); '
        'its transparency (alpha 0.6, review round 2: was 0.5) and tint; the pane butt joints (0.03 m, dark: the published '
        'frameless butt glazing, photo t2) and the dark shade band inside the glass head (from 0.62 of the slant; obs t1, nature '
        'and tone inf)',
        'slot screens (review round 2): a perforated sheet 0.06 m behind the cladding face over every slot cell above the glazed '
        'lowest pane (obs photo t4: a dot grid); hole pitch ~0.05 m, hole 0.022 m, sheet tone sRGB 122-131 (tuned to the t2 '
        'slot / panel display ratio ~0.6-0.7) and the void behind are inf',
        'LED ribbon night colour: the observed photo-t5 blue (median sRGB 82 / 137 / 209) as the default of a programmable '
        'array (material extras.led_color, linear (0.077, 0.536, 2.848): the photo chroma compensated for the app\'s tone '
        'mapping, at the loader\'s previous mean level); any other night '
        'colour or animation is unknown (manifest night_glow)',
        'cab roof deck 0.30 m below the rim coping; inner curb r 4.75 m, 0.3 m high',
        'mast / pole bearings and heights (+-5 deg / +-0.3 m); pole heads schematic; red-light bearing (225, SW)',
        'base-building panel module 3.0 x 1.2 m, glazing-band mullions 1.5 m, parapet 0.7 m',
        'roof-garden level (1.7 m below the roof); rooftop unit position (photo t4, +-5 m)',
        'joint line width / tone (6.5 cm, 0.35 x), seam band width (0.10 m), per-panel tone (+-5 %)',
        'all materials / finishes (colours chosen to match the reference photos; no photo pixels used)',
    ]
    unknown = [
        'what the published 221 ft measures (rim or mast tips)',
        'blade / channel plan depth beyond the BT-01 wing-tip point; channel wall geometry',
        'cab glazing pane phase; cab interior: floor (sRGB 74), console ring (0.9 m high, 0.8 m deep, 0.25 m inside the sill; '
        'sRGB 96) and ceiling (sRGB 62) are neutral placeholders (no source for the furniture; 13 positions in a snippet, '
        'unverified)',
        'obstruction-light fixture type (L-810 steady / L-864 flashing) and count (one seen, t5)',
        'core diameter, floor levels (not visible; not modelled)',
        'airside face of the base building SW of u -12.9 (hidden in photo t2): drawn as plain panels',
        'foot of the landside curtain-wall bay (below 9.6 m from the roof): drawn as panels',
        'NE and SW faces of the base building (grey metal panels per the spec text)',
        'the base building lower face on the airside (hidden by the gates in t2)',
    ]
    not_modelled = [
        'T1-T2 connector corridors (one with a 35-ft glass ceiling) [pub]: plan not in any source',
        'the cab centre column and three landside tension columns [snippet, unverified]',
        'the 2015 jib davit on the SW flare deck (construction-era, not in 2025 photos)',
        'tuned mass dampers, lightning discharge system (not visible)',
        'the Terminal 2 AirTrain station block seen beside the shaft in the photos (91 m NW; not part of this asset)',
    ]
    TW2 = results[2]['tower'] if 2 in results else None
    conflicts = [
        (f'F2: the 147-ft ribbon from the F2 base-building roof ({TW2.ibf:.2f} m) would end at {TW2.ibf + G.RIB_H:.2f} m, above the F2 '
         f'flare corner ({TW2.h_top:.2f} m): drawn capped at the flare corner ({TW2.ht - TW2.hb:.1f} m) in {FILE[2]}') if TW2 is not None else '',
        'upper slots: the one at ~348 deg reaches the NE blade root at the top of the band (the sheet lets the blade cover it); '
        'clipped 0.3 m clear of the crease in 3-D',
        'cab glass: ENR 24 panes x 6 ft vs the ring circumference (5.6 ft per pane at the head): the 24-pane ring is kept',
    ]
    lods = []
    for lod in (0, 1, 2):
        sw = G.LODS[lod]['switch_m']
        lods.append(dict(node=f'LOD{lod}', tris=rD['stats'][lod]['tris'], **{f'tris_f{A_}': rA['stats'][lod]['tris'] if rA else None},
                         switch_m=[sw[0], sw[1]], ao_atlas=rD['ao'].get(lod, {}).get('res'), nodes=rD['stats'][lod]['nodes']))
    tex = rD['info']['images']
    an = {fam: anchors(results[fam]['tower']) for fam in results}
    return dict(
        name='SFO air traffic control tower (2016) and base building (IBF)',
        files=dict(default='data/buildings3d/' + FILE[D_], **{f'F{fam}': 'data/buildings3d/' + FILE[fam] for fam in results},
                   lod2_only=rD['info'].get('lod2_file', {}).get('path'), lod2_family=f'F{D_}'),
        default=f'F{D_}', family_decided=False,
        family_roles={f'F{k}': v for k, v in FAM_ROLE.items()},
        family_note='Two self-consistent height families (docs/research/buildings_tower.md 12.3). Default (3-D review round 1, '
                    '2026-11-05): F2 (D 14.5, rim 64.0) lies within the observations (cab-roof D 14.3 +-1.0 measured, 14.75 +-0.5 EXIF; '
                    'rim 63.3-64.1 m for D 14.3, 65 +-2 m for D 14.75); F1 (D 15.2, rim 67.36 = 221 ft) needs D >= 15.1 and rests on '
                    'the CTBUH classification of 221 ft (a database class, not a survey): kept as the published-height hypothesis '
                    '(tower_f1.glb, ?b3dtower=f1). Settle with a surveyed ground photo, the NAIP shadow with the flight time, or an '
                    'SFO / FAA elevation drawing.',
        bytes=dict(**{f'F{fam}': results[fam]['info']['bytes'] for fam in results}, lod2_only=rD['info'].get('lod2_file', {}).get('bytes')),
        placement=dict(frame='ltp-nad83-2011 (js/geo.js): x east, y up, z south, m from the ARP; ground GROUND_Y = 3.0',
                       root_translation=[float(G.AXIS[0]), GROUND_Y, float(G.AXIS[1])],
                       note='root node "tower" carries the translation; geometry is local to the shaft axis at grade'),
        anchors=an[D_], **{f'anchors_f{fam}': an[fam] for fam in results},
        anchors_note='anchors = the default family (tower.glb); each file also carries its own in the root node extras (userData.anchors '
                     'in three.js): js/three/buildings3d.js takes the tower camera and the in-cab test from the loaded file',
        lods=lods, textures=tex,
        texture_note='AO atlases on TEXCOORD_1 (grey-scale PNG, sun-independent, Cycles); detail tiles on TEXCOORD_0 (procedural, '
                     'tools/blender/tower_tex.py): the cladding base colour (joint lines, per-panel tone) + normal tile (4 x 2 panels), '
                     'the slot-screen base colour (perforated sheet: a staggered hole grid on the same 4 x 2 tile, review round 2), '
                     'louvres, base-building panels. KTX2 / meshopt: later (tools/engine/glb_compress.mjs).',
        night_glow=_night_glow(rD['glb']),
        dimensions=dims, inferred=inferred, unknown=unknown, not_modelled=not_modelled, conflicts=[c for c in conflicts if c],
        node_extras='every node: extras {src, feature, spec (spec_tower.json keys), drawing, tags}; materials: extras.src '
                    '(+ led / led_color / obstruction_light / ambient_only for the app)',
        verification=dict(**{f'F{fam}': ver[fam]['summary'] for fam in ver},
                          max_abs_dev_m=max(abs(c['dev']) for fam in ver for c in ver[fam]['checks'] if c['unit'] == 'm'),
                          gltf_validator={f'F{fam}': ver[fam].get('gltf_validator') for fam in ver}, file='out/buildings3d/tower_verify.json',
                          tolerance='0.5 m or 2 % per dimension (deg / m2 where stated)',
                          failures=[dict(c, family=f'F{fam}') for fam in ver for c in ver[fam]['checks'] if not c['ok']],
                          plausibility=vD['plausibility']),
        integration=dict(
            replaces='js/live/terminals.js buildTower() + the atc branch of js/live/airport.js (procedural shaft at the footprint '
                     'centroid, 7.2 m S of the inferred axis)',
            app_parts_over_footprint=vD['plausibility'].get('app_parts_over_footprint'),
            action='cut the base-building footprint (below its parapet) out of the listed app parts of data/sfo_buildings.json ('
                   + '; '.join(f"{o['part']} h {o['h']}: {o['overlap_m2']} m2" for o in (vD['plausibility'].get('app_parts_over_footprint') or []))
                   + ' of overlap with the asset below 20 m) or the base building disappears inside the T2 hall volume',
            exclusion_footprint_world=[[round(float(x), 2), round(float(z), 2)] for x, z in
                                       np.asarray(DT.D.sfom('Air Traffic Control Tower')[0][0], float)],
            flare_overhang=dict(centre_world=[float(G.AXIS[0]), float(G.AXIS[1])],
                                radius_m=round(max(results[fam]['tower'].r_top for fam in results) + 2.0, 2),
                                above_h=round(min(results[fam]['tower'].h_top for fam in results) - 8.0, 1),
                                note='round flare + SW wing (both families); nothing else reaches this height'),
            tower_camera=dict(eye_world=[float(G.CAB_W[0]), round(GROUND_Y + TW.floor_h + 1.6, 2), float(G.CAB_W[1])],
                              **{f'eye_world_f{fam}': [float(G.CAB_W[0]), round(GROUND_Y + results[fam]['tower'].floor_h + 1.6, 2), float(G.CAB_W[1])]
                                 for fam in results},
                              note='js/live/app.js view "tower" takes world.towerPos.eyeY (set by js/three/buildings3d.js from the loaded '
                                   'file\'s anchors.cab_eye_h; GROUND_Y + 62 before a tower file is shown); the cab glass (alpha-blended) is '
                                   'hidden while the camera is inside the glass ring of the loaded family'),
            lod_files=dict(all='data/buildings3d/tower.glb (LOD0-2, F2)', alternative='data/buildings3d/tower_f1.glb (LOD0-2, F1)',
                           phone='data/buildings3d/tower_lod2.glb (LOD2 only, F2)')),
        renders=renders,
        build=dict(cmd='python3 tools/blender/build_tower.py --render --audit', tools=['tools/blender/build_tower.py', 'tools/blender/tower_geom.py',
                   'tools/blender/tower_tex.py', 'tools/blender/tower3d_verify.py'], bpy=__import__('bpy').app.version_string
                   if 'bpy' in sys.modules else None, git=rev, seconds=secs, ao_samples=args.ao_samples,
                   date=__import__('datetime').date.today().isoformat()),
    )


# ------------------------------------------------------------------------------------------------ docs/research/buildings3d.md
DOC_BEGIN, DOC_END = '<!-- tower:begin (written by tools/blender/build_tower.py) -->', '<!-- tower:end -->'


# Review round 1 of the 3-D asset (2026-11-05, 9 items): what was done, with the evidence (numbers re-measured after the fix)
REVIEW_R1 = [
    '1 (major) cladding read as flat grey plastic, seams as light raised bands - FIXED: procedural base-colour + normal tile '
    '(4 joints x 2 rows per tile) with dark helical and row joint lines; the two seams are dark 0.10-m joint bands flush in the '
    'shell (the light 0.03-m-proud band is withdrawn); material seam 98 / clad 150 sRGB (was 196 / 149).',
    '2 (major) NE blade spike above the flare rim - FIXED in the sheet first (draw_tower.NE_TIP = 0, BT-02 redrawn: flush with '
    'the flare corner and the ribbon head, photos t3 / t4 / t5 re-read), then in 3-D: prow top = flare corner, F2 55.93 m '
    '(F1 58.90; was 61.7 F1), verify check "NE blade top". The deck over the landside sector (wing, ribbon head, NE blade) is '
    'now flat, then rises ~14 deg to the plinth (photos t3 / t4: flat blade tops; from t4, ~30 deg below, no deck shows above '
    'the blade or the ribbon head): a first rebuild with the round-body shoulder there showed a sunlit facet above the NE blade.',
    '3 (major) cab an opaque black band - FIXED: tinted see-through glass (alpha 0.5, teal-grey; far-side panes and sky show '
    'through) with light 6-cm joints; glass / sky: Cycles t2 0.25 (photo 0.28), t3 0.16 (photo 0.10).',
    '4 (major) shaft as bright as the sky in the app - CHECKED at the photo\'s sun, albedo kept: APP_NOTE.',
    '5 (minor) upper slots too wide / long slot right of centre - FIXED width and phase in the sheet (SLOT_W 1.4 -> 0.95 m, '
    'SLOT_PHASE 124 -> 127, t1 + t2 together); the long-slot offset is REJECTED: at the same three rows the t2 photo reads u/R '
    '+0.37 / +0.12 / -0.07, the render +0.34 / +0.07 / -0.11 (within 0.05 = ~3 deg); the review compared different rows.',
    '6 (major) red obstruction light only in LOD0, no masts in LOD2 - FIXED: the red-light fixture (material red_light, the '
    'app\'s beacon glow) is in LOD0 / LOD1 / LOD2 and in tower_lod2.glb, LOD2 carries the 15 whips (3-sided): the top is 68.48 m '
    '(F2) at every LOD.',
    '7 (major) F1 default - FIXED: tower.glb = F2 (default, within the observations), tower_f1.glb = F1 (the published-height '
    'hypothesis, ?b3dtower=f1); family_decided stays false.',
    '8 (minor) mast tips vs spec - FIXED: spec h_antenna_tips = 71.8 spec m (2025-08-12 obs ratio 0.30-0.31 D; 2015 station 70.7 '
    'kept as station_2015); F2 restated as "221 ft at the 2015 mast station"; mesh vs spec 2025 value: F2 68.48 vs 68.50, F1 '
    '72.06 vs 72.08.',
    '9 (minor) tower camera / in-cab test on F1 values - FIXED: the loader takes eye and bounds from the loaded file\'s '
    'anchors (root extras); app.js reads towerPos.eyeY (one-line hook); APP_EYE.',
]
APP_NOTE = ('the review compared the app at the snapshot time (sun az 134 / el 42 behind the camera: cos 0.74 on the face) '
            'with photo t2 (11:57 PDT, sun az 137 / el 62: cos 0.47). Same camera and sun as t2 (tools/blender/tower_app_job.mjs, '
            'out/buildings3d/app/tapp_t2.png): lit shaft / sky 0.82 in the app, 0.77 in Cycles (tower_t2.png), photo 0.82 against '
            'the blue sky / 0.70 against the fog; metalness 0 instead of 0.15: 0.83, base colour x 0.85: 0.62 (too dark). At the '
            'snapshot time (t2like) 1.08. The clad albedo (~0.31 linear) also reproduces the photo\'s shaft / bridge-roof ratio, so '
            'it is kept. The Cycles photo suns were typed in by hand in round 1 (t2 az 165, t3 110): now computed (NOAA; 137.4 / '
            '95.5); the cab glass reads 0.12 of the sky in the app from 12 deg below (the unlit ceiling behind the upper half, the '
            'sky through the lower half; Cycles 0.25 with interior bounce light; photos 0.28 / 0.10)')
APP_EYE = ('app check: tower view eye at y 62.15 = GROUND_Y + 59.151 (F2), glass hidden inside the ring (tapp_towercam.png); '
           'F1 file anchors: eye 62.2 above grade, glass head r 6.537')

# Review round 2 of the 3-D asset (2026-11-05, 4 items). Numbers measured on the final renders: Cycles = the photo|render
# comparisons tower_compare_t2/t3.jpg (grey levels, meas: slot runs < 0.8 x the local median along rows 260 / 530; cab:
# vertical profile through the cab centre); app = out/buildings3d/app/r2/*.png (three.js, llvmpipe)
R2N = dict(
    slot_c='Cycles t2, display ratio slot / neighbouring panels: upper band 0.64-0.74 (photo 0.69-0.76; round 1 0.10-0.20), '
           'long slot 0.73 (photo 0.62-0.72; round 1 0.30); a first pass with the sheet at sRGB 112-121 gave 0.56-0.65 / 0.66.',
    slot_app='R2_SLOT_APP', glass_c='R2_GLASS_C', glass_app='R2_GLASS_APP', moire='R2_MOIRE', led='R2_LED', towercam='R2_TOWERCAM')
REVIEW_R2 = [
    '1 (major) slots read as black gashes - FIXED: every slot cell above its glazed lowest pane carries a perforated screen '
    '0.06 m behind the cladding face (obs photo t4: a dot grid; base-colour tile tower_tex.slot_color, a staggered hole grid '
    '~0.05 m pitch on a sheet sRGB 122-131: tile linear albedo 0.56 x the cladding tile), a light reveal (the panel return) '
    'and the dark pocket behind; LOD1 / LOD2 flat slots take the screen tone (material slot_screen). {slot_c} {slot_app} '
    'At night the screens stay dark (photo t5); only the glazed lowest panes keep the office glow.',
    '2 (major) cab glass an empty jar from below, two-tone - FIXED: a dark shade band inside the glass head (obs photo t1: the '
    'top ~0.35-0.4 of the glass dark all round; from 0.62 of the slant, 0.12 m inside the glass) hides the far side\'s sky that '
    'showed through the lower third; the ceiling is mid-dark (sRGB 62), the glass a lighter teal-grey tint (80, 98, 106) at '
    'alpha 0.6 (two panes pass 16 % of the sky). {glass_c} {glass_app}',
    '3 (minor) light joints, black in-cab void, floor moire - FIXED: pane butt joints 0.03 m and dark (sRGB 38-43; the '
    'published frameless butt glazing, the thin dark joints of t2; were light 0.06 m); a neutral console ring (0.9 m high, '
    '0.8 m deep, sRGB 96) and floor (sRGB 74) as unknown placeholders, in their own node cab_interior without baked AO (the Cycles AO of the enclosed cab was noisy and read as blotches in the tower view). Floor moire: root cause measured on the low tier '
    '(tools/blender/tower_app_job.mjs experiments, old file, out/buildings3d/app/r2exp/): high-pass of the floor 50.5 grey '
    'levels per pixel, 50.0 with GTAO off (aoAmount 0), 0.65 with the floor\'s receiveShadow off: the sun shadow test, not AO '
    'or a texture. The alpha-blended glass casts no shadow, so the sun reached the whole floor through the glass ring and '
    'the floor sat in the PCF penumbra of the 1024-px low-tier cascade, whose per-pixel rotated taps TRAA did not average. The '
    'interior placeholders (floor, consoles, shade band, ceiling) are now lit by the sky only (material extras.ambient_only: '
    'the loader gives them an empty lights node, no sun, no shadow lookup; IBL x baked AO stays). {moire} {towercam}',
    '4 (minor) LED ribbon glows white at night - FIXED: the ribbon material carries extras.led_color = the observed photo-t5 '
    'blue (median sRGB 82 / 137 / 209 of the lit ribbon, Varnum 2018-04 dusk; linear (0.084, 0.250, 0.638)), scaled to '
    'the loader\'s previous mean level and compensated for the app\'s AgX desaturation (a first night render with the '
    'photo-linear colour showed hue 209 / saturation 0.35 against the photo\'s 214 / 0.58; display ratios fit out = in^0.56, '
    'so the input is (0.077, 0.536, 2.848)); the loader glows in that colour (the wave modulates the level only; GLOW_DEF.led / '
    'setGlow(\'led\') tint and scale it at run time) and the manifest lists it under night_glow as the observed default of a '
    'programmable array, inferred for any other night. {led}',
]


def doc_section(entry, ver):
    """the tower section of docs/research/buildings3d.md, from the manifest entry and the verification."""
    D_ = DEFAULT_FAM; A_ = 3 - D_
    vD = ver[D_]; L = entry['lods']; a = entry['anchors']; aA = entry.get(f'anchors_f{A_}') or {}
    fails = entry['verification']['failures']
    lines = [DOC_BEGIN, '## Control tower (ATCT 2016) and base building: `data/buildings3d/tower.glb`', '',
             '```bash', 'python3 tools/blender/build_tower.py --render --audit   # both families, AO bake, export, manifest, '
             'verification, renders (~16 min, 4 CPUs)', 'python3 tools/blender/tower3d_verify.py data/buildings3d/tower.glb 2   '
             '# re-measure an exported file (tower.glb = F2, tower_f1.glb = F1)', '```', '',
             '**Source of the geometry.** Everything is generated from the approved sheets BT-01..03: `tools/blender/tower_geom.py` '
             'imports `tools/buildings/draw_tower.py` (and through it `spec_tower.json` and the SFO Museum footprint) and uses its '
             'functions and constants (`shaft_outline`, `cab_outline`, `plinth`, `SHOULDER`, slot / mast / pole bearings, `WING_TIP`, '
             '`NE_TIP`, `RIB_BRG`, `IBF_AIR_BAND`, `IBF_CW`, rows / twist of the cladding). Nothing is typed in twice. The one new '
             'measurement is the roof-garden outline (NAIP 2024 vegetated pixels, lean-corrected). No imagery is used as a texture.', '',
             f'**Height family.** The sheets draw two self-consistent families (buildings_tower.md 12.3). Default (3-D review round 1, '
             f'2026-11-05): `tower.glb` = F2 (D 14.5, rim 64.0; 221 ft at the 2015 mast station), the family that lies within the '
             f'observations (cab-roof D 14.3 +-1.0 measured, 14.75 +-0.5 EXIF; rim 63.3-64.1 m for D 14.3 and 65 +-2 m for D 14.75 in '
             f'the `h_roof_top` test). `tower_f1.glb` = F1 (D 15.2, rim 67.36 = 221 ft at the rim) is the published-height hypothesis: '
             f'it needs D >= ~15.1 and rests on the CTBUH classification of 221 ft (a database class, not a survey); `?b3dtower=f1` '
             f'loads it. `manifest.json#tower.family_decided = false`: the owner decides.', '',
             '**Placement.** Root node `tower` at world (-740.5, GROUND_Y, 324.5) = the inferred shaft axis at grade '
             '(x east, y up, z south, js/geo.js). Cab-floor / eye heights and the other anchors are in the root extras of each file '
             f'and the manifest (F2: floor {a["cab_floor_h"]} m, eye {a["cab_eye_h"]} m, glass {a["glass_sill_h"]}-{a["glass_head_h"]} m, '
             f'rim {a["roof_rim_h"]} m, highest whip {a["mast_tip_max_h"]} m; F1: floor {aA.get("cab_floor_h")}, eye {aA.get("cab_eye_h")}, '
             f'glass {aA.get("glass_sill_h")}-{aA.get("glass_head_h")}, rim {aA.get("roof_rim_h")}, whip {aA.get("mast_tip_max_h")} m).', '',
             f'| LOD | Use (suggested camera distance) | Triangles F2 / F1 | AO atlas (TEXCOORD_1) | Content |', '|---|---|---|---|---|']
    use = {0: '< 350 m (close-up, tower view)', 1: '350-1200 m', 2: '> 1200 m; phone (`tower_lod2.glb`, F2)'}
    cont = {0: '272 helical columns, recessed slots with perforated screens and glazed lowest panes, dark seam joints, 24 tinted '
               'cab panes + slim dark joints, cab interior (floor, console ring, shade band, ceiling), ribbon '
               'mullions, 15 whips + 9 poles + red light, base-building mullions, coping, rails, rooftop unit, sunken garden',
            1: '136 columns, flat slots (screen tone), dark seam joints, 24-facet cab, 15 whips + red light, plain base building with parapet',
            2: '68 columns, flat slots, 12-facet cab, 15 whips (3-sided) + red light, base building as a box'}
    for l in L:
        lod = int(l['node'][3:])
        lines.append(f"| {l['node']} | {use[lod]} | {l['tris']:,} / {l.get(f'tris_f{A_}') or 0:,} | {l['ao_atlas']} px | {cont[lod]} |")
    b = entry['bytes']
    lines += ['', f"Files: `tower.glb` (F2) {b['F2'] / 1e6:.2f} MB, `tower_f1.glb` {b['F1'] / 1e6:.2f} MB, "
              f"`tower_lod2.glb` (F2) {b['lod2_only'] / 1e6:.2f} MB (PNG textures; KTX2 / meshopt later with "
              '`tools/engine/glb_compress.mjs`). Materials are PBR (our choices for the published "SFO Silver" ACM, glass, panels; '
              '`extras.src` on every material). The cladding carries a procedural base-colour + normal tile on TEXCOORD_0 '
              '(`tools/blender/tower_tex.py`, 4 joints x 2 panel rows per tile): dark helical and row joint lines (6.5 cm, 0.35 x the '
              'panel tone at the centre) and a +-5 % tone per panel, mip-mapped (no moire); the two circumferential seams are dark '
              '0.10-m joint bands flush in the shell. The slots are recessed pockets with a perforated screen 0.06 m behind the face '
              '(base-colour tile: a staggered hole grid on a mid-grey sheet) and a light reveal. The cab glass is tinted and '
              'see-through (alpha 0.6, double-sided: the far-side panes and the sky show through in a level view) with slim dark '
              '3-cm butt joints; behind it a neutral placeholder interior (floor, console ring, a dark shade band inside the glass '
              'head, mid-dark ceiling). Sun-independent AO baked by Cycles (48 samples, 8 m '
              'rays, ground plane as occluder). Every other surface is single-sided and wound outwards (back-face audit renders).', '',
              '**Verification** (`out/buildings3d/tower_verify.json`, measured on the exported GLB against the sheet functions):',
              f"- F2 (default): {ver[2]['summary']}" if 2 in ver else '', f"- F1: {ver[1]['summary']}" if 1 in ver else '',
              f"- largest deviation of a length: {entry['verification']['max_abs_dev_m']:.3f} m (tolerance 0.5 m / 2 %); "
              f"{len(fails)} failures.",
              '- Khronos glTF-Validator ' + '; '.join(f"{k}: {g.get('errors')} errors, {g.get('warnings')} warnings, {g.get('infos')} infos "
                                                     f"({', '.join(g.get('codes', {}))})" for k, g in entry['verification']['gltf_validator'].items() if g),
              f"- plausibility (F2): {vD['plausibility']['verdict']}; nearest aircraft envelope {vD['plausibility']['nearest_aircraft_envelope_m']} m "
              f"({vD['plausibility']['nearest_aircraft_stand']}), bridge {vD['plausibility']['nearest_bridge_m']} m, taxiway centreline "
              f"{vD['plausibility']['nearest_taxi_centreline_m']} m.", '',
              '**Integration.** The loader (`js/three/buildings3d.js`) reads the anchors from the loaded file\'s root extras: the app\'s '
              'tower view takes `world.towerPos.eyeY` = GROUND_Y + `cab_eye_h` of that family (js/live/app.js hook; GROUND_Y + 62 '
              'before a tower file is shown), and the alpha-blended cab glass is hidden while the camera is inside that family\'s '
              'glass ring (radius `glass_head_r` + 0.3, `cab_floor_h` - 0.5 .. `glass_head_h` + 0.5). The first-pass T2 hall / BA-D '
              'walkway parts over the base-building footprint are cut by `tools/blender/b3d_integrate.py`.', '',
              '**Renders** (Cycles CPU, 64 samples + OIDN, AgX; ours; of the default family F2): `out/buildings3d/tower_A.png`, '
              '`tower_B.png` (the BT-02 elevations, orthographic; `tower_overlay_A/B.png` carry the sheet outlines in red), '
              '`tower_t2.png`, `tower_t3.png`, `tower_t4.png` (camera-matched to the reference photos t2 / t3 / t4, Famartin 2025, '
              'CC BY-SA 4.0; per family the focal length follows the rim width in pixels and the camera height the angle below the '
              'rim, the sun is computed for the photo time; side-by-side comparisons `tower_compare_*.jpg` stay local). App views '
              '(three.js, llvmpipe, `?b3donly=tower`, photo-matched camera and sun; `tools/blender/tower_app_job.mjs`): '
              '`out/buildings3d/app/tapp_t2.png`, `tapp_t4.png`, `tapp_t4close.png`, `tapp_t2like.png`, `tapp_towercam.png` '
              '(+ `tapp_t2_metal0.png` / `tapp_t2_col085.png`, material experiments), `tower_app_info.json` (round 1). Round 2: '
              '`out/buildings3d/app/r2/tapp_t2.png`, `tapp_t4.png`, `tapp_towercam.png`, `tapp_t4night.png` (21:30 PDT: the LED '
              'ribbon), `r2/low/tapp_lowcam.png` (low tier, tower view); the floor-moire experiments (old file, low tier) in '
              '`out/buildings3d/app/r2exp/`.', '',
              '**Observed vs inferred.** Per dimension in `manifest.json#tower.dimensions`; lists `inferred`, `unknown`, '
              '`not_modelled`, `conflicts` there. Node extras carry `src`, the spec keys and per-feature tags.', '',
              '**Review round 1 (2026-11-05).**'] + ['- ' + r.replace('APP_NOTE', APP_NOTE).replace('APP_EYE', APP_EYE) for r in REVIEW_R1] + [
              '', '**Review round 2 (2026-11-05).**'] + ['- ' + r.format(**R2N) for r in REVIEW_R2] + [
              '',
              '**Open (for the owner).**',
              '- The height family (F2 default / F1 hypothesis).',
              '- t2 camera match: the camera height and focal length are estimates (no EXIF here); a camera-model check only.',
              '- For the domestic group: `tools/blender/dom_geom.py` leaves out the T2 walls that face the base building up to '
              '14.07 m (the F1 roof). With F2 as the default, the base-building parapet tops at 13.83 m, so a 0.24-m slit opens in the '
              'T2 wall above it. Take `anchors.ibf_parapet_h` of the loaded tower file, or the family minimum.',
              '- NE channel wall: louvred like the SW wing (photos t3 / t4). In the sunny t4-matched render its upper part, '
              'which faces bearing 40, catches the 09:10 sun (az 95) and reads bright against the shaded NW faces. The photo was '
              'overcast, so the brightness cannot be compared.',
              '- Obstruction light: one red fixture (t5) is modelled in every LOD; at a few km it is sub-pixel, so a LOD-independent '
              'point sprite belongs to the environment\'s lighting layer (data/sfo_lighting.js lists the tower as obstruction '
              '06-323169, fixtures inferred from AC 70/7460-1N).',
              DOC_END]
    return '\n'.join(x for x in lines if x is not None)


def write_doc(entry, ver):
    path = os.path.join(ROOT, 'docs', 'research', 'buildings3d.md')
    sec = doc_section(entry, ver)
    if os.path.exists(path):
        txt = open(path).read()
        if DOC_BEGIN in txt and DOC_END in txt:
            i = txt.index(DOC_BEGIN); j = txt.index(DOC_END) + len(DOC_END)
            txt = txt[:i] + sec + txt[j:]
        else:
            txt = txt.rstrip('\n') + '\n\n' + sec + '\n'
    else:
        txt = ('# 3-D building assets (Blender, from the verified 2-D sheets)\n\n'
               'One section per asset group, each written by its builder under `tools/blender/`. The assets live in '
               '`data/buildings3d/` with one key per group in `data/buildings3d/manifest.json`. Owner\'s rules: drawings first; '
               'no unverified key assumption (inferred / unknown items are listed per asset); no third-party imagery as textures; '
               'observed vs inferred per asset; nothing physically implausible.\n\n' + sec + '\n')
    tmp = path + '.tower.tmp'
    open(tmp, 'w').write(txt); os.replace(tmp, path)
    return path


if __name__ == '__main__' and '--doc' in sys.argv:
    # rewrite the tower section of docs/research/buildings3d.md from the manifest and the last verification
    ent = json.load(open(os.path.join(ROOT, 'data', 'buildings3d', 'manifest.json')))['tower']
    vj = json.load(open(os.path.join(ROOT, 'out', 'buildings3d', 'tower_verify.json')))
    print(write_doc(ent, {int(k[1:]): v for k, v in vj.items()}))
    sys.exit(0)

if __name__ == '__main__':
    glb = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'data', 'buildings3d', 'tower.glb')
    fam = int(sys.argv[2]) if len(sys.argv) > 2 else (1 if glb.endswith('_f1.glb') else DEFAULT_FAM)
    v = verify(glb, fam)
    for c in v['checks']:
        print(('  ok ' if c['ok'] else 'FAIL '), f"{c['item']:<58} model {c['model']:>9} drawing {c['drawing']:>9} dev {c['dev']:>+7} "
              f"tol {c['tol']} {c['unit']} [{c['tag']}] {c['note']}")
    print(v['summary']); print(json.dumps(v['plausibility'], indent=1))
