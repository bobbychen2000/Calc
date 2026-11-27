// sha3d Phase 3 (P3-B): aircraft performance table for the kinematic simulator (new). Pure ES module (node + browser).
// Every value is an INTEGER in cm, cm/s, cm/s^2 or ms (design §1.4) and carries src / basis. Aircraft-type priors only:
// no airfield value (airfield rules come from the AIP (mirror) facts in the data, the route table and js/sim/router.js).
//
// Sources of the priors:
// - geometry (span, length, nose-gear and main-gear stations, track): js/aircraft/types.js SPEC (manufacturers' airport
//   planning documents, see that file's header); C919 / C909 (AJ27) dimensions: COMAC published figures quoted in
//   docs/phase3/design.md §2.3 / sha_stands.json class_ref.B [sec], drawn with an A320 / CRJ900 stand-in model;
// - liftoff speeds: sfo3d@e3218d6 js/live/traffic.js LIFTOFF_KT (:154; observed at SFO, a sea-level field like ZSSS),
//   else 150 / 165 kt by length (design §4.4) and 125 kt below 30 m (sfo3d attitude rule :3138);
// - accelerations: design §4.4 [inf] (take-off 2.0 narrow / 1.7 wide m/s^2, landing deceleration 2.0 / 1.7 m/s^2, taxi
//   +1.0 / -1.5 m/s^2; all under sfo3d ctlGround's caps 3.3 (rolls) and 1.8 / 2.0 (taxi), traffic.js:2795);
// - approach speeds: typical Vref + 5 kt from memory (unverified) [inf], 125-160 kt;
// - wake categories: ICAO Doc 4444 (H >= 136 t MTOW, L <= 7 t, J = A380) from memory (unverified) [inf];
// - minimum turning radius of the main-gear centre 0.27 x wheelbase (sfo3d traffic.js:2782, ~75 deg nose-wheel steering) and
//   the fillet floor 1.6 x that (traffic.js:457 Rlo).

import { TYPES, ICAO_TYPES } from '../aircraft/types.js';

const KT = 51.4444;   // cm/s per knot
export const kt2cms = (kt) => Math.round(kt * KT);

export const PERF = {
  aToCms2: { narrow: 200, wide: 170 },          // design §4.4 [inf]; 'wide' = wide-body (wake H / J), not the span class
  aDecCms2: { narrow: 200, wide: 170 },         // landing braking (design §4.2) [inf]; by body (wake H / J)
  taxiMaxCms: { narrow: 1200, wide: 1000 },     // taxiways A / B / C / D (design §4.4) [inf]
  taxiAccCms2: 100, taxiDecCms2: 150,           // design §4.4 [inf]
  pushCms: 120, pushAccCms2: 30,                // design §4.3 [inf]
  startupMs: 90000,                             // engine start at the push end (design §4.3) [inf]
  vExitCms: 2500,                               // turn-off speed at the rapid-exit node: 25 m/s, the design's rapid-exit entry bound (§4.4; §4.2 said 20 m/s, see movement.md §5) [inf]
  rapidMaxCms: 2500,                            // rapid-exit entry <= 25 m/s (design §4.4; ICAO RET design speed from memory) [inf]
  climbAccCms2: 60, vClimbCms: kt2cms(250),     // after liftoff: +0.6 m/s^2 to 250 kt [inf]
  steerFactor: 0.27, filletFactor: 1.6,         // R_min = 0.27 wheelbase (sfo3d traffic.js:2782); fillets >= 1.6 R_min (:457)
  wideSpanCm: 3600,                             // span >= 36 m (code D-F) counts as "wide" for radii, taxi speed, rolls [inf]
  src: 'inf',
  basis: 'design.md §4.2-4.4; sfo3d@e3218d6 js/live/traffic.js priors (LIFTOFF_KT :154, ctlGround caps :2795, R_min :2782)',
};

