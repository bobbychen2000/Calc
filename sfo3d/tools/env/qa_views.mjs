// Environment QA view kinds for livetest.mjs jobs (docs/research/environment_spec.md §11.1; review finding truth1-7):
// `papi:<end>,<angle deg>,<dist m>` and `thr:<end>,<dist m>,<pitch deg>` mapped onto the app's SFO.qa.look(target, yaw,
// pitch, dist, fov). Anchors from the spec (M, tools/env/lighting_spec.json): PAPI row centres and landing thresholds
// (world x, z), approach bearings (compass bearing from the target to the camera = the reciprocal of the landing
// direction): 117.8° for 28L/28R, 27.8° for 19L/19R, 297.8° for 10L/10R. The PAPI target is the row centre at the
// light height (GROUND_Y + 0.8 m, I); the camera then sits on the given glide angle through it.
// Not implemented: `lighttest:<cd>,<visSM>,<day|night>,<distSM>` (a synthetic one-light scene for A-VIS needs its own
// page; open, see docs/research/environment_impl.md).
export const PAPI_ROW = { '28R': [1132.4, 406.7], '28L': [1026.0, 608.6], '19L': [597.7, -555.9], '19R': [338.5, -544.7], '10L': [-1135.6, -941.3], '10R': [-1182.7, -701.1] };
export const THRESHOLD = { '28R': [1532.6, 542.3], '28L': [1426.1, 744.5], '19L': [733.2, -947.5] };
export const APPROACH_BEARING = { '28R': 117.8, '28L': 117.8, '19L': 27.8, '19R': 27.8, '10L': 297.8, '10R': 297.8 };
const GROUND_Y = 3;
/** Parse one view token; returns {kind, args: [target, yaw, pitch, dist, fov]} for SFO.qa.look, or null. */
export function envView(tok) {
  const [kind, rest = ''] = tok.split(':'); const a = rest.split(',');
  if (kind === 'papi') { const e = a[0], ang = +a[1], d = +(a[2] || 1852); const c = PAPI_ROW[e]; if (!c) return null;
    return { kind, label: `papi_${e}_${ang}`, args: [[c[0], GROUND_Y + 0.8, c[1]], APPROACH_BEARING[e], ang, d, 20] }; }
  if (kind === 'thr') { const e = a[0], d = +(a[1] || 305), pitch = +(a[2] || 5); const c = THRESHOLD[e]; if (!c) return null;
    return { kind, label: `thr_${e}_${d}`, args: [[c[0], GROUND_Y, c[1]], APPROACH_BEARING[e], pitch, d, 40] }; }
  return null;
}
/** All C2 PAPI views of the spec (§11.2): six ends × five angles about the published glide path. */
export const C2_VIEWS = Object.entries({ '28R': [2.3, 2.6, 3.0, 3.4, 3.7], '10L': [2.3, 2.6, 3.0, 3.4, 3.7], '10R': [2.3, 2.6, 3.0, 3.4, 3.7], '19L': [2.3, 2.6, 3.0, 3.4, 3.7],
  '28L': [2.15, 2.45, 2.85, 3.25, 3.55], '19R': [2.45, 2.75, 3.15, 3.55, 3.85] }).flatMap(([e, A]) => A.map(x => `papi:${e},${x},1852`));
