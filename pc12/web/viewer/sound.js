// Engine and propeller sound (owner 2026-10-03: "can you add sound effect too when propellor starts rolling").
//
// Pure Web Audio synthesis from built-in nodes (oscillators, looped noise buffers, biquads, gains, convolvers, a
// compressor; no files, no AudioWorklet module: the claude.ai Artifact's CSP), driven every frame by the state the
// viewer animates -- the propeller spool and the gas generator of kinematics.js (GasGenerator: Ng, light-off, starter,
// igniters) -- so a start, a power change or a shutdown sounds exactly as long as it looks.  The same graph
// (EngineVoice) and the same state -> parameter law (engineParams) render offline for the tests (renderOffline:
// test/viewer_test.py writes the WAV and its spectrogram and measures it).
//
// Sound design: a PT6E-67XP free-turbine turboprop with the Hartzell 5-blade composite propeller (2.67 m).  Sources
// and assumptions (levels and timings are viewer estimates for a plausible sound, not measurements):
//  - propeller (the dominant source): the blade-passing tone at 5 x rpm / 60 Hz (83 Hz at the ~1,000 rpm ground idle,
//    142 Hz at 1,700 rpm) with its harmonics -- the classic result of propeller-noise theory (Gutin; Hubbard ed.,
//    "Aeroacoustics of Flight Vehicles", NASA RP-1258, 1991: loading and thickness noise at the blade-passage harmonics,
//    the higher harmonics growing steeply with the tip Mach number).  Tip Mach 0.41 at 1,000 rpm, 0.70 at 1,700 static:
//    harmonics ~ n^-0.7 low-passed at a harmonic count that grows with Mt^2, level ~ (rpm / 1,700)^2 x the blade
//    loading (kinematics.js bladeLoad: the feathered blades edge-on to the flow are much quieter; reverse loads them
//    most).  Two paths on one frequency driver: harmonics 1-3 in phase (the blade-passage pulse) and 4+ with scattered
//    (Schroeder) phases, the latter amplitude-modulated by band-limited 3-15 Hz noise -- a static propeller ingests
//    ground-vortex turbulence, and the unsteady loading lifts mainly the higher harmonics (the ragged, gusty buzz).  The
//    whole propeller sound also carries a 1/rev wobble (blade-to-blade differences) and slow gusts (~+-2 dB).  The
//    broadband blade 'swish' is chopped at the blade passage; beta / reverse adds the low roar and a broad 0.6-1.5 kHz
//    rasp of the reversed, partly stalled blades and the air they recirculate, and lifts the harmonics.
//  - gas generator: the compressor scream at blade-passing orders of Ng (100 % = 37,468 rpm = 624 Hz, the PT6A-60 /
//    -67 series' figure, assumed for the -67XP; the blade counts are not public: the main tone is taken at 16 x the
//    shaft frequency -- ~6 kHz at the ~60 % ground idle, ~9-10 kHz near 100 % -- with its 2nd harmonic and two more
//    stage orders, 21 and 27, a few dB down), each tone with its own slow pitch drift, a narrowband 'haystack' of noise
//    around the main tone (turbulence scattering) and a 25-90 Hz roughness: a breathy, slightly beating chord rather
//    than a pure line; a faint 1 x Ng shaft tone and a broadband inlet hiss ~ Ng^2.5.  During the start: the electric
//    starter-generator's whine (a sine pair + a gear-mesh partial, low-passed, and its brush whirr sweeping up through
//    the mid band: the start is heard from its first ~0.3 s, on small speakers too) and the igniters' snaps (~2.5 a
//    second) until the starter cuts out at 50 % Ng (PT6 start practice).  The propeller stays still until light-off (the
//    free power turbine turns only once hot gas flows: kinematics.js); as it starts rolling its blades' chopped
//    'whoosh' is heard (the swish held up below ground idle while the engine burns).
//  - combustion / exhaust: broadband roar once lit (low-passed noise, brighter and louder with power); the light-off a
//    one-shot 'whump' (SHOTS.light: a falling thump, a broadband poof, the combustor's hollow resonances and a rumble,
//    sample-accurate when GasGenerator.lightN counts up; ~+9 LU over the crank) and a surge of the roar.
//  - crest factor (how loud it plays under the same peaks): the broadband bands' rare 4-5 sigma peaks are rounded
//    above 2.5 sigma (TAME), the gust / turbulence modulators cap their swells (MOD.lim) and the chop of the swish
//    trails the tonal pulse by an eighth of a blade passage (CHOP): the 3/4 view's peak-to-loudness ~10-11 dB (14-22)
//  - listener = the camera: distance to the propeller hub -> level ~ (D0 / d)^0.8 (a compressed spherical spreading,
//    capped at ~5.6 m and at the loudness ceiling: SOUND.ceil) and
//    a gentle low-pass (air absorption); the propeller tone loudest in its plane of rotation, the inlet whine ahead (the
//    chin inlet), the exhaust beside / behind (the stacks).  Inside the cabin (the interior tour or a camera inside the
//    closed cabin): low-passed (~0.9 kHz on the flight deck, ~0.5 kHz in the aft cabin) with the propeller's low drone
//    kept (structure-borne, a +6 dB bump near the blade-passing frequency) and the whine ~18 dB down above 1.8 kHz
//    (through the firewall and the windshield), quieter aft; an open door lets more in.  Stereo: panned toward the hub's
//    side of the screen, plus a synthesised room: outside the apron's early reflections and a ~0.4 s tail, inside a
//    boxy ~80 ms cabin (ConvolverNode, independent noise per channel), ~-12 dB.
//  - output (review r2 SR2-01: the default listening level): DC block, master gain (SOUND.level x volume^2 x mute: the
//    3/4 view at BS.1770 ~-25 LUFS short-term at ground idle, ~-15 at 1,700 rpm, ~-12 in reverse, the crank ~-32 and the
//    light-off ~-22 momentary), a safety limiter above every peak of the 3/4 view (LIMITER: it works only at the
//    loudness ceiling close to the disc, by a fraction of a dB on average) and the output curve (OUT_CURVE: linear to
//    0.7, a tanh shoulder to 0.95; < 0.01 % of the 3/4 view's samples reach it).
// Browsers start audio only after a user gesture: the AudioContext is created by the gesture that starts the engine
// (or, sticky activation, on a later start while sound is on), suspended while the engine is off, the page hidden or
// the sound muted.
import * as THREE from 'three';
import { PROP_RPM, NG, bladeLoad, ngRun } from './kinematics.js';

const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const BLADES = 5, DIAM = 2.67, C_SOUND = 340;
const F_NG100 = NG.rpm100 / 60;           // Hz, the gas generator's shaft frequency at 100 % Ng
const WHINE = [16, 32, 21, 27];           // compressor tones: blade-passing orders of the shaft frequency (assumed):
                                          // the main stage, its 2nd harmonic, two more stages
const STARTER = [2.6, 5.2, 11.3];         // starter-generator whine: its order, 2nd harmonic, AGB gear mesh (assumed)
const STARTER_BRUSH = 23.4;               // its brush / commutator whirr (9 segments x 2.6, assumed)
const R_IDLE = PROP_RPM.idle / PROP_RPM.max;
const CHOP = 0.125;                       // the broadband chop's delay after the tonal pulse (blade passages; measured:
                                          // the mix's 99.99th-percentile peak 1.2 dB under the coincident 0.5)
const PROP_N = 40, PROP_LO = 3;           // propeller harmonics: 1 .. PROP_LO in phase, PROP_LO + 1 .. PROP_N scattered
const SQRT2 = Math.SQRT2;

