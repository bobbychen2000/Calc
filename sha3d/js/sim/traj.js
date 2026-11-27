// sha3d Phase 3 (P3-B): time-parameterised trajectories (new; the physical priors are cited in js/sim/perf.js).
// Pure ES module (node + browser). A Traj is a list of constant-acceleration segments along one path:
//   Traj = { kind, t0, t1, segs: [{t0, t1, s0Cm, s1Cm, v0Cms, v1Cms, aCms2, kind}], route, phases: [[t, phase]], ... }
// Segment boundaries are integers (ms, cm, cm/s). Inside a segment the position is the quadratic through (t0, s0) and
// (t1, s1) with the start speed v0 (so every segment ends exactly at its integer s1).
//
// Commit path (design §1.4): building a trajectory (groundTraj, pushTraj, approachTraj, landingTraj, takeoffTraj),
// timeAtS and sAt use integers, + - * /, Math.round / floor and Math.sqrt only. No Math.sin / cos / atan2 / hypot / exp /
// pow (tools/sim/test_traj.mjs wraps them and counts calls). evalTraj is DISPLAY evaluation and may use trigonometry.
//
// Reference point: s is the NOSE-GEAR station along the path (the taxi-graph centreline; the stand stop node is the
// nose-wheel stop, CLAUDE.md "Conventions"). The main gear follows the same path one wheelbase behind (forward) or ahead
// (push-back), and the heading is the chord from the main gear to the nose gear ("chord model": both gears on the
// filleted centreline). Air and runway trajectories use the runway axis: s = distance from the physical runway end of
// that landing / take-off direction (negative on the approach).

import { pointAt } from './path.js';
import { PERF } from './perf.js';
import { hdgVec, vecHdg, groundY } from '../geo.js';

export const TRAJ = {
  glideDeg: 3, tanGlide: 0.052407779283041196,      // AIP (mirror) PAPI 3 deg (aip_facts.ends.*.papi.angle_deg); tan 3 deg as a literal
  approachCm: 1200000,                              // straight-in from 12 km before the threshold (design §4.4) [inf]
  flareFromCm: 1200,                                // flare from 12 m (sfo3d attitude rule :3135) [inf]
  tdSinkCms: 100,                                   // touchdown sink 1 m/s (design §4.4) [inf]
  climbDeg: 7, tanClimb: 0.1227845609029046, climbToCm: 91440,   // gamma 7 deg to 3,000 ft (design §4.4) [inf]
  fadeBeyondEndCm: 1500000,                         // the climb-out fades 15 km beyond the far runway end (design §4.4) [inf]
  rotateDegS: 3, rotatePitchDeg: 8,                 // rotate 3 deg/s to 8 deg (sfo3d attitude :3138) [inf]
  rotMaxMs: 50000,                                  // AIP (mirror) AD 2.20 2.1.4.2: vacate within 50 s after touchdown
  rolloutDecCms2: 50,                                // roll-out before braking: idle reverse + drag 0.5 m/s^2 (inf)
  src: 'inf', basis: 'design.md §4.2, §4.4; sfo3d@e3218d6 js/live/traffic.js attitude :3129-3154 (pitch, flare, gear / flap rules)',
};

