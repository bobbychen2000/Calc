// Movable parts driven by the pivot extras in the GLB.
//
// Axes: pivot.origin / pivot.axis are glTF axes (X = butt line, Y = water line, Z = station).
// Some brace / flap fields are stored in MODEL axes (x = station, y = butt line, z = water line) and
// are converted with gl = (y, z, x).  All rotations are right-handed about the stored axis, applied
// to the part node about its own origin (the mesh vertices are relative to the pivot).
import * as THREE from 'three';
import { PropBlur } from './propblur.js';

const DEG = Math.PI / 180;
export const modelToGl = (a) => new THREE.Vector3(a[1], a[2], a[0]);
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const smooth = (t) => t * t * (3 - 2 * t);

// scratch vectors (no per-frame allocation)
const _d = new THREE.Vector3(), _u = new THREE.Vector3(), _p = new THREE.Vector3();
const _a = new THREE.Vector3(), _b = new THREE.Vector3(), _c = new THREE.Vector3();
const _e1 = new THREE.Vector3(), _e2 = new THREE.Vector3();

/**
 * Port of model/brace.py:solve_knee.  Knee K of the two-link chain A-K-B in the plane normal to
 * `axis`; the solution on the side of `bendRef` is chosen.  Like the Python original, D is clamped
 * to L1 + L2 (an unreachable B leaves u un-normalised, exactly as in brace.py).
 */
export function solveKnee(A, B, L1, L2, axis, bendRef, out) {
  _d.subVectors(B, A);
  _d.addScaledVector(axis, -_d.dot(axis));          // project B - A into the plane
  let D = _d.length();
  D = Math.min(D, L1 + L2 - 1e-9);
  _u.copy(_d).divideScalar(Math.max(D, 1e-12));
  const a = (L1 * L1 - L2 * L2 + D * D) / (2 * D);   // distance from A to the chord foot
  const h = Math.sqrt(Math.max(L1 * L1 - a * a, 0));  // knee offset from the A-B line
  _p.crossVectors(axis, _u);
  if (_p.dot(bendRef) < 0) _p.negate();
  return out.copy(A).addScaledVector(_u, a).addScaledVector(_p, h);
}

// signed angle from u to v about unit axis n (both projected into the plane normal to n)
export function signedAngle(u, v, n) {
  _a.copy(u).addScaledVector(n, -u.dot(n));
  _b.copy(v).addScaledVector(n, -v.dot(n));
  _c.crossVectors(_a, _b);
  return Math.atan2(n.dot(_c), _a.dot(_b));
}

// Propeller speed (PT6E-67XP free turbine driving the Hartzell 5-blade; POH NGX / PC-12 PRO): ground idle ~1,000 rpm,
// 1,550 rpm low-speed (quiet cruise) mode, 1,700 rpm take-off / max.  Spool model (rpm / s), a viewer estimate of a
// start and shutdown: on a start the free power turbine -- and the propeller -- stays still (a creep of a few rpm) until
// the gas generator lights off (GasGenerator below, ~2.3 s after the start), then accelerates as the gas generator
// spools up (~12 s from the start to ground idle); the governor moves between governed speeds in ~3 s; after shutdown
// the feathering prop runs down in ~15 s.
export const PROP_RPM = { idle: 1000, cruise: 1550, max: 1700, governed: 900 };   // governed: below it, starting / running down
const GOVERNED = PROP_RPM.governed;
const FEATHERED = 60, UNFEATHER_RPM = 300;     // deg (feather 62), rpm: out of feather on a start (setProp)
const START = { a0: 55, k: 0.14 };            // d rpm / dt = a0 + k rpm while starting (from light-off)
const CREEP = { rpm: 4, tau: 1.5 };           // before light-off: the propeller creeps toward CREEP.rpm (first order)
const STOP = { a0: 25, k: 0.12 };             // d rpm / dt = -(a0 + k rpm) while running down
const GOV = { k: 1.6, up: 320, down: 260 };   // governed: k (target - rpm), rate-limited

