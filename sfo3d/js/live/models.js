// Loader for converted airliner models (.sfom = gzip(SFOM header + JSON + blob)).
// Materials are baked into vertex attributes so a whole airframe draws in one call per texture.
import { gl, Mesh } from '../gl.js';

const cache = new Map();      // key -> Promise<Model>
export const MODEL_SOURCES = {}; // key -> ArrayBuffer | url | () => ArrayBuffer (set by the app)
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

// stretch (js/aircraft/fit.js), all in model units of the unstretched model (x forward, nose = 0, aft negative; y up; z right):
//   cut1, cut2, d1, d2  fuselage plugs: vertices aft of cut1 move back by d1, aft of cut2 by d1 + d2
//   wing {z0, z1, dz, xMin}  span fit: outboard of z0 the wing is stretched spanwise, linearly up to z1, and everything
//                        outboard of z1 (the tip device) moves rigidly by dz (only vertices ahead of xMin: not the tailplane)
//   fin {yF, xF, k}      fin height fit: vertices aft of xF and above the fuselage top yF (not engines, pylons, gear)
//                        are scaled vertically about yF by k
const ZONE_NOFIN = new Set([2, 3, 7]); // engine, gear, pylon (tools/convert_models.py ZONE)
export function applyStretch(pos, zone, nv, st, dims) {
  const W = st.wing, Fn = st.fin;
  if (W) {
    const { z0, z1, dz, xMin } = W; const sc = dz / (z1 - z0);
    for (let i = 0; i < nv; i++) {
      if (pos[i * 3] < xMin) continue;
      const z = pos[i * 3 + 2], az = Math.abs(z); if (az <= z0) continue;
      pos[i * 3 + 2] = z + Math.sign(z) * (az >= z1 ? dz : (az - z0) * sc);
    }
    dims.span += 2 * dz;
  }
  if (Fn) {
    const { yF, xF, k } = Fn; let top = -1e9;
    for (let i = 0; i < nv; i++) {
      const y = pos[i * 3 + 1];
      if (pos[i * 3] < xF && y > yF && !(zone && ZONE_NOFIN.has(zone[i]))) pos[i * 3 + 1] = yF + (y - yF) * k;
      if (pos[i * 3 + 1] > top) top = pos[i * 3 + 1];
    }
    dims.H = top;
  }
  if (st.cut1 != null) {
    const { cut1, cut2, d1, d2 } = st;
    for (let i = 0; i < nv; i++) {
      const x = pos[i * 3];
      if (x < cut2) pos[i * 3] = x - d1 - d2; else if (x < cut1) pos[i * 3] = x - d1;
    }
    dims.L += d1 + d2; dims.tailX -= d1 + d2;
  }
}
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
  if (stretch) applyStretch(pos, zq, nv, stretch, dims);
  const idxIn = head.idxType === 'u16' ? new Uint16Array(raw, B + o.idx, head.ni) : new Uint32Array(raw, B + o.idx, head.ni);
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
  let mn = [1e9, 1e9, 1e9], mx = [-1e9, -1e9, -1e9];
  for (let i = 0; i < nv; i++) for (let k = 0; k < 3; k++) { const v = pos[i * 3 + k]; if (v < mn[k]) mn[k] = v; if (v > mx[k]) mx[k] = v; }
  const anchors = lightAnchors(pos, nv, mn, mx, dims.R || 2);
  const mesh = new Mesh({ pos, nrm, uv, col, extra, idx });
  const textures = [];
  for (const t of head.textures) {
    const im = await decodeImage(new Uint8Array(raw, B + t.offset, t.length), t.fmt === 'png' ? 'image/png' : 'image/jpeg');
    textures.push(srgbTexture(im.img)); im.close();
  }
  const white = { tex: null };
  const drawList = draws.map(d => ({ ...d, U: { uAlbedo: d.tex >= 0 ? textures[d.tex] : (textures[0] || white), uHasTex: d.tex >= 0 ? 1 : 0 },
    sub: { draw: () => mesh.drawRange(d.first, d.count) } }));
  const all = { draw: () => mesh.drawRange(0, head.ni) };
  return { key: head.key, name: head.name, head, dims, mesh, draws: drawList, all, bbox: [mn, mx], verts: nv, tris: head.ni / 3, anchors };
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
export function getModel(key, stretch) {
  const ck = key + (stretch ? ':' + JSON.stringify(stretch) : '');
  if (!cache.has(ck)) {
    const p = (async () => {
      const src = MODEL_SOURCES[key];
      if (!src) throw new Error('no model source for ' + key);
      const m = await decodeModel(await sourceBytes(src), stretch);
      p._value = m; return m;
    })();
    cache.set(ck, p);
  }
  return cache.get(ck);
}
