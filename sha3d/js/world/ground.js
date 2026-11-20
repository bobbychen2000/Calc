// sha3d ground: the airfield map, the context map, the Sentinel-2 colour hint and the flat ground mesh (new module; the
// sfo3d ground - js/world/terrain.js, airfield.js, world.js bakes - is SFO-specific and not forked).
//
// Inputs (all injected, nothing imported at module scope):
//   airport  = window.SHA_AIRPORT (data/sha_airport.js): surfaces.{runway, runway_shoulders_blast_pads, taxiway,
//              taxiway_shoulders}, aprons, helipads, runways[].aip_facts.surface_segments_m, aerodrome, extent, context
//              {roads, rail, water_lines, water_areas}
//   s2       = window.SHA_GROUND_S2 (data/sha_ground_s2.js, optional): Sentinel-2 reflectance colour hint
//   ext      = the registered extensions (js/live/ext.js): ext.pavement(api) may add pavement to the airfield map
// Rules and their provenance (every one is a rendering rule [inf] unless stated):
//   - airside pavement = the data's surface polygons + aprons + helipads (surfaces are src inf: AIP widths on OSM axes);
//   - concrete vs asphalt: runways per aip_facts.surface_segments_m (AIP (mirror) AD 2.12: 18L/36R asphalt with 100 m
//     concrete ends, 18R/36L concrete) [obs, AIP mirror]; aprons, taxiways and helipads concrete [inf: no OSM surface tag;
//     on the Sentinel-2 hint they are as bright as the concrete runway 18R/36L]; shoulders and blast pads are drawn as a
//     lighter asphalt [inf];
//   - roads: OSM context roads, width from lanes x 3.5 m else a class default (ROAD_W) [inf]; tunnels and layer < 0 are not
//     drawn; bridges / viaducts are drawn on the ground (no elevated decks yet) [inf];
//   - rail: OSM rail lines (no subway, no tunnels), 5 m ballast per line [inf];
//   - water: OSM water areas + waterway lines with a width per kind (WATER_W) [inf]; ditches / drains as damp ground lines;
//   - the ground is flat at GROUND_Y (2.5 m nominal) everywhere; beyond the detailed extent (convex hull of the aerodrome
//     + 1 km, PLAN s.6b Q3) the ground fades over ~200 m to one neutral colour (the mean Sentinel-2 reflectance when the
//     hint is loaded).
import { gl, Mesh, texture } from '../gl.js';
import { GROUND_Y } from '../geo.js';

export const ROAD_W = { motorway: 24, trunk: 21, primary: 17, secondary: 13, tertiary: 9, motorway_link: 8, trunk_link: 8, primary_link: 7, secondary_link: 7, tertiary_link: 6 };
export const WATER_W = { river: 16, canal: 10, stream: 5, ditch: 3, drain: 3 };
const RAIL_W = 5;

