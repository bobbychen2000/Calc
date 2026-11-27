// Look module "furniture": materials of the outdoor furniture / yard objects (model/furniture.py), registered by
// name (see ../materials.js for the contract).  Every texture is generated here at load from seeded noise: no image
// files, no network, nothing taken from the photos.
//
// Conventions (the same as the surfaces family): a texture is a tile of W x H METRES (the kit's UVs are metres):
// repeat = (1 / W, 1 / H), RepeatWrapping, flipY = false, so row 0 of a texture is its TOP and rows run down a wall;
// colour maps hold sRGB bytes of LINEAR albedo factors and are multiplied by the material's colour; normal maps are
// built from height fields in metres (a real slope, no "strength" guess) with +G along +v.
//
// Colours are linear albedos measured on the listing photos as ratios to the white siding in the same light
// (p25 for the dining and teak sets, p27 for the cabana lounge, p26 for the fireplace and heat pump), then checked
// in the test zone model/zones/test_furniture.py under the stage's own day light.
//
// Material                 texture tile (m)       what it shows
//   furniture_dark         0.06 x 0.06 grit       charcoal powder coat (dining set)
//   furn_black             0.06 x 0.06 grit       near-black powder coat (cabana lounge frames, fire-bowl plinth)
//   furn_slat_grey         1.20 x 0.30 grain      grey wood-look composite slats: grain along u
//   furniture_wood         1.20 x 0.30 grain      oiled teak: grain along u
//   furn_wood_taupe        1.20 x 0.30 grain      weathered teak-look slab
//   furn_wood_light        1.20 x 0.30 grain      light hardwood of the hoop chairs
//   cushion, furn_fabric_slate, furn_fabric_charcoal, furn_fabric_white
//                          0.70 melange + 0.10 weave normal     upholstery
//   *_edge                 0.40 x 0.10            a cushion's side band: one tile in v from piping to piping
//   furn_rope              0.08 x 0.08            four twisted cords per tile, running along v
//   fireplace_stone        1.28 x 1.28            stacked ledgestone, 32 courses of 40 mm (course joints at v = k * 0.04)
//   fireplace_firebrick    0.456 x 0.456          herringbone of 57 x 228 mm splits, laid at 45 degrees
//   firebowl_concrete, furn_plaster_white, pot_terracotta        0.90 x 0.90 mottle
//   firebowl_media         0.20 x 0.20            lava rock
//   rug_diamond            2.40 x 1.70            ONE rug: border + diamond lattice (the builder scales the UVs)
//   doormat_coir           0.25 x 0.25            coir
//   condenser_fan          1 x 1 (UV 0..1)        ONE fan opening: blades behind a wire guard
//   furn_ceramic_white, furn_bronze, fireplace_soot, condenser_white, utility_grey     plain
import * as THREE from 'three';

// ---------------------------------------------------------------------------------------------------- numbers
function prng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const LUT = (() => {
  const t = new Uint8Array(4097);
  for (let i = 0; i <= 4096; i++) {
    const v = i / 4096;
    t[i] = Math.round(255 * (v <= 0.0031308 ? 12.92 * v : 1.055 * Math.pow(v, 1 / 2.4) - 0.055));
  }
  return t;
})();
const srgb8 = (v) => LUT[v <= 0 ? 0 : v >= 1 ? 4096 : (v * 4096 + 0.5) | 0];
const smooth = (a, b, x) => { const t = x <= a ? 0 : x >= b ? 1 : (x - a) / (b - a); return t * t * (3 - 2 * t); };
const q = (ctx, n) => (ctx.quality === 'low' ? n >> 1 : n);

// generation times (ms), for the tests: window.__furnitureTex = { total, items }
const TIMES = { total: 0, items: {} };
if (typeof window !== 'undefined') window.__furnitureTex = TIMES;
const CACHE = new Map();
function shared(ctx, key, make) {
  const k = key + ':' + ctx.quality;
  if (!CACHE.has(k)) {
    const t0 = performance.now();
    CACHE.set(k, make());
    const dt = performance.now() - t0;
    TIMES.items[key] = dt;
    TIMES.total += dt;
  }
  return CACHE.get(k);
}

