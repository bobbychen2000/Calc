// Stage: renderer, sky, sun + shadows, image-based light, cameras.
// World (model) axes: x right along the street, y into the lot, z up.  three axes: X = x, Y = z, Z = -y.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { SkyDome, skyRadiance } from './sky.js';
import { Picture } from './picture.js';

export const toGL = (p) => new THREE.Vector3(p[0], p[2], -p[1]);

// Tone mapping: the Khronos "PBR Neutral" curve (base colours pass 1:1 up to 0.76, a soft shoulder above), so a
// material's albedo is what the photo shows under the same light and white walls can sit near 245 without ACES'
// hue shifts.  three r160 has no built-in for it: it goes in as the custom tone-mapping function.
THREE.ShaderChunk.tonemapping_pars_fragment = THREE.ShaderChunk.tonemapping_pars_fragment.replace(
  'vec3 CustomToneMapping( vec3 color ) { return color; }',
  `vec3 CustomToneMapping( vec3 color ) {
    const float startCompression = 0.8 - 0.04;
    const float desaturation = 0.15;
    color *= toneMappingExposure;
    float x = min( color.r, min( color.g, color.b ) );
    float offset = x < 0.08 ? x - 6.25 * x * x : 0.04;
    color -= offset;
    float peak = max( color.r, max( color.g, color.b ) );
    if ( peak < startCompression ) return color;
    float d = 1.0 - startCompression;
    float newPeak = 1.0 - d * d / ( peak + d - startCompression );
    color *= newPeak / peak;
    float g = 1.0 - 1.0 / ( desaturation * ( peak - newPeak ) + 1.0 );
    return mix( color, vec3( newPeak ), g );
  }`);

// picture.js replaces part of the sky's image-based DIFFUSE light by shadowed sky samples while it refines a still:
// uSkyOff (zero unless a material is hooked and a refinement pass is running) is that part, for a sky-facing surface.
THREE.ShaderChunk.envmap_physical_pars_fragment = 'uniform vec3 uSkyOff;\n' + THREE.ShaderChunk.envmap_physical_pars_fragment;
THREE.ShaderChunk.lights_fragment_maps = THREE.ShaderChunk.lights_fragment_maps.replace(
  'iblIrradiance += getIBLIrradiance( geometryNormal );',
  'iblIrradiance += max( getIBLIrradiance( geometryNormal ) - uSkyOff * ( 0.5 + 0.5 * inverseTransformDirection( geometryNormal, viewMatrix ).y ), vec3( 0.0 ) );');

// Light balance, calibrated on the listing photos (their real-estate grade lifts the shade): a sunlit white wall
// renders ~245, the same wall in open shade ~180.
export const LOOK = {
  day: { exposure: 1.0, sun: 3.0, sunColor: 0xfff3e0, env: 1.3 },
  dusk: { exposure: 1.0, sun: 0.45, sunColor: 0xffc4a4, env: 1.45 },
  shadow: { size: 4096, half: 34, near: 1, far: 220, bias: -0.00025, normalBias: 0.035, radius: 2.5 },
};

export class Stage {
  constructor(canvas) {
    this.canvas = canvas;
    const r = this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
    r.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    r.outputColorSpace = THREE.SRGBColorSpace;
    r.toneMapping = THREE.CustomToneMapping;
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
    this.controls.addEventListener('start', () => { this.design = null; });   // the user moves: resizes keep their camera

    this.sky = new SkyDome();
    this.scene.add(this.sky.mesh);
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
    this.picture = new Picture(this);
    this.refine = false;                    // progressive refinement of stills (main.js turns it on)
    this.skyMean = new THREE.Color(0, 0, 0);
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
    const el = THREE.MathUtils.degToRad(this.time === 'dusk' ? 1.5 : this.sunDir.el);
    const az = THREE.MathUtils.degToRad(this.time === 'dusk' ? this.sunDir.az + 95 : this.sunDir.az);
    // unit vector toward the sun in model axes, then three axes
    const d = toGL([Math.sin(az) * Math.cos(el), Math.cos(az) * Math.cos(el), Math.sin(el)]);
    this.sky.set(this.time, d);
    // at dusk the "sun" light is the bright part of the sky, well above the horizon
    const lit = this.time === 'dusk' ? toGL([Math.sin(az) * 0.94, Math.cos(az) * 0.94, 0.34]).normalize() : d;
    this.sun.position.copy(this.centre).addScaledVector(lit, 120);
    this.sun.target.position.copy(this.centre);
    this.sun.color.set(L.sunColor);
    this.sun.intensity = L.sun;
    this.renderer.toneMappingExposure = L.exposure;
    if (this.envRT) this.envRT.dispose();
    this.envRT = this.sky.environment(this.pmrem, this.time, d, L.env);
    this.scene.environment = this.envRT.texture;
    this.skyMean.setRGB(0, 0, 0);          // mean radiance of the lighting sky's upper hemisphere (picture.js)
    for (let i = 0; i < 64; i++) {
      const y = (i + 0.5) / 64, a = i * 2.399963, c = Math.sqrt(1 - y * y);
      this.skyMean.add(skyRadiance(this.time, new THREE.Vector3(c * Math.cos(a), y, c * Math.sin(a)), L.env));
    }
    this.skyMean.multiplyScalar(1 / 64);
    this.picture.reset();
    this.envGain = L.env;                // the image-based light is this much brighter than the sky looks: mirror-like
                                         // materials (glass, water) divide their envMapIntensity by it (stage.envGain)
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
    this.design = null;
    this.controls.target.copy(this.camera.position).addScaledVector(fwd, 15);
    this.resize();
  }

