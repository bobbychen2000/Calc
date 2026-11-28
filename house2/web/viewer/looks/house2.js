// Look module "house2": the materials the second house's zones added (model/zones/*.py MATERIALS), and the names of
// the shared library whose finish differs on this property (the flagstone under the name 'bluestone', the grey stone
// coping, the darker roof).  Registered LAST in ../materials.js, so an entry here overrides the earlier modules.
//
// Colours are LINEAR albedos measured on the listing photographs through the registered cameras (p21, p28, p29, the
// hero) against the viewer's light: a sunlit surface shows ~1.05 x its albedo, one in open shade ~0.52 x.
//
// PATTERN MODULES (metres, the kit's UVs):
//   siding_shingle   cedar shingles, 0.140 exposure (butts at v = k * 0.140), shingles 0.09 - 0.22 wide; tile 1.6 x 1.12
//   bluestone        full-range flagstone, random ashlar on a 0.305 grid (pieces up to 1.22 x 0.915), 12 mm joints; tile 3.66
//   fieldstone       dry-stacked ledge stone, courses 0.10 - 0.20; tile 2.4 x 1.2
//   yard_fieldstone  the fireplace's ashlar veneer, pieces 0.10 - 0.40; tile 1.6
//   solar            156 mm cells; spa_mosaic 25 mm glass tiles; vent_louvre blades every 45 mm
// PHOTO SWATCHES (../materials.js applySwatch): the patches are ~1 cm a pixel -- right from the drone, a blur at eye
// level.  Looks that draw their own pieces pass `swatchFade: [from, to]` (metres from the eye): the drawn stones /
// shingles / chips up close, the photo patch beyond.  `worldUV` lays flagstone in plan (square to the pool) whatever
// the terrain mesh's UVs are, and keeps the mesh's facets out of its shading.  stone_veneer keeps its own look only.
// PLANTING: the zone's crowns are flat-shaded lumpy blobs without usable UVs.  `foliage` shades them in WORLD space
// (three-plane projection): a field of clumps bends the normal and opens dark hollows, a tile of leaves gives the
// grain, and the faces that turn away from the eye are eaten into by the leaf pattern (the blob is drawn two-sided,
// so a hole shows the dark inside of the crown) -- a ragged, leafy outline instead of a polygon's.  Bark is projected
// the same way from the sides.
import * as THREE from 'three';
import {
  prng, srgb8, smooth, timed, addNoise, fbm, coursed, rasterRects, packNR, texture, canvasTexture, tileCanvas, shared,
  surface, flatNR, macroNoise,
} from './textures.js';
import { C as SC, q, bk, put, pick, paint, grooveTex, shingleTex, groundTex, strokes, canvasNR, css, lawnTex, mulchTex, PAVER, coursedTex } from './surfaces.js';

// ------------------------------------------------------------------------------------------------ colours
const C = {
  shingleSiding: [0.21, 0.216, 0.216],     // grey cedar shingle (p21 shade 81 90 101, hero 97 110 127 against the trim)
  trim: [0.74, 0.715, 0.62],               // cream-white casings, fascia, columns, railings
  gutter: [0.72, 0.695, 0.60],
  bronze: [0.022, 0.021, 0.022],           // window frames: near black
  espresso: [0.017, 0.012, 0.010],
  louvre: [0.20, 0.185, 0.16],
  roof: [0.28, 0.30, 0.345],             // charcoal-grey composition shingle (p28 118 119 126, the aerial)
  ridge: [0.32, 0.34, 0.385],
  flag: [1.0, 0.965, 0.91],
  coping: [0.60, 0.61, 0.60],              // thermal bluestone coping, light grey (p22 216 218 218)
  wallCap: [0.46, 0.47, 0.47],
  stoneCap: [0.36, 0.38, 0.40],
  chips: [1.25, 1.2, 1.1],
  turf: [1.35, 1.12, 1.8],
  gravel: [0.40, 0.40, 0.39],
  crushed: [0.36, 0.37, 0.37],
  orchard: [0.27, 0.225, 0.14],
  litter: [0.15, 0.115, 0.075],
  timber: [0.34, 0.24, 0.13],
  edging: [0.055, 0.047, 0.04],
  timberDark: [0.050, 0.036, 0.027],       // the arbor's dark stain
  woodGrey: [0.15, 0.125, 0.105],            // weathered cedar of the play structure
  teakGrey: [0.21, 0.21, 0.21],           // silvered teak (p24 78 80 88 in the shade)
  picket: [0.23, 0.20, 0.165],
  slide: [0.030, 0.19, 0.095],
  umbrella: [0.10, 0.10, 0.105],
  cushion: [0.17, 0.17, 0.175],
  rope: [0.52, 0.48, 0.38],
};

// ------------------------------------------------------------------------------------------------ helpers
const metals = [];
const envK = (ctx) => 1 / (ctx.envGain || 1);
function metal(ctx, color, roughness, metalness) {
  const m = new THREE.MeshStandardMaterial({ roughness, metalness });
  m.color.setRGB(color[0], color[1], color[2], THREE.LinearSRGBColorSpace);
  m.envMapIntensity = envK(ctx);
  metals.push(m);
  return m;
}
const timberLook = (ctx, color, roughness = 0.85, amount = 0.3) => surface(ctx, { color, roughness,
  detail: { kind: 'fibre', size: 0.17, albedo: amount, normal: 0.4 }, macro: { s1: 1.9, s2: 7.3, amount: 0.16 } });

// ------------------------------------------------------------------------------------------------ cedar shingle siding
function cedarTex(ctx) {
  return shared('h2cedar', () => timed('siding_shingle', () => {
    const w = q(ctx, 1024), h = q(ctx, 512), n = 8, ch = h / n, W = 1.6, H = n * 0.14, pxu = w / W;
    const { A, B, S, M } = bk(ctx);
    const rnd = prng(2008);
    const side = new Float32Array(n * w), tone = new Float32Array(n * w), warm = new Float32Array(n * w), lift = new Float32Array(n * w);
    for (let c = 0; c < n; c++) {
      const x0 = (rnd() * w) | 0;
      let filled = 0;
      while (filled < w) {
        let len = Math.round((0.075 + rnd() * 0.075) * pxu);
        if (w - filled - len < 0.06 * pxu) len = w - filled;
        const t = 0.955 + rnd() * 0.09, wm = (rnd() - 0.5) * 0.03, lf = rnd();
        for (let i = 0; i < len; i++) {
          const o = c * w + ((x0 + filled + i) % w);
          side[o] = Math.min(i + 0.5, len - i - 0.5); tone[o] = t; warm[o] = wm; lift[o] = lf;
        }
        filled += len;
      }
    }
    const alb = new Uint8Array(w * h * 4), hgt = new Float32Array(w * h), rgh = new Float32Array(w * h);
    for (let c = 0; c < n; c++) {
      for (let r = 0; r < ch; r++) {            // r runs DOWN the wall: 0 under the butt of the course above
        const y = c * ch + r, fr = r / ch, butt = r >= ch - 1 ? 0.2 : 1;
        const ao = 1 - 0.2 * Math.exp(-r / (ch * 0.04)) - 0.04 * Math.exp(-r / (ch * 0.25));
        for (let x = 0; x < w; x++) {
          const i = y * w + x, o = c * w + x, s = side[o];
          const gap = smooth(0.2, 1.5, s);                                                     // the keyway between two shingles
          const grain = A[((y >> 2) & M) * S + ((x * 4 + c * 97) & M)], fine = B[(y & M) * S + ((x * 3) & M)];
          const v = tone[o] * ao * (0.78 + 0.22 * gap) * (1 + 0.05 * grain + 0.04 * fine) * (r >= ch - 1 ? 0.93 : 1);
          put(alb, i * 4, v * (1 + warm[o]), v, v * (1 - warm[o]));
          hgt[i] = (0.005 * fr + 0.001 * lift[o] * fr) * butt * (0.5 + 0.5 * gap) + 0.0003 * grain;
          rgh[i] = 0.94 + 0.06 * fine;
        }
      }
    }
    return { map: texture(ctx, alb, w, h, W, H, true), nr: texture(ctx, packNR(hgt, w, h, W, H, rgh), w, h, W, H) };
  }));
}

// ------------------------------------------------------------------------------------------------ stone in pieces
// random ashlar: the tile (units x units) cut by guillotine splits into pieces of at most maxW x maxH units
function ashlar(units, rnd, maxW, maxH, stop = 0.55) {
  const out = [];
  const split = (x0, y0, x1, y1) => {
    const w = x1 - x0, h = y1 - y0;
    const big = w > maxW || h > maxH;
    if (!big && (w * h <= 2 || rnd() < stop)) { out.push({ x0, y0, x1, y1 }); return; }
    const vert = w > maxW ? true : h > maxH ? false : w > h ? rnd() < 0.75 : w < h ? rnd() < 0.25 : rnd() < 0.5;
    if (vert && w >= 2) { const c = 1 + Math.floor(rnd() * (w - 1)); split(x0, y0, x0 + c, y1); split(x0 + c, y0, x1, y1); }
    else if (!vert && h >= 2) { const c = 1 + Math.floor(rnd() * (h - 1)); split(x0, y0, x1, y0 + c); split(x0, y0 + c, x1, y1); }
    else out.push({ x0, y0, x1, y1 });
  };
  split(0, 0, units, units);
  return out;
}

// pieces with joints (flagstone, veneer, dry-stacked walls): o.layout(rnd) gives the rects in units of a
// o.units x o.unitsV tile of o.tile x o.tileV metres
function piecesTex(ctx, key, o) {
  return shared(key, () => timed(key, () => {
    const w = q(ctx, o.size || 1024), W = o.tile, H = o.tileV || o.tile, h = Math.round(w * H / W), upx = w / o.units, rnd = prng(o.seed);
    const { A, B, W: Wn, S, M } = bk(ctx);
    const rects = o.layout(rnd).map((r) => {
      const c = pick(o.palette, rnd()), c2 = pick(o.palette, rnd()), l = 1 + (rnd() - 0.5) * o.toneVar;
      return { x0: r.x0 * upx, x1: r.x1 * upx, y0: r.y0 * upx, y1: r.y1 * upx, col: [c[0] * l, c[1] * l, c[2] * l], col2: [c2[0] * l, c2[1] * l, c2[2] * l],
        ox: (rnd() * S) | 0, oy: (rnd() * S) | 0, off: rnd() - 0.5, tx: (rnd() - 0.5), ty: (rnd() - 0.5) };
    });
    const { id, edge } = rasterRects(w, h, rects, o.round || 0);
    const alb = new Uint8Array(w * h * 4), hgt = new Float32Array(w * h), rgh = new Float32Array(w * h);
    const jw = o.joint * w / W * 0.5, J = o.jointColor, bev = o.bevel * w / W, vein = o.vein || 0, tilt = (o.tilt || 0) / upx;
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const i = y * w + x, s = rects[id[i]] || rects[0];
        const a = A[((y + s.oy) & M) * S + ((x + s.ox) & M)], b = B[((y + s.oy) & M) * S + ((x + s.ox) & M)], wn = Wn[(i * 7) & (S * S - 1)];
        const e = edge[i] + (o.chip || 0) * b;
        const m = smooth(jw - 0.7, jw + 0.7, e), bv = bev > 0 ? smooth(jw, jw + bev, e) : 1;
        const l = (1 + o.cloud * a + o.grain * b + o.speck * wn) * (0.88 + 0.12 * bv);
        const k = vein ? smooth(-0.1, 0.4, A[((y * 2 + s.ox) & M) * S + ((x * 2 + s.oy) & M)]) * vein : 0;      // a second tone bleeding through the piece
        const c = s.col, d = s.col2;
        const cr = (c[0] + (d[0] - c[0]) * k) * l, cg = (c[1] + (d[1] - c[1]) * k) * l, cb = (c[2] + (d[2] - c[2]) * k) * l;
        put(alb, i * 4, J[0] + (cr - J[0]) * m, J[1] + (cg - J[1]) * m, J[2] + (cb - J[2]) * m);
        const cx = x - (s.x0 + s.x1) * 0.5, cy = y - (s.y0 + s.y1) * 0.5;
        hgt[i] = m * (o.cleft * a + o.cleft * 0.4 * b + o.lip * s.off + tilt * (cx * s.tx + cy * s.ty)) - (1 - bv) * o.bevelDepth - (1 - m) * o.jointDepth;
        rgh[i] = o.rough + (1 - m) * (0.97 - o.rough) + 0.05 * b;
      }
    }
    return { map: texture(ctx, alb, w, h, W, H, true), nr: texture(ctx, packNR(hgt, w, h, W, H, rgh), w, h, W, H) };
  }));
}

// full-range flagstone: light grey, blue-grey, buff, tan-rust, lilac (p21, p22: mean sunlit 199 193 186)
const FLAG = {
  seed: 12366, tile: 3.66, units: 12, layout: (rnd) => ashlar(12, rnd, 3, 3, 0.45), joint: 0.014, jointColor: [0.27, 0.25, 0.22], jointDepth: 0.004,
  bevel: 0.006, bevelDepth: 0.0008, round: 1.5, cleft: 0.0016, lip: 0.0015, cloud: 0.16, grain: 0.09, speck: 0.04, rough: 0.82, toneVar: 0.14, vein: 0.55,
  palette: [[[0.55, 0.555, 0.55], 0.32], [[0.46, 0.50, 0.535], 0.24], [[0.58, 0.53, 0.45], 0.14], [[0.53, 0.43, 0.33], 0.05], [[0.50, 0.49, 0.50], 0.14], [[0.62, 0.60, 0.55], 0.11]],
};
// the fireplace and seat wall: tan / rust / grey / cream ashlar veneer (p24)
const FIRE = {
  seed: 77, size: 512, tile: 1.6, units: 16, layout: (rnd) => ashlar(16, rnd, 4, 3, 0.5), joint: 0.008, jointColor: [0.05, 0.045, 0.04], jointDepth: 0.012,
  bevel: 0.012, bevelDepth: 0.004, round: 2, chip: 1.0, cleft: 0.006, lip: 0.012, tilt: 0.004, cloud: 0.14, grain: 0.1, speck: 0.04, rough: 0.9, toneVar: 0.16, vein: 0.5,
  palette: [[[0.40, 0.33, 0.25], 0.30], [[0.33, 0.24, 0.17], 0.14], [[0.33, 0.32, 0.31], 0.22], [[0.47, 0.41, 0.32], 0.14], [[0.24, 0.20, 0.17], 0.10], [[0.38, 0.36, 0.33], 0.10]],
};
// retaining walls: dry-stacked grey-brown ledge stone in thin courses (p18, p22, p24)
const LEDGE = {
  seed: 404, tile: 2.4, tileV: 1.2, units: 48, layout: (rnd) => {      // units of 5 cm: courses 5 - 10 cm, stones 15 - 55 cm
    const rows = [2, 1, 2, 2, 1, 2, 1, 2, 2, 1, 2, 2, 1, 1, 2], out = [];
    let y = 0;
    for (const hh of rows) {
      let x = Math.floor(rnd() * 6);
      const end = x + 48;
      while (x < end) { let len = 3 + Math.floor(rnd() * 9); if (end - x - len < 3) len = end - x; out.push({ x0: x, x1: x + len, y0: y, y1: y + hh }); x += len; }
      y += hh;
    }
    return out;
  }, joint: 0.005, jointColor: [0.02, 0.018, 0.016], jointDepth: 0.02,
  bevel: 0.01, bevelDepth: 0.005, round: 1.5, chip: 1.0, cleft: 0.006, lip: 0.012, tilt: 0.003, cloud: 0.12, grain: 0.1, speck: 0.04, rough: 0.92, toneVar: 0.16, vein: 0.35,
  palette: [[[0.185, 0.165, 0.145], 0.36], [[0.215, 0.18, 0.145], 0.22], [[0.155, 0.155, 0.16], 0.20], [[0.25, 0.22, 0.185], 0.12], [[0.12, 0.105, 0.095], 0.10]],
};
const FIREBRICK = {
  seed: 5, size: 256, tile: 0.92, units: 16, rows: 12, choices: [4], joint: 0.009, jointColor: [0.20, 0.18, 0.16], jointDepth: 0.003,
  bevel: 0.003, bevelDepth: 0.001, round: 0, cleft: 0.0008, lip: 0.001, cloud: 0.12, grain: 0.1, speck: 0.06, blush: 0, rough: 0.92, toneVar: 0.2,
  palette: [[[0.50, 0.33, 0.22], 0.5], [[0.44, 0.30, 0.22], 0.3], [[0.56, 0.40, 0.28], 0.2]],
};

