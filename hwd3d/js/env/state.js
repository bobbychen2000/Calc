// Forked from sfo3d/js/env/state.js @ a967f9b. Kept: EnvState (data-clock weather selection, natural light, photocells,
// fog slabs / horizontal structure, clouds, precipitation, lightning, surface wetness start rule, wind, night sky, light
// visibility, exposure) and the HUD lines. Changed: observer = HWD (ephemeris OBSERVER), FIELD_ELEV_FT 52.1 (FAA NASR),
// routine METAR minute 54 [verify], TWR VIS split height 12 m (HWD tower eye) [inf], the runway configuration (HWD
// west / east flow from the ADS-B flow or the METAR wind, replacing the SFO West / Southeast plans), IAP_ENDS = {28L}
// (LOC/DME, NASR), the open-question defaults. Dropped: the SFO airfield-lighting controller (lighting/controller.js:
// SFO ALS / REIL / TDZ fixtures; HWD fixtures are not sourced) - st.lighting is null.
// EnvState: the one environment object both renderers consume (docs/research/environment_spec.md §3.6). Built from the
// data clock (js/env/clock.js), the current METAR/SPECI (+ TAF) decoded by js/env/wx/metar.js, the ephemeris
// (js/env/ephemeris.js) and the runway configuration (§3.5). Pure ES module, no DOM: Node tests in
// tools/env/test_env_state.mjs reproduce the environment fields of the 14 real-weather presets
// (tools/env/fixtures/env_presets.json, written by tools/env/env_spec_checks.py).
// `lighting` = the JO 7110.65 controller output for this state (js/env/lighting/controller.js, step 2, gate A-CTL).
// Not computed here (later steps): slab/cloud/rain rendering (step 3-4). Every field carries its provenance tag in `prov` (V / M / I / 2nd / NV, spec tag table).
import { skyState, naturalIlluminanceAt, ev100ForIlluminance, OBSERVER } from './ephemeris.js';
import { decodeMetar, decodeTaf, renderParams, extinctionFromVisibility, FT_M, KT_MS, SM_M } from './wx/metar.js';
import { tafAt } from './wx/taf.js';
// HWD: no airfield-lighting controller yet (fixture positions are not sourced, data/hwd_airport.json not_yet_sourced;
// Phase 4). st.lighting stays null.
const controllerFromEnv = () => null, controllerHud = () => '';
import { dropsAbove, medianVolumeDiameter, fallSpeed, DRIZZLE_D, DRIZZLE_V } from './atmo/weather_fx.js';

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
export const FIELD_ELEV_FT = 52.1;             // FAA NASR APT_BASE ELEV (HWD); METAR heights are above field elevation (JO 7900.5E 10.8)
// KHWD routine METAR minute: hh:54 [verify]: one report seen so far ('METAR KHWD 130154Z ...', aviationweather.gov
// 2026-11-13, fork map 2.6 / measurements); sfo3d used 56 for KSFO
export const ROUTINE_MINUTE = 54;
// Runway headings (true, deg): the airport grid (CLAUDE.md: s along 117.83°, t along 27.83°)
// HWD runway directions (deg true): FAA NASR TRUE_ALIGNMENT 120 / 300 (js/geo.js RWY_ENDS trueAln); both runways parallel
const RWY_HDG = { '28': 300, '10': 120 };

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

