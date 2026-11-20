// forked from sfo3d@e3218d6 js/live/signs.js (SIGN_VS / SIGN_FS, the face atlas, the box / panel mesh helpers). The SFO
// sign list, the FAA distance-remaining signs and the module-scope SFO data imports are gone; sign content, colours,
// sizes and placement follow CAAC MH 5001-2021 ch. 8 / app. H (js/live/caac_markings.js CAAC.sign). sha3d markings package.
//
// Signs built (all positions inferred [inf]: no sign position is sourced for ZSSS):
//   - runway-holding position A (not exit-only): a runway designation sign (red, white "18L-36R" in the order seen) at
//     both ends of the holding marking, each with a location sign (black, yellow taxiway ref) outboard (8.3.3, 8.3.5,
//     8.3.6, 8.4.2-3 1)); the taxiway ref only where OSM names the taxiway;
//   - intermediate holding positions: a location sign with a yellow border on the left (8.4.2-3 6));
//   - named taxiway junctions: a direction assembly (location sign + yellow direction signs with arrows, left turns on the
//     left, 8.4.3-3 / -6) on the left side >= 60 m before the junction (8.4.3-10, -12), facing the approaching aircraft.
// Setback 11 m from the taxiway pavement edge (table 8.2.6 minimum, code 3-4); a sign whose footprint lies on pavement is
// pushed outwards (<= 12 m) or dropped.
import { gl, Mesh } from '../gl.js';
import { CAAC, val } from './caac_markings.js';

