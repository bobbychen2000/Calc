// Apron floodlighting for the three.js renderer: the high masts are a LIGHT that illuminates everything under them
// (ground, markings, signs, buildings, bridges, vehicles, aircraft), not an emission of the concrete.
// Review round 1 (critical): the old model added the floodlight pools to the ground's emission (albedo x E), so at night
// the concrete glowed white while the paint, aircraft and buildings on it stayed black. Here:
//   1. floodField(): on the CPU, once, the irradiance field of all mast luminaires over the aprons at a receiver height
//      of 2 m (the ICAO vertical-illuminance height), stored as RGBA16F over the masts' bounding box:
//        rgb = vector irradiance  E_v = sum_i I_i(dir) / r_i^2 * l_i   (l_i: unit vector from the receiver to lamp i)
//        a   = horizontal spread  S_h = sum_i I_i / r_i^2 * (d_i / r_i) (horizontal part, summed as scalars)
//      For a surface with normal N the irradiance is  max(0, N . E_v)  (exact for one lamp; exact for any number of
//      lamps on a horizontal surface, since all lamps are above it) plus, for tilted surfaces lit from several sides,
//      (1 - |N.y|) / pi * max(0, S_h - |E_v.xz|)  (the part of the horizontal flux that cancels in the vector sum).
//   2. FloodLight / FloodLightNode: a three.js light whose node samples that field per pixel and feeds the lighting
//      model like any analytic light (diffuse + specular, dotNL from the material normal; direction = E_v) plus the
//      spread part as irradiance (so GTAO occludes it). Registered in js/three/engine.js (renderer.library.addLight).
// Sources and labels:
//   - mast positions: data/sfo_details.json masts (OpenStreetMap man_made=mast + tower:type=lighting, observed; drawn by
//     js/live/items.js buildMasts); lamp height js/live/items.js MAST_H (27 m, inferred there); luminaires aimed "roughly
//     toward the terminal core" as items.js builds them (yaw = atan2(-x - 900, -z - 300)), inferred.
//   - intensity distribution (inferred, typical of aimed high-mast floods): I ~ 1 / cos^3 of the angle from nadir (which
//     makes the horizontal illuminance of one mast uniform) out to 100 m, fading to 0 at 170 m; full intensity ahead of
//     the head frame, half behind. Resulting horizontal uniformity over stand-like texels ~3.3:1 (ICAO asks <= 4:1);
//     vertical illuminance facing a mast is ~1.5-2x the horizontal (aircraft sides are brightly lit, as in night
//     photographs of aprons).
//   - level: ICAO Annex 14 Vol I 5.3.24 (apron floodlighting): aircraft stands >= 20 lux average horizontal illuminance,
//     uniformity (average:minimum) <= 4:1, 20 lux vertical at 2 m. A DESIGN value, not a measurement at SFO. The lamp
//     intensity is solved so the mean horizontal irradiance over stand-like texels (25-110 m from the nearest mast)
//     equals E_STAND (scene units, 0.62 = 20 lux; renderer3 derives the night exposure from it).
//   - no floodlight shadows (Inferred consequence: surfaces under wings and bridges are lit; GTAO darkens the spread part).
import { THREE, TSL } from './lib.js';
import { MAST_H } from '../live/items.js';
const { Fn, texture, uniform, vec2, vec3, vec4, float, max, abs, length, normalize, dot, positionWorld, normalWorld, cameraViewMatrix, step } = TSL;

export const E_STAND = 0.62;      // scene irradiance units for the ICAO 20 lux stand average (see renderer3 nightExposure)
export const FLOOD_COLOR = [1.0, 0.93, 0.84]; // ~4000 K LED (colour of the SFO luminaires not verified: inferred)