// FAA Order 8400.9 "National Safety and Operational Criteria for Runway Use Programs" (1981, active; PDF cached
// refs/cache/env_src/faa_order_8400-9.pdf, read 2026-11-07, close-out round 3 env-5: V) ¶7d(1): clear and dry runways - the
// crosswind component INCLUDING GUSTS must not be greater than 20 kt (unless Flight Standards approves more), the
// tailwind component not greater than 5 kt (7 kt where anemometers are installed near the touchdown zone / departure
// end: SFO's NV, the 5-kt value also reproduces SFO's climatology, above); runways not clear or not dry - ¶7d(2): crosswind
// incl. gusts <= 15 kt and "(b) No tailwind component may be present except the nominal range of winds reported as calm
// (0-3 knots) may be considered to have no tailwind component" (pdftotext of the cached PDF, re-read 2026-11-09): the
// 3 kt bound applies to the REPORTED WIND SPEED (gusts included), not to the tailwind component - a wet runway with any
// tailwind component fails unless the reported wind is 0-3 kt (close-out round 5: the code had accepted wet tailwind
// COMPONENTS up to 3 kt, so '18004KT -RA' kept the West Plan with 1.9 kt on 28). A plan is acceptable when its arrival
// runway meets them; the West Plan unless it fails and the Southeast Plan does not (both fail: the smaller excess). "Not
// dry" = precipitation in the METAR's present weather (I: the runway condition itself is not reported in the METAR).
export const TAILWIND_SE_KT = 5, CROSSWIND_SE_KT = 20, WET_CROSSWIND_KT = 15, WET_CALM_KT = 3;
/** @deprecated the wet rule's 3 kt is the calm wind speed (WET_CALM_KT), not a tailwind-component limit */
export const WET_TAILWIND_KT = WET_CALM_KT;
// HWD: the only charted instrument approach whose type is in the data is the 28L LOC/DME (FAA NASR, js/geo.js RWY_ENDS
// ils). Other HWD approach plates (RNAV / GPS) were not read [verify]; they are not listed here.
export const IAP_ENDS = new Set(['28L']);
// HWD runway configuration (replaces sfo3d's SFO West / Southeast plans, which do not apply): observed ADS-B flow (the
// caller's runway events) > METAR wind: the direction pair (28L/28R or 10L/10R) with the headwind component, calm or a
// tailwind below TAILWIND_SE_KT keeps west flow (28) [inf: 92 % of low airborne fixes in the recorded week were
// westbound, PLAN §3; one west-flow week]; the FAA Order 8400.9 dry / wet limits are applied as in sfo3d.
export function runwayConfigFrom(d, observed, override) {
  if (override) return override;
  if (observed && observed.n > 0 && (observed.arr.length || observed.dep.length)) {
    const arr = {}; for (const e of observed.arr) arr[e] = 'observed'; return { arr, dep: observed.dep.slice(), source: 'ADS-B flow', tag: 'M' };
  }
  const w = d && d.wind; const kt = w && w.speed_kt; const dir = w && w.dir_true_deg; const kX = Math.max(kt || 0, (w && w.gust_kt) || 0);
  const comp = (rw) => (kt != null && dir != null) ? { tail: -kt * Math.cos((dir - RWY_HDG[rw]) * DEG), cross: Math.abs(kX * Math.sin((dir - RWY_HDG[rw]) * DEG)) } : { tail: 0, cross: 0 };
  const c28 = comp('28'), c10 = comp('10');
  const wet = !!(d && (d.weather || []).some(x => (x.precip || []).length));
  const calm = kX <= WET_CALM_KT;
  const lim = wet ? { tail: calm ? Infinity : 0 } : { tail: TAILWIND_SE_KT };
  const west = wet ? (calm || c28.tail <= 0) : c28.tail < lim.tail;
  const P = west ? [['28L', '28R'], ['28L', '28R']] : [['10L', '10R'], ['10L', '10R']];
  const vis = d && d.visibility ? d.visibility.sm : null, ceil = d ? d.ceiling_ft : null;
  const instr = (vis != null && vis < 3) || (ceil != null && ceil < 1000);   // basic VFR minima, 14 CFR 91.155 (I: used as the switch)
  const arr = {}; for (const e of P[0]) arr[e] = instr && IAP_ENDS.has(e) ? 'instrument' : 'unknown';
  const why = `28 tail ${c28.tail.toFixed(1)} kt / 10 tail ${c10.tail.toFixed(1)} kt (${wet ? 'wet' : 'dry'}): ${west ? 'west flow (28)' : 'east flow (10)'}`;
  return { arr, dep: P[1], plan: west ? 'west' : 'east', tail28: c28.tail, cross28: c28.cross, wet, source: 'METAR fallback, ' + why, tag: 'I (HWD flow from the METAR wind; FAA Order 8400.9 ¶7d limits V)' };
}

