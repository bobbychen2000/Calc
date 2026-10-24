#!/usr/bin/env node
// The live avionics' engine / atmosphere model (web/viewer/engine.js, env.js) against the POH NGX / TCDS figures and the
// fix r1 timings: node test/avx_model_test.mjs  (exit 0 = all pass; pure JS, no browser)
import { Engine, driveEngine, LIMITS, ratingShp, npIdle, ngIdleFor, START, FEATHER_SEL, PSI_SHP } from '../web/viewer/engine.js';
import { isa, airData, ENV_DEFAULTS, fuelMaxLb, Environment, altOf } from '../web/viewer/env.js';

let fails = 0, n = 0;
function check(name, ok, detail = '') {
  n++;
  if (!ok) fails++;
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  -- ' + detail : ''}`);
}
const atmOf = (o = {}) => {
  const e = { ...ENV_DEFAULTS, ...o };
  const a = isa({ oat: e.oat, elev: e.elev, qnh: e.qnh });
  a.air = airData(e, a);
  return a;
};
// a stand-in for Kinematics: the commanded / current propeller, the blade pitch slewed at 35 deg/s as the viewer does
function rig(atm, { rpm = 0, pitch = 62, run = false } = {}) {
  const eng = new Engine(atm, { fuelLb: 2170 });
  const k = { t: { rpm, pitch }, c: { rpm: run ? rpm : 0, pitch }, unfeather: false, eng, time: 0 };
  if (run) eng.snap(rpm, rpm, pitch);
  k.step = (sec, hz = 60, each = null) => {
    const m = Math.round(sec * hz);
    for (let i = 0; i < m; i++) {
      const d = 35 / hz;
      k.c.pitch += Math.max(-d, Math.min(d, k.t.pitch - k.c.pitch));
      driveEngine(k, 1 / hz);
      k.time += 1 / hz;
      if (each) each(k);
    }
  };
  return k;
}

// ---------------------------------------------------------------- atmosphere
{
  const a = isa({ oat: 15, elev: 0, qnh: 1013.25 });
  check('ISA sea level: delta = theta = sigma = 1, rho 1.225', Math.abs(a.delta - 1) < 1e-9 && Math.abs(a.theta - 1) < 1e-9 && Math.abs(a.rho - 1.225) < 1e-6);
  const b = isa({ oat: 22, elev: 1370, qnh: 1013 });
  check('the altimeter set to QNH reads the field elevation (to the foot)', Math.abs(b.indAlt - 1370) < 1, `${b.indAlt.toFixed(2)} ft`);
  check('pressure altitude at 1013 hPa = elevation + 0.25 hPa x ~27 ft', Math.abs(b.pa - 1377) < 3, `${b.pa.toFixed(1)} ft`);
  const c = isa({ oat: 45, elev: 6000, qnh: 1013.25 });
  check('density altitude hot and high (45 C, 6,000 ft) ~10,500 ft', c.da > 9800 && c.da < 11200, `${c.da.toFixed(0)} ft`);
  check('ISA deviation: 22 C at 1,377 ft = ISA +10', Math.abs(b.isaDev - 9.7) < 0.3, `${b.isaDev.toFixed(2)}`);
  check('the altitude law inverts (1 - p^(1/n)) / k', Math.abs(altOf(Math.pow(1 - 6.87559e-6 * 5000, 5.25588)) - 5000) < 0.01);
  check('usable fuel 402 US gal = 2,703.6 lb at 15 C (POH)', Math.abs(fuelMaxLb(15) - 2703.45) < 0.5, `${fuelMaxLb(15).toFixed(1)} lb`);
  const w = airData({ windDir: 180, windKt: 20 }, a, 180);
  check('a 20 kt headwind on the nose: IAS 20 kt at sea level', Math.abs(w.ias - 20) < 1e-6 && Math.abs(w.cross) < 1e-6);
  const env = new Environment({ search: '?oat=35&elev=5000&qnh=29.92&wind=270/15&fuel=900', storage: false });
  const v = env.get();
  check('URL knobs: ?oat ?elev ?qnh (inHg) ?wind ?fuel', v.oat === 35 && v.elev === 5000 && Math.abs(v.qnh - 1013.21) < 0.05 && v.windDir === 270 && v.windKt === 15 && v.fuelLb === 900 && v.qnhUnit === 'inHg');
  env.set({ oat: 99, fuelLb: 99999 }, { store: false });
  check('knobs clamped: OAT <= 50 C, fuel <= the tanks at that temperature', env.get().oat === 50 && env.get().fuelLb === Math.floor(fuelMaxLb(50)));
}

