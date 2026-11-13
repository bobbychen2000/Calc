// Forked from sfo3d/js/live/traffic.js @ a967f9b (3,247 lines). Kept (re-written compactly, same design): the report
// buffer per track with position time = relay _pt + clock offset; ingest hygiene (duplicate / out-of-order reports, the
// position-jump test with "three consistent jumps = real", the altitude-step plausibility test, sticky vehicles, '~'
// anonymous ground targets as vehicles); the Hermite sample between real reports with the reported velocities and the
// chord fallback; dead reckoning <= DR_MAX_S with constant turn, then a smooth stop on the ground; the kinematic body that
// FOLLOWS the target with bounded acceleration and turn rate, moving along its nose on the ground (no sideways sliding);
// fades instead of jumps (CUT_S re-placement); stale / parked persistence (localStorage, now 'hwdlive.parked.v1'); TaxiNet
// (map matching of taxiing reports + paved test) with the adaptive display delay.
// Changed for HWD / GA (fork map 2.7, risks R1-R5):
//  - headings in DEGREES TRUE at the package boundary (disp.hdg, park.pose.hdg); radians only inside (tr.ctl.psi);
//  - heights from the Phase 1 calibration (classifier.js prep: h = alt_geom - GEOM_OFF - NASR runway surface, GEOM_OFF
//    -108.09 ft) and ground from site.groundY (NAVD 88 field surface, 8.44-15.88 m), never a constant GROUND_Y;
//  - ground = the ground flag OR 'ground by kinematics' (h <= 30 ft, gs < 35 kt: GA units without weight-on-wheels report
//    airborne while rolling; hwd_events.json rules_text) OR runway contact (R state); helicopters keep the flag (hover);
//  - THE 46-S HOLES (docs/PLAN.md section 3, fork map R3): in replay the display runs lookahead_s (60 s) behind, so a hole
//    lies between two real fixes. On the ground a hole longer than HOLE_S is bridged ALONG THE TAXI GRAPH
//    (data/hwd_taxigraph.json links, TaxiNet.routeXY), never straight across grass or buildings; in the air by Hermite;
//  - phases from js/live/classifier.js (GA rules of hwd_events.json, back-dated revisions), parking from js/live/parking.js
//    (tie-downs, ramp, hangar aprons, helipads, hangared), solid planforms from js/aircraft/ga_dims.js;
//  - D6 scope (tr.scope) and display window (tr.inView: <= 5 NM, <= 3,000 ft AGL); identity with D1 (lookup.js).
// Dropped (SFO only): stands, jet bridges and docking, silent docking, push-back / tow logic, the flysfo plan, routes,
// liveries, the 4-runway airliner phase machine (airLogic / groundLogic, LIFTOFF_KT, the 40-kt rule), inAirport, GEOID_M.
//
// Node-pure (fork map 2.0): imports geo.js, the P3 modules and nothing that touches the DOM or WebGL at module scope.
import { wgs84ToWorld, FT, RWY_ENDS, thrDispM } from '../geo.js';
import { PhaseClassifier, PHASES, RULES as CR, towerStatus } from './classifier.js';
import { identity, isVehicle } from './lookup.js';
import { gaDims } from '../aircraft/ga_dims.js';
import { pavedWith } from './ground.js';

