// ------------------------------------------------------------------
// Procedural textures (generated at load; no external image assets)
//  Detail layers are RGBA: RG = tangent normal (xy), B = albedo mod, A = roughness mod
// ------------------------------------------------------------------
const LAYER = { none: 0, fabric: 1, leather: 2, carpet: 3, plastic: 4, brushed: 5, marble: 6, vinyl: 7, grille: 8, yagasuri: 9, wood: 10, yMosaic: 11, atlasLit: 14, atlasGlow: 15, yJacq: 16, pyFleck: 17, tweed: 18, ashGrain: 19, fWood: 20, fTweed: 21, yCarpet: 22, pyConfetti: 23, yDiamond: 24, yFleck: 25 };
const N_LAYERS = 26;
// layers >= 16 take their pattern from a photo swatch when PHOTO_TEX is embedded (build.py), else procedural
const PHOTO_LAYERS = {
  16: 'y_tick',
  17: 'py_back',
  18: 'j_tweed',
  19: 'j_ash',
  20: 'f_wood',
  21: 'f_tweed',
  22: 'y_carpet',
  23: 'py_confetti',
  24: 'y_diamond',
  25: 'y_fleck',   // econ w5: petal-fleck Y fabric
};
let PHOTO_PIX = null;
// photo pattern strength per layer (1 = as photographed). QA r1 (relative luminance SD measured on the photos):
//  17 PY dash weave 0.8 (clean re-cut, py_37305), 18 J tweed 0.35 (SD 0.17-0.23 on c_27315 / omaat_room_13 vs 0.42 rendered),
//  19 J ash 0.3 (SD 0.025-0.05 on omaat_room_10 / c_27313), 21 F tweed 0.5 (reads as a uniform fine weave, omaat_f11 / f2),
//  20 F wood 0.7 (near-black veneer with fine lighter streaks, omaat_f60)
// QA r2: 17 PY dashes 1.0 (high-passed re-cut; the light dashes carry the brightness, py_37301 p10/p90 100/201),
//  18 J tweed 0.5 (luminance-only re-cut, fine weave), 19 J ash 2.0 (c_27305 cabinet: high-pass SD 6.1 % in sRGB = ~13 %
//  linear vs 6.3 % in the column-normalised swatch -> x2) [D], 23 PY / Y confetti 1.0 (white flakes ~220 on a 55-65
//  ground, py_37305)
const PHOTO_GAIN = {
  17: 1.0,   // PY: synthesised ANA dash-grid tile (make_swatches synth_py_back), contrast measured on py_37305 [D]
  18: 0.5,
  19: 2.0,
  20: 0.7,
  21: 0.5,
  23: 1.0,
};
// swatches stored as ratio / ENC instead of ratio / 2 (test/make_swatches.py ENC): the Y ticks are ~10x the navy ground
// in linear light and clipped away at 2x. photoBase() lifts the material colour by ENC/2 to compensate.
// QA r2: 5 (was 8) so the brighter cobalt base (#5468a8) lifted by ENC/2 stays below 1 in blue
// py_back 4 / py_confetti 6: white dashes / flakes 4.6x / ~17x their charcoal ground (py_37301 / 37305)
const PHOTO_ENC = {
  y_tick: 5,
  y_diamond: 5,
  y_fleck: 5,
  py_back: 4,
  py_confetti: 6,
};
function photoBase(hex, name) {
  const k = (typeof PHOTO_TEX !== 'undefined' && PHOTO_TEX && PHOTO_TEX[name] && PHOTO_ENC[name]) ? PHOTO_ENC[name] / 2 : 1;
  if (k === 1) return hex;
  // shader decode: lin = c^2 (0.31 c + 0.69) (04_shaders toLin); scale in linear light, re-encode by bisection
  const enc = (l) => { let a = 0, b = 1; for (let i = 0; i < 30; i++) { const m = (a + b) / 2; if (m * m * (0.31 * m + 0.69) < l) a = m; else b = m; } return a; };
  return '#' + hexRGB(hex).map((v) => { const c = v / 255; return Math.round(clamp(enc(c * c * (0.31 * c + 0.69) * k), 0, 1) * 255).toString(16).padStart(2, '0'); }).join('');
}
// per-layer params: [scale (tiles per meter), normal strength, albedo strength, roughness strength]
const LAYER_PARAMS = {
  1: [22, 0.26, 0.14, 0.18], 2: [9, 0.32, 0.14, 0.3], 3: [3.2, 0.7, 0.5, 0.2], 4: [9, 0.1, 0.04, 0.12],
  5: [3.0, 0.1, 0.06, 0.22], 6: [1.1, 0.05, 0.9, 0.2], 7: [2.0, 0.15, 0.45, 0.2], 8: [22, 0.8, 0.9, 0.2],
  // 9 ANA J pillow check jacquard: 8 x 8 checks of 0.028 m per tile -> 4.46 tiles/m, two tones #32355d / #45508a
  //   (c_27303, omaat_room_13) -> albedo strength 0.3 [D]
  // 11 Y mosaic fabric (third Y variant, y_47302 left seat / y_47306 right seat): checker of dense / sparse short pale
  //   dashes, 0.2 m tile (6 x 6 checks of ~33 mm, measured against the 0.27 m flap) [D]
  9: [4.46, 0.15, 0.16, 0.15], 10: [2.4, 0.12, 0.28, 0.25], 11: [5.0, 0.12, 1.5, 0.15],   // 11 albedo 1.5: econ w2 (q15 p10/p90 57/94 vs photo 41/107)
  // photo-derived fabrics (ANA seat pages, see REFERENCE777.md): Y blue tick jacquard, PY charcoal/white fleck, J/F tweed, J ash
  // Y normal strength 0.12 (was 0.3: read as a knit; the Y jacquard is a flat woven face, y_47306)
  16: [5.5, 0.12, 1.4, 0.15], 17: [7.5, 0.3, 0.8, 0.15], 18: [14, 0.5, 0.35, 0.2], 19: [1.6, 0.06, 0.22, 0.2],
  20: [2.4, 0.08, 0.28, 0.25], 21: [14, 0.5, 0.35, 0.2], 22: [3.2, 0.7, 0.5, 0.2], 23: [5.0, 0.3, 0.8, 0.15], 24: [5.5, 0.12, 1.4, 0.15],
  25: [5.0, 0.12, 1.4, 0.15],   // econ w5: Y petal fleck (0.2 m tile)
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
  // 9 navy check jacquard of ANA's J pillows (room QA w1: small offset checks ~2.8 cm, not chevrons; c_27303,
  //    omaat_room_13): 8 x 8 checks per tile, alternate rows offset half a check, each check with a soft woven sheen
  L[9] = makeLayer(S, (u, v) => {
    const n = 8, j = Math.floor(v * n), fu = (u * n + (j & 1) * 0.5) % 1, fv = v * n - j;
    return 0.5 + 0.25 * Math.sin(fu * Math.PI) * Math.sin(fv * Math.PI) * ((Math.floor(u * n + (j & 1) * 0.5) + j) & 1 ? 1 : -1);
  }, (u, v) => {
    const n = 8, j = Math.floor(v * n), x = u * n + (j & 1) * 0.5, i = Math.floor(x), fu = x - i, fv = v * n - j;
    const on = ((i + j) & 1) === 1, sh = Math.sin(fu * Math.PI) * Math.sin(fv * Math.PI);
    return clamp((on ? 0.62 + 0.18 * sh : 0.3 + 0.1 * sh) + 0.06 * (vnoise(u * 128, v * 128, 128, 71) - 0.5), 0, 1);
  }, () => 0.5, 0.6);
  // 10 wood/laminate grain
  L[10] = makeLayer(S, (u, v) => 0.5, (u, v) => {
    const g = Math.sin((v * 40 + fbm(u * 2, v * 3, 2, 4, 81) * 1.2) * Math.PI * 2) * 0.5 + 0.5;
    return clamp(0.45 + g * 0.2 + 0.1 * (fbm(u * 8, v * 30, 8, 2, 82) - 0.5), 0, 1);
  }, () => 0.5, 0.2);
  // 11 Y mosaic: 6 x 6 checks per tile, dense / sparse rows of short pale horizontal dashes on the cobalt ground
  //    (y_47302 left seat, y_47306 right seat); ground ~0.6 x, dashes ~2 x the material colour (mean ~1)
  L[11] = makeLayer(S, (u, v) => 0.5 + 0.3 * (vnoise(u * 180, v * 180, 180, 131) - 0.5), (u, v) => {
    const nc = 6, ci = Math.floor(u * nc), cj = Math.floor(v * nc);
    const dense = ((ci + cj) & 1) === 0;
    const nv = 60, j = Math.floor(v * nv), fv = v * nv - j;
    const nu = 42, i = Math.floor(u * nu + hash2(j, 3, 132) * 2), fu = u * nu + hash2(j, 3, 132) * 2 - i;
    const on = hash2(i, j, 133) < (dense ? 0.55 : 0.12) && fv > 0.3 && fv < 0.75 && fu > 0.15 && fu < 0.9;
    return clamp((on ? 0.95 + 0.05 * hash2(i, j, 134) : 0.3) + 0.05 * (vnoise(u * 90, v * 90, 90, 135) - 0.5), 0, 1);
  }, () => 0.5, 0.6);
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
  L[20] = L[10]; L[21] = L[18]; L[22] = L[3]; L[23] = L[17]; L[24] = L[16]; L[25] = L[16];
  // photo swatches: tile scale from the swatch's physical size; normal + roughness from its luminance
  if (PHOTO_PIX) for (const [k, name] of Object.entries(PHOTO_LAYERS)) {
    const px = PHOTO_PIX[name]; if (!px) continue;
    LAYER_PARAMS[k] = [1 / PHOTO_TEX[name].size, LAYER_PARAMS[k][1], PHOTO_GAIN[k] ?? 1, LAYER_PARAMS[k][3]];
    const lum = (u, v) => { const i = ((Math.floor(v * 256) & 255) * 256 + (Math.floor(u * 256) & 255)) * 4; return (px[i] + px[i + 1] + px[i + 2]) / 765; };
    L[k] = makeLayer(S, lum, () => 0.5, (u, v, h) => 0.5 + 0.3 * (0.5 - h), 0.9);
  }
  return L;
}
// RGB photo-swatch array (layer k-16), colour relative to the swatch mean x0.5; neutral grey where no photo
function buildPhotoLayers(S = 256) {
  const out = [];
  for (let k = 16; k < N_LAYERS; k++) {
    const px = PHOTO_PIX && PHOTO_PIX[PHOTO_LAYERS[k]];
    const d = new Uint8Array(S * S * 4);
    if (px) d.set(px); else d.fill(128);
    out.push(d);
  }
  return out;
}
async function loadPhotoTex() {
  if (typeof PHOTO_TEX === 'undefined' || !PHOTO_TEX) return;
  const cv = document.createElement('canvas'); cv.width = cv.height = 256;
  const g = cv.getContext('2d', { willReadFrequently: true });
  PHOTO_PIX = {};
  for (const [name, t] of Object.entries(PHOTO_TEX)) {
    const im = new Image(); im.src = t.src;
    try { await im.decode(); } catch (e) { continue; }
    g.clearRect(0, 0, 256, 256); g.drawImage(im, 0, 0, 256, 256);
    PHOTO_PIX[name] = g.getImageData(0, 0, 256, 256).data;
  }
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
