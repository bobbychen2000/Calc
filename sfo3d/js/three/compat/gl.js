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
// Image sources are copied at upload time: the builders release them right after the gl upload (models.js closes the
// ImageBitmap, signs.js makeAtlas shrinks its canvas to 1x1), while three.js uploads lazily at first use.
// The copy is createImageBitmap(src, {premultiplyAlpha: 'none', colorSpaceConversion: 'none'}), which captures the
// source synchronously (HTML spec: the bitmap data is copied before the promise is returned) without a 2D canvas: no
// canvas memory (iOS Safari caps it), no premultiplication (the colour of alpha-0 texels is kept, so alpha-tested
// edges do not fringe dark when mipmapped), and js/three/convert.js closes the bitmap once three.js has uploaded it
// (review round 1: 48 image textures kept 359 MB of canvas pixels for the whole session). On tiers with a texture cap
// (setMaxTextureSize, phones 1024) larger images are resized in the same call. Browsers without createImageBitmap
// fall back to the old canvas copy.
let maxTexSize = 0;
export function setMaxTextureSize(n) { maxTexSize = n || 0; }
export const retained = new Set(); // records whose CPU-side image copy is still held (debug: convert.retainedImageBytes)
// decoded images are uploaded at once, as the old renderer did at gl.texSubImage2D time (review round 1: model atlases
// of aircraft beyond the LOD distance stayed on the CPU until first drawn): js/three/renderer3.js sets imageHooks.ready
// once three.js is initialised; images decoded before that wait in imageHooks.queue
export const imageHooks = { ready: null, queue: [] };
const imageReady = (rec) => { if (imageHooks.ready) imageHooks.ready(rec); else imageHooks.queue.push(rec); };
function snapshot(src, rec) {
  if (!src || typeof document === 'undefined' || !(src.width > 0)) return src;
  if ((typeof ImageData !== 'undefined' && src instanceof ImageData) || ArrayBuffer.isView(src)) return src;
  if (typeof createImageBitmap === 'function') {
    try {
      const o = { premultiplyAlpha: 'none', colorSpaceConversion: 'none' }; const w = src.width, h = src.height, big = Math.max(w, h);
      if (maxTexSize && big > maxTexSize) { const k = maxTexSize / big; o.resizeWidth = Math.max(1, Math.round(w * k)); o.resizeHeight = Math.max(1, Math.round(h * k)); o.resizeQuality = 'high'; }
      const p = createImageBitmap(src, o);
      if (rec) {
        rec.source = null; rec.pending = p; retained.add(rec);
        p.then((bmp) => {
          if (rec.pending !== p) { bmp.close(); return; } rec.pending = null;
          if (rec.deleted) { bmp.close(); retained.delete(rec); return; }
          rec.source = bmp; rec.sw = bmp.width; rec.sh = bmp.height; if (rec.onSource) rec.onSource(bmp); imageReady(rec); // upload now in both cases (a texture made before the bitmap arrived used to wait for its first draw, and aircraft beyond the LOD distance kept their bitmaps)
        }, (e) => { rec.pending = null; retained.delete(rec); console.warn('[r3] image copy failed', e); });
      }
      return null;
    } catch (e) { /* fall through to the canvas copy */ }
  }
  const c = document.createElement('canvas'); c.width = src.width; c.height = src.height;
  c.getContext('2d').drawImage(src, 0, 0); if (rec) { retained.add(rec); Promise.resolve().then(() => { if (!rec.deleted && rec.source === c) imageReady(rec); }); } return c;
}

// texture record: { id, w, h, internal, format, type, data | source, mips, minFilter, magFilter, wrapS, wrapT, aniso, version, deleted }
export function newTexRecord(extra = {}) { return { id: ++texSerial, isTexRecord: true, w: 0, h: 0, internal: K.RGBA8, format: K.RGBA, type: K.UNSIGNED_BYTE, data: null, source: null, mips: false, minFilter: K.LINEAR, magFilter: K.LINEAR, wrapS: K.CLAMP_TO_EDGE, wrapT: K.CLAMP_TO_EDGE, aniso: 1, version: 0, deleted: false, ...extra }; }

