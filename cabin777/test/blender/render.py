"""Cycles (CPU) review render of a unit / cabin slice exported by test/blender/export.js.

  blender -b -P test/blender/render.py -- <export>.json [more.json ...] [--out DIR] [--samples 96] [--w 800 --h 600]
          [--exposure 0] [--view AgX|Standard] [--cove 1] [--down 1] [--emis 1] [--no-denoise] [--blend]

Materials replicate the engine's shader inputs (src/04_shaders.js): per-vertex colour (linear, instance tint applied),
per-vertex roughness / metal / emissive, detail layers 1-24 as exact triplanar box projection of the exported layer
textures (albedo, roughness and normal perturbation), photo swatches for layers 16-24 (base *= mix(1, 2c, gain)),
canvas atlas for layers 13-15 (screens / signs / placards), LED layer 12, window glass. Lighting is a neutral cabin
rig: cove wash lights, aisle downlights, sidewall wash (slices use the real ceiling; unit renders get a hidden ceiling
plane to bounce the cove light off), plus the studio floor and backdrop for units.
Denoising: Cycles OIDN when compiled in, else denoise.py (python3 + `oidn` wheel; set CABIN_OIDN_PATH to its dir).
"""
import array
import json
import math
import os
import subprocess
import sys
import shutil
import tempfile
import time

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))


def parse_args():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    a = {'files': [], 'out': None, 'samples': 96, 'w': None, 'h': None, 'exposure': 0.0, 'view': 'AgX',
         'cove': 1.0, 'down': 1.0, 'emis': 1.0, 'denoise': True, 'blend': False, 'threads': 0}
    i = 0
    while i < len(argv):
        k = argv[i]
        if k == '--no-denoise': a['denoise'] = False
        elif k == '--blend': a['blend'] = True
        elif k.startswith('--'):
            key, val = k[2:], argv[i + 1]; i += 1
            a[key] = val if key in ('out', 'view') else (int(val) if key in ('samples', 'w', 'h', 'threads') else float(val))
        else: a['files'].append(k)
        i += 1
    return a


# ---------------------------------------------------------------- geometry
def load_mesh(meta, base):
    raw = open(os.path.join(base, meta['bin']), 'rb').read()

    def block(name, code):
        L = meta['layout'][name]
        arr = array.array(code)
        arr.frombytes(raw[L['offset']:L['offset'] + L['bytes']])
        return arr
    pos, nrm, col, mat, uv = block('pos', 'f'), block('nrm', 'f'), block('col', 'f'), block('mat', 'f'), block('uv', 'f')
    idx = block('idx', 'i')                     # uint32 < 2^31, reinterpret as int32
    fm = block('fmat', 'B')
    nv, nt = meta['nv'], meta['nt']
    me = bpy.data.meshes.new(meta['name'])
    me.vertices.add(nv)
    me.vertices.foreach_set('co', pos)
    me.loops.add(nt * 3)
    me.loops.foreach_set('vertex_index', idx)
    me.polygons.add(nt)
    me.polygons.foreach_set('loop_start', array.array('i', range(0, nt * 3, 3)))
    try: me.polygons.foreach_set('loop_total', array.array('i', [3]) * nt)
    except Exception: pass
    me.polygons.foreach_set('material_index', array.array('i', fm))
    me.polygons.foreach_set('use_smooth', array.array('b', [1]) * nt)
    ca = me.color_attributes.new('col', 'FLOAT_COLOR', 'POINT')
    ca.data.foreach_set('color', col)
    ma = me.attributes.new('mat', 'FLOAT_VECTOR', 'POINT')
    ma.data.foreach_set('vector', mat)
    uvl = me.uv_layers.new(name='UVMap')
    uvl.data.foreach_set('uv', uv)
    me.update(calc_edges=True)
    if hasattr(me, 'use_auto_smooth'): me.use_auto_smooth = True       # Blender < 4.1: needed for custom normals
    it = iter(nrm)
    me.normals_split_custom_set_from_vertices(list(zip(it, it, it)))
    return me


