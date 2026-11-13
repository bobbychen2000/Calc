import { BAY_WATER_KM, AIRPORT_LAND_ST, stToEN, enToST, GROUND_Y } from '../geo.js';
import { fbm, ridged, vnoise, smooth, clamp } from '../math.js';
// Shoreline measured on USDA NAIP 2024 near-infrared (tools/imagery/shore_naip.py, review round 3): decides land vs Bay
// water inside the NAIP coverage around the airport. AIRPORT_LAND_ST (js/geo.js, 16 vertices) stays the airport AREA
// mask of the shaders; as a coastline the old one was off by tens of metres (east edge 44 m out in the Bay at the 28
// ends, the north basin as land), and the regional BAY_WATER_KM polygon is km-scale.
import { SHORE } from '../../data/sfo_shore.js';
// Peninsula reservoirs and the SFPUC watershed (close-out round 3, env-14; engine_closeout.md §2: the San Andreas valley
// west of the airport had no water and city blocks, and the "crystal springs / san andreas valley lakes carve" comment
// below carved nothing). js/env/reservoirs_data.js (tools/env/build_reservoirs.py: OSM ways 33449157 / 815759758 /
// 23782143 and relation 3944756, ODbL; San Andreas Lake level from USGS 3DEP, Crystal Springs from the OSM ele tags):
// the watershed (94 km², SFPUC, undeveloped) is excluded from the urban mask like NATURE_KM, and each lake is carved into
// the procedural terrain: a bed below its level inside the shore line (LAKE_BED_MAX below), and around it the ground raised to at
// least the level + a bank rising LAKE_BANK_SLOPE per metre over LAKE_BANK_M (the procedural valley floor lies 30-50 m
// below the Crystal Springs levels and 0-80 m below San Andreas Lake: a water surface there would float; I). The water
// surfaces themselves are items of their own (js/live/app.js, both renderers).
import { RESERVOIRS } from '../env/reservoirs_data.js';
export const LAKE_DEPTH = 3.0, LAKE_BANK_M = 400, LAKE_BANK_SLOPE = 0.12;   // (LAKE_DEPTH: the round-3 bed depth, unused since round 5)
// The terrain MESH samples height() on its grid (buildMeshes below: 15 m cells to +-4.2 km, then x1.052 per cell - up to
// 550 m long at the lakes, 5-14 km out) and interpolates linearly between the samples, so the drawn shore lies where the
// interpolated ground crosses the water level. With a bed only LAKE_DEPTH below the level inside the shore and the bank
// rising LAKE_BANK_SLOPE per metre outside, that crossing fell up to ~0.9 cell INTO the lake and the land covered 6-31 %
// of each lake (c3 verifier env-14: 69-94 % of the water visible). Close-out round 5: (1) the bed falls with the bank's
// slope mirrored (0.5 m + LAKE_BANK_SLOPE x distance below the level, to LAKE_BED_MAX), so a cell spanning the shore
// interpolates to the level near the shore itself (the depth is not drawn: the water surface hides it, I); (2) buildMeshes
// adds grid lines across the lake boxes (lakeCell 80 m). Built mesh, step 15 / 30: 95.3-98.7 % of each lake visible
// (tools/env/test_c3.mjs, >= 95 %).
export const LAKE_BED_MAX = 60;
// Per lake: the ring's segments, bucketed (uniform LAKE_GRID cells; a segment is listed in every cell within LAKE_DMAX of
// its bounding box) for the distance, and per LAKE_BAND z-band for the even-odd crossing test, so height() near a lake
// costs a few dozen segments instead of the whole 269-510-point ring (the round-5 mesh lines put ~90k grid vertices in
// the lake boxes). Exact for every distance below LAKE_DMAX, which covers both uses: the bed reaches LAKE_BED_MAX at
// (LAKE_BED_MAX - 0.5) / LAKE_BANK_SLOPE = 496 m and the bank ends at LAKE_BANK_M.
const LAKE_DMAX = Math.max(LAKE_BANK_M, (LAKE_BED_MAX - 0.5) / LAKE_BANK_SLOPE) + 1, LAKE_GRID = 250, LAKE_BAND = 50;
const LAKES = (RESERVOIRS.lakes || []).map(L => {
  let x0 = 1e9, z0 = 1e9, x1 = -1e9, z1 = -1e9; for (const [x, z] of L.ring) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); z0 = Math.min(z0, z); z1 = Math.max(z1, z); }
  const box = [x0 - LAKE_BANK_M, z0 - LAKE_BANK_M, x1 + LAKE_BANK_M, z1 + LAKE_BANK_M];
  const R = L.ring, n = R.length, S = new Float64Array(n * 4);
  for (let i = 0, j = n - 1; i < n; j = i++) { S[i * 4] = R[j][0]; S[i * 4 + 1] = R[j][1]; S[i * 4 + 2] = R[i][0]; S[i * 4 + 3] = R[i][1]; }
  const gx0 = box[0] - LAKE_DMAX, gz0 = box[1] - LAKE_DMAX, gw = Math.ceil((box[2] - box[0] + 2 * LAKE_DMAX) / LAKE_GRID) + 1, gh = Math.ceil((box[3] - box[1] + 2 * LAKE_DMAX) / LAKE_GRID) + 1;
  const cells = Array.from({ length: gw * gh }, () => []);
  const bz0 = z0, bands = Array.from({ length: Math.ceil((z1 - z0) / LAKE_BAND) + 1 }, () => []);
  for (let i = 0; i < n; i++) { const xa = S[i * 4], za = S[i * 4 + 1], xb = S[i * 4 + 2], zb = S[i * 4 + 3];
    const ci0 = Math.max(0, Math.floor((Math.min(xa, xb) - LAKE_DMAX - gx0) / LAKE_GRID)), ci1 = Math.min(gw - 1, Math.floor((Math.max(xa, xb) + LAKE_DMAX - gx0) / LAKE_GRID));
    const cj0 = Math.max(0, Math.floor((Math.min(za, zb) - LAKE_DMAX - gz0) / LAKE_GRID)), cj1 = Math.min(gh - 1, Math.floor((Math.max(za, zb) + LAKE_DMAX - gz0) / LAKE_GRID));
    for (let cj = cj0; cj <= cj1; cj++) for (let ci = ci0; ci <= ci1; ci++) cells[cj * gw + ci].push(i);
    const b0 = Math.max(0, Math.floor((Math.min(za, zb) - bz0) / LAKE_BAND)), b1 = Math.min(bands.length - 1, Math.floor((Math.max(za, zb) - bz0) / LAKE_BAND));
    for (let b = b0; b <= b1; b++) bands[b].push(i); }
  return { ...L, box, S, cells, gx0, gz0, gw, gh, bands, bz0, zr: [z0, z1] };
});
function lakeShape(x, z, h) {   // inside a lake: its bed; near one or more: the highest bank requirement (Upper / Lower Crystal Springs adjoin)
  let out = h;
  for (const L of LAKES) {
    const b = L.box; if (x < b[0] || x > b[2] || z < b[1] || z > b[3]) continue;
    const S = L.S; let inside = false, d = 1e9;
    if (z >= L.zr[0] && z <= L.zr[1]) for (const i of L.bands[Math.min(L.bands.length - 1, Math.floor((z - L.bz0) / LAKE_BAND))]) {   // even-odd rule
      const xa = S[i * 4], za = S[i * 4 + 1], xb = S[i * 4 + 2], zb = S[i * 4 + 3];
      if ((za > z) !== (zb > z) && x < (xb - xa) * (z - za) / (zb - za) + xa) inside = !inside; }
    const ci = Math.floor((x - L.gx0) / LAKE_GRID), cj = Math.floor((z - L.gz0) / LAKE_GRID);
    if (ci >= 0 && cj >= 0 && ci < L.gw && cj < L.gh) for (const i of L.cells[cj * L.gw + ci]) {
      const xa = S[i * 4], za = S[i * 4 + 1], dx = S[i * 4 + 2] - xa, dz = S[i * 4 + 3] - za, l2 = dx * dx + dz * dz || 1;
      const t = Math.max(0, Math.min(1, ((x - xa) * dx + (z - za) * dz) / l2)); d = Math.min(d, Math.hypot(x - xa - t * dx, z - za - t * dz)); }
    if (inside) return L.level_y - Math.min(LAKE_BED_MAX, 0.5 + d * LAKE_BANK_SLOPE);   // (the bank's slope mirrored: see LAKE_BED_MAX)
    if (d < LAKE_BANK_M) { const bank = L.level_y + 0.5 + d * LAKE_BANK_SLOPE; const k = smooth(LAKE_BANK_M * 0.5, LAKE_BANK_M, d); out = Math.max(out, Math.max(h, bank) * (1 - k) + h * k); }   // at least the bank near the shore, the terrain beyond
  }
  return out;
}

