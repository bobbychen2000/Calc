// Forked from sfo3d/js/env/aircraft_lights.js @ a967f9b. Kept: aircraft light states and sprites (14 CFR 25.1385-1401 intensities, Allard visibility, flash timing). Changed: DAY_GAIN is a local constant (= sfo3d js/env/lighting/airfield.js DAY_GAIN 30, I) instead of an import of the SFO fixture system. Not checked: whether 14 CFR Part 23 light values differ for GA aircraft (fork map 4.3, open). Dropped: nothing.
// Aircraft exterior lights (docs/research/environment_spec.md §6; step 2, gates A-NAV1 / A-FLASH1). Renderer-agnostic,
// no DOM: which lights are on in which flight phase, the position-light sectors and intensities, the anti-collision
// flashes, and the sprite records both renderers draw (js/aircraft/fleet.js lightSprites delegates here).
// Sources (cached, public domain, refs/cache/env/ecfr + refs/cache/env/aim, SOURCES.json):
//   14 CFR 25.1387 (dihedral angles L / R = 0–110° left / right of dead ahead, A = ±70° about dead aft),
//   25.1391 (minimum horizontal intensities: L and R (forward red and green) 40 cd 0–10°, 30 cd 10–20°, 5 cd 20–110°;
//   A (rear white) 20 cd 110–180°), 25.1393 (vertical factors 1.00 at 0°, 0.90 0–5°, 0.80 5–10°, 0.70 10–15°, 0.50
//   15–20°, 0.30 20–30°, 0.10 30–40°, 0.05 40–90°), 25.1395 (maximum intensities in overlaps: Area A 10–20° past the
//   common boundary plane 10 cd (5 cd for the aft overlaps), Area B > 20° 1 cd), 25.1397 (aviation red / green / white),
//   25.1401 (anticollision: 40–100 cycles/min; effective intensity 400 cd 0–5°, 240 5–10°, 80 10–20°, 40 20–30°,
//   20 30–75° above or below the horizontal plane; Blondel–Rey effective intensity, (e)) — eCFR point in time 2026-11-01;
//   14 CFR 91.209 (position lights sunset to sunrise when operating; parked: clearly illuminated, OR position lights, OR
//   an area marked by obstruction lights; anticollision lights whenever operating) — eCFR 2026-11-01;
//   AIM 4-3-24 "Use of Aircraft Lights" (FAA AIM HTML fetched 2026-11-05): rotating beacon "anytime their aircraft
//   engines are in operation"; "Prior to commencing taxi, it is recommended to turn on navigation, position,
//   anti-collision, and logo lights"; taxi light on "when the aircraft is moving or intending to move on the ground"
//   and off "when stopped or yielding"; "When entering the departure runway for takeoff or 'line up and wait,' all
//   lights, except for landing lights, should be illuminated"; landing lights "when takeoff clearance is received or
//   when commencing takeoff roll" and "when operating below 10,000 feet".
// Choices (I, shown in docs/research/environment_impl.md): intensities = 2 × the regulatory minima (spec §6 default);
// no spill outside a sector beyond a 2° anti-aliasing ramp (within the 25.1395 maxima: no limit is set within 10° of the
// boundary, 0 cd elsewhere); parked aircraft (display phase gate / parked, internal 'still'; not moving) have position lights OFF (owner Q11 default;
// 91.209(a)(2) "clearly illuminated" suffices at a floodlit stand); the beacon runs from pushback to parking (engines
// in operation); strobes from line-up until the runway is vacated (rollout) and in flight; landing lights on the take-off
// roll, in flight below 10,000 ft (3,048 m) and on the landing roll above 30 kt; taxi light only when moving under own
// power on the ground (≥ 1 kt, not during pushback); logo lights are not drawn (no anchors on the models, photometry NV);
// landing light 770,000 cd in 15° × 16° (Honeywell LED example for 737NG/757/767/777, spec §6, V for those types; NV for
// others); taxi light 50,000 cd (parameter, NV: not regulated).
import { clamp, flashGain, lampUnits, visibilityFactor, aureole } from './lighting/photometry.js';
export const DAY_GAIN = 30;   // = sfo3d js/env/lighting/airfield.js DAY_GAIN (I, its header); the SFO fixture module is not forked
import { renderSlabs, slabTau } from './atmo/sky_model.js';   // one σ field with the scene fog (review truth1-3)
export { lampUnits };

