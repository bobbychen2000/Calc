// Apron floodlighting for the three.js renderer: the high masts are a LIGHT that illuminates everything under them
// (ground, markings, signs, buildings, bridges, vehicles, aircraft), not an emission of the concrete.
// Review round 1 (critical): the old model added the floodlight pools to the ground's emission (albedo x E), so at night
// the concrete glowed white while the paint, aircraft and buildings on it stayed black.
// Review round 2 (26 Sep 2026): roofs rendered snow-white (every receiver got the 2 m field whatever its height), nothing
// cast a floodlight shadow, and faces turned away from the masts were pure black (no bounce). Now:
//   1. floodField(): on the CPU, once, the irradiance field of all mast luminaires over the aprons, for receivers at
//      FIELD_LAYERS heights above the ground (2, 9, 16, 23 m), stored as a half-float 3-D texture (x, z, height):
//        rgb = vector irradiance  E_v = sum_i I_i(dir) / r_i^2 * l_i   (l_i: unit vector from the receiver to lamp i)
//        a   = horizontal spread  S_h = sum_i I_i / r_i^2 * (d_i / r_i) (horizontal part, summed as scalars)
//      The luminaire intensity is a function of the DIRECTION (angle from nadir, azimuth to the aim), the same for every
//      receiver: a roof 10 m under the lamps and beyond the beam's upper cut-off gets nothing, one inside it gets what
//      the geometry gives (mastE below; the 2 m layer is the old field exactly). The height interpolates between layers;
//      above the lamps the field is 0 (the floods do not light upwards).
//      For a surface with normal N the irradiance is  max(0, N . E_v)  (exact for one lamp; exact for any number of
//      lamps on a horizontal surface, since all lamps are above it) plus, for tilted surfaces lit from several sides,
//      (1 - |N.y|) / pi * max(0, S_h - |E_v.xz|)  (the part of the horizontal flux that cancels in the vector sum).
//   2. FloodLight / FloodLightNode: a three.js light whose node samples that field per pixel and feeds the lighting
//      model like any analytic light (diffuse + specular, dotNL from the material normal; direction = E_v), multiplied
//      by the screen-space AO (GTAO: the concrete under a fuselage, a wing or a bridge sees fewer of the masts), plus
//      the spread part and the GROUND BOUNCE as irradiance (so GTAO occludes them too):
//        E_bounce = rho_ground x E_h(ground) x (1 - N.y) / 2   (the lit concrete, a Lambertian floor, seen by the lower
//      hemisphere of the surface; rho_ground = the airfield bake's mean albedo, renderer3 _groundAlbedo).
//   3. MastSpot / MastSpotNode: the masts nearest to what the camera looks at (renderer3 picks them per frame) are
//      drawn as real shadow-casting spot lights with the same intensity distribution (mastE), and their share is
//      subtracted from the field in FloodLightNode, so the total stays the calibrated field while aircraft, bridges and
//      vehicles under those masts cast crisp floodlight shadows. The spot points straight down with a 80 deg half angle:
//      a downward perspective shadow map has a uniform texel size on the ground (0.14 m at 2048^2 over +-142 m). The
//      masts' own geometry is kept out of these shadow maps (layer MAST_LAYER, js/three/engine.js).
// Sources and labels:
//   - mast positions: data/sfo_details.json masts (OpenStreetMap man_made=mast + tower:type=lighting, observed; drawn by
//     js/live/items.js buildMasts); lamp height js/live/items.js MAST_H (27 m, inferred there); luminaires aimed "roughly
//     toward the terminal core" as items.js builds them (yaw = atan2(-x - 900, -z - 300)), inferred.
//   - intensity distribution (inferred, typical of aimed high-mast floods): I ~ 1 / cos^3 of the angle from nadir (which
//     makes the horizontal illuminance of one mast uniform on the apron) out to 76 deg from nadir (100 m on the 2 m
//     plane), then a cut-off to 0 at 80 deg (140 m): glare-controlled apron floods have a sharp upper beam edge; round 2
//     narrowed it from 81.7 deg (170 m) so roofs beside the aprons stay out of the beam. Full intensity ahead of the head
//     frame, half behind. Horizontal uniformity over stand-like texels ~3:1 (ICAO asks <= 4:1).
//   - level: ICAO Annex 14 Vol I 5.3.24 (apron floodlighting): aircraft stands >= 20 lux average horizontal illuminance,
//     uniformity (average:minimum) <= 4:1, 20 lux vertical at 2 m. A DESIGN value, not a measurement at SFO. The lamp
//     intensity is solved so the mean horizontal irradiance over stand-like texels (25-100 m from the nearest mast, 2 m
//     layer) equals E_STAND (scene units, 0.62 = 20 lux; renderer3 derives the night exposure from it).
//   - buildings do not occlude the field (Inferred consequence: ground on the far side of a building within ~140 m of a
//     mast is lit through it; the roofs themselves are handled by the height layers). Shadows only from the spot masts.
import { THREE, TSL } from './lib.js';
import { MAST_H } from '../live/items.js';
import { GROUND_Y } from '../geo.js';
const { Fn, texture, texture3D, uniform, vec2, vec3, vec4, float, max, min, abs, length, normalize, dot, sqrt, positionWorld, normalWorld, cameraViewMatrix, step, smoothstep, clamp, select } = TSL;

