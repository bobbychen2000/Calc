// sha3d Phase 3 (P3-B) router tests (node, no browser): tools/sim/test_router.mjs
//   node tools/sim/test_router.mjs            # all checks (about 1 min); exit 1 on a failed acceptance check
//   node tools/sim/test_router.mjs --quick    # skip the full-route pavement scan
// Checks (design §7.2 P3-B, §5): route table determinism (two builds, md5) and size; table == live routing; 164 / 164 stands x
// 4 departure and arrival ends; option A for the 14 one-way stands found by rule (runs = optA_push.mjs or shorter); 0 runway-link
// use outside the line-up; 0 off-list crossings; 0 foreign lead-ins; 0 turns > 100 deg; one-way and use rules; end-arounds; the
// F4552 variant; integer pieces vs float lengths (<= 1 cm); option A pushes: swept planform and gear points on pavement for each
// stand's class reference. Fix round 1 (docs/phase3/movement.md "Verification fixes, round 1"): vertex stations, link blocks,
// junction boxes, holds and the push end where the path really is (V1); the path-level turn rule (V3); one-at-a-time lane
// blocks and push resources (V4); wide-body crossings on every exit with real spans (V10); apron_polys in the pavement (V15);
// main-gear pavement for both gear models (V5). Fix round 2 (movement.md "Verification fixes, round 2"): every metre of every
// route inside some block; the links, junction boxes and one-at-a-time lanes geometrically under the push sweep and the
// start-up fuselage in push.resources; lane membership by geometry; the driven push path's turn rule; runway holds on every
// served arrival incl. the opposite side; wide-bodies full length; toraCm in live mode; pavement on three surfaces (drawn,
// load-bearing, halfWidth corridor) for the displayed (oversteered), round-1 tractrix and chord gear models. Prints aggregates only.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { makeRouter, END_IDS, ROUTER } from '../../js/sim/router.js';
import { floatLen, pointAt as pathAt, pieceAt } from '../../js/sim/path.js';
const pieceAtS = (pieces, sc) => pieceAt({ pieces }, sc);
import { perfOf } from '../../js/sim/perf.js';
import { pushTraj, evalTraj, initTraj, gearFollower, followAt, noseAt, runwayGeom } from '../../js/sim/traj.js';
import { gearOf, sweptSamples } from '../../js/sim/bodies.js';
import { TYPES, ICAO_TYPES } from '../../js/aircraft/types.js';

const HERE = path.dirname(fileURLToPath(import.meta.url)), ROOT = path.resolve(HERE, '../..');
const QUICK = process.argv.includes('--quick');
const rd = (f) => JSON.parse(fs.readFileSync(path.join(ROOT, 'data', f)));
const G = rd('sha_taxigraph.json'), S = rd('sha_stands.json'), A = rd('sha_airport.json'), B3 = rd('sha_buildings3d.json');
const results = []; let failed = 0;
const check = (name, ok, detail) => { results.push({ name, ok, detail }); if (!ok) failed++; console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? '  -- ' + detail : '')); };
const info = (name, detail) => console.log('INFO ' + name + '  -- ' + detail);
const mx = (a) => a.reduce((m, x) => (x > m ? x : m), -Infinity), mn = (a) => a.reduce((m, x) => (x < m ? x : m), Infinity);
const q = (a, p) => { if (!a.length) return NaN; const s = a.slice().sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.floor(p * (s.length - 1) + 0.5))]; };

// ------------------------------------------------------------------------------------------- 1. table: determinism, size
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'sha_routes_'));
const md5 = (f) => crypto.createHash('md5').update(fs.readFileSync(f)).digest('hex');
for (const k of ['a', 'b']) execFileSync(process.execPath, [path.join(HERE, 'build_routes.mjs'), '--out', path.join(tmp, k), '--quiet']);
const ha = md5(path.join(tmp, 'a/sha_routes.json')), hb = md5(path.join(tmp, 'b/sha_routes.json')), hc = md5(path.join(ROOT, 'data/sha_routes.json'));
check('route table deterministic (two builds, md5)', ha === hb, ha + ' / ' + hb);
check('committed data/sha_routes.json is up to date', ha === hc, 'built ' + ha + ', data ' + hc);
const jsTxt = fs.readFileSync(path.join(ROOT, 'data/sha_routes.js'), 'utf8');
check('sha_routes.js wraps the same JSON', jsTxt.includes('window.SHA_ROUTES = ' + fs.readFileSync(path.join(ROOT, 'data/sha_routes.json'), 'utf8') + ';'), '');
const size = fs.statSync(path.join(ROOT, 'data/sha_routes.json')).size;
check('route table <= 0.6 MB', size <= 600 * 1024, (size / 1024).toFixed(1) + ' kB (.js ' + (fs.statSync(path.join(ROOT, 'data/sha_routes.js')).size / 1024).toFixed(1) + ' kB)');
fs.rmSync(tmp, { recursive: true, force: true });
const T = rd('sha_routes.json');
initTraj(T);

// ------------------------------------------------------------------------------------------- 2. routers
const RL = makeRouter(G, { stands: S, live: true });
const RT = makeRouter(G, { stands: S, table: T });
check('router uses the table', RT.info().variant === 'base', RT.info().table);
const RVT = makeRouter(G, { stands: S, table: T, closedLinks: T.variants.F4552.closedLinks, crossOnly: T.variants.F4552.crossOnly });
const RVL = makeRouter(G, { stands: S, live: true, closedLinks: T.variants.F4552.closedLinks, crossOnly: T.variants.F4552.crossOnly });
check('router recognises the F4552 closure set', RVT.info().variant === 'F4552', RVT.info().table);
const stands = RL.graph.standNames; const L = G.links; const nodeOf = RL.graph.nodeOf;
const span = new Map(S.stands.map(s => [s.name, Math.round((s.span_max || 36) * 100)]));

// ------------------------------------------------------------------------------------------- 3. coverage + table == live
let depOk = 0, depN = 0, arrOk = 0, arrN = 0, mism = 0, mismV = 0; const depFail = [], arrFail = [];
const sameSeq = (a, b) => { if (a && a.seq) { if (!b || !b.seq || a.nPush !== b.nPush || a.swing !== b.swing) return false; a = a.seq; b = b.seq; } return (!a && !b) || (a && b && a.length === b.length && a.every((x, i) => x[0] === b[i][0] && x[1] === b[i][1])); };
for (const s of stands) {
  for (const e of END_IDS) {
    depN++; const r = RT.departure(s, e); if (r) depOk++; else depFail.push(s + '>' + e);
    const ent = ['full'].concat(ROUTER.intersection[e] ? [ROUTER.intersection[e]] : []);
    for (const en of ent) { if (!sameSeq(RT._search.depSeq(s, e, en), RL._search.depSeq(s, e, en))) mism++; if (e === '18R' || e === '36L') if (!sameSeq(RVT._search.depSeq(s, e, en), RVL._search.depSeq(s, e, en))) mismV++; }
    const side = RT.standSide(s, RT.graph.ENDS[e].rw);
    const ex = RT.exits(e, true).filter(x => x.side === side); arrN++;
    if (ex.some(x => RT.arrival(x.id, s))) arrOk++; else arrFail.push(s + '<' + e);
    for (const x of ex) for (const cls of ['n', 'w', 'x']) {
      if (cls !== 'n' && span.get(s) < (cls === 'w' ? 3600 : 6500)) continue;
      if (!sameSeq(RT._search.arrSeq(x.id, s, cls), RL._search.arrSeq(x.id, s, cls))) mism++;
      if (e === '18R' || e === '36L') if (!sameSeq(RVT._search.arrSeq(x.id, s, cls), RVL._search.arrSeq(x.id, s, cls))) mismV++;
    }
  }
}
check('departures: 164 stands x 4 take-off ends', depOk === depN && depN === 656, depOk + ' / ' + depN + (depFail.length ? ' failed ' + depFail.slice(0, 8).join(' ') : ''));
check('arrivals: 164 stands x 4 landing ends (an exit on the stand side)', arrOk === arrN && arrN === 656, arrOk + ' / ' + arrN + (arrFail.length ? ' failed ' + arrFail.slice(0, 8).join(' ') : ''));
check('table link sequences == live routing (base)', mism === 0, mism + ' mismatches');
check('table link sequences == live routing (F4552 variant)', mismV === 0, mismV + ' mismatches');

// ------------------------------------------------------------------------------------------- 4. option A by rule
const REF_OPTA = {   // optA_push.mjs (design scratch, rev. 2) result: stand -> [run links, swing link]
  218: [[1016], 823], 219: [[1016], 823], 225: [[1003], 827], 226: [[1003], 827], 227: [[991], 829], '238A': [[1149, 1148], 839], 239: [[1006], 836],
  240: [[1007, 1006], 836], '240A': [[1007, 1006], 836], 271: [[957], 815], 272: [[957], 815], 278: [[963], 812], 279: [[964, 963], 812], 280: [[964, 963], 812] };
const oa = stands.filter(s => RL.optionA(s)); let sameRuns = 0, shorter = 0, longer = 0; const turnDeg = [], runM = [], pushM = [];
for (const s of oa) {
  const r = RL.optionA(s); const ref = REF_OPTA[s]; const lenRun = (ids) => ids.reduce((a, id) => a + L[id].len, 0);
  if (ref && ref[0].join() === r.run.join() && ref[1] === r.swing) sameRuns++; else if (ref && lenRun(r.run) < lenRun(ref[0])) shorter++; else longer++;
  turnDeg.push(r.turnDeg); runM.push(r.runCm / 100);
  const d = RT.departure(s, '18R'); pushM.push(d.push.lenCm / 100);
  // every run link two-way, swing link one-way (the reason), all four ends reachable
  if (!r.run.every(id => L[id].dir === 'both')) longer++;
}
check('option A: the 14 one-way stands found by rule', oa.length === 14 && oa.every(s => s in REF_OPTA), oa.length + ' stands: ' + oa.join(' '));
check('option A runs = optA_push.mjs or shorter', longer === 0, sameRuns + ' same, ' + shorter + ' shorter, ' + longer + ' other');
info('option A', 'run ' + mn(runM).toFixed(1) + '-' + mx(runM).toFixed(1) + ' m (total ' + runM.reduce((a, b) => a + b, 0).toFixed(1) + ' m), push-turn ' + mn(turnDeg) + '-' + mx(turnDeg) + ' deg, push length ' + mn(pushM).toFixed(0) + '-' + mx(pushM).toFixed(0) + ' m (median ' + q(pushM, 0.5).toFixed(0) + ')');

