// HWD airport grid (new for hwd3d; replaces sfo3d js/world/airfield.js APT_RECT / RWY (s,t) and the s/t helpers that
// sfo3d kept in js/geo.js, which hwd3d's frozen geo.js dropped - fork map 1.3, risk R9). Node-pure.
//
// The grid is the world frame rotated so that s runs along the runway direction 10 -> 28 and t across it:
//   s = unit vector of the 10L -> 28R axis in world (x, z) (geo.js rwyAxis('10L').hdg, 119.857 deg true: the bearing in
//       the local tangent plane from the two FAA NASR runway ends; fork map R9);
//   t = s turned 90 deg clockwise seen from above = the pilot's right when moving 10 -> 28 (south-west).
// Both HWD runways are parallel to 0.005 deg (rwyAxis('10R').hdg 119.852), so a single axis serves both; each runway's own
// marking geometry is laid in its own exact axis (geo.js rwyAlongAcross), never in this grid.
// origin = the world origin (NASR ARP). Units: metres.
import { rwyAxis } from '../geo.js';

const AX = rwyAxis('10L');
export const GRID = Object.freeze({
  hdg: AX.hdg,                       // deg true
  s: Object.freeze([AX.dir[0], AX.dir[1]]),      // world (x, z) unit vector along 10 -> 28
  t: Object.freeze([AX.right[0], AX.right[1]]),  // world (x, z) unit vector across (right of s)
  src: "geo.js rwyAxis('10L') (FAA NASR runway ends)",
});
// world (x, z) -> grid [s, t]
export function worldToGrid(x, z) { return [x * GRID.s[0] + z * GRID.s[1], x * GRID.t[0] + z * GRID.t[1]]; }
// grid (s, t) -> world [x, z]
export function gridToWorld(s, t) { return [s * GRID.s[0] + t * GRID.t[0], s * GRID.s[1] + t * GRID.t[1]]; }
// grid-aligned rectangle {s0, t0, w, h} containing world points [[x, z], ...] with a margin (m)
export function gridRectOf(pts, margin = 0) {
  let s0 = 1e9, s1 = -1e9, t0 = 1e9, t1 = -1e9;
  for (const p of pts) { const [s, t] = worldToGrid(p[0], p[1]); s0 = Math.min(s0, s); s1 = Math.max(s1, s); t0 = Math.min(t0, t); t1 = Math.max(t1, t); }
  return { s0: s0 - margin, t0: t0 - margin, w: s1 - s0 + 2 * margin, h: t1 - t0 + 2 * margin };
}
