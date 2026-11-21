// forked from sfo3d@e3218d6 js/shaders/objects.js
// Generic object shader (buildings, jet bridges, vehicles, props) with optional instancing
import { defineChunk } from '../gl.js';
import * as GROUND_SHADER from './ground.js';   // APRON_FLOOD (level, tint) of the ground's apron night flood (namespace import:
                                                // the object flood falls back to its own copy if the export changes)

// Object apron flood (fix round 2, review_visual_fix1.md N3) [inf]: at night the ground's apron flood (js/shaders/ground.js
// shaApronFlood, APRON_FLOOD x albedo) lit the apron and its paint, but aircraft, GSE and bridges standing on it stayed
// navy-black silhouettes; photo 19 shows lit fuselages and wings. shaObjFlood adds the same warm flood to an object surface
// that stands over apron (airfield map R paved and G 255, sampled ~4 m in front of the surface, ~4 m mip footprint) below
// OBJ_FLOOD.h m above the ground (the masts are 30 m: js/live/gate_system.js placeMasts), full on up-facing surfaces and half
// on vertical / down-facing ones (lamps above, bounce from the lit apron): alb x tint x level x (0.5 + 0.5 max(N.y, 0)).
// When the markings package's apron light map is bound (uObjLightOn = 1: js/live/markings.js apronLightMap, ground uniforms
// uApLight / uApLightRect / uApLightOn; R = lit area incl. the airside fill + spill, G = mast pools / gScale) the object
// flood follows it exactly as the ground does (lit = max(apron, R), level x gScale x G); otherwise the apron test alone.
// The chunk is self-contained (declares its uniforms, own names); the aircraft programs include it too (aircraft.js, aircraft_real.js):
//   uAptMap, uAptRect = the ground's airfield map (js/world/ground.js uniforms); uObjLight, uObjLightRect, uObjLightOn = the
//   light map (or the airfield map with uObjLightOn 0: a sampler is always bound); uObjFlood 1 = on (0 = off, per item);
//   uFloodNight = the night factor (js/live/app.js R.extraCommon; the bridges' objG program dims uNight, not this).
const AF = GROUND_SHADER.APRON_FLOOD || { level: 0.42, tint: [1.0, 0.82, 0.6] };
export const OBJ_FLOOD = { level: AF.level, tint: AF.tint, gScale: AF.gScale || 2.5, h: [14, 24], probe: 4.0, src: 'inf: the ground apron flood (APRON_FLOOD, light map when bound) applied to objects over the lit apron below 14-24 m (masts 30 m); photo 19' };
export const OBJ_FLOOD_GLSL = `
uniform sampler2D uAptMap; uniform vec4 uAptRect; uniform float uObjFlood; uniform float uFloodNight;
uniform sampler2D uObjLight; uniform vec4 uObjLightRect; uniform float uObjLightOn;
vec3 shaObjFlood(vec3 wp, vec3 N, vec3 alb, float hAbove){
  if (uObjFlood < 0.5 || uFloodNight < 0.001) return vec3(0.0);
  float hk = 1.0 - smoothstep(${OBJ_FLOOD.h[0].toFixed(1)}, ${OBJ_FLOOD.h[1].toFixed(1)}, hAbove);
  if (hk <= 0.0) return vec3(0.0);
  vec2 p = wp.xz + N.xz * ${OBJ_FLOOD.probe.toFixed(1)};   // the ground in front of the surface
  vec2 auv = (p - uAptRect.xy) / uAptRect.zw;
  if (any(lessThan(auv, vec2(0.0))) || any(greaterThan(auv, vec2(1.0)))) return vec3(0.0);
  vec4 apt = textureLod(uAptMap, auv, 2.0);
  float apronN = smoothstep(0.35, 0.65, apt.r) * smoothstep(0.86, 0.95, apt.g);   // apron = R paved + G 255 (js/world/ground.js)
  float k = 1.0;
  if (uObjLightOn > 0.5) { vec2 L = textureLod(uObjLight, (p - uObjLightRect.xy) / max(uObjLightRect.zw, vec2(1.0)), 1.0).rg; apronN = max(apronN, L.r); k = ${(+OBJ_FLOOD.gScale).toFixed(2)} * L.g; }
  return alb * vec3(${OBJ_FLOOD.tint.map(v => (+v).toFixed(3)).join(', ')}) * ${(+OBJ_FLOOD.level).toFixed(3)} * apronN * k * hk * (0.5 + 0.5 * max(N.y, 0.0)) * uFloodNight;
}`;
defineChunk('sha_obj_flood', OBJ_FLOOD_GLSL);
export const OBJ_VS = `
#include <common>
#include <vout>
layout(location=0) in vec3 aPos; layout(location=1) in vec3 aNrm; layout(location=2) in vec2 aUV;
layout(location=3) in vec4 aCol; layout(location=4) in vec4 aExtra;
#ifdef INSTANCED
layout(location=5) in vec4 iM0; layout(location=6) in vec4 iM1; layout(location=7) in vec4 iM2; layout(location=8) in vec4 iData;
#else
uniform mat4 uModel; uniform mat4 uPrevModel;
#endif
out vec3 vWP; out vec3 vN; out vec4 vCol; out vec4 vExt; out vec3 vLP; out vec3 vLN; out vec2 vUV; out vec4 vData;
void main(){
#ifdef INSTANCED
  mat4 M = mat4(vec4(iM0.x, iM1.x, iM2.x, 0.0), vec4(iM0.y, iM1.y, iM2.y, 0.0), vec4(iM0.z, iM1.z, iM2.z, 0.0), vec4(iM0.w, iM1.w, iM2.w, 1.0));
  mat4 PM = M; vData = iData;
#else
  mat4 M = uModel; mat4 PM = uPrevModel; vData = vec4(0);
#endif
  vec4 wp = M * vec4(aPos, 1.0);
  vWP = wp.xyz; vN = normalize(mat3(M) * aNrm); vCol = aCol; vExt = aExtra; vLP = aPos; vLN = aNrm; vUV = aUV;
#ifdef INSTANCED
  if (iData.w > 0.5) vCol.rgb = mix(vCol.rgb, iData.rgb, step(0.5, aCol.a) * 0.0 + (aExtra.z > 19.5 && aExtra.z < 20.5 ? 1.0 : 0.0));
#endif
  vec4 pwp = PM * vec4(aPos, 1.0);
  emitClip(wp.xyz, pwp.xyz);
}`;