// ------------------------------------------------------------------------------------------ runway geometry (integers)
let RWY = null;
/** runway-end geometry in integer cm (baked into data/sha_routes.json `runwayEnds` by tools/sim/build_routes.mjs) */
export function runwayGeom(airport) {
  const out = {};
  const ext = airport.extent && airport.extent.ring;
  for (const r of airport.runways) {
    const f = r.aip_facts || {};
    const E = r.ends;
    for (let i = 0; i < 2; i++) {
      const e = E[i], o = E[1 - i]; const fe = (f.ends || {})[e.id] || {};
      const p = [Math.round(e.end.xz[0] * 100), Math.round(e.end.xz[1] * 100)], q = [Math.round(o.end.xz[0] * 100), Math.round(o.end.xz[1] * 100)];
      const dx = q[0] - p[0], dz = q[1] - p[1], len = Math.sqrt(dx * dx + dz * dz); const h = [dx / len, dz / len];
      const along = (xz) => Math.round((xz[0] * 100 - p[0]) * h[0] + (xz[1] * 100 - p[1]) * h[1]);
      const thrS = e.dthr ? along(e.dthr.xz) : 0;
      const papiIn = fe.papi && fe.papi.inward_of_dthr_m != null ? Math.round(fe.papi.inward_of_dthr_m * 100) : 30000;
      const D = fe.declared_m || {};
      const inter = {}; for (const it of D.intersection || []) inter[it.from_twy] = { toraCm: Math.round(it.TORA * 100), todaCm: Math.round(it.TODA * 100), asdaCm: Math.round(it.ASDA * 100) };
      // the runway profile as [s, y] from this end (data runways[].profile_y: s from the OSM north end node)
      const s0 = E[0].end.s_m; const prof = ((r.profile_y && r.profile_y.points_s_y) || []).map(([s, y]) => [i === 0 ? Math.round((s - s0) * 100) : Math.round(len - (s - s0) * 100), y]).sort((a, b) => a[0] - b[0]);
      const rec = { id: e.id, runway: r.id, pCm: p, h, hdg: e.heading_true_deg, lenCm: Math.round(len), thrSCm: thrS, aimSCm: thrS + papiIn,
        toraCm: D.TORA != null ? Math.round(D.TORA * 100) : null, todaCm: D.TODA != null ? Math.round(D.TODA * 100) : null,
        asdaCm: D.ASDA != null ? Math.round(D.ASDA * 100) : null, ldaCm: D.LDA != null ? Math.round(D.LDA * 100) : null,
        intersections: inter, profile: prof, papiAngleDeg: fe.papi ? fe.papi.angle_deg : 3, src: 'AIP (mirror) + data/sha_airport.json' };
      if (ext) { rec.extentBeforeThrCm = rayToRing(ext, p, h, thrS, -1); rec.extentBeyondEndCm = rayToRing(ext, p, h, Math.round(len), 1); }
      out[e.id] = rec;
    }
  }
  return out;
}
function rayToRing(ring, p, h, s0, dir) {   // distance from s0 along +-h to the extent ring (cm), 10 m steps
  const inR = (x, z) => { let c = false; for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) { const a = ring[i], b = ring[j]; if ((a[1] > z) !== (b[1] > z) && x < (b[0] - a[0]) * (z - a[1]) / (b[1] - a[1]) + a[0]) c = !c; } return c; };
  for (let d = 0; d < 3000000; d += 1000) { const s = s0 + dir * d; const x = (p[0] + h[0] * s) / 100, z = (p[1] + h[1] * s) / 100; if (!inR(x, z)) return d; }
  return null;
}
/** set the runway geometry used when a call does not pass opts.rwy: a route table (its runwayEnds) or runwayGeom(airport) */
export function initTraj(src) { RWY = src && src.runwayEnds ? src.runwayEnds : src; return RWY; }
const rwyOf = (end, opts) => { const R = (opts && opts.rwy) || RWY; if (!R || !R[end]) throw new Error('traj: no runway geometry for ' + end + ' (initTraj)'); return R[end]; };

// ------------------------------------------------------------------------------------------ integer kinematics
export function isqrt(n) { if (!(n > 0)) return 0; let r = Math.floor(Math.sqrt(n)); while (r * r > n) r--; while ((r + 1) * (r + 1) <= n) r++; return r; }
const durMs = (d, v0, v1) => (d <= 0 ? 0 : Math.round(2000 * d / (v0 + v1)));
function seg(t0, s0, s1, v0, v1, kind) {
  const T = durMs(s1 - s0, v0, v1);
  return { t0, t1: t0 + T, s0Cm: s0, s1Cm: s1, v0Cms: v0, v1Cms: v1, aCms2: T > 0 ? Math.round((v1 - v0) * 1000 / T) : 0, kind };
}
/**
 * Speed profile over [s0, s1] with piecewise caps; forward-backward pass in v^2 (integers), then constant-acceleration
 * segments (accelerate / cruise / brake per cap interval).
 * caps: [{a, b, c}] sorted, contiguous; returns [{s0, s1, v0, v1}] and warnings.
 */
