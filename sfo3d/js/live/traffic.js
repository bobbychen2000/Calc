// Live traffic engine: turns the relay's ~1 Hz merged ADS-B stream into smoothly moving, phase-aware aircraft at SFO.
//
// Design and evidence: docs/research/traffic_audit.md (s.6), docs/research/realtime_feeds.md, docs/research/realtime_impl.md.
//  * Reports: position time = provider now - seen_pos (relay: _pt). WGS 84 -> world with geo.js wgs84ToWorld.
//    Hygiene: surface `track` ignored (audit s.4.3), position jumps rejected, vehicles sticky (F8).
//  * Flight phase from KINEMATICS, never from the transponder air/ground flag (it is the 100 kt WOW override, EASA
//    CS-ACNS AMC1 ACNS.D.ELS.020; audit s.4.6 -- and ~50 kt on E175s, observed 24 Sep day recording):
//    touchdown = onset of >= 1 kt/s deceleration after the threshold; liftoff = sustained climb; take-off roll needs
//    >= 50 kt or >= 1.5 kt/s acceleration; Bayesian runway assignment on final; go-around detector; cold starts.
//  * Display: a short adaptive delay (1-3 s) so that motion is interpolated (Hermite) between real reports; dead
//    reckoning <= 5 s. The drawn aircraft is a kinematic body that FOLLOWS that target with bounded acceleration, jerk,
//    turn rate and (on the ground) a nose-wheel steering radius, moving along its nose (no sideways sliding) -- so a
//    late or noisy report is absorbed as a smooth correction (~0.8 s), never as a jump or a morph.
//  * Surface: taxiing reports are map-matched to the OSM taxiway graph (data/sfo_taxigraph.js); parked aircraft use
//    the median of their reports; stand matching uses SFO's own allocation (relay /api/gates) when available, else
//    geometry + heading; docking follows the stand's lead-in line.
import * as GEO from '../geo.js';
import { parseCallsign, typeInfo, liveryForAirline } from './lookup.js';
import { typeForIcao } from './aircraft.js';
import { TYPES } from '../aircraft/types.js';

const { runwayByEnd, RUNWAYS, GROUND_Y, stToWorld } = GEO;
// ADS-B positions are WGS 84; the world frame is NAD83(2011) (geo.js, docs/requests/geo_frame_switch.md). Fall back to
// llToWorld on an older geo.js without wgs84ToWorld.
const toWorld = GEO.wgs84ToWorld || GEO.llToWorld;
const toWgs84 = GEO.worldToWgs84 || GEO.worldToLL || null;

const FT = 0.3048, KT = 0.514444, NM = 1852, DEG = Math.PI / 180, GRAV = 9.81;
const GEOID_M = 32.29;          // EGM96 undulation at the ARP is -32.29 m (realtime_feeds.md s.4.6): MSL = HAE + 32.29 m
export const DELAY_MS = 1500;   // initial display delay; adapted between DELAY_MIN and DELAY_MAX to the report ages
export const DELAY_MIN = 1000, DELAY_MAX = 3000;
const DR_MAX_S = 5;             // dead reckoning horizon past the newest report
const STALE_AIR_MS = 60000, STALE_GROUND_MS = 75000, PARK_KEEP_MS = 8 * 3600e3, VEH_KEEP_MS = 120000, MOVING_LOST_MS = 45000;
// a settled parked aircraft (bridge docked) keeps its displayed pose through parked-pose estimate changes smaller than
// this: the real aircraft does not move while docked, only our estimate does (review round 1: bridges misdocked when the
// pose was refined after docking)
// (the parked-pose median moves in >= 4 m steps by design -- 4 m hysteresis, stationary() -- so the lock tolerates 6 m / 10
// deg at a stand pose, x1.4 for an own-pose or free parking whose median carries the full report scatter)
const LOCK_M = 6, LOCK_DEG = 10 * DEG;
const CUT_S = 0.4;               // fade out / fade in (s) of a re-placement (data gap, re-acquisition): never a visible jump
// an arrival's jet bridge starts docking this long after the drawn aircraft came to rest (+ gates.js DOCK_DELAY 12 s):
// engines are shut down and the beacon is off before a bridge approaches [inferred design value; see syncBridge]
const DOCK_WAIT_MS = 20000;
const REACQ_PARK_M = 15;         // a parked aircraft heard again within this distance of its parked pose has not moved
const STORE_KEY = 'sfolive.parked.v4'; // v4: stand names back to gate numbers, new stands (static_geometry_round1.md #4)
// audit s.6.4-6.6 (ft/min, kt/s, ft, ft/min). DECEL_TD: flare deceleration before touchdown was 0.4-0.8 kt/s at night
// (audit s.3.2) but up to 1.39 kt/s by day (SKW5562 CRJ2, 24 Sep 15:19Z); after touchdown 2.4-5.8 kt/s -> 1.6 kt/s
const VR_CLIMB = 192, DECEL_TD = 1.6, GA_CLIMB_FT = 150, GA_VR = 500;
// touchdown point predicted before the deceleration is seen: metres past the landing threshold. Observed 24 Sep:
// night 520-959 m (6 arrivals, audit s.3.2), day 549-894 m (16 arrivals, replay_events 15:13-15:45Z); median ~770 m.
const TD_PRED_M = 770;
// observed liftoff groundspeeds (kt) by ICAO type, 24 Sep recording (audit s.3.3 + day replay); others: by length
const LIFTOFF_KT = { A21N: 157, A321: 165, A320: 150, A319: 145, B39M: 172, B38M: 172, B738: 162, B739: 173, A359: 172, B77W: 175, B772: 157,
  B789: 174, E75L: 140, E75S: 140, C680: 124, G280: 133 };
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const sstep = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
const wrapPi = (a) => { a = (a + Math.PI) % (2 * Math.PI); if (a < 0) a += 2 * Math.PI; return a - Math.PI; };
const lerpAng = (a, b, u) => a + wrapPi(b - a) * u;
const median = (a) => { if (!a.length) return null; const s = a.slice().sort((p, q) => p - q); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
const circMedian = (hs) => { if (!hs.length) return null; let sx = 0, sz = 0; for (const h of hs) { sx += Math.sin(h); sz += Math.cos(h); } const m = Math.atan2(sx, sz); return wrapPi(m + median(hs.map(h => wrapPi(h - m)))); };
export const hdgVec = (h) => [Math.sin(h), -Math.cos(h)];   // world (x east, z south) unit vector for a true heading
export const vecHdg = (x, z) => Math.atan2(x, -z);
export const ANT = 0.2; // ADS-B position reference (GNSS antenna) assumed ~20% of the length behind the nose
// ...except the Airbus A318-A321 family, whose parked reports lie 1-5 m behind the stand nose (median ~2.5 m; 46 parked
// stays of AAL/JBU/FFT/UAL/DAL/ASA/ACA A32x in the 24 Sep recording, measured against the surveyed stand noses; Boeing,
// Embraer, A220: 6-17 m) -- stands_rebuild.md s.3.2: "referenced near the nose (antenna offset compensated)"
export const ANT_A32X = 0.06;
export const antOf = (T, L = 38) => (T && /^Airbus A3(18|19|20|21)/.test(T.name || '') ? ANT_A32X : ANT) * (T ? T.L : L);
const typeOf = (tr) => (tr.model && TYPES[tr.model.t]) || null;

// stop-point family of an ICAO designator: the families of data/sfo_stands.json `type_stops` (tools/stands/geom.py
// FAMILY + ALIAS, docs/requests/static_geometry_round2.md #3)
const FAMILY = {};
for (const [f, ts] of Object.entries({ B737: 'B736 B737 B738 B739 B37M B38M B39M B3XM', A320: 'A319 A19N A320 A20N A321 A21N', B757: 'B752 B753',
  B767: 'B762 B763 B764', EJET: 'E170 E75L E75S E190 E195', A220: 'BCS1 BCS3', CRJ: 'CRJ2 CRJ7 CRJ9', B777: 'B772 B77L B773 B77W B779',
  B787: 'B788 B789 B78X', A330: 'A332 A333 A338 A339', A350: 'A359 A35K', B747: 'B744 B748', A380: 'A388', MD11: 'MD11' })) for (const t of ts.split(' ')) FAMILY[t] = f;
const TYPE_ALIAS = { E175: 'E75L', B787: 'B789', B76W: 'B763', B75W: 'B752', E295: 'E195' };   // (geom.py ALIAS)
const icaoN = (icao) => icao ? (TYPE_ALIAS[icao] || icao) : null;
export const familyOf = (icao) => FAMILY[icaoN(icao)] || null;
// does an aircraft of type T (ICAO designator icao) fit a stand: its class limits / span_max / len_max; the stand's
// `types_ok` whitelist where the data sets one (E10/E12, F19/F20: only with the types SFO parks there do the neighbours
// clear each other -- static_geometry_round2.md #2; `strict` false = SFO's own allocation, which is followed); the
// A380 / 747-8 / 777-9 only on the stands the data marks `a380` (A6, A11, G13: round2 #1). Unknown types are allowed.
function standFits(g, T, icao = null, strict = true) {
  if (strict && g.typesOk && g.typesOk.length && icao && !g.typesOk.includes(icaoN(icao))) return false;
  if (!T || g.remote || !g.maxSpan) return true;
  const span = T.wing ? T.wing.span : 36;
  if (span <= g.maxSpan + 0.6 && T.L <= g.maxLen + 2) return true;
  return !!g.a380 && span <= 80;
}
// the stand's stop point for this family, metres along the stand axis from the stand nose (- = short of it): the data's
// `type_stops` (ADS-B evidence per family and stand, static_geometry_round2.md #3), else 0 (the stand nose)
function stopAlong(g, icao) { const f = familyOf(icao); const s = f && g.typeStops && g.typeStops[f]; return s && Number.isFinite(s.along) ? Math.min(0, s.along) : 0; }

// ---------------------------------------------------------------- runways (world frame)
export const RWY = [];
for (const r of RUNWAYS) for (const end of r.ends) {
  const R = runwayByEnd(end);
  RWY.push({ name: end, start: [R.from[0], -R.from[1]], thr: [R.thr[0], -R.thr[1]], dir: [R.dir[0], -R.dir[1]], len: R.length, hdg: Math.atan2(R.dir[0], R.dir[1]), pair: r.ends.join('/'), disp: R.disp });
}
const RWYN = Object.fromEntries(RWY.map(R => [R.name, R]));
// the parallel runway of each runway end (same direction within 2 deg, centrelines < 1.5 km apart): 28L <-> 28R etc.
const PARALLEL = {};
for (const R of RWY) for (const Q of RWY) { if (Q === R || Math.abs(wrapPi(Q.hdg - R.hdg)) > 2 * DEG) continue; const dx = Q.thr[0] - R.thr[0], dz = Q.thr[1] - R.thr[1]; if (Math.abs(-dx * R.dir[1] + dz * R.dir[0]) < 1500) PARALLEL[R.name] = Q.name; }
// the runway an arrival on final is shown for: its own name once the assignment is firm, else the parallel pair
// ("28L/28R"): far out the two centrelines (230 m apart at SFO) cannot be told apart reliably from the position alone
export function finalRwyLabel(tr) {
  const n = (tr.finalInfo && tr.finalInfo.R.name) || tr.m.rwy; if (!n) return null;
  if (tr.m.rwyFirm !== false || !PARALLEL[n]) return n;
  return [n, PARALLEL[n]].sort().join('/');
}
function rwyCoords(R, x, z) { const dx = x - R.thr[0], dz = z - R.thr[1]; return [dx * R.dir[0] + dz * R.dir[1], -dx * R.dir[1] + dz * R.dir[0]]; }
function runwayAt(x, z, halfW = 36) { // physical runway under a ground position -> [RWY entries for both directions]
  for (const R of RWY) {
    const dx = x - R.start[0], dz = z - R.start[1];
    const a = dx * R.dir[0] + dz * R.dir[1], c = -dx * R.dir[1] + dz * R.dir[0];
    if (a > -40 && a < R.len + 40 && Math.abs(c) < halfW) return RWY.filter(q => q.pair === R.pair);
  }
  return null;
}
function alignedRunway(list, h, tol = 15 * DEG) { let best = null, bd = tol; for (const R of list) { const d = Math.abs(wrapPi(h - R.hdg)); if (d < bd) { bd = d; best = R; } } return best; }
export const inAirport = (x, z) => x > -2700 && x < 1950 && z > -2350 && z < 1800;

// ---------------------------------------------------------------- taxi graph (OSM, data/sfo_taxigraph.js)
export class TaxiNet {
  constructor(G) {
    this.ok = !!(G && G.edges && G.edges.length); if (!this.ok) return;
    this.hw = G.halfWidth || 7.6; this.ways = G.ways || []; this.C = 40; this.grid = new Map();
    this.E = G.edges.map(e => { const dx = e[2] - e[0], dz = e[3] - e[1], L = Math.hypot(dx, dz); return { x0: e[0], z0: e[1], x1: e[2], z1: e[3], ux: dx / L, uz: dz / L, L, w: e[4], rw: (this.ways[e[4]] || {}).kind === 'runway' }; });
    this.E.forEach((e, i) => { const n = Math.ceil(e.L / 10); for (let k = 0; k <= n; k++) { const x = e.x0 + (e.x1 - e.x0) * k / n, z = e.z0 + (e.z1 - e.z0) * k / n; const key = Math.floor(x / this.C) + ',' + Math.floor(z / this.C); let s = this.grid.get(key); if (!s) this.grid.set(key, s = new Set()); s.add(i); } });
    this.aprons = (G.aprons || []).map(r => { let x0 = 1e9, z0 = 1e9, x1 = -1e9, z1 = -1e9; for (const p of r) { x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0]); z0 = Math.min(z0, p[1]); z1 = Math.max(z1, p[1]); } return { r, bb: [x0, z0, x1, z1] }; });
    this.leadins = G.leadins || [];
  }
  cand(x, z) { const out = new Set(); const i = Math.floor(x / this.C), j = Math.floor(z / this.C); for (let a = -1; a <= 1; a++) for (let b = -1; b <= 1; b++) { const s = this.grid.get((i + a) + ',' + (j + b)); if (s) for (const k of s) out.add(k); } return out; }
  proj(e, x, z) { const u = clamp((x - e.x0) * e.ux + (z - e.z0) * e.uz, 0, e.L); const px = e.x0 + e.ux * u, pz = e.z0 + e.uz * u; return { px, pz, d: Math.hypot(x - px, z - pz), u }; }
  // best centreline segment for a moving aircraft: lateral distance + heading agreement (either direction along the
  // edge) + continuity with the previously matched way (a one-step Viterbi)
  match(x, z, h, prevWay, maxD = 10, maxDh = 35 * DEG) {
    if (!this.ok) return null; let best = null, bs = 1e9;
    for (const k of this.cand(x, z)) {
      const e = this.E[k]; const p = this.proj(e, x, z); if (p.d > maxD) continue;
      let dh = 0; if (h != null) { const eh = vecHdg(e.ux, e.uz); dh = Math.min(Math.abs(wrapPi(h - eh)), Math.abs(wrapPi(h - eh - Math.PI))); if (dh > maxDh) continue; }
      const s = (p.d / 4) ** 2 + (dh / (12 * DEG)) ** 2 + (prevWay != null && e.w !== prevWay ? 0.6 : 0);
      if (s < bs) { bs = s; best = { ...p, e, k, way: e.w, ux: e.ux, uz: e.uz }; }
    }
    return best;
  }
  inApron(x, z) { for (const a of this.aprons) { if (x < a.bb[0] || x > a.bb[2] || z < a.bb[1] || z > a.bb[3]) continue; if (inRing(a.r, x, z)) return true; } return false; }
  paved(x, z) {
    if (!this.ok) return false;
    for (const k of this.cand(x, z)) { const e = this.E[k]; const p = this.proj(e, x, z); if (p.d < (e.rw ? 30.5 : this.hw)) return true; }
    return this.inApron(x, z);
  }
}

// ---------------------------------------------------------------- gates in world coordinates
function prepGates(gates, raw) {
  const o = stToWorld(0, 0, 0);
  const rec = new Map(((raw && raw.stands) || []).map(s => [s.name, s]));
  for (const g of gates) {
    const R = rec.get(g.name); // the rebuilt stand record (docs/research/stands_rebuild.md): AODB names, exclusions
    if (R) { if (!g.aodb && R.aodb) g.aodb = R.aodb; if (!g.gateName && R.gate) g.gateName = R.gate; if (!g.excl && R.excl) g.excl = R.excl; if (!g.altOf && R.alt_of) g.altOf = R.alt_of; }
    const n = stToWorld(g.nose[0], g.nose[1], 0), d = stToWorld(g.dir[0], g.dir[1], 0), a = stToWorld(g.attach[0], g.attach[1], 0);
    const dx = d[0] - o[0], dz = d[2] - o[2], l = Math.hypot(dx, dz);
    g.w = { x: n[0], z: n[2], dx: dx / l, dz: dz / l, hdg: vecHdg(dx / l, dz / l), ax: a[0], az: a[2] };
    g.occupant = null;
    // every name SFO may use for this stand: our name, hold-room aliases, and fields of the rebuilt stand set
    // (docs/research/stands_rebuild.md: SFO names, suffixed / MARS alternates) when present
    const names = new Set([g.name, ...(g.alias || [])]);
    for (const k of ['aodb', 'gateName', 'sfo', 'sfoName', 'sfoNames', 'alt', 'alts', 'alternates', 'mars', 'names']) { const v = g[k] ?? (g.src && g.src[k]); if (Array.isArray(v)) v.forEach(s => s && names.add(String(s))); else if (typeof v === 'string') names.add(v); }
    g.names = [...names].map(s => String(s).toUpperCase());
  }
  return gates;
}
// taxiway polygons (world x,z) for telling "waiting on a taxiway" from "parked on a ramp"
function prepPolys(airport) {
  const P = [];
  for (const t of (airport && airport.taxiways) || []) for (const poly of t.polys) {
    let x0 = 1e9, z0 = 1e9, x1 = -1e9, z1 = -1e9; for (const p of poly[0]) { x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0]); z0 = Math.min(z0, p[1]); z1 = Math.max(z1, p[1]); }
    P.push({ rings: poly, bb: [x0, z0, x1, z1] });
  }
  return P;
}
function inRing(r, x, z) { let c = false; for (let i = 0, j = r.length - 1; i < r.length; j = i++) { const a = r[i], b = r[j]; if ((a[1] > z) !== (b[1] > z) && x < (b[0] - a[0]) * (z - a[1]) / (b[1] - a[1]) + a[0]) c = !c; } return c; }
function inPolys(P, x, z) { for (const q of P) { if (x < q.bb[0] || x > q.bb[2] || z < q.bb[1] || z > q.bb[3]) continue; if (inRing(q.rings[0], x, z) && !q.rings.slice(1).some(h => inRing(h, x, z))) return true; } return false; }

// ---------------------------------------------------------------- track
class Track {
  constructor(hex) {
    this.hex = hex; this.reps = []; this.info = {}; this.firstSeen = 0; this.lastFixT = 0; this.lastRecv = 0;
    this.phase = 'new'; this.dirSFO = null; this.runway = null; this.gate = null; this.route = undefined; this.finalInfo = null;
    this.m = { phase: 'new', since: 0, rwy: null, logp: {}, td: null, lo: null, flagAir: null, climbN: 0, geomRef: [], minAlt: null, decidedAt: null, exitT: null, gaT: null };
    this.hist = [];                  // [(t, phase, runway)] machine phase history (data time), for display-time labels
    this.air = [];                   // [(t, ground bool)] kinematic air/ground timeline (data time)
    this.still = [];                 // stationary reports (for the median parked pose)
    this.groundSFO = false; this.landedAt = 0; this.liftoffAt = 0; this.pushback = false; this.stale = false; this.vehicle = false;
    this.altBias = null; this.rejects = 0; this.matchWay = null;
    this.disp = { x: 0, y: GROUND_Y, z: 0, hdg: 0, pitch: 0, roll: 0, gear: 1, flaps: 0, spoilers: 0, gs: 0, vs: 0, ground: true, valid: false, extrap: 0 };
    this.ctl = null;
  }
  get last() { return this.reps[this.reps.length - 1]; }
  get fixes() { return this.reps; }
  phaseAt(t) { const H = this.hist; for (let i = H.length - 1; i >= 0; i--) if (H[i][0] <= t) return H[i]; return H[0] || null; }
  groundAt(t, fallback) { const A = this.air; for (let i = A.length - 1; i >= 0; i--) if (A[i][0] <= t) return A[i][1]; return fallback; }
}

