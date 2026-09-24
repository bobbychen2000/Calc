// Airfield lighting for the live scene: runway/approach lighting (surveyed runway ends) + blue taxiway edge lights
// along the real taxiway outlines wherever the outline borders unpaved ground.
import { buildAirfieldLights, lightSpriteFn, buildPierGeometry } from '../anim/lights.js';
import { GROUND_Y } from '../geo.js';

const BLUE = [0.2, 0.35, 1];
export function buildLiveLights(airport, paved) {
  const sys = buildAirfieldLights(1.0, { taxiways: false });
  let n = 0;
  if (paved) for (const t of airport.taxiways) for (const poly of t.polys) for (const ring of poly) {
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
        sys.L.push({ p: [px + nx * o * 1.2, GROUND_Y + 0.35, pz + nz * o * 1.2], c: BLUE, i: 10, s: 0.2 }); n++;
      }
      acc -= L;
    }
  }
  sys.taxiCount = n;
  return sys;
}
export { lightSpriteFn, buildPierGeometry };
