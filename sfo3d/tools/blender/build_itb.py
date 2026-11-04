# SPDX-License-Identifier: GPL-3.0-or-later
# (imports bpy: Blender's licence asks scripts that use its API to be GPL-compatible if published, docs/research/engine.md 7.3)
"""Build the 3-D asset of the International Terminal (main hall, Boarding Areas A and G) with Blender (bpy 5.0, Cycles CPU):

    python3 tools/blender/build_itb.py                  # geometry, textures, AO bake, export, verification, manifest
    python3 tools/blender/build_itb.py --no-bake        # quick: no AO bake (occlusion textures white)
    python3 tools/blender/render_itb.py                 # Cycles reference renders of the exported glb (separate script)

Inputs (all in the repo, read through tools/blender/itb_geom.py):
  tools/buildings/draw_itb.py + draw_data.py + spec_itb.json + itb_pods.json   the 2-D sheets BI-01..04 (the reference)
  data/sfo_airport.json   SFO Museum outlines (ITB, Boarding Areas A / G)
  data/sfo_stands.json    bridge attach points (only to centre the pier gate-room glazing [inf])
  refs/cache/naip/naip_2024_world_0.5m_bgr.npy (optional)   roof colours sampled from NAIP 2024 (public domain); without
                          it the recorded values below are used. NAIP is never used as a texture.
Outputs:
  data/buildings3d/itb.glb              the asset (LOD0 / LOD1 / LOD2)
  data/buildings3d/manifest.json        key "itb" (merged under a file lock; other groups own their keys)
  out/buildings3d/itb_tex/*.png         textures as built (local); out/buildings3d/itb_build.json (stats)

glTF layout: root node "itb" at world (OX, GROUND_Y, OZ) = the relief-corrected roof centre (app frame: x east, y up,
z south, metres from the ARP; GROUND_Y = 3.0 per js/geo.js), children LOD0 / LOD1 / LOD2 (extras.lod, extras.switch_m),
each holding the nodes of itb_geom.build(lod). LOD0 and LOD1 share the shell meshes (one glTF mesh, two nodes) and their
baked AO atlas; LOD1 has lighter trusses / columns / hangers and no mullions or lettering; LOD2 is a coarse shell with its
own 512 px atlas. Every node carries extras {src, feature, spec (spec_itb.json keys), dims (per-dimension tags), lod}.
Materials are PBR (baseColor / metallic / roughness, coated glass IOR 1.9 -> F0 0.096 via KHR_materials_ior); tiling detail
normal maps on TEXCOORD_0 (UV_detail, metres / tile); sun-independent AO baked by Cycles on TEXCOORD_1 (UV_ao,
occlusionTexture.texCoord = 1). KTX2 / meshopt compression is a later step (tools/engine/glb_compress.mjs).
"""
import argparse
import datetime
import fcntl
import json
import math
import os
import subprocess
import sys
import time

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import itb_geom as G  # noqa: E402
import itb_tex  # noqa: E402

ROOT = G.ROOT
DATA = os.path.join(ROOT, 'data', 'buildings3d')
OUT = os.path.join(ROOT, 'out', 'buildings3d')
TEX = os.path.join(OUT, 'itb_tex')
GROUND_Y = 3.0                      # js/geo.js GROUND_Y
AO_RES = {'A': 2048, 'B': 512}      # A: LOD0 + LOD1 shells (shared meshes), B: LOD2
AO_DIST = 10.0                      # AO ray length, m (canopy / soffit / contact scale) [our choice]
T0 = time.time()

