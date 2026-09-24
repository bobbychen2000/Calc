// Camera rig + input: map-style pan/zoom/rotate/tilt (mouse, touch, keyboard), follow & chase, tower view.
import { GROUND_Y } from '../geo.js';

const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const DEG = Math.PI / 180;
const ease = (t) => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
const wrapPi = (a) => { a = (a + Math.PI) % (2 * Math.PI); if (a < 0) a += 2 * Math.PI; return a - Math.PI; };

export class CameraRig {
  constructor(el, { heightAt = () => 0, onTap = null, onUserMove = null } = {}) {
    this.el = el; this.heightAt = heightAt; this.onTap = onTap; this.onUserMove = onUserMove;
    this.target = [-600, GROUND_Y, 200]; this.yaw = 135 * DEG; this.pitch = 24 * DEG; this.dist = 5200; this.fov = 50 * DEG;
    this.mode = 'orbit'; this.followFn = null; this.chase = false; this.chaseOff = 0; this.fp = null;
    this.anim = null; this.pointers = new Map(); this.vel = null; this.W = 1; this.H = 1;
    this.bind();
  }
  // ---------------------------------------------------------------- camera output
  camera() {
    if (this.mode === 'fp') {
      const f = this.fp; const dir = [Math.cos(f.pitch) * Math.sin(f.yaw), Math.sin(f.pitch), -Math.cos(f.pitch) * Math.cos(f.yaw)];
      return { pos: f.pos.slice(), dir, fov: f.fov, near: 1.0, split: 2500, far: 160000, shadowSplits: [300, 1500, 6000] };
    }
    const cp = Math.cos(this.pitch);
    const off = [cp * Math.sin(this.yaw), Math.sin(this.pitch), -cp * Math.cos(this.yaw)];
    let pos = [this.target[0] + off[0] * this.dist, this.target[1] + off[1] * this.dist, this.target[2] + off[2] * this.dist];
    const gmin = Math.max(this.heightAt(pos[0], pos[2]), 0) + 2.5;
    if (pos[1] < gmin) pos[1] = gmin;
    const d = this.dist;
    return { pos, target: this.target.slice(), fov: this.fov, near: clamp(d * 0.008, 0.25, 40), split: clamp(d * 3.5, 350, 6000), far: 180000,
      shadowSplits: [clamp(d * 1.4, 70, 1800), clamp(d * 5, 450, 7000), clamp(d * 16, 2500, 22000)] };
  }
  // ---------------------------------------------------------------- per-frame update
  update(dt) {
    if (this.anim) {
      const A = this.anim; A.t += dt; const u = ease(Math.min(1, A.t / A.dur));
      const tgt = A.to.follow && this.followFn ? this.followFn().p : A.to.target;
      for (let k = 0; k < 3; k++) this.target[k] = A.from.target[k] + (tgt[k] - A.from.target[k]) * u;
      this.dist = Math.exp(Math.log(A.from.dist) + (Math.log(A.to.dist) - Math.log(A.from.dist)) * u);
      this.yaw = A.from.yaw + wrapPi(A.to.yaw - A.from.yaw) * u; this.pitch = A.from.pitch + (A.to.pitch - A.from.pitch) * u;
      if (A.to.fov) this.fov = A.from.fov + (A.to.fov - A.from.fov) * u;
      if (A.t >= A.dur) this.anim = null;
    } else if (this.mode === 'follow' && this.followFn) {
      const f = this.followFn(); if (!f) { this.mode = 'orbit'; } else {
        const k = 1 - Math.exp(-dt / 0.25);
        for (let i = 0; i < 3; i++) this.target[i] += (f.p[i] - this.target[i]) * k;
        if (this.chase) { const want = f.hdg + Math.PI + this.chaseOff; this.yaw += wrapPi(want - this.yaw) * (1 - Math.exp(-dt / 1.2)); }
      }
    }
    if (this.vel && !this.pointers.size) { // inertia after a flick
      const v = this.vel; const k = Math.exp(-dt / 0.35);
      if (v.kind === 'pan') this.panBy(v.x * dt, v.y * dt); else if (v.kind === 'orbit') this.orbitBy(v.x * dt, v.y * dt);
      v.x *= k; v.y *= k; if (Math.hypot(v.x, v.y) < 2) this.vel = null;
    }
  }
  flyTo(to, dur = 1.6) {
    this.anim = { t: 0, dur, from: { target: this.target.slice(), dist: this.dist, yaw: this.yaw, pitch: this.pitch, fov: this.fov },
      to: { target: to.target || this.target.slice(), dist: to.dist ?? this.dist, yaw: to.yaw ?? this.yaw, pitch: to.pitch ?? this.pitch, fov: to.fov, follow: !!to.follow } };
  }
  setFollow(fn, opts = {}) {
    this.followFn = fn; this.mode = 'follow'; this.chase = !!opts.chase; this.chaseOff = 0;
    const f = fn(); if (!f) return;
    const dist = opts.dist ?? clamp(f.L * 2.6, 60, 400);
    this.flyTo({ target: f.p, dist, yaw: this.chase ? f.hdg + Math.PI : this.yaw, pitch: opts.pitch ?? clamp(this.pitch, 8 * DEG, 30 * DEG), follow: true }, 1.4);
  }
  stopFollow() { if (this.mode === 'follow') this.mode = 'orbit'; this.followFn = null; this.chase = false; }
  setTower(pos, look) { this.stopFollow(); this.anim = null; this.mode = 'fp'; this.fp = { pos, yaw: look.yaw, pitch: look.pitch, fov: look.fov || 55 * DEG }; }
  leaveTower() { if (this.mode === 'fp') this.mode = 'orbit'; }
  // ---------------------------------------------------------------- motions
  pxToM() { return 2 * this.dist * Math.tan(this.fov / 2) / this.H; }
  panBy(dx, dy) {
    if (this.mode === 'fp') return;
    if (this.mode === 'follow') { this.orbitBy(dx, dy); return; }
    const s = this.pxToM() * (1 + 0.6 * (1 - Math.sin(this.pitch)));
    const r = [-Math.cos(this.yaw), 0, -Math.sin(this.yaw)], f = [-Math.sin(this.yaw), 0, Math.cos(this.yaw)]; // screen right, forward (horizontal)
    this.target[0] += (-dx * r[0] + dy * f[0]) * s; this.target[2] += (-dx * r[2] + dy * f[2]) * s;
    const R = Math.hypot(this.target[0], this.target[2]); if (R > 60000) { this.target[0] *= 60000 / R; this.target[2] *= 60000 / R; }
  }
  orbitBy(dx, dy) {
    if (this.mode === 'fp') { const f = this.fp; const k = f.fov / this.H; f.yaw -= dx * k; f.pitch = clamp(f.pitch + dy * k, -60 * DEG, 30 * DEG); return; }
    if (this.mode === 'follow' && this.chase) { this.chaseOff = wrapPi(this.chaseOff + dx * 0.005); }
    else this.yaw += dx * 0.005;
    this.pitch = clamp(this.pitch + dy * 0.004, 2 * DEG, 88 * DEG);
  }
  zoomBy(f, sx, sy) {
    if (this.mode === 'fp') { this.fp.fov = clamp(this.fp.fov * f, 6 * DEG, 75 * DEG); return; }
    const nd = clamp(this.dist * f, 12, 90000);
    // zoom toward the ground point under the cursor (orbit mode)
    if (sx != null && this.mode === 'orbit') {
      const hit = this.groundHit(sx, sy);
      if (hit) { const k = 1 - nd / this.dist; this.target[0] += (hit[0] - this.target[0]) * k; this.target[2] += (hit[2] - this.target[2]) * k; }
    }
    this.dist = nd;
  }
  groundHit(sx, sy) {
    const c = this.camera(); const pos = c.pos;
    const f = norm(sub(c.target, pos)); const r = norm(cross(f, [0, 1, 0])); const u = cross(r, f);
    const th = Math.tan(this.fov / 2), asp = this.W / this.H;
    const nx = (sx / this.W) * 2 - 1, ny = 1 - (sy / this.H) * 2;
    const d = norm([f[0] + r[0] * nx * th * asp + u[0] * ny * th, f[1] + r[1] * nx * th * asp + u[1] * ny * th, f[2] + r[2] * nx * th * asp + u[2] * ny * th]);
    if (d[1] > -1e-3) return null; const t = (GROUND_Y - pos[1]) / d[1]; if (t > 60000) return null;
    return [pos[0] + d[0] * t, GROUND_Y, pos[2] + d[2] * t];
  }
  // ---------------------------------------------------------------- input
  bind() {
    const el = this.el;
    el.style.touchAction = 'none';
    el.addEventListener('contextmenu', e => e.preventDefault());
    el.addEventListener('pointerdown', e => {
      el.setPointerCapture(e.pointerId);
      this.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY, x0: e.clientX, y0: e.clientY, t0: performance.now(), btn: e.button, mod: e.ctrlKey || e.shiftKey || e.altKey || e.metaKey });
      this.anim = null; this.vel = null; this.gesture = null;
      if (this.onUserMove) this.onUserMove();
    });
    const end = (e) => {
      const p = this.pointers.get(e.pointerId); if (!p) return;
      this.pointers.delete(e.pointerId);
      const moved = Math.hypot(e.clientX - p.x0, e.clientY - p.y0), dt = performance.now() - p.t0;
      if (moved < 8 && dt < 450 && !this.gesture && this.onTap) { const r = el.getBoundingClientRect(); this.onTap(e.clientX - r.left, e.clientY - r.top); }
      if (this.pointers.size < 2) this.gesture = null;
    };
    el.addEventListener('pointerup', end); el.addEventListener('pointercancel', end);
    el.addEventListener('pointermove', e => {
      const p = this.pointers.get(e.pointerId); if (!p) return;
      const dx = e.clientX - p.x, dy = e.clientY - p.y; const now = performance.now();
      if (this.pointers.size === 1) {
        if (Math.hypot(e.clientX - p.x0, e.clientY - p.y0) > 6) this.gesture = this.gesture || 'drag';
        const orbit = p.btn === 2 || p.btn === 1 || p.mod || this.mode === 'follow' || this.mode === 'fp';
        if (orbit) this.orbitBy(dx, dy); else this.panBy(dx, dy);
        const dtp = Math.max(8, now - (p.t || now - 16)); this.vel = { kind: orbit ? 'orbit' : 'pan', x: dx / dtp * 1000, y: dy / dtp * 1000 };
      } else if (this.pointers.size === 2) {
        const [a, b] = [...this.pointers.values()];
        const before = { cx: (a.x + b.x) / 2, cy: (a.y + b.y) / 2, d: Math.hypot(a.x - b.x, a.y - b.y), ang: Math.atan2(b.y - a.y, b.x - a.x) };
        p.x = e.clientX; p.y = e.clientY;
        const after = { cx: (a.x + b.x) / 2, cy: (a.y + b.y) / 2, d: Math.hypot(a.x - b.x, a.y - b.y), ang: Math.atan2(b.y - a.y, b.x - a.x) };
        this.gesture = 'multi'; this.vel = null;
        if (before.d > 10 && after.d > 10) {
          const r = el.getBoundingClientRect();
          this.zoomBy(before.d / after.d, after.cx - r.left, after.cy - r.top);
          if (this.mode !== 'fp') { const da = wrapPi(after.ang - before.ang); if (this.mode === 'follow' && this.chase) this.chaseOff -= da; else this.yaw -= da; }
          const vy = after.cy - before.cy; if (this.mode !== 'fp') this.pitch = clamp(this.pitch + vy * 0.004, 2 * DEG, 88 * DEG); else this.orbitBy(0, vy);
          if (this.mode === 'orbit') this.panBy(after.cx - before.cx, 0);
        }
        return;
      }
      p.x = e.clientX; p.y = e.clientY; p.t = now;
    });
    el.addEventListener('wheel', e => {
      e.preventDefault(); this.anim = null; if (this.onUserMove) this.onUserMove();
      const r = el.getBoundingClientRect();
      const k = e.deltaMode === 1 ? 0.05 : 0.0016;
      this.zoomBy(Math.exp(clamp(e.deltaY, -300, 300) * k), e.clientX - r.left, e.clientY - r.top);
    }, { passive: false });
    window.addEventListener('keydown', e => {
      if (e.target && /input|textarea|select/i.test(e.target.tagName)) return;
      const s = 40; let used = true;
      switch (e.key) {
        case 'ArrowLeft': case 'a': this.panBy(s, 0); break; case 'ArrowRight': case 'd': this.panBy(-s, 0); break;
        case 'ArrowUp': case 'w': this.panBy(0, s); break; case 'ArrowDown': case 's': this.panBy(0, -s); break;
        case 'q': this.orbitBy(-30, 0); break; case 'e': this.orbitBy(30, 0); break;
        case 'r': this.orbitBy(0, 25); break; case 'f': this.orbitBy(0, -25); break;
        case '+': case '=': this.zoomBy(0.8); break; case '-': case '_': this.zoomBy(1.25); break;
        default: used = false;
      }
      if (used) { this.anim = null; if (this.onUserMove) this.onUserMove(); }
    });
  }
  resize(W, H) { this.W = W; this.H = H; }
}
const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const norm = (a) => { const l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };
