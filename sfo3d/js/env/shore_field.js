// Distance into the Bay from the NAIP 2024 shoreline (data/sfo_shore.js, tools/imagery/shore_naip.py: 2 m water
// classification, land inside `rings`, Bay water elsewhere inside `coverage`) for the seawall foam of both renderers
// (close-out round 3, env-13; static_geometry_round3.md §6, engine_closeout.md §3). Before, both water shaders took the
// distance from the 16-vertex AIRPORT_LAND_ST polygon (js/geo.js: up to ~100-143 m off the real seawall, median 11 m),
// so the foam band floated in open water or ran over land. Pure JS, no DOM: a land mask on a CELL-m grid over the
// coverage (scanline fill of the rings, even-odd), then the exact Euclidean distance of every water cell to the nearest
// land cell centre (Felzenszwalb & Huttenlocher 2012, "Distance Transforms of Sampled Functions", 1-D squared-distance
// lower envelopes per row and column), minus half a cell (the shore lies between a land and a water cell), clamped to
// MAX_M and stored as 0..255. Land cells are 0. Outside the coverage the shaders keep their old distance.
import { SHORE } from '../../data/sfo_shore.js';

export const CELL = 2.0, MAX_M = 40.0;
let cache = null;
/** {w, h, rect: [x0, z0, width, depth] (world m), data: Uint8Array w*h (distance into the water x 255 / MAX_M), cell,
 *  maxM, stats} - computed once. */
export function shoreField() {
  if (cache) return cache;
  const [x0, z0, x1, z1] = SHORE.coverage; const w = Math.ceil((x1 - x0) / CELL), h = Math.ceil((z1 - z0) / CELL);
  const land = new Uint8Array(w * h);
  const edges = []; for (const r of SHORE.rings) for (let i = 0, j = r.length - 1; i < r.length; j = i++) edges.push(r[j][0], r[j][1], r[i][0], r[i][1]);
  const xs = [];
  for (let row = 0; row < h; row++) {
    const z = z0 + (row + 0.5) * CELL; xs.length = 0;
    for (let e = 0; e < edges.length; e += 4) { const za = edges[e + 1], zb = edges[e + 3]; if ((za > z) !== (zb > z)) xs.push(edges[e] + (z - za) / (zb - za) * (edges[e + 2] - edges[e])); }
    xs.sort((a, b) => a - b);
    for (let k = 0; k + 1 < xs.length; k += 2) {
      const c0 = Math.max(0, Math.ceil((xs[k] - x0) / CELL - 0.5)), c1 = Math.min(w - 1, Math.floor((xs[k + 1] - x0) / CELL - 0.5));
      for (let c = c0; c <= c1; c++) land[row * w + c] = 1;
    }
  }
  // squared distance (in cells) to the nearest land cell: rows, then columns
  const INF = 1e20, f = new Float64Array(Math.max(w, h)), d = new Float64Array(Math.max(w, h)), v = new Int32Array(Math.max(w, h)), zz = new Float64Array(Math.max(w, h) + 1);
  const dt1 = (n) => { // in f[0..n), out d[0..n)
    let k = 0; v[0] = 0; zz[0] = -INF; zz[1] = INF;
    for (let q = 1; q < n; q++) {
      let s = ((f[q] + q * q) - (f[v[k]] + v[k] * v[k])) / (2 * q - 2 * v[k]);
      while (s <= zz[k]) { k--; s = ((f[q] + q * q) - (f[v[k]] + v[k] * v[k])) / (2 * q - 2 * v[k]); }
      k++; v[k] = q; zz[k] = s; zz[k + 1] = INF;
    }
    k = 0; for (let q = 0; q < n; q++) { while (zz[k + 1] < q) k++; d[q] = (q - v[k]) * (q - v[k]) + f[v[k]]; }
  };
  const D = new Float64Array(w * h);
  for (let row = 0; row < h; row++) { for (let c = 0; c < w; c++) f[c] = land[row * w + c] ? 0 : INF; dt1(w); for (let c = 0; c < w; c++) D[row * w + c] = d[c]; }
  for (let c = 0; c < w; c++) { for (let row = 0; row < h; row++) f[row] = D[row * w + c]; dt1(h); for (let row = 0; row < h; row++) D[row * w + c] = d[row]; }
  const data = new Uint8Array(w * h); let nW = 0, nNear = 0;
  for (let i = 0; i < w * h; i++) {
    if (land[i]) continue; nW++;
    const m = Math.max(0, Math.sqrt(D[i]) * CELL - CELL / 2); if (m < 8) nNear++;
    data[i] = Math.min(255, Math.round(Math.min(m, MAX_M) / MAX_M * 255));
  }
  cache = { w, h, rect: [x0, z0, x1 - x0, z1 - z0], data, cell: CELL, maxM: MAX_M, stats: { cells: w * h, water: nW, within8m: nNear } };
  return cache;
}
/** Distance into the water (m) at world (x, z) from the field (nearest cell), or null outside the coverage (tests). */
export function shoreDistanceAt(x, z) {
  const F = shoreField(); const c = Math.floor((x - F.rect[0]) / F.cell), r = Math.floor((z - F.rect[1]) / F.cell);
  if (c < 0 || r < 0 || c >= F.w || r >= F.h) return null;
  return F.data[r * F.w + c] / 255 * F.maxM;
}
