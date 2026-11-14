// Dev model viewer (hwd3d Phase 3, M2): ONE detailed aircraft drawn by the hwd3d renderer (sun, 3 shadow cascades,
// sky / env reflections, bloom) at full quality on the HWD ramp, or on a neutral concrete pad when the world fails to
// load (?world=0 forces the pad). Not the app: js/live/** is not touched; the aircraft is a js/aircraft/detailed.js
// DetailedAircraft exactly as Phase 3b will use it.
//
// URL parameters
//   model=PC12|SF50          ICAO type (js/aircraft/models.js registry; default PC12)
//   cam=<preset>             front34 | rear34 | side | chase | front | top | gear | nose | tail | under   (default front34)
//   eye=x,y,z&tgt=x,y,z      a custom camera in the AIRCRAFT frame (+x forward, +y up, +z starboard, origin = main-gear
//                            contact), fov=deg; drag / wheel / pinch orbit the target when not in shot mode
//   gear=0..1 (1 = down)     flaps=deg   rpm=propeller rpm (or rotor=rad/s)   bpitch=blade pitch deg
//   ctl=roll,pitch,yaw (-1..1)   trim=stab deg   doors=door_airstair:1,door_cargo:0.5
//   at=ramp|run28L|rwy28L|x,z   hdg=deg true   alt=m (origin above the ground)   apitch / aroll = aircraft attitude (deg)
//   t=<ISO UTC> (default 2026-11-13T20:30Z, 12:30 PST)   metar=<raw>   lights=nav,beacon,strobe,landing,taxi
//   world=0 (neutral pad)   scale=<render scale>   shot=1 (no HUD; window.HWDM.shot(opts) returns a JPEG / PNG data URL)
//   alpha=0..1               the screen-door fade js/live/aircraft.js sets on a re-placement (default 1)
import { initGL, Mesh } from '../js/gl.js';
import { Renderer } from '../js/renderer.js';
import { Scene } from '../js/scene.js';
import { Geo } from '../js/geom.js';
import { OBJ_VS, OBJ_FS } from '../js/shaders/objects.js';
import '../js/shaders/ground.js';   // chunks 'vout' / 'fout' (the obj shader of the neutral pad needs them)
import { AppEnv } from '../js/env/app_env.js';
import { applyEnvToRenderer } from '../js/env/render_env.js';
import { setLightViewer, setLightFrame, setLightEnv, DAY_GAIN } from '../js/env/aircraft_lights.js';
import { gaDims } from '../js/aircraft/ga_dims.js';
import { DetailedAircraft } from '../js/aircraft/detailed.js';
import { loadModel, MODELS, withModelFrame } from '../js/aircraft/models.js';
import { m4 } from '../js/math.js';

const q = new URLSearchParams(location.search);
const SHOT = q.has('shot'); if (SHOT) document.body.classList.add('shot');
const hud = document.getElementById('hud'), ui = document.getElementById('ui');
// the live parameter set: the URL, then HWDM.set({...}) (model_shot.mjs changes the pose / camera without a reload)
const P = Object.fromEntries(q.entries());
const has = (k) => P[k] != null && P[k] !== '';
const num = (k, d) => (has(k) && isFinite(+P[k]) ? +P[k] : d);
const vec = (k) => has(k) ? String(P[k]).split(',').map(Number) : null;
const D2R = Math.PI / 180;
const canvas = document.getElementById('c');
const scale = num('scale', Math.min(window.devicePixelRatio || 1, 2));
function size() { return [Math.max(64, Math.round(innerWidth * scale)), Math.max(64, Math.round(innerHeight * scale))]; }
let [W, H] = size(); canvas.width = W; canvas.height = H;
window.ANISO = 8;
initGL(canvas);
const R = new Renderer(W, H, { msaa: 4, shadowRes: 4096 });   // one quality level (OD1)
const TYPE = (q.get('model') || 'PC12').toUpperCase();

