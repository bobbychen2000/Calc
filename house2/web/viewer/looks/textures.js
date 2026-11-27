// Procedural texture helpers of the "surfaces" look family (./surfaces.js).
// Everything is generated at load from seeded noise: no image files, no network.
//
// Conventions
//   * A texture is a tile of W x H METRES (the kit's UVs are metres): repeat = (1 / W, 1 / H), RepeatWrapping.
//   * Row 0 of a texture is its TOP: rows run down the wall / down the slope (the GLB stores v flipped and the
//     textures use flipY = false), columns run along +u.  So a pattern is authored the way it is seen.
//   * Colour maps are sRGB bytes made from LINEAR albedo values (srgb8); "NR packs" hold the tangent-space
//     normal in RG (z is rebuilt in the shader), the roughness factor in B and 255 in A.
//   * surface() returns a MeshStandardMaterial whose shader also blends a shared DETAIL tile (crisp grain at
//     1.5 m, mip-mapped away at distance) and two octaves of a shared MACRO noise (no visible tiling at 30 m).
import * as THREE from 'three';

// ------------------------------------------------------------------------------------------------ numbers
export function prng(seed) {
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
/** linear 0..1 -> sRGB byte */
export const srgb8 = (v) => LUT[v <= 0 ? 0 : v >= 1 ? 4096 : (v * 4096 + 0.5) | 0];
/** sRGB bytes -> linear triple */
export const lin = (r, g, b) => [r, g, b].map((c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); });
export const smooth = (a, b, x) => { const t = x <= a ? 0 : x >= b ? 1 : (x - a) / (b - a); return t * t * (3 - 2 * t); };

// generation time of the family (ms), read by the tests: window.__surfaceTex
export const TIMES = { total: 0, items: {} };
if (typeof globalThis !== 'undefined') globalThis.__surfaceTex = TIMES;
export function timed(name, fn) {
  const t0 = performance.now();
  const r = fn();
  const dt = performance.now() - t0;
  TIMES.items[name] = Math.round(dt * 10) / 10;
  TIMES.total = Math.round((TIMES.total + dt) * 10) / 10;
  return r;
}

// ------------------------------------------------------------------------------------------------ noise
/** out += amp * tileable value noise on a cx x cy lattice (smoothstep interpolation), range -amp .. amp */
export function addNoise(out, w, h, cx, cy, amp, seed) {
  const r = prng(seed);
  const L = new Float32Array(cx * cy);
  for (let i = 0; i < L.length; i++) L[i] = r() * 2 - 1;
  const x0 = new Int32Array(w), x1 = new Int32Array(w), fx = new Float32Array(w);
  for (let x = 0; x < w; x++) {
    const u = (x * cx) / w, i = Math.floor(u), f = u - i;
    x0[x] = i % cx; x1[x] = (i + 1) % cx; fx[x] = f * f * (3 - 2 * f);
  }
  let o = 0;
  for (let y = 0; y < h; y++) {
    const v = (y * cy) / h, j = Math.floor(v);
    let g = v - j;
    g = g * g * (3 - 2 * g);
    const r0 = (j % cy) * cx, r1 = ((j + 1) % cy) * cx;
    for (let x = 0; x < w; x++) {
      const a = L[r0 + x0[x]], c = L[r1 + x0[x]], f = fx[x];
      const top = a + (L[r0 + x1[x]] - a) * f, bot = c + (L[r1 + x1[x]] - c) * f;
      out[o++] += amp * (top + (bot - top) * g);
    }
  }
  return out;
}

/** tileable fractal noise, zero mean, about -1 .. 1 (sd ~0.3) */
export function fbm(w, h, cx, cy, oct, seed, gain = 0.5) {
  const out = new Float32Array(w * h);
  let amp = 1, sum = 0;
  for (let o = 0; o < oct; o++) {
    if ((cx << o) > w || (cy << o) > h) break;
    addNoise(out, w, h, cx << o, cy << o, amp, seed + o * 1013);
    sum += amp; amp *= gain;
  }
  const k = 1.6 / sum;
  for (let i = 0; i < out.length; i++) out[i] *= k;
  return out;
}

