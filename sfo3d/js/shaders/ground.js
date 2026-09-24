import { defineChunk } from '../gl.js';

defineChunk('vout', `
uniform mat4 uPrevViewProj; uniform vec3 uPrevCamPos;
out vec4 vClip; out vec4 vPrevClip;
void emitClip(vec3 wp, vec3 prevWp){
  vClip = uViewProj * vec4(wp - uCamPos, 1.0);
  vPrevClip = uPrevViewProj * vec4(prevWp - uPrevCamPos, 1.0);
  gl_Position = vClip;
}`);
defineChunk('fout', `
in vec4 vClip; in vec4 vPrevClip;
layout(location=0) out vec4 oColor;
layout(location=1) out vec4 oAux;
void writeOut(vec3 col, vec3 wp, float alpha){
  oColor = vec4(max(col, vec3(0.0)), alpha);
  vec2 v = vClip.xy / vClip.w - vPrevClip.xy / vPrevClip.w;
  oAux = vec4(length(wp - uCamPos), v * 0.5, alpha);
}`);

export const GROUND_VS = `
#include <common>
#include <vout>
layout(location=0) in vec3 aPos; layout(location=1) in vec3 aNrm;
out vec3 vWP; out vec3 vN;
void main(){ vWP = aPos; vN = aNrm; emitClip(aPos, aPos); }`;