# ---------------------------------------------------------------- materials
class NB:
    """tiny node-graph helper"""
    def __init__(self, mat):
        mat.use_nodes = True
        self.nt = mat.node_tree
        self.nt.nodes.clear()
        self.x = 0

    def n(self, kind, **props):
        nd = self.nt.nodes.new(kind)
        nd.location = (self.x, 0); self.x += 40
        for k, v in props.items():
            setattr(nd, k, v)
        return nd

    def link(self, a, b):
        self.nt.links.new(a, b)

    def math(self, op, a, b=None, clamp=False):
        nd = self.n('ShaderNodeMath', operation=op, use_clamp=clamp)
        for i, v in enumerate((a, b)):
            if v is None: continue
            if isinstance(v, (int, float)): nd.inputs[i].default_value = v
            else: self.link(v, nd.inputs[i])
        return nd.outputs[0]

    def vmath(self, op, a, b=None):
        nd = self.n('ShaderNodeVectorMath', operation=op)
        for i, v in enumerate((a, b)):
            if v is None: continue
            if isinstance(v, (tuple, list)): nd.inputs[i].default_value = v
            else: self.link(v, nd.inputs[i])
        return nd.outputs['Value'] if op in ('DOT_PRODUCT', 'LENGTH', 'DISTANCE') else nd.outputs['Vector']

    def mix(self, blend, fac, a, b):
        nd = self.n('ShaderNodeMix', data_type='RGBA', blend_type=blend)
        nd.inputs['Factor'].default_value = 1.0
        if isinstance(fac, (int, float)): nd.inputs['Factor'].default_value = fac
        else: self.link(fac, nd.inputs['Factor'])
        for sock, v in ((nd.inputs[6], a), (nd.inputs[7], b)):
            if isinstance(v, (tuple, list)): sock.default_value = v
            else: self.link(v, sock)
        return nd.outputs[2]

    def comb(self, x, y, z=0.0):
        nd = self.n('ShaderNodeCombineXYZ')
        for i, v in enumerate((x, y, z)):
            if isinstance(v, (int, float)): nd.inputs[i].default_value = v
            else: self.link(v, nd.inputs[i])
        return nd.outputs[0]

    def sep(self, v):
        nd = self.n('ShaderNodeSeparateXYZ'); self.link(v, nd.inputs[0]); return nd.outputs

    def sep_rgb(self, v):
        nd = self.n('ShaderNodeSeparateColor'); self.link(v, nd.inputs[0]); return nd.outputs


IMG = {}


def image(path, color=False):
    if path in IMG: return IMG[path]
    im = bpy.data.images.load(path, check_existing=True)
    im.colorspace_settings.name = 'sRGB' if color else 'Non-Color'
    im.alpha_mode = 'CHANNEL_PACKED'
    IMG[path] = im
    return im


