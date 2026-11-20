// sha3d markings extension (markings package; new file - contains edt1d / edt2d forked from sfo3d@e3218d6
// js/world/textures.js): CAAC MH 5001-2021 runway, taxiway, holding-position, stand and apron
// markings, and the taxi-guidance signs. Every dimension comes from js/live/caac_markings.js (clause or 'inf'); the ZSSS
// facts (widths, displaced thresholds, blast pads, PAPI distances) from data/sha_airport.js aip_facts ("AIP (mirror)").
//
// Two layers:
//   1. runway paint, procedural in the ground shader (chunk sha_ground_paint, js/shaders/ground.js hook): threshold
//      stripes, CAAC designation numerals (fig. 6.2.2-2 polygons -> signed-distance atlas), displaced-threshold bar and
//      arrows, pre-threshold chevrons on the blast pads, aiming point at the PAPI origin, touchdown-zone pairs,
//      centreline, edge stripes interrupted at taxiway junctions, tyre rubber; white on both asphalt and concrete;
//   2. decals (js/live/caac_decals.js): taxiway centrelines, edge lines, holding positions A / intermediate, enhanced
//      centrelines, painted mandatory instruction markings, stand lead-ins / stop lines / number plates, stand safety
//      lines with hatching, bridge areas, equipment areas; and signs (js/live/caac_signs.js).
// No FAA constant is used (sfo3d's FAA runway marks, js/live/markings.js and js/live/signs.js are not forked; only the
// ribbon / sign mesh helpers are, with their headers).
import { registerExtension } from './ext.js';
import { gl, texture } from '../gl.js';
import { CAAC, val, stripeLayout, tdzPositions, tdzPairCount, arrowH, glyphWidth, aimStartNoPapi, paramList } from './caac_markings.js';
import { buildDecals } from './caac_decals.js';
import { buildSigns } from './caac_signs.js';

const R_ = CAAC.runway;
const f1 = (x) => Number(x).toFixed(4);
const MAX_RW = 4;
// glyph signed-distance atlas: cells of GW x GH metres at PPM px / m; glyph origin (lower-left of its 9 m box) at (GX0, GY0)
const PPM = 32, GX0 = 0.7, GY0 = 0.8, CW = 170, CH = 352, GW = CW / PPM, GH = CH / PPM, SPREAD = 0.6;
const NG = CAAC.glyphs.order.length;
const gIndex = (ch) => { const i = CAAC.glyphs.order.indexOf(ch); return i < 0 ? -1 : i; };