export class Kinematics {
  constructor(model) {
    this.model = model;
    const P = (id) => model.part(id);
    const piv = (id) => { const p = P(id); return p && p.ex.pivot; };
    const axisOf = (id) => new THREE.Vector3().fromArray(piv(id).axis).normalize();

    this.surf = {};
    for (const id of ['flap_R', 'flap_L', 'aileron_R', 'aileron_L', 'ail_tab_R', 'ail_tab_L', 'elevator_R', 'elevator_L',
      'rudder', 'rudder_tab', 'stabilizer', 'door_airstair', 'door_cargo', 'gear_main_R', 'gear_main_L', 'gear_nose',
      'gear_door_NR', 'gear_door_NL', 'propeller', 'blade_1', 'blade_2', 'blade_3', 'blade_4', 'blade_5']) {
      const p = P(id);
      if (!p || !p.ex.pivot) continue;
      this.surf[id] = { rec: p, pv: p.ex.pivot, axis: axisOf(id), angle: 0 };
    }
    // Fowler travel is stored in model axes -> glTF
    for (const id of ['flap_R', 'flap_L']) {
      const s = this.surf[id];
      if (s) s.travel = modelToGl(s.pv.travel || [0, 0, 0]);
    }
    // braces: A, B0, K0, bend in model axes -> glTF; B0 moves with the gear node
    this.braces = [];
    for (const id of ['brace_main_R_up', 'brace_main_L_up', 'brace_nose_up']) {
      const up = P(id);
      if (!up) continue;
      const pv = up.ex.pivot;
      const lo = up.children.find((c) => c.ex.pivot && c.ex.pivot.role === 'lower');
      const g = this.surf[pv.gear];
      if (!lo || !g) continue;
      const A = modelToGl(pv.A), B0 = modelToGl(pv.B0), K0 = modelToGl(pv.K0);
      this.braces.push({
        up, lo, gear: g, A, B0, K0, L1: pv.L1, L2: pv.L2,
        axis: new THREE.Vector3().fromArray(pv.axis).normalize(),
        bend: modelToGl(pv.bend),
        gOrigin: new THREE.Vector3().fromArray(g.pv.origin),
        B: new THREE.Vector3(), K: new THREE.Vector3(),
        ua: 0, la: 0,
      });
    }

    // folding children of a door (pivot kind 'fold', e.g. the airstair handrails of model/airstair.py): they follow
    // pivot.follows and unfold by pivot.open (rad) about their own axis over the door-travel window [w0, w1]
    this.folds = [];
    for (const rec of model.list) {
      const pv = rec.ex.pivot;
      if (!pv || pv.kind !== 'fold' || !this.surf[pv.follows]) continue;
      this.folds.push({ rec, pv, axis: new THREE.Vector3().fromArray(pv.axis).normalize(), door: pv.follows,
        w: pv.window || [0, 1], angle: 0 });
    }

    // crew controls (model/flightdeck.py control_pivots, review r2 M4): the yokes roll about their columns and slide
    // fore / aft with the pitch command, the rudder pedals swing about their hanging-arm pivots with the yaw command,
    // the nose-wheel fork ('steer', gear_nose_steer) turns with it while the gear is down
    this.controls = [];
    for (const rec of model.list) {
      const pv = rec.ex.pivot;
      if (!pv || (pv.kind !== 'yoke' && pv.kind !== 'pedal' && pv.kind !== 'steer')) continue;
      this.controls.push({ rec, pv, axis: new THREE.Vector3().fromArray(pv.axis).normalize(),
        pull: pv.travel_pull ? modelToGl(pv.travel_pull) : null, push: pv.travel_push ? modelToGl(pv.travel_push) : null });
    }

    // club tables (model/cabin.py table_parts, review r3 F5): pivot kind 'table' on the outboard leaf (slides out of
    // the ledge fascia by pivot.slide, model axes, over open 0 .. 0.5; built at open 0.5 = pivot.rest, the leaf out)
    // and its child 'table_leaf' (the inboard leaf, built folded under it, unfolds by pivot.fold rad over 0.5 .. 1);
    // the materials are clipped at the fascia plane (model.js), so a stowed table is inside the ledge, unseen
    this.tables = [];
    for (const rec of model.list) {
      const pv = rec.ex.pivot;
      if (!pv || pv.kind !== 'table') continue;
      const lf = rec.children.find((c) => c.ex.pivot && c.ex.pivot.kind === 'table_leaf');
      this.tables.push({ rec, pv, slide: modelToGl(pv.slide || [0, 0, 0]), rest: pv.rest != null ? pv.rest : 0.5,
        leaf: lf || null, leafAxis: lf ? new THREE.Vector3().fromArray(lf.ex.pivot.axis).normalize() : null,
        fold: lf ? lf.ex.pivot.fold : 0 });
    }

    // commanded targets and current (smoothed) values
    this.t = { flaps: 0, rpm: 0, pitch: 0, roll: 0, pitchCmd: 0, yaw: 0, stabTrim: 0, ailTrim: 0, rudTrim: 0,
      door_airstair: 0, door_cargo: 0, table: 0 };
    this.c = { ...this.t, propAngle: 0 };
    // gear: pos 0 = down .. 1 = up; door 0 = closed .. 1 = open (nose clamshells).  The nose doors hang open
    // whenever the gear is down or travelling and close only once it is locked up (photo s/n 3001); the GLB
    // builds them open (pivot.rest = 1), so the rest pose is gear down, doors open.
    this.gear = { pos: 0, door: 1, target: 0, run: null };
    this.defl = {};   // current surface deflections in degrees (for readouts / tests)
    // the spinning propeller's motion blur (propblur.js): blurred disc + spinner band, the solid blades fade out
    this.blur = this.surf.propeller ? PropBlur.create(model, this.surf.propeller.rec) : null;
    this.disc = this.blur ? this.blur.disc : null;
    this.bladeRec = this.model.part('blade_1');
    this.bladePush = this.bladeRec ? this.bladeRec.explode.length() : 0;    // radial explode of each blade (m at f = 1)
    this.push = 0;
    this.gg = new GasGenerator();     // engine sound (sound.js): the gas generator's Ng alongside the propeller spool
    this.apply();
  }

