// Look module "surfaces": the large surfaces of the property -- walls, roofs, paving, ground, door finishes.
// Every material is procedural (./textures.js): seeded noise -> colour map + NR pack (normal, roughness), plus a
// shared detail tile for close range and a shared macro noise against visible tiling.
//
// PATTERN MODULES (metres; the kit's UVs are metres, u along the face, v up the wall / up the slope, origin at
// the UV origin of the face -- align geometry to these):
//   siding_lap, chimney_white   course (exposure) 0.122: 20 courses per 2.44 m door; a course's butt edge is at v = k * 0.122
//   siding_bb                   plain painted board; battens are geometry (0.406 spacing assumed, 64 x 19 mm)
//   soffit_white                tongue-and-groove boards 0.140 wide, grooves along u (lines of constant v)
//   door_garage                 vertical V-groove planks 0.152 wide (grooves at u = k * 0.152)
//   roof_shingle                course 0.143 up the slope (butts at v = k * 0.143), tabs 0.13 - 0.32 wide; tile 3.2 x 2.288
//   roof_seam                   the pan only; ribs are geometry (0.406 pan assumed); no module in the texture
//   roof_flat                   cap-sheet laps every 0.915 along v
//   stone_veneer                ledger panels 0.1525 high (courses at v = k * 0.1525) split into 1 - 3 strips, stones 0.14 - 0.45 long; tile 1.83 x 0.915
//   bluestone                   courses 0.610 deep along v, pieces 0.610 / 0.915 / 1.220 long, joints 7 mm; tile 3.66 x 3.66
//   paver_drive                 courses 0.2286 deep along v, pavers 0.152 / 0.229 / 0.305 long, joints 3 mm; tile 2.743 x 2.743
//   paving_pale                 limestone pavers 0.610 x 0.610 (joints at u, v = k * 0.610); coping = the same stone without joints
//   pool_tile                   0.1524 x 0.1524 tiles, 3 mm grout (joints at u, v = k * 0.1524)
//   fence_wood                  vertical boards 0.140 wide (gaps at u = k * 0.140), grain along v; tile 2.24 x 2.24
//   lawn 4.2, mulch 1.0, soil 1.5, concrete 2.0, asphalt 1.5, pool_plaster 1.0 (tiles without a module)
import {
  prng, srgb8, smooth, timed, addNoise, fbm, bank, coursed, rasterRects, packNR, texture, canvasTexture, tileCanvas,
  shared, surface,
} from './textures.js';

export const MODULES = {
  lap: 0.122, batten: 0.406, soffit: 0.14, garagePlank: 0.1524, shingleCourse: 0.143, seamPan: 0.406, flatLap: 0.915,
  stonePanel: 0.1525, bluestoneCourse: 0.61, paverCourse: 0.2286, palePaver: 0.61, poolTile: 0.1524, fenceBoard: 0.14,
};

// Calibrated base colours (LINEAR albedo multipliers of the colour maps), see the test zone's renders against the
// listing photos: sunlit / shaded medians under the stage's default day light.
const C = {
  white: [0.86, 0.855, 0.83],
  trim: [0.88, 0.875, 0.85],
  soffit: [0.84, 0.835, 0.81],
  shingle: [0.27, 0.262, 0.255],
  seam: [0.058, 0.063, 0.072],
  flat: [0.34, 0.33, 0.32],
  stone: [0.80, 0.79, 0.78],
  bluestone: [0.95, 0.94, 0.91],
  paver: [1.10, 1.04, 0.92],
  limestone: [0.90, 0.855, 0.70],
  concrete: [0.58, 0.565, 0.50],
  asphalt: [0.082, 0.082, 0.086],
  poolTile: [1.0, 1.0, 1.0],
  plaster: [0.80, 0.86, 0.87],
  fence: [1.0, 1.0, 1.0],
  fenceFrame: [0.20, 0.085, 0.036],
  lawn: [1.0, 1.0, 1.0],
  mulch: [1.0, 1.0, 1.0],
  soil: [0.105, 0.075, 0.052],
  navy: [0.019, 0.027, 0.058],
  mahogany: [0.15, 0.036, 0.016],
  awning: [0.030, 0.030, 0.029],
  gutter: [0.017, 0.018, 0.020],
  pergola: [0.070, 0.074, 0.082],
  cap: [0.018, 0.019, 0.022],
};

const q = (ctx, n) => (ctx.quality === 'low' ? n >> 1 : n);
const bk = (ctx) => bank(q(ctx, 1024));
const put = (d, o, r, g, b) => { d[o] = srgb8(r); d[o + 1] = srgb8(g); d[o + 2] = srgb8(b); d[o + 3] = 255; };

// ---------------------------------------------------------------------------------------------- walls
function sidingTex(ctx) {
  return shared('siding', () => timed('siding_lap', () => {
    const w = q(ctx, 256), h = q(ctx, 512), n = 8, ch = h / n, W = 1.0, H = n * MODULES.lap;
    const { A, S, M } = bk(ctx);
    const alb = new Uint8Array(w * h * 4), hgt = new Float32Array(w * h), rgh = new Float32Array(w * h);
    const rnd = prng(41);
    for (let c = 0; c < n; c++) {
      const tone = 1 - rnd() * 0.022, ox = (rnd() * S) | 0;
      for (let r = 0; r < ch; r++) {
        const y = c * ch + r;
        // a course leans out 8 mm toward its butt edge (the bottom rows), which is rounded and undercut
        const fall = r >= ch - 1 ? 0.12 : r >= ch - 2 ? 0.62 : 1;
        const hh = 0.008 * Math.min(1, r / (ch - 2)) * fall;
        // the shadow / occlusion line under the butt of the course above, baked: it does not depend on the view
        const ao = 1 - 0.55 * (1 - smooth(ch * 0.025, ch * 0.062, r)) - 0.06 * Math.exp(-r / (ch * 0.2)) - (r >= ch - 1 ? 0.3 : 0);
        for (let x = 0; x < w; x++) {
          const i = y * w + x, nz = A[((y * 3 + c * 131) & M) * S + ((x * 2 + ox) & M)];
          const v = tone * ao * (0.978 + 0.022 * nz);
          put(alb, i * 4, v, v, v);
          hgt[i] = hh + 0.0002 * nz;
          rgh[i] = 0.95 + 0.05 * nz;
        }
      }
    }
    return { map: texture(ctx, alb, w, h, W, H, true), nr: texture(ctx, packNR(hgt, w, h, W, H, rgh), w, h, W, H) };
  }));
}

