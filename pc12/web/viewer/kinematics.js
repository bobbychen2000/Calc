// Movable parts driven by the pivot extras in the GLB.
//
// Axes: pivot.origin / pivot.axis are glTF axes (X = butt line, Y = water line, Z = station).
// Some brace / flap fields are stored in MODEL axes (x = station, y = butt line, z = water line) and
// are converted with gl = (y, z, x).  All rotations are right-handed about the stored axis, applied
// to the part node about its own origin (the mesh vertices are relative to the pivot).
import * as THREE from 'three';

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

const PROP_BLUR_RPM = 300;
const DISC_R = 1.34;          // blur disc radius (m), just outside the 2.67 m prop tips
const RING_R = 1.2725;        // mid radius of the light tip ring

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

    // commanded targets and current (smoothed) values
    this.t = { flaps: 0, rpm: 0, pitch: 0, roll: 0, pitchCmd: 0, yaw: 0, stabTrim: 0, ailTrim: 0, rudTrim: 0,
      door_airstair: 0, door_cargo: 0 };
    this.c = { ...this.t, propAngle: 0 };
    // gear: pos 0 = down .. 1 = up; door 0 = closed .. 1 = open (nose clamshells).  The nose doors hang open
    // whenever the gear is down or travelling and close only once it is locked up (photo s/n 3001); the GLB
    // builds them open (pivot.rest = 1), so the rest pose is gear down, doors open.
    this.gear = { pos: 0, door: 1, target: 0, run: null };
    this.defl = {};   // current surface deflections in degrees (for readouts / tests)
    this._makePropDisc();
    this.apply();
  }

  // translucent blurred disc for a fast-turning propeller (cheap motion blur): a dark disc whose
  // alpha comes from an opaque greyscale canvas (alphaMap, no premultiplied-alpha surprises) plus
  // a light ring where the white blade tips sweep.  When the blades are pushed out radially (explode
  // or build fly-in) the disc grows and its alpha is remapped radially (uPush) so the blurred band
  // stays on the blades instead of on the empty hub gap.
  _makePropDisc() {
    const prop = this.surf.propeller;
    if (!prop) return;
    const cv = document.createElement('canvas');
    cv.width = cv.height = 256;
    const g = cv.getContext('2d');
    g.fillStyle = '#000';
    g.fillRect(0, 0, 256, 256);
    const grd = g.createRadialGradient(128, 128, 0, 128, 128, 128);
    grd.addColorStop(0.0, '#000');
    grd.addColorStop(0.14, '#000');
    grd.addColorStop(0.2, 'rgb(200,200,200)');
    grd.addColorStop(0.7, 'rgb(135,135,135)');
    grd.addColorStop(0.9, 'rgb(105,105,105)');
    grd.addColorStop(0.93, '#000');
    grd.addColorStop(1.0, '#000');
    g.fillStyle = grd;
    g.fillRect(0, 0, 256, 256);
    const alpha = new THREE.CanvasTexture(cv);
    const common = { transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide, fog: false };
    const disc = new THREE.Group();
    const discMat = new THREE.MeshBasicMaterial({ ...common, color: 0x17181a, alphaMap: alpha });
    this.discU = { uPush: { value: 0 }, uR1: { value: DISC_R } };
    discMat.onBeforeCompile = (sh) => {
      Object.assign(sh.uniforms, this.discU);
      sh.fragmentShader = 'uniform float uPush;\nuniform float uR1;\n' + sh.fragmentShader.replace('#include <alphamap_fragment>', `{
    vec2 dd = vAlphaMapUv - 0.5;
    float rr = length(dd) * 2.0;                 // 0..1 across the (scaled) disc
    float rho0 = rr * uR1 - uPush;               // radius (m) on the unexploded disc
    vec2 uv0 = 0.5 + dd / max(rr, 1e-5) * (0.5 * rho0 / ${DISC_R.toFixed(3)});
    diffuseColor.a *= rho0 < 0.0 ? 0.0 : texture2D(alphaMap, uv0).g;
  }`);
    };
    discMat.customProgramCacheKey = () => 'pc12:propdisc';
    disc.add(new THREE.Mesh(new THREE.CircleGeometry(DISC_R, 72), discMat));
    disc.add(new THREE.Mesh(new THREE.RingGeometry(1.225, 1.32, 72), new THREE.MeshBasicMaterial({ ...common, color: 0xe6e6e0 })));
    disc.position.set(0, 0, 0.02);   // blade pitch-axis plane, relative to the hub origin
    for (const m of disc.children) { m.renderOrder = 3; m.raycast = () => {}; }
    disc.visible = false;
    prop.rec.node.add(disc);
    this.disc = disc;
    const b1 = this.model.part('blade_1');
    this.bladeRec = b1;
    this.bladePush = b1 ? b1.explode.length() : 0;    // radial explode of each blade (m at f = 1)
    this.push = 0;
  }

  // radial offset of the blades (explode factor + build fly-in) -> disc size and alpha remap
  setExplodeView(f) {
    if (!this.disc) return;
    const b = this.bladeRec;
    const e = this.bladePush * (f + (b && b.fly > 0 && !b.grow ? 3 * b.fly : 0));
    if (e === this.push) return;
    this.push = e;
    this.discU.uPush.value = e;
    this.discU.uR1.value = DISC_R + e;
    this.disc.children[0].scale.setScalar((DISC_R + e) / DISC_R);
    this.disc.children[1].scale.setScalar((RING_R + e) / RING_R);
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

  setProp({ rpm, pitch, angle } = {}, instant) {
    if (angle != null) this.c.propAngle = +angle;          // spin phase (radians), e.g. 0 for tests
    if (rpm != null) this.t.rpm = clamp(+rpm, 0, 1700);
    if (pitch != null) this.t.pitch = clamp(+pitch, -38, 62);
    if (instant) { this.c.rpm = this.t.rpm; this.c.pitch = this.t.pitch; }
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
    approach('pitch', 35);
    lag('roll', 7, 1e-3); lag('pitchCmd', 7, 1e-3); lag('yaw', 7, 1e-3);
    approach('stabTrim', 1.2); approach('ailTrim', 6); approach('rudTrim', 6);
    lag('rpm', 1.1, 0.5);
    const movedBeforeSpin = moved;
    if (c.rpm > 0) {
      c.propAngle = (c.propAngle + (c.rpm / 60) * 2 * Math.PI * dt) % (2 * Math.PI);
      moved = true;
    }
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
    // doors (open angle in radians), eased
    for (const id of ['door_airstair', 'door_cargo']) {
      const s = S[id];
      if (!s) continue;
      const a = s.pv.open * smooth(c[id]);
      s.angle = a / DEG;
      s.rec.anim.quat.setFromAxisAngle(s.axis, a);
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
      if (this.disc) {
        const f = clamp((c.rpm - PROP_BLUR_RPM) / 900, 0, 1);
        this.disc.children[0].material.opacity = 0.8 * f;
        this.disc.children[1].material.opacity = 0.45 * f;
        this.disc.visible = f > 0.01 && S.propeller.rec.shown;
      }
    }
  }
}
