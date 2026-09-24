// ------------------------------------------------------------------
// Procedural textures (generated at load; no external image assets)
//  Detail layers are RGBA: RG = tangent normal (xy), B = albedo mod, A = roughness mod
// ------------------------------------------------------------------
const LAYER = { none: 0, fabric: 1, leather: 2, carpet: 3, plastic: 4, brushed: 5, marble: 6, vinyl: 7, grille: 8, knit: 9, wood: 10, perf: 11, atlasLit: 14, atlasGlow: 15, yJacq: 16, pyFleck: 17, tweed: 18, ashGrain: 19 };
const N_LAYERS = 20;
// per-layer params: [scale (tiles per meter), normal strength, albedo strength, roughness strength]
const LAYER_PARAMS = {
  1: [22, 0.26, 0.14, 0.18], 2: [9, 0.32, 0.14, 0.3], 3: [3.2, 0.7, 0.5, 0.2], 4: [9, 0.1, 0.04, 0.12],
  5: [3.0, 0.1, 0.06, 0.22], 6: [1.1, 0.05, 0.9, 0.2], 7: [2.0, 0.15, 0.45, 0.2], 8: [22, 0.8, 0.9, 0.2],
  9: [20, 0.4, 0.2, 0.2], 10: [2.4, 0.12, 0.28, 0.25], 11: [7, 0.45, 0.28, 0.3],
  // photo-derived fabrics (ANA seat pages, see REFERENCE777.md): Y blue tick jacquard, PY charcoal/white fleck, J/F tweed, J ash
  16: [5.5, 0.3, 1.4, 0.15], 17: [7.5, 0.3, 0.8, 0.15], 18: [14, 0.5, 0.35, 0.2], 19: [1.6, 0.06, 0.22, 0.2],
};

function hash2(ix, iy, seed) {
  let h = (ix * 374761393 + iy * 668265263 + seed * 144269504) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  h ^= h >>> 16;
  return (h >>> 0) / 4294967296;
}
// tileable value noise, period p (in lattice units)
function vnoise(x, y, p, seed) {
  const x0 = Math.floor(x), y0 = Math.floor(y), fx = x - x0, fy = y - y0;
  const u = fx * fx * (3 - 2 * fx), v = fy * fy * (3 - 2 * fy);
  const m = (a) => ((a % p) + p) % p;
  const a = hash2(m(x0), m(y0), seed), b = hash2(m(x0 + 1), m(y0), seed), c = hash2(m(x0), m(y0 + 1), seed), d = hash2(m(x0 + 1), m(y0 + 1), seed);
  return lerp(lerp(a, b, u), lerp(c, d, u), v);
}
function fbm(x, y, p, oct, seed) {
  let s = 0, a = 0.5, f = 1, n = 0;
  for (let o = 0; o < oct; o++) { s += a * vnoise(x * f, y * f, p * f, seed + o * 17); n += a; a *= 0.5; f *= 2; }
  return s / n;
}
// tileable worley (F1, F2)
function worley(x, y, p, seed) {
  const x0 = Math.floor(x), y0 = Math.floor(y);
  let f1 = 9, f2 = 9;
  for (let j = -1; j <= 1; j++) for (let i = -1; i <= 1; i++) {
    const cx = x0 + i, cy = y0 + j;
    const mx = ((cx % p) + p) % p, my = ((cy % p) + p) % p;
    const px = cx + hash2(mx, my, seed), py = cy + hash2(mx, my, seed + 7);
    const d = Math.hypot(px - x, py - y);
    if (d < f1) { f2 = f1; f1 = d; } else if (d < f2) f2 = d;
  }
  return [f1, f2];
}

// Build RGBA layer from height function h(u,v) in [0,1], plus albedo & rough mods
function makeLayer(S, hf, af, rf, nstr = 1) {
  const H = new Float32Array(S * S), A = new Float32Array(S * S), R = new Float32Array(S * S);
  for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) {
    const u = x / S, v = y / S, k = y * S + x;
    H[k] = hf(u, v);
    A[k] = af ? af(u, v, H[k]) : 0.5;
    R[k] = rf ? rf(u, v, H[k]) : 0.5;
  }
  const out = new Uint8Array(S * S * 4);
  for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) {
    const k = y * S + x;
    const hl = H[y * S + ((x + S - 1) % S)], hr = H[y * S + ((x + 1) % S)];
    const hd = H[((y + S - 1) % S) * S + x], hu = H[((y + 1) % S) * S + x];
    let nx = (hl - hr) * nstr * S / 64, ny = (hd - hu) * nstr * S / 64;
    const l = Math.hypot(nx, ny, 1);
    nx /= l; ny /= l;
    out[k * 4] = clamp(Math.round((nx * 0.5 + 0.5) * 255), 0, 255);
    out[k * 4 + 1] = clamp(Math.round((ny * 0.5 + 0.5) * 255), 0, 255);
    out[k * 4 + 2] = clamp(Math.round(A[k] * 255), 0, 255);
    out[k * 4 + 3] = clamp(Math.round(R[k] * 255), 0, 255);
  }
  return out;
}

