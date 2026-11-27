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
//   one-at-a-time lanes, the 18R/36L end boxes), holds, crossings, the line-up point and the push (incl. option A);
// - fix round 1: the path-level turn rule (a driven arc or a 40 m stretch turning > 100 deg is re-searched with its
//   transitions banned, ROUTER.pathTurn), lane blocks from the pieces, the swing branch's blocks on the taxi route and in
//   push.resources, the push end on a 33 m straight (both gears aligned), 20 km per off-H2 / H6 crossing for spans >= 36 m.
// Commit path: integers and + - * / sqrt only (path.js header); the precomputed table data/sha_routes.js (built by
// tools/sim/build_routes.mjs with this same module) replaces the searches.

// - fix round 2 (docs/phase3/movement.md "Verification fixes, round 2"): the push continues on the graph beyond the swing
//   link (the straight-ahead chain, real link ids), push.resources and the departure's start blocks come from the links
//   geometrically under the aircraft (nose gear path + the start-up fuselage, ROUTER.foot), one-at-a-time lanes by geometry,
//   junction boxes also for nodes beside the path that are not route vertices (geoBoxes), behind blocks held to the end of
//   the taxi's near stretch, every metre of every route inside some block (gap fill), the push path's own turn rule (re-search), arrivals that
//   re-cross the runway they landed on keep it occupied until the far side (no hold on the strip), wide-bodies full length.
import { buildPath, PATH, atanDet, RAD2DEG, turnProfile, projectOnPieces, arcPointDet } from './path.js';
import { TYPES } from '../aircraft/types.js';

// the largest nose-gear -> tail distance of each span class (n < 36 m, w 36-65 m, x >= 65 m) over js/aircraft/types.js SPEC:
// the start-up fuselage footprint behind the push end (fix round 2, H1) [inf: geometry of the type table]
// the largest wheelbase of each span class: the push path is (nearly) straight for this far past the push end (fix round 2)
const WB_CM = (() => { const o = { n: 0, w: 0, x: 0 }; for (const t of Object.values(TYPES)) { const sp = t.wing.span * 100; const c = sp < 3600 ? 'n' : sp < 6500 ? 'w' : 'x'; o[c] = Math.max(o[c], Math.ceil(t.xMain - t.xNose) * 100); } return o; })();
const TAIL_CM = (() => { const o = { n: 0, w: 0, x: 0 }; for (const t of Object.values(TYPES)) { const sp = t.wing.span * 100; const c = sp < 3600 ? 'n' : sp < 6500 ? 'w' : 'x'; o[c] = Math.max(o[c], Math.ceil((t.L - t.xNose) * 100 / 100) * 100); } return o; })();