export const REGION = { x0: -60000, z0: -60000, size: 120000, res: 2048 };

// Pacific coast (km e,n) -> ocean to the west
const PACIFIC_COAST_KM = [[-9.0, 40], [-9.2, 15], [-9.6, 8], [-10.3, 3], [-10.7, -1], [-11.2, -5], [-12.3, -8.7], [-11.2, -13], [-8.5, -17], [-7, -22], [-5.5, -30], [-3, -40], [-3, -70], [-70, -70], [-70, 70], [-9, 70]];

// Nature (non-urban) areas in km (e,n)
const NATURE_KM = [
  // Coast range west of the San Andreas valley, south of San Bruno
  [[-5.6, 3.2], [-4.2, -3.0], [-1.6, -6.6], [1.4, -10.1], [3.4, -12.8], [6.5, -17], [8, -22], [-3, -40], [-12, -12], [-11, -2], [-9.5, 3.5], [-7.5, 4.2]],
  // San Bruno Mountain
  [[-7.6, 8.9], [-5.8, 8.6], [-3.4, 8.0], [-2.3, 7.3], [-2.6, 6.6], [-4.5, 6.6], [-6.5, 7.2], [-7.8, 7.9]],
];
const FREEWAYS_KM = [
  // US-101 west of SFO (approx)
  [[6.0, -8.0], [3.6, -5.2], [1.2, -3.3], [-0.6, -2.3], [-1.6, -1.2], [-2.05, -0.2], [-2.3, 0.8], [-2.0, 2.2], [-1.3, 3.4], [-0.9, 4.8], [-1.1, 6.2], [-1.2, 7.4], [-1.0, 9.2], [-1.6, 11.5], [-2.3, 14.0], [-2.0, 16.5], [-1.6, 18.2]],
  // I-380
  [[-2.1, 1.0], [-3.2, 1.6], [-4.6, 1.9], [-5.8, 1.6]],
  // I-280
  [[-8.6, 9.0], [-7.4, 5.4], [-5.9, 2.0], [-5.0, -0.5], [-4.3, -2.6], [-2.4, -5.3], [0.3, -8.4], [2.4, -10.5], [4.8, -13.5], [7.5, -17.5]],
  // San Mateo Bridge approach (SR-92)
  [[0.5, -9.8], [3.0, -8.4], [5.8, -6.6], [9.5, -4.6]],
  // I-880 east bay
  [[6.0, 20.0], [9.0, 16.0], [12.8, 12.5], [15.5, 9.0], [18.0, 5.5], [20.5, 2.0], [22.0, -2.0], [24.5, -8.0], [27.0, -14.0]],
];

