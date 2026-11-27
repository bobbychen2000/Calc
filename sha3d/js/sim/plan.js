// SHA Live 3D Phase 3 (package P3-A): the day plan. buildDayPlan(...) -> DayPlan exactly as docs/phase3/design.md s.7.1
// (frozen interface: fields may be added, never renamed); algorithm s.2.2, terminal / type rules s.2.3, stands s.2.4
// (js/sim/alloc.js), NOTAMs / night s.2.5, other days and labels s.2.6, identity s.3 (OD4).
// Pure ES module (node + browser): it imports only js/sim/*, js/aircraft/types.js; every window datum (inputs, stands,
// overlay, gate times) is passed in. Integer ms / s arithmetic and seeded integer draws (js/sim/rng.js): the same plan and
// the same plan.hash on every engine for the same inputs.
//
// Tiers (OD2 order): 'oe' observed elsewhere (only with a local overlay; ?identity=0 = overlay null = the public plan),
// 'pub' published HKG / TSA rows on their own date (owner default Q1b), 'rep' flight numbers seen on other days (owner
// question Q1: OFF by default, needs the local overlays), 'cont' continuations of observed airframes (airline + type only),
// 'inf' the fill (airline + type from the Hongqiao mix). Every slot is src 'inf' for position, stand, route and time.

import { PLAN_VERSION, daySeed, draw, drawInt, drawRange, drawPermille, PURPOSE, shuffled, hashOf, apportion } from './rng.js';
import { dayWindow, localHour, hourStart, totalFor, noLandingAt } from './inputs.js';
import { allocate, standTable, closureWindows } from './alloc.js';
import { checkOverlay } from './identity.js';
import { TYPES, ICAO_TYPES } from '../aircraft/types.js';

const S = 1000, MIN = 60000, H = 3600000;
const WIDE = new Set(['A332', 'A333', 'A338', 'A339', 'A359', 'A35K', 'B762', 'B763', 'B764', 'B772', 'B773', 'B77L', 'B77W',
  'B788', 'B789', 'B78X', 'B744', 'B748', 'A388', 'A306', 'MD11']);
// generic business jets (js/aircraft/fit.js BIZ: FAA Aircraft Characteristics Database [length, span] m)
const BIZ_DIMS = { CL60: [20.85, 19.60], C68A: [18.99, 22.04], CL35: [20.91, 21.00], G280: [20.36, 19.20] };
const MAINLAND = /^(ZB|ZG|ZH|ZJ|ZL|ZP|ZS|ZU|ZW|ZY)/;
const TIER_RANK = { oe: 0, cont: 1, pub: 2, rep: 3, inf: 4 };

/** type facts for the plan: {icao, model (ICAO of the drawn model), typeKey, spanM, lenM, wide, size, family, wake, standIn} */
export function typeInfo(icao, inputs) {
  const si = inputs && inputs.params && inputs.params.standIns ? inputs.params.standIns[icao] : null;
  const model = si ? si.model : icao;
  const key = ICAO_TYPES[model] || null;
  const T = key ? TYPES[key] : null;
  let spanM, lenM, typeKey = key, unknown = false;
  if (si) { spanM = si.spanM; lenM = si.lenM; }
  else if (T) { spanM = T.wing.span; lenM = T.L; }
  else if (BIZ_DIMS[icao]) { lenM = BIZ_DIMS[icao][0]; spanM = BIZ_DIMS[icao][1]; typeKey = 'biz_' + icao; }
  else { spanM = 35.8; lenM = 44.5; unknown = true; }
  const wide = WIDE.has(icao) || spanM > 41.2;
  const size = !wide ? 'narrow' : (spanM > 60.5 || lenM > 64.0) ? 'el' : 'wide';
  const fam = (inputs && inputs.families && inputs.families[icao]) || (wide ? 'wide-body' : BIZ_DIMS[icao] ? 'business' : 'other');
  const wake = icao === 'A388' ? 'J' : wide ? 'H' : 'M';
  return { icao, model, typeKey, spanM, lenM, wide, size, family: fam, wake, standIn: !!si, unknown };
}

/** piecewise-linear inverse CDF through the turnaround quantiles (s), clamped to the type minimum */
function drawTurnS(seed, key, TA, wide) {
  const u = drawPermille(seed, key, PURPOSE.TURN);
  const minS = wide ? TA.minWideS : TA.minNarrowS;
  const lo = Math.max(minS, TA.p10 - ((TA.p50 - TA.p10) >> 1)), hi = TA.p90 + ((TA.p90 - TA.p50) >> 1);
  const pts = [[0, lo], [100, TA.p10], [500, TA.p50], [900, TA.p90], [1000, hi]];
  for (let i = 1; i < pts.length; i++) {
    if (u <= pts[i][0]) {
      const [u0, v0] = pts[i - 1], [u1, v1] = pts[i];
      return Math.max(minS, v0 + Math.floor((v1 - v0) * (u - u0) / (u1 - u0)));
    }
  }
  return Math.max(minS, hi);
}

/** the type minimum as a runway-time gap (s): taxi-in + minimum ground time + taxi-out of the side */
function minGapFor(TA, TX, wide, side) {
  const t = TX[side] || TX.T2;
  return t.inS + (wide ? TA.minWideS : TA.minNarrowS) + t.outS;
}

/** a runway-time gap (s) drawn from the turnaround quantiles (runway gaps of observed same-airframe pairs), at least the
 *  type minimum (verification fix round 1, F5: the quantiles were applied to the ground time before) */
function drawGap(seed, key, TA, TX, wide, side) {
  return Math.max(minGapFor(TA, TX, wide, side), drawTurnS(seed, key, TA, wide));
}