/** add tileable value noise (cx x cy cells over the tile, amplitude amp, values -amp .. amp) to out */
function addNoise(out, w, h, cx, cy, amp, seed) {
  const r = prng(seed), g = new Float32Array(cx * cy);
  for (let i = 0; i < g.length; i++) g[i] = r() * 2 - 1;
  const x0 = new Int32Array(w), x1 = new Int32Array(w), fx = new Float32Array(w);
  for (let x = 0; x < w; x++) {
    const u = x / w * cx, i = Math.floor(u), t = u - i;
    x0[x] = i % cx; x1[x] = (i + 1) % cx; fx[x] = t * t * (3 - 2 * t);
  }
  for (let y = 0; y < h; y++) {
    const v = y / h * cy, j = Math.floor(v), t = v - j, s = t * t * (3 - 2 * t);
    const a = (j % cy) * cx, b = ((j + 1) % cy) * cx, o = y * w;
    for (let x = 0; x < w; x++) {
      const f = fx[x], p = g[a + x0[x]], m = g[b + x0[x]];
      const top = p + (g[a + x1[x]] - p) * f, bot = m + (g[b + x1[x]] - m) * f;
      out[o + x] += amp * (top + (bot - top) * s);
    }
  }
  return out;
}

/** tangent-space normal map of a height field in METRES; du, dv = metres per pixel */
function normalData(hgt, w, h, du, dv) {
  const d = new Uint8Array(w * h * 4), ku = 0.5 / du, kv = 0.5 / dv;
  for (let y = 0; y < h; y++) {
    const up = ((y + h - 1) % h) * w, dn = ((y + 1) % h) * w, o = y * w;
    for (let x = 0; x < w; x++) {
      const nx = (hgt[o + (x + w - 1) % w] - hgt[o + (x + 1) % w]) * ku, ny = (hgt[up + x] - hgt[dn + x]) * kv;
      const inv = 127.5 / Math.sqrt(nx * nx + ny * ny + 1), i = (o + x) * 4;
      d[i] = 127.5 + nx * inv; d[i + 1] = 127.5 + ny * inv; d[i + 2] = 127.5 + inv; d[i + 3] = 255;
    }
  }
  return d;
}

function tex(ctx, data, w, h, W, H, srgb, clamp) {
  const t = new THREE.DataTexture(data, w, h, THREE.RGBAFormat, THREE.UnsignedByteType);
  t.wrapS = t.wrapT = clamp ? THREE.ClampToEdgeWrapping : THREE.RepeatWrapping;
  t.repeat.set(1 / W, 1 / H);
  t.magFilter = THREE.LinearFilter;
  t.minFilter = THREE.LinearMipmapLinearFilter;
  t.generateMipmaps = true;
  t.anisotropy = ctx.anisotropy || 1;
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  if (clamp) t.offset.set(0, 1);          // the GLB's v runs 0 .. -1 over a once-only texture: bring it into 0 .. 1
  t.needsUpdate = true;
  return t;
}
/** grey factor field (linear, 0 .. 1) -> colour map */
function greyTex(ctx, f, w, h, W, H) {
  const d = new Uint8Array(w * h * 4);
  for (let i = 0; i < w * h; i++) { const v = srgb8(f[i]); d[i * 4] = v; d[i * 4 + 1] = v; d[i * 4 + 2] = v; d[i * 4 + 3] = 255; }
  return tex(ctx, d, w, h, W, H, true);
}
const col = (c) => new THREE.Color().setRGB(c[0], c[1], c[2]);   // linear triple -> Color (working space)
const scl = (c, k) => [c[0] * k, c[1] * k, c[2] * k];