# PBR materials: sRGB base colour, metallic, roughness (+ normal tile, IOR). Colours are our reading of the reference photos
# (i1-i4, a2, d2: reference only) and of NAIP 2024 for the roofs; tags in the manifest.
MATS = {
    'roof_membrane':      dict(rgb=(218, 220, 216), m=0.0, r=0.85, nrm=('itb_n_membrane', 0.6), naip='hall',
                               src='obs NAIP 2024 roof colour (pre-2024-26 re-roofing; new membrane / PV not imaged) [obs, low]'),
    'roof_membrane_pier': dict(rgb=(200, 202, 198), m=0.0, r=0.85, nrm=('itb_n_membrane', 0.6), naip='pier',
                               src='obs NAIP 2024 pier roof colour [obs, low]'),
    'glass_roof':         dict(rgb=(70, 86, 96), m=0.0, r=0.05, ior=1.9, src='obs NAIP (glazed lines, lenses, tip bands); glass inf'),
    'glass_roof_under':   dict(rgb=(150, 172, 178), m=0.0, r=0.10, ior=1.9, src='obs photo i3 (light glazed strip in the soffit)'),
    'soffit':             dict(rgb=(84, 87, 91), m=0.30, r=0.55, nrm=('itb_n_panel', 0.5), src='obs photo i3 (dark grey soffit panels); module inf'),
    'fascia':             dict(rgb=(236, 237, 237), m=0.20, r=0.35, src='obs photos i1 / i4 (white roof edge)'),
    'steel_white':        dict(rgb=(232, 233, 230), m=0.0, r=0.40, src='obs photos i3 / i4 (white painted trusses / columns)'),
    'steel_grey':         dict(rgb=(96, 100, 105), m=0.30, r=0.50, src='obs photo i3 (dark outriggers, hangers)'),
    'glass_clear':        dict(rgb=(26, 32, 36), m=0.0, r=0.04, ior=1.9, nrm=('itb_n_curtain', 0.5), src='obs photo i4 (dark clear strip above the canopy)'),
    'glass_entrance':     dict(rgb=(34, 40, 44), m=0.0, r=0.05, ior=1.9, nrm=('itb_n_curtain', 0.5), src='obs photos i3 / i4 (clear glazing under the canopy)'),
    'glass_frit':         dict(rgb=(214, 218, 220), m=0.0, r=0.22, ior=1.9, tex='itb_c_frit', nrm=('itb_n_curtain', 0.4),
                               src='pub "three layers of ceramic frit"; white banded look obs photos i1 / i4; pattern inf'),
    'glass_hall':         dict(rgb=(118, 130, 136), m=0.0, r=0.06, ior=1.9, nrm=('itb_n_curtain', 0.5),
                               src='obs photos i1 / i4 (clear central bay reads light: the lit hall seen through); value inf'),
    'mullion':            dict(rgb=(178, 182, 186), m=0.60, r=0.40, src='inf (aluminium mullion caps)'),
    'canopy_top':         dict(rgb=(150, 152, 150), m=0.0, r=0.75, src='inf'),
    'concrete':           dict(rgb=(166, 164, 158), m=0.0, r=0.85, src='inf (curb, podium)'),
    'glass_dark':         dict(rgb=(28, 33, 38), m=0.0, r=0.06, ior=1.9, nrm=('itb_n_curtain', 0.4), tex='itb_c_curtain_dark',
                               src='inf / unk (window bands)'),
    'glass_tinted':       dict(rgb=(42, 56, 60), m=0.0, r=0.06, ior=1.9, nrm=('itb_n_curtain', 0.5), tex='itb_c_curtain_tinted',
                               src='inf (end walls, clerestory: tint unk)'),
    'alu_panel':          dict(rgb=(190, 193, 196), m=0.50, r=0.40, nrm=('itb_n_panel', 0.7),
                               src='pub BA-G "metallic-finish composite aluminium panels"; BA-A / core: same by photo a2 [inf]'),
    'alu_panel_pod':      dict(rgb=(206, 208, 209), m=0.40, r=0.45, nrm=('itb_n_panel', 0.7), src='obs photo a2 (light grey pods); finish inf'),
    'coping':             dict(rgb=(200, 202, 204), m=0.50, r=0.40, src='inf'),
    'service_dark':       dict(rgb=(78, 81, 84), m=0.10, r=0.70, nrm=('itb_n_panel', 0.4), src='obs photo a2 (dark apron level); detail unk'),
    'glass_pier':         dict(rgb=(36, 50, 52), m=0.0, r=0.05, ior=1.9, nrm=('itb_n_curtain', 0.5), tex='itb_c_curtain_pier',
                               src='pub BA-G "tinted energy-efficient glazed curtain wall"; BA-A obs photo a2; bay positions inf'),
    'lettering':          dict(rgb=(38, 42, 46), m=0.30, r=0.40, src='obs photos i1 / i3 / i4 ("SAN FRANCISCO INTERNATIONAL"); font inf'),
}


