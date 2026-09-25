#!/usr/bin/env python3
"""Render check of the baked liveries with Blender Cycles (CPU): one three-quarter close-up per brand, of the brand's most
frequent model at SFO wearing its baked texture, under out/liveries/<BRAND>.png (reference renders for the visual QA of
the liveries; compare with the official references listed in data/liveries/manifest.json).

The model is built from the .sfom exactly as the app draws it: the type's fuselage plugs / span / fin fit applied
(tools/liveries/common.apply_stretch), texture 0 = the livery (alpha 0 = cabin-window glass), other textures as converted,
glass dark and glossy, metal parts metallic. Lighting: a sun at 35 deg elevation and an even sky; a concrete ground plane.

Usage: python3 tools/liveries/render_blender.py [BRAND ...] [--res lo|mid|hi] [--samples 24] [--size 1280x720] [--out out/liveries]
Needs the bpy module (Blender 5.0.1 as a Python module).
"""
import argparse, io, json, math, os, sys, tempfile
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common, sfom

VIEW = dict(az=38.0, el=11.0)    # camera azimuth from the nose toward port, elevation (deg)
# named views: '34' three-quarter front from port (default), 'stbd34' from starboard, 'port' / 'stbd' side views (low
# elevation, orthographic: window rows, titles and cheatlines along the whole body), 'rear34' tail from port
VIEWS = {'34': dict(az=38.0, el=11.0), 'stbd34': dict(az=-38.0, el=11.0), 'port': dict(az=90.0, el=2.0, ortho=True),
         'stbd': dict(az=-90.0, el=2.0, ortho=True), 'rear34': dict(az=140.0, el=12.0)}


