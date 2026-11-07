// Airfield lighting for the live scene: runway/approach lighting (surveyed runway ends) + blue taxiway edge lights
// along the real taxiway outlines wherever the outline borders unpaved ground.
// Since the environment step 2 (js/live/app.js) only the approach-light STRUCTURES (piers, opts.lightPlane: built at the
// ALS light plane) and the blue taxiway-edge positions (the last sys.taxiCount records of sys.L) are used from here; the
// runway / approach / PAPI sprites come from data/sfo_lighting.js via js/env/lighting/airfield.js.
import { buildAirfieldLights, lightSpriteFn, buildPierGeometry, alsPlacement, buildMountGeometry } from '../anim/lights.js';
import { GROUND_Y } from '../geo.js';
import { DETAILS } from '../../data/sfo_details.js';

const BLUE = [0.2, 0.35, 1];
export function buildLiveLights(airport, paved, opts = {}) {
  const sys = buildAirfieldLights(1.0, { taxiways: false, lightPlane: opts.lightPlane });
  let n = 0;
  // retired SFO Museum taxiway pavement (close-out round 3, env-12): whole polygons (DETAILS.pavementRetired, key name +
  // '#' + polygon index as js/live/airport.js) have no edge, and no light stands inside a retired part (pavementRetiredParts)
  const retired = new Set(((DETAILS && DETAILS.pavementRetired) || []).filter(r => r.layer === 'taxiways').map(r => r.name + '#' + r.poly));
  const parts = ((DETAILS && DETAILS.pavementRetiredParts) || []).map(r => r.ring);
  const inRing = (r, x, z) => { let w = false; for (let i = 0, j = r.length - 1; i < r.length; j = i++) { const a = r[i], b = r[j]; if ((a[1] > z) !== (b[1] > z) && x < (b[0] - a[0]) * (z - a[1]) / (b[1] - a[1]) + a[0]) w = !w; } return w; };
  let nRetired = 0;
  if (paved) for (const t of airport.taxiways) for (const [pi, poly] of t.polys.entries()) { if (retired.has(t.name + '#' + pi)) continue; for (const ring of poly) {
    let acc = 22;
    for (let i = 0; i < ring.length; i++) {
      const a = ring[i], b = ring[(i + 1) % ring.length];
      const dx = b[0] - a[0], dz = b[1] - a[1], L = Math.hypot(dx, dz); if (L < 1) continue;
      const nx = -dz / L, nz = dx / L;
      for (; acc < L; acc += 48) {
        const px = a[0] + dx * acc / L, pz = a[1] + dz * acc / L;
        const s1 = paved(px + nx * 3, pz + nz * 3), s2 = paved(px - nx * 3, pz - nz * 3);
        if (s1 === s2) continue; // junction with other pavement (or a sliver): no edge light
        const o = s1 ? -1 : 1; // offset toward the unpaved side
        const qx = px + nx * o * 1.2, qz = pz + nz * o * 1.2;
        if (parts.some(r => inRing(r, px, pz) || inRing(r, qx, qz))) { nRetired++; continue; }
        sys.L.push({ p: [qx, GROUND_Y + 0.35, qz], c: BLUE, i: 10, s: 0.2 }); n++;
      }
      acc -= L;
    }
  } }
  sys.taxiCount = n; sys.taxiRetiredSkipped = nRetired;
  return sys;
}
export { lightSpriteFn, buildPierGeometry, alsPlacement, buildMountGeometry };
