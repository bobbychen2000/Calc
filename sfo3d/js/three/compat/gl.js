// Recording stand-in for js/gl.js, used by the three.js renderer (live3.html remaps '/js/gl.js' to this file through
// its import map; tools/build3/build.mjs --app applies the same alias).
//
// Why: the engine-independent builders (airport/terminal/gate/marking/sign geometry, the .sfom decoder, the procedural
// textures in js/world/textures.js, LiveGateSystem, LiveAircraft) end in `new Mesh(data)`, `texture(w, h, opts)` or a
// few raw gl.tex* calls. Re-implementing those modules would fork them while other workflows keep changing them, so
// instead this module records what they build: a Mesh keeps its typed arrays, a texture keeps its pixels/source and
// sampling parameters. js/three/convert.js turns the records into three.js BufferGeometry / Texture objects.
//
// API surface mirrored from js/gl.js (read 24 Sep 2026): gl, initGL, defineChunk, Program, Mesh(data) with
// setInstances/dispose/draw/drawRange, texture(w, h, opts), FBO, fullscreen. Raw calls seen in signs.js (makeAtlas),
// models.js (srgbTexture), world/textures.js (wave/cloud/noise textures): createTexture, bindTexture, texStorage2D,
// texSubImage2D (6/7- and 9-argument forms), texParameteri/f, generateMipmap, pixelStorei, getExtension, deleteTexture.
// Any other method is a no-op, so a new call in those modules degrades gracefully instead of throwing.

const K = typeof WebGL2RenderingContext !== 'undefined' ? WebGL2RenderingContext : {};
const ANISO_EXT = { TEXTURE_MAX_ANISOTROPY_EXT: 0x84FE, MAX_TEXTURE_MAX_ANISOTROPY_EXT: 0x84FF };
let texSerial = 0;

// texture record: { id, w, h, internal, format, type, data | source, mips, minFilter, magFilter, wrapS, wrapT, aniso, version, deleted }
export function newTexRecord(extra = {}) { return { id: ++texSerial, isTexRecord: true, w: 0, h: 0, internal: K.RGBA8, format: K.RGBA, type: K.UNSIGNED_BYTE, data: null, source: null, mips: false, minFilter: K.LINEAR, magFilter: K.LINEAR, wrapS: K.CLAMP_TO_EDGE, wrapT: K.CLAMP_TO_EDGE, aniso: 1, version: 0, deleted: false, ...extra }; }

function makeFakeGL() {
  let bound = null;
  const impl = {
    isFakeGL: true,
    createTexture: () => newTexRecord(),
    bindTexture: (target, t) => { bound = t && t.isTexRecord ? t : null; },
    texStorage2D: (target, levels, internal, w, h) => { if (!bound) return; bound.internal = internal; bound.w = w; bound.h = h; bound.levels = levels; },
    texImage2D: (...a) => impl.texSubImage2D(...a),
    texSubImage2D: (...a) => {
      if (!bound) return;
      if (a.length >= 9) { const [, , , , w, h, format, type, data] = a; bound.w = bound.w || w; bound.h = bound.h || h; bound.format = format; bound.type = type; bound.data = data; }
      else { const src = a[a.length - 1]; bound.format = a[a.length - 3]; bound.type = a[a.length - 2]; bound.source = src; if (src && !bound.w) { bound.w = src.width; bound.h = src.height; } }
      bound.version++;
    },
    texParameteri: (target, p, v) => {
      if (!bound) return;
      if (p === K.TEXTURE_MIN_FILTER) bound.minFilter = v; else if (p === K.TEXTURE_MAG_FILTER) bound.magFilter = v;
      else if (p === K.TEXTURE_WRAP_S) bound.wrapS = v; else if (p === K.TEXTURE_WRAP_T) bound.wrapT = v;
    },
    texParameterf: (target, p, v) => { if (bound && p === ANISO_EXT.TEXTURE_MAX_ANISOTROPY_EXT) bound.aniso = v; },
    generateMipmap: () => { if (bound) bound.mips = true; },
    deleteTexture: (t) => { if (t && t.isTexRecord) { t.deleted = true; t.data = null; t.source = null; } },
    getExtension: (name) => /anisotropic/i.test(name) ? ANISO_EXT : {},
    getParameter: (p) => p === ANISO_EXT.MAX_TEXTURE_MAX_ANISOTROPY_EXT ? 16 : 0,
  };
  return new Proxy(impl, {
    get(o, k) {
      if (k in o) return o[k];
      if (typeof k === 'string' && k in K) return K[k];
      return () => undefined; // unknown gl.* call: no-op
    },
  });
}
export let gl = makeFakeGL();
export function initGL() { return gl; }
export function defineChunk() { }
export class Program { constructor() { this.u = {}; } use() { return this; } set() { return this; } setAll() { return this; } }
export class FBO { constructor(w, h) { this.w = w; this.h = h; this.tex = []; } bind() { } dispose() { } }
export function fullscreen() { }

let meshSerial = 0;
// Mesh: keeps the attribute arrays (pos 3, nrm 3, uv 2, col 4, extra 4, idx) for js/three/convert.js
export class Mesh {
  constructor(data) {
    this.id = ++meshSerial; this.isShimMesh = true; this.data = data;
    this.count = data.idx ? data.idx.length : data.pos.length / 3; this.indexed = !!data.idx;
    this.bbox = data.bbox || null; this.mode = data.mode || 4;
    this.instanced = false; this.inst = null; this.nInst = 0; this.instVersion = 0; this.disposed = false;
  }
  // instance data: 16 floats per instance: 3 rows of a 3x4 matrix (12) + data (4), as in js/gl.js
  setInstances(f32, n) { this.inst = f32; this.nInst = n; this.instanced = true; this.instVersion++; }
  dispose() { this.disposed = true; if (this.onDispose) this.onDispose(this); }
  drawRange() { }
  draw() { }
}
export function texture(w, h, opts = {}) {
  const r = newTexRecord({ w, h, internal: opts.internal || K.RGBA8, format: opts.format || K.RGBA, type: opts.type || K.UNSIGNED_BYTE,
    data: opts.data || null, source: opts.source || null, mips: !!opts.mips, repeat: !!opts.repeat, nearest: !!opts.nearest, aniso: opts.aniso || 1 });
  r.minFilter = opts.mips ? K.LINEAR_MIPMAP_LINEAR : opts.nearest ? K.NEAREST : K.LINEAR; r.magFilter = opts.nearest ? K.NEAREST : K.LINEAR;
  r.wrapS = r.wrapT = opts.repeat ? K.REPEAT : K.CLAMP_TO_EDGE;
  return { tex: r, w, h };
}