// ------------------------------------------------------------------------------------------------ runway paint (GLSL)
const sl = { start: val(R_.stripeStart), len: val(R_.stripeLen), w: val(R_.stripeW) };
const GLSL = `
// sha3d runway paint: CAAC MH 5001-2021 (js/live/caac_markings.js). Per runway i: uMkRwA = (ax, az, dx, dz) pavement end of
// the first end + unit direction; uMkRwB = (L, W, CL start s, CL end s); uMkRwC = (aim / TDZ inner half gap, ...).
// Per end k = 2 i + j (j = 0 at ax, 1 at the far end), 4 vec4: e0 (disp, pad, aim, tdzMask), e1 (letter, d1, d2,
// letterX0), e2 (w1, w2, numberX0, -), e3 (stripes per side, stripe gap, arrows, arrow h). x = metres from the pavement end
// inwards, y = metres to the right of a pilot landing on that end.
uniform vec4 uMkRwA[${MAX_RW}]; uniform vec4 uMkRwB[${MAX_RW}]; uniform vec4 uMkRwC[${MAX_RW}]; uniform vec4 uMkEnd[${MAX_RW * 8}];
uniform int uMkNRw; uniform float uMkOn; uniform sampler2D uMkGlyphs; uniform sampler2D uMkEdge;
uniform vec3 uMkWhite; uniform vec3 uMkYellow; uniform vec3 uMkRubber;
float mkBand(float x, float a, float b, float fw){ return clamp(smoothstep(a - fw, a + fw, x) - smoothstep(b - fw, b + fw, x), 0.0, 1.0); }
float mkGlyph(float code, vec2 p, float fw){
  if (code < -0.5) return 0.0;
  vec2 q = (p + vec2(${f1(GX0)}, ${f1(GY0)})) / vec2(${f1(GW)}, ${f1(GH)});
  if (q.x < 0.0 || q.x > 1.0 || q.y < 0.0 || q.y > 1.0) return 0.0;
  float d = (texture(uMkGlyphs, vec2((code + q.x) / ${NG}.0, q.y)).r - 0.5) * ${f1(2 * SPREAD)};   // metres, + inside
  return smoothstep(-fw, fw, d);
}
float mkSeg(vec2 p, vec2 a, vec2 b){ vec2 pa = p - a, ba = b - a; float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0); return length(pa - ba * h); }
// white (x) and yellow (y) coverage of one runway end
vec2 mkEnd(int k, float x, float y, float W, float gHalf, float fw){
  vec4 e0 = uMkEnd[4 * k], e1 = uMkEnd[4 * k + 1], e2 = uMkEnd[4 * k + 2], e3 = uMkEnd[4 * k + 3];
  float disp = e0.x, pad = e0.y, ay = abs(y), hw = W * 0.5; float m = 0.0, my = 0.0;
  if (x < 0.0) {
    // pre-threshold ">" chevrons (6.2.25, fig. 6.2.25): yellow, 0.9 m, 45 deg, apexes ${val(R_.chevronPitch)} m apart; the
    // nearest legs start X/4 before the pavement end; X = W
    if (pad >= ${f1(val(R_.chevronMinLen))} - 0.5 && x > -pad && ay < hw) {
      float u = x + ay, a0 = W * ${f1(val(R_.chevronLastLegFromThr))};
      float kk = max(0.0, floor((a0 - u) / ${f1(val(R_.chevronPitch))} + 0.5)); float d = abs(u - (a0 - kk * ${f1(val(R_.chevronPitch))})) * 0.70711;
      float c = 1.0 - smoothstep(${f1(val(R_.chevronW) / 2)} - fw, ${f1(val(R_.chevronW) / 2)} + fw, d);
      c *= mix(1.0, ${f1(val(R_.chevronW) / val(R_.chevronPitch) * 1.41)}, smoothstep(4.0, 14.0, fw));
      my = max(my, c * mkBand(x, -pad, 0.0, fw));
    }
    return vec2(m, my);
  }
  float xs = x - disp;
  if (disp > 0.5 && xs < 0.0) {
    // permanently displaced threshold (6.2.4-5, fig. 6.2.4 (b)): centreline arrows; first tip ${val(R_.arrowFirstTipBeforeThr)} m before the
    // threshold, ${val(R_.arrowLen)} m long, ${val(R_.arrowGap)} m apart; head h (table 6.2.4-2), legs >= h/12
    float r = -xs - ${f1(val(R_.arrowFirstTipBeforeThr))};
    if (r > -1.0) {
      float n = floor(max(r, 0.0) / ${f1(val(R_.arrowLen) + val(R_.arrowGap))}); float xl = r - n * ${f1(val(R_.arrowLen) + val(R_.arrowGap))};
      if (n < e3.z - 0.5) {
        float h = e3.w; float b = h * ${f1(val(R_.arrowHeadHalfBase))}; float lw = h * ${f1(val(R_.arrowLegW))};
        float dl = mkSeg(vec2(xl, ay), vec2(0.0), vec2(h, b));
        m = max(m, (1.0 - smoothstep(lw * 0.5 - fw, lw * 0.5 + fw, dl)) * step(-0.5, xl));
        m = max(m, mkBand(xl, 2.0, ${f1(val(R_.arrowLen))}, fw) * mkBand(ay, -1.0, ${f1(val(R_.clW) / 2)}, fw));
      }
    }
  }
  // transverse bar at a displaced threshold (6.2.4-4), between the edge stripes
  if (disp > 0.5) m = max(m, mkBand(xs, 0.0, ${f1(val(R_.dthrBarW))}, fw) * mkBand(ay, -1.0, hw - ${f1(val(R_.edgeW))}, fw));
  if (xs < 0.0) return vec2(m, my);
  // threshold stripes (6.2.4): ${sl.len} m from ${sl.start} m, ${sl.w} m wide, fitted gaps, double centre gap
  if (xs > ${f1(sl.start - 2)} && xs < ${f1(sl.start + sl.len + 2)}) {
    float per = e3.x, g = e3.y, P = ${f1(sl.w)} + g; float f = ay - g; float kk = floor(f / P); float ff = f - kk * P;
    float c = (kk >= 0.0 && kk < per) ? mkBand(ff, 0.0, ${f1(sl.w)}, fw) : 0.0;
    c = mix(c, ${f1(sl.w)} / P * step(g, ay) * step(ay, g + per * P), smoothstep(0.6, 2.0, fw));
    m = max(m, c * mkBand(xs, ${f1(sl.start)}, ${f1(sl.start + sl.len)}, fw));
  }
  // designation (6.2.2, fig. 6.2.2-1 (b)): letter, then the number; CAAC numerals 9 m (fig. 6.2.2-2)
  float lx0 = e1.w, nx0 = e2.z;
  if (xs > lx0 - 1.0 && xs < lx0 + 10.0) m = max(m, mkGlyph(e1.x, vec2(y + 1.5, xs - lx0), fw));
  if (xs > nx0 - 1.0 && xs < nx0 + 10.5) {
    float T = e2.x + ${f1(val(R_.digitClearGap))} + e2.y;
    m = max(m, mkGlyph(e1.y, vec2(y + T * 0.5, xs - nx0), fw));
    m = max(m, mkGlyph(e1.z, vec2(y + T * 0.5 - e2.x - ${f1(val(R_.digitClearGap))}, xs - nx0), fw));
  }
  // aiming point (6.2.5): at the visual approach slope origin (the PAPI position, AIP (mirror)); ${val(R_.aimLen)} x ${val(R_.aimW)} m
  float aim = e0.z;
  m = max(m, mkBand(xs, aim, aim + ${f1(val(R_.aimLen))}, fw) * mkBand(ay, gHalf, gHalf + ${f1(val(R_.aimW))}, fw));
  // touchdown zone pairs (6.2.6, pattern A ${val(R_.tdzLen)} x ${val(R_.tdzW)} m), every ${val(R_.tdzPitch)} m from ${val(R_.tdzPitch)} m; omitted pairs masked out
  int mask = int(e0.w + 0.5);
  float kt = floor(xs / ${f1(val(R_.tdzPitch))});
  if (kt >= 1.0 && kt <= 6.0 && ((mask >> (int(kt) - 1)) & 1) == 1) {
    float x0 = kt * ${f1(val(R_.tdzPitch))};
    m = max(m, mkBand(xs, x0, x0 + ${f1(val(R_.tdzLen))}, fw) * mkBand(ay, gHalf, gHalf + ${f1(val(R_.tdzW))}, fw));
  }
  return vec2(m, my);
}
vec4 shaGroundPaint(vec3 wp, float fw, vec4 apt, float paved, inout float rough){
  if (uMkOn < 0.5 || paved < 0.01) return vec4(0.0);
  for (int i = 0; i < ${MAX_RW}; i++) {
    if (i >= uMkNRw) break;
    vec4 ra = uMkRwA[i], rb = uMkRwB[i];
    vec2 p = wp.xz - ra.xy; float s = dot(p, ra.zw), t = -p.x * ra.w + p.y * ra.z;
    float L = rb.x, W = rb.y, hw = W * 0.5;
    if (abs(t) > hw + 1.0 || s < -200.0 || s > L + 200.0) continue;
    int j = s < L * 0.5 ? 0 : 1; int k = 2 * i + j;
    float x = j == 0 ? s : L - s, y = j == 0 ? t : -t;
    vec2 c = mkEnd(k, x, y, W, uMkRwC[i].x, fw);
    float m = c.x, my = c.y;
    if (s >= 0.0 && s <= L) {
      // centreline (6.2.3): ${val(R_.clStripe)} m stripes, ${val(R_.clGap)} m gaps, ${val(R_.clW)} m (CAT I), one rhythm from the first end
      if (s > rb.z && s < rb.w) {
        float f = mod(s - rb.z, ${f1(val(R_.clStripe) + val(R_.clGap))});
        float cl = mkBand(f, 0.0, ${f1(val(R_.clStripe))}, fw) * mkBand(min(s - rb.z, rb.w - s), 0.0, 1e5, fw);
        cl = mix(cl, ${f1(val(R_.clStripe) / (val(R_.clStripe) + val(R_.clGap)))}, smoothstep(8.0, 20.0, fw));
        m = max(m, cl * mkBand(abs(t), -1.0, ${f1(val(R_.clW) / 2)}, fw));
      }
      // edge stripes (6.2.7): ${val(R_.edgeW)} m, outer edge on the pavement edge, interrupted at taxiway junctions (mask)
      float cut = texelFetch(uMkEdge, ivec2(clamp(int(s), 0, 4095), 2 * i + (t < 0.0 ? 0 : 1)), 0).r;
      m = max(m, mkBand(abs(t), hw - ${f1(val(R_.edgeW))}, hw, fw) * (1.0 - cut));
    }
    float wear = 0.86 + 0.14 * texture(uNoise, wp.xz * 0.37).g;
    m *= paved * wear; my *= paved * wear;
    // tyre rubber [inf]: streaks along the main-gear tracks over the touchdown zone, on paint and pavement alike
    float xs = x - uMkEnd[4 * k].x;
    float rub = smoothstep(120.0, 380.0, xs) * (1.0 - smoothstep(750.0, 1250.0, xs));
    rub *= smoothstep(13.0, 6.5, abs(y)) * (0.55 + 0.45 * smoothstep(1.0, 4.5, abs(y)));
    rub *= 0.25 + 0.75 * texture(uNoise, vec2(s * 0.004, t * 0.21)).r * texture(uNoise, vec2(s * 0.031, t * 0.45)).g;
    rub = clamp(rub * 0.85, 0.0, 0.7) * paved;
    vec3 C = uMkWhite * m; float A = m;
    C = uMkYellow * my + C * (1.0 - my); A = my + A * (1.0 - my);
    C = uMkRubber * rub + C * (1.0 - rub); A = rub + A * (1.0 - rub);
    rough = mix(rough, 0.62, m);
    return vec4(C / max(A, 1e-4), A);
  }
  return vec4(0.0);
}
`;