// ---------------------------------------------------------------------------------------------------- textures
// Powder coat: a faint orange-peel normal so highlights on the flat tubes are not dead straight.
function gritNormal(ctx) {
  return shared(ctx, 'grit', () => {
    const n = q(ctx, 128), h = new Float32Array(n * n);
    addNoise(h, n, n, 24, 24, 0.00006, 11); addNoise(h, n, n, 48, 48, 0.00003, 12);
    return tex(ctx, normalData(h, n, n, 0.06 / n, 0.06 / n), n, n, 0.06, 0.06, false);
  });
}

// Wood grain along u.  Returns { strong, soft } colour maps (mean factor 0.8) and a normal map; tile 1.20 x 0.30 m.
const GRAIN = { W: 1.2, H: 0.3, mean: 0.8 };
function grainTex(ctx) {
  return shared(ctx, 'grain', () => {
    const w = q(ctx, 512), h = q(ctx, 256), n = w * h;
    const f = new Float32Array(n);
    addNoise(f, w, h, 2, 7, 0.55, 21);            // broad bands of figure
    addNoise(f, w, h, 3, 22, 0.42, 22);
    addNoise(f, w, h, 5, 60, 0.30, 23);           // growth lines
    addNoise(f, w, h, 9, h >> 1, 0.20, 24);       // hairlines (2 px across the grain)
    const p = new Float32Array(n);
    addNoise(p, w, h, 40, h >> 1, 1.0, 25);       // pores: short dark dashes
    const strong = new Float32Array(n), soft = new Float32Array(n), hgt = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const t = Math.max(-1, Math.min(1, f[i] * 0.9));
      const pore = p[i] > 0.62 ? (p[i] - 0.62) * 1.6 : 0;
      strong[i] = GRAIN.mean * (1 + 0.30 * t) * (1 - 0.5 * pore);
      soft[i] = GRAIN.mean * (1 + 0.13 * t) * (1 - 0.3 * pore);
      hgt[i] = 0.00022 * t - 0.0004 * pore;
    }
    return { strong: greyTex(ctx, strong, w, h, GRAIN.W, GRAIN.H), soft: greyTex(ctx, soft, w, h, GRAIN.W, GRAIN.H),
      normal: tex(ctx, normalData(hgt, w, h, GRAIN.W / w, GRAIN.H / h), w, h, GRAIN.W, GRAIN.H, false) };
  });
}

// Upholstery: a melange colour map (tile 0.70 m, mean 0.9) and a plain-weave normal map (tile 0.10 m, 32 threads).
const FAB = { W: 0.7, mean: 0.9, weave: 0.1 };
function fabricTex(ctx) {
  return shared(ctx, 'fabric', () => {
    const n = q(ctx, 256), f = new Float32Array(n * n);
    addNoise(f, n, n, 5, 5, 0.035, 31); addNoise(f, n, n, 17, 17, 0.03, 32);
    addNoise(f, n, n, n >> 1, n >> 2, 0.05, 33); addNoise(f, n, n, n >> 2, n >> 1, 0.05, 34);   // yarn flecks, both ways
    for (let i = 0; i < n * n; i++) f[i] = FAB.mean * (1 + f[i]);
    const m = q(ctx, 256), th = m / 32, hgt = new Float32Array(m * m), jit = new Float32Array(m * m);
    addNoise(jit, m, m, 16, 16, 0.25, 35);
    for (let y = 0; y < m; y++) for (let x = 0; x < m; x++) {
      const i = Math.floor(x / th), j = Math.floor(y / th), a = x / th - i - 0.5, b = y / th - j - 0.5;
      const over = (i + j) & 1;                    // which yarn lies on top in this cell
      const across = over ? b : a, along = over ? a : b;
      const hh = Math.cos(Math.PI * across) * (0.65 + 0.35 * Math.cos(Math.PI * along));
      hgt[y * m + x] = 0.00028 * hh * (1 + jit[y * m + x]);
    }
    return { map: greyTex(ctx, f, n, n, FAB.W, FAB.W), normal: tex(ctx, normalData(hgt, m, m, FAB.weave / m, FAB.weave / m), m, m, FAB.weave, FAB.weave, false) };
  });
}
// A cushion's side band: 0.40 m x 0.10 m, piping (a 7 mm cord in the seam) along the top and bottom rows.
function fabricEdgeTex(ctx) {
  return shared(ctx, 'fabricEdge', () => {
    const w = q(ctx, 256), h = q(ctx, 64), f = new Float32Array(w * h), hgt = new Float32Array(w * h);
    addNoise(f, w, h, 6, 2, 0.03, 41); addNoise(f, w, h, w >> 1, h >> 1, 0.05, 42);
    const cord = 0.0045 / 0.1 * h;                // half the cord, in rows
    for (let y = 0; y < h; y++) {
      const d = Math.min(y + 0.5, h - y - 0.5);   // rows from the nearer seam
      const onCord = d < cord, crease = d >= cord && d < cord + Math.max(1.2, h / 40);
      const bulge = onCord ? Math.sqrt(1 - (d / cord) * (d / cord)) : 0;
      // the panel is drawn tight between the pipings: a slight hollow next to each cord
      const hollow = -0.0012 * Math.exp(-Math.max(0, d - cord) / (h * 0.09));
      for (let x = 0; x < w; x++) {
        const i = y * w + x;
        f[i] = FAB.mean * (1 + f[i]) * (crease ? 0.62 : onCord ? 0.96 + 0.06 * bulge : 1);
        hgt[i] = onCord ? 0.0035 * bulge : hollow;
      }
    }
    return { map: greyTex(ctx, f, w, h, 0.4, 0.1), normal: tex(ctx, normalData(hgt, w, h, 0.4 / w, 0.1 / h), w, h, 0.4, 0.1, false) };
  });
}

