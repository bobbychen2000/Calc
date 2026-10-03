// Engine and propeller sound (owner 2026-10-03: "can you add sound effect too when propellor starts rolling").
//
// Pure Web Audio synthesis from built-in nodes (oscillators, looped noise buffers, biquads, gains, a compressor; no
// files, no AudioWorklet module: the claude.ai Artifact's CSP), driven every frame by the state the viewer animates --
// the propeller spool and the gas generator of kinematics.js (GasGenerator: Ng, light-off, starter, igniters) -- so a
// start, a power change or a shutdown sounds exactly as long as it looks.  The same graph (EngineVoice) and the same
// state -> parameter law (engineParams) render offline for the tests (renderOffline: test/viewer_test.py writes the
// WAV and its spectrogram).
//
// Sound design: a PT6E-67XP free-turbine turboprop with the Hartzell 5-blade composite propeller (2.67 m).  Sources
// and assumptions (levels and timings are viewer estimates for a plausible, comfortable sound, not measurements):
//  - propeller (the dominant source): the blade-passing tone at 5 x rpm / 60 Hz (83 Hz at the ~1,000 rpm ground idle,
//    142 Hz at 1,700 rpm) with its harmonics -- the classic result of propeller-noise theory (Gutin; Hubbard ed.,
//    "Aeroacoustics of Flight Vehicles", NASA RP-1258, 1991: loading and thickness noise at the blade-passage harmonics,
//    the higher harmonics growing steeply with the tip Mach number).  Tip Mach 0.41 at 1,000 rpm, 0.70 at 1,700 static:
//    a pulse wave low-passed at a harmonic count that grows with Mt^2, level ~ (rpm / 1,700)^2.2 x the blade loading
//    (kinematics.js bladeLoad: the feathered blades edge-on to the flow are much quieter; reverse loads them most).
//    The broadband blade 'swish' is amplitude-modulated at the blade passage (the chop heard while the propeller turns
//    slowly), with a 1/rev wobble (blade-to-blade differences) and slow gusty fluctuations.  Beta / reverse adds the
//    characteristic low roar / 'growl' of the reversed, partly stalled blades (broadband, rough, modulated at the
//    blade passage and 1/rev).
//  - gas generator: the compressor whine at a blade-passing order of Ng (100 % = 37,468 rpm = 624 Hz, the PT6A-60 /
//    -67 series' figure, assumed for the -67XP; the blade counts are not public: the main tone is taken at 16 x the
//    shaft frequency -- ~6 kHz at the ~60 % ground idle, ~9-10 kHz near 100 % -- plus its 2nd harmonic), a hum at
//    2 x Ng and a broadband inlet hiss ~ Ng^2.5.  During the start: the electric starter-generator's whirr and the
//    igniters' snaps (~2.5 a second) until the starter cuts out at 50 % Ng (PT6 start practice).
//  - combustion / exhaust: broadband roar once lit (low-passed noise, brighter and louder with power); the light-off a
//    soft low 'whoomp' (GasGenerator.light).
//  - listener = the camera: distance to the propeller hub -> level ~ (D0 / d)^0.85 and a gentle low-pass (air
//    absorption); the propeller tone loudest in its plane of rotation, the inlet whine ahead (the chin inlet), the
//    exhaust beside / behind (the stacks).  Inside the cabin (the interior tour or a camera inside the closed cabin):
//    strongly low-passed (~0.9 kHz on the flight deck, ~0.5 kHz in the aft cabin) with the propeller's low drone kept
//    (structure-borne, a +6 dB bump near the blade-passing frequency), quieter aft; an open door lets more in.
//    Stereo: panned toward the hub's side of the screen.
//  - output: DC block, master gain (volume x mute), a compressor and a soft clip: nothing clips.
// Browsers start audio only after a user gesture: the AudioContext is created on the first gesture while sound is on
// (the engine buttons and keys count), suspended while the engine is off, the page hidden or the sound muted.
import * as THREE from 'three';
import { PROP_RPM, NG, bladeLoad } from './kinematics.js';

