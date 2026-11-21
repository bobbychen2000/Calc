// forked from sfo3d@e3218d6 js/live/app.js
// SHA Live 3D - application: boot, render loop, environment (sun / sky / night / METAR), camera views, UI glue, QA hooks.
// sha3d changes: Phase 2 is a static scene - no traffic engine, feeds, jet bridges, ATC, runway statistics, airfield
// lighting or SFO bakes (sfo3d's reservoirs, shore foam, flysfo plan, KSFO METAR, RUNWAY_SIGNS, SFO camera presets are
// gone). Data are injected (cfg.airport / stands / taxigraph = window.SHA_*; arch.md R4); airport-specific geometry comes
// from the extensions (js/live/ext.js); views come from the data (runway ends, terminal and tower anchors). Kept from
// sfo3d: quality tiers, dynamic resolution, the EnvState glue (applyEnv), clouds, camera rig, the QA hooks pattern
// (window.SHA.qa, as sfo3d's window.SFO.qa). Storage prefix 'shalive.'.
// P2e (relay / modes / UI shell): cfg.mode 'live' | 'snapshot' (js/live/entry.js), the snapshot's recorded reports feed
// AppEnv; app.hooks.status lets js/live/shell.js own the status pill and clock line; app.cfg / app.mode for extensions.
import { initGL, gl, Mesh } from '../gl.js';
import '../shaders/common.js';
import '../shaders/ground.js';
import { Renderer } from '../renderer.js';
import * as GEO from '../geo.js';
import { Scene } from '../scene.js';
import { TYPES } from '../aircraft/types.js';
import { CLOUD_VS, CLOUD_FS } from '../shaders/env.js';
import { AppEnv } from '../env/app_env.js';
import { setRunwayHeadings } from '../env/state.js';
import { aircraftLightStates, setLightViewer, setLightFrame, setLightEnv } from '../env/aircraft_lights.js';
import { DAY_GAIN } from '../env/lighting/display.js';
import { LiveAircraft, TYPE_MODELS } from './aircraft.js';
import { MODEL_SOURCES } from './models.js';
import { liveryForAirline } from './lookup.js';
import { buildLiveWorld } from './world.js';
import { extensions } from './ext.js';
import { CameraRig } from './controls.js';
import { UI } from './ui.js';
import { RELAY, fetchMetarList } from './relay.js';