export const DELAY_MS = 3000;                 // initial live display delay
export const DELAY_MIN = 1500, DELAY_MAX = 65000;   // live: adapted to the report ages, up to the relay's poll period (fork map 2.7)
const KT = 1852 / 3600, NM = 1852, D2R = Math.PI / 180, GRAV = 9.81;
const DR_MAX_S = 5;                           // dead reckoning past the newest fix (constant turn), sfo3d
const DR_STOP_TAU_S = 3;                      // then the ground body stops smoothly (sfo3d DRG: tau 3 s)
const CUT_S = 0.4;                            // fade out / in of a re-placement (sfo3d)
const HOLE_S = CR.HOLE_S;                     // s: a gap longer than this between fixes is a polling hole (derive.py)
const ROUTE_MIN_M = 12;                       // m: a ground hole shorter than this is interpolated directly [inf]
const ROUTE_RATIO = 1.8, ROUTE_EXTRA_M = 80;  // a taxi-graph route is used when <= 1.8 x the chord + 80 m [inf]
const TAXI_MAX_KT = 30;                       // the route's mean speed must not exceed this (GA taxi <= ~20 kt) [inf]
const STALE_AIR_MS = 60000, MOVING_LOST_MS = 45000, VEH_KEEP_MS = 120000, PARK_KEEP_MS = 8 * 3600e3;   // sfo3d values
const REACQ_PARK_M = 15;                      // a parked aircraft heard again within this of its pose has not moved (sfo3d)
const VIEW_NM = 5, VIEW_FT = 3000, VIEW_HYST = 1.1;     // D6 display window, with 10 % hysteresis [inf]
const PAVED_NEAR_M = 8;                       // m: GNSS error of a ground fix (NACp 9-10 EPU < 10-30 m [verify]) [inf]
const SIM_NM = 7;                             // bodies are simulated within this (a track entering the view is already moving)
export const STORE_KEY = 'hwdlive.parked.v1';
// kinematic limits [inf: typical GA handling, not measured; tools/traffic reports what the drawn motion does]
const LIM = {
  taxiAcc: 1.2, taxiDec: 2.0, latGround: 2.0, wGround: 25, wPivot: 20,      // m/s2, m/s2, m/s2 lateral, deg/s, deg/s at rest
  rollAcc: { single_hw: 2.5, single_lw: 2.5, twin: 3.0, turboprop: 3.5, jet: 4.5, heli: 2.0, glider: 2.0, ultralight: 2.0, unknown: 2.5 },
  rollDec: 3.5, airAcc: 4.5, airVAcc: 2.5, airVs: { jet: 25, turboprop: 15, default: 12 }, bankMax: 35,   // vs m/s: 4,900 / 2,950 / 2,360 ft/min
};
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const wrapPi = (a) => { a = (a + Math.PI) % (2 * Math.PI); if (a < 0) a += 2 * Math.PI; return a - Math.PI; };
const hvR = (h) => [Math.sin(h), -Math.cos(h)];            // radians -> world (x, z)
const bearR = (x, z) => Math.atan2(x, -z);                 // world (x, z) -> radians
const toDeg = (r) => ((r / D2R) % 360 + 360) % 360;
const median = (a) => { if (!a.length) return null; const s = a.slice().sort((p, q) => p - q); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
const circMedianDeg = (hs) => { if (!hs.length) return null; let sx = 0, sz = 0; for (const h of hs) { sx += Math.sin(h * D2R); sz += Math.cos(h * D2R); } const m = Math.atan2(sx, sz) / D2R; return ((m + median(hs.map(h => ((h - m + 540) % 360) - 180))) % 360 + 360) % 360; };
function inRing(r, x, z) { let c = false; for (let i = 0, j = r.length - 1; i < r.length; j = i++) { const a = r[i], b = r[j]; if ((a[1] > z) !== (b[1] > z) && x < (b[0] - a[0]) * (z - a[1]) / (b[1] - a[1]) + a[0]) c = !c; } return c; }

// ---------------------------------------------------------------- taxi network: map matching, paved test, routing
export class TaxiNet {
  constructor(G) {
    this.ok = !!(G && G.edges && G.edges.length); if (!this.ok) return;
    this.hw = G.halfWidth || 5.33; this.ways = G.ways || []; this.C = 40; this.grid = new Map();
    this.E = G.edges.map(e => { const dx = e[2] - e[0], dz = e[3] - e[1], L = Math.hypot(dx, dz) || 1e-6; return { x0: e[0], z0: e[1], x1: e[2], z1: e[3], ux: dx / L, uz: dz / L, L, w: e[4], rw: (this.ways[e[4]] || {}).kind === 'runway' }; });
    this.E.forEach((e, i) => { const n = Math.ceil(e.L / 10); for (let k = 0; k <= n; k++) { const x = e.x0 + (e.x1 - e.x0) * k / n, z = e.z0 + (e.z1 - e.z0) * k / n; const key = Math.floor(x / this.C) + ',' + Math.floor(z / this.C); let s = this.grid.get(key); if (!s) this.grid.set(key, s = new Set()); s.add(i); } });
    this.aprons = (G.aprons || []).map(r => { let x0 = 1e9, z0 = 1e9, x1 = -1e9, z1 = -1e9; for (const p of r) { x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0]); z0 = Math.min(z0, p[1]); z1 = Math.max(z1, p[1]); } return { r, bb: [x0, z0, x1, z1] }; });
    // routing graph (hwd-taxigraph/1 nodes + links); air links (helicopter-only connectors) are kept apart
    this.nodes = G.nodes || []; this.links = (G.links || []).map((l, i) => {
      const pts = l.pts && l.pts.length >= 2 ? l.pts : [[this.nodes[l.a].x, this.nodes[l.a].z], [this.nodes[l.b].x, this.nodes[l.b].z]];
      const cum = [0]; for (let k = 1; k < pts.length; k++) cum.push(cum[k - 1] + Math.hypot(pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1]));
      const way = this.ways[l.way] || {};
      return { i, a: l.a, b: l.b, pts, cum, len: cum[cum.length - 1], air: !!l.air, runway: l.runway || null, maxSpan: way.max_span_m ?? null, way: l.way };
    });
    this.adj = this.nodes.map(() => []); for (const L of this.links) { this.adj[L.a].push(L); this.adj[L.b].push(L); }
    this.LC = 30; this.lgrid = new Map();
    for (const L of this.links) for (let k = 1; k < L.pts.length; k++) { const a = L.pts[k - 1], b = L.pts[k]; const n = Math.max(1, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / 10));
      for (let q = 0; q <= n; q++) { const x = a[0] + (b[0] - a[0]) * q / n, z = a[1] + (b[1] - a[1]) * q / n; const key = Math.floor(x / this.LC) + ',' + Math.floor(z / this.LC); let s = this.lgrid.get(key); if (!s) this.lgrid.set(key, s = []); if (!s.length || s[s.length - 1][0] !== L.i || s[s.length - 1][1] !== k) s.push([L.i, k]); } }
    this.routes = 0; this.routeFails = 0;
  }
  cand(x, z) { const out = new Set(); const i = Math.floor(x / this.C), j = Math.floor(z / this.C); for (let a = -1; a <= 1; a++) for (let b = -1; b <= 1; b++) { const s = this.grid.get((i + a) + ',' + (j + b)); if (s) for (const k of s) out.add(k); } return out; }
  proj(e, x, z) { const u = clamp((x - e.x0) * e.ux + (z - e.z0) * e.uz, 0, e.L); const px = e.x0 + e.ux * u, pz = e.z0 + e.uz * u; return { px, pz, d: Math.hypot(x - px, z - pz), u }; }
  // best centreline segment for a moving aircraft (h: radians or null): lateral distance + heading agreement (either way) +
  // continuity with the previously matched way (sfo3d one-step Viterbi)
  match(x, z, h, prevWay, maxD = 10, maxDh = 35 * D2R) {
    if (!this.ok) return null; let best = null, bs = 1e9;
    for (const k of this.cand(x, z)) {
      const e = this.E[k]; const p = this.proj(e, x, z); if (p.d > maxD) continue;
      let dh = 0; if (h != null) { const eh = bearR(e.ux, e.uz); dh = Math.min(Math.abs(wrapPi(h - eh)), Math.abs(wrapPi(h - eh - Math.PI))); if (dh > maxDh) continue; }
      const s = (p.d / 4) ** 2 + (dh / (12 * D2R)) ** 2 + (prevWay != null && e.w !== prevWay ? 0.6 : 0);
      if (s < bs) { bs = s; best = { ...p, e, k, way: e.w, ux: e.ux, uz: e.uz }; }
    }
    return best;
  }
  inApron(x, z) { for (const a of this.aprons) { if (x < a.bb[0] || x > a.bb[2] || z < a.bb[1] || z > a.bb[3]) continue; if (inRing(a.r, x, z)) return true; } return false; }
  paved(x, z) { if (!this.ok) return false; for (const k of this.cand(x, z)) { const e = this.E[k]; const p = this.proj(e, x, z); if (p.d < (e.rw ? 23 : this.hw)) return true; } return this.inApron(x, z); }
  // projection of (x, z) on the routing links: [{L, s (arc position), d, ux, uz}] best first
  projLinks(x, z, h = null, opt = {}) {
    const out = []; const seen = new Map(); const i0 = Math.floor(x / this.LC), j0 = Math.floor(z / this.LC);
    for (let a = -1; a <= 1; a++) for (let b = -1; b <= 1; b++) { const s = this.lgrid.get((i0 + a) + ',' + (j0 + b)); if (!s) continue;
      for (const [li, k] of s) {
        const L = this.links[li]; if (L.air && !opt.air) continue; if (opt.span && L.maxSpan != null && opt.span > L.maxSpan) continue;
        const p = L.pts[k - 1], q = L.pts[k], dx = q[0] - p[0], dz = q[1] - p[1], l2 = dx * dx + dz * dz || 1e-9;
        const u = clamp(((x - p[0]) * dx + (z - p[1]) * dz) / l2, 0, 1); const px = p[0] + dx * u, pz = p[1] + dz * u, d = Math.hypot(x - px, z - pz);
        const sc = d + (h != null ? 6 * Math.min(Math.abs(wrapPi(h - bearR(dx, dz))), Math.abs(wrapPi(h - bearR(dx, dz) - Math.PI))) : 0);
        const prev = seen.get(li); if (prev && prev.sc <= sc) continue;
        const l = Math.sqrt(l2); seen.set(li, { L, s: L.cum[k - 1] + u * l, d, sc, ux: dx / l, uz: dz / l, px, pz });
      } }
    for (const v of seen.values()) out.push(v);
    return out.sort((p, q) => p.sc - q.sc).slice(0, 4);
  }
  // shortest path between two nodes (Dijkstra; 742 nodes): -> { nodes, len, pts } | null   (fork map 2.7 net.route)
  route(from, to, opt = {}) { const r = this.dijkstra([[from, 0, null]], new Map([[to, 0]]), opt); return r ? { nodes: r.nodes, len: r.len, pts: r.pts } : null; }
  dijkstra(starts, goals, opt) {
    const N = this.nodes.length, dist = new Float64Array(N).fill(Infinity), prev = new Int32Array(N).fill(-1), via = new Array(N).fill(null);
    const heap = []; const push = (d, n) => { heap.push([d, n]); let i = heap.length - 1; while (i > 0) { const p = (i - 1) >> 1; if (heap[p][0] <= heap[i][0]) break; [heap[p], heap[i]] = [heap[i], heap[p]]; i = p; } };
    const pop = () => { const t = heap[0], e = heap.pop(); if (heap.length) { heap[0] = e; let i = 0; for (;;) { const l = 2 * i + 1, r = l + 1; let m = i; if (l < heap.length && heap[l][0] < heap[m][0]) m = l; if (r < heap.length && heap[r][0] < heap[m][0]) m = r; if (m === i) break; [heap[m], heap[i]] = [heap[i], heap[m]]; i = m; } } return t; };
    for (const [n, d] of starts) if (d < dist[n]) { dist[n] = d; push(d, n); }
    let best = null;
    while (heap.length) {
      const [d, n] = pop(); if (d > dist[n]) continue; if (best && d >= best.len) break;
      if (goals.has(n)) { const tot = d + goals.get(n); if (!best || tot < best.len) best = { node: n, len: tot }; }
      for (const L of this.adj[n]) {
        if (L.air && !opt.air) continue; if (opt.span && L.maxSpan != null && opt.span > L.maxSpan) continue;
        const m = L.a === n ? L.b : L.a, nd = d + L.len + (L.runway && !opt.runway ? 40 : 0);   // runways only when needed [inf]
        if (nd < dist[m]) { dist[m] = nd; prev[m] = n; via[m] = L; push(nd, m); }
      }
    }
    if (!best) return null;
    const nodes = []; const ls = []; for (let n = best.node; n >= 0; n = prev[n]) { nodes.push(n); if (via[n]) ls.push(via[n]); }
    nodes.reverse(); ls.reverse();
    const pts = [[this.nodes[nodes[0]].x, this.nodes[nodes[0]].z]];
    for (let k = 0; k < ls.length; k++) { const L = ls[k]; const fwd = L.a === nodes[k]; const P = fwd ? L.pts : L.pts.slice().reverse(); for (let q = 1; q < P.length; q++) pts.push(P[q]); }
    return { nodes, len: best.len, pts, end: best.node };
  }
  // sub-polyline of link L from arc s0 to s1 (either direction)
  sub(L, s0, s1) {
    const at = (s) => { let k = 1; while (k < L.cum.length - 1 && L.cum[k] < s) k++; const a = L.pts[k - 1], b = L.pts[k], l = L.cum[k] - L.cum[k - 1] || 1e-9, u = clamp((s - L.cum[k - 1]) / l, 0, 1); return [[a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u], k]; };
    const [p0, k0] = at(s0), [p1, k1] = at(s1); const out = [p0];
    if (s1 >= s0) for (let k = k0; k < k1; k++) out.push(L.pts[k]); else for (let k = k0 - 1; k >= k1; k--) out.push(L.pts[k]);
    out.push(p1); return out;
  }
  // a taxi route between two world positions with headings (radians or null) -> { pts, len } | null
  routeXY(x0, z0, h0, x1, z1, h1, opt = {}) {
    if (!this.ok || !this.links.length) return null;
    const A = this.projLinks(x0, z0, h0, opt), B = this.projLinks(x1, z1, h1, opt);
    if (!A.length || !B.length) { this.routeFails++; return null; }
    let best = null;
    for (const a of A.slice(0, 2)) for (const b of B.slice(0, 2)) {
      if (a.d > 40 || b.d > 40) continue;
      let r;
      if (a.L === b.L) { const P = this.sub(a.L, a.s, b.s); r = { pts: P, len: Math.abs(b.s - a.s) }; }
      else {
        const starts = [[a.L.a, a.s], [a.L.b, a.L.len - a.s]];
        const goals = new Map([[b.L.a, b.s], [b.L.b, b.L.len - b.s]]);
        const g = this.dijkstra(starts, goals, opt); if (!g) continue;
        const n0 = g.nodes[0], n1 = g.end;
        const head = this.sub(a.L, a.s, n0 === a.L.a ? 0 : a.L.len), tail = this.sub(b.L, n1 === b.L.a ? 0 : b.L.len, b.s);
        r = { pts: head.concat(g.pts.slice(1), tail.slice(1)), len: g.len };
      }
      const pts = [[x0, z0], ...r.pts, [x1, z1]];
      // reversal penalty: the route starts against the aircraft's heading / ends against its heading [inf]
      let cost = r.len + a.d + b.d;
      const d0 = pts.length > 2 ? bearR(pts[2][0] - pts[1][0], pts[2][1] - pts[1][1]) : null;
      if (h0 != null && d0 != null && Math.abs(wrapPi(d0 - h0)) > 100 * D2R) cost += 60;
      if (!best || cost < best.cost) best = { pts, len: r.len + a.d + b.d, cost };
    }
    if (!best) { this.routeFails++; return null; }
    // clean: drop consecutive duplicates; cumulative length
    const P = [best.pts[0]]; for (const p of best.pts.slice(1)) if (Math.hypot(p[0] - P[P.length - 1][0], p[1] - P[P.length - 1][1]) > 0.05) P.push(p);
    const cum = [0]; for (let k = 1; k < P.length; k++) cum.push(cum[k - 1] + Math.hypot(P[k][0] - P[k - 1][0], P[k][1] - P[k - 1][1]));
    this.routes++;
    return { pts: P, cum, len: cum[cum.length - 1] };
  }
}
function polyAt(R, s) {
  const c = R.cum; s = clamp(s, 0, R.len); let lo = 0, hi = c.length - 1;
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (c[m] <= s) lo = m; else hi = m; }
  const a = R.pts[lo], b = R.pts[hi], l = c[hi] - c[lo] || 1e-9, u = (s - c[lo]) / l;
  return { x: a[0] + (b[0] - a[0]) * u, z: a[1] + (b[1] - a[1]) * u, ux: (b[0] - a[0]) / l, uz: (b[1] - a[1]) / l };
}

// ---------------------------------------------------------------- track
class Track {
  constructor(key) {
    this.key = key; this.fx = []; this.info = {}; this.firstSeen = 0; this.lastFixT = 0; this.lastRecv = 0;
    this.ident = null; this.dims = null; this.phase = 'unknown'; this.phaseInfo = { label: 'Unknown', rwy: null, leg: null, src: null, rule: null, since: 0, provisional: false, tower: null };
    this.scope = 'pending'; this.inView = false; this.park = null; this.stale = false; this.removed = false; this.noData = false; this.vehicle = false; this.hidden = false;
    this.disp = { x: 0, y: 0, z: 0, hdg: 0, pitch: 0, roll: 0, gs: 0, vs: 0, ground: true, valid: false, alpha: 0, gear: 1, flaps: 0, extrap: 0 };
    this.ctl = null; this.physOff = null; this.restPose = null; this.rests = new Map(); this.rejects = 0; this.matchWay = null; this.routeCache = new Map();
  }
  get last() { return this.fx[this.fx.length - 1]; }
}

export class Traffic {
  constructor({ airport = null, taxigraph = null, site = null, parking = null, persist = true, delay = DELAY_MS } = {}) {
    this.airport = airport; this.site = site; this.parking = parking; this.persist = persist;
    this.tracks = new Map(); this.events = []; this.onEvent = null; this.net = new TaxiNet(taxigraph);
    this.classifier = new PhaseClassifier({ airport, site });
    this.delay = delay; this.delayTarget = delay; this.adaptDelay = true; this.ages = [];
    this.offset = null; this.dataNow = 0; this.version = 0; this._tgt = {};
    this.counters = { reports: 0, rejects: 0, altRejects: 0, reacquire: 0, cuts: 0, routes: 0, routeFallback: 0, parked: 0, hangared: 0, removed: 0, vehicles: 0 };
    this.groundY = site ? (x, z) => site.groundY(x, z) : () => 11.4;
    this.paved = pavedWith(site);
    if (persist) this.loadParked();
  }
  displayTime(now) { return now - this.delay; }
  pavedNear(x, z, r = PAVED_NEAR_M) { const P = this.paved; if (!this.site) return true; if (P(x, z)) return true; for (const [dx, dz] of [[r, 0], [-r, 0], [0, r], [0, -r]]) if (P(x + dx, z + dz)) return true; return false; }
  // replay / pack: display lookahead_s behind, fixed (fork map 2.7)
  setLookahead(s) { this.delay = this.delayTarget = s * 1000; this.adaptDelay = false; }
  event(e) { this.events.push(e); if (this.events.length > 2000) this.events.splice(0, 500); if (this.onEvent) try { this.onEvent(e); } catch (err) { } }

