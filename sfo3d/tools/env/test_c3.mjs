// Close-out round 3 (env track) regression checks, no GPU: FAA Order 8400.9 runway-use limits (env-5), the day incident
// bound of the exposure (env-4 / env-16), the position-light lens rule (env-6), the NAIP shoreline foam field (env-13),
// retired pavement in the lighting spec and the sign / edge-light placement (env-12), the sign atlas exports (env-15),
// the Peninsula reservoirs carved into the terrain (env-14).
// Run: node tools/env/test_c3.mjs (also from tools/env/run_gates.sh)
import fs from 'fs'; import path from 'path'; import { fileURLToPath } from 'url';
import { runwayConfigFrom, WET_CROSSWIND_KT, CROSSWIND_SE_KT } from '../../js/env/state.js';
import { decodeMetar } from '../../js/env/wx/metar.js';
import { incidentBound, INCIDENT_SPAN } from '../../js/env/atmo/exposure.js';
import { lensGain, NAV_LENS_S, SPRITE_MIN_PX, aircraftSprites, setLightViewer, setLightEnv, setLightFrame } from '../../js/env/aircraft_lights.js';
import { CD_PER_LAMP_S2 } from '../../js/env/lighting/photometry.js';
import { DAY_GAIN } from '../../js/env/lighting/airfield.js';
import { shoreField, shoreDistanceAt } from '../../js/env/shore_field.js';
import { SHORE } from '../../data/sfo_shore.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
let n = 0, fails = 0;
const check = (name, ok, info = '') => { n++; if (!ok) fails++; console.log(`${ok ? 'PASS' : 'FAIL'} | ${name}${info !== '' ? ' | ' + info : ''}`); };