function speedProfile(s0, s1, v0, v1, caps, aAcc, aDec) {
  const X = [s0], C = [];
  for (const k of caps) { if (k.b <= s0 || k.a >= s1) continue; const b = Math.min(k.b, s1); if (b > X[X.length - 1]) { X.push(b); C.push(k.c); } }
  if (X[X.length - 1] < s1) { X.push(s1); C.push(C.length ? C[C.length - 1] : 1e6); }
  const n = X.length - 1;
  // boundary speed limits (integers): the start and end speeds, else the lower of the two adjacent caps
  const W = new Array(n + 1); W[0] = v0; W[n] = v1; for (let k = 1; k < n; k++) W[k] = Math.min(C[k - 1], C[k]);
  // forward / backward passes on INTEGER speeds: v[k]^2 <= v[k-1]^2 + 2 a l holds exactly, so every leg is feasible
  const F = new Array(n + 1); F[0] = W[0];
  for (let k = 1; k <= n; k++) F[k] = Math.min(W[k], isqrt(F[k - 1] * F[k - 1] + 2 * aAcc * (X[k] - X[k - 1])));
  const B = new Array(n + 1); B[n] = Math.min(F[n], W[n]);
  for (let k = n - 1; k >= 0; k--) B[k] = Math.min(F[k], isqrt(B[k + 1] * B[k + 1] + 2 * aDec * (X[k + 1] - X[k])));
  const warn = []; if (B[0] < W[0]) { warn.push('start speed above the braking envelope'); B[0] = W[0]; }
  const out = [];
  // a leg u -> w gets d = ceil((w^2 - u^2) / 2a): its effective acceleration never exceeds the cap; the peak speed of an
  // interval is the largest integer for which both legs fit
  const need = (u, w, a) => (w > u ? Math.ceil((w * w - u * u) / (2 * a)) : 0);
  for (let k = 1; k <= n; k++) {
    const d = X[k] - X[k - 1]; if (d <= 0) continue;
    const va = B[k - 1], vb = B[k], c = C[k - 1];
    const vTop = Math.max(va, vb, Math.min(c, isqrt(Math.floor((va * va * aDec + vb * vb * aAcc + 2 * aAcc * aDec * d) / (aAcc + aDec)))));
    let lo = Math.max(va, vb), hi = vTop;
    const fits = (vm) => need(va, vm, aAcc) + need(vb, vm, aDec) <= d;
    if (fits(lo)) { while (lo < hi) { const m = (lo + hi + 1) >> 1; if (fits(m)) lo = m; else hi = m - 1; } }
    else warn.push('infeasible leg ' + va + ' -> ' + vb + ' over ' + d + ' cm');
    const vm = lo;
    let d1 = need(va, vm, aAcc), d3 = need(vb, vm, aDec); if (d1 + d3 > d) { d1 = va < vb ? d : 0; d3 = d - d1; }
    const d2 = d - d1 - d3; let s = X[k - 1];
    if (d1 > 0) { out.push({ s0: s, s1: s + d1, v0: va, v1: vm }); s += d1; }
    if (d2 > 0) { out.push({ s0: s, s1: s + d2, v0: d1 > 0 ? vm : va, v1: vm }); s += d2; }
    if (d3 > 0) { out.push({ s0: s, s1: s + d3, v0: d1 > 0 || d2 > 0 ? vm : va, v1: vb }); s += d3; }
  }
  return { segs: out, warn };
}
function capsOf(route, path, zones, sMin, sMax) {
  const caps = path.pieces.map(p => ({ a: p.s0Cm, b: p.s0Cm + p.lenCm, c: p.vmaxCms }));
  if (caps.length && caps[caps.length - 1].b < sMax) caps.push({ a: caps[caps.length - 1].b, b: sMax, c: caps[caps.length - 1].c });
  if (!zones || !zones.length) return caps;
  // split at zone boundaries and take the minimum
  const cut = new Set(); for (const k of caps) { cut.add(k.a); cut.add(k.b); } for (const z of zones) { cut.add(z.s0Cm); cut.add(z.s1Cm); }
  const xs = [...cut].filter(x => x >= sMin && x <= sMax).sort((a, b) => a - b); const out = [];
  let j = 0;
  for (let i = 0; i < xs.length - 1; i++) {
    const a = xs[i], b = xs[i + 1]; if (b <= a) continue; const m = a;   // cap at the interval start
    while (j < caps.length - 1 && caps[j].b <= m) j++;
    let c = caps[j] ? caps[j].c : 1e6; for (const z of zones) if (z.s0Cm <= m && m < z.s1Cm) c = Math.min(c, z.vmaxCms);
    out.push({ a, b, c });
  }
  return out;
}

/** highest speed (cm/s) at s = 0 of an arrival route from which the caps ahead can be met with taxi braking (backward pass) */
export function arrivalEntryCms(route, perf, vMax = PERF.vExitCms) {
  const aDec = perf.taxiDecCms2 ?? PERF.taxiDecCms2; const caps = capsOf(route, route.path, route.zones, 0, route.lenCm);
  let v = 0;   // the stop at the stand
  for (let i = caps.length - 1; i >= 0; i--) { const c = caps[i]; v = Math.min(c.c, isqrt(v * v + 2 * aDec * (c.b - c.a))); if (i > 0) v = Math.min(v, caps[i - 1].c); }
  return Math.min(vMax, v);
}
/**
 * Ground trajectory along route.path (taxi) from s = sStart at time t0.
 * opts: {vStart, vEnd, stops: [{sCm, dwellMs} | {sCm, untilMs}], leadinStop (default true: the route's 'leadin' holds),
 *        sStart, sEnd, phase}
 */
