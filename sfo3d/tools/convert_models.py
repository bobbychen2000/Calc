#!/usr/bin/env python3
"""Convert open-source airliner models (glTF .glb from FlightAirMap-3dmodels, AC3D .ac from FlightGear)
into a compact runtime format for SFO Live.

Output per model: data/models/<key>.sfom  (gzip of: b'SFOM' + u32 version + u32 jsonLen + json + pad + blob)
The runtime (js/live/models.js) decodes it. tools/liveries/atlas.py then adds the livery atlas (texture 0: one uniform
layout for the fuselage, fin, nacelles, ... that every brand livery of data/liveries/ is baked into).

Normalised frame: x = forward (toward nose), y = up, z = right (starboard). Metres.
Origin: x = main-gear centre, y = ground (lowest wheel), z = fuselage centreline.
"""
import json, struct, os, sys, io, gzip, math, re
import numpy as np
from PIL import Image, ImageFilter

OUT = os.environ.get('SFOM_OUT', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'models'))
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- glTF loading
COMP = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NCOMP = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


def load_glb(path):
    b = open(path, 'rb').read()
    l0, _ = struct.unpack('<II', b[12:20])
    js = json.loads(b[20:20 + l0])
    off = 20 + l0
    l1, _ = struct.unpack('<II', b[off:off + 8])
    return js, b[off + 8:off + 8 + l1]


def accessor(js, blob, i):
    a = js['accessors'][i]
    bv = js['bufferViews'][a['bufferView']]
    dt = COMP[a['componentType']]
    n = NCOMP[a['type']]
    isz = np.dtype(dt).itemsize
    off = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    stride = bv.get('byteStride', 0) or isz * n
    cnt = a['count']
    arr = np.ndarray((cnt, n), dtype=dt, buffer=blob, offset=off, strides=(stride, isz)).copy()
    if a.get('normalized'):
        if dt == np.uint8: arr = arr.astype(np.float32) / 255
        elif dt == np.uint16: arr = arr.astype(np.float32) / 65535
        elif dt == np.int8: arr = np.maximum(arr.astype(np.float32) / 127, -1)
        elif dt == np.int16: arr = np.maximum(arr.astype(np.float32) / 32767, -1)
    return arr


def node_local(n):
    if 'matrix' in n:
        return np.array(n['matrix'], dtype=np.float64).reshape(4, 4).T
    T = np.eye(4); T[:3, 3] = n.get('translation', [0, 0, 0])
    x, y, z, w = n.get('rotation', [0, 0, 0, 1])
    R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    M = np.eye(4); M[:3, :3] = R @ np.diag(n.get('scale', [1, 1, 1]))
    return T @ M


def glb_primitives(path):
    """Return list of prims: dict(pos, nrm, uv, idx, mat, node) in source (glTF) space, plus materials/images."""
    js, blob = load_glb(path)
    nodes = js.get('nodes', [])
    parent = {}
    for i, n in enumerate(nodes):
        for c in n.get('children', []): parent[c] = i

    def world(i):
        M = node_local(nodes[i])
        while i in parent:
            i = parent[i]; M = node_local(nodes[i]) @ M
        return M
    prims = []
    for i, n in enumerate(nodes):
        if 'mesh' not in n: continue
        M = world(i); N = np.linalg.inv(M[:3, :3]).T
        for p in js['meshes'][n['mesh']]['primitives']:
            if p.get('mode', 4) != 4: continue
            at = p['attributes']
            pos = accessor(js, blob, at['POSITION']).astype(np.float64)
            pos = (M[:3, :3] @ pos.T).T + M[:3, 3]
            if 'NORMAL' in at:
                nrm = (N @ accessor(js, blob, at['NORMAL']).astype(np.float64).T).T
                nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)
            else:
                nrm = None
            uv = accessor(js, blob, at['TEXCOORD_0']).astype(np.float64) if 'TEXCOORD_0' in at else np.zeros((len(pos), 2))
            idx = accessor(js, blob, p['indices']).reshape(-1).astype(np.int64) if 'indices' in p else np.arange(len(pos))
            if np.linalg.det(M[:3, :3]) < 0:  # mirrored node: flip winding
                idx = idx.reshape(-1, 3)[:, ::-1].reshape(-1)
            prims.append(dict(pos=pos, nrm=nrm, uv=uv, idx=idx, mat=p.get('material', -1), node=n.get('name', '') + '|' + js['meshes'][n['mesh']].get('name', '')))
    mats = []
    for m in js.get('materials', []):
        pbr = m.get('pbrMetallicRoughness', {})
        tex = pbr.get('baseColorTexture', {}).get('index', -1)
        mats.append(dict(name=m.get('name', ''), color=pbr.get('baseColorFactor', [1, 1, 1, 1]), tex=tex,
                         metal=pbr.get('metallicFactor', 1.0), rough=pbr.get('roughnessFactor', 1.0),
                         alphaMode=m.get('alphaMode', 'OPAQUE'), doubleSided=m.get('doubleSided', False)))
    images = []
    for im in js.get('images', []):
        bv = js['bufferViews'][im['bufferView']]
        data = blob[bv.get('byteOffset', 0):bv.get('byteOffset', 0) + bv['byteLength']]
        images.append(dict(name=im.get('name') or 'img', data=data))
    textures = [dict(image=t.get('source', -1)) for t in js.get('textures', [])]
    return prims, mats, images, textures


