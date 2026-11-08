# SPDX-License-Identifier: GPL-3.0-or-later
# (imports bpy: Blender's licence asks scripts that use its API to be GPL-compatible if published, docs/research/engine.md 7.3)
"""Build the 3-D asset of the SFO air traffic control tower (2016) and its base building with Blender (bpy 5.0, Cycles CPU):

    python3 tools/blender/build_tower.py                 # both families, AO bake, export, manifest, verification
    python3 tools/blender/build_tower.py --render        # + Cycles reference renders of the default family (out/buildings3d/tower_*.png)
    python3 tools/blender/build_tower.py --family 2 --no-bake --render --samples 16 --res 480    # quick look

Inputs (all in the repo, read through tools/blender/tower_geom.py):
  tools/buildings/draw_tower.py + spec_tower.json   the approved 2-D sheets BT-01..03 (the reference geometry)
  data/sfo_airport.json                             SFO Museum footprint of the base building
Outputs:
  data/buildings3d/tower.glb       the DEFAULT family, F2 (D 14.5, rim 64.0, 221 ft at the 2015 mast station): the family
                                   anchored on the observed cab-roof diameter (14.3 +-1.0, EXIF 14.75 +-0.5)  } the sheets draw
  data/buildings3d/tower_f1.glb    F1 (D 15.2, rim 67.36 = 221 ft): the published-height hypothesis (CTBUH        } both; the
                                   classification, not a survey; ?b3dtower=f1 in the app)                         } owner decides
  data/buildings3d/tower_lod2.glb  LOD2 of the default family (phones / far)
  data/buildings3d/manifest.json   key "tower" (merged; other groups own their keys)
  out/buildings3d/tower_*.png      Cycles reference renders (local), tower_verify.json (numbers)

glTF layout: root node "tower" at world (axis x, GROUND_Y, axis z) (app frame: x east, y up, z south, metres from the ARP;
GROUND_Y = 3.0 per js/geo.js), children LOD0 / LOD1 / LOD2 (extras.lod, extras.switch_m), each with the nodes of
tower_geom (shaft, landside, ribbon, flare_deck, cab, cab_glass, roof_masts, ibf, ibf_equipment). Every node carries
extras {src, feature, spec (spec_tower.json keys), drawing, tags}. Materials are PBR (baseColor / metallic / roughness);
detail normal maps tile on TEXCOORD_0; sun-independent ambient occlusion is baked by Cycles into one atlas per LOD on
TEXCOORD_1 (occlusionTexture.texCoord = 1). No imagery is used as a texture (NAIP 2024 only gave the roof-garden outline
and hue, see tower_geom.GARDEN). KTX2 / meshopt compression is a later step (tools/engine/glb_compress.mjs).
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
import tower_geom as G  # noqa: E402
import tower_tex  # noqa: E402
import tower3d_verify as TV  # noqa: E402

ROOT = G.ROOT
# TOWER_DATA_DIR / TOWER_OUT_DIR: write the files of a quick look elsewhere (the app and other agents read data/buildings3d)
DATA = os.environ.get('TOWER_DATA_DIR') or os.path.join(ROOT, 'data', 'buildings3d')
OUT = os.environ.get('TOWER_OUT_DIR') or os.path.join(ROOT, 'out', 'buildings3d')
GROUND_Y = 3.0                       # js/geo.js GROUND_Y (nominal airfield elevation; the app's ground plane)
AO_RES = {0: 2048, 1: 1024, 2: 512}
AO_FLAG = {}                         # object name -> receives the baked AO (thin details, glass and masts do not)
AO_DIST = 8.0                        # AO ray length, m
RENDER = dict(sun=3.0, sky=0.05, exposure=-0.3)   # reference-render lighting (set by --sun / --sky / --exposure)
DEFAULT_FAM = TV.DEFAULT_FAM          # 2 (review round 1, 2026-11-05: F2 lies within the observations; F1 rests on a database class)

# PBR materials: sRGB base colour, metallic, roughness, extras. Values are our choices for the published materials
# (tags in the manifest); no texture is taken from imagery.
MATS = {
    # clad: panel colour of the base-colour tile (tower_tex.clad_color: dark joint lines + +-5 % per-panel tone; mean ~(150, 154,
    # 160) as round 1, linear albedo ~0.31: with the t2 geometry (sunlit face at cos 0.37 vs a horizontal white bridge roof at
    # cos 0.88) this reproduces the photo's shaft / bridge display ratio ~0.5, so the albedo is not lowered for the app view)
    'clad':          dict(rgb=(152, 156, 162), m=0.15, r=0.50, nrm=('tile_panel_tower', 1.0), tex='tile_clad_color',
                          src='pub material (4-mm Alucobond Plus, custom "SFO Silver", MCN 2017); colour / finish inf; dark joint '
                          'lines obs photos t2 / t4 (width / tone inf)'),
    'clad_deck':     dict(rgb=(150, 154, 160), m=0.15, r=0.50, src='as clad (flare-top shoulder, no joint tile: its UVs are not '
                          'panel-aligned); colour = the clad tile mean'),
    'louvre':        dict(rgb=(132, 136, 142), m=0.15, r=0.55, nrm=('tile_louvre', 1.0),
                          src='obs photos t3/t4 (horizontally louvred SW wing); finish inf'),
    'seam':          dict(rgb=(98, 101, 106), m=0.15, r=0.60, src='obs photos t2 / t4 (the two circumferential seams read as dark '
                          'recessed joints, darker than the row joints); width 0.10 m and tone inf'),
    # slots (review round 2, finding 1: near-black pockets read as black gashes, t2 display ratio slot / panel 0.1-0.3 vs the
    # photo's 0.6-0.7): a perforated screen (base-colour tile tower_tex.slot_color: holes on a mid-grey sheet) SCREEN_INSET
    # behind the face; the pocket behind it is only seen around the glazed lowest panes. Sheet sRGB 122-131 (tile mean 114-123,
    # linear albedo 0.56 x the cladding tile): Cycles t2 display ratio slot / panel 0.64-0.73 (upper band, photo 0.69-0.76) and
    # 0.74 (long slot, photo 0.62-0.72); a first pass at sheet 112-121 gave 0.56-0.65 / 0.66
    'slot_screen':   dict(rgb=(122, 126, 131), m=0.15, r=0.60, tex='tile_slot_color',
                          src='obs photo t4 (perforated screen, a fine dot grid, in every slot above its glazed lowest pane); '
                          'tone tuned to the t2 photo (slot / panel display ratio ~0.6-0.7); hole grid and finish inf'),
    'slot_pocket':   dict(rgb=(40, 44, 48), m=0.0, r=0.85, src='inf (the void behind the screen and the glazed pane)'),
    'slot_reveal':   dict(rgb=(132, 136, 142), m=0.15, r=0.55, src='inf (panel return around the screen: obs photo t4, a thin '
                          'light reveal)'),
    'slot_glass':    dict(rgb=(150, 175, 190), m=0.0, r=0.08, src='obs photos t3/t4 (glazed lowest pane)'),
    # led_color: the app's night glow colour of the ribbon (material extras.led_color, linear RGB; js/three/buildings3d.js led
    # glow): the hue of photo t5 (Varnum 2018-04, dusk; median of 91k ribbon pixels sRGB (82, 137, 209), IQR R 65-93 / G 125-145
    # / B 194-226 -> linear (0.084, 0.250, 0.638)), scaled to the luminance of the loader's previous blue-cyan wave mean
    # (0.605) so the tuned night level is kept. The array is programmable (pub: LED-backlit): this is the observed default,
    # an inferred choice for every other night (review round 2, finding 4: the ribbon glowed near-white).
    # Tone-mapping compensation: with the photo's own linear colour (0.21, 0.623, 1.588) the app's night render
    # (out/buildings3d/app/r2/tapp_t4night.png, 21:30 PDT) showed the ribbon at median sRGB (104, 144, 182): hue 209 /
    # saturation 0.35 against the photo's 214 / 0.58 (AgX desaturates). The display ratios fit out = in^0.56 (R/B and G/B), so
    # the input chroma is set to the ratios that map onto the photo's (R/B 0.027, G/B 0.188), at the same luminance 0.605
    'ribbon_glass':  dict(rgb=(150, 182, 175), m=0.0, r=0.06, src='pub (Guardian SNX 62/27 IGUs, LED-backlit); daytime tint obs photos '
                          't3/t4; emissive off by day (extras.led); night colour obs photo t5 (extras.led_color: the observed '
                          'default of a programmable array, inf for any other night)', led=True,
                          led_color=(0.077, 0.536, 2.848), led_color_obs=dict(photo='t5', srgb_median=(82, 137, 209), linear=(0.084, 0.250, 0.638),
                          note='input chroma compensated for the app tone mapping (round-2 night render: photo-linear colour '
                          'gave hue 209 / sat 0.35 vs the photo 214 / 0.58)')),
    'mullion':       dict(rgb=(85, 88, 92), m=0.70, r=0.40, src='inf'),
    'plinth':        dict(rgb=(60, 70, 80), m=0.40, r=0.45, src='obs photo t1 (dark ring under the cab glass)'),
    # cab glass: tinted, see-through. Photos: glass / sky display 0.31 (t1, near-level view: the sky shows through the far-side
    # panes, teal tint, dark consoles below and a dark band above), 0.28 (t2), 0.10 (t3, 12 deg below the rim: the ceiling
    # behind). Review round 2 (finding 2): from below, round 1 (alpha 0.5, black ceiling) read two-tone, the upper part ~0.5x
    # the photo (the black ceiling behind), the lower third ~1.8x (sky through both panes); the photo is a uniform dark tint.
    # Now alpha 0.6 (two panes: 16 % of the sky), a mid-dark ceiling and the dark shade band inside the glass head (obs t1),
    # which from 12 deg below hides the far side's sky, and a lighter teal-grey tint: Cycles t2 vertical profile through the
    # cab centre 24-35 (mean 33, uniform) vs the photo 26-41 (mean 34); variants (one session): tint (48, 60, 64) mean 26
    # (upper 18, 0.5x), (80, 98, 106) at alpha 0.7 mean 38, (100, 122, 130) at 0.7 mean 50
    'cab_glass':     dict(rgb=(80, 98, 106), m=0.0, r=0.04, alpha=0.6, src='pub (clear laminated frameless glass, Fentress); tint '
                          'and see-through look obs photos t1 / t2 / t3 (glass / sky 0.28-0.31 level, uniform dark from below); '
                          'alpha blend (0.6 inf)', blend=True),
    'cab_joint':     dict(rgb=(38, 40, 43), m=0.30, r=0.50, src='pub cab_glass_type (frameless butt-glazed); obs photo t2 (thin dark '
                          'joint lines; review round 2, finding 3: round 1 had light 6-cm joints); width 0.03 m and tone inf'),
    # interior (review round 2, findings 2 / 3): neutral mid-dark placeholders instead of one near-black material.
    # ambient_only (material extras -> js/three/buildings3d.js): sky light only in the app, no sun / shadow lookup (the
    # alpha-blended glass casts no shadow, so the sun lit the whole floor through it and the floor sat in the PCF penumbra:
    # a per-pixel checker on the low tier, finding 3); Cycles renders them physically
    'cab_floor':     dict(rgb=(74, 74, 76), m=0.0, r=0.90, ambient_only=True, src='unknown (neutral placeholder floor)'),
    'cab_console':   dict(rgb=(96, 96, 94), m=0.0, r=0.70, ambient_only=True, src='unknown (neutral placeholder console ring)'),
    'cab_ceiling':   dict(rgb=(62, 62, 64), m=0.0, r=0.90, ambient_only=True, src='unknown (mid-dark placeholder ceiling)'),
    'cab_shade':     dict(rgb=(52, 54, 58), m=0.0, r=0.85, ambient_only=True, src='obs photo t1 (dark band over the top ~0.35-0.4 of the glass, all '
                          'round); nature (sun shades / valance) and tone inf'),
    'roof_deck':     dict(rgb=(205, 205, 200), m=0.0, r=0.85, src='obs NAIP 2024 (white membrane, saturated: albedo inf)'),
    'coping':        dict(rgb=(176, 178, 180), m=0.15, r=0.45, src='inf'),
    'ibf_panel':     dict(rgb=(140, 144, 148), m=0.15, r=0.50, nrm=('tile_panel_ibf', 1.2),
                          src='obs photos t2/t4 (grey metal panels); module / finish inf'),
    'ibf_glass_dark': dict(rgb=(35, 42, 50), m=0.0, r=0.06, src='obs photo t2 (continuous dark glazing band)'),
    'ibf_curtain':   dict(rgb=(55, 78, 72), m=0.0, r=0.06, glazing=True, src='obs photo t4 (green-tinted curtain-wall bay)'),
    'garden':        dict(rgb=(128, 122, 92), m=0.0, r=0.95, src='obs NAIP 2024 hue of the planted roof garden; value inf'),
    'equipment':     dict(rgb=(200, 202, 200), m=0.30, r=0.50, nrm=('tile_louvre', 0.6), src='obs photo t4 (white louvred unit)'),
    'rail':          dict(rgb=(150, 152, 155), m=0.80, r=0.45, src='obs photos t2/t3 (railings); finish inf'),
    'mast':          dict(rgb=(60, 60, 62), m=0.60, r=0.50, src='obs photos t2/t3 (dark whips)'),
    'pole':          dict(rgb=(190, 190, 190), m=0.40, r=0.50, src='obs photos t2/t3 (light poles, cameras, lamps)'),
    'red_light':     dict(rgb=(170, 10, 10), m=0.0, r=0.30, src='obs photo t5 (red obstruction light on the rim, SW); lit at '
                          'night by the app (extras.obstruction_light)', light='obstruction'),
}


def srgb2lin(c):
    c = np.asarray(c, float) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def log(*a):
    print('[build_tower]', *a, flush=True)


# ------------------------------------------------------------------------------------------------ scene setup
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    try:
        sc.render.threads_mode = 'FIXED'; sc.render.threads = 4
    except Exception:  # noqa: BLE001
        pass
    world = bpy.data.worlds.new('world'); sc.world = world
    world.light_settings.distance = AO_DIST
    return sc


def gltf_output_group():
    grp = bpy.data.node_groups.get('glTF Material Output')
    if grp is None:
        grp = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
        grp.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
    return grp


def make_material(key, lod, tex_imgs, ao_img):
    spec = MATS[key]
    name = f'{key}' if ao_img is None else f'{key}.L{lod}'
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get('Principled BSDF')
    lin = srgb2lin(spec['rgb'])
    b.inputs['Base Color'].default_value = (*lin, 1.0)
    b.inputs['Metallic'].default_value = spec['m']
    b.inputs['Roughness'].default_value = spec['r']
    if 'IOR' in b.inputs:
        b.inputs['IOR'].default_value = 1.5
    if spec.get('alpha') is not None:
        b.inputs['Alpha'].default_value = spec['alpha']
        try:
            m.surface_render_method = 'BLENDED'
        except Exception:  # noqa: BLE001
            pass
        try:
            m.blend_method = 'BLEND'
        except Exception:  # noqa: BLE001
            pass
        m.use_backface_culling = False
    if spec.get('tex'):                                   # base-colour tile (sRGB) on UV_detail; the factor stays white
        b.inputs['Base Color'].default_value = (1.0, 1.0, 1.0, 1.0)
        tc = nt.nodes.new('ShaderNodeTexImage'); tc.image = tex_imgs[spec['tex']]; tc.interpolation = 'Linear'
        uvc = nt.nodes.new('ShaderNodeUVMap'); uvc.uv_map = 'UV_detail'
        nt.links.new(uvc.outputs['UV'], tc.inputs['Vector'])
        nt.links.new(tc.outputs['Color'], b.inputs['Base Color'])
    if spec.get('nrm'):
        tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = tex_imgs[spec['nrm'][0]]
        tex.interpolation = 'Linear'
        uvn = nt.nodes.new('ShaderNodeUVMap'); uvn.uv_map = 'UV_detail'
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.uv_map = 'UV_detail'; nm.inputs['Strength'].default_value = spec['nrm'][1]
        nt.links.new(uvn.outputs['UV'], tex.inputs['Vector'])
        nt.links.new(tex.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    if ao_img is not None:
        tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = ao_img; tex.name = 'AO_BAKE'
        uva = nt.nodes.new('ShaderNodeUVMap'); uva.uv_map = 'UV_ao'
        nt.links.new(uva.outputs['UV'], tex.inputs['Vector'])
        for n in nt.nodes: n.select = False
        tex.select = True; nt.nodes.active = tex
    m['src'] = spec['src']
    if spec.get('led'): m['led'] = True
    if spec.get('light'): m['obstruction_light'] = True
    return m


def make_object(part, lod, parent, tex_imgs, ao_img):
    me = bpy.data.meshes.new(f'L{lod}_{part.name}')
    me.from_pydata(part.V, [], part.F)
    me.validate(clean_customdata=False)
    me.update()
    uv = me.uv_layers.new(name='UV_detail')
    loops_v = np.zeros(len(me.loops), np.int64); me.loops.foreach_get('vertex_index', loops_v)
    UV = np.asarray(part.UV, np.float32)
    uv.data.foreach_set('uv', UV[loops_v].ravel())
    keys = list(dict.fromkeys(part.M))
    for k in keys:
        me.materials.append(make_material(k, lod, tex_imgs, ao_img if (part.ao and ao_img is not None) else None))
    idx = np.array([keys.index(k) for k in part.M], np.int32)
    if len(idx) == len(me.polygons):
        me.polygons.foreach_set('material_index', idx)
    ob = bpy.data.objects.new(f'L{lod}_{part.name}', me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = parent
    for k, v in part.extras.items():
        ob[k] = v
    ob['lod'] = lod
    ob['tris'] = part.tris()
    if part.smooth:
        me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
        bpy.context.view_layer.objects.active = ob
        for o in bpy.context.selected_objects: o.select_set(False)
        ob.select_set(True)
        try:
            bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35.0))
        except Exception as e:  # noqa: BLE001
            log('shade_smooth_by_angle failed', e)
    return ob


def unwrap_ao(objs):
    """one non-overlapping lightmap UV set (UV_ao) over all AO objects of one LOD (Blender multi-object edit)."""
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
    try:
        bpy.ops.uv.pack_islands(udim_source='CLOSEST_UDIM', rotate=True, margin_method='FRACTION', margin=0.003,
                                shape_method='CONCAVE')
    except TypeError:
        bpy.ops.uv.pack_islands(rotate=True, margin=0.003)
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
    # pre-fill with white and bake without clearing: texels outside the islands stay 1.0 (unoccluded), so mip levels do not
    # bleed black into the island edges at distance
    img.pixels[:] = np.ones(img.size[0] * img.size[1] * 4, np.float32)
    bpy.ops.object.bake(type='AO', margin=6, margin_type='EXTEND', use_clear=False)
    for o in hide: o.hide_render = False
    for o in objs:
        o.data.uv_layers.active = o.data.uv_layers['UV_detail']
    return time.time() - t


def smooth_ao(img):
    """light 3x3 blur of the baked AO (Cycles noise at 32-64 samples), applied to the whole atlas (margins extended)."""
    w, h = img.size
    px = np.array(img.pixels[:], np.float32).reshape(h, w, 4)
    a = px[..., 0]
    k = np.array([1, 2, 1], np.float32) / 4
    b = np.pad(a, 1, mode='edge')
    b = k[0] * b[:-2] + k[1] * b[1:-1] + k[2] * b[2:]
    b = k[0] * b[:, :-2] + k[1] * b[:, 1:-1] + k[2] * b[:, 2:]
    px[..., 0] = px[..., 1] = px[..., 2] = b; px[..., 3] = 1.0
    img.pixels[:] = px.ravel()
    return float(b.mean()), float(np.percentile(b, 2))


def wire_ao(mats):
    # close-out r3 fix 2 (verifier v8): ONE glass rule for all four assets (as domestic, buildings-5): no glTF occlusion on a
    # GLASS material. The baked AO is a diffuse visibility; three.js applies a material's aoMap to the indirect diffuse AND,
    # through its specular occlusion (computeSpecularOcclusion), to the IBL reflection that makes glass read, while Cycles
    # ignores the glTF occlusion - so AO on glass made the app and Cycles disagree. The image node stays (the bake target).
    # Close-out round 4 (verifier: the rule keyed on the NAME missed ibf_curtain, the base building's curtain-wall bays): a
    # material is glazing when its MATS entry says glazing=True, else when 'glass' is in its key.
    grp = gltf_output_group()
    for m in mats:
        nt = m.node_tree
        tex = nt.nodes.get('AO_BAKE')
        if tex is None or any(n.type == 'GROUP' and n.node_tree == grp for n in nt.nodes): continue
        k = m.name.split('.L')[0]
        if MATS.get(k, {}).get('glazing', 'glass' in k): continue    # close-out r4: keyed on the glazing flag
        sep = nt.nodes.new('ShaderNodeSeparateColor')
        g = nt.nodes.new('ShaderNodeGroup'); g.node_tree = grp
        nt.links.new(tex.outputs['Color'], sep.inputs['Color'])
        nt.links.new(sep.outputs['Red'], g.inputs['Occlusion'])


# ------------------------------------------------------------------------------------------------ one family
def build_family(fam, args, tex_paths):
    sc = reset_scene()
    t0 = time.time()
    model, TW = G.build(fam)
    tex_imgs = {}
    for k, p in tex_paths.items():
        if k.startswith('_'): continue
        im = bpy.data.images.load(p); im.colorspace_settings.name = 'sRGB' if k.endswith('_color') else 'Non-Color'; im.name = k
        tex_imgs[k] = im
    root = bpy.data.objects.new('tower', None)
    sc.collection.objects.link(root)
    root.location = (float(G.AXIS[0]), float(-G.AXIS[1]), GROUND_Y)
    anchors = TV.anchors(TW)
    root['asset'] = 'SFO air traffic control tower (2016) + base building (IBF)'
    root['family'] = f"F{fam}: {G.DT.FAM[fam]['label']}"
    root['family_decided'] = False
    root['placement'] = dict(frame='ltp-nad83-2011 (js/geo.js): x east, y up, z south, m from the ARP',
                             origin_world_xz=[float(G.AXIS[0]), float(G.AXIS[1])], origin_y=GROUND_Y,
                             origin='inferred shaft axis at grade [inf] (position_shaft_axis, +-5.5 / 3 m)')
    root['anchors'] = anchors
    root['src'] = 'inf'
    root['spec'] = 'tools/buildings/spec_tower.json; drawings docs/drawings/buildings/BT-01..03'
    root['manifest'] = 'data/buildings3d/manifest.json#tower'
    lod_objs = {}
    stats = {}
    for lod in (0, 1, 2):
        e = bpy.data.objects.new(f'LOD{lod}', None); sc.collection.objects.link(e); e.parent = root
        e['lod'] = lod
        sw = G.LODS[lod]['switch_m']
        e['switch_m'] = [sw[0], sw[1] if sw[1] is not None else -1]
        e['note'] = 'suggested camera-distance band (m); -1 = no upper limit'
        ao_img = None
        if not args.no_bake:
            ao_img = bpy.data.images.new(f'tower_ao_L{lod}' + ('' if fam == 1 else '_f2'), AO_RES[lod], AO_RES[lod],
                                         alpha=False, float_buffer=False)
            ao_img.colorspace_settings.name = 'Non-Color'
        objs = []
        parts = model[lod]
        for name, part in parts.items():
            if name.startswith('_'): continue
            o = make_object(part, lod, e, tex_imgs, ao_img)
            AO_FLAG[o.name] = part.ao
            objs.append(o)
        lod_objs[lod] = (e, objs, ao_img)
        stats[lod] = dict(tris=sum(p.tris() for k, p in parts.items() if not k.startswith('_')),
                          nodes={k: p.tris() for k, p in parts.items() if not k.startswith('_')},
                          notes=parts['_notes'], stations=len(parts['_stations']))
        e['tris'] = stats[lod]['tris']
    log(f'F{fam}: geometry {time.time() - t0:.1f} s', {l: s['tris'] for l, s in stats.items()})
    # AO ground (bake only, not exported)
    bpy.ops.mesh.primitive_plane_add(size=400, location=(float(G.AXIS[0]), float(-G.AXIS[1]), GROUND_Y))
    ground = bpy.context.object; ground.name = 'AO_ground'
    ao_info = {}
    if not args.no_bake:
        for lod, (e, objs, img) in lod_objs.items():
            aoo = [o for o in objs if AO_FLAG[o.name]]
            t = time.time()
            unwrap_ao(aoo)
            others = [o for l2, (_, ob2, _) in lod_objs.items() if l2 != lod for o in ob2]
            hide = others + [o for o in objs if o not in aoo]
            dt = bake_ao(aoo, hide, img, args.ao_samples)
            mean, p2 = smooth_ao(img)
            img.filepath_raw = os.path.join(OUT, f'{img.name}.png'); img.file_format = 'PNG'; img.save()
            ao_info[lod] = dict(res=AO_RES[lod], bake_s=round(dt, 1), mean=round(mean, 3), p2=round(p2, 3), samples=args.ao_samples,
                                distance_m=AO_DIST, unwrap_bake_s=round(time.time() - t, 1))
            log(f'F{fam} LOD{lod}: AO {AO_RES[lod]} baked in {dt:.1f} s, mean {mean:.3f}')
        wire_ao([m for m in bpy.data.materials if m.node_tree and m.node_tree.nodes.get('AO_BAKE')])
    bpy.data.objects.remove(ground, do_unlink=True)
    # export
    os.makedirs(DATA, exist_ok=True)
    glb = os.path.join(DATA, TV.FILE[fam])
    bpy.ops.object.select_all(action='DESELECT')
    root.select_set(True)
    for lod, (e, objs, img) in lod_objs.items():
        e.select_set(True)
        for o in objs: o.select_set(True)
    t = time.time()
    bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_extras=True, export_yup=True,
                              export_apply=False, export_texcoords=True, export_normals=True, export_tangents=True,
                              export_materials='EXPORT', export_image_format='AUTO', export_cameras=False, export_lights=False,
                              export_animations=False)
    log(f'F{fam}: exported {glb} in {time.time() - t:.1f} s')
    info = TV.postprocess(glb, fam, TW, stats, ao_info, MATS)
    # phone / far-field file: LOD2 only (default family only; same root placement and extras)
    if fam == DEFAULT_FAM:
        bpy.ops.object.select_all(action='DESELECT')
        root.select_set(True)
        e2, objs2, _ = lod_objs[2]
        e2.select_set(True)
        for o in objs2: o.select_set(True)
        glb2 = os.path.join(DATA, TV.LOD2_FILE)
        bpy.ops.export_scene.gltf(filepath=glb2, export_format='GLB', use_selection=True, export_extras=True, export_yup=True,
                                  export_apply=False, export_texcoords=True, export_normals=True, export_tangents=True,
                                  export_materials='EXPORT', export_image_format='AUTO', export_cameras=False, export_lights=False,
                                  export_animations=False)
        info['lod2_file'] = TV.postprocess(glb2, fam, TW, stats, ao_info, MATS)
        info['lod2_file']['path'] = os.path.relpath(glb2, ROOT)
        log(f'F{fam}: LOD2-only file {glb2} ({info["lod2_file"]["bytes"]} B)')
    return dict(glb=glb, stats=stats, ao=ao_info, info=info, tower=TW, lod_objs=lod_objs, root=root)


# ------------------------------------------------------------------------------------------------ renders (Cycles)
def setup_render_world(sun_brg, sun_elev):
    sc = bpy.context.scene
    world = sc.world
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes.get('Background')
    try:
        sky = nt.nodes.new('ShaderNodeTexSky')
        for t_ in ('MULTIPLE_SCATTERING', 'NISHITA', 'HOSEK_WILKIE'):
            try:
                sky.sky_type = t_; break
            except Exception:  # noqa: BLE001
                continue
        try:
            sky.sun_elevation = math.radians(sun_elev); sky.sun_rotation = math.radians(sun_brg)   # 0 = north, 90 = east (tested)
            sky.sun_disc = False
        except Exception:  # noqa: BLE001
            pass
        nt.links.new(sky.outputs['Color'], bg.inputs['Color'])
        bg.inputs['Strength'].default_value = RENDER['sky']
    except Exception as e:  # noqa: BLE001
        log('sky texture unavailable', e)
        bg.inputs['Color'].default_value = (0.5, 0.62, 0.8, 1); bg.inputs['Strength'].default_value = 0.9
    sund = bpy.data.lights.new('sun', 'SUN'); sund.energy = RENDER['sun']; sund.angle = math.radians(0.6)
    sun = bpy.data.objects.new('sun', sund); sc.collection.objects.link(sun)
    # sun direction: light travels from (brg, elev) towards the ground
    az = math.radians(sun_brg); el = math.radians(sun_elev)
    d = np.array([math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)])   # towards the sun
    rot = d_to_euler(-d)
    sun.rotation_euler = rot
    return sun


def d_to_euler(direction):
    from mathutils import Vector
    return Vector(direction).to_track_quat('-Z', 'Y').to_euler()


def add_ground():
    bpy.ops.mesh.primitive_plane_add(size=3000, location=(float(G.AXIS[0]), float(-G.AXIS[1]), GROUND_Y - 0.02))
    g = bpy.context.object; g.name = 'render_ground'
    m = bpy.data.materials.new('render_ground'); m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (*srgb2lin((128, 126, 120)), 1); b.inputs['Roughness'].default_value = 0.9
    g.data.materials.append(m)
    return g


def camera(name, loc, yaw, pitch, ortho=None, f_px=None, res=(640, 960)):
    """camera at loc (Blender world) looking along bearing yaw (deg, clockwise from north), pitched up by pitch (deg)."""
    cd = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, cd); bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = (math.radians(90.0 + pitch), 0.0, -math.radians(yaw))
    cd.clip_start = 0.5; cd.clip_end = 5000
    if ortho:
        cd.type = 'ORTHO'; cd.ortho_scale = ortho; cd.sensor_fit = 'AUTO'
    else:
        cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36.0
        cd.lens = f_px * 36.0 / res[0]
    return cam


# photo-matched views: camera_world from spec_tower.json photos (EXIF GPS), camera ~12 deg below the rim at 263 m (draw_tower
# masts note) -> 11.5 m; f in px of the 1920-px thumbnail from the rim width (t2 474 px, t3 371 px for D 15.2 at 263 m);
# rim-centre pixel read on the thumbnails (refs/cache/buildings/review_likeness, reference only)
def sun_pos(utc, lat=37.6188, lon=-122.3754):
    """sun (azimuth from north, elevation) in deg at the ISO UTC time `utc` (NOAA GML 'General Solar Position Calculations',
    ~0.1 deg; agrees with js/env/ephemeris.js to 0.7 deg at the photo times). Round 1 typed the photo suns in by hand and had
    t2 at azimuth 165 (true 137.4) and t3 at 110 (95.5)."""
    t = datetime.datetime.fromisoformat(utc)
    doy = t.timetuple().tm_yday; hr = t.hour + t.minute / 60 + t.second / 3600
    g = 2 * math.pi / 365 * (doy - 1 + (hr - 12) / 24)
    eqt = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g) - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    dec = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g)
           - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    ha = math.radians((hr * 60 + eqt + 4 * lon) / 4 - 180); la = math.radians(lat)
    z = math.acos(math.sin(la) * math.sin(dec) + math.cos(la) * math.cos(dec) * math.cos(ha))
    az = math.degrees(math.atan2(math.sin(ha), math.cos(ha) * math.sin(la) - math.tan(dec) * math.cos(la))) + 180
    return (round(az % 360, 1), round(90 - math.degrees(z), 1))


# photo times: the file names (local PDT = UTC - 7), refs/cache/buildings/review_likeness/manifest.json
PHOTO_VIEWS = {
    't2': dict(cam_world=(-527.4, 479.9), h=11.5, f1920=8200.0, size=(1920, 2560), rim_px=(930, 314), sun=sun_pos('2025-08-12T18:57:15'),
               photo='refs/cache/buildings/review_likeness/t2.jpg', credit='Famartin 2025-08-12 11:57, CC BY-SA 4.0 (reference only)'),
    't3': dict(cam_world=(-911.4, 124.4), h=11.5, f1920=6419.0, size=(1920, 1440), rim_px=(1202, 155), sun=sun_pos('2025-08-12T16:12:13'),
               photo='refs/cache/buildings/review_likeness/t3.jpg', credit='Famartin 2025-08-12 09:12, CC BY-SA 4.0 (reference only)'),
    # t4: 81 m from the axis; camera height ~20 m and f ~3040 px fitted to the rim width (493 px) and the rim-to-shaft-foot span
    't4': dict(cam_world=(-769.2, 248.6), h=20.0, f1920=3040.0, size=(1920, 2560), rim_px=(1014, 224), sun=sun_pos('2025-08-12T16:10:05'),
               photo='refs/cache/buildings/review_likeness/t4.jpg', credit='Famartin 2025-08-12 09:10, CC BY-SA 4.0 (reference only)'),
}


def render_views(res_obj, args):
    """Cycles reference renders of the default family's LOD0: the two BT-02 elevations (orthographic) and the photo-matched
    perspectives. The photo cameras are family-dependent: the focal length comes from the rim width in pixels (f1920 was
    fitted with D 15.2: f x 15.2 / D) and the camera height from the angle below the rim (h - (rim_F1 - rim)), so each family
    is seen as the photo would show it if that family were the real tower."""
    sc = bpy.context.scene
    TW = res_obj['tower']
    kD = 15.2 / TW.f['D']; dh = G.DT.FAM[1]['rim'] - TW.rim_h
    for lod, (e, objs, img) in res_obj['lod_objs'].items():
        for o in objs: o.hide_render = lod != 0
    add_ground()
    sc.view_settings.view_transform = 'AgX'
    try:
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:  # noqa: BLE001
        pass
    sc.view_settings.exposure = RENDER['exposure']
    sc.cycles.samples = args.samples
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    except Exception:  # noqa: BLE001
        pass
    sc.render.film_transparent = False
    ax = np.array([G.AXIS[0], -G.AXIS[1]])

    def W(local_xy, z):
        return (float(ax[0] + local_xy[0]), float(ax[1] + local_xy[1]), float(GROUND_Y + z))
    views = []
    # A: from the ESE (117.7) looking WNW; B: from the WNW (297.7) looking ESE (BT-02); centred on the base building span
    for nm, brg, right in (('A', 117.7, G.RIGHT_A), ('B', 297.7, G.RIGHT_B)):
        u0, u1 = G.DT.ibf_u_extent(right)
        uc = (u0 + u1) / 2
        r_loc = np.array([right[0], -right[1]])        # world (x, z) -> local (east, north)
        c = r_loc * uc
        d = G.bvec(brg)
        H = 82.0; hc = 38.0
        res = (int(args.res * 0.75), args.res)
        loc = W(c + d * 400.0, hc)
        views.append((nm, camera(f'cam_{nm}', loc, (brg + 180.0) % 360, 0.0, ortho=H, res=res), res,
                      dict(sun=(150, 40) if nm == 'A' else (255, 30), ortho_m=H, centre_u=round(uc, 3), centre_h=hc,
                           m_per_px=round(H / max(res), 5), view_bearing=(brg + 180.0) % 360)))
    for nm, pv in PHOTO_VIEWS.items():
        res = (args.res * 3 // 4, args.res) if pv['size'][1] > pv['size'][0] else (args.res, args.res * 3 // 4)
        cl = np.array([pv['cam_world'][0] - G.AXIS[0], -(pv['cam_world'][1] - G.AXIS[1])])
        rim = np.array([G.CAB[0], G.CAB[1], TW.rim_h])
        hc = pv['h'] - dh
        dv = rim - np.array([cl[0], cl[1], hc])
        yaw0 = math.degrees(math.atan2(dv[0], dv[1])); el0 = math.degrees(math.atan2(dv[2], math.hypot(dv[0], dv[1])))
        f = pv['f1920'] * kD; W0, H0 = pv['size']
        yaw = yaw0 - math.degrees(math.atan((pv['rim_px'][0] - W0 / 2) / f))
        pitch = el0 - math.degrees(math.atan((H0 / 2 - pv['rim_px'][1]) / f))
        fp = f * res[0] / W0
        views.append((nm, camera(f'cam_{nm}', W(cl, hc), yaw, pitch, f_px=fp, res=res), res,
                      dict(sun=pv['sun'], cam_world=list(pv['cam_world']), cam_h=round(hc, 2), yaw=round(yaw, 2), pitch=round(pitch, 2),
                           f_px=round(fp, 1), photo=pv['photo'], photo_credit=pv['credit'])))
    outs = {}
    sun = None
    for nm, cam, res, meta in views:
        if nm not in args.views.split(','): continue
        if sun is not None:
            bpy.data.objects.remove(sun, do_unlink=True)
        for n in list(sc.world.node_tree.nodes):
            if n.type == 'TEX_SKY': sc.world.node_tree.nodes.remove(n)
        sun = setup_render_world(*meta['sun'])
        sc.camera = cam
        sc.render.resolution_x, sc.render.resolution_y = res
        sc.render.resolution_percentage = 100
        p = os.path.join(OUT, f'tower_{nm}.png')
        sc.render.filepath = p
        t = time.time()
        bpy.ops.render.render(write_still=True)
        meta['render_s'] = round(time.time() - t, 1)
        log(f'render {nm} {res} in {meta["render_s"]} s -> {p}')
        outs[nm] = dict(path=os.path.relpath(p, ROOT), res=list(res), samples=args.samples, **meta)
    return outs


def backface_audit(res_obj, res=320):
    """orientation audit: every opaque material replaced by a shader that is grey on front faces and pure red on back faces;
    each LOD rendered alone (glass hidden: it is double-sided by design) from 6 directions (4 sides at 15 deg elevation,
    two 50-deg obliques for the roofs). Returns the share of red pixels among the building's pixels."""
    sc = bpy.context.scene
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.exposure = 0.0
    sc.cycles.samples = 4; sc.cycles.use_denoising = False
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes.get('Background'); bg.inputs['Color'].default_value = (0, 0, 0, 1)
    for n in list(sc.world.node_tree.nodes):
        if n.type == 'TEX_SKY': sc.world.node_tree.nodes.remove(n)
    m = bpy.data.materials.new('audit'); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial'); geo = nt.nodes.new('ShaderNodeNewGeometry')
    mix = nt.nodes.new('ShaderNodeMixShader'); e1 = nt.nodes.new('ShaderNodeEmission'); e2 = nt.nodes.new('ShaderNodeEmission')
    e1.inputs['Color'].default_value = (0.5, 0.5, 0.5, 1); e2.inputs['Color'].default_value = (1, 0, 0, 1)
    nt.links.new(geo.outputs['Backfacing'], mix.inputs['Fac']); nt.links.new(e1.outputs[0], mix.inputs[1])
    nt.links.new(e2.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], out.inputs['Surface'])
    ax = np.array([G.AXIS[0], -G.AXIS[1]])
    result = {}
    for lod, (e, objs, img) in res_obj['lod_objs'].items():
        for l2, (e2_, ob2, _) in res_obj['lod_objs'].items():
            for o in ob2:
                o.hide_render = (l2 != lod) or o.name.endswith('cab_glass')
        if os.environ.get('TOWER_AUDIT_SELFTEST') and lod == 0:      # flip one node: the audit must then report red pixels
            ob_t = [o for o in objs if o.name.endswith('_ibf')][0]
            ob_t.data.flip_normals()
        saved = {}
        for o in objs:
            saved[o.name] = list(o.data.materials)
            for i in range(len(o.data.materials)): o.data.materials[i] = m
        reds = []
        for k, (brg, el) in enumerate(((0, 15), (90, 15), (180, 15), (270, 15), (45, 50), (225, 50))):
            d = np.array([math.sin(math.radians(brg)) * math.cos(math.radians(el)), math.cos(math.radians(brg)) * math.cos(math.radians(el)),
                          math.sin(math.radians(el))])
            loc = (float(ax[0] + d[0] * 300), float(ax[1] + d[1] * 300), float(GROUND_Y + 36 + d[2] * 300))
            cam = camera(f'audit_{lod}_{k}', loc, (brg + 180) % 360, -el, ortho=90.0, res=(res, res))
            sc.camera = cam; sc.render.resolution_x = sc.render.resolution_y = res
            p = os.path.join(OUT, f'tower_audit_L{lod}_{k}.png'); sc.render.filepath = p
            bpy.ops.render.render(write_still=True)
            a = np.array(bpy.data.images.load(p).pixels[:]).reshape(res, res, 4)
            red = (a[..., 0] > 0.6) & (a[..., 1] < 0.2); bld = a[..., :3].sum(-1) > 0.05
            reds.append(round(float(red.sum()) / max(1, int(bld.sum())), 5))
        for o in objs:
            for i, mm in enumerate(saved[o.name]): o.data.materials[i] = mm
        result[f'LOD{lod}'] = dict(max_red_share=max(reds), per_view=reds)
        log(f'audit LOD{lod}: back-face share per view {reds}')
    return result