def make_material(layer, meta, base, gains):
    """engine material for one detail layer (0 = none, 25 = window glass)"""
    tx = meta['tex']
    mat = bpy.data.materials.new('L%02d' % layer)
    b = NB(mat)
    out = b.n('ShaderNodeOutputMaterial')
    if layer == 25:     # window glass: thin, clear, slightly tinted
        tr = b.n('ShaderNodeBsdfTransparent'); tr.inputs[0].default_value = (0.86, 0.9, 0.92, 1)
        gl = b.n('ShaderNodeBsdfGlossy'); gl.inputs['Roughness'].default_value = 0.02
        fr = b.n('ShaderNodeFresnel'); fr.inputs['IOR'].default_value = 1.5
        mx = b.n('ShaderNodeMixShader')
        b.link(fr.outputs[0], mx.inputs[0]); b.link(tr.outputs[0], mx.inputs[1]); b.link(gl.outputs[0], mx.inputs[2])
        b.link(mx.outputs[0], out.inputs[0])
        return mat
    bsdf = b.n('ShaderNodeBsdfPrincipled')
    b.link(bsdf.outputs[0], out.inputs[0])
    ac = b.n('ShaderNodeAttribute', attribute_type='GEOMETRY', attribute_name='col')
    am = b.n('ShaderNodeAttribute', attribute_type='GEOMETRY', attribute_name='mat')
    m = b.sep(am.outputs['Vector'])
    col, rough, metal, emis = ac.outputs['Color'], m[0], m[1], m[2]
    normal = None
    emission, estr = None, None
    P = tx['params'].get(str(layer))
    if layer in (13, 14, 15):
        uvn = b.n('ShaderNodeUVMap', uv_map='UVMap')
        s = b.sep(uvn.outputs[0])
        flip = b.comb(s[0], b.math('SUBTRACT', 1.0, s[1]))       # canvas row 0 is v = 0 in WebGL
        t = b.n('ShaderNodeTexImage', interpolation='Linear'); t.image = image(os.path.join(base, tx['atlas']), color=True)
        b.link(flip, t.inputs[0])
        tc = t.outputs['Color']
        if layer == 14:
            col = b.mix('MULTIPLY', 1.0, col, tc)
        else:
            emission = tc
            estr = b.math('MULTIPLY', emis, 4.0 * (0.8 if layer == 13 else 1.0) * gains['emis'])
            col = b.mix('MULTIPLY', 1.0, tc, (0.04, 0.04, 0.04, 1))
            rough = 0.25
    elif layer == 12:
        emission = (0.8, 0.85, 1.0, 1)
        estr = b.math('MULTIPLY', emis, 6.0 * gains['emis'])
        col = b.mix('MULTIPLY', 1.0, col, (0.3, 0.3, 0.3, 1))
    elif layer > 0 and P and str(layer) in tx['detail']:
        # exact triplanar of the engine: q = objpos * scale; X face (q.z, q.y), Y face (q.x, q.z), Z face (q.x, q.y)
        tco = b.n('ShaderNodeTexCoord')
        q = b.sep(tco.outputs['Object'])
        sc = P[0]
        qx, qy, qz = (b.math('MULTIPLY', q[i], sc) for i in range(3))
        nrm_o = tco.outputs['Normal']                                  # object space = engine space
        na = b.sep(b.vmath('ABSOLUTE', nrm_o))
        w4 = [b.math('POWER', na[i], 4.0) for i in range(3)]
        wsum = b.math('ADD', b.math('ADD', w4[0], w4[1]), w4[2])
        w = [b.math('DIVIDE', w4[i], wsum) for i in range(3)]
        uvs = [b.comb(qz, b.math('MULTIPLY', qy, -1.0)), b.comb(qx, b.math('MULTIPLY', qz, -1.0)), b.comb(qx, b.math('MULTIPLY', qy, -1.0))]

        def tri(path, color_space=False):
            smp = []
            for k in range(3):
                t = b.n('ShaderNodeTexImage', interpolation='Linear', extension='REPEAT')
                t.image = image(path, color=color_space)
                b.link(uvs[k], t.inputs[0])
                smp.append(t)
            return smp
        smp = tri(os.path.join(base, tx['detail'][str(layer)]))

        def blend(outs):
            acc = None
            for k in range(3):
                v = b.vmath('SCALE', outs[k]); v.node.inputs['Scale'].default_value = 0
                b.link(w[k], v.node.inputs['Scale'])
                acc = v if acc is None else b.vmath('ADD', acc, v)
            return acc
        trgb = blend([s.outputs['Color'] for s in smp])
        tr_ = b.sep(trgb)
        ta = None
        for k in range(3):
            v = b.math('MULTIPLY', smp[k].outputs['Alpha'], w[k])
            ta = v if ta is None else b.math('ADD', ta, v)
        # albedo
        if layer >= 16 and str(layer) in tx['photo']:
            ph = tri(os.path.join(base, tx['photo'][str(layer)]))
            c2 = b.vmath('SCALE', blend([s.outputs['Color'] for s in ph])); c2.node.inputs['Scale'].default_value = 2.0
            fac = b.mix('MIX', P[2], (1, 1, 1, 1), c2)
            col = b.mix('MULTIPLY', 1.0, col, fac)
        else:
            f = b.math('ADD', 1.0, b.math('MULTIPLY', b.math('SUBTRACT', tr_[2], 0.5), 2.0 * P[2]))
            col = b.mix('MULTIPLY', 1.0, col, b.comb(f, f, f))
        rough = b.math('MINIMUM', b.math('MAXIMUM', b.math('MULTIPLY', rough, b.math('ADD', 1.0, b.math('MULTIPLY', b.math('SUBTRACT', ta, 0.5), 2.0 * P[3]))), 0.04), 1.0)
        # normal: dn = (0, nx.y, nx.x) wx + (ny.x, 0, ny.y) wy + (nz.x, nz.y, 0) wz ; N = normalize(N + dn * P.y)
        cs = [b.sep(s.outputs['Color']) for s in smp]
        d = lambda c: b.math('SUBTRACT', b.math('MULTIPLY', c, 2.0), 1.0)
        dnx = b.math('ADD', b.math('MULTIPLY', d(cs[1][0]), w[1]), b.math('MULTIPLY', d(cs[2][0]), w[2]))
        dny = b.math('ADD', b.math('MULTIPLY', d(cs[0][1]), w[0]), b.math('MULTIPLY', d(cs[2][1]), w[2]))
        dnz = b.math('ADD', b.math('MULTIPLY', d(cs[0][0]), w[0]), b.math('MULTIPLY', d(cs[1][1]), w[1]))
        dn = b.vmath('SCALE', b.comb(dnx, dny, dnz)); dn.node.inputs['Scale'].default_value = P[1]
        no = b.vmath('NORMALIZE', b.vmath('ADD', nrm_o, dn))
        vt = b.n('ShaderNodeVectorTransform', vector_type='NORMAL', convert_from='OBJECT', convert_to='WORLD')
        b.link(no, vt.inputs[0])
        normal = vt.outputs[0]
    if emission is None:       # generic emissive (engine: base * emis * 3)
        emission, estr = col, b.math('MULTIPLY', emis, 3.0 * gains['emis'])
    for sock, v in (('Base Color', col), ('Roughness', rough), ('Metallic', metal), ('Emission Color', emission),
                    ('Emission Strength', estr), ('Normal', normal)):
        if v is None: continue
        if sock not in bsdf.inputs: sock = {'Emission Color': 'Emission'}.get(sock, sock)
        if isinstance(v, (int, float)): bsdf.inputs[sock].default_value = v
        elif isinstance(v, tuple): bsdf.inputs[sock].default_value = v
        else: b.link(v, bsdf.inputs[sock])
    if isinstance(rough, (int, float)): pass
    else:
        r = b.math('MAXIMUM', rough, 0.12)       # engine floor after specular AA
        b.link(r, bsdf.inputs['Roughness'])
    return mat