function grooveTex(ctx, key, vertical, pitch, gw = 0.006, depth = 0.003) {
  return shared('groove:' + key, () => timed('grooves ' + key, () => {
    const n = q(ctx, 256), m = 8, w = vertical ? n : m, h = vertical ? m : n;
    const alb = new Uint8Array(w * h * 4), hgt = new Float32Array(w * h);
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const p = vertical ? x : y, d = (Math.min(p, n - 1 - p) + 0.5) * pitch / n, i = y * w + x;
        const t = Math.min(1, d / (gw / 2));
        hgt[i] = -depth * (1 - t);
        const v = 0.5 + 0.5 * smooth(0, gw * 0.9, d);
        put(alb, i * 4, v, v, v);
      }
    }
    return { map: texture(ctx, alb, w, h, pitch, pitch, true), nr: texture(ctx, packNR(hgt, w, h, pitch, pitch, 1), w, h, pitch, pitch) };
  }));
}

const paint = (ctx, color, roughness, extra = {}) => surface(ctx, {
  color, roughness, detail: { kind: 'grit', size: 0.19, albedo: 0.012, normal: 0.035, rough: 0.03 }, macro: { amount: 0.02 }, ...extra,
});

// ---------------------------------------------------------------------------------------------- roofs
function shingleTex(ctx) {
  return shared('shingle', () => timed('roof_shingle', () => {
    const w = q(ctx, 1024), h = q(ctx, 1024), n = 16, ch = h / n, W = 3.2, H = n * MODULES.shingleCourse, pxu = w / W;
    const { B, W: Wn, S, M } = bk(ctx);
    const rnd = prng(73);
    const kind = new Uint8Array(n * w), side = new Float32Array(n * w), tone = new Float32Array(n * w), warm = new Float32Array(n * w);
    for (let c = 0; c < n; c++) {
      const x0 = (rnd() * w) | 0;
      let filled = 0, raised = rnd() < 0.5;
      while (filled < w) {
        let len = Math.round((raised ? 0.13 + rnd() * 0.19 : 0.08 + rnd() * 0.13) * pxu);
        if (w - filled - len < 0.07 * pxu) len = w - filled;
        const t = raised ? 0.98 + rnd() * 0.22 : 0.9 + rnd() * 0.12, wm = (rnd() - 0.5) * 0.06;
        for (let i = 0; i < len; i++) {
          const o = c * w + ((x0 + filled + i) % w);
          kind[o] = raised ? 1 : 0; side[o] = Math.min(i + 0.5, len - i - 0.5); tone[o] = t; warm[o] = wm;
        }
        filled += len; raised = !raised;
      }
    }
    const alb = new Uint8Array(w * h * 4), hgt = new Float32Array(w * h);
    for (let c = 0; c < n; c++) {
      const cu = ((c + n - 1) % n) * w, cw = c * w;
      for (let r = 0; r < ch; r++) {
        const y = c * ch + r, fr = r / ch, butt = r >= ch - 1 ? 0.15 : r >= ch - 2 ? 0.62 : 1;
        const eA = Math.exp(-r / (ch * 0.07)), eB = Math.exp(-r / (ch * 0.035));
        for (let x = 0; x < w; x++) {
          const i = y * w + x, k = kind[cw + x], s = side[cw + x], ka = kind[cu + x];
          const up = smooth(0, 2.4, s);
          hgt[i] = (0.003 * fr + (k ? 0.0034 * up : 0)) * butt;
          // baked: the shadow under the butt of the course above (deeper under a laminated tab), the shadow band
          // of the cut-outs and the shade beside the tabs
          let sh = 1 - (ka ? 0.62 * eA : 0.34 * eB);
          if (!k) sh *= (0.84 - 0.42 * (1 - smooth(0.28, 0.62, fr))) * (0.76 + 0.24 * smooth(0, 4, s));   // the dark shadow band
          else sh *= (0.9 + 0.1 * up) * (1.03 - 0.1 * fr * fr);
          if (r >= ch - 1) sh *= 0.8;
          const g = 1 + 0.11 * Wn[((y * 7) & M) * S + ((x * 5) & M)] + 0.09 * B[(y & M) * S + (x & M)];
          const v = tone[cw + x] * sh * g, wm = warm[cw + x];
          put(alb, i * 4, v * (1 + wm), v, v * (1 - wm));
        }
      }
    }
    return { map: texture(ctx, alb, w, h, W, H, true), nr: texture(ctx, packNR(hgt, w, h, W, H, 1), w, h, W, H) };
  }));
}

function seamTex(ctx) {
  return shared('seam', () => timed('roof_seam', () => {
    const n = 256, W = 2.44, H = 4.88;
    const f = fbm(n, n, 6, 2, 3, 311, 0.45), g = fbm(n, n, 5, 5, 4, 312, 0.55);
    const hgt = new Float32Array(n * n), rgh = new Float32Array(n * n);
    for (let i = 0; i < n * n; i++) { hgt[i] = 0.0009 * f[i]; rgh[i] = 0.9 + 0.1 * g[i] + 0.05 * f[i]; }
    return { nr: texture(ctx, packNR(hgt, n, n, W, H, rgh), n, n, W, H) };
  }));
}

