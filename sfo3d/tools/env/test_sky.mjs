// Environment step 3-4 unit gates (docs/research/environment_spec.md §11.3; docs/research/environment_impl.md §3):
// the numeric halves of A-SUN (render: shadow azimuth, the drawn Sun disc at sunset), A-MOON, A-EXP, A-FOG, A-CLD,
// A-RAIN, A-WET, A-LTG, run on the JS mirrors of the new renderer's shader formulas (js/env/atmo/*.js) with the
// EnvState of the 14 real-weather presets. No GPU. Usage: node tools/env/test_sky.mjs [GATE ...]
import { buildEnvState } from '../../js/env/state.js';
import { ENV_PRESETS, presetById, presetRunway } from '../../js/env/presets.js';
import { skyState, sunPosition, SFO } from '../../js/env/ephemeris.js';
import { rng } from '../../js/math.js';
import * as SM from '../../js/env/atmo/sky_model.js';
import * as EX from '../../js/env/atmo/exposure.js';
import * as WX from '../../js/env/atmo/weather_fx.js';

const want = new Set(process.argv.slice(2));
const run = (g) => !want.size || want.has(g);
let fails = 0, checks = 0; const out = {};
const ok = (c, msg) => { checks++; if (!c) { fails++; console.log('FAIL ' + msg); } return c; };
const env = (id, extra = {}) => { const p = presetById(id); return buildEnvState(Date.parse(p.time_utc), { mode: 'snapshot', overridden: true, reports: [p.metar], live: true, rwyOverride: presetRunway(p), groundY: 3, ...extra }); };
const f = (x, n = 3) => Number(x).toFixed(n);

// ------------------------------------------------------------------------------------------------ A-SUN (render half)
if (run('A-SUN')) {
  const r = {};
  // 1. a vertical pole's shadow under the renderer's light (the renderer takes EnvState sun.dir unchanged: renderer3
  //    setSun(L.sunDir), L.sunDir = env.sunDir = EnvState sun.dir) points to the Sun azimuth + 180 deg
  let worst = 0;
  for (const p of ENV_PRESETS) { const st = env(p.id); if (st.sun.el <= 0) continue; const a = SM.shadowAzimuth(st.sun.dir), e = (st.sun.az + 180) % 360; const d = Math.abs(((a - e) % 360 + 540) % 360 - 180); worst = Math.max(worst, d); }
  ok(worst < 1, `shadow azimuth within 1 deg of the ephemeris (worst ${worst})`); r.shadowAzWorstDeg = +worst.toExponential(2);
  // 2. sunset of 23 Sep 2026 (spec: 19:04:33 PDT = 02:04:33Z on 24 Sep, USNO 19:05). The sky shader draws the disc
  //    at the APPARENT (Bennett-refracted) direction with radius acos(0.99998918) (js/three/sky.js); the USNO sunset
  //    is the UPPER LIMB on the horizon (centre 50' below, airless). Find both instants of the drawn disc.
  const t0 = Date.parse('2026-09-24T01:50:00Z'); const R = Math.acos(0.99998918) * 180 / Math.PI;
  const at = (fn) => { let a = t0, b = t0 + 40 * 60e3; for (let i = 0; i < 50; i++) { const m = (a + b) / 2; if (fn(sunPosition(new Date(m), SFO)) > 0) a = m; else b = m; } return new Date((a + b) / 2); };
  const tCentre = at(s => s.el), tLimb = at(s => s.el + R), tUSNO = at(s => s.elTrue + 50 / 60);
  const usnoSpec = Date.parse('2026-09-24T02:04:33Z');
  r.drawnRadiusDeg = +R.toFixed(4); r.ephemerisSemidiameterDeg = +sunPosition(tLimb, SFO).semidiameter.toFixed(4);
  r.centreOnHorizon = tCentre.toISOString(); r.upperLimbOnHorizon = tLimb.toISOString(); r.usno50arcmin = tUSNO.toISOString();
  r.upperLimbMinusSpecMin = +((tLimb - usnoSpec) / 60e3).toFixed(2); r.centreMinusSpecMin = +((tCentre - usnoSpec) / 60e3).toFixed(2);
  ok(Math.abs(tLimb - usnoSpec) < 60e3, `drawn upper limb on the horizon within 1 min of the USNO sunset (${r.upperLimbMinusSpecMin} min)`);
  ok(Math.abs(R - r.ephemerisSemidiameterDeg) < 0.01, `drawn disc radius ${f(R, 4)} deg = solar semidiameter ${r.ephemerisSemidiameterDeg}`);
  out['A-SUN'] = r;
}

