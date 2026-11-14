// GA phase classifier for HWD (hwd3d Phase 2, P3; new file, fork map 2.8 / section 3). Node-pure.
//
// It is the LIVE twin of the Phase 1 offline classifier tools/adsb/events.py + derive.py (whose rules and counts are in
// refs/cache/adsb/hwd_events.json): the same fix states, runway episodes, contexts, hidden transitions, low passes and
// helicopter events, with the same named constants (RULES below, each from hwd_events.json `rules`), evaluated causally
// on a sliding window of each track's fixes. An event is emitted once its context is decided - the deciding fix has
// been seen (a ground fix, or an airborne fix above H_BREAK) or CTX_GAP has passed - so the live answer equals the offline
// one whenever the offline context lies inside what has arrived. Phase labels are written onto the fixes and REVISED
// (back-dated) when an episode or low pass is decided: the display runs `lookahead_s` (60 s) behind the data in replay,
// so most revisions land before they are shown; while undecided a label is `provisional`.
//
// What is NEW here (not in events.py; thresholds [inf], to be calibrated on more data - fork map 3.2):
//  - display phases per fix (the 28 ids of PHASES): taxi / parked / hold_short / runup / line_up, the pattern legs
//    (upwind, crosswind, downwind, base, final) and departing / arriving, helicopter hover / hover-taxi, overflight;
//  - scope (D6): 'hwd' when a track touches HWD runways / taxiways / ramps (R or G fixes on the field, an L corridor
//    fix, a hidden transition, helicopter ground contact on the field) or flies >= 2 pattern legs; 'overflight' after
//    SCOPE_S of observation without such evidence or at once for emitter categories A3-A5 (airliners); else 'pending';
//  - stops: runup / hold_short / line_up events once a stop lasts U.MIN_S (30 s, refs/cache/adsb/hwd_runup_holds.json
//    rules), parked after PARK_S of standing still.
// Pattern legs follow AIM 4-3-3 (traffic pattern: upwind / departure leg, crosswind, downwind, base, final) [verify:
// recalled, not re-read]; pattern sides and TPA from FAA NASR (docs/PLAN.md section 1): 10R right, 28L left, 10L left,
// 28R right; TPA 600 ft AGL (10R/28L), 800 ft AGL (10L/28R). Tower hours 07:00-21:00 local (NASR ATC_BASE).
//
//   new PhaseClassifier({ airport, site, holds? })
//   .prep(tr, f)                 derived quantities of one new fix (h, strip, corridor, ground by kinematics ...)
//   .step(tr, f, dataNow)        -> { phase, src, rule, rwy, leg, provisional, events }   (fork map 2.8)
//   .tick(tr, dataNow)           re-evaluates a track without a new fix (contexts that time out) -> events
//   .flush(tr, dataNow)          end of a track / of a run: decides what is still open -> events
//   .flow                        { end: '28'|'10', src, n } landing direction for the pattern legs
import { RWY_PAIRS, RWY_DATA, RWY_ENDS, FT, rwyAxis, rwySurfaceY, thrDispM } from '../geo.js';
import { HELI_TYPES } from '../aircraft/ga_dims.js';

// ---- the rules of tools/adsb/events.py / derive.py, values copied from refs/cache/adsb/hwd_events.json `rules`
// (heights ft above the runway surface, times s, speeds kt, distances m). Their basis there: "none comes from a standard.
// All are chosen by me for HWD from typical GA speeds / heights and the recorder's ~46 s polling hole".
export const RULES = {
  H_CONTACT: 30, H_CONTACT_COARSE: 80, H_LOW: 400, H_BREAK: 150, H_PASS: 300, EP_GAP: 100, CTX_GAP: 150, STOP_GS: 15, STOP_HOLE_GS: 25,
  LIFT_GS: 40, EXIT_GS: 30, HID_GAP: 100, HID_NEAR: 150, HID_H: 800, PASS_ISO: 60, SLOW_RATIO: 0.9, PASS_MIN_N: 3, DECEL_RATIO: 0.85,
  PASS_GS: 35, HOLE_S: 8, HELI_H: 150, HELI_GS: 40, HELI_R: 2000, HOVER_MIN_M: 30, STRIP_M: 12, CORR_M: 75, CORR_BEFORE: 2000,
  CORR_AFTER: 1000, ALIGN_DEG: 30, R_FIELD: 6000, GK_H: 30, GK_GS: 35,
  // derive.py (not in the json rules list): GK_H_COARSE 80 ft, PER_AC_N 5, CAL_GS 20-50 kt, motion track <= 15 s / >= 4 m
  GK_H_COARSE: 80, PER_AC_N: 5,
  // calibration (hwd_events.json `calibration`, n 797): h = alt_geom - GEOM_OFF - NASR runway surface; baro fallback offset
  GEOM_OFF: -108.08793657146512, BARO_GLOBAL: -148.56185264633592,
  // refs/cache/adsb/hwd_runup_holds.json `rules`
  STILL_GS: 1.0, BREAK_M: 8.0, MIN_S: 30.0, MAX_S: 600.0, HOLD_R: 25.0,
  // new for the live display [inf]: see the header
  END_GS: 15, GEOM_BAD_FT: 500,   // fix round 1 [inf]
    // fix round 1: runway-end direction only from episode fixes at >= 15 kt [inf]
  FIN_ALIGN: 20,   // round 4 (E7): final-approach evidence for the D6 scope [inf]
  UPW_M: 800,      // round 4 (E5): the upwind leg lies within this of the runway's extended centreline [inf]
  // round 4 iteration 2 (F6): an aircraft descending (< -300 ft/min) toward the field - its track within ARR_DEG of the bearing to the ARP,
  // closing by > 300 m in 60 s - within ARR_R_M and below ARR_H_FT is an arrival that has not joined yet: not 'overflight' (case P was
  // 'Overflight (not HWD traffic)' for 120 s, 5,055 -> 3,067 ft, 8 km out); an overflight decision waits ARR_HOLD_S after the last such fix [inf]
  ARR_R_M: 10000, ARR_H_FT: 6000, ARR_DEG: 30, ARR_HOLD_S: 60,
  PARK_S: 60, SCOPE_S: 90, WIN_S: 900, LEG_ALIGN: 30, LEG_MAX_NM: 4, LEG_ABOVE_TPA_FT: 700, CL_M: 300, VISIT_GAP_S: 1800,
};
const R = RULES;
const KT = 1852 / 3600;
const RIDS = RWY_PAIRS.map(([a, b]) => `${a}/${b}`);
const AX = Object.fromEntries(RIDS.map(r => [r, rwyAxis(r.split('/')[0])]));
const HALF_W = Object.fromEntries(RIDS.map(r => [r, RWY_DATA[r].widthFt * FT / 2]));
// TPA (NASR / CS, docs/PLAN.md section 1): 600 ft AGL, 800 ft AGL for 10L/28R; pattern side from RWY_ENDS.rhTraffic
const TPA_AGL = { '10L/28R': 800, '10R/28L': 600 };
const angd = (a, b) => Math.abs(((a - b) % 360 + 540) % 360 - 180);
const wrap180 = (a) => ((a % 360) + 540) % 360 - 180;
const brg = (dx, dz) => ((Math.atan2(dx, -dz) * 180 / Math.PI) % 360 + 360) % 360;

