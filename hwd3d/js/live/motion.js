// Motion primitives of the HWD traffic engine (hwd3d Phase 2, fix round 1; new file, P3 package). Node-pure, no imports.
//
// Why (review of Phase 2, docs/phase2_run.md section 6): the kinematic bodies of traffic.js FOLLOW a target with bounded
// acceleration and turn rate. Where the target itself was not drivable - a taxi route taken at 23 kt through a 115-deg
// corner, a take-off roll that restarted from 0 kt under an aircraft rolling at 58 kt, a Hermite across a 46-s air hole
// whose middle ran at 1.5 x the reported speed - the body fell behind and was re-placed (a 0.4-s fade, i.e. a visual
// teleport). The primitives below make the TARGET physically drivable, so the body can follow it without a cut:
//
//   polyOf(pts)                      -> { pts, cum, len }       polyline with cumulative arc length
//   polyAt(R, s)                     -> { x, z, ux, uz }        point and unit tangent at arc length s
//   filletPath(pts, r, ok)           -> pts                     corners rounded with radius <= r (arcs every <= 10 deg);
//                                                               `ok(x, z, tx, tz)` (tangent) rejects an arc point (a wheel
//                                                               off pavement / in a
//                                                               building) and the radius is halved down to 1 m; turns
//                                                               above 150 deg (a turn-around) stay sharp (pivot there)
//   profilePath(R, D, v0, v1, opt)   -> profile                 a speed profile along R that starts at v0, ends at v1 and
//                                                               respects corner speeds (v <= sqrt(lat * r), v <= w * r),
//                                                               per-section caps and the accel / brake limits, timed to
//                                                               take D seconds: slack is taken by a lower cruise speed
//                                                               (not below vTyp; both ends moving: down to max(vCont, half
//                                                               the slower end speed)) and then by one stop (wait); a path that
//                                                               cannot be driven in D (tmin > D) is reported (feasible)
//   profAt(P, t)                     -> { s, v }                arc length and speed at time t in [0, D]
//   geoHermite(p0, d0, s0, p1, d1, s1, D)                       an air-hole curve: the Hermite SHAPE between two fixes with
//                                                               the reported directions d0 / d1 (unit), its tangent scale
//                                                               chosen so that the curve length is what the reported
//                                                               speeds s0 / s1 fly in D, travelled by arc length with the
//                                                               end speeds -> .at(t) = { x, z, vx, vz, s, v }
// All limits are passed in by the caller (traffic.js LIM, every value [inf]).
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const wrapPi = (a) => { a = (a + Math.PI) % (2 * Math.PI); if (a < 0) a += 2 * Math.PI; return a - Math.PI; };

export function polyOf(pts) {
  const P = [pts[0]]; for (const p of pts.slice(1)) if (Math.hypot(p[0] - P[P.length - 1][0], p[1] - P[P.length - 1][1]) > 0.05) P.push(p);
  if (P.length === 1) P.push([P[0][0] + 1e-3, P[0][1]]);
  const cum = [0]; for (let q = 1; q < P.length; q++) cum.push(cum[q - 1] + Math.hypot(P[q][0] - P[q - 1][0], P[q][1] - P[q - 1][1]));
  return { pts: P, cum, len: cum[cum.length - 1] };
}
export function polyAt(R, s) {
  const c = R.cum; s = clamp(s, 0, R.len); let lo = 0, hi = c.length - 1;
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (c[m] <= s) lo = m; else hi = m; }
  const a = R.pts[lo], b = R.pts[hi], l = c[hi] - c[lo] || 1e-9, u = (s - c[lo]) / l;
  return { x: a[0] + (b[0] - a[0]) * u, z: a[1] + (b[1] - a[1]) * u, ux: (b[0] - a[0]) / l, uz: (b[1] - a[1]) / l };
}

