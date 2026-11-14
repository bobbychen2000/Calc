// Forked from sfo3d/js/shaders/sprites.js @ a967f9b. Kept: additive light sprites, smoke puffs. Changed: a per-sprite depth pull
// for lights on detailed aircraft (iData.y; hwd3d OD4 iteration 3, docs/phase3_models.md section 15.7). Dropped: nothing.
// Additive light sprites (instanced billboards)
export const SPRITE_VS = `
#include <common>
#include <vout>
layout(location=0) in vec3 aPos; // quad corner in [-1,1]
layout(location=5) in vec4 iM0; layout(location=6) in vec4 iM1; layout(location=7) in vec4 iM2; layout(location=8) in vec4 iData;
uniform vec2 uViewport; uniform float uFovScale; // 2*tan(fov/2)/H  (world size per pixel at distance 1)
uniform vec3 uCamRight; uniform vec3 uCamUp;
out vec2 vQ; out vec3 vCol; out float vI; out float vLens;
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
