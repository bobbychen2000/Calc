// The PT6E-67XP / Hartzell HC-E5A-31A as the cockpit sees it: gas-generator speed Ng, propeller speed Np, torque, ITT,
// fuel flow, oil pressure / temperature, the batteries and the fuel quantity -- from engine physics bounded by the POH
// limits, in the atmosphere of the viewer's Environment knobs (env.js).  ONE state model: the engine sound (sound.js)
// reads the same object (Kinematics.gg === Kinematics.eng: ng, phase, lit, comb, light, starter, ign, power, t, startN,
// lightN, lightAge -- the GasGenerator API it was tuned on), the live G3000 PRIME pages (avionics.js) read `state`.
// Pure JS (no three.js): test/avx_model_test.mjs runs it under node.
//
// Tags: [S] sourced (POH NGX 02406, EASA TCDS A.089), [D] derived, [M] measured on a photo, [E] estimate inside [S]
// limits.  Laws (out/tmp/avx/DESIGN.md sec. 1; the prototype's tables reproduced by the node test):
//   propeller   P = Cp(beta) rho n^3 D^5, D 2.67 m; beta at station 42 from the viewer's pitch (fine 0 = 14.7 deg,
//               feather 62 = 80, reverse -38 = -17.5 [S POH 2-4-7]); the static Cp(beta) table [D/E] puts ground idle at
//               ~3 psi (POH 2-4 psi [D]), 1,700 rpm fine pitch at ~9 psi (the stick-pusher test's 5-10 [S])
//   torque      psi = shp / (0.015924 Np)  [D TCDS: 44.34 psi = 1,200 shp at 1,700 rpm]
//   EPECS       the rating = min(flat 44.3 psi, the power at which ITT reaches 850 C, Ng 104 %) [S]; reverse 900 shp
//   gas gen.    corrected map Pc = P / (delta sqrt(theta)) = 1200 ((Nc - 55.75) / 42.25)^2, Nc = Ng / sqrt(theta) [D/E]
//   ITT         ITT_K = theta f(Pc) (+ sub-idle and start-acceleration heat), f fitted to POH Fig 5-3-2-1 (static T/O
//               torque vs OAT and PA at 850 C: rms 0.49 psi) [D]
//   fuel flow   Wf = delta sqrt(theta) (138.3 Nc / 64.5 + 0.325 Pc) + the acceleration's heat [E: idle ~155, T/O ~600]
//   oil         P from the pump (Ng^2) and a viscosity regulator (cold oil to the 160 psi relief [S]); T one thermal node
//               (40 kJ/K) with a thermostatic cooler [E: warm-up ~5 min, idle OAT + 40]
//   electrical  two 24 V 42 Ah lead-acid; the starter from BAT2, BAT1 tied in at 10 % Ng or 10 s; generators on line at
//               ground idle [S]; ground power 28.2 V
//   start       the starter alone to 13 % Ng in ~4.6 s, fuel, light-off 2 s later (~6.6 s, ~17 % [S ~16]), the
//               acceleration 1.4 .. ~3.6 %/s slowed so the start ITT stays <= 870 C (abort predicted at 945 [S]); the
//               propeller turns with the power turbine from the light-off; ground idle ~28 s [E]; starter out at
//               ground idle [S]
//   shutdown    fuel off, Ng runs down -(0.35 + 0.09 Ng) %/s (~32 s from idle); with T1 >= 23 C a 15 s dry motoring
//               [S POH 4-18-01]
//   feather     selected with the engine running: Ng to ground idle, the propeller on its power balance to the
//               feathered-idle ~600 rpm (no governed speed, no torque spike); likewise a pitch the rating cannot turn
// The free turbine (the propeller) waits for the light-off (Kinematics); ground idle is the POH's 64.5 % Ng, raised
// so that the unfeathered propeller turns >= 1,000 rpm (350-900 rpm ground operation is not permitted [S]).

const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const smooth = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };

// ------------------------------------------------------------------ limits / markings (POH Table 2-4-1, 2-5-1, 7-10-1)
export const LIMITS = {
  tq: { max: 55, green: [0, 40.63], amber: 40.63, red: 44.84, white: 15, flat: 44.3, rec: 44.34, rev: 34.26 },
  itt: { min: 400, max: 1000, green: [400, 820], amber: 820, red: 850, redStart: 1000, rev: 820, idle: 750 },
  ng: { max: 120, idle: 64.5, green: [64.5, 104.3], amber: [64.5, 104], red: 104.3, mark13: 13 },
  oilT: { min: 0, max: 120, green: [15, 105], amber: [15, 105], red: 110 },
  oilP: { min: 50, max: 150, green: [90, 135], amber: 90, red: [60, 135] },
  np: { max: 1700, rev: 1650, trans: 1870, revGov: 1615, idleMin: 1000, band: [350, 900] },
  bat: { min: 22, max: 30.3 },
};
// gauge scales and colour bands (drawn by avx_pages.js): [from, to, colour] + marks [value, colour]
export function bands(id, { start = false } = {}) {
  switch (id) {
    case 'tq': return { lo: 0, hi: 55, arcs: [[0, 40.63, 'green'], [40.63, 55, 'grey']],
      marks: [[15, 'white'], [40.63, 'amber'], [44.84, 'red']] };
    case 'itt': return { lo: 400, hi: 1000, arcs: [[400, 820, 'green'], [820, 1000, 'grey']],
      marks: [[820, 'amber'], [start ? 1000 : 850, 'red']] };
    case 'ng': return { lo: 0, hi: 120, arcs: [[0, 64.5, 'grey'], [64.5, 104.3, 'green'], [104.3, 120, 'grey']],
      marks: [[64.5, 'amber'], [104, 'amber'], [104.3, 'red']] };
    case 'oilT': return { lo: 0, hi: 120, arcs: [[0, 15, 'grey'], [15, 105, 'green'], [105, 120, 'grey']],
      marks: [[15, 'amber'], [105, 'amber'], [110, 'red']] };
    case 'oilP': return { lo: 50, hi: 150, arcs: [[50, 90, 'grey'], [90, 135, 'green'], [135, 150, 'grey']],
      marks: [[60, 'red'], [90, 'amber'], [135, 'red']] };
    default: return null;
  }
}