// ---------------------------------------------------------------- steady states (POH)
{
  const a = atmOf();
  const idle = rig(a, { rpm: 1000, pitch: 0, run: true }).eng.state;
  check('ground idle: Ng 64.5-66 % (POH 64.5), Np >= 1,000 (350-900 not permitted), torque 2-4 psi',
    idle.ng >= 64.5 && idle.ng <= 66 && idle.np >= 1000 && idle.tq >= 2 && idle.tq <= 4, `Ng ${idle.ng.toFixed(1)}, Np ${idle.np.toFixed(0)}, TQ ${idle.tq.toFixed(1)}`);
  check('ground idle: ITT 550-700 C, fuel flow 120-180 lb/h, oil 90-135 psi green', idle.itt > 550 && idle.itt < 700 && idle.ff > 120 && idle.ff < 180 && idle.oilP >= 90 && idle.oilP <= 135,
    `ITT ${idle.itt.toFixed(0)}, FF ${idle.ff.toFixed(0)}, oil ${idle.oilP.toFixed(0)} psi`);
  const sl = atmOf({ oat: 15, elev: 0, qnh: 1013.25 });
  const r = ratingShp(sl, 1700) / (PSI_SHP * 1700);
  check('take-off rating ISA sea level: flat 44.3 psi (1,200 shp at 1,700 rpm, TCDS)', Math.abs(r - 44.3) < 0.05, `${r.toFixed(2)} psi`);
  const hot = atmOf({ oat: 45, elev: 6000, qnh: 1013.25 });
  const k = rig(hot, { rpm: 1700, pitch: 0, run: true });
  k.t.pitch = k.eng.toPitch(); k.step(15);
  const s = k.eng.state;
  check('T/O hot and high (45 C, 6,000 ft): ITT-limited below 44.3 psi, ITT <= 850 C and amber (> 820)',
    s.rating < 40 && s.tq <= s.rating + 0.3 && s.itt <= 850.5 && s.itt > 820 && s.caution.itt && !s.warning.itt,
    `rating ${s.rating.toFixed(1)}, TQ ${s.tq.toFixed(1)}, ITT ${s.itt.toFixed(0)} (caution ${!!s.caution.itt})`);
  const k2 = rig(atmOf({ oat: 15, elev: 0, qnh: 1013.25 }), { rpm: 1700, pitch: 0, run: true });
  k2.t.pitch = k2.eng.toPitch(); k2.step(15);
  const s2 = k2.eng.state;
  check('T/O ISA sea level: 44.3 psi at 1,700 rpm, Ng 95-104 %, ITT < 820 (green)', Math.abs(s2.tq - 44.3) < 0.4 && s2.ng > 95 && s2.ng < 104 && s2.itt < 820 && !s2.caution.itt,
    `TQ ${s2.tq.toFixed(1)}, Ng ${s2.ng.toFixed(1)}, ITT ${s2.itt.toFixed(0)}`);
  check('npIdle / ngIdleFor: a cold dense day raises ground idle only through the 1,000 rpm floor', npIdle(atmOf({ oat: -30 })) >= 1000 && ngIdleFor(atmOf({ oat: -30 })) >= 64.5);
}

