// sha3d ground shader (new). Replaces sfo3d@e3218d6 js/shaders/ground.js, which is NOT forked: its procedural runway
// markings are FAA AC 150/5340-1 geometry and its city bakes are SFO's. Here the ground is:
//   - the airfield map (js/world/ground.js, CPU-painted from data/sha_airport.js surfaces / runways / aprons): R airside
//     pavement, G concrete fraction, B shoulder / blast pad, A landside road; edges are re-sharpened at magnification
//     (threshold at 0.5 with a derivative-width smoothstep), so a 1 m map gives crisp edges up close;
//   - the context map (extent bbox, coarse): R water, G road, B rail, A = 0.5 x extent mask + 0.5 x aerodrome mask;
//   - the Sentinel-2 colour hint (data/sha_ground_s2.js, 10 m surface reflectance) for unpaved ground, with procedural
//     detail on top; outside the 23.5 km2 detailed extent everything fades to one neutral ground colour.
// Paint (markings) is NOT drawn here: the chunk `sha_ground_paint` is a hook (default: none) that js/live/markings.js may
// redefine (gl.js defineChunk) before the world compiles the ground program - see js/live/ext.js.
// The chunk `sha_ground_far` (added by package P2d, js/live/terminals.js redefines it) is the hook for the ground BEYOND
// the detailed extent: its default returns the neutral colour and no haze, i.e. exactly the core behaviour above.
// Every material value below is an inferred rendering default [inf], not a measured property.
import { defineChunk } from '../gl.js';

defineChunk('sha_ground_paint', `
// Ground paint hook (default: no paint). Return rgb = paint albedo (linear), a = coverage 0..1. Inputs: wp world position,
// fw = isotropic world size of a pixel (m), dxy = (dFdx(wp.xz), dFdy(wp.xz)) taken in uniform control flow (for footprints
// along a given direction: an edge is smoothed over the footprint along its normal, fix round 1 H1), apt = airfield-map
// sample (r paved, g concrete, b shoulder, a landside road; raw, not sharpened), paved = sharpened airside-pavement
// coverage. May lower rough (paint is smoother).
vec4 shaGroundPaint(vec3 wp, float fw, vec4 dxy, vec4 apt, float paved, inout float rough){ return vec4(0.0); }
`);

defineChunk('sha_ground_far', `
// Far-ground hook (default: the core's neutral ground, no water, no glow, no haze). shaGroundFar returns the albedo beyond
// the detailed extent (it is mixed in where the extent mask ext < 1) and may set water (0..1, sky-reflecting water) and glow
// (0..1, night urban glow); shaGroundFarHaze is applied to the lit colour after applyFog (V = unit vector to the camera,
// night = uNight). Redefined by js/live/terminals.js (ESA WorldCover far ground + distance haze, package P2d).
vec3 shaGroundFar(vec3 wp, float dist, vec3 neutral, inout float water, inout float glow){ return neutral; }
vec3 shaGroundFarHaze(vec3 col, vec3 wp, float dist, vec3 V, float ext, float night){ return col; }
`);