// ------------------------------------------------------------------ propeller (Hartzell HC-E5A-31A, D 2.67 m)
const D5 = Math.pow(2.67, 5), W_PER_SHP = 745.7;
export const PSI_SHP = 0.015924;                // shp = 0.015924 psi Np  [D TCDS]
export const beta42 = (pitch) => (pitch >= 0 ? 14.7 + pitch * (80 - 14.7) / 62 : 14.7 + pitch * (14.7 + 17.5) / 38);
export const pitchOf = (beta) => (beta >= 14.7 ? (beta - 14.7) * 62 / (80 - 14.7) : (beta - 14.7) * 38 / (14.7 + 17.5));
// past ~46 deg the static blades are stalled: with no forward speed a feathered blade meets the air at ~80 deg, a flat
// plate across its own path -- the drag stays high to feather (why a feathered propeller turns slowly at ground idle:
// ~600 rpm at 64.5 % Ng) [D: flat-plate post-stall, fix r1]
const CP = [[-17.5, 0.150], [-8, 0.060], [3, 0.018], [14.7, 0.050], [25, 0.130], [32, 0.200], [40, 0.280], [46, 0.310],
  [52, 0.300], [60, 0.285], [70, 0.265], [80, 0.250]];
export function cp(b) {
  if (b <= CP[0][0]) return CP[0][1];
  for (let i = 0; i < CP.length - 1; i++) if (b <= CP[i + 1][0]) {
    const [x0, y0] = CP[i], [x1, y1] = CP[i + 1];
    return y0 + (y1 - y0) * (b - x0) / (x1 - x0);
  }
  return CP[CP.length - 1][1];
}
export const propShp = (rpm, pitch, rho) => cp(beta42(pitch)) * rho * Math.pow(rpm / 60, 3) * D5 / W_PER_SHP;
// the governor's blade angle at which the propeller absorbs `shp` at `rpm` (the rising branch, 14.7 .. 46 deg)
export function betaFor(shp, rpm, rho) {
  const need = shp * W_PER_SHP / (rho * Math.pow(rpm / 60, 3) * D5);
  let lo = 14.7, hi = 46;
  for (let i = 0; i < 40; i++) { const m = (lo + hi) / 2; if (cp(m) < need) lo = m; else hi = m; }
  return (lo + hi) / 2;
}

// ------------------------------------------------------------------ gas generator (corrected, static)
export const NGM = { idle: 64.5, max: 104, n0: 55.75, nRef: 98, pRef: 1200 };
const pcOf = (nc) => (nc <= NGM.n0 ? 0 : NGM.pRef * Math.pow((nc - NGM.n0) / (NGM.nRef - NGM.n0), 2));
const ncOf = (pc) => NGM.n0 + (NGM.nRef - NGM.n0) * Math.sqrt(Math.max(0, pc) / NGM.pRef);
const F = [862.28, 0.135677, 3.08495e-5];                  // corrected ITT f(Pc) [K], fitted (proto/fit_itt.py)
const fItt = (pc) => F[0] + F[1] * pc + F[2] * pc * pc;
const W_I = 138.3, B_F = 0.325, K_ACC = 60;               // fuel [lb/h]; the start's acceleration heat [K] [E]
const START_ITT_CAP = 870;                                 // EPECS keeps the start peak under it [E; abort 945 S]
// the start's pace (fix r1: the first model lit at 2.5 s and idled at 11.5 s; a PT6 start takes 20-40 s): the starter
// alone toward `crank` % with `tau` s (13 % in ~4.6 s), fuel at `fuelAt`, light-off `lightDelay` s later (ignition delay
// 2-5 s), then the acceleration `acc` [a, b] = a + b (Ng - 15) %/s (1.4 at light-off, ~3.6 near idle; the starter's
// share falls as the turbine takes over), capped by the EPECS ITT schedule: ground idle ~25 s from the start [E]
export const START = { crank: 19, tau: 4.0, fuelAt: 13, lightDelay: 2.0, acc: [1.4, 0.045], max: 6.5 };
// the run-down with the fuel off: d Ng / dt = -(a0 + k Ng) %/s -- ~32 s from ground idle, ~35 s from 90 % [E]
export const RUNDOWN = { a0: 0.35, k: 0.09 };
// a feather selected with the engine running (the viewer's blade pitch >= FEATHER_SEL): the EPECS takes the gas
// generator to ground idle and the governor lets go -- the propeller's speed then follows its own power balance
// (J d w / dt = P_turbine - P_aero) down to the feathered-idle equilibrium (~600 rpm), the torque meter reading the
// turbine's torque (no spike as the blades pass the worst pitch); the same balance carries a blade pitch the rating
// cannot turn at the governed speed (the propeller droops instead of the torque exceeding the limit) [D, fix r1]
export const FEATHER_SEL = 55;
export const J_PROP = 18.0;                                 // kg m^2: the propeller + power turbine at the propeller [E]

