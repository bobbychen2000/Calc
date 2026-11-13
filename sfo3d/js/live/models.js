// Loader for converted airliner models (.sfom = gzip(SFOM header + JSON + blob)).
// Materials are baked into vertex attributes so a whole airframe draws in one call per texture.
// Texture 0 of an atlased model (head.atlas, tools/liveries/atlas.py) is the livery atlas: its draw carries uAtlas = 1 and
// can wear a brand livery texture (getLiveryTexture, js/aircraft/liveries.js); its alpha marks cabin-window glass.
import { gl, Mesh } from '../gl.js';
import { applyStretch } from '../aircraft/stretch.js';

const cache = new Map();      // key -> Promise<Model>
export const MODEL_SOURCES = {}; // key -> ArrayBuffer | url | () => ArrayBuffer (set by the app)
// models added after js/live/entry.js MODEL_KEYS was written (777 family, review round 1): resolved like entry.js does
// (embedded base64, else SFO_MODEL_BASE + key + SFO_MODEL_EXT) until entry.js lists them (docs/requests/aircraft_models_777.md)
for (const k of ['b772', 'b77w']) MODEL_SOURCES[k] = () => {
  const w = typeof window !== 'undefined' ? window : {};
  if (w.SFO_EMBED && w.SFO_EMBED[k]) { const bin = atob(w.SFO_EMBED[k]); const u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i); return u.buffer; }
  return (w.SFO_MODEL_BASE || 'data/models/') + k + (w.SFO_MODEL_EXT || '.sfom');
};
export const KIND = { paint: 0, glass: 1, metal: 2, dark: 3, light: 4 };

async function gunzip(buf) {
  if (typeof DecompressionStream === 'undefined') throw new Error('This browser cannot decompress models (DecompressionStream missing).');
  const ds = new DecompressionStream('gzip');
  return await new Response(new Blob([buf]).stream().pipeThrough(ds)).arrayBuffer();
}

function srgbTexture(src) {
  const t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t);
  const w = src.width, h = src.height;
  const levels = Math.floor(Math.log2(Math.max(w, h))) + 1;
  gl.texStorage2D(gl.TEXTURE_2D, levels, gl.SRGB8_ALPHA8, w, h);
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false); gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
  gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, gl.RGBA, gl.UNSIGNED_BYTE, src);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.REPEAT);
  gl.generateMipmap(gl.TEXTURE_2D);
  const e = gl.getExtension('EXT_texture_filter_anisotropic'); if (e) gl.texParameterf(gl.TEXTURE_2D, e.TEXTURE_MAX_ANISOTROPY_EXT, 4);
  return { tex: t, w, h };
}
const MIME = { png: 'image/png', jpg: 'image/jpeg', webp: 'image/webp' };
async function decodeImage(bytes, type) {
  const blob = new Blob([bytes], { type });
  try {
    const bmp = await createImageBitmap(blob, { premultiplyAlpha: 'none', colorSpaceConversion: 'none' });
    return { img: bmp, close: () => bmp.close && bmp.close() };
  } catch (e) { // older Safari: fall back to an <img>
    const url = URL.createObjectURL(blob);
    const img = new Image(); img.decoding = 'async'; img.src = url;
    await img.decode();
    return { img, close: () => URL.revokeObjectURL(url) };
  }
}

// applyStretch (the fit's stretch of the vertex positions) lives in js/aircraft/stretch.js (pure: also used by node tools)
export { applyStretch };

