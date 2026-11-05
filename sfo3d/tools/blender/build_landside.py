# SPDX-License-Identifier: GPL-3.0-or-later
# (imports bpy: Blender's licence asks scripts that use its API to be GPL-compatible if published, docs/research/engine.md 7.3)
"""Build the 3-D landside asset (garages, AirTrain, Grand Hyatt, RCC, CAC, Superbay, United MOC) with Blender (bpy 5.0):

    flock out/.heavy.lock python3 tools/blender/build_landside.py              # geometry, textures, AO bake, export, verify, manifest
    flock out/.heavy.lock python3 tools/blender/build_landside.py --no-bake    # quick: no AO bake (occlusion textures white)
    flock out/.heavy.lock python3 tools/blender/render_landside.py            # Cycles references (separate script)

Inputs (all in the repo, read through tools/blender/landside_geom.py / landside_airtrain.py / landside_cars.py):
  tools/buildings/draw_landside.py + draw_data.py + spec_landside.json + landside_naip_measurements.json   the 2-D sheets BL-01..03
  data/sfo_airport.json     SFO Museum outlines (buildings, AirTrain guideway and stations)
  refs/cache/naip/naip_2024_world_0.5m_bgr.npy (optional)   deck / roof colours sampled from NAIP 2024 (public domain) at the
                            imaged (relief-shifted) roof positions; without it the recorded values below are used. NAIP is
                            never used as a texture.
Outputs:
  data/buildings3d/landside.glb         the asset; data/buildings3d/landside_lod2.glb (the LOD2 subtrees alone, far / phone tier)
  data/buildings3d/manifest.json        key "landside" (merged under a file lock; other groups own their keys)
  out/buildings3d/landside_tex/*.png    textures as built; out/buildings3d/landside_build.json (stats)

glTF layout: root "landside" at world (0, GROUND_Y, 0) (app frame: x east, y up, z south, metres from the ARP; GROUND_Y = 3.0,
js/geo.js); one child per building / AirTrain tile at its own origin (extras: src, spec keys, per-dimension tags, inferred /
unknown / conflicts / deviations, anchors), each with LOD0 / LOD1 / LOD2 children (extras.lod, extras.switch_m = camera
distance from THAT building node). LOD0 / LOD1 share the shell meshes and their baked AO atlas (A: parking structures, B: the
other buildings and the AirTrain); LOD2 is one joined node per building with atlas C. Parked cars: one node per (deck, shape,
colour) with EXT_mesh_gpu_instancing under LOD0 and LOD1. PBR materials (baseColor / metallic / roughness; coated glass IOR
1.9 via KHR_materials_ior), tiling detail maps on TEXCOORD_0, AO on TEXCOORD_1 (occlusionTexture.texCoord = 1).
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
import zlib

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import landside_geom as G  # noqa: E402
import landside_cars as C  # noqa: E402
import landside_tex  # noqa: E402

ROOT = G.ROOT
DATA = os.path.join(ROOT, 'data', 'buildings3d')
OUT = os.path.join(ROOT, 'out', 'buildings3d')
TEX = os.path.join(OUT, 'landside_tex')
GROUND_Y = 3.0
AO_RES = {'A': 2048, 'B': 2048, 'C': 1024}
AO_DIST = 8.0
PARKING = ('central_garage', 'garage_a', 'garage_g', 'ltp_garage_1', 'ltp_garage_2', 'rental_car_center')
T0 = time.time()

# PBR materials: sRGB base colour, metallic, roughness (+ base-colour tile, normal tile, IOR). Colours are our reading of the
# reference photos (l1-l5, a2: reference only) and NAIP 2024 for decks / roofs (factors per building, naip_colours()).
MATS = {
    'precast':        dict(rgb=(214, 210, 198), m=0.0, r=0.80, nrm=('ls_n_precast', 0.6), src='obs photo l1 (light architectural precast, square grid); colour inf'),
    'precast_band':   dict(rgb=(214, 210, 198), m=0.0, r=0.80, nrm=('ls_n_band', 0.6), src='obs photos l1 / a2 (banded core cylinder)'),
    'drum_metal':     dict(rgb=(212, 218, 226), m=0.45, r=0.38, nrm=('ls_n_drum', 0.5), src='obs photo i2 (helix drums in smooth light metal panels with long horizontal slots); colour obs i2 / inf'),
    'precast_white':  dict(rgb=(232, 231, 225), m=0.0, r=0.75, nrm=('ls_n_ribs', 0.6), src='obs photo i2 (white precast stair / elevator towers, fine horizontal ribs)'),
    'red_light':      dict(rgb=(214, 22, 18), m=0.0, r=0.40, obstruction_light=dict(colour='red', dof='06-001451', lighting='R (FAA DOF)', fixture='L-810 [inf]'),
                           src='pub FAA DOF 06-001451 lighting R (red obstruction light at the 135-ft point); fixture inf'),
    'deck_plain':     dict(rgb=(228, 228, 224), m=0.0, r=0.88, naip='deck_plain', src='obs NAIP 2024 (central-garage roof lobes without stall marks: median colour)'),
    'deck_rim':       dict(rgb=(196, 178, 146), m=0.0, r=0.90, naip='deck_rim', src='obs NAIP 2024 (beige rims / curbs round the roof lobes: median colour); nature unk'),
    'bart_panel':     dict(rgb=(226, 226, 220), m=0.0, r=0.70, nrm=('ls_n_precast', 0.5), src='obs photo a2 (white panelled BART station body); material inf'),
    'glass_bart':     dict(rgb=(255, 255, 255), m=0.0, r=0.08, ior=1.9, tex='ls_c_glassbart', src='obs photo a2 (green glazed band of the BART station)'),
    'vault_roof':     dict(rgb=(236, 238, 238), m=0.50, r=0.35, double=True, src='obs NAIP 2024 / photo a2 (white curved roof over the Garage G / BART AirTrain station)'),
    'guide_rail':     dict(rgb=(150, 154, 158), m=0.70, r=0.45, src='obs photos l1 / l5 (low galvanised guide / power rail)'),
    'running_pad':    dict(rgb=(176, 174, 166), m=0.0, r=0.85, tex='ls_c_weather', src='obs photos l1 / l5 (concrete running pads)'),
    'walkway':        dict(rgb=(150, 146, 136), m=0.0, r=0.85, tex='ls_c_weather', src='obs photo l1 (walkway between the tracks)'),
    'handrail':       dict(rgb=(168, 172, 176), m=0.70, r=0.40, double=True, src='obs photos l1 / l5 (galvanised handrails)'),
    'concrete':       dict(rgb=(188, 185, 177), m=0.0, r=0.85, nrm=('ls_n_concrete', 0.4), src='inf (cast concrete spandrels)'),
    'concrete_lt':    dict(rgb=(204, 202, 194), m=0.0, r=0.82, nrm=('ls_n_concrete', 0.4), src='obs photo l2 (LTP 2 exposed frame) / l4 (Hyatt sign pier)'),
    'concrete_board': dict(rgb=(180, 176, 166), m=0.0, r=0.88, nrm=('ls_n_board', 0.8), src='obs photo l5 (board-formed concrete)'),
    'screen':         dict(rgb=(236, 238, 238), m=0.15, r=0.55, tex='ls_c_screen', nrm=('ls_n_screen', 0.6), src='obs photo l1 (perforated metal panels, horizontal slots); reads mid-grey at a distance (photo a2)'),
    'slot':           dict(rgb=(30, 32, 34), m=0.0, r=0.30, src='obs photo l1 (dark window slots of the station block)'),
    'screen_edge':    dict(rgb=(200, 202, 202), m=0.60, r=0.45, src='inf'),
    'interior':       dict(rgb=(40, 41, 43), m=0.0, r=0.95, double=True, src='inf (shaded parking interior behind the openings)'),
    'sill':           dict(rgb=(118, 118, 114), m=0.0, r=0.90, src='inf (slab top inside the openings)'),
    'soffit':         dict(rgb=(92, 92, 90), m=0.0, r=0.90, src='inf (slab underside)'),
    'soffit_lt':      dict(rgb=(176, 176, 172), m=0.0, r=0.85, src='inf'),
    'deck':           dict(rgb=(170, 168, 162), m=0.0, r=0.90, tex='ls_c_deck', naip='deck', src='obs NAIP 2024 deck colour (factor); stall lines inf'),
    'deck_lanes':     dict(rgb=(170, 168, 162), m=0.0, r=0.90, tex='ls_c_lanes', naip='deck', src='obs NAIP 2024 deck colour; lane lines obs NAIP / spacing inf'),
    'deck_far':       dict(rgb=(160, 158, 152), m=0.0, r=0.90, naip='deck_far', src='obs NAIP 2024 deck colour incl. cars (LOD2)'),
    'coping':         dict(rgb=(206, 204, 198), m=0.0, r=0.70, double=True, src='inf'),
    'glass_hyatt':    dict(rgb=(255, 255, 255), m=0.0, r=0.08, ior=1.9, tex='ls_c_hyatt', src='obs photo l4 (saturated blue reflective unitised curtain wall, one spandrel per floor; r1 retint: photo mean (38, 113, 150))'),
    'glass_band':     dict(rgb=(255, 255, 255), m=0.0, r=0.08, ior=1.9, tex='ls_c_glassband', src='obs photo l4 (banded curved end bay)'),
    'metal_dark':     dict(rgb=(66, 69, 74), m=0.55, r=0.45, src='obs photo l4 (dark metal podium / penthouse)'),
    'cac_wall':       dict(rgb=(255, 255, 255), m=0.0, r=0.60, tex='ls_c_cac', src='inf (panels + window bands; reduced window-to-wall ratio [pub])'),
    'louvre':         dict(rgb=(255, 255, 255), m=0.45, r=0.50, tex='ls_c_louvre', nrm=('ls_n_louvre', 0.6), double=True, src='obs photo l5 (green-grey canted louvre screen)'),
    'louvre_blade':   dict(rgb=(128, 146, 140), m=0.45, r=0.45, double=True, src='obs photo l5 (green-grey blades)'),
    'ribbon':         dict(rgb=(255, 255, 255), m=0.0, r=0.12, ior=1.9, tex='ls_c_ribbon', src='obs photo l5 (ribbon windows)'),
    'hangar_wall':    dict(rgb=(216, 212, 198), m=0.25, r=0.60, nrm=('ls_n_corrugated', 0.5), src='obs photo l3 (light hangar walls); cladding inf'),
    'hangar_door':    dict(rgb=(255, 255, 255), m=0.35, r=0.50, tex='ls_c_door', nrm=('ls_n_door', 0.6), src='obs photo l3 (grey door leaves); leaves inf'),
    'hangar_roof':    dict(rgb=(176, 172, 160), m=0.25, r=0.60, nrm=('ls_n_roof', 0.5), naip='superbay', src='obs NAIP 2024 roof colour'),
    'spine_roof':     dict(rgb=(214, 214, 208), m=0.20, r=0.60, nrm=('ls_n_roof', 0.5), naip='superbay_spine', src='obs NAIP 2024 (bright spine)'),
    'spine_wall':     dict(rgb=(255, 255, 255), m=0.0, r=0.60, tex='ls_c_spine', src='inf (office floors in the spine [pub 6 levels])'),
    'fascia':         dict(rgb=(198, 196, 188), m=0.30, r=0.50, src='obs photo l3 (light roof edge)'),
    'moc_wall':       dict(rgb=(200, 202, 200), m=0.35, r=0.55, nrm=('ls_n_corrugated', 0.5), src='inf (no MOC photo)'),
    'moc_roof':       dict(rgb=(200, 200, 196), m=0.10, r=0.75, nrm=('ls_n_roof', 0.4), naip='moc', src='obs NAIP 2024 roof colour'),
    'barrel_roof':    dict(rgb=(160, 146, 120), m=0.30, r=0.55, nrm=('ls_n_roof', 0.4), naip='moc_barrel', src='obs NAIP 2024 roof colour'),
    'roof_membrane':  dict(rgb=(214, 214, 210), m=0.0, r=0.85, naip='roof', src='obs NAIP 2024 roof colour'),
    'steel':          dict(rgb=(150, 154, 158), m=0.80, r=0.40, src='inf (galvanised / painted steel)'),
    'mullion':        dict(rgb=(176, 184, 188), m=0.70, r=0.35, src='inf (aluminium frame)'),
    'sign_red':       dict(rgb=(196, 32, 32), m=0.0, r=0.50, src='obs photo l4 (red vertical sign), DOF red light'),
    'pv':             dict(rgb=(255, 255, 255), m=0.20, r=0.25, tex='ls_c_pv', src='pub (PV canopies); module layout inf'),
    'guideway':       dict(rgb=(164, 161, 152), m=0.0, r=0.88, tex='ls_c_weather', nrm=('ls_n_concrete', 0.4), src='obs photos l1 / l5 (weathered concrete, r1: was a light white)'),
    'guideway_deck':  dict(rgb=(118, 118, 114), m=0.0, r=0.88, src='obs photos l1 / l5 (dark track bed between the pads)'),
    'platform':       dict(rgb=(168, 168, 164), m=0.0, r=0.80, src='inf'),
    'station_roof':   dict(rgb=(198, 202, 206), m=0.60, r=0.40, double=True, src='obs photos l1 / l5 (light metal roofs)'),
    'station_soffit': dict(rgb=(150, 154, 158), m=0.50, r=0.50, double=True, src='inf'),
    'station_glass':  dict(rgb=(255, 255, 255), m=0.0, r=0.06, ior=1.9, tex='ls_c_glass', src='obs photos (glazed enclosures / door cabins)'),
    'perf_tower':     dict(rgb=(255, 255, 255), m=0.50, r=0.55, tex='ls_c_perf', double=True, src='obs photo l5 (perforated metal cylinder, open raked top)'),
    'car':            dict(rgb=(255, 255, 255), m=0.40, r=0.35, vcol=True, src='inf (fleet colours, landside_cars.COLOURS) - vertex colours'),
}
TEX_SCALE = {}   # none


def log(*a):
    print('[landside %6.1f s]' % (time.time() - T0), *a, flush=True)


def srgb2lin(rgb):
    c = np.asarray(rgb, float) / 255.0
    return tuple(np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).tolist())


# ------------------------------------------------------------------------------------------------ NAIP colours
def naip_colours(bldgs):
    """median NAIP 2024 sRGB of each deck / roof at its IMAGED position (true polygon + the relief shift of its height):
    parking decks with the shift the car detector used (landside_naip_measurements roof_cars.roof_shift_used), the
    Superbay with its fitted roof shift (sb_roof_shift), the North Field (CAC) with the 0.315 m/m east lean, the Hyatt with the
    ITB k(x) model, the MOC at its imaged corners. The deck median includes few cars (median), deck_far the mean."""
    sys.path.insert(0, os.path.join(ROOT, 'tools', 'buildings'))
    import draw_lib as DLb
    import draw_data as DD
    import shapely
    from shapely.geometry import Polygon
    from shapely import affinity
    if not DLb.naip_available():
        return None
    A, T = DLb._naip(); R = T['res']

    def sample(poly_w, step=2.0):
        x0, z0, x1, z1 = poly_w.bounds
        xs, zs = np.meshgrid(np.arange(x0, x1, step), np.arange(z0, z1, step))
        pts = shapely.points(xs.ravel(), zs.ravel())
        ok = shapely.contains(poly_w, pts)
        xs, zs = xs.ravel()[ok], zs.ravel()[ok]
        if not len(xs): return None
        c = np.round((xs - T['x0']) / R - 0.5).astype(int); r = np.round((zs - T['z0']) / R - 0.5).astype(int)
        bgr = np.asarray(A[r, c], float)
        return bgr[:, ::-1]
    out = {}
    by = {b.key: b for b in bldgs}
    for k in PARKING:
        b = by.get(k)
        if not b or not b.decks: continue
        d = b.decks[0]
        P = b.F.wpoly(d['poly']).buffer(-2.0)
        sh = G.LB[k]['roof_cars']['roof_shift_used']
        s = sample(affinity.translate(P, sh[0], sh[1]))
        if s is None: continue
        out['deck.' + k] = dict(rgb=np.median(s, 0).round().astype(int).tolist(), n=len(s), shift=sh)
        out['deck_far.' + k] = dict(rgb=s.mean(0).round().astype(int).tolist(), n=len(s), shift=sh)
    if 'central_garage' in by:
        b = by['central_garage']; rf = G.R1['cg_roof']; sh = tuple(rf['roof_shift'])
        for nm, key in (('deck_plain', 'lobes'), ('deck_rim', 'rims')):
            Pz = shapely.union_all([Polygon(q).buffer(-0.6) for q in rf[key]])
            s_ = sample(affinity.translate(Pz, *sh), step=1.0) if not Pz.is_empty else None
            if s_ is not None and len(s_) > 20: out[nm + '.central_garage'] = dict(rgb=np.median(s_, 0).round().astype(int).tolist(), n=len(s_), shift=sh)
    if 'superbay' in by:
        b = by['superbay']; sh = (-7.0, -7.5)
        a0, s0_, s1_, a1 = b.anchors['a']; T_ = b.anchors['t'][1]
        sl, tl = G.hdg_vec(117.83), G.hdg_vec(27.83); c = np.array([b.F.ox, b.F.oz])
        W_ = lambda a, t: tuple(c + sl * a + tl * t)
        for nm, (aa, ab) in (('superbay', (a0 + 4, s0_ - 4)), ('superbay_spine', (s0_ + 3, s1_ - 3))):
            P = Polygon([W_(aa, -T_ + 6), W_(ab, -T_ + 6), W_(ab, T_ - 6), W_(aa, T_ - 6)])
            s = sample(affinity.translate(P, *sh))
            if s is not None: out[nm + '.superbay'] = dict(rgb=np.median(s, 0).round().astype(int).tolist(), n=len(s), shift=sh)
    if 'cac' in by:
        b = by['cac']; P = b.footprint_w.buffer(-3.0); sh = (G.MOC_LEAN * b.top, 0.0)
        s = sample(affinity.translate(P, *sh))
        if s is not None: out['roof.cac'] = dict(rgb=np.median(s, 0).round().astype(int).tolist(), n=len(s), shift=sh)
    if 'grand_hyatt' in by:
        b = by['grand_hyatt']; P = b.footprint_w.buffer(-4.0); h = b.anchors['parapet_top']
        sh = (float(DD.k_x_model(P.centroid.x)) * h, 0.0)
        s = sample(affinity.translate(P, *sh))
        if s is not None: out['roof.grand_hyatt'] = dict(rgb=np.median(s, 0).round().astype(int).tolist(), n=len(s), shift=sh)
    if 'united_moc' in by:
        P = Polygon(G.MOC['moc_large_hangar']['corners_imaged']).buffer(-6.0)
        s = sample(P)
        if s is not None: out['moc.united_moc'] = dict(rgb=np.median(s, 0).round().astype(int).tolist(), n=len(s), shift='imaged corners')
        P = Polygon(G.MOC['moc_barrel_hangars']['corners_imaged']).buffer(-8.0)
        s = sample(P)
        if s is not None: out['moc_barrel.united_moc'] = dict(rgb=np.median(s, 0).round().astype(int).tolist(), n=len(s), shift='imaged corners')
    return out


# ------------------------------------------------------------------------------------------------ materials / objects
def gltf_output_group():
    grp = bpy.data.node_groups.get('glTF Material Output')
    if grp is None:
        grp = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
        grp.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
    return grp


NAIP_C = {}


def mat_variant(key, bkey):
    """per-building material key for NAIP-coloured materials ('deck.garage_a'), else the plain key."""
    spec = MATS[key]
    if spec.get('naip'):
        nk = spec['naip'] + '.' + bkey
        if nk in NAIP_C or (spec['naip'] in ('deck', 'deck_far') and bkey in PARKING):
            return f'{key}.{bkey}'
    return key


def make_material(name, atlas, tex_imgs, ao_img):
    key, _, bkey = name.partition('.')
    spec = MATS[key]
    full = name if atlas is None else f'{name}@{atlas}'
    if full in bpy.data.materials:
        return bpy.data.materials[full]
    m = bpy.data.materials.new(full)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get('Principled BSDF')
    rgb = spec['rgb']
    if spec.get('naip') and bkey:
        nk = spec['naip'] + '.' + bkey
        if nk in NAIP_C:
            rgb = tuple(NAIP_C[nk]['rgb'])
            if spec.get('tex'):              # texture base 0.80 grey: factor = colour / 0.80
                rgb = tuple(min(255, int(round(c / 0.80))) for c in rgb)
    b.inputs['Base Color'].default_value = (*srgb2lin(rgb), 1.0)
    b.inputs['Metallic'].default_value = spec['m']
    b.inputs['Roughness'].default_value = spec['r']
    b.inputs['IOR'].default_value = spec.get('ior', 1.5)
    if spec.get('ior'):
        b.inputs['Specular IOR Level'].default_value = 0.499      # exports KHR_materials_specular + _ior (see build_itb.py)
        m['ior'] = spec['ior']
    m.use_backface_culling = not spec.get('double', False)     # doubleSided only for see-through thin screens
    if spec.get('vcol'):
        ca = nt.nodes.new('ShaderNodeVertexColor'); ca.layer_name = 'Col'
        nt.links.new(ca.outputs['Color'], b.inputs['Base Color'])
    if spec.get('tex'):
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = tex_imgs[spec['tex']]
        uvn = nt.nodes.new('ShaderNodeUVMap'); uvn.uv_map = 'UV_detail'
        nt.links.new(uvn.outputs['UV'], t.inputs['Vector'])
        if rgb != (255, 255, 255):
            mul = nt.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'
            mul.inputs['Factor'].default_value = 1.0
            mul.inputs[7].default_value = (*srgb2lin(rgb), 1.0)
            nt.links.new(t.outputs['Color'], mul.inputs[6])
            nt.links.new(mul.outputs[2], b.inputs['Base Color'])
        else:
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
    if spec.get('obstruction_light'):
        m['obstruction_light'] = spec['obstruction_light']       # js/three/buildings3d.js glowKind -> 'beacon' (lit at night)
    if spec.get('naip') and bkey and (spec['naip'] + '.' + bkey) in NAIP_C:
        m['naip_rgb'] = list(NAIP_C[spec['naip'] + '.' + bkey]['rgb'])
    return m


def mesh_from_mb(name, mb, atlas, tex_imgs, ao_img, bkey, vcols=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata(mb.V, [], mb.F)
    me.update()
    nloops = sum(len(f) for f in mb.F)
    assert len(me.loops) == nloops and len(me.polygons) == len(mb.F), (name, len(me.loops), nloops)
    uv = me.uv_layers.new(name='UV_detail')
    uv.data.foreach_set('uv', np.asarray([t for f in mb.UV for t in f], np.float32).ravel())
    keys = [mat_variant(k, bkey) for k in mb.M]
    uniq = list(dict.fromkeys(keys))
    for k in uniq:
        me.materials.append(make_material(k, atlas, tex_imgs, ao_img))
    me.polygons.foreach_set('material_index', np.array([uniq.index(k) for k in keys], np.int32))
    me.polygons.foreach_set('use_smooth', np.array(mb.S, bool))
    if vcols is not None:
        ca = me.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
        cols = np.repeat(np.asarray(vcols, np.float32), [len(f) for f in mb.F], axis=0)
        ca.data.foreach_set('color', np.c_[cols, np.ones(len(cols), np.float32)].ravel())
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
    co = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    c = (co.min(0) + co.max(0)) / 2; c[2] = 0.0
    co -= c; me.vertices.foreach_set('co', co.ravel()); me.update()
    return tuple(float(x) for x in c)


def jsonable(x):
    """Blender ID properties: dicts / lists / numbers / strings only."""
    if isinstance(x, dict): return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)): return [jsonable(v) for v in x]
    if isinstance(x, (np.floating,)): return float(x)
    if isinstance(x, (np.integer,)): return int(x)
    if x is None: return 'null'
    return x


# ------------------------------------------------------------------------------------------------ cars
def car_meshes(tex_imgs):
    """{(shape, colour): (mesh LOD0, mesh LOD1)}: one material 'car', paint / glass / skirt as vertex colours."""
    out = {}
    glass, dark = (24, 28, 32), (18, 18, 18)
    for si, sh in enumerate(C.SHAPES):
        for lod in (0, 1):
            mb = C.car_mesh(sh, lod)
            for ci, (cn, rgb, _) in enumerate(C.COLOURS):
                cols = [srgb2lin({'paint': rgb, 'car_glass': glass, 'car_dark': dark}[m]) for m in mb.M]
                mb2 = G.MB(); mb2.V, mb2.F, mb2.UV, mb2.S = mb.V, mb.F, mb.UV, mb.S; mb2.M = ['car'] * len(mb.F)
                me = mesh_from_mb(f'car_{sh[0]}_{cn}_L{lod}', mb2, None, tex_imgs, None, '', vcols=cols)
                out.setdefault((si, ci), [None, None])[lod] = me
    return out


def add_cars(B, lod_empty, lod, cmeshes, cars, tag):
    groups = {}
    for (x, y, z, yaw, si, ci) in cars:
        groups.setdefault((si, ci), []).append((x, y, z, yaw))
    sc = bpy.context.scene
    n = 0
    for (si, ci), lst in sorted(groups.items()):
        me = cmeshes[(si, ci)][lod]
        e = bpy.data.objects.new(f'L{lod}_{B.key}_cars_{C.SHAPES[si][0]}_{C.COLOURS[ci][0]}', None); sc.collection.objects.link(e)
        e.parent = lod_empty
        e['src'] = 'obs/inf'; e['feature'] = 'parked cars (EXT_mesh_gpu_instancing): count / axis obs NAIP, stall positions random [inf]'
        e['lod'] = lod; e['instances'] = len(lst); e['spec'] = [f'{B.key}_roof_cars'] if B.key != 'central_garage' else ['cg_roof_cars']
        for i, (x, y, z, yaw) in enumerate(lst):
            o = bpy.data.objects.new(f'{e.name}_{i}', me); sc.collection.objects.link(o)
            o.parent = e; o.location = (x, y, z); o.rotation_euler = (0, 0, yaw)
            n += 1
    return n


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
    bpy.ops.uv.smart_project(angle_limit=math.radians(50), island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(udim_source='CLOSEST_UDIM', rotate=True, rotate_method='ANY', scale=True, margin_method='FRACTION',
                            margin=0.002, shape_method='AABB')
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
    w, h = img.size
    img.pixels.foreach_set(np.ones(w * h * 4, np.float32))
    bpy.ops.object.bake(type='AO', margin=6, margin_type='EXTEND', use_clear=False)
    for o in hide: o.hide_render = False
    for o in objs:
        o.data.uv_layers.active = o.data.uv_layers['UV_detail']
    return time.time() - t


def smooth_ao(img):
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
        mesh_tris.append((t, v, len(m['primitives'])))
    nodes = j['nodes']
    per = {}
    lods = {0: dict(tris=0, verts=0, draws=0, instanced_tris=0), 1: dict(tris=0, verts=0, draws=0, instanced_tris=0), 2: dict(tris=0, verts=0, draws=0, instanced_tris=0)}
    root = next(i for i, n in enumerate(nodes) if n.get('name') == 'landside')
    for bi in nodes[root].get('children', []):
        b = nodes[bi]; per[b['name']] = {}
        for li in b.get('children', []):
            ln = nodes[li]; nm = ln.get('name', '')
            if not nm.startswith('LOD'): continue
            lod = int(nm.split('_')[0][3:]) if nm[3:4].isdigit() else None
            tris = verts = draws = inst = 0; stack = list(ln.get('children', []))
            while stack:
                c = nodes[stack.pop()]
                if 'mesh' in c:
                    t, v, d = mesh_tris[c['mesh']]
                    ni = 1
                    ext = c.get('extensions', {}).get('EXT_mesh_gpu_instancing')
                    if ext: ni = acc[ext['attributes']['TRANSLATION']]['count']; inst += t * ni
                    else: tris += t
                    verts += v; draws += d
                stack += c.get('children', [])
            per[b['name']][lod] = dict(tris=tris, instanced_tris=inst, draws=draws)
            lods[lod]['tris'] += tris; lods[lod]['verts'] += verts; lods[lod]['draws'] += draws; lods[lod]['instanced_tris'] += inst
    imgs = []
    for im in j.get('images', []):
        bv = j['bufferViews'][im['bufferView']]
        imgs.append(dict(name=im.get('name'), mime=im.get('mimeType'), bytes=bv['byteLength']))
    mats = j.get('materials', [])
    return dict(bytes=size, generator=j['asset'].get('generator'), lods=lods, per_building=per, meshes=len(j['meshes']), nodes=len(nodes),
                materials=len(mats), materials_with_occlusion=sum(1 for m in mats if 'occlusionTexture' in m),
                occlusion_texcoords=sorted({m['occlusionTexture'].get('texCoord', 0) for m in mats if 'occlusionTexture' in m}),
                normal_textures=sum(1 for m in mats if 'normalTexture' in m), images=imgs, extensionsUsed=j.get('extensionsUsed', []),
                instanced_nodes=sum(1 for n in nodes if 'EXT_mesh_gpu_instancing' in n.get('extensions', {})))


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
        cur['landside'] = update_fn(cur.get('landside'))
        tmp = path + '.landside.tmp'
        with open(tmp, 'w') as f:
            json.dump(cur, f, indent=1)
        os.replace(tmp, path)
        fcntl.flock(lf, fcntl.LOCK_UN)
    try:
        os.remove(lock)
    except OSError:
        pass
    return path


def git_rev():
    try:
        r = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip()
        d = subprocess.run(['git', 'status', '--porcelain', '--', 'tools/blender', 'tools/buildings'], cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip()
        return r + ('+dirty' if d else '')
    except Exception:  # noqa: BLE001
        return 'unknown'


# ------------------------------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-bake', action='store_true')
    ap.add_argument('--ao-samples', type=int, default=40)
    ap.add_argument('--threads', type=int, default=3)
    ap.add_argument('--out', default=os.path.join(DATA, 'landside.glb'))
    ap.add_argument('--no-manifest', action='store_true')
    ap.add_argument('--only', default='', help='comma list of building keys (+ airtrain) for a quick partial build')
    ap.add_argument('--blend', action='store_true')
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); os.makedirs(TEX, exist_ok=True); os.makedirs(os.path.dirname(args.out), exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
    sc.render.threads_mode = 'FIXED'; sc.render.threads = args.threads
    world = bpy.data.worlds.new('world'); sc.world = world
    world.light_settings.distance = AO_DIST

    only = [s for s in args.only.split(',') if s] or None
    t = time.time()
    bldgs, tiles, at_info, lev = G.build_all(only)
    log('geometry: %d buildings, %d AirTrain tiles in %.1f s' % (len(bldgs), len(tiles), time.time() - t))
    nc = None
    try:
        nc = naip_colours(bldgs)
    except Exception as e:  # noqa: BLE001
        log('NAIP colour sampling failed:', e)
    if nc:
        NAIP_C.update(nc)
        log('NAIP colours', {k: v['rgb'] for k, v in nc.items()})

    paths = landside_tex.make_all(TEX)
    tex_imgs = {}
    for k, p in paths.items():
        im = bpy.data.images.load(p); im.name = k
        if k.startswith('ls_n_'): im.colorspace_settings.name = 'Non-Color'
        tex_imgs[k] = im
    ao_imgs = {}
    for a, res in AO_RES.items():
        im = bpy.data.images.new(f'landside_ao_{a}', res, res, alpha=False, float_buffer=False)
        im.colorspace_settings.name = 'Non-Color'; im.generated_color = (1, 1, 1, 1)
        ao_imgs[a] = im

    root = bpy.data.objects.new('landside', None); sc.collection.objects.link(root)
    root.location = (0.0, 0.0, GROUND_Y)
    root['src'] = 'mixed: per node'
    root['frame'] = 'ltp-nad83-2011; root at world (0, %.1f, 0) = the ARP at GROUND_Y; one child per building at its own origin' % GROUND_Y
    root['manifest'] = 'data/buildings3d/manifest.json#landside'
    root['drawings'] = 'docs/drawings/buildings/BL-01..03'
    root['lod_rule'] = 'per building node: show LODn when the camera distance to that node >= LODn.switch_m and < the next switch_m'
    cmeshes = car_meshes(tex_imgs)
    objs = {0: [], 1: [], 2: []}; shells = {'A': [], 'B': [], 'C': []}; cars_all = []
    stats_parts = {}; car_info = {}
    lod_empties = []
    for B in bldgs + tiles:
        be = bpy.data.objects.new(B.key, None); sc.collection.objects.link(be); be.parent = root
        be.location = (B.F.ox, -B.F.oz, 0.0)
        for k, v in jsonable(B.extras()).items():
            be[k] = v
        atlas = 'A' if B.key in PARKING else 'B'
        shared = {}
        for lod in (0, 1, 2):
            e = bpy.data.objects.new(f'LOD{lod}_{B.key}', None); sc.collection.objects.link(e); e.parent = be
            e['lod'] = lod; e['switch_m'] = G.SWITCH_M[lod]
            lod_empties.append((lod, e))
            if lod < 2:
                for part in B.shells:
                    if part.mb.empty(): continue
                    if part.name in shared:
                        me, loc = shared[part.name]
                    else:
                        me = mesh_from_mb(f'{part.name}', part.mb, atlas, tex_imgs, ao_imgs[atlas], B.key)
                        loc = recentre(me); shared[part.name] = (me, loc)
                        ob0 = None
                    ob = new_object(f'L{lod}_{part.name}', me, e, jsonable(part.extras(lod)))
                    ob.location = loc
                    objs[lod].append(ob)
                    if lod == 0: shells[atlas].append(ob)
                    stats_parts.setdefault(B.key, {}).setdefault(part.name, {})[lod] = part.mb.tris()
                for part in B.details[lod]:
                    if part.mb.empty(): continue
                    me = mesh_from_mb(f'L{lod}_{part.name}', part.mb, None, tex_imgs, None, B.key)
                    loc = recentre(me)
                    ob = new_object(f'L{lod}_{part.name}', me, e, jsonable(part.extras(lod)))
                    ob.location = loc
                    objs[lod].append(ob)
                    stats_parts.setdefault(B.key, {}).setdefault(part.name, {})[lod] = part.mb.tris()
            else:
                l2 = []
                for part in B.coarse:
                    if part.mb.empty(): continue
                    me = mesh_from_mb(f'L2_{part.name}', part.mb, 'C', tex_imgs, ao_imgs['C'], B.key)
                    ob = new_object(f'L2_{part.name}', me, e, {})
                    l2.append(ob)
                    stats_parts.setdefault(B.key, {}).setdefault(part.name, {})[2] = part.mb.tris()
                if l2:
                    bpy.ops.object.select_all(action='DESELECT')
                    for o in l2: o.select_set(True)
                    bpy.context.view_layer.objects.active = l2[0]
                    if len(l2) > 1: bpy.ops.object.join()
                    j2 = bpy.context.view_layer.objects.active
                    j2.name = f'L2_{B.key}'; j2.data.name = f'L2_{B.key}'
                    for k, v in jsonable(dict(src=B.src, feature=B.name + ' (coarse, joined)', lod=2, parts={p.name: p.extras(2) for p in B.coarse})).items():
                        j2[k] = v
                    loc = recentre(j2.data); j2.location = loc
                    objs[2].append(j2); shells['C'].append(j2)
        for di, d in enumerate(B.decks):
            cars, inf = C.place(d, B.F, G.car_layout, seed=zlib.crc32(B.key.encode()) % 1000 + di)
            car_info[B.key] = inf
            for lod in (0, 1):
                e = next(x for l_, x in lod_empties if l_ == lod and x.parent == be)
                add_cars(B, e, lod, cmeshes, cars, inf)
            cars_all += cars
    log('objects: %s; cars %d' % ({l: len(o) for l, o in objs.items()}, len(cars_all)))
    car_objs = [o for o in bpy.data.objects if '_cars_' in o.name and o.type == 'MESH']

    ao_info = {}
    if not args.no_bake:
        bpy.ops.mesh.primitive_plane_add(size=6000, location=(-1200, 700, GROUND_Y))
        ground = bpy.context.object; ground.name = 'bake_ground'
        lod1_cars = [o for o in car_objs if o.name.startswith('L1_')]
        lod0_cars = [o for o in car_objs if o.name.startswith('L0_')]
        for a, lod_objs in (('A', shells['A']), ('B', shells['B']), ('C', shells['C'])):
            if not lod_objs: continue
            t = time.time(); unwrap_ao(lod_objs); log(f'atlas {a}: UV_ao packed over {len(lod_objs)} objects in {time.time() - t:.1f} s')
            if a in ('A', 'B'):     # LOD0 scene (shells + details + LOD0 cars) occludes; LOD1 / LOD2 hidden
                hide = objs[1] + objs[2] + lod1_cars + ([] if a == 'A' else lod0_cars)
            else:                   # LOD2 alone
                hide = objs[0] + objs[1] + car_objs
            dt = bake_ao(lod_objs, hide, ao_imgs[a], args.ao_samples)
            mean, p2 = smooth_ao(ao_imgs[a])
            ao_info[a] = dict(res=AO_RES[a], bake_s=round(dt, 1), mean=round(mean, 3), p2=round(p2, 3), samples=args.ao_samples, distance_m=AO_DIST,
                              objects=len(lod_objs), ground_plane=True, cars_as_occluders=(a == 'A'))
            log(f'atlas {a}: AO {AO_RES[a]} baked in {dt:.1f} s, mean {mean:.3f}, p2 {p2:.3f}')
        bpy.data.objects.remove(ground)
    else:
        for a in shells:
            if shells[a]: unwrap_ao(shells[a])
    for a, im in ao_imgs.items():
        # JPEG (q 90): the AO is smooth and grey; PNG of a Cycles bake is 3-4 MB per 2048 atlas. KTX2 later (glb_compress.mjs)
        im.filepath_raw = os.path.join(TEX, f'landside_ao_{a}.jpg'); im.file_format = 'JPEG'
        im.save(quality=90); im.colorspace_settings.name = 'Non-Color'

    bpy.ops.object.select_all(action='DESELECT')
    root.select_set(True)
    for o in root.children_recursive: o.select_set(True)
    t = time.time()
    common = dict(export_format='GLB', use_selection=True, export_extras=True, export_yup=True, export_apply=False, export_texcoords=True,
                  export_normals=True, export_tangents=False, export_materials='EXPORT', export_image_format='AUTO', export_cameras=False,
                  export_lights=False, export_animations=False, export_gpu_instances=True, export_vertex_color='MATERIAL')
    # export to temporary files and move both into place at the end (a job killed mid-export leaves the published files intact)
    out_tmp = args.out[:-4] + '.tmp.glb'
    bpy.ops.export_scene.gltf(filepath=out_tmp, **common)
    log(f'exported {out_tmp} in {time.time() - t:.1f} s')
    lod2_path = os.path.join(os.path.dirname(args.out), os.path.basename(args.out).replace('.glb', '_lod2.glb'))
    lod2_tmp = lod2_path[:-4] + '.tmp.glb'
    bpy.ops.object.select_all(action='DESELECT')
    root.select_set(True)
    for B in bldgs + tiles:
        be = bpy.data.objects[B.key]; be.select_set(True)
        for l_, e in lod_empties:
            if l_ == 2 and e.parent == be:
                e.select_set(True)
                for o in e.children_recursive: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=lod2_tmp, **common)
    os.replace(out_tmp, args.out); os.replace(lod2_tmp, lod2_path)
    log(f'exported {args.out} + {lod2_path}')
    if args.blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'wip', 'landside.blend'))
    st = glb_stats(args.out)
    log('glb', json.dumps({k: st[k] for k in ('bytes', 'lods', 'materials', 'materials_with_occlusion', 'occlusion_texcoords', 'instanced_nodes')}))
    build = dict(built=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'), git=git_rev(), bpy=bpy.app.version_string,
                 glb=st, ao=ao_info, naip_colours=nc, parts_tris=stats_parts, cars=car_info, cars_total=len(cars_all),
                 airtrain=at_info, lod2_glb=dict(path=os.path.relpath(lod2_path, ROOT), bytes=os.path.getsize(lod2_path)),
                 buildings={B.key: jsonable(B.extras()) for B in bldgs}, seconds=round(time.time() - T0, 1), out=os.path.relpath(args.out, ROOT))
    bj = os.path.join(OUT, 'landside_build.json' if os.path.abspath(args.out) == os.path.abspath(os.path.join(DATA, 'landside.glb')) else 'wip/landside_build_wip.json')
    json.dump(build, open(bj, 'w'), indent=1, default=str)
    ver = None
    try:
        r = subprocess.run([sys.executable, os.path.join(HERE, 'verify_landside.py'), args.out], capture_output=True, text=True, timeout=1800)
        print(r.stdout[-5000:], r.stderr[-3000:])
        vp = os.path.join(OUT, 'landside_verify.json')
        if os.path.exists(vp): ver = json.load(open(vp))
    except Exception as e:  # noqa: BLE001
        log('verification failed:', e)
    if not args.no_manifest and os.path.abspath(args.out) == os.path.abspath(os.path.join(DATA, 'landside.glb')):
        import landside_manifest
        entry = landside_manifest.entry(build, ver, bldgs, tiles, MATS)
        path = merge_manifest(lambda old: landside_manifest.keep_renders(old, entry))
        log('manifest ->', path)
    log('done')


if __name__ == '__main__':
    main()
