// Detailed aircraft drawable (hwd3d Phase 3, M2; new file): a glTF model (js/aircraft/glb.js) posed by its pivots
// (js/aircraft/kinematics.js), with the SAME public interface as GaAircraft (js/aircraft/placeholder.js) so that
// js/live/aircraft.js can swap it in (Phase 3b wires it; this file does not touch js/live/**).
//
//   new DetailedAircraft(T, { model (AircraftModel | Promise<AircraftModel>), R (Renderer: installs the glass program),
//                             id, colour, lodDist, shadowDist, propBlur })
//     fields as GaAircraft: pos [x, y, z] (main-gear contact, world), fwd [x, 0, z] unit, pitch, roll (rad: nose up / right
//     wing down positive), gear 0..1 (1 = down), rotor (rad/s: propeller / fan), rotorAng, visible, selected, alpha
//     (0..1 screen-door fade set by js/live/aircraft.js on a re-placement; every item carries it, fix round 1 of Phase 3a),
//     lightsOn {nav, beacon, strobe, landing, taxi}, T (dims record), ready (Promise -> this), lodDist, shadowDist
//     methods as GaAircraft: items(camPos), lightSprites(t), step(dt), commit(), worldPt(p), dispose()
//     plus: setFlaps(deg, instant), setControls({ roll, pitch, yaw (-1..1), stabTrim, ailTrim, rudTrim, bladePitch (deg),
//           doors: { part id: 0..1 } }, instant), state() (the kinematics state), loaded, info (model summary),
//           groundRef (ground y under the aircraft for the contact occlusion of the acobj shader; null = off)
//   Until the model is ready (or if it fails to load) the drawable delegates to a GaAircraft placeholder of the same
//   dims record, so an aircraft is never invisible.
//   installAircraftPrograms(R)   registers 'acglass' (alpha-blended glass / clear lenses / propeller disc) and 'acobj'
//     (opaque aircraft surfaces: clear-coat paint, occluded interior, self-lit displays). Without them everything is drawn
//     with the obj program and the glass is opaque (dark, glossy: still reflective, no interior).
//
// Rendering: per mover group one 'acobj' item (opaque, all materials of glTF doubleSided -> noCull) and, when the group
// has alpha-blended materials, one 'acglass' item (blend 'alpha', both passes with the cloud shader's view-depth range
// rule of js/env/render_env.js, sorted back to front by distance). Propeller: when it turns faster than PROP_BLUR
// rad/s, the blade groups fade out and a blurred disc (radial profile + five soft blade sectors that drift at a slow
// apparent rate) fades in - a picture of a 30-fps camera, not physics [inf]; the hub / spinner keeps its true angle.
import { Mesh, Program } from '../gl.js';
import { m4 } from '../math.js';
import { GaAircraft } from './placeholder.js';
import { Kinematics, DEFAULT_STATE, xform, xdir } from './kinematics.js';
import { aircraftSprites } from '../env/aircraft_lights.js';
import '../shaders/common.js';   // shader chunks 'common', 'shadow' (side effect: defineChunk)
import '../shaders/ground.js';   // shader chunks 'vout', 'fout' (camera-relative clip + the colour / aux outputs)

