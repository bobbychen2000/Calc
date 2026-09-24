// Airfield surface markings as anti-aliased decal ribbons, built to FAA AC 150/5340-1 dimensions:
//   taxiway centerline 6 in yellow; enhanced centerline: dashed 9 ft / 3 ft gaps each side for 150 ft before a hold line;
//   runway holding position: 4 yellow lines 12 in wide, 12 in apart (2 solid on the holding side, 2 dashed 3 ft / 3 ft);
//   taxiway edge: two continuous 6 in lines 6 in apart; ramp service road: white 6 in lines, dashed centre.
// Lines keep a minimum on-screen width (with proportionally reduced opacity) so they stay stable at a distance.
import { Mesh } from '../gl.js';
import { GROUND_Y } from '../geo.js';

const FT = 0.3048, IN = 0.0254;
const YEL = [0.85, 0.6, 0.06], WHT = [0.86, 0.86, 0.84], RED = [0.55, 0.03, 0.03];

export const MARK_VS = `
#include <common>
#include <vout>
layout(location=0) in vec3 aPos; layout(location=1) in vec3 aNrm; layout(location=3) in vec4 aCol; layout(location=4) in vec4 aExtra;
uniform float uPxScale; // world size of one pixel at unit distance
out vec3 vWP; out vec4 vCol; out vec3 vDash; out float vA;
void main(){
  // aNrm.xz = unit perpendicular, aExtra = (half width, side -1/+1, distance along line, dash period (0 = solid))
  float dist = length(aPos - uCamPos);
  float px = dist * uPxScale * 0.75;
  float hw = max(aExtra.x, px);
  vA = aExtra.x / hw;
  vec3 wp = aPos + vec3(aNrm.x, 0.0, aNrm.z) * aExtra.y * hw;
  vWP = wp; vCol = aCol; vDash = vec3(aExtra.z, aExtra.w, aNrm.y); // along, period, duty ratio
  emitClip(wp, wp);
}`;
export const MARK_FS = `
#include <common>
#include <shadow>
#include <fout>
in vec3 vWP; in vec4 vCol; in vec3 vDash; in float vA;
uniform float uNight;
void main(){
  vec3 wp = vWP; vec3 V = uCamPos - wp; float dist = length(V); V /= dist;
  float a = vCol.a * vA;
  if (vDash.y > 0.0) {
    float period = vDash.y; float duty = vDash.z * period;
    float f = mod(vDash.x, period); float fw = fwidth(vDash.x) + 1e-4;
    a *= smoothstep(-fw, fw, f) * (1.0 - smoothstep(duty - fw, duty + fw, f));
    a *= 1.0 - smoothstep(0.35 * period, 1.0 * period, fw); // far away the dash pattern averages out
  }
  a *= 1.0 - smoothstep(2500.0, 6000.0, dist);
  if (a < 0.003) discard;
  vec3 N = vec3(0, 1, 0);
  float sh = getShadow(wp, N, dist) * cloudShadow(wp);
  vec3 alb = vCol.rgb * (0.82 + 0.18 * texture(uNoise, wp.xz * 0.23).r);
  vec3 col = shadePBR(alb, N, V, 0.6, 0.0, sh, 1.0, 0.6);
  col = applyFog(col, wp);
  writeOut(col, wp, a);
}`;

