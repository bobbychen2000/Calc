// Physical sky, fog, cloud, Moon and night-sky model shared by the renderers (environment spec §4.2, §4.4, §4.5, §4.9,
// §7.1-7.4). Pure ES module (no DOM, no three.js): the CPU halves of the new renderer's sky (js/three/sky.js imports
// skyAmbientCPU / modelLight from here), the parameters it sends to the GPU, and the JS mirrors of its shader formulas
// that the Node gates check (tools/env/test_sky.mjs: A-SUN render half, A-MOON, A-EXP, A-FOG, A-CLD).
//
// Units. The renderer's "sky units": the sun outside the atmosphere is sunI = 20 units (js/live/app.js applyEnv), and
// js/three/renderer3.js LUX_PER_UNIT = 133,300 / 20 lx per unit (its own constant, quoted here). A radiance of 1 unit is
// then LUX_PER_UNIT cd/m² (Lambertian: L = ρE/π in both systems). The absolute scale is tied to USNO Circular 171 by
// sunCalibration() below (spec §7.2: "calibrate the relative sunI so that the global horizontal illuminance equals
// Circular 171", I), so the 133.3 klx figure only names the unit.
//
// Tags (spec): V verified · M measured / computed by our tools · I inferred (our choice) · 2nd secondary · NV unknown.
import { opticalDepth } from '../lighting/photometry.js';

export const LUX_PER_UNIT = 133300 / 20;            // = js/three/renderer3.js LUX_PER_UNIT (unit definition, see above)
const lum = (c) => 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];   // Rec. 709 luminance of linear sRGB
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const DEG = Math.PI / 180;
export const sstep = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };

// ------------------------------------------------------------------------------------------------ 1. clear-sky model
// Single-scattering Rayleigh + Mie sky of js/shaders/common.js SKY_PRECOMPUTE_FS (the old renderer) and js/three/sky.js
// precomputeNode: Re 6360 km, Ra 6420 km, Rayleigh βR (5.8, 13.5, 33.1)e-6 m⁻¹ at Hr 7994 m, Mie at Hm 1200 m (×1.1
// extinction), g 0.76, 32 view / 8 light steps (Bruneton & Neyret 2008 constants as used there; values copied, not
// re-derived). Ozone (review look2-11): absorption (0.65, 1.881, 0.085)e-6 m⁻¹ on its own tent profile, density 1 at
// 25 km falling to 0 at 10 / 40 km (Bruneton 2017 demo constants, 2nd); was × 1.8 on the Rayleigh profile (same column).
const Re = 6360e3, Ra = 6420e3, Hr = 7994.0, Hm = 1200.0;
const bRc = [5.8e-6, 13.5e-6, 33.1e-6], bOc = [0.65e-6, 1.881e-6, 0.085e-6];
export const OZ_H = 25000, OZ_W = 15000;
const ozone = (h) => Math.max(0, 1 - Math.abs(h - OZ_H) / OZ_W);
const rs = (ro, rd, r) => { const b = ro[0] * rd[0] + ro[1] * rd[1] + ro[2] * rd[2], c = ro[0] * ro[0] + ro[1] * ro[1] + ro[2] * ro[2] - r * r; const d = b * b - c; if (d < 0) return [-1, -1]; const q = Math.sqrt(d); return [-b - q, -b + q]; };

/** Sun transmittance from the camera to the top of the atmosphere (same as js/renderer.js sunTransmittance). */
export function sunTransmittanceCPU(sunDir, mie, camH = 30) {
  const ro = [0, Re + camH, 0]; const t = rs(ro, sunDir, Ra)[1];
  const N = 64; let odR = 0, odM = 0, odO = 0; const seg = t / N;
  for (let i = 0; i < N; i++) {
    const p = [sunDir[0] * seg * (i + 0.5), Re + camH + sunDir[1] * seg * (i + 0.5), sunDir[2] * seg * (i + 0.5)]; const h = Math.hypot(...p) - Re;
    if (h < 0) return [0, 0, 0];
    odR += Math.exp(-h / Hr) * seg; odM += Math.exp(-h / Hm) * seg; odO += ozone(h) * seg;
  }
  return bRc.map((br, k) => Math.exp(-(br * odR + bOc[k] * odO + mie * 1.1 * odM)));
}