function bboxOf(rings, pad = 0) {
  let x0 = 1e9, z0 = 1e9, x1 = -1e9, z1 = -1e9;
  for (const r of rings) for (const p of r) { x0 = Math.min(x0, p[0]); z0 = Math.min(z0, p[1]); x1 = Math.max(x1, p[0]); z1 = Math.max(z1, p[1]); }
  return [x0 - pad, z0 - pad, x1 + pad, z1 + pad];
}
// a 2-D canvas covering rect (x0, z0, w, h) at res m/px; drawing helpers in world metres
function makeCanvas(rect, res) {
  const W = Math.max(1, Math.round(rect[2] / res)), H = Math.max(1, Math.round(rect[3] / res));
  const cv = (typeof OffscreenCanvas !== 'undefined') ? new OffscreenCanvas(W, H) : Object.assign(document.createElement('canvas'), { width: W, height: H });
  const cx = cv.getContext('2d', { willReadFrequently: true });
  cx.fillStyle = '#000'; cx.fillRect(0, 0, W, H); cx.lineJoin = 'round'; cx.lineCap = 'round';
  const P = (p) => [(p[0] - rect[0]) / res, (p[1] - rect[1]) / res];
  const path = (rings) => { cx.beginPath(); for (const r of rings) { if (!r || r.length < 2) continue; r.forEach((p, i) => { const q = P(p); i ? cx.lineTo(q[0], q[1]) : cx.moveTo(q[0], q[1]); }); cx.closePath(); } };
  const api = {
    W, H, cx, rect, res,
    fill(rings, style) { cx.fillStyle = style; path(rings); cx.fill('evenodd'); },
    line(pts, w, style) { if (!pts || pts.length < 2) return; cx.strokeStyle = style; cx.lineWidth = Math.max(w / res, 0.6); cx.beginPath(); pts.forEach((p, i) => { const q = P(p); i ? cx.lineTo(q[0], q[1]) : cx.moveTo(q[0], q[1]); }); cx.stroke(); },
    read() { return cx.getImageData(0, 0, W, H).data; },
  };
  return api;
}
// separable [1 2 1] / 4 blur of one channel of an RGBA array, in place (softens the canvas edge ramp to ~2 px so the
// shader's re-sharpening threshold gives smooth iso-lines)
function blur121(a, W, H, ch, passes = 1) {
  const tmp = new Uint8Array(W * H);
  for (let p = 0; p < passes; p++) {
    for (let y = 0; y < H; y++) { const o = y * W; for (let x = 0; x < W; x++) { const l = a[(o + Math.max(0, x - 1)) * 4 + ch], c = a[(o + x) * 4 + ch], r = a[(o + Math.min(W - 1, x + 1)) * 4 + ch]; tmp[o + x] = (l + 2 * c + r + 2) >> 2; } }
    for (let y = 0; y < H; y++) { const u = Math.max(0, y - 1) * W, d = Math.min(H - 1, y + 1) * W, o = y * W; for (let x = 0; x < W; x++) a[(o + x) * 4 + ch] = (tmp[u + x] + 2 * tmp[o + x] + tmp[d + x] + 2) >> 2; }
  }
}
// box blur (radius r px, 3 passes ~ Gaussian) of a single-channel Float32Array
function boxBlur(f, W, H, r) {
  const t = new Float32Array(W * H);
  for (let pass = 0; pass < 3; pass++) {
    for (let y = 0; y < H; y++) { let s = 0; const o = y * W; for (let x = -r; x <= r; x++) s += f[o + Math.min(W - 1, Math.max(0, x))]; for (let x = 0; x < W; x++) { t[o + x] = s / (2 * r + 1); s += f[o + Math.min(W - 1, x + r + 1)] - f[o + Math.max(0, x - r)]; } }
    for (let x = 0; x < W; x++) { let s = 0; for (let y = -r; y <= r; y++) s += t[Math.min(H - 1, Math.max(0, y)) * W + x]; for (let y = 0; y < H; y++) { f[y * W + x] = s / (2 * r + 1); s += t[Math.min(H - 1, y + r + 1) * W + x] - t[Math.max(0, y - r) * W + x]; } }
  }
}
const roadWidth = (r) => { const n = parseInt(r.lanes, 10); if (n > 0) return Math.max(6, n * 3.5 + (/^(motorway|trunk)$/.test(r.class) ? 3 : 1)); return ROAD_W[r.class] || 8; };
const drawnRoad = (r) => !(r.tunnel && r.tunnel !== 'no') && !(r.layer != null && +r.layer < 0);