// ---------------------------------------------------------------- world (HWD) or neutral pad
let world = null, site = null, worldMode = 'pad', worldErr = null;
async function buildWorld() {
  if (q.get('world') !== '0') {
    try {
      const [{ buildSite }, { buildHwdWorld }, { HWD_AIRPORT }] = await Promise.all([import('../js/world/site.js'), import('../js/live/world.js'), import('../data/hwd_airport.js')]);
      site = buildSite(HWD_AIRPORT);
      world = buildHwdWorld(R, HWD_AIRPORT, { site, quality: 'high', naip: q.get('ground') !== 'procedural', log: () => {} });
      worldMode = 'hwd'; return world;
    } catch (e) { worldErr = String(e && e.message || e); console.warn('world failed, neutral pad:', worldErr); world = null; site = null; }
  }
  const { makeCloudTexture, makeNoiseTexture } = await import('../js/world/textures.js');
  if (!R.progs.obj) R.addProgram('obj', OBJ_VS, OBJ_FS);
  const g = new Geo(), poly = []; for (let i = 0; i < 64; i++) { const a = -i / 64 * Math.PI * 2; poly.push([Math.cos(a) * 300, Math.sin(a) * 300]); }
  g.extrude(poly, -0.5, 0, [0.42, 0.41, 0.39, 1], [0.85, 0, 0, 0], [0.42, 0.41, 0.39, 1], [0.85, 0, 0, 0]);   // plain concrete-grey PBR (mat 0)
  const pad = new Mesh(g.data());
  world = { items: [{ mesh: pad, prog: 'obj', model: m4.ident(), bbox: [-300, -1, -300, 300, 1, 300], castShadow: false, noCull: true }], textures: { clouds: makeCloudTexture(11), noise: makeNoiseTexture() },
    site: null, staticSprites: () => [], ready: Promise.resolve(), stats: {} };
  return world;
}
const gy = (x, z) => site ? site.groundY(x, z) : 0;

// ---------------------------------------------------------------- placement
function placement() {
  const at = P.at || 'ramp';
  let x = 0, z = 0, hdg = num('hdg', 135);
  if (site) {
    const A = site.anchors;
    if (at === 'ramp') [x, z] = A.aprons['Green Ramp'];
    else if (at === 'run28L') [x, z] = A.aprons['28L Run-up'];
    else if (at === 'rwy28L') { const t = A.thresholds['28L'], e = A.thresholds['28L_end']; const L = Math.hypot(t[0] - e[0], t[1] - e[1]); const u = [(t[0] - e[0]) / L, (t[1] - e[1]) / L];
      // 300 m down runway 28L from its threshold, on the centreline, heading along it (geo.js hdgVec = [sin, -cos])
      x = t[0] + u[0] * 300; z = t[1] + u[1] * 300; if (!has('hdg')) hdg = (Math.atan2(u[0], -u[1]) / D2R + 360) % 360; }
    else if (/^-?[\d.]+,-?[\d.]+$/.test(at)) [x, z] = at.split(',').map(Number);
  }
  return { x, z, hdg };
}

// ---------------------------------------------------------------- environment (as dev/world.js)
const T = q.get('t') || '2026-11-13T20:30:00Z';
const env = new AppEnv({ mode: 'live', search: '?t=' + T + (q.get('metar') ? '&metar=' + encodeURIComponent(q.get('metar')) : ''), station: 'KHWD' });
const obsT = Date.parse(T) - 36 * 60e3, iso = new Date(obsT).toISOString();
if (!q.get('metar')) env.setReports([{ rawOb: 'METAR KHWD ' + iso.slice(8, 10) + iso.slice(11, 13) + '54Z 29008KT 10SM FEW060 19/12 A2974', obsTime: obsT / 1000 }]);
const post = { exposure: 0.45, shutter: 0, bloom: 0.012, vignette: 0.18, grain: 0.006, sat: 1.0 };
function applyEnv(force) { const E = env.update(Date.now()); const r = applyEnvToRenderer(R, world, E, { quality: 'high', force }); post.exposure = r.exposure; if (r.changed) setLightEnv(E, DAY_GAIN / 258); return E; }