def plain_material(name, rgb, rough=0.8):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    p = mat.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*rgb, 1)
    p.inputs['Roughness'].default_value = rough
    return mat


# ---------------------------------------------------------------- scene
def srgb2lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def look_matrix(eye, look):
    """camera / light local frame in engine space: looks down -Z, +Y up (same as the GL view)"""
    e, t = Vector(eye), Vector(look)
    z = (e - t).normalized()
    up = Vector((0, 1, 0)) if abs(z.y) < 0.999 else Vector((0, 0, 1))
    x = up.cross(z).normalized()
    y = z.cross(x)
    M = Matrix.Identity(4)
    for r in range(3):
        M[r][0], M[r][1], M[r][2], M[r][3] = x[r], y[r], z[r], e[r]
    return M


def add_area(root, name, pos, aim, size, size_y, power, spread=180.0, color=(1.0, 0.97, 0.93)):
    L = bpy.data.lights.new(name, 'AREA')
    L.shape = 'RECTANGLE'; L.size = size; L.size_y = size_y
    L.energy = power; L.color = color
    if hasattr(L, 'spread'): L.spread = math.radians(spread)
    ob = bpy.data.objects.new(name, L)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = root
    M = look_matrix(pos, [pos[0] + aim[0], pos[1] + aim[1], pos[2] + aim[2]])
    ob.matrix_basis = M
    ob.visible_camera = False
    return ob