function flatRoofTex(ctx) {
  return shared('flatroof', () => timed('roof_flat', () => {
    const n = q(ctx, 512), W = 1.83, H = 1.83, half = n / 2;
    const { A, B, W: Wn, S, M } = bk(ctx);
    const alb = new Uint8Array(n * n * 4), hgt = new Float32Array(n * n);
    for (let y = 0; y < n; y++) {
      const r = y % half, lap = r < 2 ? 1 : 0, sheet = y < half ? 1.0 : 0.965;
      for (let x = 0; x < n; x++) {
        const i = y * n + x, a = A[((y * 2 + 300) & M) * S + ((x * 2 + 77) & M)], b = B[(y & M) * S + ((x + 400) & M)];
        const v = sheet * (1 + 0.07 * a + 0.06 * b + 0.08 * Wn[i & (S * S - 1)]) * (lap ? 0.6 : 1) * (1 - 0.12 * Math.exp(-r / 5));
        put(alb, i * 4, v, v, v);
        hgt[i] = 0.003 * Math.min(1, r / 3) + 0.0006 * b;
      }
    }
    return { map: texture(ctx, alb, n, n, W, H, true), nr: texture(ctx, packNR(hgt, n, n, W, H, 1), n, n, W, H) };
  }));
}

// ---------------------------------------------------------------------------------------------- stone
const STONE = [   // linear albedo, weight: the warm grey / buff / blue-grey / gold mix of the ledger stone
  [[0.42, 0.40, 0.37], 0.30], [[0.53, 0.51, 0.46], 0.24], [[0.36, 0.38, 0.40], 0.16], [[0.50, 0.44, 0.34], 0.16],
  [[0.48, 0.36, 0.22], 0.06], [[0.62, 0.60, 0.56], 0.08],
];
const tame = (c) => [0.47 + (c[0] - 0.47) * 0.6, 0.45 + (c[1] - 0.45) * 0.6, 0.41 + (c[2] - 0.41) * 0.6];
const pick = (table, u) => { let a = 0; for (const [v, p] of table) { a += p; if (u <= a) return v; } return table[table.length - 1][0]; };

function stoneTex(ctx) {
  return shared('stone', () => timed('stone_veneer', () => {
    const w = q(ctx, 1024), h = q(ctx, 512), W = 1.83, H = 0.915, bands = 6, bh = h / bands, pxm = w / W;
    const { A, B, S, M } = bk(ctx);
    const rnd = prng(1907), rects = [];
    for (let j = 0; j < bands; j++) {
      let x = (rnd() * 0.4 * pxm) | 0;
      const end = x + w;
      while (x < end) {
        let seg = (0.26 + rnd() * 0.36) * pxm;
        if (end - x - seg < 0.2 * pxm) seg = end - x;
        const u = rnd();
        const split = u < 0.08 ? [1] : u < 0.42 ? [0.5, 0.5] : u < 0.60 ? [0.34, 0.66] : u < 0.78 ? [0.66, 0.34] : [0.333, 0.334, 0.333];
        let y = j * bh;
        for (const f of split) {
          let sx = x;
          const xe = x + seg;
          while (sx < xe) {
            let len = (f > 0.9 ? 0.2 + rnd() * 0.22 : 0.13 + rnd() * 0.3) * pxm;
            if (xe - sx - len < 0.11 * pxm) len = xe - sx;
            rects.push({ x0: sx, x1: sx + len, y0: y, y1: y + f * bh, col: tame(pick(STONE, rnd())), col2: tame(pick(STONE, rnd())),
              off: rnd(), ox: (rnd() * S) | 0, oy: (rnd() * S) | 0, tx: (rnd() - 0.5) * 0.06, ty: (rnd() - 0.5) * 0.22, lum: 0.88 + rnd() * 0.24 });
            sx += len;
          }
          y += f * bh;
        }
        x += seg;
      }
    }
    const { id, edge } = rasterRects(w, h, rects, 2.5);
    const alb = new Uint8Array(w * h * 4), hgt = new Float32Array(w * h), rgh = new Float32Array(w * h);
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const i = y * w + x, s = rects[id[i]];
        if (!s) { put(alb, i * 4, 0.03, 0.03, 0.03); hgt[i] = -0.014; rgh[i] = 1; continue; }
        const a = A[((y * 2 + s.oy) & M) * S + ((x * 2 + s.ox) & M)], b = B[((y + s.oy) & M) * S + ((x + s.ox) & M)];
        const e = edge[i] + b * 1.2;                           // chipped arrises
        const m = smooth(-0.4, 1.2, e), rim = smooth(0, 5, e);
        const cx = x - (s.x0 + s.x1) * 0.5, cy = y - (s.y0 + s.y1) * 0.5;
        const a2 = A[((y * 5 + s.ox) & M) * S + ((x * 5 + s.oy) & M)];      // split-face cleft, 2 - 6 cm
        hgt[i] = m * (0.003 + 0.012 * s.off + 0.006 * a + 0.009 * Math.abs(a2) + 0.004 * a2 + 0.003 * b + (cx * s.tx + cy * s.ty) / pxm) - (1 - m) * 0.012;
        const vein = smooth(-0.15, 0.45, A[((y * 3 + s.ox) & M) * S + ((x + s.oy) & M)]) * 0.6;
        const l = s.lum * (1 + 0.16 * a + 0.1 * a2 + 0.12 * b) * (0.3 + 0.7 * m) * (0.88 + 0.12 * rim);
        const c = s.col, d = s.col2;
        put(alb, i * 4, l * (c[0] + (d[0] - c[0]) * vein), l * (c[1] + (d[1] - c[1]) * vein), l * (c[2] + (d[2] - c[2]) * vein));
        rgh[i] = 0.9 + 0.1 * b;
      }
    }
    return { map: texture(ctx, alb, w, h, W, H, true), nr: texture(ctx, packNR(hgt, w, h, W, H, rgh), w, h, W, H) };
  }));
}

