// sha3d Phase 3 (P3-B) trajectory tests (node, no browser): tools/sim/test_traj.mjs
//   node tools/sim/test_traj.mjs              # exit 1 on a failed acceptance check
// Checks (design §7.2 P3-B, §4.4, §5): no transcendental Math function on the commit path (route assembly, push / taxi /
// approach / landing / take-off construction, the exit model, time <-> position); kinematics within the §4.4 limits (|a|,
// speeds per link kind, turn radius >= R_min, position steps, heading continuity, push 1.2 m/s / 0.3 m/s^2, line-up within
// 60 s); take-off roll <= TORA - 400 m; ROT from touchdown <= 50 s for >= 90 % of the narrow-body type x exit cases on 18L/36R
// (fix round 3: the narrow-body target; 18R/36L, wide-bodies and the <= 70 s row reported);
// glide path 3.0 +- 0.1 deg; determinism. Fix round 1 (docs/phase3/movement.md "Verification fixes, round 1"): no `**` in
// js/sim (V6); joins push -> taxi -> take-off and approach -> landing -> taxi-in for every stand x end, yaw rate <= 20 deg/s
// on every stand (V2); main-gear slip and nose-wheel angle of the displayed no-slip gear model (V5); segment end speeds
// (V7); Traj.route on every kind (V8); touchdown and threshold height of the main gear (V9). Fix round 3 (movement.md
// "Verification fixes, round 3", V3-2): every published pose point (x / z reference, nose, main) against its own published
// speed at 1 s and 0.5 s, main-gear lateral acceleration and yaw rate. Prints aggregates only.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { makeRouter, END_IDS, ROUTER } from '../../js/sim/router.js';
import { perfOf, PERF } from '../../js/sim/perf.js';
import * as TJ from '../../js/sim/traj.js';
import { pointAt, pieceAt } from '../../js/sim/path.js';
import { bodyOf, overlaps, clearance, samples } from '../../js/sim/bodies.js';
import { TYPES } from '../../js/aircraft/types.js';

const HERE = path.dirname(fileURLToPath(import.meta.url)), ROOT = path.resolve(HERE, '../..');
const rd = (f) => JSON.parse(fs.readFileSync(path.join(ROOT, 'data', f)));
const G = rd('sha_taxigraph.json'), S = rd('sha_stands.json'), T = rd('sha_routes.json');
let failed = 0, n = 0;
const check = (name, ok, detail) => { n++; if (!ok) failed++; console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? '  -- ' + detail : '')); };
const info = (name, detail) => console.log('INFO ' + name + '  -- ' + detail);
const mx = (a) => a.reduce((m, x) => (x > m ? x : m), -Infinity), mn = (a) => a.reduce((m, x) => (x < m ? x : m), Infinity);
const q = (a, p) => { if (!a.length) return NaN; const s = a.slice().sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.floor(p * (s.length - 1) + 0.5))]; };
const TYPES_TEST = ['A319', 'A320', 'A20N', 'A321', 'A21N', 'B738', 'B38M', 'C919', 'AJ27', 'CRJ9', 'E190', 'B753', 'B763', 'A332', 'A333', 'A359', 'B789', 'B77W', 'B744'];
const classRef = S.class_ref; const refType = new Map(S.stands.map(s => [s.name, (classRef[s.cls] || classRef.C).type]));
TJ.initTraj(T);
const prof = (RE, sc) => { const P = RE.profile; if (!P || !P.length) return 2.5; if (sc <= P[0][0]) return P[0][1]; for (let i = 1; i < P.length; i++) if (sc <= P[i][0]) { const k = (sc - P[i - 1][0]) / (P[i][0] - P[i - 1][0]); return P[i - 1][1] + k * (P[i][1] - P[i - 1][1]); } return P[P.length - 1][1]; };

