// Renderer, studio lighting, ground, camera + OrbitControls, camera presets and tweening.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { installToneMapping, loadHDR, StudioEnvironment, ContactShadow, CONTACT_LAYER, makeGrid } from './studio.js';

const _v = new THREE.Vector3();
const _v2 = new THREE.Vector3();
const _r = new THREE.Vector3();
const _u = new THREE.Vector3();
const _f = new THREE.Vector3();
const _corner = new THREE.Vector3();
const _t = new THREE.Vector3();

const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const Q_ = new URLSearchParams(location.search);

// Render quality by device class.  Phones: pixel ratio capped at 1.5 (1.0 while the camera moves: a drag, its
// damped coast after lift-off, a preset tween; the full ratio is re-rendered once the camera has been still for two
// frames; a tap never drops it), 1024 shadow map, 256 contact shadow.  ?dpr= / ?quality=low|high override (for tests
// and slow devices).
// index.html's boot script makes the same choice first (PC12_URLS.quality: it preloads the matching studio HDRI).
export const QUALITY = (() => {
  const coarse = !!(window.matchMedia && matchMedia('(pointer: coarse)').matches);
  const mobile = coarse || /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent || '');
  const force = Q_.get('quality');
  const boot = window.PC12_URLS && window.PC12_URLS.quality;
  const low = force ? force === 'low' : boot ? boot === 'low' : mobile;
  const dpr = window.devicePixelRatio || 1;
  const cap = +Q_.get('dpr') || (low ? 1.5 : 2);
  const dprMax = Math.min(dpr, cap);
  return {
    mobile, low, dprMax,
    dprMove: low ? Math.min(dprMax, 1) : dprMax,
    shadowMap: low ? 1024 : 2048,
    contactMap: low ? 256 : 512,
  };
})();

// Studio defaults (Blender hero: studio_small_09, AgX + "AgX - Punchy"): environment turned so neither octabox
// softbox sits on a preset's axis (at 150 one mirrored straight back into the port-side view and turned the
// cabin windows white); at 212 they light the wing leading edges and the nose shoulders of the 3/4 view
// and the glazing stays dark from the side.  Key light (shadows) from above the port bow.
// Per theme: the environment grade (StudioEnvironment.get: floor / walls / top / lift / strips) and the exposure
// (toneMappingExposure, linear):
//   light  the bright hangar of photo 130 / the Blender hangar render behind a white CSS cyclorama: the HDRI's black
//          foam lifted only to a dark grey overhead (lift 0.06, the hangar's ceiling) and to 0.3 round the horizon
//          (wallLift), rows of ceiling LED strips (strips 25, studio.js STRIPS) for the chrome, clear coat and glazing
//          to mirror, walls 0.8, exposure 1.9.  At hangar_port34's camera (photo 130 / Blender): cowl blue 77/112/177,
//          HSV saturation 0.56 (74/105/165, 0.54 / 62/101/175), exhaust stack p10/p90 75/204 (63/213 / 71/227), nose
//          tyre 63 (66 / 69), upper blade 63 (62 / 70), windshield median 90 with strip streaks over the dark cockpit.
//          The spinner (median 173) stays darker than the photo's blown-out mirror of white hangar walls (241)
//   dark   a dark cyclorama like the Blender hero (walls 0.3, floor 0.12) with the softboxes kept; exposure 2.6
//          matched at the hero's camera: blue median 47/82/141 (Blender 49/86/142)
// (The exposures are > 1 because the look is Blender's AgX + Punchy, which is ~0.8 stop darker in the mid-tones
// than three's plain AgX; see studio.js.)
// ?floor= ?walls= ?top= ?lift= ?strips= ?exposure= override these in both themes, ?look=punchy|base|agx|aces the curve (look
// development).
const qn = (k) => (Q_.has(k) && Q_.get(k) !== '' && isFinite(+Q_.get(k)) ? +Q_.get(k) : undefined);
const OVERRIDE = Object.fromEntries(['floor', 'walls', 'top', 'lift', 'wallLift', 'strips', 'exposure'].map((k) => [k, qn(k)]).filter(([, v]) => v !== undefined));
// the studio HDRI: 1k, or a 512 x 256 box-filtered copy on the low tier (phones: a quarter of the download, the same
// look at phone sizes); index.html's boot script picks and preloads it (PC12_URLS.hdr), ?hdr= overrides
const HDR = { high: '../assets/studio_small_09_1k.hdr', low: '../assets/studio_small_09_512.hdr' };
export const LOOK = {
  hdr: Q_.get('hdr') || (window.PC12_URLS && window.PC12_URLS.hdr) || new URL(QUALITY.low ? HDR.low : HDR.high, import.meta.url).href,
  envRot: qn('envrot') ?? 212,
  look: Q_.get('look') || 'punchy',
  theme: {
    light: { floor: 1, walls: 0.8, top: 0, lift: 0.06, wallLift: 0.3, strips: 25, exposure: 1.9, ...OVERRIDE },
    dark: { floor: 0.12, walls: 0.3, top: 0.4, lift: 0, strips: 0, exposure: 2.6, ...OVERRIDE },
  },
  keyDir: [-0.45, 0.8, -0.4],
  keyIntensity: qn('key') ?? 1.6,
};