// ------------------------------------------------------------------------------------------- 5. rule checks on every route
const CROSS_OK = { '18R/36L': ['H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'H7'], '18L/36R': ['H1', 'H4', 'H7'] };
const COS100 = Math.cos(100 * Math.PI / 180);
const turnsSet = new Set(); for (const [n, pairs] of Object.entries(G.turns)) for (const [a, b] of pairs) turnsSet.add(n + ':' + a + ':' + b);
const allRoutes = [];   // [router, route, variant]
for (const [R, vr] of [[RT, 'base'], [RVT, 'F4552']]) {
  for (const s of stands) for (const e of END_IDS) {
    if (vr === 'F4552' && !(e === '18R' || e === '36L')) continue;
    for (const en of ['full'].concat(ROUTER.intersection[e] ? [ROUTER.intersection[e]] : [])) { const r = R.departure(s, e, { entry: en }); if (r) allRoutes.push([R, r, vr]); }
    const side = R.standSide(s, R.graph.ENDS[e].rw);
    for (const x of R.exits(e, true).filter(x => x.side === side)) for (const sp of [0, 3600, 6500]) { if (sp && span.get(s) < sp) continue; const r = R.arrival(x.id, s, { spanCm: sp }); if (r) allRoutes.push([R, r, vr]); }
  }
}
let rwyUse = 0, offList = 0, foreign = 0, turn100 = 0, notInTurns = 0, oneWay = 0, useBad = 0, spanBad = 0, pieceErr = 0, pieceMax = 0, sumBad = 0, nPieces = 0, lenTab = 0, holdBad = 0, blockBad = 0;
const maxTurn = []; let nTrans = 0, nRoutes = 0; const lens = { dep: [], arr: [] }; const rMinArc = []; const xDep = { 0: 0, 1: 0, 2: 0 };
const pushMotion = [], pushSwing = []; let pushRuns = 0, pushNoRun = 0, pushFb = 0;
for (const [R, r, vr] of allRoutes) {
  nRoutes++;
  const seq = r.links; const role = r.kind; const nPush = r.push ? r.push.nLinks : 0;
  for (let i = 0; i < seq.length; i++) {
    const [lid, from] = seq[i]; const l = L[lid];
    if (l.use === 'runway') rwyUse++;
    if (l.use === 'stand' && l.stand !== r.stand) foreign++;
    if (l.kind === 'push' && i !== 0) useBad++;
    if ((l.use === 'arrival' && role !== 'arr') || (l.use === 'departure' && role !== 'dep')) useBad++;
    if (r.cls === 'x' && ROUTER.endAround.includes(l.ref)) spanBad++;
    const can = l.dir === 'both' || (l.dir === 'ab' && l.a === from);
    if (!can && !(i < nPush && l.kind === 'push')) oneWay++;
    if (i === 0) continue;
    const [pl, pf] = seq[i - 1]; const v = from;
    const din = R.graph.dirOut(pl, v), dout = R.graph.dirOut(lid, v); const c = -(din[0] * dout[0] + din[1] * dout[1]);
    const ang = Math.acos(Math.max(-1, Math.min(1, c))) * 180 / Math.PI;
    if (i < nPush) { pushMotion.push(ang); continue; }   // pushed links: the tail-first motion turns along the run
    if (i === nPush && nPush > 0) continue;                    // the forward start at K: checked below against the swing branch
    nTrans++; maxTurn.push(ang); if (c < COS100) turn100++;
    if (!turnsSet.has(v + ':' + pl + ':' + lid)) notInTurns++;
    const n = nodeOf[v]; if (n.kind === 'rwy' && L[pl].use !== 'runway' && l.use !== 'runway') { const okRefs = vr === 'F4552' && T.variants.F4552.crossOnly[n.runway] ? T.variants.F4552.crossOnly[n.runway] : CROSS_OK[n.runway]; if (!okRefs.includes(l.ref)) offList++; }
  }
  // the first taxi transition after the push is geometric (<= 100 deg from the reverse of the swing branch), checked here
  if (r.push && r.push.swing != null) { const J = r.push.node; const hx = R.graph.dirOut(r.push.swing, J); const d = R.graph.dirOut(seq[nPush][0], J); const c = -(hx[0] * d[0] + hx[1] * d[1]); maxTurn.push(Math.acos(Math.max(-1, Math.min(1, c))) * 180 / Math.PI); if (c < COS100) turn100++; pushSwing.push(r.push.run.turnDeg); if (r.push.run.run.length) pushRuns++; else pushNoRun++; }
  if (r.push && r.push.fallback) pushFb++;
  // integer pieces vs floats
  let sum = 0; for (const p of r.pieces) { nPieces++; const fl = floatLen(p); const d = Math.abs(fl - p.lenCm); if (!p.cut && d > 1) pieceErr++; if (!p.cut) pieceMax = Math.max(pieceMax, d); sum += p.lenCm; if (p.kind === 'arc') rMinArc.push(p.rCm / 100); }
  if (sum !== r.lenCm) sumBad++;
  if (r.push) for (const p of r.push.pieces) { nPieces++; const d = Math.abs(floatLen(p) - p.lenCm); if (d > 1) pieceErr++; pieceMax = Math.max(pieceMax, d); }
  // holds / blocks sanity
  if (r.kind === 'dep' && !r.holds.some(h => h.kind === 'lineup')) holdBad++;
  if (r.kind === 'arr' && (!r.holds.some(h => h.kind === 'leadin') || !r.vacate)) holdBad++;
  for (const c of r.crossings) if (!r.holds.some(h => h.kind === 'rwyhold' && h.node === c.node && h.sCm <= c.sCm)) holdBad++;
  for (const b of r.blocks) if (!(b.s0Cm >= 0 && b.s1Cm <= r.lenCm && b.s0Cm <= b.s1Cm)) blockBad++;
  if (vr === 'base' && r.cls === 'n') { (r.kind === 'dep' ? lens.dep : lens.arr).push(r.lenCm / 100); if (r.kind === 'dep' && (r.end === '18R' || r.end === '36L') && r.entry === 'full') { const n = r.crossings.filter(c => c.runway === '18L/36R').length; xDep[n] = (xDep[n] || 0) + 1; } }
}
// table lengths
for (const [k, g] of Object.entries(T.groups)) {
  const [kind, a, b, vr] = k.split('|'); const R = vr === 'base' ? RT : RVT;
  for (let i = 0; i < T.stands.length; i++) { if (g.leaf[i] < 0) continue; const s = T.stands[i];
    if (kind === 'dep') { if (g.lenN[i] !== R.departure(s, a, { entry: b, geom: 'narrow' }).lenCm || g.lenW[i] !== R.departure(s, a, { entry: b, geom: 'wide' }).lenCm) lenTab++; }
    else { const sp = b === 'n' ? 0 : b === 'w' ? 3600 : 6500; const r = R.arrival(a, s, { spanCm: sp, geom: 'narrow' }); if (!r) { lenTab++; continue; } if (g.lenN[i] !== r.lenCm) lenTab++; if (g.lenW[i] !== R.arrival(a, s, { spanCm: sp, geom: 'wide' }).lenCm) lenTab++; } }
}
info('routes checked', nRoutes + ' (departures and arrivals, both variants, all span classes), ' + nTrans + ' taxi transitions, ' + nPieces + ' pieces');
check('0 runway-link use outside the line-up', rwyUse === 0, rwyUse + ' (the line-up and the arrival roll lead are runway centreline pieces, not taxi links)');
check('0 off-list runway crossings', offList === 0, offList + ' (18R/36L: H1-H7; 18L/36R: H1, H4, H7; F4552 / F4551: H4, H7)');
check('0 foreign lead-ins', foreign === 0, String(foreign));
check('0 turns > 100 deg', turn100 === 0, turn100 + '; max taxi turn ' + mx(maxTurn).toFixed(1) + ' deg, p99 ' + q(maxTurn, 0.99).toFixed(1));
check('every taxi transition is in the committed turns table', notInTurns === 0, notInTurns + ' outside (option A geometric starts excluded)');
check('one-way and use rules (arrival-only / departure-only, push first)', oneWay === 0 && useBad === 0, 'one-way ' + oneWay + ', use ' + useBad);
check('span >= 65 m never on an end-around', spanBad === 0, String(spanBad));
check('baked integer pieces = float length within 1 cm per piece', pieceErr === 0, pieceErr + ' of ' + nPieces + ' pieces > 1 cm (max ' + pieceMax.toFixed(3) + ' cm); route sum mismatches ' + sumBad);
check('table route lengths (narrow / wide geometry) == runtime rebuild', lenTab === 0, lenTab + ' mismatches');
check('holds: line-up hold per departure, lead-in hold + vacate per arrival, a runway hold before every crossing', holdBad === 0, String(holdBad));
check('blocks inside [0, route length]', blockBad === 0, String(blockBad));
info('route lengths', 'departures median ' + q(lens.dep, 0.5).toFixed(0) + ' m, p90 ' + q(lens.dep, 0.9).toFixed(0) + ', max ' + Math.max(...lens.dep).toFixed(0) + '; arrivals median ' + q(lens.arr, 0.5).toFixed(0) + ' m, p90 ' + q(lens.arr, 0.9).toFixed(0) + ', max ' + Math.max(...lens.arr).toFixed(0));
info('departures to 18R / 36L crossing 18L/36R', JSON.stringify(xDep));
info('fillet radii', 'arcs ' + rMinArc.length + ', min ' + mn(rMinArc).toFixed(1) + ' m, p01 ' + q(rMinArc, 0.01).toFixed(1) + ', p10 ' + q(rMinArc, 0.1).toFixed(1) + ' m; below the B77W fillet floor 1.6 x 0.27 x wheelbase (' + (perfOf('B77W').rFilletMinCm / 100).toFixed(1) + ' m): ' + rMinArc.filter(r => r < perfOf('B77W').rFilletMinCm / 100).length + ', below the A321 floor (' + (perfOf('A321').rFilletMinCm / 100).toFixed(1) + ' m): ' + rMinArc.filter(r => r < perfOf('A321').rFilletMinCm / 100).length);
check('push motion turns <= 100 deg (tail first over the run) and push-turns <= 100 deg', mx(pushMotion) <= 100 && mx(pushSwing) <= 100, 'run motion turns max ' + mx(pushMotion).toFixed(1) + ' deg; push-turn (swing) max ' + mx(pushSwing).toFixed(1) + ' deg, p50 ' + q(pushSwing, 0.5).toFixed(0));
check('every departure has a geometric push (tail-first run + swing), no graph fallback', pushFb === 0, pushRuns + ' with a run of 1-2 lanes, ' + pushNoRun + ' swinging at the lead-in fork, ' + pushFb + ' fallbacks');

// ------------------------------------------------------------------------------------------- 5b. fix round 1: where the path is
// Independent float geometry (path.js pointAt sampling, link polylines from the taxi graph), over every route served above.
{
  const t0 = performance.now();
  const holdPts = []; for (const h of A.holds) holdPts.push([h.x, h.z, h.runway]); for (const h of G.hold_inf) holdPts.push([h.x, h.z, h.runway]);
  const RWF = {}; for (const r of A.runways) { const a = r.ends[0].end.xz, b = r.ends[1].end.xz; const dx = b[0] - a[0], dz = b[1] - a[1], l = Math.hypot(dx, dz); RWF[r.id] = { p: a, n: [-dz / l, dx / l] }; }
  const latOf = (rw, x, z) => Math.abs((x - RWF[rw].p[0]) * RWF[rw].n[0] + (z - RWF[rw].p[1]) * RWF[rw].n[1]);
  const LC = new Map(); const lc = (lid) => { let c = LC.get(lid); if (c) return c; const P = L[lid].pts; const cum = [0]; let x0 = 1e9, z0 = 1e9, x1 = -1e9, z1 = -1e9;
    for (let i = 0; i < P.length; i++) { if (i) cum.push(cum[i - 1] + Math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1])); x0 = Math.min(x0, P[i][0]); x1 = Math.max(x1, P[i][0]); z0 = Math.min(z0, P[i][1]); z1 = Math.max(z1, P[i][1]); }
    c = { P, cum, bb: [x0, z0, x1, z1] }; LC.set(lid, c); return c; };
  const segD = (lid, x, z, f0 = 0, f1 = 1) => {   // distance (m) from (x, z) to the part [f0, f1] (length fractions) of link lid
    const { P, cum, bb } = lc(lid); const tot = cum[cum.length - 1];
    if (x < bb[0] - 30 || x > bb[2] + 30 || z < bb[1] - 30 || z > bb[3] + 30) return 99;
    let bd = Infinity; for (let i = 1; i < P.length; i++) { let ta = (f0 * tot - cum[i - 1]) / (cum[i] - cum[i - 1] || 1), tb = (f1 * tot - cum[i - 1]) / (cum[i] - cum[i - 1] || 1); ta = Math.max(0, ta); tb = Math.min(1, tb); if (tb < ta) continue;
      const a = P[i - 1], b = P[i]; const ex = b[0] - a[0], ez = b[1] - a[1]; let t = ((x - a[0]) * ex + (z - a[1]) * ez) / (ex * ex + ez * ez || 1); t = Math.max(ta, Math.min(tb, t)); bd = Math.min(bd, Math.hypot(a[0] + ex * t - x, a[1] + ez * t - z)); }
    return bd; };
  const nearestS = (path, x, z, lo, hi) => { let best = lo, bd = Infinity, q = {}; for (let sc = lo; sc <= hi; sc += 200) { pathAt(path, sc, q); const d = (q.x - x) * (q.x - x) + (q.z - z) * (q.z - z); if (d < bd) { bd = d; best = sc; } }
    for (let sc = Math.max(lo, best - 200); sc <= Math.min(hi, best + 200); sc += 10) { pathAt(path, sc, q); const d = (q.x - x) * (q.x - x) + (q.z - z) * (q.z - z); if (d < bd) { bd = d; best = sc; } } return { s: best, d: Math.sqrt(bd) / 100 }; };
  const V1 = { verts: 0, vErr: 0, vErrMax: 0, blocks: 0, blkBad: 0, blkCut: 0, blk12: 0, boxes: 0, boxBad: 0, holds: 0, holdBad: 0, vac: 0, vacBad: 0, pushK: 0, pushKBad: 0, pathM: 0, uncovM: 0, ex: [] };
  const V3 = { routes: 0, arcMax: 0, winMax: 0, bad: 0, ex: [] };
  const V4 = { laneM: 0, laneUncovM: 0, pushLane: 0, pushLaneMissing: 0 };
  const q = {};
  let nGeo = 0;
  for (const [R, r, vr] of allRoutes) {
    if (vr !== 'base' || r.cls !== 'n') continue; nGeo++;   // base variant, span class n (both geometries' links are the same)
    const P = r.path, len = r.lenCm; const seq = r.links; const nPush = r.push ? r.push.nLinks : 0;
    // path samples every 1 m: position and heading
    const S = []; for (let sc = 0; sc <= len; sc += 100) { pathAt(P, sc, q); S.push([sc, q.x / 100, q.z / 100, Math.atan2(q.hx, -q.hz)]); }
    // V1 a: vertex stations of the graph nodes (nearest path point within +-150 m of vS, where the node is within 25 m of the path)
    for (let k = 0; k < r.verts.length; k++) { const v = r.verts[k]; if (v.node == null) continue; const pr = nearestS(P, v.x, v.z, Math.max(0, r.vS[k] - 15000), Math.min(len, r.vS[k] + 15000)); if (pr.d > 25) continue;
      V1.verts++; const e = Math.abs(pr.s - r.vS[k]) / 100; V1.vErrMax = Math.max(V1.vErrMax, e); if (e > 1) { V1.vErr++; if (V1.ex.length < 4) V1.ex.push('vertex ' + r.kind + ' ' + r.stand + ' node ' + v.node + ' ' + e.toFixed(1) + ' m'); } }
    // V1 b: link blocks where the path runs along the block's own part of its link (+-15 m), unless the fillet cuts that part
    const routeLinks = new Set(seq.slice(nPush).map(x => x[0])); if (r.push && r.push.swing != null) routeLinks.add(r.push.swing); if (r.push) for (const [c] of r.push.chain) routeLinks.add(c);
    for (const b of r.blocks) { if (b.kind !== 'link' || b.behind || b.geo) continue; V1.blocks++;   // (behind: under the start-up fuselage at s = 0; geo: gap fill)
      const l = L[b.link]; const nb = Math.max(1, Math.floor(Math.round(l.len * 100) / ROUTER.blockMinCm)); const k = +b.id.split(':')[2]; const f0 = k / nb, f1 = (k + 1) / nb;
      // the contiguous stretch of near samples (<= 12 m from the block's part; gaps < 4 m) that overlaps the block window +-16 m
      // (fix round 2: a route can pass the same part of a link twice, e.g. the swing chain at the start and a parallel lane later)
      const nearAll = S.filter(p => p[0] >= b.s0Cm - 20000 && p[0] <= b.s1Cm + 20000 && segD(b.link, p[1], p[2], f0, f1) < 12).map(p => p[0]);
      const runsN = []; for (const sc of nearAll) { const lr = runsN[runsN.length - 1]; if (lr && sc - lr[1] <= 400) lr[1] = sc; else runsN.push([sc, sc]); }
      const hit = runsN.filter(([u, v]) => v >= b.s0Cm - 1600 && u <= b.s1Cm + 1600); const near = hit.length ? [hit[0][0], hit[hit.length - 1][1]] : [];
      const inWin = S.filter(p => p[0] >= b.s0Cm && p[0] <= b.s1Cm); if (inWin.length > 3 && inWin.filter(p => segD(b.link, p[1], p[2]) < 12).length / inWin.length < 0.5) V1.blk12++;
      if (!near.length) { V1.blkCut++; continue; }
      const e0 = near[0], e1 = near[near.length - 1];
      const tol = 1500 + 100; if (!(Math.abs(b.s0Cm - e0) <= tol || b.s0Cm === 0) || !(Math.abs(b.s1Cm - e1) <= tol || b.s1Cm === len)) { V1.blkBad++; if (V1.ex.length < 8) V1.ex.push('block ' + b.id + ' ' + r.kind + ' ' + r.stand + ' [' + b.s0Cm + ', ' + b.s1Cm + '] vs path along it [' + e0 + ', ' + e1 + ']'); } }
    //   coverage: path metres within 8 m of exactly the route link they are nearest to, outside every block of that link
    for (const p of S) { let lk = null, bd = 8; for (const id of routeLinks) { const d = segD(id, p[1], p[2]); if (d < bd) { bd = d; lk = id; } } if (lk == null) continue; V1.pathM++;
      if (!r.blocks.some(b => b.kind === 'link' && b.link === lk && p[0] >= b.s0Cm - 100 && p[0] <= b.s1Cm + 100)) V1.uncovM++; }
    // V1 c: every junction box contains the path point nearest its node
    for (const b of r.blocks) { if (b.kind !== 'box') continue; V1.boxes++;   // (behind boxes included since their windows run to the end of the near start stretch)
      const n = nodeOf[b.node]; const pr = nearestS(P, n.x * 100, n.z * 100, Math.max(0, b.s0Cm - 15000), Math.min(len, b.s1Cm + (b.behind ? 1500 : 15000)));   // (a route can pass a node twice: the local nearest; a behind box is the start's pass)
      if (!(pr.s >= b.s0Cm - 100 && pr.s <= b.s1Cm + 100)) { V1.boxBad++; if (V1.ex.length < 10) V1.ex.push('box ' + b.id + ' ' + r.kind + ' ' + r.stand + ' [' + b.s0Cm + ', ' + b.s1Cm + '] nearest ' + pr.s); } }
    // V1 d: holds at a runway-holding position (5 m) or 90 +- 2 m from the centreline; the arrival's vacate point likewise
    const atHold = (sc, rw) => { pathAt(P, sc, q); const x = q.x / 100, z = q.z / 100; const dmin = Math.min(...holdPts.filter(h => h[2] === rw).map(h => Math.hypot(h[0] - x, h[1] - z))); return dmin <= 5 || Math.abs(latOf(rw, x, z) - 90) <= 2; };
    for (const h of r.holds) { if (!h.runway) continue; V1.holds++; if (!atHold(h.sCm, h.runway)) V1.holdBad++; }
    if (r.kind === 'arr') { V1.vac++; if (!atHold(r.vacate.sCm, R.graph.ENDS[r.end].rw)) V1.vacBad++; }
    // V1 e: the push ends beyond K (the swing junction)
    if (r.push) { V1.pushK++; const n = nodeOf[r.push.node]; const pr = nearestS(r.push.path, n.x * 100, n.z * 100, 0, r.push.path.lenCm); if (pr.s > r.push.lenCm + 50) V1.pushKBad++; }
    // V3: the driven path's turns (own float heading, 1 m samples): any single arc and any 40 m window <= 100 deg
    V3.routes++; let arc = 0; for (const p of r.pieces) if (p.kind === 'arc') arc = Math.max(arc, p.g.th * 180 / Math.PI);
    const u = [S[0][3]]; for (let i = 1; i < S.length; i++) { let d = S[i][3] - S[i - 1][3]; while (d > Math.PI) d -= 2 * Math.PI; while (d < -Math.PI) d += 2 * Math.PI; u.push(u[i - 1] + d); }
    let win = 0; for (let i = 0; i + 40 < u.length; i++) win = Math.max(win, Math.abs(u[i + 40] - u[i]) * 180 / Math.PI);
    V3.arcMax = Math.max(V3.arcMax, arc); V3.winMax = Math.max(V3.winMax, win); if (arc > 100 || win > 100.5) { V3.bad++; if (V3.ex.length < 4) V3.ex.push(r.kind + ' ' + r.stand + ' ' + (r.end || '') + ' arc ' + arc.toFixed(1) + ' win ' + win.toFixed(1)); }
    // V4: every metre on a piece whose in- or out-link is a one-at-a-time lane lies inside a lane block of that ref
    for (const p of S) { const pc = r.pieces[pieceAtS(r.pieces, p[0])]; const refs = [pc.linkId, pc.kind === 'arc' && pc.tagOut ? pc.tagOut.link : null].filter(x => x != null).map(id => L[id].ref).filter(rf => rf && ROUTER.exclusiveLanes.includes(rf));
      for (const rf of new Set(refs)) { V4.laneM++; if (!r.blocks.some(b => b.kind === 'lane' && b.id === 'lane:' + rf && p[0] >= b.s0Cm && p[0] <= b.s1Cm)) V4.laneUncovM++; } }
    if (r.push) { const refs = new Set(seq.slice(1, nPush).map(([id]) => L[id].ref).concat(r.push.swing != null ? [L[r.push.swing].ref] : []).filter(rf => rf && ROUTER.exclusiveLanes.includes(rf)));
      for (const rf of refs) { V4.pushLane++; if (!r.push.resources.includes('lane:' + rf)) V4.pushLaneMissing++; } }
  }
  check('V1: vertex stations = where the path passes the graph node (nearest point, <= 1 m)', V1.vErr === 0, V1.vErr + ' of ' + V1.verts + ' node vertices off by > 1 m (max ' + V1.vErrMax.toFixed(2) + ' m)');
  check('V1: link blocks where the path runs along their part of the link (+-16 m; parts cut off by a fillet excepted)', V1.blkBad === 0, V1.blkBad + ' of ' + V1.blocks + ' link blocks misplaced; ' + V1.blkCut + ' block parts never within 12 m of the path (fillet corner cuts of short links)' + (V1.blkBad ? '; e.g. ' + V1.ex.filter(x => x.startsWith('block')).slice(0, 2).join('; ') : ''));
  info('V1: link blocks with < 50 % of their window within 12 m of their link (the verifier\'s round-1 measure)', V1.blk12 + ' of ' + V1.blocks + ' (fillets cut the corners of short links)');
  check('V1: path on a route link covered by a block of that link (>= 99.5 %)', V1.uncovM / V1.pathM <= 0.005, (100 * V1.uncovM / V1.pathM).toFixed(2) + ' % of ' + (V1.pathM / 1000).toFixed(0) + ' km uncovered');
  check('V1: every junction box contains the path point nearest its node (within 150 m of the box)', V1.boxBad === 0, V1.boxBad + ' of ' + V1.boxes + (V1.boxBad ? '; e.g. ' + V1.ex.filter(x => x.startsWith('box')).slice(0, 2).join('; ') : ''));
  check('V1: every runway hold and vacate point within 5 m of a runway-holding position or 90 +- 2 m from the centreline', V1.holdBad === 0 && V1.vacBad === 0, 'holds ' + V1.holdBad + ' of ' + V1.holds + ' off, vacate ' + V1.vacBad + ' of ' + V1.vac + ' off');
  check('V1: every push ends beyond its swing junction K', V1.pushKBad === 0, V1.pushKBad + ' of ' + V1.pushK);
  check('V3: driven path: no arc > 100 deg and no heading change > 100 deg within 40 m (AIP (mirror) AD 2.20 2.3.1 + 10 deg)', V3.bad === 0, V3.bad + ' of ' + V3.routes + ' routes; max arc ' + V3.arcMax.toFixed(1) + ' deg, max 40 m window ' + V3.winMax.toFixed(1) + ' deg' + (V3.ex.length ? '; ' + V3.ex.join('; ') : ''));
  check('V4: every metre on a one-at-a-time lane piece (Y1-Y3, M1-M6, L15-L17) inside a lane block of that ref', V4.laneUncovM === 0, V4.laneUncovM + ' of ' + V4.laneM + ' m uncovered');
  check('V4: push.resources holds the lane of an exclusive run or swing link', V4.pushLaneMissing === 0, V4.pushLaneMissing + ' of ' + V4.pushLane + ' missing');
  info('fix round 1 geometry checks', nGeo + ' base routes (span class n) in ' + ((performance.now() - t0) / 1000).toFixed(0) + ' s');
}