// What the device can do, for js/live/app.js's start-up check (it asks for EXT_color_buffer_float and the anisotropy
// limit right after initGL; review round 1: this stand-in answered yes to everything, so an unsupported browser got a
// blank canvas instead of the app's message). Probed once on a throwaway WebGL 2 context, released at once. A browser
// with WebGPU renders through three's WebGPU backend, which has float targets natively.
let _caps = null;
function caps() {
  if (_caps) return _caps; _caps = { webgl2: false, floatRT: false, aniso: 1, webgpu: typeof navigator !== 'undefined' && !!navigator.gpu };
  try {
    const c = document.createElement('canvas'); c.width = c.height = 1; const g = c.getContext('webgl2');
    if (g) {
      _caps.webgl2 = true; _caps.floatRT = !!(g.getExtension('EXT_color_buffer_float') || g.getExtension('EXT_color_buffer_half_float'));
      const a = g.getExtension('EXT_texture_filter_anisotropic'); _caps.aniso = a ? g.getParameter(a.MAX_TEXTURE_MAX_ANISOTROPY_EXT) : 1;
      const l = g.getExtension('WEBGL_lose_context'); if (l) l.loseContext();
    }
  } catch (e) { /* no WebGL 2 */ }
  if (_caps.webgpu && !_caps.webgl2) { _caps.floatRT = true; _caps.aniso = 16; }
  return _caps;
}
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
      else { const img = a[a.length - 1]; bound.format = a[a.length - 3]; bound.type = a[a.length - 2]; if (img && !bound.w) { bound.w = img.width; bound.h = img.height; } const src = snapshot(img, bound); if (src) bound.source = src; }
      bound.version++;
    },
    texParameteri: (target, p, v) => {
      if (!bound) return;
      if (p === K.TEXTURE_MIN_FILTER) bound.minFilter = v; else if (p === K.TEXTURE_MAG_FILTER) bound.magFilter = v;
      else if (p === K.TEXTURE_WRAP_S) bound.wrapS = v; else if (p === K.TEXTURE_WRAP_T) bound.wrapT = v;
    },
    texParameterf: (target, p, v) => { if (bound && p === ANISO_EXT.TEXTURE_MAX_ANISOTROPY_EXT) bound.aniso = v; },
    generateMipmap: () => { if (bound) bound.mips = true; },
    deleteTexture: (t) => { if (t && t.isTexRecord) { t.deleted = true; t.data = null; if (t.source && t.source.close) t.source.close(); t.source = null; retained.delete(t); } },
    getExtension: (name) => { const C = caps(); if (/anisotropic/i.test(name)) return C.aniso > 1 ? ANISO_EXT : null; if (/color_buffer_(half_)?float/i.test(name)) return C.floatRT ? {} : null; return {}; },
    getParameter: (p) => p === ANISO_EXT.MAX_TEXTURE_MAX_ANISOTROPY_EXT ? caps().aniso : 0,
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
// the page's canvas (js/live/app.js creates it and calls initGL(canvas)); the three.js renderer draws into it
export let glCanvas = null;
export function initGL(canvas) { glCanvas = canvas || null; return gl; }
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
    data: opts.data || null, source: null, mips: !!opts.mips, repeat: !!opts.repeat, nearest: !!opts.nearest, aniso: opts.aniso || 1 });
  if (opts.source) { const src = snapshot(opts.source, r); if (src) r.source = src; }
  r.minFilter = opts.mips ? K.LINEAR_MIPMAP_LINEAR : opts.nearest ? K.NEAREST : K.LINEAR; r.magFilter = opts.nearest ? K.NEAREST : K.LINEAR;
  r.wrapS = r.wrapT = opts.repeat ? K.REPEAT : K.CLAMP_TO_EDGE;
  return { tex: r, w, h };
}