export function groundTraj(route, perf, t0, opts = {}) {
  const path = route.path; const sStart = opts.sStart ?? 0, sEnd = opts.sEnd ?? route.lenCm;
  const vStart = opts.vStart ?? (route.kind === 'arr' && sStart === 0 ? arrivalEntryCms(route, perf) : 0), vEnd = opts.vEnd ?? 0;
  const aAcc = perf.taxiAccCms2 ?? PERF.taxiAccCms2, aDec = perf.taxiDecCms2 ?? PERF.taxiDecCms2;
  const stops = [];
  if (opts.leadinStop !== false) for (const h of route.holds || []) if (h.kind === 'leadin' && h.dwellMs) stops.push({ sCm: h.sCm, dwellMs: h.dwellMs, why: 'leadin' });
  for (const s of opts.stops || []) stops.push(s);
  const st = stops.filter(s => s.sCm > sStart && s.sCm < sEnd).sort((a, b) => a.sCm - b.sCm);
  const caps = capsOf(route, path, route.zones, sStart, sEnd);
  const segs = []; const warn = []; let t = t0, s = sStart, v = vStart;
  const legs = st.map(x => ({ ...x })).concat([{ sCm: sEnd, end: true }]);
  for (const lg of legs) {
    const vTo = lg.end ? vEnd : 0;
    if (lg.sCm > s) {
      const P = speedProfile(s, lg.sCm, v, vTo, caps, aAcc, aDec); warn.push(...P.warn);
      for (const q of P.segs) { const g = seg(t, q.s0, q.s1, q.v0, q.v1, 'taxi'); segs.push(g); t = g.t1; }
      s = lg.sCm; v = vTo;
    }
    if (!lg.end) {
      const dw = lg.untilMs != null ? Math.max(0, lg.untilMs - t) : (lg.dwellMs || 0);
      if (dw > 0) { segs.push({ t0: t, t1: t + dw, s0Cm: s, s1Cm: s, v0Cms: 0, v1Cms: 0, aCms2: 0, kind: 'hold', why: lg.why || 'stop' }); t += dw; }
    }
  }
  const tr = { kind: 'ground', role: route.kind, t0, t1: t, segs, route, path, dir: 1, perf: slimPerf(perf), warn, phases: [] };
  // phases: landing roll-out on the exit until the tail is clear of the vacate point; holding at stops; line-up
  const ph = []; const tailBehind = perf.lenCm - perf.noseGearCm;
  if (route.kind === 'arr' && route.vacate && sStart < route.vacate.sCm + tailBehind) { ph.push([t0, 'landing']); const tv = timeAtS(tr, Math.min(sEnd, route.vacate.sCm + tailBehind)); if (tv != null) ph.push([tv, 'taxi']); }
  else ph.push([t0, opts.phase || 'taxi']);
  for (const g of segs) if (g.kind === 'hold') { ph.push([g.t0, 'holding']); ph.push([g.t1, phaseAtS(route, g.s0Cm, tailBehind)]); }
  if (route.kind === 'dep' && route.lineup) { const tl = timeAtS(tr, route.lineup.holdSCm); if (tl != null && tl < t) ph.push([tl, 'lineup']); }
  ph.sort((a, b) => a[0] - b[0]);
  tr.phases = ph;
  tr.marks = marksOf(tr, route, perf);
  return tr;
}
const phaseAtS = (route, s, tail) => (route.kind === 'arr' && route.vacate && s < route.vacate.sCm + tail ? 'landing' : route.kind === 'dep' && route.lineup && s >= route.lineup.holdSCm ? 'lineup' : 'taxi');
function marksOf(tr, route, perf) {
  const m = {}; const tail = perf.lenCm - perf.noseGearCm;
  if (route.kind === 'arr' && route.vacate) { const sv = route.vacate.sCm + tail; m.vacateTailMs = sv <= tr.segs[tr.segs.length - 1].s1Cm ? timeAtS(tr, sv) : null; }
  if (route.kind === 'dep' && route.lineup) { m.lineupHoldMs = timeAtS(tr, route.lineup.holdSCm); m.lineupMs = tr.t1; }
  for (const c of route.crossings || []) (m.crossings || (m.crossings = [])).push({ runway: c.runway, node: c.node, inMs: timeAtS(tr, c.sInCm), outTailMs: timeAtS(tr, Math.min(c.sOutCm + tail, tr.segs[tr.segs.length - 1].s1Cm)) });
  return m;
}
const slimPerf = (p) => ({ icao: p.icao, typeKey: p.typeKey, wheelbaseCm: p.wheelbaseCm, noseGearCm: p.noseGearCm, lenCm: p.lenCm, spanCm: p.spanCm, wide: p.wide, vlofCms: p.vlofCms, vappCms: p.vappCms });

/** Push-back along route.push.path (tail first), then the start-up hold at the push end. */
export function pushTraj(route, perf, t0, opts = {}) {
  const P = route.push; const v = opts.pushCms ?? PERF.pushCms, a = opts.pushAccCms2 ?? PERF.pushAccCms2;
  const prof = speedProfile(0, P.lenCm, 0, 0, [{ a: 0, b: P.lenCm, c: v }], a, a);
  const segs = []; let t = t0;
  for (const q of prof.segs) { const g = seg(t, q.s0, q.s1, q.v0, q.v1, 'push'); segs.push(g); t = g.t1; }
  const tPushEnd = t;
  const su = opts.startupMs ?? PERF.startupMs;
  if (su > 0) { segs.push({ t0: t, t1: t + su, s0Cm: P.lenCm, s1Cm: P.lenCm, v0Cms: 0, v1Cms: 0, aCms2: 0, kind: 'hold', why: 'start-up' }); t += su; }
  return { kind: 'push', role: 'dep', t0, t1: t, segs, route, path: P.path, dir: -1, perf: slimPerf(perf), phases: [[t0, 'pushback'], [tPushEnd, 'holding']], marks: { pushEndMs: tPushEnd }, warn: prof.warn };
}

