// ------------------------------------------------------------------
// GLSL programs
// ------------------------------------------------------------------
const SH = {};
// QA r3 (integration): material flag, added to a material's layer (e.g. `l: LAYER.none + SHEEN`): a grazing sheen lobe
// for satin leatherette (mainFS). The layer byte keeps the detail layer in its low 7 bits (layers < 128)
const SHEEN = 128;

SH.mainVS = `
precision highp float;
in vec3 a_pos; in vec3 a_nrm; in vec2 a_uv; in vec4 a_col; in vec4 a_mat;
in vec4 a_i0; in vec4 a_i1; in vec4 a_i2; in vec4 a_i3; in vec4 a_tint;
uniform mat4 u_viewProj;
out vec3 v_wpos; out vec3 v_nrm; out vec2 v_uv; out vec4 v_col; out vec4 v_mat; flat out vec4 v_tint;
void main(){
  mat4 m = mat4(a_i0, a_i1, a_i2, a_i3);
  vec4 wp = m * vec4(a_pos, 1.0);
  v_wpos = wp.xyz;
  v_nrm = mat3(m) * a_nrm;
  v_uv = a_uv; v_col = a_col; v_mat = a_mat; v_tint = a_tint;
  gl_Position = u_viewProj * wp;
}`;

SH.mainFS = `
precision highp float;
precision highp sampler3D;
precision highp sampler2DShadow;
precision mediump sampler2DArray;
in vec3 v_wpos; in vec3 v_nrm; in vec2 v_uv; in vec4 v_col; in vec4 v_mat; flat in vec4 v_tint;
uniform vec3 u_camPos;
uniform vec3 u_sunDir; uniform vec3 u_sunCol;
uniform mat4 u_shadowMat; uniform sampler2DShadow u_shadow; uniform vec2 u_shadowTexel;
uniform vec3 u_hemiTop; uniform vec3 u_hemiBot; uniform vec3 u_wash; uniform vec3 u_led; uniform vec3 u_sideLed; uniform vec3 u_winGlow;
uniform vec3 u_vault; uniform vec3 u_lowTint; uniform float u_bandCut; uniform float u_sideLow; uniform vec3 u_sideWall; uniform vec3 u_extBounce; uniform vec2 u_aoTune; uniform vec3 u_fZone;
uniform float u_lowGain; uniform vec3 u_monFill; uniform float u_cove; uniform float u_toe; uniform float u_fLow; uniform float u_sLowZ;
uniform vec4 u_extPtP[2]; uniform vec3 u_extPtC[2];
uniform vec4 u_spotP[8]; uniform vec4 u_spotT[8]; uniform vec3 u_spotCol;
uniform vec4 u_stripP[8]; uniform vec4 u_stripA[8]; uniform vec3 u_stripCol;
uniform vec4 u_scrP[6]; uniform vec4 u_scrN[6]; uniform vec3 u_scrCol; uniform float u_fillLift; uniform vec3 u_lensCore; uniform vec2 u_vaultE;
uniform sampler2D u_scrMask; uniform vec4 u_scrMaskR; uniform float u_scrOff; uniform vec4 u_scrOwn; uniform float u_binLo; uniform float u_monHemi;
uniform float u_tubWash; uniform vec3 u_binLift; uniform vec3 u_hemiBotN; uniform vec3 u_washN; uniform vec2 u_tubSky; uniform float u_ctrLo; uniform float u_ctrLift;
uniform sampler2D u_sDepth; uniform vec4 u_sRes; uniform vec4 u_sProj; uniform vec3 u_sFwd; uniform vec3 u_sRight; uniform vec3 u_sUp; uniform vec4 u_ssao; uniform float u_sDither; uniform float u_sMix; uniform float u_sAng; uniform float u_sLow; uniform float u_sIn; uniform vec2 u_sEase; uniform vec2 u_sTap;
uniform sampler3D u_ao; uniform vec3 u_aoMin; uniform vec3 u_aoSize; uniform sampler2D u_contact; uniform vec4 u_contactR; uniform float u_contactK;
uniform sampler2DArray u_detail; uniform vec4 u_layer[${N_LAYERS}]; uniform sampler2DArray u_photo; uniform float u_photoOn;
uniform sampler2D u_atlas; uniform float u_screenStep; uniform float u_emisGain; uniform float u_screenGain;
uniform sampler2D u_win; uniform vec2 u_winZ;
uniform float u_R; uniform float u_yc; uniform vec2 u_winY;
uniform float u_exposure; uniform float u_exterior; uniform float u_fill; uniform float u_sheen; uniform float u_sheenTint;
uniform vec3 u_skyTop; uniform vec3 u_skyBot;
uniform float u_detailOn;
out vec4 o;

vec3 toLin(vec3 c){ return c*c*(c*0.31+0.69); }
vec3 aces(vec3 x){ return clamp((x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14), 0.0, 1.0); }
// QA r3: display encode = the sRGB OETF, the inverse of toLin (was sqrt = gamma 2.0, which returned #404040 as 56 and
// crushed every charcoal / navy / taupe by 12-15 %) [D]
vec3 toSRGB(vec3 c){ return mix(c*12.92, 1.055*pow(c, vec3(1.0/2.4)) - 0.055, step(vec3(0.0031308), c)); }
// QA r1 (light): tone after ACES in the white moods (k = u_toe 1), on luminance so hues hold: near-blacks (< ~0.03
// linear, sRGB L48) go deeper and the top end (> ~0.5) follows half an S-curve, while the mid-darks (navy fabric,
// charcoal) stay put [V: p5 / p99 / % > 235 c_27312 15 / 255 / 7.2, y_47301 28 / 254 / 9.5, c_27316 33 / 254 / 9.0
// vs q06 40 / 238 / 1.5, q16 35 / 224 / 0.2] (integration r1; the suggested full S-curve also took ~12 % off the Y
// fabric, which already read L56 vs 66, from_econ w10)
vec3 tone(vec3 c, float k){
  float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
  float t = mix(1.0 - 0.45*k, 1.0, smoothstep(0.002, 0.03, l));
  t *= 1.0 + 0.5*k*smoothstep(0.4, 0.75, l)*(l*(3.0 - 2.0*l) - 1.0);   // l -> l + w (l^2 (3 - 2l) - l)
  return c * t;
}

// QA r3: 3x3 hardware-PCF taps at 1 texel (was 4 at 0.7): softer sun-patch edges, no stair steps [V: omaat_f57 / f58]
// QA r3 (integration): taps 2 texels apart, penumbrae several cm wide [V: omaat_f57 / f58; q14 rhombus on 26B, from_py 9]
float shadowF(vec3 wp, vec3 n){
  vec3 p = (u_shadowMat * vec4(wp + n*0.028, 1.0)).xyz * 0.5 + 0.5;
  // outside the camera slice the shadow map holds no casters: no sun there (windowT only gates by window z)
  if (p.x < 0.0 || p.x > 1.0 || p.y < 0.0 || p.y > 1.0 || p.z > 1.0) return 0.0;
  float z = p.z - 0.0004;
  vec2 t = u_shadowTexel * 2.0;
  float s = 0.0;
  for (int i = -1; i <= 1; i++) for (int j = -1; j <= 1; j++) s += texture(u_shadow, vec3(p.xy + vec2(float(i), float(j))*t, z));
  return s / 9.0;
}
// window LUT rows (12_scene updateWindowLUT): left / right windows (rgb = shade transmittance, a = reveal glow), a
// zone row (r / g = |dz| / half-width to the nearest left / right pane, /4; b = 1 where the outboard bins and their
// lens stand, i.e. the seat zones) and a shade row (r / g = left / right shade transmittance / 0.92 over the whole
// +-0.30 m reveal span; QA r2)
const float WL = 0.125, WR = 0.375, WZ = 0.625, WS = 0.875;
// sun transmission through the fuselage: the ray to the sun is intersected with the skin circle and looked up in the
// window LUT (rgb = shade transmittance, 0 between windows: the skin is opaque). QA r3: the hit must also lie within
// the glass height, 15 in = +-0.19 m about the pane centre (u_winY = CAB.win yc, h/2: y 1.02, Boeing D6-58329-2 fig
// 2.5.1 [V]); without it every ray in a window's z span leaked through the wall above / below the pane as dashed sun
// stripes on the shells (q01, q14, q15)
// QA r1 (light): the pane is a rounded rectangle, 10 x 15 in with large corner radii [V: REFERENCE777.md], so the gate
// is one superellipse (exponent 4 [A]) in pane units instead of separate z / y edges, which cut the patches as hard
// rectangles / parallelograms on slanted seat backs (integration r1 low, from_py 5, from_shell 3)
vec3 windowT(vec3 wp){
  vec2 o2 = vec2(wp.x, wp.y - u_yc); vec2 d = u_sunDir.xy;
  float a = dot(d, d);
  if (a < 1e-5) return vec3(0.0);
  float b = 2.0*dot(o2, d); float c = dot(o2, o2) - u_R*u_R;
  float disc = b*b - 4.0*a*c;
  if (disc < 0.0) return vec3(0.0);
  float t = (-b + sqrt(disc)) / (2.0*a);
  float zh = wp.z + u_sunDir.z * t;
  vec2 hit = o2 + d * t;
  float zt = (zh - u_winZ.x)/(u_winZ.y - u_winZ.x);
  vec4 zr = texture(u_win, vec2(zt, WZ));
  float dzn = (hit.x < 0.0 ? zr.r : zr.g) * 4.0;
  float dyn = (hit.y + u_yc - u_winY.x) / u_winY.y;
  float q = dzn*dzn*dzn*dzn + dyn*dyn*dyn*dyn;
  // QA r3 (integration): the gate ramps over 0.75-1.3 of the superellipse radius q^(1/4) (was 0.75-1.1 of q, i.e.
  // 0.93-1.02 of the radius: a ~1 cm penumbra): on a slanted seat back the gate projected to a hard-edged sheared quad
  // [V: q14 26B back L212 on fabric L138 with straight edges vs py_37301 / 37303 no patch; omaat_f57 / f58 penumbrae
  // several cm] (from_py 5 / 6 / 9); width [D]
  return (1.0 - smoothstep(0.75, 1.3, sqrt(sqrt(q)))) * texture(u_win, vec2(zt, hit.x < 0.0 ? WL : WR)).rgb;
}
// lo = 1 for surfaces below ~1.5 m: QA r1 (light) the cool window light reaching seat level is half desaturated, it
// left a blue cast on the charcoal shells (h216-218 s0.14-0.20 vs c_27312 shell back #5c626a, dark side #4e4f55,
// s0.08-0.13) [V]
vec3 envInside(vec3 R, float lo, vec3 hBot){
  float up = smoothstep(-0.25, 0.75, R.y);
  vec3 e = mix(hBot*0.7, u_hemiTop*1.25, up);
  float side = (1.0 - abs(R.y)) * smoothstep(0.35, 0.95, abs(R.x));
  vec3 wg = mix(u_winGlow, vec3(dot(u_winGlow, vec3(0.2126, 0.7152, 0.0722))), 0.5*lo);
  e += wg * side * 0.6;
  return e;
}
// QA r1 (light): specular from the two cove LED lines along the top inner edge of the outboard bins (x +-1.70,
// y 2.238: 08_bins MAT.led), as line lights: the point on each line nearest the reflected ray, GGX at a widened
// roughness. They put the soft sheen lines on the rounded shell caps, armrests and leatherette folds of the photos
// [V: c_27312 rim highlights on the charcoal caps, tlfl_IMG_9217 streaks on the cap rails, y_47303 armrest tops p99
// 248-251, y_47306 flap fold 2.1x the face]; level [D] from those ratios
vec3 coveSpec(vec3 P, vec3 N, vec3 V, vec3 R, float rough, vec3 F0, float NdV){
  vec3 s = vec3(0.0);
  float r2 = max(rough, 0.3); float a2 = r2*r2*r2*r2;
  float k = (r2 + 1.0)*(r2 + 1.0) / 8.0;
  float rxy = max(length(R.xy), 0.05);
  for (int i = 0; i < 2; i++) {
    vec2 dxy = vec2(i == 0 ? -1.70 : 1.70, 2.238) - P.xy;
    float lxy = length(dxy);
    vec3 Lc = normalize(vec3(dxy, R.z / rxy * lxy));
    float ndl = max(dot(N, Lc), 0.0);
    if (ndl <= 0.0) continue;
    vec3 H = normalize(Lc + V);
    float NdH = max(dot(N, H), 0.0);
    float dd = NdH*NdH*(a2 - 1.0) + 1.0;
    float D = a2 / (3.14159 * dd * dd);
    vec3 F = F0 + (1.0 - F0) * pow(1.0 - max(dot(H, V), 0.0), 5.0);
    float G = 1.0 / ((ndl*(1.0 - k) + k) * (NdV*(1.0 - k) + k));
    s += D * F * G * 0.25 * ndl / max(lxy, 0.4);
  }
  return s;
}
// QA L8 (integration): small-radius screen-space AO from a depth pre-pass (12_scene render, u_sDepth): 8 taps on a disc of
// u_ssao.x m (0.05) at the fragment's depth, a golden-angle spiral (one fixed pattern; u_sDither 1 turns it per pixel by
// interleaved gradient noise, off: QA L9 below); each tap is put back in world space (u_sProj = proj[0], [5], [10], [14]; u_sFwd /
// Right / Up = camera basis) and occludes by the angle of its point over the fragment's face plane (Nf, from the position
// derivatives: the true triangle plane, so a flat face never self-occludes), less a 6 mm bias and an angle bias u_sAng
// (0.25: the facets of coarse curved lofts, e.g. the window tubs, drew dark seams at 0), faded out by the range u_ssao.w
// (L8 0.05-0.10 m; 0.15 left grey halos on a wall ~10 cm behind the PY headrests, fixL8 f2; L9 below). Returns the occluded share 0-1.
// The pre-pass is full size: at half size the snapped taps drew half-res stair steps on the bin faces (fixL8 f1). The 8 cm AO volume and the floor contact map cannot hold the cm-scale dark lines at shell edges,
// cushion-to-shell gaps, panel splits and seat bases that outline every unit in the photos [V: thin dark-line share
// q13 0.55 vs py_37302 2.77 %, q06 1.81 vs c_27312 4.77, q05 0.89 vs f_17313 2.21] (integration L8 medium) [D]
// QA L9 (integration medium): each occluder 1-10 cm in front of a surface printed stepped, offset copies of its outline
// (one tap on it took the ambient to 0.25x): beside the THE Suite bulkhead monitor L145-180 -> 54-80, a detached band above
// the THE Room headrest flap L83-103 -> 29-50, where the photos show the wall clean and a soft shade under the flap
// [V: omaat_f13 monitor surround, c_27315 flap; integ6 halo_cmp / mon_halo / q10_zoom]. A tap now counts in full up to
// u_sIn x the range (0.3 x 0.07 m = 2 cm: the contact / crease taps) and fades out by the range (7 cm), with strength 6:
// a part 5 cm off a wall counts 0.14 of a contact tap (12_scene LIGHT_TUNE.ssao / ssaoIn). Tried [D fixL9 tss-tss5]: the
// raters' (1 - dl / 0.10)^2 at strength 4 (clean, but q06 / q13 / q03 thin dark-line share 2.96 / 0.91 / 1.70 -> 1.89 /
// 0.55 / 0.63 %) and a per-pixel disc turn (interleaved gradient noise, u_sDither 1; 0.15 / 0.3 of a turn): without a
// blur pass (none: phone budget) it draws dot grain along every contact edge and on the cap rails. kR scales the disc and
// the range (QA L9, lighting low: 1.5 low in the PY / economy legroom, see mainFS)
// QA L10 (integration medium): with 8 fixed taps the coverage stepped in eighths as the disc crossed an occluder's edge, one
// tap taking the ambient to 0.25x, so a panel 1-3 cm proud of a surface drew a detached, stair-ended band (the THE Room
// headrest flap on all 64 seats: q10 x 650 rows 398-410 L49-57 vs 84-91 without it) and near the eye, where the 5 cm disc
// spans 50-100 px, each tap painted a flat band tens of px wide (y_aisle_fwd curtain pleats, row 300: 13 steps > 6 L, max
// 101 vs 9 / 53 without the AO) [V: c_27315 no band; integ8 q10_flap4x, curtain_zoom]. Now u_sTap.x = 12 taps (steps of
// 1/12; the loop takes up to 16) and the disc and range capped at u_sTap.y = 16 px on screen (a surface 0.3 m from the eye
// no longer spreads its taps over 100 px; aft of THE Room only above the seat backs, see below), strength 6 -> 8 for the
// contact lines (12_scene LIGHT_TUNE). The raters' fix (an R8 AO target with the per-pixel turn and a 4 x 4 depth-aware
// blur) adds full-screen passes, which this run's brief rules out (questions_lighting 13). Leaving every surface within
// ~0.75 m uncapped kept the q14 seat shells' shade but brought the curtain stripes back (y_aisle_fwd 19 steps, max 117)
// [D fixL10 t1-t19]
float ssaoF(vec3 P, vec3 Nf, float kR){
  float dep = dot(P - u_camPos, u_sFwd);
  vec2 ruv = u_sProj.xy * (0.5 * u_ssao.x * kR / max(dep, 0.05));
  float rng = u_ssao.w * kR;
  float px = ruv.y * u_sRes.y;                              // disc radius in pixels
  if (px < 2.0) return 0.0;                                 // far: the disc is under ~2 px
  // (QA L10) screen-space cap; aft of THE Room only above the seat backs (1.1-1.3 m): below them the PY / economy seat joints
  // keep the full disc (their contact lines are already short of the photos'; capped, the q14 seat shells lost theirs)
  float capW = max(1.0 - step(u_sLowZ, P.z), smoothstep(1.1, 1.3, P.y));
  float kc = mix(1.0, u_sTap.y > 0.0 ? min(1.0, u_sTap.y / px) : 1.0, capW);
  ruv *= kc; rng *= kc;
  vec2 uv0 = gl_FragCoord.xy / u_sRes.xy;
  float a0 = u_sDither * 6.2832 * fract(52.9829 * fract(dot(gl_FragCoord.xy, vec2(0.06711, 0.00584)))) + 0.39;
  float occB = 0.0, occX = 0.0, nT = max(u_sTap.x, 1.0);
  // (QA L10) every third tap of the spiral is an extra one, taken only where the capped disc spans more than 10-14 px; a
  // smaller disc (steps there are ~1-2 px) and the uncapped PY / economy seats keep the 8 others, so most of the cabin costs
  // what the 8-tap AO cost (12 taps everywhere: frame time +7-11 % at Sharp) [D fixL10]
  float tX = smoothstep(10.0, 14.0, px * kc) * capW;
  for (int i = 0; i < 16; i++) {
    float fi = float(i);
    if (fi >= nT) break;
    bool xt = mod(fi, 3.0) > 1.5;
    if (xt && tX <= 0.0) continue;
    float an = a0 + fi * 2.39996;
    // snapped to the depth texel's centre, where the pre-pass sampled the surface: the point is then on the surface
    // itself (a sample uv off the centre with that texel's depth leaves the plane by up to half a texel at grazing angles:
    // dotted dark crescents in the far window tubs) [D]
    vec2 uv = (floor((uv0 + vec2(cos(an), sin(an)) * sqrt((fi + 0.5) / nT) * ruv) * u_sRes.zw) + 0.5) / u_sRes.zw;
    float z = u_sProj.w / (textureLod(u_sDepth, uv, 0.0).r * 2.0 - 1.0 + u_sProj.z);
    vec2 nd = uv * 2.0 - 1.0;
    vec3 v = u_camPos + z * (u_sFwd + nd.x / u_sProj.x * u_sRight + nd.y / u_sProj.y * u_sUp) - P;
    float dl = length(v);
    float o = clamp(((dot(v, Nf) - u_ssao.z) / max(dl, 1e-3) - u_sAng) / (1.0 - u_sAng), 0.0, 1.0) * (1.0 - smoothstep(u_sIn * rng, rng, dl));
    if (xt) occX += o; else occB += o;
  }
  float nX = floor(nT / 3.0);
  return mix(occB / (nT - nX), (occB + occX) / nT, tX) * smoothstep(2.0, 4.0, px);
}

void main(){
  vec3 base = toLin(v_col.rgb) * v_tint.rgb;
  float rough = v_mat.r, metal = v_mat.g;
  int layer = int(v_mat.b * 255.0 + 0.5);
  float sheen = layer >= ${SHEEN} ? 1.0 : 0.0;   // SHEEN flag (top bit of the layer byte)
  if (layer >= ${SHEEN}) layer -= ${SHEEN};
  float emis = v_mat.a;
  vec3 N = normalize(v_nrm);
  if (!gl_FrontFacing) N = -N;
  vec3 V = normalize(u_camPos - v_wpos);
  // face-plane normal toward the eye (QA L8 ssaoF): the plane the depth pre-pass holds, free of smoothing / detail normals
  vec3 Nf = cross(dFdx(v_wpos), dFdy(v_wpos));
  Nf = dot(Nf, Nf) > 1e-24 ? normalize(Nf) : N;
  if (dot(Nf, V) < 0.0) Nf = -Nf;
  vec3 emissive = vec3(0.0);
  float hl = step(0.25, fract(v_tint.a + 0.01));
  if (layer >= 13 && layer <= 15) {
    vec2 uv = v_uv;
    if (layer == 13) uv.y += floor(v_tint.a + 0.001) * u_screenStep;
    vec3 tc = toLin(texture(u_atlas, uv).rgb);
    if (layer == 14) base *= tc;
    else {
      // QA r3: layer 15 (glowing atlas text) takes the material hue, so the THE Suite plaques glow blue-violet
      // [V: omaat_f7 / f9 '2K' lit characters]; normalised to the brightest channel so e alone sets the level
      vec3 hue = layer == 15 ? base / max(max(base.r, base.g), max(base.b, 1e-3)) : vec3(1.0);
      emissive = tc * hue * (layer == 13 ? u_screenGain : u_emisGain) * emis * 4.0; base = tc * 0.04; rough = 0.25;
      // QA r4 (light): in Night / Blue most seat screens are off (black glass): each screen's footprint holds a per-screen
      // hash (12_scene buildScreenMask, 4 cm cells); off below u_scrOff (0.7), except the screen nearest the eye that
      // faces it (u_scrOwn: centre, radius^2) [V: sany_40 economy at night < 1/3 of the seat-back screens lit, sany_47
      // blue phase ~6 of 25, ucr_room-night-lighting only the passenger's own screen]
      if (layer == 13 && u_scrOff > 0.0) {
        vec3 dw = v_wpos - u_scrOwn.xyz;
        float off = step(texture(u_scrMask, (v_wpos.xz - u_scrMaskR.xy) / u_scrMaskR.zw).r, u_scrOff - 0.002) * step(u_scrOwn.w, dot(dw, dw));
        emissive *= 1.0 - off; base = mix(base, vec3(0.012), off);
      }
    }
  } else if (layer == 12) {
    // two LED circuits [V: tlfl_IMG_9217, sany_10/12, roame_7672]: the ceiling cove (u_led) stays near-white while the
    // sidewall lens under the outboard bins (the only layer-12 part below 2 m) drives the blue sidewall band (u_sideLed)
    // QA r3: the dim vault wash (CEILMAT.vault eFn 0.04-0.3) takes its own colour u_vault, blending to the LED colour
    // at the cove (e 0.85): in the amber phase the LED line is saturated amber but the vault reads soft warm beige
    // [V: ff_door-gap lens #ffa33c, ff_seat-with-door-closed ceiling #d9b77d]; u_vault = u_led in the white moods
    // QA r2 (light): the lens core adds u_lensCore (amber moods: G / B) so the LED line clips to pale yellow, the
    // brightest thing in the frame, while its light on the wall (u_sideLed x u_sideWall) keeps the amber [V: ucr_the-room-
    // cabin lens #fefed6, ff_door-gap #fefeb6 beside the PSU band #603b1d]
    vec3 lc = u_exterior > 0.5 ? u_led : v_wpos.y < 2.0 ? u_sideLed + u_lensCore : mix(u_vault, u_led, smoothstep(0.3, 0.85, emis));
    // QA r3 (light): the dim vault / cove wash (y >= 2 m, e < 0.5) is clamped to u_vaultE per mood (floor, cap).
    // Amber floor 0.14: the THE Room vault between the bins (07b eFn 0.02-0.08) read dark brown under a pale seat level,
    // while every amber photo shows the cove-washed ceiling as the brightest warm surface [V: ucr_the-room-cabin aisle
    // ceiling #cc9957 / #cb9b53 L161 s0.58, ff_seat-with-door-closed #d6ae72 L179 vs d_room_dining #663918-#714826
    // L67-81; d06 vault L68-73 s0.80 -> L140-146 s0.65 with 12_scene's paler vault hue]; the door domes (e 0.06-0.2)
    // already matched (q21 #d09748 vs ucr #c89552) and barely move. Night cap 0.09:
    // the cove panel (07b CEILMAT.cove e 0.36) stayed the brightest surface after the screens, while the night photo's
    // ceiling is dark throughout [V: ucr_room-night-lighting ceiling L13-55, cove panel <= #3f352f vs q20 #a39a8c L155];
    // the mid-vault (e 0.02-0.08) keeps its level (q20 L28 vs ucr L21-27) [D]
    float ev = u_exterior < 0.5 && v_wpos.y >= 2.0 && emis < 0.5 ? clamp(emis, u_vaultE.x, u_vaultE.y) : emis;
    // QA r4 (light): at night (vault cap < 0.1) the cove LED lines themselves (e >= 0.5) run at half level: they read as
    // two neutral-white stripes the length of the cabin [V: ucr_room-night-lighting no lit cove line, upper band p99 58;
    // sany_25 pale-yellow line core #fef2ad vs q20 #dcdcda L220]; hue in 12_scene MOODS.sleep.led
    if (u_exterior < 0.5 && v_wpos.y >= 2.0 && u_vaultE.y < 0.1) ev = min(ev, 0.5);
    emissive = lc * ev * 6.0;
    base *= 0.3;
  } else if (layer > 0 && u_detailOn > 0.5) {
    vec4 P = u_layer[layer];
    // QA r1 (light): photo layers (>= 16) blend the three projections more sharply (exponent 10, was 4): at ~45 deg the
    // two ~50/50 projections smeared the fabric into diagonal streaks (econ back-top roll, from_econ w6) [D]
    vec3 w = pow(abs(N), vec3(layer >= 16 ? 10.0 : 4.0)); w /= (w.x + w.y + w.z);
    vec3 q = v_wpos * P.x;
    float L = float(layer);
    vec4 tx = texture(u_detail, vec3(q.zy, L));
    vec4 ty = texture(u_detail, vec3(q.xz, L));
    vec4 tz = texture(u_detail, vec3(q.xy, L));
    vec4 t = tx*w.x + ty*w.y + tz*w.z;
    vec2 nx = tx.xy*2.0 - 1.0, ny = ty.xy*2.0 - 1.0, nz = tz.xy*2.0 - 1.0;
    vec3 dn = vec3(0.0, nx.y, nx.x)*w.x + vec3(ny.x, 0.0, ny.y)*w.y + vec3(nz.x, nz.y, 0.0)*w.z;
    N = normalize(N + dn * P.y);
    if (layer < 16 || u_photoOn < 0.5) base *= 1.0 + (t.b - 0.5) * 2.0 * P.z;
    else {
      // QA r2 (integration): photo tiles sampled half a mip sharper (bias -0.5; the arrays are already 8x anisotropic):
      // the Y tick-stitch columns and the ash grain washed out at row distance [V: q15 column CV 0.06-0.08 vs y_47300
      // 0.24 (from_econ w17); THE Room ash grain 0.017-0.032 vs c_27316 0.10-0.16 (from_room w13a)]. Not on layer 16
      // (y_tick), which speckled at row distance with it (q15 bright 0.12-0.14 vs y_47300 0.083; from_econ w23)
      // QA r3 (light): beyond ~3 m the bias fades out and the tile contrast eases halfway to the tile mean (its 1x1 mip,
      // so the mean colour holds): the far economy rows read as white snow [V: q16 rows 3+ p90 / p50 2.2, bright 0.28-0.31
      // vs y_47301 1.61 / 0.13] (from_econ w27); the q15 rows (2-4 m) keep theirs [D]
      float far = smoothstep(3.0, 7.0, length(u_camPos - v_wpos));
      // QA r3 (light): layer 16 (y_tick) at -0.25: exempt, its stitch-column contrast faded at row distance, and a tile
      // that held it went near-black close up (from_econ w31; q15 back p90 / p10 vs y_47300 3.2-3.5) [D econ]
      float PL = float(layer - 16), mb = (layer == 16 ? -0.25 : -0.5) * (1.0 - far);
      vec3 c = texture(u_photo, vec3(q.zy, PL), mb).rgb*w.x + texture(u_photo, vec3(q.xz, PL), mb).rgb*w.y + texture(u_photo, vec3(q.xy, PL), mb).rgb*w.z;
      if (far > 0.0) c = mix(c, textureLod(u_photo, vec3(0.5, 0.5, PL), 8.0).rgb, 0.5 * far);
      base *= mix(vec3(1.0), c * 2.0, P.z);
    }
    rough = clamp(rough * (1.0 + (t.a - 0.5) * 2.0 * P.w), 0.04, 1.0);
  }
  // small e (< 0.2; QA r3: was < 0.12, but e is stored in 8 bits, so CEILMAT.bezel e 0.12 arrived as 31/255 = 0.1216
  // and took the lamp branch (glowing vault rings at night, q20), and BINMAT.band e 0.16 lit the PSU band white at
  // night; lamps use e >= 0.2) is a fill lift for faces the hemisphere fill under-lights (08_bins doorC / bandC), not a lamp: it
  // follows the cabin light colour and level (1 at boarding / cruise), so the dimmed moods do not leave the centre bins
  // glowing grey (QA r2 night: #a0a1a3 vs ucr_room-night-lighting bins #322a1f) [D]
  // QA r2 (light): x u_fillLift per mood (0.15 in the amber moods, 0.4 in Blue): the lift kept the PSU band glowing
  // tan in the amber phase, where the photos show it as a dark amber-brown strip beside the clipped lens [V: ff_door-gap
  // PSU band #603b1d L65, ucr_the-room-cabin #6f482a L79 vs q21 #ad7c42 L131, d06 #926532]
  if (emis > 0.0 && (layer < 12 || layer > 15))
    emissive += base * emis * 3.0 * (emis < 0.2 ? min(u_hemiTop / 0.8, vec3(1.0)) * u_fillLift : vec3(u_emisGain));
  // specular anti-aliasing: widen roughness where the normal varies across pixels
  vec3 dNdx = dFdx(N), dNdy = dFdy(N);
  float nvar = 0.25 * (dot(dNdx, dNdx) + dot(dNdy, dNdy));
  rough = sqrt(clamp(rough*rough + min(2.0*nvar, 0.25), 0.0, 1.0));
  rough = max(rough, 0.12);

  float NdV = max(dot(N, V), 1e-3);
  vec3 amb; float ao = 1.0; float sz = 1.0; vec3 lt = vec3(1.0); vec3 tubRef = vec3(0.0); vec3 hBot = u_hemiBot;
  if (u_exterior > 0.5) {
    // QA r3: the exterior sees the lit cloud deck below (u_extBounce per sky), so shaded flanks / undersides of the
    // wing, canoes and nacelle read mid-grey, not slate [V: alv_ANA77W_NH211_26K shaded flank #8090a0, belly #59636c]
    // (from_exterior 1). The studio leaves u_extBounce at 0 and keeps its plain two-colour fill
    amb = dot(u_extBounce, u_extBounce) > 0.0 ? mix(u_extBounce, u_skyTop, smoothstep(-0.6, 0.8, N.y))
                                             : mix(u_skyBot, u_skyTop, clamp(N.y*0.5 + 0.5, 0.0, 1.0));
    // exterior lights that also light the airframe (ext.lights with a 'light' gain, e.g. the belly beacon washing the
    // lower cowl at night [V: yt_p97zMaCMWRg_EVA77W_night_beacon], from_exterior 4); blink state set per frame.
    // QA r1 (light): only faces looking down take it, so the wash stays on the cowl / wing undersides and leaves the
    // canoe flanks dark (n19A read red-painted canoes; from_exterior 9)
    for (int i = 0; i < 2; i++) {
      if (u_extPtP[i].w < 0.5) continue;
      vec3 d = u_extPtP[i].xyz - v_wpos; float r2 = dot(d, d);
      amb += u_extPtC[i] * max(dot(N, d * inversesqrt(r2)), 0.0) / max(r2, 0.25) * (1.0 - smoothstep(-0.5, 0.1, N.y));
    }
  } else {
    vec3 auv = (v_wpos + N*0.07 - u_aoMin) / u_aoSize;
    ao = texture(u_ao, auv).r;
    // QA r3: THE Suite interior (z in u_fZone.xy, below the 1.3 m shell tops, away from the sidewall) sees the bright
    // open ceiling over the shells: AO eased toward 1 by u_fZone.z [V: f_17300, omaat_f2 / f5 open-topped suites;
    // omaat_f11 ottoman #9f8c85 vs q03 #312f2d]
    float inFzy = smoothstep(u_fZone.x, u_fZone.x + 0.3, v_wpos.z) * (1.0 - smoothstep(u_fZone.y - 0.3, u_fZone.y, v_wpos.z))
                * (1.0 - smoothstep(1.2, 1.5, v_wpos.y));
    float inF = inFzy * (1.0 - smoothstep(2.4, 2.75, abs(v_wpos.x)));
    ao = mix(ao, 1.0, u_fZone.z * inF);
    // QA r1 (light): ceiling and bin faces above ~1.9 m stand > 0.6 m over the seat backs and are lit by the cove
    // above, so the dense economy block may not darken them: the Y ceiling / bins read 10-15 % under the J ones and the
    // official photos [V: y_47301 ceiling #e8e8e7 vs q16 #c2c4c7; y_47300 bins #e1e1e1 vs q15 #c5c6c7; floor 0.85 D]
    // QA r2 (integration): only in the seat zones (sz, the LUT zone row): in the galleys the floor lifted the upper
    // compartments from 1.8 to 2.0 m into a white band over grey lower banks [V: sans_38 even mid-grey upper row;
    // from_monuments w9b / w13-15 m01, m09, m12, q19]
    // QA r3 (integration): floor 0.85 -> 0.72, so the bin doors keep a top-to-lip gradient instead of a flat white slab
    // [V: bin / vault 0.73-0.87 in c_27312, y_47301, sany_10 vs 1.15-1.2 in q06 / q16; bin high-pass std 16-38 vs 0.2-1.3]
    sz = texture(u_win, vec2((v_wpos.z - u_winZ.x)/(u_winZ.y - u_winZ.x), WZ)).b;
    ao = max(ao, 0.72 * smoothstep(1.8, 2.0, v_wpos.y) * sz);
    // QA r3: up-facing floor (fl) takes the AO 2.5 cm above the carpet as well, so the seat bases / monument toes
    // leave a contact line [V: c_27312 dark line along every monument base]
    float fl = step(0.7, N.y) * (1.0 - smoothstep(0.02, 0.15, v_wpos.y));
    // QA r2 (integration): aoPk = the pocket AO for the floor / underside terms below: on the carpet the larger of the
    // AO here and 0.35 m up, which stays low under a seat pan but opens up in an aisle next to a bulkhead or curtain
    // (the plain AO darkened the q13 PY aisle to < 30 vs py_37302 charcoal carpet ~L45-60) [D]
    // QA r3 (integration): on the carpet the AO is the mean of 4 taps +-0.17 m in x / z (5 cm up), so the volume's
    // cell-sized sweep wedges blur out; the 2.5 cm sample counts at half weight, and the thin line at each base comes from
    // the contact map [V: kn_room_1 aisle centre L34, shell-base edge L33; omaatJ_oj_r31 dark base line ~20 px at 1200 px,
    // edges 0.85-0.9x the centre; q06 aisle p10 20, 34 % < 30 vs c_27312 p10 41, 5.5 %]; the pocket AO takes this mean [D]
    float aoPk = ao, ctc = 0.0;
    if (fl > 0.5) {
      vec3 pb = v_wpos + vec3(0.0, 0.05, 0.0) - u_aoMin;
      float aoB = 0.25 * (texture(u_ao, (pb + vec3(0.17, 0.0, 0.0)) / u_aoSize).r + texture(u_ao, (pb - vec3(0.17, 0.0, 0.0)) / u_aoSize).r
                        + texture(u_ao, (pb + vec3(0.0, 0.0, 0.17)) / u_aoSize).r + texture(u_ao, (pb - vec3(0.0, 0.0, 0.17)) / u_aoSize).r);
      ao = min(aoB, mix(texture(u_ao, (v_wpos + N*0.025 - u_aoMin) / u_aoSize).r, 1.0, 0.5));
      aoPk = max(aoB, texture(u_ao, (v_wpos + vec3(0.0, 0.35, 0.0) - u_aoMin) / u_aoSize).r);
      // the thin dark line where a seat, shell, monument or the sidewall meets the carpet (12_scene contact map, 3 cm
      // cells; applied to amb below) [V: kn_room_1, omaatJ_oj_r31 / r37 thin base line; c_27312 monument bases]
      ctc = texture(u_contact, (v_wpos.xz - u_contactR.xy) / u_contactR.zw).r;
    }
    float up = clamp(N.y*0.5 + 0.5, 0.0, 1.0);
    float down = clamp(-N.y, 0.0, 1.0);
    // QA r4 (light): + u_binLift on the lower hemisphere above ~1.6 m in the seat zones (amber moods): the bin faces and
    // undersides seen from a seat read dark and over-saturated (dd #86582a L95 s0.69, d06 #835325 L90 s0.71) where the photos
    // show them as the bright, soft-amber layer [V: ff_seat-with-door-closed bins #b99662 L154 s0.47; ucr_the-room-cabin
    // bins from below #b3834b L138 s0.58] (lighting r4 medium). Not the whole hemiBot (the raters' fit): that lifted the
    // seat level and the door zones as well (q21 median 134 -> 142 vs ucr 86) [D]
    // QA L8 (light): the lift acts on the bin door faces only, outboard (binO, below) and centre (cBin: |x| < ~1 m above
    // 1.62-1.70 m up to the bin tops at ~2.3 m, in the seat zones), at 2x the step; the flat undersides and PSU band (N.y <
    // -0.85..-0.98) keep the r4 level (0.25 of it), which the photos show dark [V: ucr_the-room-cabin centre-bin underside
    // #7a502a L87, ff_door-gap PSU band #603b1d L65; dd undersides L89, PSU L78 at r4]: at the full lift the dd PSU band read
    // L93 (cap 85), with none dd went darker than r4 (undersides L82) [D fixL8 t2 / after] (12_scene MOODS binLift): r4's lift on the whole lower hemisphere
    // above 1.6 m stopped at 0.6 of the step because it also lifted the seat level and door zones, and moved the dd / d06
    // bins only 3-6 L [V: ucr_the-room-cabin outboard bins #9e7240 L120 s0.59, ff_seat-with-door-closed #b99662 L154 s0.47
    // vs dd #7e5227 L89 s0.69, d06 #8c5c2b L99 s0.69] (lighting L8 medium)
    // QA r4 (light): binO = the outboard bin doors (08_bins OBIN_DOOR: lip x 1.53 y 1.795, bulging to x 1.47 at 2.03, crest
    // 1.64 / 2.23), see binK below
    float binO = smoothstep(1.30, 1.42, abs(v_wpos.x)) * smoothstep(1.62, 1.7, v_wpos.y) * (1.0 - smoothstep(2.18, 2.22, v_wpos.y)) * sz;
    float cBin = (1.0 - smoothstep(0.95, 1.05, abs(v_wpos.x))) * smoothstep(1.62, 1.70, v_wpos.y) * (1.0 - smoothstep(2.28, 2.36, v_wpos.y)) * sz;
    float wallProx = smoothstep(1.7, 2.55, abs(v_wpos.x));
    float facingIn = clamp(-sign(v_wpos.x) * N.x, 0.0, 1.0);
    // QA r2 (light): only faces recessed behind the lining circle (R = u_R - 0.10, 07_shell wallAt) count as the reveal:
    // at the belt the flat lining itself stands at |x| ~2.92, so the old |x| > 2.72-2.84 test took the whole wall between
    // the windows for reveal and nearPane kept the cruise lavender off it [V: ml_DSC_1939-1 belt between the windows
    // #888db0 (B-R +40) vs cF03 #cccccf (+3), the tubs by the glass near-white]
    float xLin = sqrt(max((u_R - 0.10)*(u_R - 0.10) - (v_wpos.y - u_yc)*(v_wpos.y - u_yc), 0.0));
    float recd = smoothstep(xLin + 0.004, xLin + 0.02, abs(v_wpos.x));
    // QA L8 (light): the cool shadow light of the Boarding look (r4: hemiBot / wash cooled for the shaded whites by the
    // windows) keyed to the window side: the sidewall faces (within ~0.06-0.25 m of the lining circle, facing in; not the
    // window seats' shells, which wallProx x facingIn took as well), the recessed reveals and tubs (recd) and
    // half of it on the outboard bin doors (binO); the seat level and the rest take the neutral u_hemiBotN / u_washN
    // (the pre-r4 values; = hemiBot / wash in the other moods), also in the reflected cabin (envInside). The r4 shift had also cooled the THE Room seat level past
    // the photo [V: q06 seat zone B-R +11 -> +16 vs c_27312 +8, shell tops +15 -> +23 vs +11; ash door leaves -4 -> +1 vs
    // c_27314 -4] and the economy bins [V: q15 bins B-R +8 vs y_47300 +0..+2], while the window-side whites are right
    // (q16 wall +10 vs y_47301 +14) (integration L8 low, lighting L8 medium) [D]
    float coolW = max((1.0 - smoothstep(0.06, 0.25, xLin - abs(v_wpos.x))) * facingIn, max(recd, 0.5 * binO));
    hBot = mix(u_hemiBotN, u_hemiBot, coolW);
    vec3 wsh = mix(u_washN, u_wash, coolW);
    // QA L9 (light): the centre bins' doors take u_ctrLift x the lift (12_scene MOODS ctrLift: 3 in Dining / Sunrise, 1
    // elsewhere, where binLift is 0 anyway). One lift for both reached the outboard doors' photo level first: seen from a
    // seat the centre-bin faces stayed ~30 L under it [V: ucr_the-room-cabin centre-bin doors #c79352 L154 s0.59 vs dd
    // #a3773f L125 s0.61; d06 centre L113 vs outboard L147]; a uniform x2 took the d06 outboard doors to L161 (photos L154)
    // [D L9rate t: x3.2 centre-only dd 144, d06 143, PSU band / outboard / q21 unchanged] (lighting L9 medium)
    vec3 hemi = mix(hBot + u_binLift * max(binO, u_ctrLift * cBin) * mix(1.0, 0.25, smoothstep(0.85, 0.98, down)), u_hemiTop, up);
    // QA r1 (light): sz = 1 where an outboard bin and its lens stand (08_bins builds them in the seat zones only), from
    // the zone row of the window LUT. The lens band, its colour and the bin overhang shade stop at the door, galley and
    // lav zones, which stay neutral white [V: sany_10 band #525d94 under the bins while the door-3 / monument zone
    // reads #e1e3d8 / #e8e8e4; was q21 door 4L lining #bf712c] (integration r1)
    float lensW = wallProx * sz;
    // the outboard bins overhang the sidewall from ~1.6 m: the wall just below sees the lens, not the ceiling
    // (tlfl_IMG_9217 / sany_10: the band under the bins is lit blue only, the aisle side of the bins white) [D]
    float binShade = 1.0 - 0.75 * lensW * facingIn * smoothstep(1.15, 1.6, v_wpos.y);
    // QA r4 (light): the outboard bin doors (binO, above) are lit by the cove above them, so the lower, inboard-down part
    // of the face sees the darker cabin
    // below: hemi + bounce x u_binLo there, x1 where the crest turns up (N.y 0.6). They read near-white and flat (q06
    // L211-218, p10 197, hp 1.3) where the photos run from a lit crest down to grey [V: c_27312 bins L190-199, p10 168,
    // hp 21; y_47301 #a3a9b1-#dddfe4; py_37302 L183 p10 161; lalf_room_119 bin faces 164 -> 71] (lighting r4 medium,
    // integration r4 high); per mood (1 in the amber / dark moods, whose bins the photos show cove-washed) [D]
    // QA L8 (light): the centre bins' doors and undersides (cBin) take their own factor u_ctrLo (1 except Cruise): in flight
    // they are the dim layer under the cove-lit vault [V: lalf_room_119 centre-bin underside #4c4e56 L79, sany_22 (cruise,
    // economy) L68-85 vs c15 #b6b7bb L183] (lighting L8 medium); Boarding keeps them (q15 L209 vs y_47300 L195, q16 L210 vs
    // y_47301 L209) [D]
    float binK = 1.0 - (binO * (1.0 - u_binLo) + cBin * (1.0 - u_ctrLo)) * (1.0 - smoothstep(-0.2, 0.6, N.y));
    // interreflection fill: a white-lined cabin bounces the cove/ceiling light onto every face (ANA photos show
    // charcoal shells and navy fabric reading mid-tone, not black); scaled by AO so crevices stay dark. QA r1: weaker
    // on down-facing faces and towards the floor, so bin undersides / PSU band and footwells keep the shadow line and
    // falloff of the photos [V: tlfl_IMG_9217 PSU underside #615c5d, c_27312 footwell #2d2c30]
    // QA r2: (0.35 + 0.65 ao) / mix(0.55, 1, height) crushed vertical fabric in the dense Y seat block to navy-black
    // (#141c47 vs y_47300 seat backs #2c3a63) and THE Room ash to #7a766d (c_27312 ash #bdb6a3): AO weight halved and the
    // height falloff eased to 0.75 on faces that do not look down; undersides keep the r1 falloff [V: y_47300, c_27312]
    // QA r1 (light): low faces (below ~0.75 m) that do not look up (N.y < 0.3) take the bounce at AO weight 0.35 + 0.65
    // ao, so the footwells / under-ottoman pockets go deep [V: c_27314 footwell #332e30 (L47) vs q09 #494852 (L73);
    // omaat_f11 under-ottoman / top 0.21 vs q03 0.46] (integration r1). Up-facing fabric and everything above keep the
    // r2 weight: applied to all heights it darkened the dense Y block (from_econ w10: q18 hood L166 -> 114)
    float noDown = 1.0 - down;
    float aoW = mix(0.35 + 0.65*ao, 0.5 + 0.5*ao, max(smoothstep(0.2, 0.4, N.y), smoothstep(0.35, 0.75, v_wpos.y)));
    vec3 bounce = mix(hBot, u_hemiTop, 0.62) * u_fill * aoW
                * mix(0.45, 1.0, up) * mix(mix(0.55, 0.75, noDown), 1.0, smoothstep(0.0, 1.4, v_wpos.y));
    // reveal glow: faces within ~0.12 m of a pane pick up the window light (alpha of the window LUT = window span in z,
    // rgb = shade transmittance) [V: tlfl_IMG_9217 / 9518 glowing reveals]
    vec4 wl = texture(u_win, vec2((v_wpos.z - u_winZ.x)/(u_winZ.y - u_winZ.x), v_wpos.x < 0.0 ? WL : WR));
    // (xLin / recd: above)
    float reveal = wl.a * recd * (1.0 - smoothstep(0.2, 0.34, abs(v_wpos.y - u_winY.x)));
    // QA r1 (light): the down-facing upper tub just above the opening keeps its shadow (0.35 of the glow): every photo
    // shows the tub darkest there, at 0.65-0.78 of the pier [V: sans_14, tt_window, sp_py14; from_shell w5]
    reveal *= mix(1.0, 0.35, smoothstep(0.20, 0.30, v_wpos.y - u_winY.x) * down);
    // next to the glass the window light wins over the lens colour [V: tlfl_IMG_9206 reveal #e0dfdd, tlfl_IMG_9217
    // #c7c1c0 by the pane; was c06 #6a73d6] (integration r1). QA r2: only as far as the shade lets the window light in
    // (shade row): a closed blackout took 0.75 off its lens / band light and read 0.45 of the wall, against 0.64 before
    // nearPane and 0.65 in the photo [V: omaat_room24; from_shell w10a]
    vec2 shT2 = texture(u_win, vec2((v_wpos.z - u_winZ.x)/(u_winZ.y - u_winZ.x), WS)).rg;
    float shT = v_wpos.x < 0.0 ? shT2.r : shT2.g;
    float nearPane = 1.0 - 0.75*reveal*shT;
    // QA r2 (light): the down-facing tub crown (0.32-0.62 m above the pane centre: F/J top 0.46, PY/Y 0.565 in 07_shell
    // REC / REC_Y) sees the lit cloud deck through the pane, so it reads near the pier, not grey: the reveal glow stops at
    // 0.34 m [V: sp_py14 / sans_14 crown ~0.85-1.0 of the pier, darkest just above the bezel; oY crown 0.69 (render);
    // from_shell w10b / w12a]; level [D]
    float crown = recd * wl.a * down * smoothstep(0.32, 0.42, v_wpos.y - u_winY.x) * (1.0 - smoothstep(0.58, 0.66, v_wpos.y - u_winY.x)) * shT;
    // QA r2: the sidewall band between the window tops and the bin lens is lit by the lens only; with the full hemi,
    // bounce and wash on top the blue/amber sideLed washed out to #b8c0d5. Those terms are cut inside the band and the
    // lens ramp starts lower so the colour reaches the window tops (glass top ~1.32 m), fading to white at the belt
    // [V: tlfl_IMG_9217 band #5d5eca / #5458dd, belt #867db2; sany_12 #4c5edc; ff_door-gap amber lens #ffa43d]
    // QA r3: the coloured band runs down past the windows (u_sideLow of the lens level at the belt, out by 0.35 m;
    // u_sideWall = per-channel share of the lens light on the wall: 1 for blue, a less red share for amber, which
    // otherwise reads blood-orange at wall level while the lens clips to amber [V: bins #945a2a h27 at low light])
    // instead of fading to white 0.3 m under the bins [V: sany_12 #556df7 at the bins, #5362e0 at the window line;
    // tlfl_IMG_9217 belt between the windows #736a88; sans-18 lavender to the floor]. u_bandCut = how much of the
    // ceiling light the band loses; both per mood (the white boarding lens needs little cut, amber stays at the lens)
    float band = lensW * facingIn * smoothstep(0.7, 1.2, v_wpos.y) * (1.0 - smoothstep(1.95, 2.1, v_wpos.y)) * u_bandCut * nearPane;
    float bandW = min(1.0, band * 1.25);   // the wash is cut a little harder (r2: 0.8 vs 0.65)
    // amber phase: u_lowTint below 1.25 m, 1 above 1.95 m (1 in the white moods). QA r1 (light): the amber reaches seat
    // level, warm and dimmer (u_lowGain), not neutral: the r3 basis (ff_door-gap ash #afafaf) re-sampled at 1024 px
    // reads #b29f84 / #6b5946 (s0.25-0.34) [V: ff_seat-with-door-closed ash cabinet #ab7f58, ash top #bb9067, shell
    // #251f17; ucr_the-room-cabin ash #ae7134 / #885635, sidewall #ba895b, bottom third L55; kn_room_35 ash #804e10]
    lt = mix(u_lowTint * u_lowGain, vec3(1.0), smoothstep(1.25, 1.95, v_wpos.y));
    // QA L10 (light medium): Blue: the open-topped THE Suite takes u_fLow (12_scene MOODS.blue fLow) of the seat-level light: the
    // suite interior read 0.17-0.23 of the matched window wall, the in-flight photos 0.36-0.47, violet-grey [V: ml_DSC_1945
    // aisle-side box #2a243c L40, table L37, pier L48 vs blueF03 L16 / 20 / 22 at window wall L96 vs 103]; the inF box with the
    // |x| fade out to 2.75-2.95 m, so the window console takes it too (1 in the other moods: Boarding q03 box L91 vs omaat_f11 L101)
    lt *= mix(1.0, u_fLow, inFzy * (1.0 - smoothstep(2.75, 2.95, abs(v_wpos.x))));
    // QA r3: the aisle floor took nearly the full hemisphere and read as a bright flat strip; carpet sits in a 1.3 m
    // trench of shells and sees the ceiling through a slot [V: c_27312 aisle #312828-#423b39, darker at the bases]
    hemi *= lt * mix(1.0, 0.55, fl); bounce *= lt * mix(1.0, 0.6, fl);
    // (QA r3 (integration): the r2 extra bounce cut on occluded carpet, x0.6 below aoPk 0.28, is gone: stacked with the
    // floor pocket term below it crushed the Y / PY legroom to L5-15 [V: q17 between rows L14 p10 5 vs y_47303 L39 p10 26;
    // sany_13 floor / seat back 0.27-0.52 vs q17 0.18])
    // QA r3: unoccluded share of the hemisphere (u_aoTune.x, was 0.15) and a bounce gain (u_aoTune.y), AO_TUNE in
    // 12_scene.js: vertical faces between the seats read 2-3x too dark against the lit tops (charcoal shells #191b1f
    // vs c_27312 #394049-#414755, ash ends #848078 vs #bdbaab)
    // QA r4 (light): Blue mood (u_monHemi 0.4): the door / galley / lav zones (sz = 0) lose most of the blue hemi (and wash) and keep
    // their warm monFill [V: sany_47 galley / door end #564a4d h346 s0.14, door zone ~#776349 under the blue cove lines
    // vs bl16 #393e6f h235] (lighting r4 low); 1 elsewhere
    // QA L9 (light): except the aft-facing THE Suite front wall (10_mono inkWall at z 7.40, in the door-1 zone just ahead of
    // u_fZone.x 7.52), which faces into the suite cabin and takes its blue light: it read neutral grey-mauve [V: ml_DSC_1946
    // bulkhead #4f3d71 L69 s0.46 / #3c3ec5 s0.70 vs blueF03 #463d49 L64 s0.17] while the economy galley ends stay warm
    // [V: sany_47 #73606a vs bl16 #6a6071] (lighting L9 low)
    float fWall = step(0.5, N.z) * smoothstep(u_fZone.x - 0.8, u_fZone.x - 0.2, v_wpos.z) * (1.0 - smoothstep(u_fZone.x, u_fZone.x + 0.1, v_wpos.z));
    float monK = mix(1.0, u_monHemi, (1.0 - sz) * (1.0 - fWall));
    hemi *= monK; bounce *= monK;
    amb = (hemi * (u_aoTune.x + (1.0 - u_aoTune.x)*ao) + bounce * u_aoTune.y) * binShade * (1.0 - band) * binK
        + wsh * lt * wallProx * (0.35 + 0.65*facingIn) * smoothstep(0.3, 1.25, v_wpos.y) * (0.45 + 0.55*ao) * noDown * (1.0 - bandW) * monK
        + u_sideLed * u_sideWall * lensW * facingIn * mix(u_sideLow, 1.0, smoothstep(0.95, 1.55, v_wpos.y)) * smoothstep(0.35, 0.8, v_wpos.y)
                    * (1.0 - smoothstep(1.95, 2.1, v_wpos.y)) * noDown * nearPane
        + u_winGlow * wallProx * facingIn * smoothstep(0.7, 1.1, v_wpos.y) * (1.0 - smoothstep(1.5, 1.8, v_wpos.y)) * 0.5 * (1.0 - band)
        // QA r1 (light): reveal glow 1.4 -> 1.9, the reveal sides read grey at grazing angles [V: c_27312 reveal sides
        // #d7dbdf / #e2e5e8 vs q06 #b2b1af / #c7c9c9] (integration r1)
        + u_winGlow * wl.rgb * reveal * 1.9 + u_winGlow * vec3(0.92, 1.0, 1.18) * crown * 1.1;
        // QA r4 (light): the crown takes 1.1 of the window light (was 0.7): shaded whites by the glass read neutral grey
        // where the official photos are cool blue-grey [V: y_47303 crown #a7adc2 (B-R +27) vs q17 #b2b3b3; py_37301 reveal
        // sides #9ba6bc vs q14 #bfbfc0] (lighting r4 medium; with the cooler boarding hemiBot / wash in 12_scene). QA L8: in
        // the sky's tint (x[0.92, 1.0, 1.18], the blue of the sky seen through the pane over the deck's grey)
    // QA L8 (light): the upper tub (0.30-0.66 m over the pane centre, any facing, shade open) sees the sky through the pane
    // and little of the cabin ceiling, so its light takes the hue of the day glow (x the sky tint above) at u_tubSky.y of its
    // level, for a share u_tubSky.x (Boarding only; 0 elsewhere, 12_scene MOODS tubSky). The cream reveal (07_shell
    // MAT.reveal #ece4d5) under the neutral cabin fill read neutral and ~25-35 L light; the official photos show the upper
    // tubs a cool blue-grey [V: y_47303 upper tub / crown #a4a9be L170 (B-R +25), #a4aac0 L171 (+28) vs q17 L188-208 (+3..+7);
    // py_37301 reveal sides #9ba6bc (+33)] (lighting L8 medium); share / level [D renders fixL8]
    float crownW = recd * wl.a * smoothstep(0.30, 0.40, v_wpos.y - u_winY.x) * (1.0 - smoothstep(0.58, 0.66, v_wpos.y - u_winY.x)) * shT;
    vec3 skyT = u_winGlow * vec3(0.92, 1.0, 1.18);
    float lSky = dot(skyT, vec3(0.2126, 0.7152, 0.0722));
    if (u_tubSky.x > 0.0 && crownW > 0.0 && lSky > 1e-4)
      amb = mix(amb, skyT * (dot(amb, vec3(0.2126, 0.7152, 0.0722)) * u_tubSky.y / lSky), u_tubSky.x * crownW);
    // night: the galley / lav / door zones (sz = 0) keep a dim neutral fill, the galley lights and lit bulkheads at the
    // end of the dark cabin [V: ucr_room-night-lighting far galley wall #645f57; sany_40 lit galley end] (lighting r1)
    // QA L9 (light): in Blue (u_monHemi < 1) half of it on the THE Suite front wall (fWall, above): the full warm fill greyed
    // the wall's blue (with the full hemi: #524a6a L79 s0.30), none read #25265c L42 (photo L69), half #3e3a63 L62 h246 s0.42
    // [V: ml_DSC_1946 bulkhead #4f3d71 L69 s0.46] [D fixL9 tlow]; the Night fill stays (Night keeps u_monHemi 1)
    amb += u_monFill * (1.0 - sz) * (1.0 - 0.5 * fWall * step(u_monHemi, 0.999)) * mix(0.45, 1.0, up) * (0.3 + 0.7*ao);
    // QA r4 (light): the recessed window tub from just above the bezel to the crown (0.10-0.66 m over the pane centre),
    // where the window light is dim (sunset, closed shades: 1 - shade x the day glow share; u_tubWash is 0 outside the
    // amber moods, 12_scene MOODS tub), keeps at least
    // u_tubWash (0.7) of the diffuse light of an unbaked cream face (07_shell MAT.reveal #ece4d5) under a pier's hemi + wash
    // (tubRef, applied to the diffuse term below). 07_shell bakes the tub x0.38-0.55 darker just above the bezel against
    // the day window glow; with the glow dim it went burnt-orange / near-black beside a pale pier [V: ucr_the-room-cabin
    // (amber, shades closed) reveals #a57449-#b28156 L124-137 vs wall #bd8b61 L147 (0.85-0.93); kn_room_35 / 36 pale cream
    // reveals; q21 #a15a2b L102 s0.73 beside a pier at L192] (lighting r4 medium); in day light (open shades) it is 0 and
    // the bake stands [D]. Only on the tub itself (MAT.reveal: no layer, r 0.45): the closed shades (sPleat / fabric /
    // plastic layers), the grey tunnel lining and the seals (r 0.5) keep their own albedo; on them the cream floor
    // painted the closed blackout out of the dd windows (fixL7 after4) [D]
    float tubB = recd * wl.a * smoothstep(0.10, 0.16, v_wpos.y - u_winY.x) * (1.0 - smoothstep(0.58, 0.66, v_wpos.y - u_winY.x))
               * (1.0 - shT * clamp(dot(u_winGlow, vec3(0.2126, 0.7152, 0.0722)) / 0.45, 0.0, 1.0))
               * (layer == 0 && abs(v_mat.r - 0.45) < 0.02 ? 1.0 : 0.0);
    tubRef = (mix(u_hemiBot, u_hemiTop, 0.5) + u_wash) * lt * u_tubWash * tubB * vec3(0.84, 0.78, 0.67);
    // QA r1 (light): crevice term for occluded low pockets: the tonal range lacked near-blacks in the footwells, console
    // gaps, under the ottomans and seats [V: pixels < 30: c_27312 10.2 % vs q06 2.9 %, c_27314 3.6 % vs q09 0.5 %;
    // c_27314 footwell L47 vs q09 L73; omaat_f11 under-ottoman / top 0.21 vs q03 0.46] (integration r1). Kept below
    // ~0.75 m and off up-facing faces and the sidewall: the 8 cm volume reads 0.2-0.5 on open seat faces in the dense Y
    // block and on the wall as well (probe), so an AO threshold alone would have darkened them too [D]
    float crev = (1.0 - mix(0.4, 1.0, smoothstep(0.06, 0.5, ao))) * (1.0 - smoothstep(0.35, 0.75, v_wpos.y))
               * (1.0 - smoothstep(0.2, 0.5, N.y)) * (1.0 - 0.6*wallProx*facingIn);
    amb *= 1.0 - crev;
    // QA r2 (integration): the crevice term above skips up-facing faces, so the occluded carpet under the seat pans and
    // the seat-pan / frame undersides kept bounce + hemi and read L35-50 where the photos read < 30: a pocket term for
    // the floor (fl) and down-facing faces below 0.5 m, off the sidewall. Vertical fabric above 0.3 m is untouched
    // (from_econ w10) [V: bottom band < 30: y_47300 20.0 % vs q15 3.2 %, y_47301 11.0 % vs q16 5.0 %; < 50 py_37302 30.5 %
    // vs q13 14.6 %; c_27312 < 30 18.4 % vs q06 12.7 %; frame p5 y_47300 21 vs q15 40] (from_econ w14)
    // The raters' AO ramp 0.08-0.55 (floor 0.25) also took ~30 % off the open aisle carpet (ao ~0.46-0.52) and crushed
    // q16 / q13 to p5 10 / 8 (y_47301 21, py_37302 25): ramp 0.02-0.28 (the probe values above), floor 0.3 [D renders r2a-f]
    // QA r3 (light + integration): on the carpet (fl) the floor is 0.5 and the ramp 0.0-0.12 of the blurred pocket AO, so
    // only the carpet under a seat pan (ao 0.00-0.01) takes it, not the aisle edge beside a 1.3 m shell (0.11-0.24), and
    // the Y / PY legroom keeps half its light [V: q06 row 520 aisle edges 0.26x the centre vs omaatJ_oj_r31 / r37
    // 0.85-0.9x, c_27312 0.75x; q17 between rows L14 vs y_47303 L39; q13 PY carpet p10 14 vs py_37302 32]; down-facing
    // undersides keep the r2 ramp 0.02-0.28 and floor 0.3 [D renders r3]
    float crevF = (1.0 - mix(fl > 0.5 ? 0.5 : 0.3, 1.0, fl > 0.5 ? smoothstep(0.0, 0.12, aoPk) : smoothstep(0.02, 0.28, aoPk)))
                * (1.0 - smoothstep(0.30, 0.50, v_wpos.y)) * max(fl, step(0.3, down)) * (1.0 - wallProx*facingIn);
    amb *= (1.0 - crevF) * (1.0 - u_contactK * ctc);
    // QA L8 (integration): screen-space contact AO (ssaoF), on the diffuse ambient only: the specular, emissive, sun, tubRef
    // and the local lights below stay out; x0.8 and fading out above 1.9-2.3 m, so the vault and cove stay clean
    // (u_ssao.y = strength, 0 = off: x-ray, low quality, studio) [D]. Not on the window reveals (recd): they are lit by the
    // pane, and the lining's lip standing proud of the tub drew a dark crescent inside every tub (fixL8 ss3 / ss4), where
    // the photos show the moulding continuous and pale [V: c_27312 reveal sides #d7dbdf / #e2e5e8]. Eased out where the AO
    // volume is already low (ao 0.4 -> 0.05, L9: u_sEase 0.25 -> 0.02: footwells, under the consoles), which the crevice terms above darken: stacked,
    // the q09 darks fell under the photo's (p5 36 -> 25 vs c_27314 36; 0.02-0.3: 30; 0.1-0.45: 35 but the q06 / q13 lines
    // fell back to 2.7 / 0.8 %) [D fixL8 f2 / f4 / after]
    float sW = u_sMix * (1.0 - smoothstep(1.9, 2.3, v_wpos.y)) * (1.0 - recd) * smoothstep(u_sEase.x, u_sEase.y, ao);
    if (u_ssao.y > 0.0 && sW > 0.01) {
      // QA L9 (light low): disc and range x(1 + u_sLow) = 1.5 (7.5 cm / 0.15 m) below the headrests (0.85-1.05 m) and off the sidewall:
      // the PY contact darks stayed ~1/3 of the photos' [V: thin dark-line share q13 0.91 vs py_37302 2.77 %, q14 0.58
      // vs py_37301 3.15 %]; the L8 0.15 range drew grey halos on the wall behind the PY headrests, which keeps x1 [D fixL9]
      // QA L10 (integration medium): only aft of THE Room (z > u_sLowZ = 05_layout z20): in THE Room the wider disc drew a second,
      // darker band 3 cm above every headrest flap (q10 x 650 rows 380-384 L92-95 at L8 -> L58-66) [V: c_27315 no band]
      float kR = 1.0 + u_sLow * (1.0 - smoothstep(0.85, 1.05, v_wpos.y)) * (1.0 - wallProx * facingIn) * step(u_sLowZ, v_wpos.z);
      amb *= mix(1.0, max(1.0 - u_ssao.y * ssaoF(v_wpos, Nf, kR), 0.0), sW);
    }
    // reading lights (night): warm cone from the lamp lens to the seat, 0.35 m pool [V: tlfl_IMG_9377 pools on the bed]
    for (int i = 0; i < 8; i++) {
      if (u_spotP[i].w < 0.5) continue;
      vec3 a = u_spotT[i].xyz - u_spotP[i].xyz; float la = length(a); a /= la;
      vec3 d = v_wpos - u_spotP[i].xyz; float t = dot(d, a);
      if (t <= 0.0) continue;
      float r = length(d - a*t) * la / max(t, 0.05);        // radius projected to the target distance
      float cone = 1.0 - smoothstep(0.12, 0.35, r);
      vec3 Ld = -normalize(d);
      amb += u_spotCol * cone * max(dot(N, Ld), 0.0) * (la*la) / max(dot(d, d), 0.04);
    }
    // seat mood strips (THE Room: under the monitor + ottoman toe line): warm local glow from the strip
    // [V: ucr_room-night-lighting strip #ffeb97, console top lit warm under the screen; falloff A]
    // QA r2 (integration): a tighter, brighter pool (0.25 m, x2.5; was 0.4 m x1): the console top under the strip read
    // p95 42 against 156 in the photo [V: ucr_room-night-lighting (520-740, 650-680) p95 156, max 239]
    for (int i = 0; i < 8; i++) {
      if (u_stripP[i].w < 0.5) continue;
      vec3 d = v_wpos - u_stripP[i].xyz; vec3 ax = u_stripA[i].xyz;
      d -= ax * clamp(dot(d, ax) / dot(ax, ax), -1.0, 1.0);          // nearest point on the strip segment
      float r = length(d);
      amb += u_stripCol * (1.0 - smoothstep(0.0, 0.25, r)) * 2.5 * (0.35 + 0.65*max(dot(N, -d / max(r, 1e-3)), 0.0));
    }
    // QA r2 (light): IFE screen spill in the dimmed moods: each of the 6 screens nearest the eye is a Lambertian area
    // light (u_scrP xyz = centre, w = area m2; u_scrN = outward normal; u_scrCol = mean screen radiance). Every in-service
    // night photo shows the housing, console and the shell faces beside the screen lit by it [V: ml_IMG_20200208_1919534
    // (THE Suite at night) housing sides #251e1e L32, console #150d0d; ucr_room-night-lighting near wall #302218 L37 vs
    // q20 #050505; ml_DSC_1945 console top #3b3e6e under the safety video]; 0.05 m2 softening of the 1/r2 [A]. The
    // emitting point is the screen-disc point (radius 0.85 sqrt(A / pi)) nearest the receiver, so the console under the
    // screen and the housing beside it see its near edge, not its centre (a representative-point area light) [D]
    // QA r3 (light): not above ~1.5 m: the spill reached the bin doors and the upper cabin read grey-cool [V: ucr_room-
    // night-lighting outboard bins #2f271e L40 h31, centre bins #0d0909 vs q20 #3d3f44 L63 h221 / #434448 L68]
    float scrH = 1.0 - smoothstep(1.4, 1.7, v_wpos.y);
    for (int i = 0; i < 6; i++) {
      if (u_scrP[i].w <= 0.0 || scrH <= 0.0) continue;
      vec3 sn = u_scrN[i].xyz, sq = v_wpos - u_scrP[i].xyz; sq -= sn * dot(sq, sn);
      float sl = length(sq), rd = 0.85 * sqrt(u_scrP[i].w / 3.14159);
      vec3 d = u_scrP[i].xyz + sq * min(1.0, rd / max(sl, 1e-4)) - v_wpos; float r2 = dot(d, d); vec3 l = d * inversesqrt(r2);
      amb += u_scrCol * scrH * u_scrP[i].w * max(dot(N, l), 0.0) * max(dot(sn, -l), 0.0) / (3.14159 * (r2 + 0.05));
    }
  }
  vec3 L = u_sunDir;
  float ndl = max(dot(N, L), 0.0);
  vec3 sun = vec3(0.0);
  if (ndl > 0.0 && dot(u_sunCol, u_sunCol) > 0.0) {
    float sh = u_exterior > 0.5 ? 1.0 : shadowF(v_wpos, N);
    vec3 tr = u_exterior > 0.5 ? vec3(1.0) : windowT(v_wpos);
    sun = u_sunCol * ndl * sh * tr;
    // QA r1 (light): interior sun soft-clipped on high-albedo faces (1 / (1 + max albedo); 0.6 left q04 at L246) and
    // capped at 2.0, so pale fabric keeps its weave inside a patch (patch <= ~1.5x the fabric) and a white sheet keeps
    // a visible edge under the ACES shoulder [V: omaat_f59 bed #d8bfa2 L194 vs q04 patch #f9f8f7 (clipped); q14 PY patch
    // #e0e0e4 on #787f92 fabric] (lighting / integration r1, from_suite 2)
    // QA r3 (integration): cap 2.0 -> 1.5, the q14 seat-back patch read 1.5x the fabric (rater target <= 1.3x) [D]
    // QA L10 (light medium): the cap acts on the luminance, not per channel: the low sunset sun [4.2, 2.2, 0.9] clipped R and
    // G both to 1.5 and turned the patch on dark materials khaki-olive at its core with an orange rim (s06 shell core #84784e
    // h47 s0.41, penumbra h24-27), where low sun on charcoal reads deep orange [V: ucr_the-room-cabin amber surfaces h28-34];
    // the same 1.5 limit on the patch's luminance keeps its hue [D fixL10, L10rate2 lumcap]
    if (u_exterior < 0.5) {
      sun /= 1.0 + max(max(base.r, base.g), base.b);
      sun *= min(1.0, 1.5 / max(dot(sun, vec3(0.2126, 0.7152, 0.0722)), 1e-4));
    }
  }
  vec3 F0 = mix(vec3(0.04), base, metal);
  vec3 diff = base * (1.0 - metal);
  vec3 H = normalize(L + V);
  float r2 = max(rough, 0.06); float a2 = r2*r2*r2*r2;
  float NdH = max(dot(N, H), 0.0);
  float dd = NdH*NdH*(a2 - 1.0) + 1.0;
  float D = a2 / (3.14159 * dd * dd);
  vec3 F = F0 + (1.0 - F0) * pow(1.0 - max(dot(H, V), 0.0), 5.0);
  float k = (r2 + 1.0)*(r2 + 1.0) / 8.0;
  float G = 1.0 / ((ndl*(1.0 - k) + k) * (NdV*(1.0 - k) + k));
  vec3 specSun = D * F * G * 0.25 * sun;
  vec3 R = reflect(-V, N);
  vec3 env = u_exterior > 0.5 ? mix(u_skyBot, u_skyTop*1.2, smoothstep(-0.2, 0.6, R.y))
                              : envInside(R, 1.0 - smoothstep(1.3, 1.7, v_wpos.y), hBot) * (0.25 + 0.75*ao) * lt;
  vec3 Fe = F0 + (max(vec3(1.0 - rough), F0) - F0) * pow(1.0 - NdV, 5.0);
  vec3 specEnv = env * Fe * (1.0 - rough*0.8);
  // QA r3 (integration): sheen lobe for SHEEN materials (satin leatherette headrest covers): the white cabin reflected
  // at grazing angles, (1 - N.V)^3, which roughness alone cannot give without mirroring the ceiling head-on [V: y_47306
  // cover navy head-on, silver-grey at grazing L86-134; y_47303 flaps #69779d L119 / #879cc6 L155 vs q17 #465079 L82 /
  // #414c73 L77; y_47301 L67-74 vs q16 L33-50] (from_econ w14 / w19 / w23 / w27, from_integration_cam); gain [D]
  // QA r4 (light): (1 - N.V)^2 (was ^3) and tinted 0.3 of the way to the fabric hue (0.5 kept the q16 covers at s0.57 vs
  // the photo's 0.37), so the covers between head-on and grazing
  // lift too and the lobe is not plain white [V: y_47301 covers L64-100 vs q16 L53-58; lobe B/R 1.09 vs y_47303 1.47;
  // q15 head-on covers (40,44,81) vs y_47300 (34,41,67) held] (from_econ w40-w42 medium)
  if (sheen > 0.0) specEnv += env * pow(1.0 - NdV, 2.0) * u_sheen * mix(vec3(1.0), base / max(max(base.r, base.g), max(base.b, 1e-3)), u_sheenTint);
  // QA r2 (integration): on the exterior the sky reflection follows the baked albedo (luminance / the wing's #636466 =
  // 0.39, clamped 0.5-1; metals keep theirs), so the near-to-far albedo ramp of 11_exterior also ramps the grazing
  // reflection that out-lit the near flap [V: KN41 near skin L196 -> far 129-145 vs w19A near L163 / far L173]
  // (from_exterior 14 / 16) [D]. Not in the studio (u_extBounce 0), which draws every unit through this branch
  if (u_exterior > 0.5 && dot(u_extBounce, u_extBounce) > 0.0) specEnv *= mix(clamp(dot(v_col.rgb, vec3(0.2126, 0.7152, 0.0722)) / 0.39, 0.5, 1.0), 1.0, metal);
  // the cove line's colour as seen in a reflection: the cabin hemi hue at the LED level (u_led itself is set so the
  // clipped lens reads amber, and below the clip it is near-red: red rim lines in the amber phase, d07)
  vec3 coveC = u_hemiTop / max(max(u_hemiTop.r, u_hemiTop.g), max(u_hemiTop.b, 1e-4)) * max(max(u_led.r, u_led.g), u_led.b);
  if (u_exterior < 0.5) specEnv += coveSpec(v_wpos, N, V, R, rough, F0, NdV) * coveC * u_cove * sz * (0.25 + 0.75*ao);
  vec3 col = max(diff * (amb + sun), tubRef) + specSun + specEnv + emissive;   // tubRef: QA r4 tub floor (above)
  col += vec3(0.30, 0.62, 1.0) * hl * (0.35 + 0.9*pow(1.0 - NdV, 2.0));
  col = aces(col * u_exposure);
  col = tone(col, u_toe);
  o = vec4(toSRGB(col), 1.0);
}`;