export const E_STAND = 0.62;      // scene irradiance units for the ICAO 20 lux stand average (see renderer3 nightExposure)
export const FLOOD_COLOR = [1.0, 0.93, 0.84]; // ~4000 K LED (colour of the SFO luminaires not verified: inferred)
export const LAMP_H = MAST_H - 0.3;           // luminaire height above the ground (m)
export const FIELD_LAYERS = [2, 9, 16, 23];   // receiver heights above the ground of the field layers (m)
export const MAST_LAYER = 2;                  // three.js layer of the mast geometry (not in the spot shadow maps)
const RECV_H = 2.0, DY2 = LAMP_H - RECV_H;    // the design plane (2 m) and the lamp height above it
const DC = 100, RC = 140;                     // beam: 1/cos^3 out to DC on the design plane, cut to 0 at RC
const RC3 = Math.pow(Math.hypot(DC, DY2) / DY2, 3);
const smooth = (t) => { t = Math.min(1, Math.max(0, t)); return t * t * (3 - 2 * t); };
export const mastAim = (x, z) => { const yaw = Math.atan2(-x - 900, -z - 300); return [Math.sin(yaw), Math.cos(yaw)]; }; // items.js head frame

// one mast at a receiver (CPU): [Ex, Ey, Ez, S] (vector irradiance and horizontal magnitude, before the level scale)
export function mastE(px, py, pz, mx, mz, ax, az) {
  const ex = px - mx, ez = pz - mz, d = Math.hypot(ex, ez), dyr = GROUND_Y + LAMP_H - py;
  if (dyr <= 0.05) return [0, 0, 0, 0];
  const rr = d * d + dyr * dyr, r = Math.sqrt(rr), deq = d / dyr * DY2;
  if (deq >= RC) return [0, 0, 0, 0];
  const fwd = d > 1e-3 ? Math.max(0, (ex * ax + ez * az) / d) : 0;
  const I = Math.min(Math.pow(r / dyr, 3), RC3) * (1 - smooth((deq - DC) / (RC - DC))) * (0.5 + 0.5 * fwd);
  const E = I / rr;
  return [E * (-ex / r), E * (dyr / r), E * (-ez / r), E * (d / r)];
}
// the same in TSL: P world position, m = vec4(mast x, mast z, aim x, aim z); returns vec4(E_v, S) x scale
export const mastEnode = (P, m, scale) => {
  const ex = P.x.sub(m.x), ez = P.z.sub(m.y);
  const d = sqrt(ex.mul(ex).add(ez.mul(ez))).max(1e-3);
  const dyr = float(GROUND_Y + LAMP_H).sub(P.y); const dyc = max(dyr, 0.05);
  const rr = d.mul(d).add(dyc.mul(dyc)); const r = sqrt(rr);
  const deq = d.div(dyc).mul(DY2);
  const ic = r.div(dyc); const I3 = min(ic.mul(ic).mul(ic), RC3);
  const fwd = max(ex.mul(m.z).add(ez.mul(m.w)).div(d), 0.0);
  const E = I3.mul(float(1.0).sub(smoothstep(DC, RC, deq))).mul(fwd.mul(0.5).add(0.5)).div(rr).mul(step(0.05, dyr)).mul(scale);
  return vec4(vec3(ex.negate(), dyc, ez.negate()).mul(E.div(r)), E.mul(d).div(r));
};