// ------------------------------------------------------------------------------------------ air and runway
/** distance from the GP intercept (aim point) to touchdown: the flare from 12 m with a 1 m/s touchdown sink (cm, integer) */
export function flareOverrunCm(vappCms) {
  const uF = 2 * TRAJ.flareFromCm / (TRAJ.tanGlide + TRAJ.tdSinkCms / vappCms);   // flare length (cm)
  return Math.round(uF - TRAJ.flareFromCm / TRAJ.tanGlide);
}
/** where the WHEEL path meets the runway (cm from the runway end): the PAPI 3 deg path is the pilot's eye path through the
 *  PAPI abeam point; the main-gear wheels fly eyeToWheel lower, so their path meets the ground that much earlier */
export function wheelAimSCm(end, perf, opts = {}) { const R = rwyOf(end, opts); return R.aimSCm - Math.round((perf.eyeToWheelCm || 0) / TRAJ.tanGlide); }
/** nominal touchdown station (cm from the runway end): wheel-path intercept + flare float (+ opts.tdOffsetCm, the caller's
 *  seeded +-60 m). Nominal touchdown -9 .. +69 m from the PAPI abeam point over the types (test_traj INFO; design §4.2 said +-60). */
export function touchdownSCm(end, perf, opts = {}) { return wheelAimSCm(end, perf, opts) + flareOverrunCm(perf.vappCms) + (opts.tdOffsetCm || 0); }
/**
 * Straight-in approach on the 3 deg glide path from 12 km before the threshold to touchdown at tTd (ms).
 * opts: {tdOffsetCm (seeded +-60 m by the caller), rwy}
 */
export function approachTraj(end, perf, tTd, opts = {}) {
  const R = rwyOf(end, opts); const v = perf.vappCms;
  const sTd = touchdownSCm(end, perf, opts), sA = R.thrSCm - (opts.approachCm ?? TRAJ.approachCm);
  const sWi = wheelAimSCm(end, perf, opts); const sFl = sWi - Math.round(TRAJ.flareFromCm / TRAJ.tanGlide);
  const tA = tTd - Math.round(1000 * (sTd - sA) / v), tFl = tTd - Math.round(1000 * (sTd - sFl) / v);
  const segs = [{ t0: tA, t1: tFl, s0Cm: sA, s1Cm: sFl, v0Cms: v, v1Cms: v, aCms2: 0, kind: 'air' }, { t0: tFl, t1: tTd, s0Cm: sFl, s1Cm: sTd, v0Cms: v, v1Cms: v, aCms2: 0, kind: 'flare' }];
  const tFinal = tTd - Math.round(1000 * (sTd - (R.thrSCm - 800000)) / v);
  const tThr = tTd - Math.round(1000 * (sTd - R.thrSCm) / v);
  const marks = { thresholdMs: tThr, touchdownMs: tTd, tdSCm: sTd, flareMs: tFl };
  if (R.extentBeforeThrCm != null) marks.extentMs = tTd - Math.round(1000 * (sTd - (R.thrSCm - R.extentBeforeThrCm)) / v);
  marks.wheelTchCm = Math.round((sWi - R.thrSCm) * TRAJ.tanGlide);
  return { kind: 'approach', role: 'arr', end, t0: tA, t1: tTd, segs, rwy: R, perf: slimPerf(perf), dir: 1, phases: [[tA, 'approach'], [tFinal, 'final']], marks, flare: { sFl, sTd, sWi } };
}
/**
 * Landing roll from touchdown to the arrival route's start (route.exit.startRwySCm): brake at aDec to vExit, then roll at
 * vExit. Returns null when the exit is too close for the type (the exit model never picks such an exit).
 */