// ------------------------------------------------------------------------------------------------ glyph SDF atlas
// exact squared Euclidean distance transform (Felzenszwalb & Huttenlocher), in place
// forked from sfo3d@e3218d6 js/world/textures.js (edt1d / edt2d), unchanged
function edt1d(f, n, off, stride, tmp) {
  const { d, v, z, g } = tmp;
  for (let q = 0; q < n; q++) g[q] = f[off + q * stride];
  let k = 0; v[0] = 0; z[0] = -Infinity; z[1] = Infinity;
  for (let q = 1; q < n; q++) {
    let s = ((g[q] + q * q) - (g[v[k]] + v[k] * v[k])) / (2 * q - 2 * v[k]);
    while (s <= z[k]) { k--; s = ((g[q] + q * q) - (g[v[k]] + v[k] * v[k])) / (2 * q - 2 * v[k]); }
    k++; v[k] = q; z[k] = s; z[k + 1] = Infinity;
  }
  k = 0;
  for (let q = 0; q < n; q++) { while (z[k + 1] < q) k++; const dq = q - v[k]; d[q] = dq * dq + g[v[k]]; }
  for (let q = 0; q < n; q++) f[off + q * stride] = d[q];
}
function edt2d(f, W, H) {
  const n = Math.max(W, H);
  const tmp = { d: new Float64Array(n), v: new Int32Array(n), z: new Float64Array(n + 1), g: new Float64Array(n) };
  for (let x = 0; x < W; x++) edt1d(f, H, x, W, tmp);
  for (let y = 0; y < H; y++) edt1d(f, W, y * W, 1, tmp);
}
/** the CAAC designation glyphs (fig. 6.2.2-2 polygons) as a signed-distance atlas: NG cells of CW x CH px, row 0 = the
 *  bottom of the glyph (y up); value 0.5 at the outline, +-SPREAD m over 0..1 */