// ---------------------------------------------------------------- env-5: FAA Order 8400.9 §4b limits in the fallback
{
  const P = (raw) => runwayConfigFrom(decodeMetar(raw), null, null);
  check('8400.9 dry: 28 crosswind incl. gust 21.8 kt > 20 (20015G22KT, VCTS only) -> Southeast', P('METAR KSFO 260022Z 20015G22KT 5SM VCTS SCT020 BKN030 14/12 A2990').plan === 'southeast');
  check('8400.9 dry: 28 crosswind 19.8 kt <= 20 (20020KT) -> West', P('METAR KSFO 260022Z 20020KT 10SM SCT020 14/12 A2990').plan === 'west', P('METAR KSFO 260022Z 20020KT 10SM SCT020 14/12 A2990').source);
  check('8400.9 wet: tailwind 4.6 kt on 28 > calm 3 kt with -DZ (14005KT) -> Southeast', P('METAR KSFO 301456Z 14005KT 10SM -DZ OVC010 14/13 A2995').plan === 'southeast');
  check('8400.9 dry: tailwind 4.6 kt on 28 <= 5 (14005KT, no precip) -> West', P('METAR KSFO 231556Z 14005KT 10SM FEW003 OVC005 14/13 A2995').plan === 'west');
  const sq = P('METAR KSFO 251056Z 22036G63KT 2SM +RA BR SQ BKN012 OVC020 12/11 A2970');
  check('8400.9 both plans fail (22036G63KT +RA): the smaller excess (Southeast)', sq.plan === 'southeast', sq.source);
  check('8400.9 constants (V): dry crosswind 20, wet 15', CROSSWIND_SE_KT === 20 && WET_CROSSWIND_KT === 15);
}
// ---------------------------------------------------------------- env-4 / env-16: day exposure within ±1 EV of the incident reading
{
  check('incident bound by day: marine-layer tower reflected 13.25 vs target 11.97 -> 12.97', Math.abs(incidentBound(13.25, 11.97, 22) - (11.97 + INCIDENT_SPAN)) < 1e-9);
  check('incident bound by day: interior view 9.0 vs 15.0 -> 14.0', Math.abs(incidentBound(9.0, 15.0, 40) - 14.0) < 1e-9);
  check('incident bound inactive at night / dusk (Sun -5.2 deg): 4.05 stays', incidentBound(4.05, 0.67, -5.2) === 4.05);
  check('incident bound: inside the band unchanged (14.26 vs 13.49)', incidentBound(14.26, 13.49, 58) === 14.26);
}
// ---------------------------------------------------------------- env-6: position-light lens by day
{
  const px = 2 * Math.tan(25 * Math.PI / 180) / 360;           // 50 deg fov, 360 px high (the review renders)
  const day = lensGain(0.22, 14.4, 0, DAY_GAIN, px), night = lensGain(0.22, 14.4, 1, 1, px), far = lensGain(0.22, 300, 0, DAY_GAIN, px);
  check('lens by day at 14.4 m: drawn at the lens size 0.08 m', Math.abs(day.s - NAV_LENS_S) < 1e-9, JSON.stringify(day));
  check('lens by day at 14.4 m: gain only to the 2.2-px floor (~1.1, not 30)', day.g >= 1 && day.g < 1.3, day.g.toFixed(3));
  check('lens at night: record size 0.22 m, gain 1', Math.abs(night.s - 0.22) < 1e-9 && night.g === 1);
  check('lens by day at 300 m (sub-pixel): the airfield display gain', far.g === DAY_GAIN, far.g);
  // peak radiance of the drawn core in sky units at the night calibration (js/three/lights.js header: I = i x LAMP_M /
  // (kUp^2 x 1.6^2 x 0.35), i = lampUnits(cd x g, s)); vs sunlit white paint 2.54 sky units (engine verify, 0.8 x 9.98 / pi)
  const LAMP_M = (20 / 6665) / 0.62;
  const peak = (cd, L) => { const i = cd * L.g / (CD_PER_LAMP_S2 * L.s * L.s); const pxS = L.s / (14.4 * px); const kUp = Math.max(SPRITE_MIN_PX / pxS, 1); return i * LAMP_M / (kUp * kUp * 1.6 * 1.6 * 0.35); };
  const pDay = peak(80, day), pOld = peak(80, { s: 0.22, g: DAY_GAIN });
  check('lens by day: peak 0.5-3 x sunlit white paint (a lens of 40-80 cd)', pDay / 2.54 > 0.5 && pDay / 2.54 < 3, `peak ${pDay.toFixed(2)} sky units = ${(pDay / 2.54).toFixed(2)} x paint; before (0.22 m, gain 30): ${(pOld / 2.54).toFixed(1)} x`);
  // aircraftSprites end to end: the record gets s 0.08 and lens: true by day only
  setLightViewer([10, 3, 10], px); setLightFrame(1);   // 14 m from the right (green) light, 42 deg off dead ahead
  const L = { navL: [-1, 3, 0], navR: [1, 3, 0], tail: [0, 3, -20] }, ax = { fwd: [0, 0, 1], right: [1, 0, 0], up: [0, 1, 0] };
  setLightEnv({ photocell: { asosNightW: 0 }, atm: null, lightVis: { ET: 4.12e-4 } }, DAY_GAIN);
  const S = aircraftSprites(L, ax, { nav: true }, 0.3, 1);
  setLightEnv({ photocell: { asosNightW: 1 }, atm: null, lightVis: { ET: 6.99e-7 } }, DAY_GAIN);
  const Sn = aircraftSprites(L, ax, { nav: true }, 0.3, 1);
  check('aircraftSprites by day: position lights at the lens size, lens flag (no glare halo)', S.length > 0 && S.every(s => s.s === NAV_LENS_S && s.lens), JSON.stringify(S.map(s => [s.nav, s.s, +s.i.toFixed(1)])));
  check('aircraftSprites at night: unchanged 0.22 m footprint, no lens flag', Sn.length > 0 && Sn.every(s => Math.abs(s.s - 0.22) < 1e-9 && !s.lens), JSON.stringify(Sn.map(s => [s.nav, s.s, +s.i.toFixed(1)])));
  setLightViewer(null, 0); setLightEnv(null);
}
// ---------------------------------------------------------------- env-13: NAIP shoreline field for the foam
{
  const F = shoreField();
  check('shore field covers SHORE.coverage at 2 m', F.cell === 2 && F.rect[0] === SHORE.coverage[0] && F.w * F.cell >= SHORE.coverage[2] - SHORE.coverage[0], `${F.w} x ${F.h}`);
  const R = SHORE.rings[0]; let near = 0, tot = 0, land = 0;
  for (let i = 0; i < R.length; i += 7) { const a = R[i], b = R[(i + 1) % R.length]; const ex = b[0] - a[0], ez = b[1] - a[1], Lr = Math.hypot(ex, ez); if (Lr < 1) continue;
    const s1 = shoreDistanceAt(a[0] + ex / 2 + ez / Lr * 4, a[1] + ez / 2 - ex / Lr * 4), s2 = shoreDistanceAt(a[0] + ex / 2 - ez / Lr * 4, a[1] + ez / 2 + ex / Lr * 4);
    if (s1 == null || s2 == null) continue; tot++; const w = Math.max(s1, s2), l = Math.min(s1, s2); if (w > 1 && w < 8) near++; if (l === 0) land++; }
  check('4 m off the NAIP shoreline: water side within the 8-m foam band, land side 0', near / tot > 0.9 && land / tot > 0.9, `${near}/${tot} water-side in band, ${land}/${tot} land side 0`);
}
// ---------------------------------------------------------------- env-12: retired pavement in the lighting spec
{
  const spec = JSON.parse(fs.readFileSync(path.join(HERE, 'lighting_spec.json'), 'utf8'));
  check('lighting spec: in-pavement runway-edge points not on retired F1 pavement (101 -> 98)', spec.in_pavement.counts.runway_edge === 98, JSON.stringify(spec.in_pavement.counts));
}
// ---------------------------------------------------------------- env-14: the Peninsula reservoirs carved into the terrain
{
  // canvas stub (no masks: the land / water and urban masks are blank; the lakes are 5-14 km inland, away from the Bay)
  if (!globalThis.document) { const ctx2d = new Proxy({ getImageData: (x, y, w, h) => ({ data: new Uint8ClampedArray(w * h * 4) }) }, { get: (t, k) => k in t ? t[k] : () => {}, set: () => true }); globalThis.document = { createElement: () => ({ width: 1, height: 1, getContext: () => ctx2d }) }; }
  const { Terrain } = await import('../../js/world/terrain.js'); const { RESERVOIRS } = await import('../../js/env/reservoirs_data.js');
  const T = new Terrain();
  for (const L of RESERVOIRS.lakes) {
    const R = L.ring; const A = R.reduce((s, p, i) => s + p[0] * R[(i + 1) % R.length][1] - R[(i + 1) % R.length][0] * p[1], 0);
    let inB = 0, inN = 0, outA = 0, outN = 0;
    for (let i = 0; i < R.length; i += 3) { const a = R[i], b = R[(i + 1) % R.length]; const ex = b[0] - a[0], ez = b[1] - a[1], l = Math.hypot(ex, ez); if (l < 5) continue;
      const s = A < 0 ? -1 : 1, nx = s * ez / l, nz = -s * ex / l, mx = (a[0] + b[0]) / 2, mz = (a[1] + b[1]) / 2;   // outward normal
      inN++; if (T.height(mx - nx * 30, mz - nz * 30) < L.level_y) inB++; outN++; if (T.height(mx + nx * 100, mz + nz * 100) > L.level_y) outA++; }
    check(`terrain carved for ${L.name} (level y ${L.level_y}): bed below the water 30 m inside, ground above it 100 m outside (>= 85 %; narrow arms excepted)`, inB / inN >= 0.85 && outA / outN >= 0.85, `inside ${inB}/${inN}, outside ${outA}/${outN}`);
  }
}
console.log(`close-out round 3 (env): ${n - fails}/${n} checks passed`);
process.exit(fails ? 1 : 0);
