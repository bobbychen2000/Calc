// SHA Live 3D, Phase 3 package E: tests of the gate and time adapter (design docs/phase3/design.md §5 "Gate adapter tests",
// §7.2 P3-E acceptance). Node 22, no browser (the gate engine runs on tools/sim/gl_stub.mjs):
//   node tools/sim/test_gate_sync.mjs            (~1-2 min)       QUICK=1: fewer table entries in T2 (every 5th)
// Prints one line per check and "test_gate_sync: N passed, M failed" (exit 1 on a failure). Counts and timings only.
//  T1 the table: present, inputs_sha256_16 = the inputs now (not stale), deterministic (rebuilt in memory = the file),
//     all 56 bridge stands (+ 238A / 259A) x exactly their fitting model keys
//  T2 dock / undock timing through gate_sync.apply vs the table, every stand x type: docked at tDock + dock_s, retracted
//     at tUndock + undock_s (both within the 0.1 s round-up), extension 0 and pushClearEta 0 before the push starts when
//     undock = off-block - max(150 s, undock_s + 15 s)
//  T3 resetTo = the animated state at the same t: a scripted 6 h apron day (40 stands, contact and remote, 238 / 238A,
//     night-stoppers, cold windows) played forward at 2 s frames; at 90 sample times (inside dockings, docked, early,
//     pushing, departure holds, rest-pose returns) a second engine jumps there with resetTo (backward and forward in a
//     shuffled order) and must hold the same engine state: occupants, early / hold / service, extension, every animation,
//     every bridge joint state, park and settle, the GSE instances; a third engine plays at irregular frames (frame-rate
//     independence); after every backward jump no animation, park or hold was started after t
//  T4 cold service: GSE at a contact stand, stairs + bus at a remote stand; 'cold' removes all of them, the bridge stays docked
//  T5 full rebuild at 130 occupied stands: per single-stand event (dock, docked, undock, push, service), measured
//  T6 the clock: now() = Date.now() without traffic, the sim time (integer ms) with it; items() uses it; the DEBUG park keeps
//     Date.now() and is refused while traffic runs; attach() is refused while a DEBUG aircraft is parked
import fs from 'node:fs';
import path from 'node:path';
import { bootGateEngine, SHA3D } from './gl_stub.mjs';
import { buildTable, inputsHash, standIns } from './build_gate_times.mjs';
import v8 from 'node:v8'; import vm from 'node:vm';
// a full garbage collection before the timing test (T5): the engines of T3 are garbage by then and a major GC inside a
// timed rebuild would be the test's own heap, not the rebuild
v8.setFlagsFromString('--expose_gc'); const gc = vm.runInNewContext('gc');

let pass = 0, fail = 0; const out = [];
const ok = (name, cond, detail = '') => { (cond ? pass++ : fail++); const l = `${cond ? 'PASS' : 'FAIL'} ${name}${detail ? ': ' + detail : ''}`; out.push(l); console.log(l); };
const QUICK = !!process.env.QUICK;
const T = await import('../../js/aircraft/types.js');
const GSY = await import('../../js/live/gate_sync.js');
const GTJ = JSON.parse(fs.readFileSync(path.join(SHA3D, 'data/sha_gate_times.json'), 'utf8'));
const q = (a, p) => { const s = a.slice().sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.floor(p * (s.length - 1)))]; };

// ------------------------------------------------------------------ T1 the table
{
  const now = inputsHash();
  ok('T1 table inputs hash is current', GTJ.inputs_sha256_16 === now, `file ${GTJ.inputs_sha256_16}, inputs now ${now}${GTJ.inputs_sha256_16 === now ? '' : ' -> node tools/sim/build_gate_times.mjs'}`);
  const t0 = performance.now(); const { out: re } = await buildTable(); const ms = performance.now() - t0;
  const same = JSON.stringify(re.stands) === JSON.stringify(GTJ.stands) && JSON.stringify(re.dockN) === JSON.stringify(GTJ.dockN);
  ok('T1 table deterministic (rebuilt in memory = file)', same, `${re.stats.entries} entries rebuilt in ${(ms / 1000).toFixed(1)} s`);
  const E = await bootGateEngine();
  const bridge = E.gates.filter(g => g.bridge).map(g => g.name).sort();
  const alt = E.gates.filter(g => g.sharesBridgesOf).map(g => g.name).sort();
  const names = Object.keys(GTJ.stands).sort();
  ok('T1 table covers all 56 bridge stands + the alternative positions', bridge.length === 56 && JSON.stringify(names) === JSON.stringify(bridge.concat(alt).sort()), `${bridge.length} bridge stands, ${alt.length} alternative (${alt.join(', ')}), table ${names.length}`);
  const SI = standIns(); let badKeys = 0; const ex = [];
  for (const g of E.gates.filter(g => names.includes(g.name))) {
    const want = new Set(E.sys.acceptedTypes(g).map(a => a.key)); for (const s of Object.values(SI)) { const k = T.ICAO_TYPES[s.model]; if (k && s.spanM <= g.maxSpan && s.lenM <= g.maxLen) want.add(k); }
    const have = Object.keys(GTJ.stands[g.name]); const w = [...want].filter(k => T.TYPES[k]).sort();
    if (JSON.stringify(have.slice().sort()) !== JSON.stringify(w)) { badKeys++; if (ex.length < 3) ex.push(g.name); }
    // and every key the allocator could ask for (js/sim/alloc.js fits: span <= maxSpan, length <= maxLen; stand-ins by their own size)
    for (const [k, Ty] of Object.entries(T.TYPES)) if (Ty && Ty.wing && T.ICAO_TYPES[Object.keys(T.ICAO_TYPES).find(i => T.ICAO_TYPES[i] === k)] && Ty.wing.span <= g.maxSpan && Ty.L <= g.maxLen && !have.includes(k)) { badKeys++; if (ex.length < 3) ex.push(g.name + ':' + k); }
  }
  ok('T1 table keys = the fitting model keys per stand (engine accepted types + stand-in models; covers the allocator rule)', badKeys === 0, `${GTJ.stats.entries} entries, ${badKeys} stands off ${JSON.stringify(ex)}`);
  ok('T1 table rows are [dock_s, undock_s, hurry_s, pushClear_s] >= 0 with src inf', GTJ.src === 'inf' && Object.values(GTJ.stands).every(o => Object.values(o).every(r => r.length === 4 && r.every(v => Number.isFinite(v) && v >= 0))), `class reference dock p50 ${GTJ.stats.classReference.dock_s.p50} s, undock p50 ${GTJ.stats.classReference.undock_s.p50} s`);
}