export const LIMITER = { pre: 0.41, threshold: -6, knee: 3, ratio: 20, attack: 0.001, release: 0.15, makeup: Math.pow(10, 2.91 / 20) };
export const OUT_CURVE = { knee: 0.7, ceil: 0.95 };
export const SOUND = {
  volume: 1.0,                            // default volume (master gain = level x volume^2): the slider attenuates
  level: 0.595,                           // master scale (the default listening level): the 3/4 view at ~-12 LUFS short-term
                                          // in reverse at 1,700 rpm (its rare peaks rounded by ~1 dB, OUT_CURVE), ~-15.5 at
                                          // 1,700 rpm, ~-25 at ground idle
  D0: 22,                                 // m: the 3/4 view's camera distance to the hub (960 x 600) -> listener gain 1
  distExp: 0.8,                           // the distance law (D0 / d)^distExp: a game-audio roll-off, gentler than 1 / d
  gainMax: 3.0,                           // its cap (+9.5 dB, reached at ~5.6 m)
  ceil: 1.2,                              // the loudness ceiling: closer than D0 the listener gain stops where the mix would
                                          // be ceil x (+1.6 dB) the 3/4 view's reverse at 1,700 rpm (the loudest state there):
                                          // a close-up at idle is ~+9 dB louder, one in reverse only ~+1.6 (a mixer's ride,
                                          // instead of the limiter / the output curve working)
  panOut: 0.25,                           // outside / inside: pan = this x the hub's screen side (-1 .. 1): ~3 dB between
  panIn: 0.25,                            // the channels with the hub at the edge of the view (~25 deg off-axis); level
                                          // only (an interaural delay combed the mono sum of phone speakers)
  tau: 0.05,                              // s, source parameter smoothing (setTargetAtTime): no zipper noise
  tauL: 0.12,                             // s, listener (distance, cabin) smoothing
  tauM: 0.04,                             // s, master (mute)
  inside: { staFwd: 4.2, staAft: 9.0, lpFwd: 900, lpAft: 480, gainFwd: 0.55, gainAft: 0.28, body: 6, hi: 0.13 },
  storeKey: 'pc12.viewer.sound', volKey: 'pc12.viewer.soundVolume',
};

// ------------------------------------------------------------------ state -> parameters (pure)
// listener geometry g: {d: m camera - hub, cos: of the angle between hub -> camera and the forward thrust axis,
// side: -1 .. 1 (hub left .. right of the view), inside: bool, sta: the camera's station (m), door: 0 .. 1}
export function listenerParams(g) {
  const I = SOUND.inside, inside = !!g.inside, door = clamp(+g.door || 0, 0, 1), c = clamp(+g.cos || 0, -1, 1);
  const f = clamp((g.sta - I.staFwd) / (I.staAft - I.staFwd), 0, 1);
  return {
    gain: inside ? Math.min(1, (I.gainFwd + (I.gainAft - I.gainFwd) * f) * (1 + door))
      : Math.min(SOUND.gainMax, Math.pow(SOUND.D0 / Math.max(+g.d || 0, 1), SOUND.distExp)),
    lpDist: inside ? 20000 : clamp(20000 * Math.pow(10 / Math.max(g.d, 10), 0.45), 3500, 20000),
    lpIn: inside ? Math.min(20000, (I.lpFwd + (I.lpAft - I.lpFwd) * f) * (1 + 3 * door)) : 20000,
    hiIn: inside ? I.hi * (1 - 0.4 * f) * (1 + 2 * door) : 0,       // the whine through the firewall / windshield
    body: inside ? I.body * (1 - 0.5 * door) : 0,
    pan: clamp(+g.side || 0, -1, 1) * (inside ? SOUND.panIn : SOUND.panOut),
    wetOut: inside ? 0 : 1, wetIn: inside ? 1 : 0,                    // the room: apron outside, cabin inside
    inside,
    dirProp: inside ? 1 : 0.7 + 0.3 * (1 - c * c),
    dirWhine: inside ? 1 : 0.65 + 0.35 * Math.max(0, c),
    dirRoar: inside ? 1 : 0.85 + 0.15 * (1 - c) / 2,
  };
}
// the reference listener: the 3/4 view (front-port, ~22 m)
export const LISTEN_REF = { d: SOUND.D0, cos: 0.55, side: -0.25, inside: false, sta: -15, door: 0 };

// engine state e: {rpm, pitch (deg), ng (%), comb, light, starter, ign, power, lightN, lightAge} -> parameter
// targets.  Levels are approximate RMS amplitudes at the reference listener before the master gain (EngineVoice.set
// scales by the wave / noise-band RMS; the light-off's one-shot plays at shot x SHOTS.light.level); frequencies in Hz;
// depths are modulation depths (rms, the modulators have unit rms).  Closer than the 3/4 view the listener gain stops
// at the loudness ceiling (SOUND.ceil x the 3/4 view's reverse at 1,700 rpm, by the rms sum of the levels)
export function engineParams(e, L = listenerParams(LISTEN_REF)) {
  const p = rawParams(e, L);
  if (p.gain > 1 && !L.inside) p.gain = Math.min(p.gain, Math.max(1, SOUND.ceil * E_REF() / Math.max(levelE(p), 1e-9)));
  return p;
}
// the rms sum of the component levels (the mix's level before the listener gain, ~ its loudness for the ceiling)
function levelE(p) {
  let e = 0;
  for (const k of ['prop', 'fund', 'swish', 'growl', 'rasp', 'whine1', 'whine2', 'whine3', 'whine4', 'hay', 'roar', 'hiss', 'starter'])
    e += (p[k] || 0) ** 2;
  return Math.sqrt(e);
}
let _eRef = 0;
const E_REF = () => _eRef || (_eRef = levelE(rawParams({ rpm: PROP_RPM.max, pitch: -38, ng: ngRun(PROP_RPM.max, -38), comb: 1, power: 1 },
  listenerParams(LISTEN_REF))));