// Camera presets.  `dir` points from the target to the camera (glTF axes: X starboard, Y up, Z aft);
// presets with `dir` are fitted to the aircraft's silhouette (a subsampled vertex set, not the
// bounding-box corners) and centred in the part of the viewport not covered by the panel/toolbar.
// `margin` > 1 leaves that fraction of air around the silhouette.
export const PRESETS = {
  three_quarter: { label: '3/4', dir: [-0.64, 0.24, -0.73], fov: 32, margin: 1.08 },   // front-port 3/4
  front: { label: 'Front', dir: [0, 0.07, -1], fov: 30, margin: 1.08 },
  side: { label: 'Side', dir: [-1, 0.04, 0], fov: 30, margin: 1.06 },         // port side: airstair + cargo doors
  top: { label: 'Top', dir: [0, 1, 0.0015], fov: 30, margin: 1.08 },
  // cockpit: flight_deck extras 'design eye' STA 3,980 / BL -335 / WL 2,360 (left seat)
  cockpit: { label: 'Cockpit', pos: [-0.335, 2.34, 3.98], target: [-0.29, 1.99, 3.1], fov: 74 },
  gear_bay: { label: 'Gear bay', pos: [4.3, 0.42, 3.55], target: [2.05, 0.78, 6.15], fov: 48 },
};