export const OBJ_FS = `
#include <common>
#include <shadow>
#include <fout>
#include <sha_obj_flood>
in vec3 vWP; in vec3 vN; in vec4 vCol; in vec4 vExt; in vec3 vLP; in vec3 vLN; in vec2 vUV; in vec4 vData;
uniform float uEmissiveBoost; uniform float uNight;
uniform float uGroundY; // sha3d: nominal ground height (frame ground_y_nominal), set by app.js in R.extraCommon (sfo3d had the literal 3.0)
float gridLine(float x, float period, float w){ float f = abs(fract(x / period + 0.5) - 0.5) * period; float fw = fwidth(x) * 0.8; return 1.0 - smoothstep(w, w + fw, f); }
// fix 1: grid-line coverage that tends to the mean line coverage (2 w / period) once a pixel spans a period (gridLine alone
// tends to 1 there, which darkened whole distant facades at night)
float gridAA(float x, float period, float w){ return mix(gridLine(x, period, w), min(1.0, 2.0 * w / period), smoothstep(0.25 * period, 0.8 * period, fwidth(x))); }
void main(){
  vec3 wp = vWP; vec3 V = uCamPos - wp; float dist = length(V); V /= dist;
  vec3 N = normalize(vN); if (!gl_FrontFacing) N = -N;
  vec3 albedo = vCol.rgb; float rough = vExt.x, metal = vExt.y; int mat = int(vExt.z + 0.5); float emis = vExt.w;
  vec3 LN = normalize(vLN);
  // wall param: u along wall, v = height
  vec2 wt = normalize(vec2(-LN.z, LN.x) + 1e-5);
  float u = dot(vLP.xz, wt), v = vLP.y;
  float ao = 1.0; float specOcc = 1.0;
  vec3 extraEmis = vec3(0);
  if (mat == 1) { // glass curtain wall
    float isWall = 1.0 - abs(LN.y);
    float mull = max(gridLine(u, 1.8, 0.035), gridLine(v, 3.9, 0.06)) * (1.0 - smoothstep(150.0, 600.0, dist) * 0.7);
    float spandrel = step(fract(v / 3.9), 0.12);
    vec3 glass = vec3(0.03, 0.042, 0.05);
    albedo = mix(glass, vec3(0.28, 0.29, 0.3), max(mull, spandrel * 0.5) * isWall);
    rough = mix(0.05, 0.4, mull); metal = mix(0.0, 0.8, mull);
    // interior hint
    float room = texture(uNoise, vec2(floor(u / 1.8) * 0.13, floor(v / 3.9) * 0.37)).r;
    albedo += vec3(0.02, 0.018, 0.015) * room * (1.0 - mull) * isWall;
    // night (fix round 1, review M3: the old 0.9 x (0.35 + 0.9 room) clipped to white; photos 07 / 12 / 13 show warm,
    // partly transparent glazing with dark frames): about 0.3 of the old level, warm tint, per-bay variation (a quarter of
    // the bays dim, a few dark), mullions and spandrels stay dark, the mullion darkening does not fade with distance [inf]
    float bay = hash12(vec2(floor(u / 1.8), floor(v / 3.9)) + vec2(17.0, 3.0));
    float bayK = bay < 0.06 ? 0.08 : bay < 0.28 ? 0.35 : 1.0;
    float mullN = max(gridAA(u, 1.8, 0.06), gridAA(v, 3.9, 0.08));
    extraEmis += vec3(1.0, 0.74, 0.46) * uNight * (0.10 + 0.22 * room) * bayK * (1.0 - mullN) * (1.0 - spandrel) * isWall;
  } else if (mat == 2) { // concrete panels
    float seam = max(gridLine(u, 3.0, 0.02), gridLine(v, 1.5, 0.02));
    albedo *= (0.9 + 0.2 * texture(uNoise, vec2(u, v) * 0.05).b) * (1.0 - 0.25 * seam);
    albedo *= 1.0 - 0.25 * smoothstep(3.0, 0.0, v) * texture(uNoise, vec2(u * 0.1, 0.5)).g; // grime at base
  } else if (mat == 3) { // parking garage facade
    float lvl = fract(v / 3.3);
    float open = step(0.28, lvl) * step(lvl, 0.9) * (1.0 - abs(LN.y));
    float col_ = gridLine(u, 9.0, 0.35);
    open *= 1.0 - col_;
    vec3 inside = vec3(0.03);
    // parked cars silhouettes
    float car = step(0.28, lvl) * step(lvl, 0.55) * step(0.35, fract(u / 2.7)) * step(texture(uNoise, vec2(floor(u / 2.7) * 0.11, floor(v / 3.3) * 0.23)).r, 0.6);
    inside = mix(inside, vec3(0.12, 0.13, 0.14) * (0.5 + texture(uNoise, vec2(floor(u / 2.7) * 0.3, 0.1)).g), car);
    albedo = mix(albedo, inside, open); rough = mix(rough, 1.0, open); specOcc = 1.0 - open;
    extraEmis += vec3(0.9, 0.95, 1.0) * uNight * open * 0.35;
  } else if (mat == 4) { // corrugated metal
    float rib = sin(u * 6.2831 / 0.25);
    N = normalize(N + (vec3(wt.x, 0, wt.y)) * rib * 0.12 * (1.0 - abs(LN.y)) * (1.0 - smoothstep(20.0, 120.0, dist)));
    albedo *= 0.95 + 0.1 * texture(uNoise, vec2(u * 0.02, v * 0.1)).b;
    albedo *= 1.0 - 0.3 * smoothstep(1.5, 0.0, v);
  } else if (mat == 5) { // flat roof
    vec2 rp = wp.xz;
    albedo *= 0.8 + 0.35 * texture(uNoise, rp * 0.01).b;
    float hv = step(0.82, texture(uNoise, floor(rp / 6.0) * 0.173).r);
    albedo = mix(albedo, min(albedo * 1.5 + 0.03, vec3(0.6)), hv * 0.6);   // fix 1 (L5): relative patches (a fixed 0.62 read as white spots on the darker roofs)
  } else if (mat == 6) { // punched windows (hotel/office)
    float isWall = 1.0 - abs(LN.y);
    vec2 cell = vec2(fract(u / 3.2), fract(v / 3.5));
    float win = step(0.18, cell.x) * step(cell.x, 0.82) * step(0.3, cell.y) * step(cell.y, 0.85) * isWall;
    win *= 1.0 - smoothstep(300.0, 1200.0, dist) * 0.6;
    albedo = mix(albedo, vec3(0.06, 0.07, 0.08), win); rough = mix(rough, 0.08, win);
    float lit = step(0.45, texture(uNoise, vec2(floor(u / 3.2) * 0.173, floor(v / 3.5) * 0.311)).g);
    extraEmis += vec3(1.0, 0.82, 0.6) * uNight * win * lit * 0.4;   // fix 1 (M3): 0.9 -> 0.4 (clipped at the night exposure) [inf]
  } else if (mat == 7) { // foliage
    float n = texture(uNoise, vLP.xz * 0.4 + vLP.y * 0.3 + vData.xy).g;
    albedo *= 0.65 + 0.7 * n; ao = 0.7 + 0.3 * smoothstep(-1.0, 1.0, vLP.y);
    N = normalize(N + (texture(uNoise, vLP.xz * 0.9 + vLP.y).rgb - 0.5) * 0.8);
  } else if (mat == 9) { // jet bridge tunnel: vertical ribs + window strip (uv: x along 0..1, y 0..1)
    float along = vUV.x * max(vData.x, 1.0); float isSide = 1.0 - abs(LN.y);
    float rib = sin(along * 6.2831 / 0.35);
    N = normalize(N + vec3(0.0, 0.0, 0.0));
    albedo *= 0.93 + 0.07 * rib * isSide;
    float strip = step(0.5, vUV.y) * step(vUV.y, 0.72) * isSide * step(0.25, fract(along / 1.4)) * (1.0 - abs(LN.x));
    albedo = mix(albedo, vec3(0.03, 0.04, 0.05), strip); rough = mix(rough, 0.08, strip);
    extraEmis += vec3(1.0, 0.85, 0.65) * uNight * strip * 0.09;   // fix 1 (M3): 0.4 of the new curtain-wall mean glow (gates.md) [inf]
    albedo *= 1.0 - 0.25 * (1.0 - smoothstep(0.0, 0.15, vUV.y)) * isSide;
  } else if (mat == 11) { // parking roof with cars
    vec2 rp = vLP.xz;
    vec2 g = vec2(rp.x / 2.7, rp.y / 5.5);
    vec2 cf = fract(g); vec2 cc = floor(g);
    float row = step(1.0, mod(cc.y, 3.0));
    float occ = step(hash12(cc + 5.3), 0.62) * row;
    float car = occ * step(0.15, cf.x) * step(cf.x, 0.85) * step(0.12, cf.y) * step(cf.y, 0.88);
    float stripe = row * step(0.95, cf.x);
    albedo = mix(albedo, vec3(0.8), stripe * 0.6);
    // US car colour mix: white, black, grey, silver, red, blue, other (linear albedo)
    float h1 = hash12(cc + 17.1);
    vec3 carCol = h1 < 0.25 ? vec3(0.72) : h1 < 0.47 ? vec3(0.025) : h1 < 0.65 ? vec3(0.14) : h1 < 0.75 ? vec3(0.42, 0.43, 0.45) : h1 < 0.85 ? vec3(0.33, 0.025, 0.02) : h1 < 0.94 ? vec3(0.02, 0.05, 0.19) : vec3(0.28, 0.22, 0.14);
    float fade = smoothstep(90.0, 450.0, dist); // far away: average colour, no aliasing noise
    albedo = mix(albedo, carCol, car * (1.0 - fade)); albedo = mix(albedo, albedo * 0.85 + vec3(0.06), fade * 0.5); rough = mix(rough, 0.3, car);
  } else if (mat == 12) { // tower cab glass (tinted, slanted)
    float mull = gridLine(atan(vLP.z, vLP.x) * 10.0, 1.0, 0.03);
    albedo = mix(vec3(0.02, 0.035, 0.04), vec3(0.3), mull); rough = mix(0.04, 0.5, mull); metal = 0.0;
    extraEmis += vec3(0.25, 0.4, 0.35) * uNight * (1.0 - mull) * 0.25;
  } else if (mat == 15) { // apron-level service facade: ribbed metal panels, roll-up doors, grime at the base
    float isWall = 1.0 - abs(LN.y); float hv = v - 3.0;
    float rib = gridLine(u, 0.6, 0.04) * (1.0 - smoothstep(40.0, 200.0, dist));
    albedo *= 1.0 - 0.12 * rib;
    float cell = floor(u / 14.0); float fu = u - cell * 14.0; float hd = fract(sin(cell * 12.9898) * 43758.5453);
    float door = step(3.5, fu) * step(fu, 8.7) * step(hv, 4.1) * step(0.35, hd) * isWall;
    float slat = 0.9 + 0.1 * sin(hv * 6.2831 / 0.14);
    albedo = mix(albedo, vec3(0.44, 0.45, 0.46) * slat, door);
    float pdoor = step(10.2, fu) * step(fu, 11.2) * step(hv, 2.2) * step(hd, 0.6) * isWall; albedo = mix(albedo, vec3(0.2, 0.22, 0.25), pdoor);
    albedo = mix(albedo, vec3(0.34, 0.35, 0.36), step(4.55, hv) * isWall);
    albedo *= 1.0 - 0.28 * smoothstep(0.7, 0.0, hv) * isWall;
    extraEmis += vec3(1.0, 0.85, 0.6) * uNight * door * step(0.8, hd) * 0.6; // a few open, lit bays at night
  } else if (mat == 16) { // tower glass ribbon with LED back-lighting ("waterfall"), lit at night
    albedo = vec3(0.03, 0.04, 0.05); rough = 0.06; metal = 0.0;
    float wave = 0.55 + 0.45 * sin(v * 0.21 - uTime * 0.9);
    extraEmis += uNight * mix(vec3(0.15, 0.45, 1.0), vec3(0.2, 0.9, 0.9), wave) * (1.4 + 0.8 * wave);
  } else if (mat == 14) { // floodlight / lamp lens: lit at night
    extraEmis += albedo * uNight * 40.0; rough = 0.1;
  } else if (mat == 17) { // canal / river bank kerb (js/world/buildings3d.js BANK). Fix round 1 (review M6): the 0.35 m kerbs
    // aliased into dotted beige outlines on the water at distance; dithered fade-out from 650 to 850 m [inf]
    if (hash12(gl_FragCoord.xy + 0.37) < smoothstep(650.0, 850.0, dist)) discard;
    albedo *= 0.9 + 0.2 * texture(uNoise, vec2(u, v) * 0.05).b;
  } else if (mat == 13) { // hangar door
    float panel = gridLine(u, 6.0, 0.08); float rib = sin(v * 6.2831 / 0.4);
    albedo *= (0.95 + 0.05 * rib) * (1.0 - 0.3 * panel);
  }
  float sh = getShadow(wp, N, dist) * cloudShadow(wp);
  // cheap ground-contact AO for buildings
  if (mat != 7) ao *= mix(0.55, 1.0, smoothstep(0.0, 4.0, wp.y - uGroundY));
  vec3 col = shadePBR(albedo, N, V, rough, metal, sh, ao, specOcc);
  col += albedo * emis * uEmissiveBoost + extraEmis;
  col += shaObjFlood(wp, N, albedo, wp.y - uGroundY) * ao;   // fix round 2 (N3): apron flood on objects over the apron [inf]
  if (mat == 7) col += albedo * uSunColor * 0.08 * max(dot(-V, uSunDir), 0.0) * sh; // translucency
  col = applyFog(col, wp);
  writeOut(col, wp, 1.0);
}`;