/** CPU evaluation of the sky precompute on a 32x16 equirect grid and the ambient integration of js/renderer.js
 *  setupSky (sky-up: cosine-weighted upper hemisphere; horizon: 0 < d.y < 0.5 band). Same constants and step counts as
 *  the shader (moved here from js/three/sky.js, which re-exports it). */
export function skyAmbientCPU(sunDir, mie, sunI, camH = 30) {
  const NX = 32, NY = 16;
  const g = 0.76; let up = [0, 0, 0], wu = 0, hz = [0, 0, 0], wh = 0;
  for (let y = 0; y < NY; y++) for (let x = 0; x < NX; x++) {
    const th = (y + 0.5) / NY * Math.PI, phi = ((x + 0.5) / NX - 0.5) * 2 * Math.PI;
    const d = [Math.sin(th) * Math.sin(phi), Math.cos(th), -Math.sin(th) * Math.cos(phi)];
    if (d[1] <= 0) continue;
    let rd = d.slice(); if (rd[1] < 0.02) { rd[1] = 0.02 + (0.02 - rd[1]) * 0.02; const l = Math.hypot(...rd); rd = rd.map(v => v / l); }
    const ro = [0, Re + camH, 0];
    let tmax = rs(ro, rd, Ra)[1]; const tg = rs(ro, rd, Re); if (tg[0] > 0) tmax = Math.min(tmax, tg[0]);
    const N = 32, seg = tmax / N; let t = 0; const sumR = [0, 0, 0], sumM = [0, 0, 0], msR = [0, 0, 0], msM = [0, 0, 0]; let odR = 0, odM = 0, odO = 0;
    const mu = rd[0] * sunDir[0] + rd[1] * sunDir[1] + rd[2] * sunDir[2];
    const pR = 3 / (16 * Math.PI) * (1 + mu * mu), pM = 3 / (8 * Math.PI) * ((1 - g * g) * (1 + mu * mu)) / ((2 + g * g) * Math.pow(1 + g * g - 2 * g * mu, 1.5));
    for (let i = 0; i < N; i++) {
      const p = [ro[0] + rd[0] * (t + seg * 0.5), ro[1] + rd[1] * (t + seg * 0.5), ro[2] + rd[2] * (t + seg * 0.5)]; const h = Math.hypot(...p) - Re;
      const hr = Math.exp(-h / Hr) * seg, hm = Math.exp(-h / Hm) * seg; odR += hr; odM += hm; odO += ozone(h) * seg;
      const sl = rs(p, sunDir, Ra)[1] / 8; let odlR = 0, odlM = 0, odlO = 0, ok = true;
      for (let j = 0; j < 8; j++) { const q = [p[0] + sunDir[0] * sl * (j + 0.5), p[1] + sunDir[1] * sl * (j + 0.5), p[2] + sunDir[2] * sl * (j + 0.5)]; const hq = Math.hypot(...q) - Re; if (hq < 0) { ok = false; break; } odlR += Math.exp(-hq / Hr) * sl; odlM += Math.exp(-hq / Hm) * sl; odlO += ozone(hq) * sl; }
      for (let k = 0; k < 3; k++) {
        if (ok) { const att = Math.exp(-(bRc[k] * (odR + odlR) + bOc[k] * (odO + odlO) + mie * 1.1 * (odM + odlM))); sumR[k] += att * hr; sumM[k] += att * hm; }
        const tv = Math.exp(-(bRc[k] * odR + bOc[k] * odO + mie * 1.1 * odM)); msR[k] += tv * hr; msM[k] += tv * hm;
      }
      t += seg;
    }
    const sunUp = sunDir[1] >= 0 ? Math.min(1, Math.max(0, sunDir[1] * 1.2 + 0.08)) : 0.08 * Math.exp(sunDir[1] * 45.8); // as precomputeNode
    const col = [0, 1, 2].map(k => (sumR[k] * bRc[k] * pR + sumM[k] * mie * pM) * sunI + (msR[k] * bRc[k] + msM[k] * mie * 0.9) * sunI * 0.055 * sunUp);
    const sa = Math.sin(th); const w = d[1] * sa;
    for (let k = 0; k < 3; k++) up[k] += col[k] * w; wu += w;
    if (d[1] < 0.5) { for (let k = 0; k < 3; k++) hz[k] += col[k] * sa; wh += sa; }
  }
  return { up: up.map(v => v / wu), hz: hz.map(v => v / wh) };
}