const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const BLADES = 5, DIAM = 2.67, C_SOUND = 340;
const F_NG100 = NG.rpm100 / 60;           // Hz, the gas generator's shaft frequency at 100 % Ng
const WHINE_ORDER = 16;                   // compressor whine: blade-passing order of the shaft frequency (assumed)
const STARTER_ORDER = 2.6;                // starter-generator whirr (gear ratio x poles, assumed)
const SQRT2 = Math.SQRT2, SQRT3 = Math.sqrt(3);

export const SOUND = {
  volume: 0.8,                            // default volume (master gain = level x volume^2)
  level: 1.5,                             // master scale: ~-16 dBFS rms at 1,700 rpm in the 3/4 view at the default volume
  D0: 22,                                 // m: the 3/4 view's camera distance to the hub (960 x 600) -> listener gain 1
  tau: 0.05,                              // s, source parameter smoothing (setTargetAtTime): no zipper noise
  tauL: 0.12,                             // s, listener (distance, cabin) smoothing
  tauM: 0.04,                             // s, master (mute)
  inside: { staFwd: 4.2, staAft: 9.0, lpFwd: 900, lpAft: 480, gainFwd: 0.55, gainAft: 0.28, body: 6 },
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
      : Math.min(1.8, Math.pow(SOUND.D0 / Math.max(g.d, 3), 0.85)),
    lpDist: inside ? 20000 : clamp(20000 * Math.pow(10 / Math.max(g.d, 10), 0.45), 3500, 20000),
    lpIn: inside ? Math.min(20000, (I.lpFwd + (I.lpAft - I.lpFwd) * f) * (1 + 3 * door)) : 20000,
    body: inside ? I.body * (1 - 0.5 * door) : 0,
    pan: clamp(+g.side || 0, -1, 1) * (inside ? 0.25 : 0.6),
    dirProp: inside ? 1 : 0.7 + 0.3 * (1 - c * c),
    dirWhine: inside ? 1 : 0.65 + 0.35 * Math.max(0, c),
    dirRoar: inside ? 1 : 0.85 + 0.15 * (1 - c) / 2,
  };
}
// the reference listener: the 3/4 view (front-port, ~22 m)
export const LISTEN_REF = { d: SOUND.D0, cos: 0.55, side: -0.25, inside: false, sta: -15, door: 0 };

// engine state e: {rpm, pitch (deg), ng (%), comb, light, starter, ign, power} -> parameter targets.  Levels are
// approximate RMS amplitudes at the reference listener before the master gain (EngineVoice.set scales by the wave /
// noise-band RMS); frequencies in Hz.
export function engineParams(e, L = listenerParams(LISTEN_REF)) {
  const rpm = Math.max(0, +e.rpm || 0), r = rpm / PROP_RPM.max, pitch = +e.pitch || 0;
  const mTip = Math.PI * DIAM * rpm / 60 / C_SOUND;             // 0.70 at 1,700 rpm
  const load = bladeLoad(pitch), loadN = (0.1 + 0.9 * load) / (0.1 + 0.9 * bladeLoad(0));
  const rev = clamp(-pitch / 38, 0, 1), fea = clamp((pitch - 40) / 22, 0, 1);
  const ng = clamp((+e.ng || 0) / 100, 0, 1.05), comb = clamp(+e.comb || 0, 0, 1), power = clamp(+e.power || 0, 0, 1);
  const prop = 0.16 * Math.pow(r, 2.2) * loadN * L.dirProp;
  return {
    bladeHz: BLADES * rpm / 60, ngHz: ng * F_NG100, whineHz: WHINE_ORDER * ng * F_NG100,
    // propeller: tone + fundamental, harmonic content by tip Mach, 1/rev and gusty wobble
    prop, fund: 0.7 * prop,
    propLP: clamp(BLADES * rpm / 60 * (2 + 16 * mTip * mTip * (1 + 0.5 * rev) * (1 - 0.6 * fea)), 40, 9000),
    shaftDepth: 0.05 + 0.10 * rev, wobDepth: 0.6 + 0.8 * rev,
    swish: 0.05 * Math.pow(r, 1.6) * (0.3 + 0.7 * load) / (0.3 + 0.7 * bladeLoad(0)) * L.dirProp,
    swishF: 300 + 1200 * mTip, amBase: 0.3 + 0.55 * r,
    growl: 0.12 * rev * Math.pow(r, 1.8) * L.dirProp, growlF: 180 + 160 * r,
    // gas generator
    whine1: 0.045 * Math.pow(ng, 0.8) * (0.7 + 0.3 * comb) * L.dirWhine,
    whine2: 0.4 * 0.045 * Math.pow(ng, 1.8) * L.dirWhine,
    hum: 0.012 * ng,
    starter: 0.025 * (+e.starter || 0) * clamp((+e.ng || 0) / 5, 0, 1),
    hiss: 0.03 * Math.pow(ng, 2.5) * L.dirWhine, hissF: 2500 + 3000 * ng,
    // combustion / exhaust, light-off, igniters
    roar: comb * (0.025 + 0.08 * power) * L.dirRoar, roarF: 300 + 1300 * power + 150 * comb,
    whoomp: 0.07 * clamp(+e.light || 0, 0, 1),
    tick: 0.25 * clamp(+e.ign || 0, 0, 1),
    // listener
    gain: L.gain, lpDist: L.lpDist, lpIn: L.lpIn, body: L.body, pan: L.pan,
  };
}

