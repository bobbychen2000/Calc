// World assembly for SFO Live: terrain, water and city from the base world; airport layout from real data.
import { gl, Mesh, texture } from '../gl.js';
import { Terrain, REGION } from '../world/terrain.js';
import { RWY, APT_RECT } from '../world/airfield.js';
import { V, U, AIRPORT_LAND_ST, stToWorld, GROUND_Y } from '../geo.js';
import { makeGlyphAtlas, glyphCode, makeWaveTexture, makeCloudTexture, makeNoiseTexture } from '../world/textures.js';
import { GROUND_VS, GROUND_FS } from '../shaders/ground.js';
import { WATER_VS, WATER_FS, DECAL_VS, DECAL_FS } from '../shaders/env.js';
import { OBJ_VS, OBJ_FS } from '../shaders/objects.js';
import { CITY_RECT, CITYFAR_RECT } from '../world/world.js';
import { liveGates, standGates, buildLiveBuildings, paintAirportMapReal, buildStandMarkings, inStandEnvelope, endZoneRects, rwEndUniform, END_ZONES, EMAS_SETBACK, EMAS_W } from './airport.js';
import { Geo } from '../geom.js';
import { v3 } from '../math.js';
import { RWY_W } from '../world/airfield.js';
import { MARK_VS, MARK_FS, buildMarkings, buildStandMarks } from './markings.js';
import { SIGN_VS, SIGN_FS, buildSigns } from './signs.js';
import { buildMasts } from './items.js';

