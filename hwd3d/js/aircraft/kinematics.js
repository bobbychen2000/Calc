// Aircraft kinematics from the glTF pivot extras (hwd3d Phase 3, M2; new file). Node-pure (tools/models/test_models.mjs
// poses the PC-12 retracted under Node). Works on the AircraftModel of js/aircraft/glb.js: every pivot is already in the
// hwd3d aircraft local frame (+x forward, +y up, +z starboard, origin = main-gear contact) at rest.
//
//   new Kinematics(model)            .pose(state) -> Array(parts.length) of Float32Array(16) (column-major): the motion of
//        each MOVER part (local rest -> local posed; identity for static parts). A part's posed geometry is
//        pose[mover] x rest geometry. Movers are posed parents first (glTF hierarchy), so a tab rides on its aileron and
//        an elevator on the trimming stabiliser.
//   gearSequence(gear) -> { leg, door }    gear 1 = down (locked) .. 0 = up (the GaAircraft field), leg 0 = down .. 1 =
//        retracted (eased), door 0 = closed .. 1 = open for 'transit' doors (open only between the locks)
//   solveKnee(A, B, L1, L2, axis, bendRef) -> K    port of pc12/model/brace.py solve_knee
//   rotAbout(origin, axis, rad) -> m4      right-handed rotation about the line (origin, axis)
//
// Pivot kinds (pc12/CLAUDE.md "Coordinates & conventions"; the SF50 builder uses the same set):
//   spin       rotation about `axis` by state.rotorAng (rad)             (propeller hub / turbofan rotor)
//   pitch      rotation about `axis` by state.bladePitch (deg; `feather` / `reverse` limits)
//   flap       rotation by state.flaps (deg, clamped to `max`) and translation `travel` x flaps / max (Fowler)
//   aileron    + = trailing edge down; cmd = -sign x state.roll (-1..1, + = roll right); d = cmd >= 0 ? cmd x range[1] :
//              -cmd x range[0]  (pc12/web/viewer/kinematics.js)
//   tab        gearing x the parent surface deflection (+ state.ailTrim on the left aileron tab, + state.rudTrim on a
//              rudder tab)
//   elevator   pull (state.pitch > 0) = trailing edge up = range[0]
//   rudder     state.yaw > 0 (right) -> range[1]
//   ruddervator V-tail surface: elevator term as `elevator` plus `side` x yaw term (range limits clamp the sum) [inf: mixing
//              law, the SF50 builder names it]
//   trim       state.stabTrim (deg, range)
//   door       `open` (rad) x state.doors[part id] (0..1, eased)
//   gear       `retract` (deg) x gearSequence(state.gear).leg
//   gear_door  `open` (deg) x door(state.gear) - `seq: 'transit'` (default: open between the locks, closed down and up:
//              pc12 nose clamshells) or `seq: 'down'` (open whenever the leg is out of the well, closed only when up)
//   brace      two-link over-centre strut: upper link about A, lower link about the knee; B = the leg attach point B0
//              carried by the `gear` part's pose; knee solved by solveKnee on the side of `bend`
// Unknown kinds stay at rest and are listed in kin.unsupported.

const DEG = Math.PI / 180;
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const smooth = (t) => { t = clamp(t, 0, 1); return t * t * (3 - 2 * t); };
const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const nrm = (a) => { const l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };

export const ident = () => { const m = new Float32Array(16); m[0] = m[5] = m[10] = m[15] = 1; return m; };
export function mul(a, b) { const o = new Float32Array(16); for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) { let s = 0; for (let k = 0; k < 4; k++) s += a[k * 4 + r] * b[c * 4 + k]; o[c * 4 + r] = s; } return o; }
export const xform = (m, p) => [m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12], m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13], m[2] * p[0] + m[6] * p[1] + m[10] * p[2] + m[14]];
// inverse of a rigid transform applied to a point: R^T (p - t)
export const xformInvRigid = (m, p) => { const q = [p[0] - m[12], p[1] - m[13], p[2] - m[14]]; return [m[0] * q[0] + m[1] * q[1] + m[2] * q[2], m[4] * q[0] + m[5] * q[1] + m[6] * q[2], m[8] * q[0] + m[9] * q[1] + m[10] * q[2]]; };
export const xdir = (m, p) => [m[0] * p[0] + m[4] * p[1] + m[8] * p[2], m[1] * p[0] + m[5] * p[1] + m[9] * p[2], m[2] * p[0] + m[6] * p[1] + m[10] * p[2]];