// ------------------------------------------------------------------------------------------------ A-MOON
if (run('A-MOON')) {
  const r = [];
  for (const p of ENV_PRESETS) {
    const st = env(p.id); if (st.moon.el < 0) continue;
    const D = SM.moonDisc(st), s = SM.moonDiscStats(D, 240);
    const dLimb = Math.abs(((s.brightLimbFromUpDeg - st.moon.brightLimbZenithAngle) % 360 + 540) % 360 - 180);
    const dirErr = Math.acos(Math.min(1, D.dir[0] * st.moon.dir[0] + D.dir[1] * st.moon.dir[1] + D.dir[2] * st.moon.dir[2])) * 180 / Math.PI;
    r.push({ id: p.id, el: +st.moon.el.toFixed(2), az: +st.moon.az.toFixed(2), litEphem: +st.moon.lit.toFixed(4), litDrawn: +s.litFraction.toFixed(4), limbEphem: +st.moon.brightLimbZenithAngle.toFixed(1), limbDrawn: +s.brightLimbFromUpDeg.toFixed(1), dirErrDeg: dirErr, discCdM2: Math.round(D.cdm2), radiusDeg: +(D.rad * 180 / Math.PI).toFixed(4) });
    ok(Math.abs(s.litFraction - st.moon.lit) < 0.02, `${p.id}: drawn lit fraction ${f(s.litFraction)} vs ephemeris ${f(st.moon.lit)}`);
    // the bright-limb direction is undefined near full / new Moon (lit fraction > 0.97 or < 0.03)
    if (st.moon.lit < 0.97 && st.moon.lit > 0.03) ok(dLimb < 5, `${p.id}: bright limb ${f(s.brightLimbFromUpDeg, 1)} vs ephemeris ${f(st.moon.brightLimbZenithAngle, 1)} deg`);
    ok(dirErr < 0.5, `${p.id}: Moon direction`);
    if (st.moon.el > 10) ok(D.cdm2 > 500 && D.cdm2 < 20000, `${p.id}: disc luminance ${Math.round(D.cdm2)} cd/m2 plausible`); // low Moon: C171 extinction (airmass)
  }
  out['A-MOON'] = r;
}