  // ---------------------------------------------------------------- ingest
  ingest(payload, recvNow = Date.now()) {
    const off = recvNow - payload.now;
    // relay clock -> this clock (sfo3d: the minimum of recvNow - now, drifting up slowly). A first payload more than 5 s old is
    // history (the relay's / shim's ?history replay of the last lookahead_s): it says nothing about the clock skew -> 0
    if (this.offset == null) this.offset = Math.abs(off) < 5000 ? off : 0;
    else this.offset = Math.min(this.offset + (recvNow - (this._lastRecv || recvNow)) * 0.002, off);
    this._lastRecv = recvNow; this.dataNow = Math.max(this.dataNow, recvNow);
    if (payload.msg && /restarts/.test(payload.msg)) this.onReplayRestart(recvNow);
    const seen = new Set();
    for (const a of payload.aircraft) {
      if (!a.hex || seen.has(a.hex)) continue; seen.add(a.hex);
      const w = wgs84ToWorld(a.lat, a.lon, 0); const x = w[0], z = w[2];
      if (Math.hypot(x, z) > 30000) continue;
      let tr = this.tracks.get(a.hex);
      const tf = a.t + this.offset;
      if (!tr && recvNow - tf > MOVING_LOST_MS) continue;
      if (!tr) { tr = new Track(a.hex); tr.firstSeen = recvNow; this.tracks.set(a.hex, tr); }
      else if (tr.stale) {
        const P = tr.restPose || tr.lastPose; const gap = recvNow - tr.lastRecv;
        const same = P && a.ground && (a.gs ?? 0) < 3 && Math.hypot(x - P.x, z - P.z) < REACQ_PARK_M;
        tr.stale = false;
        if (!same) { tr.reacquire = true; this.releasePark(tr, tf, 'moved while silent'); }
        else if (tr.park && tr.park.inside) { tr.park.inside = false; tr.hidden = false; this.event({ t: tf, kind: 'hangar_out', type: 'hangar_out', key: tr.key, rwy: null, spot: tr.park.spotId || null, src: 'inf', rule: 'heard again at its hangar', cls: tr.dims && tr.dims.cls, tower: towerStatus(tf) }); }
        if (gap > 600000) tr.reacquire = true;
      }
      this.setInfo(tr, a);
      const L = tr.last;
      if (L && tf <= L.t + 20) { tr.lastRecv = recvNow; continue; }    // same report again / out of order
      if (L && !tr.stale) this.ages.push([recvNow, (recvNow - L.t) / 1000, !L.ground || (L.gs || 0) > 1]);
      if (L && tf - L.t > 90000) tr.reacquire = true;                    // longer than any polling hole: re-placed (fade)
      const f = this.report(tr, a, x, z, tf);
      if (!f) { tr.lastRecv = recvNow; continue; }
      tr.fx.push(f); while (tr.fx.length > 700 || (tr.fx.length > 4 && f.t - tr.fx[0].t > 20 * 60000)) tr.fx.shift();
      tr.lastFixT = tf; tr.lastRecv = recvNow; this.counters.reports++;
      if (tr.vehicle) { tr.phase = 'vehicle'; f.ph = 'vehicle'; f.pi = { src: 'obs', rule: 'emitter category / type / relay _veh' }; continue; }
      const res = this.classifier.step(tr, f, recvNow);
      for (const e of res.events) this.event(e);
      // rest poses of the newest still runs now (not lazily at display time): a segment that ends at a still fix then
      // already ends at the pose drawn there (spot pose / median), so arriving at a spot is continuous
      for (let q = Math.max(0, tr.fx.length - 3); q < tr.fx.length; q++) if (tr.fx[q].ground && tr.fx[q].stillRun) this.restOf(tr, tr.fx[q]);
    }
    if (this.adaptDelay) this.adapt(recvNow);
    this.version++;
  }
  onReplayRestart(now) { for (const tr of this.tracks.values()) { tr.reacquire = true; } }
  adapt(now) {
    while (this.ages.length && now - this.ages[0][0] > 120000) this.ages.shift();
    const a = this.ages.filter(q => q[2]).map(q => q[1]).filter(v => v < 70).sort((p, q) => p - q);
    if (a.length < 10) return;
    // the age the newest report reaches before the next arrives (p90) + 0.5 s: interpolation between real fixes nearly
    // always (sfo3d used p50 + 0.3 s at a 1 Hz relay; the HWD relay polls every >= 6.5 s, docs/phase2_relay.md)
    this.delayTarget = clamp((a[Math.floor(a.length * 0.9)] + 0.5) * 1000, DELAY_MIN, DELAY_MAX);
  }
  setInfo(tr, a) {
    const I = tr.info;
    Object.assign(I, { flight: a.flight || I.flight || null, reg: a.reg || I.reg || null, icao: a.icao || I.icao || null, desc: a.desc || I.desc || null, ownOp: a.ownOp || I.ownOp || null,
      category: a.category || I.category || null, masked: !!(a.masked || I.masked), mx: a.mx || I.mx || null, src: a.srcType || I.src, nacp: a.nacp ?? I.nacp, squawk: tr.ident && tr.ident.masked ? null : (a.squawk ?? I.squawk ?? null),
      emergency: a.emergency, vehFlag: a.veh || I.vehFlag });
    if (I.masked) { I.flight = null; I.reg = null; I.ownOp = null; I.squawk = null; if (I.mx) I.mx = { r: null, t: I.mx.t, d: I.mx.d, op: null }; }
    if (!I.icao && I.mx && I.mx.t) I.icao = I.mx.t;
    tr.ident = identity(I, tr.key, tr.ident);
    const dk = (I.icao || '-') + '|' + (I.category || '-');
    if (dk !== tr._dimsKey) { tr._dimsKey = dk; tr.dims = gaDims(I.icao, I.category); }
    if (!tr.vehicle && (I.vehFlag || isVehicle({ category: I.category, icao: I.icao }) || a.srcType === 'adsb_icao_nt')) { tr.vehicle = true; this.counters.vehicles++; }
    if (!tr.vehicle && String(tr.key)[0] === '~' && a.ground && !a.flight && !a.reg && !a.icao) { tr.vehicle = true; tr.anon = true; this.counters.vehicles++; }
  }
  // one report: hygiene (position jump, altitude step), derived heights (classifier.prep), heading, velocity, map matching
  report(tr, a, x, z, tf) {
    const L = tr.last, g = !!a.ground;
    const f = { t: tf, x, z, g, gs: a.gs, trk: g ? null : a.track, th: a.trueHeading, altB: a.altBaro, altG: a.altGeom, vs: a.baroRate ?? a.geomRate ?? null, nacp: a.nacp, src: a.srcType };
    if (L) {   // position jump test (sfo3d): faster than physically possible; three consistent "jumps" = real
      const dt = Math.max(0.2, (tf - L.t) / 1000), d = Math.hypot(x - L.x, z - L.z);
      const vmax = Math.max(a.gs ?? 0, L.gs ?? 0, g ? 10 : 160) * KT;
      if (d > 1.5 * vmax * dt + (g ? 30 : 250) && dt < 60) {
        const R0 = tr.rejPt; tr.rejects = R0 && Math.hypot(x - R0[0], z - R0[1]) < 40 ? tr.rejects + 1 : 1; tr.rejPt = [x, z]; this.counters.rejects++;
        if (tr.rejects < 3) return null;
        tr.reacquire = true; this.counters.reacquire++;
      }
    }
    tr.rejects = 0; tr.rejPt = null;
    this.classifier.prep(tr, f);
    const heli = tr.dims && tr.dims.cls === 'heli';
    const hc = (tr._k && tr._k.q === 100) ? CR.H_CONTACT_COARSE : CR.H_CONTACT;
    // display ground: the flag, runway contact, or ground by kinematics ON (or within PAVED_NEAR_M of) pavement - a low slow
    // fix over the approach grass (a per-unit altitude bias of tens of ft, derive.py) stays airborne in the drawing; the
    // classifier keeps the offline G state for its counts
    f.ground = heli ? g : (g || (!!f.strip && f.h != null && f.h <= hc && (f.gs == null || f.gs < 120)) || (f.gk && this.pavedNear(x, z)));
    const gy = this.groundY(x, z);
    if (f.ground) f.y = gy;
    else {
      let y = f.h != null ? f.surfFt * FT + f.h * FT : (L ? L.y : gy + 300);
      // altitude plausibility (sfo3d): a step implying > ~6,000 ft/min against the previous fix is garbled unless 3 agree
      if (L && tf > L.t) {
        const dt = (tf - L.t) / 1000, pred = L.ground ? L.y : L.y + (L.vsm || 0) * Math.min(dt, 10), lim = 30.5 * dt + 25 + (L.ground ? 0 : Math.abs(L.vsm || 0) * 0.5 * dt);
        if (Math.abs(y - pred) > lim && dt < 20) { const q = tr.altRej; tr.altRej = q && Math.abs(q.y - y) < 60 ? { y, n: q.n + 1 } : { y, n: 1 };
          if (tr.altRej.n < 3) { y = pred + clamp(y - pred, -lim, lim); this.counters.altRejects++; } } else tr.altRej = null;
      }
      f.y = Math.max(gy + 0.3, y);
    }
    f.vsm = f.vs != null ? f.vs * FT / 60 : null;
    // direction of motion and nose (radians internally)
    let chord = null, dtL = L ? (tf - L.t) / 1000 : 0;
    if (L) { const dx = x - L.x, dz = z - L.z, d = Math.hypot(dx, dz); if (d > (f.ground ? 3 : 20)) chord = bearR(dx, dz); if (f.gs == null && dtL > 0) f.gs = d / dtL / KT; }
    f.gsm = (f.gs ?? 0) * KT;
    const th = f.th != null ? f.th * D2R : null;
    if (!f.ground) { f.dir = f.trk != null ? f.trk * D2R : chord ?? (L ? L.dir : th ?? 0); f.hd = th ?? f.dir; f.hdReal = th != null; }
    else {
      const moving = f.gsm > 0.5;
      f.dir = moving ? (chord ?? th ?? (L ? L.dir : 0)) : (L ? L.dir : th ?? 0);
      f.hd = th ?? (moving ? f.dir : (L ? L.hd : null)); f.hdReal = th != null;
      // map matching onto the taxiway centrelines (sfo3d): snap laterally when close, aligned and at taxi speed
      if (moving && f.gs > 2 && this.net.ok && !tr.vehicle && !heli && !f.strip) {
        const mm = this.net.match(x, z, f.dir, tr.matchWay, 10, (th != null ? 20 : 35) * D2R);
        if (mm) { const s = (lo, hi, v) => { const t = clamp((v - lo) / (hi - lo), 0, 1); return t * t * (3 - 2 * t); };
          const wgt = (1 - s(5, 10, mm.d)) * s(2, 4, f.gs); f.px = x + (mm.px - x) * wgt; f.pz = z + (mm.pz - z) * wgt; tr.matchWay = mm.way; f.snap = mm.d * wgt; }
        else tr.matchWay = null;
      }
    }
    if (f.px == null) { f.px = x; f.pz = z; }
    const v = hvR(f.dir); f.vx = v[0] * f.gsm; f.vz = v[1] * f.gsm;
    f.turn = 0; if (L && L.dir != null && dtL > 0.3 && dtL < 6) { const w = wrapPi(f.dir - L.dir) / dtL; f.turn = Math.abs(w) < (f.ground ? 20 : 6) * D2R ? w : 0; }
    return f;
  }