// Ridges: polylines with height profiles [e,n,h] (km, km, m) and half-width (km)
const RIDGES = [
  { pts: [[-7.8, 1.5, 300], [-7.4, -1.0, 390], [-8.4, -4.5, 470], [-9.3, -7.1, 580], [-6.5, -10.5, 430], [-3.0, -14.5, 470], [1.0, -18.5, 560], [4.5, -23, 600]], w: 2.6 },
  { pts: [[-7.3, 8.4, 250], [-5.2, 7.6, 402], [-3.8, 7.3, 330], [-2.5, 7.0, 160]], w: 1.1 },
  { pts: [[-4.4, 4.8, 170], [-3.7, 2.6, 190], [-3.4, 0.2, 170], [-2.3, -3.2, 180], [-0.4, -6.2, 190], [2.2, -9.2, 210], [4.6, -12.2, 220]], w: 1.4 },
  // San Francisco hills
  { pts: [[-7.4, 12.8, 150], [-6.9, 13.8, 280], [-6.4, 15.1, 280], [-6.0, 16.5, 170], [-5.0, 17.5, 90]], w: 1.2 },
  { pts: [[-4.6, 12.6, 120], [-3.4, 13.8, 130], [-2.5, 14.8, 60]], w: 0.8 },
  // East Bay hills
  { pts: [[6.5, 28, 420], [8.6, 23, 470], [11.4, 18.6, 480], [14.4, 13.6, 420], [17.6, 9.2, 330], [20.8, 4.8, 330], [23.6, 0.2, 400], [26.4, -5, 420], [29.6, -10.4, 520], [33.4, -16.6, 760], [36, -22, 700]], w: 3.2 },
  { pts: [[12, 30, 350], [18, 24, 420], [24, 16, 480], [30, 8, 520], [36, 0, 600], [42, -8, 700]], w: 5.0 },
  // Mt Diablo
  { pts: [[39.5, 28.0, 900], [41.2, 29.2, 1173], [43.0, 30.0, 950]], w: 4.5 },
];