# ---------------------------------------------------------------- classification helpers
GLASS_RE = re.compile(r'glass|windshield|windscreen|cockpit\.?windows|cockpitwindows|screen', re.I)
GEAR_RE = re.compile(r'gear|wheel|tire|tyre|strut|oleo|axle|brake|bogie|NLG|FLG|MLG|eixo|torque|scissor', re.I)
DOOR_RE = re.compile(r'door', re.I)
ENG_RE = re.compile(r'engine|eng[12]|nacelle|cowl|casing|reverser|revers|intake|inlet|fan|spinner|blades|cone|exhaust|nozzle|turbofan|shroud|bypass|stage1|FanCasing|iCone|no[12]eng', re.I)
PYLON_RE = re.compile(r'pylon', re.I)
FIN_RE = re.compile(r'^(fin|vstab|vertical|rudder|tail\.?fin)|\|(fin|vstab)', re.I)
LIGHT_RE = re.compile(r'light|lamp|beacon|strobe|lens|navlit|landlt|lenz', re.I)
INTERIOR_RE = re.compile(r'interior|int$|\.in$|carpet|seat|cabin(?!.?windows)|stairs|well|cargo.?int|doorint|pilot', re.I)

ZONE = dict(base=0, fin=1, engine=2, gear=3, gdoor=4, glass=5, light=6, pylon=7, interior=8)


