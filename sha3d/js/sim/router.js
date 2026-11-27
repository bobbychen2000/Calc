// sha3d Phase 3 (P3-B): edge-based taxi router on data/sha_taxigraph.json (new; no sfo3d code - sfo3d's TaxiNet is a
// map-matcher, not a router, design §1.1). Pure ES module: runs in node and in the browser; the taxi graph, the stands and
// the route table are passed in (never imported at module scope), headings are degrees true at the interfaces.
//
// What it does (design §4.1, §4.2, §7.1):
// - Dijkstra over (link, exit node) states using ONLY the committed transition table `turns` (<= 90 deg + 10 deg, one-way,
//   runway crossings on the AIP list H1-H7 / H1, H4, H7), the link use rules (runway links never, push links only as the
//   first leg, a stand's own lead-in only for that stand, arrival-only / departure-only links per role, `span_max`);
// - option A for the stands whose push end reaches no take-off end: the push continues TAIL FIRST over <= 2 two-way apron
//   lanes (<= 60 m, motion turns <= 100 deg) to a junction J, where a push-turn (<= 100 deg) swings the tail into a branch
//   X; the aircraft then taxis forward through J as if it had arrived via X. Found by rule: the shortest run that reaches
//   all four take-off ends (no link ids);
// - end-arounds: arrivals from 18L/36R to stands west of 18R/36L pay 5 km per 18R/36L crossing when the span is < 36 m
//   (AIP (mirror) AD 2.20 2.3.3: ROUTE-NORTH / ROUTE-SOUTH normally for arrivals to the west apron); spans >= 36 m cross
//   at H2 (landing 18L, south flow) / H6 (landing 36R, north flow) ("mainly cross RWY18R (36L) via H2 (H6)"), pay 10 km
//   for an end-around when < 65 m ("limited") and never use one at >= 65 m (link span_max, "forbidden");
// - exits: the named rapid exits of each landing direction (F4301 first exits and the next), two per side; the unnamed
//   rapid links before the F4301 first exits are excluded (review L1);
// - the F4552 closure variant (closedLinks) and the F4551 crossing restriction (18L/36R only at H4 / H7);
// - route assembly: integer pieces from js/sim/path.js, blocks (>= 60 m per link, junction boxes, runway strips,
//   one-at-a-time lanes, the 18R/36L end boxes), holds, crossings, the line-up point and the push (incl. option A).
// Commit path: integers and + - * / sqrt only (path.js header); the precomputed table data/sha_routes.js (built by
// tools/sim/build_routes.mjs with this same module) replaces the searches.

import { buildPath, PATH, atanDet, RAD2DEG } from './path.js';

export const ROUTER = {
  fullLengthCm: 12000,        // a take-off entry within 120 m of the runway end counts as full length (H1, H7, T6, the end connectors) [inf]
  intersection: { '18R': 'H2', '36L': 'H6' },          // AIP (mirror) AD 2.20 2.1.7 (intersection take-off)
  lineupTurnCos: 0.7071067811865476,                   // the runway link after the line-up points within 45 deg of the take-off heading
  optA: { maxRunCm: 6000, maxRunLinks: 2, turnCos: -0.17364817766693033,     // <= 60 m, <= 2 lanes, turns <= 100 deg (design §4.1)
    longRunCm: 15000, longRunLinks: 4 },                                       // retry for an end the short runs cannot reach (inf)
  geoTurnCos: -0.17364817766693033,                    // cos 100 deg
  xPenCm: 500000,             // 5 km per 18R/36L crossing (design §4.1, inf)
  eaLimitedPenCm: 1000000,    // 10 km for an end-around at 36-65 m span ("limited") [inf]
  wideCrossFree: { '18L': 'H2', '36R': 'H6' },         // span >= 36 m: cross 18R/36L via H2 (south flow) / H6 (north flow)
  spanNarrowCm: 3600, spanEaMaxCm: 6500,
  endAround: ['N', 'S', 'BN', 'BS'],
  exclusiveLanes: ['Y1', 'Y2', 'Y3', 'M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'L15', 'L16', 'L17'],   // AD 2.20 3.1.5 (taxigraph rules.facts)
  endExitWithinCm: 60000,     // a far-end connector within 600 m of the far end is the last-resort exit of its side [inf]
  rollLeadCm: 5000,           // arrival routes start 50 m before the exit node on the runway centreline (the end of the landing roll; room for the exit fillet)
  lineupLeadCm: 15000, lineupAlignCm: 3500,            // line-up: arc onto the centreline + 35 m (>= wheelbase + 2 m of every type)
  holdLatCm: 9000, holdSearchCm: 30000, holdSnapCm: 1500,   // 90 m runway-holding fallback (taxigraph hold_inf rule), search window
  boxPadCm: 1500,             // junction box = fillet region + 15 m (design §4.5)
  blockMinCm: 6000,           // blocks >= 60 m (design §4.5)
  endBox: { alongCm: [3000, 80000], latCm: 30000, holdBeforeCm: 3000 },   // 18R/36L end boxes beyond each end [inf]
  simplifyCm: 100,            // link interior vertices simplified (Douglas-Peucker 1 m) before filleting: OSM digitising jitter would cap turn speeds [inf]
  swingExtCm: 9000,           // push path continues 90 m into the swing branch (main gear + tail evaluation)
  swingCos: 0.5,              // (graph fallback only) the swing branch lies within 60 deg of the reverse of the departure's first link
  pushWeight: 3,              // a pushed metre costs 3 taxied metres in the departure search (1.2 m/s against 7-12 m/s) [inf]
  pushEndPastArcCm: 200,      // the push ends >= 2 m past the push-turn arc (both gears aligned on the lane)
  fwdTurnRCm: 2000,           // ... and far enough into the branch for a 20 m fillet of the forward turn at K (>= 1.6 R_min of every type) [inf]
  pushTailRoomCm: 4000,       // the push path keeps >= 40 m beyond the push end (main gear on the path) [inf]
  caps: { taxiway: 1200, taxiwayWide: 1000, taxilane: 700, leadin: 300, rapid: 2500, lineup: 500, push: 120, stopZoneCm: 1500, stopCms: 100 },   // rapid: the 25 m/s turn-off speed, no acceleration on the exit (design §4.4: entry <= 25 m/s, decelerating)
  leadinStopMs: 5000,         // arrivals stop 5 s before turning onto the lead-in (AIP (mirror) AD 2.20 3.2.2.2; aip_facts.stop_before_leadin; 5 s inf)
  src: 'inf',
  basis: 'design.md §4.1-4.5; AIP (mirror) AD 2.20 2.1.4.2, 2.1.7, 2.2.5, 2.3.1-2.3.3, 3.1.5, 3.2.2.2 via sha_taxigraph rules.facts',
};

const EA = new Set(ROUTER.endAround);
const EXCL = new Set(ROUTER.exclusiveLanes);
const RWY_OF = { '18L': '18L/36R', '36R': '18L/36R', '18R': '18R/36L', '36L': '18R/36L' };
const OTHER_END = { '18L': '36R', '36R': '18L', '18R': '36L', '36L': '18R' };
export const END_IDS = ['18L', '36R', '18R', '36L'];
export const runwayOfEnd = (e) => RWY_OF[e];

/** cheap deterministic fingerprint of the routable part of a taxi graph (FNV-1a 32) */
export function graphFingerprint(G) {
  let h = 0x811c9dc5 >>> 0;
  const mix = (s) => { for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; } };
  for (const l of G.links) mix(l.id + ',' + l.a + ',' + l.b + ',' + Math.round(l.len * 100) + ',' + l.dir + ',' + l.use + ',' + l.status + ',' + (l.ref || '') + ';');
  for (const n of Object.keys(G.turns)) mix(n + ':' + G.turns[n].length + ';');
  return ('00000000' + h.toString(16)).slice(-8);
}

// --------------------------------------------------------------------------------------------- binary heap (cost, key)
class Heap {
  constructor() { this.c = []; this.k = []; }
  get size() { return this.c.length; }
  less(i, j) { return this.c[i] < this.c[j] || (this.c[i] === this.c[j] && this.k[i] < this.k[j]); }
  swap(i, j) { const c = this.c[i]; this.c[i] = this.c[j]; this.c[j] = c; const k = this.k[i]; this.k[i] = this.k[j]; this.k[j] = k; }
  push(cost, key) { this.c.push(cost); this.k.push(key); let i = this.c.length - 1; while (i > 0) { const p = (i - 1) >> 1; if (!this.less(i, p)) break; this.swap(i, p); i = p; } }
  pop() { const cost = this.c[0], key = this.k[0]; const lc = this.c.pop(), lk = this.k.pop(); if (this.c.length) { this.c[0] = lc; this.k[0] = lk; let i = 0; for (;;) { const a = 2 * i + 1, b = a + 1; let m = i; if (a < this.c.length && this.less(a, m)) m = a; if (b < this.c.length && this.less(b, m)) m = b; if (m === i) break; this.swap(i, m); i = m; } } return [cost, key]; }
}

