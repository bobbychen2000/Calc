// HWD surface paint as decal geometry: runway markings (FAA AC 150/5340-1M Chg 1), taxiway centrelines, runway holding
// position markings and the Green Ramp tie-down tees.
// Forked from sfo3d/js/live/markings.js @ a967f9b. Kept: the anti-aliased decal ribbon technique (MARK_VS / MARK_FS:
// lines keep a minimum on-screen width with proportionally reduced opacity, dash patterns averaged out far away, lit with
// the PBR sun + sky + shadows + fog), the Ribbons builder (miter joints, dash period / duty) and its colours. Changed:
// the vertex y follows the HWD ground (site.groundY + LIFT; sfo3d used the flat GROUND_Y + 0.03) and long lines are
// subdivided to <= SEG m so they follow the runway profiles; area polygons (runway stripes, bars, arrowheads, the
// designator glyphs) are drawn by the same program without the minimum-width widening (aExtra.x < 0); all SFO data
// inputs (sfo_details centrelines / holds / enhanced centrelines, stand lead-ins, red boxes) are replaced by
// data/hwd_airport.json + js/geo.js. Dropped: stand marks (no stands at HWD), enhanced taxiway centrelines (whether
// HWD paints them is not established; Part 139 status not read).
//
// Every dimension below cites AC 150/5340-1M (Chg 1, 12/23/2020; the full AC is in refs/cache/local/faa/, paras 2.8,
// 2.9.1 and 3.3.4.1 are also committed in refs/cache/faa/ac150_5340_1m_chg1_p52-54_63.pdf). Feet are converted with
// FT = 0.3048 (geo.js). Where the AC leaves a choice, or the layout is read from NAIP 2024 (public domain), the inventory
// record says so (src 'inf' / 'obs').
import { Mesh } from '../gl.js';
import { FT, RWY_ENDS, RWY_DATA, RWY_PAIRS, rwyAxis, thrDispM } from '../geo.js';
import { earcut } from '../world/earcut.js';

const IN = 0.0254;
export const LIFT = 0.03;     // paint above the ground surface (m), as sfo3d (+ polygon offset in the render item)
const SEG = 8;                // max piece length along a line / runway (m): the ground mesh is a 10 m grid
// paint albedo (linear): sfo3d markings.js colours (white, yellow FS 33538)
export const WHT = [0.80, 0.80, 0.78], YEL = [0.85, 0.6, 0.06];

export const PAINT_VS = `
#include <common>
#include <vout>
layout(location=0) in vec3 aPos; layout(location=1) in vec3 aNrm; layout(location=3) in vec4 aCol; layout(location=4) in vec4 aExtra;
uniform float uPxScale; // world size of one pixel at unit distance
out vec3 vWP; out vec4 vCol; out vec3 vDash; out float vA;
void main(){
  // ribbons: aNrm.xz = unit perpendicular, aExtra = (half width, side -1/+1, distance along line, dash period (0 = solid));
  // polygons: aExtra.x < 0 (drawn as given)
  vec3 wp = aPos; vA = 1.0; vDash = vec3(0.0);
  if (aExtra.x >= 0.0) {
    float dist = length(aPos - uCamPos);
    float px = dist * uPxScale * 0.75;
    float hw = max(aExtra.x, px);
    vA = aExtra.x / hw;
    wp = aPos + vec3(aNrm.x, 0.0, aNrm.z) * aExtra.y * hw;
    vDash = vec3(aExtra.z, aExtra.w, aNrm.y); // along, period, duty ratio
  }
  vWP = wp; vCol = aCol;
  emitClip(wp, wp);
}`;
export const PAINT_FS = `
#include <common>
#include <shadow>
#include <fout>
in vec3 vWP; in vec4 vCol; in vec3 vDash; in float vA;
void main(){
  vec3 wp = vWP; vec3 V = uCamPos - wp; float dist = length(V); V /= dist;
  float a = vCol.a * vA;
  if (vDash.y > 0.0) {
    float period = vDash.y; float duty = vDash.z * period;
    float f = mod(vDash.x, period); float fw = fwidth(vDash.x) + 1e-4;
    a *= smoothstep(-fw, fw, f) * (1.0 - smoothstep(duty - fw, duty + fw, f));
    a *= 1.0 - smoothstep(0.35 * period, 1.0 * period, fw); // far away the dash pattern averages out
  }
  a *= 1.0 - smoothstep(4000.0, 8000.0, dist);
  if (a < 0.003) discard;
  vec3 N = vec3(0, 1, 0);
  float sh = getShadow(wp, N, dist) * cloudShadow(wp);
  // worn paint: low-frequency fading and fine grain (no source for the paint condition; NASR marking condition GOOD)
  vec3 alb = vCol.rgb * (0.80 + 0.2 * texture(uNoise, wp.xz * 0.23).r) * (0.9 + 0.1 * texture(uNoise, wp.xz * 0.011).b);
  vec3 col = shadePBR(alb, N, V, 0.6, 0.0, sh, 1.0, 0.6);
  col = applyFog(col, wp);
  writeOut(col, wp, a);
}`;

