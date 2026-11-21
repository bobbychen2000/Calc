// sha3d terminals extension (package P2d): T1 / T2 with their piers and concourses, the east control tower, the two
// untyped south-west towers, the hangars, the business-aviation terminal and the other airport buildings, the Hongqiao
// transport hub (low detail), the context buildings of the detailed extent as LOD blocks, and the far ground beyond the
// extent (ESA WorldCover 2021 class colours fading into haze). Replaces the core placeholders through js/live/ext.js.
// Pattern: sfo3d@e3218d6 js/live/terminals.js (one module builds the terminal complex, the tower and their anchors);
// NO SFO geometry, dimension or data is used - everything comes from the injected data:
//   window.SHA_BUILDINGS3D   data/sha_buildings3d.js   (tools/buildings/build_buildings3d.py: OSM outlines split into
//                            volumes, heights from B3 / rules, styles; all inf except the outlines)
//   window.SHA_LANDCOVER_FAR data/sha_landcover_far.js (tools/terrain/worldcover_far.py: ESA WorldCover 2021, CC BY 4.0,
//                            50 m class fractions, colours calibrated on Sentinel-2 inside the extent)
//   ctx.airport              data/sha_airport.js       (context buildings for the LOD blocks; control-tower node)
// URL switches (QA): ?bld=0 keeps the core placeholders (claims nothing), ?far=0 keeps the core's neutral far ground.
// Geometry: js/world/buildings3d.js. Every facade, roof form, colour and the haze law are rendering parameters [inf].
import { registerExtension } from './ext.js';
import { gl, Mesh, texture } from '../gl.js';
import { m4 } from '../math.js';
import { Geo } from '../geom.js';
import { buildPart, buildHangar, buildControlTower, buildBlockTower, buildContextBlocks, buildWaterEdges } from '../world/buildings3d.js';

const Q = (typeof location !== 'undefined') ? new URLSearchParams(location.search) : new URLSearchParams('');
const ON = Q.get('bld') !== '0', FAR_ON = Q.get('far') !== '0';
const B3D = () => (typeof window !== 'undefined' && window.SHA_BUILDINGS3D) || null;
const FAR = () => (typeof window !== 'undefined' && window.SHA_LANDCOVER_FAR) || null;
// the haze law [inf]: strength, start distance from the camera (m), e-folding distance (m; used only when the scaling below
// is off), ramp width outside the detailed extent (m; the far attribute map's B channel holds the signed edge distance)
const FAR_HAZE = [1.0, 2500, 14000, 4000];
// fix round 1 (review L9): the e-folding distance follows the environment's surface extinction (uFog.x, from the METAR
// visibility via js/env/state.js): L = clamp(K / sigma, Lmin, Lmax). K 0.8, Lmin 1.2 km; Lmax 20 km is the Shanghai haze
// floor (even a dry CAVOK day keeps a residual haze, photos 22 / 23) [inf]. CAVOK / clear air (sigma 3.3e-5 /m) -> 20 km
// (was a fixed 14 km); 10 km visibility (sigma 3.9e-4) -> 2 km; 5 km -> 1.2 km
const FAR_HAZE_SIGMA = [0.8, 1200, 20000];
// fix round 1 (lead: hard ring at the edge of the detailed extent): the haze ramp starts EDGE_HAZE_IN m inside the edge,
// and the Sentinel-2 hint is cross-faded to the far land-cover colour over the inner EDGE_COL m (see featherS2) [inf]
const EDGE_HAZE_IN = 300, EDGE_COL = [60, 480];

