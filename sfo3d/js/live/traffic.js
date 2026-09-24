// Live traffic engine: turns periodic ADS-B snapshots into smoothly moving, phase-aware aircraft around SFO.
// Positions are shown with a short delay (DELAY_MS) so that motion is interpolated between real position reports;
// when reports are late the aircraft is dead-reckoned and corrections are blended out smoothly.
import { llToWorld, runwayByEnd, RUNWAYS, GROUND_Y, stToWorld, worldToST } from '../geo.js';
import { parseCallsign, typeInfo, liveryForAirline } from './lookup.js';
import { typeForIcao } from './aircraft.js';
import { TYPES } from '../aircraft/types.js';

const FT = 0.3048, KT = 0.514444, NM = 1852, DEG = Math.PI / 180, GRAV = 9.81;
const GEOID_N = -32.3;          // geoid undulation near SFO (m): orthometric (MSL) height = ellipsoid height - N
export const DELAY_MS = 7000;   // display delay: positions are interpolated between reports
const STALE_AIR_MS = 60000, STALE_GROUND_MS = 75000, PARK_KEEP_MS = 8 * 3600e3;
const STORE_KEY = 'sfolive.parked.v2'; // v2: surveyed stand layout (stand names changed)
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const sstep = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
const wrapPi = (a) => { a = (a + Math.PI) % (2 * Math.PI); if (a < 0) a += 2 * Math.PI; return a - Math.PI; };
const lerpAng = (a, b, u) => a + wrapPi(b - a) * u;
export const hdgVec = (h) => [Math.sin(h), -Math.cos(h)];   // world (x east, z south) unit vector for a true heading
export const ANT = 0.2; // ADS-B position reference (GNSS antenna) assumed ~20% of the length behind the nose
// does an aircraft of type T fit a stand (its class limits); unknown types are allowed
function standFits(g, T) {
  if (!T || g.remote || !g.maxSpan) return true;
  const span = T.wing ? T.wing.span : 36;
  if (span <= g.maxSpan + 0.6 && T.L <= g.maxLen + 2) return true;
  return g.maxSpan >= 64 && span <= 80; // 747-8 / A380 / 777-9 only on the largest stands (neighbours then blocked)
}
export const vecHdg = (x, z) => Math.atan2(x, -z);

// ---------------------------------------------------------------- runways (world frame)
export const RWY = [];
for (const r of RUNWAYS) for (const end of r.ends) {
  const R = runwayByEnd(end);
  RWY.push({ name: end, start: [R.from[0], -R.from[1]], thr: [R.thr[0], -R.thr[1]], dir: [R.dir[0], -R.dir[1]], len: R.length, hdg: Math.atan2(R.dir[0], R.dir[1]), pair: r.ends.join('/') });
}
function runwayAt(x, z) { // physical runway under a ground position -> [RWY entries for both directions]
  for (const R of RWY) {
    const dx = x - R.start[0], dz = z - R.start[1];
    const a = dx * R.dir[0] + dz * R.dir[1], c = -dx * R.dir[1] + dz * R.dir[0];
    if (a > -40 && a < R.len + 40 && Math.abs(c) < 36) return RWY.filter(q => q.pair === R.pair);
  }
  return null;
}
function runwayByHeading(list, h) { let best = null, bd = 1e9; for (const R of list) { const d = Math.abs(wrapPi(h - R.hdg)); if (d < bd) { bd = d; best = R; } } return best; }
function detectFinal(x, z, h, yAgl) { // aligned with a landing runway, before or over its first part
  let best = null;
  for (const R of RWY) {
    if (Math.abs(wrapPi(h - R.hdg)) > 22 * DEG) continue;
    const dx = x - R.thr[0], dz = z - R.thr[1];
    const a = dx * R.dir[0] + dz * R.dir[1], c = -dx * R.dir[1] + dz * R.dir[0];
    if (a < -30000 || a > 900) continue;
    if (Math.abs(c) > 150 + 0.1 * Math.abs(a)) continue;
    if (yAgl > 250 + Math.max(0, -a) * Math.tan(7 * DEG)) continue; // far above any glide path
    if (!best || Math.abs(c) < Math.abs(best.c)) best = { R, a, c };
  }
  return best;
}
export const inAirport = (x, z) => x > -2700 && x < 1950 && z > -2350 && z < 1800;

