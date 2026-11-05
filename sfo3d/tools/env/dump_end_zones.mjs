// Runway end zones of the app (js/live/airport.js END_ZONES: blast pads type 1, EMAS beds type 2; NAIP-measured by the
// static track) as world polygons for tools/env/build_lighting_spec.py (in-pavement test of the threshold / end lights,
// environment review finding truth2-8). Run: node tools/env/dump_end_zones.mjs > tools/env/end_zones.json
import { endZoneRects, EMAS_SETBACK } from '../../js/live/airport.js';
import { RWY, RWY_W } from '../../js/world/airfield.js';
import { stToWorld } from '../../js/geo.js';
const w = ([s, t]) => { const p = stToWorld(s, t); return [+p[0].toFixed(2), +p[2].toFixed(2)]; };
const zones = endZoneRects().map(z => {
  const r = RWY[z.rw]; const end = r.name[z.end];
  // the paved part: a blast pad (type 1) over the runway width; an EMAS (type 2) only its setback over the runway width (I)
  const hw = RWY_W / 2, sgn = z.end === 0 ? -1 : 1, a = z.end === 0 ? r.a0 : r.a1;
  const L = z.type === 1 ? z.len : EMAS_SETBACK, u0 = a, u1 = a + sgn * L;
  const rect = r.axis === 0 ? [[u0, r.c - hw], [u1, r.c - hw], [u1, r.c + hw], [u0, r.c + hw]] : [[r.c - hw, u0], [r.c + hw, u0], [r.c + hw, u1], [r.c - hw, u1]];
  return { end, type: z.type === 1 ? 'blast pad' : 'EMAS setback', len_m: L, poly: rect.map(w) };
});
console.log(JSON.stringify({ source: 'js/live/airport.js END_ZONES (static track, NAIP) via tools/env/dump_end_zones.mjs', zones }, null, 1));