// ------------------------------------------------------------------ helpers
const E = await bootGateEngine(); const { sys, gates, byName, GS } = E;
const T0 = Date.UTC(2026, 10, 12, 0, 0, 0);      // 08:00 local, 12 Nov 2026 (any instant: only differences matter)
const REF = { B: 'crj9', C: 'a321', CL: 'b753', D: 'b763', E: 'a333', EL: 'b77w', F: 'b748' };
const row = (n, k) => GTJ.stands[n] && GTJ.stands[n][k];

// ------------------------------------------------------------------ T2 dock / undock timing vs the table
{
  const gs = GSY.createGateSync(sys, gates, { gateTimes: GTJ, check: false });
  gs.attach(() => T0);
  let n = 0, badDock = 0, badUndock = 0, notClear = 0, pushHold = 0, maxD = 0, maxU = 0; const ex = [];
  const entries = []; for (const s of Object.keys(GTJ.stands).sort()) for (const k of Object.keys(GTJ.stands[s]).sort()) entries.push([s, k]);
  const pick = QUICK ? entries.filter((e, i) => i % 5 === 0) : entries;
  const p0 = performance.now();
  for (const [s, k] of pick) {
    const r = row(s, k); const g = byName.get(s); const eg = gs.engineGate(s);
    gs.resetTo(T0, []);
    const tD = T0 + 1000; gs.apply([{ t: tD, kind: 'dock', stand: s, data: { typeKey: k } }], tD);
    const a = sys.anims.get(eg.id); const end = a ? a.t0 + a.dur : tD;
    const dEnd = (end - tD) / 1000; maxD = Math.max(maxD, r[0] - dEnd);
    if (!(dEnd <= r[0] + 1e-9 && dEnd > r[0] - 0.1 - 1e-9)) { badDock++; if (ex.length < 4) ex.push(`${s}:${k} dock ${dEnd.toFixed(2)} vs ${r[0]}`); }
    const tU = tD + 1800e3; gs.apply([], tU); gs.apply([{ t: tU, kind: 'undock', stand: s, data: {} }], tU);
    const a2 = sys.anims.get(eg.id); const uEnd = a2 ? (a2.t0 + a2.dur - tU) / 1000 : 0; maxU = Math.max(maxU, r[1] - uEnd);
    if (!(uEnd <= r[1] + 1e-9 && uEnd > r[1] - 0.1 - 1e-9)) { badUndock++; if (ex.length < 4) ex.push(`${s}:${k} undock ${uEnd.toFixed(2)} vs ${r[1]}`); }
    const tP = tU + GSY.undockLeadS(r) * 1000; gs.apply([], tP - 1); sys.step(tP - 1);
    if (sys.extension(eg) !== 0 || sys.anims.has(eg.id)) { notClear++; if (ex.length < 4) ex.push(`${s}:${k} extension ${sys.extension(eg)} at push - 1 ms`); }
    if (sys.pushClearEta(eg, tP - 1) > 0) pushHold++;
    gs.apply([{ t: tP, kind: 'pushstart', stand: s, data: {} }], tP);
    n++;
  }
  gs.detach();
  ok('T2 docked at tDock + dock_s (table, 0.1 s round-up) for every stand x type', badDock === 0, `${n} entries${QUICK ? ' (QUICK: every 5th)' : ''}, ${badDock} off, largest round-up ${maxD.toFixed(3)} s; ${ex.join('; ')}`);
  ok('T2 retracted at tUndock + undock_s (table) for every stand x type', badUndock === 0, `${badUndock} off, largest round-up ${maxU.toFixed(3)} s`);
  ok('T2 undock at off-block - max(150 s, undock_s + 15 s): extension 0, no animation and pushClearEta 0 before the push, every stand x type', notClear === 0 && pushHold === 0, `${notClear} not clear, ${pushHold} with a push hold; ${((performance.now() - p0) / 1000).toFixed(1)} s`);
}