  // radial offset of the blades (explode factor + build fly-in): the blur disc grows with them
  setExplodeView(f) {
    const b = this.bladeRec;
    const e = this.bladePush * (f + (b && b.fly > 0 && !b.grow ? 3 * b.fly : 0));
    if (e === this.push) return;
    this.push = e;
    if (this.blur) this.blur.setPush(e);
  }

  // ------------------------------------------------------------------ commands
  setFlaps(deg, instant) {
    const s = this.surf.flap_R;
    this.t.flaps = clamp(+deg || 0, 0, s ? s.pv.max : 40);
    if (instant) this.c.flaps = this.t.flaps;
  }

  setDoor(id, v, instant) {
    const key = id === 'airstair' ? 'door_airstair' : id === 'cargo' ? 'door_cargo' : id;
    if (!(key in this.t)) throw new Error('unknown door ' + id);
    this.t[key] = clamp(+v || 0, 0, 1);
    if (instant) this.c[key] = this.t[key];
  }

  // club tables: 0 stowed (TTL) .. 0.5 the outboard leaf out .. 1 deployed (inboard leaf unfolded)
  setTable(v, instant) {
    this.t.table = clamp(+v || 0, 0, 1);
    if (instant) this.c.table = this.t.table;
  }

  // a start from feather (no pitch given, the blades feathered, the propeller below the governed range) comes out of
  // feather to fine pitch once it turns UNFEATHER_RPM (the oil pressure the governor needs), as a PT6 / Hartzell does
  setProp({ rpm, pitch, angle } = {}, instant) {
    if (angle != null) this.c.propAngle = +angle;          // spin phase (radians), e.g. 0 for tests
    if (rpm != null) this.t.rpm = clamp(+rpm, 0, PROP_RPM.max);
    if (pitch != null) this.t.pitch = clamp(+pitch, -38, 62);
    this.unfeather = pitch == null && rpm != null && this.t.rpm > 0 && this.t.pitch >= FEATHERED && this.c.rpm < GOVERNED;
    if (instant) {
      this.c.rpm = this.t.rpm;
      if (this.unfeather && this.c.rpm >= UNFEATHER_RPM) { this.t.pitch = 0; this.unfeather = false; }
      this.c.pitch = this.t.pitch;
      this.gg.snap(this.t.rpm, this.c.rpm, this.c.pitch);
    }
  }

  setControls(o = {}, instant) {
    const map = { roll: 'roll', pitch: 'pitchCmd', yaw: 'yaw', stabTrim: 'stabTrim', ailTrim: 'ailTrim', rudTrim: 'rudTrim' };
    const lim = { roll: [-1, 1], pitchCmd: [-1, 1], yaw: [-1, 1], stabTrim: [-4, 2], ailTrim: [-10, 10], rudTrim: [-12, 12] };
    for (const k in map) {
      if (o[k] == null) continue;
      const key = map[k];
      this.t[key] = clamp(+o[k], lim[key][0], lim[key][1]);
      if (instant) this.c[key] = this.t[key];
    }
  }