/** Light terms of the clear-sky model (sky units): sun radiance colour, mean sky radiance up / horizon, and the
 *  horizontal illuminance split (beam on the horizontal, diffuse = π × sky-up luminance). */
export function modelLight(sunDir, mie, sunI) {
  const { up, hz } = skyAmbientCPU(sunDir, mie, sunI, 30);
  const T = sunTransmittanceCPU(sunDir, mie, 30);
  const sunColor = T.map(t => t * sunI);
  const beam = lum(sunColor) * Math.max(sunDir[1], 0), diffuse = Math.PI * lum(up);
  return { sunColor, skyUp: up, skyHorizon: hz, beam, diffuse, ghi: beam + diffuse };
}

// ------------------------------------------------------------------------------------------------ 2. C171 calibration
/** Scale of sunI so that the clear-sky model's global horizontal illuminance equals USNO Circular 171's clear-sky Sun
 *  term at this instant (spec §7.2, I on V). st = EnvState (natural.sun is C171 ÷ D; × D = clear). Below the elevation
 *  where C171's Sun term falls under 0.05 lx (deep nautical twilight, where C171 is outside its fitted range: "from the
 *  zenith down to nautical twilight") the factor of that limit is kept. Returns {k, modelLux, c171Lux}. */
export const CAL_MIN_LUX = 0.05;
export function sunCalibration(st, mie = 21e-6, dir = null) {
  // dir: the Sun direction the sky model is evaluated at (renderer3: geometric below the horizon, look1-10)
  const c171 = st.natural.sun * st.natural.D;
  const m = modelLight(dir || st.sun.dir, mie, 20);
  const modelLux = m.ghi * LUX_PER_UNIT;
  let k = c171 > CAL_MIN_LUX && modelLux > 1e-6 ? c171 / modelLux : null;
  return { k: k == null ? null : clamp(k, 0.1, 10), modelLux, c171Lux: c171 };
}

// ------------------------------------------------------------------------------------------------ 3. clouds -> light
/** Cloud-adjusted light (spec §4.2, §4.5): the total horizontal illuminance is the clear value ÷ D (EnvState
 *  natural.D: 1 / Kasten–Czeplak, or 10 with TS/CB; I on 2nd); the beam keeps its clear radiance (the renderer's
 *  per-layer coverage maps remove it where a cloud is, their area mean = sunVisibleP); the diffuse sky takes the rest:
 *  π·skyUp' = E_clear / D − P·E_beam (≥ 0), and turns grey with the cloud cover (I). light = modelLight-like terms. */
