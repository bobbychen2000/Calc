// Exposure for the new renderer (environment spec §8): metering of the HDR frame, EV100, adaptation, clamp and
// compensation, the display calibration and the pre-exposure scale. Pure ES module (no DOM): js/three/renderer3.js
// calls it with a small luminance readback of the frame; tools/env/test_sky.mjs checks it (A-EXP unit half).
//
//   EV100 = log2(L_avg · 100 / K), K = 12.5 (reflected-light meter constant; Frostbite PBR §5.1, ISO 2720) — V
//   exposure = 1 / (1.2 · 2^EV100) (saturation-based sensitivity, Frostbite listing 26-27) — V
//   metering: log-average, centre-weighted, excluding the top 2 % and the bottom 50 % of pixels (Filament "Automatic
//     exposure": histogram method) — V method, I parameters
//   adaptation: L += (L_new − L)(1 − e^(−Δt/τ)), τ 1.5 s brightening, 3.5 s darkening (Filament / Pattanaik 2000:
//     τ ≈ 1-2 s / 3-4 s) — V form, I values; snap on camera cuts and environment changes
//   clamp EV100 ∈ [2, 16] (sun_night §6.3, I), and a compensation darkening below Sun −4° (spec §8 "so night stays
//     night and lights bloom", I, QA-tuned): the lower clamp rises to EV_NIGHT_FLOOR at Sun ≤ −10°.
import { LUX_PER_UNIT, sstep } from './sky_model.js';

export const K_METER = 12.5, EV_MIN = 2, EV_MAX = 16;
export const TAU_UP = 1.5, TAU_DOWN = 3.5;
export const EXCL_LOW = 0.50, EXCL_HIGH = 0.02;
// Night floor of the clamp: EV100 4.6 = the spec's floodlit-apron target (54 lx on 18 % grey; spec §8 table, M):
// at night an average darker than a floodlit apron is not brightened further (I).
export const EV_NIGHT_FLOOR = 4.6;
// Display calibration (I): the reviewed day grade of the new renderer (engine track round 2: DAY_GAIN 0.80 × the
// app's 0.45 = exposure 0.36 in sky units at the snapshot, whose natural target is EV100 15.0, spec §10) is kept:
// exposure = DISPLAY_K · LUX_PER_UNIT / (1.2 · 2^EV100) with DISPLAY_K = 0.36 · 1.2 · 2^15 / LUX_PER_UNIT = 2.12.
export const DISPLAY_K = 0.36 * 1.2 * Math.pow(2, 15.0) / LUX_PER_UNIT;

export const ev100FromLuminance = (Lcd) => Math.log2(Math.max(Lcd, 1e-9) * 100 / K_METER);
export const luminanceFromEV100 = (ev) => Math.pow(2, ev) * K_METER / 100;
/** Exposure (multiplier of sky-unit radiance -> display-referred input of the tone mapper) for an EV100. */
export const exposureForEV = (ev) => DISPLAY_K * LUX_PER_UNIT / (1.2 * Math.pow(2, ev));
export const evForExposure = (x) => Math.log2(DISPLAY_K * LUX_PER_UNIT / (1.2 * x));

/** Meter a w×h array of luminances (sky units, linear): centre-weighted log average of the pixels between the 50th
 *  and the 98th percentile. Weight = 1 + 2·(1 − r²) inside the inscribed ellipse (r = normalised distance from the
 *  centre), 1 outside (I). Returns {Lcd, ev100, n}. */
export function meter(lumUnits, w, h) {
  const n = w * h; const idx = new Array(n);
  for (let i = 0; i < n; i++) idx[i] = i;
  idx.sort((a, b) => lumUnits[a] - lumUnits[b]);
  const i0 = Math.floor(n * EXCL_LOW), i1 = Math.max(i0 + 1, Math.ceil(n * (1 - EXCL_HIGH)));
  let s = 0, ws = 0;
  for (let k = i0; k < i1; k++) {
    const i = idx[k]; const x = (i % w + 0.5) / w * 2 - 1, y = (Math.floor(i / w) + 0.5) / h * 2 - 1; const r2 = x * x + y * y;
    const wt = 1 + 2 * Math.max(0, 1 - r2);
    s += wt * Math.log2(Math.max(lumUnits[i], 1e-12) * LUX_PER_UNIT); ws += wt;
  }
  const Lcd = ws > 0 ? Math.pow(2, s / ws) : 1e-9;
  return { Lcd, ev100: ev100FromLuminance(Lcd), n: i1 - i0 };
}
/** Lower clamp of EV100 for a true Sun elevation (deg). */
export const evLow = (sunElTrue) => EV_MIN + (EV_NIGHT_FLOOR - EV_MIN) * sstep(-4, -10, sunElTrue);
/** Clamped EV100. */
export const clampEV = (ev, sunElTrue) => Math.min(EV_MAX, Math.max(evLow(sunElTrue), ev));
/** One adaptation step of the metered luminance (cd/m²) over dt seconds; snap = true jumps. */
export function adapt(Lprev, Lnew, dt, snap = false) {
  if (snap || !(Lprev > 0)) return Lnew;
  const tau = Lnew > Lprev ? TAU_UP : TAU_DOWN;
  // in log space (perceptual), the same exponential form
  const a = 1 - Math.exp(-Math.max(0, dt) / tau);
  return Math.pow(2, Math.log2(Lprev) + (Math.log2(Lnew) - Math.log2(Lprev)) * a);
}
/** Pre-exposure (Filament): the scale applied to every emitter before shading so that the half-float frame holds
 *  display-range values (night: the 0.0005 lx floor is 7.5e-8 sky units, below the half-float normal range 6.1e-5).
 *  A power of two near the exposure, changed only when it is off by more than 2 stops (TRAA history and the bloom mips
 *  then see one scale step at a time). */
export function preExposure(prev, expo) {
  const want = Math.pow(2, Math.round(Math.log2(Math.max(expo, 1e-6))));
  if (!(prev > 0)) return want;
  return Math.abs(Math.log2(expo / prev)) > 2 ? want : prev;
}
