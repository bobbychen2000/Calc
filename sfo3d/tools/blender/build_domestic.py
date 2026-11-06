# SPDX-License-Identifier: GPL-3.0-or-later
# (imports bpy: Blender's licence asks scripts that use its API to be GPL-compatible if published, docs/research/engine.md 7.3)
"""Build the 3-D asset of the domestic terminals (Harvey Milk Terminal 1 Center with Boarding Areas B and C, Terminal 2
with Boarding Area D, Terminal 3 West / East with Boarding Areas E and F) with Blender (bpy 5.0, Cycles CPU):

    flock out/.heavy.lock python3 tools/blender/build_domestic.py            # WIP build -> out/buildings3d/wip/domestic.glb
    flock out/.heavy.lock python3 tools/blender/build_domestic.py --final    # + copy to data/buildings3d/, verify, manifest
    python3 tools/blender/build_domestic.py --no-bake                        # quick geometry check (white occlusion)
    python3 tools/blender/verify_domestic.py [glb]                           # numbers only (no bpy)
    flock out/.heavy.lock python3 tools/blender/render_domestic.py           # Cycles references (separate script)

Inputs (all in the repo, read through tools/blender/dom_geom.py, which imports the 2-D sheet code):
  tools/buildings/draw_domestic.py + draw_data.py + spec_domestic.json + dom_bab_band.json / dom_baf_hub.json / dom_bab_roof.json
                          the 2-D sheets BD-01..03 (the reference)
  data/sfo_airport.json   SFO Museum outlines; data/sfo_buildings.json (curbside trim); data/sfo_stands.json (bridge doors)
  tools/blender/dom_pv.json  PV rack blocks measured on NAIP 2024 (tools/blender/dom_pv.py)
  refs/cache/naip/naip_2024_world_0.5m_bgr.npy (optional)  roof colours sampled from NAIP 2024 (public domain) at the
                          imaged (relief-shifted) roof positions; without it the recorded values in MATS are used. NAIP is
                          never used as a texture.
Outputs:
  out/buildings3d/wip/domestic.glb (+ _lod2)   work in progress (local; NOT copied to data/ unless --final)
  data/buildings3d/domestic.glb, domestic_lod2.glb, manifest.json key "domestic" (merged under a file lock)  with --final
  out/buildings3d/dom_tex/*.png (textures as built), out/buildings3d/domestic_build.json (stats)

glTF layout: root node "domestic" at world (OX, GROUND_Y, OZ) (app frame: x east, y up, z south, metres from the ARP;
GROUND_Y = 3.0 per js/geo.js), children LOD0 / LOD1 / LOD2 (extras.lod, extras.switch_m). LOD0 / LOD1 hold one node per
building and kind (L<k>_<bld>_shell / _detail / _pv; bld in T1, BA_B, BA_C, T2, BA_D, T3W, T3E, BA_E, BA_F), each recentred
on its own plan bbox (the node translation = the building's centre at grade): the complex spans ~1.3 km, so the runtime
should pick the LOD PER BUILDING from the distance to that node (extras.switch_m on the LOD groups). LOD0 and LOD1 share
the shell meshes and their baked AO (two 2048 atlases: S = T1 / BA-B / BA-C / T2, N = BA-D / T3 / BA-E / BA-F); LOD1
drops the mullion fins, door frames and rack sides. LOD2 is one joined node (whole complex) with a reduced palette and its
own 1024 atlas; also exported alone as domestic_lod2.glb (phone / far tier).
Every node carries extras {src, feature, spec (spec_domestic.json keys), dims (per-dimension tags), lod, building}.
Materials are PBR (baseColor / metallic / roughness; coated glass IOR 1.9 -> F0 0.096 via KHR_materials_ior); tiling
detail maps on TEXCOORD_0 (UV_detail, metres / tile, tools/blender/dom_tex.py); sun-independent AO baked by Cycles on
TEXCOORD_1 (UV_ao, occlusionTexture.texCoord = 1). KTX2 / meshopt compression is a later step (tools/engine/glb_compress.mjs).
"""
import argparse
import datetime
import fcntl
import json
import math
import os
import shutil
import subprocess
import sys
import time

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dom_geom as G  # noqa: E402
import dom_mesh as DM  # noqa: E402
import dom_tex  # noqa: E402

ROOT = G.ROOT
DATA = os.path.join(ROOT, 'data', 'buildings3d')
OUT = os.path.join(ROOT, 'out', 'buildings3d')
WIP = os.path.join(OUT, 'wip')
TEX = os.path.join(OUT, 'dom_tex')
GROUND_Y = 3.0                      # js/geo.js GROUND_Y
ATLAS = {'S': ('T1', 'BA_B', 'BA_C', 'T2', 'C3C'), 'N': ('BA_D', 'T3W', 'T3E', 'BA_E', 'BA_F')}
AO_RES = {'S': 2048, 'N': 2048, 'L2': 1024}
AO_DIST = 10.0                      # AO ray length, m (wall bases, parapets, wells, overhangs) [our choice, as the ITB]
T0 = time.time()