export function cloudAdjust(light, st, Tf = 1) {
  // Tf: the direct beam's transmittance through the fog / mist / VV obscuration (fogBeamT; review truth1-5): the beam lost
  // there goes to the diffuse sky, so the global horizontal illuminance stays C171 ÷ D (I)
  const P = st.sunVisibleP != null ? st.sunVisibleP : 1, D = st.natural.D || 1;
  const sy = Math.max(0, st.sun.dir[1]);
  const beam = lum(light.sunColor) * sy, diff = Math.PI * lum(light.skyUp);
  const target = (beam + diff) / D;
  const diffT = Math.max(target - P * Tf * beam, 0.25 * diff / D);
  const s = diff > 1e-12 ? diffT / diff : 1;
  const grey = clamp(1 - P, 0, 1) * 0.8;   // overcast sky colour toward neutral (I)
  const tint = (c) => { const l = lum(c); return c.map(v => (v + (l - v) * grey) * s); };
  const skyUp = tint(light.skyUp), skyHorizon = tint(light.skyHorizon);
  const Eh = P * Tf * beam + Math.PI * lum(skyUp);
  return { ...light, skyUp, skyHorizon, ground: [Eh * 0.16 / Math.PI, Eh * 0.16 / Math.PI, Eh * 0.16 / Math.PI], P, D, ghi: Eh, beamT: Tf };
}
/** Direct-beam transmittance of the Sun / Moon through the NON-cloud render slabs (fog, mist, the VV obscuration: excess
 *  over the sky model's clear air) from the ground up at elevation elDeg; the cloud layers cut the beam through their
 *  own coverage maps (review truth1-5: under VV002 the Moon stayed the directional light at its clear-sky illuminance). */
export function fogBeamT(slabs, elDeg) {
  let tau = 0; for (const s of slabs || []) if (!s.isCloud) tau += Math.max(0, s.sigma - SIGMA_CLEAR) * Math.max(0, s.y1 - s.y0);
  return Math.exp(-tau / Math.max(Math.sin(elDeg * DEG), 0.05));
}

// ------------------------------------------------------------------------------------------------ 4. night sky, Moon
/** Night-sky luminance (cd/m²): natural 174 µcd/m² ÷ D (Falchi et al. 2016, V) + artificial zenith luminance 3 mcd/m²
 *  × up to 10 under a low deck at night (Falchi Table 1 class, I; Kyba et al. 2011, V; applied to SFO, I), from
 *  EnvState.nightSky; in sky units as well. */
export function nightSkyLuminance(st) {
  const n = st.nightSky || { naturalCdM2: 0, artificialCdM2: 0 };
  const cd = n.naturalCdM2 + n.artificialCdM2;
  return { cdm2: cd, natural: n.naturalCdM2, artificial: n.artificialCdM2, units: cd / LUX_PER_UNIT };
}

export const MOON_DIST_KM = 384400;            // mean Earth–Moon distance (Meeus ch. 47), only for the Sun direction seen from the Moon
export const AU_KM = 149597870.7;              // IAU 2012
const norm = (v) => { const l = Math.hypot(v[0], v[1], v[2]) || 1; return [v[0] / l, v[1] / l, v[2] / l]; };
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];

/** Moon disc for the sky shader: direction, angular radius, disc basis (right, up: up = the zenith projected on the
 *  disc plane), the Sun direction seen from the Moon, and the disc luminance. Luminance = C171's horizontal Moon
 *  illuminance (clear, i.e. × D) / sin(el) / disc solid angle (V via C171; the disc is drawn uniformly bright, the
 *  Moon's limb darkening is small: I). */
export function moonDisc(st) {
  const m = st.moon; const md = norm(m.dir);
  const rad = (m.angularDiameter || 0.52) / 2 * DEG;
  const up0 = [0, 1, 0]; let upv = [up0[0] - md[0] * md[1], up0[1] - md[1] * md[1], up0[2] - md[2] * md[1]];
  if (Math.hypot(...upv) < 1e-6) upv = [0, 0, -1];
  const up = norm(upv), right = norm(cross(md, up));
  const sd = st.sun.dir; const sm = norm([sd[0] * AU_KM - md[0] * MOON_DIST_KM, sd[1] * AU_KM - md[1] * MOON_DIST_KM, sd[2] * AU_KM - md[2] * MOON_DIST_KM]);
  const omega = 2 * Math.PI * (1 - Math.cos(rad));
  const elRad = Math.max(m.el, 0.5) * DEG;
  const Eclear = (st.natural.moon || 0) * (st.natural.D || 1);
  const Lcd = Eclear / Math.sin(elRad) / omega;
  return { dir: md, rad, right, up, sunFromMoon: sm, cdm2: m.el > -1 ? Lcd : 0, units: m.el > -1 ? Lcd / LUX_PER_UNIT : 0, omega };
}

