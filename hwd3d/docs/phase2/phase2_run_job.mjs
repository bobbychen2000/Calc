// Independent Phase 2 run of the integrated app (docs/phase2_run.md). QA only: it changes nothing in the app. Run from
// hwd3d/ under the harness, e.g.
//   python3 -I tools/qa/phase2_run_ref.py satA 2026-11-07T20:00Z 12 out/phase2/ref_satA.json   # local-only D1 reference
//   RELAY=spawn REPLAY_FROM=2026-11-07T20:00Z WIN=satA SIM_MIN=12.5 SHOT_AT=6,11 PREFIX=run_satA REF=out/phase2/ref_satA.json \
//     node livetest.mjs docs/phase2/phase2_run_job.mjs
//   (+ MOBILE=1 for 390x844; RELAY_ARGS="--ident type-only" for commit-safe HUD shots; WATCH_TYPE=<ICAO type> WATCH_DIST/PITCH to
//   shoot a type whose fuselage enters a building footprint)
// It opens the app ON THE RELAY's own port (the real deployment path: the relay's static serving, gzip) unless DIRECT=0,
// samples the drawn traffic in-page at ~10 Hz of engine time (the same measures as P3's tools/traffic/replay_engine.mjs,
// on the bodies the app actually draws), records traffic counts by phase every 30 s, the network bytes (CDP), frame
// intervals, console errors; scans the DOM for D1 leaks (REF: a LOCAL-ONLY list of identity strings of LADD/PIA aircraft,
// never written here), checks the ATC link and the About panel, and writes screenshots run_<WIN>_<name>_<dev>.png plus
// run_<WIN>_<dev>.json (aggregates + opaque ids + ICAO types only: no key, registration or callsign is written).
import fs from 'node:fs'; import path from 'node:path';