// Rope: four twisted cords per 0.08 m tile, running along v, dark between them.
function ropeTex(ctx) {
  return shared(ctx, 'rope', () => {
    const n = q(ctx, 128), f = new Float32Array(n * n), hgt = new Float32Array(n * n), p = n / 4;
    const jit = new Float32Array(n * n); addNoise(jit, n, n, 32, 32, 0.08, 51);
    for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
      const a = (x % p) / p - 0.5, i = y * n + x;                  // -0.5 .. 0.5 across one cord + gap
      const r = Math.abs(a) / 0.36;                                // the cord fills 72 % of the pitch
      if (r >= 1) { f[i] = 0.16; hgt[i] = -0.004; continue; }
      const round = Math.sqrt(1 - r * r);
      const twist = 0.5 + 0.5 * Math.cos(2 * Math.PI * (y / n * 6 + a * 1.6 + Math.floor(x / p) * 0.37));
      f[i] = (0.62 + 0.38 * round) * (0.86 + 0.14 * twist) * (1 + jit[i]);
      hgt[i] = 0.004 * round + 0.0006 * twist;
    }
    return { map: greyTex(ctx, f, n, n, 0.08, 0.08), normal: tex(ctx, normalData(hgt, n, n, 0.08 / n, 0.08 / n), n, n, 0.08, 0.08, false) };
  });
}