const FAR_GLSL = `
// sha_ground_far (js/live/terminals.js, package P2d): ESA WorldCover 2021 class colours beyond the detailed extent, with a
// procedural roof-tone pattern on built-up cells (no buildings, no roads: PLAN s.6b Q3), sky-reflecting water and a night
// urban glow; beyond the 20 km land-cover crop, the crop's mean colour; a distance haze toward the horizon sky colour that
// ramps in from 300 m inside the extent edge to 4 km outside it (so the edge shows no step), with an e-folding distance
// from the environment's surface extinction (fix round 1; rendering law [inf]).
uniform sampler2D uFarCol; uniform sampler2D uFarAttr; uniform vec4 uFarRect; uniform float uHasFar; uniform vec3 uFarMean;
uniform vec4 uFarHaze; uniform sampler2D uFarSky; uniform float uHasFarSky; uniform vec2 uFarDist; uniform vec4 uFarHazeSig;
vec3 shaFarLin(vec3 c){ return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(0.04045, c)); }
vec3 shaGroundFar(vec3 wp, float dist, vec3 neutral, inout float water, inout float glow){
  if (uHasFar < 0.5) return neutral;
  vec2 uv = (wp.xz - uFarRect.xy) / uFarRect.zw;
  vec2 e2 = min(uv, 1.0 - uv) * uFarRect.zw; float inMap = smoothstep(0.0, 1800.0, min(e2.x, e2.y));
  vec2 cuv = clamp(uv, 0.0, 1.0);
  vec3 rho = shaFarLin(texture(uFarCol, cuv).rgb) * 0.5;
  vec4 at = texture(uFarAttr, cuv);
  vec4 nA = texture(uNoise, wp.xz / 2300.0), nB = texture(uNoise, wp.xz / 260.0), nC = texture(uNoise, wp.xz / 37.0);
  vec2 q = (wp.xz + (nA.gb - 0.5) * 140.0) / 60.0; vec2 cell = floor(q); float h1 = hash12(cell), h2 = hash12(cell + 17.3);
  float fade = 1.0 - smoothstep(3500.0, 15000.0, dist);
  float built = at.g;
  // built-up cells: 0.9 x the class colour for the streets / shadows a 50 m cell cannot resolve [inf], per-cell roof tone
  vec3 tone = rho * mix(1.0, 0.9 * (0.82 + 0.36 * h1), built * mix(0.6, 1.0, fade));
  tone = mix(tone, vec3(0.18, 0.18, 0.17), built * step(0.94, h2) * fade * 0.35);
  tone = mix(tone, vec3(0.06, 0.09, 0.13), built * step(0.97, h1) * fade * 0.3);
  tone *= 0.95 + 0.1 * mix(0.5, nC.r, fade);
  vec3 col = mix(uFarMean * (0.96 + 0.08 * nA.b), tone, inMap);
  water = smoothstep(0.35, 0.8, at.r) * inMap;
  // night: the core adds alb x warm x glow x 0.10 x uNight; x 4 here so the built-up plain reads as a lit city [inf]
  glow = 4.0 * (built * inMap + 0.5 * (1.0 - inMap)) * (0.4 + 0.6 * nB.b) * (0.5 + 0.8 * step(0.6, nC.g));
  return col;
}
vec3 shaGroundFarHaze(vec3 col, vec3 wp, float dist, vec3 V, float ext, float night){
  if (uFarHaze.x <= 0.0) return col;
  // signed distance to the detailed extent's edge (far attribute map B over uFarDist = (min, max) m; beyond the map: max).
  // Fix round 1: the ramp starts uFarHazeSig.w m inside the edge (the old data had 0 inside; then uFarDist.x = 0)
  vec2 uv = (wp.xz - uFarRect.xy) / uFarRect.zw; float dS = uFarDist.y;
  if (uHasFar > 0.5 && uv.x > 0.0 && uv.y > 0.0 && uv.x < 1.0 && uv.y < 1.0) dS = mix(uFarDist.x, uFarDist.y, texture(uFarAttr, uv).b);
  // e-folding distance from the surface extinction (fix round 1, L9): clamp(K / sigma, Lmin, Lmax); off (K = 0): uFarHaze.z
  float L = uFarHazeSig.x > 0.0 ? clamp(uFarHazeSig.x / max(uFog.x, 1e-7), uFarHazeSig.y, uFarHazeSig.z) : uFarHaze.z;
  float a = uFarHaze.x * (1.0 - exp(-max(dist - uFarHaze.y, 0.0) / L)) * smoothstep(-uFarHazeSig.w, uFarHaze.w, dS);
  // haze colour: the sky the sky pass draws (the renderer's sky base, set in start()) at the horizon in the view
  // direction; toward the end of the ground mesh (80 km) the direction tends to the actual (below-horizon) view ray, so
  // the mesh edge meets the sky drawn beyond it without a step. Fallback before start(): the env map.
  float w = smoothstep(25000.0, 75000.0, dist); vec3 rd = -V;
  a = max(a, smoothstep(45000.0, 78000.0, dist) * step(0.0, dS));   // the 80 km mesh edge always meets the drawn sky (with a long L)
  vec3 hz = uHasFarSky > 0.5 ? textureLod(uFarSky, dirToEquirect(normalize(vec3(rd.x, mix(0.0, rd.y, w), rd.z))), 0.0).rgb
                             : mix(skyEnv(normalize(vec3(rd.x, 0.02, rd.z)), 3.0), skyEnv(rd, 3.0), w);
  return mix(col, hz, clamp(a, 0.0, 0.99));
}
`;

