// glTF 2.0 binary (.glb) parser and converter to hwd3d Geo data (hwd3d Phase 3, M2; new file). Node-pure: no WebGL, no
// DOM, so tools/models/test_models.mjs runs it under Node.
//
//   parseGLB(arrayBuffer | Uint8Array) -> { json, bin }            the two chunks of a .glb (glTF 2.0 spec section 4.4)
//   readAccessor(json, bin, i) -> { data: Float32Array | Uint16Array | Uint32Array, size, count }
//        component types BYTE / UNSIGNED_BYTE / SHORT / UNSIGNED_SHORT / UNSIGNED_INT / FLOAT, byteStride, sparse
//        accessors, and normalized integers (KHR_mesh_quantization, as written by pc12/cad/glb.py: SHORT positions with the
//        dequantisation in the node scale / translation, BYTE normals pre-multiplied by that scale) decoded with the
//        glTF 2.0 section 3.11 rules (c / 127, c / 32767 clamped to -1; c / 255, c / 65535)
//   convertGLB(buf, opts) -> AircraftModel   the node hierarchy (TRS or matrix), every mesh baked into the hwd3d aircraft
//        local frame AT REST (gear down, surfaces neutral, doors closed), grouped by the part that moves it, plus the
//        pivots, light anchors, origin and bounding box in that frame
//
// Frames. glTF axes as written by pc12/cad/glb.py (and by the SF50 builder, same conventions): X = butt line
// (+ starboard), Y = water line (+ up), Z = fuselage station (+ aft); metres; ground = 0 with the aircraft static on its
// gear. The hwd3d aircraft local frame (js/aircraft/placeholder.js): +x forward, +y up, +z starboard, origin = main-gear
// ground contact. The axis map local = (-Z, Y, X) is a proper rotation (det +1), so triangle winding is kept. The ORIGIN is
// measured from the geometry: the lowest points of the two main-gear wheel sets in the gear-down rest pose (their
// midpoint), not a constant; the nose-wheel contact is measured the same way (wheelbase check). opts.groundGl = a number
// (the glTF Y of the source model's own ground plane, e.g. 0 for pc12 / SF50 whose ground is "z = 0 static on the gear")
// puts the origin's height on that plane instead of the lowest tyre point: a source that sinks its tyres by a static
// deflection (pc12: axle 14.5 mm lower than the free tyre radius, pc12/model/gear.py MAIN_AXLE / MAIN_TYRE) then keeps its
// sourced heights (pc12/CLAUDE.md: height 4.26, prop clearance 0.32); contacts.*.y then report the tyre penetration.
// Model axes of pc12 (x = station aft of the datum, y = butt line, z = water line) appear in a few pivot fields (Fowler
// travel, brace A / B0 / K0 / bend; pc12/web/viewer/kinematics.js header): gl = (y, z, x), then the axis map above.
//
// AircraftModel {
//   name, asset, stats {tris, verts, parts, groups, skipped[], glazingT (OD4: vertex-weighted 1 - alpha of the glass materials)},
//   origin_gl [X, Y, Z] (the local origin in glTF coordinates), contacts {mainL, mainR, nose} (local), wheelbase, track,
//   bbox [x0, y0, z0, x1, y1, z1] (local, rest pose, included parts),
//   parts [{ id, name, group, parent (index | -1), node (glTF node index), pivot (local frame, see convertPivot) | null,
//            mover (index of the part whose pivot moves this part's geometry: itself, a pivoted ancestor, or -1 = static),
//            tris, extras }],
//   groups [{ key (part id of the mover or 'static'; with opts.groupBy 'part': the part id), mover (part index | -1),
//             part (with groupBy 'part'), opaque: GeoData | null, glass: GeoData | null, bbox }]   GeoData = { pos, nrm, col, extra, uv, idx, bbox } exactly as js/geom.js Geo.data() returns,
//   lights { navL, navR, tail, beaconTop, beaconBot, strobeL, strobeR, strobeTail, landL, landR, taxi: { p: [x, y, z], part,
//            src } | null; plus any other kind a node names in extras.light (e.g. the SF50's iceLight), kept, not drawn },
//   regPanels [{ part, mover, centre, normal, up, textDir, length, height, note }] (blank registration areas, local frame;
//            D1: never filled by this module),
//   materials [{ name, base [r, g, b, a], rough, metal, blend, cls, (when opts.look replaced the factor: baseGlb = the file's, palette) }],
//   partIndex Map id -> index
// }
// Material channel (js/shaders/objects.js OBJ_FS): per-vertex colour = baseColorFactor (linear RGB, alpha) x COLOR_0, and
// ext = [roughness, metallic, mat id, emissive]; mat id 0 = the plain PBR path of the obj shader (opts.matId can map a
// material to another id). Alpha-blended materials (alphaMode BLEND) go to the `glass` Geo of their group.

import { Kinematics, DEFAULT_STATE } from './kinematics.js';

const CT = { 5120: [1, Int8Array, 127], 5121: [1, Uint8Array, 255], 5122: [2, Int16Array, 32767], 5123: [2, Uint16Array, 65535], 5125: [4, Uint32Array, 0], 5126: [4, Float32Array, 0] };
const NCOMP = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4, MAT2: 4, MAT3: 9, MAT4: 16 };

export function parseGLB(buf) {
  const u8 = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
  const dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength);
  if (dv.getUint32(0, true) !== 0x46546c67) throw new Error('not a glb (magic)');
  if (dv.getUint32(4, true) !== 2) throw new Error('glb version ' + dv.getUint32(4, true) + ' (2 expected)');
  const total = dv.getUint32(8, true); let off = 12, json = null, bin = null;
  while (off + 8 <= Math.min(total, u8.byteLength)) {
    const len = dv.getUint32(off, true), type = dv.getUint32(off + 4, true); const body = u8.subarray(off + 8, off + 8 + len);
    if (type === 0x4e4f534a) json = JSON.parse(new TextDecoder().decode(body));
    else if (type === 0x004e4942) bin = body;
    off += 8 + len;
  }
  if (!json) throw new Error('glb without a JSON chunk');
  return { json, bin };
}

function bufferViewBytes(json, bin, bvi) {
  const bv = json.bufferViews[bvi]; if (bv.buffer !== 0 || !bin) throw new Error('only the embedded GLB buffer is supported');
  return { u8: bin.subarray(bv.byteOffset || 0, (bv.byteOffset || 0) + bv.byteLength), stride: bv.byteStride || 0 };
}
// decode `count` x `size` components starting at byte `base` of `u8` (row stride `stride`) into `out` (Float32 / Uint32)
function decode(u8, stride, ctype, size, count, normalized, out) {
  const [bytes, , nmax] = CT[ctype]; const dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength); const st = stride || bytes * size;
  const get = { 5120: (o) => dv.getInt8(o), 5121: (o) => dv.getUint8(o), 5122: (o) => dv.getInt16(o, true), 5123: (o) => dv.getUint16(o, true), 5125: (o) => dv.getUint32(o, true), 5126: (o) => dv.getFloat32(o, true) }[ctype];
  const signed = ctype === 5120 || ctype === 5122;
  for (let i = 0; i < count; i++) for (let k = 0; k < size; k++) {
    let v = get(i * st + k * bytes);
    if (normalized && nmax) v = signed ? Math.max(v / nmax, -1) : v / nmax;
    out[i * size + k] = v;
  }
  return out;
}
export function readAccessor(json, bin, i) {
  const a = json.accessors[i]; const size = NCOMP[a.type]; if (!size) throw new Error('accessor type ' + a.type);
  if (!CT[a.componentType]) throw new Error('componentType ' + a.componentType);
  const isIndex = !a.normalized && (a.componentType === 5121 || a.componentType === 5123 || a.componentType === 5125) && size === 1;
  const out = isIndex ? new Uint32Array(a.count * size) : new Float32Array(a.count * size);
  if (a.bufferView != null) { const { u8, stride } = bufferViewBytes(json, bin, a.bufferView); decode(u8.subarray(a.byteOffset || 0), stride, a.componentType, size, a.count, !!a.normalized, out); }
  if (a.sparse) {
    const s = a.sparse, ib = bufferViewBytes(json, bin, s.indices.bufferView), vb = bufferViewBytes(json, bin, s.values.bufferView);
    const idx = decode(ib.u8.subarray(s.indices.byteOffset || 0), 0, s.indices.componentType, 1, s.count, false, new Uint32Array(s.count));
    const val = decode(vb.u8.subarray(s.values.byteOffset || 0), 0, a.componentType, size, s.count, !!a.normalized, new Float32Array(s.count * size));
    for (let j = 0; j < s.count; j++) for (let k = 0; k < size; k++) out[idx[j] * size + k] = val[j * size + k];
  }
  return { data: out, size, count: a.count };
}

// ---------------------------------------------------------------- 4x4 column-major (Float64: the bake is done once)
const M = {
  id: () => { const m = new Float64Array(16); m[0] = m[5] = m[10] = m[15] = 1; return m; },
  mul(a, b) { const o = new Float64Array(16); for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) { let s = 0; for (let k = 0; k < 4; k++) s += a[k * 4 + r] * b[c * 4 + k]; o[c * 4 + r] = s; } return o; },
  trs(t, q, s) {
    const [x, y, z, w] = q || [0, 0, 0, 1], [sx, sy, sz] = s || [1, 1, 1], o = M.id();
    o[0] = (1 - 2 * (y * y + z * z)) * sx; o[1] = 2 * (x * y + z * w) * sx; o[2] = 2 * (x * z - y * w) * sx;
    o[4] = 2 * (x * y - z * w) * sy; o[5] = (1 - 2 * (x * x + z * z)) * sy; o[6] = 2 * (y * z + x * w) * sy;
    o[8] = 2 * (x * z + y * w) * sz; o[9] = 2 * (y * z - x * w) * sz; o[10] = (1 - 2 * (x * x + y * y)) * sz;
    if (t) { o[12] = t[0]; o[13] = t[1]; o[14] = t[2]; } return o;
  },
  pt: (m, p) => [m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12], m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13], m[2] * p[0] + m[6] * p[1] + m[10] * p[2] + m[14]],
  dir: (m, p) => [m[0] * p[0] + m[4] * p[1] + m[8] * p[2], m[1] * p[0] + m[5] * p[1] + m[9] * p[2], m[2] * p[0] + m[6] * p[1] + m[10] * p[2]],
  // inverse transpose of the upper 3x3 (normal matrix), as a 3x3 row-major array
  normal3(m) {
    const a = m[0], b = m[4], c = m[8], d = m[1], e = m[5], f = m[9], g = m[2], h = m[6], i = m[10];
    const A = e * i - f * h, B = -(d * i - f * g), C = d * h - e * g, det = a * A + b * B + c * C || 1;
    // inverse = adj / det; inverse transpose = cofactor / det
    return [A / det, B / det, C / det, -(b * i - c * h) / det, (a * i - c * g) / det, -(a * h - b * g) / det, (b * f - c * e) / det, -(a * f - c * d) / det, (a * e - b * d) / det];
  },
};
export const nodeMatrix = (n) => n.matrix ? Float64Array.from(n.matrix) : M.trs(n.translation, n.rotation, n.scale);

// ---------------------------------------------------------------- frames
/** glTF (X starboard, Y up, Z aft) vector -> hwd3d local axes (+x forward, +y up, +z starboard). */
export const glToLocalDir = (v) => [-v[2], v[1], v[0]];
/** pc12 model axes (x station aft, y butt line starboard, z water line up) vector -> glTF axes. */
export const modelToGl = (v) => [v[1], v[2], v[0]];
const norm = (v) => { const l = Math.hypot(v[0], v[1], v[2]) || 1; return [v[0] / l, v[1] / l, v[2] / l]; };

