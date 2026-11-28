// Boot: load the model + meta, wire the controls, expose a small API for tests and screenshots (window.viewer).
// URL parameters (dev / screenshots): ?view=NAME (a named view or a photo-matched camera of the meta file),
// ?cam=x,y,z&tgt=x,y,z&fov=DEG (a free camera in world metres), ?mode=white, ?time=dusk, ?glb=FILE&meta=FILE,
// ?hide=part,part (leave parts out: faster test renders), ?photo=1 (whole photographs cast onto the model: a test
// layer), ?swatch=0 (no photo swatches on the materials), ?quality=low|high (procedural texture sizes),
// ?phone=1|0 (force the phone tier on or off), ?ui=0 (hide the controls), ?still=1 (no animation: one
// deterministic frame), ?hq=N (refine the still over N passes).
//
// Rendering is on demand: a frame is drawn when the camera, the light or a material changed, and the gentle motion
// (water, leaves) runs for a few seconds after the last input only, so an untouched page draws nothing (battery).
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { Stage, toGL } from './stage.js';
import { Materials, CLAY, CLAY_GLASS, CLAY_WATER } from './materials.js';
import { PhotoLayer } from './photo.js';

const CFG = window.HOUSE_CONFIG || { data: '../out/' };
const Q = new URLSearchParams(location.search);
const $ = (id) => document.getElementById(id);
const media = (q) => { try { return matchMedia(q).matches; } catch (e) { return false; } };
const PHONE = Q.has('phone') ? Q.get('phone') === '1' : media('(pointer: coarse)') && Math.min(screen.width, screen.height) < 820;
const STILL = Q.get('still') === '1';
const ANIMATE = !STILL && !media('(prefers-reduced-motion: reduce)');
const ANIM_AFTER_INPUT = 8000;      // ms of motion after the last input
const ANIM_STEP = 33;               // ms between animation steps (~30 Hz)

// the status line, optionally with one action button (Reload, Retry)
function status(text, action) {
  const el = $('status');
  el.textContent = text;
  if (action) {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = action.label;
    b.addEventListener('click', action.fn);
    el.append(' ', b);
  }
}
const reload = { label: 'Reload', fn: () => location.reload() };

let stage;
try {
  stage = new Stage($('view'), { phone: PHONE });
} catch (e) {
  status('This browser cannot show 3-D graphics: WebGL is turned off or not available (for example in Lockdown Mode).');
  throw e;
}
const mats = new Materials(stage.renderer, Q.get('quality') === 'low' ? 'low' : 'high');
const photo = new PhotoLayer(stage.renderer);
mats.hook = (m) => { photo.hook(m); stage.picture.hook(m); };
for (const m of [CLAY, CLAY_GLASS, CLAY_WATER]) stage.picture.hook(m);
// ?hq=N refines stills over N passes (soft shadows, sky-light shading, antialiasing); hq=0 turns it off
if (Q.has('hq')) { stage.refine = +Q.get('hq') > 0; stage.picture.passes = Math.max(1, +Q.get('hq')); }
const state = { mode: (Q.get('mode') || CFG.mode) === 'white' ? 'white' : 'full', time: Q.get('time') === 'dusk' ? 'dusk' : 'day', view: null, meta: null,
  photo: Q.get('photo') === '1' };
const viewer = window.viewer = { stage, mats, state, photo, phone: PHONE, ready: null, errors: [] };
const logError = (s) => { viewer.errors.push(String(s).slice(0, 2000)); if (viewer.errors.length > 20) viewer.errors.shift(); };
window.addEventListener('error', (e) => logError(e.message));

// a shader that does not compile on this GPU leaves its surfaces out: say so instead of failing silently
let shaderFailed = false;
stage.renderer.debug.onShaderError = (gl, program, vs, fs) => {
  const log = [gl.getProgramInfoLog(program), gl.getShaderInfoLog(vs), gl.getShaderInfoLog(fs)].filter(Boolean).join('\n');
  console.error('THREE.WebGLProgram: shader error\n' + log);
  logError('shader: ' + log);
  shaderFailed = true;
};

// the system may take the GPU back (memory pressure, the app in the background); stage.js restores what three does not
let lostTimer = 0;
stage.onLost = () => {
  status('The graphics were reset by the system. Restoring…');
  lostTimer = setTimeout(() => status('The graphics did not come back.', reload), 5000);
};
stage.onRestored = () => { clearTimeout(lostTimer); status(''); poke(); };

// input keeps the motion going for a while
let lastInput = performance.now();
const poke = () => { lastInput = performance.now(); stage.needs = true; };

function applyMode() {
  stage.scene.traverse((o) => {
    if (!o.isMesh || !o.userData.matName) return;
    o.material = state.mode === 'white' ? mats.clay(o.userData.matName) : mats.get(o.userData.matName);
  });
  $('b-mode').setAttribute('aria-pressed', state.mode === 'white');
  stage.shadowsChanged();             // the clay materials drop the leaves' cut-outs: the casters change
  applyPhoto();
}