  // v: 0 = down .. 1 = up, or 'up' / 'down'.  Instant poses put the nose doors open unless the gear is
  // locked up (the sequence never has them closed in transit or with the gear down).
  setGear(v, instant) {
    const x = v === 'up' ? 1 : v === 'down' ? 0 : clamp(+v || 0, 0, 1);
    const g = this.gear;
    g.target = x;
    if (instant) {
      g.pos = x;
      g.door = this.doorTarget();
      g.run = null;
    }
  }

  // nose-door target at the current gear state: closed (0) only when locked up, otherwise open (1)
  doorTarget() {
    const g = this.gear;
    return g.pos >= 1 && g.target >= 1 ? 0 : 1;
  }

  get gearMoving() {
    const g = this.gear;
    return g.pos !== g.target || g.door !== this.doorTarget();
  }

  // ------------------------------------------------------------------ update
  // returns true when anything moved
  update(dt) {
    if (dt <= 0) return false;
    const t = this.t, c = this.c;
    let moved = false;
    const approach = (key, rate) => {           // linear rate (units / s)
      const d = t[key] - c[key];
      if (d === 0) return;
      const step = rate * dt;
      c[key] = Math.abs(d) <= step ? t[key] : c[key] + Math.sign(d) * step;
      moved = true;
    };
    const lag = (key, k, eps) => {              // first-order lag
      const d = t[key] - c[key];
      if (d === 0) return;
      c[key] = Math.abs(d) < eps ? t[key] : c[key] + d * (1 - Math.exp(-k * dt));
      moved = true;
    };
    approach('flaps', 11);                      // ~3.6 s for 0 -> 40 deg
    approach('door_airstair', 0.45);
    approach('door_cargo', 0.5);
    approach('table', 0.5);
    approach('pitch', 35);
    lag('roll', 7, 1e-3); lag('pitchCmd', 7, 1e-3); lag('yaw', 7, 1e-3);
    approach('stabTrim', 1.2); approach('ailTrim', 6); approach('rudTrim', 6);
    this.gg.update(dt, t.rpm, c.pitch);
    // a start: no power on the propeller until light-off (the free turbine); a creep from the compressor's air flow
    if (t.rpm > c.rpm && this.gg.phase === 'start' && !this.gg.lit) {
      const r = c.rpm <= CREEP.rpm ? c.rpm + (CREEP.rpm - c.rpm) * (1 - Math.exp(-dt / CREEP.tau))
        : this._spool(c.rpm, CREEP.rpm, dt);                       // a restart while running down: it keeps slowing
      if (r !== c.rpm) { c.rpm = r; moved = true; }
    } else if (t.rpm !== c.rpm) { c.rpm = this._spool(c.rpm, t.rpm, dt); moved = true; }
    if (this.unfeather && c.rpm >= UNFEATHER_RPM) { t.pitch = 0; this.unfeather = false; }
    const movedBeforeSpin = moved;
    if (c.rpm > 0) {
      c.propAngle = (c.propAngle + (c.rpm / 60) * 2 * Math.PI * dt) % (2 * Math.PI);
      moved = true;
    }
    if (this.blur) this.blur.tick(dt, c.rpm);
    // gear sequence: nose doors open -> gear travels (~4 s, eased) -> doors close once locked UP (they stay open
    // with the gear down)
    const g = this.gear;
    if (g.pos !== g.target) {
      if (g.door < 1) {
        g.door = Math.min(1, g.door + dt / 0.8);
        g.run = null;
      } else {
        if (!g.run || g.run.to !== g.target) g.run = { from: g.pos, to: g.target, s: 0, dur: Math.max(0.3, 4.0 * Math.abs(g.target - g.pos)) };
        const r = g.run;
        r.s = Math.min(1, r.s + dt / r.dur);
        g.pos = r.from + (r.to - r.from) * smooth(r.s);
        if (r.s >= 1) { g.pos = r.to; g.run = null; }
      }
      moved = true;
    } else if (g.door !== this.doorTarget()) {
      // locked up: the doors close; gear down (or stopped between the locks): they open / stay open
      const dT = this.doorTarget();
      g.door = dT > g.door ? Math.min(1, g.door + dt / 0.8) : Math.max(0, g.door - dt / 0.8);
      moved = true;
    }
    this.onlySpin = moved && !movedBeforeSpin && g.pos === g.target && g.door === this.doorTarget();
    if (moved) this.apply();
    return moved;
  }