// ------------------------------------------------------------------------------------------- 1. transcendental guard
{
  const names = ['sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'atan2', 'sinh', 'cosh', 'tanh', 'asinh', 'acosh', 'atanh', 'hypot', 'exp', 'expm1', 'pow', 'log', 'log1p', 'log2', 'log10', 'cbrt'];
  const orig = {}; const calls = {}; let on = true;
  for (const k of names) { orig[k] = Math[k]; calls[k] = 0; Math[k] = function (...a) { if (on) calls[k]++; return orig[k].apply(Math, a); }; }
  const total = () => names.reduce((a, k) => a + calls[k], 0);
  // the whole commit path: router construction + route assembly from the table, every trajectory builder, the exit model,
  // time <-> position, on a fresh router (nothing cached) for a spread of stands, ends and types
  const R = makeRouter(G, { stands: S, table: T });
  const stands = ['101', '233', '238A', '271', '404', '411', '520', '604'].filter(s => R.graph.standNode.has(s));
  let built = 0;
  for (const s of stands) for (const e of END_IDS) for (const ty of ['A320', 'B77W', 'AJ27']) {
    const P = perfOf(ty);
    const d = R.departure(s, e, { spanCm: P.spanCm }); const pt = TJ.pushTraj(d, P, 1000); const gt = TJ.groundTraj(d, P, pt.t1, { stops: [{ sCm: Math.round(d.lenCm / 2), dwellMs: 30000 }] });
    const to = TJ.takeoffTraj(e, d.lineup, P, gt.t1 + 20000); TJ.timeAtS(gt, d.lineup.holdSCm); TJ.sAt(gt, gt.t0 + 60000); TJ.vAt(gt, gt.t0 + 60000); TJ.timeAtS(to, to.segs[0].s1Cm);
    const ce = TJ.chooseExit(R, e, s, P, 0.85, { tdOffsetCm: 2500 });
    const a = R.arrival(ce.exit.id, s, { spanCm: P.spanCm }); const tTd = 5000000;
    const ap = TJ.approachTraj(e, P, tTd, { tdOffsetCm: 2500 }); const ld = TJ.landingTraj(e, P, tTd, { route: a, tdSCm: ap.marks.tdSCm });
    if (ld) { const ga = TJ.groundTraj(a, P, ld.t1, { vStart: ld.marks.vExitCms }); TJ.rotMs(ld, ga); TJ.timeAtS(ga, a.vacate.sCm); TJ.arrivalEntryCms(a, P); }
    TJ.timeAtS(ap, 0); built++;
  }
  // live routing (no table: the path-level turn rule's re-searches run on the commit path too) and an unknown closure set
  const RLv = makeRouter(G, { stands: S, live: true });
  for (const s of ['233', '271', '301', '604']) for (const e of END_IDS) { RLv.departure(s, e); for (const x of RLv.exits(e, true)) RLv.arrival(x.id, s, { spanCm: 3580 }); }
  const commitCalls = total(); const detail = names.filter(k => calls[k]).map(k => k + ' ' + calls[k]).join(', ');
  // the guard must see display evaluation (it uses cos / sin / atan2)
  const P = perfOf('A320'); const d = R.departure('233', '36L'); const gt = TJ.groundTraj(d, P, 0); TJ.evalTraj(gt, 60000); const displayCalls = total() - commitCalls;
  on = false; for (const k of names) Math[k] = orig[k];
  check('no transcendental call on the commit path (router, route assembly, push / taxi / approach / landing / take-off, exit model, time <-> s)', commitCalls === 0, commitCalls + ' calls in ' + built + ' departure + arrival builds' + (detail ? ' (' + detail + ')' : '') + '; the guard sees display evaluation: ' + displayCalls + ' calls in one evalTraj');
  check('the guard works (display evaluation is counted)', displayCalls > 0, String(displayCalls));
  // V6: the exponentiation operator (implementation-approximated like Math.pow, invisible to the wrap) in js/sim/*.js
  const starLines = []; for (const f of ['router.js', 'path.js', 'traj.js', 'perf.js', 'bodies.js']) fs.readFileSync(path.join(ROOT, 'js/sim', f), 'utf8').split('\n').forEach((ln, i) => { const code = ln.replace(/\/\/.*$/, '').replace(/\/\*.*?\*\//g, '').replace(/^\s*\*.*$/, ''); if (/\*\*/.test(code) && !/\/\*\*/.test(ln)) starLines.push(f + ':' + (i + 1)); });
  check('no ** operator in P3-B\'s js/sim modules (router, path, traj, perf, bodies; V6)', starLines.length === 0, starLines.length ? starLines.join(' ') : '0 lines');
}

// ------------------------------------------------------------------------------------------- 2. kinematics on every departure and arrival
const R = makeRouter(G, { stands: S, table: T });
const stands = R.graph.standNames; const L = G.links;
const capLimit = (p, wide) => { const l = L[p.linkId]; if (!l) return null; if (l.for_landing) return ROUTER.caps.rapid; if (l.kind === 'leadin') return ROUTER.caps.leadin; if (l.kind === 'taxilane') return ROUTER.caps.taxilane; if (l.kind === 'push') return ROUTER.caps.push; return wide ? ROUTER.caps.taxiwayWide : ROUTER.caps.taxiway; };
const V = { accel: 0, speed: 0, kindCap: 0, radius: 0, radiusSoft: 0, step: 0, heading: 0, push: 0, lineup60: 0, startup: 0, segs: 0, trajs: 0 };
const steer = [], lineupS = [], taxiS = { dep: [], arr: [] }, buildMs = [];
function segCheck(tr, aAcc, aDec, caps) {
  for (const g of tr.segs) {
    V.segs++; if (g.kind === 'hold') continue; const d = g.s1Cm - g.s0Cm; if (d <= 0) continue;
    const a = (g.v1Cms * g.v1Cms - g.v0Cms * g.v0Cms) / (2 * d);
    if (a > aAcc * 1.02 + 1 || -a > aDec * 1.02 + 1) V.accel++;
    if (caps) for (const c of caps) { if (c.b <= g.s0Cm || c.a >= g.s1Cm) continue; const s0 = Math.max(c.a, g.s0Cm), s1 = Math.min(c.b, g.s1Cm); const va = Math.sqrt(Math.max(0, g.v0Cms ** 2 + 2 * a * (s0 - g.s0Cm))), vb = Math.sqrt(Math.max(0, g.v0Cms ** 2 + 2 * a * (s1 - g.s0Cm))); if (Math.max(va, vb) > c.c + 2) { V.speed++; break; } }
  }
}
const dh = (a, b) => { let d = Math.abs(a - b) % 360; return d > 180 ? 360 - d : d; };
const vhd = (dx, dz) => ((Math.atan2(dx, -dz) * 180 / Math.PI) + 360) % 360;
const K = { yaw: [], yawOver: 0, slipOut: [], slipIn: [], slipInV: 0, steer: [], segV1: 0, segV1Max: 0, segA: 0, segAMax: 0, segs: 0, routeMissing: 0 };
const J = { pushTaxi: [], taxiTo: [], apLd: [], ldTaxi: [], bad: 0, worst: [] };
const SP = { push: [], arr: [], chordArr: [] };
const tan = {};
// fix round 3 (V3-2): every published pose point against its own published speed, on a 0.1 s grid: the reference point
// x / z (the nose-gear station on the centreline) at gs, the displayed main gear at mainGs, the displayed nose gear at noseGs.
// The design §5 kinematics row at 1 s (and 0.5 s): chord <= (the largest published speed in the window) dt + 0.1 m; the
// speeds are not inflated: the path length over 0.5 s (0.1 s chords) >= (the smallest) dt x 0.97 - 0.1 m; main-gear lateral acceleration (main speed x
// yaw rate, windows of >= 1 m or 0.5 s as the verifier's) <= a_lat of the piece under the main gear (1.0 m/s^2, 1.25 on rapid
// exits and the runway lead; + 1 % for the +2 cm/s speed tolerance of the integer legs, D13); yaw rate <= 20 deg/s.
const KN = { win1: 0, win05: 0, over1: { ref: 0, main: 0, nose: 0 }, over05: { ref: 0, main: 0, nose: 0 }, low: { ref: 0, main: 0, nose: 0 }, ratio: { main: 0, nose: 0 },
  latN: 0, latOver: 0, latOver100: 0, latMax: 0, latRel: 0, latEx: '', yawMax: 0, yawEx: '', yawOver: 0, ex: [] };
const D2R_ = Math.PI / 180;
function aLatUnderMain(tr, s, wb) {   // m/s^2: the a_lat of the piece under the main gear (forward taxi: s - wb; push: s + wb)
  const P = tr.path && tr.path.pieces; if (!P || !P.length) return 1; const sm = Math.max(0, Math.min(tr.path.lenCm, tr.kind === 'push' ? s + wb : s - wb));
  const p = P[pieceAt(tr.path, sm)]; return (p.aLatCms2 || 100) / 100;
}
function poseCheck(tr, path, wb, dtMs, zone, key = '') {   // published-speed steps, a_lat, yaw rate, main-gear slip outside / inside the stand alignment zone
  const Gp = []; for (let t = tr.t0; ; t += 100) { const tt = Math.min(t, tr.t1); const p = TJ.evalTraj(tr, tt, {}); p.s = TJ.sAt(tr, tt); Gp.push(p); if (tt >= tr.t1) break; }
  // gs peaks between grid samples: the segment boundary speeds
  const segV = (ta, tb) => { let v = 0; for (const g of tr.segs) { if (g.t1 < ta) continue; if (g.t0 > tb) break; v = Math.max(v, g.v0Cms / 100, g.v1Cms / 100); } return v; };
  const pt = (p, w) => (w === 'ref' ? [p.x, p.z] : w === 'main' ? p.main : p.nose);
  const sp = (p, w) => (w === 'ref' ? p.gs : w === 'main' ? p.mainGs : p.noseGs);
  for (const [m, over, cnt] of [[10, KN.over1, 'win1'], [5, KN.over05, 'win05']]) for (let k = 0; k + m < Gp.length; k++) {
    const A = Gp[k], B = Gp[k + m]; const dt = (B.t - A.t) / 1000; if (dt <= 0) continue; KN[cnt]++;
    for (const w of ['ref', 'main', 'nose']) {
      let vmx = 0, vmn = Infinity; for (let j = k; j <= k + m; j++) { const v = sp(Gp[j], w); if (v > vmx) vmx = v; if (v < vmn) vmn = v; }
      if (w === 'ref') vmx = Math.max(vmx, segV(A.t, B.t));
      const a = pt(A, w), b = pt(B, w); const d = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (d > vmx * dt + 0.1) { over[w]++; if (KN.ex.length < 6) KN.ex.push(key + ' ' + w + ' ' + d.toFixed(2) + ' > ' + (vmx * dt + 0.1).toFixed(2) + ' in ' + dt + ' s'); }
      if (m === 5) { let pl = 0; for (let j = k + 1; j <= k + m; j++) { const p0 = pt(Gp[j - 1], w), p1 = pt(Gp[j], w); pl += Math.hypot(p1[0] - p0[0], p1[1] - p0[1]); }   // the path length (0.1 s chords): the displayed nose path has corners
        if (pl < vmn * dt * 0.97 - 0.1) { KN.low[w]++; if (KN.ex.length < 6) KN.ex.push(key + ' ' + w + ' slow ' + pl.toFixed(2) + ' < ' + (vmn * dt * 0.97 - 0.1).toFixed(2)); } }
    }
    if (m === 10) for (const w of ['main', 'nose']) { const r = sp(B, w) / Math.max(0.5, B.gs); if (B.gs > 0.5 && r > KN.ratio[w]) KN.ratio[w] = r; }
  }
  // lateral acceleration of the displayed main gear and the yaw rate (windows of >= 1 m of the reference point, <= 0.5 s)
  for (let k = 0; k < Gp.length - 1; k++) {
    let m = 1; while (k + m < Gp.length - 1 && m < 5 && Gp[k + m].s - Gp[k].s < 100) m++;
    const A = Gp[k], B = Gp[k + m]; const dt = (B.t - A.t) / 1000; if (dt <= 0) continue;
    const vm = Math.hypot(B.main[0] - A.main[0], B.main[1] - A.main[1]) / dt; const yaw = dh(A.hdg, B.hdg) / dt;
    if (yaw > KN.yawMax) { KN.yawMax = yaw; KN.yawEx = key + ' t=' + B.t; } if (yaw > 20) KN.yawOver++;
    if (vm < 0.5) continue; const lat = vm * yaw * D2R_; const al = aLatUnderMain(tr, (A.s + B.s) / 2, wb); KN.latN++;
    if (lat > KN.latMax) KN.latMax = lat; if (lat / al > KN.latRel) { KN.latRel = lat / al; KN.latEx = key + ' t=' + B.t + ' ' + lat.toFixed(3) + ' m/s^2 at ' + vm.toFixed(1) + ' m/s (a_lat ' + al + ')'; }
    if (lat > al * 1.01) KN.latOver++; if (lat > al) KN.latOver100++;
  }
  // slip and the nose-wheel angle at the round-1 sampling (0.25 s push, 0.5 s taxi)
  const st = Math.max(1, Math.round(dtMs / 100)); let prev = null;
  for (let k = 0; k < Gp.length; k += st) {
    const p = Gp[k]; const sNow = p.s;
    if (prev) {
      const yaw = dh(p.hdg, prev.hdg) / ((p.t - prev.t) / 1000 || 1); K.yaw.push(yaw); if (yaw > 20) K.yawOver++;
      const ex = p.main[0] - prev.main[0], ez = p.main[1] - prev.main[1];
      if (Math.hypot(ex, ez) > 0.05) { let a = dh(vhd(ex, ez), p.hdg); a = Math.min(a, 180 - a); if (zone && zone(sNow)) { K.slipIn.push(a); K.slipInV = Math.max(K.slipInV, p.gs); } else K.slipOut.push(a); }
    }
    K.steer.push(p.steerDeg);
    if (path && p.gs > 0.3) { pointAt(path, sNow, tan); const th = Math.atan2(tan.hx, -tan.hz) * 180 / Math.PI; let a = Math.abs(((th - p.hdg) % 360 + 540) % 360 - 180); if (tr.dir < 0) a = Math.abs(180 - a); steer.push(a); }
    prev = p;
  }
}
function segCons(tr) {   // V7: the segment quadratic ends at v1Cms (<= 1 cm/s) and aCms2 is its acceleration (<= 1 cm/s^2); V8: Traj.route
  if (!('route' in tr)) K.routeMissing++;
  for (const g of tr.segs) { const T = g.t1 - g.t0; if (T <= 0 || g.kind === 'hold') continue; K.segs++; const b = g.v0Cms / 1000, A = (g.s1Cm - g.s0Cm - b * T) / (T * T);
    const vEnd = (b + 2 * A * T) * 1000; const e = Math.abs(vEnd - g.v1Cms); K.segV1Max = Math.max(K.segV1Max, e); if (e > 1) K.segV1++;
    const ea = Math.abs(2 * A * 1e6 - g.aCms2); K.segAMax = Math.max(K.segAMax, ea); if (ea > 1) K.segA++;
    const Ts = T / 1000, ei = Math.abs(g.s0Cm + g.v0Cms * Ts + 0.5 * g.aCms2 * Ts * Ts - g.s1Cm); K.integMax = Math.max(K.integMax || 0, ei); if (ei > 15) K.integBad = (K.integBad || 0) + 1; }
}
const join = (arr, a, b, who) => { const dp = Math.max(Math.hypot(a.x - b.x, a.z - b.z), Math.hypot(a.nose[0] - b.nose[0], a.nose[1] - b.nose[1])), dm = Math.hypot(a.main[0] - b.main[0], a.main[1] - b.main[1]), dhh = dh(a.hdg, b.hdg); arr.push(Math.max(dp, dm)); if (dp > 0.1 || dm > 0.1 || dhh > 1) { J.bad++; if (J.worst.length < 5) J.worst.push(who + ' ' + dp.toFixed(2) + ' m / main ' + dm.toFixed(2) + ' m / ' + dhh.toFixed(2) + ' deg'); } };
const stI = new Map(S.stands.map(x => [x.name, x]));
for (const s of stands) {
  const P = perfOf(refType.get(s)); const wide = P.spanCm >= 3600;
  for (const e of END_IDS) {
    const t0 = performance.now();
    const d = R.departure(s, e, { spanCm: P.spanCm });
    const pt = TJ.pushTraj(d, P, 0); const gt = TJ.groundTraj(d, P, pt.t1); const to = TJ.takeoffTraj(e, d.lineup, P, gt.t1);
    buildMs.push(performance.now() - t0); V.trajs += 3; segCons(pt); segCons(gt); segCons(to);
    // push: <= 1.2 m/s, <= 0.3 m/s^2, 90 s start-up at the end
    for (const g of pt.segs) { if (g.kind === 'hold') { if (g.t1 - g.t0 !== PERF.startupMs) V.startup++; continue; } const dd = g.s1Cm - g.s0Cm; const a = (g.v1Cms * g.v1Cms - g.v0Cms * g.v0Cms) / (2 * dd); if (Math.max(g.v0Cms, g.v1Cms) > PERF.pushCms + 1 || Math.abs(a) > PERF.pushAccCms2 * 1.02 + 1) V.push++; }
    segCheck(gt, P.taxiAccCms2, P.taxiDecCms2, d.pieces.map(p => ({ a: p.s0Cm, b: p.s0Cm + p.lenCm, c: p.vmaxCms })).concat(TJ.turnZones(d, P).map(z => ({ a: z.s0Cm, b: z.s1Cm, c: z.vmaxCms }))));   // fix round 3: + turn and main-gear zones
    for (const p of d.pieces) { const lim = capLimit(p, wide); if (lim != null && p.vmaxCms > lim) V.kindCap++; if (p.kind === 'arc') { if (p.rCm < P.rMinCm) V.radius++; else if (p.rCm < P.rFilletMinCm) V.radiusSoft++; } }
    const pf = TJ.pushFollower(d, P.wheelbaseCm);
    poseCheck(pt, d.push.path, P.wheelbaseCm, 250, (x) => x <= pf.alignCm + 100, s + '>' + e + ' push'); poseCheck(gt, d.path, P.wheelbaseCm, 500, null, s + '>' + e + '/' + P.icao);
    join(J.pushTaxi, TJ.evalTraj(pt, pt.t1, {}), TJ.evalTraj(gt, gt.t0, {}), s + '>' + e + ' push>taxi');
    join(J.taxiTo, TJ.evalTraj(gt, gt.t1, {}), TJ.evalTraj(to, to.t0, {}), s + '>' + e + ' taxi>take-off');
    const p0 = TJ.evalTraj(pt, pt.t0, {}); SP.push.push(dh(p0.hdg, stI.get(s).hdg));
    const tl = gt.t1 - gt.marks.lineupHoldMs; lineupS.push(tl / 1000); if (tl > 60000) V.lineup60++;
    taxiS.dep.push((gt.t1 - gt.t0) / 1000);
  }
  for (const e of END_IDS) {
    const ce = TJ.chooseExit(R, e, s, P, 0.5); const a = ce.route || R.arrival(ce.exit.id, s, { spanCm: P.spanCm });
    const ap = TJ.approachTraj(e, P, 0, { route: a }); const ld = TJ.landingTraj(e, P, 0, { route: a, tdSCm: ap.marks.tdSCm }); if (!ld) continue;
    const ga = TJ.groundTraj(a, P, ld.t1, { vStart: ld.marks.vExitCms }); V.trajs += 3; if (ga.warn.length) V.warn = (V.warn || 0) + 1; segCons(ap); segCons(ld); segCons(ga);
    segCheck(ld, 1e9, P.aDecCms2, null);
    segCheck(ga, P.taxiAccCms2, P.taxiDecCms2, a.pieces.map(p => ({ a: p.s0Cm, b: p.s0Cm + p.lenCm, c: p.vmaxCms })).concat(TJ.turnZones(a, P).map(z => ({ a: z.s0Cm, b: z.s1Cm, c: z.vmaxCms }))));   // + turn and main-gear zones (round 3)
    for (const p of a.pieces) { const lim = capLimit(p, wide); if (lim != null && p.vmaxCms > lim) V.kindCap++; if (p.kind === 'arc') { if (p.rCm < P.rMinCm) V.radius++; else if (p.rCm < P.rFilletMinCm) V.radiusSoft++; } }
    const gf = TJ.gearFollower(a, P.wheelbaseCm);
    poseCheck(ga, a.path, P.wheelbaseCm, 500, (x) => x >= a.lenCm - gf.alignCm - 100, e + ':' + ce.exit.id + '>' + s + '/' + P.icao);
    join(J.apLd, TJ.evalTraj(ap, ap.t1, {}), TJ.evalTraj(ld, ld.t0, {}), s + '<' + ce.exit.id + ' approach>landing');
    join(J.ldTaxi, TJ.evalTraj(ld, ld.t1, {}), TJ.evalTraj(ga, ga.t0, {}), s + '<' + ce.exit.id + ' landing>taxi');
    const pe = TJ.evalTraj(ga, ga.t1, {}); SP.arr.push(dh(pe.hdg, stI.get(s).hdg)); SP.chordArr.push(dh(vhd(pe.x - pe.mainChord[0], pe.z - pe.mainChord[1]), stI.get(s).hdg));
    if (e === '18L' || e === '36R') taxiS.arr.push((ga.t1 - ga.t0) / 1000);
  }
}
info('trajectories checked', V.trajs + ' (push + taxi-out + take-off for 164 stands x 4 ends, approach + landing + taxi-in for 164 x 4 (exit model, u = 0.5), the stand\'s class reference type), ' + V.segs + ' segments; poses on EVERY stand at 0.25 s (push) / 0.5 s (taxi)');
check('accelerations within the caps (taxi +1.0 / -1.5, landing a_dec)', V.accel === 0, V.accel + ' segments over');
check('speeds within the piece caps (link kind, turn sqrt(a_lat R), last 15 m 1 m/s; since round 3 also the turn zones and the main-gear zones)', V.speed === 0, V.speed + ' segments over');
check('piece caps within the link-kind limits (taxiway 12 / 10, lanes 7, lead-in 3, rapid exit 25 m/s)', V.kindCap === 0, String(V.kindCap));
check('turn radius >= R_min (0.27 x wheelbase) for the type using the route', V.radius === 0, V.radius + ' arcs below R_min; ' + V.radiusSoft + ' arcs between R_min and the 1.6 R_min fillet floor');
check('V3-2 / design §5 kinematics row: no step > v dt + 0.1 m at 1 s for EVERY published point at its published speed: the reference point x / z at gs, the displayed main gear at mainGs, the displayed nose gear at noseGs (also at 0.5 s; 0.1 s grid; every stand x end, push + taxi-out + taxi-in)', KN.over1.ref + KN.over1.main + KN.over1.nose + KN.over05.ref + KN.over05.main + KN.over05.nose === 0, '1 s windows ' + KN.win1 + ': ref ' + KN.over1.ref + ', main ' + KN.over1.main + ', nose ' + KN.over1.nose + ' over; 0.5 s windows ' + KN.win05 + ': ' + KN.over05.ref + ' / ' + KN.over05.main + ' / ' + KN.over05.nose + (KN.ex.length ? '; ' + KN.ex.slice(0, 3).join('; ') : ''));
check('V3-2: published speeds not inflated (path length over 0.5 s, 0.1 s chords, >= 0.97 x the smallest published speed x dt - 0.1 m, every point)', KN.low.ref + KN.low.main + KN.low.nose === 0, 'ref ' + KN.low.ref + ', main ' + KN.low.main + ', nose ' + KN.low.nose + '; largest mainGs / gs ' + KN.ratio.main.toFixed(3) + ', noseGs / gs ' + KN.ratio.nose.toFixed(3));
check('V3-2: displayed main gear lateral acceleration (main speed x yaw rate) <= a_lat of the piece under it (1.0 m/s^2, 1.25 on rapid exits / the runway lead; +1 % speed tolerance of the integer legs)', KN.latOver === 0, KN.latOver + ' of ' + KN.latN + ' windows over (' + KN.latOver100 + ' over without the 1 %); max ' + KN.latMax.toFixed(3) + ' m/s^2, max / a_lat ' + KN.latRel.toFixed(3) + ' (' + KN.latEx + ')');
check('V3-2: yaw rate <= 20 deg/s (windows of >= 1 m or 0.5 s)', KN.yawOver === 0, KN.yawOver + ' over; max ' + KN.yawMax.toFixed(2) + ' deg/s (' + KN.yawEx + ')');
check('V2: yaw rate <= 20 deg/s (0.25 s push, 0.5 s taxi; every stand x end)', K.yawOver === 0, K.yawOver + ' samples over; p99 ' + q(K.yaw, 0.99).toFixed(1) + ', max ' + mx(K.yaw).toFixed(1) + ' deg/s');
check('V2: joins push -> taxi -> take-off and approach -> landing -> taxi-in (<= 0.1 m nose and main gear, <= 1 deg; every stand x end)', J.bad === 0, J.bad + ' over; max push>taxi ' + mx(J.pushTaxi).toFixed(3) + ' m, taxi>take-off ' + mx(J.taxiTo).toFixed(3) + ', approach>landing ' + mx(J.apLd).toFixed(3) + ', landing>taxi ' + mx(J.ldTaxi).toFixed(3) + ' m' + (J.worst.length ? '; ' + J.worst.join('; ') : ''));
check('V5: main-gear slip <= 10 deg outside the stand alignment zones (displayed no-slip model; 0.5 s chords)', mx(K.slipOut) <= 10, 'p50 ' + q(K.slipOut, 0.5).toFixed(2) + ', p99 ' + q(K.slipOut, 0.99).toFixed(2) + ', max ' + mx(K.slipOut).toFixed(2) + ' deg over ' + K.slipOut.length + ' samples');
info('V5: slip inside the stand alignment zones (main gear blended onto the lead-in over 2.5 wheelbases + 10 m)', 'p50 ' + q(K.slipIn, 0.5).toFixed(1) + ', p99 ' + q(K.slipIn, 0.99).toFixed(1) + ', max ' + mx(K.slipIn).toFixed(1) + ' deg; ' + K.slipIn.filter(x => x > 10).length + ' of ' + K.slipIn.length + ' samples > 10 deg, speed <= ' + K.slipInV.toFixed(1) + ' m/s');
check('V5: nose-wheel angle <= 75 deg (the steering limit behind R_min = 0.27 wheelbase)', mx(K.steer) <= 75, 'p50 ' + q(K.steer, 0.5).toFixed(1) + ', p99 ' + q(K.steer, 0.99).toFixed(1) + ', max ' + mx(K.steer).toFixed(1) + ' deg');
info('round-0 chord-model nose-wheel angle (path tangent vs heading), for comparison', 'p50 ' + q(steer, 0.5).toFixed(1) + ', p99 ' + q(steer, 0.99).toFixed(1) + ', max ' + mx(steer).toFixed(1) + ' deg');
check('V5: stand poses (push start, arrival stop) within 0.5 deg of the lead-in chord heading', mx(SP.arr.map((x, i) => Math.abs(x - SP.chordArr[i]))) <= 0.5, 'vs the stand heading: push start p99 ' + q(SP.push, 0.99).toFixed(2) + ' max ' + mx(SP.push).toFixed(2) + ' deg, arrival stop p99 ' + q(SP.arr, 0.99).toFixed(2) + ' max ' + mx(SP.arr).toFixed(2) + ' deg (the lead-in data itself: max ' + mx(SP.chordArr).toFixed(2) + ' deg)');
check('V7: segment quadratic ends at v1Cms (<= 1 cm/s) and aCms2 is its acceleration (<= 1 cm/s^2)', K.segV1 === 0 && K.segA === 0, K.segV1 + ' / ' + K.segA + ' of ' + K.segs + ' segments over (max ' + K.segV1Max.toFixed(3) + ' cm/s, ' + K.segAMax.toFixed(3) + ' cm/s^2)');
check('V7: integrating the frozen fields (t0, s0Cm, v0Cms, aCms2) ends within 15 cm of s1Cm (accelerating legs cut into <= 4 s segments, cruises into <= 10 s)', !K.integBad, (K.integBad || 0) + ' segments over; max ' + (K.integMax || 0).toFixed(1) + ' cm');
check('V8: Traj.route present on every trajectory kind (push, ground, approach, landing, take-off)', K.routeMissing === 0, K.routeMissing + ' without');
check('push-back <= 1.2 m/s and <= 0.3 m/s^2; 90 s start-up', V.push === 0 && V.startup === 0, 'push ' + V.push + ', start-up ' + V.startup);
check('line-up within 60 s of the holding position (AIP (mirror) AD 2.20 2.1.5)', V.lineup60 === 0, 'hold -> line-up point p50 ' + q(lineupS, 0.5).toFixed(0) + ' s, max ' + mx(lineupS).toFixed(0) + ' s; ' + V.lineup60 + ' over 60 s');
info('taxi times', 'out p50 ' + q(taxiS.dep, 0.5).toFixed(0) + ' s (p90 ' + q(taxiS.dep, 0.9).toFixed(0) + '), in (18L / 36R) p50 ' + q(taxiS.arr, 0.5).toFixed(0) + ' s (p90 ' + q(taxiS.arr, 0.9).toFixed(0) + '); route + push + taxi + take-off build p50 ' + q(buildMs, 0.5).toFixed(2) + ' ms, max ' + mx(buildMs).toFixed(1) + ' ms');

// ------------------------------------------------------------------------------------------- 3. take-off roll <= TORA - 400 m
{
  let bad = 0, nn = 0; const margin = []; const worst = {};
  for (const e of END_IDS) for (const entry of ['full'].concat(ROUTER.intersection[e] ? [ROUTER.intersection[e]] : [])) {
    // the line-up point furthest into the runway over all stands for this end and entry
    let lu = null; for (const s of stands) { const d = R.departure(s, e, { entry }); if (d && (!lu || d.lineup.toraLeftCm < lu.toraLeftCm)) lu = d.lineup; }
    for (const ty of TYPES_TEST) {
      if (entry !== 'full' && perfOf(ty).spanCm >= 3600) continue;   // intersection: code C only (design §4.2)
      const P = perfOf(ty); const to = TJ.takeoffTraj(e, lu, P, 0); nn++;
      const m = (lu.toraLeftCm - 40000 - to.marks.rollCm) / 100; margin.push(m); if (!to.marks.rollOk) { bad++; } const k = e + '|' + entry; if (worst[k] == null || m < worst[k]) worst[k] = m;
    }
  }
  check('take-off roll <= TORA - 400 m (every type, end and entry; the line-up point furthest in)', bad === 0, bad + ' of ' + nn + '; smallest margin ' + mn(margin).toFixed(0) + ' m (' + Object.entries(worst).map(([k, v]) => k + ' ' + v.toFixed(0)).join(', ') + ')');
}

// ------------------------------------------------------------------------------------------- 4. ROT
{
  const cases = new Map();
  for (const e of END_IDS) {
    const rw = R.graph.ENDS[e].rw;
    const bySide = {}; for (const s of stands) { const sd = R.standSide(s, rw); if (!bySide[sd]) bySide[sd] = s; }
    for (const [sd, s] of Object.entries(bySide)) for (const ty of TYPES_TEST) { const P = perfOf(ty);
      for (const off of [-6000, 0, 6000]) for (const u of [0.1, 0.9]) {
        const c = TJ.chooseExit(R, e, s, P, u, { tdOffsetCm: off }); if (!c.exit) continue;
        const k = [e, sd, ty, c.exit.id, off].join('|'); if (!cases.has(k)) cases.set(k, { rot: c.rotMs, why: c.why, body: P.body, e, off, type: ty });
      } }
  }
  const all = [...cases.values()]; const nom = all.filter(c => c.off === 0);
  const pct = (a) => (a.length ? 100 * a.filter(c => c.rot != null && c.rot <= 50000).length / a.length : NaN);
  const isEast = (c) => c.e === '18L' || c.e === '36R';
  // fix round 3 (lead decision, inf, reversible by the owner): the AIP (mirror) AD 2.20 2.1.4.2 50 s is the NARROW-BODY target
  // on the landing runway of the segregated mode (18L/36R, AD 2.20 2.1.1); 18R/36L and the wide-bodies are reported, not
  // tuned (no ZSSS ROT evidence); the scheduler spaces each arrival with its own computed ROT (chooseExit rotMs)
  const nE = nom.filter(c => c.body === 'narrow' && isEast(c)), nW = nom.filter(c => c.body === 'narrow' && !isEast(c));
  const wE = nom.filter(c => c.body === 'wide' && isEast(c)), wW = nom.filter(c => c.body === 'wide' && !isEast(c));
  const st = (a) => { const r = a.filter(c => c.rot != null).map(c => c.rot / 1000); return 'p50 ' + q(r, 0.5).toFixed(1) + ', p90 ' + q(r, 0.9).toFixed(1) + ', max ' + mx(r).toFixed(1) + ' s'; };
  check('ROT (narrow-body target, AIP (mirror) AD 2.20 2.1.4.2): touchdown -> tail clear of the runway-holding position <= 50 s for >= 90 % of the nominal narrow-body type x chosen-exit cases on 18L/36R (the landing runway of the segregated mode)', pct(nE) >= 90, pct(nE).toFixed(1) + ' % of ' + nE.length + ' cases (' + st(nE) + ')');
  const nulls = all.filter(c => c.rot == null).length; const rots = all.filter(c => c.rot != null).map(c => c.rot / 1000);
  check('every type x end x side has a reachable exit with a route (ROT defined: the scheduler spaces arrivals with chooseExit rotMs)', nulls === 0, nulls + ' without');
  info('ROT report: narrow-bodies on 18R/36L (nominal; landings there only when 18L/36R is unavailable)', pct(nW).toFixed(1) + ' % of ' + nW.length + ' <= 50 s (' + st(nW) + ')');
  info('ROT report: wide-bodies (nominal; reported, not tuned: no ZSSS ROT evidence)', '18L/36R ' + pct(wE).toFixed(1) + ' % of ' + wE.length + ' <= 50 s (' + st(wE) + '); 18R/36L ' + pct(wW).toFixed(1) + ' % of ' + wW.length + ' (' + st(wW) + ')');
  info('ROT report: all nominal cases', pct(nom).toFixed(1) + ' % of ' + nom.length + ' <= 50 s; narrow-bodies all ends ' + pct(nom.filter(c => c.body === 'narrow')).toFixed(1) + ' %, east runway all bodies ' + pct(nom.filter(isEast)).toFixed(1) + ' %');
  info('ROT report: touchdown -60 / 0 / +60 m, all cases (design §5 day-test row "<= 70 s for all", now a report row)', 'p50 ' + q(rots, 0.5).toFixed(1) + ' s, p90 ' + q(rots, 0.9).toFixed(1) + ', max ' + mx(rots).toFixed(1) + '; ' + all.filter(c => c.rot > 70000).length + ' of ' + all.length + ' over 70 s; narrow-bodies on 18L/36R with the spread: ' + pct(all.filter(c => c.body === 'narrow' && isEast(c))).toFixed(1) + ' % <= 50 s, max ' + mx(all.filter(c => c.body === 'narrow' && isEast(c) && c.rot != null).map(c => c.rot / 1000)).toFixed(1) + ' s');
  const over70 = {}; for (const c of all.filter(c => c.rot > 70000)) { const k = c.e + ' ' + c.type; over70[k] = (over70[k] || 0) + 1; }
  const eastAll = all.filter(isEast); const eastMax = mx(eastAll.map(c => c.rot / 1000));
  info('ROT > 70 s (all offsets)', JSON.stringify(over70) + '; east runway (the segregated arrival runway) max ' + eastMax.toFixed(1) + ' s, ' + eastAll.filter(c => c.rot > 70000).length + ' of ' + eastAll.length + ' cases over 70 s');
  const why = {}; for (const c of nom.filter(c => c.rot > 50000)) why[(c.body === 'narrow' ? 'narrow ' : 'wide ') + (isEast(c) ? '18L/36R ' : '18R/36L ') + c.why] = (why[(c.body === 'narrow' ? 'narrow ' : 'wide ') + (isEast(c) ? '18L/36R ' : '18R/36L ') + c.why] || 0) + 1;
  info('ROT > 50 s by body, runway and exit-model branch (nominal)', JSON.stringify(why));
}

// ------------------------------------------------------------------------------------------- 5. glide path, touchdown, climb-out
{
  const slopes = [], tdDev = [], tch = [];
  for (const e of END_IDS) for (const ty of TYPES_TEST) {
    const P = perfOf(ty); const ap = TJ.approachTraj(e, P, 0);
    let prev = null;
    for (let t = ap.t0; t < ap.marks.flareMs; t += 2000) { const p = TJ.evalTraj(ap, t, {}); if (prev) { const ds = Math.hypot(p.x - prev.x, p.z - prev.z); slopes.push(Math.atan2(prev.y - p.y, ds) * 180 / Math.PI); } prev = p; }
    tdDev.push((ap.marks.tdSCm - T.runwayEnds[e].aimSCm) / 100); tch.push(ap.marks.wheelTchCm / 100);
  }
  check('glide path 3.0 +- 0.1 deg (12 km to the flare, every type and end)', mn(slopes) >= 2.9 && mx(slopes) <= 3.1, 'min ' + mn(slopes).toFixed(3) + ', max ' + mx(slopes).toFixed(3) + ' deg (' + slopes.length + ' samples)');
  info('touchdown vs the PAPI abeam point (nominal, before the caller\'s seeded +-60 m)', 'touchdown - PAPI abeam: ' + mn(tdDev).toFixed(0) + ' .. ' + mx(tdDev).toFixed(0) + ' m; wheel height over the threshold ' + mn(tch).toFixed(1) + '-' + mx(tch).toFixed(1) + ' m (eye on the PAPI path: 24.8 / 20.6 m)');
  // V9: the same from the DISPLAYED main gear (pose.main, pose.y): where it touches down and its height over the DTHR
  const tdM = [], thM = []; let flareBefore = 0;
  for (const e of END_IDS) for (const ty of TYPES_TEST) { const P = perfOf(ty); const ap = TJ.approachTraj(e, P, 0); const RE = T.runwayEnds[e]; const al = (x, z) => ((x * 100 - RE.pCm[0]) * RE.h[0] + (z * 100 - RE.pCm[1]) * RE.h[1]);
    let prev = null; for (let t = ap.t0 + Math.max(0, ap.t1 - ap.t0 - 60000); t <= ap.t1; t += 100) { const p = TJ.evalTraj(ap, t, {}); const sm = al(p.main[0], p.main[1]); if (prev && prev.sm < RE.thrSCm && sm >= RE.thrSCm) thM.push(p.y - prof(RE, RE.thrSCm)); prev = { sm }; }
    const pe = TJ.evalTraj(ap, ap.t1, {}); tdM.push((al(pe.main[0], pe.main[1]) - RE.aimSCm) / 100); if (ap.flare.sFl < RE.thrSCm) flareBefore++; }
  check('V9: displayed main gear touches down at the nominal station (-10 .. +70 m from the PAPI abeam point) and crosses the DTHR at >= 12 m', mn(tdM) >= -10 && mx(tdM) <= 70 && mn(thM) >= 12 && flareBefore === 0, 'main gear touchdown ' + mn(tdM).toFixed(1) + ' .. ' + mx(tdM).toFixed(1) + ' m from the PAPI abeam point; main gear over the DTHR ' + mn(thM).toFixed(1) + '-' + mx(thM).toFixed(1) + ' m; flares starting before the DTHR ' + flareBefore);
  const P = perfOf('A320'); const to = TJ.takeoffTraj('36L', { rwySCm: 5000 }, P, 0);
  const pz = TJ.evalTraj(to, to.marks.extentMs, {}); const pf = TJ.evalTraj(to, to.t1, {});
  info('climb-out (A320, 36L)', 'liftoff after ' + ((to.marks.liftoffMs - to.t0) / 1000).toFixed(1) + ' s / ' + (to.marks.rollCm / 100).toFixed(0) + ' m; extent edge after ' + ((to.marks.extentMs - to.t0) / 1000).toFixed(0) + ' s at ' + (pz.y - 2.6).toFixed(0) + ' m AGL; fade 15 km beyond the end after ' + ((to.t1 - to.t0) / 1000).toFixed(0) + ' s at ' + (pf.y - 2.6).toFixed(0) + ' m');
}

// ------------------------------------------------------------------------------------------- 6. determinism, bodies
{
  const R2 = makeRouter(G, { stands: S, table: T }); const P = perfOf('B738');
  let same = 0, nn = 0;
  for (const s of ['101', '233', '271', '404']) for (const e of END_IDS) {
    const a = JSON.stringify(TJ.groundTraj(R.departure(s, e, { spanCm: P.spanCm }), P, 12345).segs), b = JSON.stringify(TJ.groundTraj(R2.departure(s, e, { spanCm: P.spanCm }), P, 12345).segs); nn++; if (a === b) same++;
  }
  check('trajectories deterministic (two routers, identical segments)', same === nn, same + ' / ' + nn);
  // bodies.js fork: degrees, nose tip; two A320s nose to tail 50 m apart on heading 90 do not overlap, wing tips 30 m apart do
  const A3 = TYPES.a320; const b1 = bodyOf(A3, 0, 0, 90), b2 = bodyOf(A3, -50, 0, 90), b3 = bodyOf(A3, -15, 1, 90);   // b3: nose 15 m into b1's fuselage
  const s1 = samples(A3, [0, 0], 90).outline[1];   // tail point: L behind the nose, heading 90 (east) -> at x = -L
  check('bodies.js: degrees and nose-tip placement (forked from sfo3d ground.js)', !overlaps(b1, b2) && overlaps(b1, b3) && Math.abs(s1[0] + A3.L) < 1e-9 && Math.abs(s1[1]) < 1e-9 && clearance(b1, b2) > 10, 'tail at ' + s1.map(v => v.toFixed(2)).join(',') + ', clearance nose-to-tail ' + clearance(b1, b2).toFixed(1) + ' m');
}

console.log('\n' + (failed ? failed + ' FAILED' : 'all passed') + ' (' + n + ' checks)');
process.exit(failed ? 1 : 0);
