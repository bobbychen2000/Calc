// Ground shader for HWD (forked from sfo3d/js/shaders/ground.js @ a967f9b). Kept: the 'vout' / 'fout' chunks (camera-
// relative clip + MRT colour / aux output, verbatim), the GROUND_VS vertex shader, the lighting model of sfo3d GROUND_FS
// (sun x NoL x cascaded shadow x cloud shadow + hemispheric sky ambient + faint pavement sheen + height fog), the dry-grass
// procedural (grassCol), the close-up detail noise. Changed: the SFO airport (s,t) grid, the 4-runway uRw layout, the
// runway marking SDF glyphs, END_ZONES / EMAS / blast pads, the SFO bakes (airfield, aux, city, far city), the urban
// procedural and the Bay shore / riprap are all gone (fork map 1.2). HWD inputs:
//   - uAptMap: the pavement map painted by js/live/airport.js in the HWD grid (js/world/grid.js): R = paved coverage of
//     taxiways / taxilanes / aprons / helipads / closed ways (anti-aliased), G = closed (abandoned / disused) pavement;
//     sharpened in the shader so that edges stay crisp when magnified (the anti-aliased coverage acts as a 1-texel SDF);
//   - the two runways analytically from the FAA NASR ends (uRw / uRwI): exact rectangles, no texture;
//   - uNaip: USDA NAIP 2024 (public domain) as the ground albedo OUTSIDE the pavement (uNaipMix = 1), mapped by an affine
//     fit of geo.js worldToUtm10 (6 mm residual); beyond the imagery it fades to its border colour. uNaipMix = 0 gives
//     the procedural dry-grass ground instead (the comparison of docs/phase2_world.md section 3).
// Paint (runway and taxiway markings) is NOT in this shader: it is decal geometry (js/live/markings.js).
import { defineChunk } from '../gl.js';

defineChunk('vout', `
uniform mat4 uPrevViewProj; uniform vec3 uPrevCamPos;
out vec4 vClip; out vec4 vPrevClip;
void emitClip(vec3 wp, vec3 prevWp){
  vClip = uViewProj * vec4(wp - uCamPos, 1.0);
  vPrevClip = uPrevViewProj * vec4(prevWp - uPrevCamPos, 1.0);
  gl_Position = vClip;
}`);
defineChunk('fout', `
in vec4 vClip; in vec4 vPrevClip;
layout(location=0) out vec4 oColor;
layout(location=1) out vec4 oAux;
void writeOut(vec3 col, vec3 wp, float alpha){
  oColor = vec4(max(col, vec3(0.0)), alpha);
  vec2 v = vClip.xy / vClip.w - vPrevClip.xy / vPrevClip.w;
  oAux = vec4(length(wp - uCamPos), v * 0.5, alpha);
}`);

export const GROUND_VS = `
#include <common>
#include <vout>
layout(location=0) in vec3 aPos; layout(location=1) in vec3 aNrm;
out vec3 vWP; out vec3 vN;
void main(){ vWP = aPos; vN = aNrm; emitClip(aPos, aPos); }`;

defineChunk('hwdground', `
// dry California annual grass (sfo3d grassCol, unchanged)
vec3 grassCol(vec2 p, float fw){
  float n1 = fbm2(p * 0.02, 4), n2 = vnoise(p * 0.25), n3 = vnoise(p * 1.7);
  vec3 dry = vec3(0.50, 0.42, 0.26), dry2 = vec3(0.40, 0.33, 0.20), green = vec3(0.26, 0.30, 0.15);
  vec3 c = mix(dry, dry2, smoothstep(0.3, 0.7, n1));
  c = mix(c, green, smoothstep(0.55, 0.8, fbm2(p * 0.006 + 3.0, 3)) * 0.7);
  float det = 1.0 - smoothstep(0.2, 1.0, fw);
  c *= 0.85 + 0.3 * mix(0.5, n2, det) ;
  c *= 0.92 + 0.16 * mix(0.5, n3, 1.0 - smoothstep(0.05, 0.3, fw));
  return c * 0.85;
}
// coverage texture value -> crisp edge: the canvas anti-aliasing makes the coverage ramp ~1 texel wide, so near the
// camera (texel larger than a pixel) it is read like a signed distance; far away (texel smaller than a pixel) the
// filtered coverage itself is the right area fraction
float crisp(float c, float texPerPx){
  float fw = max(fwidth(c), 1e-4);
  float sharp = clamp((c - 0.5) / fw + 0.5, 0.0, 1.0);
  return mix(sharp, c, smoothstep(0.6, 1.4, texPerPx));
}
`);