// ---------------------------------------------------------------- corners
export function filletPath(pts, r, ok = null) {
  if (pts.length < 3 || !(r > 0)) return pts.slice();
  const out = [pts[0]];
  for (let k = 1; k < pts.length - 1; k++) {
    const A = out[out.length - 1], B = pts[k], C = pts[k + 1];
    const ax = B[0] - A[0], az = B[1] - A[1], bx = C[0] - B[0], bz = C[1] - B[1];
    const la = Math.hypot(ax, az), lb = Math.hypot(bx, bz);
    if (la < 1e-6 || lb < 1e-6) { out.push(B); continue; }
    const th = Math.abs(wrapPi(Math.atan2(bx, -bz) - Math.atan2(ax, -az)));
    if (th < 3 * Math.PI / 180 || th > 150 * Math.PI / 180) { out.push(B); continue; }
    const tn = Math.tan(th / 2);
    let rr = Math.min(r, 0.45 * Math.min(la, lb) / tn);
    let arc = null;
    for (let it = 0; it < 5 && rr >= 1; it++, rr /= 2) {
      const t = rr * tn; const P0 = [B[0] - ax / la * t, B[1] - az / la * t], P1 = [B[0] + bx / lb * t, B[1] + bz / lb * t];
      // arc centre: from P0 along the inward normal
      const cr = ax * bz - az * bx > 0 ? 1 : -1;      // turn sign (z-south frame: cross > 0 = turn to the left? either way consistent)
      const nx = -az / la * cr, nz = ax / la * cr; const Cx = P0[0] + nx * rr, Cz = P0[1] + nz * rr;
      const a0 = Math.atan2(P0[1] - Cz, P0[0] - Cx), a1 = Math.atan2(P1[1] - Cz, P1[0] - Cx);
      const da = wrapPi(a1 - a0); const m = Math.max(2, Math.ceil(Math.abs(da) / (10 * Math.PI / 180)));
      const pts2 = []; let good = true;
      for (let q = 0; q <= m; q++) { const an = a0 + da * q / m; const p = [Cx + Math.cos(an) * rr, Cz + Math.sin(an) * rr]; const tx = -Math.sin(an) * Math.sign(da), tz = Math.cos(an) * Math.sign(da); if (ok && q > 0 && q < m && !ok(p[0], p[1], tx, tz)) { good = false; break; } pts2.push(p); }
      if (good) { arc = pts2; break; }
    }
    if (arc) for (const p of arc) out.push(p); else out.push(B);
  }
  out.push(pts[pts.length - 1]);
  return out;
}