// Stacked ledgestone: 32 courses of 40 mm in a 1.28 m tile, pieces 90 .. 380 mm long, split faces that stand in and
// out by up to 9 mm, tight dark joints.  Colour map = factor (mean ~0.9) with a few cooler / greyer pieces.
const STONE = { W: 1.28, rows: 32 };
function stoneTex(ctx) {
  return shared(ctx, 'ledgestone', () => {
    const n = q(ctx, 1024), rows = STONE.rows, rh = n / rows, px = STONE.W / n, r = prng(77);
    const split = new Float32Array(n * n);
    addNoise(split, n, n, 14, 90, 1.0, 71);        // layered cleavage: long along the course
    addNoise(split, n, n, 40, 160, 0.6, 72);
    addNoise(split, n, n, 150, 300, 0.35, 73);
    const hgt = new Float32Array(n * n), d = new Uint8Array(n * n * 4);
    for (let row = 0; row < rows; row++) {
      let x = Math.floor(r() * 0.2 * n);
      const start = x, y0 = Math.round(row * rh), y1 = Math.round((row + 1) * rh);
      while (x < start + n) {
        let len = Math.round((0.09 + 0.29 * r() * r()) / px + 0.02 * n * r());
        if (start + n - x - len < 0.07 / px) len = start + n - x;
        const lift = r(), tu = (r() - 0.5) * 0.006, tv = (r() - 0.5) * 0.004;
        const grey = r() < 0.16, tone = grey ? 0.70 + 0.10 * r() : 0.86 + 0.12 * r(), warm = r();
        const cr = tone * (grey ? 0.96 : 0.99 + 0.02 * warm), cg = tone, cb = tone * (grey ? 1.04 : 1.0 - 0.035 * warm);
        for (let yy = y0; yy < y1; yy++) {
          const b = (yy - y0 + 0.5) / rh, ey = Math.min(yy - y0, y1 - 1 - yy);
          for (let k = 0; k < len; k++) {
            const xx = (x + k) % n, i = yy * n + xx, e = Math.min(ey, k, len - 1 - k);
            const a = (k + 0.5) / len, s = split[i];
            const edge = smooth(0, 2.5 * n / 1024 + 0.5, e);       // 0 in the joint -> 1 on the face
            hgt[i] = edge * (0.003 + lift * 0.009 + tu * (a - 0.5) + tv * (b - 0.5) + 0.0016 * s) - (1 - edge) * 0.003;
            const sh = (0.52 + 0.48 * edge) * (1 + 0.035 * s);
            const o = i * 4;
            d[o] = srgb8(cr * sh); d[o + 1] = srgb8(cg * sh); d[o + 2] = srgb8(cb * sh); d[o + 3] = 255;
          }
        }
        x += len;
      }
    }
    return { map: tex(ctx, d, n, n, STONE.W, STONE.W, true), normal: tex(ctx, normalData(hgt, n, n, px, px), n, n, STONE.W, STONE.W, false) };
  });
}

// Herringbone firebrick: 57 x 228 mm splits (ratio 4), 8 x 8 cells per tile; the material turns it 45 degrees.
function herringTex(ctx) {
  return shared(ctx, 'herring', () => {
    const n = q(ctx, 512), cells = 8, cs = n / cells, k = 4, W = cells * 0.057, r = prng(91);
    const tint = new Map();
    const grit = new Float32Array(n * n); addNoise(grit, n, n, 64, 64, 1, 92); addNoise(grit, n, n, 180, 180, 0.6, 93);
    const hgt = new Float32Array(n * n), d = new Uint8Array(n * n * 4), joint = 2.2 * n / 512;
    for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
      const i = Math.floor(x / cs), j = Math.floor(y / cs), s = (((i - j) % (2 * k)) + 2 * k) % (2 * k);
      let bx0, by0, bw, bh;                                         // the brick's box in cells
      if (s < k) { bx0 = i - s; by0 = j; bw = k; bh = 1; } else { bx0 = i; by0 = j - (2 * k - 1 - s); bw = 1; bh = k; }
      const key = (((bx0 % cells) + cells) % cells) + 16 * (((by0 % cells) + cells) % cells) + (s < k ? 0 : 512);
      if (!tint.has(key)) tint.set(key, [0.86 + 0.2 * r(), r(), r()]);
      const t = tint.get(key);
      const e = Math.min(x - bx0 * cs, (bx0 + bw) * cs - 1 - x, y - by0 * cs, (by0 + bh) * cs - 1 - y);
      const face = smooth(joint - 1, joint + 1, e), g = grit[y * n + x], o = (y * n + x) * 4;
      hgt[y * n + x] = face * (0.0015 + 0.0008 * t[1] + 0.0004 * g) - (1 - face) * 0.0015;
      const v = t[0] * (1 + 0.05 * g);
      // brick: buff with a little pink / grey from piece to piece; joint: pale fireclay mortar
      const br = [0.80 * v, (0.74 + 0.05 * t[2]) * v, (0.64 + 0.08 * t[2]) * v], mo = [0.74, 0.72, 0.68];
      d[o] = srgb8(mo[0] + (br[0] - mo[0]) * face); d[o + 1] = srgb8(mo[1] + (br[1] - mo[1]) * face);
      d[o + 2] = srgb8(mo[2] + (br[2] - mo[2]) * face); d[o + 3] = 255;
    }
    const a = tex(ctx, d, n, n, W, W, true), b = tex(ctx, normalData(hgt, n, n, W / n, W / n), n, n, W, W, false);
    for (const t of [a, b]) { t.rotation = Math.PI / 4; }
    return { map: a, normal: b };
  });
}

