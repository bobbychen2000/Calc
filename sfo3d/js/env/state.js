// EnvState: the one environment object both renderers consume (docs/research/environment_spec.md §3.6). Built from the
// data clock (js/env/clock.js), the current METAR/SPECI (+ TAF) decoded by js/env/wx/metar.js, the ephemeris
// (js/env/ephemeris.js) and the runway configuration (§3.5). Pure ES module, no DOM: Node tests in
// tools/env/test_env_state.mjs reproduce the environment fields of the 14 real-weather presets
// (tools/env/fixtures/env_presets.json, written by tools/env/env_spec_checks.py).
// Not computed here (later steps): the lighting controller (§5.3, step 2: `lighting` stays null), slab/cloud/rain
// rendering (step 3-4). Every field carries its provenance tag in `prov` (V / M / I / 2nd / NV, spec tag table).
import { skyState, naturalIlluminanceAt, ev100ForIlluminance, SFO } from './ephemeris.js';
import { decodeMetar, decodeTaf, renderParams, extinctionFromVisibility, FT_M, KT_MS, SM_M } from './wx/metar.js';

const DEG = Math.PI / 180;
// ---------------------------------------------------------------------------------------------------- constants
export const FC_LUX = 10.7639;                 // lux per foot-candle (exact: 1 fc = 1 lm/ft²)
// ASOS photocell "between 0.5 and 3 foot candles (deep twilight)", ASOS User's Guide §4.2 (V) -> night weight
export const ASOS_DAY_LUX = 3 * FC_LUX, ASOS_NIGHT_LUX = 0.5 * FC_LUX;   // 32.3 lx, 5.38 lx
// Apron floodlights on below 32.3 lx (Sun ≈ −3.7° clear; sun_night §8.2, I; no SFO/FAA switching rule: NV)
export const FLOODS_ON_LUX = 3 * FC_LUX;
// PAPI photocell: day mode when the north-facing vertical illuminance rises to 50-60 fc, night below 25-35 fc,
// 45-75 s delay (AC 150/5345-28H §3.3.6, V); thresholds 55 fc up / 30 fc down and 60 s are the midpoints (I);
// north-sky vertical illuminance = half the horizontal C171 value, isotropic sky (I)
export const PAPI_DAY_FC = 55, PAPI_NIGHT_FC = 30, PAPI_DELAY_MS = 60e3;
// Obstruction lights on when the north sky falls below 60 fc, before it reaches 35 fc (AC 70/7460-1N §5.3, V):
// switch at the 47.5 fc midpoint of that window (I)
export const OBSTRUCTION_ON_FC = 47.5;
// USNO sunset/sunrise: centre of the Sun 50' below the horizon, airless (https://aa.usno.navy.mil/faq/RST_defs, V);
// tower-operated lights "between sunset and sunrise" (JO 7110.65BB 3-4-5, 3-4-10, 3-4-17, 3-4-18, V)
export const TOWER_NIGHT_EL = -50 / 60;
// Allard thresholds fitted to AC 70/7460-1N Table B-1 + B.3 with the ASOS σ inversion (spec §4.10, M)
export const ET_DAY_LUX = 4.12e-4, ET_NIGHT_LUX = 6.99e-7;
// Clear-air extinction of the app's sky model: Rayleigh + Mie 21e-6 m⁻¹ ≈ 3.3e-5 m⁻¹ (spec §4.10, M); a 10SM / P6SM
// report is a lower bound on visibility, so σ from it is an upper bound: use the clear air, clamped ≤ 1.8e-4 (§4.3, I)
export const SIGMA_CLEAR = 3.3e-5, SIGMA_10SM_DAY = 1.80e-4;
// Cloud slab defaults (§4.4): in-cloud σ_c 0.04 m⁻¹ (I; range 0.025-0.075), stratus depth 1000 ft (MIT LL ATC-319
// "usually less than 1000 feet", V), fog top without VV 200 ft (I), MIFG below 6 ft (JO 7900.5E 13.13e, V)
export const SIGMA_CLOUD = 0.04, STRATUS_DEPTH_FT = 1000, FOG_TOP_FT = 200, MIFG_TOP_FT = 6;
// Night sky (§4.9): natural 174 µcd/m² (Falchi 2016, V) ÷ D; artificial zenith 3 mcd/m² (I, parameter) × up to 10
// under a low deck (Kyba 2011 Berlin ×10.1, V; applied to SFO, I)
export const NIGHT_NATURAL_CDM2 = 174e-6, NIGHT_ARTIFICIAL_CDM2 = 3e-3, OVERCAST_AMP = 10;
// Exposure clamp EV100 ∈ [2, 16] (sun_night §6.3, I, QA-tuned)
export const EV_MIN = 2, EV_MAX = 16;
export const STALE_MIN = 90;                   // report older than 90 min of data time -> stale (spec §3.3)
export const FIELD_ELEV_FT = 13.1;             // FAA NASR / AirNav; METAR heights are above field elevation (JO 7900.5E 10.8)
// Runway headings (true, deg): the airport grid (CLAUDE.md: s along 117.83°, t along 27.83°)
const RWY_HDG = { '28': 297.83, '10': 117.83, '19': 207.83, '1': 27.83 };