function pointInPoly(x, y, poly) {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i], [xj, yj] = poly[j];
    if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) inside = !inside;
  }
  return inside;
}
function segDist(px, py, ax, ay, bx, by) {
  const dx = bx - ax, dy = by - ay; const l2 = dx * dx + dy * dy;
  let t = l2 > 0 ? ((px - ax) * dx + (py - ay) * dy) / l2 : 0; t = clamp(t, 0, 1);
  const cx = ax + dx * t, cy = ay + dy * t; return [Math.hypot(px - cx, py - cy), t];
}
export function polySDF(x, y, poly) { // positive inside
  let d = 1e9;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) d = Math.min(d, segDist(x, y, poly[j][0], poly[j][1], poly[i][0], poly[i][1])[0]);
  return pointInPoly(x, y, poly) ? d : -d;
}

export class Terrain {
  constructor() {
    const R = REGION.res;
    // --- paint regional maps with canvas ---
    const cv = document.createElement('canvas'); cv.width = R; cv.height = R;
    const cx = cv.getContext('2d');
    const toPx = (e, n) => [(e * 1000 - REGION.x0) / REGION.size * R, (-n * 1000 - REGION.z0) / REGION.size * R];
    const poly = (pts, km = true) => { cx.beginPath(); pts.forEach((p, i) => { const q = km ? toPx(p[0], p[1]) : p; if (i) cx.lineTo(q[0], q[1]); else cx.moveTo(q[0], q[1]); }); cx.closePath(); };
    const aptPolyEN = AIRPORT_LAND_ST.map(([s, t]) => { const [e, n] = stToEN(s, t); return [e / 1000, n / 1000]; });
    this.aptPolyEN = aptPolyEN;
    // Water mask
    cx.fillStyle = '#000'; cx.fillRect(0, 0, R, R);
    cx.fillStyle = '#fff'; poly(BAY_WATER_KM); cx.fill(); poly(PACIFIC_COAST_KM); cx.fill();
    cx.fillStyle = '#000'; poly(aptPolyEN); cx.fill();
    const water = cx.getImageData(0, 0, R, R).data;
    // urban-allowed mask
    cx.fillStyle = '#000'; cx.fillRect(0, 0, R, R);
    cx.fillStyle = '#fff'; cx.fillRect(0, 0, R, R);
    cx.fillStyle = '#000'; NATURE_KM.forEach(p => { poly(p); cx.fill(); });
    // the SFPUC Peninsula Watershed: no urban development (env-14; world x, z -> km e, n)
    for (const r of (RESERVOIRS.watershed && RESERVOIRS.watershed.rings) || []) { poly(r.map(([x, z]) => [x / 1000, -z / 1000])); cx.fill(); }
    poly(aptPolyEN); cx.fill();
    // parks (circles)
    const parks = [[-8.2, 16.6, 0.9], [-5.6, 12.4, 0.6], [3.9, -2.9, 0.35], [-0.2, 11.7, 0.3]];
    parks.forEach(([e, n, r]) => { const [x, y] = toPx(e, n); cx.beginPath(); cx.arc(x, y, r * 1000 / REGION.size * R, 0, 7); cx.fill(); });
    const urban = cx.getImageData(0, 0, R, R).data;
    // freeways
    cx.fillStyle = '#000'; cx.fillRect(0, 0, R, R);
    cx.strokeStyle = '#fff'; cx.lineWidth = 45 / REGION.size * R; cx.lineJoin = 'round';
    FREEWAYS_KM.forEach(l => { cx.beginPath(); l.forEach((p, i) => { const q = toPx(p[0], p[1]); i ? cx.lineTo(q[0], q[1]) : cx.moveTo(q[0], q[1]); }); cx.stroke(); });
    const fwy = cx.getImageData(0, 0, R, R).data;
    this.freeways = FREEWAYS_KM;

    // --- signed distance field to shoreline (meters, + on land) ---
    const N = R; const INF = 1e9;
    const inW = new Uint8Array(N * N); for (let i = 0; i < N * N; i++) inW[i] = water[i * 4] > 127 ? 1 : 0;
    const dt = (target) => { // distance (in px) to nearest pixel with inW==target
      const d = new Float32Array(N * N).fill(INF);
      for (let i = 0; i < N * N; i++) if (inW[i] === target) d[i] = 0;
      const a = 1, b = Math.SQRT2;
      for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
        const i = y * N + x; let v = d[i];
        if (x > 0) v = Math.min(v, d[i - 1] + a);
        if (y > 0) { v = Math.min(v, d[i - N] + a); if (x > 0) v = Math.min(v, d[i - N - 1] + b); if (x < N - 1) v = Math.min(v, d[i - N + 1] + b); }
        d[i] = v;
      }
      for (let y = N - 1; y >= 0; y--) for (let x = N - 1; x >= 0; x--) {
        const i = y * N + x; let v = d[i];
        if (x < N - 1) v = Math.min(v, d[i + 1] + a);
        if (y < N - 1) { v = Math.min(v, d[i + N] + a); if (x < N - 1) v = Math.min(v, d[i + N + 1] + b); if (x > 0) v = Math.min(v, d[i + N - 1] + b); }
        d[i] = v;
      }
      return d;
    };
    const dLand = dt(0), dWater = dt(1); const px = REGION.size / R;
    this.sdf = new Float32Array(N * N);
    for (let i = 0; i < N * N; i++) this.sdf[i] = inW[i] ? -(dLand[i] - 0.5) * px : (dWater[i] - 0.5) * px;

