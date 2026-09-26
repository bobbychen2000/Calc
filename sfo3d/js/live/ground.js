// Ground plausibility layer between the traffic engine and the renderer: aircraft on the ground are solid bodies.
// Reported positions of parked aircraft scatter by metres (and the transponder antenna is not the aircraft's reference
// point), so without this layer aircraft could end up inside each other, on grass or in a building.
//  - aircraft parked at a surveyed contact stand in the stand's own pose are authoritative (the layout is collision-free);
//    a parked aircraft drawn in its own reported pose (it reports a heading that differs from the survey) is checked,
//    and falls back to the stand pose if that pose would hit a building or a neighbour;
//  - other stationary aircraft get the nearest pose (<= 6 m away: never further than the report scatter, audit s.6.9)
//    where their gear stands on pavement, nothing of the airframe is inside a building and nothing overlaps;
//  - moving aircraft get a fading target offset away from an overlap. Offsets act on the TARGET the kinematic body in
//    traffic.js follows, so corrections are driven (bounded acceleration and steering), never slid or teleported.
// Pavement = the rendered airport mask (airport.js) UNION the OSM aprons and taxiway strips (data/sfo_taxigraph.js):
// the mask lacks the cargo, GA and remote ramps where aircraft really park (audit F6, s.4.9).
import { TYPES } from '../aircraft/types.js';
import { antOf } from './traffic.js';

const hv = (h) => [Math.sin(h), -Math.cos(h)];

// building occupancy grid (2 m) from the airport's building footprints
export function buildingGrid(airport, res = 2) {
  const x0 = -2600, z0 = -2300, x1 = 1800, z1 = 1800;
  const W = Math.ceil((x1 - x0) / res), H = Math.ceil((z1 - z0) / res);
  const cv = document.createElement('canvas'); cv.width = W; cv.height = H; const cx = cv.getContext('2d', { willReadFrequently: true });
  cx.fillStyle = '#fff';
  const ring = (r) => { r.forEach((p, i) => { const X = (p[0] - x0) / res, Z = (p[1] - z0) / res; i ? cx.lineTo(X, Z) : cx.moveTo(X, Z); }); cx.closePath(); };
  const poly = (rings) => { cx.beginPath(); for (const r of rings) ring(r); cx.fill('evenodd'); };
  for (const p of airport.terminalComplex || []) poly(p);
  for (const b of airport.boardingAreas || []) for (const p of b.polys) poly(p);
  for (const s of airport.structures || []) { if (s.kind === 'rail' || s.kind === 'hangar') continue; for (const p of s.polys) poly(p); } // aircraft may stand inside hangars
  const d = cx.getImageData(0, 0, W, H).data; const m = new Uint8Array(W * H);
  for (let i = 0; i < W * H; i++) m[i] = d[i * 4] > 127 ? 1 : 0;
  cv.width = cv.height = 1;
  return (x, z) => { const i = Math.floor((x - x0) / res), j = Math.floor((z - z0) / res); return i >= 0 && j >= 0 && i < W && j < H && m[j * W + i] === 1; };
}
// pavement test: rendered mask OR the OSM taxi net (aprons + taxiway strips); cached on a 1 m grid
export function pavedUnion(mask, net) {
  if (!net || !net.ok) return mask;
  const cache = new Map();
  return (x, z) => {
    if (mask && mask(x, z)) return true;
    const k = Math.round(x) * 8192 + Math.round(z); let v = cache.get(k);
    if (v === undefined) { v = net.paved(Math.round(x), Math.round(z)); if (cache.size > 400000) cache.clear(); cache.set(k, v); }
    return v;
  };
}