// ---------------------------------------------------------------- gates in world coordinates
function prepGates(gates) {
  const o = stToWorld(0, 0, 0);
  for (const g of gates) {
    const n = stToWorld(g.nose[0], g.nose[1], 0), d = stToWorld(g.dir[0], g.dir[1], 0), a = stToWorld(g.attach[0], g.attach[1], 0);
    const dx = d[0] - o[0], dz = d[2] - o[2], l = Math.hypot(dx, dz);
    g.w = { x: n[0], z: n[2], dx: dx / l, dz: dz / l, hdg: vecHdg(dx / l, dz / l), ax: a[0], az: a[2] };
    g.occupant = null;
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
    this.hex = hex; this.fixes = []; this.info = {}; this.firstSeen = 0; this.lastFixT = 0; this.lastRecv = 0;
    this.phase = 'new'; this.dirSFO = null; this.runway = null; this.gate = null; this.route = undefined; this.finalInfo = null;
    this.groundSFO = false; this.lastAirT = 0; this.lastGroundT = 0; this.landedAt = 0; this.liftoffAt = 0; this.stillSince = 0;
    this.pushback = false; this.stale = false; this.altBias = null;
    this.disp = { x: 0, y: GROUND_Y, z: 0, hdg: 0, pitch: 0, roll: 0, gear: 1, flaps: 0, spoilers: 0, gs: 0, vs: 0, ground: true, valid: false };
    this.corr = [0, 0, 0]; this.corrH = 0; this.prevHdg = null; this.turn = 0;
  }
  get last() { return this.fixes[this.fixes.length - 1]; }
  addFix(f) {
    const F = this.fixes;
    if (F.length && f.t <= F[F.length - 1].t + 20) { // same report again: refresh values only
      Object.assign(F[F.length - 1], { gs: f.gs, vs: f.vs, trk: f.trk ?? F[F.length - 1].trk, hd: f.hd ?? F[F.length - 1].hd });
      return false;
    }
    if (F.length && f.t < F[F.length - 1].t) return false; // out of order
    // fill in missing direction/speed from the previous report
    const p = F[F.length - 1];
    if (p) {
      const dt = (f.t - p.t) / 1000, dx = f.x - p.x, dz = f.z - p.z, d = Math.hypot(dx, dz);
      f.chordHdg = d > 3 ? vecHdg(dx, dz) : null; f.chordSpd = dt > 0 ? d / dt : 0;
      if (f.trk == null) f.trk = f.chordHdg ?? p.trk;
      if (f.hd == null) f.hd = f.trk ?? p.hd;
      if (f.gs == null) f.gs = f.chordSpd;
    }
    if (f.hd == null) f.hd = f.trk ?? 0; if (f.trk == null) f.trk = f.hd;
    F.push(f); while (F.length > 10 || (F.length > 3 && f.t - F[0].t > 90000)) F.shift();
    return true;
  }
  // position/heading/altitude at local time t (ms), from report history
  sample(t, out) {
    const F = this.fixes, n = F.length;
    if (!n) return null;
    if (t <= F[0].t || n === 1) return t <= F[0].t ? fixState(F[0], out) : extrap(F[n - 1], t, out);
    if (t >= F[n - 1].t) return extrap(F[n - 1], t, out);
    let i = n - 1; while (i > 0 && F[i - 1].t > t) i--;
    return interp(F[i - 1], F[i], t, out);
  }
}
function fixState(f, o) { o.x = f.x; o.z = f.z; o.y = f.y; o.hdg = f.hd; o.gs = f.gs; o.vs = f.ground ? 0 : (f.vs || 0); o.ground = f.ground; o.extrap = 0; return o; }
function vel(f) { const v = hdgVec(f.trk ?? f.hd); return [v[0] * f.gs, v[1] * f.gs]; }
function interp(a, b, t, o) {
  const dtm = b.t - a.t, dt = dtm / 1000, u = (t - a.t) / dtm;
  const cx = (b.x - a.x) / dt, cz = (b.z - a.z) / dt, cs = Math.hypot(cx, cz);
  let va = vel(a), vb = vel(b);
  const ok = (v) => Math.hypot(v[0] - cx, v[1] - cz) < Math.max(12, 0.45 * cs);
  const lin = dt > 30 || a.ground !== b.ground;
  if (lin || !ok(va)) va = [cx, cz]; if (lin || !ok(vb)) vb = [cx, cz];
  const u2 = u * u, u3 = u2 * u;
  const h00 = 2 * u3 - 3 * u2 + 1, h10 = u3 - 2 * u2 + u, h01 = -2 * u3 + 3 * u2, h11 = u3 - u2;
  o.x = h00 * a.x + h10 * dt * va[0] + h01 * b.x + h11 * dt * vb[0];
  o.z = h00 * a.z + h10 * dt * va[1] + h01 * b.z + h11 * dt * vb[1];
  if (!a.ground && !b.ground) {
    const cy = (b.y - a.y) / dt; let sa = a.vs ?? cy, sb = b.vs ?? cy;
    if (Math.abs(sa - cy) > Math.max(3, Math.abs(cy))) sa = cy; if (Math.abs(sb - cy) > Math.max(3, Math.abs(cy))) sb = cy;
    o.y = h00 * a.y + h10 * dt * sa + h01 * b.y + h11 * dt * sb;
  } else o.y = a.y + (b.y - a.y) * u;
  o.hdg = lerpAng(a.hd, b.hd, u);
  o.gs = a.gs + (b.gs - a.gs) * u; o.vs = a.ground || b.ground ? (b.y - a.y) / dt : (a.vs ?? 0) + ((b.vs ?? 0) - (a.vs ?? 0)) * u;
  o.ground = u < 0.5 ? a.ground : b.ground; o.extrap = 0;
  return o;
}
function extrap(f, t, o) {
  const dt = Math.min((t - f.t) / 1000, 45); o.extrap = dt;
  o.ground = f.ground; o.gs = f.gs; o.vs = f.ground ? 0 : (f.vs || 0);
  if (f.gs < 0.4) { o.x = f.x; o.z = f.z; o.y = f.y; o.hdg = f.hd; return o; }
  const maxW = (f.ground ? 12 : 3) * DEG; const w = clamp(f.trkRate || 0, -maxW, maxW);
  const th0 = f.trk ?? f.hd;
  const tt = Math.abs(w) > 1e-4 ? Math.min(dt, (Math.PI / 2) / Math.abs(w)) : 0;
  let x = f.x, z = f.z, th = th0;
  if (tt > 0) { const th1 = th0 + w * tt; x += f.gs / w * (Math.cos(th0) - Math.cos(th1)); z -= f.gs / w * (Math.sin(th1) - Math.sin(th0)); th = th1; }
  const rest = dt - tt; const v = hdgVec(th); x += v[0] * f.gs * rest; z += v[1] * f.gs * rest;
  o.x = x; o.z = z; o.hdg = f.hd + (th - th0);
  o.y = f.ground ? f.y : Math.max(GROUND_Y + 2, f.y + (f.vs || 0) * Math.min(dt, 20));
  return o;
}