def srgb_to_lin(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


# ---------------------------------------------------------------- texture processing
def neutralize(img, strength=1.0, keep_dark=True):
    """Replace saturated livery paint (and text/logos enclosed by it) with flat white. Returns RGB image, alpha."""
    from scipy import ndimage
    a = np.asarray(img.convert('RGBA')).astype(np.float32) / 255
    rgb = a[..., :3]
    mx = rgb.max(-1); mn = rgb.min(-1)
    sat = np.where(mx > 1e-3, (mx - mn) / np.maximum(mx, 1e-3), 0)
    paint = (sat > 0.16) & (mx > 0.08)
    # close small gaps (white/dark lettering inside painted areas) and grow over anti-aliased edges
    H, W = paint.shape; r = max(2, int(round(min(H, W) / 180)))
    st = np.ones((2 * r + 1, 2 * r + 1), bool)
    closed = ndimage.binary_closing(paint, structure=st, iterations=2)
    filled = ndimage.binary_fill_holes(closed)
    # only fill holes that are small (lettering), not whole fuselage panels enclosed by a cheatline
    holes = filled & ~closed
    lab, n = ndimage.label(holes)
    if n:
        sizes = ndimage.sum(holes, lab, index=np.arange(1, n + 1))
        big = np.isin(lab, np.where(sizes > (H * W) * 0.004)[0] + 1)
        filled = filled & ~big
    mask = ndimage.binary_dilation(filled, structure=np.ones((3, 3), bool), iterations=max(1, r // 2))
    m = ndimage.gaussian_filter(mask.astype(np.float32), 0.8)[..., None] * strength
    lum = rgb @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    # white level of the unpainted skin
    skin = lum[~mask & (sat < 0.1) & (lum > 0.45)]
    wl = float(np.percentile(skin, 75)) if skin.size > 100 else 0.93
    white = np.full(3, wl, np.float32)
    out = rgb * (1 - m) + white * m
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8), 'RGB'), a[..., 3]


def white_level(img_rgb):
    a = np.asarray(img_rgb).astype(np.float32) / 255
    mx = a.max(-1); mn = a.min(-1); sat = np.where(mx > 1e-3, (mx - mn) / np.maximum(mx, 1e-3), 0)
    lum = a @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    sel = lum[(sat < 0.12) & (lum > 0.3)]
    return float(np.percentile(sel, 80)) if sel.size > 200 else 0.9


def encode_texture(img_rgb, alpha, max_size, has_alpha):
    w, h = img_rgb.size
    s = min(1.0, max_size / max(w, h))
    if s < 1:
        img_rgb = img_rgb.resize((max(4, int(w * s)), max(4, int(h * s))), Image.LANCZOS)
    buf = io.BytesIO()
    if has_alpha:
        A = Image.fromarray((alpha * 255).astype(np.uint8)).resize(img_rgb.size, Image.LANCZOS)
        im = img_rgb.convert('RGBA'); im.putalpha(A)
        im.save(buf, 'PNG', optimize=True)
        return buf.getvalue(), 'png', im.size
    img_rgb.save(buf, 'JPEG', quality=86, optimize=True, progressive=False)
    return buf.getvalue(), 'jpg', img_rgb.size


# ---------------------------------------------------------------- main conversion
def convert(key, prims, mats, images, textures, cfg):
    # ---- merge & orient
    allp = np.concatenate([p['pos'] for p in prims])
    lo, hi = allp.min(0), allp.max(0)
    top = allp[np.argmax(allp[:, 1])]
    fx = (top[0] - lo[0]) / max(hi[0] - lo[0], 1e-6)
    fz = (top[2] - lo[2]) / max(hi[2] - lo[2], 1e-6)
    if cfg.get('axis'):
        axis, tail_pos = cfg['axis']
    else:
        axis = 0 if abs(fx - 0.5) > abs(fz - 0.5) else 2
        tail_pos = (fx if axis == 0 else fz) > 0.5
    fwd = np.zeros(3); fwd[axis] = -1.0 if tail_pos else 1.0
    up = np.array([0, 1.0, 0])
    right = np.cross(fwd, up)
    R = np.stack([fwd, up, right])  # rows: new axes in old coords

    def tf(p): return p @ R.T
    for p in prims:
        p['pos'] = tf(p['pos'])
        if p['nrm'] is not None: p['nrm'] = tf(p['nrm'])
    allp = np.concatenate([p['pos'] for p in prims])
    lo, hi = allp.min(0), allp.max(0)
    L = hi[0] - lo[0]
    sc = cfg.get('length', L) / L if cfg.get('length') else 1.0
    if abs(sc - 1) > 0.03:
        print(f'  scaling {key} by {sc:.4f} (model length {L:.2f} m)')
    else:
        sc = 1.0
    for p in prims: p['pos'] *= sc
    allp = np.concatenate([p['pos'] for p in prims]); lo, hi = allp.min(0), allp.max(0)
    # lateral centre from the fin (top 3% of height)
    ft = allp[allp[:, 1] > hi[1] - 0.03 * (hi[1] - lo[1])]
    zc = float(np.median(ft[:, 2]))
    Lm = hi[0] - lo[0]
    mid = (allp[:, 0] > lo[0] + 0.3 * Lm) & (allp[:, 0] < hi[0] - 0.3 * Lm)
    fwd = (allp[:, 0] < hi[0] - 0.17 * Lm) & (allp[:, 0] > hi[0] - 0.33 * Lm)
    col = allp[fwd & (np.abs(allp[:, 2] - zc) < 0.35)]
    if len(col) < 40 or (np.percentile(col[:, 1], 99.5) - np.percentile(col[:, 1], 0.5)) < 1.0:
        col = allp[fwd & (np.abs(allp[:, 2] - zc) < 1.0)]
    crown = float(np.percentile(col[:, 1], 99.5)); belly = float(np.percentile(col[:, 1], 0.5))
    cy = (crown + belly) / 2; Rf = (crown - belly) / 2
    near = allp[(np.abs(allp[:, 2] - zc) < 0.6) & (np.abs(allp[:, 1] - cy) < Rf)]
    noseX = float(near[:, 0].max())
    slab = allp[mid & (np.abs(allp[:, 1] - cy) < 0.3 * Rf) & (np.abs(allp[:, 2] - zc) < 1.35 * Rf)]
    Rz = float(np.percentile(np.abs(slab[:, 2] - zc), 97)) if len(slab) else Rf
    shift = np.array([noseX, cy, zc])
    for p in prims: p['pos'] = p['pos'] - shift
    allp = np.concatenate([p['pos'] for p in prims]); lo, hi = allp.min(0), allp.max(0)
    tailX = float(lo[0])
    crown -= cy; belly -= cy
    dims = dict(L=float(-tailX), span=float(hi[2] - lo[2]), H=float(hi[1]), low=float(lo[1]), noseX=0.0, tailX=tailX,
                R=Rf, Rz=Rz, crown=crown, belly=belly, hasGear=bool(cfg.get('hasGear')))
    print(f'  {key}: L={dims["L"]:.2f} span={dims["span"]:.2f} finTop={dims["H"]:.2f} low={dims["low"]:.2f} R={Rf:.2f} Rz={Rz:.2f}')
    # ---- per-primitive classification
    out_prims = []
    for p in prims:
        m = mats[p['mat']] if 0 <= p['mat'] < len(mats) else dict(name='', color=[0.8, 0.8, 0.8, 1], tex=-1, metal=0, rough=0.5, alphaMode='OPAQUE')
        name = p['node']; mname = m['name']
        zone = 'base'
        alpha = m['color'][3] if len(m['color']) > 3 else 1
        if INTERIOR_RE.search(name.split('|')[0]):
            zone = 'interior'
        elif GLASS_RE.search(name) or GLASS_RE.search(mname) or re.search(r'window', name + ' ' + mname, re.I) or (alpha < 0.8 and m['alphaMode'] == 'BLEND'):
            zone = 'glass'
        elif DOOR_RE.search(name) and GEAR_RE.search(name):
            zone = 'gdoor'
        elif (GEAR_RE.search(name) or (cfg.get('gearRe') and re.search(cfg['gearRe'], name))) and cfg.get('hasGear'):
            zone = 'gear'
        elif PYLON_RE.search(name):
            zone = 'pylon'
        elif ENG_RE.search(name):
            zone = 'engine'
        elif FIN_RE.search(name):
            zone = 'fin'
        elif LIGHT_RE.search(name) or LIGHT_RE.search(mname):
            zone = 'light'
        for rx, z in cfg.get('zoneOverride', []):
            if re.search(rx, name): zone = z
        p['zone'] = zone; p['m'] = m
        out_prims.append(p)
    # drop interior
    prims = [p for p in out_prims if p['zone'] != 'interior' or cfg.get('keepInterior')]

    # ---- geometric per-triangle refinement for merged meshes: fin & gear
    verts = []; tris = []
    base = 0
    for p in prims:
        n = len(p['pos'])
        if p['nrm'] is None:
            p['nrm'] = compute_normals(p['pos'], p['idx'])
        p['base'] = base; base += n
    P = np.concatenate([p['pos'] for p in prims])
    Nn = np.concatenate([p['nrm'] for p in prims])
    UV = np.concatenate([p['uv'] for p in prims])
    Z = np.concatenate([np.full(len(p['pos']), ZONE[p['zone']], np.uint8) for p in prims])
    # geometric fin: above crown+0.35, near centreline, aft 45%
    geo_fin = (P[:, 1] > crown + 0.35) & (np.abs(P[:, 2]) < 0.9) & (P[:, 0] < tailX * 0.55)
    Z = np.where((Z == 0) & geo_fin, ZONE['fin'], Z)

    # ---- materials / draw batching: key = (material index, zone)
    mat_slots = {}; slot_list = []
    tri_slot = []; tri_idx = []
    for p in prims:
        m = p['m']
        t = p['idx'].reshape(-1, 3) + p['base']
        # per-triangle zone = zone of first vertex (majority)
        zt = Z[t[:, 0]]
        for zval in np.unique(zt):
            sel = t[zt == zval]
            k = (id(m), int(zval))
            if k not in mat_slots:
                mat_slots[k] = len(slot_list)
                slot_list.append(dict(m=m, zone=int(zval)))
            tri_slot.append(np.full(len(sel), mat_slots[k])); tri_idx.append(sel)
    tri_slot = np.concatenate(tri_slot); tri_idx = np.concatenate(tri_idx)
    order = np.argsort(tri_slot, kind='stable')
    tri_slot = tri_slot[order]; tri_idx = tri_idx[order]
    # remove degenerate
    ok = (tri_idx[:, 0] != tri_idx[:, 1]) & (tri_idx[:, 1] != tri_idx[:, 2]) & (tri_idx[:, 0] != tri_idx[:, 2])
    tri_slot = tri_slot[ok]; tri_idx = tri_idx[ok]
    # compact vertices
    used = np.unique(tri_idx)
    remap = -np.ones(len(P), np.int64); remap[used] = np.arange(len(used))
    P = P[used]; Nn = Nn[used]; UV = UV[used]; Z = Z[used]; tri_idx = remap[tri_idx]
    # ---- textures
    tex_out = []; tex_map = {}
    def tex_for(tindex, neutral):
        if tindex < 0 or tindex >= len(textures): return -1
        im_i = textures[tindex]['image']
        if im_i < 0: return -1
        k = (im_i, neutral)
        if k in tex_map: return tex_map[k]
        im = Image.open(io.BytesIO(images[im_i]['data']))
        rgba = im.convert('RGBA')
        if neutral:
            rgb, alpha = neutralize(rgba, strength=cfg.get('neutralStrength', 1.0))
        else:
            arr = np.asarray(rgba).astype(np.float32) / 255
            rgb = rgba.convert('RGB'); alpha = arr[..., 3]
        for (x0, y0, x1, y1) in cfg.get('erase', {}).get(images[im_i]['name'], []):
            W, H = rgb.size
            box = (int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H))
            reg = rgb.crop(box).filter(ImageFilter.GaussianBlur(25))
            fill = Image.new('RGB', reg.size, (236, 237, 238))
            rgb.paste(Image.blend(reg, fill, 0.85), box)
        has_alpha = bool((alpha < 0.5).mean() > 0.002) and cfg.get('alphaTest', True)
        wl = white_level(rgb)
        data, fmt, size = encode_texture(rgb, alpha, cfg.get('texSize', 1024), has_alpha)
        tex_map[k] = len(tex_out)
        tex_out.append(dict(name=images[im_i]['name'], fmt=fmt, w=size[0], h=size[1], data=data, alpha=has_alpha, white=wl))
        return tex_map[k]
    mats_out = []; draws = []
    for si, s in enumerate(slot_list):
        m = s['m']; zone = s['zone']
        col = list(m['color'][:3]); name = m['name'].lower()
        kind = 'paint'
        if zone == ZONE['glass']: kind = 'glass'
        elif zone == ZONE['light']: kind = 'light'
        elif re.search(r'chrome|alumin|metal|silver|nozzle|exhaust', name): kind = 'metal'
        elif re.search(r'black|rubber|tire|tyre|charcoa', name) or max(col) < 0.12: kind = 'dark'
        neutral = zone in (ZONE['base'], ZONE['fin'], ZONE['engine'], ZONE['gdoor']) and cfg.get('neutral', True)
        ti = tex_for(m['tex'], neutral) if kind != 'glass' else -1
        rough = float(min(max(m.get('rough', 0.5), 0.15), 0.9)) if 'rough' in m else 0.5
        tw = tex_out[ti]['white'] if ti >= 0 else max(max(col), 0.05)
        mats_out.append(dict(kind=kind, zone=zone, tex=ti, white=tw, color=[float(c) for c in col], rough=0.35 if kind == 'paint' else (0.25 if kind == 'metal' else rough),
                             metal=1.0 if kind == 'metal' else 0.0, alphaTest=bool(ti >= 0 and tex_out[ti]['alpha'])))
    for si in range(len(slot_list)):
        sel = np.where(tri_slot == si)[0]
        if len(sel) == 0: continue
        draws.append(dict(mat=si, first=int(sel[0] * 3), count=int(len(sel) * 3), zone=slot_list[si]['zone']))
    # ---- UVs: bring every triangle's UVs next to [0, 1) by an integer shift (the texture wraps, so this changes nothing
    # on screen) and give untextured vertices a neutral UV. Without this a few tiled or garbage UVs (e.g. +-1500 on the
    # 747-400, 767 and A220-100 sources) stretch the u16 quantisation range until every other UV loses its precision.
    tex_of_slot = np.array([mats_out[si]['tex'] for si in range(len(slot_list))])
    tri_tex = tex_of_slot[tri_slot]
    P, Nn, UV, Z, tri_idx = normalize_uvs(P, Nn, UV, Z, tri_idx, tri_tex, [mean_texel(t) for t in tex_out])
    # ---- quantize & pack
    plo, phi = P.min(0), P.max(0)
    pscale = (phi - plo) / 65535.0
    pq = np.round((P - plo) / np.maximum(pscale, 1e-9)).astype(np.uint16)
    nq = np.round(np.clip(Nn, -1, 1) * 127).astype(np.int8)
    ulo, uhi = UV.min(0), UV.max(0)
    uscale = np.maximum(uhi - ulo, 1e-6) / 65535.0
    uq = np.round((UV - ulo) / uscale).astype(np.uint16)
    idx32 = tri_idx.reshape(-1)
    idx_type = 'u16' if len(P) < 65536 else 'u32'
    ib = idx32.astype(np.uint16 if idx_type == 'u16' else np.uint32)
    blob = io.BytesIO()
    def put(arr):
        off = blob.tell(); blob.write(arr.tobytes())
        while blob.tell() % 4: blob.write(b'\0')
        return off
    offs = dict(pos=put(pq), nrm=put(np.concatenate([nq, np.zeros((len(nq), 1), np.int8)], 1)), uv=put(uq), zone=put(Z.astype(np.uint8)), idx=put(ib))
    for t in tex_out:
        t['offset'] = blob.tell(); blob.write(t['data']); t['length'] = len(t['data'])
        while blob.tell() % 4: blob.write(b'\0')
        del t['data']
    head = dict(key=key, name=cfg.get('name', key), source=cfg.get('source', ''), license=cfg.get('license', 'GPL-2.0-or-later'),
                dims=dims, nv=int(len(P)), ni=int(len(ib)), idxType=idx_type, offsets=offs,
                quant=dict(pmin=plo.tolist(), pscale=pscale.tolist(), umin=ulo.tolist(), uscale=uscale.tolist()),
                mats=mats_out, draws=draws, textures=tex_out, zones=ZONE)
    hj = json.dumps(head, separators=(',', ':')).encode()
    while len(hj) % 4: hj += b' '
    raw = b'SFOM' + struct.pack('<II', 1, len(hj)) + hj + blob.getvalue()
    gz = gzip.compress(raw, 9)
    open(os.path.join(OUT, key + '.sfom'), 'wb').write(gz)
    ntri = len(ib) // 3
    print(f'  -> {key}.sfom  verts {len(P)} tris {ntri} draws {len(draws)} textures {len(tex_out)} raw {len(raw)/1e6:.2f} MB gz {len(gz)/1e6:.2f} MB')
    return head