/** Right-handed rotation by `ang` rad about the line through `o` along unit `a` (Rodrigues), column-major. */
export function rotAbout(o, a, ang, tr = null) {
  const [x, y, z] = nrm(a), c = Math.cos(ang), s = Math.sin(ang), t = 1 - c;
  const m = new Float32Array(16);
  m[0] = c + x * x * t; m[1] = y * x * t + z * s; m[2] = z * x * t - y * s;
  m[4] = x * y * t - z * s; m[5] = c + y * y * t; m[6] = z * y * t + x * s;
  m[8] = x * z * t + y * s; m[9] = y * z * t - x * s; m[10] = c + z * z * t; m[15] = 1;
  // translation o - R o (+ tr)
  m[12] = o[0] - (m[0] * o[0] + m[4] * o[1] + m[8] * o[2]) + (tr ? tr[0] : 0);
  m[13] = o[1] - (m[1] * o[0] + m[5] * o[1] + m[9] * o[2]) + (tr ? tr[1] : 0);
  m[14] = o[2] - (m[2] * o[0] + m[6] * o[1] + m[10] * o[2]) + (tr ? tr[2] : 0);
  return m;
}

/** Port of pc12/model/brace.py solve_knee: knee K of the chain A-K-B in the plane normal to `axis`, on the side of
 *  `bendRef`. Like the original, D is clamped to L1 + L2 (an unreachable B leaves u un-normalised). */
export function solveKnee(A, B, L1, L2, axis, bendRef) {
  const ax = nrm(axis); let d = sub(B, A); const k = dot(d, ax); d = [d[0] - ax[0] * k, d[1] - ax[1] * k, d[2] - ax[2] * k];
  let D = Math.hypot(d[0], d[1], d[2]); D = Math.min(D, L1 + L2 - 1e-9);
  const u = d.map(v => v / Math.max(D, 1e-12));
  const a = (L1 * L1 - L2 * L2 + D * D) / (2 * D), h = Math.sqrt(Math.max(L1 * L1 - a * a, 0));
  let p = cross(ax, u); if (dot(p, bendRef) < 0) p = p.map(v => -v);
  return [A[0] + a * u[0] + h * p[0], A[1] + a * u[1] + h * p[1], A[2] + a * u[2] + h * p[2]];
}
/** Signed angle from u to v about unit n (both projected into the plane normal to n). */
export function signedAngle(u, v, n) {
  const pu = sub(u, n.map(x => x * dot(u, n))), pv = sub(v, n.map(x => x * dot(v, n)));
  return Math.atan2(dot(n, cross(pu, pv)), dot(pu, pv));
}

// Gear cycle as a function of the GaAircraft `gear` field (1 = down .. 0 = up; traffic.js ramps it over 6 s): the doors
// open in the first DOOR_T of the cycle, the legs travel (eased) in between, the doors close in the last DOOR_T. pc12's
// viewer runs 0.8 s doors + 4 s travel [inf: the POH gives no timing]; 0.12 of a 6-s ramp = 0.72 s.
export const DOOR_T = 0.12;
export function gearSequence(gear) {
  const s = clamp(1 - gear, 0, 1);
  return { s, leg: smooth((s - DOOR_T) / (1 - 2 * DOOR_T)), door: smooth(s / DOOR_T) * (1 - smooth((s - (1 - DOOR_T)) / DOOR_T)), doorDown: 1 - smooth((s - (1 - DOOR_T)) / DOOR_T) };
}

export const DEFAULT_STATE = { gear: 1, flaps: 0, rotorAng: 0, bladePitch: 0, roll: 0, pitch: 0, yaw: 0, stabTrim: 0, ailTrim: 0, rudTrim: 0, doors: {} };
const KNOWN = new Set(['spin', 'pitch', 'flap', 'aileron', 'tab', 'elevator', 'rudder', 'ruddervator', 'trim', 'door', 'gear', 'gear_door', 'brace']);