// Pivot fields stored in pc12 MODEL axes (pc12/web/viewer/kinematics.js): flap `travel`, brace `A`, `B0`, `K0`, `bend`.
// A pivot may say `axes: 'gl'` to have them read as glTF axes instead.
const MODEL_AXIS_POINTS = ['A', 'B0', 'K0'], MODEL_AXIS_DIRS = ['travel', 'bend'];
function convertPivot(pv, toLocalPt, nodeOriginGl) {
  const o = { ...pv, raw: pv };
  const og = pv.origin || nodeOriginGl;
  o.origin = toLocalPt(og); o.originGl = og;
  if (pv.axis) o.axis = norm(glToLocalDir(pv.axis));
  const fromModel = pv.axes !== 'gl';
  for (const k of MODEL_AXIS_POINTS) if (Array.isArray(pv[k])) o[k] = toLocalPt(fromModel ? modelToGl(pv[k]) : pv[k]);
  for (const k of MODEL_AXIS_DIRS) if (Array.isArray(pv[k])) o[k] = glToLocalDir(fromModel ? modelToGl(pv[k]) : pv[k]);
  if (nodeOriginGl && pv.origin) o.originMismatch = Math.hypot(pv.origin[0] - nodeOriginGl[0], pv.origin[1] - nodeOriginGl[1], pv.origin[2] - nodeOriginGl[2]);
  return o;
}

// ---------------------------------------------------------------- materials
const GLASS_RE = /glass|windshield|canopy|window/i;
function materialInfo(m, opts) {
  const pbr = (m && m.pbrMetallicRoughness) || {};
  const base = (pbr.baseColorFactor || [1, 1, 1, 1]).slice(); if (base.length === 3) base.push(1);
  const info = { name: (m && m.name) || '', base, rough: pbr.roughnessFactor ?? 1, metal: pbr.metallicFactor ?? 1,
    emis: m && m.emissiveFactor ? Math.max(...m.emissiveFactor) : 0, blend: !!m && m.alphaMode === 'BLEND', doubleSided: !!(m && m.doubleSided),
    textured: !!(pbr.baseColorTexture || pbr.metallicRoughnessTexture || (m && m.normalTexture)), extras: (m && m.extras) || null };
  info.cls = info.blend ? (GLASS_RE.test(info.name) ? 'glass' : 'clear') : /^tire|^tyre/i.test(info.name) ? 'tyre' : /^light_|^lens$/i.test(info.name) ? 'light' : 'opaque';
  info.matId = (opts.matId && opts.matId(info)) || 0;
  if (opts.look) Object.assign(info, opts.look(info) || {});
  return info;
}

// ---------------------------------------------------------------- Geo accumulation (same layout as js/geom.js Geo.data())
class Acc {
  constructor() { this.pos = []; this.nrm = []; this.col = []; this.ext = []; this.idx = []; this.mat = []; this.nv = 0; }
  data() {
    const pos = new Float32Array(this.pos), b = [1e9, 1e9, 1e9, -1e9, -1e9, -1e9];
    for (let i = 0; i < pos.length; i += 3) for (let k = 0; k < 3; k++) { b[k] = Math.min(b[k], pos[i + k]); b[k + 3] = Math.max(b[k + 3], pos[i + k]); }
    return { pos, nrm: new Float32Array(this.nrm), col: new Float32Array(this.col), extra: new Float32Array(this.ext), uv: new Float32Array(this.nv * 2), idx: new Uint32Array(this.idx), bbox: b,
      mat: Uint16Array.from(this.mat) };   // per-vertex material index into AircraftModel.materials (not a GPU attribute)
  }
}

/**
 * convertGLB(buf, { name, exclude: [part ids], matId(info) -> id, look(info) -> overrides, originGl: [X, Y, Z] (override:
 * skip the wheel-contact measurement), glassToOpaque: false, groupBy: 'mover' | 'part' })
 */