const DEG = Math.PI / 180;
export const NAV_H = [[10, 40], [20, 30], [110, 5]];                      // 25.1391 forward red / green (V)
export const NAV_REAR_CD = 20;                                            // 25.1391 rear white (V)
export const NAV_V = [[0, 1.0], [5, 0.9], [10, 0.8], [15, 0.7], [20, 0.5], [30, 0.3], [40, 0.1], [90, 0.05]];   // 25.1393 (V)
export const ACL_V = [[5, 400], [10, 240], [20, 80], [30, 40], [75, 20]];   // 25.1401(f) effective cd (V)
export const OVERLAP_MAX = { A: { fwd: 10, aft: 5 }, B: 1 };               // 25.1395 (V)
export const MINIMA_FACTOR = 2;                                           // spec §6: default = 2 × minima (I)
export const SPILL_RAMP_DEG = 2;                                          // anti-aliasing ramp past a sector boundary (I)
export const LANDING_CD = 770000, LANDING_BEAM = [15, 16];                // Honeywell LED example (spec §6; V for 737NG/757/767/777)
export const TAXI_CD = 50000;                                             // NV parameter (not regulated)
export const ALT_LANDING_M = 3048;                                        // 10,000 ft (AIM 4-3-24)
// Anti-collision flashing (25.1401(c): effective flash frequency 40–100 cycles/min): red beacons 60 cycles/min with a
// 0.15 s pulse (LED beacon pulse length NV, I); white wing-tip strobes: one double flash per cycle at 66 cycles/min
// (the app's existing rates, spec §6 "comply"), the two flashes 0.12 s apart (I), each a short (xenon / LED) flash.
export const BEACON = { fpm: 60, on: 0.15 }, STROBE = { fpm: 66, gap: 0.12, on: 0.002 };
// Aircraft light colours as linear sRGB, each an inferred point (I) INSIDE the 14 CFR 25.1397 box (eCFR text cached in
// refs/cache/env/ecfr/part25_1397.xml, V), gamut-clipped. They are not the airfield EB 67D boxes (review truth2-10: the
// former header said "= 25.1397 boxes", but 25.1397(a) aviation red needs z <= 0.002 while the EB 67D restricted-red
// centroid (0.685, 0.305) has z = 0.010, and 25.1397(c) white spans x 0.300-0.540 against EB 67D's 0.32-0.44):
//   red   (0.700, 0.299): y <= 0.335, z = 0.001 <= 0.002                             -> lin 1 / 0 / 0
//   green (0.180, 0.665): x <= 0.440 - 0.320 y, x <= y - 0.170, y >= 0.390 - 0.170 x -> lin 0 / 1 / 0.035
//   white (0.313, 0.329): 0.300 <= x <= 0.540, y within x - 0.040 .. x + 0.020        -> lin 1 / 0.996 / 0.996
//     (strobes and the tail light: xenon / LED sources near 6,500 K, I; the warm EB 67D airfield-white centroid
//      1 / 0.614 / 0.411 used before is a 2,800 K-like incandescent white)
export const AV_RED = [1, 0, 0], AV_GREEN = [0, 1, 0.0354], AV_WHITE = [1, 0.9959, 0.9959];

const tbl = (T, x) => { for (const [lim, v] of T) if (x <= lim) return v; return 0; };
/** 25.1393 vertical factor at |el| deg (0° -> 1.00; (0, 5] -> 0.90; ...; > 90 -> 0). */
export const navVertical = (elDeg) => { const a = Math.abs(elDeg); return a === 0 ? 1.0 : a <= 90 ? tbl(NAV_V.slice(1), a) : 0; };
/** 25.1401(f) minimum effective anticollision intensity at |el| (0 beyond 75°). */
export const aclMinimum = (elDeg) => tbl(ACL_V, Math.abs(elDeg));
const ramp = (past) => clamp(1 - past / SPILL_RAMP_DEG, 0, 1);
/** Position-light intensity (cd) of colour 'red' | 'green' | 'white' seen at azimuth az (deg from dead ahead, positive to
 *  the RIGHT, −180..180) and elevation el (deg from the aircraft's horizontal plane), at MINIMA_FACTOR × the minima. */
