'use strict';
// ------------------------------------------------------------------
// Minimal linear algebra (column-major 4x4, like WebGL expects)
// ------------------------------------------------------------------
const DEG = Math.PI / 180;
const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
const lerp = (a, b, t) => a + (b - a) * t;
const smooth = (e0, e1, x) => { const t = clamp((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t); };

const V3 = {
  add: (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]],
  sub: (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]],
  scale: (a, s) => [a[0] * s, a[1] * s, a[2] * s],
  dot: (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2],
  cross: (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]],
  len: (a) => Math.hypot(a[0], a[1], a[2]),
  norm: (a) => { const l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; },
  lerp: (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t],
};

const M4 = {
  ident() { const m = new Float32Array(16); m[0] = m[5] = m[10] = m[15] = 1; return m; },
  mul(a, b, out = new Float32Array(16)) {
    const r = out;
    for (let c = 0; c < 4; c++) {
      const b0 = b[c * 4], b1 = b[c * 4 + 1], b2 = b[c * 4 + 2], b3 = b[c * 4 + 3];
      r[c * 4] = a[0] * b0 + a[4] * b1 + a[8] * b2 + a[12] * b3;
      r[c * 4 + 1] = a[1] * b0 + a[5] * b1 + a[9] * b2 + a[13] * b3;
      r[c * 4 + 2] = a[2] * b0 + a[6] * b1 + a[10] * b2 + a[14] * b3;
      r[c * 4 + 3] = a[3] * b0 + a[7] * b1 + a[11] * b2 + a[15] * b3;
    }
    return r;
  },
  perspective(fovy, aspect, near, far) {
    const f = 1 / Math.tan(fovy / 2), nf = 1 / (near - far), m = new Float32Array(16);
    m[0] = f / aspect; m[5] = f; m[10] = (far + near) * nf; m[11] = -1; m[14] = 2 * far * near * nf;
    return m;
  },
  ortho(l, r, b, t, n, f) {
    const m = new Float32Array(16);
    m[0] = 2 / (r - l); m[5] = 2 / (t - b); m[10] = -2 / (f - n);
    m[12] = -(r + l) / (r - l); m[13] = -(t + b) / (t - b); m[14] = -(f + n) / (f - n); m[15] = 1;
    return m;
  },
  lookAt(eye, target, up) {
    let z = V3.norm(V3.sub(eye, target));
    let x = V3.cross(up, z);
    if (V3.len(x) < 1e-6) x = V3.cross([0, 0, 1], z);
    x = V3.norm(x);
    const y = V3.cross(z, x);
    const m = new Float32Array(16);
    m[0] = x[0]; m[1] = y[0]; m[2] = z[0];
    m[4] = x[1]; m[5] = y[1]; m[6] = z[1];
    m[8] = x[2]; m[9] = y[2]; m[10] = z[2];
    m[12] = -V3.dot(x, eye); m[13] = -V3.dot(y, eye); m[14] = -V3.dot(z, eye); m[15] = 1;
    return m;
  },
  invert(a) {
    const m = new Float32Array(16);
    const a00 = a[0], a01 = a[1], a02 = a[2], a03 = a[3], a10 = a[4], a11 = a[5], a12 = a[6], a13 = a[7];
    const a20 = a[8], a21 = a[9], a22 = a[10], a23 = a[11], a30 = a[12], a31 = a[13], a32 = a[14], a33 = a[15];
    const b00 = a00 * a11 - a01 * a10, b01 = a00 * a12 - a02 * a10, b02 = a00 * a13 - a03 * a10;
    const b03 = a01 * a12 - a02 * a11, b04 = a01 * a13 - a03 * a11, b05 = a02 * a13 - a03 * a12;
    const b06 = a20 * a31 - a21 * a30, b07 = a20 * a32 - a22 * a30, b08 = a20 * a33 - a23 * a30;
    const b09 = a21 * a32 - a22 * a31, b10 = a21 * a33 - a23 * a31, b11 = a22 * a33 - a23 * a32;
    let det = b00 * b11 - b01 * b10 + b02 * b09 + b03 * b08 - b04 * b07 + b05 * b06;
    if (!det) return M4.ident();
    det = 1 / det;
    m[0] = (a11 * b11 - a12 * b10 + a13 * b09) * det; m[1] = (a02 * b10 - a01 * b11 - a03 * b09) * det;
    m[2] = (a31 * b05 - a32 * b04 + a33 * b03) * det; m[3] = (a22 * b04 - a21 * b05 - a23 * b03) * det;
    m[4] = (a12 * b08 - a10 * b11 - a13 * b07) * det; m[5] = (a00 * b11 - a02 * b08 + a03 * b07) * det;
    m[6] = (a32 * b02 - a30 * b05 - a33 * b01) * det; m[7] = (a20 * b05 - a22 * b02 + a23 * b01) * det;
    m[8] = (a10 * b10 - a11 * b08 + a13 * b06) * det; m[9] = (a01 * b08 - a00 * b10 - a03 * b06) * det;
    m[10] = (a30 * b04 - a31 * b02 + a33 * b00) * det; m[11] = (a21 * b02 - a20 * b04 - a23 * b00) * det;
    m[12] = (a11 * b07 - a10 * b09 - a12 * b06) * det; m[13] = (a00 * b09 - a01 * b07 + a02 * b06) * det;
    m[14] = (a31 * b01 - a30 * b03 - a32 * b00) * det; m[15] = (a20 * b03 - a21 * b01 + a22 * b00) * det;
    return m;
  },
  // Compose translation * rotY(ry) * rotX(rx) * rotZ(rz) * scale(s)
  trs(tx, ty, tz, ry = 0, rx = 0, rz = 0, sx = 1, sy = 1, sz = 1) {
    const cy = Math.cos(ry), sy_ = Math.sin(ry), cx = Math.cos(rx), sx_ = Math.sin(rx), cz = Math.cos(rz), sz_ = Math.sin(rz);
    // R = Ry * Rx * Rz
    const r00 = cy * cz + sy_ * sx_ * sz_, r01 = -cy * sz_ + sy_ * sx_ * cz, r02 = sy_ * cx;
    const r10 = cx * sz_, r11 = cx * cz, r12 = -sx_;
    const r20 = -sy_ * cz + cy * sx_ * sz_, r21 = sy_ * sz_ + cy * sx_ * cz, r22 = cy * cx;
    const m = new Float32Array(16);
    m[0] = r00 * sx; m[1] = r10 * sx; m[2] = r20 * sx;
    m[4] = r01 * sy; m[5] = r11 * sy; m[6] = r21 * sy;
    m[8] = r02 * sz; m[9] = r12 * sz; m[10] = r22 * sz;
    m[12] = tx; m[13] = ty; m[14] = tz; m[15] = 1;
    return m;
  },
  point(m, p) {
    const x = p[0], y = p[1], z = p[2];
    const w = m[3] * x + m[7] * y + m[11] * z + m[15];
    return [(m[0] * x + m[4] * y + m[8] * z + m[12]) / w, (m[1] * x + m[5] * y + m[9] * z + m[13]) / w, (m[2] * x + m[6] * y + m[10] * z + m[14]) / w];
  },
  dir(m, d) {
    return [m[0] * d[0] + m[4] * d[1] + m[8] * d[2], m[1] * d[0] + m[5] * d[1] + m[9] * d[2], m[2] * d[0] + m[6] * d[1] + m[10] * d[2]];
  },
};

// Deterministic PRNG so the cabin looks identical on every load
function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// sRGB hex -> [r,g,b] 0..255
function hexRGB(h) {
  const v = parseInt(h.replace('#', ''), 16);
  return [(v >> 16) & 255, (v >> 8) & 255, v & 255];
}
// sRGB hex -> linear float triple
function hexLin(h, k = 1) {
  const c = hexRGB(h);
  return c.map((x) => Math.pow(x / 255, 2.2) * k);
}