// the EPECS rating (shp) at rpm: the flat 44.3 psi, the ITT limit (850 C, 820 in reverse) or Ng 104 %
export function ratingShp(atm, rpm = 1700, rev = false) {
  const sq = Math.sqrt(atm.theta), k = atm.delta * sq;
  const target = ((rev ? LIMITS.itt.rev : LIMITS.itt.red) + 273.15) / atm.theta, [a, b, c] = F;
  const pcItt = (-b + Math.sqrt(b * b - 4 * c * (a - target))) / (2 * c);
  const pcNg = pcOf(NGM.max / sq);
  const flat = rev ? 900 : LIMITS.tq.flat * PSI_SHP * rpm;
  return Math.min(flat, k * pcItt, k * pcNg);
}
// ground idle: Ng >= 64.5 % and the fine-pitch propeller kept >= NP_IDLE_MIN (out of the 350-900 band) [D]
export const NP_IDLE_MIN = 1000;
export function npIdle(atm) {
  const sq = Math.sqrt(atm.theta), p = atm.delta * sq * pcOf(NGM.idle / sq);
  return Math.max(NP_IDLE_MIN, 60 * Math.cbrt(p * W_PER_SHP / (cp(14.7) * atm.rho * D5)));
}
export function ngIdleFor(atm) {
  const sq = Math.sqrt(atm.theta), p = propShp(NP_IDLE_MIN, 0, atm.rho);
  return Math.max(NGM.idle, sq * ncOf(p / (atm.delta * sq)));
}
// the viewer's commanded propeller speed -> the speed the governor / EPECS holds: ground idle by the power balance,
// reverse at 1,615 rpm [S POH 2-4-4 note 11], otherwise the governed speed
// a commanded speed under NP_POSE_MAX is a POSE (tests, look development: the spool-up's smeared blades at 120 rpm, the
// blade cross-fade at 20-44 rpm): the propeller held there windmilling with the fuel off -- no governed speed is that low
export const NP_POSE_MAX = 300;
export const fuelRpm = (rpmT) => (rpmT >= NP_POSE_MAX ? rpmT : 0);
export function npTarget(atm, rpmT, pitch) {
  if (!(rpmT > 0)) return 0;
  if (rpmT < NP_POSE_MAX) return rpmT;
  let r = rpmT <= NP_IDLE_MIN ? Math.max(rpmT, npIdle(atm)) : rpmT;
  if (pitch < -2) r = Math.min(r, LIMITS.np.revGov);
  return r;
}

// the sound's roar reference: shaft power above ground idle, normalised so the tuned states keep their levels
// (1,700 rpm fine pitch ~0.6, full reverse 1.0: the GasGenerator's (Ng - idle) / (max - idle) it replaces)
const P_SND = [51, 650];

const H = 1 / 240;                // the fixed integration sub-step (s): frame-rate independent

export class Engine {
  constructor(atm, env = {}) {
    this.atm = atm;
    this.env = { fuelLb: 2170, gpu: false, ...env };
    this.startN = 0;              // event counters (never reset): starts, light-offs (the sound's one-shot)
    this.lightN = 0;
    this.acc = 0;
    this.last = { rpmT: 0, np: 0, pitch: 62 };
    this.fuel0 = this.env.fuelLb;
    this.used = 0;
    this.soc = [1, 1];
    this.timers = {};
    this.reset();
    this._adcSnap();
  }

  reset() {
    const soak = this.atm.oat + 4.5;          // the cowl soaked in the sun [M P1046408: ITT 29 / oil 28 at 24]
    Object.assign(this, { phase: 'off', ng: 0, np: 0, t: 0, fuelT: -1, lightT: -1, lit: false, comb: 0, starter: 0,
      ign: 0, light: 0, power: 0, ndot: 0, tGas: soak, itt: soak, tMetal: soak, oilT: soak, oilP: 0, ff: 0, tq: 0,
      shp: 0, dry: 0, dryDone: true, tie: false, peak: soak, startEnd: -1, limited: false, gen: false, pumps: false,
      batV: [0, 0], batA: [0, 0], beta: 0, feather: false, ungov: false });
    this._elec(0, 0, false);
    this.timers = {};
  }

  // ---- environment (env.js): a knob changes the day at once; the engine follows with its own dynamics, {instant}
  // (tests) snaps it
  setEnv(atm, env = {}, { instant = false } = {}) {
    this.atm = atm;
    const fuelChanged = env.fuelLb != null && env.fuelLb !== this.env.fuelLb;
    this.env = { ...this.env, ...env };
    if (fuelChanged || instant) { this.fuel0 = this.env.fuelLb; this.used = 0; }     // a FUEL RESET
    if (instant) {
      const L = this.last;
      if (this.phase === 'off') { this.reset(); }
      else if (this.phase === 'run') this.snap(L.rpmT, L.np, L.pitch);
      this._adcSnap();
    }
  }