// planform samples of an aircraft in world (x,z): gear points (must be on pavement) and outline points (must be
// clear of buildings and of other aircraft)
export function samples(T, nose, h) {
  const f = hv(h), r = [-f[1], f[0]];
  const P = (along, side) => [nose[0] - f[0] * along + r[0] * side, nose[1] - f[1] * along + r[1] * side];
  const w = T.wing, span = w ? w.span / 2 : 16, le = w ? w.rootLE : T.L * 0.4, sw = Math.tan(((w && w.sweep) || 27) * Math.PI / 180);
  const tipLE = le + span * sw, tipC = w ? w.tipC : 1.5;
  const gear = [P(T.xNose ?? 3, 0), P(T.xMain, (T.track || 6) / 2), P(T.xMain, -(T.track || 6) / 2)];
  const hs = T.hstab ? T.hstab.span / 2 : 6, hx = T.hstab ? T.hstab.x + (T.hstab.rootC || 3) : T.L - 2;
  const outline = [P(0, 0), P(T.L, 0), P(tipLE + tipC / 2, span), P(tipLE + tipC / 2, -span), P(le + span * 0.5 * sw, span * 0.5), P(le + span * 0.5 * sw, -span * 0.5),
    P(hx, hs), P(hx, -hs), P(T.L * 0.25, 0), P(T.L * 0.5, 0), P(T.L * 0.75, 0), P(le, T.R), P(le, -T.R)];
  return { gear, outline, f, r };
}
// is point q inside the planform of aircraft A (nose, heading, type) with margin m
export function inside(A, q, m) {
  const T = A.T, f = A.f, r = A.r;
  const dx = q[0] - A.nose[0], dz = q[1] - A.nose[1];
  const x = -(dx * f[0] + dz * f[1]), y = dx * r[0] + dz * r[1];
  if (x > -m && x < T.L + m && Math.abs(y) < T.R + m) return true;
  const w = T.wing;
  if (w) {
    const ay = Math.abs(y), le = w.rootLE + ay * Math.tan((w.sweep || 27) * Math.PI / 180);
    const ch = w.rootC - (w.rootC - w.tipC) * Math.min(1, ay / (w.span / 2));
    if (ay < w.span / 2 + m && x > le - m && x < le + ch + m) return true;
  }
  if (T.hstab && x > T.hstab.x - m && x < T.L + m && Math.abs(y) < T.hstab.span / 2 + m) return true;
  return false;
}
export function bodyOf(T, x, z, h) { const f = hv(h); const k = antOf(T); return { T, nose: [x + f[0] * k, z + f[1] * k], h, f, r: [-f[1], f[0]] }; }
export function overlaps(A, B, m = 0) {
  if (Math.hypot(A.nose[0] - B.nose[0], A.nose[1] - B.nose[1]) > (A.T.L + B.T.L) * 0.5 + 45) return false;
  const Sa = A.S || (A.S = samples(A.T, A.nose, A.h)), Sb = B.S || (B.S = samples(B.T, B.nose, B.h));
  return Sa.outline.some(p => inside(B, p, m)) || Sb.outline.some(p => inside(A, p, m));
}

