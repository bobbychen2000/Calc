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

const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

// Camera presets.  `dir` points from the target to the camera (glTF axes: X starboard, Y up, Z aft);
// presets with `dir` are distance-fitted to the whole aircraft in the visible part of the viewport.
export const PRESETS = {
  three_quarter: { label: '3/4', dir: [-0.62, 0.34, -0.71], fov: 35 },
  front: { label: 'Front', dir: [0, 0.07, -1], fov: 30 },
  side: { label: 'Side', dir: [-1, 0.04, 0], fov: 30 },         // port side: airstair + cargo doors
  top: { label: 'Top', dir: [0, 1, 0.0015], fov: 30 },
  cockpit: { label: 'Cockpit', pos: [-0.30, 2.06, 4.02], target: [-0.26, 1.93, 3.55], fov: 68 },
  gear_bay: { label: 'Gear bay', pos: [3.35, 0.32, 4.75], target: [2.2, 0.92, 6.25], fov: 55 },
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

    // lights: environment (studio room) + one shadow-casting key light + soft sky fill
    const key = (this.key = new THREE.DirectionalLight(0xffffff, 2.2));
    key.castShadow = true;
    key.shadow.mapSize.set(2048, 2048);
    key.shadow.bias = -0.0004;
    key.shadow.normalBias = 0.02;
    key.shadow.radius = 3;
    scene.add(key, key.target);
    this.hemi = new THREE.HemisphereLight(0xffffff, 0x8a96a3, 0.35);
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
    scene.fog = new THREE.Fog(0xe9ecef, 45, 110);

    this.insets = { right: 0, bottom: 0 };
    this.modelBox = new THREE.Box3(new THREE.Vector3(-8.2, 0, 0.4), new THREE.Vector3(8.2, 4.3, 14.8));
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
    grid.position.y = -0.002;
    this.scene.add(grid);
    this.shadowPlane.material.opacity = dark ? 0.35 : 0.2;
    this.hemi.groundColor.set(dark ? 0x3a4450 : 0x8a96a3);
    this.dark = dark;
    this.needsRender = true;
  }

  setModelBox(box) {
    this.modelBox.copy(box);
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
  setInsets(right, bottom) {
    this.insets.right = right | 0;
    this.insets.bottom = bottom | 0;
    this.resize();
  }

  resize() {
    const w = Math.max(1, this.host.clientWidth), h = Math.max(1, this.host.clientHeight);
    this.size.w = w; this.size.h = h;
    this.renderer.setSize(w, h, false);
    const R = Math.min(this.insets.right, w * 0.6), B = Math.min(this.insets.bottom, h * 0.7);
    const fw = w + R, fh = h + B;
    const cam = this.camera;
    cam.aspect = fw / fh;
    if (R || B) cam.setViewOffset(fw, fh, R, B, w, h);
    else cam.clearViewOffset();
    cam.updateProjectionMatrix();
    this.visible = { w: w - R, h: h - B, fh };
    this.needsRender = true;
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

  presetView(name) {
    const p = PRESETS[name];
    if (!p) return null;
    if (p.pos) return { pos: new THREE.Vector3().fromArray(p.pos), target: new THREE.Vector3().fromArray(p.target), fov: p.fov };
    const box = this.modelBox;
    const target = box.getCenter(new THREE.Vector3());
    if (name === 'three_quarter') target.y -= 0.35;
    const dir = new THREE.Vector3().fromArray(p.dir).normalize();
    const d = this.fitDistance(dir, target, box, p.fov, name === 'three_quarter' ? 1.02 : 1.06);
    return { pos: target.clone().addScaledVector(dir, d), target, fov: p.fov };
  }

  // frame a box keeping the current viewing direction
  frameBox(box, { instant = false, minDist = 1.2 } = {}) {
    const target = box.getCenter(new THREE.Vector3());
    const dir = _v2.subVectors(this.camera.position, this.controls.target);
    if (dir.lengthSq() < 1e-8) dir.set(-0.6, 0.35, -0.7);
    dir.normalize();
    const fov = Math.min(this.camera.fov, 45);
    const d = Math.max(minDist, this.fitDistance(dir, target, box, fov, 1.35));
    this.goTo({ pos: target.clone().addScaledVector(dir, d), target, fov }, { instant });
  }

  goTo(view, { instant = false, duration = 0.9 } = {}) {
    if (typeof view === 'string') view = this.presetView(view);
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
