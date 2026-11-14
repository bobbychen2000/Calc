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
import { pavedWith, bodyOf, overlaps } from './ground.js';
import { polyOf, polyAt, filletPath, profilePath, profAt, geoHermite, hermiteMaxCurv, turnFlight } from './motion.js';

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
const STALL_CATCH_S = 60;   // s of a stalled frame caught up by sub-stepping (review round 3) [inf: > the 28-s stall measured]
const STALE_AIR_MS = 60000, MOVING_LOST_MS = 45000, VEH_KEEP_MS = 120000, PARK_KEEP_MS = 8 * 3600e3;   // sfo3d values
// fix round 2 (review round 2, finding 2): a ground aircraft whose signal ends is KEPT where it was last placed (stale,
// 'No signal', inferred) - also on a taxiway, a taxilane or a run-up pad - and fades out only after this long without a
// report [inf]; it used to fade out at once off aprons and reappear minutes later where it had stood
const LOST_KEEP_MS = 30 * 60000;
// report latency: the relay sends a position up to seen_pos old (adsb.lol / readsb README-json.md); a ground track is
// declared silent only when the display is this far past its newest fix AND no report arrived for MOVING_LOST_MS plus
// this allowance [inf: the latencies seen in the recordings reach ~25 s]
const LATENCY_ALLOW_MS = 30000;
const REACQ_PARK_M = 15;                      // a parked aircraft heard again within this of its pose has not moved (sfo3d)
const VIEW_NM = 5, VIEW_FT = 3000, VIEW_HYST = 1.1;     // D6 display window, with 10 % hysteresis [inf]
const PAVED_NEAR_M = 8;                       // m: GNSS error of a ground fix (NACp 9-10 EPU < 10-30 m [verify]) [inf]
const SIM_NM = 7;                             // bodies are simulated within this (a track entering the view is already moving)
// fix round 1 (docs/phase2_run.md section 6) [inf, all design values]:
const TAXI_V = 10.3;                          // m/s (20 kt): speed cap of a planned taxi path (GA taxi ~5-20 kt)
const TAXI_V_FAST = 12.9;                     // m/s (25 kt): the cap tried when a hole cannot be taxied at TAXI_V
const TAXI_TYP = 4.5;                         // m/s (~9 kt): a planned path is not driven slower than this; spare time is a stop
const FILLET_M = 20;                          // m: corner radius of a planned taxi path where the pavement allows (halved down to 1 m; runway exits are paved for ~25-30 m radii) [inf]
const CATCH_MS = 3;                           // m/s: a lagging ground body may run this much faster than its target, no more
const TAXI_BODY_MAX = 12.9;                   // m/s (25 kt): a taxiing body (not on a roll) never runs faster than this
const ERR_G = 150, ERR_ROLL = 400, ERR_AIR = 250, ERR_AIR_V = 8;   // m, m, m, s: re-placement thresholds (air: max(250, 8 s x v))
const JUMP_G_M = 10;                          // m: a ground target that moves farther than this in one step jumped (re-placed)
const AIR_HIDE_S = 20;                        // s: an airborne track dead-reckoned longer than this fades out (live mode)
const GROUND_VIEW_M = 3000;                   // m: ground bodies farther than this from the ARP are not drawn (no pavement model: OAK)
const SLOW_FRAC = 0.45;                       // a fixed-wing fix below 0.45 x its ACD approach speed is on the ground [inf]
const HELD_H_FT = 250;                        // ft: one airborne-by-altitude fix of a slow aircraft after a ground fix is held on the ground
// type speeds [inf]: lift-off groundspeed VLOF = 0.85 x the FAA ACD approach speed (Approach_Speed_knot, the AAC speed,
// defined as 1.3 x the stall speed in landing configuration [recalled, verify]; so VLOF ~ 1.1 Vso); touchdown 0.95 x;
// the slowest drawn airborne speed 0.7 x (~0.9 Vso in still air - a headwind lowers the groundspeed). Class defaults (kt)
// where the ACD has no row.
const VAPP_DEF = { jet: 120, turboprop: 85, twin: 80, default: 62 };
// take-off performance (review round 3, M3: a reconstructed take-off rolls at a type-appropriate acceleration - the class
// table of fix round 2 (2.5-4.5 m/s2) drew a 175-m 'jet' roll for an SF50 whose AFM ground roll is 2,036 ft). The drawn roll
// accelerates at the constant mean rate a = VR^2 / (2 x roll) that gives the ground roll below at the rotation speed VR
// (sea level, ISA, calm, maximum weight; the field is at 52 ft). climb: m/s, the initial climb of a reconstructed take-off
// (never steeper than the class vertical-speed limit LIM.airVs). Each row says its basis.
const PERF_CLS = {
  single_hw: { roll: 290, climb: 3.7, basis: 'C172S POH: 960 ft ground roll (SL, 15 C, 2,550 lb), 730 ft/min climb [recalled, not re-read: inf]' },
  single_lw: { roll: 300, climb: 3.5, basis: 'PA-28 / SR2x singles ~1,000 ft ground roll [inf]' },
  twin: { roll: 340, climb: 6.0, basis: 'light piston twins ~1,100 ft ground roll [inf]' },
  turboprop: { roll: 450, climb: 7.0, basis: 'single turboprops (PC-12 / TBM class) ~1,500 ft ground roll [inf: no POH read]' },
  turboprop_twin: { roll: 600, climb: 8.0, basis: 'King Air 200 class ~2,000 ft ground roll [inf]' },
  jet: { roll: 750, climb: 10, basis: 'light jets (Citation / Phenom 100 class) ~2,500 ft ground roll [inf]' },
  jet_biz: { roll: 1000, climb: 12, basis: 'business jets ~3,300 ft ground roll [inf]' },
  jet_airliner: { roll: 1700, climb: 12, basis: 'airliners [inf]' },
  heli: { roll: 0, climb: 4, basis: 'not used (helicopters lift off vertically)' },
  other: { roll: 250, climb: 3.0, basis: 'gliders / ultralights / unknown: single-like [inf]' },
};
const PERF_TYPE = {
  SF50: { roll: 621, vr_kt: 85, climb: 9.6, basis: 'Cirrus SF50 AFM P/N 31452-001 Rev 4 (tools/models/sf50/SF50_FACTS.md S5): take-off ground roll 2,036 ft at SL ISA, 6,000 lb, flaps 50 % (sec. 5; 1,483-2,231 ft over 5,000-6,000 lb and -20 to +20 C); normal take-off "VR ... 80-90 KIAS" (sec. 4; 85 used); take-off rate of climb 1,892 ft/min at SL 10 C 6,000 lb (sec. 5) [obs; the mid VR and the weight are inf]' },
};
const SPD = new WeakMap();
function speedsOf(T) {
  if (T && SPD.has(T)) return SPD.get(T);
  const va = (T && T.vapp_kt) || VAPP_DEF[T && T.cls] || VAPP_DEF.default;
  const ty = T && PERF_TYPE[T.icao || T.type || ''];
  const pc = !T ? PERF_CLS.other : T.cls === 'jet' ? (T.sub === 'biz' ? PERF_CLS.jet_biz : T.sub === 'airliner' ? PERF_CLS.jet_airliner : PERF_CLS.jet) : T.cls === 'turboprop' && T.sub === 'twin' ? PERF_CLS.turboprop_twin : PERF_CLS[T.cls] || PERF_CLS.other;
  const vr = ty && ty.vr_kt ? ty.vr_kt * KT : 0.85 * va * KT, roll = ty ? ty.roll : pc.roll;
  const S = { vapp: va * KT, vr, vtd: Math.max(0.95 * va * KT, vr * 1.05), vmin: 0.7 * va * KT, src: T && T.vapp_kt ? 'FAA ACD approach speed x factor [inf]' : 'class default [inf]',
    roll, accTO: roll > 0 ? vr * vr / (2 * roll) : 2, climb: ty ? ty.climb : pc.climb, perf: (ty || pc).basis };
  if (T) SPD.set(T, S);
  return S;
}
export { speedsOf, PERF_CLS, PERF_TYPE };
export const STORE_KEY = 'hwdlive.parked.v1';
// kinematic limits [inf: typical GA handling, not measured; tools/traffic reports what the drawn motion does]
const LIM = {
  taxiAcc: 1.2, taxiDec: 2.0, latGround: 2.0, wGround: 25, wPivot: 20,      // m/s2, m/s2, m/s2 lateral, deg/s, deg/s at rest
  rollAcc: { single_hw: 2.5, single_lw: 2.5, twin: 3.0, turboprop: 3.5, jet: 4.5, heli: 2.0, glider: 2.0, ultralight: 2.0, unknown: 2.5 },
  rollDec: 3.5, airAcc: 4.5, airAccGA: 6.0,   // airAccGA: lateral 6 m/s2 = 31 deg bank, GA pattern turns (fix round 1) [inf]
  airAccMax: 9.8,                             // 45 deg bank: only where the data path itself turns that hard (fix round 2) [inf]
  airVAcc: 2.5, airVs: { jet: 25, turboprop: 15, default: 12 }, bankMax: 35,   // vs m/s: 4,900 / 2,950 / 2,360 ft/min
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
      return { i, a: l.a, b: l.b, pts, cum, len: cum[cum.length - 1], air: !!l.air, runway: l.runway || null, maxSpan: way.max_span_m ?? null, way: l.way, alongRwy: way.kind === 'runway' };
    });
    this.adj = this.nodes.map(() => []); for (const L of this.links) { this.adj[L.a].push(L); this.adj[L.b].push(L); }
    this.holds = G.holds || [];
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
  // out-and-back spurs of a route (fix round 2): where the graph's nodes at a crossing are offset along a runway or a
  // taxiway, the shortest path runs 30-45 m past the crossing and turns round (a 180-deg pivot, ~9 s of dwell); a stretch
  // that returns within 15 m of where it left, after more than 2.5 x that distance + 20 m, is cut short when the shortcut
  // is on the taxi pavement [inf]
  despur(P) {
    // micro-reversals: a vertex where the route doubles back (> 150 deg) next to a segment shorter than 8 m (two link ends a
    // metre apart) would be a stop-and-pivot in the speed profile - the vertex is dropped
    for (let k = 1; k < P.length - 1; k++) {
      const a = P[k - 1], b = P[k], c = P[k + 1], l1 = Math.hypot(b[0] - a[0], b[1] - a[1]), l2 = Math.hypot(c[0] - b[0], c[1] - b[1]);
      if (Math.min(l1, l2) < 8 && Math.abs(wrapPi(bearR(c[0] - b[0], c[1] - b[1]) - bearR(b[0] - a[0], b[1] - a[1]))) > 150 * D2R) { P.splice(k, 1); k = Math.max(0, k - 2); this.spurs = (this.spurs || 0) + 1; }
    }
    for (let i = 0; i < P.length - 2; i++) {
      let cum = 0, cut = -1;
      for (let j = i + 1; j < P.length && cum < 160; j++) { cum += Math.hypot(P[j][0] - P[j - 1][0], P[j][1] - P[j - 1][1]); const d = Math.hypot(P[j][0] - P[i][0], P[j][1] - P[i][1]);
        if (j > i + 1 && d < 15 && cum > 2.5 * d + 20) cut = j; }
      if (cut < 0) continue;
      const A = P[i], B = P[cut], L = Math.hypot(B[0] - A[0], B[1] - A[1]); let ok = true;
      for (let q = 1; q < Math.max(2, Math.ceil(L / 2)); q++) { const u = q / Math.max(2, Math.ceil(L / 2)); if (!this.paved(A[0] + (B[0] - A[0]) * u, A[1] + (B[1] - A[1]) * u)) { ok = false; break; } }
      if (ok) { P.splice(i + 1, cut - i - 1); this.spurs = (this.spurs || 0) + 1; }
    }
    return P;
  }
  // ---- runway exits (review round 3, M1 / M2): graph nodes on runway r's centreline (taxigraph node kind 'runway') with a
  // link that is not a runway link - the junctions of the exit / crossing taxiways - as { n, al, x, z, out: [links] } by along
  // position; and the path from such a node out along one of its links until an aircraft of length Lm standing there is clear
  // of the runway: its tail past the runway holding position (the hold bars of data/hwd_taxigraph.json on runway r: median
  // centreline distance 39 m for 10L/28R, 61 m for 10R/28L [obs]), 38 m where r has none [inf: AC 150/5300-13B Table 3-2,
  // 125 ft for small aircraft - recalled]
  exitsOf(r) {
    this._ex = this._ex || new Map(); if (this._ex.has(r.id)) return this._ex.get(r.id);
    const out = [];
    this.nodes.forEach((N, n) => {
      if (N.runway && N.runway !== r.id) return;
      const px = N.x - r.origin[0], pz = N.z - r.origin[1], al = px * r.dir[0] + pz * r.dir[1], ac = px * r.right[0] + pz * r.right[1];
      if (Math.abs(ac) > Math.min(6, r.halfWidth) || al < -5 || al > r.length + 5) return;
      // (links of taxiway / connector ways, also where they lie on the runway pavement - the graph flags those 'runway')
      const ls = this.adj[n].filter(L => !L.air && !L.alongRwy); if (ls.length) out.push({ n, al, x: N.x, z: N.z, out: ls });
    });
    out.sort((p, q) => p.al - q.al); this._ex.set(r.id, out); return out;
  }
  holdDist(r) { if (!this._hd) this._hd = new Map(); if (!this._hd.has(r.id)) { const H = (this.holds || []).filter(h => h.runway === r.id).map(h => h.cl_dist_m).filter(Number.isFinite).sort((p, q) => p - q); this._hd.set(r.id, H.length ? H[H.length >> 1] : 38); } return this._hd.get(r.id); }
  exitPath(r, ex, L, Lm) {
    const acOf = (p) => Math.abs((p[0] - r.origin[0]) * r.right[0] + (p[1] - r.origin[1]) * r.right[1]);
    const clear = this.holdDist(r) + 0.6 * Lm;
    const pts = [[ex.x, ex.z]]; let n = ex.n, link = L, seen = new Set([n]);
    for (let k = 0; k < 6 && link; k++) {
      const fwd = link.a === n, P = fwd ? link.pts : link.pts.slice().reverse();
      for (let q = 1; q < P.length; q++) {
        const A = pts[pts.length - 1], B = P[q], dA = acOf(A), dB = acOf(B);
        if (dB >= clear) { const u = dB > dA ? clamp((clear - dA) / (dB - dA), 0, 1) : 1; pts.push([A[0] + (B[0] - A[0]) * u, A[1] + (B[1] - A[1]) * u]); return pts; }
        pts.push(B);
      }
      n = fwd ? link.b : link.a; if (seen.has(n)) return null; seen.add(n);
      // on: the link from the far node that leads furthest from the runway (not a runway link)
      let best = null, bd = -1; for (const L2 of this.adj[n]) { if (L2 === link || L2.air || L2.alongRwy) continue; const far = L2.a === n ? L2.pts[L2.pts.length - 1] : L2.pts[0]; const d = acOf(far); if (d > bd) { bd = d; best = L2; } }
      if (!best || bd <= acOf(pts[pts.length - 1]) + 1) return pts.length > 1 && acOf(pts[pts.length - 1]) > r.halfWidth + 10 ? pts : null;
      link = best;
    }
    return null;
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
        // runways only when needed [inf]; (review round 3, M2) opt.noRunway: never along a runway (x 8 - crossing one is a taxiway
        // link through its centreline node, not a runway link)
        const m = L.a === n ? L.b : L.a, nd = d + L.len * (L.alongRwy && opt.noRunway ? 8 : 1) + (L.runway && !opt.runway ? 40 : 0) + (opt.block ? opt.block(L) : 0);
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
  // a taxi route from graph node n to the world position (x1, z1) (review round 3: exit routes) -> { pts, cum, len } | null
  routeFrom(n, x1, z1, h1, opt = {}) {
    const B = this.projLinks(x1, z1, h1, opt).filter(b => b.d <= 40); if (!B.length) return null; let best = null;
    for (const b of B.slice(0, 2)) {
      const goals = new Map([[b.L.a, b.s], [b.L.b, b.L.len - b.s]]), g = this.dijkstra([[n, 0]], goals, opt); if (!g) continue;
      const tail = this.sub(b.L, g.end === b.L.a ? 0 : b.L.len, b.s), pts = g.pts.concat(tail.slice(1), [[x1, z1]]);
      if (!best || g.len + b.d < best.c) best = { pts, c: g.len + b.d };
    }
    if (!best) return null;
    const P = [best.pts[0]]; for (const p of best.pts.slice(1)) if (Math.hypot(p[0] - P[P.length - 1][0], p[1] - P[P.length - 1][1]) > 0.05) P.push(p);
    this.despur(P); const cum = [0]; for (let k = 1; k < P.length; k++) cum.push(cum[k - 1] + Math.hypot(P[k][0] - P[k - 1][0], P[k][1] - P[k - 1][1]));
    return { pts: P, cum, len: cum[cum.length - 1] };
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
      if (a.d > (opt.far ? 60 : 40) || b.d > (opt.far ? 60 : 40)) continue;
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
      // (review round 3: and the obstacle penalty of the start / end links themselves, opt.block)
      let cost = r.len + a.d + b.d + (opt.block ? opt.block(a.L) + (b.L !== a.L ? opt.block(b.L) : 0) : 0);
      // (fix round 2: the direction over the first / last 15 m of the route, not of its first 1-2-m segment - a route that
      // stepped forward 1 m and then doubled back escaped the penalty and a jet turned round instead of taxiing to the end)
      const along = (P, k0, step, dist) => { let d = 0, k = k0; while (k + step >= 0 && k + step < P.length && d < dist) { d += Math.hypot(P[k + step][0] - P[k][0], P[k + step][1] - P[k][1]); k += step; } return k; };
      const k15 = pts.length > 2 ? along(pts, 1, 1, 15) : 1, d0 = pts.length > 2 && k15 !== 1 ? bearR(pts[k15][0] - pts[1][0], pts[k15][1] - pts[1][1]) : null;
      if (h0 != null && d0 != null && Math.abs(wrapPi(d0 - h0)) > 100 * D2R) cost += 60 + 40 * (opt.v0 || 0);   // a moving aircraft does not turn round at once (fix round 1: +40 m per m/s)
      const m = pts.length, kE = m > 2 ? along(pts, m - 2, -1, 15) : m - 2, d1 = m > 2 && kE !== m - 2 ? bearR(pts[m - 2][0] - pts[kE][0], pts[m - 2][1] - pts[kE][1]) : null;
      if (h1 != null && d1 != null && (opt.v1 || 0) > 1 && Math.abs(wrapPi(d1 - h1)) > 100 * D2R) cost += 60 + 40 * (opt.v1 || 0);
      if (!best || cost < best.cost) best = { pts, len: r.len + a.d + b.d, cost };
    }
    if (!best) { this.routeFails++; return null; }
    // clean: drop consecutive duplicates; cumulative length
    const P = [best.pts[0]]; for (const p of best.pts.slice(1)) if (Math.hypot(p[0] - P[P.length - 1][0], p[1] - P[P.length - 1][1]) > 0.05) P.push(p);
    this.despur(P);
    const cum = [0]; for (let k = 1; k < P.length; k++) cum.push(cum[k - 1] + Math.hypot(P[k][0] - P[k - 1][0], P[k][1] - P[k - 1][1]));
    this.routes++;
    return { pts: P, cum, len: cum[cum.length - 1] };
  }
}

// a flight path re-timed (review round 3): the path of C (anything with .at(t) over [0, D]) flown in D seconds starting at
// speed s0, accelerating at <= acc to one cruise speed vc that makes the length fit, and - when s1 is given - blending linearly
// to s1 over the last <= 6 s (no speed step where the next segment starts) -> { at(t), len, vc }
function retimePath(C, D, s0, acc, s1 = null) {
  const N = 96, pts = []; for (let j = 0; j <= N; j++) { const q = C.at(D * j / N); pts.push([q.x, q.z]); }
  const R = polyOf(pts), L = R.len, t2 = s1 != null ? Math.min(0.25 * D, 6) : 0;
  const lenOf = (vc) => { const t1 = Math.min(D - t2, Math.abs(vc - s0) / acc); return [(s0 + vc) / 2 * t1 + vc * (D - t1 - t2) + (s1 != null ? (vc + s1) / 2 * t2 : 0), t1]; };
  let vc = L / D; for (let it = 0; it < 50; it++) { const [len, t1] = lenOf(vc); vc += (L - len) / Math.max(1, D - 0.5 * t1 - 0.5 * t2); }
  const [Ltot, t1] = lenOf(vc), a1 = t1 > 1e-6 ? (vc - s0) / t1 : 0, a2 = t2 > 1e-6 ? ((s1 ?? vc) - vc) / t2 : 0, tB = D - t2;
  const at = (t) => { const tt = clamp(t, 0, D); let sA, v;
    if (tt <= t1) { sA = s0 * tt + 0.5 * a1 * tt * tt; v = s0 + a1 * tt; }
    else if (tt <= tB) { sA = (s0 + vc) / 2 * t1 + vc * (tt - t1); v = vc; }
    else { const u = tt - tB; sA = (s0 + vc) / 2 * t1 + vc * (tB - t1) + vc * u + 0.5 * a2 * u * u; v = vc + a2 * u; }
    const p = polyAt(R, sA * L / Math.max(1e-6, Ltot)); return { x: p.x, z: p.z, vx: p.ux * v, vz: p.uz * v, s: sA, v }; };
  return { at, len: L, vc, dubins: C.dubins, k: C.k };
}