const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
/** ASOS photocell night weight from horizontal illuminance E (lx): 0 at ≥ 32.3 lx, 1 at ≤ 5.38 lx, log-linear (§4.2). */
export function asosNightWeight(E) { const a = Math.log(ASOS_DAY_LUX), b = Math.log(ASOS_NIGHT_LUX); return clamp((a - Math.log(Math.max(E, 1e-9))) / (a - b), 0, 1); }
/** Cloud divisor D (§4.2, I): 10 with TS (not VC) or a CB layer; else 1 / max(0.25, Kasten–Czeplak ratio). */
export function cloudDivisor(d, p) {
  const wx = d.weather || [];
  if (wx.some(w => w.descriptor === 'TS' && !w.vicinity) || (d.sky || []).some(s => s.type === 'CB')) return 10.0;
  return 1.0 / Math.max(0.25, p.global_irradiance_ratio);
}
/** Allard threshold E_T for night weight w (§4.10 rule, I on M). */
export const allardThreshold = (w) => Math.exp((1 - w) * Math.log(ET_DAY_LUX) + w * Math.log(ET_NIGHT_LUX));

/** Sort reports [{raw, obsTime?}] by observation time resolved against tEnv; returns [{raw, obsMs, d}], newest first. */
export function indexReports(reports, tEnv) {
  const ref = new Date(tEnv);
  const out = [];
  for (const r of reports || []) {
    const raw = typeof r === 'string' ? r : r.raw || r.rawOb;
    if (!raw) continue;
    const d = decodeMetar(raw, ref);
    const obsMs = (r && r.obsTime != null) ? r.obsTime * 1000 : (d.time && d.time.utc ? Date.parse(d.time.utc) : null);
    out.push({ raw: d.raw, obsMs, receiptMs: r && r.receiptTime ? Date.parse(r.receiptTime) : null, d });
  }
  return out.sort((a, b) => (b.obsMs ?? 0) - (a.obsMs ?? 0));
}
/** Current report by data clock (§3.3): the latest with obsTime ≤ t_env (live: the latest received). */
export function selectReport(indexed, tEnv, live = false) {
  if (!indexed.length) return null;
  if (live) return indexed[0];
  return indexed.find(r => r.obsMs != null && r.obsMs <= tEnv) || null;
}

/** Runway configuration (§3.5): observed ADS-B flow (stats.js runwayConfig) > METAR true wind with JO 7110.65 3-5-1
 *  ("most nearly aligned with the wind when 5 knots or more") > SFO West Plan below 5 kt ("95-98% of the time",
 *  flysfo.com). Plans other than West (arrive 28, depart 1) and Southeast (arrive 19, depart 10) are I. */
