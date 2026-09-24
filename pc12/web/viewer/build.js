// Step-by-step build: construction lines are drawn first, then the step's parts fly in from an
// exaggerated explode offset.  Skins stay in primer until the final 'paint' step.
import * as THREE from 'three';

const KIND_COLORS = {
  datum: 0xd9480f, line: 0x1c7ed6, section: 0x0c9f74, tick: 0x7a838c, spar: 0xe8590c,
  axis: 0xae3ec9, mac: 0x2f9e44, arc: 0xf08c00, dim: 0x5c6670, circle: 0x7048e8,
};
const LINE_DUR = 0.9;      // s to draw a step's construction lines
const FLY_START = 0.55;    // s after the step starts
const FLY_DUR = 1.2;       // s per part
const STAGGER = 0.14;      // s between parts

const _v = new THREE.Vector3();
const hex = (c) => '#' + c.toString(16).padStart(6, '0');

export class Build {
  constructor({ model, meta, scene, labelsEl }) {
    this.model = model;
    this.steps = meta.steps;
    this.n = this.steps.length;
    this.index = this.n - 1;
    this.time = 0;
    this.t0 = -100;
    this.playing = false;
    this.showAllLines = false;
    this.flying = [];
    this.lineProg = 1;
    this.labelsEl = labelsEl;
    this.key = (i) => this.steps[i] && this.steps[i].key;
    this.indexOf = (key) => this.steps.findIndex((s) => s.key === key);
    this.paintIndex = this.indexOf('paint');
    this.root = new THREE.Group();
    this.root.name = 'construction';
    scene.add(this.root);
    this.groups = this.steps.map((s) => this._makeGroup((meta.construction || {})[s.key] || []));
    // parts per step, in order; children of a part in the same step share its start time
    this.stepParts = this.steps.map((_, i) => model.list.filter((p) => p.stepIndex === i));
    this.listeners = [];
  }

  onChange(fn) { this.listeners.push(fn); }
  _emit() { for (const fn of this.listeners) fn(this.index); }

  _makeGroup(items) {
    const g = new THREE.Group();
    g.visible = false;
    this.root.add(g);
    const mats = new Map();
    const matFor = (kind) => {
      if (!mats.has(kind)) {
        const color = KIND_COLORS[kind] || 0x495057;
        const opts = { color, transparent: true, opacity: 0, depthTest: false, depthWrite: false, fog: false, toneMapped: false };
        mats.set(kind, kind === 'axis' || kind === 'dim'
          ? new THREE.LineDashedMaterial({ ...opts, dashSize: 0.12, gapSize: 0.07 })
          : new THREE.LineBasicMaterial(opts));
      }
      return mats.get(kind);
    };
    const lines = [], labels = [], fills = [];
    for (const it of items) {
      if (!it.pts || it.pts.length < 2) continue;
      const pts = it.pts.map((p) => new THREE.Vector3(p[0], p[1], p[2]));
      const geo = new THREE.BufferGeometry().setFromPoints(pts);
      const line = new THREE.Line(geo, matFor(it.kind));
      if (it.kind === 'axis' || it.kind === 'dim') line.computeLineDistances();
      line.renderOrder = 20;
      line.raycast = () => {};
      line.userData.n = pts.length;
      g.add(line);
      lines.push(line);
      if (it.kind === 'datum') {
        // translucent datum plane inside its outline
        const box = new THREE.Box3().setFromPoints(pts);
        const size = box.getSize(new THREE.Vector3()), c = box.getCenter(new THREE.Vector3());
        const m = new THREE.MeshBasicMaterial({ color: KIND_COLORS.datum, transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide, fog: false });
        const plane = new THREE.Mesh(new THREE.PlaneGeometry(Math.max(size.x, 0.01), Math.max(size.y, 0.01)), m);
        plane.position.copy(c);
        plane.raycast = () => {};
        plane.renderOrder = 19;
        g.add(plane);
        fills.push(plane);
      }
      if (it.label) {
        const el = document.createElement('div');
        el.className = 'cl';
        el.textContent = it.label;
        el.style.color = hex(KIND_COLORS[it.kind] || 0x495057);
        this.labelsEl.appendChild(el);
        const k = it.pts.length;
        const anchor = it.kind === 'dim' || it.kind === 'mac'
          ? pts[0].clone().add(pts[k - 1]).multiplyScalar(0.5)
          : it.kind === 'tick' ? pts[k - 1].clone() : pts[0].clone();
        labels.push({ el, anchor, on: false });
      }
    }
    return { g, mats, lines, labels, fills };
  }

  // group display state: current step lines draw in over everything; with "Lines" on, earlier
  // steps' lines stay visible (dimmer, depth-tested)
  _styleGroups() {
    this.groups.forEach((gr, i) => {
      const current = i === this.index;
      const vis = current || (this.showAllLines && i < this.index);
      gr.g.visible = vis && (gr.lines.length > 0);
      if (!vis) return;
      const prog = current ? this.lineProg : 1;
      const op = current ? 0.95 * Math.min(1, prog * 1.6) : 0.4;
      for (const m of gr.mats.values()) { m.opacity = op; m.depthTest = !current; }
      for (const f of gr.fills) f.material.opacity = (current ? 0.08 : 0.04) * Math.min(1, prog * 1.6);
      for (const l of gr.lines) {
        const n = l.userData.n;
        l.geometry.setDrawRange(0, prog >= 1 ? n : Math.max(2, Math.ceil(n * prog)));
      }
    });
  }