def lighting(root, meta, a, cabin):
    mn, mx = meta['bounds']
    cove, down = a['cove'], a['down']
    warm = (1.0, 0.96, 0.9)
    if cabin:
        z0, z1 = mn[2], mx[2]
        n = max(1, round((z1 - z0) / 2.0)); L = (z1 - z0) / n
        for k in range(n):
            zc = z0 + (k + 0.5) * L
            for s in (-1, 1):
                # cove wash onto the curved aisle panel from the outboard and centre bin top edges
                add_area(root, 'coveO', [1.66 * s, 2.25, zc], [-0.55 * s, 1, 0], 0.04, L, 18 * L * cove, color=warm)
                add_area(root, 'coveC', [0.74 * s, 2.28, zc], [0.55 * s, 1, 0], 0.04, L, 18 * L * cove, color=warm)
                # sidewall wash lens under the outboard bins
                add_area(root, 'wash', [2.70 * s, 1.58, zc], [0.5 * s, -1, 0], 0.04, L, 12 * L * cove, color=warm)
        # aisle downlights in the ceiling trough (every frame pair)
        nz = max(1, round((z1 - z0) / 1.07))
        for k in range(nz):
            zc = z0 + (k + 0.5) * (z1 - z0) / nz
            for s in (-1, 1):
                add_area(root, 'down', [1.05 * s, 2.36, zc], [0, -1, 0], 0.08, 0.08, 8 * down, spread=70, color=warm)
    else:
        cx, cz = (mn[0] + mx[0]) / 2, (mn[2] + mx[2]) / 2
        ex, ez = mx[0] - mn[0], mx[2] - mn[2]
        top = max(2.45, mx[1] + 0.15)
        # hidden white ceiling plane (bounces the cove light like the real aisle panels)
        me = bpy.data.meshes.new('ceiling')
        hx, hz = ex / 2 + 1.6, ez / 2 + 1.6
        me.from_pydata([(cx - hx, top, cz - hz), (cx + hx, top, cz - hz), (cx + hx, top, cz + hz), (cx - hx, top, cz + hz)], [], [(0, 3, 2, 1)])
        ob = bpy.data.objects.new('ceiling', me); bpy.context.scene.collection.objects.link(ob); ob.parent = root
        me.materials.append(plain_material('ceiling', (0.85, 0.85, 0.83), 0.85))
        ob.visible_camera = False; ob.visible_shadow = False
        Lz = ez + 1.2
        for s in (-1, 1):
            add_area(root, 'cove', [cx + s * (ex / 2 + 0.5), top - 0.18, cz], [-0.5 * s, 1, 0], 0.04, Lz, 30 * Lz * cove, color=warm)
        nz = max(1, round((ez + 0.6) / 0.9))
        for k in range(nz):
            zc = cz - (ez + 0.6) / 2 + (k + 0.5) * (ez + 0.6) / nz
            for xo in (-0.45, 0.45):
                add_area(root, 'down', [cx + xo * max(1.0, ex / 1.2), top - 0.02, zc], [0, -1, 0], 0.1, 0.1, 11 * down, spread=75, color=warm)
        # studio floor (#cfd3d8, as studioRender)
        me = bpy.data.meshes.new('floor')
        r = 12
        me.from_pydata([(-r + cx, -0.002, -r + cz), (r + cx, -0.002, -r + cz), (r + cx, -0.002, r + cz), (-r + cx, -0.002, r + cz)], [], [(0, 3, 2, 1)])
        ob = bpy.data.objects.new('floor', me); bpy.context.scene.collection.objects.link(ob); ob.parent = root
        me.materials.append(plain_material('floor', tuple(srgb2lin(v / 255) for v in (0xcf, 0xd3, 0xd8)), 0.8))