def mean_texel(t):
    """UV of the texel whose colour is closest to the texture's mean colour (what a triangle with garbage UVs, spanning
    hundreds of texture repeats, shows through the smallest mip level)"""
    im = np.asarray(Image.open(io.BytesIO(t['data'])).convert('RGB').resize((64, 64), Image.BOX), float)
    d = np.abs(im - im.reshape(-1, 3).mean(0)).sum(-1); y, x = np.unravel_index(np.argmin(d), d.shape)
    return ((x + 0.5) / 64, (y + 0.5) / 64)


def normalize_uvs(P, N, UV, Z, tri, tri_tex, flat_uv, max_spread=4.0):
    """per triangle: shift its UVs by the integer part of their centroid (duplicating vertices shared by triangles that
    need different shifts); untextured triangles get UV 0.5; textured triangles whose UVs span more than `max_spread`
    texture repeats (garbage UVs in the source: 747-400 misc / fin, 767 wing and fuselage strips, A220-100 chrome) get
    the constant UV flat_uv[tex] (the mean colour they show on screen through the mip chain)"""
    UV = UV.copy()
    tu = UV[tri]
    bad = (tri_tex >= 0) & ((tu.max(1) - tu.min(1)).max(1) > max_spread)
    shift = np.where(tri_tex[:, None] >= 0, np.floor(tu.mean(1)), 0.0)            # (nt, 2)
    shift[bad] = 0
    notex = tri_tex < 0
    newP, newN, newUV, newZ = [P], [N], [UV], [Z]
    key = {}; tri = tri.copy(); nv = len(P)
    for t in np.where((np.abs(shift).sum(1) > 0) | notex | bad)[0]:
        for k in range(3):
            v = tri[t, k]
            if notex[t]: kk = (v, 'n'); uv = np.array([[0.5, 0.5]])
            elif bad[t]: kk = (v, 'f', int(tri_tex[t])); uv = np.array([flat_uv[tri_tex[t]]])
            else: kk = (v, shift[t, 0], shift[t, 1]); uv = UV[v:v + 1] - shift[t]
            if kk not in key:
                key[kk] = nv; nv += 1
                newP.append(P[v:v + 1]); newN.append(N[v:v + 1]); newZ.append(Z[v:v + 1]); newUV.append(uv)
            tri[t, k] = key[kk]
    if bad.any(): print(f'  UVs: {int(bad.sum())} triangles with garbage UVs (> {max_spread:g} repeats) flattened to the mean texel')
    P = np.concatenate(newP); N = np.concatenate(newN); UV = np.concatenate(newUV); Z = np.concatenate(newZ)
    used = np.unique(tri); rm = -np.ones(len(P), np.int64); rm[used] = np.arange(len(used))
    return P[used], N[used], UV[used], Z[used], rm[tri]