    // --- pack region texture RGBA: R water, G urban, B forest, A freeway ---
    const rgba = new Uint8Array(N * N * 4);
    for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
      const i = y * N + x; const e = (REGION.x0 + (x + 0.5) * px) / 1000, n = -(REGION.z0 + (y + 0.5) * px) / 1000;
      const forest = clamp((fbm(e * 0.9 + 3.1, n * 0.9 - 7.7, 4) - 0.52) * 4.0, 0, 1);
      rgba[i * 4] = water[i * 4]; rgba[i * 4 + 1] = urban[i * 4]; rgba[i * 4 + 2] = forest * 255; rgba[i * 4 + 3] = fwy[i * 4];
    }
    this.regionRGBA = rgba;
    this.urbanMask = urban; this.fwyMask = fwy;
    this.buildShore();
  }

  // NAIP shoreline (data/sfo_shore.js) as a 2.5 m mask over its coverage: 255 land, 0 Bay water, 128 no data.
  // shoreAt() -> land fraction 0..1 (bilinear), -1 outside the coverage or on no-data pixels
  buildShore() {
    this.shore = null;
    if (!SHORE || !SHORE.rings || !SHORE.coverage) return;
    const res = 2.5, [x0, z0, x1, z1] = SHORE.coverage; const W = Math.ceil((x1 - x0) / res), H = Math.ceil((z1 - z0) / res);
    const cv = document.createElement('canvas'); cv.width = W; cv.height = H; const cx = cv.getContext('2d', { willReadFrequently: true });
    const path = (rings) => { cx.beginPath(); for (const r of rings) r.forEach((p, i) => { const X = (p[0] - x0) / res, Y = (p[1] - z0) / res; i ? cx.lineTo(X, Y) : cx.moveTo(X, Y); }); cx.closePath(); };
    cx.fillStyle = '#000'; cx.fillRect(0, 0, W, H);
    cx.fillStyle = '#fff'; for (const r of SHORE.rings) { path([r]); cx.fill(); }
    cx.fillStyle = '#808080'; for (const r of SHORE.nodata || []) { path([r]); cx.fill(); }
    const d = cx.getImageData(0, 0, W, H).data; const m = new Uint8Array(W * H);
    for (let i = 0; i < W * H; i++) m[i] = d[i * 4];
    cv.width = cv.height = 1;
    this.shore = { m, W, H, ox: x0, oz: z0, res };
  }
  shoreAt(x, z) {
    const S = this.shore; if (!S) return -1;
    const fx = (x - S.ox) / S.res - 0.5, fz = (z - S.oz) / S.res - 0.5;
    if (fx < 0 || fz < 0 || fx >= S.W - 1 || fz >= S.H - 1) return -1;
    const ix = Math.floor(fx), iz = Math.floor(fz), tx = fx - ix, tz = fz - iz, m = S.m, W = S.W;
    const a = m[iz * W + ix], b = m[iz * W + ix + 1], c = m[(iz + 1) * W + ix], dd = m[(iz + 1) * W + ix + 1];
    if (a === 128 || b === 128 || c === 128 || dd === 128) return -1;
    return (a + (b - a) * tx + (c - a) * tz + (a - b - c + dd) * tx * tz) / 255;
  }

  sampleSDF(x, z) {
    const N = REGION.res; const fx = (x - REGION.x0) / REGION.size * N - 0.5, fz = (z - REGION.z0) / REGION.size * N - 0.5;
    const ix = clamp(Math.floor(fx), 0, N - 2), iz = clamp(Math.floor(fz), 0, N - 2); const tx = clamp(fx - ix, 0, 1), tz = clamp(fz - iz, 0, 1);
    const s = this.sdf; const a = s[iz * N + ix], b = s[iz * N + ix + 1], c = s[(iz + 1) * N + ix], d = s[(iz + 1) * N + ix + 1];
    return a + (b - a) * tx + (c - a) * tz + (a - b - c + d) * tx * tz;
  }
  sampleMask(arr, x, z) {
    const N = REGION.res; const ix = clamp(Math.floor((x - REGION.x0) / REGION.size * N), 0, N - 1), iz = clamp(Math.floor((z - REGION.z0) / REGION.size * N), 0, N - 1);
    return arr[(iz * N + ix) * 4] / 255;
  }
  hills(e, n) { // e,n in meters
    const ek = e / 1000, nk = n / 1000; let h = 0;
    for (const r of RIDGES) {
      let best = 0;
      for (let i = 0; i < r.pts.length - 1; i++) {
        const a = r.pts[i], b = r.pts[i + 1];
        const [d, t] = segDist(ek, nk, a[0], a[1], b[0], b[1]);
        const hh = a[2] + (b[2] - a[2]) * t;
        const w = r.w * (0.8 + 0.4 * vnoise(ek * 0.7 + i, nk * 0.7));
        const f = Math.exp(-Math.pow(d / w, 2) * 1.6);
        best = Math.max(best, hh * f);
      }
      h = Math.max(h, best) + 0.15 * Math.min(h, best);
    }
    // ridged detail scaled by height
    const det = ridged(ek * 1.3, nk * 1.3, 5);
    h *= 0.75 + 0.5 * det;
    return h;
  }
  height(x, z) {
    const e = x, n = -z;
    // airport exact SDF (in s,t)
    const [s, t] = enToST(e, n);
    const aptD = polySDF(s, t, AIRPORT_LAND_ST);
    let d = this.sampleSDF(x, z);
    if (aptD > -400) d = Math.max(d, aptD); // union
    let h;
    if (d < 0) { // water
      h = -1.2 - Math.min(-d * 0.004, 9) - 1.5 * fbm(e * 0.0005, n * 0.0005, 3);
      if (aptD > -60) h = Math.min(h, -2.5 + aptD * 0.08);
    } else {
      const coastal = Math.min(d * 0.012, 30) + 1.2;
      const hillsH = this.hills(e, n) * smooth(0, 900, d);
      const bumps = (fbm(e * 0.002, n * 0.002, 4) - 0.5) * 14 * smooth(200, 1500, d);
      h = coastal + hillsH + bumps;
      // the Peninsula reservoirs (env-14: the old comment here promised a carve that the code never did)
      h = lakeShape(x, z, h);
      // airport flattening
      if (aptD > -400) {
        const k = smooth(-400, 20, aptD);
        const flat = GROUND_Y;
        h = h * (1 - k) + flat * k;
        const dReg = this.sampleSDF(x, z);
        if (aptD < 25 && dReg < 30) { // seawall only where the outside is bay water
          const w = smooth(-9, 6, aptD); h = Math.min(h, -2.6 + (flat + 2.6) * w);
        }
      }
      // gentle shore slope for natural shores
      if (aptD < -250) h = Math.min(h, d * 0.09 + 0.3);
    }
    // review round 3: inside the NAIP coverage (~4.8 x 5 km around the airport) the measured shoreline decides land and
    // water (the regional Bay polygon and the 16-vertex airport polygon are km- / 100 m-scale approximations): water
    // drops to the Bay floor at the line (vertical seawalls), land rises to the airfield level near the airport
    // (within 200 m of its polygon) and to at least 1.2 m elsewhere
    const m = this.shoreAt(x, z);
    if (m >= 0) {
      // (only where the ground is coastal lowland: a misclassified 'water' cell in the hills became a 100 m deep shaft --
      // the US-101 / I-380 strip at the NAIP west edge, 13 Nov 2026; the data is fixed in tools/imagery/shore_naip.py, this
      // guard keeps any future misclassification from carving more than the shore: real water cells lie below 8.5 m here)
      if (m < 0.5 && h < 20) h = Math.min(h, -2.6 - 0.8 * fbm(e * 0.0011, n * 0.0011, 2));
      else if (aptD > -200 && h < GROUND_Y) h = GROUND_Y;
      else if (h < 1.2) h = 1.2;
    }
    return h;
  }

  // Build chunked non-uniform grid mesh data. lakeCell: across each reservoir's box (+ LAKE_BANK_M) the grid lines are
  // no further apart than this (extra lines, per axis), so the drawn shore follows the ring (0 = off). Without them the
  // cells there are 100-550 m along z and the interpolated land covered 5-17 % of the water (close-out round 5, env-14;
  // scratch lake_mesh2.mjs, San Andreas / Lower / Upper Crystal Springs visible: step 15 (high) 95.3 / 86.4 / 85.9 % ->
  // 96.7 / 95.7 / 98.7 % at 80 m, +14 % vertices; step 30 (low / phone) 94.5 / 83.3 / 84.7 -> 95.9 / 95.1 / 98.3 %, +25 %
  // = +53k vertices; tools/env/test_c3.mjs checks the built mesh). GPU cost unmeasured (owner item OD-7).
  buildMeshes(center = [0, 0], step = 15, inner = 4200, lakeCell = 80) {
    const coords = []; // 1D grid coords (fine region +-inner)
    for (let x = -inner; x <= inner + 1e-6; x += step) coords.push(x);
    let x = inner, s = step; const rr = 1.052;
    while (x < 60000) { s *= rr; x += s; coords.unshift(-x); coords.push(x); }
    const refine = (C, ranges) => {   // split the cells that overlap a range into equal parts <= lakeCell
      if (!(lakeCell > 0) || !ranges.length) return C; const out = [C[0]];
      for (let i = 1; i < C.length; i++) { const a = C[i - 1], b = C[i];
        if (b - a > lakeCell && ranges.some(([r0, r1]) => b > r0 && a < r1)) { const k = Math.ceil((b - a) / lakeCell); for (let q = 1; q < k; q++) out.push(a + (b - a) * q / k); }
        out.push(b); }
      return out; };
    const LB = LAKES.map(L => L.box);   // (already grown by LAKE_BANK_M)
    const xs = refine(coords, LB.map(b => [b[0] - center[0], b[2] - center[0]])), zs = refine(coords, LB.map(b => [b[1] - center[1], b[3] - center[1]]));
    const nx = xs.length, nz = zs.length;
    const H = new Float32Array(nx * nz);
    for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) H[j * nx + i] = this.height(xs[i] + center[0], zs[j] + center[1]);
    this.gridN = nx; this.gridNz = nz;
    // chunks
    const CH = 48; const chunks = [];
    for (let cj = 0; cj < nz - 1; cj += CH) for (let ci = 0; ci < nx - 1; ci += CH) {
      const i1 = Math.min(ci + CH, nx - 1), j1 = Math.min(cj + CH, nz - 1);
      const w = i1 - ci + 1, h = j1 - cj + 1;
      const pos = new Float32Array(w * h * 3), nrm = new Float32Array(w * h * 3);
      let minY = 1e9, maxY = -1e9;
      for (let j = cj; j <= j1; j++) for (let i = ci; i <= i1; i++) {
        const k = ((j - cj) * w + (i - ci)) * 3; const y = H[j * nx + i];
        pos[k] = xs[i] + center[0]; pos[k + 1] = y; pos[k + 2] = zs[j] + center[1];
        minY = Math.min(minY, y); maxY = Math.max(maxY, y);
        const il = Math.max(0, i - 1), ir = Math.min(nx - 1, i + 1), jl = Math.max(0, j - 1), jr = Math.min(nz - 1, j + 1);
        const dx = xs[ir] - xs[il], dz = zs[jr] - zs[jl];
        const gx = (H[j * nx + ir] - H[j * nx + il]) / dx, gz = (H[jr * nx + i] - H[jl * nx + i]) / dz;
        const l = Math.hypot(gx, 1, gz); nrm[k] = -gx / l; nrm[k + 1] = 1 / l; nrm[k + 2] = -gz / l;
      }
      const idx = new Uint32Array((w - 1) * (h - 1) * 6); let q = 0;
      for (let j = 0; j < h - 1; j++) for (let i = 0; i < w - 1; i++) {
        const a = j * w + i, b = a + 1, c = a + w, d = c + 1;
        // alternate diagonal for better shape
        if ((i + j) & 1) { idx[q++] = a; idx[q++] = c; idx[q++] = b; idx[q++] = b; idx[q++] = c; idx[q++] = d; }
        else { idx[q++] = a; idx[q++] = c; idx[q++] = d; idx[q++] = a; idx[q++] = d; idx[q++] = b; }
      }
      chunks.push({ pos, nrm, idx, bbox: [xs[ci] + center[0], minY, zs[cj] + center[1], xs[i1] + center[0], maxY, zs[j1] + center[1]] });
    }
    return chunks;
  }
}
