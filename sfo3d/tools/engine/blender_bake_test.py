# Blender 5.0 (bpy) pipeline smoke test for docs/research/engine.md.
#
# Checks that the pip-installed bpy in this sandbox can do the three jobs the engine report assigns to Blender:
#   1. scripted asset authoring (a toy control tower, jet-bridge tunnel and tug on an apron slab, built from primitives,
#      real metres, Z-up; the glTF exporter converts to Y-up),
#   2. an ambient-occlusion bake with Cycles on the CPU into per-object textures (lightmap-style UVs), wired to the
#      glTF occlusion slot through the exporter's "glTF Material Output" node group, then a .glb export, and
#   3. a small Cycles reference render of the same scene (the QA "ground truth" role).
# The shapes are placeholders, not SFO geometry: nothing here is a claim about real dimensions.
#
# Run:  python3 tools/engine/blender_bake_test.py [out_dir]      (default: refs/cache/blender_test)
# Writes: scene.blend, asset.glb, ao_*.png, ref_cycles.png, report.json (timings, glb structure summary)
import json
import math
import os
import struct
import sys
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', '..', 'refs', 'cache', 'blender_test'))
os.makedirs(OUT, exist_ok=True)
REPORT = {'bpy': bpy.app.version_string, 'build_hash': bpy.app.build_hash.decode() if isinstance(bpy.app.build_hash, bytes) else str(bpy.app.build_hash), 'steps': {}}
T0 = time.time()


def step(name, t):
    REPORT['steps'][name] = round(time.time() - t, 2)
    print(f'[{name}] {REPORT["steps"][name]} s', flush=True)


# ------------------------------------------------------------------ scene
t = time.time()
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'


def material(name, rgb, rough=0.6, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (*rgb, 1.0)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    return m


def finish(obj, mat, name):
    obj.name = name
    obj.data.name = name
    obj.data.materials.append(mat)
    return obj


CONCRETE = material('apron_concrete', (0.42, 0.41, 0.38), 0.85)
WHITE = material('tower_white', (0.8, 0.8, 0.78), 0.45)
GLASS = material('cab_glass', (0.03, 0.04, 0.05), 0.05)
BRIDGE = material('bridge_panel', (0.75, 0.76, 0.77), 0.4, 0.3)
YELLOW = material('tug_yellow', (0.8, 0.6, 0.08), 0.5)

objs = []
bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, 0))
objs.append(finish(bpy.context.object, CONCRETE, 'apron'))
# tapered shaft (cone primitive with two radii), cab, roof disc
bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=3.2, radius2=2.2, depth=38, location=(0, 0, 19))
objs.append(finish(bpy.context.object, WHITE, 'tower_shaft'))
bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=5.0, depth=4.5, location=(1.2, 0, 40.25))
objs.append(finish(bpy.context.object, GLASS, 'tower_cab'))
bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=6.2, depth=0.6, location=(1.2, 0, 42.8))
objs.append(finish(bpy.context.object, WHITE, 'tower_roof'))
# jet-bridge tunnel on two legs
bpy.ops.mesh.primitive_cube_add(size=1, location=(-14, 12, 5.2))
o = bpy.context.object; o.scale = (22, 3.0, 2.9); bpy.ops.object.transform_apply(scale=True)
objs.append(finish(o, BRIDGE, 'bridge_tunnel'))
for x in (-22, -7):
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.35, depth=3.8, location=(x, 12, 1.9))
    objs.append(finish(bpy.context.object, BRIDGE, f'bridge_leg_{x}'))
# baggage tug
bpy.ops.mesh.primitive_cube_add(size=1, location=(10, -9, 0.75))
o = bpy.context.object; o.scale = (3.0, 1.6, 1.5); bpy.ops.object.transform_apply(scale=True)
objs.append(finish(o, YELLOW, 'tug'))
step('build_scene', t)

# ------------------------------------------------------------------ lightmap UVs (one non-overlapping UV set per object)
t = time.time()
for ob in objs:
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')
step('uv_unwrap', t)

# ------------------------------------------------------------------ AO bake (Cycles, CPU)
t = time.time()
world = bpy.data.worlds.new('world'); scene.world = world
world.light_settings.distance = 12.0          # AO ray length (m) used by the Cycles AO bake
scene.cycles.samples = 64
AO_RES = {'apron': 512}
images = {}
for ob in objs:
    res = AO_RES.get(ob.name, 256)
    img = bpy.data.images.new('ao_' + ob.name, res, res, alpha=False, float_buffer=False)
    img.colorspace_settings.name = 'Non-Color'
    images[ob.name] = img
    # a per-object copy of the material so each object bakes into its own image
    m = ob.data.materials[0].copy(); m.name = ob.data.materials[0].name + '_' + ob.name; ob.data.materials[0] = m
    nt = m.node_tree
    tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = img; tex.name = 'AO_BAKE'
    for n in nt.nodes: n.select = False
    tex.select = True; nt.nodes.active = tex
bpy.ops.object.select_all(action='DESELECT')
for ob in objs: ob.select_set(True)
bpy.context.view_layer.objects.active = objs[0]
bake_err = None
try:
    bpy.ops.object.bake(type='AO', margin=4, use_clear=True)
