// PC-12 PRO viewer: bootstrap, UI wiring, keyboard shortcuts, picking, render loop, test hooks.
import * as THREE from 'three';
import { Stage, PRESETS, QUALITY, LOOK } from './scene.js';
import { loadGLB, parseGLB, Model, INTERNAL_PARTS } from './model.js';
import { loadMaterialSpec, setLights } from './materials.js';
import { Kinematics } from './kinematics.js';
import { Build } from './build.js';
import { PartsPanel, InfoCard, DrawingViewer, buildSpecs } from './panels.js';

const $ = (id) => document.getElementById(id);
const app = $('app');
const q = new URLSearchParams(location.search);

// ------------------------------------------------------------------ data URLs
// ?data=<base> re-hosts everything next to the page; ?glb= / ?meta= / ?svg=ga,sections override single files.
// Default: window.PC12_CONFIG.data (index.html: '../out/' in the repo, './data/' in the packaged bundle).
// index.html's boot script resolves them (window.PC12_URLS), fetches the metadata and the GLB itself (PC12_META /
// PC12_GLB promises, with the loading bar) and preloads the HDRI and the materials, so the requests below are served
// by those preloads.
const CONFIG = window.PC12_CONFIG || {};
const URLS = window.PC12_URLS || (() => {
  const base = (q.get('data') || CONFIG.data || '../out/').replace(/\/?$/, '/');
  const svg = (q.get('svg') || '').split(',').map((s) => s.trim()).filter(Boolean);
  return { glb: q.get('glb') || base + 'pc12.glb', meta: q.get('meta') || base + 'pc12_meta.json',
    ga: svg[0] || base + 'pc12_ga.svg', sections: svg[1] || base + 'pc12_sections.svg' };
})();
const BOOT = window.PC12_BOOT || { progress() {}, fail: null, unsupported: '' };

// ------------------------------------------------------------------ loading screen
let readyResolve, readyReject;
const ready = new Promise((res, rej) => { readyResolve = res; readyReject = rej; });
ready.catch(() => {});
// every progress report also feeds index.html's stall watchdog ("Still loading…" after 20 s without one)
const setProgress = (frac, text) => {
  $('loadBar').style.width = `${Math.round(Math.max(0, Math.min(1, frac)) * 100)}%`;
  if (text != null) $('loadBytes').textContent = text;
  BOOT.progress();
};
const setStage = (text) => { $('loadMsg').textContent = text; BOOT.progress(); };
// load / first-frame timings (ms since navigation start), reported by viewer.perf()
const PERF = { t: {}, mark(k) { this.t[k] = Math.round(performance.now()); } };
PERF.mark('script');
const yieldFrame = () => new Promise((r) => requestAnimationFrame(() => setTimeout(r, 0)));
function fail(err, what) {
  let msg = `Could not load ${what}.\n${err && err.message ? err.message : err}`;
  if (location.protocol === 'file:') msg += '\n\nOpen the page over HTTP, e.g.\n  python3 -m http.server 8765 --directory pc12\nthen http://localhost:8765/web/';
  if (BOOT.fail) BOOT.fail(msg);          // the loading card's error state + Retry (index.html)
  else {
    const load = $('loading');
    load.classList.add('error');
    load.classList.remove('done');
    $('loadMsg').textContent = msg;
    window.__error = msg;
    window.__ready = true;   // lets headless tests stop waiting
  }
  readyReject(err);
}

let stage, model, kin, build, parts, info, drawings, meta;
const S = {
  explode: { target: 0, cur: 0 },
  cutUser: false, xray: false, lines: false,
  tab: 'build', selected: null, hidden: new Set(), isolate: null,
  paused: false, demo: null, lights: false,
};