// ------------------------------------------------------------------------------------------------ loose grounds
// chips / litter / gravel: short strokes or flecks from a palette (linear), the later ones on top and lighter
function flecksTex(ctx, key, o) {
  return shared(key, () => timed(key, () => {
    const n = q(ctx, o.size || 512), W = o.tile;
    const { c, g } = tileCanvas(n, n);
    g.fillStyle = css(...o.ground); g.fillRect(0, 0, n, n);
    const rnd = prng(o.seed);
    g.lineCap = o.round ? 'round' : 'butt';
    const N = Math.round(n * o.density);
    strokes(g, n, N, rnd, (i) => {
      const a = rnd() * 6.283, l = n * (o.len[0] + rnd() * (o.len[1] - o.len[0])), top = i / N, v = (0.5 + 0.62 * top) * (0.8 + rnd() * 0.4);
      const col = pick(o.palette, rnd());
      g.strokeStyle = css(col[0] * v, col[1] * v, col[2] * v);
      g.lineWidth = n / 512 * (o.width[0] + rnd() * (o.width[1] - o.width[0]));
      return { l, dx: Math.sin(a) * l, dy: Math.cos(a) * l, bend: 0 };
    });
    return { map: canvasTexture(ctx, c, W, W), nr: canvasNR(ctx, g, n, W, o.relief, 1) };
  }));
}
const CHIPS = {      // playground fibre: golden straw / tan (p28 239 191 132, p29, p19)
  seed: 19, tile: 1.2, density: 16, ground: [0.42, 0.25, 0.10], len: [0.012, 0.04], width: [1.2, 3.0], relief: 0.04,
  palette: [[[0.74, 0.47, 0.19], 0.5], [[0.64, 0.38, 0.15], 0.25], [[0.84, 0.58, 0.27], 0.17], [[0.48, 0.28, 0.11], 0.08]],
};
const LITTER = {
  seed: 23, tile: 1.4, density: 6, ground: [0.085, 0.062, 0.04], len: [0.012, 0.04], width: [2.5, 6], relief: 0.035, round: true,
  palette: [[[0.24, 0.17, 0.09], 0.4], [[0.16, 0.11, 0.065], 0.3], [[0.34, 0.25, 0.12], 0.18], [[0.12, 0.13, 0.05], 0.12]],
};
const GRAVEL = {     // pea gravel / crushed stone: round grey-tan grains 10 - 20 mm
  seed: 29, tile: 0.8, density: 9, ground: [0.17, 0.155, 0.135], len: [0.003, 0.008], width: [8, 15], relief: 0.035, round: true,
  palette: [[[0.44, 0.41, 0.36], 0.4], [[0.37, 0.36, 0.34], 0.3], [[0.52, 0.47, 0.40], 0.2], [[0.29, 0.27, 0.25], 0.1]],
};

// synthetic turf: short, even, fine blades; no dry patches (p18: 120 150 40 sunlit, p28 109 114 57)
function turfTex(ctx) {
  return shared('h2turf', () => timed('turf_synthetic', () => {
    const n = q(ctx, 512), W = 1.1;
    const { A, B, S, M } = bk(ctx);
    const F = new Float32Array(n * n);
    addNoise(F, n, n, n / 2, n / 8, 1.0, 191); addNoise(F, n, n, n / 8, n / 2, 0.8, 192); addNoise(F, n, n, n / 4, n / 4, 0.4, 193);
    const alb = new Uint8Array(n * n * 4), hgt = new Float32Array(n * n), k = S / n;
    for (let y = 0; y < n; y++) {
      for (let x = 0; x < n; x++) {
        const i = y * n + x, a = A[((y * k) & M) * S + ((x * k) & M)], b = B[((y * k) & M) * S + ((x * k) & M)];
        const t = smooth(-0.9, 1.0, F[i] + 0.25 * b), tone = 1 + 0.05 * a;
        const thatch = F[((y + 211) & (n - 1)) * n + ((x + 57) & (n - 1))] > 1.25 ? 0.35 : 0;      // tan thatch fibres
        let r = (0.075 + 0.135 * t) * tone, g = (0.125 + 0.20 * t) * tone, bl = (0.022 + 0.04 * t) * tone;
        r += (0.30 * t - r) * thatch; g += (0.27 * t - g) * thatch; bl += (0.10 * t - bl) * thatch;
        put(alb, i * 4, r, g, bl);
        hgt[i] = 0.012 * t;
      }
    }
    return { map: texture(ctx, alb, n, n, W, W, true), nr: texture(ctx, packNR(hgt, n, n, W, W, 1), n, n, W, W) };
  }));
}

// ------------------------------------------------------------------------------------------------ small patterns
function solarTex(ctx) {            // 2 x 2 cells of 156 mm: pseudo-square mono cells, bus bars, the white backsheet in the corners
  return shared('h2solar', () => timed('solar', () => {
    const n = 256, W = 0.316, { c, g } = tileCanvas(n, n), cs = n / 2, R = prng(11);
    g.fillStyle = css(0.035, 0.04, 0.05); g.fillRect(0, 0, n, n);
    for (let j = 0; j < 2; j++) {
      for (let i = 0; i < 2; i++) {
        const x = i * cs + 1.5, y = j * cs + 1.5, s = cs - 3, k = 0.9 + R() * 0.2, ch = 9;
        g.fillStyle = css(0.04 * k, 0.052 * k, 0.085 * k);
        g.beginPath();
        g.moveTo(x + ch, y); g.lineTo(x + s - ch, y); g.lineTo(x + s, y + ch); g.lineTo(x + s, y + s - ch); g.lineTo(x + s - ch, y + s);
        g.lineTo(x + ch, y + s); g.lineTo(x, y + s - ch); g.lineTo(x, y + ch); g.closePath(); g.fill();
        g.fillStyle = 'rgba(150,160,180,0.16)';
        for (let b = 1; b <= 3; b++) g.fillRect(x + (b * s) / 4 - 0.6, y, 1.2, s);
      }
    }
    return canvasTexture(ctx, c, W, W);
  }));
}

const MOSAIC = { key: 'spa_mosaic', t: 8, W: 8 * 0.0254 * 1.06, rough: 0.2,      // the spa dam: 25 mm dark slate-blue glass with a few bronze / pearl tiles (p21)
  pal: [[[0.065, 0.085, 0.105], 0.4], [[0.085, 0.105, 0.125], 0.25], [[0.13, 0.105, 0.08], 0.12], [[0.17, 0.18, 0.20], 0.08], [[0.045, 0.06, 0.08], 0.15]] };
const WATERLINE = { key: 'pool_tile', t: 4, W: 4 * 0.1524, rough: 0.22,       // the waterline band: dark slate-blue 6 in tile (p21, p22)
  pal: [[[0.045, 0.068, 0.09], 0.4], [[0.058, 0.08, 0.10], 0.3], [[0.038, 0.055, 0.078], 0.3]] };
