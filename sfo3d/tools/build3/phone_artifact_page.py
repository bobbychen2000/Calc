"""Assemble the phone-test artifact page (see phone_artifact.sh): inline live.css and the app bundle, add a test card
that reports backend (WebGPU / WebGL 2), tier, fps, frame-time p50/p95, load time, canvas and GPU; copy the supporting
files. Snapshot mode (artifacts cannot fetch live data), low-resolution liveries."""
import glob, json, os, shutil, sys
S, O = sys.argv[1], sys.argv[2]
os.makedirs(O, exist_ok=True)
tmpl = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'phone_artifact_template.html')).read()
bundle = open(f'{S}/out/build3/live3.bundle.js').read()
assert '</script' not in bundle
# close-out round 3 (integration-4): more rows on the test card, so the owner's next phone test answers what the
# headless runs cannot: (1) whether the artifact page may compile WebAssembly (the meshopt / KTX2 decoders need it; the
# artifact CSP is unverified - a CSP without 'wasm-unsafe-eval' / 'unsafe-eval' makes WebAssembly.compile throw), probed
# with the 8-byte empty module; (2) memory. Nothing is sent anywhere.
# Fix round 2 (verifier v5): performance.memory is the V8 heap only (Chromium only, bucketed; n/a on iOS Safari) and leaves
# out the ArrayBuffer backing stores where the geometry lives, so the memory row adds what the page can count itself on
# every browser - the bytes of the scene's geometry buffers (unique BufferAttribute arrays + indices under SFO.R.engine.scene)
# and three.js' texture estimate (SFO.R.debugInfo().texMB) - plus performance.measureUserAgentSpecificMemory() where the
# page is cross-origin isolated (its total includes ArrayBuffers). "Copy results" is built by this probe alone: one
# capture-phase handler composes the whole text from the card's rows (the template's included), writes the clipboard once
# and stops the template's own handler (round 3 had two writeText calls in one gesture, the second appending these rows).
PROBE_ROWS = ('<div class="row"><span class="k">WebAssembly</span><span id="pt-wasm">–</span></div>'
              '<div class="row"><span class="k">JS heap (V8 only)</span><span id="pt-heap">–</span></div>'
              '<div class="row"><span class="k">Geometry / textures</span><span id="pt-mem">–</span></div>')
PROBE_JS = r"""<script>
(function () {
  var $ = function (id) { return document.getElementById(id); }, r = { wasm: 'probing', heap: null, mem: null, ua: null };
  function show() { if ($('pt-wasm')) $('pt-wasm').textContent = r.wasm; if ($('pt-heap')) $('pt-heap').textContent = r.heap || 'n/a (no performance.memory)';
    if ($('pt-mem')) $('pt-mem').textContent = (r.mem || '–') + (r.ua ? ' · UA total ' + r.ua : ''); }
  try {
    if (typeof WebAssembly !== 'object') r.wasm = 'no WebAssembly object';
    else WebAssembly.compile(new Uint8Array([0, 97, 115, 109, 1, 0, 0, 0])).then(function () { r.wasm = 'compiles (meshopt / KTX2 decoders possible)'; show(); },
      function (e) { r.wasm = 'blocked: ' + String(e && e.message || e).slice(0, 160); show(); });
  } catch (e) { r.wasm = 'blocked: ' + String(e && e.message || e).slice(0, 160); }
  function geoMB() {   // unique geometry ArrayBuffer bytes in the three.js scene (attributes + indices; shared arrays once)
    var S = window.SFO && SFO.R && SFO.R.engine && SFO.R.engine.scene; if (!S || !S.traverse) return null;
    var seen = new Set(), b = 0;
    S.traverse(function (o) { var g = o.geometry; if (!g || !g.attributes) return; var A = [];
      for (var k in g.attributes) A.push(g.attributes[k]); if (g.index) A.push(g.index);
      for (var i = 0; i < A.length; i++) { var a = A[i] && (A[i].array || (A[i].data && A[i].data.array)); if (a && a.buffer && !seen.has(a.buffer)) { seen.add(a.buffer); b += a.buffer.byteLength; } } });
    return b / 1048576;
  }
  function poll() {
    var m = performance.memory; if (m) r.heap = (m.usedJSHeapSize / 1048576).toFixed(0) + ' / ' + (m.totalJSHeapSize / 1048576).toFixed(0) + ' MB';
    try { var g = geoMB(), t = window.SFO && SFO.R && SFO.R.debugInfo ? SFO.R.debugInfo().texMB : null;
      if (g != null) r.mem = 'geometry ' + g.toFixed(0) + ' MB' + (t != null ? ' · textures ~' + Number(t).toFixed(0) + ' MB' : ''); } catch (e) { r.mem = 'n/a (' + String(e.message || e).slice(0, 60) + ')'; }
    show();
  }
  setInterval(poll, 3000);
  if (window.crossOriginIsolated && performance.measureUserAgentSpecificMemory) {
    var ua = function () { performance.measureUserAgentSpecificMemory().then(function (x) { r.ua = (x.bytes / 1048576).toFixed(0) + ' MB'; show(); }, function () {}); };
    setTimeout(ua, 20000); setInterval(ua, 60000);
  }
  function text() {
    var L = ['SFO Live 3D phone test'], rows = document.querySelectorAll('#ptest .body .row');
    for (var i = 0; i < rows.length; i++) { var s = rows[i].querySelectorAll('span'); if (s.length >= 2) L.push(s[0].textContent + ': ' + s[1].textContent); }
    L.push('state: ' + ($('pt-state') ? $('pt-state').textContent : '?'), 'navigator.gpu: ' + (navigator.gpu ? 'yes' : 'no'), 'dpr: ' + (window.devicePixelRatio || 1), 'ua: ' + navigator.userAgent);
    if (window.__sfoError) L.push('error: ' + String(window.__sfoError).slice(0, 300));
    return L.join('\n');
  }
  document.addEventListener('click', function (e) {
    if (!e.target || e.target.id !== 'pt-copy') return;
    e.stopImmediatePropagation(); poll();
    var t = text(), out = $('pt-out'), btn = e.target; if (out) { out.textContent = t; out.hidden = false; }
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(t).then(function () { btn.textContent = 'Copied'; }, function () { btn.textContent = 'Select text below'; });
    else btn.textContent = 'Select text below';
  }, true);
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
