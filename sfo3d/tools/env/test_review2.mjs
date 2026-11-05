// Regression checks for the environment review round 2 fixes (docs/research/environment_impl.md §R2; findings truth2-1 ..
// truth2-11, look2-12 of the workflow wf_41410c83-b48). No GPU, no network. Each check names its finding.
// Run: node tools/env/test_review2.mjs   (exit 1 on failure)
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { buildEnvState, runwayConfigFrom, TAILWIND_SE_KT, IAP_ENDS } from '../../js/env/state.js';
import { decodeMetar, extinctionFromVisibility, SM_M } from '../../js/env/wx/metar.js';
import { controller, controllerFromEnv } from '../../js/env/lighting/controller.js';
import { rainParams, wetStart, TRACE_MM } from '../../js/env/atmo/weather_fx.js';
import { cloudLayers, detailDistribution, CIRRUS_OPACITY } from '../../js/env/atmo/sky_model.js';
import { loadFixtures } from '../../js/env/lighting/fixtures.js';
import { AV_RED, AV_GREEN, AV_WHITE } from '../../js/env/aircraft_lights.js';
import { AppEnv } from '../../js/env/app_env.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
let n = 0, fails = 0;
const check = (name, ok, info = '') => { n++; if (!ok) fails++; console.log(`${ok ? 'PASS' : 'FAIL'} | ${name}${info !== '' ? ' | ' + info : ''}`); };
const st = (raw, t = '2026-11-05T13:56:00Z', extra = {}) => buildEnvState(Date.parse(t), { reports: [raw], live: true, ...extra });

