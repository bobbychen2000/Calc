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
// the haze law [inf]: strength, start distance from the camera (m), e-folding distance (m), ramp width outside the
// detailed extent (m; the far attribute map's B channel holds the distance outside the extent)
const FAR_HAZE = [1.0, 2500, 14000, 4000];

const FAR_GLSL = `
// sha_ground_far (js/live/terminals.js, package P2d): ESA WorldCover 2021 class colours beyond the detailed extent, with a
// procedural roof-tone pattern on built-up cells (no buildings, no roads: PLAN s.6b Q3), sky-reflecting water and a night
// urban glow; beyond the 20 km land-cover crop, the crop's mean colour; a distance haze toward the horizon sky colour that
// ramps in over 4 km outside the extent (so the extent edge shows no step; rendering law [inf]).
uniform sampler2D uFarCol; uniform sampler2D uFarAttr; uniform vec4 uFarRect; uniform float uHasFar; uniform vec3 uFarMean;
uniform vec4 uFarHaze; uniform sampler2D uFarSky; uniform float uHasFarSky;
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
  // ramp with the distance outside the detailed extent (far attribute map B: 0 inside .. 1 at 6 km; 1 beyond the map)
  vec2 uv = (wp.xz - uFarRect.xy) / uFarRect.zw; float dOut = 6000.0;
  if (uHasFar > 0.5 && uv.x > 0.0 && uv.y > 0.0 && uv.x < 1.0 && uv.y < 1.0) dOut = texture(uFarAttr, uv).b * 6000.0;
  float a = uFarHaze.x * (1.0 - exp(-max(dist - uFarHaze.y, 0.0) / uFarHaze.z)) * smoothstep(0.0, uFarHaze.w, dOut) * (1.0 - ext);
  // haze colour: the sky the sky pass draws (the renderer's sky base, set in start()) at the horizon in the view
  // direction; toward the end of the ground mesh (80 km) the direction tends to the actual (below-horizon) view ray, so
  // the mesh edge meets the sky drawn beyond it without a step. Fallback before start(): the env map.
  float w = smoothstep(25000.0, 75000.0, dist); vec3 rd = -V;
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

// one renderer item from a Geo built with y above the ground (drawn at GROUND_Y)
function item(g, G, extra = {}) {
  const d = g.data(); if (!d.idx.length) return null; const b = d.bbox;
  return { mesh: new Mesh(d), prog: 'obj', model: m4.translate(0, G, 0), bbox: [b[0], b[1] + G, b[2], b[3], b[4] + G, b[5]], castShadow: true, uniforms: { uEmissiveBoost: 1 }, src: 'inf', tris: d.idx.length / 3, ...extra };
}

let stats = null;
registerExtension({
  name: 'terminals',
  order: 40,
  shaderChunks: FAR_ON ? { sha_ground_far: FAR_GLSL } : {},
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
    return { uFarCol: one, uFarAttr: one, uFarSky: one, uHasFarSky: 0, uFarRect: [0, 0, 1, 1], uHasFar: 0, uFarMean: F ? F.mean_reflectance_rgb.map(v => v * 0.92) : [0.085, 0.082, 0.068], uFarHaze: FAR_HAZE };
  },
  async buildWorld(ctx) {
    const G = ctx.groundY; const items = []; const anchors = {}; const info = { src: 'inf (heights B3 / rules; forms from photos)', parts: 0 };
    const t0 = performance.now();
    // far ground textures
    const F = FAR();
    if (FAR_ON && F) {
      try {
        const [tc, ta] = await Promise.all([pngTexture(F.png_col), pngTexture(F.png_attr)]);
        Object.assign(ctx.ground.uniforms, { uFarCol: tc, uFarAttr: ta, uFarRect: F.rect, uHasFar: 1 });
        info.far = { rect: F.rect, res_m: F.res_m, px: [F.w, F.h], licence: F.licence };
      } catch (e) { console.warn('[terminals] far land cover not loaded', e); info.far = 'FAILED'; }
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
          const b = T.geo.bbox; const it = { mesh: new Mesh(T.geo), prog: 'obj', model: m4.translate(t.x, G, t.z), bbox: [b[0] + t.x, b[1] + G, b[2] + t.z, b[3] + t.x, b[4] + G, b[5] + t.z], castShadow: true, uniforms: { uEmissiveBoost: 1 }, src: 'inf', what: 'east control tower' };
          items.push(it);
          // cabHalf (P2f): the cab's half-width at eye height (glazing leans out from cab_w0 to cab_w1), so the app's Tower view
          // can stand the eye near the glass instead of at the cab centre (the console band filled ~40 % of the frame)
          const dm = t.dims || {}; const cabHalf = dm.cab_w0 && dm.cab_w1 && dm.head_y1 && dm.cab_y1 ? 0.5 * (dm.cab_w0 + (dm.cab_w1 - dm.cab_w0) * Math.min(1, 1.6 / (dm.cab_y1 - dm.head_y1))) : null;
          anchors.tower = { pos: [t.x, G, t.z], eyeY: G + T.eye, top: G + T.top, cabHalf, src: 'height AIP (mirror); form inf (photo 02)' };
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