// ------------------------------------------------------------------------------------------------ A-EXP (unit half)
if (run('A-EXP')) {
  const r = { presets: [] };
  for (const p of ENV_PRESETS) {
    const st = env(p.id); const cal = SM.sunCalibration(st);
    const k = cal.k;
    let row = { id: p.id, sunEl: +st.sun.el.toFixed(2), c171ClearLux: +cal.c171Lux.toPrecision(4), modelLux: +cal.modelLux.toPrecision(4), k: k == null ? null : +k.toFixed(3) };
    if (k != null) {
      const L = SM.modelLight(st.sun.dir, 21e-6, 20 * k); const C = SM.cloudAdjust(L, st);
      row.renderedGhiLux = +(C.ghi * SM.LUX_PER_UNIT).toPrecision(4); row.c171Lux = +st.natural.E.toPrecision(4);
      row.err = +(row.renderedGhiLux / (st.natural.E - st.natural.moon - 0.0005 / st.natural.D) - 1).toFixed(4);
    }
    row.ev100Target = +st.exposure.ev100Target.toFixed(2); row.ev100Clamped = +EX.clampEV(st.exposure.ev100Target, st.sun.elTrue).toFixed(2);
    r.presets.push(row);
  }
  const noon = r.presets.find(x => x.id === 'noon');
  ok(Math.abs(noon.err) <= 0.2, `noon rendered GHI ${noon.renderedGhiLux} lx within 20 % of C171 ${noon.c171Lux} lx (err ${noon.err})`);
  r.noonUncalibratedErr = +(noon.modelLux / noon.c171ClearLux - 1).toFixed(3);
  for (const x of r.presets) if (x.err != null) ok(Math.abs(x.err) < 0.02, `${x.id}: calibrated GHI vs C171 (${x.err})`);
  // spec §10 EV100 targets (natural light before the clamp)
  const T = { noon: 15.3, snapshot: 15.0, marine_layer: 12.0, dusk: 0.7, night_clear: -5.0, dawn: 2.6 };
  for (const [id, ev] of Object.entries(T)) { const x = r.presets.find(y => y.id === id); ok(Math.abs(x.ev100Target - ev) < 0.15, `${id}: EV100 target ${x.ev100Target} vs spec ${ev}`); }
  // night: the clamp holds (>= 2, and the night floor below Sun -10 deg)
  for (const x of r.presets) ok(x.ev100Clamped >= 2 - 1e-9, `${x.id}: clamped EV100 >= 2`);
  // metering: a uniform 18 % grey frame under E meters EV100 = ev100ForIlluminance(E); the 2 % top / 50 % bottom
  // exclusion ignores a sun disc and a black half
  { const E = 71000, n = 64 * 36; const Lu = 0.18 * E / Math.PI / SM.LUX_PER_UNIT; const A = new Float32Array(n).fill(Lu); const m1 = EX.meter(A, 64, 36);
    const B = A.slice(); for (let i = 0; i < n / 2; i++) B[i] = 0; for (let i = n / 2; i < n / 2 + 20; i++) B[i] = 1e4; const m2 = EX.meter(B, 64, 36);
    r.meterGrey = +m1.ev100.toFixed(3); r.meterGreyBlackHalfSun = +m2.ev100.toFixed(3);
    ok(Math.abs(m1.ev100 - 15.0) < 0.05, `meter: 18 % grey at 71 klx = EV ${f(m1.ev100)} (15.0)`); ok(Math.abs(m2.ev100 - 15.0) < 0.05, `meter ignores the black half and the sun disc (${f(m2.ev100)})`); }
  // sky exclusion (renderer3 leaves out the background when >= 10 % of the frame is geometry): 60 % bright sky
  { const E = 8725, n = 64 * 36; const Lg = 0.18 * E / Math.PI / SM.LUX_PER_UNIT; const A = new Float32Array(n).fill(Lg), X = new Uint8Array(n);
    for (let i = 0; i < n * 0.6; i++) { A[i] = 5.5 * Lg; X[i] = 1; } const all = EX.meter(A, 64, 36), geo = EX.meter(A, 64, 36, X);
    r.meterSkyIncluded = +all.ev100.toFixed(2); r.meterSkyExcluded = +geo.ev100.toFixed(2);
    ok(Math.abs(geo.ev100 - 11.97) < 0.05 && all.ev100 > geo.ev100 + 2, `sky excluded: ${f(geo.ev100, 2)} (target 11.97) vs included ${f(all.ev100, 2)}`); }
  // display calibration: EV 15.0 -> the reviewed day exposure 0.36
  ok(Math.abs(EX.exposureForEV(15.0) - 0.36) < 1e-9, 'display calibration');
  // pre-exposure keeps the night-sky floor (0.0005 lx -> luminance 0.0005/pi cd/m2 on 18 %... the sky floor itself
  // 174 ucd/m2) inside the half-float normal range (>= 6.1e-5) once multiplied
  { const ev = EX.clampEV(-5, -49); const x = EX.exposureForEV(ev); const pre = EX.preExposure(null, x); const floor = 174e-6 / SM.LUX_PER_UNIT;
    r.nightPre = pre; r.nightFloorPreExposed = floor * pre; ok(floor < 6.1e-5 && floor * pre > 6.1e-5 * 0.01, `night floor ${floor.toExponential(2)} units -> ${(floor * pre).toExponential(2)} pre-exposed`); }
  // adaptation: tau 1.5 s up / 3.5 s down
  { let L = 1; for (let i = 0; i < 90; i++) L = EX.adapt(L, 1024, 1 / 60); r.adapt1s = +Math.log2(L).toFixed(2); ok(Math.abs(Math.log2(L) - 10 * (1 - Math.exp(-1.5 / 1.5))) < 0.05, 'adaptation tau up'); }
  out['A-EXP'] = r;
}

