// ------------------------------------------------------------------
// App: camera modes (walk / seat / x-ray), picking, UI wiring, guided tour
// ------------------------------------------------------------------
const $ = (s) => document.querySelector(s);
const store = {
  get(k, d) { try { const v = localStorage.getItem('cab777.' + k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem('cab777.' + k, JSON.stringify(v)); } catch (e) { /* storage unavailable */ } },
};

class App {
  constructor() {
    this.canvas = $('#view');
    this.G = new GL(this.canvas, { preserve: !!window.__TEST__ });
    const coarse = matchMedia('(pointer: coarse)').matches;
    this.touch = coarse;
    this.quality = store.get('quality', coarse ? 'balanced' : 'high');
    this.scene = new Scene(this.G, { quality: this.quality === 'low' ? 'low' : 'high' });
    this.L = this.scene.layout;
    this.mode = 'walk';
    // start: standing at door 1 looking aft toward THE Suite
    this.cam = { pos: [1.32, 1.62, 5.55], yaw: Math.PI + 0.06, pitch: -0.06, fov: 70 };
    this.orbit = { target: [0, 0.6, 32], dist: 38, az: 0.0, el: 58 * DEG };
    this.sel = null; this.seated = null; this.bed = null;
    this.keys = {};
    this.joy = { x: 0, y: 0, active: false };
    this.anim = null;
    this.tour = null;
    this.t0 = performance.now();
    this.lastInteract = 0;
    this.frameMs = 16;
    this.dirty = true;
    this.bindInput();
    this.bindUI();
    this.resize();
    addEventListener('resize', () => this.resize());
    this.applyMood(store.get('mood', 'boarding'));
    this.applySky(store.get('sky', 'day'));
    this.drawMap();
    if (!coarse) $('#hintText').textContent = 'W A S D or arrow keys to walk. Click a seat to see it or sit in it. Click a window to move its shade.';
    this.loop = this.loop.bind(this);
    requestAnimationFrame(this.loop);
    window.__app = this;
  }

  // ---------------- sizing ----------------
  resize() {
    const r = this.canvas.getBoundingClientRect();
    const cap = this.quality === 'low' ? 1.0 : this.quality === 'balanced' ? 1.5 : 2.0;
    this.dpr = Math.min(window.devicePixelRatio || 1, cap) * (this.dynScale || 1);
    const w = Math.max(1, Math.round(r.width * this.dpr)), h = Math.max(1, Math.round(r.height * this.dpr));
    if (this.canvas.width !== w || this.canvas.height !== h) { this.canvas.width = w; this.canvas.height = h; }
    this.cw = r.width; this.ch = r.height;
    this.dirty = true;
    this.drawMap();
  }

  // ---------------- camera ----------------
  camDir(yaw = this.cam.yaw, pitch = this.cam.pitch) {
    return [-Math.sin(yaw) * Math.cos(pitch), Math.sin(pitch), -Math.cos(yaw) * Math.cos(pitch)];
  }
  camera() {
    const aspect = this.canvas.width / this.canvas.height;
    let pos, target;
    if (this.mode === 'xray') {
      const o = this.orbit;
      pos = [o.target[0] + o.dist * Math.cos(o.el) * Math.sin(o.az), o.target[1] + o.dist * Math.sin(o.el), o.target[2] + o.dist * Math.cos(o.el) * Math.cos(o.az)];
      target = o.target;
    } else {
      pos = this.cam.pos;
      target = V3.add(pos, this.camDir());
    }
    // keep horizontal FOV reasonable on tall phones
    const hfovTarget = 64 * DEG;
    let fovY = 2 * Math.atan(Math.tan(hfovTarget / 2) / aspect);
    fovY = clamp(fovY, (this.mode === 'xray' ? 40 : 58) * DEG, 92 * DEG);
    const view = M4.lookAt(pos, target, [0, 1, 0]);
    const proj = M4.perspective(fovY, aspect, this.mode === 'xray' ? 0.5 : 0.03, 3000);
    const right = [view[0], view[4], view[8]], up = [view[1], view[5], view[9]];
    const fwd = V3.norm(V3.sub(target, pos));
    const halfDiag = Math.atan(Math.hypot(Math.tan(fovY / 2), Math.tan(fovY / 2) * aspect));
    this.camState = { view, proj, pos, right, up, fovY, aspect, fwd, halfDiag };
    return this.camState;
  }

  // world ray from screen point (css px)
  ray(px, py) {
    const c = this.camState || this.camera();
    const nx = (px / this.cw) * 2 - 1, ny = 1 - (py / this.ch) * 2;
    const inv = M4.invert(M4.mul(c.proj, c.view));
    const a = M4.point(inv, [nx, ny, -1]), b = M4.point(inv, [nx, ny, 1]);
    return { o: a, d: V3.norm(V3.sub(b, a)) };
  }

  // ---------------- picking ----------------
  pickSeat(r) {
    let best = null, bt = 1e9;
    for (const s of this.L.seats) {
      const t = rayBox(r, seatPickBox(s));
      if (t !== null && t < bt) { bt = t; best = s; }
    }
    return best ? { seat: best, t: bt } : null;
  }
  pickWindow(r) {
    let best = null, bt = 1e9;
    const x = wallAt(CAB.win.yc)[0];
    this.L.windows.forEach((w, i) => {
      const bx = [w.side > 0 ? x - 0.04 : -x - 0.12, w.side > 0 ? x + 0.12 : -x + 0.04, CAB.win.yc - 0.25, CAB.win.yc + 0.25, w.z - 0.17, w.z + 0.17];
      const t = rayBox(r, bx);
      if (t !== null && t < bt) { bt = t; best = i; }
    });
    return best !== null ? { win: best, t: bt } : null;
  }
  pickFloor(r) {
    if (r.d[1] >= -1e-4) return null;
    const t = -r.o[1] / r.d[1];
    const p = V3.add(r.o, V3.scale(r.d, t));
    return { p, t };
  }

  walkable(x, z) {
    for (const [x0, x1, z0, z1] of this.L.walk) if (x >= x0 && x <= x1 && z >= z0 && z <= z1) return true;
    return false;
  }
  nearestWalkable(x, z) {
    let best = null, bd = 1e9;
    for (const [x0, x1, z0, z1] of this.L.walk) {
      const px = clamp(x, x0, x1), pz = clamp(z, z0, z1);
      const d = Math.hypot(px - x, pz - z);
      if (d < bd) { bd = d; best = [px, pz]; }
    }
    return best;
  }

  // ---------------- input ----------------
  bindInput() {
    const cv = this.canvas;
    this.pointers = new Map();
    cv.addEventListener('pointerdown', (e) => {
      cv.setPointerCapture(e.pointerId);
      this.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY, x0: e.clientX, y0: e.clientY, t0: performance.now(), btn: e.button });
      if (this.pointers.size === 2) this.pinch = this.pinchState();
      this.interrupt();
    });
    cv.addEventListener('pointermove', (e) => {
      const p = this.pointers.get(e.pointerId);
      if (!p) return;
      const dx = e.clientX - p.x, dy = e.clientY - p.y;
      p.x = e.clientX; p.y = e.clientY;
      if (this.pointers.size >= 2) { this.handlePinch(); return; }
      if (Math.hypot(p.x - p.x0, p.y - p.y0) < 4) return;
      this.onDrag(dx, dy, p.btn === 2 || e.shiftKey);
    });
    const up = (e) => {
      const p = this.pointers.get(e.pointerId);
      if (!p) return;
      this.pointers.delete(e.pointerId);
      if (this.pointers.size < 2) this.pinch = null;
      const moved = Math.hypot(e.clientX - p.x0, e.clientY - p.y0);
      if (moved < 8 && performance.now() - p.t0 < 450 && e.type === 'pointerup') this.onTap(e.clientX, e.clientY);
    };
    cv.addEventListener('pointerup', up);
    cv.addEventListener('pointercancel', up);
    cv.addEventListener('contextmenu', (e) => e.preventDefault());
    cv.addEventListener('wheel', (e) => {
      e.preventDefault();
      this.interrupt();
      if (this.mode === 'xray') this.orbit.dist = clamp(this.orbit.dist * Math.exp(e.deltaY * 0.0012), 4, 70);
      else if (this.mode === 'walk') this.moveBy(-e.deltaY * 0.004, 0);
      else this.cam.fov = clamp(this.cam.fov + e.deltaY * 0.02, 40, 80);
      this.dirty = true;
    }, { passive: false });
    addEventListener('keydown', (e) => {
      if (e.target && (e.target.tagName === 'INPUT')) return;
      this.keys[e.key.toLowerCase()] = true;
      if (['arrowup', 'arrowdown', 'arrowleft', 'arrowright', ' '].includes(e.key.toLowerCase())) e.preventDefault();
      if (e.key === 'Escape') this.closeCard();
      this.interrupt();
    });
    addEventListener('keyup', (e) => { this.keys[e.key.toLowerCase()] = false; });
    // joystick
    const joy = $('#joy'), knob = $('#joyKnob');
    const jmove = (e) => {
      const r = joy.getBoundingClientRect();
      const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
      let dx = (e.clientX - cx) / (r.width / 2), dy = (e.clientY - cy) / (r.height / 2);
      const l = Math.hypot(dx, dy);
      if (l > 1) { dx /= l; dy /= l; }
      this.joy.x = dx; this.joy.y = dy;
      knob.style.transform = `translate(${dx * r.width * 0.32}px, ${dy * r.height * 0.32}px)`;
    };
    joy.addEventListener('pointerdown', (e) => { joy.setPointerCapture(e.pointerId); this.joy.active = true; jmove(e); this.interrupt(); if (this.mode === 'seat') this.standUp(); });
    joy.addEventListener('pointermove', (e) => { if (this.joy.active) jmove(e); });
    const jup = () => { this.joy.active = false; this.joy.x = this.joy.y = 0; knob.style.transform = ''; };
    joy.addEventListener('pointerup', jup); joy.addEventListener('pointercancel', jup);
  }
  pinchState() {
    const ps = [...this.pointers.values()];
    return { d: Math.hypot(ps[0].x - ps[1].x, ps[0].y - ps[1].y), cx: (ps[0].x + ps[1].x) / 2, cy: (ps[0].y + ps[1].y) / 2 };
  }
  handlePinch() {
    const now = this.pinchState();
    const prev = this.pinch || now;
    const s = prev.d / Math.max(now.d, 1);
    if (this.mode === 'xray') {
      this.orbit.dist = clamp(this.orbit.dist * s, 4, 70);
      this.panOrbit(now.cx - prev.cx, now.cy - prev.cy);
    } else if (this.mode === 'walk') {
      this.moveBy((1 - s) * 2.2, 0);
    } else {
      this.cam.fov = clamp(this.cam.fov * s, 40, 80);
    }
    this.pinch = now;
    this.dirty = true;
  }
  panOrbit(dx, dy) {
    const o = this.orbit;
    const k = o.dist / this.ch * 1.2;
    const fx = Math.sin(o.az), fz = Math.cos(o.az);
    const rx = Math.cos(o.az), rz = -Math.sin(o.az);
    o.target[0] = clamp(o.target[0] - (rx * dx) * k, -3, 3);
    o.target[2] = clamp(o.target[2] - (rz * dx + fz * dy) * k - fx * 0, 3, 61);
    this.dirty = true;
  }
  onDrag(dx, dy, pan) {
    if (this.mode === 'xray') {
      if (pan) { this.panOrbit(dx, dy); return; }
      this.orbit.az -= dx * 0.006;
      this.orbit.el = clamp(this.orbit.el + dy * 0.005, 12 * DEG, 88 * DEG);
    } else {
      const k = (this.cam.fov / 70) * 0.0052;
      this.cam.yaw += dx * k;
      this.cam.pitch = clamp(this.cam.pitch + dy * k, -1.25, 1.2);
      if (this.mode === 'seat' && this.seated) this.clampSeatLook();
    }
    this.dirty = true;
  }
  clampSeatLook() { this.cam.pitch = clamp(this.cam.pitch, -1.1, 1.0); }
  interrupt() {
    this.lastInteract = performance.now();
    if (this.tour) this.stopTour();
    $('#hint') && $('#hint').classList.add('gone');
    this.dirty = true;
  }

  onTap(px, py) {
    const r = this.ray(px, py);
    const ps = this.pickSeat(r);
    const pw = this.mode !== 'xray' ? this.pickWindow(r) : null;
    const pf = this.mode === 'walk' ? this.pickFloor(r) : null;
    if (pw && (!ps || pw.t < ps.t)) {
      const i = pw.win;
      const lv = (this.scene.winLevels[i] + 1) % 3;
      this.scene.setWindow(i, lv);
      const w = this.L.windows[i];
      this.toast(`${w.electric ? 'Electric shade' : 'Window shade'}: ${SHADE_STATE.label(w, lv)}`);
      this.dirty = true;
      return;
    }
    if (ps && (!pf || ps.t <= pf.t + 0.3)) { this.selectSeat(ps.seat); return; }
    if (pf && this.mode === 'walk') {
      const p = pf.p;
      const q = this.walkable(p[0], p[2]) ? [p[0], p[2]] : this.nearestWalkable(p[0], p[2]);
      if (q && Math.hypot(q[0] - p[0], q[1] - p[2]) < 1.2) this.flyTo({ pos: [q[0], 1.62, q[1]], yaw: this.cam.yaw, pitch: this.cam.pitch }, 0.9);
      return;
    }
    this.closeCard();
  }

  moveBy(fwd, strafe) {
    if (this.mode !== 'walk') return;
    const y = this.cam.yaw;
    const f = [-Math.sin(y), -Math.cos(y)], r = [Math.cos(y), -Math.sin(y)];
    const dx = f[0] * fwd + r[0] * strafe, dz = f[1] * fwd + r[1] * strafe;
    const p = this.cam.pos;
    const tryMove = (nx, nz) => { if (this.walkable(nx, nz)) { p[0] = nx; p[2] = nz; return true; } return false; };
    if (!tryMove(p[0] + dx, p[2] + dz)) { if (!tryMove(p[0] + dx, p[2])) tryMove(p[0], p[2] + dz); }
    this.dirty = true;
  }

  // ---------------- modes ----------------
  setMode(m) {
    if (m === this.mode) return;
    const prev = this.mode;
    if (m === 'xray') {
      if (prev === 'walk' || prev === 'seat') this.orbit.target = [clamp(this.cam.pos[0], -1, 1), 0.6, clamp(this.cam.pos[2], 8, 58)];
      this.orbit.az = this.cw < this.ch ? 0.0 : Math.PI / 2 * 0.92;
      this.orbit.dist = this.cw < this.ch ? 24 : 22;
      this.orbit.el = this.cw < this.ch ? 64 * DEG : 55 * DEG;
      this.scene.xray = true;
    } else {
      this.scene.xray = false;
      if (m === 'walk' && prev === 'xray') {
        const q = this.nearestWalkable(this.orbit.target[0], this.orbit.target[2]);
        this.cam.pos = [q[0], 1.62, q[1]];
        this.cam.pitch = -0.05;
      }
    }
    if (m !== 'seat' && this.seated) { this.setBed(false); this.seated = null; }
    this.mode = m;
    document.body.dataset.mode = m;
    for (const b of document.querySelectorAll('[data-setmode]')) b.setAttribute('aria-pressed', String(b.dataset.setmode === m || (m === 'seat' && b.dataset.setmode === 'walk')));
    this.dirty = true;
    this.drawMap();
  }

  eyeFor(s, bed = false) { return seatEye(s, bed); }
  sit(s, opts = {}) {
    this.closeCard(true);
    if (this.mode === 'xray') { this.scene.xray = false; }
    this.setBed(false);
    this.mode = 'seat';
    document.body.dataset.mode = 'seat';
    for (const b of document.querySelectorAll('[data-setmode]')) b.setAttribute('aria-pressed', String(b.dataset.setmode === 'walk'));
    this.seated = s;
    const e = this.eyeFor(s);
    this.flyTo({ pos: e.pos, yaw: e.yaw, pitch: e.pitch }, opts.instant ? 0 : 1.2);
    if (opts.window) setTimeout(() => { if (this.seated === s) this.lookOut(s); }, opts.instant ? 0 : 1250);
    this.showSeatBar(s);
    this.highlight(null);
    this.drawMap();
  }
  // lean toward the nearest window on the seat's side and look out (slightly aft and down)
  lookOut(s) {
    const side = s.x < 0 ? -1 : 1;
    const e = this.eyeFor(s);
    const headZ = e.pos[2];
    const facing = e.yaw > 1 ? 1 : -1;          // +1 = rear-facing seat (looks toward +z)
    let best = null, bd = 1e9;
    for (const w of this.L.windows) {
      if (w.side !== side) continue;
      const d = Math.abs(w.z - (headZ + facing * 0.25));
      if (d < bd) { bd = d; best = w; }
    }
    if (best && bd < 0.9 && s.pos === 'window') {
      if (this.scene.winLevels[this.L.windows.indexOf(best)] > 0) this.scene.setWindow(this.L.windows.indexOf(best), 0);
      const ez = best.z - facing * 0.10;
      const eye = [side * 2.60, 1.16, ez];
      const tgt = [side * 3.4, 1.02, ez + facing * 0.38];
      const dx = tgt[0] - eye[0], dz = tgt[2] - eye[2];
      this.flyTo({ pos: eye, yaw: Math.atan2(-dx, -dz), pitch: Math.atan2(tgt[1] - eye[1], Math.hypot(dx, dz)) }, 0.9);
    } else this.flyTo({ pos: e.pos, yaw: e.yaw + (side < 0 ? 1.2 : -1.2) * (facing > 0 ? -1 : 1), pitch: -0.05 }, 0.9);
  }
  standUp() {
    if (!this.seated) return;
    const s = this.seated;
    this.setBed(false);
    this.seated = null;
    const q = this.nearestWalkable(s.x, s.z - 0.4);
    this.mode = 'walk';
    document.body.dataset.mode = 'walk';
    this.hideSeatBar();
    this.flyTo({ pos: [q[0], 1.62, q[1]], yaw: this.cam.yaw, pitch: -0.05 }, 0.8);
  }
  setBed(on) {
    const S = this.scene.seats, GR = this.scene.seatGroups, G = this.G;
    if (this.bed) {
      const { g, i, mat, bedKey } = this.bed;
      groupSetMatrix(g, i, mat);
      G.setInstances(S[bedKey], []);
      this.bed = null;
      this.scene.shadowDirty = true;
    }
    if (!on || !this.seated || !seatHasBed(this.seated)) { this.updateBedBtn(); return; }
    const s = this.seated;
    const g = GR[s.meshKey];
    const i = g.refs.indexOf(s);
    const mat = g.master.slice(i * 20, i * 20 + 16);
    groupSetMatrix(g, i, M4.trs(0, -50, 0));
    const bedKey = 'bed_' + s.meshKey;
    G.setInstances(S[bedKey], [mat], [[1, 1, 1, g.master[i * 20 + 19]]]);
    this.bed = { g, i, mat, bedKey };
    this.scene.shadowDirty = true;
    this.updateBedBtn();
  }
  toggleBed() {
    if (!this.seated || !seatHasBed(this.seated)) return;
    const on = !this.bed;
    this.setBed(on);
    const s = this.seated;
    if (on) {
      const bed = seatBedCenter(s);
      const q = this.nearestWalkable(bed[0], bed[2]);
      const eye = [q[0], 1.70, q[1]];
      const dx = bed[0] - eye[0], dz = bed[2] - eye[2], dy = bed[1] - eye[1];
      this.flyTo({ pos: eye, yaw: Math.atan2(-dx, -dz), pitch: Math.atan2(dy, Math.hypot(dx, dz)) }, 1.0);
    } else {
      const e = this.eyeFor(s);
      this.flyTo({ pos: e.pos, yaw: e.yaw, pitch: e.pitch }, 1.0);
    }
  }
  updateBedBtn() {
    const b = $('#bedBtn');
    if (!b) return;
    b.hidden = !(this.seated && seatHasBed(this.seated));
    b.textContent = this.bed ? 'Sit up' : 'Lie flat';
  }

  flyTo(pose, dur) {
    const from = { pos: [...this.cam.pos], yaw: this.cam.yaw, pitch: this.cam.pitch };
    // shortest yaw path
    let dy = pose.yaw - from.yaw;
    dy = ((dy + Math.PI) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2) - Math.PI;
    const to = { pos: pose.pos, yaw: from.yaw + dy, pitch: pose.pitch };
    if (!dur) { this.cam.pos = [...to.pos]; this.cam.yaw = to.yaw; this.cam.pitch = to.pitch; this.dirty = true; return; }
    this.anim = { from, to, t0: performance.now(), dur: dur * 1000, arc: pose.arc || 0 };
  }

  selectSeat(s) {
    this.sel = s;
    this.highlight(s);
    this.showCard(s);
    this.drawMap();
  }
  highlight(s) {
    const GR = this.scene.seatGroups;
    if (this.hl) {
      const { g, i } = this.hl;
      groupSetTint(g, i, [1, 1, 1, Math.floor(g.master[i * 20 + 19])]);
      this.hl = null;
    }
    if (!s) { this.dirty = true; return; }
    for (const g of Object.values(GR)) {
      if (g.key === 'roomDiv') continue;
      const i = g.refs.findIndex((r) => r === s || (Array.isArray(r) && r.includes(s)));
      if (i >= 0) {
        groupSetTint(g, i, [1, 1, 1, Math.floor(g.master[i * 20 + 19]) + 0.5]);
        this.hl = { g, i };
        break;
      }
    }
    this.dirty = true;
  }

  // ---------------- UI ----------------
  bindUI() {
    for (const b of document.querySelectorAll('[data-setmode]')) b.addEventListener('click', () => { this.interrupt(); if (this.mode === 'seat' && b.dataset.setmode === 'walk') this.standUp(); else this.setMode(b.dataset.setmode); });
    $('#settingsBtn').addEventListener('click', () => { const p = $('#settings'); p.hidden = !p.hidden; $('#settingsBtn').setAttribute('aria-expanded', String(!p.hidden)); });
    $('#settingsClose').addEventListener('click', () => { $('#settings').hidden = true; $('#settingsBtn').setAttribute('aria-expanded', 'false'); });
    const moodRow = $('#moodRow');
    for (const [k, m] of Object.entries(MOODS)) {
      const b = document.createElement('button'); b.className = 'chip'; b.textContent = m.label; b.dataset.mood = k;
      b.addEventListener('click', () => { this.applyMood(k); this.interrupt(); });
      moodRow.appendChild(b);
    }
    const skyRow = $('#skyRow');
    for (const [k, s] of Object.entries(SKIES)) {
      const b = document.createElement('button'); b.className = 'chip'; b.textContent = s.label; b.dataset.sky = k;
      b.addEventListener('click', () => { this.applySky(k); this.interrupt(); });
      skyRow.appendChild(b);
    }
    const dimRow = $('#dimRow');
    ['Open', 'Half / sheer', 'Closed'].forEach((t, lv) => {
      const b = document.createElement('button'); b.className = 'chip'; b.textContent = t; b.dataset.dim = lv;
      b.setAttribute('aria-label', ['All shades open', 'Shades half down, sheer blinds in First and Business', 'All shades closed'][lv]);
      b.addEventListener('click', () => { this.scene.setAllWindows(lv); this.syncChips(); this.dirty = true; this.interrupt(); });
      dimRow.appendChild(b);
    });
    const qRow = $('#qualityRow');
    for (const [k, t] of [['low', 'Battery'], ['balanced', 'Balanced'], ['high', 'Sharp']]) {
      const b = document.createElement('button'); b.className = 'chip'; b.textContent = t; b.dataset.quality = k;
      b.addEventListener('click', () => { this.quality = k; store.set('quality', k); this.scene.q = k === 'low' ? 'low' : 'high'; this.dynScale = 1; this.resize(); this.syncChips(); });
      qRow.appendChild(b);
    }
    $('#cardClose').addEventListener('click', () => this.closeCard());
    $('#sitBtn').addEventListener('click', () => { if (this.sel) this.sit(this.sel); });
    $('#lookBtn').addEventListener('click', () => { if (this.sel) this.sit(this.sel, { window: true }); });
    $('#standBtn').addEventListener('click', () => this.standUp());
    $('#bedBtn').addEventListener('click', () => this.toggleBed());
    $('#seatInfoBtn').addEventListener('click', () => { if (this.seated) this.showCard(this.seated, true); });
    $('#lookOutBtn').addEventListener('click', () => { if (this.seated) this.lookOut(this.seated); });
    $('#findForm').addEventListener('submit', (e) => {
      e.preventDefault();
      const v = $('#findInput').value.trim().toUpperCase().replace(/\s+/g, '');
      const s = this.L.seats.find((q) => q.id === v);
      if (!s) { this.toast(`No seat ${v || ''} on this 777-300ER. Try 1A, 11K, 26D or 35C.`); return; }
      $('#findInput').blur();
      this.interrupt();
      this.selectSeat(s);
      this.sit(s);
    });
    $('#tourBtn').addEventListener('click', () => { if (this.tour) this.stopTour(); else this.startTour(); });
    const map = $('#map');
    map.addEventListener('pointerdown', (e) => {
      e.preventDefault();
      const r = map.getBoundingClientRect();
      const u = (e.clientX - r.left) / r.width, v = (e.clientY - r.top) / r.height;
      this.interrupt();
      this.mapTap(u, v);
    });
    this.syncChips();
  }
  syncChips() {
    for (const b of document.querySelectorAll('[data-mood]')) b.setAttribute('aria-pressed', String(b.dataset.mood === this.scene.mood));
    for (const b of document.querySelectorAll('[data-sky]')) b.setAttribute('aria-pressed', String(b.dataset.sky === this.scene.sky));
    for (const b of document.querySelectorAll('[data-dim]')) b.setAttribute('aria-pressed', String(+b.dataset.dim === this.scene.globalShade));
    for (const b of document.querySelectorAll('[data-quality]')) b.setAttribute('aria-pressed', String(b.dataset.quality === this.quality));
  }
  applyMood(k) {
    if (!MOODS[k]) k = 'boarding';
    this.scene.mood = k; store.set('mood', k);
    if (k === 'sleep' && this.scene.globalShade < 2) this.scene.setAllWindows(2);
    this.syncChips(); this.dirty = true;
  }
  applySky(k) {
    if (!SKIES[k]) k = 'day';
    this.scene.sky = k; store.set('sky', k);
    this.scene.updateSheerTint();
    this.scene.shadowDirty = true;
    this.syncChips(); this.dirty = true;
  }
  toast(msg) {
    const t = $('#toast');
    t.textContent = msg; t.classList.add('on');
    clearTimeout(this.toastT);
    this.toastT = setTimeout(() => t.classList.remove('on'), 2200);
  }

  showCard(s, fromSeat) {
    const ci = CLASS_INFO[s.cls];
    $('#cardSeat').textContent = s.id;
    $('#cardClass').textContent = ci.name;
    $('#cardClass').style.setProperty('--cls', ci.color);
    let posTxt = s.pos[0].toUpperCase() + s.pos.slice(1);
    if (s.kind === 'room') posTxt += s.odd ? ' · faces rear' : ' · faces forward';
    if (s.kind === 'suite') posTxt += ' suite';
    $('#cardPos').textContent = `${posTxt} · Row ${s.row} · ${ci.config}`;
    const specs = $('#cardSpecs'); specs.innerHTML = '';
    for (const [k, v] of ci.specs) { const dt = document.createElement('dt'); dt.textContent = k; const dd = document.createElement('dd'); dd.textContent = v; specs.append(dt, dd); }
    const notes = $('#cardNotes'); notes.innerHTML = '';
    for (const n of s.notes) { const li = document.createElement('li'); li.textContent = n; notes.appendChild(li); }
    $('#sitBtn').hidden = !!fromSeat;
    $('#lookBtn').hidden = !!fromSeat || s.pos !== 'window';
    $('#card').hidden = false;
    this.dirty = true;
  }
  closeCard(keepSel) {
    $('#card').hidden = true;
    if (!keepSel) { this.sel = null; this.highlight(null); this.drawMap(); }
  }
  showSeatBar(s) {
    $('#seatBar').hidden = false;
    $('#seatBarId').textContent = s.id;
    $('#seatBarCls').textContent = CLASS_INFO[s.cls].short;
    this.updateBedBtn();
  }
  hideSeatBar() { $('#seatBar').hidden = true; }

  // ---------------- mini map ----------------
  mapGeom() {
    const cv = $('#map');
    const r = cv.getBoundingClientRect();
    return { cv, w: r.width, h: r.height };
  }
  drawMap() {
    const { cv, w, h } = this.mapGeom();
    if (!w) return;
    const d = Math.min(window.devicePixelRatio || 1, 2);
    if (cv.width !== Math.round(w * d)) { cv.width = Math.round(w * d); cv.height = Math.round(h * d); }
    const g = cv.getContext('2d');
    g.setTransform(d, 0, 0, d, 0, 0);
    g.clearRect(0, 0, w, h);
    const z0 = 2.2, z1 = 62.0, pad = 6;
    const sx = (w - pad * 2) / (z1 - z0), halfW = 3.05;
    const sy = (h - pad * 2) / (halfW * 2);
    const X = (z) => pad + (z - z0) * sx, Y = (x) => pad + (x + halfW) * sy;
    this.mapT = { X, Y, z0, z1, pad, sx, sy, halfW, w, h };
    g.fillStyle = 'rgba(210,222,240,0.07)'; g.strokeStyle = 'rgba(210,222,240,0.35)'; g.lineWidth = 1;
    g.beginPath();
    g.moveTo(X(2.4), Y(-1.3)); g.quadraticCurveTo(X(2.7), Y(-3.0), X(4.2), Y(-3.0)); g.lineTo(X(58.5), Y(-3.0)); g.quadraticCurveTo(X(61.7), Y(-2.9), X(61.7), Y(-1.5));
    g.lineTo(X(61.7), Y(1.5)); g.quadraticCurveTo(X(61.7), Y(2.9), X(58.5), Y(3.0)); g.lineTo(X(4.2), Y(3.0)); g.quadraticCurveTo(X(2.7), Y(3.0), X(2.4), Y(1.3)); g.closePath();
    g.fill(); g.stroke();
    g.fillStyle = 'rgba(255,196,90,0.9)';
    for (const c of CAB.doors) for (const s of [-1, 1]) g.fillRect(X(c - 0.5), Y(s * 3.0) - 1.5, 1.0 * sx, 3);
    g.fillStyle = 'rgba(200,210,225,0.28)';
    for (const m of this.L.mon) if (m.h > 0.5) g.fillRect(X(m.z0), Y(m.x0), (m.z1 - m.z0) * sx, (m.x1 - m.x0) * sy);
    for (const s of this.L.seats) {
      const ci = CLASS_INFO[s.cls];
      const on = this.sel === s || this.seated === s;
      g.fillStyle = on ? '#ffd166' : ci.color;
      g.globalAlpha = on ? 1 : 0.85;
      if (s.kind === 'room' || s.kind === 'suite') {
        const b = seatPickBox(s);
        const inset = s.kind === 'room' ? 0.06 : 0.05;
        g.fillRect(X(b[4] + inset), Y(b[0] + inset), Math.max(1, (b[5] - b[4] - 2 * inset) * sx), Math.max(1, (b[1] - b[0] - 2 * inset) * sy));
      } else {
        const sw = s.kind === 'py' ? 0.50 : 0.42, sl = 0.5;
        g.fillRect(X(s.z - sl), Y(s.x - sw / 2), Math.max(1, sl * sx - 0.5), Math.max(1, sw * sy - 0.5));
      }
    }
    g.globalAlpha = 1;
    const c = this.mode === 'xray' ? this.orbit.target : this.cam.pos;
    const cx = X(c[2]), cy = Y(c[0]);
    g.fillStyle = '#ffffff'; g.strokeStyle = '#0b1220'; g.lineWidth = 2;
    if (this.mode !== 'xray') {
      const dz = -Math.cos(this.cam.yaw), dx = -Math.sin(this.cam.yaw);
      const a = Math.atan2(dx * sy, dz * sx);
      g.save(); g.translate(cx, cy); g.rotate(a);
      g.fillStyle = 'rgba(255,255,255,0.28)';
      g.beginPath(); g.moveTo(0, 0); g.arc(0, 0, 16, -0.5, 0.5); g.closePath(); g.fill();
      g.restore();
    }
    g.beginPath(); g.arc(cx, cy, 3.8, 0, Math.PI * 2); g.fillStyle = '#ffffff'; g.fill(); g.stroke();
  }
  mapTap(u, v) {
    const T = this.mapT;
    if (!T) return;
    const z = T.z0 + ((u * T.w) - T.pad) / T.sx, x = ((v * T.h) - T.pad) / T.sy - T.halfW;
    let best = null, bd = 0.7;
    for (const s of this.L.seats) {
      let cx, cz;
      if (s.kind === 'room' || s.kind === 'suite') { const b = seatPickBox(s); cx = (b[0] + b[1]) / 2; cz = (b[4] + b[5]) / 2; }
      else { cx = s.x; cz = s.z - 0.25; }
      const d = Math.hypot((cx - x) * 0.8, cz - z);
      if (d < bd) { bd = d; best = s; }
    }
    if (best) { this.selectSeat(best); if (this.mode === 'xray') { this.orbit.target = [0, 0.6, best.z]; } return; }
    if (this.mode === 'xray') { this.orbit.target = [clamp(x, -1, 1), 0.6, clamp(z, 5, 60)]; this.dirty = true; this.drawMap(); return; }
    if (this.mode === 'seat') { this.seated = null; this.setBed(false); this.hideSeatBar(); this.mode = 'walk'; document.body.dataset.mode = 'walk'; }
    const q = this.nearestWalkable(x, z);
    this.flyTo({ pos: [q[0], 1.62, q[1]], yaw: this.cam.yaw, pitch: -0.05 }, 0.9);
  }

  // ---------------- tour ----------------
  startTour() {
    const S = (id) => this.L.seats.find((s) => s.id === id);
    const d3 = CAB.doors[2];
    const steps = [
      { mood: 'boarding', sky: 'day', dim: 0, walk: { pos: [1.32, 1.62, 5.55], yaw: Math.PI + 0.06, pitch: -0.06 }, title: 'Door 1', text: 'Boarding at the forward door. The 777-300ER has five pairs of Type A doors; THE Suite is just behind this one.' },
      { walk: { pos: [1.36, 1.62, 7.1], yaw: Math.PI, pitch: -0.2 }, title: 'THE Suite', text: 'Eight first-class suites, 1-2-1 in two rows. Sliding doors, an open top and dark wood and grey-brown finishes.' },
      { seat: '1A', title: 'Suite 1A', text: 'A 43 in 4K screen fills the front wall above a full-width ottoman. A long shelf runs along the windows.' },
      { bed: true, title: 'Lie flat', text: 'Seat and ottoman form a bed of roughly 76 to 81 in.' },
      { walk: { pos: [-1.43, 1.62, 17.9], yaw: Math.PI, pitch: -0.14 }, title: 'THE Room', text: '64 business seats. Odd rows face the tail beside the windows; even rows face forward by the aisle.' },
      { seat: '11A', title: 'Seat 11A', text: 'A rear-facing window seat. Its 24 in screen stands on the neighbour’s console, and its side table sits over their footwell.' },
      { walk: { pos: [0.0, 1.62, d3 - 0.1], yaw: 0, pitch: -0.05 }, title: 'Self-service bar', text: 'Between rows 16 and 17: two lavatories with bidets and a snack bar with backlit washi-style panels.' },
      { seat: '17A', window: true, title: 'Over the wing', text: 'Door 3 is the overwing exit. From row 17 the wing root and the huge GE90-115B engine sit just outside.' },
      { seat: '26A', title: 'Premium Economy', text: '24 seats, 2-4-2: 38 in pitch, 15.6 in screens, a leg rest and a bicycle-style footrest.' },
      { mood: 'sleep', sky: 'night', walk: { pos: [1.2, 1.62, 47.2], yaw: Math.PI, pitch: -0.05 }, title: 'Economy at night', text: '116 seats, 3-4-3 at 34 in pitch with 13.3 in screens. Tap any window to move its shade.' },
      { xray: true, mood: 'cruise', sky: 'day', dim: 0, title: 'The whole cabin', text: '212 seats: 8 THE Suite, 64 THE Room, 24 Premium Economy and 116 Economy.' },
    ];
    for (const st of steps) if (st.seat) st.seatObj = S(st.seat);
    this.tour = { steps, i: -1, t: 0 };
    $('#tourLabel').textContent = 'Stop tour';
    $('#tourBtn').setAttribute('aria-pressed', 'true');
    this.closeCard();
    this.nextTourStep();
  }
  nextTourStep() {
    const T = this.tour;
    if (!T) return;
    T.i++;
    if (T.i >= T.steps.length) { this.stopTour(); return; }
    const st = T.steps[T.i];
    if (st.mood) this.applyMood(st.mood);
    if (st.sky) this.applySky(st.sky);
    if (st.dim !== undefined) { this.scene.setAllWindows(st.dim); this.syncChips(); }
    if (st.xray) { if (this.seated) { this.setBed(false); this.seated = null; this.hideSeatBar(); } this.mode = 'walk'; this.setMode('xray'); }
    else if (st.walk) {
      if (this.mode === 'xray') { this.scene.xray = false; }
      if (this.seated) { this.setBed(false); this.seated = null; this.hideSeatBar(); }
      this.mode = 'walk'; document.body.dataset.mode = 'walk';
      this.flyTo(st.walk, 1.8);
    } else if (st.seatObj) { this.sit(st.seatObj); if (st.window) setTimeout(() => this.tour && this.lookOut(st.seatObj), 1300); }
    else if (st.bed) this.toggleBed();
    const cap = $('#caption');
    $('#capStep').textContent = `${T.i + 1} / ${T.steps.length}`;
    $('#capTitle').textContent = st.title;
    $('#capText').textContent = st.text;
    cap.hidden = false;
    T.next = performance.now() + (T.i === 0 ? 4200 : 5200);
    this.drawMap();
  }
  stopTour() {
    this.tour = null;
    $('#caption').hidden = true;
    $('#tourLabel').textContent = 'Guided tour';
    $('#tourBtn').setAttribute('aria-pressed', 'false');
  }

  // synchronous render (used by tests and screenshots)
  renderNow() {
    this.anim = null;
    const cam = this.camera();
    this.scene.render(cam, this.canvas.width, this.canvas.height, (performance.now() - this.t0) / 1000);
    this.G.gl.finish();
    return { calls: this.G.stats.calls, tris: this.G.stats.tris };
  }
  setView(pos, yaw, pitch, mode = 'walk') {
    if (mode === 'xray') { this.setMode('xray'); if (pos) this.orbit.target = pos; if (yaw !== undefined) this.orbit.az = yaw; if (pitch !== undefined) this.orbit.el = pitch; }
    else { if (this.mode === 'xray') this.setMode('walk'); this.cam.pos = [...pos]; this.cam.yaw = yaw; this.cam.pitch = pitch; }
    this.dirty = true;
  }

  // ---------------- loop ----------------
  loop(now) {
    requestAnimationFrame(this.loop);
    const dt = Math.min(0.05, (now - (this.prevT || now)) / 1000);
    this.prevT = now;
    // animation
    if (this.anim) {
      const a = this.anim;
      let t = clamp((now - a.t0) / a.dur, 0, 1);
      const e = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
      this.cam.pos = V3.lerp(a.from.pos, a.to.pos, e);
      this.cam.yaw = lerp(a.from.yaw, a.to.yaw, e);
      this.cam.pitch = lerp(a.from.pitch, a.to.pitch, e);
      if (t >= 1) this.anim = null;
      this.dirty = true;
    }
    // keyboard / joystick walking
    if (this.mode === 'walk' || this.mode === 'seat') {
      const k = this.keys;
      let f = 0, s = 0, turn = 0;
      if (k['w'] || k['arrowup']) f += 1;
      if (k['s'] || k['arrowdown']) f -= 1;
      if (k['a']) s -= 1;
      if (k['d']) s += 1;
      if (k['arrowleft'] || k['q']) turn += 1;
      if (k['arrowright'] || k['e']) turn -= 1;
      if (this.joy.active) { f += -this.joy.y; s += this.joy.x; }
      if ((f || s) && this.mode === 'seat') this.standUp();
      if (f || s) { this.moveBy(f * 1.45 * dt, s * 1.1 * dt); this.anim = null; this.mapDirty = true; }
      if (turn) { this.cam.yaw += turn * 1.6 * dt; this.dirty = true; }
    }
    if (this.mode === 'xray' && (this.keys['arrowup'] || this.keys['arrowdown'])) {
      this.orbit.target[2] = clamp(this.orbit.target[2] + (this.keys['arrowdown'] ? 6 : -6) * dt, 3, 61); this.dirty = true;
    }
    if (this.tour && now > this.tour.next && !this.anim) this.nextTourStep();
    const time = (now - this.t0) / 1000;
    const animSky = !this.scene.xray;
    const idleMs = now - this.lastInteract;
    // render continuously while interacting; when idle, throttle (clouds drift slowly past the windows)
    const every = idleMs < 2500 ? 0 : idleMs < 15000 ? 50 : 160;
    if (!this.dirty && !(animSky && (now - (this.lastRender || 0)) > every)) return;
    const t1 = performance.now();
    const cam = this.camera();
    this.scene.render(cam, this.canvas.width, this.canvas.height, time);
    this.lastRender = now;
    this.dirty = false;
    const ft = performance.now() - t1;
    this.frameMs = this.frameMs * 0.9 + ft * 0.1;
    this.frames = (this.frames || 0) + 1;
    if (this.mapDirty || this.frames % 10 === 0) { this.drawMap(); this.mapDirty = false; }
    // adaptive resolution when frames get slow (not in tests)
    if (!window.__TEST__ && this.frames % 60 === 0) {
      const slow = this.frameMs > 30, fast = this.frameMs < 12;
      const ds = this.dynScale || 1;
      if (slow && ds > 0.6) { this.dynScale = ds * 0.85; this.resize(); }
      else if (fast && ds < 1) { this.dynScale = Math.min(1, ds * 1.1); this.resize(); }
    }
  }
}

function rayBox(r, b) {
  let t0 = 0, t1 = 1e9;
  for (let a = 0; a < 3; a++) {
    const o = r.o[a], d = r.d[a], lo = b[a * 2], hi = b[a * 2 + 1];
    if (Math.abs(d) < 1e-9) { if (o < lo || o > hi) return null; continue; }
    let ta = (lo - o) / d, tb = (hi - o) / d;
    if (ta > tb) [ta, tb] = [tb, ta];
    t0 = Math.max(t0, ta); t1 = Math.min(t1, tb);
    if (t0 > t1) return null;
  }
  return t0;
}

function boot() {
  try {
    new App();
    document.body.dataset.ready = '1';
    window.__ready = true;
  } catch (e) {
    console.error(e);
    const f = $('#fatal');
    if (f) { f.hidden = false; $('#fatalMsg').textContent = /WebGL2/.test(e.message) ? 'This page needs WebGL 2, which this browser or device does not provide. Try a recent Chrome, Safari or Firefox.' : 'The 3D view could not start: ' + e.message; }
  }
}