  // ---- the GasGenerator API (sound.js): instant poses -- running at the commanded speed, or stopped
  snap(rpmT, np, pitch) {
    this.last = { rpmT, np, pitch };
    if (rpmT > 0 && Math.abs(np - rpmT) < 1e-6 || (rpmT > 0 && Math.abs(np - npTarget(this.atm, rpmT, pitch)) < 1e-6)) {
      const counters = [this.startN, this.lightN];
      this.reset();
      Object.assign(this, { phase: 'run', lit: true, comb: 1, np, pumps: true });
      [this.startN, this.lightN] = counters;
      // the steady state: Ng at the demand, the gas and the metal at its temperature, the oil at its equilibrium
      this.ng = this._ngTarget(np, pitch);
      for (let i = 0; i < 3; i++) this._thermo(np, pitch, 0, true);
      this._torque(np, np, pitch, 1, true);
      this.oilT = this._oilEq(np);
      this.oilP = this._oilPTarget();
      this.soc = [1, 1];
      this._elec(0, 0, false);
      this._sndPower();
    } else if (!(rpmT > 0)) {                       // stopped, or a windmilling pose (NP_POSE_MAX): the fuel off
      const counters = [this.startN, this.lightN];
      this.reset();
      [this.startN, this.lightN] = counters;
    }
  }

  // ---- one frame with the propeller's speed given: dt (s); inp {rpmT commanded (0 = fuel off), np the propeller's rpm
  // now, npPrev at the frame's start, pitch (viewer deg)}; sub-stepped at H (driveEngine also steps the propeller at H)
  update(dt, inp) {
    if (!(dt > 0)) return;
    const npPrev = inp.npPrev != null ? inp.npPrev : this.np;
    this.acc += dt;
    const n = Math.floor(this.acc / H + 1e-9);
    this.acc -= n * H;
    for (let i = 1; i <= n; i++) {
      const f0 = (i - 1) / n, f1 = i / n;
      this.tick(H, { rpmT: inp.rpmT, np: npPrev + (inp.np - npPrev) * f1, npPrev: npPrev + (inp.np - npPrev) * f0,
        pitch: inp.pitch });
    }
    this.frame(dt);
  }
  // one fixed sub-step, and the per-frame bookkeeping (air-data filter, caution timers)
  tick(h, inp) {
    this._step(h, inp);
    this.last = { rpmT: inp.rpmT, np: inp.np, pitch: inp.pitch };
  }
  frame(dt) {
    this._adc(dt);
    this._limits(dt);
  }

  _ngTarget(np, pitch) {
    const a = this.atm, sq = Math.sqrt(a.theta), k = a.delta * sq;
    if (this.feather) { this.limited = false; return ngIdleFor(a); }       // feather selected: ground idle
    if (this.ungov) {                     // the governor short of power: the fuel control at the rating
      const rev = pitch < -2, cap = rev ? ratingShp(a, np, true) : ratingShp(a, Math.max(np, NP_IDLE_MIN));
      this.limited = true;
      return Math.max(ngIdleFor(a), sq * ncOf(cap / k));
    }
    return Math.max(ngIdleFor(a), sq * ncOf(this._demand(np, pitch) / k));
  }
  _demand(np, pitch) {
    const rev = pitch < -2;
    const aero = np > 1 ? propShp(np, pitch, this.atm.rho) : 0;
    const cap = rev ? ratingShp(this.atm, np, true) : ratingShp(this.atm, Math.max(np, NP_IDLE_MIN));
    this.limited = aero > cap + 0.5;
    return Math.min(aero, cap);
  }
  _accK(ndot) {                      // the start's excess gas temperature from accelerating the spool [K] [E]
    const a = this.atm, sq = Math.sqrt(a.theta), ncv = Math.max(this.ng / sq, 8) / 100;
    const share = 0.3 * clamp(1 - (this.ng - 13) / 40, 0, 1);                 // the starter's share of the work
    return K_ACC * (this.ng / 100) * (ndot / 6.5) * (1 - share) / (Math.pow(ncv, 1.8) * a.delta / sq);
  }
  _crank() { return START.crank - 0.06 * Math.max(0, 15 - this.oilT); }    // the starter alone; cold oil drags [E]
  // the free turbine's (the propeller's) speed through the start: it turns once the flame drives the power turbine and
  // reaches the idle speed with the gas generator (the propeller follows with a lag: driveEngine)
  npStart() {
    const ngIdle = ngIdleFor(this.atm), s = clamp((this.ng - 17) / (ngIdle - 17), 0, 1);
    return this.lit ? npIdle(this.atm) * Math.pow(s, 1.5) : 0;
  }
  // the turbine's shaft power (shp) at the current Ng, capped by the EPECS rating at the propeller's speed
  gasShp(np, pitch) {
    const a = this.atm, sq = Math.sqrt(a.theta), k = a.delta * sq;
    const cap = pitch < -2 ? ratingShp(a, np, true) : ratingShp(a, Math.max(np, NP_IDLE_MIN));
    return this.lit ? this.comb * Math.min(k * pcOf(this.ng / sq), cap) : 0;
  }