// ---------------------------------------------------------------- traffic
export class Traffic {
  constructor({ gates = [], airport = null, delay = DELAY_MS, onGateChange = null, persist = true, centerlines = null } = {}) {
    this.centerlines = centerlines; this.tracks = new Map(); this.gates = prepGates(gates); this.taxiways = prepPolys(airport); this.delay = delay; this.offset = null;
    this.qnh = 1013.25; this.qnhSrc = 'standard'; this.metarQnh = null; this.onGateChange = onGateChange; this.persist = persist;
    this.lastIngest = 0; this.counts = {}; this.version = 0; this._tmp = {};
    if (persist) this.loadParked();
  }
  displayTime(now = Date.now()) { return now - this.delay; }

  // payload: { now (server ms), aircraft: [normalized records] }
  ingest(payload, recvNow = Date.now()) {
    const off = recvNow - payload.now;
    this.offset = this.offset == null ? off : Math.min(this.offset + (recvNow - (this._lastRecv || recvNow)) * 0.002, off);
    this._lastRecv = recvNow; this.lastIngest = recvNow;
    // local QNH from the altimeter settings of aircraft below 10,000 ft (fallback: METAR, then standard)
    const q = payload.aircraft.filter(a => a.navQnh && a.altBaro != null && a.altBaro < 10000 && a.navQnh > 960 && a.navQnh < 1050).map(a => a.navQnh).sort((a, b) => a - b);
    if (q.length >= 3) { this.qnh = q[q.length >> 1]; this.qnhSrc = 'aircraft'; } else if (this.metarQnh) { this.qnh = this.metarQnh; this.qnhSrc = 'METAR'; }
    const tDisp = this.displayTime(recvNow);
    const seen = new Set();
    for (const a of payload.aircraft) {
      if (!a.hex || seen.has(a.hex)) continue; seen.add(a.hex);
      if ((a.category && a.category[0] === 'C') || a.srcType === 'adsb_icao_nt') continue; // ground vehicles & obstacles
      const w = llToWorld(a.lat, a.lon, 0); const x = w[0], z = w[2];
      if (Math.hypot(x, z) > 75000) continue;
      let tr = this.tracks.get(a.hex);
      if (!tr) { tr = new Track(a.hex); tr.firstSeen = recvNow; this.tracks.set(a.hex, tr); }
      else if (tr.stale && tr.staleRecord) { tr.stale = false; tr.staleRecord = false; tr.fixes = []; } // a remembered aircraft is transmitting again
      this.setInfo(tr, a);
      const tf = a.t + this.offset;
      const ground = !!a.ground;
      let y = GROUND_Y;
      if (!ground) {
        const baro = a.altBaro != null ? (a.altBaro + (this.qnh - 1013.25) * 27.3) * FT : null;
        const geom = a.altGeom != null ? a.altGeom * FT - GEOID_N : null;
        if (baro != null && geom != null && a.altBaro < 20000) { const b = geom - baro; tr.altBias = tr.altBias == null ? b : tr.altBias + (b - tr.altBias) * 0.2; }
        y = baro != null ? baro + (tr.altBias != null ? clamp(tr.altBias, -150, 150) : 0) : geom != null ? geom : (tr.last ? tr.last.y : 300);
        y = Math.max(y, GROUND_Y + 1);
      }
      const trk = a.track != null ? a.track * DEG : null;
      const gsm = a.gs != null ? a.gs * KT : null;
      let hd = a.trueHeading != null ? a.trueHeading * DEG : trk;
      if (ground && a.trueHeading == null) {
        // on the ground the reported track is the direction of motion; keep a separate nose heading
        const moving = (gsm ?? 0) > 1.0;
        const lf = tr.last;
        const motion = trk ?? (lf && Math.hypot(x - lf.x, z - lf.z) > 3 ? vecHdg(x - lf.x, z - lf.z) : null);
        if (moving && motion != null && tr.gate && !tr.pushback && (gsm ?? 0) < 8 * KT) { const v = hdgVec(motion); if (v[0] * tr.gate.w.dx + v[1] * tr.gate.w.dz < -0.3) { tr.pushback = true; tr.pushbackFrom = tr.gate.name; } }
        if (tr.pushback && moving && motion != null && tr.nose != null && (Math.abs(wrapPi(motion - tr.nose)) < 60 * DEG || (gsm ?? 0) > 12 * KT)) tr.pushback = false;
        if (!moving || motion == null) hd = tr.nose ?? hd;
        else hd = tr.pushback ? wrapPi(motion + Math.PI) : motion;
      }
      if ((gsm ?? 0) > 1.0 && trk != null) tr.seenMoving = true;
      if (ground && hd != null && (tr.seenMoving || a.trueHeading != null || tr.nose != null)) tr.nose = hd;
      const f = { t: tf, x, z, y, ground, gs: gsm, trk, hd, hdReal: a.trueHeading != null, vs: a.baroRate != null ? a.baroRate * FT / 60 : (a.geomRate != null ? a.geomRate * FT / 60 : null),
        trkRate: a.trackRate != null ? a.trackRate * DEG : null, roll: a.roll != null ? a.roll * DEG : null };
      if (f.trkRate == null && tr.last && trk != null && tr.last.trk != null && tf > tr.last.t) { const r = wrapPi(trk - tr.last.trk) / ((tf - tr.last.t) / 1000); if (Math.abs(r) < 10 * DEG) f.trkRate = r; }
      const before = tr.disp.valid ? tr.sample(tDisp, this._tmp) && { x: this._tmp.x, y: this._tmp.y, z: this._tmp.z, hdg: this._tmp.hdg } : null;
      if (tr.addFix(f)) {
        tr.lastFixT = tf;
        if (before) { // blend the change of estimate out over the next seconds instead of jumping
          const s = tr.sample(tDisp, this._tmp);
          const dx = before.x - s.x, dy = before.y - s.y, dz = before.z - s.z;
          if (Math.hypot(dx, dz) < 600) { tr.corr[0] += dx; tr.corr[1] += dy; tr.corr[2] += dz; tr.corrH = wrapPi(tr.corrH + wrapPi(before.hdg - s.hdg)); }
          else { tr.corr = [0, 0, 0]; tr.corrH = 0; }
        }
        this.classify(tr, f, recvNow);
      }
      tr.lastRecv = recvNow;
    }
    this.version++;
  }
  setInfo(tr, a) {
    const I = tr.info;
    const changedType = I.icao !== a.icao;
    Object.assign(I, { flight: a.flight || I.flight || null, reg: a.reg || I.reg || null, icao: a.icao || I.icao || null, desc: a.desc || I.desc || null, ownOp: a.ownOp || I.ownOp || null,
      squawk: a.squawk, emergency: a.emergency, category: a.category || I.category, altBaro: a.altBaro, gsKt: a.gs, vsFpm: a.baroRate ?? a.geomRate, trackDeg: a.track, navAlt: a.navAlt,
      src: a.srcType || I.src, seen: a.seen, year: a.year || I.year });
    if (!tr.cs || tr.cs.callsign !== (I.flight || null)) tr.cs = parseCallsign(I.flight);
    if (changedType || !tr.type) {
      tr.type = typeInfo(I.icao, I.desc); tr.model = typeForIcao(I.icao);
    }
    const al = tr.cs && tr.cs.airline ? tr.cs.airline.icao : null;
    tr.livery = liveryForAirline(al);
  }