function rawParams(e, L) {
  const rpm = Math.max(0, +e.rpm || 0), r = rpm / PROP_RPM.max, pitch = +e.pitch || 0;
  const mTip = Math.PI * DIAM * rpm / 60 / C_SOUND;             // 0.70 at 1,700 rpm
  const load = bladeLoad(pitch), loadN = (0.1 + 0.9 * load) / (0.1 + 0.9 * bladeLoad(0));
  const rev = clamp(-pitch / 38, 0, 1), fea = clamp((pitch - 40) / 22, 0, 1);
  const ngN = (+e.ng || 0) / 100, ng = clamp(ngN, 0, 1.05), comb = clamp(+e.comb || 0, 0, 1), power = clamp(+e.power || 0, 0, 1);
  // (the tone gains less in reverse than the loading alone says: the stalled blades' energy goes broadband, below)
  const prop = 0.16 * Math.pow(r, 2.0) * loadN * (1 - 0.4 * rev) * L.dirProp;
  const lightV = clamp(+e.light || 0, 0, 1);
  const whine1 = 0.045 * Math.pow(ng, 0.6) * (0.7 + 0.3 * comb) * L.dirWhine;
  return {
    bladeHz: BLADES * rpm / 60, ngHz: ng * F_NG100, whineHz: WHINE[0] * ng * F_NG100,
    // propeller: tone + fundamental, harmonic content by tip Mach (more in reverse), the upper harmonics lifted in
    // reverse and modulated by the ingested turbulence, 1/rev wobble and gusts
    prop, fund: 0.7 * prop, propHi: 1 + 0.3 * rev,
    propLP: clamp(BLADES * rpm / 60 * (2 + 16 * mTip * mTip * (1 + 1.5 * rev) * (1 - 0.6 * fea)), 40, 9000),
    turbDepth: 0.42 + 0.1 * rev, shaftDepth: 0.05 + 0.10 * rev, gustDepth: 0.22 + 0.08 * rev,
    // (below ground idle, while the engine burns, the swish falls off as r^0.5 instead of r^1.1: the blades'
    // 'whoosh .. whoosh' as the propeller starts rolling after the light-off -- the moment the owner asked for -- is
    // heard, not only seen; it fades in over the first ~100 rpm; the run-down, fuel off, keeps r^1.1)
    swish: 0.11 * (r >= R_IDLE ? Math.pow(r, 1.1)
      : Math.pow(R_IDLE, 1.1) * Math.pow(r / R_IDLE, 1.1 - 0.6 * comb) * (1 - Math.exp(-((r / 0.06) ** 2))))
      * (0.3 + 0.7 * load) / (0.3 + 0.7 * bladeLoad(0)) * L.dirProp,
    swishF: 300 + 1200 * mTip, amBase: 0.3 + 0.55 * r,
    growl: 0.11 * rev * Math.pow(r, 1.8) * L.dirProp, growlF: 180 + 160 * r,
    rasp: 0.11 * rev * r * r * L.dirProp,                            // reverse: the broad 0.6-1.5 kHz rasp
    // gas generator: the compressor chord + haystack, the shaft tone, the starter, the inlet hiss
    whine1, whine2: 0.4 * 0.045 * Math.pow(ng, 1.8) * L.dirWhine, whine3: 0.35 * whine1, whine4: 0.25 * whine1,
    hay: 0.4 * whine1, roughDepth: 0.22,
    hum: 0.056 * whine1,                                             // 1 x Ng, -25 dB under the main whine
    // the starter: the main sound of the crank (the compressor barely turns), ~5 dB under the whine past 40 % Ng; its
    // brush / commutator whirr (STARTER_BRUSH x the shaft) sweeps up through the mid band in the first ~0.5 s: the
    // start's onset is heard on small speakers too
    starter: 0.034 * (1 - 0.5 * clamp((ngN - 0.2) / 0.2, 0, 1)) * L.dirWhine * (+e.starter || 0) * clamp(ngN / 0.03, 0, 1),
    hiss: 0.03 * Math.pow(ng, 2.5) * L.dirWhine, hissF: 2500 + 3000 * ng,
    // combustion / exhaust, light-off, igniters
    // (the light-off: the one-shot SHOTS.light, plus a surge of the roar and its low swell while the flame settles)
    roar: (comb * (0.033 + 0.165 * power) + 0.035 * lightV) * L.dirRoar, roarF: 300 + 1300 * power + 150 * comb + 400 * lightV,
    whoomp: 0.04 * lightV,
    shot: L.dirRoar, lightN: +e.lightN || 0, lightAge: e.lightAge === undefined ? -1 : +e.lightAge,
    tick: 0.25 * clamp(+e.ign || 0, 0, 1),
    // listener (closer than the 3/4 view: no louder than the ceiling, by the levels above)
    gain: L.gain, lpDist: L.lpDist, lpIn: L.lpIn, hiIn: L.hiIn, body: L.body, pan: L.pan, wetOut: L.wetOut, wetIn: L.wetIn,
  };
}

