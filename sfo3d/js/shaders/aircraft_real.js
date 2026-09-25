// Shader for imported (artist-built) airliner models: textured albedo, airline paint zones, flat-glass windows.
// Per-vertex material: aCol = (color.rgb, texture white level), aExtra = (zone, kind + 8*alphaTest, roughness, metalness)
// uAtlas = 1: this draw uses the model's livery atlas (tools/liveries/atlas.py); its alpha < 0.5 marks cabin-window glass
//   painted into the atlas (models without window geometry): dark glass by day, warm cabin light at night.
// uLivTex = 1: the atlas is a baked brand livery (data/liveries/): its colours are the paint, no zone recolouring.
// uNoCabin = 1: freighter (brand flagged `cargo` in data/liveries/manifest): the model's cabin-window glass (kind 1 aft of
//   the flight deck) is shaded as painted-over window plugs in the top colour, no cabin light; the baked freighter
//   liveries paint no windows.
export const ACR_VS = `
#include <common>
#include <vout>
layout(location=0) in vec3 aPos; layout(location=1) in vec3 aNrm; layout(location=2) in vec2 aUV; layout(location=3) in vec4 aCol; layout(location=4) in vec4 aExtra;
uniform mat4 uModel; uniform mat4 uPrevModel; uniform float uGearUp;
out vec3 vWP; out vec3 vN; out vec2 vUV; out vec3 vLP; flat out vec4 vMat; flat out vec4 vMat2;
void main(){
  int zone = int(aExtra.x + 0.5);
  vec3 p = aPos;
  if (uGearUp > 0.5 && (zone == 3 || zone == 4)) p = vec3(0.0); // retracted gear & open gear doors collapse away
  vec4 wp = uModel * vec4(p, 1.0);
  vWP = wp.xyz; vN = normalize(mat3(uModel) * aNrm); vUV = aUV; vLP = aPos;
  vMat = aCol; vMat2 = aExtra;
  vec4 pwp = uPrevModel * vec4(p, 1.0);
  emitClip(wp.xyz, pwp.xyz);
}`;

