// Airfield-lighting controller (docs/research/environment_spec.md §5.3, step 2 / gate A-CTL): which light systems are on,
// at which intensity step, from the tower's point of view. Port of the reference controller `controller()` in
// tools/env/env_spec_checks.py (same keys, same values: node tools/env/test_controller.mjs reproduces its output for the
// 14 real-weather presets of tools/env/fixtures/env_presets.json). Renderer-agnostic, no DOM (Node and browser).
//
// Rules: FAA JO 7110.65BB chapter 3 section 4 "Airport Lighting"
// (https://www.faa.gov/air_traffic/publications/atpubs/atc_html/chap3_section_4.html; paragraph and table numbers as
// re-read for the spec, §2.3 item 2):
//   3-4-10 / 3-4-11, TBL 3-4-8   HIRL (+ RCL and TDZL, 3-4-14/3-4-15): on between sunset and sunrise for runways in use;
//                                by day when the surface visibility is less than 2 miles. Night steps: 4 < 1 SM,
//                                3: 1 to < 3, 2: 3 to 5 inclusive, 1: > 5. Day: 5 < 1 SM, 4: 1 to < 2.
//   3-4-5 / 3-4-6, TBL 3-4-5     ALS (ALSF-2): on at night when it serves the landing runway; by day when the ceiling is
//                                below 1,000 ft or the visibility 5 SM or less. Steps by visibility / RVR (RVR <= 6,000 ft
//                                or < 1 SM -> 5 by day, 3 at night: "At night, use step 4 or 5 only when requested").
//   3-4-8, TBL 3-4-7             MALSR / MALSF: 3-step (separate controls; SFO wiring NV, owner Q10 -> TBL 3-4-7, I).
//   3-4-9                        28R ALSF-2 when visibility <= 3/4 SM or RVR <= 4,000 ft, else SSALR mode.
//   3-4-7                        sequenced flashers only below 3 SM with instrument approaches to that runway.
//   3-4-2, TBL 3-4-1             REIL with the associated runway lights.
//   3-4-4                        PAPI continuous (photo-electric day/night, AC 150/5345-28H 3.3.6; night 20 %, Q6 I).
//   3-4-16, TBL 3-4-12           taxiway lights: night; by day below 1 SM.
//   3-4-18 + 14 CFR 91.155(c),(d)(1)  rotating beacon: night, or by day below basic VFR (ceiling < 1,000 ft or
//                                visibility < 3 SM). Not drawn (position unknown, Q1).
// Intensity of a step (percent of full output): HIRL / RCL / TDZ / taxiway CL 5-step 100/25/5/1.2/0.15 (AC 150/5340-30J
// 2.6.4.1); ALSF-2 steady 100/20/4/0.8/0.16 and flashers 100/20/2.3 (steady 4-5 -> high, 3 -> medium, 1-2 -> low); MALS
// steady 100/20/4 and flashers 100/10/2.3 (FAA Order JO 6850.2C Table 2-3; the 1:1 MALS step -> flasher step mapping is
// I); REIL style E effective 15,000 / 1,500 / 300 cd (AC 150/5345-51B Table 1; SFO's REIL style NV, Q5).
// SFO facility directives may override all of this (NV).

export const HIRL_PCT = { 5: 100, 4: 25, 3: 5, 2: 1.2, 1: 0.15 };          // AC 150/5340-30J 2.6.4.1 (V)
export const ALSF2_PCT = { 5: 100, 4: 20, 3: 4, 2: 0.8, 1: 0.16 };         // JO 6850.2C Table 2-3 (V)
export const MALS_PCT = { 3: 100, 2: 20, 1: 4 };                           // JO 6850.2C Table 2-3 (V)
export const ALSF2_SFL = { 5: 100, 4: 100, 3: 20, 2: 2.3, 1: 2.3 };        // T2-3 flashers high / medium / low (V)
export const MALS_SFL = { 3: 100, 2: 10, 1: 2.3 };                         // T2-3 MALS flashers 100/10/2.3 (V); 1:1 mapping I
export const REIL_CD = { 3: 15000, 2: 1500, 1: 300 };                      // AC 150/5345-51B Table 1 style E (V); style NV
export const ALS_OF = { '28R': 'ALSF2', '28L': 'MALSR', '19L': 'MALSF' };   // FAA NASR APT_RWY_END (V)
export const REIL_ENDS = ['10L', '1L', '1R'];                               // NASR RWY_END_LGTS_FLAG (V)
export const TDZ_ENDS = ['28R', '19L'];                                     // NASR (V)
export const RUNWAY_OF = { '10L': '10L/28R', '28R': '10L/28R', '10R': '10R/28L', '28L': '10R/28L', '1L': '1L/19R', '19R': '1L/19R', '1R': '1R/19L', '19L': '1R/19L' };
const MALS_NOTE = 'TBL 3-4-7 (separate MALSR controls); TBL 3-4-9 if slaved to the HIRL - SFO wiring NV';
const OBSTR_NOTE = 'photocell 60->35 fc north sky (AC 70/7460-1N 5.3); tower rule sunset-sunrise (3-4-17)';