// ------------------------------------------------------------------ geometry accumulator
class Paint {
  constructor(groundY) { this.gy = groundY; this.pos = []; this.nrm = []; this.col = []; this.ext = []; this.idx = []; this.tris = 0; }
  y(x, z) { return this.gy(x, z) + LIFT; }
  // ribbon along polyline pts [[x, z], ...]: hw half width, offset lateral (+ right of travel), dash [period, on]
  line(pts, hw, color, alpha = 1, dash = null, s0 = 0) {
    pts = densify(pts, SEG); if (pts.length < 2) return;
    const n = pts.length; const P = [], N = [], S = []; let s = s0;
    for (let i = 0; i < n; i++) {
      const a = pts[Math.max(0, i - 1)], b = pts[Math.min(n - 1, i + 1)];
      let dx = b[0] - a[0], dz = b[1] - a[1]; const l = Math.hypot(dx, dz) || 1; dx /= l; dz /= l;
      let nx = -dz, nz = dx;
      if (i > 0 && i < n - 1) {
        const d1 = [pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]]; const l1 = Math.hypot(d1[0], d1[1]) || 1; const n1 = [-d1[1] / l1, d1[0] / l1];
        const k = 1 / Math.max(0.5, n1[0] * nx + n1[1] * nz); nx *= k; nz *= k;
      }
      if (i > 0) s += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
      P.push(pts[i]); N.push([nx, nz]); S.push(s);
    }
    const base = this.pos.length / 3; const period = dash ? dash[0] : 0, ratio = dash ? dash[1] / dash[0] : 0;
    for (let i = 0; i < n; i++) for (const side of [-1, 1]) {
      this.pos.push(P[i][0], this.y(P[i][0], P[i][1]), P[i][1]); this.nrm.push(N[i][0], ratio, N[i][1]);
      this.col.push(color[0], color[1], color[2], alpha); this.ext.push(hw, side, S[i], period);
    }
    for (let i = 0; i < n - 1; i++) { const a = base + i * 2; this.idx.push(a, a + 2, a + 1, a + 1, a + 2, a + 3); this.tris += 2; }
  }
  // simple polygon (optionally with holes) in world [x, z]; triangulated with earcut
  poly(outer, color, holes = []) {
    const flat = [], hi = []; for (const p of outer) flat.push(p[0], p[1]);
    for (const h of holes) { hi.push(flat.length / 2); for (const p of h) flat.push(p[0], p[1]); }
    const tri = earcut(flat, hi.length ? hi : undefined);
    const base = this.pos.length / 3;
    for (let i = 0; i < flat.length; i += 2) { const x = flat[i], z = flat[i + 1]; this.pos.push(x, this.y(x, z), z); this.nrm.push(0, 0, 0); this.col.push(color[0], color[1], color[2], 1); this.ext.push(-1, 0, 0, 0); }
    // earcut winding is irrelevant: the item is drawn without culling
    for (let i = 0; i < tri.length; i += 3) { this.idx.push(base + tri[i], base + tri[i + 1], base + tri[i + 2]); this.tris++; }
  }
  mesh() {
    if (!this.idx.length) return null;
    return new Mesh({ pos: new Float32Array(this.pos), nrm: new Float32Array(this.nrm), col: new Float32Array(this.col), extra: new Float32Array(this.ext), idx: new Uint32Array(this.idx) });
  }
  bbox() { const b = [1e9, 1e9, 1e9, -1e9, -1e9, -1e9]; for (let i = 0; i < this.pos.length; i += 3) for (let k = 0; k < 3; k++) { b[k] = Math.min(b[k], this.pos[i + k]); b[k + 3] = Math.max(b[k + 3], this.pos[i + k]); } b[1] -= 1; b[4] += 1; return b; }
}
function densify(pts, maxL) {
  const out = [pts[0]];
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1], b = pts[i]; const L = Math.hypot(b[0] - a[0], b[1] - a[1]); const n = Math.max(1, Math.ceil(L / maxL));
    for (let k = 1; k <= n; k++) out.push([a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n]);
  }
  return out;
}
export function polyLen(p) { let L = 0; for (let i = 1; i < p.length; i++) L += Math.hypot(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]); return L; }