export function makeRunwayGlyphAtlas() {
  const SS = 2;   // rasterise at 2x (64 px / m), then measure distances at 1x from the 2x mask (sub-pixel outline)
  const W = CW * NG, H = CH, W4 = W * SS, H4 = H * SS;
  const cv = (typeof OffscreenCanvas !== 'undefined') ? new OffscreenCanvas(W4, H4) : Object.assign(document.createElement('canvas'), { width: W4, height: H4 });
  const cx = cv.getContext('2d', { willReadFrequently: true });
  cx.fillStyle = '#000'; cx.fillRect(0, 0, W4, H4); cx.fillStyle = '#fff';
  CAAC.glyphs.order.forEach((ch, i) => {
    const rings = CAAC.glyphs.rings[ch]; if (!rings) return;
    cx.beginPath();
    for (const r of rings) r.forEach(([x, y], k) => { const px = (i * CW + (x + GX0) * PPM) * SS, py = H4 - (y + GY0) * PPM * SS; k ? cx.lineTo(px, py) : cx.moveTo(px, py); });
    cx.closePath(); cx.fill('evenodd');
  });
  const px = cx.getImageData(0, 0, W4, H4).data;
  const INF = 1e20; const inside = new Float64Array(W4 * H4), outside = new Float64Array(W4 * H4);
  for (let i = 0; i < W4 * H4; i++) { const on = px[i * 4] > 127; inside[i] = on ? INF : 0; outside[i] = on ? 0 : INF; }
  edt2d(inside, W4, H4); edt2d(outside, W4, H4);
  const out = new Uint8Array(W * H);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    // sample the 4x field at the centre of the 1x texel; texture row 0 = bottom (y up), canvas row 0 = top
    const X = x * SS + SS / 2, Y = (H - 1 - y) * SS + SS / 2; const i = Y * W4 + X;
    const d = (Math.sqrt(inside[i]) - Math.sqrt(outside[i])) / (PPM * SS);   // metres, + inside
    out[y * W + x] = Math.max(0, Math.min(255, Math.round((0.5 + d / (2 * SPREAD)) * 255)));
  }
  if (cv.width) { cv.width = cv.height = 1; }
  gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);   // rows of W = 2,210 bytes
  const t = texture(W, H, { data: out, internal: gl.R8, format: gl.RED, mips: true });
  gl.pixelStorei(gl.UNPACK_ALIGNMENT, 4);
  return t;
}