/** seeded delay (s) by the bands of inputs.delays (design s.2.2 step 8) */
function drawDelayS(seed, key, D) {
  const u = drawPermille(seed, key, PURPOSE.DELAY_BAND);
  let acc = 0;
  for (const b of D.bands) {
    acc += Math.round(b.p * 1000);
    if (u < acc) return drawRange(seed, key, PURPOSE.DELAY_VAL, b.minS, b.maxS);
  }
  const b = D.bands[D.bands.length - 1];
  return drawRange(seed, key, PURPOSE.DELAY_VAL, b.minS, b.maxS);
}

/** hourly targets per local hour (largest remainder of the profile shape over n) */
export function hourTargets(profile, n) {
  const w = {}; profile.forEach((p, h) => { w[String(h).padStart(2, '0')] = p; });
  const a = apportion(w, n);
  return profile.map((_, h) => a[String(h).padStart(2, '0')] || 0);
}

/** the airline's type weights with 'other' resolved through the group pool */
function resolvedMix(I, set, airline) {
  const mix = (I.typeMix[set] && I.typeMix[set][airline]) || null;
  const grp = (I.airlines[airline] && I.airlines[airline].group) || 'mainland';
  const pool = (I.typeMix.pool && I.typeMix.pool[set] && I.typeMix.pool[set][grp]) || { A320: 1 };
  const out = {};
  const add = (t, w) => { out[t] = (out[t] || 0) + w; };
  if (!mix) { for (const [t, w] of Object.entries(pool)) add(t, w); return out; }
  const pt = Object.values(pool).reduce((s, x) => s + x, 0) || 1;
  for (const [t, w] of Object.entries(mix)) {
    if (t === 'other') for (const [pt2, pw] of Object.entries(pool)) add(pt2, w * pw / pt);
    else add(t, w);
  }
  return out;
}

const sideOf = (I, airline, intl) => !airline ? 'BIZ' : (intl || (I.terminals.T1 || []).includes(airline)) ? 'T1' : 'T2';

/**
 * buildDayPlan({day, inputs, stands, overlay = null, notams, gateTimes, prevEnd = null, opts}) -> DayPlan (design s.7.1)
 *   opts: {rule = 'tailwind', published = true (Q1b), repeatFlights = false (Q1), repCandidates, nowMs (timing only),
 *          localPrev = false (use a prevEnd whose identity is not 'none'; the plan is then 'derived' without an overlay)}
 */