// ---------------------------------------------------------------------------------------------- airfield map (fine)
// channels: R airside pavement, G concrete (255 apron, 204 other concrete: the shader reads >= 0.9 as apron), B shoulder /
// blast pad, A landside road (inside the rect). Returns {rect, res, w, h, data (RGBA Uint8Array), stats}.
export function paintAirfieldMap(airport, res = 1.0, exts = []) {
  const S = airport.surfaces || {};
  const rings = [...(S.runway || []), ...(S.runway_shoulders_blast_pads || []), ...(S.taxiway || []), ...(S.taxiway_shoulders || [])].map(p => p.ring)
    .concat((airport.aprons || []).map(a => a.ring));
  const bb = bboxOf(rings, 80); const rect = [Math.floor(bb[0]), Math.floor(bb[1]), Math.ceil(bb[2] - bb[0]), Math.ceil(bb[3] - bb[1])];
  const A = makeCanvas(rect, res); const cx = A.cx; cx.globalCompositeOperation = 'lighter';
  const polyRings = (p) => [p.ring, ...((p.holes) || [])];
  const PAVED = 'rgb(255,0,0)', CONC = 'rgb(0,204,0)', APRON = 'rgb(0,255,0)', SHOULDER = 'rgb(0,0,255)';
  // pavement (R)
  for (const p of S.runway || []) A.fill(polyRings(p), PAVED);
  for (const p of S.runway_shoulders_blast_pads || []) { A.fill(polyRings(p), PAVED); A.fill(polyRings(p), SHOULDER); }
  for (const p of S.taxiway || []) { A.fill(polyRings(p), PAVED); A.fill(polyRings(p), CONC); }
  for (const p of S.taxiway_shoulders || []) { A.fill(polyRings(p), PAVED); A.fill(polyRings(p), SHOULDER); }
  for (const a of airport.aprons || []) { A.fill(polyRings(a), PAVED); A.fill(polyRings(a), APRON); }
  for (const h of airport.helipads || []) { A.fill(polyRings(h), PAVED); A.fill(polyRings(h), CONC); }
  // runway concrete sections (AIP (mirror) AD 2.12 surface_segments_m, s from the first end's pavement start)
  for (const r of airport.runways || []) {
    const f = r.aip_facts || {}; const E = r.ends || []; if (!E[0] || !E[1]) continue;
    const a = E[0].end.xz, b = E[1].end.xz; const L = Math.hypot(b[0] - a[0], b[1] - a[1]); const d = [(b[0] - a[0]) / L, (b[1] - a[1]) / L], n = [-d[1], d[0]];
    const hw = (f.width_m || 45) / 2;
    for (const [s0, s1, t] of f.surface_segments_m || []) {
      if (t !== 'CONC') continue;
      const q = (s, w) => [a[0] + d[0] * s + n[0] * w, a[1] + d[1] * s + n[1] * w];
      A.fill([[q(s0, -hw), q(s1, -hw), q(s1, hw), q(s0, hw)]], CONC);
    }
  }
  // extension pavement (e.g. remote-stand pads from js/live/gates.js): api.fill(rings, kind) / api.line(pts, w, kind)
  const STYLE = { paved: PAVED, concrete: CONC, apron: APRON, shoulder: SHOULDER };
  const extApi = { fill: (rs, kind = 'paved') => A.fill(rs, STYLE[kind] || PAVED), line: (pts, w, kind = 'paved') => A.line(pts, w, STYLE[kind] || PAVED), rect, res };
  for (const e of exts) if (e.pavement) { try { e.pavement(extApi, airport); } catch (err) { console.warn('[ground] extension pavement ' + e.name, err); } }
  const rgb = A.read();
  // landside roads (A) on a second canvas
  const B = makeCanvas(rect, res); B.cx.globalCompositeOperation = 'lighter';
  for (const r of ((airport.context || {}).roads || [])) if (drawnRoad(r)) for (const ln of r.lines || []) B.line(ln, roadWidth(r), '#fff');
  const rd = B.read();
  const W = A.W, H = A.H, out = new Uint8Array(W * H * 4);
  for (let i = 0, n = W * H; i < n; i++) { out[i * 4] = rgb[i * 4]; out[i * 4 + 1] = rgb[i * 4 + 1]; out[i * 4 + 2] = rgb[i * 4 + 2]; out[i * 4 + 3] = rd[i * 4]; }
  for (let ch = 0; ch < 4; ch++) blur121(out, W, H, ch, 1);
  let paved = 0; for (let i = 0, n = W * H; i < n; i++) paved += out[i * 4];
  return { rect, res, w: W, h: H, data: out, stats: { pavedKm2: paved / 255 * res * res / 1e6 } };
}