// the photo layer shows in daylight only (the photographs are daylight ones)
function applyPhoto() {
  photo.mix.value = state.photo && state.time === 'day' && photo.n ? 1 : 0;
  const b = $('b-photo');
  if (b) { b.hidden = !photo.n; b.setAttribute('aria-pressed', state.photo); b.disabled = state.time !== 'day' || state.mode === 'white'; }
  stage.needs = true;
}

function applyTime() {
  stage.setTime(state.time);
  mats.ctx.envGain = stage.envGain;
  mats.setTime(state.time);
  $('b-time').setAttribute('aria-pressed', state.time === 'dusk');
  applyPhoto();
}

function setView(name) {
  const m = state.meta, v = (m.views || {})[name], c = (m.cameras || {})[name];
  if (v) stage.setOrbit(v.pos, v.target, v.fov || 40, { fit: v.fit, aspect: v.aspect });
  else if (c) stage.setPhotoCamera(c);
  else return false;
  state.view = name;
  for (const b of document.querySelectorAll('#g-views button')) b.setAttribute('aria-pressed', b.dataset.view === name);
  return true;
}
viewer.setView = (n) => { const ok = setView(n); poke(); return ok; };
viewer.setMode = (m) => { state.mode = m; applyMode(); poke(); };
viewer.setTime = (t) => { state.time = t; applyTime(); poke(); };
viewer.setPhoto = (on) => { state.photo = !!on; applyPhoto(); poke(); };
viewer.renderNow = () => { stage.needs = true; stage.frame(); };
// resolves when the still has converged (immediately when refinement is off)
viewer.settle = () => new Promise((res) => {
  const tick = () => { if (!stage.refine || (stage.picture.done && !stage.needs)) res(stage.picture.n); else requestAnimationFrame(tick); };
  tick();
});

const yieldFrame = () => new Promise((r) => setTimeout(r, 0));

// one text file, streamed, with a stall timeout and two retries; onBytes(n) reports progress (n < 0 takes it back)
async function fetchText(url, onBytes) {
  for (let attempt = 0; ; attempt++) {
    const ctl = new AbortController();
    let timer = 0, got = 0;
    const arm = () => { clearTimeout(timer); timer = setTimeout(() => ctl.abort(), 30000); };
    try {
      arm();
      const r = await fetch(url, { signal: ctl.signal });
      if (!r.ok) throw new Error(`${url.split('/').pop()}: HTTP ${r.status}`);
      let t = '';
      if (!r.body) {
        t = await r.text();
      } else {
        const reader = r.body.getReader(), dec = new TextDecoder();
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          arm();
          t += dec.decode(value, { stream: true });
          got += value.length;
          onBytes(value.length);
        }
        t += dec.decode();
      }
      clearTimeout(timer);
      return t;
    } catch (e) {
      clearTimeout(timer);
      onBytes(-got);
      if (attempt >= 2) throw new Error(ctl.signal.aborted ? 'the download stalled' : (e && e.message) || String(e));
      await new Promise((r) => setTimeout(r, 800 * (attempt + 1)));
    }
  }
}

// base64 -> bytes without a per-character callback (that path needed ~15x the memory in JavaScriptCore)
function fromBase64(t) {
  if (typeof Uint8Array.fromBase64 === 'function') return Uint8Array.fromBase64(t);
  const s = atob(t), b = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) b[i] = s.charCodeAt(i);
  return b;
}

// The packaged bundle carries the model as base64 text parts (CFG.b64 = { file: parts }); the dev page loads the GLB.
// Each part is decoded as soon as it has arrived and its text dropped.
async function loadGLB(name) {
  const loader = new GLTFLoader(), parts = (CFG.b64 || {})[name];
  if (!parts) return loader.loadAsync(CFG.data + name);
  let got = 0;
  const total = (state.meta && state.meta.stats ? state.meta.stats.bytes : 0) * 4 / 3;
  const onBytes = (n) => {
    got += n;
    if (total) status(`Loading the model… ${Math.max(0, Math.min(99, Math.round(100 * got / total)))} %`);
  };
  const bins = await Promise.all(Array.from({ length: parts }, async (_, i) => fromBase64(await fetchText(`${CFG.data}${name}.b64.${i}.txt`, onBytes))));
  status('Unpacking the model…');
  await yieldFrame();
  let all = bins[0];
  if (bins.length > 1) {
    all = new Uint8Array(bins.reduce((n, b) => n + b.length, 0));
    let o = 0;
    for (let i = 0; i < bins.length; i++) { all.set(bins[i], o); o += bins[i].length; bins[i] = null; }
  }
  return new Promise((res, rej) => loader.parse(all.buffer, '', res, rej));
}