def world(cabin):
    w = bpy.data.worlds.new('world'); bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    lp = nt.nodes.new('ShaderNodeLightPath')
    bg_cam = nt.nodes.new('ShaderNodeBackground'); bg_fill = nt.nodes.new('ShaderNodeBackground')
    mx = nt.nodes.new('ShaderNodeMixShader')
    if cabin:   # daylight sky seen through the windows / open slice ends
        bg_cam.inputs[0].default_value = (0.55, 0.68, 0.9, 1); bg_cam.inputs[1].default_value = 1.0
        bg_fill.inputs[0].default_value = (0.62, 0.72, 0.9, 1); bg_fill.inputs[1].default_value = 1.2
    else:       # studio backdrop (studioRender clear colour) + soft grey fill
        bg_cam.inputs[0].default_value = tuple(srgb2lin(v) for v in (0.80, 0.83, 0.87)) + (1,); bg_cam.inputs[1].default_value = 1.0
        bg_fill.inputs[0].default_value = (0.62, 0.64, 0.68, 1); bg_fill.inputs[1].default_value = 0.18
    nt.links.new(lp.outputs['Is Camera Ray'], mx.inputs[0])
    nt.links.new(bg_fill.outputs[0], mx.inputs[1]); nt.links.new(bg_cam.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs[0])


def camera(root, meta):
    o = meta['opts']
    mn, mx = meta['bounds']
    if 'eye' in o:
        eye, look = o['eye'], o['look']
    else:
        c = o.get('target') or [(mn[i] + mx[i]) / 2 for i in range(3)]
        size = max(mx[i] - mn[i] for i in range(3))
        az, el, dist = o.get('az', 0.7), o.get('el', 0.25), o.get('dist', 1.7) * size
        eye = [c[0] + dist * math.cos(el) * math.sin(az), c[1] + dist * math.sin(el), c[2] + dist * math.cos(el) * math.cos(az)]
        look = c
    cam = bpy.data.cameras.new('cam')
    cam.sensor_fit = 'VERTICAL'
    cam.angle = math.radians(o.get('fov', 34))
    cam.clip_start = 0.02; cam.clip_end = 200
    ob = bpy.data.objects.new('cam', cam)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = root
    ob.matrix_basis = look_matrix(eye, look)
    bpy.context.scene.camera = ob


def cycles_has_oidn():
    try:
        import _cycles
        return bool(getattr(_cycles, 'with_openimagedenoise', False))
    except Exception:
        return False


def pixels_of(path):
    im = bpy.data.images.load(path)
    px = array.array('f', bytes(4 * im.size[0] * im.size[1] * 4))
    im.pixels.foreach_get(px)
    bpy.data.images.remove(im)
    return px