// Hermite sample of the report buffer at time t (ms) -> target {x,z,y,vx,vz,vy,gs,ex} (ex = seconds of dead reckoning)
function sampleReps(F, t, o) {
  const n = F.length;
  o.push = false;
  if (t <= F[0].t) { fill(o, F[0], 0); if (!F[0].ground) { const b = (F[0].t - t) / 1000; o.x -= o.vx * b; o.z -= o.vz * b; o.y -= o.vy * b; } return o; } // before the first report: back along its velocity
  const L = F[n - 1];
  if (t >= L.t) {
    const dt = (t - L.t) / 1000; o.ex = dt;
    const ground = L.ground;
    let vx = L.vx, vz = L.vz, x = L.px, z = L.pz;
    const w = L.turn || 0;
    const t1 = Math.min(dt, DR_MAX_S);
    if (Math.abs(w) > 1e-4) { // constant turn rate for the first seconds (heading of velocity)
      const sp = Math.hypot(vx, vz), h0 = vecHdg(vx, vz), h1 = h0 + w * t1;
      x += sp / w * (Math.cos(h0) - Math.cos(h1)); z -= sp / w * (Math.sin(h1) - Math.sin(h0)); const v = hdgVec(h1); vx = v[0] * sp; vz = v[1] * sp;
    } else { x += vx * t1; z += vz * t1; }
    const rest = dt - t1;
    if (rest > 0) {
      if (ground) { const k = 2.0 * (1 - Math.exp(-rest / 2.0)); x += vx * k; z += vz * k; const d = Math.exp(-rest / 2.0); vx *= d; vz *= d; } // smooth stop
      else { x += vx * rest; z += vz * rest; }
    }
    o.x = x; o.z = z; o.vx = vx; o.vz = vz; o.acc = 0; o.nh = L.hd + (Math.hypot(vx, vz) > 0.5 ? wrapPi(vecHdg(vx, vz) - vecHdg(L.vx, L.vz || 1e-9)) : 0);
    o.y = ground ? GROUND_Y : L.y + (L.vs || 0) * Math.min(dt, 10); o.vy = ground || dt > 10 ? 0 : (L.vs || 0); o.gs = Math.hypot(vx, vz); o.ground = ground; o.push = !!L.push;
    return o;
  }
  let i = n - 1; while (i > 0 && F[i - 1].t > t) i--;
  const a = F[i - 1], b = F[i];
  const dtm = b.t - a.t, dt = dtm / 1000, u = (t - a.t) / dtm;
  const cx = (b.px - a.px) / dt, cz = (b.pz - a.pz) / dt, cs = Math.hypot(cx, cz);
  let va = [a.vx, a.vz], vb = [b.vx, b.vz];
  const ok = (v) => Math.hypot(v[0] - cx, v[1] - cz) < Math.max(3, 0.35 * cs);
  const lin = dt > (a.ground ? 20 : 12) || a.ground !== b.ground;
  if (lin || !ok(va)) va = [cx, cz]; if (lin || !ok(vb)) vb = [cx, cz];
  const u2 = u * u, u3 = u2 * u;
  const h00 = 2 * u3 - 3 * u2 + 1, h10 = u3 - 2 * u2 + u, h01 = -2 * u3 + 3 * u2, h11 = u3 - u2;
  const d00 = (6 * u2 - 6 * u) / dt, d10 = 3 * u2 - 4 * u + 1, d01 = (-6 * u2 + 6 * u) / dt, d11 = 3 * u2 - 2 * u; // for the vertical rate
  o.x = h00 * a.px + h10 * dt * va[0] + h01 * b.px + h11 * dt * vb[0];
  o.z = h00 * a.pz + h10 * dt * va[1] + h01 * b.pz + h11 * dt * vb[1];
  // velocity: the reported velocities interpolated (smooth; the Hermite derivative carries the position noise)
  o.vx = va[0] + (vb[0] - va[0]) * u; o.vz = va[1] + (vb[1] - va[1]) * u;
  o.acc = (Math.hypot(vb[0], vb[1]) - Math.hypot(va[0], va[1])) / dt; // speed change between the reports (feed-forward)
  if (!a.ground && !b.ground) {
    const cy = (b.y - a.y) / dt; let sa = a.vs ?? cy, sb = b.vs ?? cy;
    if (Math.abs(sa - cy) > Math.max(3, Math.abs(cy))) sa = cy; if (Math.abs(sb - cy) > Math.max(3, Math.abs(cy))) sb = cy;
    o.y = h00 * a.y + h10 * dt * sa + h01 * b.y + h11 * dt * sb; o.vy = sa + (sb - sa) * u; // reported rates (smooth)
  } else { o.y = a.y + (b.y - a.y) * u; o.vy = (b.y - a.y) / dt; }
  o.gs = Math.hypot(o.vx, o.vz); o.ground = u < 0.5 ? a.ground : b.ground; o.ex = 0; o.nh = lerpAng(a.hd, b.hd, u); o.push = !!(b.push || (u < 0.5 && a.push));
  return o;
}
function fill(o, r, ex) { o.push = !!r.push; o.acc = 0; o.nh = r.hd; o.x = r.px; o.z = r.pz; o.y = r.y; o.vx = r.vx; o.vz = r.vz; o.vy = r.ground ? 0 : (r.vs || 0); o.gs = Math.hypot(r.vx, r.vz); o.ground = r.ground; o.ex = ex; return o; }

// ---------------------------------------------------------------- traffic
export class Traffic {
  constructor({ gates = [], airport = null, delay = DELAY_MS, onGateChange = null, persist = true, centerlines = null, taxigraph = null, stands = null } = {}) {
    this.centerlines = centerlines; this.tracks = new Map(); this.gates = prepGates(gates, stands); this.gateBy = new Map(this.gates.map(g => [g.name, g])); this.taxiways = prepPolys(airport); this.delay = delay; this.delayTarget = delay; this.offset = null;
    this.adaptDelay = true; this.net = new TaxiNet(taxigraph); this.audioDelay = 0; this.audioDelayTarget = 0;
    this.qnh = 1013.25; this.qnhSrc = 'standard'; this.metarQnh = null; this.onGateChange = onGateChange; this.persist = persist;
    this.lastIngest = 0; this.version = 0; this._tmp = {}; this._tgt = {}; this._la = {};
    this.ages = [];              // [recvNow, age s] of the newest report before a new one arrived (delay adaptation)
    this.events = [];            // runway/stand events (data time) for the statistics panel and QA
    this.plan = null;            // SFO stand allocation (relay /api/gates), optional
    this.counters = { rejects: 0, reacquire: 0, vehicles: 0 };
    if (persist) this.loadParked();
  }
  // scene time: real time minus the interpolation delay and the optional ATC audio delay (atc.md s.4.1: LiveATC runs
  // "typically less than 20 seconds" behind, so the viewer can hold the scene back to line it up with the audio)
  displayTime(now = Date.now()) { return now - this.delay - (this.audioDelay || 0); }
  // change the audio delay. Scene time cannot run backwards physically: a change > 2 s re-places every body at its
  // target (an explicit user jump in time); a small change is ramped (<= 0.25 s per s, the scene runs 25 % slow/fast)
  setAudioDelay(ms) {
    ms = clamp(Math.round(ms), 0, 30000); const cur = this.audioDelay || 0; this.audioDelayTarget = ms;
    if (Math.abs(ms - cur) > 2000) { this.audioDelay = ms; for (const tr of this.tracks.values()) { tr.ctl = null; tr.reacquire = false; } this.counters.timeJumps = (this.counters.timeJumps || 0) + 1; }
  }
  // SFO's plan (relay /api/gates) for this aircraft's callsign: {cs, alias, arr, dep, flight (the one relevant now),
  // stand (window covering now or null), gate (passenger gate of that flight)} or null
  planFor(tr) {
    const P = this.plan; if (!P || !tr.cs || !tr.cs.callsign) return null;
    const norm = (c) => { const m = /^([A-Z]{3})0*(\d+[A-Z]?)$/.exec(c || ''); return m ? m[1] + m[2] : c; };
    const cs0 = norm(tr.cs.callsign); let cs = cs0, alias = null;
    if (P.aliases && P.aliases[cs]) { const a = P.aliases[cs]; const to = a && typeof a === 'object' ? a.to : a; if (to) { cs = to; alias = a; } }
    const e = P.byCallsign && P.byCallsign[cs]; if (!e) return null;
    const F = P.flights || {}; const arr = e.arr ? F[e.arr] || null : null, dep = e.dep ? F[e.dep] || null : null;
    const ground = tr.disp && tr.disp.ground;
    // the flight that matters now: arriving until in-block, then the linked departure
    // SFO links a turn's arrival and departure (a different flight number, e.g. arrival UA1095 -> departure UA336):
    // prefer the record that carries this callsign
    const own = (f) => !!f && norm(String(f.cs || '').toUpperCase()) === cs;
    const pick = (a, d) => tr.dirSFO === 'dep' ? (d || a) : tr.dirSFO === 'arr' ? (a || d) : (ground && tr.landedAt ? (a || d) : (d || a));
    const flight = own(arr) || own(dep) ? pick(own(arr) ? arr : null, own(dep) ? dep : null) : pick(arr, dep);
    // every stand / gate SFO lists for this callsign's arrival and departure (a turn can use two stands: tows), with
    // the stand windows that are near now (+-45 min) flagged; times in ms
    const ms = (v) => v == null ? null : v > 1e12 ? v : v * 1000; const now = this._lastRecv || Date.now(); const cands = [];
    for (const [kind, f] of [['arr', arr], ['dep', dep]]) {
      if (!f) continue; const st = (f.stands || []).filter(x => x && x[0]);
      const fn = f.fn || null, linked = !own(f);
      if (!st.length) { if (f.gate) cands.push({ kind, fn, linked, stand: null, gate: String(f.gate).toUpperCase(), from: null, to: null, now: false }); continue; }
      for (const [n, a, b] of st) { const A = ms(a), B = ms(b); cands.push({ kind, fn, linked, stand: String(n).toUpperCase(), gate: f.gate ? String(f.gate).toUpperCase() : null, from: A, to: B, now: A != null && B != null && now >= A - 2700e3 && now <= B + 2700e3 }); }
    }
    return { cs: cs0, mapped: cs, alias, arr, dep, flight, stand: e.stand || null, gate: flight ? flight.gate || null : null, term: flight ? flight.term || null : null, cands };
  }
  event(tr, t, kind, extra = {}) { const e = { t, kind, hex: tr.hex, flight: tr.info.flight || null, icao: tr.info.icao || null, reg: tr.info.reg || null, ...extra }; this.events.push(e); if (this.events.length > 5000) this.events.splice(0, 1000); this.onEvent && this.onEvent(e); return e; }

  // payload: { now (server ms), aircraft: [normalized records] }
  ingest(payload, recvNow = Date.now()) {
    const off = recvNow - payload.now;
    this.offset = this.offset == null ? off : Math.min(this.offset + (recvNow - (this._lastRecv || recvNow)) * 0.002, off);
    this._lastRecv = recvNow; this.lastIngest = recvNow;
    // local QNH from the altimeter settings of aircraft below 10,000 ft (fallback: METAR, then standard)
    const q = payload.aircraft.filter(a => a.navQnh && a.altBaro != null && a.altBaro < 10000 && a.navQnh > 960 && a.navQnh < 1050).map(a => a.navQnh).sort((a, b) => a - b);
    if (q.length >= 3) { this.qnh = q[q.length >> 1]; this.qnhSrc = 'aircraft'; } else if (this.metarQnh) { this.qnh = this.metarQnh; this.qnhSrc = 'METAR'; }
    const seen = new Set();
    for (let a of payload.aircraft) {
      if (!a.hex || seen.has(a.hex)) continue; seen.add(a.hex);
      const w = toWorld(a.lat, a.lon, 0); const x = w[0], z = w[2];
      if (Math.hypot(x, z) > 75000) continue;
      let tr = this.tracks.get(a.hex);
      // an "airborne" report at taxi speed on the airport, at field elevation, is a ground report. The flag toggles on
      // parked aircraft (AAL2856 A321 at B23, 24 Sep 08:13Z: alt_baro 75 ft, gs 0.7 kt, between ground reports) and E175s
      // switch it at ~50 kt (realtime_impl.md step 2). Rotorcraft keep the flag (they hover).
      // Elsewhere (Palo Alto, San Carlos, Hayward ...: GA parked 'airborne' at 0 kt, review round 1) below 25 kt.
      if (!a.ground && !(a.category === 'A7' || (tr && tr.type && tr.type.species === 'H'))) {
        const gs = a.gs ?? 0, low = a.altGeom != null ? a.altGeom < 150 : (a.altBaro == null || a.altBaro < 500); // SFO: 13 ft MSL = -93 ft HAE
        const sfo = inAirport(x, z);
        // (elsewhere <= 40 kt, or <= 60 kt right after a ground report: GA landing / take-off rolls at San Carlos and Palo
        // Alto reported 'airborne' at 18-26 kt between ground reports and flickered approach <-> ground -- review round 2)
        // (elsewhere < 50 kt: light aircraft touch down at ~45-55 kt and roll out 'airborne'-flagged; drawn as slow floats at
        // ground level, replay check 25 Sep: vert.float.other_airfield 17,028 frames at Palo Alto / San Carlos)
        const wasG = !!(tr && tr.last && tr.last.ground);
        if (low && (sfo ? (gs < 30 || (wasG && gs < 50)) : (gs < 50 || (wasG && gs < 60)))) a = { ...a, ground: true, altBaro: null, altGeom: null, flagFixed: true };
      }
      // (a position already older than the moving-on-the-ground limit is not worth starting a track for: it would be
      // dropped again at once)
      if (!tr && a.t != null && this.offset != null && recvNow - (a.t + this.offset) > (this.movingLostMs ?? MOVING_LOST_MS)) continue;
      if (!tr) { tr = new Track(a.hex); tr.firstSeen = recvNow; this.tracks.set(a.hex, tr); }
      else if (tr.stale) { // transmitting again (a remembered aircraft, or after a data gap)
        const gap = recvNow - tr.lastRecv; tr.stale = false;
        // a parked aircraft heard again where it was parked, not moving: the same parking (keeps its gate, pose and
        // docked bridge; review round 1: every silent minute at a gate had released the gate and re-placed the body)
        const P = tr.stillPos || tr.parkRep || (tr.lock ? [tr.lock.x, tr.lock.z] : null);
        const same = P && a.ground && (a.gs ?? 0) < 3 && tr.m.phase === 'still' && this.stillHere(tr, P, x, z, a);
        if (same) { tr.staleRecord = false; this.counters.reacqParked = (this.counters.reacqParked || 0) + 1; }
        else if (tr.staleRecord || gap > 60000) { tr.staleRecord = false; tr.reps = []; tr.reacquire = true; if (tr.gate) this.releaseGate(tr); tr.stillPos = null; tr.still = []; tr.dock = null; tr.lock = null; tr.pushOk = false; tr.leaving = false; }
      }
      this.setInfo(tr, a);
      if (!tr.vehicle && (a.veh || (a.category && /^C[1-7]$/.test(a.category)) || ['SERV', 'GRND', 'TWR'].includes(a.icao) || a.srcType === 'adsb_icao_nt')) { tr.vehicle = true; this.counters.vehicles++; }
      // non-ICAO address with no identity at all, on the ground ('~' ids, type adsb_other): shown as an unidentified
      // ground target with vehicle kinematics [inferred: 11 such targets moved at <= 18 kt around the SFO ramps on 24 Sep]
      if (!tr.vehicle && a.hex[0] === '~' && a.ground && !a.flight && !a.reg && !a.icao) { tr.vehicle = true; tr.anon = true; this.counters.vehicles++; }
      const tf = a.t + this.offset;
      const L = tr.last;
      if (L && tf <= L.t + 20) { if (Math.abs(tf - L.t) <= 20) { L.gs = a.gs != null ? a.gs * KT : L.gs; } tr.lastRecv = recvNow; continue; } // same report again / out of order
      if (L && !tr.stale) this.ages.push([recvNow, (recvNow - L.t) / 1000, !L.ground || (L.gs || 0) > 1]);
      if (L && tf - L.t > (L.ground ? 30000 : 15000)) {   // coverage gap: re-acquire (fade out / in), do not race
        const P = tr.stillPos || tr.parkRep || (tr.lock ? [tr.lock.x, tr.lock.z] : null);
        const parkedHere = P && a.ground && (a.gs ?? 0) < 3 && tr.m.phase === 'still' && this.stillHere(tr, P, x, z, a);
        if (!parkedHere) { tr.reacquire = true; }
      }
      const r = this.report(tr, a, x, z, tf);
      if (!r) { tr.lastRecv = recvNow; continue; }
      if (tr.fadeOut) { tr.fadeOut = false; tr.reacquire = true; }   // heard again while fading out: re-placed where it is
      tr.reps.push(r); while (tr.reps.length > 60 || (tr.reps.length > 4 && r.t - tr.reps[0].t > 120000)) tr.reps.shift();
      tr.lastFixT = tf; tr.lastRecv = recvNow;
      if (tr.vehicle) { tr.phase = 'vehicle'; tr.m.phase = 'vehicle'; continue; }
      this.classify(tr, r, recvNow);
    }
    if (this.adaptDelay) this.adapt(recvNow);
    this.version++;
  }
  // a parked aircraft heard again (after silence / a gap) is still at its parking: within REACQ_PARK_M of its parked
  // position, or -- at a stand -- still inside that stand's (1.3x) limits: the first fix after silence can lie 16 m off
  // (replay check 25 Sep: AAL166 A321 at B25 19:17:31Z was released and re-docked for a 16 m fix)
  stillHere(tr, P, x, z, a) {
    if (Math.hypot(x - P[0], z - P[1]) < REACQ_PARK_M) return true;
    return !!(tr.gate && Math.hypot(x - P[0], z - P[1]) < 40 && this.gateScore(tr.gate, { x, z, hd: a.trueHeading != null ? a.trueHeading * DEG : null, hdReal: a.trueHeading != null, icao: tr.info.icao }, typeOf(tr), 1.3) != null);
  }
  // delay target: cover the age the newest report reaches before the next one arrives (p90 over the last minute)
  adapt(now) {
    while (this.ages.length && now - this.ages[0][0] > 60000) this.ages.shift();
    const a = this.ages.filter(q => q[2]).map(q => q[1]).filter(v => v < 8).sort((p, q) => p - q);
    if (a.length < 20) return;
    // median age the newest report reaches before the next arrives, + 0.3 s: interpolation most of the time, <= ~1.5 s
    // of dead reckoning otherwise (the audit measured p99 < 10 m airborne at 1.5 s, s.6.7)
    const p50 = a[Math.floor(a.length * 0.5)];
    this.delayTarget = clamp((p50 + 0.3) * 1000, DELAY_MIN, DELAY_MAX);
  }