async function boot() {
  if (BOOT.unsupported) { fail(new Error(BOOT.unsupported), 'the 3-D view'); return; }
  // the WebGL renderer first: without a context (WebGL off, a blocklisted or lost GPU) nothing is downloaded
  try {
    stage = new Stage($('stage'));
  } catch (e) {
    fail(new Error(`${e && e.message ? e.message : e}\nThis viewer needs WebGL 2: it may be switched off (e.g. iOS Lockdown Mode, a browser setting) or blocked for this graphics driver.`), 'the 3-D view');
    return;
  }
  stage.goTo('three_quarter', { instant: true });
  stage.onContextChange = onContextChange;
  $('glReload').addEventListener('click', () => location.reload());
  // everything is requested at once: metadata, materials, the studio environment and the model.  The boot script
  // (index.html) has already started the metadata and the GLB and drives the loading bar while they download.
  const metaP = window.PC12_META || fetch(URLS.meta).then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status} for ${URLS.meta}`); return r.json(); });
  metaP.catch(() => {});
  const matP = loadMaterialSpec().catch((e) => { console.warn('materials.json unavailable, GLB materials kept:', e.message || e); return null; });
  const envP = stage.loadEnvironment().then(() => PERF.mark('env'));
  setStage('Downloading model…');
  let glbP;
  if (window.PC12_GLB) {
    glbP = window.PC12_GLB.then((buf) => { PERF.mark('glbBytes'); return parseGLB(buf, URLS.glb); });
  } else {
    // no boot script (a page embedding main.js on its own): three's loader, with a monotonic bar
    let total = 0, frac = 0;
    glbP = loadGLB(URLS.glb, (e) => {
      if (!total) total = (!q.get('glb') && meta && meta.stats && meta.stats.glb_bytes) || e.total || 0;
      if (e.loaded > total) total = e.loaded;
      frac = Math.max(frac, total ? 0.92 * e.loaded / total : 0);
      setProgress(frac, total ? `${(e.loaded / 1048576).toFixed(1)} / ${(total / 1048576).toFixed(1)} MB` : `${(e.loaded / 1048576).toFixed(1)} MB`);
    });
  }
  glbP.catch(() => {});
  try { meta = await metaP; PERF.mark('meta'); } catch (e) { fail(e, 'the model metadata (' + URLS.meta + ')'); return; }
  let gltf;
  try { gltf = await glbP; PERF.mark('glb'); } catch (e) { fail(e, 'the 3-D model (' + URLS.glb + ')'); return; }
  setStage('Preparing materials…');
  setProgress(0.94);
  const matSpec = await matP;
  await envP;
  await yieldFrame();
  await init(gltf, matSpec);
}

// WebGL context lost (a backgrounded phone tab, GPU memory pressure): rendering pauses and a note shows until the
// browser restores the context; Stage rebuilds the environment and shadows, then one frame is drawn.  If no restore
// comes within 8 s the note offers a reload.
let glNoteTimer = 0;
function onContextChange(lost) {
  const note = $('glNote');
  clearTimeout(glNoteTimer);
  if (lost) {
    note.hidden = false;
    note.classList.remove('stuck');
    glNoteTimer = setTimeout(() => note.classList.add('stuck'), 8000);
  } else {
    note.hidden = true;
    if (stage) { stage.needsRender = true; forceFrames = Math.max(forceFrames, 2); }
  }
}

// ------------------------------------------------------------------ init
async function init(gltf, matSpec) {
  model = new Model(gltf, meta, { materials: matSpec });
  stage.scene.add(model.root);
  stage.addToContactLayer(model.root);
  stage.setModelBox(model.box, model.silhouettePoints());
  kin = new Kinematics(model);
  build = new Build({ model, meta, scene: stage.scene, labelsEl: $('labels') });
  parts = new PartsPanel({ meta, onSelect: (id) => select(id) });
  info = new InfoCard({ meta });
  drawings = new DrawingViewer({ sheets: [
    { url: URLS.ga, title: 'General arrangement', desc: 'PC12-GA-001 — A1 general arrangement, 1:50: three views, dimensions, stations.' },
    { url: URLS.sections, title: 'Sections', desc: 'PC12-SEC-002 — A2 sections through the fuselage, wing and empennage.' },
  ] });
  buildSpecs(meta);
  buildStepList();
  wireUI();

  build.onChange(() => { refreshModes(); syncBuildUI(); });
  const qs = q.get('step');
  build.setStep(qs == null ? build.n - 1 : isNaN(+qs) ? qs : +qs, { instant: true });
  if (q.get('tab')) setTab(q.get('tab'));
  poseNow();
  syncUI();
  // panel / toolbar insets first, so the first camera fit uses the free part of the viewport
  layoutInsets();
  const cam = q.get('cam');
  stage.goTo(cam && PRESETS[cam] ? cam : 'three_quarter', { instant: true });
  PERF.mark('init');
  // compile the visible materials' shaders before the first frame (parallel where the driver allows),
  // so the page does not freeze on a long first render
  setStage('Compiling shaders…');
  setProgress(0.97);
  await yieldFrame();
  try {
    const R = stage.renderer;
    if (R.extensions.has('KHR_parallel_shader_compile')) await R.compileAsync(stage.scene, stage.camera);
    else R.compile(stage.scene, stage.camera);
  } catch (e) { /* compiled on first render instead */ }
  PERF.mark('compiled');
  setStage('Rendering…');
  setProgress(1);
  requestAnimationFrame(frame);
  // hide the loading screen once the first frame (and its shader compiles) is on screen
  waitFrames(1).then(() => {
    PERF.mark('firstFrame');
    PERF.firstRenderMs = Math.round(stage.stats.lastRenderMs);
    return waitFrames(1);
  }).then(() => {
    $('loading').classList.add('done');
    setTimeout(() => {
      $('loading').hidden = true;
      PERF.mark('ready');
      window.__ready = true;
      readyResolve(hooks);
    }, 450);
  });
}

// ------------------------------------------------------------------ modes
function effectiveCut() {
  return S.cutUser || (build && build.key(build.index) === 'interior');
}
function refreshModes() {
  const i = build.index;
  const cut = effectiveCut();
  if (model.cutaway !== cut || model.xray !== S.xray) { model.cutaway = cut; model.xray = S.xray; model.applyMaterials(); }
  // structure: visible in X-ray, and during the build until the wing skins have landed over it
  // (the ribs run the full chord, so once the skins are on they would poke out of the open
  // flap / aileron coves; tick() calls refreshModes() again when the fly-in ends)
  const iWing = build.indexOf('wing');
  model.structureOn = S.xray || (i >= build.indexOf('structure') && i < iWing) || (i === iWing && build.animating);
  model.updateVisibility();
  poseNow();          // also settles parts that were still flying when the step changed
  syncToolbar();
  if (S.selected) info.show(S.selected, { hint: hintFor(S.selected) });
}

function poseNow() {
  kin.apply();
  model.applyTransforms(S.explode.cur);
  afterTransforms();
  model.root.updateMatrixWorld(true);
  stage.shadowDirty = true;
  stage.needsRender = true;
}
// things that follow the explode / fly-in offsets: the ground drop and the prop blur disc
function afterTransforms() {
  stage.setGround(model.groundY);
  kin.setExplodeView(S.explode.cur);
}

// ------------------------------------------------------------------ selection
const meshRec = new Map();
function hintFor(id) {
  if (id === 'structure') return 'Primary structure is shown in X-ray mode.';
  if (INTERNAL_PARTS.has(id) && !S.xray && !effectiveCut() && !(model.isolate && model.isolate.has(id)))
    return 'Inside the skin: switch on X-ray (X) or Cutaway (C), or Isolate it.';
  return '';
}

function select(id, { frame = true, instant = false } = {}) {
  if (!id || !model.part(id)) { clearSelection(); return; }
  const rec = model.part(id);
  if (!rec.buildVisible) build.setStep(build.n - 1, { instant: true });
  if (S.hidden.size) {
    for (const d of model.descendants(id)) if (S.hidden.has(d)) { S.hidden.delete(d); model.part(d).userHidden = false; }
    model.updateVisibility();
    parts.setHidden(S.hidden);
  }
  if (model.isolate && !model.isolate.has(id)) setIsolate(null);
  if (id === 'structure' && !S.xray) setXray(true);
  if (!app.classList.contains('panel-open')) setPanel(true);
  S.selected = id;
  model.setHighlight('sel', id);
  info.show(id, { hint: hintFor(id) });
  parts.setCurrent(id);
  $('icIsolate').setAttribute('aria-pressed', String(!!(model.isolate && S.isolate === id)));
  // internal parts are framed from further out so the surrounding structure gives context
  if (frame) stage.frameBox(model.worldBox(id), { instant, minDist: INTERNAL_PARTS.has(id) && !S.xray && !effectiveCut() ? 4 : 1.5 });
  stage.needsRender = true;
}

function clearSelection() {
  S.selected = null;
  model.setHighlight('sel', null);
  info.hide();
  parts.setCurrent(null);
  stage.needsRender = true;
}

function setIsolate(id) {
  S.isolate = id;
  model.setIsolate(id);
  $('icIsolate').setAttribute('aria-pressed', String(!!id));
  stage.shadowDirty = true;
  stage.needsRender = true;
  if (S.selected) info.show(S.selected, { hint: hintFor(S.selected) });
}

function hidePart(id) {
  for (const d of model.descendants(id)) { S.hidden.add(d); model.part(d).userHidden = true; }
  model.updateVisibility();
  parts.setHidden(S.hidden);
  if (S.selected && S.hidden.has(S.selected)) clearSelection();
  syncHiddenButtons();
  stage.shadowDirty = true;
  stage.needsRender = true;
}

function showAllParts() {
  for (const id of S.hidden) model.part(id).userHidden = false;
  S.hidden.clear();
  setIsolate(null);
  model.updateVisibility();
  parts.setHidden(S.hidden);
  syncHiddenButtons();
}

function syncHiddenButtons() {
  $('icShowAll').hidden = S.hidden.size === 0;
  $('icShowAll').textContent = `Show hidden (${S.hidden.size})`;
  $('pShowAll').disabled = S.hidden.size === 0 && !model.isolate;
}

// ------------------------------------------------------------------ picking
const raycaster = new THREE.Raycaster();
const ndc = new THREE.Vector2();
function pick(clientX, clientY) {
  stage.camera.updateMatrixWorld();
  const r = stage.renderer.domElement.getBoundingClientRect();
  ndc.set(((clientX - r.left) / r.width) * 2 - 1, -((clientY - r.top) / r.height) * 2 + 1);
  raycaster.setFromCamera(ndc, stage.camera);
  const hits = raycaster.intersectObjects(model.pickables, false);
  const cut = model.cutaway;
  let skin = null;
  for (const h of hits) {
    const m = h.object;
    if (!m.visible) continue;
    const mr = meshRec.get(m);
    if (!mr) continue;
    if (cut && mr.cut && h.point.x < 0) continue;              // clipped away by the cutaway
    if (model.xray && mr.part.xray) { if (!skin) skin = mr.part.id; continue; } // prefer what's inside
    return mr.part.id;
  }
  return skin;
}

let down = null, hoverAt = null, lastHover = 0;
function wirePicking() {
  for (const mr of model.meshRecs) meshRec.set(mr.mesh, mr);
  const cv = stage.renderer.domElement;
  cv.addEventListener('pointerdown', (e) => { down = { x: e.clientX, y: e.clientY, b: e.button }; });
  cv.addEventListener('pointerup', (e) => {
    if (!down) return;
    const moved = Math.hypot(e.clientX - down.x, e.clientY - down.y);
    const b = down.b;
    down = null;
    if (moved > 5 || b !== 0) return;
    const id = pick(e.clientX, e.clientY);
    if (id) select(id);
    else clearSelection();
  });
  cv.addEventListener('pointermove', (e) => {
    if (e.pointerType !== 'mouse' || e.buttons) { hoverAt = null; return; }
    hoverAt = { x: e.clientX, y: e.clientY };
  });
  cv.addEventListener('pointerleave', () => { hoverAt = null; if (model.setHighlight('hover', null)) stage.needsRender = true; });
}

function updateHover(now) {
  if (!hoverAt || now - lastHover < 90 || stage.tween) return;
  lastHover = now;
  const id = pick(hoverAt.x, hoverAt.y);
  hoverAt = null;
  const h = id && id !== S.selected ? id : null;
  if (model.setHighlight('hover', h)) stage.needsRender = true;
  stage.renderer.domElement.style.cursor = id ? 'pointer' : '';
}

// ------------------------------------------------------------------ setters (shared by UI, keys and hooks)
function setExplode(f, { instant = false } = {}) {
  S.explode.target = Math.max(0, Math.min(1.5, +f || 0));
  if (instant) { S.explode.cur = S.explode.target; poseNow(); }
  $('explode').value = S.explode.target;
  $('explodeOut').value = S.explode.target.toFixed(2);
}
function setCutaway(on) { S.cutUser = !!on; refreshModes(); }
function setXray(on) { S.xray = !!on; refreshModes(); }
function setLines(on) { S.lines = !!on; build.setShowAllLines(S.lines); stage.needsRender = true; syncToolbar(); }
function setPaint(on, { instant = false } = {}) { model.setPaint(!!on, instant); stage.needsRender = true; syncToolbar(); }
function setCamera(v, { instant = false } = {}) { stage.goTo(v, { instant }); }
function setStep(i, { instant = false } = {}) { build.playing = false; build.setStep(i, { instant }); if (instant) poseNow(); }
function setGear(v, { instant = false } = {}) { kin.setGear(v, instant); if (instant) poseNow(); syncAnimUI(); }
function setFlaps(d, { instant = false } = {}) { kin.setFlaps(d, instant); if (instant) poseNow(); syncAnimUI(); }
function setDoor(id, v, { instant = false } = {}) { kin.setDoor(id, v, instant); if (instant) poseNow(); syncAnimUI(); }
function setProp(o, { instant = false } = {}) { kin.setProp(o, instant); if (instant) poseNow(); syncAnimUI(); }
function setControls(o, { instant = false } = {}) { kin.setControls(o, instant); if (instant) poseNow(); syncAnimUI(); }
function setNavLights(on) { S.lights = !!on; setLights(S.lights); $('aLights').setAttribute('aria-pressed', String(S.lights)); stage.needsRender = true; }

function neutral({ instant = false } = {}) {
  setControls({ roll: 0, pitch: 0, yaw: 0, stabTrim: 0, ailTrim: 0, rudTrim: 0 }, { instant });
}

function reset() {
  stopDemo();
  setExplode(0);
  S.cutUser = false; S.xray = false;
  setLines(false);
  showAllParts();
  clearSelection();
  neutral();
  kin.setGear(0); kin.setFlaps(0); kin.setDoor('door_airstair', 0); kin.setDoor('door_cargo', 0); kin.setProp({ rpm: 0, pitch: 0 });
  setNavLights(false);
  build.playing = false;
  if (build.index !== build.n - 1) build.setStep(build.n - 1, { instant: true });
  model.setPaint(true, false);
  refreshModes();
  stage.goTo('three_quarter');
  syncUI();
}

// ------------------------------------------------------------------ demo
const waits = [];
let animClock = 0;
function waitAnim(sec, tk) {
  return new Promise((res) => waits.push({ until: animClock + sec, res, tk }));
}
function stopDemo() {
  if (S.demo) { S.demo.cancelled = true; S.demo = null; }
  for (const w of waits.splice(0)) w.res();
  $('aDemo').textContent = '▶ Demo';
}
async function demo() {
  if (S.demo) { stopDemo(); return; }
  const tk = (S.demo = { cancelled: false });
  $('aDemo').textContent = '■ Stop demo';
  const w = async (s) => { await waitAnim(s, tk); if (tk.cancelled) throw tk; };
  try {
    if (build.index !== build.n - 1) build.setStep(build.n - 1, { instant: true });
    stage.goTo('three_quarter');
    setProp({ rpm: 1000, pitch: 0 }); await w(2.2);
    setProp({ rpm: 1700 }); await w(1.5);
    setFlaps(15); await w(1.8);
    for (const [k, v, t] of [['roll', 1, 1.1], ['roll', -1, 1.4], ['roll', 0, 0.8], ['pitch', 1, 1.1], ['pitch', -1, 1.3],
      ['pitch', 0, 0.8], ['yaw', 1, 1.1], ['yaw', -1, 1.3], ['yaw', 0, 0.8]]) { setControls({ [k]: v }); await w(t); }
    setGear('up'); await w(6.0);
    setFlaps(0); await w(1.6);
    setControls({ stabTrim: -3 }); await w(2.8);
    setControls({ stabTrim: 0 }); await w(2.6);
    stage.goTo('gear_bay'); await w(1.0);
    setGear('down'); await w(6.0);
    stage.goTo('three_quarter');
    setFlaps(40); await w(3.8);
    setProp({ pitch: -38 }); await w(3.0);
    setProp({ pitch: 62, rpm: 0 }); await w(3.5);
    stage.goTo('side');
    setDoor('door_airstair', 1); setDoor('door_cargo', 1); await w(3.2);
    setDoor('door_airstair', 0); setDoor('door_cargo', 0); await w(3.0);
    setFlaps(0); setProp({ pitch: 0 });
    stage.goTo('three_quarter');
  } catch (e) { if (e !== tk) throw e; }
  if (S.demo === tk) stopDemo();
}

// ------------------------------------------------------------------ UI
function setTab(name) {
  const tabs = [...document.querySelectorAll('#tabs [role="tab"]')];
  const t = tabs.find((b) => b.id === 'tab-' + name);
  if (!t) return;
  const body = $('panelBody');
  tabScroll[S.tab] = body.scrollTop;
  S.tab = name;
  for (const b of tabs) {
    const on = b === t;
    b.setAttribute('aria-selected', String(on));
    b.tabIndex = on ? 0 : -1;
    $(b.getAttribute('aria-controls')).hidden = !on;
  }
  app.classList.toggle('drawings', name === 'drawings');
  drawings.show(name === 'drawings');
  $('toolbar').hidden = name === 'drawings';
  if (name === 'drawings') { info.hide(); } else if (S.selected) info.show(S.selected, { hint: hintFor(S.selected) });
  if (!app.classList.contains('panel-open')) setPanel(true);
  body.scrollTop = tabScroll[name] || 0;
  syncBuildUI();
  stage.needsRender = true;
}
const tabScroll = {};

function setPanel(open) {
  app.classList.toggle('panel-open', open);
  $('panelToggle').setAttribute('aria-expanded', String(open));
  $('panelOpen').hidden = open || isNarrow();
  requestAnimationFrame(layoutInsets);
  setTimeout(layoutInsets, 300);
}
// bottom sheet: narrow portrait screens (viewer.css uses the same query; short landscape screens keep a side panel)
const narrowMQ = window.matchMedia('(max-width: 760px) and (min-height: 501px)');
const isNarrow = () => narrowMQ.matches;
function layoutInsets() {
  const open = app.classList.contains('panel-open');
  const p = $('panel'), tb = $('toolbar');
  // the toolbar floats over the top of the canvas: keep fitted views below it
  const top = tb.hidden ? 0 : Math.max(0, Math.round(tb.getBoundingClientRect().bottom - $('stage').getBoundingClientRect().top + 6));
  // safe-area insets (notch, home indicator; viewer.css #safeProbe): the collapsed sheet keeps its 92 px header above
  // the home-indicator band, and fitted views stay clear of a landscape notch
  const sp = getComputedStyle($('safeProbe')), px = (k) => parseFloat(sp[k]) || 0;
  if (isNarrow()) stage.setInsets(0, open ? p.offsetHeight : 92 + px('paddingBottom'), top, px('paddingLeft'));
  else stage.setInsets(open ? p.offsetWidth : px('paddingRight'), px('paddingBottom'), top, px('paddingLeft'));
  $('panelOpen').hidden = open || isNarrow();
}

function buildStepList() {
  const ol = $('stepList');
  ol.replaceChildren();
  meta.steps.forEach((s, i) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.innerHTML = `<span class="n">${String(i + 1).padStart(2, '0')}</span><span></span>`;
    b.lastChild.textContent = s.title;
    b.addEventListener('click', () => { build.playing = false; build.setStep(i); });
    const li = document.createElement('li');
    li.append(b);
    ol.append(li);
  });
}

function syncBuildUI() {
  if (!build) return;
  const i = build.index, s = meta.steps[i];
  $('bCounter').textContent = `Step ${i + 1} of ${build.n}`;
  $('bTitle').textContent = s.title;
  $('bText').textContent = s.text;
  $('bText').parentElement.scrollTop = 0;
  const chips = $('bParts');
  chips.replaceChildren();
  for (const id of s.parts) {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = id;
    b.addEventListener('click', () => select(id));
    chips.append(b);
  }
  [...$('stepList').children].forEach((li, k) => {
    li.classList.toggle('done', k < i);
    li.classList.toggle('current', k === i);
    li.firstChild.setAttribute('aria-current', k === i ? 'step' : 'false');
  });
  // keep the current step in view inside the list only (never scroll the whole panel)
  const ol = $('stepList'), cur = ol.children[i];
  if (cur && ol.scrollHeight > ol.clientHeight + 2) {
    if (cur.offsetTop < ol.scrollTop || cur.offsetTop + cur.offsetHeight > ol.scrollTop + ol.clientHeight)
      ol.scrollTop = Math.max(0, cur.offsetTop - ol.clientHeight / 2);
  }
  $('bPlay').textContent = build.playing ? '❚❚ Pause' : '▶ Play';
  $('bPlay').setAttribute('aria-label', build.playing ? 'Pause build (Space)' : 'Play build (Space)');
  $('bPrev').disabled = i === 0;
  $('bNext').disabled = i === build.n - 1;
  const cap = $('stepCaption');
  const showCap = (i < build.n - 1 || build.playing) && S.tab !== 'drawings';
  cap.hidden = !showCap;
  if (showCap) cap.textContent = `${i + 1}/${build.n} · ${s.title}${effectiveCut() && !S.cutUser ? ' · cutaway' : ''}`;
  syncToolbar();
}

function syncToolbar() {
  const pressed = (id, on) => $(id).setAttribute('aria-pressed', String(!!on));
  pressed('tCut', S.cutUser);
  pressed('tXray', S.xray);
  pressed('tLines', S.lines);
  pressed('tPrimer', model && !model.painted);
}

function syncAnimUI() {
  if (!kin) return;
  const t = kin.t;
  for (const b of document.querySelectorAll('[data-rpm]')) b.setAttribute('aria-pressed', String(+b.dataset.rpm === t.rpm));
  for (const b of document.querySelectorAll('[data-flap]')) b.setAttribute('aria-pressed', String(+b.dataset.flap === t.flaps));
  $('sPitch').value = t.pitch; $('oPitch').value = `${t.pitch.toFixed(0)}°`;
  $('sRoll').value = t.roll; $('sPitchCtl').value = t.pitchCmd; $('sYaw').value = t.yaw;
  $('sStab').value = t.stabTrim; $('sAilTrim').value = t.ailTrim; $('sRudTrim').value = t.rudTrim;
  $('oRoll').value = t.roll.toFixed(2); $('oPitchCtl').value = t.pitchCmd.toFixed(2); $('oYaw').value = t.yaw.toFixed(2);
  $('oStab').value = `${t.stabTrim.toFixed(1)}°`; $('oAilTrim').value = `${t.ailTrim.toFixed(1)}°`; $('oRudTrim').value = `${t.rudTrim.toFixed(1)}°`;
  $('aAirstair').setAttribute('aria-pressed', String(t.door_airstair > 0.5));
  $('aCargo').setAttribute('aria-pressed', String(t.door_cargo > 0.5));
  updateReadouts();
}

const SURF_ROWS = [
  ['Aileron R', 'aileron_R'], ['Aileron L', 'aileron_L'], ['Aileron tab R', 'ail_tab_R'], ['Aileron tab L', 'ail_tab_L'],
  ['Elevators', 'elevator_R'], ['Rudder', 'rudder'], ['Rudder tab', 'rudder_tab'], ['Stabiliser', 'stabilizer'],
];
let surfCells = null;
function updateReadouts() {
  const c = kin.c, g = kin.gear, D = kin.defl;
  $('rProp').textContent = `${Math.round(c.rpm).toLocaleString('en-US')} rpm · ${c.pitch.toFixed(0)}°`;
  // nose doors close only once locked up; with the gear down (or stopped between the locks) they stay open
  const status = g.pos === 0 && g.target === 0 && g.door === 1 ? 'DOWN' : g.pos === 1 && g.door === 0 ? 'UP'
    : g.pos !== g.target ? (g.door < 1 ? 'doors opening' : g.target > g.pos ? 'retracting' : 'extending')
    : g.pos >= 1 ? 'doors closing' : g.pos <= 0 ? 'doors opening' : 'stopped · doors open';
  $('rGear').textContent = `${status} · ${Math.round(g.pos * 100)} %`;
  $('sGear').value = g.pos; $('oGear').value = `${Math.round(g.pos * 100)} %`;
  $('rFlaps').textContent = `${c.flaps.toFixed(1)}°`;
  if (!surfCells) {
    const tb = $('surfTable');
    surfCells = SURF_ROWS.map(([label]) => {
      const tr = document.createElement('tr');
      const a = document.createElement('td'), b = document.createElement('td');
      a.textContent = label;
      tr.append(a, b);
      tb.append(tr);
      return b;
    });
  }
  SURF_ROWS.forEach(([, id], k) => {
    const v = D[id] || 0;
    surfCells[k].textContent = `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(1)}°`;
  });
}

function wireUI() {
  wirePicking();
  // toolbar
  for (const b of document.querySelectorAll('[data-cam]')) b.addEventListener('click', () => setCamera(b.dataset.cam));
  $('explode').addEventListener('input', (e) => setExplode(e.target.value));
  $('tCut').addEventListener('click', () => setCutaway(!S.cutUser));
  $('tXray').addEventListener('click', () => setXray(!S.xray));
  $('tLines').addEventListener('click', () => setLines(!S.lines));
  $('tPrimer').addEventListener('click', () => setPaint(!model.painted));
  $('tReset').addEventListener('click', reset);
  $('tHelp').addEventListener('click', () => toggleHelp());
  $('helpClose').addEventListener('click', () => toggleHelp(false));
  $('help').addEventListener('click', (e) => { if (e.target === $('help')) toggleHelp(false); });
  // panel
  $('panelToggle').addEventListener('click', () => setPanel(false));
  $('panelOpen').addEventListener('click', () => setPanel(true));
  $('sheetHandle').addEventListener('click', () => setPanel(!app.classList.contains('panel-open')));
  wireSheetHeader();
  narrowMQ.addEventListener('change', () => { setPanel(app.classList.contains('panel-open')); });
  new ResizeObserver(() => { stage.resize(); layoutInsets(); }).observe($('stage'));
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => stage.setTheme(e.matches));
  // tabs (arrow keys move between tabs)
  const tabs = [...document.querySelectorAll('#tabs [role="tab"]')];
  tabs.forEach((t, k) => {
    t.addEventListener('click', () => setTab(t.id.slice(4)));
    t.addEventListener('keydown', (e) => {
      let j = null;
      if (e.key === 'ArrowRight') j = (k + 1) % tabs.length;
      else if (e.key === 'ArrowLeft') j = (k - 1 + tabs.length) % tabs.length;
      else if (e.key === 'Home') j = 0;
      else if (e.key === 'End') j = tabs.length - 1;
      if (j == null) return;
      e.preventDefault();
      e.stopPropagation();
      setTab(tabs[j].id.slice(4));
      tabs[j].focus();
    });
  });
  // build
  $('bPrev').addEventListener('click', () => build.prev());
  $('bNext').addEventListener('click', () => { build.playing = false; build.next(); });
  $('bPlay').addEventListener('click', () => build.play());
  $('bAll').addEventListener('click', () => { build.playing = false; build.setStep(build.n - 1, { instant: true }); poseNow(); });
  // animate
  const manual = () => { if (S.demo) stopDemo(); };
  $('aDemo').addEventListener('click', demo);
  $('aCentre').addEventListener('click', () => { manual(); neutral(); });
  for (const b of document.querySelectorAll('[data-rpm]')) b.addEventListener('click', () => { manual(); setProp({ rpm: +b.dataset.rpm }); });
  $('sPitch').addEventListener('input', (e) => { manual(); setProp({ pitch: +e.target.value }); });
  $('aReverse').addEventListener('click', () => { manual(); setProp({ pitch: -38 }); });
  $('aFine').addEventListener('click', () => { manual(); setProp({ pitch: 0 }); });
  $('aFeather').addEventListener('click', () => { manual(); setProp({ pitch: 62 }); });
  $('aGearUp').addEventListener('click', () => { manual(); setGear('up'); });
  $('aGearDown').addEventListener('click', () => { manual(); setGear('down'); });
  $('sGear').addEventListener('input', (e) => { manual(); setGear(+e.target.value, { instant: true }); });
  for (const b of document.querySelectorAll('[data-flap]')) b.addEventListener('click', () => { manual(); setFlaps(+b.dataset.flap); });
  $('aAirstair').addEventListener('click', () => { manual(); setDoor('door_airstair', kin.t.door_airstair > 0.5 ? 0 : 1); });
  $('aCargo').addEventListener('click', () => { manual(); setDoor('door_cargo', kin.t.door_cargo > 0.5 ? 0 : 1); });
  $('aLights').addEventListener('click', () => setNavLights(!S.lights));
  const ctl = (id, key) => $(id).addEventListener('input', (e) => { manual(); setControls({ [key]: +e.target.value }); });
  ctl('sRoll', 'roll'); ctl('sPitchCtl', 'pitch'); ctl('sYaw', 'yaw');
  ctl('sStab', 'stabTrim'); ctl('sAilTrim', 'ailTrim'); ctl('sRudTrim', 'rudTrim');
  // double-click a control slider to centre it
  for (const [id, key] of [['sRoll', 'roll'], ['sPitchCtl', 'pitch'], ['sYaw', 'yaw'], ['sStab', 'stabTrim'], ['sAilTrim', 'ailTrim'], ['sRudTrim', 'rudTrim']])
    $(id).addEventListener('dblclick', () => setControls({ [key]: 0 }));
  // parts / info card
  $('icClose').addEventListener('click', clearSelection);
  $('icFrame').addEventListener('click', () => S.selected && stage.frameBox(model.worldBox(S.selected)));
  $('icIsolate').addEventListener('click', () => { if (!S.selected) return; setIsolate(S.isolate === S.selected ? null : S.selected); if (S.isolate) stage.frameBox(model.worldBox(S.selected)); });
  $('icHide').addEventListener('click', () => S.selected && hidePart(S.selected));
  $('icShowAll').addEventListener('click', showAllParts);
  $('pShowAll').addEventListener('click', showAllParts);
  syncHiddenButtons();
  // drawings
  for (const b of document.querySelectorAll('[data-sheet]')) b.addEventListener('click', () => drawings.select(+b.dataset.sheet));
  $('dFit').addEventListener('click', () => drawings.fit());
  $('dIn').addEventListener('click', () => drawings.zoomCentre(1.4));
  $('dOut').addEventListener('click', () => drawings.zoomCentre(1 / 1.4));
  // keyboard
  window.addEventListener('keydown', onKey);
  // a mouse/touch click must not leave focus on the button (Space would re-activate it instead of
  // playing the build); keyboard focus (Tab) is unaffected
  document.addEventListener('pointerup', (e) => {
    const b = e.target && e.target.closest && e.target.closest('button, summary');
    if (b && document.activeElement === b) b.blur();
  });
}

// Bottom sheet (narrow screens): a tap on the header outside its buttons toggles the sheet like the grab bar, and a
// vertical swipe on the header opens (up) or closes (down) it.
function wireSheetHeader() {
  const head = document.querySelector('#panel .panel-head');
  let sw = null, swiped = false;
  head.addEventListener('pointerdown', (e) => { sw = isNarrow() ? { x: e.clientX, y: e.clientY } : null; });
  head.addEventListener('pointercancel', () => { sw = null; });
  head.addEventListener('pointerup', (e) => {
    if (!sw) return;
    const dx = e.clientX - sw.x, dy = e.clientY - sw.y;
    sw = null;
    if (Math.abs(dy) > 24 && Math.abs(dy) > 1.5 * Math.abs(dx)) {
      swiped = true;                         // the click that may follow must not toggle it back
      setTimeout(() => { swiped = false; }, 400);
      setPanel(dy < 0);
    }
  });
  // capture: runs before the grab bar's own click listener
  head.addEventListener('click', (e) => {
    if (!isNarrow()) return;
    if (swiped) { swiped = false; e.stopPropagation(); e.preventDefault(); return; }
    if (e.target.closest('button, a, input')) return;
    setPanel(!app.classList.contains('panel-open'));
  }, true);
}

function toggleHelp(on = $('help').hidden) {
  $('help').hidden = !on;
  if (on) $('helpClose').focus();
}

const FLAP_CYCLE = [0, 15, 30, 40];
const RPM_CYCLE = [0, 1000, 1550, 1700];
const NON_TEXT_INPUT = /^(range|checkbox|radio|button|submit|reset|color)$/i;
function onKey(e) {
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  const t = e.target, tag = t && t.tagName;
  // only text entry swallows the shortcuts
  if ((tag === 'INPUT' && !NON_TEXT_INPUT.test(t.type)) || tag === 'TEXTAREA' || tag === 'SELECT' || (t && t.isContentEditable)) {
    if (e.key === 'Escape') t.blur();
    return;
  }
  // a focused slider keeps its own keys; letters and Space still reach the shortcuts
  if (tag === 'INPUT' && t.type === 'range' && /^(Arrow|Home$|End$|Page)/.test(e.key)) return;
  if ((tag === 'BUTTON' || tag === 'SUMMARY' || tag === 'A') && (e.key === ' ' || e.key === 'Enter')) return;
  if (!model) return;
  const k = e.key;
  let handled = true;
  switch (k) {
    case 'ArrowRight': build.playing = false; build.next(); break;
    case 'ArrowLeft': build.prev(); break;
    case ' ': build.play(); break;
    case 'e': case 'E': setExplode(S.explode.target > 0.01 ? 0 : 1); break;
    case 'x': case 'X': setXray(!S.xray); break;
    case 'c': case 'C': setCutaway(!S.cutUser); break;
    case 'l': case 'L': setLines(!S.lines); break;
    case 'g': case 'G': stopDemo(); setGear(kin.gear.target > 0.5 ? 'down' : 'up'); break;
    case 'f': case 'F': { stopDemo(); const i = FLAP_CYCLE.indexOf(kin.t.flaps); setFlaps(FLAP_CYCLE[(i + 1) % FLAP_CYCLE.length]); break; }
    case 'p': case 'P': { stopDemo(); const i = RPM_CYCLE.indexOf(kin.t.rpm); setProp({ rpm: RPM_CYCLE[(i + 1) % RPM_CYCLE.length] }); break; }
    case 'r': case 'R': reset(); break;
    case '?': toggleHelp(); break;
    case 'Escape':
      if (tag === 'INPUT') t.blur();
      if (!$('help').hidden) toggleHelp(false);
      else { clearSelection(); if (S.isolate) setIsolate(null); }
      break;
    default: {
      const n = +k;
      const names = Object.keys(PRESETS);
      if (n >= 1 && n <= names.length) setCamera(names[n - 1]);
      else handled = false;
    }
  }
  if (handled) e.preventDefault();
}

function syncUI() {
  syncToolbar();
  syncBuildUI();
  syncAnimUI();
  $('explode').value = S.explode.target;
  $('explodeOut').value = S.explode.target.toFixed(2);
}

// ------------------------------------------------------------------ render loop
let last = performance.now(), frameCount = 0, forceFrames = 0, readoutT = 0, shadowSkip = 0;
let readoutsDirty = false, kinMoving = false;
const frameWaiters = [];
function waitFrames(n = 1) {
  forceFrames = Math.max(forceFrames, n);
  return new Promise((res) => frameWaiters.push({ at: frameCount + n, res }));
}

// advance all animation state by adt seconds; returns true if the pose changed
function tick(adt) {
  animClock += adt;
  let posed = false;
  kinMoving = kin.update(adt);
  if (kinMoving) { posed = true; readoutsDirty = true; }
  const wasBuilding = build.playing || build.animating;
  const wasAnimating = build.animating;
  if (build.update(adt)) posed = true;
  const ex = S.explode;
  if (ex.cur !== ex.target && adt > 0) {
    ex.cur += (ex.target - ex.cur) * (1 - Math.exp(-7 * adt));
    if (Math.abs(ex.target - ex.cur) < 5e-4) ex.cur = ex.target;
    posed = true;
  }
  if (model.updatePaint(adt)) stage.needsRender = true;
  if (posed) {
    model.applyTransforms(ex.cur);
    afterTransforms();
    // a spinning prop alone only needs an occasional key-shadow refresh (and no contact-shadow render)
    if (!kin.onlySpin || build.animating || ex.cur !== ex.target) stage.shadowDirty = true;
    else if (++shadowSkip % 4 === 0) stage.keyShadowOnly();
    stage.needsRender = true;
  }
  if (waits.length) {
    for (let i = waits.length - 1; i >= 0; i--) {
      const w = waits[i];
      if (animClock >= w.until || w.tk.cancelled) { waits.splice(i, 1); w.res(); }
    }
  }
  if (wasAnimating && !build.animating) refreshModes();      // e.g. wing structure hides once the skins land
  if (wasBuilding && !build.playing && !build.animating) syncBuildUI();
  return posed;
}

function frame(now) {
  requestAnimationFrame(frame);
  const dt = Math.min(0.1, Math.max(0, (now - last) / 1000));
  last = now;
  const posed = tick(S.paused ? 0 : dt);
  if (stage.update(dt)) stage.needsRender = true;
  stage.applyQuality();
  if (forceFrames > 0) { forceFrames--; stage.needsRender = true; }
  stage.busy = posed;
  // shadows skipped while animating on the low tier (Stage.render): one more frame once the motion stops
  if (!posed && (stage.shadowDirty || stage.contactDirty)) stage.needsRender = true;
  // interior light by viewpoint (and how far a cabin door is open)
  if (stage.needsRender) {
    const wasInside = model.camInside;
    model.updateCabin(stage.camera.position, S.explode.cur, Math.max(kin.c.door_airstair, kin.c.door_cargo));
    if (model.camInside !== wasInside) stage.shadowDirty = true;      // parts hidden inside the cabin (antennas)
  }
  if (stage.needsRender) {
    stage.render();
    frameCount++;
    build.updateLabels(stage.camera, stage.size.w, stage.size.h);
    for (let i = frameWaiters.length - 1; i >= 0; i--) {
      if (frameCount >= frameWaiters[i].at) { frameWaiters[i].res(); frameWaiters.splice(i, 1); }
    }
    if (frameWaiters.length) forceFrames = Math.max(forceFrames, 1);
  }
  updateHover(now);
  // readouts: at most every 100 ms while things move, plus once when they stop (never stale)
  const moving = kinMoving || kin.gearMoving;
  if (readoutsDirty && (!moving || now - readoutT > 100)) { readoutT = now; readoutsDirty = false; updateReadouts(); }
}

// ------------------------------------------------------------------ test hooks
const v3 = (a) => new THREE.Vector3().fromArray(a);
const boxOut = (b) => ({ min: b.min.toArray(), max: b.max.toArray(), center: b.getCenter(new THREE.Vector3()).toArray(), size: b.getSize(new THREE.Vector3()).toArray() });
const hooks = {
  ready,
  get state() {
    if (!model) return { ready: false };
    const g = kin.gear, c = kin.c;
    return {
      ready: true, step: build.index, stepKey: build.key(build.index), playing: build.playing,
      explode: S.explode.cur, explodeTarget: S.explode.target,
      cutaway: model.cutaway, cutawayUser: S.cutUser, xray: S.xray, construction: S.lines, paint: model.painted,
      paintSweep: model.U.paintSweep.value, tab: S.tab, selected: S.selected, hovered: model.hovered, isolate: S.isolate, hidden: [...S.hidden],
      gear: { pos: g.pos, door: g.door, target: g.target, moving: kin.gearMoving,
        noseDeg: kin.surf.gear_nose && kin.surf.gear_nose.angle, mainRDeg: kin.surf.gear_main_R && kin.surf.gear_main_R.angle,
        noseDoorDeg: kin.surf.gear_door_NR && kin.surf.gear_door_NR.angle },
      flaps: c.flaps, doors: { airstair: c.door_airstair, cargo: c.door_cargo },
      prop: { rpm: c.rpm, pitch: c.pitch, angle: c.propAngle },
      controls: { roll: c.roll, pitch: c.pitchCmd, yaw: c.yaw, stabTrim: c.stabTrim, ailTrim: c.ailTrim, rudTrim: c.rudTrim },
      deflections: { ...kin.defl }, camera: stage.cameraState(), paused: S.paused, frames: frameCount,
      demo: !!S.demo, lights: S.lights, contextLost: stage.contextLost, camInside: model.camInside, structureVisible: model.structureOn, groundY: stage.groundY, propDiscPush: kin.push,
      cameraPreset: stage.preset,
      linesVisible: build.root.children.reduce((n, g) => n + (g.visible ? g.children.length : 0), 0),
      loading: !$('loading').hidden,
    };
  },
  setStep: (i, o = {}) => setStep(i, o),
  setExplode: (f, o = {}) => setExplode(f, o),
  setCutaway: (on) => setCutaway(on),
  setXray: (on) => setXray(on),
  setConstruction: (on) => setLines(on),
  setPaint: (on, o = {}) => setPaint(on, o),
  setCamera: (v, o = {}) => setCamera(v, o),
  setGear: (v, o = {}) => setGear(v, o),
  setFlaps: (d, o = {}) => setFlaps(d, o),
  setDoor: (id, v, o = {}) => setDoor(id, v, o),
  setProp: (p, o = {}) => setProp(p, o),
  setControls: (p, o = {}) => setControls(p, o),
  setLights: (on) => setNavLights(on),
  select: (id, o = {}) => select(id, { frame: true, ...o }),
  isolate: (id) => setIsolate(id || null),
  hide: (id) => hidePart(id),
  showAll: () => showAllParts(),
  tab: (name) => setTab(name),
  panel: (open) => setPanel(!!open),
  reset: () => reset(),
  demo: () => demo(),
  play: (on) => { build.play(on); },
  pause: (on = true) => { S.paused = !!on; },
  partWorldBox: (id) => { poseNow(); return boxOut(model.worldBox(id)); },
  nodeWorldPoint: (id, p = [0, 0, 0]) => { poseNow(); const r = model.part(id); return r ? r.node.localToWorld(v3(p)).toArray() : null; },
  worldToLocal: (id, p) => { poseNow(); const r = model.part(id); return r ? r.node.worldToLocal(v3(p)).toArray() : null; },
  partExtras: (id) => { const r = model.part(id); return r ? JSON.parse(JSON.stringify(r.ex)) : null; },
  parts: () => model.list.map((p) => p.id),
  visibleParts: () => model.list.filter((p) => p.shown).map((p) => p.id),
  frames: (n = 2) => waitFrames(n),
  // deterministic time stepping for tests: advance every animation by `sec` in 1/60 s steps
  advance: (sec, step = 1 / 60) => {
    for (let t = 0; t < sec - 1e-9; t += step) tick(Math.min(step, sec - t));
    stage.update(0);
    poseNow();
    return hooks.state;
  },
  pick: (x, y) => pick(x, y),
  // load timings (ms since navigation start) + render statistics
  perf: () => ({
    marks: { ...PERF.t }, firstRenderMs: PERF.firstRenderMs,
    quality: { ...stage.quality, dpr: stage.dpr }, env: stage.envSource, look: { ...LOOK, hdr: undefined },
    renders: { ...stage.stats }, frames: frameCount,
    info: model ? { calls: stage.renderer.info.render.calls, triangles: stage.renderer.info.render.triangles,
      programs: stage.renderer.info.programs ? stage.renderer.info.programs.length : null,
      geometries: stage.renderer.info.memory.geometries, textures: stage.renderer.info.memory.textures } : null,
    materials: model ? model.materialInfo : null,
  }),
  // render n frames back to back and return the mean / max ms per frame (a 1-pixel readPixels after
  // each render waits for the GPU; gl.finish() does not block in Chromium)
  bench: (n = 5, { contact = false } = {}) => {
    const gl = stage.renderer.getContext(), ms = [], px = new Uint8Array(4);
    for (let i = 0; i < n; i++) {
      if (contact) stage.shadowDirty = true;
      const t0 = performance.now();
      stage.render();
      gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
      ms.push(performance.now() - t0);
    }
    return { mean: ms.reduce((a, b) => a + b, 0) / n, max: Math.max(...ms), min: Math.min(...ms), n };
  },
  // world point (glTF axes) -> CSS pixel position in the page
  project: (p) => {
    poseNow();
    stage.camera.updateMatrixWorld();
    const v = v3(p).project(stage.camera), r = stage.renderer.domElement.getBoundingClientRect();
    return [r.left + ((v.x + 1) / 2) * r.width, r.top + ((1 - v.y) / 2) * r.height, v.z];
  },
};
Object.defineProperty(hooks, '_internals', { get: () => ({ THREE, stage, model, kin, build }) });   // for debugging
window.viewer = hooks;

boot().catch((e) => fail(e, 'the viewer'));