// masts: [[x, z], ...] (world metres, ground at GROUND_Y). Returns { data (Float32 RGBA, x fastest, then z, then layer),
// w, h, d (layers), rect: [x0, z0, sx, sz], layers, scale (level factor applied), stats }
export function floodField(masts, { res = 3 } = {}) {
  if (!masts || !masts.length) return null;
  let x0 = Infinity, x1 = -Infinity, z0 = Infinity, z1 = -Infinity;
  for (const [x, z] of masts) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); z0 = Math.min(z0, z); z1 = Math.max(z1, z); }
  const R = RC; // horizontal reach (d < RC x dyr / DY2: the 2 m layer reaches farthest)
  const M = R + 2 * res; x0 -= M; z0 -= M; x1 += M; z1 += M;
  const w = Math.ceil((x1 - x0) / res) + 1, h = Math.ceil((z1 - z0) / res) + 1, NL = FIELD_LAYERS.length;
  const F = new Float32Array(w * h * NL * 4); const near = new Float32Array(w * h).fill(1e9);
  for (const [mx, mz] of masts) {
    const [ax, az] = mastAim(mx, mz);
    const i0 = Math.max(0, Math.floor((mx - R - x0) / res)), i1 = Math.min(w - 1, Math.ceil((mx + R - x0) / res));
    const j0 = Math.max(0, Math.floor((mz - R - z0) / res)), j1 = Math.min(h - 1, Math.ceil((mz + R - z0) / res));
    for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) {
      const px = x0 + i * res, pz = z0 + j * res; const d = Math.hypot(px - mx, pz - mz);
      const k = j * w + i; if (d < near[k]) near[k] = d;
      if (d > R) continue;
      for (let L = 0; L < NL; L++) {
        const e = mastE(px, GROUND_Y + FIELD_LAYERS[L], pz, mx, mz, ax, az); if (!e[3] && !e[1]) continue;
        const o = (L * w * h + k) * 4; F[o] += e[0]; F[o + 1] += e[1]; F[o + 2] += e[2]; F[o + 3] += e[3];
      }
    }
  }
  // calibrate: mean horizontal irradiance (= E_v.y, all lamps are above the receiver) over stand-like texels, 2 m layer
  let s = 0, n = 0; const vals = [];
  for (let k = 0; k < w * h; k++) if (near[k] >= 25 && near[k] <= DC) { const e = F[k * 4 + 1]; s += e; n++; vals.push(e); }
  const scale = n ? E_STAND / (s / n) : 1;
  for (let k = 0; k < F.length; k++) F[k] *= scale;
  vals.sort((a, b) => a - b); const mn = vals.length ? vals[Math.floor(vals.length * 0.05)] * scale : 0;
  return { data: F, w, h, d: NL, rect: [x0, z0, (w - 1) * res, (h - 1) * res], layers: FIELD_LAYERS.slice(), scale, stats: { masts: masts.length, texels: n, meanH: E_STAND, p5H: +mn.toFixed(4), uniformity: mn > 0 ? +(E_STAND / mn).toFixed(2) : Infinity, res, layers: NL } };
}