  // build one report (hygiene, heading, velocity, map matching); null = rejected
  report(tr, a, x, z, tf) {
    const L = tr.last, ground = !!a.ground;
    let gs = a.gs != null ? a.gs * KT : null;
    if (L) { // position jump test (MLAT/garbled positions; parked multipath): faster than physically possible
      const dt = Math.max(0.2, (tf - L.t) / 1000), d = Math.hypot(x - L.x, z - L.z);
      const vmax = Math.max(gs ?? 0, L.gs ?? 0, ground ? 4 : 60);
      if (d > 1.5 * vmax * dt + (ground ? 25 : 150) && dt < 30) {
        // three CONSISTENT "jumps" in a row (within 30 m of each other) = the aircraft really is there; multipath at a
        // gate flips back and forth (UAL2649 at D16, 24 Sep 17:44Z: 15-28 m scatter) and never qualifies
        const R0 = tr.rejPt; tr.rejects = R0 && Math.hypot(x - R0[0], z - R0[1]) < 30 ? tr.rejects + 1 : 1; tr.rejPt = [x, z]; this.counters.rejects++;
        if (tr.rejects < 3) return null;
        this.counters.reacquire++; tr.reacquire = true;
      }
    }
    tr.rejects = 0; tr.rejPt = null;
    let y = GROUND_Y;
    if (!ground) {
      const baro = a.altBaro != null ? (a.altBaro + (this.qnh - 1013.25) * 27.3) * FT : null;
      const geom = a.altGeom != null ? a.altGeom * FT + GEOID_M : null;
      if (baro != null && geom != null && a.altBaro < 20000) { const b = geom - baro; tr.altBias = tr.altBias == null ? b : tr.altBias + (b - tr.altBias) * 0.2; }
      const T = typeOf(tr); const ant = T ? (T.top ?? (T.Hc + T.R)) : 4;  // GNSS antenna ~ on the crown: wheels are lower
      y = (geom != null ? geom : baro != null ? baro + (tr.altBias != null ? clamp(tr.altBias, -150, 150) : 0) : (L ? L.y : 300)) - ant * 0.8;
      y = Math.max(y, GROUND_Y);
      // altitude plausibility: a step implying > 6,000 ft/min against the previous airborne report (unless its own
      // vertical rate says so) is garbled -- accepted only when 3 reports in a row agree (review round 1: '~' TIS-B
      // targets and a C152 at -11,800 / -25,900 ft/min below 150 m)
      if (L && !L.ground && tf > L.t) {
        const dt = (tf - L.t) / 1000, pred = L.y + (L.vs || 0) * Math.min(dt, 10), lim = 30.5 * dt + 25 + Math.abs(L.vs || 0) * 0.5 * dt;
        if (Math.abs(y - pred) > lim && dt < 20) {
          const q = tr.altRej; tr.altRej = q && Math.abs(q.y - y) < 60 ? { y, n: q.n + 1 } : { y, n: 1 };
          if (tr.altRej.n < 3) { y = Math.max(GROUND_Y, pred + clamp(y - pred, -lim, lim)); this.counters.altRejects = (this.counters.altRejects || 0) + 1; }
        } else tr.altRej = null;
      }
    }
    const th = a.trueHeading != null ? a.trueHeading * DEG : null;
    const trk = !ground && a.track != null ? a.track * DEG : null;   // surface `track` is not trustworthy (audit s.4.3)
    const r = { t: tf, x, z, px: x, pz: z, y, ground, gs, gsKt: a.gs ?? null, th, trk, vs: a.baroRate != null ? a.baroRate * FT / 60 : (a.geomRate != null ? a.geomRate * FT / 60 : null),
      alt: a.altBaro, geom: a.altGeom, vr: a.baroRate ?? a.geomRate ?? null, roll: a.roll != null ? a.roll * DEG : null, hdReal: th != null };
    let chord = null;
    if (L) { const dx = x - L.x, dz = z - L.z, d = Math.hypot(dx, dz), dt = (tf - L.t) / 1000; if (d > (ground ? 3 : 20)) chord = vecHdg(dx, dz); if (r.gs == null && dt > 0) r.gs = d / dt; }
    if (r.gs == null) r.gs = 0;
    r.chord = chord;
    // direction of motion and nose heading
    if (!ground) { r.dir = trk ?? chord ?? (L ? L.dir : th ?? 0); r.hd = th ?? r.dir; }
    else {
      const moving = r.gs > 0.5;
      // leaving a parked position slowly: at 0.5 Hz a 1-1.5 m/s push-back moves 2-3 m between reports, under the 3 m chord
      // threshold, and was taken for forward taxi. The displacement from the parked position (median of its reports)
      // gives the direction instead once it exceeds 2.5 m (review round 2: SKW5456 at F9 15:58Z, ASA811 at B11S)
      if (chord == null && tr.m.phase === 'still') { const P = tr.stillPos || tr.parkRep; if (P) { const dd = Math.hypot(x - P[0], z - P[1]); if (dd > 2.5 && dd < 60) chord = vecHdg(x - P[0], z - P[1]); } }
      let nose = th ?? (L ? L.hd : null);
      if (moving) {
        const wasPush = tr.pushback;
        if (th != null) {
          // push-back: motion against the reported nose (audit s.6.9) -- reliable anywhere
          if (chord != null && Math.abs(wrapPi(chord - th)) > 120 * DEG && r.gs < 8 * KT && r.gs > 0.5) tr.pushback = true;
          else if (tr.pushback && ((chord != null && Math.abs(wrapPi(chord - th)) < 60 * DEG) || r.gs > 10 * KT)) tr.pushback = false;
        } else if (!tr.pushback) {
          // no heading reported: a push-back is inferred only for the FIRST movement out of a stand / parking position
          // (tr.pushOk, set while parked there), never on a taxiway or runway or once taxiing has begun (review round 1:
          // UAL888 B772 without true_heading was labelled 'Pushback from G5' at the 28L threshold, 11 off-blocks). At a
          // nose-in contact stand the first motion is a push-back unless it is clearly along the nose (review round 1:
          // UAL888 at G5 was driven forward into the terminal on a first report without a chord).
          if (tr.pushOk && r.gs < 8 * KT) {
            const ref = tr.lock ? tr.lock.hdg : (tr.parkHdg ?? tr.stillHdg ?? (tr.gate ? tr.gate.w.hdg : null));
            if (ref != null) {
              const noseIn = !!(tr.gate && tr.gate.bridge); const dd = chord != null ? Math.abs(wrapPi(chord - ref)) : null;
              if (dd == null ? noseIn : dd > (noseIn ? 100 : 120) * DEG) { tr.pushback = true; tr.pushNose = ref; }
              else if (dd != null && dd < 60 * DEG) tr.pushOk = false;   // taxiing forward out of the parking position
            }
          }
        } else if (r.gs > 10 * KT || (chord != null && tr.pushNose != null && Math.abs(wrapPi(chord - tr.pushNose)) < 60 * DEG)) {
          // pushed without a heading: moving along the nose again (the push motion reversed) = taxiing forward
          // (review round 1: a6bbef A21N stayed 'push' at 8-9 kt forward and was clamped to 1 m/s)
          tr.pushback = false; tr.pushOk = false;
        }
        if (tr.pushback && !wasPush) tr._pushSetAt = tf;   // reverted if this motion turns out to be position noise
        if (tr.pushback && th == null && chord != null) tr.pushNose = wrapPi(chord + Math.PI);   // the tail leads: nose = motion reversed
        let motion = chord;
        if (motion == null) motion = th != null ? (tr.pushback ? th + Math.PI : th) : tr.pushback && tr.pushNose != null ? tr.pushNose + Math.PI : (L ? L.dir : null);
        if (th == null) nose = tr.pushback ? (tr.pushNose ?? (motion != null ? motion + Math.PI : nose)) : (motion ?? nose);
        r.dir = tr.pushback ? wrapPi((th ?? nose) + Math.PI) : (th ?? motion ?? nose ?? 0);
      } else {
        if (nose == null) { nose = this.guessGroundHeading(tr, x, z); if (nose != null) tr.headingGuessed = true; }
        r.dir = L ? L.dir : (nose ?? 0);
      }
      r.hd = wrapPi(nose ?? r.dir);
      if (tr.pushback) { r.push = true; if (!tr.pushbackFrom && tr.gate) tr.pushbackFrom = tr.gate.name; }
      // map matching (OSM taxiway/taxilane centrelines): snap taxiing reports laterally when close and aligned
      if (moving && !tr.pushback && r.gs > 2 && this.net.ok && !tr.dock && !tr.vehicle) {
        // (with a reported heading the edge must agree within 20 deg: at junctions a 30-deg-off crossing edge pulled a
        // stopping B39M 28 deg off its heading, UAL583 24 Sep 16:40:56Z)
        const mm = this.net.match(x, z, r.dir, tr.matchWay, 10, (th != null ? 20 : 35) * DEG);
        // weight: close to the centreline, at taxi speed and on straight segments -- faded out continuously in turns and
        // when slowing to a stop (aircraft do not follow the centreline through a turn; switching the snap off at a stop made
        // the target jump 3.9 m sideways, UAL583 16:40:54Z)
        const tRate = th != null && L && L.th != null && tf > L.t ? Math.abs(wrapPi(th - L.th)) / ((tf - L.t) / 1000) : chord != null && L && L.chord != null && tf > L.t ? Math.abs(wrapPi(chord - L.chord)) / ((tf - L.t) / 1000) : 0;
        if (mm) { const wgt = (1 - sstep(5, 10, mm.d)) * sstep(2, 4, r.gs) * (1 - sstep(1 * DEG, 3 * DEG, tRate)); r.px = x + (mm.px - x) * wgt; r.pz = z + (mm.pz - z) * wgt; tr.matchWay = mm.way; r.way = mm.way; r.snap = mm.d * wgt;
          // velocity along the edge when snapped
          const eh = vecHdg(mm.ux, mm.uz); const al = Math.abs(wrapPi(r.dir - eh)) < Math.PI / 2 ? eh : eh + Math.PI; r.dir = lerpAng(r.dir, al, wgt * 0.7); if (th == null) r.hd = r.dir; }
        else tr.matchWay = null;
      }
    }
    const v = hdgVec(r.dir); r.vx = v[0] * r.gs; r.vz = v[1] * r.gs;
    r.turn = 0;
    if (L && L.dir != null && r.dir != null) { const dt = (tf - L.t) / 1000; if (dt > 0.3 && dt < 6) { const w = wrapPi(r.dir - L.dir) / dt; r.turn = Math.abs(w) < (ground ? 12 : 4) * DEG ? w : 0; } }
    return r;
  }

  setInfo(tr, a) {
    const I = tr.info;
    // the two providers' aircraft databases can disagree (ACA738 C-FDUW: BCS3 at adsb.fi, BCS1 at adsb.lol, 24 Sep): a
    // DATABASE type change is accepted only after 5 consecutive reports agree, so the model never flickers
    let dbIcao = a.icao, dbDesc = a.desc;
    if (a.icao && I.dbIcao && a.icao !== I.dbIcao) { tr._typeCand = tr._typeCand === a.icao ? tr._typeCand : a.icao; tr._typeN = tr._typeCand === a.icao ? (tr._typeN || 0) + 1 : 1; if (tr._typeN < 5) { dbIcao = I.dbIcao; dbDesc = I.dbDesc; } }
    else tr._typeN = 0;
    Object.assign(I, { flight: a.flight || I.flight || null, reg: a.reg || I.reg || null, dbIcao: dbIcao || I.dbIcao || null, dbDesc: dbDesc || I.dbDesc || null, ownOp: a.ownOp || I.ownOp || null,
      squawk: a.squawk ?? I.squawk, emergency: a.emergency, category: a.category || I.category, altBaro: a.altBaro, gsKt: a.gs, vsFpm: a.baroRate ?? a.geomRate, trackDeg: a.track, navAlt: a.navAlt,
      src: a.srcType || I.src, seen: a.seen, year: a.year || I.year, prov: a.prov || I.prov || null, posSrc: a.src || null, dbAlt: a.dbAlt || I.dbAlt || null });
    const cs = I.flight || null;
    if (!tr.cs || tr.cs.callsign !== cs) {
      const old = tr.cs && tr.cs.callsign; tr.cs = parseCallsign(I.flight);
      // a turn at the gate: the arrival's flight number becomes the departure's (AAL76 -> AAL16 24 Sep 17:46Z, ACA739 ->
      // ACA540 -> ACA740, FFT1229 -> FFT1094). The old flight's route, direction and SFO record no longer apply (review
      // round 1: the card said 'from JFK' while AAL16 departed to JFK)
      if (old && cs && old !== cs) {
        tr.route = undefined; tr.dirFromRoute = false; tr.csChangedAt = tr.lastFixT || 0; this.counters.callsignChanges = (this.counters.callsignChanges || 0) + 1;
        if (tr.groundSFO && tr.m.phase === 'still') tr.dirSFO = 'dep';
      }
    }
    const key = [I.dbIcao, I.dbDesc, I.category, I.dbAlt && I.dbAlt.t, this.planType(tr)].join('|');
    if (key !== tr._typeKey || !tr.type) { tr._typeKey = key; this.resolveType(tr); }
    const al = tr.cs && tr.cs.airline ? tr.cs.airline.icao : null;
    tr.livery = liveryForAirline(al);
  }
  // The type drawn: the aircraft database's, unless it contradicts the transponder's own emitter category (DO-260B:
  // A1 < 15,500 lb, A2 < 75,000 lb, A3 < 300,000 lb, A4 B757, A5 heavy) by wake class (ICAO Doc 8643: L < 7 t, M, H >=
  // 136 t, J). Then the other provider's database entry (relay _dbalt) or SFO's own flight record (flysfo aircraft type)
  // that agrees with the category is used. Review round 1: DAL1053 N342DU is A333 in both databases but transmits A3 and
  // SFO lists BCS3 at C11 (class C, largest type BCS3) -- drawn as an A330 it fitted no stand and stood in the terminal;
  // AAL1023 N959XV: adsb.fi 'PA27 Piper Aztec', adsb.lol A21N, category A3 -- no bridge may dock to a light-aircraft marker.
  resolveType(tr) {
    const I = tr.info, cat = I.category; let icao = I.dbIcao, desc = I.dbDesc, src = 'db';
    const bad = (t) => { if (!t || !t.wake || !/^A[1-5]$/.test(cat || '')) return false; const w = t.wake;
      return ((w === 'H' || w === 'J') && /^A[1-3]$/.test(cat)) || (w === 'L' && /^A[3-5]$/.test(cat)) || (w === 'M' && cat === 'A5'); };
    const plan = this.planType(tr);
    if (!icao && plan) { icao = plan; desc = null; src = 'sfo'; }
    else if (icao && bad(typeInfo(icao, desc))) {
      src = 'conflict';
      for (const [t2, s2] of [[I.dbAlt && I.dbAlt.t, 'db2'], [plan, 'sfo']]) { if (!t2 || t2 === icao) continue; const ti = typeInfo(t2, null); if (ti.wake && !bad(ti)) { icao = t2; desc = null; src = s2; break; } }
    }
    if (src !== 'db' && icao !== I.icao) this.counters.typeFixed = (this.counters.typeFixed || 0) + 1;
    I.icao = icao || null; I.desc = src === 'db' || src === 'conflict' ? desc : null; tr.typeSrc = src;
    tr.type = typeInfo(I.icao, I.desc); tr.model = typeForIcao(I.icao);
  }
  // SFO's aircraft type for this callsign's flight (relay /api/gates: flysfo aircraft_transport_type, ICAO designator;
  // flysfo 'E175' = ICAO E75L/E75S, realtime_impl.md s.4)
  planType(tr) {
    const P = this.plan; if (!P || !tr.cs || !tr.cs.callsign) return null;
    const m = /^([A-Z]{3})0*(\d+[A-Z]?)$/.exec(tr.cs.callsign); let cs = m ? m[1] + m[2] : tr.cs.callsign;
    if (P.aliases && P.aliases[cs]) { const q = P.aliases[cs]; cs = (q && typeof q === 'object' ? q.to : q) || cs; }
    const e = P.byCallsign && P.byCallsign[cs]; if (!e) return null;
    let t = e.type || null;
    if (!t) { const F = P.flights || {}; for (const k of ['dep', 'arr']) { const f = e[k] && F[e[k]]; if (f && f.type) { t = f.type; break; } } }
    return t === 'E175' ? 'E75L' : t;
  }

