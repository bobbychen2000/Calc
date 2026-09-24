import { gl, texture } from '../gl.js';
import { rng } from '../math.js';

// Runway glyph atlas: 16 cells: 0-9, L(10), R(11), C(12)
export function makeGlyphAtlas() {
  const CW = 160, CH = 400; const cv = document.createElement('canvas'); cv.width = CW * 16; cv.height = CH;
  const cx = cv.getContext('2d'); cx.fillStyle = '#000'; cx.fillRect(0, 0, cv.width, cv.height);
  cx.fillStyle = '#fff'; cx.textAlign = 'center'; cx.textBaseline = 'alphabetic';
  const chars = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'L', 'R', 'C'];
  chars.forEach((ch, i) => {
    cx.save(); cx.translate(i * CW + CW / 2, CH * 0.97);
    // tall condensed bold glyphs (runway font is ~ 3:1 tall)
    cx.font = 'bold 300px "DejaVu Sans", "Liberation Sans", Arial, sans-serif';
    const m = cx.measureText(ch); const w = m.width;
    const asc = m.actualBoundingBoxAscent;
    cx.scale((CW * 0.86) / w, (CH * 0.94) / asc);
    cx.fillText(ch, 0, 0); cx.restore();
  });
  // signed distance field (inside positive, 0.5 = edge, 64 atlas px per unit) so that strokes stay crisp and never
  // vanish under mipmapping
  const W = cv.width, H = cv.height; const px = cx.getImageData(0, 0, W, H).data;
  const INF = 1e20; const inside = new Float64Array(W * H), outside = new Float64Array(W * H);
  for (let i = 0; i < W * H; i++) { const on = px[i * 4] > 127; inside[i] = on ? INF : 0; outside[i] = on ? 0 : INF; }
  edt2d(inside, W, H); edt2d(outside, W, H);
  const out = new Uint8Array(W * H * 4);
  for (let i = 0; i < W * H; i++) {
    const d = Math.sqrt(inside[i]) - Math.sqrt(outside[i]); // >0 inside the glyph
    const v = Math.max(0, Math.min(255, Math.round((0.5 + d / 64) * 255)));
    out[i * 4] = out[i * 4 + 1] = out[i * 4 + 2] = v; out[i * 4 + 3] = 255;
  }
  cv.width = cv.height = 1;
  return texture(W, H, { data: out, mips: true });
}
// exact squared Euclidean distance transform (Felzenszwalb & Huttenlocher), in place; f: 0 at features, 1e20 elsewhere
function edt1d(f, n, off, stride, tmp) {
  const { d, v, z, g } = tmp;
  for (let q = 0; q < n; q++) g[q] = f[off + q * stride];
  let k = 0; v[0] = 0; z[0] = -Infinity; z[1] = Infinity;
  for (let q = 1; q < n; q++) {
    let s = ((g[q] + q * q) - (g[v[k]] + v[k] * v[k])) / (2 * q - 2 * v[k]);
    while (s <= z[k]) { k--; s = ((g[q] + q * q) - (g[v[k]] + v[k] * v[k])) / (2 * q - 2 * v[k]); }
    k++; v[k] = q; z[k] = s; z[k + 1] = Infinity;
  }
  k = 0;
  for (let q = 0; q < n; q++) { while (z[k + 1] < q) k++; const dq = q - v[k]; d[q] = dq * dq + g[v[k]]; }
  for (let q = 0; q < n; q++) f[off + q * stride] = d[q];
}
function edt2d(f, W, H) {
  const n = Math.max(W, H);
  const tmp = { d: new Float64Array(n), v: new Int32Array(n), z: new Float64Array(n + 1), g: new Float64Array(n) };
  for (let x = 0; x < W; x++) edt1d(f, H, x, W, tmp);
  for (let y = 0; y < H; y++) edt1d(f, W, y * W, 1, tmp);
}
export function glyphCode(des) { // '28R' -> packed
  const m = /^(\d{1,2})([LRC]?)$/.exec(des); const num = m[1], let_ = m[2];
  const d1 = num.length === 2 ? +num[0] : +num[0]; const d2 = num.length === 2 ? +num[1] : 15;
  const l = let_ === 'L' ? 10 : let_ === 'R' ? 11 : let_ === 'C' ? 12 : 15;
  return l * 256 + d1 * 16 + d2;
}