// Cast concrete / plaster / clay: a soft mottle (mean 0.92) with pinholes; tile 0.90 m.
function mottleTex(ctx) {
  return shared(ctx, 'mottle', () => {
    const n = q(ctx, 256), f = new Float32Array(n * n), p = new Float32Array(n * n);
    addNoise(f, n, n, 3, 3, 0.03, 61); addNoise(f, n, n, 9, 9, 0.025, 62); addNoise(f, n, n, 40, 40, 0.02, 63);
    addNoise(p, n, n, n >> 1, n >> 1, 1, 64);
    for (let i = 0; i < n * n; i++) f[i] = 0.92 * (1 + f[i]) * (p[i] > 0.86 ? 0.8 : 1);
    return greyTex(ctx, f, n, n, 0.9, 0.9);
  });
}
function lavaTex(ctx) {
  return shared(ctx, 'lava', () => {
    const n = q(ctx, 128), f = new Float32Array(n * n), hgt = new Float32Array(n * n);
    addNoise(f, n, n, 10, 10, 0.5, 65); addNoise(f, n, n, 22, 22, 0.35, 66); addNoise(f, n, n, 60, 60, 0.2, 67);
    for (let i = 0; i < n * n; i++) { hgt[i] = 0.006 * f[i]; f[i] = 0.5 + 0.5 * Math.max(-1, Math.min(1, f[i] * 1.2)); }
    return { map: greyTex(ctx, f, n, n, 0.2, 0.2), normal: tex(ctx, normalData(hgt, n, n, 0.2 / n, 0.2 / n), n, n, 0.2, 0.2, false) };
  });
}
function coirTex(ctx) {
  return shared(ctx, 'coir', () => {
    const n = q(ctx, 128), f = new Float32Array(n * n), hgt = new Float32Array(n * n);
    addNoise(f, n, n, n >> 1, n >> 1, 0.30, 68); addNoise(f, n, n, 24, 24, 0.12, 69); addNoise(f, n, n, 5, 5, 0.06, 70);
    for (let i = 0; i < n * n; i++) { hgt[i] = 0.002 * f[i]; f[i] = 0.8 * (1 + f[i]); }
    return { map: greyTex(ctx, f, n, n, 0.25, 0.25), normal: tex(ctx, normalData(hgt, n, n, 0.25 / n, 0.25 / n), n, n, 0.25, 0.25, false) };
  });
}

// The outdoor rug, one texture for the whole 2.40 x 1.70 m rug: a darker border, a field of pale diamond lines
// on a grey-beige flat weave (seg123_039).
function rugTex(ctx) {
  return shared(ctx, 'rug', () => {
    const w = q(ctx, 512), h = Math.round(w * 1.7 / 2.4), W = 2.4, H = 1.7, px = W / w;
    const yarn = new Float32Array(w * h);
    addNoise(yarn, w, h, w >> 1, h >> 2, 0.07, 81); addNoise(yarn, w, h, w >> 2, h >> 1, 0.07, 82); addNoise(yarn, w, h, 7, 5, 0.05, 83);
    const d = new Uint8Array(w * h * 4), pitch = 0.34, line = 0.012;
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const X = x * px, Y = y * px, e = Math.min(X, W - X, Y, H - Y);
      const a = ((X + Y) / pitch) % 1, b = (((X - Y) / pitch) % 1 + 1) % 1;
      const da = Math.min(a, 1 - a) * pitch, db = Math.min(b, 1 - b) * pitch;
      const onLine = 1 - smooth(line * 0.5, line * 0.5 + px * 1.2, Math.min(da, db) * 0.7071);
      let c = [0.300, 0.265, 0.245];                                   // the field
      if (e < 0.10) c = [0.150, 0.140, 0.140];                         // border
      else if (e < 0.125) c = [0.52, 0.48, 0.44];                      // pale inner line
      else c = [c[0] + (0.50 - c[0]) * onLine, c[1] + (0.46 - c[1]) * onLine, c[2] + (0.42 - c[2]) * onLine];
      const k = 1 + yarn[y * w + x], o = (y * w + x) * 4;
      d[o] = srgb8(c[0] * k); d[o + 1] = srgb8(c[1] * k); d[o + 2] = srgb8(c[2] * k); d[o + 3] = 255;
    }
    return tex(ctx, d, w, h, W, H, true, true);
  });
}