def log(*a):
    print('[itb %6.1f s]' % (time.time() - T0), *a, flush=True)


def srgb2lin(rgb):
    c = np.asarray(rgb, float) / 255.0
    return tuple(np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).tolist())


# ------------------------------------------------------------------------------------------------ NAIP roof colours
def naip_colours():
    """median NAIP 2024 sRGB of the membrane at its IMAGED position (true roof point + frame-model relief shift at its
    height; BA-G: k(x) east-only, as its spec height): hall wings between the truss lines, pier roofs off the pods."""
    sys.path.insert(0, os.path.join(ROOT, 'tools', 'buildings'))
    import draw_lib as DL
    import draw_data as DD
    from shapely.geometry import Point
    if not DL.naip_available():
        return None
    A, T = DL._naip(); R = T['res']

    def px(x, z):
        c = int(round((x - T['x0']) / R - 0.5)); r = int(round((z - T['z0']) / R - 0.5))
        b, g, rr = A[r, c]
        return (int(rr), int(g), int(b))
    out = {}
    pts = []
    for u in np.arange(-100, 101, 2.0):
        if abs(u) < 35: continue
        for k in range(4):
            v = 0.5 * (G.LINES_V[k] + G.LINES_V[k + 1]) + np.array([-3.0, 0.0, 3.0])
            for vv in v:
                x, z = G.UVw(u, vv); h = G.roof_top(u)
                s = DD.lean_frame((x, z), h)
                pts.append(px(x + s[0], z + s[1]))
    out['hall'] = dict(rgb=np.median(np.array(pts), 0).round().astype(int).tolist(), n=len(pts),
                       method='NAIP 2024 median at imaged membrane points between the truss lines, |u| 35-100 (frame-model relief)')
    pts = []
    for key, poly in (('A', G.PIER_A), ('G', G.PIER_G)):
        h = float(G.PIERS[key]['h_main_roof'])
        pods = [g for _, g in G.pod_polys(key)]
        inner = poly.buffer(-4.0)
        x0, z0, x1, z1 = inner.bounds
        for x in np.arange(x0, x1, 3.0):
            for z in np.arange(z0, z1, 3.0):
                p = Point(x, z)
                if not inner.contains(p) or any(g.buffer(4).contains(p) for g in pods): continue
                if key == 'A':
                    s = DD.lean_frame((x, z), h)
                else:
                    s = (DD.k_x_model(x) * h, 0.0)
                pts.append(px(x + s[0], z + s[1]))
    out['pier'] = dict(rgb=np.median(np.array(pts), 0).round().astype(int).tolist(), n=len(pts),
                       method='NAIP 2024 median over the BA-A / BA-G main roofs, 4 m inside the outline, pods excluded')
    return out


# ------------------------------------------------------------------------------------------------ materials / objects
def gltf_output_group():
    grp = bpy.data.node_groups.get('glTF Material Output')
    if grp is None:
        grp = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
        grp.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
    return grp


