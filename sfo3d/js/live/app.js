// SFO Live 3D — application: boot, render loop, live feed / recorded snapshot, camera views, UI glue.
import { initGL, gl, Mesh } from '../gl.js';
import '../shaders/common.js';
import '../shaders/ground.js';
import { Renderer } from '../renderer.js';
import { bakeGround } from '../world/world.js';
import { polySDF } from '../world/terrain.js';
import * as GEO from '../geo.js';
const { ARP, GROUND_Y, worldToST, stToWorld } = GEO;
import { Scene } from '../scene.js';
import { TYPES } from '../aircraft/types.js';
import { CLOUD_VS, CLOUD_FS } from '../shaders/env.js';
// environment core (docs/research/environment_spec.md §3): data clock, METAR/TAF, ephemeris -> EnvState for both renderers
import { AppEnv } from '../env/app_env.js';
import { loadFixtures, provCounts, PROV_TINT } from '../env/lighting/fixtures.js';
// environment step 2: airfield-lighting fixtures + JO 7110.65 controller, aircraft lights (14 CFR 25 / AIM 4-3-24)
import { AirfieldLighting, DAY_GAIN } from '../env/lighting/airfield.js';
import { LIGHTING_SPEC, LIGHTING_FIXTURES } from '../../data/sfo_lighting.js';
import { aircraftLightStates, setLightViewer, setLightFrame, setLightEnv } from '../env/aircraft_lights.js';
import { LiveAircraft, TYPE_MODELS } from './aircraft.js';
import { footprint } from './gates.js';
import { MODEL_SOURCES } from './models.js';
import { buildLiveWorld, releaseAirportMap } from './world.js';
import { LiveGateSystem } from './gates.js';
import { buildLiveLights, buildPierGeometry, alsPlacement, buildMountGeometry } from './lights.js';
import { Traffic, category, hdgVec, RWY, phaseLabel, antOf, DELAY_MS } from './traffic.js';
import { GroundPhysics, buildingGrid, bridgeGrid } from './ground.js';
import { Feed, StreamFeed, Routes, fetchMetar, fetchTaf, fetchGates, parsePayload, SOURCES } from './feed.js';
import { runwayStats, statsLine, statsHtml, runwayQueue, runwayConfig } from './stats.js';
import { atcRoles, onFeed, roleChip, FEEDS, FEED_BY } from './atc.js';
import { CameraRig } from './controls.js';
import { UI } from './ui.js';

