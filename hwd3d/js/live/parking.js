// Parking model of HWD (hwd3d Phase 2, P3; new file, fork map 2.8). Node-pure. Replaces sfo3d's stand matching
// (traffic.js matchGate / gateScore / occupy, data/sfo_stands.js), which does not apply: HWD has no contact stands.
//
// Spots: the 177 parking spots of data/hwd_airport.json (Phase 1; 113 obs / 64 inf): 80 painted tie-downs and 9 rule
// hangar-apron spots with a heading (their position = the main-gear / wing line, `ref_point` tee_junction / rule_point),
// ramp / hangar-apron / helipad spots at the median ADS-B position (`gnss_antenna`), at a NAIP blob centroid
// (`naip_blob_centroid`, about the planform centre) or at an OSM helipad centroid. Labels are the descriptive Phase 1
// zones ("Green Ramp row 1, tie-down 1"), never official numbers (D3). Sizes: `size.capacity_span_m` (the practical
// size with a 1.0 m wingtip gap, Phase 1 section 3) - an aircraft whose span exceeds it by more than SPAN_TOL does not fit.
//
//   new ParkingModel({ airport, taxigraph, site })
//   .match(pose, dims, {heli, key}) -> { spot, d, ok, why } | null     pose = {x, z, hdg (deg | null), ant: [x, z]}
//   .occupy(key, spot) / .release(key) / .occupancy() -> Map(spotId -> key) / .spotOf(key)
//   .parkPose(spot, dims, pose) -> {x, z, hdg, src, rule}               the pose drawn at that spot
//   .hangarNear(x, z, r = HANGAR_R) -> {hangar, d, inside} | null        hangared state (signal ends at a hangar)
//   .spots                                                              [{id, kind, zone, src, x, z, hdg, ref, cap, ...}]
// Matching radius and size tolerance are design values [inf]: MATCH_R covers the NACp 10-11 position error of 74 % of the
// ground fixes and NACp 8-9 of 18 % (docs/PLAN.md section 3: EPU < 10 m / < 30 m at NACp 10 / 9, DO-260B, from memory
// [verify]) plus the antenna-to-reference offset of a GA single (1-3 m, Phase 1 [inf]).
import { pointInRing } from '../world/site.js';

export const PARK_RULES = {
  MATCH_R: 7.5,        // m: the spot's reference point within this of the aircraft's matching point [inf]
  MATCH_R_HELI: 10,    // m: helipads (polygon ~10 m) [inf]
  SPAN_TOL: 0.5,       // m: span may exceed capacity_span_m by this (rounding of the 1.0 m gap) [inf]
  HANGAR_R: 8,         // m: hangar outline within this = at the hangar (data/hwd_airport.json adsb_signal_edges_8m)
};
const P = PARK_RULES;
const D2R = Math.PI / 180;
const hv = (h) => [Math.sin(h * D2R), -Math.cos(h * D2R)];

function segDist(px, pz, a, b) { const dx = b[0] - a[0], dz = b[1] - a[1], L2 = dx * dx + dz * dz; let u = L2 ? ((px - a[0]) * dx + (pz - a[1]) * dz) / L2 : 0; u = Math.max(0, Math.min(1, u)); return Math.hypot(px - a[0] - u * dx, pz - a[1] - u * dz); }
function ringDist(x, z, r) { let d = 1e9; for (let i = 0; i < r.length; i++) d = Math.min(d, segDist(x, z, r[i], r[(i + 1) % r.length])); return d; }