export function landingTraj(end, perf, tTd, opts = {}) {
  const R = rwyOf(end, opts); const sTd = opts.tdSCm ?? touchdownSCm(end, perf, opts);
  const sTo = opts.toSCm ?? (opts.route ? opts.route.exit.startRwySCm : null); if (sTo == null) throw new Error('landingTraj: toSCm or route');
  const v0 = opts.vTdCms ?? perf.vappCms, a2 = perf.aDecCms2, a1 = opts.rolloutDecCms2 ?? TRAJ.rolloutDecCms2;
  const v1 = opts.vExitCms ?? (opts.route ? arrivalEntryCms(opts.route, perf) : PERF.vExitCms);   // the turn-off speed the exit allows
  const d = sTo - sTd; const need = (v0 * v0 - v1 * v1) / (2 * a2);
  if (need > d) return null;
  // two phases [inf]: roll-out at a1 (idle reverse + drag) down to vb, then braking at the type's a_dec to vExit exactly at
  // the exit; an exit beyond the a1-only stopping point: a1 to vExit, then roll at vExit
  let vb2 = Math.floor((a2 * v0 * v0 - a1 * v1 * v1 - 2 * a1 * a2 * d) / (a2 - a1));
  const segs = []; let t = tTd, s = sTd;
  if (vb2 > v0 * v0) vb2 = v0 * v0;
  if (vb2 >= v1 * v1) {
    const vb = isqrt(vb2); const d1 = Math.round((v0 * v0 - vb2) / (2 * a1));
    if (d1 > 0) { const g = seg(t, s, s + d1, v0, vb, 'roll'); segs.push(g); t = g.t1; s += d1; }
    const g2 = seg(t, s, sTo, d1 > 0 ? vb : v0, v1, 'roll'); segs.push(g2);
  } else {
    const d1 = Math.round((v0 * v0 - v1 * v1) / (2 * a1)); const g = seg(t, s, s + d1, v0, v1, 'roll'); segs.push(g);
    if (sTo > s + d1) segs.push(seg(g.t1, s + d1, sTo, v1, v1, 'roll'));
  }
  const t1 = segs[segs.length - 1].t1;
  return { kind: 'landing', role: 'arr', end, t0: tTd, t1, segs, rwy: R, perf: slimPerf(perf), dir: 1, phases: [[tTd, 'landing']], marks: { touchdownMs: tTd, exitStartMs: t1, vExitCms: v1 } };
}
/** Take-off from the line-up point (entry = route.lineup or {rwySCm}) at tRoll: roll at aTo to Vlof, then climb to the fade. */
export function takeoffTraj(end, entry, perf, tRoll, opts = {}) {
  const R = rwyOf(end, opts); const s0 = entry.rwySCm ?? entry.sCm ?? 0; const a = perf.aToCms2, vl = perf.vlofCms;
  const dRoll = Math.round(vl * vl / (2 * a));
  const g1 = seg(tRoll, s0, s0 + dRoll, 0, vl, 'roll');
  const va = PERF.vClimbCms, ac = PERF.climbAccCms2;
  const dAcc = Math.round((va * va - vl * vl) / (2 * ac));
  const sFade = R.lenCm + (opts.fadeBeyondEndCm ?? TRAJ.fadeBeyondEndCm);
  const sLof = s0 + dRoll; const segs = [g1];
  if (sLof + dAcc < sFade) { const g2 = seg(g1.t1, sLof, sLof + dAcc, vl, va, 'climb'); segs.push(g2); segs.push(seg(g2.t1, sLof + dAcc, sFade, va, va, 'climb')); }
  else segs.push(seg(g1.t1, sLof, sFade, vl, isqrt(vl * vl + 2 * ac * (sFade - sLof)), 'climb'));
  const tLof = g1.t1;
  const marks = { rollMs: tRoll, liftoffMs: tLof, liftoffSCm: sLof, rollCm: dRoll, fadeMs: segs[segs.length - 1].t1 };
  const tr = { kind: 'takeoff', role: 'dep', end, t0: tRoll, t1: segs[segs.length - 1].t1, segs, rwy: R, perf: slimPerf(perf), dir: 1, phases: [[tRoll, 'takeoff'], [tLof, 'departure']], marks };
  marks.farEndMs = timeAtS(tr, R.lenCm);
  if (R.extentBeyondEndCm != null) marks.extentMs = timeAtS(tr, R.lenCm + R.extentBeyondEndCm);
  const toraLeft = (entry.toraLeftCm != null) ? entry.toraLeftCm : (R.toraCm != null ? R.toraCm - s0 : null);
  marks.toraLeftCm = toraLeft; marks.rollOk = toraLeft == null ? null : dRoll <= toraLeft - 40000;
  return tr;
}

// ------------------------------------------------------------------------------------------ time <-> position (integers)
function segIdxT(tr, t) { const S = tr.segs; let lo = 0, hi = S.length - 1; if (t <= S[0].t0) return 0; while (lo < hi) { const m = (lo + hi + 1) >> 1; if (S[m].t0 <= t) lo = m; else hi = m - 1; } return lo; }
/** s (cm, integer) at time t (ms) */
export function sAt(tr, t) {
  const g = tr.segs[segIdxT(tr, t)]; if (t <= g.t0) return g.s0Cm; if (t >= g.t1) return g.s1Cm;
  const T = g.t1 - g.t0, tau = t - g.t0, b = g.v0Cms / 1000, A = (g.s1Cm - g.s0Cm - b * T) / (T * T);
  return Math.round(g.s0Cm + b * tau + A * tau * tau);
}
/** first time (ms, integer) at which s reaches sCm, or null if it never does */
export function timeAtS(tr, sCm) {
  for (const g of tr.segs) {
    if (g.s1Cm < sCm) continue; if (g.s0Cm >= sCm) return g.t0;
    const T = g.t1 - g.t0; if (T <= 0) return g.t0;
    const b = g.v0Cms / 1000, A = (g.s1Cm - g.s0Cm - b * T) / (T * T), d = sCm - g.s0Cm;
    const disc = b * b + 4 * A * d; const tau = 2 * d / (b + Math.sqrt(disc > 0 ? disc : 0));
    return g.t0 + Math.round(Math.min(T, Math.max(0, tau)));
  }
  return null;
}
/** speed (cm/s) at t, from the segment quadratic */
export function vAt(tr, t) { const g = tr.segs[segIdxT(tr, t)]; const T = g.t1 - g.t0; if (T <= 0) return g.v1Cms; const tau = Math.min(T, Math.max(0, t - g.t0)); const b = g.v0Cms / 1000, A = (g.s1Cm - g.s0Cm - b * T) / (T * T); return (b + 2 * A * tau) * 1000; }
export const phaseAt = (tr, t) => { let p = tr.phases.length ? tr.phases[0][1] : null; for (const [tt, q] of tr.phases) if (tt <= t) p = q; return p; };

