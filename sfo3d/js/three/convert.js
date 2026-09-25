// Conversions from the records produced by js/three/compat/gl.js (the gl.js stand-in) to three.js objects:
//   shim Mesh {pos, nrm, uv, col, extra, idx}  -> BufferGeometry with attributes position, normal, uv, color (vec4),
//                                                 extra (vec4: roughness, metalness, material id, emissive — js/geom.js)
//   texture record (data / canvas / ImageBitmap) -> DataTexture / Texture with the same filtering and wrapping
// Image-backed textures: the record's ImageBitmap copy (js/three/compat/gl.js snapshot) may still be decoding; the
// Texture is created at once (three shows a default texture) and gets the bitmap when it resolves. After three has
// uploaded it (texture.onUpdate), the CPU copy is closed and dropped (review round 1: every image stayed in memory twice
// for the whole session). Only data textures keep their arrays (small, except the airfield maps, which are disposed
// after the bake).
import { THREE } from './lib.js';
import { retained } from './compat/gl.js';

const K = WebGL2RenderingContext;
const geoCache = new WeakMap();
export function geometryFromData(d, opts = {}) {
  const g = new THREE.BufferGeometry();
  const f32 = (a) => a instanceof Float32Array ? a : new Float32Array(a);
  g.setAttribute('position', new THREE.BufferAttribute(f32(d.pos), 3));
  if (d.nrm) g.setAttribute('normal', new THREE.BufferAttribute(f32(d.nrm), 3));
  if (d.uv) g.setAttribute('uv', new THREE.BufferAttribute(f32(d.uv), 2));
  if (d.col) g.setAttribute('color', new THREE.BufferAttribute(f32(d.col), 4));
  if (d.extra) g.setAttribute('extra', new THREE.BufferAttribute(f32(d.extra), 4));
  if (d.idx) { const n = d.pos.length / 3; const I = d.idx instanceof Uint32Array || d.idx instanceof Uint16Array ? d.idx : (n > 65535 ? new Uint32Array(d.idx) : new Uint16Array(d.idx)); g.setIndex(new THREE.BufferAttribute(I, 1)); }
  if (d.bbox && d.bbox.length === 6 && isFinite(d.bbox[0])) { g.boundingBox = new THREE.Box3(new THREE.Vector3(d.bbox[0], d.bbox[1], d.bbox[2]), new THREE.Vector3(d.bbox[3], d.bbox[4], d.bbox[5])); g.boundingSphere = g.boundingBox.getBoundingSphere(new THREE.Sphere()); }
  else { g.computeBoundingBox(); g.computeBoundingSphere(); }
  if (!d.col && opts.defaultColor !== false) { /* materials treat a missing color attribute as white */ }
  return g;
}
// shim Mesh -> BufferGeometry (cached; disposed with the shim mesh)
export function geometryOf(mesh) {
  let g = geoCache.get(mesh); if (g) return g;
  g = geometryFromData(mesh.data); geoCache.set(mesh, g);
  const prev = mesh.onDispose; mesh.onDispose = (m) => { g.dispose(); if (prev) prev(m); };
  return g;
}

const texCache = new WeakMap();
const halfOf = (f32) => { const h = new Uint16Array(f32.length); for (let i = 0; i < f32.length; i++) h[i] = THREE.DataUtils.toHalfFloat(f32[i]); return h; };
// rec: texture record ({tex: rec} wrappers are accepted); opts: { anisotropy, colorSpace }
export function textureOf(recOrWrap, opts = {}) {
  let rec = recOrWrap; for (let i = 0; i < 3 && rec && !rec.isTexRecord; i++) rec = rec.tex; // {tex: rec} / {tex: {tex: rec}} wrappers
  if (!rec || !rec.isTexRecord) return null;
  let t = texCache.get(rec); if (t && t.userData.version === rec.version) return t;
  if (t) t.dispose();
  const srgb = rec.internal === K.SRGB8_ALPHA8;
  if (rec.source || rec.pending) {
    t = rec.source ? new THREE.Texture(rec.source) : new THREE.Texture(); if (rec.source) t.needsUpdate = true;
    const tt = t; rec.onSource = (bmp) => { tt.image = bmp; tt.needsUpdate = true; };
    t.onUpdate = () => releaseImage(tt, rec);
  } else {
    let data = rec.data, format = THREE.RGBAFormat, type = THREE.UnsignedByteType;
    if (rec.format === K.RED) format = THREE.RedFormat; else if (rec.format === K.RG) format = THREE.RGFormat;
    if (rec.type === K.FLOAT) { type = THREE.HalfFloatType; data = halfOf(data); } // half float: filterable everywhere (no OES_texture_float_linear on iOS)
    else if (rec.type === K.HALF_FLOAT) type = THREE.HalfFloatType;
    t = new THREE.DataTexture(data, rec.w, rec.h, format, type); t.needsUpdate = true;
  }
  t.flipY = false; t.premultiplyAlpha = false; // the builders upload with UNPACK_FLIP_Y false: v = 0 is the first row
  t.colorSpace = opts.colorSpace || (srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace);
  const mm = rec.mips || rec.minFilter === K.LINEAR_MIPMAP_LINEAR || rec.minFilter === K.LINEAR_MIPMAP_NEAREST;
  t.generateMipmaps = mm; t.minFilter = mm ? THREE.LinearMipmapLinearFilter : rec.minFilter === K.NEAREST ? THREE.NearestFilter : THREE.LinearFilter;
  t.magFilter = rec.magFilter === K.NEAREST ? THREE.NearestFilter : THREE.LinearFilter;
  const wrap = (w) => w === K.REPEAT ? THREE.RepeatWrapping : w === K.MIRRORED_REPEAT ? THREE.MirroredRepeatWrapping : THREE.ClampToEdgeWrapping;
  t.wrapS = wrap(rec.wrapS); t.wrapT = wrap(rec.wrapT);
  t.anisotropy = Math.max(1, Math.min(opts.anisotropy || 1, rec.aniso > 1 ? 16 : (opts.anisotropy || 1)));
  t.userData.version = rec.version; t.userData.rec = rec;
  texCache.set(rec, t);
  return t;
}
// drop the CPU copy of an uploaded image (a bitmap is closed a moment later: WebGPU's copyExternalImageToTexture is
// queued; the spec captures the source at the call, the delay is only a margin)
function releaseImage(t, rec) {
  const img = t.image; if (!img || img.isReleased) return;
  const w = img.width, h = img.height;
  if (typeof img.close === 'function') setTimeout(() => img.close(), 1500);
  else if (img.getContext) { img.width = img.height = 1; }
  t.image = { width: w, height: h, isReleased: true }; if (rec) { rec.source = null; retained.delete(rec); }
}
// bytes of image copies still held on the CPU (debug / QA)
export function retainedImageBytes() { let b = 0; for (const r of retained) { const s = r.source; if (s && s.width) b += s.width * s.height * 4; else if (r.pending) b += (r.w || 0) * (r.h || 0) * 4; } return b; }
// release pixel memory held by the record once three.js owns the texture (it keeps its own copy only until upload)
export function releaseRecord(recOrWrap) { const rec = recOrWrap && recOrWrap.isTexRecord ? recOrWrap : recOrWrap && recOrWrap.tex; if (rec) { rec.data = null; } }
