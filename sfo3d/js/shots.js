// Director: hero aircraft choreography, camera moves, overlays
import { v3, clamp, smooth, smoother, easeInOut, lerp, catmull, rng } from './math.js';
import { stToWorld, GROUND_Y, TERMINAL_CENTER } from './geo.js';
import { Aircraft, liveryFor, LIVERIES } from './aircraft/fleet.js';
import { llToWorld } from './geo.js';
import { landingState, takeoffState, runwayFrame, TaxiPath, taxiDistance } from './anim/traffic.js';
import { stDir } from './scene.js';
import { TYPES } from './aircraft/model.js';
import { PIERS } from './geo.js';
import { pierFrame } from './world/airfield.js';

const P = (s, t, h) => stToWorld(s, t, GROUND_Y + h);
const D2R = Math.PI / 180;
// smooth camera noise (handheld)
function shake(t, amp, seed = 0) { const n = (f, p) => Math.sin(t * f + p) * 0.6 + Math.sin(t * f * 2.3 + p * 1.7) * 0.3 + Math.sin(t * f * 5.1 + p * 0.3) * 0.1; return [n(0.9, seed) * amp, n(1.1, seed + 2) * amp, n(0.7, seed + 4) * amp]; }
function applyState(ac, s) { ac.pos = s.pos; ac.fwd = s.fwd; ac.pitch = s.pitch; ac.roll = s.roll; ac.gear = s.gear; ac.flaps = s.flaps; ac.spoilers = s.spoilers; Object.assign(ac.lightsOn, s.lights); }