function mosaicTex(ctx, o) {
  return shared('h2' + o.key, () => timed(o.key, () => {
    const n = 256, t = o.t, ts = n / t, W = o.W;
    const R = prng(66), pal = o.pal;
    const alb = new Uint8Array(n * n * 4), hgt = new Float32Array(n * n), rgh = new Float32Array(n * n);
    const tiles = [];
    for (let k = 0; k < t * t; k++) tiles.push({ c: pick(pal, R()), l: 0.85 + R() * 0.3, tx: (R() - 0.5) * 0.004, ty: (R() - 0.5) * 0.004 });
    for (let y = 0; y < n; y++) {
      for (let x = 0; x < n; x++) {
        const i = y * n + x, tl = tiles[((y / ts) | 0) * t + ((x / ts) | 0)], lx = x % ts, ly = y % ts;
        const e = Math.min(lx, ts - 1 - lx, ly, ts - 1 - ly) + 0.5, m = smooth(1.0, 2.6, e);
        put(alb, i * 4, 0.11 + (tl.c[0] * tl.l - 0.11) * m, 0.105 + (tl.c[1] * tl.l - 0.105) * m, 0.10 + (tl.c[2] * tl.l - 0.10) * m);
        hgt[i] = m * (0.0008 + ((lx - ts / 2) * tl.tx + (ly - ts / 2) * tl.ty) / ts * W / t * 8) - (1 - m) * 0.0008;
        rgh[i] = o.rough + (1 - m) * 0.75;
      }
    }
    return { map: texture(ctx, alb, n, n, W, W, true), nr: texture(ctx, packNR(hgt, n, n, W, W, rgh), n, n, W, W) };
  }));
}

function weaveTex(ctx) {            // outdoor canvas (umbrella, cushions): a fine weave on a 0.12 m tile
  return shared('h2weave', () => {
    const n = 128, W = 0.12, hgt = new Float32Array(n * n), alb = new Uint8Array(n * n * 4), R = prng(3);
    const jit = new Float32Array(n); for (let i = 0; i < n; i++) jit[i] = R();
    for (let y = 0; y < n; y++) {
      for (let x = 0; x < n; x++) {
        const i = y * n + x, a = Math.sin(x * Math.PI / 2) * (((y >> 1) & 1) ? 1 : -1), v = 0.94 + 0.045 * a + 0.03 * (jit[x] + jit[y] - 1);
        hgt[i] = 0.00025 * a;
        put(alb, i * 4, v, v, v);
      }
    }
    return { map: texture(ctx, alb, n, n, W, W, true), nr: texture(ctx, packNR(hgt, n, n, W, W, 1), n, n, W, W) };
  });
}
const canvasCloth = (ctx, color) => surface(ctx, { ...weaveTex(ctx), color, roughness: 1.0, macro: { s1: 0.9, s2: 2.3, amount: 0.06 } });

// ------------------------------------------------------------------------------------------------ world-space planting
// leaves: R = height of the leaf layer (0 = a gap), G = tone, B = hue shift; tile ~1.5 m
function leafTile(ctx, kind) {
  return shared('h2leaf:' + kind, () => timed('leaf tile ' + kind, () => {
    const n = q(ctx, 512), { c, g } = tileCanvas(n, n), R = prng(kind.length * 131 + 7);
    g.fillStyle = 'rgb(0,96,128)'; g.fillRect(0, 0, n, n);
    const needle = kind === 'needle', N = needle ? 6000 : 4200;
    for (let i = 0; i < N; i++) {
      const x = R() * n, y = R() * n, a = R() * 6.283, top = i / N;
      const len = n * (needle ? 0.012 + R() * 0.02 : 0.013 + R() * 0.016), wid = needle ? Math.max(1, n / 512 * 1.3) : len * (0.42 + R() * 0.25);
      const hv = Math.round(Math.min(255, 30 + 170 * top * top + R() * 55)), tone = Math.round(70 + R() * 150), hue = Math.round(R() * 255);
      g.fillStyle = `rgb(${hv},${tone},${hue})`;
      for (let oy = -n; oy <= n; oy += n) {
        if (y + oy < -len || y + oy > n + len) continue;
        for (let ox = -n; ox <= n; ox += n) {
          if (x + ox < -len || x + ox > n + len) continue;
          g.beginPath(); g.ellipse(x + ox, y + oy, len, wid, a, 0, 6.2832); g.fill();
        }
      }
    }
    const t = canvasTexture(ctx, c, 1, 1, false);
    return t;
  }));
}