  // ---------------------------------------------------------------- per frame
  update(now, dt) {
    const el = this._lastNow != null ? clamp((now - this._lastNow) / 1000, 0, 5) : dt; this._lastNow = now;
    const nSub = Math.max(1, Math.ceil(el / 0.1 - 1e-6)), h = el / nSub || dt;
    if (this.adaptDelay) this.delay += clamp(this.delayTarget - this.delay, -500 * el, 500 * el);
    const tDisp = this.displayTime(now);
    const removed = [];
    for (const tr of this.tracks.values()) {
      if (tr.fadeOut && !(tr.disp.alpha > 0.01)) { removed.push(tr); continue; }
      if (!tr.vehicle) for (const e of this.classifier.tick(tr, now)) this.event(e);
      const lf = tr.last; if (!lf) continue;
      const age = now - lf.t; tr.noData = age > 20000;
      const shownLast = tDisp - lf.t;         // how far the display is past the newest fix
      if (!tr.stale && !tr.fadeOut) {
        if (tr.vehicle && age > VEH_KEEP_MS) this.gone(tr, 'vehicle');
        else if (!lf.ground && age > STALE_AIR_MS && shownLast > 15000) this.gone(tr, 'air');
        else if (lf.ground && shownLast > 15000 && age > MOVING_LOST_MS) this.groundLost(tr, now, lf);
      } else if (tr.stale && now - tr.lastRecv > PARK_KEEP_MS) this.gone(tr, 'expired');
      // simulate bodies near HWD only (SIM_NM); others keep their fixes but are not drawn
      // (ground tracks only on and around HWD: aircraft on the ground at OAK, 6 NM away, are outside the D6 window)
      const rl = Math.hypot(lf.x, lf.z);
      const near = (lf.ground ? rl < 4000 : rl < SIM_NM * NM) || (tr.ctl && !tr.ctl.ground && Math.hypot(tr.ctl.x, tr.ctl.z) < SIM_NM * NM);
      if (!near) { tr.disp.valid = false; tr.inView = false; tr.ctl = null; continue; }
      for (let i = 0; i < nSub; i++) this.step(tr, tDisp - (nSub - 1 - i) * h * 1000, h);
      this.view(tr);
    }
    for (const tr of removed) this.remove(tr);
  }
  gone(tr, why) { if (!tr.disp.valid || !(tr.disp.alpha > 0.01)) { this.remove(tr); return; } tr.fadeOut = true; tr.goneWhy = why; }
  // a ground track without a position for MOVING_LOST_MS: parked (kept), hangared (hidden), or lost (faded out)
  groundLost(tr, now, lf) {
    const H = this.parking && this.parking.hangarNear(lf.x, lf.z);
    const slow = (lf.gs ?? 0) < 8;
    if (H && slow) {
      tr.stale = true; tr.hidden = true; tr.park = { ...(tr.park || {}), spotId: tr.park ? tr.park.spotId : null, kind: 'hangar', zone: H.hangar.name || 'hangar', src: 'inf', inside: true, hangar: H.hangar.id,
        pose: tr.restPose ? { x: tr.restPose.x, z: tr.restPose.z, hdg: tr.restPose.hdg } : { x: lf.x, z: lf.z, hdg: lf.hd != null ? toDeg(lf.hd) : null } };
      this.counters.hangared++; this.event({ t: lf.t, kind: 'hangar_in', type: 'hangar_in', key: tr.key, rwy: null, spot: tr.park.spotId || null, src: 'inf', rule: `signal ended ${H.d.toFixed(1)} m from ${H.hangar.name || 'a hangar'} (<= 8 m)`, cls: tr.dims && tr.dims.cls, tower: towerStatus(lf.t) });
      this.saveParkedSoon(); return;
    }
    const parked = tr.restPose && (lf.ph === 'parked' || (lf.gs ?? 0) < 1);
    if (parked && !(lf.strip)) { tr.stale = true; tr.staleSince = now; this.saveParkedSoon(); return; }
    this.gone(tr, 'ground lost');
  }
  remove(tr) { tr.removed = true; this.releasePark(tr, this.dataNow, 'removed'); for (const e of this.classifier.flush(tr, this.dataNow)) this.event(e); this.tracks.delete(tr.key); this.counters.removed++; if (tr.park || tr.stale) this.saveParkedSoon(); }
  clearParked() { for (const tr of [...this.tracks.values()]) if (tr.stale) this.remove(tr); this.saveParked(); }
  releasePark(tr, t, why) {
    if (!tr.park) return; const p = tr.park; tr.park = null; tr.hidden = false;
    if (this.parking) this.parking.release(tr.key);
    if (p.spotId || p.kind) this.event({ t, kind: 'unpark', type: 'unpark', key: tr.key, rwy: null, spot: p.spotId || null, src: p.src || 'obs', rule: why, cls: tr.dims && tr.dims.cls, tower: towerStatus(t) });
  }
  // D6 display window with hysteresis: <= 5 NM and <= 3,000 ft AGL (on the ground: anywhere within the window)
  view(tr) {
    const D = tr.disp; if (!D.valid) { tr.inView = false; return; }
    const r = Math.hypot(D.x, D.z) / NM, hAgl = (D.y - this.groundY(D.x, D.z)) / FT;
    const k = tr.inView ? VIEW_HYST : 1;
    tr.inView = r <= VIEW_NM * k && (D.ground || hAgl <= VIEW_FT * k);
  }