export function runwayConfigFrom(d, observed, override) {
  if (override) return override;
  if (observed && observed.n > 0 && (observed.arr.length || observed.dep.length)) {
    const arr = {}; for (const e of observed.arr) arr[e] = 'observed'; return { arr, dep: observed.dep.slice(), source: 'ADS-B flow (last 20 min)', tag: 'M' };
  }
  const w = d && d.wind; const kt = w && w.speed_kt; const dir = w && w.dir_true_deg;
  let plan = 'west';
  if (kt != null && kt >= 5 && dir != null) {
    const off = (h) => Math.abs(((dir - h) % 360 + 540) % 360 - 180);
    const best = Object.entries(RWY_HDG).sort((a, b) => off(a[1]) - off(b[1]))[0][0];
    plan = { '28': 'west', '19': 'southeast', '10': 'east', '1': 'north' }[best];
  }
  const P = { west: [['28L', '28R'], ['1L', '1R']], southeast: [['19L', '19R'], ['10L', '10R']], east: [['10L', '10R'], ['10L', '10R']], north: [['1L', '1R'], ['1L', '1R']] }[plan];
  // instrument approaches when below the charted visual-approach minima "SFO 2500'/5" (Quiet Bridge / Tipp Toe, V)
  const vis = d && d.visibility ? d.visibility.sm : null, ceil = d ? d.ceiling_ft : null;
  const instr = (vis != null && vis < 5) || (ceil != null && ceil < 2500);
  const arr = {}; for (const e of P[0]) arr[e] = instr ? 'instrument' : 'unknown';
  return { arr, dep: P[1], plan, source: kt != null && kt >= 5 ? 'METAR wind, JO 7110.65 3-5-1' : 'calm/light wind: SFO West Plan', tag: plan === 'west' || plan === 'southeast' ? 'V+I' : 'I' };
}

/** Vertical σ(y) profile (§4.4): piecewise-constant slabs in world y (m) = groundY + ft × 0.3048. */
function slabsFor(d, p, sigmaSurface, groundY) {
  const y = (ft) => groundY + ft * FT_M;
  const S = [];
  const wx = d.weather || [];
  const desc = new Set(wx.map(w => w.descriptor));
  const vv = (d.sky || []).find(s => s.cover === 'VV');
  const ceil = d.ceiling_ft;
  const fog = p.fog;
  let top = ceil != null ? ceil : null;            // sub-cloud slab up to the ceiling (or VV)
  if (fog && fog.kind === 'fog') {
    top = desc.has('MI') ? MIFG_TOP_FT : (vv && vv.height_ft != null ? vv.height_ft : (top != null && top > 0 ? Math.min(top, FOG_TOP_FT) : FOG_TOP_FT));
    S.push({ y0: groundY, y1: y(top), sigma: sigmaSurface, kind: desc.has('MI') ? 'MIFG' : (desc.has('BC') || desc.has('PR')) ? 'patchy fog' : 'fog',
      patchy: desc.has('BC') || desc.has('PR'), tag: vv ? 'V meaning, I depth' : 'I (top 200 ft without VV)' });
  } else {
    S.push({ y0: groundY, y1: top != null ? y(top) : y(3000), sigma: sigmaSurface, kind: fog ? 'mist' : 'sub-cloud', tag: 'I' });
  }
  for (const L of p.cloud_layers) {
    if (L.cover === 'VV' || L.height_ft == null || !['BKN', 'OVC'].includes(L.cover)) continue;
    const depth = L.thickness_m_guess != null ? L.thickness_m_guess : STRATUS_DEPTH_FT * FT_M;
    S.push({ y0: y(L.height_ft), y1: y(L.height_ft) + depth, sigma: SIGMA_CLOUD, kind: 'cloud ' + L.cover, tag: 'I (σ_c 0.04, depth ' + (L.thickness_m_guess != null ? 'marine layer' : 'default') + ')' });
  }
  return S;
}

/** Build EnvState for data time tEnv. in: {mode, overridden, reports [{raw, obsTime?, receiptTime?} | raw],
 *  taf (raw | null), live (bool: the latest received report is current), observedFlow, rwyOverride, groundY,
 *  prev (previous EnvState, for the photocell hysteresis / delay and the 60 s weather transition)}. */