export function navIntensity(colour, az, el) {
  const a = ((az % 360) + 540) % 360 - 180;            // −180..180
  let h = 0;
  if (colour === 'red' || colour === 'green') {
    const s = colour === 'red' ? -a : a;                // angle into the light's own side (L for red, R for green)
    const ab = Math.abs(a);
    if (s >= 0 && ab <= 110) h = tbl(NAV_H, ab);
    else if (s >= 0) h = NAV_H[2][1] * ramp(ab - 110);  // past the aft boundary (110°)
    else h = NAV_H[0][1] * ramp(-s);                    // past the forward boundary (dead ahead) into the other side
  } else {
    const ab = Math.abs(a);
    h = ab >= 110 ? NAV_REAR_CD : NAV_REAR_CD * ramp(110 - ab);
  }
  return MINIMA_FACTOR * h * navVertical(el);
}
/** Which dihedral angle (25.1387) a direction lies in: 'L' (left, 0–110°), 'R' (right), 'A' (aft, beyond 110°). */
export const dihedral = (az) => { const a = ((az % 360) + 540) % 360 - 180; return Math.abs(a) > 110 ? 'A' : a < 0 ? 'L' : 'R'; };

/** The traffic phase as the light logic needs it. js/live/app.js passes the DISPLAY phase (js/live/traffic.js
 *  displayPhase, the label at the display time: tr.phase), whose names differ from the classifier's internal ones
 *  (tr.m.phase): 'still' is shown as gate / parked / holding / pushed / pushback, 'rollout' as 'landing' (or 'taxi' once
 *  the body is > 40 m off the centreline), 'flare' as 'final', 'climb' as 'departure', 'new' as holding / parked /
 *  enroute (review finding truth1-1: the logic checked internal names only, so every parked aircraft at a gate counted as
 *  operating). Both vocabularies map to: 'parked' (engines off), 'stopped' (stationary with engines running: pushed,
 *  holding short, queueing), 'pushback', 'taxi', 'lineup', 'takeoff', 'air' (climb, enroute, approach, final, flare,
 *  go-around), 'rollout' (landing roll), 'vehicle'. */
export function lightPhase(phase, ground) {
  switch (phase) {
    case 'gate': case 'parked': case 'still': return 'parked';
    case 'pushed': case 'holding': return 'stopped';
    case 'new': return ground ? 'stopped' : 'air';
    case 'landing': case 'rollout': return 'rollout';
    case 'flare': case 'final': return ground ? 'rollout' : 'air';
    case 'departure': case 'climb': case 'enroute': case 'approach': case 'goaround': return ground ? 'taxi' : 'air';
    case 'pushback': case 'taxi': case 'lineup': case 'takeoff': case 'vehicle': return phase;
    default: return ground ? 'stopped' : 'air';       // ground-other ('other'), unknown labels
  }
}
/** Light states from the traffic phase (AIM 4-3-24, 91.209; choices above). in: {phase (display or internal name, see
 *  lightPhase), ground, gs (kt), altAgl (m), stale}. A parked aircraft that moves (towed, or a silent docking still
 *  driving in) counts as operating. */
export function aircraftLightStates({ phase, ground, gs = 0, altAgl = 0, stale = false }) {
  const moving = !ground || gs > 0.5;
  const ph = lightPhase(phase, ground);
  const parked = stale || ((ph === 'parked' || ph === 'vehicle') && !moving);
  const operating = !parked && ph !== 'vehicle';      // engines in operation: pushback .. parked
  const air = !ground;
  const onRunwayPhase = ph === 'lineup' || ph === 'takeoff' || ph === 'rollout';
  return {
    nav: operating,                                      // AIM: before taxi; 91.209(a)(1) at night; parked: off (Q11, I)
    beacon: operating,                                   // AIM 4-3-24 / 91.209(b)
    strobe: !stale && operating && (air || onRunwayPhase),   // line-up until the runway is vacated (rollout ends off the CL)
    landing: !stale && operating && ((air && altAgl < ALT_LANDING_M) || ph === 'takeoff' || (ph === 'rollout' && gs > 30)),
    taxi: !stale && operating && ground && gs >= 1 && ph !== 'pushback' && ph !== 'takeoff' && !(ph === 'rollout' && gs > 30),
  };
}

// ------------------------------------------------------------------------------------------------ sprites
// Sprite intensity units: js/env/lighting/photometry.js lampUnits (cd -> lamp units at the night calibration).
let viewer = null, pxAngle = 0;
/** The camera position for the direction-dependent intensities (set once per frame by js/live/app.js); px = the angle
 *  of one screen pixel at distance 1 (2 tan(fov / 2) / height px; 0 = unknown: no lens footprint, see NAV_LENS_S). */
