// forked from sfo3d@e3218d6 js/live/markings.js (the Ribbons class and the MARK_VS / MARK_FS decal shader); everything
// FAA there (AC 150/5340-1 dimensions, the SFO details source, the NAIP red boxes) is replaced. sha3d markings package.
//
// Pavement decals per CAAC MH 5001-2021 (parameters: js/live/caac_markings.js): taxiway centrelines with black borders on
// light pavement, taxiway edge lines, runway-holding positions (pattern A) and intermediate holding positions, enhanced
// taxiway centrelines, painted mandatory instruction markings, stand lead-ins / stop lines / stand number plates, stand
// safety lines with hatched overlaps, bridge activity areas and equipment areas. One alpha-blended mesh in three layers
// (black backgrounds, paint, characters), drawn over the ground without depth writes.
// Inputs (injected): ctx.airport (taxiways, taxilanes, holds, surfaces.taxiway, aprons), ctx.taxigraph (hold_inf, links),
// ctx.stands (lead-ins, stop nodes, headings, classes, bridges), ctx.ground.pavedAt, ctx.geo.
import { gl, Mesh, texture } from '../gl.js';
import { earcut } from './earcut.js';
import { CAAC, val } from './caac_markings.js';

const T_ = CAAC.taxiway, H_ = CAAC.hold, S_ = CAAC.stand, M_ = CAAC.mandatoryMarking;
const AL = CAAC.albedo;
const YEL = val(AL.yellow), WHT = val(AL.white), RED = val(AL.red), BLK = val(AL.black);

export const DECAL_VS = `
#include <common>
#include <vout>
layout(location=0) in vec3 aPos; layout(location=1) in vec3 aNrm; layout(location=2) in vec2 aUV; layout(location=3) in vec4 aCol; layout(location=4) in vec4 aExtra;
uniform float uPxScale; // world size of one pixel at unit distance
out vec3 vWP; out vec4 vCol; out vec3 vDash; out float vA; out vec2 vUV; out float vPoly;
void main(){
  // ribbons: aNrm.xz = unit perpendicular, aNrm.y = dash duty, aExtra = (half width, side -1/+1, distance along, dash
  // period (0 = solid)); polygons and character quads: aExtra.x = 0 (no widening), aUV >= 0 for characters
  float dist = length(aPos - uCamPos);
  float px = dist * uPxScale * 0.75;
  vec3 wp = aPos; vA = 1.0; vPoly = 1.0;
  if (aExtra.x > 0.0) { float hw = max(aExtra.x, px); vA = aExtra.x / hw; wp += vec3(aNrm.x, 0.0, aNrm.z) * aExtra.y * hw; vPoly = 0.0; }
  vWP = wp; vCol = aCol; vDash = vec3(aExtra.z, aExtra.w, aNrm.y); vUV = aUV;
  emitClip(wp, wp);
}`;
export const DECAL_FS = `
#include <common>
#include <shadow>
#include <fout>
in vec3 vWP; in vec4 vCol; in vec3 vDash; in float vA; in vec2 vUV; in float vPoly;
uniform sampler2D uChars; uniform float uNight;
void main(){
  vec3 wp = vWP; vec3 V = uCamPos - wp; float dist = length(V); V /= dist;
  float a = vCol.a * vA;
  if (vDash.y > 0.0) {
    float period = vDash.y; float duty = vDash.z * period;
    float f = mod(vDash.x, period); float fw = fwidth(vDash.x) + 1e-4;
    a *= smoothstep(-fw, fw, f) * (1.0 - smoothstep(duty - fw, duty + fw, f));
    a = mix(a, vCol.a * vA * vDash.z, smoothstep(0.35 * period, 1.0 * period, fw)); // far away the pattern averages out
  }
  if (vUV.x >= 0.0) { float g = texture(uChars, vUV).a; float w = max(fwidth(g), 1e-3); a *= smoothstep(0.5 - w, 0.5 + w, g) * 0.6 + g * 0.4; }
  // polygons and characters have no minimum width: fade them out before they alias
  a *= 1.0 - vPoly * smoothstep(350.0, 1100.0, dist);
  a *= 1.0 - smoothstep(2500.0, 6000.0, dist);
  if (a < 0.003) discard;
  vec3 N = vec3(0, 1, 0);
  float sh = getShadow(wp, N, dist) * cloudShadow(wp);
  vec3 alb = vCol.rgb * (0.84 + 0.16 * texture(uNoise, wp.xz * 0.23).r);
  vec3 col = shadePBR(alb, N, V, 0.62, 0.0, sh, 1.0, 0.6);
  col = applyFog(col, wp);
  writeOut(col, wp, a);
}`;