export function convertGLB(buf, opts = {}) {
  const { json, bin } = parseGLB(buf);
  if ((json.extensionsRequired || []).some(e => e !== 'KHR_mesh_quantization')) throw new Error('unsupported required extension ' + json.extensionsRequired.join(','));
  const nodes = json.nodes || [], exclude = new Set(opts.exclude || []);
  const mats = (json.materials || []).map(m => materialInfo(m, opts)); const defMat = materialInfo(null, opts);
  // ---- hierarchy: world (rest) matrices, the part each node belongs to
  const parentOf = new Int32Array(nodes.length).fill(-1);
  nodes.forEach((n, i) => (n.children || []).forEach(c => { parentOf[c] = i; }));
  const scene = json.scenes ? json.scenes[json.scene || 0] : { nodes: nodes.map((_, i) => i).filter(i => parentOf[i] < 0) };
  const world = new Array(nodes.length).fill(null), partOfNode = new Int32Array(nodes.length).fill(-1);
  const parts = [], partIndex = new Map();
  const visit = (ni, Wp, partP) => {
    const n = nodes[ni]; const W = M.mul(Wp, nodeMatrix(n)); world[ni] = W;
    let p = partP; const ex = n.extras || {};
    if (ex.part) {
      p = parts.length; partIndex.set(ex.part, p);
      parts.push({ id: ex.part, name: ex.name || ex.part, group: ex.group || null, parent: partP, node: ni, pivotRaw: ex.pivot || null, extras: ex,
        excluded: exclude.has(ex.part) || (partP >= 0 && parts[partP].excluded), originGl: [W[12], W[13], W[14]], tris: 0 });
    }
    partOfNode[ni] = p;
    for (const c of n.children || []) visit(c, W, p);
  };
  for (const r of scene.nodes) visit(r, M.id(), -1);
  // the mover of a part: itself when it has a pivot, else the nearest pivoted ancestor, else -1 (static airframe)
  for (const p of parts) { let q = parts.indexOf(p); p.mover = -1; while (q >= 0) { if (parts[q].pivotRaw) { p.mover = q; break; } q = parts[q].parent; } }

  // ---- read every mesh primitive once, in glTF world coordinates (rest pose)
  const prims = [];
  nodes.forEach((n, ni) => {
    if (n.mesh == null || !world[ni]) return;
    const pi = partOfNode[ni]; if (pi >= 0 && parts[pi].excluded) return;
    const W = world[ni], N3 = M.normal3(W);
    for (const pr of json.meshes[n.mesh].primitives) {
      if ((pr.mode ?? 4) !== 4) continue;   // triangles only (pc12 / SF50 write mode 4)
      const P = readAccessor(json, bin, pr.attributes.POSITION), Nn = pr.attributes.NORMAL != null ? readAccessor(json, bin, pr.attributes.NORMAL) : null;
      const C0 = pr.attributes.COLOR_0 != null ? readAccessor(json, bin, pr.attributes.COLOR_0) : null;
      const I = pr.indices != null ? readAccessor(json, bin, pr.indices).data : Uint32Array.from({ length: P.count }, (_, i) => i);
      const nv = P.count, pos = new Float64Array(nv * 3), nrm = new Float32Array(nv * 3);
      for (let i = 0; i < nv; i++) {
        const p = M.pt(W, [P.data[i * 3], P.data[i * 3 + 1], P.data[i * 3 + 2]]); pos[i * 3] = p[0]; pos[i * 3 + 1] = p[1]; pos[i * 3 + 2] = p[2];
        if (Nn) { const a = Nn.data[i * 3], b = Nn.data[i * 3 + 1], c = Nn.data[i * 3 + 2]; const v = norm([N3[0] * a + N3[1] * b + N3[2] * c, N3[3] * a + N3[4] * b + N3[5] * c, N3[6] * a + N3[7] * b + N3[8] * c]); nrm[i * 3] = v[0]; nrm[i * 3 + 1] = v[1]; nrm[i * 3 + 2] = v[2]; }
      }
      if (!Nn) {   // flat normals from the faces (accumulated per vertex)
        for (let t = 0; t < I.length; t += 3) { const a = I[t] * 3, b = I[t + 1] * 3, c = I[t + 2] * 3; const u = [pos[b] - pos[a], pos[b + 1] - pos[a + 1], pos[b + 2] - pos[a + 2]], v = [pos[c] - pos[a], pos[c + 1] - pos[a + 1], pos[c + 2] - pos[a + 2]];
          const n3 = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]; for (const k of [a, b, c]) { nrm[k] += n3[0]; nrm[k + 1] += n3[1]; nrm[k + 2] += n3[2]; } }
        for (let i = 0; i < nv; i++) { const v = norm([nrm[i * 3], nrm[i * 3 + 1], nrm[i * 3 + 2]]); nrm.set(v, i * 3); }
      }
      prims.push({ part: pi, node: ni, mat: pr.material != null ? mats[pr.material] : defMat, matIndex: pr.material != null ? pr.material : mats.length, pos, nrm, col0: C0, idx: I, nv });
      if (pi >= 0) parts[pi].tris += I.length / 3;
    }
  });

  // ---- origin: main-gear ground contact (gear-down rest pose), measured from the wheels
  const gearParts = parts.map((p, i) => i).filter(i => parts[i].pivotRaw && parts[i].pivotRaw.kind === 'gear');
  const subtreeOf = (pi) => { const s = new Set([pi]); let grow = true; while (grow) { grow = false; parts.forEach((p, i) => { if (!s.has(i) && s.has(p.parent)) { s.add(i); grow = true; } }); } return s; };
  const lowest = (set, tyreOnly) => {   // lowest vertices of the parts in `set` (tyre materials preferred) -> contact point
    let minY = Infinity; const pts = [];
    for (const pr of prims) { if (!set.has(pr.part) || (tyreOnly && pr.mat.cls !== 'tyre')) continue; for (let i = 0; i < pr.nv; i++) if (pr.pos[i * 3 + 1] < minY) minY = pr.pos[i * 3 + 1]; }
    if (!isFinite(minY)) return null;
    for (const pr of prims) { if (!set.has(pr.part) || (tyreOnly && pr.mat.cls !== 'tyre')) continue; for (let i = 0; i < pr.nv; i++) if (pr.pos[i * 3 + 1] < minY + 0.004) pts.push([pr.pos[i * 3], pr.pos[i * 3 + 1], pr.pos[i * 3 + 2]]); }
    const c = [0, 0, 0]; for (const p of pts) for (let k = 0; k < 3; k++) c[k] += p[k] / pts.length; c[1] = minY; return c;
  };
  let contactsGl = null;
  if (gearParts.length) {
    const g = gearParts.map(i => ({ i, c: lowest(subtreeOf(i), true) || lowest(subtreeOf(i), false) })).filter(o => o.c);
    // nose (or tail) unit: the one nearest the centreline; mains: the outboard pair
    g.sort((a, b) => Math.abs(a.c[0]) - Math.abs(b.c[0]));
    const centre = g.length >= 3 ? g[0] : null, mains = (centre ? g.slice(1) : g).sort((a, b) => a.c[0] - b.c[0]);
    if (mains.length >= 2) contactsGl = { mainL: mains[0].c, mainR: mains[mains.length - 1].c, nose: centre ? centre.c : null, ids: { mainL: parts[mains[0].i].id, mainR: parts[mains[mains.length - 1].i].id, nose: centre ? parts[centre.i].id : null } };
  }
  if (!contactsGl) {   // fixed gear / no gear pivots: lowest tyre vertices on each side
    const all = new Set(parts.map((_, i) => i)); all.add(-1);
    const side = (s) => { let minY = Infinity, pts = []; for (const pr of prims) { if (pr.mat.cls !== 'tyre') continue; for (let i = 0; i < pr.nv; i++) { const x = pr.pos[i * 3]; if (s * x > 0.3 && pr.pos[i * 3 + 1] < minY) minY = pr.pos[i * 3 + 1]; } }
      for (const pr of prims) { if (pr.mat.cls !== 'tyre') continue; for (let i = 0; i < pr.nv; i++) { const x = pr.pos[i * 3]; if (s * x > 0.3 && pr.pos[i * 3 + 1] < minY + 0.004) pts.push([x, pr.pos[i * 3 + 1], pr.pos[i * 3 + 2]]); } }
      if (!pts.length) return null; const c = [0, 0, 0]; for (const p of pts) for (let k = 0; k < 3; k++) c[k] += p[k] / pts.length; c[1] = minY; return c; };
    const l = side(-1), r = side(1); if (l && r) contactsGl = { mainL: l, mainR: r, nose: null, ids: {} };
  }
  const originGl = opts.originGl || (contactsGl ? [(contactsGl.mainL[0] + contactsGl.mainR[0]) / 2, (contactsGl.mainL[1] + contactsGl.mainR[1]) / 2, (contactsGl.mainL[2] + contactsGl.mainR[2]) / 2] : null);
  if (!originGl) throw new Error('no main-gear wheels found to set the origin (pass opts.originGl)');
  if (!opts.originGl && typeof opts.groundGl === 'number') originGl[1] = opts.groundGl;   // the source's ground plane (header)
  const toLocalPt = (g) => [-(g[2] - originGl[2]), g[1] - originGl[1], g[0] - originGl[0]];

  // ---- pivots in the local frame
  for (const p of parts) p.pivot = p.pivotRaw ? convertPivot(p.pivotRaw, toLocalPt, p.originGl) : null;

  // ---- bake into groups (one per mover + 'static'), opaque and glass separately
  // groupBy 'mover' (default, the runtime: one group per moving part + 'static') or 'part' (tests: one group per part)
  const groups = new Map(); const byPart = opts.groupBy === 'part';
  const getG = (mv, pi) => { const k = byPart ? (pi >= 0 ? parts[pi].id : 'root') : mv < 0 ? 'static' : parts[mv].id; if (!groups.has(k)) groups.set(k, { key: k, mover: mv, part: byPart ? pi : -1, opaque: new Acc(), glass: new Acc() }); return groups.get(k); };
  let tris = 0, verts = 0, glzW = 0, glzT = 0;
  for (const pr of prims) {
    const mv = pr.part >= 0 ? parts[pr.part].mover : -1; const G = getG(mv, pr.part);
    const m = pr.mat; const toGlass = m.blend && !opts.glassToOpaque; const A = toGlass ? G.glass : G.opaque;
    const base = A.nv, b = m.base;
    // OD4: material id per part (opts.partMatId(matId, partId): e.g. every plain material of an interior part -> the cabin
    // id), and the glazing transmission (1 - alpha of the 'glass' materials, vertex-weighted): the light that reaches the cabin
    // (OD4 iteration 4: the material record is passed too, so a part rule can leave blended materials alone)
    const mid = opts.partMatId ? opts.partMatId(m.matId, pr.part >= 0 ? parts[pr.part].id : null, m) : m.matId;
    if (m.cls === 'glass') { glzW += pr.nv; glzT += pr.nv * (1 - b[3]); }
    for (let i = 0; i < pr.nv; i++) {
      const l = toLocalPt([pr.pos[i * 3], pr.pos[i * 3 + 1], pr.pos[i * 3 + 2]]); A.pos.push(l[0], l[1], l[2]);
      const n = glToLocalDir([pr.nrm[i * 3], pr.nrm[i * 3 + 1], pr.nrm[i * 3 + 2]]); A.nrm.push(n[0], n[1], n[2]);
      let c = [b[0], b[1], b[2], b[3]]; if (pr.col0) { const s = pr.col0.size; for (let k = 0; k < s; k++) c[k] *= pr.col0.data[i * s + k]; }
      if (m.blend && opts.glassToOpaque) c[3] = 1;
      A.col.push(c[0], c[1], c[2], c[3]); A.ext.push(m.rough, m.metal, mid, m.emis); A.mat.push(pr.matIndex);
    }
    for (let t = 0; t < pr.idx.length; t++) A.idx.push(base + pr.idx[t]);
    A.nv += pr.nv; tris += pr.idx.length / 3; verts += pr.nv;
  }
  const outGroups = [...groups.values()].map(g => { const o = g.opaque.nv ? g.opaque.data() : null, gl = g.glass.nv ? g.glass.data() : null;
    const bb = [o, gl].filter(Boolean).reduce((a, d) => [Math.min(a[0], d.bbox[0]), Math.min(a[1], d.bbox[1]), Math.min(a[2], d.bbox[2]), Math.max(a[3], d.bbox[3]), Math.max(a[4], d.bbox[4]), Math.max(a[5], d.bbox[5])], [1e9, 1e9, 1e9, -1e9, -1e9, -1e9]);
    return { key: g.key, mover: g.mover, part: g.part, opaque: o, glass: gl, bbox: bb }; });
  const bbox = outGroups.reduce((a, g) => [Math.min(a[0], g.bbox[0]), Math.min(a[1], g.bbox[1]), Math.min(a[2], g.bbox[2]), Math.max(a[3], g.bbox[3]), Math.max(a[4], g.bbox[4]), Math.max(a[5], g.bbox[5])], [1e9, 1e9, 1e9, -1e9, -1e9, -1e9]);

  // ---- light anchors
  const lights = lightAnchors(prims, parts, toLocalPt, partIndex, nodes, world, opts.lightAnchors);
  for (const k in lights) if (lights[k]) lights[k].occ = lampShape(lights[k], prims, parts, toLocalPt);
  // ---- registration panels (SF50 builder: part extras info.reg_panel {centre, normal, up, length, height}, model axes):
  // blank areas the runtime may fill for aircraft not flagged LADD / PIA (D1); never filled here
  const regPanels = [];
  parts.forEach((pt) => { const r = pt.extras && pt.extras.info && pt.extras.info.reg_panel; if (!r || pt.excluded || !Array.isArray(r.centre)) return;
    const g = r.axes === 'gl'; const P = (v) => toLocalPt(g ? v : modelToGl(v)), Dd = (v) => norm(glToLocalDir(g ? v : modelToGl(v)));
    // every field the builder wrote is kept (fix round 1: text_dir was dropped); vectors are mapped to the local frame
    regPanels.push({ part: pt.id, mover: pt.mover, centre: P(r.centre), normal: r.normal ? Dd(r.normal) : null, up: r.up ? Dd(r.up) : null,
      textDir: r.text_dir ? Dd(r.text_dir) : null, length: r.length ?? null, height: r.height ?? null, note: r.note ?? null }); });
  const contacts = contactsGl ? { mainL: toLocalPt(contactsGl.mainL), mainR: toLocalPt(contactsGl.mainR), nose: contactsGl.nose ? toLocalPt(contactsGl.nose) : null, parts: contactsGl.ids } : null;
  return {
    name: opts.name || (json.asset && json.asset.generator) || 'glb', asset: json.asset || {}, originGl, contacts,
    wheelbase: contacts && contacts.nose ? contacts.nose[0] : null, track: contacts ? contacts.mainR[2] - contacts.mainL[2] : null,
    bbox, parts: parts.map(({ pivotRaw, excluded, ...p }) => ({ ...p, excluded })), partIndex, groups: outGroups, lights, regPanels,
    materials: [...mats, defMat].map(m => ({ name: m.name, base: m.base, rough: m.rough, metal: m.metal, blend: m.blend, cls: m.cls, matId: m.matId, textured: m.textured, ...(m.baseGlb ? { baseGlb: m.baseGlb, palette: m.palette } : {}) })),
    stats: { tris, verts, parts: parts.length, groups: outGroups.length, excluded: parts.filter(p => p.excluded).map(p => p.id), textured: mats.filter(m => m.textured).map(m => m.name),
      glazingT: glzW ? glzT / glzW : null },
  };
}

// Light anchors. (0) opts.lightAnchors { kind: { p: [x, y, z] MODEL axes (or axes: 'gl'), part: part id | null, src } }: anchors
// the hwd3d registry adds for lamps the source model does not draw (js/aircraft/models.js; each one cites its basis);
// (1) Node extras `light: '<kind>'` or `{ kind }` (the anchor is the node origin; kinds outside KINDS are kept too); (1b) part extras
// `light_anchors` / `info.light_anchors` (SF50 builder); (2) otherwise clusters of the light lens materials: light_red / light_green / light_white
// (pc12/model/details.py: red = port wing-tip nav + upper + lower beacon; green = starboard nav; white = the two wing-tip
// strobes + the tail light) and `lens` on a gear part (the nose-strut landing / taxi lamp, pc12/model/gear.py).
// strobeTail: the third anti-collision light of a type with a tail strobe (SF50 AFM: anti-collision lights 3); drawn by
// js/aircraft/detailed.js in phase with the wing-tip strobes. Other kinds (iceLight ...) are kept, not drawn.
export const KINDS = ['navL', 'navR', 'tail', 'beaconTop', 'beaconBot', 'strobeL', 'strobeR', 'strobeTail', 'landL', 'landR', 'taxi'];
function lightAnchors(prims, parts, toLocalPt, partIndex, nodes, world, extra) {
  const L = Object.fromEntries(KINDS.map(k => [k, null]));
  // (0) registry anchors (model axes unless axes: 'gl')
  for (const [kind, a] of Object.entries(extra || {})) { if (!a || !Array.isArray(a.p)) continue; const pi = a.part != null && partIndex.has(a.part) ? partIndex.get(a.part) : -1;
    L[kind] = { p: toLocalPt(a.axes === 'gl' ? a.p : modelToGl(a.p)), part: pi >= 0 ? parts[pi].mover : -1, src: 'registry (js/aircraft/models.js): ' + (a.src || '?') }; }
  // (1) explicit anchors
  nodes.forEach((n, ni) => {
    const e = n.extras && n.extras.light; if (!e || !world[ni]) return; const kind = typeof e === 'string' ? e : e.kind; if (!kind || L[kind]) return;
    let pi = -1; for (let q = ni; q >= 0 && pi < 0; q = nodes.findIndex(m => (m.children || []).includes(q))) { const ex = nodes[q].extras; if (ex && ex.part && partIndex.has(ex.part)) pi = partIndex.get(ex.part); }
    const W = world[ni]; L[kind] = { p: toLocalPt([W[12], W[13], W[14]]), part: pi >= 0 ? parts[pi].mover : -1, src: 'node extras' };
  });
  // (1b) part extras `light_anchors` (or `info.light_anchors`): { kind: { p: [x, y, z] in MODEL axes (or glTF with
  //      axes: 'gl'), src } } - the SF50 builder's form (tools/models/sf50); the anchor rides on that part's mover
  parts.forEach((pt, pi) => {
    const A = (pt.extras && (pt.extras.light_anchors || (pt.extras.info && pt.extras.info.light_anchors))) || null; if (!A || pt.excluded) return;
    for (const [kind, a] of Object.entries(A)) { if (L[kind] || !a || !Array.isArray(a.p)) continue;
      L[kind] = { p: toLocalPt(a.axes === 'gl' ? a.p : modelToGl(a.p)), part: pt.mover, src: 'part extras light_anchors' + (a.src ? ' (' + a.src + ')' : '') }; }
  });
  // (2) lens clusters (single linkage, 0.25 m)
  const clusters = (sel) => {
    const out = [];
    for (const pr of prims) { if (!sel(pr)) continue;
      for (let i = 0; i < pr.nv; i++) { const p = toLocalPt([pr.pos[i * 3], pr.pos[i * 3 + 1], pr.pos[i * 3 + 2]]);
        let c = out.find(c => Math.hypot(c.p[0] / c.n - p[0], c.p[1] / c.n - p[1], c.p[2] / c.n - p[2]) < 0.25 && c.part === pr.part);
        if (!c) { c = { p: [0, 0, 0], n: 0, part: pr.part }; out.push(c); } c.p[0] += p[0]; c.p[1] += p[1]; c.p[2] += p[2]; c.n++; } }
    return out.map(c => ({ p: c.p.map(v => v / c.n), part: c.part >= 0 ? parts[c.part].mover : -1 }));
  };
  const set = (k, c, src) => { if (!L[k] && c) L[k] = { p: c.p, part: c.part, src }; };
  const red = clusters(pr => pr.mat.name === 'light_red'), green = clusters(pr => pr.mat.name === 'light_green'), white = clusters(pr => pr.mat.name === 'light_white');
  const byZ = (a) => a.slice().sort((u, v) => u.p[2] - v.p[2]);
  const tipsR = red.filter(c => Math.abs(c.p[2]) > 1.5), midR = red.filter(c => Math.abs(c.p[2]) <= 1.5).sort((u, v) => v.p[1] - u.p[1]);
  set('navL', byZ(tipsR)[0], 'lens cluster light_red (port tip)'); set('navR', byZ(green.filter(c => Math.abs(c.p[2]) > 1.5)).pop(), 'lens cluster light_green (starboard tip)');
  set('beaconTop', midR[0], 'lens cluster light_red (centreline, upper)'); if (midR.length > 1) set('beaconBot', midR[midR.length - 1], 'lens cluster light_red (centreline, lower)');
  const tipsW = byZ(white.filter(c => Math.abs(c.p[2]) > 1.5)), midW = white.filter(c => Math.abs(c.p[2]) <= 1.5).sort((u, v) => u.p[0] - v.p[0]);
  set('strobeL', tipsW[0], 'lens cluster light_white (port tip)'); if (tipsW.length > 1) set('strobeR', tipsW[tipsW.length - 1], 'lens cluster light_white (starboard tip)');
  set('tail', midW[0], 'lens cluster light_white (aft-most)');
  const lamps = clusters(pr => pr.mat.name === 'lens' && pr.part >= 0 && parts[pr.part].pivotRaw && /gear/.test(parts[pr.part].pivotRaw.kind));
  if (lamps.length) { const c = lamps.sort((u, v) => v.p[0] - u.p[0])[0]; set('taxi', c, 'lens on the nose gear (strut lamp)'); set('landL', { p: [c.p[0], c.p[1], c.p[2] - 0.02], part: c.part }, 'lens on the nose gear (strut lamp)'); set('landR', { p: [c.p[0], c.p[1], c.p[2] + 0.02], part: c.part }, 'lens on the nose gear (strut lamp)'); }
  return L;
}