export class GroundPhysics {
  constructor({ paved, building, net = null }) { this.paved = pavedUnion(paved, net); this.building = building; this.frame = 0; this.stats = {}; }
  body(tr, pose) {
    const T = tr.model && TYPES[tr.model.t]; if (!T) return null;
    const D = pose || tr.disp; const B = bodyOf(T, D.x, D.z, D.hdg); B.tr = tr; return B;
  }
  valid(B, others, gear = true) {
    const S = samples(B.T, B.nose, B.h);
    if (gear && this.paved) for (const g of S.gear) if (!this.paved(g[0], g[1])) return false;
    for (const p of S.outline) if (this.building && this.building(p[0], p[1])) return false;
    for (const o of others) {
      if (Math.hypot(o.nose[0] - B.nose[0], o.nose[1] - B.nose[1]) > (o.T.L + B.T.L) * 0.5 + 45) continue;
      for (const p of S.outline) if (inside(o, p, 1.0)) return false;
      const So = samples(o.T, o.nose, o.h); for (const p of So.outline) if (inside(B, p, 1.0)) return false;
    }
    return true;
  }
  // run after traffic.update(): sets tr.physOff (target offsets) for the next frame; checks data-pose stand parking
  resolve(traffic, dt) {
    const fixed = [], free = [], moving = [], silent = []; let conflicts = 0;
    for (const tr of traffic.tracks.values()) {
      const D = tr.disp; if (!D.valid || !D.ground || tr.vehicle || tr.dropping) { tr.physOff = null; continue; }
      // (silent: transponder off (stale), or stopped off a stand with no position for a while (traffic.js tr.quiet))
      const sil = tr.stale || tr.quiet;
      if (tr.gate && tr.gate.bridge && tr.parkPos && (tr.m.phase === 'still' || tr.stale)) {
        // the pose it is drawn in: its lock (where it came to rest, the pose its bridge docked to), else the parked pose
        const S = traffic.shownPark ? traffic.shownPark(tr) : { x: tr.parkPos[0], z: tr.parkPos[1], hdg: tr.parkHdg };
        const B = this.body(tr, { x: S.x, z: S.z, hdg: S.hdg }); if (!B) continue;
        if (tr.parkMode === 'data' && !tr._poseChecked) { tr._poseChecked = true; const Bp = this.body(tr, { x: tr.parkPos[0], z: tr.parkPos[1], hdg: tr.parkHdg }); if (!this.valid(Bp, fixed, false)) { tr.forceStand = true; traffic.updatePark(tr); continue; } }
        // two aircraft at neighbouring stands must not touch: an own-pose (data) parking yields to the stand pose
        // ...and a stand pose SHORT of the stop point (the reports' median, up to 25 m short) yields to the stop point
        // (this aircraft or the neighbour it touches: static_geometry_round2.md #4)
        const hit = fixed.find(o => overlaps(o, B, 0.5));
        if (hit) {
          const short = (q) => q && q.gate && q.parkMode === 'stand' && !q.shortBlocked && q.parkAlong != null && q.parkAlong < (q.stopAlong ?? 0) - 1;
          if (tr.parkMode === 'data') { tr.forceStand = true; traffic.updatePark(tr); }
          else if (short(tr)) { tr.shortBlocked = true; traffic.updatePark(tr); traffic.counters.shortBlocked = (traffic.counters.shortBlocked || 0) + 1; }
          else if (short(hit.tr)) { hit.tr.shortBlocked = true; traffic.updatePark(hit.tr); traffic.counters.shortBlocked = (traffic.counters.shortBlocked || 0) + 1; }
          else conflicts++;
        }
        fixed.push(B); tr.physOff = null; if (sil) silent.push(B);
      } else { const B = this.body(tr); if (!B) continue; if ((D.gs || 0) < 0.3 && (tr.m.phase === 'still' || tr.stale)) { free.push(B); if (sil) silent.push(B); } else moving.push(B); }
    }
    // stationary aircraft off the surveyed stands: nearest valid pose (once per pose), within the report scatter (6 m),
    // widened to 15 m when nothing nearer is clear of buildings / neighbours (review round 1: DAL1053 and UAL1881 were
    // drawn inside a building when the 6 m search failed). A LOCKED body (at rest where it is drawn) keeps its pose while
    // that pose is valid; if it becomes invalid it is unlocked and moved to the nearest valid pose.
    const placed = fixed.slice();
    free.sort((a, b) => (a.tr.firstSeen || 0) - (b.tr.firstSeen || 0));
    let moved = 0, unresolved = 0;
    for (const B of free) {
      const tr = B.tr;
      if (tr.lock) {
        const L = tr.lock; const base = bodyOf(B.T, L.x, L.z, L.hdg); const key = 'L' + Math.round(L.x * 4) + ',' + Math.round(L.z * 4) + ',' + Math.round(L.hdg * 100);
        // (buildings and neighbours only: a gear point a few decimetres outside the traced pavement is not worth moving a
        // parked aircraft for; the pavement test applies when it is placed)
        if (!tr.physL || tr.physL.key !== key || this.frame % 30 === 0) tr.physL = { key, ok: this.valid(base, placed, false) };
        if (tr.physL.ok) { placed.push(base); continue; }
        tr.lock = null; traffic.counters.physUnlocks = (traffic.counters.physUnlocks || 0) + 1; tr.phys = null;
      }
      const P0 = tr.parkPos || tr.stillPos || [tr.disp.x, tr.disp.z]; const h = tr.parkPos ? tr.parkHdg : (tr.stillHdg ?? tr.disp.hdg);
      const key = Math.round(P0[0]) + ',' + Math.round(P0[1]) + ',' + Math.round((h || 0) * 20);
      const base = bodyOf(B.T, P0[0], P0[1], h);
      if (!tr.phys || tr.phys.key !== key || (this.frame % 30 === 0 && !tr.phys.ok)) {
        let off = [0, 0], ok = this.valid(base, placed);
        if (!ok) {
          search: for (let rad = 1; rad <= 15; rad += rad < 6 ? 1 : 1.5) {
            const n = Math.max(8, Math.round(rad * 3));
            for (let i = 0; i < n; i++) {
              const a = (i / n) * Math.PI * 2; const o = [Math.cos(a) * rad, Math.sin(a) * rad];
              const C = { ...base, nose: [base.nose[0] + o[0], base.nose[1] + o[1]] };
              if (this.valid(C, placed)) { off = o; ok = true; break search; }
            }
          }
        }
        tr.phys = { key, off, ok };
      }
      tr.physOff = tr.phys.off[0] || tr.phys.off[1] ? tr.phys.off : null;
      if (tr.physOff) moved++; if (!tr.phys.ok) unresolved++;
      placed.push({ ...base, nose: [base.nose[0] + tr.phys.off[0], base.nose[1] + tr.phys.off[1]] });
    }
    // moving aircraft: a fading target offset away from any displayed overlap. A silent aircraft that a live one drives
    // into is not there any more (the live one's positions are real): it fades out BEFORE the contact -- the live one's
    // newest report already lies on it (off a stand; at a surveyed stand, whose layout is collision-free, only an actual
    // overlap). Review round 1: stale ghosts overlapped by passing traffic; review round 2: removed with a pop, and
    // only after the overlap had been drawn (SWA3085 on a taxilane driven through by two aircraft)
    let ghosts = 0;
    for (const B of moving) {
      const tr = B.tr; const cur = tr.physOff ? tr.physOff.slice() : [0, 0]; let push = [0, 0];
      // (the evidence: the live aircraft's NEWEST report -- ~ where its drawn body will be a few seconds later -- already lies
      // on the silent one's planform. Not an extrapolation: in a queue the aircraft behind decelerates and stops short)
      const L = tr.last; const ahead = L && L.ground && (tr.disp.gs || 0) > 0.5 && L.hd != null ? (() => { const A = bodyOf(B.T, L.px ?? L.x, L.pz ?? L.z, L.hd); return A; })() : null;
      for (const S of silent) {
        if (S.tr.removed || S.tr.dropping) continue;
        const hit = overlaps(B, S, 0) || (!S.tr.gate && ahead && overlaps(ahead, S, 0.5));
        if (hit) { traffic.event && traffic.event(S.tr, traffic._lastRecv || 0, 'stale-replaced', { by: tr.hex, moving: true, quiet: S.tr.stale ? 0 : 1 }); if (traffic.fadeRemove) traffic.fadeRemove(S.tr, 'ghost'); else traffic.remove(S.tr); ghosts++; }
      }
      for (const o of placed) {
        if (o.tr && (o.tr.removed || o.tr.dropping)) continue;
        const d = Math.hypot(B.nose[0] - o.nose[0], B.nose[1] - o.nose[1]);
        if (d > (o.T.L + B.T.L) * 0.5 + 40) continue;
        const S = samples(B.T, B.nose, B.h); let hits = 0; for (const p of S.outline) if (inside(o, p, 1.5)) hits++;
        if (hits) { const cB = [B.nose[0] - B.f[0] * B.T.L * 0.45, B.nose[1] - B.f[1] * B.T.L * 0.45], cO = [o.nose[0] - o.f[0] * o.T.L * 0.45, o.nose[1] - o.f[1] * o.T.L * 0.45];
          const vx = cB[0] - cO[0], vz = cB[1] - cO[1], vl = Math.hypot(vx, vz) || 1; push[0] += vx / vl * hits; push[1] += vz / vl * hits; }
      }
      const decay = Math.exp(-dt / 3);
      cur[0] = cur[0] * decay + push[0] * dt * 2; cur[1] = cur[1] * decay + push[1] * dt * 2;
      const pl = Math.hypot(cur[0], cur[1]); if (pl > 10) { cur[0] *= 10 / pl; cur[1] *= 10 / pl; }
      tr.physOff = pl > 0.05 ? cur : null;
      placed.push(B);
    }
    this.frame++;
    this.stats = { fixed: fixed.length, free: free.length, moving: moving.length, moved, unresolved, standConflicts: conflicts, ghostsRemoved: ghosts };
  }
}