// ------------------------------------------------------------------------------------------------ geometry helpers
const sub = (a, b) => [a[0] - b[0], a[1] - b[1]], add = (a, b) => [a[0] + b[0], a[1] + b[1]], mul = (a, k) => [a[0] * k, a[1] * k];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1], len = (a) => Math.hypot(a[0], a[1]);
const norm = (a) => { const l = len(a) || 1; return [a[0] / l, a[1] / l]; };
const rightOf = (u) => [-u[1], u[0]];   // right of the direction u in the x-east / z-south frame
const leftOf = (u) => [u[1], -u[0]];
function cum(pts) { const c = [0]; for (let i = 1; i < pts.length; i++) c.push(c[i - 1] + len(sub(pts[i], pts[i - 1]))); return c; }
function at(pts, c, s) {   // point and unit tangent at arc length s
  s = Math.max(0, Math.min(c[c.length - 1], s)); let i = 1; while (i < c.length - 1 && c[i] < s) i++;
  const a = pts[i - 1], b = pts[i]; const L = c[i] - c[i - 1] || 1e-9; const k = (s - c[i - 1]) / L;
  return { p: [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k], t: norm(sub(b, a)) };
}
function subPoly(pts, c, s0, s1) {
  if (s1 - s0 < 0.05) return null; const out = [at(pts, c, s0).p];
  for (let i = 0; i < pts.length; i++) if (c[i] > s0 + 1e-6 && c[i] < s1 - 1e-6) out.push(pts[i]);
  out.push(at(pts, c, s1).p); return out;
}
/** split a polyline where cut(p) is true (sampled every step m): the kept parts */
function cutPoly(pts, cutFn, step = 0.5) {
  if (!pts || pts.length < 2) return [];
  const c = cum(pts), L = c[c.length - 1]; const out = []; let s0 = null;
  const n = Math.max(1, Math.ceil(L / step));
  for (let k = 0; k <= n; k++) {
    const s = L * k / n; const keep = !cutFn(at(pts, c, s).p, s);
    if (keep && s0 == null) s0 = s;
    if ((!keep || k === n) && s0 != null) { const s1 = keep ? s : Math.max(s0, s - L / n * 0.5); const q = subPoly(pts, c, s0, s1); if (q) out.push(q); s0 = null; }
  }
  return out;
}
function inRings(rings, x, z) {
  let inside = false;
  for (const r of rings) for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
    const a = r[i], b = r[j]; if ((a[1] > z) !== (b[1] > z) && x < (b[0] - a[0]) * (z - a[1]) / (b[1] - a[1]) + a[0]) inside = !inside;
  }
  return inside;
}
function bboxOf(pts) { let x0 = 1e9, z0 = 1e9, x1 = -1e9, z1 = -1e9; for (const p of pts) { x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0]); z0 = Math.min(z0, p[1]); z1 = Math.max(z1, p[1]); } return { x0, z0, x1, z1 }; }
function polyIndex(list) { return list.map(rings => ({ rings, ...bboxOf(rings[0]) })); }
const inAny = (idx, x, z, m = 0) => idx.some(P => x >= P.x0 - m && x <= P.x1 + m && z >= P.z0 - m && z <= P.z1 + m && inRings(P.rings, x, z));
function segDist(p, a, b) { const ab = sub(b, a), ap = sub(p, a); const L2 = dot(ab, ab) || 1e-9; const k = Math.max(0, Math.min(1, dot(ap, ab) / L2)); return len(sub(ap, mul(ab, k))); }
function nearestOnPolys(polys, p, maxD = 6) {
  let best = null;
  for (const pl of polys) for (let i = 1; i < pl.pts.length; i++) {
    const d = segDist(p, pl.pts[i - 1], pl.pts[i]); if (d < maxD && (!best || d < best.d)) best = { d, pl, i };
  }
  return best;
}

// ------------------------------------------------------------------------------------------------ mesh builder
// forked from sfo3d@e3218d6 js/live/markings.js class Ribbons (line / rect / mesh); polygons and character quads added
class Layer {
  constructor(y) { this.y = y; this.pos = []; this.nrm = []; this.uv = []; this.col = []; this.ext = []; this.idx = []; }
  // polyline pts [[x,z],...]; offset: lateral offset (m, + = right of travel); hw: half width; dash: [period, duty] (m)
  line(pts, hw, color, alpha = 1, offset = 0, dash = null, s0 = 0) {
    if (!pts || pts.length < 2) return;
    const n = pts.length; const P = [], N = []; let s = s0; const S = [];
    for (let i = 0; i < n; i++) {
      const a = pts[Math.max(0, i - 1)], b = pts[Math.min(n - 1, i + 1)];
      let dx = b[0] - a[0], dz = b[1] - a[1]; const l = Math.hypot(dx, dz) || 1; dx /= l; dz /= l;
      let nx = -dz, nz = dx;
      if (i > 0 && i < n - 1) {
        const d1 = [pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]];
        const l1 = Math.hypot(...d1) || 1; const n1 = [-d1[1] / l1, d1[0] / l1];
        const dt = n1[0] * nx + n1[1] * nz; const k = 1 / Math.max(0.5, dt); nx *= k; nz *= k;
      }
      if (i > 0) s += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
      P.push([pts[i][0] + nx * offset, pts[i][1] + nz * offset]); N.push([nx, nz]); S.push(s);
    }
    const base = this.pos.length / 3; const period = dash ? dash[0] : 0, ratio = dash ? dash[1] / dash[0] : 0;
    for (let i = 0; i < n; i++) for (const side of [-1, 1]) {
      this.pos.push(P[i][0], this.y, P[i][1]); this.nrm.push(N[i][0], ratio, N[i][1]); this.uv.push(-1, -1);
      this.col.push(color[0], color[1], color[2], alpha); this.ext.push(hw, side, S[i], period);
    }
    for (let i = 0; i < n - 1; i++) { const a = base + i * 2; this.idx.push(a, a + 2, a + 1, a + 1, a + 2, a + 3); }
  }
  poly(rings, color, alpha = 1) {   // filled polygon (even-odd holes) via earcut
    const flat = [], holes = []; for (const r of rings) { if (flat.length) holes.push(flat.length / 2); for (const p of r) flat.push(p[0], p[1]); }
    const tri = earcut(flat, holes); const base = this.pos.length / 3;
    for (let i = 0; i < flat.length / 2; i++) { this.pos.push(flat[2 * i], this.y, flat[2 * i + 1]); this.nrm.push(0, 0, 0); this.uv.push(-1, -1); this.col.push(color[0], color[1], color[2], alpha); this.ext.push(0, 0, 0, 0); }
    for (const k of tri) this.idx.push(base + k);
  }
  quad(c, right, up, w, h, r, color, alpha = 1) {   // character quad: centre c, unit right / up (x, z), size, atlas rect r
    const base = this.pos.length / 3;
    const P = (a, b) => [c[0] + right[0] * a + up[0] * b, c[1] + right[1] * a + up[1] * b];
    const corners = [[P(-w / 2, -h / 2), r.u0, r.v1], [P(w / 2, -h / 2), r.u1, r.v1], [P(w / 2, h / 2), r.u1, r.v0], [P(-w / 2, h / 2), r.u0, r.v0]];
    for (const [p, u, v] of corners) { this.pos.push(p[0], this.y, p[1]); this.nrm.push(0, 0, 0); this.uv.push(u, v); this.col.push(color[0], color[1], color[2], alpha); this.ext.push(0, 0, 0, 0); }
    this.idx.push(base, base + 1, base + 2, base, base + 2, base + 3);
  }
}
function merge(layers) {
  let nv = 0, ni = 0; for (const L of layers) { nv += L.pos.length / 3; ni += L.idx.length; }
  if (!ni) return null;
  const pos = new Float32Array(nv * 3), nrm = new Float32Array(nv * 3), uv = new Float32Array(nv * 2), col = new Float32Array(nv * 4), ext = new Float32Array(nv * 4), idx = new Uint32Array(ni);
  let v = 0, k = 0;
  for (const L of layers) {
    pos.set(L.pos, v * 3); nrm.set(L.nrm, v * 3); uv.set(L.uv, v * 2); col.set(L.col, v * 4); ext.set(L.ext, v * 4);
    for (let i = 0; i < L.idx.length; i++) idx[k++] = L.idx[i] + v;
    v += L.pos.length / 3;
  }
  let x0 = 1e9, z0 = 1e9, x1 = -1e9, z1 = -1e9; for (let i = 0; i < pos.length; i += 3) { x0 = Math.min(x0, pos[i]); x1 = Math.max(x1, pos[i]); z0 = Math.min(z0, pos[i + 2]); z1 = Math.max(z1, pos[i + 2]); }
  return { mesh: new Mesh({ pos, nrm, uv, col, extra: ext, idx }), bbox: [x0, 0, z0, x1, 12, z1], verts: nv, tris: ni / 3 };
}