  // ---------------------------------------------------------------- display target at display time t
  restOf(tr, f) {
    if (!f || !f.stillRun) return null; const k = f.stillRun[0];
    let P = tr.rests.get(k); const run = tr.fx.filter(q => q.stillRun && q.stillRun[0] === k);
    if (P && P.n === run.length) return P;
    // median antenna position of the still fixes -> main-gear origin (dims.ant behind the nose, xMain behind the nose)
    const xs = run.map(q => q.x), zs = run.map(q => q.z); const ax = median(xs), az = median(zs);
    const hs = run.filter(q => q.th != null).map(q => q.th);
    let hdg = hs.length ? circMedianDeg(hs) : null, hdgReal = hs.length > 0, hsrc = hs.length ? 'obs (true_heading)' : null;
    if (hdg == null) { const i0 = tr.fx.indexOf(run[0]); for (let i = i0; i >= Math.max(0, i0 - 6); i--) { const q = tr.fx[i]; if (q.gsm > 1 && q.dir != null) { hdg = toDeg(q.dir); hsrc = 'inf (direction of the last motion)'; break; } } }
    const isPark = run.some(q => q.ph === 'parked');
    let pose = { x: ax, z: az, hdg, hdgReal, ant: [ax, az], src: 'obs', rule: 'median of the still fixes' };
    const T = tr.dims; const toOrigin = (p, hd) => { if (hd == null || !T) return p; const fv = hvR(hd * D2R), d = T.xMain - T.ant; return { ...p, x: p.ant[0] - fv[0] * d, z: p.ant[1] - fv[1] * d }; };
    let spot = null;
    if (isPark && this.parking && T) {
      const m = this.parking.match(toOrigin(pose, hdg), T, { heli: T.cls === 'heli', key: tr.key });
      if (m && m.ok) { spot = m.spot; const pp = this.parking.parkPose(spot, T, toOrigin(pose, hdg)); pose = { ...pose, x: pp.x, z: pp.z, hdg: pp.hdg ?? hdg, src: pp.src, rule: pp.rule, headed: spot.hdg != null && (spot.ref === 'tee_junction' || spot.ref === 'rule_point') };
        if (pose.hdg == null) { pose.hdg = this.faceTaxi(pose.x, pose.z); hsrc = 'inf (nose toward the nearest taxi line)'; } else if (pose.headed) hsrc = 'spot heading (' + (spot.hdgSrc || 'inf') + ')'; }
    }
    if (!spot) { if (pose.hdg == null) { pose.hdg = this.faceTaxi(ax, az); hsrc = 'inf (nose toward the nearest taxi line)'; } pose = toOrigin(pose, pose.hdg); }
    P = { ...pose, n: run.length, spot, isPark, hsrc, t0: k };   // t0 = the run's stable start (classifier run0)
    tr.rests.set(k, P); if (tr.rests.size > 12) tr.rests.delete(tr.rests.keys().next().value);
    if (isPark) this.notePark(tr, P, run[run.length - 1].t);
    return P;
  }
  faceTaxi(x, z) { const L = this.net.ok ? this.net.projLinks(x, z) : []; if (!L.length || L[0].d < 1) return 0; return toDeg(bearR(L[0].px - x, L[0].pz - z)); }
  notePark(tr, P, t) {
    const prev = tr.park;
    if (prev && prev.t0 === P.t0 && (prev.spotId || null) === (P.spot ? P.spot.id : null)) { prev.pose = { x: P.x, z: P.z, hdg: P.hdg }; return; }
    if (prev && prev.t0 !== P.t0) this.releasePark(tr, t, 'parked elsewhere');
    if (P.spot && this.parking) this.parking.occupy(tr.key, P.spot);
    tr.park = { spotId: P.spot ? P.spot.id : null, kind: P.spot ? P.spot.kind : 'unspotted', zone: P.spot ? P.spot.zone : (this.site && this.site.apronAt(P.x, P.z) ? this.site.apronAt(P.x, P.z).name : null), src: P.spot ? P.spot.src : 'obs',
      inside: false, pose: { x: P.x, z: P.z, hdg: P.hdg }, headed: !!P.headed, hdgSrc: P.hsrc, t0: P.t0 };
    this.counters.parked++;
    this.event({ t: P.t0, kind: 'park', type: 'park', key: tr.key, rwy: null, spot: tr.park.spotId, src: tr.park.src, rule: P.spot ? `matched to ${P.spot.kind} spot (${P.rule})` : 'parked off the Phase 1 spots (own pose)', cls: tr.dims && tr.dims.cls, tower: towerStatus(P.t0) });
    this.saveParkedSoon();
  }
  target(tr, t, o) {
    const F = tr.fx, n = F.length; o.stop = false; o.hd = null; o.route = false;
    if (tr.stale && tr.park && tr.park.pose) { const p = tr.park.pose; Object.assign(o, { x: p.x, z: p.z, y: this.groundY(p.x, p.z), vx: 0, vz: 0, vy: 0, gs: 0, ground: true, ex: 0, stop: true, hd: p.hdg != null ? p.hdg * D2R : null }); o.rest = tr.restPose; return o; }
    let i = n - 1; while (i > 0 && F[i - 1].t > t) i--;
    if (t <= F[0].t) {   // before the first fix: hidden (alpha stays 0); airborne: back along its velocity (sfo3d), <= 10 s
      this.fill(o, F[0]); o.ex = 0; o.before = true;
      if (!F[0].ground) { const b = Math.min(10, (F[0].t - t) / 1000); o.x -= o.vx * b; o.z -= o.vz * b; o.y -= (o.vy || 0) * b; if ((F[0].t - t) / 1000 > 10) { o.vx = o.vz = o.vy = 0; o.gs = 0; } }
      else { o.vx = o.vz = 0; o.gs = 0; }
      return this.restTarget(tr, o, F[0], F[0]) || o;
    }
    o.before = false;
    if (t >= F[n - 1].t) return this.extrapolate(tr, F[n - 1], (t - F[n - 1].t) / 1000, o);
    const a = F[i - 1], b = F[i];
    const dtm = b.t - a.t, dt = dtm / 1000, u = (t - a.t) / dtm;
    // a take-off or landing inside a polling hole: drawn along the taxi graph, the runway centreline (roll) and a straight
    // climb-out / approach (transition) instead of a straight line from the holding point to the climb-out fix
    if (a.ground !== b.ground && dt > HOLE_S && tr.dims && tr.dims.cls !== 'heli') {
      const P = this.transitionFor(tr, a, b, dt); if (P) return this.samplePlan(P, t, o);
    }
    if (a.ground && b.ground) {
      const rt = this.restTarget(tr, o, a, b); if (rt) return rt;
      const A0 = this.endPt(tr, a), B0 = this.endPt(tr, b);
      const d = Math.hypot(B0[0] - A0[0], B0[1] - A0[1]);
      if (d > ROUTE_MIN_M && !(tr.dims && tr.dims.cls === 'heli') && (dt > HOLE_S || this.offPaveSeg(tr, a, b))) {
        let R = this.routeFor(tr, a, b, dt);
        // no route (or an implausible one) across a ground hole: the straight chord, but with the end speeds of the two fixes
        // (arc-length Hermite as for routes) - never the sfo3d linear fallback, whose constant chord speed jumps at both ends
        if (!R && dt > 20) R = this.polyOf([A0, B0]);
        if (R) {
          // arc length by a cubic Hermite with the end speeds (clamped for monotonicity: alpha, beta <= 2.1)
          const va = Math.min(a.gsm, 2.1 * R.len / dt), vb = Math.min(b.gsm, 2.1 * R.len / dt);
          const u2 = u * u, u3 = u2 * u, h10 = u3 - 2 * u2 + u, h01 = -2 * u3 + 3 * u2, h11 = u3 - u2;
          const s = h01 * R.len + h10 * dt * va + h11 * dt * vb;
          const ds = (6 * u - 6 * u2) * R.len / dt + (3 * u2 - 4 * u + 1) * va + (3 * u2 - 2 * u) * vb;
          const p = polyAt(R, s);
          Object.assign(o, { x: p.x, z: p.z, y: this.groundY(p.x, p.z), vx: p.ux * ds, vz: p.uz * ds, vy: 0, gs: Math.abs(ds), ground: true, ex: 0, route: true });
          return o;
        }
      }
    }
    // Hermite between real reports (sfo3d sampleReps)
    const [apx, apz] = a.ground ? this.endPt(tr, a) : [a.px, a.pz], [bpx, bpz] = b.ground ? this.endPt(tr, b) : [b.px, b.pz];
    const cx = (bpx - apx) / dt, cz = (bpz - apz) / dt, cs = Math.hypot(cx, cz);
    let va = [a.vx, a.vz], vb = [b.vx, b.vz];
    // (sfo3d: a reported velocity the chord cannot explain is replaced by the chord velocity - right for 1-s reports with
    // noisy velocities. Across a polling hole in the air the reported velocities are the only knowledge of the turn the
    // aircraft flew in the hole (a pattern turn of 90-180 deg in 46 s), so they are kept unless the chord is faster than the
    // aircraft or the two speeds differ by more than 2.5 x.)
    const airHole = !a.ground && !b.ground && dt > HOLE_S && a.gsm > 10 && b.gsm > 10 && cs < 1.3 * Math.max(a.gsm, b.gsm) && Math.max(a.gsm, b.gsm) < 2.5 * Math.min(a.gsm, b.gsm);
    const ok = (v) => airHole || Math.hypot(v[0] - cx, v[1] - cz) < Math.max(3, 0.35 * cs);
    const lin = dt > (a.ground ? 20 : 60) || a.ground !== b.ground;
    const jump = !lin && a.ground && b.ground && cs * dt > 1.6 * Math.max(a.gsm || 0, b.gsm || 0, 0.8) * dt + 3;
    if (lin || (!ok(va) && !jump)) va = [cx, cz]; if (lin || (!ok(vb) && !jump)) vb = [cx, cz];
    const u2 = u * u, u3 = u2 * u;
    const h00 = 2 * u3 - 3 * u2 + 1, h10 = u3 - 2 * u2 + u, h01 = -2 * u3 + 3 * u2, h11 = u3 - u2;
    o.x = h00 * apx + h10 * dt * va[0] + h01 * bpx + h11 * dt * vb[0];
    o.z = h00 * apz + h10 * dt * va[1] + h01 * bpz + h11 * dt * vb[1];
    o.vx = va[0] + (vb[0] - va[0]) * u; o.vz = va[1] + (vb[1] - va[1]) * u;
    if (!a.ground && !b.ground) {
      const cy = (b.y - a.y) / dt; let sa = a.vsm ?? cy, sb = b.vsm ?? cy;
      if (Math.abs(sa - cy) > Math.max(3, Math.abs(cy))) sa = cy; if (Math.abs(sb - cy) > Math.max(3, Math.abs(cy))) sb = cy;
      o.y = h00 * a.y + h10 * dt * sa + h01 * b.y + h11 * dt * sb; o.vy = sa + (sb - sa) * u;
    } else { o.y = a.y + (b.y - a.y) * u; o.vy = (b.y - a.y) / dt; }
    o.gs = Math.hypot(o.vx, o.vz); o.ex = 0;
    // ground <-> air across a hole: lift-off soon after a ground fix, touchdown shortly before one - never a 23-s "roll" over
    // the grass beyond the runway end (the drawn half of a 46-s hole). Lift-off at VR after accelerating at ROLL_ACC from the
    // ground fix's speed; touchdown at the air fix's speed decelerating at ROLL_DEC to the ground fix's [inf, GA values]
    if (a.ground !== b.ground) {
      const T = tr.dims, VR = T && T.cls === 'jet' ? 55 : T && T.cls === 'turboprop' ? 40 : 28, heli = T && T.cls === 'heli';
      if (a.ground) { const tl = heli ? Math.min(3, dt * 0.5) : clamp((VR - a.gsm) / 2.5, 0, 0.8 * dt); o.ground = (t - a.t) / 1000 < tl; }
      else { const tt = heli ? Math.min(3, dt * 0.5) : clamp((Math.max(a.gsm * 0.9, VR) - b.gsm) / 2.0, 0, 0.8 * dt); o.ground = (b.t - t) / 1000 < tt; }
    } else o.ground = a.ground;
    if (o.ground) o.y = this.groundY(o.x, o.z);
    else o.y = Math.max(o.y, this.groundY(o.x, o.z) + 0.3);
    const ha = a.hdReal ? a.hd : null, hb = b.hdReal ? b.hd : null;
    o.hd = ha != null && hb != null ? ha + wrapPi(hb - ha) * u : null;
    return o;
  }
  // the position a segment starts / ends at: a fix of a still run stands for the run's rest pose (spot pose, median, physics
  // offset) - so leaving a parking spot or arriving at one is continuous with the pose drawn there
  endPt(tr, f) { if (f.ground && f.stillRun) { const P = tr.rests.get(f.stillRun[0]); if (P) return [P.x, P.z]; } return [f.px, f.pz]; }
  // both bracket fixes in the same still run: the run's rest pose
  restTarget(tr, o, a, b) {
    if (!a.stillRun || !b.stillRun || a.stillRun[0] !== b.stillRun[0]) return null;
    const P = this.restOf(tr, a); if (!P) return null;
    tr.restPose = P;
    Object.assign(o, { x: P.x, z: P.z, y: this.groundY(P.x, P.z), vx: 0, vz: 0, vy: 0, gs: 0, ground: true, ex: 0, stop: true, hd: P.hdg != null ? P.hdg * D2R : null });
    return o;
  }
  fill(o, r) { Object.assign(o, { x: r.px, z: r.pz, y: r.y, vx: r.vx, vz: r.vz, vy: r.ground ? 0 : (r.vsm || 0), gs: r.gsm, ground: r.ground, hd: r.hdReal ? r.hd : null }); return o; }
  extrapolate(tr, L, dt, o) {
    o.ex = dt;
    if (L.ground && L.stillRun) { const rt = this.restTarget(tr, o, L, L); if (rt) return rt; }
    let vx = L.vx, vz = L.vz, x = L.px, z = L.pz; const w = L.turn || 0; const t1 = Math.min(dt, DR_MAX_S);
    if (Math.abs(w) > 1e-4) { const sp = Math.hypot(vx, vz), h0 = bearR(vx, vz), h1 = h0 + w * t1; x += sp / w * (Math.cos(h0) - Math.cos(h1)); z -= sp / w * (Math.sin(h1) - Math.sin(h0)); const v = hvR(h1); vx = v[0] * sp; vz = v[1] * sp; }
    else { x += vx * t1; z += vz * t1; }
    const rest = dt - t1;
    if (rest > 0) { if (L.ground) { const k = DR_STOP_TAU_S * (1 - Math.exp(-rest / DR_STOP_TAU_S)); x += vx * k; z += vz * k; const d = Math.exp(-rest / DR_STOP_TAU_S); vx *= d; vz *= d; } else { x += vx * Math.min(rest, 20); z += vz * Math.min(rest, 20); if (rest > 20) { vx = 0; vz = 0; } } }
    Object.assign(o, { x, z, vx, vz, gs: Math.hypot(vx, vz), ground: L.ground, hd: L.hdReal ? L.hd : null });
    o.y = L.ground ? this.groundY(x, z) : Math.max(this.groundY(x, z) + 0.3, L.y + (L.vsm || 0) * Math.min(dt, 10)); o.vy = L.ground || dt > 10 ? 0 : (L.vsm || 0);
    return o;
  }
  // ---- take-off / landing in a hole: a timed plan of segments
  //   {kind: 'wait', t0, t1, x, z, hd} | {kind: 'path', t0, t1, R (polyline), v0, v1} (ground, constant acceleration)
  //   | {kind: 'air', t0, t1, p0: [x, y, z], p1, v0: [vx, vy, vz], v1} (Hermite)
  // Values [inf, GA]: VR / lift-off 28 m/s (55 kt; jets 55, turboprops 40), roll acceleration 2.5 m/s2 (jets 4), landing
  // deceleration 2.0 m/s2 to an exit speed of 7 m/s, touchdown 150 m past the landing threshold, taxi 5 m/s (max 12).
  transitionFor(tr, a, b, dt) {
    const k = 'x' + a.t; if (tr.routeCache.has(k)) return tr.routeCache.get(k);
    let P = null;
    try { P = a.ground ? this.planTakeoff(tr, a, b, dt) : this.planLanding(tr, a, b, dt); } catch (e) { P = null; }
    this.counters[P ? 'transitionPlans' : 'transitionLinear'] = (this.counters[P ? 'transitionPlans' : 'transitionLinear'] || 0) + 1;
    tr.routeCache.set(k, P); return P;
  }
  rwyFor(x, z, trk, near = 150) {   // runway whose axis is within `near` m across and aligned (+-30 deg) with trk (rad)
    let best = null;
    for (const r of (this.site && this.site.runways) || []) {
      const px = x - r.origin[0], pz = z - r.origin[1]; const al = px * r.dir[0] + pz * r.dir[1], ac = px * r.right[0] + pz * r.right[1];
      if (Math.abs(ac) > near || al < -2100 || al > r.length + 1100) continue;
      let sgn = 1; if (trk != null) { const h = bearR(r.dir[0], r.dir[1]); const d = Math.abs(wrapPi(trk - h)); if (d > 150 * D2R) sgn = -1; else if (d > 30 * D2R) continue; }
      if (!best || Math.abs(ac) < Math.abs(best.ac)) best = { r, al, ac, sgn };
    }
    return best;
  }
  axisPt(r, al) { return [r.origin[0] + r.dir[0] * al, r.origin[1] + r.dir[1] * al]; }
  polyOf(pts) { const P = [pts[0]]; for (const p of pts.slice(1)) if (Math.hypot(p[0] - P[P.length - 1][0], p[1] - P[P.length - 1][1]) > 0.05) P.push(p); const cum = [0]; for (let q = 1; q < P.length; q++) cum.push(cum[q - 1] + Math.hypot(P[q][0] - P[q - 1][0], P[q][1] - P[q - 1][1])); return { pts: P, cum, len: cum[cum.length - 1] }; }
  planTakeoff(tr, a, b, dt) {
    const T = tr.dims, VR = T.cls === 'jet' ? 55 : T.cls === 'turboprop' ? 40 : 28, ACC = T.cls === 'jet' ? 4 : 2.5;
    // the runway: aligned with the climb-out fix b (within 400 m of its axis), else the runway beside the ground fix a (the
    // aircraft held short of it), in the direction b lies along it, or the current flow when b is abeam [inf]
    let B = this.rwyFor(b.x, b.z, b.dir, 400), sgn;
    if (B) sgn = B.sgn;
    else {
      B = this.rwyFor(a.px, a.pz, null, 150); if (!B) return this.why(1);
      const r0 = B.r, alB = (b.px - r0.origin[0]) * r0.dir[0] + (b.pz - r0.origin[1]) * r0.dir[1];
      sgn = Math.abs(alB - B.al) > 150 ? Math.sign(alB - B.al) : (this.classifier.flow.end === '10' ? 1 : -1);
    }
    const r = B.r;
    // entry: a's projection on the axis (a holding beside the runway, or already on it)
    const pa = (a.px - r.origin[0]) * r.dir[0] + (a.pz - r.origin[1]) * r.dir[1];
    const alE = clamp(pa, 0, r.length); const E = this.axisPt(r, alE);
    const dRoll = Math.min(VR * VR / (2 * ACC), sgn > 0 ? r.length - alE : alE);
    if (dRoll < 60) return this.why(2);
    const alLO = alE + sgn * dRoll, LO = this.axisPt(r, alLO);
    let taxi = null; const dA = Math.hypot(a.px - E[0], a.pz - E[1]);
    if (dA > 15) { taxi = this.net.routeXY(a.px, a.pz, a.gsm > 0.5 ? a.dir : (a.hdReal ? a.hd : null), E[0], E[1], bearR(r.dir[0] * sgn, r.dir[1] * sgn), { span: T.span, runway: true }); if (!taxi || taxi.len > 4 * dA + 150) return this.why(3); }
    const tTaxi = taxi ? taxi.len / 5 : 0, tRoll = Math.sqrt(2 * dRoll / ACC), dAir = Math.hypot(b.px - LO[0], b.pz - LO[1]), tAir = dAir / Math.max(10, (VR + b.gsm) / 2);
    const need = tTaxi + tRoll + tAir; if (need > dt * 1.15) return this.why(4);
    const segs = []; let t0 = a.t; const wait = Math.max(0, dt - need) * 1000;
    if (wait > 0) { segs.push({ kind: 'wait', t0, t1: t0 + wait, x: a.px, z: a.pz, hd: a.hdReal ? a.hd : (taxi ? bearR(taxi.pts[1][0] - taxi.pts[0][0], taxi.pts[1][1] - taxi.pts[0][1]) : a.dir) }); t0 += wait; }
    const sc = Math.min(1, dt / need);
    if (taxi) { const t1 = t0 + tTaxi * 1000 * sc; segs.push({ kind: 'path', t0, t1, R: taxi, v0: wait > 0 ? 0 : a.gsm, v1: 2 }); t0 = t1; }
    { const t1 = t0 + tRoll * 1000 * sc; segs.push({ kind: 'path', t0, t1, R: this.polyOf([E, LO]), v0: taxi ? 2 : 0, v1: VR, takeoff: true }); t0 = t1; }
    const gyLO = this.groundY(LO[0], LO[1]); const dirR = [r.dir[0] * sgn, r.dir[1] * sgn];
    segs.push({ kind: 'air', t0, t1: b.t, p0: [LO[0], gyLO, LO[1]], p1: [b.px, b.y, b.pz], v0: [dirR[0] * VR, 1.5, dirR[1] * VR], v1: [b.vx, b.vsm || 0, b.vz] });
    return { segs, kind: 'takeoff', rwy: r.id };
  }
  planLanding(tr, a, b, dt) {
    const T = tr.dims, VR = T.cls === 'jet' ? 55 : T.cls === 'turboprop' ? 40 : 28;
    // the runway: aligned with the approach fix a (within 150 m of its axis), else the runway beside the ground fix b in the
    // current flow direction (the turn to final happened in the hole: the Hermite approach segment flies it) [inf]
    let A_ = this.rwyFor(a.x, a.z, a.dir, 150), sgn;
    if (A_) sgn = A_.sgn;
    else { A_ = this.rwyFor(b.px, b.pz, null, 200); if (!A_) return this.why(5); sgn = this.classifier.flow.end === '10' ? 1 : -1; }
    const r = A_.r;
    const endName = sgn > 0 ? r.id.split('/')[0] : r.id.split('/')[1];
    const thrAl = sgn > 0 ? thrDispM(endName) : r.length - thrDispM(endName);
    let alTD = thrAl + sgn * 150; const pa = (a.px - r.origin[0]) * r.dir[0] + (a.pz - r.origin[1]) * r.dir[1];
    if ((pa - alTD) * sgn > -30) alTD = pa + sgn * 60;
    alTD = clamp(alTD, 0, r.length);
    if ((alTD - pa) * sgn < -50 && Math.hypot(a.px - r.origin[0], a.pz - r.origin[1]) < r.length + 2500) return this.why(8);   // touchdown behind the approach fix
    const vTD = Math.max(VR, Math.min(a.gsm, VR * 1.3));
    // exit: where the ground fix b projects on the runway (>= 120 m past touchdown), i.e. the roll ends where b leaves it
    const pb = (b.px - r.origin[0]) * r.dir[0] + (b.pz - r.origin[1]) * r.dir[1];
    const alX = clamp((pb - alTD) * sgn >= 120 ? pb : alTD + sgn * 120, 0, r.length);
    const TD = this.axisPt(r, alTD), X = this.axisPt(r, alX);
    let pts = [TD, X]; const dB = Math.hypot(b.px - X[0], b.pz - X[1]);
    if (dB > 8) { const taxi = this.net.routeXY(X[0], X[1], bearR(r.dir[0] * sgn, r.dir[1] * sgn), b.px, b.pz, b.gsm > 0.5 ? b.dir : (b.hdReal ? b.hd : null), { span: T.span, runway: true });
      if (!taxi || taxi.len > 4 * dB + 150) return this.why(6); pts = [TD, ...taxi.pts]; }
    const G = this.polyOf(pts);
    const dAir = Math.hypot(TD[0] - a.px, TD[1] - a.pz), tAir = dAir / Math.max(10, (a.gsm + vTD) / 2);
    const tGround = (b.t - a.t) / 1000 - tAir;
    // the ground part must be drivable: mean speed <= the touchdown speed, and not slower than 1/4 of it unless b stopped
    if (tGround < 5 || G.len / tGround > vTD) return this.why(7);
    const segs = []; const t1 = a.t + tAir * 1000;
    const dirR = [r.dir[0] * sgn, r.dir[1] * sgn];
    segs.push({ kind: 'air', t0: a.t, t1, p0: [a.px, a.y, a.pz], p1: [TD[0], this.groundY(TD[0], TD[1]), TD[1]], v0: [a.vx, a.vsm || -3, a.vz], v1: [dirR[0] * vTD, -1.0, dirR[1] * vTD] });
    segs.push({ kind: 'path', t0: t1, t1: b.t, R: G, v0: vTD, v1: b.gsm });
    return { segs, kind: 'landing', rwy: r.id };
  }
  why(k) { this.counters['planFail' + k] = (this.counters['planFail' + k] || 0) + 1; return null; }
  samplePlan(P, t, o) {
    let S = P.segs.find(q => t >= q.t0 && t <= q.t1) || (t < P.segs[0].t0 ? P.segs[0] : P.segs[P.segs.length - 1]);
    const D = Math.max(1e-3, (S.t1 - S.t0) / 1000), u = clamp((t - S.t0) / (S.t1 - S.t0 || 1), 0, 1), u2 = u * u, u3 = u2 * u;
    o.ex = 0; o.route = true; o.hd = null;
    if (S.kind === 'wait') { Object.assign(o, { x: S.x, z: S.z, y: this.groundY(S.x, S.z), vx: 0, vz: 0, vy: 0, gs: 0, ground: true, stop: true, hd: S.hd }); return o; }
    if (S.kind === 'path') {
      // constant acceleration from v0 to v1 when it covers the length, else a trapezoid-free cruise at len / D
      // arc length by a cubic Hermite with the segment's end speeds (clamped for monotonicity), as for taxi routes
      const L = S.R.len, v0 = Math.min(S.v0, 2.1 * L / D), v1 = Math.min(S.v1, 2.1 * L / D);
      const h10 = u3 - 2 * u2 + u, h01 = -2 * u3 + 3 * u2, h11 = u3 - u2;
      const s = h01 * L + h10 * D * v0 + h11 * D * v1, v = (6 * u - 6 * u2) * L / D + (3 * u2 - 4 * u + 1) * v0 + (3 * u2 - 2 * u) * v1;
      const p = polyAt(S.R, s); Object.assign(o, { x: p.x, z: p.z, y: this.groundY(p.x, p.z), vx: p.ux * v, vz: p.uz * v, vy: 0, gs: Math.abs(v), ground: true });
      return o;
    }
    const h00 = 2 * u3 - 3 * u2 + 1, h10 = u3 - 2 * u2 + u, h01 = -2 * u3 + 3 * u2, h11 = u3 - u2;
    const X = (k) => h00 * S.p0[k] + h10 * D * S.v0[k] + h01 * S.p1[k] + h11 * D * S.v1[k];
    o.x = X(0); o.y = X(1); o.z = X(2); o.vx = S.v0[0] + (S.v1[0] - S.v0[0]) * u; o.vz = S.v0[2] + (S.v1[2] - S.v0[2]) * u; o.vy = S.v0[1] + (S.v1[1] - S.v0[1]) * u;
    o.gs = Math.hypot(o.vx, o.vz); o.ground = false; o.y = Math.max(o.y, this.groundY(o.x, o.z) + 0.3);
    return o;
  }
  // does the straight / Hermite path between two ground fixes leave the pavement? (5 samples; cached per segment)
  offPaveSeg(tr, a, b) {
    const k = 'o' + a.t; if (tr.routeCache.has(k)) return tr.routeCache.get(k);
    const dt = (b.t - a.t) / 1000; let off = false; const A0 = this.endPt(tr, a), B0 = this.endPt(tr, b);
    for (let q = 1; q <= 5 && !off; q++) { const u = q / 6, u2 = u * u, u3 = u2 * u;
      const x = (2 * u3 - 3 * u2 + 1) * A0[0] + (u3 - 2 * u2 + u) * dt * a.vx + (-2 * u3 + 3 * u2) * B0[0] + (u3 - u2) * dt * b.vx;
      const z = (2 * u3 - 3 * u2 + 1) * A0[1] + (u3 - 2 * u2 + u) * dt * a.vz + (-2 * u3 + 3 * u2) * B0[1] + (u3 - u2) * dt * b.vz;
      if (!this.paved(x, z)) off = true; }
    tr.routeCache.set(k, off); return off;
  }
  routeFor(tr, a, b, dt) {
    const k = a.t; if (tr.routeCache.has(k)) return tr.routeCache.get(k);
    const span = tr.dims ? tr.dims.span : null;
    const onRwy = !!(a.strip || b.strip);
    const A0 = this.endPt(tr, a), B0 = this.endPt(tr, b);
    let R = this.net.routeXY(A0[0], A0[1], a.gsm > 0.5 ? a.dir : (a.hdReal ? a.hd : null), B0[0], B0[1], b.gsm > 0.5 ? b.dir : (b.hdReal ? b.hd : null), { span, runway: onRwy });
    const chord = Math.hypot(B0[0] - A0[0], B0[1] - A0[1]);
    if (R && R.len > ROUTE_RATIO * chord + ROUTE_EXTRA_M) { R = null; this.counters.routeFallback++; this.counters.routeTooLong = (this.counters.routeTooLong || 0) + 1; }
    else if (R && R.len / dt > TAXI_MAX_KT * KT) { R = null; this.counters.routeFallback++; this.counters.routeTooFast = (this.counters.routeTooFast || 0) + 1; }
    else if (R) this.counters.routes++;
    else { this.counters.routeFallback++; this.counters.routeNone = (this.counters.routeNone || 0) + 1; }
    tr.routeCache.set(k, R); if (tr.routeCache.size > 40) tr.routeCache.delete(tr.routeCache.keys().next().value);
    return R;
  }