// field -> half-float RGBA 3-D texture (linear filtering works everywhere for half float; float32 needs an extension on iOS)
export function floodTexture(field) {
  const half = new Uint16Array(field.data.length); for (let i = 0; i < half.length; i++) half[i] = THREE.DataUtils.toHalfFloat(field.data[i]);
  const t = new THREE.Data3DTexture(half, field.w, field.h, field.d); t.format = THREE.RGBAFormat; t.type = THREE.HalfFloatType;
  t.minFilter = t.magFilter = THREE.LinearFilter; t.generateMipmaps = false; t.wrapS = t.wrapT = t.wrapR = THREE.ClampToEdgeWrapping; t.unpackAlignment = 1; t.needsUpdate = true;
  return t;
}

// the light: intensity = lamps on (0..1 x LAMP_M, from the app's night factor), colour = lamp colour.
// spotU[k] = vec4(mast x, z, aim x, z) of the masts drawn as MastSpot lights (their share is subtracted from the field),
// spotOn[k] = 1 while spot k carries a mast. bounce = the ground albedo (rgb) for the ground-bounce term. aoNode: the
// screen-space AO node multiplied into the direct term (js/three/engine.js sets it before any material is built).
export class FloodLight extends THREE.Light {
  constructor(nSpots = 2) {
    super(new THREE.Color(...FLOOD_COLOR), 0);
    this.isFloodLight = true; this.type = 'FloodLight';
    this.fieldTex = new THREE.Data3DTexture(new Uint16Array(4 * 2), 1, 1, 2); this.fieldTex.format = THREE.RGBAFormat; this.fieldTex.type = THREE.HalfFloatType; this.fieldTex.needsUpdate = true;
    this.rect = new THREE.Vector4(0, 0, 1, 1); // x0, z0, width, depth (world metres)
    this.scale = 1; this.nSpots = nSpots; this.spotU = []; this.spotOn = [];
    for (let k = 0; k < nSpots; k++) { this.spotU.push(new THREE.Vector4(1e6, 1e6, 1, 0)); this.spotOn.push(0); }
    this.bounce = new THREE.Vector3(0.3, 0.27, 0.21); this.aoNode = null;
  }
  setField(field) { // before the first compile (renderer3.attachWorld); the node samples this.fieldTex
    if (!field) return; this.fieldTex = floodTexture(field); this.rect.set(field.rect[0], field.rect[1], field.rect[2], field.rect[3]); this.scale = field.scale; this.stats = field.stats;
  }
}
const NL = FIELD_LAYERS.length, H0 = FIELD_LAYERS[0], H1 = FIELD_LAYERS[NL - 1];
export class FloodLightNode extends THREE.AnalyticLightNode {
  static get type() { return 'FloodLightNode'; }
  constructor(light = null) {
    super(light);
    this.rectU = uniform(new THREE.Vector4(0, 0, 1, 1)); this.scaleU = uniform(1); this.bounceU = uniform(new THREE.Vector3(0.3, 0.27, 0.21));
    this.spotUs = []; this.spotOnU = [];
    const n = light ? light.nSpots : 0; for (let k = 0; k < n; k++) { this.spotUs.push(uniform(new THREE.Vector4(1e6, 1e6, 1, 0))); this.spotOnU.push(uniform(0)); }
  }
  update(frame) {
    super.update(frame); const L = this.light; if (!L) return;
    this.rectU.value.copy(L.rect); this.scaleU.value = L.scale; this.bounceU.value.copy(L.bounce);
    for (let k = 0; k < this.spotUs.length; k++) { this.spotUs[k].value.copy(L.spotU[k]); this.spotOnU[k].value = L.spotOn[k]; }
  }
  // field at the receiver (height-interpolated) and at the ground (bounce); zero outside the masts' box
  fields() {
    const L = this.light; const r = this.rectU; const wp = positionWorld;
    const u = wp.x.sub(r.x).div(r.z), v = wp.z.sub(r.y).div(r.w);
    const inside = step(0.0, u).mul(step(u, 1.0)).mul(step(0.0, v)).mul(step(v, 1.0));
    const hgt = wp.y.sub(GROUND_Y);
    const w = clamp(hgt, H0, H1).sub(H0).div(H1 - H0).mul((NL - 1) / NL).add(0.5 / NL);
    const above = float(1.0).sub(smoothstep(LAMP_H - 4.0, LAMP_H - 0.5, hgt)); // nothing above the lamps
    const f = texture3D(L.fieldTex, vec3(u, v, w)).mul(inside.mul(above));
    const g = texture3D(L.fieldTex, vec3(u, v, 0.5 / NL)).y.mul(inside);
    return { f, g };
  }
  // field minus the spot masts' share (they are drawn as shadow-casting MastSpot lights)
  residual() {
    const { f, g } = this.fields(); let Ev = f.xyz, S = f.w;
    for (let k = 0; k < this.spotUs.length; k++) { const e = mastEnode(positionWorld, this.spotUs[k], this.scaleU.mul(this.spotOnU[k])); Ev = Ev.sub(e.xyz); S = S.sub(e.w); }
    return { Ev: vec3(Ev.x, max(Ev.y, 0.0), Ev.z), S: max(S, 0.0), g };
  }
  setupDirect() {
    const { Ev } = this._res || this.residual(); const E = Ev.add(vec3(0.0, 1e-6, 0.0));
    const lightDirection = normalize(cameraViewMatrix.mul(vec4(E, 0.0)).xyz);
    let lightColor = this.colorNode.mul(length(E));
    if (this.light && this.light.aoNode) lightColor = lightColor.mul(this.light.aoNode);
    return { lightDirection, lightColor };
  }
  setup(builder) {
    const res = this.residual(); this._res = res; // one field evaluation per material build (setupDirect reads it)
    try { super.setup(builder); } finally { this._res = null; } // direct part (setupDirect), no shadows (castShadow false)
    const { Ev, S, g } = res; const N = normalWorld;
    const spread = max(S.sub(length(Ev.xz)), 0.0).mul(float(1.0).sub(abs(N.y))).mul(1.0 / Math.PI);
    const bounce = this.bounceU.mul(g).mul(float(1.0).sub(N.y).mul(0.5));
    builder.context.irradiance.addAssign(this.colorNode.mul(bounce.add(spread)));
  }
}

