// ------------------------------------------------------------------
// GLSL programs
// ------------------------------------------------------------------
const SH = {};

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
uniform vec3 u_hemiTop; uniform vec3 u_hemiBot; uniform vec3 u_wash; uniform vec3 u_led; uniform vec3 u_winGlow;
uniform sampler3D u_ao; uniform vec3 u_aoMin; uniform vec3 u_aoSize;
uniform sampler2DArray u_detail; uniform vec4 u_layer[20];
uniform sampler2D u_atlas; uniform float u_screenStep; uniform float u_emisGain; uniform float u_screenGain;
uniform sampler2D u_win; uniform vec2 u_winZ;
uniform float u_R; uniform float u_yc;
uniform float u_exposure; uniform float u_exterior;
uniform vec3 u_skyTop; uniform vec3 u_skyBot;
uniform float u_detailOn;
out vec4 o;

vec3 toLin(vec3 c){ return c*c*(c*0.31+0.69); }
vec3 aces(vec3 x){ return clamp((x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14), 0.0, 1.0); }

float shadowF(vec3 wp, vec3 n){
  vec3 p = (u_shadowMat * vec4(wp + n*0.028, 1.0)).xyz * 0.5 + 0.5;
  if (p.x < 0.0 || p.x > 1.0 || p.y < 0.0 || p.y > 1.0 || p.z > 1.0) return 1.0;
  float z = p.z - 0.0004;
  vec2 t = u_shadowTexel;
  float s = texture(u_shadow, vec3(p.xy + vec2(-0.7,-0.7)*t, z))
          + texture(u_shadow, vec3(p.xy + vec2( 0.7,-0.7)*t, z))
          + texture(u_shadow, vec3(p.xy + vec2(-0.7, 0.7)*t, z))
          + texture(u_shadow, vec3(p.xy + vec2( 0.7, 0.7)*t, z));
  return s * 0.25;
}
vec3 windowT(vec3 wp){
  vec2 o2 = vec2(wp.x, wp.y - u_yc); vec2 d = u_sunDir.xy;
  float a = dot(d, d);
  if (a < 1e-5) return vec3(1.0);
  float b = 2.0*dot(o2, d); float c = dot(o2, o2) - u_R*u_R;
  float disc = b*b - 4.0*a*c;
  if (disc < 0.0) return vec3(1.0);
  float t = (-b + sqrt(disc)) / (2.0*a);
  float zh = wp.z + u_sunDir.z * t;
  float xh = o2.x + d.x * t;
  return texture(u_win, vec2((zh - u_winZ.x)/(u_winZ.y - u_winZ.x), xh < 0.0 ? 0.25 : 0.75)).rgb;
}
vec3 envInside(vec3 R){
  float up = smoothstep(-0.25, 0.75, R.y);
  vec3 e = mix(u_hemiBot*0.7, u_hemiTop*1.25, up);
  float side = (1.0 - abs(R.y)) * smoothstep(0.35, 0.95, abs(R.x));
  e += u_winGlow * side * 0.6;
  return e;
}