// masts: [[x, z], ...] (world metres, ground at GROUND_Y). Returns { data (Float32 RGBA), w, h, rect: [x0, z0, sx, sz], stats }
export function floodField(masts, { lampH = MAST_H - 0.3, recvH = 2.0, res = 3, R = 170 } = {}) {
  if (!masts || !masts.length) return null;
  let x0 = Infinity, x1 = -Infinity, z0 = Infinity, z1 = -Infinity;
  for (const [x, z] of masts) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); z0 = Math.min(z0, z); z1 = Math.max(z1, z); }
  const M = R + 2 * res; x0 -= M; z0 -= M; x1 += M; z1 += M;
  const w = Math.ceil((x1 - x0) / res) + 1, h = Math.ceil((z1 - z0) / res) + 1;
  const F = new Float32Array(w * h * 4); const near = new Float32Array(w * h).fill(1e9);
  const dy = lampH - recvH; const dc = 100, rc3 = Math.pow(Math.hypot(dc, dy) / dy, 3);
  for (const [mx, mz] of masts) {
    const yaw = Math.atan2(-mx - 900, -mz - 300); const ax = Math.sin(yaw), az = Math.cos(yaw); // items.js head frame
    const i0 = Math.max(0, Math.floor((mx - R - x0) / res)), i1 = Math.min(w - 1, Math.ceil((mx + R - x0) / res));
    const j0 = Math.max(0, Math.floor((mz - R - z0) / res)), j1 = Math.min(h - 1, Math.ceil((mz + R - z0) / res));
    for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) {
      const px = x0 + i * res, pz = z0 + j * res; const ex = px - mx, ez = pz - mz; const d = Math.hypot(ex, ez);
      const k = j * w + i; if (d < near[k]) near[k] = d;
      if (d > R) continue;
      const rr = d * d + dy * dy, r = Math.sqrt(rr);
      // aimed floods: intensity ~ 1/cos^3 of the angle from nadir (uniform horizontal illuminance, the purpose of
      // aiming), up to 100 m out, then cut off by R; asymmetric: full ahead of the head frame, half behind
      const fwd = d > 1e-3 ? Math.max(0, (ex * ax + ez * az) / d) : 0;
      const I = Math.min(Math.pow(r / dy, 3), rc3) * (1 - smooth((d - dc) / (R - dc))) * (0.5 + 0.5 * fwd);
      const E = I / rr;
      F[k * 4] += E * (-ex / r); F[k * 4 + 1] += E * (dy / r); F[k * 4 + 2] += E * (-ez / r); F[k * 4 + 3] += E * (d / r);
    }
  }
  // calibrate: mean horizontal irradiance (= E_v.y, all lamps are above the receiver) over stand-like texels
  let s = 0, n = 0, mn = Infinity; const vals = [];
  for (let k = 0; k < w * h; k++) if (near[k] >= 25 && near[k] <= 110) { const e = F[k * 4 + 1]; s += e; n++; vals.push(e); }
  const scale = n ? E_STAND / (s / n) : 1;
  for (let k = 0; k < F.length; k++) F[k] *= scale;
  vals.sort((a, b) => a - b); mn = vals.length ? vals[Math.floor(vals.length * 0.05)] * scale : 0;
  return { data: F, w, h, rect: [x0, z0, (w - 1) * res, (h - 1) * res], stats: { masts: masts.length, texels: n, meanH: E_STAND, p5H: mn, uniformity: mn > 0 ? E_STAND / mn : Infinity, res } };
}
function smooth(t) { t = Math.min(1, Math.max(0, t)); return t * t * (3 - 2 * t); }

// field -> half-float RGBA texture (linear filtering works everywhere for half float; float32 needs an extension on iOS)
export function floodTexture(field) {
  const half = new Uint16Array(field.data.length); for (let i = 0; i < half.length; i++) half[i] = THREE.DataUtils.toHalfFloat(field.data[i]);
  const t = new THREE.DataTexture(half, field.w, field.h, THREE.RGBAFormat, THREE.HalfFloatType);
  t.minFilter = t.magFilter = THREE.LinearFilter; t.generateMipmaps = false; t.wrapS = t.wrapT = THREE.ClampToEdgeWrapping; t.flipY = false; t.needsUpdate = true;
  return t;
}

// the light: intensity = lamps on (0..1, from the app's night factor), colour = lamp colour
export class FloodLight extends THREE.Light {
  constructor() {
    super(new THREE.Color(...FLOOD_COLOR), 0);
    this.isFloodLight = true; this.type = 'FloodLight';
    this.fieldTex = new THREE.DataTexture(new Uint16Array(4), 1, 1, THREE.RGBAFormat, THREE.HalfFloatType); this.fieldTex.needsUpdate = true;
    this.rect = new THREE.Vector4(0, 0, 1, 1); // x0, z0, width, depth (world metres)
  }
  setField(field) { // before the first compile (renderer3.attachWorld); the node samples this.fieldTex
    if (!field) return; this.fieldTex = floodTexture(field); this.rect.set(field.rect[0], field.rect[1], field.rect[2], field.rect[3]); this.stats = field.stats;
  }
}
export class FloodLightNode extends THREE.AnalyticLightNode {
  static get type() { return 'FloodLightNode'; }
  constructor(light = null) { super(light); this.rectU = uniform(new THREE.Vector4(0, 0, 1, 1)); }
  update(frame) { super.update(frame); if (this.light) this.rectU.value.copy(this.light.rect); }
  field() {
    const L = this.light; const r = this.rectU; const wp = positionWorld;
    const uv = vec2(wp.x.sub(r.x).div(r.z), wp.z.sub(r.y).div(r.w));
    const inside = step(0.0, uv.x).mul(step(uv.x, 1.0)).mul(step(0.0, uv.y)).mul(step(uv.y, 1.0));
    return texture(L.fieldTex, uv).mul(inside);
  }
  setupDirect() {
    const f = this.field(); const Ev = f.xyz.add(vec3(0.0, 1e-6, 0.0));
    const lightDirection = normalize(cameraViewMatrix.mul(vec4(Ev, 0.0)).xyz);
    return { lightDirection, lightColor: this.colorNode.mul(length(Ev)) };
  }
  setup(builder) {
    super.setup(builder); // direct part (setupDirect), no shadows (castShadow false)
    const f = this.field(); const N = normalWorld;
    const spread = max(f.w.sub(length(f.xz)), 0.0).mul(float(1.0).sub(abs(N.y))).mul(1.0 / Math.PI);
    builder.context.irradiance.addAssign(this.colorNode.mul(spread));
  }
}