// pieces laid in courses (bluestone, driveway pavers): shared generator
function coursedTex(ctx, key, o) {
  return shared(key, () => timed(key, () => {
    const n = q(ctx, 1024), W = o.tile, upx = n / o.units, rnd = prng(o.seed);
    const { A, B, W: Wn, S, M } = bk(ctx);
    const rects = coursed(o.rows, o.units, o.choices, rnd, o.units / o.rows).map((r) => {
      const c = pick(o.palette, rnd()), l = 1 + (rnd() - 0.5) * o.toneVar;
      return { x0: r.x0 * upx, x1: r.x1 * upx, y0: r.y0 * upx, y1: r.y1 * upx, col: [c[0] * l, c[1] * l, c[2] * l],
        ox: (rnd() * S) | 0, oy: (rnd() * S) | 0, off: rnd() - 0.5 };
    });
    const { id, edge } = rasterRects(n, n, rects, o.round || 0);
    const alb = new Uint8Array(n * n * 4), hgt = new Float32Array(n * n), rgh = new Float32Array(n * n);
    const jw = o.joint * n / W * 0.5, J = o.jointColor, bev = o.bevel * n / W;
    for (let y = 0; y < n; y++) {
      for (let x = 0; x < n; x++) {
        const i = y * n + x, s = rects[id[i]] || rects[0];
        const a = A[((y + s.oy) & M) * S + ((x + s.ox) & M)], b = B[((y + s.oy) & M) * S + ((x + s.ox) & M)], wn = Wn[(i * 7) & (S * S - 1)];
        const e = edge[i];
        const m = smooth(jw - 0.7, jw + 0.7, e), bv = bev > 0 ? smooth(jw, jw + bev, e) : 1;
        const l = (1 + o.cloud * a + o.grain * b + o.speck * wn) * (0.9 + 0.1 * bv);
        const c = s.col, blush = o.blush ? smooth(0.25, 0.75, A[((y * 2 + s.ox) & M) * S + ((x * 2 + s.oy) & M)]) * o.blush : 0;
        put(alb, i * 4, J[0] + (c[0] * l * (1 + blush) - J[0]) * m, J[1] + (c[1] * l - J[1]) * m, J[2] + (c[2] * l * (1 - blush) - J[2]) * m);
        hgt[i] = m * (o.cleft * a + o.cleft * 0.4 * b + o.lip * s.off) - (1 - bv) * o.bevelDepth - (1 - m) * o.jointDepth;
        rgh[i] = o.rough + (1 - m) * (0.97 - o.rough) + 0.05 * b;
      }
    }
    return { map: texture(ctx, alb, n, n, W, W, true), nr: texture(ctx, packNR(hgt, n, n, W, W, rgh), n, n, W, W) };
  }));
}

const BLUESTONE = {
  seed: 5, tile: 3.66, rows: 6, units: 12, choices: [2, 3, 4], joint: 0.007, jointColor: [0.60, 0.60, 0.57], jointDepth: 0.002,
  bevel: 0.004, bevelDepth: 0.0006, round: 1, cleft: 0.0011, lip: 0.0008, cloud: 0.085, grain: 0.05, speck: 0.03, blush: 0.035, rough: 0.8, toneVar: 0.13,
  palette: [[[0.42, 0.44, 0.455], 0.45], [[0.385, 0.415, 0.44], 0.2], [[0.45, 0.455, 0.455], 0.2], [[0.405, 0.435, 0.435], 0.1], [[0.46, 0.45, 0.43], 0.05]],
};
const PAVER = {
  seed: 9, tile: 2.7432, rows: 12, units: 36, choices: [2, 3, 4], joint: 0.004, jointColor: [0.10, 0.095, 0.085], jointDepth: 0.006,
  bevel: 0.006, bevelDepth: 0.003, round: 2, cleft: 0.0006, lip: 0.0015, cloud: 0.13, grain: 0.08, speck: 0.07, blush: 0, rough: 0.92, toneVar: 0.12,
  palette: [[[0.52, 0.505, 0.475], 0.34], [[0.445, 0.435, 0.415], 0.34], [[0.35, 0.345, 0.34], 0.2], [[0.49, 0.45, 0.395], 0.12]],
};

function limestoneTex(ctx, jointed) {
  return shared('limestone' + (jointed ? 'J' : ''), () => timed(jointed ? 'paving_pale' : 'coping', () => {
    const n = q(ctx, 512), W = 1.22, half = n / 2;
    const { A, B, W: Wn, S, M } = bk(ctx);
    const alb = new Uint8Array(n * n * 4), hgt = new Float32Array(n * n), rgh = new Float32Array(n * n);
    const tones = [1.0, 0.965, 0.975, 1.02];
    for (let y = 0; y < n; y++) {
      for (let x = 0; x < n; x++) {
        const i = y * n + x, pc = (y < half ? 0 : 2) + (x < half ? 0 : 1);
        const ox = jointed ? pc * 211 : 0;
        const a = A[((y * 2 + ox) & M) * S + ((x * 2 + ox * 3) & M)], b = B[((y + ox) & M) * S + ((x + 91) & M)], wn = Wn[(i * 3) & (S * S - 1)];
        const e = jointed ? Math.min(x % half, half - 1 - (x % half), y % half, half - 1 - (y % half)) + 0.5 : 99;
        const m = smooth(0.4, 1.8, e), pit = wn > 0.93 && b < 0 ? 0.86 : 1;
        const l = (jointed ? tones[pc] : 1) * (1 + 0.035 * a + 0.03 * b + 0.02 * wn) * pit * (0.5 + 0.5 * m);
        put(alb, i * 4, l, l * (1 - 0.012 * a), l * (1 - 0.035 * a));
        hgt[i] = m * (0.0003 * b - (pit < 1 ? 0.0006 : 0)) - (1 - m) * 0.002;
        rgh[i] = 0.92 + 0.08 * b + (1 - m) * 0.1;
      }
    }
    return { map: texture(ctx, alb, n, n, W, W, true), nr: texture(ctx, packNR(hgt, n, n, W, W, rgh), n, n, W, W) };
  }));
}