// ---------------------------------------------------------------- ground speed profile
// opt: { acc, dec, lat, w (rad/s), pivotW (rad/s), cap(s) -> m/s, vTyp (cruise floor before a stop is added), vCont (round 4),
//        lu: { len (m), lat (m/s2), w (rad/s), vmax (m/s) } (round 4 iteration 2: a line-up section at the end of the path) }
export function profilePath(R, D, v0, v1, opt) {
  const L = Math.max(R.len, 1e-3), n = Math.max(3, Math.min(1200, Math.ceil(L / 1.0) + 1)), h = L / (n - 1);
  const S = new Float64Array(n), cap = new Float64Array(n), dwell = new Float64Array(n);
  const hd = new Float64Array(n);
  for (let i = 0; i < n; i++) { S[i] = i * h; const p = polyAt(R, Math.min(L, S[i] + 1e-6)); hd[i] = Math.atan2(p.ux, -p.uz); }
  const w = Math.max(2, 2 * h), wi = Math.max(1, Math.round(w / h));
  const rr = new Float64Array(n); let iM = -1;   // local radius; iM: the first sample of a line-up section (the speed only falls from there)
  for (let i = 0; i < n; i++) {
    const a = Math.max(0, i - wi), b = Math.min(n - 1, i + wi);
    const dth = Math.abs(wrapPi(hd[b] - hd[a])), span = (b - a) * h || h;
    const r = dth > 1e-3 ? span / dth : 1e6;
    cap[i] = Math.min(opt.cap ? opt.cap(S[i]) : 10, Math.sqrt(opt.lat * r), opt.w * r);
    rr[i] = r;
  }
  // (round 4 iteration 2, F2) a LINE-UP section (a taxi onto the runway for a take-off): from the first turning sample (radius < 60 m)
  // of the last opt.lu.len m of the path to its end - the turn onto the runway and whatever bends follow it. There: gentler corner speeds
  // (lateral opt.lu.lat, turn rate opt.lu.w), at most opt.lu.vmax, and (run below) a speed that never rises again - case S turned 85 deg
  // onto 28L at 10-14 kt with ~2 m/s2 lateral and a speed sawtooth
  if (opt.lu) {
    for (let k = 0; k < n; k++) if (S[k] >= L - opt.lu.len && rr[k] < 60) { iM = k; break; }
    if (iM >= 0) for (let k = iM; k < n; k++) { const r = rr[k]; cap[k] = Math.min(cap[k], Math.sqrt(opt.lu.lat * r), opt.lu.w * r, opt.lu.vmax); }
  }
  // turn-arounds (sharp vertices > 150 deg kept by filletPath): stop and pivot there
  for (let k = 1; k < R.pts.length - 1; k++) {
    const A = R.pts[k - 1], B = R.pts[k], C = R.pts[k + 1];
    const th = Math.abs(wrapPi(Math.atan2(C[0] - B[0], -(C[1] - B[1])) - Math.atan2(B[0] - A[0], -(B[1] - A[1]))));
    if (th > 150 * Math.PI / 180) { const i = clamp(Math.round(R.cum[k] / h), 0, n - 1); cap[i] = 0; dwell[i] += th / opt.pivotW; }
  }
  const start = Math.max(0, v0), end = Math.max(0, v1);
  const run = (vc, stopAt) => {
    const v = new Float64Array(n);
    for (let i = 0; i < n; i++) {
      let c = cap[i];
      if (vc != null) c = Math.min(c, Math.max(vc, Math.sqrt(Math.max(0, start * start - 2 * opt.dec * S[i])), Math.sqrt(Math.max(0, end * end - 2 * opt.acc * (L - S[i])))));
      if (stopAt === i) c = 0;
      v[i] = c;
    }
    v[0] = Math.min(Math.max(v[0], start), start); v[n - 1] = Math.min(v[n - 1], end);
    for (let i = 1; i < n; i++) v[i] = Math.min(v[i], Math.sqrt(v[i - 1] * v[i - 1] + 2 * opt.acc * h));
    for (let i = n - 2; i >= 0; i--) v[i] = Math.min(v[i], Math.sqrt(v[i + 1] * v[i + 1] + 2 * opt.dec * h));
    // (F2) monotonic line-up: from the first turn of the line-up section on, the speed never rises again (only lowers values, so the
    // acceleration / braking limits above still hold)
    if (iM >= 0) for (let i = Math.max(iM, stopAt) + 1; i < n; i++) v[i] = Math.min(v[i], v[i - 1]);
    let T = 0; const tA = new Float64Array(n);
    for (let i = 1; i < n; i++) { T += dwell[i - 1]; T += 2 * h / Math.max(0.05, v[i - 1] + v[i]); tA[i] = T; }
    T += dwell[n - 1];
    return { v, tA, T };
  };
  const base = run(null, -1);
  const out = { R, D, S, h, n, dwell, startErr: start - base.v[0], tmin: base.T, feasible: base.T <= D * 1.15 };
  let pr = base;
  if (base.T < D) {
    // slack: lower cruise speed first (not below vTyp), then one stop
    // (round 4, E7: when BOTH ends move (> 1 m/s) the cruise may go down to half the slower end speed, >= opt.vCont (1.5 m/s) - a
    // continuous taxi that fits the two fixes is preferred to a stop in the middle of the hole: case S stopped for ~16 s inside a
    // 48-s hole whose two fixes both moved at 6-9 kt, nobody within 81 m) [inf: 0.5, 1.5 m/s]
    const vMax = Math.max(...base.v), vC = start > 1 && end > 1 ? Math.max(opt.vCont ?? 1.5, 0.5 * Math.min(start, end)) : Infinity, vTyp = Math.min(opt.vTyp ?? 4, vMax, vC);
    const tTyp = run(vTyp, -1);
    if (tTyp.T >= D) {
      let lo = vTyp, hi = vMax;
      for (let it = 0; it < 30; it++) { const m = (lo + hi) / 2; if (run(m, -1).T > D) lo = m; else hi = m; }
      pr = run(hi, -1);
    } else {
      // where to stop: at the start if v0 is (nearly) zero, at the end if v1 is, else at the slowest interior point
      let k;
      if (start < 0.5) k = 0;
      else if (end < 0.5) k = n - 1;
      // (F2: never inside a line-up section - the speed there only falls - but before it)
      else { const iEnd = iM > 1 ? iM : n - 1; let bi = Math.floor(iEnd / 2), bv = 1e9; for (let i = 1; i < iEnd; i++) if (cap[i] < bv - 1e-6) { bv = cap[i]; bi = i; } k = bi; }
      const pr2 = run(vTyp, k); const extra = Math.max(0, D - pr2.T); dwell[k] += extra; pr = run(vTyp, k);
      out.stop = { i: k, s: S[k], dur: extra };
    }
  }
  out.v = pr.v; out.tA = pr.tA; out.T = pr.T; out.scale = pr.T > 0 ? pr.T / D : 1;
  return out;
}
export function profAt(P, t) {
  const tt = clamp(t, 0, P.D) * P.scale; const { v, tA, dwell, S, h, n } = P;
  let lo = 0, hi = n - 1; while (hi - lo > 1) { const m = (lo + hi) >> 1; if (tA[m] <= tt) lo = m; else hi = m; }
  // within the dwell at lo?
  const dep = tA[lo] + dwell[lo];
  if (tt < dep) return { s: S[lo], v: 0 };
  if (lo >= n - 1) return { s: S[n - 1], v: v[n - 1] };
  const tau = Math.min(tt - dep, tA[lo + 1] - dep), a = (v[lo + 1] * v[lo + 1] - v[lo] * v[lo]) / (2 * h);
  let s, vv;
  if (Math.abs(a) < 1e-6) { s = S[lo] + v[lo] * tau; vv = v[lo]; }
  else { s = S[lo] + v[lo] * tau + 0.5 * a * tau * tau; vv = v[lo] + a * tau; }
  return { s: Math.min(S[lo + 1], Math.max(S[lo], s)), v: Math.max(0, vv * P.scale) };   // d s / d t_real = v_profile * scale
}

