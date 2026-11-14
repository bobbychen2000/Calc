// Aircraft views (hwd3d Phase 2, P3; Phase 3b: detailed models in the app). Replaces sfo3d/js/live/aircraft.js @ a967f9b
// (LiveAircraft: imported airliner models + procedural airliner + liveries), which is not forked. Every drawn track gets
// one drawable: a DetailedAircraft (js/aircraft/models.js createAircraft: PC12 and SF50, the types with a model) or the GA
// placeholder (js/aircraft/placeholder.js) for every other type, both sized from the dimension record with the detailed
// model's measured frame (js/aircraft/models.js withModelFrame: xMain / xNose / track / L / span / H of the model, so the
// drawn gear stands on the engine's main-gear origin; docs/phase3_models.md section 3).
//
//   new AircraftViews(scene, { quality })
//   .sync(traffic, now, { nightF, selectedKey, dt })   creates / updates / removes one drawable per drawn track: position =
//        the traffic body (main-gear contact; on the ground y = site.groundY, set by traffic.js), heading (deg true) ->
//        fwd, pitch / roll (tr.disp.pitch / roll, rad; 0 when the engine gives none), gear, rotor / propeller / fan speed,
//        flaps, control surfaces and light states, all driven from the drawn motion (below)
//   .get(key) -> drawable | null ;  .dimsOf(tr) -> the drawable's dims record ;  .modelNote(tr) -> text ;  .dispose()
//   .drive(key) -> the drive state of a drawable { gear, gearUp, flaps, rotor, running, ctl, lights } (QA / video trace)
// A track is drawn when disp.valid, inside the D6 window (tr.inView), not hidden (hangared) and its fade alpha > 0.02; the
// fade is drawn as a screen-door dither (js/shaders/objects.js uAlpha, fix round 1; js/aircraft/detailed.js acobj).
//
// Driving the detailed models (Phase 3b). The ADS-B data says nothing about gear, flaps, power, control surfaces or lights:
// every rule here is a design choice [inf], made to look like normal operation, never shown as data:
//  - gear (retractable types, T.retract): retracts once the aircraft climbs ("positive rate of climb": > 15 m above the
//    ground, climbing > 0.75 m/s, 2 s after lift-off, not on an approach leg); extends on an approach leg (downwind, base,
//    final, arriving) below 2,000 ft above the ground or below 1,000 ft when descending > 1.5 m/s (each after the gear has
//    been up >= 10 s), and below 400 ft whenever it descends (> 0.3 m/s); vertical speed smoothed over 2 s;
//    a full cycle takes GEAR_S (6 s, as traffic.js; js/aircraft/kinematics.js gearSequence splits it into doors and legs);
//    an aircraft first drawn in the air starts in its rule state (no cycle at its first frame);
//  - flaps (degrees, the model's own flap settings from its pivot `settings`: PC-12 0 / 15 / 30 / 40, SF50 0 / 15 / 39):
//    take-off setting (the second) from the hold / run-up / line-up through the roll and the climb-out to 400 ft above the
//    ground; the same setting on a downwind below 1,500 ft; the approach setting (the second highest) on base and on final
//    above 500 ft; the landing setting (the highest) on final below 500 ft, kept through the landing roll until the
//    aircraft taxis (an aircraft first drawn on its landing roll starts with it); up (0) otherwise; js/aircraft/detailed.js
//    moves them at 11 deg/s;
//  - propeller / fan: off when parked, in a hangar or silent at rest; else spooling (time constant SPOOL_S) to the idle
//    speed on the ground below 30 kt and to the run speed on a take-off / landing roll and in the air (PC-12: the pc12
//    pivot's 1,700 rpm = 178 rad/s run, 110 rad/s idle; SF50 fan 100 / 120 rad/s - both idle values and the SF50 fan speed
//    are not sourced); PC-12 blades feathered at rest, flat while running, in reverse (-15 deg) on a landing roll above 40 kt;
//  - control surfaces (-1..1 commands, js/aircraft/kinematics.js signs): ailerons from the roll rate, elevator from the
//    pitch rate, rudder from the turn rate (on the ground the nose-wheel steering angle, linked to the pedals; in the air a
//    little with the aileron); rates smoothed over 0.4 s and capped at 0.35 / 0.35 / 0.6, then the drawable's own lag;
//  - lights: js/env/aircraft_lights.js aircraftLightStates (P2: nav and beacon whenever the engine runs, strobes on the
//    runway and in the air, landing lights on the take-off / landing roll and low in the air, taxi light when taxiing); a
//    silent aircraft whose motion the engine continues counts as operating (before: its lights went out at once).
import { GaAircraft } from '../aircraft/placeholder.js';
import { dimsNote } from '../aircraft/ga_dims.js';
import { aircraftLightStates } from '../env/aircraft_lights.js';
import { MODELS, hasModel, createAircraft, withModelFrame } from '../aircraft/models.js';