export class ParkingModel {
  constructor({ airport, taxigraph = null, site = null } = {}) {
    this.site = site;
    const tg = new Map(((taxigraph && taxigraph.spots) || []).map(s => [s.id, s]));
    this.spots = ((airport && airport.parking) || []).map(s => ({
      id: s.id, kind: s.kind, zone: s.zone || null, src: s.src, x: s.x, z: s.z, hdg: s.heading ?? null, hdgSrc: s.heading_src || null,
      ref: s.ref_point || 'gnss_antenna', cap: s.size && s.size.capacity_span_m != null ? s.size.capacity_span_m : null,
      maxRotor: s.size && s.size.max_rotor_m != null ? s.size.max_rotor_m : null, apron: s.apron || null, door: !!s.door_spot,
      node: tg.has(s.id) ? tg.get(s.id).node : null,
    }));
    this.byId = new Map(this.spots.map(s => [s.id, s]));
    this.grid = new Map(); const C = 25;
    for (const s of this.spots) { const k = Math.floor(s.x / C) + ',' + Math.floor(s.z / C); if (!this.grid.has(k)) this.grid.set(k, []); this.grid.get(k).push(s); }
    this.C = C;
    this.hangars = ((airport && airport.hangars) || []).map(h => { let x0 = 1e9, z0 = 1e9, x1 = -1e9, z1 = -1e9; for (const p of h.ring) { x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0]); z0 = Math.min(z0, p[1]); z1 = Math.max(z1, p[1]); }
      return { id: h.id, name: h.name, letter: h.letter || null, kind: h.kind, ring: h.ring, bb: [x0, z0, x1, z1] }; });
    this.occ = new Map(); this.of = new Map();
    this.stats = { spots: this.spots.length, withHeading: this.spots.filter(s => s.hdg != null).length };
  }
  near(x, z, r) { const C = this.C, out = []; const i0 = Math.floor((x - r) / C), i1 = Math.floor((x + r) / C), j0 = Math.floor((z - r) / C), j1 = Math.floor((z + r) / C);
    for (let i = i0; i <= i1; i++) for (let j = j0; j <= j1; j++) { const L = this.grid.get(i + ',' + j); if (L) for (const s of L) if (Math.hypot(s.x - x, s.z - z) <= r) out.push(s); } return out; }
  // the aircraft point that a spot's reference stands for: main gear (tee / rule point), antenna, planform centre
  refPoint(spot, pose, dims) {
    if (spot.ref === 'gnss_antenna' || spot.ref === 'helipad_polygon_centroid') return pose.ant || [pose.x, pose.z];
    if (spot.ref === 'naip_blob_centroid' || spot.ref === 'naip_by_eye_aircraft_centre') {
      if (pose.hdg == null || !dims) return [pose.x, pose.z];
      const f = hv(pose.hdg), c = dims.xMain - dims.L / 2;   // planform centre = mid-length, xMain behind the nose
      return [pose.x + f[0] * c, pose.z + f[1] * c];
    }
    return [pose.x, pose.z];   // tee_junction / rule_point: main-gear line
  }
  match(pose, dims, { heli = false, key = null } = {}) {
    const R = heli ? P.MATCH_R_HELI : P.MATCH_R;
    let best = null;
    for (const s of this.near(pose.x, pose.z, R + 12)) {
      const occ = this.occ.get(s.id); if (occ && occ !== key) continue;
      if (s.kind === 'helipad' && !heli) continue;              // fixed-wing aircraft do not park on helipads
      const q = this.refPoint(s, pose, dims); const d = Math.hypot(q[0] - s.x, q[1] - s.z);
      if (d > R) continue;
      const span = dims ? (heli ? dims.rotor || dims.span : dims.span) : null;
      let fit = true, why = null;
      if (!heli && s.cap != null && span != null && span > s.cap + P.SPAN_TOL) { fit = false; why = `span ${span.toFixed(1)} m > spot capacity ${s.cap.toFixed(1)} m`; }
      if (heli && s.kind !== 'helipad' && s.cap != null && span > s.cap + 3) { fit = false; why = 'rotor larger than the spot'; }
      // heading agreement where both are known: tie-downs are entered nose first or pushed back, so either direction
      let dh = 0; if (s.hdg != null && pose.hdg != null) { const a = Math.abs(((pose.hdg - s.hdg) % 360 + 540) % 360 - 180); dh = Math.min(a, 180 - a); }
      // too big for the spot's equal-share capacity (sized as if every neighbour were taken): still this spot when no
      // occupied spot lies within the aircraft's span of it - the physics keeps it clear of the others [inf]
      if (!fit && span != null) { let busy = false; for (const o of this.near(s.x, s.z, span + 2)) { if (o === s) continue; const k = this.occ.get(o.id); if (k && k !== key) { busy = true; break; } }
        if (!busy) { fit = true; why = (why || '') + ' (neighbours free: matched, oversize)'; } }
      const score = d + dh / 15 + (fit ? 0 : 50) + (s.kind === 'helipad' && heli ? -2 : 0);
      if (!best || score < best.score) best = { spot: s, d, ok: fit, why, score };
    }
    return best;
  }
  occupy(key, spot) { if (!spot) return; const prev = this.of.get(key); if (prev && prev !== spot.id) this.occ.delete(prev); this.occ.set(spot.id, key); this.of.set(key, spot.id); }
  release(key) { const s = this.of.get(key); if (s && this.occ.get(s) === key) this.occ.delete(s); this.of.delete(key); }
  occupancy() { return this.occ; }
  spotOf(key) { const s = this.of.get(key); return s ? this.byId.get(s) : null; }
  // pose drawn for an aircraft parked at a spot: a headed spot (tie-down tee / rule point) gives position (main-gear line)
  // and heading, keeping the aircraft's own direction if it stands nose-out; otherwise the aircraft's own median pose
  parkPose(spot, dims, pose) {
    if (spot && spot.hdg != null && (spot.ref === 'tee_junction' || spot.ref === 'rule_point')) {
      let h = spot.hdg;
      if (pose && pose.hdgReal && pose.hdg != null) { const a = Math.abs(((pose.hdg - h) % 360 + 540) % 360 - 180); if (a > 90) h = (h + 180) % 360; }
      return { x: spot.x, z: spot.z, hdg: h, src: spot.src, rule: `spot ${spot.id} pose (${spot.ref}; heading ${spot.hdgSrc || 'inf'})` };
    }
    return { x: pose.x, z: pose.z, hdg: pose.hdg, src: 'obs', rule: spot ? `own median pose at spot ${spot.id} (${spot.ref})` : 'own median pose (no spot)' };
  }
  hangarNear(x, z, r = P.HANGAR_R) {
    let best = null;
    for (const h of this.hangars) {
      if (x < h.bb[0] - r || x > h.bb[2] + r || z < h.bb[1] - r || z > h.bb[3] + r) continue;
      const inside = pointInRing(x, z, h.ring); const d = inside ? 0 : ringDist(x, z, h.ring);
      if (d <= r && (!best || d < best.d)) best = { hangar: h, d, inside };
    }
    return best;
  }
}