// ------------------------------------------------------------------------------------------------ A-FOG
if (run('A-FOG')) {
  const r = {};
  // day, ifr_mist_day (3/4 SM): a black target at the reported visibility, eye 2 m, horizontal, contrast vs the horizon
  { const st = env('ifr_mist_day'); const S = SM.renderSlabs(st); const V = st.atm.visM;
    const T = SM.fogTransmittance(S, [0, 5, 0], [V, 5, 0]); r.ifrMistDay = { visM: +V.toFixed(1), sigma: st.atm.sigmaSurface, w: st.photocell.asosNightW, contrast: +T.toFixed(4), slabs: S.map(s => [+s.y0.toFixed(1), +s.y1.toFixed(1), +s.sigma.toExponential(3)]) };
    ok(Math.abs(T - 0.055) <= 0.02, `ifr_mist_day: black target at ${f(V, 0)} m has contrast ${f(T, 4)} (5.5 % +- 2 %)`); }
  // marine layer: nothing above the OVC005 base (152 m above the field) visible from below the deck
  { const st = env('marine_layer'); const S = SM.renderSlabs(st); const base = st.clouds.find(c => c.cover === 'OVC').base;
    const T = SM.fogTransmittance(S, [0, 60, 0], [800, base + 400, 0]); const Tin = SM.fogTransmittance(S, [0, base + 20, 0], [120, base + 20, 0]);
    r.marineLayer = { base: +base.toFixed(1), slabs: S.map(s => [s.kind, +s.y0.toFixed(1), +s.y1.toFixed(1), +s.sigma.toExponential(3)]), TthroughDeck: T, TinCloud120m: +Tin.toFixed(4) };
    ok(Math.abs(base - (3 + 500 * 0.3048)) < 0.01, 'OVC005 base at 152.4 m + GROUND_Y'); ok(T < 1e-4, `transmittance through the deck ${T.toExponential(2)}`);
    ok(Tin < 0.02 && Tin > 1e-4, `in-cloud visual range 40-120 m (T over 120 m ${f(Tin, 4)})`); }
  // predawn fog M1/4SM VV002: fog top 200 ft; no see-through cap: T -> 0 over long paths
  { const st = env('predawn_fog'); const S = SM.renderSlabs(st); const T = SM.fogTransmittance(S, [0, 5, 0], [3000, 5, 0]);
    r.predawnFog = { slabs: S.map(s => [s.kind, +s.y0.toFixed(1), +s.y1.toFixed(1), +s.sigma.toExponential(3)]), T3km: T };
    ok(T < 1e-6, `no residual see-through (T over 3 km ${T.toExponential(2)}; the old cap kept 3 %)`); ok(Math.abs(S[0].y1 - (3 + 200 * 0.3048)) < 0.01, 'surface fog to the VV height 200 ft (the obscuration above it)'); }
  // clear day: 10SM is a lower bound -> clear air (sigma <= 1.8e-4, spec §4.3)
  { const st = env('noon'); r.noonSigma = st.atm.sigmaSurface; ok(st.atm.sigmaSurface <= 1.8e-4, 'noon sigma is the clear-air bound'); }
  // ---- review round 1 (truth1-3/-5/-6, look1-2): one σ field, partial obscuration, VV obscuration, horizontal structure
  const at = (raw, t = '2026-01-26T12:43:00Z') => buildEnvState(Date.parse(t), { mode: 'snapshot', overridden: true, reports: [raw], live: true, groundY: 3 });
  const Th = (S, az, d, y = 5) => SM.fogTransmittance(S, [0, y, 0], [d * Math.sin(az * Math.PI / 180), y, -d * Math.cos(az * Math.PI / 180)]);
  const rangeOf = (S, I, ET, eyeY = 8) => { let lo = 1, hi = 20000; const E = (d) => I * Math.exp(-SM.slabTau(S, [0, eyeY, 0], [d, 3.3, 0])) / (d * d + (eyeY - 3.3) ** 2); if (E(lo) < ET) return 0; for (let k = 0; k < 100; k++) { const m = Math.sqrt(lo * hi); if (E(m) > ET) lo = m; else hi = m; } return lo; };
  // FG BKN000 (night_fog): the 000 layer is the fog's partial obscuration, no cloud slab; a 2,500 cd light reaches the
  // same 536 m as in predawn_fog (same M1/4SM fog; spec §4.10 example; was 198 m with the BKN000 slab)
  { const st = env('night_fog'), st2 = env('predawn_fog'); const S = SM.renderSlabs(st), S2 = SM.renderSlabs(st2);
    const rN = rangeOf(S, 2500, st.lightVis.ET), rP = rangeOf(S2, 2500, st2.lightVis.ET); r.nightFog = { slabs: S.map(s => [s.kind, +s.y0.toFixed(1), +s.y1.toFixed(1), +s.sigma.toExponential(3)]), range2500cd: Math.round(rN) };
    ok(!S.some(s => s.isCloud) && S.length === 1 && Math.abs(S[0].y1 - (3 + 200 * 0.3048)) < 0.01, 'night_fog FG BKN000: one fog slab to 200 ft, no cloud slab at the ground');
    ok(Math.abs(rN - 536) < 6 && Math.abs(rN - rP) < 1, `night_fog HIRL step 4 (2,500 cd) visual range ${Math.round(rN)} m = predawn_fog ${Math.round(rP)} m (spec 536 m)`); }
  // FG with a low ceiling: the fog reaches the ceiling (no clear gap under BKN003)
  { const S = SM.renderSlabs(at('KSFO 261256Z 00000KT 1/4SM FG BKN003 09/09 A3030'));
    ok(Math.abs(S[0].y1 - (3 + 300 * 0.3048)) < 0.01 && S[1] && Math.abs(S[1].y0 - S[0].y1) < 0.01, `FG BKN003: fog to 300 ft, the cloud slab starts there (${S.map(s => s.kind + ' ' + s.y0.toFixed(0) + '-' + s.y1.toFixed(0)).join(', ')})`); }
  // VV002 (predawn_fog): the sky, the Moon disc and the Moon light are hidden by the obscuration above the VV height
  { const st = env('predawn_fog'); const S = SM.renderSlabs(st); const ob = S.find(s => /^obscuration/.test(s.kind));
    const bg = (cy, el) => { let tau = 0; S.forEach((s, k) => { const y0 = k === 0 ? -1e6 : s.y0; const inside = cy >= y0 && cy < s.y1; if (!s.isCloud || inside) { const sg = s.isCloud ? s.sigma : Math.max(s.sigma - SM.SIGMA_CLEAR, 0); tau += sg * Math.max(s.y1 - Math.max(cy, y0), 0) / Math.max(Math.sin(el * Math.PI / 180), 1e-4); } }); return Math.exp(-tau); };
    const Tz = bg(7.5, 90), Tm = bg(7.5, st.moon.el), Tb = SM.fogBeamT(S, st.moon.el);
    r.vv = { obscuration: ob && [+ob.y0.toFixed(1), +ob.y1.toFixed(1), +ob.sigma.toExponential(3)], bgZenith: Tz, bgMoon: Tm, moonBeamT: Tb };
    ok(ob && Math.abs(ob.sigma - 3 / (200 * 0.3048)) < 1e-6, 'VV002: obscuration slab above 200 ft with σ = 3 / VV');
    ok(Tz < 1e-3 && Tm < 1e-3 && Tb < 1e-3, `VV002: sky from the ground T ${Tz.toExponential(1)} (was 0.37), Moon direction ${Tm.toExponential(1)} (was 0.28), Moon beam ${Tb.toExponential(1)}`); }
  // horizontal structure: BCFG + VIS NW 1/2 (10SM prevailing) is not clear air; NW at 1 km denser than SE
  { const st = at('KSFO 261243Z 19003KT 10SM BCFG FEW002 BKN004 09/08 A3030 RMK AO2 VIS NW 1/2 T00890078'); const S = SM.renderSlabs(st);
    let m = 0; for (let a = 0; a < 360; a += 10) m += Th(S, a, 1000) / 36; const tNW = Th(S, 315, 1000), tSE = Th(S, 135, 1000);
    r.bcfg = { horiz: st.atm.horiz && { patch: st.atm.horiz.patch, lobes: st.atm.horiz.lobes.map(l => l.what) }, meanT1km: +m.toFixed(3), tNW: +tNW.toExponential(2), tSE: +tSE.toFixed(3) };
    ok(st.atm.horiz && st.atm.horiz.patch && st.atm.horiz.lobes.length === 1 && m < 0.9 && tNW < 0.05 && tSE > 10 * tNW, `10SM BCFG VIS NW 1/2: mean T over 1 km ${f(m)} (was 0.97 clear air), NW ${tNW.toExponential(1)}, SE ${f(tSE)}`); }
  { const st = at('KSFO 070925Z COR 02004KT 3SM R28R/1600VP6000FT PRFG BKN000 11/11 A3019 RMK AO2 VIS NE E M1/4 PRFG BKN000 T01110111', '2025-01-07T09:25:00Z'); const S = SM.renderSlabs(st);
    const tE = Th(S, 67.5, 600), tW = Th(S, 247.5, 600); r.prfg = { tE: +tE.toExponential(2), tW: +tW.toFixed(3), slabs: S.map(s => s.kind) };
    ok(!S.some(s => s.isCloud) && tE < 1e-3 && tW > 30 * tE, `3SM PRFG BKN000 VIS NE E M1/4: toward ENE over 600 m T ${tE.toExponential(1)}, toward WSW ${f(tW)} (no BKN000 cloud slab)`); }
  { const st = at('KSFO 150256Z 29021KT 9SM VCFG FEW003 14/12 A2989 RMK AO2 SLP120 FG IN GAP W T01390117 55000', '2016-08-15T02:56:00Z'); const S = SM.renderSlabs(st);
    const tW = Th(S, 270, 8000, 30), tE = Th(S, 90, 8000, 30), tW2 = Th(S, 270, 2500, 30); r.gap = { tW8km: +tW.toExponential(2), tE8km: +tE.toFixed(3), tW2500m: +tW2.toFixed(3) };
    ok(tW < 1e-3 && tE > 0.2 && tW2 > 0.2, `FG IN GAP W: a bank to the W beyond 3 km (T over 8 km W ${tW.toExponential(1)}, E ${f(tE)}; 2.5 km W ${f(tW2)})`); }
  { const st = at('KSFO 131956Z 03007KT 1/2SM R28R/2200VP6000FT BCFG VV002 16/14 A3017 RMK AO2 TWR VIS 6 SLP216 T01610139', '2016-11-13T19:56:00Z'); const S = SM.renderSlabs(st);
    r.twrVis = S.map(s => [s.kind, +s.y0.toFixed(1), +s.y1.toFixed(1), +s.sigma.toExponential(2)]);
    ok(S.length >= 3 && S[0].sigma > 5 * S[1].sigma && Math.abs(S[0].y1 - 33) < 0.01, `TWR VIS 6 over a 1/2SM surface: σ ${S[0].sigma.toExponential(1)} below 30 m, ${S[1].sigma.toExponential(1)} above (cab level)`); }
  { const raw = 'KSFO 171624Z 00000KT 1SM R28R/3000VP6000FT BR FEW003 FEW008 BKN016 18/16 A2998 RMK AO2 VIS 1/2V2 1/2 VIS 3SM VIS E 1SM T01780161';
    const sg = []; for (let k = 0; k <= 10; k++) sg.push(at(raw, new Date(Date.parse('2020-09-17T16:24:00Z') + k * 60e3).toISOString()).atm.sigmaSurface);
    const lo = Math.min(...sg), hi = Math.max(...sg); r.visVariable = { sigmaMin: +lo.toExponential(2), sigmaMax: +hi.toExponential(2) };
    ok(hi / lo > 3, `VIS 1/2V2 1/2: σ swings ${lo.toExponential(1)} .. ${hi.toExponential(1)} over 10 min of data time`); }
  out['A-FOG'] = r;
}