export function setupDirector(scene, world, env, live) {
  const R = rng(2026);
  const hero = {};
  // liveries: pick from live data if present (by airline color family), else defaults
  const Tsnap = 7.0; // video time corresponding to the live snapshot
  const A28R = live && live.arrivals['28R'] ? live.arrivals['28R'] : [], A28L = live && live.arrivals['28L'] ? live.arrivals['28L'] : [];
  const dep = live ? live.departures : [];
  const pickDep = (pred) => dep.find(pred);
  const mk = (type, liv, id, lod, src) => { const ac = scene.add(new Aircraft(type, src ? liveryFor(src.a ? src.a.flight : src.flight, LIVERIES[liv % LIVERIES.length]) : liv, { lod, id, dirt: 0.35 })); if (src) ac.label = src.label; return ac; };
  const h1src = A28R[0], h2src = A28L[0];
  const h3src = pickDep(d => d.track > 250 && d.track < 330), h5src = pickDep(d => d.track < 120);
  hero.h1 = mk(h1src ? h1src.type.key : 'b77w', 0, 'H1', 1, h1src);   // 28R arrival
  hero.h2 = mk(h2src ? h2src.type.key : 'b38m', 2, 'H2x', 1, h2src);  // 28L arrival
  hero.h3 = mk(h3src ? h3src.type.key : 'b789', 3, 'H3xx', 1, h3src); // west departure 28L
  const t4src = live ? live.taxiing.find(a => a.flight && /ASA|SWA|UAL/.test(a.flight) && ['B737', 'B738', 'B739', 'A319', 'A320', 'B38M', 'B39M'].includes(a.icao)) : null;
  hero.h4 = mk(t4src ? (TYPES[t4src.icao.toLowerCase()] ? t4src.icao.toLowerCase() : 'b738') : 'a21n', 1, 'H4xxx', 1, t4src ? { a: t4src, label: [t4src.flight, t4src.icao, t4src.reg].join(' · '), flight: t4src.flight } : null);
  if (t4src) hero.h4.label = hero.h4.label.replace('B737', 'Boeing 737-700').replace('B738', 'Boeing 737-800').replace('B739', 'Boeing 737-900ER');
  hero.h5 = mk(h5src ? h5src.type.key : 'b738', 5, 'H5', 1, h5src);  // 1R departure (finale)
  // extra live arrivals + airborne traffic (extrapolated from the snapshot)
  hero.extraArr = [];
  for (const [end, list] of [['28R', A28R.slice(1)], ['28L', A28L.slice(1)]]) for (const p of list) { const ac = mk(p.type.key, 4, 'X' + p.a.hex, 0, p); hero.extraArr.push({ ac, end, x: p.x, V: p.a.gsKt * 0.5144 }); }
  hero.air = [];
  if (live) for (const a of live.other) {
    if ([h1src, h2src, h3src, h5src].some(s => s && s.a.hex === a.hex) || hero.extraArr.some(e => e.ac.id === 'X' + a.hex)) continue;
    if (!a.track || a.altFt > 12000) continue;
    const t = inferTypeKey(a); const ac = mk(t, 6, 'A' + a.hex, 0, { a, label: a.flight, flight: a.flight });
    hero.air.push({ ac, p0: llToWorld(a.lat, a.lon, a.altFt * 0.3048), v: [Math.sin(a.track * D2R) * a.gsKt * 0.5144, (a.vsFpm || 0) * 0.00508, -Math.cos(a.track * D2R) * a.gsKt * 0.5144] });
  }
  // ambient taxi traffic (live taxiing aircraft on plausible routes, at their reported speeds)
  const taxiSrc = live ? live.taxiing.filter(a => a !== t4src) : [{ icao: 'A388' }, { icao: 'B748' }, { icao: 'E75L' }];
  hero.taxi = taxiSrc.slice(0, 6).map((a, i) => ({ ac: mk(ICAO_TO_KEY(a.icao), 7 + i, 'Tx' + i, 0, a.flight ? { a, label: a.flight, flight: a.flight } : null), speed: Math.max(4, (a.gsKt || 12) * 0.5144), route: i % 3, d0: 120 + i * 260 }));
  function inferTypeKey(a) { return ICAO_TO_KEY(a.icao) || 'b738'; }
  function ICAO_TO_KEY(icao) { const M = { B39M: 'b39m', B38M: 'b38m', B738: 'b738', B739: 'b739', B737: 'b737', B789: 'b789', B772: 'b772', B77W: 'b77w', B753: 'b753', B752: 'b752', A319: 'a319', A320: 'a320', A321: 'a321', A21N: 'a21n', E75L: 'e75l', CRJ2: 'crj2', BCS3: 'bcs3', A388: 'a388', B748: 'b748', A359: 'a359', B763: 'b763' }; return M[icao] || 'b738'; }
  // times derived from live positions
  const Vh1 = h1src ? h1src.a.gsKt * 0.5144 : 76, Vh2 = h2src ? h2src.a.gsKt * 0.5144 : 70;
  const tdH1 = h1src ? Tsnap + (430 - h1src.x) / Vh1 : 22.0;
  const tdH2 = h2src ? Tsnap + (430 - h2src.x) / Vh2 : 26.5;
  // hero gate: choose a narrowbody gate on pier E/D whose lead-in approach is clear, emptied for the arrival
  const cands = world.gates.filter(g => !g.wide && g.pier === 'E');
  const pierE = PIERS.find(p => p.name === 'E'); const fE = pierFrame(pierE);
  const alongE = (g) => (g.attach[0] - pierE.root[0]) * fE.d[0] + (g.attach[1] - pierE.root[1]) * fE.d[1];
  // prefer a side gate near the tip on the sun-facing side
  const sunST = [env.sunDir[0], -env.sunDir[2]];
  const scored = cands.filter(g => alongE(g) < pierE.len - 30).map(g => ({ g, sc: alongE(g) + 60 * (g.outN[0] * 0 + 1) }));
  scored.sort((a, b) => b.sc - a.sc);
  const gate = (scored[0] && scored[0].g) || world.gates[0];
  if (gate.aircraft) { scene.aircraft = scene.aircraft.filter(a => a !== gate.aircraft); gate.aircraft = null; }
  gate.dynamic = true; gate.acType = hero.h4.type;
  scene.gateSys.buildStatic();
  hero.gate = gate;
  // taxi-in path: from the open apron beyond the pier tip, curve onto lead-in line to stop
  const T4 = TYPES[hero.h4.type]; const stop = [gate.nose[0] - gate.dir[0] * T4.xMain, gate.nose[1] - gate.dir[1] * T4.xMain];
  const leadStart = [stop[0] - gate.dir[0] * 70, stop[1] - gate.dir[1] * 70];
  const side = fE.d; // toward pier tip = open apron
  const entry = [leadStart[0] + side[0] * 160 - gate.dir[0] * 10, leadStart[1] + side[1] * 160 - gate.dir[1] * 10];
  const taxiPath = new TaxiPath([entry, leadStart, stop], 55);
  hero.taxiPath = taxiPath;
  const TV = 6.0, TD = 0.9; // taxi speed, braking decel
  // ambient taxi path along PS taxiway
  hero.ambPath = new TaxiPath([[900, -140], [-150, -140], [-171, -300], [-171, -1300]], 60);
  hero.ambPath2 = new TaxiPath([[-1700, 385], [-400, 385], [600, 385], [1500, 385]], 60);
  hero.ambPath3 = new TaxiPath([[-171, -1300], [-171, -400], [-171, 600], [-171, 1100]], 60);

  const F28R = runwayFrame('28R'), F28L = runwayFrame('28L'), F1R = runwayFrame('1R'), F1L = runwayFrame('1L');
  const sunDir = env.sunDir; const sunH = v3.norm([sunDir[0], 0, sunDir[2]]);
  const along = (F, x, off = 0, h = 0) => v3.add(v3.add(F.thr, v3.mul(F.dir, x)), v3.add(v3.mul(F.right, off), [0, h, 0]));

  // helper: set all heroes for a global time T (seconds, video timeline)
  const timeline = {
    tdH1,  // global time of H1 touchdown (from live position)
    tdH2,
    rotH3: 28.0, // H3 rotation time
    taxiH4: 0, // computed below from path length so H4 stops at T=40.5
    rotH5: 63.0,
  };
  const H1OPT = { vapp: Vh1, pitchApp: 2.6, pitchTD: 5.5, phase: 1 }, H2OPT = { vapp: Vh2, pitchApp: 2.6, pitchTD: 5.5, phase: 2.5 };
  const H3OPT = { vr: 82, accel: 1.75, pitchMax: 14, x0: 60 };
  timeline.taxiH4 = 40.5 - ((taxiPath.length - TV * TV / (2 * TD)) / TV + TV / TD);
  hero.update = (T) => {
    applyState(hero.h1, landingState('28R', T - timeline.tdH1, H1OPT));
    applyState(hero.h2, landingState('28L', T - timeline.tdH2, H2OPT));
    applyState(hero.h3, takeoffState('28L', T - timeline.rotH3, H3OPT));
    for (const e of hero.extraArr) applyState(e.ac, landingState(e.end, T - (Tsnap + (430 - e.x) / e.V), { vapp: e.V, phase: 3 }));
    for (const q of hero.air) { const dt = T - Tsnap; q.ac.pos = [q.p0[0] + q.v[0] * dt, q.p0[1] + q.v[1] * dt, q.p0[2] + q.v[2] * dt]; q.ac.fwd = v3.norm([q.v[0], 0, q.v[2]]); q.ac.pitch = Math.atan2(q.v[1], Math.hypot(q.v[0], q.v[2])) + 0.04; q.ac.gear = q.p0[1] < 600 ? 1 : 0; q.ac.flaps = q.p0[1] < 900 ? 0.6 : 0; q.ac.lightsOn = { nav: true, beacon: true, strobe: true, landing: q.p0[1] < 3000, taxi: false }; }
    // H4 taxi-in
    {
      const tt = T - timeline.taxiH4; const L = taxiPath.length;
      const { d, v } = tt < 0 ? { d: 0, v: TV } : taxiDistance(tt, L, TV, 0.6, TD);
      const dd = tt < 0 ? tt * TV : d;
      const smp = taxiPath.at(Math.max(0, dd)); let p = smp.p;
      if (dd < 0) p = [p[0] + smp.dir[0] * dd, p[1] + smp.dir[1] * dd];
      const ac = hero.h4; ac.pos = stToWorld(p[0], p[1], GROUND_Y); ac.fwd = stDir(smp.dir); ac.pitch = 0; ac.roll = 0; ac.gear = 1; ac.flaps = 0; ac.spoilers = 0;
      const stopped = tt > 0 && v === 0;
      const tStop = tt - ((L - TV * TV / (2 * TD)) / TV + TV / TD);
      ac.lightsOn = { nav: true, beacon: !(tt > 0 && d >= L - 0.01 && tStop > 1.5), strobe: false, landing: false, taxi: !(d >= L - 0.01) };
      // jet bridge docking after stop
      const kB = d >= L - 0.01 ? smoother((tStop - 2.0) / 7.0) : 0;
      scene.dynBridges = [{ gate, k: Math.max(0, kB) }];
      hero.h4stopT = tStop;
    }
    // H5 departure on 1L (finale) — hidden before its lineup
    { const s = takeoffState('1R', T - timeline.rotH5, { vr: 70, accel: 2.2, pitchMax: 16 }); applyState(hero.h5, s); hero.h5.visible = T > timeline.rotH5 - 40; }
    // H6 ambient taxi
    const amb = (ac, path, d0, v) => { const tt = d0 + T * v; const smp = path.at(((tt % path.length) + path.length) % path.length); ac.pos = stToWorld(smp.p[0], smp.p[1], GROUND_Y); ac.fwd = stDir(smp.dir); ac.lightsOn = { nav: true, beacon: true, taxi: true, strobe: false, landing: false }; };
    const routes = [hero.ambPath, hero.ambPath2, hero.ambPath3];
    for (const q of hero.taxi) amb(q.ac, routes[q.route], q.d0, q.speed);
  };

  // tire smoke on touchdown (deterministic particles)
  const hash = (i, k) => { let x = Math.sin(i * 127.1 + k * 311.7) * 43758.5453; return x - Math.floor(x); };
  const smokeFor = (end, tdT, opts, track) => (T) => {
    const tt = T - tdT; if (tt < 0 || tt > 7) return [];
    const F = runwayFrame(end); const out = [];
    for (let i = 0; i < 70; i++) {
      const ts = (i % 35) * 0.018; if (ts > tt) continue; const side = i < 35 ? 1 : -1;
      const s0 = landingState(end, ts, opts);
      const age = tt - ts;
      const base = v3.add(s0.pos, v3.mul(F.right, side * track / 2));
      const drift = v3.add(v3.mul(F.dir, s0.speed * 0.18 * (1 - Math.exp(-age * 1.5)) / 1.5), v3.add(v3.add(v3.mul(F.right, (hash(i, 1) - 0.5) * 3 * age), [env.wind[0] * age, 0, env.wind[1] * age]), [0, 0.5 + age * (0.6 + hash(i, 2) * 0.5), 0]));
      const p = v3.add(base, drift);
      const s = 0.8 + age * (2.2 + hash(i, 3) * 1.5);
      const a = 0.55 * Math.exp(-age / 1.1) * Math.min(1, age * 8) * (0.6 + 0.4 * hash(i, 4));
      if (a > 0.01) out.push({ p, s, a, seed: hash(i, 5) });
    }
    return out;
  };
  env.wind = env.wind || [1.5, 0, 0];
  scene.smokeFns.push(smokeFor('28R', timeline.tdH1, H1OPT, hero.h1.T.track));
  scene.smokeFns.push(smokeFor('28L', timeline.tdH2, H2OPT, hero.h2.T.track));

  // -------- shots --------
  const shots = [];
  const cam = (pos, target, fovDeg, extra = {}) => ({ pos, target, fov: fovDeg * D2R, near: extra.near ?? 0.5, split: extra.split ?? 3000, far: 160000, shadowSplits: extra.splits || [200, 1000, 4000], roll: extra.roll || 0 });

  const sunSideOf = (F) => v3.dot(F.right, sunH) > 0 ? 1 : -1;
  // Shot 1: establishing — drone below the marine layer following the 28R arrival toward the airport
  shots.push({ name: 'establishing', dur: 9.0, start: 0.0,
    camera: (t) => {
      const T = t; const u = t / 9.0; const sg = sunSideOf(F28R);
      const xH1 = 430 + Vh1 * (T - timeline.tdH1);
      const xc = xH1 - lerp(430, 640, u);
      const pos = v3.add(along(F28R, xc, sg * lerp(230, 170, u), lerp(150, 110, smoother(u))), shake(T, 0.5, 1));
      const tgt = along(F28R, xH1 + lerp(450, 1100, u), sg * 20, lerp(20, 4, u));
      return cam(pos, tgt, lerp(42, 38, u), { near: 2, split: 5000, splits: [700, 2600, 7000] });
    },
    overlay: (t) => ({ kind: 'title', alpha: smooth(1.0, 2.4, t) * (1 - smooth(7.0, 8.6, t)) }) });

  // Shot 2: formation with H1 on short final over the water
  shots.push({ name: 'formation', dur: 7.0, start: 9.0,
    camera: (t) => {
      const T = 9.0 + t; const s = landingState('28R', T - timeline.tdH1, H1OPT);
      const F = F28R; const u = t / 7.0; const sg = sunSideOf(F);
      const Lh = hero.h1.T.L;
      const off = v3.add(v3.add(v3.mul(F.right, sg * lerp(Lh * 1.3, Lh * 1.05, u)), v3.mul(F.dir, lerp(Lh * 0.9, Lh * 0.2, u))), [0, lerp(8, 3, u), 0]);
      const pos = v3.add(v3.add(s.pos, off), shake(T, 0.3, 3));
      const tgt = v3.add(s.pos, v3.add(v3.mul(F.dir, lerp(Lh * 0.2, 0.05 * Lh, u)), [0, hero.h1.T.Hc * 0.8, 0]));
      return cam(pos, tgt, lerp(46, 50, u), { near: 0.5, split: 3000, splits: [160, 900, 4000], roll: 0.03 * Math.sin(t * 0.6) });
    },
    overlay: (t) => ({ kind: 'label', text: hero.h1.label || 'Final approach · Runway 28R', sub: hero.h1.label ? 'Short final · Runway 28R · live ADS-B track' : 'Gear down · flaps 30', alpha: smooth(0.6, 1.5, t) * (1 - smooth(5.8, 6.8, t)) }) });

  // Shot 3: touchdown — telephoto from the infield beside 28R
  shots.push({ name: 'touchdown', dur: 8.0, start: 16.0,
    camera: (t) => {
      const T = 16.0 + t; const s = landingState('28R', T - timeline.tdH1, H1OPT);
      const F = F28R; const sg = sunSideOf(F);
      const pos = v3.add(along(F, 560, sg * 105, 2.0), shake(T, 0.1, 7));
      const tgt = v3.add(s.pos, [0, hero.h1.T.Hc * 0.8, 0]);
      const d = v3.dist(pos, tgt);
      const fov = clamp(2 * Math.atan(hero.h1.T.L * 0.6 / d) / D2R, 5, 40);
      return cam(pos, tgt, fov, { near: 1.0, split: 4000, splits: [Math.max(250, d * 1.5), 1600, 5000] });
    },
    overlay: (t) => ({ kind: 'label', text: 'Touchdown · Runway 28R', sub: hero.h1.label || 'Spoilers deploy · reverse thrust', alpha: smooth(1.0, 2.0, t) * (1 - smooth(6.5, 7.6, t)) }) });

  // Shot 4: westbound departure from 28L — low angle at the rotation point
  shots.push({ name: 'takeoff', dur: 9.0, start: 24.0,
    camera: (t) => {
      const T = 24.0 + t; const s = takeoffState('28L', T - timeline.rotH3, H3OPT);
      const F = runwayFrame('28L'); const sg = sunSideOf(F);
      const xR = H3OPT.x0 + 0.5 * H3OPT.vr * H3OPT.vr / H3OPT.accel;
      const pos = v3.add(v3.add(v3.add(F.start, v3.mul(F.dir, xR + 170)), v3.mul(F.right, sg * 118)), [0, 1.7, 0]);
      const tgt = v3.add(s.pos, v3.add(v3.mul(F.dir, 8), [0, 5, 0]));
      const d = v3.dist(pos, tgt);
      const fov = clamp(2 * Math.atan(hero.h3.T.L * 0.72 / d) / D2R, 8, 55);
      return cam(v3.add(pos, shake(T, 0.08, 11)), tgt, fov, { near: 1.0, split: 4000, splits: [Math.max(300, d * 1.6), 1600, 5000] });
    },
    overlay: (t) => ({ kind: 'label', text: 'Departure · Runway 28L', sub: hero.h3.label || 'Rotate · positive climb · gear up', alpha: smooth(0.8, 1.8, t) * (1 - smooth(7.4, 8.5, t)) }) });

  // Shot 5: taxi-in and park at the gate; jet bridge docks (view from above the pier)
  shots.push({ name: 'gate', dur: 16.0, start: 33.0,
    camera: (t) => {
      const T = 33.0 + t; const g = gate; const u = smoother(t / 16.0);
      const pd = fE.d; const out = g.outN;
      const c0 = [g.attach[0] + pd[0] * 30 - out[0] * 2, g.attach[1] + pd[1] * 30 - out[1] * 2];
      const c1 = [g.attach[0] + pd[0] * 22 + out[0] * 3, g.attach[1] + pd[1] * 22 + out[1] * 3];
      const pp = [lerp(c0[0], c1[0], u), lerp(c0[1], c1[1], u)];
      const pos = P(pp[0], pp[1], lerp(30, 23, u));
      const acp = hero.h4.pos;
      const doorTgt = P(g.nose[0] - g.dir[0] * 6, g.nose[1] - g.dir[1] * 6, 3.5);
      const tgt = v3.lerp(v3.add(acp, v3.add(v3.mul(hero.h4.fwd, 12), [0, 2, 0])), doorTgt, smooth(7, 13, t));
      return cam(v3.add(pos, shake(T, 0.05, 13)), tgt, lerp(50, 42, u), { near: 0.3, split: 2500, splits: [150, 700, 3500] });
    },
    overlay: (t) => ({ kind: 'label', text: 'Arrival at gate ' + (gate.id || ''), sub: hero.h4.label || 'Taxi-in · park · jet bridge docks', alpha: smooth(0.8, 1.8, t) * (1 - smooth(13.5, 15, t)) }) });

  // Shot 6: control tower orbit
  shots.push({ name: 'tower', dur: 8.0, start: 49.0,
    camera: (t) => {
      const a0 = -16 * D2R; const tc = [TERMINAL_CENTER[0] + Math.cos(a0) * 262, TERMINAL_CENTER[1] + Math.sin(a0) * 262];
      const ang = lerp(-0.9, 0.25, t / 8.0);
      const r = 150; const pos = P(tc[0] + Math.cos(ang) * r, tc[1] + Math.sin(ang) * r, 72 - t * 1.5);
      const tgt = P(tc[0], tc[1], 58);
      return cam(pos, tgt, 55, { near: 0.5, split: 3000, splits: [300, 1200, 4000] });
    },
    overlay: (t) => ({ kind: 'label', text: 'SFO Air Traffic Control Tower', sub: '67 m · between Terminals 1 and 2', alpha: smooth(0.8, 1.8, t) * (1 - smooth(6.5, 7.6, t)) }) });

  // Shot 7: finale — rise through the broken marine layer to reveal the airport; departure on 1R
  shots.push({ name: 'finale', dur: 11.0, start: 57.0,
    camera: (t) => {
      const u = easeInOut(t / 11.0);
      const pos = v3.lerp(P(-300, -1900, 150), P(1300, -3300, 820), u);
      const tgt = v3.lerp(P(-500, -500, 0), P(-300, 0, 0), u);
      return cam(pos, tgt, lerp(55, 50, u), { near: 2, split: 6000, splits: [800, 3000, 9000] });
    },
    overlay: (t) => ({ kind: 'end', alpha: smooth(5.5, 7.5, t) }),
    fade: (t) => 1 - smooth(9.8, 11.0, t) });

  return { hero, shots, timeline, totalDur: shots.reduce((s, x) => Math.max(s, x.start + x.dur), 0) };
}