// One fan opening of the heat pump (UV 0..1 over the opening's square): dark depth, hub and three blades, and the
// guard: horizontal wires on two uprights, as in p26.
function fanTex(ctx) {
  return shared(ctx, 'fan', () => {
    const n = q(ctx, 256), d = new Uint8Array(n * n * 4);
    for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
      const u = (x + 0.5) / n - 0.5, v = (y + 0.5) / n - 0.5, r = Math.hypot(u, v) * 2, a = Math.atan2(v, u);
      let c = 0.035;
      const blade = Math.cos(3 * a + r * 2.2);
      if (r < 0.92 && blade > 0.25) c = 0.075 + 0.04 * blade;        // blades
      if (r < 0.2) c = 0.11;                                           // hub
      const row = (y + 0.5) / n * 24, wire = Math.abs(row - Math.round(row)) * n / 24;   // 24 wires down the opening
      if (wire < 0.9 * n / 256) c = 0.50;
      if (Math.abs(Math.abs(u) - 0.17) < 0.006) c = 0.50;             // two uprights
      if (r > 0.97) c = 0.45;                                          // the opening's rim
      const o = (y * n + x) * 4, s = srgb8(c);
      d[o] = s; d[o + 1] = s; d[o + 2] = srgb8(c * 0.97); d[o + 3] = 255;
    }
    const t = tex(ctx, d, n, n, 1, 1, true, true);
    return t;
  });
}

// ---------------------------------------------------------------------------------------------------- materials
function std(o) { return new THREE.MeshStandardMaterial(o); }

function powder(ctx, c, roughness) {
  const m = std({ color: col(c), roughness, metalness: 0.0, normalMap: gritNormal(ctx) });
  m.normalScale.set(1, 1);
  return m;
}
function wood(ctx, c, roughness, strong, bump = 1) {
  const g = grainTex(ctx);
  const m = std({ color: col(scl(c, 1 / GRAIN.mean)), roughness, map: strong ? g.strong : g.soft, normalMap: g.normal });
  m.normalScale.set(bump, bump);
  return m;
}
function fabric(ctx, c, edge) {
  const t = edge ? fabricEdgeTex(ctx) : fabricTex(ctx);
  const m = std({ color: col(scl(c, 1 / FAB.mean)), roughness: 1.0, metalness: 0, map: t.map, normalMap: t.normal });
  m.normalScale.set(edge ? 1 : 0.8, edge ? 1 : 0.8);
  m.envMapIntensity = 0.9;
  return m;
}
function mottled(ctx, c, roughness) {
  return std({ color: col(scl(c, 1 / 0.92)), roughness, map: mottleTex(ctx) });
}

// linear albedos (see the header)
const C = {
  dark: [0.130, 0.137, 0.146],
  black: [0.036, 0.040, 0.048],
  slat: [0.44, 0.43, 0.41],
  teak: [0.170, 0.092, 0.060],
  taupe: [0.36, 0.28, 0.23],
  lightwood: [0.55, 0.36, 0.20],
  pale: [0.715, 0.722, 0.740],
  slate: [0.37, 0.40, 0.41],
  charcoal: [0.125, 0.135, 0.15],
  white: [0.80, 0.80, 0.79],
  rope: [0.50, 0.46, 0.40],
  stone: [0.88, 0.875, 0.86],
  firebrick: [0.62, 0.50, 0.40],
  concrete: [0.80, 0.80, 0.79],
  plaster: [0.78, 0.77, 0.74],
  terracotta: [0.45, 0.20, 0.10],
  coir: [0.36, 0.23, 0.11],
  ceramic: [0.82, 0.82, 0.80],
  condenser: [0.72, 0.70, 0.64],
  utility: [0.25, 0.26, 0.27],
  bronze: [0.060, 0.048, 0.038],
};