const DEG = Math.PI / 180, FT = 0.3048;
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const sstep = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
// physical runways for distance-remaining signs: start of end A, unit direction, length, sign side (outboard of the parallel pair)
function RUNWAY_SIGNS() {
  const out = [];
  for (const [a, side] of [['10L', 'left'], ['10R', 'right'], ['1L', 'left'], ['1R', 'right']]) {
    const R = RWY.find(r => r.name === a); const d = R.dir; const left = [d[1], -d[0]], right = [-d[1], d[0]];
    out.push({ pa: R.start, dir: d, len: R.len, side: side === 'left' ? left : right });
  }
  return out;
}
const QUALITY = {
  high: { name: 'high', msaa: 4, shadow: 3072, scaleMax: 1.0, dprMax: 2, maxPx: 3.2e6, terrainStep: 15, mapRes: 1.0, aptRes: 0.8, cityRes: 4096, lod: 1800, shadowDist: 1600 },
  medium: { name: 'medium', msaa: 4, shadow: 2048, scaleMax: 0.9, dprMax: 1.5, maxPx: 2.0e6, terrainStep: 20, mapRes: 1.25, aptRes: 1.0, cityRes: 4096, lod: 1300, shadowDist: 1100 },
  // stills / visual QA only (?quality=ultra): full-resolution, no dynamic scaling (see FIXED_RES), large shadow map
  ultra: { name: 'ultra', msaa: 4, shadow: 4096, scaleMax: 1.0, dprMax: 3, maxPx: 3.4e7, terrainStep: 10, mapRes: 0.75, aptRes: 0.6, cityRes: 8192, lod: 4000, shadowDist: 2500 },
  low: { name: 'low', msaa: 2, shadow: 2048, scaleMax: 0.8, dprMax: 2, maxPx: 1.1e6, terrainStep: 30, mapRes: 1.6, aptRes: 1.25, cityRes: 2048, lod: 1000, shadowDist: 700 },
};
const store = { get(k, d) { try { const v = localStorage.getItem('sfolive.' + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } }, set(k, v) { try { localStorage.setItem('sfolive.' + k, JSON.stringify(v)); } catch (e) { } } };
function pickQuality(pref) {
  const ua = navigator.userAgent || '';
  const mobile = /iPhone|iPad|iPod|Android/i.test(ua) || (matchMedia('(pointer: coarse)').matches && Math.min(screen.width, screen.height) < 900);
  const mem = navigator.deviceMemory || 8;
  const url = new URLSearchParams(location.search).get('quality');   // ?quality=high|medium|low|ultra overrides the setting
  const q = url && QUALITY[url] ? url : pref && pref !== 'auto' ? pref : mobile ? 'low' : mem <= 4 ? 'medium' : 'high';
  return QUALITY[q] || QUALITY.medium;
}
const nextFrame = () => new Promise(r => setTimeout(r, 0));
// ?fixedres=1 pins the render scale at the tier maximum (no dynamic resolution): for stills and QA renders on slow
// (software) GPUs, where the frame-time controller would otherwise drop the scale to 0.4 before the screenshot
const FIXED_RES = new URLSearchParams(location.search).has('fixedres');

// cfg: { mode: 'live'|'snapshot', airport, snapshot: {now, ac|aircraft}, snapshotLabel, metar, models: {key: source}, relay: bool, about, attrib }
export async function startApp(cfg) {
  const root = document.getElementById('app');
  const canvas = document.createElement('canvas'); canvas.id = 'gl'; root.prepend(canvas);
  const qPref = store.get('quality', 'auto'); const Q = pickQuality(qPref);
  let lightMode = store.get('light', 'real'), showOthers = store.get('others', true);
  let selected = null, followMode = null;
  const ui = new UI(root, {
    onSelect: (hex, fly) => select(hex, fly), onView: (v) => view(v), onFollow: (m) => followCmd(m),
    onSetting: (k, v) => setting(k, v), showOthers: () => showOthers,
    onAtc: (a, v) => atcCmd(a, v), onStatsOpen: () => statsSheet(Date.now()),
    planFor: (tr) => { try { return traffic.planFor(tr); } catch (e) { return null; } },   // (list rows: the leg SFO lists for the flight, ui.js routeText)
  });
  ui.root.querySelector('[data-set="light"]').value = lightMode; ui.root.querySelector('[data-set="quality"]').value = qPref; ui.root.querySelector('[data-set="others"]').checked = showOthers;
  ui.setAbout(cfg.about || ''); ui.setAttrib(cfg.attrib || '');
  try {
    ui.progress(0.05, 'Starting graphics…'); await nextFrame();
    initGL(canvas);
    if (!gl.getExtension('EXT_color_buffer_float') && !gl.getExtension('EXT_color_buffer_half_float')) throw new Error('This device\'s browser lacks floating-point render targets (WebGL2 EXT_color_buffer_float).');
    { // anisotropic filtering for the ground textures (grazing view angles on the airfield)
      const ext = gl.getExtension('EXT_texture_filter_anisotropic');
      const maxA = ext ? gl.getParameter(ext.MAX_TEXTURE_MAX_ANISOTROPY_EXT) : 1;
      window.ANISO = Math.min(maxA, Q.name === 'high' ? 16 : Q.name === 'medium' ? 8 : 4);
    }
  } catch (e) { ui.fail('Sorry — this browser can\'t run the 3D view (WebGL 2 required).<br><small>' + String(e.message || e) + '</small>'); throw e; }
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
  // ---------------------------------------------------------------- world
  ui.progress(0.12, 'Building terrain and airport…'); await nextFrame();
  const world = buildLiveWorld(R, cfg.airport, () => { }, { terrainStep: Q.terrainStep, mapRes: Q.mapRes, details: cfg.details, buildings: cfg.buildings, stands: cfg.stands, paint: cfg.paint, pavement: cfg.pavement, runways: RUNWAY_SIGNS() });
  const scene = new Scene(R, world);
  const gateSys = new LiveGateSystem(world.gates, { atlasExtra: Object.keys(TYPE_MODELS) }); scene.gateSys = gateSys;
  ui.progress(0.45, 'Airfield lighting…'); await nextFrame();
  const pavedMask = world.paved; // keep it for GroundPhysics (it used to be nulled before use: traffic_audit F6)
  // Airfield lighting (environment step 2, docs/research/environment_impl.md §2): the 3,633 fixture faces of
  // data/sfo_lighting.js switched by the JO 7110.65 controller of the EnvState and drawn at cd x step x beam x Allard
  // visibility (js/env/lighting/airfield.js); js/live/lights.js now gives only the approach-light structures (built at the
  // ALS light plane = landing-threshold elevation, JO 6850.2C 201a) and the blue taxiway-edge positions (inf, Q4).
  const alsPlane = {}; for (const R of LIGHTING_SPEC.runways) for (const [E, e] of Object.entries(R.ends)) if (e.als && e.landing_threshold) alsPlane[E] = GROUND_Y + (e.landing_threshold.elev_ft - 13.1) * FT;
  const lsys = buildLiveLights(cfg.airport, world.paved, { lightPlane: alsPlane }); world.paved = null;
  let camPos = [0, 100, 0];
  const airfield = new AirfieldLighting(LIGHTING_FIXTURES, LIGHTING_SPEC, { groundY: GROUND_Y, taxiEdges: lsys.L.slice(lsys.L.length - (lsys.taxiCount || 0)),
    // over the bay = outside the airport land polygon (js/geo.js AIRPORT_LAND_ST, the terrain's water mask)
    alsPlace: Object.fromEntries(Object.entries(alsPlane).map(([E, y]) => { const f = alsPlacement(E, y); return [E, (st, lat) => f(st, lat, (x, z) => { const q = worldToST(x, z); return polySDF(q[0], q[1], GEO.AIRPORT_LAND_ST) < 0; })]; })),
    // day display gain (I): renderer3 draws physical records at the night calibration; the WebGL2 renderer draws lamp units
    // unscaled at its day exposure 0.45 (~258 x renderer3's 0.36 x LAMP_M), so its gain is divided by that ratio
    dayGain: typeof R.frameScene === 'function' ? DAY_GAIN : DAY_GAIN / 258 });
  const relIn = [];   // RWSL REL activation from the traffic (AIM 2-1-6; js/env/lighting/airfield.js rwslFromTraffic)
  scene.staticLights.push((t) => {
    const T = envCore.clock.traffic; relIn.length = 0;
    if (T) for (const tr of T.tracks.values()) { const ph = tr.phase; if (ph === 'takeoff' || ph === 'final' || ph === 'flare' || ph === 'rollout') relIn.push({ phase: ph, rwy: tr.m && tr.m.rwy, x: tr.disp.x, z: tr.disp.z, gs: tr.disp.gs, ground: tr.disp.ground }); }
    airfield.rwslFromTraffic(relIn);
    return airfield.update(envCore.state, camPos, t);
  });
  scene.staticLights.push(() => nightF > 0.25 ? world.mastSprites : []);
  {
    // over-water structures (NAIP-imaged piers, lowered to the light plane) + low mounts under the land ALS lights
    // (js/anim/lights.js buildMountGeometry; the builder's land posts are replaced: they stood 1.3 m tall under lights now
    // at the light plane)
    const pd = buildPierGeometry(lsys.piers.filter(P => P.water)); const I4 = new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]); world.items.push({ mesh: new Mesh(pd), prog: 'obj', model: I4, bbox: pd.bbox, castShadow: true, uniforms: { uEmissiveBoost: 1 } });
    const md = buildMountGeometry(airfield.mountGroups()); if (md.bbox) world.items.push({ mesh: new Mesh(md), prog: 'obj', model: I4, bbox: md.bbox, castShadow: true, uniforms: { uEmissiveBoost: 1 } });
  }
  // markers for aircraft without a 3D model (light aircraft, helicopters, unknown types)
  scene.staticLights.push(() => markerSprites());
  // ---------------------------------------------------------------- environment
  // Sun / Moon / time / weather from the EnvState (js/env/state.js; 2026-11-05 environment track): the data clock (live =
  // traffic display time, replay = relay dataNow, snapshot = cfg.snapshot.now, ?t= / ?wx= overrides), the ephemeris
  // (replaces js/world/textures.js solarPosition) and the light-mode instants from sunEvents (replaces the hard-coded
  // UTC-7 presets). `metar` is the compact view of the CURRENT report by data clock (js/env/wx/metar.js decoder).
  const envCore = new AppEnv({ mode: cfg.mode, relayInfo: cfg.relayInfo, snapshotNow: cfg.snapshot && cfg.snapshot.now, snapshotMetar: cfg.metar || '', search: location.search, groundY: GROUND_Y });
  envCore.setLightMode(lightMode); envCore.attachHud(root);
  // ?qa=prov (spec §11.4): every airfield fixture face of data/sfo_lighting.js tinted by provenance (pub/obs green, std
  // blue, inf orange, NV red), day and night, on top of the current lights; counts in the ?qa=env HUD
  // (positions as drawn: ALS lights on their structures, js/env/lighting/airfield.js; counts over all fixture faces)
  if (envCore.qa.has('prov')) { const S = envCore.provSprites(airfield.recs, PROV_TINT, provCounts(airfield.loaded.records)); scene.staticLights.push(() => S); }
  let metar = null;
  let env = null, lastSunKey = '', lastBakeSun = null, nightF = 0, exposure = 0.45, cloudItems = [];
  function applyEnv(now, force) {
    const T = envCore.clock.traffic; // set once traffic exists (below); observed runway flow = stats.js runwayConfig (spec §3.5)
    const E = envCore.update(now, T && T.events ? runwayConfig(T.events, T.displayTime(now)) : null);
    metar = envCore.summary(); R.envState = E;   // the full EnvState for the renderers (both read sun / time below)
    // el = apparent (Bennett) for the sun direction / bake key; elN = geometric, for the night heuristics below (the
    // ephemeris clamps refraction at its -1 deg value, +0.65 deg, below the horizon; twilight is defined geometrically, USNO)
    const sp = { az: E.sun.az, el: E.sun.el }, elN = E.sun.elTrue;
    const key = sp.az.toFixed(1) + ':' + sp.el.toFixed(1) + ':' + (metar ? metar.raw : '');
    if (!force && key === lastSunKey) return; lastSunKey = key;
    const sunDir = E.sun.dir;
    const M = metar; const layers = M ? M.clouds.slice().sort((a, b) => a.ft - b.ft) : [];
    const COVER = { FEW: 0.14, SCT: 0.4, BKN: 0.68, OVC: 0.95 };
    const main = layers.find(c => c.cover !== 'FEW') || layers[0];
    // 10SM / P6SM (TAF forecast) are lower bounds ("10 miles or greater", ASOS; "P6SM" = more than 6 SM, AIM 7-1-28)
    const vis = M && M.visSM != null ? (M.visSM >= 10 || M.visPrefix === 'P' ? 40000 : Math.max(800, M.visSM * 1609)) : 40000;
    const wdir = ((M && M.windDir) ?? 290) * DEG, wms = ((M && M.windKt) ?? 8) * 0.5144;
    const windTo = [-Math.sin(wdir), 0, Math.cos(wdir)];
    const lowSlab = main && main.ft < 5000 && (main.cover === 'BKN' || main.cover === 'OVC');
    // old renderer, spec §9.1 items 2-3 (environment step 3): fog a = the EnvState surface extinction σ (ASOS inversion,
    // day/night blend) at the ground, b = 1 / the fog or sub-cloud top, both caps removed (uFog.w = 1: no 3 % see-through);
    // cloud cover = the layer's de-summed own coverage (JO 7900.5E summation amounts) at its real base (EnvState clouds;
    // the three.js renderer draws every layer from the EnvState itself and ignores env.fog / env.cloud)
    const fogTop = Math.max(5, ((E.atm.slabs[0] || {}).y1 ?? GROUND_Y + 914) - GROUND_Y);
    const ownOf = (c) => { const L = c && E.clouds.find(l => l.cover === c.cover && l.baseFt === c.ft); return L ? L.own : c ? COVER[c.cover] : 0.12; };
    const baseOf = (c) => { const L = c && E.clouds.find(l => l.cover === c.cover && l.baseFt === c.ft); return L ? L.base : c ? Math.max(150, c.ft * FT) : 1500; };
    env = { sunDir, mie: 21e-6, sunI: 20, fog: [E.atm.sigmaSurface * Math.exp(GROUND_Y / fogTop), 1 / fogTop, 1.0, 1.0],
      cloud: [ownOf(main), main ? Math.max(150, baseOf(main)) : 1500, lowSlab ? 4200 : 14000, 0.5], // (planes kept >= 150 m: a lower plane would cut the terminals; the fog draws lower decks)
      cloudWind: [windTo[0] * (wms * 2.5 + 1), windTo[2] * (wms * 2.5 + 1)], cloudTex: world.textures.clouds, noiseTex: world.textures.noise, refPos: [0, 60, 0],
      slab: !!lowSlab, wind: [windTo[0] * wms, windTo[2] * wms] };
    world.waterU.uWind = [windTo[0] * Math.max(wms, 1), windTo[2] * Math.max(wms, 1)]; world.waterU.uWaveAmp = Math.min(1.3, 0.45 + (wms / 0.5144) / 22);
    R.setupSky(env);
    // night: keep a faint moon/city-glow ambient so silhouettes stay readable
    const nf = sstep(3, -9, elN);
    const floorUp = [0.010, 0.012, 0.018].map(v => v * nf), floorHz = [0.012, 0.011, 0.012].map(v => v * nf);
    R.light.skyUp = R.light.skyUp.map((v, i) => Math.max(v, floorUp[i])); R.light.skyHorizon = R.light.skyHorizon.map((v, i) => Math.max(v, floorHz[i]));
    R.light.ground = R.light.ground.map((v, i) => Math.max(v, floorHz[i] * 0.5));
    const first = !lastBakeSun;
    if (first || Math.abs(sp.el - lastBakeSun.el) > 2 || Math.abs(sp.az - lastBakeSun.az) > 4 || force) {
      bakeGround(R, world, () => { }, { aptRes: Q.aptRes, cityRes: Q.cityRes, sunOnly: !first });
      if (first) releaseAirportMap(world);
      lastBakeSun = sp;
    }
    nightF = sstep(6, -4, elN);
    const dark = sstep(2, -10, elN);
    exposure = (0.45 + 0.25 * (env.cloud[0] > 0.6 ? 1 : 0) * (1 - dark)) * (1 - dark) + 2.4 * dark + sstep(8, 2, elN) * (1 - dark) * 0.25;
    R.extraCommon = { uNight: nightF };
    setLightEnv(E, typeof R.frameScene === 'function' ? DAY_GAIN : DAY_GAIN / 258);   // aircraft lights: Allard visibility (spec §4.10)
    setClouds(lowSlab ? { H: env.cloud[1], cov: env.cloud[0] } : null);
    envInfo = { sun: sp, metar: M };
  }
  let envInfo = null;
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
  const nightScale = (arr) => { if (nightF > 0.5) return arr; const k = 0.25 + 0.75 * nightF; return arr.map(s => ({ ...s, i: s.i * k })); };
  ui.progress(0.6, 'Lighting and sky…'); await nextFrame();
  applyEnv(Date.now(), true);
  // ---------------------------------------------------------------- aircraft models & traffic
  Object.assign(MODEL_SOURCES, cfg.models || {});
  // bridges of aircraft already parked when the page opens dock at once; after that every docking / retraction animates
  let bootUntil = null; const booted = () => bootUntil != null && Date.now() > bootUntil;
  const firstData = () => { if (bootUntil == null) bootUntil = Date.now() + 20000; };
  // pose a jet bridge docks to: the DRAWN pose the aircraft came to rest in (traffic.js syncBridge: tr.dockPose), as nose
  // position & heading in the airport (s,t) frame
  const poseST = (tr) => { const T = tr.model && TYPES[tr.model.t] || TYPES.a320; const P = tr.dockPose || (tr.parkPos ? { x: tr.parkPos[0], z: tr.parkPos[1], hdg: tr.parkHdg } : { x: tr.last.x, z: tr.last.z, hdg: tr.last.hd });
    const h = hdgVec(P.hdg); const k = antOf(T);
    const n = worldToST(P.x + h[0] * k, P.z + h[1] * k), o = worldToST(0, 0), d = worldToST(h[0], h[1]); return { nose: n, dir: [d[0] - o[0], d[1] - o[1]] }; };
  const traffic = new Traffic({ gates: world.gates, airport: cfg.airport, persist: cfg.mode === 'live', centerlines: cfg.details ? cfg.details.centerlines : null, taxigraph: cfg.taxigraph || null, stands: cfg.stands || null,
    onGateChange: (g, tr, opt) => applyGate(g, tr, opt) });
  envCore.setTraffic(traffic);
  // the physical bridges of a stand: its own, or -- for an alternative (MARS) position without bridges of its own, e.g.
  // B5S / B16S / C9V (data/sfo_stands.json shares_bridges_of) -- those of its base stand, which dock to the aircraft there
  const gateByName = new Map(world.gates.map(g => [g.name, g]));
  const bridgeGate = (g) => (g.sharesBridgesOf && !(g.bridges && g.bridges.length) && gateByName.get(g.sharesBridgesOf)) || g;
  // jet-bridge docking follows the scene: traffic.js calls this at display time (docks once the drawn aircraft has come to
  // rest; retracts when it is leaving, before it moves) and only for aircraft with a 3-D airframe
  // opt.early (traffic.js earlyUndock, realtime-v6): the departure is known before its push -- gates.js undockEarly() retracts
  // at the sheet's rates while the aircraft stays parked; a later onGateChange(g, tr) with the same type and pose re-docks it
  // (gates.js redock). opt.fast (traffic.js undock of a departing / removed aircraft seen only with its push): gates.js
  // hurryUndock(), the rest of the retraction at the sheet's maximum rates (docs/requests/bridges_closeout.md Round 2 API)
  function applyGate(g, tr, opt) {
    const G = bridgeGate(g); const now = Date.now();
    if (!tr && opt && opt.early && gateSys.undockEarly) { gateSys.undockEarly(G, now); return; }
    gateSys.setOccupant(G, tr && tr.model && TYPES[tr.model.t] ? tr.model.t : null, booted(), now, tr ? poseST(tr) : null, tr ? tr.info.icao : null);
    if (!tr && opt && opt.fast && gateSys.hurryUndock) gateSys.hurryUndock(G, opt.s || 5, now);
  }
  // extension (0 retracted .. 1 docked) of a stand's bridges, for the engine's hold-until-clear (gates.js extension(): 1
  // only when a bridge actually docks the occupant)
  traffic.bridgeK = (g) => { const G = bridgeGate(g); if (gateSys.extension) return gateSys.extension(G); const a = gateSys.anims.get(G.id); return a ? a.k : (G.acType ? 1 : 0); };
  // seconds until the stand's bridges are clear of the occupant's straight push-back (the body's hold) and until they are
  // fully retracted (gates.js pushClearEta / undockEta)
  if (gateSys.pushClearEta) { traffic.pushClearEta = (g) => gateSys.pushClearEta(bridgeGate(g), Date.now()); traffic.undockEta = (g) => gateSys.undockEta(bridgeGate(g), Date.now()); }
  const buildingAt = buildingGrid(cfg.airport); traffic.buildingAt = buildingAt;
  // ---------------------------------------------------------------- ATC (atc.js): tuned LiveATC feed + audio delay (per device)
  let atcTuned = store.get('atc.mount', null); if (atcTuned && !FEED_BY.has(atcTuned)) atcTuned = null;
  let atcDelayS = clamp(+store.get('atc.delay', 0) || 0, 0, 30); traffic.setAudioDelay(atcDelayS * 1000);
  let atcRolesBy = new Map(), atcLikely = new Map();
  function atcUpdate(now) {
    atcRolesBy = new Map(); atcLikely = new Map(FEEDS.map(f => [f.mount, []]));
    const tuned = atcTuned ? FEED_BY.get(atcTuned) : null; const mark = new Map();
    for (const tr of traffic.tracks.values()) {
      const roles = atcRoles(tr, traffic, now); if (!roles.length) continue; atcRolesBy.set(tr.hex, roles);
      const name = (tr.cs && tr.cs.display) || tr.info.reg || tr.hex.toUpperCase();
      for (const f of FEEDS) { const r = onFeed(roles, f); if (r) atcLikely.get(f.mount).push({ hex: tr.hex, name, chip: roleChip(r) }); }
      if (tuned) { const r = onFeed(roles, tuned); if (r) mark.set(tr.hex, roleChip(r)); }
    }
    ui.atcMark = mark;
    ui.setAtc({ tuned: atcTuned, delayS: atcDelayS, snapshot: cfg.mode === 'snapshot', likely: atcLikely, chip: tuned ? shortFeed(tuned) : null });
  }
  const shortFeed = (f) => ({ twr: 'TWR', gnd: 'GND', clr: 'CLR', fin: 'APP', app: 'APP', dep: 'DEP', ramp: 'RAMP', atis: 'ATIS', ctr: 'CTR' }[f.group] || 'on');
  function atcCmd(a, v) {
    if (a === 'tune') { atcTuned = v && v !== atcTuned ? v : null; store.set('atc.mount', atcTuned); }
    else if (a === 'listen') { if (FEED_BY.get(v) && FEED_BY.get(v).keys.length) { atcTuned = v; store.set('atc.mount', v); } }
    else if (a === 'delay') { atcDelayS = clamp(Math.round(v), 0, 30); store.set('atc.delay', atcDelayS); traffic.setAudioDelay(atcDelayS * 1000); status(Date.now()); }
    atcUpdate(Date.now()); ui.renderList(true, [...traffic.tracks.values()]);
  }
  function statsSheet(now) { if (!ui.statsOpen()) return; const tD = traffic.displayTime(now); const ages = (traffic.ages || []).filter(q => q[2]).map(q => q[1]).sort((a, b) => a - b);
    ui.setStatsSheet(statsHtml(runwayStats(traffic.events, tD), runwayQueue(traffic.tracks.values(), RWY), { delayS: traffic.delay / 1000, audioS: (traffic.audioDelay || 0) / 1000, ageS: ages.length ? ages[ages.length >> 1] : null })); }
  // (the jet bridges at rest are obstacles for aircraft parked off a stand: gates.js solids(g, b, 0), ground.js bridgeGrid)
  const restBridges = (() => { if (!gateSys.solids) return null; const boxes = []; try { for (const g of world.gates) for (const b of g.bridges || []) boxes.push(...gateSys.solids(g, b, 0)); } catch (e) { console.warn('bridge solids', e); return null; } return bridgeGrid(boxes, GROUND_Y); })();
  const physics = new GroundPhysics({ paved: pavedMask, building: buildingAt, net: traffic.net, bridges: restBridges });
  traffic.restBridgeAt = restBridges;   // (traffic.js fusInRestBridge: no rest pose accepted past a stop inside a bridge)
  // can the stand's L1 bridge dock this aircraft at that drawn pose (gates.js makePlan; traffic.js restDockOk keeps a rest
  // pose off the parked pose only where it can -- round 3)
  if (gateSys.makePlan && gateSys.bridgesOf) traffic.canDock = (g, tr, P) => { const G = bridgeGate(g); const ty = tr.model && TYPES[tr.model.t] ? tr.model.t : null; if (!ty) return true;
    const gp = { ...G, acType: ty, _lastType: ty, dockType: tr.info.icao || null, dock: poseST({ model: tr.model, dockPose: P }) }; return gateSys.bridgesOf(G).some(b => b.door === 1 && !b.upper && gateSys.makePlan(gp, b).ok); };
  // footprints of aircraft on the ground (vehicles around a stand must not hit them)
  gateSys.aircraftFootprints = () => {
    const out = [];
    for (const tr of traffic.tracks.values()) {
      if (!tr.disp.valid || !tr.disp.ground) continue; const T = tr.model && TYPES[tr.model.t]; if (!T) continue;
      const h = hdgVec(tr.disp.hdg); const k = antOf(T); out.push(footprint([tr.disp.x + h[0] * k, GROUND_Y, tr.disp.z + h[1] * k], [h[0], 0, h[1]], T, tr.gate || null));
    }
    return out;
  };
  scene.staticLights.push((t) => { const S = []; for (const s of gateSys.sprites) { if (s.night) { if (nightF > 0.3) S.push(s); } else if (s.beacon) { if (s.moving) { const k = Math.pow(Math.max(0, Math.sin(t * 6.3)), 6); S.push({ ...s, i: 40 + 400 * k }); } } else S.push(s); } return S; });
  const views = new Map(); // hex -> LiveAircraft | 'marker'
  function makeView(tr) {
    const m = tr.model;
    if (tr.vehicle || !m || !TYPES[m.t]) return 'marker';
    const ac = new LiveAircraft(m.t, m.m && MODEL_SOURCES[m.m] ? m.m : null, tr.livery, { id: tr.hex, lod: 1, lodDist: Q.lod, shadowDist: Q.shadowDist });
    ac.trackType = m.t; scene.add(ac); return ac;
  }
  function modelNote(tr) {
    const m = tr.model; if (!m) return tr.info.icao ? 'No 3D model for this type — shown as a marker.' : 'Aircraft type not reported — shown as a marker.';
    if (m.generic) return '3D model: generic business-jet airframe scaled to this type (not type-accurate).';
    if (!m.m) return '3D model: simplified procedural airframe (no detailed model available for this type).';
    const base = { b738: '737-800', a319: 'A319', a320: 'A320', a321: 'A321', b788: '787-8', e170: 'E170', e75l: 'E175', e190: 'E190', bcs1: 'A220-100', bcs3: 'A220-300', crj2: 'CRJ200', crj7: 'CRJ700', crj9: 'CRJ900', b752: '757-200', b763: '767-300', b744: '747-400', b748: '747-8', a333: 'A330-300', a359: 'A350-900', a388: 'A380', md11: 'MD-11' }[m.m];
    const own = TYPES[m.t] ? TYPES[m.t].name : '';
    return `3D model: FlightGear/FlightAirMap ${base}` + (own && !own.endsWith(base) ? ` (adapted to ${own.replace(/^(Boeing|Airbus|Embraer|Bombardier|McDonnell Douglas) /, '')})` : '') + '. Livery colours simplified.';
  }
  function syncViews(now) {
    for (const [hex, v] of views) { const tr = traffic.tracks.get(hex); if (!tr || tr.removed) { if (v !== 'marker') scene.aircraft.splice(scene.aircraft.indexOf(v), 1); views.delete(hex); if (selected === hex) select(null); } }
    for (const tr of traffic.tracks.values()) {
      if (!tr.disp.valid) continue;
      let v = views.get(tr.hex);
      const want = tr.model ? tr.model.t : null;
      if (v && v !== 'marker' && v.trackType !== want) { scene.aircraft.splice(scene.aircraft.indexOf(v), 1); v = null; }
      if (v === 'marker' && want && TYPES[want] && !tr.vehicle) v = null;
      if (!v) { v = makeView(tr); views.set(tr.hex, v); }
      if (v === 'marker') continue;
      const D = tr.disp; v.visible = !(D.alpha < 0.5);   // re-placements fade out / in (traffic.js CUT_S)
      const h = hdgVec(D.hdg); const back = v.T.xMain - antOf(v.T); // model origin = main gear; reported point = antenna
      v.pos = [D.x - h[0] * back, D.y, D.z - h[1] * back]; v.fwd = [h[0], 0, h[1]];
      v.pitch = D.pitch; v.roll = D.roll; v.gear = D.gear; v.flaps = D.flaps; v.spoilers = D.spoilers;
      if (v.liv !== tr.livery) { v.liv = tr.livery; v._pu = null; }
      const moving = !D.ground || D.gs > 0.5, air = !D.ground, ph = tr.phase;
      // exterior lights per phase (environment step 2: AIM 4-3-24, 14 CFR 91.209; js/env/aircraft_lights.js)
      Object.assign(v.lightsOn, aircraftLightStates({ phase: ph, ground: !air, gs: (D.gs || 0) / 0.514444, altAgl: D.y - GROUND_Y, stale: tr.stale }));   // disp.gs m/s -> kt
      v.cabin = nightF * (tr.stale ? 0.15 : 1) * 0.9; v.selected = tr.hex === selected ? 1 : 0; v.dirt = 0.35;
    }
  }
  function markerSprites() {
    const out = [];
    for (const [hex, v] of views) { if (v !== 'marker') continue; const tr = traffic.tracks.get(hex); if (!tr || !tr.disp.valid || tr.disp.alpha < 0.5) continue; const D = tr.disp;
      const cat = category(tr); const c = { arr: [0.3, 0.8, 1], dep: [1, 0.7, 0.3], ground: [0.5, 0.9, 0.6], other: [0.85, 0.85, 0.9], vehicle: [1, 0.72, 0.1] }[cat] || [0.85, 0.85, 0.9];
      out.push(cat === 'vehicle' ? { p: [D.x, D.y + 1.6, D.z], c, i: 60, s: 0.7 } : { p: [D.x, D.y + 2, D.z], c, i: 120, s: 1.4 }); }
    return out;
  }
  // ---------------------------------------------------------------- camera
  const rig = new CameraRig(canvas, { heightAt: (x, z) => world.terrain.height(x, z), onTap: (x, y) => tap(x, y), onUserMove: () => { if (followMode && rig.mode !== 'follow') followMode = null; } });
  const tower = world.towerPos || [-600, GROUND_Y, 300];
  const thr = (n) => RWY.find(r => r.name === n);
  const mid = (a, b) => [(a[0] + b[0]) / 2, GROUND_Y, (a[1] + b[1]) / 2];
  function view(name) {
    rig.stopFollow(); followMode = null; if (name !== 'tower') rig.leaveTower();
    if (name === 'overview') rig.flyTo({ target: [-450, GROUND_Y, 150], dist: 5400, yaw: 138 * DEG, pitch: 23 * DEG, fov: 50 * DEG });
    else if (name === 'terminal') rig.flyTo({ target: [-1030, GROUND_Y, 330], dist: 1500, yaw: 105 * DEG, pitch: 30 * DEG, fov: 50 * DEG });
    else if (name === 'final28') { const a = thr('28L'), b = thr('28R'); const t = mid(a.thr, b.thr); rig.flyTo({ target: [t[0] + a.dir[0] * 400, GROUND_Y + 20, t[2] + a.dir[1] * 400], dist: 4200, yaw: (a.hdg / DEG + 180) * DEG, pitch: 5 * DEG, fov: 45 * DEG }); }
    else if (name === 'runways1') { const a = thr('1L'), b = thr('1R'); const t = mid(a.thr, b.thr); rig.flyTo({ target: [t[0] + a.dir[0] * 900, GROUND_Y, t[2] + a.dir[1] * 900], dist: 2600, yaw: (a.hdg / DEG + 75) * DEG, pitch: 14 * DEG, fov: 50 * DEG }); }
    else if (name === 'top') rig.flyTo({ target: [-450, GROUND_Y, 150], dist: 8200, yaw: 180 * DEG, pitch: 88 * DEG, fov: 50 * DEG });
    else if (name === 'tower') rig.setTower([tower[0], tower.eyeY || GROUND_Y + 62, tower[2]], { yaw: 70 * DEG, pitch: -6 * DEG, fov: 58 * DEG }); // eyeY: the 3-D tower's cab eye (js/three/buildings3d.js)
    ui.root.querySelectorAll('#views [data-view]').forEach(b => b.classList.toggle('on', b.dataset.view === name));
  }
  const followFn = (hex) => () => { const tr = traffic.tracks.get(hex); if (!tr || !tr.disp.valid) return null; const D = tr.disp; const T = tr.model && TYPES[tr.model.t] || TYPES.a20n; return { p: [D.x, D.y + T.Hc * 0.8, D.z], hdg: D.hdg, L: T.L }; };
  function select(hex, fly) {
    selected = hex; const tr = hex && traffic.tracks.get(hex);
    if (!tr) { selected = null; ui.renderCard(null); if (followMode) { rig.stopFollow(); followMode = null; } ui.renderList(true, [...traffic.tracks.values()]); return; }
    if (fly) { rig.leaveTower(); rig.setFollow(followFn(hex), { chase: false }); followMode = 'follow'; }
    ui.renderCard(tr, cardExtra(tr)); ui.renderList(true, [...traffic.tracks.values()]);
    if (window.innerWidth < 760) ui.setSheet('peek');
  }
  const cardExtra = (tr) => ({ modelNote: modelNote(tr), follow: followMode, sfo: traffic.planFor(tr), atc: atcRoles(tr, traffic, Date.now()) });
  function followCmd(m) {
    if (!selected) return;
    if (m === 'free') { rig.stopFollow(); followMode = null; }
    else { rig.leaveTower(); rig.setFollow(followFn(selected), { chase: m === 'chase', pitch: m === 'chase' ? 9 * DEG : undefined }); followMode = m; }
    const tr = traffic.tracks.get(selected); if (tr) ui.renderCard(tr, cardExtra(tr));
  }
  let screenPts = new Map();
  function tap(x, y) {
    let best = null, bd = 1e9;
    for (const [hex, p] of screenPts) { const d = Math.hypot(p.x - x, p.y - y); if (d < Math.max(26, p.r) && d < bd) { bd = d; best = hex; } }
    if (best) select(best, true); else if (selected) select(null);
  }
  function setting(k, v) {
    if (k === 'light') { lightMode = v; store.set('light', v); envCore.setLightMode(v); applyEnv(Date.now(), true); }
    else if (k === 'quality') { store.set('quality', v); location.reload(); }
    else if (k === 'others') { showOthers = v; store.set('others', v); ui.renderList(true, [...traffic.tracks.values()]); }
    else if (k === 'clearParked') { traffic.clearParked(); for (const tr of [...traffic.tracks.values()]) if (tr.stale) traffic.remove(tr); }
  }
  // ---------------------------------------------------------------- data
  let feedState = { state: 'wait', text: 'Connecting…' }; let gatesInfo = null;
  if (cfg.mode === 'snapshot') {
    const snap = cfg.snapshot;
    // (one recorded instant: nothing goes silent in reality, so no silent docking of arrivals -- traffic.js silentDock)
    traffic.noSilentDock = true;
    // the recorded snapshot is one instant: parked aircraft stay (kept alive, bridges stay docked); aircraft that were
    // moving are re-created every 90 s so they never run far from where they were recorded
    const load = () => {
      firstData(); const p = parsePayload(snap); const off = Date.now() - p.now; p.now += off; for (const a of p.aircraft) a.t += off;
      const keep = new Set();
      // (kept alive: the engine ages a track by its newest POSITION, lastFixT)
      // (a moving one that is drawn is re-placed at its recorded position with a fade -- traffic.js 'gap' cut: its old
      // reports are dropped, the recorded one is ingested below -- never a pop)
      for (const tr of [...traffic.tracks.values()]) { if (!tr.vehicle && tr.disp.ground && (tr.m.phase === 'still' || tr.gate)) { tr.lastRecv = tr.lastFixT = Date.now(); keep.add(tr.hex); } else if (tr.disp.valid && tr.disp.alpha > 0.01 && !tr.fadeOut) { tr.reps = []; tr.cutting = 'gap'; } else traffic.remove(tr); }
      p.aircraft = p.aircraft.filter(a => !keep.has(a.hex)); traffic.offset = null; traffic.ingest(p, Date.now());
    };
    traffic.movingLostMs = 100000;   // (moving aircraft are re-created every 90 s from the one recorded instant: not 'lost')
    load(); setInterval(load, 90000);
    // parked aircraft of the recording stay current (not 'last signal … ago') between the reloads
    setInterval(() => { for (const tr of traffic.tracks.values()) if (!tr.vehicle && tr.disp.ground && (tr.m.phase === 'still' || tr.gate)) { tr.lastRecv = tr.lastFixT = Date.now(); tr.stale = false; } }, 20000);
    feedState = { state: 'snap', text: cfg.snapshotLabel || 'Recorded snapshot' };
  } else {
    const relay = !!cfg.relay;
    let lastSrc = null, fails = 0, fellBack = false;
    const onData = (p, src) => { firstData(); lastSrc = p.source || src.name; if (p.dataNow != null) envCore.setDataNow(p.dataNow, Date.now()); traffic.ingest(p, Date.now()); fails = 0; if (fellBack) { fellBack = false; } };
    const onStatus = (s) => {
      const nAc = () => [...traffic.tracks.values()].filter(t => !t.vehicle && !t.stale).length;
      if (s.ok) feedState = { state: 'live', text: 'Live', n: nAc(), src: s.source.name };
      else { fails++; feedState = { state: fails > 3 ? 'err' : 'wait', text: fails > 3 ? 'Live feed unavailable' : 'Reconnecting…', err: s.error }; if (fails === 4 && cfg.snapshot && !traffic.tracks.size) { const p = parsePayload(cfg.snapshot); const off = Date.now() - p.now; p.now += off; for (const a of p.aircraft) a.t += off; traffic.ingest(p, Date.now()); fellBack = true; } }
    };
    let feed;
    if (relay) {
      // the relay's merged ~1 Hz stream (SSE, deltas), shown DELAY_MS (1.5 s, adapted 1-3 s) behind real time
      feed = new StreamFeed({ onData, onStatus }); traffic.delay = traffic.delayTarget = DELAY_MS; traffic.adaptDelay = true;
    } else {
      // no relay: direct provider polling (browsers are usually blocked by CORS, docs/research/realtime_feeds.md s.3)
      feed = new Feed({ lat: ARP.lat, lon: ARP.lon, radiusNm: 40, intervalMs: 7000, sources: SOURCES, onData, onStatus });
      traffic.adaptDelay = false; traffic.delay = traffic.delayTarget = 9500;
    }
    feed.start();
    if (relay && cfg.relayInfo && cfg.relayInfo.features && cfg.relayInfo.features.gates) {
      // SFO's own gate/stand plan through the relay (it fetches flysfo.com at most every 10 min): strong prior for the
      // stand an aircraft is parked at, plus deep links for the owner's own check (docs/research/gate_truth.md s.6)
      const gp = async () => { const g = await fetchGates('api/gates'); if (g) { traffic.setPlan(g); gatesInfo = g; } };
      gp(); setInterval(gp, 60000);
    }
    const routes = new Routes({ url: relay ? '/api/routeset' : 'https://api.adsb.lol/api/0/routeset' });
    setInterval(async () => {
      const need = [...traffic.tracks.values()].filter(t => t.route === undefined && t.cs && t.cs.airline && t.last && !routes.pending.has(t.cs.callsign)).slice(0, 80);
      if (!need.length) return;
      const toLL = GEO.worldToWgs84 || GEO.worldToLL;
      const pl = need.map(t => { const ll = toLL(t.last.x, t.last.z); return { callsign: t.cs.callsign, lat: +ll[0].toFixed(3), lng: +ll[1].toFixed(3) }; });
      await routes.request(pl);
      for (const t of need) { const r = routes.get(t.cs.callsign); if (r !== undefined || routes.cache.has(t.cs.callsign)) traffic.setRoute(t, r || null); }
    }, 6000);
    // relay METAR (JSON, last 3 h) every 60 s -- the relay's conditional, scheduled upstream cache makes this free and a
    // SPECI shows within a minute (environment_spec.md §3.3); TAF every 10 min. No relay: SNAPSHOT_METAR only.
    const wx = async () => { const L = await fetchMetar('KSFO', relay ? '/api/metar?ids=KSFO&format=json' : null); if (L) { envCore.setReports(L); applyEnv(Date.now(), false); if (metar && metar.altim) traffic.metarQnh = metar.altim * 33.8639; } };
    const taf = async () => { if (relay && cfg.relayInfo && cfg.relayInfo.features && cfg.relayInfo.features.taf) { const t = await fetchTaf('/api/taf?format=json'); if (t) envCore.setTaf(t); } };
    wx(); setInterval(wx, 60000); taf(); setInterval(taf, 10 * 60000);
    ui.statusSource = () => lastSrc;
  }
  // ---------------------------------------------------------------- loop
  view('overview'); rig.anim = null; rig.update(0); // start at the overview
  { const a = rig; a.target = [-450, GROUND_Y, 150]; a.dist = 5400; a.yaw = 138 * DEG; a.pitch = 23 * DEG; }
  ui.progress(0.9, 'Loading aircraft…'); await nextFrame();
  let running = true, last = performance.now(), simT = 0, tList = 0, tCard = 0, tEnv = 0, ftEMA = 16, tScale = 0; // UI timers use wall-clock seconds
  const post = { exposure: 0.45, shutter: 0, bloom: 0.012, vignette: 0.18, grain: 0.0, sat: 1.1 };
  function onResize() { S = size(); if (canvas.width !== S.cw || canvas.height !== S.ch) { canvas.width = S.cw; canvas.height = S.ch; } R.resize(S.rw, S.rh); rig.resize(canvas.clientWidth, canvas.clientHeight); }
  window.addEventListener('resize', onResize); onResize();
  function tick() {
    if (!running) return;
    const tp = performance.now(); const wall = (tp - last) / 1000; let dt = Math.min(wall, 0.1); last = tp; simT += dt;
    const now = Date.now();
    try {
      traffic.update(now, dt); physics.resolve(traffic, dt); syncViews(now); rig.update(dt);
      if ((tEnv += wall) > 30) { tEnv = 0; applyEnv(now, false); }
      const cam = rig.camera(); camPos = cam.pos; setLightViewer(camPos); setLightFrame(simT);   // aircraft light sectors / flashes
      const fr = scene.frame(simT, cam.pos);
      post.exposure = exposure;
      const C = R.render(fr, cam, simT, post); scene.commit(); R.present(canvas.width, canvas.height);
      labels(C, now);
      if ((tList += wall) > 1) { tList = 0; ui.renderList(false, [...traffic.tracks.values()]); status(now); }
      if (selected && (tCard += wall) > 0.5) { tCard = 0; const tr = traffic.tracks.get(selected); if (tr) ui.renderCard(tr, cardExtra(tr)); }
    } catch (e) { console.error(e); }
    // dynamic resolution: keep the frame time near 33 ms
    const ft = performance.now() - tp; ftEMA += (ft - ftEMA) * 0.05;
    if (!FIXED_RES && (tScale += wall) > 2.5) { tScale = 0; const ns = ftEMA > 36 ? scale * 0.88 : ftEMA < 20 ? Math.min(Q.scaleMax, scale * 1.08) : scale; if (Math.abs(ns - scale) > 0.02) { scale = clamp(ns, 0.4, Q.scaleMax); onResize(); } }
    requestAnimationFrame(tick);
  }
  function status(now) {
    // "Live · 1.4 s · adsb.fi + adsb.lol": how far the scene runs behind real time (interpolation delay + ATC audio delay)
    const s = feedState; const lag = (traffic.delay + (traffic.audioDelay || 0)) / 1000; const provs = s.src ? String(s.src).split('+').join(' + ') : '';
    const txt = s.state === 'live' ? `Live · ${lag.toFixed(1)} s` : s.state === 'snap' ? s.text + (atcDelayS ? ` · +${atcDelayS} s` : '') : s.text;
    ui.setStatus({ state: s.state, text: txt, sub: s.state === 'snap' ? '' : provs, title: s.err ? 'Last error: ' + s.err : s.state === 'live' ? `${s.n ?? ''} aircraft · scene ${lag.toFixed(1)} s behind real time (interpolation ${(traffic.delay / 1000).toFixed(1)} s${traffic.audioDelay ? ` + ATC audio delay ${(traffic.audioDelay / 1000).toFixed(0)} s` : ''}) · positions from ${provs || 'the relay'}` : '' });
    const M = metar; const wx = M ? `${M.windDir != null ? String(M.windDir).padStart(3, '0') + '°' : 'VRB'} ${M.windKt ?? 0} kt · ${M.visPrefix === 'P' ? 'P' : ''}${M.visSM ?? '—'} SM${M.clouds.length ? ' · ' + M.clouds.map(c => c.cover + String(c.ft / 100).padStart(3, '0')).join(' ') : ''}` : '';
    ui.setClock(new Date(cfg.mode === 'snapshot' ? cfg.snapshot.now : traffic.audioDelay ? traffic.displayTime(now) : now), wx + envCore.clockNote());
    const tD = traffic.displayTime(now);
    ui.setStats(statsLine(runwayStats(traffic.events, tD), tD)); statsSheet(now); atcUpdate(now);
  }
  // labels + picking points
  function labels(C, now) {
    const W = canvas.clientWidth, H = canvas.clientHeight; const vp = C.vpNear, cp = C.pos;
    const items = []; screenPts = new Map();
    for (const tr of traffic.tracks.values()) {
      const D = tr.disp; if (!D.valid) continue;
      const cat = category(tr); if (cat === 'other' && !showOthers && tr.hex !== selected) continue;
      if (cat === 'vehicle' && tr.hex !== selected && Math.hypot(D.x - cp[0], D.y - cp[1], D.z - cp[2]) > 1200) continue;
      const T = tr.model && TYPES[tr.model.t] || null; const hgt = T ? T.Hc + T.R * 2.4 : 6;
      const x = D.x - cp[0], y = D.y + hgt - cp[1], z = D.z - cp[2];
      const cw = vp[3] * x + vp[7] * y + vp[11] * z + vp[15]; if (cw < 0.5) continue;
      const sx = (vp[0] * x + vp[4] * y + vp[8] * z + vp[12]) / cw, sy = (vp[1] * x + vp[5] * y + vp[9] * z + vp[13]) / cw;
      const px = (sx * 0.5 + 0.5) * W, py = (0.5 - sy * 0.5) * H;
      const dist = Math.hypot(x, y, z); const r = (T ? T.L * 0.55 : 8) / dist * H / (2 * Math.tan(C.fov / 2));
      const gx = D.x - cp[0], gy = D.y + (T ? T.Hc : 2) - cp[1], gz = D.z - cp[2];
      const gw = vp[3] * gx + vp[7] * gy + vp[11] * gz + vp[15];
      if (gw > 0.5) screenPts.set(tr.hex, { x: ((vp[0] * gx + vp[4] * gy + vp[8] * gz + vp[12]) / gw * 0.5 + 0.5) * W, y: (0.5 - (vp[1] * gx + vp[5] * gy + vp[9] * gz + vp[13]) / gw * 0.5) * H, r });
      const sel = tr.hex === selected;
      const text = (tr.cs && tr.cs.display) || tr.info.reg || tr.hex.toUpperCase();
      let sub = null;
      if (sel || dist < 2500 || (dist < 9000 && cat !== 'ground')) {
        const alt = !D.ground && !tr.stale && tr.info.altBaro != null ? Math.round(tr.info.altBaro / 100) * 100 : null;
        sub = [tr.info.icao, alt != null ? (alt >= 18000 ? 'FL' + Math.round(alt / 100) : alt.toLocaleString('en-US') + ' ft') : (tr.gate ? tr.gate.name : phaseLabel(tr, now).split(' · ')[0])].filter(Boolean).join(' · ');
      }
      items.push({ hex: tr.hex, x: px, y: py, depth: dist, cat, text, sub, sel: sel ? 1 : 0, stale: tr.stale, atc: ui.atcMark.get(tr.hex) || null });
    }
    ui.updateLabels(items, W, H);
  }
  ui.progress(1, 'Ready'); ui.ready(); status(Date.now());
  requestAnimationFrame(tick);
  // ---------------------------------------------------------------- QA camera helpers (used by the test harness)
  const vh = (x, z) => Math.atan2(x, -z);
  const look = (target, yawDeg, pitchDeg, dist, fovDeg = 50) => { rig.stopFollow(); rig.leaveTower(); rig.anim = null; rig.target = target.slice(); rig.yaw = yawDeg * DEG; rig.pitch = pitchDeg * DEG; rig.dist = dist; rig.fov = fovDeg * DEG; };
  const qa = {
    hideUI: (on = true) => document.body.classList.toggle('qa', on),
    look,
    gate(name, dist = 38, side = 1, pitch = 9) {
      // camera on a stand: looking at the L1 door area from the stand's front quarter
      const g = world.gates.find(q => q.name === name); if (!g) return false;
      const b = g.bridges && g.bridges[0]; if (!b) { const n = stToWorld(g.nose[0], g.nose[1], GROUND_Y); look([n[0], GROUND_Y + 3, n[2]], 0, pitch, dist); return true; }
      const P = gateSys.pose(g, b, g.acType ? 1 : 0); const d = P.door;
      const f = gateSys.dirW ? gateSys.dirW(g) : null;
      const n = stToWorld(g.nose[0], g.nose[1], 0), o = stToWorld(0, 0, 0), dd = stToWorld(g.dir[0], g.dir[1], 0);
      const fx = dd[0] - o[0], fz = dd[2] - o[2]; const fl = Math.hypot(fx, fz); const fw = [fx / fl, fz / fl]; const lf = [fw[1], -fw[0]];
      // viewpoint ahead-left of the nose (bridge side), looking back at the door
      const off = [-fw[0] * 0.45 + lf[0] * 0.9 * side, -fw[1] * 0.45 + lf[1] * 0.9 * side]; // left (bridge) side, a little aft of the door
      look([d[0], d[1] - 1, d[2]], vh(off[0], off[1]) / DEG, pitch, dist); return true;
    },
    hold(i, dist = 32) { const h = cfg.details.holds[i]; if (!h) return false; const off = [-h.dir[0] * 0.95 + h.dir[1] * 0.3, -h.dir[1] * 0.95 - h.dir[0] * 0.3]; look([h.p[0], GROUND_Y + 1.5, h.p[1]], vh(off[0], off[1]) / DEG, 9, dist); return true; },
    threshold(name, dist = 180, pitch = 7) { const R = RWY.find(r => r.name === name); const t = [R.thr[0] + R.dir[0] * 80, GROUND_Y, R.thr[1] + R.dir[1] * 80]; look(t, vh(-R.dir[0], -R.dir[1]) / DEG, pitch, dist); return true; },
    tower(dist = 170, yaw = 235, pitch = 11) { look([world.towerPos[0], GROUND_Y + 32, world.towerPos[2]], yaw, pitch, dist); return true; },
    aircraft(hex, dist = 60, yaw = null, pitch = 10) { const tr = traffic.tracks.get(hex); if (!tr) return false; const D = tr.disp; look([D.x, D.y + 3, D.z], yaw ?? (D.hdg / DEG + 140), pitch, dist); return true; },
    gatesOccupied: () => world.gates.filter(g => g.acType).map(g => g.name),
    tracks: () => [...traffic.tracks.values()].map(t => ({ hex: t.hex, flight: t.info.flight, icao: t.info.icao, phase: t.phase, gate: t.gate && t.gate.name, ground: t.disp.ground })),
  };
  window.SFO = { R, scene, traffic, physics, rig, ui, world, gateSys, select, view, applyEnv, qa, env: () => envCore.state, envCore, airfield, stats: () => runwayStats(traffic.events, traffic.displayTime(Date.now())), atc: () => ({ tuned: atcTuned, delayS: atcDelayS, roles: Object.fromEntries(atcRolesBy), likely: Object.fromEntries(atcLikely) }), atcCmd: (a, v) => atcCmd(a, v), setLight: (m) => setting('light', m), frameNow: () => { last = performance.now() - 16; tick(); } };
  return window.SFO;
}