  // A named view is composed for a landscape screen (opts.aspect, 16:9).  On a narrower screen it keeps most of its
  // width: 'dolly' views (from outside the lot or above it) step back along their line of sight, 'fov' views (eye level
  // inside the lot, where stepping back would put a fence in front of the lens) widen the lens up to 74 deg instead.
  setOrbit(pos, target, fov = 40, opts = {}) {
    this.fixed = null;
    this.design = { pos: toGL(pos), target: toGL(target), fov, fit: opts.fit || 'fov', aspect: opts.aspect || 16 / 9 };
    this.resize();
  }

  frameDesign(a) {
    const d = this.design, rad = THREE.MathUtils.degToRad;
    let fov = d.fov;
    const pos = d.pos.clone();
    if (a < d.aspect) {
      const cover = a < 1 ? 0.8 : 1;                              // portrait: 80 % of the composed width
      let tv = Math.tan(rad(d.fov / 2)) * d.aspect * cover / a;   // tan(half vertical fov) that shows it
      const tvMax = Math.tan(rad(d.fit === 'dolly' ? d.fov / 2 + 6 : 37));
      if (d.fit === 'dolly' && tv > tvMax) pos.sub(d.target).multiplyScalar(tv / tvMax).add(d.target);
      tv = Math.min(tv, tvMax);
      fov = THREE.MathUtils.radToDeg(2 * Math.atan(tv));
    }
    this.camera.position.copy(pos);
    this.controls.target.copy(d.target);
    this.camera.fov = fov;
    this.camera.lookAt(d.target);
  }

  resize() {
    const w = this.canvas.clientWidth || window.innerWidth, h = this.canvas.clientHeight || window.innerHeight;
    this.renderer.setSize(w, h, false);
    if (this.design && !this.fixed) this.frameDesign(w / h);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.needs = true;
  }

  skyRadiance(d) { return skyRadiance(this.time, d, LOOK[this.time].env); }

  // one animation frame: a plain render when something changed, else refinement passes until the still converges
  // Exposure follows the view as a photographer's would: looking at the faces the sun lights, the calibrated value;
  // looking at the shaded side (toward the sun's side of the sky), opened up - the daylight photographs of the street
  // front show its shaded white walls near 235, not 180.
  meter() {
    const L = LOOK[this.time];
    let k = 1;
    if (this.time === 'day' && this.sunDir && this.autoExposure !== false) {
      const f = this.camera.getWorldDirection(new THREE.Vector3());
      const az = THREE.MathUtils.degToRad(this.sunDir.az);
      const sun = toGL([Math.sin(az), Math.cos(az), 0]);
      const flat = Math.hypot(f.x, f.z);
      const toward = flat > 1e-6 ? (f.x * sun.x + f.z * sun.z) / flat : 0;
      k = 1 + 0.5 * THREE.MathUtils.smoothstep(toward, -0.15, 0.75) * THREE.MathUtils.smoothstep(flat, 0.35, 0.8);
    }
    this.renderer.toneMappingExposure = L.exposure * k;
  }

  frame() {
    if (!this.fixed) this.controls.update();
    if (this.needs) {
      this.needs = false;
      this.meter();
      this.picture.reset();
      if (this.refine) { this.picture.pass(); } else { this.renderer.render(this.scene, this.camera); }
      this.frames = (this.frames || 0) + 1;
    } else if (this.refine && !this.picture.done) {
      this.picture.pass();
    }
  }
}
