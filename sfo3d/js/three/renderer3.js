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
// Review round 1 changes made here: exposure (day gain; keyed on the total horizontal illuminance), lamp units (LAMP_M), floodlight
// field + lamp state, ground-bake tiles spread over frames, dynamic resolution quantised with hysteresis, bridges / GSE
// independent of the sign font (canvas-atlas fallback when the MSDF font fails), IBL ground from the airfield bake's
// mean colour, fatal-error UI (init failure, WebGPU device loss), per-frame draw-call / memory metrics.
import { THREE, TSL } from './lib.js';
import { Engine, QUALITY3 } from './engine.js';
import { Sky } from './sky.js';
import { GroundBakes, groundMaterial, waterMaterial } from './ground.js';
import { objectMaterial } from './objects.js';
import { markingMaterial } from './markings.js';
import { loadSignFont, SignBuilder, signMaterials, signMeshes, faceIndex, worldSignAtlasMap, atlasSignMaterial } from './signs.js';
import { Bridges3 } from './bridges.js';
import { Sprites } from './lights.js';
import { AircraftRenderer } from './aircraft.js';
import { geometryOf, textureOf, retainedImageBytes } from './convert.js';
import { glCanvas, setMaxTextureSize, imageHooks } from './compat/gl.js';
import { floodField, E_STAND } from './flood.js';
import { lampK } from './tsl/common.js';

const { uniform } = TSL;
const T0 = performance.now();
const tlog = (m) => console.log('[r3] ' + m + ' at ' + ((performance.now() - T0) / 1000).toFixed(1) + ' s');
const sstep = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };

// Exposure. Day: the app's exposure (js/live/app.js applyEnv, 0.45 in sun) x DAY_GAIN (review round 1: sunlit white
// paint rendered mid-grey, and the image was flat). DAY_GAIN and the AgX look (engine.js grade: contrast 1.8 in log2
// around 18 % grey, look saturation 1.0, saturation 1.0) were chosen offline on HDR dumps of the named views
// (tools/build3/grade_hdr.py; docs/research/engine_impl.md §4.4): gate view p1 62 / p50 212 / p99.5 246, close-up p1 40.
// (Round-1 grade 1.2 / 1.4 / 1.1 / 1.05: p1 85, p99.5 238.) Night: derived from the floodlight
// level instead of the app's fixed 2.4: lit stand concrete (albedo RHO_CONC, the airfield bake's concrete) under the
// ICAO stand average (E_STAND, js/three/flood.js) is placed at the display key KEY_NIGHT (exposed value that the AgX look
// maps to ~18 % display grey). Between the two the app's darkness curve (sun elevation +2 deg .. -10 deg) blends.
const DAY_GAIN = 1.02, KEY_NIGHT = 0.16, RHO_CONC = 0.37, APP_NIGHT_EXPO = 2.4;
// Lamps vs sky (review round 1: "re-check dusk"). The lamps (floods, windows, signs, city lights, sprites) are authored in
// lamp units (E_STAND = 0.62 = 20 lux) and the sun and sky in the sky model's units, where the sun outside the
// atmosphere is env.sunI = 20 (js/live/app.js) = the luminous solar constant, ~133 klx (Darula, Kittler & Gueymard
// 2005, 133.3 klx; recalled, not re-checked here), so 1 unit ~ 6,670 lux. The two used to be mixed 1:1, which made the
// floods ~200x too strong against the twilight sky: at the 'dusk' preset (sun -4.5 deg) the sky model gives ~0.006
// units (~40 lux) of sky irradiance, the floods 20 lux, yet the apron rendered 5x brighter than the sky and the dusk
// view looked like night. LAMP_M converts lamp units to sky units; it is applied once the lamps are on (tsl/common.js
// lampK = LAMP_M ^ nightF, nightE = nightF x LAMP_M), and the exposure is keyed on the total horizontal illuminance.
const LUX_PER_UNIT = 133300 / 20;
export const LAMP_M = (20 / LUX_PER_UNIT) / E_STAND;
export const NIGHT_EXPOSURE = KEY_NIGHT * Math.PI / (RHO_CONC * E_STAND * LAMP_M); // in sky units (lamps x LAMP_M)
const lum = (c) => 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];

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
    const qs = new URLSearchParams(location.search);
    this.W = W; this.H = H; this.tier = tierOf(opts); this.Q = QUALITY3[this.tier];
    setMaxTextureSize(this.Q.maxTex); // image textures decoded after this point are capped (phones: 1024)
    this.canvas = glCanvas; this.dbgNoCast = qs.get('nocast') === '1'; this.fixedRes = qs.get('res') === '1';
    this.engine = new Engine(document.getElementById('app') || document.body, this.Q, { canvas: this.canvas });
    this.engine.onLost = (info) => this.lost(info);
    this.ready = false; this.failed = null; this.frames = 0; this.jobs = [];
    this.light = { sunDir: [0, 1, 0], sunColor: [1, 1, 1], skyUp: [0.3, 0.4, 0.6], skyHorizon: [0.5, 0.55, 0.6], ground: [0.1, 0.1, 0.1] };
    this.baseLight = null; this.extraCommon = {}; this.progs = {}; this.curCam = null; this.curRange = null;
    this.world = null; this.sceneShim = null; this.seen = new Set(); this.pendingSigns = []; this.clouds = new Map();
    this.pxScale = uniform(0.001); this.time = uniform(0); this.night = uniform(0); this.nightE = uniform(0); // nightE: night-only lamp emission scale (nightF x LAMP_M)
    this.exposureScale = +(qs.get('expo') || 1.0);
    this.initP = this.engine.init().then(() => this._onReady()).catch((e) => {
      this.failed = e; console.error('three.js renderer failed to start', e);
      this.fatal('Sorry — this browser could not start the 3D renderer (WebGPU / WebGL 2).<br><small>' + String(e && e.message || e) + '</small>', 'renderer: ' + String(e && e.stack || e));
    });
    this.fontP = loadSignFont().then(f => { this.font = f; }).catch(e => { this.fontFailed = true; console.error('[r3] ERROR: MSDF sign font failed to load; signs use the canvas atlas', e); });
  }
  // ------------------------------------------------------------ failure paths
  // fatal error: the app's loading overlay if it is still there, and an overlay of our own (the app has no hook yet:
  // docs/requests/engine_exports.md); also window.__sfoError for the QA harness
  fatal(html, detail) {
    window.__sfoError = detail || html;
    const L = document.getElementById('loading'); if (L) { const m = L.querySelector('.msg'); if (m) m.innerHTML = html; L.classList.add('err'); L.classList.remove('done'); }
    let o = document.getElementById('r3fatal');
    if (!o) { o = document.createElement('div'); o.id = 'r3fatal'; o.style.cssText = 'position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);max-width:min(90vw,420px);padding:16px 20px;background:rgba(12,14,18,0.92);color:#eee;font:15px/1.4 system-ui,sans-serif;border-radius:10px;z-index:9999;text-align:center'; document.body.appendChild(o); }
    o.innerHTML = html;
  }
  // WebGPU device loss (on WebGL 2 the canvas fires webglcontextlost itself, which js/live/app.js handles): send the
  // app the same event so it stops its loop, and show the message
  lost(info) {
    tlog('device lost: ' + (info && info.message));
    if (this.engine.backend === 'webgpu' && this.canvas) { try { this.canvas.dispatchEvent(new Event('webglcontextlost', { cancelable: true })); } catch (e) { } }
    this.fatal('The graphics device was lost (the GPU ran out of memory or was reset). <a href="#" onclick="location.reload()">Reload</a>, or pick a lower quality in Settings.', 'device lost: ' + (info && info.message));
  }
  // ------------------------------------------------------------ old Renderer interface
  addProgram(name) { this.progs[name] = true; }
  // Render size. ?res=1 pins it to the canvas size x devicePixelRatio (QA renders). Otherwise the app's dynamic
  // resolution (js/live/app.js: x0.88 / x1.08 every 2.5 s) is quantised to a few steps of the canvas size and applied at
  // most every 8 s (a new size reallocates every post target and restarts TRAA's history: review round 1); a change of
  // the canvas itself (rotation, window resize) applies at once.
  resize(w, h) {
    const c = this.canvas;
    if (this.fixedRes && c) { const d = Math.min(window.devicePixelRatio || 1, 2); w = Math.max(2, Math.round(c.clientWidth * d)); h = Math.max(2, Math.round(c.clientHeight * d)); }
    else if (c && c.width > 0 && c.height > 0) {
      const cw = c.width, ch = c.height; const ratio = Math.min(1, Math.max(w / cw, h / ch));
      const steps = [1, 0.85, 0.72, 0.6, 0.5, 0.4]; let st = steps[steps.length - 1]; for (const s of steps) if (s <= ratio + 0.03) { st = s; break; }
      const now = performance.now(); const canvasChanged = this._cw !== cw || this._ch !== ch;
      if (!canvasChanged && this._step !== undefined && st !== this._step && now - (this._tStep || 0) < 8000) return; // hysteresis
      if (!canvasChanged && st === this._step) return;
      this._cw = cw; this._ch = ch; this._step = st; this._tStep = now;
      w = Math.max(2, Math.round(cw * st)); h = Math.max(2, Math.round(ch * st));
    }
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
    this.sky.u.night = this.nightE; this.sky.u.time = this.time; // ground.js city lights: nightE
    if (this.env) this.sky.setEnv(this.env);
    // apron floodlight field from the masts (before any material is compiled: the light node samples it)
    const masts = (world.details && world.details.masts) || [];
    const f = floodField(masts); if (f) { this.engine.flood.setField(f); tlog('flood field ' + f.w + 'x' + f.h + ' (' + JSON.stringify(f.stats) + ')'); }
  }
  // js/world/world.js bakeGround(R, world, log, opts) (compat/world.js): queued as tiles, rendered in frameScene
  requestBake(world, opts = {}) {
    if (!this.bakes) this.bakes = new GroundBakes(this.engine, world, this.sky, this.Q); // takes the source maps now
    const sunOnly = !!opts.sunOnly && this.bakedOnce;
    this.bakedOnce = true;
    this.bakes.enqueue({ sunOnly }); this.bakeT0 = performance.now(); this.bakeKind = sunOnly ? 'sun' : 'full';
  }
  run(fn) { if (this.ready) fn(); else this.jobs.push(fn); }
  // ------------------------------------------------------------ init
  _onReady() {
    this.ready = true; this.resize(this.W, this.H); const E = this.engine;
    const qs = new URLSearchParams(location.search);
    for (const k of ['sat', 'contrast', 'lookSat', 'vignette']) if (qs.get(k) != null) { E.grade[k].value = +qs.get(k); (this.gradeLock = this.gradeLock || {})[k] = true; }
    for (const fn of this.jobs.splice(0)) fn();
    // upload decoded images at once and drop their CPU copies (js/three/compat/gl.js imageHooks, convert.js releaseImage)
    imageHooks.ready = (rec) => { if (rec.deleted) return; const t = textureOf(rec, { anisotropy: 8 }); if (t && t.image && !t.image.isReleased) { try { E.renderer.initTexture(t); } catch (e) { console.warn('[r3] texture upload', e); } } };
    for (const r of imageHooks.queue.splice(0)) imageHooks.ready(r);
    console.log('three.js r' + THREE.REVISION + ' ' + E.backend + (E.reversed ? ' (reversed depth)' : '') + ', tier ' + this.tier);
  }
  // ground bakes: a few tiles per frame (all tiles of the first bake before the scene is built)
  _stepBakes() {
    const B = this.bakes; if (!B || !B.pending) return true;
    // first bake: 6 tiles per frame (nothing is shown yet); rebakes: 1 tile (<= 1024² texels) per frame, so a sun-driven
    // city rebake (32 tiles) is spread over ~1 s; QA renders (?res=1) do 8 per frame
    const first = !this.built; const done = B.step(this.engine.renderer, first ? 6 : this.fixedRes ? 8 : 1);
    if (done) { tlog('bake (' + this.bakeKind + ') done in ' + ((performance.now() - this.bakeT0) / 1000).toFixed(1) + ' s'); if (!this.groundAlb && !this._albP) this._groundAlbedo(); }
    return done;
  }
  // mean colour of the airfield bake (coverage-weighted), read back once: the IBL ground below the horizon (review
  // round 1: the grey sky-coloured ground made shade on the apron blue; sunlit concrete bounces warm light)
  _groundAlbedo() {
    const R = this.engine.renderer; const rt = new THREE.RenderTarget(16, 16, { depthBuffer: false, generateMipmaps: false });
    const m = new THREE.NodeMaterial(); m.blending = THREE.NoBlending; m.depthTest = m.depthWrite = false;
    m.colorNode = TSL.texture(this.bakes.apt.texture, TSL.uv()).level(8.0);
    const q = new THREE.QuadMesh(m); const prev = R.getRenderTarget(); R.setRenderTarget(rt); q.render(R); R.setRenderTarget(prev);
    this._albP = R.readRenderTargetPixelsAsync(rt, 0, 0, 16, 16).then((px) => {
      let r = 0, g = 0, b = 0, w = 0; const s = px.BYTES_PER_ELEMENT === 1 ? 1 / 255 : 1;
      for (let i = 0; i < px.length; i += 4) { const a = px[i + 3] * s; r += px[i] * s * a; g += px[i + 1] * s * a; b += px[i + 2] * s * a; w += a; }
      const lin = (c) => c; // the bake target is linear (NoColorSpace, UnsignedByte)
      if (w > 0) { this.groundAlb = [lin(r / w), lin(g / w), lin(b / w)]; this.envDirty = true; tlog('IBL ground albedo ' + this.groundAlb.map(v => v.toFixed(3)).join(',')); }
    }).catch(e => console.warn('ground albedo readback', e)).finally(() => { rt.dispose(); m.dispose(); });
  }
  // scene objects, built once the world, the sky and the first bake exist
  _buildStatic() {
    const E = this.engine, S = E.scene, W = this.world, Q = this.Q;
    const sky = this.sky;
    S.backgroundNode = sky.backgroundNode(); S.fogNode = sky.fogNode();
    // sun radiance x cloud shadow (the old shaders' getShadow() * cloudShadow(wp)); three multiplies the CSM term in
    this.sunRad = uniform(new THREE.Vector3(1, 1, 1));
    E.sun.colorNode = this.sunRad.mul(sky.cloudShadow(TSL.positionWorld));
    this.gMat = groundMaterial(W, this.bakes, sky, Q); this.wMat = waterMaterial(W, this.bakes, sky);
    const common = { noiseTex: this.noiseTex, night: this.nightE, time: this.time }; // objects.js night emissions: nightE
    this.objMat = objectMaterial(common); this.vehMat = objectMaterial({ ...common, instanced: true });
    this.markMat = markingMaterial({ noiseTex: this.noiseTex, pxScale: this.pxScale, reversed: E.reversed });
    this.sprites = new Sprites(24000, { depthNode: E.depthNode, expo: E.expo, night: this.night }); E.fxScene.add(this.sprites.mesh);
    this.acr = new AircraftRenderer(S, { noiseTex: this.noiseTex });
    this.staticGroup = new THREE.Group(); this.staticGroup.name = 'world'; S.add(this.staticGroup);
    this.built = true; tlog('static scene built');
    // compile the scene's programs off the frame loop where the backend can (KHR_parallel_shader_compile / WebGPU
    // async pipelines); frames are held until then (at most 30 s) so the first frames do not stall one by one
    this._syncItems();
    this.compiling = Promise.race([E.renderer.compileAsync(S, E.camera), new Promise(r => setTimeout(r, 30000))])
      .then(() => { this.compiled = true; tlog('programs compiled'); }, (e) => { this.compiled = true; console.warn('compileAsync', e); });
  }
  _signMats() { if (!this.signMats && this.font) this.signMats = signMaterials(this.font, { night: this.nightE, noiseTex: this.noiseTex, reversed: this.engine.reversed }); return this.signMats; }
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
    // airfield signs: MSDF text once the font is there; the canvas atlas (as live.html draws them) if it failed
    if (this.pendingSigns.length && (this._signMats() || this.fontFailed)) {
      if (!this.worldLookup) this.worldLookup = faceIndex(worldSignAtlasMap(W.details || {}));
      for (const it of this.pendingSigns.splice(0)) {
        let g;
        if (this.signMats) { const d = it.mesh.data; const sb = new SignBuilder(this.font); sb.addSignArrays({ pos: d.pos, nrm: d.nrm, uv: d.uv, ext: d.extra }, this.worldLookup); g = signMeshes(sb, this.signMats, 'signs'); }
        else g = this._atlasSign(it);
        if (!g) continue; if (!it.castShadow) g.traverse(o => { o.castShadow = false; }); G.add(g);
      }
    }
  }
  // fallback sign mesh: the builder's own quads and canvas atlas (uniforms.uAtlas), js/live/signs.js SIGN_FS look
  _atlasSign(it) {
    const u = typeof it.uniforms === 'function' ? it.uniforms() : it.uniforms; const rec = u && (u.uAtlas || u.uTex);
    const tex = rec ? textureOf(rec, { anisotropy: 8, colorSpace: THREE.SRGBColorSpace }) : null; if (!tex) return null;
    const m = new THREE.Mesh(geometryOf(it.mesh), atlasSignMaterial(tex, { night: this.nightE, reversed: this.engine.reversed })); m.castShadow = true; m.receiveShadow = true; m.matrixAutoUpdate = false;
    return m;
  }
  // ------------------------------------------------------------ per frame (compat/scene.js Scene.frame)
  frameScene(sc, t, camPos) {
    if (!this.ready || !this.bakes || !this.sky) return;
    if (!this._stepBakes() && !this.built) return; // the first bake completes before the scene is built
    if (!this.built) this._buildStatic();
    this._syncItems();
    // bridges, stand equipment and GSE do not wait for the sign font (review round 1: without the font the scene had
    // no bridges at all); their sign faces are added when the font arrives, or from the canvas atlas if it failed
    if (sc.gateSys && !this.bridges) {
      this.bridges = new Bridges3(sc.gateSys, { objMat: this.objMat, vehMat: this.vehMat, signFont: null, signMats: null, night: this.nightE, reversed: this.engine.reversed });
      this.engine.scene.add(this.bridges.group);
    }
    if (this.bridges) {
      if (!this.bridges.signMats && this._signMats()) this.bridges.setSignFont(this.font, this.signMats);
      else if (!this.bridges.signMats && this.fontFailed && !this.bridges.atlasFallback) this.bridges.useAtlasFallback();
      this.bridges.update(Date.now()); sc.gateSys.sprites = this.bridges.sprites;
    }
    this.acr.sync(sc.aircraft, camPos);
  }
  // ------------------------------------------------------------ render (fr = compat Scene.frame result)
  render(fr, cam, t, post = {}) {
    const E = this.engine;
    const C = this._camInfo(cam);
    if (!this.ready || !this.built || !this.compiled) return C;
    const R = E.renderer, S = E.scene, L = this.light;
    // environment: GPU sky, sun, IBL (after the app's night-floor adjustment of R.light)
    if (this.envDirty) {
      this.envDirty = false;
      // the app's night floor (moon / city glow, js/live/app.js applyEnv: max(sky, floor)) is in lamp units: keep the
      // physical sky and add LAMP_M x the part the floor raised
      const B0 = this.baseLight;
      if (B0 && !L._lampScaled) { for (const k of ['skyUp', 'skyHorizon', 'ground']) L[k] = L[k].map((v, i) => B0[k][i] + LAMP_M * Math.max(0, v - B0[k][i])); L._lampScaled = true; }
      if (this.groundAlb && !L._albScaled) { const a = this.groundAlb; L.ground = L.ground.map((g, k) => g / 0.16 * a[k]); L._albScaled = true; } // Sky.lightFor: ground = E x 0.16 / pi
      this.sky.applyLight(L);
      const bu = this.baseLight ? this.baseLight.skyUp : L.skyUp;
      this.sky.u.skyFloor.value.setRGB(...L.skyUp.map((v, k) => Math.max(0, v - bu[k])));
      this.sky.renderSky(R);
      this.sky.updateEnvironment(R, S);
      E.setSun(L.sunDir, L.sunColor); this.sunRad.value.set(L.sunColor[0], L.sunColor[1], L.sunColor[2]);
    }
    const nightF = this.extraCommon.uNight || 0;
    this.time.value = t; this.night.value = nightF; this.nightE.value = nightF * LAMP_M; lampK.value = Math.pow(LAMP_M, nightF);
    E.flood.intensity = nightF * LAMP_M; // floodlights switch on with the app's night factor (sun below ~6 deg .. -4 deg)
    const wu = this.world.waterU; if (this.wMat && wu) { const u = this.wMat.userData; if (wu.uWind) u.uWind.value.set(wu.uWind[0], wu.uWind[1]); if (wu.uWaveAmp != null) u.uAmp.value = wu.uWaveAmp; }
    E.setCamera(cam, this.W, this.H);
    this.pxScale.value = 2 * Math.tan(cam.fov / 2) / Math.max(1, this.H);
    // light sprites
    const sp = this.sprites; sp.begin(); for (const s of fr && fr.sprites || []) sp.put(s); sp.end(E.camera, this.H);
    // exposure and grade (the app's post settings: exposure, sat, bloom, vignette, grain)
    const el = Math.asin(Math.max(-1, Math.min(1, L.sunDir[1]))) * 180 / Math.PI; const dark = sstep(2, -10, el);
    // day: the app's exposure without its night term, x DAY_GAIN; lamps on / low sun: lit concrete at the key KEY_NIGHT
    // under the total horizontal illuminance (sun + sky from the sky model, + floods); the larger of the two
    const pe = post.exposure ?? 0.45; const B = this.baseLight || L;
    const eAmb = lum(B.sunColor) * Math.max(0, B.sunDir[1]) + Math.PI * lum(B.skyUp);
    const eKey = eAmb + E_STAND * LAMP_M * nightF;
    const expoKey = KEY_NIGHT * Math.PI / (RHO_CONC * Math.max(eKey, 1e-7));
    const expoDay = dark < 0.999 ? Math.max(0, (pe - APP_NIGHT_EXPO * dark) / (1 - dark)) * DAY_GAIN : 0;
    E.expo.value = Math.max(expoDay, expoKey) * this.exposureScale; this.eKey = eKey;
    const G = E.grade, lock = this.gradeLock || {};
    if (!lock.sat) G.sat.value = (post.sat ?? 1.1) / 1.1; // the app's 1.1 was tuned on top of ACES: 1.0 here; user changes stay relative
    if (!lock.vignette) G.vignette.value = post.vignette ?? 0.18;
    G.grain.value = post.grain ?? 0; G.time.value = t;
    if (E.bloomNode) E.bloomNode.strength.value = 0.035 * ((post.bloom ?? 0.012) / 0.012);
    if (this.dbgNoCast) S.traverse(o => { if (o.isMesh) o.castShadow = false; });
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
  // for QA jobs: a summary of what is drawn. drawCalls / triangles are per frame (info.render resets every frame);
  // info.render.calls counts render() calls since start-up and is NOT a per-frame figure (review round 1)
  debugInfo() {
    const R = this.engine.renderer; const I = R.info; let nObj = 0, nVis = 0; this.engine.scene.traverse(o => { if (o.isMesh) { nObj++; if (o.visible) nVis++; } });
    const out = { meshes: nObj, visible: nVis, backend: this.engine.backend, tier: this.tier, W: this.W, H: this.H,
      drawCalls: I.render.drawCalls, frameCalls: I.render.frameCalls, tris: I.render.triangles, renderCallsTotal: I.render.calls, frames: this.frames,
      texMB: +((I.memory.texturesSize || 0) / 1048576).toFixed(1), textures: I.memory.textures, renderTargets: I.memory.renderTargets, retainedImageMB: +(retainedImageBytes() / 1048576).toFixed(1),
      expo: +this.engine.expo.value.toFixed(3), eKeyLux: this.eKey != null ? Math.round(this.eKey * LUX_PER_UNIT * 10) / 10 : null, night: this.night.value, flood: this.engine.flood.stats || null, bakesPending: this.bakes ? this.bakes.pending : null, groundAlb: this.groundAlb || null };
    if (this.acr) { out.aircraft = []; for (const [ac, e] of this.acr.entries) { if (out.aircraft.length >= 3) break; out.aircraft.push({ id: ac.id, type: ac.type, real: !!(e.real && e.real.visible), liv: ac.liv && ac.liv.name }); } }
    return out;
  }
  // for QA jobs: everything drawable is on screen (sign text may come from the fallback atlas if the font failed)
  isComplete() { return this.ready && this.built && !!this.compiled && !!this.bridges && !(this.bakes && this.bakes.pending) && !this.pendingSigns.length && (!!this.bridges.signMats || !!this.bridges.atlasFallback); }
}