  // ---------------------------------------------------------- flight phase
  classify(tr, f, now) {
    const kt = (f.gs || 0) / KT, atSFO = inAirport(f.x, f.z);
    const prevPhase = tr.phase;
    if (f.ground) {
      if (tr.lastAirT && tr.lastAirT > tr.lastGroundT && atSFO && f.t - tr.lastAirT < 60000) tr.landedAt = f.t;
      tr.lastGroundT = f.t; if (atSFO) tr.groundSFO = true;
      if (!atSFO) { tr.phase = 'ground-other'; tr.runway = null; return; }
      const rws = runwayAt(f.x, f.z);
      const moving = kt > 1.5;
      if (!moving) { if (!tr.stillSince) tr.stillSince = f.t; } else tr.stillSince = 0;
      // gate occupancy
      if (tr.gate && moving && this.distToStand(tr, tr.gate, f) > 8) this.releaseGate(tr);
      if (!tr.gate && kt < 3) { const g = this.matchGate(tr, f); if (g) this.occupy(tr, g); }
      if (rws && kt > 30) {
        const landing = tr.landedAt && f.t - tr.landedAt < 150000;
        tr.runway = runwayByHeading(rws, f.trk ?? f.hd).name; tr.phase = landing ? 'landing' : 'takeoff';
      } else if (moving) {
        tr.phase = tr.pushback ? 'pushback' : 'taxi';
        tr.runway = rws ? runwayByHeading(rws, f.hd).name : (tr.phase === 'taxi' ? tr.runway && tr.landedAt ? tr.runway : null : null);
      } else {
        if (tr.gate) tr.phase = 'gate';
        else if (rws) { tr.phase = 'holding'; tr.runway = runwayByHeading(rws, f.hd).name; }
        else if (inPolys(this.taxiways, f.x, f.z)) { tr.phase = 'holding'; tr.runway = null; }
        else tr.phase = 'parked';
        if (!f.hdReal && !tr.seenMoving && !tr.headingGuessed && !tr.gate) { const h = this.guessGroundHeading(f, tr.phase); tr.headingGuessed = true; if (h != null) { tr.nose = h; f.hd = h; for (const q of tr.fixes) q.hd = h; } } // never seen moving, no heading reported
      }
      if (!tr.dirSFO && tr.phase !== 'landing') tr.dirSFO = tr.landedAt ? 'arr' : null;
    } else {
      if (tr.lastGroundT && tr.lastGroundT > tr.lastAirT && tr.groundSFO && f.t - tr.lastGroundT < 60000) { tr.liftoffAt = f.t; tr.dirSFO = 'dep'; }
      tr.lastAirT = f.t; if (tr.gate) this.releaseGate(tr);
      tr.pushback = false; tr.stillSince = 0;
      const agl = f.y - GROUND_Y;
      const fin = detectFinal(f.x, f.z, f.trk ?? f.hd, agl);
      tr.finalInfo = fin && (f.vs == null || f.vs < 2.5) && !(tr.dirSFO === 'dep' && f.t - tr.liftoffAt < 300000) ? fin : null;
      if (tr.finalInfo) { tr.dirSFO = 'arr'; tr.runway = tr.finalInfo.R.name; }
      this.routeDirection(tr);
      if (!tr.dirSFO) tr.dirSFO = this.guessDirection(tr, f);
      if (tr.finalInfo) tr.phase = 'final';
      else if (tr.dirSFO === 'arr') tr.phase = 'approach';
      else if (tr.dirSFO === 'dep') tr.phase = 'departure';
      else tr.phase = 'enroute';
      if (tr.phase === 'departure' && tr.liftoffAt && !tr.depRunway) tr.depRunway = tr.runway;
    }
    if (prevPhase !== tr.phase) tr.phaseSince = f.t;
  }
  routeDirection(tr) {
    const r = tr.route; if (!r || !r.codes || !r.plausible || tr.dirFromRoute) return;
    const c = r.codes; const i = c.indexOf('SFO'); tr.dirFromRoute = true;
    if (i < 0) tr.dirSFO = tr.dirSFO === 'arr' && tr.finalInfo ? 'arr' : 'other';
    else if (i === c.length - 1) tr.dirSFO = 'arr';
    else if (i === 0) tr.dirSFO = 'dep';
  }
  guessDirection(tr, f) {
    const d = Math.hypot(f.x, f.z), altFt = (f.y - GROUND_Y) / FT; if (d > 60000 || altFt > 14000) return null;
    const v = hdgVec(f.trk ?? f.hd); const toward = -(f.x * v[0] + f.z * v[1]) / Math.max(d, 1); // cos of angle between track and bearing to SFO
    const vsFpm = (f.vs ?? 0) / FT * 60;
    const miss = Math.abs(f.x * v[1] - f.z * v[0]); // closest approach of the current track line
    if (toward > 0.7 && miss < 9000 && vsFpm < -250 && altFt < 11000) return 'arr';
    if (toward < -0.5 && d < 14000 && vsFpm > 400 && altFt < 9000) return 'dep';
    return null;
  }
  setRoute(tr, route) { tr.route = route; tr.dirFromRoute = false; if (route && !tr.finalInfo && !tr.groundSFO) this.routeDirection(tr); }

