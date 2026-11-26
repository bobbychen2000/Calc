// Sky: an analytic dome drawn in DISPLAY colours (not tone mapped: the photographed sky, as it looks), and a
// separate lighting version of the same sky rendered into the image-based light (scene-referred radiance).
import * as THREE from 'three';

// colours are sRGB hex as measured on the listing photos (day: p26 / p02; dusk: p01)
export const SKIES = {
  day: {
    zenith: 0x3a6cae, mid: 0x7fa9d6, horizon: 0xc9dcec, ground: 0x7d8a72,
    sun: 0xfff6e4, glow: 0.55, clouds: 0.42, cloudLit: 0xffffff, cloudShade: 0xb9c3cf,
    light: 1.0,                 // radiance scale of the lighting copy
    bounce: 0xc4beb0,           // what the lower hemisphere sends back up in the lighting copy: sunlit paving, lawn, walls
    lightDesat: 0.45,           // the lighting copy is less blue than the sky looks: shade on white walls is near neutral in the photos
  },
  dusk: {
    zenith: 0x8d9cc4, mid: 0xb7b4d2, horizon: 0xe6c3c8, ground: 0x4a4d50,
    sun: 0xffc9a0, glow: 0.9, clouds: 0.25, cloudLit: 0xf2c8c8, cloudShade: 0x9a9fba,
    light: 1.0,
    bounce: 0x6a6660,
    lightDesat: 0.2,
  },
};

const VERT = /* glsl */`
varying vec3 vDir;
void main() {
  vDir = normalize(position);
  vec4 p = modelViewMatrix * vec4(position, 0.0);      // rotate only: the dome is at infinity
  gl_Position = (projectionMatrix * vec4(p.xyz, 1.0)).xyww;
}`;

const FRAG = /* glsl */`
precision highp float;
varying vec3 vDir;
uniform vec3 uZenith, uMid, uHorizon, uGround, uSun, uCloudLit, uCloudShade, uSunDir;
uniform float uGlow, uClouds, uScale, uTime, uDesat, uAlpha;
float hash(vec2 p) { p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
float noise(vec2 p) {
  vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1, 0)), f.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), f.x), f.y);
}
float fbm(vec2 p) { float a = 0.5, s = 0.0; for (int i = 0; i < 5; i++) { s += a * noise(p); p = p * 2.03 + 11.7; a *= 0.5; } return s; }
void main() {
  vec3 d = normalize(vDir);
  float e = d.y;                                             // sine of the elevation
  vec3 col = mix(uHorizon, uMid, smoothstep(0.0, 0.22, e));
  col = mix(col, uZenith, smoothstep(0.15, 0.85, e));
  float mu = max(dot(d, normalize(uSunDir)), 0.0);
  col += uSun * uGlow * (0.28 * pow(mu, 8.0) + 0.5 * pow(mu, 64.0));
  col = mix(col, uSun * 1.6, smoothstep(0.99975, 0.99992, mu));  // the disc
  if (uClouds > 0.0 && e > 0.02) {                           // flat cloud layer, perspective-projected
    vec2 q = d.xz / (e + 0.12) * 0.9 + vec2(uTime * 0.004, 0.0);
    float n = fbm(q * 1.3) * 0.75 + fbm(q * 4.1) * 0.25;
    float c = smoothstep(1.0 - uClouds * 0.92, 1.0 - uClouds * 0.92 + 0.22, n) * smoothstep(0.02, 0.18, e);
    float lit = clamp(0.55 + 0.6 * (fbm(q * 1.3 + normalize(uSunDir).xz * 0.25) - n) * 3.0 + 0.3 * mu, 0.0, 1.0);
    col = mix(col, mix(uCloudShade, uCloudLit, lit), c * 0.92);
  }
  col = mix(uGround, col, smoothstep(-0.04, 0.0, e));
  col = mix(col, vec3(dot(col, vec3(0.2126, 0.7152, 0.0722))), uDesat);
  gl_FragColor = vec4(col * uScale, uAlpha);
  #include <colorspace_fragment>
}`;

function uniforms(k, sunDir, scale) {
  const c = (h) => ({ value: new THREE.Color(h) });           // sRGB hex -> linear working space
  return {
    uZenith: c(k.zenith), uMid: c(k.mid), uHorizon: c(k.horizon), uGround: c(k.ground), uSun: c(k.sun),
    uCloudLit: c(k.cloudLit), uCloudShade: c(k.cloudShade), uSunDir: { value: sunDir.clone() },
    uGlow: { value: k.glow }, uClouds: { value: k.clouds }, uScale: { value: scale }, uTime: { value: 0 },
    uDesat: { value: k.desat || 0 }, uAlpha: { value: 1 },
  };
}

export class SkyDome {
  constructor() {
    this.geo = new THREE.SphereGeometry(1, 48, 24);
    this.mat = new THREE.ShaderMaterial({ vertexShader: VERT, fragmentShader: FRAG, side: THREE.BackSide, depthWrite: false,
      depthTest: true, toneMapped: false, uniforms: uniforms(SKIES.day, new THREE.Vector3(0, 1, 0), 1) });
    this.mesh = new THREE.Mesh(this.geo, this.mat);
    this.mesh.frustumCulled = false;
    this.mesh.renderOrder = -1000;
  }

  set(time, sunDir) {
    const u = uniforms(SKIES[time], sunDir, 1);
    for (const k of Object.keys(u)) this.mat.uniforms[k].value = u[k].value;
  }

  // the same sky as scene-referred radiance for the image-based light
  // gain: three r160 has no scene-wide environment intensity, so the level of the ambient light is baked into the map
  environment(pmrem, time, sunDir, gain = 1) {
    const k = SKIES[time];
    const mat = new THREE.ShaderMaterial({ vertexShader: VERT, fragmentShader: FRAG.replace('#include <colorspace_fragment>', ''),
      side: THREE.BackSide, depthWrite: false, toneMapped: false, uniforms: uniforms({ ...k, glow: k.glow * 0.4, ground: k.bounce, desat: k.lightDesat }, sunDir, k.light * gain) });
    const scene = new THREE.Scene();
    scene.add(new THREE.Mesh(this.geo, mat));
    const rt = pmrem.fromScene(scene, 0.03);
    mat.dispose();
    return rt;
  }
}

// The lighting sky's radiance toward d (three axes, unit, d.y = sine of the elevation), without sun and clouds:
// the JS twin of the shader above, for the sky-light samples of picture.js.
export function skyRadiance(time, d, gain = 1) {
  const k = SKIES[time], e = d.y;
  const ss = (a, b, x) => { const t = Math.min(Math.max((x - a) / (b - a), 0), 1); return t * t * (3 - 2 * t); };
  const col = new THREE.Color(k.horizon).lerp(new THREE.Color(k.mid), ss(0.0, 0.22, e)).lerp(new THREE.Color(k.zenith), ss(0.15, 0.85, e));
  const lum = 0.2126 * col.r + 0.7152 * col.g + 0.0722 * col.b;
  return col.lerp(new THREE.Color(lum, lum, lum), k.lightDesat || 0).multiplyScalar(k.light * gain);
}