// OD4 iteration 5 (review F1 / F3, docs/phase3_models.md 15.9): the lamp's OWN shape around each anchor, for the lens
// occlusion test of its light sprite (js/shaders/sprites.js lensVisible, js/aircraft/detailed.js lightSprites):
//   occ { c: [x, y, z] (local; the shape centre, not always the anchor), ax: [3 unit axes, local], h: [3 half extents, m],
//         shape: 'ellipsoid' | 'box', geom: true (the lamp surface is opaque, so it is in the scene depth) | false,
//         face: { n: [x, y, z] local unit, cos } | null (a one-sided lamp patch: hidden where dot(toCam, n) <= cos), mat, n, cover }
// The lamp = the vertices of one lamp material connected to the anchor: seed = the vertex of an opaque lamp material ('light'
// class: light_red / light_green / light_white) nearest to the anchor within LAMP_SEED, grown by single linkage (LAMP_LINK)
// over vertices of the same material on the same mover within LAMP_REACH; failing that the same with a clear lens cover
// ('clear' class: pc12's nose-strut 'lens'), which is blended and NOT in the depth (geom false); failing that (a registry
// anchor with no lamp geometry: the PC-12 wing landing lights) a sphere of LAMP_VIRTUAL_R around the anchor (geom false).
// Fit: principal axes of the vertices, the bounding box in that frame; an ellipsoid through the farthest vertex when it is
// smaller than the box (pc12/model/details.py lens(): superellipsoids, e = 0.9 - nearly ellipsoids), else the box (the
// SF50's lamp patches under their lens covers, tools/models/sf50/sf50_wing.py); + LAMP_MARGIN. Measured per anchor
// (docs/phase3_models.md 15.9); the shapes are inferred from the geometry, not sourced [inf].
const LAMP_SEED = 0.08, LAMP_LINK = 0.06, LAMP_REACH = 0.35, LAMP_COVER = 0.02, LAMP_PATCH = 0.5, LAMP_VIRTUAL_R = 0.02, LAMP_MARGIN = 0.002, LAMP_MIN_H = 0.003;
function jacobi3(A) {   // symmetric 3 x 3 -> { vals, vecs: unit eigenvectors }
  const a = A.map(r => r.slice()), v = [[1, 0, 0], [0, 1, 0], [0, 0, 1]];
  for (let sweep = 0; sweep < 40; sweep++) {
    if (Math.abs(a[0][1]) + Math.abs(a[0][2]) + Math.abs(a[1][2]) < 1e-22) break;
    for (const [p, q] of [[0, 1], [0, 2], [1, 2]]) {
      if (Math.abs(a[p][q]) < 1e-24) continue;
      const th = (a[q][q] - a[p][p]) / (2 * a[p][q]), t = (th >= 0 ? 1 : -1) / (Math.abs(th) + Math.sqrt(th * th + 1)), c = 1 / Math.sqrt(t * t + 1), s = t * c;
      for (let k = 0; k < 3; k++) { const kp = a[k][p], kq = a[k][q]; a[k][p] = c * kp - s * kq; a[k][q] = s * kp + c * kq; }
      for (let k = 0; k < 3; k++) { const pk = a[p][k], qk = a[q][k]; a[p][k] = c * pk - s * qk; a[q][k] = s * pk + c * qk; }
      for (let k = 0; k < 3; k++) { const kp = v[k][p], kq = v[k][q]; v[k][p] = c * kp - s * kq; v[k][q] = s * kp + c * kq; }
    }
  }
  return { vals: [a[0][0], a[1][1], a[2][2]], vecs: [0, 1, 2].map(j => norm([v[0][j], v[1][j], v[2][j]])) };
}
export function lampShape(a, prims, parts, toLocalPt) {
  const moverOf = (pr) => (pr.part >= 0 ? parts[pr.part].mover : -1);
  const localDir = (N, i) => [-N[i * 3 + 2], N[i * 3 + 1], N[i * 3]];   // glTF -> local (the axis map of toLocalPt)
  const d3 = (u, w) => Math.hypot(u[0] - w[0], u[1] - w[1], u[2] - w[2]);
  for (const [cls, geom] of [['light', true], ['clear', false]]) {
    const V = [];
    for (const pr of prims) { if (pr.mat.cls !== cls || moverOf(pr) !== a.part) continue;
      for (let i = 0; i < pr.nv; i++) { const p = toLocalPt([pr.pos[i * 3], pr.pos[i * 3 + 1], pr.pos[i * 3 + 2]]); const r = d3(p, a.p); if (r < LAMP_REACH) V.push({ p, r, mat: pr.mat.name, n: localDir(pr.nrm, i) }); } }
    if (!V.length) continue;
    const seed = V.reduce((b, v) => (v.r < b.r ? v : b)); if (seed.r > LAMP_SEED) continue;
    const pool = V.filter(v => v.mat === seed.mat), inC = new Uint8Array(pool.length), stack = [pool.indexOf(seed)]; inC[stack[0]] = 1;
    while (stack.length) { const q = pool[stack.pop()].p; for (let j = 0; j < pool.length; j++) if (!inC[j] && d3(pool[j].p, q) < LAMP_LINK) { inC[j] = 1; stack.push(j); } }
    const P = pool.filter((_, j) => inC[j]).map(v => v.p), Nn = pool.filter((_, j) => inC[j]).map(v => v.n), nLamp = P.length;
    // the clear lens cover over an opaque lamp (SF50: the tip lens 14 / 10 mm above its lamp patches, the tail-light lens bump
    // over a lamp the tail-cone skin covers): its vertices within LAMP_COVER of the lamp join the fit, so the skin under the
    // lens (the surface the depth holds there) lies inside the shape
    let nCover = 0;
    if (geom) for (const pr of prims) { if (pr.mat.cls !== 'clear' || moverOf(pr) !== a.part) continue;
      for (let i = 0; i < pr.nv; i++) { const p = toLocalPt([pr.pos[i * 3], pr.pos[i * 3 + 1], pr.pos[i * 3 + 2]]); if (d3(p, a.p) > LAMP_REACH) continue;
        for (let j = 0; j < nLamp; j++) if (d3(p, P[j]) < LAMP_COVER) { P.push(p); Nn.push(localDir(pr.nrm, i)); nCover++; break; } } }
    const n = P.length;
    // facing: a lamp that is a one-sided patch (|mean vertex normal| > LAMP_PATCH; the SF50's lamps under their lens covers,
    // not pc12's closed lamp bodies) emits only to the side its surface faces. Seen from where no part of it faces the camera
    // (dot(toCam, n) <= -sqrt(1 - cmin^2), cmin = the smallest dot of a vertex normal with the mean one) it is hidden
    // whatever the depth says - from behind, the airframe's far skin can lie within the lamp's shape (the SF50's thin upturn)
    const nm = [0, 1, 2].map(k => Nn.reduce((s2, v) => s2 + v[k], 0) / n), nmL = Math.hypot(nm[0], nm[1], nm[2]);
    let face = null;
    if (nmL > LAMP_PATCH) { const f = nm.map(v => v / nmL), cmin = Math.min(...Nn.map(v => v[0] * f[0] + v[1] * f[1] + v[2] * f[2])); if (cmin > 0) face = { n: f, cos: -Math.sqrt(1 - cmin * cmin) }; }
    const m = [0, 1, 2].map(k => P.reduce((s, p) => s + p[k], 0) / n);
    const C = [0, 1, 2].map(i => [0, 1, 2].map(j => P.reduce((s, p) => s + (p[i] - m[i]) * (p[j] - m[j]), 0) / n));
    const ax = jacobi3(C).vecs, lo = [1e9, 1e9, 1e9], hi = [-1e9, -1e9, -1e9];
    const U = P.map(p => ax.map(e => (p[0] - m[0]) * e[0] + (p[1] - m[1]) * e[1] + (p[2] - m[2]) * e[2]));
    for (const u of U) for (let k = 0; k < 3; k++) { lo[k] = Math.min(lo[k], u[k]); hi[k] = Math.max(hi[k], u[k]); }
    const mid = [0, 1, 2].map(k => (lo[k] + hi[k]) / 2), h = [0, 1, 2].map(k => Math.max((hi[k] - lo[k]) / 2, LAMP_MIN_H));
    const se = Math.max(...U.map(u => Math.hypot((u[0] - mid[0]) / h[0], (u[1] - mid[1]) / h[1], (u[2] - mid[2]) / h[2])));
    const ell = se * se * se < 6 / Math.PI;   // the ellipsoid through the farthest vertex is smaller than the box
    const c = [0, 1, 2].map(k => m[k] + ax[0][k] * mid[0] + ax[1][k] * mid[1] + ax[2][k] * mid[2]);
    return { c, ax, h: h.map(v => (ell ? v * se : v) + LAMP_MARGIN), shape: ell ? 'ellipsoid' : 'box', geom, face, mat: seed.mat, n: nLamp, cover: nCover };
  }
  return { c: a.p.slice(), ax: [[1, 0, 0], [0, 1, 0], [0, 0, 1]], h: [LAMP_VIRTUAL_R, LAMP_VIRTUAL_R, LAMP_VIRTUAL_R], shape: 'ellipsoid', geom: false, face: null, mat: null, n: 0, cover: 0 };
}