// the shared noise bank: two fractal fields and white noise of S x S (S a power of two), sampled with wrap
const BANKS = new Map();
export function bank(S) {
  if (!BANKS.has(S)) {
    BANKS.set(S, timed('noise bank ' + S, () => {
      const r = prng(977);
      const Wn = new Float32Array(S * S);
      for (let i = 0; i < Wn.length; i++) Wn[i] = r() * 2 - 1;
      return { S, M: S - 1, A: fbm(S, S, 4, 4, 8, 11, 0.55), B: fbm(S, S, 24, 24, 5, 23, 0.6), W: Wn };
    }));
  }
  return BANKS.get(S);
}

// ------------------------------------------------------------------------------------------------ layouts
/** rows of pieces: each of `rows` rows is filled with pieces whose lengths (in units) come from `choices`,
 *  summing to `units`; the joints of a row are shifted by a random number of units.  Returns rects in units. */
export function coursed(rows, units, choices, rnd, rowH = 1) {
  const out = [];
  const lo = Math.min(...choices);
  for (let j = 0; j < rows; j++) {
    let x = 0;
    const shift = Math.floor(rnd() * units);
    let last = -1;
    while (x < units) {
      const rem = units - x;
      let ok = choices.filter((c) => c === rem || rem - c >= lo);
      const alt = ok.filter((c) => c !== last);
      if (alt.length && rnd() < 0.7) ok = alt;
      const c = ok.length ? ok[Math.floor(rnd() * ok.length)] : rem;
      out.push({ x0: x + shift, x1: x + c + shift, y0: j * rowH, y1: (j + 1) * rowH, row: j });
      x += c; last = c;
    }
  }
  return out;
}

/** rasterise rects (pixels, may run past the edges: wrapped) -> id per pixel and the distance (px) to the
 *  piece's border, with corners rounded by `round` px */
export function rasterRects(w, h, rects, round = 0) {
  const id = new Int32Array(w * h).fill(-1), edge = new Float32Array(w * h);
  for (let k = 0; k < rects.length; k++) {
    const q = rects[k];
    const ya = Math.ceil(q.y0 - 0.5), yb = Math.ceil(q.y1 - 0.5), xa = Math.ceil(q.x0 - 0.5), xb = Math.ceil(q.x1 - 0.5);
    for (let y = ya; y < yb; y++) {
      const dy = Math.min(y + 0.5 - q.y0, q.y1 - y - 0.5), row = (((y % h) + h) % h) * w;
      for (let x = xa; x < xb; x++) {
        const dx = Math.min(x + 0.5 - q.x0, q.x1 - x - 0.5);
        let d = dx < dy ? dx : dy;
        if (dx < round && dy < round) d = round - Math.hypot(round - dx, round - dy);
        const i = row + (((x % w) + w) % w);
        id[i] = k; edge[i] = d;
      }
    }
  }
  return { id, edge };
}

// ------------------------------------------------------------------------------------------------ packing
/** height field (metres) of a W x H m tile -> RGBA bytes: normal xy, roughness (array or number), 255.
 *  three's derivative tangent frame shortens the shorter axis of a non-square tile; the slopes are
 *  pre-scaled so the shaded normal is the metric one. */
export function packNR(hgt, w, h, W, H, rough = 1, gain = 1) {
  const out = new Uint8Array(w * h * 4);
  const M = Math.max(W, H);
  const kx = (w / W) * 0.5 * (M / W) * gain, ky = (h / H) * 0.5 * (M / H) * gain;
  const ra = typeof rough === 'number' ? null : rough, rc = ra ? 0 : Math.round(rough * 255);
  for (let y = 0; y < h; y++) {
    const ym = ((y + h - 1) % h) * w, yp = ((y + 1) % h) * w, yo = y * w;
    for (let x = 0; x < w; x++) {
      const xm = (x + w - 1) % w, xp = (x + 1) % w;
      const sx = (hgt[yo + xp] - hgt[yo + xm]) * kx, sy = (hgt[yp + x] - hgt[ym + x]) * ky;
      const inv = 127.5 / Math.sqrt(sx * sx + sy * sy + 1), o = (yo + x) * 4;
      out[o] = 127.5 - sx * inv; out[o + 1] = 127.5 - sy * inv;
      out[o + 2] = ra ? Math.max(0, Math.min(255, ra[yo + x] * 255)) : rc;
      out[o + 3] = 255;
    }
  }
  return out;
}

