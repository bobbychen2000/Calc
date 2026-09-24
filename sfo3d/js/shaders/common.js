import { defineChunk } from '../gl.js';

defineChunk('noise', `
float hash12(vec2 p){ vec3 p3 = fract(vec3(p.xyx) * .1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
vec2 hash22(vec2 p){ vec3 p3 = fract(vec3(p.xyx) * vec3(.1031, .1030, .0973)); p3 += dot(p3, p3.yzx+33.33); return fract((p3.xx+p3.yz)*p3.zy); }
float hash13(vec3 p3){ p3 = fract(p3 * .1031); p3 += dot(p3, p3.zyx + 31.32); return fract((p3.x + p3.y) * p3.z); }
float vnoise(vec2 p){ vec2 i=floor(p), f=fract(p); vec2 u=f*f*(3.-2.*f);
  return mix(mix(hash12(i),hash12(i+vec2(1,0)),u.x), mix(hash12(i+vec2(0,1)),hash12(i+vec2(1,1)),u.x), u.y); }
float fbm2(vec2 p, int oct){ float s=0., a=.5, n=0.; for(int i=0;i<8;i++){ if(i>=oct) break; s+=a*vnoise(p); n+=a; p=p*2.03+vec2(1.7,9.2); a*=.5; } return s/n; }
// integer hash for procedural placement (matches JS ihash)
uint ihash(uint x){ x ^= x >> 16; x *= 0x7feb352dU; x ^= x >> 15; x *= 0x846ca68bU; x ^= x >> 16; return x; }
float ihashf(ivec2 c, int salt){ return float(ihash(uint(c.x*73856093) ^ uint(c.y*19349663) ^ uint(salt*83492791))) / 4294967295.0; }
`);

defineChunk('common', `
#include <noise>
uniform mat4 uViewProj;      // camera-relative view*proj
uniform vec3 uCamPos;        // world camera position
uniform vec3 uSunDir;        // direction to sun
uniform vec3 uSunColor;      // sun radiance (HDR)
uniform vec3 uSkyUp;         // ambient irradiance from upper hemisphere
uniform vec3 uSkyHorizon;
uniform vec3 uGroundBounce;
uniform sampler2D uSkyTex;   // equirect sky+clouds env (HDR)
uniform float uTime;
uniform vec4 uFog;           // x: density at sea level (1/m), y: height falloff (1/m), z: mie strength, w: max opacity
uniform vec4 uCloud;         // x: coverage, y: base height, z: scale, w: shadow strength
uniform vec2 uCloudWind;
uniform sampler2D uCloudTex;
uniform sampler2D uNoise;
const float PI = 3.14159265;

vec2 dirToEquirect(vec3 d){ float u = atan(d.x, -d.z) / (2.0*PI) + 0.5; float v = acos(clamp(d.y,-1.,1.)) / PI; return vec2(u, v); }
vec3 skyEnv(vec3 d, float lod){ return textureLod(uSkyTex, dirToEquirect(normalize(d)), lod).rgb; }

float cloudDensityAt(vec2 xz){
  vec2 uv = (xz + uCloudWind * uTime) / uCloud.z;
  float n = texture(uCloudTex, uv).r;
  float c = smoothstep(1.0 - uCloud.x, 1.0 - uCloud.x + 0.28, n);
  return c;
}
float cloudShadow(vec3 wp){
  if (uCloud.x <= 0.001) return 1.0;
  float t = (uCloud.y - wp.y) / max(uSunDir.y, 0.05);
  vec2 p = wp.xz + uSunDir.xz * t;
  return 1.0 - uCloud.w * cloudDensityAt(p);
}

// Aerial perspective: exponential height fog with sky-colored inscatter + mie sun glow
vec3 applyFog(vec3 col, vec3 wp){
  vec3 d = wp - uCamPos; float dist = length(d); vec3 rd = d / max(dist, 1e-3);
  float a = uFog.x, b = uFog.y;
  float ch = uCamPos.y;
  // integral of a*exp(-b*h) along ray
  float fogAmt;
  if (abs(rd.y) > 1e-4) fogAmt = a * exp(-b * ch) * (1.0 - exp(-b * rd.y * dist)) / (b * rd.y);
  else fogAmt = a * exp(-b * ch) * dist;
  float T = exp(-fogAmt);
  vec3 hd = normalize(vec3(rd.x, max(rd.y, 0.0) * 0.5 + 0.035, rd.z));
  vec3 inscat = skyEnv(hd, 5.0);
  float mu = dot(rd, uSunDir);
  float g = 0.75; float hg = (1.0 - g*g) / pow(1.0 + g*g - 2.0*g*mu, 1.5) / (4.0*PI);
  inscat += uSunColor * hg * uFog.z * 0.08;
  T = max(T, 1.0 - uFog.w);
  return col * T + inscat * (1.0 - T);
}

// GGX
float D_GGX(float NoH, float r){ float a=r*r; float a2=a*a; float d=NoH*NoH*(a2-1.)+1.; return a2/(PI*d*d); }
float V_Smith(float NoV, float NoL, float r){ float k=(r+1.)*(r+1.)/8.; return 0.25/((NoV*(1.-k)+k)*(NoL*(1.-k)+k)); }
vec3 F_Schlick(vec3 f0, float VoH){ return f0 + (1.-f0)*pow(1.-VoH, 5.); }

// Standard PBR shading with sun + hemispheric sky + env specular
vec3 shadePBR(vec3 albedo, vec3 N, vec3 V, float rough, float metal, float shadow, float ao, float specOcc){
  vec3 L = uSunDir; vec3 H = normalize(L + V);
  float NoL = max(dot(N, L), 0.0), NoV = max(dot(N, V), 1e-3), NoH = max(dot(N, H), 0.0), VoH = max(dot(V, H), 0.0);
  vec3 f0 = mix(vec3(0.04), albedo, metal);
  vec3 F = F_Schlick(f0, VoH);
  vec3 spec = D_GGX(NoH, max(rough, 0.04)) * V_Smith(NoV, NoL, max(rough,0.04)) * F;
  vec3 kd = (1.0 - F) * (1.0 - metal);
  vec3 direct = (kd * albedo / PI + spec) * uSunColor * NoL * shadow;
  // ambient: hemispheric
  float up = N.y * 0.5 + 0.5;
  vec3 amb = mix(uGroundBounce, mix(uSkyHorizon, uSkyUp, smoothstep(0.3, 1.0, up)), smoothstep(0.0, 0.55, up));
  vec3 diffAmb = amb * albedo * (1.0 - metal) * ao;
  vec3 R = reflect(-V, N);
  vec3 env = skyEnv(R.y < 0.0 ? vec3(R.x, -R.y * 0.3, R.z) : R, rough * 7.0);
  env = R.y < 0.0 ? mix(env, uGroundBounce * 0.8, smoothstep(0.0, -0.25, R.y)) : env;
  vec3 Fa = f0 + (max(vec3(1.0 - rough), f0) - f0) * pow(1.0 - NoV, 5.0);
  vec3 specAmb = env * Fa * specOcc * ao;
  return direct + diffAmb + specAmb;
}
`);

