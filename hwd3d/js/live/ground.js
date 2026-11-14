// Forked from sfo3d/js/live/ground.js @ a967f9b. Kept: the ground plausibility layer between the traffic engine and the
// renderer - aircraft on the ground are solid planforms; stationary aircraft get the nearest pose (seek: rings of growing
// radius) where every wheel stands on pavement, nothing of the airframe is inside a building and nothing overlaps; moving
// aircraft get a fading offset away from an overlap that acts on the TARGET the kinematic body follows (driven, never slid);
// samples / inside / overlaps / valid / seek / place / resolve; firstSeen order for placing stationary aircraft.
// Changed: planforms from the GA dimension records (js/aircraft/ga_dims.js: wing, h-stab, fuselage half-width, tricycle /
// tail-wheel / skid gear, helicopter rotor disc) around the main-gear origin (fork map 2.9 local frame), headings in
// degrees; pavement and buildings from the site model (js/world/site.js paved / building, Node-pure rasters - no canvas)
// united with the NAIP-seen airside asphalt of js/aircraft/pave_naip.js (naipPaved);
// clearances for GA: a parked pair keeps PARK_GAP_M (1.0 m, the spot capacity gap of data/hwd_airport.json, observed use at
// HWD) and other stationary pairs OTHER_GAP_M (3 m, AC 150/5300-13B 10 ft ~ 3 m wingtip clearance at tie-downs, Fig E-2
// [inf as a rule here]); hangared aircraft are not solid. Dropped: jet bridges (restBridgeField, bridgeGrid, liveBridges),
// stands and their ICAO Annex 14 clearances, the canvas building grid, ghost replacement at stands.
//
//   new GroundPhysics({ site, net, parking })
//   .resolve(traffic, dt)       sets tr.physOff ([dx, dz] m on the target) / tr.physPose for stationary bodies
//   .stats                      { fixed, free, moving, moved, unresolved, overlapsMoving }
//   samples(dims, x, z, hdg) / inside(B, q, m) / overlaps(A, B, m) / bodyOf(dims, x, z, hdg)   (also used by tools/traffic)
import { PAVE_NAIP } from '../aircraft/pave_naip.js';
const D2R = Math.PI / 180;
const hv = (h) => [Math.sin(h * D2R), -Math.cos(h * D2R)];
// airside asphalt seen on NAIP 2024 but not in the OSM pavement of the site model (tools/traffic/build_pave_mask.py: grey
// test, inside the aerodrome, outside car parks / buildings / fences, connected to and within 30 m of OSM pavement [inf]).
// Decoded once into a 1-m bit raster (110,619 m2 added to 493,718 m2 of OSM pavement in the current build).
let NAIPM = null;
export function naipPaved(x, z) {
  const P = PAVE_NAIP; if (!P) return false;
  if (!NAIPM) { NAIPM = new Uint8Array(P.nx * P.nz); P.rows.forEach((r, j) => { for (let k = 0; k < r.length; k += 2) NAIPM.fill(1, j * P.nx + r[k], j * P.nx + r[k] + r[k + 1]); }); }
  const i = Math.floor((x - P.x0) / P.res), j = Math.floor((z - P.z0) / P.res);
  return i >= 0 && j >= 0 && i < P.nx && j < P.nz && NAIPM[j * P.nx + i] === 1;
}
// the pavement the physics uses: the site model's (P2) united with the NAIP-seen airside asphalt
export const pavedWith = (site) => (x, z) => (site ? site.paved(x, z) : false) || naipPaved(x, z);
export const PHYS_RULES = { PARK_GAP_M: 1.0, OTHER_GAP_M: 3.0, MOVING_M: 1.5, SCATTER_M: 6, SEEK_MAX_M: 25, ROTOR_M: 0.0, LOCK_M: 3.0, PUSH_M: 6.0 };   // LOCK_M = traffic.js REST_LOCK_M (round 4)   // SEEK_MAX_M 15 -> 25 m (fix round 1: a GNSS pose 15-20 m off the runway end pavement stayed on the grass) [inf]

