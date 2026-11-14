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
//   materials [{ name, base [r, g, b, a], rough, metal, blend, cls }],
//   partIndex Map id -> index
// }
// Material channel (js/shaders/objects.js OBJ_FS): per-vertex colour = baseColorFactor (linear RGB, alpha) x COLOR_0, and
// ext = [roughness, metallic, mat id, emissive]; mat id 0 = the plain PBR path of the obj shader (opts.matId can map a
// material to another id). Alpha-blended materials (alphaMode BLEND) go to the `glass` Geo of their group.

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
    const mid = opts.partMatId ? opts.partMatId(m.matId, pr.part >= 0 ? parts[pr.part].id : null) : m.matId;
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
    materials: [...mats, defMat].map(m => ({ name: m.name, base: m.base, rough: m.rough, metal: m.metal, blend: m.blend, cls: m.cls, matId: m.matId, textured: m.textured })),
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