export async function decodeModel(buf, stretch = null) {
  const b0 = new Uint8Array(buf, 0, 2);
  const raw = (b0[0] === 0x1f && b0[1] === 0x8b) ? await gunzip(buf) : buf; // accept already-decompressed data too
  const dv = new DataView(raw);
  const magic = String.fromCharCode(dv.getUint8(0), dv.getUint8(1), dv.getUint8(2), dv.getUint8(3));
  if (magic !== 'SFOM') throw new Error('bad model file');
  const hl = dv.getUint32(8, true);
  const head = JSON.parse(new TextDecoder().decode(new Uint8Array(raw, 12, hl)));
  const B = 12 + hl; const nv = head.nv, q = head.quant, o = head.offsets;
  const pq = new Uint16Array(raw, B + o.pos, nv * 3), nq = new Int8Array(raw, B + o.nrm, nv * 4), uq = new Uint16Array(raw, B + o.uv, nv * 2), zq = new Uint8Array(raw, B + o.zone, nv);
  const pos = new Float32Array(nv * 3), nrm = new Float32Array(nv * 3), uv = new Float32Array(nv * 2), extra = new Float32Array(nv * 4), col = new Float32Array(nv * 4);
  for (let i = 0; i < nv; i++) {
    for (let k = 0; k < 3; k++) { pos[i * 3 + k] = q.pmin[k] + pq[i * 3 + k] * q.pscale[k]; nrm[i * 3 + k] = nq[i * 4 + k] / 127; }
    uv[i * 2] = q.umin[0] + uq[i * 2] * q.uscale[0]; uv[i * 2 + 1] = q.umin[1] + uq[i * 2 + 1] * q.uscale[1];
    extra[i * 4] = zq[i];
  }
  const dims = { ...head.dims };
  // retraction legs of the model's own gear (737 / 777): legs on the unstretched mesh (the same assignment for every
  // variant), pivots / fold angles on the stretched one (what is drawn)
  const legs = dims.hasGear ? gearLegs(pos, zq, extra, nv) : null;
  if (stretch) applyStretch(pos, zq, nv, stretch, dims);
  const idxIn = head.idxType === 'u16' ? new Uint16Array(raw, B + o.idx, head.ni) : new Uint32Array(raw, B + o.idx, head.ni);
  const gear = legs ? gearPivots(pos, zq, extra, nv, legs, idxIn) : null;
  // bake material properties into vertices; regroup triangles by texture
  const mats = head.mats;
  const groups = new Map(); // tex index (-1 = none) -> [draws]
  for (const d of head.draws) {
    const m = mats[d.mat]; const kind = KIND[m.kind] ?? 0;
    for (let i = d.first; i < d.first + d.count; i++) {
      const v = idxIn[i];
      col[v * 4] = m.color[0]; col[v * 4 + 1] = m.color[1]; col[v * 4 + 2] = m.color[2]; col[v * 4 + 3] = m.white ?? 0.9;
      extra[v * 4 + 1] = kind + (m.alphaTest ? 8 : 0); extra[v * 4 + 2] = m.rough; extra[v * 4 + 3] = m.metal;
    }
    const key = m.tex >= 0 ? m.tex : -1;
    if (!groups.has(key)) groups.set(key, []); groups.get(key).push(d);
  }
  const idx = new Uint32Array(head.ni); let w = 0; const draws = [];
  for (const [tex, list] of groups) {
    const first = w;
    for (const d of list) for (let i = d.first; i < d.first + d.count; i++) idx[w++] = idxIn[i];
    draws.push({ tex, first, count: w - first });
  }
  const nIdx = w;
  repairNormals(pos, nrm, idx.subarray(0, nIdx), nv);
  let mn = [1e9, 1e9, 1e9], mx = [-1e9, -1e9, -1e9];
  for (let i = 0; i < nv; i++) for (let k = 0; k < 3; k++) { const v = pos[i * 3 + k]; if (v < mn[k]) mn[k] = v; if (v > mx[k]) mx[k] = v; }
  const anchors = lightAnchors(pos, nv, mn, mx, dims.R || 2);
  const tip = wingTip(pos, zq, nv, mn, mx);
  const mesh = new Mesh({ pos, nrm, uv, col, extra, idx: idx.slice(0, nIdx) });
  const textures = [];
  for (const t of head.textures) {
    const im = await decodeImage(new Uint8Array(raw, B + t.offset, t.length), MIME[t.fmt] || 'image/jpeg');
    textures.push(srgbTexture(im.img)); im.close();
  }
  const white = { tex: null };
  const atlas = !!head.atlas;
  const drawList = draws.map(d => ({ ...d, atlas: atlas && d.tex === 0, U: { uAlbedo: d.tex >= 0 ? textures[d.tex] : (textures[0] || white), uHasTex: d.tex >= 0 ? 1 : 0, uAtlas: atlas && d.tex === 0 ? 1 : 0, uLivTex: 0 },
    sub: { draw: () => mesh.drawRange(d.first, d.count) } }));
  const all = { draw: () => mesh.drawRange(0, nIdx) };
  return { key: head.key, name: head.name, head, dims, mesh, draws: drawList, all, bbox: [mn, mx], verts: nv, tris: nIdx / 3, anchors, tip, gearRig: gear };
}