export const PHASES = {
  parked: { label: 'Parked', group: 'ground', airborne: false },
  hangared: { label: 'In hangar', group: 'ground', airborne: false },
  taxi: { label: 'Taxiing', group: 'ground', airborne: false },
  runup: { label: 'Engine run-up', group: 'ground', airborne: false },
  hold_short: { label: 'Holding short', group: 'ground', airborne: false },
  line_up: { label: 'Lined up', group: 'runway', airborne: false },
  runway_taxi: { label: 'Taxiing on the runway', group: 'runway', airborne: false },
  takeoff_roll: { label: 'Take-off roll', group: 'runway', airborne: false },
  initial_climb: { label: 'Climbing out', group: 'pattern', airborne: true },
  upwind: { label: 'Upwind', group: 'pattern', airborne: true },
  crosswind: { label: 'Crosswind', group: 'pattern', airborne: true },
  downwind: { label: 'Downwind', group: 'pattern', airborne: true },
  base: { label: 'Base', group: 'pattern', airborne: true },
  final: { label: 'Final', group: 'pattern', airborne: true },
  landing_roll: { label: 'Landing roll', group: 'runway', airborne: false },
  touch_and_go: { label: 'Touch-and-go', group: 'runway', airborne: false },
  stop_and_go: { label: 'Stop-and-go', group: 'runway', airborne: false },
  go_around: { label: 'Low approach / go-around', group: 'pattern', airborne: true },
  low_pass: { label: 'Low pass (touch-and-go or low approach)', group: 'pattern', airborne: true },
  departing: { label: 'Departing', group: 'area', airborne: true },
  arriving: { label: 'Arriving', group: 'area', airborne: true },
  heli_ground: { label: 'Helicopter on the ground', group: 'heli', airborne: false },
  heli_hover_taxi: { label: 'Hover-taxi', group: 'heli', airborne: true },
  heli_hover: { label: 'Hovering', group: 'heli', airborne: true },
  heli_air: { label: 'Helicopter in flight', group: 'heli', airborne: true },
  overflight: { label: 'Overflight (not HWD traffic)', group: 'area', airborne: true },
  vehicle: { label: 'Ground vehicle', group: 'ground', airborne: false },
  // fix round 2: a ground aircraft whose signal ended away from a parking place - drawn where it was last placed, inferred
  no_signal: { label: 'No signal · last position', group: 'ground', airborne: false },
  unknown: { label: 'Unknown', group: 'area', airborne: false },
};
// offline event type (hwd_events.json counts) -> TrafficEvent kind (fork map 2.8)
export const KIND_OF = { takeoff: 'takeoff', full_stop_landing: 'landing', landing_unresolved: 'landing', touch_and_go: 'touch_and_go',
  stop_and_go: 'stop_and_go', low_approach_go_around: 'go_around', low_pass_unresolved: 'low_pass', runway_ground_move: 'runway_taxi',
  unresolved: 'runway_taxi', lift_off: 'lift_off', touch_down: 'touch_down', hover_taxi: 'hover_taxi', low_transit: 'overflight' };

// local time (America/Los_Angeles: NASR tower hours are local; PST/PDT handled by Intl) -> tower open/closed
let _tz = null; const _tzCache = new Map();
export function localHour(ms) {
  const k = Math.floor(ms / 60000); let v = _tzCache.get(k); if (v != null) return v;
  try { if (!_tz) _tz = new Intl.DateTimeFormat('en-US', { timeZone: 'America/Los_Angeles', hour: 'numeric', minute: 'numeric', hourCycle: 'h23' });
    const p = _tz.formatToParts(new Date(ms)); v = +p.find(q => q.type === 'hour').value + +p.find(q => q.type === 'minute').value / 60; }
  catch (e) { v = (((ms / 3600e3 - 8) % 24) + 24) % 24; }   // fallback PST = UTC-8 [inf]
  if (_tzCache.size > 5000) _tzCache.clear(); _tzCache.set(k, v); return v;
}
export const towerStatus = (ms) => { const h = localHour(ms); return h >= 7 && h < 21 ? 'open' : 'closed'; };

function rwyFrame(x, z) {
  const out = {};
  for (const rid of RIDS) { const A = AX[rid], px = x - A.origin[0], pz = z - A.origin[1]; out[rid] = [px * A.dir[0] + pz * A.dir[1], px * A.right[0] + pz * A.right[1]]; }
  return out;
}
const surfaceFt = (rid, al) => rwySurfaceY(rid.split('/')[0], Math.min(Math.max(al, 0), AX[rid].length)) / FT;
export const aligned = (trk, rid, tol = R.ALIGN_DEG) => { const d = Math.abs(((trk - AX[rid].hdg + 90) % 180 + 180) % 180 - 90); return d <= tol; };
export const endOf = (rid, trk) => { const [a, b] = rid.split('/'); return angd(trk, AX[rid].hdg) < 90 ? a : b; };
function median(a) { if (!a.length) return null; const s = a.slice().sort((p, q) => p - q); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; }

export class PhaseClassifier {
  constructor({ airport, site = null } = {}) {
    this.site = site;
    this.holds = ((airport && airport.holds) || []).map(h => ({ id: h.id, x: h.bar ? h.bar.x : h.x, z: h.bar ? h.bar.z : h.z, runway: h.runway }));
    this.runupAprons = ((airport && airport.aprons) || []).filter(a => a.name && /run-?up/i.test(a.name)).map(a => a.name);
    this.flow = { end: '28', src: 'inf', basis: 'default: 92 % of low airborne fixes were westbound in the one recorded week (docs/PLAN.md section 3)', n: 0 };
    this.flowEv = [];             // [t, '28'|'10'] of recent HWD runway events
    this.baroDelta = [];          // [t, altBaro - altGeom] of airborne fixes (QNH + geoid; the baro fallback)
    this.counters = { evals: 0, events: 0 };
    this.parkable = null;         // (x, z, heli) -> bool: set by traffic.js (an apron / helipad / hangar door, not a taxiway)
  }
  // ------------------------------------------------------------------------------------------------ per-fix derivation
  // f: {t, x, z, g, gs, trk, th, altB, altG, vs, cat} -> adds r, Rf, near, alNear, acNear, surfFt, h, hRaw, hSrc, gk, strip, corr
  prep(tr, f) {
    const K = this.k(tr);
    f.r = Math.hypot(f.x, f.z);
    const Rf = rwyFrame(f.x, f.z); f.Rf = Rf;
    let near = RIDS[0]; for (const rid of RIDS) if (Math.abs(Rf[rid][1]) < Math.abs(Rf[near][1])) near = rid;
    f.near = near; f.alNear = Rf[near][0]; f.acNear = Rf[near][1];
    const surf = surfaceFt(near, f.alNear); f.surfFt = surf;
    // alt quantum (derive.alt_quantum): 100 ft when every airborne alt_baro within 3 km is a multiple of 100 (>= 10 seen)
    if (!f.g && f.altB != null && f.r < 3000) { K.qn++; if (f.altB % 100 !== 0) K.q25 = true; }
    K.q = K.qn >= 10 && !K.q25 ? 100 : 25;
    // a geometric altitude that disagrees with the barometric one by > GEOM_BAD_FT more than the regional (QNH + geoid) offset
    // is not used (fix round 1: TIS-B trackfiles reported alt_geom jumping by +-3,150 ft between bursts while alt_baro was
    // smooth; the drawn aircraft was cut back and forth by 190 m) [inf]
    let geomOk = f.altG != null;
    if (geomOk && f.altB != null && !f.g && this.baroDelta.length >= 5) { const md = median(this.baroDelta.slice(-80).map(q => q[1])); if (Math.abs(f.altB - f.altG - md) > R.GEOM_BAD_FT) { geomOk = false; f.geomBad = true; } }
    if (geomOk && f.altB != null && !f.g && f.altB < 10000) { this.baroDelta.push([f.t, f.altB - f.altG]); if (this.baroDelta.length > 400) this.baroDelta.shift(); }
    let h = null, src = '';
    if (f.g) { h = 0; src = 'gnd'; }
    else if (geomOk) { h = f.altG - (K.perAc ?? R.GEOM_OFF) - surf; src = 'geom'; }
    else if (f.altB != null) {
      const d = this.baroDelta.filter(q => Math.abs(q[0] - f.t) < 3 * 3600e3).map(q => q[1]);
      h = d.length >= 5 ? f.altB - median(d) - R.GEOM_OFF - surf : f.altB - R.BARO_GLOBAL - surf; src = 'baro';
    }
    f.hRaw = h; f.h = h; f.hSrc = src;
    const heli = this.isHeli(tr);
    const gkH = K.q === 25 ? R.GK_H : R.GK_H_COARSE;
    f.gk = !!f.g || (!heli && h != null && h <= gkH && f.gs != null && f.gs < R.GK_GS);
    f.strip = ''; f.corr = '';
    for (const rid of RIDS) {
      const [al, ac] = Rf[rid], L = AX[rid].length;
      if (!f.strip && al >= -30 && al <= L + 30 && Math.abs(ac) <= HALF_W[rid] + R.STRIP_M) f.strip = rid;
      if (!f.corr && al >= -R.CORR_BEFORE && al <= L + R.CORR_AFTER && Math.abs(ac) <= R.CORR_M) f.corr = rid;
    }
    // per-aircraft GEOM offset (derive.calibrate per_ac): airborne-flag fixes rolling 20-50 kt on a runway within 60 s of a
    // ground-flag fix of the same aircraft, 25-ft units, >= PER_AC_N samples
    if (f.g) K.lastG = f.t;
    else if (f.altG != null && f.gs != null && f.gs >= 20 && f.gs <= 50 && K.lastG != null && f.t - K.lastG <= 60000 && K.q === 25) {
      const rid = RIDS.find(r => Rf[r][0] >= 0 && Rf[r][0] <= AX[r].length && Math.abs(Rf[r][1]) <= HALF_W[r] + 10);
      if (rid) { K.cal.push(f.altG - surfaceFt(rid, Rf[rid][0])); if (K.cal.length > 40) K.cal.shift(); if (K.cal.length >= R.PER_AC_N) K.perAc = median(K.cal); }
    }
    return f;
  }
  isHeli(tr) { const I = tr.info || {}; return !!((I.icao && HELI_TYPES.has(I.icao)) || I.category === 'A7' || (tr.dims && tr.dims.cls === 'heli')); }
  k(tr) {
    if (!tr._k) tr._k = { q: 25, qn: 0, q25: false, cal: [], perAc: null, lastG: null, done: new Set(), evalN: 0, lastEvalT: 0, inViewS: 0, seenT0: null, legs: [],
      scopeEv: false, ofEv: false, stops: new Set(), visitEnd: null };
    return tr._k;
  }
  // ------------------------------------------------------------------------------------------------ evaluation
  step(tr, f, dataNow) { const ev = this.evaluate(tr, dataNow); const L = tr.fx[tr.fx.length - 1] || f; return { phase: L.ph, src: L.pi && L.pi.src, rule: L.pi && L.pi.rule, rwy: L.pi && L.pi.rwy, leg: L.pi && L.pi.leg, provisional: !!(L.pi && L.pi.provisional), events: ev }; }
  tick(tr, dataNow) { const K = this.k(tr); if (dataNow - K.lastEvalT < 5000) return []; return this.evaluate(tr, dataNow); }
  flush(tr, dataNow) { return this.evaluate(tr, dataNow, true); }