function buildDetailLayers(S = 256) {
  const L = [];
  const flat = new Uint8Array(S * S * 4);
  for (let i = 0; i < S * S; i++) { flat[i * 4] = 128; flat[i * 4 + 1] = 128; flat[i * 4 + 2] = 128; flat[i * 4 + 3] = 128; }
  for (let i = 0; i < N_LAYERS; i++) L.push(flat);
  // 1 fabric: basket/twill weave with fibre noise
  const nT = 40;
  L[1] = makeLayer(S, (u, v) => {
    const i = Math.floor(u * nT), j = Math.floor(v * nT), fu = u * nT - i, fv = v * nT - j;
    const over = ((i + (j >> 1)) & 1) === 0;
    const b = over ? Math.sin(Math.PI * fu) : Math.sin(Math.PI * fv);
    return 0.35 + 0.5 * b * (0.8 + 0.2 * vnoise(u * 160, v * 160, 160, 3)) + 0.15 * vnoise(u * 32, v * 32, 32, 5);
  }, (u, v) => 0.5 + 0.35 * (fbm(u * 8, v * 8, 8, 3, 11) - 0.5) + 0.08 * (vnoise(u * 90, v * 90, 90, 2) - 0.5), (u, v, h) => 0.5 + 0.2 * (h - 0.5), 2.2);
  // 2 leather: worley creases
  L[2] = makeLayer(S, (u, v) => {
    const [f1, f2] = worley(u * 28, v * 28, 28, 9);
    return clamp((f2 - f1) * 1.6, 0, 1) * 0.8 + 0.2 * vnoise(u * 64, v * 64, 64, 4);
  }, (u, v, h) => 0.5 + 0.25 * (h - 0.5) + 0.15 * (fbm(u * 4, v * 4, 4, 3, 21) - 0.5), (u, v, h) => 0.45 + 0.35 * (0.6 - h), 1.3);
  // 3 carpet: cut pile + small repeating diamond motif (albedo)
  L[3] = makeLayer(S, (u, v) => 0.5 + 0.45 * (vnoise(u * 128, v * 128, 128, 13) - 0.5) + 0.3 * (vnoise(u * 48, v * 48, 48, 14) - 0.5), (u, v) => {
    const nx = u * 6, ny = v * 6;
    const fx = nx - Math.floor(nx) - 0.5, fy = ny - Math.floor(ny) - 0.5;
    const d = Math.abs(fx) + Math.abs(fy);
    const motif = smooth(0.34, 0.30, Math.abs(d - 0.32)) * 0.55 + (d < 0.07 ? 0.5 : 0);
    const cross = (Math.abs(fx) < 0.02 || Math.abs(fy) < 0.02) ? 0.12 : 0;
    return clamp(0.42 + motif * 0.45 + cross + 0.25 * (vnoise(u * 128, v * 128, 128, 15) - 0.5) + 0.12 * (fbm(u * 5, v * 5, 5, 3, 16) - 0.5), 0, 1);
  }, () => 0.5, 1.6);
  // 4 plastic: orange-peel stipple
  L[4] = makeLayer(S, (u, v) => fbm(u * 48, v * 48, 48, 2, 31), (u, v) => 0.5 + 0.06 * (fbm(u * 6, v * 6, 6, 2, 32) - 0.5), (u, v, h) => 0.5 + 0.2 * (h - 0.5), 0.8);
  // 5 brushed metal: streaks along u
  L[5] = makeLayer(S, (u, v) => 0.5 + 0.5 * (vnoise(u * 2, v * 220, 220, 41) - 0.5) + 0.2 * (vnoise(u * 8, v * 80, 80, 42) - 0.5), (u, v, h) => 0.5 + 0.3 * (h - 0.5), (u, v, h) => 0.5 + 0.25 * (vnoise(u * 3, v * 120, 120, 43) - 0.5), 0.6);
  // 6 marble: veins in albedo
  L[6] = makeLayer(S, () => 0.5, (u, v) => {
    const t = fbm(u * 4, v * 4, 4, 5, 51);
    const vein = Math.abs(Math.sin((u * 2 + v * 1 + t * 2.4) * Math.PI * 2));
    const vv = Math.pow(1 - vein, 14) * 0.7 + Math.pow(1 - Math.abs(Math.sin((u * 5 - v * 3 + t * 3) * Math.PI)), 30) * 0.3;
    return clamp(0.62 - vv * 0.55 + 0.08 * (fbm(u * 16, v * 16, 16, 3, 52) - 0.5), 0, 1);
  }, () => 0.5, 0.2);
  // 7 vinyl floor: speckles
  L[7] = makeLayer(S, (u, v) => 0.5 + 0.2 * (vnoise(u * 96, v * 96, 96, 61) - 0.5), (u, v) => {
    const n1 = vnoise(u * 110, v * 110, 110, 62), n2 = vnoise(u * 70, v * 70, 70, 63);
    return clamp(0.5 + (n1 > 0.8 ? 0.35 : 0) - (n2 > 0.84 ? 0.3 : 0) + 0.1 * (fbm(u * 6, v * 6, 6, 2, 64) - 0.5), 0, 1);
  }, () => 0.5, 0.5);
  // 8 grille: round perforations
  L[8] = makeLayer(S, (u, v) => {
    const n = 16, fx = u * n - Math.floor(u * n) - 0.5, fy = v * n - Math.floor(v * n) - 0.5;
    const d = Math.hypot(fx, fy);
    return d < 0.28 ? 0.0 : d < 0.34 ? (d - 0.28) / 0.06 : 1.0;
  }, (u, v) => {
    const n = 16, fx = u * n - Math.floor(u * n) - 0.5, fy = v * n - Math.floor(v * n) - 0.5;
    return Math.hypot(fx, fy) < 0.3 ? 0.08 : 0.55;
  }, () => 0.5, 1.2);
  // 9 knit (headrest covers): rib pattern
  L[9] = makeLayer(S, (u, v) => {
    const r = Math.sin(u * Math.PI * 2 * 48) * 0.5 + 0.5;
    return r * 0.7 + 0.3 * vnoise(u * 96, v * 24, 96, 71);
  }, (u, v) => 0.5 + 0.12 * (vnoise(u * 16, v * 16, 16, 72) - 0.5), () => 0.5, 1.4);
  // 10 wood/laminate grain
  L[10] = makeLayer(S, (u, v) => 0.5, (u, v) => {
    const g = Math.sin((v * 40 + fbm(u * 2, v * 3, 2, 4, 81) * 1.2) * Math.PI * 2) * 0.5 + 0.5;
    return clamp(0.45 + g * 0.2 + 0.1 * (fbm(u * 8, v * 30, 8, 2, 82) - 0.5), 0, 1);
  }, () => 0.5, 0.2);
  // 11 perforated leather: fine grain + a regular grid of small perforations
  L[11] = makeLayer(S, (u, v) => {
    const n = 26, fx = u * n - Math.floor(u * n) - 0.5, fy = v * n - Math.floor(v * n) - 0.5;
    const hole = Math.hypot(fx, fy) < 0.16 ? -0.55 : 0;
    const [f1, f2] = worley(u * 22, v * 22, 22, 19);
    return 0.55 + hole + clamp((f2 - f1) * 1.2, 0, 1) * 0.25;
  }, (u, v) => {
    const n = 26, fx = u * n - Math.floor(u * n) - 0.5, fy = v * n - Math.floor(v * n) - 0.5;
    return Math.hypot(fx, fy) < 0.16 ? 0.22 : 0.5 + 0.1 * (fbm(u * 4, v * 4, 4, 3, 23) - 0.5);
  }, () => 0.5, 1.1);
  // 16 ANA economy jacquard: royal blue ground, short light-blue ticks; ticks cluster into a diamond lattice
  //    (seat-to-seat pattern variation per ANA/reviews; lattice density from y_47306 close-up)
  L[16] = makeLayer(S, (u, v) => 0.5 + 0.3 * (vnoise(u * 180, v * 180, 180, 91) - 0.5), (u, v) => {
    const nu = 34, nv = 22;
    const i = Math.floor(u * nu), j = Math.floor(v * nv), fu = u * nu - i - 0.5, fv = v * nv - j - 0.5;
    const off = (hash2(i, j, 92) - 0.5) * 0.4;
    // lattice: diamonds of period 1/4 tile
    const du = Math.abs(((u * 4) % 1) - 0.5), dv = Math.abs(((v * 4) % 1) - 0.5);
    const inDiamond = du + dv < 0.3 ? 1 : 0;
    const dens = 0.30 + 0.45 * inDiamond;
    const tick = hash2(i, j, 93) < dens && Math.abs(fu + off * 0.5) < 0.13 && Math.abs(fv - off) < 0.34 ? 1 : 0;
    return clamp(0.42 + tick * (0.34 + 0.12 * hash2(i, j, 94)) + 0.06 * (vnoise(u * 60, v * 60, 60, 95) - 0.5), 0, 1);
  }, () => 0.5, 0.8);
  // 17 ANA premium economy: charcoal ground with white broken horizontal dashes (heather) - py_37305 close-up
  L[17] = makeLayer(S, (u, v) => 0.5 + 0.3 * (vnoise(u * 180, v * 180, 180, 101) - 0.5), (u, v) => {
    const nv = 70, j = Math.floor(v * nv);
    const seg = 10 + Math.floor(hash2(j, 0, 102) * 14);
    const i = Math.floor(u * seg + hash2(j, 1, 103) * 3);
    const on = hash2(i, j, 104) < 0.42 + 0.25 * (fbm(u * 3, v * 3, 3, 2, 105) - 0.5);
    const fv = v * nv - j;
    const dash = on && fv > 0.25 && fv < 0.8 ? 1 : 0;
    return clamp(0.36 + dash * 0.42 + 0.05 * (vnoise(u * 90, v * 90, 90, 106) - 0.5), 0, 1);
  }, () => 0.5, 0.8);
  // 18 tweed / boucle (THE Room + THE Suite seat textile): coarse nubby weave with light and dark yarns
  L[18] = makeLayer(S, (u, v) => {
    const n = 64, i = Math.floor(u * n), j = Math.floor(v * n), fu = u * n - i, fv = v * n - j;
    const over = ((i + j) & 1) === 0;
    return 0.3 + 0.45 * (over ? Math.sin(Math.PI * fu) : Math.sin(Math.PI * fv)) + 0.25 * vnoise(u * 128, v * 128, 128, 111);
  }, (u, v) => {
    const k = vnoise(u * 128, v * 128, 128, 112);
    return clamp(0.5 + (k > 0.72 ? 0.35 : 0) - (k < 0.22 ? 0.25 : 0) + 0.08 * (fbm(u * 8, v * 8, 8, 2, 113) - 0.5), 0, 1);
  }, (u, v, h) => 0.5 + 0.2 * (h - 0.5), 1.4);
  // 19 light Japanese ash (THE Room): fine, straight, dense streaks - no wavy figure (c_27305/27308/27313)
  L[19] = makeLayer(S, () => 0.5, (u, v) => {
    const w = 0.012 * (fbm(u * 1, v * 4, 1, 2, 121) - 0.5);
    const a = vnoise(u * 3, (v + w) * 160, 160, 122), b = vnoise(u * 6, (v + w) * 64, 64, 123);
    return clamp(0.5 + 0.55 * (a - 0.5) + 0.3 * (b - 0.5), 0, 1);
  }, () => 0.5, 0.2);
  return L;
}

// Tileable cloud noise texture (R: fbm, G: detail fbm), 256^2
function buildCloudNoise(S = 256) {
  const d = new Uint8Array(S * S * 4);
  for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) {
    const u = x / S, v = y / S, k = (y * S + x) * 4;
    const a = fbm(u * 4, v * 4, 4, 6, 101);
    const b = fbm(u * 16, v * 16, 16, 4, 202);
    const [w1] = worley(u * 6, v * 6, 6, 303);
    d[k] = clamp(Math.round(a * 255), 0, 255);
    d[k + 1] = clamp(Math.round(b * 255), 0, 255);
    d[k + 2] = clamp(Math.round((1 - clamp(w1, 0, 1)) * 255), 0, 255);
    d[k + 3] = 255;
  }
  return d;
}