// Retraction of a model that carries its own landing gear (dims.hasGear: the 737 / 777 families; zone 3 = gear, 4 = gear
// doors; tools/convert_models.py ZONE). Until 13 Nov 2026 the gear stayed down and vanished once retracted (owner: 'I don't
// see landing gear pull up during take off'). Each leg now swings about the top of its strut: the nose gear FORWARD (about
// the lateral z axis), the main gears INBOARD (about the longitudinal x axis), as on the 737 and 777 (the landing-gear
// descriptions of the Boeing FCOMs as quoted by secondary sources -- smartcockpit 737NG gear quiz, scribd B777 landing-gear
// notes, planefyi gear-retraction page; the FCOM text itself was not retrieved: V-secondary).
// The role of each gear / door vertex is written into the fraction of extra.x in steps of 0.05 (the zone stays the integer
// part, floor(x + 0.5), everywhere else): 1 nose leg, 2 / 3 port / starboard main leg (rigid), 4 static (zone-3 parts that
// are not legs: the 777 flap-track fairing tips at 11-20 m span, the 737 nose wheel-well box), 5 / 6 port / starboard
// brace (side braces and actuators: a rigid swing about the trunnion lifts them through the wing, verifier 13 Nov: up to
// 1.6 m above the 777 wing; they fold away during the swing), 7 / 8 port / starboard belly door (the 777's inboard main
// gear doors, closed on the ground: open about their outboard hinge while the trucks pass, then close; drawn closed with
// the gear up), 0 other doors (collapse once the gear is up, as before). Shaders: js/three/aircraft.js realMaterial,
// js/shaders/aircraft_real.js ACR_VS.
const GEAR_STEP = 0.05;
// Stage 1 (unstretched mesh; 0.5-unit cells, 26-neighbourhood): the strut clusters are the zone-3 clusters reaching the
// ground (lowest vertex within 0.5 of the lowest gear vertex; nose ahead of 0.3 L, mains by side). Split-off pieces whose
// centre lies INSIDE a strut cluster's box join it (rigid); for the mains, pieces within 1 unit of the box are braces; the
// rest is static. Main-leg vertices inboard of the strut axis by > 0.3 in the upper 55 % of the leg are braces.
// Returns { strut: Uint8Array (1 = vertex of a strut cluster) } or null.
export function gearLegs(pos, zone, extra, nv) {
  let x0 = 1e9, x1 = -1e9, yLow = 1e9;
  for (let i = 0; i < nv; i++) { const x = pos[i * 3]; if (x < x0) x0 = x; if (x > x1) x1 = x; if (zone[i] === 3 && pos[i * 3 + 1] < yLow) yLow = pos[i * 3 + 1]; }
  if (yLow > 1e8) return null;
  const xs = x1 - 0.3 * (x1 - x0), C = 0.5, cellOf = (i) => Math.floor(pos[i * 3] / C) + ',' + Math.floor(pos[i * 3 + 1] / C) + ',' + Math.floor(pos[i * 3 + 2] / C);
  const cells = new Map();
  for (let i = 0; i < nv; i++) if (zone[i] === 3) { const k = cellOf(i); let a = cells.get(k); if (!a) cells.set(k, a = []); a.push(i); }
  const seen = new Set(), clusters = [];
  for (const k0 of cells.keys()) {
    if (seen.has(k0)) continue; const st = [k0], idx = []; seen.add(k0);
    while (st.length) {
      const k = st.pop(); idx.push(...cells.get(k)); const [a, b, c] = k.split(',').map(Number);
      for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) for (let dz = -1; dz <= 1; dz++) {
        const kk = (a + dx) + ',' + (b + dy) + ',' + (c + dz); if (cells.has(kk) && !seen.has(kk)) { seen.add(kk); st.push(kk); }
      }
    }
    const bb = [1e9, 1e9, 1e9, -1e9, -1e9, -1e9]; let zm = 0;
    for (const i of idx) { for (let k = 0; k < 3; k++) { bb[k] = Math.min(bb[k], pos[i * 3 + k]); bb[k + 3] = Math.max(bb[k + 3], pos[i * 3 + k]); } zm += pos[i * 3 + 2]; }
    const ground = bb[1] < yLow + 0.5, cx = (bb[0] + bb[3]) / 2;
    clusters.push({ idx, bb, ground, leg: ground ? (cx > xs ? 1 : zm < 0 ? 2 : 3) : 4 });
  }
  const struts = clusters.filter(c => c.ground);
  if (!struts.some(c => c.leg === 1) || !struts.some(c => c.leg !== 1)) return null;
  const inBox = (g, m, d) => [0, 1, 2].every(k => m[k] >= g.bb[k] - d && m[k] <= g.bb[k + 3] + d);
  const strut = new Uint8Array(nv), code = new Uint8Array(nv);
  for (const c of clusters) {
    let cd = c.leg;
    if (!c.ground) {
      const m = [0, 1, 2].map(k => (c.bb[k] + c.bb[k + 3]) / 2);
      const G = struts.find(g => inBox(g, m, 0)), Gm = struts.find(g => g.leg !== 1 && inBox(g, m, 1));
      cd = G ? G.leg : Gm ? Gm.leg + 3 : 4;          // inside a strut box: rigid with it; near a main strut: brace; else static
    }
    for (const i of c.idx) { code[i] = cd; if (c.ground) strut[i] = 1; }
  }
  // side braces / actuators of the mains: inboard of the strut axis (median |z| of the mid-strut band) in the upper part
  for (const g of struts) {
    if (g.leg === 1) continue; const yb = g.bb[1], yt = g.bb[4], span = yt - yb;
    const band = []; for (const i of g.idx) { const y = pos[i * 3 + 1]; if (y > yb + 0.45 * span && y < yb + 0.75 * span) band.push(Math.abs(pos[i * 3 + 2])); }
    band.sort((a, b) => a - b); const zAx = band.length ? band[band.length >> 1] : 0;
    for (const i of g.idx) if (pos[i * 3 + 1] > yb + 0.45 * span && Math.abs(pos[i * 3 + 2]) < zAx - 0.3) code[i] = g.leg + 3;
  }
  for (let i = 0; i < nv; i++) if (zone[i] === 3) extra[i * 4] = 3 + code[i] * GEAR_STEP;
  // doors: on a leg (outboard of its strut, within its span) move with it; inboard of the mains = belly doors; else 0
  const mainBoxes = struts.filter(g => g.leg !== 1);
  let zAxis = 1e9; for (const g of mainBoxes) zAxis = Math.min(zAxis, Math.abs((g.bb[2] + g.bb[5]) / 2));
  for (let i = 0; i < nv; i++) {
    if (zone[i] !== 4) continue; const x = pos[i * 3], z = pos[i * 3 + 2], az = Math.abs(z), side = z < 0 ? 0 : 1;
    const onMain = mainBoxes.some(g => x >= g.bb[0] - 0.5 && x <= g.bb[3] + 0.5);
    const cd = x > xs ? 1 : onMain && az >= zAxis - 0.2 ? 2 + side : onMain ? 7 + side : 0;
    extra[i * 4] = 4 + cd * GEAR_STEP;
  }
  return { strut };
}
// Stage 2 (the drawn, stretched mesh): pivots and fold angles. Returns [xNose, yNose, yMain, zMain, aNose, aMain, yHinge,
// zHinge] (model units, rad). Strut top = the highest strut vertex; strut axis = the median of the mid-strut band (45-75 %
// of the leg height: the side brace and the top fittings no longer pull the pivot inboard, 0.45 / 0.98 units on the 737 /
// 777, verifier 13 Nov). The fold angles are solved on a skin height map (0.5-unit (x, z) cells; topmost / lowest surface
// of the non-gear triangles at each cell centre): the nose angle is the smallest in 85..120 deg that folds 98 % of the tyre
// vertices (lowest 35 % of the leg) above the belly (the 777 nose needs ~100-105 deg, the 737 ~100); the main angle the
// largest in 80..88 deg (88 = the procedural gear's 0.98 x 90) that leaves no rigid leg vertex above the top skin (the
// models have no well cavity: at 88-90 deg the 777's inboard tyres rose up to 0.35 above the wing-body fairing). Belly-door
// hinge = the doors' outboard top edge.
export function skinMap(pos, zone, idx, C = 0.5) {
  const top = new Map(), bot = new Map();
  for (let t = 0; t + 2 < idx.length; t += 3) {
    const a = idx[t], b = idx[t + 1], c = idx[t + 2]; const g = v => zone[v] === 3 || zone[v] === 4 || zone[v] === 8; if (g(a) || g(b) || g(c)) continue;
    const ax = pos[a * 3], az = pos[a * 3 + 2], bx = pos[b * 3], bz = pos[b * 3 + 2], cx = pos[c * 3], cz = pos[c * 3 + 2];
    const d = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz); if (Math.abs(d) < 1e-12) continue;
    for (let gx = Math.floor(Math.min(ax, bx, cx) / C); gx <= Math.floor(Math.max(ax, bx, cx) / C); gx++) for (let gz = Math.floor(Math.min(az, bz, cz) / C); gz <= Math.floor(Math.max(az, bz, cz) / C); gz++) {
      const x = (gx + 0.5) * C, z = (gz + 0.5) * C;
      const w0 = ((bz - cz) * (x - cx) + (cx - bx) * (z - cz)) / d, w1 = ((cz - az) * (x - cx) + (ax - cx) * (z - cz)) / d, w2 = 1 - w0 - w1;
      if (w0 < -1e-6 || w1 < -1e-6 || w2 < -1e-6) continue;
      const y = w0 * pos[a * 3 + 1] + w1 * pos[b * 3 + 1] + w2 * pos[c * 3 + 1], k = gx * 65536 + gz;
      if (!top.has(k) || y > top.get(k)) top.set(k, y); if (!bot.has(k) || y < bot.get(k)) bot.set(k, y);
    }
  }
  const key = (x, z) => Math.floor(x / C) * 65536 + Math.floor(z / C);
  return { top: (x, z) => top.get(key(x, z)), bot: (x, z) => bot.get(key(x, z)) };
}
export function gearPivots(pos, zone, extra, nv, legs, idx) {
  const code = (i) => Math.round((extra[i * 4] - zone[i]) / GEAR_STEP);
  const axis = (sel, f) => {
    let yb = 1e9, yt = -1e9; for (let i = 0; i < nv; i++) if (sel(i)) { const y = pos[i * 3 + 1]; yb = Math.min(yb, y); yt = Math.max(yt, y); }
    const span = yt - yb, v = []; for (let i = 0; i < nv; i++) if (sel(i)) { const y = pos[i * 3 + 1]; if (y > yb + 0.45 * span && y < yb + 0.75 * span) v.push(f(i)); }
    v.sort((a, b) => a - b); return { yb, yt, med: v.length ? v[v.length >> 1] : 0 };
  };
  const nose = axis(i => zone[i] === 3 && legs.strut[i] && code(i) === 1, i => pos[i * 3]);
  const main = axis(i => zone[i] === 3 && legs.strut[i] && (code(i) === 2 || code(i) === 3), i => Math.abs(pos[i * 3 + 2]));
  if (nose.yt < -1e8 || main.yt < -1e8) return null;
  const xN = nose.med, yN = nose.yt, yM = main.yt, zM = main.med;
  const S = idx ? skinMap(pos, zone, idx) : null;
  // nose: smallest angle that stows 98 % of the tyre vertices above the belly
  const tyres = []; const tTop = nose.yb + 0.35 * (nose.yt - nose.yb);
  for (let i = 0; i < nv; i++) if (zone[i] === 3 && code(i) === 1 && pos[i * 3 + 1] < tTop) tyres.push(i);
  let aN = Math.PI / 2 * 0.95;
  if (S) {
    let best = -1;
    for (let deg = 85; deg <= 120; deg++) {
      const a = deg * Math.PI / 180, c = Math.cos(a), s = Math.sin(a); let ok = 0;
      for (const i of tyres) { const dx = pos[i * 3] - xN, dy = pos[i * 3 + 1] - yN, x = c * dx - s * dy + xN, y = s * dx + c * dy + yN; const b = S.bot(x, pos[i * 3 + 2]); if (b === undefined || y > b + 0.02) ok++; }
      const f = tyres.length ? ok / tyres.length : 1;
      if (f > best + 1e-9) { best = f; aN = a; } if (f >= 0.98) { aN = a; break; }
    }
  }
  // mains: largest angle (<= 88 deg) with no rigid leg vertex above the top skin
  let aM = Math.PI / 2 * 0.98;
  if (S) for (let deg = 88; deg >= 80; deg--) {
    const a0 = deg * Math.PI / 180; let above = 0;
    for (let i = 0; i < nv && !above; i++) {
      const cd = code(i); if (zone[i] !== 3 || (cd !== 2 && cd !== 3)) continue;
      const sg = cd === 3 ? 1 : -1, a = a0 * sg, c = Math.cos(a), s = Math.sin(a), zp = zM * sg, dy = pos[i * 3 + 1] - yM, dz = pos[i * 3 + 2] - zp;
      const y = c * dy - s * dz + yM, z = s * dy + c * dz + zp, t = S.top(pos[i * 3], z); if (t !== undefined && y > t - 0.02) above++;
    }
    aM = a0; if (!above) break;
  }
  let zH = 0, yH = 0; for (let i = 0; i < nv; i++) { const cd = code(i); if (zone[i] === 4 && (cd === 7 || cd === 8)) zH = Math.max(zH, Math.abs(pos[i * 3 + 2])); }
  if (zH > 0) { yH = -1e9; for (let i = 0; i < nv; i++) { const cd = code(i); if (zone[i] === 4 && (cd === 7 || cd === 8) && Math.abs(pos[i * 3 + 2]) > zH - 0.1) yH = Math.max(yH, pos[i * 3 + 1]); } }
  return [xN, yN, yM, zM, aN, aM, yH, zH];
}
// one call on one position set (tests / tools)
export function gearRig(pos, zone, extra, nv, idx = null) { const L = gearLegs(pos, zone, extra, nv); return L ? gearPivots(pos, zone, extra, nv, L, idx) : null; }