// ---------------------------------------------------------------------------------------------- context map (coarse)
// channels: R water, G road, B rail, A = 0.5 x extent (soft, ~200 m) + 0.5 x aerodrome (soft, ~30 m)
export function paintContextMap(airport, res = 4.0) {
  const ring = airport.extent && airport.extent.ring; const bb = bboxOf([ring], 900);
  const rect = [Math.floor(bb[0]), Math.floor(bb[1]), Math.ceil(bb[2] - bb[0]), Math.ceil(bb[3] - bb[1])];
  const C = makeCanvas(rect, res); C.cx.globalCompositeOperation = 'lighter';
  const K = airport.context || {};
  for (const w of K.water_areas || []) C.fill([w.ring, ...(w.holes || [])], 'rgb(255,0,0)');
  // ditches and drains (3 m, often grassed) are painted at 110 / 255: below the shader's water threshold (0.5), they draw
  // as damp, darker ground lines instead of open water [inf]
  const NARROW = new Set(['ditch', 'drain']);
  for (const w of K.water_lines || []) if (!(w.tunnel && w.tunnel !== 'no')) for (const ln of w.lines || []) C.line(ln, WATER_W[w.waterway] || 4, NARROW.has(w.waterway) ? 'rgb(110,0,0)' : 'rgb(255,0,0)');
  for (const r of K.roads || []) if (drawnRoad(r)) for (const ln of r.lines || []) C.line(ln, roadWidth(r), 'rgb(0,255,0)');
  for (const r of K.rail || []) if (r.railway === 'rail' && !(r.tunnel && r.tunnel !== 'no') && !(r.layer != null && +r.layer < 0)) for (const ln of r.lines || []) C.line(ln, RAIL_W, 'rgb(0,0,255)');
  const rgb = C.read();
  const M = makeCanvas(rect, res); M.cx.globalCompositeOperation = 'lighter';
  M.fill([ring], 'rgb(255,0,0)'); for (const r of (airport.aerodrome && airport.aerodrome.rings) || []) M.fill([r], 'rgb(0,255,0)');
  const mk = M.read(); const W = C.W, H = C.H, n = W * H;
  const ext = new Float32Array(n), aer = new Float32Array(n);
  for (let i = 0; i < n; i++) { ext[i] = mk[i * 4] / 255; aer[i] = mk[i * 4 + 1] / 255; }
  boxBlur(ext, W, H, Math.max(1, Math.round(150 / res))); boxBlur(aer, W, H, Math.max(1, Math.round(12 / res)));
  const out = new Uint8Array(n * 4);
  for (let i = 0; i < n; i++) { out[i * 4] = rgb[i * 4]; out[i * 4 + 1] = rgb[i * 4 + 1]; out[i * 4 + 2] = rgb[i * 4 + 2]; out[i * 4 + 3] = Math.round(127.5 * Math.min(1, ext[i]) + 127.5 * Math.min(1, aer[i])); }
  return { rect, res, w: W, h: H, data: out };
}

// ---------------------------------------------------------------------------------------------- Sentinel-2 hint
export async function loadS2Hint(s2) {
  if (!s2 || !s2.png) return null;
  const bin = atob(s2.png); const u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
  const bmp = await createImageBitmap(new Blob([u], { type: 'image/png' }), { premultiplyAlpha: 'none', colorSpaceConversion: 'none' });
  const t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t);
  gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false); gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL, gl.NONE);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, gl.RGBA, gl.UNSIGNED_BYTE, bmp);
  gl.generateMipmap(gl.TEXTURE_2D);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  if (bmp.close) bmp.close();
  const m = s2.mean_reflectance_rgb || [0.1, 0.1, 0.085];
  return { tex: { tex: t, w: s2.w, h: s2.h }, rect: s2.rect, mean: m };
}

// ---------------------------------------------------------------------------------------------- ground mesh
// flat tiles at GROUND_Y: 1 km tiles over +-6 km (culling, near / far split), then a ring of large tiles to +-80 km
export function buildGroundMesh(y = GROUND_Y) {
  const chunks = []; const T = 1000, R0 = 6000, RF = 80000;
  const quad = (x0, z0, x1, z1, n) => { const pos = [], nrm = [], idx = [];
    for (let j = 0; j <= n; j++) for (let i = 0; i <= n; i++) { pos.push(x0 + (x1 - x0) * i / n, y, z0 + (z1 - z0) * j / n); nrm.push(0, 1, 0); }
    for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) { const a = j * (n + 1) + i; idx.push(a, a + n + 1, a + 1, a + 1, a + n + 1, a + n + 2); }
    chunks.push({ pos: new Float32Array(pos), nrm: new Float32Array(nrm), idx: new Uint32Array(idx), bbox: [x0, y - 1, z0, x1, y + 1, z1] }); };
  for (let z = -R0; z < R0; z += T) for (let x = -R0; x < R0; x += T) quad(x, z, x + T, z + T, 4);
  for (const [x0, z0, x1, z1] of [[-RF, -RF, RF, -R0], [-RF, R0, RF, RF], [-RF, -R0, -R0, R0], [R0, -R0, RF, R0]]) quad(x0, z0, x1, z1, 8);
  return chunks;
}