export function setLightViewer(p, px = 0) { viewer = p; pxAngle = px > 0 ? px : 0; }
export const lightViewer = () => viewer;
let frameT = { prev: null, t: null };
// Viewing conditions (spec §4.10, as for the airfield lights): the renderer's slabs (renderSlabs + slabTau), E_T and the day display
// gain (js/env/lighting/airfield.js DAY_GAIN, I); null = no attenuation (tests).
let viewEnv = null;
/** Set from the EnvState once per environment update (js/live/app.js applyEnv): {slabs, ET, gain}. */
export function setLightEnv(env, dayGain) {
  if (!env) { viewEnv = null; return; }
  const w = env.photocell ? env.photocell.asosNightW : 1;
  const slabs = env.atm ? renderSlabs(env) : null;
  const g = Math.pow(dayGain ?? 1, 1 - w), G = Math.pow(DAY_GAIN, 1 - w);
  viewEnv = { slabs, ET: env.lightVis ? env.lightVis.ET : 6.99e-7, gain: g, w, G, rf: G > 0 ? g / G : 1, fogAur: !!(slabs && slabs[0] && slabs[0].sigma > 1e-4) };   // aureoles only in mist / fog (airfield.js)
}
// Position-light lens by day (close-out round 3, env-6; engine verify finding engine-v3 residual). The sprite size s of a
// record is the footprint the light is drawn over: 0.22 m for the position lights is their night look (lens + glare). By
// day there is no visible glare: a lit lens is a small coloured dot of its own luminance (a 40-80 cd lens of ~20-30 cm²
// is 13-40 kcd/m², 0.5-2 x sunlit white paint ~17 kcd/m²), while the same energy over the 0.22-m night footprint peaked
// at ~9 % of white paint and vanished, and the display gain G (DAY_GAIN, airfield.js header: what a 2.2-px sprite needs to
// reach the eye's daylight threshold on a display) made a near light a 30 x glare disk. Now the footprint blends with the
// ASOS night weight w from the lens (NAV_LENS_S: the Gaussian core's area π (0.341 s)² = 23 cm², I) by day to the
// record's s at night (energy kept: lampUnits divides by s²), and the display gain is the one that restores the LENS
// LUMINANCE when the lens is smaller than the sprites' 2.2-px floor, (2.2 / lens px)², at most G and at least 1: a
// resolved lens (near) is drawn at its physical luminance, a sub-pixel one (far) gets the airfield lights' gain G as
// before, and at night (w = 1, G = 1) nothing changes. rf: the old renderer's lamp-unit scale (its dayGain / DAY_GAIN).
export const NAV_LENS_S = 0.08, SPRITE_MIN_PX = 2.2;
/** Drawn size and display gain of a position light of record size s0 at distance d (m), ASOS night weight w, day display
 *  gain G; px = angle of one pixel at distance 1 (setLightViewer). Without px: the record as it was (s0, G). */
export function lensGain(s0, d, w, G, px = pxAngle) {
  if (!(px > 0) || !(d > 0)) return { s: s0, g: G, pxL: null };
  const pxL = NAV_LENS_S / (d * px);
  const W = clamp(w ?? 1, 0, 1);
  return { s: NAV_LENS_S + (s0 - NAV_LENS_S) * W, pxL, g: Math.min(G, Math.max(1, (SPRITE_MIN_PX / pxL) ** 2)) };
}
/** Frame clock for the flash scheduler (seconds; set once per frame by js/live/app.js). */
export function setLightFrame(t) { if (frameT.t !== t) { frameT.prev = frameT.t; frameT.t = t; } }

function angles(p, fwd, right, up) {
  if (!viewer) return { az: 0, el: 0 };
  const v = [viewer[0] - p[0], viewer[1] - p[1], viewer[2] - p[2]]; const d = Math.hypot(v[0], v[1], v[2]) || 1;
  const f = v[0] * fwd[0] + v[1] * fwd[1] + v[2] * fwd[2], r = v[0] * right[0] + v[1] * right[1] + v[2] * right[2], u = v[0] * up[0] + v[1] * up[1] + v[2] * up[2];
  return { az: Math.atan2(r, f) / DEG, el: Math.asin(clamp(u / d, -1, 1)) / DEG };
}
/** Sprite records for one aircraft. L = world light anchors {navL, navR, tail, beaconTop, beaconBot, strobeL, strobeR,
 *  landL, landR, taxi}, axes = {fwd, right, up} world unit vectors, on = light states, seed = per-aircraft phase offset (s),
 *  t = time (s). All records carry phys: true (physical intensity day and night: js/three/renderer3.js draws them at
 *  the night calibration; js/three/lights.js `fixed`). */
