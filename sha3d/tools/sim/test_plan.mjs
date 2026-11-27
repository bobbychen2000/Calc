// SHA Live 3D Phase 3 (package P3-A): day-plan tests, every P3-A acceptance criterion of docs/phase3/design.md s.7.2.
//   node tools/sim/test_plan.mjs            (public part always; the local overlay part when refs/cache/observed_elsewhere exists)
// Prints aggregates and PASS / FAIL per criterion only: no callsign, flight number from the overlay, registration, address
// or per-flight time (OD4). Exit 1 on any failure. Uses a STUB gate-times table until package P3-E's data/sha_gate_times
// exists (then it also runs with the real one).
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const J = (p) => JSON.parse(fs.readFileSync(path.join(ROOT, p), 'utf8'));
globalThis.SHA_SIM_INPUTS = J('data/sha_sim_inputs.json');
const STANDS = J('data/sha_stands.json');
const { simInputs, dayWindow, localHour, closedStands } = await import(path.join(ROOT, 'js/sim/inputs.js'));
const { buildDayPlan, endState, typeInfo, hourTargets } = await import(path.join(ROOT, 'js/sim/plan.js'));
const { standTable, closureWindows } = await import(path.join(ROOT, 'js/sim/alloc.js'));
const { checkOverlay, labelFor, dayLine, repCandidates, OVERLAY_FIELDS } = await import(path.join(ROOT, 'js/sim/identity.js'));
const { TYPE_MODELS, BIZ } = await import(path.join(ROOT, 'js/aircraft/fit.js'));
const I = simInputs();
const P = I.params;