export const ACR_FS = `
#include <common>
#include <shadow>
#include <fout>
in vec3 vWP; in vec3 vN; in vec2 vUV; in vec3 vLP; flat in vec4 vMat; flat in vec4 vMat2;
uniform sampler2D uAlbedo; uniform float uHasTex; uniform vec4 uFusB; // crown, belly, cockpit-glass x threshold, cabin light
uniform vec3 uLivTop; uniform vec3 uLivBelly; uniform vec3 uLivTail; uniform vec3 uLivTail2; uniform vec3 uLivEngine; uniform vec4 uLivStripe;
uniform float uBellyLine; uniform float uTailStyle; uniform float uDirt; uniform float uAtlas; uniform float uLivTex; uniform float uNoCabin;
uniform vec4 uFus;   // R, Rz, tailX, length (model units)
uniform float uLights; // 1 = landing/taxi lights on (lens glow)
uniform float uSel;    // selection highlight
vec3 glassRefl(vec3 Ng, vec3 V, float sh, float F0, out float F){
  float NoV = clamp(dot(Ng, V), 1e-3, 1.0);
  F = F0 + (1.0 - F0) * pow(1.0 - NoV, 5.0);
  vec3 Rr = reflect(-V, Ng);
  vec3 env = skyEnv(Rr.y < 0.0 ? vec3(Rr.x, -Rr.y * 0.3, Rr.z) : Rr, 0.0);
  env = Rr.y < 0.0 ? mix(env, uGroundBounce * 0.9, smoothstep(0.0, -0.12, Rr.y)) : env;
  vec3 H = normalize(uSunDir + V);
  float spec = min(D_GGX(max(dot(Ng, H), 0.0), 0.04), 300.0) * 0.25 * F * max(dot(Ng, uSunDir), 0.0);
  return env * F + uSunColor * spec * sh;
}
void main(){
  vec3 wp = vWP; vec3 V = uCamPos - wp; float dist = length(V); V /= dist;
  vec3 N = normalize(vN); if (dot(N, V) < 0.0) N = -N;
  int zone = int(vMat2.x + 0.5); float kc = vMat2.y; bool alphaTest = kc > 7.5; int kind = int(mod(kc, 8.0) + 0.5);
  vec4 tx = uHasTex > 0.5 ? texture(uAlbedo, vUV) : vec4(1.0);
  if (alphaTest && tx.a < 0.5) discard;
  vec3 mcol = vMat.rgb; float texWhite = vMat.a;
  vec3 albedo = mcol * tx.rgb; float rough = vMat2.z, metal = vMat2.w;
  vec3 emis = vec3(0.0);
  if (kind == 1 && uNoCabin > 0.5 && vLP.x < -uFusB.z) { kind = 0; albedo = uLivTop; rough = 0.4; tx = vec4(1.0); }  // freighter window plug
  if (kind == 1) {
    albedo = vec3(0.012, 0.013, 0.015); rough = 0.4;
    // night: warm cabin light behind passenger windows, faint instrument glow in the cockpit
    bool cockpit = vLP.x > -uFusB.z;
    float h = hash12(floor(vec2(vLP.x * 2.0, sign(vLP.z)) + 13.0));
    emis = cockpit ? vec3(0.02, 0.03, 0.05) : vec3(1.0, 0.78, 0.5) * (0.55 + 0.45 * h) * step(0.08, h);
    emis *= uFusB.w;
  }
  bool plug = kind == 0 && vMat2.y > 0.5 && vMat2.y < 7.5;        // (a kind-1 glass vertex turned into a freighter plug)
  float winA = (uAtlas > 0.5 && kind == 0 && !plug) ? 1.0 - smoothstep(0.35, 0.6, tx.a) : 0.0;   // painted cabin window
  if (plug) {
    albedo = uLivTop;
  } else if (kind == 0 && uLivTex > 0.5) {
    albedo = tx.rgb;                                            // baked brand livery
    albedo *= 1.0 - uDirt * 0.18 * smoothstep(-0.3, -0.9, vLP.y / max(uFus.x, 0.5));
  } else if (kind == 0) {
    // neutralised (white) base keeps its panel shading; airline colours are applied by region
    // texture white level is stored in sRGB; texture samples are linear
    float lumL = dot(tx.rgb, vec3(0.2126, 0.7152, 0.0722));
    float sh = uHasTex > 0.5 ? clamp(lumL / pow(max(texWhite, 0.2), 2.2), 0.0, 1.1) : 1.0;
    bool whiteish = sh > 0.5 && dot(mcol, vec3(0.333)) > 0.4;
    float shT = mix(1.0, sh, 0.5);
    bool finPx = vLP.y > uFusB.x + 0.06 && abs(vLP.z) < 1.2 && vLP.x < uFus.z * 0.5;
    if (finPx && whiteish && zone != 2 && zone != 7) {
      albedo = uLivTail * shT;
    } else if (zone == 2 && whiteish) {
      albedo = uLivEngine * shT;
    } else if (zone == 0 && whiteish) {
      float e = length(vec2(vLP.y / (uFus.x * 1.12), vLP.z / (uFus.y * 1.12)));
      if (e < 1.0 && vLP.x > uFus.z + 0.5) {
        float px = fwidth(vLP.y) + 1e-3;
        float belly = 1.0 - smoothstep(uBellyLine - px, uBellyLine + px, vLP.y);
        vec3 c = mix(uLivTop, uLivBelly, belly);
        if (uLivStripe.a > 0.5) { float sy = uBellyLine + 0.25 * uFus.x; c = mix(c, uLivStripe.rgb, (smoothstep(sy - 0.09 - px, sy - 0.09 + px, vLP.y) - smoothstep(sy + 0.09 - px, sy + 0.09 + px, vLP.y))); }
        albedo = c * sh;
      } else {
        albedo = vec3(0.9) * sh;
      }
    } else if (whiteish) {
      albedo = vec3(0.9) * sh;
    }
    albedo *= 1.0 - uDirt * 0.18 * smoothstep(-0.3, -0.9, vLP.y / max(uFus.x, 0.5));
  } else if (kind == 2) { rough = 0.28; metal = 0.9; albedo = max(albedo, vec3(0.55)); }
  else if (kind == 3) { rough = 0.7; }
  float sh = getShadow(wp, N, dist) * cloudShadow(wp);
  float ao = mix(0.72, 1.0, smoothstep(-0.7, 0.3, N.y));
  vec3 col = shadePBR(albedo, N, V, rough, metal, sh, ao, 1.0);
  if (kind == 1) {
    float Fg; vec3 refl = glassRefl(N, V, sh, 0.06, Fg) * vec3(0.92, 0.95, 0.97);
    col = col * (1.0 - Fg) + refl + emis * (1.0 - Fg);
  } else if (kind == 0 && winA > 0.01) {
    // painted cabin window: smooth glass over a dark cabin, warm light at night (as the kind-1 windows)
    float Fg; vec3 refl = glassRefl(N, V, sh, 0.06, Fg) * vec3(0.92, 0.95, 0.97);
    float h = hash12(floor(vec2(vLP.x * 2.0, sign(vLP.z)) + 13.0));
    vec3 cab = vec3(1.0, 0.78, 0.5) * (0.55 + 0.45 * h) * step(0.08, h) * uFusB.w;
    vec3 gl = col * 0.35 * (1.0 - Fg) + refl + cab * (1.0 - Fg);
    col = mix(col, gl, winA);
  }
  if (kind == 0 && winA < 0.99) {
    // clear-coat on paint
    vec3 R2 = reflect(-V, N); float F = 0.04 + 0.96 * pow(1.0 - max(dot(N, V), 0.0), 5.0);
    vec3 env = skyEnv(R2.y < 0.0 ? vec3(R2.x, -R2.y * 0.3, R2.z) : R2, 1.5);
    env = R2.y < 0.0 ? mix(env, uGroundBounce, smoothstep(0.0, -0.2, R2.y)) : env;
    vec3 H = normalize(uSunDir + V); float spec = D_GGX(max(dot(N, H), 0.0), 0.09) * 0.22 * F;
    col += env * F * 0.45 + uSunColor * spec * sh * max(dot(N, uSunDir), 0.0);
  } else if (kind == 4) {
    col += albedo * (0.6 + 40.0 * uFusB.w) * uLights;
  }
  col += vec3(1.0, 0.72, 0.2) * uSel * 0.35 * pow(1.0 - max(dot(N, V), 0.0), 3.0) * (0.3 + dot(uSkyUp, vec3(0.3)));
  col = applyFog(col, wp);
  writeOut(col, wp, 1.0);
}`;