const D2R = Math.PI / 180, KT = 1852 / 3600, FT = 0.3048;
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const wrapPi = (a) => { a = (a + Math.PI) % (2 * Math.PI); if (a < 0) a += 2 * Math.PI; return a - Math.PI; };
// GA display phases -> the light-state vocabulary of aircraft_lights.js lightPhase
const LIGHT_PHASE = { parked: 'parked', hangared: 'parked', taxi: 'taxi', runup: 'holding', hold_short: 'holding', line_up: 'lineup', runway_taxi: 'taxi',
  takeoff_roll: 'takeoff', landing_roll: 'rollout', touch_and_go: 'rollout', stop_and_go: 'rollout', heli_ground: 'holding', vehicle: 'vehicle' };
// ---------------------------------------------------------------- drive rules [inf, see the header]
export const GEAR_S = 6;                  // s for a full gear cycle (traffic.js ramps disp.gear over the same 6 s)
export const SPOOL_S = 2.5;               // s, first-order time constant of the propeller / fan speed
const APPROACH = new Set(['downwind', 'base', 'final', 'arriving']);
const CLIMB_OUT = new Set(['initial_climb', 'upwind', 'departing', 'go_around', 'low_pass', 'crosswind']);
const TO_GROUND = new Set(['hold_short', 'runup', 'line_up', 'takeoff_roll', 'touch_and_go', 'stop_and_go']);
const OFF_PHASE = new Set(['parked', 'hangared', 'no_signal']);
// per type: rotor speeds (rad/s) and blade pitch (deg, js/aircraft/kinematics.js 'pitch': clamped to [reverse, feather])
const POWER = {
  PC12: { idle: 110, run: 178, feather: 62, flat: 0, reverse: -15,
    basis: 'run = the pc12 pivot rpm 1,700 (pc12/out/pc12_meta.json); idle 110 rad/s (~1,050 rpm), the blade angles and the reverse on the roll are inferred' },
  SF50: { idle: 100, run: 120, basis: 'fan speeds inferred (not sourced); above 60 rad/s the fan is drawn at a slow apparent angle (js/aircraft/detailed.js)' },
};
const FLAP_FALLBACK = { PC12: [0, 15, 30, 40], SF50: [0, 15, 39] };   // the models' pivot settings (until the model has loaded)
const LIGHTS_OFF = { nav: false, beacon: false, strobe: false, landing: false, taxi: false };

