// Scripted cinematic camera of the OD3 videos (hwd3d Phase 3, video). Pure ES module (no DOM, no WebGL): the driver plans
// every frame's camera in Node from the scout trace (the hero's exact per-frame pose from the same engine run - the virtual
// clock makes the render run repeat it), and the page (js/video/director.js) hands the planned camera to the renderer in
// place of the app's CameraRig. Not the app's CameraRig: nothing in js/live is used or changed.
//
//   planCamera({ trace, shots, site, fps, aspect }) -> { cams: [[px, py, pz, tx, ty, tz, fovDeg], ...], report }
//   trace[f] = { valid, x, y, z, hdg (deg true), gs (kt), ground, agl, near: [[x, y, z, r], ...], L, span, ... }
//   shots    = [{ kind, f0, f1 (exclusive), ...params }] covering the frames; a new shot is a deliberate CUT (the smoothing
//              state restarts), within a shot every quantity moves through a critically damped spring (smoothDamp, exact).
// Shot kinds (params, defaults in KIND_DEFAULTS):
//   establish  fixed / slowly drifting wide camera placed relative to the hero at the shot's first frame (anchor 'end': its
//              last frame) (az: bearing from the hero to the camera, deg true; dist, h above ground; drift [east, north] m/s)
//   chase      behind / above the hero in its (smoothed) heading frame: back, up, side (m), lead (m, aim ahead), hdgSmooth (s),
//              leadOn ('smoothed': the aim point ahead along the smoothed heading - camera, hero and aim stay in line, so the
//              camera turns no faster than its heading spring; 'actual': along the hero's own heading - the first version,
//              which whipped the view round in tight time-lapse turns), aimFF (feed the aim spring forward by the rate of
//              its own target, so it does not trail it)
//   dolly      a camera car on a line parallel to a runway centreline: rwy, side ('left'|'right' of the runway direction),
//              off (m from the centreline), h (m above ground), lag (m: along-track position relative to the hero, held:
//              the car's spring is fed forward by the hero's along-track velocity and acceleration), vmax (m/s: the car's
//              top speed - above it the car falls behind and pans), smooth (s)
//   fixed      a fixed point that pans (and zooms within 30-55 deg) to follow the hero: pos [x, y, z] (y may be null: h above
//              ground), or at { rwy, along (m from the runway end), across (m, + right), h } - e.g. the runway edge at the
//              lift-off point taken from the trace; zoom (target hero size as a fraction of the frame height) or fov
//   tower      the tower-cab eye (site.anchors.tower) panning / zooming after the hero
//   hold       keep the previous camera (end card)
// Every kind aims by the rule of thirds: `frame: [sx, sy]` is where the hero's centre should sit in NDC (-1..1; -1/3 is a
// thirds line). Constraints, after smoothing, on every frame: camera >= site.groundY + 1.5 m; never inside a building
// footprint below its roof (raised over it); never within (body radius + 3 m) of any drawn aircraft (pushed out); FOV
// clamped to 30-55 deg (vertical). The report lists per shot: camera height over the ground (min), the largest per-frame
// camera move, the closest aircraft, the hero's screen position (max |NDC|, frames off-screen), building occlusions of the
// line of sight, the closest light unit / windsock (obstacles [x, z, r]), any constraint that acted, and the on-screen motion:
// the hero's screen speed (px / frame) and its change (px / frame^2), the background's pan speed from the camera's rotation
// alone (px / frame at the frame centre), the dolly's lag error (m) and the hero's rest jitter (pose changes while it stands).
const D2R = Math.PI / 180;
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]], add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const mul = (a, s) => [a[0] * s, a[1] * s, a[2] * s], len = (a) => Math.hypot(a[0], a[1], a[2]);
const norm = (a) => { const l = len(a) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const fwdOf = (hdgDeg) => [Math.sin(hdgDeg * D2R), 0, -Math.cos(hdgDeg * D2R)];
const rightOf = (hdgDeg) => [Math.cos(hdgDeg * D2R), 0, Math.sin(hdgDeg * D2R)];
const wrap180 = (a) => ((a + 180) % 360 + 360) % 360 - 180;
export const FOV_MIN = 30, FOV_MAX = 55, CAM_AGL_MIN = 1.5, AC_CLEAR = 3;

/** critically damped spring toward `target` (x'' = -w^2 (x - target) - 2 w x', w = 2 / smoothTime), integrated EXACTLY over dt
 *  with the target held for the step (stable for any dt, no overshoot clamp: Unity's SmoothDamp zeroes the velocity when it
 *  passes a moving target, which stalled a camera car matched to a rolling aircraft); maxSpeed caps the speed (a camera car's
 *  top speed); returns [value, velocity] */
export function smoothDamp(cur, target, vel, smoothTime, dt, maxSpeed = Infinity) {
  const w = 2 / Math.max(1e-4, smoothTime), y0 = cur - target, k = vel + w * y0, e = Math.exp(-w * dt);
  let out = target + (y0 + k * dt) * e, v = (vel - w * k * dt) * e;
  if (Math.abs(v) > maxSpeed) { v = Math.sign(v) * maxSpeed; out = cur + clamp(out - cur, -maxSpeed * dt, maxSpeed * dt); }
  return [out, v];
}
class Spring3 {
  constructor(p) { this.p = p.slice(); this.v = [0, 0, 0]; }
  step(t, st, dt, vmax = Infinity) { for (let i = 0; i < 3; i++) [this.p[i], this.v[i]] = smoothDamp(this.p[i], t[i], this.v[i], st, dt, vmax); return this.p.slice(); }
}
class SpringA {   // an angle (deg), unwrapped toward the target
  constructor(a) { this.a = a; this.v = 0; }
  step(t, st, dt) { const tt = this.a + wrap180(t - this.a); [this.a, this.v] = smoothDamp(this.a, tt, this.v, st, dt); return this.a; }
}
export const KIND_DEFAULTS = {
  establish: { az: 200, dist: 140, h: 35, drift: [0, 0], fov: 40, frame: [0.33, -0.25], aimSmooth: 0.6 },
  chase: { back: 38, up: 13, side: 0, lead: 14, fov: 40, frame: [0, -0.2], hdgSmooth: 0.9, posSmooth: 0.25, aimSmooth: 0.35, leadOn: 'smoothed', aimFF: true },
  dolly: { rwy: '28L', side: 'left', off: 50, h: 2.2, lag: -20, vmax: 45, smooth: 1.2, fov: 40, frame: [-0.3, -0.12], aimSmooth: 0.35, zoom: 0 },
  fixed: { pos: null, at: null, fov: 40, zoom: 0, frame: [0, -0.1], aimSmooth: 0.35, zoomSmooth: 0.8 },
  tower: { fov: 40, zoom: 0, frame: [0, -0.1], aimSmooth: 0.4, zoomSmooth: 0.8 },
  hold: {},
};
/** a camera aim (target point) that puts world point P at NDC (sx, sy) for a camera at C with vertical fov (deg) */
export function thirdsAim(C, P, fovDeg, aspect, sx, sy) {
  const d = sub(P, C), dist = len(d) || 1;
  const yaw = Math.atan2(d[0], -d[2]), pitch = Math.asin(clamp(d[1] / dist, -1, 1));
  const tv = Math.tan(fovDeg * D2R / 2), th = tv * aspect;
  // the hero to the right of centre (sx > 0) -> the camera looks left of it
  const yaw2 = yaw - Math.atan(sx * th), pitch2 = pitch - Math.atan(sy * tv);
  const f = [Math.cos(pitch2) * Math.sin(yaw2), Math.sin(pitch2), -Math.cos(pitch2) * Math.cos(yaw2)];
  return add(C, mul(f, dist));
}
/** NDC of world point P for camera C -> T (fov deg, aspect); null behind the camera */
export function project(C, T, fovDeg, aspect, P) {
  const f = norm(sub(T, C)); const r = norm(cross(f, [0, 1, 0])); const u = cross(r, f); const d = sub(P, C);
  const z = dot(d, f); if (z <= 0.1) return null;
  const tv = Math.tan(fovDeg * D2R / 2); return [dot(d, r) / (z * tv * aspect), dot(d, u) / (z * tv), z];
}
function runwayFrame(site, rwyAxis, name) {
  const A = rwyAxis(name); return { o: [A.origin[0], 0, A.origin[1]], d: [A.dir[0], 0, A.dir[1]], r: [A.right[0], 0, A.right[1]], hdg: A.hdg };
}

export function planCamera({ trace, shots, site, rwyAxis, fps = 30, aspect = 16 / 9, obstacles = [], heightPx = 1080 }) {
  const dt = 1 / fps, gy = (x, z) => site.groundY(x, z), Hp = heightPx, Wp = heightPx * aspect;
  const cams = new Array(trace.length).fill(null); const report = [];
  let last = null;   // last valid hero pose (frames where the hero is not drawn keep it)
  // the hero's velocity in VIDEO time (m per video second: includes the time-lapse factor), central difference on the trace;
  // an absolute aim spring is fed forward by v x smoothTime, the steady lag of a critically damped spring behind a target
  // moving at v, so a panning camera keeps the hero on its framing point instead of trailing it
  let lo = 0, hi = trace.length;   // the current shot's frames: velocities never reach across a cut (a skip in data time)
  const okAt = (f) => f >= lo && f < hi && trace[f] && trace[f].found !== false && trace[f].valid;
  const velAt = (f) => { const a = okAt(f - 1) ? trace[f - 1] : trace[f], b = okAt(f + 1) ? trace[f + 1] : trace[f]; const n = (okAt(f - 1) ? 1 : 0) + (okAt(f + 1) ? 1 : 0);
    if (!n || !a || !b) return [0, 0, 0]; const k = 1 / (n * dt); return [(b.x - a.x) * k, (b.y - a.y) * k, (b.z - a.z) * k]; };
  // a smoother velocity (central difference over +-k valid frames) for the dolly's feed-forward
  const velK = (f, k) => { let a = f - k, b = f + k; while (a < f && !okAt(a)) a++; while (b > f && !okAt(b)) b--; if (b <= a) return [0, 0, 0];
    const A = trace[a], B = trace[b], s = 1 / ((b - a) * dt); return [(B.x - A.x) * s, (B.y - A.y) * s, (B.z - A.z) * s]; };
  let prevCam = null;
  for (const S0 of shots) {
    const S = { ...KIND_DEFAULTS[S0.kind], ...S0 }; const R = { kind: S.kind, name: S.name || S.kind, f0: S.f0, f1: S.f1, frames: S.f1 - S.f0,
      camAglMin: Infinity, fixtureMin: Infinity, stepMax: 0, stepMaxAt: null, relStepMax: 0, acClearMin: Infinity, ndcMax: 0, offScreen: 0, occluded: 0, heroInvalid: 0, raised: 0, pushed: 0, fov: [Infinity, -Infinity],
      heroPxMax: 0, heroPxAt: null, heroAccMax: 0, heroAccAt: null, bgPxMax: 0, bgPxAt: null, bgOver20: 0, lagErrMax: null, lagErrAt: null, carAtVmax: 0, restJitter: 0, restJitterAt: null };
    let st = null, scr1 = null, scr2 = null, dir1 = null; lo = S.f0; hi = S.f1;
    for (let f = S.f0; f < S.f1 && f < trace.length; f++) {
      const P0 = trace[f]; const ok = P0 && P0.found !== false && P0.valid && P0.alpha > 0.05;
      if (ok) last = P0; else R.heroInvalid++;
      const P = last || P0; const hero = [P.x, P.y + 1.4, P.z];
      let pos, tgt, fov = S.fov;
      if (S.kind === 'hold') { if (prevCam) { cams[f] = prevCam.slice(); } continue; }
      if (!st) st = { first: true };
      if (S.kind === 'establish') {
        // anchor 'start' (default): placed from the hero's pose at the shot's first frame; 'end': from its pose at the last
        // frame (an aircraft that taxis INTO the shot and stops - the ramp shot of a landing)
        if (st.first) { const A = S.anchor === 'end' ? (trace[Math.min(S.f1, trace.length) - 1] || P) : P; const a = S.az;
          const base = [A.x + Math.sin(a * D2R) * S.dist, 0, A.z - Math.cos(a * D2R) * S.dist]; base[1] = gy(base[0], base[2]) + S.h; st.base = base; st.k = 0; }
        const tt = (f - S.f0) * dt; pos = [st.base[0] + S.drift[0] * tt, st.base[1], st.base[2] - S.drift[1] * tt];
        tgt = thirdsAim(pos, add(hero, mul(velAt(f), S.aimSmooth)), fov, aspect, S.frame[0], S.frame[1]);
        if (st.first) st.aim = new Spring3(tgt); tgt = st.aim.step(tgt, S.aimSmooth, dt);
      } else if (S.kind === 'chase') {
        const h = P.gs > 4 || !P.ground ? P.hdg : P.hdg;
        if (st.first) { st.hd = new SpringA(h); }
        const hs = st.hd.step(h, S.hdgSmooth, dt); const fw = fwdOf(hs), rt = rightOf(hs);
        const want = add(add(add(hero, mul(fw, -S.back)), mul(rt, S.side)), [0, S.up, 0]);
        if (st.first) st.off = new Spring3(sub(want, hero));
        pos = add(hero, st.off.step(sub(want, hero), S.posSmooth, dt));
        // aim ahead along the smoothed heading (leadOn 'smoothed', default: the view turns with the camera's heading spring)
        // or the hero's actual heading ('actual': the first version - in tight 8x turns the view whipped round at up to
        // 80 px / frame)
        const aimPt = add(hero, mul(fwdOf(S.leadOn === 'actual' ? P.hdg : hs), S.lead));
        tgt = thirdsAim(pos, aimPt, fov, aspect, S.frame[0], S.frame[1]);
        // the aim spring (relative to the camera) fed forward by its target's rate (aimFF): no steady lag behind a turning
        // target, so the hero stays on its framing point instead of trailing it by rate x aimSmooth
        const rel = sub(tgt, pos); let relT = rel;
        if (S.aimFF && st.relPrev) relT = add(rel, mul(sub(rel, st.relPrev), S.aimSmooth / dt));
        st.relPrev = rel;
        if (st.first) st.aim = new Spring3(rel); tgt = add(pos, st.aim.step(relT, S.aimSmooth, dt));
      } else if (S.kind === 'dolly') {
        const W = runwayFrame(site, rwyAxis, S.rwy); const sgn = S.side === 'right' ? 1 : -1;
        const sH = dot(sub([P.x, 0, P.z], W.o), W.d);
        const mv = dot(fwdOf(P.hdg), W.d) >= 0 ? 1 : -1;            // the hero's motion along the axis
        // feed-forward: a critically damped spring (w = 2 / smooth) follows its target with X/T = w^2 / (s + w)^2, so the
        // target T = S + smooth S' + smooth^2 / 4 S'' makes the car follow the hero's along-track position S exactly (the
        // first version had no feed-forward: the car settled v x smooth behind its planned lag - 63 m instead of 12 at the
        // S lift-off); velocity and acceleration in VIDEO time from the trace
        const vA = dot(velK(f, 3), W.d), aA = (dot(velK(f + 3, 3), W.d) - dot(velK(f - 3, 3), W.d)) / (6 * dt);
        const tgtS = sH + S.lag * mv + S.smooth * vA + 0.25 * S.smooth * S.smooth * aA;
        // (the car is already moving with the hero when the shot starts: a cut into a running dolly, not a standing start)
        if (st.first) { st.s = sH + S.lag * mv; st.v = clamp(vA, -S.vmax, S.vmax); }
        [st.s, st.v] = smoothDamp(st.s, tgtS, st.v, S.smooth, dt, S.vmax);
        if (Math.abs(st.v) >= S.vmax - 1e-6) R.carAtVmax++;
        const le = Math.abs((st.s - sH) * mv - S.lag); if (R.lagErrMax == null || le > R.lagErrMax) { R.lagErrMax = le; R.lagErrAt = f; }
        const base = add(add(W.o, mul(W.d, st.s)), mul(W.r, sgn * S.off)); base[1] = gy(base[0], base[2]) + S.h; pos = base;
        if (S.zoom) { const dd = len(sub(hero, pos)); fov = clamp(2 * Math.atan((0.5 * Math.max(P.span || 12, P.L || 10) / S.zoom) / dd) / D2R, FOV_MIN, FOV_MAX); if (st.first) st.fz = { v: fov, dv: 0 }; [st.fz.v, st.fz.dv] = smoothDamp(st.fz.v, fov, st.fz.dv, 0.8, dt); fov = st.fz.v; }
        // lead room: the camera looks across the runway (toward -sgn x right), so screen-right is sgn x d; a hero moving
        // screen-right sits on the left thirds line, and vice versa
        const movesRight = sgn * mv > 0, sx = (movesRight ? -1 : 1) * Math.abs(S.frame[0]);
        tgt = thirdsAim(pos, hero, fov, aspect, sx, S.frame[1]);
        // the car moves with the hero: the aim is smoothed relative to the camera (as in the chase)
        if (st.first) st.aim = new Spring3(sub(tgt, pos)); tgt = add(pos, st.aim.step(sub(tgt, pos), S.aimSmooth, dt));
      } else if (S.kind === 'fixed' || S.kind === 'tower') {
        if (st.first) {
          if (S.kind === 'tower') { const T = site.anchors.tower; st.base = [T.x, T.eyeY, T.z]; }
          else if (S.pos) { st.base = S.pos.slice(); if (st.base[1] == null) st.base[1] = gy(st.base[0], st.base[2]) + (S.h ?? 2); }
          else if (S.at) { const W = runwayFrame(site, rwyAxis, S.at.rwy); const b = add(add(W.o, mul(W.d, S.at.along)), mul(W.r, S.at.across)); b[1] = gy(b[0], b[2]) + (S.at.h ?? 2); st.base = b; }
          else throw new Error('fixed shot without pos / at');
        }
        pos = st.base.slice();
        if (S.zoom) { const dd = len(sub(hero, pos)); fov = clamp(2 * Math.atan((0.5 * Math.max(P.span || 12, P.L || 10) / S.zoom) / dd) / D2R, FOV_MIN, FOV_MAX); if (st.first) st.fz = { v: fov, dv: 0 }; [st.fz.v, st.fz.dv] = smoothDamp(st.fz.v, fov, st.fz.dv, S.zoomSmooth, dt); fov = st.fz.v; }
        tgt = thirdsAim(pos, add(hero, mul(velAt(f), S.aimSmooth)), fov, aspect, S.frame[0], S.frame[1]);
        if (st.first) { st.aim = new Spring3(tgt); st.aim.v = velAt(f); } tgt = st.aim.step(tgt, S.aimSmooth, dt);
      } else throw new Error('unknown shot kind ' + S.kind);
      st.first = false;
      // ---- constraints
      fov = clamp(fov, FOV_MIN, FOV_MAX);
      const g = gy(pos[0], pos[2]);
      if (pos[1] < g + CAM_AGL_MIN) { pos[1] = g + CAM_AGL_MIN; R.raised++; }
      const b = site.buildingAt(pos[0], pos[2]);
      if (b && pos[1] < g + (b.height_m || 8) + 2) { pos[1] = g + (b.height_m || 8) + 2; R.raised++; }
      for (const o of [[P.x, P.y + 1.4, P.z, 0.5 * Math.max(P.L || 10, P.span || 12)], ...(P.near || [])]) {
        const d = sub(pos, [o[0], o[1], o[2]]), dl = len(d), need = o[3] + AC_CLEAR;
        if (dl < need) { pos = add([o[0], o[1], o[2]], mul(norm(dl > 1e-3 ? d : [0, 1, 0]), need)); R.pushed++; }
      }
      // ---- metrics
      const cam = [pos[0], pos[1], pos[2], tgt[0], tgt[1], tgt[2], fov];
      R.camAglMin = Math.min(R.camAglMin, pos[1] - gy(pos[0], pos[2]));
      for (const [x, z, r] of obstacles) R.fixtureMin = Math.min(R.fixtureMin, Math.hypot(pos[0] - x, pos[2] - z) - r);
      if (prevCam && f > S.f0) {
        const s = Math.hypot(pos[0] - prevCam[0], pos[1] - prevCam[1], pos[2] - prevCam[2]); if (s > R.stepMax) { R.stepMax = s; R.stepMaxAt = f; }
        // relative to the hero (a chase camera moves with it): a jump is a change of the camera-to-hero offset
        if (st.prevHero) { const rs = len(sub(sub(pos, hero), sub(prevCam.slice(0, 3), st.prevHero))); R.relStepMax = Math.max(R.relStepMax, rs); }
      }
      st.prevHero = hero;
      for (const o of P.near || []) R.acClearMin = Math.min(R.acClearMin, len(sub(pos, [o[0], o[1], o[2]])) - o[3]);
      R.acClearMin = Math.min(R.acClearMin, len(sub(pos, hero)) - 0.5 * Math.max(P.L || 10, P.span || 12));
      const n = project(pos, tgt, fov, aspect, hero);
      if (!n || Math.abs(n[0]) > 0.92 || Math.abs(n[1]) > 0.92) R.offScreen++; else R.ndcMax = Math.max(R.ndcMax, Math.abs(n[0]), Math.abs(n[1]));
      if (occluded(site, pos, hero)) R.occluded++;
      R.fov[0] = Math.min(R.fov[0], fov); R.fov[1] = Math.max(R.fov[1], fov);
      // on-screen motion inside the shot (px at heightPx): the hero's screen position, its speed and change of speed
      const scr = n ? [n[0] * Wp / 2, n[1] * Hp / 2] : null;
      if (scr && scr1) { const v = Math.hypot(scr[0] - scr1[0], scr[1] - scr1[1]); if (v > R.heroPxMax) { R.heroPxMax = v; R.heroPxAt = f; }
        if (scr2) { const a = Math.hypot(scr[0] - 2 * scr1[0] + scr2[0], scr[1] - 2 * scr1[1] + scr2[1]); if (a > R.heroAccMax) { R.heroAccMax = a; R.heroAccAt = f; } } }
      scr2 = scr1; scr1 = scr;
      // the background's pan speed from the camera's rotation alone (at the frame centre; zoom and parallax left out)
      const dir = norm(sub(tgt, pos));
      if (dir1) { const ang = Math.acos(clamp(dot(dir, dir1), -1, 1)), px = Math.tan(ang) / Math.tan(fov * D2R / 2) * Hp / 2;
        if (px > R.bgPxMax) { R.bgPxMax = px; R.bgPxAt = f; } if (px > 20) R.bgOver20++; }
      dir1 = dir;
      // rest jitter: the hero standing on the ground (< 1 kt in this and the previous frame) yet hopping (a step > 5 cm whose
      // implied speed contradicts the reported one: > 2 kt + 2 gs over the frame's data time) or twitching (a yaw step > 1 deg
      // undone by one of the next 3 frames); a smooth creep or a slow pivot at time-lapse speed is not jitter
      const Pp = f > S.f0 && okAt(f - 1) ? trace[f - 1] : null;
      if (ok && Pp && P0.ground && Pp.ground && P0.gs < 1 && Pp.gs < 1) {
        const step = Math.hypot(P0.x - Pp.x, P0.z - Pp.z), dtD = Math.max(1e-3, (P0.t - Pp.t) / 1000), kt = step / dtD * 3600 / 1852;
        const dh = wrap180(P0.hdg - Pp.hdg); let back = false;
        if (Math.abs(dh) > 1) for (let k = 1; k <= 3 && !back; k++) { const A = trace[f + k - 1], B = trace[f + k]; if (okAt(f + k) && A && B) { const d2 = wrap180(B.hdg - A.hdg); back = Math.abs(d2) > 1 && Math.sign(d2) !== Math.sign(dh); } }
        if ((step > 0.05 && kt > 2 + 2 * Math.max(P0.gs, Pp.gs)) || back) { R.restJitter++; if (R.restJitterAt == null) R.restJitterAt = f; }
      }
      cams[f] = cam.map(v => +v.toFixed(4)); prevCam = cams[f];
    }
    for (const k of ['camAglMin', 'fixtureMin', 'stepMax', 'relStepMax', 'acClearMin', 'ndcMax', 'heroPxMax', 'heroAccMax', 'bgPxMax', 'lagErrMax']) if (Number.isFinite(R[k])) R[k] = +R[k].toFixed(2);
    R.fov = R.fov.map(v => +(+v).toFixed(1));
    report.push(R);
  }
  // frames no shot covered: the previous camera (never a jump to a default)
  for (let f = 0; f < cams.length; f++) if (!cams[f]) cams[f] = f ? cams[f - 1] : null;
  return { cams, report };
}
/** the line of sight camera -> point passes through a building below its roof */
export function occluded(site, C, P, stepM = 4) {
  const d = sub(P, C), L = len(d), n = Math.max(2, Math.ceil(L / stepM));
  for (let i = 1; i < n - 1; i++) {
    const q = add(C, mul(d, i / n)); const b = site.buildingAt(q[0], q[2]);
    if (b && q[1] < site.groundY(q[0], q[2]) + (b.height_m || 8)) return true;
  }
  return false;
}
