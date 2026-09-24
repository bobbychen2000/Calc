import { initGL, gl } from './gl.js';
import './shaders/common.js';
import './shaders/ground.js';
import { Renderer } from './renderer.js';
import { buildBaseWorld, bakeGround } from './world/world.js';
import { solarPosition, sunVector } from './world/textures.js';
import { ARP, stToWorld, GROUND_Y } from './geo.js';
import { LiveAircraft } from './live/aircraft.js';
import { MODEL_SOURCES } from './live/models.js';
import { Scene, stDir } from './scene.js';
import { Aircraft } from './aircraft/fleet.js';
import { setupDirector } from './shots.js';
import { buildAirfieldLights, lightSpriteFn, buildPierGeometry } from './anim/lights.js';
import { Overlay } from './overlay.js';
import { Mesh } from './gl.js';
import { CLOUD_VS, CLOUD_FS } from './shaders/env.js';
window.__cloudShaders = { CLOUD_VS, CLOUD_FS };

const log = (s) => { console.log(s); };
window.APP = {};

async function postFrame(session, idx, px) {
  await fetch(`/frame/${session}/${idx}`, { method: 'POST', body: px });
}

window.initApp = async function (cfg) {
  const canvas = document.createElement('canvas'); canvas.width = 4; canvas.height = 4; document.body.appendChild(canvas);
  initGL(canvas);
  const R = new Renderer(cfg.W, cfg.H, { msaa: cfg.msaa ?? 4, shadowRes: cfg.shadowRes || 4096 });
  const world = buildBaseWorld(R, log);
  APP.R = R; APP.world = world; APP.cfg = cfg;
  setEnvironment(cfg.env || {});
  APP.scene = new Scene(R, world);
  APP.scene.parkAtGates(world.gates, { seed: 3, liveParked: cfg.live ? cfg.live.parked : null });
  if (cfg.testAircraft) {
    const types = ['narrow', 'mid', 'wide'];
    cfg.testAircraft.forEach((a, i) => { if (a.model) MODEL_SOURCES[a.model] = MODEL_SOURCES[a.model] || ('data/models/' + a.model + '.sfom');
      const ac = a.model ? new LiveAircraft(a.type, a.model, a.liv ?? i, { lod: 1, id: 'T' + i }) : new Aircraft(a.type, a.liv ?? i, { lod: 1, id: 'T' + i }); ac.pos = stToWorld(a.s, a.t, (a.h ?? 0) + GROUND_Y); ac.fwd = stDir(a.dir); ac.gear = a.gear ?? 1; ac.flaps = a.flaps ?? 0; ac.spoilers = a.spoilers ?? 0; ac.pitch = a.pitch ?? 0; ac.lightsOn.landing = !!a.landing; ac.lightsOn.strobe = !!a.strobe; APP.scene.add(ac); });
  }
  return 'ok';
};
window.modelsReady = async () => { await Promise.all(APP.scene.aircraft.map(a => a.ready).filter(Boolean)); return APP.scene.aircraft.filter(a => a.model).length; };

export function setEnvironment(e) {
  const date = new Date(e.utc || '2026-09-23T16:30:00Z');
  const sp = solarPosition(date, ARP.lat, ARP.lon);
  const sunDir = sunVector(e.sunAz ?? sp.az, e.sunEl ?? sp.el);
  const visM = e.visibilityM || 45000;
  const wdir = (e.windDir ?? 280) * Math.PI / 180, wms = (e.windKt ?? 6) * 0.5144;
  const windTo = [-Math.sin(wdir), 0, Math.cos(wdir)]; // wind blows toward (world x east, z south)
  const env = {
    sunDir, mie: e.mie ?? 21e-6, sunI: 20,
    fog: [Math.min(3.912 / visM, 0.004) * 0.9, 1 / 700, 1.0, 0.97],
    cloud: [e.cloudCover ?? 0.25, e.cloudBase ?? 1200, e.cloudScale ?? (e.slab ? 4200 : 14000), 0.5],
    cloudWind: [windTo[0] * (wms * 2.5 + 1), windTo[2] * (wms * 2.5 + 1)], cloudTex: APP.world.textures.clouds, noiseTex: APP.world.textures.noise, refPos: [0, 60, 0],
    slab: !!e.slab, cloudLow: e.cloudLow || null, wind: [windTo[0] * wms, windTo[2] * wms], windKt: e.windKt ?? 6,
  };
  APP.world.waterU.uWind = [windTo[0] * Math.max(wms, 1), windTo[2] * Math.max(wms, 1)];
  APP.world.waterU.uWaveAmp = Math.min(1.3, 0.45 + (e.windKt ?? 6) / 22);
  APP.R.setupSky(env);
  bakeGround(APP.R, APP.world, log);
  APP.sun = { ...sp, dir: sunDir };
  log('sun az ' + sp.az.toFixed(1) + ' el ' + sp.el.toFixed(1));
  APP.env = env;
}
window.setEnvironment = setEnvironment;

window.renderStill = async function (cam, session, idx, post) {
  const R = APP.R; const t0 = performance.now();
  R.prev = null;
  const fr = APP.scene.frame(cam.t || 0);
  R.render(fr, cam, cam.t || 0, post || { exposure: 1.0, shutter: 0 });
  APP.scene.commit();
  const px = R.readPixels();
  const t1 = performance.now();
  await postFrame(session, idx, px);
  return { renderMs: t1 - t0, totalMs: performance.now() - t0 };
};

window.setupShots = function (live) {
  const S = APP.scene;
  const sys = buildAirfieldLights(1.0);
  const fn = lightSpriteFn(sys);
  S.staticLights.push((t) => fn(t, APP.curCamPos));
  const pd = buildPierGeometry(sys.piers);
  const I4 = new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]);
  APP.world.items.push({ mesh: new Mesh(pd), prog: 'obj', model: I4, bbox: pd.bbox, castShadow: true, uniforms: { uEmissiveBoost: 1 } });
  // low cloud slab (from METAR layers)
  if (APP.env.slab) {
    const { CLOUD_VS, CLOUD_FS } = window.__cloudShaders;
    APP.R.addProgram('cloud', CLOUD_VS, CLOUD_FS);
    const N = 96; const pos = []; const idx = [];
    for (let j = 0; j <= N; j++) for (let i = 0; i <= N; i++) { const u = i / N * 2 - 1, v = j / N * 2 - 1; const f = (x) => Math.sign(x) * Math.pow(Math.abs(x), 2.2); pos.push(f(u), 0, f(v)); }
    for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) { const a = j * (N + 1) + i; idx.push(a, a + N + 1, a + 1, a + 1, a + N + 1, a + N + 2); }
    const plane = new Mesh({ pos: new Float32Array(pos), idx: new Uint32Array(idx) });
    const layers = [];
    const H0 = APP.env.cloud[1], cov = APP.env.cloud[0];
    for (let k = 0; k < 3; k++) layers.push({ H: H0 + k * 32, cov, k: k / 2, off: 0, op: 0.62 });
    if (APP.env.cloudLow) for (let k = 0; k < 2; k++) layers.push({ H: APP.env.cloudLow.base + k * 18, cov: APP.env.cloudLow.cover, k: k, off: 0.37, op: 0.5 });
    for (const L of layers) APP.world.items.push({ mesh: plane, prog: 'cloud', blend: 'alpha', bothPasses: true, bbox: null, castShadow: false, noCull: true,
      sortKey: (cp) => Math.abs(cp[1] - L.H),
      uniforms: () => ({ uH: L.H, uExtent: 40000, uLayer: [L.cov, L.k, L.off, L.op], uCamDir: APP.R.curCam.dir, uRange: APP.R.curRange }) });
  }
  APP.dir = setupDirector(S, APP.world, APP.env, live);
  APP.overlay = new Overlay(APP.R.W, APP.R.H);
  if (live && live.info) Object.assign(APP.overlay.info, live.info);
  return APP.dir.shots.map(s => ({ name: s.name, start: s.start, dur: s.dur }));
};

function frameAt(shot, t, fps, post) {
  const T = shot.start + t;
  APP.dir.hero.update(T);
  const cam = shot.camera(t);
  APP.curCamPos = cam.pos;
  const fr = APP.scene.frame(T);
  const ov = shot.overlay ? shot.overlay(t) : null;
  if (APP.overlay.draw(ov)) APP.R.setOverlay(APP.overlay.cv);
  const p = Object.assign({}, post, { fade: shot.fade ? shot.fade(t) : 1 });
  // fade in at very start of video
  if (shot.start === 0) p.fade *= Math.min(1, t / 0.8);
  APP.R.render(fr, cam, T, p);
  APP.scene.commit();
}
window.renderShotFrames = async function (shotIdx, f0, f1, session, fps, post) {
  const shot = APP.dir.shots[shotIdx]; const R = APP.R;
  // prime motion history with previous frame state
  { const t = (f0 - 1) / fps; const T = shot.start + t; APP.dir.hero.update(T); const cam = shot.camera(t); APP.curCamPos = cam.pos; APP.scene.frame(T); APP.scene.commit(); R.prev = R.computeCamera(cam); }
  let pending = null; const times = [];
  for (let f = f0; f < f1; f++) {
    const t0 = performance.now();
    frameAt(shot, f / fps, fps, post);
    const px = R.readPixels();
    if (pending) { await pending; if (window.gc) window.gc(); }
    pending = fetch(`/frame/${session}/${f}`, { method: 'POST', body: px });
    times.push(performance.now() - t0);
  }
  if (pending) await pending;
  return { avgMs: times.reduce((a, b) => a + b, 0) / Math.max(1, times.length) };
};
window.renderShotStill = async function (shotIdx, t, session, idx, fps, post) {
  const shot = APP.dir.shots[shotIdx]; const R = APP.R;
  { const tp = t - 1 / fps; APP.dir.hero.update(shot.start + tp); const cam = shot.camera(tp); APP.curCamPos = cam.pos; APP.scene.frame(shot.start + tp); APP.scene.commit(); R.prev = R.computeCamera(cam); }
  const t0 = performance.now();
  frameAt(shot, t, fps, post);
  const px = R.readPixels();
  await fetch(`/frame/${session}/${idx}`, { method: 'POST', body: px });
  return performance.now() - t0;
};