// ------------------------------------------------------------------ runway designator glyphs (AC Figure A-6)
// In feet, box 20 ft wide x 60 ft high (Fig. A-6 note 2: 60 ft high, 20 ft wide, vertical stroke 5 ft, horizontal
// stroke 10 ft, diagonal stroke 5 ft); x to the pilot's right, y away from the threshold. Each glyph = [outer, holes].
// The stroke layout of 0, 2, 8, L, R and the two-digit "1" (7 ft wide: 5 ft stem + 2 ft flag, Fig. A-6 and Painting
// Note 2 "Numeral 1 is 7 feet wide") follows Fig. A-6 (outline proportions read on a 300 dpi render, +-1 ft) [inf in
// the details: the AC figure is not fully dimensioned].
const R4 = (x0, y0, x1, y1) => [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];
export const GLYPHS = {
  '0': { w: 20, parts: [[R4(0, 0, 20, 60), [R4(5, 10, 15, 50)]]] },
  '1': { w: 7, parts: [[[[2, 0], [7, 0], [7, 60], [2, 60], [0, 57], [0, 50], [2, 50]], []]] },
  '2': { w: 20, parts: [[R4(0, 50, 20, 60), []], [R4(0, 44, 5, 50), []], [R4(15, 34, 20, 50), []],
    [[[0, 10], [6.5, 10], [20, 36], [13.5, 36]], []], [R4(0, 0, 20, 10), []]] },
  '8': { w: 20, parts: [[[[0, 0], [20, 0], [20, 30.5], [16.5, 34], [20, 37.5], [20, 60], [0, 60], [0, 37.5], [3.5, 34], [0, 30.5]],
    [R4(5, 10, 15, 29), R4(5, 39, 15, 49)]]] },
  'L': { w: 20, parts: [[R4(0, 0, 5, 60), []], [R4(5, 0, 20, 10), []]] },
  'R': { w: 20, parts: [[[[0, 0], [5, 0], [5, 25], [20, 25], [20, 60], [0, 60]], [R4(5, 35, 15, 50)]], [[[7, 25], [12.5, 25], [20, 0], [14.5, 0]], []]] },
};

// ------------------------------------------------------------------ runway markings
// Per-end facts beyond NASR (marking type PIR / NPI, displaced thresholds): what precedes each runway end, read on
// NAIP 2024 (out/phase1/crop_2024_<end>_end.png, 0.2 m crops; docs/phase2_world.md section 4):
//   10R, 28L: paved aligned taxiway area before the runway end with a yellow demarcation bar and 4 yellow arrowheads
//             (AC Fig. A-10 case: "aligned taxiway preceding a displaced threshold");
//   10L:      paved area before the end with a white threshold bar at the end and 3 yellow arrowheads (Fig. A-8 case);
//   28R:      a perpendicular taxiway at the end, no threshold bar.
export const END_SCHEME = {
  '10R': { preceded: 'aligned_taxiway', src: 'obs', evidence: 'NAIP 2024 crop 10R end: yellow bar at the runway end, 4 yellow arrowheads on the paved area before it' },
  '28L': { preceded: 'aligned_taxiway', src: 'obs', evidence: 'NAIP 2024 crop 28L end: yellow bar at the runway end, 4 yellow arrowheads on the paved area before it' },
  '10L': { preceded: 'aligned_taxiway', src: 'obs', evidence: 'NAIP 2024 crop 10L end: white threshold bar at the end, 3 yellow arrowheads on the paved area before it' },
  '28R': { preceded: 'none', src: 'obs', evidence: 'NAIP 2024 crop 28R end: threshold stripes, no bar; a taxiway crosses at the end' },
};

// arrowheads across a runway (Fig. A-7 / A-8 chart): count and spacing by runway width W (ft)
function arrowheadRow(Wft) {
  if (Wft >= 100) return { n: 4, pitch: Wft / 4 };   // spacing W/4, to the edge W/8
  if (Wft >= 60) return { n: 3, pitch: Wft / 3 };    // W/3, W/6
  return { n: 2, pitch: Wft / 2 };                   // W/2, W/4
}
// arrowhead chevron (Fig. A-7 detail): 45 ft long, 15 ft across the rear, prong stroke 3 ft; tip at (tip, c), pointing
// +along; returns 2 quads in (along, across) feet
function chevron(tip, c) {
  const L = 45, hw = 7.5, s = 3;
  const t = s * Math.hypot(L, hw) / L;   // across-offset of a prong's inner edge (3 ft measured perpendicular to the prong)
  const apexIn = tip - t * L / hw;       // where the inner edges of the two prongs meet on the axis
  // each prong: rear outer corner, tip, inner apex, rear inner corner
  return [
    [[tip - L, c + hw], [tip, c], [apexIn, c], [tip - L, c + hw - t]],
    [[tip - L, c - hw], [tip - L, c - hw + t], [apexIn, c], [tip, c]],
  ];
}

