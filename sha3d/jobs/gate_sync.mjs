// Phase 3 package E: the gate and time adapter in the page (docs/phase3/gates_time.md). Run through the harness:
//   SOFTGL=1 node livetest.mjs jobs/gate_sync.mjs                       (renders into sha3d/out/phase3/E/, ~3-4 min)
//   SOFTGL=1 RENDERS=0 node livetest.mjs jobs/gate_sync.mjs             (checks only)
// Env: CHECK_N (stands of the boot check, default 8), CHECK_KEYS (type keys per stand, default 3), RENDERS=0, STAND (233),
// REMOTE (404), T (environment time, default 2026-11-14T03:00:00Z = 11:00 local). Output never goes to docs/ directly:
// the composites for docs/phase3/gates_time_*.png are made from these renders by the lead / tools (at most 2).
// What it does, in the page (window.SHA), with traffic OFF (the harness default) and no DEBUG park:
//  1. boot check: js/live/gate_sync.js check() re-measures CHECK_N sampled stands x CHECK_KEYS type keys of
//     data/sha_gate_times.json on the live engine and compares (equal to 0.0 s expected: the same code and inputs);
//  2. attaches the adapter to a job-driven sim clock (window.__simT) and plays a turnaround at STAND (on-block, dock call
//     20 s later, docked; undock 40 min later at off-block - max(150 s, undock_s + 15 s); push) and one at the remote stand
//     REMOTE (stairs + bus; then cold), rendering the stand at fixed instants with a QA aircraft the job places itself at
//     the stop convention pose (LiveAircraft, as the DEBUG park places it; it is NOT traffic: there is none yet);
//  3. a backward scrub: from after the push back to the mid-docking instant (resetTo with the StandStates) - the render
//     must equal the forward one (mean absolute pixel difference reported) and no animation may hold a future time;
//  4. the full rebuild at 130 occupied stands in the browser (the build's own timer, GL uploads included) per single-stand
//     event; 5. the DEBUG park refused while the adapter is attached, allowed after detach; SHA.qa.pavedVec; 6. a clean
//     console (no error / warning during the job).
import fs from 'fs'; import path from 'path'; import { fileURLToPath } from 'url';
const HERE = path.dirname(fileURLToPath(import.meta.url));
export default async ({ page, shot, base, IDENTITY }) => {
  const OUTD = path.join(HERE, '..', 'out', 'phase3', 'E'); fs.mkdirSync(OUTD, { recursive: true });
  // HARNESS=1: the harness gates only (no app boot): what the page gets from /api/observed_elsewhere, /api/ping and a refs/
  // path. Prints availability and counts only, never a record (OD4).
  if (process.env.HARNESS) {
    await page.goto(base + 'data/sha_gate_times.json');
    const r = await page.evaluate(async ([day, B]) => { const j = async (u) => { const x = await fetch(u); let b = null; try { b = await x.json(); } catch (e) { } return { status: x.status, b }; };
      const oe = await j(B + 'api/observed_elsewhere?day=' + day); const ping = await j(B + 'api/ping'); const ref = await fetch(B + 'refs/cache/observed_elsewhere/SOURCES.json');
      const m = await j(B + 'api/metar?ids=ZSSS&format=json');
      const ID = await import(B + 'js/sim/identity.js'); const chk = oe.b && oe.b.available ? ID.checkOverlay(oe.b, { day }) : null;
      return { overlayCheck: chk ? { kept: chk.records.length, dropped: chk.dropped } : null, oe: { status: oe.status, available: oe.b ? oe.b.available : null, records: oe.b && Array.isArray(oe.b.records) ? oe.b.records.length : 0, synthetic: !!(oe.b && oe.b.synthetic), reason: oe.b && oe.b.reason },
        pingIdentityDays: ping.b && ping.b.features ? (ping.b.features.identity || null) && ping.b.features.identity.length : null, refsStatus: ref.status, harness: window.SHA_HARNESS || null, trafficDefault: window.SHA_TRAFFIC_DEFAULT,
        metar: Array.isArray(m.b) ? { n: m.b.length, receipt: m.b.filter(x => x.receiptTime).length, spanH: m.b.length > 1 ? +((m.b[0].obsTime - m.b[m.b.length - 1].obsTime) / 3600).toFixed(1) : 0 } : m.status };
    }, [process.env.OVERLAY_DAY || '2026-11-12', base]);
    console.log('harness gates:', JSON.stringify(r));
    return;
  }
  const con = { error: 0, warning: 0, list: [] };
  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') { if (/GPU stall|GL Driver|Automatic fallback|fonts.g/.test(m.text())) return; con[m.type()]++; con.list.push(m.type() + ': ' + m.text().slice(0, 240)); } });
  page.on('pageerror', e => { con.error++; con.list.push('pageerror: ' + e.message); });
  const t = process.env.T || '2026-11-14T03:00:00Z';
  await page.goto(base + 'live.html?fixedres=1&quality=high&t=' + encodeURIComponent(t));
  await page.waitForFunction(() => window.__shaReady || window.__shaError, null, { timeout: 0 });
  const err = await page.evaluate(() => window.__shaError || null); if (err) throw new Error(err);
  await page.evaluate(() => SHA.qa.hideUI(true));
  const frames = (n) => page.evaluate((n) => new Promise(r => { let k = 0; const f = () => { if (++k >= n) r(); else requestAnimationFrame(f); }; requestAnimationFrame(f); }), n);
  const STAND = process.env.STAND || '233', REMOTE = process.env.REMOTE || '404';
  const res = { checks: [] }; const ok = (name, cond, detail) => { res.checks.push({ name, ok: !!cond, detail }); console.log(`${cond ? 'PASS' : 'FAIL'} ${name}${detail ? ': ' + detail : ''}`); if (!cond) process.exitCode = 1; };

  // ---- 1. boot check (and the module set-up the later steps use)
  const boot = await page.evaluate(async ([n, k]) => {
    const GT = await (await fetch(new URL('data/sha_gate_times.json', location.href))).json();
    const M = await import(new URL('js/live/gate_sync.js', location.href).href);
    const sys = SHA.scene.gateSys; window.__gsM = M; window.__GT = GT;
    const gs = M.createGateSync(sys, sys.gates, { gateTimes: GT, check: false }); window.__gs = gs;
    const c = gs.check(n, k);
    return { check: c, traffic: sys.trafficRunning(), harness: window.SHA_HARNESS || null, trafficDefault: window.SHA_TRAFFIC_DEFAULT, inputs: GT.inputs_sha256_16, entries: GT.stats.entries };
  }, [+(process.env.CHECK_N || 8), +(process.env.CHECK_KEYS || 3)]);
  ok('harness: traffic off by default (window.SHA_TRAFFIC_DEFAULT false, engine on Date.now())', boot.trafficDefault === false && !boot.traffic, JSON.stringify(boot.harness));
  ok('boot check: the table agrees with the live engine on the sampled stands', boot.check.ok, `${boot.check.agree}/${boot.check.entries} entries equal on ${boot.check.stands.join(' ')} (max diff ${boot.check.maxDiffS} s, ${boot.check.ms} ms; table ${boot.inputs}, ${boot.entries} entries)${boot.check.mismatches.length ? ' ' + JSON.stringify(boot.check.mismatches.slice(0, 3)) : ''}`);

  // ---- 2. attach to a job-driven sim clock; QA aircraft helper
  const T0 = Date.UTC(2026, 10, 14, 3, 0, 0);
  const setup = await page.evaluate(async ([T0, S, R]) => {
    const gs = window.__gs, sys = SHA.scene.gateSys;
    window.__simT = T0; const a = gs.attach(() => window.__simT);
    const A = await import(new URL('js/live/aircraft.js', location.href).href); const MD = await import(new URL('js/live/models.js', location.href).href);
    const LK = await import(new URL('js/live/lookup.js', location.href).href); const LI = await import(new URL('js/env/aircraft_lights.js', location.href).href);
    const GSY = await import(new URL('js/live/gate_system.js', location.href).href); const TY = await import(new URL('js/aircraft/types.js', location.href).href);
    const byName = new Map(sys.gates.map(g => [g.name, g])); window.__qaAc = new Map();
    // a QA aircraft at the stand's stop convention pose (the DEBUG park formula: nose tip standTip, model origin xMain behind it)
    window.__place = async (name, icao) => { const g = byName.get(name); const m = A.TYPE_MODELS[icao]; const mk = m.m && MD.MODEL_SOURCES[m.m] ? m.m : null; const T = TY.TYPES[m.t];
      const tip = GSY.standTip(g, T, mk); const ac = new A.LiveAircraft(m.t, mk, LK.liveryForAirline(null), { id: 'qa-gate-sync-' + name, lod: 1, lodDist: 1800, shadowDist: 1600 });
      ac.pos = [tip[0] - g.dir[0] * ac.T.xMain, tip[1], tip[2] - g.dir[1] * ac.T.xMain]; ac.fwd = [g.dir[0], 0, g.dir[1]]; ac.gear = 1; ac.dirt = 0.35;
      Object.assign(ac.lightsOn, LI.aircraftLightStates({ phase: 'parked', ground: true, gs: 0, altAgl: 0, stale: false })); SHA.scene.add(ac); window.__qaAc.set(name, ac); await ac.ready;
      return { type: m.t, pose: { nose: [tip[0], tip[2]], dir: g.dir.slice() } }; };
    window.__unplace = (name) => { const ac = window.__qaAc.get(name); if (!ac) return; const i = SHA.scene.aircraft.indexOf(ac); if (i >= 0) SHA.scene.aircraft.splice(i, 1); window.__qaAc.delete(name); };
    window.__step = (t, evs = []) => { window.__simT = t; return gs.apply(evs, t); };
    const row = (n, k) => (window.__GT.stands[n] || {})[k] || null;
    return { attach: a, row: row(S, 'a320'), remoteBridge: !!byName.get(R).bridge };
  }, [T0, STAND, REMOTE]);
  ok('attach: the engine clock is the sim clock while traffic runs', setup.attach.ok, JSON.stringify(setup.attach).slice(0, 200));
  const dbg = await page.evaluate(async () => { const r = await SHA.qa.park('234', 'A320'); return r; });
  ok('the DEBUG park is refused while the adapter runs', dbg && dbg.ok === false, dbg && dbg.why);
  const R0 = setup.row; const dockS = R0[0], undockS = R0[1]; const lead = Math.max(150, undockS + 15);
  const tOn = T0 + 60e3, tD = tOn + 20e3, tU = tOn + 40 * 60e3, tP = tU + lead * 1000;
  const evs = [{ t: tD, kind: 'dock', stand: STAND, data: { typeKey: 'a320', icao: 'A320' } }, { t: tU, kind: 'undock', stand: STAND }, { t: tP, kind: 'pushstart', stand: STAND }];
  const st = (tt) => { const m = new Map(); const life = { typeKey: 'a320', icao: 'A320', tDock: tD, tUndock: tU, tPush: tP };
    if (tt >= tP) m.set(STAND, { state: 'empty', prev: life }); else if (tt >= tU) m.set(STAND, { state: 'early', since: tU, service: 'turn', ...life });
    else if (tt >= tD + dockS * 1000) m.set(STAND, { state: 'docked', since: tD + dockS * 1000, service: 'turn', ...life }); else if (tt >= tD) m.set(STAND, { state: 'docking', since: tD, service: 'turn', ...life });
    return [...m.entries()]; };
  const RENDER = process.env.RENDERS !== '0';
  const view = async () => { await page.evaluate((n) => SHA.qa.stand(n, 70, 1, 24), STAND); };   // (the named stand view of Phase 2: stand:233,-,70,1,24)
  const shots = [];
  const at = async (tt, name, label) => { const info = await page.evaluate(([tt, evs, S]) => { const done = window.__done || (window.__done = new Set()); const todo = evs.filter(e => e.t <= tt && !done.has(e.t + e.kind)); todo.forEach(e => done.add(e.t + e.kind));
      window.__step(tt, todo); const sys = SHA.scene.gateSys; const g = sys.gates.find(x => x.name === S); const a = sys.anims.get(g.id);
      return { ext: +sys.extension(g).toFixed(3), anim: a ? { to: a.to, k: +a.k.toFixed(3) } : null, acType: g.acType, early: !!g._early }; }, [tt, evs, STAND]);
    await frames(3); await page.evaluate(() => new Promise(r => setTimeout(r, 50))); await frames(2);
    const inf = await page.evaluate((S) => { const sys = SHA.scene.gateSys; const g = sys.gates.find(x => x.name === S); const a = sys.anims.get(g.id); const c = sys._chunks && sys._chunks.get(g.id);
      return { ext: +sys.extension(g).toFixed(3), anim: a ? { to: a.to, k: +a.k.toFixed(3) } : null, gse: c ? Object.values(c.veh).reduce((n, l) => n + l.length, 0) : null, pending: sys._gsePending ? sys._gsePending.size : 0 }; }, STAND);
    let f = null; if (RENDER) { f = await shot(path.relative(path.resolve(process.env.OUT || path.join(HERE, '..', 'out', 'live')), path.join(OUTD, name))); shots.push({ f, label }); }
    console.log(`  ${name}: t = ${((tt - tOn) / 1000).toFixed(0)} s after on-block; ${label}; extension ${inf.ext}${inf.anim ? ', animation to ' + inf.anim.to + ' at k ' + inf.anim.k : ''}, GSE ${inf.gse}`);
    return { ...info, ...inf, f };
  };
  const pl = await page.evaluate(async (S) => window.__place(S, 'A320'), STAND);
  await view();
  const s0 = await at(tOn + 5e3, 'e_233_1_onblock', 'on-block, bridge at rest');
  const s1 = await at(tD + 12e3 + Math.round((dockS - 12) * 400), 'e_233_2_docking', 'docking (40 % of the path)');
  const s2 = await at(tD + Math.ceil(dockS) * 1000 + 2e3, 'e_233_3_docked', 'docked, GSE placed');
  const s3 = await at(tU + Math.round(undockS * 500), 'e_233_4_undocking', 'undocking (half way)');
  const s4 = await at(tU + Math.ceil(undockS) * 1000 + 2e3, 'e_233_5_retracted', 'retracted before the push, GSE gone');
  ok('docking sequence at ' + STAND + ': rest -> docking -> docked with GSE -> undocking -> retracted, no GSE', s0.ext === 0 && s1.anim && s1.anim.to === 1 && s2.ext === 1 && !s2.anim && s2.gse > 0 && s3.anim && s3.anim.to === 0 && s4.ext === 0 && !s4.anim && s4.gse === 0,
    JSON.stringify({ s0: s0.ext, s1: s1.anim, s2: [s2.ext, s2.gse], s3: s3.anim, s4: [s4.ext, s4.gse] }));
  await page.evaluate((S) => window.__unplace(S), STAND);
  const s5 = await at(tP + 30e3, 'e_233_6_pushed', 'after the push start (aircraft removed by the job)');
  // ---- 3. backward scrub: back to the docking instant with resetTo, the same picture as the forward play
  await page.evaluate(async (S) => window.__place(S, 'A320'), STAND);
  const tBack = tD + 12e3 + Math.round((dockS - 12) * 400);
  const back = await page.evaluate(([tt, L, S]) => { window.__simT = tt; const r = window.__gs.resetTo(tt, new Map(L)); const sys = SHA.scene.gateSys;
    let future = 0; for (const a of sys.anims.values()) if (a.t0 - 12e3 > tt) future++; for (const g of sys.gates) if (g._parkHold && g._parkHold.until - 180e3 > tt) future++;
    const g = sys.gates.find(x => x.name === S); const a = sys.anims.get(g.id); return { r, future, anim: a ? { to: a.to, t0: a.t0, dur: a.dur } : null }; }, [tBack, st(tBack), STAND]);
  await frames(3); await page.evaluate(() => new Promise(r => setTimeout(r, 50))); await frames(2);
  let diff = null;
  if (RENDER) { const fb = await shot(path.relative(path.resolve(process.env.OUT || path.join(HERE, '..', 'out', 'live')), path.join(OUTD, 'e_233_7_scrub_back')));
    shots.push({ f: fb, label: 'backward scrub to the docking instant (resetTo)' });
    diff = await page.evaluate(async ([a, b]) => { const load = (src) => new Promise((r, j) => { const i = new Image(); i.onload = () => r(i); i.onerror = j; i.src = src; });
      const [A, B] = await Promise.all([load(a), load(b)]); const c = document.createElement('canvas'); c.width = A.width; c.height = A.height; const x = c.getContext('2d', { willReadFrequently: true });
      x.drawImage(A, 0, 0); const da = x.getImageData(0, 0, c.width, c.height).data; x.clearRect(0, 0, c.width, c.height); x.drawImage(B, 0, 0); const db = x.getImageData(0, 0, c.width, c.height).data;
      let s = 0, n = 0, big = 0; for (let i = 0; i < da.length; i += 4) { const d = (Math.abs(da[i] - db[i]) + Math.abs(da[i + 1] - db[i + 1]) + Math.abs(da[i + 2] - db[i + 2])) / 3; s += d; n++; if (d > 24) big++; }
      return { mean: +(s / n).toFixed(3), over24: big }; }, ['data:image/png;base64,' + fs.readFileSync(s1.f).toString('base64'), 'data:image/png;base64,' + fs.readFileSync(fb).toString('base64')]); }
  ok('backward scrub: resetTo rebuilds the mid-docking state (no future animation / hold; the same picture)', back.future === 0 && back.anim && back.anim.to === 1 && (!diff || diff.mean < 0.5),
    `resetTo ${JSON.stringify(back.r)}; animation ${JSON.stringify(back.anim)}; render vs forward: ${diff ? 'mean |d| ' + diff.mean + ' / 255, ' + diff.over24 + ' px > 24' : 'not rendered'}`);
  await page.evaluate((S) => window.__unplace(S), STAND);
  // the remote stand: stairs + bus while turning, none when cold
  await page.evaluate(([tt, S]) => { window.__simT = tt; window.__gs.resetTo(tt, new Map()); }, [tP + 60e3, STAND]);
  await page.evaluate(async (R) => window.__place(R, 'A320'), REMOTE);
  const tR = tP + 120e3;
  await page.evaluate(([tt, R]) => window.__step(tt, [{ t: tt, kind: 'onblock', stand: R, data: { typeKey: 'a320', icao: 'A320' } }]), [tR, REMOTE]);
  await page.evaluate((n) => SHA.qa.stand(n, 75, 1, 22), REMOTE);
  const veh = () => page.evaluate((R) => { const sys = SHA.scene.gateSys; const c = sys._chunks && sys._chunks.get(sys.gates.find(x => x.name === R).id); const o = {}; if (c) for (const [k, l] of Object.entries(c.veh)) if (l.length) o[k] = l.length; return o; }, REMOTE);
  await frames(4); const vTurn = await veh(); if (RENDER) { const f = await shot(path.relative(path.resolve(process.env.OUT || path.join(HERE, '..', 'out', 'live')), path.join(OUTD, 'e_404_1_turn'))); shots.push({ f, label: 'remote stand, turn: stairs + bus + GSE' }); }
  await page.evaluate(([tt, R]) => window.__step(tt, [{ t: tt, kind: 'service', stand: R, data: { mode: 'cold' } }]), [tR + 1800e3, REMOTE]);
  await frames(4); const vCold = await veh(); if (RENDER) { const f = await shot(path.relative(path.resolve(process.env.OUT || path.join(HERE, '..', 'out', 'live')), path.join(OUTD, 'e_404_2_cold'))); shots.push({ f, label: 'remote stand, cold: no stairs, bus or GSE' }); }
  ok('remote stand ' + REMOTE + ': stairs + bus at a turn, none when cold', Object.keys(vTurn).some(k => /^stairs/.test(k)) && vTurn.bus && !Object.keys(vCold).length, `turn ${JSON.stringify(vTurn)}, cold ${JSON.stringify(vCold)}`);
  await page.evaluate((R) => window.__unplace(R), REMOTE);

  // ---- 4. the full rebuild at 130 occupied stands in the browser
  const rb = await page.evaluate(async (T0) => {
    const sys = SHA.scene.gateSys, gs = window.__gs; const REF = { B: 'crj9', C: 'a321', CL: 'b753', D: 'b763', E: 'a333', EL: 'b77w', F: 'b748' };
    const occ = new Map(); let n = 0; for (const g of sys.gates) { if (g.sharesBridgesOf || n >= 130) continue; const k = REF[g.cls]; if (g.bridge && !(window.__GT.stands[g.name] || {})[k]) continue; occ.set(g.name, { state: 'docked', since: T0 - 3600e3, tDock: null, typeKey: k, service: 'turn' }); n++; }
    let t = T0 + 7200e3; window.__simT = t; const r = gs.resetTo(t, occ); const P = performance.now(); sys.items(sys.now()); const cold = performance.now() - P;
    const ms = []; const slow = []; const frame = () => { const d = !!sys.dirty; const p = performance.now(); sys.items(sys.now()); const v = +(performance.now() - p).toFixed(1); if (d) { ms.push(v); if (v > 30 && slow.length < 6) slow.push({ ms: v, ...sys.lastBuild }); } };
    for (let i = 0; i < 80; i++) { t += 1000; window.__simT = t; gs.apply([], t); frame(); }   // (the deferred GSE placements of the cold build)
    const names = [...occ.keys()].filter((x, i) => i % 9 === 4).slice(0, 10);
    for (const s of names) { const o = occ.get(s); t += 1000; window.__simT = t; gs.apply([{ t, kind: 'service', stand: s, data: { mode: 'cold' } }], t); frame();
      t += 1000; window.__simT = t; gs.apply([{ t, kind: 'pushstart', stand: s }], t); frame(); for (let i = 0; i < 3; i++) { t += 1000; window.__simT = t; gs.apply([], t); frame(); }
      t += 1000; window.__simT = t; const g = sys.gates.find(x => x.name === s); gs.apply([{ t, kind: g.bridge ? 'dock' : 'onblock', stand: s, data: { typeKey: o.typeKey } }], t); frame();
      for (let i = 0; i < 160; i++) { t += 1000; window.__simT = t; gs.apply([], t); frame(); } }
    const q = (a, p) => { const s = a.slice().sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.floor(p * (s.length - 1)))]; };
    return { reset: r, cold: +cold.toFixed(0), n: ms.length, p50: q(ms, 0.5), p90: q(ms, 0.9), max: Math.max(...ms), over30: ms.filter(v => v > 30).length, slow, lastBuild: sys.lastBuild };
  }, T0);
  ok('full rebuild at 130 occupied stands in the browser (llvmpipe Chromium, GL uploads included): p90 <= 30 ms per build (max reported)', rb.p90 <= 30, `${rb.n} builds: p50 ${rb.p50} ms, p90 ${rb.p90} ms, max ${rb.max} ms (${rb.over30} over 30 ms: ${JSON.stringify(rb.slow)}); resetTo ${rb.reset.ms} ms; first build after the jump (cold cache, GSE deferred) ${rb.cold} ms`);
  // ---- 5. detach; the DEBUG park again; pavedVec
  const fin = await page.evaluate(async () => { const d = window.__gs.detach(); const sys = SHA.scene.gateSys; const p = await SHA.qa.park('234', 'A320'); SHA.qa.unparkAll();
    const S = SHA.data.stands.stands; const s = S.find(x => x.name === '233'); const pv = [SHA.qa.pavedVec(s.nose[0], s.nose[1]), SHA.qa.pavedVec(s.nose[0] + 3000, s.nose[1] + 3000)];
    return { d, traffic: sys.trafficRunning(), dnow: sys.now() - Date.now(), park: p && p.ok, pv }; });
  ok('detach: Date.now() again, the DEBUG park works', fin.d && !fin.traffic && Math.abs(fin.dnow) < 1000 && fin.park, JSON.stringify(fin));
  ok('SHA.qa.pavedVec exported (true on a stand node, false 3 km off)', fin.pv[0] === true && fin.pv[1] === false, JSON.stringify(fin.pv));
  await frames(2);
  ok('clean console during the job', con.error === 0 && con.warning === 0, `${con.error} errors, ${con.warning} warnings ${JSON.stringify(con.list.slice(0, 4))}`);
  fs.writeFileSync(path.join(OUTD, 'gate_sync_result.json'), JSON.stringify({ ...res, boot: boot.check, rebuild: rb, shots: shots.map(s => ({ f: path.basename(s.f), label: s.label })) }, null, 1));
  console.log('gate_sync job:', res.checks.filter(c => c.ok).length, 'passed,', res.checks.filter(c => !c.ok).length, 'failed; renders in', OUTD);
};