export const GROUND_FS = `
#include <common>
#include <shadow>
#include <fout>
#include <hwdground>
in vec3 vWP; in vec3 vN;
uniform sampler2D uAptMap; uniform vec4 uMapRect; uniform vec2 uGs; uniform vec2 uGt; uniform vec2 uMapSize;
uniform vec4 uRw[2]; uniform vec4 uRwI[2];   // runway: (origin x, z, dir x, z), (half width, length, touchdown zone a, b)
uniform sampler2D uNaip; uniform vec3 uNaipU; uniform vec3 uNaipV; uniform float uNaipMix; uniform float uNaipGain; uniform vec3 uNaipBorder;
uniform float uNight;
void main(){
  vec3 wp = vWP; vec3 V = uCamPos - wp; float dist = length(V); V /= dist;
  vec3 N = normalize(vN);
  float fw = length(fwidth(wp.xz)) * 0.7 + 0.001;
  vec4 nzA = texture(uNoise, wp.xz * (1.0 / 2300.0));
  vec4 nzB = texture(uNoise, wp.xz * (1.0 / 170.0));
  // ---- natural ground: NAIP 2024 (public domain) or procedural dry grass
  vec3 grass = grassCol(wp.xz, fw);
  vec2 nuv = vec2(dot(uNaipU, vec3(wp.xz, 1.0)), dot(uNaipV, vec3(wp.xz, 1.0)));
  float inN = step(0.0, nuv.x) * step(nuv.x, 1.0) * step(0.0, nuv.y) * step(nuv.y, 1.0);
  float edgeN = min(min(nuv.x, 1.0 - nuv.x), min(nuv.y, 1.0 - nuv.y));
  vec3 naip = inN > 0.5 ? texture(uNaip, nuv).rgb : uNaipBorder;
  // beyond the imagery: its border colour, broken up by low-frequency noise so the edge is not a straight seam
  vec3 beyond = uNaipBorder * (0.82 + 0.36 * nzA.b) * (0.9 + 0.2 * nzB.g);
  naip = mix(beyond, naip, smoothstep(0.0, 0.03, edgeN) * inN);
  vec3 albedo = mix(grass, naip * uNaipGain, uNaipMix);
  float rough = 0.95;
  // ---- pavement
  vec2 gs = vec2(dot(wp.xz, uGs), dot(wp.xz, uGt));
  vec2 muv = (gs - uMapRect.xy) / uMapRect.zw;
  vec4 m = vec4(0.0);
  if (muv.x > 0.0 && muv.x < 1.0 && muv.y > 0.0 && muv.y < 1.0) m = texture(uAptMap, muv);
  float texPerPx = length(fwidth(muv * uMapSize));
  float paved = crisp(m.r, texPerPx);
  float closed = m.g;
  float n1 = texture(uNoise, wp.xz * 0.013).b, n2 = texture(uNoise, wp.xz * 0.6).r;
  // aged asphalt (HWD aprons and taxiways read light grey on NAIP 2024; no surface survey: [inf] tone)
  vec3 asph = vec3(0.17, 0.17, 0.172) * (0.86 + 0.28 * n1) * (0.94 + 0.12 * n2);
  vec2 pc = floor(gs / vec2(31.0, 19.0)); if (ihashf(ivec2(pc), 3) < 0.10) asph *= 1.12;   // patch repairs
  asph = mix(asph, vec3(0.24, 0.23, 0.21) * (0.85 + 0.3 * n1), closed * 0.8);              // abandoned: weathered
  albedo = mix(albedo, asph, paved);
  rough = mix(rough, 0.85, paved);
  // ---- runways (FAA NASR rectangles, exact)
  for (int i = 0; i < 2; i++) {
    vec2 d = wp.xz - uRw[i].xy; float al = dot(d, uRw[i].zw); float ac = dot(d, vec2(-uRw[i].w, uRw[i].z));
    float hw = uRwI[i].x, L = uRwI[i].y;
    vec2 q = abs(vec2(al - 0.5 * L, ac)) - vec2(0.5 * L, hw);
    float dOut = length(max(q, 0.0)) + min(max(q.x, q.y), 0.0);   // signed distance to the rectangle (inside < 0)
    float fwr = max(fw * 0.6, 1e-3);
    float inR = 1.0 - smoothstep(-fwr, fwr, dOut);
    if (inR > 0.0) {
      float r1 = texture(uNoise, vec2(al * 0.0012, ac * 0.02)).b, r2 = texture(uNoise, vec2(al * 0.02, ac * 0.5)).r;
      vec3 ra = vec3(0.145, 0.146, 0.152) * (0.84 + 0.32 * r1) * (0.95 + 0.1 * r2);
      ra *= 0.96 + 0.06 * smoothstep(6.0, 16.0, abs(ac));   // traffic-darkened centre band
      // rubber deposits in the touchdown zones (from each landing threshold, uRwI.zw = along of the two thresholds)
      float t0 = al - uRwI[i].z, t1 = uRwI[i].w - al;
      float rub = max(smoothstep(60.0, 180.0, t0) * (1.0 - smoothstep(450.0, 800.0, t0)), smoothstep(60.0, 180.0, t1) * (1.0 - smoothstep(450.0, 800.0, t1)));
      rub *= (1.0 - smoothstep(4.0, 11.0, abs(ac))) * (0.55 + 0.45 * texture(uNoise, vec2(al * 0.05, ac * 1.3)).g);
      ra *= 1.0 - 0.45 * rub;
      albedo = mix(albedo, ra, inR); rough = mix(rough, 0.82, inR);
      paved = max(paved, inR);
    }
  }
  // close-up detail
  if (dist < 400.0) { float dd = texture(uNoise, wp.xz * 0.9).a * 0.6 + texture(uNoise, wp.xz * 3.7).r * 0.4; albedo *= mix(1.0, 0.85 + 0.3 * dd, 1.0 - smoothstep(100.0, 400.0, dist)); }
  float sh = getShadow(wp, N, dist) * cloudShadow(wp);
  float NoL = max(dot(N, uSunDir), 0.0);
  float up = N.y * 0.5 + 0.5;
  vec3 amb = mix(uSkyHorizon, uSkyUp, up);
  vec3 col = albedo / PI * uSunColor * NoL * sh + albedo * amb;
  vec3 H = normalize(uSunDir + V); float spec = D_GGX(max(dot(N, H), 0.0), rough) * 0.03 * NoL * sh;
  col += uSunColor * spec * (1.0 - rough) * 2.0 * paved;
  col = applyFog(col, wp);
  writeOut(col, wp, 1.0);
}`;
