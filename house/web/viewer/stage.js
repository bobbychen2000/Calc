// Stage: renderer, sky, sun + shadows, image-based light, cameras.
// World (model) axes: x right along the street, y into the lot, z up.  three axes: X = x, Y = z, Z = -y.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { Sky } from 'three/addons/objects/Sky.js';

export const toGL = (p) => new THREE.Vector3(p[0], p[2], -p[1]);

export const LOOK = {
  day: { exposure: 0.62, sun: 3.4, sunColor: 0xfff1dc, sky: 1.0, turbidity: 3.2, rayleigh: 1.1, env: 1.0, hemi: 0.0 },
  dusk: { exposure: 0.85, sun: 0.25, sunColor: 0xffb08a, sky: 1.0, turbidity: 6.0, rayleigh: 2.6, env: 1.0, hemi: 0.0 },
  shadow: { size: 4096, half: 34, near: 1, far: 220, bias: -0.00025, normalBias: 0.035, radius: 2.5 },
};

export class Stage {
  constructor(canvas) {
    this.canvas = canvas;
    const r = this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
    r.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    r.outputColorSpace = THREE.SRGBColorSpace;
    r.toneMapping = THREE.ACESFilmicToneMapping;
    r.shadowMap.enabled = true;
    r.shadowMap.type = THREE.PCFSoftShadowMap;
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(40, 1, 0.1, 2000);
    this.camera.position.set(-18, 9, 26);
    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.maxPolarAngle = Math.PI * 0.497;
    this.controls.minDistance = 2;
    this.controls.maxDistance = 220;
    this.controls.addEventListener('change', () => { this.fixed = null; this.needs = true; });

    this.sky = new Sky();
    this.sky.scale.setScalar(900);
    this.scene.add(this.sky);
    this.sun = new THREE.DirectionalLight(0xffffff, 3);
    const s = LOOK.shadow;
    this.sun.castShadow = true;
    this.sun.shadow.mapSize.set(s.size, s.size);
    Object.assign(this.sun.shadow.camera, { left: -s.half, right: s.half, top: s.half, bottom: -s.half, near: s.near, far: s.far });
    this.sun.shadow.bias = s.bias;
    this.sun.shadow.normalBias = s.normalBias;
    this.sun.shadow.radius = s.radius;
    this.scene.add(this.sun, this.sun.target);
    this.pmrem = new THREE.PMREMGenerator(r);
    this.time = 'day';
    this.sunDir = { az: 200, el: 42 };      // azimuth clockwise from +y (into the lot) seen from above, elevation, degrees
    this.centre = new THREE.Vector3(0, 0, 0);
    this.needs = true;
    this.fixed = null;                      // a photo-matched camera pins the aspect
    window.addEventListener('resize', () => this.resize());
    this.resize();
  }

  setCentre(p) {
    this.centre.copy(p);
    this.controls.target.copy(p);
    this.applyLight();
  }

  setSun(az, el) { this.sunDir = { az, el }; this.applyLight(); }

  setTime(t) { this.time = t; this.applyLight(); }

  applyLight() {
    const L = LOOK[this.time];
    const el = THREE.MathUtils.degToRad(this.time === 'dusk' ? -3.5 : this.sunDir.el);
    const az = THREE.MathUtils.degToRad(this.time === 'dusk' ? this.sunDir.az + 95 : this.sunDir.az);
    // unit vector toward the sun in model axes, then three axes
    const d = toGL([Math.sin(az) * Math.cos(el), Math.cos(az) * Math.cos(el), Math.sin(el)]);
    const u = this.sky.material.uniforms;
    u.sunPosition.value.copy(d);
    u.turbidity.value = L.turbidity;
    u.rayleigh.value = L.rayleigh;
    u.mieCoefficient.value = 0.004;
    u.mieDirectionalG.value = 0.82;
    const lit = this.time === 'dusk' ? toGL([Math.sin(az) * 0.94, Math.cos(az) * 0.94, 0.34]) : d;
    this.sun.position.copy(this.centre).addScaledVector(lit, 120);
    this.sun.target.position.copy(this.centre);
    this.sun.color.set(L.sunColor);
    this.sun.intensity = L.sun;
    this.renderer.toneMappingExposure = L.exposure;
    if (this.envRT) this.envRT.dispose();
    const env = new THREE.Scene();
    const sky2 = new Sky();
    sky2.scale.setScalar(900);
    sky2.material.uniforms.sunPosition.value.copy(d);
    for (const k of ['turbidity', 'rayleigh', 'mieCoefficient', 'mieDirectionalG']) sky2.material.uniforms[k].value = u[k].value;
    env.add(sky2);
    this.envRT = this.pmrem.fromScene(env, 0.02);
    this.scene.environment = this.envRT.texture;
    this.scene.environmentIntensity = L.env;
    this.needs = true;
  }

  // photo-matched camera: {w, h, f, R (world->camera rows: right, down, forward), C}
  setPhotoCamera(cam) {
    const R = cam.R, right = toGL(R[0]), down = toGL(R[1]), fwd = toGL(R[2]);
    const m = new THREE.Matrix4().makeBasis(right, down.clone().negate(), fwd.clone().negate());
    this.camera.quaternion.setFromRotationMatrix(m);
    this.camera.position.copy(toGL(cam.C));
    this.camera.fov = THREE.MathUtils.radToDeg(2 * Math.atan(cam.h / 2 / cam.f));
    this.fixed = { aspect: cam.w / cam.h };
    this.controls.target.copy(this.camera.position).addScaledVector(fwd, 15);
    this.resize();
  }

  setOrbit(pos, target, fov = 40) {
    this.fixed = null;
    this.camera.position.copy(toGL(pos));
    this.controls.target.copy(toGL(target));
    this.camera.fov = fov;
    this.camera.lookAt(this.controls.target);
    this.resize();
  }

  resize() {
    const w = this.canvas.clientWidth || window.innerWidth, h = this.canvas.clientHeight || window.innerHeight;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.needs = true;
  }

  frame() {
    if (!this.fixed) this.controls.update();
    if (this.needs) {
      this.needs = false;
      this.renderer.render(this.scene, this.camera);
      this.frames = (this.frames || 0) + 1;
    }
  }
}