export function texture(ctx, data, w, h, W, H, srgb = false) {
  const t = new THREE.DataTexture(data, w, h, THREE.RGBAFormat, THREE.UnsignedByteType);
  finish(ctx, t, W, H, srgb);
  return t;
}
export function canvasTexture(ctx, canvas, W, H, srgb = true) {
  const t = new THREE.CanvasTexture(canvas);
  t.flipY = false;
  finish(ctx, t, W, H, srgb);
  return t;
}
function finish(ctx, t, W, H, srgb) {
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(1 / W, 1 / H);
  t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
  t.generateMipmaps = true;
  t.minFilter = THREE.LinearMipmapLinearFilter;
  t.magFilter = THREE.LinearFilter;
  t.anisotropy = Math.min(ctx.anisotropy || 1, 8);
  t.needsUpdate = true;
}

/** a canvas whose 2-D context draws every stroke nine times so the picture tiles */
export function tileCanvas(w, h) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  const g = c.getContext('2d', { willReadFrequently: true });
  return { c, g, w, h };
}

// ------------------------------------------------------------------------------------------------ shared tiles
const SHARED = new Map();
export function shared(key, make) {
  if (!SHARED.has(key)) SHARED.set(key, make());
  return SHARED.get(key);
}

/** the macro noise: 3 decorrelated fractal channels, sampled at two large scales by every surface */
export function macroNoise(ctx) {
  return shared('macro', () => timed('macro noise', () => {
    const n = 256, d = new Uint8Array(n * n * 4);
    const f = [fbm(n, n, 3, 3, 6, 301, 0.55), fbm(n, n, 3, 3, 6, 302, 0.55), fbm(n, n, 4, 4, 6, 303, 0.55)];
    for (let i = 0; i < n * n; i++) {
      for (let c = 0; c < 3; c++) d[i * 4 + c] = Math.max(0, Math.min(255, 127.5 + f[c][i] * 190));
      d[i * 4 + 3] = 255;
    }
    return texture(ctx, d, n, n, 1, 1);
  }));
}

