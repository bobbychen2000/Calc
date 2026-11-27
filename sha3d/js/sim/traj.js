// sha3d Phase 3 (P3-B): time-parameterised trajectories (new; the physical priors are cited in js/sim/perf.js).
// Pure ES module (node + browser). A Traj is a list of constant-acceleration segments along one path:
//   Traj = { kind, t0, t1, segs: [{t0, t1, s0Cm, s1Cm, v0Cms, v1Cms, aCms2, kind}], route, phases: [[t, phase]], ... }
// Segment boundaries are integers (ms, cm, cm/s). Inside a segment the position is the quadratic through (t0, s0) and
// (t1, s1) with the start speed v0 (so every segment ends exactly at its integer s1).
//
// Commit path (design §1.4): building a trajectory (groundTraj, pushTraj, approachTraj, landingTraj, takeoffTraj),
// timeAtS and sAt use integers, + - * /, Math.round / floor and Math.sqrt only. No Math.sin / cos / atan2 / hypot / exp /
// pow (tools/sim/test_traj.mjs wraps them and counts calls). evalTraj is DISPLAY evaluation and may use trigonometry.
// Fix round 3 (docs/phase3/movement.md "Verification fixes, round 3"): groundTraj also caps the speed where the displayed
// main gear would exceed a_lat / the yaw guard (mainGearZones), so the gear follower is on the commit path and deterministic;
// evalTraj's x / z is the reference point (the nose-gear station on the centreline, moving at gs), pose.nose / pose.main the
// displayed gears with their own speeds noseGs / mainGs; every speed maximum of a taxi profile is held >= 1 s (holdPeaks).
//
// Reference point: s is the NOSE-GEAR station along the path (the taxi-graph centreline; the stand stop node is the
// nose-wheel stop, CLAUDE.md "Conventions"). The main gear follows the same path one wheelbase behind (forward) or ahead
// (push-back), and the heading is the chord from the main gear to the nose gear ("chord model": both gears on the
// filleted centreline). Air and runway trajectories use the runway axis: s = distance from the physical runway end of
// that landing / take-off direction (negative on the approach).

import { pointAt, pieceAt, pointAtDet, angleDet, RAD2DEG } from './path.js';
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
  peakHoldMs: 1000,                                  // fix round 3 (V3-2): a taxi speed maximum holds >= 1 s (no 1 s step beyond its end speeds x 1 s + 0.1 m, design §5) [inf]
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
/**
 * One constant-acceleration segment from the ACTUAL start speed v0 toward the target end speed v1t over [s0, s1] (fix round
 * 1, V7). T = ceil(2 d / (v0 + v1t)) ms, so the quadratic through (t0, s0) and (t1, s1) with start speed v0 ends at
 * vEnd <= v1t; v1Cms = floor(vEnd) (>= 0), so |vEnd - v1Cms| < 1 cm/s and the next segment starts at v1Cms (speed
 * continuous to 1 cm/s); aCms2 is that quadratic's acceleration, rounded. An accelerating target is lowered so that
 * the leg never exceeds aCapCms2 from the actual v0. Integers in, integers out; + - * / sqrt only.
 */
function legSeg(t0, s0, s1, v0, v1t, kind, aCapCms2 = 0, dCapCms2 = 0) {
  const d = s1 - s0; if (d <= 0) return null;
  if (aCapCms2 > 0 && v1t > v0) v1t = Math.min(v1t, isqrt(v0 * v0 + 2 * aCapCms2 * d));
  const sum = v0 + v1t > 0 ? v0 + v1t : 1; const Tx = 2000 * d / sum;
  // T: the whole ms within 3 of the exact duration whose quadratic ends at the target, within the caps + 2 % + 1 cm/s^2
  // (the 1 ms quantization of short legs: one ms moves the end speed by (v0 + v1) / T); else ceil
  let best = null; const aLim = aCapCms2 ? aCapCms2 * 1.02 + 1 : 0, dLim = dCapCms2 ? dCapCms2 * 1.02 + 1 : 0;
  // ranking: exactly the target; else the highest end speed <= the target; else at most 2 cm/s above it (within the
  // speed tolerance of the caps), the lowest first
  // fix round 3: when no duration meets both, keep the acceleration caps (the end speed then misses the target by up to one
  // ms of quantization, (v0 + v1) / T; the next leg starts from it)
  const rank = (c) => (!c.ok ? (c.capOk ? 5e8 - Math.abs(c.v1 - v1t) : 0) : c.v1 === v1t ? 4e9 : c.v1 < v1t ? 2e9 + c.v1 : 1e9 - c.v1);
  const T0 = Math.max(1, Math.ceil(Tx));
  for (const T of [T0, T0 - 1, T0 + 1, T0 - 2, T0 + 2, T0 - 3, T0 + 3]) {
    if (T < 1) continue;
    const vEnd = 2000 * d / T - v0; if (vEnd < -0.5) continue; const v1 = Math.max(0, Math.floor(vEnd + 1e-9)); const a = (v1 * v1 - v0 * v0) / (2 * d);
    const capOk = (!aLim || a <= aLim) && (!dLim || -a <= dLim);
    const c = { T, vEnd, v1, capOk, ok: v1 <= v1t + 2 && capOk };
    if (!best || rank(c) > rank(best)) best = c;
  }
  const { T, vEnd, v1 } = best;
  return { t0, t1: t0 + T, s0Cm: s0, s1Cm: s1, v0Cms: v0, v1Cms: v1, aCms2: Math.round((vEnd - v0) * 1000 / T), kind };
}
const SEG_MAX_MS = 4000, CRUISE_MAX_MS = 10000;   // accelerating / braking legs are cut into <= 4 s segments, cruise legs into
                          // <= 10 s: integrating the frozen integer fields (t0, s0Cm, v0Cms, aCms2) then ends within ~10 cm of s1Cm (V7) [inf]
/** chain planned legs [{s0, s1, v1}] into segments from start speed v; returns {segs, t, v} */
function chainLegs(legs, t, v, kind, aCapCms2, out = [], dCapCms2 = 0) {
  for (let li = 0; li < legs.length; li++) {
    const q = legs[li]; const d = q.s1 - q.s0; if (d <= 0) continue;
    // a rounding residue (<= 0.2 %): keep the speed (an exact cruise); fix round 3: a planned cruise before a braking leg (a
    // held speed maximum, holdPeaks) entered below its speed (an accelerating leg ended lower: its target is capped from the
    // actual start) stays at the actual speed - accelerating there makes a peak without its hold and steepens the braking
    const nx = legs[li + 1]; const plateau = q.v0 === q.v1 && v > 0 && v < q.v1 && nx && nx.v1 < nx.v0;
    const tgt = plateau || (q.v1 > 0 && v > 0 && Math.abs(q.v1 - v) <= Math.max(2, Math.floor(v / 500))) ? v : q.v1;
    const sum = v + tgt; const n = sum > 0 ? Math.ceil(2000 * d / sum / (tgt !== v ? SEG_MAX_MS : CRUISE_MAX_MS)) : 1;
    let s0 = q.s0; const aLeg = (tgt * tgt - v * v) / (2 * d);   // the leg's constant acceleration (cm/s^2, signed)
    for (let k = 1; k <= n; k++) {   // equal-speed-step cuts; each cut distance rounded UP so no cut exceeds aLeg
      const vNow = out.length && k > 1 ? out[out.length - 1].v1Cms : v;
      let s1 = q.s1, vk = tgt;
      if (k < n) { if (tgt === v) s1 = q.s0 + Math.round(d * k / n); else { vk = Math.round(v + (tgt - v) * k / n); s1 = s0 + Math.ceil((vk * vk - vNow * vNow) / (2 * aLeg)); } if (s1 <= s0 || s1 >= q.s1) continue; }
      const g = legSeg(t, s0, s1, vNow, vk, kind, aCapCms2, dCapCms2); if (!g) continue; out.push(g); t = g.t1; s0 = s1;
    }
    v = out.length ? out[out.length - 1].v1Cms : v;
  }
  return { segs: out, t, v };
}
const LEG_MIN_MS = 500;   // planned legs shorter than this are merged into a neighbour (V7) [inf]
/**
 * Merge short legs (their duration would be rounded to whole ms) so that no speed rises above the plan and no leg's
 * acceleration exceeds its neighbours': an accelerating leg joins the next one, a decelerating leg the previous one, a
 * cruise leg the neighbour that turns down from it; a cruise leg in a speed valley (decelerate, cruise, accelerate) is
 * cut at x = d aAcc / (aAcc + aDec) and its two parts join the neighbours with the valley speed lowered to
 * sqrt(v^2 - 2 aDec x) (both parts then stay within the caps). Integers, + - * / and isqrt.
 */