# PBR materials: sRGB base colour, metallic, roughness (+ normal tile / base tile, IOR). Colours are our reading of the
# reference photos (a1, d1, d2: reference only) and of NAIP 2024 for the roofs (per building, NAIP_ROOF below); src = tag.
GL = dict(m=0.0, ior=1.9)           # coated architectural glass: F0 0.096 (as the ITB / tower assets)
MATS = {
    'roof_membrane':  dict(rgb=(214, 216, 212), m=0.0, r=0.85, nrm=('dom_n_membrane', 0.6), src='NAIP 2024 roof colour per building (roof_<bld>) [obs, low]'),
    'panel_light':    dict(rgb=(206, 208, 209), m=0.40, r=0.45, nrm=('dom_n_panel', 0.6), src='inf (light metal panels; photos a1 / d2)'),
    'panel_dark':     dict(rgb=(92, 96, 100), m=0.30, r=0.55, nrm=('dom_n_panel', 0.5), src='inf (dark spandrel / band; photo a1)'),
    'panel_acm':      dict(rgb=(152, 154, 155), m=0.55, r=0.40, nrm=('dom_n_panel', 0.6), src='pub T3W ACM "Whetstone Gray Metallic" (CDR p.23); value inf'),
    'panel_acm_dark': dict(rgb=(44, 46, 48), m=0.45, r=0.45, nrm=('dom_n_panel', 0.5), src='pub T3W ACM "Focus Black" spandrel; value inf'),
    'panel_platinum': dict(rgb=(192, 194, 196), m=0.55, r=0.40, nrm=('dom_n_panel', 0.6), src='pub t3e.facade (platinum metal panels); value inf'),
    'service':        dict(rgb=(104, 106, 108), m=0.10, r=0.75, nrm=('dom_n_panel', 0.4), src='inf (apron-level service walls, doors not modelled; photo a1 dark base)'),
    'fascia':         dict(rgb=(228, 229, 229), m=0.20, r=0.40, nrm=('dom_n_panel', 0.4), src='inf (light roof edge; photos a1 / d1)'),
    'coping':         dict(rgb=(200, 202, 204), m=0.50, r=0.40, src='inf'),
    'soffit':         dict(rgb=(176, 178, 178), m=0.20, r=0.55, nrm=('dom_n_panel', 0.4), src='inf'),
    'concrete':       dict(rgb=(168, 166, 160), m=0.0, r=0.85, src='inf (curb sidewalk, well bridges)'),
    'penthouse_corr': dict(rgb=(202, 204, 206), m=0.50, r=0.45, nrm=('dom_n_corr', 0.8), src='pub T3E penthouse "light grey perforated corrugated metal"; value inf'),
    'pv':             dict(rgb=(34, 42, 64), m=0.20, r=0.25, tex='dom_c_pv', nrm=('dom_n_pv', 0.5), src='obs NAIP 2024 rack extents (dom_pv.json); module look inf'),
    'planting':       dict(rgb=(84, 104, 66), m=0.0, r=0.95, src='obs NAIP (green roof wells, BA-B) [pub "roof wells"]; value inf'),
    'door_dark':      dict(rgb=(46, 50, 54), m=0.30, r=0.50, src='inf (bridge door leaf)'),
    'mullion':        dict(rgb=(170, 175, 180), m=0.60, r=0.40, src='inf (aluminium fins / frames)'),
    'mullion_dark':   dict(rgb=(58, 62, 66), m=0.60, r=0.40, src='pub t3w.materials "vertical mullion fins (dark gray metallic)"; T1: obs photo d1 dark mullions'),
    'fascia_plain':   dict(rgb=(236, 237, 237), m=0.0, r=0.45, src='obs photo d1 (white "1" of the sign)'),
    'lettering':      dict(rgb=(20, 22, 24), m=0.10, r=0.55, src='obs photo d1 ("Harvey Milk Terminal / Terminal 1": near-black, review r2); font inf'),
    'glass_canopy':   dict(rgb=(188, 200, 200), m=0.0, r=0.30, src='pub t1c canopy (glass); reads light grey-green from above and below '
                             '(photo d1; review r1: the coated dark glass read as a thin dark line): laminated / fritted, uncoated F0 0.04, rough; value inf'),
    'glass_sky':      dict(rgb=(72, 88, 98), r=0.06, src='obs NAIP skylights; glass inf', **GL),
    'glass_ec':       dict(rgb=(58, 74, 86), r=0.05, tex='dom_c_glass_ec', nrm=('dom_n_curtain24', 0.5),
                           src='pub bab.glazing (electrochromic); per-pane tint states (dom_tex.EC_STATES, review r1) inf', **GL),
    'glass_lowe':     dict(rgb=(66, 82, 92), r=0.05, tex='dom_c_glass_lowe', nrm=('dom_n_curtain', 0.5), src='inf (clerestory / lantern glass)', **GL),
    'glass_tint':     dict(rgb=(40, 54, 58), r=0.05, tex='dom_c_glass_tint', nrm=('dom_n_curtain', 0.5), src='unk (gate-room glass not described: generic tint)', **GL),
    'glass_clear':    dict(rgb=(30, 36, 40), r=0.04, tex='dom_c_glass_clear', nrm=('dom_n_curtain', 0.5), src='obs photo a1 (BA-E end wall, dark clear glass)', **GL),
    'glass_lobby':    dict(rgb=(112, 120, 122), r=0.06, tex='dom_c_glass_lobby', nrm=('dom_n_curtain', 0.5),
                           src='obs photo d1 (T1 Center clear glass under the canopy: the lit hall seen through, mid-grey); value inf '
                               '(as the ITB glass_hall; review r1)', **GL),
    'unit':           dict(rgb=(178, 182, 184), m=0.45, r=0.50, nrm=('dom_n_panel', 0.5),
                           src='inf (rooftop mechanical units: painted / galvanised metal casings; extents obs NAIP 2024, dom_roofobs.json)'),
    'unit_top':       dict(rgb=(150, 154, 156), m=0.30, r=0.60, src='inf (unit tops: fans / grilles read darker than the casing)'),
    'glass_frit_grey': dict(rgb=(110, 118, 122), r=0.12, tex='dom_c_frit_grey', nrm=('dom_n_curtain', 0.4), src='pub bae.facade "clear glass with grey frit"; pattern inf', **GL),
    'glass_frit_green': dict(rgb=(165, 186, 172), m=0.0, r=0.22, tex='dom_c_frit_green', src='pub t1c.landside_facade (fritted glass); green obs photo d1; '
                             'the ceramic frit dominates: uncoated F0 0.04, rougher; pattern inf'),
    'glass_t3w':      dict(rgb=(98, 114, 124), r=0.08, tex='dom_c_t3w', nrm=('dom_n_t3w', 0.5), src='pub t3w.materials (fritted IGU window wall); module unk', **GL),
    'glass_c3c':      dict(rgb=(26, 40, 35), r=0.05, tex='dom_c_glass_c3c', nrm=('dom_n_c3c', 0.5),
                           src='C3C office curtain wall (review r2): "Dynamic glazing" [pub HOK]; storey-height panes with staggered mullions, '
                               'very dark green glass, light frames [obs photo a1, low]; pane widths inf', **GL),
    'louvre':         dict(rgb=(72, 76, 82), m=0.40, r=0.50, nrm=('dom_n_louvre', 0.8),
                           src='C3C penthouse louvre band (review r2): dark grey [obs photo a1, low]; blades inf'),
}
# LOD2 (far / phone): reduced palette, no detail maps (they average out at > 1.3 km); per-building roofs kept
L2_MAP = {'glass_ec': 'glass_tint', 'glass_lowe': 'glass_tint', 'glass_clear': 'glass_tint', 'glass_sky': 'glass_tint',
          'glass_canopy': 'glass_tint', 'glass_t3w': 'glass_tint', 'coping': 'panel_light', 'fascia': 'panel_light', 'mullion': 'panel_light',
          'concrete': 'panel_light', 'panel_platinum': 'panel_light', 'panel_acm': 'panel_light', 'penthouse_corr': 'panel_light',
          'soffit': 'panel_dark', 'door_dark': 'panel_dark', 'panel_acm_dark': 'panel_dark', 'planting': 'planting', 'lettering': 'panel_dark',
          'unit': 'panel_light', 'glass_lobby': 'glass_lobby', 'louvre': 'panel_dark'}