// ---------------------------------------------------------------------------------------------- assembly
// opts: {mapRes, ctxRes, exts}. Returns {items, uniforms, maps: {apt, ctx}, pavedAt(x, z), s2}
export async function buildGround(R, airport, opts = {}) {
  const t0 = performance.now();
  const exts = opts.exts || [];
  const apt = paintAirfieldMap(airport, opts.mapRes || 1.0, exts);
  const ctxm = paintContextMap(airport, opts.ctxRes || 4.0);
  const t1 = performance.now();
  const aptTex = texture(apt.w, apt.h, { data: apt.data, mips: true, aniso: 8 });
  const ctxTex = texture(ctxm.w, ctxm.h, { data: ctxm.data, mips: true, aniso: 4 });
  let s2 = null; try { s2 = await loadS2Hint(opts.s2); } catch (e) { console.warn('[ground] Sentinel-2 hint not loaded', e); }
  // CPU copy of the pavement coverage at 2 m (for physics / placement code: pavedAt)
  const k = Math.max(1, Math.round(2 / apt.res)); const pw = Math.ceil(apt.w / k), ph = Math.ceil(apt.h / k); const pav = new Uint8Array(pw * ph);
  for (let y = 0; y < ph; y++) for (let x = 0; x < pw; x++) pav[y * pw + x] = apt.data[((Math.min(apt.h - 1, y * k)) * apt.w + Math.min(apt.w - 1, x * k)) * 4];
  const pavedAt = (x, z) => { const i = Math.floor((x - apt.rect[0]) / (apt.res * k)), j = Math.floor((z - apt.rect[1]) / (apt.res * k)); return i < 0 || j < 0 || i >= pw || j >= ph ? 0 : pav[j * pw + i] / 255; };
  // runway axis for the slab grid: the mean of the runway directions (both parallel, 177.3 deg)
  let gd = [0, 1]; if (airport.runways && airport.runways.length) { let sx = 0, sz = 0; for (const r of airport.runways) { sx += r.axis_unit_xz[0]; sz += r.axis_unit_xz[1]; } const l = Math.hypot(sx, sz); gd = [sx / l, sz / l]; }
  // neutral: the luminance of the mean Sentinel-2 reflectance of the extent, slightly green-grey [inf]
  const neutral = (() => { const m = s2 ? s2.mean : [0.10, 0.10, 0.085]; const L = 0.2126 * m[0] + 0.7152 * m[1] + 0.0722 * m[2]; return [L * 1.0, L * 1.03, L * 0.94]; })();
  const uniforms = { uAptMap: aptTex, uAptRect: apt.rect, uCtxMap: ctxTex, uCtxRect: ctxm.rect, uS2: s2 ? s2.tex : aptTex, uS2Rect: s2 ? s2.rect : [0, 0, 1, 1], uHasS2: s2 ? 1 : 0, uS2Mix: 0.85, uGridDir: gd, uNeutral: neutral };
  const items = buildGroundMesh().map(c => ({ mesh: new Mesh({ pos: c.pos, nrm: c.nrm, idx: c.idx }), prog: 'ground', uniforms, bbox: c.bbox, castShadow: false, ground: true }));
  const info = { aptMap: `${apt.w}x${apt.h} @ ${apt.res} m`, ctxMap: `${ctxm.w}x${ctxm.h} @ ${ctxm.res} m`, pavedKm2: +apt.stats.pavedKm2.toFixed(3), s2: !!s2, paintMs: Math.round(t1 - t0), totalMs: Math.round(performance.now() - t0) };
  return { items, uniforms, maps: { apt: { rect: apt.rect, res: apt.res, w: apt.w, h: apt.h }, ctx: { rect: ctxm.rect, res: ctxm.res, w: ctxm.w, h: ctxm.h } }, pavedAt, s2, info };
}
