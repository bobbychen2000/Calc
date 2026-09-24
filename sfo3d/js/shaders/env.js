// Sky, water, simple colored geometry, env compose
export const SKY_VS = `
layout(location=0) in vec3 aPos; out vec2 vNdc;
void main(){ vNdc = aPos.xy; gl_Position = vec4(aPos.xy, 1.0, 1.0); }`;

export const SKY_FS = `
#include <common>
in vec2 vNdc;
uniform mat4 uInvViewProj; uniform mat4 uPrevViewProj;
uniform sampler2D uSkyBase;
uniform float uSunDiskScale; uniform float uSkyClouds;
layout(location=0) out vec4 oColor; layout(location=1) out vec4 oAux;

vec3 cloudLayer(vec3 ro, vec3 rd, vec3 bg, out float alpha){
  alpha = 0.0;
  if (uCloud.x <= 0.001 || rd.y <= 0.002 || ro.y > uCloud.y) return bg;
  float t = (uCloud.y - ro.y) / rd.y;
  vec2 p = ro.xz + rd.xz * t;
  float d = cloudDensityAt(p);
  // extra detail
  d *= 0.7 + 0.6 * texture(uNoise, p * 0.00021 + uTime * 0.0004).b;
  d = clamp(d, 0.0, 1.0);
  if (d <= 0.0) return bg;
  float d2 = cloudDensityAt(p + uSunDir.xz / max(uSunDir.y, 0.2) * 180.0);
  float selfSh = exp(-d2 * 2.2);
  float mu = dot(rd, uSunDir); float g = 0.55;
  float hg = (1.0 - g*g) / pow(1.0 + g*g - 2.0*g*mu, 1.5) * 0.25;
  vec3 lit = uSunColor * (0.08 + 0.55 * selfSh) * (0.6 + hg * 1.8) * 0.45 + uSkyUp * 0.55 + uSkyHorizon * 0.15;
  lit *= mix(1.0, 0.72, d); // denser = darker base
  alpha = smoothstep(0.0, 0.6, d) * (1.0 - smoothstep(18000.0, 60000.0, t));
  // aerial perspective to cloud
  float fogT = exp(-t * 0.00004);
  lit = mix(bg, lit, fogT);
  return mix(bg, lit, alpha);
}
float cirrus(vec3 ro, vec3 rd){
  if (rd.y <= 0.01) return 0.0;
  float t = (9000.0 - ro.y) / rd.y; vec2 p = ro.xz + rd.xz * t;
  vec2 q = vec2(p.x * 0.00008 + p.y * 0.00003, p.y * 0.0004 - p.x * 0.0001);
  float n = texture(uNoise, q * 0.6 + vec2(uTime * 0.0004, 0.0)).b * 0.7 + texture(uNoise, q * 2.3).g * 0.3;
  float s = texture(uNoise, p * 0.000021 + 0.3).b;
  return smoothstep(0.55, 0.85, n) * smoothstep(0.55, 0.72, s) * (1.0 - smoothstep(30000.0, 90000.0, t));
}

void main(){
  vec4 w = uInvViewProj * vec4(vNdc, 1.0, 1.0);
  vec3 rd = normalize(w.xyz / w.w);
  vec3 col = textureLod(uSkyBase, dirToEquirect(rd), 0.0).rgb;
  // sun disk
  float mu = dot(rd, uSunDir);
  float sunR = 0.99998918;
  if (mu > sunR) { float r = sqrt(max(0.0, 1.0 - (1.0 - mu) / (1.0 - sunR))); col += uSunColor * 900.0 * uSunDiskScale * (0.4 + 0.6 * r); }
  float ci = cirrus(uCamPos, rd) * 0.22 * (1.0 - uCloud.x * 0.6);
  col = mix(col, (uSunColor * 0.25 * (1.0 + 2.0 * pow(max(mu, 0.0), 8.0)) + uSkyUp * 0.9), ci);
  float a; if (uSkyClouds > 0.5) col = cloudLayer(uCamPos, rd, col, a);
  oColor = vec4(col, 1.0);
  vec4 pc = uPrevViewProj * vec4(rd * 1e5, 1.0);
  vec2 v = vNdc - pc.xy / pc.w;
  oAux = vec4(60000.0, v * 0.5, 1.0);
}`;