// ------------------------------------------------------------------------------------------- 5c. fix round 2 (H1, M2, L1, C2, C4)
// Independent float geometry (Math.hypot / trig through path.js pointAt; the taxi graph's raw link polylines).
{
  const t0 = performance.now(); const q = {};
  const EXL = new Set(ROUTER.exclusiveLanes); const openL = L.filter(l => l.status === 'open' && l.use !== 'runway');
  const GRID = 20; const grid = new Map(); const gk = (x, z) => Math.floor(x / GRID) + ',' + Math.floor(z / GRID);
  for (const l of openL) for (let i = 1; i < l.pts.length; i++) { const a = l.pts[i - 1], b = l.pts[i]; const n = Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / 5); for (let k = 0; k <= n; k++) { const key = gk(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n); let c = grid.get(key); if (!c) grid.set(key, c = new Set()); c.add(l.id * 10000 + i); } }
  const cum = new Map(); const cumOf = (id) => { let c = cum.get(id); if (c) return c; const P = L[id].pts; c = [0]; for (let i = 1; i < P.length; i++) c.push(c[i - 1] + Math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1])); cum.set(id, c); return c; };
  // segments within d (m) of (x, z): [{id, i, t, d, ux, uz}]
  const near = (x, z, d) => { const out = []; const r = Math.ceil(d / GRID); const cx = Math.floor(x / GRID), cz = Math.floor(z / GRID); const seen = new Set();
    for (let a = -r; a <= r; a++) for (let b = -r; b <= r; b++) { const c = grid.get((cx + a) + ',' + (cz + b)); if (!c) continue; for (const code of c) { if (seen.has(code)) continue; seen.add(code); const id = Math.floor(code / 10000), i = code % 10000; const P = L[id].pts; const A0 = P[i - 1], B0 = P[i]; const ex = B0[0] - A0[0], ez = B0[1] - A0[1], l2 = ex * ex + ez * ez; let t = l2 > 0 ? ((x - A0[0]) * ex + (z - A0[1]) * ez) / l2 : 0; t = Math.max(0, Math.min(1, t)); const dd = Math.hypot(A0[0] + ex * t - x, A0[1] + ez * t - z); if (dd <= d) out.push({ id, i, t, d: dd, ux: ex / Math.sqrt(l2), uz: ez / Math.sqrt(l2) }); } }
    return out; };
  const blockId = (h) => { const c = cumOf(h.id); const tot = c[c.length - 1]; const nb = Math.max(1, Math.floor(Math.round(L[h.id].len * 100) / ROUTER.blockMinCm)); const f = (c[h.i - 1] + (c[h.i] - c[h.i - 1]) * h.t) / tot; return 'b:' + h.id + ':' + Math.min(nb - 1, Math.floor(f * nb)); };
  const junctions = G.nodes.filter(n => n.kind === 'junction' && (RT.graph.degree.get(n.id) || 0) >= 3);
  const jGrid = new Map(); for (const n of junctions) { const k = gk(n.x, n.z); if (!jGrid.has(k)) jGrid.set(k, []); jGrid.get(k).push(n); }
  const nearJ = (x, z, d) => { const out = []; const r = Math.ceil(d / GRID); const cx = Math.floor(x / GRID), cz = Math.floor(z / GRID); for (let a = -r; a <= r; a++) for (let b = -r; b <= r; b++) for (const n of jGrid.get((cx + a) + ',' + (cz + b)) || []) if (Math.hypot(n.x - x, n.z - z) <= d) out.push(n); return out; };
  const H = { routes: 0, uncovM: 0, uncovRoutes: 0, gapFills: 0, pushes: 0, footMiss: 0, footLinks: 0, sweepMiss: 0, sweepLinks: 0, laneMiss: 0, laneN: 0, boxMiss: 0, ex: [], along: 0, alongBad: 0, cross: 0, crossM: 0, crossNoBox: 0, behind: 0, jPass: 0, jBad: 0, geoBoxes: 0 };
  const M2 = { n: 0, bad: 0, arcMax: 0, winMax: 0, ex: [] };
  for (const [R, r, vr] of allRoutes) {
    H.routes++;
    // (H1 a) every metre of the route inside some block (blocks of zero length, "behind", do not count)
    let unc = 0; const iv = r.blocks.filter(b => b.s1Cm > b.s0Cm && b.res !== false); for (let sc = 0; sc <= r.lenCm; sc += 100) if (!iv.some(b => b.s0Cm <= sc && sc <= b.s1Cm)) unc++;   // (fix round 3: the tail-clear markers reserve nothing and do not count)
    if (unc) { H.uncovRoutes++; H.uncovM += unc; if (H.ex.length < 4) H.ex.push('uncovered ' + r.kind + ' ' + r.stand + ' ' + unc + ' m'); }
    H.gapFills += r.gapFill || 0; H.behind += r.blocks.filter(b => b.behind).length;
    // (H1 d) one-at-a-time lanes by geometry on the route path: stretches with the nose gear within 3 m of a lane centreline;
    // a stretch with a sample within 37 deg of the lane direction must lie inside a lane block of that ref, a bare crossing
    // (no such sample) inside a junction box
    if (vr === 'base') {
      const runs = new Map(), jr = new Map(); H.geoBoxes += r.geoBoxes || 0;
      for (let sc = 0; sc <= r.lenCm; sc += 100) { pathAt(r.path, sc, q);
        // (H1 e) junction nodes within 15 m of the nose gear: per pass (gaps <= 3 m), the nearest station
        for (const n of nearJ(q.x / 100, q.z / 100, 15)) { const d = Math.hypot(n.x - q.x / 100, n.z - q.z / 100); let a = jr.get(n.id); if (!a) jr.set(n.id, a = []); const last = a[a.length - 1];
          if (last && sc - last.s1 <= 300) { last.s1 = sc; if (d < last.d) { last.d = d; last.sm = sc; } } else a.push({ s0: sc, s1: sc, d, sm: sc }); }
        const hs = near(q.x / 100, q.z / 100, 3).filter(h => L[h.id].ref && EXL.has(L[h.id].ref)); const seen = new Map();
        for (const h of hs) { const par = Math.abs(h.ux * q.hx + h.uz * q.hz) >= 0.8; const rf = L[h.id].ref; seen.set(rf, (seen.get(rf) || false) || par); }
        for (const [rf, par] of seen) { let a = runs.get(rf); if (!a) runs.set(rf, a = []); const last = a[a.length - 1]; if (last && sc - last.s1 <= 300) { last.s1 = sc; last.par = last.par || par; } else a.push({ s0: sc, s1: sc, par }); } }
      for (const [rf, a] of runs) for (const sr of a) {
        if (sr.par) { H.along++; if (!r.blocks.some(b => b.kind === 'lane' && b.id === 'lane:' + rf && b.s0Cm <= sr.s0 + 100 && b.s1Cm >= sr.s1 - 100)) { H.alongBad++; if (H.ex.length < 8) H.ex.push('lane ' + rf + ' ' + r.kind + ' ' + r.stand + ' [' + sr.s0 + ', ' + sr.s1 + ']'); } }
        else { H.cross++; H.crossM += (sr.s1 - sr.s0) / 100 + 1; if (!r.blocks.some(b => b.kind === 'box' && b.s0Cm <= sr.s0 + 100 && b.s1Cm >= sr.s1 - 100)) H.crossNoBox++; }
      }
      // every pass inside a box of that node at its nearest station (or inside a runway block: the strip is held whole)
      for (const [v, a] of jr) for (const p of a) { H.jPass++; if (r.blocks.some(b => (b.kind === 'box' && b.node === v && b.s0Cm - 100 <= p.sm && p.sm <= b.s1Cm + 100) || (b.kind === 'rwy' && b.s0Cm <= p.sm && p.sm <= b.s1Cm))) continue;
        H.jBad++; if (H.ex.length < 12) H.ex.push('junction j:' + v + ' ' + r.kind + ' ' + r.stand + '>' + r.end + ' s ' + p.sm + ' d ' + p.d.toFixed(1)); }
    }
    if (r.kind !== 'dep') continue;
    H.pushes++; const P = r.push; const res = new Set(P.resources); const tail = ROUTER.foot.tailCm[r.cls] / 100;
    // (H1 b) the start-up fuselage: the push path from the push end to the tail and the straight body from the nose gear
    // along the push direction; every open non-runway link within 4 m -> its block in push.resources and as a route block
    // from s = 0; every junction node within 15 m -> its box; every exclusive lane within 6 m -> lane:<ref>
    const pe = pathAt(P.path, P.lenCm, {}); const startPts = []; for (let d = 0; d <= tail; d += 1) { pathAt(P.path, P.lenCm + d * 100, q); startPts.push([q.x / 100, q.z / 100]); startPts.push([pe.x / 100 + pe.hx * d, pe.z / 100 + pe.hz * d]); }
    const sweepPts = []; for (let sc = 0; sc <= P.lenCm + tail * 100; sc += 200) { pathAt(P.path, sc, q); sweepPts.push([q.x / 100, q.z / 100]); }
    const startB = new Set(r.blocks.filter(b => b.s0Cm === 0).map(b => b.id));
    const fl = new Set(), sl = new Set(), ln = new Set(), bx = new Set();
    for (const [x, z] of startPts) { for (const h of near(x, z, 6)) { if (h.d <= 4) fl.add(blockId(h)); if (L[h.id].ref && EXL.has(L[h.id].ref)) ln.add(L[h.id].ref); } for (const n of nearJ(x, z, 15)) bx.add('j:' + n.id); }
    for (const [x, z] of sweepPts) { for (const h of near(x, z, 6)) { if (h.d <= 4) sl.add(blockId(h)); if (L[h.id].ref && EXL.has(L[h.id].ref)) ln.add(L[h.id].ref); } }
    for (const id of fl) { H.footLinks++; if (!res.has(id) || !startB.has(id)) { H.footMiss++; if (H.ex.length < 10) H.ex.push('start-up ' + r.stand + '>' + r.end + ' ' + id + (res.has(id) ? ' (not a route block at s = 0)' : ' (not in push.resources)')); } }
    for (const id of sl) { H.sweepLinks++; if (!res.has(id)) { H.sweepMiss++; if (H.ex.length < 12) H.ex.push('sweep ' + r.stand + '>' + r.end + ' ' + id); } }
    for (const rf of ln) { H.laneN++; if (!res.has('lane:' + rf)) H.laneMiss++; }
    for (const id of bx) if (!res.has(id) || !startB.has(id)) H.boxMiss++;
    // (M2) the driven push path (stand -> push end): no arc > 100 deg, no heading change > 100 deg within 40 m (own float headings, 1 m)
    if (vr === 'base') {
      M2.n++; let arc = 0; for (const p of P.pieces) if (p.kind === 'arc' && p.s0Cm < P.lenCm) arc = Math.max(arc, p.g.th * 180 / Math.PI);
      const hd = []; for (let sc = 0; sc <= P.lenCm; sc += 100) { pathAt(P.path, sc, q); hd.push(Math.atan2(q.hx, -q.hz)); }
      const u = [hd[0]]; for (let i = 1; i < hd.length; i++) { let dd = hd[i] - hd[i - 1]; while (dd > Math.PI) dd -= 2 * Math.PI; while (dd < -Math.PI) dd += 2 * Math.PI; u.push(u[i - 1] + dd); }
      let win = 0; for (let i = 0; i < u.length; i++) for (let j = i + 1; j < u.length && j <= i + 40; j++) win = Math.max(win, Math.abs(u[j] - u[i]) * 180 / Math.PI);
      M2.arcMax = Math.max(M2.arcMax, arc); M2.winMax = Math.max(M2.winMax, win); if (arc > 100 || win > 100.5) { M2.bad++; if (M2.ex.length < 4) M2.ex.push(r.stand + '>' + r.end + ' arc ' + arc.toFixed(1) + ' win ' + win.toFixed(1)); }
    }
  }
  check('H1: every metre of every route inside some block (all routes, both variants, all span classes; 1 m)', H.uncovM === 0, H.uncovM + ' m uncovered on ' + H.uncovRoutes + ' of ' + H.routes + ' routes; gap-fill stretches ' + H.gapFills + '; behind blocks (under the start-up fuselage at s = 0) ' + H.behind + (H.ex.filter(x => x.startsWith('uncovered')).length ? '; ' + H.ex.filter(x => x.startsWith('uncovered')).join('; ') : ''));
  check('H1: every link within 4 m of the start-up fuselage (push end -> tail along the push path and the straight body) in push.resources and a route block at s = 0; every junction within 15 m its box', H.footMiss === 0 && H.boxMiss === 0, H.footMiss + ' of ' + H.footLinks + ' link blocks missing, boxes missing ' + H.boxMiss + ' (' + H.pushes + ' departures)' + (H.ex.filter(x => x.startsWith('start-up')).length ? '; ' + H.ex.filter(x => x.startsWith('start-up')).slice(0, 3).join('; ') : ''));
  check('H1: every link within 4 m of the push sweep (stand -> push end + tail) in push.resources', H.sweepMiss === 0, H.sweepMiss + ' of ' + H.sweepLinks + ' missing' + (H.ex.filter(x => x.startsWith('sweep')).length ? '; ' + H.ex.filter(x => x.startsWith('sweep')).slice(0, 3).join('; ') : ''));
  check('H1: lanes by geometry: every one-at-a-time lane within 6 m of the push sweep or the start-up fuselage in push.resources', H.laneMiss === 0, H.laneMiss + ' of ' + H.laneN + ' missing');
  check('H1: lanes by geometry on the route path: every stretch with the nose gear within 3 m of a lane and along it (37 deg) inside a lane block of that ref', H.alongBad === 0, H.alongBad + ' of ' + H.along + ' stretches' + (H.ex.filter(x => x.startsWith('lane')).length ? '; ' + H.ex.filter(x => x.startsWith('lane')).slice(0, 3).join('; ') : ''));
  check('H1: junctions by geometry: every pass of the nose gear within 15 m of a junction node inside a box of that node at the nearest station (or a runway block)', H.jBad === 0, H.jBad + ' of ' + H.jPass + ' passes (base routes); geometric boxes (nodes not on the route) ' + H.geoBoxes + (H.ex.filter(x => x.startsWith('junction')).length ? '; ' + H.ex.filter(x => x.startsWith('junction')).slice(0, 3).join('; ') : ''));
  check('H1: bare crossings of a lane mouth (within 3 m, never along it) inside a junction box', H.crossNoBox === 0, H.cross + ' crossings (' + H.crossM.toFixed(0) + ' m), ' + H.crossNoBox + ' outside a box');
  check('M2: driven push path (stand -> push end): no arc > 100 deg and no heading change > 100 deg within 40 m', M2.bad === 0, M2.bad + ' of ' + M2.n + ' pushes; max arc ' + M2.arcMax.toFixed(1) + ' deg, max 40 m window ' + M2.winMax.toFixed(1) + ' deg' + (M2.ex.length ? '; ' + M2.ex.join('; ') : ''));
  // (L1) runway holds on EVERY arrival the router serves: every exit (rank 1-3, far-end connectors) x every stand (also the side
  // opposite the stand), both variants, span class n
  const holdPts = []; for (const h of A.holds) holdPts.push([h.x, h.z, h.runway]); for (const h of G.hold_inf) holdPts.push([h.x, h.z, h.runway]);
  const RWF = {}; for (const rr of A.runways) { const a = rr.ends[0].end.xz, b = rr.ends[1].end.xz; const dx = b[0] - a[0], dz = b[1] - a[1], l = Math.hypot(dx, dz); RWF[rr.id] = { p: a, n: [-dz / l, dx / l] }; }
  const atHold = (path, sc, rw) => { pathAt(path, sc, q); const x = q.x / 100, z = q.z / 100; const dmin = Math.min(...holdPts.filter(h => h[2] === rw).map(h => Math.hypot(h[0] - x, h[1] - z))); const lat = Math.abs((x - RWF[rw].p[0]) * RWF[rw].n[0] + (z - RWF[rw].p[1]) * RWF[rw].n[1]); return dmin <= 5 || Math.abs(lat - 90) <= 2; };
  const LH = { routes: 0, holds: 0, bad: 0, vac: 0, vacBad: 0, opp: 0, reCross: 0, ex: [] };
  for (const [R, vr] of [[RT, 'base'], [RVT, 'F4552']]) for (const e of END_IDS) { if (vr === 'F4552' && !(e === '18R' || e === '36L')) continue;
    for (const x of R.exits(e, true)) for (const st of stands) { const r = R.arrival(x.id, st, {}); if (!r) continue; LH.routes++; if (r.exit.oppositeSide) LH.opp++; if (r.exit.reCross) LH.reCross++;
      for (const h of r.holds) { if (h.kind !== 'rwyhold') continue; LH.holds++; if (!atHold(r.path, h.sCm, h.runway)) { LH.bad++; if (LH.ex.length < 4) LH.ex.push(x.id + '>' + st + ' s ' + h.sCm); } }
      LH.vac++; if (!atHold(r.path, r.vacate.sCm, R.graph.ENDS[e].rw)) LH.vacBad++; } }
  check('L1: every runway hold and vacate point at a holding position / 90 m line on EVERY served arrival (all exits incl. rank 3 and far-end connectors, every stand, both variants)', LH.bad === 0 && LH.vacBad === 0, 'holds ' + LH.bad + ' of ' + LH.holds + ' off, vacate ' + LH.vacBad + ' of ' + LH.vac + ' off; ' + LH.routes + ' routes, ' + LH.opp + ' on an exit opposite the stand, ' + LH.reCross + ' re-crossing the landing runway (one runway occupancy to the far side)' + (LH.ex.length ? '; ' + LH.ex.join('; ') : ''));
  // (C4) span >= 36 m is served at full length even when an intersection entry is asked; (C2) toraCm in live mode
  const wf = RT.departure('233', '18R', { entry: 'H2', spanCm: 6480 }), nf = RT.departure('233', '18R', { entry: 'H2', spanCm: 3400 });
  const RLR = makeRouter(G, { stands: S, live: true, runwayEnds: runwayGeom(A) }); const lr = RLR.departure('233', '36L', {}), lh = RLR.departure('233', '36L', { entry: 'H6' });
  check('C4: span >= 36 m lines up at full length (an intersection request is served as full length, flagged); code C keeps the intersection', wf.entry === 'full' && wf.entryAsked === 'H2' && nf.entry === 'H2', 'B77W asked H2 -> ' + wf.entry + ' (' + (wf.entryNote || '') + '); A320 asked H2 -> ' + nf.entry);
  check('C2: lineup.toraCm / toraLeftCm also in live mode (runwayEnds from traj.js runwayGeom)', lr.lineup.toraCm === T.runwayEnds['36L'].toraCm && lr.lineup.toraLeftCm != null && lh.lineup.toraCm === T.runwayEnds['36L'].intersections.H6.toraCm, 'live 36L full ' + lr.lineup.toraCm + ' / left ' + lr.lineup.toraLeftCm + ', H6 ' + lh.lineup.toraCm);
  info('fix round 2 geometry checks', H.routes + ' routes, ' + H.pushes + ' pushes in ' + ((performance.now() - t0) / 1000).toFixed(0) + ' s');
}