// ---------------------------------------------------------------- the start (fix r1: 20-40 s, not 11.5)
{
  const k = rig(atmOf(), { rpm: 1000, pitch: 62 });
  k.unfeather = true;
  let lit = -1, fuel = -1, idle = -1, preMax = 0, peak = 0, tqMax = 0, ngAtLight = 0, np2 = -1;
  k.step(60, 60, (q) => {
    const e = q.eng;
    if (fuel < 0 && e.fuelT >= 0) fuel = q.time;
    if (lit < 0 && e.lit) { lit = q.time; ngAtLight = e.ng; }
    if (lit < 0) preMax = Math.max(preMax, q.c.rpm);
    if (lit >= 0 && np2 < 0 && q.time >= lit + 5) np2 = q.c.rpm;
    if (idle < 0 && e.phase === 'run') idle = q.time;
    peak = Math.max(peak, e.itt); tqMax = Math.max(tqMax, e.tq);
  });
  check('start: fuel at 13 % Ng 3-7 s after the starter, light-off 1.5-4 s later at 15-19 % Ng',
    fuel >= 3 && fuel <= 7 && lit - fuel >= 1.5 && lit - fuel <= 4 && ngAtLight >= 15 && ngAtLight <= 19,
    `fuel ${fuel.toFixed(1)} s, light-off ${lit.toFixed(1)} s at ${ngAtLight.toFixed(1)} %`);
  check('start: stabilised ground idle 20-40 s after the starter (a PT6 start)', idle >= 20 && idle <= 40, `${idle.toFixed(1)} s`);
  check('start: ITT peak 600-870 C (EPECS cap, abort at 945), torque <= 6 psi', peak >= 600 && peak <= 870 && tqMax <= 6, `peak ${peak.toFixed(0)} C, TQ max ${tqMax.toFixed(1)}`);
  check('start: the propeller still until the light-off (<= 5 rpm), turning 5 s after it, unfeathered, ~1,000 rpm at idle',
    preMax <= 5 && np2 > 30 && k.t.pitch === 0 && k.c.rpm >= 990, `pre ${preMax.toFixed(1)} rpm, +5 s ${np2.toFixed(0)} rpm, now ${k.c.rpm.toFixed(0)} rpm`);
  check('start: starter and igniters off at ground idle, generators on line', !k.eng.starter && !k.eng.ign && k.eng.gen);
  // frame-rate independence (the fixed sub-step)
  const tr = [30, 60, 144].map((hz) => { const q = rig(atmOf(), { rpm: 1000, pitch: 0 }); q.step(20, hz); return [q.eng.ng, q.c.rpm, q.eng.itt]; });
  check('the same start at 30 / 60 / 144 Hz frames (Ng, Np, ITT within 0.5 %)', tr.every((x) => x.every((v, i) => Math.abs(v - tr[1][i]) <= 0.005 * Math.max(1, Math.abs(tr[1][i])))),
    tr.map((x) => x.map((v) => v.toFixed(1)).join('/')).join('  '));
}

// ---------------------------------------------------------------- feather with the engine running, limited, reverse
{
  const k = rig(atmOf(), { rpm: 1700, pitch: 0, run: true });
  const tq0 = k.eng.state.tq;
  let tqMax = 0;
  k.t.pitch = 62;
  k.step(12, 60, (q) => { tqMax = Math.max(tqMax, q.eng.state.tq); });
  const s = k.eng.state;
  check(`feather selected at 1,700 rpm (pitch >= ${FEATHER_SEL}): no torque spike (<= the governed torque + 2 psi), Ng to ground idle`,
    tqMax <= tq0 + 2 && Math.abs(s.ng - ngIdleFor(k.eng.atm)) < 1, `TQ ${tq0.toFixed(1)} -> max ${tqMax.toFixed(1)}, Ng ${s.ng.toFixed(1)}`);
  check('feather selected: the propeller leaves 1,700 and settles at the feathered-idle 450-750 rpm, 3-8 psi',
    s.np >= 450 && s.np <= 750 && s.tq >= 3 && s.tq <= 8, `Np ${s.np.toFixed(0)}, TQ ${s.tq.toFixed(1)}`);
  k.t.pitch = 0; k.step(20);
  check('unfeathered again: back to the governed 1,700 rpm', Math.abs(k.c.rpm - 1700) < 1 && !k.eng.ungov, `${k.c.rpm.toFixed(0)} rpm`);
  const L = rig(atmOf(), { rpm: 1700, pitch: 0, run: true });
  let tqL = 0;
  L.t.pitch = 40; L.step(10, 60, (q) => { tqL = Math.max(tqL, q.eng.state.tq); });
  check('a blade pitch the rating cannot turn at 1,700: the propeller droops, the torque <= the red line (44.84)',
    L.c.rpm < 1650 && tqL <= LIMITS.tq.red && L.eng.state.tq > 38, `Np ${L.c.rpm.toFixed(0)}, TQ ${L.eng.state.tq.toFixed(1)} (max ${tqL.toFixed(1)})`);
  const R = rig(atmOf(), { rpm: 1700, pitch: 0, run: true });
  let caut = 0;
  R.t.pitch = -38; R.step(8, 60, (q) => { if (q.eng.caution.np) caut++; });
  const sr = R.eng.state;
  check('reverse: Np governed at 1,615 (POH), torque 15-35 psi, no Np caution on the way in', Math.abs(sr.np - 1615) < 2 && sr.tq > 15 && sr.tq < 35 && caut === 0,
    `Np ${sr.np.toFixed(0)}, TQ ${sr.tq.toFixed(1)}, caution frames ${caut}`);
}