LEAN_OF = {'BA_B': 'B', 'BA_C': 'C', 'BA_D': 'D', 'BA_E': 'E', 'BA_F': 'F', 'T1': 'BC', 'T2': 'CD', 'T3W': 'EF', 'T3E': 'EF', 'C3C': None}
ROOF_CAP = 215                      # sRGB cap of a NAIP roof colour: NAIP saturates on the white membranes (>= 245); aged white
                                    # single-ply solar reflectance ~0.65-0.70 -> base colour <= sRGB 215 (linear 0.68) [inf]


def log(*a):
    print('[dom %6.1f s]' % (time.time() - T0), *a, flush=True)


def srgb2lin(rgb):
    c = np.asarray(rgb, float) / 255.0
    return tuple(np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).tolist())


# ------------------------------------------------------------------------------------------------ NAIP roof colours
def naip_colours(W):
    """median NAIP 2024 sRGB of each building's roof membrane at its IMAGED position: grid points (2.5 m) 2 m inside the
    roof decks, off the deck holes (wells, skylights, drums, lantern ...) and the PV blocks (+1.5 m), shifted east by the
    pier's NAIP 2024 relief (draw_data.dom_lean x the roof height; halls: the mean of the adjoining piers)."""
    sys.path.insert(0, os.path.join(ROOT, 'tools', 'buildings'))
    import draw_lib as DL
    import draw_data as DD
    from shapely.geometry import Point
    from shapely.ops import unary_union
    import shapely.prepared
    if not DL.naip_available():
        return None
    A, T = DL._naip(); R = T['res']
    lean = {k: float(DD.dom_lean(k)[0][0]) for k in 'BCDEF'}
    pv = unary_union([q for r in (G.PV or {}).get('regions', {}) for q in G.pv_block_outlines(r)]) if G.PV else None
    us = unary_union([q for q, _, _ in G.roof_units(W, 0)]) if G.ROOFOBS else None
    out = {}
    for bld in G.BLD_INFO:
        k = float(np.mean([lean[c] for c in LEAN_OF[bld]])) if LEAN_OF.get(bld) else None
        pts = []
        for s in W.S:
            if s.bld != bld or not s.top or s.style in ('drum', 'lantern', 'monitor', 'penthouse', 'walk', 'vest'): continue
            g = s.roof.buffer(-2.0, join_style=2)
            if s.holes: g = g.difference(unary_union(s.holes).buffer(1.0))
            if pv is not None: g = g.difference(pv.buffer(1.5))
            if us is not None and not us.is_empty: g = g.difference(us.buffer(1.5))
            if g.is_empty: continue
            kk = k if k is not None else G.lean_x(G.Wp(*g.centroid.coords[0])[0])
            gp = shapely.prepared.prep(g)
            x0, y0, x1, y1 = g.bounds
            for X in np.arange(x0, x1, 2.5):
                for Y in np.arange(y0, y1, 2.5):
                    if not gp.contains(Point(X, Y)): continue
                    x, z = G.Wp(X, Y)
                    c = int(round((x + kk * s.h - T['x0']) / R - 0.5)); r = int(round((z - T['z0']) / R - 0.5))
                    if 0 <= r < A.shape[0] and 0 <= c < A.shape[1]:
                        b_, g_, r_ = A[r, c]
                        pts.append((int(r_), int(g_), int(b_)))
        if len(pts) < 30: continue
        P = np.array(pts, float)
        lum = P.mean(1)
        P = P[lum >= np.percentile(lum, 35)]          # membrane, not shadows / equipment / dirt (upper 65 %)
        rgb = np.median(P, 0)
        if rgb.max() > ROOF_CAP: rgb = rgb * ROOF_CAP / rgb.max()
        out[bld] = dict(rgb=[int(round(v)) for v in rgb], n=len(pts), lean_m_per_m=round(k if k is not None else G.lean_x(-812.0), 3),
                        method='NAIP 2024 median of the upper 65 pct (luminance) at the imaged deck points, 2.5 m grid, 2 m inside, '
                               'off holes / PV; capped at sRGB ' + str(ROOF_CAP))
    return out