// ------------------------------------------------------------------------------------------- 5d. fix round 3 (V3-1): tail clear
// After every runway no-stop block (a crossing's strip, the landing roll to the vacate point) and every end box, the first
// station where the scheduler may plan a stop - a block boundary that is not strictly inside any no-stop block (no chaining:
// the strictest reading) - must leave the whole aircraft behind the far end: stop - tail >= far end, tail = the largest
// nose-gear -> tail distance of any perf.js type of the route's span class. Holds never inside a no-stop block. Queue room
// behind the holds that follow a tail-clear stretch (INFO, with and without the tail clear).
{
  const T3 = { n: 0, bad: 0, byKind: {}, ex: [], holdIn: 0, holdBox: 0, holdBoxK: {}, holds: 0, room: [], room0: [], roomShort: 0, roomShort0: 0, markers: 0, tailMiss: 0 };
  const tailRef = { n: 0, w: 0, x: 0 }, lenRef = { n: 0, w: 0, x: 0 };
  for (const id of [...Object.keys(ICAO_TYPES), 'C919', 'AJ27', 'GLF6']) { const p = perfOf(id); const c = p.spanCm < 3600 ? 'n' : p.spanCm < 6500 ? 'w' : 'x'; tailRef[c] = Math.max(tailRef[c], p.lenCm - p.noseGearCm); lenRef[c] = Math.max(lenRef[c], p.lenCm); }
  for (const c of ['n', 'w', 'x']) if (ROUTER.foot.tailCm[c] < tailRef[c]) T3.tailMiss++;
  // plus the departures of the wide span classes (allRoutes holds the departures of class n)
  const routes3 = allRoutes.slice();
  for (const [R, vr] of [[RT, 'base'], [RVT, 'F4552']]) for (const st of stands) for (const e of END_IDS) { if (vr === 'F4552' && !(e === '18R' || e === '36L')) continue;
    for (const sp of [3600, 6500]) { if (span.get(st) < sp) continue; const r = R.departure(st, e, { spanCm: sp }); if (r) routes3.push([R, r, vr]); } }
  for (const [R, r, vr] of routes3) {
    const ns = r.blocks.filter(b => b.noStop && b.s1Cm > b.s0Cm); const inNS = (x) => ns.some(b => b.s0Cm < x && x < b.s1Cm);
    const bounds = [...new Set(r.blocks.flatMap(b => [b.s0Cm, b.s1Cm]))].sort((a, b) => a - b);
    const tail = tailRef[r.cls]; T3.markers += r.blocks.filter(b => b.kind === 'clear').length;
    for (const b of r.blocks) {
      const k = b.kind === 'endbox' ? 'endbox' : b.kind === 'rwy' && b.noStop ? (b.landing ? 'landing' : 'crossing') : null; if (!k) continue;
      const stop = bounds.find(x => x > b.s1Cm && !inNS(x)); if (stop == null || stop >= r.lenCm) continue;   // the route ends inside the sequence (the stand / line-up)
      T3.n++; const K = T3.byKind[k] || (T3.byKind[k] = { n: 0, bad: 0 }); K.n++;
      if (stop - tail < b.s1Cm) { T3.bad++; K.bad++; if (T3.ex.length < 6) T3.ex.push((r.kind === 'dep' ? r.stand + '>' + r.end : r.exitId + '>' + r.stand) + '/' + r.cls + ' ' + k + ' far end ' + (b.s1Cm / 100).toFixed(1) + ' first stop ' + (stop / 100).toFixed(1)); }
    }
    for (const h of r.holds) { T3.holds++; const inside = ns.filter(b => b.s0Cm < h.sCm && h.sCm < b.s1Cm);
      if (inside.some(b => b.kind !== 'box')) { T3.holdIn++; if (T3.ex.length < 10) T3.ex.push('hold ' + h.kind + ' inside ' + inside.map(b => b.id).join('+') + ' ' + r.kind + ' ' + r.stand + ' s ' + h.sCm); }
      else if (inside.length) { T3.holdBox++; T3.holdBoxK[h.kind] = (T3.holdBoxK[h.kind] || 0) + 1; }
      if (h.kind !== 'rwyhold' && h.kind !== 'lineup' && h.kind !== 'endbox') continue;
      // the queue room behind the hold: back to the end of the previous no-stop sequence that holds a tail-clear marker
      const prev = r.blocks.filter(b => b.kind === 'clear' && b.s1Cm <= h.sCm).sort((a, b) => b.s1Cm - a.s1Cm)[0]; if (!prev) continue;
      const room = (h.sCm - prev.s1Cm) / 100, room0 = room + prev.tailCm / 100; T3.room.push(room); T3.room0.push(room0);
      if (room * 100 < lenRef[r.cls]) T3.roomShort++; if (room0 * 100 < lenRef[r.cls]) T3.roomShort0++; }
  }
  check('V3-1: after every runway no-stop block (crossing, landing) and end box, the first plannable stop (a block boundary outside every no-stop block) leaves the whole aircraft behind the far end (largest nose-gear -> tail of the class: n ' + (tailRef.n / 100).toFixed(1) + ' / w ' + (tailRef.w / 100).toFixed(1) + ' / x ' + (tailRef.x / 100).toFixed(1) + ' m)', T3.bad === 0 && T3.tailMiss === 0, T3.bad + ' of ' + T3.n + ' events short (' + Object.entries(T3.byKind).map(([k, v]) => k + ' ' + v.bad + ' / ' + v.n).join(', ') + '); ' + T3.markers + ' tail-clear markers on ' + routes3.length + ' routes (all variants and span classes, departures of every class); ROUTER.foot.tailCm below a type of its class: ' + T3.tailMiss + (T3.ex.length ? '; ' + T3.ex.slice(0, 4).join('; ') : ''));
  check('V3-1: no hold strictly inside a runway no-stop block or a tail-clear marker', T3.holdIn === 0, T3.holdIn + ' of ' + T3.holds + ' holds');
  info('V3-1: holds inside a no-stop junction box (round 0 on; a hold is a mandatory stop and overrides the box\'s no-stop flag, movement.md §8)', T3.holdBox + ' of ' + T3.holds + ' holds (' + JSON.stringify(T3.holdBoxK) + ')');
  info('V3-1: queue room behind a runway / line-up / end-box hold that follows a tail-clear stretch (hold back to the end of the no-stop sequence)', T3.room.length + ' holds: min ' + mn(T3.room).toFixed(0) + ' m, p10 ' + q(T3.room, 0.1).toFixed(0) + ', p50 ' + q(T3.room, 0.5).toFixed(0) + ' m (without the tail clear: min ' + mn(T3.room0).toFixed(0) + ', p50 ' + q(T3.room0, 0.5).toFixed(0) + ' m); shorter than the longest type of the class: ' + T3.roomShort + ' (without: ' + T3.roomShort0 + ')');
}