// ------------------------------------------------------------------------------------------------ A-CLD
// the app's cloud texture (js/world/textures.js makeCloudTexture(11), js/live/world.js): same generator, CPU copy
function cloudTexture(seed = 11) {
  const N = 512; const R = rng(seed);
  const P = 8; const grid = []; for (let o = 0; o < 7; o++) { const p = P << o; const g = new Float32Array(p * p); for (let i = 0; i < p * p; i++) g[i] = R(); grid.push({ p, g }); }
  const noise = (x, y, o) => { const { p, g } = grid[o]; const X = x * p, Y = y * p; const i = Math.floor(X), j = Math.floor(Y); const fx = X - i, fy = Y - j; const u = fx * fx * (3 - 2 * fx), v = fy * fy * (3 - 2 * fy);
    const a = g[((j % p + p) % p) * p + ((i % p + p) % p)], b = g[((j % p + p) % p) * p + (((i + 1) % p + p) % p)], c = g[(((j + 1) % p + p) % p) * p + ((i % p + p) % p)], d = g[(((j + 1) % p + p) % p) * p + (((i + 1) % p + p) % p)];
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v; };
  const data = new Uint8Array(N * N);
  for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) { let s = 0, a = 0.5, n = 0; for (let o = 0; o < 7; o++) { s += a * noise(x / N, y / N, o); n += a; a *= 0.52; } s /= n; data[y * N + x] = Math.max(0, Math.min(255, (s - 0.2) / 0.6 * 255)); }
  return data;
}
if (run('A-CLD')) {
  const tex = cloudTexture(11); const N = 512; const H = SM.histogram8(tex); const dist = SM.detailDistribution(H);
  const samp = (u, v) => { u = (u % 1 + 1) % 1 * N - 0.5; v = (v % 1 + 1) % 1 * N - 0.5; const i = Math.floor(u), j = Math.floor(v), fx = u - i, fy = v - j; const g = (a, b) => tex[((b % N + N) % N) * N + ((a % N + N) % N)] / 255; return g(i, j) * (1 - fx) * (1 - fy) + g(i + 1, j) * fx * (1 - fy) + g(i, j + 1) * (1 - fx) * fy + g(i + 1, j + 1) * fx * fy; };
  const r = { textureSum: tex.reduce((a, b) => a + b, 0), presets: [] }; const R = rng(5);
  for (const p of ENV_PRESETS) {
    const st = env(p.id); const L = SM.cloudLayers(st, dist);
    const rep = (st.wx.decoded.sky || []).filter(s => s.cover && s.cover !== 'VV' && s.cover !== 'CLR' && s.cover !== 'SKC' && s.height_ft != null && s.height_ft >= SM.MIN_CLOUD_FT);
    ok(L.length === Math.min(rep.length, SM.MAX_CLOUD_LAYERS), `${p.id}: ${L.length} layers drawn for ${rep.length} reported`);
    const row = { id: p.id, layers: [] };
    let shadowMean = 0; const NS = 20000;
    const dens = [];
    for (const l of L) {
      ok(Math.abs(l.baseY - (3 + l.baseFt * 0.3048)) < 1e-6, `${p.id}: base of ${l.cover}${l.baseFt}`);
      // area mean of the shader's density over a large area (random points over 50 x 50 km)
      let m = 0; const D = [];
      for (let i = 0; i < NS; i++) { const x = (R() - 0.5) * 50000, z = (R() - 0.5) * 50000; const u = x / l.scale + l.off[0], v = z / l.scale + l.off[1];
        const n = samp(u, v) + SM.CLOUD_DETAIL * (samp(u * 7.3 + 0.43, v * 7.3 + 0.71) - 0.5); const d = SM.sstep(l.thr - SM.CLOUD_RAMP, l.thr + SM.CLOUD_RAMP, n) * l.opacity; m += d; D.push(d); }
      m /= NS; dens.push(D);
      row.layers.push({ cover: l.cover, baseFt: l.baseFt, own: +l.own.toFixed(3), drawn: +m.toFixed(3), thr: +l.thr.toFixed(3), slab: l.slab, kind: l.kind });
      ok(Math.abs(m - l.own) <= 0.1, `${p.id}: ${l.cover}${l.baseFt} coverage ${f(m)} vs own ${f(l.own)}`);
    }
    // sun transmittance through all layers (product of 1 - d, independent layers at different offsets) vs sunVisibleP
    for (let i = 0; i < NS; i++) { let t = 1; for (const D of dens) t *= 1 - D[i]; shadowMean += t; }
    row.sunVisibleDrawn = +(shadowMean / NS).toFixed(3); row.sunVisibleP = st.sunVisibleP;
    if (L.length) ok(Math.abs(row.sunVisibleDrawn - st.sunVisibleP) <= 0.1, `${p.id}: mean sun transmittance ${row.sunVisibleDrawn} vs sunVisibleP ${st.sunVisibleP}`);
    r.presets.push(row);
  }
  out['A-CLD'] = r;
}