/**
 * Runway marking geometry for both HWD runways. Returns the inventory (one record per element) used by the docs and
 * the dev page. groundY from the site model.
 */
export function buildRunwayPaint(P) {
  const inv = [];
  const rec = (end, el, n, ac, src, extra = {}) => inv.push({ end, element: el, count: n, ac, src, ...extra });
  for (const [a, b] of RWY_PAIRS) {
    const id = `${a}/${b}`; const D = RWY_DATA[id]; const Wft = D.widthFt; const W = Wft * FT, hw = W / 2;
    const L = rwyAxis(a).length;
    const prec = RWY_ENDS[a].marking === 'PIR';
    const edgeW = (Wft >= 100 ? 36 : 18) * IN;          // 2.8.4: min 36 in for runways >= 100 ft wide, 18 in otherwise
    const clW = (prec ? 36 : 18) * IN;                  // 2.4.4 item 2: 36 in precision, 18 in non-precision
    const th = { [a]: thrDispM(a), [b]: thrDispM(b) };  // surveyed displacement (m) from each end
    // runway-local helper from end `e` (along from that end, across + = right of a pilot landing on e)
    const AX = { [a]: rwyAxis(a), [b]: rwyAxis(b) };
    const W2 = (e, al, ac) => { const A = AX[e]; return [A.origin[0] + al * A.dir[0] + ac * A.right[0], A.origin[1] + al * A.dir[1] + ac * A.right[1]]; };
    const rect = (e, al0, al1, ac0, ac1, col) => {   // split along to <= SEG m
      const n = Math.max(1, Math.ceil((al1 - al0) / SEG));
      for (let k = 0; k < n; k++) { const u0 = al0 + (al1 - al0) * k / n, u1 = al0 + (al1 - al0) * (k + 1) / n; P.poly([W2(e, u0, ac0), W2(e, u1, ac0), W2(e, u1, ac1), W2(e, u0, ac1)], col); }
    };
    const polyFt = (e, base, pts, col, holes = []) => P.poly(pts.map(([u, v]) => W2(e, base + u * FT, v * FT)), col, holes.map(h => h.map(([u, v]) => W2(e, base + u * FT, v * FT))));
    // --- edge stripes (2.8): outer edge on the runway edge, the full length incl. the displaced areas (2.8.4 item 1)
    for (const s of [-1, 1]) rect(a, 0, L, s > 0 ? hw - edgeW : -hw, s > 0 ? hw : -hw + edgeW, WHT);
    rec(id, 'edge stripes', 2, `2.8 (width ${Wft >= 100 ? 36 : 18} in, full length, 2.8.4 item 1)`, 'obs', { note: 'stripes measured on NAIP 2024 / 2022 within 0.12 m of the NASR edges (Phase 1 report section 2)' });
    for (const e of [a, b]) {
      const o = e === a ? b : a; const disp = th[e]; const S = END_SCHEME[e];
      // --- threshold bar (2.9.1): 10 ft white, outboard edge on the (displaced) threshold, between the edge markings;
      // required for a displaced threshold or an aligned taxiway before the threshold (2.9.1.2)
      if (disp > 0 || S.preceded === 'aligned_taxiway') { rect(e, disp, disp + 10 * FT, -(hw - edgeW), hw - edgeW, WHT); rec(e, 'threshold bar', 1, '2.9.1.3 / 2.9.1.5 (10 ft, outboard edge on the threshold)', S.src, { evidence: S.evidence }); }
      // --- threshold stripes (2.5): 20 ft from the threshold, 150 ft long, 5.75 ft stripes and gaps, the two central
      // stripes 11.5 ft apart; count from Table 2-2 (12 for 150 ft, 6 for 75 ft)
      const nStr = Wft >= 150 ? 12 : Wft >= 100 ? 8 : Wft >= 75 ? 6 : 4;
      for (let k = 0; k < nStr / 2; k++) for (const s of [-1, 1]) { const c0 = (11.5 / 2 + k * 11.5) * FT; rect(e, disp + 20 * FT, disp + 170 * FT, s > 0 ? c0 : -c0 - 5.75 * FT, s > 0 ? c0 + 5.75 * FT : -c0, WHT); }
      rec(e, 'threshold stripes', nStr, '2.5.4 + Table 2-2 + Fig. A-1/A-2 (20 ft from the threshold, 150 x 5.75 ft, 11.5 ft central gap)', 'inf', { note: 'AC standard layout; NAIP 2024 shows the stripe groups at all four ends' });
      // --- designation (2.3 + Fig. A-1 / A-6): letter 210-270 ft, numerals 290-350 ft from the threshold, stacked
      const num = e.replace(/[LRC]$/, ''), let_ = e.slice(num.length);
      if (let_) { const g = GLYPHS[let_]; for (const [o2, hs] of g.parts) polyFt(e, disp + 210 * FT, o2.map(([x, y]) => [y, x - g.w / 2]), WHT, hs.map(h => h.map(([x, y]) => [y, x - g.w / 2]))); }
      { const gs = [...num].map(ch => GLYPHS[ch]); const tot = gs.reduce((s, g) => s + g.w, 0) + 15 * (gs.length - 1); let x0 = -tot / 2;
        for (const g of gs) { for (const [o2, hs] of g.parts) polyFt(e, disp + (let_ ? 290 : 210) * FT, o2.map(([x, y]) => [y, x0 + x]), WHT, hs.map(h => h.map(([x, y]) => [y, x0 + x]))); x0 += g.w + 15; } }
      rec(e, `designation ${e}`, 1, '2.3 + Fig. A-1 (stacked: letter 210-270 ft, number 290-350 ft) + Fig. A-6 (60 x 20 ft glyphs, 15 ft numeral spacing)', 'inf');
      // --- displaced threshold arrows (2.9.2 + Fig. A-7): 4 / 3 arrowheads (W/4 or W/3 apart) with tips 5 ft before
      // the threshold; centreline arrows (80 ft tail 1.5 ft wide + 45 ft head = 120 ft) every 200 ft, the last tip
      // 100 ft before the start of the threshold stripes (= 80 ft before the threshold)
      if (disp > 0) {
        const row = arrowheadRow(Wft);
        for (let k = 0; k < row.n; k++) { const c = (k - (row.n - 1) / 2) * row.pitch; for (const q of chevron(disp / FT - 5, c)) polyFt(e, 0, q, WHT); }
        let nA = 0;
        for (let tip = disp / FT - 80; tip - 120 > 0; tip -= 200) {
          for (const q of chevron(tip, 0)) polyFt(e, 0, q, WHT);
          polyFt(e, 0, [[tip - 120, -0.75], [tip - 40, -0.75], [tip - 40, 0.75], [tip - 120, 0.75]], WHT); nA++;
        }
        rec(e, 'displaced-threshold arrowheads', row.n, 'Fig. A-7 (45 ft, 15 ft wide, 3 ft stroke; tips 5 ft before the threshold; chart: n and spacing by width)', 'inf');
        rec(e, 'displaced-area centreline arrows', nA, 'Fig. A-7 (120 ft arrows every 200 ft, last tip 100 ft before the threshold stripes)', 'inf', { note: 'count matches NAIP 2024 (10R 4, 28L 3)' });
      }
      // --- before the runway end: yellow demarcation bar (2.9.3: 3 ft, on the taxiway, its runway-side edge at the
      // start of the runway, across the paved width) + yellow arrowheads (Fig. A-10 / A-8 chart, tips 5 ft before the
      // bar or the threshold bar)
      if (S.preceded === 'aligned_taxiway') {
        const row = arrowheadRow(Wft);
        if (disp > 0) { rect(e, -3 * FT, 0, -hw, hw, YEL); rec(e, 'demarcation bar', 1, '2.9.3.3 / 2.9.3.5 (3 ft yellow, on the taxiway at the start of the runway)', S.src, { evidence: S.evidence }); }
        const tip0 = (disp > 0 ? -3 : 0) - 5;
        for (let k = 0; k < row.n; k++) { const c = (k - (row.n - 1) / 2) * row.pitch; for (const q of chevron(tip0, c)) polyFt(e, 0, q, YEL); }
        rec(e, 'yellow arrowheads (aligned taxiway)', row.n, `2.9.2.4 item 2 + Fig. ${disp > 0 ? 'A-10' : 'A-8'} (tips 5 ft before the ${disp > 0 ? 'demarcation' : 'threshold'} bar [inf for A-10, dimensioned in A-8 only])`, S.src, { evidence: S.evidence });
      }
      // --- aiming point (2.6): 1,020 ft from the threshold; 150 ft long for >= 4,200 ft between thresholds, else
      // 100 ft; width / inner spacing by runway width (2.6.5); Table 2-1: required on precision runways; on
      // non-precision runways only when instrumented and >= 4,200 ft (Note 3) - 10L/28R is 3,108 ft: none
      const between = D.lenFt - RWY_ENDS[e].disp - RWY_ENDS[o].disp;
      if (prec) {
        const apL = between >= 4200 ? 150 : 100; const apW = Wft >= 150 ? 30 : Wft >= 100 ? 20 : Wft >= 75 ? 15 : 12; const apIn = Wft >= 150 ? 72 : Wft >= 100 ? 48 : Wft >= 75 ? 36 : 28.8;
        for (const s of [-1, 1]) rect(e, disp + 1020 * FT, disp + (1020 + apL) * FT, s > 0 ? apIn / 2 * FT : -(apIn / 2 + apW) * FT, s > 0 ? (apIn / 2 + apW) * FT : -apIn / 2 * FT, WHT);
        rec(e, 'aiming point', 2, `2.6.3 / 2.6.5 (1,020 ft; ${apL} ft long because ${between} ft lie between the thresholds; ${apW} ft wide, ${apIn} ft inner spacing)`, 'inf');
        // --- touchdown zone (2.7): groups start 500 ft apart from 20 ft past the threshold (Table 2-3 Note 1);
        // 3-bar group at 520 ft, 2-bar at 1,520 / 2,020, 1-bar at 2,520 / 3,020; bars 75 x 6 ft, 5 ft spaces, inner
        // sides on the aiming point's (2.7.4); pairs that extend within 900 ft of the midpoint between the thresholds
        // are not painted (2.7.3.1) - with 4,192 ft between the HWD thresholds only the 3-bar group remains
        const mid = between / 2; const groups = [[520, 3], [1520, 2], [2020, 2], [2520, 1], [3020, 1]]; let ng = 0;
        for (const [g0, nb] of groups) {
          if (g0 + 75 > mid - 900) continue;
          for (const s of [-1, 1]) for (let k = 0; k < nb; k++) { const c0 = (apIn / 2 + k * 11) * FT; rect(e, disp + g0 * FT, disp + (g0 + 75) * FT, s > 0 ? c0 : -c0 - 6 * FT, s > 0 ? c0 + 6 * FT : -c0, WHT); }
          ng++;
        }
        rec(e, 'touchdown zone bars', ng, '2.7 + Table 2-4 / 2.7.3.1 (900 ft no-marking zone from the midpoint) + 2.7.4 (75 x 6 ft, 5 ft spaces)', 'inf', { note: `${ng} group(s): midpoint ${mid.toFixed(0)} ft from the threshold` });
      }
    }
    // --- centreline (2.4): 120 ft stripes, 80 ft gaps, from 40 ft past the designation (390 ft from each threshold,
    // Fig. A-1); adjustments made near the midpoint by shortening stripes (>= 80 ft) and gaps (>= 40 ft) (2.4.4 item 3)
    {
      const s0 = (th[a] / FT + 390), s1 = (L / FT - th[b] / FT - 390); const Lc = s1 - s0;
      const n = Math.ceil((Lc + 80) / 200); let ex = n * 120 + (n - 1) * 80 - Lc;
      const st = new Array(n).fill(120), gp = new Array(n - 1).fill(80);
      // shrink symmetric pairs around the middle until the excess is absorbed
      const order = []; const m = (n - 1) / 2; for (let i = 0; i < n; i++) order.push(i); order.sort((p, q) => Math.abs(p - m) - Math.abs(q - m));
      for (const i of order) { if (ex <= 1e-6) break; const d = Math.min(40, ex); st[i] -= d; ex -= d; if (i < n - 1 && ex > 1e-6) { const d2 = Math.min(40, ex); gp[i] -= d2; ex -= d2; } }
      let u = s0; for (let i = 0; i < n; i++) { rect(a, u * FT, (u + st[i]) * FT, -clW / 2, clW / 2, WHT); u += st[i] + (gp[i] || 0); }
      rec(id, 'centreline', n, `2.4.4 (120 ft / 80 ft, ${prec ? 36 : 18} in wide; starts 390 ft from each threshold per Fig. A-1; midpoint adjustment 2.4.4 item 3)`, 'inf');
    }
  }
  return inv;
}

