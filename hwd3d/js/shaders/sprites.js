// Forked from sfo3d/js/shaders/sprites.js @ a967f9b. Kept: additive light sprites, smoke puffs. Changed: a per-sprite depth pull
// for lights on detailed aircraft (iData.y; hwd3d OD4 iteration 3, docs/phase3_models.md section 15.7) and, for the same
// sprites, a lens-centre occlusion test against the scene depth that fades the whole sprite (OD4 iteration 4, review G1,
// section 15.8). Dropped: nothing.
// Additive light sprites (instanced billboards)
export const SPRITE_VS = `
#include <common>
#include <vout>
layout(location=0) in vec3 aPos; // quad corner in [-1,1]
layout(location=5) in vec4 iM0; layout(location=6) in vec4 iM1; layout(location=7) in vec4 iM2; layout(location=8) in vec4 iData;
uniform vec2 uViewport; uniform float uFovScale; // 2*tan(fov/2)/H  (world size per pixel at distance 1)
uniform vec3 uCamRight; uniform vec3 uCamUp;
out vec2 vQ; out vec3 vCol; out float vI; out float vLens;
// OD4 iteration 4 (review G1): lens occlusion of a light on a detailed aircraft (iData.y > 0.5). The pull below keeps the glow
// disc from being cut by the airframe beside the lens, but on its own it let a light show through up to 3 m of airframe: the
// PC-12 belly beacon drew as a red disc on the wing root / fuselage side from any camera above the belly, the under-wing
// landing lamp through the wing. Now the lens decides: uSceneDepth is the near pass's opaque depth (js/renderer.js copyDepth,
// made before the blended items are drawn), and the sprite's intensity is multiplied by the share of 3 x 3 taps over the
// lamp's footprint (radius LENS_R, at 0.7 of it) whose scene depth lies behind the lens centre moved toward the camera by
// LENS_ALLOW + LENS_PER_M x distance. LENS_ALLOW = 0.09 m: the anchor sits inside the lamp body or under a flush lens - PC-12
// lamp bodies reach 22-68 mm from their anchors along the sight lines measured, the SF50 anchors lie 1-16 mm under their
// lenses - while the nearest real occluder measured is 116-122 mm in front of an anchor (the PC-12 tail bullet in front of the
// top beacon seen from behind; out/pc12_look_it4/tools/light_hits.mjs) [inf]; LENS_PER_M = 0.0008 (about one pixel of a
// surface at 45 deg at fov 40 deg / 1080 lines, plus the depth resolution at airport range) [inf]; LENS_R = 0.04 m (lamp
// radius, as measured) [inf]. The whole disc fades with the lens: it is not cut by the adjacent airframe (the pull still
// applies to its fragments), and a lamp half behind an edge reads half bright. uOcclude 0 (no copy this frame) = no test.
uniform sampler2D uSceneDepth; uniform float uOcclude;
const float LENS_ALLOW = 0.09, LENS_PER_M = 0.0008, LENS_R = 0.04;
float lensVisible(vec3 p, vec3 toCam, float d){
  vec4 cp = uViewProj * vec4(p - uCamPos, 1.0);
  vec4 cq = uViewProj * vec4(p + toCam * min(LENS_ALLOW + LENS_PER_M * d, d * 0.5) - uCamPos, 1.0);
  if (cp.w <= 0.0 || cq.w <= 0.0) return 1.0;
  float zq = cq.z / cq.w * 0.5 + 0.5;                       // window depth of the moved lens centre (depth range 0..1)
  ivec2 sz = textureSize(uSceneDepth, 0);
  vec2 px = (cp.xy / cp.w * 0.5 + 0.5) * vec2(sz);
  float r = clamp(0.7 * LENS_R / max(d * uFovScale, 1e-6), 0.0, 8.0);   // tap spacing in pixels
  float v = 0.0;
  for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) {
    ivec2 q = ivec2(floor(px + vec2(float(i), float(j)) * r));
    if (q.x < 0 || q.y < 0 || q.x >= sz.x || q.y >= sz.y) { v += 1.0; continue; }   // off screen: nothing known, visible
    v += texelFetch(uSceneDepth, q, 0).r >= zq ? 1.0 : 0.0;
  }
  return v / 9.0;
}
void main(){
  vec3 p = iM0.xyz; float size = iM0.w;
  // iData.x: a position light drawn over its lens by day (js/env/aircraft_lights.js lens: true; close-out round 5, env-6 -
  // packed by js/scene.js put() as B[o + 12] = s.lens ? 1 : 0 since close-out round 6, env_closeout.md R5.2 / R6.2):
  // a lit lens by day has no glare halo, as js/three/lights.js draws it
  vLens = iData.x;
  vec3 toCam = uCamPos - p; float d = length(toCam); toCam /= d;
  float I = iM1.w;
  if (iM2.w > 0.0) { float c = max(dot(normalize(iM2.xyz), toCam), 0.0); I *= pow(c, iM2.w) * 0.97 + 0.03 * c; }
  // minimum on-screen size: 2.2 px; conserve energy
  float pxSize = size / (d * uFovScale);
  float minPx = 2.2; float s = size;
  if (pxSize < minPx) { float k = minPx / max(pxSize, 1e-4); s *= k; I /= (k * k); }
  float glow = 1.6; s *= glow; I /= glow * glow * 0.35;
  // OD4 iteration 4 (G1, above): a hidden lens hides its whole sprite (a zero-size quad draws nothing)
  if (iData.y > 0.5 && uOcclude > 0.5) { float lv = lensVisible(p, toCam, d); I *= lv; if (lv <= 0.0) s = 0.0; }
  // iData.y (hwd3d OD4 iteration 3, review F7; js/scene.js put() packs s.pull): a light on a detailed aircraft
  // (js/aircraft/detailed.js lightSprites) is pulled toward the camera by 3 m or its drawn radius s if larger (at most half
  // the distance), so the glow disc is not cut by the airframe next to the lens - the dusk still showed the tail-strobe disc
  // cut by the fin and the wing edge running through a tip disc, both within ~2 m of the lens; 3 m is about the depth of the
  // airframe around an extremity light (tip, tail) [inf]. An occluder farther from the lens (the fuselage in front of the far
  // wing tip: 5.9 m on the SF50, 8 m on the PC-12) still hides it. Every other sprite (airfield lights, placeholders) keeps
  // the sfo3d pull min(2 m, 5 % of the distance).
  // (the pulled disc keeps its angular size: s x (d - pull) / d)
  float pull = max(min(2.0, d * 0.05), iData.y > 0.5 ? min(max(s, 3.0), d * 0.5) : 0.0);
  if (iData.y > 0.5) s *= (d - pull) / d;
  vec3 wp = p + (uCamRight * aPos.x + uCamUp * aPos.y) * s + toCam * pull;
  vQ = aPos.xy; vCol = iM1.rgb; vI = I;
  emitClip(wp, wp);
}`;
export const SPRITE_FS = `
#include <common>
in vec4 vClip; in vec4 vPrevClip;
in vec2 vQ; in vec3 vCol; in float vI; in float vLens;
layout(location=0) out vec4 oColor; layout(location=1) out vec4 oAux;
void main(){
  float r2 = dot(vQ, vQ); if (r2 > 1.0) discard;
  float core = exp(-r2 * 22.0); float halo = exp(-r2 * 6.0) * 0.08 * (1.0 - step(0.5, vLens));
  vec3 c = vCol * vI * (core + halo);
  oColor = vec4(c, 0.0); oAux = vec4(0.0);
}`;