  // ---------------------------------------------------------- flight phase state machine (data time)
  setPhase(tr, p, t, rwy = tr.m.rwy, tStart = null) {
    const M = tr.m; if (M.phase === p && tr.hist.length && tr.hist[tr.hist.length - 1][2] === rwy) return;
    tr.fromStill = M.phase === 'still';
    M.phase = p; M.since = t; M.rwy = rwy;
    // a phase recognised a few seconds after it began (take-off roll, push-back) is back-dated in the display history
    // to where it began, so the display (1-3 s behind) shows it from the right moment
    let ts = t; if (tStart != null && tr.hist.length) ts = Math.max(tStart, tr.hist[tr.hist.length - 1][0] + 1);
    tr.hist.push([ts, p, rwy]); if (tr.hist.length > 40) tr.hist.shift();
  }
  setGround(tr, t, g) { const A = tr.air; if (A.length && A[A.length - 1][1] === g) return; A.push([t, g]); if (A.length > 20) A.shift(); }
  classify(tr, r, now) {
    const M = tr.m, t = r.t, kt = r.gs / KT, atSFO = inAirport(r.x, r.z);
    if (r.ground && atSFO) tr.groundSFO = true;
    if (!r.ground) tr.lastAirT = t;
    if (!tr.air.length) this.setGround(tr, t, r.ground);
    // ---- rollout: wheels on the runway from touchdown until the exit, whatever the transponder flag says
    if (M.phase === 'rollout') {
      const R = RWYN[M.rwy]; if (R) { const [aa, c] = rwyCoords(R, r.x, r.z); if (Math.abs(c) > 45) { this.setPhase(tr, 'taxi', t); M.exitT = t; this.event(tr, t, 'exit', { rwy: M.rwy, a: Math.round(aa), rot: M.td && M.td.how !== 'late' ? Math.round((t - M.td.t) / 1000) : null }); } }
      if (kt < 1 && M.phase === 'rollout' && t - M.since > 120000) this.setPhase(tr, 'still', t);
      return;
    }
    if (!r.ground || ['takeoff', 'final', 'flare', 'goaround'].includes(M.phase)) this.airLogic(tr, r, t);
    else this.groundLogic(tr, r, t, kt, atSFO);
    // direction (arrival / departure) for labels and aircraft configuration
    const p = M.phase;
    const turned = tr.inBlockAt != null && (!tr.landedAt || tr.inBlockAt > tr.landedAt);   // parked since its landing (or seen parked first)
    if (['final', 'flare', 'rollout'].includes(p) || (p === 'taxi' && tr.landedAt && t - tr.landedAt < 3600e3 && !tr.pushed && !turned)) tr.dirSFO = 'arr';
    else if (['pushback', 'lineup', 'takeoff', 'climb'].includes(p) || (p === 'taxi' && (tr.pushed || turned))) tr.dirSFO = 'dep';
    else if (p === 'approach') tr.dirSFO = 'arr';
    else if (p === 'departure') tr.dirSFO = 'dep';
  }
  airLogic(tr, r, t) {
    const M = tr.m, gnd = r.ground, gs = r.gs / KT, alt = r.alt, geom = r.geom, vr = r.vr, x = r.x, z = r.z;
    const hdg = r.trk ?? r.chord ?? r.th;
    // ---- take-off roll continues through the (~100 kt, E175: ~50 kt) flag until real climb evidence
    if (M.phase === 'takeoff') {
      if (!gnd && M.flagAir == null) M.flagAir = t;
      if (geom != null && M.flagAir != null && M.climbN === 0 && (vr == null || vr < VR_CLIMB)) { M.geomRef.push(geom); if (M.geomRef.length > 20) M.geomRef.shift(); }
      const climb = vr != null && vr >= VR_CLIMB; M.climbN = climb ? M.climbN + 1 : 0;
      const ref = median(M.geomRef);
      if (!gnd && (M.climbN >= 2 || (vr != null && vr >= 500) || (ref != null && geom != null && geom >= ref + 50))) {
        // liftoff: first report of the climbing sequence (the event is between it and the previous report)
        const F = tr.reps; const tl = M.climbN >= 2 && F.length >= 2 ? F[F.length - 2].t : t;
        M.lo = { t: tl }; tr.liftoffAt = tl; this.setGround(tr, tl, false); this.setPhase(tr, 'climb', tl);
        this.event(tr, tl, 'liftoff', { rwy: M.rwy, gs: Math.round(gs) }); tr.depRunway = M.rwy; return;
      }
      const F = tr.reps; const since = t - (M.rollT ?? M.since);
      const dec = F.length >= 3 && F[F.length - 3].gs != null && gs < F[F.length - 3].gs / KT - 6;
      // first seen already rolling (cold start) and now slowing or slow: it was landing. Whatever the flag says: E175s
      // report 'airborne' down to ~50 kt on the rollout (review round 1: SKW3007 E75L, first seen at 45 kt on the 28L
      // rollout, stayed 'Takeoff roll 28L' at its gate for 40 min)
      if (M.coldT != null && t - M.coldT < 90000 && (dec || gs < 40)) { M.coldT = null; this.touchdown(tr, r, t, 'late'); return; }
      if (dec && gs > 40 && gs < 120 && (gnd || gs < 60)) {
        this.setPhase(tr, 'rollout', t); M.td = { t, a: 0 }; this.event(tr, t, 'rejected-takeoff', { rwy: M.rwy }); return;
      }
      // no liftoff: a "take-off roll" that is slow for 20 s or lasts 90 s was not one (airborne and fast: it left unseen)
      if ((gs < 30 && since > 20000) || since > 90000) {
        if (!gnd && gs > 100) { this.setGround(tr, t, false); this.setPhase(tr, 'climb', t); M.lo = { t }; tr.liftoffAt = t; this.event(tr, t, 'liftoff', { rwy: M.rwy, gs: Math.round(gs), late: true }); tr.depRunway = M.rwy; return; }
        M.coldT = null; this.setGround(tr, t, true); this.setPhase(tr, gs < 1.5 ? 'still' : 'taxi', t, null); return;
      }
      return;
    }
    // touchdown by the ground flag only at landing speeds: below 40 kt the aircraft is taxiing and the "final" came from
    // airborne-flagged surface reports (observed: UAL1469 B753 taxiing at 16 kt east of 28L, 24 Sep 16:05Z replay)
    if (gnd && (M.phase === 'final' || M.phase === 'flare')) { if (gs >= 40) this.touchdown(tr, r, t, 'flag'); else { this.setPhase(tr, 'taxi', t, null); tr.finalInfo = null; } return; }
    // ---- cold start: first seen with the "airborne" flag while still on the runway (mid take-off roll)
    if (M.phase === 'new' && !gnd && runwayAt(x, z) && hdg != null) {
      const R = alignedRunway(runwayAt(x, z), hdg);
      if (R && (vr == null || vr > -300) && (alt == null || alt < 300)) { this.setPhase(tr, 'takeoff', t, R.name); this.setGround(tr, t, true); M.flagAir = t; M.climbN = 0; M.geomRef = []; M.coldT = t; M.rollT = t; return; }
    }
    // ---- airborne again after a data gap while we had it on the ground at SFO: it departed unseen
    if (!gnd && ['taxi', 'lineup', 'still', 'pushback', 'takeoff'].includes(M.phase) && (alt ?? 0) > 400 && tr.groundSFO) {
      this.setGround(tr, t, false); this.setPhase(tr, 'climb', t); M.lo = { t }; tr.liftoffAt = t; tr.dirSFO = 'dep';
      this.event(tr, t, 'liftoff', { rwy: M.phase === 'takeoff' ? M.rwy : null, unseen: true }); return;
    }
    // ---- climb / departure
    if (M.phase === 'climb' || M.phase === 'departure') {
      if (M.phase === 'climb' && (t - (M.lo ? M.lo.t : t) > 120000 || (alt != null && alt > 3000))) this.setPhase(tr, 'departure', t);
      if (M.phase === 'departure' && t - M.since > 900000) this.setPhase(tr, 'enroute', t);
      return;
    }
    // ---- landing with no final seen (track acquired late): runway, aligned, ground flag, decelerating
    // ---- runway posterior (arrivals): Bayesian accumulation of cross-track likelihoods, sigma widening with distance
    let best = null; const climbing = vr != null && vr > 300;
    const onFinal = M.phase === 'final' || M.phase === 'flare';
    // who can be "on final": a jet or turboprop (type engine class, else emitter category A2-A5), identified (not a '~'
    // TIS-B target), not a rotorcraft, at approach speed and -- to enter final -- descending >= 300 ft/min. Review round
    // 1: VFR pistons, a Bell 206 and anonymous targets crossing the extended centrelines at 900-3,500 ft were assigned
    // 'final' and then logged as go-arounds (N16894, N642ND C172; N42SL B06; ~2b0c43; BYF19 C172).
    const ty = tr.type || {}; const cat = tr.info.category;
    const fixedWing = !(cat === 'A7' || ty.species === 'H');
    const powered = ty.engType ? (ty.engType === 'J' || ty.engType === 'T') : /^A[2-5]$/.test(cat || '');
    const eligible = fixedWing && powered && tr.hex[0] !== '~' && gs >= (cat === 'A1' ? 90 : 80);
    const descending = vr != null && (vr <= -300 || (alt != null && alt < 1000 && vr < -100));
    if (!climbing && hdg != null && M.phase !== 'goaround' && eligible && (onFinal || descending)) {
      // log-likelihoods with forgetting (a ~7-report memory): a parallel offset track far out (vectors, the 28R LDA
      // offset) must not outweigh the alignment near the runway (review round 1: 14 runway flips on final, 6-23 km out)
      for (const n in M.logp) M.logp[n] *= 0.85;
      for (const R of RWY) {
        if (Math.abs(wrapPi(hdg - R.hdg)) > 25 * DEG) continue;
        const [aa, c] = rwyCoords(R, x, z);
        if (!(aa > -25000 && aa < 1500)) continue;
        const h = (alt ?? 0) - 13; if (h > 3000 + Math.max(0, -aa) * 0.09) continue;
        const sig = 25 + 0.012 * Math.abs(Math.min(aa, 0));
        M.logp[R.name] = (M.logp[R.name] || 0) - 0.5 * (c / sig) ** 2 - Math.log(sig);
        if (!best || Math.abs(c) < Math.abs(best.c)) best = { R, a: aa, c };
      }
      const names = Object.keys(M.logp);
      if (best && names.length) {
        const pr = this.runwayPrior();
        const cand = names.map(n => [n, M.logp[n] + Math.log(pr[n] || 0.02)]); const m = Math.max(...cand.map(q => q[1]));
        const Z = cand.reduce((s, q) => s + Math.exp(q[1] - m), 0); let top = null, tp = 0;
        for (const [n, v] of cand) { const p = Math.exp(v - m) / Z; if (p > tp) { tp = p; top = n; } }
        const R = RWYN[top]; const [aa, c] = rwyCoords(R, x, z);
        if (tp >= 0.9 && Math.abs(c) < 150 + 0.1 * Math.abs(aa)) {
          if (!onFinal) { M.decidedAt = { t, a: Math.round(aa), rwy: top, p: +tp.toFixed(3) }; this.setPhase(tr, 'final', t, top); M.altRwy = null; tr.finalInfo = { R, a: aa, c }; tr.runway = top; M.rwyFirm = false; M.firmT = null; }
          else if (M.rwy !== top && !M.rwyFirm) {
            // not yet firm (shown as the parallel pair): follow the posterior without a runway-change event (review round 1:
            // 14 flips 6-23 km out -- all ended on the runway actually used, so they were corrections of an early call)
            M.rwy = top; tr.runway = top; tr.finalInfo = { R, a: aa, c }; M.firmT = null; M.altRwy = null; tr.hist.push([t, 'final', top]); if (tr.hist.length > 40) tr.hist.shift();
            this.counters.finalRwyEarlySwitch = (this.counters.finalRwyEarlySwitch || 0) + 1;
          }
          else if (M.rwy !== top) {
            // established on final: a change needs the other runway at >= 0.99 for 20 s (a sidestep, or a wrong early call)
            if (tp >= 0.99) { if (!M.altRwy || M.altRwy.rwy !== top) M.altRwy = { rwy: top, t }; }
            else M.altRwy = null;
            if (M.altRwy && t - M.altRwy.t >= 20000) { this.event(tr, t, 'runway-change', { from: M.rwy, rwy: top, a: Math.round(aa) }); M.rwy = top; M.altRwy = null; tr.runway = top; tr.finalInfo = { R, a: aa, c }; }
          } else M.altRwy = null;
        } else M.altRwy = null;
        // firm: no parallel runway, or the posterior for the assigned runway >= 0.99 for 10 s, or >= 0.9 inside 3 nm of
        // the threshold (where the 230 m between the SFO parallels is ~ 4 sigma of the cross-track model)
        if (onFinal && M.rwyFirm === false) {
          const [aF] = rwyCoords(RWYN[M.rwy], x, z);
          // (not earlier: the 28R arrivals fly the SOIA LDA course, offset from the 28R centreline until ~3.4 nm (FAA IAP
          // LDA PRM RWY 28R), so a far-out posterior is over-confident -- review round 2: 4 of the calls that had been
          // >= 0.99 for 10 s at 4-6 nm were later corrected to the other runway)
          if (!PARALLEL[M.rwy] || (top === M.rwy && tp >= 0.9 && aF > -3 * NM)) M.rwyFirm = true;
        }
      }
    }
    // ---- final -> flare -> touchdown / go-around
    if ((M.phase === 'final' || M.phase === 'flare') && M.rwy) {
      const R = RWYN[M.rwy]; const [aa, c] = rwyCoords(R, x, z); tr.finalInfo = { R, a: aa, c };
      if (alt != null) M.minAlt = M.minAlt == null ? alt : Math.min(M.minAlt, alt);
      // a go-around: climbing >= 150 ft above the lowest point at >= 500 ft/min, from below 1,500 ft (the lowest true
      // go-around of 24 Sep, UAL1506 A21N 28R, levelled at 1,075 ft; the false ones were VFR traffic at 975-3,300 ft)
      if (M.minAlt != null && M.minAlt < 1500 && alt != null && alt >= M.minAlt + GA_CLIMB_FT && vr != null && vr >= GA_VR && !M.td) {
        this.setPhase(tr, 'goaround', t); M.gaT = t; this.event(tr, t, 'go-around', { rwy: M.rwy, alt, minAlt: M.minAlt }); M.logp = {}; M.minAlt = null; tr.finalInfo = null; return;
      }
      if (Math.abs(c) > 400 + 0.15 * Math.abs(aa) || aa < -30000) { this.setPhase(tr, 'approach', t, null); M.logp = {}; tr.finalInfo = null; return; } // turned away (vectors, circling)
      if (M.phase === 'final' && aa > -150) this.setPhase(tr, 'flare', t);
      const F = tr.reps;
      if (M.phase === 'flare' && aa > 100 && F.length >= 3) {
        const q = F.slice(-3); const g = q.map(p => p.gs / KT), ts = q.map(p => p.t / 1000);
        if (ts[2] > ts[1] && ts[1] > ts[0]) { const d1 = (g[1] - g[0]) / (ts[1] - ts[0]), d2 = (g[2] - g[1]) / (ts[2] - ts[1]);
          if (d1 <= -DECEL_TD && d2 <= -DECEL_TD) { this.touchdown(tr, q[0], q[0].t, 'decel'); return; } }
      }
      if (aa > 2500 && M.phase === 'flare' && alt != null && alt < 150) this.touchdown(tr, r, t, 'position');
      return;
    }
    if (M.phase === 'goaround') {
      if ((alt != null && alt > 2500) || t - M.gaT > 180000) { this.setPhase(tr, 'approach', t, null); M.minAlt = null; }
      return;
    }
    if (!gnd) {
      this.setGround(tr, t, false);   // elsewhere (other airports, overflights) the flag decides air/ground
      const d = Math.hypot(x, z); const inbound = (vr != null && vr < -300 && d < 40000 && (alt ?? 1e9) < 12000) || tr.dirSFO === 'arr';
      const p = inbound ? 'approach' : 'enroute';
      if (M.phase !== p) this.setPhase(tr, p, t, null);
      this.routeDirection(tr);
    }
  }
  runwayPrior() { // arrivals' runways of the last 30 min make the current configuration likelier (self-learned, no ATIS)
    const t = this._lastRecv || 0; const pr = {}; let n = 0;
    for (let i = this.events.length - 1; i >= 0; i--) { const e = this.events[i]; if (t - e.t > 1800e3) break; if (e.kind === 'touchdown' && e.rwy) { pr[e.rwy] = (pr[e.rwy] || 0) + 1; n++; } }
    const out = {}; for (const R of RWY) out[R.name] = n ? 0.1 + 0.35 * (pr[R.name] || 0) / n : 0.25; return out;
  }
  touchdown(tr, r, t, how) {
    const M = tr.m; const R = RWYN[M.rwy]; const a = R ? rwyCoords(R, r.x, r.z)[0] : null;
    M.td = { t, a, how }; tr.landedAt = t; this.setGround(tr, t, true); this.setPhase(tr, 'rollout', t);
    this.event(tr, t, 'touchdown', { rwy: M.rwy, how, a: a != null ? Math.round(a) : null, gs: Math.round(r.gs / KT) });
    tr.arrRunway = M.rwy; tr.runway = M.rwy;
  }
  groundLogic(tr, r, t, kt, atSFO) {
    const M = tr.m;
    if (!atSFO) { this.setPhase(tr, 'ground-other', t, null); this.setGround(tr, t, true); return; }
    this.setGround(tr, t, true);
    const rp = runwayAt(r.x, r.z); const hdg = r.dir;
    // landed with no final seen (acquired late): on a runway at speed with the ground flag -> rollout, back-dated
    if (rp && kt > 40 && ['new', 'approach', 'enroute'].includes(M.phase) && (tr.lastAirT == null || t - tr.lastAirT < 30000)) {
      const R = alignedRunway(rp, hdg); if (R && tr.reps.length >= 2 && tr.reps[tr.reps.length - 2].gs >= r.gs) { M.rwy = R.name; this.touchdown(tr, r, t - clamp((130 - kt) / 3.2, 0, 25) * 1000, 'late'); return; }
    }
    // first report of a new track on a runway at speed: one report cannot tell a landing roll-out from a take-off roll
    if (rp && kt > 40 && M.phase === 'new' && tr.reps.length < 2) return;
    // take-off roll: on a runway, aligned, and >= 50 kt or accelerating >= 1.2 kt/s over ~3 s from >= 12 kt (take-off
    // acceleration 3-5.8 kt/s; a runway back-taxi at 30-36 kt was 0.03-0.1 kt/s: audit s.3.5, s.6.5)
    let acc = null; const F = tr.reps;
    if (F.length >= 4) { const q = F[F.length - 4]; if (r.t - q.t > 1500) acc = (r.gs - q.gs) / KT / ((r.t - q.t) / 1000); }
    if (rp && (kt >= 50 || (kt >= 12 && acc != null && acc >= 1.2))) {
      const R = alignedRunway(rp, hdg);
      if (R) { if (M.phase !== 'takeoff') {
          // roll start: the last report below 5 kt (standing start) or on entering the runway (rolling start), <= 60 s back
          let t0 = t; for (let i = F.length - 2; i >= 0 && t - F[i].t < 60000; i--) { t0 = F[i].t; if (F[i].gs < 5 * KT || !runwayAt(F[i].x, F[i].z)) break; }
          if (M.phase === 'new') M.coldT = t; else M.coldT = null;
          this.setPhase(tr, 'takeoff', t, R.name, t0); M.flagAir = null; M.climbN = 0; M.geomRef = []; M.rollT = t; this.event(tr, t, 'takeoff-roll', { rwy: R.name }); } return; }
    }
    let moving = kt >= 1.5 || (r.push && kt >= 0.6);   // push-backs run at 1-6 kt (audit s.3.6)
    // a stopped aircraft starts moving only when two consecutive reports agree (displacement growing, consistent with the
    // reported speed and direction): parked multipath makes spurious 3-9 kt reports that jump 15-28 m back and forth
    // (review round 1: UAL2649 A319 at D16, 24 Sep 17:44Z -- the body swung 133 -> 277 -> 97 deg and left the stand)
    if (M.phase === 'still') {
      // (in the reports' own frame: the median of the stationary reports, not the drawn / stand pose, which can lie a few
      // metres from where the transponder puts itself)
      const ref = tr.stillPos || tr.parkRep || (tr.lock ? [tr.lock.x, tr.lock.z] : null);
      // (a displacement while the transponder itself reports ~0 kt is GNSS wander, not motion: AAL2885 at B19 crept 25 m in
      // 2 min at a reported 0.0 kt, 24 Sep 16:39-16:47Z)
      // (...unless it follows a moving candidate: a sparse track that moved and has already stopped at its new place)
      const cand = moving || (ref && Math.hypot(r.x - ref[0], r.z - ref[1]) > 6 && (!(r.gsKt != null && r.gsKt < 0.5) || !!(tr.mvCand && tr.mvCand.length)));
      if (!cand) tr.mvCand = null;
      else if (!this.motionConfirmed(tr, r, ref)) { moving = false; r.noise = true; if (tr._pushSetAt === r.t) { tr.pushback = false; r.push = false; } this.counters.motionHeld = (this.counters.motionHeld || 0) + 1; }
      else moving = true;
    }
    if (!moving) {
      // stationary: on a runway aligned = lined up; on a taxiway = holding; else parked (stand matched separately)
      let p = 'still';
      if (rp) { const R = alignedRunway(rp, r.hd ?? hdg, 20 * DEG); if (R && (tr.pushed || M.phase === 'taxi' || M.phase === 'lineup')) { p = 'lineup'; if (M.phase !== 'lineup') { this.setPhase(tr, 'lineup', t, R.name); this.event(tr, t, 'lineup', { rwy: R.name }); } return; } }
      if (M.phase !== p) this.setPhase(tr, p, t, null);
      this.stationary(tr, r, t);
      return;
    }
    r.mv = true;
    // an arrival closing up to its stop mark: forward along a contact stand's lead-in, slowly, not past the stop point.
    // Nose-in contact stands have no forward way out, so this is never an off-block (replay check 25 Sep: UAL2 B789 read as
    // stationary at 0.3-0.6 kt 7 m short of the G8 stop mark, 24 Sep 15:20:44Z; the 'forward off-block' that followed
    // kept its bridge from docking for the whole 81-min turn)
    // (and any slow motion in the first 10 min after in-block at a contact stand that is not a push-back: departures leave
    // nose-in contact stands by push-back only; replay check 25 Sep: UAL984 B77W at G8 20:22:34Z logged a 'forward
    // off-block' 26 s after in-block and its bridge never docked for 46 min)
    const creep = this.creepToStop(tr, r) || !!(tr.gate && tr.gate.bridge && !r.push && !tr.pushback && !tr.pushed && r.gs <= 3 * KT && tr.inBlockAt != null && t - tr.inBlockAt < 600000);
    // leaving a parked position: the jet bridge retracts first (the display holds the body until it is clear); a creep
    // to the stop mark retracts only a bridge that is already out, and it re-docks when the aircraft has stopped
    // (a body at rest at a taxiway hold or on a ramp has no bridge: nothing to retract)
    if (creep ? tr.bridgeOn : (tr.bridgeOn || (tr.lock && tr.gate))) tr.leaving = true;
    if (creep) this.counters.creeps = (this.counters.creeps || 0) + 1;
    const wasStill = M.phase === 'still';
    tr.still = []; tr.seenMoving = true; tr.stillPos = null; tr.stillHdg = null; tr.freePark = null; tr.dockComplete = false; tr.lock = null;
    if (tr.gate && this.distToPark(tr, r) > (creep ? 30 : 12)) this.releaseGate(tr, t);
    // the start of the motion (first report of the confirmed sequence), for back-dating the phase
    const F2 = tr.reps; let t0 = t; for (let i = F2.length - 2; i >= 0 && t - F2[i].t < 30000; i--) { if (!F2[i].mv && !(F2[i].gs >= 0.6 && !F2[i].noise)) break; t0 = F2[i].t; }
    // (one off-block per turn: a push-back that stops and continues is not a second one -- review round 2: 108 off-block
    // events for 49 take-off rolls in the 15:25-16:45Z replay)
    if (r.push) { if (M.phase !== 'pushback') { this.setPhase(tr, 'pushback', t, null, t0); if (!tr.pushed) { this.event(tr, t, 'off-block', { stand: tr.pushbackFrom || null }); tr.offBlock = { stand: tr.pushbackFrom || null, t }; } tr.pushed = true; } return; }
    // first forward motion out of a parking position (no push-back seen): that is the off-block (power-out / ramp)
    if (wasStill && tr.pushOk && !tr.pushed && !creep) { tr.pushed = true; this.event(tr, t, 'off-block', { stand: tr.gate ? tr.gate.name : null, forward: true }); }
    if (!creep) tr.pushOk = false;
    if (rp) { const R = alignedRunway(rp, hdg, 20 * DEG); if (R && M.phase === 'lineup') { this.setPhase(tr, 'lineup', t, R.name); return; } }
    if (M.phase !== 'taxi') this.setPhase(tr, 'taxi', t, null, wasStill ? t0 : null);
    this.docking(tr, r, t);
  }
  // consecutive moving candidates out of a stop: displacement from the stop growing, each step consistent with the
  // reported speed (<= 1.6 gs dt + 3 m) and with the direction away from the stop (<= 60 deg)
  motionConfirmed(tr, r, ref) {
    const C = tr.mvCand || (tr.mvCand = []);
    // (candidates up to 25 s apart: near the terminals reports can be 10-14 s apart, and a real 21 m move into B11 went
    // unconfirmed and was shown as fade-out/fade-in re-placements -- replay check 25 Sep, UAL718 A320 24 Sep 17:55:49-17:56:09Z)
    if (C.length && r.t - C[C.length - 1].t > 25000) C.length = 0;
    C.push(r); if (C.length > 4) C.shift();
    if (C.length < 2) return false;
    const a = C[C.length - 2];
    let ok = true;
    const dt = Math.max(0.3, (r.t - a.t) / 1000), step = Math.hypot(r.x - a.x, r.z - a.z);
    if (step > 1.6 * Math.max(a.gs, r.gs, 0.8) * dt + 3) ok = false;
    if (a.gsKt != null && r.gsKt != null && Math.max(a.gsKt, r.gsKt) < 0.5) ok = false;
    if (ref) {
      const da = Math.hypot(a.x - ref[0], a.z - ref[1]), db = Math.hypot(r.x - ref[0], r.z - ref[1]);
      if (!(db > da + 0.3 && db > 2)) ok = false;
      if (ok && da > 2 && step > 1 && Math.abs(wrapPi(vecHdg(a.x - ref[0], a.z - ref[1]) - vecHdg(r.x - a.x, r.z - a.z))) > 60 * DEG) ok = false;
    }
    if (!ok) return false;
    for (const q of C) q.mv = true; tr.mvCand = null; return true;
  }
  // moving forward along its contact stand's lead-in toward the stop point (< 3 kt, direction within 40 deg of the stand
  // heading, the reported position at most 4 m past where the stop point puts this type's antenna)
  creepToStop(tr, r) {
    const g = tr.gate; if (!g || !g.bridge || r.push || tr.pushback || tr.pushed || r.gs > 3 * KT) return false;
    const P = tr.stillPos || tr.parkRep; if (!P) return false;
    const dx = r.x - P[0], dz = r.z - P[1]; if (Math.hypot(dx, dz) < 1) return false;
    if (Math.abs(wrapPi(vecHdg(dx, dz) - g.w.hdg)) > 40 * DEG) return false;
    const T = typeOf(tr); const along = (r.x - g.w.x) * g.w.dx + (r.z - g.w.z) * g.w.dz + antOf(T, T ? T.L : 38);
    return along < 4;
  }
  // stationary on the ground: median pose, stand matching, parking
  stationary(tr, r, t) {
    const S = tr.still; if (!S.length) tr.stillSince = t; S.push(r); while (S.length > 200 || (S.length > 12 && t - S[0].t > 600000)) S.shift();
    // median of every stationary report kept (<= 200, <= 10 min): a parked aircraft's GNSS position wanders +-15 m at
    // 0 kt near the terminal (AAL2885 at B19, 24 Sep 16:39-16:47Z), a short window follows the wander
    // At its stand, 20 s after in-block, a transponder that reports < 0.5 kt is not moving: the parked pose is frozen and
    // the position wander is ignored until a report shows >= 0.5 kt (a slow tow: ACA738 0.7 kt off C10) or real motion.
    // Replay check 25 Sep: AAL177 A321, SFO stand B16, 07:46:37-07:47:12Z -- 0.0 kt reports wandered 24 m toward B15; the
    // median followed, the body was re-placed three times and the stand flipped B16 -> B15 (review round 1: x4 in-blocks)
    const frozen = !!(tr.gate && tr.stillPos && tr.inBlockAt != null && t - tr.inBlockAt > 20000 && !(r.gsKt != null && r.gsKt >= 0.5));
    if (frozen) this.counters.parkFrozen = (this.counters.parkFrozen || 0) + 1;
    const mx = frozen ? tr.stillPos[0] : median(S.map(q => q.x)), mz = frozen ? tr.stillPos[1] : median(S.map(q => q.z));
    const hs = S.filter(q => q.hdReal).map(q => q.th);
    // hysteresis: the parked pose moves only when the median really moved (> 4 m / > 5 deg), so parked aircraft never
    // creep with the report scatter
    if (!tr.stillPos || Math.hypot(mx - tr.stillPos[0], mz - tr.stillPos[1]) > 4) tr.stillPos = [mx, mz];
    const hm = hs.length >= 3 && !frozen ? circMedian(hs) : null;
    if (tr.stillHdg == null || (hm != null && Math.abs(wrapPi(hm - tr.stillHdg)) > 5 * DEG)) tr.stillHdg = hm ?? tr.stillHdg ?? r.hd;
    // a remembered aircraft whose transponder is off cannot be where a live one now stands: it has left (towed/departed)
    const T0 = typeOf(tr), L0 = T0 ? T0.L : 38;
    for (const o of this.tracks.values()) {
      if (o === tr || !o.stale) continue; const P = o.parkPos || o.stillPos || (o.last && [o.last.x, o.last.z]); if (!P) continue;
      // (fuselages overlapping: < 0.25 (L1 + L2) apart. Not 0.45: adjacent contact stands are only ~35-45 m apart, and a
      // live aircraft stopping at B23 removed the silent one parked at B24 -- review round 2, AAL2506, 24 Sep 08:57Z. The
      // same stand is handled by occupy())
      const To = typeOf(o); if (Math.hypot(P[0] - mx, P[1] - mz) < 0.25 * (L0 + (To ? To.L : 38))) { this.event(o, t, 'stale-replaced', { by: tr.hex }); this.remove(o); }
    }
    const dur = t - S[0].t;
    // no longer on its stand: a tow or a creep below the taxi threshold (1.5 kt) moves the median away from the stand while
    // every report is 'stationary' (review round 2: ACA738 towed off C10 at 0.7 kt, FFT3308 off B17 at 0.5 kt, both
    // labelled at their old gate 80-114 m away). The stand is released when the pose no longer fits it (1.3x limits).
    // (the misfit must last 20 s, and not within the first minute after in-block, while the median still carries the
    // arrival's creep: AAL177 A321 flipped B16 -> B15 -> B16 within 64 s of stopping, replay check 25 Sep, 07:46Z)
    if (tr.gate && !tr.stale && this.gateScore(tr.gate, { x: mx, z: mz, hd: tr.stillHdg, hdReal: hs.length >= 3, icao: tr.info.icao }, T0, 1.3) == null) {
      if (tr.misfitT == null) tr.misfitT = t;
      if (t - tr.misfitT >= 20000 && t - (tr.inBlockAt ?? 0) >= 60000) {
        this.event(tr, t, 'stand-left', { stand: tr.gate.name, slow: true }); this.releaseGate(tr, t); tr.leaving = false; this.counters.standLeftSlow = (this.counters.standLeftSlow || 0) + 1;
      }
    } else tr.misfitT = null;
    // (not back onto the stand it was pushed back from within 10 min: a push-back that pauses on the lead-in -- engine
    // start, tug disconnect -- is not a new in-block, and its bridge must not come out again; replay check 25 Sep: UAL1111
    // at E7 15:38:19-15:39:09Z logged off-block, in-block, off-block. A 'forward' off-block can be a missed creep or push
    // start (UAL755 F17 20:09Z), so it does not block the stand)
    if (!tr.gate && (dur >= 20000 || tr.dock || !tr.seenMoving)) { const g = this.matchGate(tr, { x: mx, z: mz, hd: tr.stillHdg, hdReal: hs.length >= 3, icao: tr.info.icao });
      if (g && !(tr.offBlock && tr.offBlock.stand === g.name && t - tr.offBlock.t < 600000)) this.occupy(tr, g, t); }
    if (tr.gate) this.updatePark(tr);
    else if (!tr.freePark || Math.hypot(tr.freePark[0] - mx, tr.freePark[1] - mz) > 15) tr.freePark = [mx, mz];
    // parked on a ramp (not a taxiway or runway) for a minute, not after its own push-back: its next movement may be a
    // push-back even without a heading (see report())
    // (off a stand: first seen parked there for a minute, or -- after it was seen moving (an arrival waiting for its
    // stand, a departure holding after its push) -- stopped there for 10 min: review round 2, 42 'forward off-blocks'
    // without a stand in 80 min, from aircraft that had only waited on the apron)
    const stillFor = t - (tr.stillSince ?? S[0].t);
    if (!tr.pushOk && !tr.pushback && (tr.gate || (stillFor >= (tr.seenMoving ? 600000 : 60000) && !tr.pushed && !inPolys(this.taxiways, mx, mz) && !runwayAt(mx, mz)))) tr.pushOk = true;
    // it stopped again where it was parked (a creep to the stop mark, a re-position): the bridge may dock again. After an
    // off-block (a push that stopped within 12 m of the stand) only after 5 min
    if (tr.leaving && dur >= (tr.pushed ? 300000 : 8000)) tr.leaving = false;
  }
  distToPark(tr, r) { const p = tr.parkRep || tr.stillPos; return p ? Math.hypot(r.x - p[0], r.z - p[1]) : 0; }

