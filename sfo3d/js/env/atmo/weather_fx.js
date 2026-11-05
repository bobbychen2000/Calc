// Precipitation, lightning and wet-surface models (environment spec §4.6, §4.7, §7.5, §7.6). Pure ES module (no DOM):
// js/three/rain.js, js/three/sky.js and js/three/ground.js take their parameters from here; tools/env/test_sky.mjs
// checks them (A-RAIN, A-LTG, A-WET unit halves). Tags: V verified · I inferred · NV unknown · 2nd secondary.
import { sstep } from './sky_model.js';

const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
// ------------------------------------------------------------------------------------------------ 1. rain / drizzle
// Marshall–Palmer drop-size distribution N(D) = N0 exp(−ΛD), Λ = 4.1 R^−0.21 mm⁻¹ (Garg & Nayar 2007 quote, V);
// N0 = 8,000 m⁻³ mm⁻¹ (2nd / NV: the spec verifier found the quoted formula gives half). Fall speed v = 200 √a
// (a = radius in m; Gunn & Kinzer via Garg & Nayar, V). Streak = v × 1/60 s (spec §4.6, V + I). Counted drops:
// D ≥ 0.5 mm (= js/env/wx/metar.js drops_per_m3_gt_0p5mm; smaller drops are the drizzle / mist term, which lives in σ).
export const MP_N0 = 8000, MP_A = 4.1, MP_B = -0.21, D_MIN_MM = 0.5, STREAK_T = 1 / 60;
// Tier budgets (spec §7.5, I): high 60k, medium 30k, low 12k particles; the budget is reached at REF_RATE (the top of
// JO 7900.5E Table 9-4's heavy class as used by js/env/wx/metar.js, 25 mm/h), so every lighter rain keeps the
// Marshall–Palmer count ratio (A-RAIN) and only rain above 25 mm/h is capped.
export const RAIN_BUDGET = { ultra: 60000, high: 60000, medium: 30000, low: 12000 };
export const REF_RATE = 25.0;
export const BOX_HALF = 40;             // camera-attached box half-size (m), spec §7.5 "~40 m radius" (I)
export const mpLambda = (R) => MP_A * Math.pow(Math.max(R, 0.01), MP_B);
export const dropsAbove = (R, Dmin = D_MIN_MM) => { const L = mpLambda(R); return MP_N0 / L * Math.exp(-L * Dmin); };
export const medianVolumeDiameter = (R) => 3.67 / mpLambda(R);
export const fallSpeed = (Dmm) => 200 * Math.sqrt(Dmm / 2 / 1000);
// Drizzle: drops < 0.5 mm, "dense fine mist, no streaks, 1–2 m/s" (spec §4.6, I): 1.5 m/s, 0.3 mm, 60 % of the budget
export const DRIZZLE_V = 1.5, DRIZZLE_D = 0.3, DRIZZLE_FRAC = 0.6;

/** Particle parameters for the renderer from EnvState.precip (null = none). tier: quality tier name. */
export function rainParams(precip, tier = 'high', windToMS = [0, 0]) {
  if (!precip || (precip.kind !== 'rain' && precip.kind !== 'drizzle')) return null;
  const budget = RAIN_BUDGET[tier] || RAIN_BUDGET.high;
  if (precip.kind === 'drizzle') {
    return { kind: 'drizzle', count: Math.round(budget * DRIZZLE_FRAC), D0mm: DRIZZLE_D, vFall: DRIZZLE_V, streak: 0, streaks: false,
      rate: precip.rateMmH, wind: windToMS, half: BOX_HALF, densityPerM3: null, density: budget / RAIN_BUDGET.high, tag: 'I (drizzle count / speed)' };
  }
  const R = Math.max(0.05, precip.rateMmH || 1);
  const n = dropsAbove(R), nRef = dropsAbove(REF_RATE);
  const D0 = medianVolumeDiameter(R), v = fallSpeed(D0);
  return { kind: 'rain', count: Math.round(budget * Math.min(1, n / nRef)), capped: n > nRef, D0mm: D0, vFall: v, streak: v * STREAK_T, streaks: true,
    rate: R, showery: !!precip.showery, wind: windToMS, half: BOX_HALF, densityPerM3: n,
    // density: this tier's share of the high-tier count; js/three/rain.js divides each streak's weight by it, so the
    // drawn rain looks equally dense on every tier (review look1-8, I)
    density: budget / RAIN_BUDGET.high, tag: 'V (Marshall–Palmer Λ, v) + 2nd (N0) + I (budget scale)' };
}
/** Shower modulation (spec §4.6 "cellular: modulate rate in space and time", I): a slow 0.35..1 factor (cells passing
 *  over the airport every ~4 min). */