  _step(dt, { rpmT, np, npPrev, pitch }) {
    const a = this.atm, sq = Math.sqrt(a.theta), T1 = a.oat;
    const run = rpmT > 0;
    if (run && (this.phase === 'off' || this.phase === 'rundown' || this.phase === 'dry')) {
      Object.assign(this, { phase: 'start', t: 0, fuelT: -1, lightT: -1, lit: false, peak: this.itt, startEnd: -1,
        dry: 0, tie: false });
      this.startN++;
    } else if (!run && (this.phase === 'start' || this.phase === 'run')) {
      Object.assign(this, { phase: 'rundown', lit: false, fuelT: -1, dryDone: T1 < 23 });   // dry motoring if T1 >= 23 C
    }
    this.t += dt;
    this.pumps = run;
    const ng0 = this.ng, ngIdle = ngIdleFor(a);
    switch (this.phase) {
      case 'start': {
        if (this.fuelT < 0 && this.ng >= START.fuelAt) this.fuelT = this.t;
        if (this.fuelT >= 0 && this.lightT < 0 && this.t - this.fuelT >= START.lightDelay) { this.lightT = this.t; this.lit = true; this.lightN++; }
        if (!this.lit) this.ng += (this._crank() - this.ng) * (1 - Math.exp(-dt / START.tau));
        else {
          // the acceleration schedule (START.acc), slowed so that the start ITT stays <= 870 C
          const base = a.theta * (fItt(0) + 60 * Math.pow(Math.max(0, ngIdle - this.ng / sq) / 48.5, 2));
          const r0 = Math.min(START.max, START.acc[0] + START.acc[1] * Math.max(0, this.ng - 15));
          const full = this._accK(r0), room = START_ITT_CAP + 273.15 - base;
          const rate = r0 * clamp(room / Math.max(full, 1), 0.2, 1);
          const tgt = ngIdle + 0.5, d = tgt - this.ng, v = Math.min(Math.abs(d) * 0.9, rate) * dt;
          this.ng = Math.abs(d) <= v ? tgt : this.ng + Math.sign(d) * v;
          if (this.ng >= ngIdle - 0.5) { this.phase = 'run'; this.startEnd = this.t; }
        }
        break;
      }
      case 'run': {
        const tgt = this._ngTarget(np, pitch);
        const d = tgt - this.ng, v = Math.min(Math.abs(d) * 0.9, d > 0 ? 12 : 10) * dt;
        this.ng = Math.abs(d) <= v || Math.abs(d) < 0.005 ? tgt : this.ng + Math.sign(d) * v;
        break;
      }
      case 'rundown':
        this.ng -= (RUNDOWN.a0 + RUNDOWN.k * this.ng) * dt;
        if (!this.dryDone && this.ng <= 20) { this.phase = 'dry'; this.dry = 0; }
        if (this.ng <= 0) { this.ng = 0; this.phase = 'off'; }
        break;
      case 'dry':                    // 15 s dry motoring on the starter (STARTER, CAS dry motoring), then the run-down
        this.dry += dt;
        this.ng += (this._crank() - this.ng) * (1 - Math.exp(-dt / START.tau));
        if (this.dry >= 15) { this.phase = 'rundown'; this.dryDone = true; }
        break;
      default: this.ng = 0;
    }
    this.ndot = (this.ng - ng0) / dt;
    this.starter = this.phase === 'start' || this.phase === 'dry' ? 1 : 0;
    this.ign = this.phase === 'start' && this.ng < 50 ? 1 : 0;     // the igniters (IGNITION): through the light-off
    this.comb += ((this.lit ? 1 : 0) - this.comb) * (1 - Math.exp(-dt / (this.lit ? 0.3 : 0.25)));
    if (this.comb < 1e-4 && !this.lit) this.comb = 0;
    const s = this.lightT >= 0 && this.phase !== 'rundown' && this.phase !== 'off' && this.phase !== 'dry' ? this.t - this.lightT : -1;
    this.light = s >= 0 && s < 6 ? (1 - Math.exp(-s / 0.07)) * Math.exp(-s / 0.7) / 0.7152 : 0;
    this._thermo(np, pitch, dt, false);
    this._torque(np, npPrev, pitch, dt, false);
    // oil pressure: the pump (Ng^2) through the viscosity regulator, tau 0.4 s
    const pT = this._oilPTarget();
    this.oilP += (pT - this.oilP) * (1 - Math.exp(-dt / 0.4));
    if (Math.abs(pT - this.oilP) < 0.05) this.oilP = pT;
    // oil temperature: one thermal node
    this.oilT += (this._oilQ(np, this.oilT)) / 40 * dt;
    // fuel burnt (lb) -- equal from both tanks (auto-balance [S])
    this.used += this.ff / 3600 * dt;
    this._elec(dt, rpmT, run);
    this.np = np;
    this.beta = beta42(pitch);
    this._sndPower();
  }