def make_material(key, atlas, tex_imgs, ao_img):
    spec = MATS[key]
    name = key if atlas is None else f'{key}@{atlas}'
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (*srgb2lin(spec['rgb']), 1.0)
    b.inputs['Metallic'].default_value = spec['m']
    b.inputs['Roughness'].default_value = spec['r']
    b.inputs['IOR'].default_value = spec.get('ior', 1.5)
    if spec.get('ior'):
        # the glTF exporter writes KHR_materials_ior only together with KHR_materials_specular / transmission: a specular
        # level of 0.499 exports KHR_materials_specular (specularFactor 0.998) and with it the coated-glass IOR 1.9
        b.inputs['Specular IOR Level'].default_value = 0.499
        m['ior'] = spec['ior']
    m.use_backface_culling = True       # single-sided (doubleSided false): every face is wound outwards (verify / back-face QA)
    if spec.get('tex'):
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = tex_imgs[spec['tex']]
        uvn = nt.nodes.new('ShaderNodeUVMap'); uvn.uv_map = 'UV_detail'
        nt.links.new(uvn.outputs['UV'], t.inputs['Vector'])
        nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    if spec.get('nrm'):
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = tex_imgs[spec['nrm'][0]]
        uvn = nt.nodes.new('ShaderNodeUVMap'); uvn.uv_map = 'UV_detail'
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.uv_map = 'UV_detail'; nm.inputs['Strength'].default_value = spec['nrm'][1]
        nt.links.new(uvn.outputs['UV'], t.inputs['Vector'])
        nt.links.new(t.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    if ao_img is not None:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = ao_img; t.name = 'AO_BAKE'
        uva = nt.nodes.new('ShaderNodeUVMap'); uva.uv_map = 'UV_ao'
        nt.links.new(uva.outputs['UV'], t.inputs['Vector'])
        sep = nt.nodes.new('ShaderNodeSeparateColor')
        g = nt.nodes.new('ShaderNodeGroup'); g.node_tree = gltf_output_group()
        nt.links.new(t.outputs['Color'], sep.inputs['Color'])
        nt.links.new(sep.outputs['Red'], g.inputs['Occlusion'])
        for n in nt.nodes: n.select = False
        t.select = True; nt.nodes.active = t
    m['src'] = spec['src']
    return m


def mesh_from_mb(name, mb, atlas, tex_imgs, ao_img):
    me = bpy.data.meshes.new(name)
    me.from_pydata(mb.V, [], mb.F)
    me.update()
    nloops = sum(len(f) for f in mb.F)
    assert len(me.loops) == nloops and len(me.polygons) == len(mb.F), (name, len(me.loops), nloops)
    uv = me.uv_layers.new(name='UV_detail')
    uv.data.foreach_set('uv', np.asarray([t for f in mb.UV for t in f], np.float32).ravel())
    keys = list(dict.fromkeys(mb.M))
    for k in keys:
        me.materials.append(make_material(k, atlas, tex_imgs, ao_img))
    me.polygons.foreach_set('material_index', np.array([keys.index(k) for k in mb.M], np.int32))
    me.polygons.foreach_set('use_smooth', np.array(mb.S, bool))
    me.update()
    return me


def new_object(name, me, parent, extras):
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = parent
    for k, v in extras.items():
        ob[k] = v
    return ob


def recentre(me):
    """move the mesh origin to its bbox centre (ground level): smaller local coordinates for later quantization."""
    co = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    c = (co.min(0) + co.max(0)) / 2; c[2] = 0.0
    co -= c; me.vertices.foreach_set('co', co.ravel()); me.update()
    return tuple(float(x) for x in c)


def lettering(parent, lod):
    """'SAN FRANCISCO INTERNATIONAL' on the clear central bay (BI-02 V1: +-33 m wide, 2.8 m tall, 25.8-28.6 m) [obs photos
    i1 / i4 extents; font: Blender's built-in, inf]; letters 0.5 m in front of the glass, 0.08 m deep."""
    cu = bpy.data.curves.new('itb_lettering_curve', 'FONT')
    cu.body = 'SAN FRANCISCO INTERNATIONAL'
    cu.align_x = 'CENTER'; cu.size = 1.0; cu.extrude = 0.04
    tmp = bpy.data.objects.new('tmp_text', cu); bpy.context.scene.collection.objects.link(tmp)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp); bpy.data.curves.remove(cu)
    co = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    lo, hi = co.min(0), co.max(0)
    sx = 2 * G.I.LETTER_HW / (hi[0] - lo[0]); sy = 2.8 / (hi[1] - lo[1])
    co[:, 0] = (co[:, 0] - 0.5 * (lo[0] + hi[0])) * sx
    co[:, 1] = (co[:, 1] - 0.5 * (lo[1] + hi[1])) * sy
    eu = np.array(G.Buv(1, 0, 0)) - np.array(G.Buv(0, 0, 0)); ev = np.array(G.Buv(0, 1, 0)) - np.array(G.Buv(0, 0, 0))
    ez = np.array([0, 0, 1.0])
    o = np.array(G.Buv(0, G.V_W - 0.5, 27.2))
    P = o[None, :] + co[:, 0:1] * eu[None, :] + co[:, 1:2] * ez[None, :] + co[:, 2:3] * (-ev)[None, :]
    me.vertices.foreach_set('co', P.astype(np.float32).ravel())
    while me.uv_layers: me.uv_layers.remove(me.uv_layers[0])
    me.uv_layers.new(name='UV_detail')
    me.materials.clear(); me.materials.append(make_material('lettering', None, {}, None))
    me.polygons.foreach_set('material_index', np.zeros(len(me.polygons), np.int32))
    me.update()
    me.name = f'L{lod}_hall_lettering'
    c = recentre(me)
    ob = new_object(me.name, me, parent, dict(src='obs', feature='west-wall lettering', spec=['facade.west'], lod=lod,
                                               dims=dict(width=G.dim(2 * G.I.LETTER_HW, 'obs', 'photos i1 / i4 (+-32.5 / +-37 m)'),
                                                         height=G.dim(2.8, 'obs', 'BI-02 V1 (25.8-28.6 m)'),
                                                         font=G.dim('Blender built-in', 'inf', 'real typeface not identified'))))
    ob.location = c
    return ob