  // heading of an aircraft first seen standing still with no heading reported: lined up on a runway (departure
  // direction from the nearer end); on a taxiway along the centreline, facing the nearest runway; on a ramp nose-in at a
  // nearby stand, else nose toward the nearest building face along the airport grid, else toward the terminal core
  guessGroundHeading(tr, x, z) {
    const rws = runwayAt(x, z);
    if (rws) { let best = null, bd = 1e9; for (const R of rws) { const a = (x - R.start[0]) * R.dir[0] + (z - R.start[1]) * R.dir[1]; if (a < bd) { bd = a; best = R; } } return best.hdg; }
    const mm = this.net.ok ? this.net.match(x, z, null, null, 12) : null;
    if (mm && !mm.e.rw && inPolys(this.taxiways, x, z)) {
      let h = vecHdg(mm.ux, mm.uz); const v = hdgVec(h);
      let rb = null, rd = 1e9; for (const R of RWY) { const a = clamp((x - R.start[0]) * R.dir[0] + (z - R.start[1]) * R.dir[1], 0, R.len); const px = R.start[0] + R.dir[0] * a, pz = R.start[1] + R.dir[1] * a; const d = Math.hypot(px - x, pz - z); if (d < rd) { rd = d; rb = [px - x, pz - z]; } }
      if (rb && v[0] * rb[0] + v[1] * rb[1] < 0) h += Math.PI;
      return wrapPi(h);
    }
    // an OSM stand lead-in line (aeroway=parking_position) within 12 m: its parked heading (covers remote/cargo stands)
    let li = null, ld = 12;
    for (const l of this.net.leadins || []) { const s0 = l.stop; if (Math.abs(s0[0] - x) > 150 || Math.abs(s0[1] - z) > 150) continue; for (let i = 1; i < l.pts.length; i++) { const a = l.pts[i - 1], b = l.pts[i]; const dx = b[0] - a[0], dz = b[1] - a[1], L2 = dx * dx + dz * dz || 1; const u = clamp(((x - a[0]) * dx + (z - a[1]) * dz) / L2, 0, 1); const d = Math.hypot(x - a[0] - dx * u, z - a[1] - dz * u); if (d < ld) { ld = d; li = l; } } }
    if (li) return li.hdg * DEG;
    let g = null, gd = 60; for (const q of this.gates) { const d = Math.hypot(x - q.w.x, z - q.w.z); if (d < gd) { gd = d; g = q; } }
    if (g) return g.w.hdg;
    if (this.buildingAt) {
      let best = null, bd = 90;
      for (const h of [27.83, 117.83, 207.83, 297.83]) { const v = hdgVec(h * DEG); for (let d = 6; d < bd; d += 3) if (this.buildingAt(x + v[0] * d, z + v[1] * d)) { bd = d; best = h * DEG; break; } }
      if (best != null) return best;
    }
    const b = vecHdg(-950 - x, 250 - z) / DEG; let hb = 27.83, dd = 1e9;
    for (const h of [27.83, 117.83, 207.83, 297.83]) { const e = Math.abs(((b - h + 540) % 360) - 180); if (e < dd) { dd = e; hb = h; } }
    return hb * DEG;
  }

  // ---------------------------------------------------------- stands
  planStand(tr) { // SFO's allocation for this callsign now (relay /api/gates), as a stand name
    const P = this.plan; if (!P || !tr.cs || !tr.cs.callsign) return null;
    const norm = (c) => { const m = /^([A-Z]{3})0*(\d+[A-Z]?)$/.exec(c || ''); return m ? m[1] + m[2] : c; };
    let cs = norm(tr.cs.callsign); if (P.aliases && P.aliases[cs]) cs = P.aliases[cs].to || P.aliases[cs];
    const e = P.byCallsign && P.byCallsign[cs]; if (!e || !e.stand) return null;
    const now = this._lastRecv || Date.now(); const s = e.stand;
    if (s.from && s.to && (now < s.from * (s.from > 1e12 ? 1 : 1000) - 1800e3 || now > s.to * (s.to > 1e12 ? 1 : 1000) + 1800e3)) return null;
    return { name: String(s.name || '').toUpperCase(), base: String(s.base || '').toUpperCase() };
  }
  gateByName(n) { if (!n) return null; for (const g of this.gates) if (g.names.includes(n.name) || (n.base && g.names.includes(n.base))) return g; return null; }
  // score of a stationary (median) pose against a stand. Contact stands: distance of the report from where this
  // aircraft's ADS-B antenna would be if its nose were at the stand's stop point (lateral error weighted more), plus
  // a heading term when a true heading is reported; the aircraft must physically fit. Remote stands: distance.
  // relax > 1 widens the limits (SFO's own allocation for this callsign; keeping a stand already occupied)
  // The expected nose is the stand's stop point for this aircraft's family where the data has one (type_stops, p.icao).
  // A stand whose axis the ADS-B evidence contradicts (data `conflict`: D3, D4, D8, D9 -- aircraft with SFO's stand
  // window sit 2-8.5 m / up to 24 deg off it) tolerates that offset (static_geometry_round2.md #6).
  gateScore(g, p, T, relax = 1) {
    if (g.bridge) {
      const L = T ? T.L : (g.wide ? 63 : 38); const a0 = stopAlong(g, p.icao);
      const ex = g.w.x + g.w.dx * (a0 - antOf(T, L)), ez = g.w.z + g.w.dz * (a0 - antOf(T, L));
      const rx = p.x - ex, rz = p.z - ez;
      const along = -(rx * g.w.dx + rz * g.w.dz), lat = -rx * g.w.dz + rz * g.w.dx;
      const cf = g.conflict || null;
      const latMax = (Math.min(18, 0.35 * g.maxSpan + 4) + (cf ? Math.abs(cf.lat_med || 0) + 2 : 0)) * relax;
      if (Math.abs(lat) > latMax || Math.abs(along) > 22 * relax) return null;
      const dh = p.hdReal && p.hd != null ? Math.abs(wrapPi(p.hd - g.w.hdg)) / DEG : 0;
      if (dh > (35 + (cf ? Math.abs(cf.dhdg_med || 0) : 0)) * relax) return null;
      return Math.abs(lat) + 0.35 * Math.abs(along) + 0.15 * dh;
    }
    const d = Math.hypot(p.x - g.w.x, p.z - g.w.z); return d < 40 * relax ? d + 4 : null;
  }
  matchGate(tr, p) {
    if (inPolys(this.taxiways, p.x, p.z) || runwayAt(p.x, p.z)) return null;
    const T = typeOf(tr);
    // 1. SFO's own allocation, if this aircraft is really close to that stand (the owner can check it on flysfo.com)
    const pn = this.planStand(tr); const pg = this.gateByName(pn);
    // (on that stand's lead-in / pose within 1.3x the geometric limits -- not merely within 70 m of it: aircraft wait on the
    // apron for their allocated stand, and were labelled 'Gate B17 · SFO' 80 m away; review round 2, FFT3308 15:58Z)
    // (class limits, not the types_ok whitelist: SFO's allocation is followed; a mutually exclusive stand occupied by a LIVE
    // aircraft blocks it -- static_geometry_round2.md #5; a silent one there is replaced, see occupy)
    const icao = tr.info.icao;
    if (pg && standFits(pg, T, icao, false) && !this.blocked(pg, tr, true) && this.gateScore(pg, p, T, 1.3) != null) { tr.gateScore = 0; tr.gateSrc = 'sfo'; return pg; }
    // 2. geometry + heading
    let best = null, bd = 1e9;
    for (const g of this.gates) {
      if (!standFits(g, T, icao)) continue;
      const sc = this.gateScore(g, p, T); if (sc == null) continue;
      if (g.occupant && g.occupant !== tr.hex) { const o = this.tracks.get(g.occupant); if (o && !o.stale && o.gateScore != null && o.gateScore <= sc) continue; }
      if (this.blocked(g, tr)) continue;
      if (sc < bd) { bd = sc; best = g; }
    }
    if (best) { tr.gateScore = bd; tr.gateSrc = pn ? (this.gateByName(pn) === best ? 'sfo' : 'geo') : 'geo'; }
    return best;
  }
  // a stand is blocked when an aircraft parked at a neighbouring stand is larger than that stand's class allows
  // (liveOnly: an aircraft that is silent (remembered) there does not block -- SFO's allocation replaces it)
  blocked(g, tr, liveOnly = false) {
    for (const n of g.excl || []) { const o = this.gateBy.get(n); if (o && o.occupant && o.occupant !== tr.hex) { const q = liveOnly && this.tracks.get(o.occupant); if (!(q && q.stale)) return true; } } // mutually exclusive stands (SFO MARS)
    for (const o of this.gates) {
      if (o === g || !o.occupant || o.occupant === tr.hex || !o.oversize) continue;
      if (Math.hypot(o.w.x - g.w.x, o.w.z - g.w.z) < 0.5 * (o.maxSpan + g.maxSpan) + 8) return true;
    }
    return false;
  }
  occupy(tr, g, t) {
    if (g.occupant && g.occupant !== tr.hex) { const o = this.tracks.get(g.occupant); if (o) { if (o.stale) this.remove(o); else this.releaseGate(o); } }
    // a silent aircraft remembered on a mutually exclusive stand (B5 / B5S ...) has left: this one stands there now
    for (const n of g.excl || []) { const q = this.gateBy.get(n); const o = q && q.occupant && q.occupant !== tr.hex ? this.tracks.get(q.occupant) : null; if (o && o.stale) { this.event(o, t ?? tr.lastFixT, 'stale-replaced', { by: tr.hex, excl: g.name }); this.remove(o); } }
    // (a body that came to rest before the stand was recognised is re-settled onto the stand pose: its free-parking lock,
    // up to 8 m off, would otherwise be kept while within LOCK_M of the stand pose -- review round 2: UAL822 at G7 drawn
    // 5.6 m off the stand for the whole turn, its bridge docked there)
    if (tr.lock && !tr.bridgeOn) tr.lock = null;
    tr.gate = g; g.occupant = tr.hex; tr.dock = null; tr.shortBlocked = false; tr.misfitT = null;
    const T = typeOf(tr); g.oversize = !!(T && T.wing && (T.wing.span > g.maxSpan + 0.5));
    this.updatePark(tr);
    // in-block: a new turn begins (its departure pushes from here; the arrival's runway no longer applies: review
    // round 1, SKW3007 reported the stale arrival runway at its departure)
    tr.pushOk = !tr.pushback; tr.pushbackFrom = null; tr.pushed = false; tr.inBlockAt = t ?? tr.lastFixT; tr.leaving = false;
    if (tr.m.phase === 'still') tr.m.rwy = null;
    if (t != null) this.event(tr, t, 'in-block', { stand: g.name, src: tr.gateSrc || 'geo' });
    // the jet bridge docks later, from the display side, once the drawn aircraft has settled at this pose (syncBridge)
    this.saveParkedSoon();
  }
  // parked pose at a stand: the stand's lead-in (nose at the stop point) unless the aircraft reports a clearly
  // different heading (the survey can be off: ACA738 reported 321 deg at C10, surveyed 298 deg, audit F7) -- then its
  // own median pose. GroundPhysics checks the data pose for clearance and falls back to the stand pose.
  updatePark(tr) {
    const g = tr.gate; if (!g) return; const T = typeOf(tr); const L = T ? T.L : (g.wide ? 63 : 38);
    const sp = tr.stillPos || (tr.last ? [tr.last.x, tr.last.z] : [g.w.x, g.w.z]); tr.parkRep = sp;
    if (g.bridge) {
      const dh = tr.stillHdg != null && tr.still.some(q => q.hdReal) ? wrapPi(tr.stillHdg - g.w.hdg) : 0;
      // on the lead-in line, at the aircraft's own stop mark: stop bars differ by type, so the along-line position comes
      // from the reports (median), never past the stand's surveyed stop point and at most 25 m short of it. Where the data
      // has this family's stop (type_stops) and the reports agree within 6 m, that stop; a pose short of the stop that
      // would touch an occupied neighbour (GroundPhysics sets tr.shortBlocked) goes to the stop -- static_geometry_round2
      // #3/#4 (stop-short overlaps A1/B2, B3/C1, B5/B10, F9/F10 ...)
      const rx = sp[0] - g.w.x, rz = sp[1] - g.w.z; const lat = -rx * g.w.dz + rz * g.w.dx;
      const fa = stopAlong(g, tr.info.icao), hasFs = !!(g.typeStops && g.typeStops[familyOf(tr.info.icao)]);
      const ownA = clamp((rx * g.w.dx + rz * g.w.dz) + antOf(T, L), -25, 0);
      const noseAlong = tr.dockComplete || tr.shortBlocked || (hasFs && Math.abs(ownA - fa) < 6) ? fa : ownA;
      tr.parkAlong = noseAlong; tr.stopAlong = fa;
      // own pose vs stand pose, with hysteresis so that the report scatter does not flip it (data: > 8 deg or > 6 m off the
      // lead-in; back to the stand pose below 5 deg and 4 m)
      const own = tr.parkMode === 'data' ? (Math.abs(dh) > 5 * DEG || Math.abs(lat) > 4) : (Math.abs(dh) > 8 * DEG || Math.abs(lat) > 6);
      if (own && !tr.forceStand) { tr.parkMode = 'data'; tr.parkHdg = tr.stillHdg; tr.parkPos = sp.slice(); }
      else { tr.parkMode = 'stand'; const a = noseAlong - antOf(T, L); tr.parkPos = [g.w.x + g.w.dx * a, g.w.z + g.w.dz * a]; tr.parkHdg = g.w.hdg; }
    } else { tr.parkMode = 'data'; tr.parkPos = sp.slice(); tr.parkHdg = tr.stillHdg ?? (tr.last ? tr.last.hd : g.w.hdg); }
  }
  releaseGate(tr, t) {
    const g = tr.gate; if (!g) return; if (g.occupant === tr.hex) { g.occupant = null; g.oversize = false; }
    tr.parkRep = null; tr.parkPos = null; tr.gate = null; tr.forceStand = false; tr.lock = null;
    this.undock(tr); this.saveParkedSoon();
  }
  // retract the jet bridge docked to this aircraft (the body is held until it is clear: holdForBridge)
  undock(tr) { if (!tr.bridgeOn) return; tr.bridgeOn = false; this.counters.undocks = (this.counters.undocks || 0) + 1; this.onGateChange && this.onGateChange(tr.bridgeGate, null); }
  // docking: a slow taxiing aircraft close to a free stand's lead-in line and heading along it follows that line
  docking(tr, r, t) {
    if (r.gs > 8 * KT || tr.pushback) { if (r.gs > 10 * KT) tr.dock = null; return; }
    const T = typeOf(tr); const L = T ? T.L : 38;
    const pn = this.planStand(tr); const pg = this.gateByName(pn);
    let best = null, bd = 1e9;
    for (const g of pg ? [pg] : this.gates) {
      if (!g.bridge || (g.occupant && g.occupant !== tr.hex) || !standFits(g, T, tr.info.icao, !pg)) continue;
      const ex = g.w.x - g.w.dx * antOf(T, L), ez = g.w.z - g.w.dz * antOf(T, L);
      const rx = r.x - ex, rz = r.z - ez; const along = -(rx * g.w.dx + rz * g.w.dz), lat = -rx * g.w.dz + rz * g.w.dx;
      if (along < -3 || along > 60 || Math.abs(lat) > (pg ? 14 : 8) + along * 0.15) continue;
      if (Math.abs(wrapPi(r.dir - g.w.hdg)) > (pg ? 55 : 30) * DEG) continue;   // SFO's own allocation: turning in
      const s = Math.abs(lat) + 0.1 * along; if (s < bd) { bd = s; best = g; }
    }
    tr.dock = best ? { g: best, t } : null;
  }