export function buildEnvState(tEnv, inp = {}) {
  const groundY = inp.groundY ?? 3;
  const date = new Date(tEnv);
  const sk = skyState(date);
  const sun = sk.sun, moon = sk.moon;
  const towerNight = sun.elTrue <= TOWER_NIGHT_EL;
  // ---- weather
  const idx = indexReports(inp.reports, tEnv);
  const cur = selectReport(idx, tEnv, !!inp.live);
  const d = cur ? cur.d : decodeMetar('');
  const ageMin = cur && cur.obsMs != null ? (tEnv - cur.obsMs) / 60000 : null;
  const p0 = renderParams(d, false);
  const D = cur ? cloudDivisor(d, p0) : 1.0;
  // ---- natural light (USNO Circular 171, V; divisor I)
  const ill = naturalIlluminanceAt(date, SFO, 1);
  const E_clear = ill.total;
  const E = E_clear / D;
  const w = asosNightWeight(E);
  const pr = renderParams(d, w >= 0.5);
  // the data clock "runs" when it moved forward by < 10 min since the previous state (live / replay); a fixed (snapshot,
  // override) or jumping clock (light mode, ?t=, seek) applies photocell switches and new reports at once
  const running = !!(inp.prev && tEnv > inp.prev.tEnv && tEnv - inp.prev.tEnv < 600e3);
  // ---- photocells (hysteresis + delay from prev)
  const Ev_fc = E / 2 / FC_LUX;
  const prevPC = inp.prev && inp.prev.photocell;
  let papiNight = prevPC ? prevPC.papiNight : Ev_fc < (PAPI_DAY_FC + PAPI_NIGHT_FC) / 2;
  let papiPending = prevPC ? prevPC.papiPendingSince : null;
  const want = Ev_fc < PAPI_NIGHT_FC ? true : Ev_fc > PAPI_DAY_FC ? false : papiNight;
  if (want !== papiNight) {
    if (!prevPC || !running) { papiNight = want; papiPending = null; }
    else if (papiPending == null) papiPending = tEnv;
    else if (tEnv - papiPending >= PAPI_DELAY_MS) { papiNight = want; papiPending = null; }
  } else papiPending = null;
  // ---- atmosphere (§4.3)
  const vis = d.visibility || null;
  const visM = vis ? vis.m : null;
  const sigmaDay = extinctionFromVisibility(visM, false), sigmaNight = extinctionFromVisibility(visM, true);
  const sigmaASOS = sigmaDay != null ? (1 - w) * sigmaDay + w * sigmaNight : null;
  const visLowerBound = pr.visibility_is_lower_bound;
  let sigmaSurface = sigmaASOS == null ? SIGMA_CLEAR : visLowerBound ? Math.min(SIGMA_CLEAR, sigmaASOS, SIGMA_10SM_DAY) : sigmaASOS;
  // 60 s data-time transition after a new report (§3.3, I): σ blends (log-linear) from the value shown when the report
  // changed to the new one; a jump of the data clock (light mode, ?t=, replay seek) > 10 min or backwards cancels it
  let transition = null;
  const prevW = inp.prev && inp.prev.wx;
  let sw = { at: null, sigmaFrom: null, fromRaw: null };
  // only while the data clock runs forward (live / replay); a fixed or jumping clock (snapshot, override) switches at once
  if (running && prevW && cur && prevW.raw && prevW.raw !== cur.raw) sw = { at: tEnv, sigmaFrom: inp.prev.atm.sigmaSurface, fromRaw: prevW.raw };
  else if (prevW && cur && prevW.raw === cur.raw && prevW.sw) sw = prevW.sw;
  if (sw.at != null && sw.sigmaFrom != null) {
    const dt = tEnv - sw.at, k = clamp(dt / 60e3, 0, 1);
    if (dt >= 0 && dt < 600e3 && k < 1) { sigmaSurface = Math.exp((1 - k) * Math.log(sw.sigmaFrom) + k * Math.log(sigmaSurface)); transition = { from: sw.fromRaw, k, t0: sw.at }; }
    else if (dt < 0 || dt >= 600e3) sw = { at: null, sigmaFrom: null, fromRaw: null };
  }
  const atm = { sigmaSurface, sigmaASOS, sigmaDay, sigmaNight, visM, visLowerBound, visPrefix: vis ? vis.prefix : null,
    slabs: slabsFor(d, pr, sigmaSurface, groundY), fog: pr.fog, aerosol: pr.aerosol,
    sectors: (d.rmk.vis_sector || []).map(s => ({ dirs: s.dirs, sm: s.sm, sigma: extinctionFromVisibility(s.sm * SM_M, w >= 0.5) })),
    lowerToward: d.rmk.lower_toward || [], visVariable: d.rmk.vis_variable_sm || null, towerVisSM: d.rmk.tower_vis_sm ?? null, surfaceVisSM: d.rmk.surface_vis_sm ?? null,
    fogInGap: d.rmk.fog_in_gap || null, transition };
  // ---- clouds (§4.5)
  const windTo = (d.wind && d.wind.dir_true_deg != null) ? [-Math.sin(d.wind.dir_true_deg * DEG), Math.cos(d.wind.dir_true_deg * DEG)] : [0, 0];
  const spd = pr.wind.speed_m_s;
  const clouds = pr.cloud_layers.filter(L => L.cover !== 'VV' && L.height_ft != null).map(L => {
    const kind = L.type === 'CB' || L.type === 'TCU' ? L.type : L.height_ft < 6500 ? 'stratiform' : L.height_ft <= 20000 ? 'mid' : 'cirriform';
    return { cover: L.cover, base: groundY + L.height_ft * FT_M, baseFt: L.height_ft, resFt: L.height_ft <= 5000 ? 50 : L.height_ft <= 10000 ? 250 : 500,
      thickness: L.thickness_m_guess, thicknessTag: L.thickness_m_guess != null ? 'I (marine layer depth)' : 'renderer default (I)', total: L.summation, own: L.own_fraction, kind,
      drift: [windTo[0] * spd, windTo[1] * spd], driftTag: 'METAR surface wind, not amplified (I; sounding winds not wired)' };
  });
  // ---- precipitation (§4.6; X9 clamp of the Prrrr average into the coded intensity class, I)
  let precip = null;
  if (pr.precip) {
    const P = pr.precip; let rate = P.rate_mm_h;
    if (P.kind === 'rain') { const [lo, hi] = { light: [0, 2.54], moderate: [2.8, 7.62], heavy: [7.62, 1e9] }[P.intensity || 'moderate']; rate = Math.round(clamp(rate, lo, hi) * 100) / 100; }
    precip = { kind: P.kind, intensity: P.intensity, rateMmH: rate, rateRaw: P.rate_mm_h, rateBasis: P.rate_basis + (rate !== P.rate_mm_h ? '; clamped into the coded class (X9, I)' : ''),
      dropsPerM3: P.drops_per_m3_gt_0p5mm, D0mm: P.median_volume_diameter_mm, vFall: P.fall_speed_m_s, showery: P.showery, thunder: P.thunder };
  }
  const lightning = { perMin: pr.lightning.flashes_per_min, atStation: pr.lightning.at_station, vicinity: pr.lightning.vicinity,
    where: pr.lightning.reports.map(r => ({ types: r.types, loc: r.loc })) };
  // ---- wetness initial state (§4.7, I; the state machine integrates in later steps)
  // (the §4.7 state machine that integrates rain rate / drying over time is step 4; until then the start rule only)
  const surface = { wet: pr.surface.precip_now ? 1 : pr.surface.precip_ended_this_hour ? 0.5 : 0, puddle: 0, tag: 'I (start rule; constants NV)' };
  // ---- wind (§4.8; METAR wind is TRUE, JO 7900.5E 13.10)
  const W = d.wind || {};
  const wind = { fromTrue: W.dir_true_deg ?? null, speed: pr.wind.speed_m_s, gust: pr.wind.gust_m_s, peak: pr.wind.peak_since_last_metar_kt != null ? pr.wind.peak_since_last_metar_kt * KT_MS : null,
    variable: !!W.variable, range: pr.wind.range_deg, sockExt: pr.wind.windsock_extension, calm: !!W.calm };
  // ---- night sky (§4.9)
  const lowDeck = (d.sky || []).some(s => ['BKN', 'OVC'].includes(s.cover) && s.height_ft != null && s.height_ft <= 5000);
  const nightSky = { naturalCdM2: NIGHT_NATURAL_CDM2 / D, artificialCdM2: NIGHT_ARTIFICIAL_CDM2 * (lowDeck && towerNight ? OVERCAST_AMP : 1),
    colour: null, colourTag: 'NV (city-light colour, owner Q7)', stars: !(d.sky || []).some(s => ['BKN', 'OVC', 'VV'].includes(s.cover)) ? 'visible' : 'hidden',
    starSource: 'none (Q12 default: takram stars.bin not shipped; no starfield with verified open terms yet)' };
  // ---- light visibility (§4.10)
  const lightVis = { ET: allardThreshold(w), sigmaEye: sigmaSurface };
  // ---- exposure (§8): natural-light target before the clamp; at night the clamp + artificial light set it
  const ev = ev100ForIlluminance(E);
  const exposure = { ev100Target: ev, ev100: clamp(ev, EV_MIN, EV_MAX), min: EV_MIN, max: EV_MAX, ec: 0, ecTag: 'I (compensation below Sun −4°: step 3, QA-tuned)' };
  // ---- TAF
  let taf = null;
  if (inp.taf) { try { taf = decodeTaf(inp.taf); } catch (e) { taf = { raw: inp.taf, error: String(e) }; } }
  const forecast = !!(taf && cur && ageMin != null && ageMin > STALE_MIN);
  const runway = runwayConfigFrom(cur ? d : null, inp.observedFlow, inp.rwyOverride);
  const st = {
    tEnv, mode: inp.mode || 'live', overridden: !!inp.overridden,
    sun: { az: sun.az, el: sun.el, elTrue: sun.elTrue, dir: sk.sunDir, semidiameter: sun.semidiameter },
    moon: { az: moon.az, el: moon.el, dir: sk.moonDir, lit: moon.illuminatedFraction, brightLimbZenithAngle: moon.brightLimbZenithAngle, angularDiameter: moon.angularDiameter, phaseName: moon.phaseName },
    phase: sk.phase, towerNight,
    natural: { E_clear, D, E, sun: ill.sun / D, moon: ill.moon / D },
    photocell: { asosNightW: w, papiNight, papiPendingSince: papiPending, obstructionOn: Ev_fc < OBSTRUCTION_ON_FC, floodsOn: E < FLOODS_ON_LUX, northSkyFc: Ev_fc },
    wx: { raw: cur ? cur.raw : null, obsTime: cur ? cur.obsMs : null, ageMin, stale: ageMin != null ? ageMin > STALE_MIN : true, decoded: cur ? d : null, params: cur ? pr : null,
      taf, forecast, sw, reports: idx.length },
    atm, clouds, sunVisibleP: pr.sun_visible_probability, kcRatio: pr.global_irradiance_ratio,
    precip, lightning, surface, wind, nightSky, lightVis, exposure,
    lighting: null,                                  // step 2: JO 7110.65 controller (js/env/lighting/controller.js)
    runway,
    prov: {
      sun: 'V/T (ephemeris.mjs vs JPL Horizons ≤ 0.01°)', moon: 'V/T', phase: 'V (USNO)', towerNight: 'V (USNO −50′; JO 7110.65 "sunset to sunrise")',
      natural: 'V (USNO C171) + I (divisor D)', photocell: 'V (ASOS 0.5-3 fc; AC 150/5345-28H; AC 70/7460-1N) + I (thresholds, vertical = E/2)',
      wx: 'V (METAR, JO 7900.5E decoding)', atm: 'V (ASOS inversion, 2nd constants) + I (day/night blend, slabs, 10SM clear air)', clouds: 'V (heights, summation) + I (overlap, thickness, drift)',
      sunVisibleP: 'I', kcRatio: '2nd (Kasten & Czeplak 1980)', precip: 'V (Table 9-4, Prrrr) + I (clamp, mid-class)', lightning: 'V (Table 13-7) + I (midpoints)',
      surface: 'I (constants NV)', wind: 'V (true wind) + I (sock shape)', nightSky: 'V (Falchi, Kyba) + I (3 mcd/m², ×10)', lightVis: 'M (Table B-1 fit)',
      exposure: 'M (EV targets) + I (clamp)', lighting: 'step 2', runway: runway.tag || 'I',
    },
  };
  return st;
}