def build_scene(bpy, model_path, type_key, livery_path, tmp, cargo=False):
    m = sfom.load(model_path); h = m['head']
    A = common.app(); f = A['types'][type_key]['fit'] if type_key else None
    P = common.apply_stretch(m['pos'], m['zone'], f['stretch'] if f and f['stretch'] else None)
    # model frame (x fwd, y up, z stbd) -> Blender (x fwd, y port, z up)
    V = np.stack([P[:, 0], -P[:, 2], P[:, 1]], -1)
    idx = m['idx']
    mesh = bpy.data.meshes.new('ac'); ob = bpy.data.objects.new('ac', mesh); bpy.context.collection.objects.link(ob)
    # faces keep the source winding (outward, like the stored normals); the per-loop UVs follow the same order.
    # RB_REWIND=1 / RB_NORMALS=none|neg are debugging switches (rewound faces with the source normals render black)
    wind = (lambda a: a[:, ::-1]) if os.environ.get('RB_REWIND') else (lambda a: a)
    mesh.from_pydata(V.tolist(), [], wind(idx).tolist())
    uvl = mesh.uv_layers.new(name='uv')
    uv = m['uv'][wind(idx)].reshape(-1, 2).copy(); uv[:, 1] = 1 - uv[:, 1]
    uvl.data.foreach_set('uv', uv.reshape(-1))
    # images
    imgs = []
    for i, im in enumerate(m['textures']):
        fn = os.path.join(tmp, f'tex{i}.png')
        (im if not (i == 0 and livery_path) else __import__('PIL.Image', fromlist=['Image']).open(livery_path).convert('RGBA')).save(fn)
        imgs.append(bpy.data.images.load(fn))
    # materials: one per sfom material
    mats = []
    for mi, mm in enumerate(h['mats']):
        mat = bpy.data.materials.new(f'm{mi}'); mat.use_nodes = True
        nt = mat.node_tree; bsdf = nt.nodes.get('Principled BSDF')
        col = list(mm['color'][:3]) + [1.0]
        bsdf.inputs['Base Color'].default_value = col
        kind = mm['kind']
        if kind == 'glass':
            bsdf.inputs['Base Color'].default_value = (0.01, 0.012, 0.015, 1); bsdf.inputs['Roughness'].default_value = 0.05
        elif kind == 'metal':
            bsdf.inputs['Metallic'].default_value = 0.9; bsdf.inputs['Roughness'].default_value = 0.3
        else:
            bsdf.inputs['Roughness'].default_value = 0.32 if kind == 'paint' else 0.6
            try: bsdf.inputs['Coat Weight'].default_value = 0.4 if kind == 'paint' else 0.0
            except KeyError: pass
        if mm['tex'] >= 0 and kind != 'glass':
            tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = imgs[mm['tex']]
            if mm.get('atlas'):
                # alpha < 0.5: painted cabin window -> dark glossy glass
                mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'
                nt.links.new(tn.outputs['Alpha'], mix.inputs['Factor'])
                mix.inputs['A'].default_value = (0.012, 0.014, 0.018, 1)
                nt.links.new(tn.outputs['Color'], mix.inputs['B'])
                nt.links.new(mix.outputs['Result'], bsdf.inputs['Base Color'])
                rmix = nt.nodes.new('ShaderNodeMapRange')
                nt.links.new(tn.outputs['Alpha'], rmix.inputs['Value']); rmix.inputs['To Min'].default_value = 0.05; rmix.inputs['To Max'].default_value = 0.32
                nt.links.new(rmix.outputs['Result'], bsdf.inputs['Roughness'])
            else:
                mul = nt.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1.0
                mul.inputs['A'].default_value = col; nt.links.new(tn.outputs['Color'], mul.inputs['B'])
                nt.links.new(mul.outputs['Result'], bsdf.inputs['Base Color'])
        mats.append(mat); mesh.materials.append(mat)
    mi_ = m['tri_mat'].astype(np.int32).copy()
    if cargo:
        # freighter: cabin-window glass aft of the flight deck is painted over (as js/shaders/aircraft_real.js uNoCabin)
        pm = bpy.data.materials.new('plug'); pm.use_nodes = True
        pb = pm.node_tree.nodes.get('Principled BSDF'); pb.inputs['Base Color'].default_value = (0.86, 0.86, 0.86, 1); pb.inputs['Roughness'].default_value = 0.35
        mesh.materials.append(pm)
        kinds = np.array([mm['kind'] for mm in h['mats']])
        Lm = float(-P[:, 0].min()); cx = P[idx].mean(1)[:, 0]
        mi_[(kinds[mi_] == 'glass') & (cx < -0.12 * Lm)] = len(mats)
    mesh.polygons.foreach_set('material_index', mi_)
    mesh.polygons.foreach_set('use_smooth', np.ones(len(idx), bool))
    Nb = np.stack([m['nrm'][:, 0], -m['nrm'][:, 2], m['nrm'][:, 1]], -1)
    Nb /= np.maximum(np.linalg.norm(Nb, axis=1, keepdims=True), 1e-6)
    nm = os.environ.get('RB_NORMALS', 'src')
    if nm != 'none':
        try: mesh.normals_split_custom_set_from_vertices((Nb if nm == 'src' else -Nb).tolist())
        except Exception: pass
    mesh.update()
    lo, hi = V.min(0), V.max(0)
    return ob, lo, hi, m