export const ROUTER = {
  fullLengthCm: 12000,        // a take-off entry within 120 m of the runway end counts as full length (H1, H7, T6, the end connectors) [inf]
  intersection: { '18R': 'H2', '36L': 'H6' },          // AIP (mirror) AD 2.20 2.1.7 (intersection take-off)
  lineupTurnCos: 0.7071067811865476,                   // the runway link after the line-up points within 45 deg of the take-off heading
  optA: { maxRunCm: 6000, maxRunLinks: 2, turnCos: -0.17364817766693033,     // <= 60 m, <= 2 lanes, turns <= 100 deg (design §4.1)
    longRunCm: 15000, longRunLinks: 4 },                                       // retry for an end the short runs cannot reach (inf)
  geoTurnCos: -0.17364817766693033,                    // cos 100 deg
  xPenCm: 500000,             // 5 km per 18R/36L crossing (design §4.1, inf)
  xPenWideCm: 2000000,        // span >= 36 m: 20 km per 18R/36L crossing other than H2 (landing 18L) / H6 (landing 36R), more than any
                              // detour along B (fix round 1, V10: 5 km let the far exits B6 / B1 / end connectors cross at H6 / H7 / H2) [inf]
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
  // the push path is straight past the push end for the class's largest wheelbase (fix round 1, V2: 33 m for every class;
  // fix round 2: n 19 / w 33 / x 32 m from js/aircraft/types.js), both gears aligned on it; bends of less than pushAlignTh
  // (10 deg: OSM digitising curvature, gentle lane bends) do not count, and a push end inside such a gentle arc stays where
  // it is (round 1 moved it past every 0.2 deg kink and to the end of any arc: pushes up to 98 m past K on the real chain) [inf]
  pushAlignTh: 0.17453292519943295, pushAlignExtraCm: 2000,   // ... and the alignment moves the push end at most 20 m (a curving lane: the push ends on the curve)
  pushAlignCm: WB_CM,
  caps: { taxiway: 1200, taxiwayWide: 1000, taxilane: 700, leadin: 300, rapid: 2500, lineup: 500, push: 120, stopZoneCm: 1500, stopCms: 100 },   // rapid: the 25 m/s turn-off speed, no acceleration on the exit (design §4.4: entry <= 25 m/s, decelerating)
  leadinStopMs: 5000,         // arrivals stop 5 s before turning onto the lead-in (AIP (mirror) AD 2.20 3.2.2.2; aip_facts.stop_before_leadin; 5 s inf)
  // path-level turn rule (fix round 1, V3; AIP (mirror) AD 2.20 2.3.1 "turns of more than 90 deg forbidden", + 10 deg of
  // digitising tolerance as the turns table): a route whose DRIVEN path has an arc of more than maxDeg or a heading change
  // of more than maxDeg within windowCm is re-searched with the transitions in that stretch banned (up to maxIter times);
  // if no such route exists the shortest one is kept and route.turn says so [inf]
  pathTurn: { maxDeg: 100, windowCm: 4000, maxIter: 8, padCm: 1000 },
  pushResCm: 9000,            // push.resources: the swing branch's blocks within 90 m of K (push end + main gear + tail) [inf]
  // fix round 2 (H1): the push continues on the graph past the swing link X: at each far node the straight-ahead link
  // (deflection <= 45 deg, a two-way or one-way apron lane / taxiway, not a lead-in or runway) up to swingExtCm from K;
  // the links under the aircraft are found geometrically: every open non-runway link centreline within tolCm (4 m + 0.5 m
  // for the chord sampling of arcs) of the nose-gear path, the push path to the tail and the straight start-up fuselage
  // (nose gear -> tail, tailCm by span class), every junction node within boxCm (the 15 m junction box pad + 0.5 m) [inf]
  chainCos: 0.7071067811865476,
  foot: { tolCm: 450, laneTolCm: 650, boxCm: 1550, stepCm: 100, cellCm: 1000, tailCm: TAIL_CM },   // lanes: 6 m + 0.5 m (nose, main gear or tail near a lane)
  // one-at-a-time lanes by geometry (H1): a path sample is on lane <ref> when an exclusive lane centreline lies within
  // laneTolCm of the nose gear (3 m + 0.5 m chord tolerance) and runs within 37 deg of the path direction (|cos| >= 0.8),
  // or when the piece's own link carries the ref; runs closer than laneGapCm are joined [inf]
  // a near-run (samples within laneTolCm in any direction) is a lane block when it contains a parallel sample, so the entry
  // and exit stretches (merging onto / leaving the lane at an angle) are in it and a bare crossing of a lane mouth is not;
  // a lane the push held (push.resources) continues from s = 0 when the taxi reaches it within laneHoldCm [inf]
  laneTolCm: 350, laneCos: 0.8, laneGapCm: 300, laneHoldCm: 6000,
  pushTurn: { maxDeg: 100, windowCm: 4000 },
  pushMergeMaxCos: -0.17364817766693033,   // push paths merge two corners only into one of < 100 deg (M2; taxi paths: 150 deg) [inf]   // the driven push path (stand -> push end) keeps the path-level turn rule (M2) [inf]
  wideFullLength: true,       // span >= 36 m (code D-F) always lines up at full length (design §4.2: code C may use H2 / H6) [inf]
  // fix round 3 (V3-1): after a runway no-stop block (a crossing's strip, the landing roll to the vacate point) and an end
  // box, the first stop the scheduler may plan leaves the WHOLE aircraft beyond the far runway-holding position: a no-stop
  // marker block (kind 'clear', res: false = not a resource) over [block start, far end + tail], tail = the class's largest
  // nose-gear -> tail distance (ROUTER.foot.tailCm: n 40 / w 71 / x 69 m, >= every perf.js type of the class) or
  // opts.tailCm; the runway block carries tailClearCm (design §4.5 no-stop zones "crossing hold -> first block beyond the
  // runway"; the 90 m holding position protects the strip only when the tail is past it, AIP (mirror) AD 2.20 holding
  // positions via sha_taxigraph hold_inf) [inf]
  tailClear: { kinds: ['crossing', 'landing', 'endbox'] },
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

  // ------------------------------------------------------------------------------------------- footprints (fix round 2, H1)
  // Spatial index of the open non-runway link centrelines (integer cm, ROUTER.foot.cellCm cells) and of the junction nodes;
  // deterministic sampling of a path's pieces (lines linear, arcs by chord bisection: + - * / sqrt only), so the links under
  // an aircraft are found by geometry, not from the route's tags. Commit path: no trigonometry.
  const FO = ROUTER.foot, FG = FO.cellCm;
  const cumCm = L.map((l) => { const p = ptsCm[l.id]; const c = [0]; for (let i = 1; i < p.length; i++) { const dx = p[i][0] - p[i - 1][0], dz = p[i][1] - p[i - 1][1]; c.push(c[i - 1] + Math.sqrt(dx * dx + dz * dz)); } return c; });
  const nBlocks = (lid) => Math.max(1, Math.floor(lenCm[lid] / ROUTER.blockMinCm));
  const gKey = (cx, cz) => (cx + 4096) * 8192 + (cz + 4096);
  const segGrid = new Map(), nodeGrid = new Map(), laneGrid = new Map();   // laneGrid: the one-at-a-time lanes only
  const gAdd = (G2, k, v) => { let a = G2.get(k); if (!a) G2.set(k, a = []); a.push(v); };
  for (const l of L) {
    if (l.status !== 'open' || l.use === 'runway') continue; const p = ptsCm[l.id];
    for (let i = 1; i < p.length; i++) {
      const x0 = Math.floor(Math.min(p[i - 1][0], p[i][0]) / FG), x1 = Math.floor(Math.max(p[i - 1][0], p[i][0]) / FG);
      const z0 = Math.floor(Math.min(p[i - 1][1], p[i][1]) / FG), z1 = Math.floor(Math.max(p[i - 1][1], p[i][1]) / FG);
      for (let cx = x0; cx <= x1; cx++) for (let cz = z0; cz <= z1; cz++) { gAdd(segGrid, gKey(cx, cz), l.id * 65536 + i); if (l.ref && EXCL.has(l.ref)) gAdd(laneGrid, gKey(cx, cz), l.id * 65536 + i); }
    }
  }
  const isJunction = (v) => { const n = nodeOf[v]; return !!n && n.kind === 'junction' && (degree.get(v) || 0) >= 3; };
  for (const n of N) if (isJunction(n.id)) gAdd(nodeGrid, gKey(Math.floor(n.x * 100 / FG), Math.floor(n.z * 100 / FG)), n.id);
  const twyNode = (v) => (adj.get(v) || []).some(id => L[id].kind === 'taxiway');
  let maxNode = 0; for (const n of N) if (n.id > maxNode) maxNode = n.id;
  const skipS = new Float64Array(maxNode + 1), skipG = new Int32Array(maxNode + 1); let skipGen = 0;   // geoBoxes scratch
  /** calls fn(lid, i, u, d2) for every indexed segment within tol (cm) of (x, z); a segment may be reported more than once */
  function nearSegs(x, z, tol, fn, grid = segGrid) {
    const cx = Math.floor(x / FG), cz = Math.floor(z / FG), t2 = tol * tol, rr = Math.ceil(tol / FG);
    for (let a = -rr; a <= rr; a++) for (let b = -rr; b <= rr; b++) {
      const arr = grid.get(gKey(cx + a, cz + b)); if (!arr) continue;
      for (const code of arr) {
        const lid = Math.floor(code / 65536), i = code - lid * 65536; const p = ptsCm[lid];
        const ax = p[i - 1][0], az = p[i - 1][1], ex = p[i][0] - ax, ez = p[i][1] - az, l2 = ex * ex + ez * ez;
        let u = l2 > 0 ? ((x - ax) * ex + (z - az) * ez) / l2 : 0; if (u < 0) u = 0; else if (u > 1) u = 1;
        const dx = ax + ex * u - x, dz = az + ez * u - z, d2 = dx * dx + dz * dz;
        if (d2 <= t2) fn(lid, i, u, d2);
      }
    }
  }
  /** the block index (from the link's a end) of the point at fraction u of segment i of link lid */
  const blockAt = (lid, i, u) => { const c = cumCm[lid]; const tot = c[c.length - 1]; const nb = nBlocks(lid); if (!(tot > 0)) return 0; const f = (c[i - 1] + (c[i] - c[i - 1]) * u) / tot; return Math.min(nb - 1, Math.max(0, Math.floor(f * nb))); };
  /**
   * Sample points [x, z, s] every <= stepCm along pieces over stations [sA, sB]; beyond the last piece the path continues
   * straight along its end tangent. Arcs (also those cut by trimPath) are evaluated on their full circle by bisection.
   */
  function samplePieces(pieces, sA, sB, stepCm = FO.stepCm) {
    const out = []; let endX = null, endZ = null, endHx = 0, endHz = 0, endS = 0;
    for (const p of pieces) {
      const e = p.s0Cm + p.lenCm; const g = p.g;
      if (p.kind === 'line') { endX = g.x0 + g.hx * p.lenCm; endZ = g.z0 + g.hz * p.lenCm; endHx = g.hx; endHz = g.hz; }
      else { const bx = g.x0 + g.hx * g.T + g.ox * g.T, bz = g.z0 + g.hz * g.T + g.oz * g.T; endHx = g.ox; endHz = g.oz;
        // a cut arc ends earlier: its end point is found below by bisection; the tangent is only used for the straight extension
        endX = bx; endZ = bz; }
      endS = e;
      if (e < sA || p.s0Cm > sB || p.lenCm <= 0) continue;
      if (p.kind === 'line') {
        const n = Math.max(1, Math.ceil(p.lenCm / stepCm));
        for (let j = 0; j <= n; j++) { const d = p.lenCm * j / n, s = p.s0Cm + d; if (s < sA || s > sB) continue; out.push([g.x0 + g.hx * d, g.z0 + g.hz * d, s]); }
      } else {
        const thF = 2 * atanDet(g.T / g.R), lenF = g.R * thF;       // the full arc (a cut arc keeps its T)
        let n = 1; while (lenF / n > stepCm) n *= 2;
        const P = new Array(n + 1); P[0] = [g.x0, g.z0]; P[n] = [g.x0 + g.hx * g.T + g.ox * g.T, g.z0 + g.hz * g.T + g.oz * g.T];
        for (let h = n; h > 1; h >>= 1) for (let j = 0; j < n; j += h) {   // midpoints on the circle: C + R (P + Q - 2C) / |P + Q - 2C|
          const a = P[j], b = P[j + h]; const mx = a[0] + b[0] - 2 * g.cx, mz = a[1] + b[1] - 2 * g.cz, m = Math.sqrt(mx * mx + mz * mz) || 1;
          P[j + h / 2] = [g.cx + mx * g.R / m, g.cz + mz * g.R / m];
        }
        for (let j = 0; j <= n; j++) { const d = lenF * j / n; if (d > p.lenCm + 1) break; const s = p.s0Cm + d; if (s < sA || s > sB) continue; out.push([P[j][0], P[j][1], s]); }
        if (p.lenCm + 1 < lenF) { const last = out.length ? out[out.length - 1] : null; if (last) { endX = last[0]; endZ = last[1]; } }   // cut arc: approx end
      }
    }
    if (endX != null && sB > endS) for (let d = stepCm; endS + d <= sB + stepCm - 1; d += stepCm) { const dd = Math.min(d, sB - endS); out.push([endX + endHx * dd, endZ + endHz * dd, endS + dd]); if (dd < d) break; }
    return out;
  }
  /** links, blocks, junction boxes and one-at-a-time lanes under a set of points (tol: centreline distance) */
  // pts: [x, z, s, inStart]: one pass fills the footprint of all points and of the points flagged inStart
  function footOf(pts, tol = FO.tolCm, boxTol = FO.boxCm, laneTol = FO.laneTolCm) {
    const mk = () => ({ blocks: new Set(), links: new Set(), lanes: new Set(), boxes: new Set() }); const A = mk(), B = mk();
    const b2 = boxTol * boxTol, t2 = tol * tol, l2 = laneTol * laneTol, rr = Math.ceil(boxTol / FG);
    for (const [x, z, , inS] of pts) {
      nearSegs(x, z, Math.max(tol, laneTol), (lid, i, u, d2) => { const r = L[lid].ref; const ln = r && EXCL.has(r) && d2 <= l2; const bk = d2 <= t2 ? 'b:' + lid + ':' + blockAt(lid, i, u) : null;
        for (const F of inS ? [A, B] : [A]) { if (ln) F.lanes.add(r); if (bk) { F.links.add(lid); F.blocks.add(bk); } } });
      const cx = Math.floor(x / FG), cz = Math.floor(z / FG);
      for (let a = -rr; a <= rr; a++) for (let b = -rr; b <= rr; b++) { const arr = nodeGrid.get(gKey(cx + a, cz + b)); if (!arr) continue; for (const v of arr) { const n = nodeOf[v]; const dx = n.x * 100 - x, dz = n.z * 100 - z; if (dx * dx + dz * dz <= b2) { A.boxes.add('j:' + v); if (inS) B.boxes.add('j:' + v); } } }
    }
    const out = (F) => ({ blocks: [...F.blocks].sort(), links: [...F.links].sort((a, b) => a - b), lanes: [...F.lanes].sort(), boxes: [...F.boxes].sort() });
    return { all: out(A), start: out(B) };
  }
  /** one-at-a-time lane runs by geometry along pieces [0, sB]: [{ref, s0, s1}] (nose gear within laneTolCm, parallel) */
  // (only the pieces whose bounding box, grown by laneTolCm, touches a lane cell are sampled)
  const pieceNearLane = (p) => {
    const g = p.g; let x0, x1, z0, z1;
    if (p.kind === 'line') { x0 = Math.min(g.x0, g.x0 + g.hx * p.lenCm); x1 = Math.max(g.x0, g.x0 + g.hx * p.lenCm); z0 = Math.min(g.z0, g.z0 + g.hz * p.lenCm); z1 = Math.max(g.z0, g.z0 + g.hz * p.lenCm); }
    else { const ex = g.x0 + g.hx * g.T + g.ox * g.T, ez = g.z0 + g.hz * g.T + g.oz * g.T; x0 = Math.min(g.x0, ex, g.cx - g.R); x1 = Math.max(g.x0, ex, g.cx + g.R); z0 = Math.min(g.z0, ez, g.cz - g.R); z1 = Math.max(g.z0, ez, g.cz + g.R);
      x0 = Math.max(x0, Math.min(g.x0, ex) - p.lenCm); x1 = Math.min(x1, Math.max(g.x0, ex) + p.lenCm); z0 = Math.max(z0, Math.min(g.z0, ez) - p.lenCm); z1 = Math.min(z1, Math.max(g.z0, ez) + p.lenCm); }
    const pad = ROUTER.laneTolCm; const c0 = Math.floor((x0 - pad) / FG), c1 = Math.floor((x1 + pad) / FG), r0 = Math.floor((z0 - pad) / FG), r1 = Math.floor((z1 + pad) / FG);
    for (let cx = c0; cx <= c1; cx++) for (let cz = r0; cz <= r1; cz++) if (laneGrid.has(gKey(cx, cz))) return true;
    return false;
  };
  function laneRunsGeo(pieces, sB) {
    const pts = []; for (const p of pieces) { if (p.s0Cm > sB || p.lenCm <= 0 || !pieceNearLane(p)) continue; for (const q of samplePieces([p], p.s0Cm, Math.min(sB, p.s0Cm + p.lenCm))) pts.push(q); }
    const runs = new Map(); const t2 = ROUTER.laneTolCm;
    const rl = Math.ceil(t2 / FG); let lastC = null, lastV = false;
    const nearLane = (x, z) => { const cx = Math.floor(x / FG), cz = Math.floor(z / FG); const ck = gKey(cx, cz); if (ck === lastC) return lastV; lastC = ck; lastV = false;
      for (let a = -rl; a <= rl && !lastV; a++) for (let b = -rl; b <= rl; b++) if (laneGrid.has(gKey(cx + a, cz + b))) { lastV = true; break; } return lastV; };
    for (let k = 0; k < pts.length; k++) {
      const [x, z, s] = pts[k]; if (!nearLane(x, z)) continue;
      const nx = pts[k + 1] && pts[k + 1][2] - s <= 2 * FO.stepCm && pts[k + 1][2] > s ? pts[k + 1] : null, pv = pts[k - 1] && s - pts[k - 1][2] <= 2 * FO.stepCm && s > pts[k - 1][2] ? pts[k - 1] : null;
      const q = nx || pv; if (!q) continue;
      let hx = (q[0] - x) * (nx ? 1 : -1), hz = (q[1] - z) * (nx ? 1 : -1); const hm = Math.sqrt(hx * hx + hz * hz); if (!(hm > 0)) continue; hx /= hm; hz /= hm;
      const refs = new Map();   // ref -> parallel?
      nearSegs(x, z, t2, (lid, i) => { const r = L[lid].ref; if (refs.get(r)) return; const p = ptsCm[lid]; const ex = p[i][0] - p[i - 1][0], ez = p[i][1] - p[i - 1][1], el = Math.sqrt(ex * ex + ez * ez); refs.set(r, el > 0 && Math.abs((ex * hx + ez * hz) / el) >= ROUTER.laneCos); }, laneGrid);
      for (const [r, par] of refs) { const a = runs.get(r); if (!a) runs.set(r, [[s, s, par]]); else { const last = a[a.length - 1]; if (s - last[1] <= ROUTER.laneGapCm) { last[1] = s; last[2] = last[2] || par; } else a.push([s, s, par]); } }
    }
    const out = []; for (const [ref, a] of runs) for (const [s0, s1, par] of a) if (par) out.push({ ref, s0: Math.round(s0), s1: Math.round(s1) });
    return out;
  }
  /** the straight-ahead chain beyond the swing link X (fix round 2, H1): [[lid, fromNode], ...], X first */
  function swingChain(x, K) {
    const ch = [[x, K]]; let cur = x, v = other(L[x], K), acc = lenCm[x]; const seen = new Set([x]);
    while (acc < ROUTER.swingExtCm) {
      const d0 = dirOut(cur, v); const din = [-d0[0], -d0[1]]; let best = null, bc = -2;
      for (const y of adj.get(v) || []) {
        if (seen.has(y)) continue; const Y = L[y]; if (!laneOK(Y) || Y.use === 'arrival') continue;   // a departure's push stays off the arrival-only lanes
        const d = dirOut(y, v); const c = din[0] * d[0] + din[1] * d[1];
        if (c >= ROUTER.chainCos && (c > bc || (c === bc && y < best))) { bc = c; best = y; }
      }
      if (best == null) break;
      ch.push([best, v]); seen.add(best); acc += lenCm[best]; cur = best; v = other(L[best], v);
    }
    return ch;
  }

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
    if (ctx.ban && ctx.ban.has(lin + ':' + v + ':' + lout.id)) return -1;   // path-level turn rule (V3)
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
      else { ctx.xPen = { rwy: '18R/36L', cm: ROUTER.xPenWideCm, free: ROUTER.wideCrossFree[end] }; if (cls === 'w') ctx.eaPenCm = ROUTER.eaLimitedPenCm; }
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
  // live departure search over every push candidate of the stand (short runs, then long); ban = {trans: Set('lin:v:lout'),
  // start: Set('swing:y')} from the path-level turn rule (V3). Returns Map key -> {seq, nPush, swing, turnDeg[, fallback]}
  function liveDep(stand, keys, ban) {
    const P = pushOf.get(stand); const out = new Map(); if (!P) return out;
    const ctx = { role: 'dep', spanCm: 0, ban: ban ? ban.trans : null };
    const run = (cands) => { const owner = new Map(), starts = [];
      for (const c of cands) for (const [y, w, c0] of c.starts) { if (ban && ban.start.has(c.swing + ':' + y)) continue; if (ban && ban.push && ban.push.has(candKey(c.run, c.swing))) continue; const k = y * 2 + (L[y].b === w ? 1 : 0); const o = owner.get(k); if (!o || c0 < o.c0) owner.set(k, { c0, c }); }
      for (const [k, o] of [...owner.entries()].sort((a, b) => a[0] - b[0])) starts.push([k >> 1, (k & 1) ? L[k >> 1].b : L[k >> 1].a, o.c0]);
      return { owner, res: search(starts, depGoalFn(END_IDS), ctx, keys) }; };
    const A1 = run(pushCands(stand)); let A2 = null, fb = null;
    for (const k of keys) {
      let A = A1, r = A1.res.get(k), rec = null;
      if (!r) { if (!A2) A2 = run(pushCands(stand, { long: true })); A = A2; r = A2.res.get(k); }
      if (r) {
        const [y, K] = r.seq[0]; const c = A.owner.get(y * 2 + (L[y].b === other(L[y], K) ? 1 : 0)).c;
        const seq = [[P.id, standNode.get(stand)]]; c.run.forEach((id, i) => seq.push([id, c.runFrom[i]])); seq.push(...r.seq);
        rec = { seq, nPush: 1 + c.run.length, swing: c.swing, turnDeg: c.turnDeg };
      } else {   // no geometric push: the graph's own push-end transition, flagged (never seen on the committed graph)
        if (!fb) fb = search(normalStarts(stand), depGoalFn(END_IDS), ctx, keys);
        const q = fb.get(k); if (q) rec = { seq: q.seq, nPush: 1, swing: null, turnDeg: null, fallback: true };
      }
      out.set(k, rec);
    }
    return out;
  }
  const candKey = (run, swing) => run.join(',') + '>' + swing;   // a push candidate (tail-first run + swing link)
  // the path-level turn check (V3) of an assembled route: null, or the bans for the stretch that turns too much
  function turnBans(route, nTaxi0) {
    const PT = ROUTER.pathTurn; const tp = turnProfile(route.path, PT.windowCm);
    if (tp.maxArcDeg <= PT.maxDeg && tp.maxWinDeg <= PT.maxDeg) return null;
    const wins = []; if (tp.maxArcDeg > PT.maxDeg) wins.push([tp.arcS0Cm, tp.arcS1Cm]); if (tp.maxWinDeg > PT.maxDeg) wins.push([tp.winS0Cm, tp.winS1Cm]);
    const V = route.verts, vS = route.vS; const bans = [];
    for (let k = 1; k < V.length - 1; k++) {
      const nd = V[k].node; if (nd == null || (V[k].li != null && V[k].li < nTaxi0)) continue;
      if (!wins.some(([a, b]) => vS[k] >= a - PT.padCm && vS[k] <= b + PT.padCm)) continue;
      const lin = V[k - 1].tag && V[k - 1].tag.link, lout = V[k].tag && V[k].tag.link; if (lin == null || lout == null || lin === lout) continue;
      if (route.push && route.push.swing === lin && route.push.node === nd) bans.push('s:' + lin + ':' + lout);
      else bans.push('t:' + lin + ':' + nd + ':' + lout);
    }
    return { tp, bans };
  }
  const turnStats = { checked: 0, rerouted: 0, kept: 0, pushBanned: 0, pushKept: 0 };
  // live departures: the path-level turn rule on the taxi path (V3) and, since fix round 2, on the driven push path (M2) and
  // the push end on a real link (H1): a failing push candidate (run + swing) is banned and the search repeated; if nothing
  // passes, the first route is kept and route.turn / route.push.turn / route.push.onGraph say so
  function depTurnFix(stand, key, rec0) {
    if (!rec0 || rec0.fallback || rec0.swing == null) return rec0;
    const [end, entry] = key.split('|'); const ban = { trans: new Set(), start: new Set(), push: new Set() };
    let rec = rec0; turnStats.checked++; let pushBans = 0;
    for (let it = 0; it <= ROUTER.pathTurn.maxIter; it++) {
      let added = 0, bad = false;
      for (const wg of [false, true]) {
        const rt = assembleDep(stand, end, entry, rec, wg ? ROUTER.spanNarrowCm : 0, wg, true);
        if (!wg && (!rt.push.turn.ok || !rt.push.onGraph)) { const kk = candKey(rt.push.run.run, rt.push.swing); bad = true; if (!ban.push.has(kk)) { ban.push.add(kk); added++; pushBans++; } }
        const v = turnBans(rt, rec.nPush); if (!v) continue; bad = true;
        for (const b of v.bans) { const set = b[0] === 's' ? ban.start : ban.trans; const kk = b.slice(2); if (!set.has(kk)) { set.add(kk); added++; } }
      }
      if (!bad) { if (it) turnStats.rerouted++; if (pushBans) turnStats.pushBanned++; return it ? { ...rec, turnRerouted: it } : rec; }
      if (!added || it === ROUTER.pathTurn.maxIter) break;
      const r = liveDep(stand, [key], ban).get(key); if (!r || r.fallback) break; rec = r;
    }
    turnStats.kept++; if (pushBans) turnStats.pushKept++; return rec0;
  }
  function depSeq(stand, end, entry) {
    const ck = 'd|' + stand + '|' + end + '|' + entry; if (seqCache.has(ck)) return seqCache.get(ck);
    const P = pushOf.get(stand); if (!P) return null;
    let rec = tableSeq('dep', 'dep|' + end + '|' + entry, stand, standNode.get(stand));
    if (rec === undefined) {   // live: one multi-source search for every end, then the path-level turn check per key
      const base = liveDep(stand, depKeys(END_IDS), null);
      for (const k of depKeys(END_IDS)) seqCache.set('d|' + stand + '|' + k, depTurnFix(stand, k, base.get(k) || null));
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
    if (seq === undefined) seq = arrTurnFix(exitId, stand, cls, arrSeqs(exitId, cls).get(stand) || null);
    seqCache.set(ck, seq); return seq;
  }
  // the path-level turn rule (V3) for a live arrival: re-search to this stand with the offending transitions banned
  function arrTurnFix(exitId, stand, cls, seq0) {
    if (!seq0) return seq0;
    const ex = exitById.get(exitId); const wg = cls !== 'n'; const sp = clsSpan[cls];
    const ban = new Set(); let seq = seq0; turnStats.checked++;
    const goal = (lid, v) => { const l = L[lid]; return l.use === 'stand' && l.stand === stand && standNode.get(stand) === v ? stand : null; };
    for (let it = 0; it <= ROUTER.pathTurn.maxIter; it++) {
      const v = turnBans(assembleArr(exitId, stand, seq, sp, wg, true), 0);
      if (!v) { if (it) turnStats.rerouted++; return seq; }
      let added = 0; for (const b of v.bans) { const kk = b.slice(2); if (!ban.has(kk)) { ban.add(kk); added++; } }
      if (!added || it === ROUTER.pathTurn.maxIter) break;
      const res = search([[ex.link, other(L[ex.link], ex.node), lenCm[ex.link]]], goal, { ...arrCtx(ex.end, cls), ban }, [stand]);
      const r = res.get(stand); if (!r) break; seq = r.seq;
    }
    turnStats.kept++; return seq0;
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
      const latIn = hb.length ? null : lateralCrossS(V, vS, rw, k, -1, ROUTER.holdLatCm), latOut = ha.length ? null : lateralCrossS(V, vS, rw, k, 1, ROUTER.holdLatCm);
      const sIn = hb.length ? hb[hb.length - 1].s : latIn ?? Math.max(0, s - ROUTER.holdLatCm);
      const sOut = ha.length ? ha[0].s : latOut ?? s + ROUTER.holdLatCm;
      // how the holds were found (fix round 2, L1): an OSM / inferred holding position, the 90 m line on the route, or the
      // bare fallback s -+ 90 m (the route never reaches the 90 m line on that side: e.g. a re-crossing of the runway just landed on)
      const inHow = hb.length ? 'hold' : latIn != null ? 'lat90' : 'fallback', outHow = ha.length ? 'hold' : latOut != null ? 'lat90' : 'fallback';
      const along = {}; for (const e of END_IDS) if (RWY_OF[e] === rw) along[e] = Math.round(alongEnd(e, n.x * 100, n.z * 100));
      let nearEnd = null; for (const e of Object.keys(along)) if (along[e] >= 0 && along[e] <= 50000) nearEnd = e;
      out.push({ runway: rw, node: nd, sCm: s, ref: lout.ref || lin.ref || null, nearEnd, alongCm: along, sInCm: sIn, sOutCm: sOut, holdSrc: hb.length ? hb[hb.length - 1].src : 'inf-90m', inHow, outHow });
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
    // one-aircraft-at-a-time lanes (AD 2.20 3.1.5), from the PIECES (fix round 1, V4): a piece is on a lane when its
    // in-link or (arcs) its out-link carries the lane's ref, so the entry and exit fillets and a departure's swing
    // remainder (from the push end back to K) are inside the lane block
    const open = new Map(); const runs = [];   // ref -> [s0, s1] of the run being built
    for (const p of path.pieces) {
      const refs = new Set(); for (const id of [p.linkId, p.kind === 'arc' && p.tagOut ? p.tagOut.link : null]) { const l = id != null ? L[id] : null; if (l && l.ref && EXCL.has(l.ref)) refs.add(l.ref); }
      for (const [ref, r] of [...open]) if (!refs.has(ref)) { runs.push({ ref, s0: r[0], s1: r[1] }); open.delete(ref); }
      for (const ref of [...refs].sort()) { const r = open.get(ref); if (r) r[1] = p.s0Cm + p.lenCm; else open.set(ref, [p.s0Cm, p.s0Cm + p.lenCm]); }
    }
    for (const [ref, r] of open) runs.push({ ref, s0: r[0], s1: r[1] });
    // fix round 2 (H1): plus the stretches where the nose gear runs ALONG a lane geometrically (another link's tag, e.g. a
    // parallel or overlapping centreline, or the swing chain); runs of one ref closer than laneGapCm are one block
    for (const r of laneRunsGeo(path.pieces, path.lenCm)) runs.push({ ...r, geo: true });
    const byRef = new Map(); for (const r of runs) { if (!byRef.has(r.ref)) byRef.set(r.ref, []); byRef.get(r.ref).push(r); }
    for (const ref of [...byRef.keys()].sort()) {
      const a = byRef.get(ref).sort((p, q) => p.s0 - q.s0 || p.s1 - q.s1); let cur = null;
      for (const r of a) { if (cur && r.s0 <= cur.s1 + ROUTER.laneGapCm) { cur.s1 = Math.max(cur.s1, r.s1); cur.geo = cur.geo && r.geo; } else { if (cur) B.push(laneBlk(cur)); cur = { ref, s0: r.s0, s1: r.s1, geo: !!r.geo }; } }
      if (cur) B.push(laneBlk(cur));
    }
    return B;
  }
  const laneBlk = (r) => ({ id: 'lane:' + r.ref, kind: 'lane', s0Cm: r.s0, s1Cm: r.s1, noStop: false, geoOnly: r.geo ? true : undefined });
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

  function assembleDep(stand, end, entry, prec, spanCm, wideGeom, lite = false, tailOpt = null) {   // lite: path, turn and push checks only (depTurnFix)
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
    // push path: push link + run (tail first) + into the swing branch X and on along the straight-ahead chain beyond X's far
    // node (fix round 2, H1: real links with their ids; a virtual straight only where the graph ends within swingExtCm)
    const chain = swing != null ? swingChain(swing, J) : [];
    const PV = [];
    for (let i = 0; i < nPush; i++) { const [lid, from] = seq[i]; const p = simpFrom(lid, from); for (let k = PV.length ? 1 : 0; k < p.length; k++) PV.push({ x: p[k][0], z: p[k][1], tag: { link: lid, cap: ROUTER.caps.push }, node: k === p.length - 1 ? other(L[lid], from) : null }); }
    const iJ = PV.length - 1;
    let ext = 0; const chainUsed = [];   // {lid, from, to, iFrom, iTo (PV index of the far node, or null when cut at swingExtCm)}
    for (const [cid, cfrom] of chain) {
      if (ext >= ROUTER.swingExtCm) break;
      const p = simpFrom(cid, cfrom); const rec2 = { lid: cid, from: cfrom, to: other(L[cid], cfrom), iFrom: PV.length - 1, iTo: null };
      for (let k = 1; k < p.length && ext < ROUTER.swingExtCm; k++) { const q = PV[PV.length - 1]; const ex = p[k][0] - q.x, ez = p[k][1] - q.z; ext += Math.sqrt(ex * ex + ez * ez); PV.push({ x: p[k][0], z: p[k][1], tag: { link: cid, cap: ROUTER.caps.push }, node: k === p.length - 1 ? rec2.to : null }); if (k === p.length - 1) rec2.iTo = PV.length - 1; }
      chainUsed.push(rec2);
    }
    const iReal = PV.length - 1;   // the last push-path vertex on a real link
    if (ext < ROUTER.swingExtCm) {   // straight on (virtual: the graph ends; or the graph fallback opposite the first taxi link)
      let d;
      if (swing != null) { const a = PV[PV.length - 2], b = PV[PV.length - 1]; const ex = b.x - a.x, ez = b.z - a.z; const m = Math.sqrt(ex * ex + ez * ez) || 1; d = [ex / m, ez / m]; }
      else if (xOut != null) { const dX = dirOut(xOut, J); d = [-dX[0], -dX[1]]; }
      else { const a = PV[PV.length - 2], b = PV[PV.length - 1]; const ex = b.x - a.x, ez = b.z - a.z; const m = Math.sqrt(ex * ex + ez * ez) || 1; d = [ex / m, ez / m]; }
      const q = PV[PV.length - 1], r = ROUTER.swingExtCm - ext;
      PV.push({ x: Math.round(q.x + d[0] * r), z: Math.round(q.z + d[1] * r), tag: { link: null, cap: ROUTER.caps.push, virtual: true }, node: null });
    }
    for (let k = 0; k < PV.length - 1; k++) PV[k].tag = PV[k + 1].tag;
    // fix round 2 (M2): push paths merge two corners only into one of < 100 deg (pushMergeMaxCos; a merged corner over a
    // short run lane had turned up to 131 deg in one arc); otherwise the corners keep their own deflection and the room's radius
    const pushPath = buildPath(PV, { rNomCm: PATH.rPushCm, capOf, mergeMaxCos: ROUTER.pushMergeMaxCos });
    const sJ = pushPath.vS[iJ], sReal = pushPath.vS[iReal];
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
    const alignCm = typeof ROUTER.pushAlignCm === 'number' ? ROUTER.pushAlignCm : ROUTER.pushAlignCm[clsOf(spanCm)], alignTh = ROUTER.pushAlignTh;
    // V2: no arc of the push path may start within pushAlignCm past the push end (both gears aligned on a straight)
    const alignMax = pushEnd + ROUTER.pushAlignExtraCm;   // fix round 2: on a curving lane the push stops within 20 m of the turn need
    for (let guard = 0; guard < 8; guard++) {
      const arc = pushPath.pieces.find(p => p.kind === 'arc' && p.g.th > alignTh && p.s0Cm + p.lenCm > pushEnd && p.s0Cm < pushEnd + alignCm);
      if (!arc || arc.s0Cm + arc.lenCm > pushMax || arc.s0Cm + arc.lenCm > alignMax) break;
      pushEnd = arc.s0Cm + arc.lenCm;
    }
    { // a point on a line piece (deterministic, no trigonometry); inside a gentle arc (< pushAlignTh): on the arc (bisection,
      // path.js arcPointDet); inside a sharper arc: the arc's end
      let i = pushPath.pieces.findIndex(p => p.s0Cm <= pushEnd && pushEnd < p.s0Cm + p.lenCm); if (i < 0) i = pushPath.pieces.length - 1;
      const p = pushPath.pieces[i]; const g = p.g;
      if (p.kind === 'line') { const u = Math.min(1, (pushEnd - p.s0Cm) / p.lenCm) * p.g.len; pushEndPt = [p.g.x0 + p.g.hx * u, p.g.z0 + p.g.hz * u]; }
      else if (g.th <= alignTh) pushEndPt = arcPointDet(g, Math.min(1, (pushEnd - p.s0Cm) / p.lenCm));
      else { pushEnd = p.s0Cm + p.lenCm; pushEndPt = [g.x0 + g.hx * g.T + g.ox * g.T, g.z0 + g.hz * g.T + g.oz * g.T]; }
    }
    const onGraph = pushEnd <= sReal + 100;   // H1: the push ends on a real link (not on the virtual straight)
    const pushDir = (() => {   // the push path's tangent at the push end (inside a gentle arc: perpendicular to the radius there)
      let i = pushPath.pieces.findIndex(p => p.s0Cm <= pushEnd && pushEnd < p.s0Cm + p.lenCm); if (i < 0) i = pushPath.pieces.length - 1; const p = pushPath.pieces[i], g = p.g;
      if (p.kind === 'line') return [g.hx, g.hz];
      if (pushEnd >= p.s0Cm + p.lenCm) return [g.ox, g.oz];
      const rx = (pushEndPt[0] - g.cx) / g.R, rz = (pushEndPt[1] - g.cz) / g.R; const t = [-rz, rx]; return t[0] * (g.hx + g.ox) + t[1] * (g.hz + g.oz) >= 0 ? t : [rz, -rx]; })();
    // the swing remainder: from the push end back to K along the push path's piece starts; each segment carries the link
    // of the push-path piece it runs on (fix round 2, H1: the chain's real link ids; an arc: its far-side link)
    const pieceLink = (k) => { const p = pushPath.pieces[k]; return p.kind === 'arc' && p.tagOut && p.tagOut.link != null ? p.tagOut.link : p.linkId; };
    const kEnd = (() => { let i = pushPath.pieces.findIndex(p => p.s0Cm < pushEnd && pushEnd <= p.s0Cm + p.lenCm); return i < 0 ? pushPath.pieces.length - 1 : i; })();
    const TV = [{ x: pushEndPt[0], z: pushEndPt[1], tag: { link: pieceLink(kEnd) ?? swing ?? seq[nPush - 1][0], cap: ROUTER.caps.taxilane }, node: null, li: nPush - 1 }];
    for (let k = pushPath.pieces.length - 1; k >= 0; k--) {   // the push path's piece starts between K and the push end, backwards
      const p = pushPath.pieces[k]; if (p.s0Cm >= pushEnd - 1 || p.s0Cm <= sJ) continue;
      const lk = k > 0 ? pieceLink(k - 1) : null;
      TV.push({ x: p.g.x0, z: p.g.z0, tag: { link: lk ?? swing ?? seq[nPush - 1][0], cap: ROUTER.caps.taxilane }, node: null, li: nPush - 1 });
    }
    if (TV.length > 1) TV[TV.length - 1].tag = { link: swing ?? seq[nPush - 1][0], cap: ROUTER.caps.taxilane };   // the last stretch to K is on X
    const rest = vertsOf(seq, nPush); const kK = TV.length;
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
    if (lite) {
      const pT0 = turnProfile(trimPath(pushPath, pushEnd), ROUTER.pushTurn.windowCm);
      return { path, verts: TV, vS, push: { swing, node: J, onGraph, run: { run: seq.slice(1, nPush).map(([id]) => id) },
        turn: { ok: pT0.maxArcDeg <= ROUTER.pushTurn.maxDeg && pT0.maxWinDeg <= ROUTER.pushTurn.maxDeg } } };
    }
    const crossings = crossingsOf(TV, vS, kRw);
    const hb = holdsNear(TV, vS, E.rw, sRw - ROUTER.holdSearchCm, sRw - 1);
    const luHold = hb.length ? hb[hb.length - 1] : { s: lateralCrossS(TV, vS, E.rw, kRw, -1, ROUTER.holdLatCm) ?? Math.max(0, sRw - ROUTER.holdLatCm), node: null, src: 'inf-90m' };
    const holds = [];
    for (const c of crossings) holds.push({ sCm: c.sInCm, node: c.node, kind: 'rwyhold', runway: c.runway, ref: c.ref });
    holds.push({ sCm: luHold.s, node: luHold.node, kind: 'lineup', runway: E.rw, src: luHold.src });
    holds.sort((a, b) => a.sCm - b.sCm);
    const blocks = blocksOf(TV, vS, path, nPush, seq, { startBox: true });
    // the swing chain from the push end back to K (fix round 1, V4; fix round 2, H1: every chain link, real ids): push-path
    // stations sp in [sJ, pushEnd] map linearly onto the taxi stations [s(K), 0]; parts beyond the push end are "behind"
    const sK = vS[kK]; const tx = (sp) => (pushEnd - sJ > 0 ? Math.round(sK * (pushEnd - sp) / (pushEnd - sJ)) : 0);
    const chainBlk = [];   // [{id, sp0, sp1, lid, from}] in push-path stations
    for (const c of chainUsed) {
      const spA = pushPath.vS[c.iFrom], spB = c.iTo != null ? pushPath.vS[c.iTo] : spA + lenCm[c.lid]; const nb = nBlocks(c.lid); const fwd = L[c.lid].a === c.from;
      for (let b = 0; b < nb; b++) {
        const sp0 = Math.round(spA + (spB - spA) * b / nb), sp1 = Math.round(spA + (spB - spA) * (b + 1) / nb); const kA = fwd ? b : nb - 1 - b;
        chainBlk.push({ id: 'b:' + c.lid + ':' + kA, sp0, sp1, lid: c.lid, from: c.from });
        const hi = tx(sp0), lo = tx(sp1);
        if (hi > 0) blocks.push({ id: 'b:' + c.lid + ':' + kA, kind: 'link', link: c.lid, dir: fwd ? -1 : 1, s0Cm: Math.max(0, lo), s1Cm: Math.min(path.lenCm, hi), noStop: false, twoWay: L[c.lid].dir === 'both', swing: true });
      }
    }
    for (let i = 1; i < chainUsed.length; i++) {   // junction boxes at the chain's own nodes (X's far node, ...)
      const v = chainUsed[i].from; if (!isJunction(v)) continue; const sp = pushPath.vS[chainUsed[i].iFrom]; const arc = arcRangeAt(pushPath, sp);
      const lo = tx(arc ? arc.s0Cm + arc.lenCm : sp) - ROUTER.boxPadCm, hi = tx(arc ? arc.s0Cm : sp) + ROUTER.boxPadCm;
      if (hi > 0) blocks.push({ id: 'j:' + v, kind: 'box', node: v, s0Cm: Math.max(0, lo), s1Cm: Math.min(path.lenCm, hi), noStop: (adj.get(v) || []).some(id => L[id].kind === 'taxiway'), start: lo <= 0 ? true : undefined, swing: true });
    }
    for (const c of crossings) blocks.push({ id: 'rwy:' + c.runway, kind: 'rwy', s0Cm: c.sInCm, s1Cm: c.sOutCm, noStop: true, crossing: true, node: c.node });
    blocks.push({ id: 'rwy:' + E.rw, kind: 'rwy', s0Cm: luHold.s, s1Cm: path.lenCm, noStop: false, lineup: true });
    // footprints (fix round 2, H1): the push sweeps the push path from the stand to the push end with the fuselage behind the
    // nose gear (the push path up to push end + tail, tail by span class) and holds the straight start-up pose (nose gear ->
    // tail along the push direction) for the 90 s start-up; every link (block), junction box and one-at-a-time lane within
    // ROUTER.foot of those points is the push's; those under the start-up pose are also the taxi's at s = 0 ("behind")
    const tailCm = FO.tailCm[clsOf(spanCm)];
    const fpts = samplePieces(pushPath.pieces, 0, pushEnd + tailCm); for (const q of fpts) q.push(q[2] >= pushEnd);
    for (let d = 0; d <= tailCm; d += FO.stepCm) fpts.push([pushEndPt[0] + pushDir[0] * d, pushEndPt[1] + pushDir[1] * d, pushEnd + d, true]);
    const FF = footOf(fpts); const FP = FF.all, FS = FF.start;
    const twyAt = (v) => (adj.get(v) || []).some(id => L[id].kind === 'taxiway');
    const startHas = (id) => blocks.some(b => b.id === id && b.s0Cm === 0);
    // a behind entry is held from s = 0 to the end of the taxi's first stretch whose nose gear is still within the footprint
    // tolerance of it (0 when the taxi moves straight away from it; verification round 3 of B's fixes, behind-box windows)
    const tx0 = samplePieces(path.pieces, 0, Math.min(path.lenCm, tailCm + FO.boxCm));
    const runEnd = (near) => { let s1 = 0; for (const [x, z, s] of tx0) { if (!near(x, z)) break; s1 = s; } return Math.round(s1); };
    const nearBlk = (id) => { const [, ls, ks] = id.split(':'); const lid = +ls, k = +ks; return (x, z) => { let hit = false; nearSegs(x, z, FO.tolCm, (l2, i, u) => { if (!hit && l2 === lid && blockAt(l2, i, u) === k) hit = true; }); return hit; }; };
    const nearBox = (v) => { const n = nodeOf[v]; const b2 = FO.boxCm * FO.boxCm; return (x, z) => { const dx = n.x * 100 - x, dz = n.z * 100 - z; return dx * dx + dz * dz <= b2; }; };
    for (const id of FS.blocks) if (!startHas(id)) { const lid = +id.split(':')[1]; blocks.push({ id, kind: 'link', link: lid, dir: 0, s0Cm: 0, s1Cm: runEnd(nearBlk(id)), noStop: false, twoWay: L[lid].dir === 'both', behind: true }); }
    for (const id of FS.boxes) if (!startHas(id)) { const v = +id.slice(2); blocks.push({ id, kind: 'box', node: v, s0Cm: 0, s1Cm: runEnd(nearBox(v)), noStop: twyAt(v), start: true, behind: true }); }
    for (const ref of FS.lanes) { const lb = blocks.find(b => b.kind === 'lane' && b.id === 'lane:' + ref && b.s0Cm <= tailCm); if (lb) lb.s0Cm = 0; else blocks.push({ id: 'lane:' + ref, kind: 'lane', s0Cm: 0, s1Cm: 0, noStop: false, behind: true }); }
    // a lane the push sweep held continues into the taxi when the taxi reaches it within laneHoldCm (no release in between)
    for (const ref of FP.lanes) { const lb = blocks.find(b => b.kind === 'lane' && b.id === 'lane:' + ref && b.s0Cm > 0 && b.s0Cm <= ROUTER.laneHoldCm); if (lb) { lb.s0Cm = 0; lb.held = true; } }
    const nGeoBox = geoBoxes(blocks, path.pieces, path.lenCm);
    const gaps = fillGaps(blocks, path.pieces, path.lenCm);
    const clrTail = tailOpt != null ? tailOpt : tailCm; tailClear(blocks, path.lenCm, clrTail);   // fix round 3 (V3-1)
    blocks.sort((a, b) => a.s0Cm - b.s0Cm || a.s1Cm - b.s1Cm || (a.id < b.id ? -1 : 1));
    const tailVec = (() => { const a = PV[iJ], b = PV[Math.min(PV.length - 1, iJ + 1)]; const dx = b.x - a.x, dz = b.z - a.z; return [dx, dz]; })();
    // push + start-up resources (fix round 1, V4; fix round 2, H1): the push link and the run's blocks, the junction boxes
    // along the run and at K, the swing chain's blocks up to the push end + tail, and every block, junction box and
    // one-at-a-time lane geometrically under the push sweep and the start-up pose (FP)
    const pushBlocks = [];
    for (let i = 0; i < nPush; i++) { const lid = seq[i][0]; const nb = nBlocks(lid); for (let b = 0; b < nb; b++) pushBlocks.push('b:' + lid + ':' + b); }
    for (let i = 1; i < nPush; i++) { const v = seq[i][1]; if (isJunction(v)) pushBlocks.push('j:' + v); }
    pushBlocks.push('j:' + J);
    for (const c of chainBlk) if (c.sp0 < pushEnd + tailCm) pushBlocks.push(c.id);
    for (const id of FP.blocks) pushBlocks.push(id);
    for (const id of FP.boxes) pushBlocks.push(id);
    const laneRefs = new Set(FP.lanes); for (const id of seq.slice(1, nPush).map(([x]) => x).concat(chainUsed.map(c => c.lid))) if (L[id].ref && EXCL.has(L[id].ref)) laneRefs.add(L[id].ref);
    for (const ref of laneRefs) pushBlocks.push('lane:' + ref);
    const resources = [...new Set(pushBlocks)].sort();
    // the driven push path (stand -> push end) keeps the path-level turn rule (fix round 2, M2)
    const pT = turnProfile(trimPath(pushPath, pushEnd), ROUTER.pushTurn.windowCm);
    const pushTurn = { maxArcDeg: Math.round(pT.maxArcDeg * 10) / 10, maxWinDeg: Math.round(pT.maxWinDeg * 10) / 10, ok: pT.maxArcDeg <= ROUTER.pushTurn.maxDeg && pT.maxWinDeg <= ROUTER.pushTurn.maxDeg };
    const toraCm = toraOf(end, entry);
    return {
      kind: 'dep', stand, end, entry, exitId: null, cls: clsOf(spanCm), geom: wideGeom ? 'wide' : 'narrow',
      links: seq.map(([a, b]) => [a, b]), lenCm: path.lenCm, pieces: path.pieces, path, vS, verts: TV,
      blocks, holds, crossings, lineup: { node: vRw.node, sCm: lineupS, rwySCm: rwyS, entrySCm: Math.round(alongEnd(end, vRw.x, vRw.z)), holdSCm: luHold.s, toraCm,
        // declared TORA: from the runway end (full length) or from the intersection (AIP (mirror) AD 2.13 'intersection')
        toraLeftCm: toraCm == null ? null : entry === 'full' ? toraCm - rwyS : toraCm - (rwyS - Math.round(alongEnd(end, vRw.x, vRw.z))) },
      turn: turnSummary(path), gapFill: gaps, geoBoxes: nGeoBox, tailCm: clrTail,
      push: { lenCm: pushEnd, pieces: pushPath.pieces, path: pushPath, verts: PV, nLinks: nPush, node: J, swing, swingVirtual, tailHdg: hdgOfVec(tailVec),
        chain: chainUsed.map(c => [c.lid, c.from]), onGraph, turn: pushTurn, startFoot: { blocks: FS.blocks, boxes: FS.boxes, lanes: FS.lanes, tailCm },
        run: { run: seq.slice(1, nPush).map(([id]) => id), node: J, swing, turnDeg: prec.turnDeg }, fallback: !!prec.fallback,
        optionA: optA ? { run: seq.slice(1, nPush).map(([id]) => id), node: J, swing, turnDeg: prec.turnDeg, record: { run: optA.run, node: optA.node, swing: optA.swing, turnDeg: optA.turnDeg } } : null, resources },
      zones: [], src: 'inf', variant: tableVariant || 'live',
    };
  }
  /**
   * Junction boxes by geometry (fix round 2, H1, after the verifier re-run): a junction node within ROUTER.foot.boxCm of the
   * path that is not one of the route's own vertices (a node of an adjacent or crossing link, or an OSM junction the route's
   * link passes without sharing it) gets a box over each pass within boxCm (`geo: true`), unless a box of that node already
   * covers the pass's nearest station or the pass lies inside a runway block. Returns the number of boxes added.
   */
  function geoBoxes(blocks, pieces, lenCm) {
    const b2 = FO.boxCm * FO.boxCm, rr = Math.ceil(FO.boxCm / FG), reach = FO.boxCm + FG; const runs = new Map(); const gen = ++skipGen; let ck = null, cand = null;
    const st = 2 * FO.stepCm;   // 2 m samples: a node within boxCm - 0.5 m is always seen; the windows are padded by one step
    for (const [x, z, s] of samplePieces(pieces, 0, lenCm, st)) {
      const cx = Math.floor(x / FG), cz = Math.floor(z / FG), k = gKey(cx, cz);
      if (k !== ck) {   // candidates of this cell: junction nodes within boxCm + one cell of the cell centre
        ck = k; cand = []; const mx = (cx + 0.5) * FG, mz = (cz + 0.5) * FG;
        for (let a = -rr; a <= rr; a++) for (let b = -rr; b <= rr; b++) { const arr = nodeGrid.get(gKey(cx + a, cz + b)); if (!arr) continue;
          for (const v of arr) { const n = nodeOf[v]; const dx = n.x * 100 - mx, dz = n.z * 100 - mz; if (dx * dx + dz * dz <= reach * reach) cand.push(v); } }
      }
      for (const v of cand) {
        if (skipG[v] === gen && s < skipS[v]) continue;   // the nose moves at most ds per ds of station: no need to look again before
        const n = nodeOf[v]; const dx = n.x * 100 - x, dz = n.z * 100 - z, d2 = dx * dx + dz * dz;
        if (d2 > b2) { skipG[v] = gen; skipS[v] = s + Math.sqrt(d2) - FO.boxCm; continue; }
        let R = runs.get(v); if (!R) runs.set(v, R = []); const r = R[R.length - 1];
        if (r && s - r.s1 <= ROUTER.laneGapCm + st) { r.s1 = s; if (d2 < r.d2) { r.d2 = d2; r.sm = s; } } else R.push({ s0: s, s1: s, d2, sm: s }); }
    }
    const rw = blocks.filter(b => b.kind === 'rwy'); const add = [];
    for (const v of [...runs.keys()].sort((a, b) => a - b)) for (const r of runs.get(v)) {
      if (blocks.some(b => b.kind === 'box' && b.node === v && b.s0Cm - 100 <= r.sm - st / 2 && r.sm + st / 2 <= b.s1Cm + 100)) continue;   // (the true nearest is within st / 2 of r.sm)
      if (rw.some(b => b.s0Cm <= r.sm && r.sm <= b.s1Cm)) continue;
      add.push({ id: 'j:' + v, kind: 'box', node: v, s0Cm: Math.max(0, Math.round(r.s0 - st)), s1Cm: Math.min(lenCm, Math.round(r.s1 + st)), noStop: twyNode(v), geo: true });
    }
    for (const b of add) blocks.push(b);
    return add.length;
  }
  /**
   * Tail clear (fix round 3, V3-1): every runway no-stop block (crossing, landing) and end box gets a no-stop marker over
   * [its start, its far end + tailCm] (kind 'clear', `res: false`: it reserves nothing, it only extends the no-stop sequence;
   * it spans the runway block too, so no boundary between the hold and the tail-clear station - the far holding position
   * itself included - lies outside the open interior of a no-stop block): the first plannable stop, a block boundary outside
   * every no-stop block, leaves the whole aircraft behind the far runway-holding position. The block itself gets
   * `tailClearCm` (the nose station from which a stop may be planned) and `tailCm`. Called after the gap fill (a marker
   * covers no metre of the route). Returns the markers added.
   */
  function tailClear(blocks, lenCm, tailCm) {
    const add = [];
    for (const b of blocks) {
      const k = b.kind === 'endbox' ? 'endbox' : b.kind === 'rwy' && b.crossing ? 'crossing' : b.kind === 'rwy' && b.landing ? 'landing' : null;
      if (!k || !b.noStop || !ROUTER.tailClear.kinds.includes(k)) continue;
      const s1 = Math.min(lenCm, b.s1Cm + tailCm); b.tailClearCm = s1; b.tailCm = tailCm;
      const tag = k === 'endbox' ? 'endbox:' + b.end : b.id.slice(4) + ':' + (k === 'crossing' ? b.node : 'vacate');
      if (s1 > b.s1Cm) add.push({ id: 'clr:' + tag, kind: 'clear', of: b.id, s0Cm: b.s0Cm, s1Cm: s1, noStop: true, tailClear: true, res: false, tailCm });
    }
    for (const c of add) blocks.push(c);
    return add;
  }
  /**
   * Every metre of a route inside some block (fix round 2, H1): the uncovered stretches get the block of the link nearest
   * the path there (geometric, `geo: true`). Returns the number of stretches filled.
   */
  function fillGaps(blocks, pieces, lenCm) {
    const iv = blocks.filter(b => b.s1Cm > b.s0Cm && b.res !== false).map(b => [b.s0Cm, b.s1Cm]).sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    const gaps = []; let cur = 0;
    for (const [a, b] of iv) { if (a > cur + 1) gaps.push([cur, a]); if (b > cur) cur = b; }
    if (lenCm > cur + 1) gaps.push([cur, lenCm]);
    let n = 0;
    for (const [a, b] of gaps) {
      const runs = [];
      for (const [x, z, s] of samplePieces(pieces, a, b)) {
        let best = null, bd = Infinity;
        nearSegs(x, z, 4000, (lid, i, u, d2) => { if (d2 < bd || (d2 === bd && lid < best.lid)) { bd = d2; best = { lid, k: blockAt(lid, i, u) }; } });
        if (!best) continue; const id = 'b:' + best.lid + ':' + best.k; const r = runs[runs.length - 1];
        if (r && r.id === id) r.s1 = s; else runs.push({ id, lid: best.lid, s0: s, s1: s });
      }
      for (let j = 0; j < runs.length; j++) { const r = runs[j]; const s0 = j === 0 ? a : Math.round(r.s0), s1 = j === runs.length - 1 ? b : Math.round(runs[j + 1].s0);
        blocks.push({ id: r.id, kind: 'link', link: r.lid, dir: 0, s0Cm: s0, s1Cm: s1, noStop: false, twoWay: L[r.lid].dir === 'both', geo: true }); n++; }
    }
    return n;
  }
  function toraOf(end, entry) {
    // declared distances come from the airport data (aip_facts); the router knows them only through the table (baked)
    // fix round 2 (C2): also in live mode, from the table passed in or opts.runwayEnds (traj.js runwayGeom(airport))
    const RE = (o.table && o.table.runwayEnds) || o.runwayEnds || null; const r = RE && RE[end]; if (!r) return null;
    if (entry === 'full') return r.toraCm; const it = r.intersections && r.intersections[entry]; return it ? it.toraCm : null;
  }
  function assembleArr(exitId, stand, seq, spanCm, wideGeom, lite = false, tailOpt = null) {
    const ex = exitById.get(exitId); const E = ENDS[ex.end];
    const v = nodeOf[ex.node]; const vx = Math.round(v.x * 100), vz = Math.round(v.z * 100);
    const V = [{ x: Math.round(vx - E.h[0] * ROUTER.rollLeadCm), z: Math.round(vz - E.h[1] * ROUTER.rollLeadCm), tag: { link: null, cap: ROUTER.caps.rapid, runway: E.rw }, node: null, li: -1 }];
    for (const q of vertsOf(seq, 0)) V.push(q);
    V[1].node = ex.node;
    const rapidTag = (t) => !!t && (t.runway || (t.link != null && L[t.link] && L[t.link].for_landing));
    const path = buildPath(V, { rNomCm: wideGeom ? PATH.rNomCm.wide : PATH.rNomCm.narrow, capOf: capFor(wideGeom), aLatOf: (a, b) => (rapidTag(a) || rapidTag(b) ? PATH.aLatRapidCms2 : PATH.aLatCms2) });
    const vS = path.vS; const sExit = vS[1];
    if (lite) return { path, verts: V, vS, push: null };
    // vacate point: the first runway-holding position of the landing runway after the exit node
    const ha = holdsNear(V, vS, E.rw, sExit + 1, sExit + ROUTER.holdSearchCm * 2);
    const vac = ha.length ? ha[0] : { s: lateralCrossS(V, vS, E.rw, 1, 1, ROUTER.holdLatCm) ?? sExit + ROUTER.holdLatCm, node: null, src: 'inf-90m' };
    let crossings = crossingsOf(V, vS, null);
    // fix round 2 (L1): a route that re-crosses the runway it landed on (an exit on the side opposite the stand: only the
    // exit model's last resort, e.g. 18R/36L with F4552) and does not reach a holding position of that runway in between
    // never leaves its strip: the landing occupancy runs to the far side of the re-crossing, no hold on the strip
    let reCross = null;
    for (const c of crossings) {
      if (c.runway !== E.rw) continue;
      if (c.inHow !== 'fallback' && c.sInCm >= vac.s) continue;   // vacated, held at a holding position, then crosses: a normal crossing
      reCross = { node: c.node, ref: c.ref, sCm: c.sCm, vacateFrom: vac.s }; vac.s = Math.max(vac.s, c.sOutCm); vac.node = null; vac.src = c.outHow === 'hold' ? c.holdSrc : 'inf-90m-recross';
    }
    if (reCross) crossings = crossings.filter(c => !(c.runway === E.rw && c.sOutCm <= vac.s));
    // the lead-in: its first vertex (the junction)
    let kLead = V.length - 1; for (let k = V.length - 2; k >= 0; k--) { const l = L[V[k].tag.link]; if (l && l.use === 'stand') kLead = k; else break; }
    const arcL = arcRangeAt(path, vS[kLead]);
    const blocks = blocksOf(V, vS, path, 0, seq, {});
    let leadS = arcL ? arcL.s0Cm : vS[kLead];
    const box = blocks.find(b => b.kind === 'box' && b.node === V[kLead].node);
    if (box && box.noStop) leadS = box.s0Cm;
    const eb = endBoxes(V, vS);
    for (const b of eb) blocks.push(b);
    for (const c of crossings) blocks.push({ id: 'rwy:' + c.runway, kind: 'rwy', s0Cm: c.sInCm, s1Cm: c.sOutCm, noStop: true, crossing: true, node: c.node });
    blocks.push({ id: 'rwy:' + E.rw, kind: 'rwy', s0Cm: 0, s1Cm: vac.s, noStop: true, landing: true });
    const nGeoBox = geoBoxes(blocks, path.pieces, path.lenCm);
    const gaps = fillGaps(blocks, path.pieces, path.lenCm);
    const clrTail = tailOpt != null ? tailOpt : FO.tailCm[clsOf(spanCm)]; tailClear(blocks, path.lenCm, clrTail);   // fix round 3 (V3-1)
    blocks.sort((a, b) => a.s0Cm - b.s0Cm || a.s1Cm - b.s1Cm || (a.id < b.id ? -1 : 1));
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
      exit: { id: exitId, ref: ex.ref, node: ex.node, side: ex.side, sCm: sExit, rwySCm: ex.sCm, startRwySCm: ex.sCm - ROUTER.rollLeadCm,
        oppositeSide: ex.side !== standSide(stand, E.rw), reCross },
      vacate: { sCm: vac.s, node: vac.node, src: vac.src, tailClearCm: Math.min(path.lenCm, vac.s + clrTail) }, endAround: ea, turn: turnSummary(path), gapFill: gaps, geoBoxes: nGeoBox, tailCm: clrTail, src: 'inf', variant: tableVariant || 'live',
    };
  }
  const hdgOfVec = (d) => { const a = Math.round(hdgVecDet(d[0], d[1]) * 10) / 10; return a; };
  // route.turn: the driven path's largest arc and 40 m heading change (deg, 0.1), and whether they meet the rule (V3)
  const turnSummary = (path) => { const t = turnProfile(path, ROUTER.pathTurn.windowCm); const PT = ROUTER.pathTurn;
    return { maxArcDeg: Math.round(t.maxArcDeg * 10) / 10, maxWinDeg: Math.round(t.maxWinDeg * 10) / 10, ok: t.maxArcDeg <= PT.maxDeg && t.maxWinDeg <= PT.maxDeg, winS0Cm: t.maxWinDeg > PT.maxDeg ? t.winS0Cm : null }; };

  // ------------------------------------------------------------------------------------------- public API
  const routeCache = new Map();
  // o.slim (C1, fix round 1 V17): drop the assembly inputs (vertex chains and their stations) from served routes;
  // route.lineup gets a non-enumerable back-reference for takeoffTraj's display (no JSON cycle)
  function finish(r) {
    if (r.lineup) Object.defineProperty(r.lineup, 'route', { value: r, enumerable: false, configurable: true });
    if (o.slim) {   // the path objects are shared copies made by trimPath / buildPath: drop their vertex stations too
      delete r.verts; delete r.vS; r.path = { lenCm: r.path.lenCm, pieces: r.path.pieces };
      if (r.push) { delete r.push.verts; r.push.path = { lenCm: r.push.path.lenCm, pieces: r.push.path.pieces }; }
      for (const p of r.pieces) { p.tag = null; if (p.tagOut) p.tagOut = { link: p.tagOut.link }; }
    }
    return r;
  }
  function departure(stand, end, opts = {}) {
    const asked = opts.entry || 'full'; const span = opts.spanCm ?? 0; const wg = opts.geom ? opts.geom === 'wide' : span >= ROUTER.spanNarrowCm;
    // fix round 2 (C4): span >= 36 m (code D-F) lines up at full length; an intersection request is served as full length
    const entry = asked !== 'full' && ROUTER.wideFullLength && span >= ROUTER.spanNarrowCm ? 'full' : asked;
    const tailOpt = opts.tailCm != null && opts.tailCm >= 0 ? Math.round(opts.tailCm) : null;   // fix round 3 (V3-1): a type's own nose-gear -> tail
    const ck = 'D|' + stand + '|' + end + '|' + entry + '|' + clsOf(span) + '|' + wg + '|' + asked + '|' + tailOpt; if (routeCache.has(ck)) return routeCache.get(ck);
    const prec = depSeq(stand, end, entry); let r = prec ? finish(assembleDep(stand, end, entry, prec, span, wg, false, tailOpt)) : null;
    if (r && entry !== asked) { r.entryAsked = asked; r.entryNote = 'span >= 36 m: full-length line-up (design §4.2; AIP (mirror) AD 2.20 2.1.7 intersection entry for code C) [inf]'; }
    routeCache.set(ck, r); return r;
  }
  function arrival(exitId, stand, opts = {}) {
    const span = opts.spanCm ?? 0; const cls = clsOf(span); const wg = opts.geom ? opts.geom === 'wide' : span >= ROUTER.spanNarrowCm;
    const tailOpt = opts.tailCm != null && opts.tailCm >= 0 ? Math.round(opts.tailCm) : null;   // fix round 3 (V3-1)
    const ck = 'R|' + exitId + '|' + stand + '|' + cls + '|' + wg + '|' + tailOpt; if (routeCache.has(ck)) return routeCache.get(ck);
    const seq = arrSeq(exitId, stand, cls); const r = seq ? finish(assembleArr(exitId, stand, seq, span, wg, false, tailOpt)) : null;
    routeCache.set(ck, r); return r;
  }
  return {
    departure, arrival, exits, optionA: (s) => { const r = optionA(s); return r && r.run ? r : null; }, standSide, westOfWest, clsOf,
    // for tools/sim/build_routes.mjs and the tests
    _search: { depSeq, arrSeq, arrSeqs, findOptionA, search, depKeys, depGoalFn, exitById, exitList },
    graph: { L, N, nodeOf, adj, turns, lenCm, ptsCm, degree, RW, ENDS, alongEnd, latEast, standNode, pushOf, ownLeadin, standNames, other, canGo, dirOut, holdInf },
    info: () => ({ fingerprint: fp, table: tableNote, variant: tableVariant || 'live', closed: closed ? closed.size : 0, cached: routeCache.size, turnRule: { ...turnStats } }),
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
      for (const v of [...nodes].sort((a, b) => a - b)) { const n = nodeOf.get(v); for (const q of xs) { const ex = n.x - q[0], ez = n.z - q[1]; const d = ex * ex + ez * ez; if (d < bd) { bd = d; best = v; } } }
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