// ------------------------------------------------------------------ the graph
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
function noiseBuffer(ctx, sec, seed) {
  const n = Math.round(sec * ctx.sampleRate), b = ctx.createBuffer(1, n, ctx.sampleRate), d = b.getChannelData(0), r = rng(seed);
  for (let i = 0; i < n; i++) d[i] = 2 * r() - 1;
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
// in-phase cosine harmonics amp(n), n = 1 .. N: a pulse train.  The browser normalises the wave to a peak of 1 (the
// sum of the amplitudes, at phase 0): rms / min of the normalised wave are returned for the level scaling
function harmonicWave(ctx, N, amp) {
  const real = new Float32Array(N + 1), imag = new Float32Array(N + 1);
  let peak = 0, sq = 0;
  for (let n = 1; n <= N; n++) { real[n] = amp(n); peak += real[n]; sq += real[n] * real[n]; }
  let min = 0;
  for (let k = 0; k < 256; k++) {
    let v = 0;
    for (let n = 1; n <= N; n++) v += real[n] * Math.cos(n * 2 * Math.PI * k / 256);
    min = Math.min(min, v / peak);
  }
  return { wave: ctx.createPeriodicWave(real, imag), rms: Math.sqrt(sq / 2) / peak, min };
}
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
    const osc = (type, wave) => {
      const o = ctx.createOscillator();
      if (wave) o.setPeriodicWave(wave); else o.type = type;
      o.frequency.value = 0;
      sources.push(o);
      return o;
    };
    const loop = (buf, rate = 1) => {
      const s = ctx.createBufferSource();
      s.buffer = buf; s.loop = true; s.playbackRate.value = rate;
      sources.push(s);
      return s;
    };
    const chain = (...n) => { for (let i = 0; i < n.length - 1; i++) n[i].connect(n[i + 1]); return n[n.length - 1]; };
    const sources = [];
    const P = (this.p = {});            // name -> AudioParam

    // output: DC block -> distance low-pass -> cabin low-pass -> structure-borne drone -> listener gain -> pan ->
    // master (volume x mute) -> compressor -> soft clip
    const bus = (this.bus = g(1));
    const dc = bq('highpass', 20, 0.7), lpDist = bq('lowpass', 20000, 0.5), lpIn = bq('lowpass', 20000, 0.6);
    const body = bq('peaking', 120, 0.9, 0), listen = g(0), master = g(0);
    const pan = ctx.createStereoPanner ? ctx.createStereoPanner() : null;
    const comp = ctx.createDynamicsCompressor();
    comp.threshold.value = -10; comp.knee.value = 6; comp.ratio.value = 10; comp.attack.value = 0.003; comp.release.value = 0.25;
    const clip = ctx.createWaveShaper(), curve = new Float32Array(1025);
    for (let i = 0; i < curve.length; i++) {         // linear to 0.6, then a tanh knee to <= 0.9
      const x = 2 * i / (curve.length - 1) - 1, a = Math.abs(x);
      curve[i] = Math.sign(x) * (a < 0.6 ? a : 0.6 + 0.3 * Math.tanh((a - 0.6) / 0.3));
    }
    clip.curve = curve;
    const out = g(0.7);
    chain(bus, dc, lpDist, lpIn, body, listen);
    if (pan) chain(listen, pan, master); else listen.connect(master);
    chain(master, comp, out, clip, dest);
    Object.assign(P, { gain: listen.gain, lpDist: lpDist.frequency, lpIn: lpIn.frequency, body: body.gain, master: master.gain });
    if (pan) P.pan = pan.pan;

    // noise: two decorrelated loops (odd lengths) and a slow random signal (the second loop played 400x slower,
    // low-passed at 1.6 Hz: ~0.1 rms) for gusts and pitch flutter
    const sr = ctx.sampleRate;
    const nA = noiseBuffer(ctx, 2.71, 0x9e3779b9), nB = noiseBuffer(ctx, 3.23, 0x85ebca6b);
    const noiseA = loop(nA), noiseB = loop(nB), slow = loop(nB, 1 / 400);
    const slowLP = bq('lowpass', 1.6, 0.5);
    slow.connect(slowLP);

    // the frequency drivers: blade-passing frequency and Ng shaft frequency (one automation each, all partials locked)
    const blade = constSource(ctx, sources), gas = constSource(ctx, sources);
    P.bladeHz = blade.offset; P.ngHz = gas.offset;
    const drive = (src, k, param) => { if (k === 1) src.node.connect(param); else { const m = g(k); src.node.connect(m); m.connect(param); } };

    // propeller: pulse tone (harmonics low-passed by tip Mach) + fundamental, wobbling at 1/rev and with the gusts
    const pw = harmonicWave(ctx, 40, (n) => Math.pow(n, -0.7)), soft = harmonicWave(ctx, 6, (n) => Math.pow(0.55, n - 1));
    this.waves = { prop: pw.rms, soft: soft.rms, softMin: soft.min };
    const propO = osc(null, pw.wave), fundO = osc('sine'), amO = osc(null, soft.wave), shaftO = osc('sine');
    drive(blade, 1, propO.frequency); drive(blade, 1, fundO.frequency); drive(blade, 1, amO.frequency);
    drive(blade, 1 / BLADES, shaftO.frequency);
    const propLP = bq('lowpass', 200, 0.6), propG = g(0), fundG = g(0), wob = g(1), shaftD = g(0), wobD = g(0);
    chain(propO, propLP, propG, wob); chain(fundO, fundG, wob); wob.connect(bus);
    chain(shaftO, shaftD, wob.gain); chain(slowLP, wobD, wob.gain);
    Object.assign(P, { prop: propG.gain, fund: fundG.gain, propLP: propLP.frequency, shaftDepth: shaftD.gain, wobDepth: wobD.gain });
    // blade swish: broadband, amplitude-modulated by a soft pulse per blade passage (gain = base + pulse)
    const swBP = bq('bandpass', 600, 0.8), swAM = g(0.5), swG = g(0);
    chain(noiseA, swBP, swAM, swG, wob);
    amO.connect(swAM.gain);
    Object.assign(P, { swish: swG.gain, swishF: swBP.frequency, amBase: swAM.gain });
    // reverse / beta growl: low broadband roar, rough (blade passage + 1/rev)
    const grBP = bq('bandpass', 220, 0.6), grAM = g(0.6), grG = g(0), grD = g(0.8), grS = g(0.35);
    chain(noiseB, grBP, grAM, grG, wob);
    chain(amO, grD, grAM.gain); chain(shaftO, grS, grAM.gain);
    Object.assign(P, { growl: grG.gain, growlF: grBP.frequency });

    // gas generator: compressor whine (+ 2nd harmonic, a few cents of flutter), hum, starter whirr, inlet hiss
    const w1 = osc('sine'), w2 = osc('sine'), hum = osc('triangle'), st = osc('sawtooth');
    drive(gas, WHINE_ORDER, w1.frequency); drive(gas, 2 * WHINE_ORDER, w2.frequency); drive(gas, 2, hum.frequency);
    drive(gas, STARTER_ORDER, st.frequency);
    const jit = g(40);                                 // ~4 cents rms
    slowLP.connect(jit); jit.connect(w1.detune); jit.connect(w2.detune);
    const w1G = g(0), w2G = g(0), humG = g(0), stLP = bq('lowpass', 900, 0.7), stG = g(0);
    chain(w1, w1G, bus); chain(w2, w2G, bus); chain(hum, humG, bus); chain(st, stLP, stG, bus);
    const hiHP = bq('highpass', 3000, 0.6), hiG = g(0);
    chain(noiseA, hiHP, hiG, bus);
    Object.assign(P, { whine1: w1G.gain, whine2: w2G.gain, hum: humG.gain, starter: stG.gain, hiss: hiG.gain, hissF: hiHP.frequency });
    // combustion / exhaust roar, the light-off 'whoomp', the igniters
    const roLP = bq('lowpass', 500, 0.5), roG = g(0), whLP = bq('lowpass', 140, 0.9), whG = g(0);
    chain(noiseB, roLP, roG, bus); chain(noiseA, whLP, whG, bus);
    const tk = loop(tickBuffer(ctx)), tkG = g(0);
    chain(tk, tkG, bus);
    Object.assign(P, { roar: roG.gain, roarF: roLP.frequency, whoomp: whG.gain, tick: tkG.gain });

    this.sr = sr;
    this.last = {};
    this.target = {};
    const t0 = ctx.currentTime;
    noiseB.start(t0, 1.1);                            // decorrelated from the slow copy of the same buffer
    for (const s of sources) if (s !== noiseB) s.start(t0);
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
    const sr = this.sr, lim = 0.45 * sr, T = SOUND.tau, TL = SOUND.tauL;
    const put = (k, v, tau = T) => this._put(k, v, when, tau);
    put('bladeHz', p.bladeHz); put('ngHz', p.ngHz);
    put('prop', p.prop / this.waves.prop); put('fund', p.fund * SQRT2); put('propLP', Math.min(p.propLP, lim));
    put('shaftDepth', p.shaftDepth); put('wobDepth', p.wobDepth);
    put('swishF', p.swishF); put('swish', p.swish * bandGain(1.57 * p.swishF / 0.8, sr)); put('amBase', Math.max(p.amBase, -this.waves.softMin));
    put('growlF', p.growlF); put('growl', p.growl * bandGain(1.57 * p.growlF / 0.6, sr));
    put('whine1', p.whine1 * SQRT2); put('whine2', p.whine2 * SQRT2); put('hum', p.hum * SQRT3); put('starter', p.starter * SQRT3 * 1.6);
    put('hissF', p.hissF); put('hiss', p.hiss * bandGain(sr / 2 - p.hissF, sr));
    put('roarF', p.roarF); put('roar', p.roar * bandGain(1.1 * p.roarF, sr));
    put('whoomp', p.whoomp * bandGain(1.1 * 140, sr)); put('tick', p.tick);
    put('gain', p.gain, TL); put('lpDist', Math.min(p.lpDist, lim), TL); put('lpIn', Math.min(p.lpIn, lim), TL);
    put('body', p.body, TL); put('pan', p.pan, TL);
  }

  setMaster(v, when) { this._put('master', v, when, SOUND.tauM); }

  // current AudioParam values (tests)
  values() {
    const o = {};
    for (const k of ['bladeHz', 'ngHz', 'master', 'gain', 'lpIn', 'lpDist', 'prop', 'whine1', 'roar', 'growl', 'pan']) if (this.p[k]) o[k] = this.p[k].value;
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
    // the first gesture creates the context (while sound is on); a gesture also resumes it when there is something
    // to hear -- the bubbling listener runs after the button's own handler, so a click on Idle counts
    const opts = { capture: true, passive: true };
    const first = (e) => {
      if (!e.isTrusted) return;
      this.gesture = true;
      if (this.on && this.supported && !this.ctx) this._create();
      this._resumeIn(false);
    };
    const after = (e) => { if (e.isTrusted) this._resumeIn(true); };
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
    this.ctx.onstatechange = () => { this.busy = false; if (this.ctx.state === 'running') this.unlocked = true; };
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
      if (!this.ctx && this.gesture) this._create();
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
      supported: this.supported, on: this.on, volume: this.vol, gesture: this.gesture, created: this.created,
      ctx: ctx ? ctx.state : null, time: ctx ? ctx.currentTime : 0, graph: !!this.voice, active: this.active,
      unlocked: this.unlocked, engine: { rpm: c.rpm, pitch: c.pitch, ...this.kin.gg.state },
      targets: this.params ? { ...this.params } : null, values: this.voice ? this.voice.values() : null,
      set: this.voice ? { ...this.voice.target } : null, listener: this.geo ? { ...this.geo } : null,
      chip: this.ui.chip ? !this.ui.chip.hidden : null,
    };
  }
}