  // ---------------------------------------------------------------- kinematic body
  step(tr, tDisp, dt) {
    const o = this.target(tr, tDisp, this._tgt); const D = tr.disp; const T = tr.dims;
    if (tr.physOff && o.ground) { o.x += tr.physOff[0]; o.z += tr.physOff[1]; }
    let c = tr.ctl;
    const err = c ? Math.max(Math.hypot(o.x - c.x, o.z - c.z), !o.ground && !c.ground ? Math.abs(o.y - c.y) * 1.5 : 0) : 0;
    const roll = o.ground && Math.max(o.gs || 0, c ? Math.abs(c.v) : 0) > 15;
    const errMax = o.ground ? (roll ? 300 : 60) : Math.max(150, 4 * Math.hypot(o.vx, o.vz));
    const reacq = tr.reacquire && c && err > (o.ground ? 20 : Math.max(30, 2 * Math.hypot(o.vx, o.vz)));
    if (tr.reacquire && c && !reacq && !tr.cutting) tr.reacquire = false;
    if (c && !tr.cutting && (reacq || err > errMax)) { const k = 'cut_' + (reacq ? 'gap' : 'err') + (o.ground ? '_g' : '_a'); this.counters[k] = (this.counters[k] || 0) + 1;
      if (this.debugCuts) this.debugCuts.push([tr.info.icao, o.ground, Math.round(err), Math.round(errMax), Math.round(Math.hypot(o.vx, o.vz)), Math.round(c.v), Math.round(o.y - c.y), tDisp]);
      if (D.valid && D.alpha > 0.01) tr.cutting = reacq ? "gap" : "err"; else c = null; }
    if (tr.fadeOut) { D.alpha = Math.max(0, (D.alpha ?? 0) - dt / CUT_S); tr.cutting = null; }
    if (tr.cutting) { D.alpha = Math.max(0, D.alpha - dt / CUT_S); if (D.alpha <= 0) { this.counters.cuts++; tr.cutting = null; c = null; } }
    if (o.before) c = null;       // before the first fix the hidden body is the target itself (no lag when it appears)
    if (!c) {
      tr.reacquire = false;
      const hd0 = o.hd != null ? o.hd : (o.gs > 0.5 ? bearR(o.vx, o.vz) : (tr.last && tr.last.hd != null ? tr.last.hd : 0));
      c = tr.ctl = { x: o.x, z: o.z, y: o.y, psi: wrapPi(hd0), v: o.gs, vx: o.vx, vz: o.vz, vy: o.vy || 0, ground: o.ground, w: 0, roll: 0, gear: 1 };
      D.alpha = 0;
    }
    if (!tr.cutting && !tr.fadeOut && D.alpha < 1 && !o.before && !tr.hidden) D.alpha = Math.min(1, D.alpha + dt / CUT_S);
    if (tr.hidden) D.alpha = 0;
    if (o.ground && !c.ground) { this.ctlAir(tr, T, c, o, dt, true); }
    else if (o.ground) this.ctlGround(tr, T, c, o, dt);
    else this.ctlAir(tr, T, c, o, dt, false);
    this.attitude(tr, T, c, o, dt);
    D.x = c.x; D.y = c.y; D.z = c.z; D.gs = Math.abs(c.v); D.vs = c.vy; D.ground = c.ground; D.extrap = o.ex || 0; D.valid = true; D.hdg = toDeg(c.psi);
    D.route = !!o.route;
    if (!o.stop) tr.restPose = tr.stale ? tr.restPose : null;
    else if (!tr.restPose && tr.park && tr.park.pose) tr.restPose = tr.park.pose;
    this.displayPhase(tr, tDisp);
  }
  // Ground body = TRAIL FOLLOWING (new for HWD; replaces sfo3d's pursuit of the target point): the target's positions are
  // laid down as a trail (a polyline) and the body moves ALONG it, at a speed that closes the gap to the target, braked for
  // the curvature ahead (v <= sqrt(latGround x R)) and limited by its acceleration. The body therefore never cuts a corner
  // the target path does not cut: a target routed along the taxi graph keeps the body on the pavement even when the body
  // lags. Heading = the trail tangent over +-h1 (smoothed corners), turned at <= wGround; at rest it pivots to the rest
  // pose heading (wPivot).
  trailPush(c, x, z) {
    const T = c.trail; const n = T.x.length;
    if (n && Math.hypot(x - T.x[n - 1], z - T.z[n - 1]) < 0.25) return;
    T.s.push(n ? T.s[n - 1] + Math.hypot(x - T.x[n - 1], z - T.z[n - 1]) : 0); T.x.push(x); T.z.push(z);
    // drop what lies more than 60 m behind the body
    let k = 0; while (k < T.s.length - 2 && T.s[k + 1] < c.s - 60) k++;
    if (k > 50) { T.s.splice(0, k); T.x.splice(0, k); T.z.splice(0, k); }
  }
  trailAt(T, s) {
    const S = T.s, n = S.length; if (n === 1) return [T.x[0], T.z[0]];
    if (s <= S[0]) return [T.x[0], T.z[0]]; if (s >= S[n - 1]) return [T.x[n - 1], T.z[n - 1]];
    let lo = 0, hi = n - 1; while (hi - lo > 1) { const m = (lo + hi) >> 1; if (S[m] <= s) lo = m; else hi = m; }
    const u = (s - S[lo]) / ((S[hi] - S[lo]) || 1e-9); return [T.x[lo] + (T.x[hi] - T.x[lo]) * u, T.z[lo] + (T.z[hi] - T.z[lo]) * u];
  }
  trailHdg(T, s, h1) {
    const end = T.s[T.s.length - 1], beg = T.s[0];
    const a = this.trailAt(T, Math.max(beg, s - h1)), b = this.trailAt(T, Math.min(end, s + h1));
    return Math.hypot(b[0] - a[0], b[1] - a[1]) > 0.3 ? bearR(b[0] - a[0], b[1] - a[1]) : null;
  }
  ctlGround(tr, T, c, o, dt) {
    if (!c.ground || !c.trail) { c.ground = true; c.vy = 0; c.trail = { x: [c.x], z: [c.z], s: [0] }; c.s = 0; }
    const cls = T ? T.cls : 'unknown';
    const roll = Math.max(o.gs, c.v) > 15;
    const aAcc = roll ? (LIM.rollAcc[cls] || 2.5) : LIM.taxiAcc, aDec = roll ? LIM.rollDec : LIM.taxiDec;
    { const Tq = c.trail, n = Tq.x.length; const dEnd = Math.hypot(o.x - Tq.x[n - 1], o.z - Tq.z[n - 1]);
      if (!(o.stop && dEnd < 0.6)) this.trailPush(c, o.x, o.z); }      // a resting target's centimetre jitter is not a path
    const Tr = c.trail, sEnd = Tr.s[Tr.s.length - 1], gap = Math.max(0, sEnd - c.s);
    const h1 = T ? clamp(0.25 * T.L, 1.5, 6) : 2.5;
    let vDes = o.stop ? (gap < 0.1 ? 0 : Math.min(2.5, 0.6 * gap)) : Math.max(0, o.gs + 0.5 * gap - 0.2);
    if (gap > 0.05) vDes = Math.min(vDes, Math.sqrt(2 * aDec * 0.8 * gap) + (o.stop ? 0 : o.gs));    // never overrun the target
    // curvature ahead: braking distance + 10 m, sampled every 2 m
    if (!roll && gap > 2) {
      const h0 = this.trailHdg(Tr, c.s, h1); const look = Math.min(gap, c.v * c.v / (2 * aDec) + 10);
      if (h0 != null) for (let d = 2; d <= look; d += 2) {
        const hd = this.trailHdg(Tr, c.s + d, h1); if (hd == null) continue;
        const dth = Math.abs(wrapPi(hd - h0)); if (dth < 0.05) continue;
        const R = Math.max(T ? Math.max(3, 0.35 * T.span) : 4, (d + h1) / dth);
        const vA = Math.sqrt(LIM.latGround * R); vDes = Math.min(vDes, Math.sqrt(vA * vA + 2 * aDec * Math.max(0, d - h1)));
      }
    }
    // turn first: the nose toward the path direction at the body (at rest: the rest pose heading)
    let dirT = this.trailHdg(Tr, c.s, h1); if (dirT == null) dirT = c.psi;
    let want = dirT;
    if (gap < 0.5 && c.v < 0.3) want = o.hd != null ? o.hd : dirT;
    // turn rate: <= wGround and <= latGround / v (>= 5 deg/s on a runway roll); pivot on a braked wheel at rest [inf]
    const wMax = c.v > 0.3 ? Math.min(LIM.wGround * D2R, Math.max(LIM.latGround / c.v, roll ? 5 * D2R : 0)) : LIM.wPivot * D2R;
    const w = clamp(wrapPi(want - c.psi), -wMax * dt, wMax * dt); c.psi = wrapPi(c.psi + w); c.w = w / dt;
    // a GA aircraft moves along its nose: the speed is held down while the nose and the path disagree (15-60 deg ramp), so
    // a path that turns sharply or doubles back makes it stop and pivot instead of sliding sideways or backwards [inf]
    const mis = Math.abs(wrapPi(dirT - c.psi)) / D2R, fac = gap < 0.3 ? 1 : clamp((60 - mis) / 45, 0, 1);
    if (fac < 1) vDes = Math.min(vDes, fac * Math.max(c.v, 1.5));
    c.v += clamp(vDes - c.v, -aDec * 1.5 * dt, aAcc * dt); if (c.v < 0) c.v = 0;
    // and it never slides: the advance along the path fades out between 20 and 60 deg of misalignment (it waits, braked,
    // while the nose comes round)
    const adv = mis < 20 || gap < 0.3 ? 1 : clamp((60 - mis) / 40, 0, 1);
    if (adv < 1) c.v = Math.min(c.v, Math.max(adv * c.v, 0));
    c.s = Math.min(sEnd, c.s + c.v * dt);
    // position: the trail box-filtered over +-h1 (rounds the corners of routed polylines, so the velocity turns
    // continuously; the deviation is <= h1 / 4 at a 90-deg corner)
    const hw = Math.max(0, Math.min(h1, sEnd - c.s, c.s - Tr.s[0]));   // symmetric window: never reaches past the trail end
    let px = 0, pz = 0; for (const k of [-1, -0.5, 0, 0.5, 1]) { const q = this.trailAt(Tr, c.s + k * hw); px += q[0]; pz += q[1]; }
    const p = [px / 5, pz / 5]; const ox = c.x, oz = c.z; c.x = p[0]; c.z = p[1];
    const f2 = hvR(c.psi); c.vx = (c.x - ox) / dt; c.vz = (c.z - oz) / dt; if (!(Math.abs(c.vx) + Math.abs(c.vz) > 0)) { c.vx = f2[0] * c.v; c.vz = f2[1] * c.v; }
    c.y = this.groundY(c.x, c.z);
  }
  ctlAir(tr, T, c, o, dt, landing) {
    if (c.ground) { c.ground = false; c.trail = null; const f = hvR(c.psi); c.vx = f[0] * c.v; c.vz = f[1] * c.v; }
    const om = 0.7, ze = 1.0; const gy0 = this.groundY(c.x, c.z);
    let ax = om * om * (o.x - c.x) + 2 * ze * om * (o.vx - c.vx), az = om * om * (o.z - c.z) + 2 * ze * om * (o.vz - c.vz);
    const am = Math.hypot(ax, az), aMax = LIM.airAcc; if (am > aMax) { ax *= aMax / am; az *= aMax / am; }
    c.vx += ax * dt; c.vz += az * dt;
    const gy = this.groundY(c.x, c.z);
    const ty = landing ? gy : o.y;
    let ay = om * om * (ty - c.y) + 2 * ze * om * ((landing ? Math.min(o.vy, -0.5) : o.vy) - c.vy); ay = clamp(ay, -LIM.airVAcc, LIM.airVAcc);
    const vsMax = LIM.airVs[T && T.cls] || LIM.airVs.default;
    c.vy = clamp(c.vy + ay * dt, -vsMax, vsMax);
    c.x += c.vx * dt; c.z += c.vz * dt; c.y += c.vy * dt;
    const sp = Math.hypot(c.vx, c.vz); c.v = sp;
    const heli = T && T.cls === 'heli';
    let want = sp > (heli ? 5 : 2) ? bearR(c.vx, c.vz) : (o.hd != null ? o.hd : c.psi);
    if (!heli && (landing || c.y - gy0 < 15) && o.gs > 5) want = bearR(o.vx, o.vz);   // de-crab / align before the wheels touch
    if (heli && o.hd != null && sp < 15) want = o.hd;
    // heading rate: a fixed-wing turns its nose with its track (coordinated flight): <= LIM.airAcc / speed, >= 3 deg/s
    const wMax = heli ? 30 * D2R : Math.max(3 * D2R, Math.min(20 * D2R, LIM.airAcc / Math.max(sp, 1)));
    const w = clamp(wrapPi(want - c.psi), -wMax * dt, wMax * dt); c.psi = wrapPi(c.psi + w); c.w = w / dt;
    if (c.y <= gy + 0.05 && (landing || o.ground)) { c.y = gy; c.vy = 0; c.ground = true; }
    if (c.y < gy) c.y = gy;
  }
  attitude(tr, T, c, o, dt) {
    const D = tr.disp; const heli = T && T.cls === 'heli';
    let rollT = 0, pitchT = 0;
    if (!c.ground) {
      rollT = clamp(Math.atan(c.v * (c.w || 0) / GRAV), -LIM.bankMax * D2R, LIM.bankMax * D2R);
      pitchT = heli ? clamp(-(c.v - 10) * 0.004, -0.1, 0.06) : clamp(Math.atan2(c.vy, Math.max(c.v, 20)) + 2 * D2R, -0.25, 0.3);
    }
    const k = 1 - Math.exp(-dt / 0.8); D.roll += (rollT - D.roll) * k; D.pitch += (pitchT - D.pitch) * k;
    const hAgl = (c.y - this.groundY(c.x, c.z)) / FT;
    const up = T && T.retract && !c.ground && hAgl > 300 ? 0 : 1;
    D.gear += clamp(up - D.gear, -dt / 6, dt / 6);
    D.flaps = !c.ground && hAgl < 1000 && (tr.phase === 'final' || tr.phase === 'base') ? 1 : 0;
  }
  displayPhase(tr, t) {
    const F = tr.fx; let i = F.length - 1; while (i > 0 && F[i].t > t) i--;
    let f = F[i];
    let ph = tr.vehicle ? 'vehicle' : (f && f.ph) || 'unknown', pi = (f && f.pi) || {};
    if (tr.stale && tr.park) { ph = tr.park.inside ? 'hangared' : 'parked'; pi = { src: tr.park.inside ? 'inf' : 'obs', rule: tr.park.inside ? 'signal ended at a hangar' : 'parked, no signal' }; }
    if (tr.scope === 'overflight' && PHASES[ph] && PHASES[ph].airborne && !['heli_hover_taxi', 'heli_hover'].includes(ph)) ph = 'overflight';
    if (ph !== tr.phase) { tr.phase = ph; tr._since = f ? f.t : t; }
    tr.phaseInfo = { label: (PHASES[ph] || PHASES.unknown).label, rwy: pi.rwy || null, leg: pi.leg || null, src: pi.src || null, rule: pi.rule || null, since: tr._since || t,
      provisional: !!pi.provisional, tower: towerStatus(t) };
  }