# ------------------------------------------------------------------------------------------------ materials / objects
def gltf_output_group():
    grp = bpy.data.node_groups.get('glTF Material Output')
    if grp is None:
        grp = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
        grp.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
    return grp


def spec_of(key):
    if key.startswith('roof_'):
        s = dict(MATS['roof_membrane']); s['rgb'] = ROOF_RGB.get(key[5:], MATS['roof_membrane']['rgb']); return s
    return MATS[key]


ROOF_RGB = {}


def make_material(key, atlas, tex_imgs, ao_img, lod2=False):
    spec = dict(spec_of(key))
    name = key if atlas is None else f'{key}@{atlas}'
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    if lod2:
        spec.pop('nrm', None)
        if spec.pop('tex', None) and key.startswith('glass'):
            pass
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
    m.use_backface_culling = True       # single-sided (doubleSided false): every face is wound outwards (back-face QA)
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
    # close-out r3 (buildings-5): no occlusion texture on GLASS. The baked AO (cosine-weighted, 10-m rays) is a diffuse
    # visibility; three.js applies a material's aoMap to the indirect diffuse AND, through its specular occlusion, to the IBL
    # reflection that makes a curtain wall read - the BA-B panes under the 2.3-m overhang (AO 0.59-0.65 at their vertices) came
    # out ~0.6 x darker in the app, while Cycles ignores the glTF occlusion (the app / Cycles disagreement of review r2). The
    # image node stays (the active bake target every material on a baked object needs); only the glTF Occlusion link is left out.
    if ao_img is not None:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = ao_img; t.name = 'AO_BAKE'
        uva = nt.nodes.new('ShaderNodeUVMap'); uva.uv_map = 'UV_ao'
        nt.links.new(uva.outputs['UV'], t.inputs['Vector'])
        if not key.startswith('glass'):
            sep = nt.nodes.new('ShaderNodeSeparateColor')
            g = nt.nodes.new('ShaderNodeGroup'); g.node_tree = gltf_output_group()
            nt.links.new(t.outputs['Color'], sep.inputs['Color'])
            nt.links.new(sep.outputs['Red'], g.inputs['Occlusion'])
        for n in nt.nodes: n.select = False
        t.select = True; nt.nodes.active = t
    m['src'] = spec['src']
    return m


def remap(mats, bld, lod2):
    out = []
    for k in mats:
        if k == 'roof_membrane': k = 'roof_' + bld
        if lod2: k = L2_MAP.get(k, k)
        out.append(k)
    return out


def mesh_from_mb(name, mb, bld, atlas, tex_imgs, ao_img, lod2=False):
    me = bpy.data.meshes.new(name)
    me.from_pydata(mb.V, [], mb.F)
    me.update()
    nloops = sum(len(f) for f in mb.F)
    assert len(me.loops) == nloops and len(me.polygons) == len(mb.F), (name, len(me.loops), nloops)
    ms = remap(mb.M, bld, lod2)
    textured = any(spec_of(k).get('tex') or spec_of(k).get('nrm') for k in set(ms))
    if textured or atlas:
        # UV_detail only where a material samples a tiling map (constant-colour detail meshes - fins, frames - carry none)
        uv = me.uv_layers.new(name='UV_detail')
        uv.data.foreach_set('uv', np.asarray([t for f in mb.UV for t in f], np.float32).ravel())
    keys = list(dict.fromkeys(ms))
    for k in keys:
        me.materials.append(make_material(k, atlas, tex_imgs, ao_img, lod2))
    me.polygons.foreach_set('material_index', np.array([keys.index(k) for k in ms], np.int32))
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
    """move the mesh origin to its plan bbox centre at grade: smaller local coordinates (quantization) and a per-building
    LOD distance reference."""
    co = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    c = (co.min(0) + co.max(0)) / 2; c[2] = 0.0
    co -= c; me.vertices.foreach_set('co', co.ravel()); me.update()
    return tuple(float(x) for x in c)