function groundTex(ctx, key, o) {      // concrete, asphalt, soil, pool plaster: mottled granular grounds
  return shared(key, () => timed(key, () => {
    const n = q(ctx, o.size || 512), W = o.tile;
    const { A, B, W: Wn, S, M } = bk(ctx);
    const alb = new Uint8Array(n * n * 4), hgt = new Float32Array(n * n);
    const k = S / n;
    for (let y = 0; y < n; y++) {
      for (let x = 0; x < n; x++) {
        const i = y * n + x, a = A[((y * k + o.oy) & M) * S + ((x * k + o.ox) & M)], b = B[((y + o.ox) & M) * S + ((x + o.oy) & M)], wn = Wn[(i * 5 + o.ox) & (S * S - 1)];
        const chip = o.chips && wn > 1 - o.chips ? 1 : 0;
        const l = (1 + o.cloud * a + o.grain * b + o.speck * wn) * (chip ? o.chipTone : 1);
        put(alb, i * 4, l * (1 + o.warm * a), l, l * (1 - o.warm * a));
        hgt[i] = o.relief * (b + 0.5 * wn) + (chip ? o.relief * 1.5 : 0);
      }
    }
    return { map: texture(ctx, alb, n, n, W, W, true), nr: texture(ctx, packNR(hgt, n, n, W, W, 1), n, n, W, W) };
  }));
}

// ---------------------------------------------------------------------------------------------- pool
function poolTileTex(ctx) {
  return shared('pooltile', () => timed('pool_tile', () => {
    const n = q(ctx, 512), W = 4 * MODULES.poolTile, t = n / 4;
    const { A, B, S, M } = bk(ctx);
    const rnd = prng(88), tiles = [];
    for (let k = 0; k < 16; k++) tiles.push({ ox: (rnd() * S) | 0, oy: (rnd() * S) | 0, l: 0.8 + rnd() * 0.45, hue: rnd() });
    const alb = new Uint8Array(n * n * 4), hgt = new Float32Array(n * n), rgh = new Float32Array(n * n);
    const jw = 0.003 * n / W * 0.5;
    for (let y = 0; y < n; y++) {
      for (let x = 0; x < n; x++) {
        const i = y * n + x, tl = tiles[((y / t) | 0) * 4 + ((x / t) | 0)];
        const e = Math.min(x % t, t - 1 - (x % t), y % t, t - 1 - (y % t)) + 0.5;
        const m = smooth(jw - 0.6, jw + 0.8, e);
        const a = A[((y * 6 + tl.oy) & M) * S + ((x * 6 + tl.ox) & M)], b = B[((y * 2 + tl.ox) & M) * S + ((x * 2 + tl.oy) & M)];
        const f = smooth(-0.35, 0.55, a + 0.4 * b) ;                // marbled glaze: deep cobalt -> lighter blue
        const l = tl.l;
        const r = (0.018 + 0.085 * f) * l, g = (0.07 + 0.2 * f + 0.03 * tl.hue) * l, bl = (0.23 + 0.33 * f) * l;
        put(alb, i * 4, 0.5 + (r - 0.5) * m, 0.54 + (g - 0.54) * m, 0.55 + (bl - 0.55) * m);
        hgt[i] = m * (0.0008 * smooth(jw, jw + 6, e)) - (1 - m) * 0.0012;
        rgh[i] = 0.16 + (1 - m) * 0.7 + 0.04 * b;
      }
    }
    return { map: texture(ctx, alb, n, n, W, W, true), nr: texture(ctx, packNR(hgt, n, n, W, W, rgh), n, n, W, W) };
  }));
}

// ---------------------------------------------------------------------------------------------- wood
const CEDAR = [[[0.40, 0.17, 0.068], 0.4], [[0.33, 0.125, 0.05], 0.3], [[0.45, 0.215, 0.095], 0.14], [[0.26, 0.10, 0.042], 0.16]];