export default async ({ page, base, OUT, DEV, MOBILE, errors, log, relayURL }) => {
  const WIN = process.env.WIN || 'w', SIM_MIN = +(process.env.SIM_MIN || 12);
  const SHOT_AT = (process.env.SHOT_AT || '6,11').split(',').filter(Boolean).map(Number);
  const SCAN_EVERY_S = 30, TL_EVERY_S = 30;
  const REF = process.env.REF ? JSON.parse(fs.readFileSync(process.env.REF, 'utf8')) : null;
  const QS = process.env.QS ?? 'fixedres=1';
  const target = (process.env.DIRECT !== '0' && relayURL) ? relayURL.href : base;
  const pngPath = (n) => path.join(OUT, `run_${WIN}_${n}_${DEV}.png`);
  const S = (f, a) => page.evaluate(f, a);
  const CONS = []; page.on('console', m => CONS.push(m.text()));
  const REQ = []; page.on('request', r => { const u = new URL(r.url()); REQ.push({ host: u.host, path: u.pathname, ident: u.pathname.endsWith('/api/ident'), masked: u.pathname.endsWith('/api/ident') && /^x/i.test(u.searchParams.get('key') || '') }); });
  // ---- network bytes (CDP: encodedDataLength = bytes on the wire incl. headers; dataLength = decoded body)
  const cdp = await page.context().newCDPSession(page); await cdp.send('Network.enable');
  const NET = new Map();
  cdp.on('Network.requestWillBeSent', e => { if (!NET.has(e.requestId)) NET.set(e.requestId, { url: e.request.url, enc: 0, encD: 0, dec: 0, done: false, t: Date.now() }); });
  cdp.on('Network.responseReceived', e => { const r = NET.get(e.requestId); if (r) { r.status = e.response.status; r.mime = e.response.mimeType; const h = e.response.headers || {}; r.ce = h['content-encoding'] || h['Content-Encoding'] || ''; r.type = e.type; } });
  cdp.on('Network.dataReceived', e => { const r = NET.get(e.requestId); if (r) { r.dec += e.dataLength; r.encD += e.encodedDataLength; } });
  cdp.on('Network.loadingFinished', e => { const r = NET.get(e.requestId); if (r) { r.enc = e.encodedDataLength; r.done = true; } });
  const netSum = () => { const by = {}; let enc = 0, dec = 0, n = 0; for (const r of NET.values()) { const u = new URL(r.url); const k = u.pathname.startsWith('/api/') ? u.pathname : (u.pathname.match(/\.(\w+)$/) || [, 'other'])[1]; const e = Math.max(r.enc, r.encD); const b = by[k] || (by[k] = { n: 0, enc: 0, dec: 0 }); b.n++; b.enc += e; b.dec += r.dec; enc += e; dec += r.dec; n++; } return { n, enc, dec, by }; };
  const big = () => [...NET.values()].filter(r => !/\/api\//.test(r.url)).map(r => ({ path: new URL(r.url).pathname, enc: Math.max(r.enc, r.encD), dec: r.dec, ce: r.ce || '', status: r.status })).sort((a, b) => b.enc - a.enc).slice(0, 14);

  const t0 = Date.now();
  await page.goto(target + 'live.html?' + QS);
  await page.waitForFunction(() => window.__hwdReady || window.__hwdError, null, { timeout: 0 });
  const err = await S(() => window.__hwdError); if (err) throw new Error(err);
  const readyMs = Date.now() - t0; const netReady = netSum();
  log('ready in', readyMs, 'ms; bytes so far', netReady.enc);
  const info = await S(() => { const c = document.createElement('canvas').getContext('webgl2'); const d = c && c.getExtension('WEBGL_debug_renderer_info');
    return { gpu: d ? c.getParameter(d.UNMASKED_RENDERER_WEBGL) : null, mode: document.querySelector('#status .txt').textContent, w: innerWidth, h: innerHeight, dpr: devicePixelRatio, render: [HWD.R.W, HWD.R.H] }; });
  log('info', JSON.stringify(info));

  // ---- in-page sampler (keys never leave the page: opaque ids only)
  await S(async (OFFHEX) => {
    const G = await import(new URL('js/live/ground.js', location.href).href);
    const T = await import(new URL('js/live/traffic.js', location.href).href);
    const H = window.HWD, site = H.site, traffic = H.traffic, parking = H.parking;
    const PAV = G.pavedWith(site), OFF = new Set(OFFHEX || []);
    const ids = new Map(); let nid = 1; const idOf = (k) => { let i = ids.get(k); if (!i) { i = nid++; ids.set(k, i); } return i; };
    const EVER = new Map(), prev = new Map();
    const M = { teleports: 0, teleportsHwd: 0, windowReentries: 0, samples: 0, drawnSum: 0, groundFW: 0, heliGround: 0, heliUnpaved: 0, air: 0, offPave: 0, offPaveMoving: 0, offPaveRoute: 0, offPaveStill: 0, offSite: 0,
      inBld: 0, inBldDoor: 0, yErr: 0, yErrMax: 0, belowGround: 0, belowGroundMax: 0, ovl: { parked: 0, mixed: 0, moving: 0 }, ovlPairs: new Set(), jumps: 0, airProx: 0, airProxPairs: new Set(),
      offTracks: new Set(), offCells: {}, bldCells: {}, kinPairs: 0, gaps: 0, offLog: [], bldLog: [], ovlLog: [] };
    const DIST = { a_label_dalt: [], a_label_lead: [], g_gs: [], a_gs: [], g_along: [], g_plat: [], g_w: [], g_crab: [], a_along: [], a_plat: [], a_w: [], a_vs: [] };
    const EXC = { label_alt200: 0, g_along3: 0, roll_along6: 0, g_lat3: 0, g_w30: 0, g_plat3: 0, g_crab10: 0, a_lat6: 0, a_w25: 0, a_vs_lim: 0, a_plat6: 0, taxi_fast: 0, ga_air_fast: 0, any_air_fast: 0 };
    const MAX = {}; const note = (k, v, ctx) => { if (!MAX[k] || v > MAX[k].v) MAX[k] = { v: +v.toFixed(2), ...ctx }; };
    const PRES = new Map(); const ctx0 = (tr, id, E, ts) => ({ id, type: E.type, cls: E.cls, phase: tr.phase, t: ts });
    const raf = []; let lastRaf = null;
    const sceneISO = () => new Date(H.qa.sceneTime()).toISOString().slice(11, 19);
    function sample() {
      const now = traffic._lastNow; if (now == null || now === R.lastNow) return;
      if (R.lastNow != null && now - R.lastNow < 95) return;
      const dt = R.lastNow != null ? (now - R.lastNow) / 1000 : null; R.lastNow = now; M.samples++;
      const kin = dt != null && dt <= 0.4; if (dt != null && !kin) M.gaps++;
      const gnd = [], air = []; let drawn = 0; const ts = sceneISO();
      // re-placements (fix round 2): presence as AircraftViews draws it (valid, in the D6 window, not hidden, alpha > 0.02);
      // ANY absence - fade cut, fade-out + removal, hidden segment, hangar - followed by a reappearance farther than
      // 1.5 x speed x absence + 10 m (and > 10 m) from where it vanished is a TELEPORT; an absence spent only outside the D6
      // window / simulation range is a window re-entry (fix round 1 counted only absences < 5 s)
      { const td = traffic.displayTime(now);
        for (const [pid, V] of PRES) if (!V.seen && V.last) { if (!V.absent) V.absent = { t: td, why: new Set() }; V.absent.why.add('removed'); }
        for (const V of PRES.values()) V.seen = false;
        for (const tr of traffic.tracks.values()) {
          const id = idOf(tr.key), D = tr.disp, present = !!(D.valid && tr.inView && !tr.hidden && D.alpha > 0.02 && tr.dims);
          let V = PRES.get(id); if (!V) PRES.set(id, V = { last: null, absent: null }); V.seen = true;
          if (present) {
            if (V.absent && V.last) { const g = (td - V.last.t) / 1000, d = Math.hypot(D.x - V.last.x, D.z - V.last.z, D.y - V.last.y);
              if (d > 1.5 * Math.max(D.gs, V.last.gs) * g + 10 && d > 10) { const why = [...V.absent.why];
                if (why.every(w => w === 'window' || w === 'far')) M.windowReentries = (M.windowReentries || 0) + 1;
                else { M.teleports = (M.teleports || 0) + 1; if (tr.scope === 'hwd') M.teleportsHwd = (M.teleportsHwd || 0) + 1; (M.teleLog = M.teleLog || []).length < 30 && M.teleLog.push({ id, type: tr.info.icao || null, phase: tr.phase, scope: tr.scope, d: +d.toFixed(1), absent_s: +g.toFixed(1), why }); } } }
            V.absent = null; V.last = { t: td, x: D.x, y: D.y, z: D.z, gs: D.gs };
          } else if (V.last) { if (!V.absent) V.absent = { t: td, why: new Set() };
            V.absent.why.add(!D.valid ? (tr._far ? 'far' : 'invalid') : !tr.inView ? 'window' : tr.hidden ? 'hidden' : tr.fadeOut ? 'fadeOut' : tr.cutting ? 'cut' : tr.inHangarRest ? 'inHangar' : tr.airHidden ? 'airHidden' : tr._hideSeg ? 'hideSeg' : 'other'); }
        } }
      for (const tr of traffic.tracks.values()) {
        const id = idOf(tr.key); let E = EVER.get(id);
        if (!E) EVER.set(id, E = { id, first: now, last: now, scopes: [], phases: {}, cats: {}, parks: new Set(), parkKinds: new Set(), minD: 1e9, minAgl: 1e9, gF: 0, dF: 0, offline: OFF.has(tr.key), masked: false, type: null, cls: null, ecat: null, maxGsA: 0, maxGsG: 0, removed: false, label: null });
        E.last = now; if (tr.ident) { E.type = tr.ident.icaoType || E.type; E.ecat = tr.ident.category || E.ecat; E.masked = E.masked || !!tr.ident.masked; E.labelTypeOnly = tr.ident.masked ? (tr.ident.label === (tr.ident.icaoType || 'Aircraft') || tr.ident.label === 'Aircraft') : null; E.maskedClean = tr.ident.masked ? !(tr.ident.reg || tr.ident.callsign || tr.ident.operator) : null; }
        if (tr.dims) E.cls = tr.dims.cls; if (tr.vehicle) E.vehicle = true;
        if (!E.scopes.length || E.scopes[E.scopes.length - 1][0] !== tr.scope) E.scopes.push([tr.scope, ts]);
        if (tr.removed) { E.removed = true; continue; }
        const D = tr.disp;
        if (!D.valid || !(D.alpha > 0.5) || !tr.inView || tr.hidden) { prev.delete(id); continue; }
        drawn++; E.dF++; E.phases[tr.phase] = (E.phases[tr.phase] || 0) + 1; const cat = T.category(tr); E.cats[cat] = (E.cats[cat] || 0) + 1;
        const gy = site.groundY(D.x, D.z), agl = (D.y - gy) / 0.3048, dARP = Math.hypot(D.x, D.z);
        E.minD = Math.min(E.minD, dARP); if (!D.ground) E.minAgl = Math.min(E.minAgl, agl);
        if (tr.park && tr.park.spotId) { E.parks.add(tr.park.spotId); E.parkKinds.add(tr.park.kind); }
        const ctx = { id, type: E.type, cls: E.cls, phase: tr.phase, t: ts };
        const Tm = tr.dims;
        if (D.ground && Tm && !tr.vehicle) {
          E.gF++;
          const dy = Math.abs(D.y - gy); if (dy > 0.3) M.yErr++; M.yErrMax = Math.max(M.yErrMax, dy);
          const Sm = G.samples(Tm, D.x, D.z, D.hdg);
          if (Tm.cls === 'heli') { M.heliGround++; if (Sm.gear.some(g => !PAV(g[0], g[1]))) M.heliUnpaved++; }
          else {
            M.groundFW++;
            if (Sm.gear.some(g => !site.paved(g[0], g[1]))) M.offSite++;
            if (Sm.gear.some(g => !PAV(g[0], g[1]))) { if (M.offLog.length < 30 && M.offPave % 5 === 0) M.offLog.push({ ...ctx, x: +D.x.toFixed(1), z: +D.z.toFixed(1), gs: +D.gs.toFixed(1), route: !!D.route, hdg: Math.round(D.hdg), park: tr.park ? tr.park.kind : null, gearOff: Sm.gear.filter(g => !PAV(g[0], g[1])).length }); M.offPave++; if (D.gs > 0.5) M.offPaveMoving++; else M.offPaveStill++; if (D.route) M.offPaveRoute++; M.offTracks.add(id); const c = Math.round(D.x / 50) * 50 + ',' + Math.round(D.z / 50) * 50; M.offCells[c] = (M.offCells[c] || 0) + 1; }
            const door = tr.park && tr.park.spotId && (parking.byId.get(tr.park.spotId) || {}).door;
            if (Sm.fus.some(p => site.building(p[0], p[1]))) { if (door) M.inBldDoor++; else { if (M.bldLog.length < 20 && M.inBld % 5 === 0) M.bldLog.push({ ...ctx, x: +D.x.toFixed(1), z: +D.z.toFixed(1), gs: +D.gs.toFixed(1), route: !!D.route, park: tr.park ? (tr.park.spotId || tr.park.kind) : null }); M.inBld++; const c = tr.phase + '@' + Math.round(D.x / 20) * 20 + ',' + Math.round(D.z / 20) * 20; M.bldCells[c] = (M.bldCells[c] || 0) + 1; } }
          }
          const B = G.bodyOf(Tm, D.x, D.z, D.hdg); B.id = id; B.gs = D.gs; B.ctx = { ...ctx, x: +D.x.toFixed(1), z: +D.z.toFixed(1), gs: +D.gs.toFixed(1), route: !!D.route, span: Tm.span, L: Tm.L }; gnd.push(B);
        } else if (!D.ground) {
          M.air++; if (D.y < gy - 0.3) { M.belowGround++; M.belowGroundMax = Math.max(M.belowGroundMax, gy - D.y); }
          // the altitude the list / labels / card print (tr.last.altB = the NEWEST report) vs the reported altitude at the
          // display time (interpolated between the fixes around it): how far ahead of the drawn aircraft the printed value is
          if (tr.last && tr.last.altB != null && M.samples % 10 === 0) { const tD = now - traffic.delay, F = tr.fx; let k = F.length - 1; while (k > 0 && F[k].t > tD) k--;
            const a = F[k], b = F[Math.min(F.length - 1, k + 1)];
            if (a && b && a.altB != null && b.altB != null && a.t <= tD) { const u = b.t > a.t ? Math.min(1, Math.max(0, (tD - a.t) / (b.t - a.t))) : 0; const altD = a.altB + (b.altB - a.altB) * u; const dA = Math.abs(tr.last.altB - altD);
              DIST.a_label_dalt.push(dA); DIST.a_label_lead.push((tr.lastFixT - tD) / 1000); if (dA > 200) EXC.label_alt200++; note('label_dalt_ft', dA, ctx); } }
          air.push({ id, x: D.x, y: D.y, z: D.z, L: Tm ? Math.max(Tm.L || 8, Tm.span || 8) : 10 });
        }
        // kinematics of the drawn body (as P3's harness, on the app's own frames, dt = engine time between samples)
        const p = prev.get(id);
        if (kin && p && p.alpha > 0.99 && D.alpha > 0.99 && p.ground === D.ground) {
          M.kinPairs++;
          const dxy = Math.hypot(D.x - p.x, D.z - p.z), v = D.gs, aL = (D.gs - p.gs) / dt;
          const dh = ((D.hdg - p.hdg + 540) % 360) - 180, w = dh / dt, aLat = v * w * Math.PI / 180;
          if (dxy > Math.max(v, p.gs) * dt * 1.5 + 2) { M.jumps++; note('jump_m', dxy, ctx); }
          const vx1 = (D.x - p.x) / dt, vz1 = (D.z - p.z) / dt, sp1 = Math.hypot(vx1, vz1);
          if (p.vx != null && sp1 > 1 && Math.hypot(p.vx, p.vz) > 1) { const ax = (vx1 - p.vx) / dt, az = (vz1 - p.vz) / dt; const pl = Math.abs(ax * vz1 - az * vx1) / sp1;
            if (D.ground) { DIST.g_plat.push(pl); if (pl > 3) EXC.g_plat3++; note('g_plat', pl, ctx); const crab = Math.abs(((Math.atan2(vx1, -vz1) * 180 / Math.PI - D.hdg) % 360 + 540) % 360 - 180); DIST.g_crab.push(crab); if (crab > 10 && sp1 > 2) EXC.g_crab10++; }
            else { DIST.a_plat.push(pl); if (pl > 6) EXC.a_plat6++; note('a_plat', pl, ctx); } }
          const kt = v / 0.514444;
          if (D.ground) {
            E.maxGsG = Math.max(E.maxGsG, kt); DIST.g_gs.push(kt); note('g_gs_kt', kt, ctx);
            if (['taxi', 'runway_taxi', 'parked', 'hold_short', 'runup', 'line_up', 'hangared'].includes(tr.phase) && kt > 35) { EXC.taxi_fast++; note('taxi_kt', kt, ctx); }
            if (v > 0.5 || p.gs > 0.5) { DIST.g_along.push(Math.abs(aL)); DIST.g_w.push(Math.abs(w)); }
            const roll = Math.max(v, p.gs) > 10; if (!roll && Math.abs(aL) > 3) EXC.g_along3++; if (roll && Math.abs(aL) > 6) EXC.roll_along6++; if (Math.abs(aLat) > 3) EXC.g_lat3++; if (Math.abs(w) > 30) EXC.g_w30++;
            note('g_along', Math.abs(aL), ctx); note('g_w', Math.abs(w), ctx);
          } else {
            E.maxGsA = Math.max(E.maxGsA, kt); DIST.a_gs.push(kt); note('a_gs_kt', kt, ctx);
            if (kt > 250 && agl < 3000) { EXC.any_air_fast++; }
            if (['single_hw', 'single_lw', 'heli', 'glider', 'ultralight'].includes(E.cls) && kt > 200) { EXC.ga_air_fast++; note('ga_air_kt', kt, ctx); }
            DIST.a_along.push(Math.abs(aL)); DIST.a_w.push(Math.abs(w)); const vs = D.vs / 0.3048 * 60; DIST.a_vs.push(Math.abs(vs));
            if (Math.abs(aLat) > 6) EXC.a_lat6++; if (Math.abs(w) > 25) EXC.a_w25++; if (Math.abs(vs) > (E.cls === 'jet' ? 6000 : 2500)) EXC.a_vs_lim++;
            note('a_along', Math.abs(aL), ctx); note('a_w', Math.abs(w), ctx); note('a_vs_fpm', Math.abs(vs), ctx);
          }
        }
        { const q = prev.get(id); prev.set(id, { x: D.x, z: D.z, hdg: D.hdg, gs: D.gs, ground: D.ground, alpha: D.alpha, vx: q && kin ? (D.x - q.x) / dt : null, vz: q && kin ? (D.z - q.z) / dt : null }); }
      }
      M.drawnSum += drawn;
      for (let i = 0; i < gnd.length; i++) for (let j = i + 1; j < gnd.length; j++) { const A = gnd[i], B = gnd[j]; if (Math.hypot(A.x - B.x, A.z - B.z) > 80) continue; if (!G.overlaps(A, B, 0)) continue;
        const pa = A.gs < 0.3, pb = B.gs < 0.3, k = pa && pb ? 'parked' : pa || pb ? 'mixed' : 'moving'; M.ovl[k]++; if (M.ovlLog.length < 20 && M.ovl[k] % 5 === 1) M.ovlLog.push({ k, a: A.ctx, b: B.ctx, d: +Math.hypot(A.x - B.x, A.z - B.z).toFixed(1), t: ts }); M.ovlPairs.add([A.id, B.id].sort((a, b) => a - b).join('|') + ':' + k); }
      for (let i = 0; i < air.length; i++) for (let j = i + 1; j < air.length; j++) { const A = air[i], B = air[j]; const dh = Math.hypot(A.x - B.x, A.z - B.z); if (dh < (A.L + B.L) / 2 && Math.abs(A.y - B.y) < 5) { M.airProx++; M.airProxPairs.add(A.id + '|' + B.id); } }
    }
    // 10-Hz engine driver (SwiftShader renders this app at 0.6-2 fps, so the harness pauses the render loop and steps the
    // app's own engine objects in the app's frame order - traffic.update -> physics.resolve - at 10 Hz, as a device at
    // >= 10 fps would; frames are rendered on demand for the UI refresh and the screenshots)
    const physics = H.physics; let lastStep = null;
    function step() { const now = Date.now(); const dt = lastStep != null ? Math.min((now - lastStep) / 1000, 0.1) : 0.1; lastStep = now;
      const t = performance.now(); if (lastRaf != null) raf.push(t - lastRaf); lastRaf = t;
      try { if (R.drive) { traffic.update(now, dt); physics.resolve(traffic, dt); } sample(); } catch (e) { R.err = String(e && e.stack || e).slice(0, 400); } }
    const pct = (a, q) => { if (!a.length) return null; const s = Float64Array.from(a).sort(); return +s[Math.min(s.length - 1, Math.floor(q * s.length))].toFixed(2); };
    const amax = (a) => { let m = -Infinity; for (const v of a) if (v > m) m = v; return a.length ? +m.toFixed(2) : null; };
    const dsum = (a) => ({ n: a.length, p50: pct(a, 0.5), p90: pct(a, 0.9), p99: pct(a, 0.99), max: amax(a) });
    const R = window.__RUN = {
      ids, EVER, M, DIST, EXC, MAX, raf, lastNow: null, drive: true,
      timeline() { const c = H.qa.counts(); const tr = [...traffic.tracks.values()].filter(t => !t.removed);
        const drawnCats = {}; for (const t of tr) { if (!(t.disp.valid && t.inView && !t.hidden && t.disp.alpha > 0.5)) continue; const k = T.category(t); drawnCats[k] = (drawnCats[k] || 0) + 1; }
        const tabs = {}; document.querySelectorAll('#panel .tabs button').forEach(b => tabs[b.dataset.tab] = +(b.querySelector('b') || {}).textContent || 0);
        return { wall: Date.now(), scene: sceneISO(), phases: c.phases, total: c.total, scope: c.scope, drawn: c.drawn, tracks: c.tracks, drawnCats, tabs, spotsOccupied: c.spotsOccupied, events: c.events, frameMs: c.frameMs, scale: c.scale, render: c.render, delayS: c.delayS,
          phaseline: document.querySelector('#phaseline').textContent, rwy: document.querySelector('#rwystats').textContent, status: document.querySelector('#status').textContent.trim(), atcChip: (document.querySelector('#btn-atc') || {}).textContent, clock: document.querySelector('#clock').textContent,
          heap: performance.memory ? Math.round(performance.memory.usedJSHeapSize / 1e6) : null, physics: c.physics }; },
      // D1 / key scan of everything the DOM shows (text and attribute values). Returns counts only.
      domScan(leak, ctrl) {
        const txt = (document.body.innerText || '').toUpperCase();
        const attrs = []; document.querySelectorAll('*').forEach(el => { for (const a of el.attributes) attrs.push(a.value); }); const at = attrs.join(' \n ').toUpperCase();
        const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); const wb = (s) => new RegExp('(^|[^A-Z0-9])' + esc(s) + '($|[^A-Z0-9])');
        const leakHit = (leak || []).filter(s => wb(s).test(txt) || wb(s).test(at)).length;
        const ctrlHit = (ctrl || []).filter(s => wb(s).test(txt)).length;
        const keys = [...ids.keys()].filter(k => typeof k === 'string' && k.length >= 6); const low = (txt + ' ' + at).toLowerCase();
        const keyHit = keys.filter(k => new RegExp('(^|[^a-z0-9])' + esc(k.toLowerCase()) + '($|[^a-z0-9])').test(low)).length;
        const media = document.querySelectorAll('audio, video, iframe, embed, object').length;
        const sceneOpen = (() => { const h = +new Date(H.qa.sceneTime()).toLocaleString('en-US', { timeZone: 'America/Los_Angeles', hour: 'numeric', hour12: false }) % 24; return h >= 7 && h < 21; })();
        const towerClosedText = (txt.match(/TOWER CLOSED/g) || []).length;
        const lbl = [...document.querySelectorAll('#labels > div')].filter(e => e.style.display !== 'none').length;
        return { leakStrings: (leak || []).length, leakHit, ctrlStrings: (ctrl || []).length, ctrlHit, keys: keys.length, keyHit, media, sceneOpen, towerClosedText, labelsShown: lbl, rows: document.querySelectorAll('#list .row').length, typeOnlyRows: document.querySelectorAll('#list .row .d1').length };
      },
      // select every drawn aircraft in turn and scan its card
      cardScan(leak) {
        const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); const wb = (s) => new RegExp('(^|[^A-Z0-9])' + esc(s) + '($|[^A-Z0-9])');
        const out = { cards: 0, masked: 0, maskedWithheld: 0, maskedLeak: 0, leakHit: 0, unmaskedWithReg: 0, towerRowOpen: 0, towerRowClosed: 0, withPark: 0, withRunway: 0, keyHit: 0, inf: 0 };
        const keys = [...ids.keys()].filter(k => typeof k === 'string' && k.length >= 6);
        for (const t of H.qa.tracks().filter(t => t.valid && t.inView && !t.hidden)) {
          H.qa.select(t.id, false); const C = document.querySelector('#card'); if (!C || C.hidden) continue; out.cards++;
          const html = C.innerHTML, tx = C.innerText.toUpperCase();
          const lh = (leak || []).filter(s => wb(s).test(tx) || wb(s).test(html.toUpperCase())).length; out.leakHit += lh;
          if (t.masked) { out.masked++; if (/Identity withheld/.test(html) && /withheld \(LADD/.test(html)) out.maskedWithheld++; if (lh) out.maskedLeak++; }
          else if (/<dt>Registration<\/dt><dd class="mono">(?!—)/.test(html)) out.unmaskedWithReg++;
          if (/<dt>Tower<\/dt><dd>Open/.test(html)) out.towerRowOpen++; if (/<dt>Tower<\/dt><dd>Closed/.test(html)) out.towerRowClosed++;
          if (/<dt>Parking<\/dt>/.test(html)) out.withPark++; if (/<dt>Runway<\/dt>/.test(html)) out.withRunway++; if (/class="inf"/.test(html)) out.inf++;
          const low = html.toLowerCase(); out.keyHit += keys.filter(k => low.includes(k.toLowerCase())).length;
        }
        H.select(null); return out;
      },
      // WATCH_TYPE: the one track of an ICAO type: is its fuselage inside a building footprint now? (app qa id for the camera)
      watch(ty) { for (const tr of traffic.tracks.values()) { if (!tr.ident || tr.ident.icaoType !== ty || !tr.disp.valid || tr.removed || !tr.dims) continue; const D = tr.disp;
          const Sm = G.samples(tr.dims, D.x, D.z, D.hdg); const inB = D.ground && Sm.fus.some(p => site.building(p[0], p[1]));
          const q = H.qa.tracks().filter(t => t.type === ty).sort((a, b) => Math.hypot(a.x - D.x, a.z - D.z) - Math.hypot(b.x - D.x, b.z - D.z))[0];
          return { qid: q ? q.id : null, inBld: inB, x: +D.x.toFixed(1), z: +D.z.toFixed(1), phase: tr.phase, gs: +D.gs.toFixed(1), route: !!D.route, hidden: tr.hidden, scene: sceneISO() }; } return null; },
      // a track that still carries a parking spot while it is on a runway or airborne (stale park record): app qa id
      stalePark() { for (const tr of traffic.tracks.values()) { if (tr.removed || !tr.park || !tr.park.spotId || !tr.disp.valid || !tr.inView) continue;
          if (!['takeoff_roll', 'initial_climb', 'upwind', 'crosswind', 'downwind', 'climb', 'departure'].includes(tr.phase) && tr.disp.ground) continue;
          const D = tr.disp; const q = H.qa.tracks().filter(t => t.park && t.park.spot === tr.park.spotId)[0]; const s = parking.byId.get(tr.park.spotId);
          return { qid: q ? q.id : null, phase: tr.phase, ground: D.ground, gs: +D.gs.toFixed(1), dSpot: s ? Math.round(Math.hypot(D.x - s.x, D.z - s.z)) : null, occupied: parking.occ.get(tr.park.spotId) === tr.key, scene: sceneISO() }; } return null; },
      // aircraft of interest for close-ups (opaque ids)
      pick() { const L = H.qa.tracks().filter(t => t.valid && t.inView && !t.hidden && t.drawn);
        const withD = L.map(t => { const q = traffic.tracks.get([...ids.entries()].find(e => e[1] === t.id)?.[0]); return { ...t, gs: q ? q.disp.gs : 0, y: q ? q.disp.y : 0 }; });
        const near = (t) => Math.hypot(t.x, t.z);
        const taxi = withD.filter(t => t.ground && t.gs > 2 && t.cls !== 'heli').sort((a, b) => near(a) - near(b))[0];
        const parked = withD.filter(t => t.ground && t.park && t.park.spot && t.gs < 0.3).sort((a, b) => near(a) - near(b))[0];
        const air = withD.filter(t => !t.ground && t.scope === 'hwd' && near(t) < 4000).sort((a, b) => near(a) - near(b))[0];
        const heli = withD.filter(t => t.cls === 'heli').sort((a, b) => near(a) - near(b))[0];
        const masked = withD.filter(t => t.masked && near(t) < 3000)[0] || withD.filter(t => t.masked)[0];
        return { taxi: taxi && taxi.id, parked: parked && parked.id, air: air && air.id, heli: heli && heli.id, masked: masked && masked.id }; },
      report(consoleTexts) {
        const tracks = [...EVER.values()].filter(E => E.dF > 0 || E.gF > 0);
        const scopeEnd = {}; for (const E of EVER.values()) { const s = E.scopes.length ? E.scopes[E.scopes.length - 1][0] : 'none'; scopeEnd[s] = (scopeEnd[s] || 0) + 1; }
        // D6: overflights / hwd by emitter category, type, geometry; offline HWD aircraft classified live
        const of = [...EVER.values()].filter(E => E.scopes.length && E.scopes[E.scopes.length - 1][0] === 'overflight');
        const hw = [...EVER.values()].filter(E => E.scopes.length && E.scopes[E.scopes.length - 1][0] === 'hwd');
        const byCat = (L) => L.reduce((m, E) => (m[E.ecat || 'none'] = (m[E.ecat || 'none'] || 0) + 1, m), {});
        const byType = (L) => L.reduce((m, E) => (m[E.type || '?'] = (m[E.type || '?'] || 0) + 1, m), {});
        const upgraded = [...EVER.values()].filter(E => { const s = E.scopes.map(q => q[0]); const i = s.indexOf('overflight'); return i >= 0 && s.indexOf('hwd', i) > i; }).length;
        const downgraded = [...EVER.values()].filter(E => { const s = E.scopes.map(q => q[0]); const i = s.indexOf('hwd'); return i >= 0 && s.indexOf('overflight', i) > i; }).length;
        const ofLowNear = of.filter(E => E.minD < 1500 && E.minAgl < 500 && E.dF > 0).map(E => ({ id: E.id, type: E.type, cls: E.cls, ecat: E.ecat, minD: Math.round(E.minD), minAgl: Math.round(E.minAgl), gF: E.gF }));
        const ofGround = of.filter(E => E.gF > 0 && E.cls !== 'heli').map(E => ({ id: E.id, type: E.type, gF: E.gF }));
        const hwFar = hw.filter(E => E.minD > 4000 && E.gF === 0 && E.dF > 0).map(E => ({ id: E.id, type: E.type, ecat: E.ecat, minD: Math.round(E.minD), minAgl: Math.round(E.minAgl) }));
        const airlinerHwd = hw.filter(E => ['A3', 'A4', 'A5'].includes(E.ecat)).map(E => ({ id: E.id, type: E.type, ecat: E.ecat, gF: E.gF, parks: E.parks.size }));
        const offl = [...EVER.values()].filter(E => E.offline); const offlScope = offl.reduce((m, E) => { const s = E.scopes.length ? E.scopes[E.scopes.length - 1][0] : 'none'; m[s] = (m[s] || 0) + 1; return m; }, {});
        const offlOver = offl.filter(E => E.scopes.length && E.scopes[E.scopes.length - 1][0] !== 'hwd').map(E => ({ id: E.id, type: E.type, ecat: E.ecat, scopes: E.scopes.map(s => s.join('@')).join(' > '), minD: Math.round(E.minD), minAgl: Math.round(E.minAgl), gF: E.gF, dF: E.dF }));
        // events (opaque ids; no key)
        const ev = traffic.events.map(e => ({ kind: e.kind, type: e.type, rwy: e.rwy || e.runway || null, src: e.src, spot: e.spot || null, cls: e.cls || null, id: e.key != null ? (ids.get(e.key) || idOf(e.key)) : null }));
        const evCounts = {}; for (const e of ev) evCounts[e.type] = (evCounts[e.type] || 0) + 1;
        const evByRwy = {}; for (const e of ev) if (e.rwy) { const k = e.type + ' ' + e.rwy; evByRwy[k] = (evByRwy[k] || 0) + 1; }
        const overEv = ev.filter(e => e.id != null && ['takeoff', 'full_stop_landing', 'touch_and_go', 'stop_and_go', 'lift_off', 'touch_down', 'park'].includes(e.type) && (() => { const E = EVER.get(e.id); return E && E.scopes.length && E.scopes[E.scopes.length - 1][0] === 'overflight'; })()).length;
        // parking
        const parks = ev.filter(e => e.type === 'park'); const spotOf = (s) => parking.byId.get(s) || {};
        const park = { events: parks.length, matched: parks.filter(e => e.spot).length, unspotted: parks.filter(e => !e.spot).length, byKind: {}, byZone: {}, heliOnFixed: 0, fixedOnHelipad: 0, unpark: ev.filter(e => e.type === 'unpark').length, hangarIn: ev.filter(e => e.type === 'hangar_in').length, hangarOut: ev.filter(e => e.type === 'hangar_out').length, spotsUsed: new Set(parks.filter(e => e.spot).map(e => e.spot)).size };
        for (const e of parks.filter(e => e.spot)) { const s = spotOf(e.spot); park.byKind[s.kind] = (park.byKind[s.kind] || 0) + 1; park.byZone[s.zone || '-'] = (park.byZone[s.zone || '-'] || 0) + 1; if (s.kind === 'helipad' && e.cls !== 'heli') park.fixedOnHelipad++; }
        // current parked tracks vs their spot (distance from the drawn pose to the spot's reference point)
        const occ = [...parking.occ.entries()]; const dup = occ.length - new Set(occ.map(o => o[1])).size;
        const parkedNow = []; for (const tr of traffic.tracks.values()) { if (!tr.park || !tr.park.spotId || tr.removed) continue; const s = parking.byId.get(tr.park.spotId); if (!s) continue; const D = tr.disp; const q = parking.refPoint(s, { x: D.x, z: D.z, hdg: D.hdg, ant: null }, tr.dims); parkedNow.push({ id: idOf(tr.key), type: tr.ident && tr.ident.icaoType, cls: tr.dims && tr.dims.cls, kind: s.kind, zone: s.zone, src: s.src, d_m: +Math.hypot(q[0] - s.x, q[1] - s.z).toFixed(1), span: tr.dims && tr.dims.span, cap: s.cap, inside: !!tr.park.inside }); }
        // D1 at the engine level
        const all = [...EVER.values()]; const d1 = { tracks: all.length, masked: all.filter(E => E.masked).length, maskedLabelTypeOnly: all.filter(E => E.masked && E.labelTypeOnly).length, maskedClean: all.filter(E => E.masked && E.maskedClean).length };
        const keys = [...ids.keys()].filter(k => typeof k === 'string' && k.length >= 6);
        const logKeyHits = (consoleTexts || []).filter(t => keys.some(k => t.toLowerCase().includes(k.toLowerCase()))).length;
        const rf = raf.slice(30); const fps = rf.length ? 1000 / (rf.reduce((a, b) => a + b, 0) / rf.length) : null;
        return { M: { ...M, ovlPairs: M.ovlPairs.size, airProxPairs: M.airProxPairs.size, offTracks: M.offTracks.size, offCells: Object.entries(M.offCells).sort((a, b) => b[1] - a[1]).slice(0, 8), bldCells: Object.entries(M.bldCells).sort((a, b) => b[1] - a[1]).slice(0, 8) },
          DIST: Object.fromEntries(Object.entries(DIST).map(([k, a]) => [k, dsum(a)])), EXC, MAX,
          stepIntervals: { n: rf.length, p50: pct(rf, 0.5), p90: pct(rf, 0.9), p99: pct(rf, 0.99), max: amax(rf), hz: fps && +fps.toFixed(1) },
          scopeEnd, overflight: { n: of.length, byCat: byCat(of), byType: byType(of), lowNear: ofLowNear, withGroundFrames: ofGround, runwayOrParkEvents: overEv }, hwd: { n: hw.length, byCat: byCat(hw), byType: byType(hw), far: hwFar, airliner: airlinerHwd },
          upgraded, downgraded, offline: { n: offl.length, scopeEnd: offlScope, notHwd: offlOver },
          events: { n: ev.length, byType: evCounts, byRwy: evByRwy }, park, parkedNow, occDup: dup, d1, logKeyHits, counters: traffic.counters, physicsStats: H.physics.stats, err: R.err || null,
          tracksDrawn: tracks.length, types: byType(tracks) };
      },
    };
    R.iv = setInterval(step, 100);
  }, REF ? REF.offline_hex : []);
  await S(() => HWD.qa.pause(true));

  // ---- helpers
  const TL = [], SCANS = [], CARDS = [], SHOTS = [], WATCHLOG = []; const WATCH = process.env.WATCH_TYPE || null; let watchShots = 0; const STALE = []; let staleDone = false;
  const refreshUI = async (ms = 3500) => { await S(() => HWD.qa.pause(false)); await page.waitForTimeout(ms); await S(() => HWD.qa.pause(true)); };
  const render = async (n = 2) => { for (let i = 0; i < n; i++) await S(() => HWD.frameNow()); };
  const fbShot = async (name) => { const url = await S(() => HWD.qa.shot(2)); const f = pngPath(name); fs.writeFileSync(f, Buffer.from(url.split(',')[1], 'base64')); SHOTS.push(path.basename(f)); };
  const domShot = async (name) => { await render(2); const f = pngPath(name); await page.screenshot({ path: f }); SHOTS.push(path.basename(f)); };
  const scan = async (label) => { const r = await S(([l, c]) => window.__RUN.domScan(l, c), [REF ? REF.leak : [], REF ? REF.ctrl : []]); r.at = label; r.scene = (await S(() => new Date(HWD.qa.sceneTime()).toISOString().slice(11, 19))); SCANS.push(r); return r; };
  const shotSet = async (m) => {
    const tag = 'm' + String(m).replace('.', '_');
    await refreshUI();
    for (const v of await S(() => HWD.qa.views())) { await S((v) => HWD.qa.view(v), v); await page.waitForTimeout(300); await domShot(v + '_' + tag); }
    await S(() => HWD.qa.view('overview')); await page.waitForTimeout(600); await fbShot('overview_clean_' + tag);
    const pk = await S(() => window.__RUN.pick()); log('pick', JSON.stringify(pk));
    for (const [k, dist, pitch] of [['parked', 45, 22], ['taxi', 55, 16], ['air', 120, 8], ['heli', 45, 18]]) {
      if (pk[k] == null) continue; const ok = await S(([id, d, p]) => HWD.qa.aircraft(id, d, p), [pk[k], dist, pitch]); if (!ok) continue; await page.waitForTimeout(900); await domShot('close_' + k + '_' + tag); await fbShot('close_' + k + '_clean_' + tag);
    }
    if (pk.masked != null) { await S((id) => HWD.qa.select(id, false), pk.masked); await page.waitForTimeout(700); await domShot('card_masked_' + tag); CARDS.push({ at: tag, masked: await S(() => document.querySelector('#card').innerText.split('\n').filter(l => !/^(Speed|Data|Altitude)/.test(l)).slice(0, 4).join(' | ')) }); await S(() => HWD.select(null)); }
    if (pk.air != null) { await S((id) => HWD.qa.select(id, true), pk.air); await refreshUI(4000); await domShot('follow_' + tag); await S(() => HWD.select(null)); }
    await S(() => HWD.qa.view('overview')); await page.waitForTimeout(400);
  };

  // ---- the run
  const simMs = SIM_MIN * 60e3; const shotQ = SHOT_AT.slice().sort((a, b) => a - b);
  const startWall = Date.now(); let nextTL = 0, nextScan = 1e3;
  log(`running ${SIM_MIN} min (wall) on ${target}`);
  while (Date.now() - startWall < simMs) {
    const el = Date.now() - startWall;
    if (el >= nextTL) { await refreshUI(); const r = await S(() => window.__RUN.timeline()); TL.push(r); nextTL = Math.max(nextTL + TL_EVERY_S * 1e3, Date.now() - startWall + 20e3); log(`tl ${(el / 60e3).toFixed(1)}m scene ${r.scene} drawn ${r.drawn} tracks ${r.tracks} phases ${JSON.stringify(r.phases)} | ${r.phaseline} | ${r.rwy} | frameMs ${r.frameMs}`); }
    if (el >= nextScan) { const r = await scan('t' + Math.round(el / 1e3)); nextScan = Math.max(nextScan + SCAN_EVERY_S * 1e3, Date.now() - startWall + 20e3); log('scan', JSON.stringify(r)); }
    if (WATCH && watchShots < 3) { const w = await S((ty) => window.__RUN.watch(ty), WATCH);
      if (w && w.qid != null) { await S(([id, d, pt]) => HWD.qa.aircraft(id, d, pt), [w.qid, +(process.env.WATCH_DIST || 60), +(process.env.WATCH_PITCH || 38)]);
        if (w.inBld) { await domShot('clip_' + watchShots); await fbShot('clip_clean_' + watchShots); watchShots++; log('clip', JSON.stringify(w)); WATCHLOG.push(w); } } }
    if (!staleDone) { const w = await S(() => window.__RUN.stalePark());
      if (w && w.qid != null && w.dSpot > 300) { STALE.push(w); await S((id) => HWD.qa.select(id, true), w.qid); await refreshUI(3000); await domShot('card_stalepark'); await S(() => HWD.select(null)); staleDone = true; log('stalepark', JSON.stringify(w)); } }
    if (shotQ.length && el >= shotQ[0] * 60e3) { const m = shotQ.shift(); log('shots at', m, 'min'); await shotSet(m); const c = await S((l) => window.__RUN.cardScan(l), REF ? REF.leak : []); c.at = m; CARDS.push(c); log('cards', JSON.stringify(c)); }
    await page.waitForTimeout(1000);
  }
  // ---- sheets: About, ATC, statistics (DOM)
  await S(() => HWD.qa.view('overview')); await refreshUI();
  await S(() => document.querySelector('#btn-about').click()); await page.waitForTimeout(500); await domShot('about');
  const aboutTxt = await S(() => document.querySelector('#about').innerText);
  const aboutLinks = await S(() => [...document.querySelectorAll('#about a[href]')].map(a => a.href));
  await S(() => document.querySelector('#btn-about').click());
  await S(() => document.querySelector('#btn-atc').click()); await page.waitForTimeout(500); await domShot('atc');
  const atc = await S(() => { const A = document.querySelector('#atc'); return { text: A.innerText, links: [...A.querySelectorAll('a[href]')].map(a => ({ href: a.getAttribute('href'), target: a.target, rel: a.rel })), media: document.querySelectorAll('audio, video, iframe, embed, object').length, chip: document.querySelector('#btn-atc').textContent, scene: new Date(HWD.qa.sceneTime()).toISOString() }; });
  await S(() => document.querySelector('#btn-atc').click());
  await S(() => document.querySelector('#phaseline').click()); await refreshUI(2500); await domShot('stats');
  const statsTxt = await S(() => { const e = document.querySelector('#rstats'); return e ? e.innerText.split('\n').filter(l => /runway|28L|28R|10L|10R|touch|movement|helicop|closed|interval|T&G|↑|↓/i.test(l)).slice(0, 14) : null; });
  await S(() => document.querySelector('#phaseline').click());
  const finalScan = await scan('final');
  // ---- About vs docs/ATTRIBUTION.md "Notices to show in the app" (each block, whitespace-normalised, markdown stripped)
  const attr = fs.readFileSync(path.resolve(process.env.ROOT || process.cwd(), 'docs', 'ATTRIBUTION.md'), 'utf8');
  const blk = attr.split('## Notices to show in the app')[1].split('\n## ')[0];
  const notices = blk.split(/\n>\s*\n/).map(b => b.split('\n').filter(l => l.startsWith('>')).map(l => l.replace(/^>\s?/, '')).join(' ').replace(/`/g, '').replace(/\s+/g, ' ').trim()).filter(Boolean);
  const norm = (s) => s.replace(/\s+/g, ' ').replace(/[‐-―]/g, '-').trim();
  const aboutN = norm(aboutTxt);
  const noticeCheck = notices.map(n => ({ start: n.slice(0, 48), found: aboutN.includes(norm(n)) }));
  const report = await S((c) => window.__RUN.report(c), CONS);
  const net = netSum();
  const out = { win: WIN, dev: DEV, mobile: MOBILE, target: target.replace(/:\d+\//, ':PORT/'), qs: QS, simMin: SIM_MIN, readyMs, info, net: { ready: { n: netReady.n, enc: netReady.enc, dec: netReady.dec }, end: net, biggest: big(), hosts: [...new Set(REQ.map(r => r.host))], identRequests: REQ.filter(r => r.ident).length, identMasked: REQ.filter(r => r.masked).length },
    timeline: TL, scans: SCANS, cards: CARDS, atc: { ...atc, text: atc.text.slice(0, 900) }, about: { notices: noticeCheck, links: aboutLinks.length, liveatc: aboutLinks.filter(h => /liveatc/.test(h)), chars: aboutTxt.length }, stats: statsTxt, finalScan, report,
    watch: WATCHLOG, stalePark: STALE, errors: errors.slice(0, 40), consoleLines: CONS.length, shots: SHOTS, ref: REF ? { leak: REF.leak.length, ctrl: REF.ctrl.length, offline_counts: REF.offline_counts, offline_hex: REF.offline_hex.length, from: REF.from, until: REF.until } : null };
  fs.writeFileSync(path.join(OUT, `run_${WIN}_${DEV}.json`), JSON.stringify(out, null, 1));
  log('wrote', `run_${WIN}_${DEV}.json`, 'errors', errors.length, 'shots', SHOTS.length);
};