  // propeller speed one step toward the target: start / governed / run-down laws (see GOVERNED)
  _spool(rpm, target, dt) {
    let r;
    if (target > rpm) {
      r = rpm < GOVERNED ? rpm + (START.a0 + START.k * rpm) * dt
        : rpm + Math.min(GOV.up, GOV.k * (target - rpm) + 2) * dt;
      r = Math.min(r, target);
    } else {
      r = target < GOVERNED || rpm < GOVERNED ? rpm - (STOP.a0 + STOP.k * rpm) * dt
        : rpm - Math.min(GOV.down, GOV.k * (rpm - target) + 2) * dt;
      r = Math.max(r, target);
    }
    return Math.abs(r - target) < 0.05 ? target : r;
  }

  // ------------------------------------------------------------------ pose
  _rot(id, deg) {
    const s = this.surf[id];
    if (!s) return;
    s.angle = deg;
    s.rec.anim.quat.setFromAxisAngle(s.axis, deg * DEG);
  }

  apply() {
    const c = this.c, S = this.surf, D = this.defl;
    // Fowler flaps: rotate about the hinge line AND translate aft/down proportionally
    for (const id of ['flap_R', 'flap_L']) {
      const s = S[id];
      if (!s) continue;
      this._rot(id, c.flaps);
      s.rec.anim.pos.copy(s.travel).multiplyScalar(c.flaps / s.pv.max);
    }
    D.flaps = c.flaps;
    // ailerons: + angle = trailing edge down (both hinge axes point to starboard).
    // Right roll: right aileron up (to range[0] = -20), left aileron down (to range[1] = +15).
    for (const id of ['aileron_R', 'aileron_L']) {
      const s = S[id];
      if (!s) continue;
      const cmd = -s.pv.sign * c.roll;     // + = this aileron trailing edge down
      const [lo, hi] = s.pv.range;
      const d = cmd >= 0 ? cmd * hi : -cmd * lo;
      this._rot(id, d);
      D[id] = d;
      // Flettner geared tab (child of the aileron): gearing x aileron, plus electric trim on the left
      const tabId = id === 'aileron_R' ? 'ail_tab_R' : 'ail_tab_L';
      const ts = S[tabId];
      if (ts) {
        const td = (ts.pv.gearing || 0) * d + (tabId === 'ail_tab_L' ? c.ailTrim : 0);
        this._rot(tabId, td);
        D[tabId] = td;
      }
    }
    // elevators (children of the stabiliser): pull (pitch > 0) = trailing edge up = range[0]
    for (const id of ['elevator_R', 'elevator_L']) {
      const s = S[id];
      if (!s) continue;
      const [lo, hi] = s.pv.range;
      const d = c.pitchCmd >= 0 ? c.pitchCmd * lo : -c.pitchCmd * hi;
      this._rot(id, d);
      D[id] = d;
    }
    // stabiliser incidence: - = leading edge down = nose-up trim (axis points to starboard,
    // hinge at 62 % chord, so a negative rotation lowers the leading edge)
    this._rot('stabilizer', c.stabTrim);
    D.stabilizer = c.stabTrim;
    // rudder: axis runs up the hinge line; + rotation moves the trailing edge to starboard = right yaw
    if (S.rudder) {
      const [lo, hi] = S.rudder.pv.range;
      const d = c.yaw >= 0 ? c.yaw * hi : -c.yaw * lo;
      this._rot('rudder', d);
      D.rudder = d;
      if (S.rudder_tab) {
        const td = (S.rudder_tab.pv.gearing || 0) * d + c.rudTrim;
        this._rot('rudder_tab', td);
        D.rudder_tab = td;
      }
    }
    // yokes (right roll = clockwise as the pilot sees it = + about the forward-pointing column axis; pull = aft),
    // rudder pedals (right rudder: the right-foot pedals forward = - about +BL, gearing -1 for the left-foot ones) and
    // the nose-wheel fork (model judging r1 GR1-07: + about the down-pointing strut axis = nose wheel right, pedal_deg
    // at full rudder, centred as soon as the gear leaves the down lock)
    for (const k of this.controls) {
      if (k.pv.kind === 'yoke') {
        k.rec.anim.quat.setFromAxisAngle(k.axis, c.roll * k.pv.roll_deg * DEG);
        if (k.pull) k.rec.anim.pos.copy(c.pitchCmd >= 0 ? k.pull : k.push).multiplyScalar(Math.abs(c.pitchCmd));
      } else if (k.pv.kind === 'steer') {
        const down = 1 - clamp(this.gear.pos / 0.05, 0, 1);
        k.angle = c.yaw * k.pv.pedal_deg * down;
        k.rec.anim.quat.setFromAxisAngle(k.axis, k.angle * DEG);
      } else {
        k.rec.anim.quat.setFromAxisAngle(k.axis, -(k.pv.gearing || 0) * c.yaw * k.pv.travel_deg * DEG);
      }
    }
    // doors (open angle in radians), eased
    for (const id of ['door_airstair', 'door_cargo']) {
      const s = S[id];
      if (!s) continue;
      const a = s.pv.open * smooth(c[id]);
      s.angle = a / DEG;
      s.rec.anim.quat.setFromAxisAngle(s.axis, a);
    }
    // club tables: slide over open 0 .. 0.5 (rest = built pose), the inboard leaf unfolds over 0.5 .. 1
    for (const tb of this.tables) {
      const o = c.table;
      const fs = smooth(clamp(o / 0.5, 0, 1)), fsr = smooth(clamp(tb.rest / 0.5, 0, 1));
      tb.rec.anim.pos.copy(tb.slide).multiplyScalar(fs - fsr);
      if (tb.leaf) {
        const ff = smooth(clamp((o - 0.5) / 0.5, 0, 1)), ffr = smooth(clamp((tb.rest - 0.5) / 0.5, 0, 1));
        tb.leaf.anim.quat.setFromAxisAngle(tb.leafAxis, tb.fold * (ff - ffr));
      }
    }
    // folding door children (airstair handrails): angle = open x clamp((door fraction - w0) / (w1 - w0)), the door
    // fraction being the eased door angle / its open angle (model/airstair.py fold_fraction / posed)
    for (const f of this.folds) {
      const df = smooth(c[f.door] || 0);
      const k = clamp((df - f.w[0]) / Math.max(f.w[1] - f.w[0], 1e-9), 0, 1);
      f.angle = f.pv.open * k;
      f.rec.anim.quat.setFromAxisAngle(f.axis, f.angle);
    }
    // gear (retract in degrees) and nose clamshell doors (open in degrees)
    const g = this.gear;
    for (const id of ['gear_main_R', 'gear_main_L', 'gear_nose']) if (S[id]) this._rot(id, S[id].pv.retract * g.pos);
    // nose doors: pivot.open = closed -> open angle; the geometry is built at pivot.rest (1 = open)
    for (const id of ['gear_door_NR', 'gear_door_NL']) {
      const s = S[id];
      if (!s) continue;
      const a = s.pv.open * smooth(g.door);
      s.angle = a;
      s.rec.anim.quat.setFromAxisAngle(s.axis, (a - s.pv.open * (s.pv.rest || 0)) * DEG);
    }
    // braces: B follows the gear leg; solve the knee; upper link about A, lower link about the knee
    for (const b of this.braces) {
      const th = b.gear.angle * DEG;
      b.B.copy(b.B0).sub(b.gOrigin).applyAxisAngle(b.gear.axis, th).add(b.gOrigin);
      solveKnee(b.A, b.B, b.L1, b.L2, b.axis, b.bend, b.K);
      // upper-link angle: (K0 - A) -> (K - A)
      b.ua = signedAngle(_e1.subVectors(b.K0, b.A), _e2.subVectors(b.K, b.A), b.axis);
      // lower link is a child of the upper: its own angle is the absolute one, (B0 - K0) -> (B - K),
      // minus the upper's
      const abs = signedAngle(_e1.subVectors(b.B0, b.K0), _e2.subVectors(b.B, b.K), b.axis);
      b.la = abs - b.ua;
      b.up.anim.quat.setFromAxisAngle(b.axis, b.ua);
      b.lo.anim.quat.setFromAxisAngle(b.axis, b.la);
    }
    // propeller spin (axis points forward: + = clockwise seen from the cockpit) and blade pitch
    if (S.propeller) {
      S.propeller.rec.anim.quat.setFromAxisAngle(S.propeller.axis, c.propAngle);
      for (let k = 1; k <= 5; k++) this._rot('blade_' + k, c.pitch);
      // motion blur only with the whole propeller on show (a hidden / isolated blade keeps the solid geometry)
      if (this.blur) this.blur.apply(c.rpm, c.pitch, c.propAngle, S.propeller.rec.shown && this.blur.blades.every((b) => b.shown));
    }
  }
}