// world pose of a stand (nose point, unit heading vector) from its airport-grid description
function gateWorld(g) {
  const n = stToWorld(g.nose[0], g.nose[1], 0), o = stToWorld(0, 0, 0), d = stToWorld(g.dir[0], g.dir[1], 0);
  const dx = d[0] - o[0], dz = d[2] - o[2], l = Math.hypot(dx, dz);
  return { x: n[0], z: n[2], dx: dx / l, dz: dz / l };
}
// opts: { terrainStep, mapRes, details, runways }
export function buildLiveWorld(R, airport, log = console.log, opts = {}) {
  const details = opts.details || null;
  let t0 = performance.now();
  const terrain = new Terrain(); log('terrain maps ' + (performance.now() - t0).toFixed(0) + 'ms'); t0 = performance.now();
  const chunks = terrain.buildMeshes([0, 0], opts.terrainStep || 15); log('terrain mesh ' + chunks.length + ' chunks ' + (performance.now() - t0).toFixed(0) + 'ms'); t0 = performance.now();
  const regionTex = texture(REGION.res, REGION.res, { data: terrain.regionRGBA, mips: true, aniso: 8 });
  terrain.regionRGBA = null;
  const gates = opts.stands ? standGates(opts.stands) : liveGates(airport); log((opts.stands ? 'surveyed stands ' : 'gates ') + gates.length);
  const apt = paintAirportMapReal(airport, gates, opts.mapRes || APT_RECT.res, details, { paint: opts.paint || null, pavement: opts.pavement || null, endZones: endZoneRects() }); const aptTex = texture(apt.w, apt.h, { data: apt.data, mips: true, aniso: 8 });
  const paintTex = apt.paint ? texture(apt.w, apt.h, { data: apt.paint, mips: true }) : null;
  log('airport map ' + apt.w + 'x' + apt.h + ' ' + (performance.now() - t0).toFixed(0) + 'ms'); t0 = performance.now();
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
  R.addProgram('mark', MARK_VS, MARK_FS);
  R.addProgram('sign', SIGN_VS, SIGN_FS);
  const groundU = {
    uRegion: regionTex, uRegionRect: [REGION.x0, REGION.z0, REGION.size, REGION.size],
    uAptRect: [APT_RECT.s0, APT_RECT.t0, APT_RECT.w, APT_RECT.h], uVw: Vw, uUw: Uw,
    uGlyphs: glyphs, uRw: rw, uRwInfo: rwInfo, uRwEnd: rwEndUniform(), uCityRect: CITY_RECT, uCityFarRect: CITYFAR_RECT,
  };
  const items = [];
  for (const c of chunks) items.push({ mesh: new Mesh({ pos: c.pos, nrm: c.nrm, idx: c.idx }), prog: 'ground', uniforms: groundU, bbox: c.bbox, castShadow: false });
  const coords = []; { let x = 0, s = 20; coords.push(0); while (x < 70000) { x += s; s *= 1.08; coords.push(x); coords.unshift(-x); } }
  const n = coords.length; const wpos = new Float32Array(n * n * 3); const widx = [];
  for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) { const k = (j * n + i) * 3; wpos[k] = coords[i]; wpos[k + 1] = 0; wpos[k + 2] = coords[j]; }
  for (let j = 0; j < n - 1; j++) for (let i = 0; i < n - 1; i++) { const a = j * n + i; widx.push(a, a + n, a + n + 1, a, a + n + 1, a + 1); }
  const waterMesh = new Mesh({ pos: wpos, idx: new Uint32Array(widx) });
  const aptPoly = AIRPORT_LAND_ST.flat();
  const waterU = { uWaves: waves, uWind: [3, -1], uWaveAmp: 1.0, uAptRect: groundU.uAptRect, uVw: Vw, uUw: Uw };
  items.push({ mesh: waterMesh, prog: 'water', uniforms: waterU, bbox: [-70000, -1, -70000, 70000, 1, 70000], castShadow: false, water: true });
  const mk = opts.standMarkings ? buildStandMarkings(gates) : { idx: [] }; // stand centrelines are not in the source data: off by default
  if (mk.idx.length) items.push({ mesh: new Mesh({ pos: mk.pos, col: mk.col, idx: mk.idx }), prog: 'decal', bbox: [-4000, 0, -4000, 4000, 10, 4000], castShadow: false, polyOffset: [-2, -4], nearOnly: true });
  if (details) {
    const mm = buildMarkings(details);
    if (mm) items.push({ mesh: mm, prog: 'mark', blend: 'alpha', bothPasses: true, noCull: true, sortKey: () => 1e12, bbox: [-3000, 0, -2600, 2200, 10, 2000], castShadow: false, polyOffset: [-2, -6],
      uniforms: () => ({ uPxScale: 2 * Math.tan((R.curCam ? R.curCam.fov : 0.9) / 2) / R.H }) });
    if (opts.stands) {
      const gw = [V[0], -V[1]]; // airport grid direction (world x,z) for the red boxes
      const sm = buildStandMarks(gates.map(g => ({ ...g, w: gateWorld(g) })), opts.stands.redBoxes || [], gw);
      if (sm) items.push({ mesh: sm, prog: 'mark', blend: 'alpha', bothPasses: true, noCull: true, sortKey: () => 1e12, bbox: [-3000, 0, -2600, 2200, 10, 2000], castShadow: false, polyOffset: [-2, -6], nearOnly: true,
        uniforms: () => ({ uPxScale: 2 * Math.tan((R.curCam ? R.curCam.fov : 0.9) / 2) / R.H }) });
    }
    const S = buildSigns(details, opts.runways || []);
    items.push({ mesh: S.mesh, prog: 'sign', bbox: [-3000, 0, -2600, 2200, 10, 2000], castShadow: true, shadowMaxCascade: 1, nearOnly: true, noCull: true, uniforms: { uAtlas: S.atlas } });
    items.push({ mesh: S.painted, prog: 'sign', bbox: [-3000, 0, -2600, 2200, 10, 2000], castShadow: false, polyOffset: [-2, -5], nearOnly: true, noCull: true, uniforms: { uAtlas: S.atlas } });
    // floodlight masts (positions inferred, not surveyed): never inside a stand's aircraft envelope
    const masts = (details.masts || []).filter(([x, z]) => !inStandEnvelope(gates, x, z, 4));
    if (masts.length !== (details.masts || []).length) log('masts inside stand envelopes removed: ' + ((details.masts || []).length - masts.length));
    const M = buildMasts(masts);
    const I4m = new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]);
    items.push({ mesh: new Mesh(M.geo), prog: 'obj', model: I4m, bbox: M.geo.bbox, castShadow: true, uniforms: { uEmissiveBoost: 1 } });
    opts._mastSprites = M.sprites;
    log('markings, ' + S.count + ' hold positions, ' + masts.length + ' masts');
  }
  // EMAS beds (engineered materials arresting systems) at the 1L/1R/19L/19R ends: raised cellular-block beds
  { const E = buildEMAS().data(); items.push({ mesh: new Mesh(E), prog: 'obj', model: new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]), bbox: E.bbox, castShadow: true, uniforms: { uEmissiveBoost: 1 } }); }
  const B = buildLiveBuildings(airport, opts.buildings || null);
  const I4 = new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]);
  items.push({ mesh: new Mesh(B.geo), prog: 'obj', model: I4, bbox: B.geo.bbox, castShadow: true, uniforms: { uEmissiveBoost: 1 } });
  log('buildings ' + (B.geo.idx.length / 3) + ' tris ' + (performance.now() - t0).toFixed(0) + 'ms');
  return { terrain, items, gates, towerPos: B.towerPos, textures: { regionTex, aptTex, paintTex, glyphs, waves, clouds, noise }, groundU, waterU, aptPoly, paved: apt.paved, details, mastSprites: opts._mastSprites || [] };
}
// the airfield source map is only needed for the one-time airfield bake
export function releaseAirportMap(world) { for (const k of ['aptTex', 'paintTex']) { const t = world.textures[k]; if (t && t.tex) { gl.deleteTexture(t.tex); world.textures[k] = null; } } }
// EMAS bed geometry: height rising from 0.25 m at the entry to 0.6 m at the far end, light grey block surface with
// yellow chevrons (apex towards the runway)
function buildEMAS() {
  const g = new Geo(); const Y = GROUND_Y;
  const BED = [0.66, 0.65, 0.62, 1], BEDE = [0.92, 0, 0, 0], YEL = [0.8, 0.58, 0.08, 1], YELE = [0.7, 0, 0, 0];
  const face = (pts, want, c, e) => { const n = v3.cross(v3.sub(pts[1], pts[0]), v3.sub(pts[3], pts[0])); if (v3.dot(n, want) < 0) pts = [pts[0], pts[3], pts[2], pts[1]]; g.quad(pts[0], pts[1], pts[2], pts[3], c, e); };
  for (const z of END_ZONES) {
    if (z.type !== 2) continue;
    const r = RWY[z.rw]; const sgn = z.end === 0 ? -1 : 1; const uE = (z.end === 0 ? r.a0 : r.a1) + sgn * EMAS_SETBACK; const L = z.len; const hw = EMAS_W / 2;
    // local (u' along the bed from the entry, v lateral) -> world
    const W3 = (up, v, h) => { const u = uE + sgn * up; const st = r.axis === 0 ? [u, r.c + v] : [r.c + v, u]; const w = stToWorld(st[0], st[1], Y + h); return w; };
    const H = (up) => 0.25 + 0.35 * up / L;
    const along = v3.norm(v3.sub(W3(1, 0, 0), W3(0, 0, 0))); const side = v3.norm(v3.sub(W3(0, 1, 0), W3(0, 0, 0)));
    face([W3(0, -hw, H(0)), W3(L, -hw, H(L)), W3(L, hw, H(L)), W3(0, hw, H(0))], [0, 1, 0], BED, BEDE);                 // top
    face([W3(0, -hw, 0), W3(0, hw, 0), W3(0, hw, H(0)), W3(0, -hw, H(0))], v3.mul(along, -1), BED, BEDE);             // entry face
    face([W3(L, -hw, 0), W3(L, hw, 0), W3(L, hw, H(L)), W3(L, -hw, H(L))], along, BED, BEDE);                          // far face
    for (const sv of [-1, 1]) face([W3(0, sv * hw, 0), W3(L, sv * hw, 0), W3(L, sv * hw, H(L)), W3(0, sv * hw, H(0))], v3.mul(side, sv), BED, BEDE);
    // chevrons: 3 ft wide, 45 deg arms, apex every 30 m starting 12 m from the entry
    for (let a = 12; a < L - 4; a += 30) for (const sv of [-1, 1]) {
      const d = Math.min(hw - 1, L - 1 - a); if (d <= 0.5) continue;
      const w2 = 0.64; // half-width along u'
      const p0 = [a - w2, 0], p1 = [a + w2, 0], p2 = [a + d + w2, sv * d], p3 = [a + d - w2, sv * d];
      const P = (q) => W3(q[0], q[1], H(q[0]) + 0.012);
      face([P(p0), P(p1), P(p2), P(p3)], [0, 1, 0], YEL, YELE);
    }
  }
  return g;
}
