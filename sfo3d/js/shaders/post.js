export const POST_VS = `
layout(location=0) in vec3 aPos; out vec2 vUV;
void main(){ vUV = aPos.xy * 0.5 + 0.5; gl_Position = vec4(aPos.xy, 0.0, 1.0); }`;

export const MBLUR_FS = `
in vec2 vUV; out vec4 o;
uniform sampler2D uColor; uniform sampler2D uAux; uniform vec2 uTexel; uniform float uShutter; uniform float uMaxPx;
float hash12(vec2 p){ vec3 p3 = fract(vec3(p.xyx) * .1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
void main(){
  vec4 aux = texture(uAux, vUV);
  vec2 v = aux.gb * uShutter;
  vec2 vpx = v / uTexel; float l = length(vpx);
  if (l > uMaxPx) v *= uMaxPx / l;
  if (l < 0.6) { o = texture(uColor, vUV); return; }
  vec3 acc = vec3(0); float wsum = 0.0;
  const int N = 10; float j = hash12(gl_FragCoord.xy) - 0.5;
  float d0 = aux.r;
  for (int i = 0; i < N; i++) {
    float t = (float(i) + 0.5 + j) / float(N) - 0.5;
    vec2 uv = vUV - v * t;
    vec4 a2 = texture(uAux, uv);
    // avoid smearing stationary background over moving foreground: weight by depth & velocity similarity
    float w = 1.0;
    if (a2.r > d0 * 1.05) w = clamp(length(a2.gb) / max(length(aux.gb), 1e-5), 0.0, 1.0) * 0.8 + 0.2;
    acc += texture(uColor, uv).rgb * w; wsum += w;
  }
  o = vec4(acc / wsum, 1.0);
}`;

export const DOWN_FS = `
in vec2 vUV; out vec4 o; uniform sampler2D uSrc; uniform vec2 uTexel; uniform float uFirst;
vec3 s(vec2 uv){ vec3 c = texture(uSrc, uv).rgb; return c; }
void main(){
  vec2 t = uTexel;
  vec3 a = s(vUV + t * vec2(-2, 2)), b = s(vUV + t * vec2(0, 2)), c = s(vUV + t * vec2(2, 2));
  vec3 d = s(vUV + t * vec2(-2, 0)), e = s(vUV), f = s(vUV + t * vec2(2, 0));
  vec3 g = s(vUV + t * vec2(-2, -2)), h = s(vUV + t * vec2(0, -2)), i = s(vUV + t * vec2(2, -2));
  vec3 j = s(vUV + t * vec2(-1, 1)), k = s(vUV + t * vec2(1, 1)), l = s(vUV + t * vec2(-1, -1)), m = s(vUV + t * vec2(1, -1));
  vec3 r = e * 0.125 + (a + c + g + i) * 0.03125 + (b + d + f + h) * 0.0625 + (j + k + l + m) * 0.125;
  if (uFirst > 0.5) { float lum = dot(r, vec3(0.2126, 0.7152, 0.0722)); r *= 1.0 / (1.0 + lum * 0.02); r = min(r, vec3(3000.0)); }
  o = vec4(r, 1.0);
}`;

export const UP_FS = `
in vec2 vUV; out vec4 o; uniform sampler2D uSrc; uniform sampler2D uBase; uniform vec2 uTexel; uniform float uMix;
void main(){
  vec2 t = uTexel;
  vec3 r = texture(uSrc, vUV).rgb * 4.0;
  r += (texture(uSrc, vUV + vec2(t.x, 0)).rgb + texture(uSrc, vUV - vec2(t.x, 0)).rgb + texture(uSrc, vUV + vec2(0, t.y)).rgb + texture(uSrc, vUV - vec2(0, t.y)).rgb) * 2.0;
  r += texture(uSrc, vUV + t).rgb + texture(uSrc, vUV - t).rgb + texture(uSrc, vUV + vec2(t.x, -t.y)).rgb + texture(uSrc, vUV + vec2(-t.x, t.y)).rgb;
  r /= 16.0;
  o = vec4(texture(uBase, vUV).rgb + r * uMix, 1.0);
}`;

export const FINAL_FS = `
in vec2 vUV; out vec4 o;
uniform sampler2D uColor; uniform sampler2D uBloom; uniform sampler2D uOverlay;
uniform float uExposure; uniform float uBloomMix; uniform float uTime; uniform float uVignette; uniform float uGrain;
uniform vec3 uLift; uniform vec3 uGain; uniform float uSat; uniform float uFade; uniform vec2 uRes;
float hash12(vec2 p){ vec3 p3 = fract(vec3(p.xyx) * .1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
vec3 RRTAndODTFit(vec3 v){ vec3 a = v * (v + 0.0245786) - 0.000090537; vec3 b = v * (0.983729 * v + 0.4329510) + 0.238081; return a / b; }
vec3 ACES(vec3 c){
  const mat3 inM = mat3(0.59719, 0.07600, 0.02840, 0.35458, 0.90834, 0.13383, 0.04823, 0.01566, 0.83777);
  const mat3 outM = mat3(1.60475, -0.10208, -0.00327, -0.53108, 1.10813, -0.07276, -0.07367, -0.00605, 1.07602);
  c = inM * c; c = RRTAndODTFit(c); c = outM * c; return clamp(c, 0.0, 1.0);
}
vec3 toSRGB(vec3 c){ return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(0.0031308, c)); }
void main(){
  vec2 uv = vUV;
  // subtle chromatic aberration at edges
  vec2 dc = uv - 0.5; float r2 = dot(dc, dc);
  vec3 col;
  col.r = texture(uColor, uv - dc * 0.0012 * r2).r;
  col.g = texture(uColor, uv).g;
  col.b = texture(uColor, uv + dc * 0.0012 * r2).b;
  col += texture(uBloom, uv).rgb * uBloomMix;
  col *= uExposure;
  // grade
  col = col * uGain + uLift;
  float l = dot(col, vec3(0.2126, 0.7152, 0.0722)); col = mix(vec3(l), col, uSat);
  col = ACES(col);
  col *= 1.0 - uVignette * smoothstep(0.15, 0.85, r2 * 1.6);
  col = toSRGB(col);
  float g = hash12(gl_FragCoord.xy + fract(uTime * 17.13) * 1000.0) - 0.5;
  col += g * uGrain;
  vec4 ov = texture(uOverlay, vec2(uv.x, 1.0 - uv.y));
  col = mix(col, ov.rgb, ov.a);
  col *= uFade;
  // ordered dither to avoid banding
  col += (hash12(gl_FragCoord.xy * 1.37) - 0.5) / 255.0;
  o = vec4(col, 1.0);
}`;
