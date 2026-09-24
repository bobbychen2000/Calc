// Renderer3: the three.js r186 renderer behind live3.html, presented to js/live/app.js through the same interface as
// the old js/renderer.js Renderer (constructor(w, h, opts), addProgram, setupSky, light, extraCommon, render, present,
// resize, curCam) so that the app, its entry logic (js/live/entry.js), the UI, the camera rig and the SFO.qa hooks run
// unchanged. live3.html's import map swaps these modules in (docs/research/engine_impl.md §2):
//   js/gl.js         -> js/three/compat/gl.js       (builders record their meshes/textures instead of uploading them)
//   js/renderer.js   -> js/three/compat/renderer.js (this class)
//   js/scene.js      -> js/three/compat/scene.js    (aircraft list, light sprites, bridges -> Renderer3.frameScene)
//   js/world/world.js-> js/three/compat/world.js    (bakeGround -> the TSL bakes in js/three/ground.js)
// What is drawn and where comes from the existing builders' output (world.items, LiveGateSystem, LiveAircraft);
// how it is shaded is the TSL ports in js/three/*.js. WebGPURenderer uses WebGPU where available and falls back to
// WebGL 2 automatically. GPU work that the app requests before the renderer finished its (async) init is queued.
import { THREE, TSL } from './lib.js';
import { Engine, QUALITY3 } from './engine.js';
import { Sky } from './sky.js';
import { GroundBakes, groundMaterial, waterMaterial } from './ground.js';
import { objectMaterial } from './objects.js';
import { markingMaterial } from './markings.js';
import { loadSignFont, SignBuilder, signMaterials, signMeshes, faceIndex, worldSignAtlasMap } from './signs.js';
import { Bridges3 } from './bridges.js';
import { Sprites } from './lights.js';
import { AircraftRenderer, LiveryLibrary } from './aircraft.js';
import { geometryOf, textureOf } from './convert.js';
import { glCanvas } from './compat/gl.js';

const { uniform } = TSL;
const T0 = performance.now();
const tlog = (m) => console.log('[r3] ' + m + ' at ' + ((performance.now() - T0) / 1000).toFixed(1) + ' s');

// tier: ?tier=high|medium|low overrides; otherwise the old app's choice, recognised from the options it passes
// (js/live/app.js QUALITY: high = 3072 shadow map, low = 2x MSAA)
function tierOf(opts) {
  const q = new URLSearchParams(location.search).get('tier');
  if (q && QUALITY3[q]) return q;
  if (opts && opts.msaa === 2) return 'low';
  if (opts && opts.shadowRes >= 3072) return 'high';
  return 'medium';
}

