// Jet-bridge bellows closure fitted to the fuselage (the bellows / door contact; drawn by js/live/gates.js bridgeGeo).
//
// Source: FAA AC 150/5220-21C §2.3.f(3) "Aircraft Closure (for PBBs). The aircraft end of the cab must be equipped with a
// folding bellows aircraft closure. The closure, when fitted to the aircraft fuselage, must surround both the open aircraft
// door and the doorway" (refs/cache/pbb/AC_150_5220-21C.pdf).
//
// Review 5 Nov 2026 (aircraft-v1): the bellows was drawn as a flat-fronted block, 3.1 m along the fuselage, its front at
// the cab stop T.dockHW (the skin at the door's own station). In the tapering nose the skin 1.55 m aft of door 1 is
// 0.17-0.25 m wider on every widebody (it cut into the skin) and 0.2-0.4 m narrower 1.55 m ahead of it (a gap), and on
// every type the skin curves away above the max breadth (the 3.0 m block stood above a narrow body's crown).
// Now every fibre of the closure runs from the cab front (frame height BELLOWS.y0..y1, unchanged) to the skin: the front
// follows the rendered skin over the whole footprint (DOCK_FOOT, measured on the drawn mesh by tools/models/dock_foot.mjs),
// and the top curtain comes down from the cab frame onto the fuselage at `top`: the highest height where the closure still
// meets the skin within REACH of the flat front on every station of the footprint, but never below the door's clear
// opening + TOP_OVER (the closure surrounds the doorway), lower only at a station where the skin at that height lies more
// than TOP_EXT in from the flat front (the nose crown ahead of a narrow body's door 1).
// Inferred (no source): REACH, TOP_OVER, TOP_EXT, EXT_MIN / EXT_MAX; DOOR_CLEAR = 1.9 m is the clear height
// js/aircraft/fit.js hwDoor uses for the passenger doors.
import { DOCK_FOOT } from '../../data/models/dock_foot.js';
import { m4 } from '../math.js';

// bellows geometry of js/live/gates.js bridgeGeo (cab frame: x towards the aircraft from the cab pivot, y up from the cab
// floor = the door sill, z along the fuselage, aft positive when the cab faces the fuselage square, as docked): 5 folds,
// half width 1.55 m (every second fold 0.05 m wider), y 0.05..3.0 m, depth 0.45 m retracted + 0.15 m extension
export const BELLOWS = { w: 1.55, ridge: 0.05, folds: 5, y0: 0.05, y1: 3.0, rest: 0.45, ext: 0.15 };
export const DOOR_CLEAR = 1.9, TOP_OVER = 0.15, REACH = 0.8, TOP_EXT = 1.2;
const EXT_MIN = -0.42, EXT_MAX = 1.3;   // m: fold depth at least 0.18 m (0.6 - 0.42); at most 1.3 m beyond the flat front