export const showerFactor = (t) => 0.675 + 0.325 * Math.sin(t * 2 * Math.PI / 240) * Math.sin(t * 2 * Math.PI / 97 + 1.3);

// ------------------------------------------------------------------------------------------------ 2. lightning
// Rate classes (JO 7900.5E Table 13-7, V): OCNL < 1/min, FRQ about 1-6/min, CONS > 6/min; EnvState lightning.perMin
// holds the class midpoints (0.5 / 3.5 / 8, I). Distance (ALDARS, JO 7900.5E 13.28b, V): TS "at the station" ≤ 5 NM,
// VC 5-10 NM, DSNT 10-30 NM. Direction from the remark's compass points (±22.5° each, I), ALQDS all round, OHD
// overhead. Timing: quasi-regular intervals (mean 60/rate s, ±40 % uniform jitter, I) so a 5-minute window stays inside
// its class; each flash = 1-4 strokes 40-80 ms apart (I), total 0.2-0.4 s. Brightness NV (spec §4.6): QA-tuned.
export const LTG_CLASS = { OCNL: [0, 1], FRQ: [1, 6], CONS: [6, Infinity] };
const NM = 1852;
const DIRS = { N: 0, NE: 45, E: 90, SE: 135, S: 180, SW: 225, W: 270, NW: 315 };
/** Sectors [{az0, az1, d0, d1}] (deg compass, m) from EnvState.lightning. */
export function lightningSectors(L) {
  const out = [];
  for (const r of (L && L.where) || []) {
    const toks = String(r.loc || '').split(/[\s-]+/).filter(Boolean);
    const dsnt = toks.includes('DSNT'), vc = toks.includes('VC'), ohd = toks.includes('OHD'), all = toks.includes('ALQDS');
    const [d0, d1] = dsnt ? [10 * NM, 30 * NM] : vc ? [5 * NM, 10 * NM] : ohd ? [0, 2 * NM] : L.atStation ? [0, 5 * NM] : [5 * NM, 10 * NM];
    const dirs = toks.filter(t => t in DIRS).map(t => DIRS[t]);
    if (all || !dirs.length) out.push({ az0: 0, az1: 360, d0, d1 });
    else for (const a of dirs) out.push({ az0: a - 22.5, az1: a + 22.5, d0, d1 });
  }
  if (!out.length && L && L.perMin > 0) out.push({ az0: 0, az1: 360, d0: L.atStation ? 0 : 5 * NM, d1: L.atStation ? 5 * NM : 10 * NM });
  return out;
}
function rng(seed) { let s = seed >>> 0 || 1; return () => { s ^= s << 13; s >>>= 0; s ^= s >> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; }; }
/** Flashes in [t0, t1) (s of data time) for EnvState.lightning: [{t, az, dist, strokes: [dt...], type}] —
 *  deterministic in (seed, t) so every renderer frame and every tab sees the same flashes. */
export function lightningFlashes(L, t0, t1, seed = 1) {
  if (!L || !(L.perMin > 0)) return [];
  const sec = lightningSectors(L); const mean = 60 / L.perMin;
  const types = [...new Set(((L.where || [])[0] || {}).types || ['IC'])];
  const out = [];
  // the process is anchored on a fixed epoch grid so a window [t0, t1) gives the same flashes whoever asks
  const k0 = Math.floor(t0 / mean) - 1;
  for (let k = k0; ; k++) {
    const r = rng(seed * 7919 + k * 104729 + 17);
    const t = k * mean + mean * (0.5 + 0.8 * (r() - 0.5));   // one flash per slot, jittered ±40 %
    if (t >= t1) break; if (t < t0) continue;
    const s = sec[Math.floor(r() * sec.length) % sec.length];
    const az = ((s.az0 + (s.az1 - s.az0) * r()) % 360 + 360) % 360;
    const dist = s.d0 + (s.d1 - s.d0) * Math.sqrt(r());
    const n = 1 + Math.floor(r() * 4); const strokes = [0]; for (let i = 1; i < n; i++) strokes.push(strokes[i - 1] + 0.04 + 0.04 * r());
    out.push({ t, az, dist, strokes, type: types[Math.floor(r() * types.length) % types.length] });
  }
  return out;
}
/** Flash brightness envelope at time t for flashes around it (0..1): each stroke a 60 ms exponential (I). */
export function flashLevel(flashes, t) {
  let e = 0, best = null;
  for (const f of flashes) for (const s of f.strokes) { const dt = t - (f.t + s); if (dt >= 0 && dt < 0.4) { const v = Math.exp(-dt / 0.06); if (v > e) { e = v; best = f; } } }
  return { level: e, flash: best };
}

