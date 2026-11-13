// HWD world assembly (fork map 2.4 contract): ground, pavement, paint, buildings, markers, textures.
// Replaces sfo3d/js/live/world.js @ a967f9b buildLiveWorld (fork map 1.3). Kept from sfo3d: one function that registers
// the world programs, builds the static render items (terrain chunks with world bboxes for culling; decal paint as an
// alpha-blended item drawn in both range passes with a polygon offset; buildings as obj items), creates the shared
// textures (clouds, noise) and returns them with the ground uniforms; releaseAirportMap(). Changed: the SFO procedural
// region / Bay water / city bakes / EMAS / masts / signs / Blender asset groups are gone; the terrain is a tensor grid
// over the HWD site (10 m inside the aerodrome, growing outward to 40 km) whose heights come from site.groundY (NASR
// runway profiles, js/world/site.js); the pavement map and the NAIP backdrop are js/live/airport.js; the paint is
// js/live/markings.js; the buildings js/live/buildings.js; markers and beacon js/live/lights.js.
//
//   buildHwdWorld(R, airport, { site, quality = 'high', taxigraph = null, naip = true, log }) -> World
//   World = { items, site, towerPos, towerEye, textures, groundU, waterU: null, staticSprites(t), stats, ready (Promise),
//             setWind(fromDeg, speedMs, ext), setGroundMode('naip' | 'procedural'), inventory }
import { gl, Mesh, texture } from '../gl.js';
import { makeCloudTexture, makeNoiseTexture } from '../world/textures.js';
import { GROUND_VS, GROUND_FS } from '../shaders/ground.js';
import { DECAL_VS, DECAL_FS } from '../shaders/env.js';
import { OBJ_VS, OBJ_FS } from '../shaders/objects.js';
import '../shaders/common.js';
import { GRID } from '../world/grid.js';
import { RWY_PAIRS, RWY_DATA, FT, rwyAxis, thrDispM } from '../geo.js';
import { paintAirportMap, mapTexture, naipTexture } from './airport.js';
import { PAINT_VS, PAINT_FS, buildPaint } from './markings.js';
import { buildBuildings } from './buildings.js';
import { buildMarkers } from './lights.js';

export const QUALITY = {
  high: { mapRes: 0.5, naip: '1m2', inner: 10 },
  low: { mapRes: 1.0, naip: '2m4', inner: 12.5 },
};
// terrain extent: 40 km from the ARP (the camera far plane, fork map 2.5 starting point far 40,000 m)
const FAR = 40000;

// tensor-grid coordinates: `step` inside [a, b], then geometric growth x1.1 per cell outward to +-FAR
function axisCoords(a, b, step) {
  const c = []; const n = Math.ceil((b - a) / step); for (let i = 0; i <= n; i++) c.push(a + (b - a) * i / n);
  let x = b, s = step; while (x < FAR) { s *= 1.1; x += s; c.push(Math.min(x, FAR)); }
  x = a; s = step; const lo = []; while (x > -FAR) { s *= 1.1; x -= s; lo.push(Math.max(x, -FAR)); }
  return lo.reverse().concat(c);
}

function buildTerrain(site, inner) {
  const r = site.rect;
  const xs = axisCoords(r.x0, r.x0 + r.w, inner), zs = axisCoords(r.z0, r.z0 + r.h, inner);
  const CH = 24; const chunks = [];
  const nx = xs.length, nz = zs.length;
  const Y = new Float32Array(nx * nz);
  for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) Y[j * nx + i] = site.groundY(xs[i], zs[j]);
  const yAt = (i, j) => Y[Math.min(nz - 1, Math.max(0, j)) * nx + Math.min(nx - 1, Math.max(0, i))];
  for (let j0 = 0; j0 < nz - 1; j0 += CH) for (let i0 = 0; i0 < nx - 1; i0 += CH) {
    const i1 = Math.min(nx - 1, i0 + CH), j1 = Math.min(nz - 1, j0 + CH);
    const w = i1 - i0 + 1, h = j1 - j0 + 1;
    const pos = new Float32Array(w * h * 3), nrm = new Float32Array(w * h * 3); const idx = [];
    const bb = [1e9, 1e9, 1e9, -1e9, -1e9, -1e9];
    for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) {
      const k = ((j - j0) * w + (i - i0)) * 3; const y = yAt(i, j);
      pos[k] = xs[i]; pos[k + 1] = y; pos[k + 2] = zs[j];
      // normal from central differences of the grid heights
      const dx = xs[Math.min(nx - 1, i + 1)] - xs[Math.max(0, i - 1)], dz = zs[Math.min(nz - 1, j + 1)] - zs[Math.max(0, j - 1)];
      const gx = (yAt(i + 1, j) - yAt(i - 1, j)) / dx, gz = (yAt(i, j + 1) - yAt(i, j - 1)) / dz; const l = Math.hypot(gx, 1, gz);
      nrm[k] = -gx / l; nrm[k + 1] = 1 / l; nrm[k + 2] = -gz / l;
      bb[0] = Math.min(bb[0], xs[i]); bb[3] = Math.max(bb[3], xs[i]); bb[1] = Math.min(bb[1], y); bb[4] = Math.max(bb[4], y); bb[2] = Math.min(bb[2], zs[j]); bb[5] = Math.max(bb[5], zs[j]);
    }
    for (let j = 0; j < h - 1; j++) for (let i = 0; i < w - 1; i++) { const a = j * w + i; idx.push(a, a + w, a + w + 1, a, a + w + 1, a + 1); }
    bb[1] -= 0.5; bb[4] += 0.5;
    chunks.push({ pos, nrm, idx: new Uint32Array(idx), bbox: bb });
  }
  return { chunks, verts: nx * nz, tris: 2 * (nx - 1) * (nz - 1), nx, nz };
}

