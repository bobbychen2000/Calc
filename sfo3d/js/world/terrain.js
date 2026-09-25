import { BAY_WATER_KM, AIRPORT_LAND_ST, stToEN, enToST, GROUND_Y } from '../geo.js';
import { fbm, ridged, vnoise, smooth, clamp } from '../math.js';
// Shoreline measured on USDA NAIP 2024 near-infrared (tools/imagery/shore_naip.py, review round 3): decides land vs Bay
// water inside the NAIP coverage around the airport. AIRPORT_LAND_ST (js/geo.js, 16 vertices) stays the airport AREA
// mask of the shaders; as a coastline the old one was off by tens of metres (east edge 44 m out in the Bay at the 28
// ends, the north basin as land), and the regional BAY_WATER_KM polygon is km-scale.
import { SHORE } from '../../data/sfo_shore.js';

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
      // crystal springs / san andreas valley lakes carve
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
      if (m < 0.5) h = Math.min(h, -2.6 - 0.8 * fbm(e * 0.0011, n * 0.0011, 2));
      else if (aptD > -200 && h < GROUND_Y) h = GROUND_Y;
      else if (h < 1.2) h = 1.2;
    }
    return h;
  }

  // Build chunked non-uniform grid mesh data
  buildMeshes(center = [0, 0], step = 15, inner = 4200) {
    const coords = []; // 1D grid coords (fine region +-inner)
    for (let x = -inner; x <= inner + 1e-6; x += step) coords.push(x);
    let x = inner, s = step; const rr = 1.052;
    while (x < 60000) { s *= rr; x += s; coords.unshift(-x); coords.push(x); }
    const n = coords.length;
    const H = new Float32Array(n * n);
    for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) H[j * n + i] = this.height(coords[i] + center[0], coords[j] + center[1]);
    this.gridN = n;
    // chunks
    const CH = 48; const chunks = [];
    for (let cj = 0; cj < n - 1; cj += CH) for (let ci = 0; ci < n - 1; ci += CH) {
      const i1 = Math.min(ci + CH, n - 1), j1 = Math.min(cj + CH, n - 1);
      const w = i1 - ci + 1, h = j1 - cj + 1;
      const pos = new Float32Array(w * h * 3), nrm = new Float32Array(w * h * 3);
      let minY = 1e9, maxY = -1e9;
      for (let j = cj; j <= j1; j++) for (let i = ci; i <= i1; i++) {
        const k = ((j - cj) * w + (i - ci)) * 3; const y = H[j * n + i];
        pos[k] = coords[i] + center[0]; pos[k + 1] = y; pos[k + 2] = coords[j] + center[1];
        minY = Math.min(minY, y); maxY = Math.max(maxY, y);
        const il = Math.max(0, i - 1), ir = Math.min(n - 1, i + 1), jl = Math.max(0, j - 1), jr = Math.min(n - 1, j + 1);
        const dx = coords[ir] - coords[il], dz = coords[jr] - coords[jl];
        const gx = (H[j * n + ir] - H[j * n + il]) / dx, gz = (H[jr * n + i] - H[jl * n + i]) / dz;
        const l = Math.hypot(gx, 1, gz); nrm[k] = -gx / l; nrm[k + 1] = 1 / l; nrm[k + 2] = -gz / l;
      }
      const idx = new Uint32Array((w - 1) * (h - 1) * 6); let q = 0;
      for (let j = 0; j < h - 1; j++) for (let i = 0; i < w - 1; i++) {
        const a = j * w + i, b = a + 1, c = a + w, d = c + 1;
        // alternate diagonal for better shape
        if ((i + j) & 1) { idx[q++] = a; idx[q++] = c; idx[q++] = b; idx[q++] = b; idx[q++] = c; idx[q++] = d; }
        else { idx[q++] = a; idx[q++] = c; idx[q++] = d; idx[q++] = a; idx[q++] = d; idx[q++] = b; }
      }
      chunks.push({ pos, nrm, idx, bbox: [coords[ci] + center[0], minY, coords[cj] + center[1], coords[i1] + center[0], maxY, coords[j1] + center[1]] });
    }
    return chunks;
  }
}