  // ---------------------------------------------------------------- persistence (D1: type only, no registration / callsign)
  saveParkedSoon() { if (!this.persist) return; clearTimeout(this._saveT); this._saveT = setTimeout(() => this.saveParked(), 2000); }
  saveParked() {
    if (!this.persist || typeof localStorage === 'undefined') return;
    try {
      const out = [];
      for (const tr of this.tracks.values()) if (tr.park && tr.park.pose && (tr.stale || tr.phase === 'parked')) out.push({ k: tr.key, t: tr.info.icao || null, c: tr.info.category || null, m: tr.ident && tr.ident.masked ? 1 : 0,
        p: tr.park, f: tr.lastFixT, r: tr.lastRecv });
      localStorage.setItem(STORE_KEY, JSON.stringify({ v: 1, saved: Date.now(), parked: out }));
    } catch (e) { }
  }
  loadParked() {
    if (typeof localStorage === 'undefined') return;
    try {
      const j = JSON.parse(localStorage.getItem(STORE_KEY) || 'null'); if (!j || j.v !== 1) return;
      const now = Date.now();
      for (const q of j.parked || []) {
        if (now - q.r > PARK_KEEP_MS || this.tracks.has(q.k) || !q.p || !q.p.pose) continue;
        const tr = new Track(q.k); tr.info = { icao: q.t, category: q.c, masked: !!q.m }; tr.ident = identity(tr.info, q.k, q.m ? { masked: true } : null); tr.dims = gaDims(q.t, q.c);
        tr.stale = true; tr.park = q.p; tr.hidden = !!q.p.inside; tr.lastFixT = q.f; tr.lastRecv = q.r; tr.firstSeen = q.r; tr.restPose = q.p.pose;
        tr.fx.push({ t: q.f, x: q.p.pose.x, z: q.p.pose.z, px: q.p.pose.x, pz: q.p.pose.z, y: this.groundY(q.p.pose.x, q.p.pose.z), ground: true, g: true, gs: 0, gsm: 0, vx: 0, vz: 0, dir: 0, hd: (q.p.pose.hdg || 0) * D2R, hdReal: false, ph: 'parked', pi: { src: 'obs', rule: 'remembered (this browser)' } });
        tr.scope = 'hwd'; this.tracks.set(q.k, tr);
        if (this.parking && q.p.spotId) { const s = this.parking.byId.get(q.p.spotId); if (s) this.parking.occupy(q.k, s); }
      }
    } catch (e) { }
  }
}