/**
 * @param {object} G        data/sha_taxigraph.json (window.SHA_TAXIGRAPH)
 * @param {object} o        {table (data/sha_routes.json) | null, closedLinks: Iterable<linkId> | null, stands (sha_stands.json) | null,
 *                           crossOnly: {runwayId: [refs]} | null, live: false (ignore the table)}
 */
export function makeRouter(G, o = {}) {
  const L = G.links, N = G.nodes;
  const nodeOf = new Array(N.length); for (const n of N) nodeOf[n.id] = n;
  const adj = new Map(); for (const l of L) for (const v of [l.a, l.b]) { if (!adj.has(v)) adj.set(v, []); adj.get(v).push(l.id); }
  const turns = new Map();
  for (const [n, pairs] of Object.entries(G.turns)) { const m = new Map(); for (const [a, b] of pairs) { if (!m.has(a)) m.set(a, []); m.get(a).push(b); } turns.set(+n, m); }
  const lenCm = L.map(l => Math.round(l.len * 100));
  const ptsCm = L.map(l => l.pts.map(p => [Math.round(p[0] * 100), Math.round(p[1] * 100)]));
  const degree = new Map(); for (const [v, ls] of adj) degree.set(v, ls.filter(id => L[id].kind !== 'push').length);
  const fp = graphFingerprint(G);
  // runways and ends (cm): end point, unit direction of the take-off / landing run, normal to the east
  const RW = {}; const ENDS = {};
  for (const r of G.runways) {
    const e0 = r.ends[0], e1 = r.ends[1];
    const a = [Math.round(e0.xz[0] * 100), Math.round(e0.xz[1] * 100)], b = [Math.round(e1.xz[0] * 100), Math.round(e1.xz[1] * 100)];
    const dx = b[0] - a[0], dz = b[1] - a[1], ln = Math.sqrt(dx * dx + dz * dz); const h = [dx / ln, dz / ln];
    const east = h[1] >= 0 ? [h[1], -h[0]] : [-h[1], h[0]];   // normal pointing east (+x)
    RW[r.id] = { id: r.id, a, b, h, lenCm: Math.round(ln), east, conns: r.connections };
    ENDS[e0.end] = { id: e0.end, rw: r.id, p: a, h, lenCm: Math.round(ln) };
    ENDS[e1.end] = { id: e1.end, rw: r.id, p: b, h: [-h[0], -h[1]], lenCm: Math.round(ln) };
  }
  const alongEnd = (end, x, z) => { const E = ENDS[end]; return (x - E.p[0]) * E.h[0] + (z - E.p[1]) * E.h[1]; };
  const latEast = (rw, x, z) => { const R = RW[rw]; return (x - R.a[0]) * R.east[0] + (z - R.a[1]) * R.east[1]; };
  // stands
  const standNode = new Map(), pushOf = new Map(), ownLeadin = new Map();
  for (const n of N) if (n.kind === 'stand') standNode.set(n.ref, n.id);
  for (const l of L) { if (l.kind === 'push') pushOf.set(l.stand, l); if (l.use === 'stand') { if (!ownLeadin.has(l.stand)) ownLeadin.set(l.stand, []); ownLeadin.get(l.stand).push(l.id); } }
  const standNames = [...standNode.keys()];
  const standInfo = new Map(); for (const s of (o.stands && o.stands.stands) || []) standInfo.set(s.name, s);
  const holdInf = (G.hold_inf || []).map(h => ({ x: Math.round(h.x * 100), z: Math.round(h.z * 100), runway: h.runway, ref: h.taxiway }));
  // closures
  const closed = o.closedLinks ? new Set([...o.closedLinks]) : null;
  const crossOnly = o.crossOnly || null;
  // the precomputed table: used only when it was built from this graph and the closure set matches base or a variant
  const T = o.live ? null : (o.table || null);
  let tableVariant = null;
  if (T && T.graph_fp === fp) {
    if (!closed || closed.size === 0) tableVariant = 'base';
    else for (const [vk, V] of Object.entries(T.variants || {})) { if (V.closedLinks && V.closedLinks.length === closed.size && V.closedLinks.every(id => closed.has(id))) tableVariant = vk; }
  }
  const tableNote = !T ? 'no table' : T.graph_fp !== fp ? 'table built from another taxi graph (fingerprint ' + T.graph_fp + ' vs ' + fp + '): live routing' : tableVariant ? 'table, variant ' + tableVariant : 'closure set unknown to the table: live routing';

  // ------------------------------------------------------------------------------------------- geometry helpers
  const other = (l, v) => (l.a === v ? l.b : l.b === v ? l.a : null);
  const canGo = (l, from) => l.dir === 'both' || (l.dir === 'ab' && l.a === from);
  const ptsFrom = (lid, v) => { const p = ptsCm[lid]; return L[lid].a === v ? p : p.slice().reverse(); };
  // the same, simplified (Douglas-Peucker, ROUTER.simplifyCm; the end nodes stay): the path geometry's input
  const simpCache = new Map();
  const simpFrom = (lid, v) => { let q = simpCache.get(lid); if (!q) { q = simplify(ptsCm[lid], ROUTER.simplifyCm); simpCache.set(lid, q); } return L[lid].a === v ? q : q.slice().reverse(); };
  function dirOut(lid, v) {   // unit direction leaving v along link lid over its first 15 m
    const seq = ptsFrom(lid, v); const q0 = seq[0]; let q1 = seq[1], acc = 0;
    for (let i = 1; i < seq.length; i++) { const dx = seq[i][0] - seq[i - 1][0], dz = seq[i][1] - seq[i - 1][1]; acc += Math.sqrt(dx * dx + dz * dz); q1 = seq[i]; if (acc >= 1500) break; }
    const dx = q1[0] - q0[0], dz = q1[1] - q0[1], m = Math.sqrt(dx * dx + dz * dz) || 1; return [dx / m, dz / m];
  }
  const laneOK = (l) => l.status === 'open' && (l.kind === 'taxilane' || l.kind === 'taxiway') && l.use !== 'runway' && l.use !== 'stand' && !(closed && closed.has(l.id));

  // ------------------------------------------------------------------------------------------- search
  function okLink(l, ctx) {
    if (l.status !== 'open') return false;
    if (closed && closed.has(l.id)) return false;
    if (l.use === 'runway' || l.kind === 'push') return false;
    if (l.use === 'stand') return ctx.role === 'arr';          // a lead-in is only ever the last leg (its stand node is a dead end)
    if (l.use === 'arrival' && ctx.role !== 'arr') return false;
    if (l.use === 'departure' && ctx.role !== 'dep') return false;
    if (l.span_max != null && ctx.spanCm >= Math.round(l.span_max * 100)) return false;
    return true;
  }
  function transCost(lin, v, lout, ctx) {   // extra cost of the transition, or -1 if not allowed
    const n = nodeOf[v]; let c = 0;
    if (n && n.kind === 'rwy' && L[lin].use !== 'runway' && lout.use !== 'runway') {
      const rw = n.runway;
      if (crossOnly && crossOnly[rw] && !crossOnly[rw].includes(lout.ref)) return -1;
      if (ctx.xPen && ctx.xPen.rwy === rw && ctx.xPen.free !== lout.ref) c += ctx.xPen.cm;
    }
    if (ctx.eaPenCm && EA.has(lout.ref) && !EA.has(L[lin].ref)) c += ctx.eaPenCm;
    return c;
  }
  /** multi-goal Dijkstra. starts: [[lid, v (exit node), cost0]]; goal(lid, v) -> key | null. Returns Map key -> {cost, seq} */
  function search(starts, goal, ctx, want = null) {
    const dist = new Map(), prev = new Map(), H = new Heap(), found = new Map();
    const key = (lid, v) => lid * 2 + (L[lid].b === v ? 1 : 0);
    for (const [lid, v, c0] of starts) { const k = key(lid, v); if (!(dist.get(k) <= c0)) { dist.set(k, c0); prev.set(k, -1); H.push(c0, k); } }
    while (H.size) {
      const [d, k] = H.pop(); if (d > dist.get(k)) continue;
      const lid = k >> 1, l = L[lid], v = (k & 1) ? l.b : l.a;
      const g = goal(lid, v);
      if (g != null) {
        for (const gk of (Array.isArray(g) ? g : [g])) if (!found.has(gk)) {
          const seq = []; let c = k; while (c !== -1) { const cl = c >> 1, cv = (c & 1) ? L[cl].b : L[cl].a; seq.push([cl, other(L[cl], cv)]); c = prev.get(c); }
          found.set(gk, { cost: d, seq: seq.reverse() });
        }
        if (want && want.every(w => found.has(w))) break;
      }
      const outs = (turns.get(v) && turns.get(v).get(lid)) || [];
      for (const o2 of outs) {
        const lo = L[o2]; if (!okLink(lo, ctx) || !canGo(lo, v)) continue;
        if (l.use === 'stand' && !(lo.use === 'stand' && lo.stand === l.stand)) continue;   // a lead-in only continues into its own next part
        const w = other(lo, v); if (w == null) continue;
        const tc = transCost(lid, v, lo, ctx); if (tc < 0) continue;
        const k2 = key(o2, w), d2 = d + lenCm[o2] + tc;
        if (!(dist.get(k2) <= d2)) { dist.set(k2, d2); prev.set(k2, k); H.push(d2, k2); }
      }
    }
    return found;
  }
  // departure goals: entering a runway node of the take-off runway with a line-up transition onto it in the take-off direction
  function depGoalFn(ends) {
    return (lid, v) => {
      const n = nodeOf[v]; if (!n || (n.kind !== 'rwy' && n.kind !== 'rwy_end')) return null;
      const lin = L[lid]; if (lin.use === 'runway') return null;
      const outs = turns.get(v) && turns.get(v).get(lid); if (!outs) return null;
      let keys = null;
      for (const end of ends) {
        if (RWY_OF[end] !== n.runway) continue;
        const s = alongEnd(end, n.x * 100, n.z * 100);
        const full = s >= -500 && s <= ROUTER.fullLengthCm, inter = ROUTER.intersection[end] && lin.ref === ROUTER.intersection[end];
        if (!full && !inter) continue;
        const E = ENDS[end];
        const okTurn = outs.some(oid => { const R = L[oid]; if (R.use !== 'runway') return false; const d = dirOut(oid, v); return d[0] * E.h[0] + d[1] * E.h[1] > ROUTER.lineupTurnCos; });
        if (!okTurn) continue;
        (keys || (keys = [])).push(end + '|' + (full ? 'full' : lin.ref));
      }
      return keys;
    };
  }
  const depKeys = (ends) => { const k = []; for (const e of ends) { k.push(e + '|full'); if (ROUTER.intersection[e]) k.push(e + '|' + ROUTER.intersection[e]); } return k; };

  // option A (design §4.1, review M13): the shortest tail-first run that reaches all four take-off ends
  const optACache = new Map();
  function optionA(stand) {
    if (optACache.has(stand)) return optACache.get(stand);
    let rec = null;
    if (T && tableVariant && T.optionA) rec = T.optionA[stand] || null;   // the table lists every option A stand
    else rec = findOptionA(stand);
    optACache.set(stand, rec); return rec;
  }
  function normalStarts(stand) { const P = pushOf.get(stand); return P ? [[P.id, P.b, 0]] : []; }
  // Push candidates (design §4.1 / §4.3, generalised, see docs/phase3/movement.md §2.3): from the push end J0 (the stand's
  // lead-in fork), the tail continues over 0-2 two-way apron lanes (<= 60 m, motion turns <= 100 deg) to a junction K, swings
  // into a branch X there (<= 100 deg), and the aircraft taxis forward from K with the heading -dir(X): the first taxi link Y
  // turns <= 100 deg from it. The taxi graph's own push-end transition ("any lane direction") is not used for the forward
  // taxi: at the OSM lead-in forks it would start the taxi in the direction the tail was moving.
  const candCache = new Map();
  function pushCands(stand, { emptyRun = true, twoWayOnly = true, long = false } = {}) {
    const ck = stand + '|' + emptyRun + '|' + twoWayOnly + '|' + long; if (candCache.has(ck)) return candCache.get(ck);
    const maxLinks = long ? ROUTER.optA.longRunLinks : ROUTER.optA.maxRunLinks, maxCm = long ? ROUTER.optA.longRunCm : ROUTER.optA.maxRunCm;
    const P = pushOf.get(stand); const out = []; if (!P) { candCache.set(ck, out); return out; }
    const ctx = { role: 'dep', spanCm: 0 };
    const J0 = P.b; const pd = dirOut(P.id, J0); const din0 = [-pd[0], -pd[1]];   // motion arriving at J0 (tail first)
    const runs = [];
    const walk = (v, din, run, from, len) => {
      if (run.length || emptyRun) runs.push({ run: run.slice(), from: from.slice(), K: v, din, len });
      if (run.length >= maxLinks) return;
      for (const oid of adj.get(v) || []) {
        const l = L[oid]; if (!laneOK(l) || run.includes(oid) || oid === P.id) continue;
        if (twoWayOnly && l.dir !== 'both') continue;   // two-way lanes only
        const d = dirOut(oid, v); if (din[0] * d[0] + din[1] * d[1] < ROUTER.optA.turnCos) continue;
        if (len + lenCm[oid] > maxCm) continue;
        const w = other(l, v); const dl = dirOut(oid, w);
        walk(w, [-dl[0], -dl[1]], run.concat([oid]), from.concat([v]), len + lenCm[oid]);
      }
    };
    walk(J0, din0, [], [], 0);
    for (const c of runs) {
      for (const x of adj.get(c.K) || []) {
        if (c.run.includes(x) || x === P.id) continue; const X = L[x]; if (!laneOK(X)) continue;
        const dX = dirOut(x, c.K); if (c.din[0] * dX[0] + c.din[1] * dX[1] < ROUTER.optA.turnCos) continue;
        const hd = [-dX[0], -dX[1]]; const starts = [];
        for (const y of adj.get(c.K) || []) {
          if (y === x || y === P.id || c.run.includes(y)) continue; const Y = L[y]; if (!okLink(Y, ctx) || !canGo(Y, c.K)) continue;
          const dY = dirOut(y, c.K); if (hd[0] * dY[0] + hd[1] * dY[1] < ROUTER.optA.turnCos) continue;
          starts.push([y, other(Y, c.K), ROUTER.pushWeight * c.len + lenCm[y]]);
        }
        if (starts.length) out.push({ run: c.run, runFrom: c.from, node: c.K, swing: x, turnDeg: Math.round(angleDeg(c.din, dX)), runCm: c.len, starts });
      }
    }
    candCache.set(ck, out); return out;
  }
  // option A record (design §4.1, review M13): for the stands whose push end reaches no take-off end under the graph's own
  // push-end rule (the 14 one-way stands), the shortest single tail-first run (>= 1 lane) that reaches all four take-off ends
  function findOptionA(stand) {
    const P = pushOf.get(stand); if (!P) return null;
    const ctx = { role: 'dep', spanCm: 0 };
    const all = depKeys(END_IDS).filter(k => k.endsWith('|full'));
    const base = search(normalStarts(stand), depGoalFn(END_IDS), ctx, all);
    if (all.every(k => base.has(k))) return null;    // not a one-way stand
    let best = null;
    for (const c of pushCands(stand, { emptyRun: false })) {
      const res = search(c.starts.map(([y, w]) => [y, w, lenCm[y]]), depGoalFn(END_IDS), ctx, all);
      if (!all.every(k => res.has(k))) continue;
      const rank = [c.runCm, c.run.reduce((a, b) => a + b, 0), c.swing];
      if (!best || rank[0] < best.rank[0] || (rank[0] === best.rank[0] && (rank[1] < best.rank[1] || (rank[1] === best.rank[1] && rank[2] < best.rank[2])))) best = { ...c, rank };
    }
    if (!best) return { failed: true };
    return { run: best.run, runFrom: best.runFrom, node: best.node, swing: best.swing, turnDeg: best.turnDeg, runCm: best.runCm };
  }

  // ------------------------------------------------------------------------------------------- exits (design §4.2)
  const exitList = {};
  for (const end of END_IDS) {
    const R = RW[RWY_OF[end]]; const list = [];
    for (const c of R.conns) {
      if (c.rapid_exit_for !== end || !c.ref) continue;           // named rapid exits only (review L1)
      const n = nodeOf[c.node]; const s = Math.round(alongEnd(end, n.x * 100, n.z * 100));
      list.push({ id: end + ':' + c.ref, end, ref: c.ref, link: c.link, node: c.node, side: c.side, sCm: s, startCm: s - ROUTER.rollLeadCm });
    }
    list.sort((p, q) => p.sCm - q.sCm || (p.ref < q.ref ? -1 : 1));
    const rank = { east: 0, west: 0 };
    for (const e of list) { e.rank = ++rank[e.side]; e.kind = 'rapid'; }
    // the last resort per side: the first end connector within the last 600 m (a long roll-out; the exit model uses it
    // only when no rapid exit of the side is reachable, e.g. a heavy on a short-exit side) [inf]
    const lenR = RW[RWY_OF[end]].lenCm;
    for (const side of ['east', 'west']) {
      const cs = R.conns.filter(c => c.end_connector && c.side === side).map(c => ({ c, s: Math.round(alongEnd(end, nodeOf[c.node].x * 100, nodeOf[c.node].z * 100)) }))
        .filter(({ c, s }) => s >= lenR - ROUTER.endExitWithinCm && canGo(L[c.link], c.node) && L[c.link].status === 'open').sort((a, b) => a.s - b.s);
      if (cs.length) { const { c, s } = cs[0]; list.push({ id: end + ':end' + side[0].toUpperCase(), end, ref: null, link: c.link, node: c.node, side, sCm: s, startCm: s - ROUTER.rollLeadCm, rank: 9, kind: 'end' }); }
    }
    exitList[end] = list;
  }
  const exitById = new Map(); for (const end of END_IDS) for (const e of exitList[end]) exitById.set(e.id, e);
  /** the exits the exit model can pick: the first two per side (design §4.2) */
  function exits(end, all = false) { return (exitList[end] || []).filter(e => (all || e.rank <= 2) && !(closed && closed.has(e.link))); }
  /** side of a stand relative to a runway ('east' | 'west'), from the stop node */
  function standSide(stand, rw) { const v = standNode.get(stand); const n = nodeOf[v]; return latEast(rw, n.x * 100, n.z * 100) > 0 ? 'east' : 'west'; }
  const westOfWest = (stand) => standSide(stand, '18R/36L') === 'west';

  // arrival class: 'n' < 36 m, 'w' 36-65 m, 'x' >= 65 m
  const clsOf = (spanCm) => (spanCm == null || spanCm < ROUTER.spanNarrowCm ? 'n' : spanCm < ROUTER.spanEaMaxCm ? 'w' : 'x');
  const clsSpan = { n: 0, w: ROUTER.spanNarrowCm, x: ROUTER.spanEaMaxCm };
  function arrCtx(end, cls) {
    const ctx = { role: 'arr', spanCm: clsSpan[cls] };
    if (RWY_OF[end] === '18L/36R') {
      if (cls === 'n') ctx.xPen = { rwy: '18R/36L', cm: ROUTER.xPenCm, free: null };
      else { ctx.xPen = { rwy: '18R/36L', cm: ROUTER.xPenCm, free: ROUTER.wideCrossFree[end] }; if (cls === 'w') ctx.eaPenCm = ROUTER.eaLimitedPenCm; }
    }
    return ctx;
  }

  // ------------------------------------------------------------------------------------------- link sequences (table or live)
  const seqCache = new Map();
  function expand(group, leaf, firstFrom) {
    const t = group.t; const ids = []; let i = leaf;
    while (i >= 0) { ids.push(t[2 * i]); i = t[2 * i + 1]; }
    if (!group.rev) ids.reverse();
    const seq = []; let from = firstFrom;
    for (const id of ids) { seq.push([id, from]); from = other(L[id], from); }
    return seq;
  }
  function tableSeq(kind, gk, stand, firstFrom) {
    if (!tableVariant) return undefined;
    const tryG = (key) => {
      const g = T.groups[key]; if (!g) return undefined; const i = T.stands.indexOf(stand); const leaf = i >= 0 ? g.leaf[i] : -1;
      if (leaf === -2) return null; if (leaf < 0) return undefined;
      const seq = expand(g, leaf, firstFrom); return kind === 'dep' ? { seq, nPush: g.pn[i], swing: g.sw[i] >= 0 ? g.sw[i] : null, turnDeg: g.td[i] >= 0 ? g.td[i] : null, fallback: g.sw[i] < 0 } : seq;
    };
    if (tableVariant !== 'base') { const r = tryG(gk + '|' + tableVariant); if (r !== undefined) return r; }
    return tryG(gk + '|base');
  }
  function depSeq(stand, end, entry) {
    const ck = 'd|' + stand + '|' + end + '|' + entry; if (seqCache.has(ck)) return seqCache.get(ck);
    const P = pushOf.get(stand); if (!P) return null;
    let rec = tableSeq('dep', 'dep|' + end + '|' + entry, stand, standNode.get(stand));
    if (rec === undefined) {   // live: one multi-source search over every push candidate of the stand (short runs, then long)
      const run = (cands) => { const owner = new Map(), starts = [];
        for (const c of cands) for (const [y, w, c0] of c.starts) { const k = y * 2 + (L[y].b === w ? 1 : 0); const o = owner.get(k); if (!o || c0 < o.c0) owner.set(k, { c0, c }); }
        for (const [k, o] of [...owner.entries()].sort((a, b) => a[0] - b[0])) starts.push([k >> 1, (k & 1) ? L[k >> 1].b : L[k >> 1].a, o.c0]);
        return { owner, res: search(starts, depGoalFn(END_IDS), { role: 'dep', spanCm: 0 }, depKeys(END_IDS)) }; };
      const A1 = run(pushCands(stand)); let A2 = null;
      let fb = null;
      for (const k of depKeys(END_IDS)) {
        let A = A1, r = A1.res.get(k), out = null;
        if (!r) { if (!A2) A2 = run(pushCands(stand, { long: true })); A = A2; r = A2.res.get(k); }
        if (r) {
          const [y, K] = r.seq[0]; const c = A.owner.get(y * 2 + (L[y].b === other(L[y], K) ? 1 : 0)).c;
          const seq = [[P.id, standNode.get(stand)]]; c.run.forEach((id, i) => seq.push([id, c.runFrom[i]])); seq.push(...r.seq);
          out = { seq, nPush: 1 + c.run.length, swing: c.swing, turnDeg: c.turnDeg };
        } else {   // no geometric push: the graph's own push-end transition, flagged (never seen on the committed graph)
          if (!fb) fb = search(normalStarts(stand), depGoalFn(END_IDS), { role: 'dep', spanCm: 0 }, depKeys(END_IDS));
          const q = fb.get(k); if (q) out = { seq: q.seq, nPush: 1, swing: null, turnDeg: null, fallback: true };
        }
        seqCache.set('d|' + stand + '|' + k, out);
      }
      return seqCache.get(ck) ?? null;
    }
    seqCache.set(ck, rec); return rec;
  }
  function arrSeqs(exitId, cls) {   // live: one Dijkstra from the exit to every stand
    const ck = 'A|' + exitId + '|' + cls; if (seqCache.has(ck)) return seqCache.get(ck);
    const ex = exitById.get(exitId); const out = new Map();
    if (ex) {
      const E = L[ex.link]; const w = other(E, ex.node);
      const goal = (lid, v) => { const l = L[lid]; return l.use === 'stand' && standNode.get(l.stand) === v ? l.stand : null; };
      const res = search([[ex.link, w, lenCm[ex.link]]], goal, arrCtx(ex.end, cls), null);
      for (const [st, r] of res) out.set(st, r.seq);
    }
    seqCache.set(ck, out); return out;
  }
  function arrSeq(exitId, stand, cls) {
    const ck = 'a|' + exitId + '|' + stand + '|' + cls; if (seqCache.has(ck)) return seqCache.get(ck);
    const ex = exitById.get(exitId); if (!ex) return null;
    let seq;
    if (cls !== 'n') { seq = tableSeq('arr', 'arr|' + exitId + '|' + cls, stand, ex.node); if (seq === undefined && tableVariant) seq = tableSeq('arr', 'arr|' + exitId + '|n', stand, ex.node); }
    else seq = tableSeq('arr', 'arr|' + exitId + '|n', stand, ex.node);
    if (seq === undefined) seq = arrSeqs(exitId, cls).get(stand) || null;
    seqCache.set(ck, seq); return seq;
  }

  // ------------------------------------------------------------------------------------------- route assembly
  const capFor = (wide) => (tag) => {
    const tw = wide ? ROUTER.caps.taxiwayWide : ROUTER.caps.taxiway;
    if (!tag) return tw;
    if (tag.cap != null) return tag.cap;
    const l = L[tag.link]; if (!l) return tw;
    if (l.for_landing) return ROUTER.caps.rapid;
    if (l.kind === 'leadin') return ROUTER.caps.leadin;
    if (l.kind === 'taxilane') return ROUTER.caps.taxilane;
    if (l.kind === 'push') return ROUTER.caps.push;
    return tw;
  };
  const capOf = capFor(false);
  function vertsOf(seq, startIdx = 0) {   // polyline vertices with segment tags and the graph node at each link end
    const V = [];
    for (let i = startIdx; i < seq.length; i++) {
      const [lid, from] = seq[i]; const p = simpFrom(lid, from); const to = other(L[lid], from);
      for (let k = V.length ? 1 : 0; k < p.length; k++) V.push({ x: p[k][0], z: p[k][1], tag: { link: lid }, node: k === 0 ? from : k === p.length - 1 ? to : null, li: i });
    }
    // the tag of a vertex is the segment AFTER it: shift (vertex k's tag = link of the segment k -> k+1)
    for (let k = 0; k < V.length - 1; k++) V[k].tag = { link: V[k + 1].tag.link };
    return V;
  }
  // input-polyline position helpers: cumulative distance and the map to route s (linear between vertices)
  function sOnSeg(V, vS, k, u) { return Math.round(vS[k] + (vS[k + 1] - vS[k]) * u); }
  function lateralCrossS(V, vS, rw, k0, dir, latCm) {   // walk from vertex k0 in direction dir (-1 back, +1 forward) until |lat| >= latCm
    for (let k = k0; k + dir >= 0 && k + dir < V.length; k += dir) {
      const a = V[k], b = V[k + dir]; const la = Math.abs(latEast(rw, a.x, a.z)), lb = Math.abs(latEast(rw, b.x, b.z));
      if (lb >= latCm) { const u = lb === la ? 1 : (latCm - la) / (lb - la); const uu = Math.max(0, Math.min(1, u)); return dir > 0 ? sOnSeg(V, vS, k, uu) : sOnSeg(V, vS, k - 1, 1 - uu); }
    }
    return null;
  }
  function holdsNear(V, vS, rw, sFrom, sTo) {   // runway-holding positions of rw on the route with s in [sFrom, sTo]
    const out = [];
    for (let k = 0; k < V.length; k++) { const nd = V[k].node; if (nd != null && nodeOf[nd].kind === 'hold' && nodeOf[nd].runway === rw && vS[k] >= sFrom && vS[k] <= sTo) out.push({ s: vS[k], node: nd, src: 'obs' }); }
    for (const h of holdInf) {
      if (h.runway !== rw) continue;
      for (let k = 0; k < V.length - 1; k++) {
        if (vS[k + 1] < sFrom || vS[k] > sTo) continue;
        const a = V[k], b = V[k + 1]; const dx = b.x - a.x, dz = b.z - a.z, l2 = dx * dx + dz * dz; if (l2 <= 0) continue;
        let u = ((h.x - a.x) * dx + (h.z - a.z) * dz) / l2; u = Math.max(0, Math.min(1, u));
        const px = a.x + dx * u - h.x, pz = a.z + dz * u - h.z;
        if (px * px + pz * pz <= ROUTER.holdSnapCm * ROUTER.holdSnapCm) { const s = sOnSeg(V, vS, k, u); if (s >= sFrom && s <= sTo) out.push({ s, node: null, src: 'inf' }); break; }
      }
    }
    return out.sort((p, q) => p.s - q.s);
  }
  function crossingsOf(V, vS, lastIdx) {
    const out = [];
    for (let k = 1; k < V.length - 1; k++) {
      const nd = V[k].node; if (nd == null) continue; const n = nodeOf[nd]; if (n.kind !== 'rwy') continue;
      const lin = L[V[k - 1].tag.link], lout = L[V[k].tag.link];
      if (!lin || !lout || lin.use === 'runway' || lout.use === 'runway') continue;
      if (lastIdx != null && k >= lastIdx) continue;
      const rw = n.runway, s = vS[k];
      const hb = holdsNear(V, vS, rw, s - ROUTER.holdSearchCm, s - 1), ha = holdsNear(V, vS, rw, s + 1, s + ROUTER.holdSearchCm);
      const sIn = hb.length ? hb[hb.length - 1].s : lateralCrossS(V, vS, rw, k, -1, ROUTER.holdLatCm) ?? Math.max(0, s - ROUTER.holdLatCm);
      const sOut = ha.length ? ha[0].s : lateralCrossS(V, vS, rw, k, 1, ROUTER.holdLatCm) ?? s + ROUTER.holdLatCm;
      const along = {}; for (const e of END_IDS) if (RWY_OF[e] === rw) along[e] = Math.round(alongEnd(e, n.x * 100, n.z * 100));
      let nearEnd = null; for (const e of Object.keys(along)) if (along[e] >= 0 && along[e] <= 50000) nearEnd = e;
      out.push({ runway: rw, node: nd, sCm: s, ref: lout.ref || lin.ref || null, nearEnd, alongCm: along, sInCm: sIn, sOutCm: sOut, holdSrc: hb.length ? hb[hb.length - 1].src : 'inf-90m' });
    }
    return out;
  }
  function arcRangeAt(path, s) {   // the arc piece containing s, or null
    for (const p of path.pieces) if (p.kind === 'arc' && p.s0Cm <= s && s <= p.s0Cm + p.lenCm) return p;
    return null;
  }
  function blocksOf(V, vS, path, seqIdx0, seq, opts) {
    const B = [];
    // link blocks (>= 60 m; ids from the link's a end so that both directions share them)
    const byLi = new Map(); for (let k = 0; k < V.length; k++) { const li = V[k].li; if (!byLi.has(li)) byLi.set(li, []); byLi.get(li).push(k); }
    for (const [li, ks] of byLi) {
      if (li < seqIdx0 || li >= seq.length) continue;
      const [lid, from] = seq[li]; const l = L[lid];
      // the link's vertices in route order: the link starts at the vertex before its first own vertex (shared node)
      const kk = ks[0] > 0 && V[ks[0] - 1] && V[ks[0]].node !== from ? [ks[0] - 1, ...ks] : ks.slice();
      if (kk.length < 2 && ks[0] > 0) kk.unshift(ks[0] - 1);
      const cum = [0]; for (let j = 1; j < kk.length; j++) { const a = V[kk[j - 1]], b = V[kk[j]]; cum.push(cum[j - 1] + Math.sqrt((b.x - a.x) * (b.x - a.x) + (b.z - a.z) * (b.z - a.z))); }
      const tot = cum[cum.length - 1]; if (!(tot > 0)) continue;
      const nb = Math.max(1, Math.floor(lenCm[lid] / ROUTER.blockMinCm));
      const fwd = l.a === from;
      const sAt = (u) => { const d = u * tot; let j = 1; while (j < cum.length - 1 && cum[j] < d) j++; const f = (d - cum[j - 1]) / ((cum[j] - cum[j - 1]) || 1); return Math.round(vS[kk[j - 1]] + (vS[kk[j]] - vS[kk[j - 1]]) * Math.max(0, Math.min(1, f))); };
      for (let b = 0; b < nb; b++) {
        const kA = fwd ? b : nb - 1 - b;   // index from the link's a end
        const s0 = sAt(b / nb), s1 = sAt((b + 1) / nb);
        B.push({ id: 'b:' + lid + ':' + kA, kind: 'link', link: lid, dir: fwd ? 1 : -1, s0Cm: Math.max(0, s0), s1Cm: Math.min(path.lenCm, s1), noStop: false, twoWay: l.dir === 'both' });
      }
    }
    // junction boxes
    for (let k = 1; k < V.length - 1; k++) {
      const nd = V[k].node; if (nd == null || V[k].li < seqIdx0) continue; const n = nodeOf[nd];
      if (n.kind !== 'junction' || (degree.get(nd) || 0) < 3) continue;
      const arc = arcRangeAt(path, vS[k]);
      const s0 = Math.max(0, (arc ? arc.s0Cm : vS[k]) - ROUTER.boxPadCm), s1 = Math.min(path.lenCm, (arc ? arc.s0Cm + arc.lenCm : vS[k]) + ROUTER.boxPadCm);
      const twy = (adj.get(nd) || []).some(id => L[id].kind === 'taxiway');
      B.push({ id: 'j:' + nd, kind: 'box', node: nd, s0Cm: s0, s1Cm: s1, noStop: twy, start: s0 === 0 && opts.startBox ? true : undefined });
    }
    // one-aircraft-at-a-time lanes (AD 2.20 3.1.5)
    let run = null;
    for (let k = 0; k < V.length - 1; k++) {
      const ref = L[V[k].tag.link] && L[V[k].tag.link].ref;
      if (V[k].li >= seqIdx0 && ref && EXCL.has(ref)) { if (run && run.ref === ref) run.s1 = vS[k + 1]; else { if (run) B.push(laneBlk(run)); run = { ref, s0: vS[k], s1: vS[k + 1] }; } }
      else if (run) { B.push(laneBlk(run)); run = null; }
    }
    if (run) B.push(laneBlk(run));
    return B;
  }
  const laneBlk = (r) => ({ id: 'lane:' + r.ref, kind: 'lane', s0Cm: r.s0, s1Cm: r.s1, noStop: false });
  function endBoxes(V, vS) {   // 18R/36L end boxes on end-around links
    const out = []; const E = ROUTER.endBox;
    for (const end of ['18R', '36L']) {
      const inBox = (p) => { const a = -alongEnd(end, p.x, p.z); return a >= E.alongCm[0] && a <= E.alongCm[1] && Math.abs(latEast('18R/36L', p.x, p.z)) <= E.latCm; };
      let s0 = null, s1 = null;
      for (let k = 0; k < V.length - 1; k++) {
        const l = L[V[k].tag.link]; if (!l || !EA.has(l.ref)) continue;
        const a = V[k], b = V[k + 1]; const n = 24;
        for (let j = 0; j <= n; j++) { const u = j / n; const p = { x: a.x + (b.x - a.x) * u, z: a.z + (b.z - a.z) * u }; if (inBox(p)) { const s = sOnSeg(V, vS, k, u); if (s0 == null) s0 = s; s1 = s; } }
      }
      if (s0 != null) out.push({ id: 'endbox:' + end, kind: 'endbox', end, s0Cm: s0, s1Cm: s1, noStop: true });
    }
    return out;
  }
  function trimPath(path, sEnd) {   // drop the pieces beyond sEnd (cut the last one)
    const P = [];
    for (const p of path.pieces) {
      if (p.s0Cm >= sEnd) break;
      if (p.s0Cm + p.lenCm > sEnd) {   // cut: the float geometry is shortened to the same length (lines: end point; arcs: angle)
        const L2 = sEnd - p.s0Cm; const g = p.g;
        const g2 = p.kind === 'line' ? { ...g, len: L2, x1: g.x0 + g.hx * L2, z1: g.z0 + g.hz * L2 } : { ...g, len: L2, th: L2 / g.R };
        P.push({ ...p, lenCm: L2, g: g2, cut: true }); break;
      }
      P.push(p);
    }
    return { ...path, pieces: P, lenCm: sEnd };
  }

  function assembleDep(stand, end, entry, prec, spanCm, wideGeom) {
    const seq = prec.seq; const rec = optionA(stand); const optA = rec && rec.run ? rec : null;
    const nPush = prec.nPush;
    const J = other(L[seq[nPush - 1][0]], seq[nPush - 1][1]);
    const xOut = seq[nPush] ? seq[nPush][0] : null;
    // swing branch: the push record's X; only the graph fallback has none (then the lane at J opposite the first taxi link)
    let swing = prec.swing, swingVirtual = false;
    if (swing == null && xOut != null) {
      const dX = dirOut(xOut, J); let best = -2;
      for (const y of adj.get(J) || []) {
        if (y === xOut || y === seq[0][0]) continue; const Y = L[y];
        if (Y.status !== 'open' || Y.use === 'runway' || Y.kind === 'push' || Y.use === 'stand') continue;
        const dY = dirOut(y, J); const c = -(dX[0] * dY[0] + dX[1] * dY[1]);
        if (c > best || (c === best && y < swing)) { best = c; swing = y; }
      }
      if (best < ROUTER.swingCos) { swing = null; swingVirtual = true; }
    }
    // push path: push link + run (tail first) + into the swing branch
    const PV = [];
    for (let i = 0; i < nPush; i++) { const [lid, from] = seq[i]; const p = simpFrom(lid, from); for (let k = PV.length ? 1 : 0; k < p.length; k++) PV.push({ x: p[k][0], z: p[k][1], tag: { link: lid, cap: ROUTER.caps.push }, node: k === p.length - 1 ? other(L[lid], from) : null }); }
    const iJ = PV.length - 1;
    let ext = 0;
    if (swing != null) { const p = simpFrom(swing, J); for (let k = 1; k < p.length && ext < ROUTER.swingExtCm; k++) { const q = PV[PV.length - 1]; ext += Math.sqrt((p[k][0] - q.x) ** 2 + (p[k][1] - q.z) ** 2); PV.push({ x: p[k][0], z: p[k][1], tag: { link: swing, cap: ROUTER.caps.push }, node: null }); } }
    if (ext < ROUTER.swingExtCm) {   // straight on (virtual swing: opposite the first taxi link)
      let d;
      if (swing != null) { const a = PV[PV.length - 2], b = PV[PV.length - 1]; const m = Math.sqrt((b.x - a.x) ** 2 + (b.z - a.z) ** 2) || 1; d = [(b.x - a.x) / m, (b.z - a.z) / m]; }
      else if (xOut != null) { const dX = dirOut(xOut, J); d = [-dX[0], -dX[1]]; }
      else { const a = PV[PV.length - 2], b = PV[PV.length - 1]; const m = Math.sqrt((b.x - a.x) ** 2 + (b.z - a.z) ** 2) || 1; d = [(b.x - a.x) / m, (b.z - a.z) / m]; }
      const q = PV[PV.length - 1], r = ROUTER.swingExtCm - ext;
      PV.push({ x: Math.round(q.x + d[0] * r), z: Math.round(q.z + d[1] * r), tag: { link: swing, cap: ROUTER.caps.push }, node: null });
    }
    for (let k = 0; k < PV.length - 1; k++) PV[k].tag = PV[k + 1].tag;
    const pushPath = buildPath(PV, { rNomCm: PATH.rPushCm, capOf });
    const sJ = pushPath.vS[iJ];
    const arcJ = arcRangeAt(pushPath, sJ);
    // the push ends far enough into the swing branch that (1) the push-turn arc is complete + 2 m and (2) the forward turn at
    // K out of the branch into the first taxi link has room for a fwdTurnRCm fillet: d >= R tan(theta / 2) + 2 m [inf]
    let dNeed = (arcJ ? arcJ.s0Cm + arcJ.lenCm - sJ : 0) + ROUTER.pushEndPastArcCm;
    if (swing != null && xOut != null) {
      const dX = dirOut(swing, J), dY = dirOut(xOut, J); const ux = -dX[0], uz = -dX[1];
      const cr = Math.abs(ux * dY[1] - uz * dY[0]), dt = ux * dY[0] + uz * dY[1];
      if (1 + dt > 1e-9) dNeed = Math.max(dNeed, Math.round(ROUTER.fwdTurnRCm * cr / (1 + dt)) + ROUTER.pushEndPastArcCm);
    }
    const pushMax = pushPath.lenCm - ROUTER.pushTailRoomCm;   // leave the main gear + tail on the push path
    let pushEnd = Math.min(sJ + dNeed, Math.max(sJ, pushMax)), pushEndPt;
    { // a point on a line piece (deterministic, no trigonometry); inside an arc: the arc's end
      let i = pushPath.pieces.findIndex(p => p.s0Cm <= pushEnd && pushEnd < p.s0Cm + p.lenCm); if (i < 0) i = pushPath.pieces.length - 1;
      const p = pushPath.pieces[i];
      if (p.kind === 'line') { const u = Math.min(1, (pushEnd - p.s0Cm) / p.lenCm) * p.g.len; pushEndPt = [p.g.x0 + p.g.hx * u, p.g.z0 + p.g.hz * u]; }
      else { pushEnd = p.s0Cm + p.lenCm; const g = p.g; pushEndPt = [g.x0 + g.hx * g.T + g.ox * g.T, g.z0 + g.hz * g.T + g.oz * g.T]; }
    }
    // the swing remainder: from the push end back to K along the branch's own vertices
    const TV = [{ x: pushEndPt[0], z: pushEndPt[1], tag: { link: swing ?? seq[nPush - 1][0], cap: ROUTER.caps.taxilane }, node: null, li: nPush - 1 }];
    for (let k = pushPath.pieces.length - 1; k >= 0; k--) {   // the push path's piece starts between K and the push end, backwards
      const p = pushPath.pieces[k]; if (p.s0Cm >= pushEnd - 1 || p.s0Cm <= sJ) continue;
      TV.push({ x: p.g.x0, z: p.g.z0, tag: { link: swing ?? seq[nPush - 1][0], cap: ROUTER.caps.taxilane }, node: null, li: nPush - 1 });
    }
    const rest = vertsOf(seq, nPush);
    for (const q of rest) TV.push(q);   // rest[0] is K (the swing remainder above runs from the push end back to K)
    const vRw = TV[TV.length - 1]; const E = ENDS[end];
    TV[TV.length - 1].tag = { link: null, cap: ROUTER.caps.lineup, runway: E.rw };
    TV.push({ x: Math.round(vRw.x + E.h[0] * ROUTER.lineupLeadCm), z: Math.round(vRw.z + E.h[1] * ROUTER.lineupLeadCm), tag: { link: null, cap: ROUTER.caps.lineup, runway: E.rw }, node: null, li: seq.length });
    const full = buildPath(TV, { rNomCm: wideGeom ? PATH.rNomCm.wide : PATH.rNomCm.narrow, capOf: capFor(wideGeom) });
    const kRw = TV.length - 2; const sRw = full.vS[kRw]; const arcR = arcRangeAt(full, sRw);
    const sArcEnd = arcR ? arcR.s0Cm + arcR.lenCm : sRw;
    const lineupS = Math.min(full.lenCm - 100, sArcEnd + ROUTER.lineupAlignCm);
    const rwyS = Math.round(alongEnd(end, vRw.x, vRw.z) + (arcR ? arcR.g.T : 0) + (lineupS - sArcEnd));
    const path = trimPath(full, lineupS);
    const vS = full.vS;
    const crossings = crossingsOf(TV, vS, kRw);
    const hb = holdsNear(TV, vS, E.rw, sRw - ROUTER.holdSearchCm, sRw - 1);
    const luHold = hb.length ? hb[hb.length - 1] : { s: lateralCrossS(TV, vS, E.rw, kRw, -1, ROUTER.holdLatCm) ?? Math.max(0, sRw - ROUTER.holdLatCm), node: null, src: 'inf-90m' };
    const holds = [];
    for (const c of crossings) holds.push({ sCm: c.sInCm, node: c.node, kind: 'rwyhold', runway: c.runway, ref: c.ref });
    holds.push({ sCm: luHold.s, node: luHold.node, kind: 'lineup', runway: E.rw, src: luHold.src });
    holds.sort((a, b) => a.sCm - b.sCm);
    const blocks = blocksOf(TV, vS, path, nPush, seq, { startBox: true });
    for (const c of crossings) blocks.push({ id: 'rwy:' + c.runway, kind: 'rwy', s0Cm: c.sInCm, s1Cm: c.sOutCm, noStop: true, crossing: true });
    blocks.push({ id: 'rwy:' + E.rw, kind: 'rwy', s0Cm: luHold.s, s1Cm: path.lenCm, noStop: false, lineup: true });
    blocks.sort((a, b) => a.s0Cm - b.s0Cm || (a.id < b.id ? -1 : 1));
    const tailVec = (() => { const a = PV[iJ], b = PV[Math.min(PV.length - 1, iJ + 1)]; const dx = b.x - a.x, dz = b.z - a.z; return [dx, dz]; })();
    const pushBlocks = [];
    for (let i = 0; i < nPush; i++) { const lid = seq[i][0]; const nb = Math.max(1, Math.floor(lenCm[lid] / ROUTER.blockMinCm)); for (let b = 0; b < nb; b++) pushBlocks.push('b:' + lid + ':' + b); }
    pushBlocks.push('j:' + J); if (swing != null) pushBlocks.push('b:' + swing + ':' + (L[swing].a === J ? 0 : Math.max(1, Math.floor(lenCm[swing] / ROUTER.blockMinCm)) - 1));
    const toraCm = toraOf(end, entry);
    return {
      kind: 'dep', stand, end, entry, exitId: null, cls: clsOf(spanCm), geom: wideGeom ? 'wide' : 'narrow',
      links: seq.map(([a, b]) => [a, b]), lenCm: path.lenCm, pieces: path.pieces, path, vS, verts: TV,
      blocks, holds, crossings, lineup: { node: vRw.node, sCm: lineupS, rwySCm: rwyS, entrySCm: Math.round(alongEnd(end, vRw.x, vRw.z)), holdSCm: luHold.s, toraCm,
        // declared TORA: from the runway end (full length) or from the intersection (AIP (mirror) AD 2.13 'intersection')
        toraLeftCm: toraCm == null ? null : entry === 'full' ? toraCm - rwyS : toraCm - (rwyS - Math.round(alongEnd(end, vRw.x, vRw.z))) },
      push: { lenCm: pushEnd, pieces: pushPath.pieces, path: pushPath, verts: PV, nLinks: nPush, node: J, swing, swingVirtual, tailHdg: hdgOfVec(tailVec),
        run: { run: seq.slice(1, nPush).map(([id]) => id), node: J, swing, turnDeg: prec.turnDeg }, fallback: !!prec.fallback,
        optionA: optA ? { run: seq.slice(1, nPush).map(([id]) => id), node: J, swing, turnDeg: prec.turnDeg, record: { run: optA.run, node: optA.node, swing: optA.swing, turnDeg: optA.turnDeg } } : null, resources: pushBlocks },
      zones: [], src: 'inf', variant: tableVariant || 'live',
    };
  }
  function toraOf(end, entry) {
    // declared distances come from the airport data (aip_facts); the router knows them only through the table (baked)
    const r = T && T.runwayEnds && T.runwayEnds[end]; if (!r) return null;
    if (entry === 'full') return r.toraCm; const it = r.intersections && r.intersections[entry]; return it ? it.toraCm : null;
  }
  function assembleArr(exitId, stand, seq, spanCm, wideGeom) {
    const ex = exitById.get(exitId); const E = ENDS[ex.end];
    const v = nodeOf[ex.node]; const vx = Math.round(v.x * 100), vz = Math.round(v.z * 100);
    const V = [{ x: Math.round(vx - E.h[0] * ROUTER.rollLeadCm), z: Math.round(vz - E.h[1] * ROUTER.rollLeadCm), tag: { link: null, cap: ROUTER.caps.rapid, runway: E.rw }, node: null, li: -1 }];
    for (const q of vertsOf(seq, 0)) V.push(q);
    V[1].node = ex.node;
    const rapidTag = (t) => !!t && (t.runway || (t.link != null && L[t.link] && L[t.link].for_landing));
    const path = buildPath(V, { rNomCm: wideGeom ? PATH.rNomCm.wide : PATH.rNomCm.narrow, capOf: capFor(wideGeom), aLatOf: (a, b) => (rapidTag(a) || rapidTag(b) ? PATH.aLatRapidCms2 : PATH.aLatCms2) });
    const vS = path.vS; const sExit = vS[1];
    // vacate point: the first runway-holding position of the landing runway after the exit node
    const ha = holdsNear(V, vS, E.rw, sExit + 1, sExit + ROUTER.holdSearchCm * 2);
    const vac = ha.length ? ha[0] : { s: lateralCrossS(V, vS, E.rw, 1, 1, ROUTER.holdLatCm) ?? sExit + ROUTER.holdLatCm, node: null, src: 'inf-90m' };
    const crossings = crossingsOf(V, vS, null);
    // the lead-in: its first vertex (the junction)
    let kLead = V.length - 1; for (let k = V.length - 2; k >= 0; k--) { const l = L[V[k].tag.link]; if (l && l.use === 'stand') kLead = k; else break; }
    const arcL = arcRangeAt(path, vS[kLead]);
    const blocks = blocksOf(V, vS, path, 0, seq, {});
    let leadS = arcL ? arcL.s0Cm : vS[kLead];
    const box = blocks.find(b => b.kind === 'box' && b.node === V[kLead].node);
    if (box && box.noStop) leadS = box.s0Cm;
    const eb = endBoxes(V, vS);
    for (const b of eb) blocks.push(b);
    for (const c of crossings) blocks.push({ id: 'rwy:' + c.runway, kind: 'rwy', s0Cm: c.sInCm, s1Cm: c.sOutCm, noStop: true, crossing: true });
    blocks.push({ id: 'rwy:' + E.rw, kind: 'rwy', s0Cm: 0, s1Cm: vac.s, noStop: true, landing: true });
    blocks.sort((a, b) => a.s0Cm - b.s0Cm || (a.id < b.id ? -1 : 1));
    const holds = [];
    for (const c of crossings) holds.push({ sCm: c.sInCm, node: c.node, kind: 'rwyhold', runway: c.runway, ref: c.ref });
    for (const b of eb) holds.push({ sCm: Math.max(0, b.s0Cm - ROUTER.endBox.holdBeforeCm), node: null, kind: 'endbox', end: b.end });
    holds.push({ sCm: leadS, node: V[kLead].node, kind: 'leadin', dwellMs: ROUTER.leadinStopMs });
    holds.sort((a, b) => a.sCm - b.sCm);
    const zones = [{ s0Cm: Math.max(0, path.lenCm - ROUTER.caps.stopZoneCm), s1Cm: path.lenCm, vmaxCms: ROUTER.caps.stopCms, why: 'last 15 m to the stop' }];
    const ea = seq.some(([lid]) => EA.has(L[lid].ref));
    return {
      kind: 'arr', stand, end: ex.end, entry: null, exitId, cls: clsOf(spanCm), geom: wideGeom ? 'wide' : 'narrow',
      links: seq.map(([a, b]) => [a, b]), lenCm: path.lenCm, pieces: path.pieces, path, vS, verts: V,
      blocks, holds, crossings, lineup: null, push: null, zones,
      exit: { id: exitId, ref: ex.ref, node: ex.node, side: ex.side, sCm: sExit, rwySCm: ex.sCm, startRwySCm: ex.sCm - ROUTER.rollLeadCm },
      vacate: { sCm: vac.s, node: vac.node, src: vac.src }, endAround: ea, src: 'inf', variant: tableVariant || 'live',
    };
  }
  const hdgOfVec = (d) => { const a = Math.round(hdgVecDet(d[0], d[1]) * 10) / 10; return a; };

  // ------------------------------------------------------------------------------------------- public API
  const routeCache = new Map();
  function departure(stand, end, opts = {}) {
    const entry = opts.entry || 'full'; const span = opts.spanCm ?? 0; const wg = opts.geom ? opts.geom === 'wide' : span >= ROUTER.spanNarrowCm;
    const ck = 'D|' + stand + '|' + end + '|' + entry + '|' + clsOf(span) + '|' + wg; if (routeCache.has(ck)) return routeCache.get(ck);
    const prec = depSeq(stand, end, entry); const r = prec ? assembleDep(stand, end, entry, prec, span, wg) : null;
    routeCache.set(ck, r); return r;
  }
  function arrival(exitId, stand, opts = {}) {
    const span = opts.spanCm ?? 0; const cls = clsOf(span); const wg = opts.geom ? opts.geom === 'wide' : span >= ROUTER.spanNarrowCm;
    const ck = 'R|' + exitId + '|' + stand + '|' + cls + '|' + wg; if (routeCache.has(ck)) return routeCache.get(ck);
    const seq = arrSeq(exitId, stand, cls); const r = seq ? assembleArr(exitId, stand, seq, span, wg) : null;
    routeCache.set(ck, r); return r;
  }
  return {
    departure, arrival, exits, optionA: (s) => { const r = optionA(s); return r && r.run ? r : null; }, standSide, westOfWest, clsOf,
    // for tools/sim/build_routes.mjs and the tests
    _search: { depSeq, arrSeq, arrSeqs, findOptionA, search, depKeys, depGoalFn, exitById, exitList },
    graph: { L, N, nodeOf, adj, turns, lenCm, ptsCm, degree, RW, ENDS, alongEnd, latEast, standNode, pushOf, ownLeadin, standNames, other, canGo, dirOut, holdInf },
    info: () => ({ fingerprint: fp, table: tableNote, variant: tableVariant || 'live', closed: closed ? closed.size : 0, cached: routeCache.size }),
    clearCache: () => { routeCache.clear(); seqCache.clear(); },
  };
}