defineChunk('groundfuncs', `
uniform sampler2D uGlyphs; uniform vec4 uRw[4]; uniform vec4 uRwInfo[4]; uniform vec4 uRwEnd[4]; // per end: (type, length) x2; type 1 blast pad, 2 EMAS bed
vec3 grassCol(vec2 p, float fw){
  float n1 = fbm2(p * 0.02, 4), n2 = vnoise(p * 0.25), n3 = vnoise(p * 1.7);
  vec3 dry = vec3(0.50, 0.42, 0.26), dry2 = vec3(0.40, 0.33, 0.20), green = vec3(0.26, 0.30, 0.15);
  vec3 c = mix(dry, dry2, smoothstep(0.3, 0.7, n1));
  c = mix(c, green, smoothstep(0.55, 0.8, fbm2(p * 0.006 + 3.0, 3)) * 0.7);
  float det = 1.0 - smoothstep(0.2, 1.0, fw);
  c *= 0.85 + 0.3 * mix(0.5, n2, det) ;
  c *= 0.92 + 0.16 * mix(0.5, n3, 1.0 - smoothstep(0.05, 0.3, fw));
  return c * 0.85;
}

// ---- runway glyph ----
// glyph atlas stores a signed distance field (0.5 = edge, 1 unit = 64 atlas px); anti-aliased at any distance
float glyph(float code, vec2 uv){
  if (code > 14.5 || uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) return 0.0;
  vec2 t = vec2((code + uv.x) / 16.0, 1.0 - uv.y);
  float d = texture(uGlyphs, t).r - 0.5;
  float w = max(fwidth(d), 1e-3) * 0.75;
  return smoothstep(-w, w, d);
}
float band(float x, float a, float b, float fw){ return smoothstep(a - fw, a + fw, x) - smoothstep(b - fw, b + fw, x); }

// markings for one runway end; x = distance from pavement end inward, y = lateral (to pilot's right)
float endMarkings(float x, float y, float disp, float codes, float fw, float lenTotal){
  float ay = abs(y); float m = 0.0;
  float xt = x - disp;
  // displaced threshold (layout measured on the SFO 28L/28R imagery): 10 ft threshold bar; a row of four arrowheads
  // at 25 ft and 75 ft either side of the centreline, tips ~2 m before the bar; centreline arrows further out
  if (disp > 1.0 && xt < 0.0) {
    m = max(m, band(xt, -3.05, 0.0, fw) * step(ay, 30.0));
    float xa = -xt - 5.0; // distance behind the arrowhead tips
    if (xa > 0.0 && xa < 12.0) {
      float hw = 2.3 * xa / 12.0; float yy = min(abs(ay - 7.62), abs(ay - 22.86));
      m = max(m, 1.0 - smoothstep(hw - fw, hw + fw, yy));
    }
    // centreline arrows: head 12 m, shaft 15 m x 0.9 m, first tip 25 m before the bar, then every 55 m
    float xr = -xt - 25.0;
    if (xr > 0.0 && x > 20.0) {
      float k = floor(xr / 55.0); float xl = xr - k * 55.0;
      if (x - (27.0 - xl) > 12.0 || k < 0.5) {
        if (xl < 12.0) { float hw = 2.3 * xl / 12.0; m = max(m, 1.0 - smoothstep(hw - fw, hw + fw, ay)); }
        else if (xl < 27.0) m = max(m, band(ay, -1.0, 0.45, fw) * band(xl, 12.0, 27.0, fw));
      }
    }
  }
  // threshold markings (AC 150/5340-1M 2.5.5): 16 stripes for a 200 ft runway, 150 ft long, 5.75 ft wide with
  // 5.75 ft gaps; the two stripes nearest the centreline are double spaced (11.5 ft between their inner edges)
  if (xt > 6.1 && xt < 51.8) {
    float k = floor((ay - 1.75) / 3.5); float f = ay - 1.75 - k * 3.5;
    if (k >= 0.0 && k < 8.0) m = max(m, band(f, 0.0, 1.75, fw) * band(xt, 6.1, 51.8, fw));
  }
  // designation: letter then number
  float l = floor(codes / 256.0), d1 = floor(mod(codes, 256.0) / 16.0), d2 = mod(codes, 16.0);
  if (xt > 60.0 && xt < 118.0) {
    if (l < 14.5) m = max(m, glyph(l, vec2((y + 3.6) / 7.2, (xt - 64.0) / 18.3)));
    float gy = (xt - 94.5) / 18.3;
    if (d2 > 14.5) m = max(m, glyph(d1, vec2((y + 3.6) / 7.2, gy)));
    else { m = max(m, glyph(d1, vec2((y + 8.8) / 7.2, gy))); m = max(m, glyph(d2, vec2((y - 1.6) / 7.2, gy))); }
  }
  // aiming point (2.6): begins 1,020 ft from the threshold, 150 ft long, 30 ft wide
  m = max(m, band(xt, 310.9, 356.6, fw) * band(ay, 11.0, 20.1, fw));
  // touchdown zone bars
  for (int i = 0; i < 5; i++) {
    float x0 = i == 0 ? 152.4 : (i == 1 ? 457.2 : (i == 2 ? 609.6 : (i == 3 ? 762.0 : 914.4)));
    float nb = i == 0 ? 3.0 : (i < 3 ? 2.0 : 1.0);
    if (xt > x0 && xt < x0 + 22.9) {
      float f = ay - 10.7; float k = floor(f / 3.35); float ff = f - k * 3.35;
      if (k >= 0.0 && k < nb) m = max(m, band(ff, 0.0, 1.83, fw) * band(xt, x0, x0 + 22.9, fw));
    }
  }
  return m;
}

// returns: x = paint mask, y = rubber amount, z = runway flag
vec3 runwayAt(vec2 st, float fw, out vec2 local){
  for (int i = 0; i < 4; i++) {
    vec4 r = uRw[i]; vec4 info = uRwInfo[i];
    float u = r.x < 0.5 ? st.x : st.y, v = r.x < 0.5 ? st.y : st.x;
    float dv = v - r.y;
    vec4 ez = uRwEnd[i];
    // beyond the pavement ends: blast pad (yellow chevrons, 45 deg, apex towards the runway, 3 ft wide; demarcation
    // bar at the end) or EMAS bed setback (plain pavement; the bed itself is 3D geometry)
    if (abs(dv) < 30.48 && ((u <= r.z && u > r.z - ez.y && ez.x > 0.5) || (u >= r.w && u < r.w + ez.w && ez.z > 0.5))) {
      bool atA = u <= r.z; float xb = atA ? r.z - u : u - r.w; float typ = atA ? ez.x : ez.z;
      float m = 0.0;
      if (typ < 1.5) {
        float q = xb - abs(dv) - 15.0; float k = floor(q / 29.7 + 0.5); float f = q - k * 29.7;
        if (k >= 0.0) m = max(m, 1.0 - smoothstep(0.64 - fw, 0.64 + fw, abs(f)));
        m = max(m, band(xb, 0.0, 0.91, fw));
        m *= band(abs(dv), -1.0, 29.9, fw);
      }
      local = vec2(u, dv);
      return vec3(m, 0.0, typ < 1.5 ? 2.0 : 3.0);
    }
    if (abs(dv) < 30.48 && u > r.z && u < r.w) {
      float L = r.w - r.z;
      float x0 = u - r.z, x1 = r.w - u;
      float y0 = r.x < 0.5 ? -dv : dv; float y1 = -y0;
      float m = 0.0;
      if (x0 < L * 0.5) m = endMarkings(x0, y0, info.x, info.z, fw, L); else m = endMarkings(x1, y1, info.y, info.w, fw, L);
      // centerline
      float xc = x0 - 120.0 - info.x;
      if (x0 > 120.0 + info.x && x1 > 120.0 + info.y) m = max(m, band(abs(dv), -1.0, 0.45, fw) * band(fract(xc / 60.96) * 60.96, 0.0, 36.58, fw));
      // edge stripes
      m = max(m, band(abs(dv), 29.27, 30.18, fw));
      // rubber in touchdown zones (landing ends: 28s => x1 side)
      float rub = 0.0;
      float xl = i < 2 ? x1 - info.y : x0 - info.x;
      rub = smoothstep(80.0, 250.0, xl) * (1.0 - smoothstep(700.0, 1300.0, xl)) * (1.0 - smoothstep(6.0, 14.0, abs(dv)));
      rub *= 0.6 + 0.4 * vnoise(vec2(u * 0.05, dv * 1.3));
      local = vec2(u, dv);
      return vec3(m, rub, 1.0);
    }
  }
  local = vec2(0);
  return vec3(0.0);
}

// ---------------- urban procedural -------------------
// returns albedo; h = height of feature for fake shadow; kind 0 ground,1 roof,2 tree
struct UrbanS { vec3 col; float h; float kind; vec3 nrm; };
UrbanS urbanSample(vec2 xz, float fw, float dens){
  UrbanS o; o.nrm = vec3(0,1,0); o.h = 0.0; o.kind = 0.0;
  // neighborhood zones with smoothly varying orientation (quantized per zone)
  ivec2 zc = ivec2(floor(xz / 1100.0 + vec2(0.37, 0.61)));
  float ang = 0.46 + (ihashf(zc, 3) - 0.5) * 0.7;
  float ca = cos(ang), sa = sin(ang);
  vec2 q = vec2(ca * xz.x + sa * xz.y, -sa * xz.x + ca * xz.y);
  float bx = 86.0 + 20.0 * ihashf(zc, 5), by = 150.0 + 70.0 * ihashf(zc, 6);
  bool commercial = ihashf(zc, 9) < 0.12 || dens < 0.55;
  vec2 cell = floor(q / vec2(bx, by)); vec2 f = q - cell * vec2(bx, by);
  float sw = 10.5;
  vec3 asphalt = vec3(0.13, 0.13, 0.135), sidewalk = vec3(0.3, 0.29, 0.27);
  ivec2 bc = ivec2(cell) + zc * 1000;
  // occasional park block
  if (ihashf(bc, 41) < 0.05) { o.col = mix(vec3(0.16, 0.2, 0.08), vec3(0.3, 0.3, 0.17), ihashf(bc, 42)); if (ihashf(ivec2(floor(xz / 7.0)), 43) < 0.3) { o.col = vec3(0.07, 0.1, 0.045); o.kind = 2.0; o.h = 9.0; } return o; }
  if (f.x < sw || f.y < sw) {
    float e = min(f.x, f.y);
    o.col = (e < 1.5 || e > sw - 1.5) ? sidewalk : asphalt;
    if ((e < 2.8 || e > sw - 2.8) && ihashf(ivec2(floor(xz / 8.0)), 31) < 0.55) { o.col = vec3(0.075, 0.1, 0.045); o.kind = 2.0; o.h = 8.0; }
    return o;
  }
  if (commercial) {
    vec2 g = f - sw; vec2 bs = vec2(bx, by) - sw;
    float split = 0.35 + 0.35 * ihashf(bc, 1);
    bool bldg = ihashf(bc, 2) < 0.8;
    vec2 lo = vec2(3.0, 3.0), hi = vec2(bs.x - 3.0, bs.y * split);
    if (bldg && g.x > lo.x && g.x < hi.x && g.y > lo.y && g.y < hi.y) {
      o.kind = 1.0; o.h = 7.0 + 12.0 * ihashf(bc, 3);
      float t = ihashf(bc, 4); o.col = mix(vec3(0.46, 0.46, 0.45), vec3(0.26, 0.26, 0.27), t);
      vec2 hv = fract(g / 9.0); if (ihashf(ivec2(floor(g / 9.0)) + bc, 8) < 0.12 && hv.x > 0.3 && hv.x < 0.7 && hv.y > 0.3 && hv.y < 0.7) o.col *= 0.75;
      return o;
    }
    o.col = vec3(0.19, 0.19, 0.195);
    float stripe = step(0.93, fract(g.x / 2.8)) * step(0.3, fract(g.y / 12.0)); o.col = mix(o.col, vec3(0.6), stripe * 0.5);
    vec2 cc = floor(vec2(g.x / 2.8, g.y / 6.0)); float hc = ihashf(ivec2(cc) + bc, 12); vec2 cf = fract(vec2(g.x / 2.8, g.y / 6.0));
    if (hc < 0.55 && cf.x > 0.18 && cf.x < 0.82 && cf.y > 0.15 && cf.y < 0.85 && mod(cc.y, 2.0) < 1.0) { o.col = mix(vec3(0.75), vec3(0.08, 0.09, 0.12), ihashf(ivec2(cc) + bc, 13)); o.kind = 1.0; o.h = 1.4; }
    if (ihashf(ivec2(floor(xz / 10.0)), 44) < 0.08) { o.col = vec3(0.07, 0.1, 0.045); o.kind = 2.0; o.h = 7.0; }
    return o;
  }
  // residential lots
  float half_ = (bx - sw) * 0.5;
  float gx = f.x - sw; float side = gx < half_ ? 0.0 : 1.0;
  float lx = side < 0.5 ? gx : (bx - sw) - gx; // depth from street
  float lotW = 12.5 + 3.5 * ihashf(bc, 21);
  float li = floor((f.y - sw) / lotW); float ly = (f.y - sw) - li * lotW;
  ivec2 lc = bc * 64 + ivec2(int(li), int(side));
  float hd = 13.0 + 7.0 * ihashf(lc, 1); float hw = lotW - 2.6 - 1.5 * ihashf(lc, 2);
  float setback = 4.5 + 3.0 * ihashf(lc, 3);
  float r0 = ihashf(lc, 4);
  vec3 lawn = mix(vec3(0.15, 0.18, 0.08), vec3(0.33, 0.29, 0.18), ihashf(lc, 5));
  o.col = lawn;
  if (ly > lotW - 3.6 && ly < lotW - 0.6 && lx < setback + 1.0) o.col = vec3(0.42, 0.41, 0.39);
  if (lx > setback && lx < setback + hd && ly > 1.2 && ly < 1.2 + hw) {
    o.kind = 1.0; o.h = 5.0 + 3.5 * ihashf(lc, 6);
    vec3 roofs[8] = vec3[](vec3(0.3, 0.29, 0.28), vec3(0.46, 0.27, 0.19), vec3(0.42, 0.41, 0.39), vec3(0.2, 0.2, 0.21), vec3(0.52, 0.33, 0.22), vec3(0.36, 0.34, 0.31), vec3(0.25, 0.24, 0.24), vec3(0.55, 0.5, 0.44));
    o.col = roofs[int(r0 * 7.99)];
    float u = (ly - 1.2) / hw - 0.5; float tilt = u > 0.0 ? 0.5 : -0.5;
    vec3 dirW = vec3(-sa, 0.0, ca);
    o.nrm = normalize(vec3(dirW.x * tilt, 1.0, dirW.z * tilt));
    return o;
  }
  if (ihashf(lc, 7) < 0.1 && lx > setback + hd + 2.5 && lx < setback + hd + 7.0 && ly > 3.5 && ly < 10.0) { o.col = vec3(0.12, 0.42, 0.5); return o; }
  for (int k = 0; k < 2; k++) {
    vec2 tp = vec2(setback + hd + 3.0 + 12.0 * ihashf(lc, 8 + k * 7), 1.5 + (lotW - 3.0) * ihashf(lc, 9 + k * 7));
    if (k == 1) tp = vec2(1.5 + 2.5 * ihashf(lc, 30), 2.0 + (lotW - 4.0) * ihashf(lc, 31));
    float tr = 2.4 + 2.8 * ihashf(lc, 10 + k * 7);
    if (ihashf(lc, 11 + k * 7) < 0.8 && length(vec2(lx, ly) - tp) < tr) { o.kind = 2.0; o.h = 6.0 + 7.0 * ihashf(lc, 12); o.col = mix(vec3(0.07, 0.1, 0.045), vec3(0.15, 0.18, 0.08), ihashf(lc, 13 + k)); return o; }
  }
  return o;
}
`);