// ------------------------------------------------------------------ offline render (tests)
// Steps the viewer's Kinematics (kin) through script [{t, set: setProp argument}] in 1/rate s steps and renders the
// same EngineVoice / engineParams on an OfflineAudioContext; returns the AudioBuffer and a log of the state.
export async function renderOffline({ kin, script, duration = 47, sampleRate = 44100, listener = LISTEN_REF,
  volume = SOUND.volume, rate = 60 }) {
  const OAC = window.OfflineAudioContext || window.webkitOfflineAudioContext;
  const ctx = new OAC(2, Math.ceil(duration * sampleRate), sampleRate);
  const voice = new EngineVoice(ctx, ctx.destination);
  const L = listenerParams(listener);
  voice.setMaster(SOUND.level * volume * volume, 0);
  const dt = 1 / rate, log = [];
  let k = 0;
  for (let i = 0; i * dt < duration; i++) {
    const t = i * dt;
    while (k < script.length && script[k].t <= t + 1e-9) kin.setProp(script[k++].set);
    if (i > 0) kin.update(dt);
    const e = { rpm: kin.c.rpm, pitch: kin.c.pitch, ...kin.gg.state };
    const p = engineParams(e, L);
    voice.set(p, t);
    if (i % 3 === 0) {
      log.push({ t, rpm: e.rpm, pitch: e.pitch, ng: e.ng, phase: e.phase, comb: e.comb, light: e.light, starter: e.starter,
        bladeHz: p.bladeHz, whineHz: p.whineHz, prop: p.prop, swish: p.swish, whine1: p.whine1, roar: p.roar, growl: p.growl });
    }
  }
  const buffer = await ctx.startRendering();
  return { buffer, log };
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

// the offline render as a base64 WAV plus its peak and the state log (test hook)
export async function renderOfflineWav(opts) {
  const { buffer, log } = await renderOffline(opts);
  let peak = 0;
  for (let c = 0; c < buffer.numberOfChannels; c++) {
    const d = buffer.getChannelData(c);
    for (let i = 0; i < d.length; i++) { const a = Math.abs(d[i]); if (a > peak) peak = a; }
  }
  const u8 = encodeWav(buffer);
  let s = '';
  for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000));
  return { wav: btoa(s), log, sampleRate: buffer.sampleRate, channels: buffer.numberOfChannels, seconds: buffer.duration, peak };
}