// ------------------------------------------------------------------------------------------------ character atlas
// painted characters (fig. 6.2.12-3 shapes approximated by a condensed bold sans [inf]); CJK apron text in 黑体 (6.2.20-1)
// with the system sans-serif CJK fallback [inf]
const LATIN = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-';
export function makeCharAtlas(extra = '') {
  const CH = 128, CWL = 52, CWC = 128; const chars = [...LATIN, ...[...new Set([...extra])].filter(c => !LATIN.includes(c))];
  const cells = chars.map(ch => ({ ch, w: LATIN.includes(ch) ? CWL : CWC }));
  const W = 2048; let x = 0, y = 0; for (const c of cells) { if (x + c.w > W) { x = 0; y += CH; } c.x = x; c.y = y; x += c.w; }
  const H = y + CH;
  const cv = Object.assign(document.createElement('canvas'), { width: W, height: H }); const cx = cv.getContext('2d');
  cx.clearRect(0, 0, W, H); cx.fillStyle = '#fff'; cx.textAlign = 'center'; cx.textBaseline = 'alphabetic';
  for (const c of cells) {
    cx.save();
    if (LATIN.includes(c.ch)) {
      cx.font = 'bold 120px "DejaVu Sans Condensed", "Liberation Sans Narrow", "Arial Narrow", "DejaVu Sans", Arial, sans-serif';
      cx.textAlign = 'left'; cx.textBaseline = 'alphabetic';
      const m = cx.measureText(c.ch); const asc = m.actualBoundingBoxAscent || 88; const lft = m.actualBoundingBoxLeft || 0, rgt = m.actualBoundingBoxRight || m.width;
      const cap = cx.measureText('H').actualBoundingBoxAscent || 88; void asc;   // one vertical scale: cap height = cell
      const wd = Math.max(1, lft + rgt); const sy = (CH - 12) / cap, sx = Math.min(sy * 0.62, (c.w - 8) / wd);
      // glyph spans x in [-lft, rgt] at the origin: centre it in the cell; baseline 6 px above the cell bottom
      cx.translate(c.x + c.w / 2 - (rgt - lft) / 2 * sx, c.y + CH - 6); cx.scale(sx, sy);
      cx.fillText(c.ch, 0, 0);
    } else {
      cx.font = 'bold 110px "WenQuanYi Zen Hei", "Noto Sans CJK SC", "Microsoft YaHei", "PingFang SC", SimHei, sans-serif';
      cx.textAlign = 'center'; cx.textBaseline = 'middle'; cx.fillText(c.ch, c.x + c.w / 2, c.y + CH / 2 + 2);
    }
    cx.restore();
  }
  const t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t);
  const levels = Math.floor(Math.log2(Math.max(W, H))) + 1;
  gl.texStorage2D(gl.TEXTURE_2D, levels, gl.RGBA8, W, H);
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false); gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
  gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, gl.RGBA, gl.UNSIGNED_BYTE, cv);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.generateMipmap(gl.TEXTURE_2D);
  const map = {}; for (const c of cells) map[c.ch] = { u0: c.x / W, v0: c.y / H, u1: (c.x + c.w) / W, v1: (c.y + CH) / H, aspect: c.w / CH, cjk: !LATIN.includes(c.ch) };
  cv.width = cv.height = 1;
  return { tex: { tex: t, w: W, h: H }, map };
}
const ADV = (ch) => ch === '-' ? 0.30 : /[0-9A-Z]/.test(ch) ? val(CAAC.markChars.widthRatio) : 1.0;   // advance / height
function textWidth(text, h) { let w = 0; for (const ch of text) w += ADV(ch) * h; return w; }
/** characters of `text` centred at c, reading along `right`, upright towards `up` (all units m) */
function textQuads(L, atlas, text, c, right, up, h, color) {
  const tw = textWidth(text, h); let x = -tw / 2;
  for (const ch of text) {
    const a = ADV(ch) * h; const r = atlas.map[ch]; if (r) { const gw = r.cjk ? h : h * r.aspect; L.quad(add(c, mul(right, x + a / 2)), right, up, gw, h, r, color); } x += a;
  }
  return tw;
}