const FOL_VERT_PARS = 'varying vec3 vPlP;\nvarying vec3 vPlN;';
const FOL_VERT = `
vPlP = ( modelMatrix * vec4( transformed, 1.0 ) ).xyz;
vPlN = normalize( mat3( modelMatrix ) * objectNormal );
`;
const FOL_FRAG_PARS = `
varying vec3 vPlP;
varying vec3 vPlN;
uniform sampler2D uPlNoise;
uniform sampler2D uPlLeaf;
uniform vec4 uPlS;          // clump scale, leaf scale (1 / m), bump of the clumps, of the leaves (m)
uniform vec4 uPlK;          // cut face-on, cut at the outline, depth tone of the hollows, hue variation
uniform vec3 uPlThrough;    // colour of the light through the leaves
uniform float uPlUp;
uniform float uPlVar;       // crown-to-crown variation of tone and hue
uniform vec4 uPlBloom;     // flowers on the top leaves: colour, share
float plClump = 0.5;
float plLeafH = 0.5;
vec3 plSun = vec3( 0.0 );
vec3 plThrough = vec3( 0.0 );
vec4 plTri( sampler2D t, vec3 p, vec3 w ) {
  return texture2D( t, p.zy ) * w.x + texture2D( t, p.xz ) * w.y + texture2D( t, p.xy ) * w.z;
}
`;
const FOL_FRAG = `
{
  vec3 plW = abs( normalize( vPlN ) );
  plW = plW * plW; plW /= ( plW.x + plW.y + plW.z );
  #ifdef PL_FAR      // a canopy seen from far off, on a near-flat sheet: two turned copies of each field, so no period shows
  vec2 plQ = vPlP.xz, plQ1 = mat2( 0.8, -0.6, 0.6, 0.8 ) * plQ, plQ2 = mat2( 0.28, 0.96, -0.96, 0.28 ) * plQ;
  vec4 plC = 0.5 + 0.6 * ( texture2D( uPlNoise, plQ1 * uPlS.x ) + texture2D( uPlNoise, plQ2 * ( uPlS.x * 0.61 ) + 0.13 ) - 1.0 );
  vec4 plC2 = 0.5 + 0.6 * ( texture2D( uPlNoise, plQ * ( uPlS.x * 2.9 ) + 0.37 ) + texture2D( uPlNoise, plQ2 * ( uPlS.x * 4.3 ) + 0.71 ) - 1.0 );
  vec4 plL = 0.5 * ( texture2D( uPlLeaf, plQ1 * uPlS.y ) + texture2D( uPlLeaf, plQ2 * ( uPlS.y * 0.63 ) + 0.21 ) );
  plL.r = smoothstep( 0.15, 0.75, plL.r );
  #else
  vec4 plC = plTri( uPlNoise, vPlP * uPlS.x, plW );
  vec4 plC2 = plTri( uPlNoise, vPlP.yzx * ( uPlS.x * 2.9 ) + 0.37, plW.yzx );
  vec4 plL = plTri( uPlLeaf, vPlP * uPlS.y, plW );
  #endif
  plClump = clamp( ( plC.r - 0.5 ) * 2.6 + ( plC2.g - 0.5 ) * 1.5 + 0.5, 0.0, 1.0 );
  plLeafH = plL.r;
  float plNdv = abs( dot( normalize( vNormal ), normalize( vViewPosition ) ) );
  float plEdge = 1.0 - plNdv;
  float plCov = plLeafH * ( 0.4 + 1.0 * plClump );
  if ( plCov < uPlK.x + uPlK.y * plEdge * plEdge ) discard;
  float plShade = mix( uPlK.z, 1.0, smoothstep( 0.05, 0.8, plLeafH ) ) * mix( 0.4, 1.15, plClump );
  vec3 plHue = mix( vec3( 1.0 + uPlK.w, 1.0, 1.0 - uPlK.w ), vec3( 1.0 - uPlK.w, 1.0, 1.0 + 0.6 * uPlK.w ), plL.b );
  diffuseColor.rgb *= plShade * ( 0.72 + 0.56 * plL.g ) * plHue * ( 0.8 + 0.4 * plC.b );
  diffuseColor.rgb = mix( diffuseColor.rgb, uPlBloom.rgb * ( 0.7 + 0.3 * plClump ) * ( 0.85 + 0.3 * plL.g ), step( 1.0 - uPlBloom.a, plL.b ) * smoothstep( 0.3, 0.55, plLeafH ) );
  {      // one crown is not the next: tone and hue drift over ~10 m (olive / yellow-green / blue-green)
    vec4 plV = texture2D( uPlNoise, vPlP.xz * 0.083 + 0.19 ), plV2 = texture2D( uPlNoise, vPlP.zx * 0.031 + 0.63 );
    float plT = clamp( ( plV.r + plV2.g - 1.0 ) * 2.2, -1.0, 1.0 ), plU = clamp( ( plV.b + plV2.r - 1.0 ) * 2.2, -1.0, 1.0 );
    diffuseColor.rgb *= 1.0 + uPlVar * 0.3 * plT;
    diffuseColor.rgb *= mix( vec3( 1.0 ), plU > 0.0 ? vec3( 1.16, 1.03, 0.78 ) : vec3( 0.80, 0.95, 1.10 ), uPlVar * abs( plU ) );
  }
  if ( ! gl_FrontFacing ) diffuseColor.rgb *= 0.3;
}
`;
const FOL_BUMP = `
{
  normal = normalize( normal + uPlUp * ( viewMatrix * vec4( 0.0, 1.0, 0.0, 0.0 ) ).xyz );      // crowns are lit from above: soften the facets
  float plHt = uPlS.z * plClump + uPlS.w * plLeafH;
  vec3 plDx = dFdx( - vViewPosition ), plDy = dFdy( - vViewPosition );
  float plHx = dFdx( plHt ), plHy = dFdy( plHt );
  vec3 plR1 = cross( plDy, normal ), plR2 = cross( normal, plDx );
  float plDet = dot( plDx, plR1 );
  vec3 plGrad = sign( plDet ) * ( plHx * plR1 + plHy * plR2 );
  normal = normalize( abs( plDet ) * normal - clamp( plGrad, -4.0 * abs( plDet ), 4.0 * abs( plDet ) ) );
}
`;
let lightsChunk = null;
function throughLights() {
  if (lightsChunk) return lightsChunk;
  const lights = THREE.ShaderChunk.lights_fragment_begin.split('#if ( NUM_DIR_LIGHTS > 0 ) && defined( RE_Direct )');
  const dir = lights[1].split('#if ( NUM_RECT_AREA_LIGHTS > 0 )');
  dir[0] = dir[0]
    .replace('getDirectionalLightInfo( directionalLight, directLight );', 'getDirectionalLightInfo( directionalLight, directLight );\n\t\tplSun = directLight.color;')
    .replace('RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );',
      `RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
      {
        float plBack = saturate( - dot( geometryNormal, directLight.direction ) );
        float plVL = saturate( dot( geometryViewDir, - directLight.direction ) );
        plThrough += mix( directLight.color, plSun, 0.4 ) * ( 0.6 * plBack + 0.3 * plVL * plVL );
      }`);
  lightsChunk = lights[0] + '#if ( NUM_DIR_LIGHTS > 0 ) && defined( RE_Direct )' + dir.join('#if ( NUM_RECT_AREA_LIGHTS > 0 )');
  return lightsChunk;
}

/** spec = { color (linear), clump (m), leaf (m, the leaf tile's size), bump: [clumps, leaves] (m), cut: [face-on, outline],
 *           depth, hue, through: [r, g, b, k], kind: 'broad' | 'needle', rough, twoSided } */
function foliage(ctx, spec) {
  const two = spec.twoSided !== false;
  const m = new THREE.MeshStandardMaterial({ roughness: spec.rough ?? 0.82, metalness: 0, side: two ? THREE.DoubleSide : THREE.FrontSide });
  m.color.setRGB(spec.color[0], spec.color[1], spec.color[2], THREE.LinearSRGBColorSpace);
  m.shadowSide = THREE.FrontSide;
  m.envMapIntensity = 0.85;
  const th = spec.through || [0.75, 1.0, 0.25, 0.4], cut = spec.cut || [0.17, 1.3], bump = spec.bump || [0.9, 0.035];
  const U = {
    uPlNoise: { value: macroNoise(ctx) },
    uPlLeaf: { value: leafTile(ctx, spec.kind || 'broad') },
    uPlS: { value: new THREE.Vector4(1 / (spec.clump || 3.4), 1 / (spec.leaf || 0.62), bump[0], bump[1]) },
    uPlK: { value: new THREE.Vector4(cut[0], cut[1], spec.depth ?? 0.22, spec.hue ?? 0.12) },
    uPlThrough: { value: new THREE.Vector3(th[0], th[1], th[2]).multiplyScalar(th[3]) },
    uPlUp: { value: spec.up ?? 0.7 },
    uPlVar: { value: spec.vary ?? (spec.far ? 0.5 : 1) },
    uPlBloom: { value: new THREE.Vector4(...(spec.bloom || [1, 1, 1, 0])) },
  };
  m.userData.foliage = U;
  m.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, U);
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\n' + FOL_VERT_PARS)
      .replace('#include <begin_vertex>', '#include <begin_vertex>\n' + FOL_VERT);
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', '#include <common>\n' + FOL_FRAG_PARS)
      .replace('#include <map_fragment>', '#include <map_fragment>\n' + FOL_FRAG)
      .replace('#include <normal_fragment_maps>', '#include <normal_fragment_maps>\n' + FOL_BUMP)
      .replace('#include <lights_fragment_begin>', throughLights())
      .replace('#include <lights_fragment_end>', '#include <lights_fragment_end>\n\treflectedLight.directDiffuse += plThrough * BRDF_Lambert( material.diffuseColor * uPlThrough );')
      // the far canopy fades into the haze of the valley (p28)
      .replace('#include <tonemapping_fragment>', `#ifdef PL_FAR
      gl_FragColor.rgb = mix( gl_FragColor.rgb, vec3( 0.56, 0.63, 0.72 ) * clamp( max( plSun.r, plSun.g ) / 3.0, 0.25, 1.0 ), 1.0 - exp( - max( length( vViewPosition ) - 110.0, 0.0 ) / 800.0 ) );
      #endif
      #include <tonemapping_fragment>`);
  };
  if (spec.far) m.defines = { PL_FAR: '' };
  m.customProgramCacheKey = () => 'h2-foliage-2' + (spec.far ? 'f' : '');
  return m;
}