// ---------------------------------------------------------------- aircraft
const PRESETS = {
  front34: { eye: [13.5, 2.6, 11.5], tgt: [0.3, 1.7, 0], fov: 36 },
  rear34: { eye: [-19, 3.6, 12.5], tgt: [-1.6, 2.0, 0], fov: 36 },
  side: { eye: [-1.2, 1.9, 27], tgt: [-1.2, 1.9, 0], fov: 36 },
  chase: { eye: [-24, 1.3, 4.5], tgt: [1.5, 1.8, 0], fov: 34 },
  front: { eye: [22, 1.7, 0.001], tgt: [0, 1.7, 0], fov: 40 },
  top: { eye: [-1, 45, 0.001], tgt: [-1, 0, 0], fov: 30 },
  gear: { eye: [5.5, 0.85, 7.0], tgt: [0.8, 0.75, 1.4], fov: 46 },
  nose: { eye: [8.5, 1.9, 4.8], tgt: [3.2, 1.55, 0], fov: 44 },
  tail: { eye: [-10.5, 5.0, 6.5], tgt: [-7.2, 3.4, 0], fov: 44 },
  under: { eye: [-4, -3.2, 10], tgt: [0.8, 0.9, 0], fov: 42 },
};
const cam = {};
// presets are framed for the PC-12 (14.4 m): other models scale them by their length; a custom eye / tgt is not scaled
function setCam() { Object.assign(cam, PRESETS[P.cam] || PRESETS.front34); cam.preset = !vec('eye') && !vec('tgt'); if (vec('eye')) cam.eye = vec('eye'); if (vec('tgt')) cam.tgt = vec('tgt'); if (has('fov')) cam.fov = num('fov', cam.fov); }
setCam();
let ac = null, place = null;
function poseAircraft() {
  const p = place, alt = num('alt', 0);
  ac.pos = [p.x, gy(p.x, p.z) + alt, p.z]; ac.groundRef = gy(p.x, p.z); ac.fwd = [Math.sin(p.hdg * D2R), 0, -Math.cos(p.hdg * D2R)];
  ac.pitch = num('apitch', 0) * D2R; ac.roll = num('aroll', 0) * D2R;
  ac.gear = num('gear', 1); ac.alpha = Math.max(0, Math.min(1, num('alpha', 1)));
  ac.rotor = has('rotor') ? num('rotor', 0) : num('rpm', 0) / 60 * 2 * Math.PI;
  ac.setFlaps(num('flaps', 0), true);
  const c = vec('ctl') || [0, 0, 0];
  const doors = {}; for (const kv of String(P.doors || '').split(',').filter(Boolean)) { const [k, v] = kv.split(':'); doors[k] = +v; }
  ac.setControls({ roll: c[0], pitch: c[1], yaw: c[2], stabTrim: num('trim', 0), bladePitch: num('bpitch', 0), doors }, true);
  const L = String(P.lights || '').split(',');
  ac.lightsOn = { nav: L.includes('nav'), beacon: L.includes('beacon'), strobe: L.includes('strobe'), landing: L.includes('landing'), taxi: L.includes('taxi') };
}
// camera: aircraft-frame eye / target -> world (heading only: a chase camera does not roll with the aircraft)
function camera() {
  const f = ac.fwd, r = [-f[2], 0, f[0]], P = ac.pos;
  const w = (l) => [P[0] + f[0] * l[0] + r[0] * l[2], P[1] + l[1], P[2] + f[2] * l[0] + r[2] * l[2]];
  // portrait screens (phones): the presets are framed for 16:9; back the eye away from the target to keep the width
  const a = W / H, k = a < 1 ? Math.min(2.4, (16 / 9) / a * 0.62) : 1;
  const inf = ac.info, sc = cam.preset && inf ? (inf.bbox[3] - inf.bbox[0]) / 14.4 : 1;
  const E0 = cam.eye.map(v => v * sc), T0 = cam.tgt.map(v => v * sc);
  const eye = k === 1 ? E0 : T0.map((t, i) => t + (E0[i] - t) * k);
  const pos = w(eye), tg = w(T0); const dir = [tg[0] - pos[0], tg[1] - pos[1], tg[2] - pos[2]]; const dl = Math.hypot(...dir); dir.forEach((v, i) => { dir[i] = v / dl; });
  const up = Math.abs(dir[1]) > 0.999 ? [f[0], 0, f[2]] : [0, 1, 0];
  return { pos, dir, up, fov: cam.fov * D2R, near: Math.max(0.05, Math.min(0.3, dl * 0.01)), split: Math.max(300, dl * 12), far: 40000, shadowSplits: [Math.max(30, dl * 2.2), Math.max(250, dl * 10), 2500] };
}
// ---------------------------------------------------------------- render
let scene = null, frames = 0, last = performance.now(), paused = false;
function render(t = performance.now()) {
  const C = camera(); const dt = Math.min(0.1, (t - last) / 1000); last = t;
  ac.step(dt);
  setLightViewer(C.pos, 2 * Math.tan(C.fov / 2) / Math.max(1, R.H)); setLightFrame(t / 1000);
  const fr = scene.frame(t / 1000, C.pos);
  R.render(fr, C, t / 1000, post); scene.commit(); R.present(canvas.width, canvas.height); frames++;
}
function hudText() {
  const i = ac.info, E = R.envState;
  hud.textContent = `${TYPE} · ${ac.loaded ? 'detailed model' : ac.error ? 'PLACEHOLDER (' + ac.error + ')' : 'loading…'} · world ${worldMode}${worldErr ? ' (' + worldErr + ')' : ''} · ${W}x${H}\n` +
    (i ? `${i.tris} tris · ${i.parts} parts · ${i.movers} movers · L ${(i.bbox[3] - i.bbox[0]).toFixed(2)} span ${(i.bbox[5] - i.bbox[2]).toFixed(2)} H ${i.bbox[4].toFixed(2)} m · wheelbase ${i.wheelbase && i.wheelbase.toFixed(2)} track ${i.track && i.track.toFixed(2)}\n` : '') +
    `gear ${ac.gear.toFixed(2)} · flaps ${ac.flaps.toFixed(0)}° · rotor ${(ac.rotor * 60 / 2 / Math.PI).toFixed(0)} rpm` + (E ? ` · sun az ${E.sun.az.toFixed(0)}° el ${E.sun.el.toFixed(1)}°` : '');
}
// shot: render n frames, return the final frame as a data URL (JPEG quality jq, or PNG)
async function shot({ n = 3, type = 'image/jpeg', jq = 0.9 } = {}) {
  for (let i = 0; i < n; i++) render(1000 + i * 33);
  const px = R.readPixels(); const c2 = document.createElement('canvas'); c2.width = R.W; c2.height = R.H;
  const cx = c2.getContext('2d'); const id = cx.createImageData(R.W, R.H);
  for (let y = 0; y < R.H; y++) id.data.set(px.subarray((R.H - 1 - y) * R.W * 4, (R.H - y) * R.W * 4), y * R.W * 4);
  cx.putImageData(id, 0, 0); window.__lastShot = c2; return c2.toDataURL(type, jq);
}
const reencode = (jq) => window.__lastShot.toDataURL('image/jpeg', jq);
// ---------------------------------------------------------------- controls (drag = orbit about the target, wheel / pinch = zoom)
function orbit(dYaw, dPitch, k = 1) {
  const e = cam.eye, t = cam.tgt; let v = [e[0] - t[0], e[1] - t[1], e[2] - t[2]]; let d = Math.hypot(...v) * k;
  let yaw = Math.atan2(v[2], v[0]) + dYaw, pit = Math.max(-1.45, Math.min(1.5, Math.asin(Math.max(-1, Math.min(1, v[1] / Math.hypot(...v)))) + dPitch));
  d = Math.max(2, Math.min(400, d)); cam.eye = [t[0] + d * Math.cos(pit) * Math.cos(yaw), t[1] + d * Math.sin(pit), t[2] + d * Math.cos(pit) * Math.sin(yaw)];
}
const ptrs = new Map(); let pinch0 = null;
canvas.addEventListener('pointerdown', e => { canvas.setPointerCapture(e.pointerId); ptrs.set(e.pointerId, [e.clientX, e.clientY]); if (ptrs.size === 2) { const [a, b] = [...ptrs.values()]; pinch0 = Math.hypot(a[0] - b[0], a[1] - b[1]); } });
canvas.addEventListener('pointermove', e => {
  const p = ptrs.get(e.pointerId); if (!p) return;
  if (ptrs.size === 1) orbit(-(e.clientX - p[0]) * 0.006, (e.clientY - p[1]) * 0.006);
  ptrs.set(e.pointerId, [e.clientX, e.clientY]);
  if (ptrs.size === 2 && pinch0) { const [a, b] = [...ptrs.values()]; const d = Math.hypot(a[0] - b[0], a[1] - b[1]); orbit(0, 0, pinch0 / Math.max(1, d)); pinch0 = d; }
});
const up = e => { ptrs.delete(e.pointerId); if (ptrs.size < 2) pinch0 = null; };
canvas.addEventListener('pointerup', up); canvas.addEventListener('pointercancel', up);
canvas.addEventListener('wheel', e => { e.preventDefault(); orbit(0, 0, Math.exp(e.deltaY * 0.001)); }, { passive: false });
addEventListener('resize', () => { [W, H] = size(); canvas.width = W; canvas.height = H; R.resize(W, H); });
function buildUI() {
  for (const k of Object.keys(PRESETS)) { const b = document.createElement('button'); b.textContent = k; b.onclick = () => Object.assign(cam, PRESETS[k]); ui.appendChild(b); }
  const slider = (label, min, max, step, get, set) => { const l = document.createElement('label'); l.textContent = label; const s = document.createElement('input'); s.type = 'range'; s.min = min; s.max = max; s.step = step; s.value = get(); s.oninput = () => set(+s.value); l.appendChild(s); ui.appendChild(l); return s; };
  const gs = slider('gear', 0, 1, 0.01, () => ac.gear, (v) => { ac.gear = v; });
  slider('flaps', 0, 40, 1, () => ac.flapsTarget, (v) => ac.setFlaps(v));
  slider('rpm', 0, 1700, 10, () => ac.rotor * 60 / 2 / Math.PI, (v) => { ac.rotor = v / 60 * 2 * Math.PI; });
  slider('roll', -1, 1, 0.05, () => 0, (v) => ac.setControls({ roll: v }));
  slider('pitch', -1, 1, 0.05, () => 0, (v) => ac.setControls({ pitch: v }));
  slider('yaw', -1, 1, 0.05, () => 0, (v) => ac.setControls({ yaw: v }));
  const cyc = document.createElement('button'); cyc.textContent = 'cycle gear'; let dirn = -1;
  cyc.onclick = () => { const t0 = performance.now(), g0 = ac.gear, g1 = dirn < 0 ? 0 : 1; dirn = -dirn; const run = () => { const s = Math.min(1, (performance.now() - t0) / 6000); ac.gear = g0 + (g1 - g0) * s; gs.value = ac.gear; if (s < 1) requestAnimationFrame(run); }; run(); };
  ui.appendChild(cyc);
}
// ---------------------------------------------------------------- go
// set({...}): merge parameters (same names as the URL; null deletes) and re-pose; a new `at` / `hdg` re-places the aircraft
function set(o) { for (const k in o) { if (o[k] == null) delete P[k]; else P[k] = String(o[k]); } if ('at' in o || 'hdg' in o) place = placement(); setCam(); poseAircraft(); if ('t' in o) console.warn('t is read at load only'); return { gear: ac.gear, flaps: ac.flaps, rotor: ac.rotor }; }
window.HWDM = { R, cam, PRESETS, P, post, set, render, shot, reencode, pause: (v = true) => { paused = !!v; }, hud: () => hudText(), applyEnv, get ac() { return ac; }, get scene() { return scene; }, get world() { return world; }, worldMode: () => worldMode };
(async () => {
  try {
    await buildWorld();
    scene = new Scene(R, world); if (world.staticSprites) scene.staticLights.push(world.staticSprites);
    applyEnv(true);
    place = placement();
    // the dims record with the model's measured gear / length layout (withModelFrame), as Phase 3b will hand it to traffic
    const dims = withModelFrame(gaDims(TYPE)) || { type: TYPE, L: 10, span: 10, H: 3, cls: 'jet', wing: { span: 10, rootLE: 3, rootC: 2, tipC: 1, pos: 'low' }, hstab: { x: 8, span: 4, rootC: 1 }, xMain: 5, xNose: 1, R: 0.7, Hc: 1.2, track: 3, gearKind: 'tricycle' };
    ac = new DetailedAircraft(dims, { R, model: MODELS[TYPE] ? loadModel(TYPE, { keepCpu: true }) : null, lodDist: 1e9, shadowDist: 1e9 });
    poseAircraft(); scene.add(ac);
    await Promise.all([ac.ready, world.ready.catch((e) => { worldErr = 'textures: ' + e; })]);
    poseAircraft(); applyEnv(true);
    window.HWDM.info = ac.info; window.HWDM.error = ac.error;
    window.HWDM.itemProgs = () => { const c = {}; for (const it of ac.items(camera().pos)) c[it.prog] = (c[it.prog] || 0) + 1; return c; };
    window.__modelReady = true; hudText();
    if (!SHOT) { buildUI(); const loop = () => { if (!paused) render(); requestAnimationFrame(loop); }; requestAnimationFrame(loop); setInterval(hudText, 500); }
  } catch (e) { window.__modelError = String(e && e.stack || e); hud.textContent = 'error: ' + e; console.error(e); }
})();