export function buildHwdWorld(R, airport, { site, quality = 'high', taxigraph = null, naip = true, log = () => {} } = {}) {
  const Q = QUALITY[quality] || QUALITY.high;
  let t0 = performance.now(); const T = {};
  const lap = (k) => { const t = performance.now(); T[k] = Math.round(t - t0); t0 = t; };
  R.addProgram('ground', GROUND_VS, GROUND_FS);
  R.addProgram('decal', DECAL_VS, DECAL_FS);
  R.addProgram('obj', OBJ_VS, OBJ_FS);
  R.addProgram('objI', OBJ_VS, OBJ_FS, { INSTANCED: 1 });
  R.addProgram('paint', PAINT_VS, PAINT_FS);
  R.addProgram('mark', PAINT_VS, PAINT_FS);   // sfo3d name of the ribbon program (fork map 2.5), same shader
  const clouds = makeCloudTexture(11), noise = makeNoiseTexture();
  lap('textures');
  // ---- pavement map
  const maxTex = Math.min(4096, gl.getParameter(gl.MAX_TEXTURE_SIZE));
  const map = paintAirportMap(airport, site, { res: Q.mapRes, maxTex }); const mapTex = mapTexture(map);
  lap('map');
  // ---- ground uniforms
  const rw = [], rwi = [];
  for (const [a, b] of RWY_PAIRS) { const A = rwyAxis(a); rw.push(A.origin[0], A.origin[1], A.dir[0], A.dir[1]); rwi.push(RWY_DATA[`${a}/${b}`].widthFt * FT / 2, A.length, thrDispM(a), A.length - thrDispM(b)); }
  const naipBorder = [0.3467, 0.3095, 0.2502];   // js/world/tex/naip2024.json border_linear_rgb (replaced when it loads)
  const placeholder = texture(1, 1, { data: new Uint8Array([150, 140, 120, 255]) });
  const groundU = {
    uAptMap: mapTex, uMapRect: [map.rect.s0, map.rect.t0, map.rect.w, map.rect.h], uMapSize: [map.w, map.h], uGs: GRID.s, uGt: GRID.t,
    uRw: rw, uRwI: rwi,
    uNaip: placeholder, uNaipU: [0, 0, -1], uNaipV: [0, 0, -1], uNaipMix: 0, uNaipGain: 0.55, uNaipBorder: naipBorder,
  };
  const items = [];
  // ---- terrain
  const TR = buildTerrain(site, Q.inner);
  for (const c of TR.chunks) items.push({ mesh: new Mesh({ pos: c.pos, nrm: c.nrm, idx: c.idx }), prog: 'ground', uniforms: groundU, bbox: c.bbox, castShadow: false });
  lap('terrain');
  // ---- paint
  const paint = buildPaint(R, site, airport); if (paint.item) items.push(paint.item);
  lap('paint');
  // ---- buildings
  const B = buildBuildings(site); items.push(...B.items);
  lap('buildings');
  // ---- markers, beacon
  const MK = buildMarkers(site, airport); items.push(...MK.items);
  lap('markers');
  const tw = site.anchors.tower;
  const world = {
    items, site,
    towerPos: tw ? [tw.x, tw.top, tw.z] : [0, 30, 0],
    towerEye: tw ? [tw.x, tw.eyeY, tw.z] : [0, 25, 0],
    textures: { clouds, noise, map: mapTex, naip: null },
    groundU, waterU: null, map,
    nightF: 0, sunEl: 30,
    staticSprites: (t) => MK.sprites(t, world.sunEl),
    setWind: (fromDeg, speedMs, ext) => MK.setWind(fromDeg, speedMs, ext),
    setGroundMode: (m) => { groundU.uNaipMix = m === 'naip' && world.textures.naip ? 1 : 0; world.groundMode = groundU.uNaipMix ? 'naip' : 'procedural'; },
    groundMode: 'procedural',
    inventory: { paint: paint.inventory, buildings: B.list, markers: MK.inventory },
    stats: { ms: T, terrain: { verts: TR.verts, tris: TR.tris, chunks: TR.chunks.length, grid: `${TR.nx} x ${TR.nz}`, inner_m: Q.inner }, map: { w: map.w, h: map.h, res: map.res }, paint: { tris: paint.tris, verts: paint.verts }, buildings: B.stats, quality },
  };
  // ---- NAIP backdrop (async; the ground shows the procedural grass until it is in)
  world.ready = (naip ? naipTexture(Q.naip).then(N => {
    groundU.uNaip = N.tex; groundU.uNaipU = N.U; groundU.uNaipV = N.V; groundU.uNaipBorder = N.meta.border_linear_rgb;
    world.textures.naip = N.tex; world.stats.naip = { level: Q.naip, w: N.level.width, h: N.level.height, residual_m: Math.round(N.residual_m * 1000) / 1000 };
    world.setGroundMode('naip');
    log('NAIP backdrop ' + Q.naip + ' ' + N.level.width + 'x' + N.level.height + ' fit residual ' + N.residual_m.toFixed(4) + ' m');
  }).catch(e => { log('NAIP backdrop not loaded: ' + e.message); world.stats.naip = { error: String(e.message || e) }; }) : Promise.resolve());
  log('world ' + JSON.stringify(world.stats));
  return world;
}
// the sfo3d contract: after the first bake the airport source map can be released. HWD keeps the map texture (the ground
// shader samples it every frame); only the CPU copy is dropped.
export function releaseAirportMap(world) { if (world.map) world.map.data = null; }