  // ---------------------------------------------------------- gates
  distToStand(tr, g, f) { const p = tr.parkRep || tr.parkPos; return p ? Math.hypot(f.x - p[0], f.z - p[1]) : 0; }
  // heading of an aircraft first seen standing still with no heading reported: lined up on a runway (departure
  // direction from the nearer end), along the taxiway centreline facing the nearest runway, else ramp rules
  guessGroundHeading(f, phase) {
    const rws = runwayAt(f.x, f.z);
    if (rws) { let best = null, bd = 1e9; for (const R of rws) { const a = (f.x - R.start[0]) * R.dir[0] + (f.z - R.start[1]) * R.dir[1]; if (a < bd) { bd = a; best = R; } } return best.hdg; }
    if (this.centerlines && inPolys(this.taxiways, f.x, f.z)) {
      let seg = null, bd = 45;
      for (const p of this.centerlines) for (let i = 1; i < p.length; i++) {
        const a = p[i - 1], b = p[i]; const dx = b[0] - a[0], dz = b[1] - a[1]; const L2 = dx * dx + dz * dz; if (L2 < 1e-6) continue;
        const u = Math.max(0, Math.min(1, ((f.x - a[0]) * dx + (f.z - a[1]) * dz) / L2)); const d = Math.hypot(f.x - a[0] - dx * u, f.z - a[1] - dz * u);
        if (d < bd) { bd = d; seg = [dx, dz]; }
      }
      if (seg) {
        let h = vecHdg(seg[0], seg[1]); const v = hdgVec(h);
        let rb = null, rd = 1e9; for (const R of RWY) { const a = Math.max(0, Math.min(R.len, (f.x - R.start[0]) * R.dir[0] + (f.z - R.start[1]) * R.dir[1])); const px = R.start[0] + R.dir[0] * a, pz = R.start[1] + R.dir[1] * a; const d = Math.hypot(px - f.x, pz - f.z); if (d < rd) { rd = d; rb = [px - f.x, pz - f.z]; } }
        if (rb && v[0] * rb[0] + v[1] * rb[1] < 0) h += Math.PI;
        return wrapPi(h);
      }
    }
    return phase === 'parked' ? this.guessParkedHeading(f) : null;
  }
  // heading of an aircraft first seen standing still (no heading reported): nose-in at a nearby stand, else nose
  // towards the nearest building face along the airport grid axes, else unchanged
  guessParkedHeading(f) {
    const g = this.nearestGate(f, 60); if (g) return g.w.hdg;
    if (!this.buildingAt) return null;
    let best = null, bd = 90;
    for (const h of [27.83, 117.83, 207.83, 297.83]) {
      const v = hdgVec(h * DEG);
      for (let d = 6; d < bd; d += 3) if (this.buildingAt(f.x + v[0] * d, f.z + v[1] * d)) { bd = d; best = h * DEG; break; }
    }
    if (best != null) return best;
    // open ramp: along the airport grid, facing the terminal core (remote stands are laid out on the grid)
    const b = vecHdg(-950 - f.x, 250 - f.z) / DEG; let hb = 27.83, dd = 1e9;
    for (const h of [27.83, 117.83, 207.83, 297.83]) { const e = Math.abs(((b - h + 540) % 360) - 180); if (e < dd) { dd = e; hb = h; } }
    return hb * DEG;
  }
  nearestGate(f, maxD) { let best = null, bd = maxD; for (const g of this.gates) { const d = Math.hypot(f.x - g.w.x, f.z - g.w.z); if (d < bd) { bd = d; best = g; } } return best; }
  // score of a stationary report against a stand. Contact stands (surveyed layout): distance of the report from where
  // this aircraft's ADS-B antenna would be if its nose were at the stand's stop point, lateral error weighted more;
  // the aircraft must fit the stand's size class. Remote stands: distance to the stand point.
  gateScore(g, x, z, T) {
    if (g.bridge) {
      const L = T ? T.L : (g.wide ? 63 : 38);
      const ex = g.w.x - g.w.dx * ANT * L, ez = g.w.z - g.w.dz * ANT * L;
      const rx = x - ex, rz = z - ez;
      const along = -(rx * g.w.dx + rz * g.w.dz), lat = -rx * g.w.dz + rz * g.w.dx;
      const latMax = Math.min(18, 0.35 * g.maxSpan + 4);
      if (Math.abs(lat) > latMax || Math.abs(along) > 20) return null;
      return Math.abs(lat) + 0.35 * Math.abs(along);
    }
    const d = Math.hypot(x - g.w.x, z - g.w.z); return d < 40 ? d + 4 : null;
  }
  dot2(f, g) { const h = f.chordHdg ?? f.trk; if (h == null) return 0; const v = hdgVec(h); return v[0] * g.w.dx + v[1] * g.w.dz; }
  matchGate(tr, f) {
    if (inPolys(this.taxiways, f.x, f.z) || runwayAt(f.x, f.z)) return null;
    const T = tr.model && TYPES[tr.model.t] || null;
    let best = null, bd = 1e9;
    for (const g of this.gates) {
      if (!standFits(g, T)) continue;
      if (g.bridge && f.hdReal && Math.abs(wrapPi(f.hd - g.w.hdg)) > 35 * DEG) continue; // reports a heading that is not nose-in here
      const sc = this.gateScore(g, f.x, f.z, T); if (sc == null) continue;
      if (g.occupant && g.occupant !== tr.hex) { const o = this.tracks.get(g.occupant); if (o && !o.stale && o.gateScore != null && o.gateScore <= sc) continue; }
      if (this.blocked(g, tr)) continue;
      if (sc < bd) { bd = sc; best = g; }
    }
    if (best) tr.gateScore = bd;
    return best;
  }
  // a stand is blocked when an aircraft parked at a neighbouring stand is larger than that stand's class allows
  blocked(g, tr) {
    for (const o of this.gates) {
      if (o === g || !o.occupant || o.occupant === tr.hex || !o.oversize) continue;
      if (Math.hypot(o.w.x - g.w.x, o.w.z - g.w.z) < 0.5 * (o.maxSpan + g.maxSpan) + 8) return true;
    }
    return false;
  }
  occupy(tr, g) {
    if (g.occupant && g.occupant !== tr.hex) { const o = this.tracks.get(g.occupant); if (o) { o.gate = null; if (o.stale) this.tracks.delete(o.hex); else { const g2 = this.matchGate(o, o.last); if (g2 && g2 !== g) this.occupy(o, g2); } } }
    const f = tr.last; tr.parkRep = [f.x, f.z];
    const T = tr.model && TYPES[tr.model.t] || null;
    if (g.bridge) {
      // contact stand: the aircraft stands exactly on the stand's lead-in line with its nose at the stop point
      const L = T ? T.L : (g.wide ? 63 : 38);
      tr.parkPos = [g.w.x - g.w.dx * ANT * L, g.w.z - g.w.dz * ANT * L]; tr.parkHdg = g.w.hdg; tr.nose = g.w.hdg;
      g.oversize = !!(T && T.wing && (T.wing.span > g.maxSpan + 0.5));
    } else {
      tr.parkPos = [f.x, f.z];
      if (!f.hdReal) { tr.nose = g.w.hdg; f.hd = g.w.hdg; } // parked nose-in unless the aircraft reports its true heading
      tr.parkHdg = f.hd; g.oversize = false;
    }
    tr.gate = g; g.occupant = tr.hex; tr.snapBlend = 0; this.onGateChange && this.onGateChange(g, tr); this.saveParkedSoon();
  }
  releaseGate(tr) { const g = tr.gate; if (!g) return; if (g.occupant === tr.hex) { g.occupant = null; g.oversize = false; } tr.parkRep = null; tr.gate = null; tr.unsnap = true; tr.snapBlend = 0; this.onGateChange && this.onGateChange(g, null); this.saveParkedSoon(); }