// Apron night flood (fix round 1, review M1 part a) [inf]: photos 12, 13, 19 and 20 show brightly flood-lit aprons (high-mast
// LED / sodium flood). The apron (airfield map G = 255) gets a warm flood of APRON_FLOOD x albedo (the stand mean), varied
// over ~2 km and ~150 m. Shared with the decal shader so the apron paint is lit like the apron. Runway, taxiway and stop-bar
// lighting is Phase 5, not here.
// Fix round 2 (review N2 / M1 / N4): when a light map is bound (uApLightOn = 1; built by js/live/markings.js apronLightMap,
// parameters CAAC.apronFlood in js/live/caac_markings.js, MH 5001-2021 9.2.2 / 9.2.6) the lit area is
//   max(apron, map R) - R = apron + the airside pavement packages add to the airfield map (the T1 / T2 airside fill, which is
//   runway-class asphalt in the map and was a black moat at night) + a soft ~20-30 m spill past that area's edge -
// and the level is x (gScale x map G) - G x gScale = the summed pools of the inferred apron masts (gates package): relative
//   to the stand mean, floor 0.5 (9.2.6-2: other apron >= 50 % of the stand average), cap 1.8, then scaled so that the mean
//   over the lit area is 1 (the fix round 1 level) [inf]; G = 1 / gScale (x 1) until the masts are known.
// Without the map (uApLightOn = 0, the GLSL default for a program that does not set it) the function is the fix round 1
// flood. Programs that include this chunk: set uApLight / uApLightRect / uApLightOn from the ground uniforms
// (app.world.groundU) to get the same light; the texture object is updated in place when the masts arrive.
export const APRON_FLOOD = { level: 0.42, tint: [1.0, 0.82, 0.6], gScale: 2.5, src: 'inf: level and tint chosen against photos 12/13/19/20 (= the mean over the lit area); shape: light map (CAAC.apronFlood, 9.2.6 floor)' };
export const APRON_FLOOD_GLSL = `
uniform sampler2D uApLight; uniform vec4 uApLightRect; uniform float uApLightOn;   // light map: R lit area + spill, G pools / 2
vec3 shaApronFlood(vec3 wp, vec4 apt, float paved, float nLarge, float nMid){
  float apronN = paved * smoothstep(0.86, 0.95, apt.g);   // apron = G 255 (js/world/ground.js)
  vec2 L = texture(uApLight, (wp.xz - uApLightRect.xy) / max(uApLightRect.zw, vec2(1.0))).rg;   // clamp to edge: 0 outside
  float k = 1.0;
  if (uApLightOn > 0.5) { apronN = max(apronN, L.r); k = ${APRON_FLOOD.gScale.toFixed(2)} * L.g; }
  return vec3(${APRON_FLOOD.tint.map(v => v.toFixed(3)).join(', ')}) * apronN * k * (0.75 + 0.25 * nLarge) * (0.85 + 0.15 * nMid) * ${APRON_FLOOD.level.toFixed(3)};
}`;
defineChunk('sha_apron_flood', APRON_FLOOD_GLSL);

export const GROUND_VS = `
#include <common>
#include <vout>
layout(location=0) in vec3 aPos; layout(location=1) in vec3 aNrm;
out vec3 vWP; out vec3 vN;
void main(){ vWP = aPos; vN = aNrm; emitClip(aPos, aPos); }`;