// Some source meshes carry degenerate or contradictory vertex normals (FAM 747-400 nose: 17 % of the skin vertices ahead of
// the wing have near-zero normals where inward and outward faces were averaged; they shade as dark blotches, review round
// 1). Each vertex's normal is compared with the area-weighted normal of its own faces (face normals oriented to agree with
// the stored normal, so the source's inconsistent winding does not matter; vertices split at hard edges keep them): a
// stored normal shorter than 0.6 or more than 60 deg away from that is replaced by it. Tools: tools/liveries/common.py
// repair_normals (the same rule, for the Blender / software renders).
export function repairNormals(pos, nrm, idx, nv) {
  const acc = new Float32Array(nv * 3);
  for (let t = 0; t < idx.length; t += 3) {
    const a = idx[t] * 3, b = idx[t + 1] * 3, c = idx[t + 2] * 3;
    const ux = pos[b] - pos[a], uy = pos[b + 1] - pos[a + 1], uz = pos[b + 2] - pos[a + 2];
    const vx = pos[c] - pos[a], vy = pos[c + 1] - pos[a + 1], vz = pos[c + 2] - pos[a + 2];
    const fx = uy * vz - uz * vy, fy = uz * vx - ux * vz, fz = ux * vy - uy * vx;     // |f| = 2 x area
    for (const v of [a, b, c]) {
      // reference direction: the stored normal, or for a degenerate one the outward radial direction from the fuselage axis
      let rx = nrm[v], ry = nrm[v + 1], rz = nrm[v + 2]; if (rx * rx + ry * ry + rz * rz < 0.09) { rx = 0; ry = pos[v + 1]; rz = pos[v + 2]; }
      const sg = (fx * rx + fy * ry + fz * rz) < 0 ? -1 : 1; acc[v] += sg * fx; acc[v + 1] += sg * fy; acc[v + 2] += sg * fz;
    }
  }
  let fixed = 0;
  for (let i = 0; i < nv; i++) {
    const o = i * 3; const al = Math.hypot(acc[o], acc[o + 1], acc[o + 2]); if (al < 1e-12) continue;
    const nl = Math.hypot(nrm[o], nrm[o + 1], nrm[o + 2]);
    const cos = nl > 1e-6 ? (acc[o] * nrm[o] + acc[o + 1] * nrm[o + 1] + acc[o + 2] * nrm[o + 2]) / (al * nl) : 0;
    if (nl < 0.6 || cos < 0.5) { nrm[o] = acc[o] / al; nrm[o + 1] = acc[o + 1] / al; nrm[o + 2] = acc[o + 2] / al; fixed++; }
  }
  return fixed;
}