/** One-line HUD text of the EnvState for ?qa=env (spec §11.4): values with their tags. */
export function envHudLines(st) {
  const f = (x, n = 2) => (x == null ? '—' : Number(x).toFixed(n));
  const iso = (ms) => (ms == null ? '—' : new Date(ms).toISOString().replace('.000Z', 'Z'));
  const L = [];
  L.push(`t_env ${iso(st.tEnv)} · ${st.mode}${st.overridden ? ' · OVERRIDE (environment time ≠ traffic time)' : ''}`);
  L.push(`Sun az ${f(st.sun.az, 1)}° el ${f(st.sun.el, 2)}° (true ${f(st.sun.elTrue, 2)}°) · ${st.phase} · tower ${st.towerNight ? 'night' : 'day'} [V/T]`);
  L.push(`Moon az ${f(st.moon.az, 1)}° el ${f(st.moon.el, 1)}° lit ${f(st.moon.lit * 100, 0)} % [V/T]`);
  L.push(`E clear ${f(st.natural.E_clear, 3)} lx ÷ D ${f(st.natural.D, 2)} = ${f(st.natural.E, 3)} lx [V+I] · EV100 ${f(st.exposure.ev100Target, 1)} → ${f(st.exposure.ev100, 1)} [M+I]`);
  L.push(`ASOS night w ${f(st.photocell.asosNightW, 2)} · PAPI ${st.photocell.papiNight ? 'night' : 'day'} · floods ${st.photocell.floodsOn ? 'on' : 'off'} · obstr ${st.photocell.obstructionOn ? 'on' : 'off'} [V+I]`);
  L.push(`report ${st.wx.raw || '—'} · age ${f(st.wx.ageMin, 0)} min${st.wx.stale ? ' · STALE' : ''}${st.wx.forecast ? ' · forecast (TAF)' : ''} [V]`);
  L.push(`σ surface ${st.atm.sigmaSurface.toExponential(2)} m⁻¹${st.atm.visLowerBound ? ' (10SM bound → clear air)' : ''} · ASOS ${st.atm.sigmaASOS != null ? st.atm.sigmaASOS.toExponential(2) : '—'} · E_T ${st.lightVis.ET.toExponential(2)} lx [M+I]`);
  L.push(`clouds ${st.clouds.map(c => `${c.cover}${String(c.baseFt / 100).padStart(3, '0')} own ${f(c.own, 2)}`).join(' ') || 'none'} · sun visible P ${f(st.sunVisibleP, 2)} [V+I]`);
  L.push(`wind ${st.wind.fromTrue == null ? (st.wind.calm ? 'calm' : 'VRB') : f(st.wind.fromTrue, 0) + '°T'} ${f(st.wind.speed / KT_MS, 0)} kt${st.wind.gust ? ' G' + f(st.wind.gust / KT_MS, 0) : ''} · sock ${f(st.wind.sockExt, 2)} [V+I]`);
  if (st.precip) L.push(`precip ${st.precip.kind} ${st.precip.intensity} ${f(st.precip.rateMmH, 2)} mm/h (${st.precip.rateBasis}) [V+I]`);
  L.push(`runway arr ${Object.keys(st.runway.arr).join(',') || '—'} dep ${st.runway.dep.join(',') || '—'} (${st.runway.source}) [${st.runway.tag || 'I'}]`);
  return L;
}