// ---------------------------------------------------------------- air-hole curve
export function geoHermite(p0, d0, s0, p1, d1, s1, D) {
  const ch = Math.hypot(p1[0] - p0[0], p1[1] - p0[1]) || 1e-3;
  const sm = Math.max(1e-3, (s0 + s1) / 2), w0 = s0 / sm, w1 = s1 / sm;
  const pt = (k, u) => { const u2 = u * u, u3 = u2 * u, h00 = 2 * u3 - 3 * u2 + 1, h10 = u3 - 2 * u2 + u, h01 = -2 * u3 + 3 * u2, h11 = u3 - u2;
    return [h00 * p0[0] + h10 * k * w0 * d0[0] + h01 * p1[0] + h11 * k * w1 * d1[0], h00 * p0[1] + h10 * k * w0 * d0[1] + h01 * p1[1] + h11 * k * w1 * d1[1]]; };
  const len = (k, m = 32) => { let L = 0, q = pt(k, 0); for (let j = 1; j <= m; j++) { const r = pt(k, j / m); L += Math.hypot(r[0] - q[0], r[1] - q[1]); q = r; } return L; };
  const Ld = D * sm;
  let k = ch; const Lnat = len(ch);
  if (Ld < Lnat) { let lo = 0.25 * ch, hi = ch; if (len(lo) < Ld) { for (let it = 0; it < 18; it++) { const m = (lo + hi) / 2; if (len(m) < Ld) lo = m; else hi = m; } k = (lo + hi) / 2; } else k = lo; }
  else if (Ld > Lnat) { let lo = ch, hi = Math.max(ch, 1.6 * Ld); if (len(hi) > Ld) { for (let it = 0; it < 20; it++) { const m = (lo + hi) / 2; if (len(m) > Ld) hi = m; else lo = m; } k = (lo + hi) / 2; } else k = hi; }
  // arc-length table
  const M = 64, U = new Float64Array(M + 1), Ls = new Float64Array(M + 1); let q = pt(k, 0);
  for (let j = 1; j <= M; j++) { const r = pt(k, j / M); Ls[j] = Ls[j - 1] + Math.hypot(r[0] - q[0], r[1] - q[1]); U[j] = j / M; q = r; }
  const Lc = Ls[M];
  // speed along the curve: linear from s0 to s1 plus a flat-topped correction (ramps of RAMP x D) that makes the length Lc -
  // the excess over the reported speeds is spread over the hole instead of peaking in its middle (a cubic would put 1.5 x
  // the mean excess there)
  const RAMP = 0.15, a0 = Math.min(s0, 2.1 * Lc / D), a1 = Math.min(s1, 2.1 * Lc / D);
  const wU = (u) => Math.min(1, u / RAMP, (1 - u) / RAMP);
  const E = (Lc / D - (a0 + a1) / 2) / (1 - RAMP);
  const vU = (u) => Math.max(0.3 * Math.min(a0, a1), a0 + (a1 - a0) * u + E * wU(u));
  const NS = 96, SU = new Float64Array(NS + 1); for (let j = 1; j <= NS; j++) SU[j] = SU[j - 1] + D / NS * 0.5 * (vU((j - 1) / NS) + vU(j / NS));
  const sc = SU[NS] > 0 ? Lc / SU[NS] : 1;
  const at = (t) => {
    const u = clamp(t / D, 0, 1), jf = u * NS, j0 = Math.min(NS - 1, Math.floor(jf)), fr = jf - j0;
    const v = vU(u) * sc, s = (SU[j0] + (SU[j0 + 1] - SU[j0]) * fr) * sc;
    let lo = 0, hi = M; const ss = clamp(s, 0, Lc); while (hi - lo > 1) { const m = (lo + hi) >> 1; if (Ls[m] <= ss) lo = m; else hi = m; }
    const f = (ss - Ls[lo]) / ((Ls[hi] - Ls[lo]) || 1e-9), uu = U[lo] + (U[hi] - U[lo]) * f;
    const P = pt(k, uu), P2 = pt(k, Math.min(1, uu + 1e-3)), P1 = pt(k, Math.max(0, uu - 1e-3));
    const tx = P2[0] - P1[0], tz = P2[1] - P1[1], tl = Math.hypot(tx, tz) || 1e-9;
    return { x: P[0], z: P[1], vx: tx / tl * v, vz: tz / tl * v, s, v };
  };
  return { at, len: Lc, k, chord: ch, Ld };
}