  // ---------------------------------------------------------- per-frame update
  update(now, dt) {
    // integrate the bodies over the real elapsed time in <= 0.1 s sub-steps (slow frames, software rendering, a tab that
    // was in the background for a few seconds), so the kinematics never depend on the frame rate
    const el = this._lastNow != null ? clamp((now - this._lastNow) / 1000, 0, 5) : dt; this._lastNow = now;
    const nSub = Math.max(1, Math.ceil(el / 0.1 - 1e-6)), h = el / nSub || dt;
    if (this.adaptDelay) this.delay += clamp(this.delayTarget - this.delay, -100 * el, 100 * el); // <= 0.1 s per s
    if (this.audioDelayTarget != null && this.audioDelay !== this.audioDelayTarget) this.audioDelay += clamp(this.audioDelayTarget - this.audioDelay, -250 * el, 250 * el);
    const tDisp = this.displayTime(now);
    const removed = [];
    // a track that has to go is faded out (CUT_S), then removed -- never a pop (a hidden one goes at once)
    const gone = (tr) => { if (!tr.disp.valid || !(tr.disp.alpha > 0.01)) removed.push(tr); else if (!tr.fadeOut) { tr.fadeOut = true; this.counters.fadeOuts = (this.counters.fadeOuts || 0) + 1; } };
    for (const tr of this.tracks.values()) {
      if (tr.fadeOut && !(tr.disp.alpha > 0.01)) { removed.push(tr); continue; }
      // lost during the take-off roll (coverage hole at the runway end): it lifted off unseen. Liftoff estimated where the
      // type's liftoff speed is reached at 2 m/s^2 from the last report; a synthetic initial climb follows (vertical()).
      // Review round 2: AAL3222 A21N, last report at 125 kt on 28L (24 Sep 20:35:34Z), was dead-reckoned on the ground
      // past the runway end into a building
      if (!tr.stale && tr.m.phase === 'takeoff' && tr.last && tr.last.gs > 60 * KT && now - tr.lastFixT > 6000) {
        const M = tr.m, lf = tr.last, T = typeOf(tr); const vlo = (LIFTOFF_KT[tr.info.icao] || (T && T.L < 30 ? 125 : T && T.L < 42 ? 150 : 168)) * KT;
        const tl = lf.t + Math.max(0, (vlo - lf.gs) / 2) * 1000;
        M.lo = { t: tl, synthetic: true }; tr.liftoffAt = tl; this.setGround(tr, tl, false); this.setPhase(tr, 'climb', tl); tr.depRunway = M.rwy; tr.dirSFO = 'dep';
        this.event(tr, tl, 'liftoff', { rwy: M.rwy, gs: Math.round(vlo / KT), unseen: true, late: true }); this.counters.liftoffUnseen = (this.counters.liftoffUnseen || 0) + 1;
      }
      if (!tr.stale && !tr.fadeOut) {
        // age of the newest POSITION (not of the last response that listed the aircraft: a provider can repeat a position
        // for up to 60 s -- review round 2, SWA3361 stood on a taxiway 97 s after its last position at 6 kt and DAL672
        // drove through it)
        const age = now - Math.max(tr.lastFixT || 0, tr.lastRecv && !tr.lastFixT ? tr.lastRecv : 0), lf = tr.last;
        tr.noData = age > 20000;   // shown on the card: the position is that old
        if (tr.vehicle && age > VEH_KEEP_MS) { gone(tr); }
        else if (lf && !lf.ground && age > STALE_AIR_MS) { gone(tr); }
        // moving on the ground (taxi, push-back, line-up, roll) with no position for 45 s: where it is now is unknown (it
        // may have moved 200 m) -- faded out, and faded in where it is heard next
        else if (lf && lf.ground && age > (this.movingLostMs ?? MOVING_LOST_MS) && inAirport(lf.x, lf.z) && !tr.gate && (tr.m.phase !== 'still' || (lf.gs || 0) > 1)) { this.counters.movingLost = (this.counters.movingLost || 0) + 1; gone(tr); }
        else if (lf && lf.ground && age > STALE_GROUND_MS) {
          if (!inAirport(lf.x, lf.z) || tr.vehicle) { removed.push(tr); continue; }
          // transponder switched off on the ground: keep it where it is parked (at its gate if it was at one)
          // (switched off while docking: it completes the docking at the stand it was lining up with)
          if (!tr.gate && (lf.gs || 0) < 8 * KT && !tr.pushed) { const p = tr.stillPos ? { x: tr.stillPos[0], z: tr.stillPos[1], hd: tr.stillHdg, hdReal: false, icao: tr.info.icao } : { x: lf.x, z: lf.z, hd: lf.hd, hdReal: false, icao: tr.info.icao };
            const dg = tr.dock && tr.dock.g && (!tr.dock.g.occupant || tr.dock.g.occupant === tr.hex) && !this.blocked(tr.dock.g, tr) ? tr.dock.g : null;
            const g = dg || (tr.m.phase === 'still' ? this.matchGate(tr, p) : null); if (g) { if (dg) { tr.stillPos = null; tr.stillHdg = g.w.hdg; tr.forceStand = true; tr.dockComplete = true; } this.occupy(tr, g, null); } }
          // ...but only a PARKED aircraft (at a stand, or stopped on a ramp): one that went silent while taxiing, pushing,
          // lined up or holding on a taxiway/runway is dropped -- a ghost there is driven through by every aircraft that
          // passes (review round 1: stale SKW5471 'taxi' at (-1020,-327) overlapped by four 777s, UAN783UA 'pushback')
          const P = tr.parkPos || tr.stillPos || [lf.x, lf.z];
          const parked = !!tr.gate || (tr.m.phase === 'still' && !tr.pushback && !tr.pushed && !inPolys(this.taxiways, P[0], P[1]) && !runwayAt(P[0], P[1]));
          if (!parked) { gone(tr); this.counters.silentDropped = (this.counters.silentDropped || 0) + 1; }
          // (silent at its stand after a creep / re-position: it is parked there, its bridge may dock)
          else { tr.stale = true; tr.staleSince = now; if (tr.gate && !tr.pushed) tr.leaving = false; this.saveParkedSoon(); }
        }
      } else if (tr.stale && now - tr.lastRecv > PARK_KEEP_MS) { removed.push(tr); continue; }
      if (!tr.reps.length) continue;
      for (let i = 0; i < nSub; i++) this.step(tr, tDisp - (nSub - 1 - i) * h * 1000, h);
      this.syncBridge(tr, tDisp);
    }
    for (const tr of removed) this.remove(tr);
  }
  // Display side of parking (runs every frame, at display time): a parked aircraft whose drawn body has come to rest at
  // its parked pose is LOCKED there (the pose the bridge docks to and GroundPhysics checks); the jet bridge docks to that
  // drawn pose -- not to the first estimate (review round 1: bridges ended 2.4-25 m from the door after the estimate was
  // refined) -- and only to a 3-D airframe. Leaving (confirmed motion) or a parked-pose estimate that moved by more than
  // LOCK_M / LOCK_DEG undocks first; the body is held until the bridge is retracted (holdForBridge).
  syncBridge(tr, tDisp) {
    const c = tr.ctl, D = tr.disp;
    let unlocked = false;
    if (tr.lock) {
      const P = tr.parkPos || tr.stillPos, H = tr.parkPos ? tr.parkHdg : tr.stillHdg; const f = tr.gate && tr.parkMode === 'stand' ? 1 : 1.4, fh = tr.gate ? f : 2.8;
      const off = tr.physOff && !tr.gate ? tr.physOff : [0, 0];
      if (!P || Math.hypot(P[0] + off[0] - tr.lock.x, P[1] + off[1] - tr.lock.z) > LOCK_M * f || (H != null && Math.abs(wrapPi(H - tr.lock.hdg)) > LOCK_DEG * fh)) {
        if (this.lockLog) this.lockLog.push([tDisp, tr.hex, 'unlock', P && +Math.hypot(P[0] + off[0] - tr.lock.x, P[1] + off[1] - tr.lock.z).toFixed(2), H != null ? +(wrapPi(H - tr.lock.hdg) / DEG).toFixed(1) : null, tr.gate ? tr.gate.name : '-', tr.parkMode]);
        tr.lock = null; this.undock(tr); this.counters.unlocks = (this.counters.unlocks || 0) + 1; unlocked = true;
      }
    }
    if (tr.leaving) this.undock(tr);
    if (tr.bridgeGate && !tr.bridgeOn && !(this.bridgeK && this.bridgeK(tr.bridgeGate) > 0.01)) tr.bridgeGate = null;
    if (!c || !c.ground || tr.vehicle || !D.valid) return;
    const ph = tr.phaseAt(tDisp); const parkedNow = tr.stale || (ph ? ph[1] : tr.m.phase) === 'still';
    // (at a stand: on the stand pose; elsewhere -- holding, free parking -- where it came to rest within the report
    // scatter, <= 8 m / 20 deg, see ctlGround)
    const S = unlocked ? null : tr._stop; const tolM = tr.gate ? 0.6 : 8, tolH = (tr.gate ? 1.5 : 20) * DEG;
    if (!tr.lock && S && parkedNow && !tr.leaving && Math.abs(c.v) < 0.02 && !c.towing && !tr.cutting && D.alpha >= 1 &&
      Math.hypot(S.x - c.x, S.z - c.z) < tolM && (S.hd == null || Math.abs(wrapPi(S.hd - c.psi)) < tolH)) {
      tr.lock = { x: c.x, z: c.z, hdg: c.psi, t: tDisp }; this.counters.locks = (this.counters.locks || 0) + 1;
      if (S.hd == null && !tr.parkPos) tr.stillHdg = c.psi;   // (no heading reported: the body's heading is the estimate, see target())
    }
    const g = tr.gate;
    // an arrival seen taxiing in: the bridge waits DOCK_WAIT_MS after the body came to rest (and for no confirmed motion in
    // the reports ahead of the display): arrivals creep up to their stop mark at < 1.5 kt, which reads as stationary
    // (replay check 25 Sep, UAL2 B789 at G8 24 Sep 15:20:44-58Z). An aircraft first seen parked docks at once.
    let wait = false;
    if (tr.lock && tr.seenMoving && !tr.stale) { wait = tDisp - tr.lock.t < DOCK_WAIT_MS; for (let i = tr.reps.length - 1; !wait && i >= 0 && tr.reps[i].t > tDisp; i--) if (tr.reps[i].mv) wait = true; }
    if (tr.lock && g && !wait && !tr.bridgeOn && !tr.leaving && (g.bridge || g.sharesBridgesOf) && typeOf(tr) && (!tr.bridgeGate || tr.bridgeGate === g)) {
      tr.bridgeOn = true; tr.bridgeGate = g; tr.dockPose = { x: tr.lock.x, z: tr.lock.z, hdg: tr.lock.hdg };
      this.counters.docks = (this.counters.docks || 0) + 1; this.onGateChange && this.onGateChange(g, tr);
    }
  }
  // the pose a parked aircraft is drawn in (GroundPhysics): its lock, else the parked pose
  shownPark(tr) { return tr.lock ? { x: tr.lock.x, z: tr.lock.z, hdg: tr.lock.hdg } : tr.parkPos ? { x: tr.parkPos[0], z: tr.parkPos[1], hdg: tr.parkHdg } : null; }
  // target state at display time (reports + phase knowledge), then the kinematic body follows it
  target(tr, t, o) {
    sampleReps(tr.reps, t, o);
    const M = tr.m;
    const ph = tr.phaseAt(t); const p = ph ? ph[1] : M.phase;
    o.ground = tr.vehicle ? true : tr.groundAt(t, o.ground);
    o.stop = false; o.hd = null;   // (the target object is reused: clear the per-track fields)
    // parked: the median / stand pose (reports of parked aircraft scatter by up to ~20 m, audit s.4.2)
    const P = tr.parkPos || tr.stillPos || (tr.stale && tr.last ? [tr.last.x, tr.last.z] : null);
    // ...unless the next report shows it moving: then it left between the two reports (interpolate, no jump)
    // (a CONFIRMED moving report: position noise of a parked aircraft never moves it, see groundLogic)
    let nxt = null; if (!tr.stale) for (let i = tr.reps.length - 1; i >= 0 && tr.reps[i].t > t; i--) nxt = tr.reps[i];
    if (o.ground && P && (tr.stale || p === 'still') && !(nxt && nxt.mv)) {
      const K = tr.lock;   // settled: the drawn pose stays where it came to rest (and the bridge docked to it)
      if (K) { o.x = K.x; o.z = K.z; o.hd = K.hdg; } else { o.x = P[0]; o.z = P[1]; o.hd = tr.parkPos ? tr.parkHdg : (tr.stillHdg ?? (tr.last && tr.last.hd));
        // stopped off a stand with no heading reported (after it was seen moving): the heading is only an inference from the
        // last reports' path, and the drawn body -- which integrated that path -- is the better estimate. No heading target:
        // the body stops the way it arrived (replay check 25 Sep: UAL888 B772, no true_heading, stopped 5 times on its way
        // to 28L with 20-52 deg between the body and the inferred heading, each re-placed with a fade)
        if (!tr.parkPos && tr.seenMoving && !tr.stale && !tr.still.some(q => q.hdReal)) o.hd = null; }
      o.vx = o.vz = 0; o.gs = 0; o.stop = true; o.push = false;
    }
    // docking: pull the target onto the stand's lead-in line over the last 40 m
    if (o.ground && tr.dock && !o.stop) {
      const g = tr.dock.g, T = typeOf(tr), L = T ? T.L : 38;
      const ex = g.w.x - g.w.dx * antOf(T, L), ez = g.w.z - g.w.dz * antOf(T, L); const rx = o.x - ex, rz = o.z - ez;
      const along = -(rx * g.w.dx + rz * g.w.dz); const w = 1 - sstep(8, 40, along);
      const px = ex - g.w.dx * along, pz = ez - g.w.dz * along; o.x += (px - o.x) * w; o.z += (pz - o.z) * w;
    }
    if (o.ground) { o.y = GROUND_Y; o.vy = 0; }
    else this.vertical(tr, t, o, p);
    if (tr.physOff && !(o.stop && tr.lock)) { o.x += tr.physOff[0]; o.z += tr.physOff[1]; }
    o.phase = p; return o;
  }
  // vertical profile near the runway: the data (alt_geom, 25 ft quantised) blended below ~1000 ft into a straight
  // 3 deg path to the aiming point, a flare from 30 ft and a float to the predicted/detected touchdown point
  vertical(tr, t, o, p) {
    const M = tr.m;
    if ((p === 'final' || p === 'flare') && M.rwy) {
      const R = RWYN[M.rwy]; const [aa] = rwyCoords(R, o.x, o.z);
      const aTd = M.td && M.td.a != null ? clamp(M.td.a, 150, 2500) : TD_PRED_M;
      const tg = Math.tan(3 * DEG), hf = 9, aAim = 300; const aF = aAim - hf / tg; const lam = Math.max(40, (aTd - aF) / 3.8);
      const prof = (a) => a < aF ? (aAim - a) * tg : a < aTd ? Math.max(0.1, hf * Math.exp(-(a - aF) / lam)) : 0.1;
      const h = prof(aa), hData = o.y - GROUND_Y; const w = 1 - sstep(90, 300, hData);
      o.y = GROUND_Y + hData + (h - hData) * w; o.vy = o.vy * (1 - w) + (prof(aa + o.gs * 0.5) - h) / 0.5 * w; // profile slope x speed
    }
    if (p === 'takeoff' || p === 'rollout') { o.y = GROUND_Y; o.vy = 0; }
    // an unseen liftoff (lost on the roll): a 1,600 ft/min initial climb from the estimated liftoff point until data returns
    if (p === 'climb' && M.lo && M.lo.synthetic && o.ex > 0 && tr.last && tr.last.t < M.lo.t + 1000) { const s = clamp((t - M.lo.t) / 1000, 0, 90); o.y = Math.max(o.y, GROUND_Y + 8.1 * s * sstep(0, 4, s)); o.vy = 8.1 * sstep(0, 4, s); }
  }
  step(tr, tDisp, dt) {
    const o = this.target(tr, tDisp, this._tgt); const D = tr.disp; const T = typeOf(tr);
    let c = tr.ctl;
    if (D.alpha == null) D.alpha = 0;
    // (in the air a vertical error counts too: with the climb/descent rate capped (ctlAir), a large accepted altitude step is
    // re-placed with a fade rather than flown at an impossible rate)
    const err = c ? Math.max(Math.hypot(o.x - c.x, o.z - c.z), !o.ground && !c.ground ? Math.abs(o.y - c.y) * 1.5 : 0) : 0;
    // a take-off / landing roll is never re-placed (review round 1: bizjets out-accelerated the body on 28R and jumped)
    const roll = o.phase === 'takeoff' || o.phase === 'rollout' || o.phase === 'ground-other';
    const errMax = o.ground ? (roll ? 600 : 200) : Math.max(300, 4 * Math.hypot(o.vx, o.vz));
    // (after a gap an airborne body within ~2 s of flight of its target is corrected in flight, not faded: SWA2980 and
    // UAL2259 were faded for 30 m at 150 m/s, replay check 25 Sep)
    const reacq = tr.reacquire && err > (o.ground ? 30 : Math.max(30, 2 * Math.hypot(o.vx, o.vz)));
    if (tr.reacquire && c && !reacq && !tr.cutting) tr.reacquire = false;   // (close enough: followed, the flag is spent)
    // re-placement of a VISIBLE body (data gap, re-acquisition, runaway error) is a fade out -> move -> fade in, never a
    // jump or a drive across the airport (review round 1: 11 km teleports after a 214 s data gap; S-curves across stands)
    if (c && !tr.cutting && (reacq || err > errMax)) { if (D.valid && D.alpha > 0.01) tr.cutting = reacq ? 'gap' : 'err'; else { tr._reset = reacq ? 'gap' : 'err'; c = null; }
      if (this.lockLog) this.lockLog.push([tDisp, tr.hex, 'cut-' + (reacq ? 'gap' : 'err'), +err.toFixed(0), o.phase, o.ground ? 'g' : 'a', tr.info.flight, tr.info.category, D.valid && D.alpha > 0.01 ? 'vis' : 'hid', +Math.hypot(o.x - c.x, o.z - c.z).toFixed(0), +(o.y - c.y).toFixed(0)]); }
    if (tr.fadeOut) { D.alpha = Math.max(0, (D.alpha ?? 0) - dt / CUT_S); tr.cutting = null; }
    if (tr.cutting) { D.alpha = Math.max(0, D.alpha - dt / CUT_S); if (D.alpha <= 0) { this.counters['cut_' + tr.cutting] = (this.counters['cut_' + tr.cutting] || 0) + 1; tr._reset = 'cut'; tr.cutting = null; c = null; } }
    if (!c) {
      tr.reacquire = false;
      const pushing = o.push || o.phase === 'pushback';
      const hd0 = o.stop && o.hd != null ? o.hd : (o.gs > 0.5 ? vecHdg(o.vx, o.vz) + (pushing ? Math.PI : 0) : (tr.last ? tr.last.hd : 0));
      c = tr.ctl = { x: o.x, z: o.z, y: o.y, psi: wrapPi(hd0), v: o.gs * (pushing ? -1 : 1), a: 0, k: 0, vy: o.vy || 0, ay: 0, ground: o.ground, crab: 0, born: tDisp,
        // first seen standing: stays invisible until its parked pose has stopped changing (stand match, median, heading:
        // <= 10 s), so it appears in place instead of snapping (review round 1: 5-9 m / 180 deg snaps in the first 30 s)
        hideUntilSettled: !!(o.stop && o.ground) && !tr.everShown, poseKey: null, poseT: tDisp };
      D.alpha = 0;
    }
    if (c.hideUntilSettled) {
      const key = o.stop ? Math.round(o.x * 2) + ',' + Math.round(o.z * 2) + ',' + Math.round((o.hd ?? 0) / DEG) : null;
      if (key !== c.poseKey) { c.poseKey = key; c.poseT = tDisp; }
      if (!o.stop || tDisp - c.poseT > 3000 || tDisp - c.born > 10000) c.hideUntilSettled = false;
    } else if (!tr.cutting && !tr.fadeOut && D.alpha < 1) { D.alpha = Math.min(1, D.alpha + dt / CUT_S); if (D.alpha >= 1) tr.everShown = true; }
    tr._stop = o.stop ? { x: o.x, z: o.z, hd: o.hd } : null;
    if (o.ground && !c.ground && c.y > GROUND_Y + 0.05) { // touching down: the wheels meet the runway, no vertical jump
      o.y = GROUND_Y; o.vy = -1.0; this.ctlAir(tr, T, c, o, tDisp, dt); if (c.y <= GROUND_Y + 0.05) { c.y = GROUND_Y; c.vy = 0; c.ay = 0; }
    } else if (o.ground) this.ctlGround(tr, T, c, o, tDisp, dt); else this.ctlAir(tr, T, c, o, tDisp, dt);
    if (this.debug === tr.hex) tr._dbg = { t: tDisp, ox: o.x, oz: o.z, oy: o.y, ovx: o.vx, ovz: o.vz, ovy: o.vy, stop: o.stop, ph: o.phase, ex: o.ex, v: c.v, a: c.a, k: c.k, psi: c.psi, x: c.x, z: c.z, y: c.y, vy: c.vy };
    this.attitude(tr, T, c, o, tDisp, dt);
    D.x = c.x; D.y = c.y; D.z = c.z; D.gs = Math.abs(c.v); D.vs = c.vy; D.ground = c.ground; D.extrap = o.ex; D.valid = true;
    tr.phase = this.displayPhase(tr, o.phase, tDisp);
    if (tr.phase === 'final' && tr.m.rwy) { const R = RWYN[tr.m.rwy]; const [aa, cc] = rwyCoords(R, c.x, c.z); tr.finalInfo = { R, a: aa, c: cc }; }
    tr.finalLabel = tr.phase === 'final' ? finalRwyLabel(tr) : null;   // (ui.js / stats.js: the runway, or the pair while not firm)
  }
  // ground: a unicycle (moves along its nose; reverses for push-back) that tracks the target with bounded
  // longitudinal acceleration/jerk and a steering (curvature) limit from the nose-wheel geometry; pure pursuit steering
  ctlGround(tr, T, c, o, t, dt) {
    if (!c.ground) { c.ground = true; c.vy = 0; c.ay = 0; } // touchdown: wheels stay on the ground from here
    c.y = GROUND_Y; { const q = c.crab * (1 - Math.exp(-dt / 0.7)); c.crab -= clamp(q, -12 * DEG * dt, 12 * DEG * dt); }   // de-crab on the ground (<= 12 deg/s)
    const veh = tr.vehicle; const wb = T ? Math.max(6, (T.xMain || 15) - (T.xNose || 3)) : 12;
    // turning radius of the main-gear centre (the no-slip point of a nose-wheel-steered aircraft, bicycle model):
    // wheelbase / tan(max nose-wheel angle); ~75 deg steering -> ~0.27 x wheelbase [design value]
    const Rmin = veh ? 4 : Math.max(3, 0.27 * wb);
    // runway rolls: business jets accelerate at ~4 m/s^2 (review round 1: PFT144 C750 on 28R, 24 Sep 17:03Z, 0.5 -> 123 kt
    // in 16 s = 8 kt/s), airliners brake at up to ~3 m/s^2 after touchdown (audit s.3.2: 2.4-5.8 kt/s)
    // (airliners: take-off ~2-2.5 m/s^2, e.g. A320 0 -> 150 kt in ~35 s; so the cap is 3.3 m/s^2 for them and 5 m/s^2 for
    // light / business jets (< 30 m long or emitter category A1/A2); taxi: 1.8 m/s^2 forward, 2.0 m/s^2 braking (~0.2 g,
    // review round 2: the 3.0 m/s^2 taxi cap made 4,989 frames > 2 m/s^2 in 4.2 h))
    // (on the ground at another field above 30 kt = a take-off or landing roll there: the traffic engine only classifies
    // SFO's runways; review round 2: GA rolls at San Carlos / Palo Alto out-ran the 1.8 m/s^2 taxi cap and were re-placed)
    const roll = o.phase === 'takeoff' || o.phase === 'rollout' || (o.phase === 'ground-other' && Math.max(Math.hypot(o.vx, o.vz), Math.abs(c.v)) > 15);
    const lightJet = (T && T.L < 30) || /^A[12]$/.test(tr.info.category || '');
    const aAcc = veh ? 2.5 : roll ? (lightJet ? 5.0 : 3.3) : 1.8, aDec = veh ? 3.5 : roll ? (lightJet ? 4.5 : 3.3) : 2.0, J = veh ? 4 : roll ? 5.0 : 2.0, wMax = (veh ? 40 : 20) * DEG;
    const f = hdgVec(c.psi);
    let ex = o.x - c.x, ez = o.z - c.z, dist = Math.hypot(ex, ez);
    let along = ex * f[0] + ez * f[1];
    const vt = o.vx * f[0] + o.vz * f[1];
    const dh = o.hd != null ? wrapPi(o.hd - c.psi) : 0;
    // a jet bridge docked or still retracting: the aircraft does not move until it is clear (review round 1: push-backs
    // dragged the fuselage through the cab and tunnel)
    const holdBridge = !veh && (tr.bridgeOn || (tr.bridgeGate && this.bridgeK && this.bridgeK(tr.bridgeGate) > 0.01));
    // moved main-gear centre / antenna: back = antenna -> main-gear distance along the fuselage
    const back = T ? clamp((T.xMain ?? T.L * 0.47) - antOf(T), 1, 30) : (veh ? 0 : 8);
    // ---- the target is stopped (parked / holding) and the body is at rest
    if (o.stop && Math.abs(c.v) < 0.08) {
      c.v = 0; c.a = 0; c.k *= 0.8;
      if (tr.disp.alpha <= 0.001 && !tr.cutting) { c.x = o.x; c.z = o.z; if (o.hd != null) c.psi = o.hd; c.k = 0; c.towing = false; c.stuckT = 0; return; } // invisible: placed
      if (dist < 0.3 && Math.abs(dh) < 1 * DEG) { c.towing = false; c.stuckT = 0; c.towV = c.towW = 0; return; }
      if (holdBridge || tr.cutting) return;
      // stopped off a stand within the report scatter of its median pose (< 8 m, < 20 deg): it is there; nothing to move
      // (it came to rest in a physically consistent pose; syncBridge locks it there)
      if (!tr.gate && !c.towing && dist < 8 && Math.abs(dh) < 20 * DEG) { c.stuckT = 0; return; }
      // where the main gear must go, relative to the nose: straight ahead = the aircraft creeps forward under its own power
      const fT = hdgVec(o.hd ?? c.psi); const gx = (o.x - fT[0] * back) - (c.x - f[0] * back), gz = (o.z - fT[1] * back) - (c.z - f[1] * back);
      const gA = gx * f[0] + gz * f[1], gL = -gx * f[1] + gz * f[0];
      // along its own axis (the parked-pose estimate moved along the lead-in line): it creeps there -- forward under its
      // own power, backward pushed (<= 0.45 m/s) -- rather than being slid or re-placed
      const axial = Math.abs(gL) < 0.3 * Math.abs(gA) + 0.5 && Math.abs(dh) < 5 * DEG && Math.abs(gA) < 30 && Math.abs(gA) > 0.3;
      const creep = !c.towing && ((gA > 1.5 && Math.abs(gL) < 0.3 * gA + 0.5 && Math.abs(dh) < 15 * DEG && dist < 40) || axial);
      c.stuckT = (c.stuckT || 0) + dt;
      if (creep && c.stuckT <= 10) { c.v = Math.sign(gA) * 0.09; c.creep = true; }   // (continues in the driving controller below, <= 1 m/s)
      if (!creep || c.stuckT > 10) {
        // a small residual (<= 3 m, <= 10 deg) is towed slowly (<= 0.5 m/s, <= 2 deg/s, ramped); anything larger -- or a
        // body stuck for 10 s -- is re-placed with a fade: a parked aircraft is never driven in circles across a stand
        // (review round 1: a0f566 A321 drove an S-curve across B26 and then sat 6.5 m / 21 deg off its pose)
        if (c.stuckT <= 10 && ((dist <= 3 && Math.abs(dh) <= 10 * DEG) || (c.towing && dist <= 6 && Math.abs(dh) <= 15 * DEG))) {
          const moveP = dist > 0.3, moveH = Math.abs(dh) > 1 * DEG;
          c.towV = moveP ? Math.min((c.towV || 0) + 0.2 * dt, 0.5, Math.sqrt(2 * 0.2 * Math.max(0, dist - 0.3))) : 0;
          c.towW = moveH ? Math.min((c.towW || 0) + 1 * DEG * dt, 2 * DEG, Math.sqrt(2 * 1 * DEG * Math.max(0, Math.abs(dh) - 1 * DEG))) : 0;
          if (moveP && c.towV > 0) { const m = Math.min(dist, c.towV * dt) / dist; c.x += ex * m; c.z += ez * m; }
          if (moveH) c.psi = wrapPi(c.psi + Math.sign(dh) * Math.min(Math.abs(dh), c.towW * dt));
          if ((moveP || moveH) && !c.towing && this.towLog && this.towLog.length < 300) this.towLog.push([new Date(t).toISOString().slice(11, 19), tr.info.flight || tr.hex, +dist.toFixed(1), +(dh / DEG).toFixed(0), tr.gate ? tr.gate.name : '-', tr.parkMode || '-', o.phase, tr.stale ? 'stale' : '']);
          c.towing = moveP || moveH; if (c.towing) { this.counters.towS = (this.counters.towS || 0) + dt; if (this.towBy) this.towBy.set(tr.info.flight || tr.hex, (this.towBy.get(tr.info.flight || tr.hex) || 0) + dt); }
          return;
        }
        if (this.lockLog) this.lockLog.push([t, tr.hex, 'cut-repark', +dist.toFixed(1), +(dh / DEG).toFixed(0), o.phase, tr.info.flight, tr.gate ? tr.gate.name : '-', tr.parkMode, c.stuckT > 10 ? 'stuck' : '', +gA.toFixed(1), +gL.toFixed(1)]);
        tr.cutting = 'repark'; c.towing = false; return;
      }
    } else c.stuckT = 0;
    c.towing = false; if (!o.stop) c.creep = false;
    if (holdBridge) { // brake to a stop (<= 1.5 m/s^2) and stay
      const dv = Math.min(Math.abs(c.v), 1.5 * dt); c.v -= Math.sign(c.v) * dv; c.a = 0;
      const m0x = c.x - f[0] * back, m0z = c.z - f[1] * back; c.x = m0x + c.v * f[0] * dt + f[0] * back; c.z = m0z + c.v * f[1] * dt + f[1] * back;
      this.counters.bridgeHoldS = (this.counters.bridgeHoldS || 0) + dt; return;
    }
    // moving: work at the main-gear centre, the point that does not slip sideways; the nose swings around it (a push-back
    // turn pivots the aircraft about its main gear).
    const fT = hdgVec(o.hd ?? o.nh ?? c.psi);
    let mx = c.x - f[0] * back, mz = c.z - f[1] * back;
    ex = o.x - fT[0] * back - mx; ez = o.z - fT[1] * back - mz; dist = Math.hypot(ex, ez); along = ex * f[0] + ez * f[1];
    // desired speed: the target's speed along the nose plus a bounded catch-up term, capped by a comfortable braking
    // envelope (0.8 m/s^2) toward a stopped target so that the body arrives instead of overshooting.
    // critically damped along-track loop (omega 0.45 rad/s): a = w^2 e + 2 w (v_target - v); catch-up <= 3 m/s (<= 10 m/s
    // on a runway roll, where the reported speed changes by up to 4 m/s^2)
    const cu = roll ? 10 : 3;
    let sStar = vt + clamp(0.225 * along, -cu, cu);
    const tsp = Math.hypot(o.vx, o.vz);
    // reverse only when pushed back / towed: a push-back report at display time, or the target moving slowly (<= 3 m/s)
    // behind the nose
    // (the inferred case -- no push-back report, the target just lies behind -- is limited to 40 m of reverse travel: a
    // push-back is ~1-2 fuselage lengths. Beyond that the body's heading was the wrong guess and it turns around. Replay
    // 24 Sep 17:02-17:06Z: UAN783UA B772 under tow, no true_heading, was driven backwards 400 m at 3 m/s)
    if (c.v > 0.3) c.revImp = 0;
    const push = o.push || o.phase === 'pushback' || (!o.stop && tsp > 0.3 && tsp <= 3 && (o.vx * f[0] + o.vz * f[1]) < -0.5 * tsp && (c.revImp || 0) < 40);
    if (c.v < 0 && !(o.push || o.phase === 'pushback')) c.revImp = (c.revImp || 0) - c.v * dt;
    if (!push && !veh) sStar = Math.max(0, sStar);          // aircraft only reverse when pushed back (or power-back)
    // push-back 1-6 kt (audit s.3.6); never slower than the target itself moves forward (review round 1: a6bbef A21N was
    // held at 1 m/s by a stale push flag while taxiing at 4 m/s and fell 200 m behind)
    if (push) sStar = clamp(sStar, -3, Math.max(1, vt + 0.5));
    // (an inferred push -- no push-back in the data, the target just lies behind -- catches up at <= 0.7 m/s over the
    // target's own speed, >= 1 m/s: SKW3450 E75L, no true heading, reversed at 2.9 m/s after its stop target moved 17 m
    // behind it; replay check 25 Sep, 16:35Z)
    if (push && !(o.push || o.phase === 'pushback')) sStar = Math.max(sStar, -Math.max(1.0, tsp + 0.7));
    if (o.stop) {
      const lim = Math.sqrt(2 * 0.8 * Math.max(0, Math.abs(along) - 0.3));
      sStar = along >= 0 ? Math.min(lim, c.creep ? 1.0 : 12) : (along < -0.5 ? -Math.min(lim, push || veh ? 0.6 : 0.45) : 0); // a stopped target behind: pushed back slowly
    }
    // target behind the nose while moving forward (a U-turn, or the heading was unknown when first seen): turn around
    // at low speed with full steering instead of reversing
    // ...and the same when the target moves off to the side (> 60 deg) and is not well ahead: a rolling take-off from a
    // hold 90 deg to the runway (review round 2: UAL893 B789 at the 28L entrance, 24 Sep 18:31:55Z, stood still for 6 s
    // -- the target was beside it, so the desired speed was 0 -- and then fell 650 m behind the roll). Turning speed:
    // lateral acceleration <= 2.5 m/s^2 on twice the minimum radius, <= 6 m/s
    const tOff = tsp > 0.5 ? Math.abs(wrapPi(vecHdg(o.vx, o.vz) - c.psi)) : 0;
    const behind = !push && !o.stop && tsp > 0.5 && (tOff > 107 * DEG || (tOff > 60 * DEG && along < 0.3 * dist));
    if (behind) sStar = Math.min(Math.max(sStar, 2.5), Math.max(3, Math.min(6, Math.sqrt(2.5 * 2 * Rmin))));
    // a (nearly) stopped target that is not ahead: brake, do not orbit it
    const slowAside = !o.stop && !push && tsp < 0.7 && dist < 25 && Math.abs(wrapPi(vecHdg(ex, ez) - c.psi)) > 60 * DEG;
    if (slowAside) sStar = 0;
    let aCmd = clamp((o.stop ? 0 : o.acc || 0) * (c.v >= 0 ? 1 : -1) + 0.9 * (sStar - c.v), -aDec, aAcc);
    c.a += clamp(aCmd - c.a, -J * dt, J * dt); c.v += c.a * dt;
    if (Math.abs(c.v) < 0.05 && Math.abs(sStar) < 0.05) { c.v = 0; c.a = 0; }
    // steering toward a look-ahead point of the target trajectory
    const sp = Math.abs(c.v); const dirSign = c.v < -0.05 || (Math.abs(c.v) <= 0.05 && sStar < 0) ? -1 : 1;
    const tla = clamp((Math.max(sp, 1) * 1.2 + 4) / Math.max(1, Math.hypot(o.vx, o.vz)), 0.6, 3);
    let lx = o.x - fT[0] * back + o.vx * tla, lz = o.z - fT[1] * back + o.vz * tla;
    if (o.stop) { // a stopped target: pursue a point on its parked axis a little before it, so the body arrives aligned
      const hv = o.hd != null ? hdgVec(o.hd) : null; const backP = hv ? clamp(dist * 0.5, 0, 25) : 0;
      const tx = o.x - fT[0] * back, tz = o.z - fT[1] * back;
      lx = tx - (hv ? hv[0] * backP : 0); lz = tz - (hv ? hv[1] * backP : 0);
      if (dist < 6) { lx = tx + (hv ? hv[0] * 6 : 0); lz = tz + (hv ? hv[1] * 6 : 0); }
    }
    const dx = lx - mx, dz = lz - mz, dl = Math.hypot(dx, dz);
    let k = 0;
    if (dl > 1.0 && sp > 0.05) { const mdir = dirSign > 0 ? c.psi : c.psi + Math.PI; const al = wrapPi(vecHdg(dx, dz) - mdir);
      if (slowAside) k = 0;
      else if (behind || (Math.abs(al) > 90 * DEG && !o.stop && dirSign > 0)) k = Math.sign(wrapPi(vecHdg(o.vx, o.vz) - c.psi) || al) / Rmin; // U-turn
      else if (!(o.stop && Math.abs(al) > 100 * DEG)) k = dirSign * 2 * Math.sin(al) / Math.max(dl, 3); }
    // the last metres to a stopped target (a hold short, the end of a turn): turn the remaining heading error out over the
    // remaining distance instead of chasing its point -- pursuit there overshot the turn (review round 1 replay: UAL583
    // B39M came to rest 28 deg off its reported heading at a hold, 24 Sep 16:41Z)
    if (o.stop && o.hd != null && dist < 8 && sp > 0.05 && !slowAside) k = dirSign * clamp(wrapPi(o.hd - c.psi) / Math.max(Math.abs(along), 2), -1 / Rmin, 1 / Rmin);
    k = clamp(k, -1 / Rmin, 1 / Rmin); if (sp > 0.1) { k = clamp(k, -wMax / sp, wMax / sp); const kl = 2.5 / (sp * sp); k = clamp(k, -kl, kl); } // lateral <= 0.25 g
    // steering rate: full lock in 1.5 s at taxi speed, and a lateral jerk v^2 dk/dt <= 2.5 m/s^3 at speed (review round 2:
    // heading corrections on the take-off roll gave 8-15 m/s^3 at 44-66 m/s)
    const kdot = Math.min((1 / Rmin) / 1.5, 2.5 / Math.max(1, sp * sp)); c.k += clamp(k - c.k, -kdot * dt, kdot * dt);
    const x0 = c.x, z0 = c.z, psi0 = c.psi;
    mx += c.v * f[0] * dt; mz += c.v * f[1] * dt; c.psi = wrapPi(c.psi + c.v * c.k * dt);
    const f2 = hdgVec(c.psi); c.x = mx + f2[0] * back; c.z = mz + f2[1] * back;
    // building veto: the nose (driving forward) or the tail (pushed back) never enters a building -- the aircraft stops
    // at the face instead (review round 1: UAL888 B772 driven forward into the G5 terminal face on a wrong first guess)
    if (T && this.buildingAt && Math.abs(c.v) > 0.01) {
      const lead = c.v > 0 ? antOf(T) + 1 : -(T.L - antOf(T) + 1); const qx = c.x + f2[0] * lead, qz = c.z + f2[1] * lead;
      const px = x0 + f[0] * lead, pz = z0 + f[1] * lead;
      if (this.buildingAt(qx, qz) && !this.buildingAt(px, pz)) { c.x = x0; c.z = z0; c.psi = psi0; c.v = 0; c.a = 0; this.counters.buildingVeto = (this.counters.buildingVeto || 0) + 1; }
    }
  }
  // air: the same body with a bank-angle-limited turn radius, speed PD and a vertical channel (<= 0.25 g)
  ctlAir(tr, T, c, o, t, dt) {
    if (c.ground) { c.ground = false; c.v = Math.abs(c.v); }
    if ((o.gs < 25 && c.v < 25) || tr.info.category === 'A7') { // rotorcraft (emitter category A7) and slow targets: a point that follows the target (<= 2 m/s^2)
      c.vx = c.vx ?? c.v * hdgVec(c.psi)[0]; c.vz = c.vz ?? c.v * hdgVec(c.psi)[1];
      const am = tr.info.category === 'A7' ? 3 : 2;   // (rotorcraft: <= 0.3 g; they out-accelerated 2 m/s^2 and were re-placed)
      const ax = clamp(0.8 * (o.x - c.x) + 1.8 * (o.vx - c.vx), -am, am), az = clamp(0.8 * (o.z - c.z) + 1.8 * (o.vz - c.vz), -am, am);
      c.vx += ax * dt; c.vz += az * dt; c.x += c.vx * dt; c.z += c.vz * dt; c.v = Math.hypot(c.vx, c.vz); c.k = 0;
      if (c.v > 2) c.psi = wrapPi(c.psi + clamp(wrapPi(vecHdg(c.vx, c.vz) - c.psi), -10 * DEG * dt, 10 * DEG * dt));
      const ay = clamp(0.8 * (o.y - c.y) + 1.8 * (o.vy - c.vy), -2, 2); c.vy += ay * dt; c.y = Math.max(GROUND_Y, c.y + c.vy * dt); c.crab = 0; return;
    }
    // leaving the point-follower (slow) branch: the body moves along its velocity from here, and the drawn heading stays
    // continuous through the crab term (it decays <= 1.5 deg/s). Before, the motion jumped to the lagging heading: air
    // acceleration spikes of 4.7 m/s^2 on light aircraft (air.acc, replay check 25 Sep)
    if (c.vx != null && Math.hypot(c.vx, c.vz) > 2) { const hv = vecHdg(c.vx, c.vz); c.crab = clamp(wrapPi(c.crab + c.psi - hv), -30 * DEG, 30 * DEG); c.psi = hv; }
    c.vx = c.vz = undefined;
    const f = hdgVec(c.psi); const ex = o.x - c.x, ez = o.z - c.z;
    const along = ex * f[0] + ez * f[1]; const vt = o.vx * f[0] + o.vz * f[1];
    // along-track loop, critically damped at omega 0.3 rad/s (errors of ~10 m at 100 m/s are 0.1 s: invisible; speed
    // wobble is not); acceleration <= 2 m/s^2 (<= 0.2 g), jerk <= 1 m/s^3
    const sStar = vt + clamp(0.15 * along, -15, 15);
    const wheels = c.y - GROUND_Y < 1.5 && (o.phase === 'flare' || o.phase === 'rollout' || o.phase === 'takeoff'); // on / just above the runway
    const aCmd = clamp((o.acc || 0) + (wheels ? 0.9 : 0.6) * (sStar - c.v), wheels ? -3.5 : -2.0, wheels ? 3.0 : 2.0); c.a += clamp(aCmd - c.a, -(wheels ? 2 : 1) * dt, (wheels ? 2 : 1) * dt); c.v = Math.max(wheels ? 5 : 20, c.v + c.a * dt);
    const sp = c.v; const tla = 2.5; const lx = o.x + o.vx * tla, lz = o.z + o.vz * tla; const dx = lx - c.x, dz = lz - c.z, dl = Math.hypot(dx, dz);
    let k = dl > 1 ? 2 * Math.sin(wrapPi(vecHdg(dx, dz) - c.psi)) / Math.max(dl, 30) : 0;
    const light = tr.info.category === 'A1' || (T && T.L < 20); // light aircraft bank more (pattern work, training)
    const kMax = GRAV * Math.tan((light ? 45 : 30) * DEG) / Math.max(sp * sp, 1); k = clamp(k, -kMax, kMax); k = clamp(k, -(light ? 12 : 6) * DEG / sp, (light ? 12 : 6) * DEG / sp);
    const kdot = kMax / 2.5; c.k += clamp(k - c.k, -kdot * dt, kdot * dt);
    c.psi = wrapPi(c.psi + sp * c.k * dt); const f2 = hdgVec(c.psi); c.x += sp * f2[0] * dt; c.z += sp * f2[1] * dt;
    // vertical
    // omega 0.4 rad/s in the air (smooths the 25 ft quantisation), 1.2 rad/s below 100 m where the synthetic flare
    // profile is smooth and must be met; <= 0.2 g
    const w = (o.y - GROUND_Y) < 100 ? 2.0 : 0.4;
    const ay = clamp(w * w * (o.y - c.y) + 2 * w * (o.vy - c.vy), -2.0, 2.0); c.ay += clamp(ay - c.ay, -(w > 1 ? 6 : 2) * dt, (w > 1 ? 6 : 2) * dt);
    // vertical speed <= 6,000 ft/min (30.5 m/s), or the reported rate if higher: an altitude step accepted after three
    // consistent reports is flown, not dived at 10,000-26,000 ft/min (review round 1: '~' TIS-B targets, a C152)
    const vyMax = Math.max(30.5, Math.abs(o.vy || 0) * 1.1);
    c.vy += c.ay * dt; if (Math.abs(c.vy) > vyMax) { c.vy = Math.sign(c.vy) * vyMax; c.ay = 0; } c.y += c.vy * dt;
    if (c.y < GROUND_Y) { c.y = GROUND_Y; if (c.vy < 0) c.vy = 0; if (c.ay < 0) c.ay = 0; }
    // crab (true heading vs track), only when the aircraft reports its heading
    // (<= 1.5 deg/s: a change of the reported heading-track difference added up to 6.7 deg/s to the drawn turn rate,
    // replay check 25 Sep: E175 departures turning at 9-10 deg/s)
    // (the crab is kicked out in the flare: none below 10 m on final / in the flare, <= 4 deg/s there -- a crab carried onto
    // the runway showed as sideslip of the wheels after touchdown, gnd.slip)
    const L = tr.last; const low = c.y - GROUND_Y < 15 && (o.phase === 'final' || o.phase === 'flare' || o.phase === 'rollout' || o.phase === 'takeoff');
    const crabT = L && !L.ground && L.th != null && L.trk != null && !(low && c.y - GROUND_Y < 10) ? clamp(wrapPi(L.th - L.trk), -20 * DEG, 20 * DEG) : 0;
    const crR = (low ? 4 : 1.5) * DEG * dt; c.crab += clamp((crabT - c.crab) * Math.min(1, dt / (low ? 1 : 3)), -crR, crR);
  }
  displayPhase(tr, p, t) {
    if (tr.vehicle) return 'vehicle';
    const c = tr.ctl; if (p !== 'taxi') tr._revLbl = false;
    switch (p) {
      case 'flare': return 'final';
      // (the label follows the DRAWN body: the rollout ends in the data when a report is > 45 m off the centreline, so the
      // body -- interpolated between the last runway report and that one -- was already on the exit while still labelled
      // 'Landed'; a push-back that has ended is labelled 'Taxiing' as soon as the body rolls forward. Replay check 25 Sep:
      // phase.rwyphase_off_runway 203 frames, phase.pushback_forward 207 frames)
      case 'rollout': { const R = RWYN[tr.m.rwy] || RWYN[tr.arrRunway]; if (R && c && Math.abs(rwyCoords(R, c.x, c.z)[1]) > 40) return 'taxi'; return 'landing'; }
      case 'pushback': return c && c.v > 0.5 ? 'taxi' : 'pushback';
      case 'taxi': { // (moving backwards = pushed, whatever the data said; sticky until it rolls forward, so no flicker)
        if (c) tr._revLbl = c.v < -0.5 ? true : c.v > 0.3 ? false : !!tr._revLbl;
        return tr._revLbl ? 'pushback' : 'taxi'; }
      case 'climb': return 'departure';
      case 'still': {
        if (tr.gate) return 'gate';
        const key = Math.round(tr.disp.x / 3) + ',' + Math.round(tr.disp.z / 3);
        if (tr._stillKey !== key) { tr._stillKey = key; tr._stillLbl = runwayAt(tr.disp.x, tr.disp.z) || inPolys(this.taxiways, tr.disp.x, tr.disp.z) || (this.net.ok && this.net.match(tr.disp.x, tr.disp.z, null, null, 6)) ? 'holding' : 'parked'; }
        return tr._stillLbl;
      }
      case 'new': return tr.disp.ground ? (tr.stale ? 'parked' : 'holding') : 'enroute';
      default: return p || 'enroute';
    }
  }
  attitude(tr, T, c, o, t, dt) {
    const D = tr.disp, ph = o.phase; const gs = Math.abs(c.v);
    let pitchT = 0, rollT = 0;
    if (!c.ground) {
      const gam = Math.atan2(c.vy, Math.max(gs, 40));
      pitchT = gam + (gs < 75 ? 4.5 : 2.5) * DEG;
      if ((ph === 'final' || ph === 'flare') && c.y - GROUND_Y < 12) pitchT = Math.max(pitchT, 4.5 * DEG); // flare
      if (ph === 'climb' || ph === 'goaround') pitchT = Math.max(pitchT, clamp(gam + 5 * DEG, 8 * DEG, 17 * DEG));
      rollT = Math.atan(gs * gs * c.k / GRAV); rollT = clamp(rollT, -30 * DEG, 30 * DEG);
    } else if (ph === 'takeoff') { // rotation from ~8 kt before the liftoff speed of the type
      const vlo = (LIFTOFF_KT[tr.info.icao] || (T && T.L < 30 ? 125 : T && T.L < 42 ? 150 : 168)) * KT;
      pitchT = sstep(vlo - 10 * KT, vlo, gs) * 8 * DEG;
    }
    D.pitch += clamp(pitchT - D.pitch, -3 * DEG * dt, 3 * DEG * dt);
    D.roll += clamp(rollT - D.roll, -6 * DEG * dt, 6 * DEG * dt);
    D.hdg = wrapPi(c.psi + c.crab);
    // configuration
    const agl = c.y - GROUND_Y;
    let gearT = 0, flapsT = 0, splT = 0;
    const M = tr.m; const since = (e) => e ? (t - e.t) / 1000 : 1e9;
    if (c.ground) { gearT = 1; flapsT = ph === 'rollout' ? 1 : ph === 'takeoff' || ph === 'lineup' || (ph === 'taxi' && tr.dirSFO === 'dep') ? 0.35 : ph === 'taxi' && since(M.td) < 300 ? 0.5 : 0; splT = ph === 'rollout' && since(M.td) > 0.5 && gs > 40 * KT ? 1 : 0; }
    else if (ph === 'final' || ph === 'flare' || ph === 'approach') { gearT = agl < 600 || (ph !== 'approach' && agl < 900) ? 1 : 0; flapsT = clamp((235 - gs / KT) / 80, 0, 1) * (agl < 3000 ? 1 : 0); }
    else if (ph === 'climb' || ph === 'departure' || ph === 'goaround') { gearT = since(M.lo && ph !== 'goaround' ? M.lo : { t: M.gaT || 0 }) < 4 && agl < 150 ? 1 : 0; flapsT = gs / KT < 205 && agl < 1200 ? 0.35 : 0; }
    D.gear += clamp(gearT - D.gear, -dt / 7, dt / 7); D.flaps += clamp(flapsT - D.flaps, -dt / 12, dt / 12); D.spoilers += clamp(splT - D.spoilers, -dt / 1.5, dt / 1.5);
    if (!D.valid) { D.gear = gearT; D.flaps = flapsT; D.pitch = pitchT; D.roll = rollT; }
  }
  routeDirection(tr) {
    const r = tr.route; if (!r || !r.codes || !r.plausible || tr.dirFromRoute) return;
    const c = r.codes; const i = c.indexOf('SFO'); tr.dirFromRoute = true;
    if (i < 0) tr.dirSFO = tr.dirSFO === 'arr' && tr.finalInfo ? 'arr' : 'other';
    else if (i === c.length - 1) tr.dirSFO = tr.dirSFO || 'arr';
    else if (i === 0) tr.dirSFO = tr.dirSFO || 'dep';
  }
  setRoute(tr, route) { tr.route = route; tr.dirFromRoute = false; if (route && !tr.finalInfo && !tr.groundSFO) this.routeDirection(tr); }
  setPlan(plan) { this.plan = plan && plan.byCallsign ? plan : null; }
  remove(tr) { if (tr.gate) this.releaseGate(tr); this.tracks.delete(tr.hex); tr.removed = true; this.onRemove && this.onRemove(tr); }