/** JS mirror of the sky shader's Moon shading (js/three/sky.js moonDiscNode): disc point (x, y) in units of the radius
 *  along (right, up); sphere normal n = x·right + y·up − √(1 − r²)·dir; lit where n·s > 0 (terminator ramp ±TERM). */
export const MOON_TERM = 0.02;
export function moonShade(D, x, y) {
  const r2 = x * x + y * y; if (r2 > 1) return 0;
  const z = Math.sqrt(1 - r2);
  const n = [x * D.right[0] + y * D.up[0] - z * D.dir[0], x * D.right[1] + y * D.up[1] - z * D.dir[1], x * D.right[2] + y * D.up[2] - z * D.dir[2]];
  return sstep(-MOON_TERM, MOON_TERM, dot(n, D.sunFromMoon));
}
/** Lit fraction of the disc and the bright-limb direction (deg from the disc's up, counter-clockwise as seen by the
 *  observer, i.e. towards the left = towards celestial east in the sense of a position angle) of the shader mirror. */
export function moonDiscStats(D, N = 200) {
  let lit = 0, area = 0, cx = 0, cy = 0;
  for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) {
    const x = (i + 0.5) / N * 2 - 1, y = (j + 0.5) / N * 2 - 1; if (x * x + y * y > 1) continue;
    area++; const s = moonShade(D, x, y); lit += s; cx += s * x; cy += s * y;
  }
  // angle from up towards LEFT (= -right): atan2(-cx, cy)
  const ang = ((Math.atan2(-cx, cy) / DEG) % 360 + 360) % 360;
  return { litFraction: lit / area, brightLimbFromUpDeg: ang };
}