export function register(lib) {
  lib.add('furniture_dark', (ctx) => powder(ctx, C.dark, 0.5));
  lib.add('furn_black', (ctx) => powder(ctx, C.black, 0.45));
  lib.add('furn_slat_grey', (ctx) => wood(ctx, C.slat, 0.62, false, 1.2));
  lib.add('furniture_wood', (ctx) => wood(ctx, C.teak, 0.5, true));
  lib.add('furn_wood_taupe', (ctx) => wood(ctx, C.taupe, 0.6, false));
  lib.add('furn_wood_light', (ctx) => wood(ctx, C.lightwood, 0.5, false, 0.6));

  for (const [name, c] of [['cushion', C.pale], ['furn_fabric_slate', C.slate], ['furn_fabric_charcoal', C.charcoal]]) {
    lib.add(name, (ctx) => fabric(ctx, c, false));
    lib.add(name + '_edge', (ctx) => fabric(ctx, c, true));
  }
  lib.add('furn_fabric_white', (ctx) => fabric(ctx, C.white, false));
  lib.add('furn_rope', (ctx) => {
    const t = ropeTex(ctx);
    const m = std({ color: col(C.rope), roughness: 1.0, map: t.map, normalMap: t.normal, side: THREE.DoubleSide });
    m.shadowSide = THREE.DoubleSide;
    return m;
  });

  lib.add('fireplace_stone', (ctx) => {
    const t = stoneTex(ctx);
    return std({ color: col(C.stone), roughness: 0.82, map: t.map, normalMap: t.normal });
  });
  lib.add('fireplace_firebrick', (ctx) => {
    const t = herringTex(ctx);
    return std({ color: col(C.firebrick), roughness: 0.92, map: t.map, normalMap: t.normal });
  });
  lib.add('fireplace_soot', { color: 0x1c1a18, roughness: 1.0 });
  lib.add('furn_bronze', (ctx) => std({ color: col(C.bronze), roughness: 0.42, metalness: 0.6, envMapIntensity: 1 / (ctx.envGain || 1) }));

  lib.add('firebowl_concrete', (ctx) => mottled(ctx, C.concrete, 0.7));
  lib.add('firebowl_media', (ctx) => {
    const t = lavaTex(ctx);
    return std({ color: col([0.10, 0.095, 0.09]), roughness: 0.95, map: t.map, normalMap: t.normal });
  });
  lib.add('furn_ceramic_white', (ctx) => std({ color: col(C.ceramic), roughness: 0.22, envMapIntensity: 1 / (ctx.envGain || 1) }));
  lib.add('furn_plaster_white', (ctx) => mottled(ctx, C.plaster, 0.92));
  lib.add('pot_terracotta', (ctx) => mottled(ctx, C.terracotta, 0.9));

  lib.add('rug_diamond', (ctx) => std({ color: 0xffffff, roughness: 1.0, map: rugTex(ctx) }));
  lib.add('doormat_coir', (ctx) => {
    const t = coirTex(ctx);
    return std({ color: col(scl(C.coir, 1 / 0.8)), roughness: 1.0, map: t.map, normalMap: t.normal });
  });

  lib.add('condenser_white', (ctx) => std({ color: col(C.condenser), roughness: 0.42, metalness: 0.0 }));
  lib.add('condenser_fan', (ctx) => std({ color: 0xffffff, roughness: 0.6, map: fanTex(ctx) }));
  lib.add('utility_grey', (ctx) => std({ color: col(C.utility), roughness: 0.55 }));
}