// ---------------------------------------------------------------------------------------------- vertical structure
// Review round 1 (truth1-3/-5, look1-2) changes, all I unless stated:
//  - a layer reported below MIN_CLOUD_FT (e.g. 'FG BKN000', 'PRFG BKN000': a partial obscuration by the surface fog, not a
//    cloud and not a ceiling, JO 7900.5E 9.3 / spec §4.4 'FG without VV') is no cloud slab: the fog slab is it (it used to
//    become a 1,000-ft cloud slab from the ground, σ 0.04, overlapping the fog: the lights died 2.5× short of the RVR);
//  - FG with a ceiling at or below STRATUS_DEPTH_FT: the fog reaches the ceiling (the decoder's top_ft_min: no clear gap
//    under a low deck); otherwise FOG_TOP_FT (200 ft) without VV;
//  - VV (indefinite ceiling, "sky obscured", JO 7900.5E 10.x: VV = the vertical visibility INTO the obscuration): the
//    surface layer reaches the VV height with the horizontal σ (it sets the lights' range, spec §4.10), and above it an
//    obscuration slab of σ = max(3 / VV, σ_surface) (Koschmieder: a vertical visual range of VV needs an optical depth of
//    ~3 within VV; the surface σ alone gave τ 1.07 over VV002, the Moon disc showed at 28 % through it) and
//    STRATUS_DEPTH_FT deep: the sky, the Sun / Moon disc and the Sun / Moon light are hidden by it;
//  - TWR VIS / SFC VIS (JO 7900.5E 8.3, 13.24; "the lower value ... prevailing ... the other value must be a remark"): the
//    surface layer splits at TWR_SPLIT_M (below the tower cab eye, 59 m in the buildings track's tower model,
//    data/buildings3d/manifest.json tower anchors cab_eye_h, I): surface visibility below, tower visibility above.
// TWR_SPLIT_M: below the HWD tower cab eye (~13.5 m above ground: OSM top 15.85 m - 2.4 m, js/world/site.js) [inf]
export const MIN_CLOUD_FT = 100, TWR_SPLIT_M = 12, CIRRUS_MIN_FT = 20000;
// aerosol layer aloft (smoke / haze, truth2-4): vertical optical depth = own fraction × AEROSOL_TAU over AEROSOL_DEPTH_FT (I)
export const AEROSOL_TAU = 1.0, AEROSOL_DEPTH_FT = 1000;
// Horizontal structure of the surface layer (spec §4.4 / §7.3; review truth1-6). It modulates the LOWEST slab only, in the
// same form in the scene fog (js/three/sky.js fogNode / bgTransmittance) and the lights' optical depth
// (js/env/atmo/sky_model.js slabTau, horizTau):
//  - BCFG / PRFG (JO 7900.5E: "may be reported when visibility is equal to or greater than 7 miles", via weather.md §2,
//    V): fog patches around the station (within PATCH_R_M of the ARP, sky_model.js; I), area cover BC 0.15 / PR 0.3 (I:
//    "patches" vs "a substantial part"), patch scale ~300-700 m (I, spec 200-500 m), σ in a patch = the fog bound
//    σ(5/8 SM) ("FG reduces horizontal visibility to less than 5/8 SM", V; the value I); the clear parts keep the
//    prevailing σ. Consistency with a 10SM prevailing visibility (M on I): the mean optical depth the BC patches add along
//    a radial at night, 0.15 × σ(5/8 SM) 6.1e-3 × ~1,750 m = 1.6, stays below the 10SM bound 2.9 − clear air 0.53;
//    with 0.25 over 2.5 km it was 3.8 (patches thicker than the report);
//  - sector visibility 'VIS NE E M1/4' (13.26) and 'VIS LWR W' (no value: 2 × the prevailing σ, I): a cosine lobe ±45°
//    about each sector direction seen from the station (ARP, I), from the station outwards;
//  - 'FG IN GAP W' (96 KSFO reports, spec §4.4, M): a fog bank in that direction from GAP_R0_M out (I: the San Bruno Gap
//    opens ~3-6 km W of the field), σ(5/8 SM), top STRATUS_DEPTH_FT (I);
//  - 'VIS 1/2V2 1/2' (13.25): the prevailing σ swings log-linearly between the two values with a VIS_VAR_PERIOD_S period
//    in data time (I).
export const PATCH_VIS_SM = 5 / 8, PATCH_COVER = { BC: 0.15, PR: 0.3 }, GAP_R0_M = 3000, VIS_VAR_PERIOD_S = 600, LWR_FACTOR = 2;
const DIR16 = { N: 0, NNE: 22.5, NE: 45, ENE: 67.5, E: 90, ESE: 112.5, SE: 135, SSE: 157.5, S: 180, SSW: 202.5, SW: 225, WSW: 247.5, W: 270, WNW: 292.5, NW: 315, NNW: 337.5 };
/** Horizontal modulation of the surface slab: {patch: {cover, sigma} | null, lobes: [{az (deg true), sigma, r0 (m), top (y), what}]}. */
function horizontalFor(d, sigmaSurface, night, groundY, topY) {
  const r = d.rmk || {}; const wx = d.weather || [];
  const sig = (sm) => Math.max(sigmaSurface, extinctionFromVisibility(sm * SM_M, night));
  const lobes = [];
  for (const s of r.vis_sector || []) for (const dd of s.dirs || []) if (DIR16[dd] != null) lobes.push({ az: DIR16[dd], sigma: sig(s.sm * (s.prefix === 'M' ? 0.99 : 1)), r0: 0, top: topY, what: 'VIS ' + dd + ' ' + (s.prefix || '') + s.sm });
  for (const l of r.lower_toward || []) if (l.what === 'VIS' && DIR16[l.dir] != null) lobes.push({ az: DIR16[l.dir], sigma: LWR_FACTOR * sigmaSurface, r0: 0, top: topY, what: 'VIS LWR ' + l.dir });
  if (r.fog_in_gap) { const dir = String(r.fog_in_gap).split(/\s+/).pop(); if (DIR16[dir] != null) lobes.push({ az: DIR16[dir], sigma: sig(PATCH_VIS_SM), r0: GAP_R0_M, top: groundY + STRATUS_DEPTH_FT * FT_M, what: 'FG IN GAP ' + dir }); }
  let patch = null;
  const pf = wx.find(w => !w.vicinity && (w.phenomena || []).includes('FG') && (w.descriptor === 'BC' || w.descriptor === 'PR'));
  if (pf) patch = { kind: pf.descriptor + 'FG', cover: PATCH_COVER[pf.descriptor], sigma: sig(PATCH_VIS_SM) };
  return (patch || lobes.length) ? { patch, lobes: lobes.slice(0, 4), tag: 'V (remarks, JO 7900.5E 13.25/13.26) + I (lobe ±45°, patch cover/scale/σ, gap distance)' } : null;
}