// ------------------------------------------------------------------------------------------------ 5. fog slabs
// The piecewise-constant σ(y) of spec §4.4 / §7.3 as sent to the shader (≤ MAX_SLABS slabs, sorted by y0), with the
// clear air above the highest slab up to CLEAR_TOP. A BKN cloud slab gets the extinction of its MEAN transmittance,
// T = (1 − own) + own·exp(−σc·L) (the deck has gaps; its look comes from the cloud planes), an OVC / VV slab σc itself.
// isCloud slabs are left out of the background (sky) transmittance unless the camera is inside them (the sky's clouds
// are drawn by the cloud layers); the sub-cloud slab's clear-air part (SIGMA_CLEAR) is already in the sky model's
// aerial perspective, so the background takes only the excess over it (I).
export const MAX_SLABS = 6, CLEAR_TOP = 3000, SIGMA_CLEAR = 3.3e-5;   // SIGMA_CLEAR = js/env/state.js (spec §4.10, M)
export function renderSlabs(st) {
  const out = [];
  const clouds = st.clouds || [];
  for (const s of (st.atm && st.atm.slabs) || []) {
    let sigma = s.sigma; const isCloud = /^cloud/.test(s.kind || '');
    if (isCloud && /BKN/.test(s.kind)) {
      const c = clouds.find(c => Math.abs(c.base - s.y0) < 0.5); const own = c ? c.own : 0.75; const L = Math.max(1, s.y1 - s.y0);
      sigma = -Math.log((1 - own) + own * Math.exp(-s.sigma * L)) / L;
    }
    const o = { y0: s.y0, y1: s.y1, sigma, isCloud, kind: s.kind }; if (s.horiz) o.horiz = s.horiz;
    out.push(o);
  }
  out.sort((a, b) => a.y0 - b.y0);
  return out.slice(0, MAX_SLABS);
}
// ---- horizontal structure of the lowest slab (js/env/state.js horizontalFor; review truth1-6). Same functions in the
// shader (js/three/sky.js horizSigma): a patch mask from four incommensurate plane waves (deterministic, identical on CPU
// and GPU; wavelengths 290-640 m, I: spec "patch scale ~200-500 m"), cosine lobes ±45° about each sector direction seen
// from the station (ARP), a radial ramp over 500 m from r0, a height limit; the extra optical depth along a path is
// integrated with HORIZ_SAMPLES stratified samples over the path's part inside the slab.
export const PATCH_WAVES = [[640, 17, 0.3], [470, 74, 1.7], [380, 131, 4.1], [290, 166, 2.6]];   // [λ m, θ deg, φ rad]
export const PATCH_RAMP = 0.06, LOBE_RAMP_M = 500, HORIZ_SAMPLES = 8, PATCH_R_M = 1500, PATCH_FADE_M = 500;   // patches within 1.5-2 km of the ARP (around the station, I; js/env/state.js horizontalFor)
export function patchNoise(x, z) { let n = 0; for (const [l, t, f] of PATCH_WAVES) n += Math.sin(2 * Math.PI * (x * Math.cos(t * DEG) + z * Math.sin(t * DEG)) / l + f); return 0.5 + 0.125 * n; }
const thrCache = new Map();
/** Threshold of the patch mask smoothstep(thr ± PATCH_RAMP, n) whose area mean is `cover` (bisection on a 6 km grid). */
export function patchThreshold(cover) {
  const key = cover.toFixed(4); if (thrCache.has(key)) return thrCache.get(key);
  const N = 160, span = 6000, vals = new Float64Array(N * N);
  for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) vals[j * N + i] = patchNoise(i / N * span - 3000 + 0.37, j / N * span - 3000 + 0.61);
  const mean = (thr) => { let m = 0; for (let k = 0; k < vals.length; k++) m += sstep(thr - PATCH_RAMP, thr + PATCH_RAMP, vals[k]); return m / vals.length; };
  let a = -0.2, b = 1.2; for (let it = 0; it < 50; it++) { const c = (a + b) / 2; if (mean(c) > cover) a = c; else b = c; }
  const thr = (a + b) / 2; thrCache.set(key, thr); return thr;
}
/** Patch mask in [0, 1] at world (x, z): the noise mask over the aerodrome (fading out beyond PATCH_R_M). */
export const patchMask = (x, z, thr) => sstep(thr - PATCH_RAMP, thr + PATCH_RAMP, patchNoise(x, z)) * (1 - sstep(PATCH_R_M, PATCH_R_M + PATCH_FADE_M, Math.hypot(x, z)));
/** Lobe weight of a sector lobe {az, r0} at world (x, z) seen from the station at the ARP (x east, z south). */
export function lobeWeight(L, x, z) {
  const r = Math.hypot(x, z); if (r < 1e-6) return L.r0 > 0 ? 0 : 1;
  const az = Math.atan2(x, -z) / DEG; const dd = ((az - L.az) % 360 + 540) % 360 - 180;
  const ang = Math.abs(dd) < 45 ? Math.cos(2 * dd * DEG) : 0;
  return ang * (L.r0 > 0 ? sstep(L.r0, L.r0 + LOBE_RAMP_M, r) : 1);
}
/** Extra extinction (m⁻¹) of the horizontal structure H at p over the slab's base σ0 (≥ SIGMA_CLEAR − σ0). */
export function horizDelta(H, sigma0, p) {
  if (!H) return 0;
  let pd = 0; if (H.patch) { if (H._thr == null) H._thr = patchThreshold(H.patch.cover); pd = patchMask(p[0], p[2], H._thr) * (H.patch.sigma - sigma0); }
  let ld = 0; for (const L of H.lobes || []) if (p[1] < L.top) ld += lobeWeight(L, p[0], p[2]) * (L.sigma - sigma0);
  return Math.max(Math.max(pd, ld), SIGMA_CLEAR - sigma0);
}
/** Extra optical depth of the lowest slab's horizontal structure along a -> b (stratified samples over the part of the
 *  segment below the slab top). */