// Compose env map (equirect) with clouds from a reference position, used for reflections/ambient
export const ENV_FS = `
#include <common>
in vec2 vUV; out vec4 o;
uniform sampler2D uSkyBase; uniform vec3 uRefPos; uniform vec3 uGroundCol;
void main(){
  float phi = (vUV.x - 0.5) * 2.0 * PI; float th = vUV.y * PI;
  vec3 rd = vec3(sin(th)*sin(phi), cos(th), -sin(th)*cos(phi));
  vec3 col = textureLod(uSkyBase, vUV, 0.0).rgb;
  if (rd.y > 0.0 && uCloud.x > 0.001) {
    float t = (uCloud.y - uRefPos.y) / max(rd.y, 0.01); vec2 p = uRefPos.xz + rd.xz * t;
    float d = cloudDensityAt(p);
    float d2 = cloudDensityAt(p + uSunDir.xz / max(uSunDir.y, 0.2) * 180.0);
    float mu = dot(rd, uSunDir); float g = 0.55; float hg = (1.0 - g*g) / pow(1.0 + g*g - 2.0*g*mu, 1.5) * 0.25;
    vec3 lit = uSunColor * (0.08 + 0.55 * exp(-d2 * 2.2)) * (0.6 + hg * 1.8) * 0.45 + uSkyUp * 0.55 + uSkyHorizon * 0.15;
    float a = smoothstep(0.0, 0.6, d) * (1.0 - smoothstep(18000.0, 60000.0, t));
    col = mix(col, mix(col, lit, exp(-t * 0.00004)), a);
  }
  if (rd.y < 0.0) {
    // distant ground/water seen from above: mix of bay water reflection & land
    vec3 hz = textureLod(uSkyBase, vec2(vUV.x, 0.49), 0.0).rgb;
    col = mix(hz, uGroundCol, smoothstep(0.0, -0.35, rd.y));
  }
  o = vec4(col, 1.0);
}`;

export const WATER_VS = `
#include <common>
#include <vout>
layout(location=0) in vec3 aPos;
out vec3 vWP;
void main(){ vWP = aPos; emitClip(aPos, aPos); }`;

export const WATER_FS = `
#include <common>
#include <shadow>
#include <fout>
in vec3 vWP;
uniform sampler2D uWaves; uniform vec2 uWind; uniform float uWaveAmp;
uniform sampler2D uAptAux; uniform vec4 uAptRect; uniform vec2 uVw; uniform vec2 uUw;
vec2 waveSlope(vec2 uv){ return texture(uWaves, uv).rg; }
void main(){
  vec3 wp = vWP; vec3 V = uCamPos - wp; float dist = length(V); V /= dist;
  float ws = length(uWind); vec2 wd = ws > 0.01 ? uWind / ws : vec2(1, 0);
  mat2 R1 = mat2(0.8, 0.6, -0.6, 0.8), R2 = mat2(0.28, -0.96, 0.96, 0.28);
  float t = uTime;
  vec2 s = vec2(0);
  s += waveSlope(wp.xz / 61.0 - wd * t * 0.028) * 0.9;
  s += waveSlope(R1 * wp.xz / 23.0 - wd * t * 0.052) * 0.7;
  s += waveSlope(R2 * wp.xz / 9.1 - (R2 * wd) * t * 0.07) * 0.5;
  s += waveSlope(R1 * R2 * wp.xz / 3.7 - wd * t * 0.11) * 0.35;
  float fw = length(fwidth(wp.xz));
  s *= uWaveAmp * (1.0 / (1.0 + fw * 0.05));
  vec3 N = normalize(vec3(-s.x, 1.0, -s.y));
  // airport seawall distance (foam)
  vec2 st = vec2(dot(wp.xz, uVw), dot(wp.xz, uUw));
  vec2 auv = (st - uAptRect.xy) / uAptRect.zw; auv.y = 1.0 - auv.y;
  float dA = (auv.x > 0.0 && auv.x < 1.0 && auv.y > 0.0 && auv.y < 1.0) ? texture(uAptAux, auv).r * 40.0 : 100.0;
  float NoV = max(dot(N, V), 0.001);
  float F = 0.02 + 0.98 * pow(1.0 - NoV, 5.0);
  vec3 R = reflect(-V, N); R.y = abs(R.y);
  float rough = 0.04 + 0.25 * smoothstep(50.0, 6000.0, dist);
  vec3 refl = skyEnv(R, rough * 6.0);
  float sh = (dist < uShadowSplits.y ? getShadow(wp, vec3(0,1,0), dist) : 1.0) * cloudShadow(wp);
  // sun glint
  vec3 L = uSunDir; vec3 H = normalize(L + V);
  float NoL = max(dot(N, L), 0.0), NoH = max(dot(N, H), 0.0);
  float spec = D_GGX(NoH, rough + 0.06) * V_Smith(NoV, NoL, rough + 0.06) * (0.02 + 0.98 * pow(1.0 - max(dot(V, H), 0.0), 5.0)) * NoL;
  vec3 body = vec3(0.045, 0.075, 0.07);
  vec3 lightIn = uSkyUp * 0.9 + uSunColor * max(uSunDir.y, 0.0) * 0.35 * mix(0.4, 1.0, sh);
  vec3 col = body * lightIn * (1.0 - F) + refl * F + uSunColor * spec * sh;
  // foam at seawall
  if (dA < 8.0) {
    vec4 fn = texture(uNoise, st * 0.02 + vec2(t * 0.004, 0.0)); vec4 fn2 = texture(uNoise, st * 0.09 - vec2(0.0, t * 0.01));
    float foam = (1.0 - smoothstep(0.0, 3.0 + 4.0 * fn.r, dA)) * smoothstep(0.35, 0.75, fn2.g);
    col = mix(col, (uSkyUp + uSunColor * max(uSunDir.y, 0.0)) * 0.55, foam * 0.6);
  }
  col = applyFog(col, wp);
  writeOut(col, wp, 1.0);
}`;