const results = [];
const check = (name, ok, detail) => { results.push({ name, ok: !!ok, detail }); console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  -- ' + detail : ''}`); };

// 0. the inputs are current (verification fix round 2, F18): every committed source listed in inputs_sha256_16 (the P3-B
//    route table included) still has the recorded sha256 prefix; local sources (refs/cache, '(local)') are skipped
{
  const { createHash } = await import('node:crypto');
  const stale = [], seen = [];
  for (const [k, h] of Object.entries(I.inputs_sha256_16 || {})) {
    if (/\(local\)$/.test(k) || /^refs\//.test(k)) continue;
    const fp = path.join(ROOT, k);
    if (!fs.existsSync(fp)) continue;
    seen.push(k);
    if (createHash('sha256').update(fs.readFileSync(fp)).digest('hex').slice(0, 16) !== h) stale.push(k);
  }
  check('inputs current: data/sha_sim_inputs was built from the committed sources as they are now (else re-run tools/sim/build_sim_inputs.py)',
    stale.length === 0 && seen.includes('data/sha_routes.json'), stale.length ? 'stale: ' + stale.join(', ') : `${seen.length} sources match`);
}
const DAYS_PUBLIC = ['2026-11-10', '2026-11-12', '2026-11-13', '2026-11-14', '2026-11-20'];
const OBS_DAYS = P.observedDays;

// ---- stub gate times (until P3-E): every contact stand with a bridge x every type key that fits it
function stubGateTimes() {
  const T = standTable(STANDS);
  const keys = new Set();
  for (const icao of Object.keys(TYPE_MODELS)) { const k = TYPE_MODELS[icao].t; if (k) keys.add(icao); }
  const stands = {};
  for (const s of T.list) {
    if (!s.contact || !s.bridges) continue;
    stands[s.name] = {};
    for (const icao of keys) { const t = typeInfo(icao, I); if (t.typeKey && t.spanM <= s.maxSpan && t.lenM <= s.maxLen) stands[s.name][t.typeKey] = [60, 47, 30, 1]; }
  }
  return { v: 1, src: 'inf', note: 'STUB (tools/sim/test_plan.mjs) until data/sha_gate_times exists', stands };
}
let GT = stubGateTimes(), gtKind = 'stub';
const gtPath = path.join(ROOT, 'data/sha_gate_times.json');
if (fs.existsSync(gtPath)) { try { GT = J('data/sha_gate_times.json'); gtKind = 'P3-E table'; } catch { /* keep stub */ } }
console.log(`gate times: ${gtKind}`);

// ---- local overlays (in memory only)
const haveLocal = fs.existsSync(path.join(ROOT, 'refs/cache/observed_elsewhere/sha_observed_2026-11-12.json'));
const overlays = {};
if (haveLocal) for (const d of OBS_DAYS) overlays[d] = JSON.parse(execFileSync('python3', ['-I', path.join(ROOT, 'tools/sim/observed_overlay.py'), '--day', d], { maxBuffer: 64 << 20 }));

const build = (day, overlay = null, extra = {}) => buildDayPlan({ day, inputs: I, stands: STANDS, overlay, gateTimes: GT, ...extra });

// ------------------------------------------------------------------------------------------------ independent checks
function standViolations(plan) {
  const T = standTable(STANDS), buf = P.bufferS * 1000;
  const clos = closureWindows(I.notams);
  const byStand = new Map();
  const byId = new Map(plan.movements.map(m => [m.id, m]));
  // buffer (design s.2.4, verification fix round 1, F6): consecutive occupants of a stand (and of an exclusive pair) are at
  // least bufferS apart: two unbuffered ground visits conflict when the gap between them is below bufferS
  let overlap = 0, excl = 0, cls = 0, closure = 0, unknown = 0, order = 0, minGap = Infinity;
  const gapOf = (x, y) => Math.max(x[0], y[0]) - Math.min(x[1], y[1]);      // > 0: the free time between two intervals
  for (const [name, L] of Object.entries(plan.stands)) {
    const s = T.byName.get(name);
    if (!s) { unknown += L.length; continue; }
    const iv = L.map(e => [e.from, e.to, e]);
    byStand.set(name, iv);
    for (let i = 0; i < iv.length; i++) for (let j = i + 1; j < iv.length; j++) {
      const g = gapOf(iv[i], iv[j]); minGap = Math.min(minGap, g); if (g < buf) overlap++;
    }
    for (const [a, b, e] of iv) {
      const m = byId.get(e.mv); const t = typeInfo(m.icao, I);
      if (!(t.spanM <= s.maxSpan && t.lenM <= s.maxLen)) cls++;
      const a2 = a === plan.t0 ? a : a - buf, b2 = b === plan.t1 ? b : b + buf;
      for (const w of clos.get(name) || []) if (a2 < w[1] && w[0] < b2) closure++;
      if (e.to < e.from) order++;
    }
  }
  for (const [name, iv] of byStand) {
    for (const e of T.byName.get(name).excl) {
      if (e < name) continue;
      const jv = byStand.get(e) || [];
      for (const x of iv) for (const y of jv) { const g = gapOf(x, y); minGap = Math.min(minGap, g); if (g < buf) excl++; }
    }
  }
  return { overlap, excl, cls, closure, unknown, order, minGapMin: Math.round(minGap / 6000) / 10 };
}

function hourlyBand(plan) {
  const tgt = plan.stats.byHour.target, n = plan.stats.byHour.sched;
  let worst = 0, bad = [];
  for (const role of ['arr', 'dep']) for (let h = 0; h < 24; h++) {
    const d = Math.abs(n[role][h] - tgt[role][h]), lim = Math.max(2, 0.1 * tgt[role][h]);
    worst = Math.max(worst, d - lim);
    if (d > lim) bad.push(`${role}${h}:${n[role][h]}/${tgt[role][h]}`);
  }
  return { worst, bad };
}

// delayed counts against the profile convolved with the delay distribution (design s.5, review L11): reported
function delayedBand(plan) {
  const D = I.delays.bands, tgt = plan.stats.byHour.target, n = plan.stats.byHour.rwy;
  const conv = { arr: new Array(24).fill(0), dep: new Array(24).fill(0) };
  for (const role of ['arr', 'dep']) for (let h = 0; h < 24; h++) {
    for (const b of D) {                     // spread each hour's target uniformly over [h*60 + min, h*60 + 60 + max] minutes
      const a0 = h * 60 + b.minS / 60, a1 = h * 60 + 60 + b.maxS / 60, w = a1 - a0;
      for (let k = Math.floor(a0 / 60); k <= Math.floor((a1 - 1e-9) / 60); k++) {
        const lo = Math.max(a0, k * 60), hi = Math.min(a1, k * 60 + 60);
        if (hi > lo) conv[role][((k % 24) + 24) % 24] += tgt[role][h] * b.p * (hi - lo) / w;
      }
    }
  }
  let bad = 0;
  for (const role of ['arr', 'dep']) for (let h = 0; h < 24; h++) if (Math.abs(n[role][h] - conv[role][h]) > Math.max(2, 0.1 * conv[role][h]) + 1) bad++;
  return bad;
}

const share = (ms, f) => { const c = {}; for (const m of ms) { const k = f(m); c[k] = (c[k] || 0) + 1; } for (const k in c) c[k] /= ms.length; return c; };
// fill rotations (verification fix round 1, F5): scheduled runway-time gap of every fill turn (arrival -> departure of one
// airframe, both tier 4) against the input quantiles (runway-time gaps of observed same-airframe pairs), and the ground time
const TA = I.turnaround;
function fillTurns(plan, all = false) {          // all: every arrival -> departure turn of one airframe, whatever its tier
  const by = plan._byId, gr = [], gb = []; let atMin = 0, ltP10 = 0;
  for (const m of plan.movements) if (m.role === 'dep' && m.prev && (all || m.tier === 'inf') && !m.biz) {
    const a = by.get(m.prev); if (!a || (!all && a.tier !== 'inf')) continue;
    const minS = typeInfo(a.icao, I).wide ? TA.minWideS : TA.minNarrowS;
    gr.push((m.tSched - a.tSched) / 1000); gb.push((m.tBlock - a.tBlock) / 1000);
    if ((m.tBlock - a.tBlock) / 1000 <= minS + 60) atMin++;
    if ((m.tSched - a.tSched) / 1000 < TA.p10) ltP10++;
  }
  gr.sort((x, y) => x - y); gb.sort((x, y) => x - y);
  const q = (g, f) => g.length ? g[Math.floor(f * (g.length - 1))] / 60 : NaN;
  return { n: gr.length, rwy: [q(gr, 0.1), q(gr, 0.5), q(gr, 0.9)], ground: [q(gb, 0.1), q(gb, 0.5), q(gb, 0.9)],
    atMinPct: 100 * atMin / Math.max(1, gr.length), belowP10Pct: 100 * ltP10 / Math.max(1, gr.length), rushed: plan.stats.counters.rushed };
}
const TURN_BAND_MIN = 15, BELOW_P10_MAX = 15, AT_MIN_MAX = 12;       // [inf] test bands (input P10 share is 10 % by definition)
// [inf] the local fill is the RESIDUAL of an observed day (target - observed - continuations per hour: arrivals heavy in
// 14-23 h, departures in 07-10 h, 43-45 turns): its P50 band is +-30 min (verification fix round 2, F17; owner-visible in
// plan.md); P10, below P10 and at the minimum keep the whole-day bands
const TURN_BAND_LOCAL_P50 = 30;
const fmtQ = (a) => a.map(x => x.toFixed(0)).join(' / ');
function checkTurns(label, plan, all = false, p50Band = TURN_BAND_MIN) {
  const t = fillTurns(plan, all), inp = [TA.p10 / 60, TA.p50 / 60, TA.p90 / 60];
  const f = fmtQ;
  const txt = `${t.n} turns; runway gap P10/P50/P90 ${f(t.rwy)} min (input ${f(inp)}); ground ${f(t.ground)} min; below input P10 ${t.belowP10Pct.toFixed(1)} %; at the minimum ${t.atMinPct.toFixed(1)} %; rushed ${t.rushed}`;
  if (all) { console.log(`info  ${label} all turns (observed, continuations, fill; not a test: the input quantiles come from the observed pairs): ${txt}`); return t; }
  check(`${label} fill turns: runway-gap P50 within +-${p50Band} min of the input, P10 within +-${TURN_BAND_MIN}, < input P10 <= ${BELOW_P10_MAX} %, ground time at the type minimum <= ${AT_MIN_MAX} %`,
    Math.abs(t.rwy[1] - inp[1]) <= p50Band && Math.abs(t.rwy[0] - inp[0]) <= TURN_BAND_MIN && t.belowP10Pct <= BELOW_P10_MAX && t.atMinPct <= AT_MIN_MAX, txt);
  return t;
}

const maxDiff = (A, B) => { let w = 0, k0 = null; for (const k of new Set([...Object.keys(A), ...Object.keys(B)])) { const d = Math.abs((A[k] || 0) - (B[k] || 0)) * 100; if (d > w) { w = d; k0 = k; } } return [w, k0]; };

// ------------------------------------------------------------------------------------------------ public plans
const plans = {};
for (const day of DAYS_PUBLIC) {
  const t = performance.now();
  plans[day] = build(day);
  const ms = performance.now() - t;
  const p = plans[day], s = p.stats;
  console.log(`\n== ${day} public plan: ${p.movements.length} movements, tiers ${JSON.stringify(p.tiers)}, weightSet ${p.weightSet}, ` +
    `build ${ms.toFixed(0)} ms, hash ${p.hash}`);
  console.log(`   night-stoppers ${JSON.stringify(s.nightStop)} (parked by stand side ${JSON.stringify(s.nightStopParked)}), flow bound ${s.flowBound} ` +
    `(with minimum turn ${s.flowBoundTurn}), crossSide ${s.crossSide}, diverted ${s.diverted}, contact share ${JSON.stringify(s.contactShare)}`);
  for (const sd of ['T1', 'T2']) { const b = s.bySide[sd]; console.log(`   ${sd}: max ${b.max}/${b.cap}, A330/B787-class ${b.wideMax}/${b.wideCap}, A350/B77W-class ${b.elMax}/${b.elCap}, own-side demand ${b.demandMax} (wide ${b.demandWideMax}, EL ${b.demandElMax})`); }
}

// 1. totals
for (const day of DAYS_PUBLIC) {
  const p = plans[day], N = p.stats.total.target;
  const n = p.stats.byHour.sched.arr.reduce((a, b) => a + b, 0) + p.stats.byHour.sched.dep.reduce((a, b) => a + b, 0);
  check(`${day} day total within +-2 % (scheduled, drawn)`, Math.abs(n - N) <= 0.02 * N, `${n} vs target ${N}`);
}
// 2. hourly band
for (const day of DAYS_PUBLIC) { const r = hourlyBand(plans[day]); check(`${day} hourly |n - target| <= max(2, 10 %) (scheduled)`, r.bad.length === 0, r.bad.length ? r.bad.join(' ') : 'all 48 role-hours'); }
for (const day of DAYS_PUBLIC) console.log(`info  ${day} delayed counts vs the delay-convolved profile: ${delayedBand(plans[day])} of 48 role-hours outside max(2, 10 %) + 1`);
// 3. night
for (const day of DAYS_PUBLIC) {
  const p = plans[day];
  const night = p.movements.filter(m => { const h = localHour(m.tSched, I); return h >= P.nightNoSched.fromLocalH && h < P.nightNoSched.toLocalH; }).length;
  const nightDelayed = p.movements.filter(m => { const h = localHour(m.tRwy, I); return h >= P.nightNoSched.fromLocalH && h < P.nightNoSched.toLocalH; });
  const nightArr = nightDelayed.filter(m => m.role === 'arr');
  check(`${day} 0 scheduled slots 01:00-05:59 local; 0 arrivals in the night while F4551 is in force`, night === 0 && nightArr.length === 0,
    `${night} scheduled; ${nightDelayed.length} delayed into the night (arrivals ${nightArr.length}, diverted to Pudong ${p.stats.diverted})`);
}
// 4. types
for (const day of DAYS_PUBLIC) {
  const p = plans[day];
  const bad = p.movements.filter(m => !(TYPE_MODELS[m.icao] || (TYPE_MODELS[m.model] && P.standIns[m.icao]) || (m.biz && BIZ[m.icao])));
  const standIn = p.movements.filter(m => m.model !== m.icao).length;
  check(`${day} every type in TYPE_MODELS or with a stand-in model`, bad.length === 0, `${bad.length} invalid; ${standIn} with a stand-in model`);
}
// 5. stands
for (const day of DAYS_PUBLIC) {
  const v = standViolations(plans[day]);
  check(`${day} 0 overlap / excl / class / closure violations (gap between occupants >= ${P.bufferS / 60} min)`, !v.overlap && !v.excl && !v.cls && !v.closure && !v.unknown && !v.order && v.minGapMin >= P.bufferS / 60, JSON.stringify(v));
}
// 6. capacity per side x class
for (const day of DAYS_PUBLIC) {
  const s = plans[day].stats; let ok = true; const parts = [];
  for (const sd of ['T1', 'T2', 'BIZ']) { const b = s.bySide[sd]; if (b.max > b.cap || b.wideMax > Math.max(b.wideCap, 0) || b.elMax > b.elCap) ok = false; parts.push(`${sd} ${b.max}/${b.cap} w ${b.wideMax}/${b.wideCap} el ${b.elMax}/${b.elCap}`); }
  check(`${day} occupancy per side x class within capacity (overflow counted: crossSide ${s.crossSide})`, ok, parts.join('; '));
}
// 7. unplaced
for (const day of ['2026-11-12', '2026-11-20']) check(`${day} unplaced 0`, plans[day].stats.unplaced === 0, `unplaced ${plans[day].stats.unplaced}`);
for (const day of DAYS_PUBLIC) console.log(`info  ${day} unplaced ${plans[day].stats.unplaced}, night-stoppers parked above cap: T1 ${plans[day].stats.nightStopParked.T1}/${plans[day].stats.bySide.T1.nightStopCap}, T2 ${plans[day].stats.nightStopParked.T2}/${plans[day].stats.bySide.T2.nightStopCap}`);
// 8. contact share
for (const day of DAYS_PUBLIC) { const c = plans[day].stats.contactShare; check(`${day} contact share per side in 60-85 %`, c.T1 >= 0.6 && c.T1 <= 0.85 && c.T2 >= 0.6 && c.T2 <= 0.85, `T1 ${(c.T1 * 100).toFixed(1)} %, T2 ${(c.T2 * 100).toFixed(1)} %`); }
// 8b. fill-turn distribution (F5); every rotation keeps its airline and type (business jets included)
for (const day of DAYS_PUBLIC) checkTurns(day, plans[day]);
for (const day of DAYS_PUBLIC) {
  const p = plans[day]; let swap = 0, n = 0;
  for (const m of p.movements) if (m.prev) { n++; const a = p._byId.get(m.prev); if (a.icao !== m.icao || a.airline !== m.airline) swap++; }
  check(`${day} every rotation keeps airline and type`, swap === 0, `${swap} of ${n}`);
}
// 11. determinism
for (const day of ['2026-11-12', '2026-11-20']) { const a = build(day), b = build(day); check(`${day} identical hash on two builds`, a.hash === b.hash && a.hash === plans[day].hash, a.hash); }
// 12. build time
{
  const t = []; for (let i = 0; i < 5; i++) { const t0 = performance.now(); build('2026-11-20'); t.push(performance.now() - t0); }
  t.sort((a, b) => a - b);
  check('plan build <= 200 ms (node, median of 5)', t[2] <= 200, `median ${t[2].toFixed(0)} ms, max ${t[4].toFixed(0)} ms`);
}
// 13. the public 12 Nov plan has no identity field
{
  const p = plans['2026-11-12'];
  const idf = p.movements.filter(m => m.ident != null || m.sigmaS != null || (m.flight != null && m.tier !== 'pub')).length;
  const regs = p.airframes.filter(a => 'reg' in a).length;
  const ALLOWED = new Set(['id', 'slot', 'role', 'af', 'airline', 'icao', 'model', 'typeKey', 'wake', 'tier', 'tSched', 'tRwy', 'delayS', 'tBlock',
    'stand', 'side', 'contact', 'overflow', 'prev', 'next', 'startsParked', 'endsParked', 'ident', 'sigmaS', 'flight', 'intl', 'src', 'far', 'farDate', 'typePublished', 'biz']);
  const extra = new Set(); for (const m of p.movements) for (const k of Object.keys(m)) if (!ALLOWED.has(k)) extra.add(k);
  const slots = p.movements.filter(m => /^(oe|rep):/.test(m.slot)).length;
  check('public 12 Nov plan: no identity field (no oe / rep slot, ident / sigmaS / flight null, no airframe reg)',
    !idf && !regs && !extra.size && !slots && p.tiers.oe === 0 && !p.tiers.rep && p.identity === 'none',
    `ident/flight ${idf}, reg ${regs}, unknown fields ${[...extra].join(',') || 0}, oe/rep slots ${slots}, identity '${p.identity}'`);
  const noOv = labelFor(p.movements[0], null, { inputs: I });
  check('labelFor without an overlay never yields an identity', noOv.chips.join() === 'inf' && /Simulated flight \(inferred\)/.test(noOv.lines[0]), noOv.row);
}
// 3b. tier 3 on its own date only (Q1b)
{
  const n13 = plans['2026-11-13'].tiers.pub, n14 = plans['2026-11-14'].tiers.pub, o = DAYS_PUBLIC.filter(d => !['2026-11-13', '2026-11-14'].includes(d)).reduce((s, d) => s + plans[d].tiers.pub, 0);
  check('published HKG / TSA rows only on their own date (13 / 14 Nov)', n13 === I.published.hkg.length && n14 === I.published.tsa.length && o === 0, `13 Nov ${n13}, 14 Nov ${n14}, other days ${o}`);
  const m = plans['2026-11-13'].movements.find(x => x.tier === 'pub');
  const L = labelFor(m, null, { inputs: I });
  check('tier-3 card text as design s.6.1', L.chips.join() === 'published,inf' && L.lines[0].startsWith('Flight number from the published Hong Kong airport schedule of 13 Nov 2026 (Airport Authority Hong Kong, via DATA.GOV.HK).'), L.lines[0].slice(0, 60) + '...');
  const off = build('2026-11-13', null, { opts: { published: false } });
  check('switch published=false removes tier 3 (reversible by one switch)', off.tiers.pub === 0, `pub ${off.tiers.pub}`);
}
// 9. non-observed day mix vs the observed days' full plans (fullDay)
{
  let ref;
  if (haveLocal) {
    const ps = OBS_DAYS.map(d => build(d, overlays[d]));
    const a = (f) => { const x = share(ps[0].movements, f), y = share(ps[1].movements, f); const o = {}; for (const k of new Set([...Object.keys(x), ...Object.keys(y)])) o[k] = ((x[k] || 0) + (y[k] || 0)) / 2; return o; };
    ref = { A: a(m => m.airline || 'BIZ'), T: a(m => m.icao), src: 'the local overlay plans of 10 / 12 Nov' };
  } else {
    const A = { ...I.weights.fullDay }; const T = {};
    for (const [al, w] of Object.entries(I.weights.fullDay)) { const mix = I.typeMix.fullDay[al] || {}; const s = Object.values(mix).reduce((x, y) => x + y, 0) || 1; for (const [t, n] of Object.entries(mix)) T[t] = (T[t] || 0) + w * n / s; }
    ref = { A, T, src: 'inputs.weights.fullDay / typeMix.fullDay (no local overlay)' };
  }
  for (const day of ['2026-11-13', '2026-11-14', '2026-11-20']) {
    const p = plans[day];
    const [dA, kA] = maxDiff(share(p.movements, m => m.airline || 'BIZ'), ref.A), [dT, kT] = maxDiff(share(p.movements, m => m.icao), ref.T);
    check(`${day} airline and type mix within +-3 points of ${ref.src}`, dA <= 3 && dT <= 3, `max airline diff ${dA.toFixed(2)} (${kA}), max type diff ${dT.toFixed(2)} (${kT === 'other' ? 'other' : kT})`);
  }
}
// warm start (design s.2.2 step 10)
{
  const d19 = build('2026-11-19'), e = endState(d19, I);
  const p = build('2026-11-20', null, { prevEnd: e });
  const same = p.movements.filter(m => m.startsParked).filter(m => e.entries.some(x => x.stand === m.stand)).length;
  console.log(`info  warm start 19 -> 20 Nov: ${e.entries.length} parked at the end of 19 Nov; 20 Nov night-stoppers on one of those stands: ${same} (preferred ${p.stats.preferredStands}); unplaced ${p.stats.unplaced}`);
  check('warm-start plan keeps unplaced 0, is deterministic and stays public (endState identity none)', p.stats.unplaced === 0 && build('2026-11-20', null, { prevEnd: e }).hash === p.hash
    && e.identity === 'none' && p.identity === 'none' && p.stats.prevEnd.used, `${p.hash}, identity ${p.identity}`);
  const bare = build('2026-11-20', null, { prevEnd: e.entries }), none = build('2026-11-20');
  check('a bare end-state array (identity unknown) is ignored unless opts.localPrev (F15)', bare.hash === none.hash && bare.identity === 'none' && bare.stats.prevEnd.ignored,
    `ignored ${bare.stats.prevEnd.ignored}`);
}
// checkOverlay on synthetic records (placeholder identities only: XXX, ZZ-SIM*)
{
  const syn = { v: 1, day: '2026-11-12', tier: 'oe', records: [
    { uid: 'u1', role: 'arr', airline: 'XXX', cs: 'XXXSIM1', flight: 'XX1', reg: 'ZZ-SIM1', type: 'A320', operator: 'Sim', far: 'ZBAA', t_sha: 1794460000, sigma_s: 300, icao: 'fff0a1', evidence: 'x' },
    { uid: 'u2', role: 'dep', airline: 'XXX', cs: 'fff0a1', flight: null, reg: 'ZZ-SIM2', type: 'A320', operator: 'Sim', far: 'ZBAA', t_sha: 1794460000, sigma_s: 300 },
    { uid: 'u3', role: 'dep', airline: 'XXX', cs: 'XXXSIM3', flight: null, reg: 'ZZ-SIM3', type: 'a320', operator: 'Sim', far: 'ZBAA', t_sha: 1794460000, sigma_s: 300 },
    { uid: 'u4', role: 'dep', airline: 'XXX', cs: 'XXXSIM4', flight: 'XX4', reg: 'ZZ-SIM4', type: 'B738', operator: 'Sim', far: 'ZBAA', t_sha: 1794461000, sigma_s: 60 }] };
  const o = checkOverlay(syn, { day: '2026-11-12' });
  const fieldsOk = o.records.every(r => Object.keys(r).every(k => OVERLAY_FIELDS.includes(k)));
  check('checkOverlay keeps the allow-list, drops 6-hex values and bad types', o && o.records.length === 2 && o.dropped === 2 && fieldsOk && checkOverlay(syn, { day: '2026-11-10' }) === null && checkOverlay({ available: false }) === null,
    `${o.records.length} kept, ${o.dropped} dropped`);
  const L = labelFor({ tier: 'oe', ident: 'u4', icao: 'B738', model: 'B738', airline: 'XXX', side: 'T2', role: 'dep' }, o, { inputs: I });
  check('tier-2 card text as design s.6.1 (synthetic)', L.lines[0] === 'Identity observed elsewhere: open ADS-B saw this flight outside the Shanghai coverage gap on 12 Nov 2026. Its time at Hongqiao is inferred (±1 min, 1σ). Stand, taxi route, runway and position are simulated.' && L.chips.join() === 'obs elsewhere,inf', L.title);
  check('day line without identities', dayLine(plans['2026-11-20'], null, I) === 'No real identities for this day: flights observed elsewhere exist for 10 and 12 Nov 2026 only.', dayLine(plans['2026-11-20'], null, I));
  check('repeat-flight switch (Q1) off by default: tiers.rep 0 on every public plan', DAYS_PUBLIC.every(d => !plans[d].tiers.rep), 'rep 0');
}

// ------------------------------------------------------------------------------------------------ local overlay part
if (haveLocal) {
  for (const day of OBS_DAYS) {
    const ov = overlays[day];
    const t = performance.now();
    const p = build(day, ov);
    const ms = performance.now() - t;
    const s = p.stats;
    const inWin = ov.records.filter(r => r.t_sha * 1000 >= p.t0 && r.t_sha * 1000 < p.t1).length;
    const contBy = {}; for (const m of p.movements) if (m.tier === 'cont') contBy[m.side] = (contBy[m.side] || 0) + 1;
    console.log(`\n== ${day} LOCAL overlay plan (counts only): ${p.movements.length} movements, tiers ${JSON.stringify(p.tiers)}, weightSet ${p.weightSet}, build ${ms.toFixed(0)} ms`);
    console.log(`   identified ${ov.records.length}, out of window ${s.counters.outOfWindow}, continuations by side ${JSON.stringify(contBy)}, night-stoppers ${JSON.stringify(s.nightStop)} (parked ${JSON.stringify(s.nightStopParked)}), crossSide ${s.crossSide}, contact ${JSON.stringify(s.contactShare)}`);
    for (const sd of ['T1', 'T2']) { const b = s.bySide[sd]; console.log(`   ${sd}: max ${b.max}/${b.cap}, A330/B787-class ${b.wideMax}/${b.wideCap}, A350/B77W-class ${b.elMax}/${b.elCap}, own-side demand ${b.demandMax} (wide ${b.demandWideMax}, EL ${b.demandElMax})`); }
    check(`${day} (local) tier 2 = identified - out of window`, p.tiers.oe === inWin && inWin === ov.records.length - s.counters.outOfWindow, `${p.tiers.oe} = ${ov.records.length} - ${s.counters.outOfWindow}`);
    check(`${day} (local) 0 tier-2 delays`, p.movements.filter(m => m.tier === 'oe' && (m.delayS !== 0 || m.tRwy !== m.tSched)).length === 0, 'delayS 0 for every tier-2 movement');
    const v = standViolations(p);
    check(`${day} (local) 0 overlap / excl / class / closure violations (gap >= ${P.bufferS / 60} min)`, !v.overlap && !v.excl && !v.cls && !v.closure && v.minGapMin >= P.bufferS / 60, JSON.stringify(v));
    check(`${day} (local) unplaced 0`, s.unplaced === 0, `unplaced ${s.unplaced}`);
    let capOk = true; for (const sd of ['T1', 'T2']) { const b = s.bySide[sd]; if (b.max > b.cap || b.wideMax > b.wideCap || b.elMax > b.elCap) capOk = false; }
    check(`${day} (local) occupancy per side x class within capacity (crossSide ${s.crossSide})`, capOk, '');
    const r = hourlyBand(p);
    check(`${day} (local) hourly |n - target| <= max(2, 10 %) (scheduled)`, r.bad.length === 0, r.bad.length ? `${r.bad.length} role-hours outside` : 'all 48 role-hours');
    const n = p.movements.length, N = s.total.target;
    check(`${day} (local) day total within +-2 %`, Math.abs(n - N) <= 0.02 * N, `${n} vs ${N}`);
    check(`${day} (local) identical hash on two builds`, build(day, ov).hash === p.hash, '');
    check(`${day} (local) plan build <= 200 ms`, ms <= 200, `${ms.toFixed(0)} ms`);
    checkTurns(`${day} (local, the residual of the observed day)`, p, false, TURN_BAND_LOCAL_P50);
    checkTurns(`${day} (local)`, p, true);
    // F19: the registration is shown per movement, tier 2 only; a continuation of the same airframe carries none
    {
      const regMv = p.movements.filter(m => 'reg' in m), badMv = regMv.filter(m => m.tier !== 'oe').length;
      const contReg = p.movements.filter(m => m.tier === 'cont' && 'reg' in m).length;
      const afReg = p.airframes.filter(a => 'reg' in a), badAf = afReg.filter(a => JSON.stringify(a.regTiers) !== '["oe"]').length;
      check(`${day} (local) registration only on tier-2 movements (movement.reg), airframes.regTiers ['oe'] (F19)`, !badMv && !contReg && !badAf && regMv.length > 0,
        `${regMv.length} tier-2 movements with reg, ${badMv} other; ${contReg} continuation movements with reg; airframes with reg ${afReg.length}, regTiers wrong ${badAf}`);
    }
    // observed same-airframe arrival -> departure pairs whose ground time is below the type minimum (t_sha kept: the
    // scheduler's holds must stretch them; F10): counts only
    console.log(`info  ${day} (local) tier-2 pairs with a ground time below the type minimum: ${s.counters.tier2ShortTurns} (of them <= 0: ${s.counters.tier2NoGround})`);
    check(`${day} (local) no stand occupancy with a negative ground time`, Object.values(p.stands).every(L => L.every(e => e.to >= e.from)), `tier-2 short pairs ${s.counters.tier2ShortTurns}`);
    // identity=0 equivalence: overlay null gives exactly the public plan
    check(`${day} (local) ?identity=0 = overlay null = the public plan`, build(day, null).hash === plans[day].hash, '');
  }
  // F15: the end state of a LOCAL plan carries the observed airframes' last stands: a public plan of the next day ignores
  // it (identity stays 'none', hash = the plan without a warm start); with opts.localPrev it is used and marked 'derived'
  {
    const loc12 = build('2026-11-12', overlays['2026-11-12']), eL = endState(loc12, I), eP = endState(plans['2026-11-12'], I);
    const ign = build('2026-11-13', null, { prevEnd: eL }), none = build('2026-11-13'), pub = build('2026-11-13', null, { prevEnd: eP });
    const der = build('2026-11-13', null, { prevEnd: eL, opts: { localPrev: true } });
    check('(local) a local end state (identity overlay) is ignored by a public plan: identity none, hash = no warm start (F15)',
      eL.identity === 'overlay' && ign.identity === 'none' && ign.hash === none.hash && ign.stats.prevEnd.ignored && ign.tiers.oe === 0,
      `endState identity ${eL.identity}; plan identity ${ign.identity}, ignored ${ign.stats.prevEnd.ignored}`);
    check('(local) with opts.localPrev the local end state is used and the plan is marked identity derived (hash differs) (F15)',
      der.identity === 'derived' && der.stats.prevEnd.used && der.hash !== pub.hash && der.hash !== none.hash && pub.identity === 'none',
      `identity ${der.identity}; public-prevEnd plan identity ${pub.identity}`);
  }
  const reps = repCandidates(OBS_DAYS.map(d => checkOverlay(overlays[d])), I);
  console.log(`info  (local) Q1 repeat-flight candidates (switch OFF by default): ${reps.length}`);
} else console.log('\n(no local observed-elsewhere tables: overlay part skipped)');

// ---- PLOTS=1: aggregates for docs/phase3/plan_*.png -> out/phase3/plan/aggregates.json (gitignored; counts and shares only)
if (process.env.PLOTS) {
  const occ = (p, side, pred) => {         // occupancy per 10 min on a side's stands (physical), 04:00 -> 04:00
    const T = standTable(STANDS), out = new Array(144).fill(0);
    for (const [name, L] of Object.entries(p.stands)) {
      if (T.byName.get(name).side !== side) continue;
      for (const e of L) {
        const m = p._byId.get(e.mv); if (pred && !pred(m)) continue;
        for (let k = 0; k < 144; k++) { const t = p.t0 + k * 600000; if (t >= e.from && t < e.to) out[k]++; }
      }
    }
    return out;
  };
  const wide = (m) => typeInfo(m.icao, I).wide;
  const agg = (p) => {
    const tierHour = {};
    for (const role of ['arr', 'dep']) { tierHour[role] = {}; for (const t of ['oe', 'cont', 'pub', 'inf']) tierHour[role][t] = new Array(24).fill(0); }
    for (const m of p.movements) tierHour[m.role][m.tier === 'rep' ? 'inf' : m.tier][localHour(m.tSched, I)]++;
    return { day: p.day, tiers: p.tiers, target: p.stats.byHour.target, tierHour, rwy: p.stats.byHour.rwy,
      occ: { T1: occ(p, 'T1'), T2: occ(p, 'T2'), T1w: occ(p, 'T1', wide), T2w: occ(p, 'T2', wide) },
      cap: { T1: p.stats.bySide.T1.cap, T2: p.stats.bySide.T2.cap, T1w: p.stats.bySide.T1.wideCap, T2w: p.stats.bySide.T2.wideCap },
      airline: share(p.movements, m => m.airline || 'BIZ'), contactShare: p.stats.contactShare };
  };
  const out = { note: 'aggregates only (OD4); stand occupancy of PUBLIC plans only (verification fix round 2, F14)', fullDay: I.weights.fullDay, public: {}, local: {} };
  for (const d of DAYS_PUBLIC) out.public[d] = agg(plans[d]);
  if (haveLocal) for (const d of OBS_DAYS) {
    const a = agg(build(d, overlays[d]));
    out.local[d] = { day: a.day, airline: a.airline, contactShare: a.contactShare, tierHour: a.tierHour };   // no occupancy, no hourly runway counts
  }
  // F14: every plotted occupancy series comes from a plan with identity 'none' and tier 2 = 0, so no 10-min step of a plot
  // can be caused by one observed movement (counted, must be 0)
  {
    let single = 0, series = 0;
    for (const d of Object.keys(out.public)) {
      const p = plans[d];
      if (p.identity !== 'none' || p.tiers.oe) single += 1e6;
      for (const L of Object.values(p.stands)) for (const e of L) for (const id of [e.arr, e.dep]) if (id && p._byId.get(id).tier === 'oe') single++;
      series += 4;
    }
    const leaked = Object.values(out.local).filter(x => 'occ' in x || 'rwy' in x).length;
    check('PLOTS: stand-occupancy series only from public plans (identity none): 0 steps from an observed movement, no local occupancy kept (F14)',
      single === 0 && leaked === 0, `${series} series, observed-movement boundaries ${single}, local days with occupancy ${leaked}`);
  }
  // the observed days pooled (verification fix round 1, F7): two-day SUM per local hour and role of the observed-elsewhere
  // movements plus their continuations ('identified') and of the fill; an identified cell with a two-day sum of 1 or 2 is
  // merged into the fill of that hour, so no plotted cell points to one or two flights
  if (haveLocal) {
    const pooled = { merged: 0 };
    for (const role of ['arr', 'dep']) {
      const id = new Array(24).fill(0), fl = new Array(24).fill(0);
      for (const d of OBS_DAYS) { const th = out.local[d].tierHour[role]; for (let h = 0; h < 24; h++) { id[h] += th.oe[h] + th.cont[h]; fl[h] += th.inf[h] + th.pub[h]; } }
      for (let h = 0; h < 24; h++) if (id[h] > 0 && id[h] < 3) { fl[h] += id[h]; id[h] = 0; pooled.merged++; }
      pooled[role] = { identified: id, fill: fl };
    }
    out.pooled = pooled;
    for (const d of OBS_DAYS) delete out.local[d].tierHour;       // the per-day tier split is not kept (F7)
  }
  fs.mkdirSync(path.join(ROOT, 'out/phase3/plan'), { recursive: true });
  fs.writeFileSync(path.join(ROOT, 'out/phase3/plan/aggregates.json'), JSON.stringify(out));
  console.log('wrote out/phase3/plan/aggregates.json (aggregates only)');
}

const bad = results.filter(r => !r.ok);
console.log(`\n${results.length - bad.length} / ${results.length} checks passed`);
process.exit(bad.length ? 1 : 0);