// ------------------------------------------------------------------ buffers and waves
function rng(seed) {                                  // mulberry32: deterministic noise (offline renders repeat)
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
// white noise loop (uniform +-1, rms 0.577)
function noiseBuffer(ctx, sec, seed) {
  const n = Math.round(sec * ctx.sampleRate), b = ctx.createBuffer(1, n, ctx.sampleRate), d = b.getChannelData(0), r = rng(seed);
  for (let i = 0; i < n; i++) d[i] = 2 * r() - 1;
  return b;
}
// a biquad on an array (RBJ cookbook; the modulators and the room responses are made with it)
function biquad(x, type, f, Q, sr) {
  const w = 2 * Math.PI * f / sr, cs = Math.cos(w), al = Math.sin(w) / (2 * Q);
  let b0, b1, b2;
  if (type === 'lowpass') { b0 = (1 - cs) / 2; b1 = 1 - cs; b2 = b0; }
  else if (type === 'highpass') { b0 = (1 + cs) / 2; b1 = -(1 + cs); b2 = b0; }
  else { b0 = al; b1 = 0; b2 = -al; }                             // bandpass (0 dB peak)
  const a0 = 1 + al, a1 = -2 * cs, a2 = 1 - al;
  let x1 = 0, x2 = 0, y1 = 0, y2 = 0;
  for (let i = 0; i < x.length; i++) {
    const y = (b0 * x[i] + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2) / a0;
    x2 = x1; x1 = x[i]; y2 = y1; y1 = y; x[i] = y;
  }
  return x;
}
// The modulators: 4 independent, unit-rms, seamlessly looping random signals in one buffer, played at MOD.rate (the
// buffer holds MOD.seconds x MOD.rate of signal at 8 kHz, so it lasts MOD.seconds at an effective 1 kHz):
//   0 gust   0.05-1.2 Hz  slow gusts of the propeller sound
//   1 turb   3-15 Hz      unsteady blade loading (the upper propeller harmonics, the swish)
//   2 drift  < 0.3 Hz     pitch / playback-rate drift
//   3 rough  25-90 Hz     the compressor scream's roughness
const MOD = { rate: 1 / 8, seconds: 47.3, sr: 1000,
  bands: [[0.05, 1.2], [3, 15], [0, 0.3], [25, 90]],
  // soft limits (sigma) of each channel's swells / dips: a gust or a turbulent load is capped where it would swell
  // (the multiplied swells of the chopped swish x turbulence x gusts made the loudest, rarest peaks: crest) and dips
  // as deep as before; then zero mean, unit rms again (the same envelope fluctuation)
  lim: [[1.5, 2.4], [1.5, 2.4], [2.2, 2.2], [2.2, 2.2]] };
function modBuffer(ctx) {
  const n = Math.round(MOD.seconds * MOD.sr), F = Math.round(2 * MOD.sr), pre = Math.round(20 * MOD.sr);
  const b = ctx.createBuffer(MOD.bands.length, n, 8000);
  MOD.bands.forEach(([lo, hi], ch) => {
    const r = rng(0x5eed + 977 * ch), x = new Float64Array(pre + n + F);
    for (let i = 0; i < x.length; i++) x[i] = 2 * r() - 1;
    if (lo > 0) { biquad(x, 'highpass', lo, 0.7, MOD.sr); biquad(x, 'highpass', lo, 0.7, MOD.sr); }
    biquad(x, 'lowpass', hi, 0.7, MOD.sr); biquad(x, 'lowpass', hi, 0.7, MOD.sr);
    // loop seam: the first F samples cross-fade from the signal's continuation past the end (no step at the loop)
    const y = b.getChannelData(ch);
    let sq = 0;
    for (let i = 0; i < n; i++) {
      const w = i < F ? 0.5 - 0.5 * Math.cos(Math.PI * i / F) : 1;
      y[i] = x[pre + i] * w + (i < F ? x[pre + n + i] * (1 - w) : 0);
      sq += y[i] * y[i];
    }
    // unit rms, the Gaussian tails softened (MOD.lim: a gust is a swell, not a spike), zero mean, unit rms again
    const [lp, ln] = MOD.lim[ch];
    let k = 1 / Math.sqrt(sq / n), mean = 0;
    for (let i = 0; i < n; i++) { const v = y[i] * k; y[i] = v > 0 ? lp * Math.tanh(v / lp) : ln * Math.tanh(v / ln); mean += y[i]; }
    mean /= n;
    let sq2 = 0;
    for (let i = 0; i < n; i++) { y[i] -= mean; sq2 += y[i] * y[i]; }
    k = 1 / Math.sqrt(sq2 / n);
    for (let i = 0; i < n; i++) y[i] *= k;
  });
  return b;
}
// the igniters' snaps: two a 0.8 s loop (~2.5 a second, estimate), each a ~4 ms crack ringing at ~3.2 kHz
function tickBuffer(ctx) {
  const sr = ctx.sampleRate, n = Math.round(0.8 * sr), b = ctx.createBuffer(1, n, sr), d = b.getChannelData(0), r = rng(7);
  for (const at of [0.02, 0.43]) {
    const i0 = Math.round(at * sr);
    for (let i = 0; i < Math.round(0.015 * sr) && i0 + i < n; i++) {
      const t = i / sr;
      d[i0 + i] += Math.exp(-t / 0.0015) * (0.6 * (2 * r() - 1) + 0.5 * Math.sin(2 * Math.PI * 3200 * t));
    }
  }
  return b;
}
// Gaussian band noise with its peaks rounded above TAME.lim sigma (a WaveShaper working in sigma units: the band is
// scaled to unit rms / TAME.k into the curve and back by TAME.k): the rare 4-5 sigma peaks of the broadband components
// set the crest factor of the whole mix, and so how loud it can play under the same peak level.  ~1.2 % of the
// samples are touched; what spills over (odd harmonics of a noise band) is noise again, and the tones stay clean
const TAME = { k: 8, lim: 2.5 };
function tameCurve() {
  const n = 4097, c = new Float32Array(n);
  for (let i = 0; i < n; i++) { const v = TAME.k * (2 * i / (n - 1) - 1); c[i] = TAME.lim * Math.tanh(v / TAME.lim) / TAME.k; }
  return c;
}
// The light-off (one-shot, played sample-accurately when GasGenerator.lightN counts up): the flame front's dull
// 'whump' -- a falling 95 -> 42 Hz thump, a broadband 'poof' (0.15-1.6 kHz, ~0.3 s), the combustor / stacks' hollow
// resonances (190 / 430 Hz) and a low rumble that hands over to the rising roar (~0.9 s).  Mono, peak 1; most of it
// above 150 Hz, so small speakers play it too.  Levels / timings are a viewer estimate
export const SHOTS = { light: { len: 2.2, level: 0.55 } };
function lightBuffer(ctx) {
  const sr = ctx.sampleRate, n = Math.round(SHOTS.light.len * sr), r = rng(0x11647);
  const noise = () => { const x = new Float64Array(n); for (let i = 0; i < n; i++) x[i] = 2 * r() - 1; return x; };
  const env = (x, rise, decay) => {
    let e = 0;
    for (let i = 0; i < n; i++) { const t = i / sr; x[i] *= (1 - Math.exp(-t / rise)) * Math.exp(-t / decay); e = Math.max(e, Math.abs(x[i])); }
    for (let i = 0; i < n; i++) x[i] /= e;
    return x;
  };
  const thump = new Float64Array(n);
  let ph = 0;
  for (let i = 0; i < n; i++) { const t = i / sr; ph += 2 * Math.PI * (42 + 53 * Math.exp(-t / 0.10)) / sr; thump[i] = Math.sin(ph); }
  env(thump, 0.010, 0.20);
  const poof = noise();
  biquad(poof, 'lowpass', 1600, 0.7, sr); biquad(poof, 'lowpass', 1600, 0.7, sr); biquad(poof, 'highpass', 150, 0.7, sr);
  env(poof, 0.018, 0.28);
  const hollow = noise(), h2 = noise();
  biquad(hollow, 'bandpass', 190, 4, sr); biquad(h2, 'bandpass', 430, 5, sr);
  for (let i = 0; i < n; i++) hollow[i] += 0.8 * h2[i];
  env(hollow, 0.035, 0.5);
  const rumble = noise();
  biquad(rumble, 'lowpass', 260, 0.7, sr); biquad(rumble, 'lowpass', 260, 0.7, sr);
  env(rumble, 0.12, 0.85);
  const b = ctx.createBuffer(1, n, sr), d = b.getChannelData(0);
  let pk = 0;
  for (let i = 0; i < n; i++) { d[i] = 0.75 * thump[i] + 0.6 * poof[i] + 0.55 * hollow[i] + 0.45 * rumble[i]; pk = Math.max(pk, Math.abs(d[i])); }
  const fade = Math.round(0.2 * sr);
  for (let i = 0; i < n; i++) d[i] *= (i > n - fade ? 0.5 + 0.5 * Math.cos(Math.PI * (i - n + fade) / fade) : 1) / pk;
  return b;
}
// The rooms (ConvolverNode impulse responses, stereo, independent per channel; the direct sound is the dry path):
// discrete early reflections [s, gain] per channel (slightly smeared) + a diffuse tail of low-passed noise (onset t0,
// decay tau = RT60 / 6.9) scaled to `tail` (energy re the direct sound).
//   out: the apron -- reflections off the ground / hangar fronts / other aircraft at 5-27 ms, a ~0.4 s tail
//   in:  the cabin -- dense reflections at 2-9 ms, ~80 ms decay, darker
export const ROOMS = {
  out: { len: 0.6, taps: [[[0.0068, 0.18], [0.0121, 0.10], [0.0230, 0.07]], [[0.0087, 0.18], [0.0104, 0.09], [0.0270, 0.07]]],
    t0: 0.012, rise: 0.015, tau: 0.058, lp: 3500, tail: 0.016 },
  in: { len: 0.12, taps: [[[0.0021, 0.22], [0.0047, 0.15], [0.0083, 0.10]], [[0.0029, 0.22], [0.0054, 0.14], [0.0091, 0.09]]],
    t0: 0.003, rise: 0.003, tau: 0.0125, lp: 2200, tail: 0.03 },
};
function roomIR(ctx, o, seed) {
  const sr = ctx.sampleRate, n = Math.round(o.len * sr), b = ctx.createBuffer(2, n, sr);
  for (let ch = 0; ch < 2; ch++) {
    const d = b.getChannelData(ch), r = rng(seed + 7919 * ch), x = new Float64Array(n);
    for (let i = 0; i < n; i++) x[i] = 2 * r() - 1;
    biquad(x, 'lowpass', o.lp, 0.7, sr);
    let e = 0;
    for (let i = 0; i < n; i++) {
      const t = i / sr - o.t0, fade = i > 0.8 * n ? 0.5 + 0.5 * Math.cos(Math.PI * (i - 0.8 * n) / (0.2 * n)) : 1;
      x[i] *= t < 0 ? 0 : (1 - Math.exp(-t / o.rise)) * Math.exp(-t / o.tau) * fade;
      e += x[i] * x[i];
    }
    const k = Math.sqrt(o.tail / Math.max(e, 1e-12));
    for (let i = 0; i < n; i++) d[i] = x[i] * k;
    for (const [t, a] of o.taps[ch]) {
      const i0 = Math.round(t * sr);
      d[i0 - 1] += 0.25 * a; d[i0] += 0.5 * a; d[i0 + 1] += 0.25 * a;
    }
  }
  return b;
}
// harmonics amp(n) at phase phase(n), n = 1 .. N.  The browser normalises the wave to a peak of 1: the peak of the
// sum (sampled) is returned, so gain = amplitude scale x peak
function harmonicWave(ctx, N, amp, phase = () => 0) {
  const real = new Float32Array(N + 1), imag = new Float32Array(N + 1);
  for (let n = 1; n <= N; n++) { const a = amp(n), p = phase(n); real[n] = a * Math.cos(p); imag[n] = -a * Math.sin(p); }
  let peak = 0, min = 0;
  for (let k = 0; k < 1024; k++) {
    let v = 0;
    for (let n = 1; n <= N; n++) { const th = n * 2 * Math.PI * k / 1024; v += real[n] * Math.cos(th) + imag[n] * Math.sin(th); }
    peak = Math.max(peak, Math.abs(v)); min = Math.min(min, v);
  }
  return { wave: ctx.createPeriodicWave(real, imag), peak, min: min / peak };
}
const propAmp = (n) => Math.pow(n, -0.7);
const PROP_UNIT = Math.sqrt(Array.from({ length: PROP_N }, (_, i) => propAmp(i + 1) ** 2).reduce((a, b) => a + b) / 2);
// a parameter-driven constant signal (ConstantSourceNode, or a looped buffer of ones through a gain on old Safari)
function constSource(ctx, sources) {
  if (ctx.createConstantSource) {
    const c = ctx.createConstantSource();
    c.offset.value = 0;
    sources.push(c);
    return { node: c, offset: c.offset };
  }
  const b = ctx.createBuffer(1, 128, ctx.sampleRate);
  b.getChannelData(0).fill(1);
  const s = ctx.createBufferSource(), g = ctx.createGain();
  s.buffer = b; s.loop = true; g.gain.value = 0; s.connect(g);
  sources.push(s);
  return { node: g, offset: g.gain };
}
// RMS of uniform white noise (+-1) after a filter of equivalent noise bandwidth enbw (Hz) -> the gain for RMS 1
const bandGain = (enbw, sr) => 1 / (0.577 * Math.sqrt(clamp(enbw, 1, sr / 2) / (sr / 2)));

export class EngineVoice {
  // ctx: an AudioContext or OfflineAudioContext; dest: where the limited stereo output goes
  constructor(ctx, dest) {
    this.ctx = ctx;
    const g = (v = 0) => { const n = ctx.createGain(); n.gain.value = v; return n; };
    const bq = (type, f, Q = Math.SQRT1_2, gain = 0) => {
      const n = ctx.createBiquadFilter();
      n.type = type; n.frequency.value = f; n.Q.value = Q; n.gain.value = gain;
      return n;
    };
    const osc = (type, wave, f0 = 0) => {
      const o = ctx.createOscillator();
      if (wave) o.setPeriodicWave(wave); else o.type = type;
      o.frequency.value = f0;
      sources.push(o);
      return o;
    };
    const chain = (...n) => { for (let i = 0; i < n.length - 1; i++) n[i].connect(n[i + 1]); return n[n.length - 1]; };
    const sources = [], starts = new Map();
    const tameC = tameCurve();
    // a band of noise -> unit rms / TAME.k (the AudioParam `pre`) -> the peak-rounding curve -> x TAME.k: unit rms out
    const tame = (src, name) => {
      const pre = g(0), sh = ctx.createWaveShaper(), post = g(TAME.k);
      sh.curve = tameC;
      chain(src, pre, sh, post);
      P[name] = pre.gain;
      return post;
    };
    const P = (this.p = {});            // name -> AudioParam

    // output: DC block -> distance low-pass -> cabin low-pass -> structure-borne drone -> listener gain (+ inside, the
    // whine's high band in parallel) -> pan -> master (volume x mute) -> limiter -> soft clip; listener -> the rooms
    const bus = (this.bus = g(1));
    const dc = bq('highpass', 20, 0.7), lpDist = bq('lowpass', 20000, 0.5), lpIn = bq('lowpass', 20000, 0.6);
    const body = bq('peaking', 120, 0.9, 0), listen = g(0), master = g(0), hiHP = bq('highpass', 1800, 0.7), hiIn = g(0);
    const pan = ctx.createStereoPanner ? ctx.createStereoPanner() : null;
    const comp = (this.comp = ctx.createDynamicsCompressor()), compIn = g(LIMITER.pre), compOut = g(1 / (LIMITER.pre * LIMITER.makeup));
    // a safety limiter for the close-ups: it sees the master x LIMITER.pre, so its threshold sits at
    // threshold - 20 log10(pre) dBFS of the mix (0 dBFS: above every peak of the 3/4 view); the browser's automatic
    // makeup gain (LIMITER.makeup, measured in Chromium for these settings) is taken back after it
    comp.threshold.value = LIMITER.threshold; comp.knee.value = LIMITER.knee; comp.ratio.value = LIMITER.ratio;
    comp.attack.value = LIMITER.attack; comp.release.value = LIMITER.release;
    // peak rounding (OUT_CURVE): linear to `knee`, then a tanh shoulder to `ceil`; the curve spans inputs of +-4
    // (pre-gain 0.25).  It rounds the rare peaks of the loud states (in reverse at the 3/4 view ~1-2 % of the samples
    // pass the knee, by <= 2 dB) without the gain riding of a compressor; quieter states never reach it
    const clipIn = g(0.25), clip = ctx.createWaveShaper(), curve = new Float32Array(8193);
    const { knee: kn, ceil: cl } = OUT_CURVE;
    for (let i = 0; i < curve.length; i++) {
      const x = 4 * (2 * i / (curve.length - 1) - 1), a = Math.abs(x);
      curve[i] = Math.sign(x) * (a < kn ? a : kn + (cl - kn) * Math.tanh((a - kn) / (cl - kn)));
    }
    clip.curve = curve;
    chain(bus, dc, lpDist, lpIn, body, listen);
    chain(lpDist, hiHP, hiIn, listen);
    if (pan) chain(listen, pan, master); else listen.connect(master);
    chain(master, compIn, comp, compOut, clipIn, clip, dest);
    const wetOut = g(0), wetIn = g(0);
    for (const [w, room, seed] of [[wetOut, ROOMS.out, 0x0a7e], [wetIn, ROOMS.in, 0xcab1]]) {
      const cv = ctx.createConvolver();
      cv.normalize = false;
      cv.buffer = roomIR(ctx, room, seed);
      chain(listen, w, cv, master);
    }
    Object.assign(P, { gain: listen.gain, lpDist: lpDist.frequency, lpIn: lpIn.frequency, hiIn: hiIn.gain, body: body.gain,
      master: master.gain, wetOut: wetOut.gain, wetIn: wetIn.gain });
    if (pan) P.pan = pan.pan;

    // noise: two long white loops (11.3 / 13.7 s); every broadband component reads its own copy from its own offset,
    // its playback rate wandering +-1.5 % with a slow modulator, so nothing repeats and no two components correlate
    const mod = ctx.createBufferSource();
    mod.buffer = modBuffer(ctx); mod.loop = true; mod.playbackRate.value = MOD.rate;
    sources.push(mod);
    const split = ctx.createChannelSplitter(MOD.bands.length);
    mod.connect(split);
    const M = (ch, k = 1) => { const m = g(k); split.connect(m, ch); return m; };   // a modulator x k
    const nA = noiseBuffer(ctx, 11.3, 0x9e3779b9), nB = noiseBuffer(ctx, 13.7, 0x85ebca6b);
    const wander = [M(2, 0.015), M(0, 0.012)];
    let nNoise = 0;
    const noise = (buf) => {
      const s = ctx.createBufferSource();
      s.buffer = buf; s.loop = true; s.playbackRate.value = 1;
      wander[nNoise % 2].connect(s.playbackRate);
      starts.set(s, (1.7 + 2.9 * nNoise++) % 10);
      sources.push(s);
      return s;
    };

    // the frequency drivers: blade-passing frequency and Ng shaft frequency (one automation each, all partials locked)
    const blade = constSource(ctx, sources), gas = constSource(ctx, sources);
    P.bladeHz = blade.offset; P.ngHz = gas.offset;
    const drive = (src, k, param) => { if (k === 1) src.node.connect(param); else { const m = g(k); src.node.connect(m); m.connect(param); } };

    // propeller: h1-3 in phase + fundamental; h4+ (Schroeder phases) low-passed by tip Mach and modulated by the
    // turbulence; all of it wobbling at 1/rev and with the gusts
    const lo = harmonicWave(ctx, PROP_LO, propAmp);
    const hi = harmonicWave(ctx, PROP_N, (n) => (n > PROP_LO ? propAmp(n) : 0), (n) => Math.PI * n * (n - 1) / 12);
    // (the chop of the swish / growl / rasp: the same blade-passage rhythm, its peak an eighth of a passage after the
    // tonal pulse -- the trailing edge leaving --, inaudible as such, but the two peaks no longer stack: CHOP)
    const soft = harmonicWave(ctx, 6, (n) => Math.pow(0.55, n - 1), (n) => 2 * Math.PI * n * CHOP);
    this.waves = { lo: lo.peak, hi: hi.peak, softMin: soft.min };
    const loO = osc(null, lo.wave), hiO = osc(null, hi.wave), fundO = osc('sine'), amO = osc(null, soft.wave), shaftO = osc('sine');
    for (const o of [loO, hiO, fundO, amO]) drive(blade, 1, o.frequency);
    drive(blade, 1 / BLADES, shaftO.frequency);
    const propLP = bq('lowpass', 200, 0.6), loG = g(0), hiG = g(0), fundG = g(0), turb = g(1), wob = g(1);
    const shaftD = g(0), gustD = g(0), turbD = g(0);
    chain(loO, loG, wob); chain(fundO, fundG, wob); chain(hiO, propLP, hiG, turb, wob); wob.connect(bus);
    chain(shaftO, shaftD, wob.gain); chain(M(0), gustD, wob.gain); chain(M(1), turbD, turb.gain);
    Object.assign(P, { propLo: loG.gain, propHi: hiG.gain, fund: fundG.gain, propLP: propLP.frequency, shaftDepth: shaftD.gain,
      gustDepth: gustD.gain, turbDepth: turbD.gain });
    // blade swish: broadband, amplitude-modulated by a soft pulse per blade passage (gain = base + pulse), unsteady
    const swBP = bq('bandpass', 600, 0.8), swAM = g(0.5), swG = g(0);
    chain(noise(nA), swBP);
    chain(tame(swBP, 'swPre'), swAM, swG, turb);
    amO.connect(swAM.gain);
    Object.assign(P, { swish: swG.gain, swishF: swBP.frequency, amBase: swAM.gain });
    // reverse / beta: the low growl (blade passage + 1/rev) and the broad rasp (blade passage, unsteady)
    const grBP = bq('bandpass', 220, 0.6), grAM = g(0.6), grG = g(0), grD = g(0.8), grS = g(0.35);
    chain(noise(nB), grBP);
    chain(tame(grBP, 'grPre'), grAM, grG, wob);
    chain(amO, grD, grAM.gain); chain(shaftO, grS, grAM.gain);
    const raBP = bq('bandpass', 950, 0.5), raAM = g(0.55), raG = g(0), raD = g(0.6);
    chain(noise(nB), raBP);
    chain(tame(raBP, 'raPre'), raAM, raG, turb);
    chain(amO, raD, raAM.gain);
    Object.assign(P, { growl: grG.gain, growlF: grBP.frequency, rasp: raG.gain });

    // gas generator: the compressor chord (each tone drifting on its own), its haystack and roughness, the shaft tone,
    // the starter whine, the inlet hiss
    const rough = g(1), roughD = g(0);
    chain(M(3), roughD, rough.gain); rough.connect(bus);
    const wG = [];
    WHINE.forEach((k, i) => {
      const o = osc('sine'), og = g(0);
      drive(gas, k, o.frequency);
      chain(M([2, 2, 2, 0][i], [4, 4, -6, 6][i]), o.detune);             // cents (rms): independent slow drifts
      chain(o, og, rough);
      wG.push(og);
    });
    const hayBP = bq('bandpass', 0, 25), hayG = g(0);
    drive(gas, WHINE[0], hayBP.frequency);
    chain(noise(nA), hayBP, hayG, rough);
    const hum = osc('sine'), humG = g(0);
    drive(gas, 1, hum.frequency); chain(hum, humG, bus);
    const stLP = bq('lowpass', 700, 0.7), stG = g(0);
    STARTER.forEach((k, i) => { const o = osc('sine'), og = g([1, 0.5, 0.3][i]); drive(gas, k, o.frequency); chain(o, og, stLP); });
    chain(stLP, stG, bus);
    const brO = osc('sine'), brLP = bq('lowpass', 3200, 0.7), brG = g(0.45);
    drive(gas, STARTER_BRUSH, brO.frequency);
    chain(M(2, 8), brO.detune);
    chain(brO, brLP, brG, stG);
    const hiHPn = bq('highpass', 3000, 0.6), hiG2 = g(0);
    chain(noise(nA), hiHPn, hiG2, bus);
    Object.assign(P, { whine1: wG[0].gain, whine2: wG[1].gain, whine3: wG[2].gain, whine4: wG[3].gain, hay: hayG.gain,
      roughDepth: roughD.gain, hum: humG.gain, starter: stG.gain, hiss: hiG2.gain, hissF: hiHPn.frequency });
    // combustion / exhaust roar, the light-off 'whoomp', the igniters
    const roLP = bq('lowpass', 500, 0.5), roG = g(0), whLP = bq('lowpass', 140, 0.9), whG = g(0);
    chain(noise(nB), roLP);
    chain(tame(roLP, 'roPre'), roG, bus); chain(noise(nA), whLP, whG, bus);
    // the one-shots (the light-off): fixed relative levels into one listener-scaled gain
    const shotG = g(0);
    shotG.connect(bus);
    P.shot = shotG.gain;
    this.shots = {};
    for (const [k, o] of Object.entries(SHOTS)) { const sg = g(o.level); sg.connect(shotG); this.shots[k] = { buffer: lightBuffer(ctx), gain: sg }; }
    this.seen = {};
    const tk = ctx.createBufferSource(), tkG = g(0);
    tk.buffer = tickBuffer(ctx); tk.loop = true; sources.push(tk);
    chain(tk, tkG, bus);
    Object.assign(P, { roar: roG.gain, roarF: roLP.frequency, whoomp: whG.gain, tick: tkG.gain });

    this.sr = ctx.sampleRate;
    this.last = {};
    this.target = {};
    const t0 = ctx.currentTime;
    for (const s of sources) s.start(t0, starts.get(s) || 0);
    this.sources = sources;
  }

  _put(name, v, when, tau) {
    const p = this.p[name];
    if (!p || !Number.isFinite(v)) return;
    const last = this.last[name];
    if (last !== undefined && Math.abs(v - last) <= 1e-5 * Math.max(1, Math.abs(v))) return;
    this.last[name] = v;
    this.target[name] = v;
    p.setTargetAtTime(v, when, tau);
  }

  // p: engineParams(); when: context time
  set(p, when) {
    const sr = this.sr, lim = 0.45 * sr, T = SOUND.tau, TL = SOUND.tauL, W = this.waves;
    const put = (k, v, tau = T) => this._put(k, v, when, tau);
    const A = p.prop / PROP_UNIT;                    // the harmonic amplitude scale: harmonic n = A n^-0.7
    put('bladeHz', p.bladeHz); put('ngHz', p.ngHz);
    put('propLo', A * W.lo); put('propHi', A * W.hi * p.propHi); put('fund', p.fund * SQRT2); put('propLP', Math.min(p.propLP, lim));
    put('shaftDepth', p.shaftDepth); put('gustDepth', p.gustDepth); put('turbDepth', p.turbDepth);
    const K = TAME.k;
    put('swishF', p.swishF); put('swPre', bandGain(1.57 * p.swishF / 0.8, sr) / K); put('swish', p.swish);
    put('amBase', Math.max(p.amBase, -W.softMin));
    put('growlF', p.growlF); put('grPre', bandGain(1.57 * p.growlF / 0.6, sr) / K); put('growl', p.growl);
    put('raPre', bandGain(1.57 * 950 / 0.5, sr) / K); put('rasp', p.rasp);
    put('whine1', p.whine1 * SQRT2); put('whine2', p.whine2 * SQRT2); put('whine3', p.whine3 * SQRT2); put('whine4', p.whine4 * SQRT2);
    put('hay', p.hay * bandGain(1.57 * Math.max(p.whineHz, 100) / 25, sr)); put('roughDepth', p.roughDepth);
    put('hum', p.hum * SQRT2); put('starter', p.starter * SQRT2);
    put('hissF', p.hissF); put('hiss', p.hiss * bandGain(sr / 2 - p.hissF, sr));
    put('roarF', p.roarF); put('roPre', bandGain(1.1 * p.roarF, sr) / K); put('roar', p.roar);
    put('whoomp', p.whoomp * bandGain(1.1 * 140, sr)); put('tick', p.tick); put('shot', p.shot);
    // the one-shots: an event that counted up less than 0.5 s ago plays from its own time (a late frame starts it now)
    if (p.lightN !== this.seen.light) {
      if (p.lightAge >= 0 && p.lightAge < 0.5) this.fire('light', when - p.lightAge);
      this.seen.light = p.lightN;
    }
    put('gain', p.gain, TL); put('lpDist', Math.min(p.lpDist, lim), TL); put('lpIn', Math.min(p.lpIn, lim), TL);
    put('hiIn', p.hiIn, TL); put('body', p.body, TL); put('pan', p.pan, TL); put('wetOut', p.wetOut, TL); put('wetIn', p.wetIn, TL);
  }

  setMaster(v, when) { this._put('master', v, when, SOUND.tauM); }

  fire(name, at) {
    const sh = this.shots[name];
    if (!sh) return;
    const s = this.ctx.createBufferSource();
    s.buffer = sh.buffer;
    s.connect(sh.gain);
    s.onended = () => s.disconnect();
    s.start(Math.max(at, this.ctx.currentTime, 0));
    this.fired = (this.fired || 0) + 1;
  }

  // current AudioParam values (tests)
  values() {
    const o = {};
    for (const k of ['bladeHz', 'ngHz', 'master', 'gain', 'lpIn', 'hiIn', 'lpDist', 'propLo', 'propHi', 'whine1', 'roar', 'growl',
      'rasp', 'pan', 'wetOut', 'wetIn']) if (this.p[k]) o[k] = this.p[k].value;
    o.reduction = this.comp.reduction;
    return o;
  }
}

// ------------------------------------------------------------------ controller (live page)
const _hub = new THREE.Vector3(), _v = new THREE.Vector3(), _r = new THREE.Vector3();
const lsGet = (k) => { try { return window.localStorage.getItem(k); } catch (e) { return null; } };
const lsSet = (k, v) => { try { window.localStorage.setItem(k, v); } catch (e) { /* storage blocked: session only */ } };

export class Sound {
  // ui: {buttons: [toggle buttons (aria-pressed)], chip: the floating toggle shown while the engine runs,
  //      volume: range input 0 .. 1}
  constructor({ kin, stage, model, tour, ui = {} }) {
    Object.assign(this, { kin, stage, model, tour, ui });
    this.AC = window.AudioContext || window.webkitAudioContext || null;
    this.supported = !!this.AC;
    // default: on (it only ever sounds after a gesture); off under automation (tests) unless ?sound=1 or a stored choice
    const q = new URLSearchParams(location.search).get('sound');
    const stored = lsGet(SOUND.storeKey);
    this.on = q === '1' || q === 'on' ? true : q === '0' || q === 'off' ? false
      : stored === 'on' ? true : stored === 'off' ? false : !navigator.webdriver;
    const v = parseFloat(lsGet(SOUND.volKey));
    this.vol = Number.isFinite(v) ? clamp(v, 0, 1) : SOUND.volume;
    this.ctx = null; this.voice = null; this.created = 0;
    this.gesture = false;        // the page has had a user gesture (sticky activation)
    this.unlocked = false;       // the context has run at least once (iOS: resumed inside a gesture)
    this.active = false;         // the engine turns / burns
    this.tailUntil = 0;          // keep running until (performance.now ms): the run-down tail, a fresh context
    this.idleTimer = 0; this.busy = false;
    this.params = null; this.geo = null;
    const rec = model.part('propeller');
    this.hub = rec ? rec.node : null;
    this.axis = kin.surf.propeller ? kin.surf.propeller.axis : new THREE.Vector3(0, 0, -1);   // forward
    this._wire();
    this._syncUI();
  }

  _wire() {
    // a gesture that starts the engine creates the context (while sound is on): the bubbling listener runs after the
    // button's / key's own handler, so the click on Idle (or P, the demo) counts -- and iOS unlocks a context only
    // inside a gesture.  A gesture with the engine off (an orbit drag) opens no audio device; any gesture also
    // resumes a context that has something to play
    const opts = { capture: true, passive: true };
    const first = (e) => {
      if (!e.isTrusted) return;
      this.gesture = true;
      this._resumeIn(false);
    };
    const after = (e) => {
      if (!e.isTrusted) return;
      if (this.on && this.supported && !this.ctx && this._engineOn()) this._create();
      this._resumeIn(true);
    };
    for (const t of ['pointerdown', 'pointerup', 'keydown', 'touchend', 'click']) {
      window.addEventListener(t, first, opts);
      window.addEventListener(t, after, { passive: true });
    }
    document.addEventListener('visibilitychange', () => {
      if (!this.ctx) return;
      if (document.hidden) { if (this.ctx.state === 'running') this.ctx.suspend().catch(() => {}); }
      else this.update();
    });
    for (const b of this.ui.buttons || []) b.addEventListener('click', () => this.toggle());
    const vol = this.ui.volume;
    if (vol) {
      vol.value = String(this.vol);
      vol.addEventListener('input', () => this.setVolume(+vol.value));
    }
  }

  // inside a user gesture: resume a context that has never run (iOS unlock), or one that has something to play
  _resumeIn(afterHandlers) {
    const ctx = this.ctx;
    if (!ctx || !this.on || document.hidden || ctx.state === 'running' || ctx.state === 'closed') return;
    if (!this.unlocked || (afterHandlers && this._wanted())) ctx.resume().catch(() => {});
  }

  _create() {
    try {
      try { this.ctx = new this.AC({ latencyHint: 'interactive' }); } catch (e) { this.ctx = new this.AC(); }
    } catch (e) {
      console.warn('Web Audio unavailable, no engine sound:', e.message || e);
      this.supported = false; this.ctx = null; this._syncUI();
      return;
    }
    this.created++;
    this.voice = new EngineVoice(this.ctx, this.ctx.destination);
    this.tailUntil = performance.now() + 1500;
    // (busy: a resume() outside a gesture may stay pending on Safari until a gesture runs it -- any change frees it)
    // (a context that starts running with nothing to play suspends on the idle timer, without waiting for a frame)
    this.ctx.onstatechange = () => {
      this.busy = false;
      if (this.ctx.state !== 'running') return;
      this.unlocked = true;
      if (!this._wanted() && !this.idleTimer) this._scheduleIdle();
    };
    if (this.ctx.state === 'running') this.unlocked = true;
  }

  // nothing to play (engine stopped + its tail, muted): suspend once the master / the last sounds have faded -- on a
  // timer, so it happens even while frames are slow or throttled
  _scheduleIdle() {
    clearTimeout(this.idleTimer);
    this.idleTimer = setTimeout(() => {
      this.idleTimer = 0;
      const ctx = this.ctx;
      if (!ctx || ctx.state !== 'running') return;
      if (!this._wanted()) ctx.suspend().catch(() => {});
      else if (!this._engineOn() || !this.on) this._scheduleIdle();      // the tail is still running out
    }, (this.on && !document.hidden ? Math.max(0, this.tailUntil - performance.now()) : 0) + 450);
  }

  _engineOn() {
    const k = this.kin;
    return k.t.rpm > 0 || k.c.rpm > 0.5 || k.gg.ng > 0.05;
  }
  _wanted() { return this.on && !document.hidden && (this._engineOn() || performance.now() < this.tailUntil); }

  toggle(on = !this.on) {
    this.on = !!on;
    lsSet(SOUND.storeKey, this.on ? 'on' : 'off');
    if (this.on && this.supported) {
      if (!this.ctx && this.gesture && this._engineOn()) this._create();
      this.tailUntil = Math.max(this.tailUntil, performance.now() + 600);
      if (this.ctx && this.ctx.state !== 'running' && !document.hidden) this.ctx.resume().catch(() => {});
    }
    if (this.voice) {
      this.voice.setMaster(this._masterLevel(), this.ctx.currentTime);
      if (!this.on) this._scheduleIdle();
    }
    this._syncUI();
    return this.on;
  }

  setVolume(v) {
    this.vol = clamp(+v || 0, 0, 1);
    lsSet(SOUND.volKey, String(this.vol));
    if (this.ui.volume && +this.ui.volume.value !== this.vol) this.ui.volume.value = String(this.vol);
    if (this.voice) this.voice.setMaster(this._masterLevel(), this.ctx.currentTime);
  }

  _masterLevel() { return this.on && !document.hidden ? SOUND.level * this.vol * this.vol : 0; }

  _syncUI() {
    const label = !this.supported ? 'Engine sound: not supported by this browser'
      : `Engine sound ${this.on ? 'on' : 'off'} (M)`;
    for (const b of this.ui.buttons || []) {
      b.setAttribute('aria-pressed', String(this.on && this.supported));
      b.title = label;
      b.disabled = !this.supported;
    }
    if (this.ui.chip) this.ui.chip.hidden = !(this.active && this.supported);
  }

  // the camera relative to the propeller hub (glTF axes; the station is Z)
  _geometry() {
    const cam = this.stage.camera;
    cam.updateMatrixWorld();
    if (this.hub) this.hub.getWorldPosition(_hub); else _hub.set(0, 1.655, 0.925);
    _v.subVectors(cam.position, _hub);
    const d = Math.max(1e-3, _v.length());
    _r.setFromMatrixColumn(cam.matrixWorld, 0);
    const k = this.kin.c;
    return {
      d, cos: _v.dot(this.axis) / d, side: -_v.dot(_r) / d,
      inside: !!(this.tour && this.tour.inside) || !!this.model.camInside, sta: cam.position.z,
      door: Math.max(k.door_airstair || 0, k.door_cargo || 0),
    };
  }

  // every frame (main.js): follow the engine state and the camera, run / suspend the context
  update() {
    const active = this._engineOn();
    if (active !== this.active) { this.active = active; this._syncUI(); }
    const now = performance.now();
    if (active) this.tailUntil = now + 2000;          // the run-down's last sounds, then suspend
    if (!this.ctx) {
      // sticky activation (Chrome, Firefox): a start without a gesture of its own (the demo's steps) after the user
      // has interacted with the page
      if (active && this.on && this.gesture && this.supported) this._create();
      if (!this.ctx) return;
    }
    const ctx = this.ctx, want = this._wanted();
    if (want && ctx.state === 'suspended' && !this.busy) {
      this.busy = true;
      ctx.resume().catch(() => {}).then(() => { this.busy = false; });
    }
    if (active && this.on) { if (this.idleTimer) { clearTimeout(this.idleTimer); this.idleTimer = 0; } }
    else if (ctx.state === 'running' && !this.idleTimer) this._scheduleIdle();
    if (ctx.state !== 'running') return;
    const c = this.kin.c;
    this.geo = this._geometry();
    this.params = engineParams({ rpm: c.rpm, pitch: c.pitch, ...this.kin.gg.state }, listenerParams(this.geo));
    this.voice.set(this.params, ctx.currentTime);
    this.voice.setMaster(want ? this._masterLevel() : 0, ctx.currentTime);
  }

  state() {
    const c = this.kin.c, ctx = this.ctx;
    return {
      supported: this.supported, on: this.on, volume: this.vol, level: SOUND.level, gesture: this.gesture, created: this.created,
      ctx: ctx ? ctx.state : null, time: ctx ? ctx.currentTime : 0, graph: !!this.voice, active: this.active,
      unlocked: this.unlocked, engine: { rpm: c.rpm, pitch: c.pitch, ...this.kin.gg.state },
      targets: this.params ? { ...this.params } : null, values: this.voice ? this.voice.values() : null,
      set: this.voice ? { ...this.voice.target } : null, listener: this.geo ? { ...this.geo } : null,
      chip: this.ui.chip ? !this.ui.chip.hidden : null, shots: this.voice ? this.voice.fired || 0 : 0,
    };
  }
}

// ------------------------------------------------------------------ offline render (tests)
// Steps the viewer's Kinematics (kin) through script [{t, set: setProp argument, instant}] in 1/rate s steps and
// renders the same EngineVoice / engineParams on an OfflineAudioContext; returns the AudioBuffer, a log of the state
// and the limiter's gain reduction (dB, sampled every grStep s through the context's suspend points); mute: names of
// engineParams() levels held at 0 (diagnostics).
export async function renderOffline({ kin, script, duration = 47, sampleRate = 44100, listener = LISTEN_REF,
  volume = SOUND.volume, rate = 60, grStep = 0.05, mute = [] }) {
  const OAC = window.OfflineAudioContext || window.webkitOfflineAudioContext;
  const ctx = new OAC(2, Math.ceil(duration * sampleRate), sampleRate);
  const voice = new EngineVoice(ctx, ctx.destination);
  const L = listenerParams(listener);
  voice.setMaster(SOUND.level * volume * volume, 0);
  const dt = 1 / rate, log = [], gr = [];
  let k = 0;
  for (let i = 0; i * dt < duration; i++) {
    const t = i * dt;
    while (k < script.length && script[k].t <= t + 1e-9) { kin.setProp(script[k].set, !!script[k].instant); k++; }
    if (i > 0) kin.update(dt);
    const e = { rpm: kin.c.rpm, pitch: kin.c.pitch, ...kin.gg.state };
    const p = engineParams(e, L);
    for (const m of mute) p[m] = 0;                 // (diagnostics: components held silent)
    voice.set(p, t);
    if (i % 3 === 0) {
      log.push({ t, rpm: e.rpm, pitch: e.pitch, ng: e.ng, phase: e.phase, lit: e.lit, comb: e.comb, light: e.light,
        starter: e.starter, bladeHz: p.bladeHz, whineHz: p.whineHz, prop: p.prop, swish: p.swish, whine1: p.whine1,
        roar: p.roar, growl: p.growl, rasp: p.rasp });
    }
  }
  if (grStep > 0 && ctx.suspend) {
    for (let t = grStep; t < duration - 1e-3; t += grStep) {
      ctx.suspend(t).then(() => { gr.push([ctx.currentTime, voice.comp.reduction]); ctx.resume(); }).catch(() => {});
    }
  }
  const buffer = await ctx.startRendering();
  return { buffer, log, gr };
}

// 16-bit PCM WAV of an AudioBuffer
export function encodeWav(buffer) {
  const ch = buffer.numberOfChannels, n = buffer.length, sr = buffer.sampleRate;
  const data = new DataView(new ArrayBuffer(44 + n * ch * 2));
  const str = (o, s) => { for (let i = 0; i < s.length; i++) data.setUint8(o + i, s.charCodeAt(i)); };
  str(0, 'RIFF'); data.setUint32(4, 36 + n * ch * 2, true); str(8, 'WAVE'); str(12, 'fmt ');
  data.setUint32(16, 16, true); data.setUint16(20, 1, true); data.setUint16(22, ch, true); data.setUint32(24, sr, true);
  data.setUint32(28, sr * ch * 2, true); data.setUint16(32, ch * 2, true); data.setUint16(34, 16, true);
  str(36, 'data'); data.setUint32(40, n * ch * 2, true);
  const chans = [];
  for (let c = 0; c < ch; c++) chans.push(buffer.getChannelData(c));
  let o = 44;
  for (let i = 0; i < n; i++) {
    for (let c = 0; c < ch; c++) {
      const s = clamp(chans[c][i], -1, 1);
      data.setInt16(o, s < 0 ? s * 32768 : s * 32767, true);
      o += 2;
    }
  }
  return new Uint8Array(data.buffer);
}

// the offline render as a base64 WAV plus its peak, the state log and the limiter's gain reduction (test hook;
// grMax: the deepest reduction, dB <= 0)
export async function renderOfflineWav(opts) {
  const { buffer, log, gr } = await renderOffline(opts);
  let peak = 0;
  for (let c = 0; c < buffer.numberOfChannels; c++) {
    const d = buffer.getChannelData(c);
    for (let i = 0; i < d.length; i++) { const a = Math.abs(d[i]); if (a > peak) peak = a; }
  }
  const u8 = encodeWav(buffer);
  let s = '';
  for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000));
  const grMax = gr.reduce((m, [t, v]) => (t >= 2 ? Math.min(m, v) : m), 0);    // (the compressor's start-up metering: < 2 s)
  return { wav: btoa(s), log, gr, grMax, sampleRate: buffer.sampleRate, channels: buffer.numberOfChannels, seconds: buffer.duration, peak };
}