  // motion track (derive.motion_track) and the 3-point median of h within a burst (derive.median3) for fix i
  derive2(F, i) {
    const f = F[i], n = F.length;
    let trk = f.g && f.th != null ? f.th : f.trk;
    for (const [j0, j1] of [[i - 1, i + 1], [i - 1, i], [i, i + 1]]) {
      if (j0 >= 0 && j1 < n && j0 !== j1 && F[j1].t - F[j0].t <= 15000) { const dx = F[j1].x - F[j0].x, dz = F[j1].z - F[j0].z; if (Math.hypot(dx, dz) >= 4) { trk = brg(dx, dz); break; } }
    }
    f.mtrk = trk;
    if (!f.g && f.hRaw != null) {
      const w = [f.hRaw];
      if (i > 0 && !F[i - 1].g && f.t - F[i - 1].t <= R.HOLE_S * 1000 && F[i - 1].hRaw != null) w.push(F[i - 1].hRaw);
      if (i + 1 < n && !F[i + 1].g && F[i + 1].t - f.t <= R.HOLE_S * 1000 && F[i + 1].hRaw != null) w.push(F[i + 1].hRaw);
      f.h = median(w);
    }
  }
  state(tr, f, heli) {
    if (f.r > (heli ? R.HELI_R : R.R_FIELD)) return ['-', ''];
    if (heli) {
      if (f.g) return ['G', ''];
      if (f.h != null && f.h <= R.HELI_H && f.gs != null && f.gs <= R.HELI_GS) return ['H', ''];
      return ['A', ''];
    }
    const hc = this.k(tr).q === 25 ? R.H_CONTACT : R.H_CONTACT_COARSE;
    const s = f.strip, trk = f.mtrk, gs = f.gs;
    if (s && (f.gk || (f.h != null && f.h <= hc))) {
      if ((gs != null && gs < 5) || trk == null || aligned(trk, s)) return ['R', s];
    }
    if (f.gk) return ['G', ''];
    const c = f.corr;
    if (c && f.h != null && f.h <= R.H_LOW && trk != null && aligned(trk, c)) return ['L', c];
    return ['A', ''];
  }
  label(f, ph, info) { f.ph = ph; f.pi = info; }

  evaluate(tr, dataNow, final = false) {
    const F = tr.fx; const n = F.length; if (!n) return [];
    const K = this.k(tr); K.lastEvalT = dataNow; this.counters.evals++;
    const heli = this.isHeli(tr);
    const tWin = dataNow - R.WIN_S * 1000;
    let w0 = n - 1; while (w0 > 0 && F[w0 - 1].t >= tWin) w0--;
    // derived values + states: recompute the newest few (their neighbours may have changed)
    const from = Math.max(w0, Math.min(K.evalN, n) - 3);
    for (let i = from; i < n; i++) this.derive2(F, i);
    for (let i = from; i < n; i++) { const [s, rid] = this.state(tr, F[i], heli); F[i].st = s; F[i].rid = rid; }
    K.evalN = n;
    const ev = [];
    if (tr.vehicle) { for (let i = from; i < n; i++) this.label(F[i], 'vehicle', { src: 'obs', rule: 'vehicle' }); return ev; }
    // base labels (per fix) for the window, then the episode / pass revisions on top
    // still runs (gs < STILL_GS, within BREAK_M of the run's first fix, gaps <= 120 s) in one pass: runA / runB = run bounds
    const runA = new Int32Array(n).fill(-1), runB = new Int32Array(n).fill(-1);
    const isStill = (q) => q.st === 'G' && (q.gs == null || q.gs < R.STILL_GS);
    let ra = -1;
    for (let i = Math.max(0, w0 - 1); i < n; i++) {
      const q = F[i]; if (!isStill(q)) { ra = -1; continue; }
      if (ra >= 0 && q.t - F[i - 1].t <= 120000 && Math.hypot(q.x - F[ra].x, q.z - F[ra].z) <= R.BREAK_M) runA[i] = ra; else { ra = i; runA[i] = i; }
    }
    for (let i = n - 1, rb = -1; i >= Math.max(0, w0 - 1); i--) { if (runA[i] < 0) { rb = -1; continue; } if (rb < 0 || runA[rb] !== runA[i]) rb = i; runB[i] = rb; }
    this._run = { runA, runB, prevParked: w0 > 0 && F[w0 - 1].ph === 'parked' };
    for (let i = w0; i < n; i++) this.baseLabel(tr, F, i, heli, dataNow);
    if (heli) this.heliEvents(tr, F, w0, dataNow, final, ev);
    else this.fixedWing(tr, F, w0, dataNow, final, ev);
    this.stops(tr, F, w0, dataNow, ev);
    this.scope(tr, F, w0, dataNow, ev);
    for (const e of ev) { e.key = tr.key; e.cls = tr.dims ? tr.dims.cls : null; e.tower = towerStatus(e.t); }
    this.counters.events += ev.length;
    return ev;
  }
  // (review round 3, iteration 2, F10) one event is emitted once: an episode re-detected after its key left K.done (pruned at
  // 400 keys) or after older fixes left the buffer (the key holds its first fix's time) came out a second time - the weekday
  // window's '7 take-offs live vs 6 offline' was one C172 take-off emitted twice, 15 min apart. Events are also identified by
  // type, runway and time (5-s buckets, +-1), kept for 2 h of event time [inf]
  emit(K, key, ev, e) {
    if (K.done.has(key)) return false; K.done.add(key);
    if (K.done.size > 400) { const it = K.done.values(); for (let i = 0; i < 100; i++) K.done.delete(it.next().value); }
    const M = K.evIds || (K.evIds = new Map()), b = Math.round((e.t || 0) / 5000), base = (e.type || e.kind || '') + ':' + (e.rwy || '') + ':';
    if (M.has(base + b) || M.has(base + (b - 1)) || M.has(base + (b + 1))) return false;
    M.set(base + b, e.t || 0); for (const [k, t] of M) if (t < (e.t || 0) - 7200e3) M.delete(k);
    ev.push(e); return true;
  }
  noteFlow(e) {
    if (!e.rwy) return; this.flowEv.push([e.t, e.rwy.startsWith('28') ? '28' : '10']);
    while (this.flowEv.length && e.t - this.flowEv[0][0] > 1800e3) this.flowEv.shift();
    const w = this.flowEv.filter(q => q[1] === '28').length, ea = this.flowEv.length - w;
    if (this.flowEv.length >= 2) this.flow = { end: ea > w ? '10' : '28', src: 'obs', basis: `${Math.max(w, ea)} of the last ${this.flowEv.length} HWD runway events within 30 min`, n: this.flowEv.length };
  }

