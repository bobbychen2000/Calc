// Forked from sfo3d/js/shaders/sprites.js @ a967f9b. Kept: additive light sprites, smoke puffs. Changed: a per-sprite depth pull
// for lights on detailed aircraft (iData.y; hwd3d OD4 iteration 3, docs/phase3_models.md section 15.7) and, for the same
// sprites, an occlusion test of the lamp against the scene depth that fades the whole sprite (OD4 iteration 4, review G1,
// section 15.8: lens centre + fixed allowance; iteration 5, review F1 / F3, section 15.9: the lamp's own shape, per-pixel
// tolerance; instance attributes iL0..iL3 at locations 9-12). Dropped: nothing.
// Additive light sprites (instanced billboards)
export const SPRITE_VS = `
#include <common>
#include <vout>
layout(location=0) in vec3 aPos; // quad corner in [-1,1]
layout(location=5) in vec4 iM0; layout(location=6) in vec4 iM1; layout(location=7) in vec4 iM2; layout(location=8) in vec4 iData;
uniform vec2 uViewport; uniform float uFovScale; // 2*tan(fov/2)/H  (world size per pixel at distance 1)
uniform vec3 uCamRight; uniform vec3 uCamUp;
out vec2 vQ; out vec3 vCol; out float vI; out float vLens;
// OD4 iteration 5 (review F1 / F3; docs/phase3_models.md 15.9): lens occlusion of a light on a detailed aircraft (iData.y
// > 0.5). Iteration 4 moved the lens centre 0.09 m + 0.0008 m per metre toward the camera and counted a 3 x 3 tap visible
// when the scene depth lay behind that point: a tap past an occluder's silhouette onto the background, or onto the skin
// next to the lamp within the 9 cm, counted as visible, and one tap of nine drew the disc - a hidden lamp within ~2.8 cm of
// a silhouette, or under less than 9.8 cm of winglet / tip skin, was drawn (PC-12 tip strobes behind the wing, the top
// beacon behind the stabilizer, the belly beacon behind the belly fairing; SF50 tip strobes from the dusk camera). Now each
// light carries its LAMP SHAPE (js/aircraft/glb.js lampShape, world-placed by js/aircraft/detailed.js lightSprites, packed
// by js/scene.js put(): iL0..iL3, iData.z / w): an ellipsoid or box (centre, two unit axes, half extents) fitted to the
// lamp's own vertices, whether its surface is in the scene depth (geom), and for a one-sided lamp patch its facing cone.
// 3 x 3 taps over the shape's projected extent (+-LENS_TAP of its half extents along the camera right / up); each tap ray
// (camera -> tap point) is cut by the shape -> [t0, t1]; the scene depth at the tap's pixel -> the distance ts along the
// ray. ts < t0 - E: an occluder in front of the lamp (counts, not seen); t0 - E <= ts <= t1 + E: the first surface lies in
// the lamp's own volume - the lamp, or the skin it is flush with (seen); ts > t1 + E: the ray passes the lamp's volume
// without meeting it (a tap beside the lamp or past a silhouette onto the background) - not counted for a lamp whose surface
// is in the depth (geom), seen for one that is not (a clear lens cover / a registry anchor: nothing in front of it).
// Visibility = seen / counted (1 when nothing counted: a lamp too small for the depth buffer to hold, or off screen).
// E = LENS_E0 + LENS_KPX x (the pixel footprint at the lamp, d x uFovScale - per pixel, so a narrow field of view keeps it
// tight) + the depth buffer's resolution at that distance (LENS_ZEPS window-depth units / (dz/dt)). LENS_TAP 0.55,
// LENS_E0 2 mm, LENS_KPX 0.5 [inf: chosen with a CPU replica of this test over 600 view directions per light at 10 and 40
// m, fov 30 deg / 720 lines, against the share of each lamp's projected area that ray casting sees, out/od4_it5/tools/
// grid_lens.mjs; docs/phase3_models.md 15.9]; LENS_ZEPS 1.8e-7 (three float32 steps of a window depth just below 1).
// A one-sided lamp patch seen from where none of it faces the camera (dot(toCam, n) <= iL3.w) is hidden outright: from
// behind, the far skin of a thin tip can lie inside the lamp's volume (the SF50's upturn). The whole disc fades with the
// visible share (the pull still applies to its fragments). uOcclude 0 (no depth copy this frame) = no test.
layout(location=9) in vec4 iL0; layout(location=10) in vec4 iL1; layout(location=11) in vec4 iL2; layout(location=12) in vec4 iL3;
uniform sampler2D uSceneDepth; uniform float uOcclude;
const float LENS_TAP = 0.55, LENS_E0 = 0.002, LENS_KPX = 0.5, LENS_ZEPS = 1.8e-7, LENS_R0 = 0.03;
vec3 nz3(vec3 v){ return vec3(v.x >= 0.0 ? max(v.x, 1e-6) : min(v.x, -1e-6), v.y >= 0.0 ? max(v.y, 1e-6) : min(v.y, -1e-6), v.z >= 0.0 ? max(v.z, 1e-6) : min(v.z, -1e-6)); }
// ray (origin os, direction ds, both in the shape's frame) vs the shape of half extents h -> (t0, t1); t0 > t1 = miss
vec2 lampHit(vec3 os, vec3 ds, vec3 h, float box){
  if (box > 0.5) { vec3 inv = 1.0 / nz3(ds); vec3 ta = (-h - os) * inv, tb = (h - os) * inv; vec3 tn = min(ta, tb), tf = max(ta, tb);
    return vec2(max(max(tn.x, tn.y), tn.z), min(min(tf.x, tf.y), tf.z)); }
  vec3 o = os / h, e = ds / h; float a = dot(e, e), b = dot(o, e), c = dot(o, o) - 1.0, D = b * b - a * c;
  if (D < 0.0) return vec2(1.0, 0.0);
  float sq = sqrt(D); return vec2((-b - sq) / a, (-b + sq) / a);
}
float lensVisible(vec3 p){
  bool rec = iData.z > 0.5;                                  // a lamp record (every light of a detailed aircraft has one)
  vec3 c = rec ? iL0.xyz : p, h = rec ? vec3(iL0.w, iL1.w, iL2.w) : vec3(LENS_R0);
  vec3 a0 = rec ? iL1.xyz : vec3(1.0, 0.0, 0.0), a1 = rec ? iL2.xyz : vec3(0.0, 1.0, 0.0);
  mat3 A = mat3(a0, a1, cross(a0, a1)); mat3 At = transpose(A);
  float box = iData.z > 1.5 ? 1.0 : 0.0, geom = rec ? iData.w : 0.0;
  vec3 toC = uCamPos - c; float dc = max(length(toC), 1e-4);
  if (rec && iL3.w > -1.5 && dot(toC / dc, iL3.xyz) <= iL3.w) return 0.0;   // a one-sided lamp seen from behind
  vec4 cc = uViewProj * vec4(c - uCamPos, 1.0); if (cc.w <= 0.0) return 1.0;
  ivec2 sz = textureSize(uSceneDepth, 0);
  vec3 pr = At * uCamRight, pu = At * uCamUp;
  float sR = box > 0.5 ? dot(h, abs(pr)) : length(h * pr), sU = box > 0.5 ? dot(h, abs(pu)) : length(h * pu);
  float e = LENS_E0 + LENS_KPX * dc * uFovScale;
  vec4 beta = uViewProj * vec4(0.0, 0.0, 0.0, 1.0); vec3 os = At * (uCamPos - c);
  float num = 0.0, den = 0.0;
  for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) {
    vec3 q = c + uCamRight * (float(i) * LENS_TAP * sR) + uCamUp * (float(j) * LENS_TAP * sU);
    vec4 cq = uViewProj * vec4(q - uCamPos, 1.0); if (cq.w <= 0.0) continue;
    ivec2 Q = ivec2(floor((cq.xy / cq.w * 0.5 + 0.5) * vec2(sz)));
    if (Q.x < 0 || Q.y < 0 || Q.x >= sz.x || Q.y >= sz.y) continue;              // off screen: nothing known
    vec3 dir = normalize(q - uCamPos);
    vec2 iv = lampHit(os, At * dir, h, box); if (iv.x > iv.y) continue;
    float zs = texelFetch(uSceneDepth, Q, 0).r;
    vec4 al = uViewProj * vec4(dir, 0.0);
    float ts = 1e30;                                         // depth 1 = nothing drawn in the near range: background
    if (zs < 1.0) { float nd = 2.0 * zs - 1.0; ts = (beta.z - nd * beta.w) / (nd * al.w - al.z); }
    float w0 = max(iv.x, 0.0) * al.w + beta.w, dzdt = 0.5 * abs(al.z * beta.w - beta.z * al.w) / max(w0 * w0, 1e-12);
    float E = e + LENS_ZEPS / max(dzdt, 1e-12);
    if (ts < iv.x - E) den += 1.0;                           // an occluder in front of the lamp
    else if (ts <= iv.y + E || geom < 0.5) { num += 1.0; den += 1.0; }   // the lamp's own volume (or nothing in front of it)
  }
  return den > 0.0 ? num / den : 1.0;
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
  if (iData.y > 0.5 && uOcclude > 0.5) { float lv = lensVisible(p); I *= lv; if (lv <= 0.0) s = 0.0; }
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
