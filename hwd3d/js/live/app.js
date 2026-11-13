// Hayward Live 3D - application shell: boot, render loop, feeds (live relay / replay / one recorded instant), environment,
// camera views, picking, UI glue, QA hooks (hwd3d Phase 2, P4).
// Forked from sfo3d/js/live/app.js @ a967f9b (596 lines), rewritten around the Phase 2 contracts (docs/phase2_fork_map.md
// 2.10). Kept: the quality tiers and the dynamic resolution (frame time held near 33 ms; ?fixedres=1 pins it for QA
// stills), the WebGL2 checks and the context-loss message, the boot progress, the tick order (traffic.update ->
// physics.resolve -> views.sync -> rig.update -> environment every 30 s -> scene.frame -> R.render -> scene.commit ->
// R.present -> labels; list + status every 1 s, the card every 0.5 s), the aircraft-light viewer / frame / environment
// hooks of js/env/aircraft_lights.js (setLightViewer, setLightFrame, setLightEnv with sfo3d's WebGL2-renderer day gain
// DAY_GAIN / 258, app.js line 237), DOM labels projected with C.vpNear, tap picking, follow / chase / free camera, the
// METAR poll every 60 s, the settings, window.<hook>.qa camera helpers.
// Changed:
//  - the world is P2's (buildSite + buildHwdWorld; render_env.js applyEnvToRenderer does the fog / clouds / exposure that
//    sfo3d's applyEnv did here); traffic, parking, physics and the aircraft drawables are P3's (Traffic, ParkingModel,
//    GroundPhysics, AircraftViews); ground heights come from site.groundY (no GROUND_Y);
//  - modes: live (relay StreamFeed, adaptive display delay starting from the relay's poll period), replay (the relay's
//    --replay or P1's in-page shim: the display runs features.replay.lookahead_s, 60 s, behind with the delay fixed, and
//    the stream starts with ?history = lookahead_s + 5 s, P1 docs/phase2_relay.md "How the app must handle the holes"),
//    snapshot (one instant S of P1's pack: the engine is run over the PRE_S s before S on the pack's own events, then
//    the traffic clock is frozen at S + lookahead_s, so S is drawn between real fixes; only rotors and lights move);
//  - D1 / fork map 2.0: names on screen come only from tr.ident (label = callsign / registration / type; type only for a
//    masked track); the DOM, the QA hooks' track lists and every log line carry an opaque per-page id, never a track key;
//  - views: Overview, Tower (eye at the cab, site.anchors.tower), Green Ramp, West Hangars (P2 dev/world.js framings) and
//    28L Final (behind an aircraft on the published 4.0 deg VASI path, NASR); the status line counts traffic by phase.
// Dropped (SFO only): jet bridges and the gate system, airfield-lighting fixtures, ALS structures, reservoirs and the shore
// field, flysfo gates, routes, LiveATC feed tuning and the audio delay (D2: a link-out only), airliner models and markers.
import { initGL, gl } from '../gl.js';
import { Renderer } from '../renderer.js';
import { Scene } from '../scene.js';
import { buildSite } from '../world/site.js';
import { buildHwdWorld, releaseAirportMap } from './world.js';
import { AppEnv } from '../env/app_env.js';
import { applyEnvToRenderer } from '../env/render_env.js';
import { setLightViewer, setLightFrame, setLightEnv, DAY_GAIN } from '../env/aircraft_lights.js';
import { Traffic, phaseLabel, category, DELAY_MS, DELAY_MAX } from './traffic.js';
import { ParkingModel } from './parking.js';
import { GroundPhysics } from './ground.js';
import { AircraftViews } from './aircraft.js';
import { StreamFeed, fetchMetar, parsePayload } from './feed.js';
import { CameraRig } from './controls.js';
import { UI, VIEW_NAMES } from './ui.js';
import { hwdStats, statsLine, statsHtml, phaseCounts } from './stats.js';
import { towerStatus } from './classifier.js';
import { thrWorld, rwyAxis, FT } from '../geo.js';