// bark, projected from the sides (u round the trunk, v up it): R = tone, alpha-less; the relief comes from the tone
function barkTile(ctx, kind) {
  return shared('h2bark:' + kind, () => timed('bark ' + kind, () => {
    const n = 256, d = new Uint8Array(n * n * 4), f = new Float32Array(n * n);
    if (kind === 'birch') {        // white paper bark, dark lenticels across, black scars
      addNoise(f, n, n, 6, 40, 0.5, 5); addNoise(f, n, n, 3, 3, 0.35, 6);
      const g = new Float32Array(n * n); addNoise(g, n, n, 14, 90, 1, 7);
      const s = new Float32Array(n * n); addNoise(s, n, n, 5, 7, 1, 8);
      for (let i = 0; i < n * n; i++) {
        let v = 0.9 + 0.1 * f[i];
        if (g[i] > 0.55) v *= 0.45;
        if (s[i] > 0.72) v *= 0.22;
        f[i] = v;
      }
    } else if (kind === 'smooth') {   // crape myrtle: smooth, mottled tan / cinnamon patches
      addNoise(f, n, n, 5, 3, 0.5, 15); addNoise(f, n, n, 11, 6, 0.3, 16); addNoise(f, n, n, 40, 12, 0.1, 17);
      for (let i = 0; i < n * n; i++) f[i] = 0.8 + 0.2 * Math.round(f[i] * 3) / 3 + 0.05 * f[i];
    } else {                          // furrowed: ridges up the trunk
      addNoise(f, n, n, 22, 4, 0.6, 25); addNoise(f, n, n, 46, 9, 0.35, 26); addNoise(f, n, n, 90, 30, 0.2, 27); addNoise(f, n, n, 4, 4, 0.2, 28);
      for (let i = 0; i < n * n; i++) f[i] = 0.42 + 0.58 * smooth(-0.45, 0.4, f[i]);
    }
    for (let i = 0; i < n * n; i++) { const v = Math.max(0, Math.min(255, f[i] * 255)); d[i * 4] = d[i * 4 + 1] = d[i * 4 + 2] = v; d[i * 4 + 3] = 255; }
    return texture(ctx, d, n, n, 1, 1);
  }));
}
function bark(ctx, spec) {
  const m = new THREE.MeshStandardMaterial({ roughness: spec.rough ?? 0.95, metalness: 0 });
  m.color.setRGB(spec.color[0], spec.color[1], spec.color[2], THREE.LinearSRGBColorSpace);
  const U = { uBkTex: { value: barkTile(ctx, spec.kind) }, uBkS: { value: new THREE.Vector3(1 / spec.tile[0], 1 / spec.tile[1], spec.bump ?? 0.01) } };
  m.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, U);
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\n' + FOL_VERT_PARS)
      .replace('#include <begin_vertex>', '#include <begin_vertex>\n' + FOL_VERT);
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vPlP;\nvarying vec3 vPlN;\nuniform sampler2D uBkTex;\nuniform vec3 uBkS;\nfloat bkH = 0.5;')
      .replace('#include <map_fragment>', `#include <map_fragment>
      {
        vec3 bkW = abs( normalize( vPlN ) ); bkW.y = 0.0; bkW = bkW * bkW + 1e-4; bkW /= ( bkW.x + bkW.z );
        bkH = texture2D( uBkTex, vec2( vPlP.z * uBkS.x, vPlP.y * uBkS.y ) ).r * bkW.x + texture2D( uBkTex, vec2( vPlP.x * uBkS.x, vPlP.y * uBkS.y ) ).r * bkW.z;
        diffuseColor.rgb *= bkH;
      }`)
      .replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
      {
        float bkHt = uBkS.z * bkH;
        vec3 bkDx = dFdx( - vViewPosition ), bkDy = dFdy( - vViewPosition );
        vec3 bkR1 = cross( bkDy, normal ), bkR2 = cross( normal, bkDx );
        float bkDet = dot( bkDx, bkR1 );
        vec3 bkG = sign( bkDet ) * ( dFdx( bkHt ) * bkR1 + dFdy( bkHt ) * bkR2 );
        normal = normalize( abs( bkDet ) * normal - clamp( bkG, -2.0 * abs( bkDet ), 2.0 * abs( bkDet ) ) );
      }`);
  };
  m.customProgramCacheKey = () => 'h2-bark-1';
  return m;
}

// spring crowns (p21, p22, p26, the video): fresh yellow-greens, olive evergreen oaks; LINEAR, the fully lit leaf
const LEAVES = {
  pl_leaf: { color: [0.070, 0.115, 0.030] },
  pl_leaf_light: { color: [0.115, 0.17, 0.042], through: [0.8, 1.0, 0.2, 0.55] },
  pl_leaf_dark: { color: [0.036, 0.058, 0.024], depth: 0.25, through: [0.7, 1.0, 0.3, 0.25], leaf: 0.55 },
  pl_leaf_yellow: { color: [0.17, 0.20, 0.04], through: [0.9, 1.0, 0.15, 0.55] },
  pl_leaf_maple: { color: [0.11, 0.16, 0.038], leaf: 0.55, clump: 3.2, through: [0.85, 1.0, 0.2, 0.6] },
  pl_leaf_red: { color: [0.19, 0.05, 0.036], leaf: 0.55, clump: 3.2, hue: 0.06, vary: 0.4, through: [1.0, 0.35, 0.2, 0.6] },
  pl_leaf_conifer: { color: [0.026, 0.048, 0.027], kind: 'needle', leaf: 0.6, clump: 2.6, depth: 0.2, cut: [0.12, 0.8], through: [0.7, 1.0, 0.4, 0.2] },
  pl_blossom: { color: [0.085, 0.13, 0.036], leaf: 0.5, clump: 1.6, bump: [0.35, 0.03], hue: 0.08, vary: 0.4, bloom: [0.80, 0.78, 0.73, 0.42] },
  yard_vine: { color: [0.07, 0.12, 0.03], leaf: 0.6, clump: 2.4, bump: [0.2, 0.03] },
  pl_far_canopy: { color: [0.085, 0.10, 0.05], clump: 23, leaf: 9, bump: [2.0, 0.4], up: 0, cut: [-1, 0], depth: 0.6, twoSided: false, far: true },
  pl_far_hill: { color: [0.13, 0.14, 0.10], clump: 310, leaf: 131, bump: [10.0, 1.5], up: 0, cut: [-1, 0], depth: 0.85, twoSided: false, far: true },
  foliage_dark: { color: [0.036, 0.058, 0.024], depth: 0.25 },
  ground_far: { color: [0.12, 0.13, 0.085], clump: 70, leaf: 31, bump: [1.0, 0.2], up: 0, cut: [-1, 0], depth: 0.8, twoSided: false, far: true },
};

// ------------------------------------------------------------------------------------------------ registry
export function register(lib) {
  lib.onTime(() => { const k = envK(lib.ctx); for (const m of metals) m.envMapIntensity = k * (m.userData.envK || 1); });
  const jointed = (m, ctx) => { m.userData.swatchNR = flatNR(ctx); return m; };      // a photo swatch brings its own joints

  // ---- the house
  lib.add('siding_shingle', (ctx) => surface(ctx, { ...cedarTex(ctx), color: C.shingleSiding, roughness: 0.9, swatchFade: [14, 40],
    detail: { kind: 'fibre', size: 0.21, albedo: 0.1, normal: 0.15 }, macro: { s1: 4.3, s2: 15, amount: 0.05, tint: [1.06, 1.0, 0.93], tintAmount: 0.25 } }));
  const trimPaint = (ctx) => surface(ctx, { color: C.trim, roughness: 0.55, detail: { kind: 'fibre', size: 0.11, albedo: 0.035, normal: 0.05, rough: 0.06 }, macro: { s1: 1.7, s2: 6.1, amount: 0.035 } });
  lib.add('trim_cream', trimPaint);
  lib.add('yard_column_white', trimPaint);
  // the front lower storey (hero, p01: taupe lap siding, ~0.10 m exposure) -- for when the house zone names it
  const lap = (ctx) => surface(ctx, { color: [0.215, 0.185, 0.14], roughness: 0.8, ...grooveTex(ctx, 'h2lap', false, 0.10, 0.006, 0.006),
    detail: { kind: 'fibre', size: 0.19, albedo: 0.06, normal: 0.1 }, macro: { s1: 3.9, s2: 13, amount: 0.05 } });
  lib.add('siding_lap_taupe', lap);
  lib.add('siding_taupe', lap);
  lib.add('gutter_cream', (ctx) => paint(ctx, C.gutter, 0.4));
  lib.add('soffit_white', (ctx) => paint(ctx, [0.80, 0.785, 0.725], 0.6, grooveTex(ctx, 'soffit', false, 0.14, 0.005, 0.003)));
  lib.add('frame_bronze', (ctx) => new THREE.MeshStandardMaterial({ color: new THREE.Color().setRGB(...C.bronze, THREE.LinearSRGBColorSpace), roughness: 0.38, metalness: 0.0 }));
  lib.add('door_espresso', (ctx) => surface(ctx, { color: C.espresso, roughness: 0.42, ...grooveTex(ctx, 'h2door', true, 0.14, 0.006, 0.002),
    detail: { kind: 'fibre', size: 0.09, sizeV: 0.5, albedo: 0.45, normal: 0.15, rough: 0.08 } }));
  lib.add('door_garage', (ctx) => paint(ctx, C.trim, 0.45, grooveTex(ctx, 'garage', true, 0.1524, 0.007, 0.003)));
  lib.add('vent_louvre', (ctx) => paint(ctx, C.louvre, 0.7, grooveTex(ctx, 'louvre', false, 0.045, 0.02, 0.012)));

  // ---- roofs
  lib.add('roof_shingle', (ctx) => surface(ctx, { ...shingleTex(ctx), color: C.roof, roughness: 0.96,
    detail: { kind: 'grit', size: 0.31, albedo: 0.4, normal: 0.55 }, macro: { s1: 6.3, s2: 23, amount: 0.1 } }));
  lib.add('ridge_cap', (ctx) => surface(ctx, { color: C.ridge, roughness: 0.96, ...grooveTex(ctx, 'ridge', true, 0.143, 0.008, 0.004),
    detail: { kind: 'grit', size: 0.31, albedo: 0.4, normal: 0.55 }, macro: { s1: 6.3, s2: 23, amount: 0.1 } }));
  lib.add('solar', (ctx) => {
    const m = new THREE.MeshStandardMaterial({ map: solarTex(ctx), roughness: 0.16, metalness: 0.0 });
    m.envMapIntensity = envK(ctx) * 2.2; m.userData.envK = 2.2; metals.push(m);
    return m;
  });
  lib.add('solar_frame', (ctx) => metal(ctx, [0.42, 0.43, 0.45], 0.42, 0.85));
  lib.add('deck_flashing', (ctx) => metal(ctx, [0.42, 0.43, 0.44], 0.5, 0.7));
  lib.add('conduit', (ctx) => metal(ctx, [0.34, 0.35, 0.36], 0.5, 0.75));
  lib.add('chimney_shroud', (ctx) => metal(ctx, [0.36, 0.34, 0.31], 0.5, 0.7));
  lib.add('vent_metal', (ctx) => metal(ctx, [0.14, 0.14, 0.15], 0.55, 0.5));
  lib.add('vent_white', (ctx) => paint(ctx, [0.74, 0.74, 0.72], 0.45));
  lib.add('dish_white', (ctx) => paint(ctx, [0.72, 0.72, 0.70], 0.4));

  // ---- paving, walls, grounds
  lib.add('bluestone', (ctx) => (surface(ctx, { ...piecesTex(ctx, 'h2flag', FLAG), color: C.flag, roughness: 1.0, swatchFade: [22, 60], worldUV: 0.80,      // laid square to the pool and the house (45.8 deg in plan)
   
    detail: { kind: 'grit', size: 0.27, albedo: 0.2, normal: 0.3, rough: 0.05 }, macro: { s1: 7.9, s2: 29, amount: 0.07, tint: [1.05, 1.0, 0.93], tintAmount: 0.3 } })));
  lib.add('coping', (ctx) => surface(ctx, { ...groundTex(ctx, 'h2coping', { tile: 1.3, ox: 311, oy: 87, cloud: 0.06, grain: 0.05, speck: 0.03, warm: 0.02, relief: 0.0004 }),
    color: C.coping, roughness: 0.82, detail: { kind: 'grit', size: 0.24, albedo: 0.14, normal: 0.2, rough: 0.04 }, macro: { s1: 2.9, s2: 9.1, amount: 0.05 } }));
  lib.add('coping_joint', { color: 0x8d8a83, roughness: 0.95 });
  lib.add('skimmer_lid', { color: 0xc9c7c0, roughness: 0.7 });
  lib.add('paver_drive', (ctx) => jointed(surface(ctx, { ...coursedTex(ctx, 'paver_drive', PAVER), color: SC.paver, roughness: 1.0,
    detail: { kind: 'grit', size: 0.21, albedo: 0.32, normal: 0.45 }, macro: { s1: 6.1, s2: 21, amount: 0.08 } }), ctx));
  const cap = (color) => (ctx) => surface(ctx, { ...groundTex(ctx, 'h2cap', { tile: 1.1, ox: 71, oy: 733, cloud: 0.1, grain: 0.07, speck: 0.04, warm: 0.02, relief: 0.0006 }),
    color, roughness: 0.85, detail: { kind: 'grit', size: 0.22, albedo: 0.2, normal: 0.3 }, macro: { s1: 2.3, s2: 7.9, amount: 0.1 } });
  lib.add('wall_cap', cap(C.wallCap));
  lib.add('yard_stone_cap', cap(C.stoneCap));
  const own = (m) => { m.userData.swatchOwn = true; return m; };      // the patch for these is one fireplace crop shared by three stones: the drawn stone is closer
  lib.add('fieldstone', (ctx) => surface(ctx, { ...piecesTex(ctx, 'h2ledge', LEDGE), color: [0.8, 0.8, 0.8], roughness: 1.0, swatchFade: [25, 70],
    detail: { kind: 'grit', size: 0.23, albedo: 0.2, normal: 0.5 }, macro: { s1: 3.1, s2: 11, amount: 0.08 } }));
  lib.add('yard_fieldstone', (ctx) => surface(ctx, { ...piecesTex(ctx, 'h2fire', FIRE), color: [0.70, 0.66, 0.62], roughness: 1.0, swatchFade: [25, 70],
    detail: { kind: 'grit', size: 0.23, albedo: 0.2, normal: 0.45 }, macro: { s1: 2.1, s2: 6.7, amount: 0.06 } }));
  lib.add('stone_veneer', (ctx) => own(surface(ctx, { ...piecesTex(ctx, 'h2ledge', LEDGE), color: [1.0, 0.97, 0.93], roughness: 1.0,
    detail: { kind: 'grit', size: 0.23, albedo: 0.2, normal: 0.45 }, macro: { s1: 2.1, s2: 6.7, amount: 0.06 } })));
  lib.add('pl_nb_stone', (ctx) => surface(ctx, { ...piecesTex(ctx, 'h2fire', FIRE), color: [1, 1, 1], roughness: 1.0 }));
  lib.add('yard_firebrick', (ctx) => surface(ctx, { ...coursedTex(ctx, 'h2firebrick', FIREBRICK), color: [1, 1, 1], roughness: 1.0,
    detail: { kind: 'grit', size: 0.2, albedo: 0.2, normal: 0.3 } }));
  lib.add('yard_soot', { color: 0x1c1a18, roughness: 1.0 });

  lib.add('turf_synthetic', (ctx) => surface(ctx, { ...turfTex(ctx), color: C.turf, roughness: 0.92, normalScale: 0.6,
    detail: { kind: 'blades', size: 0.3, albedo: 0.22, normal: 0.3 }, macro: { s1: 9.1, s2: 33, amount: 0.07 } }));
  lib.add('mulch', (ctx) => surface(ctx, { ...mulchTex(ctx), color: [0.64, 0.6, 0.6], roughness: 0.95,
    detail: { kind: 'fibre', size: 0.13, albedo: 0.2, normal: 0.3 }, macro: { s1: 2.7, s2: 8.9, amount: 0.12 } }));
  lib.add('wood_chips', (ctx) => surface(ctx, { ...flecksTex(ctx, 'h2chips', CHIPS), color: C.chips, roughness: 0.95, swatchFade: [35, 90],
    detail: { kind: 'fibre', size: 0.13, albedo: 0.18, normal: 0.3 }, macro: { s1: 3.1, s2: 9.7, amount: 0.04 } }));
  lib.add('leaf_litter', (ctx) => surface(ctx, { ...flecksTex(ctx, 'h2litter', LITTER), color: [1.4, 1.4, 1.4], roughness: 1.0,
    detail: { kind: 'fibre', size: 0.15, albedo: 0.2, normal: 0.3 }, macro: { s1: 4.7, s2: 14, amount: 0.25, tint: [0.8, 1.05, 0.7], tintAmount: 0.35 } }));
  lib.add('gravel_path', (ctx) => surface(ctx, { ...flecksTex(ctx, 'h2gravel', GRAVEL), color: [0.95, 0.93, 0.88], roughness: 1.0, swatchFade: [30, 80],
    detail: { kind: 'grit', size: 0.19, albedo: 0.15, normal: 0.4 }, macro: { s1: 3.7, s2: 12, amount: 0.08 } }));
  lib.add('crushed_stone', (ctx) => surface(ctx, { ...flecksTex(ctx, 'h2gravel', GRAVEL), color: [0.86, 0.86, 0.84], roughness: 1.0, swatchFade: [30, 80],
    detail: { kind: 'grit', size: 0.19, albedo: 0.15, normal: 0.4 }, macro: { s1: 3.7, s2: 12, amount: 0.08 } }));
  const soil = (key, color, ox) => (ctx) => surface(ctx, { ...groundTex(ctx, key, { tile: 1.5, ox, oy: 222, cloud: 0.2, grain: 0.18, speck: 0.14, warm: 0.04, relief: 0.004, chips: 0.03, chipTone: 1.5 }),
    color, roughness: 1.0, detail: { kind: 'grit', size: 0.21, albedo: 0.3, normal: 0.5 }, macro: { s1: 3.7, s2: 12, amount: 0.18 } });
  lib.add('orchard_soil', soil('h2orchard', C.orchard, 411));
  lib.add('yard_soil', soil('h2bedsoil', [0.085, 0.06, 0.042], 655));
  lib.add('timber', (ctx) => timberLook(ctx, C.timber));
  lib.add('edging_dark', (ctx) => timberLook(ctx, C.edging, 0.8, 0.15));
  lib.add('handrail_black', (ctx) => metal(ctx, [0.02, 0.02, 0.022], 0.45, 0.5));
  lib.add('grate_metal', (ctx) => metal(ctx, [0.05, 0.052, 0.055], 0.55, 0.6));
  lib.add('lid_green', { color: 0x2c6b40, roughness: 0.65 });

  // ---- pool
  lib.add('spa_mosaic', (ctx) => { const m = surface(ctx, { ...mosaicTex(ctx, MOSAIC), color: [1, 1, 1], roughness: 1.0 }); m.envMapIntensity = envK(ctx) * 1.5; m.userData.envK = 1.5; metals.push(m); return m; });
  lib.add('pool_tile', (ctx) => { const m = surface(ctx, { ...mosaicTex(ctx, WATERLINE), color: [1, 1, 1], roughness: 1.0 }); m.envMapIntensity = envK(ctx); metals.push(m); return m; });
  lib.add('lawn', (ctx) => surface(ctx, { ...lawnTex(ctx), color: [1.02, 1.02, 0.95], roughness: 0.9, normalScale: 0.7,
    detail: { kind: 'blades', size: 0.45, albedo: 0.3, normal: 0.35 }, macro: { s1: 8.3, s2: 37, amount: 0.18, tint: [1.2, 1.06, 0.8], tintAmount: 0.4 } }));
  lib.add('pool_cover_lid', (ctx) => surface(ctx, { ...groundTex(ctx, 'h2coping', { tile: 1.3, ox: 311, oy: 87, cloud: 0.06, grain: 0.05, speck: 0.03, warm: 0.02, relief: 0.0004 }),
    color: [0.55, 0.56, 0.55], roughness: 0.82, detail: { kind: 'grit', size: 0.24, albedo: 0.14, normal: 0.2 } }));

  // ---- yard
  lib.add('yard_timber_dark', (ctx) => timberLook(ctx, C.timberDark, 0.7, 0.25));
  lib.add('yard_wood_grey', (ctx) => timberLook(ctx, C.woodGrey, 0.92, 0.4));
  lib.add('yard_teak_grey', (ctx) => timberLook(ctx, C.teakGrey, 0.85, 0.35));
  lib.add('yard_picket_wood', (ctx) => timberLook(ctx, C.picket, 0.92, 0.4));
  lib.add('yard_slide_green', (ctx) => { const m = new THREE.MeshStandardMaterial({ roughness: 0.42, metalness: 0 }); m.color.setRGB(...C.slide, THREE.LinearSRGBColorSpace); m.envMapIntensity = envK(ctx); metals.push(m); return m; });
  lib.add('yard_stainless', (ctx) => metal(ctx, [0.56, 0.57, 0.58], 0.34, 0.95));
  lib.add('yard_umbrella', (ctx) => canvasCloth(ctx, C.umbrella));
  lib.add('yard_cushion_white', (ctx) => canvasCloth(ctx, C.cushion));
  lib.add('cushion', (ctx) => canvasCloth(ctx, C.cushion));
  lib.add('cushion_edge', (ctx) => canvasCloth(ctx, C.cushion));
  lib.add('furniture_wood', (ctx) => timberLook(ctx, [0.30, 0.25, 0.20], 0.8, 0.35));      // weathered teak (p23)
  lib.add('yard_tire', (ctx) => paint(ctx, [0.02, 0.02, 0.021], 0.85));
  lib.add('yard_rope', (ctx) => timberLook(ctx, C.rope, 0.95, 0.45));
  lib.add('yard_pot_grey', (ctx) => paint(ctx, [0.20, 0.20, 0.21], 0.75));

  // ---- planting
  for (const [name, spec] of Object.entries(LEAVES)) lib.add(name, (ctx) => foliage(ctx, spec));
  lib.add('pl_bark', (ctx) => bark(ctx, { color: [0.20, 0.165, 0.13], kind: 'furrow', tile: [0.5, 1.4], bump: 0.02 }));
  lib.add('bark', (ctx) => bark(ctx, { color: [0.20, 0.165, 0.13], kind: 'furrow', tile: [0.5, 1.4], bump: 0.02 }));
  lib.add('pl_bark_white', (ctx) => bark(ctx, { color: [0.80, 0.78, 0.72], kind: 'birch', tile: [0.45, 0.9], bump: 0.004, rough: 0.8 }));
  lib.add('pl_bark_tan', (ctx) => bark(ctx, { color: [0.50, 0.38, 0.27], kind: 'smooth', tile: [0.3, 0.6], bump: 0.002, rough: 0.7 }));

  // ---- the neighbours (seen from the air, far off): plain, matte, a little weathered
  const far = (color, amount = 0.12) => (ctx) => surface(ctx, { color, roughness: 1.0, macro: { s1: 5.3, s2: 17, amount } });
  lib.add('pl_nb_stucco', far([0.66, 0.62, 0.54], 0.06));
  lib.add('pl_nb_tile', (ctx) => surface(ctx, { color: [0.50, 0.26, 0.14], roughness: 1.0, ...grooveTex(ctx, 'nbtile', true, 0.3, 0.1, 0.04), macro: { s1: 3.3, s2: 11, amount: 0.25, tint: [1.2, 0.95, 0.8], tintAmount: 0.5 } }));
  lib.add('pl_nb_shake', far([0.27, 0.225, 0.17], 0.2));
  lib.add('pl_nb_slate', far([0.20, 0.21, 0.23], 0.14));
  lib.add('pl_nb_deck', far([0.56, 0.54, 0.48], 0.08));
  lib.add('pl_nb_lawn', (ctx) => surface(ctx, { ...lawnTex(ctx), color: [0.9, 0.9, 0.9], roughness: 0.95, macro: { s1: 8.3, s2: 37, amount: 0.2 } }));
  lib.add('pl_nb_water', (ctx) => { const m = new THREE.MeshStandardMaterial({ roughness: 0.08, metalness: 0 }); m.color.setRGB(0.03, 0.22, 0.34, THREE.LinearSRGBColorSpace); m.envMapIntensity = envK(ctx); metals.push(m); return m; });
}