// ---------------------------------------------------------------- transients (pilot judge r2): the torque WITH Ng
{
  const k = rig(atmOf({ oat: 15, elev: 0, qnh: 1013.25 }), { rpm: 1000, pitch: 0, run: true });
  k.t.rpm = 1700; k.step(8);
  const q0 = k.eng.state.tq;
  k.t.pitch = k.eng.toPitch();
  let t10 = -1, t90 = -1, lead = 0;
  const q1 = 44.3;
  k.step(15, 60, (q) => {
    const s = q.eng.state, tt = q.time - 8;
    if (t10 < 0 && s.tq >= q0 + 0.1 * (q1 - q0)) t10 = tt;
    if (t90 < 0 && s.tq >= q0 + 0.9 * (q1 - q0)) t90 = tt;
    // the torque the gas generator's Ng can make at that moment (the power map) -- never exceeded
    const a = q.eng.atm, sq = Math.sqrt(a.theta);
    const gas = a.delta * sq * 1200 * Math.pow(Math.max(0, (s.ng / sq - 55.75) / 42.25), 2) / (PSI_SHP * s.np);
    lead = Math.max(lead, s.tq - gas);
  });
  check('T/O from 1,700 fine: the torque rises with Ng (10 -> 90 % in 2-7 s), never ahead of the power Ng makes (<= +0.5 psi)',
    t90 - t10 >= 2 && t90 - t10 <= 7 && lead <= 0.5, `10 % at ${t10.toFixed(2)} s, 90 % at ${t90.toFixed(2)} s, lead ${lead.toFixed(2)} psi`);
  const u = rig(atmOf(), { rpm: 1000, pitch: 0, run: true });
  u.t.pitch = 62; u.step(12);
  u.t.pitch = 0;
  let ngMax = 0, tqMax = 0;
  u.step(20, 60, (q) => { ngMax = Math.max(ngMax, q.eng.ng); tqMax = Math.max(tqMax, q.eng.state.tq); });
  check('unfeathered at ground idle: no run-up (Ng <= 68 %, torque <= 8 psi), back to 1,000 rpm', ngMax <= 68 && tqMax <= 8 && Math.abs(u.c.rpm - 1000) < 1,
    `Ng max ${ngMax.toFixed(1)}, TQ max ${tqMax.toFixed(1)}, Np ${u.c.rpm.toFixed(0)}`);
  const d = rig(atmOf(), { rpm: 1000, pitch: 0, run: true });
  d.t.rpm = 0; d.t.pitch = 62;
  const itt = [];
  d.step(10, 60, (q) => itt.push(q.eng.itt));
  check('after the fuel cut-off the ITT falls with the hot section: 3 s 350-550 C, 10 s 250-500 C', itt[179] >= 350 && itt[179] <= 550 && itt[599] >= 250 && itt[599] <= 500,
    `${itt[179].toFixed(0)} / ${itt[599].toFixed(0)} C`);
}

// ---------------------------------------------------------------- shutdown, cautions
{
  const k = rig(atmOf(), { rpm: 1000, pitch: 0, run: true });
  k.t.rpm = 0; k.t.pitch = 62;
  let ng1 = -1, np0 = -1;
  k.step(60, 60, (q) => { if (ng1 < 0 && q.eng.ng < 1) ng1 = q.time; if (np0 < 0 && q.c.rpm < 1) np0 = q.time; });
  check('shutdown from ground idle: the propeller stopped in 12-30 s, Ng below 1 % in 25-45 s', np0 >= 12 && np0 <= 30 && ng1 >= 25 && ng1 <= 45,
    `propeller ${np0.toFixed(1)} s, Ng ${ng1.toFixed(1)} s`);
  const f = rig(atmOf(), { rpm: 1000, pitch: 0, run: true });
  f.eng.setEnv(f.eng.atm, { fuelLb: 250 });
  check('fuel low: under 134 lb a side (POH) -> low', f.eng.state.fuel.low && !rig(atmOf(), { rpm: 1000, pitch: 0, run: true }).eng.state.fuel.low);
  const off = rig(atmOf()).eng.state;
  check('engine off: no cautions / warnings (P1046410: oil 0 psi stays green)', !Object.keys(off.caution).length && !Object.keys(off.warning).length);
  check('START table: fuelAt 13 % (POH), acceleration <= 6.5 %/s', START.fuelAt === 13 && START.max <= 6.5);
}

console.log(`\n${n - fails}/${n} passed${fails ? `, ${fails} FAILED` : ''}`);
process.exit(fails ? 1 : 0);