// ---------------------------------------------------------------- labels for the UI (P4)
export function phaseLabel(tr, now = Date.now()) {
  const P = tr.phaseInfo || {}; let s = P.label || 'Unknown';
  if (P.rwy && /^(final|base|downwind|crosswind|upwind|initial_climb|takeoff_roll|landing_roll|touch_and_go|stop_and_go|go_around|low_pass|line_up|runway_taxi)$/.test(tr.phase)) s += ' ' + P.rwy;
  if ((tr.phase === 'parked' || tr.phase === 'hangared') && tr.park && tr.park.zone) s += ' · ' + tr.park.zone;
  if (P.provisional) s += ' (provisional)';
  if (P.tower === 'closed' && tr.scope === 'hwd' && PHASES[tr.phase] && PHASES[tr.phase].group !== 'ground') s += ' · tower closed (CTAF)';
  return s;
}
export function category(tr) {
  if (tr.vehicle) return 'vehicle';
  if (tr.dims && tr.dims.cls === 'heli') return tr.scope === 'overflight' ? 'overflight' : 'heli';
  if (tr.scope === 'overflight') return 'overflight';
  if (tr.scope === 'hwd') return tr.disp && tr.disp.ground ? 'hwd_ground' : 'hwd_air';
  return 'unknown';
}
export { PHASES };