void main(){
  vec3 base = toLin(v_col.rgb) * v_tint.rgb;
  float rough = v_mat.r, metal = v_mat.g;
  int layer = int(v_mat.b * 255.0 + 0.5);
  float emis = v_mat.a;
  vec3 N = normalize(v_nrm);
  if (!gl_FrontFacing) N = -N;
  vec3 V = normalize(u_camPos - v_wpos);
  vec3 emissive = vec3(0.0);
  float hl = step(0.25, fract(v_tint.a + 0.01));
  if (layer >= 13) {
    vec2 uv = v_uv;
    if (layer == 13) uv.y += floor(v_tint.a + 0.001) * u_screenStep;
    vec3 tc = toLin(texture(u_atlas, uv).rgb);
    if (layer == 14) base *= tc;
    else { emissive = tc * (layer == 13 ? u_screenGain : u_emisGain) * emis * 4.0; base = tc * 0.04; rough = 0.25; }
  } else if (layer == 12) {
    emissive = u_led * emis * 6.0;
    base *= 0.3;
  } else if (layer > 0 && u_detailOn > 0.5) {
    vec4 P = u_layer[layer];
    vec3 w = pow(abs(N), vec3(4.0)); w /= (w.x + w.y + w.z);
    vec3 q = v_wpos * P.x;
    float L = float(layer);
    vec4 tx = texture(u_detail, vec3(q.zy, L));
    vec4 ty = texture(u_detail, vec3(q.xz, L));
    vec4 tz = texture(u_detail, vec3(q.xy, L));
    vec4 t = tx*w.x + ty*w.y + tz*w.z;
    vec2 nx = tx.xy*2.0 - 1.0, ny = ty.xy*2.0 - 1.0, nz = tz.xy*2.0 - 1.0;
    vec3 dn = vec3(0.0, nx.y, nx.x)*w.x + vec3(ny.x, 0.0, ny.y)*w.y + vec3(nz.x, nz.y, 0.0)*w.z;
    N = normalize(N + dn * P.y);
    base *= 1.0 + (t.b - 0.5) * 2.0 * P.z;
    rough = clamp(rough * (1.0 + (t.a - 0.5) * 2.0 * P.w), 0.04, 1.0);
  }
  if (emis > 0.0 && layer < 12) emissive += base * emis * u_emisGain * 3.0;
  // specular anti-aliasing: widen roughness where the normal varies across pixels
  vec3 dNdx = dFdx(N), dNdy = dFdy(N);
  float nvar = 0.25 * (dot(dNdx, dNdx) + dot(dNdy, dNdy));
  rough = sqrt(clamp(rough*rough + min(2.0*nvar, 0.25), 0.0, 1.0));
  rough = max(rough, 0.12);

  float NdV = max(dot(N, V), 1e-3);
  vec3 amb; float ao = 1.0;
  if (u_exterior > 0.5) {
    amb = mix(u_skyBot, u_skyTop, clamp(N.y*0.5 + 0.5, 0.0, 1.0));
  } else {
    vec3 auv = (v_wpos + N*0.07 - u_aoMin) / u_aoSize;
    ao = texture(u_ao, auv).r;
    vec3 hemi = mix(u_hemiBot, u_hemiTop, clamp(N.y*0.5 + 0.5, 0.0, 1.0));
    float wallProx = smoothstep(1.7, 2.55, abs(v_wpos.x));
    float facingIn = clamp(-sign(v_wpos.x) * N.x, 0.0, 1.0);
    amb = hemi * (0.32 + 0.68*ao)
        + u_wash * wallProx * (0.35 + 0.65*facingIn) * smoothstep(0.3, 1.25, v_wpos.y) * (0.45 + 0.55*ao)
        + u_winGlow * wallProx * facingIn * smoothstep(0.7, 1.1, v_wpos.y) * (1.0 - smoothstep(1.5, 1.8, v_wpos.y)) * 0.5;
  }
  vec3 L = u_sunDir;
  float ndl = max(dot(N, L), 0.0);
  vec3 sun = vec3(0.0);
  if (ndl > 0.0 && dot(u_sunCol, u_sunCol) > 0.0) {
    float sh = u_exterior > 0.5 ? 1.0 : shadowF(v_wpos, N);
    vec3 tr = u_exterior > 0.5 ? vec3(1.0) : windowT(v_wpos);
    sun = u_sunCol * ndl * sh * tr;
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
  vec3 env = u_exterior > 0.5 ? mix(u_skyBot, u_skyTop*1.2, smoothstep(-0.2, 0.6, R.y)) : envInside(R) * (0.25 + 0.75*ao);
  vec3 Fe = F0 + (max(vec3(1.0 - rough), F0) - F0) * pow(1.0 - NdV, 5.0);
  vec3 specEnv = env * Fe * (1.0 - rough*0.8);
  vec3 col = diff * (amb + sun) + specSun + specEnv + emissive;
  col += vec3(0.30, 0.62, 1.0) * hl * (0.35 + 0.9*pow(1.0 - NdV, 2.0));
  col = aces(col * u_exposure);
  o = vec4(sqrt(col), 1.0);
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
uniform vec3 u_zenith; uniform vec3 u_horizon; uniform vec3 u_haze; uniform vec3 u_sunTint; uniform float u_night;
uniform vec3 u_cloudLit; uniform vec3 u_cloudShade; uniform float u_exposure; uniform float u_sunVis;
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
    float t = pow(clamp(h, 0.0, 1.0), 0.42);
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
  o = vec4(sqrt(col), 1.0);
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