// ------------------------------------------------------------------ gas generator (engine sound, sound.js)
// The PT6E-67XP's gas-generator speed Ng (% of 37,468 rpm: the PT6A-60 / -67 series' 100 %, assumed for the -67XP),
// a viewer estimate of a start, a ground run and a shutdown that runs alongside the propeller spool above.  sound.js
// turns it into the compressor whine, the combustion roar, the light-off and the starter / igniter sounds; on screen
// only its light-off counts (the propeller waits for it).  PT6 practice (POH-style start: starter on, fuel at 12-13 % Ng, light-off, starter off at ~50 %):
//   start      starter engaged: Ng toward ~18 % on the starter alone; fuel at 12 % Ng, light-off NG.lightDelay (0.7 s)
//              later (ignition delay, ~2.3 s after the start), then the acceleration to ground idle (~60 % Ng) at
//              <= 6.5 % / s, the starter and the igniters off at 50 %; the propeller starts turning at light-off
//              (Kinematics.update) and both reach ground idle ~12 s after the start
//   running    Ng follows the power the governed propeller absorbs (ngRun: rpm and blade pitch), <= 12 % / s up, 10 down
//   shutdown   a commanded rpm of 0 = fuel off: the flame goes out, Ng runs down at -(0.6 + 0.16 Ng) % / s (~18 s from
//              ground idle, ~20 s from 95 %), as the feathered propeller runs down
export const NG = { idle: 60, max: 101, crank: 18, crankTau: 1.4, fuelAt: 12, lightDelay: 0.7, starterOff: 50,
  startRate: 6.5, k: 0.9, up: 12, down: 10, stop: { a0: 0.6, k: 0.16 }, rpm100: 37468 };