function fenceTex(ctx) {
  return shared('fence', () => timed('fence_wood', () => {
    const w = q(ctx, 1024), h = q(ctx, 512), nb = 16, bw = w / nb, W = nb * MODULES.fenceBoard, H = W;
    const { A, B, W: Wn, S, M } = bk(ctx);
    const rnd = prng(606), boards = [];
    for (let k = 0; k < nb; k++) {
      boards.push({ col: pick(CEDAR, rnd()), l: 0.86 + rnd() * 0.28, ox: (rnd() * S) | 0, oy: (rnd() * S) | 0, ring: 5 + rnd() * 7, ph: rnd() * 6.28,
        knots: [0, 1].filter(() => rnd() < 0.3).map(() => ({ x: bw * (0.25 + rnd() * 0.5), y: rnd() * h, r: 3.5 + rnd() * 4.5 })) });
    }
    const alb = new Uint8Array(w * h * 4), hgt = new Float32Array(w * h), rgh = new Float32Array(w * h);
    const ky = S / h;
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const i = y * w + x, k = (x / bw) | 0, bd = boards[k], lx = x - k * bw;
        const e = Math.min(lx, bw - 1 - lx) + 0.5;
        const m = smooth(0.6, 1.7, e);
        // long streaks along the board, growth rings bent by the low noise, knots
        const st = B[((y * ky * 0.5 + bd.oy) & M) * S + ((x * 4 + bd.ox) & M)], lo = A[((y * ky * 0.5 + bd.oy) & M) * S + ((x * 2 + bd.ox) & M)];
        let ring = Math.sin(bd.ph + (lx / bd.ring) * 6.283 * 0.6 + lo * 11 + st * 1.5);
        ring = ring > 0 ? ring * ring : ring * 0.5;                // narrow dark latewood lines
        let kn = 0;
        for (const kt of bd.knots) {
          let dy = Math.abs(y - kt.y); dy = Math.min(dy, h - dy);
          const d = Math.hypot(lx - kt.x, dy * 0.55 * (w / h) * (H / W)) / kt.r;
          if (d < 3) { kn = Math.max(kn, 1 - smooth(0.6, 1.25, d)); ring = ring + (Math.sin(d * 5) - ring) * (1 - smooth(1, 3, d)) * 0.8; }
        }
        const l = bd.l * (1 + 0.2 * st + 0.1 * lo - 0.13 * ring + 0.06 * Wn[(i * 3) & (S * S - 1)]) * (1 - 0.6 * kn) * (0.08 + 0.92 * m) * (0.86 + 0.14 * smooth(0, 4, e));
        const c = bd.col;
        put(alb, i * 4, c[0] * l, c[1] * l * (1 + 0.05 * lo), c[2] * l * (1 + 0.1 * lo));
        const cup = 1 - Math.pow(Math.abs(lx / bw - 0.5) * 2, 6);
        hgt[i] = m * (0.0008 * cup + 0.0005 * st - 0.0004 * ring) - (1 - m) * 0.012;
        rgh[i] = 0.92 + 0.08 * st;
      }
    }
    return { map: texture(ctx, alb, w, h, W, H, true), nr: texture(ctx, packNR(hgt, w, h, W, H, rgh), w, h, W, H) };
  }));
}

function mahoganyTex(ctx) {
  return shared('mahogany', () => timed('door_wood', () => {
    const w = q(ctx, 256), h = q(ctx, 512), W = 0.45, H = 0.9;
    const { A, B, W: Wn, S, M } = bk(ctx);
    const alb = new Uint8Array(w * h * 4), hgt = new Float32Array(w * h), rgh = new Float32Array(w * h);
    const k = S / h;
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const i = y * w + x;
        const st = B[((y * k * 0.25 + 60) & M) * S + ((x * 8) & M)], lo = A[((y * k * 0.5) & M) * S + ((x * 4 + 500) & M)], pore = Wn[((y >> 3) * 977 + x * 131) & (S * S - 1)];
        const l = 1 + 0.2 * st + 0.16 * lo - (pore > 0.72 ? 0.18 : 0);
        put(alb, i * 4, l, l * (1 - 0.1 * lo), l * (1 - 0.18 * lo));
        hgt[i] = 0.00012 * st - (pore > 0.72 ? 0.00012 : 0);
        rgh[i] = 0.9 + 0.1 * st + (pore > 0.72 ? 0.12 : 0);
      }
    }
    return { map: texture(ctx, alb, w, h, W, H, true), nr: texture(ctx, packNR(hgt, w, h, W, H, rgh), w, h, W, H) };
  }));
}

// ---------------------------------------------------------------------------------------------- planting grounds
const css = (r, g, b) => `rgb(${srgb8(r)},${srgb8(g)},${srgb8(b)})`;

function strokes(g, n, N, rnd, draw) {
  for (let i = 0; i < N; i++) {
    const x = rnd() * n, y = rnd() * n, s = draw(i);
    for (let oy = -n; oy <= n; oy += n) {
      if (y + oy < -s.l || y + oy > n + s.l) continue;
      for (let ox = -n; ox <= n; ox += n) {
        if (x + ox < -s.l || x + ox > n + s.l) continue;
        g.beginPath(); g.moveTo(x + ox, y + oy);
        if (s.bend) g.quadraticCurveTo(x + ox + s.dx * 0.5 + s.bend, y + oy + s.dy * 0.5, x + ox + s.dx, y + oy + s.dy);
        else g.lineTo(x + ox + s.dx, y + oy + s.dy);
        g.stroke();
      }
    }
  }
}

function canvasNR(ctx, g, n, W, relief, rough) {
  const px = g.getImageData(0, 0, n, n).data, hgt = new Float32Array(n * n);
  for (let i = 0; i < n * n; i++) hgt[i] = (px[i * 4] * 0.3 + px[i * 4 + 1] * 0.6 + px[i * 4 + 2] * 0.1) / 255 * relief;
  return texture(ctx, packNR(hgt, n, n, W, W, rough), n, n, W, W);
}