SH.depthVS = `
precision highp float;
in vec3 a_pos; in vec4 a_i0; in vec4 a_i1; in vec4 a_i2; in vec4 a_i3;
uniform mat4 u_viewProj;
void main(){ gl_Position = u_viewProj * (mat4(a_i0, a_i1, a_i2, a_i3) * vec4(a_pos, 1.0)); }`;
SH.depthFS = `precision mediump float; out vec4 o; void main(){ o = vec4(1.0); }`;

// Fullscreen sky: gradient, sun, cloud deck far below, stars at night
SH.skyVS = `
precision highp float;
out vec2 v_ndc;
void main(){
  vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2) * 2.0 - 1.0;
  v_ndc = p;
  gl_Position = vec4(p, 1.0, 1.0);
}`;
SH.skyFS = `
precision highp float;
in vec2 v_ndc;
uniform mat4 u_invViewProj; uniform vec3 u_camPos; uniform vec3 u_sunDir; uniform float u_time;
uniform vec3 u_zenith; uniform vec3 u_horizon; uniform vec3 u_haze; uniform vec3 u_sunTint; uniform float u_night; uniform float u_skyK;
uniform vec3 u_cloudLit; uniform vec3 u_cloudShade; uniform float u_exposure; uniform float u_sunVis; uniform float u_toe;
uniform sampler2D u_cloud;
out vec4 o;
vec3 aces(vec3 x){ return clamp((x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14), 0.0, 1.0); }
float hash(vec3 p){ p = fract(p*0.3183099 + 0.1); p *= 17.0; return fract(p.x*p.y*p.z*(p.x + p.y + p.z)); }
void main(){
  vec4 w = u_invViewProj * vec4(v_ndc, 1.0, 1.0);
  vec3 dir = normalize(w.xyz / w.w - u_camPos);
  float h = dir.y;
  vec3 col;
  float sd = max(dot(dir, u_sunDir), 0.0);
  if (h >= -0.02) {
    // u_skyK > 0 (day): exponential falloff, pale band only in the lowest few degrees, deep blue above ~10 deg
    // [V: F-GSQR_1/_2 cruise window views, #93c3f3 at the horizon -> #2f5b98 -> #15305d; user: deep-blue cruise sky]
    float t = u_skyK > 0.0 ? 1.0 - exp(-u_skyK * max(h, 0.0)) : pow(clamp(h, 0.0, 1.0), 0.42);
    col = mix(u_horizon, u_zenith, t);
    col += u_sunTint * (pow(sd, 6.0)*0.35 + pow(sd, 64.0)*0.8) * u_sunVis;
    col += u_sunTint * smoothstep(0.99955, 0.99975, sd) * 40.0 * u_sunVis;
    if (u_night > 0.5) {
      vec3 sp = floor(dir * 420.0);
      float s = hash(sp);
      col += vec3(0.8, 0.85, 1.0) * step(0.9975, s) * (0.5 + 0.5*hash(sp + 3.1)) * smoothstep(0.02, 0.2, h) * 1.6;
    }
  } else {
    // cloud deck ~3.2 km below; aircraft flies toward -z so the deck drifts toward +z
    float dist = 3200.0 / max(-h, 0.004);
    vec2 p = dir.xz * dist;
    p.y += u_time * 245.0;
    vec2 uv = p / 9000.0;
    float n = texture(u_cloud, uv).r * 0.62 + texture(u_cloud, uv * 3.1 + 0.37).g * 0.28 + texture(u_cloud, uv * 0.35 + 0.1).b * 0.25;
    float cov = smoothstep(0.42, 0.66, n);
    float lit = clamp(0.55 + 0.9*(n - 0.5) + 0.5*dot(normalize(vec3(dir.x, 0.0, dir.z) + 0.0001), vec3(u_sunDir.x, 0.0, u_sunDir.z)) * 0.3, 0.0, 1.2);
    vec3 cloud = mix(u_cloudShade, u_cloudLit, lit);
    vec3 below = mix(u_haze * 0.55, u_haze * 0.35, clamp(-h * 3.0, 0.0, 1.0));
    col = mix(below, cloud, cov);
    float fog = 1.0 - exp(-dist / 60000.0);
    col = mix(col, u_haze, clamp(fog, 0.0, 1.0));
    col += u_sunTint * pow(max(dot(reflect(dir, vec3(0.0, 1.0, 0.0)), u_sunDir), 0.0), 12.0) * 0.12 * cov * u_sunVis;
    col = mix(col, u_horizon, smoothstep(-0.05, -0.02, h));
  }
  col = aces(col * u_exposure);
  float l = dot(col, vec3(0.2126, 0.7152, 0.0722));   // the mainFS tone()
  col *= mix(1.0 - 0.45*u_toe, 1.0, smoothstep(0.002, 0.03, l)) * (1.0 + 0.5*u_toe*smoothstep(0.4, 0.75, l)*(l*(3.0 - 2.0*l) - 1.0));
  o = vec4(mix(col*12.92, 1.055*pow(col, vec3(1.0/2.4)) - 0.055, step(vec3(0.0031308), col)), 1.0);   // sRGB, as mainFS
}`;

