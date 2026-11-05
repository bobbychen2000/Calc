// Photometry for the airfield and aircraft light sprites (docs/research/environment_spec.md §4.10, §5.4, §6; step 2).
// Pure functions, no DOM (Node tests: tools/env/test_lights.mjs, gates A-VIS1, A-PAPI1, A-FLASH1).
//
// 1. Light visibility (§4.10). Allard's law: the illuminance at the eye from a point light is E = I·T/d² with
//    T = exp(−∫σ ds) (Rasmussen et al. 1999 eqs. 22–24, V); a light is seen when E ≥ E_T. E_T = 4.12e-4 lx by day and
//    6.99e-7 lx at night, fitted with the ASOS σ inversion to the FAA's own table (AC 70/7460-1N Table B-1 + B.3, M;
//    js/env/state.js ET_DAY_LUX / ET_NIGHT_LUX, log-blended by the ASOS night weight). The sprite core is multiplied by
//    the visibility factor v = smoothstep(0, 1, log10(E/E_T)/0.3): 0 at E_T, 1 at 2·E_T (fade band = factor 2, spec I).
// 2. Optical depth through the EnvState slabs (§4.4, §7.3: piecewise-constant σ(y); the same σ field as the scene fog).
// 3. Beam pattern B(θh, θv) (§5.4, I interpolation on V limits): 1 inside the AC 150/5345-46F main-beam ellipse, a
//    log-linear fall to 0.1 at the 10 % ellipse, then 0 (with a short fade, I, so lights do not pop).
// 4. PAPI (§5.4): white above / red below each LHA's aiming angle, transition 3′ wide at the beam centre and 5′ at the
//    edges (AC 150/5345-28H §3.2.1, V); isocandela contours of Fig 3-1 as read for lighting_spec.json (V ±0.25°);
//    LED units emit only within ±10.5° azimuth (JO 6850.2C 504b, V).
// 5. Flashes (§5.4 "Flash rendering", 14 CFR 25.1401(e), V): the effective intensity of a flash of duration t with
//    constant instantaneous intensity I_f is I_eff = I_f·t / (0.2 + t) (the Blondel–Rey relation 25.1401(e) prescribes:
//    I_e = ∫I(t)dt / (0.2 + t2 − t1)). A flash drawn for n frames of duration dt is perceived as I_f·n·dt/(0.2 + n·dt), so
//    I_f is solved for the target at the ACTUAL frame time (e.g. 400 cd effective -> 5,200 cd for one 60 Hz frame).

export const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
export const smoothstep = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
const DEG = Math.PI / 180;

// ------------------------------------------------------------------------------------------------ 1. Allard
/** Illuminance at the eye (lx) from intensity I (cd) at distance d (m) through uniform extinction σ (m⁻¹). */
export const allardE = (I, sigma, d) => I * Math.exp(-sigma * d) / (d * d);
/** Visual range (m) of a light of I cd for threshold ET (lx): the d where I·exp(−σd)/d² = ET (bisection). */
export function visualRange(I, sigma, ET) {
  let lo = 0.01, hi = 1e7;
  if (allardE(I, sigma, lo) <= ET) return 0;
  for (let k = 0; k < 200; k++) { const m = Math.sqrt(lo * hi); if (allardE(I, sigma, m) > ET) lo = m; else hi = m; }
  return lo;
}
/** Sprite visibility factor (§4.10 "Rendering the threshold on a display", I): 0 at E ≤ E_T, 1 at E ≥ 2·E_T. */
export const visibilityFactor = (E, ET) => (E > ET ? smoothstep(0, 1, Math.log10(E / ET) / 0.3) : 0);

// ------------------------------------------------------------------------------------------------ 2. optical depth
/** Optical depth along the segment a -> b ([x, y, z] m) through piecewise-constant slabs [{y0, y1, sigma}] (EnvState
 *  atm.slabs; the lowest slab extends down below the ground, e.g. to ALS lights on the light plane); sigmaAbove for the
 *  parts of the path outside every slab (clear air, js/env/state.js SIGMA_CLEAR). */