// sfo3d LIFTOFF_KT (traffic.js:154, observed at SFO 24 Sep 2025 recording) [obs elsewhere -> inf here]
const LIFTOFF_KT = { A21N: 157, A321: 165, A320: 150, A319: 145, B39M: 172, B38M: 172, B738: 162, B739: 173, A359: 172, B77W: 175,
  B772: 157, B789: 174, E75L: 140, E75S: 140 };
// approach speed (kt) by ICAO type: typical Vref + 5 kt from memory (unverified) [inf]
const VAPP_KT = { A319: 130, A19N: 130, A320: 135, A20N: 135, A321: 140, A21N: 140, B736: 130, B737: 130, B738: 140, B38M: 140,
  B739: 145, B39M: 145, B37M: 135, B3XM: 145, B752: 135, B753: 140, B762: 135, B763: 140, B764: 145, A332: 135, A333: 140, A338: 135,
  A339: 140, A359: 140, A35K: 145, B772: 140, B77L: 145, B773: 145, B77W: 150, B779: 150, B788: 140, B789: 145, B78X: 150, B744: 155,
  B74F: 155, B748: 160, A388: 140, MD11: 155, E170: 125, E75L: 125, E75S: 125, E190: 130, E195: 130, BCS1: 125, BCS3: 130,
  CRJ2: 135, CRJ7: 130, CRJ9: 135, C919: 140, AJ27: 135 };
const HEAVY = new Set(['B762', 'B763', 'B764', 'A332', 'A333', 'A338', 'A339', 'A359', 'A35K', 'B772', 'B77L', 'B773', 'B77W', 'B779',
  'B788', 'B789', 'B78X', 'B744', 'B74F', 'B748', 'MD11']);
// types without a TYPES entry: published dimensions + the stand-in geometry key [sec / inf]
const EXTRA = {
  C919: { key: 'a320', spanM: 35.8, lenM: 38.9, src: 'COMAC C919 span 35.8 m, length 38.9 m [sec]; geometry of the A320 stand-in (design §2.3)' },
  AJ27: { key: 'crj9', spanM: 27.3, lenM: 33.5, src: 'C909 / ARJ21: sha_stands.json class_ref.B (span 27.3 m, length 33.5 m) [sec]; geometry of the CRJ900 stand-in' },
};
// business jets (business apron; the plan draws generic ones): one generic entry [inf]
const BIZ = { key: 'crj2', spanM: 28.0, lenM: 30.0, src: 'generic business jet (Gulfstream / Global class), dimensions inferred [inf]' };
const BIZ_TYPES = new Set(['GLF4', 'GLF5', 'GLF6', 'GL5T', 'GL7T', 'GLEX', 'GLXS', 'CL60', 'CL35', 'C680', 'C68A', 'C700', 'C750', 'F2TH', 'FA7X', 'FA8X', 'E55P', 'E35L', 'BIZ']);

const cache = new Map();
/**
 * Performance of an ICAO type. All integers (cm, cm/s, cm/s^2, ms).
 * @returns {{icao, typeKey, wake, wide, vappCms, vlofCms, aToCms2, aDecCms2, taxiMaxCms, spanCm, lenCm, wheelbaseCm,
 *   noseGearCm, mainGearCm, trackCm, rMinCm, rFilletMinCm, src, basis}}
 */