// ------------------------------------------------------------------------------------------------ A-RAIN
if (run('A-RAIN')) {
  const r = {};
  const light = WX.rainParams({ kind: 'rain', rateMmH: 1 }, 'high'), heavy = WX.rainParams({ kind: 'rain', rateMmH: 10 }, 'high');
  const mpRatio = WX.dropsAbove(1) / WX.dropsAbove(10), drawnRatio = light.count / heavy.count;
  r.light = light; r.heavy = heavy; r.mpRatio = +mpRatio.toFixed(4); r.drawnRatio = +drawnRatio.toFixed(4);
  ok(Math.abs(drawnRatio / mpRatio - 1) <= 0.25, `drop count ratio light/heavy ${f(drawnRatio, 4)} vs Marshall–Palmer ${f(mpRatio, 4)}`);
  for (const p of [light, heavy]) { const want = WX.fallSpeed(p.D0mm) / 60; ok(Math.abs(p.streak / want - 1) <= 0.25, `streak ${f(p.streak, 4)} m = v(D0) / 60 s`); }
  ok(Math.abs(WX.fallSpeed(WX.medianVolumeDiameter(1)) - 4.2) < 0.15 && Math.abs(WX.fallSpeed(WX.medianVolumeDiameter(10)) - 5.4) < 0.15, 'fall speed 4.2 / 5.4 m/s at 1 / 10 mm/h (spec §4.6)');
  const dz = WX.rainParams({ kind: 'drizzle', rateMmH: 0.25 }, 'high'); r.drizzle = dz; ok(!dz.streaks && dz.streak === 0, 'drizzle has no streaks');
  // presets: rain_day +RA 8 mm/h, squall_night 7.62, drizzle_night, ts_evening -TSRA
  r.presets = {}; for (const id of ['rain_day', 'squall_night', 'drizzle_night', 'ts_evening']) { const st = env(id); const q = WX.rainParams(st.precip, 'high'); r.presets[id] = q && { kind: q.kind, rate: q.rate, count: q.count, D0mm: +q.D0mm.toFixed(3), vFall: +q.vFall.toFixed(2), streak: +q.streak.toFixed(4) }; ok(!!q, `${id}: precipitation drawn`); }
  out['A-RAIN'] = r;
}