  setShowAllLines(on) { this.showAllLines = !!on; this._styleGroups(); }

  setStep(i, { instant = false } = {}) {
    if (typeof i === 'string') i = this.indexOf(i);
    i = Math.max(0, Math.min(this.n - 1, i | 0));
    this.index = i;
    this.t0 = this.time;
    this.flying = [];
    const starts = new Map();
    let k = 0;
    for (const p of this.model.list) {
      if (p.stepIndex < i) { p.buildVisible = true; p.fly = 0; }
      else if (p.stepIndex > i) { p.buildVisible = false; p.fly = 0; }
      else if (instant) { p.buildVisible = true; p.fly = 0; }
      else {
        let start;
        if (p.parent && starts.has(p.parent.id)) start = starts.get(p.parent.id);
        else start = FLY_START + STAGGER * k++;
        starts.set(p.id, start);
        p.buildVisible = false;
        p.fly = 1;
        this.flying.push({ rec: p, start });
      }
    }
    this.stepDuration = Math.max(3.6, FLY_START + STAGGER * Math.max(0, k - 1) + FLY_DUR + 1.8);
    this.lineProg = instant ? 1 : 0;
    this._styleGroups();
    this.model.updateVisibility();
    this.model.setPaint(i >= this.paintIndex, instant);
    this._emit();
  }

  next() { if (this.index < this.n - 1) this.setStep(this.index + 1); else this.playing = false; }
  prev() { this.playing = false; if (this.index > 0) this.setStep(this.index - 1); }

  play(on = !this.playing) {
    this.playing = !!on;
    if (this.playing && this.index >= this.n - 1) this.setStep(0);
    else if (this.playing && this.time - this.t0 > this.stepDuration) this.next();
    this._emit();
  }

  get animating() { return this.flying.length > 0 || this.lineProg < 1; }

  // returns true while something is animating
  update(dt) {
    this.time += dt;
    const tt = this.time - this.t0;
    let active = false;
    if (this.lineProg < 1) {
      this.lineProg = Math.min(1, tt / LINE_DUR);
      this._styleGroups();
      active = true;
    }
    if (this.flying.length) {
      let vis = false, done = 0;
      for (const f of this.flying) {
        const p = f.rec;
        const s = (tt - f.start) / FLY_DUR;
        if (s < 0) continue;
        if (!p.buildVisible) { p.buildVisible = true; vis = true; }
        const e = Math.min(1, s);
        p.fly = Math.pow(1 - e, 3);            // ease-out: fast approach, soft landing
        if (e >= 1) { p.fly = 0; f.done = true; done++; }
      }
      if (done) this.flying = this.flying.filter((f) => !f.done);
      if (vis) this.model.updateVisibility();
      active = true;
    }
    if (this.playing) {
      active = true;
      if (tt >= this.stepDuration) {
        if (this.index < this.n - 1) this.setStep(this.index + 1);
        else { this.playing = false; this._emit(); }
      }
    }
    return active;
  }

  // project construction labels (only for visible groups); a label that would overlap one
  // already placed is hidden (current step first), so crowded areas stay readable
  updateLabels(camera, w, h) {
    const placed = this._placed || (this._placed = new Float32Array(4 * 128));
    let np = 0;
    const order = this._order || (this._order = []);
    order.length = 0;
    order.push(this.index);
    for (let i = 0; i < this.groups.length; i++) if (i !== this.index) order.push(i);
    for (const i of order) {
      const gr = this.groups[i];
      const show = gr.g.visible && (i === this.index ? this.lineProg > 0.6 : true);
      for (const lb of gr.labels) {
        let on = false;
        if (show) {
          _v.copy(lb.anchor).project(camera);
          if (_v.z < 1 && _v.x > -1.1 && _v.x < 1.1 && _v.y > -1.1 && _v.y < 1.1) {
            const x = ((_v.x + 1) / 2) * w, y = ((1 - _v.y) / 2) * h;
            if (!lb.w) lb.w = lb.el.offsetWidth || 60;
            const x0 = x - lb.w / 2 - 2, x1 = x + lb.w / 2 + 2, y0 = y - 23, y1 = y - 5;
            on = true;
            for (let k = 0; k < np; k++) {
              const o = k * 4;
              if (x0 < placed[o + 2] && x1 > placed[o] && y0 < placed[o + 3] && y1 > placed[o + 1]) { on = false; break; }
            }
            if (on) {
              if (np < 128) { const o = np * 4; placed[o] = x0; placed[o + 1] = y0; placed[o + 2] = x1; placed[o + 3] = y1; np++; }
              lb.el.style.transform = `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px) translate(-50%, -130%)`;
            }
          }
        }
        if (on !== lb.on) { lb.el.classList.toggle('on', on); lb.on = on; }
      }
    }
  }
}