export class Renderer3 {
  constructor(W, H, opts = {}) {
    this.W = W; this.H = H; this.tier = tierOf(opts); this.Q = QUALITY3[this.tier];
    this.canvas = glCanvas; this.fixedRes = new URLSearchParams(location.search).get('res') === '1';
    this.engine = new Engine(document.getElementById('app') || document.body, this.Q, { canvas: this.canvas });
    this.ready = false; this.failed = null; this.frames = 0; this.jobs = [];
    this.light = { sunDir: [0, 1, 0], sunColor: [1, 1, 1], skyUp: [0.3, 0.4, 0.6], skyHorizon: [0.5, 0.55, 0.6], ground: [0.1, 0.1, 0.1] };
    this.baseLight = null; this.extraCommon = {}; this.progs = {}; this.curCam = null; this.curRange = null;
    this.world = null; this.sceneShim = null; this.seen = new Set(); this.pendingSigns = []; this.clouds = new Map();
    this.pxScale = uniform(0.001); this.time = uniform(0); this.night = uniform(0);
    this.exposureScale = +(new URLSearchParams(location.search).get('expo') || 1.0);
    this.initP = this.engine.init().then(() => this._onReady()).catch((e) => {
      this.failed = e; console.error('three.js renderer failed to start', e);
      window.__sfoError = 'renderer: ' + String(e && e.stack || e);
    });
    this.fontP = loadSignFont().then(f => { this.font = f; }).catch(e => console.warn('MSDF sign font failed to load', e));
    this.liveriesP = LiveryLibrary.load().then(L => { this.liveries = L; });
  }
  // ------------------------------------------------------------ old Renderer interface
  addProgram(name) { this.progs[name] = true; }
  // ?res=1 pins the render size to the canvas size x devicePixelRatio (QA renders: the app's dynamic resolution
  // otherwise drops to 0.4x on a software rasteriser)
  resize(w, h) {
    if (this.fixedRes && this.canvas) { const d = Math.min(window.devicePixelRatio || 1, 2); w = Math.max(2, Math.round(this.canvas.clientWidth * d)); h = Math.max(2, Math.round(this.canvas.clientHeight * d)); }
    this.W = w; this.H = h; if (this.ready) this.engine.resize(w, h, 1);
  }
  present() { }
  // sky model + ambient terms (synchronous, as js/renderer.js setupSky); GPU sky textures and the PMREM IBL follow at
  // the next frame, after the app has adjusted R.light (night floor)
  setupSky(env) {
    this.env = env;
    this.light = Sky.lightFor(env); this.baseLight = { ...this.light, skyUp: this.light.skyUp.slice() };
    if (this.sky) this.sky.setEnv(env);
    this.envDirty = true;
  }
  // ------------------------------------------------------------ attachments from the compat modules
  attachWorld(world, sceneShim) {
    this.world = world; this.sceneShim = sceneShim;
    const T = world.textures;
    this.noiseTex = textureOf(T.noise, { anisotropy: this.Q.aniso }); this.noiseTex.wrapS = this.noiseTex.wrapT = THREE.RepeatWrapping;
    const cloudTex = textureOf(T.clouds); cloudTex.wrapS = cloudTex.wrapT = THREE.RepeatWrapping;
    this.sky = new Sky(this.engine, { cloudTex, noiseTex: this.noiseTex, baseRes: this.Q.skyRes });
    this.sky.u.night = this.night; this.sky.u.time = this.time;
    if (this.env) this.sky.setEnv(this.env);
  }
  // js/world/world.js bakeGround(R, world, log, opts) (compat/world.js)
  requestBake(world, opts = {}) {
    if (!this.bakes) this.bakes = new GroundBakes(this.engine, world, this.sky, this.Q); // takes the source maps now
    const sunOnly = !!opts.sunOnly && this.bakedOnce;
    this.bakedOnce = true;
    this.run(() => { this.bakes.run(this.engine.renderer, { sunOnly }); tlog('bake' + (sunOnly ? ' (sun)' : '')); });
  }
  run(fn) { if (this.ready) fn(); else this.jobs.push(fn); }
  // ------------------------------------------------------------ init
  _onReady() {
    this.ready = true; this.resize(this.W, this.H); const E = this.engine;
    const qs = new URLSearchParams(location.search); if (qs.get('sat')) E.grade.sat.value = +qs.get('sat'); if (qs.get('gamma')) E.grade.gamma.value = +qs.get('gamma');
    for (const fn of this.jobs.splice(0)) fn();
    console.log('three.js r' + THREE.REVISION + ' ' + E.backend + (E.reversed ? ' (reversed depth)' : '') + ', tier ' + this.tier);
  }
  // scene objects, built once the world, the sky and the first bake exist
  _buildStatic() {
    const E = this.engine, S = E.scene, W = this.world, Q = this.Q;
    const sky = this.sky;
    S.backgroundNode = sky.backgroundNode(); S.fogNode = sky.fogNode();
    this.gMat = groundMaterial(W, this.bakes, sky, Q); this.wMat = waterMaterial(W, this.bakes, sky);
    const common = { noiseTex: this.noiseTex, night: this.night, time: this.time };
    this.objMat = objectMaterial(common); this.vehMat = objectMaterial({ ...common, instanced: true });
    this.markMat = markingMaterial({ noiseTex: this.noiseTex, pxScale: this.pxScale, reversed: E.reversed });
    this.sprites = new Sprites(); S.add(this.sprites.mesh);
    this.acr = new AircraftRenderer(S, { noiseTex: this.noiseTex, liveries: this.liveries || null, track: (ac) => window.SFO && window.SFO.traffic ? window.SFO.traffic.tracks.get(ac.id) : null });
    this.staticGroup = new THREE.Group(); this.staticGroup.name = 'world'; S.add(this.staticGroup);
    this.built = true; tlog('static scene built');
  }
  _signMats() { if (!this.signMats && this.font) this.signMats = signMaterials(this.font, { night: this.night, noiseTex: this.noiseTex, reversed: this.engine.reversed }); return this.signMats; }
  // world.items -> three objects (items appended later, e.g. the approach-light piers, are picked up too)
  _syncItems() {
    const W = this.world; const G = this.staticGroup;
    for (const it of W.items) {
      if (this.seen.has(it)) continue; this.seen.add(it);
      const p = it.prog;
      if (p === 'ground' || p === 'water') {
        const m = new THREE.Mesh(geometryOf(it.mesh), p === 'ground' ? this.gMat : this.wMat); m.receiveShadow = true; m.matrixAutoUpdate = false;
        if (p === 'water') { m.frustumCulled = false; m.renderOrder = -1; }
        G.add(m);
      } else if (p === 'obj') {
        const m = new THREE.Mesh(geometryOf(it.mesh), this.objMat); m.castShadow = !!it.castShadow; m.receiveShadow = true;
        m.matrixAutoUpdate = false; if (it.model) { m.matrix.fromArray(it.model); } G.add(m);
      } else if (p === 'mark') {
        const m = new THREE.Mesh(geometryOf(it.mesh), this.markMat); m.frustumCulled = false; m.receiveShadow = true; m.renderOrder = 1; m.matrixAutoUpdate = false; G.add(m);
      } else if (p === 'sign') this.pendingSigns.push(it);
      else if (p === 'cloud') {
        const L = { H: uniform(1000), extent: uniform(40000), layer: uniform(new THREE.Vector4()) };
        const m = new THREE.Mesh(geometryOf(it.mesh), this.sky.cloudSlabMaterial(L)); m.frustumCulled = false; m.renderOrder = 5; m.matrixAutoUpdate = false;
        m.onBeforeRender = () => { const u = typeof it.uniforms === 'function' ? it.uniforms() : it.uniforms; if (u) { L.H.value = u.uH; L.extent.value = u.uExtent; L.layer.value.fromArray(u.uLayer); } };
        this.clouds.set(it, m); this.engine.scene.add(m);
      }
      // 'decal' (stand centrelines) is off by default in js/live/world.js (standMarkings) and not ported
    }
    // cloud layers removed by the app (setClouds rebuilds them when the METAR changes)
    if (this.clouds.size) { const live = new Set(W.items); for (const [it, m] of this.clouds) if (!live.has(it)) { this.engine.scene.remove(m); m.material.dispose(); this.clouds.delete(it); } }
    if (this.pendingSigns.length && this._signMats()) {
      if (!this.worldLookup) this.worldLookup = faceIndex(worldSignAtlasMap(W.details || {}));
      for (const it of this.pendingSigns.splice(0)) {
        const d = it.mesh.data; const sb = new SignBuilder(this.font);
        sb.addSignArrays({ pos: d.pos, nrm: d.nrm, uv: d.uv, ext: d.extra }, this.worldLookup);
        const g = signMeshes(sb, this.signMats, 'signs'); if (!it.castShadow) g.traverse(o => { o.castShadow = false; }); G.add(g);
      }
    }
  }
  // ------------------------------------------------------------ per frame (compat/scene.js Scene.frame)
  frameScene(sc, t, camPos) {
    if (!this.ready || !this.bakes || !this.sky) return;
    if (!this.built) this._buildStatic();
    this._syncItems();
    if (sc.gateSys && !this.bridges && this._signMats()) {
      this.bridges = new Bridges3(sc.gateSys, { objMat: this.objMat, vehMat: this.vehMat, signFont: this.font, signMats: this.signMats });
      this.engine.scene.add(this.bridges.group);
    }
    if (this.bridges) { this.bridges.update(Date.now()); sc.gateSys.sprites = this.bridges.sprites; }
    if (this.liveries && this.acr && !this.acr.liveries) this.acr.liveries = this.liveries;
    this.acr.sync(sc.aircraft, camPos);
  }
  // ------------------------------------------------------------ render (fr = compat Scene.frame result)
  render(fr, cam, t, post = {}) {
    const E = this.engine;
    const C = this._camInfo(cam);
    if (!this.ready || !this.built) return C;
    const R = E.renderer, S = E.scene, L = this.light;
    // environment: GPU sky, sun, IBL (after the app's night-floor adjustment of R.light)
    if (this.envDirty) {
      this.envDirty = false;
      this.sky.applyLight(L);
      const bu = this.baseLight ? this.baseLight.skyUp : L.skyUp;
      this.sky.u.skyFloor.value.setRGB(...L.skyUp.map((v, k) => Math.max(0, v - bu[k])));
      this.sky.renderSky(R);
      this.sky.updateEnvironment(R, S);
      E.setSun(L.sunDir, L.sunColor);
    }
    this.time.value = t; this.night.value = this.extraCommon.uNight || 0;
    const wu = this.world.waterU; if (this.wMat && wu) { const u = this.wMat.userData; if (wu.uWind) u.uWind.value.set(wu.uWind[0], wu.uWind[1]); if (wu.uWaveAmp != null) u.uAmp.value = wu.uWaveAmp; }
    E.setCamera(cam, this.W, this.H);
    this.pxScale.value = 2 * Math.tan(cam.fov / 2) / Math.max(1, this.H);
    // light sprites
    const sp = this.sprites; sp.begin(); for (const s of fr && fr.sprites || []) sp.put(s); sp.end(E.camera, this.H);
    R.toneMappingExposure = (post.exposure ?? 0.45) * this.exposureScale;
    const tr0 = performance.now(); E.render(); this.frames++;
    if (this.frames <= 3 || this.frames % 50 === 0) console.log('[r3] frame ' + this.frames + ' ' + (performance.now() - tr0).toFixed(0) + ' ms (t=' + ((performance.now() - T0) / 1000).toFixed(1) + ' s)');
    return C;
  }
  // camera record for the app (labels / picking use C.vpNear = projection x rotation-only view, C.pos, C.fov)
  _camInfo(cam) {
    const pos = cam.pos; const dir = cam.dir || [cam.target[0] - pos[0], cam.target[1] - pos[1], cam.target[2] - pos[2]];
    const l = Math.hypot(dir[0], dir[1], dir[2]) || 1; const f = [dir[0] / l, dir[1] / l, dir[2] / l];
    let r = [-f[2], 0, f[0]]; const rl = Math.hypot(r[0], r[2]) || 1; r = [r[0] / rl, 0, r[2] / rl];
    const u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]];
    const asp = this.W / Math.max(1, this.H); const n = 1, fa = 1e5; const th = 1 / Math.tan(cam.fov / 2);
    // column-major P * V (V rows: r, u, -f; no translation)
    const P = [th / asp, 0, 0, 0, 0, th, 0, 0, 0, 0, -(fa + n) / (fa - n), -1, 0, 0, -2 * fa * n / (fa - n), 0];
    const V = [r[0], u[0], -f[0], 0, r[1], u[1], -f[1], 0, r[2], u[2], -f[2], 0, 0, 0, 0, 1];
    const M = new Float32Array(16);
    for (let c = 0; c < 4; c++) for (let rr = 0; rr < 4; rr++) { let s = 0; for (let k = 0; k < 4; k++) s += P[k * 4 + rr] * V[c * 4 + k]; M[c * 4 + rr] = s; }
    this.curCam = { pos, dir: f, up: u, fov: cam.fov };
    return { vpNear: M, vp: M, pos, fov: cam.fov, dir: f, up: u };
  }
  // for QA jobs: a summary of what is drawn
  debugInfo() {
    const R = this.engine.renderer; const out = { backend: this.engine.backend, tier: this.tier, W: this.W, H: this.H, calls: R.info.render.calls, tris: R.info.render.triangles, frames: this.frames };
    if (this.acr) { out.aircraft = []; for (const [ac, e] of this.acr.entries) { if (out.aircraft.length >= 3) break; const U = {}; for (const k of ['top', 'tail', 'belly']) if (e.U[k]) U[k] = e.U[k].toArray().map(v => +v.toFixed(3)); out.aircraft.push({ id: ac.id, type: ac.type, real: !!(e.real && e.real.visible), liv: ac.liv && ac.liv.name, U }); } }
    return out;
  }
  // for QA jobs: everything drawable is on screen
  isComplete() { return this.ready && this.built && !!this.bridges && !this.pendingSigns.length; }
}
