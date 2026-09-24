import { gl, Mesh, texture, Program, fullscreen } from '../gl.js';
import { FS_VERT } from '../shaders/common.js';
import { Terrain, REGION } from './terrain.js';
import { RWY, APT_RECT, computeGates, paintAirportMap, buildMarkingRibbons } from './airfield.js';
import { V, U, AIRPORT_LAND_ST } from '../geo.js';
import { makeGlyphAtlas, glyphCode, makeWaveTexture, makeCloudTexture, makeNoiseTexture } from './textures.js';
import { GROUND_VS, GROUND_FS, BAKE_APT_FS, BAKE_AUX_FS, BAKE_CITY_FS, BAKE_CITYFAR_FS } from '../shaders/ground.js';
import { WATER_VS, WATER_FS, DECAL_VS, DECAL_FS } from '../shaders/env.js';
import { OBJ_VS, OBJ_FS } from '../shaders/objects.js';
import { buildBuildings } from './buildings.js';

export function buildBaseWorld(R, log = console.log) {
  let t0 = performance.now();
  const terrain = new Terrain(); log('terrain maps ' + (performance.now() - t0).toFixed(0) + 'ms'); t0 = performance.now();
  const chunks = terrain.buildMeshes(); log('terrain mesh ' + chunks.length + ' chunks ' + (performance.now() - t0).toFixed(0) + 'ms'); t0 = performance.now();
  const regionTex = texture(REGION.res, REGION.res, { data: terrain.regionRGBA, mips: true, aniso: 8 });
  const gates = computeGates(); log('gates ' + gates.length);
  const apt = paintAirportMap(gates); const aptTex = texture(apt.w, apt.h, { data: apt.data, mips: true, aniso: 8 });
  log('airport map ' + apt.w + 'x' + apt.h + ' ' + (performance.now() - t0).toFixed(0) + 'ms');
  const glyphs = makeGlyphAtlas();
  const waves = makeWaveTexture(0.3);
  const clouds = makeCloudTexture(11);
  const noise = makeNoiseTexture();
  const Vw = [V[0], -V[1]], Uw = [U[0], -U[1]];
  const rw = [], rwInfo = [];
  RWY.forEach(r => { rw.push(r.axis, r.c, r.a0, r.a1); rwInfo.push(r.disp0, r.disp1, glyphCode(r.name[0]), glyphCode(r.name[1])); });

  R.addProgram('ground', GROUND_VS, GROUND_FS);
  R.addProgram('water', WATER_VS, WATER_FS);
  R.addProgram('decal', DECAL_VS, DECAL_FS);
  R.addProgram('obj', OBJ_VS, OBJ_FS);
  R.addProgram('objI', OBJ_VS, OBJ_FS, { INSTANCED: 1 });
  const groundU = {
    uRegion: regionTex, uRegionRect: [REGION.x0, REGION.z0, REGION.size, REGION.size],
    uAptRect: [APT_RECT.s0, APT_RECT.t0, APT_RECT.w, APT_RECT.h], uVw: Vw, uUw: Uw,
    uGlyphs: glyphs, uRw: rw, uRwInfo: rwInfo, uCityRect: CITY_RECT, uCityFarRect: CITYFAR_RECT,
  };
  const items = [];
  for (const c of chunks) {
    const m = new Mesh({ pos: c.pos, nrm: c.nrm, idx: c.idx });
    items.push({ mesh: m, prog: 'ground', uniforms: groundU, bbox: c.bbox, castShadow: false });
  }
  // water: nonuniform grid
  const coords = []; { let x = 0, s = 20; coords.push(0); while (x < 70000) { x += s; s *= 1.08; coords.push(x); coords.unshift(-x); } }
  const n = coords.length; const wpos = new Float32Array(n * n * 3); const widx = [];
  for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) { const k = (j * n + i) * 3; wpos[k] = coords[i]; wpos[k + 1] = 0; wpos[k + 2] = coords[j]; }
  for (let j = 0; j < n - 1; j++) for (let i = 0; i < n - 1; i++) { const a = j * n + i; widx.push(a, a + n, a + n + 1, a, a + n + 1, a + 1); }
  // chunk the water too for culling
  const waterMesh = new Mesh({ pos: wpos, idx: new Uint32Array(widx) });
  const aptPoly = AIRPORT_LAND_ST.flat();
  const waterU = { uWaves: waves, uWind: [3, -1], uWaveAmp: 1.0, uAptRect: groundU.uAptRect, uVw: Vw, uUw: Uw };
  items.push({ mesh: waterMesh, prog: 'water', uniforms: waterU, bbox: [-70000, -1, -70000, 70000, 1, 70000], castShadow: false, water: true });
  // markings
  const rib = buildMarkingRibbons(gates);
  const ribMesh = new Mesh({ pos: rib.pos, col: rib.col, idx: rib.idx });
  items.push({ mesh: ribMesh, prog: 'decal', bbox: [-4000, 0, -4000, 4000, 10, 4000], castShadow: false, polyOffset: [-2, -4], nearOnly: true });
  t0 = performance.now();
  const bd = buildBuildings(); const bMesh = new Mesh(bd);
  const I4 = new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]);
  items.push({ mesh: bMesh, prog: 'obj', model: I4, bbox: bd.bbox, castShadow: true, uniforms: { uEmissiveBoost: 1 } });
  log('buildings ' + (bd.idx.length / 3) + ' tris ' + (performance.now() - t0).toFixed(0) + 'ms');
  return { terrain, items, gates, textures: { regionTex, aptTex, glyphs, waves, clouds, noise }, groundU, waterU, aptPoly };
}