// ------------------------------------------------------------------------------------------------ runway set-up (CPU)
// point-in-polygon (even-odd) over rings
function inRings(rings, x, z) {
  let inside = false;
  for (const r of rings) for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
    const a = r[i], b = r[j]; if ((a[1] > z) !== (b[1] > z) && x < (b[0] - a[0]) * (z - a[1]) / (b[1] - a[1]) + a[0]) inside = !inside;
  }
  return inside;
}
function polyIndex(polys) {
  return polys.map(p => { const rings = [p.ring, ...(p.holes || [])]; let x0 = 1e9, z0 = 1e9, x1 = -1e9, z1 = -1e9; for (const q of p.ring) { x0 = Math.min(x0, q[0]); x1 = Math.max(x1, q[0]); z0 = Math.min(z0, q[1]); z1 = Math.max(z1, q[1]); } return { rings, x0, z0, x1, z1 }; });
}
const inAny = (idx, x, z) => idx.some(P => x >= P.x0 && x <= P.x1 && z >= P.z0 && z <= P.z1 && inRings(P.rings, x, z));

/** the runway marking plan from the data + the CAAC table (also used by the report / QA: window.SHA.markings) */
export function runwayPlan(airport, geo) {
  const plan = [];
  geo.RUNWAYS.forEach((R, i) => {
    const W = R.width || 45; const sl = stripeLayout(W); const ends = [];
    R.ends.forEach((id, j) => {
      const E = geo.RUNWAY_ENDS[id]; const other = geo.RUNWAY_ENDS[R.ends[1 - j]];
      const disp = E.dthrM || 0, pad = (R.blastPad || [0, 0])[j] || 0;
      const lda = (E.declared && E.declared.LDA) || (R.len - disp);
      const between = R.len - disp - ((other && other.dthrM) || 0);   // distance between the two thresholds (6.2.6-2)
      const rec = (airport.runways || []).find(r => r.id === R.id) || {};
      const fe = ((rec.aip_facts || {}).ends || {})[id] || {};
      const papi = fe.papi && fe.papi.inward_of_dthr_m != null ? fe.papi.inward_of_dthr_m : null;   // AIP (mirror) AD 2.14
      const aim = papi != null && val(R_.aimAtPapi) ? papi : aimStartNoPapi(lda);
      const tdz = tdzPositions(between, aim); let mask = 0; tdz.forEach((t, k) => { if (t.keep) mask |= 1 << k; });
      const m = /^(\d{2})([LRC]?)$/.exec(id) || [id, id.slice(0, 2), ''];
      const d1 = m[1][0], d2 = m[1][1], letter = m[2] || '';
      const lx0 = sl.start + sl.len + val(R_.desigGapAfterStripes);
      const nx0 = letter ? lx0 + val(R_.desigH) + val(R_.desigLetterNumberGap) : lx0;
      const cStart = nx0 + val(R_.desigH) + val(R_.desigGapToCL);
      const h = arrowH(W); let arrows = 0;
      if (disp > 0) for (let n = 0; n < 50; n++) { const tail = val(R_.arrowFirstTipBeforeThr) + n * (val(R_.arrowLen) + val(R_.arrowGap)) + val(R_.arrowLen); if (tail <= disp - val(R_.arrowEndMargin)) arrows = n + 1; else break; }
      ends.push({ id, disp, pad, aim, aimSrc: papi != null ? 'PAPI origin (AIP (mirror) PAPI distance; 6.2.5-2)' : 'table 6.2.5', lda, between,
        tdzPairs: tdzPairCount(between), tdz: tdz.map(t => ({ at: t.x0, painted: t.keep })), mask, letter, d1, d2,
        g: [gIndex(letter), gIndex(d1), gIndex(d2)], w1: glyphWidth(d1), w2: glyphWidth(d2), lx0, nx0, cStart, arrows, arrowH: h,
        chevrons: pad >= val(R_.chevronMinLen) - 0.5, stripes: sl });
    });
    plan.push({ id: R.id, a: R.a, dir: R.dir, L: R.len, W, gHalf: val(R_.aimGap)[W] != null ? val(R_.aimGap)[W] / 2 : 9, ends, R });
  });
  return plan;
}
/** edge-stripe interruption mask: 4096 x (2 x runways) R8, 1 m / px along s; 255 where a taxiway meets the edge */
function edgeMask(plan, airport) {
  const twy = polyIndex(((airport.surfaces || {}).taxiway) || []);
  const H = Math.max(2, plan.length * 2), W = 4096; const data = new Uint8Array(W * H); const stats = [];
  plan.forEach((P, i) => {
    const hw = P.W / 2; let cuts = 0;
    for (const [row, sg] of [[2 * i, -1], [2 * i + 1, 1]]) {
      const raw = new Uint8Array(W);
      for (let s = 0; s < Math.min(W, Math.ceil(P.L)); s++) {
        let hit = false;
        for (const off of [2.5, 5.0]) { const t = sg * (hw + off); const x = P.a[0] + P.dir[0] * (s + 0.5) - P.dir[1] * t, z = P.a[1] + P.dir[1] * (s + 0.5) + P.dir[0] * t; if (inAny(twy, x, z)) { hit = true; break; } }
        raw[s] = hit ? 1 : 0;
      }
      for (let s = 0; s < W; s++) { let v = 0; for (let d = -2; d <= 2; d++) if (raw[Math.max(0, Math.min(W - 1, s + d))]) v = 1; data[row * W + s] = v ? 255 : 0; if (v && !raw[Math.max(0, s - 1)] && raw[s]) cuts++; }
    }
    stats.push({ id: P.id, junctions: cuts });
  });
  return { tex: texture(W, H, { data, internal: gl.R8, format: gl.RED, nearest: true }), stats };
}
function runwayUniforms(plan, glyphTex, edgeTex) {
  const A = new Float32Array(MAX_RW * 4), B = new Float32Array(MAX_RW * 4), C = new Float32Array(MAX_RW * 4), E = new Float32Array(MAX_RW * 8 * 4);
  plan.slice(0, MAX_RW).forEach((P, i) => {
    A.set([P.a[0], P.a[1], P.dir[0], P.dir[1]], i * 4);
    B.set([P.L, P.W, P.ends[0].disp + P.ends[0].cStart, P.L - P.ends[1].disp - P.ends[1].cStart], i * 4);   // CL from / to s (pavement-end metres)
    C.set([P.gHalf, 0, 0, 0], i * 4);
    P.ends.forEach((e, j) => {
      const k = 2 * i + j, o = k * 16;
      E.set([e.disp, e.pad, e.aim, e.mask, e.g[0], e.g[1], e.g[2], e.disp ? e.lx0 : e.lx0, e.w1, e.w2, e.nx0, 0, e.stripes.per, e.stripes.gap, e.arrows, e.arrowH], o);
    });
  });
  const al = CAAC.albedo;
  return { uMkRwA: A, uMkRwB: B, uMkRwC: C, uMkEnd: E, uMkNRw: Math.min(plan.length, MAX_RW), uMkOn: 1, uMkGlyphs: glyphTex, uMkEdge: edgeTex,
    uMkWhite: val(al.white), uMkYellow: val(al.yellow), uMkRubber: val(al.rubber) };
}