// ---------------------------------------------------------------- glass / disc program (own shader, same chunks as obj)
export const GLASS_VS = `
#include <common>
#include <vout>
layout(location=0) in vec3 aPos; layout(location=1) in vec3 aNrm; layout(location=2) in vec2 aUV;
layout(location=3) in vec4 aCol; layout(location=4) in vec4 aExtra;
uniform mat4 uModel; uniform mat4 uPrevModel;
out vec3 vWP; out vec3 vN; out vec4 vCol; out vec4 vExt; out vec2 vUV;
void main(){
  vec4 wp = uModel * vec4(aPos, 1.0);
  vWP = wp.xyz; vN = normalize(mat3(uModel) * aNrm); vCol = aCol; vExt = aExtra; vUV = aUV;
  emitClip(wp.xyz, (uPrevModel * vec4(aPos, 1.0)).xyz);
}`;
export const GLASS_FS = `
#include <common>
#include <shadow>
#include <fout>
in vec3 vWP; in vec3 vN; in vec4 vCol; in vec4 vExt; in vec2 vUV;
uniform vec2 uRange;      // view-depth range of this pass (renderer curRange), as the cloud shader
uniform float uKind;      // 0 = glass / clear lens, 1 = propeller disc
uniform float uDisc;      // disc opacity scale (0..1)
uniform float uDiscAng;   // apparent blade angle (rad) of the disc sectors
uniform float uHub;       // hub radius / tip radius
uniform vec3 uDiscCol; uniform vec3 uTipCol;
uniform float uAlpha;     // item fade (render item field 'alpha', set by the renderer like the obj shader's): scales the blend alpha
void main(){
  if (vClip.w < uRange.x || vClip.w > uRange.y) discard;
  vec3 V = uCamPos - vWP; float dist = length(V); V /= dist;
  vec3 N = normalize(vN); if (!gl_FrontFacing) N = -N;
  float sh = getShadow(vWP, N, dist) * cloudShadow(vWP);
  vec3 col; float alpha;
  if (uKind < 0.5) {
    // thin dielectric sheet: Fresnel reflection of the sky + sun glint, tinted absorption (vCol.a = material opacity)
    float NoV = max(dot(N, V), 1e-3); float r = max(vExt.x, 0.02);
    float F = 0.04 + 0.96 * pow(1.0 - NoV, 5.0);
    vec3 R = reflect(-V, N);
    vec3 env = skyEnv(R.y < 0.0 ? vec3(R.x, -R.y * 0.3, R.z) : R, r * 7.0);
    env = R.y < 0.0 ? mix(env, uGroundBounce * 0.8, smoothstep(0.0, -0.25, R.y)) : env;
    vec3 H = normalize(uSunDir + V); float NoL = max(dot(N, uSunDir), 0.0);
    vec3 spec = D_GGX(max(dot(N, H), 0.0), r) * V_Smith(NoV, NoL, r) * F_Schlick(vec3(0.04), max(dot(V, H), 0.0)) * uSunColor * NoL * sh;
    float a0 = vCol.a;
    vec3 body = vCol.rgb * (mix(uSkyHorizon, uSkyUp, 0.5 + 0.5 * N.y) + uSunColor * NoL * sh * 0.15);
    vec3 pre = env * F + spec + body * (1.0 - F) * a0;
    alpha = clamp(F + (1.0 - F) * a0, 0.0, 1.0);
    col = min(pre / max(alpha, 1e-3), vec3(30000.0));
  } else {
    // propeller disc: radial coverage profile, soft blade sectors, white tip band
    float x = length(vUV); float ph = atan(vUV.y, vUV.x) - uDiscAng;
    float sector = pow(0.5 + 0.5 * cos(5.0 * ph), 6.0);
    float cover = smoothstep(uHub, uHub + 0.05, x) * (1.0 - smoothstep(0.95, 1.0, x));
    float tip = smoothstep(0.87, 0.91, x);
    vec3 alb = mix(uDiscCol, uTipCol, tip * 0.6);
    alpha = cover * uDisc * mix(0.15 + 0.22 * sector, 0.08 + 0.12 * sector, tip) * mix(1.0, 0.7, x);
    col = shadePBR(alb, N, V, 0.5, 0.0, sh, 1.0, 0.6);
  }
  col = applyFog(col, vWP);
  writeOut(col, vWP, alpha * clamp(uAlpha, 0.0, 1.0));
}`;
// Opaque aircraft surfaces ('acobj'). OD4 (owner request 2026-11-14: the PC-12 must look in hwd3d as it does in the pc12
// project's own three.js viewer) replaced the obj shader's PBR path + the added clear-coat lobe by the glTF 2.0
// metallic-roughness BRDF exactly as three.js r160 MeshStandardMaterial evaluates it for these glb materials (the reference
// viewer): ONE specular lobe (GGX, Smith-GGX correlated visibility, Schlick Fresnel, F0 0.04 for dielectrics, the glb's own
// roughness), Lambert diffuse, and the image-based part with three's DFG approximation and multiple-scattering energy
// compensation (three.js r160 lights_physical_pars_fragment computeMultiscattering). Before (measured, out/pc12_look):
// - a second clear-coat lobe (F0 0.04, roughness 0.05) on every paint_* / trim_* material doubled the sky reflection, so
//   the glossy black windshield surround (trim_black, roughness 0.16) and the navy cheatline read grey-blue;
// - the obj shader's hemisphere weighting (smoothstep(0, 0.55, (1 + N.y) / 2)) gave a vertical surface 98 % sky and 2 %
//   ground, so a shaded side was lit by the blue sky alone (white paint (116, 128, 146) at the reference cockpit camera);
//   now the sky / ground view factors of a plane, (1 + N.y) / 2 and (1 - N.y) / 2 (as three's HemisphereLight);
// - the cabin and flight deck were lit by the full sun and sky (the glazing casts no shadow), so through glass of 20 %
//   transmission the seats glowed; light reaches the cabin only through the glazing: sun x uCabinT (the type's glazing
//   transmission, 1 - glass alpha, js/aircraft/glb.js stats.glazingT) where the shadow map lets it in, sky x uCabinT x
//   0.35 (the windows' share of the cabin's view [inf]).
// Material ids (js/aircraft/models.js AC_MAT / AC_PART_INTERIOR; ext.z): 21 paint / trim (plain glTF material since OD4),
// 22 avionics display (self-lit, ~0.2 scene units ~ 800 cd/m2 by day at the scale of the aircraft_lights.js note "sunlit
// white paint ~17 kcd/m2" [inf]), 23 cabin / flight-deck interior (lit through the glazing, above); the back face of any
// skin (the inside of the fuselage seen through a window) counts as interior. uCabin = 0 switches the cabin rule off for a
// group (an open door's lining faces the outside). Unknown ids take the plain path; the obj program draws the same vertices
// (ids 21-23 unused there) when 'acobj' is not installed.
export const ACOBJ_FS = `
#include <common>
#include <shadow>
#include <fout>
in vec3 vWP; in vec3 vN; in vec4 vCol; in vec4 vExt; in vec2 vUV;
uniform float uEmissiveBoost; uniform float uNight; uniform float uGroundRef;
uniform float uCabinT;   // glazing transmission of the type (1 - glass alpha): the share of sun / sky that reaches the cabin
uniform float uCabin;    // 1: this group's interior surfaces are inside the closed cabin; 0: not (open door)
// uAlpha: screen-door fade of one item, the obj shader's rule (js/shaders/objects.js, fix round 1): a 4x4 ordered-dither
// threshold discards a growing share of fragments, so a re-placement fades instead of blinking (render item field 'alpha')
uniform float uAlpha;
float acBayer4(vec2 p){ ivec2 q = ivec2(mod(p, 4.0)); int i = q.x + q.y * 4; int m[16] = int[16](0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5); return (float(m[i]) + 0.5) / 16.0; }
// three.js r160 DFGApprox (Karis, "Physically Based Shading on Mobile"): scale / bias of F0 for the pre-integrated GGX lobe
vec2 acDFG(float NoV, float r){ const vec4 c0 = vec4(-1.0, -0.0275, -0.572, 0.022); const vec4 c1 = vec4(1.0, 0.0425, 1.04, -0.04);
  vec4 q = r * c0 + c1; float a004 = min(q.x * q.x, exp2(-9.28 * NoV)) * q.x + q.y; return vec2(-1.04, 1.04) * a004 + q.zw; }
// three.js r160 V_GGX_SmithCorrelated
float acVis(float NoL, float NoV, float a){ float a2 = a * a; float gv = NoL * sqrt(a2 + (1.0 - a2) * NoV * NoV); float gl = NoV * sqrt(a2 + (1.0 - a2) * NoL * NoL); return 0.5 / max(gv + gl, 1e-6); }
// sky radiance seen along R (the env map; below the horizon the ground), at the blur of roughness r
vec3 acEnv(vec3 R, float r){ vec3 e = skyEnv(R.y < 0.0 ? vec3(R.x, -R.y * 0.3, R.z) : R, r * 7.0);
  return R.y < 0.0 ? mix(e, uGroundBounce * 0.8, smoothstep(0.0, -0.25, R.y)) : e; }
void main(){
  if (uAlpha < 0.999 && uAlpha >= 0.0 && acBayer4(gl_FragCoord.xy) > uAlpha) discard;
  vec3 V = uCamPos - vWP; float dist = length(V); V /= dist;
  vec3 N = normalize(vN); bool back = !gl_FrontFacing; if (back) N = -N;
  vec3 albedo = vCol.rgb; float rough = clamp(vExt.x, 0.03, 1.0), metal = vExt.y; int mat = int(vExt.z + 0.5);
  vec3 emis = albedo * vExt.w * uEmissiveBoost;
  // light that reaches a cabin surface: through the glazing only (header)
  bool cabin = uCabin > 0.5 && (mat == 23 || mat == 22 || back);
  float sunT = cabin ? uCabinT : 1.0, ambT = cabin ? uCabinT * 0.35 : 1.0;
  // ground-contact occlusion of belly / wells / gear near the pavement (item groundRef = ground y; -1e4 = off), a softer
  // version of the obj shader's building rule (0.55 over 4 m): 0.8 over 2 m [inf]
  float ao = 1.0; if (uGroundRef > -1000.0) ao *= mix(0.8, 1.0, smoothstep(0.0, 2.0, vWP.y - uGroundRef));
  float sh = getShadow(vWP, N, dist) * cloudShadow(vWP);
  // glTF metallic-roughness: f0 = mix(0.04, base, metallic), diffuse = base x (1 - metallic), alpha = roughness^2
  vec3 f0 = mix(vec3(0.04), albedo, metal); vec3 cdiff = albedo * (1.0 - metal); float a = rough * rough;
  float NoV = clamp(dot(N, V), 1e-4, 1.0);
  // sun (direct): GGX x Smith-correlated x Schlick + Lambert
  vec3 L = uSunDir, H = normalize(L + V); float NoL = clamp(dot(N, L), 0.0, 1.0), NoH = clamp(dot(N, H), 0.0, 1.0), VoH = clamp(dot(V, H), 0.0, 1.0);
  vec3 Fs = f0 + (1.0 - f0) * pow(1.0 - VoH, 5.0);
  float a2 = a * a, dd = NoH * NoH * (a2 - 1.0) + 1.0, D = a2 / (PI * dd * dd);
  vec3 direct = (cdiff / PI + Fs * acVis(NoL, NoV, a) * D) * uSunColor * NoL * sh * sunT;
  // sky + ground (indirect): irradiance from the two view factors of a plane (header); specular from the env map with
  // three's single + multiple scattering split
  vec3 skyL = mix(uSkyHorizon, uSkyUp, clamp(N.y, 0.0, 1.0));
  vec3 Lamb = mix(uGroundBounce, skyL, 0.5 + 0.5 * N.y) * ambT * ao;     // cosine-weighted radiance (irradiance / pi)
  vec2 fab = acDFG(NoV, rough); vec3 FssEss = f0 * fab.x + fab.y; float Ess = fab.x + fab.y, Ems = 1.0 - Ess;
  vec3 Favg = f0 + (1.0 - f0) * 0.047619; vec3 Fms = FssEss * Favg / (1.0 - Ems * Favg);
  vec3 radiance = acEnv(reflect(-V, N), rough) * ambT * ao;
  vec3 indirect = radiance * FssEss + Lamb * (Fms * Ems) + Lamb * cdiff * (1.0 - (FssEss + Fms * Ems));
  vec3 col = direct + indirect;
  if (mat == 22) emis += albedo * 2.0 + vec3(0.04, 0.07, 0.11) * (1.0 + 5.0 * uNight);
  col = applyFog(col + emis, vWP);
  writeOut(min(col, vec3(30000.0)), vWP, 1.0);
}`;
// Shadow pass of 'acobj' (fix round 2): the renderer's shadow program is 'void main(){}' (js/renderer.js SHADOW_FS), so a
// fading aircraft cast its full shadow at once (review: pc12_fade.jpg, a dithered aircraft over a solid shadow). The same
// 4x4 ordered dither as the colour pass, in shadow-map texels: the PCF lookup then darkens the ground in proportion to
// uAlpha. The renderer sets uAlpha for any program that declares it (drawItems, both passes), so this needs no change in
// renderer.js; installAircraftPrograms swaps it in as the shadow half of the 'acobj' entry (an entry it created itself).
export const ACOBJ_SHADOW_FS = `
uniform float uAlpha;
float acBayer4s(vec2 p){ ivec2 q = ivec2(mod(p, 4.0)); int i = q.x + q.y * 4; int m[16] = int[16](0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5); return (float(m[i]) + 0.5) / 16.0; }
void main(){ if (uAlpha < 0.999 && uAlpha >= 0.0 && acBayer4s(gl_FragCoord.xy) > uAlpha) discard; }`;
export function installAircraftPrograms(R) {
  if (!(R && R.progs)) return false;
  if (!R.progs.acglass) R.addProgram('acglass', GLASS_VS, GLASS_FS);
  if (!R.progs.acobj) {
    R.addProgram('acobj', GLASS_VS, ACOBJ_FS);
    try { R.progs.acobj.shadow = new Program(GLASS_VS, ACOBJ_SHADOW_FS, { SHADOW_PASS: 1 }); R.progs.acobj.fadeShadow = true; }
    catch (e) { R.progs.acobj.fadeShadow = false; }   // keep the renderer's plain shadow program (items then switch at alpha 0.5)
  }
  return !!(R.progs.acglass && R.progs.acobj);
}

