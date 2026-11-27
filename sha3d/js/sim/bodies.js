// forked from sfo3d@e3218d6 js/live/ground.js (samples / inside / bodyOf / overlaps / fusIn)
// Aircraft planforms as solid bodies for the Phase 3 test suite (design §1.2, §5; review L6). Changes from sfo3d:
// - headings are DEGREES TRUE (js/geo.js hdgVec), not radians (sfo3d's hv(h) took radians, ground.js:16);
// - a body is placed by its NOSE TIP (bodyOf(T, noseX, noseZ, hdg)); sfo3d's bodyOf added the transponder-antenna offset
//   from traffic.js antOf (ground.js:14, :187), which is dropped: the simulator knows the nose-gear point exactly
//   (tip = nose gear + noseGearX ahead, js/live/gate_system.js noseGearX / standTip);
// - no DOM: the canvas building grid, the bridge grids and the GroundPhysics class are not forked (the sim's tests use
//   polygon pavement tests in node);
// - new: gear points of a pose from the nose gear (gearOf), the clearance between two bodies (clearance), and a
//   planform-sample generator for swept-path tests (sweptSamples).
// Pure module: T is a js/aircraft/types.js TYPES entry (passed in); nothing is imported at module scope except geo.js.
import { hdgVec } from '../geo.js';

const D2R = Math.PI / 180;

/** planform samples of an aircraft (nose tip at `nose`, heading hdg in degrees): gear points, outline points, fuselage */
export function samples(T, nose, hdg) {
  const f = hdgVec(hdg), r = [-f[1], f[0]];
  const P = (along, side) => [nose[0] - f[0] * along + r[0] * side, nose[1] - f[1] * along + r[1] * side];
  const w = T.wing, span = w ? w.span / 2 : 16, le = w ? w.rootLE : T.L * 0.4, sw = Math.tan(((w && w.sweep) || 27) * D2R);
  const tipLE = le + span * sw, tipC = w ? w.tipC : 1.5;
  const gear = [P(T.xNose ?? 3, 0), P(T.xMain, (T.track || 6) / 2), P(T.xMain, -(T.track || 6) / 2)];
  const hs = T.hstab ? T.hstab.span / 2 : 6, hx = T.hstab ? T.hstab.x + (T.hstab.rootC || 3) : T.L - 2;
  const outline = [P(0, 0), P(T.L, 0), P(tipLE + tipC / 2, span), P(tipLE + tipC / 2, -span), P(le + span * 0.5 * sw, span * 0.5), P(le + span * 0.5 * sw, -span * 0.5),
    P(hx, hs), P(hx, -hs), P(T.L * 0.25, 0), P(T.L * 0.5, 0), P(T.L * 0.75, 0), P(le, T.R), P(le, -T.R)];
  const fus = []; const n = Math.max(4, Math.ceil(T.L / 3)), R = (T.R || 2) * 0.9;
  for (let i = 0; i <= n; i++) { const a = 1 + (T.L - 2) * i / n; fus.push(P(a, R), P(a, -R), P(a, 0)); }
  return { gear, outline, fus, f, r };
}
/** is point q inside the planform of body A with margin m (metres) */
export function inside(A, q, m) {
  const T = A.T, f = A.f, r = A.r;
  const dx = q[0] - A.nose[0], dz = q[1] - A.nose[1];
  const x = -(dx * f[0] + dz * f[1]), y = dx * r[0] + dz * r[1];
  if (x > -m && x < T.L + m && Math.abs(y) < T.R + m) return true;
  const w = T.wing;
  if (w) {
    const ay = Math.abs(y), le = w.rootLE + ay * Math.tan((w.sweep || 27) * D2R);
    const ch = w.rootC - (w.rootC - w.tipC) * Math.min(1, ay / (w.span / 2));
    if (ay < w.span / 2 + m && x > le - m && x < le + ch + m) return true;
  }
  if (T.hstab && x > T.hstab.x - m && x < T.L + m && Math.abs(y) < T.hstab.span / 2 + m) return true;
  return false;
}
/** body of type T with its nose tip at (x, z) and heading hdg (degrees true) */
export function bodyOf(T, x, z, hdg) { const f = hdgVec(hdg); return { T, nose: [x, z], h: hdg, f, r: [-f[1], f[0]] }; }
/** body from a nose-gear point (the simulator's path point): the nose tip is noseGearX ahead */
export function bodyFromNoseGear(T, x, z, hdg) { const f = hdgVec(hdg); const k = T.xNose ?? 3; return bodyOf(T, x + f[0] * k, z + f[1] * k, hdg); }
export function overlaps(A, B, m = 0) {
  const dx = A.nose[0] - B.nose[0], dz = A.nose[1] - B.nose[1];
  if (Math.sqrt(dx * dx + dz * dz) > (A.T.L + B.T.L) * 0.5 + 45 + m) return false;
  const Sa = A.S || (A.S = samples(A.T, A.nose, A.h)), Sb = B.S || (B.S = samples(B.T, B.nose, B.h));
  return Sa.outline.some(p => inside(B, p, m)) || Sb.outline.some(p => inside(A, p, m)) || Sa.fus.some(p => inside(B, p, m)) || Sb.fus.some(p => inside(A, p, m));
}
/** fuselage samples of each body inside the other's planform (depth of an overlap) */
export function fusIn(A, B) {
  const Sa = A.S || (A.S = samples(A.T, A.nose, A.h)), Sb = B.S || (B.S = samples(B.T, B.nose, B.h)); let n = 0;
  for (const p of Sa.fus) if (inside(B, p, 0)) n++; for (const p of Sb.fus) if (inside(A, p, 0)) n++; return n;
}
/** clearance (m) between two planforms: the largest margin at which they do not overlap (bisection, 0.1 m); 0 if they overlap */
export function clearance(A, B, max = 60) {
  if (overlaps(A, B, 0)) return 0;
  if (!overlaps(A, B, max)) return max;
  let lo = 0, hi = max; while (hi - lo > 0.1) { const m = (lo + hi) / 2; if (overlaps(A, B, m)) hi = m; else lo = m; }
  return lo;
}
/** gear points (nose, left main, right main) of a pose given by the nose-gear point and heading */
export function gearOf(T, ngX, ngZ, hdg) {
  const f = hdgVec(hdg), r = [-f[1], f[0]]; const wb = T.xMain - (T.xNose ?? 3), tr = (T.track || 6) / 2;
  const mx = ngX - f[0] * wb, mz = ngZ - f[1] * wb;
  return [[ngX, ngZ], [mx + r[0] * tr, mz + r[1] * tr], [mx - r[0] * tr, mz - r[1] * tr]];
}
/** outline samples of a pose for swept-path tests: nose, tail, wing tips, wing half-span points, tailplane tips */
export function sweptSamples(T, ngX, ngZ, hdg) { const b = bodyFromNoseGear(T, ngX, ngZ, hdg); return samples(T, b.nose, hdg).outline; }