# ------------------------------------------------------------------------------------------------ AO
def unwrap_ao(objs):
    for o in objs:
        uv = o.data.uv_layers.new(name='UV_ao')
        o.data.uv_layers.active = uv
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(50), island_margin=0.0, area_weight=0.0, correct_aspect=True,
                             scale_to_bounds=False)
    bpy.ops.uv.pack_islands(udim_source='CLOSEST_UDIM', rotate=True, rotate_method='ANY', scale=True, margin_method='FRACTION',
                            margin=0.0025, shape_method='CONCAVE')
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in objs:
        o.data.uv_layers['UV_detail'].active_render = True


def bake_ao(objs, hide, img, samples):
    sc = bpy.context.scene
    for o in hide: o.hide_render = True
    sc.cycles.samples = samples
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    for o in objs:
        o.data.uv_layers.active = o.data.uv_layers['UV_ao']
    t = time.time()
    # the atlas starts white and is not cleared: texels outside the islands (+ the 8-px margins) stay unoccluded, so the
    # mip levels do not bleed black into the island edges at a distance
    w, h = img.size
    img.pixels.foreach_set(np.ones(w * h * 4, np.float32))
    bpy.ops.object.bake(type='AO', margin=8, margin_type='EXTEND', use_clear=False)
    for o in hide: o.hide_render = False
    for o in objs:
        o.data.uv_layers.active = o.data.uv_layers['UV_detail']
    return time.time() - t


def smooth_ao(img):
    """3x3 blur of the baked AO (Cycles noise at 32-64 samples); stats over the texels below 0.999 (the islands)."""
    w, h = img.size
    px = np.array(img.pixels[:], np.float32).reshape(h, w, 4)
    a = px[..., 0]
    p = np.pad(a, 1, mode='edge')
    b = sum(p[1 + dy:h + 1 + dy, 1 + dx:w + 1 + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1)) / 9.0
    px[..., 0] = px[..., 1] = px[..., 2] = b; px[..., 3] = 1.0
    img.pixels.foreach_set(px.ravel())
    isl = b[b < 0.999]
    return float(isl.mean()) if len(isl) else 1.0, float(np.percentile(isl, 2)) if len(isl) else 1.0


# ------------------------------------------------------------------------------------------------ glb stats
def glb_json(path):
    import struct
    data = open(path, 'rb').read()
    clen, _ = struct.unpack_from('<I4s', data, 12)
    return json.loads(data[20:20 + clen]), len(data)


