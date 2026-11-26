// Boot: load the model + meta, wire the controls, expose a small API for tests and screenshots (window.viewer).
// URL parameters (dev / screenshots): ?view=NAME (a named view or a photo-matched camera of the meta file),
// ?cam=x,y,z&tgt=x,y,z&fov=DEG (a free camera in world metres), ?mode=white, ?time=dusk, ?glb=FILE&meta=FILE,
// ?ui=0 (hide the controls), ?still=1 (no animation: one deterministic frame).
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { Stage, toGL } from './stage.js';
import { Materials } from './materials.js';

const CFG = window.HOUSE_CONFIG || { data: '../out/' };
const Q = new URLSearchParams(location.search);
const $ = (id) => document.getElementById(id);
const status = (t) => { $('status').textContent = t; };

const stage = new Stage($('view'));
const mats = new Materials(stage.renderer, Q.get('quality') === 'low' ? 'low' : 'high');
const state = { mode: Q.get('mode') === 'white' ? 'white' : 'full', time: Q.get('time') === 'dusk' ? 'dusk' : 'day', view: null, meta: null };
const viewer = window.viewer = { stage, mats, state, ready: null, errors: [] };
window.addEventListener('error', (e) => viewer.errors.push(String(e.message)));

function applyMode() {
  stage.scene.traverse((o) => {
    if (!o.isMesh || !o.userData.matName) return;
    o.material = state.mode === 'white' ? mats.clay(o.userData.matName) : mats.get(o.userData.matName);
  });
  $('b-mode').setAttribute('aria-pressed', state.mode === 'white');
  stage.needs = true;
}

function applyTime() {
  stage.setTime(state.time);
  mats.setTime(state.time);
  $('b-time').setAttribute('aria-pressed', state.time === 'dusk');
}

function setView(name) {
  const m = state.meta, v = (m.views || {})[name], c = (m.cameras || {})[name];
  if (v) stage.setOrbit(v.pos, v.target, v.fov || 40);
  else if (c) stage.setPhotoCamera(c);
  else return false;
  state.view = name;
  for (const b of document.querySelectorAll('#g-views button')) b.setAttribute('aria-pressed', b.dataset.view === name);
  return true;
}
viewer.setView = setView;
viewer.setMode = (m) => { state.mode = m; applyMode(); };
viewer.setTime = (t) => { state.time = t; applyTime(); };
viewer.renderNow = () => { stage.needs = true; stage.frame(); };

async function boot() {
  const metaUrl = CFG.data + (Q.get('meta') || 'house_meta.json');
  const meta = state.meta = await (await fetch(metaUrl)).json();
  status('Loading the model…');
  const gltf = await new GLTFLoader().loadAsync(CFG.data + (Q.get('glb') || meta.glb || 'house.glb'));
  const root = gltf.scene;
  root.traverse((o) => {
    if (!o.isMesh) return;
    o.userData.matName = o.material.name;
    const k = mats.kind(o.material.name);
    o.castShadow = !(k.glass || k.water || k.noShadow);
    o.receiveShadow = true;
  });
  stage.scene.add(root);
  const box = new THREE.Box3().setFromObject(root);
  const c = meta.centre ? toGL(meta.centre) : box.getCenter(new THREE.Vector3());
  stage.setCentre(c);
  if (meta.sun) stage.setSun(meta.sun.az, meta.sun.el);
  applyMode();
  applyTime();
  const g = $('g-views');
  for (const [name, v] of Object.entries(meta.views || {})) {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = v.label || name;
    b.dataset.view = name;
    b.addEventListener('click', () => setView(name));
    g.append(b);
  }
  const num = (k) => (Q.get(k) || '').split(',').map(Number);
  if (Q.get('cam')) stage.setOrbit(num('cam'), num('tgt'), +(Q.get('fov') || 40));
  else if (!setView(Q.get('view') || meta.start || Object.keys(meta.views || {})[0])) stage.setOrbit([c.x - 22, -c.z - 30, 12], [c.x, -c.z, 3]);
  if (Q.get('ui') === '0') { $('bar').hidden = true; $('status').hidden = true; }
  $('b-mode').addEventListener('click', () => viewer.setMode(state.mode === 'white' ? 'full' : 'white'));
  $('b-time').addEventListener('click', () => viewer.setTime(state.time === 'dusk' ? 'day' : 'dusk'));
  status('');
  const still = Q.get('still') === '1';
  const t0 = performance.now();
  const loop = () => {
    if (mats.tick(still ? 0 : (performance.now() - t0) / 1000) && !still) stage.needs = true;
    stage.frame();
    requestAnimationFrame(loop);
  };
  loop();
  stage.needs = true;
  stage.frame();
  return { triangles: stage.renderer.info.render.triangles, parts: root.children.length };
}

viewer.ready = boot().catch((e) => { status('Could not load the model: ' + e.message); viewer.errors.push(String(e)); throw e; });
