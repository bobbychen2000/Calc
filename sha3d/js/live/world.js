// World assembly for SHA Live 3D (adapted from sfo3d@e3218d6 js/live/world.js: the role is the same - one call builds the
// static scene - but every input is the injected ZSSS data and the airport-specific builders are extensions).
// Order: (1) extension shader chunks; (2) programs; (3) ground (airfield + context maps, Sentinel-2 hint, flat mesh);
// (4) placeholder buildings + tower stand-in (minus the ids extensions claim); (5) each extension's buildWorld.
// No SFO data, no FAA geometry: markings, signs, lights, stands and terminals all come from the extensions
// (js/live/ext.js).
import { defineChunk } from '../gl.js';
import { Mesh } from '../gl.js';
import * as GEO from '../geo.js';
import { GROUND_VS, GROUND_FS } from '../shaders/ground.js';
import { OBJ_VS, OBJ_FS } from '../shaders/objects.js';
import { makeWaveTexture, makeCloudTexture, makeNoiseTexture } from '../world/textures.js';
import { buildGround } from '../world/ground.js';
import { buildPlaceholderBuildings, buildTowerPlaceholder } from '../world/placeholders.js';
import { extensions } from './ext.js';

const I4 = () => new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]);
const centroid = (r) => { let x = 0, z = 0; for (const p of r) { x += p[0]; z += p[1]; } return [x / r.length, z / r.length]; };

// data: {airport, stands, taxigraph, s2}; opts: {mapRes, ctxRes, quality, log}
export async function buildLiveWorld(R, data, opts = {}) {
  const log = opts.log || (() => { });
  const airport = data.airport; const exts = extensions();
  const geoInit = GEO.initGeo(airport);
  if (!geoInit.ok) log('frame check: ' + geoInit.diffs.join('; '));
  // (1) shader chunk overrides
  for (const e of exts) for (const [k, src] of Object.entries(e.shaderChunks || {})) defineChunk(k, src);
  // (2) programs
  R.addProgram('ground', GROUND_VS, GROUND_FS);
  R.addProgram('obj', OBJ_VS, OBJ_FS);
  R.addProgram('objI', OBJ_VS, OBJ_FS, { INSTANCED: 1 });
  const textures = { waves: makeWaveTexture(0.3), clouds: makeCloudTexture(11), noise: makeNoiseTexture() };
  const items = []; const sprites = []; const info = { extensions: exts.map(e => e.name) };
  // (3) ground
  const ground = await buildGround(R, airport, { mapRes: opts.mapRes || 1.0, ctxRes: opts.ctxRes || 4.0, exts, s2: data.s2 });
  items.push(...ground.items); info.ground = ground.info; log('ground ' + JSON.stringify(ground.info));
  // (4) placeholders
  const claimed = new Set();
  for (const e of exts) if (e.claimBuildings) { try { for (const id of e.claimBuildings(airport) || []) claimed.add(id); } catch (err) { console.warn('[world] claimBuildings ' + e.name, err); } }
  const B = buildPlaceholderBuildings([...(airport.buildings || []), ...((airport.context && airport.context.buildings) || [])], { skip: claimed });
  if (B.geo.idx.length) items.push({ mesh: new Mesh(B.geo), prog: 'obj', model: I4(), bbox: B.geo.bbox, castShadow: true, uniforms: { uEmissiveBoost: 1 }, placeholder: 'buildings', src: 'inf' });
  info.buildings = { placeholders: B.count, claimedByExtensions: B.skipped };
  const anchors = {};
  const T = airport.control_tower;
  if (T) {
    anchors.tower = { pos: [T.x, GEO.GROUND_Y, T.z], eyeY: GEO.GROUND_Y + (T.height_m || 44.5) - 4, top: GEO.GROUND_Y + (T.height_m || 44.5), src: T.height_src || 'inf' };
    if (!claimed.has('tower')) { const tw = buildTowerPlaceholder(T); items.push({ mesh: new Mesh(tw.geo), prog: 'obj', model: I4(), bbox: tw.geo.bbox, castShadow: true, uniforms: { uEmissiveBoost: 1 }, placeholder: 'tower', src: 'inf' }); anchors.tower.eyeY = tw.eyeY; }
  }
  for (const b of airport.buildings || []) {
    const nm = (b.name_en || '') + ' ' + (b.name || '');   // OSM name / name:en
    if (b.kind === 'terminal' && /Terminal 1\b|T1\b|1号航站楼/.test(nm)) anchors.t1 = { pos: [...centroid(b.ring)], id: b.id };
    if (b.kind === 'terminal' && /Terminal 2\b|T2\b|2号航站楼/.test(nm)) anchors.t2 = { pos: [...centroid(b.ring)], id: b.id };
  }
  // (5) extensions
  const world = { items, sprites, textures, ground, anchors, gates: [], info, airport, stands: data.stands || null, taxigraph: data.taxigraph || null, pavedAt: ground.pavedAt, groundU: ground.uniforms };
  const ctx = { R, airport, stands: data.stands || null, taxigraph: data.taxigraph || null, geo: GEO, groundY: GEO.GROUND_Y, quality: opts.quality || null, ground, textures, log, addItems: (a) => items.push(...a) };
  for (const e of exts) {
    if (e.groundUniforms) { try { Object.assign(ground.uniforms, e.groundUniforms(ctx) || {}); } catch (err) { console.warn('[world] groundUniforms ' + e.name, err); } }
    if (!e.buildWorld) continue;
    try {
      const r = await e.buildWorld(ctx) || {};
      if (r.items) items.push(...r.items); if (r.sprites) sprites.push(...r.sprites); if (r.gates) world.gates.push(...r.gates);
      if (r.anchors) Object.assign(anchors, r.anchors); info[e.name] = r.info || 'ok';
    } catch (err) { console.error('[world] extension ' + e.name + ' failed', err); info[e.name] = 'FAILED: ' + (err && err.message); }
  }
  return world;
}