// ---------------------------------------------------------------- shared per model (types repeat: one GPU copy)
export const PROP_BLUR = [25, 60];   // rad/s: blades fade out / disc fades in over this range (~240-570 rpm) [inf]
export const FLAP_RATE = 11;         // deg/s (pc12 viewer: 0 -> 40 in ~3.6 s) [inf]
export const CONTROL_LAG = 7;        // 1/s first-order lag of roll / pitch / yaw commands (pc12 viewer) [inf]
const RES = new WeakMap();
function resources(model) {
  let r = RES.get(model); if (r) return r;
  const kin = new Kinematics(model); const P = model.parts;
  // propeller: a 'spin' mover with 'pitch' blade movers below it -> a disc (blade tip radius, hub radius, plane)
  let prop = null;
  const spin = kin.movers.find(i => P[i].pivot.kind === 'spin');
  if (spin != null) {
    const blades = kin.movers.filter(i => P[i].pivot.kind === 'pitch' && kin.up[i] === spin);
    if (blades.length) {
      const o = P[spin].pivot.origin, a = P[spin].pivot.axis; let R = 0, along = 0, n = 0, tipCol = null, bladeCol = null;
      for (const g of model.groups) { if (!blades.includes(g.mover) || !g.opaque) continue; const p = g.opaque.pos;
        for (let i = 0; i < p.length; i += 3) { const d = [p[i] - o[0], p[i + 1] - o[1], p[i + 2] - o[2]]; const t = d[0] * a[0] + d[1] * a[1] + d[2] * a[2];
          const rr = Math.hypot(d[0] - a[0] * t, d[1] - a[1] * t, d[2] - a[2] * t); if (rr > R) { R = rr; tipCol = [g.opaque.col[i / 3 * 4], g.opaque.col[i / 3 * 4 + 1], g.opaque.col[i / 3 * 4 + 2]]; } along += t; n++; }
        bladeCol = bladeCol || [g.opaque.col[0], g.opaque.col[1], g.opaque.col[2]]; }
      let hub = 0; const sg = model.groups.find(g => g.mover === spin);
      if (sg && sg.opaque) { const p = sg.opaque.pos; for (let i = 0; i < p.length; i += 3) { const d = [p[i] - o[0], p[i + 1] - o[1], p[i + 2] - o[2]]; const t = d[0] * a[0] + d[1] * a[1] + d[2] * a[2]; hub = Math.max(hub, Math.hypot(d[0] - a[0] * t, d[1] - a[1] * t, d[2] - a[2] * t)); } }
      prop = { spin, blades, R, hub: Math.min(0.6, hub / R), centre: [o[0] + a[0] * along / n, o[1] + a[1] * along / n, o[2] + a[2] * along / n], axis: a, bladeCol, tipCol, rpm: P[spin].pivot.rpm || null };
      prop.disc = discGeo(prop);
    }
  }
  // the rotor mover of any kind of rotor (propeller with blade movers, or a fan without them: SF50) - motion vectors use it
  r = { kin, prop, spin: spin != null ? spin : -1, gpu: null, glassProg: false };
  RES.set(model, r); return r;
}
function discGeo(pr) {   // flat annulus in the prop plane; uv = (cos, sin) x r / R in the disc's own basis
  const a = pr.axis, t1 = Math.abs(a[1]) < 0.9 ? [0, 1, 0] : [1, 0, 0];
  let u = [a[1] * t1[2] - a[2] * t1[1], a[2] * t1[0] - a[0] * t1[2], a[0] * t1[1] - a[1] * t1[0]]; const lu = Math.hypot(...u); u = u.map(v => v / lu);
  const w = [a[1] * u[2] - a[2] * u[1], a[2] * u[0] - a[0] * u[2], a[0] * u[1] - a[1] * u[0]];
  const S = 96, rings = [pr.hub * 0.95, 0.5, 0.88, 0.9, 1.0], pos = [], nrm = [], col = [], ext = [], uv = [], idx = [];
  for (let j = 0; j < rings.length; j++) for (let i = 0; i <= S; i++) {
    const f = i / S * Math.PI * 2, c = Math.cos(f), s = Math.sin(f), r = rings[j] * pr.R;
    pos.push(pr.centre[0] + (u[0] * c + w[0] * s) * r, pr.centre[1] + (u[1] * c + w[1] * s) * r, pr.centre[2] + (u[2] * c + w[2] * s) * r);
    nrm.push(a[0], a[1], a[2]); col.push(1, 1, 1, 1); ext.push(0.5, 0, 0, 0); uv.push(c * rings[j], s * rings[j]);
  }
  for (let j = 0; j < rings.length - 1; j++) for (let i = 0; i < S; i++) { const p = j * (S + 1) + i, q = p + S + 1; idx.push(p, q, p + 1, p + 1, q, q + 1); }
  const P = new Float32Array(pos); const bb = [1e9, 1e9, 1e9, -1e9, -1e9, -1e9]; for (let i = 0; i < P.length; i += 3) for (let k = 0; k < 3; k++) { bb[k] = Math.min(bb[k], P[i + k]); bb[k + 3] = Math.max(bb[k + 3], P[i + k]); }
  return { pos: P, nrm: new Float32Array(nrm), col: new Float32Array(col), extra: new Float32Array(ext), uv: new Float32Array(uv), idx: new Uint32Array(idx), bbox: bb };
}
function gpu(res, model) {
  if (res.gpu) return res.gpu;
  res.gpu = { groups: model.groups.map(g => ({ key: g.key, mover: g.mover, opaque: g.opaque ? new Mesh(g.opaque) : null, glass: g.glass ? new Mesh(g.glass) : null })),
    disc: res.prop ? new Mesh(res.prop.disc) : null };
  // the vertex / index arrays are on the GPU now: a model loaded by js/aircraft/models.js loadModel with keepCpu false (the
  // app) drops its CPU copies (~21 MB of JS heap per type; the review's cost finding); a model passed in directly (tests,
  // tools) or loaded with keepCpu true (dev viewer) keeps them. Kinematics, lights, bbox and the prop disc do not need them.
  if (model.keepCpu === false) for (const g of model.groups) for (const k of ['opaque', 'glass']) if (g[k]) g[k] = { bbox: g[k].bbox, released: true };
  return res.gpu;
}