// ------------------------------------------------------------------ T3 forward play vs resetTo
// a scripted apron day: deterministic pseudo-random turnarounds on 40 stands, the sim's rules of design §1.5 / §4.3
function rng(seed) { let a = seed >>> 0; return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
function scenario(seed = 7) {
  const R = rng(seed);
  const want = ['221', '222', '223', '224', '225', '226', '227', '228', '229', '230', '231', '232', '233', '234', '236', '237', '238', '238A', '239', '240',
    '212', '213', '214', '215', '216', '217', '276', '277', '278', '279', '113', '114', '115', '120', '257', '258', '259', '259A', '260', '261'];
  const H6 = 6 * 3600e3; const turns = [];
  for (const s of want) {
    const g = byName.get(s); if (!g) continue; const eg = g.sharesBridgesOf ? byName.get(g.sharesBridgesOf) : g; const contact = !!eg.bridge;
    const keys = contact ? Object.keys(GTJ.stands[s] || {}) : ['a320', 'a321', 'b738', 'a20n'].filter(k => T.TYPES[k] && T.TYPES[k].wing.span <= g.maxSpan + 0.6);
    if (!keys.length) continue;
    let t = T0 + Math.floor(R() * 40) * 60e3;
    // (some stands start the day with a night-stopper parked: tDock null)
    if (s !== '238A' && s !== '259A' && R() < 0.3) { const k = REF[g.cls] && keys.includes(REF[g.cls]) ? REF[g.cls] : keys[0]; const off = T0 + (20 + Math.floor(R() * 60)) * 60e3; turns.push({ s, g, eg, contact, k, on: null, off }); t = off + (25 + Math.floor(R() * 30)) * 60e3; }
    while (t < T0 + H6 - 3600e3) {
      if ((s === '238A' || s === '259A') && R() < 0.6) { t += 90 * 60e3; continue; }
      const k = R() < 0.5 && REF[g.cls] && keys.includes(REF[g.cls]) ? REF[g.cls] : keys[Math.floor(R() * keys.length)];
      const dur = R() < 0.25 ? (110 + Math.floor(R() * 60)) * 60e3 : (35 + Math.floor(R() * 40)) * 60e3;
      turns.push({ s, g, eg, contact, k, on: t + Math.floor(R() * 59e3), off: t + dur });
      t += dur + (25 + Math.floor(R() * 40)) * 60e3;
    }
  }
  // 238 / 238A and 259 / 259A share one set of bridges: keep their turns apart (the sim's exclusive pairs)
  for (const [a, b] of [['238', '238A'], ['259', '259A']]) { const A = turns.filter(x => x.s === a), B = turns.filter(x => x.s === b);
    for (const x of B) if (A.some(y => (y.on ?? -1e15) - 25 * 60e3 < x.off && y.off + 25 * 60e3 > x.on)) x.drop = true; }
  const T2 = turns.filter(x => !x.drop);
  const ev = [];
  for (const x of T2) {
    const r = x.contact ? row(x.s, x.k) : null;
    x.tDock = x.on == null ? null : x.contact ? x.on + 20e3 : x.on;
    x.tDocked = x.tDock == null ? null : x.contact ? x.tDock + Math.round(r[0] * 1000) : x.tDock;
    x.tUndock = x.contact ? x.off - GSY.undockLeadS(r) * 1000 : null; x.tPush = x.off; x.tPushEnd = x.off + 90e3;
    x.cold = (x.on == null ? [T0 - 3600e3, x.off - 45 * 60e3] : x.off - x.on > 100 * 60e3 ? [x.on + 30 * 60e3, x.off - 45 * 60e3] : null);
    if (x.on != null) { ev.push({ t: x.on, kind: 'onblock', stand: x.s, data: { typeKey: x.k } }); if (x.contact) { ev.push({ t: x.tDock, kind: 'dock', stand: x.s, data: { typeKey: x.k } }); ev.push({ t: x.tDocked, kind: 'docked', stand: x.s }); } }
    if (x.cold) { if (x.cold[0] >= T0) ev.push({ t: x.cold[0], kind: 'service', stand: x.s, data: { mode: 'cold' } }); ev.push({ t: x.cold[1], kind: 'service', stand: x.s, data: { mode: 'turn' } }); }
    if (x.contact) ev.push({ t: x.tUndock, kind: 'undock', stand: x.s });
    ev.push({ t: x.tPush, kind: 'pushstart', stand: x.s }); ev.push({ t: x.tPushEnd, kind: 'pushend', stand: x.s });
  }
  ev.sort((a, b) => a.t - b.t);
  // StandState at t (design §7.1, with the exact times and the previous occupant)
  const statesAt = (t) => {
    const M = new Map();
    for (const x of T2) {
      const life = { typeKey: x.k, icao: null, tDock: x.tDock, tUndock: x.tUndock, tPush: x.tPush };
      if (x.tPush <= t && (x.tPushEnd <= t)) { const m = M.get(x.s) || { state: 'empty' }; if (!m.prev || m.prev.tPush < x.tPush) M.set(x.s, { ...(m.state === 'empty' ? { state: 'empty' } : m), prev: life }); continue; }
      if (x.on != null && x.on > t) continue;
      let st, since;
      if (x.tPush <= t) { st = 'pushing'; since = x.tPush; }
      else if (x.tUndock != null && x.tUndock <= t) { st = 'early'; since = x.tUndock; }
      else if (x.tDock == null || x.tDocked <= t) { st = 'docked'; since = x.tDocked ?? T0 - 3600e3; }
      else if (x.tDock <= t) { st = 'docking'; since = x.tDock; }
      else continue;   // (on-block, bridge not called yet: no engine state)
      const svc = x.cold && x.cold[0] <= t && t < x.cold[1] ? 'cold' : 'turn';
      const prev = (M.get(x.s) || {}).prev || null;
      M.set(x.s, { state: st, since, service: svc, ...life, prev });
    }
    return M;
  };
  return { turns: T2, events: ev, statesAt };
}
// the GSE placements a build deferred past its budget (gseBudgetMs) are made by the next builds: flush them before a comparison
const flush = (S) => { for (let i = 0; i < 500 && S._gsePending && S._gsePending.size; i++) { S.dirty = true; S.items(S.now()); } };
function engineState(S, t) {
  flush(S);
  const st = {}; const J = (x) => x == null ? null : JSON.parse(JSON.stringify(x));
  for (const g of S.gates) {
    const a = S.anims.get(g.id);
    const o = { ac: g.acType || null, ty: g.dockType || null, cargo: !!g.dockCargo, dock: J(g.dock), early: g._early ? { type: g._early.type, t: g._early.t, pose: J(g._early.pose) } : null,
      hold: g._parkHold ? { type: g._parkHold.type, until: g._parkHold.until } : null, svc: g._service || null, ext: S.extension(g),
      anim: a ? { from: a.from, to: a.to, t0: a.t0, dur: a.dur, k: a.k, fast: !!a.fast, early: !!a.early } : null, br: [] };
    for (const b of S.bridgesOf(g)) { if (!b.m) continue; const L = S.legsNow(g, b, t); const p = S.parks && S.parks.get(b); const s = S.settles && S.settles.get(b);
      o.br.push({ hRest: b.hRest ?? null, q: J(L.q), parkQ: J(b._parkQ || null), park: p ? { t0: p.t0, total: p.total, end: J(p.pts[p.pts.length - 1]) } : null, settle: s ? { from: s.from, t0: s.t0, dur: s.dur } : null }); }
    const c = S._chunks && S._chunks.get(g.id); o.gse = c ? Object.entries(c.veh).filter(([k, l]) => l.length).map(([k, l]) => k + ':' + l.length + ':' + l.map(v => Array.from(v).map(x => +x.toFixed(4)).join(',')).join('/')).sort().join('|') : null;
    st[g.name] = o;
  }
  st._holds = [...(S._holdG || [])].map(g => g.name).sort();
  return st;
}
function diff(A, B, pre = '', out = []) {
  if (out.length > 40) return out;
  if (A === B) return out; if (typeof A === 'number' && typeof B === 'number' && Object.is(A, B)) return out;
  if (A && B && typeof A === 'object' && typeof B === 'object') { for (const k of new Set([...Object.keys(A), ...Object.keys(B)])) diff(A[k], B[k], pre + '.' + k, out); return out; }
  out.push({ at: pre, a: A, b: B, d: typeof A === 'number' && typeof B === 'number' ? Math.abs(A - B) : null }); return out;
}
{
  const SC = scenario(7);
  const nTurns = SC.turns.length, nEv = SC.events.length;
  const tStart = T0 - 60e3, tEnd = T0 + 6 * 3600e3;
  // sample instants: inside dockings, docked, early (mid-retraction), pushing, after the push (hold, rest-pose return), cold, random
  const R = rng(99); const samp = new Set();
  for (const x of SC.turns) { if (samp.size > 400) break;
    if (x.tDock != null) for (const d of [1, 5e3, 13e3, 31e3]) samp.add(x.tDock + d);
    if (x.tUndock != null) for (const d of [0, 7e3, 33e3]) samp.add(x.tUndock + d);
    for (const d of [0, 40e3, 179e3, 181e3, 200e3, 400e3]) samp.add(x.tPush + d);
    if (x.cold) samp.add(x.cold[0] + 1); }
  const all = [...samp].filter(t => t > tStart && t < tEnd).sort((a, b) => a - b);
  const pickN = 90; const samples = []; for (let i = 0; i < pickN; i++) samples.push(all[Math.floor((i + R()) * all.length / pickN)]);
  samples.sort((a, b) => a - b);
  // engine A: forward play at 2 s frames (and every sample instant), items() every frame
  const A = sys; const gsA = GSY.createGateSync(A, gates, { gateTimes: GTJ, check: false });
  let simT = tStart; gsA.attach(() => simT); gsA.resetTo(tStart, SC.statesAt(tStart));
  const frames = []; for (let t = tStart; t <= tEnd; t += 2000) frames.push(t); for (const s of samples) frames.push(s); frames.sort((a, b) => a - b);
  const SA = new Map(); let ei = 0, prev = tStart; const p0 = performance.now(); let maxBuild = 0, sumBuild = 0, nBuild = 0;
  for (const t of frames) { if (t <= prev && t !== tStart) continue;
    const evs = []; while (ei < SC.events.length && SC.events[ei].t <= t) evs.push(SC.events[ei++]);
    simT = t; gsA.apply(evs, t); const b0 = performance.now(); A.items(A.now()); const bm = performance.now() - b0; if (evs.length) { maxBuild = Math.max(maxBuild, bm); sumBuild += bm; nBuild++; if (bm > 30 && process.env.VERBOSE) console.log('  slow event frame', ((t - T0) / 1000).toFixed(0), 's', bm.toFixed(1), 'ms', evs.map(e => e.kind + ':' + e.stand).join(' '), JSON.stringify(A.lastBuild)); }
    if (samples.includes(t) && !SA.has(t)) SA.set(t, engineState(A, t)); prev = t; }
  const msA = performance.now() - p0;
  // engine B: jumps (resetTo) to the samples in a shuffled order (backward and forward)
  const EB = await bootGateEngine({ fresh: true }); const B = EB.sys; const gsB = GSY.createGateSync(B, EB.gates, { gateTimes: GTJ, check: false });
  let simB = tStart; gsB.attach(() => simB);
  const order = samples.slice(); for (let i = order.length - 1; i > 0; i--) { const j = Math.floor(R() * (i + 1)); [order[i], order[j]] = [order[j], order[i]]; }
  let same = 0, nBack = 0, stale = 0; const bad = []; const resetMs = []; let maxNum = 0, last = -Infinity;
  for (const t of order) {
    if (t < last) nBack++; last = t; simB = t;
    const r0 = performance.now(); gsB.resetTo(t, SC.statesAt(t)); resetMs.push(performance.now() - r0); B.items(B.now());
    const D = diff(SA.get(t), engineState(B, t));
    // no animation, park or hold started after t (review H1)
    for (const a of B.anims.values()) if (a.t0 - 12e3 > t + 1e-6 && a.t0 > t) stale++;
    for (const p of (B.parks || new Map()).values()) if (p.t0 > t) stale++;
    for (const g of B.gates) if (g._parkHold && g._parkHold.until - 3780e3 > t + 1e-6 && g._parkHold.until - 180e3 > t) stale++;
    if (!D.length) same++; else { for (const d of D) if (d.d != null) maxNum = Math.max(maxNum, d.d); if (bad.length < 6) bad.push({ t: new Date(t).toISOString().slice(11, 23), n: D.length, first: D.slice(0, 3) }); }
  }
  ok('T3 resetTo = the forward play at the same t (every engine field and the GSE), backward and forward jumps', same === samples.length,
    `${same}/${samples.length} samples identical (${nBack} backward jumps); scenario ${nTurns} turnarounds, ${nEv} events on 40 stands over 6 h; forward play ${(msA / 1000).toFixed(1)} s, rebuild at an event frame mean ${(sumBuild / Math.max(1, nBuild)).toFixed(1)} ms max ${maxBuild.toFixed(1)} ms; resetTo p50 ${q(resetMs, 0.5).toFixed(0)} ms max ${Math.max(...resetMs).toFixed(0)} ms${bad.length ? '; first differences ' + JSON.stringify(bad).slice(0, 900) + ' largest numeric ' + maxNum : ''}`);
  ok('T3 after every jump no animation, park or hold was started after t (review H1)', stale === 0, `${stale} stale entries over ${samples.length} jumps`);
  // what the samples cover (so that "identical" is not vacuous)
  const cov = { docking: 0, undocking: 0, hurry: 0, park: 0, settle: 0, hold: 0, early: 0, cold: 0, gse: 0 };
  for (const t of samples) { const S = SA.get(t); const has = (f) => Object.entries(S).some(([n, o]) => n[0] !== '_' && f(o));
    if (has(o => o.anim && o.anim.to === 1)) cov.docking++; if (has(o => o.anim && o.anim.to === 0)) cov.undocking++; if (has(o => o.anim && o.anim.fast)) cov.hurry++;
    if (has(o => o.br.some(b => b.park))) cov.park++; if (has(o => o.br.some(b => b.settle))) cov.settle++; if (has(o => o.hold && o.hold.until > t)) cov.hold++;
    if (has(o => o.early)) cov.early++; if (has(o => o.svc === 'cold')) cov.cold++; if (has(o => o.gse)) cov.gse++; }
  ok('T3 the samples cover running dockings, retractions, settles, departure holds, early, cold and GSE (rest-pose parks: T3b)', Object.entries(cov).filter(([k]) => k !== 'hurry' && k !== 'park').every(([k, v]) => v > 0), JSON.stringify(cov) + ' samples (of ' + samples.length + ') with at least one');
  // negative controls: (a) a reset that snaps every call (horizon 0) and (b) a forward play at 7 s frames whose engine
  // retires its timers only at frame times (no advance) must differ at mid-animation samples - else the comparison could
  // not see such a defect
  const mids = samples.filter(t => { const S = SA.get(t); return Object.entries(S).some(([n, o]) => n[0] !== '_' && (o.anim || o.br.some(b => b.park || b.settle))); });
  let negA = 0; for (const t of mids) { simB = t; gsB.resetTo(t, SC.statesAt(t), { horizonS: 0 }); B.items(B.now()); if (diff(SA.get(t), engineState(B, t)).length) negA++; }
  const ED = await bootGateEngine({ fresh: true }); const Dn = ED.sys; const gsD = GSY.createGateSync(Dn, ED.gates, { gateTimes: GTJ, check: false });
  let simD = tStart; gsD.attach(() => simD); gsD.resetTo(tStart, SC.statesAt(tStart)); Dn.advance = () => {};
  const fr3 = []; for (let t = tStart; t <= tEnd; t += 7000) fr3.push(t); for (const s of mids) fr3.push(s); fr3.sort((a, b) => a - b);
  let negB = 0; ei = 0; prev = -Infinity;
  for (const t of fr3) { if (t <= prev) continue; const evs = []; while (ei < SC.events.length && SC.events[ei].t <= t) evs.push(SC.events[ei++]);
    simD = t; gsD.apply(evs, t); Dn.items(Dn.now()); prev = t; if (mids.includes(t) && diff(SA.get(t), engineState(Dn, t)).length) negB++; }
  gsD.detach();
  ok('T3 negative controls differ (the comparison sees a reset that snaps everything, and timers retired at frame times)', negA > 0 && negB > 0, `snap-all reset: ${negA}/${mids.length} mid-animation samples differ; frame-time timers at 7 s frames: ${negB}/${mids.length} differ`);
  // engine C: the same day at irregular frames (0.3-7 s): the frame rate does not change the state
  const EC = await bootGateEngine({ fresh: true }); const Cs = EC.sys; const gsC = GSY.createGateSync(Cs, EC.gates, { gateTimes: GTJ, check: false });
  let simC = tStart; gsC.attach(() => simC); gsC.resetTo(tStart, SC.statesAt(tStart));
  const R2 = rng(5); const fr2 = []; for (let t = tStart; t <= tEnd; t += 300 + Math.floor(R2() * 6700)) fr2.push(t); for (const s of samples) fr2.push(s); fr2.sort((a, b) => a - b);
  let sameC = 0; ei = 0; prev = -Infinity; const badC = [];
  for (const t of fr2) { if (t <= prev) continue; const evs = []; while (ei < SC.events.length && SC.events[ei].t <= t) evs.push(SC.events[ei++]);
    simC = t; gsC.apply(evs, t); Cs.items(Cs.now()); prev = t;
    if (samples.includes(t)) { const D = diff(SA.get(t), engineState(Cs, t)); if (!D.length) sameC++; else if (badC.length < 3) badC.push({ t: new Date(t).toISOString().slice(11, 23), n: D.length, first: D.slice(0, 2) }); } }
  ok('T3 frame-rate independence: the same day at irregular 0.3-7 s frames gives the same state at every sample', sameC === samples.length, `${sameC}/${samples.length}${badC.length ? ' ' + JSON.stringify(badC).slice(0, 600) : ''}`);
  gsA.detach(); gsB.detach(); gsC.detach();
  // T3b rest-pose parks: with every aircraft on the stop convention no ZSSS bridge ever parks for an occupant (0 of 56 with
  // every stand holding its largest fitting type), so this case shifts three aircraft sideways off their stop lines (a
  // pose the sim could hand over) until their own bridge cannot dock and parks clear of them, then pushes them; samples
  // inside the park animations (parking, and the return after the 180 s departure hold)
  const shift = [['250', 4], ['114', 7], ['233', 10]]; const ev3 = []; const life3 = [];
  shift.forEach(([n, dl], i) => { const g = byName.get(n); const k = REF[g.cls]; const tip = GS.standTip(g, T.TYPES[k]); const lf = [g.dir[1], -g.dir[0]];
    const pose = { nose: [tip[0] + lf[0] * dl, tip[2] + lf[1] * dl], dir: g.dir.slice() }; const r = row(n, k);
    const tD = T0 + 600e3 + i * 37e3, tU = tD + 3000e3, tP = tU + GSY.undockLeadS(r) * 1000;
    ev3.push({ t: tD, kind: 'dock', stand: n, data: { typeKey: k, pose } }, { t: tU, kind: 'undock', stand: n }, { t: tP, kind: 'pushstart', stand: n });
    life3.push({ n, k, pose, tD, tU, tP }); });
  ev3.sort((a, b) => a.t - b.t);
  const st3 = (t) => { const M = new Map(); for (const L of life3) { const life = { typeKey: L.k, pose: L.pose, tDock: L.tD, tUndock: L.tU, tPush: L.tP };
    if (t < L.tD) continue; if (t >= L.tP) { M.set(L.n, { state: 'empty', prev: life }); continue; } M.set(L.n, { state: t >= L.tU ? 'early' : 'docked', since: t >= L.tU ? L.tU : L.tD, service: 'turn', ...life }); } return M; };
  const s3 = []; for (const L of life3) for (const d of [1, 3e3, 9e3, 20e3]) { s3.push(L.tD + d); s3.push(L.tP + 180e3 + 1000 + d); }
  s3.sort((a, b) => a - b);
  const EA = await bootGateEngine({ fresh: true }); const A3 = EA.sys; const gA3 = GSY.createGateSync(A3, EA.gates, { gateTimes: GTJ, check: false }); let sA3 = T0; gA3.attach(() => sA3); gA3.resetTo(T0, new Map());
  const f3 = []; for (let t = T0; t <= s3[s3.length - 1]; t += 2000) f3.push(t); for (const x of s3) f3.push(x); f3.sort((a, b) => a - b);
  const R3 = new Map(); let e3 = 0, p3 = -Infinity, parkSeen = 0;
  for (const t of f3) { if (t <= p3) continue; const evs = []; while (e3 < ev3.length && ev3[e3].t <= t) evs.push(ev3[e3++]); sA3 = t; gA3.apply(evs, t); A3.items(A3.now()); p3 = t;
    if (s3.includes(t)) { const S = engineState(A3, t); R3.set(t, S); if (Object.values(S).some(o => o && o.br && o.br.some(b => b.park))) parkSeen++; } }
  const EB3 = await bootGateEngine({ fresh: true }); const B3 = EB3.sys; const gB3 = GSY.createGateSync(B3, EB3.gates, { gateTimes: GTJ, check: false }); let sB3 = T0; gB3.attach(() => sB3);
  let same3 = 0; const bad3 = []; const o3 = s3.slice().reverse();
  for (const t of o3) { sB3 = t; gB3.resetTo(t, st3(t)); B3.items(B3.now()); const D = diff(R3.get(t), engineState(B3, t)); if (!D.length) same3++; else if (bad3.length < 3) bad3.push({ t: (t - T0) / 1000, first: D.slice(0, 2) }); }
  ok('T3b rest-pose parks: resetTo = the forward play inside park animations (parking and the return after the hold)', parkSeen > 0 && same3 === s3.length, `${same3}/${s3.length} samples identical, ${parkSeen} with a park animation running${bad3.length ? ' ' + JSON.stringify(bad3).slice(0, 600) : ''}`);
  gA3.detach(); gB3.detach();
}

// ------------------------------------------------------------------ T4 cold service
{
  const gs = GSY.createGateSync(sys, gates, { gateTimes: GTJ, check: false }); let simT = T0; gs.attach(() => simT);
  const contact = '233', remote = '404';
  const tk = 'a320';
  gs.resetTo(T0, new Map([[contact, { state: 'docked', since: T0 - 600e3, tDock: T0 - 900e3, typeKey: tk, service: 'turn' }], [remote, { state: 'docked', since: T0 - 900e3, tDock: T0 - 900e3, typeKey: tk, service: 'turn' }]]));
  sys.items(sys.now());
  const veh = (n) => { const c = sys._chunks.get(byName.get(n).id); const o = {}; for (const [k, l] of Object.entries(c.veh)) if (l.length) o[k] = l.length; return o; };
  flush(sys); const v0c = veh(contact), v0r = veh(remote); const ext0 = sys.extension(byName.get(contact));
  simT = T0 + 1000; gs.apply([{ t: simT, kind: 'service', stand: contact, data: { mode: 'cold' } }, { t: simT, kind: 'service', stand: remote, data: { mode: 'cold' } }], simT); sys.items(sys.now());
  flush(sys); const v1c = veh(contact), v1r = veh(remote); const ext1 = sys.extension(byName.get(contact));
  const hasStairs = Object.keys(v0r).some(k => /^stairs/.test(k)), hasBus = !!v0r.bus;
  simT = T0 + 2000; gs.apply([{ t: simT, kind: 'service', stand: contact, data: { mode: 'turn' } }, { t: simT, kind: 'service', stand: remote, data: { mode: 'turn' } }], simT); sys.items(sys.now());
  flush(sys); const v2c = veh(contact), v2r = veh(remote);
  ok('T4 cold service removes the GSE at a contact stand and the stairs + bus (+ GSE) at a remote stand; the bridge stays docked', Object.keys(v0c).length > 0 && hasStairs && hasBus && !Object.keys(v1c).length && !Object.keys(v1r).length && ext0 === 1 && ext1 === 1,
    `turn: ${contact} ${JSON.stringify(v0c)}, ${remote} ${JSON.stringify(v0r)}; cold: ${JSON.stringify(v1c)} / ${JSON.stringify(v1r)}; bridge extension ${ext0} -> ${ext1}`);
  ok('T4 turn again restores the same placement (LRU)', JSON.stringify(v2c) === JSON.stringify(v0c) && JSON.stringify(v2r) === JSON.stringify(v0r), `${JSON.stringify(v2c)} / ${JSON.stringify(v2r)}`);
  gs.detach();
}

// ------------------------------------------------------------------ T5 full rebuild at 130 occupied stands
{
  gc(); gc();
  const gs = GSY.createGateSync(sys, gates, { gateTimes: GTJ, check: false }); let simT = T0; gs.attach(() => simT);
  const occ = new Map(); let n = 0; const free = [];
  for (const g of gates) { if (g.sharesBridgesOf) continue; const tk = REF[g.cls]; const ok2 = !g.bridge || (row(g.name, tk));
    if (n < 130 && ok2 && g.name !== '233' && g.name !== '404' && g.name !== '229' && g.name !== '413') { occ.set(g.name, { state: 'docked', since: T0 - 3600e3, tDock: null, typeKey: tk, service: 'turn' }); n++; } else free.push(g.name); }
  gs.resetTo(T0, occ); const c0 = performance.now(); sys.items(sys.now()); const cold = performance.now() - c0;
  const ms = []; const kinds = {}; const rec = (k, v) => { ms.push(v); (kinds[k] || (kinds[k] = [])).push(v); };
  let t = T0 + 1000;
  const frame = (kind) => { simT = t; const b0 = performance.now(); sys.items(sys.now()); rec(kind, performance.now() - b0); };
  // every frame at 1 s sim; a rebuild is timed whenever an event or an engine timer made the engine dirty
  const run = (kind, evs, secs) => { gs.apply(evs, t); for (let i = 0; i <= secs; i++) { if (i) { t += 1000; gs.apply([], t); } const d = !!sys.dirty; simT = t; const b0 = performance.now(); sys.items(sys.now()); if (d) rec(i ? kind + ' (timer)' : kind, performance.now() - b0); } };
  // dockings at four free stands, then full turnarounds (undock, push, the hold's end, a new arrival) at 16 occupied
  // contact and remote stands with their neighbours occupied
  for (const s of ['233', '229', '404', '413']) { const g = byName.get(s); const tk = REF[g.cls]; const r = g.bridge ? row(s, tk) : [0, 0, 0, 0];
    run('dock', [{ t, kind: g.bridge ? 'dock' : 'onblock', stand: s, data: { typeKey: tk } }], Math.ceil(r[0] + 2)); t += 60e3; }
  const busy = [...occ.keys()].filter((n, i) => i % 8 === 3).slice(0, 16);
  for (const s of busy) { const g = byName.get(s); const tk = REF[g.cls]; const r = g.bridge ? row(s, tk) : [0, 0, 0, 0];
    if (g.bridge) { run('undock', [{ t, kind: 'undock', stand: s }], Math.ceil(r[1] + 2)); t += 150e3 - Math.ceil(r[1] + 2) * 1000; }
    run('push', [{ t, kind: 'pushstart', stand: s }], 5); t += 180e3; run('hold end', [], 60);
    t += 20 * 60e3; run('dock', [{ t, kind: g.bridge ? 'dock' : 'onblock', stand: s, data: { typeKey: tk } }], Math.ceil(r[0] + 2)); t += 60e3; }
  let k2 = 0; for (const [s] of occ) { if (k2++ >= 30) break; t += 1000; gs.apply([{ t, kind: 'service', stand: s, data: { mode: 'cold' } }], t); frame('service'); }
  const per = Object.fromEntries(Object.entries(kinds).map(([k, v]) => [k, `${v.length}x p50 ${q(v, 0.5).toFixed(1)} max ${Math.max(...v).toFixed(1)}`]));
  ok('T5 full rebuild <= 30 ms per single-stand event at 130 occupied stands (node, this sandbox)', Math.max(...ms) <= 30,
    `${ms.length} rebuilds: p50 ${q(ms, 0.5).toFixed(1)} ms, p90 ${q(ms, 0.9).toFixed(1)} ms, max ${Math.max(...ms).toFixed(1)} ms; ${JSON.stringify(per)}; the first build with an empty cache (all 130 stands' GSE placed): ${cold.toFixed(0)} ms (reported, not part of the target)`);
  gs.detach();
}

// ------------------------------------------------------------------ T6 the clock and the DEBUG park
{
  const d0 = Date.now(); const n0 = sys.now();
  ok('T6 without traffic the engine clock is Date.now()', !sys.trafficRunning() && Math.abs(n0 - d0) < 50, `now() - Date.now() = ${n0 - d0} ms`);
  const gs = GSY.createGateSync(sys, gates, { gateTimes: GTJ, check: false }); let simT = T0 + 0.75; gs.attach(() => simT);
  sys.items(sys.now()); const used = sys._now;
  ok('T6 with traffic now() = the sim time (integer ms) and items() steps the engine with it', sys.trafficRunning() && sys.now() === Math.floor(simT) && used === Math.floor(simT), `now() ${sys.now() - T0} ms after T0, engine stepped at ${used - T0}`);
  gs.detach();
  ok('T6 detach restores Date.now()', !sys.trafficRunning() && Math.abs(sys.now() - Date.now()) < 50);
  // the gates extension itself (buildWorld + start with a minimal app): the DEBUG park with and without traffic
  globalThis.location.search = '?masts=live';
  const ext = (await import('../../js/live/ext.js')).extension('gates');
  const geo = E.geo; const ctx = { R: { addProgram() {} }, airport: E.data.airport, stands: E.data.stands, taxigraph: E.data.taxigraph, geo, groundY: geo.groundY ? geo.groundY() : 2.5, ground: { pavedAt: null }, log() {} };
  const quiet = console.log; console.log = () => {};
  let W, app;
  try {
    W = await ext.buildWorld(ctx);
    app = { scene: { aircraft: [], add(a) { this.aircraft.push(a); return a; } }, qa: { info: () => ({ quality: 'high' }), look() {} }, ui: { setNoteLine() {}, addLegendLine() {} }, markings: null, geo: { RUNWAYS: geo.RUNWAYS || [] }, world: { anchors: {} }, R: {} };
    await ext.start(app);
  } finally { console.log = quiet; }
  const S2 = app.scene.gateSys;
  const r1 = await app.qa.park('233', 'A320');
  const parkNow = S2._now;
  ok('T6 DEBUG park works without traffic and keeps Date.now()', r1 && r1.ok && Math.abs(parkNow - Date.now()) < 10e3, `park 233: ${r1 && r1.ok}, engine time at the park - Date.now() = ${parkNow - Date.now()} ms`);
  const gs2 = GSY.createGateSync(S2, S2.gates, { gateTimes: GTJ, check: false });
  const a1 = gs2.attach(() => T0);
  ok('T6 attach (traffic) is refused while a DEBUG aircraft is parked', a1 && a1.ok === false, a1 && a1.why);
  app.qa.unparkAll();
  const a2 = gs2.attach(() => T0); const r2 = await app.qa.park('233', 'A320');
  ok('T6 the DEBUG park is refused while traffic runs', a2.ok && r2 && r2.ok === false, r2 && r2.why);
  gs2.detach(); const r3 = await app.qa.park('234', 'A320');
  ok('T6 after detach the DEBUG park works again', r3 && r3.ok);
}

console.log(`test_gate_sync: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