/** Douglas-Peucker simplification of an integer polyline (first and last points kept), deterministic */
export function simplify(P, tol) {
  if (P.length <= 2) return P.slice();
  const keep = new Uint8Array(P.length); keep[0] = 1; keep[P.length - 1] = 1;
  const st = [[0, P.length - 1]]; const t2 = tol * tol;
  while (st.length) {
    const [i, j] = st.pop(); const ax = P[i][0], az = P[i][1], dx = P[j][0] - ax, dz = P[j][1] - az, l2 = dx * dx + dz * dz;
    let best = -1, bd = t2;
    for (let k = i + 1; k < j; k++) {
      const px = P[k][0] - ax, pz = P[k][1] - az; let d2;
      if (l2 <= 0) d2 = px * px + pz * pz; else { const cr = px * dz - pz * dx; d2 = cr * cr / l2; }
      if (d2 > bd) { bd = d2; best = k; }
    }
    if (best > 0) { keep[best] = 1; st.push([i, best], [best, j]); }
  }
  const out = []; for (let k = 0; k < P.length; k++) if (keep[k]) out.push(P[k]); return out;
}

function angleDeg(a, b) { const c = a[0] * b[0] + a[1] * b[1], s = Math.abs(a[0] * b[1] - a[1] * b[0]); return 2 * atanDet(s / (1 + c)) * RAD2DEG; }
function hdgVecDet(dx, dz) {   // degrees true of (dx, dz) = atan2(dx, -dz), deterministic
  const PI = Math.PI; let a;
  if (dz < 0) a = atanDet(dx / -dz); else if (dz > 0) a = (dx >= 0 ? PI : -PI) - atanDet(dx / dz); else a = dx > 0 ? PI / 2 : dx < 0 ? -PI / 2 : 0;
  let h = a * RAD2DEG; if (h < 0) h += 360; return h;
}