// Short form for the HUD (one line): the same defaults
export const OPEN_QUESTION_SHORT = 'Q7 flood colour/bridge beacon unchanged NV · Q2 FAA ALS stations · Q1 no beacon · Q3 RCL all runways · Q4 blue edges inf · Q10 TBL 3-4-7 · Q5/6 REIL NV, PAPI HG4 20 % · Q8 ?wx= only · Q9 ADS-B>METAR>West · Q12 no takram/stars · Q13 photographic · Q11 step 2 · Q14 3 mcd/m² · Q15 no socks · Q16 NV';
// Open owner questions (spec §12): the default used for each until the owner answers (all I), shown in the ?qa=env HUD.
export const OPEN_QUESTION_DEFAULTS = [
  'Q7 night photos: apron flood colour / bridge beacon / glazing glow unchanged (parameters, NV)',
  'Q2 pier ALS stations: FAA stations from the landing threshold (fixtures std)',
  'Q1 rotating beacon: not drawn (position unknown)',
  'Q3 RCL: on all four runways (CS + NASR)',
  'Q4 taxiway lights: current blue edge lights, inf; no green CL / stop bars / RGLs',
  'Q10 28L MALSR: separate controls, TBL 3-4-7',
  'Q5/Q6 REIL style NV; PAPI HG4 aiming, night 20 %',
  'Q8 archived-weather presets: ?wx= QA hook only, no user menu',
  'Q9 runway config: ADS-B flow, else METAR wind (3-5-1), else West Plan; no D-ATIS',
  'Q12 takram atmosphere: not adopted (no GPU test here); no stars.bin, no starfield',
  'Q13 night look: photographic (auto-exposed)',
  'Q11 parked nav/logo lights: unchanged until the step-2 aircraft-light logic',
  'Q14 artificial sky 3 mcd/m2 (parameter); Q15 windsocks not drawn; Q16 wetness constants NV',
];