// planform sample points of an aircraft whose main-gear origin is at (x, z), nose heading hdg (deg). Local: a = metres
// ahead of the origin along the nose, s = metres to the right.
export function samples(T, x, z, hdg) {
  const f = hv(hdg), r = [-f[1], f[0]];
  const P = (a, s) => [x + f[0] * a + r[0] * s, z + f[1] * a + r[1] * s];
  const nose = T.xMain, tail = T.xMain - T.L;      // nose a = +xMain, tail a = xMain - L
  let gear;
  if (T.gearKind === 'skid') { const hl = (T.skidLen || 2.6) / 2, ht = T.track / 2; gear = [P(hl, ht), P(hl, -ht), P(-hl, ht), P(-hl, -ht)]; }
  else gear = [P(0, T.track / 2), P(0, -T.track / 2), P(T.xMain - T.xNose, 0)];   // xNose: the third wheel behind the nose (nose or tail wheel)
  const out = [P(nose, 0), P(tail, 0), P(nose - 0.4 * T.L, T.R), P(nose - 0.4 * T.L, -T.R), P(nose - 0.15 * T.L, T.R * 0.8), P(nose - 0.15 * T.L, -T.R * 0.8)];
  const W = T.wing;
  if (W) {
    const hs = W.span / 2, le = nose - W.rootLE, sw = Math.tan((W.sweep || 0) * D2R);
    const tipLE = le - hs * sw;
    for (const sg of [1, -1]) { out.push(P(tipLE, sg * hs), P(tipLE - W.tipC, sg * hs), P(le - hs * 0.5 * sw, sg * hs * 0.5), P(le - hs * 0.5 * sw - (W.rootC + W.tipC) / 2, sg * hs * 0.5), P(le - W.rootC, sg * T.R)); }
  }
  if (T.hstab) { const hx = nose - T.hstab.x; for (const sg of [1, -1]) out.push(P(hx, sg * T.hstab.span / 2), P(hx - T.hstab.rootC, sg * T.hstab.span / 2)); }
  if (T.rotor) { const rr = T.rotor / 2; for (let k = 0; k < 12; k++) { const a = k / 12 * Math.PI * 2; out.push(P(Math.cos(a) * rr, Math.sin(a) * rr)); } }
  const fus = []; const n = Math.max(3, Math.ceil(T.L / 2));
  for (let i = 0; i <= n; i++) { const a = nose - 0.3 - (T.L - 0.6) * i / n; fus.push(P(a, T.R * 0.85), P(a, -T.R * 0.85), P(a, 0)); }
  return { gear, outline: out, fus, f, r };
}
export function bodyOf(T, x, z, hdg) { const f = hv(hdg); return { T, x, z, hdg, f, r: [-f[1], f[0]] }; }
// is q inside B's planform (margin m)? fuselage rectangle, wing trapezoid, h-stab rectangle, rotor disc
export function inside(B, q, m = 0) {
  const T = B.T, dx = q[0] - B.x, dz = q[1] - B.z;
  const a = dx * B.f[0] + dz * B.f[1], s = dx * B.r[0] + dz * B.r[1];
  const nose = T.xMain, tail = T.xMain - T.L;
  if (a < nose + m && a > tail - m && Math.abs(s) < T.R + m) return true;
  const W = T.wing;
  if (W) {
    const as = Math.abs(s); if (as < W.span / 2 + m) {
      const le = nose - W.rootLE - as * Math.tan((W.sweep || 0) * D2R);
      const ch = W.rootC - (W.rootC - W.tipC) * Math.min(1, as / (W.span / 2));
      if (a < le + m && a > le - ch - m) return true;
    }
  }
  if (T.hstab) { const hx = nose - T.hstab.x; if (a < hx + m && a > hx - T.hstab.rootC - m && Math.abs(s) < T.hstab.span / 2 + m) return true; }
  if (T.rotor && Math.hypot(a, s) < T.rotor / 2 + m) return true;
  return false;
}
export function overlaps(A, B, m = 0) {
  const ra = Math.max(A.T.L, A.T.span, A.T.rotor || 0), rb = Math.max(B.T.L, B.T.span, B.T.rotor || 0);
  if (Math.hypot(A.x - B.x, A.z - B.z) > (ra + rb) * 0.75 + m) return false;
  const Sa = A.S || (A.S = samples(A.T, A.x, A.z, A.hdg)), Sb = B.S || (B.S = samples(B.T, B.x, B.z, B.hdg));
  return Sa.outline.some(p => inside(B, p, m)) || Sb.outline.some(p => inside(A, p, m)) || Sa.fus.some(p => inside(B, p, m)) || Sb.fus.some(p => inside(A, p, m));
}