// ------------------------------------------------------------------------------------------- 6. end-arounds and wide crossings
const west = stands.filter(s => RT.westOfWest(s));
let eaN = 0, eaYes = 0, wN = 0, wH = 0, wEA = 0, xEA = 0, xN = 0; const eaExtra = [];
for (const s of west) for (const e of ['18L', '36R']) for (const x of RT.exits(e).filter(x => x.side === 'west')) {
  const r = RT.arrival(x.id, s, { spanCm: 0 }); eaN++; if (r.endAround) eaYes++;
  if (span.get(s) >= 3600) { const w = RT.arrival(x.id, s, { spanCm: 4500 }); wN++; if (w.endAround) wEA++; const c = w.crossings.filter(c => c.runway === '18R/36L'); if (c.length && c.every(c => c.ref === ROUTER.wideCrossFree[e])) wH++; }
  if (span.get(s) >= 6500) { const xx = RT.arrival(x.id, s, { spanCm: 6800 }); xN++; if (xx.endAround) xEA++; }
}
check('end-around for >= 90 % of span < 36 m west-side arrivals (east runway)', eaYes / eaN >= 0.9, eaYes + ' / ' + eaN + ' = ' + (100 * eaYes / eaN).toFixed(1) + ' %');
check('span >= 65 m: never an end-around', xEA === 0, xEA + ' / ' + xN);
check('span 36-65 m: cross 18R/36L via H2 (18L) / H6 (36R)', wH === wN, wH + ' / ' + wN + ' via H2 / H6, end-arounds ' + wEA);
// V10: every exit the exit model can pick (rank 1-3 and the far-end connectors) and the real wide-body spans
{
  const SPANS = { B753: 3805, B763: 4757, B789: 6012, A332: 6030, A333: 6030, B744: 6444, A359: 6475, B77W: 6480 };
  let n = 0, ok = 0, ea = 0; const bad = {};
  for (const s of west) for (const e of ['18L', '36R']) for (const x of RT.exits(e, true).filter(x => x.side === 'west')) for (const [ty, sp] of Object.entries(SPANS)) {
    if (span.get(s) < sp) continue; const r = RT.arrival(x.id, s, { spanCm: sp }); if (!r) continue; n++;
    const c = r.crossings.filter(c => c.runway === '18R/36L'); if (r.endAround) ea++;
    if (!r.endAround && c.length && c.every(c => c.ref === ROUTER.wideCrossFree[e])) ok++; else { const k = x.id + ' ' + (c.map(c => c.ref).join('+') || (r.endAround ? 'end-around' : 'none')); bad[k] = (bad[k] || 0) + 1; }
  }
  check('V10: span 36-65 m cross 18R/36L via H2 (18L) / H6 (36R) on EVERY exit incl. rank 3 and the far-end connectors (real spans 38-65 m)', ok === n && ea === 0, ok + ' / ' + n + ', end-arounds ' + ea + (Object.keys(bad).length ? ' ' + JSON.stringify(bad) : ''));
}
const southFlowEA = { N: 0, S: 0 }, northFlowEA = { N: 0, S: 0 };
for (const s of west) for (const [e, acc] of [['18L', southFlowEA], ['36R', northFlowEA]]) for (const x of RT.exits(e).filter(x => x.side === 'west')) { const r = RT.arrival(x.id, s, { spanCm: 0 }); if (!r.endAround) continue; const refs = new Set(r.links.map(([id]) => L[id].ref)); if (refs.has('N') || refs.has('BN')) acc.N++; if (refs.has('S') || refs.has('BS')) acc.S++; }
info('end-around side', 'south flow (18L): ROUTE-NORTH ' + southFlowEA.N + ', ROUTE-SOUTH ' + southFlowEA.S + '; north flow (36R): ROUTE-NORTH ' + northFlowEA.N + ', ROUTE-SOUTH ' + northFlowEA.S + ' (end boxes and holds on every one)');
let ebOk = 0, ebN = 0; for (const s of west) for (const x of RT.exits('18L').filter(x => x.side === 'west')) { const r = RT.arrival(x.id, s, { spanCm: 0 }); if (!r.endAround) continue; ebN++; if (r.blocks.some(b => b.kind === 'endbox') && r.holds.some(h => h.kind === 'endbox')) ebOk++; }
check('every end-around carries an 18R/36L end box and its hold', ebOk === ebN, ebOk + ' / ' + ebN);