// ------------------------------------------------------------------ taxiway / taxilane centrelines, holds, tees
// Runway rectangle test with a margin (m): taxiway centrelines end at the outer edge of the runway edge marking
// (4.2.3.2.1), i.e. at the runway edge; lead-on / lead-off lines on the runway are not drawn (their painted geometry is
// not measured; NAIP 2024 shows them at the 28L displaced area).
function runwayRects() {
  return RWY_PAIRS.map(([a, b]) => { const A = rwyAxis(a); return { A, hw: RWY_DATA[`${a}/${b}`].widthFt * FT / 2, L: A.length }; });
}
function inRunway(R, x, z, m = 0) { for (const r of R) { const px = x - r.A.origin[0], pz = z - r.A.origin[1]; const al = px * r.A.dir[0] + pz * r.A.dir[1], ac = px * r.A.right[0] + pz * r.A.right[1]; if (al >= -m && al <= r.L + m && Math.abs(ac) <= r.hw + m) return true; } return false; }
// split a polyline into the pieces where `inside` is false (tested every 0.25 m); the pieces keep the original vertices
// plus the cut points
function cutWhere(pts, inside) {
  const out = []; let cur = []; let prevIn = inside(pts[0][0], pts[0][1]);
  if (!prevIn) cur.push(pts[0]);
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1], b = pts[i]; const L = Math.hypot(b[0] - a[0], b[1] - a[1]); const n = Math.max(1, Math.ceil(L / 0.25));
    for (let k = 1; k <= n; k++) {
      const p = [a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n]; const now = inside(p[0], p[1]);
      if (now !== prevIn) { if (now) { cur.push(p); if (cur.length > 1) out.push(cur); cur = []; } else cur = [p]; prevIn = now; }
    }
    if (!prevIn) { const q = cur[cur.length - 1]; if (!q || q[0] !== b[0] || q[1] !== b[1]) cur.push(b); }
  }
  if (cur.length > 1) out.push(cur);
  return out.filter(q => polyLen(q) > 0.5);
}