export function horizTau(slabs, a, b) {
  const S = slabs && slabs[0]; if (!S || !S.horiz) return 0;
  const y1 = S.y1, dy = b[1] - a[1];
  let s0 = 0, s1 = 1;
  if (Math.abs(dy) < 1e-9) { if (a[1] >= y1) return 0; }
  else { const sc = (y1 - a[1]) / dy; if (dy > 0) s1 = Math.min(1, sc); else s0 = Math.max(0, sc); }
  if (s1 <= s0) return 0;
  const L = Math.hypot(b[0] - a[0], dy, b[2] - a[2]) * (s1 - s0); let sum = 0;
  for (let k = 0; k < HORIZ_SAMPLES; k++) { const s = s0 + (s1 - s0) * (k + 0.5) / HORIZ_SAMPLES; sum += horizDelta(S.horiz, S.sigma, [a[0] + (b[0] - a[0]) * s, a[1] + dy * s, a[2] + (b[2] - a[2]) * s]); }
  return sum / HORIZ_SAMPLES * L;
}
/** Optical depth of a path a -> b through the render slabs (+ clear air above the slabs up to CLEAR_TOP, + the
 *  horizontal structure of the lowest slab). The light sprites (js/env/lighting/airfield.js, js/env/aircraft_lights.js)
 *  and the CPU mirror of the shader's fog use THIS function on renderSlabs(st): the scene and the lights see one σ field
 *  (spec §4.10; review truth1-3: the lights used the raw EnvState slabs). */
export function slabTau(slabs, a, b) {
  const tau = opticalDepth(a, b, slabs.map(s => ({ y0: s.y0, y1: s.y1, sigma: s.sigma })), 0);
  // clear air above the top slab, below CLEAR_TOP
  const top = slabs.length ? slabs[slabs.length - 1].y1 : -Infinity;
  const L = Math.hypot(b[0] - a[0], b[1] - a[1], b[2] - a[2]);
  const ylo = Math.min(a[1], b[1]), yhi = Math.max(a[1], b[1]), h = yhi - ylo;
  const f = h < 1e-6 ? (a[1] >= top && a[1] < CLEAR_TOP ? 1 : 0) : Math.max(0, Math.min(yhi, CLEAR_TOP) - Math.max(ylo, top)) / h;
  return tau + SIGMA_CLEAR * f * L + horizTau(slabs, a, b);
}
/** JS mirror of the shader's fog: transmittance camera -> point and the apparent contrast of a black target against
 *  the fog-coloured horizon (Koschmieder: C = T when the background is the in-scatter colour; spec A-FOG). */
export const fogTransmittance = (slabs, cam, p) => Math.exp(-slabTau(slabs, cam, p));

