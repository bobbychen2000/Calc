// Forked from sfo3d/js/shaders/sprites.js @ a967f9b. Kept: additive light sprites, smoke puffs. Changed: a per-sprite depth pull
// for lights on detailed aircraft (iData.y; hwd3d OD4 iteration 3, docs/phase3_models.md section 15.7) and, for the same
// sprites, an occlusion test of the lamp against the scene depth that fades the whole sprite (OD4 iteration 4, review G1,
// section 15.8: lens centre + fixed allowance; iteration 5, review F1 / F3, section 15.9: the lamp's own shape, per-pixel
// tolerance; instance attributes iL0..iL3 at locations 9-12; iteration 6, recheck R1 / R2, section 15.10: below ~2 px the
// lamp's self-visibility table (js/aircraft/glb.js lampTables, uLampVis) x a test of the occluders outside the aircraft's
// bounding sphere, instance attributes iL4 / iL5 at locations 13-14; round 2, recheck F2, section 15.11: other occluders are
// depth more than the aircraft's reach (table channel A) in front of the lamp, the bounding sphere only beyond the reach's
// radius). Dropped: nothing.
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
// OD4 iteration 6 (recheck of iteration 5, R1 / R2; docs/phase3_models.md 15.10). Beyond ~60 m a lamp is smaller than a
// pixel and the depth copy holds ONE sample per pixel, taken up to half a pixel from the lamp: the iteration-5 taps of a
// sub-pixel lamp all read the one or two texels next to it. A lamp at its own body's silhouette (the PC-12 belly beacon from
// just below the horizon: the belly beside it lies 0.3 m in front of it at a grazing angle, the row above is background)
// read as hidden at some sub-pixel positions and seen at others, so a light on a moving aircraft blinked (3-13 % of positions
// at 80-300 m); a lamp under 5-10 cm of winglet skin was drawn once the half-pixel allowance outgrew the skin (beyond ~100 m).
// One sample per pixel cannot tell those apart. The airframe that hides a lamp is the aircraft itself, so each lamp now
// carries a SELF-VISIBILITY TABLE computed once per model by ray casting the model at rest (js/aircraft/glb.js lampTables:
// the seen share of the lamp's projected area by view direction in the lamp shape's frame, gear down / gear up; js/scene.js
// keeps the tables in the RGBA8 atlas uLampVis, band iL5.x (< 0: none), gear-up share iL5.y). The test is then
//   v = mix(max(v5 x g(T), T x g(T) x vExt x n(T) x qn), T x g(T) x vExt, w),   w = qn x (1 - smoothstep(LENS_R1, LENS_R2, r)),
//   g(T) = mix(1, smoothstep(LENS_G0, LENS_G1, T), qn),   n(T) = smoothstep(LENS_N0, LENS_N1, T),   qn: below
// r = the smaller projected half extent of the ellipsoid of the lamp's half extents h, in pixels (for a box lamp, its
// inscribed ellipsoid: the box's own projected support over-states a flat SF50 lamp patch by up to sqrt 3); T = the table
// (bilinear) for the direction to the camera; v5 = the
// iteration-5 depth test below (a resolved lamp: it also sees the flaps, gear legs and doors as posed, and every other
// occluder); g vetoes v5 where the table says the lamp is hidden beyond the table's ~4 deg smoothing (the skin around a flush
// SF50 lens lies inside the lamp's volume, which v5 counts as the lamp); vExt = the share of 3 x 3 taps (over the lamp's
// extent, at least LENS_QMIN px apart) whose depth lies IN FRONT OF THE AIRCRAFT'S BOUNDING SPHERE (iL4: world centre,
// radius) - the occluders that are not the aircraft (buildings, other aircraft); the aircraft itself never counts there
// (round 2: in front of the aircraft's reach for the direction instead, below).
// A sub-pixel lamp's answer then depends on its view direction only, not on where it falls inside its pixel. Above LENS_R2
// px (w = 0: a near lamp, 3-17 px across) v5 alone still blinked where a few taps straddle a lamp's own rim (SF50 strobes and
// landing lights at 5-20 m), so the near term is max(v5 x g, T x g x vExt x smoothstep(LENS_N0, LENS_N1, T)): never below the
// table where the table clearly sees the lamp (T >= 0.5), unchanged where the table is near its edge (T < 0.25), so a hidden
// lamp is not drawn more often than by v5. Constants [inf: chosen with the CPU replica out/od4_it6/tools/lens6.mjs it6Test
// over 300 directions x 16 sub-pixel positions x 5-300 m, both types]: LENS_R1 1.5, LENS_R2 3 px, LENS_G0 0.04, LENS_G1 0.2,
// LENS_QMIN 0.5 px, LENS_N0 0.25, LENS_N1 0.5. The table is a view from afar: a camera nearer to the lamp than an occluder
// of that direction (5-20 m from a wing-tip lamp, between it and the fuselage or the tail) sees past it, where the table says
// hidden. Its third channel holds the distance from the lamp to the farthest such occluder of the cell (0.1 m units), and
// qn = smoothstep(f, f + LENS_TF, distance to the camera) takes the table out where qn < 1 (w, the veto g and the floor n are
// scaled by qn): that close the lamp is several pixels across and the depth test v5 alone is right. LENS_TF 0.5 m [inf].
// OD4 iteration 6, round 2 (recheck F2; docs/phase3_models.md 15.11): vExt counted only depth in front of the aircraft's
// bounding sphere (11.6 m radius on the PC-12, 8.2 m on the SF50), so another aircraft's wing, a hangar wall or a door jamb
// 1-3 m in front of a lamp never hid a sub-pixel lamp (and through the near floor, a near one). The table's fourth channel
// now holds the aircraft's REACH in front of the lamp for the direction (js/aircraft/glb.js LAMPVIS: an upper bound of how
// far in front of the lamp any surface of this aircraft at rest lies within LAMPVIS.RHO of the line of sight), and a tap's
// depth counts as another object's when it lies more than reach + LENS_XM in front of the plane through the lamp normal to
// the line of sight (LENS_XM 0.3 m >= LAMPVIS.RMIN, the lamp housing left out of the reach, + posed movers near rest [inf]).
// The reach holds for depth samples within LENS_RHO (= LAMPVIS.RHO, 0.5 m) of the line of sight: a tap's texel lies within
// its offset + LENS_TXL px; a tap beyond (fov 45 deg / 1080 lines: beyond ~460 m) falls back to the bounding sphere.
// Limit: an occluder that lies within reach + LENS_XM in front of the lamp is still not seen while the lamp is sub-pixel (the
// reach is a conservative bound: 0.3-0.5 m beyond the aircraft's true reach in most directions, metres where the aircraft
// itself runs along the line of sight - the PC-12 taxi light from ahead, 2.7 m; docs/phase3_models.md 15.11).
layout(location=13) in vec4 iL4; layout(location=14) in vec4 iL5;
uniform sampler2D uLampVis; uniform float uLampVisNE;
const float LENS_R1 = 1.5, LENS_R2 = 3.0, LENS_G0 = 0.04, LENS_G1 = 0.2, LENS_QMIN = 0.5;
const float LENS_N0 = 0.25, LENS_N1 = 0.5, LENS_TF = 0.5;
const float LENS_XM = 0.3, LENS_RHO = 0.5, LENS_TXL = 0.7072;
vec3 nz3(vec3 v){ return vec3(v.x >= 0.0 ? max(v.x, 1e-6) : min(v.x, -1e-6), v.y >= 0.0 ? max(v.y, 1e-6) : min(v.y, -1e-6), v.z >= 0.0 ? max(v.z, 1e-6) : min(v.z, -1e-6)); }
// ray (origin os, direction ds, both in the shape's frame) vs the shape of half extents h -> (t0, t1); t0 > t1 = miss
vec2 lampHit(vec3 os, vec3 ds, vec3 h, float box){
  if (box > 0.5) { vec3 inv = 1.0 / nz3(ds); vec3 ta = (-h - os) * inv, tb = (h - os) * inv; vec3 tn = min(ta, tb), tf = max(ta, tb);
    return vec2(max(max(tn.x, tn.y), tn.z), min(min(tf.x, tf.y), tf.z)); }
  vec3 o = os / h, e = ds / h; float a = dot(e, e), b = dot(o, e), c = dot(o, o) - 1.0, D = b * b - a * c;
  if (D < 0.0) return vec2(1.0, 0.0);
  float sq = sqrt(D); return vec2((-b - sq) / a, (-b + sq) / a);
}
// the self-visibility table (iteration 6): dl = the unit direction lamp -> camera in the lamp shape's frame; columns =
// azimuth atan(dl.z, dl.x) (the atlas wraps them: REPEAT), rows = elevation asin(dl.y) inside band "band" (clamped to its
// first / last row centre, so the bilinear filter never reads the next band); R = gear down, G = gear up, B = the farthest
// occluder of the direction (x 25.5 m), A = the aircraft's reach in front of the lamp (x 25.5 m) -> (seen share, farthest
// occluder in m, reach in m)
vec3 lampTable(vec3 dl, float band, float gearUp){
  float NE = uLampVisNE, H = float(textureSize(uLampVis, 0).y);
  float u = atan(dl.z, dl.x) * 0.15915494309;
  float y = clamp((asin(clamp(dl.y, -1.0, 1.0)) * 0.31830988618 + 0.5) * NE, 0.5, NE - 0.5);
  vec4 t = textureLod(uLampVis, vec2(u, (band * NE + y) / H), 0.0);
  return vec3(mix(t.r, t.g, gearUp), t.b * 25.5, t.a * 25.5);
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
  float fp = dc * uFovScale;                                 // pixel footprint at the lamp (m)
  // iteration 6: the share of the self-visibility table (sub-pixel lamps) and its veto g
  bool tab = rec && iL5.x > -0.5;
  vec3 tt = tab ? lampTable(At * (toC / dc), iL5.x, iL5.y) : vec3(1.0, 0.0, 0.0);
  float T = tt.x, qn = tab ? smoothstep(tt.y, tt.y + LENS_TF, dc) : 0.0;   // qn < 1: the camera is nearer than an occluder
  float w = qn * (1.0 - smoothstep(LENS_R1, LENS_R2, min(length(h * pr), length(h * pu)) / fp));
  float g = mix(1.0, smoothstep(LENS_G0, LENS_G1, T), qn);
  float e = LENS_E0 + LENS_KPX * fp;
  vec4 beta = uViewProj * vec4(0.0, 0.0, 0.0, 1.0); vec3 os = At * (uCamPos - c);
  float v5 = 0.0;
  if (w < 1.0) {   // iteration 5: the lamp-shape taps against the depth (comment above)
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
    v5 = (den > 0.0 ? num / den : 1.0) * g;
  }
  if (!tab) return v5;
  // iteration 6: the table x the share of taps not hidden by an occluder that is not this aircraft: depth more than the
  // aircraft's reach (round 2, F2) + LENS_XM in front of the lamp, or in front of the aircraft's bounding sphere
  float vt = T * g, vx = 1.0;
  if (vt > 0.0 && iL4.w > 0.0) {
    float qR = max(LENS_TAP * sR, LENS_QMIN * fp), qU = max(LENS_TAP * sU, LENS_QMIN * fp), num = 0.0, den = 0.0;
    vec3 oc = uCamPos - iL4.xyz; float cB = dot(oc, oc) - iL4.w * iL4.w;
    vec3 nc = (c - uCamPos) / dc; float rx = tt.z + LENS_XM;
    for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) {
      vec3 q = c + uCamRight * (float(i) * qR) + uCamUp * (float(j) * qU);
      vec4 cq = uViewProj * vec4(q - uCamPos, 1.0); if (cq.w <= 0.0) continue;
      ivec2 Q = ivec2(floor((cq.xy / cq.w * 0.5 + 0.5) * vec2(sz)));
      if (Q.x < 0 || Q.y < 0 || Q.x >= sz.x || Q.y >= sz.y) continue;
      vec3 dir = normalize(q - uCamPos);
      float b = dot(oc, dir), D = b * b - cB, tb = D > 0.0 ? max(0.0, -b - sqrt(D)) : dc;   // entry into the bounding sphere
      // where the tap ray lies reach + LENS_XM in front of the lamp's plane; valid while its texel is within LENS_RHO of the
      // line of sight (the reach's cylinder)
      float tR = (dc - rx) / max(dot(dir, nc), 1e-3), off = length(vec2(float(i) * qR, float(j) * qU)) + LENS_TXL * fp;
      float tc = mix(tb, max(tb, tR), 1.0 - smoothstep(0.8 * LENS_RHO, LENS_RHO, off));
      float zs = texelFetch(uSceneDepth, Q, 0).r;
      vec4 al = uViewProj * vec4(dir, 0.0);
      float ts = 1e30;
      if (zs < 1.0) { float nd = 2.0 * zs - 1.0; ts = (beta.z - nd * beta.w) / (nd * al.w - al.z); }
      float w0 = tc * al.w + beta.w, dzdt = 0.5 * abs(al.z * beta.w - beta.z * al.w) / max(w0 * w0, 1e-12);
      den += 1.0; if (!(ts < tc - LENS_E0 - LENS_ZEPS / max(dzdt, 1e-12))) num += 1.0;
    }
    vx = den > 0.0 ? num / den : 1.0;
  }
  return mix(max(v5, vt * vx * smoothstep(LENS_N0, LENS_N1, T) * qn), vt * vx, w);
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