// the wing tip (model units, starboard; the port tip mirrors it): leading / trailing edge x and the lower surface y of the
// outermost 0.35 of the wing (not the tailplane), for the procedural tip devices (js/aircraft/fit.js TIP_ADD)
function wingTip(pos, zone, nv, mn, mx) {
  const L = mx[0] - mn[0]; let zmax = 0;
  for (let i = 0; i < nv; i++) if (zone[i] === 0 && pos[i * 3] > mx[0] - 0.75 * L) zmax = Math.max(zmax, Math.abs(pos[i * 3 + 2]));
  let x0 = -1e9, x1 = 1e9, ys = 0, n = 0;
  for (let i = 0; i < nv; i++) {
    if (zone[i] !== 0 || pos[i * 3] <= mx[0] - 0.75 * L || Math.abs(pos[i * 3 + 2]) < zmax - 0.35) continue;
    x0 = Math.max(x0, pos[i * 3]); x1 = Math.min(x1, pos[i * 3]); ys += pos[i * 3 + 1]; n++;
  }
  return n ? { z: zmax, x: x0, c: x0 - x1, y: ys / n } : null;
}

// exterior light positions from the model's own geometry (model units: x forward (nose 0), y up, z to the right):
// navigation lights at the wing-tip leading edges, tail light at the tail cone, anti-collision beacons on the crown
// and belly above/below the wing box
function lightAnchors(pos, nv, mn, mx, R0) {
  const zR = mx[2], zL = mn[2];
  let r = null, l = null, tail = null, top = null, bot = null;
  const L = mx[0] - mn[0], xw0 = mx[0] - 0.55 * L, xw1 = mx[0] - 0.3 * L;
  for (let i = 0; i < nv; i++) {
    const x = pos[i * 3], y = pos[i * 3 + 1], z = pos[i * 3 + 2];
    if (z > zR - 0.03 * (zR - zL) * 0.5) { if (!r || x > r[0]) r = [x, y, z]; }
    if (z < zL + 0.03 * (zR - zL) * 0.5) { if (!l || x > l[0]) l = [x, y, z]; }
    if (Math.abs(z) < 0.25) {
      if (y > -0.5 * R0 && y < 1.2 * R0 && (!tail || x < tail[0])) tail = [x, y, z];   // tail cone (not the fin tip)
      if (x > xw0 && x < xw1) { if (!top || y > top[1]) top = [x, y, 0]; if (!bot || y < bot[1]) bot = [x, y, 0]; }
    }
  }
  return r && l ? { navR: r, navL: l, tail, beaconTop: top, beaconBot: bot } : null;
}
async function sourceBytes(src) {
  if (typeof src === 'function') src = await src();
  if (typeof src === 'string') { const r = await fetch(src); if (!r.ok) throw new Error('model fetch ' + r.status); return await r.arrayBuffer(); }
  return src;
}
// the model file of `key`, fetched once and shared by every stretched variant decoded from it (737-700/-800/-900/MAX on
// b738, CRJ-700/-900 on crj2, ...): before, each variant fetched the same file again (the phone replay of 8 Nov 20:38Z
// fetched b738 5x and crj2 7x). decodeModel and modelPositions only read the buffer, as with an ArrayBuffer source.
// A failed fetch is dropped from the cache so a later variant retries.
const srcCache = new Map();   // key -> Promise<ArrayBuffer>
function keyBytes(key) {
  const src = MODEL_SOURCES[key]; if (!src) return Promise.reject(new Error('no model source for ' + key));
  if (!srcCache.has(key)) { const p = sourceBytes(src); srcCache.set(key, p); p.catch(() => { if (srcCache.get(key) === p) srcCache.delete(key); }); }
  return srcCache.get(key);
}
// vertex positions (model frame, after the fit's stretch) and zones of model `key`, without GPU objects: for QA tools that
// measure what is drawn in the running app (tools/models/qa_stance.mjs: tyre contact on the mesh, close-out round 3,
// aircraft-3). Returns { pos: Float32Array(nv * 3), zone: Uint8Array(nv), nv, dims } (dims after the stretch)
export async function modelPositions(key, stretch = null) {
  const buf = await keyBytes(key); const b0 = new Uint8Array(buf, 0, 2);
  const raw = (b0[0] === 0x1f && b0[1] === 0x8b) ? await gunzip(buf) : buf; const dv = new DataView(raw);
  const hl = dv.getUint32(8, true); const head = JSON.parse(new TextDecoder().decode(new Uint8Array(raw, 12, hl)));
  const B = 12 + hl, nv = head.nv, q = head.quant, o = head.offsets;
  const pq = new Uint16Array(raw, B + o.pos, nv * 3), zone = new Uint8Array(raw, B + o.zone, nv).slice(), pos = new Float32Array(nv * 3);
  for (let i = 0; i < nv * 3; i++) pos[i] = q.pmin[i % 3] + pq[i] * q.pscale[i % 3];
  const dims = { ...head.dims }; if (stretch) applyStretch(pos, zone, nv, stretch, dims);
  return { pos, zone, nv, dims };
}
export function getModel(key, stretch) {
  const ck = key + (stretch ? ':' + JSON.stringify(stretch) : '');
  if (!cache.has(ck)) {
    const p = (async () => {
      const m = await decodeModel(await keyBytes(key), stretch);
      p._value = m; return m;
    })();
    cache.set(ck, p);
  }
  return cache.get(ck);
}