// ---------------------------------------------------------------- drawable
// fields copied to the GaAircraft placeholder every frame while the model loads (or after it failed): every field
// js/live/aircraft.js sets on a drawable (fix round 1: 'alpha' was missing, so a loading aircraft blinked)
export const SYNC_KEYS = ['pos', 'fwd', 'pitch', 'roll', 'gear', 'rotor', 'lightsOn', 'selected', 'visible', 'alpha'];
export class DetailedAircraft {
  constructor(T, { model = null, R = null, id = null, colour = null, lodDist = 8000, shadowDist = 2500, propBlur = true } = {}) {
    this.T = T; this.id = id; this.colour = colour; this.lodDist = lodDist; this.shadowDist = shadowDist; this.R = R; this.propBlur = propBlur;
    this.pos = [0, 0, 0]; this.fwd = [0, 0, -1]; this.pitch = 0; this.roll = 0; this.gear = 1; this.rotor = 0; this.rotorAng = 0; this.discAng = 0;
    this.visible = true; this.alpha = 1; this.selected = false; this.lightsOn = { nav: false, beacon: false, strobe: false, landing: false, taxi: false };
    this.seed = Math.random() * 10; this.model = m4.ident(); this.prevModel = null;
    this.flaps = 0; this.flapsTarget = 0; this.groundRef = null;   // groundRef: ground y under the aircraft (contact AO; null = off)
    this.ctl = { roll: 0, pitch: 0, yaw: 0, stabTrim: 0, ailTrim: 0, rudTrim: 0, bladePitch: 0 }; this.ctlTarget = { ...this.ctl }; this.doors = {};
    this.placeholder = T ? new GaAircraft(T, { id, colour, lodDist, shadowDist }) : null;
    this.m = null; this.res = null; this.loaded = false; this.error = null; this._pose = null; this._prev = new Map(); this._cur = new Map();
    this.glassProg = installAircraftPrograms(R);
    this.ready = Promise.resolve(model).then((mdl) => { if (!mdl) throw new Error('no model'); this.m = mdl; this.res = resources(mdl); this.loaded = true; return this; })
      .catch((e) => { this.error = String(e && e.message || e); return this; });
  }
  get info() { const m = this.m; return m ? { name: m.name, tris: m.stats.tris, parts: m.stats.parts, movers: this.res.kin.movers.length, bbox: m.bbox, contacts: m.contacts, wheelbase: m.wheelbase, track: m.track, prop: this.res.prop ? { R: this.res.prop.R, rpm: this.res.prop.rpm } : null } : null; }
  // ---- commands
  setFlaps(deg, instant = false) { this.flapsTarget = Math.max(0, +deg || 0); if (instant) this.flaps = this.flapsTarget; return this; }
  setControls(o = {}, instant = false) {
    for (const k of Object.keys(this.ctl)) if (o[k] != null) { this.ctlTarget[k] = +o[k]; if (instant) this.ctl[k] = this.ctlTarget[k]; }
    if (o.doors) Object.assign(this.doors, o.doors);
    return this;
  }
  // a fan (a 'spin' mover without blade movers: no disc) shows the slow apparent angle above PROP_BLUR[1] rad/s, so a
  // video does not strobe through random blade positions [inf: a picture choice]
  state() {
    const fanApparent = this.res && !this.res.prop && Math.abs(this.rotor) > PROP_BLUR[1];
    return { ...DEFAULT_STATE, gear: this.gear, flaps: this.flaps, rotorAng: fanApparent ? this.discAng : this.rotorAng, ...this.ctl, doors: this.doors };
  }
  step(dt) {
    this.rotorAng = (this.rotorAng + this.rotor * dt) % (Math.PI * 2);
    // apparent disc-sector rate: a slow drift (stroboscopic look of a video camera) [inf]
    this.discAng = (this.discAng + Math.sign(this.rotor) * Math.min(Math.abs(this.rotor), 2.5) * dt) % (Math.PI * 2);
    const d = this.flapsTarget - this.flaps, st = FLAP_RATE * dt; this.flaps = Math.abs(d) <= st ? this.flapsTarget : this.flaps + Math.sign(d) * st;
    const k = 1 - Math.exp(-CONTROL_LAG * dt);
    for (const key of ['roll', 'pitch', 'yaw']) this.ctl[key] += (this.ctlTarget[key] - this.ctl[key]) * k;
    for (const key of ['stabTrim', 'ailTrim', 'rudTrim', 'bladePitch']) { const e = this.ctlTarget[key] - this.ctl[key], s = (key === 'bladePitch' ? 35 : key === 'stabTrim' ? 1.2 : 6) * dt; this.ctl[key] = Math.abs(e) <= s ? this.ctlTarget[key] : this.ctl[key] + Math.sign(e) * s; }
    if (this.placeholder) this.placeholder.step(dt);
  }
  basis() {
    const f = this.fwd, r = [-f[2], 0, f[0]];
    const B = new Float32Array([f[0], 0, f[2], 0, 0, 1, 0, 0, r[0], 0, r[2], 0, this.pos[0], this.pos[1], this.pos[2], 1]);
    return m4.mul(m4.mul(B, m4.rotZ(this.pitch)), m4.rotX(this.roll));
  }
  syncPlaceholder() { const p = this.placeholder; if (!p) return null; for (const k of SYNC_KEYS) p[k] = this[k]; return p; }
  items(camPos) {
    if (!this.loaded) {   // placeholder (js/aircraft/placeholder.js, not M2): its shadow switches at alpha 0.5 (see above)
      const p = this.syncPlaceholder(); const it = p ? p.items(camPos) : []; const a = this.alpha == null ? 1 : +this.alpha;
      if (a < 0.5) for (const i of it) i.castShadow = false; return it;
    }
    const m = this.m, res = this.res, R0 = this.R; const G = gpu(res, m); this.model = this.basis();
    const d = camPos ? Math.hypot(camPos[0] - this.pos[0], camPos[1] - this.pos[1], camPos[2] - this.pos[2]) : 0;
    if (d > this.lodDist) return [];
    const pose = this._pose = res.kin.pose(this.state());
    // world bbox of the rest bbox (+0.6 m for moving parts), conservative
    const b = m.bbox, bb = [1e9, 1e9, 1e9, -1e9, -1e9, -1e9];
    for (let k = 0; k < 8; k++) { const p = xform(this.model, [k & 1 ? b[3] + 0.6 : b[0] - 0.6, k & 2 ? b[4] + 0.6 : b[1] - 0.6, k & 4 ? b[5] + 0.6 : b[2] - 0.6]); for (let j = 0; j < 3; j++) { bb[j] = Math.min(bb[j], p[j]); bb[j + 3] = Math.max(bb[j + 3], p[j]); } }
    const out = [], prop = res.prop, w = Math.abs(this.rotor);
    const alpha = this.alpha == null ? 1 : Math.max(0, Math.min(1, +this.alpha));
    // shadows fade with the aircraft (fix round 2): the acobj shadow program dithers by uAlpha; the obj fallback (renderer's
    // plain shadow program) casts from alpha 0.5 on, half way through the fade, instead of from the first frame
    const fadeSh = !!(R0 && R0.progs && R0.progs.acobj && R0.progs.acobj.fadeShadow);
    const sh = d < this.shadowDist && alpha > 0 && (fadeSh && this.glassProg ? true : alpha >= 0.5);
    const blur = this.propBlur && prop ? Math.min(1, Math.max(0, (w - PROP_BLUR[0]) / (PROP_BLUR[1] - PROP_BLUR[0]))) : 0;
    // fix round 2: keyed on the 'spin' mover itself, not on the propeller disc - the SF50 fan has no blade movers (no disc,
    // prop null), so its groups kept the true previous-frame rotation (0.31-0.42 m of false motion 0.25 m off the axis at
    // 40-59 rad/s, review probe); above PROP_BLUR[1] the fan shows the slow apparent angle (state()), which is left out too
    const spinning = (mv) => { if (res.spin < 0 || w < PROP_BLUR[0]) return false; for (let q = mv; q >= 0; q = res.kin.up[q]) if (q === res.spin) return true; return false; };
    this._cur.clear();
    const R = this.R, glassOK = this.glassProg && R;
    const cabinT = m.stats && m.stats.glazingT != null ? m.stats.glazingT : 0.2;   // 1 - glass alpha (js/aircraft/glb.js stats.glazingT)
    // motion vectors: a group's prevModel is its previous-frame model; a group riding on a fast-spinning propeller / fan
    // takes the previous AIRCRAFT model times its CURRENT pose, so its velocity is the aircraft's (translation and attitude
    // change kept, the blade rotation left out: ~340 deg per 30-fps frame at 1,700 rpm is not a velocity a buffer can hold)
    // - fix round 1: it was the current model, i.e. no aircraft motion at all, which streaks under a moving chase camera
    const prevBasis = this.prevModel || this.model;
    for (const g of G.groups) {
      if (prop && blur >= 1 && prop.blades.includes(g.mover)) continue;   // blades replaced by the disc
      const Mg = g.mover >= 0 && pose[g.mover] ? m4.mul(this.model, pose[g.mover]) : this.model;
      const prev = spinning(g.mover) ? m4.mul(prevBasis, pose[g.mover]) : (this._prev.get(g.key) || Mg); this._cur.set(g.key, Mg);
      // acobj uniforms are set on EVERY draw (GL keeps uniform values per program, so a value would leak to the next aircraft):
      // the selection glow, the type's glazing transmission and whether this group's lining is inside the closed cabin (an open
      // door's lining faces the outside; OD4)
      const doorOpen = g.mover >= 0 && m.parts[g.mover].pivot && m.parts[g.mover].pivot.kind === 'door' && (this.doors[g.key] || 0) > 0.02;
      if (g.opaque) out.push({ mesh: g.opaque, prog: glassOK ? 'acobj' : 'obj', model: Mg, prevModel: prev, bbox: bb, castShadow: sh, noCull: true,
        uniforms: glassOK ? { uEmissiveBoost: this.selected ? 0.15 : 0, uCabinT: cabinT, uCabin: doorOpen ? 0 : 1 } : (this.selected ? { uEmissiveBoost: 0.15 } : undefined),
        groundRef: glassOK && this.groundRef != null ? this.groundRef : undefined });
      if (g.glass) {
        if (glassOK) { const c = xform(Mg, [(m.bbox[0] + m.bbox[3]) / 2, (m.bbox[1] + m.bbox[4]) / 2, (m.bbox[2] + m.bbox[5]) / 2]);
          out.push({ mesh: g.glass, prog: 'acglass', blend: 'alpha', bothPasses: true, model: Mg, prevModel: prev, bbox: bb, castShadow: false, noCull: true,
            sortKey: (cp) => Math.hypot(cp[0] - c[0], cp[1] - c[1], cp[2] - c[2]) - 0.01, uniforms: () => ({ uRange: R.curRange || [0, 1e9], uKind: 0 }) }); }
        else out.push({ mesh: g.glass, prog: 'obj', model: Mg, prevModel: prev, bbox: bb, castShadow: false, noCull: true });
      }
    }
    if (prop && blur > 0 && glassOK && G.disc) {
      const par = res.kin.up[prop.spin], Md = par >= 0 ? m4.mul(this.model, pose[par]) : this.model; const c = xform(Md, prop.centre);
      const Mdp = par >= 0 ? m4.mul(prevBasis, pose[par]) : prevBasis;   // the disc moves with the aircraft (see above)
      const U = { uKind: 1, uDisc: blur, uDiscAng: this.discAng * Math.sign(this.rotor || 1), uHub: prop.hub, uDiscCol: prop.bladeCol || [0.05, 0.05, 0.05], uTipCol: prop.tipCol || [0.9, 0.9, 0.9] };
      out.push({ mesh: G.disc, prog: 'acglass', blend: 'alpha', bothPasses: true, model: Md, prevModel: Mdp, bbox: bb, castShadow: false, noCull: true,
        sortKey: (cp) => Math.hypot(cp[0] - c[0], cp[1] - c[1], cp[2] - c[2]), uniforms: () => Object.assign({ uRange: R.curRange || [0, 1e9] }, U) });
    }
    for (const it of out) { if (!it.uniforms) delete it.uniforms; if (it.groundRef === undefined) delete it.groundRef; it.alpha = alpha; }
    return out;
  }
  // world position of a local point riding on part `mover` (-1 = airframe)
  worldPt(p, mover = -1) { const P = this._pose; const q = mover >= 0 && P && P[mover] ? xform(P[mover], p) : p; return m4.xform(this.model, q); }
  lightSprites(t) {
    if (!this.loaded) { const p = this.syncPlaceholder(); return p ? p.lightSprites(t) : []; }
    const on = this.lightsOn; if (!on || !(on.nav || on.beacon || on.strobe || on.landing || on.taxi)) return [];
    if (!this._pose) this._pose = this.res.kin.pose(this.state());
    const Lc = this.m.lights, W = {};
    for (const k in Lc) W[k] = Lc[k] ? this.worldPt(Lc[k].p, Lc[k].part) : null;
    // landing / taxi lamps on a retracting leg: off once the leg leaves the down lock (they point into the well)
    const legDown = this.gear > 0.98;
    for (const k of ['landL', 'landR', 'taxi']) if (Lc[k] && Lc[k].part >= 0 && !legDown) W[k] = null;
    const fwd = m4.xdir(this.model, [1, 0, 0]), up = m4.xdir(this.model, [0, 1, 0]), right = m4.xdir(this.model, [0, 0, 1]);
    const landDir = m4.xdir(this.model, [Math.cos(0.05), -Math.sin(0.05), 0]), taxiDir = m4.xdir(this.model, [Math.cos(0.1), -Math.sin(0.1), 0]);
    const axes = { fwd, right, up, landDir, taxiDir };
    try {
      const S = aircraftSprites(W, axes, on, this.seed, t, this.gear);
      // a tail strobe (SF50: AFM anti-collision lights 3 = 2 tips + tail): js/env/aircraft_lights.js draws strobeL / strobeR
      // only, so the third one goes through the same function as a 'strobeL' with the same seed -> the same flash phase
      if (on.strobe && W.strobeTail) for (const sp of aircraftSprites({ strobeL: W.strobeTail }, axes, { strobe: true }, this.seed, t, this.gear)) S.push(sp);
      return S;
    } catch (e) { return []; }
  }
  commit() { this.prevModel = this.model; const t = this._prev; this._prev = this._cur; this._cur = t; if (this.placeholder) this.placeholder.commit(); }
  dispose() { if (this.placeholder) this.placeholder.dispose(); }   // GPU meshes are shared per model (released with the page)
}
export { xdir };