  // gas temperature at the probes, the probe lag, the hot section's metal, the fuel flow
  _thermo(np, pitch, dt, steady) {
    const a = this.atm, sq = Math.sqrt(a.theta), k = a.delta * sq, T1 = a.oat, ngIdle = ngIdleFor(a);
    const ncv = this.ng / sq;
    let dTacc = 0;
    if (this.comb > 1e-3) {
      const pc = this.phase === 'run' ? pcOf(ncv) : 0;
      const base = a.theta * (fItt(pc) + 60 * Math.pow(Math.max(0, ngIdle - ncv) / 48.5, 2));
      dTacc = this.phase === 'start' ? this._accK(Math.max(0, this.ndot)) : 0;
      const lit = base + dTacc;
      const cold = this.tMetal + 273.15 - (this.tMetal - T1) * clamp(this.ng / 25, 0, 0.6);
      this.tGas = cold + this.comb * (lit - cold) - 273.15;
    } else this.tGas = this.tMetal - (this.tMetal - T1) * clamp(this.ng / 25, 0, 0.6);
    if (steady) { this.itt = this.tGas; this.tMetal = this.tGas; }
    else {
      const d = this.tGas - this.itt;
      this.itt = Math.abs(d) < 0.02 ? this.tGas : this.itt + d * (1 - Math.exp(-dt / 0.9));
      const tauM = this.lit ? 60 : 240 / (1 + 0.6 * this.ng);
      const toward = this.lit ? this.tGas : a.oat + 4.5, dm = toward - this.tMetal;
      this.tMetal = Math.abs(dm) < 0.01 ? toward : this.tMetal + dm * (1 - Math.exp(-dt / tauM));
    }
    if (this.phase === 'start') this.peak = Math.max(this.peak, this.itt);
    // fuel flow (lb/h): the core + the shaft power + the acceleration's heat
    const waKgS = 4.5 * Math.pow(Math.max(ncv, 1) / 100, 1.8) * a.delta / sq;
    const accLb = waKgS * 1150 * dTacc / (0.98 * 43e6) * 7936.6;
    // (from the fuel-on at 13 % Ng the start schedule flows before the flame: the FF readout leaves 0 first)
    const fuelOn = this.lit || (this.phase === 'start' && this.fuelT >= 0);
    this.ff = fuelOn ? k * (W_I * ncv / 64.5 + (this.lit ? B_F * pcOf(ncv) : 0)) + accLb : 0;
  }

  // the torque meter (reduction gearbox): the propeller's demand + its acceleration while lit, capped by the gas power
  // the current Ng makes and the rating; 0 unlit; + the 0.2 psi zero offset of the parked meter [M P1046408], faded out
  // over the first 2 psi (state: T/O reads the rating itself)
  _torque(np, npPrev, pitch, dt, steady) {
    const a = this.atm, sq = Math.sqrt(a.theta), k = a.delta * sq;
    let q = 0;
    if (this.lit && np > 1 && this.ungov && !steady) {
      q = this.gasShp(np, pitch) / this.comb / (PSI_SHP * np);           // the power balance: the turbine's torque
    } else if (this.lit && np > 1) {
      const aero = propShp(np, pitch, a.rho);
      const w = np * Math.PI / 30, wdot = steady ? 0 : (np - npPrev) * Math.PI / 30 / dt;
      const pAcc = Math.max(0, 8.0 * w * wdot) / W_PER_SHP;
      const avail = this.phase === 'run' ? Math.max(k * pcOf(this.ng / sq), aero) : Infinity;
      const cap = pitch < -2 ? ratingShp(a, np, true) : ratingShp(a, Math.max(np, NP_IDLE_MIN));
      q = Math.min(aero + pAcc, avail, cap) / (PSI_SHP * np);
    }
    this.tqRaw = this.comb * q;
    this.shp = this.tqRaw * PSI_SHP * np;
    this.tq = this.tqRaw;
  }

  _oilPTarget() {
    const T = this.oilT;
    const preg = Math.min(160, 100 + 0.5 * Math.max(0, 60 - T) - 0.25 * Math.max(0, T - 60));
    return preg * Math.min(1, Math.pow(this.ng / 58, 2));
  }
  // the oil node's heat balance (kW): the bearings / gears (Ng^2) + 1.2 % of the shaft power in, the nacelle and the
  // thermostatic cooler (70-85 C, its air flow with the propeller's slipstream) out
  _oilQ(np, T) {
    const a = this.atm, shaftKw = this.shp * 0.7457;
    const qin = (this.ng > 1 ? 4.5 * Math.pow(this.ng / 64.5, 2) : 0) + 0.012 * shaftKw;
    const valve = smooth(70, 85, T) * (0.3 + 0.7 * np / 1700);
    return qin - (0.125 * (T - (a.oat + 4.5)) + 0.6 * valve * (T - a.oat));
  }
  _oilEq(np) {
    let lo = this.atm.oat - 10, hi = 160;
    for (let i = 0; i < 50; i++) { const m = (lo + hi) / 2; if (this._oilQ(np, m) > 0) lo = m; else hi = m; }
    return (lo + hi) / 2;
  }

  // two 24 V 42 Ah lead-acid batteries; the starter from BAT2 (BAT1 tied in at 10 % Ng or 10 s), the generators on
  // line once the starter cuts out at idle; ground power 28.2 V.  Positive current = charging.
  _elec(dt, rpmT, run) {
    const a = this.atm, gpu = !!this.env.gpu;
    const tBat = Math.max(a.oat, 4);                       // heated batteries [S POH 7-13]
    const R = 0.010 * (1 + 0.025 * Math.max(0, 20 - tBat));
    const voc = (s) => 23.6 + 1.9 * s - 0.004 * Math.max(0, 20 - tBat);
    const iSt = this.starter ? 600 * Math.max(0.12, 1 - this.ng / 70) : 0;
    const load = 26 + (run ? 10 : 0);                      // the avionics; + the boost pumps at RUN [E]
    if (this.phase === 'start' && (this.ng >= 10 || this.t >= 10)) this.tie = true;
    if (this.phase !== 'start') this.tie = false;
    this.gen = this.phase === 'run';
    let iB = [0, 0];
    if (this.gen || gpu) {
      const vb = 28.2;
      for (let j = 0; j < 2; j++) iB[j] = (1 + 400 * (1 - this.soc[j])) * Math.tanh((vb - voc(this.soc[j])) / 0.5);
      if (gpu && !this.gen && iSt > 0) iB = [0, 0];
      const sag = gpu && !this.gen && iSt > 0 ? iSt * 0.004 : 0;
      this.batV = [vb - sag, vb - sag];
    } else {
      const share2 = this.tie ? 0.5 : 1;
      iB = [-(load / 2 + iSt * (1 - share2)), -(load / 2 + iSt * share2)];
      this.batV = iB.map((i, j) => voc(this.soc[j]) + i * R);
    }
    this.batA = iB;
    for (let j = 0; j < 2; j++) this.soc[j] = clamp(this.soc[j] + iB[j] * dt / (42 * 3600), 0, 1);
  }