  // ---------------------------------------------------------------- base label of one fix (before episode revisions)
  baseLabel(tr, F, i, heli, dataNow) {
    const f = F[i]; const tw = towerStatus(f.t); f.stillRun = null;
    if (heli) {
      if (f.st === 'G') {
        // still runs for helicopters too (fix round 1): a helicopter standing still gets a rest pose (its median position,
        // placed by GroundPhysics, or hidden inside a hangar) instead of sliding with the GNSS noise
        const RA = this._run.runA[i], RB = this._run.runB[i];
        if (RA >= 0) { let t0 = F[RA].run0 != null && F[RA].run0 < F[RA].t ? F[RA].run0 : F[RA].t; for (let q = RA; q <= RB; q++) if (F[q].run0 == null || F[q].run0 > t0) F[q].run0 = t0;
          f.stillRun = [t0, F[RB].t]; const dur = (F[RB].t - t0) / 1000;
          return this.label(f, 'heli_ground', { src: 'obs', rule: 'hwd_events.heli.G (still)', heliPark: RA === 0 || dur >= R.PARK_S, tower: tw }); }
        return this.label(f, 'heli_ground', { src: 'obs', rule: 'hwd_events.heli.G', tower: tw });
      }
      if (f.st === 'H') {
        const p = F[i - 1], q = F[i + 1]; let mv = f.gs != null ? f.gs >= 3 : false;
        if (p && f.t - p.t <= 15000 && Math.hypot(f.x - p.x, f.z - p.z) >= 4) mv = true;
        return this.label(f, mv ? 'heli_hover_taxi' : 'heli_hover', { src: mv ? 'obs' : 'inf', rule: mv ? 'hwd_events.heli.H moving' : 'H state, < 3 kt [inf]', tower: tw });
      }
      return this.label(f, tr.scope === 'overflight' ? 'overflight' : 'heli_air', { src: 'obs', rule: 'hwd_events.heli.A', tower: tw });
    }
    if (f.st === 'G') return this.groundLabel(tr, F, i, tw);
    if (f.st === 'R') return this.label(f, 'runway_taxi', { src: 'obs', rule: 'hwd_events.R', rwy: f.rid, provisional: true, tower: tw });   // revised by the episode
    if (f.st === 'L') {
      const end = f.mtrk != null ? endOf(f.rid, f.mtrk) : null; let ph = 'final';
      if (end) {
        const A = rwyAxis(end), al = (f.x - A.origin[0]) * A.dir[0] + (f.z - A.origin[1]) * A.dir[1];
        const climbing = f.vs != null ? f.vs > 200 : false, desc = f.vs != null ? f.vs < -200 : false;
        ph = desc ? 'final' : climbing ? 'initial_climb' : al < A.length / 2 ? 'final' : 'initial_climb';
      }
      return this.label(f, ph, { src: 'obs', rule: 'hwd_events.L (corridor) + direction [inf]', rwy: end, leg: ph === 'final' ? 'final' : 'upwind', tower: tw });
    }
    if (f.st === '-') {
      const ph = tr.scope === 'hwd' ? (f.g ? 'unknown' : this.inOut(tr, F, i)) : f.g ? 'overflight' : (tr.scope === 'overflight' ? 'overflight' : this.inOut(tr, F, i));
      return this.label(f, ph, { src: 'inf', rule: 'beyond R_FIELD', tower: tw });
    }
    // A: pattern legs
    const leg = this.leg(f);
    if (leg) return this.label(f, leg.ph, { src: 'inf', rule: 'pattern leg (AIM 4-3-3 [verify]; thresholds [inf])', rwy: leg.end, leg: leg.ph, tower: tw });
    return this.label(f, tr.scope === 'overflight' ? 'overflight' : this.inOut(tr, F, i), { src: 'inf', rule: 'range rate', tower: tw });
  }
  inOut(tr, F, i) {
    const f = F[i], p = F[Math.max(0, i - 3)];
    if (p === f || f.t - p.t > 120000) return tr.scope === 'overflight' ? 'overflight' : 'arriving';
    return f.r < p.r - 20 ? 'arriving' : 'departing';
  }
  groundLabel(tr, F, i, tw) {
    const f = F[i];
    if (f.strip) return this.label(f, 'runway_taxi', { src: 'obs', rule: 'G on a runway strip (crossing / not aligned)', rwy: f.strip, tower: tw });
    const still = f.gs == null ? true : f.gs < R.STILL_GS;
    if (!still) return this.label(f, 'taxi', { src: 'obs', rule: 'ground (flag or kinematics), moving', tower: tw });
    const RA = this._run.runA[i], RB = this._run.runB[i];
    const a = RA >= 0 ? RA : i, b = RB >= 0 ? RB : i;
    // a run that began before the window (or the track's first fix): long enough / first heard standing
    const first = a === 0;
    // the run's start is kept stable across evaluations (the window slides; the earliest start seen for its first fix wins)
    let t0 = F[a].run0 != null && F[a].run0 < F[a].t ? F[a].run0 : F[a].t;
    for (let q = a; q <= b; q++) if (F[q].run0 == null || F[q].run0 > t0) F[q].run0 = t0;
    f.stillRun = [t0, F[b].t];
    const dur = (F[b].t - t0) / 1000;
    const hold = this.holds.find(h => Math.hypot(h.x - f.x, h.z - f.z) <= R.HOLD_R);
    const ap = this.site ? this.site.apronAt(f.x, f.z) : null;
    if (hold && !first) return this.label(f, 'hold_short', { src: 'obs', rule: 'runup_holds.HOLD_R (place obs; clearance inf)', rwy: hold.runway, hold: hold.id, tower: tw });
    if (ap && ap.name && /run-?up/i.test(ap.name) && !first) return this.label(f, 'runup', { src: 'inf', rule: 'still in a run-up apron (place obs, purpose inf)', apron: ap.name, tower: tw });
    // parked only where an aircraft can be left (an apron / helipad / a hangar door, this.parkable); standing on a taxiway or a
    // runway is a stop while taxiing however long it lasts (fix round 1: 'first heard standing' on a taxiway made a park record)
    const place = this.parkable ? this.parkable(f.x, f.z, false) : true;
    if ((first || dur >= R.PARK_S) && place) return this.label(f, 'parked', { src: 'obs', rule: first ? 'first heard standing still' : `still >= ${R.PARK_S} s [inf]`, tower: tw });
    return this.label(f, 'taxi', { src: 'obs', rule: place ? 'stopped while taxiing' : 'stopped on a taxiway', stopped: true, tower: tw });
  }
  // pattern leg of an airborne fix [inf thresholds]: the pattern of the runway pair on whose side the aircraft is
  onFinalFix(f) {
    for (const rid of RIDS) { const A = AX[rid], [al, ac] = f.Rf[rid], L = A.length;
      for (const [end, sg] of [[rid.split('/')[0], 1], [rid.split('/')[1], -1]]) {
        const thr = sg > 0 ? thrDispM(end) : L - thrDispM(end), before = (thr - al) * sg, hdg = sg > 0 ? A.hdg : (A.hdg + 180) % 360;
        if (before < 556 || before > 4 * 1852 || Math.abs(ac) > Math.max(150, 0.06 * before) || angd(f.mtrk, hdg) > R.FIN_ALIGN) continue;
        if (f.h <= before * Math.tan(4.5 * Math.PI / 180) / FT + 150) return end;
      } }
    return null;
  }
  // (round 4, E2 / E5) the pattern leg of a DRAWN body (x, z m; hFt above the runway surface; trkDeg its direction of motion, deg true) -
  // the same rule as a fix's: traffic.js labels a climbing-out / crosswind / downwind body by where it is and where it flies, not by the
  // label of the fix before a hole -> { ph, end } | null
  legOf(x, z, hFt, trkDeg) { return this.leg({ x, z, h: hFt, mtrk: trkDeg, r: Math.hypot(x, z), Rf: rwyFrame(x, z) }); }
  leg(f) {
    if (f.h == null || f.mtrk == null || f.r > R.LEG_MAX_NM * 1852) return null;
    // which pair: south of the midline of the two runways -> 10R/28L (its pattern sides are south: 10R right, 28L left);
    // north -> 10L/28R (10L left, 28R right) [obs NASR sides; the midline split is inf]
    const acS = f.Rf['10R/28L'][1], acN = f.Rf['10L/28R'][1];   // across right of the 10x direction (heading ~120): right = south-west
    const rid = (acS + acN) / 2 > 0 ? '10R/28L' : '10L/28R';
    if (f.h > TPA_AGL[rid] + R.LEG_ABOVE_TPA_FT) return null;
    const end = this.flow.end === '10' ? rid.split('/')[0] : rid.split('/')[1];
    const A = rwyAxis(end); const L = A.length;
    const px = f.x - A.origin[0], pz = f.z - A.origin[1];
    const al = px * A.dir[0] + pz * A.dir[1], ac = px * A.right[0] + pz * A.right[1];
    const side = RWY_ENDS[end].rhTraffic ? 1 : -1;             // pattern side: + right of the landing direction
    const rel = wrap180(f.mtrk - A.hdg);
    const thr = thrDispM(end);
    if (Math.abs(rel) <= R.LEG_ALIGN) {
      if (Math.abs(ac) <= R.CL_M) return { ph: al < thr ? 'final' : 'initial_climb', end };
      // (round 4, E5: no 'upwind' leg 3-4 km beside the runway - a parallel track that far off is not the departure leg) [inf: UPW_M]
      return Math.abs(ac) <= R.UPW_M ? { ph: 'upwind', end } : null;
    }
    if (Math.abs(rel) >= 180 - R.LEG_ALIGN) {
      if (ac * side > 0.25 * 1852 && ac * side < 2.5 * 1852) return { ph: 'downwind', end };
      return null;
    }
    if (Math.abs(Math.abs(rel) - 90) <= 90 - R.LEG_ALIGN) {
      // perpendicular: moving toward the pattern side or toward the centreline?
      const vAc = Math.sin(rel * Math.PI / 180);     // + = toward the right of the landing direction
      const away = vAc * side > 0 ? (ac * side > -R.CL_M) : false;
      if (al > L * 0.5 && away) return { ph: 'crosswind', end };
      if (al < L * 0.5 && !away && ac * side > 0) return { ph: 'base', end };
      return null;
    }
    return null;
  }