// the dock station, cab floor and cab stop of door `which` (1 = 1L, 2 = the second bridge's door, 3 = A380 U1L) exactly
// as js/live/gates.js doorOf takes them
export function dockRef(T, which = 1) {
  if (!T) return null;
  if (which === 3) return T.dockX3 != null ? { X: T.dockX3, sill: T.dockSill3, hw: T.dockHW3 } : null;
  if (which === 2) return T.dockX2 != null ? { X: T.dockX2, sill: T.dockSill2 ?? T.dockSill, hw: T.dockHW2 ?? T.dockHW ?? T.R } : null;
  return { X: T.dockX1 ?? T.doors[0], sill: T.dockSill ?? T.sill, hw: T.dockHW ?? T.R };
}
const warned = new Set();
// measured skin grid of door `which` of type T, if it still belongs to the door doorOf docks to (else null: flat bellows)
export function footOf(T, which = 1, foot = DOCK_FOOT) {
  const w = which >= 3 ? 3 : which >= 2 ? 2 : 1;
  const g = T && foot && foot.types && foot.types[T.key] && foot.types[T.key][w]; if (!g) return null;
  const r = dockRef(T, w);
  if (!r || Math.abs(r.X - g.X) > 0.005 || Math.abs(r.sill - g.sill) > 0.005 || Math.abs(r.hw - g.hw) > 0.005) {
    const k = T.key + ':' + w; if (!warned.has(k)) { warned.add(k); if (typeof console !== 'undefined') console.warn(`dock_foot: ${k} measured for another door position: re-run tools/models/dock_foot.mjs`); }
    return null;
  }
  return { g, grid: foot };
}
// the closure's shape at deployment kk (0 retracted .. 1 on the fuselage), or null (no aircraft / no measured grid: the
// flat retracted bellows). ext(z, y): extension (m) of the front beyond the flat front at the cab stop, at z along the
// fuselage (aft +) and height y above the sill; topAt(z): height of the front's top edge (the top curtain's contact):
// one height over the footprint, lower only at stations whose skin ends below it (the nose crown ahead of a narrow body's
// door 1).
export function bellowsShape(T, which = 1, kk = 1, foot = DOCK_FOOT) {
  if (!(kk > 0)) return null;
  const F = footOf(T, which, foot); if (!F) return null;
  const { g, grid } = F; const n = grid.n, ds = grid.ds, dz = grid.dz, m = grid.m, hw = g.hw;
  // per station the squared half width Q = skin^2 at each measured height (interpolated linearly in Q: towards the crown
  // the skin of a round section goes as sqrt(height to the crown), Q is nearly linear there); the skin ends at the
  // column's last measured row (the local crown, Q extrapolated to 0 above it); an isolated row without a crossing below
  // it (a cut through a door gap) is interpolated
  const qAt = (c, y) => {
    const Q = c.Q, L = c.last; if (L < 0) return 0; const w = y / dz;
    if (w <= 0) return Q[0];
    if (w >= L) { const sl = L > 0 ? Q[L] - Q[L - 1] : 0; return Math.max(0, Q[L] + Math.min(0, sl) * (w - L)); }
    const j = Math.floor(w); return Q[j] + (Q[j + 1] - Q[j]) * (w - j);
  };
  const ext1 = (c, y) => hw - Math.sqrt(qAt(c, y));
  // highest height (searched every 1 cm, at most the column's last measured row) at which the skin of column c is within
  // e of the flat front
  const within = (c, e) => { const yM = Math.min(BELLOWS.y1, Math.max(0, c.last) * dz); let y = 0; while (y + 0.01 <= yM + 1e-9 && ext1(c, y + 0.01) <= e) y += 0.01; return y; };
  const cols = g.S.map(col => {
    let last = -1; for (let j = 0; j <= m; j++) if (col[j] != null) last = j;
    const Q = []; for (let j = 0; j <= last; j++) Q.push(col[j] == null ? null : col[j] * col[j]);
    for (let j = 0; j <= last; j++) if (Q[j] == null) {
      let a = j - 1; while (a >= 0 && Q[a] == null) a--; let b = j + 1; while (b <= last && Q[b] == null) b++;
      Q[j] = a < 0 ? (b + 1 <= last && Q[b + 1] != null ? 2 * Q[b] - Q[b + 1] : Q[b]) : Q[a] + (Q[b] - Q[a]) * (j - a) / (b - a);
    }
    return { Q, last };
  });
  // closure top: one height over the footprint, the highest at which every station's skin is within REACH of the flat
  // front, but at least the door's clear opening + TOP_OVER (the closure surrounds the doorway); lowered only at a station
  // whose skin there is more than TOP_EXT in from the flat front (narrow bodies: the nose crown ahead of door 1)
  const flat = Math.min(BELLOWS.y1, Math.max(DOOR_CLEAR + TOP_OVER, Math.min(...cols.map(c => within(c, REACH)))));
  for (const c of cols) c.top = Math.min(flat, within(c, TOP_EXT));
  const lerpCol = (z, f) => { const u = Math.max(0, Math.min(2 * n, z / ds + n)); const i = Math.min(2 * n - 1, Math.floor(u)), a = u - i; return (1 - a) * f(cols[i]) + a * f(cols[i + 1]); };
  const ext = (z, y) => Math.max(EXT_MIN, Math.min(EXT_MAX, hw - Math.sqrt(Math.max(0, lerpCol(z, c => qAt(c, y))))));
  const topAt = (z) => lerpCol(z, c => c.top);
  return { top: Math.max(...cols.map(c => c.top)), topAt, ext, kk, cols: Array.from({ length: 2 * n + 1 }, (_, i) => (i - n) * ds), dz };
}
// plan-view taper of the skin at the door (d half width / d station, aft +) at the door's mid height: for a cab that
// turns to the fuselage (js/live/gates.js keeps the cab square to the fuselage axis)
export function skinTaper(T, which = 1) {
  const F = footOf(T, which); if (!F) return null; const { g, grid } = F; const j = Math.round(0.95 / grid.dz);
  const a = g.S[0][j], b = g.S[2 * grid.n][j]; return a != null && b != null ? +((b - a) / (2 * grid.n * grid.ds)).toFixed(4) : null;
}