// ---------------- one-time bakes ----------------
export const BAKE_APT_FS = `
#include <common>
#include <groundfuncs>
in vec2 vUV; layout(location=0) out vec4 o;
uniform sampler2D uApt; uniform vec4 uAptRect; uniform vec2 uAptPoly[16]; uniform float uTexel;
uniform sampler2D uPaint; uniform float uHasPaint; // green no-taxi island paint (FS 595 34108), mapped from imagery
float segD(vec2 p, vec2 a, vec2 b){ vec2 pa = p - a, ba = b - a; float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0); return length(pa - ba * h); }
float polySDF(vec2 p){
  float d = 1e9; bool inside = false;
  for (int i = 0; i < 16; i++) { vec2 a = uAptPoly[i], b = uAptPoly[(i + 1) % 16]; d = min(d, segD(p, a, b));
    if (((a.y > p.y) != (b.y > p.y)) && (p.x < (b.x - a.x) * (p.y - a.y) / (b.y - a.y) + a.x)) inside = !inside; }
  return inside ? d : -d;
}
void main(){
  vec2 st = vec2(uAptRect.x + vUV.x * uAptRect.z, uAptRect.y + (1.0 - vUV.y) * uAptRect.w);
  vec4 apt = texture(uApt, vec2(vUV.x, vUV.y));
  float fw = uTexel;
  float sdf = polySDF(st);
  vec3 g = grassCol(st, fw) * (0.94 + 0.06 * step(0.5, fract(st.x / 24.0)));
  // dirt near pavement edges / service roads
  float n1 = fbm2(st * 0.013, 3); float n2 = vnoise(st * 0.6);
  vec3 asph = vec3(0.13, 0.13, 0.135) * (0.85 + 0.3 * n1) * (0.93 + 0.14 * n2);
  vec2 pc = floor(st / vec2(37.0, 23.0)); if (ihashf(ivec2(pc), 3) < 0.12) asph *= 1.2;
  vec3 conc = vec3(0.42, 0.41, 0.38) * (0.88 + 0.2 * n1);
  vec2 slab = floor(st / 7.62); conc *= 0.965 + 0.06 * ihashf(ivec2(slab), 5);
  conc *= 0.85 + 0.3 * fbm2(st * 0.004 + 7.0, 4); conc *= 1.0 - 0.12 * smoothstep(0.55, 0.8, fbm2(st * 0.03, 3));
  vec2 jf = abs(fract(st / 7.62 + 0.5) - 0.5) * 7.62;
  float joint = (1.0 - smoothstep(0.0, fw * 0.6, min(jf.x, jf.y))) * 0.03 / fw;
  conc *= 1.0 - 0.25 * clamp(joint, 0.0, 1.0);
  // stains
  conc *= 1.0 - 0.18 * smoothstep(0.6, 0.9, vnoise(st * 0.15)) * vnoise(st * 1.3);
  vec3 pav = mix(asph, conc, apt.g);
  pav *= 1.0 - apt.b * (0.5 + 0.3 * vnoise(st * 0.3));
  if (apt.a > 0.8) pav = mix(pav, vec3(0.17, 0.17, 0.18) * (0.9 + 0.2 * n1), 0.85);
  else if (apt.a > 0.4) {
    vec3 lot = vec3(0.19, 0.19, 0.2) * (0.9 + 0.2 * n1);
    vec2 g2 = vec2(st.x / 2.7, st.y / 5.6); vec2 cf = fract(g2); vec2 cc = floor(g2);
    float row = step(1.0, mod(cc.y, 3.0));
    lot = mix(lot, vec3(0.75), row * step(0.94, cf.x) * 0.7);
    float occ = step(ihashf(ivec2(cc), 17), 0.7) * row;
    float car = occ * step(0.14, cf.x) * step(cf.x, 0.86) * step(0.1, cf.y) * step(cf.y, 0.9);
    vec3 carCol = mix(vec3(0.82), vec3(0.07, 0.08, 0.1), ihashf(ivec2(cc), 18)); if (ihashf(ivec2(cc), 19) > 0.85) carCol = vec3(0.5, 0.07, 0.05);
    pav = mix(lot, carCol, car);
  }
  if (uHasPaint > 0.5) { float gp = texture(uPaint, vUV).r; vec3 green = vec3(0.075, 0.2, 0.105) * (0.9 + 0.2 * n1) * (0.95 + 0.1 * n2); pav = mix(pav, green, gp * 0.95); }
  vec3 col = mix(g, pav, apt.r);
  float cover = max(apt.r, smoothstep(-1.0, 1.0, sdf));
  o = vec4(col, cover);
}`;
export const BAKE_AUX_FS = `
in vec2 vUV; layout(location=0) out vec4 o;
uniform vec4 uAptRect; uniform vec2 uAptPoly[16]; uniform sampler2D uApt;
float segD(vec2 p, vec2 a, vec2 b){ vec2 pa = p - a, ba = b - a; float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0); return length(pa - ba * h); }
void main(){
  vec2 st = vec2(uAptRect.x + vUV.x * uAptRect.z, uAptRect.y + (1.0 - vUV.y) * uAptRect.w);
  float d = 1e9; bool inside = false;
  for (int i = 0; i < 16; i++) { vec2 a = uAptPoly[i], b = uAptPoly[(i + 1) % 16]; d = min(d, segD(st, a, b));
    if (((a.y > st.y) != (b.y > st.y)) && (st.x < (b.x - a.x) * (st.y - a.y) / (b.y - a.y) + a.x)) inside = !inside; }
  float sdf = inside ? d : -d;
  vec4 apt = texture(uApt, vUV);
  o = vec4(clamp(-sdf / 40.0, 0.0, 1.0), clamp(sdf / 40.0 * 0.5 + 0.5, 0.0, 1.0), apt.r * apt.g * (1.0 - step(0.3, apt.a)), 1.0);
}`;
export const BAKE_CITY_FS = `
#include <common>
#include <groundfuncs>
in vec2 vUV; layout(location=0) out vec4 o;
uniform vec4 uCityRect; uniform sampler2D uRegion; uniform vec4 uRegionRect; uniform float uTexel;
void main(){
  vec2 xz = uCityRect.xy + vUV * uCityRect.zw;
  vec4 reg = texture(uRegion, (xz - uRegionRect.xy) / uRegionRect.zw);
  vec3 acc = vec3(0); float sh = 0.0; vec3 nacc = vec3(0);
  // 2x2 supersample
  for (int k = 0; k < 4; k++) {
    vec2 p = xz + (vec2(k & 1, k >> 1) - 0.5) * uTexel * 0.5;
    UrbanS u = urbanSample(p, uTexel * 0.5, reg.g);
    float s = 1.0;
    if (u.kind < 0.5) {
      vec2 sd = -uSunDir.xz / max(uSunDir.y, 0.15);
      UrbanS s1 = urbanSample(p - sd * 3.0, 1.0, reg.g); UrbanS s2 = urbanSample(p - sd * 6.5, 1.0, reg.g);
      s = 1.0 - 0.75 * max(step(3.0, s1.h), step(6.5, s2.h));
    } else if (u.kind > 0.5 && u.kind < 1.5) {
      // roof slope shading baked (sun fixed)
      s = clamp(dot(u.nrm, uSunDir) / max(uSunDir.y, 0.2), 0.55, 1.25);
    }
    acc += u.col * s;
  }
  o = vec4(acc / 4.0, 1.0);
}`;