// brand livery textures (data/liveries/<brand>/<model>[@type]-<res>.webp): fetched on demand, shared by every aircraft
// wearing them, kept for the session (a few MB each at the default resolution)
const livCache = new Map();
export function getLiveryTexture(url) {
  if (!livCache.has(url)) {
    const p = (async () => {
      const r = await fetch(url); if (!r.ok) throw new Error('livery fetch ' + r.status + ' ' + url);
      const im = await decodeImage(new Uint8Array(await r.arrayBuffer()), MIME[url.split('.').pop()] || 'image/webp');
      const t = srgbTexture(im.img); im.close(); return t;
    })();
    p.catch(e => console.log('livery load failed', url, e.message));
    livCache.set(url, p);
  }
  return livCache.get(url);
}

// Registration decal (the aircraft's own tail number, painted per aircraft at run time: js/live/aircraft.js places it on
// the aft fuselage as measured on the brand's photographs, tools/liveries/liveries.py REG). Two rows of one texture: the
// port-side layout on top ("N37440 [flag]": text then the flag aft of it, or the flag first when the airline paints it
// ahead), the starboard layout below (the flag stays on the same end of the aircraft, so the order is reversed; the flag
// is mirrored so its canton leads, as flags are painted on aircraft). Text pixels are pure black: the shader inks them
// dark or white by the paint under them; flag pixels keep their colours. -> { tex, w, h, aspect (row width / height) }
const regCache = new Map();
const ROW = 96, CAP = 0.74;                       // row height px, cap height as a fraction of the row
export function drawFlag(ctx, kind, x, y, h, mirror) {
  const w = h * (kind === 'MX' ? 7 / 4 : 19 / 10);
  ctx.save(); ctx.translate(x + (mirror ? w : 0), y); ctx.scale(mirror ? -1 : 1, 1);
  if (kind === 'US') {                            // 4 USC 1: 13 stripes, canton 7 stripes high, 0.76 of the hoist... (simplified, stars as dots)
    for (let i = 0; i < 13; i++) { ctx.fillStyle = i % 2 ? '#FFFFFF' : '#B22234'; ctx.fillRect(0, i * h / 13, w, h / 13 + 0.5); }
    ctx.fillStyle = '#3C3B6E'; ctx.fillRect(0, 0, w * 0.4, h * 7 / 13);
    ctx.fillStyle = '#FFFFFF'; for (let r = 0; r < 5; r++) for (let c = 0; c < 6; c++) { ctx.beginPath(); ctx.arc(w * 0.4 * (c + 0.5) / 6, h * 7 / 13 * (r + 0.5) / 5, h * 0.022, 0, 7); ctx.fill(); }
  } else if (kind === 'MX') {                     // green, white, red vertical; the coat of arms as a brown dot
    const cs = ['#006847', '#FFFFFF', '#CE1126']; cs.forEach((c, i) => { ctx.fillStyle = c; ctx.fillRect(i * w / 3, 0, w / 3 + 0.5, h); });
    ctx.fillStyle = '#8C5A2B'; ctx.beginPath(); ctx.arc(w / 2, h / 2, h * 0.14, 0, 7); ctx.fill();
  }
  ctx.strokeStyle = 'rgba(120,120,120,0.8)'; ctx.lineWidth = 1; ctx.strokeRect(0.5, 0.5, w - 1, h - 1);
  ctx.restore(); return w;
}
// the registration decal's layout (close-out round 3, aircraft-10: js/three/aircraft.js RegAtlas replicated it; engine_exports.md
// §7 / engine_closeout.md §4): row height `row` px (default ROW), the font and the draw list of both rows (port on top: nose
// on the left, the flag aft of the text unless flagFirst; starboard below: order reversed, flag mirrored). measure(font,
// text) -> width px (a 2-D context's measureText); maxW: when the layout would be wider, everything is scaled down to fit
// (RegAtlas slots). -> { font, px, w, h, aspect, ops: [{ op: 'flag', kind, x, y, h, mirror } | { op: 'text', text, x, y }] }
// (coordinates relative to the layout's top-left corner; text y is the alphabetic baseline). drawRegistration draws it.
export function registrationLayout(reg, flag = null, flagFirst = false, { row = ROW, maxW = Infinity, measure } = {}) {
  const fontOf = (px) => `bold ${px}px Helvetica, Arial, "Liberation Sans", sans-serif`;
  let px = Math.round(row * CAP / 0.72), font = fontOf(px);
  let tw = Math.ceil(measure(font, reg)), fh = row * CAP, fw = flag ? fh * 1.9 : 0, gap = flag ? row * 0.35 : 0;
  let W = Math.ceil(tw + fw + gap + 8);
  if (W > maxW) { const k = maxW / W; px = Math.floor(px * k); fh *= k; fw *= k; gap *= k; font = fontOf(px); tw = Math.ceil(measure(font, reg)); W = Math.ceil(tw + fw + gap + 8); }
  const flagW = flag ? fh * (flag === 'MX' ? 7 / 4 : 19 / 10) : 0; const ops = [];
  const line = (y0, flagLeft, mirror) => {
    let x = 4; const base = y0 + row * (0.5 + CAP / 2);
    if (flag && flagLeft) { ops.push({ op: 'flag', kind: flag, x, y: base - fh, h: fh, mirror }); x += flagW + gap; }
    ops.push({ op: 'text', text: reg, x, y: base }); x += tw + gap;
    if (flag && !flagLeft) ops.push({ op: 'flag', kind: flag, x, y: base - fh, h: fh, mirror });
  };
  line(0, flagFirst, false); line(row, !flagFirst, true);
  return { font, px, w: W, h: 2 * row, aspect: W / row, ops };
}
export function drawRegistration(ctx, L, x0 = 0, y0 = 0) {
  ctx.font = L.font; ctx.textBaseline = 'alphabetic';
  for (const o of L.ops) {
    if (o.op === 'flag') drawFlag(ctx, o.kind, x0 + o.x, y0 + o.y, o.h, o.mirror);
    else { ctx.fillStyle = '#000000'; ctx.fillText(o.text, x0 + o.x, y0 + o.y); }
  }
}
export function registrationTexture(reg, flag = null, flagFirst = false) {
  const key = reg + '|' + (flag || '') + '|' + (flagFirst ? 1 : 0);
  if (regCache.has(key)) return regCache.get(key);
  let out = null;
  try {
    const mk = (w, h) => (typeof OffscreenCanvas !== 'undefined' ? new OffscreenCanvas(w, h) : Object.assign(document.createElement('canvas'), { width: w, height: h }));
    const m = mk(8, 8).getContext('2d'); const measure = (font, text) => { m.font = font; return m.measureText(text).width; };
    const L = registrationLayout(reg, flag, flagFirst, { measure });
    const cv = mk(L.w, L.h), ctx = cv.getContext('2d');
    ctx.clearRect(0, 0, L.w, L.h);
    drawRegistration(ctx, L);           // port side: nose on the left, the image runs nose -> tail; starboard: nose on the right (the shader flips u)
    out = { ...srgbTexture(cv), aspect: L.aspect };
  } catch (e) { out = null; }
  regCache.set(key, out);
  return out;
}