// ------------------------------------------------------------------------------------------------ A-WET
if (run('A-WET')) {
  const r = {};
  const W1 = { film: 1, pore: 1, puddle: 0 };
  for (const [s, por] of Object.entries(WX.POROSITY)) { const m = WX.wetMaterial(0.85, por, W1); r[s] = m; ok(m.albedoK >= 0.2 && m.albedoK <= 0.9, `wet ${s} diffuse albedo ${f(m.albedoK)} of dry (0.2-0.9)`); ok(m.rough < 0.85, `wet ${s} smoother`); }
  const P = WX.wetMaterial(0.85, 0.5, { film: 1, pore: 1, puddle: 1 }); r.puddle = P; ok(P.rough <= 0.05, `puddle roughness ${P.rough} (mirror: PMREM level 0)`);
  const Fm = WX.wetMaterial(0.85, 0.5, W1); ok(P.albedoK >= Fm.albedoK - 1e-9, `puddle diffuse ${f(P.albedoK)} not below the wet film's ${f(Fm.albedoK)} (review look1-3: puddles never darker than the film)`);
  // drying after rain: the specular (film) fades before the diffuse (pores)
  const st0 = env('rain_day'); let W = WX.wetStep(null, st0); const dry = { ...st0, precip: null, surface: { wet: 0 } };
  const trace = []; for (let k = 1; k <= 12; k++) { W = WX.wetStep(W, { ...dry, tEnv: st0.tEnv + k * 5 * 60e3 }); trace.push([k * 5, +W.film.toFixed(3), +W.pore.toFixed(3), +W.puddle.toFixed(3)]); }
  r.drying = trace; const half = trace.find(x => x[1] < 0.5); ok(half && half[2] > half[1] + 0.1, `drying: film ${half && half[1]} below half while pores ${half && half[2]}`);
  // start rule
  ok(WX.wetStart(env('rain_day')).film === 1 && WX.wetStart(env('noon')).film === 0, 'start rule (spec §4.7)');
  out['A-WET'] = r;
}

