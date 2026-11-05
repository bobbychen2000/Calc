// Gate A-CTL (docs/research/environment_spec.md §11.3): the JS lighting controller (js/env/lighting/controller.js)
// reproduces `lights` of tools/env/fixtures/env_presets.json (written by the Python reference controller in
// tools/env/env_spec_checks.py) for all 14 real-weather presets, two ways:
//   (a) direct: controller(tower_night, vis, rvr28r, ceiling, runway_config_input) with the fixture's own inputs;
//   (b) through the app path: preset -> buildEnvState (js/env/state.js, the data the renderers get) ->
//       controllerFromEnv -> output deep-equal to the fixture (and its PAPI photocell mode equals the reference mode).
// Plus edge cases of the tables (TBL 3-4-8 "3 to 5 miles inclusive", 3-4-9 ALSF-2 / SSALR switch, day ALS with a low
// ceiling, the flasher rule with the app's 'instrument' / 'observed' approach types).
// Run: node tools/env/test_controller.mjs   (exit 1 on failure)
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { controller, controllerFromEnv, controllerInputs, rvrValue, MITL_PCT } from '../../js/env/lighting/controller.js';
import { buildEnvState } from '../../js/env/state.js';
import { presetById, presetRunway } from '../../js/env/presets.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const P = JSON.parse(fs.readFileSync(path.join(HERE, 'fixtures', 'env_presets.json'), 'utf8')).presets;
let fails = 0, n = 0;
const check = (name, ok, info = '') => { n++; if (!ok) fails++; console.log(`${ok ? 'PASS' : 'FAIL'} | ${name}${info !== '' ? ' | ' + info : ''}`); };
const canon = (x) => JSON.stringify(x, (k, v) => (v && typeof v === 'object' && !Array.isArray(v)) ? Object.fromEntries(Object.keys(v).sort().map(q => [q, v[q]])) : v);
const diff = (a, b) => { const out = []; for (const k of new Set([...Object.keys(a), ...Object.keys(b)])) if (canon(a[k]) !== canon(b[k])) out.push(`${k}: ${canon(a[k])} != ${canon(b[k])}`); return out; };

for (const p of P) {
  // (a) direct, with the reference's inputs (visibility reduced by 1 % for 'M', 10 SM when missing)
  const vis = p.metar.match(/\sM?(\d+(?:\s\d\/\d)?|\d\/\d)SM\s/);
  const S = buildEnvState(Date.parse(p.time_utc), { mode: 'preset', overridden: true, reports: [/^(METAR|SPECI)/.test(p.metar) ? p.metar : 'METAR ' + p.metar], rwyOverride: presetRunway(presetById(p.id)) });
  const inp = controllerInputs(S);
  const a = controller(p.tower_night, inp.vis, p.rvr28r_min_ft, p.ceiling_ft, p.runway_config_input);
  const da = diff(a, p.lights);
  check(`A-CTL direct ${p.id.padEnd(17)}`, da.length === 0, da.length ? da.join('; ') : `${Object.keys(a).length} systems, vis ${inp.vis} SM${vis ? '' : ' (none)'}`);
  // (b) through EnvState (what the renderers use)
  const c = controllerFromEnv(S);
  const db = diff(c.out, p.lights);
  const papiSame = (c.papi.night ? 'night' : 'day') === p.lights['PAPI (all 6)'].mode;
  check(`A-CTL EnvState ${p.id.padEnd(15)}`, db.length === 0 && papiSame && c.inputs.night === p.tower_night,
    db.length ? db.join('; ') : `night ${c.inputs.night}, vis ${c.inputs.vis}, RVR ${c.inputs.rvr28r}, ceil ${c.inputs.ceil}, PAPI photocell ${c.papi.night ? 'night' : 'day'} = reference`);
}

// ------------------------------------------------------------------------------------------- table edge cases (V rules)
const W = { arr: { '28L': 'ILS', '28R': 'ILS' }, dep: ['1L', '1R'] };
const st = (o, k) => o[k] && o[k].step;
check('TBL 3-4-8 night: 3 SM -> step 2, 5 SM -> 2 ("3 to 5 inclusive"), 5.01 -> 1, 2.99 -> 3, 0.99 -> 4',
  st(controller(true, 3, null, null, W), 'HIRL 10L/28R') === 2 && st(controller(true, 5, null, null, W), 'HIRL 10L/28R') === 2 &&
  st(controller(true, 5.01, null, null, W), 'HIRL 10L/28R') === 1 && st(controller(true, 2.99, null, null, W), 'HIRL 10L/28R') === 3 && st(controller(true, 0.99, null, null, W), 'HIRL 10L/28R') === 4);