export function buildTaxiPaint(P, airport, site) {
  const inv = []; const RR = runwayRects();
  const holds = airport.holds.map(h => {
    const way = [...airport.taxiways, ...airport.taxilanes].find(w => w.id === h.way);
    const bx = h.bar && h.bar.x != null ? h.bar.x : h.x, bz = h.bar && h.bar.z != null ? h.bar.z : h.z;
    // bar direction: measured (NAIP) or perpendicular to the way at the node [inf]
    let dir = h.bar && h.bar.dir;
    let wayDir = null;
    if (way) { let best = 1e9; for (let i = 1; i < way.pts.length; i++) { const a = way.pts[i - 1], b = way.pts[i]; const dx = b[0] - a[0], dz = b[1] - a[1]; const L2 = dx * dx + dz * dz; if (L2 < 1e-9) continue; const t = Math.max(0, Math.min(1, ((bx - a[0]) * dx + (bz - a[1]) * dz) / L2)); const d = Math.hypot(bx - a[0] - dx * t, bz - a[1] - dz * t); if (d < best) { best = d; const l = Math.sqrt(L2); wayDir = [dx / l, dz / l]; } } }
    if (!dir && wayDir) dir = [-wayDir[1], wayDir[0]];
    const width = way ? (way.width && way.width.naip_src === 'obs' && way.width.naip_grey_width_m ? way.width.naip_grey_width_m : (way.width && way.width.default_m) || 10.67) : 10.67;
    return { h, x: bx, z: bz, dir, width, dirSrc: h.bar && h.bar.dir ? 'obs' : 'inf', way };
  });
  // centrelines (4.2: yellow, 6 in = 0.15 m, 4.2.5.1), interrupted at the runways and at the holding position markings
  let nCl = 0, lenCl = 0;
  const nearHold = (x, z) => { for (const H of holds) { if (!H.dir) continue; const n = [-H.dir[1], H.dir[0]]; const dx = x - H.x, dz = z - H.z; if (Math.abs(dx * n[0] + dz * n[1]) < 7 * 12 * IN / 2 + 0.3 && Math.abs(dx * H.dir[0] + dz * H.dir[1]) < H.width / 2 + 1) return true; } return false; };
  for (const k of ['taxiways', 'taxilanes']) for (const w of airport[k]) {
    if (w.status !== 'open') continue;
    for (const piece of cutWhere(w.pts, (x, z) => inRunway(RR, x, z, 0) || nearHold(x, z))) { P.line(piece, 6 * IN / 2, YEL, 1); nCl++; lenCl += polyLen(piece); }
  }
  inv.push({ element: 'taxiway / taxilane centrelines', count: nCl, length_m: Math.round(lenCl), ac: '4.2 (yellow; 6 in, 4.2.5.1; ends at the runway edge, 4.2.3.2.1; interrupted by holding position markings, 3.3.4.2)', src: 'obs geometry (OSM centrelines, 4 ways moved onto NAIP paint in Phase 1)', note: 'lead-on / lead-off lines on the runways are not drawn' });
  // runway holding position markings, Pattern A (3.3.4.1): 4 lines x 12 in with 12 in spaces (operating ATCT), two
  // solid on the holding side, two dashed (3 ft dashes / 3 ft spaces, Fig. A-13) toward the runway, a dash centred on
  // the taxiway centreline, across the taxiway width
  let nH = 0;
  for (const H of holds) {
    if (!H.dir) continue;
    const u = H.dir; let n = [-u[1], u[0]];
    // n must point from the holding side toward the runway: compare with the direction to the runway centreline
    const r = RR.find(rr => `${rr.A.end}/${rr.A.opp}` === H.h.runway) || RR[0];
    const px = H.x - r.A.origin[0], pz = H.z - r.A.origin[1]; const ac = px * r.A.right[0] + pz * r.A.right[1];
    const toRw = [-r.A.right[0] * Math.sign(ac), -r.A.right[1] * Math.sign(ac)];
    if (n[0] * toRw[0] + n[1] * toRw[1] < 0) n = [-n[0], -n[1]];
    const half = H.width / 2; const LW = 12 * IN;
    for (let k = 0; k < 4; k++) {
      const off = (-1.5 + k) * 2 * LW;     // line centres at -3, -1, +1, +3 x 12 in from the bar centre (toward the runway +)
      const c = [H.x + n[0] * off, H.z + n[1] * off];
      const pts = [[c[0] - u[0] * half, c[1] - u[1] * half], [c[0] + u[0] * half, c[1] + u[1] * half]];
      if (k < 2) P.line(pts, LW / 2, YEL, 1);
      else {
        const per = 6 * FT; const s0 = per - ((half - 1.5 * FT) % per);   // a dash centred on the taxiway centreline (3.3.4.1)
        P.line(pts, LW / 2, YEL, 1, [per, 3 * FT], s0);
      }
    }
    nH++;
  }
  inv.push({ element: 'runway holding position markings (Pattern A)', count: nH, ac: '3.3.4.1 + Fig. A-13 (4 x 12 in lines, 12 in spaces, 3 ft dashes)', src: `obs position / direction for ${holds.filter(H => H.dirSrc === 'obs').length} (NAIP-measured bars), inf direction for ${holds.filter(H => H.dirSrc !== 'obs').length} (perpendicular to the way at the OSM node)` });
  // tie-down tees (Green Ramp): cross-bar 6.0 m on the wing line, stem 4.8 m toward the tail (tools/airport/tiedowns.py,
  // read by eye on NAIP 2024, +-0.5 m; AC 150/5300-13B E.2.3.2); line width 0.3 m [inf]; white (NAIP: "painted white T
  // marks", refs/cache/naip/naip_visual_notes.json). Only tees seen on NAIP (src obs) are painted.
  let nT = 0;
  for (const s of airport.parking) {
    if (s.kind !== 'tiedown' || s.ref_point !== 'tee_junction') continue;
    const seen = s.evidence && s.evidence.tee_seen && s.evidence.tee_seen.length;
    if (!seen) continue;
    const h = s.heading * Math.PI / 180; const f = [Math.sin(h), -Math.cos(h)]; const r = [-f[1], f[0]];   // nose direction, its right
    P.line([[s.x - r[0] * 3.0, s.z - r[1] * 3.0], [s.x + r[0] * 3.0, s.z + r[1] * 3.0]], 0.15, WHT, 1);
    P.line([[s.x, s.z], [s.x - f[0] * 4.8, s.z - f[1] * 4.8]], 0.15, WHT, 1);
    nT++;
  }
  inv.push({ element: 'tie-down tees (Green Ramp)', count: nT, ac: 'AC 150/5300-13B E.2.3.2 (shape); dimensions read on NAIP 2024 (6.0 / 4.8 m, +-0.5 m)', src: 'obs (tee seen on NAIP 2022 and/or 2024); the 14 inferred tie-downs (no tee seen) are not painted' });
  inv.push({ element: 'taxiway edge markings', count: 0, src: 'not drawn', note: 'no source locates them (data/hwd_airport.json not_yet_sourced: marking geometry)' });
  inv.push({ element: 'hot spots', count: 0, src: 'not painted', note: 'chart symbols (AL-5015), not pavement paint' });
  return inv;
}

// geometry + inventory without WebGL (Node-testable)
export function buildPaintData(site, airport) {
  const P = new Paint(site.groundY);
  const runway = buildRunwayPaint(P);
  const taxi = buildTaxiPaint(P, airport, site);
  return { P, inventory: { runway, taxi }, tris: P.tris, verts: P.pos.length / 3 };
}
// All paint as one render item (alpha-blended decal, drawn in both range passes, polygon offset as sfo3d markings)
export function buildPaint(R, site, airport) {
  const D = buildPaintData(site, airport); const mesh = D.P.mesh();
  const item = mesh ? { mesh, prog: 'paint', blend: 'alpha', bothPasses: true, noCull: true, sortKey: () => 1e12, bbox: D.P.bbox(), castShadow: false, polyOffset: [-2, -6],
    uniforms: () => ({ uPxScale: 2 * Math.tan((R.curCam ? R.curCam.fov : 0.9) / 2) / R.H }) } : null;
  return { item, inventory: D.inventory, tris: D.tris, verts: D.verts };
}