// Unlit-ish decal geometry (taxi lines) with lighting
export const DECAL_VS = `
#include <common>
#include <vout>
layout(location=0) in vec3 aPos; layout(location=3) in vec4 aCol;
out vec3 vWP; out vec4 vCol;
void main(){ vWP = aPos; vCol = aCol; emitClip(aPos, aPos); }`;
export const DECAL_FS = `
#include <common>
#include <shadow>
#include <fout>
in vec3 vWP; in vec4 vCol;
void main(){
  vec3 wp = vWP; vec3 V = uCamPos - wp; float dist = length(V); V /= dist;
  vec3 N = vec3(0,1,0);
  float sh = getShadow(wp, N, dist) * cloudShadow(wp);
  vec3 alb = vCol.rgb * (0.85 + 0.15 * texture(uNoise, wp.xz * 0.37).r);
  vec3 col = shadePBR(alb, N, V, 0.7, 0.0, sh, 1.0, 0.5);
  col = applyFog(col, wp);
  writeOut(col, wp, 1.0);
}`;

// Low cloud slab: stacked alpha planes (visible from below and above), lit, fogged
export const CLOUD_VS = `
#include <common>
#include <vout>
layout(location=0) in vec3 aPos;
uniform float uH; uniform float uExtent;
out vec3 vWP;
void main(){ vec3 wp = vec3(aPos.x * uExtent, uH, aPos.z * uExtent); vWP = wp; emitClip(wp, wp); }`;
export const CLOUD_FS = `
#include <common>
in vec4 vClip; in vec4 vPrevClip; in vec3 vWP;
uniform vec4 uLayer; // cover, k (0 bottom .. 1 top), uv offset, opacity
uniform float uH; uniform vec3 uCamDir; uniform vec2 uRange;
layout(location=0) out vec4 oColor; layout(location=1) out vec4 oAux;
float dens(vec2 xz, float thr){
  vec2 uv = (xz + uCloudWind * uTime) / uCloud.z + uLayer.z;
  float n = texture(uCloudTex, uv).r + (texture(uNoise, xz * 0.0021 + uLayer.z + uTime * 0.0006).b - 0.5) * 0.28 + (texture(uNoise, xz * 0.011 - uTime * 0.001).g - 0.5) * 0.09;
  return smoothstep(thr, thr + 0.2, n);
}
void main(){
  vec3 wp = vWP; vec3 V = uCamPos - wp; float dist = length(V); V /= dist;
  float vz = dot(wp - uCamPos, uCamDir); if (vz < uRange.x || vz > uRange.y) discard;
  float k = uLayer.y; float thr = 1.0 - uLayer.x + k * 0.13;
  float d = dens(wp.xz, thr);
  if (d < 0.004) discard;
  float d2 = dens(wp.xz + uSunDir.xz / max(uSunDir.y, 0.25) * 70.0, thr - 0.05);
  float mu = dot(-V, uSunDir);
  float g = 0.6; float hg = (1.0 - g * g) / pow(1.0 + g * g - 2.0 * g * mu, 1.5) * 0.08;
  vec3 col;
  bool below = uCamPos.y < uH;
  if (below) {
    // underside: gray base, brighter at thin edges, silver lining toward the sun
    col = uSkyUp * 0.5 + uGroundBounce * 0.3 + uSunColor * (0.035 + 0.14 * (1.0 - d) * (1.0 - d)) * (0.5 + hg * 6.0);
    col *= mix(0.72, 1.0, k) * mix(1.0, 0.82, d);
  } else {
    float shade = exp(-d2 * 1.4 * (1.0 - k * 0.6));
    col = uSunColor * (0.08 + 0.3 * shade) * (0.8 + hg * 3.0) + uSkyUp * (0.8 + 0.25 * k);
  }
  float a = d * uLayer.w * (1.0 - smoothstep(20000.0, 38000.0, length(wp.xz - uCamPos.xz)));
  col = applyFog(col, wp);
  oColor = vec4(col, a);
  oAux = vec4(dist, 0.0, 0.0, a);
}`;
