// What the airfield-lighting module draws from the spec §11.2 QA views for the real-weather presets (environment step 2,
// docs/research/environment_impl.md §2.5): lit sprites per fixture system, and how many are below the Allard threshold.
// Numeric (no GPU). Run: node tools/env/lights_views.mjs
import { LIGHTING_SPEC, LIGHTING_FIXTURES } from '../../data/sfo_lighting.js';
import { AirfieldLighting } from '../../js/env/lighting/airfield.js';
import { buildEnvState } from '../../js/env/state.js';
import { presetById, presetRunway } from '../../js/env/presets.js';
import { visualRange } from '../../js/env/lighting/photometry.js';
const D = Math.PI / 180;
const AL = new AirfieldLighting(LIGHTING_FIXTURES, LIGHTING_SPEC, { groundY: 3 });
// cameras (spec §11.2 / §11.1 anchors): 28R approach 2 NM on a 3° path (+16.8 m TCH-ish); C3 eye 5 m on the 28R CL at
// the landing threshold looking west; C1 1,000 ft out, 100 ft up; the tower cab (DOF tower position, eye ~70 m)
const views = { 'E3/E4 28R 2NM': [1532.6 + 0.8846 * 3704 * Math.cos(3 * D), 3 + 3704 * Math.sin(3 * D) + 16.8, 542.3 + 0.4664 * 3704 * Math.cos(3 * D)],
  'C3 28R thr eye 5m': [1178.8 + 0.8846 * 400, 8, 355.7 + 0.4664 * 400], 'C1 28R 1000ft out 100ft up': [1532.6 + 0.8846 * 305, 33.5, 542.3 + 0.4664 * 305], 'tower cab': [-741, 70, 336] };
for (const id of ['dusk', 'night_clear', 'predawn_fog', 'ifr_mist_day', 'marine_layer', 'drizzle_night', 'noon']) {
  const p = presetById(id);
  const E = buildEnvState(Date.parse(p.time_utc), { mode: 'preset', overridden: true, reports: [p.metar], rwyOverride: presetRunway(p) });
  for (const [vn, cam] of Object.entries(views)) {
    const S = AL.update(E, cam, 100); const by = {}; for (const s of S) by[s.sys] = (by[s.sys] || 0) + 1;
    console.log(id.padEnd(13) + ' ' + vn.padEnd(27) + ' lit ' + String(S.length).padStart(4) + ' (below E_T ' + String(AL.stats.invisible).padStart(4) + ')  ' + Object.entries(by).map(([k, v]) => k + ' ' + v).join(', '));
  }
}
const s1 = visualRange(15, 3.3e-5, 6.99e-7), s1o = visualRange(0.075, 3.3e-5, 6.99e-7), twy = visualRange(2, 3.3e-5, 6.99e-7);
console.log('night clear: HIRL step 1 in-beam 15 cd range', (s1 / 1609.344).toFixed(2), 'SM; omni 0.075 cd', s1o.toFixed(0), 'm; L-861T 2 cd', twy.toFixed(0), 'm');