def render(code, model_path, type_key, livery_path, out, size=(1280, 720), samples=24, view='34', zoom=None):
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    tmp = tempfile.mkdtemp()
    import liveries
    ob, lo, hi, m = build_scene(bpy, model_path, type_key, livery_path, tmp, cargo=bool(liveries.LIVERIES.get(code, {}).get('cargo')))
    L = hi[0] - lo[0]; zmin = lo[2]
    # ground
    bpy.ops.mesh.primitive_plane_add(size=L * 8, location=((lo[0] + hi[0]) / 2, 0, zmin - 0.02))
    g = bpy.context.object; gm = bpy.data.materials.new('ground'); gm.use_nodes = True
    gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.32, 0.32, 0.31, 1)
    gm.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.85
    g.data.materials.append(gm)
    # sun + sky
    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 4.2; sun.angle = math.radians(1.0)
    so = bpy.data.objects.new('sun', sun); bpy.context.collection.objects.link(so)
    so.rotation_euler = (math.radians(55), 0, math.radians(-40))
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (0.42, 0.55, 0.75, 1); bg.inputs['Strength'].default_value = 0.9
    # camera: three-quarter from the front on the port side
    V_ = VIEWS.get(view, VIEW)
    cam = bpy.data.cameras.new('cam'); cam.lens = 45
    co = bpy.data.objects.new('cam', cam); bpy.context.collection.objects.link(co); sc.camera = co
    tgt = np.array([lo[0] + 0.5 * L, 0.0, zmin + 0.38 * (hi[2] - zmin)])
    if V_.get('ortho'):
        cam.type = 'ORTHO'; cam.ortho_scale = 1.04 * L
        tgt = np.array([lo[0] + 0.5 * L, 0.0, zmin + 0.5 * (hi[2] - zmin)])
    if zoom:        # (fraction of the length from the nose, ortho scale as a fraction of the length)
        tgt = np.array([hi[0] - zoom[0] * L, 0.0, tgt[2]]); cam.ortho_scale = zoom[1] * L
    az, el = math.radians(V_['az']), math.radians(V_['el'])
    d = 1.3 * L
    pos = tgt + d * np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
    co.location = pos.tolist()
    dirv = tgt - pos; co.rotation_euler = (math.atan2(math.hypot(dirv[0], dirv[1]), -dirv[2]), 0, math.atan2(dirv[1], dirv[0]) - math.pi / 2)
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples
    try: sc.cycles.use_denoising = True
    except Exception: pass
    sc.render.resolution_x, sc.render.resolution_y = size; sc.render.film_transparent = False
    sc.view_settings.view_transform = 'AgX' if 'AgX' in [v.name for v in bpy.types.ColorManagedViewSettings.bl_rna.properties['view_transform'].enum_items] else 'Filmic'
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('brands', nargs='*'); ap.add_argument('--res', default='hi'); ap.add_argument('--samples', type=int, default=24)
    ap.add_argument('--size', default='1280x720'); ap.add_argument('--out', default=os.path.join(common.ROOT, 'out', 'liveries'))
    ap.add_argument('--view', default='34', help='34 | stbd34 | port | stbd | rear34')
    ap.add_argument('--type', help='render this TYPES key (its model and the brand\'s bake for it) instead of the brand\'s most frequent type')
    ap.add_argument('--zoom', help='side views: "f,w" = centre at fraction f of the length from the nose, width w x length')
    ap.add_argument('--suffix', default='')
    a = ap.parse_args()
    zoom = tuple(float(v) for v in a.zoom.split(',')) if a.zoom else None
    man = json.load(open(os.path.join(common.LIV, 'manifest.json')))
    os.makedirs(a.out, exist_ok=True)
    A = common.app()
    sizes = tuple(int(v) for v in a.size.split('x'))
    # the model each brand is rendered on: its most frequent SFO type (DataSF landings Aug 2025 - Jul 2026,
    # docs/research/liveries.md §1.1) where listed in PREF, else its first listed SFO type that has a bake
    PREF = dict(UAL='B738', DAL='B739', AAL='A321', ASA='B739', SWA='B737', JBU='A321', FFT='A20N', ACA='B38M', AMX='B38M',
                WJA='B738', HAL='A21N', AVA='A20N', CMP='B39M', SCX='B738', MXY='BCS3', DLH='B748', VIR='B789', JAL='B789')
    import liveries
    for code, L in liveries.LIVERIES.items():
        if a.brands and code not in a.brands: continue
        ent = {e['model']: e for e in man['entries'] if e['brand'] == code}
        pick = None
        cands = [a.type] if a.type else [A['icao'].get(icao) for icao in ([PREF[code]] if code in PREF else []) + L.get('types', [])]
        for t in cands:
            mdl = A['typeModel'].get(t) if t else None
            if mdl in ent:
                e = ent[mdl]; f = None
                for v in [e] + e.get('variants', []):
                    if t in v.get('types', []): f = v
                if f is None: continue
                pick = (mdl, t, f['files'][a.res]); break
        if not pick: print(code, 'no bake (procedural airframe only)'); continue
        mdl, typ, file = pick
        out = os.path.join(a.out, f'{code}{a.suffix}.png')
        render(code, os.path.join(common.MD, mdl + '.sfom'), typ, os.path.join(common.LIV, file), out, sizes, a.samples, a.view, zoom)
        print(code, mdl, typ, '->', os.path.relpath(out, common.ROOT))