// ---------------------------------------------------------------------------------------------------------------------
// OD4 iteration 6 (recheck of iteration 5, findings R1 / R2; docs/phase3_models.md 15.10): per-lamp SELF-VISIBILITY TABLES.
// Beyond ~60 m a lamp is smaller than a pixel: the scene depth holds one sample per pixel, taken up to half a pixel from the
// lamp, so the lens test of js/shaders/sprites.js cannot tell a lamp at its own body's silhouette (the PC-12 belly beacon seen
// from just below the horizon: the belly beside it lies 0.3 m in front of it at a grazing angle) from a lamp just behind an
// occluder's silhouette (a nav lamp under 5-10 cm of winglet skin) - whichever way it decides, the answer depends on where
// the lamp falls inside its pixel, and a light on a moving aircraft blinks. The airframe that hides a lamp of a detailed
// aircraft is the aircraft itself, so for every lamp its visible share is tabulated here once per model, by ray casting
// the model at rest: T(d) = the share of the lamp's projected area that is seen from direction d (the ground truth of the
// iteration-5 sweeps: G x G parallel rays over the lamp's footprint; a ray is in the footprint when it meets the lamp's own
// triangles (its lamp material, + the clear lens cover over it) or, for a lamp with no geometry, its shape; it sees the lamp
// when the first opaque surface along it lies at or behind the lamp's surface less LAMPVIS.TOL (5 mm: the PC-12 tail lamp
// is sunk 1-5 mm into the bullet tip and seen from behind). js/shaders/sprites.js looks the table up for a lamp below about
// two pixels (bilinear; the view direction in the lamp's shape frame), so the answer no longer depends on the pixel grid,
// and keeps the depth test for the occluders that are not the aircraft (buildings, other aircraft: only depth in front of
// the aircraft's bounding sphere counts there).
//   Layout: lat-long in the lamp shape's frame e0 = ax[0], e1 = ax[1], e2 = e0 x e1 (the frame js/shaders/sprites.js builds
//   from the sprite's iL1 / iL2): d = cos(el) cos(az) e0 + sin(el) e1 + cos(el) sin(az) e2; column ia = az in
//   [ia, ia + 1) x 2 pi / NA, row je = el in -90 deg + [je, je + 1) x 180 deg / NE (cell centres sampled); two channels:
//   0 = gear down (the model at rest), 1 = gear up (the same without the gear legs, wheels, braces and gear doors - retracted
//   into their wells they hide no lamp; the PC-12's tyres protrude ~1 in) [inf: approximation]; values x 255 (Uint8); channel
//   2 = the distance from the lamp's surface to the farthest of the cell's occluders (over its rays, the first opaque surface
//   along each hidden ray), in LAMPVIS.TFS = 0.1 m units (capped at 25.5 m): the table is a view from afar, and a camera
//   nearer than an occluder of its direction (between a wing-tip lamp and the fuselage, 5-20 m away) sees past it - there
//   js/shaders/sprites.js uses its depth test alone; channel 3 (OD4 iteration 6 round 2, recheck F2) = the aircraft's REACH
//   in front of the lamp: an upper bound of how far in front of the lamp (along d, from the plane through its centre normal
//   to d) any surface of the aircraft at rest (gear down, no propeller blades) lies within LAMPVIS.RHO of the line of sight
//   through the lamp's centre, in LAMPVIS.TFS units (capped at 25.5 m) - js/shaders/sprites.js counts a depth sample of its
//   external-occluder taps as another object's (an occluder that is not this aircraft) when it lies more than the reach (+ a
//   margin) in front of the lamp. Iteration 6 counted only depth in front of the aircraft's bounding sphere (11.6 m on the
//   PC-12), so another aircraft's wing or a hangar wall 1-3 m in front of a lamp was not an occluder of a sub-pixel lamp.
//   The reach of a direction is the largest along-distance over the surface points inside the cylinder of radius RHO around
//   it (the first surface a ray inside the cylinder meets coming from the camera is its farthest point in front of the lamp),
//   computed conservatively by splatting: the opaque surface is sampled at <= LAMPVIS.VS spacing into LAMPVIS.VOX voxels; a
//   voxel at distance r (centre) bounds its surface points within bV = VOX x sqrt(3) / 2 + VS of its centre, so it lies in
//   the cylinder only for directions within asin((RHO + bV) / r) of it (90 deg + asin(bV / r) when it is that close), where
//   no point of it lies more than r cos(b) + bV in front (b: the angle between the direction and the voxel); each cell takes
//   the largest such value over every voxel whose cap comes within one cell diagonal of the cell centre, at the smallest b
//   over that support (so the bilinear lookup between four cell centres never falls below the true reach there). Voxels with r + bV <= LAMPVIS.RMIN (the lamp's own housing) are left out: the shader's margin covers
//   them.
//   Round 3 (recheck F1 / F3; docs/phase3_models.md 15.12): the pose is the DRAWN one (js/aircraft/kinematics.js): gear down
//   = pose gear 1 (the SF50's nose doors open), gear up = pose gear 0 (channel 1 no longer drops the gear parts), and a lamp
//   whose seen share the flaps change also gets one table per tabulated flap setting (lampFlapSettings; S.visF, mixed by
//   js/shaders/sprites.js lampTable at lampFlapX of the flap angle); channel 3 (the reach) is one upper bound over the gear
//   down / up / in transit and every tabulated flap setting. Control surfaces neutral, doors closed, gear doors in transit
//   (the PC-12's nose clamshells, open only between the locks) not tabulated [inf]; above two pixels the depth test (which
//   sees them) decides.
//   lampTables(model, { yieldMs, NA, NE, flaps }) -> Promise<{ ms, rays, lamps, bladeTris, voxels, flapSet, flapLamps, posed }>:
//   sets model.lights[k].occ.vis = { NA, NE, data } for every light with a lamp shape, and occ.visF = { set, tables: [{ NA,
//   NE, data }, ..], dmax } | null (round 3: flaps false = no flap tables). yieldMs > 0: gives the event loop a turn every yieldMs of work
//   (js/aircraft/models.js loadModel: the app stays responsive while a model's tables are computed). NA / NE: the grid (tools;
//   default LAMPVIS). Needs the CPU geometry (groups), i.e. before js/aircraft/detailed.js drops it after the GPU upload.
export const LAMPVIS = { NA: 128, NE: 64, G: 4, MINFOOT: 4, TOL: 0.005, TFS: 0.1, RHO: 0.5, VOX: 0.1, VS: 0.05, RMIN: 0.25, FLAPDIFF: 3, BACK: 1.0 };
const GEAR_KINDS = new Set(['gear', 'gear_door', 'brace']);
// one turn of the event loop: a MessageChannel message (not a timer: browsers throttle the timers of a page that is not in
// front to one per second or less, which would stretch a model's tables over minutes)
const yieldTurn = () => new Promise(r => { if (typeof MessageChannel === 'undefined') { setTimeout(r, 0); return; }
  const ch = new MessageChannel(); ch.port1.onmessage = () => { ch.port1.close(); r(); }; ch.port2.postMessage(0); });
// OD4 iteration 6, round 3 (recheck F3; docs/phase3_models.md 15.12): the FLAP SETTINGS tabulated besides flaps 0 - the
// smallest and the largest non-zero setting of the model's flap pivots (`settings`; PC-12 0 / 15 / 30 / 40 -> 15, 40; SF50
// 0 / 15 / 39 -> 15, 39: the take-off and the landing setting js/live/aircraft.js flies); a type without flap pivots: none
export function lampFlapSettings(model) {
  let set = null; for (const p of model.parts) if (p.pivot && !p.excluded && p.pivot.kind === 'flap') { const s = (p.pivot.settings || [p.pivot.max || 40]).filter(v => v > 0); if (s.length) set = s; }
  if (!set) return []; const a = Math.min(...set), b = Math.max(...set); return a < b ? [a, b] : [b];
}
// the table position of a flap angle (deg) for js/shaders/sprites.js lampTable (iL5.w): 0 = flaps 0, 1 = set[0], 2 = set[1];
// piecewise linear in between (PC-12 30 deg: 1.6) [inf: the share between two tabulated settings]
export function lampFlapX(set, flaps) { if (!set || !set.length || !(flaps > 0)) return 0; if (flaps <= set[0]) return flaps / set[0];
  return set.length < 2 ? 1 : 1 + Math.min(1, (flaps - set[0]) / (set[1] - set[0])); }
const isIdent4 = (m) => !m || (Math.abs(m[0] - 1) < 1e-6 && Math.abs(m[5] - 1) < 1e-6 && Math.abs(m[10] - 1) < 1e-6 && Math.abs(m[1]) < 1e-6 && Math.abs(m[2]) < 1e-6 && Math.abs(m[4]) < 1e-6
  && Math.abs(m[6]) < 1e-6 && Math.abs(m[8]) < 1e-6 && Math.abs(m[9]) < 1e-6 && Math.abs(m[12]) < 1e-6 && Math.abs(m[13]) < 1e-6 && Math.abs(m[14]) < 1e-6);