// ---------------------------------------------------------------- truth2-1: runway fallback = SFO's two published plans
{
  const fx = fs.readFileSync(path.join(HERE, 'fixtures', 'ksfo_archive_wx.txt'), 'utf8').split('\n').filter(l => /\|KSFO /.test(l)).map(l => 'METAR ' + l.split('|')[1]);
  const rec = fs.readFileSync(path.join(HERE, 'fixtures', 'ksfo_recent_20260920_24.txt'), 'utf8').split('\n').filter(l => /^(METAR|SPECI) KSFO/.test(l));
  let nonWest = 0, badInstr = 0, plans = new Set();
  for (const raw of [...fx, ...rec]) { const r = runwayConfigFrom(decodeMetar(raw), null, null); plans.add(r.plan); if (r.plan !== 'west') nonWest++; for (const [e, ty] of Object.entries(r.arr)) if (ty === 'instrument' && !IAP_ENDS.has(e)) badInstr++; }
  check('truth2-1 fallback plans only West / Southeast; no instrument arrival to an end without an IAP', [...plans].every(p => p === 'west' || p === 'southeast') && badInstr === 0, `${fx.length + rec.length} reports: plans ${[...plans].join('/')}, non-West ${nonWest}, instrument-to-no-IAP ${badInstr}`);
  const fog = runwayConfigFrom(decodeMetar('METAR KSFO 131956Z 03007KT 1/2SM R28R/2200VP6000FT BCFG VV002 16/14 A3007'), null, null);
  check('truth2-1 131956Z 03007KT 1/2SM VV002: West Plan, 28L/28R instrument (3-5-1 gave 1L/1R)', fog.plan === 'west' && fog.arr['28R'] === 'instrument' && fog.arr['28L'] === 'instrument', JSON.stringify(fog.arr));
  const S = st('METAR KSFO 131956Z 03007KT 1/2SM R28R/2200VP6000FT BCFG VV002 16/14 A3007', '2026-11-13T19:58:00Z');
  const als = S.lighting.out['ALS 28R'];
  check('truth2-1 ... and the 28R ALSF-2 is lit by day in 1/2 SM (was "ALS none")', als && als.on && als.mode === 'ALSF-2' && als.step === 5, JSON.stringify(als));
  const mar = runwayConfigFrom(decodeMetar('METAR KSFO 231556Z 14005KT 10SM FEW003 OVC005 14/13 A2995'), null, null);
  check('truth2-1 231556Z 14005KT OVC005 (28 tailwind 4.6 kt): West, instrument (ceiling 500 ft)', mar.plan === 'west' && mar.arr['28R'] === 'instrument', `${mar.source}`);
  const se = runwayConfigFrom(decodeMetar('METAR KSFO 250956Z 15023G32KT 4SM -RA FEW036 BKN048 OVC070 13/11 A2990'), null, null);
  check(`truth2-1 15023KT (28 tailwind >= ${TAILWIND_SE_KT} kt): Southeast Plan (19L/19R, depart 10L/10R)`, se.plan === 'southeast' && '19L' in se.arr && se.dep.includes('10L'), se.source);
  check('truth2-1 tagged I and shown with its rule', /^I/.test(se.tag) && /METAR fallback/.test(se.source), se.tag);
}
// ---------------------------------------------------------------- truth2-2: MALSR RAIL on TBL 3-4-7's RAIL row
{
  const W = { arr: { '28L': 'unknown', '28R': 'unknown' }, dep: ['1L', '1R'] };
  const nightVfr = controller(true, 10, null, null, W)['ALS 28L'];
  const dayIfr = controller(false, 4, null, null, W)['ALS 28L'];
  const SE = { arr: { '19L': 'unknown', '19R': 'unknown' }, dep: ['10L', '10R'] };
  const malsf = controller(true, 10, null, null, SE)['ALS 19L'];
  check('truth2-2 28L MALSR RAIL at night >= 3 SM: step 1 with the MALS (TBL 3-4-7 RAIL row)', nightVfr.SFL === true && nightVfr.step === 1 && nightVfr.SFL_pct === 2.3, JSON.stringify(nightVfr));
  check('truth2-2 28L MALSR RAIL by day 4 SM: step 2 (10 %)', dayIfr.SFL === true && dayIfr.step === 2 && dayIfr.SFL_pct === 10, JSON.stringify(dayIfr));
  check('truth2-2 19L MALSF flashers keep the 3-4-7 SFL rule (off in VFR)', malsf.SFL === false, JSON.stringify(malsf));
}
// ---------------------------------------------------------------- truth2-3: one precipitation value set
{
  const S = st('METAR KSFO 130052Z 36005KT 1 3/4SM +RA FEW019 SCT025 BKN032 09/06 A2996 RMK AO2 VIS 1V3 RAB34 P0003', '2026-11-13T00:55:00Z');
  const R = rainParams(S.precip, 'high');
  check('truth2-3 +RA P0003 clamped to 7.62 mm/h: EnvState D0 / v / drops = the drawn rain', S.precip.rateMmH === 7.62 && Math.abs(S.precip.D0mm - R.D0mm) < 0.006 && Math.abs(S.precip.vFall - R.vFall) < 0.006 && Math.abs(S.precip.dropsPerM3 - R.densityPerM3) < 1, `D0 ${S.precip.D0mm}/${R.D0mm.toFixed(3)} v ${S.precip.vFall}/${R.vFall.toFixed(3)} drops ${S.precip.dropsPerM3}/${R.densityPerM3.toFixed(1)}`);
  const D = st('METAR KSFO 051356Z 18008KT 10SM -DZ BKN040 14/10 A3000 RMK AO2 P0000');
  check('truth2-3 drizzle: EnvState fall speed = the drawn 1.5 m/s', D.precip.vFall === rainParams(D.precip).vFall, `${D.precip.vFall}`);
}
// ---------------------------------------------------------------- truth2-4: smoke aloft is an aerosol, not a cloud
{
  const S = st('METAR KSFO 271256Z 00000KT 10SM FEW004 FEW007 SCT200 11/09 A2976 RMK AO2 SLP079 FU FEW004 T01110089', '2026-05-27T13:00:00Z');
  const smoke = S.atm.slabs.find(s => s.aerosol === 'FU');
  check('truth2-4 FU FEW004: not a cloud layer, an aerosol slab at 400 ft; sunVisibleP from the water clouds only', !S.clouds.some(c => c.baseFt === 400) && smoke && Math.abs(smoke.y0 - 3 - 400 * 0.3048) < 0.5 && S.sunVisibleP > 0.6,
    `clouds ${S.clouds.map(c => c.cover + c.baseFt).join(' ')}, slab ${smoke && smoke.kind} σ ${smoke && smoke.sigma.toExponential(2)}, sunVisibleP ${S.sunVisibleP}`);
}
// ---------------------------------------------------------------- truth2-5: MIFG slab at least σ(5/8 SM)
{
  for (const [raw, night] of [['METAR KSFO 051356Z 00000KT 10SM MIFG CLR 09/08 A3010', false], ['METAR KSFO 050656Z 00000KT 7SM MIFG FEW200 09/08 A3010', true]]) {
    const S = st(raw, night ? '2026-11-05T06:58:00Z' : '2026-11-05T20:00:00Z'); const sl = S.atm.slabs[0];
    const lo = extinctionFromVisibility(5 / 8 * SM_M, S.photocell.asosNightW >= 0.5);
    check(`truth2-5 ${raw.split(' ').slice(3, 5).join(' ')}: MIFG slab σ ${sl.sigma.toExponential(2)} >= σ(5/8 SM) ${lo.toExponential(2)}`, sl.kind === 'MIFG' && sl.sigma >= lo * 0.999);
  }
}
// ---------------------------------------------------------------- truth2-6: wet start from the reported amounts
{
  const T = wetStart(st('METAR KSFO 051356Z 18008KT 10SM -DZ BKN040 14/10 A3000 RMK AO2 P0000'));
  check(`truth2-6 -DZ P0000 (trace, < ${TRACE_MM} mm): film only, no standing water`, T.film === 1 && T.water === 0 && T.pore < 0.5, JSON.stringify(T));
  const H = wetStart(st('METAR KSFO 051356Z 18012KT 2SM +RA BR OVC010 14/12 A2990 RMK AO2 P0040'));
  check('truth2-6 +RA P0040 (10.2 mm in the hour): standing water = amount − 1 h drainage', Math.abs(H.water - (0.40 * 25.4 - 2)) < 1e-6 && H.pore === 1, JSON.stringify(H));
}
// ---------------------------------------------------------------- truth2-7: snapshot weather before the 3 snapshot reports
{
  const A = new AppEnv({ mode: 'snapshot', snapshotNow: Date.parse('2026-09-23T17:51:25Z'), snapshotMetar: '', search: '' });
  A.setLightMode('dawn'); const D = A.update();
  check('truth2-7 snapshot light mode Dawn (23 Sep 13:45Z): the 231256Z marine-layer report, not a clear default', /231256Z/.test(D.wx.raw || '') && D.clouds.some(c => c.cover === 'BKN') && D.prov.wx.startsWith('V'), `${D.wx.raw} · clouds ${D.clouds.map(c => c.cover + c.baseFt).join(' ')}`);
  const B = new AppEnv({ mode: 'snapshot', snapshotNow: Date.parse('2026-09-23T17:51:25Z'), snapshotMetar: '', search: '?t=2026-09-20T12:00:00Z' }).update();
  check('truth2-7 before the earliest report and TAF: labelled "no weather data" (I)', B.wx.none === true && /^I \(no weather data/.test(B.prov.wx), B.prov.wx);
}
// ---------------------------------------------------------------- truth2-8: in-pavement lights
{
  const { LIGHTING_SPEC, LIGHTING_FIXTURES } = await import('../../data/sfo_lighting.js');
  const { records } = loadFixtures(LIGHTING_FIXTURES, LIGHTING_SPEC, { groundY: 3 });
  const inp = records.filter(r => r.inpav), elev = records.filter(r => !r.inpav && /^(runway_edge|threshold_end|runway_end|threshold_wingbar)$/.test(r.system));
  check('truth2-8 in-pavement edge / threshold / end faces at 1/2 in with L-850C / L-850D photometry', inp.length > 0 && inp.every(r => Math.abs(r.p[1] - 3 - 0.0127) < 1e-6 && /^L-850[CD]$/.test(r.ftype)),
    `${inp.length} faces (${LIGHTING_SPEC.in_pavement && JSON.stringify(LIGHTING_SPEC.in_pavement.counts)}), elevated ${elev.length} at ${elev.length ? (elev[0].p[1] - 3).toFixed(2) : '-'} m`);
}
// ---------------------------------------------------------------- truth2-10: aircraft colours inside the 25.1397 boxes
{
  // linear sRGB -> CIE xy (IEC 61966-2-1 matrix)
  const xy = (c) => { const X = 0.4124 * c[0] + 0.3576 * c[1] + 0.1805 * c[2], Y = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2], Z = 0.0193 * c[0] + 0.1192 * c[1] + 0.9505 * c[2]; const s = X + Y + Z; return [X / s, Y / s]; };
  const [wx, wy] = xy(AV_WHITE);
  check('truth2-10 aircraft white (strobes, tail) inside 25.1397(c): 0.300 <= x <= 0.540, x - 0.040 <= y <= x + 0.020, y <= 0.636 - 0.400 x', wx >= 0.3 && wx <= 0.54 && wy >= wx - 0.04 && wy <= wx + 0.02 && wy <= 0.636 - 0.4 * wx, `xy (${wx.toFixed(3)}, ${wy.toFixed(3)})`);
  // green: the stated point (0.180, 0.665) is inside 25.1397(b); its sRGB display is gamut-clipped (the box lies almost
  // entirely outside the sRGB gamut, M: the sRGB green primary (0.30, 0.60) fails x <= 0.440 - 0.320 y), as every display
  const [gx, gy] = [0.18, 0.665], [cx, cy] = xy(AV_GREEN);
  check('truth2-10 aircraft green point inside 25.1397(b) (display gamut-clipped)', gx <= 0.44 - 0.32 * gy && gx <= gy - 0.17 && gy >= 0.39 - 0.17 * gx && AV_GREEN[0] === 0 && AV_GREEN[1] === 1, `point (${gx}, ${gy}); displayed xy (${cx.toFixed(3)}, ${cy.toFixed(3)})`);
  check('truth2-10 aircraft red: lin 1/0/0 (the inferred point (0.700, 0.299), z 0.001, gamut-clipped)', AV_RED.join() === '1,0,0');
}
// ---------------------------------------------------------------- truth2-11: 20,000-ft layers are cirrus
{
  const S = st('METAR KSFO 241856Z 03006KT 10SM SCT200 22/16 A2989', '2026-09-24T19:00:00Z');
  const h = new Float64Array(256).fill(1 / 256); const L = cloudLayers(S, detailDistribution(h));
  check('truth2-11 SCT200: cirriform, opacity ' + CIRRUS_OPACITY, S.clouds[0].kind === 'cirriform' && L[0].opacity === CIRRUS_OPACITY, `${S.clouds[0].kind}`);
}
console.log(`\nreview round 2: ${n - fails}/${n} checks passed`);
process.exit(fails ? 1 : 0);
