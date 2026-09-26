// Loader for converted airliner models (.sfom = gzip(SFOM header + JSON + blob)).
// Materials are baked into vertex attributes so a whole airframe draws in one call per texture.
// Texture 0 of an atlased model (head.atlas, tools/liveries/atlas.py) is the livery atlas: its draw carries uAtlas = 1 and
// can wear a brand livery texture (getLiveryTexture, js/aircraft/liveries.js); its alpha marks cabin-window glass.
import { gl, Mesh } from '../gl.js';
import { plugShift } from '../aircraft/fit.js';

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

// stretch (js/aircraft/fit.js), all in model units of the unstretched model (x forward, nose = 0, aft negative; y up; z right):
//   cut1, cut2, d1, d2, bl2  fuselage plugs at cut1 / cut2 of length d1 / d2 (negative: section removed, the aft one
//                        blended over bl2), see js/aircraft/fit.js plugShift. The atlas (tools/liveries/atlas.py) splits the
//                        mesh at the stations, so only a 2 cm band of triangles is stretched by a plug.
//   wing {z0, z1, dz, xMin}  span fit: outboard of z0 the wing is stretched spanwise, linearly up to z1, and everything
//                        outboard of z1 (the tip device) moves rigidly by dz (only vertices ahead of xMin: not the tailplane)
//   tipCut {z0, y0, zTo, yTo}  vertices outboard of z0 and above y0 (the model's winglet) folded to (zTo, yTo)
//   engScale {k}         nacelles scaled radially by k about their axis, the lowest line kept (737 MAX LEAP-1B)
//   wingLift {z0, t, xMin} / htLift {z0, t, xMax}  wing / tailplane sheared up by t per unit |z| outboard of z0
//   squash {y0, k}       everything below y0 compressed vertically by k (engine ground clearance fit)
//   gearUp               model units the model's own gear (zone 3) is moved up (oleo compression)
//   fin {yF, xF, k}      fin height fit: vertices aft of xF and above the fuselage top yF (not engines, pylons, gear)
//                        are scaled vertically about yF by k
const ZONE_NOFIN = new Set([2, 3, 7]); // engine, gear, pylon (tools/convert_models.py ZONE)
export function applyStretch(pos, zone, nv, st, dims) {
  const W = st.wing, Fn = st.fin;
  if (st.tipCut) {                    // fold the model's own tip device onto the wing tip (a procedural one replaces it)
    const { z0, y0, zTo, yTo } = st.tipCut;
    for (let i = 0; i < nv; i++) { const z = pos[i * 3 + 2]; if (Math.abs(z) > z0 && pos[i * 3 + 1] > y0) { pos[i * 3 + 1] = yTo; pos[i * 3 + 2] = Math.sign(z) * Math.min(Math.abs(z), zTo); } }
  }
  if (st.engScale && zone) {          // nacelles (zone 2) scaled radially about their own axis, lowest line kept
    const k = st.engScale.k;
    for (const sg of [-1, 1]) {
      let y0 = 1e9, y1 = -1e9, zs = 0, n = 0;
      for (let i = 0; i < nv; i++) if (zone[i] === 2 && Math.sign(pos[i * 3 + 2]) === sg) { const y = pos[i * 3 + 1]; if (y < y0) y0 = y; if (y > y1) y1 = y; zs += pos[i * 3 + 2]; n++; }
      if (!n) continue; const yc = (y0 + y1) / 2, zc = zs / n, lift = (k - 1) * (yc - y0);
      for (let i = 0; i < nv; i++) if (zone[i] === 2 && Math.sign(pos[i * 3 + 2]) === sg) { pos[i * 3 + 1] = yc + (pos[i * 3 + 1] - yc) * k + lift; pos[i * 3 + 2] = zc + (pos[i * 3 + 2] - zc) * k; }
    }
  }
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
  if (st.wingLift) {                  // wing dihedral fit: outboard of z0 (fuselage side) the wing, pylons and nacelles rise by t per unit |z|
    const { z0, t, xMin } = st.wingLift;
    for (let i = 0; i < nv; i++) { const az = Math.abs(pos[i * 3 + 2]); if (az > z0 && pos[i * 3] >= xMin && !(zone && (zone[i] === 1 || zone[i] === 3))) pos[i * 3 + 1] += t * (az - z0); }
  }
  if (st.htLift) {                    // tailplane dihedral fit (aft of xMax)
    const { z0, t, xMax } = st.htLift;
    for (let i = 0; i < nv; i++) { const az = Math.abs(pos[i * 3 + 2]); if (az > z0 && pos[i * 3] < xMax && !(zone && zone[i] === 1)) pos[i * 3 + 1] += t * (az - z0); }
  }
  if (st.squash) {                    // vertical compression below the fuselage centre line (js/aircraft/fit.js engine clearance)
    const { y0, k } = st.squash;
    for (let i = 0; i < nv; i++) { const y = pos[i * 3 + 1]; if (y < y0) pos[i * 3 + 1] = y0 + (y - y0) * k; }
    if (dims.low != null) dims.low = y0 + (dims.low - y0) * k;
  }
  if (st.gearUp) {                    // oleo compression of a model's own gear (js/aircraft/fit.js): the gear moves up
    let low = 1e9;
    for (let i = 0; i < nv; i++) { if (zone && zone[i] === 3) pos[i * 3 + 1] += st.gearUp; if (pos[i * 3 + 1] < low) low = pos[i * 3 + 1]; }
    dims.low = low;
  }
  if (st.cut1 != null) {
    const { cut1, cut2, d1, d2 } = st; const bl2 = st.bl2 || 0;
    for (let i = 0; i < nv; i++) {
      const x = pos[i * 3]; pos[i * 3] = x + plugShift(x, cut1, d1) + plugShift(x, cut2, d2, bl2);
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
  // exact duplicate triangles (same three vertex positions; e.g. 592 on the FAM 747-8 nose, double-sided copies) z-fight
  // with opposite normals and shade as dark blotches (review round 1): only the first copy is drawn
  const seenTri = new Set(); const pk = (v) => pq[v * 3] + ',' + pq[v * 3 + 1] + ',' + pq[v * 3 + 2];
  const dupTri = (i) => { const k = [pk(idxIn[i]), pk(idxIn[i + 1]), pk(idxIn[i + 2])].sort().join('|'); if (seenTri.has(k)) return true; seenTri.add(k); return false; };
  const idx = new Uint32Array(head.ni); let w = 0; const draws = [];
  for (const [tex, list] of groups) {
    const first = w;
    for (const d of list) for (let i = d.first; i < d.first + d.count; i += 3) { if (dupTri(i)) continue; idx[w++] = idxIn[i]; idx[w++] = idxIn[i + 1]; idx[w++] = idxIn[i + 2]; }
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
  return { key: head.key, name: head.name, head, dims, mesh, draws: drawList, all, bbox: [mn, mx], verts: nv, tris: nIdx / 3, anchors, tip };
}

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
function drawFlag(ctx, kind, x, y, h, mirror) {
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
export function registrationTexture(reg, flag = null, flagFirst = false) {
  const key = reg + '|' + (flag || '') + '|' + (flagFirst ? 1 : 0);
  if (regCache.has(key)) return regCache.get(key);
  let out = null;
  try {
    const mk = (w, h) => (typeof OffscreenCanvas !== 'undefined' ? new OffscreenCanvas(w, h) : Object.assign(document.createElement('canvas'), { width: w, height: h }));
    const font = `bold ${Math.round(ROW * CAP / 0.72)}px Helvetica, Arial, "Liberation Sans", sans-serif`;
    const m = mk(8, 8).getContext('2d'); m.font = font; const tw = Math.ceil(m.measureText(reg).width);
    const fh = ROW * CAP, fw = flag ? fh * 1.9 : 0, gap = flag ? ROW * 0.35 : 0;
    const W = Math.ceil(tw + fw + gap + 8), H = 2 * ROW;
    const cv = mk(W, H), ctx = cv.getContext('2d');
    ctx.clearRect(0, 0, W, H); ctx.font = font; ctx.textBaseline = 'alphabetic'; ctx.fillStyle = '#000000';
    const row = (y0, flagLeft, mirror) => {
      let x = 4; const base = y0 + ROW * (0.5 + CAP / 2);
      if (flag && flagLeft) { x += drawFlag(ctx, flag, x, base - fh, fh, mirror) + gap; }
      ctx.fillStyle = '#000000'; ctx.fillText(reg, x, base); x += tw + gap;
      if (flag && !flagLeft) drawFlag(ctx, flag, x, base - fh, fh, mirror);
    };
    // port side: nose on the left, the image runs nose -> tail; starboard: nose on the right (the shader flips u)
    row(0, flagFirst, false); row(ROW, !flagFirst, true);
    out = { ...srgbTexture(cv), aspect: W / ROW };
  } catch (e) { out = null; }
  regCache.set(key, out);
  return out;
}