  // ---------------------------------------------------------- persistence of parked aircraft
  saveParkedSoon() { if (!this.persist || this._saveT) return; this._saveT = setTimeout(() => { this._saveT = null; this.saveParked(); }, 3000); }
  saveParked() {
    const out = {};
    for (const tr of this.tracks.values()) {
      const lf = tr.last; if (!lf || !lf.ground || !inAirport(lf.x, lf.z) || tr.vehicle) continue;
      if (!(tr.gate || tr.m.phase === 'still' || tr.stale)) continue;
      const P = tr.parkPos || tr.stillPos || [lf.x, lf.z];
      out[tr.hex] = { hex: tr.hex, info: { flight: tr.info.flight, reg: tr.info.reg, icao: tr.info.icao, desc: tr.info.desc, ownOp: tr.info.ownOp },
        gate: tr.gate ? tr.gate.name : null, x: P[0], z: P[1], hd: tr.parkHdg ?? tr.stillHdg ?? lf.hd, mode: tr.parkMode || null, t: tr.lastRecv, route: tr.route || null, landedAt: tr.landedAt || 0 };
    }
    try { localStorage.setItem(STORE_KEY, JSON.stringify(out)); } catch (e) { }
  }
  loadParked() {
    let recs = null; try { recs = JSON.parse(localStorage.getItem(STORE_KEY) || 'null'); } catch (e) { }
    if (!recs) return;
    const now = Date.now();
    for (const r of Object.values(recs)) {
      if (!r || now - r.t > PARK_KEEP_MS) continue;
      const tr = new Track(r.hex); tr.firstSeen = r.t; tr.lastRecv = r.t; tr.stale = true; tr.staleRecord = true; tr.staleSince = r.t; tr.groundSFO = true; tr.route = r.route || undefined;
      this.setInfo(tr, { ...r.info, hex: r.hex });
      const t0 = now - DELAY_MAX - 1000;
      tr.reps.push({ t: t0, x: r.x, z: r.z, px: r.x, pz: r.z, y: GROUND_Y, ground: true, gs: 0, th: r.hd, trk: null, dir: r.hd, hd: r.hd, hdReal: true, vs: 0, vx: 0, vz: 0, turn: 0 });
      tr.lastFixT = t0; tr.stillPos = [r.x, r.z]; tr.stillHdg = r.hd; tr.m.phase = 'still'; tr.hist.push([0, 'still', null]); tr.air.push([0, true]);
      const g = r.gate && this.gates.find(q => q.name === r.gate);
      if (g && !g.occupant) { tr.gate = g; g.occupant = tr.hex; tr.parkPos = [r.x, r.z]; tr.parkRep = [r.x, r.z]; tr.parkHdg = r.hd; tr.parkMode = r.mode || 'stand'; tr.inBlockAt = r.t; }
      this.tracks.set(r.hex, tr);
    }
    // (their jet bridges dock once the drawn aircraft has settled: syncBridge)
  }
  clearParked() { try { localStorage.removeItem(STORE_KEY); } catch (e) { } }
  // lat/lon of a world point (WGS 84) for route lookups
  static wgs84(x, z) { return toWgs84 ? toWgs84(x, z) : null; }
}