SIGN_FONT = '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'   # SIL OFL 1.1 (glyph outlines baked into the mesh)
# review r2 (finding 4): sign sizes / heights measured on photo d1 with its solved camera (render_domestic.view_d1: the
# facade scale 48.8 px/m at the sign from the canopy line -> glass head span, 7.85 m): line 1 bbox incl. the descender 1.41 m,
# 14.0 m wide, centre 14.03 m above the apron (= canopy soffit + 5.15); line 2 "Terminal" cap height 0.79 m, 4.15 m wide,
# the disc 1.10 m with the flagged white "1" (0.66 of the disc), centre 12.10 m (= soffit + 3.22) [obs photo d1, low].
# Typeface: the real one (a humanist semi-bold sans) is not identified -> Liberation Sans Bold, 0.93 horizontal scale (it is
# ~7 % wider than the photo's letters at the same height) [inf]
SIGN = dict(l1_h=1.41, l1_z=5.15, l2_h=0.79, l2_z=3.22, disc_d=1.10, one_k=0.66, x_scale=0.93)


def lettering_t1(parent, lod, W):
    """'Harvey Milk Terminal' / 'Terminal 1' on the T1 Center landside face (photo d1; BD-03 view 1 signage zone on the
    east run of the developed face) [obs photo d1 text, position, sizes (review r2); font inf]. Placed on the longest
    landside facade edge of the west run (BD-03: the right-hand run looking SE), centred, 0.28 m in front of the glass,
    0.06 m deep."""
    s = next(o for o in W.S if o.key == 'T1_hall')
    best = None
    for ring in DM.rings_of(s.poly):
        for i in range(len(ring)):
            a, b = np.array(ring[i]), np.array(ring[(i + 1) % len(ring)])
            L = float(np.hypot(*(b - a)))
            if L < 20 or not G.is_landside(tuple(a), tuple(b)): continue
            mx, mz = G.Wp(*((a + b) / 2))
            if mx > -880: continue                 # the WEST run of the face (BD-03 view 1 right-hand run, looking SE)
            if best is None or L > best[2]: best = (a, b, L)
    if best is None: return None
    a, b, L = best
    d = (b - a) / L; n = np.array([d[1], -d[0]])
    import bmesh

    fnt = bpy.data.fonts.load(SIGN_FONT, check_existing=True) if os.path.exists(SIGN_FONT) else None

    def text_mesh(txt, height, xs=SIGN['x_scale']):
        """Liberation Sans Bold (review r2: the built-in regular font read thin and grey, and its "1" is a plain bar) -> (co
        (x along, y up, z out), mesh) with the bbox scaled to `height` (x by xs more) and centred."""
        cu = bpy.data.curves.new('t1_txt', 'FONT')
        if fnt is not None: cu.font = fnt
        cu.body = txt; cu.align_x = 'CENTER'; cu.size = 1.0; cu.extrude = 0.03
        tmp = bpy.data.objects.new('tmp_text', cu); bpy.context.scene.collection.objects.link(tmp)
        dg = bpy.context.evaluated_depsgraph_get()
        me_ = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
        bpy.data.objects.remove(tmp); bpy.data.curves.remove(cu)
        co = np.zeros(len(me_.vertices) * 3, np.float32); me_.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
        lo, hi = co.min(0), co.max(0)
        sc = height / (hi[1] - lo[1])
        co[:, 0] = (co[:, 0] - 0.5 * (lo[0] + hi[0])) * sc * xs; co[:, 1] = (co[:, 1] - 0.5 * (lo[1] + hi[1])) * sc
        return co, me_

    parts = []          # (co, mesh, (u0, zc, out), material index)
    # (text, bbox height, centre height): SIGN (photo d1, review r2); line 2 = "Terminal" + the white flagged "1" in a dark
    # disc, the group centred under line 1 (photo d1)
    co1, m1 = text_mesh('Harvey Milk Terminal', SIGN['l1_h']); parts.append((co1, m1, (0.0, G.T1_CANOPY_H + SIGN['l1_z'], 0.28), 0))
    h2 = SIGN['l2_h']
    co2, m2 = text_mesh('Terminal', h2)
    w2 = np.ptp(co2[:, 0]); R_ = SIGN['disc_d'] / 2; gap = 0.30 * h2
    grp_w = w2 + gap + 2 * R_
    u_t = -grp_w / 2 + w2 / 2; parts.append((co2, m2, (u_t, G.T1_CANOPY_H + SIGN['l2_z'], 0.28), 0))
    u_d = grp_w / 2 - R_
    bm = bmesh.new()
    seg = bmesh.ops.create_circle(bm, cap_ends=True, radius=R_, segments=32)
    bmesh.ops.extrude_face_region(bm, geom=[f for f in bm.faces])
    # extrude along +z by 0.03 (the duplicated cap is selected: move it)
    top = [v for v in bm.verts if v.is_valid][len(bm.verts) // 2:]
    for v in top: v.co.z += 0.03
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    topf = max(bm.faces, key=lambda f: f.calc_center_median().z)
    if topf.normal.z < 0: bmesh.ops.reverse_faces(bm, faces=list(bm.faces))     # outward (back-face QA)
    md = bpy.data.meshes.new('t1_disc'); bm.to_mesh(md); bm.free()
    cod = np.zeros(len(md.vertices) * 3, np.float32); md.vertices.foreach_get('co', cod); cod = cod.reshape(-1, 3)
    parts.append((cod, md, (u_d, G.T1_CANOPY_H + SIGN['l2_z'], 0.28), 0))
    co3, m3 = text_mesh('1', SIGN['one_k'] * SIGN['disc_d'], xs=1.0); parts.append((co3, m3, (u_d, G.T1_CANOPY_H + SIGN['l2_z'], 0.315), 1))
    c0 = (a + b) / 2
    bm = bmesh.new(); mids = []
    for co, me_, (u0, zc, out), mi in parts:
        P = np.zeros_like(co)
        P[:, 0] = c0[0] + (co[:, 0] + u0) * d[0] + (co[:, 2] + out) * n[0]
        P[:, 1] = c0[1] + (co[:, 0] + u0) * d[1] + (co[:, 2] + out) * n[1]
        P[:, 2] = zc + co[:, 1]
        me_.vertices.foreach_set('co', P.astype(np.float32).ravel())
        me_.update()
        mids += [mi] * len(me_.polygons)          # (a mesh without material slots clamps material_index: set after the join)
        bm.from_mesh(me_)
        bpy.data.meshes.remove(me_)
    me = bpy.data.meshes.new(f'L{lod}_T1_lettering'); bm.to_mesh(me); bm.free()
    while me.uv_layers: me.uv_layers.remove(me.uv_layers[0])
    me.materials.clear(); me.materials.append(make_material('lettering', None, {}, None)); me.materials.append(make_material('fascia_plain', None, {}, None))
    me.polygons.foreach_set('material_index', np.array(mids, np.int32))
    me.update()
    c = recentre(me)
    ob = new_object(me.name, me, parent, dict(src='obs', building='T1', lod=lod, feature='T1 Center landside sign "Harvey Milk Terminal / Terminal 1"',
                                              spec=['t1c.landside_facade'],
                                              dims=dict(text_height_1=G.tagdim(SIGN['l1_h'], 'obs', 'photo d1 with its solved camera (review r2; incl. the descender), low'),
                                                        text_height_2=G.tagdim(SIGN['l2_h'], 'obs', 'photo d1 cap height (review r2), low'),
                                                        disc=G.tagdim(SIGN['disc_d'], 'obs', 'photo d1 (review r2), low'),
                                                        centre_heights=G.tagdim('%.2f / %.2f' % (G.T1_CANOPY_H + SIGN['l1_z'], G.T1_CANOPY_H + SIGN['l2_z']), 'obs',
                                                                                'photo d1 (review r2) above the curb placeholder'),
                                                        position=G.tagdim('west run of the landside face, upper tier', 'obs', 'photo d1 / BD-03 view 1'),
                                                        font=G.tagdim('Liberation Sans Bold (SIL OFL 1.1), x 0.93', 'inf', 'real typeface not identified'))))
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
                            margin=0.002, shape_method='CONCAVE')
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
    # the atlas starts white and is not cleared: texels outside the islands (+ margins) stay unoccluded, so the mip levels
    # do not bleed black into the island edges at a distance
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
        mesh_tris.append((t, v, len(m['primitives'])))
    nodes = j['nodes']
    lods = {}
    for i, n in enumerate(nodes):
        nm = n.get('name', '')
        if nm in ('LOD0', 'LOD1', 'LOD2'):
            tris = verts = prims = 0; stack = list(n.get('children', []))
            while stack:
                c = nodes[stack.pop()]
                if 'mesh' in c:
                    tris += mesh_tris[c['mesh']][0]; verts += mesh_tris[c['mesh']][1]; prims += mesh_tris[c['mesh']][2]
                stack += c.get('children', [])
            lods[nm] = dict(tris=tris, verts=verts, draw_calls=prims)
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
        cur['domestic'] = update_fn(cur.get('domestic'))
        tmp = path + '.domestic.tmp'
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
        d = subprocess.run(['git', 'status', '--porcelain', '--', 'tools/blender', 'tools/buildings'], cwd=ROOT,
                           capture_output=True, text=True, timeout=10).stdout.strip()
        return r + ('+dirty' if d else '')
    except Exception:  # noqa: BLE001
        return 'unknown'