async function boot() {
  const metaUrl = CFG.data + (Q.get('meta') || 'house_meta.json');
  const meta = state.meta = JSON.parse(await fetchText(metaUrl, () => {}));
  status('Loading the model…');
  mats.onChange = () => { stage.needs = true; };
  if (Q.get('swatch') !== '0') mats.setSwatches(meta.swatches, CFG.data);
  if (Q.get('photo') === '1') await photo.load(meta, CFG.data);
  const gltf = await loadGLB(Q.get('glb') || meta.glb || 'house.glb');
  status('Preparing the scene…');
  await yieldFrame();
  const root = gltf.scene;
  const names = new Set();
  root.traverse((o) => {
    if (!o.isMesh) return;
    o.userData.matName = o.material.name;
    mats.seed(o.material);                 // a name the look library lacks keeps the GLB's own colour / roughness
    names.add(o.material.name);
    const k = mats.kind(o.material.name);
    o.castShadow = !(k.glass || k.water || k.noShadow);
    o.receiveShadow = true;
  });
  // (an empty name would match the root itself, whose glTF name is empty: filter it out)
  for (const n of (Q.get('hide') || '').split(',').map((x) => x.trim()).filter(Boolean)) {
    const o = root.getObjectByName(n);
    if (o && o !== root) o.visible = false;
  }
  stage.scene.add(root);
  root.updateMatrixWorld(true);
  photo.bake(stage.scene, root);
  const box = new THREE.Box3().setFromObject(root);
  const c = meta.centre ? toGL(meta.centre) : box.getCenter(new THREE.Vector3());
  stage.setCentre(c);
  mats.ctx.envGain = stage.envGain;
  if (meta.sun) stage.setSun(meta.sun.az, meta.sun.el);
  // the procedural textures are generated here: one material at a time, so the page keeps answering and shows progress
  if (state.mode === 'full') {
    const list = [...names];
    let t = performance.now();
    for (let i = 0; i < list.length; i++) {
      mats.get(list[i]);
      if (performance.now() - t > 40) {
        status(`Preparing the materials… ${Math.round(100 * (i + 1) / list.length)} %`);
        await yieldFrame();
        t = performance.now();
      }
    }
  }
  applyMode();
  applyTime();
  const g = $('g-views');
  for (const [name, v] of Object.entries(meta.views || {})) {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = v.label || name;
    b.dataset.view = name;
    b.addEventListener('click', () => viewer.setView(name));
    g.append(b);
  }
  const num = (k) => (Q.get(k) || '').split(',').map(Number);
  if (Q.get('cam')) stage.setOrbit(num('cam'), num('tgt'), +(Q.get('fov') || 40));
  else if (!setView(Q.get('view') || meta.start || Object.keys(meta.views || {})[0])) stage.setOrbit([c.x - 22, -c.z - 30, 12], [c.x, -c.z, 3]);
  // the shaders: compiled before the first frame, without freezing the page where the browser can do it in parallel
  status('Preparing the shaders…');
  await yieldFrame();
  try {
    if (stage.renderer.compileAsync) await stage.renderer.compileAsync(stage.scene, stage.camera);
  } catch (e) { logError('compile: ' + e); }
  if (Q.get('ui') === '0') { $('bar').hidden = true; $('status').hidden = true; }
  $('b-mode').addEventListener('click', () => viewer.setMode(state.mode === 'white' ? 'full' : 'white'));
  if (CFG.whiteOnly) $('b-mode').hidden = true;      // a white-model-only bundle (package.py --white)
  $('b-time').addEventListener('click', () => viewer.setTime(state.time === 'dusk' ? 'day' : 'dusk'));
  $('b-photo').addEventListener('click', () => viewer.setPhoto(!state.photo));
  for (const b of document.querySelectorAll('#bar button')) b.disabled = false;
  applyPhoto();
  stage.controls.addEventListener('start', poke);
  stage.controls.addEventListener('end', poke);
  stage.canvas.addEventListener('pointerdown', poke);
  stage.canvas.addEventListener('wheel', poke, { passive: true });
  document.addEventListener('visibilitychange', () => { if (!document.hidden) poke(); });
  status('');

  // the loop: survives an exception in one frame (reported once; after three in a row it slows to once a second)
  let clock = 0, lastT = performance.now(), lastStep = 0, fails = 0;
  mats.tick(0);
  const loop = () => {
    let ok = true;
    try {
      const now = performance.now(), dt = Math.min(0.1, (now - lastT) / 1000);
      lastT = now;
      if (ANIMATE && now - lastInput < ANIM_AFTER_INPUT) {
        clock += dt;
        if (now - lastStep >= ANIM_STEP && mats.tick(clock)) { lastStep = now; stage.needs = true; }
      }
      stage.frame();
    } catch (e) {
      ok = false;
      logError(e && e.stack || e);
      if (++fails === 1) status('Drawing failed: ' + (e && e.message || e), reload);
    }
    if (ok && fails) { fails = 0; status(''); }
    if (fails >= 3) setTimeout(() => requestAnimationFrame(loop), 1000);
    else requestAnimationFrame(loop);
  };
  poke();                             // a few seconds of motion as the scene appears
  loop();
  if (shaderFailed) status('Some surfaces could not be drawn on this device.');
  return { triangles: stage.renderer.info.render.triangles, parts: root.children.length, phone: PHONE };
}

viewer.ready = boot().catch((e) => {
  status('Could not load the model: ' + (e && e.message || e), reload);
  logError(e);
  throw e;
});