# ------------------------------------------------------------------------------------------------ manifest
def merge_manifest(entry):
    path = os.path.join(DATA, 'manifest.json')
    lock = path + '.lock'
    os.makedirs(DATA, exist_ok=True)
    with open(lock, 'a') as lf:                       # shared with the other groups' builders (flock; never deleted)
        fcntl.flock(lf, fcntl.LOCK_EX)
        cur = json.load(open(path)) if os.path.exists(path) else {}     # a broken file raises: never drop other keys
        cur.setdefault('_about', 'SFO Live 3D building assets (glTF 2.0, built with Blender from the verified 2-D sheets); one key '
                       'per asset group; frame ltp-nad83-2011 (x east, y up, z south, m from the ARP); see docs/research/buildings3d.md')
        cur['tower'] = entry
        tmp = path + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(cur, f, indent=1)
        os.replace(tmp, path)
        fcntl.flock(lf, fcntl.LOCK_UN)
    return path


def validate(glb):
    """Khronos glTF-Validator through tools/blender/tower_validate.mjs (if installed under refs/cache/engine/node)."""
    mods = os.path.join(ROOT, 'refs', 'cache', 'engine', 'node')
    if not os.path.exists(os.path.join(mods, 'node_modules', 'gltf-validator')):
        return dict(skipped='gltf-validator not installed (npm i --prefix refs/cache/engine/node gltf-validator@2.0.0-dev.3.10)')
    try:
        r = subprocess.run(['node', os.path.join(HERE, 'tower_validate.mjs'), glb, mods], capture_output=True, text=True, timeout=120)
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception as e:  # noqa: BLE001
        return dict(error=str(e))