// ------------------------------------------------------------------------------------------------ extension
let state = { plan: null, edgeStats: null, decals: null, signs: null, holds: null };
registerExtension({
  name: 'markings', order: 20,
  shaderChunks: { sha_ground_paint: GLSL },
  groundUniforms(ctx) {
    const t0 = performance.now();
    state.plan = runwayPlan(ctx.airport, ctx.geo);
    const glyphs = makeRunwayGlyphAtlas(); const t1 = performance.now();
    const em = edgeMask(state.plan, ctx.airport); state.edgeStats = em.stats;
    ctx.log('markings: runway paint set-up ' + Math.round(performance.now() - t0) + ' ms (glyph atlas ' + Math.round(t1 - t0) + ' ms, edge mask ' + Math.round(performance.now() - t1) + ' ms)');
    return runwayUniforms(state.plan, glyphs, em.tex);
  },
  async buildWorld(ctx) {
    const t0 = performance.now(); const items = [];
    const D = buildDecals(ctx, state.plan); items.push(...D.items); state.decals = D.info;
    state.apron = (D.info.stands && D.info.stands.apron) || null;
    state.holds = D.holds.map(h => ({ id: h.id, p: h.p, u: h.u, kind: h.kind, exitOnly: h.exitOnly, rwy: h.R.id, ref: h.twyRef, text: h.mandText || null, src: h.src, eL: h.eL, eR: h.eR }));
    const t1 = performance.now();
    const S = buildSigns(ctx, D.holds, D.junctions); items.push(...S.items); state.signs = S.info;
    state.signList = (S.assemblies || []).map(a => ({ c: a.c, f: a.f, text: a.faces.map(f => f.text).join(' | '), kinds: a.faces.map(f => f.kind), why: a.why }));
    const info = { runways: state.plan.map(P => ({ id: P.id, W: P.W, ends: P.ends.map(e => ({ id: e.id, disp: e.disp, pad: e.pad, aim: e.aim, tdz: e.tdz.filter(t => t.painted).map(t => t.at), stripes: e.stripes.n, gap: +e.stripes.gap.toFixed(3), arrows: e.arrows, chevrons: e.chevrons, cStart: e.cStart })) })),
      edge: state.edgeStats, decals: D.info, signs: S.info, ms: { decals: Math.round(t1 - t0), signs: Math.round(performance.now() - t1) } };
    return { items, info };
  },
  start(app) {
    app.markings = { plan: () => state.plan, holds: () => state.holds || [], signs: () => state.signList || [], apron: () => state.apron, info: () => ({ edge: state.edgeStats, decals: state.decals, signs: state.signs }), params: paramList, CAAC,
      setRunwayPaint: (on) => { app.world.groundU.uMkOn = on ? 1 : 0; } };
  },
});