// ------------------------------------------------------------------------------------------- 7. exits, F4552
const exitTxt = END_IDS.map(e => e + ': ' + RT.exits(e, true).map(x => (x.ref || 'end') + '/' + x.side[0] + x.rank + ' ' + (x.sCm / 100).toFixed(0)).join(', ')).join('; ');
check('exits: named rapid exits only (unnamed links before the F4301 first exits excluded; + one far-end connector per side as the last resort)', END_IDS.every(e => RT.exits(e, true).every(x => x.ref || x.kind === 'end') && RT.exits(e).every(x => x.ref)), exitTxt);
const f4301 = { '18L': { B4: 1850, A3: 1890 }, '36R': { A2: 1715, B3: 1950 } };   // F4301: first rapid exits from the DTHR (m)
const dF = []; for (const [e, m] of Object.entries(f4301)) for (const [ref, d] of Object.entries(m)) { const x = RT.exits(e, true).find(x => x.ref === ref); dF.push((x.sCm - T.runwayEnds[e].thrSCm) / 100 - d); }
info('F4301 first exits vs the graph (graph - NOTAM, m from the DTHR)', dF.map(d => d.toFixed(0)).join(', '));
const vClosed = T.variants.F4552.closedLinks.length; let vUses = 0;
for (const [R, r, vr] of allRoutes) if (vr === 'F4552' && r.links.some(([id]) => T.variants.F4552.closedLinks.includes(id))) vUses++;
check('F4552 variant: no route uses a closed link', vUses === 0, vClosed + ' closed links; ' + vUses + ' routes using one; ' + T.counts.variantRoutes + ' variant routes (' + T.counts.variantNull + ' without a route: arrivals leaving 18R/36L to the east, onto the closed taxiway B (B7, B8 and the east end connectors); no landings in the F4551 window anyway)');
const depV = Object.entries(T.groups).filter(([k]) => k.startsWith('dep') && k.endsWith('F4552')); const depVnone = depV.reduce((a, [, g]) => a + g.leaf.filter(x => x === -2).length, 0);
check('F4552: every departure to 18R / 36L still has a route', depVnone === 0, depVnone + ' without');