def render_one(path, a):
    base = os.path.dirname(os.path.abspath(path))
    meta = json.load(open(path))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    IMG.clear()
    sc = bpy.context.scene
    cabin = bool(meta.get('slice')) or meta['opts'].get('cabin', False)
    t0 = time.time()
    root = bpy.data.objects.new('engine_axes', None)       # engine (x, y up, z aft) -> Blender (x, -z, y)
    sc.collection.objects.link(root)
    root.rotation_euler = (math.pi / 2, 0, 0)
    me = load_mesh(meta, base)
    gains = {'emis': a['emis']}
    for layer in range(26):
        me.materials.append(make_material(layer, meta, base, gains))
    ob = bpy.data.objects.new(meta['name'], me)
    sc.collection.objects.link(ob)
    ob.parent = root
    lighting(root, meta, a, cabin)
    world(cabin)
    camera(root, meta)
    t_load = time.time() - t0
    # render settings
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = a['samples']
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.02
    sc.cycles.max_bounces = 8; sc.cycles.diffuse_bounces = 4; sc.cycles.glossy_bounces = 4
    sc.cycles.transparent_max_bounces = 8; sc.cycles.transmission_bounces = 4
    sc.cycles.sample_clamp_indirect = 8.0
    if hasattr(sc.cycles, 'use_light_tree'): sc.cycles.use_light_tree = True
    if a['threads']:
        sc.render.threads_mode = 'FIXED'; sc.render.threads = a['threads']
    sc.render.resolution_x = a['w'] or meta['w']
    sc.render.resolution_y = a['h'] or meta['h']
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.view_settings.view_transform = a['view']
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = a['exposure']
    sc.render.image_settings.file_format = 'PNG'
    out_dir = a['out'] or base
    os.makedirs(out_dir, exist_ok=True)
    out_png = os.path.join(out_dir, meta['name'] + '.png')
    ext_denoise = a['denoise'] and not cycles_has_oidn()
    sc.cycles.use_denoising = a['denoise'] and not ext_denoise
    tmp = None
    if ext_denoise:
        # write beauty + denoising albedo / normal as float EXRs through the compositor, denoise outside Blender
        tmp = tempfile.mkdtemp(prefix='.oidn_', dir=out_dir)
        sc.view_layers[0].cycles.denoising_store_passes = True
        sc.use_nodes = True
        nt = sc.node_tree; nt.nodes.clear()
        rl = nt.nodes.new('CompositorNodeRLayers')
        fo = nt.nodes.new('CompositorNodeOutputFile')
        fo.base_path = tmp
        fo.format.file_format = 'OPEN_EXR'; fo.format.color_depth = '32'; fo.format.exr_codec = 'NONE'
        fo.file_slots.clear()
        for slot, sock in (('rgb_', 'Image'), ('alb_', 'Denoising Albedo'), ('nrm_', 'Denoising Normal')):
            fo.file_slots.new(slot)
            nt.links.new(rl.outputs[sock], fo.inputs[slot])
        comp = nt.nodes.new('CompositorNodeComposite')
        nt.links.new(rl.outputs['Image'], comp.inputs[0])
    if a['blend']:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, meta['name'] + '.blend'))
    t1 = time.time()
    sc.render.filepath = out_png
    bpy.ops.render.render(write_still=True)
    t_render = time.time() - t1
    t_dn = 0.0
    if ext_denoise:
        t2 = time.time()
        W, H = sc.render.resolution_x, sc.render.resolution_y
        fr = '%04d' % sc.frame_current
        raws = []
        for slot in ('rgb_', 'alb_', 'nrm_'):
            px = pixels_of(os.path.join(tmp, slot + fr + '.exr'))
            p = os.path.join(tmp, slot + '.f32'); open(p, 'wb').write(px.tobytes()); raws.append(p)
        outp = os.path.join(tmp, 'out.f32')
        py = os.environ.get('CABIN_PYTHON', 'python3')
        r = subprocess.run([py, os.path.join(HERE, 'denoise.py'), str(W), str(H), *raws, outp], capture_output=True, text=True)
        if r.returncode == 0 and os.path.exists(outp):
            px = array.array('f'); px.frombytes(open(outp, 'rb').read())
            im = bpy.data.images.new('denoised', W, H, float_buffer=True)
            im.pixels.foreach_set(px)
            raw_png = out_png.replace('.png', '_noisy.png')
            os.replace(out_png, raw_png)
            im.save_render(out_png, scene=sc)       # applies the view transform / exposure
            if not a.get('keep_noisy'): os.remove(raw_png)
        else:
            print('denoise failed (install the oidn wheel, set CABIN_OIDN_PATH):', r.stderr.strip()[-400:])
        shutil.rmtree(tmp, ignore_errors=True)
        t_dn = time.time() - t2
    print('RENDER %s: %d verts %d tris, %dx%d, %d spp, setup %.1fs, render %.1fs, denoise %.1fs -> %s' % (
        meta['name'], meta['nv'], meta['nt'], sc.render.resolution_x, sc.render.resolution_y, a['samples'],
        t_load, t_render, t_dn, out_png))
    return t_render


if __name__ == '__main__':
    args = parse_args()
    for f in args['files']:
        render_one(f, args)