def export(path, sel_roots):
    bpy.ops.object.select_all(action='DESELECT')
    for r in sel_roots:
        r.select_set(True)
        for o in r.children_recursive: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_extras=True, export_yup=True,
                              export_apply=False, export_texcoords=True, export_normals=True, export_tangents=False,
                              export_materials='EXPORT', export_image_format='AUTO', export_cameras=False, export_lights=False,
                              export_animations=False)


# ------------------------------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-bake', action='store_true')
    ap.add_argument('--ao-samples', type=int, default=48)
    ap.add_argument('--threads', type=int, default=3)
    ap.add_argument('--final', action='store_true', help='copy the build to data/buildings3d/, verify and write the manifest')
    ap.add_argument('--no-manifest', action='store_true')
    ap.add_argument('--blend', action='store_true', help='also save out/buildings3d/wip/domestic.blend')
    args = ap.parse_args()
    for d in (OUT, WIP, TEX, DATA): os.makedirs(d, exist_ok=True)
    out_glb = os.path.join(WIP, 'domestic.glb'); out_l2 = os.path.join(WIP, 'domestic_lod2.glb')

    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
    sc.render.threads_mode = 'FIXED'; sc.render.threads = args.threads
    world = bpy.data.worlds.new('world'); sc.world = world
    world.light_settings.distance = AO_DIST

    # ---- geometry (all three LODs first: the roof colours need the solids)
    built = {}
    for lod in (0, 1, 2):
        t = time.time(); built[lod] = G.build(lod); log(f'LOD{lod} geometry in {time.time() - t:.1f} s')
    W0 = built[0][1]; info0 = built[0][2]

    # ---- roof colours from NAIP (public domain; colour only)
    nc = None
    try:
        nc = naip_colours(W0)
    except Exception as e:  # noqa: BLE001
        log('NAIP colour sampling failed:', e)
    for bld in G.BLD_INFO:
        ROOF_RGB[bld] = tuple(nc[bld]['rgb']) if nc and bld in nc else MATS['roof_membrane']['rgb']
    log('NAIP roof colours', {k: v for k, v in ROOF_RGB.items()})

    # ---- textures
    paths = dom_tex.make_all(TEX)
    tex_imgs = {}
    for k, p in paths.items():
        im = bpy.data.images.load(p); im.name = k
        if k.startswith('dom_n_'): im.colorspace_settings.name = 'Non-Color'
        tex_imgs[k] = im
    ao_imgs = {}
    for a, res in AO_RES.items():
        im = bpy.data.images.new(f'dom_ao_{a}', res, res, alpha=False, float_buffer=False)
        im.colorspace_settings.name = 'Non-Color'
        im.generated_color = (1, 1, 1, 1)
        ao_imgs[a] = im
    atlas_of = {b: a for a, bs in ATLAS.items() for b in bs}

    # ---- hierarchy
    root = bpy.data.objects.new('domestic', None); sc.collection.objects.link(root)
    root.location = (G.OX, -G.OZ, GROUND_Y)
    root['src'] = 'mixed: per node'
    root['frame'] = 'ltp-nad83-2011; root at world (x %.3f, y %.1f, z %.3f) = centre of the domestic complex bbox at GROUND_Y' % (G.OX, GROUND_Y, G.OZ)
    root['manifest'] = 'data/buildings3d/manifest.json#domestic'
    root['drawings'] = 'docs/drawings/buildings/BD-01..03'
    root['lod_note'] = ('LOD0 / LOD1: one node per building and kind (L<k>_<bld>_<kind>, extras.building); choose the LOD per building '
                        'from the camera distance to that node; LOD2: one joined node (whole complex)')
    lod_empties, objs, shells = {}, {0: [], 1: [], 2: []}, {'S': [], 'N': [], 'L2': []}
    shared, stats_parts = {}, {}
    for lod in (0, 1, 2):
        e = bpy.data.objects.new(f'LOD{lod}', None); sc.collection.objects.link(e); e.parent = root
        e['lod'] = lod; e['switch_m'] = G.SWITCH_M[lod]
        e['switch_note'] = ('show this LOD when the camera is at least switch_m from the building node (LOD2: from the root) and below '
                            'the next LOD\'s switch_m')
        lod_empties[lod] = e
        P = built[lod][0]
        for bld, parts in P.items():
            for part in parts:
                # LOD0 / LOD1: shells on the S / N atlas, details without AO; LOD2: everything on the L2 atlas (joined below)
                atlas = 'L2' if lod == 2 else (atlas_of[bld] if part.kind == 'shell' else None)
                if part.kind == 'shell' and lod == 1 and part.name in shared:
                    me, loc = shared[part.name]
                else:
                    me = mesh_from_mb(f'L{lod}_{part.name}', part.mb, bld, atlas, tex_imgs, ao_imgs[atlas] if atlas else None, lod2=(lod == 2))
                    loc = recentre(me)
                    if part.kind == 'shell' and lod == 0: shared[part.name] = (me, loc)
                ex = part.extras(lod); ex['building'] = bld
                ob = new_object(f'L{lod}_{part.name}', me, e, ex)
                ob.location = loc
                objs[lod].append(ob)
                if atlas and lod != 1:
                    shells[atlas].append(ob)
                stats_parts.setdefault(part.name, {})[lod] = part.mb.tris()
        if lod == 0:
            ob = lettering_t1(e, 0, W0)
            if ob is not None:
                objs[0].append(ob); stats_parts['T1_lettering'] = {0: len(ob.data.polygons)}
    # (LOD1 shells are the LOD0 meshes: only the LOD0 shell objects are in the S / N bakes)
    log('objects built', {l: len(o) for l, o in objs.items()}, {a: len(v) for a, v in shells.items()})
    # LOD2: all parts joined into one node -> one primitive per material; the per-part tags move into extras.parts
    l2 = objs[2]
    parts2 = {p.name: dict(p.extras(2), building=b) for b, ps in built[2][0].items() for p in ps}
    bpy.ops.object.select_all(action='DESELECT')
    for o in l2: o.select_set(True)
    bpy.context.view_layer.objects.active = l2[0]
    bpy.ops.object.join()
    j2 = bpy.context.view_layer.objects.active
    for k in list(j2.keys()): del j2[k]
    j2.name = 'L2_domestic'; j2.data.name = 'L2_domestic'
    j2['src'] = 'mixed: see parts'; j2['feature'] = 'coarse shell of the domestic complex: halls, piers, roof features, PV (joined)'
    j2['lod'] = 2; j2['parts'] = parts2; j2['building'] = 'all'
    objs[2] = [j2]; shells['L2'] = [j2]
    log('LOD2 joined: %d material slots' % len(j2.data.materials))

    # ---- AO
    ao_info = {}
    if not args.no_bake:
        bpy.ops.mesh.primitive_plane_add(size=4000, location=(0, 0, 0))
        ground = bpy.context.object; ground.name = 'bake_ground'
        for a in ('S', 'N', 'L2'):
            t = time.time(); unwrap_ao(shells[a]); log(f'atlas {a}: UV_ao packed over {len(shells[a])} objects in {time.time() - t:.1f} s')
            if a == 'L2':
                hide = objs[0] + objs[1]
            else:
                hide = objs[1] + objs[2]          # LOD0 shells + details of all buildings occlude (neighbours included)
            dt = bake_ao(shells[a], [o for o in hide if o not in shells[a]], ao_imgs[a], args.ao_samples)
            mean, p2 = smooth_ao(ao_imgs[a])
            ao_info[a] = dict(res=AO_RES[a], lods=[0, 1] if a != 'L2' else [2], buildings=list(ATLAS.get(a, ('all',))), bake_s=round(dt, 1),
                              mean=round(mean, 3), p2=round(p2, 3), samples=args.ao_samples, distance_m=AO_DIST, ground_plane=True)
            log(f'atlas {a}: AO {AO_RES[a]} baked in {dt:.1f} s, mean {mean:.3f}, p2 {p2:.3f}')
        bpy.data.objects.remove(ground)
    else:
        for a in shells:
            unwrap_ao(shells[a])
    for a, im in list(ao_imgs.items()):
        # 8-bit GREYSCALE PNG (the occlusion texture reads R; a grey PNG decodes as R = G = B): ~1/3 of Blender's RGB PNG. The
        # file is loaded back and swapped into the materials, so the exporter embeds these bytes
        from PIL import Image as PImage
        w, h = im.size
        px = np.array(im.pixels[:], np.float32).reshape(h, w, 4)[::-1, :, 0]
        path = os.path.join(TEX, f'dom_ao_{a}.png')
        PImage.fromarray(np.clip(np.round(px * 255), 0, 255).astype(np.uint8), 'L').save(path, optimize=True)
        im2 = bpy.data.images.load(path); im2.colorspace_settings.name = 'Non-Color'
        for m in bpy.data.materials:
            if not m.use_nodes: continue
            for n in m.node_tree.nodes:
                if n.type == 'TEX_IMAGE' and n.image == im: n.image = im2
        name = im.name; bpy.data.images.remove(im); im2.name = name
        ao_imgs[a] = im2

    # ---- export (WIP first; data/ only with --final)
    t = time.time()
    export(out_glb, [root])
    log(f'exported {out_glb} in {time.time() - t:.1f} s')
    bpy.ops.object.select_all(action='DESELECT')
    root.select_set(True); lod_empties[2].select_set(True)
    for o in lod_empties[2].children_recursive: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=out_l2, export_format='GLB', use_selection=True, export_extras=True, export_yup=True,
                              export_apply=False, export_texcoords=True, export_normals=True, export_tangents=False,
                              export_materials='EXPORT', export_image_format='AUTO', export_cameras=False, export_lights=False,
                              export_animations=False)
    log(f'exported {out_l2}')
    if args.blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(WIP, 'domestic.blend'))
    st = glb_stats(out_glb)
    log('glb', json.dumps({k: st[k] for k in ('bytes', 'lods', 'materials', 'materials_with_occlusion', 'occlusion_texcoords')}))
    doors = info0.get('doors', [])
    build = dict(built=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'), git=git_rev(),
                 bpy=bpy.app.version_string, glb=st, ao=ao_info, naip_colours=nc, roof_rgb={k: list(v) for k, v in ROOF_RGB.items()},
                 parts_tris=stats_parts, lod2_glb=dict(path=os.path.relpath(out_l2, ROOT), bytes=os.path.getsize(out_l2)),
                 doors=dict(n=len(doors), vestibules=sum(1 for d in doors if d['gap'] > 0.12 or d['low']),
                            bulkheads_over_low_roofs=sum(1 for d in doors if d['low']),
                            notched=sum(1 for d in doors if d.get('notched'))),
                 seconds=round(time.time() - T0, 1), final=args.final)
    json.dump(build, open(os.path.join(OUT, 'domestic_build.json'), 'w'), indent=1)

    if not args.final:
        log('WIP build done (use --final to publish to data/buildings3d/)')
        return
    # ---- publish: copy, verify (separate process: it reads the glb back), manifest
    final = os.path.join(DATA, 'domestic.glb'); final_l2 = os.path.join(DATA, 'domestic_lod2.glb')
    shutil.copyfile(out_glb, final); shutil.copyfile(out_l2, final_l2)
    build['glb_path'] = os.path.relpath(final, ROOT); build['lod2_glb']['path'] = os.path.relpath(final_l2, ROOT)
    json.dump(build, open(os.path.join(OUT, 'domestic_build.json'), 'w'), indent=1)
    log('published', final, final_l2)
    ver = None
    try:
        r = subprocess.run([sys.executable, os.path.join(HERE, 'verify_domestic.py'), final], capture_output=True, text=True, timeout=1500)
        print(r.stdout[-6000:], r.stderr[-3000:])
        ver = json.load(open(os.path.join(OUT, 'domestic_verify.json')))
    except Exception as e:  # noqa: BLE001
        log('verification failed:', e)
    if not args.no_manifest:
        import dom_manifest
        entry = dom_manifest.entry(build, ver, {lod: built[lod][0] for lod in (0, 1, 2)}, MATS, ROOF_RGB, info0)
        path = merge_manifest(lambda old: dom_manifest.keep_renders(old, entry))
        log('manifest ->', path)


if __name__ == '__main__':
    main()