def glb_stats(path):
    j, size = glb_json(path)
    acc = j['accessors']
    mesh_tris = []
    for m in j['meshes']:
        t = 0; v = 0
        for p in m['primitives']:
            t += acc[p['indices']]['count'] // 3 if 'indices' in p else acc[p['attributes']['POSITION']]['count'] // 3
            v += acc[p['attributes']['POSITION']]['count']
        mesh_tris.append((t, v))
    nodes = j['nodes']
    lods = {}
    for i, n in enumerate(nodes):
        nm = n.get('name', '')
        if nm in ('LOD0', 'LOD1', 'LOD2'):
            tris = verts = 0; stack = list(n.get('children', []))
            while stack:
                c = nodes[stack.pop()]
                if 'mesh' in c:
                    tris += mesh_tris[c['mesh']][0]; verts += mesh_tris[c['mesh']][1]
                stack += c.get('children', [])
            lods[nm] = dict(tris=tris, verts=verts)
    imgs = []
    for im in j.get('images', []):
        bv = j['bufferViews'][im['bufferView']]
        imgs.append(dict(name=im.get('name'), mime=im.get('mimeType'), bytes=bv['byteLength']))
    mats = j.get('materials', [])
    return dict(bytes=size, generator=j['asset'].get('generator'), lods=lods, meshes=len(j['meshes']), nodes=len(nodes),
                materials=len(mats), materials_with_occlusion=sum(1 for m in mats if 'occlusionTexture' in m),
                occlusion_texcoords=sorted({m['occlusionTexture'].get('texCoord', 0) for m in mats if 'occlusionTexture' in m}),
                normal_textures=sum(1 for m in mats if 'normalTexture' in m), images=imgs,
                extensionsUsed=j.get('extensionsUsed', []))


# ------------------------------------------------------------------------------------------------ manifest
def merge_manifest(update_fn):
    path = os.path.join(DATA, 'manifest.json')
    lock = path + '.lock'
    os.makedirs(DATA, exist_ok=True)
    with open(lock, 'a') as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            cur = json.load(open(path)) if os.path.exists(path) else {}
        except Exception:  # noqa: BLE001
            cur = {}
        cur.setdefault('_about', 'SFO Live 3D building assets (glTF 2.0, built with Blender from the verified 2-D sheets); one key '
                       'per asset group; frame ltp-nad83-2011 (x east, y up, z south, m from the ARP); see docs/research/buildings3d.md')
        cur['itb'] = update_fn(cur.get('itb'))
        tmp = path + '.itb.tmp'
        with open(tmp, 'w') as f:
            json.dump(cur, f, indent=1)
        os.replace(tmp, path)
        fcntl.flock(lf, fcntl.LOCK_UN)
    try:
        os.remove(lock)          # as build_tower.py does: no stray lock file in data/
    except OSError:
        pass
    return path


def git_rev():
    try:
        r = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip()
        d = subprocess.run(['git', 'status', '--porcelain', '--', 'tools/blender', 'tools/buildings'], cwd=ROOT,
                           capture_output=True, text=True, timeout=10).stdout.strip()
        return r + ('+dirty' if d else '')
    except Exception:  # noqa: BLE001
        return 'unknown'