export async function lampTables(model, { yieldMs = 0, NA = LAMPVIS.NA, NE = LAMPVIS.NE, flaps = true } = {}) {
  const t0 = Date.now(); let tl = Date.now(), rays = 0, lamps = 0, flapLamps = 0;
  const parts = model.parts, mats = model.materials;
  const chain = (pi, test) => { for (let q = pi; q >= 0; q = parts[q].parent) if (parts[q].pivot && test(parts[q].pivot.kind)) return true; return false; };
  const gearChain = (pi) => chain(pi, (k) => GEAR_KINDS.has(k)), flapChain = (pi) => chain(pi, (k) => k === 'flap');
  // OD4 iteration 6, round 2 (recheck F1): the PROPELLER BLADES are not occluders of the tables. They were tabulated frozen
  // at rotor angle 0, but a lamp is only on with the engine running (idle ~110 rad/s taxiing, ~178 on the roll), where
  // js/aircraft/detailed.js draws the translucent disc instead of the blades (above PROP_BLUR[1]): the depth copy holds no
  // blade and the lamp is seen through the disc - the rest blades hid the PC-12 nose-leg taxi light from ground cameras
  // ahead (az +-8..21 deg, el -4..+10 deg) and blinked it as a taxiing aircraft turned. A blade = a part whose mover chain
  // holds a 'pitch' mover below a 'spin' mover (detailed.js resources: prop.blades); the axisymmetric spinner (the 'spin'
  // mover's own part) stays. A slowly turning prop with drawn blades (below PROP_BLUR[1], an engine start) is still seen by
  // the depth test of a resolved lamp, and by the external-occluder taps where a blade lies beyond the reach (channel 3) +
  // the shader's margin; nearer (the PC-12 taxi light from ahead: reach 2.7 m, the blades 2.15 m in front) a sub-pixel lamp
  // is drawn through them [inf]
  const bladeChain = (pi) => { let pitch = false; for (let q = pi; q >= 0; q = parts[q].parent) { const k = parts[q].pivot && parts[q].pivot.kind;
    if (k === 'pitch') pitch = true; else if (k === 'spin') return pitch; } return false; };
  // OD4 iteration 6, round 3 (recheck F1 / F3): the tables are of the pose that is DRAWN (js/aircraft/kinematics.js, the
  // app's own pose code), not of the raw glTF rest geometry: gear down = pose({ gear: 1 }) - the SF50's nose-gear doors
  // (seq 'down') stand open 85 deg beside the nose leg whenever the gear is down, and the raw rest geometry has them closed,
  // so the table drew the SF50 taxi light through its own doors -, gear up = pose({ gear: 0 }) (legs retracted, doors shut;
  // iteration 6 dropped the gear parts instead), and per tabulated flap setting the flaps posed (lampFlapSettings). Flaps
  // 0, controls neutral, doors closed otherwise (DEFAULT_STATE).
  const kin = new Kinematics(model), st = (o) => ({ ...DEFAULT_STATE, ...o });
  const flapSet = flaps ? lampFlapSettings(model) : [];
  const PD = kin.pose(st({ gear: 1 })), PU = kin.pose(st({ gear: 0 })), PM = kin.pose(st({ gear: 0.5 }));
  const PF = [PD, ...flapSet.map(f => kin.pose(st({ gear: 1, flaps: f })))];
  const NF = PF.length;   // flap states: 0 = flaps 0, k = flapSet[k - 1]
  const pushX = (out, d, i, Mx) => { for (let v = 0; v < 3; v++) { const a = d.idx[i + v] * 3, x = d.pos[a], y = d.pos[a + 1], z = d.pos[a + 2];
    if (!Mx) out.push(x, y, z); else out.push(Mx[0] * x + Mx[4] * y + Mx[8] * z + Mx[12], Mx[1] * x + Mx[5] * y + Mx[9] * z + Mx[13], Mx[2] * x + Mx[6] * y + Mx[10] * z + Mx[14]); } };
  const mx = (P, mv) => mv >= 0 && !isIdent4(P[mv]) ? P[mv] : null;
  // opaque triangles (9 floats each, local frame, posed): the airframe without gear and flaps (A), the gear chain gear down /
  // up / in transit (GD / GU / GM), the flap chain per flap state (F[k])
  const A = [], GD = [], GU = [], GM = [], F = PF.map(() => []);
  let bladeTris = 0;
  for (const g of model.groups) { const d = g.opaque; if (!d || !d.idx) continue; const mv = g.mover;
    if (mv >= 0 && bladeChain(mv)) { bladeTris += d.idx.length / 3; continue; }
    if (mv >= 0 && gearChain(mv)) { const a = mx(PD, mv), b = mx(PU, mv), c = mx(PM, mv); for (let i = 0; i < d.idx.length; i += 3) { pushX(GD, d, i, a); pushX(GU, d, i, b); pushX(GM, d, i, c); } }
    else if (mv >= 0 && flapChain(mv)) { const M = PF.map(P => mx(P, mv)); for (let i = 0; i < d.idx.length; i += 3) for (let k = 0; k < NF; k++) pushX(F[k], d, i, M[k]); }
    else { const a = mx(PD, mv); for (let i = 0; i < d.idx.length; i += 3) pushX(A, d, i, a); } }
  if (!A.length) return { ms: 0, rays: 0, lamps: 0, skipped: 'no CPU geometry' };
  const bv = (T) => T.length ? bvhBuild(new Float32Array(T)) : null;
  const BA = bv(A), BGD = bv(GD), BGU = bv(GU), BF = F.map(bv);
  const { TOL } = LAMPVIS, RB = 40;
  // channel 3: the surface (airframe, the gear down / up / in transit; no blades) as voxel centres - an upper bound over the
  // gear poses - plus the flaps: at rest for a lamp's flaps-0 table and at each setting for its flap table (sprites.js
  // lampTable takes the larger reach of the two tables it mixes, so a flap between two settings is covered by both); a lamp
  // without flap tables gets the flaps of every setting in its one table
  const VX = reachVoxels([A, GD, GU, GM, F[0]]), VF = F.map((T, k) => k ? reachVoxels([T]) : null);
  const firstOr = (B, px, py, pz, d) => B ? bvhFirst(B, px, py, pz, d[0], d[1], d[2], TOL, RB) : -1;
  const mn = (a, b) => a < 0 ? b : b < 0 ? a : Math.min(a, b);
  const visD = new Float64Array(NF), visU = new Float64Array(NF), tfk = new Float64Array(NF), tF = new Float64Array(NF);
  for (const [k, L] of Object.entries(model.lights)) {
    const S0 = L && L.occ; if (!S0 || !KINDS.includes(k)) continue;   // kinds that are drawn (js/aircraft/detailed.js)
    const onGear = L.part >= 0 && gearChain(L.part);
    // the lamp as drawn with the gear down (its mover's pose; every lamp of both types is at rest there - the taxi lights'
    // nose legs are down - but a posed one is placed and its table is in its posed frame, the frame lampWorld gives the shader)
    const P0 = mx(PD, L.part), S = P0 ? { ...S0, c: [0, 1, 2].map(q => P0[q] * S0.c[0] + P0[4 + q] * S0.c[1] + P0[8 + q] * S0.c[2] + P0[12 + q]),
      ax: S0.ax.map(a => [0, 1, 2].map(q => P0[q] * a[0] + P0[4 + q] * a[1] + P0[8 + q] * a[2])) } : S0;
    // the lamp's own triangles (its lamp material on its mover, + the clear lens cover over it; centroid inside the shape x 1.05)
    let LB = null, LV = null;
    if (S.geom) { const V = [];
      for (const g of model.groups) { if (g.mover !== L.part) continue;
        for (const [d, sel] of [[g.opaque, (mi) => mats[mi] && mats[mi].name === S.mat], [g.glass, (mi) => S.cover > 0 && mats[mi] && mats[mi].cls === 'clear']]) { if (!d || !d.idx) continue;
          for (let i = 0; i < d.idx.length; i += 3) { if (!sel(d.mat[d.idx[i]])) continue; const T3 = []; pushX(T3, d, i, P0); const c = [0, 1, 2].map(q => (T3[q] + T3[3 + q] + T3[6 + q]) / 3);
            if (inLamp(c, S, 1.05)) V.push(...T3); } } }
      LB = V.length ? bvhBuild(new Float32Array(V)) : null; LV = V.length ? new Float32Array(V) : null; }
    const e0 = S.ax[0], e1 = S.ax[1], e2 = [e0[1] * e1[2] - e0[2] * e1[1], e0[2] * e1[0] - e0[0] * e1[2], e0[0] * e1[1] - e0[1] * e1[0]];
    // one cell of an na x ne grid: GG x GG parallel rays over the lamp's footprint seen from the cell-centre direction ->
    // the footprint rays; per flap state k: visD[k] / visU[k] = rays seen with the gear down / up, tfk[k] = the farthest
    // first occluder of a hidden ray (m, either gear state)
    const cell = (na, ne, je, ia, GG) => {
      const el = -Math.PI / 2 + (je + 0.5) / ne * Math.PI, az = (ia + 0.5) / na * 2 * Math.PI, ce = Math.cos(el), se = Math.sin(el), ca = Math.cos(az), sa = Math.sin(az);
      const d = [0, 1, 2].map(q => ce * ca * e0[q] + se * e1[q] + ce * sa * e2[q]);
      const up0 = Math.abs(d[1]) > 0.99 ? [1, 0, 0] : [0, 1, 0];
      let R = [d[1] * up0[2] - d[2] * up0[1], d[2] * up0[0] - d[0] * up0[2], d[0] * up0[1] - d[1] * up0[0]]; const rl = Math.hypot(R[0], R[1], R[2]); R = R.map(v => v / rl);
      const U = [R[1] * d[2] - R[2] * d[1], R[2] * d[0] - R[0] * d[2], R[0] * d[1] - R[1] * d[0]];
      // the rays cover the bounding rectangle of the lamp's projection (its own vertices +- 1 mm; a lamp with no geometry: its
      // shape x 1.05, as the ground truth): an unbiased estimate of the seen share of its projected area, with few rays wasted
      // on a flat lamp patch seen nearly edge-on
      let r0, r1, u0, u1;
      if (LV) { r0 = u0 = 1e9; r1 = u1 = -1e9; for (let v = 0; v < LV.length; v += 3) { const x = LV[v] - S.c[0], y = LV[v + 1] - S.c[1], z = LV[v + 2] - S.c[2];
          const pr = x * R[0] + y * R[1] + z * R[2], pu = x * U[0] + y * U[1] + z * U[2]; if (pr < r0) r0 = pr; if (pr > r1) r1 = pr; if (pu < u0) u0 = pu; if (pu > u1) u1 = pu; }
        r0 -= 0.001; r1 += 0.001; u0 -= 0.001; u1 += 0.001; }
      else { const sR = lampSupport(S, R) * 1.05, sU = lampSupport(S, U) * 1.05; r0 = -sR; r1 = sR; u0 = -sU; u1 = sU; }
      let foot = 0; visD.fill(0); visU.fill(0); tfk.fill(0);
      for (let j = 0; j < GG; j++) for (let i = 0; i < GG; i++) {
        const u = r0 + (i + 0.5) / GG * (r1 - r0), w = u0 + (j + 0.5) / GG * (u1 - u0);
        const ox = S.c[0] + R[0] * u + U[0] * w + d[0] * RB, oy = S.c[1] + R[1] * u + U[1] * w + d[1] * RB, oz = S.c[2] + R[2] * u + U[2] * w + d[2] * RB;
        let t;   // distance from o (outside, toward the viewer) back to the lamp's surface along -d
        if (LB) { t = bvhFirst(LB, ox, oy, oz, -d[0], -d[1], -d[2], 0, 2 * RB); if (t < 0) continue; }
        else { const iv = lampRay([ox, oy, oz], [-d[0], -d[1], -d[2]], S); if (!iv) continue; t = iv[0]; }
        foot++; rays++;
        const px = ox - d[0] * t, py = oy - d[1] * t, pz = oz - d[2] * t;
        // an occluder between the lamp's surface (+ TOL) and the viewer: the airframe (A) hides it in every state
        const tA = firstOr(BA, px, py, pz, d), occA = tA >= 0;
        if (occA && !onGear) { for (let q = 0; q < NF; q++) if (tA > tfk[q]) tfk[q] = tA; continue; }
        const tGD = firstOr(BGD, px, py, pz, d), tGU = firstOr(BGU, px, py, pz, d);
        for (let q = 0; q < NF; q++) tF[q] = firstOr(BF[q], px, py, pz, d);
        // a lamp with geometry: the ray must also meet an opaque surface at or behind (lamp surface - TOL) - a ray through the
        // rim of a clear lens cover that meets nothing is not a view of the lamp (the ground truth's rule; a lamp with no lens
        // cover: the surface found IS an opaque lamp triangle, so the check holds by construction)
        // (round 3: within LAMPVIS.BACK = 1 m behind it, as the recheck's ray-cast truth - with 2 RB = 80 m a ray through the
        // SF50 wing-tip landing light's clear cover that met the main gear legs 3 m behind counted as a view of the lamp with
        // the gear down and not with it up: gear-down / gear-up shares 0.38 / 0.11 where the ray cast sees 0.08)
        const back = (B) => !!B && bvhAny(B, px + d[0] * TOL, py + d[1] * TOL, pz + d[2] * TOL, -d[0], -d[1], -d[2], 0, LAMPVIS.BACK);
        let bD = true, bU = true;
        if (LB && S.cover > 0 && !back(BA)) { const bF = back(BF[0]); bD = bF || back(BGD); bU = bF || back(BGU); }
        if (!bD && !bU) continue;
        if (onGear) {   // a lamp on a gear leg is off unless the gear is down (its gear-up share = its gear-down share)
          for (let q = 0; q < NF; q++) { const h = mn(mn(occA ? tA : -1, tGD), tF[q]); if (h < 0) { if (bD) { visD[q]++; visU[q]++; } } else if (h > tfk[q]) tfk[q] = h; }
          continue; }
        for (let q = 0; q < NF; q++) { const hD = mn(tGD, tF[q]), hU = mn(tGU, tF[q]);
          if (hD < 0) { if (bD) visD[q]++; } else if (hD > tfk[q]) tfk[q] = hD;
          if (hU < 0) { if (bU) visU[q]++; } else if (hU > tfk[q]) tfk[q] = hU; }
      }
      return foot;
    };
    // every cell of the NA x NE grid with G x G rays; a lamp seen nearly edge-on (fewer than MINFOOT rays meet its footprint:
    // a flat SF50 lamp patch) is cast again with 3G x 3G
    const data = PF.map(() => new Uint8Array(NA * NE * 4)), hole = new Uint8Array(NA * NE);
    for (let je = 0; je < NE; je++) {
      for (let ia = 0; ia < NA; ia++) {
        let foot = cell(NA, NE, je, ia, LAMPVIS.G);
        if (foot < LAMPVIS.MINFOOT) foot = cell(NA, NE, je, ia, 3 * LAMPVIS.G);
        const q = je * NA + ia; if (!foot) { hole[q] = 1; continue; }
        for (let f = 0; f < NF; f++) { const D = data[f]; D[q * 4] = Math.round(255 * visD[f] / foot); D[q * 4 + 1] = Math.round(255 * visU[f] / foot); D[q * 4 + 2] = Math.min(255, Math.ceil(tfk[f] / LAMPVIS.TFS)); }
      }
      if (yieldMs > 0 && Date.now() - tl > yieldMs) { await yieldTurn(); tl = Date.now(); }
    }
    // directions from which the lamp has no projected area at all (a flat patch exactly edge-on): the mean of the cells
    // around them, so the bilinear lookup next to them is not pulled to 0 (a one-sided lamp seen from behind is hidden by
    // js/shaders/sprites.js anyway)
    for (let pass = 0; pass < 4 && hole.some(Boolean); pass++) { const fill = [];
      for (let q = 0; q < NA * NE; q++) { if (!hole[q]) continue; const je = (q / NA) | 0, ia = q % NA; let n = 0; const acc = data.map(() => [0, 0, 0]);
        for (const [dj, di] of [[0, 1], [0, -1], [1, 0], [-1, 0]]) { const j2 = je + dj; if (j2 < 0 || j2 >= NE) continue; const q2 = j2 * NA + (ia + di + NA) % NA; if (hole[q2]) continue; n++;
          data.forEach((D, f) => { acc[f][0] += D[q2 * 4]; acc[f][1] += D[q2 * 4 + 1]; acc[f][2] = Math.max(acc[f][2], D[q2 * 4 + 2]); }); }
        if (n) fill.push([q, acc.map(a => [Math.round(a[0] / n), Math.round(a[1] / n), a[2]])]); }
      for (const [q, v] of fill) { data.forEach((D, f) => { D[q * 4] = v[f][0]; D[q * 4 + 1] = v[f][1]; D[q * 4 + 2] = v[f][2]; }); hole[q] = 0; } }
    // the flap tables, kept only for a lamp whose seen share some flap setting changes by more than FLAPDIFF / 255 somewhere
    let dmax = 0; for (let f = 1; f < NF; f++) for (let q = 0; q < NA * NE * 4; q += 4) dmax = Math.max(dmax, Math.abs(data[f][q] - data[0][q]), Math.abs(data[f][q + 1] - data[0][q + 1]));
    const keepF = dmax > LAMPVIS.FLAPDIFF;
    reachSplat(data[0], NA, NE, S.c, e0, e1, e2, VX);
    for (let f = 1; f < NF; f++) { for (let q = 0; q < NA * NE; q++) data[f][q * 4 + 3] = data[0][q * 4 + 3];
      reachSplat(keepF ? data[f] : data[0], NA, NE, S.c, e0, e1, e2, VF[f], true); }
    S0.vis = { NA, NE, data: data[0] }; lamps++;
    S0.visF = keepF ? { set: flapSet.slice(), tables: data.slice(1).map(D => ({ NA, NE, data: D })), dmax } : null;
    if (S0.visF) flapLamps++;
    if (yieldMs > 0 && Date.now() - tl > yieldMs) { await yieldTurn(); tl = Date.now(); }
  }
  return { ms: Date.now() - t0, rays, lamps, bladeTris, voxels: VX.length / 3, flapSet, flapLamps, posed: { gearTris: GD.length / 9, flapTris: F[0].length / 9 } };
}
// the opaque surface sampled at <= LAMPVIS.VS into LAMPVIS.VOX voxels -> Float32Array of voxel centres (x, y, z, ...)
function reachVoxels(sets) {
  const { VOX, VS } = LAMPVIS, seen = new Set(), out = [];
  const add = (x, y, z) => { const ix = Math.floor(x / VOX), iy = Math.floor(y / VOX), iz = Math.floor(z / VOX);
    const key = ((ix + 2048) * 4096 + (iy + 2048)) * 4096 + (iz + 2048); if (seen.has(key)) return; seen.add(key); out.push((ix + 0.5) * VOX, (iy + 0.5) * VOX, (iz + 0.5) * VOX); };
  for (const T of sets) for (let o = 0; o < T.length; o += 9) {
    const ax = T[o], ay = T[o + 1], az = T[o + 2], bx = T[o + 3] - ax, by = T[o + 4] - ay, bz = T[o + 5] - az, cx = T[o + 6] - ax, cy = T[o + 7] - ay, cz = T[o + 8] - az;
    const e = Math.max(Math.hypot(bx, by, bz), Math.hypot(cx, cy, cz), Math.hypot(bx - cx, by - cy, bz - cz));
    const n = Math.max(1, Math.ceil(e / VS));   // barycentric grid of step e / n <= VS: every point of the triangle is within VS of a sample
    for (let i = 0; i <= n; i++) for (let j = 0; i + j <= n; j++) { const u = i / n, v = j / n; add(ax + bx * u + cx * v, ay + by * u + cy * v, az + bz * u + cz * v); }
  }
  return new Float32Array(out);
}
// channel 3 of a table (see LAMPVIS above): the largest along-distance r + bV of every voxel whose cylinder cap reaches each
// cell (+ one cell diagonal), in TFS units
function reachSplat(data, NA, NE, c, e0, e1, e2, VX, keep = false) {   // keep: raise the channel (max) instead of starting from 0
  const { VOX, VS, RHO, RMIN, TFS } = LAMPVIS, bV = VOX * Math.sqrt(3) / 2 + VS, dAz = 2 * Math.PI / NA, dEl = Math.PI / NE;
  const rel = new Float64Array(NE), sel = new Float64Array(NE), cel = new Float64Array(NE), del = new Float64Array(NE);
  const ang = (a1, e1_, a2, e2_) => Math.acos(Math.max(-1, Math.min(1, Math.sin(e1_) * Math.sin(e2_) + Math.cos(e1_) * Math.cos(e2_) * Math.cos(a1 - a2))));
  for (let j = 0; j < NE; j++) { const el = -Math.PI / 2 + (j + 0.5) * dEl; rel[j] = el; sel[j] = Math.sin(el); cel[j] = Math.cos(el);
    del[j] = Math.max(ang(0, el, dAz, Math.min(Math.PI / 2, el + dEl)), ang(0, el, dAz, Math.max(-Math.PI / 2, el - dEl))); }
  const dMax = Math.max(...del);
  const cdx = new Float64Array(NA * NE), cdy = new Float64Array(NA * NE), cdz = new Float64Array(NA * NE);   // cell-centre directions (lamp frame)
  for (let j = 0; j < NE; j++) for (let i = 0; i < NA; i++) { const az = (i + 0.5) * dAz, q = j * NA + i; cdx[q] = cel[j] * Math.cos(az); cdy[q] = sel[j]; cdz[q] = cel[j] * Math.sin(az); }
  if (!keep) for (let k = 0; k < NA * NE; k++) data[k * 4 + 3] = 0;
  for (let o = 0; o < VX.length; o += 3) {
    const vx = VX[o] - c[0], vy = VX[o + 1] - c[1], vz = VX[o + 2] - c[2], r = Math.hypot(vx, vy, vz), val = r + bV;
    if (val <= RMIN) continue;
    const x = vx * e0[0] + vy * e0[1] + vz * e0[2], y = vx * e1[0] + vy * e1[1] + vz * e1[2], z = vx * e2[0] + vy * e2[1] + vz * e2[2];
    const ux = x / r, uy = y / r, uz = z / r;
    const elv = Math.asin(Math.max(-1, Math.min(1, y / r))), azv = Math.atan2(z, x), sv = Math.sin(elv), cv = Math.cos(elv);
    // a point of the voxel inside the cylinder: the centre's lateral offset r sin(b) <= RHO + bV, its along-distance
    // r cos(b) > -bV; both hold beyond 90 deg only when r^2 < (RHO + bV)^2 + bV^2
    const th = r * r < (RHO + bV) * (RHO + bV) + bV * bV ? Math.PI / 2 + Math.asin(Math.min(1, bV / r)) : Math.asin((RHO + bV) / r);
    const j0 = Math.max(0, Math.floor((elv - th - dMax + Math.PI / 2) / dEl - 0.5)), j1 = Math.min(NE - 1, Math.ceil((elv + th + dMax + Math.PI / 2) / dEl - 0.5));
    for (let j = j0; j <= j1; j++) {
      const T = th + del[j]; if (Math.abs(rel[j] - elv) > T) continue;
      let i0, i1;
      const den = cel[j] * cv, num = Math.cos(Math.min(Math.PI, T)) - sel[j] * sv;
      if (T >= Math.PI || den < 1e-9 || num / den <= -1) { i0 = 0; i1 = NA - 1; }
      else { const cc = num / den; if (cc > 1) continue; const half = Math.acos(cc); i0 = Math.ceil((azv - half) / dAz - 0.5); i1 = Math.floor((azv + half) / dAz - 0.5); if (i1 - i0 >= NA - 1) { i0 = 0; i1 = NA - 1; } }
      const row = j * NA, cd = Math.cos(del[j]), sd = Math.sin(del[j]);
      // the voxel's points lie at most r cos(b - dj) + bV in front over the cell's support (directions within dj of its centre)
      for (let i = i0; i <= i1; i++) { const q = row + ((i % NA) + NA) % NA, cb = cdx[q] * ux + cdy[q] * uy + cdz[q] * uz;
        const v = (cb >= cd ? r : r * (cb * cd + Math.sqrt(Math.max(0, 1 - cb * cb)) * sd)) + bV; if (v <= RMIN) continue;
        const code = Math.min(255, Math.ceil(v / TFS)); if (data[q * 4 + 3] < code) data[q * 4 + 3] = code; }
    }
  }
}
// bilinear lookup of a table (as the GPU's LINEAR filter on the RGBA8 atlas: columns wrap, rows clamp) - for tools and tests:
// the seen share; lampVisFar: the farthest occluder distance (m) of channel 2; lampVisReach: the aircraft's reach in front of
// the lamp (m) of channel 3
export function lampVisLookup(vis, S, dir, gearUp = 0) { const v = lampVisSample(vis, S, dir); return v[0] * (1 - gearUp) + v[1] * gearUp; }
export function lampVisFar(vis, S, dir) { return lampVisSample(vis, S, dir)[2] * 255 * LAMPVIS.TFS; }
export function lampVisReach(vis, S, dir) { return lampVisSample(vis, S, dir)[3] * 255 * LAMPVIS.TFS; }
// round 3 (F3): the lookup with the flap tables as js/shaders/sprites.js lampTable mixes them (flapX = lampFlapX(S.visF.set,
// flaps)) -> [seen share, farthest occluder (m), reach (m)]
export function lampVisState(S, dir, gearUp = 0, flapX = 0) {
  let v = lampVisSample(S.vis, S, dir);
  if (S.visF && flapX > 0) { const t1 = lampVisSample(S.visF.tables[0], S, dir), t2 = S.visF.tables[1] ? lampVisSample(S.visF.tables[1], S, dir) : t1;
    const mixv = (a, b, x) => [...[0, 1, 2].map(i => a[i] + (b[i] - a[i]) * x), Math.max(a[3], b[3])];   // the reach: the larger of the two
    v = flapX <= 1 ? mixv(v, t1, flapX) : mixv(t1, t2, Math.min(1, flapX - 1)); }
  return [v[0] * (1 - gearUp) + v[1] * gearUp, v[2] * 255 * LAMPVIS.TFS, v[3] * 255 * LAMPVIS.TFS];
}
function lampVisSample(vis, S, dir) {
  const e0 = S.ax[0], e1 = S.ax[1], e2 = [e0[1] * e1[2] - e0[2] * e1[1], e0[2] * e1[0] - e0[0] * e1[2], e0[0] * e1[1] - e0[1] * e1[0]];
  const l = Math.hypot(dir[0], dir[1], dir[2]) || 1, x = (dir[0] * e0[0] + dir[1] * e0[1] + dir[2] * e0[2]) / l, y = (dir[0] * e1[0] + dir[1] * e1[1] + dir[2] * e1[2]) / l, z = (dir[0] * e2[0] + dir[1] * e2[1] + dir[2] * e2[2]) / l;
  const { NA, NE, data } = vis; const el = Math.asin(Math.max(-1, Math.min(1, y))), az = Math.atan2(z, x);
  const fx = (az / (2 * Math.PI)) * NA - 0.5, fy = Math.min(NE - 0.5, Math.max(0.5, (el / Math.PI + 0.5) * NE)) - 0.5;
  const x0 = Math.floor(fx), y0 = Math.floor(fy), ax = fx - x0, ay = fy - y0;
  const g = (ix, iy, ch) => data[((Math.min(NE - 1, Math.max(0, iy)) * NA + (((ix % NA) + NA) % NA)) * 4) + ch] / 255;
  const v = (ch) => (g(x0, y0, ch) * (1 - ax) + g(x0 + 1, y0, ch) * ax) * (1 - ay) + (g(x0, y0 + 1, ch) * (1 - ax) + g(x0 + 1, y0 + 1, ch) * ax) * ay;
  return [v(0), v(1), v(2), v(3)];
}
function inLamp(p, S, k) { const u = S.ax.map(a => (p[0] - S.c[0]) * a[0] + (p[1] - S.c[1]) * a[1] + (p[2] - S.c[2]) * a[2]);
  return S.shape === 'box' ? u.every((v, i) => Math.abs(v) <= S.h[i] * k) : Math.hypot(u[0] / S.h[0], u[1] / S.h[1], u[2] / S.h[2]) <= k; }