  // ---------------------------------------------------------- per-frame update
  update(now, dt) {
    const tDisp = this.displayTime(now); const s = this._tmp;
    const removed = [];
    for (const tr of this.tracks.values()) {
      // staleness
      if (!tr.stale) {
        const age = now - tr.lastRecv, lf = tr.last;
        if (lf && !lf.ground && age > STALE_AIR_MS) { removed.push(tr); continue; }
        if (lf && lf.ground && age > STALE_GROUND_MS) {
          if (!inAirport(lf.x, lf.z)) { removed.push(tr); continue; }
          // transponder switched off on the ground: keep it where it stopped (at its gate if it was at one)
          if (!tr.gate && (lf.gs || 0) < 8 * KT) { const g = this.matchGate(tr, lf); if (g) this.occupy(tr, g); }
          tr.stale = true; tr.staleSince = now; tr.phase = tr.gate ? 'gate' : 'parked'; this.saveParkedSoon();
        }
      } else if (now - tr.lastRecv > PARK_KEEP_MS) { removed.push(tr); continue; }
      if (!tr.fixes.length) continue;
      const S = tr.sample(tDisp, s); if (!S) continue;
      const D = tr.disp;
      // decay corrections
      const k = Math.exp(-dt / 1.4);
      tr.corr[0] *= k; tr.corr[1] *= k; tr.corr[2] *= k; tr.corrH *= Math.exp(-dt / 1.0);
      let x = S.x + tr.corr[0], y = S.y + tr.corr[1], z = S.z + tr.corr[2], hdg = S.hdg + tr.corrH;
      const lf = tr.last;
      const grounded = S.ground || (lf.ground && tr.stale);
      if (grounded) y = GROUND_Y;
      // glide-path assist on final: the last ~1,500 ft follow a 3 degree path to the touchdown zone
      if (!grounded && tr.phase === 'final' && tr.finalInfo) {
        const R = tr.finalInfo.R; const a = (x - R.thr[0]) * R.dir[0] + (z - R.thr[1]) * R.dir[1];
        const yg = GROUND_Y + Math.max(0, (330 - a) * Math.tan(3 * DEG));
        const w = 1 - sstep(140, 480, y - GROUND_Y);
        y = y + (yg - y) * w;
      }
      // just after liftoff: climb smoothly from the runway
      if (!grounded && tr.liftoffAt && tDisp - tr.liftoffAt < 25000) y = Math.max(GROUND_Y, y);
      // parked at a gate: hold the parked position and heading (nose-in unless the aircraft reports its heading)
      if (tr.gate && grounded && tr.parkPos && (tr.phase === 'gate' || tr.stale || S.gs < 1.2)) {
        tr.snapBlend = Math.min(1, (tr.snapBlend || 0) + dt / 2.5); const b = sstep(0, 1, tr.snapBlend);
        x += (tr.parkPos[0] - x) * b; z += (tr.parkPos[1] - z) * b; hdg = lerpAng(hdg, tr.parkHdg ?? tr.gate.w.hdg, b);
      }
      // leaving a stand: blend from the snapped stand position to the reported track
      if (tr.unsnap) { tr.unsnap = false; if (D.valid) { tr.corr[0] += D.x - x; tr.corr[2] += D.z - z; tr.corrH = wrapPi(tr.corrH + wrapPi(D.hdg - hdg)); x = D.x; z = D.z; hdg = D.hdg; } }
      // attitude
      const gsm = S.gs || 0;
      let pitchT = 0, rollT = 0;
      if (!grounded) {
        const gam = Math.atan2(S.vs || 0, Math.max(gsm, 40));
        pitchT = gam + (gsm < 130 ? 4.5 : 2.5) * DEG;
        if (tr.phase === 'final' && y - GROUND_Y < 12) pitchT = Math.max(pitchT, 4 * DEG); // flare
        // bank from turn rate (heading change of the displayed path) or the reported roll angle
        if (D.valid) { const w = wrapPi(hdg - D.hdg) / Math.max(dt, 1e-3); tr.turn += (clamp(w, -0.2, 0.2) - tr.turn) * Math.min(1, dt / 1.5); }
        rollT = lf.roll != null && Math.abs(lf.roll) < 45 * DEG && (tDisp - lf.t) < 15000 ? lf.roll : Math.atan(gsm * tr.turn / GRAV);
        rollT = clamp(rollT, -32 * DEG, 32 * DEG);
      } else if (tr.phase === 'takeoff') {
        pitchT = sstep(125, 160, gsm / KT) * 8 * DEG; tr.turn = 0;
      } else tr.turn = 0;
      D.pitch += clamp(pitchT - D.pitch, -3 * DEG * dt, 3 * DEG * dt);
      D.roll += (rollT - D.roll) * Math.min(1, dt / 0.8);
      // configuration
      const agl = y - GROUND_Y;
      let gearT = 0, flapsT = 0, splT = 0;
      if (grounded) { gearT = 1; flapsT = tr.phase === 'landing' ? 1 : tr.phase === 'takeoff' || (tr.phase === 'taxi' && !tr.landedAt) || tr.phase === 'holding' ? 0.35 : 0; splT = tr.phase === 'landing' && gsm > 45 * KT ? 1 : 0; }
      else if (tr.dirSFO === 'arr' || tr.phase === 'final') { gearT = agl < 750 || (tr.phase === 'final' && agl < 1000) ? 1 : 0; flapsT = clamp((235 - gsm / KT) / 80, 0, 1) * (agl < 3000 ? 1 : 0); }
      else if (tr.dirSFO === 'dep' || tr.phase === 'departure') { gearT = agl < 90 && tDisp - tr.liftoffAt < 12000 ? 1 : 0; flapsT = gsm / KT < 205 && agl < 1200 ? 0.35 : 0; }
      D.gear += clamp(gearT - D.gear, -dt / 7, dt / 7); D.flaps += clamp(flapsT - D.flaps, -dt / 12, dt / 12); D.spoilers += clamp(splT - D.spoilers, -dt / 1.5, dt / 1.5);
      if (!D.valid) { D.gear = gearT; D.flaps = flapsT; D.pitch = pitchT; D.roll = rollT; }
      D.x = x; D.y = y; D.z = z; D.hdg = hdg; D.gs = gsm; D.vs = S.vs || 0; D.ground = grounded; D.extrap = S.extrap; D.valid = true;
    }
    for (const tr of removed) this.remove(tr);
  }
  remove(tr) { if (tr.gate) this.releaseGate(tr); this.tracks.delete(tr.hex); tr.removed = true; this.onRemove && this.onRemove(tr); }

