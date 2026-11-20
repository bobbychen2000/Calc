// forked from sfo3d@e3218d6 js/env/lighting/photometry.js
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
// sha3d: sfo3d's airfield-fixture photometry (beamOf / beamFactor: FAA AC 150/5345-46F beam patterns; papiWhite / papiCd /
// papiPattern, PAPI_LED_HALF_AZ, PAPI_TRANSITION_ARCMIN: FAA AC 150/5345-28H / JO 6850.2C PAPI values) is removed - no FAA
// lighting constants in sha3d. The airfield-lighting package brings CAAC MH 5001-2021 photometry. What remains is generic
// (Allard / Koschmieder visibility, Blondel-Rey flashes, lamp units, aureole) and used by the aircraft lights and the sky.
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
// ------------------------------------------------------------------------------------------------ 7. fog aureole
// Spec §4.10: "Fog adds a forward-scatter aureole ∝ I·(1 − T) with angular radius growing with optical depth" (I,
// QA-tuned; review finding look1-1: the light sprites had no aureole, lights in fog looked as on a clear night). The part
// of the light scattered out of the direct beam (1 − T) that still travels towards the eye: fog droplets scatter
// strongly forward (asymmetry g ≈ 0.85 for ~10 µm droplets: textbook Mie value, I), so after an optical depth τ the
// forward-scattered light keeps ≈ exp(−(1 − g) τ) (transport / diffusion approximation, I); drawn as a Gaussian of
// angular radius 1.5° × √(1 + τ) (the forward lobe widening with multiple scattering, I), at most 5° (fill-rate cap, I),
// only while T < 0.97. Returns {f, theta (rad), tau} or null; aureole energy at the eye = I × f / d².
export const AUR_G = 0.85, AUR_R0_DEG = 1.5, AUR_RMAX_DEG = 5, AUR_T_MAX = 0.97;
export function aureole(T) {
  if (!(T < AUR_T_MAX)) return null;
  const tau = -Math.log(Math.max(T, 1e-300)); const f = (1 - T) * Math.exp(-(1 - AUR_G) * tau);
  if (!(f > 1e-6)) return null;
  return { f, tau, theta: Math.min(AUR_RMAX_DEG, AUR_R0_DEG * Math.sqrt(1 + tau)) * DEG };
}
