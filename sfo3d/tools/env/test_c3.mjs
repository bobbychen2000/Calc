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
  // close-out round 5: §4b(2)(b) "No tailwind component may be present except the nominal range of winds reported as calm
  // (0-3 knots)" - the 3 kt is the reported wind speed (gusts included), not a tailwind-component allowance
  check('8400.9 wet: 18004KT -RA (28 tail 1.9 kt, wind 4 kt not calm) -> Southeast', P('METAR KSFO 301456Z 18004KT 10SM -RA OVC010 14/13 A2995').plan === 'southeast', P('METAR KSFO 301456Z 18004KT 10SM -RA OVC010 14/13 A2995').source);
  check('8400.9 wet: 18003KT -RA (wind reported in the calm range 0-3 kt) -> West', P('METAR KSFO 301456Z 18003KT 10SM -RA OVC010 14/13 A2995').plan === 'west');
  check('8400.9 wet: 18003G12KT -RA (gusts: not calm, 28 tail 1.4 kt) -> Southeast', P('METAR KSFO 301456Z 18003G12KT 10SM -RA OVC010 14/13 A2995').plan === 'southeast');
  check('8400.9 wet: 30008KT -RA (headwind on 28) -> West', P('METAR KSFO 301456Z 30008KT 10SM -RA OVC010 14/13 A2995').plan === 'west');
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
  // close-out round 5 (c3 verifier env-14): what the terrain MESH shows - Terrain.buildMeshes' grid (step 15 to +-4.2 km,
  // then x1.052 per cell: 100-550 m at the lakes) interpolated between its samples; the water is visible where that
  // surface lies below the level (round 3: 94 / 73 / 69 %, the bed only 3 m deep against a bank rising 0.12 m/m)
  const co = []; for (let x = -4200; x <= 4200 + 1e-6; x += 15) co.push(x); { let x = 4200, s = 15; while (x < 60000) { s *= 1.052; x += s; co.unshift(-x); co.push(x); } }
  const ix = (v) => { let lo = 0, hi = co.length - 1; while (hi - lo > 1) { const m = (lo + hi) >> 1; if (co[m] <= v) lo = m; else hi = m; } return lo; };
  const meshH = (x, z) => { const i = ix(x), j = ix(z); const u = (x - co[i]) / (co[i + 1] - co[i]), v = (z - co[j]) / (co[j + 1] - co[j]); return (T.height(co[i], co[j]) * (1 - u) + T.height(co[i + 1], co[j]) * u) * (1 - v) + (T.height(co[i], co[j + 1]) * (1 - u) + T.height(co[i + 1], co[j + 1]) * u) * v; };
  const inR = (R, x, z) => { let c = false; for (let i = 0, j = R.length - 1; i < R.length; j = i++) { const [xa, za] = R[j], [xb, zb] = R[i]; if ((za > z) !== (zb > z) && x < (xb - xa) * (z - za) / (zb - za) + xa) c = !c; } return c; };
  const vis = []; for (const L of RESERVOIRS.lakes) { let x0 = 1e9, z0 = 1e9, x1 = -1e9, z1 = -1e9; for (const [x, z] of L.ring) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); z0 = Math.min(z0, z); z1 = Math.max(z1, z); }
    let n = 0, b = 0; for (let x = x0; x <= x1; x += 50) for (let z = z0; z <= z1; z += 50) { if (!inR(L.ring, x, z)) continue; n++; if (meshH(x, z) < L.level_y) b++; } vis.push(b / n); }
  check('lakes over the terrain MESH (step-15 grid): water visible >= 85 % of each lake (residual: shore bends finer than the far cells)', vis.every(v => v >= 0.85), vis.map(v => (100 * v).toFixed(1) + ' %').join(' / '));
}
// ---------------------------------------------------------------- env-3: fog aureole profile (js/three/lights.js, CPU mirror)
{
  const L = await import('../../js/three/lights.js');
  const g = 0.5 * 1 + (1 - L.AUR_CORE_SHARE) * L.AUR_G_GEOM;   // overall asymmetry of diffraction (g ~ 1) + refraction lobe
  const { AUR_G } = await import('../../js/env/lighting/photometry.js');
  check('aureole split: 0.5 x diffraction (g~1) + 0.5 x refraction lobe (g_geom) = photometry AUR_G', Math.abs(g - AUR_G) < 1e-9, `g ${g} vs ${AUR_G}`);
  // the small-angle HG shape (1 + (ψ/θt)²)^-1.5 vs Henyey-Greenstein g_geom out to 1.5 θt (within 15 %)
  const hg = (psi, gg) => (1 - gg * gg) / Math.pow(1 + gg * gg - 2 * gg * Math.cos(psi), 1.5), th = L.AUR_TAIL_RAD;
  let worst = 0; for (const k of [0.25, 0.5, 1, 1.5]) { const r = (hg(k * th, L.AUR_G_GEOM) / hg(0, L.AUR_G_GEOM)) / Math.pow(1 + k * k, -1.5); worst = Math.max(worst, Math.abs(r - 1)); }
  check('broad lobe shape = small-angle Henyey-Greenstein (|err| < 15 % to 1.5 θt)', worst < 0.15, `θt ${(th * 180 / Math.PI).toFixed(1)} deg, worst ${(100 * worst).toFixed(1)} %`);
  // its plane integral: ∫ 2πθ (1 + θ²/θt²)^-1.5 dθ = 2π θt² (the shader's normalisation)
  let I = 0; const dt = th / 2000; for (let t = dt / 2; t < 400 * th; t += dt * (1 + t / th)) { const w = dt * (1 + t / th); I += 2 * Math.PI * t * Math.pow(1 + (t / th) ** 2, -1.5) * w; }
  check('broad lobe normalisation 2π θt²', Math.abs(I / (2 * Math.PI * th * th) - 1) < 0.01, `${(I / (2 * Math.PI * th * th)).toFixed(4)}`);
  // veil share of the broad lobe in front of a surface: 0 at the eye, 1 at the lamp, monotonic; = numeric ∫_1^{u_o} p(θu) du / ∫_1^∞
  const gv = (v) => v / Math.sqrt(1 + v * v), Ft = (v1, uo) => (gv(v1 * uo) - gv(v1)) / Math.max(1 - gv(v1), 1e-6);
  const num = (v1, uo) => { const p = (u) => Math.pow(1 + (v1 * u) ** 2, -1.5); let a = 0, b = 0; for (let u = 1; u < 4000; u *= 1.0005) { const w = u * 0.0005; const f = p(u) * w; b += f; if (u < uo) a += f; } return a / b; };
  let errF = 0, mono = true, prev = -1; for (const uo of [1.05, 1.5, 2.5, 6, 30]) { const f = Ft(0.3, uo); errF = Math.max(errF, Math.abs(f - num(0.3, uo))); if (f < prev) mono = false; prev = f; }
  check('broad-lobe veil share F(u_o) analytic = numeric path integral, monotonic', errF < 0.01 && mono && Ft(0.3, 1) === 0, `max err ${errF.toFixed(4)}`);
  // quad extent: where each part falls to AUR_EPS once exposed (Gaussian: k = √ln(L/ε) >= 2; lobe: (1 + k²)^-1.5 = ε / L)
  const Lx = 1e4 * L.AUR_EPS, kc = Math.sqrt(Math.log(Lx / L.AUR_EPS)), kt = Math.sqrt(Math.pow(Lx / L.AUR_EPS, 2 / 3) - 1);
  // energy: drawn core (Gaussian inside kc radii) + drawn lobe (inside kt θt) = the aureole energy, for dim to bright lamps
  // (the lobe beyond kt goes to the core; the core's Gaussian beyond kc >= 2 radii is below EPS by construction)
  let worstE = 0; const thA = 2 * Math.PI / 180;
  for (const peak of [0.3, 3, 30, 3e3, 3e6]) {   // nominal lobe peak / EPS
    const E = 1, wT = 1 - L.AUR_CORE_SHARE, Lt = E * wT / (2 * Math.PI * th * th); const expo = peak * L.AUR_EPS / Lt;
    const kt = Math.min(L.AUR_K_TAIL_MAX, Math.sqrt(Math.max(Math.pow(Math.max(Lt * expo / L.AUR_EPS, 1), 2 / 3) - 1, 0)));
    const Lc = E * (1 - wT + wT / Math.sqrt(kt * kt + 1)) / (Math.PI * thA * thA);
    const kc = Math.min(L.AUR_K_CORE_MAX, Math.max(2, Math.sqrt(Math.log(Math.max(Lc * expo / L.AUR_EPS, 1)))));
    const drawn = Lc * Math.PI * thA * thA * (1 - Math.exp(-kc * kc)) + Lt * 2 * Math.PI * th * th * (1 - 1 / Math.sqrt(1 + kt * kt));
    worstE = Math.max(worstE, Math.abs(drawn / E - 1));
  }
  check('aureole energy drawn = aureole energy (lobe beyond its quad folded into the core), dim to bright lamps', worstE < 0.02, `worst ${(100 * worstE).toFixed(2)} % (plane model, no rim)`);
  // close-out round 5: the same, integrating what the SHADER draws - the quad's soft rim 1 - smoothstep(0.7, 1, r) and
  // the billboard's tan mapping (a plane offset x = ρ/d subtends cos³(atan x) dA/d²), the quad's actual extents kq / kcq,
  // and the fold-back gains (lights.js aurCoreGain / aurLobeGain); the round-3 shader (no gains, kq = kt, kcq = kc) for
  // comparison. Desktop (lobe on, core <= 5 radii) and phone tier (no lobe, core 2 radii)
  const sm = (x) => { const t = Math.min(1, Math.max(0, (x - 0.7) / 0.3)); return t * t * (3 - 2 * t); };
  const shaderE = (peak, tail, kMax, fold) => {
    const E = 1, wT = tail ? 1 - L.AUR_CORE_SHARE : 0, LtN = E * (1 - L.AUR_CORE_SHARE) / (2 * Math.PI * th * th); const expo = peak * L.AUR_EPS / LtN;
    const Lt = E * wT / (2 * Math.PI * th * th);
    const kt = Math.min(L.AUR_K_TAIL_MAX, Math.sqrt(Math.max(Math.pow(Math.max(Lt * expo / L.AUR_EPS, 1), 2 / 3) - 1, 0)));
    const Lc0 = E * (1 - wT + wT / Math.sqrt(kt * kt + 1)) / (Math.PI * thA * thA);
    const kc = Math.min(kMax, Math.max(2, Math.sqrt(Math.log(Math.max(Lc0 * expo / L.AUR_EPS, 1)))));
    const q = Math.max(thA * kc, kt * th);   // quad half size / d (the core sprite itself is smaller)
    const kq = Math.min(q / th, L.AUR_K_TAIL_MAX), kcq = q / thA;
    const LcD = fold ? E * (1 - wT + wT / Math.sqrt(kq * kq + 1)) / (Math.PI * thA * thA) * L.aurCoreGain(kcq) : Lc0, LtD = fold ? Lt * L.aurLobeGain(kq) : Lt;
    let e = 0; const n = 20000, dx = q / n;
    for (let i = 0; i < n; i++) { const x = (i + 0.5) * dx; e += (LcD * Math.exp(-((x / thA) ** 2)) + LtD * Math.pow(1 + (x / th) ** 2, -1.5)) * (1 - sm(x / q)) * 2 * Math.PI * x * dx * Math.pow(Math.cos(Math.atan(x)), 3); }
    return { e, kc, q: q / thA };
  };
  let wNew = 0, wOld = 0, wPh = 0, wPhOld = 0, kcPh = 0;
  for (const peak of [0.3, 3, 30, 3e3, 3e6]) {
    wNew = Math.max(wNew, Math.abs(shaderE(peak, true, L.AUR_K_CORE_MAX, true).e - 1)); wOld = Math.max(wOld, Math.abs(shaderE(peak, true, L.AUR_K_CORE_MAX, false).e - 1));
    const ph = shaderE(peak, false, L.AUR_K_CORE_LOW, true); wPh = Math.max(wPh, Math.abs(ph.e - 1)); kcPh = Math.max(kcPh, ph.q);
    wPhOld = Math.max(wPhOld, Math.abs(shaderE(peak, false, 3, false).e - 1));
  }
  check('aureole energy as the SHADER draws it (soft rim, tan-mapped billboard, fold-back gains), desktop: within 2 %', wNew < 0.02, `worst ${(100 * wNew).toFixed(2)} % (round-3 shader: ${(100 * wOld).toFixed(1)} %)`);
  check('phone tier: aureole quad <= 2 core radii (round 2 fill rate) and its energy within 2 %', kcPh <= 2 + 1e-9 && wPh < 0.02, `quad ${kcPh.toFixed(2)} radii, worst ${(100 * wPh).toFixed(2)} % (round-3 phone shader: 3 radii, ${(100 * wPhOld).toFixed(1)} %)`);
  check('quad edge values = AUR_EPS (core, lobe) for a lamp 1e4 x above it', Math.abs(Lx * Math.exp(-kc * kc) / L.AUR_EPS - 1) < 1e-9 && Math.abs(Lx * Math.pow(1 + kt * kt, -1.5) / L.AUR_EPS - 1) < 1e-9, `kc ${kc.toFixed(2)} (cap ${L.AUR_K_CORE_MAX}), kt ${kt.toFixed(2)} (cap ${L.AUR_K_TAIL_MAX})`);
}
console.log(`close-out round 3 (env): ${n - fails}/${n} checks passed`);
process.exit(fails ? 1 : 0);
