// Flight/taxi trajectories. All functions return {pos, fwd, pitch, roll, gear, flaps, spoilers, speed, lights}
import { runwayByEnd, stToWorld, GROUND_Y } from '../geo.js';
import { v3, clamp, smooth, smoother, lerp } from '../math.js';

const D2R = Math.PI / 180;
export function runwayFrame(end) {
  const r = runwayByEnd(end);
  const thr = [r.thr[0], GROUND_Y, -r.thr[1]]; const start = [r.from[0], GROUND_Y, -r.from[1]];
  const dir = v3.norm([r.dir[0], 0, -r.dir[1]]); const right = v3.norm(v3.cross(dir, [0, 1, 0]));
  return { thr, start, dir, right, length: r.length, disp: r.disp };
}

// hermite
const herm = (p0, v0, p1, v1, T, t) => { const s = clamp(t / T, 0, 1); const s2 = s * s, s3 = s2 * s; return (2 * s3 - 3 * s2 + 1) * p0 + (s3 - 2 * s2 + s) * v0 * T + (-2 * s3 + 3 * s2) * p1 + (s3 - s2) * v1 * T; };

// Landing: t relative to touchdown (t=0 at main-gear touchdown)
export function landingState(end, t, opts = {}) {
  const F = runwayFrame(end);
  const V = opts.vapp ?? 72; const gs = (opts.glide ?? 3) * D2R; const vs = V * Math.tan(gs);
  const xTD = opts.xTD ?? 430; const hf = opts.flareH ?? 11; const vsTD = 0.7;
  const Tf = 2 * hf / (vs + vsTD); // flare duration
  const pitchApp = (opts.pitchApp ?? 2.4) * D2R, pitchTD = (opts.pitchTD ?? 5.5) * D2R;
  let x, h, pitch, speed, spoilers = 0, gear = 1, flaps = 1, roll = 0;
  if (t < 0) {
    // airborne: constant-ish speed with slight decel in flare
    const decel = 0.6;
    const tt = Math.max(t, -Tf);
    x = xTD + V * t + (t > -Tf ? 0.5 * decel * (t + Tf) * (t + Tf) * 0 : 0);
    speed = V;
    if (t > -Tf) { h = herm(hf, -vs, 0, -vsTD, Tf, t + Tf); pitch = lerp(pitchApp, pitchTD, smoother((t + Tf) / Tf)); }
    else { h = hf + vs * (-Tf - t); pitch = pitchApp; }
    // gentle roll/pitch wobble on approach (turbulence), fading near ground
    const w = clamp(h / 60, 0, 1);
    roll = w * (Math.sin(t * 0.7 + (opts.phase || 0)) * 1.2 + Math.sin(t * 1.9 + 1.3) * 0.4) * D2R;
    pitch += w * Math.sin(t * 0.9 + 0.4) * 0.25 * D2R;
  } else {
    const a = opts.decel ?? 2.3; const vTaxi = 14;
    const tStop = (V - vTaxi) / a;
    if (t < tStop) { x = xTD + V * t - 0.5 * a * t * t; speed = V - a * t; }
    else { x = xTD + V * tStop - 0.5 * a * tStop * tStop + vTaxi * (t - tStop); speed = vTaxi; }
    h = 0;
    // derotation: hold then lower nose over 3s
    pitch = t < 1.6 ? pitchTD : lerp(pitchTD, 0, smoother((t - 1.6) / 3.2));
    spoilers = smooth(0.3, 1.3, t) * (1 - smooth(tStop + 4, tStop + 7, t));
    flaps = 1 - smooth(tStop + 5, tStop + 12, t);
  }
  const pos = v3.add(v3.add(F.thr, v3.mul(F.dir, x)), [0, h, 0]);
  if (opts.offset) { pos[0] += F.right[0] * opts.offset; pos[2] += F.right[2] * opts.offset; }
  return { pos, fwd: F.dir, pitch, roll, gear, flaps, spoilers, speed, h, x, lights: { landing: t < 20, strobe: true, beacon: true, nav: true, taxi: t > 15 } };
}

