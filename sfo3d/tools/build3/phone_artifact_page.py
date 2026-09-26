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
print('files:', sum(len(fs) for _, _, fs in os.walk(O)))