// Window glass: multiply what is behind by the pane transmittance
SH.glassFS = `
precision highp float;
in vec3 v_wpos; in vec3 v_nrm; in vec2 v_uv; in vec4 v_col; in vec4 v_mat; flat in vec4 v_tint;
out vec4 o;
void main(){ o = vec4(v_tint.rgb, 1.0); }`;

// Additive glow sprites (reading lights, nav lights)
SH.glowVS = `
precision highp float;
in vec3 a_pos; in vec2 a_uv; in vec4 a_i0; in vec4 a_i1; in vec4 a_i2; in vec4 a_i3; in vec4 a_tint;
uniform mat4 u_viewProj; uniform vec3 u_camRight; uniform vec3 u_camUp; uniform float u_time;
out vec2 v_uv; out vec4 v_tint;
void main(){
  mat4 m = mat4(a_i0, a_i1, a_i2, a_i3);
  vec3 c = m[3].xyz; float s = length(m[0].xyz);
  float blink = 1.0;
  if (a_tint.a > 1.5) blink = step(0.92, fract(u_time * 0.9 + a_tint.a));
  vec3 wp = c + (u_camRight * a_pos.x + u_camUp * a_pos.y) * s;
  v_uv = a_uv; v_tint = vec4(a_tint.rgb * blink, 1.0);
  gl_Position = u_viewProj * vec4(wp, 1.0);
}`;
SH.glowFS = `
precision highp float;
in vec2 v_uv; in vec4 v_tint;
out vec4 o;
void main(){
  float d = length(v_uv - 0.5) * 2.0;
  float a = exp(-d*d*5.0) * (1.0 - smoothstep(0.8, 1.0, d));
  o = vec4(v_tint.rgb * a, 1.0);
}`;
