// sha3d Phase 3 (P3-B) trajectory tests (node, no browser): tools/sim/test_traj.mjs
//   node tools/sim/test_traj.mjs              # exit 1 on a failed acceptance check
// Checks (design §7.2 P3-B, §4.4, §5): no transcendental Math function on the commit path (route assembly, push / taxi /
// approach / landing / take-off construction, the exit model, time <-> position); kinematics within the §4.4 limits (|a|,
// speeds per link kind, turn radius >= R_min, position steps, heading continuity, push 1.2 m/s / 0.3 m/s^2, line-up within
// 60 s); take-off roll <= TORA - 400 m; ROT from touchdown <= 50 s for >= 90 % of type x exit cases (<= 70 s for all);
// glide path 3.0 +- 0.1 deg; determinism. Prints aggregates only.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { makeRouter, END_IDS, ROUTER } from '../../js/sim/router.js';
import { perfOf, PERF } from '../../js/sim/perf.js';
import * as TJ from '../../js/sim/traj.js';
import { pointAt } from '../../js/sim/path.js';
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
  const commitCalls = total(); const detail = names.filter(k => calls[k]).map(k => k + ' ' + calls[k]).join(', ');
  // the guard must see display evaluation (it uses cos / sin / atan2)
  const P = perfOf('A320'); const d = R.departure('233', '36L'); const gt = TJ.groundTraj(d, P, 0); TJ.evalTraj(gt, 60000); const displayCalls = total() - commitCalls;
  on = false; for (const k of names) Math[k] = orig[k];
  check('no transcendental call on the commit path (router, route assembly, push / taxi / approach / landing / take-off, exit model, time <-> s)', commitCalls === 0, commitCalls + ' calls in ' + built + ' departure + arrival builds' + (detail ? ' (' + detail + ')' : '') + '; the guard sees display evaluation: ' + displayCalls + ' calls in one evalTraj');
  check('the guard works (display evaluation is counted)', displayCalls > 0, String(displayCalls));
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
function poseCheck(tr, path, wb, dtMs = 1000) {
  let prev = null; const tan = {};
  for (let t = tr.t0; t <= tr.t1; t += dtMs) {
    const p = TJ.evalTraj(tr, t, {});
    if (prev) {
      let vmx = Math.max(p.gs, prev.gs); for (const g of tr.segs) if (g.t1 > t - dtMs && g.t0 < t) vmx = Math.max(vmx, g.v0Cms / 100, g.v1Cms / 100);   // the peak between the samples
      const dd = Math.hypot(p.x - prev.x, p.z - prev.z); if (dd > vmx * dtMs / 1000 + 0.1) V.step++;
      let dh = Math.abs(p.hdg - prev.hdg); if (dh > 180) dh = 360 - dh; if (dh > 30 * dtMs / 1000 + 1) V.heading++;
    }
    if (path && p.gs > 0.3) { const s = TJ.sAt(tr, t); pointAt(path, s, tan); const th = Math.atan2(tan.hx, -tan.hz) * 180 / Math.PI; let a = Math.abs(((th - p.hdg) % 360 + 540) % 360 - 180); if (tr.dir < 0) a = Math.abs(180 - a); steer.push(a); }
    prev = p;
  }
}
for (const s of stands) {
  const P = perfOf(refType.get(s)); const wide = P.spanCm >= 3600;
  for (const e of END_IDS) {
    const t0 = performance.now();
    const d = R.departure(s, e, { spanCm: P.spanCm });
    const pt = TJ.pushTraj(d, P, 0); const gt = TJ.groundTraj(d, P, pt.t1);
    buildMs.push(performance.now() - t0); V.trajs += 2;
    // push: <= 1.2 m/s, <= 0.3 m/s^2, 90 s start-up at the end
    for (const g of pt.segs) { if (g.kind === 'hold') { if (g.t1 - g.t0 !== PERF.startupMs) V.startup++; continue; } const dd = g.s1Cm - g.s0Cm; const a = (g.v1Cms ** 2 - g.v0Cms ** 2) / (2 * dd); if (Math.max(g.v0Cms, g.v1Cms) > PERF.pushCms + 1 || Math.abs(a) > PERF.pushAccCms2 * 1.02 + 1) V.push++; }
    segCheck(gt, P.taxiAccCms2, P.taxiDecCms2, d.pieces.map(p => ({ a: p.s0Cm, b: p.s0Cm + p.lenCm, c: p.vmaxCms })));
    for (const p of d.pieces) { const lim = capLimit(p, wide); if (lim != null && p.vmaxCms > lim) V.kindCap++; if (p.kind === 'arc') { if (p.rCm < P.rMinCm) V.radius++; else if (p.rCm < P.rFilletMinCm) V.radiusSoft++; } }
    if (s === stands[0] || stands.indexOf(s) % 8 === 0) { poseCheck(pt, d.push.path, P.wheelbaseCm); poseCheck(gt, d.path, P.wheelbaseCm); }
    const tl = gt.t1 - gt.marks.lineupHoldMs; lineupS.push(tl / 1000); if (tl > 60000) V.lineup60++;
    taxiS.dep.push((gt.t1 - gt.t0) / 1000);
  }
  for (const e of ['18L', '36R']) {
    const ce = TJ.chooseExit(R, e, s, P, 0.5); const a = ce.route || R.arrival(ce.exit.id, s, { spanCm: P.spanCm });
    const ld = TJ.landingTraj(e, P, 0, { route: a }); if (!ld) continue;
    const ga = TJ.groundTraj(a, P, ld.t1, { vStart: ld.marks.vExitCms }); V.trajs += 2; if (ga.warn.length) V.warn = (V.warn || 0) + 1;
    segCheck(ld, 1e9, P.aDecCms2, null);
    segCheck(ga, P.taxiAccCms2, P.taxiDecCms2, a.pieces.map(p => ({ a: p.s0Cm, b: p.s0Cm + p.lenCm, c: p.vmaxCms })).concat(a.zones.map(z => ({ a: z.s0Cm, b: z.s1Cm, c: z.vmaxCms }))));
    for (const p of a.pieces) { const lim = capLimit(p, wide); if (lim != null && p.vmaxCms > lim) V.kindCap++; if (p.kind === 'arc') { if (p.rCm < P.rMinCm) V.radius++; else if (p.rCm < P.rFilletMinCm) V.radiusSoft++; } }
    if (stands.indexOf(s) % 8 === 0) poseCheck(ga, a.path, P.wheelbaseCm);
    taxiS.arr.push((ga.t1 - ga.t0) / 1000);
  }
}
info('trajectories checked', V.trajs + ' (push + taxi-out for 164 stands x 4 ends, landing + taxi-in for 164 x 2, the stand\'s class reference type), ' + V.segs + ' segments; poses at 1 s on every 8th stand');
check('accelerations within the caps (taxi +1.0 / -1.5, landing a_dec)', V.accel === 0, V.accel + ' segments over');
check('speeds within the piece caps (link kind, turn sqrt(a_lat R), last 15 m 1 m/s)', V.speed === 0, V.speed + ' segments over');
check('piece caps within the link-kind limits (taxiway 12 / 10, lanes 7, lead-in 3, rapid exit 25 m/s)', V.kindCap === 0, String(V.kindCap));
check('turn radius >= R_min (0.27 x wheelbase) for the type using the route', V.radius === 0, V.radius + ' arcs below R_min; ' + V.radiusSoft + ' arcs between R_min and the 1.6 R_min fillet floor');
check('no position step > v dt + 0.1 m (1 s)', V.step === 0, String(V.step));
check('heading continuous (no jump > 30 deg/s + 1 deg per 1 s step)', V.heading === 0, String(V.heading));
info('nose-wheel angle (chord model: path tangent vs heading)', 'p50 ' + q(steer, 0.5).toFixed(1) + ', p99 ' + q(steer, 0.99).toFixed(1) + ', max ' + mx(steer).toFixed(1) + ' deg (forward taxi and push)');
check('push-back <= 1.2 m/s and <= 0.3 m/s^2; 90 s start-up', V.push === 0 && V.startup === 0, 'push ' + V.push + ', start-up ' + V.startup);
check('line-up within 60 s of the holding position (AIP (mirror) AD 2.20 2.1.5)', V.lineup60 === 0, 'hold -> line-up point p50 ' + q(lineupS, 0.5).toFixed(0) + ' s, max ' + mx(lineupS).toFixed(0) + ' s; ' + V.lineup60 + ' over 60 s');
info('taxi times', 'out p50 ' + q(taxiS.dep, 0.5).toFixed(0) + ' s (p90 ' + q(taxiS.dep, 0.9).toFixed(0) + '), in p50 ' + q(taxiS.arr, 0.5).toFixed(0) + ' s (p90 ' + q(taxiS.arr, 0.9).toFixed(0) + '); route + push + taxi build p50 ' + q(buildMs, 0.5).toFixed(2) + ' ms, max ' + mx(buildMs).toFixed(1) + ' ms');

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
  const pct = (a) => (100 * a.filter(c => c.rot != null && c.rot <= 50000).length / a.length);
  const east = nom.filter(c => c.e === '18L' || c.e === '36R');
  check('ROT from touchdown <= 50 s for >= 90 % of type x exit cases (nominal touchdown, all four ends)', pct(nom) >= 90, pct(nom).toFixed(1) + ' % of ' + nom.length + ' (east runway 18L/36R ' + pct(east).toFixed(1) + ' %; narrow-bodies ' + pct(nom.filter(c => c.body === 'narrow')).toFixed(1) + ' %, wide-bodies ' + pct(nom.filter(c => c.body === 'wide')).toFixed(1) + ' %)');
  const nulls = all.filter(c => c.rot == null).length; const rots = all.filter(c => c.rot != null).map(c => c.rot / 1000);
  check('every type x end x side has a reachable exit with a route (ROT defined)', nulls === 0, nulls + ' without');
  check('ROT <= 70 s for all type x exit cases (touchdown -60 / 0 / +60 m)', mx(rots) <= 70, 'p50 ' + q(rots, 0.5).toFixed(1) + ' s, p90 ' + q(rots, 0.9).toFixed(1) + ', max ' + mx(rots).toFixed(1) + '; <= 50 s with the +-60 m spread: ' + pct(all).toFixed(1) + ' %');
  const over70 = {}; for (const c of all.filter(c => c.rot > 70000)) { const k = c.e + ' ' + c.type; over70[k] = (over70[k] || 0) + 1; }
  const eastAll = all.filter(c => c.e === '18L' || c.e === '36R'); const eastMax = mx(eastAll.map(c => c.rot / 1000));
  info('ROT > 70 s (all offsets)', JSON.stringify(over70) + '; east runway (the segregated arrival runway) max ' + eastMax.toFixed(1) + ' s, ' + eastAll.filter(c => c.rot > 70000).length + ' of ' + eastAll.length + ' cases over 70 s');
  const why = {}; for (const c of nom.filter(c => c.rot > 50000)) why[c.why] = (why[c.why] || 0) + 1;
  info('ROT > 50 s by exit-model branch (nominal)', JSON.stringify(why));
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