export class Kinematics {
  constructor(model) {
    this.model = model; const P = model.parts;
    this.movers = P.map((p, i) => i).filter(i => P[i].pivot && !P[i].excluded);
    this.unsupported = this.movers.filter(i => !KNOWN.has(P[i].pivot.kind)).map(i => P[i].id + ':' + P[i].pivot.kind);
    // the mover above each mover (pose parent)
    this.up = P.map((p) => { let q = p.parent; while (q >= 0 && !P[q].pivot) q = P[q].parent; return q; });
    this.byId = model.partIndex;
    // braces: upper / lower pairs and their gear
    this.braces = [];
    for (const i of this.movers) { const pv = P[i].pivot; if (pv.kind !== 'brace' || pv.role !== 'upper') continue;
      const lo = this.movers.find(j => P[j].parent === i && P[j].pivot.kind === 'brace' && P[j].pivot.role === 'lower');
      const g = this.byId.get(pv.gear); if (lo == null || g == null) continue;
      this.braces.push({ up: i, lo, gear: g, A: pv.A || pv.origin, B0: pv.B0, K0: pv.K0, L1: pv.L1, L2: pv.L2, axis: nrm(pv.axis), bend: pv.bend }); }
    this.defl = {};   // last deflections (deg) per part id, for readouts / tests
  }
  pose(state = {}) {
    const S = { ...DEFAULT_STATE, ...state }, P = this.model.parts, out = new Array(P.length).fill(null), D = this.defl;
    const seq = gearSequence(S.gear);
    const local = new Array(P.length).fill(null);   // the mover's own motion about its rest pivot
    const angleOf = {};
    for (const i of this.movers) {
      const p = P[i], pv = p.pivot; let ang = 0, tr = null;
      switch (pv.kind) {
        case 'spin': ang = S.rotorAng; break;
        case 'pitch': ang = clamp(S.bladePitch, pv.reverse ?? -90, pv.feather ?? 90) * DEG; break;
        case 'flap': { const mx = pv.max || 40, f = clamp(S.flaps, 0, mx); ang = f * DEG; if (pv.travel) tr = pv.travel.map(v => v * f / mx); break; }
        case 'aileron': { const [lo, hi] = pv.range || [-20, 15]; const cmd = -(pv.sign ?? 1) * clamp(S.roll, -1, 1); ang = (cmd >= 0 ? cmd * hi : -cmd * lo) * DEG; break; }
        case 'elevator': { const [lo, hi] = pv.range || [-20, 15]; const c = clamp(S.pitch, -1, 1); ang = (c >= 0 ? c * lo : -c * hi) * DEG; break; }
        case 'rudder': { const [lo, hi] = pv.range || [-25, 25]; const c = clamp(S.yaw, -1, 1); ang = (c >= 0 ? c * hi : -c * lo) * DEG; break; }
        case 'ruddervator': { const [lo, hi] = pv.range || [-20, 20]; const c = clamp(S.pitch, -1, 1), y = clamp(S.yaw, -1, 1);
          const e = c >= 0 ? c * (pv.pitchRange || pv.range || [lo])[0] : -c * (pv.pitchRange || pv.range || [lo, hi])[1];
          const r = (pv.side ?? 1) * y * (pv.yawGain ?? Math.min(Math.abs(lo), Math.abs(hi)) * 0.5); ang = clamp(e + r, lo, hi) * DEG; break; }
        case 'trim': { const [lo, hi] = pv.range || [-90, 90]; ang = clamp(S.stabTrim, lo, hi) * DEG; break; }
        case 'door': ang = (pv.open || 0) * smooth((S.doors && S.doors[p.id]) || 0); break;
        case 'gear': ang = (pv.retract || 0) * DEG * seq.leg; break;
        case 'gear_door': ang = (pv.open || 0) * DEG * (pv.seq === 'down' ? seq.doorDown : seq.door); break;
        case 'tab': ang = NaN; break;     // after its parent (below)
        case 'brace': ang = NaN; break;
        default: ang = 0;
      }
      angleOf[i] = ang; local[i] = isNaN(ang) ? null : rotAbout(pv.origin, pv.axis, ang, tr);
    }
    // tabs: gearing x parent deflection (+ trim)
    for (const i of this.movers) {
      const pv = P[i].pivot; if (pv.kind !== 'tab') continue;
      const par = this.up[i], pd = par >= 0 && !isNaN(angleOf[par]) ? angleOf[par] / DEG : 0;
      let d = (pv.gearing || 0) * pd;
      const pk = par >= 0 ? P[par].pivot.kind : '';
      if (pk === 'aileron' && (P[par].pivot.sign ?? 1) < 0) d += S.ailTrim;   // electric trim tab on the left aileron (pc12 viewer)
      if (pk === 'rudder') d += S.rudTrim;
      if (pv.range) d = clamp(d, pv.range[0], pv.range[1]);
      angleOf[i] = d * DEG; local[i] = rotAbout(pv.origin, pv.axis, d * DEG);
    }
    // compose parents first (parts are in glTF depth-first order); braces need the gear pose first
    const I = ident();
    const compose = (i) => { if (out[i]) return out[i]; const par = this.up[i]; const Pm = par >= 0 ? compose(par) : I;
      out[i] = local[i] ? mul(Pm, local[i]) : Pm; return out[i]; };
    for (const i of this.movers) if (P[i].pivot.kind !== 'brace') compose(i);
    for (const b of this.braces) {
      const Gp = compose(b.gear), Up0 = this.up[b.up] >= 0 ? compose(this.up[b.up]) : I;
      // work in the frame of the brace's own parent (static airframe for pc12): B in that frame
      const B = xformInvRigid(Up0, xform(Gp, b.B0)); const K = solveKnee(b.A, B, b.L1, b.L2, b.axis, b.bend);
      const ua = signedAngle(sub(b.K0, b.A), sub(K, b.A), b.axis);
      const abs = signedAngle(sub(b.B0, b.K0), sub(B, K), b.axis);
      out[b.up] = mul(Up0, rotAbout(b.A, b.axis, ua));
      out[b.lo] = mul(out[b.up], rotAbout(b.K0, b.axis, abs - ua));
      angleOf[b.up] = ua; angleOf[b.lo] = abs - ua; b.K = K; b.B = B;
    }
    for (const i of this.movers) { if (!out[i]) out[i] = compose(i); D[P[i].id] = angleOf[i] / DEG; }
    return out;
  }
}