export class Stage {
  constructor(host) {
    this.host = host;
    // transparent canvas: the studio backdrop is a CSS gradient behind it (viewer.css #stage)
    const r = (this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' }));
    this.quality = QUALITY;
    this.dpr = QUALITY.dprMax;
    r.setPixelRatio(this.dpr);
    r.setClearColor(0x000000, 0);
    installToneMapping(r, LOOK.look);
    r.toneMappingExposure = LOOK.theme.light.exposure;     // setTheme() sets the theme's value
    r.outputColorSpace = THREE.SRGBColorSpace;
    r.localClippingEnabled = true;
    r.shadowMap.enabled = true;
    r.shadowMap.type = THREE.VSMShadowMap;      // soft studio shadow (only the ground receives it)
    r.shadowMap.autoUpdate = false;          // re-rendered only when the pose changes
    host.appendChild(r.domElement);
    r.domElement.tabIndex = 0;
    // WebGL context loss (phones drop the context of a backgrounded tab or under GPU memory pressure).  three.js
    // re-creates its GL state on 'webglcontextrestored' (its own listener runs first) and re-uploads geometry and
    // image textures, but render-target contents are gone: the prefiltered environment (PMREM), the contact shadow
    // and the shadow map are rebuilt here.  onContextChange(lost) lets the page show a note and stop rendering.
    this.contextLost = false;
    this.onContextChange = null;
    r.domElement.addEventListener('webglcontextlost', () => {
      this.contextLost = true;
      if (this.onContextChange) this.onContextChange(true);
    });
    r.domElement.addEventListener('webglcontextrestored', () => {
      this.contextLost = false;
      this._restoreGL();
      if (this.onContextChange) this.onContextChange(false);
    });

    const scene = (this.scene = new THREE.Scene());
    scene.background = null;
    this.envSource = 'none';

    this.camera = new THREE.PerspectiveCamera(35, 1, 0.05, 500);
    const c = (this.controls = new OrbitControls(this.camera, r.domElement));
    c.enableDamping = true;
    c.dampingFactor = 0.085;
    c.screenSpacePanning = true;
    c.minDistance = 0.05;
    c.maxDistance = 120;
    c.zoomSpeed = 1.1;
    // a preset view is re-fitted when the free viewport changes (panel opened/closed, resize)
    // until the user moves the camera
    this.preset = null;
    this.interacting = false;
    this.dragged = false;       // the pointer has moved the camera since 'start' (a tap has not)
    this.camMoving = false;     // the camera moved visibly this frame (drag, damping coast, tween)
    this._still = 0;            // frames the camera has been still
    this._lastEye = new THREE.Vector3();
    this._lastTarget = new THREE.Vector3();
    c.addEventListener('start', () => { this.preset = null; this.interacting = true; this.dragged = false; });
    c.addEventListener('change', () => { if (this.interacting) this.dragged = true; });
    c.addEventListener('end', () => { this.interacting = false; });

    // key light: soft shadows onto the ground (the environment does the rest of the lighting)
    const key = (this.key = new THREE.DirectionalLight(0xffffff, LOOK.keyIntensity));
    key.castShadow = true;
    key.shadow.mapSize.set(QUALITY.shadowMap, QUALITY.shadowMap);
    key.shadow.bias = -0.0004;
    key.shadow.normalBias = 0.02;
    key.shadow.radius = 10;
    key.shadow.blurSamples = 16;
    scene.add(key, key.target);

    // ground: key-light shadow catcher + contact shadow + fading grid
    const shadowPlane = (this.shadowPlane = new THREE.Mesh(
      new THREE.PlaneGeometry(120, 120),
      new THREE.ShadowMaterial({ opacity: 0.16, depthWrite: false })
    ));
    shadowPlane.rotation.x = -Math.PI / 2;
    shadowPlane.receiveShadow = true;
    shadowPlane.renderOrder = -1;
    shadowPlane.raycast = () => {};
    scene.add(shadowPlane);
    this.contact = new ContactShadow(r, { size: QUALITY.contactMap });
    scene.add(this.contact.group);
    this.grid = makeGrid();
    scene.add(this.grid);
    this.groundY = 0;          // lowered below exploded parts (see setGround)

    this.insets = { right: 0, bottom: 0, top: 0, left: 0 };
    this.modelBox = new THREE.Box3(new THREE.Vector3(-8.2, 0, 0.4), new THREE.Vector3(8.2, 4.3, 14.8));
    this.silhouette = null;     // Float32Array of silhouette sample points (world, rest pose)
    this.tween = null;
    this._sd = true;
    this.contactDirty = true;
    this.needsRender = true;
    this._near = 0.05;
    this.size = { w: 1, h: 1 };
    this.stats = { renders: 0, contactRenders: 0, shadowRenders: 0, lastRenderMs: 0 };
    // true while the pose animates (set by the render loop): on the low-quality tier the key-light shadow
    // map and the contact shadow (each a full pass over the ~700k-triangle model) follow every 3rd frame
    // only; the loop renders once more when the motion stops so they end exact
    this.busy = false;
    this._tick = 0;
    this.setTheme(window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches);
    this.resize();
  }

  // pose changes invalidate both shadows; keyShadowOnly() (a spinning prop) only the key-light map
  get shadowDirty() { return this._sd; }
  set shadowDirty(v) { this._sd = !!v; if (v) this.contactDirty = true; }
  keyShadowOnly() { this._sd = true; }

  // Environment: the studio HDRI (falls back to three's RoomEnvironment if it cannot be loaded).
  async loadEnvironment(url = LOOK.hdr, onProgress) {
    try {
      const hdr = await loadHDR(url, onProgress);
      this.studioEnv = new StudioEnvironment(this.renderer, hdr, LOOK.envRot);
      this._applyEnv();
    } catch (e) {
      console.warn('HDRI environment unavailable, using RoomEnvironment:', e && e.message ? e.message : e);
      this.useRoomEnvironment();
    }
  }
  _restoreGL() {
    // drop the dead PMREM textures without disposing them (their GL objects belong to the lost context)
    this.scene.environment = null;
    if (this.studioEnv) {
      this.studioEnv.cache.clear();
      this._applyEnv();
    } else if (this.envSource === 'room') this.useRoomEnvironment();
    this.contactDirty = true;
    this._sd = true;
    this.renderer.shadowMap.needsUpdate = true;
    this.needsRender = true;
  }
  useRoomEnvironment() {
    const pm = new THREE.PMREMGenerator(this.renderer);
    this.setEnvironment(pm.fromScene(new RoomEnvironment(), 0.04).texture, 'room');
    pm.dispose();
  }
  _applyEnv() {
    if (!this.studioEnv) return;
    const { floor, walls, top, lift, wallLift, strips } = LOOK.theme[this.dark ? 'dark' : 'light'];
    this.setEnvironment(this.studioEnv.get({ floor, walls, top, lift, wallLift, strips }), 'hdri');
  }
  setEnvironment(tex, source) {
    const old = this.scene.environment;
    if (old && old !== tex && !(this.studioEnv && [...this.studioEnv.cache.values()].includes(old))) old.dispose();
    this.scene.environment = tex;
    this.envSource = source;
    this.needsRender = true;
  }

  // meshes that darken the contact shadow
  addToContactLayer(root) {
    root.traverse((o) => { if (o.isMesh) o.layers.enable(CONTACT_LAYER); });
    this.contactDirty = true;
  }

  setTheme(dark) {
    const g = this.grid.material.uniforms;
    g.uColor.value.set(dark ? 0xc8d2dc : 0x1b2530);
    g.uAlpha.value = dark ? 0.07 : 0.07;
    this.shadowPlane.material.opacity = dark ? 0.3 : 0.16;
    this.contact.material.opacity = dark ? 0.85 : 0.62;
    this.dark = dark;
    this.renderer.toneMappingExposure = LOOK.theme[dark ? 'dark' : 'light'].exposure;
    this._applyEnv();
    this.needsRender = true;
  }

  // exploded parts can reach below Y = 0: the ground (grid + shadow catchers) drops with them
  setGround(y) {
    if (y === this.groundY) return;
    this.groundY = y;
    this.grid.position.y = y - 0.002;
    this.shadowPlane.position.y = y;
    this.contact.setGround(y + 0.001);
    this.shadowDirty = true;
    this.needsRender = true;
  }

  setModelBox(box, points = null) {
    this.modelBox.copy(box);
    this.silhouette = points;
    const c = box.getCenter(new THREE.Vector3());
    const k = this.key;
    k.target.position.copy(c);
    k.position.copy(c).add(_v.fromArray(LOOK.keyDir).normalize().multiplyScalar(18));
    const s = k.shadow.camera;
    const R = box.getSize(_v).length() * 0.55;
    s.left = -R; s.right = R; s.top = R; s.bottom = -R; s.near = 1; s.far = 40;
    s.updateProjectionMatrix();
    this.contact.fit(box, this.groundY + 0.001);
    this.grid.material.uniforms.uCenter.value.set(c.x, c.z);
    this.shadowDirty = true;
  }

  // Keep the model centred in the part of the canvas not covered by the panel (right / bottom) or a notch (left: the
  // safe-area inset): the camera renders a sub-window of a larger virtual image (setViewOffset) whose centre is the
  // centre of the free part.  `top` (the toolbar) is only reserved when fitting presets.
  setInsets(right, bottom, top = this.insets.top, left = 0) {
    this.insets.right = right | 0;
    this.insets.bottom = bottom | 0;
    this.insets.top = top | 0;
    this.insets.left = left | 0;
    this.resize();
  }

  resize() {
    const w = Math.max(1, this.host.clientWidth), h = Math.max(1, this.host.clientHeight);
    const key = `${w}x${h}:${this.insets.right},${this.insets.bottom},${this.insets.top},${this.insets.left}`;
    const changed = key !== this._fitKey;
    this._fitKey = key;
    this.size.w = w; this.size.h = h;
    this.renderer.setSize(w, h, false);
    const R = Math.min(this.insets.right, w * 0.6), B = Math.min(this.insets.bottom, h * 0.7);
    const L = Math.min(this.insets.left, w * 0.2);
    const fw = w + Math.abs(R - L), fh = h + B;
    const cam = this.camera;
    cam.aspect = fw / fh;
    if (R || B || L) cam.setViewOffset(fw, fh, Math.max(0, R - L), B, w, h);
    else cam.clearViewOffset();
    cam.updateProjectionMatrix();
    this.visible = { w: w - R - L, h: h - B, fh, top: Math.min(this.insets.top, (h - B) * 0.3) };
    this.needsRender = true;
    // an untouched preset view follows the free viewport (first fit, panel toggle, window resize)
    if (changed && this.preset && !this.tween) this.goTo(this.preset, { instant: true });
    else if (changed && this.preset && this.tween) this.goTo(this.preset, { duration: Math.max(0.2, this.tween.dur - this.tween.t * this.tween.dur) });
  }

  // distance so that `box` fits the visible viewport, looking along -dir at target
  fitDistance(dir, target, box, fov, margin = 1.1) {
    const k = this.visible.fh / (2 * Math.tan((fov * Math.PI) / 360)); // px per unit at distance 1
    const tanH = (0.5 * this.visible.w) / k, tanV = (0.5 * this.visible.h) / k;
    _f.copy(dir).normalize();                 // from target toward camera
    _r.crossVectors(_v.set(0, 1, 0), _f);
    if (_r.lengthSq() < 1e-8) _r.set(1, 0, 0);
    _r.normalize();
    _u.crossVectors(_f, _r).normalize();
    let d = 0;
    for (let i = 0; i < 8; i++) {
      _corner.set(i & 1 ? box.max.x : box.min.x, i & 2 ? box.max.y : box.min.y, i & 4 ? box.max.z : box.min.z).sub(target);
      const depth = _corner.dot(_f);          // toward the camera
      d = Math.max(d, depth + Math.abs(_corner.dot(_r)) / tanH, depth + Math.abs(_corner.dot(_u)) / tanV);
    }
    return d * margin;
  }

  // Fit a point cloud: camera looks along -dir; returns {pos, target} so that every point lies in the
  // free viewport rectangle (right/bottom panel insets and the top toolbar excluded) with the
  // silhouette centred in it.  Perspective-exact per point; a few fixed-point iterations for centring.
  fitPoints(dir, pts, fov, margin = 1.06) {
    const vis = this.visible;
    const k = vis.fh / (2 * Math.tan((fov * Math.PI) / 360));           // px per unit tangent
    // free rectangle in tangent units relative to the optical axis (the centre of the uncovered area)
    const halfW = (0.5 * vis.w) / k, halfH = (0.5 * (vis.h - vis.top)) / k;
    const offY = (-0.5 * vis.top) / k;                                   // rectangle centre (toolbar pushes it down)
    _f.copy(dir).normalize();
    _r.crossVectors(_v.set(0, 1, 0), _f);
    if (_r.lengthSq() < 1e-8) _r.set(1, 0, 0);
    _r.normalize();
    _u.crossVectors(_f, _r).normalize();
    const n = pts.length / 3;
    const target = this.modelBox.getCenter(new THREE.Vector3());
    let d = 0;
    for (let it = 0; it < 6; it++) {
      // distance at which the (centred) silhouette just fits
      d = 0;
      for (let i = 0; i < n; i++) {
        _t.set(pts[3 * i] - target.x, pts[3 * i + 1] - target.y, pts[3 * i + 2] - target.z);
        const z = _t.dot(_f);
        d = Math.max(d, z + Math.abs(_t.dot(_r)) / (halfW / margin), z + Math.abs(_t.dot(_u)) / (halfH / margin));
      }
      // projected extents at that distance -> move the target so they are centred
      let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
      for (let i = 0; i < n; i++) {
        _t.set(pts[3 * i] - target.x, pts[3 * i + 1] - target.y, pts[3 * i + 2] - target.z);
        const den = Math.max(1e-3, d - _t.dot(_f));
        const x = _t.dot(_r) / den, y = _t.dot(_u) / den;
        if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
      }
      const cx = 0.5 * (x0 + x1), cy = 0.5 * (y0 + y1);
      if (Math.abs(cx) < 1e-4 && Math.abs(cy) < 1e-4) break;
      target.addScaledVector(_r, cx * d).addScaledVector(_u, cy * d);
    }
    // shift so the silhouette centre lands in the centre of the free rectangle (below the toolbar)
    target.addScaledVector(_u, -offY * d);
    return { pos: target.clone().addScaledVector(_f, d), target };
  }

  presetView(name) {
    const p = PRESETS[name];
    if (!p) return null;
    if (p.pos) return { pos: new THREE.Vector3().fromArray(p.pos), target: new THREE.Vector3().fromArray(p.target), fov: p.fov };
    const dir = new THREE.Vector3().fromArray(p.dir).normalize();
    let pts = this.silhouette;
    if (!pts) {   // before the model is loaded: the box corners
      const b = this.modelBox;
      pts = new Float32Array(24);
      for (let i = 0; i < 8; i++) pts.set([i & 1 ? b.max.x : b.min.x, i & 2 ? b.max.y : b.min.y, i & 4 ? b.max.z : b.min.z], 3 * i);
    }
    const v = this.fitPoints(dir, pts, p.fov, p.margin || 1.06);
    return { pos: v.pos, target: v.target, fov: p.fov };
  }

  // frame a box keeping the current viewing direction
  frameBox(box, { instant = false, minDist = 1.2 } = {}) {
    const target = box.getCenter(new THREE.Vector3());
    const dir = _v2.subVectors(this.camera.position, this.controls.target);
    if (dir.lengthSq() < 1e-8) dir.set(-0.6, 0.35, -0.7);
    dir.normalize();
    const fov = Math.min(this.camera.fov, 45);
    const d = Math.max(minDist, this.fitDistance(dir, target, box, fov, 1.6));
    this.goTo({ pos: target.clone().addScaledVector(dir, d), target, fov }, { instant });
  }

  goTo(view, { instant = false, duration = 0.9 } = {}) {
    if (typeof view === 'string') {
      const name = view;
      view = this.presetView(name);
      if (!view) return;
      this.preset = PRESETS[name].dir ? name : null;    // fitted presets follow later viewport changes
    } else this.preset = null;
    if (!view) return;
    const pos = view.pos.isVector3 ? view.pos.clone() : new THREE.Vector3().fromArray(view.pos);
    const target = view.target.isVector3 ? view.target.clone() : new THREE.Vector3().fromArray(view.target);
    const fov = view.fov || this.camera.fov;
    // flush any residual damping so it does not fight the tween
    const c = this.controls;
    c.enableDamping = false; c.update(); c.enableDamping = true;
    if (instant) {
      this.tween = null;
      this.camera.position.copy(pos);
      c.target.copy(target);
      this.camera.fov = fov;
      this.camera.updateProjectionMatrix();
      c.update();
      this.camera.updateMatrixWorld();
      this.needsRender = true;
      return;
    }
    this.tween = {
      p0: this.camera.position.clone(), t0: c.target.clone(), f0: this.camera.fov,
      p1: pos, t1: target, f1: fov, t: 0, dur: duration,
    };
  }

  // returns true while something camera-related changed
  update(dt) {
    let active = false;
    const tw = this.tween;
    if (tw) {
      tw.t = Math.min(1, tw.t + dt / tw.dur);
      const e = ease(tw.t);
      this.camera.position.lerpVectors(tw.p0, tw.p1, e);
      this.controls.target.lerpVectors(tw.t0, tw.t1, e);
      this.camera.fov = tw.f0 + (tw.f1 - tw.f0) * e;
      this.camera.updateProjectionMatrix();
      if (tw.t >= 1) this.tween = null;
      active = true;
    }
    if (this.controls.update()) active = true;
    // near plane follows the orbit distance (cockpit needs ~1 cm, exterior views don't)
    const dist = this.camera.position.distanceTo(this.controls.target);
    const near = Math.min(0.2, Math.max(0.01, dist * 0.005));
    if (Math.abs(near - this._near) > this._near * 0.15) {
      this._near = near;
      this.camera.near = near;
      this.camera.updateProjectionMatrix();
      active = true;
    }
    // visible motion: eye + target displacement per frame relative to the orbit distance.  OrbitControls reports a
    // change only once the damped coast has accumulated 1 mm, so near the end of a coast it says "moved" every few
    // frames; below ~0.2 mm per metre (a fraction of a pixel) the camera counts as still, so the pixel ratio does not
    // flip back and forth (a drawing-buffer reallocation each time).
    const moved = this.camera.position.distanceTo(this._lastEye) + this.controls.target.distanceTo(this._lastTarget);
    this._lastEye.copy(this.camera.position);
    this._lastTarget.copy(this.controls.target);
    this.camMoving = !!this.tween || moved > 2e-4 * Math.max(dist, 0.5);
    return active;
  }

  // phones: lower pixel ratio while the camera moves (drag, damping coast, tween), the full ratio again after two
  // still frames (one render).  A tap (no 'change' between 'start' and 'end') keeps the full ratio.
  applyQuality() {
    const moving = (this.interacting && this.dragged) || !!this.tween || this.camMoving;
    this._still = moving ? 0 : this._still + 1;
    const want = moving ? this.quality.dprMove : this._still >= 2 ? this.quality.dprMax : this.dpr;
    if (want === this.dpr) return false;
    this.dpr = want;
    this.renderer.setPixelRatio(want);     // r160: setPixelRatio() re-applies setSize() itself (one buffer realloc)
    this.needsRender = true;
    return true;
  }

  render() {
    if (this.contextLost) return;
    const t0 = performance.now();
    const st = this.stats;
    const skip = this.quality.low && this.busy && (this._tick++ % 3) !== 0;
    if (this.contactDirty && !skip) {
      this.contact.update(this.scene);
      this.contactDirty = false;
      st.contactRenders++;
    }
    if (this._sd && !skip) {
      this.renderer.shadowMap.needsUpdate = true;
      this._sd = false;
      st.shadowRenders++;
    }
    this.renderer.render(this.scene, this.camera);
    this.needsRender = false;
    st.renders++;
    st.lastRenderMs = performance.now() - t0;
  }

  cameraState() {
    return {
      pos: this.camera.position.toArray(),
      target: this.controls.target.toArray(),
      fov: this.camera.fov,
    };
  }
}