// ---------------------------------------------------------------- turn-limited flight path (fix round 2)
// geoHermite can turn far tighter than an aircraft does when the two reported directions differ a lot (downwind -> final:
// a 180-deg hairpin of < 100 m radius; the kinematic body swung wide by 300-700 m and was re-placed). The maximum curvature
// of the Hermite shape is checked (hermiteMaxCurv); above 1 / rMin the hole is flown as a Dubins path instead:
//   dubinsCSC(p0, d0, p1, d1, r)            -> { pts, len }   shortest turn-straight-turn path (LSL, RSR, LSR, RSL) of radius r
//                                                            from p0 heading d0 (unit) to p1 heading d1 (world x east, z south)
//   turnFlight(p0, d0, s0, p1, d1, s1, D, r, opt) -> like geoHermite (.at(t) = { x, z, vx, vz, s, v }, .len): the Dubins
//                                                            path, lengthened by a straight on the initial heading (a longer
//                                                            downwind / upwind) until it is as long as the reported speeds fly
//                                                            in D; opt.final = m of straight final into p1 (a landing);
//                                                            opt.initial = m straight on d0 before the first turn (a climb-out)
export function hermiteMaxCurv(G, D, n = 48) {
  let kMax = 0, prev = null, pp = null;
  for (let j = 0; j <= n; j++) { const q = G.at(D * j / n); if (pp && prev) { const a1 = Math.atan2(prev[0] - pp[0], prev[1] - pp[1]), a2 = Math.atan2(q.x - prev[0], q.z - prev[1]), ds = Math.hypot(q.x - prev[0], q.z - prev[1]); if (ds > 0.5) kMax = Math.max(kMax, Math.abs(wrapPi(a2 - a1)) / ds); } pp = prev; prev = [q.x, q.z]; }
  return kMax;
}
export function dubinsCSC(p0, d0, p1, d1, r) {
  // standard frame: X = x, Y = -z (north up, CCW positive)
  const P0 = [p0[0], -p0[1]], P1 = [p1[0], -p1[1]], a0 = Math.atan2(-d0[1], d0[0]), a1 = Math.atan2(-d1[1], d1[0]);
  const ctr = (P, a, s) => [P[0] - s * r * Math.sin(a), P[1] + s * r * Math.cos(a)];   // s = +1 left (CCW), -1 right
  const mod2 = (x) => { x %= 2 * Math.PI; return x < 0 ? x + 2 * Math.PI : x; };
  let best = null;
  for (const s0 of [1, -1]) for (const s1 of [1, -1]) {
    const c0 = ctr(P0, a0, s0), c1 = ctr(P1, a1, s1), vx = c1[0] - c0[0], vy = c1[1] - c0[1], Dd = Math.hypot(vx, vy), phi = Math.atan2(vy, vx);
    let al, L;
    if (s0 === s1) { al = phi; L = Dd; }
    else { if (Dd < 2 * r) continue; const q = Math.asin(clamp(2 * r * s0 / Dd, -1, 1)); al = phi + q; L = Dd * Math.cos(q); }
    const t0 = [c0[0] + s0 * r * Math.sin(al), c0[1] - s0 * r * Math.cos(al)], t1 = [c1[0] + s1 * r * Math.sin(al), c1[1] - s1 * r * Math.cos(al)];
    const A0 = s0 > 0 ? mod2(al - a0) : mod2(a0 - al), A1 = s1 > 0 ? mod2(a1 - al) : mod2(al - a1);
    const tot = r * A0 + Math.max(0, L) + r * A1;
    if (!best || tot < best.tot) best = { tot, s0, s1, c0, c1, t0, t1, A0, A1, a0, al };
  }
  if (!best) return null;
  const pts = [], B = best, push = (X, Y) => pts.push([X, -Y]);
  const arc = (c, s, aStart, A) => { const m = Math.max(1, Math.ceil(A / (5 * Math.PI / 180))); for (let k = 0; k <= m; k++) { const a = aStart + s * A * k / m; push(c[0] + s * r * Math.sin(a), c[1] - s * r * Math.cos(a)); } };
  arc(B.c0, B.s0, B.a0, B.A0); arc(B.c1, B.s1, B.al, B.A1);
  return { pts, len: B.tot };
}
export function turnFlight(p0, d0, s0, p1, d1, s1, D, r, opt = {}) {
  // opt.initial: m flown straight on the initial heading first (a climb-out before the first turn)
  const fin = opt.final || 0, P1f = fin > 0 ? [p1[0] - d1[0] * fin, p1[1] - d1[1] * fin] : p1, e0 = opt.initial || 0;
  const build = (e) => { const S = [p0[0] + d0[0] * (e + e0), p0[1] + d0[1] * (e + e0)]; const C = dubinsCSC(S, d0, P1f, d1, r); if (!C) return null;
    const pts = (e + e0 > 0.5 ? [p0] : []).concat(C.pts); if (fin > 0) pts.push(p1); return pts; };
  const lenOf = (pts) => { let L = 0; for (let k = 1; k < pts.length; k++) L += Math.hypot(pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1]); return L; };
  const Lreq = D * Math.max(1e-3, (s0 + s1) / 2);
  let pts = build(0); if (!pts) return null;
  let L = lenOf(pts);
  if (L < 0.97 * Lreq) {           // time to spare: fly on along the initial heading first (bisection on the extension)
    let lo = 0, hi = Lreq, bestP = pts, bestE = Math.abs(L - Lreq);
    for (let it = 0; it < 30; it++) { const m = (lo + hi) / 2, P = build(m); if (!P) { hi = m; continue; } const Lm = lenOf(P); if (Math.abs(Lm - Lreq) < bestE) { bestE = Math.abs(Lm - Lreq); bestP = P; } if (Lm < Lreq) lo = m; else hi = m; }
    pts = bestP; L = lenOf(pts);
  }
  const R = polyOf(pts);
  // speed: linear from s0 to s1, scaled so that the path is flown in D (k > 1: the data say faster than reported)
  const k = R.len / (D * Math.max(1e-3, (s0 + s1) / 2));
  const at = (t) => { const tt = clamp(t, 0, D), v = k * (s0 + (s1 - s0) * tt / D), s = k * (s0 * tt + (s1 - s0) * tt * tt / (2 * D)); const p = polyAt(R, s); return { x: p.x, z: p.z, vx: p.ux * v, vz: p.uz * v, s, v }; };
  return { at, len: R.len, k, dubins: true };
}
