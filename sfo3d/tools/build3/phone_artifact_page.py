"""Assemble the phone-test artifact page (see phone_artifact.sh): inline live.css and the app bundle, add a test card
that reports backend (WebGPU / WebGL 2), tier, fps, frame-time p50/p95, load time, canvas and GPU; copy the supporting
files. Snapshot mode (artifacts cannot fetch live data), low-resolution liveries."""
import glob, os, shutil, sys
S, O = sys.argv[1], sys.argv[2]
os.makedirs(O, exist_ok=True)
tmpl = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'phone_artifact_template.html')).read()
bundle = open(f'{S}/out/build3/live3.bundle.js').read()
assert '</script' not in bundle
open(f'{O}/sfo_phone_test.html', 'w').write(tmpl.replace('/*LIVE_CSS*/', open(f'{S}/live.css').read()).replace('/*APP_BUNDLE*/', bundle))
for f in glob.glob(f'{S}/out/build3/assets/*'):
    os.makedirs(f'{O}/assets', exist_ok=True); shutil.copy(f, f'{O}/assets/')
for f in glob.glob(f'{S}/data/models/*.sfom'):
    os.makedirs(f'{O}/data/models', exist_ok=True); shutil.copy(f, f'{O}/data/models/' + os.path.basename(f)[:-5] + '.wasm')
for f in glob.glob(f'{S}/data/liveries/*/*-lo.webp'):
    d = os.path.join(O, os.path.relpath(os.path.dirname(f), S)); os.makedirs(d, exist_ok=True); shutil.copy(f, d)
# Blender building assets (js/three/buildings3d.js): renamed .glb -> .wasm like the models (artifacts serve standard web
# types only; the loader fetches the bytes, window.SFO_B3D_EXT = '.wasm' in the template). B3D=all (default: the phone's
# low tier loads the *_lod2 files, a desktop browser the full ones) | lod2 | none. Artifact limits: 15 MB per binary
# file (landside.glb is 14.9 MB), 64 MB per publish (publish in two calls if the total says so); all = 36.8 MB.
b3d = os.environ.get('B3D', 'all'); nb = 0
for f in sorted(glob.glob(f'{S}/data/buildings3d/*.glb')):
    if b3d == 'none' or (b3d == 'lod2' and not f.endswith('_lod2.glb')): continue
    if f.endswith(('_f1.glb', '_f2.glb')) and 'alt' not in b3d: continue  # the tower's alternative height family (tower_f1.glb, ?b3dtower=f1): B3D=all+alt
    sz = os.path.getsize(f); assert sz < 15 * 1024 * 1024, f + ' is over the 15 MB per-file artifact limit'
    os.makedirs(f'{O}/data/buildings3d', exist_ok=True); shutil.copy(f, f'{O}/data/buildings3d/' + os.path.basename(f)[:-4] + '.wasm'); nb += sz
print('buildings3d:', b3d, '%.1f MB' % (nb / 1e6))
print('files:', sum(len(fs) for _, _, fs in os.walk(O)), '%.1f MB' % (sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(O) for f in fs) / 1e6))