async function pngTexture(b64) {
  const bin = atob(b64); const u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
  const bmp = await createImageBitmap(new Blob([u], { type: u[0] === 0xff ? 'image/jpeg' : 'image/png' }), { premultiplyAlpha: 'none', colorSpaceConversion: 'none' });
  const t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t);
  gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false); gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL, gl.NONE);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, gl.RGBA, gl.UNSIGNED_BYTE, bmp); gl.generateMipmap(gl.TEXTURE_2D);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  const w = bmp.width, h = bmp.height; if (bmp.close) bmp.close();
  return { tex: t, w, h };
}

async function decodePixels(b64) {   // base64 PNG / JPEG -> {w, h, data (RGBA, sRGB-encoded values as stored)}
  const bin = atob(b64); const u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
  const bmp = await createImageBitmap(new Blob([u], { type: u[0] === 0xff ? 'image/jpeg' : 'image/png' }), { premultiplyAlpha: 'none', colorSpaceConversion: 'none' });
  const w = bmp.width, h = bmp.height;
  const cv = (typeof OffscreenCanvas !== 'undefined') ? new OffscreenCanvas(w, h) : Object.assign(document.createElement('canvas'), { width: w, height: h });
  const cx = cv.getContext('2d', { willReadFrequently: true }); cx.drawImage(bmp, 0, 0);
  const data = cx.getImageData(0, 0, w, h).data; if (bmp.close) bmp.close();
  return { w, h, data };
}
// Edge cross-fade (fix round 1, lead finding: a hard ring at the edge of the detailed extent in view_overview). The core
// mixes the far ground in with a soft extent mask (~+-250 m) but the Sentinel-2 hint (data/sha_ground_s2.js) has a binary
// alpha at the extent polygon, so its 10 m detail stopped dead at half weight. This builds a replacement for the ground
// program's uS2 texture: inside the polygon the hint is cross-faded (in linear reflectance) to the far land-cover colour
// (data/sha_landcover_far.js, the same encoding: 255 srgb(min(1, 2 rho))) over the inner EDGE_COL m; outside the polygon
// (still inside the hint's rectangle) it carries the far land-cover colour only (alpha 1, fading out over the last 150 m
// before the rectangle's edge, where the core's procedural ground takes over). No detail is added beyond the
// extent: outside it the texture holds nothing but the 50 m land-cover colours (PLAN s.6b Q3) [inf: widths].
async function featherS2(S, F) {
  const [a, f] = await Promise.all([decodePixels(S.png), decodePixels(F.png_col)]);
  const W = a.w, H = a.h, res = S.res_m || (S.rect[2] / W);
  // chamfer (3-4) distance in pixels from each valid pixel to the nearest nodata pixel (outside the image = nodata)
  const PW = W + 2, PH = H + 2, D = new Float32Array(PW * PH);
  for (let j = 0; j < PH; j++) for (let i = 0; i < PW; i++) { const ii = i - 1, jj = j - 1; D[j * PW + i] = (ii >= 0 && jj >= 0 && ii < W && jj < H && a.data[(jj * W + ii) * 4 + 3] > 127) ? 1e9 : 0; }
  for (let j = 1; j < PH - 1; j++) for (let i = 1; i < PW - 1; i++) { const k = j * PW + i; if (!D[k]) continue;
    D[k] = Math.min(D[k], D[k - 1] + 3, D[k - PW] + 3, D[k - PW - 1] + 4, D[k - PW + 1] + 4); }
  for (let j = PH - 2; j >= 1; j--) for (let i = PW - 2; i >= 1; i--) { const k = j * PW + i; if (!D[k]) continue;
    D[k] = Math.min(D[k], D[k + 1] + 3, D[k + PW] + 3, D[k + PW + 1] + 4, D[k + PW - 1] + 4); }
  const LIN = new Float32Array(256); for (let v = 0; v < 256; v++) { const c = v / 255; LIN[v] = c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }
  const enc = (l) => { const c = Math.min(1, Math.max(0, l)); return Math.round(255 * (c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055)); };
  const sm = (e0, e1, x) => { const t = Math.min(1, Math.max(0, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t); };
  const out = new Uint8Array(W * H * 4); const fr = F.rect, fres = F.res_m || (fr[2] / f.w);
  let nIn = 0, nFade = 0;
  for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
    const x = S.rect[0] + (i + 0.5) * res, z = S.rect[1] + (j + 0.5) * res;
    // far colour, bilinear on the 50 m cells
    const fx = Math.min(f.w - 1.001, Math.max(0, (x - fr[0]) / fres - 0.5)), fz = Math.min(f.h - 1.001, Math.max(0, (z - fr[1]) / fres - 0.5));
    const i0 = Math.floor(fx), j0 = Math.floor(fz), tx = fx - i0, tz = fz - j0;
    const k = (j * W + i) * 4, dIn = D[(j + 1) * PW + i + 1] / 3 * res, wgt = sm(EDGE_COL[0], EDGE_COL[1], dIn);
    if (dIn > 0) nIn++; if (dIn > 0 && wgt < 1) nFade++;
    for (let c = 0; c < 3; c++) {
      const q = (jj, ii) => LIN[f.data[(jj * f.w + ii) * 4 + c]];
      const lf = (q(j0, i0) * (1 - tx) + q(j0, i0 + 1) * tx) * (1 - tz) + (q(j0 + 1, i0) * (1 - tx) + q(j0 + 1, i0 + 1) * tx) * tz;
      out[k + c] = wgt >= 1 ? a.data[k + c] : enc(lf + (LIN[a.data[k + c]] - lf) * wgt);
    }
    // alpha: 1 inside the polygon; outside it the far colour fades out over the last 150 m before the hint's rectangle
    // ends (the core draws its procedural ground beyond the rectangle: no seam where the polygon nears the rectangle)
    out[k + 3] = dIn > 0 ? 255 : Math.round(255 * sm(0, 150, (Math.min(i, j, W - 1 - i, H - 1 - j) + 0.5) * res));
  }
  return { tex: texture(W, H, { data: out, mips: true }), stats: { px: [W, H], inside: nIn, crossfaded: nFade, widths_m: EDGE_COL, src: 'inf' } };
}