// ------------------------------------------------------------------------------------------------ A-LTG
if (run('A-LTG')) {
  const r = {};
  const st = env('ts_evening'); const L = st.lightning; r.report = L; r.sectors = WX.lightningSectors(L);
  const t0 = 1e6; const F = WX.lightningFlashes(L, t0, t0 + 300, 42);
  const perMin = F.length / 5; r.flashes5min = F.length; r.perMin = perMin;
  const cls = WX.LTG_CLASS.FRQ; ok(perMin >= cls[0] && perMin <= cls[1], `ts_evening FRQ: ${perMin} flashes/min in 1-6`);
  const inSE = F.every(x => x.az >= 112.5 - 1e-9 && x.az <= 157.5 + 1e-9); ok(inSE, 'every flash in the SE sector (112.5-157.5 deg)');
  r.az = [Math.min(...F.map(x => x.az)), Math.max(...F.map(x => x.az))].map(v => +v.toFixed(1));
  // every 5-minute window of an hour stays in its class, for OCNL / FRQ / CONS
  for (const [c, rate] of [['OCNL', 0.5], ['FRQ', 3.5], ['CONS', 8]]) {
    let worst = null; for (let w = 0; w < 12; w++) { const n = WX.lightningFlashes({ ...L, perMin: rate }, t0 + w * 300, t0 + (w + 1) * 300, 7).length / 5; const [a, b] = WX.LTG_CLASS[c]; if (!(n >= a && (c === 'OCNL' ? n < b : n <= b) && (c !== 'CONS' || n > 6))) worst = n; }
    ok(worst == null, `${c}: every 5-min window in class${worst != null ? ' (fails at ' + worst + '/min)' : ''}`);
  }
  // determinism (two tabs / frames see the same flashes)
  ok(JSON.stringify(WX.lightningFlashes(L, t0 + 60, t0 + 120, 42)) === JSON.stringify(F.filter(x => x.t >= t0 + 60 && x.t < t0 + 120)), 'flash schedule is a pure function of time');
  out['A-LTG'] = r;
}

// ------------------------------------------------------------------------------------------------ A-WIND (unit half)
// Windsocks are not drawn (Q15: positions unpublished). The extension law (AC 150/5345-27F: moves at 3 kt, full at
// 15 kt; linear between, I) and the TRUE wind direction (JO 7900.5E 13.10) that drives the rain slant and the water:
if (run('A-WIND')) {
  const r = {};
  for (const [id, want] of [['dawn', 0], ['dusk', (13 - 3) / 12], ['squall_night', 1], ['night_fog', 0], ['noon', (8 - 3) / 12]]) { const st = env(id); r[id] = { fromTrue: st.wind.fromTrue, kt: +(st.wind.speed / 0.514444).toFixed(1), sockExt: st.wind.sockExt }; ok(Math.abs(st.wind.sockExt - want) < 1e-3, `${id}: windsock extension ${st.wind.sockExt} (${f(want)})`); }
  // the rain falls downwind of the METAR true direction: squall 22036G63KT -> velocity towards 040 deg true
  const st = env('squall_night'); const fr = st.wind.fromTrue * Math.PI / 180, sp = st.wind.speed; const P = WX.rainParams(st.precip, 'high', [-Math.sin(fr) * sp, Math.cos(fr) * sp]);
  const to = (Math.atan2(P.wind[0], -P.wind[1]) * 180 / Math.PI + 360) % 360; r.squallRainToDeg = +to.toFixed(2);
  ok(Math.abs(to - (st.wind.fromTrue + 180) % 360) < 1e-6, `rain drifts towards ${f(to, 1)} deg = METAR true ${st.wind.fromTrue} + 180`);
  out['A-WIND'] = r;
}

if (process.env.JSON_OUT) { const fs = await import('fs'); fs.writeFileSync(process.env.JSON_OUT, JSON.stringify(out, null, 1)); }
if (process.argv.includes('--print') || process.env.PRINT) console.log(JSON.stringify(out, null, 1));
console.log(`${fails ? 'FAIL' : 'PASS'}: ${checks - fails}/${checks} checks (${[...(want.size ? want : ['A-SUN', 'A-MOON', 'A-EXP', 'A-FOG', 'A-CLD', 'A-RAIN', 'A-WET', 'A-LTG', 'A-WIND'])].join(', ')})`);
process.exit(fails ? 1 : 0);