export const BAKE_CITYFAR_FS = `
#include <common>
#include <groundfuncs>
in vec2 vUV; layout(location=0) out vec4 o;
uniform vec4 uCityRect; uniform sampler2D uRegion; uniform vec4 uRegionRect; uniform float uTexel;
void main(){
  vec2 xz = uCityRect.xy + vUV * uCityRect.zw;
  vec4 reg = texture(uRegion, (xz - uRegionRect.xy) / uRegionRect.zw);
  vec3 acc = vec3(0);
  for (int k = 0; k < 16; k++) {
    vec2 p = xz + (vec2(k & 3, k >> 2) + 0.5 - 2.0) * uTexel * 0.25 + (hash22(vec2(k, 1.0) + xz) - 0.5) * uTexel * 0.25;
    UrbanS u = urbanSample(p, 1.0, reg.g);
    float s = u.kind > 1.5 ? 0.8 : (u.kind > 0.5 ? clamp(dot(u.nrm, uSunDir) / max(uSunDir.y, 0.2), 0.6, 1.2) : 0.85);
    acc += u.col * s;
  }
  o = vec4(acc / 16.0, 1.0);
}`;

// ---------------- per-frame light ground shader ----------------
export const GROUND_FS = `
#include <common>
#include <shadow>
#include <fout>
#include <groundfuncs>
in vec3 vWP; in vec3 vN;
uniform sampler2D uRegion; uniform vec4 uRegionRect;
uniform sampler2D uAptAlb; uniform sampler2D uAptAux; uniform vec4 uAptRect;
uniform sampler2D uCity; uniform vec4 uCityRect; uniform sampler2D uCityFar; uniform vec4 uCityFarRect;
uniform vec2 uVw; uniform vec2 uUw; uniform float uNight;
// night: street lights (city), high-mast floodlights (airport ramps)
vec3 nightLight(vec2 xz, vec2 st, float fw, float urb, float ramp, float pave, vec3 albedo){
  vec3 nl = vec3(0.0);
  if (urb > 0.01) {
    const float S = 34.0;
    vec2 g = xz / S; vec2 c = floor(g); vec2 f = fract(g) - 0.5;
    float h = hash12(c * 1.37 + 11.0);
    vec2 off = (vec2(hash12(c + 3.1), hash12(c + 7.7)) - 0.5) * 0.7;
    float d = length(f - off) * S;
    float r = 2.5 + 1.5 * fw;
    float spot = exp(-d * d / (r * r)) * step(0.3, h);
    float avg = 0.7 * 3.1416 * r * r / (S * S);
    float k = smoothstep(3.0, 14.0, fw);
    float lum = mix(spot * (0.6 + 0.8 * h), avg, k) + 0.08;
    vec3 lc = mix(vec3(1.0, 0.6, 0.3), vec3(0.95, 0.92, 0.88), step(0.72, h));
    nl += lc * lum * urb * 5.0;
    nl += albedo * vec3(1.0, 0.8, 0.6) * 0.9 * urb;
  }
  if (ramp > 0.01 || pave > 0.01) {
    const float S2 = 90.0;
    vec2 g = st / S2; vec2 c = floor(g + 0.5); float pool = 0.0;
    for (int i = -1; i <= 1; i++) for (int j = -1; j <= 1; j++) {
      vec2 cc = c + vec2(i, j); vec2 o = (vec2(hash12(cc + 5.3), hash12(cc + 9.1)) - 0.5) * 0.5;
      float d = length(g - cc - o) * S2; pool += exp(-d * d / (38.0 * 38.0));
    }
    float E = ramp * (0.45 + 0.9 * min(pool, 1.5)) + pave * (1.0 - ramp) * 0.05;
    nl += albedo * vec3(1.0, 0.9, 0.78) * E * 2.2;
  }
  return nl;
}
void main(){
  vec3 wp = vWP; vec3 V = uCamPos - wp; float dist = length(V); V /= dist;
  vec3 N = normalize(vN);
  vec2 st = vec2(dot(wp.xz, uVw), dot(wp.xz, uUw));
  float fw = length(fwidth(wp.xz)) * 0.7 + 0.001;
  vec4 reg = texture(uRegion, (wp.xz - uRegionRect.xy) / uRegionRect.zw);
  vec4 nzA = texture(uNoise, wp.xz * (1.0 / 2300.0));
  vec4 nzB = texture(uNoise, wp.xz * (1.0 / 170.0));
  float h = wp.y;
  // natural terrain
  vec3 hillDry = mix(vec3(0.46, 0.38, 0.24), vec3(0.36, 0.29, 0.18), nzA.g);
  vec3 scrub = vec3(0.11, 0.135, 0.07);
  float slope = 1.0 - N.y; float north = -N.z;
  float forest = clamp(reg.b + (nzA.b - 0.5) * 1.2 + north * 0.9 + slope * 0.8 - 0.25, 0.0, 1.0);
  forest = smoothstep(0.35, 0.65, forest) * smoothstep(8.0, 60.0, h);
  vec3 albedo = mix(hillDry, scrub, forest) * (0.85 + 0.3 * nzB.r);
  float shore = 1.0 - smoothstep(0.4, 2.2, h);
  albedo = mix(albedo, vec3(0.19, 0.17, 0.13), shore);
  vec2 auv = (st - uAptRect.xy) / uAptRect.zw; auv.y = 1.0 - auv.y;
  bool inApt = auv.x > 0.0 && auv.x < 1.0 && auv.y > 0.0 && auv.y < 1.0;
  vec4 aptA = inApt ? texture(uAptAlb, auv) : vec4(0.0);
  // urban
  float urb = reg.g * (1.0 - smoothstep(110.0, 180.0, h + 60.0 * nzA.r)) * (1.0 - shore) * (1.0 - aptA.a);
  if (urb > 0.01) {
    vec2 cuv = (wp.xz - uCityRect.xy) / uCityRect.zw;
    vec3 far = vec3(0.2, 0.19, 0.175) * (0.75 + 0.5 * nzB.g) * (0.85 + 0.3 * nzA.a);
    vec2 fuv = (wp.xz - uCityFarRect.xy) / uCityFarRect.zw;
    if (fuv.x > 0.0 && fuv.x < 1.0 && fuv.y > 0.0 && fuv.y < 1.0) far = texture(uCityFar, fuv).rgb;
    vec3 cc = far;
    if (cuv.x > 0.0 && cuv.x < 1.0 && cuv.y > 0.0 && cuv.y < 1.0) { vec3 c = texture(uCity, cuv).rgb; float e = min(min(cuv.x, cuv.y), min(1.0 - cuv.x, 1.0 - cuv.y)); cc = mix(far, c, smoothstep(0.0, 0.04, e)); }
    albedo = mix(albedo, cc, urb);
  }
  albedo = mix(albedo, vec3(0.17, 0.17, 0.18), reg.a * (1.0 - aptA.a) * 0.9);
  float rough = 0.95; vec2 local = vec2(0); vec3 rw = vec3(0);
  if (inApt) {
    albedo = mix(albedo, aptA.rgb, aptA.a);
    // riprap on the seawall slope
    float rip = (1.0 - smoothstep(1.6, 2.7, h)) * smoothstep(-3.0, -1.0, h) * (1.0 - reg.g * 0.0);
    if (rip > 0.0) { float rk = texture(uNoise, st * 0.35).r * 0.6 + texture(uNoise, st * 1.1).g * 0.4; albedo = mix(albedo, vec3(0.3, 0.28, 0.26) * (0.5 + 0.8 * rk), rip * aptA.a); }
    // runways (procedural markings)
    rw = runwayAt(st, fw, local);
    if (rw.z > 1.5) {
      float n1 = texture(uNoise, local * vec2(0.0012, 0.02)).b; float n2 = texture(uNoise, local * vec2(0.02, 0.5)).r;
      vec3 asph = vec3(0.105, 0.108, 0.118) * (0.8 + 0.4 * n1) * (0.94 + 0.12 * n2);
      vec3 yel = vec3(0.62, 0.42, 0.06) * (0.85 + 0.15 * n2);
      albedo = mix(asph, yel, rw.x); rough = mix(0.85, 0.65, rw.x);
    } else if (rw.z > 0.5) {
      float n1 = texture(uNoise, local * vec2(0.0012, 0.02)).b; float n2 = texture(uNoise, local * vec2(0.02, 0.5)).r;
      vec3 asph = vec3(0.12, 0.12, 0.125) * (0.8 + 0.4 * n1) * (0.94 + 0.12 * n2);
      asph *= 0.95 + 0.08 * smoothstep(8.0, 20.0, abs(local.y));
      asph *= 1.0 - rw.y * 0.62;
      vec3 paint = vec3(0.74, 0.74, 0.72) * (0.88 + 0.12 * n2);
      paint = mix(paint, asph, rw.y * 0.7);
      albedo = mix(asph, paint, rw.x);
      rough = mix(0.8, 0.6, rw.x);
    }
  }
  // close-up concrete joints (analytic, anti-aliased)
  float concMask = inApt ? texture(uAptAux, auv).b : 0.0;
  if (dist < 350.0 && concMask > 0.5 && rw.z < 0.5) {
    vec2 jf = abs(fract(st / 7.62 + 0.5) - 0.5) * 7.62; float jw = max(fw, 0.005);
    float joint = (1.0 - smoothstep(0.012, 0.012 + jw, min(jf.x, jf.y))) * min(1.0, 0.025 / jw); // area-correct: thin lines fade instead of widening
    albedo *= 1.0 - 0.3 * joint * (1.0 - smoothstep(60.0, 220.0, dist));
  }
  // close-up detail
  if (dist < 400.0) { float d = texture(uNoise, wp.xz * 0.9).a * 0.6 + texture(uNoise, wp.xz * 3.7).r * 0.4; albedo *= mix(1.0, 0.85 + 0.3 * d, 1.0 - smoothstep(100.0, 400.0, dist)); }
  float sh = getShadow(wp, N, dist) * cloudShadow(wp);
  float NoL = max(dot(N, uSunDir), 0.0);
  float up = N.y * 0.5 + 0.5;
  vec3 amb = mix(uSkyHorizon, uSkyUp, up);
  vec3 col = albedo / PI * uSunColor * NoL * sh + albedo * amb;
  // faint specular sheen on pavement at grazing sun
  vec3 H = normalize(uSunDir + V); float spec = D_GGX(max(dot(N, H), 0.0), rough) * 0.03 * NoL * sh;
  col += uSunColor * spec * (1.0 - rough) * 2.0;
  if (uNight > 0.001) {
    float urbN = reg.g * (1.0 - smoothstep(110.0, 180.0, h + 60.0 * nzA.r)) * (1.0 - shore) * (1.0 - aptA.a);
    col += nightLight(wp.xz, st, fw, urbN, concMask, inApt ? aptA.a : 0.0, albedo) * uNight;
  }
  col = applyFog(col, wp);
  writeOut(col, wp, 1.0);
}`;