export function perfOf(icao) {
  const id = String(icao || '').toUpperCase();
  if (cache.has(id)) return cache.get(id);
  let key = ICAO_TYPES[id] || null, spanM = null, lenM = null, srcDim = 'js/aircraft/types.js SPEC (manufacturer airport-planning documents)';
  if (!key && EXTRA[id]) { key = EXTRA[id].key; spanM = EXTRA[id].spanM; lenM = EXTRA[id].lenM; srcDim = EXTRA[id].src; }
  if (!key && BIZ_TYPES.has(id)) { key = BIZ.key; spanM = BIZ.spanM; lenM = BIZ.lenM; srcDim = BIZ.src; }
  let unknown = false;
  if (!key) { key = 'a320'; unknown = true; srcDim = 'unknown type ' + id + ': A320 values [inf]'; }
  const T = TYPES[key];
  const span = spanM ?? T.wing.span, L = lenM ?? T.L;
  const scale = lenM ? lenM / T.L : 1;                         // stand-in geometry scaled to the real length
  const xNose = T.xNose * scale, xMain = T.xMain * scale, track = T.track * scale;
  const spanCm = Math.round(span * 100), wide = spanCm >= PERF.wideSpanCm;   // code D-F: fillet radii, taxi speed
  const wake = id === 'A388' ? 'J' : HEAVY.has(id) ? 'H' : 'M'; const body = wake === 'H' || wake === 'J' ? 'wide' : 'narrow';   // rolls
  const lenCm = Math.round(L * 100);
  const wheelbaseCm = Math.round((xMain - xNose) * 100);
  const vlofKt = LIFTOFF_KT[id] ?? (BIZ_TYPES.has(id) || L < 30 ? 125 : L <= 42 ? 150 : 165);
  const vappKt = VAPP_KT[id] ?? (BIZ_TYPES.has(id) ? 125 : HEAVY.has(id) ? 145 : 140);
  const rMinCm = Math.round(PERF.steerFactor * wheelbaseCm);
  // pilot eye above the main-gear wheels on the approach: door-1 sill + 0.9 m (seated eye above the cockpit floor) on the
  // ground, plus the main gear -> cockpit distance x sin 2.5 deg of approach pitch [inf]. The PAPI (3 deg) path is the EYE
  // path; the wheels fly this much lower (traj.js touchdownSCm)
  const sill = (typeof T.sill === 'number' ? T.sill : 3.0) * scale;
  const eyeToWheelCm = Math.round((sill + 0.9 + (xMain - 2.5 * scale) * 0.0436) * 100);
  const p = {
    icao: id, typeKey: key, unknown, wake, wide, body,
    vappCms: kt2cms(vappKt), vlofCms: kt2cms(vlofKt),
    aToCms2: PERF.aToCms2[body], aDecCms2: PERF.aDecCms2[body],
    taxiMaxCms: wide ? PERF.taxiMaxCms.wide : PERF.taxiMaxCms.narrow, taxiAccCms2: PERF.taxiAccCms2, taxiDecCms2: PERF.taxiDecCms2,
    spanCm, lenCm, wheelbaseCm, noseGearCm: Math.round(xNose * 100), mainGearCm: Math.round(xMain * 100), trackCm: Math.round(track * 100),
    rMinCm, rFilletMinCm: Math.round(PERF.filletFactor * rMinCm), eyeToWheelCm,
    src: 'inf',
    basis: { dims: srcDim, vlof: LIFTOFF_KT[id] ? 'sfo3d traffic.js LIFTOFF_KT (observed at SFO)' : 'by length (design §4.4)', vapp: VAPP_KT[id] ? 'Vref + 5 kt from memory (unverified)' : 'class default', wake: 'ICAO Doc 4444 from memory (unverified)', rolls: 'design §4.4' },
  };
  Object.freeze(p); cache.set(id, p); return p;
}
/** wake-category pair separations on final (NM) and between departures (s), ICAO Doc 4444 from memory (unverified) [inf] */
export const WAKE = {
  arrNM: { 'J>H': 6, 'J>M': 7, 'J>L': 8, 'H>H': 4, 'H>M': 5, 'H>L': 6, 'M>L': 5 },   // radar minima; others: the 5 km AIP minimum (AD 2.22 4.1)
  depS: { 'J>*': 180, 'H>M': 120, 'H>L': 120, 'M>L': 120, default: 60 },
  src: 'inf', basis: 'ICAO Doc 4444 from memory (unverified); design §4.6',
};
export const NM_CM = 185200;