/** Vertical σ(y) profile (§4.4): piecewise-constant slabs in world y (m) = groundY + ft × 0.3048, sorted, non-overlapping. */
function slabsFor(d, p, sigmaSurface, groundY, night) {
  const y = (ft) => groundY + ft * FT_M;
  const S = [];
  const wx = d.weather || [];
  const desc = new Set(wx.filter(w => !w.vicinity).map(w => w.descriptor));
  const vv = (d.sky || []).find(s => s.cover === 'VV' && s.height_ft != null);
  const ceil = d.ceiling_ft;
  const fog = p.fog;
  let top = ceil != null && ceil > 0 ? ceil : null;            // sub-cloud slab up to the ceiling (or VV)
  let surf;
  if (fog && fog.kind === 'fog') {
    top = desc.has('MI') ? MIFG_TOP_FT : vv ? vv.height_ft : (top != null && top <= STRATUS_DEPTH_FT ? top : FOG_TOP_FT);
    // MIFG (shallow fog, JO 7900.5E 13.13e: "apparent visibility in the fog layer less than 5/8 SM", via weather.md §2,
    // V): the prevailing visibility is measured above it, so the 0-6 ft slab gets at least σ(5/8 SM) (lower bound, V
    // meaning + I value; review truth2-5: it had the prevailing σ, i.e. clear air for '10SM MIFG')
    const mi = desc.has('MI');
    surf = { y0: groundY, y1: y(top), sigma: mi ? Math.max(sigmaSurface, extinctionFromVisibility(PATCH_VIS_SM * SM_M, night)) : sigmaSurface,
      kind: mi ? 'MIFG' : (desc.has('BC') || desc.has('PR')) ? 'patchy fog' : 'fog',
      patchy: desc.has('BC') || desc.has('PR'), tag: mi ? 'V (MIFG < 5/8 SM in the layer) + I (σ(5/8 SM) lower bound, depth 6 ft)' : vv ? 'V meaning, I depth' : top === FOG_TOP_FT ? 'I (top 200 ft without VV)' : 'I (to the ceiling, decoder top_ft_min)' };
  } else {
    surf = { y0: groundY, y1: top != null ? y(top) : y(3000), sigma: sigmaSurface, kind: fog ? 'mist' : 'sub-cloud', tag: 'I' };
  }
  // TWR VIS / SFC VIS: surface visibility below TWR_SPLIT_M, tower visibility above (I)
  const r = d.rmk || {}; const vis = d.visibility;
  if (!desc.has('MI') && vis && vis.sm != null && (r.tower_vis_sm != null || r.surface_vis_sm != null) && surf.y1 > groundY + TWR_SPLIT_M) {
    const sOf = (sm) => sm >= 10 ? Math.min(SIGMA_CLEAR, sigmaSurface) : extinctionFromVisibility(sm * SM_M, night);
    const twrSm = r.tower_vis_sm != null ? r.tower_vis_sm : vis.sm, sfcSm = r.surface_vis_sm != null ? r.surface_vis_sm : vis.sm;
    const lo = r.surface_vis_sm != null ? sOf(sfcSm) : sigmaSurface, hi = r.tower_vis_sm != null ? sOf(twrSm) : sigmaSurface;
    S.push({ ...surf, y1: groundY + TWR_SPLIT_M, sigma: lo, kind: surf.kind + ' (SFC VIS ' + sfcSm + ')', tag: 'V (JO 7900.5E 8.3) + I (split height)' });
    S.push({ ...surf, y0: groundY + TWR_SPLIT_M, sigma: hi, kind: surf.kind + ' (TWR VIS ' + twrSm + ')', patchy: false, tag: 'V (JO 7900.5E 8.3) + I (split height)' });
  } else S.push(surf);
  const surfTop = S[S.length - 1].y1;
  // VV: an obscuration above the surface layer (I; header)
  if (vv && !desc.has('MI')) {
    const vvM = Math.max(vv.height_ft * FT_M, 15);
    S.push({ y0: Math.max(surfTop, y(vv.height_ft)), y1: Math.max(surfTop, y(vv.height_ft)) + STRATUS_DEPTH_FT * FT_M, sigma: Math.max(3 / vvM, sigmaSurface), kind: 'obscuration VV' + String(vv.height_ft / 100).padStart(3, '0'),
      obscuration: true, tag: 'V (VV = vertical visibility into the obscuration) + I (σ = 3/VV, depth 1,000 ft)' });
  }
  for (const L of p.cloud_layers) {
    if (L.cover === 'VV' || L.height_ft == null || L.height_ft < MIN_CLOUD_FT || !['BKN', 'OVC'].includes(L.cover)) continue;
    const depth = L.thickness_m_guess != null ? L.thickness_m_guess : STRATUS_DEPTH_FT * FT_M;
    S.push({ y0: y(L.height_ft), y1: y(L.height_ft) + depth, sigma: SIGMA_CLOUD, kind: 'cloud ' + L.cover, tag: 'I (σ_c 0.04, depth ' + (L.thickness_m_guess != null ? 'marine layer' : 'default') + ')' });
  }
  // sorted and non-overlapping (photometry.opticalDepth / the shader assume it): a slab starts where the one below ends
  S.sort((a, b) => a.y0 - b.y0);
  for (let i = 1; i < S.length; i++) { if (S[i].y0 < S[i - 1].y1) S[i].y0 = Math.min(S[i - 1].y1, S[i].y1); }
  let out = S.filter((s, i) => i === 0 || s.y1 > s.y0);
  // smoke / haze aloft ('FU FEW004', decoder aerosol_layers, JO 7900.5E 13.35, V): an aerosol slab, not a cloud (review
  // truth2-4): extra σ = own × AEROSOL_TAU / depth over AEROSOL_DEPTH_FT from the reported base, added to the slabs it
  // overlaps (split at its bounds); where no slab exists, clear air + the extra σ. All values I.
  for (const L of p.aerosol_layers || []) {
    if (L.height_ft == null) continue;
    const a = y(L.height_ft), b = a + AEROSOL_DEPTH_FT * FT_M, dS = (L.own_fraction || 0) * AEROSOL_TAU / (b - a);
    if (!(dS > 0)) continue;
    const res = []; let cur = a;
    for (const sl of out) {
      if (sl.y1 <= a || sl.y0 >= b) { res.push(sl); continue; }
      if (sl.y0 < a) res.push({ ...sl, y1: a });
      if (sl.y0 > cur) res.push({ y0: cur, y1: sl.y0, sigma: SIGMA_CLEAR + dS, kind: 'smoke aloft ' + L.aerosol, aerosol: L.aerosol, tag: 'V (13.35 obscuration aloft) + I (τ, depth)' });
      res.push({ ...sl, y0: Math.max(sl.y0, a), y1: Math.min(sl.y1, b), sigma: sl.sigma + dS, kind: sl.kind + ' + ' + L.aerosol + ' aloft', aerosol: L.aerosol });
      if (sl.y1 > b) res.push({ ...sl, y0: b, horiz: undefined });
      cur = Math.max(cur, sl.y1);
    }
    if (cur < b) res.push({ y0: cur, y1: b, sigma: SIGMA_CLEAR + dS, kind: 'smoke aloft ' + L.aerosol, aerosol: L.aerosol, tag: 'V (13.35 obscuration aloft) + I (τ, depth)' });
    out = res.sort((u, v) => u.y0 - v.y0).filter(sl => sl.y1 > sl.y0);
  }
  return out;
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
  const ageMin = cur && cur.obsMs != null ? (tEnv - cur.obsMs) / 60000 : null;
  // Beyond the latest METAR (§3.3, I): no report, or the latest older than 90 min -> the prevailing conditions of the
  // TAF in force (issued <= t_env, valid at t_env; js/env/wx/taf.js, AIM 7-1-28 FM / BECMG), labelled "forecast"
  let taf = null;
  if (inp.taf) { try { taf = decodeTaf(inp.taf); } catch (e) { taf = { raw: inp.taf, error: String(e) }; } }
  const fc = taf && (!cur || (ageMin != null && ageMin > STALE_MIN)) ? tafAt(taf, tEnv) : null;
  const d = fc ? fc.d : cur ? cur.d : decodeMetar('');
  const wxKey = fc ? fc.key : cur ? cur.raw : null;     // what the weather fields come from (transition key)
  const p0 = renderParams(d, false, null, ROUTINE_MINUTE);
  const D = cur || fc ? cloudDivisor(d, p0) : 1.0;
  // ---- natural light (USNO Circular 171, V; divisor I)
  const ill = naturalIlluminanceAt(date, OBSERVER, 1);
  const E_clear = ill.total;
  const E = E_clear / D;
  const w = asosNightWeight(E);
  const pr = renderParams(d, w >= 0.5, null, ROUTINE_MINUTE);
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
  // 'VIS vnVvx' (13.25): the prevailing σ swings between the two values in data time (I; header of slabsFor)
  const vVar = d.rmk && d.rmk.vis_variable_sm;
  let visSwing = null;
  if (vVar && !visLowerBound && sigmaASOS != null) {
    const sOf = (sm) => (1 - w) * extinctionFromVisibility(sm * SM_M, false) + w * extinctionFromVisibility(sm * SM_M, true);
    const k = 0.5 - 0.5 * Math.cos(2 * Math.PI * (tEnv / 1000) / VIS_VAR_PERIOD_S);
    sigmaSurface = Math.exp((1 - k) * Math.log(sOf(vVar[1])) + k * Math.log(sOf(vVar[0]))); visSwing = { lo: vVar[0], hi: vVar[1], k };
  }
  // 60 s data-time transition after a new report (§3.3, I): σ blends (log-linear) from the value shown when the report
  // changed to the new one; a jump of the data clock (light mode, ?t=, replay seek) > 10 min or backwards cancels it
  let transition = null;
  const prevW = inp.prev && inp.prev.wx;
  let sw = { at: null, sigmaFrom: null, fromRaw: null };
  // only while the data clock runs forward (live / replay); a fixed or jumping clock (snapshot, override) switches at once
  if (running && prevW && wxKey && prevW.key && prevW.key !== wxKey) sw = { at: tEnv, sigmaFrom: inp.prev.atm.sigmaSurface, fromRaw: prevW.key };
  else if (prevW && wxKey && prevW.key === wxKey && prevW.sw) sw = prevW.sw;
  if (sw.at != null && sw.sigmaFrom != null) {
    const dt = tEnv - sw.at, k = clamp(dt / 60e3, 0, 1);
    if (dt >= 0 && dt < 600e3 && k < 1) { sigmaSurface = Math.exp((1 - k) * Math.log(sw.sigmaFrom) + k * Math.log(sigmaSurface)); transition = { from: sw.fromRaw, k, t0: sw.at }; }
    else if (dt < 0 || dt >= 600e3) sw = { at: null, sigmaFrom: null, fromRaw: null };
  }
  const atm = { sigmaSurface, sigmaASOS, sigmaDay, sigmaNight, visM, visLowerBound, visPrefix: vis ? vis.prefix : null,
    slabs: slabsFor(d, pr, sigmaSurface, groundY, w >= 0.5), fog: pr.fog, aerosol: pr.aerosol, visSwing,
    sectors: (d.rmk.vis_sector || []).map(s => ({ dirs: s.dirs, sm: s.sm, sigma: extinctionFromVisibility(s.sm * SM_M, w >= 0.5) })),
    lowerToward: d.rmk.lower_toward || [], visVariable: d.rmk.vis_variable_sm || null, towerVisSM: d.rmk.tower_vis_sm ?? null, surfaceVisSM: d.rmk.surface_vis_sm ?? null,
    fogInGap: d.rmk.fog_in_gap || null, transition };
  atm.horiz = horizontalFor(d, sigmaSurface, w >= 0.5, groundY, atm.slabs[0] ? atm.slabs[0].y1 : groundY + 914);
  if (atm.horiz) atm.slabs[0].horiz = atm.horiz;     // the lowest slab carries it (renderSlabs / slabTau / the shader)
  // ---- clouds (§4.5)
  const windTo = (d.wind && d.wind.dir_true_deg != null) ? [-Math.sin(d.wind.dir_true_deg * DEG), Math.cos(d.wind.dir_true_deg * DEG)] : [0, 0];
  const spd = pr.wind.speed_m_s;
  const clouds = pr.cloud_layers.filter(L => L.cover !== 'VV' && L.height_ft != null).map(L => {
    // étage by base height (I): low < 6,500 ft (WMO 2 km), high ≥ CIRRUS_MIN_FT; the WMO high étage starts at 5 km
    // (16,500 ft) in temperate latitudes with the middle étage reaching 7 km, so the overlap is resolved at 20,000 ft:
    // KSFO observers' SCT200 / BKN200 are drawn as cirrus (review truth2-11: '<= 20000' classed them 'mid', opaque)
    const kind = L.type === 'CB' || L.type === 'TCU' ? L.type : L.height_ft < 6500 ? 'stratiform' : L.height_ft < CIRRUS_MIN_FT ? 'mid' : 'cirriform';
    return { cover: L.cover, base: groundY + L.height_ft * FT_M, baseFt: L.height_ft, resFt: L.height_ft <= 5000 ? 50 : L.height_ft <= 10000 ? 250 : 500,
      thickness: L.thickness_m_guess, thicknessTag: L.thickness_m_guess != null ? 'I (marine layer depth)' : 'renderer default (I)', total: L.summation, own: L.own_fraction, kind,
      drift: [windTo[0] * spd, windTo[1] * spd], driftTag: 'METAR surface wind, not amplified (I; sounding winds not wired)' };
  });
  // ---- precipitation (§4.6; X9 clamp of the Prrrr average into the coded intensity class, I)
  let precip = null;
  if (pr.precip) {
    const P = pr.precip; let rate = P.rate_mm_h;
    if (P.kind === 'rain') { const [lo, hi] = { light: [0, 2.54], moderate: [2.8, 7.62], heavy: [7.62, 1e9] }[P.intensity || 'moderate']; rate = Math.round(clamp(rate, lo, hi) * 100) / 100; }
    // drop parameters from the CLAMPED rate with the same functions the renderer uses (js/env/atmo/weather_fx.js
    // rainParams), so EnvState, the HUD and the drawn rain are one value set (review truth2-3: they kept the unclamped
    // Prrrr values; the drizzle fall speed was the decoder's 1 m/s while 1.5 m/s was drawn)
    const isRain = P.kind === 'rain', isDz = P.kind === 'drizzle';
    const Rr = Math.max(0.05, rate || 1);
    const D0 = isRain ? medianVolumeDiameter(Rr) : isDz ? DRIZZLE_D : null;
    precip = { kind: P.kind, intensity: P.intensity, rateMmH: rate, rateRaw: P.rate_mm_h, rateBasis: P.rate_basis + (rate !== P.rate_mm_h ? '; clamped into the coded class (X9, I)' : ''),
      dropsPerM3: isRain ? Math.round(dropsAbove(Rr)) : null, D0mm: D0 != null ? Math.round(D0 * 100) / 100 : null,
      vFall: isRain ? Math.round(fallSpeed(D0) * 100) / 100 : isDz ? DRIZZLE_V : null, dropTag: isRain ? 'Marshall–Palmer at the clamped rate (weather_fx)' : isDz ? 'drizzle 0.3 mm, 1.5 m/s (I, weather_fx)' : null,
      showery: P.showery, thunder: P.thunder,
      hail: P.hail || null, hailTag: P.hail ? (P.kind === 'rain' ? 'with rain: drawn as the rain (hail stones not drawn, size / fall speed NV)' : 'not drawn (size / fall speed NV)') : null };
  }
  const lightning = { perMin: pr.lightning.flashes_per_min, atStation: pr.lightning.at_station, vicinity: pr.lightning.vicinity,
    where: pr.lightning.reports.map(r => ({ types: r.types, loc: r.loc })) };
  // ---- wetness initial state (§4.7, I; the state machine integrates in later steps)
  // (the §4.7 state machine that integrates rain rate / drying over time is step 4; until then the start rule only)
  // Reported amounts for the start state (review truth2-6): Prrrr = precipitation since the last routine METAR (JO 7900.5E
  // 13.46, hundredths of an inch; P0000 = a trace, < 0.01 in), 6RRRR = the 3- or 6-hour amount (13.48; 3 h at 03/09/15/21Z,
  // 6 h at 00/06/12/18Z reports, V). The window of Prrrr runs from the last routine report at hh:56 (as the decoder's rate).
  const sf = pr.surface; let amount = null;
  if (sf.precip_since_last_metar_in != null || sf.precip_3or6h_in != null) {
    const RM = ROUTINE_MINUTE; const min = d.time && d.time.minute != null ? (d.time.minute === RM ? 60 : ((d.time.minute - RM) % 60 + 60) % 60 || 60) : 60;
    const hr = d.time && d.time.hour != null ? d.time.hour : null;
    const h6 = hr != null && d.time.minute >= 50 ? ((hr + 1) % 24) % 6 === 0 ? 6 : 3 : 6;
    amount = { hourlyMm: sf.precip_since_last_metar_in != null ? sf.precip_since_last_metar_in * 25.4 : null, hourlyH: min / 60,
      sixMm: sf.precip_3or6h_in != null ? sf.precip_3or6h_in * 25.4 : null, sixH: h6, tag: 'V (Prrrr 13.46 / 6RRRR 13.48)' };
  }
  const surface = { wet: sf.precip_now ? 1 : sf.precip_ended_this_hour ? 0.5 : 0, puddle: 0, amount, rateMmH: precip ? precip.rateMmH : null,
    tag: 'I (start rule from the reported amounts; constants NV)' };
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
  // ---- forecast label (TAF in use, above)
  const forecast = fc ? { issued: taf.issued, applied: fc.applied, text: fc.text, groups: fc.groups.map(g => g.id), validFrom: fc.validFromMs, validTo: fc.validToMs, tag: 'I (prevailing TAF conditions; TEMPO/PROB not rendered)' } : null;
  const runway = runwayConfigFrom(cur || fc ? d : null, inp.observedFlow, inp.rwyOverride);
  const st = {
    tEnv, mode: inp.mode || 'live', overridden: !!inp.overridden,
    sun: { az: sun.az, el: sun.el, elTrue: sun.elTrue, dir: sk.sunDir, semidiameter: sun.semidiameter },
    moon: { az: moon.az, el: moon.el, dir: sk.moonDir, lit: moon.illuminatedFraction, brightLimbZenithAngle: moon.brightLimbZenithAngle, angularDiameter: moon.angularDiameter, phaseName: moon.phaseName },
    phase: sk.phase, towerNight,
    natural: { E_clear, D, E, sun: ill.sun / D, moon: ill.moon / D },
    photocell: { asosNightW: w, papiNight, papiPendingSince: papiPending, obstructionOn: Ev_fc < OBSTRUCTION_ON_FC, floodsOn: E < FLOODS_ON_LUX, northSkyFc: Ev_fc },
    wx: { raw: cur ? cur.raw : null, obsTime: cur ? cur.obsMs : null, ageMin, stale: ageMin != null ? ageMin > STALE_MIN : true, decoded: cur || fc ? d : null, params: cur || fc ? pr : null,
      taf, forecast, key: wxKey, sw, reports: idx.length, none: !cur && !fc },
    atm, clouds, sunVisibleP: pr.sun_visible_probability, kcRatio: pr.global_irradiance_ratio,
    precip, lightning, surface, wind, nightSky, lightVis, exposure,
    lighting: null,                                  // set below: JO 7110.65 controller (js/env/lighting/controller.js)
    runway,
    prov: {
      sun: 'V/T (ephemeris.mjs vs JPL Horizons ≤ 0.01°)', moon: 'V/T', phase: 'V (USNO)', towerNight: 'V (USNO −50′; JO 7110.65 "sunset to sunrise")',
      natural: 'V (USNO C171) + I (divisor D)', photocell: 'V (ASOS 0.5-3 fc; AC 150/5345-28H; AC 70/7460-1N) + I (thresholds, vertical = E/2)',
      wx: fc ? 'I (forecast: prevailing TAF conditions, AIM 7-1-28; latest METAR stale or none)' : cur ? 'V (METAR, JO 7900.5E decoding)' : 'I (no weather data: no report at or before t_env and no TAF in force; clear default drawn)', atm: 'V (ASOS inversion, 2nd constants) + I (day/night blend, slabs, 10SM clear air)', clouds: 'V (heights, summation) + I (overlap, thickness, drift)',
      sunVisibleP: 'I', kcRatio: '2nd (Kasten & Czeplak 1980)', precip: 'V (Table 9-4, Prrrr) + I (clamp, mid-class)', lightning: 'V (Table 13-7) + I (midpoints)',
      surface: 'I (constants NV)', wind: 'V (true wind) + I (sock shape)', nightSky: 'V (Falchi, Kyba) + I (3 mcd/m², ×10)', lightVis: 'M (Table B-1 fit)',
      exposure: 'M (EV targets) + I (clamp)', lighting: 'V (JO 7110.65BB 3-4 tables) + I (Q10 TBL 3-4-7, Q6 PAPI 20 %, flasher rule for non-visual arrivals)', runway: runway.tag || 'I',
    },
  };
  st.lighting = controllerFromEnv(st);
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
  L.push(st.wx.none ? `report — · NO WEATHER DATA (no report at or before t_env, no TAF in force): clear default drawn [I]` : `report ${st.wx.raw || '—'} · age ${f(st.wx.ageMin, 0)} min${st.wx.stale ? ' · STALE' : ''} [V]`);
  if (st.wx.forecast) L.push(`FORECAST TAF ${st.wx.forecast.issued} ${st.wx.forecast.applied.join('+')}: ${st.wx.forecast.text}${st.wx.forecast.groups.length ? ' (not rendered: ' + st.wx.forecast.groups.join(', ') + ')' : ''} [I]`);
  L.push(`σ surface ${st.atm.sigmaSurface.toExponential(2)} m⁻¹${st.atm.visLowerBound ? ` (${st.atm.visPrefix === 'P' ? 'P' : ''}${f(st.atm.visM / 1609.344, 0)}SM lower bound → clear air)` : ''} · ASOS ${st.atm.sigmaASOS != null ? st.atm.sigmaASOS.toExponential(2) : '—'} · E_T ${st.lightVis.ET.toExponential(2)} lx [M+I]`);
  { const sl = st.atm.slabs.map(s => `${s.kind} ${f(s.y0 - (st.atm.slabs[0] ? st.atm.slabs[0].y0 : 0), 0)}-${f(s.y1 - (st.atm.slabs[0] ? st.atm.slabs[0].y0 : 0), 0)} m σ ${s.sigma.toExponential(1)}`).join(' | ');
    const H = st.atm.horiz; const hz = H ? ` · structure${H.patch ? ' ' + H.patch.kind + ' patches ' + f(H.patch.cover, 2) + ' (σ ' + H.patch.sigma.toExponential(1) + ')' : ''}${H.lobes.length ? ' lobes ' + H.lobes.map(l => l.what).join(', ') : ''}` : '';
    const sw = st.atm.visSwing ? ` · VIS ${st.atm.visSwing.lo}V${st.atm.visSwing.hi} swing ${f(st.atm.visSwing.k, 2)}` : '';
    L.push(`slabs ${sl}${hz}${sw} [V+I]`); }
  L.push(`clouds ${st.clouds.map(c => `${c.cover}${String(c.baseFt / 100).padStart(3, '0')} own ${f(c.own, 2)}`).join(' ') || 'none'} · sun visible P ${f(st.sunVisibleP, 2)} [V+I]`);
  L.push(`wind ${st.wind.fromTrue == null ? (st.wind.calm ? 'calm' : 'VRB') : f(st.wind.fromTrue, 0) + '°T'} ${f(st.wind.speed / KT_MS, 0)} kt${st.wind.gust ? ' G' + f(st.wind.gust / KT_MS, 0) : ''} · sock ${f(st.wind.sockExt, 2)} [V+I]`);
  if (st.precip) L.push(`precip ${st.precip.kind} ${st.precip.intensity} ${f(st.precip.rateMmH, 2)} mm/h (${st.precip.rateBasis}) [V+I]`);
  L.push(`runway arr ${Object.keys(st.runway.arr).join(',') || '—'} dep ${st.runway.dep.join(',') || '—'} (${st.runway.source}) [${st.runway.tag || 'I'}]`);
  if (st.lighting) L.push(`lights ${controllerHud(st.lighting)} [V+I]`);
  return L;
}

// Short form for the HUD (one line): the HWD defaults
export const OPEN_QUESTION_SHORT = 'HWD Phase 2: no airfield-lighting controller (fixtures not sourced) · runway flow ADS-B, else METAR wind (west if calm) · KHWD routine minute 54 [verify] · no TAF';
export const OPEN_QUESTION_DEFAULTS = [
  'Airfield lighting (MIRL, VASI, PAPI, REIL): fixture positions not sourced - not drawn, no controller (Phase 4)',
  'Runway configuration: ADS-B flow, else the METAR wind: 28L/28R (west) unless the 28 tailwind is >= 5 kt dry (any when wet and not calm), then 10L/10R [inf]',
  'KHWD routine METAR at hh:54 [verify over 24 h]; no KHWD TAF (aviationweather.gov returns none)',
];