// ---------------------------------------------------------------- display text
// the passenger gate number SFO displays (stands_rebuild.md s.8 `gate`: B5S -> B5), with the AODB stand when it differs
export function gateLabel(g) { const n = g.gateName || g.gate; return n && typeof n === 'string' && n !== g.name ? `${n} (stand ${g.name})` : g.name; }
export function phaseLabel(tr, now = Date.now()) {
  const base = phaseLabel0(tr, now);
  // no position for > 20 s (coverage gap, transponder off): say so (review round 1)
  return base && tr.noData && !tr.stale ? base + ' · no data ' + Math.round((now - tr.lastRecv) / 1000) + ' s' : base;
}
function phaseLabel0(tr, now) {
  const rw = tr.runway || tr.m.rwy; const g = tr.gate ? gateLabel(tr.gate) : null;
  const ago = (ms) => { const m = Math.round(ms / 60000); return m < 1 ? 'just now' : m < 60 ? m + ' min ago' : Math.floor(m / 60) + ' h ' + (m % 60) + ' min ago'; };
  switch (tr.phase) {
    case 'final': { if (!tr.finalInfo) return 'Final'; const d = -tr.finalInfo.a / NM; return d > 0.15 ? `Final ${finalRwyLabel(tr)} · ${d.toFixed(1)} nm` : `Landing ${tr.finalInfo.R.name}`; }
    case 'approach': return 'Arriving';
    case 'goaround': return `Go-around ${tr.m.rwy || ''}`.trim();
    case 'departure': return tr.depRunway ? `Departed ${tr.depRunway}` : 'Departing';
    case 'takeoff': return `Takeoff roll ${tr.m.rwy || rw || ''}`.trim();
    case 'lineup': return `Lined up ${tr.m.rwy || ''}`.trim();
    case 'landing': return `Landed ${tr.arrRunway || tr.m.rwy || ''}`.trim();
    case 'taxi': return tr.dirSFO === 'arr' ? 'Taxiing in' : tr.dirSFO === 'dep' ? 'Taxiing out' : 'Taxiing';
    case 'pushback': return 'Pushback' + (tr.pushbackFrom ? ' from ' + tr.pushbackFrom : '');
    case 'holding': return 'Holding';
    case 'gate': return (tr.gate && !tr.gate.bridge ? 'Stand ' : 'Gate ') + g + (tr.gateSrc === 'sfo' ? ' · SFO' : '') + (tr.stale ? ' · last signal ' + ago(now - tr.lastRecv) : '');
    case 'parked': return 'Parked' + (tr.stale ? ' · last signal ' + ago(now - tr.lastRecv) : '');
    case 'ground-other': return 'On ground (other airport)';
    case 'enroute': return 'En route';
    case 'vehicle': return tr.anon ? 'Unidentified ground target' : 'Airport vehicle';
    default: return '';
  }
}
export function category(tr) {
  if (tr.vehicle || tr.phase === 'vehicle') return 'vehicle';
  if (tr.phase === 'ground-other') return 'other';
  if (['gate', 'parked', 'taxi', 'pushback', 'holding', 'lineup', 'takeoff', 'landing'].includes(tr.phase)) return 'ground';
  if (tr.phase === 'final' || tr.phase === 'approach' || tr.phase === 'goaround') return 'arr';
  if (tr.phase === 'departure') return 'dep';
  return 'other';
}