// ------------------------------------------------------------------------------------------ exit model and ROT (design §4.2)
/**
 * Exit choice (design §4.2): exits on the stand's side of the landing runway; the first (rank 1) the stopping distance
 * reaches, else the second; when both are reachable, rank 1 if u < 0.7 (u: the caller's seeded draw in [0, 1)), but a
 * second-exit pick whose predicted ROT exceeds rotMaxMs (50 s, AIP (mirror) AD 2.20 2.1.4.2) while the first exit meets it
 * goes to the first exit [inf]. Falls back to the later named exits of the side, then to any reachable exit.
 * opts: {tdOffsetCm | tdSCm, spanCm (route class; default perf.spanCm), rotMaxMs}
 * Returns {exit, why, needSCm, side, rotMs, route}. Commit path: integer kinematics only.
 */
export function chooseExit(router, end, stand, perf, u, opts = {}) {
  const R = rwyOf(end, opts); const rw = R.runway; const side = router.standSide(stand, rw);
  const sTd = opts.tdSCm ?? touchdownSCm(end, perf, opts);
  const need = sTd + Math.round((perf.vappCms * perf.vappCms - PERF.vExitCms * PERF.vExitCms) / (2 * perf.aDecCms2));
  const all = router.exits(end, true); const same = all.filter(e => e.side === side);
  const rotMax = opts.rotMaxMs ?? TRAJ.rotMaxMs;
  const span = opts.spanCm ?? perf.spanCm;
  // reachable: braking at a_dec from touchdown reaches the turn-off speed this exit's path allows before the route start
  const reach = (e) => { if (e.startCm < need) return false; const rt = router.arrival(e.id, stand, { spanCm: span }); if (!rt) return false; const v = arrivalEntryCms(rt, perf); return e.startCm >= sTd + (perf.vappCms * perf.vappCms - v * v) / (2 * perf.aDecCms2); };
  const rot = (e) => { const rt = router.arrival(e.id, stand, { spanCm: span }); if (!rt) return { ms: null, rt: null }; const ld = landingTraj(end, perf, 0, { tdSCm: sTd, route: rt, rwy: opts.rwy }); if (!ld) return { ms: null, rt }; const g = groundTraj(rt, perf, ld.t1, { vStart: ld.marks.vExitCms, leadinStop: false }); return { ms: rotMs(ld, g), rt }; };
  const r1 = same.find(e => e.rank === 1), r2 = same.find(e => e.rank === 2);
  let pick = null, why = '', q = null;
  if (r1 && reach(r1) && r2 && reach(r2)) {
    if (u < 0.7) { pick = r1; why = 'both reachable: first (70 %)'; }
    else { const q2 = rot(r2); if (q2.ms != null && q2.ms > rotMax) { const q1 = rot(r1); if (q1.ms != null && q1.ms <= rotMax) { pick = r1; q = q1; why = 'both reachable: second drawn, ROT > 50 s there: first'; } } if (!pick) { pick = r2; q = q2; why = 'both reachable: second (30 %)'; } }
  } else if (r1 && reach(r1)) { pick = r1; why = 'first'; }
  else if (r2 && reach(r2)) { pick = r2; why = 'second (first not reachable)'; }
  else { pick = same.find(reach) || all.find(reach) || same[same.length - 1] || null; why = pick && pick.kind === 'end' ? 'far-end connector (no rapid exit of the side reachable)' : 'fallback (a later rapid exit)'; }
  if (pick && !q) q = rot(pick);
  return { exit: pick, why, needSCm: need, side, rotMs: q ? q.ms : null, route: q ? q.rt : null };
}
/** runway occupancy time from touchdown to the tail clear of the vacate point (ms), from a landing and a ground traj */
export function rotMs(landing, ground) { return ground && ground.marks && ground.marks.vacateTailMs != null ? ground.marks.vacateTailMs - landing.t0 : null; }