  // ---------------------------------------------------------------- fixed wing: episodes, hidden transitions, low passes
  ctx(F, st, i, step, dataNow) {
    const n = F.length; let j = i + step; const low = [];
    while (j >= 0 && j < n && F[j].st !== '-' && Math.abs(F[j].t - F[i].t) <= R.CTX_GAP * 1000) {
      const s = F[j].st;
      if (s === 'G') return ['ground', j, true];
      if (s === 'A' || s === 'L') { if (F[j].h == null || F[j].h > R.H_BREAK) return ['air', j, true]; low.push(j); }
      j += step;
    }
    // decided when the scan stopped at a fix beyond CTX_GAP or at a '-' fix, or (forward) when time has passed CTX_GAP
    const decided = step < 0 || (j < n) || dataNow - F[i].t > R.CTX_GAP * 1000;
    if (low.length) {
      if (step < 0) return ['air', low[0], true];
      const hh = low.map(k => F[k].h); if (Math.max(...hh) >= hh[0] + 25) return ['air', low[low.length - 1], decided];
    }
    return ['none', null, decided];
  }
  fixedWing(tr, F, w0, dataNow, final, ev) {
    const K = this.k(tr); const n = F.length;
    const isR = (i) => F[i].st === 'R';
    const eps = []; let cur = [];
    for (let i = w0; i < n; i++) {
      if (!isR(i)) continue;
      if (cur.length) {
        const p = cur[cur.length - 1]; let br = F[i].rid !== F[p].rid || F[i].t - F[p].t > R.EP_GAP * 1000;
        if (!br) for (let k = p + 1; k < i; k++) { const s = F[k].st; if (s === 'G' || ((s === 'A' || s === '-') && (F[k].h == null || F[k].h > R.H_BREAK))) { br = true; break; } }
        if (br) { eps.push(cur); cur = []; }
      }
      cur.push(i);
    }
    if (cur.length) eps.push(cur);
    const tR = eps.map(e => [F[e[0]].t, F[e[e.length - 1]].t]);
    for (const e of eps) {
      if (e[0] === w0 && w0 > 0) continue;     // cut by the window start: decided long ago (its key would change)
      const r = F[e[0]].rid;
      const [pv, ip] = this.ctx(F, null, e[0], -1, dataNow);
      const [nx, inx, decided0] = this.ctx(F, null, e[e.length - 1], +1, dataNow);
      // decided only when the deciding fix has a successor or is older than HOLE_S (its own state is then stable)
      const decided = final || (decided0 && (inx == null || inx + 1 < n || dataNow - F[inx].t > R.HOLE_S * 1000));
      const gsL = e.map(i => F[i].gs).filter(v => v != null);
      const gmin = gsL.length ? Math.min(...gsL) : null, g0 = gsL.length ? gsL[0] : null, g1 = gsL.length ? gsL[gsL.length - 1] : null;
      let hmin = null; for (let q = 1; q < e.length; q++) { const a = F[e[q - 1]], b = F[e[q]], dt = (b.t - a.t) / 1000; if (dt > R.HOLE_S) { const v = Math.hypot(b.x - a.x, b.z - a.z) / dt / KT; hmin = hmin == null ? v : Math.min(hmin, v); } }
      const nG = e.filter(i => F[i].g).length, nK = e.filter(i => F[i].gk && !F[i].g).length;
      const gApp = ip != null ? F[ip].gs : null;
      const decel = gmin != null && gApp != null && pv === 'air' && gmin < R.DECEL_RATIO * gApp;
      const contact = nG > 0 || nK > 0 || (e.length >= 2 && K.q === 25) || decel;
      let typ, src = 'obs', evd = [];
      if (pv === 'air' && nx === 'air') {
        if (gmin != null && gmin < R.STOP_GS) { typ = 'stop_and_go'; evd.push(`min gs ${gmin.toFixed(0)} kt observed`); }
        else if (hmin != null && hmin < R.STOP_HOLE_GS) { typ = 'stop_and_go'; src = 'inf'; evd.push(`mean ${hmin.toFixed(0)} kt across a hole`); }
        else { typ = 'touch_and_go'; if (!contact) { src = 'inf'; evd.push(K.q === 25 ? 'single fix at h <= 30 ft' : '100-ft altitude unit, no ground flag or deceleration'); } }
      } else if (pv === 'air' && nx === 'ground') typ = 'full_stop_landing';
      else if (pv === 'ground' && nx === 'air') typ = 'takeoff';
      else if (pv === 'none' && nx === 'air') { typ = 'takeoff'; src = 'inf'; evd.push('taxi-out unobserved'); }
      else if (pv === 'ground' && nx === 'none') { if (g1 != null && g1 >= R.LIFT_GS) { typ = 'takeoff'; src = 'inf'; evd.push('lift-off unobserved'); } else typ = 'runway_ground_move'; }
      else if (pv === 'air' && nx === 'none') { if (g1 != null && g1 < R.EXIT_GS) { typ = 'full_stop_landing'; src = 'inf'; evd.push('exit unobserved'); } else typ = 'landing_unresolved'; }
      else if (pv === 'none' && nx === 'ground') { if (g0 != null && g0 >= R.LIFT_GS) { typ = 'full_stop_landing'; src = 'inf'; evd.push('approach unobserved'); } else typ = 'runway_ground_move'; }
      else if (pv === 'ground' && nx === 'ground') typ = 'runway_ground_move';
      else typ = 'unresolved';
      // runway end (fix round 1): the direction of the airborne neighbour that decides the episode - the climb-out fix of a
      // take-off, the approach fix of a landing - when it is aligned with the runway; else the gs-weighted circular mean of
      // the episode fixes at >= END_GS kt (a slow line-up turn at the far end said nothing about the direction: a 28R
      // departure was counted as a 10L take-off); else the displacement of the episode
      let end = null; {
        const dec = typ === 'takeoff' ? [inx, ip] : typ === 'full_stop_landing' || typ === 'landing_unresolved' ? [ip, inx] : [ip, inx];
        for (const k of dec) { if (k == null || F[k].mtrk == null || F[k].st === 'G') continue; if (aligned(F[k].mtrk, r)) { end = endOf(r, F[k].mtrk); break; } }
        if (!end) { let sx = 0, sz = 0; for (const i of e) { const f = F[i]; if (f.mtrk == null || (f.gs != null && f.gs < R.END_GS)) continue; const w = Math.max(f.gs ?? 10, 1); sx += Math.sin(f.mtrk * Math.PI / 180) * w; sz += Math.cos(f.mtrk * Math.PI / 180) * w; }
          if (sx || sz) end = endOf(r, brg(sx, -sz)); }
        if (!end && e.length >= 2) { const a = F[e[0]], b = F[e[e.length - 1]]; if (Math.hypot(b.x - a.x, b.z - a.z) > 20) end = endOf(r, brg(b.x - a.x, b.z - a.z)); }
        if (!end) for (const k of [ip, inx]) if (k != null && F[k].mtrk != null) { end = endOf(r, F[k].mtrk); break; } }
      // labels: provisional while undecided
      const prov = !decided;
      const lab = (ph, i, extra = {}) => this.label(F[i], ph, { src, rule: `hwd_events.${typ}`, rwy: end, provisional: prov || typ === 'landing_unresolved' || typ === 'unresolved', tower: towerStatus(F[i].t), ...extra });
      if (prov) {
        for (const i of e) {
          const f = F[i]; let ph;
          if (pv === 'air') ph = 'landing_roll';
          else if (f.gs != null && f.gs < 5 && aligned(f.mtrk ?? AX[r].hdg, r)) ph = 'line_up';
          else { const p = F[i - 1]; ph = (f.gs != null && f.gs >= 20) || (p && p.gs != null && f.gs != null && f.gs > p.gs + 1) ? 'takeoff_roll' : 'runway_taxi'; }
          lab(ph, i);
        }
      } else {
        for (const i of e) {
          const f = F[i]; let ph;
          if (typ === 'touch_and_go') ph = 'touch_and_go';
          else if (typ === 'stop_and_go') ph = 'stop_and_go';
          else if (typ === 'full_stop_landing' || typ === 'landing_unresolved') ph = 'landing_roll';
          else if (typ === 'takeoff') ph = f.gs != null && f.gs < 5 ? 'line_up' : 'takeoff_roll';
          else ph = f.gs != null && f.gs < 5 && f.mtrk != null && aligned(f.mtrk, r) ? 'line_up' : 'runway_taxi';
          lab(ph, i);
        }
        const tEv = typ === 'takeoff' ? F[e[e.length - 1]].t : F[e[0]].t;
        const E = { t: tEv, kind: KIND_OF[typ], type: typ, rwy: end, runway: r, src, rule: `hwd_events.${typ}`, evidence: evd.join('; '), via: 'runway_episode',
          dur_s: (F[e[e.length - 1]].t - F[e[0]].t) / 1000, n: e.length, x: F[e[0]].x, z: F[e[0]].z };
        if (this.emit(K, `ep:${r}:${F[e[0]].t}`, ev, E)) { if (end && ['takeoff', 'full_stop_landing', 'touch_and_go', 'stop_and_go'].includes(typ)) this.noteFlow(E); K.hwd = K.hwd || E.t; }
      }
      K.hwd = K.hwd || F[e[0]].t;     // runway contact = HWD traffic (D6)
    }
    // hidden transitions G <-> air (no R fix between)
    const hid = new Set();
    for (let i = w0; i < n - 1; i++) {
      const a = F[i], b = F[i + 1];
      if (a.st === '-' || b.st === '-' || b.t - a.t > R.HID_GAP * 1000) continue;
      let g, air, typ;
      if (a.st === 'G' && (b.st === 'L' || b.st === 'A') && b.h != null && b.h <= R.HID_H) { g = i; air = i + 1; typ = 'takeoff'; }
      else if ((a.st === 'L' || a.st === 'A') && b.st === 'G' && a.h != null && a.h <= R.HID_H) { g = i + 1; air = i; typ = 'full_stop_landing'; }
      else continue;
      if (Math.abs(F[g].acNear) > R.HID_NEAR) continue;
      if (F[air].gs == null || F[air].gs < R.PASS_GS) continue;
      if (tR.some(([s, e]) => s - R.CTX_GAP * 1000 <= b.t && a.t <= e + R.CTX_GAP * 1000)) continue;
      hid.add(i); hid.add(i + 1);
      const rr = F[air].st === 'L' ? F[air].rid : F[g].near; const end = F[air].mtrk != null ? endOf(rr, F[air].mtrk) : null;
      K.hwd = K.hwd || b.t;
      if (!final && dataNow - b.t <= R.CTX_GAP * 1000) continue;    // an episode may still appear within CTX_GAP
      const E = { t: F[air].t, kind: KIND_OF[typ], type: typ, rwy: end, runway: rr, src: 'inf', rule: `hwd_events.hidden_transition.${typ}`,
        evidence: `roll unobserved: ${a.st}->${b.st} in ${((b.t - a.t) / 1000).toFixed(0)} s`, via: 'hidden_transition', x: F[g].x, z: F[g].z };
      if (this.emit(K, `hid:${a.t}`, ev, E)) this.noteFlow(E);
    }
    // low passes
    const runs = []; cur = [];
    for (let i = w0; i < n; i++) {
      if (F[i].st !== 'L') continue;
      if (cur.length) { const p = cur[cur.length - 1]; let br = F[i].rid !== F[p].rid || F[i].t - F[p].t > R.EP_GAP * 1000; if (!br) for (let k = p + 1; k < i; k++) if (['G', 'R', '-'].includes(F[k].st)) { br = true; break; } if (br) { runs.push(cur); cur = []; } }
      cur.push(i);
    }
    if (cur.length) runs.push(cur);
    for (const rn of runs) {
      if (rn[0] === w0 && w0 > 0) continue;    // cut by the window start (see the episodes)
      const t0 = F[rn[0]].t, t1 = F[rn[rn.length - 1]].t;
      if (tR.some(([s, e]) => s - R.PASS_ISO * 1000 <= t1 && t0 <= e + R.PASS_ISO * 1000)) continue;
      if (rn.some(k => hid.has(k)) || hid.has(rn[0] - 1) || hid.has(rn[rn.length - 1] + 1)) continue;
      const hh = rn.map(i => F[i].h ?? 1e9); let k = 0; for (let q = 1; q < hh.length; q++) if (hh[q] < hh[k]) k = q;
      const imin = rn[k];
      if (hh[k] > R.H_PASS || rn.length < R.PASS_MIN_N) continue;
      if (F[imin].gs == null || F[imin].gs < R.PASS_GS) continue;
      K.hwd = K.hwd || F[imin].t;
      const later = hh.slice(k + 1); const nxt = rn[rn.length - 1] + 1;
      const climbs = (later.length && Math.max(...later) >= hh[k] + 50) || (nxt < n && F[nxt].st === 'A' && F[nxt].t - t1 <= R.CTX_GAP * 1000);
      const isDone = final || dataNow - t1 > R.CTX_GAP * 1000;
      if (!climbs) { if (!isDone) for (const i of rn) if (F[i].ph === 'final' || F[i].ph === 'initial_climb') F[i].pi = { ...F[i].pi, provisional: true }; continue; }
      const end = (() => { let sx = 0, sz = 0; for (const i of rn) { const f = F[i]; if (f.mtrk == null) continue; sx += Math.sin(f.mtrk * Math.PI / 180); sz += Math.cos(f.mtrk * Math.PI / 180); } return sx || sz ? endOf(F[imin].rid, brg(sx, -sz)) : null; })();
      let b0 = k; while (b0 > 0 && F[rn[b0]].t - F[rn[b0 - 1]].t <= R.HOLE_S * 1000) b0--;
      let b1 = k; while (b1 + 1 < rn.length && F[rn[b1 + 1]].t - F[rn[b1]].t <= R.HOLE_S * 1000) b1++;
      let seenDown = false, seenUp = false; for (let q = b0; q < k; q++) if (hh[q] >= hh[k] + 25) seenDown = true; for (let q = k + 1; q <= b1; q++) if (hh[q] >= hh[k] + 50) seenUp = true;
      let typ = 'low_approach_go_around', src = 'obs'; const evd = []; let slow = null;
      if (!(seenDown && seenUp)) {
        src = 'inf'; typ = 'low_pass_unresolved'; const nb = [];
        if (!seenDown) { const ib = rn[b0] - 1; if (ib >= 0 && F[ib].st !== '-') nb.push([ib, rn[b0]]); }
        if (!seenUp) { const ia = rn[b1] + 1; if (ia < n && F[ia].st !== '-') nb.push([rn[b1], ia]); }
        for (const [i, j] of nb) {
          const dt = (F[j].t - F[i].t) / 1000; if (dt <= R.HOLE_S || dt > R.EP_GAP) continue;
          const v = Math.hypot(F[j].x - F[i].x, F[j].z - F[i].z) / dt / KT; const gi = F[i].gs, gj = F[j].gs;
          const ref = gi == null && gj == null ? null : Math.min(gi ?? Infinity, gj ?? Infinity);
          const r_ = ref ? v / ref : null; evd.push(`hole of ${dt.toFixed(0)} s next to the lowest observed fix`);
          if (r_ != null && (slow == null || r_ < slow)) slow = r_;
        }
        if (slow != null && slow < R.SLOW_RATIO && hh[k] <= 100) { typ = 'touch_and_go'; evd.push(`mean speed across the hole ${(100 * slow).toFixed(0)} % of the slower side`); }
        if (!evd.length) evd.push('lowest point at the end of the observed track');
      }
      const ph = typ === 'touch_and_go' ? 'touch_and_go' : typ === 'low_approach_go_around' ? 'go_around' : 'low_pass';
      // label the fixes of the lowest burst (b0..b1) with the pass phase
      for (let q = b0; q <= b1; q++) this.label(F[rn[q]], ph, { src, rule: `hwd_events.low_pass.${typ}`, rwy: end, provisional: !isDone || typ === 'low_pass_unresolved', tower: towerStatus(F[rn[q]].t) });
      if (!isDone) continue;
      const E = { t: F[imin].t, kind: KIND_OF[typ], type: typ, rwy: end, runway: F[imin].rid, src, rule: `hwd_events.low_pass.${typ}`, evidence: evd.join('; '), via: 'low_pass',
        h_min: Math.round(hh[k]), x: F[imin].x, z: F[imin].z };
      if (this.emit(K, `lp:${t0}`, ev, E) && typ === "touch_and_go") this.noteFlow(E);
    }
  }
  // ---------------------------------------------------------------- helicopters
  heliEvents(tr, F, w0, dataNow, final, ev) {
    const K = this.k(tr); const n = F.length;
    for (let i = Math.max(w0, 1) - 1; i < n - 1; i++) {
      const a = F[i], b = F[i + 1];
      if (a.st === '-' || b.st === '-' || b.t - a.t > R.HID_GAP * 1000) continue;
      let typ, g;
      if (a.st === 'G' && (b.st === 'H' || b.st === 'A')) { typ = 'lift_off'; g = i; }
      else if ((a.st === 'H' || a.st === 'A') && b.st === 'G') { typ = 'touch_down'; g = i + 1; }
      else continue;
      if (F[g].r <= 1500) K.hwd = K.hwd || F[g].t;
      const ap = this.site ? this.site.apronAt(F[g].x, F[g].z) : null; const sf = this.site ? this.site.surface(F[g].x, F[g].z) : null;
      this.emit(K, `h:${typ}:${a.t}`, ev, { t: F[g].t, kind: typ, type: typ, rwy: null, src: b.t - a.t <= R.HOLE_S * 1000 ? 'obs' : 'inf', rule: `hwd_events.heli.${typ}`,
        place: sf, apron: ap && ap.name, x: F[g].x, z: F[g].z });
    }
    // hover-taxi runs
    let cur = [];
    const flush = (c, closed) => {
      if (c.length < 2 || (c[0] === w0 && w0 > 0)) return; let path = 0; for (let q = 1; q < c.length; q++) path += Math.hypot(F[c[q]].x - F[c[q - 1]].x, F[c[q]].z - F[c[q - 1]].z);
      if (path < R.HOVER_MIN_M) return;
      if (F[c[0]].r <= 1500) K.hwd = K.hwd || F[c[0]].t;
      if (!closed) return;
      this.emit(K, `hv:${F[c[0]].t}`, ev, { t: F[c[0]].t, kind: 'hover_taxi', type: 'hover_taxi', rwy: null, src: 'obs', rule: 'hwd_events.heli.hover_taxi', dur_s: (F[c[c.length - 1]].t - F[c[0]].t) / 1000,
        path_m: Math.round(path), place: this.site ? this.site.surface(F[c[0]].x, F[c[0]].z) : null, x: F[c[0]].x, z: F[c[0]].z });
    };
    for (let i = w0; i < n; i++) {
      if (F[i].st === 'H' && (!cur.length || F[i].t - F[cur[cur.length - 1]].t <= R.EP_GAP * 1000)) cur.push(i);
      else { flush(cur, true); cur = F[i].st === 'H' ? [i] : []; }
    }
    flush(cur, final || (cur.length && dataNow - F[cur[cur.length - 1]].t > R.EP_GAP * 1000));
    // low transit: a visit (fixes within HELI_R, visits > 30 min apart) with H/A fixes below HELI_H and no G fix
    if (!K.visit) K.visit = { start: null, last: null, g: false, low: null };
    const V = K.visit;
    for (let i = K.visitI ?? 0; i < n; i++) {
      const f = F[i]; if (f.st === '-') continue;
      if (V.last != null && f.t - V.last > R.VISIT_GAP_S * 1000) { this.closeVisit(tr, K, ev); }
      if (V.start == null) V.start = f.t;
      V.last = f.t; if (f.st === 'G') V.g = true; if (f.h != null && (V.low == null || f.h < V.low.h)) V.low = { h: f.h, t: f.t, x: f.x, z: f.z };
    }
    K.visitI = n;
    if (V.last != null && (final || dataNow - V.last > R.VISIT_GAP_S * 1000)) this.closeVisit(tr, K, ev);
  }
  closeVisit(tr, K, ev) {
    const V = K.visit;
    if (V.start != null && !V.g && V.low && V.low.h <= R.HELI_H)
      this.emit(K, `lt:${V.start}`, ev, { t: V.low.t, kind: 'overflight', type: 'low_transit', rwy: null, src: 'obs', rule: 'hwd_events.heli.low_transit', h_min: Math.round(V.low.h), x: V.low.x, z: V.low.z });
    K.visit = { start: null, last: null, g: false, low: null };
  }
  // ---------------------------------------------------------------- stops (runup / hold short / line up) of >= MIN_S
  stops(tr, F, w0, dataNow, ev) {
    const K = this.k(tr);
    for (let i = w0; i < F.length; i++) {
      const f = F[i]; if (!f.stillRun) continue;
      const kind = f.ph === 'runup' ? 'runup' : f.ph === 'hold_short' ? 'hold_short' : f.ph === 'line_up' ? 'line_up' : null; if (!kind) continue;
      const dur = (f.stillRun[1] - f.stillRun[0]) / 1000; if (dur < R.MIN_S) continue;
      // one stop event per still run (fix round 1: a run whose fixes were labelled both hold_short and runup gave both)
      this.emit(K, `st:${f.stillRun[0]}`, ev, { t: f.stillRun[0], kind, type: kind, rwy: f.pi && f.pi.rwy || null, src: kind === 'runup' ? 'inf' : 'obs', rule: `runup_holds.${kind} (>= ${R.MIN_S} s still)`,
        dur_s: dur, x: f.x, z: f.z, apron: f.pi && f.pi.apron || null });
    }
    // line-up stops on the runway (R fixes still >= MIN_S)
    let a = null;
    for (let i = w0; i < F.length; i++) {
      const f = F[i]; const still = f.st === 'R' && f.gs != null && f.gs < R.STILL_GS;
      if (still && a == null) a = i;
      if ((!still || i === F.length - 1) && a != null) { const b = still ? i : i - 1; const dur = (F[b].t - F[a].t) / 1000;
        if (dur >= R.MIN_S && b > a && !(a === w0 && w0 > 0)) this.emit(K, `lu:${F[a].t}`, ev, { t: F[a].t, kind: 'line_up', type: 'line_up', rwy: F[a].pi && F[a].pi.rwy || null, src: 'obs', rule: 'runup_holds.line_up', dur_s: dur, x: F[a].x, z: F[a].z });
        a = null; }
    }
  }
  // (round 4 iteration 2, F6) descending toward the field (RULES ARR_*)
  arrivingField(F, L) {
    if (L.g || L.h == null || L.h > R.ARR_H_FT || L.r > R.ARR_R_M || L.mtrk == null || !(L.vs != null && L.vs < -300)) return false;
    const brg = (Math.atan2(-L.x, L.z) * 180 / Math.PI + 360) % 360; if (angd(L.mtrk, brg) > R.ARR_DEG) return false;
    let i = F.length - 1; while (i > 0 && L.t - F[i - 1].t <= 60000) i--;
    return F[i] !== L && F[i].r - L.r > 300;
  }
  // closing on HWD below 2,000 ft AGL within 5 NM (an arrival that has not joined yet stays 'pending') [inf]
  closing(F, L) {
    if (L.g || L.h == null || L.h > 2000 || L.r > 9260) return false;
    let i = F.length - 1; while (i > 0 && L.t - F[i - 1].t <= 60000) i--;
    return F[i] !== L && F[i].r - L.r > 200;
  }
  // ---------------------------------------------------------------- scope (D6)
  scope(tr, F, w0, dataNow, ev) {
    const K = this.k(tr); const L = F[F.length - 1];
    // ground on the field (G within 1.5 km of the ARP on pavement), pattern legs
    for (let i = w0; i < F.length; i++) {
      const f = F[i];
      if (!K.hwd && (f.st === 'G' || (f.st === 'H' && f.h != null && f.h <= 50)) && f.r <= 1500 && (!this.site || this.site.paved(f.x, f.z) || f.r <= 1200)) K.hwd = f.t;
      // an L corridor fix (aligned with an HWD runway within CORR_M of its axis, h <= H_LOW) at or below H_PASS within R_FIELD:
      // an aircraft that low on an HWD approach / climb-out corridor uses HWD (fix round 1: documented, not implemented; a
      // departure first heard just after lift-off was tagged overflight)
      if (!K.hwd && f.st === 'L' && f.h != null && f.h <= R.H_PASS && f.r <= R.R_FIELD) K.hwd = f.t;
      // (round 4, E7) on FINAL for an HWD runway: aligned with a landing direction (<= FIN_ALIGN), on its extended centreline (<=
      // max(150 m, 6 % of the distance)), 0.3-4 NM before the threshold, at or below a 4.5-deg path + 150 ft (<= 1,600 ft) and not
      // climbing - its track leads to an HWD runway (case P was 'Overflight (not HWD traffic)' on base and early final, until ~1.3 NM
      // out, where its first corridor fix at <= 300 ft arrived) [inf: every value]
      if (!K.hwd && !f.g && f.h != null && f.h <= 1600 && f.mtrk != null && !(f.vs != null && f.vs > 300) && this.onFinalFix(f)) { K.hwd = f.t; K.hwdWhy = 'final'; }
      // (round 4 iteration 2, F6: a fix on an HWD pattern leg holds the overflight decision for ARR_HOLD_S, like a descent toward the field -
      // a single on the 28R downwind at its pattern altitude flipped 'Downwind 28R' <-> 'Overflight (not HWD traffic)')
      if (!f.g && ['downwind', 'base', 'final'].includes(f.ph)) K.legT = Math.max(K.legT ?? -Infinity, f.t);
      if (['crosswind', 'downwind', 'base'].includes(f.ph)) { const lg = K.legs; if (!lg.length || lg[lg.length - 1][1] !== f.ph) lg.push([f.t, f.ph]); while (lg.length && f.t - lg[0][0] > 600e3) lg.shift(); if (new Set(lg.map(q => q[1])).size >= 2) K.hwd = K.hwd || f.t; }
    }
    if (K.seenT0 == null) K.seenT0 = L.t;
    const cat = tr.info && tr.info.category;
    if (K.hwd) {
      if (tr.scope !== 'hwd') { tr.scope = 'hwd'; if (!K.scopeEv) { K.scopeEv = true; ev.push({ t: K.hwd, kind: 'scope_hwd', type: 'scope_hwd', rwy: null, src: 'obs', rule: 'D6: HWD runway / taxiway / ramp contact or pattern legs' }); } }
    } else if (!['A3', 'A4', 'A5'].includes(cat) && this.arrivingField(F, L)) { K.arrT = L.t; if (tr.scope !== 'pending') { tr.scope = 'pending'; this.counters_arr = (this.counters_arr || 0) + 1; } }
    else if (['A3', 'A4', 'A5'].includes(cat) || (L.t - K.seenT0 >= R.SCOPE_S * 1000 && !this.closing(F, L) && !(K.arrT != null && L.t - K.arrT < R.ARR_HOLD_S * 1000) && !(K.legT != null && L.t - K.legT < R.ARR_HOLD_S * 1000))) {
      if (tr.scope !== 'overflight') { tr.scope = 'overflight'; if (!K.ofEv) { K.ofEv = true; ev.push({ t: L.t, kind: 'overflight', type: 'overflight', rwy: null, src: 'inf', rule: ['A3', 'A4', 'A5'].includes(cat) ? `D6: emitter category ${cat}` : `D6: no HWD evidence in ${R.SCOPE_S} s` }); } }
    } else tr.scope = tr.scope || 'pending';
  }
}