export function opticalDepth(a, b, slabs, sigmaAbove) {
  const dx = b[0] - a[0], dy = b[1] - a[1], dz = b[2] - a[2];
  const L = Math.sqrt(dx * dx + dy * dy + dz * dz); if (!(L > 0)) return 0;
  const ylo = Math.min(a[1], b[1]), yhi = Math.max(a[1], b[1]), h = yhi - ylo;
  let tau = 0, covered = 0;
  for (let i = 0; i < (slabs ? slabs.length : 0); i++) {
    const s = slabs[i]; const y0 = i === 0 ? -Infinity : s.y0, y1 = s.y1;
    const f = h < 1e-6 ? (a[1] >= y0 && a[1] < y1 ? 1 : 0) : Math.max(0, Math.min(yhi, y1) - Math.max(ylo, y0)) / h;
    tau += s.sigma * f * L; covered += f;
  }
  return tau + (sigmaAbove || 0) * Math.max(0, 1 - covered) * L;
}

// ------------------------------------------------------------------------------------------------ 3. beam
/** Main / 10 % beam of a photometry entry of LIGHTING_SPEC.fixtures for a colour: {main, ten} or null (omni / NV). */
export function beamOf(F, colourName) {
  if (!F) return null;
  if (Array.isArray(F.beams)) { const b = F.beams.find(x => x.colour === colourName) || F.beams[0]; return b && b.main ? { main: b.main, ten: b.ten || null } : null; }
  return F.main ? { main: F.main, ten: F.ten || null } : null;
}
function ellR(e, dh, dv) {
  if (e.circle_deg != null) return Math.hypot(dh, dv) / e.circle_deg;
  const hc = (e.h[0] + e.h[1]) / 2, ha = Math.max(1e-3, (e.h[1] - e.h[0]) / 2), vc = (e.v[0] + e.v[1]) / 2, va = Math.max(1e-3, (e.v[1] - e.v[0]) / 2);
  return Math.hypot((dh - hc) / ha, (dv - vc) / va);
}
/** Relative intensity B in [0, 1] at horizontal angle dh (deg, positive toward the toe-in side, i.e. the runway CL for
 *  edge / TDZ lights) and vertical angle dv (deg above the horizontal) for a beam {main, ten}. Omni beams (|h| = 180)
 *  only test the vertical range. Without a 10 % curve the main ellipse scaled ×1.5 is used (I). */
export function beamFactor(beam, dh, dv) {
  if (!beam) return 1;
  const M = beam.main;
  if (M.h && M.h[1] - M.h[0] >= 360) { dh = (M.h[0] + M.h[1]) / 2; }     // omnidirectional in azimuth
  const r1 = ellR(M, dh, dv);
  if (r1 <= 1) return 1;
  const T = beam.ten;
  const rt = T ? ellR(T.h && T.h[1] - T.h[0] >= 360 ? { ...T, h: M.h } : T, dh, dv) : r1 / 1.5;
  if (rt < 1) { const f = clamp((r1 - 1) / Math.max(1e-6, r1 / rt - 1), 0, 1); return Math.pow(10, -f); }
  return 0.1 * Math.max(0, 1 - (rt - 1) / 0.5);                          // I: fade over half the 10 % radius
}

// ------------------------------------------------------------------------------------------------ 4. PAPI
export const PAPI_LED_HALF_AZ = 10.5;                   // JO 6850.2C 504b / lighting_spec rules.papi.coverage (V)
export const PAPI_TRANSITION_ARCMIN = [3, 5];           // AC 150/5345-28H 3.2.1: 3′ at the beam centre, 5′ at the edges (V)
/** Fraction of white (0 = red, 1 = white) seen from elevation angle elDeg (deg above the horizontal at the LHA) for an
 *  LHA aimed at aimDeg, at horizontal angle dhDeg from the beam axis (transition width 3′ -> 5′ linear in |dh| over
 *  the ±10° beam, I). */
export function papiWhite(aimDeg, elDeg, dhDeg = 0) {
  const w = (PAPI_TRANSITION_ARCMIN[0] + (PAPI_TRANSITION_ARCMIN[1] - PAPI_TRANSITION_ARCMIN[0]) * clamp(Math.abs(dhDeg) / 10, 0, 1)) / 60;
  return clamp((elDeg - aimDeg) / w + 0.5, 0, 1);
}
function inStadium(dh, dv, A, B) {          // stadium of half-width A (h) and half-height B (v), A >= B; circle when A = B
  if (A < B) { const t = A; A = B; B = t; const u = dh; dh = dv; dv = u; }
  const x = Math.max(0, Math.abs(dh) - (A - B));
  return x * x + dv * dv <= B * B;
}
/** PAPI isocandela (AC 150/5345-28H Fig 3-1 via LIGHTING_SPEC.fixtures.PAPI_LHA.isocandela): intensity of the white and
 *  red parts at (dh, dv) deg from the beam axis (dv measured from the aiming angle). Step function: the value of the
 *  innermost contour containing the point (minimum intensities, I). LED cut-off at ±10.5°. */