def compute_normals(pos, idx):
    t = idx.reshape(-1, 3)
    n = np.zeros_like(pos)
    fn = np.cross(pos[t[:, 1]] - pos[t[:, 0]], pos[t[:, 2]] - pos[t[:, 0]])
    for k in range(3): np.add.at(n, t[:, k], fn)
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)


def ac_model(files, skip=None):
    """Assemble one or more AC3D files (same frame) into glb-like prims/mats/images/textures."""
    sys.path.insert(0, os.path.dirname(__file__))
    from ac3d import ac_primitives
    prims = []; mats = []; images = []; textures = []; mkey = {}; tkey = {}
    for f in files:
        off = (0, 0, 0)
        if isinstance(f, tuple): f, off = f
        pr, am = ac_primitives(f, offset=off, skip=skip)
        for p in pr:
            _, path, mi, tex = p['mat']
            k = (path, mi, tex)
            if k not in mkey:
                ti = -1
                if tex:
                    tp = os.path.join(os.path.dirname(path), tex)
                    if tp not in tkey and os.path.exists(tp):
                        images.append(dict(name=os.path.basename(tp), data=open(tp, 'rb').read()))
                        textures.append(dict(image=len(images) - 1)); tkey[tp] = len(textures) - 1
                    ti = tkey.get(tp, -1)
                m = am[mi] if mi < len(am) else dict(name='?', rgb=[0.8, 0.8, 0.8], trans=0)
                a = 1 - m['trans']
                mats.append(dict(name=m['name'], color=m['rgb'] + [a], tex=ti, metal=0.0, rough=0.5, alphaMode='BLEND' if a < 0.99 else 'OPAQUE'))
                mkey[k] = len(mats) - 1
            p['mat'] = mkey[k]
            prims.append(p)
    return prims, mats, images, textures