// ------------------------------------------------------------------------------------------- NOTAM link mapping
/**
 * Links closed by a NOTAM target record (derived effect records only, design §2.5 / sources_sim.md §4.2 "Committed form").
 * targets: [{twy: [refs]}                          every link with that ref
 *           {twy: [refs], between: [X, Y]}         the part of each ref's chain between its junctions with X and Y
 *                                                   (X / Y: a taxiway ref or a runway id '18R/36L')]
 */
export function closedLinksFor(G, targets) {
  const L = G.links; const nodeOf = new Map(G.nodes.map(n => [n.id, n]));
  const byRef = new Map(); for (const l of L) if (l.ref) { if (!byRef.has(l.ref)) byRef.set(l.ref, []); byRef.get(l.ref).push(l); }
  const out = new Set(); const report = [];
  const junctions = (ref, X) => {   // nodes shared by a ref-link and an X-link (or a runway node of runway X)
    const nodes = new Set(); for (const l of byRef.get(ref) || []) { nodes.add(l.a); nodes.add(l.b); }
    const res = [];
    if (/\//.test(X)) { for (const v of nodes) { const n = nodeOf.get(v); if (n && (n.kind === 'rwy' || n.kind === 'rwy_end') && n.runway === X) res.push(v); } }
    else { const xn = new Set(); for (const l of byRef.get(X) || []) { xn.add(l.a); xn.add(l.b); } for (const v of nodes) if (xn.has(v)) res.push(v); }
    if (!res.length) {   // X does not meet the chain (e.g. B ends just short of H1 / H7): the chain node nearest to X, within 150 m
      const xs = /\//.test(X) ? G.nodes.filter(n => (n.kind === 'rwy' || n.kind === 'rwy_end') && n.runway === X).map(n => [n.x, n.z]) : (byRef.get(X) || []).flatMap(l => l.pts);
      let best = null, bd = 150 * 150;
      for (const v of [...nodes].sort((a, b) => a - b)) { const n = nodeOf.get(v); for (const q of xs) { const d = (n.x - q[0]) ** 2 + (n.z - q[1]) ** 2; if (d < bd) { bd = d; best = v; } } }
      if (best != null) res.push(best);
    }
    return res.sort((a, b) => a - b);
  };
  const chainPath = (ref, p, q) => {   // shortest path p -> q over links with this ref (BFS by length)
    const ls = byRef.get(ref) || []; const ad = new Map(); for (const l of ls) for (const v of [l.a, l.b]) { if (!ad.has(v)) ad.set(v, []); ad.get(v).push(l); }
    const dist = new Map([[p, 0]]), prev = new Map(); const Q = [p];
    while (Q.length) { Q.sort((a, b) => dist.get(a) - dist.get(b) || a - b); const v = Q.shift(); if (v === q) break; for (const l of ad.get(v) || []) { const w = l.a === v ? l.b : l.a; const d = dist.get(v) + l.len; if (!(dist.get(w) <= d)) { dist.set(w, d); prev.set(w, l); Q.push(w); } } }
    if (!dist.has(q)) return null; const path = []; let v = q; while (v !== p) { const l = prev.get(v); path.push(l.id); v = l.a === v ? l.b : l.a; } return { len: dist.get(q), ids: path };
  };
  for (const t of targets) {
    for (const ref of t.twy) {
      if (!t.between) { const ids = (byRef.get(ref) || []).map(l => l.id); ids.forEach(i => out.add(i)); report.push({ ref, n: ids.length }); continue; }
      const [X, Y] = t.between; const P = junctions(ref, X), Q = junctions(ref, Y); let best = null;
      for (const p of P) for (const q of Q) { const r = chainPath(ref, p, q); if (r && (!best || r.len < best.len)) best = r; }
      if (best) best.ids.forEach(i => out.add(i));
      report.push({ ref, between: t.between, n: best ? best.ids.length : 0, m: best ? Math.round(best.len) : 0 });
    }
  }
  return { ids: [...out].sort((a, b) => a - b), report };
}