const DEG = Math.PI / 180, KT = 1852 / 3600;
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
// quality tiers: P2's world tiers 'high' | 'low' (pavement map 0.5 / 1 m, NAIP 1.2 / 2.4 m); msaa / shadow map as P2's dev
// page; canvas caps and dynamic resolution as sfo3d's high / low tiers
// One quality level (owner decision OD1, 2026-11-13, CLAUDE.md / docs/PLAN.md 6b): the full-feature, highest-resolution
// tier everywhere - no phone 'lite' tier and no ?quality=low (fix round 1 removed the low tier that was still selectable)
const QUALITY = {
  high: { name: 'high', world: 'high', msaa: 4, shadow: 4096, scaleMax: 1.0, dprMax: 2, maxPx: 3.2e6, aniso: 8 },
};
const store = { get(k, d) { try { const v = localStorage.getItem('hwdlive.' + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } }, set(k, v) { try { localStorage.setItem('hwdlive.' + k, JSON.stringify(v)); } catch (e) { } } };
function pickQuality() { return QUALITY.high; }
const nextFrame = () => new Promise(r => setTimeout(r, 0));
const Q_ = new URLSearchParams(location.search);
const FIXED_RES = Q_.has('fixedres');
const SRC_TXT = (s) => !s ? null : /^adsb/.test(s) ? 'ADS-B 1090' : /^adsr/.test(s) ? 'ADS-R (UAT rebroadcast)' : /^tisb/.test(s) ? 'TIS-B' : /mlat/.test(s) ? 'MLAT' : /mode_s/.test(s) ? 'Mode S' : s;

// cfg: { mode: 'live'|'replay'|'snapshot', relayInfo, replayInfo, snapshot: {pack, at (s), preS}, note, airport, taxigraph, about, attrib }
export async function startApp(cfg) {
  const root = document.getElementById('app');
  const canvas = document.createElement('canvas'); canvas.id = 'gl'; root.prepend(canvas);
  const Q = pickQuality();
  const mode = cfg.mode; const snap = mode === 'snapshot' ? cfg.snapshot : null;
  let lightMode = store.get('light', 'real'), showOthers = store.get('others', true);
  let selected = null, followMode = null; let relayPoll = cfg.relayInfo && cfg.relayInfo.poll || null;
  // opaque per-page ids for the DOM (fork map 2.0: a track key never reaches the UI)
  const idByKey = new Map(), keyById = new Map(); let nextId = 1;
  const idOf = (k) => { if (k == null) return null; let i = idByKey.get(k); if (i == null) { i = nextId++; idByKey.set(k, i); keyById.set(i, k); } return i; };
  const ui = new UI(root, {
    onSelect: (id, fly) => select(id == null ? null : keyById.get(id), fly), onView: (v) => view(v), onFollow: (m) => followCmd(m),
    onSetting: (k, v) => setting(k, v), showOthers: () => showOthers, idOf,
    onStatsOpen: () => statsSheet(), onAtcOpen: () => ui.setAtc(sceneTime(), mode),
  });
  ui.root.querySelector('[data-set="light"]').value = lightMode; ui.root.querySelector('[data-set="others"]').checked = showOthers;
  ui.setAbout(cfg.about || ''); ui.setAttrib(cfg.attrib || '');
  try {
    ui.progress(0.05, 'Starting graphics…'); await nextFrame();
    initGL(canvas);
    if (!gl.getExtension('EXT_color_buffer_float') && !gl.getExtension('EXT_color_buffer_half_float')) throw new Error('This browser lacks floating-point render targets (WebGL2 EXT_color_buffer_float).');
    const ext = gl.getExtension('EXT_texture_filter_anisotropic');
    window.ANISO = Math.min(ext ? gl.getParameter(ext.MAX_TEXTURE_MAX_ANISOTROPY_EXT) : 1, Q.aniso);
  } catch (e) { ui.fail('Sorry — this browser can\'t run the 3D view (WebGL 2 required).<br><small>' + String(e.message || e) + '</small>'); throw e; }
  let running = true;
  canvas.addEventListener('webglcontextlost', (e) => { e.preventDefault(); ui.fail('The graphics context was lost (the device ran low on GPU memory). <a href="#" onclick="location.reload()">Reload</a>, or close other tabs and apps.'); running = false; });
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
  // ---------------------------------------------------------------- world (P2)
  ui.progress(0.12, 'Building the airfield…'); await nextFrame();
  const site = buildSite(cfg.airport);
  const world = buildHwdWorld(R, cfg.airport, { site, quality: Q.world, taxigraph: cfg.taxigraph || null, log: (s) => console.log(s) });
  const scene = new Scene(R, world); scene.staticLights.push(world.staticSprites);
  const gy = (x, z) => site.groundY(x, z);
  // ---------------------------------------------------------------- environment (P2: AppEnv + applyEnvToRenderer)
  ui.progress(0.4, 'Sun and weather…'); await nextFrame();
  const envCore = new AppEnv({ mode, relayInfo: cfg.relayInfo, snapshotNow: snap ? snap.at * 1000 : null, search: location.search, station: 'KHWD' });
  envCore.setLightMode(lightMode); envCore.attachHud(root);
  if (snap) envCore.setReports((snap.pack.metar || []).filter(m => m.obsTime <= snap.at && m.obsTime >= snap.at - 3 * 3600).sort((a, b) => b.obsTime - a.obsTime));
  let exposure = 0.45, nightF = 0, metar = null;
  function applyEnv(now, force) {
    const E = envCore.update(now, null);
    const r = applyEnvToRenderer(R, world, E, { quality: Q.world, force });
    exposure = r.exposure; nightF = r.nightF; metar = envCore.summary();
    // aircraft lights: Allard visibility and the day display gain of the WebGL2 renderer (sfo3d app.js: DAY_GAIN / 258)
    if (r.changed) setLightEnv(E, DAY_GAIN / 258);
    return E;
  }
  // ---------------------------------------------------------------- traffic (P3)
  ui.progress(0.55, 'Traffic engine…'); await nextFrame();
  const parking = new ParkingModel({ airport: cfg.airport, taxigraph: cfg.taxigraph || null, site });
  const traffic = new Traffic({ airport: cfg.airport, taxigraph: cfg.taxigraph || null, site, parking, persist: mode === 'live' });
  envCore.setTraffic(traffic);
  const physics = new GroundPhysics({ site, net: traffic.net, parking });
  const views = new AircraftViews(scene, { quality: Q.world });
  applyEnv(Date.now(), true);
  releaseAirportMap(world);
  // ---------------------------------------------------------------- camera
  const rig = new CameraRig(canvas, { heightAt: gy, onTap: (x, y) => tap(x, y), onUserMove: () => { if (followMode && rig.mode !== 'follow') followMode = null; markView(null); } });
  const P = (x, z) => [x, gy(x, z), z];
  const tw = site.anchors.tower;
  // named views. Orbit views: target, yaw = view heading (deg, where the camera looks), pitch down (deg), dist (m), fov;
  // pyaw: the view heading on portrait screens (P2 dev/world.js VIEWS framings, which use the same convention)
  const A28 = rwyAxis('28L'), T28 = thrWorld('28L');
  const fin = 600, finY = gy(T28[0], T28[2]) + fin * Math.tan(4.0 * DEG) + 35 * FT;   // NASR VASI 28L 4.0 deg, TCH 35 ft
  const VIEWS = {
    // pdist: the distance on portrait screens before portraitK (fix round 1: 2,700 m x 2.39 put the phone camera 6.45 km out,
    // an 11-m aircraft was 1.5 px); 1,250 m x 2.39 = 3 km frames the two runways across a 390-px screen
    overview: { target: P(40, 30), yaw: 22, pitch: 30, dist: 2700, pdist: 1250, fov: 45, pyaw: 300 },
    tower: { eye: tw ? [tw.x, tw.eyeY, tw.z] : [38.5, 23.6, -409.6], yaw: 165, pitch: -7, fov: 62 },
    green: { target: P(-50, -335), yaw: 30, pitch: 38, dist: 230, fov: 50 },
    west: { target: P(-235, -615), yaw: 335, pitch: 32, dist: 430, fov: 50 },
    final28l: { target: [T28[0] - A28.dir[0] * fin, finY, T28[2] - A28.dir[1] * fin], yaw: A28.hdg - 12, pitch: 7, dist: 1300, fov: 40 },
  };
  const markView = (name) => ui.root.querySelectorAll('#views [data-view]').forEach(b => b.classList.toggle('on', b.dataset.view === name));
  function view(name, instant = false) {
    const v = VIEWS[name]; if (!v) return false;
    rig.stopFollow(); followMode = null;
    if (v.eye) rig.setTower(v.eye, { yaw: v.yaw * DEG, pitch: v.pitch * DEG, fov: v.fov * DEG });
    else {
      rig.leaveTower();
      const portrait = canvas.clientWidth < canvas.clientHeight;
      const to = { target: v.target.slice(), yaw: ((portrait && v.pyaw != null ? v.pyaw : v.yaw) + 180) * DEG, pitch: v.pitch * DEG, dist: portrait && v.pdist ? v.pdist : v.dist, fov: v.fov * DEG };
      if (instant) rig.set(to); else rig.flyTo(to);
    }
    markView(name); currentView = name;
    return true;
  }
  let currentView = null;
  const followFn = (key) => () => { const tr = traffic.tracks.get(key); if (!tr || !tr.disp.valid || tr.removed) return null; const D = tr.disp, T = tr.dims || {}; return { p: [D.x, D.y + (T.Hc || 1.5), D.z], hdg: D.hdg * DEG, L: T.L || 9 }; };
  function select(key, fly) {
    const tr = key != null ? traffic.tracks.get(key) : null;
    if (!tr) { selected = null; ui.renderCard(null); if (followMode) { rig.stopFollow(); followMode = null; } ui.renderList(true, [...traffic.tracks.values()]); return; }
    selected = key;
    if (fly && tr.disp.valid) { rig.leaveTower(); rig.setFollow(followFn(key), { chase: false }); followMode = 'follow'; markView(null); }
    ui.renderCard(tr, cardExtra(tr)); ui.renderList(true, [...traffic.tracks.values()]);
    if (window.innerWidth < 760) ui.setSheet('peek');
  }
  function cardExtra(tr) {
    const now = engineNow(); const D = tr.disp;
    const spot = tr.park && tr.park.spotId ? parking.byId.get(tr.park.spotId) : null;
    return { modelNote: views.modelNote(tr), follow: tr.key === selected ? followMode : null, tScene: sceneTime(), parkLabel: spot ? spot.zone : null,
      ageS: tr.lastFixT ? Math.max(0, (now - tr.lastFixT) / 1000) : null, staleMs: tr.stale ? now - tr.lastRecv : null, srcText: SRC_TXT(tr.info && tr.info.src),
      hAglFt: D.valid ? (D.y - gy(D.x, D.z)) / FT : null };
  }
  function followCmd(m) {
    if (!selected) return;
    if (m === 'free') { rig.stopFollow(); followMode = null; }
    else { rig.leaveTower(); rig.setFollow(followFn(selected), { chase: m === 'chase', pitch: m === 'chase' ? 9 * DEG : undefined }); followMode = m; markView(null); }
    const tr = traffic.tracks.get(selected); if (tr) ui.renderCard(tr, cardExtra(tr));
  }
  let screenPts = new Map();
  function tap(x, y) {
    let best = null, bd = 1e9;
    for (const [key, p] of screenPts) { const d = Math.hypot(p.x - x, p.y - y); if (d < Math.max(28, p.r) && d < bd) { bd = d; best = key; } }
    if (best) select(best, true); else if (selected) select(null);
  }
  function setting(k, v) {
    if (k === 'light') { lightMode = v; store.set('light', v); envCore.setLightMode(v); applyEnv(Date.now(), true); }
    else if (k === 'others') { showOthers = v; store.set('others', v); ui.renderList(true, [...traffic.tracks.values()]); }
    else if (k === 'clearParked') traffic.clearParked();
  }
  // ---------------------------------------------------------------- clocks
  // engine clock: wall time, except in snapshot mode (frozen at S + lookahead_s once the pre-roll has run)
  let frozenNow = null;
  const engineNow = () => frozenNow != null ? frozenNow : Date.now();
  // scene time on the data clock (the recording's clock in replay / snapshot; real time minus the delay live)
  const sceneTime = () => snap ? snap.at * 1000 : envCore.clock.trafficTime(Date.now());
  // an engine-clock instant (event times) -> the data clock
  const toData = (t) => { const A = envCore.clock.anchor; return mode === 'replay' && A ? A.dataNow + (t - A.wall) * (envCore.clock.replaySpeed || 1) : t; };
  const hhmm = (t) => new Date(toData(t)).toLocaleTimeString('en-US', { timeZone: 'America/Los_Angeles', hour: 'numeric', minute: '2-digit' });
  const towerOf = (e) => towerStatus(toData(e.t));                    // event tower state on the DATA clock (fork map I3)
  const towerAtScene = () => { const h = new Date(sceneTime()).toLocaleString('en-US', { timeZone: 'America/Los_Angeles', hour: 'numeric', hour12: false }); const n = +h % 24; return n >= 7 && n < 21; };
  // ---------------------------------------------------------------- data
  let feedState = { state: 'wait', text: 'Connecting…' }; let lastSrc = null;
  const feat = (cfg.relayInfo && cfg.relayInfo.features) || {};
  const lookahead = (feat.replay && feat.replay.lookahead_s) || (cfg.replayInfo && cfg.replayInfo.lookahead_s) || (snap && snap.pack.lookahead_s) || 60;
  if (snap) {
    // one recorded instant S: run the engine over the PRE_S seconds before it on the pack's own payloads (the live code
    // path: parsePayload -> ingest -> update -> physics), then freeze the traffic clock at S + lookahead_s
    ui.progress(0.7, 'Replaying the minutes before the snapshot…'); await nextFrame();
    traffic.setLookahead(lookahead);
    const pack = snap.pack, t1 = snap.at + lookahead, t0 = Math.max(pack.from, snap.at - (snap.preS || 600));
    const st = {}, frames = [];
    for (const e of pack.events) {   // field deltas (hwd-pack/1 = sfo3d replay pack v2): expand every event in order
      if (e.T > t1) break;
      const ac = e.p.d.map(r => { const a = st[r[0]] || (st[r[0]] = { hex: r[0] }); for (const k in r[1]) a[k] = r[1][k]; if (r[2]) for (const k of r[2]) delete a[k]; return a; });
      if (e.T >= t0) frames.push({ T: e.T, json: { now: e.p.now, dataNow: e.p.dataNow, _source: e.p._source, msg: e.p.msg, ac: ac.map(a => ({ ...a })) } });
    }
    const dt = 0.2; let i = 0, n = 0; const t0w = performance.now();
    for (let t = t0; t <= t1 + 1e-6; t += dt) {
      while (i < frames.length && frames[i].T <= t) { const f = frames[i++]; const rr = f.T * 1000; traffic.ingest(parsePayload(f.json, rr), rr); }
      traffic.update(t * 1000, dt); physics.resolve(traffic, dt);
      if (++n % 250 === 0) { ui.progress(0.7 + 0.2 * (t - t0) / (t1 - t0)); await nextFrame(); }
    }
    frozenNow = t1 * 1000;
    console.log(`snapshot: ${frames.length} payloads, ${n} engine steps over ${Math.round(t1 - t0)} s in ${Math.round(performance.now() - t0w)} ms; scene ${new Date(snap.at * 1000).toISOString()}`);
    feedState = { state: 'snap', text: 'Recorded instant' };
  } else if (cfg.relayInfo) {
    const replay = mode === 'replay';
    if (replay) traffic.setLookahead(lookahead);
    else {
      // live: the relay polls adsb.lol every >= 6.5 s (up to ~60 s as the day's budget runs down) unless adsb.fi (2 s) is on:
      // start the display delay at 1.5 polls + 2 s and let the engine adapt it (fork map 2.7: DELAY_MAX covers the period)
      const per = cfg.relayInfo.poll && cfg.relayInfo.poll.adsbfi ? 2 : (cfg.relayInfo.poll && cfg.relayInfo.poll.adsblol_s) || 8;
      traffic.delay = traffic.delayTarget = clamp(per * 1500 + 2000, DELAY_MS, DELAY_MAX); traffic.adaptDelay = true;
    }
    const hist = replay ? lookahead + 5 : Math.min(120, Math.round(traffic.delay / 1000) + 5);
    // Opening-burst / catch-up payloads (relay & shim ?history: the last lookahead_s + 5 s at once). Integration workaround
    // (docs/phase2_app.md I2): traffic.js ingest() drops a NEW track's fix when recvNow - fix > MOVING_LOST_MS (45 s). The
    // 60-s history has a ~46-s polling hole (the recorder saw ~14 s of each minute), so its older cluster of fixes is
    // 50-63 s old and was all dropped, leaving only the freshest batch, and the display (60 s behind) waited ~58 s. A
    // payload older than ~3 s is therefore ingested AT ITS OWN SEND TIME (p.now, wall clock), as it would have been live,
    // so those historical fixes are kept; dataNow (the scene clock) is only advanced from head (live) payloads.
    const onData = (p, src) => {
      const wall = Date.now(); const hist = p.now != null && p.now < wall - 3000;
      lastSrc = p.source || (src && src.name);
      if (p.dataNow != null && !hist) envCore.setDataNow(p.dataNow, wall);
      traffic.ingest(p, hist ? p.now : wall);
    };
    let fails = 0;
    const onStatus = (s) => { if (s.ok) { fails = 0; feedState = { state: replay ? 'replay' : 'live', text: replay ? 'Replay' : 'Live', src: s.source && s.source.name }; } else { fails++; feedState = { state: fails > 3 ? 'err' : 'wait', text: fails > 3 ? 'Feed unavailable' : 'Reconnecting…', err: s.error }; } };
    const feed = new StreamFeed({ onData, onStatus, onForget: (keys) => traffic.forget(keys), history: hist }); feed.start();
    const wx = async () => { const L = await fetchMetar('KHWD'); if (L) { envCore.setReports(L); applyEnv(Date.now(), false); } };
    if (!replay) setInterval(async () => { try { const r = await fetch('api/ping', { cache: 'no-store' }); if (r.ok) { const j = await r.json(); relayPoll = j && j.poll; } } catch (e) { } }, 60000);
    wx(); setInterval(wx, 60000);
    window.addEventListener('pagehide', () => feed.stop());
  } else feedState = { state: 'err', text: 'No data', err: cfg.note || 'no relay' };
  // ---------------------------------------------------------------- loop
  const v0 = Q_.get('view'); view(VIEWS[v0] ? v0 : 'overview', true); rig.update(0);
  ui.progress(0.92, 'Loading imagery…');
  await Promise.race([world.ready, new Promise(r => setTimeout(r, 20000))]);
  let last = performance.now(), simT = 0, tList = 1, tCard = 0, tEnv = 0, ftEMA = 16, tScale = 0, nFrames = 0;
  const post = { exposure: 0.45, shutter: 0, bloom: 0.012, vignette: 0.18, grain: 0.0, sat: 1.05 };
  function onResize() { S = size(); if (canvas.width !== S.cw || canvas.height !== S.ch) { canvas.width = S.cw; canvas.height = S.ch; } R.resize(S.rw, S.rh); rig.resize(canvas.clientWidth, canvas.clientHeight); }
  window.addEventListener('resize', onResize); onResize();
  let lastC = null, qaPaused = false;
  function frame(wall) {
    const tp = performance.now(); let dt = Math.min(wall, 0.1); simT += dt;
    const now = engineNow();
    traffic.update(now, dt); physics.resolve(traffic, dt);
    views.sync(traffic, now, { nightF, selectedKey: selected, dt });
    rig.update(dt);
    if ((tEnv += wall) > 30) { tEnv = 0; applyEnv(Date.now(), false); }
    const cam = rig.camera();
    setLightViewer(cam.pos, 2 * Math.tan((cam.fov || 0.8) / 2) / Math.max(1, R.H)); setLightFrame(simT);
    const fr = scene.frame(simT, cam.pos);
    post.exposure = exposure;
    const C = R.render(fr, cam, simT, post); scene.commit(); R.present(canvas.width, canvas.height); lastC = C;
    labels(C);
    if ((tList += wall) > 1) { tList = 0; ui.renderList(false, [...traffic.tracks.values()]); status(); }
    if (selected && (tCard += wall) > 0.5) { tCard = 0; const tr = traffic.tracks.get(selected); if (tr && !tr.removed) ui.renderCard(tr, cardExtra(tr)); else select(null); }
    return performance.now() - tp;
  }
  function tick() {
    if (!running) return;
    if (qaPaused) { requestAnimationFrame(tick); return; }   // QA stills: the harness drives frames via HWD.qa.shot/frameNow
    const tp = performance.now(); const wall = (tp - last) / 1000; last = tp;
    let ft = 16;
    try { ft = frame(wall); } catch (e) { console.error(e); }
    ftEMA += (ft - ftEMA) * 0.05; nFrames++;
    if (!FIXED_RES && (tScale += wall) > 2.5) { tScale = 0; const ns = ftEMA > 36 ? scale * 0.88 : ftEMA < 20 ? Math.min(Q.scaleMax, scale * 1.08) : scale; if (Math.abs(ns - scale) > 0.02) { scale = clamp(ns, 0.4, Q.scaleMax); onResize(); } }
    requestAnimationFrame(tick);
  }
  function status() {
    const s = feedState, lag = traffic.delay / 1000;
    // the relay's current adsb.lol poll period (fix round 1: the budget thins the polls out over a day of watching - the pill
    // says so once it is slower than 20 s, from /api/ping, refreshed every minute)
    const pp = relayPoll && relayPoll.adsblol_s, slow = pp != null && pp > 20 ? ` · polls ${pp >= 120 ? Math.round(pp / 60) + ' min' : Math.round(pp) + ' s'}` : '';
    const txt = s.state === 'live' ? `Live · ${lag.toFixed(0)} s${slow}` : s.state === 'replay' ? `Replay · ${lag.toFixed(0)} s behind` : s.state === 'snap' ? 'Recorded instant' : s.text;
    const provs = s.src ? String(s.src).split('+').join(' + ') : '';
    ui.setStatus({ state: s.state, text: txt, sub: s.state === 'snap' ? '' : provs,
      title: s.err ? 'Last error: ' + s.err : s.state === 'live' ? `scene ${lag.toFixed(0)} s behind real time so motion is interpolated between real reports · positions from ${provs || 'the relay'}`
        : s.state === 'replay' ? `recorded adsb.lol data replayed at real speed, shown ${lag.toFixed(0)} s behind the recording head so every gap lies between two real reports` : s.state === 'snap' ? 'one recorded instant, frozen' : (cfg.note || '') });
    const M = metar; const wx = M ? `${M.windDir != null ? String(M.windDir).padStart(3, '0') + '°' : 'VRB'} ${M.windKt ?? 0} kt · ${M.visPrefix === 'P' ? 'P' : ''}${M.visSM ?? '—'} SM${M.clouds.length ? ' · ' + M.clouds.map(c => c.cover + String(c.ft / 100).padStart(3, '0')).join(' ') : ''}` : '';
    const tS = sceneTime();
    ui.towerOpen = towerAtScene();
    ui.setClock(tS, wx + envCore.clockNote());
    const tracks = [...traffic.tracks.values()];
    ui.setPhaseLine(phaseCounts(tracks));
    const tD = traffic.displayTime(engineNow());
    ui.setStats(statsLine(hwdStats(traffic.events, tD, 3600e3, towerOf)));
    statsSheet(); ui.setAtc(tS, mode);
  }
  const nameOf = (key) => { const tr = key != null && traffic.tracks.get(key); return tr && tr.ident ? tr.ident.label : null; };
  function statsSheet() {
    if (!ui.statsOpen()) return; const tD = traffic.displayTime(engineNow());
    ui.setStatsSheet(statsHtml(hwdStats(traffic.events, tD, 3600e3, towerOf), { nameOf, towerOf, idOf: (k) => (k != null && traffic.tracks.has(k) ? idOf(k) : null), clock: hhmm, delayS: snap ? null : traffic.delay / 1000, pc: phaseCounts(traffic.tracks.values()), mode }));
  }
  // labels + picking points (projected with the near-range view-projection, camera-relative: renderer computeCamera)
  function labels(C) {
    const W = canvas.clientWidth, H = canvas.clientHeight; const vp = C.vpNear, cp = C.pos;
    const items = []; screenPts = new Map();
    const proj = (x, y, z) => { const w = vp[3] * x + vp[7] * y + vp[11] * z + vp[15]; if (w < 0.5) return null; return [((vp[0] * x + vp[4] * y + vp[8] * z + vp[12]) / w * 0.5 + 0.5) * W, (0.5 - (vp[1] * x + vp[5] * y + vp[9] * z + vp[13]) / w * 0.5) * H]; };
    for (const tr of traffic.tracks.values()) {
      const D = tr.disp; if (!D.valid || !tr.inView || tr.hidden || !(D.alpha > 0.5) || !tr.ident) continue;
      const cat = category(tr); if (cat === 'vehicle') continue;
      const sel = tr.key === selected;
      if (cat === 'overflight' && !showOthers && !sel) continue;
      const T = tr.dims || {}; const top = (T.H || 3) + 1.2;
      const x = D.x - cp[0], z = D.z - cp[2];
      const pt = proj(x, D.y + top - cp[1], z); if (!pt) continue;
      const dist = Math.hypot(x, D.y - cp[1], z);
      const r = (Math.max(T.L || 8, T.span || 8, T.rotor || 0) * 0.55) / dist * H / (2 * Math.tan(C.fov / 2));
      const pc = proj(x, D.y + (T.Hc || 1.5) - cp[1], z); if (pc) screenPts.set(tr.key, { x: pc[0], y: pc[1], r });
      const I = tr.ident;
      let sub = null;
      if (sel || dist < 1800 || (!D.ground && dist < 6000)) {
        // (fix round 1: Math.round(-30 / 100) * 100 is -0 -> '-0 ft'; + 0 turns negative zero into 0)
        const alt = !D.ground && tr.last && tr.last.altB != null ? Math.round(tr.last.altB / 100) * 100 + 0 : null;
        sub = [I.icaoType && I.icaoType !== I.label ? I.icaoType : null, alt != null ? alt.toLocaleString('en-US') + ' ft' : phaseLabel(tr).split(' · ')[0].replace(/ \(provisional\)$/, '')].filter(Boolean).join(' · ');
      }
      items.push({ id: idOf(tr.key), x: pt[0], y: pt[1], depth: dist, cat, text: I.label, sub, sel: sel ? 1 : 0, stale: tr.stale });
    }
    ui.updateLabels(items, W, H);
  }
  ui.progress(1, 'Ready'); ui.ready(); status();
  if (cfg.note) console.log('note:', cfg.note);
  requestAnimationFrame(tick);
  // ---------------------------------------------------------------- QA hooks (the harness, livetest.mjs)
  // look(target [x, y, z], yawDeg = view heading, pitchDeg = down angle, dist, fovDeg): an orbit camera (P2 view convention)
  const look = (target, yawDeg, pitchDeg, dist, fovDeg = 50) => { rig.stopFollow(); rig.leaveTower(); rig.set({ target, yaw: (yawDeg + 180) * DEG, pitch: pitchDeg * DEG, dist, fov: fovDeg * DEG }); markView(null); followMode = null; return true; };
  const trackById = (id) => { const k = keyById.get(+id); return k != null ? traffic.tracks.get(k) : null; };
  const qa = {
    hideUI: (on = true) => document.body.classList.toggle('qa', on),
    pause: (on = true) => { qaPaused = on; if (!on) last = performance.now(); return qaPaused; },
    look,
    view: (name) => { const ok = view(name, true); rig.update(0); return ok; },
    views: () => VIEW_NAMES.map(v => v[0]),
    spot(id, dist = 60) { const s = parking.byId.get(id); if (!s) return false; return look([s.x, gy(s.x, s.z) + 1, s.z], (s.hdg ?? 30) + 150, 28, dist, 45); },
    hold(id, dist = 70) { const L = (cfg.taxigraph && cfg.taxigraph.holds) || []; const h = typeof id === 'number' ? L[id] : L.find(q => q.id === id); if (!h) return false; return look([h.x, gy(h.x, h.z) + 1, h.z], Math.atan2(h.dir[0], -h.dir[1]) / DEG, 20, dist, 45); },
    thr(end, dist = 260) { const t = thrWorld(end), A = rwyAxis(end); return look([t[0] + A.dir[0] * 120, gy(t[0], t[2]), t[2] + A.dir[1] * 120], A.hdg, 10, dist, 50); },
    aircraft(id, dist = 45, pitch = 14) { const tr = trackById(id); if (!tr || !tr.disp.valid) return false; const D = tr.disp; return look([D.x, D.y + 1.5, D.z], D.hdg - 140, pitch, dist, 45); },
    select: (id, fly = false) => { const tr = trackById(id); if (!tr) return false; select(tr.key, fly); return true; },
    // D1-safe track list: opaque ids and what the UI shows, never a key
    tracks: () => [...traffic.tracks.values()].filter(t => !t.removed).map(t => ({ id: idOf(t.key), label: t.ident ? t.ident.label : null, masked: !!(t.ident && t.ident.masked), type: t.ident ? t.ident.icaoType : null, cls: t.dims && t.dims.cls,
      phase: t.phase, phaseSrc: t.phaseInfo && t.phaseInfo.src, scope: t.scope, cat: category(t), inView: t.inView, valid: t.disp.valid, drawn: !!views.get(t.key), ground: t.disp.ground, stale: t.stale, hidden: t.hidden,
      park: t.park ? { spot: t.park.spotId, zone: t.park.zone, kind: t.park.kind, src: t.park.src, inside: !!t.park.inside } : null, x: +t.disp.x.toFixed(1), z: +t.disp.z.toFixed(1) })),
    counts: () => { const pc = phaseCounts(traffic.tracks.values()); const tr = [...traffic.tracks.values()];
      return { phases: pc.counts, total: pc.total, scope: tr.reduce((m, t) => (m[t.scope] = (m[t.scope] || 0) + 1, m), {}), drawn: views.map.size, tracks: tr.length,
        spotsOccupied: parking.occ ? parking.occ.size : null, events: traffic.events.length, physics: physics.stats, counters: traffic.counters, delayS: traffic.delay / 1000,
        frames: nFrames, frameMs: +ftEMA.toFixed(1), scale: +scale.toFixed(2), render: [R.W, R.H] }; },
    screen: (id) => { const k = keyById.get(+id); return k != null ? screenPts.get(k) || null : null; },
    tap: (x, y) => tap(x, y),
    sceneTime, frozen: () => frozenNow,
    // a fast screenshot from the renderer's final framebuffer (P2 dev/world.js): avoids page.screenshot recompositing the
    // heavy SwiftShader scene. Returns a PNG data URL of the 3-D view only (no DOM HUD).
    shot: (n = 2) => { for (let i = 0; i < n; i++) frame(1 / 60); const px = R.readPixels(); const c = document.createElement('canvas'); c.width = R.W; c.height = R.H; const cx = c.getContext('2d'); const id = cx.createImageData(R.W, R.H); for (let y = 0; y < R.H; y++) id.data.set(px.subarray((R.H - 1 - y) * R.W * 4, (R.H - y) * R.W * 4), y * R.W * 4); cx.putImageData(id, 0, 0); return c.toDataURL('image/png'); },
  };
  window.HWD = { R, scene, world, site, traffic, physics, parking, views, rig, ui, env: envCore, qa, VIEWS, select: (key, fly) => select(key, fly), view, applyEnv: () => applyEnv(Date.now(), true),
    stats: () => hwdStats(traffic.events, traffic.displayTime(engineNow())), frameNow: () => { last = performance.now() - 16; return frame(1 / 60); }, lastCamera: () => lastC };
  return window.HWD;
}