export const GROUND_FS = `
#include <common>
#include <shadow>
#include <fout>
#include <sha_ground_paint>
#include <sha_ground_far>
#include <sha_apron_flood>
in vec3 vWP; in vec3 vN;
uniform sampler2D uAptMap; uniform vec4 uAptRect;     // airfield map, rect = (x0, z0, w, h) in world metres
uniform sampler2D uCtxMap; uniform vec4 uCtxRect;     // context map
uniform sampler2D uS2; uniform vec4 uS2Rect; uniform float uHasS2; uniform float uS2Mix;
uniform vec2 uGridDir;                                // runway axis (world x, z), for the concrete slab grid
uniform vec3 uNeutral;                                // ground albedo beyond the detailed extent
uniform float uNight;
float sharp(float v, float lo, float hi){ float w = clamp(fwidth(v) * 0.75, 0.004, 0.5); return smoothstep(0.5 - w, 0.5 + w, v); }
vec3 srgb2lin(vec3 c){ return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(0.04045, c)); }
bool inRect(vec2 uv){ return uv.x > 0.0 && uv.x < 1.0 && uv.y > 0.0 && uv.y < 1.0; }
void main(){
  vec3 wp = vWP; vec3 V = uCamPos - wp; float dist = length(V); V /= dist;
  vec3 N = vec3(0.0, 1.0, 0.0);
  float fw = length(fwidth(wp.xz)) * 0.7 + 0.001;
  vec4 dxy = vec4(dFdx(wp.xz), dFdy(wp.xz));   // for the paint hook (directional footprints)
  vec2 cuv = (wp.xz - uCtxRect.xy) / uCtxRect.zw; vec4 ctx = inRect(cuv) ? texture(uCtxMap, cuv) : vec4(0.0);
  vec2 auv = (wp.xz - uAptRect.xy) / uAptRect.zw; bool inApt = inRect(auv); vec4 apt = inApt ? texture(uAptMap, auv) : vec4(0.0);
  float ext = clamp(ctx.a * 2.0, 0.0, 1.0), aero = clamp(ctx.a * 2.0 - 1.0, 0.0, 1.0);
  // the OSM context lines (roads, rail, water, ditches) end at the extent polygon, where the soft mask is 0.5: fade them out
  // inside the ramp so they do not stop at half weight (fix round 1, buildings hand-off; rendering rule, inf)
  float extF = smoothstep(0.55, 0.95, ext);
  vec4 nzA = texture(uNoise, wp.xz * (1.0 / 1900.0)), nzB = texture(uNoise, wp.xz * (1.0 / 150.0)), nzC = texture(uNoise, wp.xz * (1.0 / 11.0));
  float near = 1.0 - smoothstep(150.0, 900.0, dist);
  // ---- unpaved ground: procedural grass (inside the aerodrome) / urban-green mix (outside) [inf], S2 colour on top
  vec3 grass = mix(vec3(0.115, 0.125, 0.060), vec3(0.150, 0.140, 0.080), nzA.g) * (0.86 + 0.28 * nzB.r);
  vec3 urban = mix(vec3(0.115, 0.112, 0.100), vec3(0.085, 0.105, 0.055), nzA.b) * (0.82 + 0.36 * nzB.g);
  vec3 alb = mix(urban, grass, aero);
  if (uHasS2 > 0.5) {
    vec2 suv = (wp.xz - uS2Rect.xy) / uS2Rect.zw;
    if (inRect(suv)) { vec4 s = texture(uS2, suv); vec3 rho = srgb2lin(s.rgb) * 0.5;
      // inside the aerodrome the 10 m pixels next to pavement are mixed with concrete: keep the hint's brightness but cap it
      rho = mix(rho, min(rho, vec3(0.16)), aero);
      alb = mix(alb, rho * mix(1.0, 0.82 + 0.36 * nzC.r, near), uS2Mix * s.a); }
  }
  alb *= mix(1.0, 0.9 + 0.2 * nzC.g, near * 0.6);
  alb *= 1.0 - 0.3 * smoothstep(0.08, 0.4, ctx.r) * (1.0 - smoothstep(0.45, 0.55, ctx.r)) * extF;   // ditches / drains: damp ground (js/world/ground.js)
  // ---- beyond the detailed extent: neutral ground with a large-scale variation only
  vec3 neutral = uNeutral * (0.95 + 0.1 * nzA.r) * (0.97 + 0.06 * nzB.g);
  float farWater = 0.0, farGlow = 0.0;
  if (ext < 0.999) neutral = shaGroundFar(wp, dist, neutral, farWater, farGlow);   // hook (default: neutral)
  alb = mix(neutral, alb, ext);
  // ---- landside roads (fine map inside its rect, the context map elsewhere) and rail ballast
  float road = max(inApt ? sharp(apt.a, 0.0, 1.0) : 0.0, sharp(ctx.g, 0.0, 1.0) * extF);
  alb = mix(alb, vec3(0.085, 0.086, 0.09) * (0.9 + 0.2 * nzB.b), road);
  float rail = sharp(ctx.b, 0.0, 1.0) * extF * (1.0 - road);
  alb = mix(alb, vec3(0.11, 0.10, 0.09) * (0.85 + 0.3 * nzC.b), rail);
  // ---- airside pavement
  float paved = inApt ? sharp(apt.r, 0.0, 1.0) : 0.0;
  float rough = 0.95;
  if (paved > 0.001) {
    float conc = sharp(apt.g, 0.0, 1.0), shoulder = sharp(apt.b, 0.0, 1.0);
    vec2 g = vec2(dot(wp.xz, vec2(-uGridDir.y, uGridDir.x)), dot(wp.xz, uGridDir));   // (across, along) the runway axis
    vec3 asph = vec3(0.085, 0.087, 0.092) * (0.86 + 0.28 * nzB.b) * (0.94 + 0.12 * nzC.g);
    // concrete: 5 m slabs on the runway grid [inf: slab size not sourced], per-slab tone, stains
    vec2 slab = floor(g / 5.0);
    vec3 cc = vec3(0.30, 0.295, 0.275) * (0.9 + 0.2 * nzB.a) * (0.96 + 0.08 * ihashf(ivec2(slab), 5));
    cc *= 1.0 - 0.14 * smoothstep(0.6, 0.9, nzB.r) * nzC.r;
    float jw = max(fw, 0.004); vec2 jf = abs(fract(g / 5.0 + 0.5) - 0.5) * 5.0;
    float joint = (1.0 - smoothstep(0.012, 0.012 + jw, min(jf.x, jf.y))) * min(1.0, 0.03 / jw) * (1.0 - smoothstep(80.0, 300.0, dist));
    cc *= 1.0 - 0.35 * joint;
    vec3 sh = vec3(0.12, 0.118, 0.11) * (0.88 + 0.24 * nzB.g);
    vec3 pav = mix(asph, cc, conc);
    pav = mix(pav, sh, shoulder * (1.0 - conc));
    alb = mix(alb, pav, paved);
    rough = mix(0.95, mix(0.82, 0.88, conc), paved);
  }
  vec4 paint = shaGroundPaint(wp, fw, dxy, apt, paved, rough);
  alb = mix(alb, paint.rgb, paint.a);
  // ---- light
  float sh = getShadow(wp, N, dist) * cloudShadow(wp);
  float NoL = max(uSunDir.y, 0.0);
  vec3 col = alb / PI * uSunColor * NoL * sh + alb * uSkyUp;
  vec3 H = normalize(uSunDir + V); float spec = D_GGX(max(H.y, 0.0), rough) * 0.03 * NoL * sh;
  col += uSunColor * spec * (1.0 - rough) * 2.0 * max(paved, road);
  // ---- water (canals, rivers, ponds: OSM context): turbid body + sky reflection with Fresnel [inf]
  // fix round 1 (review M6): the body was ink-black (0.016, 0.022, 0.016) from above while the far rivers read blue; the
  // Shanghai canals are turbid green-brown [inf: rendering albedo, not measured], and a reflection floor (ripples, haze)
  // keeps near-normal views from going black. Narrow ditches / drains (3-5 m, peak coverage < 0.9 in the 4 m context map)
  // stay body-only (damp ground lines); water wider than ~10 m (coverage 1) gets the full Fresnel term with the floor.
  float water = sharp(ctx.r, 0.0, 1.0) * extF;
  float farW = farWater * (1.0 - ext); water = max(water, farW);
  if (water > 0.001) {
    vec2 rp = (texture(uNoise, wp.xz * 0.05 + uTime * 0.01).rg - 0.5) * 0.06 * near;
    vec3 Nw = normalize(vec3(rp.x, 1.0, rp.y)); vec3 R = reflect(-V, Nw);
    float F = mix(0.06, 1.0, pow(1.0 - max(dot(Nw, V), 0.0), 5.0));
    F *= max(smoothstep(0.55, 0.9, ctx.r) * step(farW, 0.0), farW);   // narrow drains: the body only (as before); far water: its fraction
    vec3 body = vec3(0.050, 0.060, 0.045) * (uSkyUp + uSunColor * NoL * sh / PI);
    vec3 wc = body * (1.0 - F) + skyEnv(R, 1.0) * F;
    col = mix(col, wc, water);
  }
  // ---- night [inf]: a faint urban glow outside the aerodrome and the apron flood (shaApronFlood: apron + airside fill + spill,
  //      mast pools when the light map is bound, fix round 2)
  if (uNight > 0.001) {
    float urbanN = ext * (1.0 - aero) * (1.0 - water);
    col += alb * vec3(1.0, 0.75, 0.5) * urbanN * (0.3 + 0.7 * nzB.g * nzC.b) * 0.10 * uNight;
    col += alb * shaApronFlood(wp, apt, paved, nzA.g, nzB.r) * uNight;
    col += alb * vec3(1.0, 0.75, 0.5) * farGlow * (1.0 - ext) * (1.0 - water) * 0.10 * uNight;   // far-ground hook glow (default 0)
  }
  col = applyFog(col, wp);
  col = shaGroundFarHaze(col, wp, dist, V, ext, uNight);   // hook (default: unchanged)
  writeOut(col, wp, 1.0);
}`;