defineChunk('shadow', `
uniform sampler2DShadow uShadow0;
uniform sampler2DShadow uShadow1;
uniform sampler2DShadow uShadow2;
uniform mat4 uShadowMat0;
uniform mat4 uShadowMat1;
uniform mat4 uShadowMat2;
uniform vec3 uShadowSplits; // view distances where cascades end
uniform vec3 uShadowTexel;  // world size of a texel per cascade
uniform float uShadowRes;
float sampleCascade(sampler2DShadow s, mat4 M, vec3 wp, float radius, float bias){
  vec4 p = M * vec4(wp, 1.0); vec3 c = p.xyz / p.w * 0.5 + 0.5;
  if (c.x < 0.002 || c.x > 0.998 || c.y < 0.002 || c.y > 0.998 || c.z > 1.0) return -1.0;
  float ang = hash12(gl_FragCoord.xy) * 6.283; vec2 d1 = vec2(cos(ang), sin(ang)) * radius, d2 = vec2(-d1.y, d1.x);
  float z = c.z - bias;
  float sum = texture(s, vec3(c.xy, z)) * 2.0;
  sum += texture(s, vec3(c.xy + d1, z)) + texture(s, vec3(c.xy - d1, z)) + texture(s, vec3(c.xy + d2, z)) + texture(s, vec3(c.xy - d2, z));
  return sum / 6.0;
}
float getShadow(vec3 wp, vec3 N, float viewDist){
  float r = 1.5 / uShadowRes;
  if (viewDist < uShadowSplits.x) {
    float s = sampleCascade(uShadow0, uShadowMat0, wp + N * uShadowTexel.x * 1.5, r, 0.00008);
    if (s >= 0.0) return s;
  }
  if (viewDist < uShadowSplits.y) {
    float s = sampleCascade(uShadow1, uShadowMat1, wp + N * uShadowTexel.y * 1.5, r, 0.00012);
    if (s >= 0.0) return s;
  }
  if (viewDist < uShadowSplits.z) {
    float s = sampleCascade(uShadow2, uShadowMat2, wp + N * uShadowTexel.z * 1.5, r, 0.00018);
    if (s >= 0.0) return mix(s, 1.0, smoothstep(uShadowSplits.z * 0.8, uShadowSplits.z, viewDist));
  }
  return 1.0;
}
`);