  _sndPower() {
    this.power = this.lit ? Math.sqrt(clamp((this.shp - P_SND[0]) / (P_SND[1] - P_SND[0]), 0, 1)) : 0;
  }

  // ---- the air-data computer's view of the day (tau 1 s): SAT, the altimeter, the pressure altitude, the pitot
  _adcSnap() {
    const a = this.atm;
    this.adc = { sat: a.oat, alt: a.indAlt, pa: a.pa, ias: a.air ? a.air.ias : 0 };
  }
  _adc(dt) {
    const a = this.atm, d = this.adc, f = 1 - Math.exp(-dt / 1.0);
    const go = (k, v, eps) => { const e = v - d[k]; d[k] = Math.abs(e) < eps ? v : d[k] + e * f; };
    go('sat', a.oat, 0.02); go('alt', a.indAlt, 0.5); go('pa', a.pa, 0.5); go('ias', a.air ? a.air.ias : 0, 0.02);
  }

  // ---- caution / warning colouring (POH Table 7-10-1 / 7-10-2), deterministic timers in sim time; none with the
  // engine not running [M P1046410: oil 0 psi and NG 0.0 stay green]
  _limits(dt) {
    const T = this.timers, on = this.phase === 'run' || this.phase === 'start';
    const tick = (k, cond) => { T[k] = cond && on ? (T[k] || 0) + dt : 0; return T[k]; };
    const start = this.phase === 'start', rev = this.last.pitch < -2;
    const c = {}, w = {};
    // torque
    if (tick('tqHi', this.tq > LIMITS.tq.red) > 5) c.tq = true;
    if (T.tqHi > 20 || this.tq > 61) w.tq = true;
    // ITT: running 850-900 20 s / > 900; starting 900-1000 5 s / > 1000
    if (start) { if (tick('ittS', this.itt > 900) > 5 || this.itt > 1000) w.itt = true; T.ittR = 0; }
    else if (on) { if (tick('ittR', this.itt > 850.5) > 20 || this.itt > 900) w.itt = true; else if (this.itt > LIMITS.itt.amber) c.itt = true; }
    // Ng: < 60 running (caution), > 104 20 s / > 104.3
    if (this.phase === 'run' && this.ng < 60) c.ng = true;
    if (tick('ngHi', this.ng > 104) > 20 || (on && this.ng > 104.3)) w.ng = true;
    // Np: reverse over 1,650; 1,760-1,870 20 s / > 1,870; 350-900 on the ground unfeathered 15 s
    const np = this.np;
    if (tick('npRev', rev && np > LIMITS.np.rev) > 2) c.np = true;          // (the governor's 1-2 s settling into beta)
    if (tick('npHi', np > 1760) > 20 || (on && np > 1870)) w.np = true;
    if (tick('npBand', np > 350 && np < 900 && this.last.pitch < 60 && this.phase === 'run') > 15) c.np = true;
    // oil pressure: < 40 (0.5 s) warning, < 60 with Ng > 72 warning, 60-90 5 s caution, > 135 caution
    if (this.phase === 'run') {
      if (tick('opLo', this.oilP < 40) > 0.5 || (this.oilP < 60 && this.ng > 72)) w.oilP = true;
      else if (tick('opMid', this.oilP < 90) > 5 || tick('opHi', this.oilP > 135) > 5) c.oilP = true;
      // oil temperature: < 15 / 105-110 caution, > 110 warning
      if (this.oilT > 110) w.oilT = true;
      else if (this.oilT < 15 || this.oilT > 105) c.oilT = true;
    }
    this.caution = c;
    this.warning = w;
  }

  // ---- the T/O rating and the governor's blade angle for it (the 'T/O' button)
  rating() { return ratingShp(this.atm, 1700) / (PSI_SHP * 1700); }
  toPitch(rpm = 1700) { return pitchOf(betaFor(ratingShp(this.atm, rpm), rpm, this.atm.rho)); }