function lampSupport(S, v) { const p = S.ax.map((a, k) => S.h[k] * (a[0] * v[0] + a[1] * v[1] + a[2] * v[2])); return S.shape === 'box' ? Math.abs(p[0]) + Math.abs(p[1]) + Math.abs(p[2]) : Math.hypot(p[0], p[1], p[2]); }
function lampRay(o, d, S) {   // ray o + t d vs the lamp shape -> [t0, t1] | null
  const oc = [o[0] - S.c[0], o[1] - S.c[1], o[2] - S.c[2]], os = S.ax.map(a => oc[0] * a[0] + oc[1] * a[1] + oc[2] * a[2]), ds = S.ax.map(a => d[0] * a[0] + d[1] * a[1] + d[2] * a[2]);
  if (S.shape === 'box') { let t0 = -1e30, t1 = 1e30; for (let k = 0; k < 3; k++) { const dk = Math.abs(ds[k]) < 1e-9 ? 1e-9 : ds[k]; let a = (-S.h[k] - os[k]) / dk, b = (S.h[k] - os[k]) / dk; if (a > b) [a, b] = [b, a]; t0 = Math.max(t0, a); t1 = Math.min(t1, b); } return t0 <= t1 ? [t0, t1] : null; }
  const oo = os.map((v, k) => v / S.h[k]), dd = ds.map((v, k) => v / S.h[k]); const a = dd[0] * dd[0] + dd[1] * dd[1] + dd[2] * dd[2], b = oo[0] * dd[0] + oo[1] * dd[1] + oo[2] * dd[2], c = oo[0] * oo[0] + oo[1] * oo[1] + oo[2] * oo[2] - 1;
  const D = b * b - a * c; if (D < 0) return null; const s = Math.sqrt(D); return [(-b - s) / a, (-b + s) / a];
}
// compact BVH over a triangle soup (9 floats per triangle): midpoint split of the centroid box, flattened typed arrays
function bvhBuild(T) {
  const n = T.length / 9, idx = new Uint32Array(n), cen = new Float32Array(n * 3), bb = new Float32Array(n * 6);
  for (let i = 0; i < n; i++) for (let k = 0; k < 3; k++) { const a = T[i * 9 + k], b = T[i * 9 + 3 + k], c = T[i * 9 + 6 + k]; bb[i * 6 + k] = Math.min(a, b, c); bb[i * 6 + 3 + k] = Math.max(a, b, c); cen[i * 3 + k] = (a + b + c) / 3; idx[i] = i; }
  const cap = 2 * n + 1, lo = new Float32Array(cap * 3), hi = new Float32Array(cap * 3), left = new Int32Array(cap), start = new Uint32Array(cap), cnt = new Uint32Array(cap), axis = new Uint8Array(cap);
  let nn = 0;
  const mk = (s, e) => { const id = nn++; let x0 = 1e30, y0 = 1e30, z0 = 1e30, x1 = -1e30, y1 = -1e30, z1 = -1e30;
    for (let j = s; j < e; j++) { const i = idx[j] * 6; x0 = Math.min(x0, bb[i]); y0 = Math.min(y0, bb[i + 1]); z0 = Math.min(z0, bb[i + 2]); x1 = Math.max(x1, bb[i + 3]); y1 = Math.max(y1, bb[i + 4]); z1 = Math.max(z1, bb[i + 5]); }
    lo[id * 3] = x0; lo[id * 3 + 1] = y0; lo[id * 3 + 2] = z0; hi[id * 3] = x1; hi[id * 3 + 1] = y1; hi[id * 3 + 2] = z1; start[id] = s; cnt[id] = e - s; left[id] = -1; return id; };
  const work = [mk(0, n)];
  while (work.length) { const id = work.pop(); const s = start[id], e = s + cnt[id]; if (e - s <= 4) continue;
    const c0 = [1e30, 1e30, 1e30], c1 = [-1e30, -1e30, -1e30]; for (let j = s; j < e; j++) for (let k = 0; k < 3; k++) { const v = cen[idx[j] * 3 + k]; c0[k] = Math.min(c0[k], v); c1[k] = Math.max(c1[k], v); }
    let ax = 0; if (c1[1] - c0[1] > c1[ax] - c0[ax]) ax = 1; if (c1[2] - c0[2] > c1[ax] - c0[ax]) ax = 2;
    if (c1[ax] - c0[ax] < 1e-9) continue;
    const mid = 0.5 * (c0[ax] + c1[ax]); let i0 = s, i1 = e - 1;
    while (i0 <= i1) { if (cen[idx[i0] * 3 + ax] < mid) i0++; else { const t = idx[i0]; idx[i0] = idx[i1]; idx[i1] = t; i1--; } }
    if (i0 === s || i0 === e) i0 = (s + e) >> 1;
    const a = mk(s, i0), b = mk(i0, e); left[id] = a; cnt[id] = 0; start[id] = b; axis[id] = ax; work.push(a, b); }
  return { T, idx, lo, hi, left, start, cnt, axis };
}
const BVH_STACK = new Int32Array(512);
function bvhWalk(B, ox, oy, oz, dx, dy, dz, tmin, tmax, any) {
  const ix = 1 / (Math.abs(dx) < 1e-12 ? 1e-12 : dx), iy = 1 / (Math.abs(dy) < 1e-12 ? 1e-12 : dy), iz = 1 / (Math.abs(dz) < 1e-12 ? 1e-12 : dz);
  const { T, idx, lo, hi, left, start, cnt, axis } = B; const st = BVH_STACK; let sp = 0, best = tmax; st[sp++] = 0;
  while (sp) { const id = st[--sp], j = id * 3;
    let a = (lo[j] - ox) * ix, b = (hi[j] - ox) * ix, t0 = Math.min(a, b), t1 = Math.max(a, b);
    a = (lo[j + 1] - oy) * iy; b = (hi[j + 1] - oy) * iy; t0 = Math.max(t0, Math.min(a, b)); t1 = Math.min(t1, Math.max(a, b));
    a = (lo[j + 2] - oz) * iz; b = (hi[j + 2] - oz) * iz; t0 = Math.max(t0, Math.min(a, b)); t1 = Math.min(t1, Math.max(a, b));
    if (t1 < Math.max(t0, tmin) || t0 > best) continue;
    if (left[id] < 0) { for (let q = start[id], e = start[id] + cnt[id]; q < e; q++) { const o = idx[q] * 9;
        const ax = T[o], ay = T[o + 1], az = T[o + 2], e1x = T[o + 3] - ax, e1y = T[o + 4] - ay, e1z = T[o + 5] - az, e2x = T[o + 6] - ax, e2y = T[o + 7] - ay, e2z = T[o + 8] - az;
        const px = dy * e2z - dz * e2y, py = dz * e2x - dx * e2z, pz = dx * e2y - dy * e2x, det = e1x * px + e1y * py + e1z * pz; if (det > -1e-14 && det < 1e-14) continue;
        const inv = 1 / det, sx = ox - ax, sy = oy - ay, sz = oz - az, u = (sx * px + sy * py + sz * pz) * inv; if (u < 0 || u > 1) continue;
        const qx = sy * e1z - sz * e1y, qy = sz * e1x - sx * e1z, qz = sx * e1y - sy * e1x, v = (dx * qx + dy * qy + dz * qz) * inv; if (v < 0 || u + v > 1) continue;
        const t = (e2x * qx + e2y * qy + e2z * qz) * inv; if (t > tmin && t < best) { if (any) return t; best = t; } } }
    // near child first (popped first): the left child holds the centroids below the split on its axis - a first-hit query
    // then shrinks `best` early and skips more boxes (OD4 it. 6 round 2: ~same hits, fewer box tests)
    else { const ax = axis[id], pos = ax === 0 ? dx > 0 : ax === 1 ? dy > 0 : dz > 0;
      if (pos) { st[sp++] = start[id]; st[sp++] = left[id]; } else { st[sp++] = left[id]; st[sp++] = start[id]; } } }
  return best < tmax ? best : -1;
}
const bvhAny = (B, ox, oy, oz, dx, dy, dz, tmin, tmax) => bvhWalk(B, ox, oy, oz, dx, dy, dz, tmin, tmax, true) >= 0;
const bvhFirst = (B, ox, oy, oz, dx, dy, dz, tmin, tmax) => bvhWalk(B, ox, oy, oz, dx, dy, dz, tmin, tmax, false);