function lawnTex(ctx) {
  return shared('lawn', () => timed('lawn', () => {
    const n = q(ctx, 1024), W = 3.2, N = n - 1;
    const { A, B, S, M } = bk(ctx);
    // blades = short streaks (3 mm x 4 - 6 cm) lying along four directions, bent by a slow warp; a patch of
    // lawn leans mostly one way
    const F = new Float32Array(n * n);
    addNoise(F, n, n, n / 2, n / 16, 1.0, 91); addNoise(F, n, n, Math.round(n / 3), Math.round(n / 26), 0.75, 92);
    addNoise(F, n, n, n / 4, n / 8, 0.4, 93);
    const WX = new Float32Array(n * n), WY = new Float32Array(n * n), wp = n / 26;      // a slow bend of the blades
    addNoise(WX, n, n, 5, 5, wp, 94); addNoise(WX, n, n, 11, 11, wp * 0.4, 95);
    addNoise(WY, n, n, 5, 5, wp, 96); addNoise(WY, n, n, 11, 11, wp * 0.4, 97);
    const alb = new Uint8Array(n * n * 4), hgt = new Float32Array(n * n), k = S / n;
    for (let y = 0; y < n; y++) {
      for (let x = 0; x < n; x++) {
        const i = y * n + x;
        const a = A[((y * k) & M) * S + ((x * k) & M)], a2 = A[((y * k + 517) & M) * S + ((x * k + 233) & M)], b = B[((y * k) & M) * S + ((x * k) & M)];
        const xw = (x + WX[i]) & N, yw = (y + WY[i]) & N;
        const w1 = 0.75 + 0.55 * a, w2 = 0.6 - 0.45 * a, w3 = 0.62 + 0.5 * a2, w4 = 0.62 - 0.5 * a2;
        const xy = (xw + yw) & N, yx = (xw - yw) & N;
        const v = Math.max(F[yw * n + xw] * w1, F[xw * n + yw] * w2, F[xy * n + yx] * w3, F[yx * n + xy] * w4);
        const t = smooth(-0.5, 0.9, v + 0.3 * b);
        const dry = F[((y + 371) & N) * n + ((x + 97) & N)] > 1.12 ? 0.5 : 0;       // a few straw-coloured blades
        const tone = 1 + 0.16 * a2 + 0.1 * b;
        let r = (0.050 + 0.165 * t) * tone, g = (0.090 + 0.235 * t) * tone, bl = (0.034 + 0.062 * t) * tone;
        r += (0.36 * t - r) * dry; g += (0.33 * t - g) * dry; bl += (0.14 * t - bl) * dry;
        put(alb, i * 4, r, g, bl);
        hgt[i] = 0.02 * t;
      }
    }
    return { map: texture(ctx, alb, n, n, W, W, true), nr: texture(ctx, packNR(hgt, n, n, W, W, 1), n, n, W, W) };
  }));
}

function mulchTex(ctx) {
  return shared('mulch', () => timed('mulch', () => {
    const n = q(ctx, 512), W = 1.0;
    const { c, g } = tileCanvas(n, n);
    g.fillStyle = css(0.09, 0.045, 0.024); g.fillRect(0, 0, n, n);
    const rnd = prng(31337);
    g.lineCap = 'butt';
    const N = n * 7;
    strokes(g, n, N, rnd, (i) => {
      const a = rnd() * 6.283, l = n * (0.02 + rnd() * 0.075), top = i / N, v = (0.45 + 0.75 * top) * (0.75 + rnd() * 0.5);
      const u = rnd();
      const col = u < 0.5 ? [0.56, 0.235, 0.115] : u < 0.75 ? [0.42, 0.165, 0.08] : u < 0.92 ? [0.70, 0.35, 0.18] : [0.27, 0.135, 0.08];
      g.strokeStyle = css(col[0] * v, col[1] * v, col[2] * v);
      g.lineWidth = n / 512 * (1.5 + rnd() * 5.5);
      return { l, dx: Math.sin(a) * l, dy: Math.cos(a) * l, bend: 0 };
    });
    return { map: canvasTexture(ctx, c, W, W), nr: canvasNR(ctx, g, n, W, 0.07, 1) };
  }));
}