// ------------------------------------------------------------------------------------------------ the build
export function buildDecals(ctx, plan) {
  const t0 = performance.now();
  const A = ctx.airport, G = ctx.geo, TG = ctx.taxigraph || {}, ST = (ctx.stands && ctx.stands.stands) || [];
  const pavedAt = (ctx.ground && ctx.ground.pavedAt) || (() => 1);
  const y0 = ctx.groundY + 0.03;
  const B = new Layer(y0), P = new Layer(y0 + 0.002), T = new Layer(y0 + 0.004);   // black, paint, characters
  const chars = makeCharAtlas(String(val(S_.equipText)));
  const info = { src: 'inf: placement and presence of every decal inferred from OSM geometry + MH 5001-2021 rules; dimensions per js/live/caac_markings.js' };
  const lines = [...(A.taxiways || []), ...(A.taxilanes || [])].filter(t => t.pts && t.pts.length >= 2 && t.status !== 'construction');
  const byId = new Map(lines.map(t => [t.id, t]));
  const runways = G.RUNWAYS;
  const onRunway = (p, m = 0) => G.runwayAt(p[0], p[1], m);

  // ---------------------------------------------------------------------------------------- holding positions
  const linkPolys = (TG.links || []).filter(l => l.kind !== 'runway' && l.kind !== 'push' && l.pts && l.pts.length >= 2);
  const rawHolds = [
    ...(A.holds || []).map(h => ({ p: [h.x, h.z], rwy: h.runway, cl: Math.abs(h.cl_dist_m), way: h.on_way, ref: h.twy_ref, id: h.id, src: 'obs (OSM holding_position)' })),
    ...((TG.hold_inf) || []).map((h, i) => ({ p: [h.x, h.z], rwy: h.runway, cl: 90, way: h.osm_way != null ? 'osm:way/' + h.osm_way : null, ref: h.taxiway, id: 'hold_inf:' + i, src: 'inf (' + h.rule + ')' })),
  ];
  const holds = [];
  for (const h of rawHolds) {
    // the taxiway centreline through the hold: its own OSM way, else the nearest line
    let L = h.way && byId.get(h.way); let near = L ? nearestOnPolys([L], h.p, 8) : null;
    if (!near) near = nearestOnPolys(lines, h.p, 8); if (!near) continue;
    L = near.pl; const tdir = norm(sub(L.pts[near.i], L.pts[near.i - 1]));
    const R = G.runwayById(h.rwy) || runways[0]; const [s, t] = G.rwyAlongAcross(R, h.p[0], h.p[1]);
    const toCL = norm(sub(G.rwyToWorld(R, s, 0), h.p)); const u = dot(tdir, toCL) >= 0 ? tdir : mul(tdir, -1);
    const n = rightOf(u);
    const ext = (sg) => { let e = 0; for (let k = 0.5; k <= val(H_.halfWidthCap); k += 0.5) { const q = add(h.p, mul(n, sg * k)); if (pavedAt(q[0], q[1]) < 0.5) break; e = k; } return Math.max(e, 11.5); };
    const runwayHold = h.cl <= val(H_.runwayHoldMaxFromCL);
    const link = nearestOnPolys(linkPolys, h.p, 6);
    const exitOnly = !!(link && link.pl.use === 'arrival');
    holds.push({ ...h, line: L, u, n, eL: ext(-1), eR: ext(1), kind: runwayHold ? 'A' : 'intermediate', exitOnly, R, twyRef: h.ref || (L && L.ref) || null });
  }
  // pattern A spans 4 x 0.3 m lines + 3 x 0.3 m gaps = 2.1 m: half depth 1.05 m
  for (const h of holds) h.half = h.kind === 'A' ? (4 * val(H_.aLineW) + 3 * val(H_.aGap)) / 2 : val(H_.iLineW) / 2;
  // two OSM / inferred holds within 15 m on the same line: keep one (the OSM one)
  for (let i = 0; i < holds.length; i++) for (let j = i + 1; j < holds.length; j++) if (!holds[j].drop && !holds[i].drop && len(sub(holds[i].p, holds[j].p)) < 15) holds[j].drop = true;
  const H = holds.filter(h => !h.drop);
  const bd = val(H_.border);
  const holdZone = (p, clear) => H.some(h => { const d = sub(p, h.p); const a = dot(d, h.u), b = dot(d, h.n); return Math.abs(a) < h.half + bd + clear && b > -h.eL - 1.5 && b < h.eR + 1.5; });
  for (const h of H) {
    const D = (a, b) => add(h.p, add(mul(h.u, a), mul(h.n, b)));
    const half = h.half + bd;
    B.poly([[D(-half, -h.eL - bd), D(-half, h.eR + bd), D(half, h.eR + bd), D(half, -h.eL - bd)]], BLK);
    if (h.kind === 'A') {
      // 4 lines 0.3 m / gaps 0.3 m; the two on the runway side dashed 0.9 / 0.9 (fig. 6.2.10-1)
      for (let k = 0; k < 4; k++) {
        const a = -h.half + val(H_.aLineW) / 2 + k * (val(H_.aLineW) + val(H_.aGap));
        P.line([D(a, -h.eL), D(a, h.eR)], val(H_.aLineW) / 2, YEL, 1, 0, k >= 2 ? [val(H_.aDash) + val(H_.aDashGap), val(H_.aDash)] : null);
      }
    } else P.line([D(0, -h.eL), D(0, h.eR)], val(H_.iLineW) / 2, YEL, 1, 0, [val(H_.iDash) + val(H_.iDashGap), val(H_.iDash)]);
  }
  info.holds = { runwayHoldsA: H.filter(h => h.kind === 'A').length, fromOSM: H.filter(h => h.kind === 'A' && h.src.startsWith('obs')).length, exitOnly: H.filter(h => h.exitOnly).length,
    intermediate: H.filter(h => h.kind !== 'A').length, droppedDuplicates: holds.length - H.length, patternB: 0, rule: 'runway hold if <= ' + val(H_.runwayHoldMaxFromCL) + ' m from the CL [inf], else intermediate' };

  // ---------------------------------------------------------------------------------------- taxiway centrelines
  const clHalf = val(T_.clW) / 2, clBorder = val(T_.clBorder);
  const off = val(CAAC.runway.clW) / 2 + val(T_.clRunwayOffset) + clHalf;   // 1.2 m: 0.9 m clear of the runway CL stripe
  let leadOns = 0, crossings = 0;
  const centrelines = [];
  for (const t of lines) {
    let pts = t.pts.map(p => p.slice());
    // ends on a runway centreline (OSM taxiways join the runway way): a tangential lead-on / -off is moved 0.9 m clear of
    // the runway CL stripe and continued parallel for 60 m (6.2.8-5); a steep entry or a crossing stops 0.9 m short
    const extra = [];
    for (const R of runways) {
      const W = R.width || 45; const st = (p) => G.rwyAlongAcross(R, p[0], p[1]);
      for (const endIdx of [0, pts.length - 1]) {
        const e = pts[endIdx]; const [se, te] = st(e); if (Math.abs(te) > 1.5 || se < -5 || se > R.len + 5) continue;
        const inward = endIdx === 0 ? 1 : -1; const c = cum(pts); const Ltot = c[c.length - 1];
        const ref = at(pts, c, endIdx === 0 ? Math.min(12, Ltot) : Math.max(0, Ltot - 12)).p;   // 12 m back from the end
        const dir = norm(sub(e, ref)); const along = dot(dir, R.dir); const ang = Math.acos(Math.min(1, Math.abs(along))) * 180 / Math.PI;
        if (ang < 35) {
          // clamp |t| to off on the approach side, then continue parallel along the runway for 60 m
          const sgn = Math.sign(st(ref)[1]) || 1;
          pts = pts.map(p => { const [s, tt] = st(p); if (Math.abs(tt) < off && s > -5 && s < R.len + 5) return G.rwyToWorld(R, s, sgn * off); return p; });
          const e2 = pts[endIdx]; const [s2] = st(e2); const sd = Math.sign(along) || 1;
          const s3 = Math.max(0, Math.min(R.len, s2 + sd * val(T_.clRunwayParallel)));
          extra.push([G.rwyToWorld(R, s2, sgn * off), G.rwyToWorld(R, s3, sgn * off)]); leadOns++;
        } else crossings++;
        void inward; void W;
      }
    }
    // cut: 0.9 m clear of the runway CL stripe (crossings) and of the holding markings
    // runway designation zones: the runway marking wins (6.2.1-2), the taxiway line is interrupted over the numerals
    const desig = (p) => { for (const Pl of plan || []) { const [s, tt] = G.rwyAlongAcross(Pl.R, p[0], p[1]); if (Math.abs(tt) > 6.5) continue;
      for (let j = 0; j < 2; j++) { const e = Pl.ends[j]; const xs = (j === 0 ? s : Pl.L - s) - e.disp; if (xs > e.lx0 - 1.5 && xs < e.nx0 + val(CAAC.runway.desigH) + 2) return true; } } return false; };
    const near = (p) => { for (const R of runways) { const [s, tt] = G.rwyAlongAcross(R, p[0], p[1]); if (Math.abs(tt) < off - 0.01 && s > -5 && s < R.len + 5) return true; } return desig(p); };
    for (const q of cutPoly(pts, (p) => near(p) || holdZone(p, val(T_.clClearOfHold)))) centrelines.push({ pts: q, ref: t.ref });
    for (const q of extra) for (const r of cutPoly(q, (p) => holdZone(p, val(T_.clClearOfHold)) || desig(p))) centrelines.push({ pts: r, ref: t.ref, lead: true });
  }
  for (const c of centrelines) {
    // black edges on light pavement (concrete aprons / taxiways), interrupted on the runways (6.2.8-2 and fig. 6.2.8-2 note)
    for (const q of cutPoly(c.pts, (p) => !!onRunway(p, 0.5), 1.0)) B.line(q, clHalf + clBorder, BLK, 1);
    P.line(c.pts, clHalf, YEL, 1);
  }
  info.centrelines = { lines: lines.length, pieces: centrelines.length, runwayLeadOns: leadOns, runwayCrossingsOrSteepEnds: crossings };

  // ---------------------------------------------------------------------------------------- enhanced centrelines
  let enh = 0;
  for (const h of H) {
    if (h.kind !== 'A' || h.exitOnly || !val(T_.enhAtZSSS)) continue;
    const L = h.line; const c = cum(L.pts); const nr = nearestOnPolys([L], h.p, 8); if (!nr) continue;
    // arc length of the hold on its line, then walk away from the runway
    const a = L.pts[nr.i - 1], b = L.pts[nr.i]; const k = Math.max(0, Math.min(1, dot(sub(h.p, a), sub(b, a)) / (dot(sub(b, a), sub(b, a)) || 1)));
    const sh = c[nr.i - 1] + k * (c[nr.i] - c[nr.i - 1]); const away = dot(norm(sub(b, a)), h.u) < 0 ? 1 : -1;
    const start = h.half + bd + val(T_.clClearOfHold), Lg = val(T_.enhLen);
    const s0 = away > 0 ? sh + start : sh - start - Lg, s1 = away > 0 ? sh + start + Lg : sh - start;
    let q = subPoly(L.pts, c, Math.max(0, s0), Math.min(c[c.length - 1], s1)); if (!q || q.length < 2) continue;
    if (away < 0) q = q.reverse();   // from the hold outwards: the dash rhythm starts at the hold
    const dOff = clHalf + val(T_.enhClear) + val(T_.enhDashW) / 2;
    B.line(q, dOff + val(T_.enhDashW) / 2 + clBorder, BLK, 1);
    for (const sg of [-1, 1]) P.line(q, val(T_.enhDashW) / 2, YEL, 1, sg * dOff, [val(T_.enhDash) + val(T_.enhGap), val(T_.enhDash)]);
    enh++;
  }
  info.enhancedCentrelines = enh;

  // ---------------------------------------------------------------------------------------- mandatory instruction markings
  let mand = 0;
  for (const h of H) {
    if (h.kind !== 'A' || h.exitOnly) continue;
    const R = h.R; const lf = leftOf(h.u);
    const e0 = R.ends[0], e1 = R.ends[1]; const leftFirst = dot(sub(R.a, h.p), lf) > dot(sub(R.b, h.p), lf);
    const text = leftFirst ? e0 + '-' + e1 : e1 + '-' + e0;
    const ch = val(M_.charH), mg = val(M_.margin); const tw = textWidth(text, ch); const pw = tw + 2 * mg, ph = ch + 2 * mg;
    const a = -(h.half + bd + val(M_.clearOfHold) + ph / 2); const right = rightOf(h.u);
    for (const sg of [-1, 1]) {
      const bOff = sg * (clHalf + val(M_.clearOfCL) + pw / 2);
      const c = add(h.p, add(mul(h.u, a), mul(h.n, bOff)));
      const C = (x, y) => add(c, add(mul(right, x), mul(h.u, y)));
      P.poly([[C(-pw / 2, -ph / 2), C(pw / 2, -ph / 2), C(pw / 2, ph / 2), C(-pw / 2, ph / 2)]], RED);
      textQuads(T, chars, text, c, right, h.u, ch, WHT);
    }
    h.mandText = text; mand++;
  }
  info.mandatoryMarkings = { holds: mand, plates: 2 * mand, src: 'inf (6.2.12-2: recommended for runway-incursion prevention; ZSSS paint not observed)' };

  // ---------------------------------------------------------------------------------------- taxiway edge lines
  const aprons = polyIndex((A.aprons || []).map(a => [a.ring, ...(a.holes || [])]));
  const twyPolys = ((A.surfaces || {}).taxiway) || []; const twyIdx = polyIndex(twyPolys.map(p => [p.ring, ...(p.holes || [])]));
  const eW = val(T_.edgeLineW), eG = val(T_.edgeLineGap); let edgeM = 0;
  for (const poly of twyPolys) for (const ring of [poly.ring, ...(poly.holes || [])]) {
    if (!ring || ring.length < 3) continue;
    const closed = [...ring, ring[0]];
    // orientation: is the interior on the right of travel?
    let area = 0; for (let i = 0; i < ring.length; i++) { const a = ring[i], b = ring[(i + 1) % ring.length]; area += a[0] * b[1] - b[0] * a[1]; }
    // x east, z south: positive "area" (x z' - x' z) = clockwise on screen with z down... decide by a probe instead
    const mid = mul(add(closed[0], closed[1]), 0.5); const tt = norm(sub(closed[1], closed[0])); const probe = add(mid, mul(rightOf(tt), 0.6));
    const interiorRight = inAny(twyIdx, probe[0], probe[1]);
    const outward = (p, t) => add(p, mul(rightOf(t), interiorRight ? -1.5 : 1.5));
    // keep the boundary parts that border shoulders / grass: not aprons, runways or other paved surfaces
    const keep = [];
    const c = cum(closed); const n = Math.max(2, Math.ceil(c[c.length - 1] / 1.0));
    let run = null;
    for (let k = 0; k <= n; k++) {
      const s = c[c.length - 1] * k / n; const q = at(closed, c, s); const o = outward(q.p, q.t);
      const bad = inAny(aprons, o[0], o[1]) || !!onRunway(o, 1.0) || holdZone(q.p, val(T_.edgeClearOfHold));
      if (!bad) { if (!run) run = [s, s]; else run[1] = s; } else if (run) { keep.push(run); run = null; }
    }
    if (run) keep.push(run);
    for (const [s0, s1] of keep) {
      const q = subPoly(closed, c, s0, s1); if (!q || s1 - s0 < 2) continue;
      const sgn = interiorRight ? 1 : -1;   // + offset = right of travel = interior
      P.line(q, eW / 2, YEL, 0.95, sgn * (eW / 2));
      P.line(q, eW / 2, YEL, 0.95, sgn * (eW * 1.5 + eG));
      edgeM += s1 - s0;
    }
    void area;
  }
  info.taxiwayEdgeLines_m = Math.round(edgeM);

  // ---------------------------------------------------------------------------------------- stands
  const SI = buildStands(ctx, ST, B, P, T, chars);
  info.stands = SI;

  const merged = merge([B, P, T]);
  const items = [];
  if (merged) items.push({ mesh: merged.mesh, prog: 'caacDecal', blend: 'alpha', bothPasses: true, noCull: true, sortKey: () => 1e12, bbox: merged.bbox, castShadow: false, polyOffset: [-2, -6], src: 'inf', layer: 'markings',
    uniforms: () => ({ uPxScale: 2 * Math.tan((ctx.R.curCam ? ctx.R.curCam.fov : 0.9) / 2) / (ctx.R.H || 720), uChars: chars.tex }) });
  ctx.R.addProgram('caacDecal', DECAL_VS, DECAL_FS);
  info.mesh = merged ? { verts: merged.verts, tris: merged.tris } : null; info.ms = Math.round(performance.now() - t0);
  // holds and named junctions for the signs
  const junctions = namedJunctions(TG);
  return { items, info, holds: H, junctions, chars };
}

