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
// Review round 2 changes made here: this class owns the canvas size (the app's size writes are recorded, not applied:
// dynamic resolution used to leave three drawing into a corner of a full-size canvas), the day grade retuned for the
// luminance-only AgX look, floodlight spots for the masts nearest the view + the ground-bounce albedo, masts on their
// own layer, unused canvas sign atlases released once the MSDF font is in, sharpening strength from the render scale,
// a progress overlay until the first frame, instanced cars on the garage roofs.
// Environment steps 3-4 (2026-11-05, docs/research/environment_impl.md §3; spec docs/research/environment_spec.md §7-8),
// when the app hands over an EnvState (R.envState, js/env/state.js): the sun and sky calibrated to USNO Circular 171
// (sky_model.js sunCalibration) and adjusted for the reported clouds (÷ D; beam through the per-layer coverage maps),
// the night-sky floor and the Moon disc (and the Moon as the directional light at night, no shadows), fog slabs, up to
// 6 cloud layers (sky shader + planes for the layers below 5,000 ft; the app's single 'cloud' slab items are ignored),
// auto-exposure (64 x 36 luminance readback, js/env/atmo/exposure.js; ?ae=0 = the previous keyed exposure, ?ev=<EV100>
// fixed), pre-exposure (every emitter x pre, the post exposure / pre; ?pre=1 pins it for the invariance check), rain /
// drizzle particles (js/three/rain.js), lightning and wet pavement (ground.js).
import { THREE, TSL } from './lib.js';
import { Engine, QUALITY3, LITE3 } from './engine.js';
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
import { disposeRecord } from './convert.js';
import { floodField, E_STAND, mastE, mastAim, MAST_LAYER, FLOOD_COLOR } from './flood.js';
import { garageCars, glassWallAttrs } from './objects.js';
import { BUILDINGS } from '../../data/sfo_buildings.js';   // BA-G rings: the light mullion finish of its first-pass panes (env-7)
import { GROUND_Y } from '../geo.js';
import { lampK } from './tsl/common.js';
import { GB as GBOUNCE, setGroundRef } from './tsl/ground_bounce.js';   // local ground bounce (env-10)
import { Buildings3D } from './buildings3d.js'; // Blender building assets (data/buildings3d/*.glb)
import { Rain } from './rain.js';
import { makeSSR } from './ssr.js';   // wet-pavement object reflections (env-2)
import { sunCalibration, cloudAdjust, nightSkyLuminance, moonDisc, renderSlabs, cloudLayers, histogram8, detailDistribution, fogTransmittance, fogBeamT, sstep as sstepE } from '../env/atmo/sky_model.js';
import { meter, adapt, clampEV, exposureForEV, evForExposure, ev100FromLuminance, preExposure, METER_BIAS, incidentBound } from '../env/atmo/exposure.js';
import { rainParams, showerFactor, lightningFlashes, flashLevel, wetStep } from '../env/atmo/weather_fx.js';
import { directionWorld } from '../env/ephemeris.js';
import { aureole } from '../env/lighting/photometry.js';

const { uniform } = TSL;
const T0 = performance.now();
const tlog = (m) => console.log('[r3] ' + m + ' at ' + ((performance.now() - T0) / 1000).toFixed(1) + ' s');
const sstep = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };

// Exposure. Day: the app's exposure (js/live/app.js applyEnv, 0.45 in sun) x DAY_GAIN (review round 1: sunlit white
// paint rendered mid-grey, and the image was flat). DAY_GAIN and the AgX look (engine.js grade: contrast 1.8 in log2
// around 18 % grey, look saturation 1.0, saturation 1.0) were chosen offline on HDR dumps of the named views
// (tools/build3/grade_hdr.py; docs/research/engine_impl.md §4.4). Round 2 (luminance-only contrast 1.6, look saturation
// 1.0 -> 1.8 on the shoulder): DAY_GAIN 0.80, gate view p1 39 / p50 189 / p99.5 233, open shade display B/R ~2.3 (was
// 4.6 with the per-channel contrast), sunlit concrete ~190. (Round-1 grade 1.2 / 1.4 / 1.1 / 1.05: p1 85, p99.5 238;
// round-1 final 1.02 / 1.8 per channel: p1 45, p99.5 243, navy shade, pastel paint.) Night: derived from the floodlight
// level instead of the app's fixed 2.4: lit stand concrete (albedo RHO_CONC, the airfield bake's concrete) under the
// ICAO stand average (E_STAND, js/three/flood.js) is placed at the display key KEY_NIGHT (exposed value that the AgX look
// maps to ~18 % display grey). Between the two the app's darkness curve (sun elevation +2 deg .. -10 deg) blends.
const DAY_GAIN = 0.80, KEY_NIGHT = 0.16, RHO_CONC = 0.37, APP_NIGHT_EXPO = 2.4;
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
// Illuminance inside the terminal halls seen through the curtain walls (js/three/objects.js id 1; review round 3: the
// hall was shaded as an outdoor wall). E_hall = HALL_DF x the exterior horizontal illuminance (sun + sky) + HALL_LUX of
// lamps by day (fading out as the night term of objects.js takes over). Both inferred: HALL_DF 5 % is a typical average
// daylight factor of a deep, fully glazed concourse; HALL_LUX 200 lx is the usual design level of airport departure
// halls (EN 12464-1 airports table, recalled, not re-checked here). Not SFO measurements.
const HALL_DF = 0.05, HALL_LUX = 200;
// Environment step 3 constants (I unless noted). K_TWILIGHT: the C171 calibration factor where C171's Sun term falls
// below 0.05 lx (Sun ~ -9 deg; sky_model.js CAL_MIN_LUX), kept below that (M: 0.167 at predawn_fog, tools/env/test_sky.mjs).
// MOON_COL: moonlight a little warmer than sunlight (~4,100 K, I). FLASH_COL / flash illuminance: lightning brightness is
// NV (spec §4.6): 3 lx at 3 km, inverse square, 0.05-20 lx (I, QA-tuned). Rain: a 1-px streak covers 0.25 of its pixel
// with the drop radiance, "over" the scene colour (I, display weight; js/three/rain.js, review look2-7).
const K_TWILIGHT = 0.167, MOON_COL = [1.0, 0.95, 0.86], FLASH_COL = [0.86, 0.9, 1.0], RAIN_K = 0.25, FLASH_GLOW_CDM2 = 50;
const MAST_LOBE_FLOOR = 0.25;   // floodlight lamps seen from the side / behind: fraction of the on-axis intensity (I / NV, Q7; attachWorld)
const AUR_LOW_MAX_N = 64, AUR_LOW_MAX_DEG = 2.5;   // phone-tier aureole caps (I; look2-10)
const REFL_MAX_M = 600, REFL_K = 0.7;   // lamp reflections on wet pavement: range, share of the Fresnel energy in the image (I)
const DEGR = Math.PI / 180;

// tier: ?tier=ultra|high|medium|low overrides; otherwise the old app's choice, recognised from the options it passes
// (js/live/app.js QUALITY: ultra = 4096 shadow map, high = 3072, low = 2x MSAA)
function tierOf(opts) {
  const q = new URLSearchParams(location.search).get('tier');
  if (q && QUALITY3[q]) return q;
  if (opts && opts.msaa === 2) return 'low';
  if (opts && opts.shadowRes >= 4096) return 'ultra';
  if (opts && opts.shadowRes >= 3072) return 'high';
  return 'medium';
}