// one mast as a shadow-casting spot light (see 3. above). mast = vec4(x, z, aim x, aim z); intensity = lamps on x LAMP_M
// (renderer3), scale = the field's level factor (floodField().scale), so that spot k + FloodLightNode's residual = field.
export class MastSpot extends THREE.SpotLight {
  constructor(mapSize = 2048) {
    super(new THREE.Color(...FLOOD_COLOR), 0, 0, 80 * Math.PI / 180, 0, 2);
    this.isMastSpot = true; this.type = 'MastSpot';
    this.mast = new THREE.Vector4(1e6, 1e6, 1, 0); this.scale = 1;
    this.shadow.mapSize.set(mapSize, mapSize); this.shadow.camera.near = 0.5; this.shadow.camera.far = 320;
    this.shadow.bias = -0.00002; this.shadow.normalBias = 0.06; this.shadow.radius = 2;
    this.shadow.camera.layers.set(0); // everything but the masts (MAST_LAYER)
  }
  setMast(x, z, ax, az) { this.mast.set(x, z, ax, az); this.position.set(x, GROUND_Y + LAMP_H, z); this.target.position.set(x + ax * 0.01, GROUND_Y, z + az * 0.01); this.updateMatrixWorld(); this.target.updateMatrixWorld(); }
}
export class MastSpotNode extends THREE.SpotLightNode {
  static get type() { return 'MastSpotNode'; }
  constructor(light = null) { super(light); this.mastU = uniform(new THREE.Vector4(1e6, 1e6, 1, 0)); this.scaleU = uniform(1); }
  update(frame) { super.update(frame); if (this.light) { this.mastU.value.copy(this.light.mast); this.scaleU.value = this.light.scale; } }
  setupDirect() {
    const e = mastEnode(positionWorld, this.mastU, this.scaleU); const E = e.xyz.add(vec3(0.0, 1e-7, 0.0));
    return { lightDirection: normalize(cameraViewMatrix.mul(vec4(E, 0.0)).xyz), lightColor: this.colorNode.mul(length(E)) };
  }
}
void select; void vec2; void texture; void dot;