  // ---- everything a page draws, in display units
  get state() {
    const lb = Math.max(0, this.fuel0 - this.used), rho = 6.725 * (1 - 0.00092 * (this.atm.oat - 15));
    return {
      // the GasGenerator API (sound.js)
      ng: this.ng, phase: this.phase, lit: this.lit, comb: this.comb, light: this.light, starter: this.starter,
      ign: this.ign, power: this.power, t: this.t, startN: this.startN, lightN: this.lightN,
      lightAge: this.lightT >= 0 && this.phase !== 'rundown' && this.phase !== 'off' && this.phase !== 'dry' ? this.t - this.lightT : -1,
      // the indications
      np: this.np, tq: this.tq + 0.2 * Math.max(0, 1 - this.tq / 2), itt: this.itt, ff: this.ff, oilP: this.oilP, oilT: this.oilT, t1: this.adc.sat,
      shp: this.shp, beta: this.beta, pumps: this.pumps, dry: this.phase === 'dry' ? this.dry : 0, peak: this.peak,
      startEnd: this.startEnd, limited: this.limited, gen: this.gen, tie: this.tie,
      bat: [{ v: this.batV[0], a: this.batA[0] }, { v: this.batV[1], a: this.batA[1] }],
      fuel: { lb: [lb / 2, lb / 2], qty: lb, gal: lb / rho, used: this.used, low: lb / 2 < 134, rho },
      rating: this.rating(), caution: { ...this.caution }, warning: { ...this.warning },
      adc: { ...this.adc },
    };
  }
}

// ------------------------------------------------------------------ the propeller's spool (Kinematics; unchanged laws)
// d rpm / dt: from rest (start) a0 + k rpm, governed k (target - rpm) rate-limited, run-down -(a0 + k rpm); before
// the light-off the free turbine only creeps (compressor air flow) toward CREEP.rpm
export const PROP_SPOOL = { governed: 900, start: { a0: 55, k: 0.14 }, creep: { rpm: 4, tau: 1.5 },
  stop: { a0: 18, k: 0.09 }, startLag: 0.8, gov: { k: 1.6, up: 320, down: 260 }, unfeather: 300, feathered: 60 };
export function spoolRpm(rpm, target, dt) {
  const P = PROP_SPOOL, G = P.governed;
  let r;
  if (target > rpm) {
    r = rpm < G ? rpm + (P.start.a0 + P.start.k * rpm) * dt : rpm + Math.min(P.gov.up, P.gov.k * (target - rpm) + 2) * dt;
    r = Math.min(r, target);
  } else {
    r = target < G || rpm < G ? rpm - (P.stop.a0 + P.stop.k * rpm) * dt : rpm - Math.min(P.gov.down, P.gov.k * (rpm - target) + 2) * dt;
    r = Math.max(r, target);
  }
  return Math.abs(r - target) < 0.05 ? target : r;
}
// one frame of the propeller + engine: k = {t: {rpm, pitch}, c: {rpm, pitch}, unfeather, eng} (Kinematics itself, or
// the node test's stand-in); returns true when the propeller's speed changed
// (both at the engine's fixed sub-step H: 30 / 60 / 144 Hz frames give the same trace)
export function driveEngine(k, dt) {
  const t = k.t, c = k.c, eng = k.eng, P = PROP_SPOOL, rpm0 = c.rpm;
  if (!(dt > 0)) return false;
  eng.acc += dt;
  const n = Math.floor(eng.acc / H + 1e-9);
  eng.acc -= n * H;
  for (let i = 0; i < n; i++) {
    const tgt = npTarget(eng.atm, t.rpm, c.pitch), npPrev = c.rpm;
    const running = eng.phase === 'run' && eng.lit && t.rpm >= NP_POSE_MAX;
    eng.feather = running && t.pitch >= FEATHER_SEL;
    if (running && !eng.feather && !eng.ungov && tgt > 0) {
      // a blade pitch the rating cannot turn at the governed speed: the propeller droops (the power balance below)
      const cap = c.pitch < -2 ? ratingShp(eng.atm, c.rpm, true) : ratingShp(eng.atm, Math.max(c.rpm, NP_IDLE_MIN));
      if (propShp(c.rpm, c.pitch, eng.atm.rho) > cap * 1.01 + 2) eng.ungov = true;
    }
    if (eng.feather) eng.ungov = true;
    if (!running) eng.ungov = false;
    if (tgt > c.rpm && eng.phase === 'start' && !eng.lit) {
      c.rpm = c.rpm <= P.creep.rpm ? c.rpm + (P.creep.rpm - c.rpm) * (1 - Math.exp(-H / P.creep.tau))
        : spoolRpm(c.rpm, P.creep.rpm, H);                        // a restart while running down: it keeps slowing
    } else if (tgt > c.rpm && eng.phase === 'start') {
      // lit: the free turbine takes the propeller up with the gas generator (eng.npStart), never down
      const want = Math.min(tgt, eng.npStart());
      if (want > c.rpm) c.rpm += (want - c.rpm) * (1 - Math.exp(-H / P.startLag));
    } else if (eng.ungov) {
      // J dw/dt = P_turbine - P_aero (the governor let go: feather selected, or the rating short of the demand)
      const w = Math.max(c.rpm, 30) * Math.PI / 30;
      const dP = (eng.gasShp(c.rpm, c.pitch) - propShp(c.rpm, c.pitch, eng.atm.rho)) * W_PER_SHP;
      c.rpm = Math.max(0, c.rpm + dP / (J_PROP * w) * 30 / Math.PI * H);
      if (!eng.feather && c.rpm >= tgt) { c.rpm = tgt; eng.ungov = false; }        // governing again
    } else if (tgt !== c.rpm) c.rpm = spoolRpm(c.rpm, tgt, H);
    if (k.unfeather && c.rpm >= P.unfeather) { t.pitch = 0; k.unfeather = false; }
    eng.tick(H, { rpmT: fuelRpm(t.rpm), np: c.rpm, npPrev, pitch: c.pitch });
  }
  eng.frame(dt);
  return c.rpm !== rpm0;
}