const S_ = CAAC.sign;
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
in vec3 vWP; in vec3 vN; in vec2 vUV; in vec4 vX; // vX.x: 1 = sign face (internally lit, 8.2.3), 0 = housing / leg
uniform sampler2D uAtlas; uniform float uNight;
void main(){
  vec3 wp = vWP; vec3 V = uCamPos - wp; float dist = length(V); V /= dist;
  vec3 N = normalize(vN); if (dot(N, V) < 0.0) N = -N;
  vec3 alb; float rough = 0.6; vec3 emis = vec3(0);
  if (vX.x > 0.5) { alb = texture(uAtlas, vUV).rgb; rough = 0.35; emis = alb * uNight * 1.6; }
  else { alb = vec3(0.05); rough = 0.5; }
  float sh = getShadow(wp, N, dist) * cloudShadow(wp);
  vec3 col = shadePBR(alb, N, V, rough, 0.0, sh, 1.0, 1.0) + emis;
  col = applyFog(col, wp);
  writeOut(col, wp, 1.0);
}`;

// ------------------------------------------------------------------------------------------------ face atlas
// faces: [{key, kind: 'mand' | 'loc' | 'locb' (location with border) | 'dir', text}]; CAAC colours (8.3.2, 8.4.2, 8.4.3)
function makeAtlas(faces) {
  const Hf = 96, pad = 4, Wmax = 2048;
  const cv = document.createElement('canvas'); const cx = cv.getContext('2d');
  const font = (px) => `bold ${px}px "DejaVu Sans Condensed", "Liberation Sans Narrow", "Arial Narrow", "DejaVu Sans", Arial, sans-serif`;
  const TXT = Math.round(Hf * val(S_.mandTextH) / val(S_.mandFaceH));   // 400 / 600 mm (and 300 / 450 mm): 2/3 of the face
  const place = []; let x = pad, y = pad, rowH = 0;
  for (const f of faces) {
    cx.font = font(TXT); const tw = cx.measureText(f.text).width;
    const w = Math.ceil(tw + Hf * 0.5), h = Hf;
    if (x + w + pad > Wmax) { x = pad; y += rowH + pad; rowH = 0; }
    place.push({ ...f, x, y, w, h }); x += w + pad; rowH = Math.max(rowH, h);
  }
  const Ht = Math.pow(2, Math.ceil(Math.log2(Math.max(4, y + rowH + pad))));
  cv.width = Wmax; cv.height = Ht; cx.textAlign = 'center'; cx.textBaseline = 'middle';
  const [mBg, mFg] = val(S_.mandColours), [lBg, lFg] = val(S_.locColours), [dBg, dFg] = val(S_.dirColours);
  for (const f of place) {
    const bg = f.kind === 'mand' ? mBg : f.kind === 'dir' ? dBg : lBg, fg = f.kind === 'mand' ? mFg : f.kind === 'dir' ? dFg : lFg;
    cx.fillStyle = bg; cx.fillRect(f.x, f.y, f.w, f.h);
    if (f.kind === 'locb') { cx.strokeStyle = lFg; cx.lineWidth = 5; cx.strokeRect(f.x + 6, f.y + 6, f.w - 12, f.h - 12); }
    if (f.kind === 'dir') { cx.fillStyle = dFg; cx.fillRect(f.x, f.y, 3, f.h); cx.fillRect(f.x + f.w - 3, f.y, 3, f.h); }   // divider lines (8.4.3-8)
    cx.fillStyle = fg; cx.font = font(TXT); cx.fillText(f.text, f.x + f.w / 2, f.y + f.h / 2 + 2);
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

// forked from sfo3d@e3218d6 js/live/signs.js class G (quad / box / mesh), unchanged
class G { constructor() { this.pos = []; this.nrm = []; this.uv = []; this.ext = []; this.idx = []; }
  quad(p0, p1, p2, p3, n, uv, kind) {
    const b = this.pos.length / 3; for (const p of [p0, p1, p2, p3]) this.pos.push(...p);
    for (let i = 0; i < 4; i++) { this.nrm.push(...n); this.ext.push(kind, 0, 0, 0); }
    this.uv.push(...(uv || [0, 0, 0, 0, 0, 0, 0, 0])); this.idx.push(b, b + 1, b + 2, b, b + 2, b + 3);
  }
  box(c, u, w, h, d, y0) {
    const n = [-u[1], u[0]]; const hw = w / 2, hd = d / 2;
    const P = (a, b, y) => [c[0] + u[0] * a + n[0] * b, y, c[1] + u[1] * a + n[1] * b];
    const y1 = y0 + h;
    const faces = [[[-hw, -hd], [hw, -hd], [-n[0], 0, -n[1]]], [[hw, hd], [-hw, hd], [n[0], 0, n[1]]], [[hw, -hd], [hw, hd], [u[0], 0, u[1]]], [[-hw, hd], [-hw, -hd], [-u[0], 0, -u[1]]]];
    for (const [a, b, nn] of faces) this.quad(P(a[0], a[1], y0), P(b[0], b[1], y0), P(b[0], b[1], y1), P(a[0], a[1], y1), nn, null, 0);
    this.quad(P(-hw, -hd, y1), P(hw, -hd, y1), P(hw, hd, y1), P(-hw, hd, y1), [0, 1, 0], null, 0);
  }
  mesh() { return new Mesh({ pos: new Float32Array(this.pos), nrm: new Float32Array(this.nrm), uv: new Float32Array(this.uv), extra: new Float32Array(this.ext), idx: new Uint32Array(this.idx) }); }
}
// one sign panel facing f (unit x, z), centre c, face height faceH, face rect r, face bottom y0 (forked from sfo3d panel())
function panel(g, c, f, faceH, r, y0, groundY) {
  const u = [-f[1], f[0]]; const w = faceH * r.aspect; const d = 0.24;
  g.box(c, u, w + 0.06, faceH + 0.06, d, y0 - 0.03);
  const hw = w / 2, hd = d / 2 + 0.005;
  const P = (a, y) => [c[0] + u[0] * a + f[0] * hd, y, c[1] + u[1] * a + f[1] * hd];
  g.quad(P(hw, y0), P(-hw, y0), P(-hw, y0 + faceH), P(hw, y0 + faceH), [f[0], 0, f[1]], [r.u0, r.v1, r.u1, r.v1, r.u1, r.v0, r.u0, r.v0], 1);
  for (const s of [-0.35, 0.35]) g.box([c[0] + u[0] * w * s, c[1] + u[1] * w * s], u, 0.06, y0 - groundY, 0.06, groundY);   // frangible legs (8.2.1)
  return w;
}

// ------------------------------------------------------------------------------------------------ helpers
const sub = (a, b) => [a[0] - b[0], a[1] - b[1]], add = (a, b) => [a[0] + b[0], a[1] + b[1]], mul = (a, k) => [a[0] * k, a[1] * k];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1], len = (a) => Math.hypot(a[0], a[1]);
const norm = (a) => { const l = len(a) || 1; return [a[0] / l, a[1] / l]; };
const leftOf = (u) => [u[1], -u[0]], rightOf = (u) => [-u[1], u[0]];
function cum(pts) { const c = [0]; for (let i = 1; i < pts.length; i++) c.push(c[i - 1] + len(sub(pts[i], pts[i - 1]))); return c; }
function at(pts, c, s) { s = Math.max(0, Math.min(c[c.length - 1], s)); let i = 1; while (i < c.length - 1 && c[i] < s) i++; const a = pts[i - 1], b = pts[i]; const k = (s - c[i - 1]) / ((c[i] - c[i - 1]) || 1e-9); return { p: [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k], t: norm(sub(b, a)) }; }
const arrowFor = (deg) => deg < -60 ? '←' : deg < -20 ? '↖' : deg <= 20 ? '↑' : deg <= 60 ? '↗' : '→';   // 8.4.3-6

// ------------------------------------------------------------------------------------------------ the build
export function buildSigns(ctx, holds, junctions) {
  const t0 = performance.now(); const groundY = ctx.groundY;
  const pavedAt = (ctx.ground && ctx.ground.pavedAt) || (() => 0);
  const setback = val(S_.setbackUsed), twyHalf = 11.5;   // AIP (mirror) 23 m main taxiways (data halfWidth)
  const assemblies = [];   // {c, f (face normal), faces: [{kind, text}], faceH, why}
  const stats = { holdAssemblies: 0, intermediateLocation: 0, junctionAssemblies: 0, skippedNoRef: 0, skippedOnPavement: 0, skippedShortArm: 0, skippedCrowded: 0 };
  // a clear spot: footprint (width w along the panel) off the pavement; pushed outwards by up to 12 m
  const clearSpot = (base, out, along, w) => {
    for (let k = 0; k <= 12; k += 1) {
      const c = add(base, mul(out, k)); let ok = true;
      for (let a = -w / 2 - 1; a <= w / 2 + 1 + 1e-6 && ok; a += Math.max(0.5, (w + 2) / 6)) for (const b of [-1, 0, 1]) { const q = add(c, add(mul(along, a), mul(out, b))); if (pavedAt(q[0], q[1]) > 0.35) { ok = false; break; } }
      if (ok) return c;
    }
    return null;
  };
  const widthOf = (faces, faceH) => faces.reduce((s, f) => s + faceH * (0.5 + 0.62 * f.text.length * 0.66), 0);   // rough, for the footprint test
  // ---- runway-holding positions (pattern A), not exit-only
  for (const h of holds) {
    if (h.kind !== 'A' || h.exitOnly) continue;
    const text = h.mandText; if (!text) continue;
    const f = mul(h.u, -1);   // faces the aircraft holding short (8.3.3)
    for (const sg of [-1, 1]) {
      // sg -1 = the pilot's left (h.n is the right of the travel direction u towards the runway)
      const out = mul(h.n, sg); const base = add(h.p, mul(out, twyHalf + setback));
      const faces = [{ kind: 'mand', text }]; if (h.twyRef) { if (sg < 0) faces.unshift({ kind: 'loc', text: h.twyRef }); else faces.push({ kind: 'loc', text: h.twyRef }); }
      const fh = val(S_.mandFaceH); const c = clearSpot(base, out, h.n, widthOf(faces, fh));
      if (!c) { stats.skippedOnPavement++; continue; }
      assemblies.push({ c, f, faces, faceH: fh, why: 'hold A ' + h.id }); stats.holdAssemblies++;
    }
  }
  // ---- intermediate holding positions: location sign with border, left side
  for (const h of holds) {
    if (h.kind === 'A') continue; if (!h.twyRef) { stats.skippedNoRef++; continue; }
    for (const dirSg of [1, -1]) {   // both travel directions along the parallel taxiway
      const travel = mul(h.u, dirSg); const f = mul(travel, -1); const out = leftOf(travel);
      const base = add(h.p, mul(out, twyHalf + setback)); const fh = val(S_.infoFaceH);
      const faces = [{ kind: 'locb', text: h.twyRef }]; const c = clearSpot(base, out, rightOf(out), widthOf(faces, fh));
      if (!c) { stats.skippedOnPavement++; continue; }
      assemblies.push({ c, f, faces, faceH: fh, why: 'intermediate ' + h.id }); stats.intermediateLocation++;
    }
  }
  // ---- direction assemblies at named junctions
  const dist = val(S_.dirBeforeJunction);
  for (const j of junctions || []) {
    for (const A of j.arms) {
      // >= 60 m before the junction (8.4.3-10); on a shorter arm before the start of the turn (8.4.3-11): arm - 15 m [inf]
      const dd = A.len >= dist + 5 ? dist : A.len >= 35 ? A.len - 15 : -1;
      if (dd < 0) { stats.skippedShortArm++; continue; }
      const q = at(A.pts, cum(A.pts), dd); const travel = mul(q.t, -1);   // towards the junction
      const appr = mul(A.dir, -1);   // travel direction arriving at the junction
      const left = [], right = [];
      const seen = new Set([A.ref + ':straight']);
      for (const Bm of j.arms) {
        if (Bm === A || Bm.ref === A.ref) continue;
        const ang = Math.atan2(appr[0] * Bm.dir[1] - appr[1] * Bm.dir[0], dot(appr, Bm.dir)) * 180 / Math.PI;   // + = right turn
        if (Math.abs(ang) > 150) continue;   // a U-turn back: not signed
        const arrow = arrowFor(ang); const key = Bm.ref + ':' + arrow; if (seen.has(key)) continue; seen.add(key);
        (ang < -20 ? left : right).push({ kind: 'dir', text: ang < -20 ? arrow + ' ' + Bm.ref : Bm.ref + ' ' + arrow, ang });
      }
      if (!left.length && !right.length) continue;
      left.sort((a, b) => a.ang - b.ang); right.sort((a, b) => a.ang - b.ang);
      const faces = [...left, { kind: 'loc', text: A.ref }, ...right];
      const out = leftOf(travel); const base = add(q.p, mul(out, twyHalf + setback)); const fh = val(S_.infoFaceH);
      const c = clearSpot(base, out, rightOf(out), widthOf(faces, fh));
      if (!c) { stats.skippedOnPavement++; continue; }
      if (assemblies.some(o => len(sub(o.c, c)) < 6)) { stats.skippedCrowded++; continue; }
      assemblies.push({ c, f: mul(travel, -1), faces, faceH: fh, why: 'junction ' + j.id }); stats.junctionAssemblies++;
      if (dd < dist) stats.shortArmPlaced = (stats.shortArmPlaced || 0) + 1;
    }
  }
  // ---- atlas + mesh
  const faceList = new Map(); for (const a of assemblies) for (const f of a.faces) { const k = f.kind + ':' + f.text; if (!faceList.has(k)) faceList.set(k, { key: k, kind: f.kind, text: f.text }); }
  const atlas = makeAtlas([...faceList.values()]);
  const g = new G(); let panels = 0;
  for (const a of assemblies) {
    // faces left to right as the viewer sees them; the viewer looks along -f, their right is rightOf(-f)
    const vr = rightOf(mul(a.f, -1)); const ws = a.faces.map(f => a.faceH * atlas.map[f.kind + ':' + f.text].aspect);
    const total = ws.reduce((s, w) => s + w, 0) + 0.04 * (ws.length - 1); let x = -total / 2;
    const y0 = groundY + val(S_.mountMax) - a.faceH - 0.02;   // face top at the maximum mounting height (table 8.2.6)
    a.faces.forEach((f, i) => { const c = add(a.c, mul(vr, x + ws[i] / 2)); panel(g, c, a.f, a.faceH, atlas.map[f.kind + ':' + f.text], y0, groundY); x += ws[i] + 0.04; panels++; });
  }
  const items = [];
  if (panels) {
    ctx.R.addProgram('caacSign', SIGN_VS, SIGN_FS);
    const xs = assemblies.map(a => a.c[0]), zs = assemblies.map(a => a.c[1]);
    items.push({ mesh: g.mesh(), prog: 'caacSign', bbox: [Math.min(...xs) - 5, groundY, Math.min(...zs) - 5, Math.max(...xs) + 5, groundY + 2, Math.max(...zs) + 5], castShadow: true, shadowMaxCascade: 1, nearOnly: true, noCull: true, uniforms: { uAtlas: atlas.tex }, src: 'inf', layer: 'signs' });
  }
  return { items, info: { ...stats, assemblies: assemblies.length, panels, faces: faceList.size, src: 'inf: sign positions and texts inferred (OSM taxiway refs, CAAC ch. 8 placement rules)', ms: Math.round(performance.now() - t0) }, assemblies };
}
