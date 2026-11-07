"""Assemble the phone-test artifact page (see phone_artifact.sh): inline live.css and the app bundle, add a test card
that reports backend (WebGPU / WebGL 2), tier, fps, frame-time p50/p95, load time, canvas and GPU; copy the supporting
files. Snapshot mode (artifacts cannot fetch live data), low-resolution liveries."""
import glob, json, os, shutil, sys
S, O = sys.argv[1], sys.argv[2]
os.makedirs(O, exist_ok=True)
tmpl = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'phone_artifact_template.html')).read()
bundle = open(f'{S}/out/build3/live3.bundle.js').read()
assert '</script' not in bundle
# close-out round 3 (integration-4): two more rows on the test card, so the owner's next phone test answers what the
# headless runs cannot: (1) whether the artifact page may compile WebAssembly (the meshopt / KTX2 decoders need it; the
# artifact CSP is unverified - a CSP without 'wasm-unsafe-eval' / 'unsafe-eval' makes WebAssembly.compile throw), probed
# with the 8-byte empty module; (2) the JS heap (performance.memory, Chromium only: used / total MB, refreshed every 2 s).
# Both are appended to "Copy results". Nothing is sent anywhere.
PROBE_ROWS = ('<div class="row"><span class="k">WebAssembly</span><span id="pt-wasm">–</span></div>'
              '<div class="row"><span class="k">JS heap</span><span id="pt-heap">–</span></div>')
PROBE_JS = r"""<script>
(function () {
  var $ = function (id) { return document.getElementById(id); }, r = { wasm: 'probing', heap: null };
  function show() { if ($('pt-wasm')) $('pt-wasm').textContent = r.wasm; if ($('pt-heap')) $('pt-heap').textContent = r.heap || 'n/a (no performance.memory)'; }
  try {
    if (typeof WebAssembly !== 'object') r.wasm = 'no WebAssembly object';
    else WebAssembly.compile(new Uint8Array([0, 97, 115, 109, 1, 0, 0, 0])).then(function () { r.wasm = 'compiles (meshopt / KTX2 decoders possible)'; show(); },
      function (e) { r.wasm = 'blocked: ' + String(e && e.message || e).slice(0, 160); show(); });
  } catch (e) { r.wasm = 'blocked: ' + String(e && e.message || e).slice(0, 160); }
  setInterval(function () { var m = performance.memory; if (m) r.heap = (m.usedJSHeapSize / 1048576).toFixed(0) + ' / ' + (m.totalJSHeapSize / 1048576).toFixed(0) + ' MB'; show(); }, 2000);
  document.addEventListener('click', function (e) {
    if (e.target.id !== 'pt-copy') return;
    var out = $('pt-out'); if (!out) return; out.textContent += '\nwasm: ' + r.wasm + '\njs heap: ' + (r.heap || 'n/a');
    if (navigator.clipboard) navigator.clipboard.writeText(out.textContent).catch(function () {});
  });
  show();
})();
</script>
"""
page = tmpl.replace('/*LIVE_CSS*/', open(f'{S}/live.css').read()).replace('/*APP_BUNDLE*/', bundle)
k_row = '<div class="row"><span class="k">GPU</span><span id="pt-gpu">–</span></div>'; k_js = '<script type="module">'
assert page.count(k_row) == 1 and page.count(k_js) >= 1
page = page.replace(k_row, k_row + PROBE_ROWS, 1).replace(k_js, PROBE_JS + k_js, 1)
open(f'{O}/sfo_phone_test.html', 'w').write(page)
for f in glob.glob(f'{S}/out/build3/assets/*'):
    os.makedirs(f'{O}/assets', exist_ok=True); shutil.copy(f, f'{O}/assets/')
for f in glob.glob(f'{S}/data/models/*.sfom'):
    os.makedirs(f'{O}/data/models', exist_ok=True); shutil.copy(f, f'{O}/data/models/' + os.path.basename(f)[:-5] + '.wasm')
for f in glob.glob(f'{S}/data/liveries/*/*-lo.webp'):
    d = os.path.join(O, os.path.relpath(os.path.dirname(f), S)); os.makedirs(d, exist_ok=True); shutil.copy(f, d)
# Blender building assets (js/three/buildings3d.js): renamed .glb -> .wasm like the models (artifacts serve standard web
# types only; the loader fetches the bytes, window.SFO_B3D_EXT = '.wasm' in the template). B3D=all (default since the
# integration review round 1: the phone's low tier shows the *_lod2 files first and loads a group's full file when the
# camera comes near it, ?b3d=near; a desktop browser loads the full ones) | lod2 | none. Artifact limits: 15 MB per binary
# file - a larger file is split into PART_MB pieces <name>.part<i>.wasm (window.SFO_B3D_PARTS = {name: n}, joined by the
# loader) -, 64 MB per publish (publish in two calls if the total says so).
PART_MB = 12
b3d = os.environ.get('B3D', 'all'); nb = 0; parts = {}
# integration review round 2 (finding 4): the landside asset ships per building (lsu_<unit>.glb, tools/blender/b3d_split.py,
# loaded per unit by buildings3d.js in every mode) with its shared images as plain files (lsu_img_*.png / .jpg, referenced
# by URI): landside.glb itself is then not shipped
units = glob.glob(f'{S}/data/buildings3d/lsu_*.glb')
for f in sorted(glob.glob(f'{S}/data/buildings3d/*.glb')):
    if b3d == 'none' or (b3d == 'lod2' and not f.endswith('_lod2.glb')): continue
    if f.endswith(('_f1.glb', '_f2.glb')) and 'alt' not in b3d: continue  # the tower's alternative height family (tower_f1.glb, ?b3dtower=f1): B3D=all+alt
    if units and os.path.basename(f) == 'landside.glb': continue
    sz = os.path.getsize(f); name = os.path.basename(f)[:-4]
    os.makedirs(f'{O}/data/buildings3d', exist_ok=True)
    if sz >= 14 * 1024 * 1024:
        data = open(f, 'rb').read(); step = PART_MB * 1024 * 1024; n = (len(data) + step - 1) // step
        for i in range(n): open(f'{O}/data/buildings3d/{name}.part{i}.wasm', 'wb').write(data[i * step:(i + 1) * step])
        parts[name] = n
    else: shutil.copy(f, f'{O}/data/buildings3d/' + name + '.wasm')
    nb += sz
if units and b3d != 'none' and b3d != 'lod2':
    for f in glob.glob(f'{S}/data/buildings3d/lsu_img_*'): shutil.copy(f, f'{O}/data/buildings3d/'); nb += os.path.getsize(f)
if parts:
    h = f'{O}/sfo_phone_test.html'; t = open(h).read(); k = "window.SFO_B3D_EXT = '.wasm';"; assert k in t
    open(h, 'w').write(t.replace(k, k + ' window.SFO_B3D_PARTS = ' + json.dumps(parts) + ';', 1))
print('buildings3d:', b3d, '%.1f MB' % (nb / 1e6), 'split:', parts or 'none')
print('files:', sum(len(fs) for _, _, fs in os.walk(O)), '%.1f MB' % (sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(O) for f in fs) / 1e6))