REFS = os.environ.get('SFO_REFS', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'refs'))
FAM = os.environ.get('FAM_DIR', os.path.join(REFS, 'fam3d'))            # github.com/Ysurac/FlightAirMap-3dmodels @0906d9b
FG738 = os.environ.get('FG738_DIR', os.path.join(REFS, 'fg_737-800', 'Models'))  # github.com/FGMEMBERS/737-800 @9126249
# github.com/FGMEMBERS/777 @371a354 (FlightGear 777 series; GPL-2.0: LICENSE in the FGAddon original,
# svn trunk/Aircraft/777/LICENSE r19240, https://sourceforge.net/p/flightgear/fgaddon/HEAD/tree/trunk/Aircraft/777/LICENSE).
# The clone is blob-less; the model files are exported with `git show HEAD:Models/<file>` into <dir>/Models.
FG777 = os.environ.get('FG777_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'refs', 'cache', 'src', 'fg', '777_export', 'Models'))
# FG 777 objects that are not airframe: volumetric light cones / flares, cabin light, ILS antennas, wipers
FG777_SKIP = r'^(LandingLights|.*\.spot$|.*\.flare$|cabinlighting|.*flash$|whiteflash|redlight|taxiL-o|Llight0|[LR]ils$|[LR]wiper$|hinge\d)'
FG777_GEAR = r'^(Frt|[LR]gear|[LR]strut|[LR]axle|[LR]brake|[LR]H?wheel|RHwheel|LHwheel|[LR]lbrace|[LR]lockbrace|[LR][UB](support|damper)|F[UL]damper|[LR]gear\.tubing|Wheaters)'

MODELS = {
    # key: (source file, config)
    'a319': (f'{FAM}/a320/glTF2/A319.glb', dict(name='Airbus A319', length=33.84)),
    'a320': (f'{FAM}/a320/glTF2/A320.glb', dict(name='Airbus A320', length=37.57)),
    'a321': (f'{FAM}/a320/glTF2/A321.glb', dict(name='Airbus A321', length=44.51)),
    'a333': (f'{FAM}/a333/glTF2/A333.glb', dict(name='Airbus A330-300', length=63.66)),
    'a359': (f'{FAM}/a350/glTF2/A350.glb', dict(name='Airbus A350-900', length=66.8)),
    'a388': (f'{FAM}/a380/glTF2/A380.glb', dict(name='Airbus A380-800', length=72.72)),
    'b744': (f'{FAM}/b744/glTF2/B747.glb', dict(name='Boeing 747-400', length=70.66)),
    'b748': (f'{FAM}/b748/glTF2/B748.glb', dict(name='Boeing 747-8', length=76.25)),
    'b752': (f'{FAM}/b752/glTF2/B752.glb', dict(name='Boeing 757-200', length=47.32)),
    'b763': (f'{FAM}/b767/glTF2/B763.glb', dict(name='Boeing 767-300', length=54.94)),
    'b788': (f'{FAM}/b788/glTF2/B788.glb', dict(name='Boeing 787-8', length=56.72)),
    'bcs1': (f'{FAM}/bcs1/glTF2/BCS1.glb', dict(name='Airbus A220-100', length=35.0)),
    'bcs3': (f'{FAM}/bcs1/glTF2/BCS3.glb', dict(name='Airbus A220-300', length=38.7)),
    'crj2': (f'{FAM}/crj2/glTF2/CRJ2.glb', dict(name='Bombardier CRJ200', length=26.77)),
    'crj7': (f'{FAM}/crj9/glTF2/CRJ7.glb', dict(name='Bombardier CRJ700', length=32.3)),
    'crj9': (f'{FAM}/crj9/glTF2/CRJ9.glb', dict(name='Bombardier CRJ900', length=36.2)),
    'e170': (f'{FAM}/e190/glTF2/E170.glb', dict(name='Embraer E170', length=29.9)),
    'e75l': (f'{FAM}/e190/glTF2/E75L.glb', dict(name='Embraer E175', length=31.68)),
    'e190': (f'{FAM}/e190/glTF2/E190.glb', dict(name='Embraer E190', length=36.24)),
    'md11': (f'{FAM}/md11/glTF2/MD11.glb', dict(name='McDonnell Douglas MD-11', length=61.6)),
}

AC_MODELS = {
    'b738': ([f'{FG738}/737-800.ac', f'{FG738}/LWing.ac', f'{FG738}/RWing.ac', f'{FG738}/HorzStab.ac', f'{FG738}/VertStab.ac', f'{FG738}/winglet.ac', f'{FG738}/nosegear.ac'],
             dict(name='Boeing 737-800', length=39.47, hasGear=True, skip=r'^a-light|^Circle\\.006$', gearRe=r'^(mg|ng[rtw]|mglh|mgrh|collar|.*steercyl|nlink|nlower|nouter|noseaxle|.*dragstrut|sidestrut|mgouter)', source='FGMEMBERS/737-800 (FlightGear)')),
    # Boeing 777-300ER and 777-200ER (FlightGear 777 series, see FG777 above): full airframe incl. gear
    # (the default paint1 textures carry an old JAL (-300) / British Airways (-200) livery: its titles, tail art, blue belly
    # and nacelles are erased before neutralising, boxes as fractions of the texture measured on the 2048 px images)
    'b77w': ([f'{FG777}/777-300ER.ac'], dict(name='Boeing 777-300ER', length=73.86, hasGear=True, skip=FG777_SKIP, gearRe=FG777_GEAR, source='FGMEMBERS/777 @371a354 (FlightGear, GPL-2.0) 777-300ER.ac', license='GPL-2.0',
             erase={'paint1.png': [(0.125, 0.16, 0.215, 0.222), (0.26, 0.165, 0.43, 0.2), (0.58, 0.41, 0.76, 0.44), (0.80, 0.41, 0.90, 0.462),
                                   (0.87, 0.03, 1.0, 0.17), (0.0, 0.265, 0.135, 0.415)]})),
    'b772': ([f'{FG777}/777-200ER.ac'], dict(name='Boeing 777-200ER', length=63.73, hasGear=True, skip=FG777_SKIP, gearRe=FG777_GEAR, source='FGMEMBERS/777 @371a354 (FlightGear, GPL-2.0) 777-200ER.ac', license='GPL-2.0',
             erase={'paint1.png': [(0.08, 0.175, 0.2, 0.21), (0.14, 0.2, 0.34, 0.226), (0.0, 0.224, 0.87, 0.266), (0.32, 0.255, 0.64, 0.34), (0.25, 0.0, 0.66, 0.14),
                                   (0.83, 0.02, 1.0, 0.21), (0.67, 0.445, 0.88, 0.476), (0.82, 0.42, 0.95, 0.456), (0.15, 0.47, 1.0, 0.525), (0.0, 0.26, 0.18, 0.46)]})),
}

if __name__ == '__main__':
    keys = sys.argv[1:] or (list(MODELS) + list(AC_MODELS))
    manifest = {}
    mp = os.path.join(OUT, 'manifest.json')
    if os.path.exists(mp): manifest = json.load(open(mp))
    for k in keys:
        if k in AC_MODELS:
            src, cfg = AC_MODELS[k]
            print('==', k, 'AC3D', len(src), 'files')
            prims, mats, images, textures = ac_model(src, skip=cfg.get('skip'))
        else:
            src, cfg = MODELS[k]
            print('==', k, src)
            prims, mats, images, textures = glb_primitives(src)
        cfg = dict(cfg); cfg.setdefault('source', 'FlightAirMap-3dmodels (FlightGear-derived), ' + (os.path.relpath(src, FAM) if isinstance(src, str) else ''))
        h = convert(k, prims, mats, images, textures, cfg)
        manifest[k] = dict(name=h['name'], dims=h['dims'], nv=h['nv'], ni=h['ni'], file=k + '.sfom', size=os.path.getsize(os.path.join(OUT, k + '.sfom')))
    json.dump(manifest, open(mp, 'w'), indent=1)
    # MODEL_FEATURES (doors, fuselage sections, wing tip) come from tools/models/model_features.py: re-run it after converting
    fp = os.path.join(OUT, 'features.json'); features = json.load(open(fp)) if os.path.exists(fp) else {}
    with open(os.path.join(OUT, 'manifest.js'), 'w') as f:
        f.write('// generated by tools/convert_models.py (MODEL_DIMS) and tools/models/model_features.py (MODEL_FEATURES)\n')
        f.write('export const MODEL_DIMS = ' + json.dumps({k: v['dims'] for k, v in manifest.items()}, separators=(',', ':')) + ';\n')
        f.write('export const MODEL_FEATURES = ' + json.dumps(features, separators=(',', ':')) + ';\n')
    if keys:
        print('re-run tools/models/model_features.py to refresh MODEL_FEATURES for the converted models')
        # every model carries a livery atlas as texture 0 (brand liveries are textures in that layout): rebuild it, then
        # re-bake the liveries of the converted models (tools/liveries/build.py --models ...)
        print('then: python3 tools/liveries/atlas.py ' + ' '.join(keys) + ' && python3 tools/liveries/build.py --models ' + ','.join(keys))