export function aircraftSprites(L, axes, on, seed, t, gearDown = 1) {
  const S = []; const tPrev = frameT.t === t && frameT.prev != null ? frameT.prev : t - 1 / 60;
  const { fwd, right, up } = axes;
  const put = (p, c, cd, s, extra) => {
    if (!p || !(cd > 0)) return;
    let k = 1, aur = 0, aurR = 0, sD = s, lens = false;
    if (viewEnv && viewer) {                     // Allard visibility through the EnvState slabs (spec §4.10)
      const d = Math.hypot(viewer[0] - p[0], viewer[1] - p[1], viewer[2] - p[2]) || 1;
      const T = viewEnv.slabs ? Math.exp(-slabTau(viewEnv.slabs, viewer, p)) : Math.exp(-3.3e-5 * d); const v = visibilityFactor(cd * T / (d * d), viewEnv.ET);
      // fog aureole (photometry.js aureole; review look1-1), also when the core is below threshold
      const A = viewEnv.fogAur ? aureole(T) : null; if (A && cd * A.f / (d * d) >= viewEnv.ET) { aur = lampUnits(cd * A.f * viewEnv.gain, s); aurR = A.theta; }
      if (!(v > 0) && !aur) return; k = T * v * viewEnv.gain;
      // position lights: the lens footprint and lens-luminance gain by day (NAV_LENS_S header; env-6)
      if (extra && extra.nav && pxAngle > 0) { const L = lensGain(s, d, viewEnv.w, viewEnv.G); sD = L.s; k = T * v * L.g * viewEnv.rf; lens = sD < s - 1e-3; }
    }
    S.push({ p, c, i: lampUnits(cd * k, sD), s: sD, phys: true, aur, aurR, lens, ...extra });
  };
  if (on.nav) {
    for (const [p, c, name] of [[L.navL, AV_RED, 'red'], [L.navR, AV_GREEN, 'green'], [L.tail, AV_WHITE, 'white']]) {
      if (!p) continue; const a = angles(p, fwd, right, up); put(p, c, navIntensity(name, a.az, a.el), 0.22, { nav: name });
    }
  }
  if (on.beacon) {
    const g = flashGain(tPrev, t, 60 / BEACON.fpm, seed % (60 / BEACON.fpm), BEACON.on);
    if (g > 0) for (const p of [L.beaconTop, L.beaconBot]) { if (!p) continue; const a = angles(p, fwd, right, up); put(p, AV_RED, MINIMA_FACTOR * aclMinimum(a.el) * g, 0.25, { flash: 'beacon' }); }
  }
  if (on.strobe) {
    const P = 60 / STROBE.fpm, ph = (seed * 0.37) % P;
    const g = Math.max(flashGain(tPrev, t, P, ph, STROBE.on), flashGain(tPrev, t, P, ph + STROBE.gap, STROBE.on));
    if (g > 0) for (const p of [L.strobeL, L.strobeR]) { if (!p) continue; const a = angles(p, fwd, right, up); put(p, AV_WHITE, MINIMA_FACTOR * aclMinimum(a.el) * g, 0.3, { flash: 'strobe' }); }
  }
  const beamCd = (p, dir, cd, hw, vw) => {
    if (!viewer) return cd;
    const v = [viewer[0] - p[0], viewer[1] - p[1], viewer[2] - p[2]]; const d = Math.hypot(v[0], v[1], v[2]) || 1;
    const c = (v[0] * dir[0] + v[1] * dir[1] + v[2] * dir[2]) / d; const off = Math.acos(clamp(c, -1, 1)) / DEG;
    const half = (hw + vw) / 4;                                           // mean half-angle of the beam (I: circular)
    return off <= half ? cd : off <= 3 * half ? cd * Math.pow(10, -2 * (off - half) / (2 * half)) : 0;   // −20 dB at 3× (I)
  };
  if (on.landing && axes.landDir) for (const p of [L.landL, L.landR]) put(p, [1, 0.95, 0.85], beamCd(p, axes.landDir, LANDING_CD, LANDING_BEAM[0], LANDING_BEAM[1]), 0.35, { beam: 'landing' });
  if (on.taxi && gearDown > 0.5 && axes.taxiDir && L.taxi) put(L.taxi, [1, 0.96, 0.9], beamCd(L.taxi, axes.taxiDir, TAXI_CD, 20, 20), 0.3, { beam: 'taxi' });
  return S;
}