check('3-4-10 day: HIRL off at 2 SM, step 4 at 1.99, step 5 at 0.99',
  st(controller(false, 2, null, null, W), 'HIRL 10L/28R') === 0 && st(controller(false, 1.99, null, null, W), 'HIRL 10L/28R') === 4 && st(controller(false, 0.99, null, null, W), 'HIRL 10L/28R') === 5);
check('3-4-9: 28R ALSF-2 at 3/4 SM or RVR 4,000 ft, SSALR at 0.8 SM / RVR 4,200',
  controller(true, 0.75, null, null, W)['ALS 28R'].mode === 'ALSF-2' && controller(true, 2, 4000, null, W)['ALS 28R'].mode === 'ALSF-2' &&
  controller(true, 0.8, null, null, W)['ALS 28R'].mode === 'SSALR' && controller(true, 2, 4200, null, W)['ALS 28R'].mode === 'SSALR');
check('3-4-5 day: ALS off at 10 SM with no ceiling, on (step 2) with a 900-ft ceiling, on at 5 SM',
  controller(false, 10, null, null, W)['ALS 28R'].on === false && controller(false, 10, null, 900, W)['ALS 28R'].step === 2 && controller(false, 5, null, null, W)['ALS 28R'].on === true);
check('3-4-7 flashers: off at 3 SM, on at 2.9 SM for ILS / instrument / observed arrivals, off for a visual one',
  !controller(true, 3, null, null, W)['ALS 28R'].SFL && controller(true, 2.9, null, null, W)['ALS 28R'].SFL &&
  controller(true, 2.9, null, null, { arr: { '28R': 'instrument' }, dep: [] })['ALS 28R'].SFL && controller(true, 2.9, null, null, { arr: { '28R': 'observed' }, dep: [] })['ALS 28R'].SFL &&
  !controller(true, 2.9, null, null, { arr: { '28R': 'visual' }, dep: [] })['ALS 28R'].SFL);
check('ALS only for arrival ends; REIL only with the runway lights on (end in use)',
  !('ALS 19L' in controller(true, 10, null, null, W)) && !('REIL 10L' in controller(true, 10, null, null, W)) && 'REIL 1L' in controller(true, 10, null, null, W) && !('REIL 1L' in controller(false, 10, null, null, W)));
check('beacon by day below basic VFR (91.155: ceiling < 1,000 ft or visibility < 3 SM)',
  controller(false, 2.9, null, null, W).beacon.on && controller(false, 10, null, 900, W).beacon.on && !controller(false, 3, null, 1000, W).beacon.on);
// review finding truth1-9: 'P6000FT' = RVR greater than 6,000 ft (JO 7900.5E 13.12) must not satisfy "RVR 6,000 ft or less"
{ const d = buildEnvState(Date.parse('2026-01-10T14:00:00Z'), { reports: ['METAR KSFO 101356Z 00000KT 1SM R28R/P6000FT BR OVC004 08/08 A3001'], rwyOverride: { arr: { '28R': 'instrument' }, dep: [] } });
  const ci = controllerInputs(d); const a = controller(false, 1.0, ci.rvr28r, 400, { arr: { '28R': 'instrument' }, dep: [] })['ALS 28R'];
  check("TBL 3-4-5 with R28R/P6000FT at 1 SM by day: step 4 (20 %), as without RVR; RVR 6,000 -> step 5", rvrValue({ min_ft: 6000, min_prefix: 'P' }) === 6001 && ci.rvr28r === 6001 && a.step === 4 &&
    controller(false, 1.0, 6000, 400, { arr: { '28R': 'instrument' }, dep: [] })['ALS 28R'].step === 5 && rvrValue({ min_ft: 600, min_prefix: 'M' }) === 599, `P6000 -> ${ci.rvr28r}, step ${a.step}`); }
// review finding truth1-15: the drawn taxiway percentage (MITL 3-step) is carried in the controller output and the HUD
{ const night = controllerFromEnv(buildEnvState(Date.parse('2026-09-24T06:56:00Z'), { reports: ['METAR KSFO 240656Z 29005KT 10SM CLR 15/10 A2992'] }));
  check('taxiway: TBL 3-4-12 step 3 at night (5-step reference 5 %) is drawn as MITL 100 % and the HUD says so', night.out.taxiway.step === 3 && night.taxiwayDrawn.pct === MITL_PCT[3] && MITL_PCT[3] === 100, JSON.stringify(night.taxiwayDrawn)); }
console.log(`\nA-CTL: ${n - fails}/${n} checks passed`);
process.exit(fails ? 1 : 0);