// ---------------------------------------------------------------------------------------------- registry
export function register(lib) {
  // walls
  lib.add('siding_lap', (ctx) => surface(ctx, { ...sidingTex(ctx), color: C.white, roughness: 0.62,
    detail: { kind: 'grit', size: 0.19, albedo: 0.012, normal: 0.03, rough: 0.03 }, macro: { amount: 0.025 } }));
  lib.add('chimney_white', (ctx) => surface(ctx, { ...sidingTex(ctx), color: C.white, roughness: 0.62,
    detail: { kind: 'grit', size: 0.19, albedo: 0.012, normal: 0.03, rough: 0.03 }, macro: { amount: 0.025 } }));
  lib.add('siding_bb', (ctx) => paint(ctx, C.white, 0.62));
  lib.add('trim_white', (ctx) => paint(ctx, C.trim, 0.5));
  lib.add('soffit_white', (ctx) => paint(ctx, C.soffit, 0.6, grooveTex(ctx, 'soffit', false, MODULES.soffit, 0.005, 0.003)));
  lib.add('door_garage', (ctx) => paint(ctx, C.trim, 0.45, grooveTex(ctx, 'garage', true, MODULES.garagePlank, 0.007, 0.003)));
  lib.add('door_navy', (ctx) => paint(ctx, C.navy, 0.34));
  lib.add('door_wood', (ctx) => surface(ctx, { ...mahoganyTex(ctx), color: C.mahogany, roughness: 0.36,
    detail: { kind: 'fibre', size: 0.16, albedo: 0.12, normal: 0.05, rough: 0.05 } }));

  // roofs
  lib.add('roof_shingle', (ctx) => surface(ctx, { ...shingleTex(ctx), color: C.shingle, roughness: 0.96,
    detail: { kind: 'grit', size: 0.31, albedo: 0.4, normal: 0.55 }, macro: { s1: 6.3, s2: 23, amount: 0.12 } }));
  lib.add('roof_seam', (ctx) => surface(ctx, { ...seamTex(ctx), color: C.seam, roughness: 0.46, metalness: 0.0, normalScale: 1,
    detail: { kind: 'grit', size: 0.4, albedo: 0.02, normal: 0.012, rough: 0.03 }, macro: { s1: 5.1, s2: 17, amount: 0.06 } }));
  lib.add('roof_flat', (ctx) => surface(ctx, { ...flatRoofTex(ctx), color: C.flat, roughness: 0.95,
    detail: { kind: 'grit', size: 0.29, albedo: 0.36, normal: 0.5 }, macro: { s1: 4.7, s2: 13, amount: 0.12 } }));
  lib.add('metal_awning', (ctx) => paint(ctx, C.awning, 0.42));
  lib.add('gutter_dark', (ctx) => paint(ctx, C.gutter, 0.36));
  lib.add('pergola_metal', (ctx) => paint(ctx, C.pergola, 0.55));
  lib.add('chimney_cap', (ctx) => paint(ctx, C.cap, 0.33, { metalness: 0.5 }));

  // stone, paving
  lib.add('stone_veneer', (ctx) => surface(ctx, { ...stoneTex(ctx), color: C.stone, roughness: 0.9,
    detail: { kind: 'grit', size: 0.23, albedo: 0.3, normal: 0.5 }, macro: { s1: 3.1, s2: 11, amount: 0.07 } }));
  lib.add('bluestone', (ctx) => surface(ctx, { ...coursedTex(ctx, 'bluestone', BLUESTONE), color: C.bluestone, roughness: 1.0,
    detail: { kind: 'grit', size: 0.27, albedo: 0.24, normal: 0.3, rough: 0.05 }, macro: { s1: 7.9, s2: 29, amount: 0.07, tint: [1.05, 1.0, 0.94], tintAmount: 0.35 } }));
  lib.add('paver_drive', (ctx) => surface(ctx, { ...coursedTex(ctx, 'paver_drive', PAVER), color: C.paver, roughness: 1.0,
    detail: { kind: 'grit', size: 0.21, albedo: 0.32, normal: 0.45 }, macro: { s1: 6.1, s2: 21, amount: 0.08 } }));
  lib.add('coping', (ctx) => surface(ctx, { ...limestoneTex(ctx, false), color: C.limestone, roughness: 0.78,
    detail: { kind: 'grit', size: 0.24, albedo: 0.1, normal: 0.14, rough: 0.04 }, macro: { s1: 2.9, s2: 9.1, amount: 0.035 } }));
  lib.add('paving_pale', (ctx) => surface(ctx, { ...limestoneTex(ctx, true), color: C.limestone, roughness: 0.78,
    detail: { kind: 'grit', size: 0.24, albedo: 0.1, normal: 0.14, rough: 0.04 }, macro: { s1: 4.9, s2: 17, amount: 0.04 } }));
  lib.add('concrete', (ctx) => surface(ctx, { ...groundTex(ctx, 'concrete', { tile: 2.0, ox: 133, oy: 811, cloud: 0.09, grain: 0.06, speck: 0.05, warm: 0.02, relief: 0.0004 }),
    color: C.concrete, roughness: 0.92, detail: { kind: 'grit', size: 0.23, albedo: 0.26, normal: 0.4 }, macro: { s1: 5.3, s2: 19, amount: 0.09 } }));
  lib.add('asphalt', (ctx) => surface(ctx, { ...groundTex(ctx, 'asphalt', { tile: 1.5, ox: 517, oy: 29, cloud: 0.1, grain: 0.14, speck: 0.2, warm: 0, relief: 0.0012, chips: 0.06, chipTone: 2.3 }),
    color: C.asphalt, roughness: 0.93, detail: { kind: 'grit', size: 0.17, albedo: 0.3, normal: 0.45 }, macro: { s1: 6.7, s2: 23, amount: 0.12 } }));

  // pool
  lib.add('pool_tile', (ctx) => surface(ctx, { ...poolTileTex(ctx), color: C.poolTile, roughness: 1.0 }));
  lib.add('pool_plaster', (ctx) => surface(ctx, { ...groundTex(ctx, 'pool_plaster', { size: 256, tile: 1.0, ox: 71, oy: 303, cloud: 0.05, grain: 0.03, speck: 0.02, warm: 0, relief: 0.0002 }),
    color: C.plaster, roughness: 0.6, macro: { s1: 3.3, s2: 9.7, amount: 0.05 } }));

  // timber, grounds
  lib.add('fence_wood', (ctx) => surface(ctx, { ...fenceTex(ctx), color: C.fence, roughness: 0.86,
    detail: { kind: 'fibre', size: 0.17, albedo: 0.34, normal: 0.4 }, macro: { s1: 5.9, s2: 19, amount: 0.1, tint: [0.92, 1.0, 1.1], tintAmount: 0.3 } }));
  // the fence's posts, rails and caps: the same timber under a darker stain, no board joints
  lib.add('fence_frame', (ctx) => surface(ctx, { color: C.fenceFrame, roughness: 0.85,
    detail: { kind: 'fibre', size: 0.17, albedo: 0.4, normal: 0.4 }, macro: { s1: 1.9, s2: 7.3, amount: 0.22 } }));
  lib.add('lawn', (ctx) => surface(ctx, { ...lawnTex(ctx), color: C.lawn, roughness: 0.9, normalScale: 0.7,
    detail: { kind: 'blades', size: 0.45, albedo: 0.3, normal: 0.35 }, macro: { s1: 8.3, s2: 37, amount: 0.22, tint: [1.22, 1.06, 0.8], tintAmount: 0.5 } }));
  lib.add('mulch', (ctx) => surface(ctx, { ...mulchTex(ctx), color: C.mulch, roughness: 0.95,
    detail: { kind: 'fibre', size: 0.13, albedo: 0.2, normal: 0.3 }, macro: { s1: 2.7, s2: 8.9, amount: 0.12 } }));
  lib.add('soil', (ctx) => surface(ctx, { ...groundTex(ctx, 'soil', { tile: 1.5, ox: 901, oy: 222, cloud: 0.22, grain: 0.2, speck: 0.14, warm: 0.04, relief: 0.004, chips: 0.02, chipTone: 1.5 }),
    color: C.soil, roughness: 1.0, detail: { kind: 'grit', size: 0.21, albedo: 0.3, normal: 0.5 }, macro: { s1: 3.7, s2: 12, amount: 0.15 } }));
}