// ------------------------------------------------------------------------------------------- 8. pavement (option A swept planform; all routes' gear)
const polys = [];
const addP = (ring, holes = []) => { let x0 = 1e9, z0 = 1e9, x1 = -1e9, z1 = -1e9; for (const p of ring) { x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0]); z0 = Math.min(z0, p[1]); z1 = Math.max(z1, p[1]); } polys.push({ ring, holes, bb: [x0, z0, x1, z1] }); };
for (const k of ['runway', 'runway_shoulders_blast_pads', 'taxiway', 'taxiway_shoulders']) for (const s of A.surfaces[k]) addP(s.ring, s.holes || []);
for (const a of A.aprons) addP(a.ring, a.holes || []); for (const h of A.helipads || []) if (h.ring) addP(h.ring);
for (const k of ['airside_fill', 'stand_head_fill']) for (const pl of (B3[k] && B3[k].polys) || []) for (const r of pl) addP(r);
for (const pl of (B3.airside_fill && B3.airside_fill.apron_polys) || []) for (const r of pl) addP(r);   // V15: drawn as apron (gates.js vectorPavement, terminals.js pavement())
const inRing = (r, x, z) => { let c = false; for (let i = 0, j = r.length - 1; i < r.length; j = i++) { const a = r[i], b = r[j]; if ((a[1] > z) !== (b[1] > z) && x < (b[0] - a[0]) * (z - a[1]) / (b[1] - a[1]) + a[0]) c = !c; } return c; };
const paved = (x, z) => polys.some(p => x >= p.bb[0] && x <= p.bb[2] && z >= p.bb[1] && z <= p.bb[3] && inRing(p.ring, x, z) && !p.holes.some(h => inRing(h, x, z)));
const classRef = S.class_ref; const typeOfCls = (c) => { const ic = (classRef[c] || classRef.C).type; return { icao: ic, T: TYPES[ICAO_TYPES[ic] || (ic === 'AJ27' ? 'crj9' : 'a321')] }; };
const pushPave = (list) => {   // every (stand, end) push of the list, class reference type, 1 s samples incl. the start-up hold
  let gear = 0, out = 0, n = 0, bad = new Set(); const det = [];
  for (const s of list) for (const e of END_IDS) {
    const st = S.stands.find(x => x.name === s); const { icao, T: TY } = typeOfCls(st.cls); const P = perfOf(icao);
    const r = RT.departure(s, e, { spanCm: P.spanCm }); const tr = pushTraj(r, P, 0); let g = 0, o = 0;
    for (let t = 0; t <= tr.t1; t += 1000) { const pz = evalTraj(tr, t); n++; for (const p of gearOf(TY, pz.x, pz.z, pz.hdg)) if (!paved(p[0], p[1])) g++; for (const p of sweptSamples(TY, pz.x, pz.z, pz.hdg)) if (!paved(p[0], p[1])) o++; }
    gear += g; out += o; if (g || o) { bad.add(s); if (det.length < 8) det.push(s + '>' + e + ' (' + icao + '): gear ' + g + ', outline ' + o); }
  }
  return { gear, out, n, bad, det };
};
const PA = pushPave(oa);
check('option A pushes (14 stands x 4 ends): gear points on pavement (class reference, 1 s samples incl. start-up)', PA.gear === 0, PA.gear + ' of ' + PA.n * 3 + ' gear samples off' + (PA.det.length ? '; ' + PA.det.join('; ') : ''));
check('option A pushes (14 stands x 4 ends): swept planform on pavement (nose, tail, wing tips, half-span, tailplane tips)', PA.out === 0, PA.out + ' of ' + PA.n * 13 + ' outline samples off');
const PAll = pushPave(stands.filter(s => !oa.includes(s)));
info('all other pushes (150 stands x 4 ends, tail-first run + swing)', 'gear ' + PAll.gear + ' of ' + PAll.n * 3 + ' samples off, outline ' + PAll.out + ' of ' + PAll.n * 13 + ' off, on ' + PAll.bad.size + ' stands' + (PAll.det.length ? ' (e.g. ' + PAll.det.slice(0, 4).join('; ') + ')' : ''));
if (!QUICK) {
  // Gear on pavement, all base routes, the stand's class reference type (narrow geometry for C / B, wide for the others), 2 m
  // steps, three surfaces (fix round 2, M1): DRAWN (incl. shoulders and blast pads), LOAD-BEARING (runway, 23 m taxiways,
  // aprons, helipads, the airside / stand-head fills; no shoulders) and the halfWidth CORRIDOR (within the taxi graph's
  // halfWidth 11.5 m of an open centreline, or inside a runway / apron / fill polygon); three gear models: the DISPLAYED one
  // (traj.js: oversteered nose, no-slip main gear), round 1's tractrix (nose on the path) and the chord model (both gears on
  // the path). 0.5 m raster; a cell decides only when its 3 x 3 neighbourhood agrees, else exact point-in-polygon.
  const t0 = performance.now(); const RES = 0.5;
  const pp = []; const addQ = (ring, holes, lb, tw) => { if (ring && ring.length > 2) pp.push({ rings: [ring, ...(holes || [])], lb, tw }); };
  for (const k of ['runway', 'taxiway']) for (const sf of A.surfaces[k]) addQ(sf.ring, sf.holes, true, k === 'taxiway');
  for (const k of ['runway_shoulders_blast_pads', 'taxiway_shoulders']) for (const sf of A.surfaces[k]) addQ(sf.ring, sf.holes, false, false);
  for (const a of A.aprons) addQ(a.ring, a.holes, true, false); for (const h of A.helipads || []) addQ(h.ring, h.holes, true, false);
  for (const pl of B3.airside_fill.polys || []) addQ(pl[0], pl.slice(1), true, false); for (const pl of B3.airside_fill.apron_polys || []) addQ(pl[0], pl.slice(1), true, false);
  for (const pl of (B3.stand_head_fill && B3.stand_head_fill.polys) || []) addQ(pl[0], pl.slice(1), true, false);
  let X0 = 1e9, Z0 = 1e9, X1 = -1e9, Z1 = -1e9; for (const p of pp) for (const v of p.rings[0]) { X0 = Math.min(X0, v[0]); X1 = Math.max(X1, v[0]); Z0 = Math.min(Z0, v[1]); Z1 = Math.max(Z1, v[1]); }
  X0 = Math.floor(X0) - 40; Z0 = Math.floor(Z0) - 40; X1 = Math.ceil(X1) + 40; Z1 = Math.ceil(Z1) + 40;
  const W = Math.ceil((X1 - X0) / RES), Hh = Math.ceil((Z1 - Z0) / RES); const M = new Uint8Array(W * Hh);
  for (const p of pp) { const bit = 1 | (p.lb ? 2 : 0) | (p.lb && !p.tw ? 8 : 0); let a = 1e9, b = -1e9; for (const v of p.rings[0]) { a = Math.min(a, v[1]); b = Math.max(b, v[1]); }
    for (let r = Math.max(0, Math.floor((a - Z0) / RES)); r <= Math.min(Hh - 1, Math.ceil((b - Z0) / RES)); r++) { const zc = Z0 + (r + 0.5) * RES; const xs = [];
      for (const ring of p.rings) for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) { const u = ring[i], v = ring[j]; if ((u[1] > zc) !== (v[1] > zc)) xs.push(u[0] + (zc - u[1]) * (v[0] - u[0]) / (v[1] - u[1])); }
      xs.sort((u, v) => u - v); for (let k = 0; k + 1 < xs.length; k += 2) for (let c = Math.max(0, Math.ceil((xs[k] - X0) / RES - 0.5)); c <= Math.min(W - 1, Math.floor((xs[k + 1] - X0) / RES - 0.5)); c++) M[r * W + c] |= bit; } }
  const hw = G.halfWidth;
  for (const l of L) { if (l.status !== 'open' || l.use === 'runway') continue; for (let i = 1; i < l.pts.length; i++) { const a = l.pts[i - 1], b = l.pts[i]; const ex = b[0] - a[0], ez = b[1] - a[1], l2 = ex * ex + ez * ez;
    for (let r = Math.max(0, Math.floor((Math.min(a[1], b[1]) - hw - Z0) / RES)); r <= Math.min(Hh - 1, Math.ceil((Math.max(a[1], b[1]) + hw - Z0) / RES)); r++) { const zc = Z0 + (r + 0.5) * RES;
      for (let c = Math.max(0, Math.floor((Math.min(a[0], b[0]) - hw - X0) / RES)); c <= Math.min(W - 1, Math.ceil((Math.max(a[0], b[0]) + hw - X0) / RES)); c++) { const xc = X0 + (c + 0.5) * RES; let t = l2 > 0 ? ((xc - a[0]) * ex + (zc - a[1]) * ez) / l2 : 0; t = Math.max(0, Math.min(1, t)); const dx = a[0] + ex * t - xc, dz = a[1] + ez * t - zc; if (dx * dx + dz * dz <= hw * hw) M[r * W + c] |= 4; } } } }
  const bbs = pp.map(p => { let a = 1e9, b = 1e9, c = -1e9, d = -1e9; for (const v of p.rings[0]) { a = Math.min(a, v[0]); c = Math.max(c, v[0]); b = Math.min(b, v[1]); d = Math.max(d, v[1]); } return [a, b, c, d]; });
  const exact = (x, z, lbOnly) => pp.some((p, i) => (!lbOnly || p.lb) && x >= bbs[i][0] && x <= bbs[i][2] && z >= bbs[i][1] && z <= bbs[i][3] && inRing(p.rings[0], x, z) && !p.rings.slice(1).some(h => inRing(h, x, z)));
  const test3 = (x, z, bit, fb) => { const c = Math.floor((x - X0) / RES), r = Math.floor((z - Z0) / RES); if (c > 0 && r > 0 && c < W - 1 && r < Hh - 1) { let n = 0; for (let a = -1; a <= 1; a++) for (let b = -1; b <= 1; b++) if (M[(r + a) * W + c + b] & bit) n++; if (n === 9) return true; if (n === 0) return false; } return fb(x, z); };
  const drawn = (x, z) => test3(x, z, 1, (u, v) => exact(u, v, false)), lb = (x, z) => test3(x, z, 2, (u, v) => exact(u, v, true));
  const cellBits = (x, z) => { const c = Math.floor((x - X0) / RES), r = Math.floor((z - Z0) / RES); return c < 0 || r < 0 || c >= W || r >= Hh ? 0 : M[r * W + c]; };
  const corridor = (x, z) => (cellBits(x, z) & 12) !== 0;
  const MD = ['shown', 'tract', 'chord']; const C = {}; for (const m of MD) C[m] = { nose: [0, 0, 0], main: [0, 0, 0], routes: new Set() }; let nS = 0;
  const jCnt = new Map(); const junc = G.nodes.filter(n => n.kind === 'junction'); const exc = [];
  const ndAt = (x, z) => { let best = null, bd = 60; for (const n of junc) { const d = Math.hypot(n.x - x, n.z - z); if (d < bd) { bd = d; best = n; } } return best; };
  const a = {}, b = {}, cq = {};
  const jobs = [];   // every stand x end: the departure (full length) and the arrivals over the stand side's exits (rank 1-3, far-end), the class reference's span
  for (const st of S.stands) { if (!RT.graph.standNode.has(st.name)) continue; const { icao, T: TY } = typeOfCls(st.cls); const P = perfOf(icao);
    for (const e of END_IDS) { jobs.push([RT.departure(st.name, e, { spanCm: P.spanCm }), P, TY]); const side = RT.standSide(st.name, RT.graph.ENDS[e].rw); for (const x of RT.exits(e, true).filter(x => x.side === side)) jobs.push([RT.arrival(x.id, st.name, { spanCm: P.spanCm }), P, TY]); } }
  for (const [r, P, TY] of jobs) {
    if (!r) continue;
    const wb = P.wheelbaseCm, tr = (TY.track || 6) / 2; const FS = gearFollower(r, wb), FT = gearFollower(r, wb, { model: 'tractrix' }); const m1 = [0, 0], m2 = [0, 0];
    const key = r.kind + ' ' + r.stand + (r.kind === 'dep' ? '>' + r.end + r.entry : '<' + r.exitId);
    for (let sc = 0; sc <= r.lenCm; sc += 200) {
      const np = pathAt(r.path, sc, a), ns = noseAt(FS, r.path, sc, cq), mc = pathAt(r.path, sc - wb, b); followAt(FS, sc, m1); followAt(FT, sc, m2); nS++;
      for (const [md, nx, nz, mx, mz] of [['shown', ns.x / 100, ns.z / 100, m1[0], m1[1]], ['tract', np.x / 100, np.z / 100, m2[0], m2[1]], ['chord', np.x / 100, np.z / 100, mc.x / 100, mc.z / 100]]) {
        let fx = nx - mx, fz = nz - mz; const fl = Math.hypot(fx, fz) || 1; fx /= fl; fz /= fl; const K = C[md];
        if (!drawn(nx, nz)) K.nose[0]++; if (!lb(nx, nz)) K.nose[1]++; if (!corridor(nx, nz)) K.nose[2]++;
        for (const [gx, gz] of [[mx - fz * tr, mz + fx * tr], [mx + fz * tr, mz - fx * tr]]) {
          const d0 = drawn(gx, gz), l0 = lb(gx, gz), c0 = corridor(gx, gz); if (!d0) K.main[0]++; if (!l0) { K.main[1]++; K.routes.add(key); } if (!c0) K.main[2]++;
          if (md === 'shown' && !l0) { const n = ndAt(gx, gz); const k = n ? n.id : 'none'; const e = jCnt.get(k) || { n: 0, routes: new Set(), drawnOff: 0, x: n ? n.x : gx, z: n ? n.z : gz }; e.n++; e.routes.add(key); if (!d0) e.drawnOff++; jCnt.set(k, e); }
        }
      }
    }
  }
  const fmt = (K) => 'nose ' + K.nose.join(' / ') + ', main wheels ' + K.main.join(' / ');
  info('M1: gear on pavement, all base routes (class reference, 2 m; counts off DRAWN / LOAD-BEARING / halfWidth CORRIDOR; ' + nS + ' samples, 1 nose + 2 main wheels each)', 'displayed (oversteer): ' + fmt(C.shown) + ' (main off load-bearing ' + (100 * C.shown.main[1] / (2 * nS)).toFixed(3) + ' % on ' + C.shown.routes.size + ' routes); round-1 tractrix: ' + fmt(C.tract) + ' (' + (100 * C.tract.main[1] / (2 * nS)).toFixed(3) + ' %); chord: ' + fmt(C.chord) + ' (' + (100 * C.chord.main[1] / (2 * nS)).toFixed(3) + ' %); ' + ((performance.now() - t0) / 1000).toFixed(0) + ' s');
  // (the chord model keeps both gears on the centreline by slipping sideways; it is the floor the OSM pavement allows)
  check('M1: the displayed main gear tracks the pavement: main wheels off the load-bearing pavement <= the chord model + 25 % and <= 1/3 of round 1\'s tractrix; displayed nose no worse than a nose on the centreline', C.shown.main[1] <= 1.25 * C.chord.main[1] && C.shown.main[1] * 3 <= C.tract.main[1] && C.shown.nose[1] <= C.chord.nose[1], 'main wheels: displayed ' + C.shown.main[1] + ', chord ' + C.chord.main[1] + ', tractrix ' + C.tract.main[1] + '; nose: displayed ' + C.shown.nose[1] + ', on the centreline ' + C.chord.nose[1]);
  const top = [...jCnt.entries()].sort((u, v) => v[1].n - u[1].n).slice(0, 15);
  info('M1: junctions with the most displayed main-wheel samples off the load-bearing pavement (for the taxi-graph owner)', top.map(([k, e]) => 'node ' + k + ' (' + e.x.toFixed(0) + ', ' + e.z.toFixed(0) + '; ' + [...new Set((RT.graph.adj.get(+k) || []).map(id => L[id].ref || L[id].kind))].join('/') + '): ' + e.n + ' on ' + e.routes.size + ' routes, ' + e.drawnOff + ' off drawn').join('; '));
  fs.mkdirSync(path.join(ROOT, 'out/phase3/B/fix2'), { recursive: true });
  fs.writeFileSync(path.join(ROOT, 'out/phase3/B/fix2/pavement_junctions.json'), JSON.stringify({ samples: nS, models: Object.fromEntries(MD.map(m => [m, { nose: C[m].nose, main: C[m].main, routes: C[m].routes.size }])), junctions: [...jCnt.entries()].sort((u, v) => v[1].n - u[1].n).map(([k, e]) => ({ node: k, x: +e.x.toFixed(1), z: +e.z.toFixed(1), refs: [...new Set((RT.graph.adj.get(+k) || []).map(id => L[id].ref || L[id].kind))], mainOffLB: e.n, drawnOff: e.drawnOff, routes: e.routes.size })) }, null, 1));
}
console.log('\n' + (failed ? failed + ' FAILED' : 'all passed') + ' (' + results.length + ' checks)');
process.exit(failed ? 1 : 0);
