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
// Also (fix round 2) the apron light map for the night flood (apronLightMap / applyMastPools below: lit area incl. the
// airside fill + spill, mast pools; ground uniforms uApLight / uApLightRect / uApLightOn read by shaApronFlood).
// No FAA constant is used (sfo3d's FAA runway marks, js/live/markings.js and js/live/signs.js are not forked; only the
// ribbon / sign mesh helpers are, with their headers).
import { registerExtension } from './ext.js';
import { gl, texture } from '../gl.js';
import { CAAC, val, src, stripeLayout, tdzPositions, tdzPairCount, arrowH, glyphWidth, aimStartNoPapi, paramList } from './caac_markings.js';
import { buildDecals } from './caac_decals.js';
import { APRON_FLOOD } from '../shaders/ground.js';
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
// Anti-aliasing (fix round 1, review H1) [inf: rendering choice, not a marking dimension]: every edge is smoothed over FWK x
// the pixel footprint measured ALONG THE EDGE NORMAL - along-track edges (stripe ends, CL dash ends, bars, TDZ / aiming-point
// ends) with the along-track footprint, lateral edges (stripe sides, CL / edge-stripe width, arrow shafts) with the
// across-track footprint, chevron legs across the 45 deg leg, glyph outlines along the signed-distance gradient. One
// isotropic footprint (the Phase 2 code) is ~5 x the across-track one at a threshold view and blurred the 1.45-1.575 m
// stripe gaps and the numerals away.
const FWK = 0.6;
// a repeating lateral pattern fades to its mean density as the across-track footprint nears its period (threshold stripes:
// 3.25 / 3.375 m, Nyquist at a 1.6 m footprint = 0.97 in FWK units): fade between these FWK-scaled footprints [inf]
const STRIPE_FADE = [0.45, 1.1];
const CL_P = val(R_.clStripe) + val(R_.clGap), ARROW_P = val(R_.arrowLen) + val(R_.arrowGap), CHEV_P = val(R_.chevronPitch);
const GLSL = `
// sha3d runway paint: CAAC MH 5001-2021 (js/live/caac_markings.js). Per runway i: uMkRwA = (ax, az, dx, dz) pavement end of
// the first end + unit direction; uMkRwB = (L, W, CL start s, CL end s); uMkRwC = (aim / TDZ inner half gap, ...).
// Per end k = 2 i + j (j = 0 at ax, 1 at the far end), 4 vec4: e0 (disp, chevron length, aim, tdzMask), e1 (letter, d1, d2,
// letterX0), e2 (w1, w2, numberX0, -), e3 (stripes per side, stripe gap, arrows, arrow h). x = metres from the pavement end
// inwards, y = metres to the right of a pilot landing on that end. jx / jy = d(x, y) per screen pixel (screen x / y); the
// end frame is +-(s, t), so only absolute values of their projections are used.
uniform vec4 uMkRwA[${MAX_RW}]; uniform vec4 uMkRwB[${MAX_RW}]; uniform vec4 uMkRwC[${MAX_RW}]; uniform vec4 uMkEnd[${MAX_RW * 8}];
uniform int uMkNRw; uniform float uMkOn; uniform sampler2D uMkGlyphs; uniform sampler2D uMkEdge;
uniform vec3 uMkWhite; uniform vec3 uMkYellow; uniform vec3 uMkRubber;
float mkBand(float x, float a, float b, float fw){ return clamp(smoothstep(a - fw, a + fw, x) - smoothstep(b - fw, b + fw, x), 0.0, 1.0); }
// smoothing width (m) for an edge whose normal is the unit vector u of the end frame
float mkFw(vec2 u, vec2 jx, vec2 jy){ return ${f1(FWK)} * (abs(dot(jx, u)) + abs(dot(jy, u))) + 0.001; }
float mkGlyphD(float code, vec2 q, float lod){ return (textureLod(uMkGlyphs, vec2((code + q.x) / ${NG}.0, q.y), lod).r - 0.5) * ${f1(2 * SPREAD)}; }   // metres, + inside
// glyph coverage: p = glyph metres (x across, y along the runway), gjx / gjy = dp per screen pixel
float mkGlyph(float code, vec2 p, vec2 gjx, vec2 gjy){
  if (code < -0.5) return 0.0;
  vec2 q = (p + vec2(${f1(GX0)}, ${f1(GY0)})) / vec2(${f1(GW)}, ${f1(GH)});
  if (q.x < 0.0 || q.x > 1.0 || q.y < 0.0 || q.y > 1.0) return 0.0;
  // the minor axis of the pixel footprint picks the distance-field level (explicit LOD: no implicit derivatives in this
  // branch); the coverage is filtered analytically along the field gradient (finite difference over one footprint)
  float a = dot(gjx, gjx) + dot(gjy, gjy), det = abs(gjx.x * gjy.y - gjx.y * gjy.x);
  float sMax = sqrt(0.5 * (a + sqrt(max(a * a - 4.0 * det * det, 0.0)))), sMin = det / max(sMax, 1e-6);
  float lod = log2(max(sMin * ${f1(PPM)}, 1.0)), e = max(sMin, ${f1(1 / PPM)});
  float d = mkGlyphD(code, q, lod);
  vec2 g = vec2(mkGlyphD(code, q + vec2(e / ${f1(GW)}, 0.0), lod) - d, mkGlyphD(code, q + vec2(0.0, e / ${f1(GH)}), lod) - d);
  float gl = length(g); vec2 u = gl > 1e-5 ? g / gl : vec2(0.0, 1.0);
  float fw = mkFw(u, gjx, gjy);
  // beyond the stored spread (+-${SPREAD} m) the field is clamped: no coverage there (no grey box at large footprints)
  return smoothstep(-fw, fw, d) * smoothstep(${f1(-SPREAD)}, ${f1(-SPREAD + 0.15)}, d);
}
float mkSeg(vec2 p, vec2 a, vec2 b){ vec2 pa = p - a, ba = b - a; float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0); return length(pa - ba * h); }
// white (x) and yellow (y) coverage of one runway end; twyPave = taxiway / apron pavement here (0..1)
vec2 mkEnd(int k, float x, float y, float W, float gHalf, vec2 jx, vec2 jy, float twyPave){
  vec4 e0 = uMkEnd[4 * k], e1 = uMkEnd[4 * k + 1], e2 = uMkEnd[4 * k + 2], e3 = uMkEnd[4 * k + 3];
  float disp = e0.x, pad = e0.y, ay = abs(y), hw = W * 0.5, sy = y < 0.0 ? -1.0 : 1.0; float m = 0.0, my = 0.0;
  float fwS = mkFw(vec2(1.0, 0.0), jx, jy), fwT = mkFw(vec2(0.0, 1.0), jx, jy);   // along-track / across-track
  if (x < 0.0) {
    // pre-threshold ">" chevrons (6.2.25, fig. 6.2.25) over the full length of the pre-threshold pavement: yellow,
    // ${val(R_.chevronW)} m, 45 deg, apexes ${CHEV_P} m apart, X = W; the nearest chevron's apex lies X/4 inside the runway, so its legs
    // (X/4 long) end at the pavement end, as drawn in the figure
    if (pad >= ${f1(val(R_.chevronMinLen))} - 0.5 && x > -pad - 1.0 && ay < hw + 1.0) {
      float u = x + ay, a0 = W * ${f1(val(R_.chevronLastLegFromThr))};
      float kk = max(0.0, floor((a0 - u) / ${f1(CHEV_P)} + 0.5)); float d = abs(u - (a0 - kk * ${f1(CHEV_P)})) * 0.70711;
      float fwC = mkFw(vec2(0.70711, 0.70711 * sy), jx, jy);   // across the leg
      float c = 1.0 - smoothstep(${f1(val(R_.chevronW) / 2)} - fwC, ${f1(val(R_.chevronW) / 2)} + fwC, d);
      c = mix(c, ${f1(val(R_.chevronW) / (CHEV_P / Math.SQRT2))}, smoothstep(4.0, 14.0, fwC));   // far: mean density
      // not where taxiway pavement crosses the pad: that pavement is in use, 6.2.25 marks pavement unfit for aircraft [inf]
      my = max(my, c * mkBand(x, -pad, 0.0, fwS) * mkBand(ay, -1.0, hw, fwT) * (1.0 - twyPave));
    }
    return vec2(m, my);
  }
  float xs = x - disp;
  if (disp > 0.5 && xs < 0.0) {
    // permanently displaced threshold (6.2.4-5, fig. 6.2.4 (b)): centreline arrows; first tip ${val(R_.arrowFirstTipBeforeThr)} m before the
    // threshold, ${val(R_.arrowLen)} m long, ${val(R_.arrowGap)} m apart; head h (table 6.2.4-2), legs >= h/12
    float r = -xs - ${f1(val(R_.arrowFirstTipBeforeThr))};
    if (r > -1.0) {
      float n = floor(max(r, 0.0) / ${f1(ARROW_P)}); float xl = r - n * ${f1(ARROW_P)};
      if (n < e3.z - 0.5) {
        float h = e3.w; float b = h * ${f1(val(R_.arrowHeadHalfBase))}; float lw = h * ${f1(val(R_.arrowLegW))};
        float dl = mkSeg(vec2(xl, ay), vec2(0.0), vec2(h, b));
        float fwL = mkFw(normalize(vec2(b, h * sy)), jx, jy);   // across the leg ((xl, ay) = (-x, |y|) + const)
        m = max(m, (1.0 - smoothstep(lw * 0.5 - fwL, lw * 0.5 + fwL, dl)) * step(-0.5, xl));
        m = max(m, mkBand(xl, 2.0, ${f1(val(R_.arrowLen))}, fwS) * mkBand(ay, -1.0, ${f1(val(R_.clW) / 2)}, fwT));
      }
    }
  }
  // transverse bar at a displaced threshold (6.2.4-4), between the edge stripes
  if (disp > 0.5) m = max(m, mkBand(xs, 0.0, ${f1(val(R_.dthrBarW))}, fwS) * mkBand(ay, -1.0, hw - ${f1(val(R_.edgeW))}, fwT));
  if (xs < 0.0) return vec2(m, my);
  // threshold stripes (6.2.4): ${sl.len} m from ${sl.start} m, ${sl.w} m wide, fitted gaps, double centre gap; ff = metres from the
  // nearest stripe's axis (symmetric edge ramps)
  if (xs > ${f1(sl.start - 2)} && xs < ${f1(sl.start + sl.len + 2)}) {
    float per = e3.x, g = e3.y, P = ${f1(sl.w)} + g; float f = ay - g - ${f1(sl.w / 2)}; float kk = floor(f / P + 0.5); float ff = f - kk * P;
    float c = (kk >= 0.0 && kk < per) ? mkBand(ff, ${f1(-sl.w / 2)}, ${f1(sl.w / 2)}, fwT) : 0.0;
    c = mix(c, ${f1(sl.w)} / P * mkBand(ay, g, g + (per - 1.0) * P + ${f1(sl.w)}, fwT), smoothstep(${f1(STRIPE_FADE[0])}, ${f1(STRIPE_FADE[1])}, fwT));
    m = max(m, c * mkBand(xs, ${f1(sl.start)}, ${f1(sl.start + sl.len)}, fwS));
  }
  // designation (6.2.2, fig. 6.2.2-1 (b)): letter, then the number; CAAC numerals 9 m (fig. 6.2.2-2); glyph x = y, glyph y = x
  vec2 gjx = vec2(jx.y, jx.x), gjy = vec2(jy.y, jy.x);
  float lx0 = e1.w, nx0 = e2.z;
  if (xs > lx0 - 1.0 && xs < lx0 + 10.0) m = max(m, mkGlyph(e1.x, vec2(y + 1.5, xs - lx0), gjx, gjy));
  if (xs > nx0 - 1.0 && xs < nx0 + 10.5) {
    float T = e2.x + ${f1(val(R_.digitClearGap))} + e2.y;
    m = max(m, mkGlyph(e1.y, vec2(y + T * 0.5, xs - nx0), gjx, gjy));
    m = max(m, mkGlyph(e1.z, vec2(y + T * 0.5 - e2.x - ${f1(val(R_.digitClearGap))}, xs - nx0), gjx, gjy));
  }
  // aiming point (6.2.5): at the visual approach slope origin (the PAPI position, AIP (mirror)); ${val(R_.aimLen)} x ${val(R_.aimW)} m
  float aim = e0.z;
  m = max(m, mkBand(xs, aim, aim + ${f1(val(R_.aimLen))}, fwS) * mkBand(ay, gHalf, gHalf + ${f1(val(R_.aimW))}, fwT));
  // touchdown zone pairs (6.2.6, pattern A ${val(R_.tdzLen)} x ${val(R_.tdzW)} m), every ${val(R_.tdzPitch)} m from ${val(R_.tdzPitch)} m; omitted pairs masked out
  int mask = int(e0.w + 0.5);
  float kt = floor(xs / ${f1(val(R_.tdzPitch))});
  if (kt >= 1.0 && kt <= 6.0 && ((mask >> (int(kt) - 1)) & 1) == 1) {
    float x0 = kt * ${f1(val(R_.tdzPitch))};
    m = max(m, mkBand(xs, x0, x0 + ${f1(val(R_.tdzLen))}, fwS) * mkBand(ay, gHalf, gHalf + ${f1(val(R_.tdzW))}, fwT));
  }
  return vec2(m, my);
}
// dxy = (dFdx(wp.xz), dFdy(wp.xz)), taken by the caller in uniform control flow (js/shaders/ground.js)
vec4 shaGroundPaint(vec3 wp, float fw, vec4 dxy, vec4 apt, float paved, inout float rough){
  if (uMkOn < 0.5 || paved < 0.01) return vec4(0.0);
  float twyPave = smoothstep(0.35, 0.65, apt.g);   // airfield map G: taxiway / apron concrete (runway pads have G = 0)
  for (int i = 0; i < ${MAX_RW}; i++) {
    if (i >= uMkNRw) break;
    vec4 ra = uMkRwA[i], rb = uMkRwB[i]; vec2 nr = vec2(-ra.w, ra.z);
    vec2 p = wp.xz - ra.xy; float s = dot(p, ra.zw), t = dot(p, nr);
    float L = rb.x, W = rb.y, hw = W * 0.5;
    if (abs(t) > hw + 1.0 || s < -200.0 || s > L + 200.0) continue;
    int j = s < L * 0.5 ? 0 : 1; int k = 2 * i + j;
    float x = j == 0 ? s : L - s, y = j == 0 ? t : -t;
    vec2 jx = vec2(dot(dxy.xy, ra.zw), dot(dxy.xy, nr)), jy = vec2(dot(dxy.zw, ra.zw), dot(dxy.zw, nr));   // d(s, t) per pixel
    float fwS = mkFw(vec2(1.0, 0.0), jx, jy), fwT = mkFw(vec2(0.0, 1.0), jx, jy);
    vec2 c = mkEnd(k, x, y, W, uMkRwC[i].x, jx, jy, twyPave);
    float m = c.x, my = c.y;
    if (s >= 0.0 && s <= L) {
      // centreline (6.2.3): ${val(R_.clStripe)} m stripes, ${val(R_.clGap)} m gaps, ${val(R_.clW)} m (CAT I), one rhythm from the first end; f = metres
      // from the nearest stripe's middle
      if (s > rb.z && s < rb.w) {
        float f = mod(s - rb.z + ${f1(CL_P / 2 - val(R_.clStripe) / 2)}, ${f1(CL_P)}) - ${f1(CL_P / 2)};
        float cl = mkBand(f, ${f1(-val(R_.clStripe) / 2)}, ${f1(val(R_.clStripe) / 2)}, fwS) * mkBand(min(s - rb.z, rb.w - s), 0.0, 1e5, fwS);
        cl = mix(cl, ${f1(val(R_.clStripe) / CL_P)}, smoothstep(8.0, 20.0, fwS));
        m = max(m, cl * mkBand(abs(t), -1.0, ${f1(val(R_.clW) / 2)}, fwT));
      }
      // edge stripes (6.2.7): ${val(R_.edgeW)} m, outer edge on the pavement edge, interrupted at taxiway junctions (mask)
      float cut = texelFetch(uMkEdge, ivec2(clamp(int(s), 0, 4095), 2 * i + (t < 0.0 ? 0 : 1)), 0).r;
      m = max(m, mkBand(abs(t), hw - ${f1(val(R_.edgeW))}, hw, fwT) * (1.0 - cut));
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
      const disp = E.dthrM || 0;
      // pre-threshold pavement (fix round 1, review L1): 6.2.25 marks the FULL length of pre-threshold pavement unfit for
      // aircraft, so the chevrons follow the paved pad surface drawn by the ground (data runways[].blast_pads ring: the
      // S2 / Umbra measurement where one exists) and fall back to aip_facts.blast_pad_m only when there is no ring
      // aip_facts.blast_pad_m is [length, width] of the pad at BOTH ends (AD 2.12 "60×60m" / "120×75m on the both ends"),
      // not one length per end (integration fix round 1: [1] was read as the 36L length, a false 75 m conflict)
      const padAip = (R.blastPad || [0, 0])[0] || 0;
      const ring = ((R.blastPads || []).find(b => b.end === id) || {}).ring;   // js/geo.js: data runways[].blast_pads
      let padSurf = null;
      if (ring && ring.length >= 3) { padSurf = 0; for (const q of ring) { const sq = (q[0] - R.a[0]) * R.dir[0] + (q[1] - R.a[1]) * R.dir[1]; padSurf = Math.max(padSurf, j === 0 ? -sq : sq - R.len); } padSurf = Math.round(padSurf * 10) / 10; }
      const pad = padSurf != null ? padSurf : padAip;
      const padSrc = padSurf != null ? (Math.abs(padSurf - padAip) > 2 ? `paved pad surface ${padSurf} m (data blast_pads ring, measured) - conflicts with AIP (mirror) blast_pad_m ${padAip} m; 6.2.25 full length` : `paved pad surface ${padSurf} m = AIP (mirror) ${padAip} m`) : `AIP (mirror) blast_pad_m ${padAip} m (no surface ring)`;
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
      ends.push({ id, disp, pad, padAip, padSurf, padSrc, aim, aimSrc: papi != null ? 'PAPI origin (AIP (mirror) PAPI distance; 6.2.5-2)' : 'table 6.2.5', lda, between,
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

// ------------------------------------------------------------------------------------------------ apron light map
// Fix round 2 (review N2 / M1 / N4) [inf]: the night flood of js/shaders/ground.js shaApronFlood lit only apron class (G 255),
// so the T1 / T2 airside fill (asphalt, airfield map R only) was a black moat next to the lit apron, and the flood was one
// even sheet with a hard polygon edge. The light map (RG8, CAAC.apronFlood.res m / texel over the airfield-map rect):
//   R = lit area: aprons + airside pavement added by packages through the pavement() hook (pavedAt >= 0.5 where no core
//       surface - runway, shoulder, blast pad, taxiway, helipad, apron - lies within one texel: the airside fill, also any
//       fill ring a package adds later), with a Gaussian spill past its edge (CAAC.apronFlood.spill);
//   G = pool factor / APRON_FLOOD.gScale: sum over the gates package's masts (SHA.qa.masts(), position + facing) of 1 / (1 + (d / poolR)^2)
//       around a point poolAhead m ahead of the mast, normalised to the mean over the painted stand envelopes (9.2.6: the
//       stand average is the reference), clamped to [floor, cap], times one gain that keeps the mean over the lit area at the
//       fix round 1 level (so stands sit at ~1.3 x, lanes far from masts at 0.5 x the stand mean); x 1 until the masts exist.
const AF = CAAC.apronFlood;
function apronLightMap(ctx) {
  const M = ctx.ground && ctx.ground.maps && ctx.ground.maps.apt, pavedAt = ctx.ground && ctx.ground.pavedAt; if (!M || !pavedAt) return null;
  const t0 = performance.now(); const A = ctx.airport, S = A.surfaces || {};
  const res = val(AF.res), W = Math.ceil(M.rect[2] / res), H = Math.ceil(M.rect[3] / res), rect = [M.rect[0], M.rect[1], W * res, H * res];
  const cv = (typeof OffscreenCanvas !== 'undefined') ? new OffscreenCanvas(W, H) : Object.assign(document.createElement('canvas'), { width: W, height: H });
  const cx = cv.getContext('2d', { willReadFrequently: true });
  cx.fillStyle = '#000'; cx.fillRect(0, 0, W, H); cx.globalCompositeOperation = 'lighter';
  const fill = (rings, style) => { cx.fillStyle = style; cx.beginPath(); for (const r of rings) { if (!r || r.length < 3) continue; r.forEach((p, i) => { const x = (p[0] - rect[0]) / res, y = (p[1] - rect[1]) / res; i ? cx.lineTo(x, y) : cx.moveTo(x, y); }); cx.closePath(); } cx.fill('evenodd'); };
  for (const a of A.aprons || []) fill([a.ring, ...(a.holes || [])], '#f00');   // red: apron
  for (const p of [...(S.runway || []), ...(S.runway_shoulders_blast_pads || []), ...(S.taxiway || []), ...(S.taxiway_shoulders || []), ...(A.helipads || [])]) fill([p.ring, ...(p.holes || [])], '#0f0');   // green: other core surfaces
  const px = cx.getImageData(0, 0, W, H).data; if (cv.width) { cv.width = cv.height = 1; }
  const n = W * H; const core = new Uint8Array(n), area = new Uint8Array(n); let nApron = 0, nFill = 0;
  for (let k = 0; k < n; k++) core[k] = px[k * 4] > 0 || px[k * 4 + 1] > 0 ? 1 : 0;
  for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
    const k = j * W + i;
    if (px[k * 4] > 127) { area[k] = 1; nApron++; continue; }
    let nearCore = false; for (let dj = -1; dj <= 1 && !nearCore; dj++) for (let di = -1; di <= 1; di++) { const ii = i + di, jj = j + dj; if (ii >= 0 && jj >= 0 && ii < W && jj < H && core[jj * W + ii]) { nearCore = true; break; } }
    if (!nearCore && pavedAt(rect[0] + (i + 0.5) * res, rect[1] + (j + 0.5) * res) >= 0.5) { area[k] = 1; nFill++; }
  }
  // spill: squared distance (texels) to the lit area, exact EDT (edt2d above)
  const d2 = new Float64Array(n); for (let k = 0; k < n; k++) d2[k] = area[k] ? 0 : 1e20;
  edt2d(d2, W, H);
  const sp = val(AF.spill), data = new Uint8Array(n * 2);
  for (let k = 0; k < n; k++) { const d = Math.sqrt(d2[k]) * res; data[k * 2] = area[k] ? 255 : Math.round(255 * Math.exp(-(d / sp) * (d / sp))); data[k * 2 + 1] = Math.round(255 / APRON_FLOOD.gScale); }
  gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
  const tex = texture(W, H, { data, internal: gl.RG8, format: gl.RG, mips: true });
  gl.pixelStorei(gl.UNPACK_ALIGNMENT, 4);
  return { tex, W, H, res, rect, data, area, stats: { texels: [W, H], res_m: res, apronTexels: nApron, fillTexels: nFill, fillKm2: +(nFill * res * res / 1e6).toFixed(3), spill_m: sp, masts: null, ms: Math.round(performance.now() - t0), src: src(AF.res) } };
}
/** mast pools into G (once the gates package has placed its masts); the texture is updated in place */
function applyMastPools(L, masts, envelopes) {
  const t0 = performance.now(); const { W, H, res, rect, data } = L; const n = W * H;
  const R = val(AF.poolR), reach = val(AF.poolReach), ahead = val(AF.poolAhead), w0 = 1 / (1 + (reach / R) * (reach / R));
  const sum = new Float32Array(n); const rT = Math.ceil(reach / res);
  for (const m of masts) {
    const f = m.face || [0, 0]; const cxm = m.p[0] + f[0] * ahead, czm = m.p[1] + f[1] * ahead;
    const ci = (cxm - rect[0]) / res - 0.5, cj = (czm - rect[1]) / res - 0.5;
    for (let j = Math.max(0, Math.floor(cj - rT)); j <= Math.min(H - 1, Math.ceil(cj + rT)); j++) for (let i = Math.max(0, Math.floor(ci - rT)); i <= Math.min(W - 1, Math.ceil(ci + rT)); i++) {
      const d = Math.hypot(i - ci, j - cj) * res; if (d >= reach) continue;
      sum[j * W + i] += (1 / (1 + (d / R) * (d / R)) - w0) / (1 - w0);
    }
  }
  // reference: the mean over the painted stand envelopes (rasterised at the map resolution); else over the apron texels
  let s = 0, c = 0; const env = new Uint8Array(n);
  if (envelopes && envelopes.length) {
    const cv = (typeof OffscreenCanvas !== 'undefined') ? new OffscreenCanvas(W, H) : Object.assign(document.createElement('canvas'), { width: W, height: H });
    const cx = cv.getContext('2d', { willReadFrequently: true }); cx.fillStyle = '#000'; cx.fillRect(0, 0, W, H); cx.fillStyle = '#fff';
    for (const e of envelopes) { const r = e.ring || []; if (r.length < 3) continue; cx.beginPath(); r.forEach((p, i) => { const x = (p[0] - rect[0]) / res, y = (p[1] - rect[1]) / res; i ? cx.lineTo(x, y) : cx.moveTo(x, y); }); cx.closePath(); cx.fill(); }
    const px = cx.getImageData(0, 0, W, H).data; for (let k = 0; k < n; k++) if (px[k * 4] > 127) { env[k] = 1; s += sum[k]; c++; }
    if (cv.width) { cv.width = cv.height = 1; }
  }
  if (!c) for (let k = 0; k < n; k++) if (L.area[k]) { s += sum[k]; c++; }
  const norm = c && s > 0 ? s / c : 1; const lo = val(AF.floor), hi = val(AF.cap);
  // factor relative to the stand mean, clamped to [floor, cap] (9.2.6-2 floor); then one gain so that the mean over the lit
  // area (apron + fill) stays at the fix round 1 level (the reviewer's measured, accepted mean) [inf]
  const fac = (k) => Math.min(hi, Math.max(lo, sum[k] / norm));
  let litN = 0, litS = 0; for (let k = 0; k < n; k++) if (L.area[k]) { litN++; litS += fac(k); }
  const gain = litN && litS > 0 ? litN / litS : 1; const gs = APRON_FLOOD.gScale; let litMin = 9, standS = 0, standN = 0;
  for (let k = 0; k < n; k++) { const f = fac(k) * gain; data[k * 2 + 1] = Math.round(Math.min(1, f / gs) * 255); if (L.area[k]) litMin = Math.min(litMin, f); if (env[k]) { standS += f; standN++; } }
  gl.activeTexture(gl.TEXTURE15);   // a per-draw unit (gl.js rebinds those with every draw), never a per-frame one
  gl.bindTexture(gl.TEXTURE_2D, L.tex.tex); gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
  gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, W, H, gl.RG, gl.UNSIGNED_BYTE, data);
  gl.pixelStorei(gl.UNPACK_ALIGNMENT, 4); gl.generateMipmap(gl.TEXTURE_2D); gl.bindTexture(gl.TEXTURE_2D, null);
  L.stats.masts = { n: masts.length, standTexels: c, norm: +norm.toFixed(3), gain: +gain.toFixed(3), standMeanFactor: +(standN ? standS / standN : gain).toFixed(3), litMeanFactor: 1, litMinFactor: +litMin.toFixed(3),
    litMaxFactor: +(hi * gain).toFixed(3), floor: lo, cap: hi, poolR_m: R, reach_m: reach, ahead_m: ahead, ms: Math.round(performance.now() - t0), src: src(AF.floor) };
}

// ------------------------------------------------------------------------------------------------ extension
let state = { plan: null, edgeStats: null, decals: null, signs: null, holds: null, light: null, lightDone: false };
registerExtension({
  name: 'markings', order: 20,
  shaderChunks: { sha_ground_paint: GLSL },
  groundUniforms(ctx) {
    const t0 = performance.now();
    state.plan = runwayPlan(ctx.airport, ctx.geo);
    const glyphs = makeRunwayGlyphAtlas(); const t1 = performance.now();
    const em = edgeMask(state.plan, ctx.airport); state.edgeStats = em.stats;
    ctx.log('markings: runway paint set-up ' + Math.round(performance.now() - t0) + ' ms (glyph atlas ' + Math.round(t1 - t0) + ' ms, edge mask ' + Math.round(performance.now() - t1) + ' ms)');
    const U = runwayUniforms(state.plan, glyphs, em.tex);
    // apron light map for the night flood (fix round 2, N2 / M1 / N4): shaApronFlood reads it from the ground uniforms
    try {
      state.light = apronLightMap(ctx);
      if (state.light) { Object.assign(U, { uApLight: state.light.tex, uApLightRect: state.light.rect, uApLightOn: 1 }); ctx.log('markings: apron light map ' + JSON.stringify(state.light.stats)); }
    } catch (err) { console.warn('[markings] apron light map', err); state.light = null; }
    return U;
  },
  async buildWorld(ctx) {
    const t0 = performance.now(); const items = [];
    const D = buildDecals(ctx, state.plan); items.push(...D.items); state.decals = D.info;
    state.apron = (D.info.stands && D.info.stands.apron) || null;
    state.holds = D.holds.map(h => ({ id: h.id, p: h.p, u: h.u, kind: h.kind, exitOnly: h.exitOnly, rwy: h.R.id, ref: h.twyRef, text: h.mandText || null, src: h.src, eL: h.eL, eR: h.eR }));
    const t1 = performance.now();
    const S = buildSigns(ctx, D.holds, D.junctions); items.push(...S.items); state.signs = S.info;
    state.signList = (S.assemblies || []).map(a => ({ c: a.c, f: a.f, text: a.faces.map(f => f.text).join(' | '), kinds: a.faces.map(f => f.kind), why: a.why }));
    const info = { runways: state.plan.map(P => ({ id: P.id, W: P.W, ends: P.ends.map(e => ({ id: e.id, disp: e.disp, pad: e.pad, padSrc: e.padSrc, aim: e.aim, tdz: e.tdz.filter(t => t.painted).map(t => t.at), stripes: e.stripes.n, gap: +e.stripes.gap.toFixed(3), arrows: e.arrows, chevrons: e.chevrons, cStart: e.cStart })) })),
      edge: state.edgeStats, decals: D.info, signs: S.info, ms: { decals: Math.round(t1 - t0), signs: Math.round(performance.now() - t1) } };
    return { items, info };
  },
  start(app) {
    app.markings = { plan: () => state.plan, holds: () => state.holds || [], signs: () => state.signList || [], apron: () => state.apron, info: () => ({ edge: state.edgeStats, decals: state.decals, signs: state.signs, apronLight: state.light ? state.light.stats : null }), params: paramList, CAAC,
      apronLight: () => (state.light ? { ...state.light.stats, rect: state.light.rect, at: (x, z) => { const L = state.light; const i = Math.floor((x - L.rect[0]) / L.res), j = Math.floor((z - L.rect[1]) / L.res); if (i < 0 || j < 0 || i >= L.W || j >= L.H) return [0, 0]; const k = j * L.W + i; return [L.data[k * 2] / 255, L.data[k * 2 + 1] / 255 * 2]; } } : null),
      setRunwayPaint: (on) => { app.world.groundU.uMkOn = on ? 1 : 0; } };
  },
  // the masts are placed by the gates package in its start() (after this one): add their pools to the light map on the first
  // frame they exist (fix round 2, N4); without masts (gates off / failed) the flood stays at the fix round 1 level
  frame(t, app) {
    if (state.lightDone || !state.light) return [];
    const M = app.qa && app.qa.masts ? app.qa.masts() : null; if (!M) return [];
    state.lightDone = true;
    try { applyMastPools(state.light, M.masts || [], (state.apron && state.apron.envelopes) || []); console.log('[markings] apron light pools ' + JSON.stringify(state.light.stats.masts)); }
    catch (err) { console.warn('[markings] apron light pools', err); }
    return [];
  },
});