export function papiCd(iso, dh, dv) {
  if (Math.abs(dh) > PAPI_LED_HALF_AZ) return { white: 0, red: 0 };
  for (const c of iso) {
    const A = (c.h[1] - c.h[0]) / 2, B = (c.v[1] - c.v[0]) / 2;
    if (inStadium(dh, dv, A, B)) return { white: c.white, red: c.red };
  }
  return { white: 0, red: 0 };
}
/** LHA pattern seen from elevation elDeg: array of 'W' / 'R' / 'P' (pink, inside the transition) per LHA, LHA 1 (nearest
 *  the runway) first. */
export function papiPattern(aims, elDeg, dhDeg = 0) {
  return aims.map(a => { const w = papiWhite(a, elDeg, dhDeg); return w >= 0.999 ? 'W' : w <= 0.001 ? 'R' : 'P'; });
}

// ------------------------------------------------------------------------------------------------ 5. flashes
export const BR_C = 0.2;   // s, 14 CFR 25.1401(e) (Blondel–Rey constant)
export const effectiveIntensity = (If, t) => If * t / (BR_C + t);
export const peakForEffective = (Ieff, t) => Ieff * (BR_C + t) / t;
/** Per-frame flash gain for a light flashing with period P (s), first flash at `phase` (s) and flash duration `on` (s),
 *  for the frame drawn at time t whose predecessor was drawn at tPrev (the image is shown for about dt = t − tPrev).
 *  Returns 0 (dark) or the factor g by which the TARGET effective intensity is multiplied for this frame, so that the
 *  drawn flash meets the target (Blondel–Rey at the actual frame time):
 *   - short flash (on < dt): drawn in the one frame whose interval (tPrev, t] contains the flash start, g = (0.2+dt)/dt;
 *   - long flash: drawn in every frame whose instant t lies in [tk, tk + on); at least n = floor(on/dt) such frames,
 *     g = (0.2 + n·dt)/(n·dt), so the perceived effective intensity is never below the target. */
export function flashGain(tPrev, t, P, phase, on) {
  const dt = t - tPrev; if (!(dt > 0) || !(P > 0)) return 0;
  const k = Math.floor((t - phase) / P), tk = k * P + phase;
  if (on < dt) return (tk > tPrev && tk <= t) ? (BR_C + dt) / dt : 0;
  if (t >= tk && t < tk + on) { const n = Math.max(1, Math.floor(on / dt + 1e-9)); return (BR_C + n * dt) / (n * dt); }
  return 0;
}
/** Is the light lit at time t (for QA counting): t within [tk, tk + on). */
export const flashLit = (t, P, phase, on) => { const k = Math.floor((t - phase) / P); return t - (k * P + phase) < on; };
// ------------------------------------------------------------------------------------------------ 6. sprite units
// A sprite record {p, c, i, s} drawn by js/three/lights.js gives the eye illuminance E = i × LAMP_M × 0.408 s² / d² sky
// units at the night calibration, i.e. i × 13.16 s² cd (js/three/renderer3.js LAMP_M = (20 lx / 6,665 lx per sky unit) /
// 0.62; the core exp(−22 r²) integrates to 0.143 of the quad, divided by the shader's 1.6² × 0.35: 0.408; M, code read).
// Physical records (phys: true) are drawn at that calibration day and night by renderer3 (lights.js `fixed`).
export const CD_PER_LAMP_S2 = (133300 / 20) * ((20 / (133300 / 20)) / 0.62) * (0.143 / 0.35);
// cap (lamp units): RGBA16F headroom of the old renderer's sprite pass, which draws lamp units unscaled (I; the step-3
// pre-exposure lifts it). It only binds for landing lights pointing at the camera (> ~32,000 cd at s = 0.35).
export const I_CAP = 20000;
export const lampUnits = (cd, s) => Math.min(I_CAP, cd / (CD_PER_LAMP_S2 * s * s));
export { DEG };