// relative blade loading of the Hartzell on the ground (no forward speed), by blade pitch (deg relative to the modelled
// fine pitch: feather +62, reverse -38): fine pitch 0.45; most near 20 deg (the blades close to the stall); the
// feathered blades edge-on to the flow ~0.05; reverse (beta) 1.0.  An estimate for the sound levels and the power.
const LOAD = [[-38, 1.0], [-20, 0.75], [0, 0.45], [20, 0.85], [40, 0.6], [62, 0.05]];
export function bladeLoad(pitch) {
  const p = clamp(+pitch || 0, LOAD[0][0], LOAD[LOAD.length - 1][0]);
  let i = 0;
  while (i < LOAD.length - 2 && p > LOAD[i + 1][0]) i++;
  const [x0, y0] = LOAD[i], [x1, y1] = LOAD[i + 1];
  return y0 + (y1 - y0) * (p - x0) / (x1 - x0);
}

// absorbed power (0 .. 1 of the full reverse / max power at 1,700 rpm) ~ blade loading x rpm^3, and the Ng that holds
// it: ground idle (1,000 rpm, fine pitch) 60 %, 1,700 rpm at fine pitch ~86 %, 1,700 at 20 deg ~98 %, full reverse 101 %
export function propPower(rpm, pitch) { return bladeLoad(pitch) * Math.pow(Math.max(0, rpm) / PROP_RPM.max, 3); }
const P_IDLE = propPower(PROP_RPM.idle, 0);
export function ngRun(rpm, pitch) {
  if (!(rpm > 0)) return 0;
  const p = Math.max(0, propPower(rpm, pitch) - P_IDLE) / (1 - P_IDLE);
  return NG.idle + (NG.max - NG.idle) * Math.sqrt(Math.min(1, p));
}

export class GasGenerator {
  constructor() {
    this.startN = 0;           // event counters (never reset): starts, light-offs (sound.js plays the light-off as a
    this.lightN = 0;           // one-shot when it counts up)
    this.reset();
  }