class Ribbons {
  constructor() { this.pos = []; this.nrm = []; this.col = []; this.ext = []; this.idx = []; }
  // polyline pts [[x,z],...]; offset: lateral offset from the line (m, + = right of travel); hw: half width; dash: [period, duty] (m)
  line(pts, hw, color, alpha = 1, offset = 0, dash = null, s0 = 0) {
    if (pts.length < 2) return;
    const n = pts.length; const P = [], N = []; let s = s0; const S = [];
    for (let i = 0; i < n; i++) {
      const a = pts[Math.max(0, i - 1)], b = pts[Math.min(n - 1, i + 1)];
      let dx = b[0] - a[0], dz = b[1] - a[1]; const l = Math.hypot(dx, dz) || 1; dx /= l; dz /= l;
      // perpendicular (right of travel in x-east / z-south frame)
      let nx = -dz, nz = dx;
      // miter correction at joints
      if (i > 0 && i < n - 1) {
        const d1 = [pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]], d2 = [pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]];
        const l1 = Math.hypot(...d1) || 1, l2 = Math.hypot(...d2) || 1; const n1 = [-d1[1] / l1, d1[0] / l1];
        const dot = n1[0] * nx + n1[1] * nz; const k = 1 / Math.max(0.5, dot); nx *= k; nz *= k;
      }
      if (i > 0) s += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
      P.push([pts[i][0] + nx * offset, pts[i][1] + nz * offset]); N.push([nx, nz]); S.push(s);
    }
    const base = this.pos.length / 3; const period = dash ? dash[0] : 0, ratio = dash ? dash[1] / dash[0] : 0;
    for (let i = 0; i < n; i++) for (const side of [-1, 1]) {
      this.pos.push(P[i][0], GROUND_Y + 0.03, P[i][1]); this.nrm.push(N[i][0], ratio, N[i][1]);
      this.col.push(color[0], color[1], color[2], alpha); this.ext.push(hw, side, S[i], period);
    }
    for (let i = 0; i < n - 1; i++) { const a = base + i * 2; this.idx.push(a, a + 2, a + 1, a + 1, a + 2, a + 3); }
  }
  // rectangle centred at c (x,z), u = unit along, lengths
  rect(c, u, len, wid, color, alpha = 1) {
    const hl = len / 2; this.line([[c[0] - u[0] * hl, c[1] - u[1] * hl], [c[0] + u[0] * hl, c[1] + u[1] * hl]], wid / 2, color, alpha);
  }
  mesh() {
    if (!this.idx.length) return null;
    return new Mesh({ pos: new Float32Array(this.pos), nrm: new Float32Array(this.nrm), col: new Float32Array(this.col), extra: new Float32Array(this.ext), idx: new Uint32Array(this.idx) });
  }
}
function polyLen(p) { let L = 0; for (let i = 1; i < p.length; i++) L += Math.hypot(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]); return L; }
function cutFrom(p, fromStart, len) { // sub-polyline of length len from one end (fromStart) of p
  const q = fromStart ? p : p.slice().reverse(); const out = [q[0]]; let acc = 0;
  for (let i = 1; i < q.length; i++) { const d = Math.hypot(q[i][0] - q[i - 1][0], q[i][1] - q[i - 1][1]); if (acc + d >= len) { const t = (len - acc) / d; out.push([q[i - 1][0] + (q[i][0] - q[i - 1][0]) * t, q[i - 1][1] + (q[i][1] - q[i - 1][1]) * t]); break; } out.push(q[i]); acc += d; }
  return fromStart ? out : out.reverse();
}