def git_rev():
    try:
        r = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip()
        d = subprocess.run(['git', 'status', '--porcelain', '--', 'tools/blender', 'tools/buildings'], cwd=ROOT,
                           capture_output=True, text=True, timeout=10).stdout.strip()
        return r + ('+dirty' if d else '')
    except Exception:  # noqa: BLE001
        return 'unknown'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--family', default='all', choices=('1', '2', 'all'))
    ap.add_argument('--no-bake', action='store_true')
    ap.add_argument('--render', action='store_true')
    ap.add_argument('--samples', type=int, default=64)
    ap.add_argument('--ao-samples', type=int, default=48)
    ap.add_argument('--res', type=int, default=960)
    ap.add_argument('--no-manifest', action='store_true')
    ap.add_argument('--sun', type=float, default=RENDER['sun'])
    ap.add_argument('--sky', type=float, default=RENDER['sky'])
    ap.add_argument('--exposure', type=float, default=RENDER['exposure'])
    ap.add_argument('--views', default='A,B,t2,t3,t4')
    ap.add_argument('--audit', action='store_true', help='back-face audit renders of the default family (out/buildings3d/tower_audit_*.png)')
    args = ap.parse_args([a for a in sys.argv[1:]])
    args.res = min(args.res, 960); args.samples = min(args.samples, 64)
    RENDER.update(sun=args.sun, sky=args.sky, exposure=args.exposure)
    os.makedirs(OUT, exist_ok=True)
    tex_paths = tower_tex.make_all(os.path.join(OUT, 'tex'), clad_rgb=MATS['clad']['rgb'], slot_rgb=MATS['slot_screen']['rgb'])
    log('clad tile mean sRGB', tex_paths.get('_clad_mean'), 'slot screen tile mean sRGB', tex_paths.get('_slot_mean'))
    fams = (1, 2) if args.family == 'all' else (int(args.family),)
    results = {}
    t0 = time.time()
    # the other family first so that the session ends on the default family (the renders and the audit are of it)
    for fam in sorted(fams, key=lambda f_: f_ == DEFAULT_FAM):
        results[fam] = build_family(fam, args, tex_paths)
    renders = {}
    D_ = DEFAULT_FAM
    if args.render and D_ in results:
        renders = render_views(results[D_], args)
        renders['_family'] = f'F{D_}'
        renders['_compare'] = TV.compare_images(renders, results[D_]['tower'])
    audit = backface_audit(results[D_]) if (args.audit and D_ in results) else None
    ver = {fam: TV.verify(r['glb'], fam) for fam, r in results.items()}
    if audit: ver[D_]['backface_audit'] = audit
    for fam, r in results.items():
        ver[fam]['gltf_validator'] = validate(r['glb'])
        log(f'F{fam}: glTF-Validator', ver[fam]['gltf_validator'])
    vpath = os.path.join(OUT, 'tower_verify.json')
    json.dump({f'F{k}': v for k, v in ver.items()}, open(vpath, 'w'), indent=1)
    log('verification ->', vpath)
    for fam, v in ver.items():
        log(f'F{fam}: {v["summary"]}')
    if not args.no_manifest and len(results) == 2:
        if not renders:                     # keep the last reference renders (they do not depend on the AO bake)
            try:
                renders = json.load(open(os.path.join(DATA, 'manifest.json')))['tower'].get('renders', {})
            except Exception:  # noqa: BLE001
                renders = {}
        entry = TV.manifest_entry(results, ver, renders, args, git_rev(), round(time.time() - t0, 1))
        log('manifest ->', merge_manifest(entry))
        log('doc ->', TV.write_doc(entry, ver))
    log(f'done in {time.time() - t0:.1f} s')


if __name__ == '__main__':
    main()