export const CITY_RECT = [-8400, -4300, 8400, 8400]; // x0, z0, w, h (world)
export const CITYFAR_RECT = [-32000, -32000, 64000, 64000];

function target(w, h, mips = true) {
  const t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t);
  const levels = mips ? Math.floor(Math.log2(Math.max(w, h))) + 1 : 1;
  gl.texStorage2D(gl.TEXTURE_2D, levels, gl.RGBA8, w, h);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, mips ? gl.LINEAR_MIPMAP_LINEAR : gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  const e = gl.getExtension('EXT_texture_filter_anisotropic'); if (e) gl.texParameterf(gl.TEXTURE_2D, e.TEXTURE_MAX_ANISOTROPY_EXT, (window.ANISO||1));
  const fb = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, fb); gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, t, 0);
  gl.drawBuffers([gl.COLOR_ATTACHMENT0]);
  return { tex: t, fb, w, h, mips };
}
function runBake(R, tgt, prog, uniforms) {
  gl.bindFramebuffer(gl.FRAMEBUFFER, tgt.fb); gl.viewport(0, 0, tgt.w, tgt.h);
  gl.disable(gl.DEPTH_TEST); gl.disable(gl.BLEND); gl.disable(gl.CULL_FACE);
  prog.use(); R.setLightUniforms(prog, R.env); prog.setAll(uniforms);
  // tile the bake to keep individual draws short
  const T = 1024; gl.enable(gl.SCISSOR_TEST);
  for (let y = 0; y < tgt.h; y += T) for (let x = 0; x < tgt.w; x += T) { gl.scissor(x, y, T, T); fullscreen(); }
  gl.disable(gl.SCISSOR_TEST);
  if (tgt.mips) { gl.bindTexture(gl.TEXTURE_2D, tgt.tex); gl.generateMipmap(gl.TEXTURE_2D); }
}
export function bakeGround(R, world, log = console.log, opts = {}) {
  let t0 = performance.now();
  const W = world; const A = [APT_RECT.s0, APT_RECT.t0, APT_RECT.w, APT_RECT.h];
  const res = opts.aptRes || 0.8; const aw = Math.round(APT_RECT.w / res), ah = Math.round(APT_RECT.h / res);
  const cityN = opts.cityRes || 4096, auxRes = opts.auxRes || 2;
  const first = !W.bakes;
  if (!W.bakes) {
    W.bakes = { apt: target(aw, ah), aux: target(Math.round(APT_RECT.w / auxRes), Math.round(APT_RECT.h / auxRes)), city: target(cityN, cityN), cityFar: target(cityN, cityN) };
    W.bakeProgs = { apt: new Program(FS_VERT, BAKE_APT_FS), aux: new Program(FS_VERT, BAKE_AUX_FS), city: new Program(FS_VERT, BAKE_CITY_FS), cityFar: new Program(FS_VERT, BAKE_CITYFAR_FS) };
  }
  const B = W.bakes, P = W.bakeProgs;
  // the airfield bakes do not depend on the sun: bake once (then the large source map can be released)
  if (first || !opts.sunOnly) {
    runBake(R, B.apt, P.apt, { uApt: W.textures.aptTex, uPaint: W.textures.paintTex || W.textures.aptTex, uHasPaint: W.textures.paintTex ? 1 : 0, uAptRect: A, uAptPoly: W.aptPoly, uTexel: res, uGlyphs: W.textures.glyphs, uRw: W.groundU.uRw, uRwInfo: W.groundU.uRwInfo });
    runBake(R, B.aux, P.aux, { uAptRect: A, uAptPoly: W.aptPoly, uApt: W.textures.aptTex });
  }
  runBake(R, B.city, P.city, { uCityRect: CITY_RECT, uRegion: W.textures.regionTex, uRegionRect: W.groundU.uRegionRect, uTexel: CITY_RECT[2] / cityN, uGlyphs: W.textures.glyphs, uRw: W.groundU.uRw, uRwInfo: W.groundU.uRwInfo });
  runBake(R, B.cityFar, P.cityFar, { uCityRect: CITYFAR_RECT, uRegion: W.textures.regionTex, uRegionRect: W.groundU.uRegionRect, uTexel: CITYFAR_RECT[2] / cityN, uGlyphs: W.textures.glyphs, uRw: W.groundU.uRw, uRwInfo: W.groundU.uRwInfo });
  gl.finish();
  W.groundU.uCityFar = B.cityFar;
  W.groundU.uAptAlb = B.apt; W.groundU.uAptAux = B.aux; W.groundU.uCity = B.city;
  W.waterU.uAptAux = B.aux;
  log('bakes ' + (performance.now() - t0).toFixed(0) + 'ms');
}