  // ---------------------------------------------------------- persistence of parked aircraft
  saveParkedSoon() { if (!this.persist || this._saveT) return; this._saveT = setTimeout(() => { this._saveT = null; this.saveParked(); }, 3000); }
  saveParked() {
    const out = {};
    for (const tr of this.tracks.values()) {
      const lf = tr.last; if (!lf || !lf.ground || !inAirport(lf.x, lf.z)) continue;
      if (!(tr.gate || tr.phase === 'parked' || tr.stale)) continue;
      out[tr.hex] = { hex: tr.hex, info: { flight: tr.info.flight, reg: tr.info.reg, icao: tr.info.icao, desc: tr.info.desc, ownOp: tr.info.ownOp },
        gate: tr.gate ? tr.gate.name : null, x: tr.parkPos ? tr.parkPos[0] : lf.x, z: tr.parkPos ? tr.parkPos[1] : lf.z, rx: tr.parkRep ? tr.parkRep[0] : lf.x, rz: tr.parkRep ? tr.parkRep[1] : lf.z, hd: tr.parkHdg ?? lf.hd, t: tr.lastRecv, route: tr.route || null, landedAt: tr.landedAt || 0 };
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
      tr.addFix({ t: now - this.delay - 1000, x: r.x, z: r.z, y: GROUND_Y, ground: true, gs: 0, trk: r.hd, hd: r.hd, hdReal: true, vs: 0 });
      tr.lastFixT = tr.last.t; tr.nose = r.hd;
      const g = r.gate && this.gates.find(q => q.name === r.gate);
      if (g && !g.occupant) { tr.gate = g; g.occupant = tr.hex; tr.snapBlend = 1; tr.parkPos = [r.x, r.z]; tr.parkRep = [r.rx ?? r.x, r.rz ?? r.z]; tr.parkHdg = r.hd; }
      tr.phase = tr.gate ? 'gate' : 'parked';
      this.tracks.set(r.hex, tr);
    }
    if (this.onGateChange) for (const g of this.gates) if (g.occupant) this.onGateChange(g, this.tracks.get(g.occupant));
  }
  clearParked() { try { localStorage.removeItem(STORE_KEY); } catch (e) { } }
}