function mergeShortLegs(legs, aAcc, aDec) {
  const L = legs.map(q => ({ ...q }));
  const short = (q) => { const sum = q.v0 + q.v1; return q.s1 > q.s0 && (sum <= 0 || 2000 * (q.s1 - q.s0) / sum < LEG_MIN_MS); };
  for (let guard = 0; guard < 4 * legs.length + 4 && L.length > 1; guard++) {
    let k = -1; for (let i = 0; i < L.length; i++) if (short(L[i]) && !L[i].keep) { k = i; break; }
    if (k < 0) break;
    const q = L[k], pv = L[k - 1], nx = L[k + 1];
    const withNext = () => { L.splice(k, 2, { s0: q.s0, s1: nx.s1, v0: q.v0, v1: nx.v1 }); };
    const withPrev = () => { L.splice(k - 1, 2, { s0: pv.s0, s1: q.s1, v0: pv.v0, v1: q.v1 }); };
    // fix round 2: two legs A, B merge into one constant-acceleration leg without exceeding the plan at their joint only when
    // B accelerates no harder than A (v^2 concave): a short braking leg after a harder one stays apart (it had lifted 6.76 m/s
    // over a 6.54 m/s turn cap)
    const acc = (x) => (x.v1 * x.v1 - x.v0 * x.v0) / (2 * (x.s1 - x.s0));
    const okNext = nx && acc(nx) <= acc(q), okPrev = pv && acc(q) <= acc(pv);
    // neither is safe: the previous leg's own acceleration is carried over the short leg (every speed at or below the plan;
    // the next leg then starts lower, and chainLegs keeps its acceleration within the cap)
    const withPrevLow = () => { const v2 = pv.v0 * pv.v0 + (pv.v1 * pv.v1 - pv.v0 * pv.v0) * (q.s1 - pv.s0) / (pv.s1 - pv.s0); const v1 = Math.min(q.v1, isqrt(Math.floor(v2)));
      L.splice(k - 1, 2, { s0: pv.s0, s1: q.s1, v0: pv.v0, v1 }); if (L[k]) L[k] = { ...L[k], v0: v1 }; };
    if (q.v1 > q.v0) { if (okNext) withNext(); else if (okPrev) withPrev(); else if (pv) withPrevLow(); else q.keep = true; continue; }
    if (q.v1 < q.v0) { if (okPrev) withPrev(); else if (okNext) withNext(); else if (pv) withPrevLow(); else q.keep = true; continue; }
    if (nx && nx.v1 <= q.v1) { withNext(); continue; }      // cruise, then down (or level)
    if (pv && pv.v0 <= q.v0) { withPrev(); continue; }      // up (or level), then cruise
    if (pv && nx) {                                         // a valley: decelerate, short cruise, accelerate
      const d = q.s1 - q.s0, x = Math.floor(d * aAcc / (aAcc + aDec)), vv = isqrt(q.v0 * q.v0 - 2 * aDec * x);
      L.splice(k - 1, 3, { s0: pv.s0, s1: q.s0 + x, v0: pv.v0, v1: vv }, { s0: q.s0 + x, s1: nx.s1, v0: vv, v1: nx.v1 });
      continue;
    }
    q.keep = true;
  }
  return L;
}
/**
 * Fix round 3 (V3-2): every speed maximum of a planned profile is held for at least TRAJ.peakHoldMs (1 s): a triangular peak
 * (accelerate, then brake at once) puts up to 0.3 m more into a 1 s step than its larger end speed x 1 s (design §5
 * kinematics row read with the step's end speeds; the excess is a1 a2 / 2 (a1 + a2) (1 - P^2) for a plateau of P s). The
 * peak is lowered to the largest integer speed vq whose stretch above vq, [r, f], is at least vq x peakHoldMs long: the
 * legs over [r, f] become a cruise at vq (speeds only lowered; the cut legs keep their accelerations: r rounded up, f down).
 * legs: [{s0, s1, v0, v1}] contiguous (cm, cm/s, integers). Integers, + - * / and isqrt only.
 */
