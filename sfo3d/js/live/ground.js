// Ground plausibility layer between the ADS-B traffic engine and the renderer: aircraft on the ground are solid
// bodies. Reported positions of parked aircraft can be off by several metres (and the transponder antenna is not the
// aircraft's reference point), so without this layer aircraft can end up inside each other, on grass or in a building.
//  - aircraft snapped to a surveyed contact stand are authoritative (the stand layout is collision-free);
//  - other stationary aircraft are moved to the nearest pose where their gear stands on pavement, nothing of the
//    airframe is inside a building and the airframe does not overlap any other aircraft;
//  - moving aircraft are nudged apart if their displayed positions overlap (positions come from real reports, so this
//    only removes interpolation artefacts), with the nudge fading out.
import { GROUND_Y } from '../geo.js';
import { TYPES } from '../aircraft/types.js';
import { ANT } from './traffic.js';

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

// planform samples of an aircraft in world (x,z): gear points (must be on pavement) and outline points (must be
// clear of buildings and of other aircraft)
function samples(T, nose, h) {
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
function inside(A, q, m) {
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

export class GroundPhysics {
  constructor({ paved, building }) { this.paved = paved; this.building = building; this.frame = 0; }
  // pose of a track as displayed: nose point and heading
  body(tr) {
    const D = tr.disp, T = tr.model && TYPES[tr.model.t]; if (!T) return null;
    const f = hv(D.hdg); const k = ANT * T.L;
    return { tr, T, nose: [D.x + f[0] * k, D.z + f[1] * k], h: D.hdg, f, r: [-f[1], f[0]] };
  }
  valid(B, others) {
    const S = samples(B.T, B.nose, B.h);
    for (const g of S.gear) if (this.paved && !this.paved(g[0], g[1])) return false;
    for (const p of S.outline) if (this.building && this.building(p[0], p[1])) return false;
    for (const o of others) {
      if (Math.hypot(o.nose[0] - B.nose[0], o.nose[1] - B.nose[1]) > (o.T.L + B.T.L) * 0.5 + 45) continue;
      for (const p of S.outline) if (inside(o, p, 1.5)) return false;
      const So = samples(o.T, o.nose, o.h); for (const p of So.outline) if (inside(B, p, 1.5)) return false;
    }
    return true;
  }
  // run after traffic.update(): adjusts tr.disp of ground aircraft in place
  resolve(traffic, dt) {
    const fixed = [], free = [], moving = [];
    for (const tr of traffic.tracks.values()) {
      const D = tr.disp; if (!D.valid || !D.ground) { tr.phys = null; continue; }
      const B = this.body(tr); if (!B) continue;
      if (tr.gate && tr.gate.bridge) { fixed.push(B); tr.phys = null; }
      else if ((D.gs || 0) < 0.8 && (tr.phase === 'parked' || tr.phase === 'gate' || tr.stale)) free.push(B);
      else moving.push(B);
    }
    // stationary aircraft off the surveyed stands: find (once) the nearest valid pose, keep it while stationary
    const placed = fixed.slice();
    free.sort((a, b) => (a.tr.firstSeen || 0) - (b.tr.firstSeen || 0));
    for (const B of free) {
      const tr = B.tr; const key = Math.round(tr.disp.x) + ',' + Math.round(tr.disp.z) + ',' + Math.round(tr.disp.hdg * 20);
      if (!tr.phys || tr.phys.key !== key || (this.frame % 30 === 0 && !tr.phys.ok)) {
        let off = [0, 0], ok = this.valid(B, placed);
        if (!ok) {
          search: for (let rad = 2; rad <= 36; rad += 2) {
            const n = Math.max(8, Math.round(rad * 1.6));
            for (let i = 0; i < n; i++) {
              const a = (i / n) * Math.PI * 2; const o = [Math.cos(a) * rad, Math.sin(a) * rad];
              const C = { ...B, nose: [B.nose[0] + o[0], B.nose[1] + o[1]] };
              if (this.valid(C, placed)) { off = o; ok = true; break search; }
            }
          }
        }
        tr.phys = { key, off, ok, cur: tr.phys ? tr.phys.cur : [0, 0] };
      }
      const P = tr.phys; const k = Math.min(1, dt / 1.2);
      P.cur[0] += (P.off[0] - P.cur[0]) * k; P.cur[1] += (P.off[1] - P.cur[1]) * k;
      tr.disp.x += P.cur[0]; tr.disp.z += P.cur[1];
      placed.push({ ...B, nose: [B.nose[0] + P.cur[0], B.nose[1] + P.cur[1]] });
    }
    // moving aircraft: separate displayed overlaps (fading nudge)
    for (const B of moving) {
      const tr = B.tr; if (!tr.phys || tr.phys.key !== 'mv') tr.phys = { key: 'mv', cur: tr.phys ? tr.phys.cur : [0, 0] };
      const P = tr.phys; let push = [0, 0];
      for (const o of placed) {
        const dx = B.nose[0] - o.nose[0], dz = B.nose[1] - o.nose[1]; const d = Math.hypot(dx, dz);
        if (d > (o.T.L + B.T.L) * 0.5 + 40) continue;
        const S = samples(B.T, B.nose, B.h); let hits = 0; for (const p of S.outline) if (inside(o, p, 1.0)) hits++;
        if (hits) { const cB = [B.nose[0] - B.f[0] * B.T.L * 0.45, B.nose[1] - B.f[1] * B.T.L * 0.45], cO = [o.nose[0] - o.f[0] * o.T.L * 0.45, o.nose[1] - o.f[1] * o.T.L * 0.45];
          const vx = cB[0] - cO[0], vz = cB[1] - cO[1], vl = Math.hypot(vx, vz) || 1; push[0] += vx / vl * hits * 0.5; push[1] += vz / vl * hits * 0.5; }
      }
      const decay = Math.exp(-dt / 4);
      P.cur[0] = P.cur[0] * decay + push[0] * dt * 2; P.cur[1] = P.cur[1] * decay + push[1] * dt * 2;
      const pl = Math.hypot(P.cur[0], P.cur[1]); if (pl > 12) { P.cur[0] *= 12 / pl; P.cur[1] *= 12 / pl; }
      tr.disp.x += P.cur[0]; tr.disp.z += P.cur[1];
      placed.push({ ...B, nose: [B.nose[0] + P.cur[0], B.nose[1] + P.cur[1]] });
    }
    this.frame++;
    this.stats = { fixed: fixed.length, free: free.length, moving: moving.length, moved: free.filter(b => b.tr.phys && (b.tr.phys.off[0] || b.tr.phys.off[1])).length, unresolved: free.filter(b => b.tr.phys && !b.tr.phys.ok).length };
  }
}
