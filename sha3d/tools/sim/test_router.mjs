// sha3d Phase 3 (P3-B) router tests (node, no browser): tools/sim/test_router.mjs
//   node tools/sim/test_router.mjs            # all checks (about 1 min); exit 1 on a failed acceptance check
//   node tools/sim/test_router.mjs --quick    # skip the full-route pavement scan
// Checks (design §7.2 P3-B, §5): route table determinism (two builds, md5) and size; table == live routing; 164 / 164 stands x
// 4 departure and arrival ends; option A for the 14 one-way stands found by rule (runs = optA_push.mjs or shorter); 0 runway-link
// use outside the line-up; 0 off-list crossings; 0 foreign lead-ins; 0 turns > 100 deg; one-way and use rules; end-arounds; the
// F4552 variant; integer pieces vs float lengths (<= 1 cm); option A pushes: swept planform and gear points on pavement for each
// stand's class reference. Prints aggregates only.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { makeRouter, END_IDS, ROUTER } from '../../js/sim/router.js';
import { floatLen, pointAt as pathAt } from '../../js/sim/path.js';
import { perfOf } from '../../js/sim/perf.js';
import { pushTraj, evalTraj, initTraj } from '../../js/sim/traj.js';
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
  // gear points of every base route for its stand's class reference (narrow geometry for C / B, wide for the others), 2 m steps
  let gOff = 0, gN = 0; const offRoutes = new Map();
  for (const [R, r, vr] of allRoutes) {
    if (vr !== 'base') continue; const st = S.stands.find(x => x.name === r.stand); const { icao, T: TY } = typeOfCls(st.cls); const P = perfOf(icao);
    if ((P.spanCm >= 3600) !== (r.geom === 'wide')) continue;
    if (r.kind === 'arr' && r.cls !== (P.spanCm < 3600 ? 'n' : P.spanCm < 6500 ? 'w' : 'x')) continue;
    const wb = P.wheelbaseCm; const a = {}, b = {};
    for (let s = 0; s <= r.lenCm; s += 200) {
      const n = pathAt(r.path, s, a), m = pathAt(r.path, s - wb, b); const h = Math.atan2(n.x - m.x, -(n.z - m.z)) * 180 / Math.PI;
      for (const p of gearOf(TY, n.x / 100, n.z / 100, h)) { gN++; if (!paved(p[0], p[1])) { gOff++; const k = r.kind + ' ' + r.stand + (r.kind === 'dep' ? '>' + r.end : '<' + r.exitId); offRoutes.set(k, (offRoutes.get(k) || 0) + 1); } }
    }
  }
  const byLink = new Map();
  info('gear on pavement, all base routes (class reference type, 2 m steps)', gOff + ' of ' + gN + ' gear samples off (' + (100 * gOff / gN).toFixed(3) + ' %) on ' + offRoutes.size + ' routes; C2 runs the day-scale pavement test (design §5)');
  void byLink;
}
console.log('\n' + (failed ? failed + ' FAILED' : 'all passed') + ' (' + results.length + ' checks)');
process.exit(failed ? 1 : 0);