/** Sequenced flashers need "instrument approaches" to the runway (3-4-7). The reference vectors state ILS / RNAV /
 *  visual per arrival end; the app's runway configuration (js/env/state.js runwayConfigFrom) says 'instrument',
 *  'unknown' (VFR, approach type not known) or 'observed' (ADS-B flow). The flasher rule only applies below 3 SM, where
 *  a visual approach is not possible (spec §3.5 item 4; VFR minimum ground visibility 3 SM, 14 CFR 91.155(d)(1)), so
 *  every arrival end that is not explicitly 'visual' counts as an instrument approach there (I). On the 14 preset
 *  vectors this is identical to the reference's `== 'ILS'` (every ALS end below 3 SM is ILS). */
export const isInstrumentApproach = (type) => type !== 'visual';

/** The reference controller (env_spec_checks.py controller(), same output keys and values).
 *  night: tower night (sunset..sunrise); vis: prevailing SM ('M' values reduced by 1 %); rvr28r: lowest 28R RVR (ft)
 *  or null; ceil: ceiling (ft) or null; rwy: {arr: {end: approach type}, dep: [ends]}. */
export function controller(night, vis, rvr28r, ceil, rwy) {
  const out = {};
  const arr = rwy.arr || {}, dep = rwy.dep || [];
  const inUse = [...new Set([...Object.keys(arr), ...dep].map(e => RUNWAY_OF[e]).filter(Boolean))].sort();
  const hasCeil = ceil != null;
  for (const r of inUse) {
    let st;
    if (night) st = vis < 1 ? 4 : vis < 3 ? 3 : vis <= 5 ? 2 : 1;      // TBL 3-4-8 night ("3 to 5 miles inclusive": 2)
    else if (vis < 2) st = vis < 1 ? 5 : 4;                           // 3-4-10 by day below 2 SM; TBL 3-4-8 day
    else st = 0;
    out['HIRL ' + r] = { step: st, pct: HIRL_PCT[st] ?? 0 };
  }
  for (const e of TDZ_ENDS) { const r = RUNWAY_OF[e]; if (inUse.includes(r)) out['TDZ ' + e] = { ...out['HIRL ' + r] }; }
  for (const [e, typ] of Object.entries(ALS_OF)) {
    if (!(e in arr)) continue;
    const on = night || (hasCeil && ceil < 1000) || vis <= 5;         // 3-4-5
    if (!on) { out['ALS ' + e] = { on: false }; continue; }
    const rv = e === '28R' ? rvr28r : null;
    const rvOk = (x) => rv != null && rv <= x;
    const sfl = vis < 3 && isInstrumentApproach(arr[e]);              // 3-4-7
    if (typ === 'ALSF2') {
      let st;
      if (night) st = (vis < 1 || rvOk(6000)) ? 3 : vis <= 3 ? 2 : 1;  // TBL 3-4-5 night (steps 4-5 only on request)
      else st = (vis < 1 || rvOk(6000)) ? 5 : vis < 3 ? 4 : vis < 5 ? 3 : 2; // >= 5 SM (low ceiling): step 2 per the NOTE (I)
      const mode = (vis <= 0.75 || rvOk(4000)) ? 'ALSF-2' : 'SSALR';  // 3-4-9
      out['ALS ' + e] = { on: true, mode, step: st, pct: ALSF2_PCT[st], SFL: sfl, SFL_pct: sfl ? ALSF2_SFL[st] : 0 };
    } else {
      const st = night ? (vis < 1 ? 3 : vis < 3 ? 2 : 1) : (vis < 2 ? 3 : 2);   // TBL 3-4-7; day > 5 SM low ceiling: 2 (I)
      out['ALS ' + e] = { on: true, mode: typ, step: st, pct: MALS_PCT[st], SFL: sfl, SFL_pct: sfl ? MALS_SFL[st] : 0, note: MALS_NOTE };
    }
  }
  for (const e of REIL_ENDS) {                                        // 3-4-2, TBL 3-4-1; only ends in use (I)
    const r = RUNWAY_OF[e];
    if ((e in arr || dep.includes(e)) && ((out['HIRL ' + r] || {}).step || 0) > 0) {
      const st = night ? (vis < 1 ? 3 : vis < 3 ? 2 : 1) : (vis < 2 ? 3 : 2);
      out['REIL ' + e] = { step: st, cd_eff: REIL_CD[st] };
    }
  }
  out['PAPI (all 6)'] = { mode: night ? 'night' : 'day', pct: night ? 20 : 100 };
  const tst = night ? (vis < 1 ? 4 : 3) : (vis < 1 ? 5 : 0);
  out.taxiway = { step: tst, pct: HIRL_PCT[tst] ?? 0 };
  out.beacon = { on: night || vis < 3 || (hasCeil && ceil < 1000) };
  out.obstruction = { on: night, note: OBSTR_NOTE };
  out.RWSL = { on: 'automatic, continuous (3-4-19); activation from traffic' };
  return out;
}