  reset() {
    this.ng = 0;               // % of 100 % Ng
    this.phase = 'off';        // off | start | run | rundown
    this.t = 0;                // s since the start was commanded
    this.fuelT = -1;           // start time of fuel flow (s, -1 = none) and of the light-off
    this.lightT = -1;
    this.lit = false;          // a flame in the combustor
    this.comb = 0;             // combustion level 0 .. 1 (first-order: ~0.3 s up at light-off, 0.25 s down at fuel off)
    this.light = 0;            // the light-off transient 0 .. 1 (rise ~0.07 s, decay ~0.7 s): the 'whoomp'
    this.starter = 0;          // starter-generator motoring (0 / 1) and the igniters (0 / 1)
    this.ign = 0;
    this.power = 0;            // 0 .. 1 above ground idle (for the roar)
  }

  // instant poses (Kinematics.setProp(.., instant)): running at the commanded speed, or stopped
  snap(rpmT, rpm, pitch) {
    if (rpmT > 0 && Math.abs(rpm - rpmT) < 1e-6) {
      this.reset();
      Object.assign(this, { phase: 'run', ng: ngRun(rpmT, pitch), lit: true, comb: 1 });
      this.power = this._power();
    } else if (!(rpmT > 0) && !(rpm > 0)) this.reset();
  }

  _power() { return clamp((this.ng - NG.idle) / (NG.max - NG.idle), 0, 1); }

  // rpmT: the commanded propeller speed (0 = shut down: fuel off); pitch: the current blade pitch (deg)
  update(dt, rpmT, pitch) {
    if (!(dt > 0)) return;
    const run = rpmT > 0;
    if (run && (this.phase === 'off' || this.phase === 'rundown')) {
      // a start (also a restart while running down): starter engaged, fuel at 12 % Ng
      Object.assign(this, { phase: 'start', t: 0, fuelT: -1, lightT: -1, lit: false });
      this.startN++;
    } else if (!run && (this.phase === 'start' || this.phase === 'run')) {
      Object.assign(this, { phase: 'rundown', lit: false, fuelT: -1 });
    }
    this.t += dt;
    const step = (target, k, up, down) => {      // rate-limited first order, no overshoot
      const d = target - this.ng, v = Math.min(Math.abs(d) * k, d > 0 ? up : down) * dt;
      this.ng = Math.abs(d) <= v ? target : this.ng + Math.sign(d) * v;
    };
    switch (this.phase) {
      case 'start':
        if (this.fuelT < 0 && this.ng >= NG.fuelAt) this.fuelT = this.t;
        if (this.fuelT >= 0 && this.lightT < 0 && this.t - this.fuelT >= NG.lightDelay) {
          this.lightT = this.t; this.lit = true; this.lightN++;
        }
        if (!this.lit) this.ng += (NG.crank - this.ng) * (1 - Math.exp(-dt / NG.crankTau));   // the starter alone
        else step(NG.idle + 0.5, NG.k, NG.startRate, NG.down);
        if (this.lit && this.ng >= NG.idle - 0.5) this.phase = 'run';
        break;
      case 'run':
        step(ngRun(rpmT, pitch), NG.k, NG.up, NG.down);
        break;
      case 'rundown':
        this.ng -= (NG.stop.a0 + NG.stop.k * this.ng) * dt;
        if (this.ng <= 0) { this.ng = 0; this.phase = 'off'; }
        break;
      default:
        this.ng = 0;
    }
    this.starter = this.phase === 'start' && this.ng < NG.starterOff ? 1 : 0;
    this.ign = this.starter;
    this.comb += ((this.lit ? 1 : 0) - this.comb) * (1 - Math.exp(-dt / (this.lit ? 0.3 : 0.25)));
    if (this.comb < 1e-4 && !this.lit) this.comb = 0;
    // light-off transient: (1 - e^(-s / 0.07)) e^(-s / 0.7), peak-normalised (0.715 at s = 0.168 s)
    const s = this.lightT >= 0 && this.phase !== 'rundown' && this.phase !== 'off' ? this.t - this.lightT : -1;
    this.light = s >= 0 && s < 6 ? (1 - Math.exp(-s / 0.07)) * Math.exp(-s / 0.7) / 0.7152 : 0;
    this.power = this.lit ? this._power() : 0;
  }

  get state() {
    return { ng: this.ng, phase: this.phase, lit: this.lit, comb: this.comb, light: this.light, starter: this.starter,
      ign: this.ign, power: this.power, t: this.t, startN: this.startN, lightN: this.lightN,
      // s since the light-off (-1: none in this run)
      lightAge: this.lightT >= 0 && this.phase !== 'rundown' && this.phase !== 'off' ? this.t - this.lightT : -1 };
  }
}