// the closure mesh into geo (js/geom.js Geo) in the cab frame M (js/live/gates.js cabM: x towards the aircraft, y up from
// the cab floor, z aft), its back at x = fr (the cab front), deployed by kk, depth of the flat front `bell`
// (BELLOWS.rest + BELLOWS.ext * kk). Each fibre (station z, row k) runs straight from the cab front at height yB to the
// front at height yF, so the top curtain slopes from the cab frame (y1) down to the contact (shape.top) as it deploys.
export function bellowsGeo(geo, M, fr, bell, shape, col, ext) {
  const B = BELLOWS, kk = shape.kk; const yTop = (z) => B.y1 + (shape.topAt(z) - B.y1) * kk;
  const K = Math.max(2, Math.ceil((B.y1 + (shape.top - B.y1) * kk - B.y0) / shape.dz));
  const yB = (k) => B.y0 + (B.y1 - B.y0) * k / K, yF = (k, z) => B.y0 + (yTop(z) - B.y0) * k / K;
  // point of fibre (z, k) at fraction t of its length (0 at the cab front, 1 on the skin)
  const P = (z, k, t) => { const y = yF(k, z); return m4.xform(M, [fr + t * (bell + kk * shape.ext(z, y)), yB(k) + (y - yB(k)) * t, z]); };
  const inner = shape.cols.filter(z => Math.abs(z) < B.w - 1e-6);
  const q = (a, b, c, d) => geo.quad(a, b, c, d, col, ext);
  for (let i = 0; i < B.folds; i++) {
    const W = B.w + (i % 2) * B.ridge, t0 = i / B.folds, t1 = (i + 1) / B.folds; const zs = [-W, ...inner, W];
    for (let k = 0; k < K; k++) {                                   // side curtains (outward +-z)
      q(P(W, k, t0), P(W, k, t1), P(W, k + 1, t1), P(W, k + 1, t0));
      q(P(-W, k, t0), P(-W, k + 1, t0), P(-W, k + 1, t1), P(-W, k, t1));
    }
    for (let c = 0; c + 1 < zs.length; c++) {                       // top curtain (+y) and bottom (-y)
      const za = zs[c], zb = zs[c + 1];
      q(P(za, K, t0), P(zb, K, t0), P(zb, K, t1), P(za, K, t1));
      q(P(za, 0, t0), P(za, 0, t1), P(zb, 0, t1), P(zb, 0, t0));
    }
    if (i % 2) for (const sg of [-1, 1]) {                          // fold ridges: the wider fold's faces beyond the narrow folds
      const zn = sg * B.w, zw = sg * W; const [zl, zr] = sg > 0 ? [zn, zw] : [zw, zn];
      for (let k = 0; k < K; k++) {
        q(P(zl, k, t1), P(zl, k + 1, t1), P(zr, k + 1, t1), P(zr, k, t1));   // facing the aircraft (+x)
        q(P(zl, k, t0), P(zr, k, t0), P(zr, k + 1, t0), P(zl, k + 1, t0));   // facing the cab (-x)
      }
    }
    if (i === B.folds - 1) for (let c = 0; c + 1 < zs.length; c++) for (let k = 0; k < K; k++)   // the front on the skin (+x)
      q(P(zs[c], k, 1), P(zs[c], k + 1, 1), P(zs[c + 1], k + 1, 1), P(zs[c + 1], k, 1));
  }
}
