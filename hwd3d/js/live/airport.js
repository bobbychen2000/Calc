// HWD airport surface map for the ground shader, and the NAIP 2024 backdrop texture.
// Replaces sfo3d/js/live/airport.js @ a967f9b (fork map 1.3: stands, SFO Museum pavement / concrete / paint map, end
// zones, buildings). Kept from sfo3d paintAirportMapReal: painting the pavement layers with a 2-D canvas (anti-aliased
// fills; ribbons stroked with round caps and joins) into an RGBA layer per channel, then packing the channels. Changed:
// the frame is the HWD grid (js/world/grid.js: s along 10 -> 28, t across), the inputs are data/hwd_airport.json, and the
// map is 2 channels (RG8): R = paved coverage of taxiways / taxilanes / aprons / helipads / closed ways, G = closed
// (abandoned / disused) pavement. The runways are not in the map: js/shaders/ground.js draws the NASR rectangles
// analytically. Dropped: stands, wear, landside categories, green paint, end zones (all SFO).
//
// paintAirportMap(airport, site, {res}) -> {data, w, h, rect: {s0, t0, w, h}, res}
// naipTexture(level) -> Promise<{tex, meta, U, V}>   U, V: affine world (x, z, 1) -> texture (u, v)
import { gl, texture } from '../gl.js';
import { gridRectOf, GRID } from '../world/grid.js';
import { wayWidth } from '../world/site.js';
import { worldToUtm10 } from '../geo.js';

export function airportGridRect(airport, margin = 60) {
  const pts = [];
  for (const k of ['taxiways', 'taxilanes']) for (const w of airport[k]) pts.push(...w.pts);
  for (const k of ['aprons', 'hangars', 'buildings', 'helipads']) for (const e of airport[k]) if (e.ring) pts.push(...e.ring);
  for (const r of airport.runways) pts.push(...r.outline.ring);
  return gridRectOf(pts, margin);
}

export function paintAirportMap(airport, site, { res = 0.5, maxTex = 4096 } = {}) {
  const R = airportGridRect(airport);
  while (Math.ceil(R.w / res) > maxTex || Math.ceil(R.h / res) > maxTex) res *= 1.25;
  const W = Math.ceil(R.w / res), H = Math.ceil(R.h / res);
  const rect = { s0: R.s0, t0: R.t0, w: W * res, h: H * res };
  const cv = document.createElement('canvas'); cv.width = W; cv.height = H; const cx = cv.getContext('2d', { willReadFrequently: true });
  const P = (x, z) => { const s = x * GRID.s[0] + z * GRID.s[1], t = x * GRID.t[0] + z * GRID.t[1]; return [(s - rect.s0) / res, (t - rect.t0) / res]; };
  const ring = (r) => { r.forEach((p, i) => { const q = P(p[0], p[1]); i ? cx.lineTo(q[0], q[1]) : cx.moveTo(q[0], q[1]); }); cx.closePath(); };
  const line = (pts, w) => { cx.lineWidth = w / res; cx.beginPath(); pts.forEach((p, i) => { const q = P(p[0], p[1]); i ? cx.lineTo(q[0], q[1]) : cx.moveTo(q[0], q[1]); }); cx.stroke(); };
  cx.lineJoin = 'round'; cx.lineCap = 'round';
  const layer = (fn) => { cx.fillStyle = '#000'; cx.fillRect(0, 0, W, H); cx.fillStyle = '#fff'; cx.strokeStyle = '#fff'; fn(); return cx.getImageData(0, 0, W, H).data; };
  const closed = (w) => w.status !== 'open';
  const pave = layer(() => {
    for (const a of airport.aprons) { cx.beginPath(); ring(a.ring); cx.fill(); }
    for (const h of airport.helipads) { cx.beginPath(); ring(h.ring); cx.fill(); }
    for (const k of ['taxiways', 'taxilanes']) for (const w of airport[k]) line(w.pts, wayWidth(w).m);
  });
  const clos = layer(() => { for (const k of ['taxiways', 'taxilanes']) for (const w of airport[k]) if (closed(w)) line(w.pts, wayWidth(w).m); });
  const data = new Uint8Array(W * H * 2);
  for (let i = 0; i < W * H; i++) { data[i * 2] = pave[i * 4]; data[i * 2 + 1] = clos[i * 4]; }
  cv.width = cv.height = 1;   // release the canvas backing store
  return { data, w: W, h: H, rect, res };
}