// ------------------------------------------------------------------------------------------------ 6. cloud layers
// Per layer a density d(p) = smoothstep(thr − H, thr + H, n(p)), n = c(p/scale + off) + A·(c(7.3·p/scale + off2) − 0.5),
// c = the app's cloud texture (js/world/textures.js makeCloudTexture, 512² R8). thr is solved so that the AREA MEAN of
// d equals the layer's own coverage (JO 7900.5E summation amounts de-summed, EnvState clouds[].own; spec A-CLD) from
// the texture's histogram (both octaves independent: the distribution of n is the convolution of two copies).
export const CLOUD_RAMP = 0.08, CLOUD_DETAIL = 0.35, MAX_CLOUD_LAYERS = 6;
/** Histogram (256 bins, 0..1) of an 8-bit texture. */
export function histogram8(data) { const h = new Float64Array(256); for (let i = 0; i < data.length; i++) h[data[i]]++; for (let i = 0; i < 256; i++) h[i] /= data.length; return h; }
/** Distribution of n = c1 + A (c2 − 0.5) on a grid of NB bins over [−A/2, 1 + A/2]: {lo, step, p[]} */
export function detailDistribution(h, A = CLOUD_DETAIL, NB = 512) {
  const lo = -A / 2, hi = 1 + A / 2, step = (hi - lo) / NB; const p = new Float64Array(NB);
  for (let i = 0; i < 256; i++) { if (!h[i]) continue; const a = i / 255; for (let j = 0; j < 256; j++) { if (!h[j]) continue; const v = a + A * (j / 255 - 0.5); const b = Math.min(NB - 1, Math.max(0, Math.floor((v - lo) / step))); p[b] += h[i] * h[j]; } }
  return { lo, step, p };
}
/** Mean density for threshold thr. */
export function meanDensity(dist, thr, H = CLOUD_RAMP) { let m = 0; for (let b = 0; b < dist.p.length; b++) { if (!dist.p[b]) continue; const v = dist.lo + (b + 0.5) * dist.step; m += dist.p[b] * sstep(thr - H, thr + H, v); } return m; }
/** Threshold whose mean density is the target coverage (bisection; 0 -> above everything, 1 -> below everything). */
export function coverageThreshold(dist, cover, H = CLOUD_RAMP) {
  if (cover <= 0) return 2.0; if (cover >= 0.999) return -2.0;
  let a = dist.lo - H - 0.01, b = dist.lo + dist.p.length * dist.step + H + 0.01;
  for (let i = 0; i < 60; i++) { const m = (a + b) / 2; if (meanDensity(dist, m, H) > cover) a = m; else b = m; }
  return (a + b) / 2;
}
/** Layers for the renderer from EnvState.clouds (≤ 6, CLR above 12,000 ft not reported): base y, own coverage,
 *  threshold, scale (texture period, m), opacity, slab (drawn as planes: base below SLAB_MAX_FT; else in the sky
 *  shader), drift (m/s, METAR surface wind, not amplified: spec §4.5, I). Thickness: EnvState value or 300 m (I). */
export const SLAB_MAX_FT = 5000, CIRRUS_OPACITY = 0.55, MIN_CLOUD_FT = 100;
export function cloudLayers(st, dist) {
  // a layer based below 100 ft (e.g. 'FG BKN000') is the fog's partial obscuration, not a cloud: the fog slab draws it
  // (JO 7900.5E 9.3 / spec §4.4 'FG without VV', I)
  const L = (st.clouds || []).filter(c => c.base != null && c.baseFt >= MIN_CLOUD_FT).sort((a, b) => a.base - b.base).slice(0, MAX_CLOUD_LAYERS);
  return L.map((c, i) => {
    const kind = c.kind; const opacity = kind === 'cirriform' ? CIRRUS_OPACITY : 1.0;
    // the area-mean coverage that must equal own: d × opacity; for thin cirrus the opacity is part of the cover (I)
    const own = clamp(c.own, 0, 1); const thr = coverageThreshold(dist, Math.min(1, own / opacity));
    const scale = kind === 'cirriform' ? 12000 : kind === 'mid' ? 7000 : (c.cover === 'FEW' || c.cover === 'SCT') ? 2600 : 4200; // texture period (m): cell sizes, I
    return { i, cover: c.cover, baseY: c.base, baseFt: c.baseFt, resFt: c.resFt, own, thr, scale, opacity, kind,
      thickness: c.thickness != null ? c.thickness : 300, slab: c.baseFt < SLAB_MAX_FT, drift: c.drift || [0, 0], off: [0.137 * (i + 1), 0.291 * (i + 1)] };
  });
}

// ------------------------------------------------------------------------------------------------ 7. A-SUN render half
/** Shadow azimuth (deg, compass) cast by a vertical pole under the directional light with direction dir (towards the
 *  light, x east, y up, z south): the shadow points away from the light. */
export function shadowAzimuth(dir) { const a = Math.atan2(-dir[0], dir[2]) / DEG; return (a % 360 + 360) % 360; }