// Lit smoke puffs (alpha blended billboards)
export const SMOKE_VS = `
#include <common>
#include <vout>
layout(location=0) in vec3 aPos;
layout(location=5) in vec4 iM0; layout(location=6) in vec4 iM1; layout(location=7) in vec4 iM2; layout(location=8) in vec4 iData;
uniform vec3 uCamRight; uniform vec3 uCamUp;
out vec2 vQ; out float vA; out float vSeed; out vec3 vWP;
void main(){
  vec3 p = iM0.xyz; float s = iM0.w;
  float ang = iM1.y * 6.283; mat2 R = mat2(cos(ang), sin(ang), -sin(ang), cos(ang));
  vec2 q = R * aPos.xy;
  vec3 wp = p + (uCamRight * q.x + uCamUp * q.y) * s;
  vQ = aPos.xy; vA = iM1.x; vSeed = iM1.y; vWP = wp;
  emitClip(wp, wp);
}`;
export const SMOKE_FS = `
#include <common>
in vec4 vClip; in vec4 vPrevClip;
in vec2 vQ; in float vA; in float vSeed; in vec3 vWP;
layout(location=0) out vec4 oColor; layout(location=1) out vec4 oAux;
void main(){
  float r = length(vQ); if (r > 1.0) discard;
  float n = texture(uNoise, vQ * 0.35 + vSeed * 7.3).b * 0.6 + texture(uNoise, vQ * 0.9 + vSeed * 3.1).g * 0.4;
  float a = smoothstep(1.0, 0.25, r + (n - 0.5) * 0.6) * vA;
  vec3 V = normalize(uCamPos - vWP); float mu = dot(-V, uSunDir);
  float phase = 0.6 + 0.8 * pow(max(mu, 0.0), 4.0);
  vec3 col = (uSkyUp * 1.1 + uSunColor * max(uSunDir.y, 0.1) * 0.35 * phase) * 0.8;
  col = applyFog(col, vWP);
  oColor = vec4(col, a);
  oAux = vec4(length(vWP - uCamPos), 0.0, 0.0, a);
}`;
