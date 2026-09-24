// Airfield guidance signs (lit panels) and surface-painted holding position signs.
//   Runway holding position (mandatory) signs: white inscription on red, e.g. "10R-28L" (left runway end first as seen
//   by the pilot), with an outboard taxiway location sign (yellow on black, yellow border). Painted holding position
//   signs on the pavement before each hold line. Runway distance-remaining signs (white numerals on black) every 1,000 ft.
import { gl, Mesh } from '../gl.js';
import { GROUND_Y } from '../geo.js';

const FT = 0.3048;
export const SIGN_VS = `
#include <common>
#include <vout>
layout(location=0) in vec3 aPos; layout(location=1) in vec3 aNrm; layout(location=2) in vec2 aUV; layout(location=4) in vec4 aExtra;
out vec3 vWP; out vec3 vN; out vec2 vUV; out vec4 vX;
void main(){ vWP = aPos; vN = aNrm; vUV = aUV; vX = aExtra; emitClip(aPos, aPos); }`;
export const SIGN_FS = `
#include <common>
#include <shadow>
#include <fout>
in vec3 vWP; in vec3 vN; in vec2 vUV; in vec4 vX; // vX.x: 1 = sign face (lit), 0 = housing/leg, 2 = painted on pavement
uniform sampler2D uAtlas; uniform float uNight;
void main(){
  vec3 wp = vWP; vec3 V = uCamPos - wp; float dist = length(V); V /= dist;
  vec3 N = normalize(vN); if (dot(N, V) < 0.0) N = -N;
  vec3 alb; float rough = 0.6; vec3 emis = vec3(0);
  if (vX.x > 1.5) { alb = texture(uAtlas, vUV).rgb * (0.8 + 0.2 * texture(uNoise, wp.xz * 0.31).r); rough = 0.7; }
  else if (vX.x > 0.5) { alb = texture(uAtlas, vUV).rgb; rough = 0.35; emis = alb * uNight * 1.6; }
  else { alb = vec3(0.05); rough = 0.5; }
  float sh = getShadow(wp, N, dist) * cloudShadow(wp);
  vec3 col = shadePBR(alb, N, V, rough, 0.0, sh, 1.0, 1.0) + emis;
  col = applyFog(col, wp);
  writeOut(col, wp, 1.0);
}`;

// ---------------------------------------------------------------- texture atlas of sign faces
export function makeAtlas(faces) { // faces: [{key, kind: 'mand'|'loc'|'drs'|'paint'|'gate'|'vdgs', text}]
  const Hf = 96, pad = 4, Wmax = 2048;
  const cv = document.createElement('canvas'); const cx = cv.getContext('2d');
  const font = (px, kind) => kind === 'vdgs' ? `bold ${px}px "Courier New", ui-monospace, monospace` : `bold ${px}px "Arial Narrow", Arial, Helvetica, sans-serif`;
  const place = []; let x = pad, y = pad, rowH = 0;
  for (const f of faces) {
    cx.font = font(f.kind === 'paint' ? 150 : 70, f.kind);
    const tw = cx.measureText(f.text).width;
    const w = Math.ceil(f.kind === 'paint' ? tw + 60 : tw + 44), h = f.kind === 'paint' ? 190 : Hf;
    if (x + w + pad > Wmax) { x = pad; y += rowH + pad; rowH = 0; }
    place.push({ ...f, x, y, w, h }); x += w + pad; rowH = Math.max(rowH, h);
  }
  const Ht = Math.pow(2, Math.ceil(Math.log2(y + rowH + pad)));
  cv.width = Wmax; cv.height = Ht;
  cx.textAlign = 'center'; cx.textBaseline = 'middle';
  for (const f of place) {
    const bg = f.kind === 'mand' || f.kind === 'paint' ? '#b3120f' : f.kind === 'gate' ? '#10151c' : '#0b0b0b', fg = f.kind === 'loc' ? '#f4c21b' : f.kind === 'vdgs' ? '#ffb020' : '#f2f2f2';
    cx.fillStyle = bg; cx.fillRect(f.x, f.y, f.w, f.h);
    if (f.kind === 'loc') { cx.strokeStyle = '#f4c21b'; cx.lineWidth = 6; cx.strokeRect(f.x + 7, f.y + 7, f.w - 14, f.h - 14); }
    if (f.kind === 'paint') { cx.strokeStyle = '#e8b51c'; cx.lineWidth = 10; cx.strokeRect(f.x + 5, f.y + 5, f.w - 10, f.h - 10); }
    cx.fillStyle = fg; cx.font = font(f.kind === 'paint' ? 150 : 70, f.kind);
    if (f.kind === 'vdgs') { cx.shadowColor = '#ff9a00'; cx.shadowBlur = 10; }
    cx.fillText(f.text, f.x + f.w / 2, f.y + f.h / 2 + 3); cx.shadowBlur = 0;
  }
  const t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t);
  const levels = Math.floor(Math.log2(Math.max(Wmax, Ht))) + 1;
  gl.texStorage2D(gl.TEXTURE_2D, levels, gl.SRGB8_ALPHA8, Wmax, Ht);
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
  gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, gl.RGBA, gl.UNSIGNED_BYTE, cv);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.generateMipmap(gl.TEXTURE_2D);
  const e = gl.getExtension('EXT_texture_filter_anisotropic'); if (e) gl.texParameterf(gl.TEXTURE_2D, e.TEXTURE_MAX_ANISOTROPY_EXT, 8);
  const map = {}; for (const f of place) map[f.key] = { u0: f.x / Wmax, v0: f.y / Ht, u1: (f.x + f.w) / Wmax, v1: (f.y + f.h) / Ht, aspect: f.w / f.h };
  cv.width = cv.height = 1;
  return { tex: { tex: t }, map };
}

