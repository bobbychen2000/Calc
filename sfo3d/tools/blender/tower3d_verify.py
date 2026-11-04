"""Verification and packaging helpers of the tower asset (no bpy): GLB read / rewrite, post-processing of the Blender
export, measurement of the exported geometry against the 2-D sheets (tools/buildings/draw_tower.py), plausibility checks
against the surveyed stands / bridges / taxiway centrelines, and the manifest entry.

    python3 tools/blender/tower3d_verify.py [data/buildings3d/tower.glb [1|2]]     # re-measure an exported GLB

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
        glass_head_h=round(c['glass_top'][1], 3), roof_rim_h=round(TW.rim_h, 3), flare_widest_h=round(TW.h_top, 3),
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
            m.setdefault('pbrMetallicRoughness', {})['baseColorFactor'] = list(m.get('pbrMetallicRoughness', {}).get(
                'baseColorFactor', [0.003, 0.005, 0.006, 0.65]))[:3] + [0.65]
        ex = m.setdefault('extras', {})
        if spec:
            ex['src'] = spec['src']
            if spec.get('led'): ex['led'] = True
            if spec.get('light'): ex['obstruction_light'] = True
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
    fl = np.concatenate([p for m, p, i in cab if m == 'cab_interior'])
    res.append(chk('cab floor', fl[:, 1].min(), TW.floor_h, 'inf'))
    # 4. flare widest, shoulder top, NE tip
    sh = _pts(meshes, L0, ['shaft'])
    rr_ = np.hypot(sh[:, 0], sh[:, 2])
    res.append(chk('flare widest radius', rr_.max(), TW.r_top, 'inf', note='1.58 D'))
    res.append(chk('flare widest height', sh[np.argmax(rr_), 1], TW.h_top, 'inf'))
    deck = _pts(meshes, L0, ['flare_deck'], ['clad'])
    dr = np.hypot(deck[:, 0] - cabC[0], deck[:, 2] - cabC[1])
    inner = deck[dr < TW.plinth_r + 0.05]
    res.append(chk('flare deck at the plinth foot', inner[:, 1].min() if len(inner) else np.nan, TW.deck_h, 'inf'))
    res.append(chk('NE blade tip height', deck[:, 1].max(), TW.tip_h, 'obs', note='photo t4 (low): deck + 1.2'))
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
    sl = _pts(meshes, L0, ['shaft'], ['slot'])
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
        p = os.path.join(ROOT, 'out', 'buildings3d', f'tower_overlay_{nm}.png')
        im.save(p); out[f'overlay_{nm}'] = os.path.relpath(p, ROOT)
    for nm in ('t2', 't3', 't4'):
        r = renders.get(nm)
        if not r or not os.path.exists(os.path.join(ROOT, r['photo'])): continue
        a = Image.open(os.path.join(ROOT, r['photo'])).convert('RGB'); b = Image.open(os.path.join(ROOT, r['path'])).convert('RGB')
        a = a.resize(b.size)
        c = Image.new('RGB', (a.width * 2 + 8, a.height), (255, 255, 255)); c.paste(a, (0, 0)); c.paste(b, (a.width + 8, 0))
        p = os.path.join(ROOT, 'out', 'buildings3d', f'tower_compare_{nm}.jpg')
        c.save(p, quality=88); out[f'compare_{nm}'] = os.path.relpath(p, ROOT) + ' (local only: contains a third-party photo)'
    return out


# ------------------------------------------------------------------------------------------------ manifest
def manifest_entry(results, ver, renders, args, rev, secs):
    r1 = results[1]; TW = r1['tower']; f = TW.f
    v1 = ver[1]
    T = DT.T

    def dim(key, value, unit, tag, source, drawing='BT-02', note=''):
        return dict(key=key, value=round(value, 3) if isinstance(value, float) else value, unit=unit, tag=tag, source=source,
                    drawing=drawing, note=note)
    F2 = results.get(2)
    dims = [
        dim('h_roof_top (rim)', TW.rim_h, 'm', 'inf', 'h_top_published 221 ft [pub]; family F1 puts 221 ft at the rim',
            note='F2: 64.0 m (221 ft at the mast tips); family NOT decided'),
        dim('d_cab_roof', f['D'], 'm', 'inf', 'family F1 (measured 14.3 +-1.0 obs, EXIF 14.75 +-0.5 obs)', 'BT-01/02'),
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
        dim('ribbon height / widths', [round(TW.ht - TW.hb, 3), G.RIB_W0, G.RIB_W1], 'm', 'pub / obs low', '147 ft [pub]; widths T2 AirTrain photo'),
        dim('ribbon facing bearing', DT.RIB_BRG, 'deg', 'inf', 'middle of the 300-320 photo range', 'BT-01/02 B'),
        dim('upper slots', f'{len(TW.upper)} slots, {DT.SLOT_W} m wide, sweep {DT.SLOT_SWEEP} deg, band '
            f'{TW.slot_band[0]:.2f}-{TW.slot_band[1]:.2f} m', '', 'inf', 'photos t1/t2 (count, phase inf)'),
        dim('long helical slot', f'bearing {DT.LONG_SLOT[0]} -> {DT.LONG_SLOT[1]}, {DT.LONG_W} m wide, {TW.long_band[0]:.2f}-'
            f'{TW.long_band[1]:.2f} m', '', 'inf', 'photos t1/t2'),
        dim('SW wing tip (plan)', f'{DT.WING_TIP[0]} deg, {DT.WING_TIP[1] * f["D"] / 15.2:.2f} m from the axis', '', 'inf',
            'the point reproducing photos t3/t4', 'BT-01'),
        dim('NE blade tip', TW.tip_h, 'm', 'obs (low)', 'photo t4: flare deck + 1.2'),
        dim('roof masts', f'{len(DT.MASTS)} whips (tips up to {TW.rim_h + max(h for b, h in DT.MASTS) * TW.k:.2f} m) + '
            f'{len(DT.POLES)} poles', '', 'obs count / inf positions', 'photos t2/t3 (2025)'),
        dim('cab panes', f'{G.CAB_PANES} flat panes, full ring', '', 'pub count (ENR) / inf arc', 'ENR 24 x 6 x 11 ft'),
        dim('roof garden', f'{G.GARDEN_DROP} m below the IBF roof, s >= {G.GARDEN[0]} m / t >= {G.GARDEN[1]} m', '', 'obs outline / inf level',
            'NAIP 2024 vegetated pixels, lean-corrected; 2,000 sq ft [pub]', 'BT-01 (note only)'),
    ]
    inferred = [
        'height family: F1 (tower.glb) and F2 (tower_f2.glb) are both built; neither is preferred (buildings_tower.md 12.3); '
        'CTBUH classification favours F1 but is not a survey',
        'every vertical station (rim - k x D), the base-building roof (rim - 3.46 D - 0.7) and the cab floor',
        'shaft axis (-740.5, 324.5) and cab centre (-739, 323.5) +-5 m in x: NAIP lean; not surveyed',
        'radius profile: A380-photo width ratios / 1.015 x D (PCHIP between the drawn stations)',
        'slot count / phase (13 positions every 27.7 deg, none in 230-335), slot recess depth 0.25 m, helical joint count (68) and '
        'twist (2.6 deg per spec m)',
        'landside plan: ribbon 1 m inside the round body, facing 310; NE blade root / tip widths; SW wing lobe shape between the '
        'BT-01 plan points; wing protrusion 0.5 m at the foot',
        'cab glass ring 360 deg (photos show glass on both sides; the published 220 / 235 / 270 deg are view / column-free angles)',
        'cab roof deck 0.30 m below the rim coping; inner curb r 4.75 m, 0.3 m high',
        'mast / pole bearings and heights (+-5 deg / +-0.3 m); pole heads schematic',
        'base-building panel module 3.0 x 1.2 m, glazing-band mullions 1.5 m, parapet 0.7 m',
        'roof-garden level (1.7 m below the roof); rooftop unit position (photo t4, +-5 m)',
        'all materials / finishes (colours chosen to match the reference photos; no photo pixels used)',
    ]
    unknown = [
        'what the published 221 ft measures (rim or mast tips)',
        'blade / channel plan depth beyond the BT-01 wing-tip point; channel wall geometry',
        'cab glazing pane phase; cab interior (floor / ceiling are dark placeholders; consoles not modelled)',
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
    conflicts = [
        'F2: the 147-ft ribbon from the F2 base-building roof (13.13 m) would end at 57.94 m, above the F2 flare corner (55.93 m): '
        'drawn capped at the flare corner (42.8 m) in tower_f2.glb' if F2 else '',
        'slot 345.5 deg: its top corner falls on the NE blade root (the sheet lets the blade cover it); clipped 0.3 m clear of '
        'the crease in 3-D',
        'cab glass: ENR 24 panes x 6 ft vs the ring circumference (5.6 ft per pane at the head): the 24-pane ring is kept',
    ]
    lods = []
    for lod in (0, 1, 2):
        sw = G.LODS[lod]['switch_m']
        lods.append(dict(node=f'LOD{lod}', tris=r1['stats'][lod]['tris'], tris_f2=F2['stats'][lod]['tris'] if F2 else None,
                         switch_m=[sw[0], sw[1]], ao_atlas=r1['ao'].get(lod, {}).get('res'),
                         nodes=r1['stats'][lod]['nodes']))
    tex = r1['info']['images']
    return dict(
        name='SFO air traffic control tower (2016) and base building (IBF)',
        files=dict(F1='data/buildings3d/tower.glb', F2='data/buildings3d/tower_f2.glb' if F2 else None,
                   F1_lod2_only=r1['info'].get('lod2_file', {}).get('path')),
        default='F1', family_decided=False,
        family_note='Two self-consistent height families (docs/research/buildings_tower.md 12.3). The sheets draw both and prefer '
                    'neither; F1 is the default file only because CTBUH classifies 221 ft as excluding antennae (not a survey). '
                    'Settle with a surveyed ground photo, the NAIP shadow with the flight time, or an SFO / FAA elevation drawing.',
        bytes=dict(F1=r1['info']['bytes'], F2=F2['info']['bytes'] if F2 else None,
                   F1_lod2_only=r1['info'].get('lod2_file', {}).get('bytes')),
        placement=dict(frame='ltp-nad83-2011 (js/geo.js): x east, y up, z south, m from the ARP; ground GROUND_Y = 3.0',
                       root_translation=[float(G.AXIS[0]), GROUND_Y, float(G.AXIS[1])],
                       note='root node "tower" carries the translation; geometry is local to the shaft axis at grade'),
        anchors=anchors(TW), anchors_f2=anchors(F2['tower']) if F2 else None,
        lods=lods, textures=tex,
        texture_note='AO atlases on TEXCOORD_1 (grey-scale PNG, sun-independent, Cycles); detail normal tiles on TEXCOORD_0 '
                     '(procedural, tools/blender/tower_tex.py). KTX2 / meshopt: later (tools/engine/glb_compress.mjs).',
        dimensions=dims, inferred=inferred, unknown=unknown, not_modelled=not_modelled, conflicts=[c for c in conflicts if c],
        node_extras='every node: extras {src, feature, spec (spec_tower.json keys), drawing, tags}; materials: extras.src '
                    '(+ led / obstruction_light flags for the app)',
        verification=dict(F1=ver[1]['summary'], F2=ver[2]['summary'] if 2 in ver else None,
                          max_abs_dev_m=max(abs(c['dev']) for c in v1['checks'] if c['unit'] == 'm'),
                          gltf_validator=dict(F1=ver[1].get('gltf_validator'), F2=ver[2].get('gltf_validator') if 2 in ver else None), file='out/buildings3d/tower_verify.json',
                          tolerance='0.5 m or 2 % per dimension (deg / m2 where stated)',
                          failures=[c for c in v1['checks'] if not c['ok']], plausibility=v1['plausibility']),
        integration=dict(
            replaces='js/live/terminals.js buildTower() + the atc branch of js/live/airport.js (procedural shaft at the footprint '
                     'centroid, 7.2 m S of the inferred axis)',
            app_parts_over_footprint=v1['plausibility'].get('app_parts_over_footprint'),
            action='cut the base-building footprint (below its parapet) out of the listed app parts of data/sfo_buildings.json ('
                   + '; '.join(f"{o['part']} h {o['h']}: {o['overlap_m2']} m2" for o in (v1['plausibility'].get('app_parts_over_footprint') or []))
                   + ' of overlap with the asset below 20 m) or the base building disappears inside the T2 hall volume',
            exclusion_footprint_world=[[round(float(x), 2), round(float(z), 2)] for x, z in
                                       np.asarray(DT.D.sfom('Air Traffic Control Tower')[0][0], float)],
            flare_overhang=dict(centre_world=[float(G.AXIS[0]), float(G.AXIS[1])], radius_m=round(TW.r_top + 2.0, 2),
                                above_h=round(TW.h_top - 8.0, 1), note='round flare + SW wing; nothing else reaches this height'),
            tower_camera=dict(eye_world=[float(G.CAB_W[0]), round(GROUND_Y + TW.floor_h + 1.6, 2), float(G.CAB_W[1])],
                              note='js/live/app.js view "tower" uses GROUND_Y + 62 at world.towerPos; use anchors.cab_eye_h instead; hide '
                                   'node cab_glass (alpha-blended) for the in-cab camera if the renderer sorts it badly'),
            lod_files=dict(all='data/buildings3d/tower.glb (LOD0-2)', phone='data/buildings3d/tower_lod2.glb (LOD2 only)')),
        renders=renders,
        build=dict(cmd='python3 tools/blender/build_tower.py --render', tools=['tools/blender/build_tower.py', 'tools/blender/tower_geom.py',
                   'tools/blender/tower_tex.py', 'tools/blender/tower3d_verify.py'], bpy=__import__('bpy').app.version_string
                   if 'bpy' in sys.modules else None, git=rev, seconds=secs, ao_samples=args.ao_samples,
                   date=__import__('datetime').date.today().isoformat()),
    )


# ------------------------------------------------------------------------------------------------ docs/research/buildings3d.md
DOC_BEGIN, DOC_END = '<!-- tower:begin (written by tools/blender/build_tower.py) -->', '<!-- tower:end -->'


def doc_section(entry, ver):
    """the tower section of docs/research/buildings3d.md, from the manifest entry and the verification."""
    v1 = ver[1]; L = entry['lods']; a = entry['anchors']
    fails = entry['verification']['failures']
    lines = [DOC_BEGIN, '## Control tower (ATCT 2016) and base building: `data/buildings3d/tower.glb`', '',
             '```bash', 'python3 tools/blender/build_tower.py --render --audit   # both families, AO bake, export, manifest, '
             'verification, renders (~16 min, 4 CPUs)', 'python3 tools/blender/tower3d_verify.py data/buildings3d/tower.glb   '
             '# re-measure an exported file', '```', '',
             '**Source of the geometry.** Everything is generated from the approved sheets BT-01..03: `tools/blender/tower_geom.py` '
             'imports `tools/buildings/draw_tower.py` (and through it `spec_tower.json` and the SFO Museum footprint) and uses its '
             'functions and constants (`shaft_outline`, `cab_outline`, `plinth`, `SHOULDER`, slot / mast / pole bearings, `WING_TIP`, '
             '`RIB_BRG`, `IBF_AIR_BAND`, `IBF_CW`, rows / twist of the cladding). Nothing is typed in twice. The one new measurement is '
             'the roof-garden outline (NAIP 2024 vegetated pixels, lean-corrected). No imagery is used as a texture.', '',
             '**Height family.** The sheets draw two self-consistent families and prefer neither (buildings_tower.md 12.3). Both are '
             'built: `tower.glb` = F1 (D 15.2, rim 67.36 = 221 ft), `tower_f2.glb` = F2 (D 14.5, rim 64.0, 221 ft at the masts). '
             'F1 is the default file only because CTBUH classifies 221 ft as a height without antennae (not a survey). '
             '`manifest.json#tower.family_decided = false`.', '',
             '**Placement.** Root node `tower` at world (-740.5, GROUND_Y, 324.5) = the inferred shaft axis at grade '
             '(x east, y up, z south, js/geo.js). Cab-floor / eye heights and the other anchors are in the root extras and the '
             f'manifest (F1: floor {a["cab_floor_h"]} m, eye {a["cab_eye_h"]} m, glass {a["glass_sill_h"]}-{a["glass_head_h"]} m, '
             f'rim {a["roof_rim_h"]} m, highest mast {a["mast_tip_max_h"]} m).', '',
             '| LOD | Use (suggested camera distance) | Triangles F1 / F2 | AO atlas (TEXCOORD_1) | Content |', '|---|---|---|---|---|']
    use = {0: '< 350 m (close-up, tower view)', 1: '350-1200 m', 2: '> 1200 m; phone (`tower_lod2.glb`)'}
    cont = {0: '272 helical columns, recessed slots with glazed panes, seams, 24 cab panes + joints, ribbon mullions, 15 whips + '
               '9 poles + red light, base-building mullions, coping, rails, rooftop unit, sunken garden',
            1: '136 columns, flat slots, 24-facet cab, 15 whips, plain base building with parapet',
            2: '68 columns, flat slots, 12-facet cab, no masts, base building as a box'}
    for l in L:
        lod = int(l['node'][3:])
        lines.append(f"| {l['node']} | {use[lod]} | {l['tris']:,} / {l['tris_f2']:,} | {l['ao_atlas']} px | {cont[lod]} |")
    lines += ['', f"Files: `tower.glb` {entry['bytes']['F1'] / 1e6:.2f} MB, `tower_f2.glb` {entry['bytes']['F2'] / 1e6:.2f} MB, "
              f"`tower_lod2.glb` {entry['bytes']['F1_lod2_only'] / 1e6:.2f} MB (PNG textures; KTX2 / meshopt later with "
              '`tools/engine/glb_compress.mjs`). Materials are PBR constants (our choices for the published "SFO Silver" ACM, glass, '
              'panels; `extras.src` on every material); detail normal tiles on TEXCOORD_0 (`tools/blender/tower_tex.py`: panel joints, '
              'louvres, base-building panels, mip-mapped: no moire); sun-independent AO baked by Cycles (48 samples, 8 m rays, ground '
              'plane as occluder). Glass of the cab is alpha-blended and double-sided; every other surface is single-sided and wound '
              'outwards (back-face audit renders: 0 back-face pixels in 6 views per LOD).', '',
              '**Verification** (`out/buildings3d/tower_verify.json`, measured on the exported GLB against the sheet functions):',
              f"- F1: {v1['summary']}", f"- F2: {ver[2]['summary']}" if 2 in ver else '',
              f"- largest deviation of a length: {entry['verification']['max_abs_dev_m']:.3f} m (tolerance 0.5 m / 2 %); "
              f"{len(fails)} failures.",
              '- Khronos glTF-Validator ' + '; '.join(f"{k}: {g.get('errors')} errors, {g.get('warnings')} warnings, {g.get('infos')} infos "
                                                     f"({', '.join(g.get('codes', {}))})" for k, g in entry['verification']['gltf_validator'].items() if g),
              f"- plausibility: {v1['plausibility']['verdict']}; nearest aircraft envelope {v1['plausibility']['nearest_aircraft_envelope_m']} m "
              f"({v1['plausibility']['nearest_aircraft_stand']}), bridge {v1['plausibility']['nearest_bridge_m']} m, taxiway centreline "
              f"{v1['plausibility']['nearest_taxi_centreline_m']} m.", '',
              '**Integration (for the app owner).** Parts of the app\'s `data/sfo_buildings.json` overlap the asset below 20 m: '
              + '; '.join(f"\"{o['part']}\" ({o['kind']}, {o['h']} m) {o['overlap_m2']} m2" for o in v1['plausibility'].get('app_parts_over_footprint') or [])
              + '. The base building would be swallowed by the T2 hall box. Cut the footprint (`manifest.json#tower.integration.'
              'exclusion_footprint_world`) out of those parts, replace `buildTower()`, and put the tower camera at `anchors.cab_eye_h` '
              '(the app uses GROUND_Y + 62).', '',
              '**Renders** (Cycles CPU, 64 samples + OIDN, AgX; ours): `out/buildings3d/tower_A.png`, `tower_B.png` (the BT-02 '
              'elevations, orthographic; `tower_overlay_A/B.png` carry the sheet outlines in red), `tower_t2.png`, `tower_t3.png`, '
              '`tower_t4.png` (camera-matched to the reference photos t2 / t3 / t4, Famartin 2025, CC BY-SA 4.0; side-by-side '
              'comparisons `tower_compare_*.jpg` stay local).', '',
              '**Observed vs inferred.** Per dimension in `manifest.json#tower.dimensions`; lists `inferred`, `unknown`, '
              '`not_modelled`, `conflicts` there. Node extras carry `src`, the spec keys and per-feature tags.', '',
              '**Open (for the owner).**',
              '- The height family (F1 / F2).',
              '- NE blade tip: drawn at deck + 1.2 (61.7 m F1, obs low). In the t3 / t4 comparisons the model\'s tip stands ~2-3 m '
              'higher than the photographed tip (perspective-corrected estimate from t3: the prow top is near the flare corner, '
              '~58-59 m). Not changed: the sheet is the reference.',
              '- t2 camera match: with the rim registered, the base-building parapet renders ~90 px (~2.9 m) higher than in the photo; '
              'the camera height (11.5 m) and focal length are estimates (no EXIF here), so this is a camera-model check only, but '
              'the parapet / roof station (rim - 3.46 D - 0.7) comes from the same photo.',
              '- Slot 345.5 deg: its top corner falls on the NE blade root; clipped 0.3 m clear of the crease (the sheet lets the '
              'blade cover it).',
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
    fam = int(sys.argv[2]) if len(sys.argv) > 2 else (2 if glb.endswith('_f2.glb') else 1)
    v = verify(glb, fam)
    for c in v['checks']:
        print(('  ok ' if c['ok'] else 'FAIL '), f"{c['item']:<58} model {c['model']:>9} drawing {c['drawing']:>9} dev {c['dev']:>+7} "
              f"tol {c['tol']} {c['unit']} [{c['tag']}] {c['note']}")
    print(v['summary']); print(json.dumps(v['plausibility'], indent=1))
