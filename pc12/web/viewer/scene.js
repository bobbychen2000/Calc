// Renderer, studio lighting, ground, camera + OrbitControls, camera presets and tweening.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const _v = new THREE.Vector3();
const _v2 = new THREE.Vector3();
const _r = new THREE.Vector3();
const _u = new THREE.Vector3();
const _f = new THREE.Vector3();
const _corner = new THREE.Vector3();
const _t = new THREE.Vector3();

const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

// Camera presets.  `dir` points from the target to the camera (glTF axes: X starboard, Y up, Z aft);
// presets with `dir` are fitted to the aircraft's silhouette (a subsampled vertex set, not the
// bounding-box corners) and centred in the part of the viewport not covered by the panel/toolbar.
// `margin` > 1 leaves that fraction of air around the silhouette.
export const PRESETS = {
  three_quarter: { label: '3/4', dir: [-0.62, 0.34, -0.71], fov: 35, margin: 1.08 },
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
    const r = (this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' }));
    r.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    r.toneMapping = THREE.ACESFilmicToneMapping;
    r.toneMappingExposure = 1.0;
    r.outputColorSpace = THREE.SRGBColorSpace;
    r.localClippingEnabled = true;
    r.shadowMap.enabled = true;
    r.shadowMap.type = THREE.PCFSoftShadowMap;
    r.shadowMap.autoUpdate = false;          // re-rendered only when the pose changes
    host.appendChild(r.domElement);
    r.domElement.tabIndex = 0;

    const scene = (this.scene = new THREE.Scene());
    const pm = new THREE.PMREMGenerator(r);
    scene.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture;
    pm.dispose();

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
    c.addEventListener('start', () => { this.preset = null; });

    // lights: environment (studio room) + one shadow-casting key light + soft sky fill
    const key = (this.key = new THREE.DirectionalLight(0xffffff, 2.2));
    key.castShadow = true;
    key.shadow.mapSize.set(2048, 2048);
    key.shadow.bias = -0.0004;
    key.shadow.normalBias = 0.02;
    key.shadow.radius = 3;
    scene.add(key, key.target);
    this.hemi = new THREE.HemisphereLight(0xffffff, 0xb4bcc4, 0.9);
    scene.add(this.hemi);

    // ground: shadow catcher + grid (faded by fog)
    const shadowPlane = (this.shadowPlane = new THREE.Mesh(
      new THREE.PlaneGeometry(120, 120),
      new THREE.ShadowMaterial({ opacity: 0.2, depthWrite: false })
    ));
    shadowPlane.rotation.x = -Math.PI / 2;
    shadowPlane.receiveShadow = true;
    shadowPlane.renderOrder = -1;
    scene.add(shadowPlane);
    this.grid = null;
    this.groundY = 0;          // lowered below exploded parts (see setGround)
    scene.fog = new THREE.Fog(0xe9ecef, 45, 110);

    this.insets = { right: 0, bottom: 0, top: 0 };
    this.modelBox = new THREE.Box3(new THREE.Vector3(-8.2, 0, 0.4), new THREE.Vector3(8.2, 4.3, 14.8));
    this.silhouette = null;     // Float32Array of silhouette sample points (world, rest pose)
    this.tween = null;
    this.shadowDirty = true;
    this.needsRender = true;
    this._near = 0.05;
    this.size = { w: 1, h: 1 };
    this.setTheme(window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches);
    this.resize();
  }

  setTheme(dark) {
    const bg = new THREE.Color(dark ? 0x14181c : 0xe9ecef);
    this.scene.background = bg;
    this.scene.fog.color.copy(bg);
    // grid: centre lines darker; rebuilt so the vertex colours follow the theme
    if (this.grid) { this.scene.remove(this.grid); this.grid.geometry.dispose(); this.grid.material.dispose(); }
    const grid = (this.grid = new THREE.GridHelper(60, 60, dark ? 0x56626e : 0x8e99a3, dark ? 0x2b333b : 0xc6ccd2));
    grid.material.transparent = true;
    grid.material.opacity = dark ? 0.8 : 0.6;
    grid.material.depthWrite = false;
    grid.position.y = this.groundY - 0.002;
    this.scene.add(grid);
    this.shadowPlane.material.opacity = dark ? 0.35 : 0.2;
    this.hemi.groundColor.set(dark ? 0x6a7480 : 0xb4bcc4);
    this.dark = dark;
    this.needsRender = true;
  }

  // exploded parts can reach below Y = 0: the ground (grid + shadow catcher) drops with them
  setGround(y) {
    if (y === this.groundY) return;
    this.groundY = y;
    this.grid.position.y = y - 0.002;
    this.shadowPlane.position.y = y;
    this.shadowDirty = true;
    this.needsRender = true;
  }

  setModelBox(box, points = null) {
    this.modelBox.copy(box);
    this.silhouette = points;
    const c = box.getCenter(new THREE.Vector3());
    const k = this.key;
    k.target.position.copy(c);
    k.position.copy(c).add(_v.set(-7, 13, -6));
    const s = k.shadow.camera;
    const R = box.getSize(_v).length() * 0.55;
    s.left = -R; s.right = R; s.top = R; s.bottom = -R; s.near = 1; s.far = 45;
    s.updateProjectionMatrix();
    this.shadowDirty = true;
  }

  // Keep the model centred in the part of the canvas not covered by the panel:
  // the camera renders a sub-window of a larger virtual image (setViewOffset).
  // `top` (the toolbar) is only reserved when fitting presets.
  setInsets(right, bottom, top = this.insets.top) {
    this.insets.right = right | 0;
    this.insets.bottom = bottom | 0;
    this.insets.top = top | 0;
    this.resize();
  }

  resize() {
    const w = Math.max(1, this.host.clientWidth), h = Math.max(1, this.host.clientHeight);
    const key = `${w}x${h}:${this.insets.right},${this.insets.bottom},${this.insets.top}`;
    const changed = key !== this._fitKey;
    this._fitKey = key;
    this.size.w = w; this.size.h = h;
    this.renderer.setSize(w, h, false);
    const R = Math.min(this.insets.right, w * 0.6), B = Math.min(this.insets.bottom, h * 0.7);
    const fw = w + R, fh = h + B;
    const cam = this.camera;
    cam.aspect = fw / fh;
    if (R || B) cam.setViewOffset(fw, fh, R, B, w, h);
    else cam.clearViewOffset();
    cam.updateProjectionMatrix();
    this.visible = { w: w - R, h: h - B, fh, top: Math.min(this.insets.top, (h - B) * 0.3) };
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
    return active;
  }

  render() {
    if (this.shadowDirty) {
      this.renderer.shadowMap.needsUpdate = true;
      this.shadowDirty = false;
    }
    this.renderer.render(this.scene, this.camera);
    this.needsRender = false;
  }

  cameraState() {
    return {
      pos: this.camera.position.toArray(),
      target: this.controls.target.toArray(),
      fov: this.camera.fov,
    };
  }
}