function holdPeaks(legs) {
  const L = legs.slice(); const hold = TRAJ.peakHoldMs;
  const vAtS = (q, s) => { if (s <= q.s0) return q.v0; if (s >= q.s1) return q.v1; return Math.sqrt(q.v0 * q.v0 + (q.v1 * q.v1 - q.v0 * q.v0) * (s - q.s0) / (q.s1 - q.s0)); };
  // station where leg q passes speed v (q monotone, v between its ends)
  const sAtV = (q, v) => (q.v1 === q.v0 ? q.s0 : q.s0 + (v * v - q.v0 * q.v0) * (q.s1 - q.s0) / (q.v1 * q.v1 - q.v0 * q.v0));
  for (let guard = 0; guard < 4 * legs.length + 4; guard++) {
    let done = true;
    for (let i = 0; i < L.length; i++) {
      // a maximum: legs i..j at the top speed vp (cruises) or one leg ending at vp; rising into it, falling out of it
      const vp = L[i].v1; if (!(L[i].v1 > L[i].v0) && !(i === 0 ? false : L[i].v0 === vp && L[i - 1].v1 === vp && L[i - 1].v0 < vp)) continue;
      if (L[i].v0 === L[i].v1) continue;   // (the rising leg is the anchor)
      let j = i + 1; while (j < L.length && L[j].v0 === vp && L[j].v1 === vp) j++;
      if (j >= L.length || !(L[j].v1 < L[j].v0) || L[j].v0 !== vp) continue;   // no fall: not a maximum (or the profile end)
      const plat = L[j].s0 - L[i].s1; if (plat * 1000 >= vp * hold) continue;
      // the stretch above vq: back through rising legs from i, forward through falling legs from j
      let ia = i; while (ia > 0 && L[ia - 1].v1 > L[ia - 1].v0 && L[ia - 1].v1 === L[ia].v0) ia--;
      let jb = j; while (jb < L.length - 1 && L[jb + 1].v1 < L[jb + 1].v0 && L[jb + 1].v0 === L[jb].v1) jb++;
      const vMin = Math.max(L[ia].v0, L[jb].v1);
      const span = (vq) => {   // [r, f] where the profile is >= vq
        let r = L[i].s1, f = L[j].s0;
        for (let k = i; k >= ia; k--) { if (L[k].v0 <= vq) { r = sAtV(L[k], vq); break; } r = L[k].s0; }
        for (let k = j; k <= jb; k++) { if (L[k].v1 <= vq) { f = sAtV(L[k], vq); break; } f = L[k].s1; }
        return [r, f];
      };
      let lo = vMin, hi = vp - 1;
      { const [r, f] = span(lo); if ((f - r) * 1000 < lo * hold) hi = lo; }
      while (lo < hi) { const m = (lo + hi + 1) >> 1; const [r, f] = span(m); if ((Math.floor(f) - Math.ceil(r)) * 1000 >= m * hold) lo = m; else hi = m - 1; }
      const vq = lo; const [r0, f0] = span(vq); const r = Math.ceil(r0), f = Math.floor(f0);
      // rebuild: legs before the rising crossing, the cut rising leg, the cruise, the cut falling leg, the rest
      let kr = i; while (kr > ia && L[kr].v0 > vq) kr--; let kf = j; while (kf < jb && L[kf].v1 > vq) kf++;
      const out = L.slice(0, kr);
      if (r > L[kr].s0) out.push({ s0: L[kr].s0, s1: r, v0: L[kr].v0, v1: vq });
      if (f > r) out.push({ s0: Math.max(r, L[kr].s0), s1: Math.min(f, L[kf].s1), v0: vq, v1: vq });
      if (L[kf].s1 > f) out.push({ s0: f, s1: L[kf].s1, v0: vq, v1: L[kf].v1 });
      for (let k = kf + 1; k < L.length; k++) out.push(L[k]);
      if (out.length && out.every((q, k) => q.s1 > q.s0 && (k === 0 || out[k - 1].s1 === q.s0))) { L.length = 0; for (const q of out) L.push(q); done = false; break; }
    }
    if (done) break;
  }
  return L;
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
  // fix round 3: hold every speed maximum >= peakHoldMs, merge the short legs that cuts, until stable (both only lower or merge)
  let Lg = mergeShortLegs(out, aAcc, aDec);
  for (let it = 0; it < 6; it++) { const H = holdPeaks(Lg); if (H.length === Lg.length && H.every((q, k) => q.s0 === Lg[k].s0 && q.s1 === Lg[k].s1 && q.v0 === Lg[k].v0 && q.v1 === Lg[k].v1)) break; Lg = mergeShortLegs(H, aAcc, aDec); }
  return { segs: Lg, warn };
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

/**
 * Turn zones (fix round 2, M1): the speed cap of every arc held until the main gear has left it, [s0, s0 + len + wheelbase]
 * (the body yaws while the main gear is on the arc; with the oversteered display the main gear follows the arc itself).
 * Integers; route.zones (stand stop) appended. Fix round 3 (V3-2): plus mainGearZones (where the displayed main gear cuts
 * inside, its lateral acceleration / yaw would exceed a_lat / the yaw guard at the arc's cap).
 */
function baseTurnZones(route, perf) {
  const wb = perf.wheelbaseCm || 0; const z = (route.zones || []).slice(); if (!wb) return z;
  for (const p of route.path.pieces) if (p.kind === 'arc' && p.vmaxCms < 1e6) z.push({ s0Cm: p.s0Cm, s1Cm: p.s0Cm + p.lenCm + wb, vmaxCms: p.vmaxCms, why: 'turn (main gear)' });
  return z;
}
export function turnZones(route, perf) {
  const z = baseTurnZones(route, perf); if (!(perf.wheelbaseCm > 0) || !route.path) return z;
  // fix round 3 (V3-2): plus the main-gear zones of the displayed gear model (mainGearZones)
  for (const q of mainGearZones(route, perf, z)) z.push(q);
  return z;
}
/** highest speed (cm/s) at s = 0 of an arrival route from which the caps ahead can be met with taxi braking (backward pass) */
export function arrivalEntryCms(route, perf, vMax = PERF.vExitCms) {
  const aDec = perf.taxiDecCms2 ?? PERF.taxiDecCms2; const caps = capsOf(route, route.path, turnZones(route, perf), 0, route.lenCm);
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
  const caps = capsOf(route, path, turnZones(route, perf), sStart, sEnd);
  const segs = []; const warn = []; let t = t0, s = sStart, v = vStart;
  const legs = st.map(x => ({ ...x })).concat([{ sCm: sEnd, end: true }]);
  for (const lg of legs) {
    const vTo = lg.end ? vEnd : 0;
    if (lg.sCm > s) {
      const P = speedProfile(s, lg.sCm, v, vTo, caps, aAcc, aDec); warn.push(...P.warn);
      const c = chainLegs(P.segs, t, v, 'taxi', aAcc, segs, aDec); t = c.t; v = c.v;
      s = lg.sCm; if (!lg.end) v = 0;
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
  t = chainLegs(prof.segs, t, 0, 'push', a, segs, a).t;
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
 * opts: {tdOffsetCm (seeded +-60 m by the caller), rwy, route (the arrival route, carried as Traj.route)}
 * Stations (fix round 1, V9): the glide path, the flare and touchdown are defined for the MAIN GEAR (the wheels touch
 * down at marks.tdSCm); the segments carry the NOSE-GEAR station (main + wheelbase), like every other trajectory, so that
 * the landing roll and the arrival route continue without a jump. Threshold / extent marks: main gear over that point.
 */
export function approachTraj(end, perf, tTd, opts = {}) {
  const R = rwyOf(end, opts); const v = perf.vappCms; const wb = perf.wheelbaseCm || 0;
  const sTd = touchdownSCm(end, perf, opts), sA = R.thrSCm - (opts.approachCm ?? TRAJ.approachCm);
  const sWi = wheelAimSCm(end, perf, opts); const sFl = sWi - Math.round(TRAJ.flareFromCm / TRAJ.tanGlide);
  const tA = tTd - Math.round(1000 * (sTd - sA) / v), tFl = tTd - Math.round(1000 * (sTd - sFl) / v);
  const segs = [{ t0: tA, t1: tFl, s0Cm: sA + wb, s1Cm: sFl + wb, v0Cms: v, v1Cms: v, aCms2: 0, kind: 'air' }, { t0: tFl, t1: tTd, s0Cm: sFl + wb, s1Cm: sTd + wb, v0Cms: v, v1Cms: v, aCms2: 0, kind: 'flare' }];
  const tFinal = tTd - Math.round(1000 * (sTd - (R.thrSCm - 800000)) / v);
  const tThr = tTd - Math.round(1000 * (sTd - R.thrSCm) / v);
  const marks = { thresholdMs: tThr, touchdownMs: tTd, tdSCm: sTd, tdNoseSCm: sTd + wb, flareMs: tFl };
  if (R.extentBeforeThrCm != null) marks.extentMs = tTd - Math.round(1000 * (sTd - (R.thrSCm - R.extentBeforeThrCm)) / v);
  marks.wheelTchCm = Math.round((sWi - R.thrSCm) * TRAJ.tanGlide);
  return { kind: 'approach', role: 'arr', end, t0: tA, t1: tTd, segs, route: opts.route ?? null, rwy: R, perf: slimPerf(perf), dir: 1, phases: [[tA, 'approach'], [tFinal, 'final']], marks, flare: { sFl, sTd, sWi, wb } };
}
/**
 * Landing roll from touchdown to the arrival route's start (route.exit.startRwySCm): brake at aDec to vExit, then roll at
 * vExit. Returns null when the exit is too close for the type (the exit model never picks such an exit).
 */
export function landingTraj(end, perf, tTd, opts = {}) {
  // opts.tdSCm: the MAIN-GEAR touchdown station (approachTraj marks.tdSCm); the roll's s is the nose-gear station (V9)
  const R = rwyOf(end, opts); const sTd = (opts.tdSCm ?? touchdownSCm(end, perf, opts)) + (perf.wheelbaseCm || 0);
  const sTo = opts.toSCm ?? (opts.route ? opts.route.exit.startRwySCm : null); if (sTo == null) throw new Error('landingTraj: toSCm or route');
  const v0 = opts.vTdCms ?? perf.vappCms, a2 = perf.aDecCms2, a1 = opts.rolloutDecCms2 ?? TRAJ.rolloutDecCms2;
  const v1 = opts.vExitCms ?? (opts.route ? arrivalEntryCms(opts.route, perf) : PERF.vExitCms);   // the turn-off speed the exit allows
  const d = sTo - sTd; const need = (v0 * v0 - v1 * v1) / (2 * a2);
  if (need > d) return null;
  // two phases [inf]: roll-out at a1 (idle reverse + drag) down to vb, then braking at the type's a_dec to vExit exactly at
  // the exit; an exit beyond the a1-only stopping point: a1 to vExit, then roll at vExit
  let vb2 = Math.floor((a2 * v0 * v0 - a1 * v1 * v1 - 2 * a1 * a2 * d) / (a2 - a1));
  const segs = []; const s = sTd; const legs = [];
  if (vb2 > v0 * v0) vb2 = v0 * v0;
  if (vb2 >= v1 * v1) {
    const vb = isqrt(vb2); const d1 = Math.round((v0 * v0 - vb2) / (2 * a1));
    if (d1 > 0) legs.push({ s0: s, s1: s + d1, v0, v1: vb });
    legs.push({ s0: s + Math.max(0, d1), s1: sTo, v0: d1 > 0 ? vb : v0, v1 });
  } else {
    const d1 = Math.round((v0 * v0 - v1 * v1) / (2 * a1)); legs.push({ s0: s, s1: s + d1, v0, v1 });
    if (sTo > s + d1) legs.push({ s0: s + d1, s1: sTo, v0: v1, v1 });
  }
  const c = chainLegs(mergeShortLegs(legs, a2, a2), tTd, v0, 'roll', 0, segs, a2);
  const t1 = c.t;
  return { kind: 'landing', role: 'arr', end, t0: tTd, t1, segs, route: opts.route ?? null, rwy: R, perf: slimPerf(perf), dir: 1, phases: [[tTd, 'landing']], marks: { touchdownMs: tTd, exitStartMs: t1, vExitCms: c.v, tdSCm: sTd - (perf.wheelbaseCm || 0) } };
}
/** Take-off from the line-up point (entry = route.lineup or {rwySCm}) at tRoll: roll at aTo to Vlof, then climb to the fade. */
export function takeoffTraj(end, entry, perf, tRoll, opts = {}) {
  const R = rwyOf(end, opts); const s0 = entry.rwySCm ?? entry.sCm ?? 0; const a = perf.aToCms2, vl = perf.vlofCms;
  const dRoll = Math.round(vl * vl / (2 * a));
  const segs = []; const g1 = legSeg(tRoll, s0, s0 + dRoll, 0, vl, 'roll'); segs.push(g1);
  const va = PERF.vClimbCms, ac = PERF.climbAccCms2; const vlA = g1.v1Cms;
  const dAcc = Math.round((va * va - vlA * vlA) / (2 * ac));
  const sFade = R.lenCm + (opts.fadeBeyondEndCm ?? TRAJ.fadeBeyondEndCm);
  const sLof = s0 + dRoll;
  if (sLof + dAcc < sFade) chainLegs([{ s0: sLof, s1: sLof + dAcc, v1: va }, { s0: sLof + dAcc, s1: sFade, v1: va }], g1.t1, vlA, 'climb', 0, segs);
  else chainLegs([{ s0: sLof, s1: sFade, v1: isqrt(vlA * vlA + 2 * ac * (sFade - sLof)) }], g1.t1, vlA, 'climb', 0, segs);
  const tLof = g1.t1;
  const marks = { rollMs: tRoll, liftoffMs: tLof, liftoffSCm: sLof, rollCm: dRoll, fadeMs: segs[segs.length - 1].t1 };
  const route = opts.route ?? entry.route ?? null;   // the departure route (router.js gives route.lineup a non-enumerable back-reference)
  const tr = { kind: 'takeoff', role: 'dep', end, t0: tRoll, t1: segs[segs.length - 1].t1, segs, route, rwy: R, perf: slimPerf(perf), dir: 1, phases: [[tRoll, 'takeoff'], [tLof, 'departure']], marks };
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
  const sTd = opts.tdSCm ?? touchdownSCm(end, perf, opts);   // main-gear touchdown station
  const sTdN = sTd + (perf.wheelbaseCm || 0);                  // the nose-gear station at touchdown (route starts are nose stations, V9)
  const need = sTdN + Math.round((perf.vappCms * perf.vappCms - PERF.vExitCms * PERF.vExitCms) / (2 * perf.aDecCms2));
  const all = router.exits(end, true); const same = all.filter(e => e.side === side);
  const rotMax = opts.rotMaxMs ?? TRAJ.rotMaxMs;
  const span = opts.spanCm ?? perf.spanCm;
  // reachable: braking at a_dec from touchdown reaches the turn-off speed this exit's path allows before the route start
  const reach = (e) => { if (e.startCm < need) return false; const rt = router.arrival(e.id, stand, { spanCm: span }); if (!rt) return false; const v = arrivalEntryCms(rt, perf); return e.startCm >= sTdN + (perf.vappCms * perf.vappCms - v * v) / (2 * perf.aDecCms2); };
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
const _a = {}, _b = {}, _c = {}, _e = {}, _f = {}, _g = {};
function profY(R, s) { const P = R.profile; if (!P || !P.length) return groundY(0, 0); if (s <= P[0][0]) return P[0][1]; for (let i = 1; i < P.length; i++) if (s <= P[i][0]) { const k = (s - P[i - 1][0]) / (P[i][0] - P[i - 1][0]); return P[i - 1][1] + k * (P[i][1] - P[i - 1][1]); } return P[P.length - 1][1]; }
/** height (m) above the runway of an air / runway trajectory at NOSE-GEAR station s (cm); the approach's glide path,
 *  flare and touchdown are main-gear stations (V9), so the approach is evaluated at s - wheelbase */
function heightAt(tr, s) {
  if (tr.kind === 'approach') {
    const { sFl, sTd } = tr.flare; const sm = s - (tr.flare.wb || 0);
    if (sm <= sFl) return (tr.flare.sWi - sm) * TRAJ.tanGlide / 100;
    const uF = sTd - sFl; const u = sTd - sm; if (u <= 0) return 0;
    const b = 2 * TRAJ.flareFromCm / uF - TRAJ.tanGlide, a = (TRAJ.tanGlide - b) / (2 * uF);   // h = a u^2 + b u, h(uF) = 12 m, h'(uF) = tan 3
    return (a * u * u + b * u) / 100;
  }
  if (tr.kind === 'takeoff') { const sl = tr.marks.liftoffSCm; if (s <= sl) return 0; return Math.min(TRAJ.climbToCm, (s - sl) * TRAJ.tanClimb) / 100; }
  return 0;
}

// ---- main-gear model (display only; fix round 1, V5 / V2)
// The main gear cannot slip sideways: it always moves along the aircraft's axis. Forward taxi: the nose gear follows the
// path (s) and the main-gear centre is its TRACTRIX (pursuit curve at the wheelbase), integrated once per route and
// wheelbase from the route start and shared by every trajectory on that route; it starts where the push left it (a
// departure) or on the runway centreline (an arrival). Push-back: the same constraint holds in reverse, so the push is
// the time reverse of a forward taxi: the nose gear (the tug) follows the push path and the main gear is the tractrix of
// that path traversed BACKWARDS from the push end, where both gears are aligned on a straight (router pushAlignCm), so
// the first taxi pose equals the last push pose. Take-off roll: the tractrix continues from the line-up pose until it
// is on the centreline. Floats (display; since fix round 3 the forward and push followers are deterministic - pointAtDet,
// angleDet - because their main-gear kinematics cap the commit-path speed, mainGearZones).
// pose.main is this model; pose.mainChord is the round-0 chord model (both gears on the path), kept for comparison (C2).
// At the stand (the end of an arrival, the start of a push) the main gear is blended over alignCm onto the chord position
// (both gears on the lead-in): the stand's parked pose (gate engine) has the stand heading, and the OSM lead-ins are often
// too short for the tractrix to align (up to 14 deg off); the blend is the pilot's / tug's alignment (small slip, low speed).
// Fix round 2 (M1): forward taxi uses JUDGEMENTAL OVERSTEERING. With the nose gear on the centreline the no-slip main gear
// cuts every corner by up to R - sqrt(R^2 - wb^2) (9.7 m for a B77W on a 55 m fillet), onto the shoulders. The displayed nose
// gear is therefore steered outward: O(s) = P(s - wb) + wb t(s - wb) puts the main gear exactly on the centreline (P = the
// route path, t its tangent; the tractrix of O is P(s - wb)); the displayed nose is N(s) = P(s) + w(s) (O(s) - P(s)) with
// w = 1 unless that moves the nose more than oversteer.maxOffCm from P (then w = maxOff / max |O - P| over the arc's
// influence [arc start, arc end + wb], ramped), so the nose gear stays within 10 m of the centreline [inf]: inside the 23 m
// main taxiway (AIP (mirror) AD 2.8, taxigraph halfWidth 11.5 m) and, at a junction, over its outer corner; measured over all
// routes (tools/sim/test_router.mjs M1) the oversteered nose is off the load-bearing pavement LESS often than a nose on the
// centreline (a 6 m cap left the wide-bodies' main gear 3.5 x as often off it as 10 m; 15 m put 4 x more noses off). The main gear is the tractrix of
// the DISPLAYED nose (no slip anywhere). Pushes keep the tug-steered nose on the push path (w = 0). At the stand (the last
// 2.5 wheelbases + 10 m of an arrival) w fades to 0 and the main gear is blended onto the lead-in as before (D11). Tight
// fillets (R <= r0Cm 10 m; partly up to r1Cm 20 m) and a departure's first wheelbase (the main gear is where the push left it,
// not on the path's backward extension) keep the nose on the path. The speed cap of a turn holds until the main gear has
// left it (groundTraj turn zones), so the main gear's yaw rate stays within sqrt(a_lat / R).
// s keeps its meaning on the commit path: the station along the centreline (= the nose gear on straights); in corners the
// displayed nose gear is up to maxOff outside it and moves at v / cos(steering angle).
// Fix round 3 (V3-2): the follower is DETERMINISTIC (path.js pointAtDet / angleDet: + - * / sqrt only, Float32 samples)
// because it now feeds the commit path: groundTraj caps the nose-station speed wherever the displayed main gear would turn
// harder than the piece's a_lat (1.0 m/s^2, 1.25 on rapid exits and the runway lead, design §4.4 / D8) or yaw faster than
// FOLLOW.yawMaxDegS (mainGearZones, part of turnZones). The pose's x / z is the REFERENCE point (the nose-gear station s on the
// centreline, the point that moves at gs); the displayed gears are pose.nose / pose.main with their own speeds noseGs / mainGs.
export const FOLLOW = { stepCm: 10, sampleCm: 100, alignWb: 2.5, alignAddCm: 1000, oversteer: { maxOffCm: 1000, rampCm: 1000, rampK: 5, r0Cm: 1000, r1Cm: 2000 },
  // fix round 3 (V3-2): main-gear speed caps from the follower: a_lat of the piece under the main gear (station s - wb), the
  // yaw guard 20 deg/s (the test bound since fix round 1, V2), each 1 m interval's demand at its peak 25 cm sub-step (the
  // displayed body axis), zones merged while their caps stay within 5 % [inf]
  yawMaxDegS: 20, capJoin: 1.05,
  snapCm: 0.05,   // fix round 3: a main gear within 0.5 mm of the centreline point P(s - wb) where the oversteer weight is 1 stays on it exactly [inf]
  src: 'inf',
  basis: 'non-holonomic main gear (no lateral slip): tractrix of the displayed nose-gear path (forward taxi: oversteered, main gear on the centreline; push: the tug on the push path, backwards from the push end); aligned onto the lead-in over 2.5 wheelbases + 10 m at the stand; main-gear lateral acceleration <= a_lat of the piece (design §4.4, D8) and yaw <= 20 deg/s by speed caps (fix round 3)' };
/** oversteer weights per sampleCm of nose station (forward routes), with the arrival's stand fade */
function oversteerW(route, wbCm, n, alignL) {
  const W = new Float32Array(n).fill(1); const path = route.path; const OS = FOLLOW.oversteer, sc = FOLLOW.sampleCm; const a = {}, b = {};
  const dev = (s) => { pointAtDet(path, s, a); pointAtDet(path, s - wbCm, b); const ox = b.x + b.hx * wbCm - a.x, oz = b.z + b.hz * wbCm - a.z; return Math.sqrt(ox * ox + oz * oz); };
  for (const p of path.pieces) {
    if (p.kind !== 'arc') continue; const s0 = p.s0Cm, s1 = p.s0Cm + p.lenCm + wbCm; let D = 0;
    for (let s = s0; s <= s1; s += sc) D = Math.max(D, dev(s));
    const wR = p.rCm <= OS.r0Cm ? 0 : p.rCm >= OS.r1Cm ? 1 : (p.rCm - OS.r0Cm) / (OS.r1Cm - OS.r0Cm);
    const w = Math.min(wR, D > OS.maxOffCm ? OS.maxOffCm / D : 1); if (w >= 1) continue;
    // the ramp is long enough that the nose's sideways shift (1 - w) D changes by at most 1 / rampK per metre of travel
    const ramp = Math.max(OS.rampCm, OS.rampK * (1 - w) * D);
    const i0 = Math.max(0, Math.floor((s0 - ramp) / sc)), i1 = Math.min(n - 1, Math.ceil((s1 + ramp) / sc));
    for (let i = i0; i <= i1; i++) { const s = i * sc; const d = s < s0 ? s0 - s : s > s1 ? s - s1 : 0; const v = d >= ramp ? 1 : w + (1 - w) * d / ramp; if (v < W[i]) W[i] = v; }
  }
  if (alignL > 0) { const sA = route.lenCm - alignL; for (let i = 0; i < n; i++) { const s = i * sc; if (s <= sA) continue; const u = Math.min(1, (s - sA) / alignL); W[i] *= 1 - u * u * (3 - 2 * u); } }
  if (route.kind === 'dep') { const r = OS.rampK * OS.maxOffCm; for (let i = 0; i < n; i++) { const s = i * sc; if (s >= wbCm + r) break; W[i] *= s <= wbCm ? 0 : (s - wbCm) / r; } }
  return W;
}
/** the displayed (oversteered) nose gear [x, z] (cm, out.x / out.z) of a forward-taxi follower at station s (cm), FOLLOW; deterministic */
export function noseAt(f, path, s, out = {}) {
  pointAtDet(path, s, out); if (!f || !f.W) return out;
  const u = s / FOLLOW.sampleCm; let i = Math.floor(u); let w;
  if (i < 0) w = f.W[0]; else if (i >= f.n - 1) w = f.W[f.n - 1]; else w = f.W[i] + (f.W[i + 1] - f.W[i]) * (u - i);
  if (!(w > 0)) return out;
  const b = pointAtDet(path, s - f.wbCm, _d); const ox = b.x + b.hx * f.wbCm, oz = b.z + b.hz * f.wbCm;
  out.x += w * (ox - out.x); out.z += w * (oz - out.z); return out;
}
const _d = {}, _g2 = {};
function blendChord(X, Z, sOf, path, wbCm, sA, sB, toChordAtB, dirSign, noseFn = null) {   // blend samples with s in [sA, sB] towards the chord position
  const q = {}, nq = {};
  for (let i = 0; i < X.length; i++) {
    const s = sOf(i); if (s < sA || (s > sB && !toChordAtB)) continue;   // (beyond the route end: fully on the chord)
    let u = Math.min(1, (s - sA) / Math.max(1, sB - sA)); if (!toChordAtB) u = 1 - u; const w = u * u * (3 - 2 * u);
    pointAtDet(path, s - dirSign * wbCm, q); if (noseFn) noseFn(s, nq); else pointAtDet(path, s, nq);
    let mx = (1 - w) * X[i] * 100 + w * q.x, mz = (1 - w) * Z[i] * 100 + w * q.z;
    const dx = nq.x - mx, dz = nq.z - mz, d = Math.sqrt(dx * dx + dz * dz) || 1; mx = nq.x - dx * wbCm / d; mz = nq.z - dz * wbCm / d;
    X[i] = mx / 100; Z[i] = mz / 100;
  }
}
/** largest main-gear slip (deg) between consecutive samples: motion direction vs the body axis (deterministic) */
function maxSlip(X, Z, sOf, path, i0, i1, noseFn = null) {
  const nq = {}; let mx = 0;
  for (let i = Math.max(1, i0); i <= Math.min(X.length - 1, i1); i++) {
    const ex = X[i] - X[i - 1], ez = Z[i] - Z[i - 1], el = Math.sqrt(ex * ex + ez * ez); if (el < 1e-3) continue;
    if (noseFn) noseFn(sOf(i), nq); else pointAtDet(path, sOf(i), nq); const hx = nq.x / 100 - X[i], hz = nq.z / 100 - Z[i];
    let a = angleDet(ex, ez, hx, hz) * RAD2DEG; if (a > 90) a = 180 - a; if (a > mx) mx = a;
  }
  return mx;
}
/** blend onto the chord over 2.5 wheelbases + 10 m at the stand; returns {L, sl: the largest slip in the blend (deg)} */
function alignBlend(X, Z, sOf, path, wbCm, atEnd, lenCm, dirSign, noseFn = null) {
  const L = Math.min(lenCm, Math.round(FOLLOW.alignWb * wbCm + FOLLOW.alignAddCm));
  const sA = atEnd ? lenCm - L : 0, sB = atEnd ? lenCm : L;
  blendChord(X, Z, sOf, path, wbCm, sA, sB, atEnd, dirSign, noseFn);
  return { L, sl: maxSlip(X, Z, sOf, path, Math.floor(sA / FOLLOW.sampleCm), Math.ceil(sB / FOLLOW.sampleCm) + 1, noseFn) };
}
/**
 * The displayed main gear between the 1 m samples (fix round 3, V3-2): a uniform Catmull-Rom spline through the samples
 * (C1: no heading kink at the samples; round 2 interpolated linearly, which put a +-2 % sawtooth on the body's yaw rate in every
 * turn - the chord direction is off the arc tangent by +-h / 2R). Interval i -> i + 1 at fraction k; writes [x, z] (m) and,
 * with d, the derivative per interval [dx/dk, dz/dk]. Deterministic.
 */
function crAt(X, Z, n, i, k, out, d = null) {
  const i0 = i > 0 ? i - 1 : -1, i3 = i + 2 < n ? i + 2 : -1;
  const x1 = X[i], z1 = Z[i], x2 = X[i + 1], z2 = Z[i + 1];
  const x0 = i0 >= 0 ? X[i0] : 2 * x1 - x2, z0 = i0 >= 0 ? Z[i0] : 2 * z1 - z2, x3 = i3 >= 0 ? X[i3] : 2 * x2 - x1, z3 = i3 >= 0 ? Z[i3] : 2 * z2 - z1;
  const ax = 2 * x0 - 5 * x1 + 4 * x2 - x3, az = 2 * z0 - 5 * z1 + 4 * z2 - z3, bx = -x0 + 3 * x1 - 3 * x2 + x3, bz = -z0 + 3 * z1 - 3 * z2 + z3, cx = x2 - x0, cz = z2 - z0;
  out[0] = x1 + 0.5 * k * (cx + k * (ax + k * bx)); out[1] = z1 + 0.5 * k * (cz + k * (az + k * bz));
  if (d) { d[0] = 0.5 * (cx + k * (2 * ax + 3 * k * bx)); d[1] = 0.5 * (cz + k * (2 * az + 3 * k * bz)); }
  return out;
}
/**
 * Per-interval kinematics of a forward follower (fix round 3, V3-2), interval i = samples i-1 -> i (nose stations (i-1) ..
 * i sampleCm), from the DISPLAYED model (Catmull-Rom main gear, the nose of noseFn) at KIN_SUB sub-steps: RM[i] = the largest
 * main-gear speed / nose-station speed, YW[i] = the largest yaw per sampleCm of nose station, QW[i] = the largest product of
 * the two (rad per sampleCm: the main gear's lateral acceleration is QW v^2 / sampleCm). Deterministic.
 */
const KIN_SUB = 4;
function intervalKin(X, Z, n, noseFn, sc, AI = null, path = null, wbCm = 0) {
  const RM = new Float32Array(n), YW = new Float32Array(n), QW = new Float32Array(n); const nq = {}, m = [0, 0], pq = {};
  noseFn(0, nq); let ex0 = nq.x / 100 - X[0], ez0 = nq.z / 100 - Z[0], mx0 = X[0], mz0 = Z[0];
  for (let i = 1; i < n; i++) {
    let rp = 0, yp = 0, qp = 0;
    for (let j = 1; j <= KIN_SUB; j++) {
      const k = j / KIN_SUB; if (AI && AI[i]) { pointAtDet(path, (i - 1 + k) * sc - wbCm, pq); m[0] = pq.x / 100; m[1] = pq.z / 100; } else crAt(X, Z, n, i - 1, k, m);
      noseFn((i - 1 + k) * sc, nq); const ex = nq.x / 100 - m[0], ez = nq.z / 100 - m[1];
      const r = Math.sqrt((m[0] - mx0) * (m[0] - mx0) + (m[1] - mz0) * (m[1] - mz0)) * KIN_SUB * 100 / sc, y = angleDet(ex0, ez0, ex, ez) * KIN_SUB;
      if (r > rp) rp = r; if (y > yp) yp = y; if (r * y > qp) qp = r * y; ex0 = ex; ez0 = ez; mx0 = m[0]; mz0 = m[1];
    }
    RM[i] = rp; YW[i] = yp; QW[i] = qp;
  }
  RM[0] = n > 1 ? RM[1] : 1; return { RM, YW, QW };
}
/** push follower: per interval the main-gear chord / nose-station length (linear interpolation; display speed only) */
function pushKin(X, Z, n, sOf) {
  const RM = new Float32Array(n);
  for (let i = 1; i < n; i++) { const ds = (sOf(i) - sOf(i - 1)) / 100; const dx = X[i] - X[i - 1], dz = Z[i] - Z[i - 1]; RM[i] = ds > 0 ? Math.sqrt(dx * dx + dz * dz) / ds : 1; }
  RM[0] = n > 1 ? RM[1] : 1; return RM;
}
const followCache = new WeakMap();
/**
 * The main-gear follower of a route for a wheelbase: Float32 x / z (m) every sampleCm of station; opts.model 'over'
 * (default, the displayed model: oversteered nose, FOLLOW) or 'tractrix' (round 1: nose gear on the path, for comparison).
 * f.W holds the oversteer weights (noseAt), f.RM / f.YW the per-interval main-gear speed ratio and yaw (fix round 3).
 * Deterministic since fix round 3 (an input of groundTraj's main-gear caps).
 */
export function gearFollower(route, wbCm, opts = {}) {
  const model = opts.model || 'over';
  const path = route.path; let m = followCache.get(path); if (!m) { m = new Map(); followCache.set(path, m); }
  const key = wbCm + '|' + route.kind + '|' + model; let f = m.get(key); if (f) return f;
  const n = Math.floor(route.lenCm / FOLLOW.sampleCm) + 2; const X = new Float64Array(n), Z = new Float64Array(n);   // fix round 3: Float64 (Float32 at 1-2 km put 1-2 % noise on the 25 cm yaw steps of the caps)
  const alignL = route.kind === 'arr' ? Math.min(route.lenCm, Math.round(FOLLOW.alignWb * wbCm + FOLLOW.alignAddCm)) : 0;
  const W = model === 'over' ? oversteerW(route, wbCm, n, alignL) : null;
  const fw = { W, n, wbCm }; const nose = (s, out) => (W ? noseAt(fw, path, s, out) : pointAtDet(path, s, out));
  let mx, mz;
  if (route.kind === 'dep' && route.push && route.push.path) { const g = pushFollowAt(pushFollower(route, wbCm), route.push.lenCm); mx = g[0] * 100; mz = g[1] * 100; }
  else { const q = pointAtDet(path, -wbCm, _c); mx = q.x; mz = q.z; }
  // fix round 3 (V3-2): where the oversteer weight is 1 and the main gear is on the centreline (within snapCm) it STAYS there
  // exactly, M = P(s - wb) (the tractrix of O is that curve); the 10 cm pursuit steps alone drift by ~0.1-1 mm at every
  // curvature change, which put 0.1-0.5 % of spurious yaw on the main gear (and 1-2 cm/s of needless caps)
  const wOne = (s) => { if (!W) return false; const u = s / FOLLOW.sampleCm; const i = Math.floor(u); if (i < 0) return W[0] >= 1; if (i >= n - 1) return W[n - 1] >= 1; return W[i] >= 1 && W[i + 1] >= 1; };
  let onLine = false; const snap2 = FOLLOW.snapCm * FOLLOW.snapCm;
  const pull = (s) => {
    if (onLine && wOne(s)) { const q = pointAtDet(path, s - wbCm, _c); mx = q.x; mz = q.z; return; }
    const q = nose(s, _c); const dx = q.x - mx, dz = q.z - mz, d = Math.sqrt(dx * dx + dz * dz) || 1; mx = q.x - dx * wbCm / d; mz = q.z - dz * wbCm / d;
    onLine = false; if (wOne(s)) { const c = pointAtDet(path, s - wbCm, _g2); const ex = c.x - mx, ez = c.z - mz; if (ex * ex + ez * ez <= snap2) { mx = c.x; mz = c.z; onLine = true; } }
  };
  pull(0); X[0] = mx / 100; Z[0] = mz / 100;
  // AI[i] = 1: the whole interval (i-1, i] was on the centreline (M = P(s - wb) exactly): displayed and measured analytically
  const AI = new Uint8Array(n);
  for (let i = 1; i < n; i++) { const s1 = i * FOLLOW.sampleCm; let all = onLine; for (let s = s1 - FOLLOW.sampleCm + FOLLOW.stepCm; s <= s1; s += FOLLOW.stepCm) { pull(s); all = all && onLine; } X[i] = mx / 100; Z[i] = mz / 100; AI[i] = all ? 1 : 0; }
  let align = null; if (route.kind === 'arr') { align = alignBlend(X, Z, (i) => i * FOLLOW.sampleCm, path, wbCm, true, route.lenCm, 1, nose); for (let i = Math.max(1, Math.floor((route.lenCm - align.L) / FOLLOW.sampleCm)); i < n; i++) AI[i] = 0; }
  const K = intervalKin(X, Z, n, nose, FOLLOW.sampleCm, AI, path, wbCm);
  f = { X, Z, n, wbCm, W, model, AI, path, RM: K.RM, YW: K.YW, QW: K.QW, alignCm: align ? align.L : 0, alignSlipDeg: align ? align.sl : 0 }; m.set(key, f); return f;
}
/** main-gear centre [x, z] (m) of a follower at nose-gear station s (cm), linear between samples */
export function followAt(f, s, out = [0, 0]) {
  const u = s / FOLLOW.sampleCm; let i = Math.floor(u);
  if (i < 0) { out[0] = f.X[0]; out[1] = f.Z[0]; return out; }
  if (i >= f.n - 1) { out[0] = f.X[f.n - 1]; out[1] = f.Z[f.n - 1]; return out; }
  if (f.AI && f.AI[i + 1]) { const q = pointAtDet(f.path, s - f.wbCm, _fa); out[0] = q.x / 100; out[1] = q.z / 100; return out; }   // on the centreline
  return crAt(f.X, f.Z, f.n, i, u - i, out);   // fix round 3: Catmull-Rom (was linear)
}
const _fa = {};
const _cr = [0, 0], _crd = [0, 0];
/** main-gear speed / nose-station speed at s (the derivative of the displayed main gear; fix round 3) */
export function followRatio(f, s) {
  if (!f) return 1; const u = s / FOLLOW.sampleCm; let i = Math.floor(u); if (i < 0) i = 0; if (i > f.n - 2) i = f.n - 2; if (i < 0) return 1;
  if (f.AI && f.AI[i + 1]) return 1;   // on the centreline: the main gear moves at the nose station's speed
  crAt(f.X, f.Z, f.n, i, Math.max(0, Math.min(1, u - i)), _cr, _crd); return Math.sqrt(_crd[0] * _crd[0] + _crd[1] * _crd[1]) * 100 / FOLLOW.sampleCm;
}
/** the push's main-gear follower: tractrix of the push path from the push end back to the stand (samples by nose station) */
export function pushFollower(route, wbCm) {
  const P = route.push; const path = P.path; let m = followCache.get(path); if (!m) { m = new Map(); followCache.set(path, m); }
  const key = wbCm + '|push|' + P.lenCm; let f = m.get(key); if (f) return f;
  const n = Math.floor(P.lenCm / FOLLOW.sampleCm) + 2; const X = new Float64Array(n), Z = new Float64Array(n);
  const q0 = pointAtDet(path, P.lenCm + wbCm, _c); let mx = q0.x, mz = q0.z;
  const pull = (s) => { const q = pointAtDet(path, s, _c); const dx = q.x - mx, dz = q.z - mz, d = Math.sqrt(dx * dx + dz * dz) || 1; mx = q.x - dx * wbCm / d; mz = q.z - dz * wbCm / d; };
  // from the push end (s = lenCm) down to 0; sample i holds s = i * sampleCm (the last sample: the push end itself)
  pull(P.lenCm); const last = n - 1; X[last] = mx / 100; Z[last] = mz / 100;   // index n - 1 stands for s = lenCm
  let sPrev = P.lenCm;
  for (let i = n - 2; i >= 0; i--) { const s1 = i * FOLLOW.sampleCm; for (let s = sPrev - FOLLOW.stepCm; s > s1; s -= FOLLOW.stepCm) pull(s); pull(s1); X[i] = mx / 100; Z[i] = mz / 100; sPrev = s1; }
  const sOf = (i) => (i === n - 1 ? P.lenCm : i * FOLLOW.sampleCm);
  const align = alignBlend(X, Z, sOf, path, wbCm, false, P.lenCm, -1);
  f = { X, Z, n, wbCm, lenCm: P.lenCm, RM: pushKin(X, Z, n, sOf), alignCm: align.L, alignSlipDeg: align.sl }; m.set(key, f); return f;
}
function pushFollowAt(f, s, out = [0, 0]) {   // samples at i * sampleCm for i < n - 1 and the push end at n - 1
  const iLast = f.n - 1, sLast = (iLast - 1) * FOLLOW.sampleCm;
  if (s >= f.lenCm) { out[0] = f.X[iLast]; out[1] = f.Z[iLast]; return out; }
  if (s <= 0) { out[0] = f.X[0]; out[1] = f.Z[0]; return out; }
  let i = Math.floor(s / FOLLOW.sampleCm), j = i + 1, s0 = i * FOLLOW.sampleCm, s1 = j * FOLLOW.sampleCm;
  if (i >= iLast - 1) { i = iLast - 1; j = iLast; s0 = sLast; s1 = f.lenCm; }
  const k = s1 > s0 ? (s - s0) / (s1 - s0) : 0; out[0] = f.X[i] + (f.X[j] - f.X[i]) * k; out[1] = f.Z[i] + (f.Z[j] - f.Z[i]) * k; return out;
}
function pushFollowRatio(f, s) { const iLast = f.n - 1; let j = s >= f.lenCm ? iLast : Math.floor(s / FOLLOW.sampleCm) + 1; if (j > iLast) j = iLast; if (j < 1) j = 1; return f.RM[j]; }
/**
 * Main-gear speed caps of a forward route for a type (fix round 3, V3-2), integers: zones [{s0Cm, s1Cm, vmaxCms, why}] where
 * the displayed main gear (the follower: tractrix of the oversteered nose) would exceed a_lat of the piece under it
 * (v^2 RM YW / sampleCm <= a_lat) or the yaw guard (v YW / sampleCm <= yawMax) at the caps it already has (pieces, turn
 * zones, route zones); each interval's demand at its peak sub-step (intervalKin). Commit path: deterministic.
 */
export function mainGearZones(route, perf, baseZones = null) {
  const wb = perf.wheelbaseCm || 0; if (!wb || !route.path || !route.path.pieces.length || route.kind === 'push') return [];
  const path = route.path; let m = followCache.get(path); if (!m) { m = new Map(); followCache.set(path, m); }
  const key = 'zones|' + wb + '|' + route.kind; let Zs = m.get(key); if (Zs) return Zs;
  const f = gearFollower(route, wb); const n = f.n, sc = FOLLOW.sampleCm;
  const base = capsOf(route, path, baseZones || baseTurnZones(route, perf), 0, route.lenCm);
  const yawMax = FOLLOW.yawMaxDegS * Math.PI / 180;
  const q = new Float64Array(n), y = new Float64Array(n);
  for (let i = 1; i < n; i++) { q[i] = f.QW[i]; y[i] = f.YW[i]; }
  Zs = []; let cur = null; let j = 0;
  for (let i = 1; i < n; i++) {
    const a = (i - 1) * sc, b = Math.min(route.lenCm, i * sc); if (b <= a) break;
    const qq = q[i], yy = y[i];   // the interval's peak (intervalKin)
    if (!(qq > 1e-9)) { if (cur) { Zs.push(cur); cur = null; } continue; }
    const pc = pieceAt(path, Math.max(0, Math.round((a + b) / 2) - wb)); const al = path.pieces[pc].aLatCms2 || PERF_ALAT;
    let c = Math.floor(Math.sqrt(al * sc / qq)); if (yy > 1e-9) c = Math.min(c, Math.floor(yawMax * sc / yy));
    while (j < base.length - 1 && base[j].b <= a) j++;
    let bc = 1e9; for (let k = j; k < base.length && base[k].a < b; k++) bc = Math.min(bc, base[k].c);
    if (c >= bc) { if (cur) { Zs.push(cur); cur = null; } continue; }
    if (cur && cur.s1Cm === a && c <= cur.vmaxCms * FOLLOW.capJoin && cur.vmaxCms <= c * FOLLOW.capJoin) { cur.s1Cm = b; cur.vmaxCms = Math.min(cur.vmaxCms, c); }
    else { if (cur) Zs.push(cur); cur = { s0Cm: a, s1Cm: b, vmaxCms: c, why: 'main gear' }; }
  }
  if (cur) Zs.push(cur);
  m.set(key, Zs); return Zs;
}
const PERF_ALAT = 100;
const toCache = new WeakMap();
/** take-off roll follower: from the line-up pose (the route's follower at its end) along the runway axis until aligned */
function takeoffFollower(tr) {
  let f = toCache.get(tr); if (f !== undefined) return f;
  f = null; const rt = tr.route; const wb = tr.perf.wheelbaseCm;
  if (rt && rt.path && wb > 0) {
    const g = followAt(gearFollower(rt, wb), rt.lenCm); let mx = g[0] * 100, mz = g[1] * 100;
    const R = tr.rwy, h = R.h, s0 = tr.segs[0].s0Cm; const X = [], Z = [];
    for (let k = 0; k < 4000; k++) {   // samples every sampleCm, up to 4 km
      const s1 = s0 + k * FOLLOW.sampleCm;
      for (let s = (k ? s1 - FOLLOW.sampleCm + FOLLOW.stepCm : s1); s <= s1; s += FOLLOW.stepCm) { const nx = R.pCm[0] + h[0] * s, nz = R.pCm[1] + h[1] * s; const dx = nx - mx, dz = nz - mz, d = Math.sqrt(dx * dx + dz * dz) || 1; mx = nx - dx * wb / d; mz = nz - dz * wb / d; }
      X.push(mx / 100); Z.push(mz / 100);
      const nx = R.pCm[0] + h[0] * s1, nz = R.pCm[1] + h[1] * s1; const lat = Math.abs((mx - nx) * h[1] - (mz - nz) * h[0]);
      if (lat < 0.1 && k > 0) break;   // within 1 mm of the centreline
    }
    const RM = new Float32Array(X.length); for (let i = 1; i < X.length; i++) RM[i] = Math.sqrt((X[i] - X[i - 1]) * (X[i] - X[i - 1]) + (Z[i] - Z[i - 1]) * (Z[i] - Z[i - 1])); if (X.length > 1) RM[0] = RM[1];
    f = { s0, X: Float64Array.from(X), Z: Float64Array.from(Z), n: X.length, RM };
  }
  toCache.set(tr, f); return f;
}
const angDiff = (a, b) => { let d = Math.abs(a - b) % 360; return d > 180 ? 360 - d : d; };
/**
 * DISPLAY: pose at time t (floats, metres, degrees true). Fix round 3 (V3-2): x, z = the REFERENCE point, the nose-gear
 * station s on the route centreline (push: the tug's nose gear on the push path; runway / air: the nose gear on the runway
 * axis), which moves at gs; nose: [x, z] the displayed nose-gear contact (oversteered outward in corners, round 2) moving at
 * noseGs; main: [x, z] main-gear centre (no-slip model above) moving at mainGs; hdg: the body axis main -> displayed nose;
 * tip: [x, z] nose tip (from nose along hdg); nosePath = [x, z] (round 2 name); mainChord: the chord model's main gear (on
 * the path, wheelbase behind); steerDeg: nose-wheel angle; y: gear-contact height (world y); gs, vs, noseGs, mainGs: m/s;
 * pitch, roll: degrees. Draw the body from nose (or main) and hdg.
 */
export function evalTraj(tr, t, out = {}) {
  const tt = Math.max(tr.t0, Math.min(tr.t1, t));
  const s = sAtFloat(tr, tt), v = vAt(tr, tt) / 100;
  const P = tr.perf; const wb = P.wheelbaseCm, ng = P.noseGearCm;
  out.phase = phaseAt(tr, tt); out.t = tt;
  if (tr.kind === 'push') {   // nose gear (tug) on the push path; main gear: the backward tractrix from the push end
    const n = pointAt(tr.path, s, _a); out.x = n.x / 100; out.z = n.z / 100; out.y = groundY(out.x, out.z);
    out.nose = [out.x, out.z]; out.nosePath = out.nose;
    const mc = pointAt(tr.path, s + wb, _b); out.mainChord = [mc.x / 100, mc.z / 100];
    const PF = tr.route && tr.route.push && tr.route.push.path === tr.path ? pushFollower(tr.route, wb) : null;
    const M = PF ? pushFollowAt(PF, s) : out.mainChord;
    out.main = [M[0], M[1]]; out.hdg = vecHdg(out.x - M[0], out.z - M[1]);
    out.steerDeg = angDiff(out.hdg, vecHdg(-n.hx, -n.hz));
    const f = hdgVec(out.hdg); out.tip = [out.x + f[0] * ng / 100, out.z + f[1] * ng / 100];
    out.gs = Math.abs(v); out.noseGs = out.gs; out.mainGs = out.gs * (PF ? pushFollowRatio(PF, s) : 1);
    out.vs = 0; out.ground = true; out.gear = 1; out.pitch = 0; out.roll = 0; out.flaps = 0; out.spoilers = 0;
    return out;
  }
  if (tr.kind === 'ground') {
    const route = tr.route; const F = route && route.path === tr.path ? gearFollower(route, wb) : null;
    const pc = pointAt(tr.path, s, _e); out.x = pc.x / 100; out.z = pc.z / 100; out.y = groundY(out.x, out.z); out.nosePath = [out.x, out.z];
    const n = F ? noseAt(F, tr.path, s, _a) : pc;   // the displayed (oversteered) nose gear, FOLLOW
    out.nose = [n.x / 100, n.z / 100];
    const mc = pointAt(tr.path, s - wb, _b); out.mainChord = [mc.x / 100, mc.z / 100];
    const M = F ? followAt(F, s) : out.mainChord;
    out.main = [M[0], M[1]];
    out.hdg = vecHdg(out.nose[0] - M[0], out.nose[1] - M[1]);
    // nose-wheel angle: the displayed nose gear's direction of motion vs the body axis; its speed from the same 0.5 m chord
    let hx = pc.hx, hz = pc.hz, rn = 1;
    if (F && F.W) { const a = noseAt(F, tr.path, s + 25, _f), b = noseAt(F, tr.path, s - 25, _g); hx = a.x - b.x; hz = a.z - b.z; rn = Math.sqrt(hx * hx + hz * hz) / 50; }
    out.steerDeg = angDiff(out.hdg, vecHdg(hx, hz));
    const f = hdgVec(out.hdg); out.tip = [out.nose[0] + f[0] * ng / 100, out.nose[1] + f[1] * ng / 100];
    out.gs = Math.abs(v); out.noseGs = out.gs * rn; out.mainGs = out.gs * (F ? followRatio(F, s) : 1);
    out.vs = 0; out.ground = true; out.gear = 1; out.pitch = 0; out.roll = 0;
    out.flaps = tr.role === 'dep' ? 0.35 : out.phase === 'landing' ? 1 : 0;
    out.spoilers = out.phase === 'landing' && out.gs > 40 * KT ? 1 : 0;
    return out;
  }
  // runway axis
  const R = tr.rwy; const h = R.h;
  const x = (R.pCm[0] + h[0] * s) / 100, z = (R.pCm[1] + h[1] * s) / 100;
  const agl = heightAt(tr, s);
  out.x = x; out.z = z; out.nose = [x, z]; out.nosePath = out.nose; out.y = profY(R, Math.max(0, Math.min(R.lenCm, s - wb))) + agl; out.hdg = R.hdg;
  out.main = [x - h[0] * wb / 100, z - h[1] * wb / 100]; out.mainChord = out.main; out.steerDeg = 0; let rm = 1;
  if (tr.kind === 'takeoff') {   // the roll continues the taxi's main-gear follower until it is on the centreline
    const tf = takeoffFollower(tr); const k = tf ? (s - tf.s0) / FOLLOW.sampleCm : 0;
    if (tf && k >= 0 && k < tf.n - 1) { const i = Math.floor(k), u = k - i; const mx = tf.X[i] + (tf.X[i + 1] - tf.X[i]) * u, mz = tf.Z[i] + (tf.Z[i + 1] - tf.Z[i]) * u; out.main = [mx, mz]; out.hdg = vecHdg(x - mx, z - mz); out.steerDeg = angDiff(out.hdg, R.hdg); rm = tf.RM[i + 1]; }
  }
  const f = hdgVec(out.hdg); out.tip = [x + f[0] * ng / 100, z + f[1] * ng / 100];
  out.gs = v; out.noseGs = v; out.mainGs = v * rm; out.ground = agl <= 0.001; out.roll = 0; out.spoilers = 0;
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
/** internals for tools/sim tests (not an interface) */
export const _internal = { speedProfile, mergeShortLegs, legSeg, chainLegs, holdPeaks, capsOf };