class G { constructor() { this.pos = []; this.nrm = []; this.uv = []; this.ext = []; this.idx = []; }
  quad(p0, p1, p2, p3, n, uv, kind) { // corners counter-clockwise seen from the front
    const b = this.pos.length / 3; for (const p of [p0, p1, p2, p3]) this.pos.push(...p);
    for (let i = 0; i < 4; i++) { this.nrm.push(...n); this.ext.push(kind, 0, 0, 0); }
    this.uv.push(...(uv || [0, 0, 0, 0, 0, 0, 0, 0])); this.idx.push(b, b + 1, b + 2, b, b + 2, b + 3);
  }
  box(c, u, w, h, d, y0) { // vertical box centred at c (x,z), u = unit along width, depth along normal
    const n = [-u[1], u[0]]; const hw = w / 2, hd = d / 2;
    const P = (a, b, y) => [c[0] + u[0] * a + n[0] * b, y, c[1] + u[1] * a + n[1] * b];
    const y1 = y0 + h;
    const faces = [[[-hw, -hd], [hw, -hd], [-n[0], 0, -n[1]]], [[hw, hd], [-hw, hd], [n[0], 0, n[1]]], [[hw, -hd], [hw, hd], [u[0], 0, u[1]]], [[-hw, hd], [-hw, -hd], [-u[0], 0, -u[1]]]];
    for (const [a, b, nn] of faces) this.quad(P(a[0], a[1], y0), P(b[0], b[1], y0), P(b[0], b[1], y1), P(a[0], a[1], y1), nn, null, 0);
    this.quad(P(-hw, -hd, y1), P(hw, -hd, y1), P(hw, hd, y1), P(-hw, hd, y1), [0, 1, 0], null, 0);
  }
  mesh() { return new Mesh({ pos: new Float32Array(this.pos), nrm: new Float32Array(this.nrm), uv: new Float32Array(this.uv), extra: new Float32Array(this.ext), idx: new Uint32Array(this.idx) }); }
}

// sign panel: faces the direction f (unit x,z), bottom at y0; face uv rect r
function panel(g, c, f, faceH, r, backR, y0 = GROUND_Y + 0.45) {
  const u = [-f[1], f[0]]; // along the panel, to the viewer's right when looking against f... (viewer faces -f)
  const w = faceH * r.aspect; const d = 0.28;
  g.box(c, u, w + 0.08, faceH + 0.08, d, y0 - 0.04);
  const hw = w / 2, hd = d / 2 + 0.005;
  // front face (normal f): viewer looks along -f; their right is -u... build so text reads left-to-right for the viewer
  const P = (a, y) => [c[0] + u[0] * a + f[0] * hd, y, c[1] + u[1] * a + f[1] * hd];
  const Q = (a, y) => [c[0] + u[0] * a - f[0] * hd, y, c[1] + u[1] * a - f[1] * hd];
  g.quad(P(hw, y0), P(-hw, y0), P(-hw, y0 + faceH), P(hw, y0 + faceH), [f[0], 0, f[1]], [r.u0, r.v1, r.u1, r.v1, r.u1, r.v0, r.u0, r.v0], 1);
  if (backR) g.quad(Q(-hw, y0), Q(hw, y0), Q(hw, y0 + faceH), Q(-hw, y0 + faceH), [-f[0], 0, -f[1]], [backR.u0, backR.v1, backR.u1, backR.v1, backR.u1, backR.v0, backR.u0, backR.v0], 1);
  // two frangible legs
  for (const s of [-0.35, 0.35]) g.box([c[0] + u[0] * w * s, c[1] + u[1] * w * s], u, 0.07, y0 - GROUND_Y, 0.07, GROUND_Y);
  return w;
}