// the centerline polyline through (near) point p, walked from p in direction dir for len metres (skipping the first
// `skip` metres): [[x,z],...] or null
function centerlineBack(cls, p, dir, len, skip) {
  let best = null, bd = 6;
  for (const pl of cls) for (let i = 1; i < pl.length; i++) {
    const a = pl[i - 1], b = pl[i]; const dx = b[0] - a[0], dz = b[1] - a[1]; const L2 = dx * dx + dz * dz; if (L2 < 1e-6) continue;
    const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L2)); const d = Math.hypot(p[0] - a[0] - dx * t, p[1] - a[1] - dz * t);
    if (d < bd) { bd = d; best = { pl, i, t }; }
  }
  if (!best) return null;
  const { pl, i, t } = best; const a = pl[i - 1], b = pl[i];
  const start = [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
  const fwd = (b[0] - a[0]) * dir[0] + (b[1] - a[1]) * dir[1] > 0; // walk towards b (forward) or towards a
  const out = [start]; let acc = 0; let prev = start; let k = fwd ? i : i - 1;
  while (k >= 0 && k < pl.length && acc < len + skip) {
    const q = pl[k]; const d = Math.hypot(q[0] - prev[0], q[1] - prev[1]);
    if (acc + d >= len + skip) { const f = (len + skip - acc) / d; out.push([prev[0] + (q[0] - prev[0]) * f, prev[1] + (q[1] - prev[1]) * f]); acc = len + skip; break; }
    if (d > 1e-3) out.push(q); acc += d; prev = q; k += fwd ? 1 : -1;
  }
  // drop the first `skip` metres
  const res = []; let s = 0;
  for (let j = 0; j < out.length; j++) {
    if (j > 0) s += Math.hypot(out[j][0] - out[j - 1][0], out[j][1] - out[j - 1][1]);
    if (s >= skip) { if (!res.length && j > 0) { const d = Math.hypot(out[j][0] - out[j - 1][0], out[j][1] - out[j - 1][1]); const f = (s - skip) / Math.max(d, 1e-6); res.push([out[j][0] - (out[j][0] - out[j - 1][0]) * f, out[j][1] - (out[j][1] - out[j - 1][1]) * f]); } res.push(out[j]); }
  }
  return res.length >= 2 ? res.reverse() : null; // drawn from the far end towards the hold line
}
export function buildMarkings(details) {
  const R = new Ribbons();
  const cl = details.centerlines || [];
  // taxiway centerlines
  for (const p of cl) R.line(p, 3 * IN, YEL, 1);
  // runway holding positions + enhanced centerline + painted holding position signs
  for (const h of details.holds || []) {
    const u = h.dir, n = [-u[1], u[0]]; // u points toward the runway
    const a = h.a, b = h.b; const L = Math.hypot(b[0] - a[0], b[1] - a[1]);
    const mid = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
    if (h.kind === 'ils') {
      // ILS critical-area holding position (FAA AC 150/5340-1M fig. A-8): two solid 12 in lines 2 ft apart, joined by
      // pairs of 12 in bars (2 ft apart) every 10 ft across the taxiway: 4 ft deep in total
      for (const s of [-1, 1]) {
        const off = s * 18 * IN; const c = [mid[0] + u[0] * off, mid[1] + u[1] * off];
        R.line([[c[0] - n[0] * L / 2, c[1] - n[1] * L / 2], [c[0] + n[0] * L / 2, c[1] + n[1] * L / 2]], 6 * IN, YEL, 1);
      }
      for (let x = -L / 2 + 0.3; x <= L / 2 - 0.3; x += 10 * FT) for (const d of [-12 * IN, 12 * IN]) {
        const q = [mid[0] + n[0] * (x + d), mid[1] + n[1] * (x + d)];
        R.line([[q[0] - u[0] * 6 * IN, q[1] - u[1] * 6 * IN], [q[0] + u[0] * 6 * IN, q[1] + u[1] * 6 * IN]], 6 * IN, YEL, 1);
      }
      continue;
    }
    // four 12 in lines, 12 in apart: two solid (holding side, i.e. away from the runway), two dashed (runway side)
    for (let k = 0; k < 4; k++) {
      const off = (-1.5 + k) * 2 * 12 * IN; // centres at -36, -12, +12, +36 in along u
      const c = [mid[0] + u[0] * off, mid[1] + u[1] * off];
      const seg = [[c[0] - n[0] * L / 2, c[1] - n[1] * L / 2], [c[0] + n[0] * L / 2, c[1] + n[1] * L / 2]];
      R.line(seg, 6 * IN, YEL, 1, 0, k >= 2 ? [6 * FT, 3 * FT] : null);
    }
    // enhanced centerline: dashes 9 ft long with 3 ft gaps, 6 in wide, either side of the centerline, over the last
    // 150 ft before the hold line, following the actual centerline polyline
    const path = h.secondary ? null : centerlineBack(cl, h.p, [-u[0], -u[1]], 150 * FT, 0.6);
    if (path) for (const sg of [-1, 1]) R.line(path, 3 * IN, YEL, 1, sg * 12 * IN, [12 * FT, 9 * FT]);
  }
  // taxiway edge markings (continuous: two 6 in lines, 6 in apart)
  for (const e of details.edges || []) { R.line(e, 3 * IN, YEL, 0.95, -4.5 * IN); R.line(e, 3 * IN, YEL, 0.95, 4.5 * IN); }
  // ramp service road: white edge lines and dashed centre (10 ft dashes, 20 ft gaps)
  for (const r of details.roads || []) R.line(r.pts, 3 * IN, WHT, 0.9, 0, r.off > 10 ? null : null);
  const roadPairs = (details.roads || []);
  for (const r of roadPairs) if (r.off > 10) R.line(r.pts, 3 * IN, WHT, 0.85, -3.7, [30 * FT, 10 * FT]);
  return R.mesh();
}
// stand markings for the surveyed contact stands: lead-in line along the mapped (possibly curved) lead-in (6 in yellow), nose-gear stop
// bars for the stand's range of types, and the red equipment-staging boxes found in the satellite imagery
export function buildStandMarks(gates, boxes = [], gridDir = null) {
  const R = new Ribbons();
  for (const g of gates) {
    if (!g.bridge || !g.w) continue;
    const f = [g.w.dx, g.w.dz], n = [-f[1], f[0]];
    const nose = [g.w.x, g.w.z];
    const back = (d) => [nose[0] - f[0] * d, nose[1] - f[1] * d];
    // lead-in: the painted line as mapped (OSM lead-in way, curved where the paint curves; data/sfo_stands.json
    // 'leadin'), continued straight to 1.5 m past the nose point; a straight line only where the data has none
    const L = g.leadinW;
    if (L && L.length >= 2) {
      const last = L[L.length - 1]; const ahead = (last[0] - nose[0]) * f[0] + (last[1] - nose[1]) * f[1];
      R.line(ahead < 1.5 ? [...L, back(-1.5)] : L, 3 * IN, YEL, 1);
    } else R.line([back(-1.5), back(g.maxLen + 28)], 3 * IN, YEL, 1);
    // stop bars for the nose gear of small / large types on this stand (3 ft wide bars, 1 ft deep)
    const bars = g.wide ? [5.2, 6.4] : [3.6, 5.0];
    for (const d of bars) { const c = back(d); R.line([[c[0] - n[0] * 1.2, c[1] - n[1] * 1.2], [c[0] + n[0] * 1.2, c[1] + n[1] * 1.2]], 6 * IN, YEL, 1); }
  }
  const u = gridDir || [0.884, 0.467], v = [-u[1], u[0]];
  for (const [x, z, sz] of boxes) {
    const h = sz / 2 - 0.15; const c = (a, b) => [x + u[0] * a + v[0] * b, z + u[1] * a + v[1] * b];
    R.line([c(-h, -h), c(h, -h), c(h, h), c(-h, h), c(-h, -h)], 6 * IN, RED, 0.85);
  }
  return R.mesh();
}
export { YEL, WHT, RED };