/** Controller inputs from an EnvState (js/env/state.js): tower night (USNO −50′), prevailing visibility (M values
 *  reduced by 1 %, none -> 10 SM as in the reference), lowest 28R RVR, ceiling, runway configuration (§3.5). */
export function controllerInputs(env) {
  const d = (env && env.wx && env.wx.decoded) || {};
  const v = d.visibility;
  const vis = v && v.sm != null ? v.sm * (v.prefix === 'M' ? 0.99 : 1.0) : 10.0;
  const rv = (d.rvr || []).find(r => r.runway === '28R');
  const rwy = env && env.runway ? { arr: env.runway.arr || {}, dep: env.runway.dep || [] } : { arr: {}, dep: [] };
  return { night: !!(env && env.towerNight), vis, rvr28r: rv ? rv.min_ft : null, ceil: d.ceiling_ft ?? null, rwy };
}

/** Controller output for an EnvState, plus the PAPI mode from the PAPI photocell (AC 150/5345-28H 3.3.6; EnvState
 *  photocell.papiNight, with its 55/30 fc hysteresis and 60 s delay) that the renderers use instead of the reference's
 *  tower-night shortcut (the two agree on all 14 presets). */
export function controllerFromEnv(env) {
  const inp = controllerInputs(env);
  const out = controller(inp.night, inp.vis, inp.rvr28r, inp.ceil, inp.rwy);
  const papiNight = env && env.photocell ? !!env.photocell.papiNight : inp.night;
  return { out, inputs: inp, papi: { night: papiNight, pct: papiNight ? 20 : 100 } };
}

/** One HUD line per system (?qa=env, spec §11.4: "the controller's steps"). */
export function controllerHud(ctl) {
  const o = ctl.out; const parts = [];
  for (const [k, v] of Object.entries(o)) {
    if (k.startsWith('HIRL ') || k.startsWith('TDZ ')) parts.push(`${k} ${v.step ? 'st' + v.step + ' ' + v.pct + '%' : 'off'}`);
    else if (k.startsWith('ALS ')) parts.push(v.on ? `${k} ${v.mode} st${v.step} ${v.pct}%${v.SFL ? ' SFL ' + v.SFL_pct + '%' : ''}` : `${k} off`);
    else if (k.startsWith('REIL ')) parts.push(`${k} st${v.step} ${v.cd_eff} cd`);
  }
  parts.push(`PAPI ${ctl.papi.night ? 'night' : 'day'} ${ctl.papi.pct}%`, `taxiway ${o.taxiway.step ? 'st' + o.taxiway.step : 'off'}`, `beacon ${o.beacon.on ? 'on (not drawn, Q1)' : 'off'}`);
  return parts.join(' · ');
}