// Tileable wave slope texture (sum of integer-frequency cosines, wind-aligned spectrum)
export function makeWaveTexture(windDirRad = 0) {
  const N = 256; const R = rng(77); const waves = [];
  for (let i = 0; i < 90; i++) {
    let kx, ky; do { kx = Math.round((R() * 2 - 1) * 24); ky = Math.round((R() * 2 - 1) * 24); } while (kx === 0 && ky === 0);
    const k = Math.hypot(kx, ky); const dir = Math.atan2(ky, kx);
    const align = Math.pow(Math.max(0.1, Math.cos(dir - windDirRad)) , 2) * 0.8 + 0.2;
    const amp = align / Math.pow(k, 1.6) * 0.7;
    waves.push([kx, ky, amp, R() * Math.PI * 2]);
  }
  const data = new Float32Array(N * N * 4);
  for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
    let sx = 0, sy = 0, h = 0; const u = x / N * Math.PI * 2, v = y / N * Math.PI * 2;
    for (const [kx, ky, a, ph] of waves) { const arg = kx * u + ky * v + ph; const s = Math.sin(arg), c = Math.cos(arg); h += a * c; sx += -a * kx * s; sy += -a * ky * s; }
    const i = (y * N + x) * 4; data[i] = sx * 0.05; data[i + 1] = sy * 0.05; data[i + 2] = h; data[i + 3] = 1;
  }
  const t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t);
  gl.texStorage2D(gl.TEXTURE_2D, 9, gl.RGBA16F, N, N);
  gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, N, N, gl.RGBA, gl.FLOAT, data);
  gl.generateMipmap(gl.TEXTURE_2D);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.REPEAT);
  const e = gl.getExtension('EXT_texture_filter_anisotropic'); if (e) gl.texParameterf(gl.TEXTURE_2D, e.TEXTURE_MAX_ANISOTROPY_EXT, (window.ANISO||1));
  return { tex: t };
}

// Tileable cloud density (periodic fbm)
export function makeCloudTexture(seed = 5) {
  const N = 512; const R = rng(seed);
  const P = 8; const grid = []; for (let o = 0; o < 7; o++) { const p = P << o; const g = new Float32Array(p * p); for (let i = 0; i < p * p; i++) g[i] = R(); grid.push({ p, g }); }
  const noise = (x, y, o) => { const { p, g } = grid[o]; const X = x * p, Y = y * p; const i = Math.floor(X), j = Math.floor(Y); const fx = X - i, fy = Y - j; const u = fx * fx * (3 - 2 * fx), v = fy * fy * (3 - 2 * fy);
    const a = g[((j % p + p) % p) * p + ((i % p + p) % p)], b = g[((j % p + p) % p) * p + (((i + 1) % p + p) % p)], c = g[(((j + 1) % p + p) % p) * p + ((i % p + p) % p)], d = g[(((j + 1) % p + p) % p) * p + (((i + 1) % p + p) % p)];
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v; };
  const data = new Uint8Array(N * N);
  for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
    let s = 0, a = 0.5, n = 0; for (let o = 0; o < 7; o++) { s += a * noise(x / N, y / N, o); n += a; a *= 0.52; }
    s /= n; // ~0.5 mean
    // billow shaping
    data[y * N + x] = Math.max(0, Math.min(255, (s - 0.2) / 0.6 * 255));
  }
  const t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t);
  gl.texStorage2D(gl.TEXTURE_2D, 10, gl.R8, N, N); gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
  gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, N, N, gl.RED, gl.UNSIGNED_BYTE, data); gl.generateMipmap(gl.TEXTURE_2D);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.REPEAT);
  gl.pixelStorei(gl.UNPACK_ALIGNMENT, 4);
  return { tex: t };
}