// one renderer item from a Geo built with y above the ground (drawn at GROUND_Y). noFlood (fix round 2, N3): the buildings
// opt out of the objects' apron flood (js/shaders/objects.js sha_obj_flood, wired in js/live/app.js): the light map's spill
// reaches under the piers, so 15 m pier roofs glowed at night (out/fix1/buildings2/n4_night_t2pier.png); facades keep their
// own night terms [inf]
function item(g, G, extra = {}) {
  const d = g.data(); if (!d.idx.length) return null; const b = d.bbox;
  return { mesh: new Mesh(d), prog: 'obj', model: m4.translate(0, G, 0), bbox: [b[0], b[1] + G, b[2], b[3], b[4] + G, b[5]], castShadow: true, uniforms: { uEmissiveBoost: 1 }, noFlood: true, src: 'inf', tris: d.idx.length / 3, ...extra };
}

let stats = null, fillInfo = null;
registerExtension({
  name: 'terminals',
  order: 40,
  shaderChunks: FAR_ON ? { sha_ground_far: FAR_GLSL } : {},
  // airside fill (fix round 1, review H2): the OSM apron ways stop 15-40 m short of the T1 / T2 airside facades, so grass
  // showed under every fixed link, rotunda and VDGS post. data airside_fill (tools/buildings/build_buildings3d.py) =
  // facade-to-apron band inside the aerodrome, minus Sentinel-2 grass pixels, plus fixed-link corridors / rotunda discs;
  // drawn as asphalt ('paved': photo 09 shows a dark asphalt service road there) [src inf]
  // stand-head fill (fix round 2, review_visual_fix1.md R1): with the nose-wheel stop convention (MH 5001-2021 6.2.16-7) the
  // nose, envelope front and equipment areas of the edge stands lay 5-12 m beyond the OSM apron edge, on grass. data
  // stand_head_fill = the stand head rectangles outside the pavement, inside the aerodrome, minus Sentinel-2 grass pixels;
  // drawn as apron ('apron': the same concrete and night flood as the apron it continues) [src inf: OSM apron gap]
  pavement(api) {
    const D = ON ? B3D() : null; if (!D) return;
    const F = D.airside_fill, H = D.stand_head_fill;
    if (F && F.polys) for (const pl of F.polys) api.fill(pl, F.kind || 'paved');
    // (the core map is additive: 'apron' sets G only, so the ring is drawn as 'paved' (R, pavedAt) + 'apron' (G 255), as the
    // core draws its OSM aprons; js/world/ground.js paintAirfieldMap)
    if (H && H.polys) for (const pl of H.polys) { api.fill(pl, 'paved'); if ((H.kind || 'apron') !== 'paved') api.fill(pl, H.kind || 'apron'); }
    fillInfo = { rings: F && F.polys ? F.polys.length : 0, kind: (F && F.kind) || 'paved', src: (F && F.src) || 'inf',
      standHead: H && H.polys ? { rings: H.polys.length, stands: (H.stands || []).length, kind: H.kind || 'apron', src: H.src || 'inf' } : null };
  },
  claimBuildings(airport) {
    if (!ON) return [];
    const D = B3D(); const ids = D ? [...D.claims] : [];
    for (const b of (airport.context && airport.context.buildings) || []) ids.push(b.id);   // context: LOD blocks here
    return ids;
  },
  groundUniforms() {
    if (!FAR_ON) return {};
    const one = texture(1, 1, { data: new Uint8Array([128, 128, 128, 255]) });
    const F = FAR();
    const dr = F && F.attr_b_range_m ? F.attr_b_range_m : [0, 6000];   // old data: B = distance outside only
    return { uFarCol: one, uFarAttr: one, uFarSky: one, uHasFarSky: 0, uFarRect: [0, 0, 1, 1], uHasFar: 0, uFarMean: F ? F.mean_reflectance_rgb.map(v => v * 0.92) : [0.085, 0.082, 0.068], uFarHaze: FAR_HAZE,
      uFarDist: dr, uFarHazeSig: [...FAR_HAZE_SIGMA, dr[0] < 0 ? EDGE_HAZE_IN : 0] };
  },
  async buildWorld(ctx) {
    const G = ctx.groundY; const items = []; const anchors = {}; const info = { src: 'inf (heights B3 / rules; forms from photos)', parts: 0, airsideFill: fillInfo };
    const t0 = performance.now();
    // far ground textures
    const F = FAR();
    if (FAR_ON && F) {
      try {
        const [tc, ta] = await Promise.all([pngTexture(F.png_col), pngTexture(F.png_attr)]);
        Object.assign(ctx.ground.uniforms, { uFarCol: tc, uFarAttr: ta, uFarRect: F.rect, uHasFar: 1 });
        info.far = { rect: F.rect, res_m: F.res_m, px: [F.w, F.h], licence: F.licence };
      } catch (e) { console.warn('[terminals] far land cover not loaded', e); info.far = 'FAILED'; }
      // edge cross-fade of the Sentinel-2 hint (replaces the ground program's uS2 texture; ?far=0 keeps the core's)
      const S = (typeof window !== 'undefined' && window.SHA_GROUND_S2) || null;
      if (info.far !== 'FAILED' && S && ctx.ground.s2 && ctx.ground.uniforms.uHasS2) {
        try { const r = await featherS2(S, F); ctx.ground.uniforms.uS2 = r.tex; info.edge = r.stats; }
        catch (e) { console.warn('[terminals] edge cross-fade not built', e); info.edge = 'FAILED'; }
      }
    } else info.far = FAR_ON ? 'no data/sha_landcover_far.js' : 'off (?far=0)';
    if (!ON) { info.buildings = 'off (?bld=0)'; return { items, anchors, info }; }
    const D = B3D();
    const groups = new Map(); const grp = (k) => { if (!groups.has(k)) groups.set(k, new Geo()); return groups.get(k); };
    if (D) {
      for (const p of D.parts) {
        const k = /^t2_/.test(p.id) ? 'T2' : /^t1_/.test(p.id) ? 'T1' : p.context ? 'hub' : 'airport';
        buildPart(grp(k), p); info.parts++;
      }
      for (const h of D.hangars) buildHangar(grp('hangars'), h);
      for (const t of D.towers) {
        if (t.form === 'control') {
          const T = buildControlTower(t);
          const b = T.geo.bbox; const it = { mesh: new Mesh(T.geo), prog: 'obj', model: m4.translate(t.x, G, t.z), bbox: [b[0] + t.x, b[1] + G, b[2] + t.z, b[3] + t.x, b[4] + G, b[5] + t.z], castShadow: true, uniforms: { uEmissiveBoost: 1 }, noFlood: true, src: 'inf', what: 'east control tower' };
          items.push(it);
          // cabHalf (P2f): the cab's half-width at eye height (glazing leans out from cab_w0 to cab_w1), so the app's Tower view
          // can stand the eye near the glass instead of at the cab centre (the console band filled ~40 % of the frame)
          const dm = t.dims || {}; const cabHalf = dm.cab_w0 && dm.cab_w1 && dm.head_y1 && dm.cab_y1 ? 0.5 * (dm.cab_w0 + (dm.cab_w1 - dm.cab_w0) * Math.min(1, 1.6 / (dm.cab_y1 - dm.head_y1))) : null;
          anchors.tower = { pos: [t.x, G, t.z], eyeY: G + T.eye, top: G + T.top, cabHalf, cabYaw: t.yaw_deg != null ? +t.yaw_deg : null, src: 'height AIP (mirror); form inf (photo 02)' };
        } else buildBlockTower(grp('airport'), t);
      }
      info.hangars = D.hangars.length; info.towers = D.towers.length;
    }
    // context LOD blocks (all context buildings except the hub parts built above)
    const skip = new Set(D ? D.claims : []); const ctxB = (ctx.airport.context && ctx.airport.context.buildings) || [];
    const quad = (b) => { const r = b.ring; let x = 0, z = 0; for (const p of r) { x += p[0]; z += p[1]; } x /= r.length; z /= r.length; return 'ctx' + (x < -200 ? 'W' : 'E') + (z < 150 ? 'N' : 'S'); };
    const byQ = new Map(); for (const b of ctxB) { const k = quad(b); if (!byQ.has(k)) byQ.set(k, []); byQ.get(k).push(b); }
    info.context = 0; for (const [k, list] of byQ) info.context += buildContextBlocks(grp(k), list, skip);
    // canal / river bank kerbs (the water surface itself is the core ground shader's)
    if (ctx.airport.context) { const gw = new Geo(); info.bankKerbM = buildWaterEdges(gw, ctx.airport.context); const it = item(gw, G, { what: 'banks', castShadow: false }); if (it) items.push(it); }
    for (const [k, g] of groups) { const it = item(g, G, { what: k, placeholder: null }); if (it) items.push(it); }
    info.items = items.length; info.tris = items.reduce((s, it) => s + (it.tris || it.mesh.count / 3 || 0), 0);
    info.ms = Math.round(performance.now() - t0);
    stats = info;
    ctx.log('terminals ' + JSON.stringify(info));
    return { items, anchors, info };
  },
  start(app) {
    // the far haze takes its colour from the renderer's sky base (what the sky pass draws); it exists once applyEnv ran
    try { if (FAR_ON && app.R.skyBase && app.world.groundU) Object.assign(app.world.groundU, { uFarSky: app.R.skyBase.tex[0], uHasFarSky: 1 }); } catch (e) { console.warn('[terminals] far sky', e); }
    // credits: ESA WorldCover (CC BY 4.0) for the far ground; the building sources in the About panel (the UI package may
    // take buildingsCredits() into js/live/about.js instead; this only appends when the texts are not there yet)
    try {
      const C = buildingsCredits();
      if (C.attrib && app.ui.el.attrib && !app.ui.el.attrib.innerHTML.includes('WorldCover')) app.ui.el.attrib.innerHTML += ' · ' + C.attrib;
      if (app.ui.el.about && !app.ui.el.about.innerHTML.includes('Buildings and surroundings')) app.ui.el.about.insertAdjacentHTML('beforeend', C.about);
    } catch (e) { console.warn('[terminals] credits', e); }
  },
});
/** About-panel section and credit-line text of this package (for js/live/about.js) */
export function buildingsCredits() {
  const far = FAR_ON && !!FAR();
  return {
    attrib: far ? 'ESA WorldCover 2021 (CC BY 4.0)' : '',
    about: `
<h4>Buildings and surroundings</h4>
<p>Building outlines from OpenStreetMap (observed). Terminal T1 / T2 volumes, piers, heights, facades and roof forms, the
control-tower form, hangar doors and roofs, and the context blocks are <b>inferred</b>: heights from our measurements
(Copernicus DEM, Umbra SAR layover, photo ratios) or rules; forms from open-licence Wikimedia Commons photos (proportions
only).${far ? ` Beyond the detailed area the ground shows land-cover classes only (no buildings, no roads): © ESA WorldCover
project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium,
<a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener">CC BY 4.0</a>, resampled to 50 m.` : ''}</p>`,
  };
}
export function terminalsInfo() { return stats; }