export class AircraftViews {
  constructor(scene, { quality = 'high' } = {}) { this.scene = scene; this.quality = quality; this.map = new Map(); this.drv = new Map(); this.t = 0; this.flapSets = new Map(); }
  /** the dims record the drawable is built from: the track's record with the detailed model's measured frame */
  dimsOf(tr) { const T = tr && tr.dims; return T ? (T.frameSrc === 'model' ? T : withModelFrame(T)) : null; }
  sync(traffic, now, { nightF = 0, selectedKey = null, dt = 1 / 30 } = {}) {
    const seen = new Set();
    for (const tr of traffic.tracks.values()) {
      const D = tr.disp;
      if (!D.valid || !tr.inView || tr.hidden || !(D.alpha > 0.02) || !tr.dims) continue;
      seen.add(tr.key);
      const T = this.dimsOf(tr);
      let v = this.map.get(tr.key);
      if (v && v.T !== T) { this.scene.remove(v); v.dispose(); v = null; this.drv.delete(tr.key); }   // type resolved later: new drawable
      const fresh = !v;
      if (!v) {
        const o = { id: tr.key, lodDist: this.quality === 'low' ? 4000 : 8000, shadowDist: this.quality === 'low' ? 1200 : 2500 };
        v = hasModel(T.type) ? createAircraft(T, { ...o, R: this.scene.R }) : new GaAircraft(T, o);
        this.map.set(tr.key, v); this.scene.add(v);
      }
      v.pos = [D.x, D.y, D.z]; v.alpha = Math.min(1, D.alpha);
      v.fwd = [Math.sin(D.hdg * D2R), 0, -Math.cos(D.hdg * D2R)];
      v.pitch = Number.isFinite(D.pitch) ? D.pitch : 0; v.roll = Number.isFinite(D.roll) ? D.roll : 0; v.selected = tr.key === selectedKey;
      const gy = traffic.groundY ? traffic.groundY(D.x, D.z) : D.y;
      const agl = D.ground ? 0 : D.y - gy;
      const moving = !D.ground || D.gs > 0.5;
      const S = this.drive(tr.key, true);
      const heli = T.cls === 'heli';
      // gear (all retractable types; fixed gear stays down)
      if (T.retract && !heli) {
        S.tAir = D.ground ? 0 : S.tAir + dt;
        S.vsF = fresh ? (D.vs || 0) : S.vsF + ((D.vs || 0) - S.vsF) * (1 - Math.exp(-dt / 2));   // vertical speed smoothed over 2 s
        const want = this.gearRule(S, D, agl, tr.phase, fresh);
        S.tGear = want !== S.gearUp || fresh ? 0 : S.tGear + dt; S.gearUp = want;
        const tgt = want ? 0 : 1;
        S.gear = fresh ? tgt : clamp(S.gear + clamp(tgt - S.gear, -dt / GEAR_S, dt / GEAR_S), 0, 1);
        if (D.ground) S.gear = 1;   // never drawn on the ground with the gear up (an engine re-placement): snap down
      } else S.gear = D.gear ?? 1;
      v.gear = S.gear;
      // power: running unless parked / hangared / silent at rest
      const running = moving || !(OFF_PHASE.has(tr.phase) || (tr.stale && !moving));
      S.running = running;
      if (heli) v.rotor = (!D.ground || D.gs > 0.5 || ['heli_hover', 'heli_hover_taxi'].includes(tr.phase)) ? 40 : 0;   // ~380 rpm [inf]
      else if (v.setFlaps) {
        const P = POWER[T.type] || { idle: 100, run: 150 };
        const fast = !D.ground || D.gs > 30 * KT || tr.phase === 'takeoff_roll';
        const tgt = running ? (fast ? P.run : P.idle) : 0;
        S.rotor = fresh ? tgt : S.rotor + (tgt - S.rotor) * (1 - Math.exp(-dt / SPOOL_S));
        if (!running && S.rotor < 0.5) S.rotor = 0;
        v.rotor = S.rotor;
        // flaps
        const set = this.flapSet(T.type, v);
        S.flaps = this.flapRule(set, fresh ? null : S.flaps, D, agl, tr.phase);
        v.setFlaps(S.flaps, fresh);
        // control surfaces from the drawn motion
        this.controls(S, D, T, dt, fresh);
        const bp = P.feather != null ? (!running && S.rotor < 20 ? P.feather : tr.phase === 'landing_roll' && D.gs > 40 * KT ? P.reverse : P.flat) : 0;
        v.setControls({ roll: S.ctl.roll, pitch: S.ctl.pitch, yaw: S.ctl.yaw, bladePitch: bp }, fresh);
        v.groundRef = gy;   // ground y under the aircraft: the ground-contact occlusion of the acobj shader
      } else v.rotor = 0;   // GA placeholders: no propeller is drawn for fixed-wing types
      v.step(dt);
      const ph = LIGHT_PHASE[tr.phase] || (D.ground ? 'taxi' : 'climb');
      const L = D.alpha > 0.5 ? aircraftLightStates({ phase: ph, ground: D.ground, gs: D.gs / KT, altAgl: agl, stale: !!tr.stale && !moving }) : LIGHTS_OFF;
      v.lightsOn = L; S.lights = L;
      v.visible = true;
    }
    for (const [k, v] of this.map) if (!seen.has(k)) { this.scene.remove(v); v.dispose(); this.map.delete(k); this.drv.delete(k); }
  }
  drive(key, make = false) {
    let S = this.drv.get(key);
    if (!S && make) { S = { gear: 1, gearUp: false, tAir: 0, vsF: 0, tGear: 0, flaps: 0, rotor: 0, running: false, ctl: { roll: 0, pitch: 0, yaw: 0 }, rr: 0, pr: 0, yr: 0, last: null, lights: LIGHTS_OFF }; this.drv.set(key, S); }
    return S || null;
  }
  // true = gear up; hysteresis on the current state (see the header)
  gearRule(S, D, agl, phase, fresh) {
    if (D.ground) return false;
    const vs = S.vsF, appr = APPROACH.has(phase);
    // first drawn in the air: the state the rule would have reached (climbing away -> up; on an approach leg or low and
    // descending -> down)
    if (fresh) return appr ? agl > 2000 * FT : (agl > 15 && vs > 0.75) || (agl > 400 * FT && !(agl < 1000 * FT && vs < -1));
    if (!S.gearUp) return agl > 15 && vs > 0.75 && S.tAir > 2 && !appr && agl > 0.05;
    // (a state is held >= 10 s - pattern climbs and descents wobble - except the low descent, which always extends)
    return !((S.tGear > 10 && ((appr && agl < 2000 * FT) || (agl < 1000 * FT && vs < -1.5))) || (agl < 400 * FT && vs < -0.3));
  }
  flapSet(type, v) {
    if (this.flapSets.has(type)) return this.flapSets.get(type);
    const m = v && v.m; let set = null;
    if (m && m.parts) { const p = m.parts.find(q => q.pivot && q.pivot.kind === 'flap' && Array.isArray(q.pivot.settings)); if (p) set = p.pivot.settings.slice().sort((a, b) => a - b); }
    if (set) { this.flapSets.set(type, set); return set; }
    return FLAP_FALLBACK[type] || [0, 15, 30];
  }
  flapRule(set, prev, D, agl, phase) {
    const n = set.length, to = set[Math.min(1, n - 1)], ap = set[Math.max(1, n - 2)], ld = set[n - 1];
    if (D.ground) {
      if (TO_GROUND.has(phase)) return to;
      // kept from the landing (or the take-off setting) until the aircraft taxis; first drawn on a landing roll: landing flaps
      if (phase === 'landing_roll') return prev != null ? prev : ld;
      if (phase === 'runway_taxi') return prev != null ? prev : 0;
      return 0;
    }
    if (CLIMB_OUT.has(phase)) return agl < 400 * FT ? to : 0;
    if (phase === 'downwind') return agl < 1500 * FT ? to : 0;
    if (phase === 'base') return ap;
    if (phase === 'final' || (phase === 'arriving' && agl < 1000 * FT)) return agl > 500 * FT ? ap : ld;
    return 0;
  }
  controls(S, D, T, dt, fresh) {
    const h = D.hdg * D2R;
    if (fresh || !S.last || !(dt > 0)) { S.last = { roll: D.roll || 0, pitch: D.pitch || 0, h }; S.rr = S.pr = S.yr = 0; S.ctl = { roll: 0, pitch: 0, yaw: 0 }; return; }
    const k = 1 - Math.exp(-dt / 0.4);
    S.rr += (((D.roll || 0) - S.last.roll) / dt - S.rr) * k;
    S.pr += (((D.pitch || 0) - S.last.pitch) / dt - S.pr) * k;
    S.yr += (wrapPi(h - S.last.h) / dt - S.yr) * k;
    S.last = { roll: D.roll || 0, pitch: D.pitch || 0, h };
    const roll = clamp(S.rr * 1.2, -0.35, 0.35), pitch = clamp(S.pr * 3, -0.35, 0.35);
    let yaw;
    // on the ground: the nose-wheel steering angle for the turn rate (atan(rate x wheelbase / speed), full pedal at 0.5 rad);
    // standing still, the pedals centre over ~1.5 s
    if (D.ground) { const v = Math.max(D.gs, 0.5), wb = Math.max(1, (T.xMain || 4) - (T.xNose || 1)); yaw = D.gs > 0.3 ? clamp(Math.atan(S.yr * wb / v) / 0.5, -0.6, 0.6) : S.ctl.yaw * Math.exp(-dt / 1.5); }
    else yaw = clamp(0.25 * roll, -0.2, 0.2);
    S.ctl = { roll, pitch, yaw };
  }
  get(key) { return this.map.get(key) || null; }
  modelNote(tr) {
    const T = this.dimsOf(tr);
    if (T && hasModel(T.type)) { const v = this.map.get(tr.key);
      return `Drawn with the detailed ${T.type} model (${MODELS[T.type].note}); gear, flaps, propeller and lights follow the drawn motion by rule [inferred]${v && v.error ? ' - model failed to load, placeholder shown' : ''}`; }
    return dimsNote(T);
  }
  dispose() { for (const v of this.map.values()) { this.scene.remove(v); v.dispose(); } this.map.clear(); this.drv.clear(); }
}