// ---------------------------------------------------------------- display text
export function phaseLabel(tr, now = Date.now()) {
  const rw = tr.runway; const g = tr.gate ? tr.gate.name : null;
  const ago = (ms) => { const m = Math.round(ms / 60000); return m < 1 ? 'just now' : m < 60 ? m + ' min ago' : Math.floor(m / 60) + ' h ' + (m % 60) + ' min ago'; };
  switch (tr.phase) {
    case 'final': { const d = -tr.finalInfo.a / NM; return d > 0.15 ? `Final ${tr.finalInfo.R.name} · ${d.toFixed(1)} nm` : `Landing ${tr.finalInfo.R.name}`; }
    case 'approach': return 'Arriving';
    case 'departure': return tr.depRunway ? `Departed ${tr.depRunway}` : 'Departing';
    case 'takeoff': return `Takeoff roll ${rw || ''}`.trim();
    case 'landing': return `Landed ${rw || ''}`.trim();
    case 'taxi': return tr.landedAt ? 'Taxiing in' : 'Taxiing';
    case 'pushback': return 'Pushback' + (tr.pushbackFrom ? ' from ' + tr.pushbackFrom : '');
    case 'holding': return rw ? `Holding · ${rw}` : 'Holding';
    case 'gate': return (tr.gate && !tr.gate.bridge ? 'Stand ' : 'Gate ') + g + (tr.stale ? ' · last signal ' + ago(now - tr.lastRecv) : '');
    case 'parked': return 'Parked' + (tr.stale ? ' · last signal ' + ago(now - tr.lastRecv) : '');
    case 'stopped': return 'Stopped';
    case 'ground-other': return 'On ground (other airport)';
    case 'enroute': return 'En route';
    default: return '';
  }
}
export function category(tr) {
  if (tr.phase === 'ground-other') return 'other';
  if (['gate', 'parked', 'taxi', 'pushback', 'holding', 'stopped', 'takeoff', 'landing'].includes(tr.phase)) return 'ground';
  if (tr.phase === 'final' || tr.phase === 'approach') return 'arr';
  if (tr.phase === 'departure') return 'dep';
  return 'other';
}