const { GROUND_Y } = GEO;
const DEG = Math.PI / 180, FT = 0.3048;
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const sstep = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
// quality tiers (sfo3d's, plus the ground-map resolutions: mapRes = airfield map m/px, ctxRes = context map m/px)
const QUALITY = {
  high: { name: 'high', msaa: 4, shadow: 3072, scaleMax: 1.0, dprMax: 2, maxPx: 3.2e6, mapRes: 1.0, ctxRes: 4, lod: 1800, shadowDist: 1600 },
  medium: { name: 'medium', msaa: 4, shadow: 2048, scaleMax: 0.9, dprMax: 1.5, maxPx: 2.0e6, mapRes: 1.25, ctxRes: 4, lod: 1300, shadowDist: 1100 },
  ultra: { name: 'ultra', msaa: 4, shadow: 4096, scaleMax: 1.0, dprMax: 3, maxPx: 3.4e7, mapRes: 0.75, ctxRes: 3, lod: 4000, shadowDist: 2500 },
  low: { name: 'low', msaa: 2, shadow: 2048, scaleMax: 0.8, dprMax: 2, maxPx: 1.1e6, mapRes: 1.6, ctxRes: 6, lod: 1000, shadowDist: 700 },
};
const store = { get(k, d) { try { const v = localStorage.getItem('shalive.' + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } }, set(k, v) { try { localStorage.setItem('shalive.' + k, JSON.stringify(v)); } catch (e) { } } };
function pickQuality(pref) {
  if (typeof window !== 'undefined' && window.SHA_LITE) return { ...QUALITY.low, lite: true, dprMax: 1.5, maxPx: 0.7e6, lod: 700, shadowDist: 450, mapRes: 2.0, ctxRes: 8 };
  const ua = navigator.userAgent || '';
  const mobile = /iPhone|iPad|iPod|Android/i.test(ua) || (matchMedia('(pointer: coarse)').matches && Math.min(screen.width, screen.height) < 900);
  const mem = navigator.deviceMemory || 8;
  const url = new URLSearchParams(location.search).get('quality');
  const q = url && QUALITY[url] ? url : pref && pref !== 'auto' ? pref : mobile ? 'low' : mem <= 4 ? 'medium' : 'high';
  return QUALITY[q] || QUALITY.medium;
}
const nextFrame = () => new Promise(r => setTimeout(r, 0));
const FIXED_RES = new URLSearchParams(location.search).has('fixedres');

// cfg: { mode ('live' | 'snapshot'), relay, relayInfo, snapshot ({now, metars, tafs, traffic} | null), modeInfo, airport, stands,
//        taxigraph, s2, models: {key: source}, about, attrib }   (js/live/entry.js)
export async function startApp(cfg) {
  const hooks = {};   // P2e UI shell (js/live/shell.js): hooks.status(now) replaces the status / clock line below
  const root = document.getElementById('app');
  const canvas = document.createElement('canvas'); canvas.id = 'gl'; root.prepend(canvas);
  const qPref = store.get('quality', 'auto'); const Q = pickQuality(qPref);
  let lightMode = store.get('light', 'real'), showOthers = store.get('others', true);
  let followMode = null;
  const ui = new UI(root, { onSelect: () => { }, onView: (v) => view(v), onFollow: () => { }, onSetting: (k, v) => setting(k, v), showOthers: () => showOthers });
  ui.root.querySelector('[data-set="light"]').value = lightMode; ui.root.querySelector('[data-set="quality"]').value = qPref; ui.root.querySelector('[data-set="others"]').checked = showOthers;
  ui.setAbout(cfg.about || ''); ui.setAttrib(cfg.attrib || '');
  try {
    ui.progress(0.05, 'Starting graphics…'); await nextFrame();
    initGL(canvas);
    if (!gl.getExtension('EXT_color_buffer_float') && !gl.getExtension('EXT_color_buffer_half_float')) throw new Error('This device\'s browser lacks floating-point render targets (WebGL2 EXT_color_buffer_float).');
    { const ext = gl.getExtension('EXT_texture_filter_anisotropic'); const maxA = ext ? gl.getParameter(ext.MAX_TEXTURE_MAX_ANISOTROPY_EXT) : 1; window.ANISO = Math.min(maxA, Q.name === 'high' ? 16 : Q.name === 'medium' ? 8 : 4); }
  } catch (e) { ui.fail('Sorry — this browser can\'t run the 3D view (WebGL 2 required).<br><small>' + String(e.message || e) + '</small>'); throw e; }
  let running = true;
  canvas.addEventListener('webglcontextlost', (e) => { e.preventDefault(); ui.fail('The graphics context was lost (the device ran low on GPU memory). <a href="#" onclick="location.reload()">Reload</a>, or pick a lower quality in Settings.'); document.body.classList.add('lost'); running = false; });
  // ---------------------------------------------------------------- sizes
  let scale = Q.scaleMax; const size = () => {
    const dpr = Math.min(window.devicePixelRatio || 1, Q.dprMax);
    const cw = Math.max(1, Math.round(canvas.clientWidth * dpr)), ch = Math.max(1, Math.round(canvas.clientHeight * dpr));
    let s = scale; if (cw * ch * s * s > Q.maxPx) s = Math.sqrt(Q.maxPx / (cw * ch));
    return { cw, ch, rw: Math.max(2, Math.round(cw * s)), rh: Math.max(2, Math.round(ch * s)) };
  };
  let S = size(); canvas.width = S.cw; canvas.height = S.ch;
  const R = new Renderer(S.rw, S.rh, { msaa: Q.msaa, shadowRes: Q.shadow });
  R.onFatal = (html) => ui.fail(html);
  // ---------------------------------------------------------------- world
  ui.progress(0.12, 'Building the airfield…'); await nextFrame();
  const data = { airport: cfg.airport, stands: cfg.stands || null, taxigraph: cfg.taxigraph || null, s2: cfg.s2 || null };
  const world = await buildLiveWorld(R, data, { mapRes: Q.mapRes, ctxRes: Q.ctxRes, quality: Q, log: (m) => console.log('[world]', m) });
  const scene = new Scene(R, world);
  scene.staticLights.push(() => world.sprites);
  ui.progress(0.6, 'Sun, sky and weather…'); await nextFrame();
  // ---------------------------------------------------------------- environment (EnvState glue as sfo3d's applyEnv)
  // snapshot mode (P2e): the recorded reports of data/sha_snapshot.js (js/env/presets.js setSnapshotWx) at its instant
  const envCore = new AppEnv({ mode: cfg.mode, relayInfo: cfg.relayInfo, snapshotNow: cfg.snapshot ? cfg.snapshot.now : null, snapshotMetar: '', search: location.search, groundY: GROUND_Y });
  GEO.onRunwayHeadings(setRunwayHeadings);
  envCore.rendererNote = 'live.html (WebGL2) renderer: fog = one exponential, one cloud deck (sfo3d old-renderer limits)';
  envCore.setLightMode(lightMode); envCore.attachHud(root);
  let metar = null, env = null, lastSunKey = '', nightF = 0, exposure = 0.45, cloudItems = [], envInfo = null;
  function applyEnv(now, force) {
    const E = envCore.update(now, null);
    metar = envCore.summary(); R.envState = E;
    const sp = { az: E.sun.az, el: E.sun.el }, elN = E.sun.elTrue;
    const key = sp.az.toFixed(1) + ':' + sp.el.toFixed(1) + ':' + (metar ? metar.raw : '') + ':' + E.atm.sigmaSurface.toPrecision(2);
    if (!force && key === lastSunKey) return; lastSunKey = key;
    const M = metar; const layers = M ? M.clouds.slice().sort((a, b) => a.ft - b.ft) : [];
    const COVER = { FEW: 0.14, SCT: 0.4, BKN: 0.68, OVC: 0.95 };
    const cl = layers.filter(c => c.ft >= 100 && E.clouds.some(l => l.cover === c.cover && l.baseFt === c.ft));
    const main = cl.find(c => (c.cover === 'BKN' || c.cover === 'OVC') && c.ft <= 5000) || cl[0];
    const wdir = ((M && M.windDir) ?? 180) * DEG, wms = ((M && M.windKt) ?? 6) * 0.5144;
    const windTo = [-Math.sin(wdir), 0, Math.cos(wdir)];
    const lowSlab = main && main.ft < 5000 && (main.cover === 'BKN' || main.cover === 'OVC');
    const surf = E.atm.slabs.filter(sl => !/^(cloud|obscuration)/.test(sl.kind || ''));
    const fogTop = Math.max(5, (surf.length ? Math.max(...surf.map(sl => sl.y1)) : GROUND_Y + 914) - GROUND_Y);
    const ownOf = (c) => { const L = c && E.clouds.find(l => l.cover === c.cover && l.baseFt === c.ft); return L ? L.own : c ? COVER[c.cover] : 0; };
    const baseOf = (c) => { const L = c && E.clouds.find(l => l.cover === c.cover && l.baseFt === c.ft); return L ? L.base : c ? GROUND_Y + c.ft * FT : 1500; };
    env = { sunDir: E.sun.dir, mie: 21e-6, sunI: 20, fog: [E.atm.sigmaSurface * Math.exp(GROUND_Y / fogTop), 1 / fogTop, 1.0, 1.0],
      cloud: [ownOf(main), main ? baseOf(main) : 1500, lowSlab ? 4200 : 14000, 0.5],
      cloudWind: [windTo[0] * wms, windTo[2] * wms], cloudTex: world.textures.clouds, noiseTex: world.textures.noise, refPos: [0, 60, 0],
      slab: !!lowSlab, wind: [windTo[0] * wms, windTo[2] * wms] };
    R.setupSky(env);
    const nf = sstep(3, -9, elN);
    const floorUp = [0.010, 0.012, 0.018].map(v => v * nf), floorHz = [0.012, 0.011, 0.012].map(v => v * nf);
    R.light.skyUp = R.light.skyUp.map((v, i) => Math.max(v, floorUp[i])); R.light.skyHorizon = R.light.skyHorizon.map((v, i) => Math.max(v, floorHz[i]));
    R.light.ground = R.light.ground.map((v, i) => Math.max(v, floorHz[i] * 0.5));
    nightF = sstep(6, -4, elN);
    const dark = sstep(2, -10, elN);
    exposure = (0.45 + 0.25 * (env.cloud[0] > 0.6 ? 1 : 0) * (1 - dark)) * (1 - dark) + 2.4 * dark + sstep(8, 2, elN) * (1 - dark) * 0.25;
    R.extraCommon = { uNight: nightF, uGroundY: GROUND_Y };
    setLightEnv(E, DAY_GAIN / 258);
    setClouds(lowSlab ? { H: env.cloud[1], cov: env.cloud[0] } : null);
    envInfo = { sun: sp, metar: M };
  }
  function setClouds(slab) {
    world.items = world.items.filter(it => !cloudItems.includes(it)); cloudItems = [];
    if (!slab) return;
    if (!R.progs.cloud) R.addProgram('cloud', CLOUD_VS, CLOUD_FS);
    if (!setClouds.plane) {
      const N = 64, pos = [], idx = [];
      for (let j = 0; j <= N; j++) for (let i = 0; i <= N; i++) { const u = i / N * 2 - 1, v = j / N * 2 - 1; const f = (x) => Math.sign(x) * Math.pow(Math.abs(x), 2.2); pos.push(f(u), 0, f(v)); }
      for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) { const a = j * (N + 1) + i; idx.push(a, a + N + 1, a + 1, a + 1, a + N + 1, a + N + 2); }
      setClouds.plane = new Mesh({ pos: new Float32Array(pos), idx: new Uint32Array(idx) });
    }
    for (let k = 0; k < 3; k++) {
      const L = { H: slab.H + k * 32, cov: slab.cov, k: k / 2, off: 0, op: 0.55 };
      const it = { mesh: setClouds.plane, prog: 'cloud', blend: 'alpha', bothPasses: true, bbox: null, castShadow: false, noCull: true, sortKey: (cp) => Math.abs(cp[1] - L.H),
        uniforms: () => ({ uH: L.H, uExtent: 40000, uLayer: [L.cov, L.k, L.off, L.op], uCamDir: R.curCam.dir, uRange: R.curRange }) };
      cloudItems.push(it); world.items.push(it);
    }
  }
  applyEnv(Date.now(), true);
  // ---------------------------------------------------------------- aircraft models (Phase 2: QA scale checks only)
  Object.assign(MODEL_SOURCES, cfg.models || {});
  const qaModels = [];
  // ---------------------------------------------------------------- camera and views
  const rig = new CameraRig(canvas, { heightAt: (x, z) => GEO.groundY(x, z), onTap: () => { }, onUserMove: () => { followMode = null; } });
  const A = world.anchors; const G = GROUND_Y;
  const t1 = A.t1 ? A.t1.pos : [600, 180], t2 = A.t2 ? A.t2.pos : [-1220, 220];
  const VIEWS = {
    // camera south-east of the field looking north-west: T2 left (west), T1 right (east), runways running away
    overview: { target: [-300, G, 150], dist: 5600, yaw: 158, pitch: 33, fov: 50 },
    t2: { target: [t2[0] + 120, G, t2[1]], dist: 1500, yaw: 112, pitch: 24, fov: 50 },   // from the airside (east) looking west
    t1: { target: [t1[0] - 90, G, t1[1]], dist: 950, yaw: 250, pitch: 22, fov: 50 },    // from the airside (west) looking east
    runways: { target: [-170, G, -300], dist: 4300, yaw: 180, pitch: 13, fov: 45 },      // from the south, looking north along both runways
    top: { target: [-250, G, 0], dist: 9800, yaw: 180, pitch: 89, fov: 50 },              // north up
  };
  function view(name) {
    rig.stopFollow(); followMode = null; if (name !== 'tower') rig.leaveTower();
    const V = VIEWS[name];
    if (V) rig.flyTo({ target: V.target.slice(), dist: V.dist, yaw: V.yaw * DEG, pitch: V.pitch * DEG, fov: V.fov * DEG });
    else if (name === 'tower' && A.tower) {
      // P2f: with a modelled cab (anchors.tower.cabHalf, terminals package) the eye stands 2 m inside the glass on the
      // runway side, so the console band below the glass no longer fills the lower ~40 % of the frame; pitch -7 deg
      const yaw = 262, hv = GEO.hdgVec(yaw), off = A.tower.cabHalf ? Math.max(0, A.tower.cabHalf - 2.0) : 0;
      rig.setTower([A.tower.pos[0] + hv[0] * off, A.tower.eyeY, A.tower.pos[2] + hv[1] * off], { yaw: yaw * DEG, pitch: (off ? -7 : -5) * DEG, fov: 58 * DEG });
    }
    ui.root.querySelectorAll('#views [data-view]').forEach(b => b.classList.toggle('on', b.dataset.view === name));
  }
  function setting(k, v) {
    if (k === 'light') { lightMode = v; store.set('light', v); envCore.setLightMode(v); applyEnv(Date.now(), true); }
    else if (k === 'quality') { store.set('quality', v); location.reload(); }
    else if (k === 'others') { showOthers = v; store.set('others', v); }
  }
  // ---------------------------------------------------------------- data (Phase 2: METAR through the relay only)
  if (cfg.relay) {
    const wx = async () => { const L = await fetchMetarList(); if (L) { envCore.setReports(L); applyEnv(Date.now(), false); } };
    wx(); setInterval(wx, RELAY.metarPollMs);
  }
  ui.emptyText = 'No traffic yet. Open ADS-B does not cover Hongqiao; simulated traffic (labelled inferred) comes in Phase 3.';
  ui.setNote('Static scene · Phase 2 core · no traffic yet'); ui.renderList(true, []);
  document.body.classList.add('no-traffic');   // (the Phase 3 traffic engine removes it when it starts)
  // (the Observed / Inferred legend is the UI shell's, js/live/shell.js; ?legend=1 opens it)
  // ---------------------------------------------------------------- loop
  { const V = VIEWS.overview; rig.anim = null; rig.target = V.target.slice(); rig.dist = V.dist; rig.yaw = V.yaw * DEG; rig.pitch = V.pitch * DEG; rig.fov = V.fov * DEG; }
  ui.root.querySelectorAll('#views [data-view]').forEach(b => b.classList.toggle('on', b.dataset.view === 'overview'));
  ui.progress(0.9, 'Almost there…'); await nextFrame();
  let last = performance.now(), simT = 0, tUi = 0, tEnv = 0, ftEMA = 16, tScale = 0;
  const post = { exposure: 0.45, shutter: 0, bloom: 0.012, vignette: 0.18, grain: 0.0, sat: 1.1 };
  function onResize() { S = size(); if (canvas.width !== S.cw || canvas.height !== S.ch) { canvas.width = S.cw; canvas.height = S.ch; } R.resize(S.rw, S.rh); rig.resize(canvas.clientWidth, canvas.clientHeight); }
  window.addEventListener('resize', onResize); onResize();
  let camPos = [0, 100, 0];
  function tick() {
    if (!running) return;
    const tp = performance.now(); const wall = (tp - last) / 1000; const dt = Math.min(wall, 0.1); last = tp; simT += dt;
    const now = Date.now();
    try {
      rig.update(dt);
      if ((tEnv += wall) > 30) { tEnv = 0; applyEnv(now, false); }
      const cam = rig.camera(); camPos = cam.pos; setLightViewer(camPos, 2 * Math.tan((cam.fov || 0.8) / 2) / Math.max(1, R.H || canvas.height || 720)); setLightFrame(simT);
      const fr = scene.frame(simT, cam.pos);
      post.exposure = exposure;
      R.render(fr, cam, simT, post); scene.commit(); R.present(canvas.width, canvas.height);
      if ((tUi += wall) > 1) { tUi = 0; status(now); }
    } catch (e) { console.error(e); }
    const ft = performance.now() - tp; ftEMA += (ft - ftEMA) * 0.05;
    if (!FIXED_RES && (tScale += wall) > 2.5) { tScale = 0; const ns = ftEMA > 36 ? scale * 0.88 : ftEMA < 20 ? Math.min(Q.scaleMax, scale * 1.08) : scale; if (Math.abs(ns - scale) > 0.02) { scale = clamp(ns, 0.4, Q.scaleMax); onResize(); } }
    requestAnimationFrame(tick);
  }
  function status(now) {
    if (hooks.status) { try { return hooks.status(now); } catch (e) { console.warn('[shell] status', e); } }
    ui.setStatus({ state: 'snap', text: cfg.relay ? 'Relay · no traffic yet' : 'Static scene', sub: '', title: 'Phase 2 core: airfield, sun, sky and weather; the traffic engine comes in Phase 3' + (cfg.relay ? ' (relay connected: METAR)' : ' (no relay: no live weather)') });
    const M = metar; const wx = M ? `${M.windDir != null ? String(M.windDir).padStart(3, '0') + '°' : 'VRB'} ${M.windKt ?? 0} kt${M.clouds.length ? ' · ' + M.clouds.map(c => c.cover + String(c.ft / 100).padStart(3, '0')).join(' ') : ''}` : '';
    ui.setClock(new Date(now), wx + envCore.clockNote());
  }
  ui.progress(1, 'Ready'); ui.ready(); status(Date.now());
  requestAnimationFrame(tick);
  // ---------------------------------------------------------------- QA camera helpers (used by the test harness)
  const vh = (x, z) => Math.atan2(x, -z) / DEG;   // camera yaw (deg) that puts the camera in direction (x, z) from the target
  const look = (target, yawDeg, pitchDeg, dist, fovDeg = 50) => { rig.stopFollow(); rig.leaveTower(); rig.anim = null; rig.target = target.slice(); rig.yaw = yawDeg * DEG; rig.pitch = pitchDeg * DEG; rig.dist = dist; rig.fov = fovDeg * DEG; };
  const standByName = (n) => (cfg.stands && cfg.stands.stands || []).find(s => s.name === String(n)) || null;
  const qa = {
    hideUI: (on = true) => document.body.classList.toggle('qa', on),
    look,
    view(name) { view(name); if (rig.anim) { rig.anim.t = rig.anim.dur; rig.update(0); } return true; },
    /** threshold view: behind the landing threshold of end `name` ('18L' ...), looking along the landing direction */
    threshold(name, dist = 650, pitch = 6, fov = 50) {
      const E = GEO.runwayEnd(name); if (!E) return false; const h = GEO.hdgVec(E.hdg);
      look([E.thr[0] + h[0] * 300, G, E.thr[1] + h[1] * 300], (E.hdg + 180) % 360, pitch, dist, fov); return true;
    },
    /** stand view: ahead of the stand's nose point, to one side, looking back at the stand (side +1 = left of the aircraft) */
    stand(name, dist = 62, side = 1, pitch = 17, fov = 50) {
      const s = standByName(name); if (!s) return false; const h = GEO.hdgVec(s.hdg);
      const c = [s.nose[0] - h[0] * 18, G, s.nose[1] - h[1] * 18]; const lf = [h[1], -h[0]];   // aircraft's left (x, z)
      const off = [h[0] * 0.75 + lf[0] * 0.66 * side, h[1] * 0.75 + lf[1] * 0.66 * side];
      look(c, vh(off[0], off[1]), pitch, dist, fov); return true;
    },
    tower(dist = 190, yaw = 245, pitch = 12) { if (!A.tower) return false; look([A.tower.pos[0], G + 22, A.tower.pos[2]], yaw, pitch, dist); return true; },
    /** QA ONLY (scale checks; never called by the app): an aircraft model parked nose-in at a stand, neutral livery, src 'qa' */
    async placeModel(name, icao = 'A320') {
      const s = standByName(name); const m = TYPE_MODELS[icao]; if (!s || !m || !TYPES[m.t]) return false;
      const ac = new LiveAircraft(m.t, m.m && MODEL_SOURCES[m.m] ? m.m : null, liveryForAirline(null), { id: 'qa-' + name, lod: 1, lodDist: Q.lod, shadowDist: Q.shadowDist });
      const h = GEO.hdgVec(s.hdg); const x = ac.T.xMain;   // model origin = main gear, xMain m behind the nose tip (sfo3d syncViews)
      ac.pos = [s.nose[0] - h[0] * x, G, s.nose[1] - h[1] * x]; ac.fwd = [h[0], 0, h[1]]; ac.gear = 1; ac.dirt = 0.35;
      Object.assign(ac.lightsOn, aircraftLightStates({ phase: 'parked', ground: true, gs: 0, altAgl: 0, stale: false }));
      scene.add(ac); qaModels.push(ac); await ac.ready; return { stand: name, type: m.t, model: m.m || null, L: ac.T.L, span: ac.T.span || null, src: 'qa' };
    },
    clearModels() { for (const a of qaModels.splice(0)) { const i = scene.aircraft.indexOf(a); if (i >= 0) scene.aircraft.splice(i, 1); } },
    info: () => ({ world: world.info, anchors: world.anchors, quality: Q.name, extensions: extensions().map(e => e.name), runways: GEO.RUNWAYS.map(r => ({ id: r.id, hdg: r.hdg, len: +r.len.toFixed(1), width: r.width })) }),
  };
  const app = { R, scene, rig, ui, world, view, applyEnv, qa, env: () => envCore.state, envCore, geo: GEO, data, extensions, frameNow: () => { last = performance.now() - 16; tick(); },
    cfg, mode: cfg.mode, hooks, quality: Q };
  window.SHA = app;
  // extensions: start hooks (live systems), per-frame items and lights
  for (const e of extensions()) {
    if (e.frame) scene.extraItemFns.push((t) => { try { return e.frame(t, app) || []; } catch (err) { console.warn('[ext] frame ' + e.name, err); return []; } });
    if (e.lights) scene.staticLights.push((t) => { try { return e.lights(t, app) || []; } catch (err) { return []; } });
    if (e.start) { try { await e.start(app); } catch (err) { console.error('[ext] start ' + e.name, err); } }
  }
  return app;
}