/** detail tiles: RG normal, B albedo factor, A roughness offset (all neutral at 0.5).  kind: grit | fibre | blades */
export function detailTile(ctx, kind) {
  const n = ctx.quality === 'low' ? 256 : 512;
  return shared('detail:' + kind, () => timed('detail ' + kind, () => {
    const hgt = new Float32Array(n * n), alb = new Float32Array(n * n);
    const r = prng(kind.length * 7919 + 5);
    if (kind === 'grit') {                       // grains of 1 - 4 mm on a 0.37 m tile
      addNoise(hgt, n, n, n / 2, n / 2, 1.0, 51); addNoise(hgt, n, n, n / 4, n / 4, 0.8, 52);
      addNoise(hgt, n, n, n / 8, n / 8, 0.5, 53); addNoise(hgt, n, n, n / 32, n / 32, 0.35, 54);
      addNoise(alb, n, n, n / 2, n / 2, 0.7, 61); addNoise(alb, n, n, n / 6 | 0, n / 6 | 0, 0.6, 62);
      addNoise(alb, n, n, n / 20 | 0, n / 20 | 0, 0.5, 63);
      for (let i = 0; i < n * n; i++) alb[i] = alb[i] * 0.6 + hgt[i] * 0.25;
    } else if (kind === 'fibre') {               // fibres along v on a 0.33 m tile
      addNoise(hgt, n, n, n / 2, 6, 1.0, 71); addNoise(hgt, n, n, n / 4, 3, 0.8, 72); addNoise(hgt, n, n, n / 8, 12, 0.5, 73);
      addNoise(alb, n, n, n / 2, 8, 0.8, 74); addNoise(alb, n, n, n / 6 | 0, 3, 0.8, 75);
      for (let i = 0; i < n * n; i++) alb[i] = alb[i] * 0.55 + hgt[i] * 0.2;
    } else {                                     // blades: thin strokes, mostly along v, on a 0.45 m tile
      const { g } = tileCanvas(n, n);
      g.fillStyle = '#000'; g.fillRect(0, 0, n, n);
      g.lineCap = 'round';
      const N = n * 9;
      for (let i = 0; i < N; i++) {
        const x = r() * n, y = r() * n, a = (r() - 0.5) * 1.9 + (r() < 0.2 ? Math.PI / 2 : 0), l = n * (0.05 + r() * 0.1);
        const dx = Math.sin(a) * l, dy = -Math.cos(a) * l, bend = (r() - 0.5) * l * 0.6;
        const v = Math.round(60 + (i / N) * 150 + r() * 45);
        g.strokeStyle = `rgb(${v},${v},${v})`;
        g.lineWidth = n / 512 * (0.8 + r() * 1.0);
        for (let oy = -n; oy <= n; oy += n) {
          if (y + oy < -l || y + oy > n + l) continue;
          for (let ox = -n; ox <= n; ox += n) {
            if (x + ox < -l || x + ox > n + l) continue;
            g.beginPath(); g.moveTo(x + ox, y + oy);
            g.quadraticCurveTo(x + ox + dx * 0.5 + bend, y + oy + dy * 0.5, x + ox + dx, y + oy + dy); g.stroke();
          }
        }
      }
      const px = g.getImageData(0, 0, n, n).data;
      for (let i = 0; i < n * n; i++) { hgt[i] = px[i * 4] / 255 * 2 - 1; alb[i] = hgt[i] * 0.85; }
    }
    const d = new Uint8Array(n * n * 4);
    const k = kind === 'blades' ? 1.6 : 0.9;
    for (let y = 0; y < n; y++) {
      const ym = ((y + n - 1) % n) * n, yp = ((y + 1) % n) * n, yo = y * n;
      for (let x = 0; x < n; x++) {
        const sx = (hgt[yo + (x + 1) % n] - hgt[yo + (x + n - 1) % n]) * k, sy = (hgt[yp + x] - hgt[ym + x]) * k;
        const inv = 127.5 / Math.sqrt(sx * sx + sy * sy + 1), o = (yo + x) * 4;
        d[o] = 127.5 - sx * inv; d[o + 1] = 127.5 - sy * inv;
        d[o + 2] = Math.max(0, Math.min(255, 127.5 + alb[yo + x] * 127.5));
        d[o + 3] = Math.max(0, Math.min(255, 127.5 - hgt[yo + x] * 90));
      }
    }
    return texture(ctx, d, n, n, 1, 1);
  }));
}

/** a 4 x 4 flat NR pack for surfaces without relief */
export function flatNR(ctx) {
  return shared('flatNR', () => {
    const d = new Uint8Array(64);
    for (let i = 0; i < 16; i++) d.set([128, 128, 255, 255], i * 4);
    return texture(ctx, d, 4, 4, 1, 1);
  });
}