export class GroundPhysics {
  constructor({ site, net = null, parking = null } = {}) {
    this.site = site; this.net = net; this.parking = parking; this.frame = 0; this.stats = {};
    this.paved = pavedWith(site);
    this.building = (x, z) => (site && site.building(x, z)) || false;
  }
  gearOk(B) { const S = B.S || (B.S = samples(B.T, B.x, B.z, B.hdg)); return S.gear.every(g => this.paved(g[0], g[1])); }
  inBuilding(B) { const S = B.S || (B.S = samples(B.T, B.x, B.z, B.hdg)); return S.fus.some(p => this.building(p[0], p[1])) || S.outline.some(p => this.building(p[0], p[1])); }
  valid(B, others, gapOf) {
    const S = B.S || (B.S = samples(B.T, B.x, B.z, B.hdg));
    // helicopters may stand on unpaved ground (skids; Phase 1 not_placed: an unmapped paved helicopter area with four pads
    // south of 10R/28L): only fixed-wing gear must be on pavement
    if (B.T.cls !== 'heli') for (const g of S.gear) if (!this.paved(g[0], g[1])) return false;
    // (a door spot of data/hwd_airport.json: "its nose may enter that hangar" - the building test is waived there)
    const door = B.tr && B.tr.park && B.tr.park.spotId && this.parking && (this.parking.byId.get(B.tr.park.spotId) || {}).door;
    if (!door) {
      for (const p of S.fus) if (this.building(p[0], p[1])) return false;
      for (const p of S.outline) if (this.building(p[0], p[1])) return false;
    }
    for (const o of others) { const m = gapOf(B, o); if (overlaps(B, o, m)) return false; }
    return true;
  }
  // nearest valid offset on rings of growing radius (sfo3d seek), hdg kept
  seek(base, others, gapOf, rMax) {
    if (this.valid(base, others, gapOf)) return [0, 0];
    for (let rad = 0.5; rad <= rMax; rad += rad < 4 ? 0.5 : 1) {
      const n = Math.max(8, Math.round(rad * 4));
      for (let i = 0; i < n; i++) {
        const a = (i / n) * Math.PI * 2, o = [Math.cos(a) * rad, Math.sin(a) * rad];
        const B = bodyOf(base.T, base.x + o[0], base.z + o[1], base.hdg);
        if (this.valid(B, others, gapOf)) return o;
      }
    }
    return null;
  }
  resolve(traffic, dt) {
    const fixed = [], free = [], moving = [];
    for (const tr of traffic.tracks.values()) {
      const D = tr.disp; tr._B = null;
      if (!D.valid || !D.ground || tr.vehicle || !tr.dims || tr.hidden || tr.inHangarRest || (tr.park && tr.park.inside)) { tr.physOff = null; continue; }
      if (!(D.alpha > 0.01) && !tr.stale) { tr.physOff = null; continue; }
      // a helicopter standing on its skids between two still runs (GNSS noise of a few m) is placed like a parked one, from
      // its target pose (fix round 1: rotor discs through hangar walls) [inf]
      if (!tr.restPose && tr.dims.cls === 'heli' && (D.gs || 0) < 0.5 && tr._raw) tr._heliRest = { x: tr._raw[0], z: tr._raw[1], hdg: D.hdg }; else tr._heliRest = null;
      // (fix round 2) stationary = the TARGET rests (a rest pose), whatever the body's own speed: a body driving to its seek
      // offset used to count as 'moving', its offset decayed, the target swung back and the body shuttled 12 m to and fro on
      // the grass for a minute. The offset is kept while the target rests and decays from where it is once the target moves
      // (one continuous offset, hysteresis by the target state)
      const stationary = !!tr.restPose || tr._heliRest;
      if (stationary) free.push(tr); else moving.push(tr);
    }
    // every stationary pair keeps PARK_GAP_M (the tie-down rows are painted 12.15 m apart for ~11 m spans: a 3 m rule would
    // push parked neighbours off their tees); OTHER_GAP_M is reported by tools/traffic, not enforced here
    const gapOf = () => PHYS_RULES.PARK_GAP_M;
    // stationary: place in firstSeen order against those already placed (parked at a headed spot first: the layout is
    // the painted one)
    // (round 4, E6) a body the engine holds at rest (traffic.js ctlGround rest lock: tr.ctl.lock) is placed where it is DRAWN, first,
    // and its offset is the one that puts its target there (within the lock radius) - the physics no longer re-places a resting
    // aircraft (a new seek whenever the list of aircraft placed before it changed moved it by up to a few m: the hold twitch of case
    // S, a 0.2-m sideways step and a 0.16-m hop); the others are placed around it
    const locked = (tr) => !!(tr.ctl && tr.ctl.lock && tr.ctl.ground);
    free.sort((a, b) => (locked(b) ? 1 : 0) - (locked(a) ? 1 : 0) || ((b.park && b.park.spotId && b.park.pose && b.park.headed) ? 1 : 0) - ((a.park && a.park.spotId && a.park.pose && a.park.headed) ? 1 : 0) || (a.firstSeen || 0) - (b.firstSeen || 0));
    let moved = 0, unresolved = 0;
    const placed = [];
    for (const tr of free) {
      const P = tr.restPose || tr._heliRest;
      if (locked(tr)) {
        // (round 4 iteration 2, F3: a wheel pivot moves the body by up to its track, so the lock keeps an offset up to track + 1 m)
        const L = tr.ctl.lock, ox = L.x - P.x, oz = L.z - P.z, keep = Math.hypot(ox, oz) < Math.max(PHYS_RULES.LOCK_M || 3, (tr.dims.track || 0) + 1);
        // (round 4 iteration 2, F4) ONCE per lock: a body that came to rest with a wing over a building or overlapping an aircraft placed
        // before it is pushed clear - the nearest valid pose AHEAD along its nose (0.5-6 m: it rolls on a few metres, never sideways or
        // backwards), released from the lock and driven there by the engine, which locks it again on arrival (traffic.js ctlGround c.push);
        // REST LOCK had stopped every push (wings over T-hangar rows, a parked pair overlapping) [inf: 6 m, forward only]
        if (!L.chk) { L.chk = true; const B0 = bodyOf(tr.dims, L.x, L.z, tr.disp.hdg); B0.tr = tr;
          if (!this.valid(B0, placed, gapOf)) { const f = hv(tr.disp.hdg); let off = null;
            for (let d = 0.5; d <= PHYS_RULES.PUSH_M && !off; d += 0.5) { const Bq = bodyOf(tr.dims, L.x + f[0] * d, L.z + f[1] * d, tr.disp.hdg); Bq.tr = tr; if (this.valid(Bq, placed, gapOf)) off = [ox + f[0] * d, oz + f[1] * d]; }
            if (off) { const c = tr.ctl; c.lock = null; c.trail = { x: [c.x], z: [c.z], s: [0] }; c.s = 0; c.hw = 0; c.po = [0, 0]; c.push = true;
              const key = Math.round(P.x * 4) + ',' + Math.round(P.z * 4) + ',' + Math.round(P.hdg) + '|' + placed.map(b => b.tr.key).join(',');
              tr.phys = { key, off, ok: true }; tr.physOff = off; this.pushed = (this.pushed || 0) + 1;
              const B = bodyOf(tr.dims, P.x + off[0], P.z + off[1], P.hdg); B.tr = tr; placed.push(B); tr._B = B; continue; } } }
        tr.physOff = keep && (Math.abs(ox) + Math.abs(oz) > 1e-6) ? [ox, oz] : null; tr.phys = { key: 'lock', off: tr.physOff || [0, 0], ok: true };
        const B = bodyOf(tr.dims, L.x, L.z, tr.disp.hdg); B.tr = tr; placed.push(B); tr._B = B; continue;
      }
      const base = bodyOf(tr.dims, P.x, P.z, P.hdg); base.tr = tr;
      const key = Math.round(P.x * 4) + ',' + Math.round(P.z * 4) + ',' + Math.round(P.hdg) + '|' + placed.map(b => b.tr.key).join(',');
      if (!tr.phys || tr.phys.key !== key || (!tr.phys.ok && this.frame % 100 === 0)) {
        // (round 4, E6) the offset found before is kept while it is still valid - a new seek only when it no longer is
        const prevOff = tr.phys && tr.phys.ok && tr.phys.key !== 'lock' ? tr.phys.off : null, Bp = prevOff ? bodyOf(base.T, base.x + prevOff[0], base.z + prevOff[1], base.hdg) : null;
        if (Bp) Bp.tr = tr;
        let o = Bp && this.valid(Bp, placed, gapOf) ? prevOff : this.seek(base, placed, gapOf, PHYS_RULES.SCATTER_M);
        if (!o) o = this.seek(base, placed, gapOf, PHYS_RULES.SEEK_MAX_M);
        tr.phys = { key, off: o || [0, 0], ok: !!o };
      }
      if (tr.phys.off[0] || tr.phys.off[1]) moved++; if (!tr.phys.ok) unresolved++;
      tr.physOff = tr.phys.off[0] || tr.phys.off[1] ? tr.phys.off : null;
      const B = bodyOf(tr.dims, P.x + tr.phys.off[0], P.z + tr.phys.off[1], P.hdg); B.tr = tr; placed.push(B); tr._B = B;
    }
    // moving: a fading offset away from overlaps with stationary / other moving bodies (sfo3d), capped at 6 m
    let ov = 0;
    const movB = moving.map(tr => { const B = bodyOf(tr.dims, tr.disp.x, tr.disp.z, tr.disp.hdg); B.tr = tr; tr._B = B; return B; });
    for (const B of movB) {
      const tr = B.tr; const cur = tr.physOff ? tr.physOff.slice() : [0, 0]; const push = [0, 0];
      for (const o of placed.concat(movB)) {
        if (o === B) continue;
        if (!overlaps(B, o, PHYS_RULES.MOVING_M)) continue;
        // (fix round 2) a SILENT aircraft (stale: drawn at its last position, inferred) that a heard, moving aircraft drives
        // into is evidently not there any more: traffic.update fades it out [inf]
        // (only 'no_signal' ones: a silent aircraft PARKED at a spot stays - there the mover is the one off its line)
        if (o.tr && o.tr.stale && !o.tr.park && !(B.tr && B.tr.stale) && overlaps(B, o, 0)) { o.tr.staleOverrun = true; continue; }
        ov++; const vx = B.x - o.x, vz = B.z - o.z, l = Math.hypot(vx, vz) || 1; push[0] += vx / l; push[1] += vz / l;
      }
      // (round 4, E7: the offset fades with the distance driven - 25 m - and at least over 30 s, not over 3 s of time: a 0.3-1 m offset of
      // a body leaving its rest pose (the seek offset at the line-up point) faded under a slow take-off roll start and yawed the nose
      // 5 deg on the centreline, 299.2 -> 294.4 -> 299.7 deg) [inf]
      const decay = Math.exp(-Math.max(dt / 30, (tr.disp.gs || 0) * dt / 25)); cur[0] = cur[0] * decay + push[0] * dt * 1.5; cur[1] = cur[1] * decay + push[1] * dt * 1.5;
      const pl = Math.hypot(cur[0], cur[1]); if (pl > 6) { cur[0] *= 6 / pl; cur[1] *= 6 / pl; }
      tr.physOff = pl > 0.05 ? cur : null;
    }
    this.frame++;
    this.stats = { fixed: fixed.length, free: free.length, moving: moving.length, moved, unresolved, overlapsMoving: ov };
  }
}
