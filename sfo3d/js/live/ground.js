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

// building occupancy grid (2 m) from the airport's building footprints; extra (optional): more footprints as polygons
// [[ring, hole...], ...] - the Blender building assets' measured footprints (data/buildings3d/integration.js physics,
// tools/blender/b3d_integrate.py: hangars and the elevated guideway / roadways left out, as here), unioned with the outlines
export function buildingGrid(airport, res = 2, extra = null) {
  const x0 = -2600, z0 = -2300, x1 = 1800, z1 = 1800;
  const W = Math.ceil((x1 - x0) / res), H = Math.ceil((z1 - z0) / res);
  const cv = document.createElement('canvas'); cv.width = W; cv.height = H; const cx = cv.getContext('2d', { willReadFrequently: true });
  cx.fillStyle = '#fff';
  const ring = (r) => { r.forEach((p, i) => { const X = (p[0] - x0) / res, Z = (p[1] - z0) / res; i ? cx.lineTo(X, Z) : cx.moveTo(X, Z); }); cx.closePath(); };
  const poly = (rings) => { cx.beginPath(); for (const r of rings) ring(r); cx.fill('evenodd'); };
  for (const p of airport.terminalComplex || []) poly(p);
  for (const b of airport.boardingAreas || []) for (const p of b.polys) poly(p);
  for (const s of airport.structures || []) { if (s.kind === 'rail' || s.kind === 'hangar') continue; for (const p of s.polys) poly(p); } // aircraft may stand inside hangars
  for (const p of (extra && extra.rings) || extra || []) if (Array.isArray(p) && p.length) poly(p);
  const d = cx.getImageData(0, 0, W, H).data; const m = new Uint8Array(W * H);
  for (let i = 0; i < W * H; i++) m[i] = d[i * 4] > 127 ? 1 : 0;
  cv.width = cv.height = 1;
  return (x, z) => { const i = Math.floor((x - x0) / res), j = Math.floor((z - z0) / res); return i >= 0 && j >= 0 && i < W && j < H && m[j * W + i] === 1; };
}
// jet bridges at rest as obstacles for the FUSELAGE of an aircraft parked off a stand: the footprints of the bridge solids
// (gates.js solids(g, b, 0): oriented boxes {c, u, hl, hw, lo, hi, round} with world heights) whose height band reaches
// below the top of an airliner fuselage (lo < 7 m above the ground, B777 crown ~6.3 m), on a 1 m grid. Review 4 Nov: UAL1180
// B77W was drawn inside the G8 bridge tunnel at rest for 18 min (bridge.hit.fus 1,097 frames) -- the outline check never
// saw it, it knew no bridges. Parked aircraft at a surveyed stand pose are not tested (the layout clears the rest poses)
export function bridgeGrid(boxes, groundY = 0, res = 1) {
  const B = boxes.filter(b => b && b.c && (b.lo - groundY) < 7);
  if (!B.length) return null;
  let x0 = 1e9, z0 = 1e9, x1 = -1e9, z1 = -1e9;
  for (const b of B) { const r = b.round || Math.hypot(b.hl, b.hw); x0 = Math.min(x0, b.c[0] - r); x1 = Math.max(x1, b.c[0] + r); z0 = Math.min(z0, b.c[1] - r); z1 = Math.max(z1, b.c[1] + r); }
  x0 = Math.floor(x0) - 1; z0 = Math.floor(z0) - 1; const W = Math.ceil((x1 - x0) / res) + 2, H = Math.ceil((z1 - z0) / res) + 2;
  const m = new Uint8Array(W * H);
  for (const b of B) {
    const r = b.round || Math.hypot(b.hl, b.hw); const i0 = Math.max(0, Math.floor((b.c[0] - r - x0) / res)), i1 = Math.min(W - 1, Math.ceil((b.c[0] + r - x0) / res));
    const j0 = Math.max(0, Math.floor((b.c[1] - r - z0) / res)), j1 = Math.min(H - 1, Math.ceil((b.c[1] + r - z0) / res));
    for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) {
      const dx = x0 + (i + 0.5) * res - b.c[0], dz = z0 + (j + 0.5) * res - b.c[1];
      if (b.round ? Math.hypot(dx, dz) < b.round : (Math.abs(dx * b.u[0] + dz * b.u[1]) < b.hl && Math.abs(-dx * b.u[1] + dz * b.u[0]) < b.hw)) m[j * W + i] = 1;
    }
  }
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
  // the fuselage itself: both sides (0.9 R) every <= 3 m from 1 m behind the nose to the tail cone, for the building and
  // bridge tests (13 outline points left 10-20 m of a 777's sides unsampled: review 4 Nov, UAL1180 drawn in the terminal)
  // (close-out round 3, realtime-11: and the centre line -- a 2.8-m bridge tunnel at rest can cross a narrow-body fuselage between
  // its two side rows (A21N at D8 L1's tunnel, 4 Nov 21:36Z, 21 acHit samples, not seen by the side rows))
  const fus = []; const n = Math.max(4, Math.ceil(T.L / 3)), R = (T.R || 2) * 0.9;
  for (let i = 0; i <= n; i++) { const a = 1 + (T.L - 2) * i / n; fus.push(P(a, R), P(a, -R), P(a, 0)); }
  return { gear, outline, fus, f, r };
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
  // (close-out round 3, static_closeout.md R4.1.5: this.mask = the rendered pavement mask alone; stationary aircraft are placed
  // with all gear on it where a pose within the report scatter allows, before the mask OR OSM-net union is accepted)
  constructor({ paved, building, net = null, bridges = null }) { this.mask = paved || null; this.paved = pavedUnion(paved, net); this.building = building; this.bridges = bridges; this.frame = 0; this.stats = {}; }
  body(tr, pose) {
    const T = tr.model && TYPES[tr.model.t]; if (!T) return null;
    const D = pose || tr.disp; const B = bodyOf(T, D.x, D.z, D.hdg); B.tr = tr; return B;
  }
  // nearest offset (rings of 1 m to 6 m, then 1.5 m) of the body's pose within rMax that is valid with the pavement test pv
  seek(base, placed, pv, rMax) {
    for (let rad = 1; rad <= rMax; rad += rad < 6 ? 1 : 1.5) {
      const n = Math.max(8, Math.round(rad * 3));
      for (let i = 0; i < n; i++) {
        const a = (i / n) * Math.PI * 2; const o = [Math.cos(a) * rad, Math.sin(a) * rad];
        if (this.valid({ ...base, nose: [base.nose[0] + o[0], base.nose[1] + o[1]] }, placed, true, pv)) return o;
      }
    }
    return null;
  }
  valid(B, others, gear = true, pv = this.paved) {
    const S = samples(B.T, B.nose, B.h);
    if (gear && pv) for (const g of S.gear) if (!pv(g[0], g[1])) return false;
    for (const p of S.outline) if (this.building && this.building(p[0], p[1])) return false;
    for (const p of S.fus) if ((this.building && this.building(p[0], p[1])) || (this.bridges && this.bridges(p[0], p[1]))) return false;
    if (this.bridges) for (const k of [0, 8, 9, 10]) { const p = S.outline[k]; if (this.bridges(p[0], p[1])) return false; }   // (nose, tail cone, centreline)
    for (const o of others) {
      if (Math.hypot(o.nose[0] - B.nose[0], o.nose[1] - B.nose[1]) > (o.T.L + B.T.L) * 0.5 + 45) continue;
      for (const p of S.outline) if (inside(o, p, 1.0)) return false;
      const So = samples(o.T, o.nose, o.h); for (const p of So.outline) if (inside(B, p, 1.0)) return false;
    }
    return true;
  }
  // run after traffic.update(): sets tr.physOff (target offsets) for the next frame; checks data-pose stand parking
  resolve(traffic, dt) {
    const fixed = [], free = [], moving = [], silent = [], waiting = []; let conflicts = 0;
    for (const tr of traffic.tracks.values()) {
      // (a body being removed that still waits for its jet bridge -- traffic.js fadeRemove: it fades once the bridge is <= 30 %
      // extended -- is no obstacle, but a live aircraft driving into it makes it fade now: round 3, the stale occupant of
      // G7 replaced ahead of UAL900 at 20:39:40Z was driven through for 35 s while its bridge retracted, overlap.gnd)
      const D = tr.disp; if (!D.valid || !D.ground || tr.vehicle || tr.dropping) { tr.physOff = null; if (tr.dropping && !tr.dropNow && !tr.fadeOut && !tr.removed && D.valid && D.ground && !tr.vehicle) { const W = this.body(tr); if (W) waiting.push(W); } continue; }
      // (silent: transponder off (stale), or stopped off a stand with no position for a while (traffic.js tr.quiet))
      const sil = tr.stale || tr.quiet;
      // (a body still driving in -- a silent docking, or the data already stopped at the stand while the drawn body is on its way,
      // more than 2 m from the stand pose and not locked -- is a MOVING aircraft here: a ghost
      // in its way is removed before the contact, and it is not checked at a pose it has not reached. Replay 4-5 Nov: EVA028
      // driving into A1 through the silent EVA018 still drawn there, 1,283 m2 for 35 s; overlap.gnd)
      const S0 = tr.gate && tr.gate.bridge && tr.parkPos && (tr.m.phase === 'still' || tr.stale) ? (traffic.shownPark ? traffic.shownPark(tr) : { x: tr.parkPos[0], z: tr.parkPos[1], hdg: tr.parkHdg }) : null;
      const driving = !!(S0 && !tr.lock && Math.hypot(D.x - S0.x, D.z - S0.z) > 2);   // (any body not yet at its stand pose)
      if (S0 && !driving) {
        // the pose it is drawn in: its lock (where it came to rest, the pose its bridge docked to), else the parked pose
        const S = S0;
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
      } else { const B = this.body(tr); if (!B) continue; if (!driving && (D.gs || 0) < 0.3 && (tr.m.phase === 'still' || tr.stale)) { free.push(B); if (sil) silent.push(B); } else moving.push(B); }
    }
    // (close-out round 3, realtime-3: a removed body still waiting for its bridge fades at once when it overlaps ANY aircraft drawn
    // on the ground -- one heard parked at its stand (fixed) or stopped beside it (free), not only a moving one: UAL1227 B789 at
    // G13, replaced when UAL29D was heard parked there, was drawn on top of it for 30 s while its bridge retracted, 904 m2;
    // ANA108 under ANZ7 at G10, 482 m2 -- 506 of the 948 overlap.gnd frames of the 4-5 Nov replay)
    for (const S of waiting) { if (S.tr.dropNow || S.tr.removed) continue;
      for (const B of fixed.concat(free)) { if (B.tr === S.tr || B.tr.dropping) continue; if (overlaps(B, S, 0)) { S.tr.dropNow = true; if (traffic.counters) traffic.counters.dropWaitFixed = (traffic.counters.dropWaitFixed || 0) + 1; break; } } }
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
        // (close-out round 3, static R4.1.5: a NEW lock pose with a gear point off the rendered mask -- N199TH GLF5, 0.15 m over
        // the apron edge on the fence line for 335,068 frames -- is unlocked once (at most twice per aircraft) when a pose
        // within 3 m has all gear on the mask; the placement below then moves it there)
        const newKey = !tr.physL || tr.physL.key !== key;
        if (newKey || this.frame % 30 === 0) tr.physL = { key, ok: this.valid(base, placed, false) };
        if (tr.physL.ok && newKey && this.mask && this.mask !== this.paved && (tr.maskUnlocks || 0) < 2 && !this.valid(base, placed, true, this.mask)
          && this.seek(base, placed, this.mask, 3)) { tr.physL.ok = false; tr.maskUnlocks = (tr.maskUnlocks || 0) + 1; traffic.counters.physMaskUnlocks = (traffic.counters.physMaskUnlocks || 0) + 1; }
        if (tr.physL.ok) { placed.push(base); continue; }
        tr.lock = null; traffic.counters.physUnlocks = (traffic.counters.physUnlocks || 0) + 1; tr.phys = null;
      }
      const P0 = tr.parkPos || tr.stillPos || [tr.disp.x, tr.disp.z]; const h = tr.parkPos ? tr.parkHdg : (tr.stillHdg ?? tr.disp.hdg);
      const key = Math.round(P0[0]) + ',' + Math.round(P0[1]) + ',' + Math.round((h || 0) * 20);
      const base = bodyOf(B.T, P0[0], P0[1], h);
      if (!tr.phys || tr.phys.key !== key || (this.frame % 30 === 0 && !tr.phys.ok)) {
        // (close-out round 3, static R4.1.5: all gear on the rendered mask first -- where it is, else within the 6 m scatter --
        // then the mask OR OSM-net union where it is, else within 15 m)
        const mk = !!(this.mask && this.mask !== this.paved);
        let o = mk && this.valid(base, placed, true, this.mask) ? [0, 0] : null;
        if (!o && mk) o = this.seek(base, placed, this.mask, 6);
        if (!o && this.valid(base, placed)) o = [0, 0];
        if (!o) o = this.seek(base, placed, this.paved, 15);
        tr.phys = { key, off: o || [0, 0], ok: !!o };
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
      for (const S of waiting) {
        if (S.tr.dropNow || S.tr.removed || S.tr === tr) continue;
        if (overlaps(B, S, 0) || (ahead && overlaps(ahead, S, 0.5))) { S.tr.dropNow = true; ghosts++; if (traffic.counters) traffic.counters.dropWaitCut = (traffic.counters.dropWaitCut || 0) + 1; }
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