export class Renderer3 {
  constructor(W, H, opts = {}) {
    const qs = new URLSearchParams(location.search);
    this.W = W; this.H = H; this.tier = tierOf(opts); this.Q = QUALITY3[this.tier];
    // lite phone build (window.SFO_LITE, engine.js LITE3): the low tier with the lite overrides; without TRAA nothing averages
    // a per-frame rotation of the shadow PCF taps, so it is turned off (as js/three/perf.js does for aa: 'fxaa')
    if (window.SFO_LITE && this.tier === 'low') { this.Q = { ...this.Q, ...LITE3 }; this.lite = true; if (!this.Q.traa) Engine.temporalShadows = false; }
    setMaxTextureSize(this.Q.maxTex); // image textures decoded after this point are capped (phones: 1024)
    this.canvas = glCanvas; this.dbgNoCast = qs.get('nocast') === '1'; this.fixedRes = qs.get('res') === '1';
    this.engine = new Engine(document.getElementById('app') || document.body, this.Q, { canvas: this.canvas });
    this._ownCanvas();
    this.engine.onLost = (info) => this.lost(info);
    this.ready = false; this.failed = null; this.frames = 0; this.jobs = [];
    this.light = { sunDir: [0, 1, 0], sunColor: [1, 1, 1], skyUp: [0.3, 0.4, 0.6], skyHorizon: [0.5, 0.55, 0.6], ground: [0.1, 0.1, 0.1] };
    this.baseLight = null; this.extraCommon = {}; this.progs = {}; this.curCam = null; this.curRange = null;
    this.world = null; this.sceneShim = null; this.seen = new Set(); this.pendingSigns = []; this.clouds = new Map();
    this.pxScale = uniform(0.001); this.time = uniform(0); this.night = uniform(0); this.nightE = uniform(0); // nightE: night-only lamp emission scale (nightF x LAMP_M)
    this.interiorE = uniform(HALL_LUX / LUX_PER_UNIT); // terminal-hall illuminance behind the curtain walls (sky units; render())
    this.shadeK = uniform(new THREE.Vector3(1, 1, 1)); // sky / (sun + sky) horizontal irradiance per channel (objects.js curtain-wall reflections)
    this.kG = uniform(new THREE.Vector3(1, 1, 1)); // concrete mean albedo / IBL ground albedo per channel (objects.js curtain-wall reflections; _groundAlbedo)
    // ?glassab=1: curtain-wall A/B switches (objects.js id 1; docs/research/engine_impl.md §4.8): x 1 = round-3 inputs
    // (also interiorE from sun + sky: glassABOld), y / z / w = weights of reflection, interior, frame. QA only.
    if (qs.get('glassab') === '1') { this.glassAB = uniform(new THREE.Vector4(0, 1, 1, 1)); this.glassABOld = false; }
    this.exposureScale = +(qs.get('expo') || 1.0);
    this.qsGB = qs.get('gbounce') === '0' ? false : true;   // ?gbounce=0: the IBL ground only (A/B of env-10; QA)
    this.gb = GBOUNCE; this.ssrForce = null;   // QA A/B: R.gb.on.value = 0 / 1 (local ground bounce), R.ssrForce = 0 / 1 / null (SSR)
    // auto-exposure / pre-exposure state (environment step 3): ?ae=0 keyed exposure, ?ev=<EV100> fixed, ?pre=1 pinned
    this.aeMode = qs.get('ae') === '0' ? 'off' : 'auto'; this.fixedEV = qs.get('ev') != null ? +qs.get('ev') : null; this.pinPre = qs.get('pre') != null ? +qs.get('pre') : null;
    this.ae = { Lcd: null, t: 0, metered: null }; this.pre = 1; this._meterSnap = true; this.envState = null; this.sunK = null; this.wet = null; this.layers = [];
    this.initP = this.engine.init().then(() => this._onReady()).catch((e) => {
      this.failed = e; console.error('three.js renderer failed to start', e);
      // the browser is blamed only when it really lacks both APIs (review round 3: a TypeError in our own code was shown
      // as "this browser could not start the 3D renderer")
      const msg = Renderer3.noGPUApi() ? 'Sorry — this browser could not start the 3D renderer (it supports neither WebGPU nor WebGL 2).'
        : 'Sorry — the 3D renderer failed to start (an error in the app, not your browser). <a href="#" onclick="location.reload()">Reload</a>, or open live.html.';
      this.fatal(msg + '<br><small>' + String(e && e.message || e) + '</small>', 'renderer: ' + String(e && e.stack || e));
    });
    this.fontP = loadSignFont().then(f => { this.font = f; }).catch(e => { this.fontFailed = true; console.error('[r3] ERROR: MSDF sign font failed to load; signs use the canvas atlas', e); });
  }
  // ------------------------------------------------------------ failure paths
  // true when the browser has neither WebGPU nor WebGL 2 (probed on a scratch canvas: the app's canvas may hold a context)
  static noGPUApi() {
    if (typeof navigator !== 'undefined' && navigator.gpu) return false;
    try { const c = document.createElement('canvas'); const g = c.getContext('webgl2'); if (g) { const x = g.getExtension('WEBGL_lose_context'); if (x) x.loseContext(); return false; } } catch (e) { }
    return true;
  }
  // fatal error: window.__sfoError for the QA harness, then the app's hook `R.onFatal(html)` when it has set one
  // (js/live/app.js -> ui.fail: the loading overlay while it is up, else its own #fatal alert; engine_exports.md s.5.2,
  // close-out request C3F2.1 - until round 5 this hook was assigned but never called); without a hook (dev pages) or if
  // it throws, the loading overlay if it is still there and an overlay of our own
  fatal(html, detail) {
    window.__sfoError = detail || html;
    if (typeof this.onFatal === 'function') { try { this.onFatal(html); return; } catch (e) { console.error('[r3] onFatal hook failed', e); } }
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
  // The canvas size belongs to this class (review round 2, critical). js/live/app.js sets canvas.width/height to the
  // full display size and asks for a smaller render size (dynamic resolution); three's setSize then sets the canvas to
  // the render size; on the app's next resize check (every 2.5 s under load) it saw canvas.width != its size and reset
  // the canvas to full size, while three kept drawing a render-size viewport into its lower-left corner (black
  // elsewhere on WebGL 2; a colour/depth size mismatch on WebGPU). Now the app's writes to canvas.width/height are
  // recorded as the intended display size (and reads return the real size three set), only the engine's own resize
  // writes the canvas, and the browser scales the canvas to its CSS size as before.
  _ownCanvas() {
    const c = this.canvas; if (!c || c._r3owned) return;
    const d = (k) => Object.getOwnPropertyDescriptor(HTMLCanvasElement.prototype, k);
    const W = d('width'), H = d('height'); if (!W || !W.set || !H || !H.set) return;
    this._appCW = c.width; this._appCH = c.height; const E = this.engine;
    Object.defineProperty(c, 'width', { configurable: true, get() { return W.get.call(this); }, set: (v) => { if (E._sizing) W.set.call(c, v); else this._appCW = v | 0; } });
    Object.defineProperty(c, 'height', { configurable: true, get() { return H.get.call(this); }, set: (v) => { if (E._sizing) H.set.call(c, v); else this._appCH = v | 0; } });
    c._r3owned = true;
  }
  // ------------------------------------------------------------ old Renderer interface
  addProgram(name) { this.progs[name] = true; }
  // Render size. ?res=1 pins it to the canvas size x devicePixelRatio (QA renders). Otherwise the app's dynamic
  // resolution (js/live/app.js: x0.88 / x1.08 every 2.5 s) is quantised to a few steps of the canvas size and applied at
  // most every 8 s (a new size reallocates every post target and restarts TRAA's history: review round 1); a change of
  // the canvas itself (rotation, window resize) applies at once.
  resize(w, h) {
    const c = this.canvas;
    if (this.fixedRes && c) { const d = Math.min(window.devicePixelRatio || 1, 2); w = Math.max(2, Math.round(c.clientWidth * d)); h = Math.max(2, Math.round(c.clientHeight * d)); this._step = 1; }
    else if (c) {
      // intended display size: the app's last canvas size (recorded by _ownCanvas), else CSS size x the tier's DPR cap
      const dpr = Math.min(window.devicePixelRatio || 1, this.Q.dprMax || 2);
      const cw = this._appCW > 0 ? this._appCW : Math.max(1, Math.round(c.clientWidth * dpr)), ch = this._appCH > 0 ? this._appCH : Math.max(1, Math.round(c.clientHeight * dpr));
      const ratio = Math.min(1, Math.max(w / cw, h / ch));
      // 0.8 is a step because it is the app's low-tier scaleMax (js/live/app.js QUALITY.low): without it phones rendered
      // 0.72x where live.html renders 0.8x (review round 3)
      const steps = [1, 0.85, 0.8, 0.72, 0.6, 0.5, 0.4]; let st = steps[steps.length - 1]; for (const s of steps) if (s <= ratio + 0.03) { st = s; break; }
      const now = performance.now(); const canvasChanged = this._cw !== cw || this._ch !== ch;
      // hysteresis: a step change at most every 8 s (a new size reallocates every post target and restarts TRAA)
      if (!canvasChanged && this._step !== undefined && st !== this._step && now - (this._tStep || 0) < 8000) st = this._step;
      if (canvasChanged || st !== this._step) { this._tStep = now; }
      this._cw = cw; this._ch = ch; this._step = st;
      w = Math.max(2, Math.round(cw * st)); h = Math.max(2, Math.round(ch * st));
    }
    this.W = w; this.H = h;
    // re-apply whenever the drawing buffer differs from the wanted size (also after someone else resized the canvas)
    if (this.ready) {
      const E = this.engine, v = E.renderer.getDrawingBufferSize(new THREE.Vector2());
      if (v.x !== w || v.y !== h || (c && (c.width !== w || c.height !== h))) E.resize(w, h, 1);
      E.casAmount.value = this.casLock != null ? this.casLock : Math.min(0.8, 0.35 + (1 - (this._step || 1)) * 0.6); // sharpen more when fewer pixels are rendered (?cas= pins it: it was parsed but never applied)
    }
  }
  present() { }
  // sky model + ambient terms (synchronous, as js/renderer.js setupSky); GPU sky textures and the PMREM IBL follow at
  // the next frame, after the app has adjusted R.light (night floor)
  setupSky(env) {
    this.env = env; const st = this.envState;
    if (st && st.sun && st.natural) {
      // physical sky (environment step 3): sunI calibrated to C171, light adjusted for the reported clouds, night floor
      // below the horizon the sky model takes the GEOMETRIC Sun (review look1-10: the ephemeris clamps refraction at
      // its -1° value, so the apparent Sun of a deep twilight sits 0.65° high; twilight is defined geometrically, USNO),
      // blended from the apparent direction between apparent el -1° and -2° (no jump at the switch)
      let sunDirSky = env.sunDir;
      { const wG = sstep(-1, -2, st.sun.el); if (wG > 0) { const g = directionWorld(st.sun.az, st.sun.elTrue), a = env.sunDir; const v = [0, 1, 2].map(i => a[i] * (1 - wG) + g[i] * wG); const l = Math.hypot(...v) || 1; sunDirSky = v.map(c => c / l); } }
      const cal = sunCalibration(st, 21e-6, sunDirSky); this.cal = cal;
      if (cal.k != null) this.sunK = cal.k; else if (this.sunK == null) this.sunK = K_TWILIGHT;
      const envP = { ...env, sunDir: sunDirSky, sunI: (env.sunI || 20) * this.sunK, physical: true }; this.envEff = envP;
      // the direct beam through the fog / mist / VV obscuration (fogBeamT; review truth1-5), the loss moved to the diffuse
      const L = cloudAdjust(Sky.lightFor(envP), st, fogBeamT(renderSlabs(st), st.sun.el));
      const ns = nightSkyLuminance(st).units;
      L.skyFloor = [ns, ns, ns]; L.skyUp = L.skyUp.map(v => Math.max(v, ns)); L.skyHorizon = L.skyHorizon.map(v => Math.max(v, ns));
      this.light = L; this.physLight = { ...L, sunColor: L.sunColor.slice(), skyUp: L.skyUp.slice(), skyHorizon: L.skyHorizon.slice(), ground: L.ground.slice() };
      this.baseLight = this.physLight;
      const key = st.wx && st.wx.key; if (key !== this._wxKey || Math.abs(st.tEnv - (this._tEnv0 || 0)) > 600e3) this._meterSnap = true; this._wxKey = key; this._tEnv0 = st.tEnv;
      if (this.sky) this._envSetup(st);
    } else {
      this.envEff = null; this.physLight = null;
      this.light = Sky.lightFor(env); this.baseLight = { ...this.light, skyUp: this.light.skyUp.slice() };
    }
    if (this.sky) this.sky.setEnv(this.envEff || env);
    this.envDirty = true;
  }
  // EnvState -> sky uniforms: fog slabs, cloud layers, Moon (needs this.sky)
  _envSetup(st) {
    const S = this.sky, L = this.physLight; if (!S || !L) return;
    const slabs = renderSlabs(st); this.slabs = slabs;
    // dense-fog in-scatter: ambient sky + ground bounce (I); under a cloud cover the radiance field in the fog is nearly
    // isotropic: half sky (the deck's mean = skyUp), half ground (review look2-8: 0.8 skyUp made the haze under the
    // marine deck brighter than the deck's base towards the horizon); cover = 1 − sunVisibleP
    const cov = 1 - (st.sunVisibleP ?? 1);
    const fogCol = L.skyUp.map((v, k) => v * (0.8 - 0.3 * cov) + L.ground[k] * (0.2 + 0.3 * cov));
    S.setSlabs(slabs, fogCol, sstepE(2e-4, 2e-3, st.atm.sigmaSurface)); S.u.sunGlow.value = st.sunVisibleP ?? 1;
    this.layers = this.cloudDist ? cloudLayers(st, this.cloudDist) : [];
    S.setLayers(this.layers); this.layers = S.layers; S.u.cloud.value.x = 1 - (st.sunVisibleP ?? 1);   // (the tier's layer count)
    S.setMoon(st.moon && st.moon.el > -1 ? moonDisc(st) : null);
    this._cloudPlanes();
  }
  // planes of the low cloud layers (base seen from below, top seen from above), built once (6 layers x 2)
  _cloudPlanes() {
    if (!this.cloudPlanes) {
      if (!this.built || !this.sky) return;
      const N = 64, pos = [], idx = []; const f = (x) => Math.sign(x) * Math.pow(Math.abs(x), 2.2); // denser near the camera (as js/live/app.js setClouds)
      for (let j = 0; j <= N; j++) for (let i = 0; i <= N; i++) pos.push(f(i / N * 2 - 1), 0, f(j / N * 2 - 1));
      for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) { const a = j * (N + 1) + i; idx.push(a, a + N + 1, a + 1, a + 1, a + N + 1, a + N + 2); }
      const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3)); g.setIndex(idx);
      this.cloudCentre = uniform(new THREE.Vector2(0, 0)); this.cloudPlanes = [];
      for (let k = 0; k < 6; k++) for (const top of [false, true]) {
        const m = new THREE.Mesh(g, this.sky.cloudSlabMaterial(k, top, this.cloudCentre)); m.frustumCulled = false; m.renderOrder = 5; m.matrixAutoUpdate = false; m.visible = false; m.userData = { k, top };
        this.engine.scene.add(m); this.cloudPlanes.push(m);
      }
    }
    for (const m of this.cloudPlanes) { const l = this.layers[m.userData.k]; m.visible = !!(l && l.slab && (!m.userData.top || l.thickness > 0)); }
  }
  // ------------------------------------------------------------ attachments from the compat modules
  attachWorld(world, sceneShim) {
    try { this._attachWorld(world, sceneShim); } catch (e) { // the app cannot continue: say so instead of leaving the loading overlay up
      this.failed = e; console.error('[r3] attachWorld failed', e);
      this.fatal('Sorry — the 3D renderer failed to start (an error in the app, not your browser). <a href="#" onclick="location.reload()">Reload</a>, or open live.html.<br><small>' + String(e && e.message || e) + '</small>', 'renderer: ' + String(e && e.stack || e));
      throw e;
    }
  }
  _attachWorld(world, sceneShim) {
    this.world = world; this.sceneShim = sceneShim;
    const T = world.textures;
    this.noiseTex = textureOf(T.noise, { anisotropy: this.Q.aniso }); this.noiseTex.wrapS = this.noiseTex.wrapT = THREE.RepeatWrapping;
    const cloudTex = textureOf(T.clouds); cloudTex.wrapS = cloudTex.wrapT = THREE.RepeatWrapping;
    this.sky = new Sky(this.engine, { cloudTex, noiseTex: this.noiseTex, baseRes: this.Q.skyRes, horizSamples: this.tier === 'low' ? 4 : 8, maxSlabs: this.tier === 'low' ? 4 : 6, maxLayers: this.tier === 'low' ? 4 : 6, floodSamples: this.tier === 'low' ? 3 : 6, floodSamplesBg: this.tier === 'low' ? 4 : 8 }); // look1-12 / look2-10: fewer fog-structure / flood in-scatter samples, slab and layer loops on the phone tier
    this.sky.u.night = this.nightE; this.sky.u.time = this.time; // ground.js city lights: nightE
    // cloud texture histogram -> coverage thresholds of the cloud layers (sky_model.js coverageThreshold; A-CLD)
    { let rec = T.clouds; for (let i = 0; i < 3 && rec && !rec.isTexRecord; i++) rec = rec.tex;
      if (rec && rec.data && rec.data.length) { const h = histogram8(rec.data); this.cloudDist = detailDistribution(h); this.cloudTexSum = rec.data.reduce((a, b) => a + b, 0); }
      else { console.warn('[r3] cloud texture data not available: cloud coverage thresholds assume a uniform distribution'); const h = new Float64Array(256).fill(1 / 256); this.cloudDist = detailDistribution(h); } }
    if (this.env) this.sky.setEnv(this.envEff || this.env);
    if (this.envState && this.physLight) this._envSetup(this.envState);
    // apron floodlight field from the masts (before any material is compiled: the light node samples it). engine.flood
    // exists before init() resolves (js/three/engine.js constructor); this runs inside the app's synchronous start-up.
    const masts = (world.details && world.details.masts) || [];
    const t0 = performance.now(); const f = floodField(masts, { res: this.tier === 'low' ? 5 : 3 });
    if (f) { this.engine.flood.setField(f); this.floodScale = f.scale; tlog('flood field ' + f.w + 'x' + f.h + 'x' + f.d + ' in ' + (performance.now() - t0).toFixed(0) + ' ms (' + JSON.stringify(f.stats) + ')'); }
    this.masts = masts.map(([x, z]) => { const [ax, az] = mastAim(x, z); return { x, z, ax, az }; }); this.spotSel = [];
    // floodlight-mast lamp sprites (js/live/items.js: i 900, s 0.5 = ~2,970 cd on the aim axis, NV; lobe (0,-1,0.3)^2):
    // a side / back floor of MAST_LOBE_FLOOR of the on-axis intensity for the lit housing and lens glare (review
    // look1-5: the lobe was 0 for 58-73 % of the lamps from the approach, the gate and the bay, while SFO photos from the
    // bay at dusk show every mast's lamps as bright points (refs/cache/env_ref/sfo_dusk_lights_fog_2016_960.jpg, CC BY
    // 4.0, obs): saturated points at EV100 2.66 from ~6 km mean >= ~70 cd toward the bay (M, rough); the value I / NV, Q7)
    for (const sp of world.mastSprites || []) sp.floor = MAST_LOBE_FLOOR;
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
    for (const k of ['sat', 'contrast', 'lookSat', 'lookSatLo', 'vignette']) if (qs.get(k) != null) { E.grade[k].value = +qs.get(k); (this.gradeLock = this.gradeLock || {})[k] = true; }
    if (qs.get('cas') != null) this.casLock = +qs.get('cas');
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
  // Also the mean albedo of the airfield's CONCRETE (the bake weighted by the aux bake's concrete mask, 64 x 64 cells):
  // what a terminal curtain wall mirrors (close-out round 2: the pane reflected the warm whole-field mean), kept apart
  // from the IBL ground so no other object's ambient changes (objects.js kG).
  _groundAlbedo() {
    const R = this.engine.renderer, B = this.bakes;
    const read = (n, colorNode, premult = false) => {
      const rt = new THREE.RenderTarget(n, n, { depthBuffer: false, generateMipmaps: false });
      const m = new THREE.NodeMaterial(); m.blending = THREE.NoBlending; m.depthTest = m.depthWrite = false; m.colorNode = colorNode;
      const q = new THREE.QuadMesh(m); const prev = R.getRenderTarget(); R.setRenderTarget(rt); q.render(R); R.setRenderTarget(prev);
      return R.readRenderTargetPixelsAsync(rt, 0, 0, n, n).then((px) => { // weighted mean of rgb by alpha (the bake targets are linear: NoColorSpace, UnsignedByte)
        let r = 0, g = 0, b = 0, w = 0; const s = px.BYTES_PER_ELEMENT === 1 ? 1 / 255 : 1;
        const k = premult ? 0 : 1; // premultiplied rgb (rgb x a in the target): sum rgb / sum a
        for (let i = 0; i < px.length; i += 4) { const a = px[i + 3] * s, f = k ? a : 1; r += px[i] * s * f; g += px[i + 1] * s * f; b += px[i + 2] * s * f; w += a; }
        return w > 0 ? [r / w, g / w, b / w] : null;
      }).finally(() => { rt.dispose(); m.dispose(); });
    };
    const uvN = TSL.uv(); const lv = (w) => Math.max(0, Math.log2(w / 64));
    // concrete mean (close-out round 3, env-7): point samples of the FULL-resolution bakes (level 0) on a 1024² grid,
    // premultiplied in the shader (rgb x mask, mask) and summed as sum(rgb x m) / sum(m): unbiased. Before: 64 x 64 cells
    // (~73 x 50 m) of the mip-averaged colour weighted by the mip-averaged mask, exact only for uniform cells, so the
    // mixed cells along every apron edge added grass and sand (apronAlb B/R 0.84 vs the bake's PCC 0.91)
    const c0 = TSL.texture(B.aux.texture, uvN).level(0.0).b; // concrete mask (ground.js auxMaterial)
    this._albP = Promise.all([
      read(16, TSL.texture(B.apt.texture, uvN).level(8.0)),
      read(1024, TSL.vec4(TSL.texture(B.apt.texture, uvN).level(0.0).rgb.mul(c0), c0), true),
    ]).then(([all, cm]) => {
      if (all) { this.groundAlb = all; this.envDirty = true; this.engine.flood.bounce.set(...all); GBOUNCE.aIBL.value.set(...all); GBOUNCE.on.value = this.qsGB === false ? 0 : 1; tlog('IBL ground albedo ' + all.map(v => v.toFixed(3)).join(',')); }
      if (cm) { this.apronAlb = cm; tlog('concrete mean albedo ' + cm.map(v => v.toFixed(3)).join(',')); }
      this._kG();
    }).catch(e => console.warn('ground albedo readback', e));
  }
  _kG() { const a = this.apronAlb, g = this.groundAlb; if (a && g) this.kG.value.set(...a.map((v, k) => g[k] > 1e-3 ? v / g[k] : 1)); else this.kG.value.set(1, 1, 1); }
  // QA (close-out round 2 A/B): IBL ground albedo override (null = the airfield bake's mean again); every object's light
  // from below and the floodlight bounce follow, the curtain walls keep reflecting the concrete (kG)
  setIBLGround(alb) {
    if (!this._groundAlbBake) this._groundAlbBake = this.groundAlb;
    this.groundAlb = alb || this._groundAlbBake; this.engine.flood.bounce.set(...this.groundAlb); GBOUNCE.aIBL.value.set(...this.groundAlb); this._kG();
    this.light._albScaled = false; this.envDirty = true;
  }
  // scene objects, built once the world, the sky and the first bake exist
  _buildStatic() {
    const E = this.engine, S = E.scene, W = this.world, Q = this.Q;
    const sky = this.sky;
    sky.setFlood(E.flood); // the floodlight field for the fog in-scatter (review look1-1; set in attachWorld before this)
    S.backgroundNode = sky.backgroundNode(); S.fogNode = sky.fogNode();
    // sun radiance x cloud shadow (the old shaders' getShadow() * cloudShadow(wp)); three multiplies the CSM term in
    this.sunRad = uniform(new THREE.Vector3(1, 1, 1));
    E.sun.colorNode = this.sunRad.mul(sky.cloudShadow(TSL.positionWorld));
    // SSR of objects in wet pavement (js/three/ssr.js, close-out round 3, env-2): tiers with a depth pre-pass (high / ultra /
    // medium) and TRAA (its history = the previous resolved frame); ?ssr=0 turns it off (A/B)
    const hist = E.traaNode && E.traaNode._historyRenderTarget && E.traaNode._historyRenderTarget.texture;
    this.ssrOn = uniform(0); this.ssrPrevVP = uniform(new THREE.Matrix4()); this._ssrOk = 0;
    this.ssrAO = uniform(1);   // QA A/B (close-out round 5): 0 = subtract the unoccluded sky reflection as before (R.ssrAO.value)
    const ssr = Q.ao === 'prepass' && hist && E.depthNode && new URLSearchParams(location.search).get('ssr') !== '0' ? makeSSR({ depth: E.depthNode, history: hist, prevVP: this.ssrPrevVP, on: this.ssrOn, sky, ao: E.aoScreen || null, aoOn: this.ssrAO }) : null;
    this.ssrBuilt = !!ssr;
    this.gMat = groundMaterial(W, this.bakes, sky, Q, { ssr }); this.wMat = waterMaterial(W, this.bakes, sky);
    // the light objects get from below: the local airfield bake instead of the IBL's whole-field mean (tsl/ground_bounce.js,
    // close-out round 3, env-10); on once the IBL ground albedo is read back (_groundAlbedo)
    setGroundRef({ tex: this.bakes.apt.texture, AR: W.groundU.uAptRect, Vw: W.groundU.uVw, Uw: W.groundU.uUw, res: this.bakes.res, G: sky.u.ground });
    const common = { noiseTex: this.noiseTex, night: this.nightE, time: this.time, interiorE: this.interiorE, sunDir: E.sunDirU, shadeK: this.shadeK, kG: this.kG, envGround: sky.u.ground, glassAB: this.glassAB }; // objects.js night emissions: nightE; envGround: curtain-wall local reflection
    this.objMat = objectMaterial(common); this.vehMat = objectMaterial({ ...common, instanced: true });
    this.carMat = objectMaterial({ ...common, instanced: true, carFade: true }); // garage-roof cars: distance fade to their mean colour
    this.markMat = markingMaterial({ noiseTex: this.noiseTex, pxScale: this.pxScale, reversed: E.reversed });
    this.sprites = new Sprites(24000, { depthNode: E.depthNode, expo: E.expo, night: this.night, slopeTaps: this.tier === 'low' ? 2 : 4, aurTail: this.tier !== 'low' }); E.fxScene.add(this.sprites.mesh);   // aurTail: the phone tier draws no broad aureole lobe (fill rate; env-3)
    this.acr = new AircraftRenderer(S, { noiseTex: this.noiseTex, Q: this.Q, renderer: E.renderer });
    this.staticGroup = new THREE.Group(); this.staticGroup.name = 'world'; S.add(this.staticGroup);
    this.built = true; tlog('static scene built');
    this.b3d = new Buildings3D(this); this.b3d.start(); // loads after the static scene; first-pass buildings until then
    // rain / drizzle particles in the light-sprite pass (js/three/rain.js) and the low cloud-layer planes (environment step 3)
    this.rain = new Rain(60000, { depthNode: E.depthNode, colorNode: E.sceneColorNode || null, groundY: GROUND_Y, floodField: (p) => sky.floodField(p) }); E.fxScene.add(this.rain.mesh); // floodlit drops (look1-4); "over" against the scene colour (look2-7)
    this._cloudPlanes();
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
        const geo = geometryOf(it.mesh);
        // curtain-wall panes: wall top / bottom and frame finish per vertex (objects.js glassWallAttrs; env-7 / env-8)
        if (!this._lightFrameRings) this._lightFrameRings = (BUILDINGS.parts || []).filter(q => /^Boarding Area G( walkway)?$/.test(q.name)).flatMap(q => q.rings);
        glassWallAttrs(geo, GROUND_Y, this._lightFrameRings);
        const m = new THREE.Mesh(geo, this.objMat); m.castShadow = !!it.castShadow; m.receiveShadow = true;
        m.matrixAutoUpdate = false; if (it.model) { m.matrix.fromArray(it.model); } G.add(m);
        if (it.b3d || it.b3dRest) { m.userData.b3d = it.b3d; m.userData.b3dRest = it.b3dRest; if (it.b3dRest) m.visible = false; } // js/three/buildings3d.js swaps them
        // the floodlight masts (js/live/items.js buildMasts: its first vertex is the first mast's base) on their own layer:
        // the floodlight spot lights sit inside the mast heads and must not see them (js/three/flood.js MastSpot)
        const P = it.mesh.data && it.mesh.data.pos, m0 = this.masts && this.masts[0];
        if (P && m0 && Math.hypot(P[0] - m0.x, P[2] - m0.z) < 1.5 && Math.abs(P[1] - GROUND_Y) < 1.0) m.layers.set(MAST_LAYER);
        // cars on the garage roofs as instanced boxes (review round 2: a mosaic of flat squares read as confetti)
        const cars = garageCars(it.mesh.data, it.model, this.carMat, this.tier); if (cars) { if (it.b3d) cars.userData.b3d = it.b3d; G.add(cars); }
      } else if (p === 'mark') {
        const m = new THREE.Mesh(geometryOf(it.mesh), this.markMat); m.frustumCulled = false; m.receiveShadow = true; m.renderOrder = 1; m.matrixAutoUpdate = false; G.add(m);
      } else if (p === 'sign') this.pendingSigns.push(it);
      else if (p === 'cloud') continue; // the EnvState cloud layers are drawn by _cloudPlanes and the sky shader (environment step 3); the app's single slab items are not used
      // 'decal' (stand centrelines) is off by default in js/live/world.js (standMarkings) and not ported
    }
    // cloud layers removed by the app (setClouds rebuilds them when the METAR changes)
    if (this.clouds.size) { const live = new Set(W.items); for (const [it, m] of this.clouds) if (!live.has(it)) { this.engine.scene.remove(m); m.material.dispose(); this.clouds.delete(it); } }
    // airfield signs: MSDF text once the font is there; the canvas atlas (as live.html draws them) if it failed
    if (this.pendingSigns.length && (this._signMats() || this.fontFailed)) {
      if (!this.worldLookup) this.worldLookup = faceIndex(worldSignAtlasMap(W.details || {}));
      if (this.signMats) this._releaseAtlases(this.pendingSigns);
      for (const it of this.pendingSigns.splice(0)) {
        let g;
        if (this.signMats) { const d = it.mesh.data; const sb = new SignBuilder(this.font); sb.addSignArrays({ pos: d.pos, nrm: d.nrm, uv: d.uv, ext: d.extra }, this.worldLookup); g = signMeshes(sb, this.signMats, 'signs'); }
        else g = this._atlasSign(it);
        if (!g) continue; if (!it.castShadow) g.traverse(o => { o.castShadow = false; }); G.add(g);
      }
    }
  }
  // the canvas sign atlases are only the fallback when the MSDF font fails (review round 2: three 2048-wide atlases were
  // uploaded and kept although nothing sampled them): released as soon as the MSDF materials exist
  _releaseAtlases(items) {
    this._relAt = this._relAt || new Set();
    const rel = (r) => { if (r && !this._relAt.has(r)) { this._relAt.add(r); disposeRecord(r); } };
    for (const it of items || []) { const u = typeof it.uniforms === 'function' ? null : it.uniforms; if (u) rel(u.uAtlas || u.uTex); }
    const gs = this.sceneShim && this.sceneShim.gateSys; if (gs && gs.atlas && this.bridges && this.bridges.signMats) rel(gs.atlas.tex);
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
      if (!this.bridges.signMats && this._signMats()) { this.bridges.setSignFont(this.font, this.signMats); this._releaseAtlases(null); }
      else if (!this.bridges.signMats && this.fontFailed && !this.bridges.atlasFallback) this.bridges.useAtlasFallback();
      this.bridges.update(Date.now()); sc.gateSys.sprites = this.bridges.sprites;
    }
    this.acr.sync(sc.aircraft, camPos);
    if (this.b3d) this.b3d.update(camPos);
  }
  // ------------------------------------------------------------ render (fr = compat Scene.frame result)
  render(fr, cam, t, post = {}) {
    const E = this.engine;
    const C = this._camInfo(cam);
    if (!this.ready || !this.built || !this.compiled) { this._progress(); return C; }
    const R = E.renderer, S = E.scene, L = this.light, st = this.envState && this.physLight ? this.envState : null;
    // environment: GPU sky, sun, IBL (after the app's night-floor adjustment of R.light)
    if (this.envDirty) {
      this.envDirty = false;
      if (st) {
        // physical light (environment step 3): the app's lamp-unit night floor is replaced by the EnvState night sky
        for (const k of ['sunColor', 'skyUp', 'skyHorizon', 'ground']) L[k] = this.physLight[k].slice();
        L._lampScaled = true; L._albScaled = false; L._ground0 = null;
      }
      // the app's night floor (moon / city glow, js/live/app.js applyEnv: max(sky, floor)) is in lamp units: keep the
      // physical sky and add LAMP_M x the part the floor raised
      const B0 = this.baseLight;
      if (B0 && !L._lampScaled) { for (const k of ['skyUp', 'skyHorizon', 'ground']) L[k] = L[k].map((v, i) => B0[k][i] + LAMP_M * Math.max(0, v - B0[k][i])); L._lampScaled = true; }
      if (this.groundAlb && !L._albScaled) { const a = this.groundAlb; if (!L._ground0) L._ground0 = L.ground.slice(); L.ground = L._ground0.map((g, k) => g / 0.16 * a[k]); L._albScaled = true; } // Sky.lightFor: ground = E x 0.16 / pi
      if (!st) { const bu = this.baseLight ? this.baseLight.skyUp : L.skyUp; L.skyFloor = L.skyUp.map((v, k) => Math.max(0, v - bu[k])); }
      this.sky.applyLight(L);
      this.sky.renderSky(R);
      this.sky.updateEnvironment(R, S);
      { const sy = Math.max(0, L.sunDir[1]); const k = [0, 1, 2].map(c => { const sk = Math.PI * L.skyUp[c], su = L.sunColor[c] * sy; return sk + su > 1e-12 ? sk / (sk + su) : 1; }); this.shadeK.value.set(k[0], k[1], k[2]); }
    }
    const nightF = this.extraCommon.uNight || 0;
    // apron floods (field, spots, the exposure key): the EnvState flood photocell (E < 32.3 lx, spec §4.2; review
    // truth1-12: they followed the app's sun-elevation ramp nightF, unsourced, while the HUD showed the photocell) with a
    // 0.5 s lamp ramp (I); without an EnvState the old ramp. (Window / city / sign lamps keep nightF: engine track.)
    { const on = st && st.photocell ? (st.photocell.floodsOn ? 1 : 0) : nightF; const now = performance.now();
      const dtw = this._fT ? Math.min(1, (now - this._fT) / 1000) : 1; this._fT = now;
      this.floodK = this.floodK == null ? on : this.floodK + (on - this.floodK) * Math.min(1, dtw / 0.5); }
    const floodK = this.floodK;
    // ---- directional light: the Sun; at night the Moon, or a lightning flash (environment step 3/4; no shadows)
    let ldir = L.sunDir, lcol = L.beamT != null && L.beamT < 1 ? L.sunColor.map(c => c * L.beamT) : L.sunColor, lname = 'sun';
    let flash = { level: 0, dir: [0, 1, 0], lux: 0 };
    if (st) {
      if (st.lightning && st.lightning.perMin > 0) {
        // (QA: R.qaForceFlash = true evaluates the next scheduled flash 10 ms into its first stroke: on a software
        // rasteriser the app's simulated time advances <= 0.1 s per frame, so a flash is rarely hit by chance)
        let tl = t; if (this.qaForceFlash) { const nx = lightningFlashes(st.lightning, t, t + 600, 1)[0]; if (nx) tl = nx.t + 0.01; }
        const fl = flashLevel(lightningFlashes(st.lightning, tl - 0.5, tl + 0.01, 1), tl);
        if (fl.flash && fl.level > 0.01) {
          const base = (this.layers.find(l => l.cover === 'BKN' || l.cover === 'OVC') || { baseY: 1500 }).baseY;
          const el = Math.atan2(base - cam.pos[1], Math.max(fl.flash.dist, 300)) / DEGR;
          flash = { level: fl.level, dir: directionWorld(fl.flash.az, el), lux: Math.min(20, Math.max(0.05, 3 * Math.pow(3000 / Math.max(fl.flash.dist, 500), 2))), az: fl.flash.az, dist: fl.flash.dist };
        }
      }
      if (st.sun.el < 0 && flash.level > 0.01) { ldir = flash.dir; lcol = FLASH_COL.map(c => c * flash.lux * flash.level / LUX_PER_UNIT); lname = 'flash'; }
      else if (st.sun.el < -1 && st.moon.el > 0) {
        // clear-sky normal illuminance: the cloud layers' coverage maps cut it; the fog / VV obscuration by fogBeamT
        const En = st.natural.moon * st.natural.D / Math.max(Math.sin(st.moon.el * DEGR), 0.05) / LUX_PER_UNIT * fogBeamT(this.slabs || renderSlabs(st), st.moon.el);
        ldir = st.moon.dir; lcol = MOON_COL.map(c => c * En); lname = 'moon';
      }
      // cloud glow at the flash: FLASH_GLOW_CDM2 x (5 km / distance)^2, 5-500 cd/m2 at the peak of sky.cloudLayers'
      // lobe (3.4 x flashCol). The illuminance at the airport alone (E/pi, ~0.2 cd/m2 at 6.6 km) left the flash invisible at
      // the night exposure (run 3: sky +0.15 display levels); brightness NV (spec §4.6), I, QA-tuned
      const glow = flash.level > 0 ? Math.min(500, Math.max(5, FLASH_GLOW_CDM2 * Math.pow(5000 / Math.max(flash.dist || 5000, 500), 2))) : 0;
      this.sky.setFlash(flash.dir, flash.level, FLASH_COL.map(c => c * glow / 3.4 / LUX_PER_UNIT));
      // wet surfaces: the state machine advances with the data clock (js/env/atmo/weather_fx.js wetStep)
      if (st.tEnv !== this._wetT) { this.wet = wetStep(this.wet, st); this._wetT = st.tEnv; const U = this.sky.u; U.wetFilm.value = this.wet.film; U.wetPore.value = this.wet.pore; U.puddle.value = this.wet.puddle; }
    }
    this.lightName = lname; this.flash = flash;
    // ---- exposure (spec §8): auto-exposure from the metered frame (EV100, clamp, compensation), else the keyed
    // exposure of review rounds 1-3 (?ae=0; also until the first metering)
    const el = Math.asin(Math.max(-1, Math.min(1, L.sunDir[1]))) * 180 / Math.PI; const dark = sstep(2, -10, el);
    const pe = post.exposure ?? 0.45; const B = this.baseLight || L;
    const eAmb = lum(B.sunColor) * Math.max(0, B.sunDir[1]) + Math.PI * lum(B.skyUp);
    const eKey = eAmb + E_STAND * LAMP_M * floodK;
    const expoKey = KEY_NIGHT * Math.PI / (RHO_CONC * Math.max(eKey, 1e-7));
    const expoDay = dark < 0.999 ? Math.max(0, (pe - APP_NIGHT_EXPO * dark) / (1 - dark)) * DAY_GAIN : 0;
    const expoKeyed = Math.max(expoDay, expoKey); this.eKey = eKey;
    let expoTotal = expoKeyed, evUsed = null;
    if (st && this.fixedEV != null) { evUsed = this.fixedEV; expoTotal = exposureForEV(evUsed); }
    // (close-out round 3, env-4 / env-16: by day the reflected reading stays within ±1 EV of the incident reading of the
    // natural illuminance, exposure.js incidentBound; the frame's metered value is kept in envInfo().metered)
    else if (st && this.aeMode === 'auto' && this.ae.Lcd != null) { const evR = ev100FromLuminance(this.ae.Lcd) - METER_BIAS; this.evReflected = evR; evUsed = clampEV(incidentBound(evR, st.exposure && st.exposure.ev100Target, st.sun.elTrue), st.sun.elTrue); expoTotal = exposureForEV(evUsed); }
    expoTotal *= this.exposureScale; this.evUsed = evUsed; this.expoTotal = expoTotal; this.expoKeyed = expoKeyed;
    // ---- pre-exposure: every emitter x pre, the post exposure = total / pre
    const pre = this.pinPre != null ? this.pinPre : preExposure(this.pre, expoTotal);
    if (pre !== this.pre) { this.pre = pre; this.sky.setPre(pre); this.sky.setEnv(this.envEff || this.env); this.envDirty = true; }
    E.expo.value = expoTotal / pre;
    S.environmentIntensity = pre / (this.sky.preEnv || pre);
    E.setSun(ldir, lcol); if (lname !== 'sun') E.sun.castShadow = false;
    this.sky.u.lightDir.value.set(...ldir);
    this.sunRad.value.set(lcol[0] * pre, lcol[1] * pre, lcol[2] * pre);
    const lampKraw = Math.pow(LAMP_M, nightF);
    this.time.value = t; this.night.value = nightF; this.nightE.value = nightF * LAMP_M * pre; lampK.value = lampKraw * pre;
    E.flood.intensity = floodK * LAMP_M * pre; // floodlights: the flood photocell (above)
    // floodlight in-scatter in the fog (sky.floodScatter; review look1-1): on while the floods are and the lowest slab is
    // denser than clean air (σ > 1e-4 m⁻¹: below that the glow is < 1 % of the lit apron's luminance, M)
    { const s0 = this.slabs && this.slabs[0] ? this.slabs[0].sigma : 0; this.sky.u.floodI.value = floodK * LAMP_M * pre; this.sky.u.floodFog.value = floodK > 0 && s0 > 1e-4 ? s0 : 0; }
    this._floodSpots(cam, floodK * LAMP_M * pre);
    const wu = this.world.waterU; if (this.wMat && wu) { const u = this.wMat.userData; if (wu.uWind) u.uWind.value.set(wu.uWind[0], wu.uWind[1]); if (wu.uWaveAmp != null) u.uAmp.value = wu.uWaveAmp; }
    // SSR (env-2): the previous frame's un-jittered view-projection (TRAA cleared its view offset after that frame), and the
    // history counted valid from the 3rd frame after a camera cut / resize; only while the pavement is wet
    if (this.ssrBuilt) {
      const C3 = E.camera; this.ssrPrevVP.value.multiplyMatrices(C3.projectionMatrix, C3.matrixWorldInverse);
      const p = cam.pos, q = this._ssrCam, cut = !q || Math.hypot(p[0] - q[0], p[1] - q[1], p[2] - q[2]) > 30 || this._ssrW !== this.W || this._ssrH !== this.H;
      this._ssrCam = p.slice(); this._ssrW = this.W; this._ssrH = this.H; this._ssrOk = cut ? 0 : this._ssrOk + 1;
      const wetR = this.wet && st ? Math.max(this.wet.film, this.wet.puddle) : 0;
      this.ssrOn.value = this.ssrForce != null ? this.ssrForce : wetR > 0.05 && this._ssrOk >= 2 ? 1 : 0;   // (QA A/B: R.ssrForce 0 / 1)
    }
    E.setCamera(cam, this.W, this.H);
    this.pxScale.value = 2 * Math.tan(cam.fov / 2) / Math.max(1, this.H);
    // camera cut -> the meter snaps (no adaptation across a cut)
    { const p = cam.pos, q = this._lastCamPos; if (!q || Math.hypot(p[0] - q[0], p[1] - q[1], p[2] - q[2]) > 30) this._meterSnap = true; this._lastCamPos = p.slice(); }
    if (this.cloudCentre) this.cloudCentre.value.set(cam.pos[0], cam.pos[2]);
    // only the cloud-plane side the camera can see is drawn (review look1-12: the hidden side rasterised full-screen at
    // opacity 0): the base plane from below, the top plane from above
    if (this.cloudPlanes) for (const m of this.cloudPlanes) { const l = this.layers[m.userData.k]; m.visible = !!(l && l.slab && (m.userData.top ? l.thickness > 0 && cam.pos[1] > l.baseY + l.thickness : cam.pos[1] < l.baseY)); }
    // rain / drizzle (js/three/rain.js; parameters js/env/atmo/weather_fx.js rainParams)
    if (this.rain) {
      let n = 0;
      if (st && st.precip) {
        const w = st.wind || {}; const fr = (w.fromTrue ?? 0) * DEGR, sp = w.speed || 0;
        const P = rainParams(st.precip, this.tier, [-Math.sin(fr) * sp, Math.cos(fr) * sp]);
        const deck = this.layers.find(l => l.cover === 'BKN' || l.cover === 'OVC'); const top = deck ? deck.baseY : 1e6;
        // drop radiance: mean of its surroundings (rain.js header; review look2-7), coverage RAIN_K per 1-px streak
        const col = L.skyUp.map((v, k) => (0.6 * v + 0.4 * L.ground[k]) * pre);
        const fc = FLOOD_COLOR.map(c => c * floodK * LAMP_M * pre / Math.PI);   // drops under the floods (rain.js floodC)
        n = this.rain.update(P, cam, t, col, top, 2 * Math.tan(cam.fov / 2) / Math.max(1, this.H), P && P.showery ? showerFactor(t) : 1, fc, RAIN_K);
      } else this.rain.update(null);
      this.rainCount = n;
    }
    // light sprites
    // aircraft position lights (the first fr.nAc records are aircraft lights, compat/scene.js) keep their physical
    // intensity by day (lights.js fixedK / isPositionLight; close-out round 2, engine-v3)
    const sp = this.sprites; sp.fixedK = LAMP_M / ((0.5 + 0.5 * nightF) * lampKraw);
    // records with phys: true (environment step 2: airfield fixtures js/env/lighting/airfield.js, aircraft lights
    // js/env/aircraft_lights.js) carry physical intensities (cd x visibility x display gain, in lamp units at the night
    // calibration) and are drawn at that calibration day and night as well
    // records without physical photometry (floodlight-mast lamps, bridge / stand lights, js/live/app.js mastSprites and
    // gateSys.sprites) get the fog transmittance camera -> light of the slabs (environment step 3; the phys records
    // already carry it through their Allard factor; markers are UI and stay visible). Found in the predawn-fog render:
    // the mast lamps 1-2 km away shone through M1/4SM fog. Always applied (review truth1-4: it was gated on the surface
    // σ > 2e-4, so under a 10SM BKN010 deck the mast lamps shone through the cloud at full brightness from above)
    const fogS = st && this.slabs && this.slabs.length ? this.slabs : null, cp = cam.pos;
    // fog aureoles (review look1-1): the phys records carry theirs (js/env/lighting/airfield.js, js/env/aircraft_lights.js:
    // photometry.js aureole); the non-photometric lamps get one from the same transmittance here, while the lowest slab is
    // fog / mist (σ > 1e-4). Any aureole whose peak would display below ~1/1000 of white is dropped (fill rate, I).
    const fogAur = fogS && fogS[0].sigma > 1e-4, expD = expoTotal / pre; let nAur = 0;
    const aurVisible = (au, ar, ss, p) => { const d2 = (p[0] - cp[0]) ** 2 + (p[1] - cp[1]) ** 2 + (p[2] - cp[2]) ** 2; return au * LAMP_M * pre * 0.408 * ss * ss / Math.max(d2, 1) / (Math.PI * ar * ar) * expD > 1e-3; };
    sp.begin(); const SL = fr && fr.sprites || [], nAc = fr && fr.nAc || 0;
    for (let k = 0; k < SL.length; k++) {
      const s = SL[k]; const phys = s.phys === true || (k < nAc && Sprites.isPositionLight(s));
      const fogged = fogS && !phys && !s.marker && !(s.s >= 0.6 && !s.dir); const T = fogged ? fogTransmittance(fogS, cp, s.p) : 1;
      let au = phys ? (s.aur || 0) : 0, ar = phys ? (s.aurR || 0) : 0;
      if (fogged && fogAur) { const A = aureole(T); if (A) { au = s.i * A.f; ar = A.theta; } }
      if (au > 0 && !aurVisible(au, ar, s.s || 0.3, s.p)) au = 0;
      // phone tier (review look2-10): aureole radius <= AUR_LOW_MAX_DEG and at most AUR_LOW_MAX_N of them (fill rate, I)
      if (au > 0 && this.tier === 'low') { if (nAur >= AUR_LOW_MAX_N) au = 0; else ar = Math.min(ar, AUR_LOW_MAX_DEG * DEGR); }
      if (au > 0) nAur++;
      sp.put(s, phys, T, au, ar);
    }
    // wet pavement mirrors the lamps (review look1-3: puddles were dark holes under the floods; no SSR / planar
    // reflection here): every light more than 1 m above the ground within REFL_MAX_M gets its mirror image, drawn where the
    // ray to the image meets the ground (so the scene depth test hides it behind objects), at the image's distance (size
    // and energy), Fresnel of water (Schlick, F0 0.02) at that incidence x the wet state (film / puddle) x REFL_K, spread
    // by the film roughness (1 + 2 film, energy kept), the lobe mirrored. Approximations (I): flat ground at GROUND_Y,
    // also where the hit is not paved; the record's beam toward the camera stands for the one toward the image.
    let nRefl = 0;
    const wetR = this.wet && st ? Math.max(this.wet.film, this.wet.puddle) : 0;
    if (wetR > 0.2 && cp[1] - GROUND_Y > 0.3) {
      const G = GROUND_Y, pool = this._refl || (this._refl = []);
      for (let k = 0; k < SL.length && sp.n < sp.max; k++) {
        const s = SL[k]; if (s.marker || (s.s >= 0.6 && !s.dir) || !(s.i > 0)) continue;
        const h = s.p[1] - G; if (h < 1) continue;
        const dx = s.p[0] - cp[0], dz = s.p[2] - cp[2]; if (dx * dx + dz * dz > REFL_MAX_M * REFL_MAX_M) continue;
        const Py = G - h, t = (cp[1] - G) / (cp[1] - Py);
        const hit = [cp[0] + t * dx, G + 0.05, cp[2] + t * dz];
        const dH = Math.hypot(hit[0] - cp[0], hit[1] - cp[1], hit[2] - cp[2]), dV = Math.hypot(dx, Py - cp[1], dz);
        const cosI = Math.min(1, (cp[1] - G) / Math.max(dH, 1e-3)); const F = 0.02 + 0.98 * Math.pow(1 - cosI, 5);
        const spread = 1 + 2 * this.wet.film; const R = F * wetR * REFL_K;
        const phys = s.phys === true || (k < nAc && Sprites.isPositionLight(s));
        const Tv = fogS && !phys ? fogTransmittance(fogS, cp, [s.p[0], Py, s.p[2]]) : 1;
        let o = pool[nRefl]; if (!o) o = pool[nRefl] = { p: [0, 0, 0], c: null, i: 0, s: 0.3, dir: null, k: 4, floor: 0, marker: false };
        o.p[0] = hit[0]; o.p[1] = hit[1]; o.p[2] = hit[2]; o.c = s.c; o.s = (s.s || 0.3) * dH / Math.max(dV, 1e-3) * spread;
        o.i = s.i * R / (spread * spread); o.dir = s.dir ? [s.dir[0], -s.dir[1], s.dir[2]] : null; o.k = s.k; o.floor = s.floor || 0;
        if (o.i * Tv > 1e-6) { sp.put(o, phys, Tv); nRefl++; }
      }
    }
    sp.end(E.camera, this.H); this.nAur = nAur; this.nRefl = nRefl;
    // terminal halls (objects.js id 1): the daylight factor applies to the sky's diffuse illuminance (CIE: overcast sky,
    // direct sun excluded; close-out round 2: it was applied to sun + sky, 3.5 klx in the hall instead of ~1 klx)
    const eSky = Math.PI * lum(B.skyUp);
    this.interiorE.value = (HALL_DF * (this.glassABOld ? eAmb : eSky) + (1 - nightF) * HALL_LUX / LUX_PER_UNIT) * pre;
    const G = E.grade, lock = this.gradeLock || {};
    if (!lock.sat) G.sat.value = (post.sat ?? 1.1) / 1.1; // the app's 1.1 was tuned on top of ACES: 1.0 here; user changes stay relative
    if (!lock.vignette) G.vignette.value = post.vignette ?? 0.18;
    G.grain.value = post.grain ?? 0; G.time.value = t;
    if (E.bloomNode) E.bloomNode.strength.value = 0.035 * ((post.bloom ?? 0.012) / 0.012);
    if (this.dbgNoCast) S.traverse(o => { if (o.isMesh) o.castShadow = false; });
    const tr0 = performance.now(); E.render(); this.frames++; if (this.frames === 1) this._progress(true);
    if (this.frames <= 3 || this.frames % 50 === 0) console.log('[r3] frame ' + this.frames + ' ' + (performance.now() - tr0).toFixed(0) + ' ms (t=' + ((performance.now() - T0) / 1000).toFixed(1) + ' s)');
    this._meterRead();
    return C;
  }
  // auto-exposure metering: asynchronous readback of the 64 x 36 luminance target (js/three/engine.js meter), every 4th
  // frame (and at once after a cut); js/env/atmo/exposure.js meter (50th-98th percentile, centre-weighted) + adapt
  _meterRead() {
    const E = this.engine; if (!this.envState || !E.meter || this._meterBusy || this.aeMode !== 'auto') return;
    if (!this._meterSnap && this.frames % 4 !== 0) return;
    this._meterBusy = true; const preAt = this.pre, snap = this._meterSnap; this._meterSnap = false;
    const rt = E.meter.renderTarget; const w = rt.width, h = rt.height;
    E.renderer.readRenderTargetPixelsAsync(rt, 0, 0, w, h).then((px) => {
      const n = w * h, half = px instanceof Uint16Array, step = Math.max(1, Math.round(px.length / n));
      const f16 = (v) => half ? THREE.DataUtils.fromHalfFloat(v) : v;
      // the sky (G = 1) is left out when at least 10 % of the frame is geometry (engine.js meter; I)
      const Lu = new Float32Array(n), sky = new Uint8Array(n); let nGeo = 0;
      for (let i = 0; i < n; i++) { Lu[i] = Math.max(0, f16(px[i * step])) / preAt; sky[i] = step > 1 && f16(px[i * step + 1]) > 0.5 ? 1 : 0; if (!sky[i]) nGeo++; }
      const m = meter(Lu, w, h, nGeo >= 0.1 * n ? sky : null); m.skyFrac = 1 - nGeo / n; const now = performance.now();
      this.ae.Lcd = adapt(this.ae.Lcd, m.Lcd, (now - (this.ae.t || now)) / 1000, snap || this.ae.Lcd == null);
      this.ae.t = now; this.ae.metered = { ev100: +m.ev100.toFixed(2), Lcd: +m.Lcd.toPrecision(4), frame: this.frames, snap, skyFrac: +m.skyFrac.toFixed(3), n: m.n };
    }).catch((e) => { this._meterErr = String(e && e.message || e); }).finally(() => { this._meterBusy = false; });
  }
  // QA: environment step 3 state (exposure, pre-exposure, calibration, layers, slabs, Moon, rain, wetness, flash)
  envInfo() {
    const r = (v, n = 3) => v == null ? null : +Number(v).toPrecision(n);
    return { sunK: r(this.sunK), cal: this.cal ? { c171Lux: r(this.cal.c171Lux, 4), modelLux: r(this.cal.modelLux, 4) } : null,
      ae: this.aeMode, metered: this.ae.metered, evReflected: r(this.evReflected, 4), evTarget: this.envState && this.envState.exposure ? r(this.envState.exposure.ev100Target, 4) : null, evUsed: r(this.evUsed, 4), evAdapted: this.ae.Lcd ? r(ev100FromLuminance(this.ae.Lcd), 4) : null, expoTotal: r(this.expoTotal, 4), expoKeyed: r(this.expoKeyed, 4), evKeyed: this.expoKeyed ? r(evForExposure(this.expoKeyed), 4) : null,
      pre: this.pre, postExpo: r(this.engine.expo.value, 4), envIntensity: r(this.engine.scene.environmentIntensity, 4), light: this.lightName, sunRad: this.sunRad ? this.sunRad.value.toArray().map(v => r(v)) : null,
      layers: this.layers.map(l => ({ cover: l.cover, baseFt: l.baseFt, own: r(l.own), thr: r(l.thr), slab: l.slab })), planes: this.cloudPlanes ? this.cloudPlanes.filter(m => m.visible).length : 0,
      slabs: (this.slabs || []).map(s => [s.kind, r(s.y0, 4), r(s.y1, 4), r(s.sigma)]), moonL: this.sky ? r(this.sky.u.moonL.value) : null, rain: this.rainCount || 0, rainParams: this.rain && this.rain.params ? { kind: this.rain.params.kind, count: this.rain.params.count, streak: r(this.rain.params.streak), v: r(this.rain.params.vFall) } : null,
      wet: this.wet ? { film: r(this.wet.film), pore: r(this.wet.pore), puddle: r(this.wet.puddle) } : null, ssr: this.ssrBuilt ? { on: this.ssrOn.value, okFrames: this._ssrOk } : null, flash: this.flash, aureoles: this.nAur || 0, reflections: this.nRefl || 0, floodK: this.floodK, meterErr: this._meterErr || null, cloudTexSum: this.cloudTexSum || null };
  }
  // floodlight spots: the masts that light the point the camera looks at most (horizontal irradiance there, the same
  // intensity distribution as the field), with hysteresis so the choice does not flip every frame
  _floodSpots(cam, on) {
    const E = this.engine, n = E.spots.length; if (!n || !this.masts || !this.masts.length) return;
    if (!(on > 0)) { E.setFloodSpots(this.spotSel, 0, this.floodScale || 1); return; }
    const p = cam.pos; const dir = cam.dir || [cam.target[0] - p[0], cam.target[1] - p[1], cam.target[2] - p[2]];
    let f = cam.target ? cam.target : null;
    if (!f) { const l = Math.hypot(...dir) || 1; const tg = dir[1] < -1e-3 ? Math.min(600, (p[1] - GROUND_Y) / (-dir[1] / l)) : 300; f = [p[0] + dir[0] / l * tg, GROUND_Y, p[2] + dir[2] / l * tg]; }
    const score = (m) => mastE(f[0], GROUND_Y + 2, f[2], m.x, m.z, m.ax, m.az)[1];
    const ranked = this.masts.map(m => [score(m), m]).filter(a => a[0] > 0).sort((a, b) => b[0] - a[0]).slice(0, n).map(a => a[1]);
    const sum = (L) => L.reduce((s, m) => s + (m ? score(m) : 0), 0);
    if (!this.spotSel.length || sum(ranked) > 1.3 * sum(this.spotSel)) this.spotSel = ranked;
    E.setFloodSpots(this.spotSel, on, this.floodScale || 1);
  }
  // progress overlay until the first frame is drawn (review round 2: the app removes its loading overlay when its own
  // start-up is done, while the first bake, the scene build and the program compile still take seconds on a phone and
  // minutes on a software rasteriser, and the canvas stayed black). Same look as the app's (#loading in live.css).
  _progress(done = false) {
    let o = this._pov;
    if (done) { if (o) { o.classList.add('done'); setTimeout(() => o.remove(), 700); this._pov = null; } this._povDone = true; return; }
    if (this._povDone || this.failed || document.getElementById('loading') && !this._pov) return; // the app's overlay is still up
    if (!o) { o = document.createElement('div'); o.id = 'loading'; o.innerHTML = '<div class="lbox"><div class="brand big"><b>SFO</b> Live 3D</div><div class="bar"><i></i></div><div class="msg"></div></div>'; (document.getElementById('app') || document.body).appendChild(o); this._pov = o; }
    const B = this.bakes; const tot = B ? (this._bakeTot = Math.max(this._bakeTot || 0, B.pending)) : 0;
    const fr = !this.built ? 0.1 + 0.6 * (tot ? 1 - B.pending / tot : 0) : !this.compiled ? 0.8 : 0.95;
    const msg = !this.built ? 'Baking the airfield textures…' : !this.compiled ? 'Compiling shaders…' : 'Drawing the first frame…';
    o.querySelector('.bar i').style.width = Math.round(fr * 100) + '%'; const m = o.querySelector('.msg'); if (m.textContent !== msg) m.textContent = msg;
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
      expo: +this.engine.expo.value.toFixed(3), eKeyLux: this.eKey != null ? Math.round(this.eKey * LUX_PER_UNIT * 10) / 10 : null, night: this.night.value, flood: this.engine.flood.stats || null, bakesPending: this.bakes ? this.bakes.pending : null, groundAlb: this.groundAlb || null, apronAlb: this.apronAlb || null, kG: this.kG.value.toArray().map(v => +v.toFixed(3)), shadeK: this.shadeK.value.toArray().map(v => +v.toFixed(3)), hallLux: Math.round(this.interiorE.value * LUX_PER_UNIT),
      canvas: this.canvas ? [this.canvas.width, this.canvas.height] : null, appCanvas: [this._appCW, this._appCH], step: this._step, spots: this.engine.spots.map(s => s.intensity > 0 ? [Math.round(s.position.x), Math.round(s.position.z), s.castShadow] : null),
      livMB: this.acr && this.acr.livCache ? +this.acr.livCache.bytes().toFixed(1) : null, env: this.envState ? this.envInfo() : null };
    if (this.acr) { out.aircraft = []; for (const [ac, e] of this.acr.entries) { if (out.aircraft.length >= 3) break; out.aircraft.push({ id: ac.id, type: ac.type, real: !!(e.real && e.real.visible), liv: ac.liv && ac.liv.name }); } }
    return out;
  }
  // for QA jobs: everything drawable is on screen (sign text may come from the fallback atlas if the font failed)
  isComplete() { return this.ready && this.built && !!this.compiled && !!this.bridges && !(this.bakes && this.bakes.pending) && !this.pendingSigns.length && (!!this.bridges.signMats || !!this.bridges.atlasFallback); }
}