except Exception as e:  # noqa: BLE001
    bake_err = str(e)
step('bake_ao', t)
REPORT['bake_error'] = bake_err
ao_stats = {}
for name, img in images.items():
    img.filepath_raw = os.path.join(OUT, f'ao_{name}.png'); img.file_format = 'PNG'; img.save()
    px = list(img.pixels[:])  # RGBA floats
    r = px[0::4]; ao_stats[name] = {'res': img.size[0], 'min': round(min(r), 3), 'mean': round(sum(r) / len(r), 3)}
REPORT['ao_stats'] = ao_stats

# ------------------------------------------------------------------ wire AO -> glTF occlusion
t = time.time()
grp = bpy.data.node_groups.get('glTF Material Output')
if grp is None:
    grp = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
    grp.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
for ob in objs:
    nt = ob.data.materials[0].node_tree
    tex = nt.nodes['AO_BAKE']
    sep = nt.nodes.new('ShaderNodeSeparateColor')
    g = nt.nodes.new('ShaderNodeGroup'); g.node_tree = grp
    nt.links.new(tex.outputs['Color'], sep.inputs['Color'])
    nt.links.new(sep.outputs['Red'], g.inputs['Occlusion'])
step('wire_occlusion', t)

# ------------------------------------------------------------------ export .glb
t = time.time()
glb = os.path.join(OUT, 'asset.glb')
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=False, export_apply=True, export_image_format='AUTO')
step('export_glb', t)


def glb_summary(path):
    with open(path, 'rb') as f:
        data = f.read()
    magic, ver, length = struct.unpack_from('<4sII', data, 0)
    clen, ctype = struct.unpack_from('<I4s', data, 12)
    j = json.loads(data[20:20 + clen])
    mats = j.get('materials', [])
    return {
        'bytes': len(data), 'magic': magic.decode(), 'version': ver, 'generator': j.get('asset', {}).get('generator'),
        'meshes': len(j.get('meshes', [])), 'nodes': len(j.get('nodes', [])), 'materials': len(mats),
        'materials_with_occlusion': sum(1 for m in mats if 'occlusionTexture' in m),
        'images': [(i.get('mimeType'), i.get('name')) for i in j.get('images', [])][:4] + (['...'] if len(j.get('images', [])) > 4 else []),
        'n_images': len(j.get('images', [])),
        'texcoord_sets': sorted({k for m in j.get('meshes', []) for p in m['primitives'] for k in p['attributes'] if k.startswith('TEXCOORD')}),
        'extensionsUsed': j.get('extensionsUsed', []),
    }


REPORT['glb'] = glb_summary(glb)

# ------------------------------------------------------------------ Cycles reference render
t = time.time()
bpy.ops.object.light_add(type='SUN', location=(0, 0, 50))
sun = bpy.context.object; sun.data.energy = 4.0; sun.rotation_euler = (math.radians(50), 0, math.radians(35))
world.use_nodes = True
bg = world.node_tree.nodes.get('Background'); bg.inputs['Color'].default_value = (0.45, 0.6, 0.85, 1); bg.inputs['Strength'].default_value = 0.8
bpy.ops.object.camera_add(location=(78, -88, 40))
cam = bpy.context.object; scene.camera = cam; cam.data.lens = 35
bpy.ops.object.empty_add(location=(-2, 2, 14)); aim = bpy.context.object
trk = cam.constraints.new('TRACK_TO'); trk.target = aim; trk.track_axis = 'TRACK_NEGATIVE_Z'; trk.up_axis = 'UP_Y'
scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 480, 270, 100
scene.cycles.samples = 32
try:
    scene.cycles.use_denoising = False
except Exception:  # noqa: BLE001
    pass
scene.view_settings.view_transform = 'AgX'
scene.render.filepath = os.path.join(OUT, 'ref_cycles.png')
bpy.ops.render.render(write_still=True)
step('cycles_render', t)
REPORT['view_transform'] = scene.view_settings.view_transform

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'scene.blend'))

# ------------------------------------------------------------------ EEVEE
# EEVEE needs an OpenGL/EGL context. In a headless container without libEGL the pip bpy aborts the whole process
# (observed here: "Couldn't open libEGL.so.1", exit 134), so the probe runs in a child process.
t = time.time()
import subprocess  # noqa: E402
probe = ("import bpy; bpy.ops.wm.open_mainfile(filepath=%r); s = bpy.context.scene; s.render.engine = 'BLENDER_EEVEE'; "
         "s.render.filepath = %r; bpy.ops.render.render(write_still=True); print('EEVEE_OK')") % (os.path.join(OUT, 'scene.blend'), os.path.join(OUT, 'ref_eevee.png'))
r = subprocess.run([sys.executable, '-c', probe], capture_output=True, text=True, timeout=300)
tail = (r.stdout + r.stderr).strip().splitlines()[-2:]
REPORT['eevee'] = {'exit_code': r.returncode, 'ok': 'EEVEE_OK' in r.stdout, 'tail': tail}
step('eevee_probe', t)

REPORT['total_s'] = round(time.time() - T0, 2)
with open(os.path.join(OUT, 'report.json'), 'w') as f:
    json.dump(REPORT, f, indent=1)
print(json.dumps(REPORT, indent=1))