export function buildDayPlan({ day, inputs, stands, overlay = null, notams, gateTimes = null, prevEnd = null, opts = {} }) {
  const I = inputs, P = I.params;
  const [t0, t1] = dayWindow(day, I);
  const seed = daySeed(day);
  const NOT = notams || I.notams || [];
  const ov = overlay ? checkOverlay(overlay, { day }) : null;            // ?identity=0 = overlay null: the public plan
  const useOv = !!(ov && ov.records.length);
  const weightSet = useOv ? 'complement' : 'fullDay';
  const rule = opts.rule || 'tailwind';
  const TA = I.turnaround, TX = P.taxi;
  const taxiIn = (sd) => (TX[sd] || TX.T2).inS * S, taxiOut = (sd) => (TX[sd] || TX.T2).outS * S;
  const ti = new Map(); const tinfo = (icao) => { if (!ti.has(icao)) ti.set(icao, typeInfo(icao, I)); return ti.get(icao); };
  const minGapS = (wide, side) => minGapFor(TA, TX, wide, side);
  const drawGapS = (sd, key, ta, wide, side) => drawGap(sd, key, ta, TX, wide, side);
  const notes = [];
  const counters = { outOfWindow: 0, coveredPub: 0, contSkipped: 0, diverted: 0, beyondDay: 0, tier2InClosure: 0, knockOn: 0,
    rushed: 0, tier2ShortTurns: 0, tier2NoGround: 0 };

  // ---- 1. targets per local hour, arrivals and departures balanced to total / 2
  const tot = totalFor(I, day);
  const N = Math.round(tot.perDay);
  const nArr = Math.floor(N / 2), nDep = N - nArr;
  const target = { arr: hourTargets(I.profile.arr, nArr), dep: hourTargets(I.profile.dep, nDep) };

  // slots: {key, role, tier, airline, icao, tSched, tRwy, delayS, intl, side, flight, far, farDate, ident, sigmaS, reg, grp}
  const slots = [];
  const sinceT0 = (t) => t - t0;

  // ---- 2. tier 2 (overlay only)
  const afGroups = new Map();          // tier-2 airframe key -> slots (registration grouping happens only in memory)
  if (useOv) {
    for (const r of ov.records) {
      const t = r.t_sha * S;
      if (t < t0 || t >= t1) { counters.outOfWindow++; continue; }
      const intl = !MAINLAND.test(r.far || 'ZS');
      const s = { key: 'oe:' + r.uid, role: r.role, tier: 'oe', airline: r.airline, icao: r.type, tSched: t, tRwy: t, delayS: 0,
        intl, ident: r.uid, sigmaS: r.sigma_s, reg: r.reg || null };
      if (noLandingAt(NOT, t) && r.role === 'arr') counters.tier2InClosure++;
      slots.push(s);
      const g = r.reg ? 'r:' + r.reg : 'u:' + r.uid;
      if (!afGroups.has(g)) afGroups.set(g, []);
      afGroups.get(g).push(s);
    }
  }
  // ---- 4. continuations of the observed airframes (tier 4 'cont': airline and type only)
  const chains = [];                   // [{slots: [...ordered movements], startsParked, endsParked, key}]
  for (const [g, L] of [...afGroups.entries()].sort((a, b) => a[0] < b[0] ? -1 : 1)) {
    L.sort((a, b) => (a.tRwy - b.tRwy) || (a.key < b.key ? -1 : 1));
    const air = L[0];
    const side = L.some(s => s.intl) ? 'T1' : sideOf(I, air.airline, false);
    const wide = tinfo(air.icao).wide;
    for (const s of L) s.side = side;
    const seq = [];
    const mk = (role, tRwy, n) => ({ key: 'cont:' + air.key.slice(3) + ':' + n, role, tier: 'cont', airline: air.airline, icao: air.icao,
      tSched: tRwy, tRwy, delayS: 0, intl: L.some(s => s.intl), side });
    let startsParked = false, endsParked = false;
    const first = L[0], last = L[L.length - 1];
    if (first.role === 'dep') {
      if (sinceT0(first.tRwy) < (P.earlyParkLocalH - P.dayStartLocalH) * H) startsParked = true;
      else {
        const tArr = first.tRwy - drawGapS(seed, first.key + ':pre', TA, wide, side) * S;      // runway-time gap (F5)
        if (tArr > t0) seq.push(mk('arr', tArr, 'a0')); else startsParked = true;
      }
    }
    for (let i = 0; i < L.length; i++) {
      seq.push(L[i]);
      const x = L[i], y = L[i + 1];
      // observed arrival -> observed departure of one airframe whose ground time is below the type minimum: t_sha is kept
      // (no tier-2 shift, review M10), so the scheduler's holds (C1) must stretch it; counted (verification fix round 1, F10)
      if (y && x.role === 'arr' && y.role === 'dep') {
        const ground = (y.tRwy - taxiOut(side)) - (x.tRwy + taxiIn(side));
        if (ground < (wide ? TA.minWideS : TA.minNarrowS) * S) counters.tier2ShortTurns++;
        if (ground <= 0) counters.tier2NoGround++;
      }
      if (!y || x.role !== y.role) continue;
      const gap = drawGapS(seed, x.key + ':mid', TA, wide, side) * S;
      if (x.role === 'arr') {        // arr, arr: an unseen departure between them
        const tDep = x.tRwy + gap;
        if (tDep <= y.tRwy - H) seq.push(mk('dep', tDep, 'm' + i)); else counters.contSkipped++;
      } else {                       // dep, dep: an unseen arrival between them
        const tArr = y.tRwy - gap;
        if (tArr >= x.tRwy + H) seq.push(mk('arr', tArr, 'm' + i)); else counters.contSkipped++;
      }
    }
    if (last.role === 'arr') {
      if (sinceT0(last.tRwy) >= (P.lateStayLocalH - P.dayStartLocalH) * H) endsParked = true;
      else {
        const tDep = last.tRwy + drawGapS(seed, last.key + ':post', TA, wide, side) * S;
        if (tDep < t1) seq.push(mk('dep', tDep, 'z')); else endsParked = true;
      }
    }
    seq.sort((a, b) => a.tRwy - b.tRwy);
    for (const s of seq) if (s.tier === 'cont') slots.push(s);
    chains.push({ key: g, slots: seq, startsParked: seq[0].role === 'dep', endsParked: seq[seq.length - 1].role === 'arr' });
  }

  // ---- 3. tier 3: published rows of this date (owner default Q1b), unless a tier-2 slot carries the same flight number
  const pubSlots = [];
  if (opts.published !== false) {
    const oeFlights = new Set(useOv ? ov.records.map(r => r.flight).filter(Boolean) : []);
    let n = 0;
    for (const r of [...(I.published.hkg || []), ...(I.published.tsa || [])]) {
      if (r.day !== day) continue;
      if (oeFlights.has(r.flight) || (r.codeshares || []).some(f => oeFlights.has(f))) { counters.coveredPub++; continue; }
      const k = 'pub:' + (n++);
      let icao = r.type, typePublished = !!r.type;
      if (!icao) {
        const mix = resolvedMix(I, weightSet, r.airline);
        const keys = Object.keys(mix).sort();
        const tw = keys.reduce((s, t) => s + Math.round(mix[t] * 1000), 0);
        let u = drawInt(seed, k, PURPOSE.TYPE, Math.max(1, tw)), pick = keys[0];
        for (const t of keys) { u -= Math.round(mix[t] * 1000); if (u < 0) { pick = t; break; } }
        icao = pick;
      }
      const s = { key: k, role: r.role, tier: 'pub', airline: r.airline, icao, tSched: r.tSha, tRwy: r.tShaAct ?? null,
        delayS: 0, intl: true, side: 'T1', flight: r.flight, far: r.far, farDate: r.farDate, typePublished, actual: r.tShaAct != null };
      slots.push(s); pubSlots.push(s);
    }
  }

  // ---- business jets (generic, business apron; part of the day total; design s.2.3)
  const bizPairs = Math.floor((P.bizPerDay || 0) / 2);
  const bizSlots = [];
  for (let i = 0; i < bizPairs; i++) {
    const k = 'biz' + i;
    const icao = P.bizTypes[drawInt(seed, k, PURPOSE.BIZ, P.bizTypes.length)];
    const ta = hourStart(t0, 9 + drawInt(seed, k + 'h', PURPOSE.TIME, 5), I) + drawInt(seed, k + 's', PURPOSE.TIME, 3600) * S;
    const td = ta + (3 * 3600 + drawInt(seed, k + 'g', PURPOSE.TIME, 2 * 3600)) * S;
    for (const [role, t] of [['arr', ta], ['dep', td]]) {
      const s = { key: 'inf:biz' + i + role[0], role, tier: 'inf', airline: null, icao, tSched: t, tRwy: null, delayS: 0, intl: false, side: 'BIZ', biz: true };
      slots.push(s); bizSlots.push(s);
    }
  }

  // ---- 5. fill: per hour and role, target - tier 2 - tier 3 - continuations - business
  const have = { arr: new Array(24).fill(0), dep: new Array(24).fill(0) };
  for (const s of slots) have[s.role][localHour(s.tSched, I)]++;
  const fill = { arr: [], dep: [] };
  for (const role of ['arr', 'dep']) {
    for (let h = 0; h < 24; h++) {
      const n = Math.max(0, target[role][h] - have[role][h]);
      const hs = hourStart(t0, h, I);
      const ts = [];
      for (let i = 0; i < n; i++) ts.push(hs + drawInt(seed, `fill:${role}:${h}:${i}`, PURPOSE.TIME, 3600) * S);
      ts.sort((a, b) => a - b);
      ts.forEach((t, i) => fill[role].push({ key: `inf:${role[0]}${String(h).padStart(2, '0')}${String(i).padStart(2, '0')}`, role, tier: 'inf', tSched: t, tRwy: null, delayS: 0 }));
    }
  }
  const W = (weightSet === 'complement' && I.weights.complementByDay && I.weights.complementByDay[day]) || I.weights[weightSet];
  // airline x type x intl quotas over n slots, deterministic, then a seeded permutation
  const quota = (n, key) => {
    const al = apportion(W, n), out = [];
    for (const a of Object.keys(al).sort()) {
      if (!al[a]) continue;
      const mix = resolvedMix(I, weightSet, a);
      const tq = apportion(mix, al[a]);
      const share = (I.intl.share && I.intl.share[a]) || 0;
      const nIntl = Math.round(share * al[a]);
      let k = 0;
      for (const t of Object.keys(tq).sort()) for (let i = 0; i < tq[t]; i++) out.push({ airline: a, icao: t, intl: (k++ < nIntl) });
    }
    // spread the international flag over the airline's types (not all on its first type)
    const byA = new Map();
    for (const o of out) { if (!byA.has(o.airline)) byA.set(o.airline, []); byA.get(o.airline).push(o); }
    for (const [a, L] of byA) {
      const nI = L.filter(o => o.intl).length;
      L.forEach(o => { o.intl = false; });
      shuffled(L.map((_, i) => i), seed, key + ':intl:' + a).slice(0, nI).forEach(i => { L[i].intl = true; });
    }
    return shuffled(out, seed, key);
  };
  const qa = quota(fill.arr.length, 'qa');
  fill.arr.forEach((s, i) => { Object.assign(s, qa[i]); s.side = sideOf(I, s.airline, s.intl); });
  for (const s of fill.arr) slots.push(s);

  // ---- 6. rotations (design s.2.2 step 6; verification fix round 1, F5). The turnaround quantiles are RUNWAY-TIME gaps
  //         (same-airframe arrival -> departure). Every pool arrival draws its own gap G from them (at least the type
  //         minimum: taxi-in + minimum ground time + taxi-out); its airframe is READY for a departure scheduled at or after
  //         arrival + G. Each departure, in time order, takes (rotation-first, D1):
  //           1. a ready airframe (gap in [G, 6 h]): the one ready EARLIEST (no airframe idles while a later one leaves);
  //           2. else, while rushed turns are below params.rushCapPermille of the fill departures so far, the not-yet-ready
  //              airframe with the smallest shortfall whose gap still has the type minimum (a rushed turn, counted);
  //           3. else it is a night-stopper (parked from t0) whose airline / type come from the quota.
  //         Tier-3 departures take an arrival of their airline (and type when TSA published it); business jets pair with
  //         business jets; unpaired arrivals stay to t1.
  const arrPool = [];
  for (const s of [...fill.arr, ...pubSlots.filter(x => x.role === 'arr'), ...bizSlots.filter(x => x.role === 'arr')]) {
    const info = tinfo(s.icao);
    const gMin = minGapS(info.wide, s.side) * S;
    const g = drawGapS(seed, s.key, TA, info.wide, s.side) * S;
    arrPool.push({ s, ready: s.tSched + g, minReady: s.tSched + gMin, used: false });
  }
  arrPool.sort((a, b) => (a.ready - b.ready) || (a.s.key < b.s.key ? -1 : 1));
  const depsToPair = [...fill.dep, ...pubSlots.filter(x => x.role === 'dep'), ...bizSlots.filter(x => x.role === 'dep')]
    .sort((a, b) => (a.tSched - b.tSched) || (a.key < b.key ? -1 : 1));
  const pairOf = new Map();            // dep key -> arr slot
  const nightStop = [];
  const maxPair = (opts.maxPairS ?? TA.maxPairS ?? 21600) * S;
  const rushCap = opts.rushCapPermille ?? P.rushCapPermille ?? 0;
  let nFillDep = 0, nRushed = 0;
  const pickNearest = (opts.pairPick ?? P.pairPick) === 'nearest';
  for (const d of depsToPair) {
    const isFill = d.tier === 'inf' && !d.biz;
    if (isFill) nFillDep++;
    let ready = null, rush = null;
    for (const c of arrPool) {
      if (c.used) continue;
      const a = c.s;
      if (d.tier === 'pub') { if (a.airline !== d.airline || a.side !== d.side || (d.typePublished && a.icao !== d.icao)) continue; }
      else if (d.biz) { if (!a.biz) continue; }
      else if (a.tier !== 'inf' || a.biz) continue;            // fill departures never take tier-3 or business arrivals
      if (d.tSched - a.tSched > maxPair || c.minReady > d.tSched) continue;
      // the pool is in ready order: the earliest ready airframe is the first ready one, the nearest (smallest surplus over
      // its drawn gap) the last ready one; the first not-ready one has the smallest shortfall (then nothing better follows)
      if (c.ready <= d.tSched) { ready = c; if (pickNearest) continue; break; }
      rush = c; break;
    }
    let c = ready;
    if (!c && rush && (!isFill || 1000 * (nRushed + 1) <= rushCap * nFillDep)) { c = rush; if (isFill) nRushed++; }
    if (c) {
      c.used = true; pairOf.set(d.key, c.s);
      if (d.tier === 'inf' && !d.biz) { d.airline = c.s.airline; d.icao = c.s.icao; d.intl = c.s.intl; d.side = c.s.side; }
      else if ((d.tier === 'pub' && !d.typePublished) || d.biz) d.icao = c.s.icao;    // a business jet keeps its type too
    } else nightStop.push(d);
  }
  counters.rushed = nRushed;
  const nsFill = nightStop.filter(d => d.tier === 'inf' && !d.biz);
  const qn = quota(nsFill.length, 'qn');
  nsFill.forEach((d, i) => { Object.assign(d, qn[i]); d.side = sideOf(I, d.airline, d.intl); });
  for (const d of nightStop) if (!d.side) d.side = d.tier === 'pub' ? 'T1' : sideOf(I, d.airline, d.intl);
  for (const s of fill.dep) slots.push(s);

  // ---- 2b / 3b. repeated flight numbers (owner question Q1, default OFF; local only)
  if (opts.repeatFlights && Array.isArray(opts.repCandidates) && !useOv) {
    const used = new Set();
    for (const c of opts.repCandidates) {
      const tLoc = hourStart(t0, Math.floor(c.minLocal / 60), I) + (c.minLocal % 60) * MIN;
      let best = null;
      for (const s of slots) {
        if (s.tier !== 'inf' || s.biz || s.role !== c.role || s.airline !== c.airline || used.has(s.key)) continue;
        const dtm = Math.abs(s.tSched - tLoc);
        if (dtm <= 20 * MIN && (!best || dtm < Math.abs(best.tSched - tLoc))) best = s;
      }
      if (best) { used.add(best.key); best.tier = 'rep'; best.flight = c.flight; best.key = 'rep:' + c.flight + ':' + c.role; }
    }
  }

  // ---- 8. delays (tiers 3 and 4 only; never tier 2 or continuations), knock-on for rotations, diversions
  const D = I.delays;
  for (const s of slots) {
    if (s.tier === 'oe' || s.tier === 'cont') continue;
    if (s.tier === 'pub' && s.actual) { s.delayS = Math.round((s.tRwy - s.tSched) / S); continue; }
    s.delayS = drawDelayS(seed, s.key, D);
    s.tRwy = s.tSched + s.delayS * S;
  }
  const arrOfDep = new Map();
  for (const [dk, a] of pairOf) arrOfDep.set(dk, a);
  const slotByKey = new Map(slots.map(s => [s.key, s]));
  for (const [dk, a] of arrOfDep) {
    const d = slotByKey.get(dk);
    const info = tinfo(a.icao);
    const minT = a.tRwy + taxiIn(a.side) + (info.wide ? TA.minWideS : TA.minNarrowS) * S + taxiOut(d.side);
    if (d.tRwy < minT) { d.delayS += Math.round((minT - d.tRwy) / S); d.tRwy = minT; counters.knockOn++; }
  }
  // diversions: an arrival delayed into a window with no landing (F4551 + AD 2.20 2.1.6) goes to Pudong (not drawn)
  const removed = new Set();
  for (const s of slots) {
    if (s.role !== 'arr' || s.tier === 'oe' || s.tier === 'cont') continue;
    if (s.tRwy >= t1) { removed.add(s.key); counters.beyondDay++; continue; }
    if (noLandingAt(NOT, s.tRwy)) { removed.add(s.key); counters.diverted++; }
  }
  for (const d of depsToPair) {
    const a = pairOf.get(d.key);
    if (a && removed.has(a.key)) { pairOf.delete(d.key); nightStop.push(d); }
  }
  for (const s of slots) if (s.role === 'dep' && s.tRwy >= t1) { removed.add(s.key); counters.beyondDay++; }

  // ---- airframes and ground visits
  const blockOf = (s) => s.role === 'arr' ? s.tRwy + taxiIn(s.side) : s.tRwy - taxiOut(s.side);
  const frames = [];                   // {seq: [slots], startsParked, endsParked, tier}
  for (const c of chains) {
    const seq = c.slots.filter(s => !removed.has(s.key));
    if (seq.length) frames.push({ seq, tier: 'oe', reg: seq.find(s => s.reg) ? seq.find(s => s.reg).reg : null });
  }
  const pairedArr = new Set([...pairOf.values()].map(a => a.key));
  for (const d of depsToPair) {
    if (removed.has(d.key)) continue;
    const a = pairOf.get(d.key);
    frames.push({ seq: a && !removed.has(a.key) ? [a, d] : [d], tier: d.tier === 'pub' ? 'pub' : 'inf' });
  }
  for (const s of slots) {
    if (s.role !== 'arr' || s.tier === 'oe' || s.tier === 'cont' || removed.has(s.key) || pairedArr.has(s.key)) continue;
    frames.push({ seq: [s], tier: s.tier });
  }
  frames.sort((a, b) => (a.seq[0].role === 'dep' ? t0 - 1 : a.seq[0].tRwy) - (b.seq[0].role === 'dep' ? t0 - 1 : b.seq[0].tRwy) ||
    (a.seq[0].key < b.seq[0].key ? -1 : 1));
  const visits = [];
  // warm start (design s.2.2 step 10; verification fix round 2, F15): prevEnd = endState(plan(D-1)) = {identity, entries}.
  // An end state of a plan built with an overlay (identity 'overlay' / 'derived', or unknown: a bare array) carries the
  // observed airframes' last stands, so it is IGNORED unless opts.localPrev; when it is used, a plan without an overlay of
  // its own is marked identity 'derived' (in the hash). The app's public plan takes endState(public plan(D-1)).
  const prevIdentity = prevEnd == null ? null : Array.isArray(prevEnd) ? 'unknown' : (prevEnd.identity || 'unknown');
  const prevEntries = prevEnd == null ? null : Array.isArray(prevEnd) ? prevEnd : (Array.isArray(prevEnd.entries) ? prevEnd.entries : []);
  const prevTainted = prevIdentity != null && prevIdentity !== 'none';
  const prevUsed = !!prevEntries && (!prevTainted || !!opts.localPrev);
  const prevList = prevUsed ? prevEntries : null;
  const prevMap = new Map();
  if (prevList) for (const e of prevList) { const k = e.airline + '|' + e.icao; if (!prevMap.has(k)) prevMap.set(k, []); prevMap.get(k).push(e); }
  const prevFam = prevList ? prevList.slice() : [];
  const usedPrev = new Set();
  // long ground visits (more than params.longRemoteS of the active day 06:00-01:00 local) try their side's remote stands
  // first: a contact stand is kept for turns (verification fix round 1; no towing is modelled, design s.2.4)
  const longRemote = (opts.longRemoteS ?? P.longRemoteS ?? 0) * S;
  const actA = hourStart(t0, P.nightNoSched.toLocalH, I), actB = hourStart(t0, P.nightNoSched.fromLocalH, I);   // 06:00, 01:00
  const activeS = (from, to) => Math.max(0, Math.min(to, actB) - Math.max(from, actA));
  frames.forEach((f, i) => {
    f.id = 'af:' + i;
    const s0 = f.seq[0], info = tinfo(s0.icao);
    f.side = s0.side; f.info = info; f.airline = s0.airline; f.icao = s0.icao;
    let prevArr = null, vi = 0;
    const mkVisit = (from, to, arr, dep, t0Edge, t1Edge) => {
      const v = { id: f.id + ':v' + (vi++), af: f, side: f.side, from, to, arr, dep, t0Edge, t1Edge, spanM: info.spanM, lenM: info.lenM,
        wide: info.wide, size: info.size, biz: !!s0.biz, typeKey: info.typeKey, tierRank: TIER_RANK[f.tier] ?? 9, prefer: null,
        remoteFirst: !s0.biz && (drawPermille(seed, f.seq.map(x => x.key).join('+') + ':' + vi, PURPOSE.STAND) < (opts.remoteFirstPermille ?? P.remoteFirstPermille ?? 0)
          || (longRemote > 0 && activeS(from, to, t0Edge, t1Edge) > longRemote)) };
      if (t0Edge && prevList) {    // day-cut continuity (design s.2.2 step 10): a night-stopper prefers the stand D-1 ended with
        const L = prevMap.get(f.airline + '|' + f.icao) || [];
        let e = L.find(x => !usedPrev.has(x));
        if (!e) e = prevFam.find(x => !usedPrev.has(x) && x.side === f.side && x.family === info.family);
        if (e) { usedPrev.add(e); v.prefer = e.stand; }
      }
      visits.push(v);
      return v;
    };
    for (const s of f.seq) {
      if (s.role === 'arr') prevArr = s;
      else {
        if (prevArr) mkVisit(blockOf(prevArr), blockOf(s), prevArr, s, false, false);
        else mkVisit(t0, blockOf(s), null, s, true, false);
        prevArr = null;
      }
    }
    if (prevArr) mkVisit(blockOf(prevArr), t1, prevArr, null, false, true);
  });

  // ---- 9. stand allocation (js/sim/alloc.js); unplaced visits remove their movements (counted)
  const closures = closureWindows(NOT);
  const TC = standTable(stands).cap;
  const nightCap = { T1: Math.floor(P.nightStopCapShare * TC.T1.usable), T2: Math.floor(P.nightStopCapShare * TC.T2.usable) };
  const A = allocate(visits, stands, { bufferS: P.bufferS, closures, gateTimes, t0, t1, nightCap });
  const unplacedKeys = new Set();
  const unplacedBy = {};
  for (const vid of A.unplaced) {
    const v = visits.find(x => x.id === vid);
    const k = `${v.side}|${v.size}|${v.t0Edge ? 'parked-from-t0' : v.t1Edge ? 'stays-to-t1' : 'turn'}`;
    unplacedBy[k] = (unplacedBy[k] || 0) + 1;
    if (v.arr) unplacedKeys.add(v.arr.key);
    if (v.dep) unplacedKeys.add(v.dep.key);
  }
  const standOfSlot = new Map();
  for (const v of visits) {
    const as = A.assign.get(v.id);
    if (!as) continue;
    if (v.arr) standOfSlot.set(v.arr.key, { ...as, v });
    if (v.dep) standOfSlot.set(v.dep.key, { ...as, v });
  }

  // ---- movements (drawn only)
  const live = [];
  for (const f of frames) for (const s of f.seq) if (!removed.has(s.key) && !unplacedKeys.has(s.key) && standOfSlot.has(s.key)) live.push([s, f]);
  live.sort((a, b) => (a[0].tRwy - b[0].tRwy) || (a[0].role < b[0].role ? -1 : a[0].role > b[0].role ? 1 : 0) || (a[0].key < b[0].key ? -1 : 1));
  const idOf = new Map();
  live.forEach(([s], i) => idOf.set(s.key, 'm:' + String(i).padStart(4, '0')));
  const usedFrames = [...new Set(live.map(([, f]) => f))].sort((a, b) => +a.id.slice(3) - +b.id.slice(3));
  const afId = new Map(usedFrames.map((f, i) => [f, 'af:' + i]));
  const movements = live.map(([s, f]) => {
    const st = standOfSlot.get(s.key);
    const info = tinfo(s.icao);
    const seq = f.seq.filter(x => idOf.has(x.key));
    const k = seq.indexOf(s);
    const m = {
      id: idOf.get(s.key), slot: s.key, role: s.role, af: afId.get(f), airline: s.airline, icao: s.icao, model: info.model,
      typeKey: info.typeKey, wake: info.wake, tier: s.tier, tSched: s.tSched, tRwy: s.tRwy, delayS: s.delayS, tBlock: blockOf(s),
      stand: st.stand, side: s.side, contact: st.contact, overflow: st.crossSide ? 'crossSide' : null,
      prev: k > 0 ? idOf.get(seq[k - 1].key) : null, next: k < seq.length - 1 ? idOf.get(seq[k + 1].key) : null,
      startsParked: s.role === 'dep' && k === 0, endsParked: s.role === 'arr' && k === seq.length - 1,
      ident: s.tier === 'oe' ? s.ident : null, sigmaS: s.tier === 'oe' ? s.sigmaS : null,
      flight: (s.tier === 'pub' || s.tier === 'rep') ? s.flight : null, intl: !!s.intl, src: 'inf',
    };
    if (s.tier === 'pub') { m.far = s.far; m.farDate = s.farDate; m.typePublished = !!s.typePublished; }
    if (s.biz) m.biz = true;
    // the registration per movement, tier 2 only (verification fix round 2, F19): a continuation of the same airframe
    // (tier 'cont') shares the airframe but never shows its registration; D takes UiTrack.info.reg from the ACTIVE movement
    if (s.tier === 'oe' && s.reg) m.reg = s.reg;
    return m;
  });

  // ---- airframes
  const airframes = usedFrames.map(f => {
    const a = { id: afId.get(f), airline: f.airline, icao: f.icao, model: f.info.model, tier: f.tier, side: f.side };
    if (f.tier === 'oe' && f.reg) { a.reg = f.reg; a.regTiers = ['oe']; }   // only with an overlay (local); shown on 'oe' movements only (F19)
    return a;
  });

  // ---- stands: occupancy {from, to, mv, af, service} (no buffer), service windows (design s.4.3)
  const standsOut = {};
  const turnA = P.serviceTurnAfterOnS * S, turnB = P.serviceTurnBeforeOffS * S, coldAfter = P.coldAfterS * S;
  for (const v of visits) {
    const as = A.assign.get(v.id);
    if (!as) continue;
    const arrId = v.arr ? idOf.get(v.arr.key) : null, depId = v.dep ? idOf.get(v.dep.key) : null;
    if (!arrId && !depId) continue;
    const from = v.from, to = v.to;
    const service = [];
    if (v.t0Edge) {                  // night-stopper: cold until off-block - 45 min
      if (to - turnB > from) service.push({ from, to: to - turnB, mode: 'cold' });
      service.push({ from: Math.max(from, to - turnB), to, mode: 'turn' });
    } else if (v.t1Edge) {           // stays to t1: turn after on-block, then cold
      service.push({ from, to: Math.min(to, from + turnA), mode: 'turn' });
      if (from + turnA < to) service.push({ from: from + turnA, to, mode: 'cold' });
    } else if (to - from > coldAfter && from + turnA < to - turnB) {
      service.push({ from, to: from + turnA, mode: 'turn' }, { from: from + turnA, to: to - turnB, mode: 'cold' }, { from: to - turnB, to, mode: 'turn' });
    } else service.push({ from, to, mode: 'turn' });
    (standsOut[as.stand] = standsOut[as.stand] || []).push({ from, to, mv: arrId || depId, arr: arrId, dep: depId, af: afId.get(v.af), service });
  }
  for (const k of Object.keys(standsOut)) standsOut[k].sort((a, b) => a.from - b.from);
  const standsSorted = {};
  for (const k of Object.keys(standsOut).sort()) standsSorted[k] = standsOut[k];

  // ---- stats (aggregates)
  const tiers = { oe: 0, pub: 0, rep: 0, inf: 0, cont: 0 };
  for (const m of movements) tiers[m.tier]++;
  const byHour = { target, sched: { arr: new Array(24).fill(0), dep: new Array(24).fill(0) }, rwy: { arr: new Array(24).fill(0), dep: new Array(24).fill(0) } };
  for (const m of movements) { byHour.sched[m.role][localHour(m.tSched, I)]++; byHour.rwy[m.role][localHour(m.tRwy, I)]++; }
  const T = standTable(stands);
  const bySide = {};
  for (const sd of ['T1', 'T2', 'BIZ']) {
    const c = T.cap[sd];
    bySide[sd] = { max: 0, cap: sd === 'BIZ' ? c.all : c.usable, wideMax: 0, wideCap: c.wide, elMax: 0, elCap: c.el, demandMax: 0,
      demandWideMax: 0, demandElMax: 0, nightStop: 0, nightStopCap: 0, contact: 0, moves: 0 };
  }
  // per-minute occupancy per side x class: physical (the stand's side) and demand (the airframe's own side)
  const sweep = (keyFn, cls) => {
    const ev = [];
    for (const v of visits) {
      const as = A.assign.get(v.id); if (!as) continue;
      if (cls && !cls(v)) continue;
      ev.push([v.from, 1, keyFn(v, as)], [v.to, -1, keyFn(v, as)]);
    }
    ev.sort((a, b) => (a[0] - b[0]) || (a[1] - b[1]));
    const cur = {}, mx = {};
    for (const [, d, k] of ev) { cur[k] = (cur[k] || 0) + d; mx[k] = Math.max(mx[k] || 0, cur[k]); }
    return mx;
  };
  const isWide = (v) => v.size === 'wide' || v.size === 'el', isEl = (v) => v.size === 'el';
  const phys = sweep((v, as) => as.side), dem = sweep((v) => v.side);
  const physW = sweep((v, as) => as.side, isWide), physE = sweep((v, as) => as.side, isEl);
  const demW = sweep((v) => v.side, isWide), demE = sweep((v) => v.side, isEl);
  for (const sd of Object.keys(bySide)) {
    Object.assign(bySide[sd], { max: phys[sd] || 0, demandMax: dem[sd] || 0, wideMax: physW[sd] || 0, elMax: physE[sd] || 0,
      demandWideMax: demW[sd] || 0, demandElMax: demE[sd] || 0 });
  }
  for (const m of movements) { const b = bySide[m.side]; if (!b) continue; b.moves++; if (m.contact) b.contact++; }
  // night-stop bounds (design s.2.2 step 7): the cumulative-flow bound on block times (turn-blind, as the design's 78) and
  // the same with the minimum turnaround (an arrival serves a departure only after on-block + minimum turn); the count of
  // night-stoppers per own side, and per side of the stands they are parked on (capped at 0.85 x usable)
  const flow = (turnAware) => {
    let cum = 0, minCum = 0;
    const evs = [];
    for (const m of movements) {
      if (m.role === 'dep') evs.push([m.tBlock, -1]);
      else evs.push([m.tBlock + (turnAware ? ((tinfo(m.icao).wide ? TA.minWideS : TA.minNarrowS) * S) : 0), 1]);
    }
    evs.sort((a, b) => (a[0] - b[0]) || (a[1] - b[1]));
    for (const [, d] of evs) { cum += d; minCum = Math.min(minCum, cum); }
    return -minCum;
  };
  const flowBound = flow(false), flowBoundTurn = flow(true);
  const nsBySide = { T1: 0, T2: 0, BIZ: 0 }, nsParked = { T1: 0, T2: 0, BIZ: 0 };
  for (const m of movements) if (m.startsParked) { nsBySide[m.side]++; nsParked[standTable(stands).byName.get(m.stand).side]++; }
  for (const sd of ['T1', 'T2']) {
    bySide[sd].nightStop = nsBySide[sd];
    bySide[sd].nightStopParked = nsParked[sd];
    bySide[sd].nightStopCap = nightCap[sd];
  }
  bySide.BIZ.nightStop = nsBySide.BIZ;
  const contactShare = {};
  for (const sd of ['T1', 'T2']) contactShare[sd] = bySide[sd].moves ? Math.round(1000 * bySide[sd].contact / bySide[sd].moves) / 1000 : null;
  const unplacedMoves = unplacedKeys.size;
  const stats = {
    byHour, bySide, contactShare, crossSide: movements.filter(m => m.overflow === 'crossSide').length, unplaced: unplacedMoves,
    unplacedVisits: A.unplaced.length, unplacedBy, diverted: counters.diverted, flowBound, flowBoundTurn, nightStop: nsBySide,
    nightStopParked: nsParked,
    total: { target: N, arr: nArr, dep: nDep, drawn: movements.length, sched: movements.length + unplacedMoves + counters.diverted + counters.beyondDay },
    counters, preferredStands: A.stats.preferred, weightSet, totalBasis: tot.basis,
  };
  if (nsParked.T2 > nightCap.T2 || nsParked.T1 > nightCap.T1)
    notes.push('night-stoppers parked above the per-side cap (0.85 x usable): see stats.bySide');
  notes.push('AIP combined wide-body positions (216E, 220E, 281E, 413E) are not placed in data/sha_stands.json: data request to tools/airport/build_stands.py (overflow step 1 skipped)');
  if (!P.refless) notes.push('the 4 OSM positions without a ref are not used (no route in the route table, no gate object)');

  // identity: 'overlay' (tier 2 from a local overlay), 'derived' (no overlay, but a local end state of D-1 was used:
  // F15), 'none' (the public plan). Part of the hash.
  const identity = useOv ? 'overlay' : (prevUsed && prevTainted) ? 'derived' : 'none';
  stats.prevEnd = prevEnd == null ? null : { identity: prevIdentity, used: prevUsed, ignored: !prevUsed, entries: prevEntries.length };
  if (prevEnd != null && !prevUsed) notes.push(`warm start: an end state with identity '${prevIdentity}' was ignored (pass endState of the public plan of D-1, or opts.localPrev locally)`);
  const plan = {
    v: 1, day, t0, t1, seed, version: PLAN_VERSION, rule, weightSet, src: 'inf', identity,
    tiers, stats, airframes, movements, stands: standsSorted,
    closures: { stands: [...closures.keys()].sort(), windows: Object.fromEntries([...closures.entries()].sort()) }, notes,
  };
  plan.hash = hashOf({ v: plan.v, day, t0, t1, seed, version: PLAN_VERSION, rule, weightSet, identity, tiers, airframes, movements, stands: standsSorted });
  Object.defineProperty(plan, '_byId', { value: new Map(movements.map(m => [m.id, m])), enumerable: false });
  for (const m of movements) Object.freeze(m);
  Object.freeze(plan.movements); Object.freeze(plan.airframes);
  return Object.freeze(plan);
}

/** the parked airframes at the end of a plan (t1), for the next day's warm start (design s.2.2 step 10):
 *  {v, day, hash, identity, entries: [{stand, af, airline, icao, side, family}]}. `identity` is the plan's (F15): an end
 *  state of a plan with an overlay is ignored by buildDayPlan unless opts.localPrev. */
export function endState(plan, inputs) {
  const entries = [];
  for (const m of plan.movements) if (m.endsParked) entries.push({ stand: m.stand, af: m.af, airline: m.airline, icao: m.icao, side: m.side, family: typeInfo(m.icao, inputs).family });
  return { v: 1, day: plan.day, hash: plan.hash, identity: plan.identity, entries };
}