// ------------------------------------------------------------------------------------------------ 3. wet surfaces
// Lagarde 2013 ("Water drop 3b - physically based wet surfaces", spec §4.7, V): diffuse albedo × lerp(1, lerp(1, 0.2,
// porosity), wet); wet surfaces smoother with a higher specular; puddles a flat water layer (F0 0.02); drying: the
// specular (surface film) disappears first, the diffuse (water in the pores) stays darker. Porosity: asphalt medium
// 0.5 (spec, I), concrete 0.3 (I). State machine constants are NV (spec: calibrate on owner-approved photo / video
// sequences, Q16): film saturates after 0.2 mm of rain, pores after 0.5 mm; puddles = accumulated mm above 1 mm minus
// 2 mm/h drainage, full at 3 mm; drying time constants film 20 min, pores 60 min, ×(1 + sun + wind) (I).
export const POROSITY = { asphalt: 0.5, concrete: 0.3 };
export const WET_FILM_MM = 0.2, WET_PORE_MM = 0.5, PUDDLE_START_MM = 1.0, PUDDLE_FULL_MM = 3.0, DRAIN_MM_H = 2.0;
export const TAU_FILM_S = 20 * 60, TAU_PORE_S = 60 * 60;
export const diffuseFactor = (porosity, wet) => 1 + ((1 + (0.2 - 1) * porosity) - 1) * clamp(wet, 0, 1);
/** Initial state from a report (spec §4.7: wet = 1 if precipitation now; 0.5 if it ended in the last hour; else 0). */
export function wetStart(st) {
  const s = st && st.surface ? st.surface.wet : 0;
  return { film: s, pore: s, water: s >= 1 ? PUDDLE_START_MM + 0.5 : 0, t: st ? st.tEnv : 0 };
}
/** Advance the state to EnvState st (data time); returns {film, pore, water, puddle, t}. A jump of the data clock
 *  (> 10 min or backwards) restarts from the start rule. */
export function wetStep(prev, st) {
  if (!prev || !(st.tEnv > prev.t) || st.tEnv - prev.t > 600e3) { const s = wetStart(st); return { ...s, puddle: puddleOf(s.water) }; }
  const dt = (st.tEnv - prev.t) / 1000; const P = st.precip; const raining = P && (P.kind === 'rain' || P.kind === 'drizzle');
  let { film, pore, water } = prev;
  if (raining) {
    const mm = (P.rateMmH || 0) * dt / 3600;
    film = Math.min(1, film + mm / WET_FILM_MM); pore = Math.min(1, pore + mm / WET_PORE_MM);
    water = Math.max(0, water + mm - DRAIN_MM_H * dt / 3600);
  } else {
    const sunUp = Math.max(0, Math.sin((st.sun.el || 0) * Math.PI / 180)) * (st.sunVisibleP ?? 1);
    const k = 1 + 2 * sunUp + Math.min(1, (st.wind && st.wind.speed || 0) / 10);
    film *= Math.exp(-dt * k / TAU_FILM_S); pore *= Math.exp(-dt * k / TAU_PORE_S);
    water = Math.max(0, water - DRAIN_MM_H * k * dt / 3600);
  }
  return { film, pore, water, puddle: puddleOf(water), t: st.tEnv };
}
export const puddleOf = (mm) => sstep(PUDDLE_START_MM, PUDDLE_FULL_MM, mm);
/** Material response (JS mirror of the ground shader, js/three/ground.js): albedo factor, roughness for a dry
 *  roughness r0, and the puddle state, for a surface of the given porosity. */
// PUDDLE_ALBEDO: the diffuse under standing water = the wet (porosity-darkened) albedo, i.e. no further darkening (Lagarde
// 2013 "flooded" state keeps the wet diffuse and adds the water's specular, V for the model, the value I). Review look1-3:
// the former 0.35 made puddles dark stains, darker than the wet film where they should mirror the sky / lamps.
export const ROUGH_FILM = 0.22, ROUGH_PUDDLE = 0.03, PUDDLE_ALBEDO = 1.0;
export function wetMaterial(r0, porosity, W, puddleMask = 1) {
  const pud = clamp(W.puddle * puddleMask, 0, 1);
  const albedoK = diffuseFactor(porosity, W.pore) * (1 + (PUDDLE_ALBEDO - 1) * pud);
  const rough = r0 + (ROUGH_FILM - r0) * clamp(W.film, 0, 1);
  return { albedoK, rough: rough + (ROUGH_PUDDLE - rough) * pud, puddle: pud };
}