// ------------------------------------------------------------------------------------------------ stands and apron
const CLASS_FUS = { B: 1.6, C: 2.0, CL: 1.9, D: 2.5, E: 2.8, EL: 3.1, F: 3.25 };   // fuselage half width (m) [inf: reference types]
function standEnvelope(s, refs) {
  const ref = refs[s.cls] || refs.C || { length_m: 44.5, span_m: 35.8 };
  const L = s.len_max || ref.length_m, Sp = s.span_max || ref.span_m, f = CLASS_FUS[s.cls] || 2.0;
  const letter = val(S_.classLetter)[s.cls] || 'C'; const Bc = val(S_.clearB)[letter] || 4.5, E = val(S_.noseE);
  const uRoot = -0.36 * L, uTip = uRoot - (Sp / 2 - f) * 0.62, uBack = -L - 3;
  const local = [[uBack, -(Sp / 2 + Bc)], [uTip, -(Sp / 2 + Bc)], [uRoot, -(f + Bc)], [E, -(f + Bc)], [E, f + Bc], [uRoot, f + Bc], [uTip, Sp / 2 + Bc], [uBack, Sp / 2 + Bc]];
  return { L, Sp, f, B: Bc, E, uRoot, uTip, uBack, local };
}
function buildStands(ctx, ST, B, P, T, chars) {
  const G = ctx.geo; const refs = (ctx.stands && ctx.stands.class_ref) || {};
  const info = { leadins: 0, stopLines: 0, numberPlates: 0, safetyLines: 0, hatchedOverlaps: 0, bridgeAreas: 0, equipmentAreas: 0, src: 'inf: envelopes from the class reference aircraft + table 4.13.5 clearances; lead-ins and stop nodes from OSM (obs)' };
  const apron = { equipment: [], bridge: [], envelopes: [] };   // exported (SHA.markings.apron()): world [x, z] rings, src inf
  Object.defineProperty(info, 'apron', { value: apron, enumerable: false });
  const lw = val(S_.leadW) / 2, lb = val(S_.leadBorder);
  const W = ST.map(s => {
    const h = G.hdgVec(s.hdg); const rn = rightOf(h); const env = standEnvelope(s, refs);
    const toW = ([u, v]) => add(s.nose, add(mul(h, u), mul(rn, v)));
    const poly = env.local.map(toW);
    return { s, h, rn, env, toW, poly, bb: bboxOf(poly) };
  });
  const placed = [];   // stand number plates placed so far ({c, r})
  const inEnv = (w, p) => p[0] >= w.bb.x0 && p[0] <= w.bb.x1 && p[1] >= w.bb.z0 && p[1] <= w.bb.z1 && inRings([w.poly], p[0], p[1]);
  const neighbours = (w) => W.filter(o => o !== w && len(sub(o.s.nose, w.s.nose)) < 160 && !(o.bb.x1 < w.bb.x0 || o.bb.x0 > w.bb.x1 || o.bb.z1 < w.bb.z0 || o.bb.z0 > w.bb.z1));
  for (const w of W) {
    const s = w.s; const nb = neighbours(w);
    // lead-in (OSM lead-in way, ending at the stop node) + alignment continued past the stop line (6.2.16-5 / -6)
    if (s.leadin && s.leadin.length >= 2) {
      const pts = [...s.leadin.map(p => p.slice()), add(s.nose, mul(w.h, val(S_.alignBeyondStop)))];
      B.line(pts, lw + lb, BLK, 1); P.line(pts, lw, YEL, 1); info.leadins++;
      // stand number plate (fig. 6.2.16-2 / -3): yellow pentagon, black 4 m characters, 1 m clear of the lead-in
      const c = cum(pts); const Lt = c[c.length - 1]; const sp = Math.min(val(S_.numAlong), Lt * 0.35);
      if (Lt > 25) {
        const q = at(pts, c, sp); const t0 = at(pts, c, 2).t; const turnRight = dot(q.t, rightOf(t0)) > 0.02;
        const side = turnRight ? -1 : 1;   // the outer side of the lead-in's first turn (left when it turns right)
        const chH = val(S_.numCharH), body = val(S_.numPlateH), pt = val(S_.numPoint), bdr = val(S_.numBorder);
        const tw = textWidth(s.name, chH); const pw = Math.max(tw + 1.2, 4.5);
        const up = q.t, right = rightOf(up);
        const cen = add(q.p, mul(rightOf(q.t), side * (lw + val(S_.numClear) + pw / 2 + bdr)));
        const C = (x, y) => add(cen, add(mul(right, x), mul(up, y)));
        const pent = (m) => [C(-pw / 2 - m, -body / 2 - m), C(pw / 2 + m, -body / 2 - m), C(pw / 2 + m, body / 2), C(0, body / 2 + pt + m * 1.4), C(-pw / 2 - m, body / 2)];
        const r = Math.hypot(pw / 2, (body + pt) / 2) + 0.5;
        if (W.some(o => o !== w && o.s.leadin && segNear(o.s.leadin, cen, pw / 2))) info.platesSkippedOnLine = (info.platesSkippedOnLine || 0) + 1;
        else if (placed.some(o => len(sub(o.c, cen)) < o.r + r)) info.platesSkippedOverlap = (info.platesSkippedOverlap || 0) + 1;   // overlay / alternative stands
        else { B.poly([pent(bdr)], BLK); P.poly([pent(0)], YEL); textQuads(T, chars, s.name, cen, right, up, chH, BLK); placed.push({ c: cen, r }); info.numberPlates++; }
      }
      // stop line at the stop node (6.2.16-7) [inf: the OSM stop node taken as the painted stop line]
      const sl = val(S_.stopLen) / 2; const a = add(s.nose, mul(w.rn, -sl)), b = add(s.nose, mul(w.rn, sl));
      B.line([a, b], val(S_.stopW) / 2 + lb, BLK, 1); P.line([a, b], val(S_.stopW) / 2, YEL, 1); info.stopLines++;
    }
    apron.envelopes.push({ stand: s.name, cls: s.cls, ring: w.poly });
    // stand safety line (6.2.18): red; dashed where it runs inside a neighbour's envelope (the overlap is hatched below)
    const line = [...w.env.local.map(w.toW)];
    const sw = val(S_.safetyW) / 2;
    const parts = splitBy(line, (p) => nb.some(o => inEnv(o, p)));
    for (const pp of parts) P.line(pp.pts, sw, RED, 1, 0, pp.flag ? [val(S_.safetyDash)[0] + val(S_.safetyDash)[1], val(S_.safetyDash)[0]] : null);
    info.safetyLines++;
    // bridge activity area (6.2.17 / 6.2.20): red outline, 45 deg hatching 2 m apart, wheel circle [inf: band from the
    // rotunda to the docked cab]
    for (const br of s.bridges || []) {
      if (!br.rotunda || !br.cab) continue;
      const ax = norm(sub(br.cab, br.rotunda)); const n = rightOf(ax); const hwb = val(S_.bridgeAreaHalfW); const Lb = len(sub(br.cab, br.rotunda)) + 2;
      const Q = (x, y) => add(br.rotunda, add(mul(ax, x), mul(n, y)));
      const ring = [Q(3, -hwb), Q(Lb, -hwb), Q(Lb, hwb), Q(3, hwb), Q(3, -hwb)];
      P.line(ring, val(S_.bridgeOutlineW) / 2, RED, 1); apron.bridge.push({ stand: s.name, ring: ring.slice(0, 4) });
      hatch(P, [ring.slice(0, 4)], [], ax, val(S_.bridgeHatchGap), val(S_.hatchW) / 2, RED);
      const wc = Q(Lb * 0.62, 0); const circ = []; for (let k = 0; k <= 24; k++) { const a = k / 24 * 2 * Math.PI; circ.push(add(wc, [Math.cos(a) * 1.5, Math.sin(a) * 1.5])); }
      P.line(circ, 0.06, RED, 1); info.bridgeAreas++;
    }
    // equipment areas (6.2.20): white outline + "设备区" (white 黑体), beside the fuselage ahead of the wing, outside every
    // safety envelope, not on the bridge side [inf]
    const bridgeSide = (s.bridges && s.bridges[0] && s.bridges[0].cab) ? Math.sign(dot(sub(s.bridges[0].cab, s.nose), w.rn)) : 0;
    for (const sg of [-1, 1]) {
      if (sg === bridgeSide) continue;
      const e = w.env; const v0 = e.f + e.B + 1.5; let wq = Math.min(9, e.Sp / 2 + e.B - v0 - 1);
      const u0 = e.uRoot + 3, u1 = e.E - 0.5; if (u1 - u0 < 8) continue;
      let ok = false;
      for (; wq >= 4; wq -= 1) {
        const cs = [[u0, v0], [u1, v0], [u1, v0 + wq], [u0, v0 + wq], [(u0 + u1) / 2, v0 + wq / 2]].map(([u, v]) => w.toW([u, sg * v]));
        if (!cs.some(p => W.some(o => o !== w && inEnv(o, p)))) { ok = true; break; }
      }
      if (!ok) continue;
      const ring = [[u0, v0], [u1, v0], [u1, v0 + wq], [u0, v0 + wq], [u0, v0]].map(([u, v]) => w.toW([u, sg * v]));
      P.line(ring, val(S_.equipW) / 2, WHT, 1); apron.equipment.push({ stand: s.name, side: sg, ring: ring.slice(0, 4) });
      const c = w.toW([(u0 + u1) / 2, sg * (v0 + wq / 2)]);
      const up = mul(w.h, -1);   // text against the parking direction (as 6.2.20-2 asks for the chock boxes) [inf]
      textQuads(T, chars, String(val(S_.equipText)), c, rightOf(up), up, Math.min(1.6, wq * 0.3), WHT);
      info.equipmentAreas++;
    }
  }
  // hatched overlaps of adjacent safety envelopes (6.2.18-5): 0.1 m red lines at 45 deg, 2 m clear
  const done = new Set();
  for (const w of W) for (const o of neighbours(w)) {
    const key = [w.s.name, o.s.name].sort().join('|'); if (done.has(key)) continue; done.add(key);
    const n = hatch(P, [w.poly], [o.poly], w.h, val(S_.hatchGap) + val(S_.hatchW), val(S_.hatchW) / 2, RED);
    if (n) info.hatchedOverlaps++;
  }
  return info;
}
function segNear(pl, p, r) { for (let i = 1; i < pl.length; i++) if (segDist(p, pl[i - 1], pl[i]) < r) return true; return false; }
/** split a polyline into runs by flag(p) (sampled every 0.5 m): [{pts, flag}] */
function splitBy(pts, flag) {
  const c = cum(pts), Lt = c[c.length - 1]; const n = Math.max(1, Math.ceil(Lt / 0.5)); const out = []; let s0 = 0, f0 = flag(pts[0]);
  for (let k = 1; k <= n; k++) { const s = Lt * k / n; const f = flag(at(pts, c, s).p); if (f !== f0 || k === n) { const q = subPoly(pts, c, s0, s); if (q) out.push({ pts: q, flag: f0 }); s0 = s; f0 = f; } }
  return out;
}
/** 45-degree hatching (to the axis ax) inside all of `inside` polygons and (if given) all of `also`; returns segment count */
function hatch(L, inside, also, ax, pitch, hw, color) {
  const d = norm(add(ax, rightOf(ax))); const nrm = rightOf(d);   // hatch direction at 45 deg to ax
  const all = [...inside[0]]; const bb = bboxOf(all); const cx = [(bb.x0 + bb.x1) / 2, (bb.z0 + bb.z1) / 2]; const R = Math.hypot(bb.x1 - bb.x0, bb.z1 - bb.z0) / 2 + 1;
  const ok = (p) => inside.every(r => inRings([r], p[0], p[1])) && (!also.length || also.every(r => inRings([r], p[0], p[1])));
  let n = 0;
  for (let o = -R; o <= R; o += pitch) {
    const a = add(cx, add(mul(nrm, o), mul(d, -R))), b = add(cx, add(mul(nrm, o), mul(d, R)));
    let run = null; const steps = Math.ceil(2 * R / 0.3);
    for (let k = 0; k <= steps; k++) {
      const p = add(a, mul(sub(b, a), k / steps)); const inn = ok(p);
      if (inn && !run) run = [p, p]; else if (inn) run[1] = p;
      if ((!inn || k === steps) && run) { if (len(sub(run[1], run[0])) > 0.6) { L.line([run[0], run[1]], hw, color, 1); n++; } run = null; }
    }
  }
  return n;
}

// ------------------------------------------------------------------------------------------------ named junctions (signs)
// taxi-graph nodes where two or more differently named taxiways meet: {p, refs: {ref: [unit directions away from p]}}
function namedJunctions(TG) {
  const nodes = new Map((TG.nodes || []).map(n => [n.id, n])); const jm = new Map();
  for (const l of TG.links || []) {
    if (!l.ref || l.kind !== 'taxiway' || !l.pts || l.pts.length < 2) continue;
    for (const [nid, pts] of [[l.a, l.pts], [l.b, [...l.pts].reverse()]]) {
      const n = nodes.get(nid); if (!n) continue;
      const c = cum(pts); const q = at(pts, c, Math.min(25, c[c.length - 1])).p; const dir = norm(sub(q, pts[0]));
      if (!jm.has(nid)) jm.set(nid, { id: nid, p: [n.x, n.z], arms: [] });
      jm.get(nid).arms.push({ ref: l.ref, dir, link: l.id, len: c[c.length - 1], pts });
    }
  }
  return [...jm.values()].filter(j => new Set(j.arms.map(a => a.ref)).size >= 2);
}