// a landing roll of length d from v0 to v1 that must take T s, longer than its natural 2 d / (v0 + v1) (review round 3):
// a full stop (aUp = 0) brakes to v1 early - at the deceleration a (<= aMax) that makes the time fit - and rolls on at v1;
// a touch-and-go (aUp > 0) brakes at aMax to a lower vm, rolls at vm and accelerates at aUp back to v1 -> [{ s0, v0, acc,
// dt }] | null when no such roll fits
function rollParts(d, v0, v1, T, aUp, aMax) {
  if (aUp > 0) {
    const build = (vm) => { const a = aMax, tA = Math.max(0, (v0 - vm) / a), sA = (v0 + vm) / 2 * tA, tC = Math.max(0, (v1 - vm) / aUp), sC = (vm + v1) / 2 * tC, sB = d - sA - sC; if (sB < 0) return null;
      return { T: tA + sB / Math.max(0.1, vm) + tC, parts: [{ s0: 0, v0, acc: -a, dt: tA }, { s0: sA, v0: vm, acc: 0, dt: sB / Math.max(0.1, vm) }, { s0: sA + sB, v0: vm, acc: aUp, dt: tC }] }; };
    let lo = 2.5, hi = Math.min(v0, v1), best = null;
    for (let it = 0; it < 40; it++) { const m = (lo + hi) / 2, B = build(m); if (!B || B.T > T) lo = m; else { hi = m; best = B; } }
    return best ? best.parts.filter(q => q.dt > 0.01) : null;
  }
  if (!(v1 > 0.5) || v1 >= v0) return null;
  // (review round 3) less time than one constant deceleration over d takes: hold v0, then brake to v1 (it used to return that
  // slower deceleration anyway - the roll ended ~50 m short of the fix and the body jumped)
  if (T < 2 * d / (v0 + v1)) {
    const build2 = (a) => { const tB = (v0 - v1) / a, sB = (v0 + v1) / 2 * tB, sA = d - sB; if (sA < 0) return null; return { T: sA / v0 + tB, parts: [{ s0: 0, v0, acc: 0, dt: sA / v0 }, { s0: sA, v0, acc: -a, dt: tB }] }; };
    const Bx = build2(aMax); if (!Bx || Bx.T > T) return null;          // even the latest, hardest braking takes longer
    let lo = 0.05, hi = aMax; for (let it = 0; it < 40; it++) { const m = (lo + hi) / 2, B = build2(m); if (!B || B.T > T) lo = m; else hi = m; }
    const B = build2(hi); return B ? B.parts.filter(q => q.dt > 0.01) : null;
  }
  const build = (a) => { const tA = (v0 - v1) / a, sA = (v0 + v1) / 2 * tA, sB = d - sA; if (sB < 0) return null; return { T: tA + sB / v1, parts: [{ s0: 0, v0, acc: -a, dt: tA }, { s0: sA, v0: v1, acc: 0, dt: sB / v1 }] }; };
  const Bm = build(aMax); if (!Bm || Bm.T < T) return null;           // even the hardest braking cannot take that long
  let lo = 0.05, hi = aMax; for (let it = 0; it < 40; it++) { const m = (lo + hi) / 2, B = build(m); if (!B || B.T < T) lo = m; else hi = m; }
  const B = build(hi); return B && Math.abs(B.T - T) < 0.5 ? B.parts.filter(q => q.dt > 0.01) : null;
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
    this.classifier.parkable = (x, z, heli) => this.parkablePlace(x, z, heli);
    this.delay = delay; this.delayTarget = delay; this.adaptDelay = true; this.ages = [];
    this.offset = null; this.dataNow = 0; this.version = 0; this._tgt = {};
    this.counters = { reports: 0, rejects: 0, altRejects: 0, reacquire: 0, cuts: 0, routes: 0, routeFallback: 0, parked: 0, hangared: 0, removed: 0, vehicles: 0 };
    this.groundY = site ? (x, z) => site.groundY(x, z) : () => 11.4;
    this.paved = pavedWith(site);
    if (persist) this.loadParked();
  }
  displayTime(now) { return now - this.delay; }
  // the type speeds of one track (review round 3): the class / ACD speeds (speedsOf), scaled down when the track has been
  // OBSERVED flying slower than the minimum drawn airborne speed (a groundspeed into a headwind, or an ACD approach speed that
  // does not fit the type: a TF19 reported 48 kt climbing out against an ACD-derived 49-kt minimum and a 59.5-kt VR) - the
  // drawn body then neither outruns the data nor lifts off later than the aircraft did [inf]
  spd(tr) {
    const S = speedsOf(tr && tr.dims); if (!tr || !(tr.vAirMin > 0) || tr.vAirMin >= 1.05 * S.vmin) return S;
    const k = Math.max(0.6, tr.vAirMin / (1.05 * S.vmin)), kq = Math.round(k * 50) / 50;
    if (tr._spd && tr._spdK === kq) return tr._spd;
    tr._spdK = kq; tr._spd = { ...S, vapp: S.vapp * kq, vr: S.vr * kq, vtd: S.vtd * kq, vmin: S.vmin * kq, accTO: S.accTO * kq * kq, src: S.src + '; scaled x' + kq.toFixed(2) + ' to the observed airborne speeds [inf]' };
    return tr._spd;
  }
  pavedNear(x, z, r = PAVED_NEAR_M) { const P = this.paved; if (!this.site) return true; if (P(x, z)) return true; for (const [dx, dz] of [[r, 0], [-r, 0], [0, r], [0, -r]]) if (P(x + dx, z + dz)) return true; return false; }
  // replay / pack: display lookahead_s behind, fixed (fork map 2.7)
  setLookahead(s) { this.delay = this.delayTarget = s * 1000; this.adaptDelay = false; }
  event(e) { if (e.key && (e.kind === 'touch_and_go' || e.kind === 'low_pass' || e.type === 'stop_and_go')) { const q = this.tracks.get(e.key); if (q) q.patternT = Math.max(q.patternT || 0, e.t); }
    this.events.push(e); if (this.events.length > 2000) this.events.splice(0, 500); if (this.onEvent) try { this.onEvent(e); } catch (err) { } }

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
      let anc = null;
      if (!tr) { tr = new Track(a.hex); tr.firstSeen = recvNow; this.tracks.set(a.hex, tr); if (this.restoredN && a.ground) this.reconcileRestored(tr, a, x, z); }
      else if (!tr.last || tf > tr.last.t + 20) {
        // a NEW report while the display is already past the newest ground fix (extrapolated stop, or a stale track): the body
        // moves on from where its target is now - a continuation anchor, the start of the next segment (fix round 2; it used to
        // be re-placed with a fade, or faded out at the signal loss and faded in at the new fix)
        anc = this.anchorAt(tr, recvNow, tf);
        if (tr.stale) {
          const P = tr.stalePose || tr.restPose; const gap = recvNow - tr.lastRecv;
          const same = P && a.ground && (a.gs ?? 0) < 3 && Math.hypot(x - P.x, z - P.z) < REACQ_PARK_M;
          tr.stale = false; tr.stalePose = null; tr.staleAir = false;
          if (!same) { if (!anc) tr.reacquire = true; this.releasePark(tr, tf, 'moved while silent'); }
          else if (tr.park && tr.park.inside) { tr.park.inside = false; tr.hidden = false; this.event({ t: tf, kind: 'hangar_out', type: 'hangar_out', key: tr.key, rwy: null, spot: tr.park.spotId || null, src: 'inf', rule: 'heard again at its hangar', cls: tr.dims && tr.dims.cls, tower: towerStatus(tf) }); }
          if (gap > 600000 && !anc) tr.reacquire = true;
        }
      }
      this.setInfo(tr, a);
      const L = tr.last;
      if (L && tf <= L.t + 20) { tr.lastRecv = recvNow; continue; }    // same report again / out of order
      if (L && !tr.stale) this.ages.push([recvNow, (recvNow - L.t) / 1000, !L.ground || (L.gs || 0) > 1]);
      if (L && tf - L.t > 90000 && !anc) tr.reacquire = true;            // longer than any polling hole: re-placed (fade)
      const f = this.report(tr, a, x, z, tf);
      if (!f) { tr.lastRecv = recvNow; continue; }
      // (fix round 2: never drop a fix the display still needs - after a long silence the buffer was trimmed under the display
      // time, the target fell back to 'before the first fix' and the aircraft was re-placed)
      tr.fx.push(f); const tKeep = recvNow - this.delay - 120000;
      while (tr.fx.length > 2 && (tr.fx.length > 700 || (tr.fx.length > 4 && f.t - tr.fx[0].t > 20 * 60000)) && tr.fx[1].t < tKeep) tr.fx.shift();
      tr.lastFixT = tf; tr.lastRecv = recvNow; this.counters.reports++;
      if (tr.vehicle) { tr.phase = 'vehicle'; f.ph = 'vehicle'; f.pi = { src: 'obs', rule: 'emitter category / type / relay _veh' }; continue; }
      const res = this.classifier.step(tr, f, recvNow);
      for (const e of res.events) this.event(e);
      // a parked aircraft that moves away from its parking pose while transmitting has left it: the spot is free again and
      // the record no longer describes it (fix round 1; it used to be released only by silence or removal)
      if (tr.park && !tr.park.inside && tr.park.pose) { const dp = Math.hypot(f.x - tr.park.pose.x, f.z - tr.park.pose.z); if (dp > REACQ_PARK_M || !f.ground) this.releasePark(tr, f.t, 'left the spot'); }
      if (String(tr.key)[0] === '~') this.dupCheck(tr, f);
      // rest poses of the newest still runs now (not lazily at display time): a segment that ends at a still fix then
      // already ends at the pose drawn there (spot pose / median), so arriving at a spot is continuous
      for (let q = Math.max(0, tr.fx.length - 3); q < tr.fx.length; q++) if (tr.fx[q].ground && tr.fx[q].stillRun) this.restOf(tr, tr.fx[q]);
    }
    if (this.adaptDelay) this.adapt(recvNow);
    this.version++;
  }
  anchorAt(tr, recvNow, tf) {
    const L = tr.last; if (!L || !L.ground || tr.vehicle || !tr.ctl || !tr.disp.valid) return null;
    const tD = this.displayTime(recvNow);
    if (!(tD > L.t + 1000 && tf > tD + 1000)) return null;        // the display is past the newest fix and before the new one
    const o = this.target(tr, tD, {}), gs = o.gs || 0;
    if (!o.ground || o.hideSeg) return null;      // (review round 3: a silent take-off continued in the air - no ground anchor)
    const A = { t: tD, x: o.x, z: o.z, px: o.x, pz: o.z, y: this.groundY(o.x, o.z), ground: true, g: true, gs: gs / KT, gsm: gs, vx: o.vx || 0, vz: o.vz || 0,
      dir: gs > 0.5 ? bearR(o.vx, o.vz) : (o.hd ?? L.dir), hd: o.hd ?? L.hd, hdReal: false, strip: L.strip, h: L.h, surfFt: L.surfFt, ph: L.ph, pi: L.pi, turn: 0, synthetic: true, after: L };
    tr.anchor = A; this.counters.anchors = (this.counters.anchors || 0) + 1;
    return A;
  }
  // a TIS-B trackfile ('~' key: the ground station's own track of a target, e.g. a radar return) right beside an ADS-B track
  // of the same aircraft is an echo, not a second aircraft: it is not drawn while it stays within 150 m / 300 ft of a track
  // heard within 10 s [inf]
  dupCheck(tr, f) {
    let dup = null;
    for (const o of this.tracks.values()) {
      if (o === tr || String(o.key)[0] === '~' || o.vehicle) continue; const L = o.last; if (!L || Math.abs(L.t - f.t) > 10000) continue;
      if (Math.hypot(L.x - f.x, L.z - f.z) > 150) continue;
      if (f.altB != null && L.altB != null && Math.abs(f.altB - L.altB) > 300) continue;
      dup = o.key; break;
    }
    if (dup && !tr.dupOf) this.counters.tisbEcho = (this.counters.tisbEcho || 0) + 1;
    tr.dupOf = dup;
  }
  // live persistence: a remembered (restored) parked aircraft and a new track standing at the same place with the same type
  // are one aircraft (its key can change: D1-masked keys are salted per relay process) - the remembered one is dropped
  reconcileRestored(tr, a, x, z) {
    if ((a.gs ?? 0) > 3) return;
    for (const o of [...this.tracks.values()]) {
      if (!o.restored || !o.stale || o === tr || !o.stalePose) continue;
      if (Math.hypot(o.stalePose.x - x, o.stalePose.z - z) > REACQ_PARK_M) continue;
      if (o.info.icao && a.icao && o.info.icao !== a.icao) continue;
      this.remove(o); this.restoredN--; this.counters.restoredMerged = (this.counters.restoredMerged || 0) + 1;
    }
  }
  // the relay learned only now that these keys are LADD / PIA (D1): their identity goes at once - the track becomes type-only
  // and is not persisted (the relay re-publishes the aircraft under its masked key)
  forget(keys) {
    for (const k of keys || []) { const tr = this.tracks.get(k); if (!tr) continue;
      // (maskWhy 'd1': the relay learned a LADD / PIA flag - the card says so, not 'type-only feed'; fix round 2)
      Object.assign(tr.info, { masked: true, maskWhy: 'd1', flight: null, reg: null, ownOp: null, squawk: null, mx: tr.info.mx ? { r: null, t: tr.info.mx.t, d: tr.info.mx.d, op: null } : null });
      tr.ident = identity(tr.info, tr.key, { masked: true }); tr.d1Late = true; this.gone(tr, 'D1 late flag'); this.saveParkedSoon(); this.counters.d1Forget = (this.counters.d1Forget || 0) + 1; }
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
      category: a.category || I.category || null, masked: !!(a.masked || I.masked), maskWhy: I.maskWhy === 'd1' || a.maskWhy === 'd1' ? 'd1' : (a.maskWhy || I.maskWhy || null), mx: a.mx || I.mx || null, src: a.srcType || I.src, nacp: a.nacp ?? I.nacp, squawk: tr.ident && tr.ident.masked ? null : (a.squawk ?? I.squawk ?? null),
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
      // (fix round 2: the SAME rejected report repeated in the next payloads - the relay re-sends an unchanged record - is not
      // a second or third agreeing report; it used to be accepted on its third copy)
      if (tr.rejT != null && Math.abs(tf - tr.rejT) < 20) return null;
      const dt = Math.max(0.2, (tf - L.t) / 1000), d = Math.hypot(x - L.x, z - L.z);
      const vmax = Math.max(a.gs ?? 0, L.gs ?? 0, g ? 10 : 160) * KT;
      if (d > 1.5 * vmax * dt + (g ? 30 : 250) && dt < 60) {
        const R0 = tr.rejPt; tr.rejects = R0 && Math.hypot(x - R0[0], z - R0[1]) < 40 ? tr.rejects + 1 : 1; tr.rejPt = [x, z]; this.counters.rejects++;
        if (tr.rejects < 3) { tr.rejT = tf; return null; }
        tr.reacquire = true; this.counters.reacquire++;
      }
      // (fix round 2) airborne kinematic consistency: a fix whose position implies a velocity change of more than 2 g against
      // the previous fix's reported velocity over 2-20 s (a 154-kt single 'reversing' in 4.6 s: a garbled TIS-B position) is
      // rejected like a position jump - unless the next two agree with it [inf: 2 g, GA normal-category limit is 3.8 g but a
      // sustained 2 g of horizontal acceleration is not flown in a pattern]
      else if (!g && !L.ground && dt >= 2 && dt <= 20 && L.gs != null && L.trk != null && !tr.vehicle) {
        const vL = hvR(L.trk * D2R), sL = L.gs * KT, vcx = (x - L.x) / dt, vcz = (z - L.z) / dt;
        const aImp = Math.hypot(vcx - vL[0] * sL, vcz - vL[1] * sL) / dt;
        if (aImp > 2 * GRAV) {
          const R0 = tr.rejPt; tr.rejects = R0 && Math.hypot(x - R0[0], z - R0[1]) < 40 + 100 * dt ? tr.rejects + 1 : 1; tr.rejPt = [x, z]; this.counters.airKinRejects = (this.counters.airKinRejects || 0) + 1;
          if (tr.rejects < 3) { tr.rejT = tf; return null; }
        }
      }
    }
    tr.rejects = 0; tr.rejPt = null; tr.rejT = null;
    this.classifier.prep(tr, f);
    const heli = tr.dims && tr.dims.cls === 'heli';
    const hc = (tr._k && tr._k.q === 100) ? CR.H_CONTACT_COARSE : CR.H_CONTACT;
    // display ground: the flag, runway contact, or ground by kinematics ON (or within PAVED_NEAR_M of) pavement - a low slow
    // fix over the approach grass (a per-unit altitude bias of tens of ft, derive.py) stays airborne in the drawing; the
    // classifier keeps the offline G state for its counts
    f.ground = heli ? g : (g || (!!f.strip && f.h != null && f.h <= hc && (f.gs == null || f.gs < 120)) || (f.gk && this.pavedNear(x, z)));
    // debounce (fix round 1): leaving the ground needs speed or a second airborne fix. One airborne-by-altitude fix of a slow
    // fixed-wing aircraft right after a ground fix is altitude noise (100-ft units, no weight-on-wheels: a parked C172 was
    // drawn taking off to 99 ft and landing back) - it is held on the ground; the next fix confirms or revises it
    if (!heli && !tr.vehicle && !f.ground && L && L.ground && !g && (f.gs ?? 0) < CR.GK_GS && f.h != null && f.h < HELD_H_FT && tf - L.t < 30000) { f.ground = true; f.held = true; this.counters.groundHeld = (this.counters.groundHeld || 0) + 1; }
    // a fixed-wing aircraft reported slower than SLOW_FRAC x its approach speed cannot be flying (no weight-on-wheels, an
    // altitude bias): it is on the ground where there is pavement near it, or anywhere off the HWD site (not drawn there) [inf]
    else if (!heli && !tr.vehicle && !f.ground && f.gs != null && f.gs < SLOW_FRAC * (tr.dims && tr.dims.vapp_kt || 62) && (f.h == null || f.h < 500) && (Math.hypot(x, z) > GROUND_VIEW_M || this.pavedNear(x, z, 30))) { f.ground = true; f.slowGround = true; this.counters.slowGround = (this.counters.slowGround || 0) + 1; }
    // (fix round 2) slower than the minimum flying speed (0.7 x the approach speed) ON a runway, whatever the altitude: a
    // landing / take-off roll with a garbled altitude (a C172 'at 990 ft' rolling out at 40 -> 31 kt along 28L, then taxiing
    // on 28R 48 s later) - not a fixed-wing aircraft hanging in the air [inf]
    // (review round 3: not a fix well above the runway with a consistent altitude - a TF19 climbing out at 48 kt, 290 ft up,
    // was put on the runway because its ACD approach speed is 70 kt; the speeds are the track's own, spd)
    // (not when the height is corroborated - barometric and geometric altitude both reported and agreeing, >= 150 ft up: the
    // garbled case was a geometric altitude alone, constant at 925 ft while the speed fell from 40 to 31 kt)
    else if (!heli && !tr.vehicle && !f.ground && f.gs != null && f.gs < 0.7 * (tr.dims && tr.dims.vapp_kt || 62) && !(f.h != null && f.h >= 150 && f.altB != null && f.altG != null && Math.abs(f.altG - f.altB) < 200) && f.strip && this.onRunway(x, z, 10)) { f.ground = true; f.slowGround = true; this.counters.slowRunway = (this.counters.slowRunway || 0) + 1; }
    else if (!heli && L && L.held && !f.ground) { L.ground = false; L.held = false; if (L.yAir != null) L.y = L.yAir; tr.routeCache.clear(); }
    // (fix round 2) a fast fix in runway contact by ALTITUDE only (no ground flag) that has not yet crossed the landing threshold
    // of the runway it is aligned with is still over the approach end (a 100-ft altitude unit reading 56 ft): it is drawn
    // airborne, low over the threshold - a touchdown is drawn past the threshold, never on the overrun / approach area
    if (f.ground && !g && !heli && !tr.vehicle && (a.gs ?? 0) > 30 && f.trk != null) {
      const B = this.rwyFor(x, z, f.trk * D2R, 60);
      if (B) { const endName = B.sgn > 0 ? B.r.id.split('/')[0] : B.r.id.split('/')[1], thrAl = B.sgn > 0 ? thrDispM(endName) : B.r.length - thrDispM(endName);
        if ((B.al - thrAl) * B.sgn < 0) { f.ground = false; f.lowThr = true; this.counters.beforeThreshold = (this.counters.beforeThreshold || 0) + 1; } }
    }
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
    if (f.held) f.yAir = Math.max(gy + 0.3, f.surfFt * FT + f.h * FT);
    if (f.lowThr) f.y = gy + Math.max(3, Math.min(f.h ?? 15, 15)) * FT;
    f.vsm = f.vs != null ? f.vs * FT / 60 : null;
    // direction of motion and nose (radians internally)
    let chord = null, dtL = L ? (tf - L.t) / 1000 : 0;
    if (L) { const dx = x - L.x, dz = z - L.z, d = Math.hypot(dx, dz); if (d > (f.ground ? 3 : 20)) chord = bearR(dx, dz); if (f.gs == null && dtL > 0) f.gs = d / dtL / KT; }
    f.gsm = (f.gs ?? 0) * KT;
    // (review round 3) the slowest this track has been seen flying: airborne, >= 150 ft above the field, with a speed
    if (!f.ground && !tr.vehicle && f.h != null && f.h >= 150 && f.gs != null && f.gs > 20 && f.altB != null && f.altG != null && Math.abs(f.altG - f.altB) < 200) tr.vAirMin = Math.min(tr.vAirMin ?? 1e9, f.gsm);
    const th = f.th != null ? f.th * D2R : null;
    if (!f.ground) { f.dir = f.trk != null ? f.trk * D2R : chord ?? (L ? L.dir : th ?? 0); f.hd = th ?? f.dir; f.hdReal = th != null; }
    else {
      const moving = f.gsm > 0.5;
      // (review round 3: the first fix of a track heard moving fast on the ground has no chord - its reported ground track
      // is used, > 10 kt only [inf limit]; it used to point north (0) and the body started turning off the runway)
      const trkG = !L && a.track != null && (a.gs ?? 0) > 10 ? a.track * D2R : null;
      f.dir = moving ? (chord ?? th ?? trkG ?? (L ? L.dir : 0)) : (L ? L.dir : th ?? 0);
      f.hd = th ?? (moving ? f.dir : (L ? L.hd : null)); f.hdReal = th != null;
      // map matching onto the taxiway centrelines (sfo3d): snap laterally when close, aligned and at taxi speed
      if (moving && f.gs > 2 && this.net.ok && !tr.vehicle && !heli && !f.strip) {
        const mm = this.net.match(x, z, f.dir, tr.matchWay, 10, (th != null ? 20 : 35) * D2R);
        if (mm) { const s = (lo, hi, v) => { const t = clamp((v - lo) / (hi - lo), 0, 1); return t * t * (3 - 2 * t); };
          const wgt = (1 - s(5, 10, mm.d)) * s(2, 4, f.gs); f.px = x + (mm.px - x) * wgt; f.pz = z + (mm.pz - z) * wgt; tr.matchWay = mm.way; f.snap = mm.d * wgt; }
        else tr.matchWay = null;
      }
    }
    // a ground roll (faster than taxi speed) on a runway strip is matched to the runway centreline - for EVERY segment that
    // starts or ends at the fix (fix round 2: only the taxi-route profile snapped it, so a landing plan or a Hermite ended at
    // the raw GNSS point 12-30 m beside the axis and the next route started on the axis - a target jump and a re-placement)
    if (f.px == null && f.ground && f.strip && f.gsm > TAXI_V && !heli && !tr.vehicle) {
      const B = this.rwyFor(x, z, f.dir, 30); if (B) { const p = this.axisPt(B.r, clamp(B.al, 0, B.r.length)); f.px = p[0]; f.pz = p[1]; f.snap = Math.abs(B.ac); }
    }
    // (review round 3, m5) a fixed-wing fix flagged on the ground faster than any taxiing (25 kt) is a take-off / landing roll:
    // drawn on the centreline of the runway its track follows when one is within 60 m (GNSS drift of 38 m beside 28R at
    // 56-63 kt was drawn as 'taxiing' across the grass); at >= 0.8 VR with no runway under it, it is flying (low) [inf]
    if (f.px == null && f.ground && !heli && !tr.vehicle && f.gsm > TAXI_BODY_MAX && Math.hypot(x, z) < GROUND_VIEW_M) {
      const B = this.rwyFor(x, z, f.dir, 60);
      // (f.rwy, not f.strip: the classifier keeps the offline strip rule)
      if (B && B.al >= -30 && B.al <= B.r.length + 30) { const p = this.axisPt(B.r, clamp(B.al, 0, B.r.length)); f.px = p[0]; f.pz = p[1]; f.snap = Math.abs(B.ac); f.rwy = B.r.id; this.counters.fastGroundSnap = (this.counters.fastGroundSnap || 0) + 1; }
      else if (f.gsm >= 0.8 * this.spd(tr).vr && !this.pavedNear(x, z, 3)) { f.ground = false; f.fastAir = true; f.y = this.groundY(x, z) + Math.max(3, Math.min(f.h ?? 15, 50)) * FT; this.counters.fastGroundAir = (this.counters.fastGroundAir || 0) + 1; }
    }
    // (fix round 2) a fixed-wing ground fix off the pavement (site + NAIP) by GNSS error - a run-up pad the pavement model does
    // not have, 15 m of position error - is drawn at the nearest point within 25 m where its wheels stand on pavement: routes
    // then end on pavement, and the body no longer drives across the grass to a placement offset [inf: SEEK_MAX_M of ground.js]
    if (f.ground && !heli && !tr.vehicle && this.site) {
      const px0 = f.px ?? x, pz0 = f.pz ?? z, hw = tr.dims ? tr.dims.track / 2 + 0.3 : 1.5;
      const okAt = (qx, qz) => this.paved(qx, qz) && this.paved(qx + hw, qz) && this.paved(qx - hw, qz) && this.paved(qx, qz + hw) && this.paved(qx, qz - hw);
      // (not a fix inside a building footprint: an aircraft entering its hangar is detected and faded there - step() inH)
      if (!okAt(px0, pz0) && !this.site.buildingAt(px0, pz0)) { let best = null;
        for (let r = 1; r <= 25 && !best; r += 1) { const n = Math.max(8, Math.round(r * 2)); for (let k = 0; k < n; k++) { const an = k / n * 2 * Math.PI, qx = px0 + Math.cos(an) * r, qz = pz0 + Math.sin(an) * r; if (okAt(qx, qz)) { best = [qx, qz]; break; } } }
        if (best) { f.px = best[0]; f.pz = best[1]; f.paveSnap = Math.hypot(best[0] - x, best[1] - z); this.counters.paveSnap = (this.counters.paveSnap || 0) + 1; } }
    }
    if (f.px == null) { f.px = x; f.pz = z; }
    const v = hvR(f.dir); f.vx = v[0] * f.gsm; f.vz = v[1] * f.gsm;
    f.turn = 0; if (L && L.dir != null && dtL > 0.3 && dtL < 6) { const w = wrapPi(f.dir - L.dir) / dtL; f.turn = Math.abs(w) < (f.ground ? 20 : 6) * D2R ? w : 0; }
    return f;
  }

  // ---------------------------------------------------------------- per frame
  update(now, dt) {
    // (review round 3) a stalled frame is caught up in 0.1-s sub-steps for up to STALL_CATCH_S: the app passes dt <= 0.1 and
    // the engine used to integrate at most 5 s of a longer gap - the bodies fell kilometres behind their targets and were
    // re-placed (a 28-s rAF stall measured in the SwiftShader sandbox gave most of the 59 in-app cuts in 8 min). A longer
    // gap (a hidden tab) re-places the bodies at their targets with a fade-in, not counted as a cut.
    const raw = this._lastNow != null ? Math.max(0, (now - this._lastNow) / 1000) : dt; this._lastNow = now;
    const el = Math.min(raw, STALL_CATCH_S), resync = raw > STALL_CATCH_S;
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
        else if (lf.ground && shownLast > 15000 && age > MOVING_LOST_MS + LATENCY_ALLOW_MS) this.groundLost(tr, now, lf);
      } else if (tr.stale && now - tr.lastRecv > (tr.park ? PARK_KEEP_MS : LOST_KEEP_MS)) this.gone(tr, 'expired');
      else if (tr.stale && tr.staleOverrun && !tr.fadeOut) { this.counters.staleOverrun = (this.counters.staleOverrun || 0) + 1; this.gone(tr, 'a heard aircraft drove through its last position'); }
      // airborne and dead-reckoned for longer than AIR_HIDE_S (live: reports stopped): fade out instead of flying on - or
      // hovering - on invented positions; drawn again (a fresh body, faded in) once a new report puts the display between fixes
      if (!lf.ground && !tr.vehicle) { const hide = shownLast > AIR_HIDE_S * 1000; if (hide && !tr.airHidden) { tr.airHidden = true; this.counters.airHidden = (this.counters.airHidden || 0) + 1; } else if (!hide && tr.airHidden) { tr.airHidden = false; tr.reacquire = true; } }
      else if (tr.airHidden) { tr.airHidden = false; tr.reacquire = true; }
      // simulate bodies near HWD only (SIM_NM); others keep their fixes but are not drawn
      // (ground tracks only on and around HWD: aircraft on the ground at OAK, 6 NM away, are outside the D6 window)
      const rl = Math.hypot(lf.x, lf.z);
      const near = (lf.ground ? rl < 4000 : rl < SIM_NM * NM) || (tr.ctl && !tr.ctl.ground && Math.hypot(tr.ctl.x, tr.ctl.z) < SIM_NM * NM);
      tr._far = !near;
      if (!near) { tr.disp.valid = false; tr.inView = false; tr.ctl = null; continue; }
      if (resync) { tr.ctl = null; tr.cutting = null; }
      for (let i = 0; i < nSub; i++) this.step(tr, tDisp - (nSub - 1 - i) * h * 1000, h);
      this.view(tr);
    }
    for (const tr of removed) this.remove(tr);
    this.staleAhead(tDisp);
  }
  // (review round 3, M1 / m4) a SILENT aircraft (stale: drawn where it was last placed, inferred) that lies in the way of a heard
  // ground aircraft's next 5 s of motion - its own target path, sampled - is faded out before the two touch (planforms within
  // 1 m): the heard aircraft's fixes are observed, the silent one's position only inferred, and it has evidently moved. Fix
  // round 2 faded it only after a margin-0 overlap. [inf: 5 s, 1 m]
  staleAhead(tDisp) {
    const S = []; for (const q of this.tracks.values()) if (q.stale && !q.staleAir && !q.fadeOut && q.disp.valid && q.disp.ground && q.dims && !q.hidden && !(q.park && q.park.inside) && q.disp.alpha > 0.01) S.push(q);
    if (!S.length) return;
    const o = {};
    for (const tr of this.tracks.values()) {
      if (tr.stale || tr.fadeOut || tr.vehicle || !tr.dims || !tr.disp.valid || !tr.disp.ground || !(tr.disp.gs > 0.3) || !(tr.disp.alpha > 0.01)) continue;
      const near = S.filter(q => !q.staleOverrun && Math.hypot(q.disp.x - tr.disp.x, q.disp.z - tr.disp.z) < 140); if (!near.length) continue;
      const rp = tr.restPose, rh = tr._raw;
      // (a silent aircraft PARKED at a spot - an apron, a tie-down - is avoided by the routes, routeBlock, and faded only when
      // the heard one is about to touch it (<= 1.5 s, 0.5 m): faded early it would come back somewhere else when heard again)
      for (const dtF of [0.5, 1.5, 3, 5]) {
        const q = this.target(tr, tDisp + dtF * 1000, o); if (!q.ground) break;
        const B = bodyOf(tr.dims, q.x, q.z, q.gs > 0.5 ? toDeg(bearR(q.vx, q.vz)) : tr.disp.hdg);
        for (const sq of near) { if (sq.staleOverrun || (sq.park && dtF > 1.5)) continue;
          if (overlaps(B, bodyOf(sq.dims, sq.disp.x, sq.disp.z, sq.disp.hdg), sq.park ? 0.5 : 1.0)) { sq.staleOverrun = true; this.counters.staleAhead = (this.counters.staleAhead || 0) + 1; } }
      }
      tr.restPose = rp; tr._raw = rh;
    }
  }
  gone(tr, why) { if (!tr.disp.valid || !(tr.disp.alpha > 0.01)) { this.remove(tr); return; } tr.fadeOut = true; tr.goneWhy = why; }
  // a ground track without a position for MOVING_LOST_MS: parked (kept), hangared (hidden), or lost (faded out)
  // the pose a ground track rests at when its signal ends: the rest pose of its NEWEST still run, else its newest fix -
  // never an older parking pose (fix round 1: a departed aircraft went back to the spot it had left, up to 1.3 km away)
  lastPose(tr, lf) {
    const R = lf.stillRun ? (tr.rests.get(lf.stillRun[0]) || this.restOf(tr, lf)) : null;
    if (R) return { x: R.x, z: R.z, hdg: R.hdg, spot: R.spot || null, rule: R.rule };
    // (fix round 2) a moving fix: where the drawn target came to rest after it - the braking stop of extrapolate(), which the
    // body has followed - so the stale pose is continuous with the drawing
    const o = this.extrapolate(tr, lf, 600, {}), h = o.hd != null ? o.hd : (lf.gsm > 0.5 ? lf.dir : lf.hd);
    return { x: o.x, z: o.z, hdg: h != null ? toDeg(h) : null, spot: null, rule: lf.gsm > 0.5 ? 'stopped after the newest fix [inf]' : 'newest fix' };
  }
  // where an aircraft can be left standing: an apron / helipad, or a taxilane at a hangar door (T-hangar rows); never a
  // runway or a taxiway (data/hwd_airport.json: every Phase 1 spot lies on 'apron' or 'helipad') [inf]
  parkablePlace(x, z, heli) {
    if (!this.site) return true;
    const s = this.site.surface(x, z);
    if (s === 'apron' || s === 'helipad') return true;
    if (s === 'taxilane') return !!(this.parking && this.parking.hangarNear(x, z, 15));
    return heli && s === 'grass';
  }
  groundLost(tr, now, lf) {
    const P = this.lastPose(tr, lf), heli = tr.dims && tr.dims.cls === 'heli';
    const H = this.parking && this.parking.hangarNear(P.x, P.z);
    const slow = (lf.gs ?? 0) < 8;
    if (H && slow) {
      if (tr.park && tr.park.pose && Math.hypot(tr.park.pose.x - P.x, tr.park.pose.z - P.z) > REACQ_PARK_M) this.releasePark(tr, lf.t, 'left the spot');
      tr.stale = true; tr.hidden = true; tr.stalePose = { x: P.x, z: P.z, hdg: P.hdg };
      tr.park = { ...(tr.park || {}), spotId: tr.park ? tr.park.spotId : null, kind: 'hangar', zone: H.hangar.name || 'hangar', src: 'inf', inside: true, hangar: H.hangar.id, pose: tr.stalePose };
      this.counters.hangared++; this.event({ t: lf.t, kind: 'hangar_in', type: 'hangar_in', key: tr.key, rwy: null, spot: tr.park.spotId || null, src: 'inf', rule: `signal ended ${H.d.toFixed(1)} m from ${H.hangar.name || 'a hangar'} (<= 8 m)`, cls: tr.dims && tr.dims.cls, tower: towerStatus(lf.t) });
      this.saveParkedSoon(); return;
    }
    // fix round 2: the aircraft STAYS where it was last placed, whatever the surface - it is drawn there, stale, until it is
    // heard again (then it moves on from this pose: the continuation anchor of ingest) or LOST_KEEP_MS / PARK_KEEP_MS pass.
    // Standing still on an apron / helipad / hangar-door taxilane it is parked there; elsewhere (a taxiway, a run-up pad, a
    // runway) its phase is 'no_signal' (inferred). Before, it faded out and reappeared minutes later where it had stood.
    if (Math.hypot(P.x, P.z) > GROUND_VIEW_M) { this.gone(tr, 'ground lost off the HWD site'); return; }   // (OAK: not drawn anyway)
    // (review round 3, M1) a take-off that continued silently (runwayCont) has left: hidden, kept until heard again
    { const C = !heli && !tr.vehicle ? this.runwayCont(tr, lf) : null;
      if (C && C.depart) { tr.stale = true; tr.staleAir = true; tr.staleSince = now; tr.stalePose = null; this.releasePark(tr, lf.t, 'departed'); this.counters.silentDeparted = (this.counters.silentDeparted || 0) + 1; return; } }
    tr.stale = true; tr.staleSince = now; tr.stalePose = { x: P.x, z: P.z, hdg: P.hdg, rule: P.rule, src: 'inf' };
    // the park record is the one at this pose; a record of another (older) pose is released
    if (tr.park && tr.park.pose && Math.hypot(tr.park.pose.x - P.x, tr.park.pose.z - P.z) > REACQ_PARK_M) this.releasePark(tr, lf.t, 'left the spot');
    if ((lf.gs ?? 0) < 1 && !lf.strip && this.parkablePlace(P.x, P.z, heli)) { if (!tr.park) this.parkAt(tr, P, lf.t, 'signal ended standing here'); }
    else this.counters.groundLostKept = (this.counters.groundLostKept || 0) + 1;
    this.saveParkedSoon();
  }
  parkAt(tr, P, t, why) {
    let spot = P.spot || null;
    if (!spot && this.parking && tr.dims) { const m = this.parking.match({ x: P.x, z: P.z, hdg: P.hdg, ant: [P.x, P.z] }, tr.dims, { heli: tr.dims.cls === 'heli', key: tr.key }); if (m && m.ok) spot = m.spot; }
    if (spot && this.parking) this.parking.occupy(tr.key, spot);
    tr.park = { spotId: spot ? spot.id : null, kind: spot ? spot.kind : 'unspotted', zone: spot ? spot.zone : (this.site && this.site.apronAt(P.x, P.z) ? this.site.apronAt(P.x, P.z).name : null), src: 'inf', inside: false, pose: { x: P.x, z: P.z, hdg: P.hdg }, headed: false, hdgSrc: null, t0: t };
    this.counters.parked++;
    this.event({ t, kind: 'park', type: 'park', key: tr.key, rwy: null, spot: tr.park.spotId, src: 'inf', rule: why, cls: tr.dims && tr.dims.cls, tower: towerStatus(t) });
  }
  remove(tr) { tr.removed = true; this.releasePark(tr, this.dataNow, 'removed'); for (const e of this.classifier.flush(tr, this.dataNow)) this.event(e); this.tracks.delete(tr.key); this.counters.removed++; if (tr.park || tr.stale) this.saveParkedSoon(); }
  clearParked() { for (const tr of [...this.tracks.values()]) if (tr.stale) this.remove(tr); this.saveParked(); }
  releasePark(tr, t, why) {
    if (!tr.park) return; const p = tr.park; tr.park = null; tr.hidden = false; tr.unparkT = Math.max(tr.unparkT || 0, t);
    if (this.parking) this.parking.release(tr.key);
    if (p.spotId || p.kind) this.event({ t, kind: 'unpark', type: 'unpark', key: tr.key, rwy: null, spot: p.spotId || null, src: p.src || 'obs', rule: why, cls: tr.dims && tr.dims.cls, tower: towerStatus(t) });
  }
  // D6 display window with hysteresis: <= 5 NM and <= 3,000 ft AGL (on the ground: anywhere within the window)
  view(tr) {
    const D = tr.disp; if (!D.valid) { tr.inView = false; return; }
    const r = Math.hypot(D.x, D.z) / NM, hAgl = (D.y - this.groundY(D.x, D.z)) / FT;
    const k = tr.inView ? VIEW_HYST : 1;
    tr.inView = r <= VIEW_NM * k && (D.ground ? r * NM <= GROUND_VIEW_M && !tr.dupOf : hAgl <= VIEW_FT * k) && !tr.dupOf;
  }

  // ---------------------------------------------------------------- display target at display time t
  restOf(tr, f) {
    if (!f || !f.stillRun) return null; const k = f.stillRun[0];
    let P = tr.rests.get(k); const run = tr.fx.filter(q => q.stillRun && q.stillRun[0] === k);
    if (P && (P.n === run.length || run.length < P.n)) return P;   // (fewer: older fixes dropped from the buffer)
    // median antenna position of the still fixes -> main-gear origin (dims.ant behind the nose, xMain behind the nose)
    // (fix round 2: the DISPLAY positions - px / pz, snapped onto the pavement where the GNSS fix fell beside it)
    const xs = run.map(q => q.px ?? q.x), zs = run.map(q => q.pz ?? q.z); const ax = median(xs), az = median(zs);
    const hs = run.filter(q => q.th != null).map(q => q.th);
    let hdg = hs.length ? circMedianDeg(hs) : null, hdgReal = hs.length > 0, hsrc = hs.length ? 'obs (true_heading)' : null;
    if (hdg == null) { const i0 = tr.fx.indexOf(run[0]); for (let i = i0; i >= Math.max(0, i0 - 6); i--) { const q = tr.fx[i]; if (q.gsm > 1 && q.dir != null) { hdg = toDeg(q.dir); hsrc = 'inf (direction of the last motion)'; break; } } }
    const isPark = run.some(q => q.ph === 'parked' || (q.pi && q.pi.heliPark));
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
    // standing inside a hangar footprint (its own still fixes put it there): it is in the hangar - not drawn through the walls
    // (fix round 1: helicopters and a T-hangar M20P were drawn inside closed hangars) [inf: no doors are modelled]
    if (this.site) { const bA = this.site.buildingAt(ax, az); const bd = bA && (/hangar/.test(bA.kind || '')); if (bd && !(spot && this.parking && (this.parking.byId.get(spot.id) || {}).door)) { P.inHangar = bA.name || bA.kind; } }
    tr.rests.set(k, P); if (tr.rests.size > 12) tr.rests.delete(tr.rests.keys().next().value);
    if (isPark) this.notePark(tr, P, run[run.length - 1].t);
    return P;
  }
  faceTaxi(x, z) { const L = this.net.ok ? this.net.projLinks(x, z) : []; if (!L.length || L[0].d < 1) return 0; return toDeg(bearR(L[0].px - x, L[0].pz - z)); }
  notePark(tr, P, t) {
    if (tr.unparkT && t <= tr.unparkT) return;     // a still run that ended before the aircraft left its spot: not parked again
    if (tr.stale) return;                          // a silent track keeps the record groundLost gave it
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
    const F = tr.fx, n = F.length; o.stop = false; o.hd = null; o.route = false; o.mode = ''; o.before = false; o.hideSeg = false; o.rest = null; o.planPh = null; o.vRep = null; o.recon = false; o.rollSeg = false;
    // a stale (silent, parked) track rests where it was last heard (its newest rest pose), never at an older parking pose
    if (tr.stale && tr.stalePose) { const p = tr.stalePose; o.mode = 'stale'; Object.assign(o, { x: p.x, z: p.z, y: this.groundY(p.x, p.z), vx: 0, vz: 0, vy: 0, gs: 0, ground: true, ex: 0, stop: true, hd: p.hdg != null ? p.hdg * D2R : null }); o.rest = p; return o; }
    // a reconstructed take-off / landing that runs past the fix it was planned to (late join, review round 3): the plan, until
    // it has joined the track again
    if (tr.xplan) { const X = tr.xplan;
      if (t >= X.t0 && (t <= X.t1 || X.lazy)) { if (X.lazy) this.xplanAir(tr, X, t); this.samplePlan(X, t, o); o.mode = 'xplan:' + X.kind + ':' + o.seg; o.recon = true; if (X.hideSeg) o.hideSeg = true; return o; }
      if (t > X.t1 + 2000) tr.xplan = null; }
    let i = n - 1; while (i > 0 && F[i - 1].t > t) i--;
    if (t <= F[0].t) {   // before the first fix: hidden (alpha stays 0); airborne: back along its velocity (sfo3d), <= 10 s
      this.fill(o, F[0]); o.ex = 0; o.before = true; o.mode = 'before';
      if (!F[0].ground) { const b = Math.min(10, (F[0].t - t) / 1000); o.x -= o.vx * b; o.z -= o.vz * b; o.y -= (o.vy || 0) * b; }
      // (review round 3: a ground track first heard moving - e.g. mid take-off roll after a recorder hole - keeps the fix's
      // velocity while it waits hidden at the fix, so the body appears at that speed; it used to start from rest and trail the
      // track by ~180 m, then 'hop' off the ground flag flicker of the roll)
      else if (!((F[0].gsm || 0) > 3)) { o.vx = o.vz = 0; o.gs = 0; }
      return this.restTarget(tr, o, F[0], F[0]) || o;
    }
    if (t >= F[n - 1].t) return this.extrapolate(tr, F[n - 1], (t - F[n - 1].t) / 1000, o);
    let a = F[i - 1]; const b = F[i];
    if (tr.anchor && tr.anchor.after === a && t >= tr.anchor.t && tr.anchor.t < b.t) a = tr.anchor;    // continuation anchor (ingest)
    // the REPORTED speeds around the display time (fix round 2): the air follower's speed cap and the re-placement limit use
    // them, not the instantaneous speed of a short-hole Hermite, which jitters with the fix timing (64 / 213 / 44 kt between
    // fixes 0.5-1 s apart of a 145-kt aircraft: the cap braked the body from 175 to 80 kt in 0.5 s and it was re-placed)
    o.vRep = Math.max(a.gsm || 0, b.gsm || 0);
    const dtm = b.t - a.t, dt = dtm / 1000, u = (t - a.t) / dtm;
    const heli = tr.dims && tr.dims.cls === 'heli';
    // a take-off or landing inside a polling hole: a timed plan - taxi path, runway roll from the ground fix's own speed,
    // climb-out / approach curve, roll-out and exit (transitionFor)
    if (a.ground !== b.ground && dt > HOLE_S && tr.dims && !heli) {
      const P = this.transitionFor(tr, a, b, dt); if (P) { if (tr.xplan === P) return this.target(tr, t, o); this.samplePlan(P, t, o); o.mode = 'plan:' + P.kind + (P.fallback ? 'F' : '') + ':' + o.seg; if ((P.far && o.ground) || P.hidden) o.hideSeg = true; o.recon = true; return o; }
    }
    if (a.ground && b.ground) {
      // a take-off roll that starts inside the hole (taxiing / holding at a, rolling fast on the runway at b): taxi, line up
      // and roll from the line-up point to b, reaching b's speed there (fix round 1: the taxi-speed path could not do it
      // and the aircraft was re-placed onto the runway)
      if (dt > HOLE_S && tr.dims && !heli && b.gsm > TAXI_BODY_MAX && b.gsm > (a.gsm || 0) + 8) {
        const P = this.rollFor(tr, a, b, dt); if (P) { this.samplePlan(P, t, o); o.mode = 'plan:' + P.kind + ':' + o.seg; return o; }
      }
      const rt = this.restTarget(tr, o, a, b); if (rt) return rt;
      const A0 = this.endPt(tr, a), B0 = this.endPt(tr, b);
      const d = Math.hypot(B0[0] - A0[0], B0[1] - A0[1]);
      // (only on the HWD site: elsewhere - OAK, 10 km away - there is no pavement model and the body is not drawn)
      if (d > ROUTE_MIN_M && !heli && Math.hypot(A0[0], A0[1]) < GROUND_VIEW_M && (dt > HOLE_S || this.offPaveSeg(tr, a, b))) {
        const G = this.groundPathFor(tr, a, b, dt);
        if (G && G.kind === 'late') { if (tr.xplan && t >= tr.xplan.t0 && t <= tr.xplan.t1) return this.target(tr, t, o); }
        else if (G && !(G.kind === 'hold' && dt <= 20)) { this.sampleGround(G, (t - a.t) / 1000, o); o.mode = G.kind; return o; }
      }
    }
    // an air hole: the Hermite shape with the reported directions, travelled at the reported speeds (motion.js geoHermite) -
    // the drawn speed stays between the two reports instead of bulging to 1.5 x in the middle of a 46-s hole
    if (!a.ground && !b.ground && dt > HOLE_S && a.gsm > 10 && b.gsm > 10 && Math.max(a.gsm, b.gsm) < 2.5 * Math.min(a.gsm, b.gsm)) {
      const G = this.airCurveFor(tr, a, b, dt);
      if (G) { const q = G.at((t - a.t) / 1000); Object.assign(o, { x: q.x, z: q.z, vx: q.vx, vz: q.vz, gs: q.v, ground: false, ex: 0, mode: 'aa:geo' }); this.vertHermite(o, a, b, dt, u); o.y = Math.max(o.y, this.groundY(o.x, o.z) + 0.3); o.hd = null; return o; }
    }
    // Hermite between real reports (sfo3d sampleReps)
    const [apx, apz] = a.ground ? this.endPt(tr, a) : [a.px, a.pz], [bpx, bpz] = b.ground ? this.endPt(tr, b) : [b.px, b.pz];
    const cx = (bpx - apx) / dt, cz = (bpz - apz) / dt, cs = Math.hypot(cx, cz);
    let va = [a.vx, a.vz], vb = [b.vx, b.vz];
    const ok = (v) => Math.hypot(v[0] - cx, v[1] - cz) < Math.max(3, 0.35 * cs);
    const lin = dt > (a.ground ? 20 : 60) || a.ground !== b.ground; o.mode = (a.ground ? 'g' : 'a') + (b.ground ? 'g' : 'a') + (lin ? ':lin' : ':herm');
    // a take-off or landing away from HWD (OAK, 10 km; no pavement model) in a SHORT hole (the long ones fly the fallback plan
    // above): drawn in the air, faded only while it is on the ground (fix round 2: the whole segment used to be hidden, so OAK
    // arrivals faded out at 125-460 ft on short final)
    const farX = a.ground !== b.ground && !heli && Math.hypot((a.ground ? a : b).px, (a.ground ? a : b).pz) > GROUND_VIEW_M;
    const jump = !lin && a.ground && b.ground && cs * dt > 1.6 * Math.max(a.gsm || 0, b.gsm || 0, 0.8) * dt + 3;
    if (lin || (!ok(va) && !jump)) va = [cx, cz]; if (lin || (!ok(vb) && !jump)) vb = [cx, cz];
    const u2 = u * u, u3 = u2 * u;
    const h00 = 2 * u3 - 3 * u2 + 1, h10 = u3 - 2 * u2 + u, h01 = -2 * u3 + 3 * u2, h11 = u3 - u2;
    o.x = h00 * apx + h10 * dt * va[0] + h01 * bpx + h11 * dt * vb[0];
    o.z = h00 * apz + h10 * dt * va[1] + h01 * bpz + h11 * dt * vb[1];
    o.vx = va[0] + (vb[0] - va[0]) * u; o.vz = va[1] + (vb[1] - va[1]) * u;
    if (!a.ground && !b.ground) this.vertHermite(o, a, b, dt, u);
    else { o.y = a.y + (b.y - a.y) * u; o.vy = (b.y - a.y) / dt; }
    o.gs = Math.hypot(o.vx, o.vz); o.ex = 0;
    // ground <-> air without a plan: lift-off soon after a ground fix, touchdown shortly before one (VR from the type)
    if (a.ground !== b.ground) {
      const T = tr.dims, VR = this.spd(tr).vr;
      if (a.ground) { const tl = heli ? Math.min(3, dt * 0.5) : clamp((VR - a.gsm) / 2.5, 0, 0.8 * dt); o.ground = (t - a.t) / 1000 < tl; }
      else { const tt = heli ? Math.min(3, dt * 0.5) : clamp((Math.max(a.gsm * 0.9, VR) - b.gsm) / 2.0, 0, 0.8 * dt); o.ground = (b.t - t) / 1000 < tt; }
    } else o.ground = a.ground;
    if (o.ground) o.y = this.groundY(o.x, o.z);
    else o.y = Math.max(o.y, this.groundY(o.x, o.z) + 0.3);
    if (farX && o.ground) o.hideSeg = true;
    const ha = a.hdReal ? a.hd : null, hb = b.hdReal ? b.hd : null;
    o.hd = ha != null && hb != null ? ha + wrapPi(hb - ha) * u : null;
    return o;
  }
  vertHermite(o, a, b, dt, u) {
    const u2 = u * u, u3 = u2 * u, h00 = 2 * u3 - 3 * u2 + 1, h10 = u3 - 2 * u2 + u, h01 = -2 * u3 + 3 * u2, h11 = u3 - u2;
    const cy = (b.y - a.y) / dt; let sa = a.vsm ?? cy, sb = b.vsm ?? cy;
    if (Math.abs(sa - cy) > Math.max(3, Math.abs(cy))) sa = cy; if (Math.abs(sb - cy) > Math.max(3, Math.abs(cy))) sb = cy;
    o.y = h00 * a.y + h10 * dt * sa + h01 * b.y + h11 * dt * sb; o.vy = sa + (sb - sa) * u;
  }
  airCurveFor(tr, a, b, dt) {
    const k = 'h' + a.t; if (tr.routeCache.has(k)) return tr.routeCache.get(k);
    const sa = Math.hypot(a.vx, a.vz), sb = Math.hypot(b.vx, b.vz);
    const G = sa > 1 && sb > 1 ? this.flightCurve(tr, [a.px, a.pz], [a.vx / sa, a.vz / sa], sa, [b.px, b.pz], [b.vx / sb, b.vz / sb], sb, dt) : null;
    this.cacheSet(tr, k, G); return G;
  }
  // the air path between two poses (fix round 2): geoHermite, unless its tightest turn needs more than ~30 deg of bank at the
  // flown speed - then a Dubins turn-straight-turn path at a 25-deg-bank radius, lengthened on the initial heading to the
  // length the reported speeds fly (motion.js turnFlight). opt.final: m of straight final into p1 (landings) [inf]
  flightCurve(tr, p0, d0, s0, p1, d1, s1, D, opt = {}) {
    const G = geoHermite(p0, d0, s0, p1, d1, s1, D);
    if (tr.dims && tr.dims.cls === 'heli') return G;
    // (the radius from the speed the path is FLOWN at - a path longer than the reported speeds fly is flown faster, and the
    // bank needed grows with the square of it)
    const vG = Math.max(s0, s1, G.len / D, 20);
    if (!opt.final && !opt.initial && hermiteMaxCurv(G, D) <= GRAV * Math.tan(30 * D2R) / (vG * vG)) return G;
    // (a straight-ahead join - the target lies on the initial heading - needs no Dubins path)
    if ((opt.initial || opt.final) && hermiteMaxCurv(G, D) <= 1e-4) return G;
    if (opt.final === 0) delete opt.final; if (opt.initial === 0) delete opt.initial;
    // bank 25 deg first; when the path is then too long for the hole, 30 and 35 deg and a shorter final [inf]
    let best = null;
    for (const [bank, fs] of [[25, 1], [30, 0.6], [35, 0.35]]) {
      let v = Math.max(s0, s1, 20), F = null;
      // (review round 3: opt.keepInitial / keepFinal - metres of the straight that are never shortened: the reconstructed
      // climb-out and final stay aligned with the runway for the first / last ~12 s)
      const ini = Math.max((opt.initial || 0) * fs, Math.min(opt.initial || 0, opt.keepInitial || 0)), fin = Math.max((opt.final || 0) * fs, Math.min(opt.final || 0, opt.keepFinal || 0));
      for (let it = 0; it < 3; it++) { F = turnFlight(p0, d0, s0, p1, d1, s1, D, Math.max(60, v * v / (GRAV * Math.tan(bank * D2R))), { ...opt, final: fin, initial: ini }); if (!F) break; const v2 = Math.max(s0, s1) * F.k; if (Math.abs(v2 - v) < 1) break; v = v2; }
      if (F && (!best || F.k < best.k)) best = F;
      if (F && F.k <= 1.15) break;
    }
    if (opt.keepInitial || opt.keepFinal) {
      if (best && best.k <= 1.35) return best;
      // (no room for the kept straight at a sane speed: shorten it, down to none - never a path flown at 2-3 x the speed)
      const ki = (opt.keepInitial || 0) * 0.5, kf = (opt.keepFinal || 0) * 0.5;
      if (ki >= 100 || kf >= 100) return this.flightCurve(tr, p0, d0, s0, p1, d1, s1, D, { ...opt, initial: Math.min(opt.initial || 0, Math.max(ki, opt.initial ? 0 : 0)), final: Math.min(opt.final || 0, Math.max(kf, 0)), keepInitial: ki >= 100 ? ki : 0, keepFinal: kf >= 100 ? kf : 0 });
      return this.flightCurve(tr, p0, d0, s0, p1, d1, s1, D, { ...opt, keepInitial: 0, keepFinal: 0 });
    }
    if (best && best.k > 1.35 && (opt.final || opt.initial)) return this.flightCurve(tr, p0, d0, s0, p1, d1, s1, D, { ...opt, final: 0, initial: 0 });   // no room for a final / straight climb-out
    if (!best || best.k > 1.35) return G;
    this.counters.turnFlight = (this.counters.turnFlight || 0) + 1;
    return best;
  }
  cacheSet(tr, k, v) { tr.routeCache.set(k, v); if (tr.routeCache.size > 60) tr.routeCache.delete(tr.routeCache.keys().next().value); }
  // the position a segment starts / ends at: a fix of a still run stands for the run's rest pose (spot pose, median, physics
  // offset) - so leaving a parking spot or arriving at one is continuous with the pose drawn there
  endPt(tr, f) { if (f.ground && f.stillRun) { const P = tr.rests.get(f.stillRun[0]); if (P) return [P.x, P.z]; } return [f.px, f.pz]; }
  // both bracket fixes in the same still run: the run's rest pose
  restTarget(tr, o, a, b) {
    if (!a.stillRun || !b.stillRun || a.stillRun[0] !== b.stillRun[0]) return null;
    const P = this.restOf(tr, a); if (!P) return null;
    tr.restPose = P;
    Object.assign(o, { x: P.x, z: P.z, y: this.groundY(P.x, P.z), vx: 0, vz: 0, vy: 0, gs: 0, ground: true, ex: 0, stop: true, rest: P, hd: P.hdg != null ? P.hdg * D2R : null, mode: 'rest' });
    return o;
  }
  fill(o, r) { Object.assign(o, { x: r.px, z: r.pz, y: r.y, vx: r.vx, vz: r.vz, vy: r.ground ? 0 : (r.vsm || 0), gs: r.gsm, ground: r.ground, hd: r.hdReal ? r.hd : null }); return o; }
  // past the newest fix: dead reckoning with constant turn for DR_MAX_S, then on the ground a smooth stop (sfo3d) and in the
  // air straight and level at constant speed (a fixed-wing aircraft never comes to rest in the air; the track fades out
  // after AIR_HIDE_S, update())
  extrapolate(tr, L, dt, o) {
    o.ex = dt; o.mode = 'extrap';
    // (review round 3, M1) on a runway: the take-off continues (then hidden) or the aircraft rolls off at the exit ahead
    if (L.ground && tr.dims && tr.dims.cls !== 'heli' && !tr.vehicle) { const C = this.runwayCont(tr, L);
      if (C) { const t = L.t + dt * 1000; this.samplePlan(C, Math.min(t, C.t1), o); o.mode = 'cont:' + C.kind + ':' + o.seg; o.ex = dt; o.recon = true; o.route = true;
        if (C.depart && t > C.t1) o.hideSeg = true; return o; } }
    if (L.ground && L.stillRun) { const rt = this.restTarget(tr, o, L, L); if (rt) return rt; }
    if (L.ground) return this.groundStop(tr, L, dt, o);
    // an airborne fixed-wing fix without a usable speed (a first TIS-B / MLAT position, gs missing): no velocity to fly on -
    // not drawn until a second fix gives one (fix round 2: the body circled away from a target standing still in the air)
    if (!tr.vehicle && tr.dims && tr.dims.cls !== 'heli' && !(L.gsm > 5)) o.hideSeg = true;
    let vx = L.vx, vz = L.vz, x = L.px, z = L.pz; const w = L.turn || 0; const t1 = Math.min(dt, DR_MAX_S);
    if (Math.abs(w) > 1e-4) { const sp = Math.hypot(vx, vz), h0 = bearR(vx, vz), h1 = h0 + w * t1; x += sp / w * (Math.cos(h0) - Math.cos(h1)); z -= sp / w * (Math.sin(h1) - Math.sin(h0)); const v = hvR(h1); vx = v[0] * sp; vz = v[1] * sp; }
    else { x += vx * t1; z += vz * t1; }
    const rest = dt - t1;
    if (rest > 0) { if (L.ground) { const k = DR_STOP_TAU_S * (1 - Math.exp(-rest / DR_STOP_TAU_S)); x += vx * k; z += vz * k; const d = Math.exp(-rest / DR_STOP_TAU_S); vx *= d; vz *= d; } else { x += vx * rest; z += vz * rest; } }
    Object.assign(o, { x, z, vx, vz, gs: Math.hypot(vx, vz), ground: L.ground, hd: L.hdReal ? L.hd : null });
    o.y = L.ground ? this.groundY(x, z) : Math.max(this.groundY(x, z) + 0.3, L.y + (L.vsm || 0) * Math.min(dt, 10)); o.vy = L.ground || dt > 10 ? 0 : (L.vsm || 0);
    return o;
  }
  // ---- a silent aircraft on a runway (review round 3, M1). The display has passed the newest fix of a fixed-wing aircraft
  // that is on a runway (rolling, or standing lined up): it is never left standing there. Either it was taking off - lined up,
  // accelerating, at >= 0.9 VR, or a pattern aircraft (a touch-and-go / low pass in the last 30 min) last heard airborne at
  // >= 0.6 VR over the runway - and the take-off continues: the roll on the centreline at the type's take-off acceleration,
  // lift-off at VR inside the runway, 20 s of straight climb-out, then the aircraft is hidden (departed, no signal; drawn again
  // when it is heard). Or it was landing / moving along the runway: it brakes on the centreline (<= 2 m/s2 GA, 2.5 others) to
  // the first exit ahead it can make and rolls off until it is clear of the runway (TaxiNet.exitPath), where groundLost keeps
  // it ('No signal'). [inf: every rule; review round 3 found a silent C172 drawn stopped ON 28L and another landing through it]
  runwayCont(tr, L) {
    const k = 'rc' + L.t; if (tr.routeCache.has(k)) return tr.routeCache.get(k);
    let P = null; try { P = this.planRunwayCont(tr, L); } catch (e) { P = null; if (this.debugCuts) console.error(e); }
    this.cacheSet(tr, k, P); if (P) this.counters['silentRunway_' + P.kind] = (this.counters['silentRunway_' + P.kind] || 0) + 1; return P;
  }
  runwayAt(x, z, m = 3) {
    for (const r of (this.site && this.site.runways) || []) { const px = x - r.origin[0], pz = z - r.origin[1], al = px * r.dir[0] + pz * r.dir[1], ac = px * r.right[0] + pz * r.right[1];
      if (al >= -5 && al <= r.length + 5 && Math.abs(ac) <= r.halfWidth + m) return { r, al, ac }; }
    return null;
  }
  planRunwayCont(tr, L) {
    const T = tr.dims; if (!T || T.cls === 'heli' || tr.vehicle || !this.site || !this.net.ok) return null;
    if (Math.hypot(L.px, L.pz) > GROUND_VIEW_M) return null;
    const RW = this.runwayAt(L.px, L.pz, 3); if (!RW) return null;
    const { r } = RW, SP = this.spd(tr), moving = L.gsm > 1.5;
    const h = moving ? L.dir : (L.hdReal ? L.hd : (L.hd ?? L.dir));
    const hR = bearR(r.dir[0], r.dir[1]); let sgn = h != null ? (Math.cos(h - hR) >= 0 ? 1 : -1) : (this.classifier.flow.end === '10' ? 1 : -1);
    const aligned = h != null && Math.abs(Math.cos(h - hR)) > Math.cos(25 * D2R);
    const i = tr.fx.indexOf(L), prev = i > 0 ? tr.fx[i - 1] : null;
    const dv = prev && prev.ground && L.t - prev.t < 20000 && L.t > prev.t ? (L.gsm - (prev.gsm || 0)) / ((L.t - prev.t) / 1000) : 0;
    const pattern = tr.patternT != null && L.t - tr.patternT < 1800e3;
    const vAl = moving ? L.gsm * Math.abs(Math.cos(h - hR)) : 0;
    const depart = (!moving && aligned && (L.ph === 'line_up' || L.ph === 'takeoff_roll')) || (moving && aligned && (vAl >= 0.9 * SP.vr || (dv > 0.3 && vAl > 8) || (!L.g && pattern && vAl >= 0.6 * SP.vr)));
    const al0 = clamp(RW.al, 0, r.length), left = (al) => sgn > 0 ? r.length - al : al, A0 = this.axisPt(r, al0), dirR = [r.dir[0] * sgn, r.dir[1] * sgn];
    if (depart) {
      const v0 = Math.min(vAl, SP.vr), acc = SP.accTO; let d = Math.max(0, (SP.vr * SP.vr - v0 * v0) / (2 * acc));
      d = Math.max(Math.min(d, left(al0) - 30), 0);
      const accE = d > 1 ? Math.max(0, (SP.vr * SP.vr - v0 * v0) / (2 * d)) : 0, tR = accE > 0 ? (SP.vr - v0) / accE : 0, LO = this.axisPt(r, al0 + sgn * d), segs = [];
      if (tR > 0.05) segs.push({ kind: 'roll', t0: L.t, t1: L.t + tR * 1000, R: polyOf([A0, this.axisPt(r, al0 + sgn * (d + 1))]), s0: 0, v0, acc: accE, takeoff: true });
      const tA = 20, v2 = 1.2 * SP.vr, len = (SP.vr + v2) / 2 * tA, P1 = [LO[0] + dirR[0] * len, LO[1] + dirR[1] * len], gy = this.groundY(LO[0], LO[1]), t1 = L.t + tR * 1000;
      segs.push({ kind: 'air', t0: t1, t1: t1 + tA * 1000, C: geoHermite(LO, dirR, SP.vr, P1, dirR, v2, tA), y0: gy, y1: gy + SP.climb * 0.8 * tA, vy0: SP.climb * 0.5, vy1: SP.climb * 0.8 });
      return { segs, kind: 'depart', depart: true, rwy: r.id, t0: L.t, t1: t1 + tA * 1000, recon: true };
    }
    // the exit ahead: the first exit junction the aircraft can brake to (to <= 6 m/s), then out along its link until clear
    const vR = Math.max(vAl, moving ? 1.5 : 0), dec = T.cls === 'jet' || T.cls === 'turboprop' ? 2.5 : 2.0, dMin = Math.max(5, (vR * vR - 36) / (2 * dec));
    const EX = this.net.exitsOf(r).filter(e => (e.al - al0) * sgn >= dMin).sort((p, q) => (p.al - q.al) * sgn);
    for (const e of EX) {
      let best = null; for (const Lk of e.out) { const X = this.net.exitPath(r, e, Lk, T.L); if (!X) continue; let len = 0; for (let q = 1; q < X.length; q++) len += Math.hypot(X[q][0] - X[q - 1][0], X[q][1] - X[q - 1][1]); if (!best || len < best.len) best = { X, len }; }
      if (!best) continue;
      const pts = [A0, ...(Math.abs(e.al - al0) > 1 ? [[e.x, e.z]] : []), ...best.X.slice(1)];
      const G = this.profiled(tr, pts, 1e-3, null, null, 'exit', true, { v0: vR, v1: 0, rwyHead: Math.abs(e.al - al0) });
      if (!G) continue;
      return { segs: [{ kind: 'prof', t0: L.t, t1: L.t + G.P.tmin * 1000, G }], kind: 'exit', rwy: r.id, t0: L.t, t1: L.t + G.P.tmin * 1000, recon: true };
    }
    return null;
  }
  // past the newest GROUND fix (fix round 2): a braking stop straight ahead from the fix's speed - taxi deceleration at taxi
  // speeds, LIM.rollDec on a roll [inf] - that ends before the centre would leave the pavement (sfo3d dead-reckoned 5 s and
  // then stopped with tau 3 s: ~8 s of travel, 45 m at 11 kt, onto the grass; and the signal-loss pose then jumped back)
  groundStop(tr, L, dt, o) {
    const v0 = L.gsm || 0, x0 = L.px, z0 = L.pz;
    if (v0 < 0.3) { const hd = L.hdReal ? L.hd : (L.gsm > 0.5 ? L.dir : L.hd); const R = L._dsRest || (L._dsRest = { x: x0, z: z0, hdg: hd != null ? toDeg(hd) : 0, planned: true });
      Object.assign(o, { x: x0, z: z0, y: this.groundY(x0, z0), vx: 0, vz: 0, vy: 0, gs: 0, ground: true, hd, stop: true, rest: R }); return o; }
    const k = 'ds' + L.t; let C = tr.routeCache.get(k);
    if (!C) {
      const ux = L.vx / v0, uz = L.vz / v0, dec = v0 > TAXI_BODY_MAX ? LIM.rollDec : LIM.taxiDec;
      let sMax = v0 * v0 / (2 * dec);
      if (this.site) for (let sq = 2; sq <= sMax + 2; sq += 2) { if (!this.paved(x0 + ux * sq, z0 + uz * sq)) { sMax = Math.max(0, sq - 4); break; } }
      const decE = sMax > 0.1 ? v0 * v0 / (2 * sMax) : 1e9;          // the deceleration that stops within sMax
      C = { ux, uz, dec: Math.max(dec, decE), sMax }; this.cacheSet(tr, k, C);
    }
    const tS = v0 / C.dec, tt = Math.min(dt, tS), s = Math.min(C.sMax, v0 * tt - 0.5 * C.dec * tt * tt), v = Math.max(0, v0 - C.dec * tt);
    const x = x0 + C.ux * s, z = z0 + C.uz * s;
    Object.assign(o, { x, z, y: this.groundY(x, z), vx: C.ux * v, vz: C.uz * v, vy: 0, gs: v, ground: true, hd: v < 0.05 ? bearR(C.ux, C.uz) : (L.hdReal ? L.hd : null), stop: v < 0.05 });
    if (v < 0.05) o.rest = C.rest || (C.rest = { x, z, hdg: toDeg(bearR(C.ux, C.uz)), planned: true });
    return o;
  }
  // ---- ground paths across a hole: a taxi-graph route (or a paved chord) with a drivable speed profile (motion.js)
  //   {kind: 'route'|'chord', R, P (profile), t0}  |  {kind: 'hold', x, z, hd}   (cached per segment)
  groundPathFor(tr, a, b, dt) {
    const k = 'g' + a.t; if (tr.routeCache.has(k)) return tr.routeCache.get(k);
    const span = tr.dims ? tr.dims.span : null;
    const onRwy = !!(a.strip || b.strip);
    const A0 = this.endPt(tr, a), B0 = this.endPt(tr, b), chord = Math.hypot(B0[0] - A0[0], B0[1] - A0[1]);
    const h0 = a.gsm > 0.5 ? a.dir : (a.hdReal ? a.hd : null), h1 = b.gsm > 0.5 ? b.dir : (b.hdReal ? b.hd : null);
    let G = null, why = null;
    // (review round 3, M2) a roll on a runway stays on THAT runway until it has slowed to an exit (rollExitRoute)
    const RWa = !tr.vehicle && tr.dims && tr.dims.cls !== 'heli' && a.gsm > TAXI_V ? this.runwayAt(A0[0], A0[1], 5) : null;
    if (RWa) { const X = this.rollExitRoute(tr, a, b, dt, RWa, A0, B0); if (X) { if (X.kind === 'late') return this.cacheSet(tr, k, X), X; this.counters.rollExit = (this.counters.rollExit || 0) + 1; this.cacheSet(tr, k, X); return X; } }
    const block = this.routeBlock(tr);
    let R = this.net.routeXY(A0[0], A0[1], h0, B0[0], B0[1], h1, { span, runway: onRwy, v0: a.gsm, v1: b.gsm, noRunway: !!RWa, block });
    if (!R) R = this.net.routeXY(A0[0], A0[1], h0, B0[0], B0[1], h1, { span: null, runway: true, far: true, v0: a.gsm, v1: b.gsm, block });   // relaxed: no span limit, runway links, 60 m
    const long = R && R.len > ROUTE_RATIO * chord + ROUTE_EXTRA_M;
    if (!R) why = 'routeNone';
    else if (!long) {
      G = this.profiled(tr, R.pts, dt, a, b, 'route');
      if (!G) { G = this.profiled(tr, R.pts, dt, a, b, 'route', false, { taxiV: TAXI_V_FAST }); if (G) this.counters.routeFastTaxi = (this.counters.routeFastTaxi || 0) + 1; }
      if (!G) why = 'routeTooFast';
    } else why = 'routeTooLong';
    // no drivable route: the straight chord only where all of it is paved and clear of buildings (an apron), never across grass
    if (!G && this.chordClear(tr, A0, B0)) { G = this.profiled(tr, [A0, B0], dt, a, b, 'chord', true); }
    // a route that is too long or too fast for the hole is still driven (faster than the taxi limits) rather than a chord across
    // grass or a jump: the taxi graph may miss the connector the aircraft used [inf]
    // (review round 3, M2: never above TAXI_BODY_MAX - the forced profile is driven at most 25 kt; not for a roll on a runway)
    let fScale = null;
    if (!G && !RWa && R && R.len <= 3.5 * chord + 150) { const Gf = this.profiled(tr, R.pts, dt, a, b, 'route', true, { taxiV: TAXI_V }); fScale = Gf.P.scale; if (Gf.P.scale <= TAXI_BODY_MAX / TAXI_V) { G = Gf; G.forced = true; this.counters.routeForced = (this.counters.routeForced || 0) + 1; } }
    // (review round 3) still nothing: the aircraft is drawn LATE - it drives the route at taxi speed and joins its track at a
    // later ground fix it can reach in time (tr.xplan), instead of a hold and a re-placement
    if (!G && !tr.vehicle && tr.dims && tr.dims.cls !== 'heli') { const X = this.lateGround(tr, a, b, A0, h0, span); if (X) { this.cacheSet(tr, k, X); return X; } }
    // nothing drivable: hold at the first fix and be re-placed at the second (a fade, counted as a re-placement)
    if (this.debugPlan && !G) console.log('groundPathFor', JSON.stringify({ why, t: a.t, chord: +chord.toFixed(0), dt, R: R ? +R.len.toFixed(0) : null, v0: +a.gsm.toFixed(1), v1: +b.gsm.toFixed(1), onRwy, fScale }));
    if (!G) { G = { kind: 'hold', x: A0[0], z: A0[1], hd: a.hdReal ? a.hd : (a.gsm > 0.5 ? a.dir : null) }; this.counters.routeHold = (this.counters.routeHold || 0) + 1; }
    if (why) this.counters[why] = (this.counters[why] || 0) + 1;
    if (G.kind === 'route') this.counters.routes++; else this.counters.routeFallback++;
    this.cacheSet(tr, k, G); return G;
  }
  // a fixed-wing fix rolling on runway RW (review round 3, M2): the roll continues on the centreline - never faster than at a -
  // and turns off at an exit ahead it can brake to (<= 3 m/s2 to 7 m/s), then taxis to b on taxiways (no running along any
  // runway: noRunway); b still on this runway ahead: the roll runs along the axis to it. The exit whose drive fits the hole
  // best wins; none fits: a late join (lateGround) -> a profiled path | null
  rollExitRoute(tr, a, b, dt, RW, A0, B0) {
    const r = RW.r, T = tr.dims, hR = bearR(r.dir[0], r.dir[1]), sgn = Math.cos(a.dir - hR) >= 0 ? 1 : -1, al0 = clamp(RW.al, 0, r.length);
    const v0 = a.gsm * Math.abs(Math.cos(a.dir - hR)), Ax = this.axisPt(r, al0);
    const RWb = this.runwayAt(B0[0], B0[1], 5), h1 = b.gsm > 0.5 ? b.dir : (b.hdReal ? b.hd : null);
    if (RWb && RWb.r === r && (RWb.al - al0) * sgn > 0) {     // still on this runway, ahead: along the axis
      const Bx = this.axisPt(r, clamp(RWb.al, 0, r.length)), pts = [Ax, Bx]; if (Math.hypot(B0[0] - Bx[0], B0[1] - Bx[1]) > 3) pts.push(B0);
      const G = this.profiled(tr, pts, dt, a, b, 'route', false, { rwyHead: 1e9, v0 }); if (G) return G;
    }
    const dMin = Math.max(5, (v0 * v0 - 49) / (2 * 3.0)), C = [], blk = this.routeBlock(tr);
    for (const e of this.net.exitsOf(r)) {
      const d = (e.al - al0) * sgn; if (d < dMin) continue;
      const R = this.net.routeFrom(e.n, B0[0], B0[1], h1, { span: T.span, noRunway: true, block: blk }); if (!R) continue;
      const pts = [Ax, [e.x, e.z], ...R.pts.slice(1)];
      const G = this.profiled(tr, pts, dt, a, b, 'route', true, { rwyHead: d, v0 }); if (!G) continue;
      C.push({ G, d, tmin: G.P.tmin, len: G.R.len });
    }
    if (!C.length) return null;
    const ok = C.filter(c => c.tmin <= dt * 1.05); if (ok.length) { ok.sort((p, q) => p.len - q.len); return ok[0].G; }
    return this.lateGround(tr, a, b, A0, a.dir, T.span, C.sort((p, q) => p.tmin - q.tmin)[0].G.R.pts);
  }
  // late join on the ground: the route from a (or the given polyline start) to a LATER known ground fix c whose drive at taxi
  // speed fits [a.t, c.t]; drawn as tr.xplan (inferred) -> { kind: 'late' } | null
  lateGround(tr, a, b, A0, h0, span, head = null) {
    const i = tr.fx.indexOf(b); if (i < 0) return null;
    for (let j = i + 1; j < tr.fx.length && j < i + 40; j++) {
      const c = tr.fx[j]; if (!c.ground) return null; const D = (c.t - a.t) / 1000; if (D > 240) return null;
      const C0 = this.endPt(tr, c), hc = c.gsm > 0.5 ? c.dir : (c.hdReal ? c.hd : null);
      let pts = null;
      if (head) { const e = head[head.length - 1], R = this.net.routeXY(e[0], e[1], null, C0[0], C0[1], hc, { span, noRunway: true }); if (R) pts = head.concat(R.pts.slice(1)); }
      else { const R = this.net.routeXY(A0[0], A0[1], h0, C0[0], C0[1], hc, { span, runway: true, v0: a.gsm, v1: c.gsm }); if (R) pts = R.pts; }
      if (!pts) continue;
      const RW0 = this.runwayAt(A0[0], A0[1], 5), G = this.profiled(tr, pts, D, a, c, 'route', false, RW0 && a.gsm > TAXI_V ? { rwyHead: head ? Math.hypot(head[1][0] - head[0][0], head[1][1] - head[0][1]) : undefined } : {});
      if (!G) continue;
      tr.xplan = { segs: [{ kind: 'prof', t0: a.t, t1: c.t, G }], kind: 'ground', t0: a.t, t1: c.t, recon: true, late: true };
      this.counters.groundLate = (this.counters.groundLate || 0) + 1;
      return { kind: 'late' };
    }
    return null;
  }
  // the aircraft standing on the ground that a taxi route of tr must not drive through (review round 3, m4: routes went through
  // parked aircraft): parked, resting or silent ones. -> a routing-link penalty (Dijkstra opt.block) of 2,000 m for a link along
  // which tr's planform would come within 0.3 m of one of them - avoided when any other way exists [inf]
  routeBlock(tr) {
    if (!tr.dims || tr.vehicle) return null;
    const obs = []; for (const q of this.tracks.values()) {
      if (q === tr || !q.dims || q.vehicle || !q.disp.valid || !q.disp.ground || q.hidden || q.staleAir || (q.park && q.park.inside) || !(q.disp.alpha > 0.01)) continue;
      if (!(q.stale || q.restPose || (q.disp.gs || 0) < 0.3)) continue;
      obs.push(bodyOf(q.dims, q.disp.x, q.disp.z, q.disp.hdg));
    }
    if (!obs.length) return null;
    const T = tr.dims, R0 = Math.max(T.L, T.span) / 2, cache = new Map();
    return (L) => {
      let v = cache.get(L.i); if (v != null) return v; v = 0;
      for (let k = 1; k < L.pts.length && !v; k++) { const a = L.pts[k - 1], b = L.pts[k], d = Math.hypot(b[0] - a[0], b[1] - a[1]), n = Math.max(1, Math.ceil(d / 2)), h = toDeg(bearR(b[0] - a[0], b[1] - a[1]));
        for (let q = 0; q <= n && !v; q++) { const x = a[0] + (b[0] - a[0]) * q / n, z = a[1] + (b[1] - a[1]) * q / n;
          for (const O of obs) { if (Math.hypot(x - O.x, z - O.z) > R0 + Math.max(O.T.L, O.T.span) / 2 + 1) continue; if (overlaps(bodyOf(T, x, z, h), O, 0.3)) { v = 2000; break; } } } }
      cache.set(L.i, v); return v;
    };
  }
  chordClear(tr, A, B) {
    const L = Math.hypot(B[0] - A[0], B[1] - A[1]), n = Math.max(2, Math.ceil(L / 2)), hw = tr.dims ? tr.dims.track / 2 + 0.3 : 1.5;
    const ux = (B[0] - A[0]) / (L || 1), uz = (B[1] - A[1]) / (L || 1), rx = -uz, rz = ux;
    for (let i = 0; i <= n; i++) { const x = A[0] + (B[0] - A[0]) * i / n, z = A[1] + (B[1] - A[1]) * i / n;
      for (const s of [-hw, 0, hw]) { const px = x + rx * s, pz = z + rz * s; if (!this.paved(px, pz) || (this.site && this.site.building(px, pz))) return false; } }
    return true;
  }
  // a polyline driven between two ground fixes (or plan points) in D seconds: corners filleted on pavement, speed profile with
  // the end speeds; null when it cannot be driven in D (unless force)
  profiled(tr, pts, D, a, b, kind, force = false, o2 = {}) {
    // an arc point is acceptable when both main wheels (track / 2 + 0.3 m either side of the path) are on pavement and nothing
    // of the centre is in a building
    const hw = tr.dims ? tr.dims.track / 2 + 0.3 : 1.5, hs = tr.dims ? tr.dims.span / 2 + 0.5 : 6;
    const bld = (x, z) => this.site && this.site.building(x, z);
    const ok = (x, z, tx = 0, tz = 0) => this.paved(x, z) && this.paved(x - tz * hw, z + tx * hw) && this.paved(x + tz * hw, z - tx * hw) && !bld(x, z) && !bld(x - tz * hs, z + tx * hs) && !bld(x + tz * hs, z - tx * hs);   // wheels on pavement, wingtips clear of buildings
    // the short lateral connectors of a projected route (fix -> centreline, a few m at 90 deg) are merged: the aircraft joins
    // the line at an angle instead of stopping for two right-angle turns
    pts = pts.slice();
    const turn = (p, q, r) => Math.abs(wrapPi(bearR(r[0] - q[0], r[1] - q[1]) - bearR(q[0] - p[0], q[1] - p[1])));
    const dd = (p, q) => Math.hypot(p[0] - q[0], p[1] - q[1]);
    // a fast fix on a runway strip (a roll) stands for its point on the centreline: the roll is drawn on the axis, not as a
    // kink to a GNSS position 12 m beside it (the next segment continues from the fix; the body absorbs the offset)
    const snap = (p, f) => { if (!f || !(f.gsm > TAXI_V) || !(f.strip || f.rwy)) return p; const B = this.rwyFor(p[0], p[1], null, 30); return B ? this.axisPt(B.r, clamp(B.al, 0, B.r.length)) : p; };
    pts[0] = snap(pts[0], a); pts[pts.length - 1] = snap(pts[pts.length - 1], b);
    // (a fix moving faster than 5 m/s merges over up to 25 m: a roll fix 12 m off the centreline is not reached by a right angle)
    const L0 = a && a.gsm > 5 ? 25 : 10, L1 = b && b.gsm > 5 ? 25 : 10;
    while (pts.length > 2 && ((dd(pts[1], pts[0]) < L0 && turn(pts[0], pts[1], pts[2]) > 30 * D2R) || (dd(pts[1], pts[0]) < 25 && turn(pts[0], pts[1], pts[2]) > 120 * D2R))) pts.splice(1, 1);
    while (pts.length > 2) { const m = pts.length; const l = dd(pts[m - 1], pts[m - 2]), tn = turn(pts[m - 3], pts[m - 2], pts[m - 1]); if ((l < L1 && tn > 30 * D2R) || (l < 25 && tn > 120 * D2R)) pts.splice(m - 2, 1); else break; }
    const R = polyOf(filletPath(pts, FILLET_M, ok));
    // the fix's speed along the path's direction near the end it is at (a fix moving against it: 0, a turn-around)
    const along = (f, at, sg) => { if (!f || !(f.gsm > 0.3)) return 0; let best = 0; for (const d of [2, 8, 15]) { const p = polyAt(R, clamp(at + sg * d, 0, R.len)); const c = Math.cos(f.dir - bearR(p.ux, p.uz)); best = Math.max(best, c); } return best > 0.5 ? f.gsm * best : 0; };
    const v0 = o2.v0 ?? along(a, 0, 1), v1 = o2.v1 ?? along(b, R.len, -1);
    const TV = o2.taxiV || TAXI_V;
    // speed caps: a runway part at the start (a roll-out) or the end keeps its speed; elsewhere TAXI_V
    let sR0 = -1, sR1 = R.len + 1;
    // (review round 3, M2: the head is the runway the roll is ON - a route that turned off it onto the infield taxiway and ran
    // down the other runway kept the roll-out speed all the way)
    const RW0 = a && a.strip && v0 > TAXI_V ? this.runwayAt(pts[0][0], pts[0][1], 15) : null;
    const onR0 = (x, z) => { const r = RW0.r, px = x - r.origin[0], pz = z - r.origin[1], al = px * r.dir[0] + pz * r.dir[1], ac = px * r.right[0] + pz * r.right[1]; return al >= -30 && al <= r.length + 30 && Math.abs(ac) <= r.halfWidth + 5; };
    if (o2.rwyHead != null) sR0 = o2.rwyHead; else if (RW0) { for (let s = 0; s <= R.len; s += 4) { const p = polyAt(R, s); if (!onR0(p.x, p.z)) break; sR0 = s; } }
    if (o2.rwyTail != null) sR1 = o2.rwyTail; else if (b && b.strip && v1 > TAXI_V) { for (let s = R.len; s >= 0; s -= 4) { const p = polyAt(R, s); if (!this.onRunway(p.x, p.z, 15)) break; sR1 = s; } }
    const cls = tr.dims ? tr.dims.cls : 'unknown';
    // (fix round 2) a roll-out that continues along runway pavement further on (the route crosses to or follows another runway,
    // or runs back onto this one): those runway stretches keep up to the roll-out speed (<= 20 m/s, ~39 kt) too - the taxi cap
    // made a landing that rolled to the far end of the runway undrivable in its hole [inf]
    // (review round 3, M2: no later runway stretch keeps roll speed - a roll stays on its runway until it has slowed to an exit,
    // rollExitRoute; anything after the head is taxiing)
    const rwyS = null, vRw = Math.min(v0, 20);
    // (the profile accelerates at 0.8 x the body's limit, so a body that fell behind can catch up on the way)
    const opt = { acc: 0.8 * (v1 > TAXI_V ? (LIM.rollAcc[cls] || 2.5) : LIM.taxiAcc), dec: v0 > TAXI_V ? (cls === 'jet' || cls === 'turboprop' ? 3.0 : 2.5) : LIM.taxiDec, lat: LIM.latGround, w: LIM.wGround * D2R, pivotW: LIM.wPivot * D2R, vTyp: TAXI_TYP,
      cap: (s) => (s <= sR0 ? Math.max(TV, v0) : s >= sR1 ? Math.max(TV, v1) : rwyS && rwyS[Math.min(rwyS.length - 1, Math.round(s / 4))] && rwyS[Math.min(rwyS.length - 1, Math.round((s + 8) / 4))] ? Math.max(TV, vRw) : TV) };
    const P = profilePath(R, D, v0, v1, opt);
    if (!P.feasible && !force) return null;
    return { kind, R, P, t0: a ? a.t : 0, v0, v1 };
  }
  onRunway(x, z, m = 3) { for (const r of (this.site && this.site.runways) || []) { const px = x - r.origin[0], pz = z - r.origin[1]; const al = px * r.dir[0] + pz * r.dir[1], ac = px * r.right[0] + pz * r.right[1]; if (al >= -30 && al <= r.length + 30 && Math.abs(ac) <= r.halfWidth + m) return true; } return false; }
  sampleGround(G, tRel, o) {
    o.ex = 0; o.route = true; o.hd = null;
    if (G.kind === 'hold') { Object.assign(o, { x: G.x, z: G.z, y: this.groundY(G.x, G.z), vx: 0, vz: 0, vy: 0, gs: 0, ground: true, stop: true, hd: G.hd, rest: G.rest || (G.rest = { x: G.x, z: G.z, hdg: G.hd != null ? toDeg(G.hd) : 0, planned: true }) }); return o; }
    const q = profAt(G.P, tRel), p = polyAt(G.R, q.s);
    Object.assign(o, { x: p.x, z: p.z, y: this.groundY(p.x, p.z), vx: p.ux * q.v, vz: p.uz * q.v, vy: 0, gs: q.v, ground: true, hd: q.v < 0.05 ? bearR(p.ux, p.uz) : null });
    // a planned stop (the profile's wait) is a rest pose too: GroundPhysics places it on pavement and clear of the others
    if (q.v < 0.05) { o.stop = true; const k = Math.round(q.s); if (!G.rests) G.rests = new Map(); let P = G.rests.get(k); if (!P) G.rests.set(k, P = { x: p.x, z: p.z, hdg: toDeg(bearR(p.ux, p.uz)), planned: true }); o.rest = P; }
    return o;
  }
  // ---- take-off / landing in a hole: a timed plan of segments
  //   {kind: 'wait', t0, t1, x, z, hd} | {kind: 'prof', t0, t1, G (profiled ground path)} | {kind: 'roll', t0, t1, R, s0, v0, acc}
  //   | {kind: 'air', t0, t1, C (geoHermite), y0, y1, vy0, vy1}
  // Values [inf, GA]: lift-off at VLOF (speedsOf: 0.85 x the ACD approach speed), roll acceleration LIM.rollAcc (stretched
  // down to ROLL_ACC_MIN when the hole leaves spare time on a rolling start), touchdown 150 m past the landing threshold at
  // 0.95 x the approach speed, roll-out braking 2.5 m/s2 to the exit, taxi TAXI_V.
  transitionFor(tr, a, b, dt) {
    const k = 'x' + a.t; if (tr.routeCache.has(k)) return tr.routeCache.get(k);
    let P = null;
    const Gf = a.ground ? a : b, far = Math.hypot(Gf.px, Gf.pz) > GROUND_VIEW_M;    // where the ground part is: OAK or HWD
    if (!far) { try { P = a.ground ? this.planTakeoff(tr, a, b, dt) : this.planLanding(tr, a, b, dt); } catch (e) { P = null; if (this.debugCuts) console.error(e); } }
    else { P = this.farTransition(tr, a, b, dt); this.counters.transitionFar = (this.counters.transitionFar || 0) + 1; this.cacheSet(tr, k, P); return P; }
    if (P && P.recon) tr.xplan = P;   // (review round 3: a reconstruction may run past b - target() follows it until it joins)
    // (review round 3, M3) a take-off that no runway explains (or that cannot be drawn on one) is NOT drawn rolling or lifting
    // off anywhere else: the aircraft stays hidden until its first airborne fix and appears there, at its reported height
    if (!P && a.ground) { P = { segs: [{ kind: 'wait', t0: a.t, t1: b.t, x: a.px, z: a.pz, hd: a.dir }], kind: 'takeoff', rwy: null, hidden: true, fallback: true, t0: a.t, t1: b.t };
      this.counters.takeoffHidden = (this.counters.takeoffHidden || 0) + 1; this.cacheSet(tr, k, P); return P; }
    if (P) this.counters.transitionPlans = (this.counters.transitionPlans || 0) + 1;
    else {
      // (fix round 2) no full plan (or away from HWD: OAK, no pavement model): the aligned fallback - a final straight along
      // the runway / the roll direction, touchdown past the threshold, a roll to the ground fix (or the mirror for a take-off);
      // before, a straight chord from a base-leg fix to the runway (24-28 deg off it), or a hidden segment at OAK
      try { P = this.fallbackTransition(tr, a, b, dt, far); } catch (e) { P = null; if (this.debugCuts) console.error(e); }
      this.counters[P ? 'transitionFallback' : 'transitionLinear'] = (this.counters[P ? 'transitionFallback' : 'transitionLinear'] || 0) + 1;
    }
    this.cacheSet(tr, k, P); return P;
  }
  // a take-off / landing away from HWD (OAK, 7-10 km; no runway or pavement model, ground bodies are not drawn there): the
  // approach is drawn along the reported track (geoHermite from the approach fix to the touchdown point on the roll fix's own
  // line, back from it by the braking distance) and the body fades out at touchdown; a departure fades in at lift-off, on the
  // reported climb-out track back from the airborne fix (fix round 2: the whole segment was hidden - arrivals vanished at
  // 125-460 ft on short final) [inf: 1.5 m/s2 braking, lift-off at VLOF]
  farTransition(tr, a, b, dt) {
    const T = tr.dims, SP = this.spd(tr), land = !a.ground, G = land ? b : a, A = land ? a : b;
    const sA = Math.max(A.gsm || 0, 10), gv = G.gsm || 0, ch = Math.hypot(A.px - G.px, A.pz - G.pz);
    const dirA = [A.vx / sA, A.vz / sA];
    const segs = [];
    if (land) {
      const dir = gv > 3 ? hvR(G.dir) : dirA, vtd = clamp(Math.min(sA, SP.vtd), SP.vr, SP.vtd * 1.3);
      const dRoll = Math.min(Math.max(0, (vtd * vtd - gv * gv) / 3), 0.4 * ch), tRoll = Math.min(0.5 * dt, dRoll > 0.5 ? 2 * dRoll / Math.max(1, vtd + gv) : 0);
      const TD = [G.px - dir[0] * dRoll, G.pz - dir[1] * dRoll], tTD = b.t - tRoll * 1000;
      segs.push({ kind: 'air', t0: a.t, t1: tTD, C: geoHermite([a.px, a.pz], dirA, sA, TD, dir, vtd, (tTD - a.t) / 1000), y0: a.y, y1: this.groundY(TD[0], TD[1]), vy0: a.vsm || -3, vy1: -1.0 });
      if (tRoll > 0) segs.push({ kind: 'roll', t0: tTD, t1: b.t, R: polyOf([TD, [G.px, G.pz]]), s0: 0, v0: vtd, acc: (gv - vtd) / tRoll, landing: true });
    } else {
      const vlo = Math.max(SP.vr, Math.min(sA, SP.vr * 1.3)), tAir = Math.min(0.6 * dt, 25), dAir = tAir * (vlo + sA) / 2;
      const LO = [b.px - dirA[0] * dAir, b.pz - dirA[1] * dAir], tLO = b.t - tAir * 1000;
      segs.push({ kind: 'wait', t0: a.t, t1: tLO, x: LO[0], z: LO[1], hd: bearR(dirA[0], dirA[1]) });
      segs.push({ kind: 'air', t0: tLO, t1: b.t, C: geoHermite(LO, dirA, vlo, [b.px, b.pz], dirA, sA, tAir), y0: this.groundY(LO[0], LO[1]), y1: b.y, vy0: 1.5, vy1: b.vsm || 0 });
    }
    return { segs, kind: land ? 'landing' : 'takeoff', rwy: null, far: true, fallback: true };
  }
  // the fallback ground <-> air plan: runway axis from the runway beside the ground fix (or, away from HWD, the ground fix's
  // own direction of motion); roll at 1.5 m/s2 braking / the class take-off acceleration [inf]; P.far: the ground part is not
  // drawn (target() fades the body at touchdown / until lift-off)
  fallbackTransition(tr, a, b, dt, far) {
    const T = tr.dims, SP = this.spd(tr), land = !a.ground, G = land ? b : a, A = land ? a : b;
    const Gp = this.endPt(tr, G), gv = G.gsm || 0;
    let dir = null, r = null, sgn = 1, thrAl = null;
    if (!far) { const B = this.rwyFor(Gp[0], Gp[1], gv > 3 ? G.dir : null, 120) || this.rwyFor(Gp[0], Gp[1], null, 600); if (B) { r = B.r; sgn = gv > 3 ? B.sgn : Math.sign(((A.px - Gp[0]) * r.dir[0] + (A.pz - Gp[1]) * r.dir[1]) * (land ? -1 : 1)) || 1; dir = [r.dir[0] * sgn, r.dir[1] * sgn];
      const endName = sgn > 0 ? r.id.split('/')[0] : r.id.split('/')[1]; thrAl = sgn > 0 ? thrDispM(endName) : r.length - thrDispM(endName); } }
    if (!dir) { if (gv > 3) dir = hvR(G.dir); else { const dx = (land ? Gp[0] - A.px : A.px - Gp[0]), dz = (land ? Gp[1] - A.pz : A.pz - Gp[1]), l = Math.hypot(dx, dz) || 1; dir = [dx / l, dz / l]; } }
    const ch = Math.hypot(A.px - Gp[0], A.pz - Gp[1]);
    const sA = Math.max(A.gsm || 0, 10), vfly = land ? clamp(Math.min(A.gsm, SP.vtd), SP.vr, SP.vtd * 1.3) : Math.max(SP.vr, gv);
    const acc = land ? 1.5 : (LIM.rollAcc[T.cls] || 2.5);
    let dRoll = Math.max(0, (vfly * vfly - gv * gv) / (2 * acc));
    dRoll = Math.min(dRoll, 0.45 * ch);
    if (r && thrAl != null && land) {   // touchdown past the landing threshold (+ 30 m) when the ground fix allows it
      const alG = (Gp[0] - r.origin[0]) * r.dir[0] + (Gp[1] - r.origin[1]) * r.dir[1], room = (alG - thrAl) * sgn - 30;
      dRoll = Math.max(0, Math.min(dRoll, room));
    }
    let E = land ? [Gp[0] - dir[0] * dRoll, Gp[1] - dir[1] * dRoll] : [Gp[0] + dir[0] * dRoll, Gp[1] + dir[1] * dRoll];   // touchdown / lift-off point
    let rollPts = land ? [E, Gp] : [Gp, E];
    // on a runway the roll runs ON ITS AXIS (fix round 2: a roll parallel to the runway through a ground fix on a taxiway beside
    // it crossed 11-30 m of grass), joined to a ground fix beside the runway by a taxi route
    if (r) {
      const alOf = (p) => (p[0] - r.origin[0]) * r.dir[0] + (p[1] - r.origin[1]) * r.dir[1];
      const alG = clamp(alOf(Gp), 0, r.length), X = this.axisPt(r, alG), hR = bearR(dir[0], dir[1]);
      let exit = [];
      if (Math.hypot(Gp[0] - X[0], Gp[1] - X[1]) > 5) { const R = land ? this.net.routeXY(X[0], X[1], hR, Gp[0], Gp[1], gv > 0.5 ? G.dir : null, { span: T.span, runway: true }) : this.net.routeXY(Gp[0], Gp[1], gv > 0.5 ? G.dir : null, X[0], X[1], hR, { span: T.span, runway: true });
        exit = R ? R.pts : [land ? Gp : X]; }
      let exLen = 0; const EP = land ? [X, ...exit] : [...exit, X]; for (let k = 1; k < EP.length; k++) exLen += Math.hypot(EP[k][0] - EP[k - 1][0], EP[k][1] - EP[k - 1][1]);
      let alE = alG - (land ? 1 : -1) * sgn * Math.max(0, dRoll - exLen);
      if (land && thrAl != null && (alE - thrAl) * sgn < 30) alE = (alG - thrAl) * sgn > 30 ? thrAl + sgn * 30 : alG;
      alE = clamp(alE, 0, r.length); E = this.axisPt(r, alE);
      rollPts = land ? [E, X, ...exit.slice(1)] : [...exit.slice(0, -1), X, E];
      dRoll = Math.abs(alE - alG) + exLen;
      // a take-off whose ground fix is away from the runway (> 30 m of taxi route) and that no plan can time (the aircraft taxied
      // out and took off unheard - a 'no signal' aircraft heard again airborne 1.3 km away): it is NOT drawn rolling along
      // taxilanes at take-off speed - it fades out where it stood and fades in on its climb-out (a re-placement after a signal
      // loss, counted by tools/traffic as one) [inf]
      if (!land && exLen > 30) { this.counters.replaceSignal = (this.counters.replaceSignal || 0) + 1; return this.farTransition(tr, a, b, dt); }
    }
    let tRoll = dRoll > 0.5 ? 2 * dRoll / Math.max(1, vfly + gv) : 0;
    if (tRoll > 0.5 * dt) tRoll = 0.5 * dt;
    const tE = land ? b.t - tRoll * 1000 : a.t + tRoll * 1000, gyE = this.groundY(E[0], E[1]);
    const dA = [A.vx / sA, A.vz / sA], distAE = Math.hypot(A.px - E[0], A.pz - E[1]);
    const fin = Math.min(T.cls === 'jet' ? 600 : 300, 0.4 * distAE);
    const segs = [];
    if (land) {
      segs.push(this.airSeg(a.t, tE, [a.px, a.pz], dA, sA, E, dir, vfly, a.y, gyE, a.vsm || -3, -1.0, tr, { final: fin }));
      if (tRoll > 0) { const R = polyOf(rollPts); segs.push({ kind: 'roll', t0: tE, t1: b.t, R, s0: 0, v0: 2 * R.len / tRoll - gv > 0 ? 2 * R.len / tRoll - gv : vfly, acc: 0, landing: true }); const sg = segs[segs.length - 1]; sg.acc = (gv - sg.v0) / tRoll; }
    } else {
      if (tRoll > 0) { const R = polyOf(rollPts); const v1 = Math.max(vfly, 2 * R.len / tRoll - gv); segs.push({ kind: 'roll', t0: a.t, t1: tE, R, s0: 0, v0: gv, acc: (v1 - gv) / tRoll, takeoff: true }); }
      segs.push(this.airSeg(tE, b.t, E, dir, vfly, [b.px, b.pz], dA, sA, gyE, b.y, 1.5, b.vsm || 0, tr, { initial: Math.min(T.cls === 'jet' ? 1500 : 500, 0.4 * Math.hypot(b.px - E[0], b.pz - E[1])) }));
    }
    return { segs, kind: land ? 'landing' : 'takeoff', rwy: r ? r.id : null, far, fallback: true };
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
  polyOf(pts) { return polyOf(pts); }
  airSeg(t0, t1, p0, d0, s0, p1, d1, s1, y0, y1, vy0, vy1, tr = null, opt = {}) {
    const D = (t1 - t0) / 1000; return { kind: 'air', t0, t1, C: tr ? this.flightCurve(tr, p0, d0, s0, p1, d1, s1, D, opt) : geoHermite(p0, d0, s0, p1, d1, s1, D), y0, y1, vy0, vy1 };
  }
  // ---- take-off reconstruction (review round 3, M3): an aircraft on the ground (holding, lined up, taxiing, or silent at its
  // last position - the continuation anchor) whose next fix is airborne took off unheard. The take-off is drawn on the runway
  // that first airborne fix is consistent with (departureRunway): taxi to the line-up point, a roll along the centreline at the
  // type's mean take-off acceleration (speedsOf accTO = VR^2 / 2 x ground roll), lift-off at VR inside the runway, a straight
  // climb-out on the runway heading, then a bank-limited join to the airborne track (flightCurve). Every sample is inferred.
  // When the hole is too short for that (a silent aircraft heard again airborne: the display is only lookahead_s behind), the
  // ground part is still drawn in full and the climb-out joins the track LATE, at the first later airborne fix it can reach at
  // <= 1.2 x the reported speeds (tr.xplan, xplanAir) - never a roll that is shorter or faster than the type can do.
  planTakeoff(tr, a0, b, dt, t0 = a0.t) {
    const T = tr.dims, SP = this.spd(tr), VR = SP.vr;
    const ep = this.endPt(tr, a0); const a = ep[0] === a0.px && ep[1] === a0.pz ? a0 : { ...a0, px: ep[0], pz: ep[1] };
    const D = this.departureRunway(tr, a, b); if (!D) return this.why(1);
    const { r, sgn } = D, dirR = [r.dir[0] * sgn, r.dir[1] * sgn], hR = bearR(dirR[0], dirR[1]);
    const onAx = (p) => { const px = p[0] - r.origin[0], pz = p[1] - r.origin[1]; return [px * r.dir[0] + pz * r.dir[1], px * r.right[0] + pz * r.right[1]]; };
    const [pa, acA] = onAx([a.px, a.pz]);
    const left = (al) => sgn > 0 ? r.length - al : al;              // runway ahead of an along position
    const need = SP.roll * 1.1 + 40;                               // runway needed from the line-up point [inf: 10 % + 40 m margin]
    const vAlong = a.gsm > 0.5 ? a.gsm * Math.cos(a.dir - hR) : 0;
    const onR = Math.abs(acA) <= r.halfWidth + 6 && pa >= -5 && pa <= r.length + 5;
    let alE, taxi = null, v0 = 0, tPiv = 0, rolling = false;
    if (onR && vAlong > 3 && left(pa) > SP.roll * 0.5 + 40) { alE = clamp(pa, 0, r.length); v0 = Math.min(vAlong, VR); rolling = true; }   // rolling start (touch-and-go / seen mid-roll)
    else if (onR && a.gsm < 1.5 && left(pa) >= need) {
      // standing on the runway (lined up / holding in position): pivot onto the centreline heading if needed, then roll from rest
      alE = clamp(pa, 0, r.length); const hA = a.hdReal ? a.hd : a.hd ?? a.dir; const turnA = hA != null ? Math.abs(wrapPi(hR - hA)) : 0;
      if (turnA > 20 * D2R) tPiv = turnA / (LIM.wPivot * D2R) + 1.5;
    } else {
      // taxi to a line-up point with enough runway ahead (the runway end or an intersection ahead of the aircraft)
      const C = this.entryCands(tr, a, r, sgn, hR, clamp(pa, 0, r.length)).filter(c => left(c.alE) >= need);
      if (!C.length) return this.why(3);
      C.sort((p, q) => p.taxi.P.tmin - q.taxi.P.tmin); taxi = C[0].taxi; alE = C[0].alE; v0 = 3;
      const hA = a.hdReal ? a.hd : a.hd ?? a.dir;
      if (a.gsm < 0.5 && hA != null && taxi.R.pts.length > 1) { const q = polyAt(taxi.R, Math.min(8, taxi.R.len)); const turnA = Math.abs(wrapPi(bearR(q.x - taxi.R.pts[0][0], q.z - taxi.R.pts[0][1]) - hA)); if (turnA > 45 * D2R) tPiv = turnA / (LIM.wPivot * D2R) + 1.5; }
    }
    // (the table acceleration is at maximum weight; a lighter aircraft rolls shorter - up to 1.3 x the acceleration, used only
    // as far as the hole needs it [inf: C172S POH ~0.7 x the ground roll at 2,200 vs 2,550 lb, recalled; SF50 AFM 1,483 ft at
    // 5,000 lb -20 C vs 2,036 ft at 6,000 lb ISA = 1.37 x])
    const budget0 = (b.t - t0) / 1000;
    let ACC = SP.accTO;
    for (const f of [1, 1.15, 1.3]) { ACC = SP.accTO * f; const tR = (VR - v0) / ACC, dR = Math.max(0, (VR * VR - v0 * v0) / (2 * ACC));
      if ((taxi ? taxi.P.tmin : 0) + tPiv + tR + Math.max(0, Math.hypot(b.px - this.axisPt(r, alE)[0], b.pz - this.axisPt(r, alE)[1]) - dR) / ((VR + Math.max(b.gsm || 0, VR)) / 2) <= budget0) break; }
    const dRoll = Math.max(0, (VR * VR - v0 * v0) / (2 * ACC)), alLO = alE + sgn * dRoll;
    if (left(alLO) < 30) return this.why(2);                       // lift-off inside the runway, >= 30 m before its end
    const E = this.axisPt(r, alE), LO = this.axisPt(r, alLO), gyLO = this.groundY(LO[0], LO[1]);
    const tTaxi = (taxi ? taxi.P.tmin : 0) + tPiv, tRoll = (VR - v0) / ACC;
    const vb = Math.max(b.gsm || 0, VR), sb = Math.max(1, Math.hypot(b.vx, b.vz)), dB = [b.vx / sb, b.vz / sb];
    const dLB = Math.hypot(b.px - LO[0], b.pz - LO[1]), ini = Math.min(T.cls === 'jet' ? 1500 : 500, 0.5 * dLB);
    const tAirNom = Math.max(2, this.flightCurve(tr, LO, dirR, VR, [b.px, b.pz], dB, vb, Math.max(2, dLB / ((VR + vb) / 2)), { initial: ini }).len / ((VR + vb) / 2));
    const budget = (b.t - t0) / 1000, slack = budget - (tTaxi + tRoll + tAirNom);
    if (this.debugPlan) console.log('planTakeoff', JSON.stringify({ rw: r.id, sgn, cost: +D.cost.toFixed(2), rolling, alE: +alE.toFixed(0), alLO: +alLO.toFixed(0), v0: +v0.toFixed(1), dRoll: +dRoll.toFixed(0), acc: +ACC.toFixed(2), tTaxi: +tTaxi.toFixed(1), tRoll: +tRoll.toFixed(1), tAir: +tAirNom.toFixed(1), budget: +budget.toFixed(1) }));
    const segs = []; let t = t0;
    const late = slack < 0;
    let wait = 0, tTx = taxi ? taxi.P.tmin : 0;
    // spare time: a taxiing aircraft lines up and waits on the runway for up to 30 s ('line up and wait'; it then rolls from
    // rest), any more is spent in the taxi profile (a hold where it stood, or at a slow point of the route); standing on the
    // runway it waits there [inf]
    let v0r = v0, tRollR = tRoll, dRollR = dRoll;
    if (!late) {
      if (taxi && slack >= 3 / ACC + 1.5) { const dR0 = VR * VR / (2 * ACC); if (left(alE + sgn * dR0) >= 30) { v0r = 0; tRollR = VR / ACC; dRollR = dR0; const s2 = slack - (tRollR - tRoll); wait = Math.min(30, s2); tTx += s2 - wait; } else tTx += slack; }
      else if (taxi) tTx += slack; else if (!rolling) wait = slack;
    }
    if (tPiv > 0) { const t1 = t + tPiv * 1000; segs.push({ kind: 'wait', t0: t, t1, x: taxi ? a.px : E[0], z: taxi ? a.pz : E[1], hd: taxi ? bearR(taxi.R.pts[Math.min(1, taxi.R.pts.length - 1)][0] - taxi.R.pts[0][0], taxi.R.pts[Math.min(1, taxi.R.pts.length - 1)][1] - taxi.R.pts[0][1]) : hR }); t = t1; }
    if (taxi) { taxi = this.profiled(tr, taxi.R.pts, Math.max(1e-3, tTx), a, null, 'taxi', true, { v1: 3 }); const t1 = t + tTx * 1000; segs.push({ kind: 'prof', t0: t, t1, G: taxi }); t = t1; }
    if (wait > 0.05) { const t1 = t + wait * 1000; segs.push({ kind: 'wait', t0: t, t1, x: E[0], z: E[1], hd: hR }); t = t1; }
    const alLO2 = alE + sgn * dRollR, LO2 = this.axisPt(r, alLO2);
    { const t1 = t + tRollR * 1000; segs.push({ kind: 'roll', t0: t, t1, R: polyOf([E, this.axisPt(r, alLO2 + sgn * 1)]), s0: 0, v0: v0r, acc: ACC, takeoff: true }); t = t1; }
    const P = { segs, kind: 'takeoff', rwy: r.id, end: sgn > 0 ? r.id.split('/')[0] : r.id.split('/')[1], rolling, t0, t1: b.t, recon: true, roll: dRollR, alLO: alLO2, alE, rLen: r.length, sgn };
    // (the climb-out starts at the speed the roll ended at: a rolling start already above VR lifts off at its own speed - it
    // used to drop from 77 to 60 kt at the wheels)
    const air = { LO: LO2, dirR, vLO: Math.max(VR, rolling ? Math.min(vAlong, 1.3 * VR) : v0r), gyLO: this.groundY(LO2[0], LO2[1]), tL: t, ini: Math.min(T.cls === 'jet' ? 1500 : 500, 600), climb: SP.climb };
    { const S = this.takeoffAir(tr, air, b, false, late ? 1.15 : 1.2); if (S) { segs.push(S); return P; } }
    // the take-off cannot reach b in time: it joins the airborne track at a later fix (xplanAir, built when it lifts off)
    P.late = true; P.t1 = Infinity; P.lazy = air; this.counters.takeoffLate = (this.counters.takeoffLate || 0) + 1;
    return P;
  }
  // the climb-out from the lift-off point to an airborne fix c over [air.tL, c.t]: straight on the runway heading first (air.ini),
  // then a bank-limited join; the height climbs monotonically from the runway to c's (at most the type's climb rate at the
  // start) -> an air segment, or null when it would need more than 1.2 x / less than 0.75 x the reported speeds [inf]
  takeoffAir(tr, air, c, force = false, kMax = 1.2) {
    const D = (c.t - air.tL) / 1000; if (!(D > 1.5)) return null;
    const sc = Math.max(1, Math.hypot(c.vx, c.vz)), dC = [c.vx / sc, c.vz / sc], vc = Math.max(c.gsm || 0, 0.8 * air.vLO);
    const dist = Math.hypot(c.px - air.LO[0], c.pz - air.LO[1]), ini = Math.max(0, Math.min(air.ini - (air.flown || 0), 0.5 * dist));
    const keep = Math.max(0, (tr.dims && tr.dims.cls === 'jet' ? 800 : 400) - (air.flown || 0));
    // (the path is sized for the climb speed at both ends - the re-timing below adds the acceleration from the lift-off speed;
    // sized for a linear VR -> vc profile it came out short and was flown below the minimum flying speed)
    const C0 = this.flightCurve(tr, air.LO, air.dirR, vc, [c.px, c.pz], dC, vc, D, { initial: Math.max(ini, Math.min(keep, 0.7 * dist)), keepInitial: Math.min(keep, 0.7 * dist) });
    // (re-timed: after lift-off the aircraft accelerates at <= 1.2 m/s2 from its lift-off speed and then flies the path at one
    // speed vc'; k = vc' / the reported speed at c - the linear VR -> vc profile of the curve made a late, slow start look like a
    // too-long path) [inf: 1.2 m/s2]
    const C = retimePath(C0, D, air.vLO, 1.2, vc), k = C.vc / Math.max(1, vc);
    if (!force && C.vc < 0.98 * this.spd(tr).vmin) return null;
    // the straight climb-out is really there: over the first `keep` metres the path stays within 5 m (+ 3 %) of the runway
    // heading line through the lift-off point (flightCurve may have had to drop it)
    if (!force && keep > 30) { const tK = Math.min(D, keep / Math.max(10, air.vLO)); for (let j = 1; j <= 12; j++) { const q = C.at(tK * j / 12), ax = q.x - air.LO[0], az = q.z - air.LO[1], al = ax * air.dirR[0] + az * air.dirR[1];
      if (Math.abs(ax * air.dirR[1] - az * air.dirR[0]) > 5 + 0.03 * Math.max(0, al) || al < -1) return null; } }
    const y0 = air.y ?? air.gyLO, dy = c.y - y0, vsMax = LIM.airVs[tr.dims && tr.dims.cls] || LIM.airVs.default;
    if (!force && (k > kMax || k < 0.75 || dy / D > vsMax)) return null;
    // (monotone cubic: both end slopes within 3 x the mean climb - Fritsch-Carlson - so the height never dips or overshoots)
    const sec = Math.max(0, dy) / D, vy0 = Math.min(air.vy ?? air.climb, 3 * sec), vy1 = clamp(c.vsm ?? sec, 0, 3 * sec);
    return { kind: 'air', t0: air.tL, t1: c.t, C, y0, y1: Math.max(c.y, y0), vy0, vy1, k };
  }
  // late join of a reconstructed take-off (tr.xplan with P.lazy): at lift-off time, the first later airborne fix the climb-out
  // reaches at <= 1.2 x the reported speeds (takeoffAir). Until one is reachable the aircraft climbs on: straight ahead on the
  // runway heading for the first air.ini metres while it accelerates (<= 1 m/s2) to its climb speed, then in a standard-rate
  // turn (3 deg/s) toward the newest known airborne fix at up to 1.15 x its reported speed - a pursuit that closes on the
  // track - in 2-s pieces [inf: all rates]
  xplanAir(tr, X, t) {
    const A = X.lazy; if (!A || t < A.tL - 100) return;
    // (only airborne fixes before the next ground fix: a pattern aircraft that lands again before the join ends its climb-out
    // there - forced onto the last airborne fix before that landing)
    const gN = tr.fx.find(q => q.ground && q.t > A.tL), tLim = gN ? gN.t : Infinity;
    for (let guard = 0; guard < 400 && X.lazy && t > A.tL - 100; guard++) {
      for (const c of tr.fx) { if (c.ground || c.t <= A.tL + 3000 || c.t >= tLim) continue; const S = this.takeoffAir(tr, A, c); if (S) { X.segs.push(S); X.t1 = c.t; X.lazy = null; X.joined = c.t; return; } }
      const known = tr.fx.filter(q => !q.ground && q.t > A.tL - 120000 && q.t < tLim), tgt = known[known.length - 1];
      if ((A.ext || 0) > 240 || !tgt || (gN && A.tL > gN.t - 30000)) {   // (4 min without a join, a landing ahead, or no airborne fix: end at the newest one, forced)
        if (tgt && tgt.t > A.tL + 3000) { const S = this.takeoffAir(tr, A, tgt, true); if (S) { X.segs.push(S); X.t1 = tgt.t; X.lazy = null; return; } }
        X.hideSeg = true; X.t1 = A.tL; X.lazy = null; return;
      }
      if (A.vR == null) A.vR = A.vLO;
      const v0 = A.v ?? A.vLO, vT = 1.15 * Math.max(tgt.gsm || 0, A.vR), v1 = v0 < vT ? Math.min(vT, v0 + 2 * 1.0) : Math.max(vT, v0 - 2 * 1.0);
      const h0 = bearR(A.dirR[0], A.dirR[1]), flown = (A.flown || 0);
      const dh = flown < A.ini ? 0 : clamp(wrapPi(bearR(tgt.px - A.LO[0], tgt.pz - A.LO[1]) - h0), -6 * D2R, 6 * D2R);
      const d1 = hvR(h0 + dh), len = (v0 + v1);   // 2 s at the mean speed
      const P1 = [A.LO[0] + (A.dirR[0] + d1[0]) / 2 * len, A.LO[1] + (A.dirR[1] + d1[1]) / 2 * len];
      const y0 = A.y ?? A.gyLO, vy = Math.min(A.climb, LIM.airVs[tr.dims && tr.dims.cls] || LIM.airVs.default), y1 = Math.min(y0 + vy * 2, Math.max(y0, tgt.y));
      X.segs.push({ kind: 'air', t0: A.tL, t1: A.tL + 2000, C: geoHermite(A.LO, A.dirR, v0, P1, d1, v1, 2), y0, y1, vy0: A.vy ?? 1.5, vy1: (y1 - y0) / 2 });
      Object.assign(A, { LO: P1, dirR: d1, v: v1, vLO: v1, tL: A.tL + 2000, y: y1, vy: (y1 - y0) / 2, ext: (A.ext || 0) + 2, flown: flown + len });
    }
  }
  // the runway (and direction) a take-off from ground fix a toward airborne fix b used. An aircraft already on a runway - rolling
  // along it, or standing lined up - takes off on that one, the way it points (a touch-and-go). Otherwise the runway end the
  // airborne fix is most consistent with: ahead of the lift-off area, within 150 deg of the runway heading (the first fix after
  // a 46-s hole is often on crosswind or downwind), close to the extended centreline for the distance flown, near the aircraft
  // and in the current flow [inf weights] -> { r, sgn, cost } | null
  departureRunway(tr, a, b) {
    const SP = this.spd(tr); let best = null;
    const RWa = this.runwayAt(a.px, a.pz, 6);
    if (RWa) { const r = RWa.r, hR = bearR(r.dir[0], r.dir[1]), h = a.gsm > 1.5 ? a.dir : (a.hdReal ? a.hd : null);
      if (h != null && Math.abs(Math.cos(h - hR)) > Math.cos(30 * D2R)) { const sgn = Math.cos(h - hR) >= 0 ? 1 : -1, left = sgn > 0 ? r.length - RWa.al : RWa.al;
        const vAl = a.gsm * Math.abs(Math.cos(h - hR));
        if ((vAl > 3 && left > SP.roll * 0.5 + 40) || left >= SP.roll * 1.1 + 40) return { r, sgn, cost: 0, onRunway: true }; } }
    for (const r of (this.site && this.site.runways) || []) for (const sgn of [1, -1]) {
      const hR = bearR(r.dir[0] * sgn, r.dir[1] * sgn), dpsi = Math.abs(wrapPi((b.trk != null ? b.trk * D2R : b.dir) - hR));
      if (dpsi > 150 * D2R) continue;
      const dep = sgn > 0 ? 0 : r.length, al = (p) => ((p[0] - r.origin[0]) * r.dir[0] + (p[1] - r.origin[1]) * r.dir[1]), ac = (p) => ((p[0] - r.origin[0]) * r.right[0] + (p[1] - r.origin[1]) * r.right[1]);
      const sB = (al([b.px, b.pz]) - dep) * sgn, acB = Math.abs(ac([b.px, b.pz])), sLO = SP.roll + 30;
      if (sB < 0.6 * sLO) continue;                                  // the airborne fix is behind the lift-off area
      if (r.length < SP.roll * 1.1 + 40) continue;                   // too short for this type
      // heading change since lift-off; still within 45 deg of the runway: near its extended centreline for the distance flown;
      // turned further: at least about a turn radius (25 deg bank at 1.3 VR) off it; then the taxi distance to the line-up point
      // (the departure end, or the runway beside the aircraft when enough of it lies ahead) - m / 400 m
      const ext = Math.max(0, sB - sLO), Rt = (1.3 * SP.vr) ** 2 / (GRAV * Math.tan(25 * D2R));
      let cost = dpsi / (90 * D2R) + (dpsi < 45 * D2R ? acB / Math.max(60, 0.15 * ext) : 0.5 * Math.max(0, Rt - acB) / Rt);
      const pa = al([a.px, a.pz]), aa = Math.abs(ac([a.px, a.pz]));
      const dEnd = Math.hypot(a.px - this.axisPt(r, dep)[0], a.pz - this.axisPt(r, dep)[1]), ahead = sgn > 0 ? r.length - pa : pa;
      cost += (pa >= 0 && pa <= r.length && ahead >= SP.roll * 1.1 + 40 ? Math.min(dEnd, aa) : dEnd) / 400;
      if (this.classifier.flow && this.classifier.flow.end && (this.classifier.flow.end === '10') !== (sgn > 0)) cost += 0.5;
      if (!best || cost < best.cost) best = { r, sgn, cost, sB, acB, dpsi: dpsi / D2R };
    }
    return best && best.cost < 5 ? best : null;
  }
  // runway entries for a take-off from ground fix a (fix round 2): routes to points down the runway (200 m / 60 m from a's
  // abeam point al0) and to the runway end behind it; each joins the centreline where the route reaches it (+ 15 m of
  // line-up). -> [{ al0, alE, taxi (profiled, tmin) }]
  entryCands(tr, a, r, sgn, hR, al0) {
    const T = tr.dims, out = [];
    const onAx = (p) => { const px = p[0] - r.origin[0], pz = p[1] - r.origin[1]; return [px * r.dir[0] + pz * r.dir[1], Math.abs(px * r.right[0] + pz * r.right[1])]; };
    const endAl = sgn > 0 ? 0 : r.length;
    for (const gAl of [al0 + sgn * 200, al0 + sgn * 60, endAl + sgn * 40]) {
      const g = clamp(gAl, 0, r.length), G = this.axisPt(r, g);
      if (out.some(c => Math.abs(c.al0 - g) < 20)) continue;
      const dA = Math.hypot(a.px - G[0], a.pz - G[1]);
      const R = this.net.routeXY(a.px, a.pz, a.gsm > 0.5 ? a.dir : (a.hdReal ? a.hd : null), G[0], G[1], hR, { span: T.span, runway: true, v0: a.gsm, block: this.routeBlock(tr) });
      if (!R || R.len > 4 * dA + 400) continue;
      let kk = R.pts.length - 1; while (kk > 0 && onAx(R.pts[kk - 1])[1] < 3 && (onAx(R.pts[kk])[0] - onAx(R.pts[kk - 1])[0]) * sgn >= -0.5) kk--;
      const aE = clamp(onAx(R.pts[kk])[0] + sgn * 15, 0, r.length);
      const taxi = this.profiled(tr, R.pts.slice(0, kk + 1).concat([this.axisPt(r, aE)]), 1e-3, a, null, 'taxi', true, { v1: 3 });
      if (taxi) out.push({ al0: g, alE: aE, taxi });
    }
    return out;
  }
  // taxi from the ground fix a, line up, and roll to the fast ground fix b on the runway, arriving with b's speed (constant
  // acceleration 0.6-4 m/s2 [inf]); spare time is a wait before the roll (holding short / lined up). null = no plan.
  rollFor(tr, a0, b, dt) {
    const k = 'r' + a0.t; if (tr.routeCache.has(k)) return tr.routeCache.get(k);
    let P = null; try { P = this.planRollTo(tr, a0, b, dt); } catch (e) { P = null; if (this.debugCuts) console.error(e); }
    this.counters[P ? 'rollPlans' : 'rollPlanFail'] = (this.counters[P ? 'rollPlans' : 'rollPlanFail'] || 0) + 1;
    this.cacheSet(tr, k, P); return P;
  }
  rwhy(k, x) { if (this.debugPlan) console.log('planRollTo fail', k, x != null ? JSON.stringify(x) : ''); return null; }
  planRollTo(tr, a0, b, dt) {
    const T = tr.dims;
    const ep = this.endPt(tr, a0); const a = ep[0] === a0.px && ep[1] === a0.pz ? a0 : { ...a0, px: ep[0], pz: ep[1] };
    const B = this.rwyFor(b.px, b.pz, b.dir, 40); if (!B) return this.rwhy(1);
    const r = B.r, sgn = B.sgn, hR = bearR(r.dir[0] * sgn, r.dir[1] * sgn);
    const onAx = (p) => { const px = p[0] - r.origin[0], pz = p[1] - r.origin[1]; return [px * r.dir[0] + pz * r.dir[1], Math.abs(px * r.right[0] + pz * r.right[1])]; };
    const [pa, acA] = onAx([a.px, a.pz]), alB = onAx([b.px, b.pz])[0];
    if ((alB - pa) * sgn < 50) return this.rwhy(2);   // b must lie down the runway from a
    let alE, taxi = null, v0 = 3, acc, tRoll, tTaxi, slack;
    const vAlong = a.gsm > 0.5 ? a.gsm * Math.cos(a.dir - hR) : 0, vb = b.gsm;
    if (acA <= r.halfWidth + 5 && vAlong > 3) {
      alE = pa; v0 = vAlong;
      const dR = (alB - alE) * sgn; if (dR < 30) return this.rwhy(5);
      acc = (vb * vb - v0 * v0) / (2 * dR); if (!(acc >= 0.6 && acc <= 4.0)) return this.rwhy(6);
      tRoll = (vb - v0) / acc; tTaxi = 0; slack = dt - tRoll;
    } else {
      // (fix round 2) the runway entry: candidates ahead of the aircraft along the runway (200 m and 60 m down from its
      // abeam point) and the runway end it is taxiing toward (a full-length departure); the one whose taxi + roll fits the
      // hole best wins [inf]
      const cands = [];
      for (const c of this.entryCands(tr, a, r, sgn, hR, pa)) {
        const dR = (alB - c.alE) * sgn; if (dR < 30) continue;
        const ac = (vb * vb - 9) / (2 * dR); if (!(ac >= 0.6 && ac <= 4.0)) continue;
        const tR = (vb - 3) / ac; cands.push({ ...c, acc: ac, tRoll: tR, tTaxi: c.taxi.P.tmin, slack: dt - c.taxi.P.tmin - tR });
      }
      if (!cands.length) return this.rwhy(3);
      cands.sort((p, q) => (q.slack >= 0) - (p.slack >= 0) || (p.slack >= 0 ? p.tTaxi + p.tRoll - (q.tTaxi + q.tRoll) : q.slack - p.slack));
      ({ alE, taxi, acc, tRoll, tTaxi, slack } = cands[0]);
    }
    if (this.debugPlan) console.log('planRollTo', JSON.stringify({ rw: r.id, sgn, alE: +alE.toFixed(0), alB: +alB.toFixed(0), v0, vb, acc: +acc.toFixed(2), tTaxi: +tTaxi.toFixed(1), tRoll: +tRoll.toFixed(1), dt }));
    if (slack < 0) return this.rwhy(7);
    const Ep = this.axisPt(r, alE), segs = []; let t0 = a.t;
    if (taxi) { const tTx = tTaxi + slack; taxi = this.profiled(tr, taxi.R.pts, tTx, a, null, 'taxi', true, { v1: 3 }); if (!taxi) return this.rwhy(8); const t1 = t0 + tTx * 1000; segs.push({ kind: 'prof', t0, t1, G: taxi }); t0 = t1; }
    else if (slack > 0) { const t1 = t0 + slack * 1000; segs.push({ kind: 'wait', t0, t1, x: Ep[0], z: Ep[1], hd: hR }); t0 = t1; }
    segs.push({ kind: 'roll', t0, t1: b.t, R: polyOf([Ep, this.axisPt(r, alB)]), s0: 0, v0, acc, takeoff: true });
    return { segs, kind: 'roll', rwy: r.id, rolling: !taxi };
  }
  planLanding(tr, a, b0, dt) {
    const T = tr.dims, SP = this.spd(tr);
    const ep = this.endPt(tr, b0); const b = ep[0] === b0.px && ep[1] === b0.pz ? b0 : { ...b0, px: ep[0], pz: ep[1] };
    // the runway: aligned with the approach fix a (within 150 m of its axis), else the runway beside the ground fix b in the
    // current flow direction (the turn to final happened in the hole: the approach curve flies it) [inf]
    let A_ = this.rwyFor(a.x, a.z, a.dir, 150), sgn;
    if (A_) sgn = A_.sgn;
    else { A_ = this.rwyFor(b.px, b.pz, null, 200); if (!A_) return this.why(5); sgn = this.classifier.flow.end === '10' ? 1 : -1; }
    const r = A_.r, dirR = [r.dir[0] * sgn, r.dir[1] * sgn], hR = bearR(dirR[0], dirR[1]);
    const endName = sgn > 0 ? r.id.split('/')[0] : r.id.split('/')[1];
    const thrAl = sgn > 0 ? thrDispM(endName) : r.length - thrDispM(endName);
    // (review round 3) touchdown in the touchdown zone: 150 m past the landing threshold for pistons, 200 m turboprops, 300 m
    // jets [inf: the aiming point marking is 1,020 ft (311 m) past the threshold on precision runways, AC 150/5340-1M; light
    // aircraft touch down before it]
    const tdz = T.cls === 'jet' ? 300 : T.cls === 'turboprop' ? 200 : 150;
    let alTD = thrAl + sgn * tdz; const pa = (a.px - r.origin[0]) * r.dir[0] + (a.pz - r.origin[1]) * r.dir[1];
    if ((pa - alTD) * sgn > -30) alTD = pa + sgn * 60;
    const pb = (b.px - r.origin[0]) * r.dir[0] + (b.pz - r.origin[1]) * r.dir[1], acB = (b.px - r.origin[0]) * r.right[0] + (b.pz - r.origin[1]) * r.right[1];
    // the ground fix is still ON the runway (mid roll-out, the usual case with 46-s holes): touchdown at least 60 m before it
    // and a roll along the centreline to it - no exit (fix round 1: the plan used to exit before b and taxi back to it)
    const bOn = Math.abs(acB) <= r.halfWidth + 12 && pb >= -30 && pb <= r.length + 30;
    if (bOn && (pb - alTD) * sgn < 60) alTD = pb - sgn * 60;
    // (review round 3) never before the landing threshold; a fast ground fix right past it (a threshold crossing at a few
    // feet that counts as runway contact) is the touchdown itself
    let tdAtB = false;
    if ((alTD - thrAl) * sgn < 10) { alTD = thrAl + sgn * 10; if (bOn && (pb - alTD) * sgn < 15) { alTD = pb; tdAtB = true; } }
    alTD = clamp(alTD, 0, r.length);
    if ((alTD - pa) * sgn < -50 && Math.hypot(a.px - r.origin[0], a.pz - r.origin[1]) < r.length + 2500) return this.why(8);   // touchdown behind the approach fix
    // (a landing roll does not speed up: the touchdown is at least as fast as the roll fix b, up to 1.3 x vtd)
    const vTD = clamp(Math.max(Math.min(a.gsm, SP.vtd), bOn ? (b.gsm || 0) + 0.5 : 0), SP.vr, SP.vtd * 1.3);
    const TD = this.axisPt(r, alTD);
    let pts, rwyHead, vTDa = vTD;
    if (bOn) { const Bx = this.axisPt(r, clamp(pb, 0, r.length)); pts = [TD, Bx]; if (Math.hypot(b.px - Bx[0], b.pz - Bx[1]) > 3) pts.push([b.px, b.pz]); rwyHead = 1e9; }
    else {
      // exit: where the ground fix b projects on the runway, but not before the roll-out has slowed to a turn-off speed
      // (2.5 m/s2 to 4 m/s + 20 m) [inf]
      const dStop = (vTD * vTD - 16) / (2 * 2.5) + 20;
      const alX = clamp((pb - alTD) * sgn >= dStop ? pb : alTD + sgn * dStop, 0, r.length);
      if (Math.abs(alX - alTD) < 0.6 * dStop) return this.why(9);
      const X = this.axisPt(r, alX); pts = [TD, X]; rwyHead = Math.abs(alX - alTD);
      const dB = Math.hypot(b.px - X[0], b.pz - X[1]);
      if (dB > 8) { const taxi = this.net.routeXY(X[0], X[1], hR, b.px, b.pz, b.gsm > 0.5 ? b.dir : (b.hdReal ? b.hd : null), { span: T.span, runway: true, noRunway: true });
        if (!taxi || taxi.len > 4 * dB + 150) return this.why(6); pts = [TD, ...taxi.pts]; }
    }
    const dAir = Math.hypot(TD[0] - a.px, TD[1] - a.pz), tAirNom = dAir / Math.max(10, (a.gsm + vTD) / 2);
    let tGround, G;
    if (tdAtB) {   // the approach ends at b, on the runway at b's speed; b's own segment rolls on
      const sa = Math.max(1, Math.hypot(a.vx, a.vz)), dirB = dirR, D = (b.t - a.t) / 1000, alongA = (TD[0] - a.px) * dirR[0] + (TD[1] - a.pz) * dirR[1];
      const fin = Math.min(T.cls === 'jet' ? 800 : 400, alongA > 0 ? 0.6 * alongA : 400);
      const S = this.airSeg(a.t, b.t, [a.px, a.pz], [a.vx / sa, a.vz / sa], Math.max(a.gsm, 10), [b.px, b.pz], dirB, Math.max(b.gsm, SP.vr), a.y, this.groundY(b.px, b.pz), a.vsm || -3, -0.8, tr, { final: fin, keepFinal: Math.min(fin, 0.6 * dAir) });
      if (!(S.C.k != null ? S.C.k <= 1.35 : S.C.len / Math.max(1e-3, S.C.Ld) <= 1.35)) return this.why(10);
      return { segs: [S], kind: 'landing', rwy: r.id, bOn, recon: true, t0: a.t, t1: b.t, tdAtB: true };
    }
    if (bOn) {
      // time split: the roll-out at a constant deceleration from the touchdown speed to b's speed (its natural time, never
      // below the profile's minimum), the approach at the mean of the reported and touchdown speeds; spare time goes to the
      // approach down to 0.85 x its nominal speed (never below the minimum flying speed), the rest to the roll [inf]
      // (review round 3) the roll-out takes its natural time - one constant deceleration from the touchdown speed to b's along the
      // centreline - and ALL spare time goes to the approach (a longer final / wider pattern); fix round 2 gave the rest to
      // the roll, which put a stop into a 46-m roll at 64 kt
      // (an approach that would have to be flown slower than the type flies - 0.8 x the mean of the reported and touchdown speeds,
      // never below its minimum - touches down earlier instead: the roll gets longer, down to 10 m past the threshold)
      const tot = (b.t - a.t) / 1000, vAirMin = Math.max(SP.vmin, 0.8 * (a.gsm + vTD) / 2);
      if (!tdAtB && pts.length === 2) {
        const alMin = thrAl + sgn * 10;
        for (let al = alTD; (al - alMin) * sgn >= -0.5; al -= sgn * 25) {
          const T2 = this.axisPt(r, al), d2 = Math.abs(pb - al), tN = 2 * d2 / Math.max(1, vTD + (b.gsm || 0)), dA = Math.hypot(T2[0] - a.px, T2[1] - a.pz) * 1.05;
          alTD = al; if (dA / Math.max(1, tot - tN) >= vAirMin) break;
        }
        const T2 = this.axisPt(r, alTD); TD[0] = T2[0]; TD[1] = T2[1]; pts[0] = T2;
      }
      const G0 = this.profiled(tr, pts, 1e-3, null, b, 'rollout', true, { v0: vTD, rwyHead });
      const vb = Math.max(0, G0.v1), dR = G0.R.len, tNat = Math.max(G0.P.tmin, 2 * dR / Math.max(1, vTD + vb));
      const tAir = tot - tNat;
      if (tAir < 0.6 * tAirNom || tAir < 2) return this.why(7);
      tGround = tNat;
      const vb2 = b.gsm || 0;
      if (pts.length === 2 && vb2 <= vTD && dR > 2) {
        G = { roll: true, R: polyOf(pts), parts: [{ s0: 0, v0: vTD, acc: (vb2 * vb2 - vTD * vTD) / (2 * dR), dt: 2 * dR / (vTD + vb2) }] }; tGround = 2 * dR / (vTD + vb2);
        // (review round 3) the approach cannot be flown slower than the type flies: when even a touchdown at the threshold
        // leaves the approach below vAirMin (the fixes' positions say slower than their speeds - position latency), the approach
        // is flown at vAirMin and the roll takes the rest: brake harder, then hold the slower speed - or, for a touch-and-go
        // (airborne again within 20 s of b), brake and accelerate again to b's speed [inf: <= 2.5 m/s2 braking]
        const dA2 = Math.hypot(TD[0] - a.px, TD[1] - a.pz) * 1.1;
        if (dA2 / Math.max(1, tot - tGround) < vAirMin) {
          const Tg = tot - dA2 / vAirMin, i = tr.fx.indexOf(b0), nx = i >= 0 ? tr.fx[i + 1] : null, tg = nx && nx.t - b0.t < 20000 && (!nx.ground || ((nx.gsm || 0) >= (b0.gsm || 0) - 0.5 && (b0.gsm || 0) > 0.6 * SP.vr));
          // (the touchdown at the slow approach speed itself, not faster: no speed step at the wheels)
          const v0s = clamp(vAirMin, Math.min(vTD, vb2 + 0.5), vTD);
          // (a full stop that cannot absorb the time by braking early slows below b's speed and taxis up to it again)
          const P2 = rollParts(dR, v0s, vb2, Tg, tg ? Math.max(0.8, SP.accTO) : 0, 2.5) || (!tg ? rollParts(dR, v0s, vb2, Tg, LIM.taxiAcc, 2.5) : null);
          if (P2) { G.parts = P2; tGround = Tg; vTDa = v0s; this.counters.landingSlowRoll = (this.counters.landingSlowRoll || 0) + 1; }
        }
      }
      else G = this.profiled(tr, pts, tGround, null, b, 'rollout', true, { v0: vTD, rwyHead });
    } else {
      tGround = (b.t - a.t) / 1000 - tAirNom;
      if (tGround < 5) return this.why(7);
      G = this.profiled(tr, pts, tGround, null, b, 'rollout', false, { v0: vTD, rwyHead });
      if (!G) return this.why(7);
    }
    const segs = []; const t1 = b.t - tGround * 1000;
    const sa = Math.max(1, Math.hypot(a.vx, a.vz));
    // (fix round 2) a straight final into the touchdown point: 300 m (jets 600 m) or half the distance of an approach fix that is
    // already lined up; the turn onto it at a 25-deg-bank radius (flightCurve) [inf]
    const alongA = (TD[0] - a.px) * dirR[0] + (TD[1] - a.pz) * dirR[1], latA = Math.abs((TD[0] - a.px) * dirR[1] - (TD[1] - a.pz) * dirR[0]);
    const finDef = T.cls === 'jet' ? 800 : 400, fin = alongA > 0 && latA < 0.3 * alongA ? Math.min(finDef, 0.6 * alongA) : finDef;
    // (review round 3: the final straight is kept - >= 400 m (jets 800 m), the last ~12 s before the wheels touch - so the
    // touchdown is aligned with the runway; keepFinal)
    const dTD = Math.hypot(TD[0] - a.px, TD[1] - a.pz);
    segs.push(this.airSeg(a.t, t1, [a.px, a.pz], [a.vx / sa, a.vz / sa], Math.max(a.gsm, 10), TD, dirR, vTDa, a.y, this.groundY(TD[0], TD[1]), a.vsm || -3, -1.0, tr, { final: fin, keepFinal: Math.min(fin, 0.6 * dTD) }));
    if (G.roll) { let tq = t1; G.parts.forEach((q, k) => { const t2 = k === G.parts.length - 1 ? b.t : tq + q.dt * 1000; segs.push({ kind: 'roll', t0: tq, t1: t2, R: G.R, s0: q.s0, v0: q.v0, acc: q.acc, landing: q.acc <= 0, takeoff: q.acc > 0 }); tq = t2; }); }
    else segs.push({ kind: 'prof', t0: t1, t1: b.t, G });
    return { segs, kind: 'landing', rwy: r.id, bOn, recon: true, t0: a.t, t1: b.t };
  }
  why(k) { this.counters['planFail' + k] = (this.counters['planFail' + k] || 0) + 1; if (this.debugPlan) console.log('plan fail', k); return null; }
  samplePlan(P, t, o) {
    let S = P.segs.find(q => t >= q.t0 && t <= q.t1) || (t < P.segs[0].t0 ? P.segs[0] : P.segs[P.segs.length - 1]); o.seg = S.kind + (S.takeoff ? 'R' : '');
    const D = Math.max(1e-3, (S.t1 - S.t0) / 1000), tau = clamp((t - S.t0) / 1000, 0, D), u = tau / D;
    o.ex = 0; o.route = true; o.hd = null;
    // the phase the plan is drawing (drawnPhase uses it where the fix label lags the drawn motion)
    o.planPh = S.kind === 'air' ? (P.kind === 'takeoff' ? 'initial_climb' : 'final') : S.kind === 'roll' ? (S.landing ? 'landing_roll' : 'takeoff_roll') : S.kind === 'wait' ? (this.onRunway(S.x, S.z) ? 'line_up' : 'hold_short') : null;
    if (S.kind === 'wait') { Object.assign(o, { x: S.x, z: S.z, y: this.groundY(S.x, S.z), vx: 0, vz: 0, vy: 0, gs: 0, ground: true, stop: true, hd: S.hd, rest: S.rest || (S.rest = { x: S.x, z: S.z, hdg: S.hd != null ? toDeg(S.hd) : 0, planned: true }) }); return o; }
    if (S.kind === 'prof') { this.sampleGround(S.G, tau, o); o.planPh = P.kind === 'landing' ? (this.onRunway(o.x, o.z) ? 'landing_roll' : 'taxi') : (this.onRunway(o.x, o.z) && o.gs > 3 ? 'line_up' : 'taxi'); return o; }
    if (S.kind === 'roll') {
      const s = S.s0 + S.v0 * tau + 0.5 * S.acc * tau * tau, v = S.v0 + S.acc * tau;
      const p = polyAt(S.R, s); Object.assign(o, { x: p.x, z: p.z, y: this.groundY(p.x, p.z), vx: p.ux * v, vz: p.uz * v, vy: 0, gs: v, ground: true, rollSeg: true });
      return o;
    }
    const q = S.C.at(tau);
    const u2 = u * u, u3 = u2 * u, h00 = 2 * u3 - 3 * u2 + 1, h10 = u3 - 2 * u2 + u, h01 = -2 * u3 + 3 * u2, h11 = u3 - u2;
    o.x = q.x; o.z = q.z; o.vx = q.vx; o.vz = q.vz; o.gs = q.v;
    o.y = h00 * S.y0 + h10 * D * S.vy0 + h01 * S.y1 + h11 * D * S.vy1; o.vy = S.vy0 + (S.vy1 - S.vy0) * u;
    o.ground = false; o.y = Math.max(o.y, this.groundY(o.x, o.z) + 0.3);
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
    this.cacheSet(tr, k, off); return off;
  }

  // ---------------------------------------------------------------- kinematic body
  step(tr, tDisp, dt) {
    const o = this.target(tr, tDisp, this._tgt); const D = tr.disp; const T = tr.dims; if (this.debugCtl) this._dbgT = tDisp;
    const rawX = o.x, rawZ = o.z, rawPrev = tr._raw; tr._raw = o.ground ? [rawX, rawZ] : null;
    if (tr.physOff && o.ground) { o.x += tr.physOff[0]; o.z += tr.physOff[1]; }
    let c = tr.ctl;
    // hidden (OAK ground part): re-created where it reappears (also on the first visible step), no cut
    if (c && (o.hideSeg || tr._hidPrev) && !(D.alpha > 0.01)) { c = null; }
    tr._hidPrev = !!o.hideSeg;
    const fw = T && T.cls !== 'heli' && !tr.vehicle;
    // lift-off guard: a fixed-wing body on the ground does not leave it below its lift-off speed - it keeps rolling straight
    // ahead (along its nose) and accelerating until it reaches it, then climbs after the target [inf]
    let synth = false;
    if (c && c.ground && fw && !o.ground && c.v < 0.8 * this.spd(tr).vr && (o.y - this.groundY(o.x, o.z)) < 60) {
      const f = hvR(c.psi), ahead = Math.max(2, c.v * dt + 0.5 * (LIM.rollAcc[T.cls] || 2.5) * dt * dt + 1), VRt = this.spd(tr).vr;
      // the point it rolls toward: the end of its trail pushed on along the nose (or a point just ahead of it)
      let px = c.x + f[0] * ahead, pz = c.z + f[1] * ahead;
      if (c.trail) { const Tq = c.trail, nq = Tq.x.length; const ex = Tq.x[nq - 1], ez = Tq.z[nq - 1]; if ((ex - c.x) * f[0] + (ez - c.z) * f[1] > ahead) { px = ex + f[0] * VRt * dt; pz = ez + f[1] * VRt * dt; } }
      Object.assign(o, { x: px, z: pz, vx: f[0] * VRt, vz: f[1] * VRt, gs: VRt, ground: true, stop: false, hd: null, mode: o.mode + '+lo' }); synth = true;
      o.y = this.groundY(o.x, o.z); this.counters.liftoffHeld = (this.counters.liftoffHeld || 0) + 1;
    }
    if (this.debugCuts) { const H = tr._mh || (tr._mh = []); const m = o.mode; if (!H.length || H[H.length - 1][1] !== m) H.push([Math.round(tDisp / 100) / 10, m, Math.round(o.gs), c ? Math.round(c.v) : null]); if (H.length > 12) H.shift(); }
    const err = c ? Math.max(Math.hypot(o.x - c.x, o.z - c.z), !o.ground && !c.ground ? Math.abs(o.y - c.y) * 1.5 : 0) : 0;
    const roll = o.ground && Math.max(o.gs || 0, c ? Math.abs(c.v) : 0) > 15;
    // (air, fix round 2: from the larger of the target's and the body's speed - a short-hole Hermite whose speed dips for a
    // moment shrank the limit under a body still catching up after a tight data turn, and it was re-placed)
    const errMax = o.ground ? (roll ? ERR_ROLL : ERR_G) : Math.max(ERR_AIR, ERR_AIR_V * Math.max(Math.hypot(o.vx, o.vz), c ? Math.abs(c.v) : 0, o.vRep || 0));
    // a ground target that moved farther than JUMP_G_M in one step has jumped (a new segment that does not start where the
    // last one ended): following it would drive the straight jump - across grass - so it is a re-placement
    let jumpG = false;
    // (measured on the target itself, before the physics offset: a placement offset appearing is not a jump)
    if (c && c.ground && o.ground && rawPrev && !c.behind && !synth && !tr.cutting) { const dj = Math.hypot(rawX - rawPrev[0], rawZ - rawPrev[1]); jumpG = dj > Math.max(JUMP_G_M, 4 * Math.max(o.gs || 0, c.v) * dt + 5); }
    const reacq = tr.reacquire && c && err > (o.ground ? 20 : Math.max(30, 2 * Math.hypot(o.vx, o.vz)));
    if (tr.reacquire && c && !reacq && !tr.cutting) tr.reacquire = false;
    if (c && !tr.cutting && (reacq || err > errMax || jumpG)) { const k = 'cut_' + (reacq ? 'gap' : jumpG ? 'jump' : 'err') + (o.ground ? '_g' : '_a'); this.counters[k] = (this.counters[k] || 0) + 1;
      if (this.debugCuts) this.debugCuts.push({ key: tr.key, type: tr.info.icao, cls: T && T.cls, ground: o.ground, cground: c.ground, err: Math.round(err), errMax: Math.round(errMax), v: Math.round(Math.hypot(o.vx, o.vz)), cv: Math.round(c.v), dy: Math.round(o.y - c.y), t: tDisp, reacq, jumpG, mode: o.mode, hist: (tr._mh || []).slice() });
      if (D.valid && D.alpha > 0.01) tr.cutting = reacq ? 'gap' : jumpG ? 'jump' : 'err'; else c = null; }
    if (tr.fadeOut || tr.airHidden || o.hideSeg) { D.alpha = Math.max(0, (D.alpha ?? 0) - dt / CUT_S); tr.cutting = null; }
    if (tr.cutting) { D.alpha = Math.max(0, D.alpha - dt / CUT_S); if (D.alpha <= 0) { this.counters.cuts++; tr.cutting = null; c = null; } }
    if (o.before) c = null;       // before the first fix the hidden body is the target itself (no lag when it appears)
    if ((tr.airHidden || o.hideSeg) && D.alpha <= 0) c = null;   // hidden: re-created at the target when it is drawn again
    if (!c) {
      tr.reacquire = false;
      const hd0 = o.hd != null ? o.hd : (o.gs > 0.5 ? bearR(o.vx, o.vz) : (tr.last && tr.last.hd != null ? tr.last.hd : 0));
      c = tr.ctl = { x: o.x, z: o.z, y: o.y, psi: wrapPi(hd0), v: o.gs, vx: o.vx, vz: o.vz, vy: o.vy || 0, ground: o.ground, w: 0, roll: 0, gear: 1 };
      D.alpha = 0;
    }
    if (!tr.cutting && !tr.fadeOut && !tr.airHidden && !o.hideSeg && D.alpha < 1 && !o.before && !tr.hidden) D.alpha = Math.min(1, D.alpha + dt / CUT_S);
    if (tr.hidden) D.alpha = 0;
    // in a hangar: a rest pose inside a hangar footprint, or a slow ground target (< 3 m/s) whose centre is inside one - it is
    // in (or entering / leaving) the hangar, which has no modelled doors: faded out, never drawn through the walls [inf]
    let inH = o.ground && o.stop && o.rest && o.rest.inHangar ? o.rest.inHangar : null;
    if (!inH && o.ground && (o.gs || 0) < 3 && this.site && !tr.vehicle) { const b = this.site.buildingAt(rawX, rawZ); if (b && /hangar/.test(b.kind || '')) { const sp = tr.park && tr.park.spotId && this.parking ? this.parking.byId.get(tr.park.spotId) : null; if (!(sp && sp.door)) inH = b.name || b.kind; } }
    // (sticky: once in, it stays in while it stays slow within 10 m of a hangar - the GNSS fixes of an aircraft in a hangar
    // door scatter in and out of the footprint)
    if (!inH && tr.inHangarRest && o.ground && (o.gs || 0) < 3 && this.parking && this.parking.hangarNear(rawX, rawZ, 10)) inH = tr.inHangarRest;
    if (inH) { D.alpha = Math.max(0, D.alpha - 2 * dt / CUT_S); tr.inHangarRest = inH; } else tr.inHangarRest = null;
    // (before the first fix the hidden body is held at the target with its heading and speed, not driven towards itself)
    if (o.before) { }
    else if (o.ground && !c.ground) { this.ctlAir(tr, T, c, o, dt, true); }
    else if (o.ground) this.ctlGround(tr, T, c, o, dt);
    else this.ctlAir(tr, T, c, o, dt, false);
    this.attitude(tr, T, c, o, dt);
    D.x = c.x; D.y = c.y; D.z = c.z; D.gs = Math.abs(c.v); D.vs = c.vy; D.ground = c.ground; D.extrap = o.ex || 0; D.valid = true; D.hdg = toDeg(c.psi);
    D.route = !!o.route;
    // the rest pose GroundPhysics places: only the target's own rest pose (a still run, a stale track) - never an older
    // parking pose (fix round 1: a stop on a taxiway used to inherit the pose of the spot the aircraft had left)
    tr.restPose = o.stop && o.rest ? o.rest : null;
    tr._planPh = o.planPh; tr._hideSeg = !!o.hideSeg;
    this.displayPhase(tr, tDisp);
  }
  // Ground body = TRAIL FOLLOWING (new for HWD; replaces sfo3d's pursuit of the target point): the target's positions are
  // laid down as a trail (a polyline) and the body moves ALONG it, at a speed that closes the gap to the target, braked for
  // the curvature ahead (v <= sqrt(latGround x R)) and limited by its acceleration. The body therefore never cuts a corner
  // the target path does not cut: a target routed along the taxi graph keeps the body on the pavement even when the body
  // lags. Heading = the trail tangent over +-h1 (smoothed corners), turned at <= wGround; at rest it pivots to the rest
  // pose heading (wPivot).
  trailPush(c, x, z) {
    const T = c.trail; let n = T.x.length;
    if (n && Math.hypot(x - T.x[n - 1], z - T.z[n - 1]) < 0.25) return;
    // loop removal (fix round 1): a new point that returns to within 2 m of a trail point still ahead of the body closes a
    // spur or a loop (a target that went back and forth: GNSS jitter, a placement offset coming and going) - the body drives
    // the direct way instead of stopping to pivot at every reversal
    for (let k = n - 2, m = 0; k >= 0 && T.s[k] > c.s + 0.5 && m < 400; k--, m++) if (Math.hypot(x - T.x[k], z - T.z[k]) < 2) { T.x.length = T.z.length = T.s.length = k + 1; n = k + 1; break; }
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
    if (!c.ground || !c.trail) { c.ground = true; c.vy = 0; c.trail = { x: [c.x], z: [c.z], s: [0] }; c.s = 0; c.behind = true; }
    // a body that reaches the ground AHEAD of its target (it touched down beyond it) must not turn round to drive back along a
    // trail laid behind it: it holds its line and brakes until the target is ahead of it again, then follows (fix round 1)
    if (c.behind) {
      const f = hvR(c.psi), ahead = (o.x - c.x) * f[0] + (o.z - c.z) * f[1];
      if (ahead < -1 && c.v > 1) {
        const aDec = Math.max(o.gs, c.v) > 15 ? LIM.rollDec : LIM.taxiDec;
        c.v = Math.max(Math.min(c.v, Math.max(o.gs * 0.8, 0)), c.v - aDec * dt); const ox = c.x, oz = c.z; c.x += f[0] * c.v * dt; c.z += f[1] * c.v * dt;
        c.vx = (c.x - ox) / dt; c.vz = (c.z - oz) / dt; c.y = this.groundY(c.x, c.z); c.w = 0; c.trail = { x: [c.x], z: [c.z], s: [0] }; c.s = 0;
        this.counters.groundAhead = (this.counters.groundAhead || 0) + 1; return;
      }
      c.behind = false;
    }
    const cls = T ? T.cls : 'unknown';
    // (review round 3: a planned take-off / landing roll is a roll from its first metre - below 15 m/s the taxi limit of
    // 1.2 m/s2 left the body behind a 1.5 m/s2 SF50 roll)
    const roll = o.rollSeg || Math.max(o.gs, c.v) > 15;
    const aAcc = roll ? (LIM.rollAcc[cls] || 2.5) : LIM.taxiAcc, aDec = roll ? LIM.rollDec : LIM.taxiDec;
    { const Tq = c.trail, n = Tq.x.length; const dEnd = Math.hypot(o.x - Tq.x[n - 1], o.z - Tq.z[n - 1]);
      // a resting target's centimetre jitter is not a path (fix round 2: 0.6 -> 0.3 m - a 0.57-m placement offset of GroundPhysics
      // was filtered out as 'jitter' and the body stayed with its nose 1 sample inside a hangar)
      if (!(o.stop && dEnd < 0.3)) this.trailPush(c, o.x, o.z); }
    const Tr = c.trail, sEnd = Tr.s[Tr.s.length - 1], gap = Math.max(0, sEnd - c.s);
    const h1 = T ? clamp(0.25 * T.L, 1.5, 6) : 2.5;
    // closing speed: the target's speed plus a bounded catch-up (CATCH_MS; a taxiing body never above TAXI_BODY_MAX) [inf]
    let vDes = o.stop ? (gap < 0.1 ? 0 : Math.min(2.5, 0.6 * gap)) : Math.max(0, o.gs + Math.min(0.5 * gap, CATCH_MS) - 0.2);
    if (!roll && !o.stop) vDes = Math.min(vDes, Math.max(o.gs, TAXI_BODY_MAX));
    if (gap > 0.05) vDes = Math.min(vDes, Math.sqrt(2 * aDec * 0.8 * gap) + (o.stop ? 0 : o.gs));    // never overrun the target
    // (review round 3) on a roll a body already at least as fast as its target does not speed up to close the gap - it closes
    // anyway; the catch-up made a landing roll accelerate by ~1.5 kt right after the touchdown
    if (roll && c.v >= o.gs) vDes = Math.min(vDes, c.v);
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
    // (review round 3: not on a fast roll - a body that had just touched down 3 m beside its target braked from 58 to 48 kt
    // for the 'misalignment' and then raced to catch up; at roll speed it steers instead)
    const mis = Math.abs(wrapPi(dirT - c.psi)) / D2R, fac = gap < 0.3 || (roll && c.v > 8 && mis < 45) ? 1 : clamp((60 - mis) / 45, 0, 1);
    if (this.debugCtl === tr.key && (this._dbgN = (this._dbgN || 0) + 1) % 5 === 0) console.log('ctl', this._dbgT, (c.s).toFixed(1), sEnd.toFixed(1), 'dirT', (dirT / D2R).toFixed(0), 'psi', (c.psi / D2R).toFixed(0), 'mis', mis.toFixed(0), 'v', c.v.toFixed(2), 'vDes', vDes.toFixed(2), 'trailN', Tr.x.length, 's0', Tr.s[0].toFixed(1));
    if (fac < 1) vDes = Math.min(vDes, fac * Math.max(c.v, 1.5));
    // (review round 3: on a roll never harder than LIM.rollDec - 1.5 x gave a 5.1 m/s2 jolt right after a touchdown)
    const vPrev = c.v; c.v += clamp(vDes - c.v, -aDec * (roll ? 1 : 1.5) * dt, aAcc * dt); if (c.v < 0) c.v = 0;
    // and it never slides: at walking speed the advance along the path fades out between 20 and 60 deg of misalignment (it
    // waits, braked, while the nose comes round); faster, it brakes at the limit above (never an instant stop: fix round 1)
    const adv = mis < 20 || gap < 0.3 ? 1 : clamp((60 - mis) / 40, 0, 1);
    // (review round 3: braked at the taxi limit, not to zero in one step - a -8 m/s2 spike at walking speed)
    // (the limit counts from the speed before this step's braking above: both used to apply, -6 m/s2 at a taxi start)
    if (adv < 1 && c.v < 1.5) c.v = Math.min(c.v, Math.max(adv * c.v, vPrev - aDec * 1.5 * dt, 0));
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
    // feed-forward of the target's own acceleration (fix round 1): without it the follower lags a turning target by
    // 2 zeta / om x speed - 130 m at 45 m/s - and a pattern turn ended in a re-placement
    let fx = 0, fz = 0; if (tr._ov && !landing) { fx = (o.vx - tr._ov[0]) / dt; fz = (o.vz - tr._ov[1]) / dt; const fm = Math.hypot(fx, fz), fl = Math.max(LIM.airAcc, Math.min(LIM.airAccMax, 1.15 * (tr._aT || 0))); if (fm > fl) { fx *= fl / fm; fz *= fl / fm; } }
    // (fix round 2) the target's own acceleration, smoothed over ~1 s: where the data path itself turns harder than the 31-deg
    // default (a 180-deg base turn flown in a 47-s hole), the body may bank up to 45 deg to stay on it instead of swinging wide
    // and being re-placed [inf: GA aerobatic / steep-turn limit]
    if (tr._ov && !landing) { const aT = Math.hypot(o.vx - tr._ov[0], o.vz - tr._ov[1]) / dt; tr._aT = (tr._aT ?? aT) + (Math.min(aT, 60) - (tr._aT ?? aT)) * Math.min(1, dt / 1.0); }
    tr._ov = [o.vx, o.vz];
    let ax = fx + om * om * (o.x - c.x) + 2 * ze * om * (o.vx - c.vx), az = fz + om * om * (o.z - c.z) + 2 * ze * om * (o.vz - c.vz);
    // (fix round 2) a body that is turning at its limit does not speed up to close a gap: a faster body turns wider, falls
    // further outside a turning target and was re-placed after a 360 / a tight base turn [inf]
    { const sp0 = Math.hypot(c.vx, c.vz), aLimT = clamp(1.15 * (tr._aT || 0), T && T.cls === 'heli' ? LIM.airAcc : LIM.airAccGA, LIM.airAccMax);
      if (sp0 > 5 && !landing) { const ux = c.vx / sp0, uz = c.vz / sp0; let at = ax * ux + az * uz; const an = -ax * uz + az * ux;
        if (Math.abs(an) > 0.8 * aLimT && at > 0 && sp0 >= Math.max(Math.hypot(o.vx, o.vz), o.vRep || 0)) { at = 0; ax = -an * uz; az = an * ux; } } }
    // (fix round 2: jets too get the 6 m/s2 / 31-deg-bank turn - at 4.5 a bizjet climbing out in a 160-deg turn at 250 kt swung
    // ~700 m wide of its data path and was re-placed) [inf]
    const am = Math.hypot(ax, az), aMax = clamp(1.15 * (tr._aT || 0), T && T.cls === 'heli' ? LIM.airAcc : LIM.airAccGA, LIM.airAccMax); if (am > aMax) { ax *= aMax / am; az *= aMax / am; } c._aMax = aMax;
    // (review round 3) the speed itself changes by at most LIM.airAcc: the bank limits above are for turning - a mode handover
    // (plan -> fix-to-fix) gave a -5.1 m/s2 speed step in the air
    { const sp0 = Math.hypot(c.vx, c.vz); if (sp0 > 5) { const ux = c.vx / sp0, uz = c.vz / sp0, at = ax * ux + az * uz, atC = clamp(at, -LIM.airAcc, LIM.airAcc); if (atC !== at) { ax += (atC - at) * ux; az += (atC - at) * uz; } } }
    c.vx += ax * dt; c.vz += az * dt;
    // a fixed-wing aircraft cannot slow below its minimum flying speed: it turns instead (the follower keeps the speed and
    // only the direction changes) [inf: speedsOf vmin]
    if (T && T.cls !== 'heli' && !tr.vehicle) { const vm = this.spd(tr).vmin, sp0 = Math.hypot(c.vx, c.vz); if (sp0 < vm) { if (sp0 > 0.1) { c.vx *= vm / sp0; c.vz *= vm / sp0; } else { const f = hvR(c.psi); c.vx = f[0] * vm; c.vz = f[1] * vm; } } }
    // and it does not race to close a gap: at most AIR_CATCH (1.15 x the target's speed + 3 m/s) [inf]
    // (fix round 2: from the reported speeds as well, and braking at no more than LIM.airAcc - the cap must not stop a body
    // that a jittering short-hole target speed briefly undercuts)
    { const vmax = Math.max(1.15 * Math.max(Math.hypot(o.vx, o.vz), o.vRep || 0) + 3, T && T.cls !== 'heli' ? this.spd(tr).vmin : 0), sp1 = Math.hypot(c.vx, c.vz);
      if (sp1 > vmax && sp1 > 0) { const v2 = Math.max(vmax, Math.min(sp1, (c._vPrev ?? sp1)) - LIM.airAcc * dt); if (v2 < sp1) { c.vx *= v2 / sp1; c.vz *= v2 / sp1; } } }
    c._vPrev = Math.hypot(c.vx, c.vz);
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
    const wMax = heli ? 30 * D2R : Math.max(3 * D2R, Math.min(20 * D2R, Math.max(LIM.airAcc, c._aMax || 0) / Math.max(sp, 1)));
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
    else if (tr.stale) { ph = 'no_signal'; pi = { src: 'inf', rule: 'signal ended here; drawn at its last position (' + ((tr.stalePose && tr.stalePose.rule) || 'newest fix') + ')' }; }
    else if (tr.inHangarRest) { ph = 'hangared'; pi = { src: 'inf', rule: 'standing inside ' + tr.inHangarRest }; }
    else if (!tr.vehicle && tr.ctl) { const r = this.drawnPhase(tr, ph, pi); if (r) { ph = r[0]; pi = r[1]; } }
    if (tr.scope === 'overflight' && PHASES[ph] && PHASES[ph].airborne && !['heli_hover_taxi', 'heli_hover'].includes(ph)) ph = 'overflight';
    if (ph !== tr.phase) { tr.phase = ph; tr._since = f ? f.t : t; }
    tr.phaseInfo = { label: (PHASES[ph] || PHASES.unknown).label, rwy: pi.rwy || null, leg: pi.leg || null, src: pi.src || null, rule: pi.rule || null, since: tr._since || t,
      provisional: !!pi.provisional, tower: towerStatus(t) };
  }

  // the label of the fix the display is at, checked against the DRAWN body (fix round 1): a label that contradicts it (an
  // airborne leg for a body rolling on the runway, 'taxi' for a body 60 ft up, 'parked' for a body moving at 4 m/s) is
  // replaced by the phase the body shows, marked provisional and inferred - the fix label catches up when the classifier
  // decides the episode
  drawnPhase(tr, ph, pi) {
    const r = this.drawnPhase0(tr, ph, pi), c = tr.ctl;
    // (review round 3) a landing roll does not speed up: a body shown as 'landing_roll' that rolls more than 1 m/s faster than
    // the slowest it has been in this roll is re-accelerating (a touch-and-go, or a fast taxi along the runway) - neither the
    // label of the fix before it (shown until the next fix) nor a landing plan's roll-out describes that
    const out = r ? r[0] : ph;
    // (a 'landing roll' that has turned off the runway, or rolls on at taxi speed, is taxiing)
    if (c && c.ground && out === 'landing_roll' && (Math.abs(c.v) < 7.7 || !this.onRunway(c.x, c.z, 0)) && !(tr.dims && tr.dims.cls === 'heli')) { tr._lr = null; return [this.onRunway(c.x, c.z, 0) ? 'runway_taxi' : 'taxi', { ...(r ? r[1] : pi), src: 'inf', rule: 'drawn state: the landing roll has slowed to taxi speed / left the runway', provisional: true }]; }
    if (c && c.ground && out === 'landing_roll' && !(tr.dims && tr.dims.cls === 'heli')) {
      const v = Math.abs(c.v), kt = v / KT, q = tr._lr || (tr._lr = { vmin: v }); q.vmin = Math.min(q.vmin, v);
      if (v > q.vmin + 2.0) { const rw = this.onRunway(c.x, c.z); return [rw && v > 0.75 * this.spd(tr).vr ? 'takeoff_roll' : rw ? 'runway_taxi' : 'taxi', { ...(r ? r[1] : pi), src: 'inf', rule: 'drawn state: rolling faster again after the landing roll', provisional: true }]; }
    } else tr._lr = null;
    return r;
  }
  drawnPhase0(tr, ph, pi) {
    const c = tr.ctl, P = PHASES[ph] || PHASES.unknown, heli = tr.dims && tr.dims.cls === 'heli';
    const hAgl = (c.y - this.groundY(c.x, c.z)) / FT, v = Math.abs(c.v), kt = v / KT;
    const mk = (p, why) => [p, { ...pi, src: 'inf', rule: 'drawn state: ' + why, provisional: true }];

    // inside a take-off / landing plan the plan says what the body is doing; the fix labels of the two fixes around the hole
    // (hold short ... climbing out) say nothing about the 46 s between them - unless the classifier already revised them to
    // the episode (touch-and-go, stop-and-go, take-off / landing roll)
    if (tr._planPh && tr._planPh !== ph && !['touch_and_go', 'stop_and_go', 'takeoff_roll', 'landing_roll', 'go_around', 'low_pass'].includes(ph)) {
      const pp = tr._planPh; const ok = c.ground ? !(PHASES[pp] || {}).airborne : (PHASES[pp] || {}).airborne; if (ok) return mk(pp, 'take-off / landing inside a polling hole');
      // (review round 3) the body is still in the air over a planned roll (touching down) or still on the ground under a
      // planned climb (lifting off): final / take-off roll, not the label of the fix before the hole
      if (!c.ground && (pp === 'landing_roll' || pp === 'taxi')) return mk('final', 'touching down (reconstructed)');
      if (c.ground && pp === 'initial_climb') return mk('takeoff_roll', 'lifting off (reconstructed)');
    }
    if (heli) {
      if (ph === 'heli_ground' && !c.ground && hAgl > 10) return mk(kt > 5 ? 'heli_hover_taxi' : 'heli_hover', 'off the ground');
      if ((ph === 'heli_hover' || ph === 'heli_hover_taxi' || ph === 'heli_air') && c.ground && v < 0.5) return mk('heli_ground', 'on the ground');
      return null;
    }
    // (review round 3, m5) a body labelled taxiing / holding / running up at more than 35 kt is rolling for take-off or landing
    if (c.ground && kt > 35 && ['taxi', 'hold_short', 'runup', 'line_up', 'parked', 'runway_taxi'].includes(ph)) {
      const rw = this.onRunway(c.x, c.z), prev = tr._vPrev ?? v; tr._vPrev = v;
      return mk(rw ? (v >= prev - 0.02 ? (v > 0.75 * this.spd(tr).vr ? 'takeoff_roll' : 'runway_taxi') : 'landing_roll') : 'taxi', 'rolling at ' + kt.toFixed(0) + ' kt');
    }
    if (c.ground) {
      if (P.airborne && kt > 5) {
        const rw = this.onRunway(c.x, c.z);
        if (!rw) return mk('taxi', 'on the ground, off the runway');
        const prev = tr._vPrev ?? v; tr._vPrev = v;
        return mk(ph === 'initial_climb' || ph === 'upwind' || ph === 'departing' ? 'takeoff_roll' : v >= prev - 0.02 && kt > 30 && !['final', 'base', 'arriving', 'downwind', 'go_around', 'low_pass'].includes(ph) ? 'takeoff_roll' : 'landing_roll', 'rolling on the runway');
      }
      // (fix round 2: > 0.5 m/s, ~1 kt - a body leaving its spot at 2-3 kt along a route stayed 'parked' 90 m from the spot)
      if (ph === 'parked' && v > 0.5) return mk('taxi', 'moving');
      return null;
    }
    if (P.group === 'ground' || P.group === 'runway') {
      if (hAgl > 50) return mk(c.vy > 0.5 ? 'initial_climb' : c.vy < -0.5 ? 'final' : 'low_pass', 'airborne');
    }
    return null;
  }
  // ---------------------------------------------------------------- persistence (live mode, this browser only)
  // What is stored (localStorage STORE_KEY, record format v 2, never sent anywhere): per parked aircraft its track key (the
  // ICAO address for an unmasked aircraft), ICAO type, emitter category, park pose (spot id / zone / pose only) and its newest
  // fix / receive times, for up to PARK_KEEP_MS after the newest receive. No registration, callsign, operator or N-number.
  // D1-masked tracks are NOT stored: their keys are salted per relay process (hwd_live_server.py D1), so a remembered key
  // never matches the same aircraft after a relay restart and would leave a ghost beside it (fix round 1).
  // D1 (fix round 3, m6: a key used to be stored whatever happened after, and restored WITH an N-number derived from it):
  //  - save: a key is written only while its aircraft is unflagged as far as this page knows - its identity came unmasked
  //    from the relay (no mask / maskWhy, no late-flag forget, not withheld after a forget horizon) - and the key is a plain
  //    address (6 hex, or '~' + 6 hex). A restored record the relay has not re-published yet is carried forward as it was;
  //  - load: only v 2 records (v 1 was written before these rules: purged), received within PARK_KEEP_MS, plain keys. The
  //    restored aircraft shows its TYPE ONLY, with no N-number derived from the stored key, until the relay re-publishes
  //    that key unmasked (setInfo then builds the identity from the relay's own record; a flagged aircraft is published only
  //    under its masked key, so it never re-validates a stored one). Storage is rewritten at once (purges everything else);
  //  - forgetHorizon (relay 'forget_horizon', js/live/feed.js): every record is purged; only re-validated aircraft return.
  saveParkedSoon() { if (!this.persist) return; clearTimeout(this._saveT); this._saveT = setTimeout(() => this.saveParked(), 2000); }
  saveParked() {
    if (!this.persist || typeof localStorage === 'undefined') return;
    try {
      const out = [];
      for (const tr of this.tracks.values()) {
        if (!(tr.park && tr.park.pose && (tr.stale || tr.phase === 'parked')) || !PERSIST_KEY.test(String(tr.key)) || tr.d1Late) continue;
        const I = tr.info || {}, D = tr.ident || {};
        if (I.masked || I.maskWhy || D.masked || (D.withheld && D.withheld !== 'restored')) continue;
        const P = tr.park, pose = P.pose;
        out.push({ k: tr.key, t: I.icao || null, c: I.category || null, f: tr.lastFixT, r: tr.lastRecv,
          p: { spotId: P.spotId ?? null, kind: P.kind ?? null, zone: P.zone ?? null, src: P.src ?? null, inside: !!P.inside, hangar: P.hangar ?? null,
               pose: { x: pose.x, z: pose.z, hdg: pose.hdg ?? null }, headed: !!P.headed, hdgSrc: P.hdgSrc ?? null, t0: P.t0 ?? null } });
      }
      localStorage.setItem(STORE_KEY, JSON.stringify({ v: 2, saved: Date.now(), parked: out }));
    } catch (e) { }
  }
  loadParked() {
    if (typeof localStorage === 'undefined') return;
    let raw = null, j = null;
    try { raw = localStorage.getItem(STORE_KEY); j = JSON.parse(raw || 'null'); } catch (e) { j = null; }
    const now = Date.now(); let kept = 0, dropped = 0;
    try {
      if (j && j.v === 2) for (const q of Array.isArray(j.parked) ? j.parked : []) {
        const P = q && q.p, pose = P && P.pose;
        if (!q || typeof q.k !== 'string' || !PERSIST_KEY.test(q.k) || !(now - q.r <= PARK_KEEP_MS) || this.tracks.has(q.k) || !pose || !Number.isFinite(pose.x) || !Number.isFinite(pose.z)) { dropped++; continue; }
        const icao = typeof q.t === 'string' && /^[A-Z0-9]{2,4}$/.test(q.t) ? q.t : null, cat = typeof q.c === 'string' && /^[A-D][0-7]$/.test(q.c) ? q.c : null;
        const tr = new Track(q.k); tr.info = { icao, category: cat, masked: false }; tr.ident = withheldIdent(tr.info, 'restored'); tr.dims = gaDims(icao, cat);
        tr.stale = true; tr.park = P; tr.hidden = !!P.inside; tr.lastFixT = q.f; tr.lastRecv = q.r; tr.firstSeen = q.r; tr.restPose = pose; tr.stalePose = pose; tr.restored = true; this.restoredN = (this.restoredN || 0) + 1;
        tr.fx.push({ t: q.f, x: pose.x, z: pose.z, px: pose.x, pz: pose.z, y: this.groundY(pose.x, pose.z), ground: true, g: true, gs: 0, gsm: 0, vx: 0, vz: 0, dir: 0, hd: (pose.hdg || 0) * D2R, hdReal: false, ph: 'parked', pi: { src: 'obs', rule: 'remembered (this browser)' } });
        tr.scope = 'hwd'; this.tracks.set(q.k, tr); kept++;
        if (this.parking && P.spotId) { const s = this.parking.byId.get(P.spotId); if (s) this.parking.occupy(q.k, s); }
      } else if (j && Array.isArray(j.parked)) dropped += j.parked.length;
    } catch (e) { }
    this.counters.persistRestored = kept; this.counters.persistDropped = dropped;
    if (raw != null && this.persist) this.saveParked();   // rewrite now: only the records restored above stay stored
  }
  // the relay's 'forget_horizon' (fix round 3, m6; js/live/feed.js StreamFeed onHorizon): late-flag forgets this page should
  // have had may be lost (it was away longer than the relay keeps them, or the relay restarted). No identity is trusted that
  // the relay does not publish in its current snapshot (`present`): every other track keeps its body but shows its type only
  // (not claimed LADD / PIA) until the relay re-publishes its key unmasked, and the persisted records are purged - only
  // re-validated parked aircraft are written back. -> the number of tracks whose identity was withheld.
  forgetHorizon({ present = [] } = {}) {
    const P = new Set(present); let n = 0;
    for (const tr of this.tracks.values()) {
      if (P.has(tr.key) || (tr.ident && tr.ident.masked)) continue;
      const I = tr.info || (tr.info = {});
      Object.assign(I, { flight: null, reg: null, ownOp: null, squawk: null, mx: I.mx ? { r: null, t: I.mx.t || null, d: I.mx.d || null, op: null } : null });
      tr.ident = withheldIdent(I, 'horizon'); n++;
    }
    this.counters.d1Horizon = (this.counters.d1Horizon || 0) + 1; this.counters.d1HorizonTracks = (this.counters.d1HorizonTracks || 0) + n;
    if (this.persist && typeof localStorage !== 'undefined') { try { localStorage.removeItem(STORE_KEY); } catch (e) { } this.saveParked(); }
    return n;
  }
}

// (fix round 3, m6) persisted keys: a plain ICAO address or a '~' (non-ICAO) address - never a D1-masked 'x' key or a split
// '~…@fi' key
const PERSIST_KEY = /^~?[0-9a-f]{6}$/;
// a type-only identity that is NOT a D1 mask: the aircraft is not known to be flagged, but its identity has not been
// re-validated by the relay (restored from this browser's storage, or held over a forget horizon). The key is not passed
// (''), so no N-number is derived from it; setInfo replaces this identity when the relay re-publishes the key.
function withheldIdent(info, why) {
  const mx = info.mx ? { r: null, t: info.mx.t || null, d: info.mx.d || null, op: null } : null;
  return Object.assign(identity({ icao: info.icao || null, desc: info.desc || null, category: info.category || null, mx }, '', null), { withheld: why });
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