export function mapTexture(map) {
  gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
  const t = texture(map.w, map.h, { internal: gl.RG8, format: gl.RG, type: gl.UNSIGNED_BYTE, data: map.data, mips: true, aniso: true });
  gl.pixelStorei(gl.UNPACK_ALIGNMENT, 4);
  return t;
}

// ---------------------------------------------------------------- NAIP 2024 backdrop (USDA NAIP, public domain)
// The texture covers the UTM-aligned mosaic of refs/cache/naip/naip_2024_hwd_rgb.jpg (js/world/tex/make_naip_tex.py makes
// the downsampled JPEGs and naip2024.json). The world -> (u, v) map is an affine least-squares fit of geo.js worldToUtm10
// over the mosaic (measured residual 6 mm, docs/phase2_world.md); u = (E - E0) / width_m, v = (N0 - N) / height_m.
export async function naipTexture(level = '1m2') {
  const base = new URL('../world/tex/', import.meta.url);
  const meta = await (await fetch(new URL('naip2024.json', base))).json();
  const L = meta.levels[level];
  const img = new Image(); img.decoding = 'async'; img.src = new URL(L.file, base).href;
  await img.decode();
  const tex = texture(L.width, L.height, { internal: gl.SRGB8_ALPHA8, format: gl.RGBA, type: gl.UNSIGNED_BYTE, source: img, mips: true, aniso: true });
  const fit = naipAffine(meta, L);
  return { tex, meta, level: L, U: fit.U, V: fit.V, residual_m: fit.residual_m };
}
// Regional backdrop beyond the HWD mosaic: a 24 x 24 km 8 m (16 m on the low tier) USDA NAIP 2024 resampling centred on
// the ARP (js/world/tex/fetch_region.py), mapped by the same kind of affine fit over +-12 km (residual measured at load,
// world.stats.region.residual_m).
export async function regionTexture(level = '8m') {
  const base = new URL('../world/tex/', import.meta.url);
  const meta = await (await fetch(new URL('naip2024.json', base))).json();
  const G = meta.region; if (!G) throw new Error('no region entry in naip2024.json');
  const file = level === '16m' ? G.file_16m : G.file; const k = level === '16m' ? 2 : 1;
  const img = new Image(); img.decoding = 'async'; img.src = new URL(file, base).href;
  await img.decode();
  const L = { width: G.width / k, height: G.height / k, pixel_size_m: G.pixel_size_m * k };
  const tex = texture(L.width, L.height, { internal: gl.SRGB8_ALPHA8, format: gl.RGBA, type: gl.UNSIGNED_BYTE, source: img, mips: true, aniso: true });
  const fit = naipAffine({ origin_E: G.origin_E, origin_N: G.origin_N }, L, 12000, 1000);
  return { tex, meta: G, level: L, U: fit.U, V: fit.V, residual_m: fit.residual_m };
}
export function naipAffine(meta, L, half = 2000, step = 250) {
  const Wm = L.width * L.pixel_size_m, Hm = L.height * L.pixel_size_m;
  const S = [];
  for (let x = -half + 100; x <= half + 100; x += step) for (let z = -half + 300; z <= half - 200; z += step) { const [E, N] = worldToUtm10(x, z); S.push([x, z, (E - meta.origin_E) / Wm, (meta.origin_N - N) / Hm]); }
  const fit = (k) => {
    let a = [[0, 0, 0], [0, 0, 0], [0, 0, 0]], b = [0, 0, 0];
    for (const s of S) { const r = [s[0], s[1], 1]; for (let i = 0; i < 3; i++) { b[i] += r[i] * s[k]; for (let j = 0; j < 3; j++) a[i][j] += r[i] * r[j]; } }
    const det = (m) => m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0]) + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]);
    const D = det(a); return [0, 1, 2].map(i => det(a.map((row, j) => row.map((v, l) => l === i ? b[j] : v))) / D);
  };
  const U = fit(2), V = fit(3);
  let res = 0; for (const s of S) res = Math.max(res, Math.hypot((U[0] * s[0] + U[1] * s[1] + U[2] - s[2]) * Wm, (V[0] * s[0] + V[1] * s[1] + V[2] - s[3]) * Hm));
  return { U, V, residual_m: res };
}