// Takeoff: t relative to rotation start (Vr)
export function takeoffState(end, t, opts = {}) {
  const F = runwayFrame(end);
  const a = opts.accel ?? 2.1; const Vr = opts.vr ?? 74; const x0 = opts.x0 ?? 40;
  const tR = Vr / a; const xR = x0 + 0.5 * a * tR * tR; // distance at rotation
  const rotRate = (opts.rotRate ?? 3.0) * D2R; const pitchMax = (opts.pitchMax ?? 15) * D2R; const pitchLO = (opts.pitchLO ?? 9) * D2R;
  const tLO = pitchLO / rotRate;
  let x, h = 0, pitch = 0, speed, gear = 1, flaps = 0.45;
  if (t < 0) { const tt = tR + t; const T = Math.max(tt, 0); x = x0 + 0.5 * a * T * T; speed = a * T; pitch = 0; }
  else {
    pitch = Math.min(pitchMax, rotRate * t) ; if (t > 6) pitch = pitchMax - (pitchMax - 13 * D2R) * smooth(6, 14, t);
    speed = Vr + a * 0.8 * t;
    x = xR + Vr * t + 0.4 * a * t * t;
    if (t > tLO) {
      const ta = t - tLO; // airborne time
      const gamma = Math.min(9 * D2R, ta * 2.2 * D2R); // flight path angle ramps
      // integrate climb: approx h = V * sum(sin gamma)
      const g1 = 9 * D2R / (2.2 * D2R); // time to reach full gamma
      if (ta < g1) h = speed * 0.5 * 2.2 * D2R * ta * ta; else h = speed * (0.5 * 2.2 * D2R * g1 * g1 + 9 * D2R * (ta - g1));
      gear = 1 - smooth(tLO + 3.0, tLO + 10.0, t);
      flaps = 0.45 * (1 - smooth(tLO + 25, tLO + 40, t));
    }
  }
  const pos = v3.add(v3.add(F.start, v3.mul(F.dir, x)), [0, h, 0]);
  return { pos, fwd: F.dir, pitch, roll: 0, gear, flaps, spoilers: 0, speed, h, x, lights: { landing: true, strobe: true, beacon: true, nav: true, taxi: false } };
}

// Smooth taxi path: polyline in (s,t) with fillet radius; returns sampler by distance
export class TaxiPath {
  constructor(ptsST, radius = 45, stepM = 1.0) {
    // build filleted polyline
    const P = ptsST.map(p => [p[0], p[1]]); const out = [P[0]];
    for (let i = 1; i < P.length - 1; i++) {
      const a = P[i - 1], b = P[i], c = P[i + 1];
      const d1 = v2n([b[0] - a[0], b[1] - a[1]]), d2 = v2n([c[0] - b[0], c[1] - b[1]]);
      const la = Math.hypot(b[0] - a[0], b[1] - a[1]), lc = Math.hypot(c[0] - b[0], c[1] - b[1]);
      const ang = Math.acos(clamp(d1[0] * d2[0] + d1[1] * d2[1], -1, 1));
      if (ang < 0.02) { out.push(b); continue; }
      let r = radius; let tlen = r * Math.tan(ang / 2); tlen = Math.min(tlen, la * 0.48, lc * 0.48); r = tlen / Math.tan(ang / 2);
      const p1 = [b[0] - d1[0] * tlen, b[1] - d1[1] * tlen], p2 = [b[0] + d2[0] * tlen, b[1] + d2[1] * tlen];
      const n = Math.max(4, Math.ceil(ang * r / 2));
      for (let k = 0; k <= n; k++) { const u = k / n; // quadratic bezier approximates arc
        const q = [(1 - u) * (1 - u) * p1[0] + 2 * u * (1 - u) * b[0] + u * u * p2[0], (1 - u) * (1 - u) * p1[1] + 2 * u * (1 - u) * b[1] + u * u * p2[1]]; out.push(q); }
    }
    out.push(P[P.length - 1]);
    this.pts = out; this.cum = [0];
    for (let i = 1; i < out.length; i++) this.cum.push(this.cum[i - 1] + Math.hypot(out[i][0] - out[i - 1][0], out[i][1] - out[i - 1][1]));
    this.length = this.cum[this.cum.length - 1];
  }
  at(d) {
    d = clamp(d, 0, this.length); let lo = 0, hi = this.cum.length - 1;
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (this.cum[m] <= d) lo = m; else hi = m; }
    const f = (d - this.cum[lo]) / Math.max(1e-6, this.cum[hi] - this.cum[lo]);
    const a = this.pts[lo], b = this.pts[hi];
    const p = [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f];
    // tangent from a wider window for smoothness
    const a2 = this.sample(d - 3), b2 = this.sample(d + 3);
    const dir = v2n([b2[0] - a2[0], b2[1] - a2[1]]);
    return { p, dir };
  }
  sample(d) { d = clamp(d, 0, this.length); let lo = 0, hi = this.cum.length - 1; while (hi - lo > 1) { const m = (lo + hi) >> 1; if (this.cum[m] <= d) lo = m; else hi = m; } const f = (d - this.cum[lo]) / Math.max(1e-6, this.cum[hi] - this.cum[lo]); const a = this.pts[lo], b = this.pts[hi]; return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f]; }
}
const v2n = (v) => { const l = Math.hypot(v[0], v[1]) || 1; return [v[0] / l, v[1] / l]; };

// distance along path as function of time for given speed profile: accelerate/cruise/decelerate to stop at end
export function taxiDistance(t, L, vmax = 8, a = 0.6, dec = 0.5, v0 = null) {
  // starts at speed v0 (default vmax) and decelerates to stop exactly at L
  const vs = v0 ?? vmax;
  const dDec = vmax * vmax / (2 * dec);
  const tCruise = Math.max(0, (L - dDec) / vmax);
  if (t <= tCruise) return { d: vmax * t, v: vmax };
  const tt = t - tCruise; const tStop = vmax / dec;
  if (tt >= tStop) return { d: L, v: 0 };
  return { d: vmax * tCruise + vmax * tt - 0.5 * dec * tt * tt, v: vmax - dec * tt };
}