// ------------------------------------------------------------------------------------------------ material
const FRAG_PARS = `
varying vec2 vSurfUv;
#ifdef SURF_MACRO
uniform sampler2D surfNoise;
uniform vec4 surfMacro;      // scale 1, scale 2 (1 / m), brightness amount, tint amount
uniform vec3 surfTint;
#endif
#ifdef SURF_DETAIL
uniform sampler2D surfDetail;
uniform vec4 surfDetailP;    // uv scale (1 / m) x, y; albedo amount; normal amount
uniform float surfDetailRough;
#endif
`;
const FRAG_ALBEDO = `
#ifdef SURF_MACRO
{
  vec3 sn1 = texture2D( surfNoise, vSurfUv * surfMacro.x ).rgb;
  vec3 sn2 = texture2D( surfNoise, vSurfUv.yx * surfMacro.y + vec2( 0.37, 0.11 ) ).rgb;
  diffuseColor.rgb *= 1.0 + surfMacro.z * ( sn1.r + sn2.g - 1.0 );
  float st = clamp( ( sn1.b + sn2.r - 1.0 ) * 1.5 + 0.5, 0.0, 1.0 );
  diffuseColor.rgb *= mix( vec3( 1.0 ), surfTint, surfMacro.w * st );
}
#endif
#ifdef SURF_DETAIL
vec4 surfDt = texture2D( surfDetail, vSurfUv * surfDetailP.xy );
diffuseColor.rgb *= 1.0 + surfDetailP.z * ( surfDt.b * 2.0 - 1.0 );
#endif
`;
const FRAG_ROUGH = `
float roughnessFactor = roughness;
#ifdef USE_NORMALMAP
vec4 surfNR = texture2D( normalMap, vNormalMapUv );
roughnessFactor *= surfNR.b;
#endif
#ifdef SURF_DETAIL
roughnessFactor = clamp( roughnessFactor + surfDetailRough * ( surfDt.a * 2.0 - 1.0 ), 0.05, 1.0 );
#endif
`;
const FRAG_NORMAL = `
#ifdef USE_NORMALMAP_TANGENTSPACE
  vec3 mapN = vec3( ( surfNR.rg * 2.0 - 1.0 ) * normalScale, 0.0 );
  #ifdef SURF_DETAIL
    mapN.xy += ( surfDt.rg * 2.0 - 1.0 ) * surfDetailP.w;
  #endif
  mapN.z = sqrt( max( 1.0 - dot( mapN.xy, mapN.xy ), 0.04 ) );
  normal = normalize( tbn * mapN );
#endif
`;

/** MeshStandardMaterial of a surface.
 *  o = { color: [r, g, b] linear | hex, roughness, metalness, map, nr (NR pack), normalScale,
 *        detail: { kind, size (m), albedo, normal, rough }, macro: { s1, s2 (m), amount, tint: [r, g, b], tintAmount },
 *        envMapIntensity } */
export function surface(ctx, o) {
  const m = new THREE.MeshStandardMaterial({ roughness: o.roughness ?? 1, metalness: o.metalness ?? 0 });
  if (Array.isArray(o.color)) m.color.setRGB(o.color[0], o.color[1], o.color[2], THREE.LinearSRGBColorSpace);
  else if (o.color !== undefined) m.color.set(o.color);
  if (o.map) m.map = o.map;
  m.normalMap = o.nr || flatNR(ctx);
  const ns = o.normalScale ?? 1;
  m.normalScale.set(ns, ns);
  if (o.envMapIntensity !== undefined) m.envMapIntensity = o.envMapIntensity;
  const U = {};
  m.defines = { ...(m.defines || {}) };
  if (o.macro && o.macro.amount !== 0) {
    m.defines.SURF_MACRO = '';
    U.surfNoise = { value: macroNoise(ctx) };
    U.surfMacro = { value: new THREE.Vector4(1 / (o.macro.s1 || 9.7), 1 / (o.macro.s2 || 31), o.macro.amount ?? 0.1, o.macro.tintAmount ?? 0) };
    U.surfTint = { value: new THREE.Vector3(...(o.macro.tint || [1, 1, 1])) };
  }
  if (o.detail) {
    m.defines.SURF_DETAIL = '';
    const s = o.detail.size || 0.37;
    U.surfDetail = { value: detailTile(ctx, o.detail.kind || 'grit') };
    U.surfDetailP = { value: new THREE.Vector4(1 / s, 1 / (o.detail.sizeV || s), o.detail.albedo ?? 0.1, o.detail.normal ?? 0.2) };
    U.surfDetailRough = { value: o.detail.rough ?? 0 };
  }
  m.userData.surf = U;
  m.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, U);
    sh.vertexShader = sh.vertexShader
      .replace('#include <uv_pars_vertex>', '#include <uv_pars_vertex>\nvarying vec2 vSurfUv;')
      .replace('#include <uv_vertex>', '#include <uv_vertex>\nvSurfUv = uv;');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <map_pars_fragment>', '#include <map_pars_fragment>\n' + FRAG_PARS)
      .replace('#include <map_fragment>', '#include <map_fragment>\n' + FRAG_ALBEDO)
      .replace('#include <roughnessmap_fragment>', FRAG_ROUGH)
      .replace('#include <normal_fragment_maps>', FRAG_NORMAL);
  };
  m.customProgramCacheKey = () => 'surfaces-1';
  return m;
}
