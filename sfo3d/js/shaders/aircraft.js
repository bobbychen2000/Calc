export const AC_VS = `
#include <common>
#include <vout>
layout(location=0) in vec3 aPos; layout(location=1) in vec3 aNrm; layout(location=2) in vec2 aUV;
layout(location=3) in vec4 aCol; layout(location=4) in vec4 aExtra;
uniform mat4 uModel; uniform mat4 uPrevModel;
out vec3 vWP; out vec3 vN; out vec4 vCol; out vec4 vExt; out vec3 vLP; out vec2 vUV; out vec3 vLN;
void main(){
  vec4 wp = uModel * vec4(aPos, 1.0);
  vWP = wp.xyz; vN = normalize(mat3(uModel) * aNrm); vLN = aNrm; vCol = aCol; vExt = aExtra; vLP = aPos; vUV = aUV;
  vec4 pwp = uPrevModel * vec4(aPos, 1.0);
  emitClip(wp.xyz, pwp.xyz);
}`;

export const AC_FS = `
#include <common>
#include <shadow>
#include <fout>
in vec3 vWP; in vec3 vN; in vec4 vCol; in vec4 vExt; in vec3 vLP; in vec2 vUV; in vec3 vLN;
uniform mat4 uModel;
uniform vec3 uPaneC[3]; uniform vec3 uPaneN[3]; uniform vec3 uPaneE1[3]; uniform vec3 uPaneE2[3]; uniform vec4 uPaneQ[9];
uniform float uPaneRad[3]; uniform vec4 uWiper;
uniform vec4 uPaneInfo; // radius, count, maskWidth, local-x threshold
uniform float uSeed;
uniform vec3 uLivTop; uniform vec3 uLivBelly; uniform vec3 uLivTail; uniform vec3 uLivTail2; uniform vec3 uLivEngine; uniform vec4 uLivStripe;
uniform vec4 uDims;   // L, R, Hc, xMain
uniform vec4 uWin;    // x0, x1, spacing, yLevel
uniform vec2 uWinSize; // w, h
uniform vec4 uWin2; uniform vec2 uWinSize2;
uniform vec4 uCock; uniform vec4 uCock2; // (x0, x1, yb, dmin), (wmax, style, slope, 0)
uniform float uDoors[5];
uniform float uBellyLine; // relative height (m) where belly color starts
uniform float uDirt;
uniform float uTailStyle;
float box(vec2 p, vec2 c, vec2 hs, float r){ vec2 d = abs(p - c) - hs + r; return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0) - r; }

float sdPoly5(vec2 p, vec2 v0, vec2 v1, vec2 v2, vec2 v3, vec2 v4){
  vec2 v[5] = vec2[](v0, v1, v2, v3, v4);
  float d = dot(p - v[0], p - v[0]); float s = 1.0;
  for (int i = 0, j = 4; i < 5; j = i, i++) {
    vec2 e = v[j] - v[i]; vec2 w = p - v[i]; float ee = dot(e, e);
    if (ee < 1e-10) continue;
    vec2 b = w - e * clamp(dot(w, e) / ee, 0.0, 1.0);
    d = min(d, dot(b, b));
    bvec3 c = bvec3(p.y >= v[i].y, p.y < v[j].y, e.x * w.y > e.y * w.x);
    if (all(c) || all(not(c))) s *= -1.0;
  }
  return s * sqrt(d);
}
// glass layer: flat-pane reflection (Fresnel, sky/ground env, sharp sun glint)
vec3 glassReflect(vec3 Ng, vec3 V, float sh, float F0, vec3 tint, out float F){
  float NoV = clamp(dot(Ng, V), 1e-3, 1.0);
  F = F0 + (1.0 - F0) * pow(1.0 - NoV, 5.0);
  vec3 Rr = reflect(-V, Ng);
  vec3 env = skyEnv(Rr.y < 0.0 ? vec3(Rr.x, -Rr.y * 0.3, Rr.z) : Rr, 0.0);
  env = Rr.y < 0.0 ? mix(env, uGroundBounce * 0.9, smoothstep(0.0, -0.12, Rr.y)) : env;
  vec3 H = normalize(uSunDir + V);
  float spec = min(D_GGX(max(dot(Ng, H), 0.0), 0.035), 400.0) * 0.25 * F * max(dot(Ng, uSunDir), 0.0);
  return (env * F + uSunColor * spec * sh) * tint;
}
void main(){
  vec3 wp = vWP; vec3 V = uCamPos - wp; float dist = length(V); V /= dist;
  vec3 N = normalize(vN); N = dot(N, V) < 0.0 ? -N : N;
  int part = int(vExt.z + 0.5);
  vec3 albedo = vCol.rgb; float rough = vExt.x, metal = vExt.y;
  float L = uDims.x, R = uDims.y;
  float px = max(fwidth(vUV.x), fwidth(vUV.y)) + 1e-4;
  float glassW = 0.0, glassF0 = 0.05, glassFlat = 0.0; vec3 glassTint = vec3(1.0); vec3 glassN = N;
  if (part == 1) {
    float xn = vUV.x; float yr = vUV.y; float side = vLP.z; float dTop = vCol.a; float zz = abs(side);
    albedo = mix(uLivBelly, uLivTop, smoothstep(uBellyLine - px, uBellyLine + px, yr));
    if (uLivStripe.a > 0.5) { float sy = uWin.w - 0.55; float st = smoothstep(sy - 0.18 - px, sy - 0.18 + px, yr) - smoothstep(sy + 0.02 - px, sy + 0.02 + px, yr); albedo = mix(albedo, uLivStripe.rgb, st * step(uWin.x - 2.0, xn)); }
    // tail color sweep onto rear fuselage
    float tw = xn + yr * 1.4 - (L - R * 4.6); float tailWrap = smoothstep(-px * 2.0, px * 2.0, tw) * smoothstep(R * 0.05 - px, R * 0.05 + px, yr) * uTailStyle;
    albedo = mix(albedo, uLivTail, tailWrap);
    float onSide = smoothstep(R * 0.5, R * 0.75, zz);
    // passenger windows (up to 2 rows): rounded acrylic panes, seal ring, per-window shade state
    for (int row = 0; row < 2; row++) {
      vec4 Wn = row == 0 ? uWin : uWin2; vec2 Ws = row == 0 ? uWinSize : uWinSize2;
      if (Wn.y <= Wn.x || xn < Wn.x - 0.3 || xn > Wn.y + 0.3 || onSide <= 0.0) continue;
      float cell = (xn - Wn.x) / Wn.z; float ci = floor(cell + 0.5); float cx = (cell - ci) * Wn.z;
      if (ci < 0.0 || ci > floor((Wn.y - Wn.x) / Wn.z + 0.5)) continue;
      float d = box(vec2(cx, yr), vec2(0.0, Wn.w), Ws * 0.5, min(Ws.x, Ws.y) * 0.46);
      float inDoor = 0.0; for (int i = 0; i < 5; i++) inDoor = max(inDoor, 1.0 - step(0.95, abs(Wn.x + ci * Wn.z - uDoors[i])));
      float aa = max(fwidth(d), 1e-4);
      float w = (1.0 - smoothstep(-aa, aa, d)) * (1.0 - inDoor) * onSide;
      float ring = (1.0 - smoothstep(0.018 - aa, 0.018 + aa, d)) * (1.0 - inDoor) * onSide - w;
      float farF = smoothstep(0.04, 0.2, px);
      albedo = mix(albedo, albedo * 0.55, max(ring, 0.0) * (1.0 - farF));
      if (w > 0.0) {
        float hsh = hash13(vec3(ci, float(row) + sign(side) * 7.0, uSeed * 113.0));
        // ~22% shades fully down, ~10% half down; open windows show the dim cabin
        float shadeTop = hsh < 0.22 ? 1.0 : (hsh < 0.32 ? 0.45 : 0.0);
        float yIn = (yr - (Wn.w - Ws.y * 0.5)) / Ws.y; // 0 bottom .. 1 top
        float shade = step(1.0 - shadeTop, yIn) * step(0.001, shadeTop);
        vec3 cabin = vec3(0.03, 0.03, 0.032) * (0.7 + 0.6 * hash13(vec3(ci, 3.0, uSeed)));
        vec3 inner = mix(cabin, vec3(0.42, 0.42, 0.41), shade);
        inner = mix(inner, vec3(0.05), farF * 0.6);
        albedo = mix(albedo, inner, w); rough = mix(rough, 0.6, w);
        glassW = max(glassW, w); glassF0 = 0.08; glassTint = vec3(0.96, 0.98, 1.0);
      }
    }
    // door outlines
    for (int i = 0; i < 5; i++) {
      float dx = xn - uDoors[i];
      if (abs(dx) < 1.2 && zz > R * 0.5) {
        float d = box(vec2(dx, yr), vec2(0.0, uWin.w - 0.62), vec2(0.5, 0.95), 0.18);
        float line = 1.0 - smoothstep(0.0, px * 1.2 + 0.012, abs(d));
        albedo = mix(albedo, albedo * 0.45, line * 0.8 * (1.0 - smoothstep(0.1, 0.3, px)));
      }
    }
    // flight-deck windows: flat glass facets (see aircraft/cockpit.js)
    if (vLP.x > uPaneInfo.w) {
      vec2 qs = vec2(xn, vExt.w); // unwrapped surface coords: distance from nose, arc length from the crown
      float best = 1e3; int bk = -1;
      for (int k = 0; k < 3; k++) {
        if (float(k) >= uPaneInfo.y) break;
        float sd = sdPoly5(qs, uPaneQ[k * 3].xy, uPaneQ[k * 3].zw, uPaneQ[k * 3 + 1].xy, uPaneQ[k * 3 + 1].zw, uPaneQ[k * 3 + 2].xy) - uPaneInfo.x;
        if (sd < best) { best = sd; bk = k; }
      }
      if (bk >= 0) {
        float aa = max(fwidth(best), 1e-4) * 0.8;
        float farF = smoothstep(0.03, 0.12, px);
        // A350-style black mask around the panes
        if (uPaneInfo.z > 0.0) { float mk = 1.0 - smoothstep(uPaneInfo.z - aa, uPaneInfo.z + aa, best); albedo = mix(albedo, vec3(0.018, 0.019, 0.021), mk); rough = mix(rough, 0.22, mk); }
        // rubber seal + retainer panel line
        float seal = 1.0 - smoothstep(0.03 - aa, 0.03 + aa, best);
        float retainer = (1.0 - smoothstep(0.005, 0.005 + aa * 1.5, abs(best - 0.075))) * (1.0 - farF);
        albedo = mix(albedo, albedo * 0.8, retainer * 0.5);
        albedo = mix(albedo, vec3(0.03, 0.031, 0.033), seal); rough = mix(rough, 0.55, seal);
        float g = 1.0 - smoothstep(-aa, aa, best);
        if (g > 0.0) {
          // dim flight deck behind tinted glass: glare shield / panel silhouettes toward the bottom of the pane
          float yb = clamp(-best / 0.25, 0.0, 1.0);
          vec3 deck = vec3(0.022, 0.024, 0.026) * (0.8 + 0.4 * yb);
          albedo = mix(albedo, deck, g); rough = mix(rough, 0.5, g);
          glassW = g; glassF0 = 0.14; glassTint = vec3(0.9, 0.97, 0.96);
          // parked wiper arm/blade on the windshield (dark, slightly glossy)
          if (bk == 0) {
            vec2 wa = uWiper.xy, wb = uWiper.zw; vec2 pa = qs - wa, ba = wb - wa; float hh = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
            float wd = length(pa - ba * hh) - mix(0.016, 0.011, hh);
            float wm = (1.0 - smoothstep(-aa, aa, wd)) * (1.0 - farF);
            glassW *= 1.0 - wm; albedo = mix(albedo, vec3(0.025), wm); rough = mix(rough, 0.35, wm); metal = mix(metal, 0.3, wm);
          }
          vec3 nF = uPaneN[bk]; nF.z *= sign(vLP.z + 1e-6);
          glassN = normalize(mat3(uModel) * nF);
          glassFlat = 0.9;
        }
      }
    }
    albedo *= mix(0.94, 1.0, smoothstep(0.8, 1.6, xn));
    float pl = max(1.0 - smoothstep(0.0, px + 0.006, abs(fract(xn / 2.5 + 0.5) - 0.5) * 2.5), 0.0) * 0.1 * (1.0 - smoothstep(0.03, 0.08, px)) * step(uDims.w, xn);
    albedo *= 1.0 - pl;
    albedo *= 1.0 - uDirt * 0.25 * smoothstep(-R * 0.4, -R, yr) * (0.6 + 0.4 * texture(uNoise, vec2(xn * 0.05, yr * 0.2)).b);
  } else if (part == 3) { // fin
    float h = vUV.y; // 0 root .. 1 tip
    albedo = uLivTail;
    float band = smoothstep(0.35, 0.37, h + (vLP.x - uDims.w) * 0.0) ;
    float diag = h + (-vLP.x) * 0.06;
    albedo = mix(uLivTail, uLivTail2, smoothstep(0.54, 0.56, fract(diag * 0.9 + 0.2)) * step(0.5, uTailStyle));
    rough = 0.26;
  } else if (part == 4) { albedo = uLivEngine; rough = 0.3;
  } else if (part == 11) { albedo = vec3(0.8, 0.81, 0.83); rough = 0.14; metal = 1.0;
  } else if (part == 5) { // fan face: blades
    float a = atan(vLP.y - 0.0, vLP.z); float r = length(vLP.yz);
    albedo = vec3(0.1, 0.105, 0.11) * (0.7 + 0.3 * step(0.5, fract(a * 22.0 / 6.2831 + 0.0)));
    rough = 0.35; metal = 0.7;
  } else if (part == 2 || part == 8 || part == 13) { // wings/stabs: light gray metallic with panels & LE
    vec3 base = part == 8 ? mix(vec3(0.72, 0.73, 0.75), uLivTop, 0.4) : vec3(0.66, 0.67, 0.69);
    float n = texture(uNoise, vLP.xz * 0.08).b;
    albedo = base * (0.92 + 0.12 * n);
    // chordwise leading edge (bare metal) using uv.y ~ airfoil loop param: LE around 0.5
    float le = 1.0 - smoothstep(0.035, 0.06, abs(vUV.y - 0.5));
    albedo = mix(albedo, vec3(0.8, 0.81, 0.83), le); metal = mix(metal, 1.0, le); rough = mix(rough, 0.2, le);
    // walkway / panel grid
    float g = 1.0 - smoothstep(0.0, 0.03 + px, abs(fract(vLP.z / 1.9 + 0.5) - 0.5) * 1.9);
    albedo *= 1.0 - 0.08 * g * (1.0 - smoothstep(0.05, 0.12, px));
  } else if (part == 12) { albedo = uLivTop * 0.95; rough = 0.35;
  }
  float sh = getShadow(wp, N, dist) * cloudShadow(wp);
  // self-occlusion approx: underside darker
  float ao = mix(0.75, 1.0, smoothstep(-0.6, 0.4, N.y));
  vec3 col = shadePBR(albedo, N, V, rough, metal, sh, ao, 1.0);
  // glass layer (cockpit facets use the flat pane normal; cabin windows the local surface normal)
  if (glassW > 0.0) {
    vec3 Ng = normalize(mix(N, glassN, glassFlat)); if (dot(Ng, V) < 0.02) Ng = N;
    float Fg; vec3 refl = glassReflect(Ng, V, sh, glassF0, glassTint, Fg);
    vec3 cg = col * (1.0 - Fg) + refl;
    col = mix(col, cg, glassW);
  }
  // clearcoat on painted parts
  if ((part == 1 && glassW < 0.999) || part == 3 || part == 4) {
    vec3 R2 = reflect(-V, N); float F = 0.04 + 0.96 * pow(1.0 - max(dot(N, V), 0.0), 5.0);
    vec3 env = skyEnv(R2.y < 0.0 ? vec3(R2.x, -R2.y * 0.3, R2.z) : R2, 1.5);
    env = R2.y < 0.0 ? mix(env, uGroundBounce, smoothstep(0.0, -0.2, R2.y)) : env;
    vec3 H = normalize(uSunDir + V); float spec = D_GGX(max(dot(N, H), 0.0), 0.08) * 0.25 * F;
    col += (env * F * 0.5 + uSunColor * spec * sh * max(dot(N, uSunDir), 0.0)) * (1.0 - glassW);
  }
  col = applyFog(col, wp);
  writeOut(col, wp, 1.0);
}`;