// Precompute sky: single scattering Rayleigh + Mie, equirect
export const SKY_PRECOMPUTE_FS = `
in vec2 vUV; out vec4 o;
uniform vec3 uSunDir; uniform float uMie; uniform float uSunI; uniform float uCamH;
const float PI=3.14159265; const float Re=6360e3; const float Ra=6420e3;
const vec3 bR = vec3(5.8e-6, 13.5e-6, 33.1e-6); const float Hr=7994.0; const float Hm=1200.0; const vec3 bO = vec3(0.65e-6, 1.881e-6, 0.085e-6) * 1.8;
vec2 raySphere(vec3 ro, vec3 rd, float r){ float b=dot(ro,rd); float c=dot(ro,ro)-r*r; float d=b*b-c; if(d<0.) return vec2(-1); d=sqrt(d); return vec2(-b-d,-b+d); }
void main(){
  float phi = (vUV.x - 0.5) * 2.0 * PI; float th = vUV.y * PI;
  vec3 rd = vec3(sin(th)*sin(phi), cos(th), -sin(th)*cos(phi));
  vec3 ro = vec3(0, Re + uCamH, 0);
  // below horizon: look at slightly above horizon (ground handled elsewhere)
  vec3 rdd = rd; if (rdd.y < 0.02) { rdd.y = 0.02 + (0.02 - rdd.y) * 0.02; rdd = normalize(rdd); }
  vec2 ta = raySphere(ro, rdd, Ra); float tmax = ta.y;
  vec2 tg = raySphere(ro, rdd, Re); if (tg.x > 0.0) tmax = min(tmax, tg.x);
  vec3 bM = vec3(uMie);
  int N = 32; float seg = tmax / float(N); float t = 0.0;
  vec3 sumR = vec3(0), sumM = vec3(0), msR = vec3(0), msM = vec3(0); float odR = 0., odM = 0.;
  float mu = dot(rdd, uSunDir); float g = 0.76;
  float pR = 3.0/(16.0*PI)*(1.0+mu*mu);
  float pM = 3.0/(8.0*PI)*((1.0-g*g)*(1.0+mu*mu))/((2.0+g*g)*pow(1.0+g*g-2.0*g*mu,1.5));
  for (int i=0;i<N;i++){
    vec3 p = ro + rdd * (t + seg*0.5); float h = length(p) - Re;
    float hr = exp(-h/Hr)*seg, hm = exp(-h/Hm)*seg; odR += hr; odM += hm;
    vec2 tl = raySphere(p, uSunDir, Ra); float sl = tl.y / 8.0; float odlR=0., odlM=0.; bool ok=true;
    for (int j=0;j<8;j++){ vec3 q = p + uSunDir*(sl*(float(j)+0.5)); float hq = length(q)-Re; if(hq<0.){ok=false;break;} odlR += exp(-hq/Hr)*sl; odlM += exp(-hq/Hm)*sl; }
    if (ok) { vec3 tau = (bR + bO)*(odR+odlR) + bM*1.1*(odM+odlM); vec3 att = exp(-tau); sumR += att*hr; sumM += att*hm; }
    vec3 tv = exp(-((bR + bO)*odR + bM*1.1*odM)); msR += tv*hr; msM += tv*hm;
    t += seg;
  }
  vec3 col = (sumR*bR*pR + sumM*bM*pM) * uSunI;
  // approximate multiple scattering: isotropic in-scatter of skylight
  float sunUp = clamp(uSunDir.y * 1.2 + 0.08, 0.0, 1.0);
  col += (msR*bR + msM*bM*0.9) * uSunI * 0.055 * sunUp;
  o = vec4(col, 1.0);
}`;

export const FS_VERT = `
layout(location=0) in vec3 aPos; out vec2 vUV;
void main(){ vUV = aPos.xy * 0.5 + 0.5; gl_Position = vec4(aPos.xy, 0.0, 1.0); }`;