// ------------------------------------------------------------------------------------------ DISPLAY evaluation
const D2R = Math.PI / 180, KT = 0.514444;
const _a = {}, _b = {};
function profY(R, s) { const P = R.profile; if (!P || !P.length) return groundY(0, 0); if (s <= P[0][0]) return P[0][1]; for (let i = 1; i < P.length; i++) if (s <= P[i][0]) { const k = (s - P[i - 1][0]) / (P[i][0] - P[i - 1][0]); return P[i - 1][1] + k * (P[i][1] - P[i - 1][1]); } return P[P.length - 1][1]; }
/** height (m) above the runway of an air / runway trajectory at station s (cm) */
function heightAt(tr, s) {
  if (tr.kind === 'approach') {
    const { sFl, sTd } = tr.flare;
    if (s <= sFl) return (tr.flare.sWi - s) * TRAJ.tanGlide / 100;
    const uF = sTd - sFl; const u = sTd - s; if (u <= 0) return 0;
    const b = 2 * TRAJ.flareFromCm / uF - TRAJ.tanGlide, a = (TRAJ.tanGlide - b) / (2 * uF);   // h = a u^2 + b u, h(uF) = 12 m, h'(uF) = tan 3
    return (a * u * u + b * u) / 100;
  }
  if (tr.kind === 'takeoff') { const sl = tr.marks.liftoffSCm; if (s <= sl) return 0; return Math.min(TRAJ.climbToCm, (s - sl) * TRAJ.tanClimb) / 100; }
  return 0;
}
/**
 * DISPLAY: pose at time t (floats, metres, degrees true). x, z: the nose-gear point; main: [x, z] main-gear centre;
 * tip: [x, z] nose tip; y: gear-contact height (world y); gs, vs: m/s; pitch, roll: degrees.
 */
export function evalTraj(tr, t, out = {}) {
  const tt = Math.max(tr.t0, Math.min(tr.t1, t));
  const s = sAtFloat(tr, tt), v = vAt(tr, tt) / 100;
  const P = tr.perf; const wb = P.wheelbaseCm, ng = P.noseGearCm;
  out.phase = phaseAt(tr, tt); out.t = tt;
  if (tr.kind === 'ground' || tr.kind === 'push') {
    const n = pointAt(tr.path, s, _a); const m = pointAt(tr.path, s - tr.dir * wb, _b);
    const dx = n.x - m.x, dz = n.z - m.z;
    out.x = n.x / 100; out.z = n.z / 100; out.y = groundY(out.x, out.z);
    out.hdg = vecHdg(dx, dz);
    const f = hdgVec(out.hdg);
    out.main = [m.x / 100, m.z / 100]; out.tip = [out.x + f[0] * ng / 100, out.z + f[1] * ng / 100];
    out.gs = Math.abs(v); out.vs = 0; out.ground = true; out.gear = 1; out.pitch = 0; out.roll = 0;
    out.flaps = tr.role === 'dep' && tr.kind === 'ground' ? 0.35 : out.phase === 'landing' ? 1 : 0;
    out.spoilers = out.phase === 'landing' && out.gs > 40 * KT ? 1 : 0;
    return out;
  }
  // runway axis
  const R = tr.rwy; const h = R.h;
  const x = (R.pCm[0] + h[0] * s) / 100, z = (R.pCm[1] + h[1] * s) / 100;
  const agl = heightAt(tr, s);
  out.x = x; out.z = z; out.y = profY(R, Math.max(0, Math.min(R.lenCm, s))) + agl; out.hdg = R.hdg;
  out.main = [x - h[0] * wb / 100, z - h[1] * wb / 100]; out.tip = [x + h[0] * ng / 100, z + h[1] * ng / 100];
  out.gs = v; out.ground = agl <= 0.001; out.roll = 0; out.spoilers = 0;
  const ds = 50; const vs = (heightAt(tr, s + ds) - heightAt(tr, s)) / (ds / 100) * v; out.vs = vs;
  const gam = Math.atan2(vs, Math.max(v, 40)) / D2R;
  if (tr.kind === 'approach') {
    out.pitch = gam + (v < 75 ? 4.5 : 2.5); if (agl < 12) out.pitch = Math.max(out.pitch, 4.5);
    out.gear = agl < 600 ? 1 : 0; out.flaps = Math.min(1, Math.max(0, (235 - v / KT) / 80)) * (agl < 3000 ? 1 : 0);
  } else if (tr.kind === 'landing') {
    const since = (tt - tr.t0) / 1000; out.pitch = Math.max(0, 4.5 - 1.5 * since); out.gear = 1; out.flaps = 1; out.spoilers = v > 40 * KT && since > 0.5 ? 1 : 0; out.ground = true;
  } else {   // takeoff
    const tl = tr.marks.liftoffMs; const rotS = TRAJ.rotatePitchDeg / TRAJ.rotateDegS;
    if (tt < tl) out.pitch = Math.max(0, TRAJ.rotatePitchDeg - (tl - tt) / 1000 * TRAJ.rotateDegS) * ((tl - tt) / 1000 < rotS ? 1 : 0);
    else out.pitch = Math.min(17, Math.max(8, gam + 5));
    out.gear = tt < tl + 4000 || agl < 1 ? 1 : 0; out.flaps = v / KT < 205 && agl < 1200 ? 0.35 : 0; out.ground = tt < tl;
  }
  return out;
}
function sAtFloat(tr, t) { const g = tr.segs[segIdxT(tr, t)]; if (t <= g.t0) return g.s0Cm; if (t >= g.t1) return g.s1Cm; const T = g.t1 - g.t0, tau = t - g.t0, b = g.v0Cms / 1000, A = (g.s1Cm - g.s0Cm - b * T) / (T * T); return g.s0Cm + b * tau + A * tau * tau; }