export function buildSigns(details, runways) {
  const faces = new Map(); const add = (kind, text) => { const key = kind + ':' + text; if (!faces.has(key)) faces.set(key, { key, kind, text }); return key; };
  const holds = details.holds || [];
  for (const h of holds) { add('mand', h.text); add('paint', h.text); const loc = locName(h.twy); if (loc) add('loc', loc); }
  for (let k = 1; k <= 12; k++) add('drs', String(k));
  const A = makeAtlas([...faces.values()]);
  const g = new G(), gp = new G();
  const faceH = 0.76; // 30 in legend panel (size 3 sign)
  for (const h of holds) {
    if (h.signs === false) continue; // second ladder at one hold (data/sfo_details.json 'secondary'): no sign pair of its own
    const u = h.dir; const right = [-u[1], u[0]], left = [u[1], -u[0]];
    const f = [-u[0], -u[1]]; // faces the approaching pilot
    const edgeL = dot(sub(h.a, h.p), left) > 0 ? h.a : h.b, edgeR = edgeL === h.a ? h.b : h.a;
    const mand = A.map['mand:' + h.text]; const locKey = locName(h.twy) ? 'loc:' + locName(h.twy) : null; const loc = locKey && A.map[locKey];
    for (const [edge, side] of [[edgeL, left], [edgeR, right]]) {
      const base = [edge[0] + side[0] * 11 - u[0] * 1.2, edge[1] + side[1] * 11 - u[1] * 1.2];
      const w = panel(g, base, f, faceH, mand, null);
      if (loc) { const wl = faceH * loc.aspect; const c2 = [base[0] + side[0] * (w / 2 + wl / 2 + 0.25), base[1] + side[1] * (w / 2 + wl / 2 + 0.25)]; panel(g, c2, f, faceH, loc, null); }
    }
    // painted holding position signs on the pavement, on the holding side; text reads toward the runway
    const r = A.map['paint:' + h.text]; const Lr = 3.6; // 12 ft deep (along travel)
    if (h.kind === 'ils') continue; // ILS holds: mandatory "ILS" signs only, no painted surface sign
    const halves = h.w > 10.7 ? [-1, 1] : [0];
    for (const s of halves) {
      const across = Math.min(h.w / (halves.length === 2 ? 2 : 1) - 1.2, Lr * r.aspect);
      const c = [h.p[0] - u[0] * (4.5 + Lr / 2) + right[0] * s * (h.w / 4), h.p[1] - u[1] * (4.5 + Lr / 2) + right[1] * s * (h.w / 4)];
      const y = GROUND_Y + 0.035; const hw = across / 2, hl = Lr / 2;
      const P = (a, b) => [c[0] + right[0] * a + u[0] * b, y, c[1] + right[1] * a + u[1] * b];
      gp.quad(P(-hw, -hl), P(hw, -hl), P(hw, hl), P(-hw, hl), [0, 1, 0], [r.u0, r.v1, r.u1, r.v1, r.u1, r.v0, r.u0, r.v0], 2);
    }
  }
  // distance remaining signs, both faces, 1,000 ft apart, 55 m from the centreline on one side
  for (const Rw of runways) {
    const L = Rw.len / FT; const n = Math.floor(L / 1000);
    for (let k = 1; k <= n; k++) {
      const xa = Rw.len - k * 1000 * FT; if (xa < 150) continue; // remaining k*1000 ft for travel from end a
      const remB = Math.round(xa / FT / 1000); if (remB < 1 || remB > 12) continue;
      const c = [Rw.pa[0] + Rw.dir[0] * xa + Rw.side[0] * 55, Rw.pa[1] + Rw.dir[1] * xa + Rw.side[1] * 55];
      const f = [-Rw.dir[0], -Rw.dir[1]]; // front faces aircraft coming from end a
      panel(g, c, f, 1.0, A.map['drs:' + k], A.map['drs:' + remB], GROUND_Y + 0.5);
    }
  }
  return { mesh: g.mesh(), painted: gp.mesh(), atlas: A.tex, count: holds.length };
}
function locName(t) { if (!t || /INTERSECTION/i.test(t)) return null; const s = t.split('/')[0].trim(); return s.length <= 3 ? s : null; }
const sub = (a, b) => [a[0] - b[0], a[1] - b[1]]; const dot = (a, b) => a[0] * b[0] + a[1] * b[1];