# ------------------------------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-bake', action='store_true')
    ap.add_argument('--ao-samples', type=int, default=48)
    ap.add_argument('--threads', type=int, default=3)
    ap.add_argument('--out', default=os.path.join(DATA, 'itb.glb'))
    ap.add_argument('--no-manifest', action='store_true')
    ap.add_argument('--blend', action='store_true', help='also save out/buildings3d/itb.blend')
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); os.makedirs(TEX, exist_ok=True); os.makedirs(os.path.dirname(args.out), exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
    sc.render.threads_mode = 'FIXED'; sc.render.threads = args.threads
    world = bpy.data.worlds.new('world'); sc.world = world
    world.light_settings.distance = AO_DIST

    # ---- roof colours from NAIP (public domain; colour only)
    nc = None
    try:
        nc = naip_colours()
    except Exception as e:  # noqa: BLE001
        log('NAIP colour sampling failed:', e)
    if nc:
        MATS['roof_membrane']['rgb'] = tuple(nc['hall']['rgb']); MATS['roof_membrane_pier']['rgb'] = tuple(nc['pier']['rgb'])
        log('NAIP roof colours', nc['hall']['rgb'], nc['pier']['rgb'])

    # ---- textures
    paths = itb_tex.make_all(TEX)
    tex_imgs = {}
    for k, p in paths.items():
        im = bpy.data.images.load(p); im.name = k
        if k.startswith('itb_n_'): im.colorspace_settings.name = 'Non-Color'
        tex_imgs[k] = im
    ao_imgs = {}
    for a, res in AO_RES.items():
        im = bpy.data.images.new(f'itb_ao_{a}', res, res, alpha=False, float_buffer=False)
        im.colorspace_settings.name = 'Non-Color'
        im.generated_color = (1, 1, 1, 1)
        ao_imgs[a] = im

    # ---- hierarchy
    root = bpy.data.objects.new('itb', None); sc.collection.objects.link(root)
    root.location = (G.OX, -G.OZ, GROUND_Y)
    root['src'] = 'mixed: per node'
    root['frame'] = 'ltp-nad83-2011; root at world (x %.3f, y %.1f, z %.3f) = relief-corrected roof centre, GROUND_Y' % (G.OX, GROUND_Y, G.OZ)
    root['manifest'] = 'data/buildings3d/manifest.json#itb'
    root['drawings'] = 'docs/drawings/buildings/BI-01..04'
    lod_empties, objs, shells = {}, {0: [], 1: [], 2: []}, {'A': [], 'B': []}
    parts = {}
    shared = {}
    stats_parts = {}
    for lod in (0, 1, 2):
        e = bpy.data.objects.new(f'LOD{lod}', None); sc.collection.objects.link(e); e.parent = root
        e['lod'] = lod; e['switch_m'] = G.SWITCH_M[lod]
        e['switch_note'] = 'show this LOD when the camera is at least switch_m from the root (and below the next LOD\'s switch_m)'
        lod_empties[lod] = e
        P = G.build(lod); parts[lod] = P
        atlas = 'A' if lod < 2 else 'B'
        for name, part in P.items():
            if part.kind == 'shell' and lod == 1 and name in shared:
                me, loc = shared[name]
            else:
                me = mesh_from_mb(f'L{lod}_{name}', part.mb, atlas if part.kind == 'shell' else None, tex_imgs,
                                  ao_imgs[atlas] if part.kind == 'shell' else None)
                loc = recentre(me)
                if part.kind == 'shell' and lod == 0: shared[name] = (me, loc)
            ob = new_object(f'L{lod}_{name}', me, e, part.extras(lod))
            ob.location = loc
            objs[lod].append(ob)
            if part.kind == 'shell' and not (lod == 1 and name in shared):
                shells[atlas].append(ob)
            stats_parts.setdefault(name, {})[lod] = part.mb.tris()
        if lod == 0:
            objs[0].append(lettering(e, 0))
            stats_parts['hall_lettering'] = {0: len(objs[0][-1].data.polygons)}
    log('objects built', {l: len(o) for l, o in objs.items()})
    # LOD2 (far / phone tier): all parts joined into one node -> one primitive per material (fewer draw calls); the per-part
    # tags move into its extras.parts
    l2 = objs[2]
    bpy.ops.object.select_all(action='DESELECT')
    for o in l2: o.select_set(True)
    bpy.context.view_layer.objects.active = l2[0]
    bpy.ops.object.join()
    j2 = bpy.context.view_layer.objects.active
    for k in list(j2.keys()): del j2[k]
    j2.name = 'L2_itb'; j2.data.name = 'L2_itb'
    j2['src'] = 'mixed: see parts'; j2['feature'] = 'coarse shell: hall roof, walls, canopy, core, piers, pods, end box (joined)'
    j2['lod'] = 2; j2['parts'] = {n: p.extras(2) for n, p in parts[2].items()}
    objs[2] = [j2]; shells['B'] = [j2]
    log('LOD2 joined: %d material slots' % len(j2.data.materials))

    # ---- AO
    ao_info = {}
    if not args.no_bake:
        bpy.ops.mesh.primitive_plane_add(size=3000, location=(0, 0, 0))
        ground = bpy.context.object; ground.name = 'bake_ground'
        for a, lods in (('A', (0,)), ('B', (2,))):
            t = time.time(); unwrap_ao(shells[a]); log(f'atlas {a}: UV_ao packed over {len(shells[a])} objects in {time.time() - t:.1f} s')
            hide = [o for l in (0, 1, 2) if l not in lods for o in objs[l]]
            dt = bake_ao(shells[a], hide, ao_imgs[a], args.ao_samples)
            mean, p2 = smooth_ao(ao_imgs[a])
            ao_info[a] = dict(res=AO_RES[a], lods=[0, 1] if a == 'A' else [2], bake_s=round(dt, 1), mean=round(mean, 3), p2=round(p2, 3),
                              samples=args.ao_samples, distance_m=AO_DIST, ground_plane=True)
            log(f'atlas {a}: AO {AO_RES[a]} baked in {dt:.1f} s, mean {mean:.3f}, p2 {p2:.3f}')
        bpy.data.objects.remove(ground)
    else:
        for a in shells:
            unwrap_ao(shells[a])
    for a, im in ao_imgs.items():
        im.filepath_raw = os.path.join(TEX, f'itb_ao_{a}.png'); im.file_format = 'PNG'
        im.save()
        im.colorspace_settings.name = 'Non-Color'

    # ---- export
    bpy.ops.object.select_all(action='DESELECT')
    root.select_set(True)
    for o in root.children_recursive: o.select_set(True)
    t = time.time()
    bpy.ops.export_scene.gltf(filepath=args.out, export_format='GLB', use_selection=True, export_extras=True, export_yup=True,
                              export_apply=False, export_texcoords=True, export_normals=True, export_tangents=False,
                              export_materials='EXPORT', export_image_format='AUTO', export_cameras=False, export_lights=False,
                              export_animations=False)
    log(f'exported {args.out} in {time.time() - t:.1f} s')
    # far / phone tier: the LOD2 subtree alone (root transform kept), so a client can load the overview without LOD0 / LOD1
    lod2_path = os.path.join(os.path.dirname(args.out), os.path.basename(args.out).replace('.glb', '_lod2.glb'))
    bpy.ops.object.select_all(action='DESELECT')
    root.select_set(True); lod_empties[2].select_set(True)
    for o in lod_empties[2].children_recursive: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=lod2_path, export_format='GLB', use_selection=True, export_extras=True, export_yup=True,
                              export_apply=False, export_texcoords=True, export_normals=True, export_tangents=False,
                              export_materials='EXPORT', export_image_format='AUTO', export_cameras=False, export_lights=False,
                              export_animations=False)
    log(f'exported {lod2_path}')
    if args.blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'itb.blend'))
    st = glb_stats(args.out)
    log('glb', json.dumps({k: st[k] for k in ('bytes', 'lods', 'materials', 'materials_with_occlusion', 'occlusion_texcoords')}))
    build = dict(built=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'), git=git_rev(),
                 bpy=bpy.app.version_string, glb=st, ao=ao_info, naip_colours=nc, parts_tris=stats_parts,
                 lod2_glb=dict(path=os.path.relpath(lod2_path, ROOT), bytes=os.path.getsize(lod2_path)),
                 seconds=round(time.time() - T0, 1))
    json.dump(build, open(os.path.join(OUT, 'itb_build.json'), 'w'), indent=1)

    # ---- verification (separate process: it reads the glb back) + manifest
    ver = None
    try:
        r = subprocess.run([sys.executable, os.path.join(HERE, 'verify_itb.py'), args.out], capture_output=True, text=True, timeout=900)
        print(r.stdout[-4000:], r.stderr[-2000:])
        ver = json.load(open(os.path.join(OUT, 'itb_verify.json')))
    except Exception as e:  # noqa: BLE001
        log('verification failed:', e)
    if not args.no_manifest and os.path.abspath(args.out) == os.path.abspath(os.path.join(DATA, 'itb.glb')):
        import itb_manifest
        entry = itb_manifest.entry(build, ver, parts, MATS)
        path = merge_manifest(lambda old: itb_manifest.keep_renders(old, entry))
        log('manifest ->', path)


if __name__ == '__main__':
    main()