// NOAA solar position. date: JS Date (UTC). returns {az (deg from N clockwise), el (deg)}
export function solarPosition(date, lat, lon) {
  const rad = Math.PI / 180;
  const jd = date.getTime() / 86400000 + 2440587.5; const T = (jd - 2451545) / 36525;
  const L0 = (280.46646 + T * (36000.76983 + T * 0.0003032)) % 360;
  const M = 357.52911 + T * (35999.05029 - 0.0001537 * T);
  const e = 0.016708634 - T * (0.000042037 + 0.0000001267 * T);
  const C = Math.sin(M * rad) * (1.914602 - T * (0.004817 + 0.000014 * T)) + Math.sin(2 * M * rad) * (0.019993 - 0.000101 * T) + Math.sin(3 * M * rad) * 0.000289;
  const trueLong = L0 + C; const omega = 125.04 - 1934.136 * T; const lambda = trueLong - 0.00569 - 0.00478 * Math.sin(omega * rad);
  const eps0 = 23 + (26 + (21.448 - T * (46.815 + T * (0.00059 - T * 0.001813))) / 60) / 60; const eps = eps0 + 0.00256 * Math.cos(omega * rad);
  const decl = Math.asin(Math.sin(eps * rad) * Math.sin(lambda * rad)) / rad;
  const y = Math.tan(eps * rad / 2) ** 2;
  const eqTime = 4 / rad * (y * Math.sin(2 * L0 * rad) - 2 * e * Math.sin(M * rad) + 4 * e * y * Math.sin(M * rad) * Math.cos(2 * L0 * rad) - 0.5 * y * y * Math.sin(4 * L0 * rad) - 1.25 * e * e * Math.sin(2 * M * rad));
  const minutes = date.getUTCHours() * 60 + date.getUTCMinutes() + date.getUTCSeconds() / 60;
  let tst = (minutes + eqTime + 4 * lon) % 1440; if (tst < 0) tst += 1440;
  let ha = tst / 4 - 180; if (ha < -180) ha += 360;
  const zen = Math.acos(Math.sin(lat * rad) * Math.sin(decl * rad) + Math.cos(lat * rad) * Math.cos(decl * rad) * Math.cos(ha * rad)) / rad;
  let az = Math.acos(((Math.sin(lat * rad) * Math.cos(zen * rad)) - Math.sin(decl * rad)) / (Math.cos(lat * rad) * Math.sin(zen * rad))) / rad;
  az = ha > 0 ? (az + 180) % 360 : (540 - az) % 360;
  return { az, el: 90 - zen };
}
export function sunVector(az, el) {
  const a = az * Math.PI / 180, e = el * Math.PI / 180;
  return [Math.sin(a) * Math.cos(e), Math.sin(e), -Math.cos(a) * Math.cos(e)];
}

// Tileable RGBA noise: R value noise (16 cells), G value noise (64 cells), B fbm (6 oct), A value noise (128 cells)
export function makeNoiseTexture() {
  const N = 512; const R = rng(99);
  const mk = (p) => { const g = new Float32Array(p * p); for (let i = 0; i < p * p; i++) g[i] = R(); return { p, g }; };
  const grids = [4, 8, 16, 32, 64, 128, 256].map(mk);
  const vn = ({ p, g }, x, y) => { const X = x * p, Y = y * p; const i = Math.floor(X), j = Math.floor(Y); const fx = X - i, fy = Y - j; const u = fx * fx * (3 - 2 * fx), v = fy * fy * (3 - 2 * fy);
    const i0 = i % p, i1 = (i + 1) % p, j0 = j % p, j1 = (j + 1) % p; const a = g[j0 * p + i0], b = g[j0 * p + i1], c = g[j1 * p + i0], d = g[j1 * p + i1];
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v; };
  const data = new Uint8Array(N * N * 4);
  for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
    const u = x / N, v = y / N; const i = (y * N + x) * 4;
    data[i] = vn(grids[2], u, v) * 255; data[i + 1] = vn(grids[4], u, v) * 255;
    let s = 0, a = 0.5, n = 0; for (let o = 0; o < 6; o++) { s += a * vn(grids[o], u, v); n += a; a *= 0.5; } data[i + 2] = s / n * 255;
    data[i + 3] = vn(grids[5], u, v) * 255;
  }
  const t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t);
  gl.texStorage2D(gl.TEXTURE_2D, 10, gl.RGBA8, N, N); gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, N, N, gl.RGBA, gl.UNSIGNED_BYTE, data); gl.generateMipmap(gl.TEXTURE_2D);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.REPEAT);
  const e = gl.getExtension('EXT_texture_filter_anisotropic'); if (e) gl.texParameterf(gl.TEXTURE_2D, e.TEXTURE_MAX_ANISOTROPY_EXT, (window.ANISO||1));
  return { tex: t };
}
