// Look module "plants": bark and foliage of model/plants.py, registered by name (see ../materials.js for the contract).
//
// Everything is drawn at load, seeded and deterministic - no image files.
//   bark, bark_young, bark_redwood   tiling albedo + normal maps (UV metres); the oak's bark gets lichen on the faces
//                                    that look up and a large-scale variation, so it does not repeat at 30 m.
//   leaf_*                           a 2 x 2 atlas of leaf clusters / twig sprays per palette, alpha-tested and
//                                    double-sided.  The cards carry a tint class in floor(u) and a shade class in
//                                    floor(v); their normals are bent outward from the crown (model/plants.py), so the
//                                    shader must NOT flip them on back faces.  Light coming through the leaves from
//                                    behind is added (the glow of backlit autumn trees); with MSAA the cut-out edge is
//                                    alpha-to-coverage: crisp close up, a soft haze of twigs far away, no shimmer.
//                                    Shadows: three's depth pass reads material.map + alphaTest, so they are cut out.
//   shrub_core, stake_wood, plant_tie
// Wind: lib.onTick drives a gentle flutter of the cards (their tips move, their roots stay); time 0 = still.

export const BARK_TILE = 1.2;      // m (model/plants.py BARK_TILE)
export const YOUNG_TILE = 0.3;
export const CORE_TILE = 0.5;
const ATLAS = [2, 2];

const shared = { time: { value: 0 } };

// ---- small tools ------------------------------------------------------------------------------------------------------
function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const lerp = (a, b, t) => a + (b - a) * t;
const mix3 = (a, b, t) => [lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t)];
const css = (c, k = 1) => `rgb(${Math.round(Math.min(255, c[0] * k))},${Math.round(Math.min(255, c[1] * k))},${Math.round(Math.min(255, c[2] * k))})`;
const sstep = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
const pick = (R, arr) => arr[Math.min(arr.length - 1, Math.floor(R() * arr.length))];

function makeCanvas(w, h) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  return c;
}

// ---- bark ---------------------------------------------------------------------------------------------------------------
// tileable value noise on a px x py lattice
function lattice(R, px, py) {
  const v = new Float32Array(px * py);
  for (let i = 0; i < v.length; i++) v[i] = R();
  return (X, Y) => {
    const x = X * px, y = Y * py, x0 = Math.floor(x), y0 = Math.floor(y);
    let fx = x - x0, fy = y - y0;
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy);
    const i0 = ((x0 % px) + px) % px, i1 = (i0 + 1) % px, j0 = ((y0 % py) + py) % py, j1 = (j0 + 1) % py;
    return lerp(lerp(v[j0 * px + i0], v[j0 * px + i1], fx), lerp(v[j1 * px + i0], v[j1 * px + i1], fx), fy);
  };
}

// A height field of plates between furrows: cell noise whose cells are stretched along the stem and pushed about by
// smooth noise (the ridges wander, merge and split), broken across by a second layer of cracks, with a fibrous grain.
// Colour and normal map follow from the height.  Tileable.
function barkMaps(ctx, o) {
  const { THREE } = ctx;
  const N = ctx.quality === 'low' ? o.size / 2 : o.size;
  const R = rng(o.seed);
  const layer = (gu, gv) => {
    const px = new Float32Array(gu * gv), py = new Float32Array(gu * gv), pr = new Float32Array(gu * gv);
    for (let i = 0; i < gu * gv; i++) { px[i] = 0.12 + 0.76 * R(); py[i] = 0.08 + 0.84 * R(); pr[i] = R(); }
    return { gu, gv, px, py, pr };
  };
  const A = layer(o.cells[0], o.cells[1]), B = layer(o.cells2[0], o.cells2[1]);
  const w1 = lattice(R, 3, 7), w2 = lattice(R, 7, 17), w3 = lattice(R, 4, 5);
  const e1 = lattice(R, 48, 20), g1 = lattice(R, 40, 12), g2 = lattice(R, 96, 30), g3 = lattice(R, 200, 70), g4 = lattice(R, 400, 180);
  const l1 = lattice(R, 3, 3), l2 = lattice(R, 9, 7);
  const H = new Float32Array(N * N), C = new Float32Array(N * N), L = new Float32Array(N * N);
  const cell = (Lr, u, v, out) => {
    const cu = Math.floor(u), cv = Math.floor(v);
    let d1 = 1e9, d2 = 1e9, id = 0;
    for (let dj = -1; dj <= 1; dj++) {
      const j = ((cv + dj) % Lr.gv + Lr.gv) % Lr.gv;
      for (let di = -1; di <= 1; di++) {
        const i = ((cu + di) % Lr.gu + Lr.gu) % Lr.gu, k = j * Lr.gu + i;
        const dx = cu + di + Lr.px[k] - u, dy = cv + dj + Lr.py[k] - v;
        const d = dx * dx + dy * dy;
        if (d < d1) { d2 = d1; d1 = d; id = k; } else if (d < d2) d2 = d;
      }
    }
    out[0] = Math.sqrt(d2) - Math.sqrt(d1);
    out[1] = Lr.pr[id];
  };
  const tmp = [0, 0];
  const s = N / o.size;                                   // the lattices are laid out for the full size
  for (let y = 0; y < N; y++) {
    const Y = y / N;
    for (let x = 0; x < N; x++) {
      const X = x / N, k = y * N + x;
      const wu = o.warp * ((w1(X, Y) - 0.5) * 2 + (w2(X, Y) - 0.5) * 0.8);
      const wv = o.warp * 0.4 * (w3(X, Y) - 0.5) * 2;
      cell(A, X * A.gu + wu, Y * A.gv + wv, tmp);
      const dA = tmp[0] + o.ragged * (e1(X, Y) - 0.5), rA = tmp[1];
      cell(B, X * B.gu + wu * B.gu / A.gu, Y * B.gv + wv * B.gv / A.gv, tmp);
      const dB = tmp[0], rB = tmp[1];
      let h = Math.pow(sstep(0.02, o.edge, dA), o.round) * (0.7 + 0.3 * rA);
      h *= 1 - o.crack * (1 - sstep(0.0, 0.16, dB)) * sstep(0.2, 0.55, h) * (rB > 0.3 ? 1 : 0.35);
      const grain = 0.4 * g1(X, Y) + 0.3 * g2(X, Y) + 0.2 * g3(X, Y) + (s >= 1 ? 0.1 * g4(X, Y) : 0.05);
      h += o.fib * (grain - 0.5) * 2 * (0.35 + 0.65 * h);
      H[k] = h; C[k] = 0.6 * rA + 0.4 * rB; L[k] = 0.6 * l1(X, Y) + 0.4 * l2(X, Y) + 0.5 * (grain - 0.5);
    }
  }
  const col = new Uint8Array(N * N * 4), nrm = new Uint8Array(N * N * 4);
  const sl = o.depth / (2 * o.tile[0] / N);
  for (let y = 0; y < N; y++) {
    const yu = ((y - 1 + N) % N) * N, yd = ((y + 1) % N) * N;
    for (let x = 0; x < N; x++) {
      const k = y * N + x, h = Math.min(1, Math.max(0, H[k]));
      let c = mix3(o.furrow, o.side, sstep(0.0, 0.4, h));
      c = mix3(c, o.top, sstep(0.35, 0.9, h));
      const b = (0.8 + 0.4 * C[k]) * (0.82 + 0.36 * L[k]);
      const li = sstep(0.5, 0.72, L[k] + 0.2 * C[k]) * sstep(0.45, 0.85, h) * o.lichen;
      c = mix3(c, o.lichenCol, li);
      col[k * 4] = Math.min(255, c[0] * b); col[k * 4 + 1] = Math.min(255, c[1] * b); col[k * 4 + 2] = Math.min(255, c[2] * b); col[k * 4 + 3] = 255;
      const dx = (H[y * N + (x + 1) % N] - H[y * N + (x - 1 + N) % N]) * sl, dy = (H[yd + x] - H[yu + x]) * sl * o.tile[0] / o.tile[1];
      const il = 1 / Math.sqrt(dx * dx + dy * dy + 1);
      nrm[k * 4] = (-dx * il * 0.5 + 0.5) * 255; nrm[k * 4 + 1] = (-dy * il * 0.5 + 0.5) * 255; nrm[k * 4 + 2] = (il * 0.5 + 0.5) * 255; nrm[k * 4 + 3] = 255;
    }
  }
  const tex = (data, srgb) => {
    const t = new THREE.DataTexture(data, N, N, THREE.RGBAFormat);
    if (srgb) t.colorSpace = THREE.SRGBColorSpace;
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.magFilter = THREE.LinearFilter; t.minFilter = THREE.LinearMipmapLinearFilter; t.generateMipmaps = true;
    t.anisotropy = Math.min(8, ctx.anisotropy || 1);
    t.repeat.set(1 / o.tile[0], 1 / o.tile[1]);
    t.needsUpdate = true;
    return t;
  };
  return { map: tex(col, true), normalMap: tex(nrm, false) };
}

const BARKS = {
  // the oak: grey ridges about 6 cm wide and a hand long between deep furrows, pale lichen
  oak: { size: 1024, seed: 5, cells: [20, 5], cells2: [9, 24], warp: 0.85, ragged: 0.22, edge: 0.4, round: 0.75, crack: 0.6, fib: 0.2, depth: 0.014,
    furrow: [30, 26, 22], side: [88, 79, 70], top: [142, 133, 121], lichen: 0.5, lichenCol: [166, 166, 148], tile: [BARK_TILE, BARK_TILE],
    rough: 0.96, lichenUp: [0.56, 0.56, 0.5, 0.42] },
  // redwood: long stringy ridges, red-brown
  redwood: { size: 512, seed: 9, cells: [18, 2], cells2: [8, 9], warp: 0.5, ragged: 0.2, edge: 0.45, round: 0.8, crack: 0.3, fib: 0.3, depth: 0.02,
    furrow: [44, 24, 18], side: [112, 62, 42], top: [150, 92, 64], lichen: 0.0, lichenCol: [150, 92, 64], tile: [BARK_TILE, BARK_TILE * 1.6],
    rough: 0.97, lichenUp: [0.4, 0.3, 0.25, 0.0] },
};

function barkMaterial(ctx, o) {
  const { THREE } = ctx;
  const maps = barkMaps(ctx, o);
  const m = new THREE.MeshStandardMaterial({ map: maps.map, normalMap: maps.normalMap, roughness: o.rough, metalness: 0 });
  m.normalScale = new THREE.Vector2(1, 1);
  m.envMapIntensity = 0.85;
  const lichen = new THREE.Vector4(...o.lichenUp);
  m.onBeforeCompile = (sh) => {
    sh.uniforms.uPlLichen = { value: lichen };
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', '#include <common>\nuniform vec4 uPlLichen;')
      .replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
      {
        vec3 plUp = inverseTransformDirection( nonPerturbedNormal, viewMatrix );
        float plLow = texture2D( map, vMapUv * 0.131 + vec2( 0.37, 0.11 ) ).g;
        float plLow2 = texture2D( map, vMapUv * 0.047 + vec2( 0.13, 0.71 ) ).r;
        diffuseColor.rgb *= 0.8 + 0.75 * plLow2;
        float plM = smoothstep( 0.1, 0.9, plUp.y + ( plLow - 0.25 ) * 1.6 ) * uPlLichen.a;
        float plLum = dot( diffuseColor.rgb, vec3( 0.3, 0.6, 0.1 ) );
        diffuseColor.rgb = mix( diffuseColor.rgb, uPlLichen.rgb * ( 0.3 + 2.4 * plLum ), plM );
      }`);
  };
  m.customProgramCacheKey = () => 'plants-bark';
  return m;
}

// young bark: smooth, grey-brown, with lenticels; drawn in 2-D
function youngBark(ctx) {
  const { THREE } = ctx;
  const N = ctx.quality === 'low' ? 128 : 256, R = rng(31);
  const cv = makeCanvas(N, N), c = cv.getContext('2d');
  c.fillStyle = 'rgb(104,86,70)'; c.fillRect(0, 0, N, N);
  for (let i = 0; i < 260; i++) {                       // soft vertical streaks and blotches
    const x = R() * N, y = R() * N, w = 2 + R() * 6, h = 20 + R() * 90, k = R();
    c.fillStyle = k < 0.5 ? `rgba(60,46,36,${0.05 + R() * 0.08})` : `rgba(150,132,112,${0.04 + R() * 0.07})`;
    for (const ox of [-N, 0, N]) for (const oy of [-N, 0, N]) c.fillRect(x + ox, y + oy, w, h);
  }
  for (let i = 0; i < 170; i++) {                       // lenticels: short pale dashes across the stem
    const x = R() * N, y = R() * N, w = 4 + R() * 12;
    c.fillStyle = `rgba(176,158,134,${0.25 + R() * 0.35})`;
    for (const ox of [-N, 0, N]) c.fillRect(x + ox, y, w, 1 + R() * 1.4);
  }
  const t = new THREE.CanvasTexture(cv);
  t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = Math.min(4, ctx.anisotropy || 1);
  t.repeat.set(1 / YOUNG_TILE, 1 / YOUNG_TILE);
  return new THREE.MeshStandardMaterial({ map: t, roughness: 0.82, metalness: 0 });
}

function shrubCore(ctx) {
  const { THREE } = ctx;
  const N = 128, R = rng(77);
  const cv = makeCanvas(N, N), c = cv.getContext('2d');
  c.fillStyle = 'rgb(16,24,12)'; c.fillRect(0, 0, N, N);
  for (let i = 0; i < 500; i++) {
    const x = R() * N, y = R() * N, k = R();
    c.fillStyle = k < 0.6 ? `rgba(8,12,6,${0.3 + R() * 0.4})` : `rgba(44,62,28,${0.25 + R() * 0.35})`;
    for (const ox of [-N, 0, N]) for (const oy of [-N, 0, N]) { c.beginPath(); c.ellipse(x + ox, y + oy, 2 + R() * 4, 1 + R() * 2.5, R() * 3.14, 0, 6.3); c.fill(); }
  }
  const t = new THREE.CanvasTexture(cv);
  t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(1 / CORE_TILE, 1 / CORE_TILE);
  return new THREE.MeshStandardMaterial({ map: t, roughness: 1, metalness: 0 });
}

// ---- drawing leaves -------------------------------------------------------------------------------------------------------
// All drawing happens in a cell's own unit square: x right, y DOWN, 0..1; a card's root is the bottom centre (0.5, 1).
function leafShape(c, len, wid, belly, tipw) {
  c.beginPath();
  c.moveTo(0, 0);
  c.bezierCurveTo(len * belly, -wid, len * 0.8, -wid * tipw, len, 0);
  c.bezierCurveTo(len * 0.8, wid * tipw, len * belly, wid, 0, 0);
}

// one leaf from its base at (x, y) along `ang`; o: { belly, tipw, rib, gloss, lobes }
function leaf(c, R, x, y, ang, len, wid, col, o = {}) {
  const belly = o.belly ?? 0.3, tipw = o.tipw ?? 0.45;
  c.save();
  c.translate(x, y); c.rotate(ang);
  leafShape(c, len, wid, belly, tipw);
  c.fillStyle = css(col); c.fill();
  if (o.lobes) {                                                      // a wavy, lobed outline (oak)
    for (let i = 0; i < o.lobes; i++) {
      const t = 0.25 + 0.6 * (i + 0.5) / o.lobes, s = i % 2 ? 1 : -1;
      c.beginPath(); c.ellipse(len * t, s * wid * 0.55, len * 0.13, wid * 0.42, 0, 0, 6.3); c.fill();
    }
  }
  // the half away from the light is darker
  c.beginPath(); c.moveTo(0, 0); c.lineTo(len, 0); c.bezierCurveTo(len * 0.8, wid * tipw, len * belly, wid, 0, 0);
  c.fillStyle = `rgba(0,0,0,${o.shade ?? 0.16})`; c.fill();
  if (o.gloss) {                                                      // sky on a glossy blade
    c.beginPath(); c.moveTo(len * 0.12, -wid * 0.12);
    c.bezierCurveTo(len * 0.35, -wid * 0.75, len * 0.7, -wid * 0.5, len * 0.9, -wid * 0.06);
    c.bezierCurveTo(len * 0.7, -wid * 0.2, len * 0.35, -wid * 0.25, len * 0.12, -wid * 0.12);
    c.fillStyle = `rgba(168,196,160,${o.gloss * (0.3 + 0.7 * R())})`; c.fill();
  }
  if (o.rib) {
    c.strokeStyle = o.rib; c.lineWidth = Math.max(len * 0.035, 0.0018);
    c.beginPath(); c.moveTo(0, 0); c.lineTo(len * 0.94, 0); c.stroke();
  }
  c.restore();
}

function stroke(c, x0, y0, x1, y1, w, col, bend = 0) {
  const mx = (x0 + x1) / 2 - (y1 - y0) * bend, my = (y0 + y1) / 2 + (x1 - x0) * bend;
  c.strokeStyle = col; c.lineWidth = w; c.lineCap = 'round';
  c.beginPath(); c.moveTo(x0, y0); c.quadraticCurveTo(mx, my, x1, y1); c.stroke();
}

const inside = (x, y, m = 0.035) => x > m && x < 1 - m && y > m && y < 1 - m * 0.4;

// a zig-zag twig spray growing from (x, y) along ang; calls tip(x, y, ang, w) at every twig end and along thin twigs
function spray(c, R, x, y, ang, len, w, depth, o, tip) {
  const a1 = ang + (R() - 0.5) * o.bend;
  const x1 = x + Math.cos(a1) * len, y1 = y + Math.sin(a1) * len;
  if (!inside(x1, y1)) { if (tip) tip(x, y, ang, w); return; }
  const k = sstep(0.0015, 0.012, w);
  stroke(c, x, y, x1, y1, w, css(mix3(o.thin, o.thick, k), 0.9 + 0.2 * R()), (R() - 0.5) * 0.25);
  if (depth <= 0 || w < o.minW) { if (tip) tip(x1, y1, a1, w); return; }
  const zig = (R() < 0.5 ? -1 : 1) * (o.zig[0] + R() * (o.zig[1] - o.zig[0]));
  spray(c, R, x1, y1, a1 + zig, len * (0.66 + R() * 0.22), w * 0.74, depth - 1, o, tip);
  const n = R() < o.side2 ? 2 : 1;
  for (let i = 0; i < n; i++) {
    const t = 0.35 + R() * 0.6, sgn = (i ? -Math.sign(zig) : Math.sign(zig)) * -1;
    spray(c, R, lerp(x, x1, t), lerp(y, y1, t), a1 + sgn * (o.fork[0] + R() * (o.fork[1] - o.fork[0])), len * (0.5 + R() * 0.3), w * 0.62, depth - 1, o, tip);
  }
  if (tip && w < o.leafW && R() < 0.6) tip(lerp(x, x1, 0.5), lerp(y, y1, 0.5), a1 + (R() - 0.5) * 2.4, w);
}

const PAL = {
  oakLeaf: [[98, 96, 48], [110, 92, 48], [76, 86, 42], [128, 110, 64], [86, 80, 40], [116, 100, 50]],
  oakTwig: { thin: [122, 110, 96], thick: [86, 76, 66] },
  green: { main: [[58, 94, 36], [74, 110, 42], [50, 82, 32], [66, 102, 40]], accent: [[112, 136, 50], [140, 152, 62], [40, 66, 28]], twig: [58, 48, 38] },
  gold: { main: [[218, 164, 30], [230, 182, 46], [204, 144, 24], [224, 172, 36]], accent: [[168, 152, 44], [240, 202, 84], [196, 116, 22], [150, 140, 50]], twig: [70, 56, 40] },
  red: { main: [[172, 36, 24], [198, 50, 28], [146, 26, 22], [184, 42, 26]], accent: [[216, 88, 30], [122, 20, 28], [206, 116, 40], [160, 30, 40]], twig: [52, 36, 30] },
  olive: { main: [[76, 88, 50], [90, 100, 56], [62, 76, 44], [84, 94, 54]], accent: [[122, 126, 82], [112, 106, 60], [50, 62, 38]], twig: [66, 58, 46] },
  sapling: { main: [[82, 100, 54], [96, 112, 60], [70, 88, 48]], accent: [[132, 142, 98], [116, 128, 78]], twig: [92, 74, 58] },
  boxwood: { main: [[42, 64, 26], [54, 78, 30], [34, 54, 22], [48, 72, 28]], accent: [[86, 114, 44], [102, 128, 52], [28, 44, 18]], twig: [48, 40, 30] },
  laurel: { main: [[32, 54, 26], [42, 68, 32], [26, 44, 22], [38, 62, 30]], accent: [[58, 88, 42], [70, 100, 48]], twig: [50, 60, 34] },
  rose: { main: [[50, 82, 40], [60, 96, 46], [42, 70, 36]], accent: [[88, 120, 58], [98, 72, 52], [72, 106, 50]], twig: [70, 84, 44] },
  conifer: { main: [[38, 60, 40], [48, 74, 46], [30, 50, 34], [44, 68, 42]], accent: [[86, 110, 60], [70, 96, 54]], twig: [74, 46, 34] },
};

// --- the oak's twig sprays: cells 0, 1 bare; 2 a few leaf remnants; 3 a leafy spray
function drawOak(c, R, k) {
  const o = { ...PAL.oakTwig, bend: 0.55, zig: [0.18, 0.55], fork: [0.55, 1.25], side2: 0.4, minW: 0.0027, leafW: 0.0046 };
  const leaves = [];
  const nl = [0, 0, 0.2, 0.62][k];
  const tip = nl > 0 ? (x, y, a, w) => { if (R() < nl) leaves.push([x, y, a]); } : null;
  const stems = k === 1 ? 4 : 3;
  for (let i = 0; i < stems; i++) {
    const a = -Math.PI / 2 + (i - (stems - 1) / 2) * (0.5 + 0.15 * R()) + (R() - 0.5) * 0.3;
    spray(c, R, 0.5 + (i - (stems - 1) / 2) * 0.012, 0.992, a, 0.2 + R() * 0.07, 0.016 - 0.003 * Math.abs(i - 1), k === 1 ? 6 : 5, o, tip);
  }
  for (const [x, y, a] of leaves) {
    const n = 1 + Math.floor(R() * (k === 3 ? 2.6 : 1.6));
    for (let i = 0; i < n; i++) {
      const col = pick(R, PAL.oakLeaf), len = 0.026 + R() * 0.02;
      leaf(c, R, x + (R() - 0.5) * 0.02, y + (R() - 0.5) * 0.02, a + (R() - 0.5) * 2.6, len, len * 0.3, mix3(col, [56, 52, 28], R() * 0.4), { lobes: 4, belly: 0.4, tipw: 0.6, shade: 0.2 });
    }
  }
}

// --- a round cluster of leaves for crowns and shrubs; o: { n, len, wid, rad, cy, hang, shape }
function drawCluster(pal, opt) {
  return (c, R, k) => {
    const o = { ...opt, ...(opt.cells ? opt.cells[k] : {}) };
    const cx = 0.5 + (R() - 0.5) * 0.06, cy = o.cy ?? 0.52, rad = o.rad ?? 0.4;
    const ph = [R() * 6.3, R() * 6.3, R() * 6.3];
    const edge = (th) => rad * (0.8 + 0.14 * Math.sin(3 * th + ph[0]) + 0.1 * Math.sin(5 * th + ph[1]) + 0.06 * Math.sin(8 * th + ph[2]));
    // twigs from the root up into the cluster
    const nt = o.twigs ?? 5;
    for (let i = 0; i < nt; i++) {
      const th = R() * 6.3, r = edge(th) * (0.4 + 0.5 * R());
      stroke(c, 0.5, 0.99, cx + Math.cos(th) * r, cy + Math.sin(th) * r, 0.004 + R() * 0.005, css(pal.twig, 0.8 + 0.4 * R()), (R() - 0.5) * 0.3);
    }
    const n = Math.round(o.n * (o.fill ?? 1));
    for (let i = 0; i < n; i++) {
      const layer = i / n;                                         // back to front: dark, mid, light
      const th = R() * 6.3, rr = Math.pow(R(), o.core ?? 0.62) * edge(th);
      if (o.holes && Math.sin(th * 3 + ph[1]) * Math.sin(rr * 19 + ph[2]) > o.holes) continue;
      const x = cx + Math.cos(th) * rr, y = cy + Math.sin(th) * rr * (o.squash ?? 1);
      const out = Math.atan2(y - cy, x - cx);
      let a = out + (R() - 0.5) * 2.2;
      a = lerp(a, Math.PI / 2 * Math.sign(Math.cos(a) || 1) * 0.6 + (Math.cos(a) < 0 ? Math.PI : 0), 0) + (o.hang ?? 0) * Math.sin(Math.PI / 2 - a);
      const len = o.len * (0.7 + 0.6 * R()), wid = len * o.wid * (0.8 + 0.4 * R());
      if (!inside(x + Math.cos(a) * len, y + Math.sin(a) * len, 0.02) || !inside(x, y, 0.02)) continue;
      let col = R() < (o.accent ?? 0.18) ? pick(R, pal.accent) : pick(R, pal.main);
      const b = (layer < 0.34 ? 0.5 : layer < 0.7 ? 0.76 : 1.0) * (0.86 + 0.28 * R()) * (1.08 - 0.3 * sstep(-0.2, 0.9, (y - cy) / rad));
      col = [col[0] * b, col[1] * b, col[2] * b];
      leaf(c, R, x, y, a, len, wid, col, { belly: o.belly, tipw: o.tipw, shade: o.shade, gloss: layer > 0.5 ? o.gloss : 0, rib: o.rib && layer > 0.3 ? o.rib : null });
    }
  };
}

// --- a shoot seen from the side: a stem from the root with leaves along it; o: { n, len, wid, spread }
function drawShoot(pal, opt) {
  return (c, R, k) => {
    const o = { ...opt, ...(opt.cells ? opt.cells[k] : {}) };
    const stems = o.stems ?? 1;
    for (let s = 0; s < stems; s++) {
      let x = 0.5 + (s - (stems - 1) / 2) * 0.03, y = 0.99, a = -Math.PI / 2 + (s - (stems - 1) / 2) * (o.fan ?? 0.5) + (R() - 0.5) * 0.25;
      const segs = o.segs ?? 9, step = (o.height ?? 0.8) / segs;
      const pts = [[x, y, a]];
      for (let i = 0; i < segs; i++) {
        a += (R() - 0.5) * (o.wander ?? 0.3);
        const x1 = x + Math.cos(a) * step, y1 = y + Math.sin(a) * step;
        if (!inside(x1, y1, 0.06)) break;
        stroke(c, x, y, x1, y1, lerp(o.stemW ?? 0.012, 0.004, i / segs), css(pal.twig, 0.85 + 0.3 * R()));
        x = x1; y = y1; pts.push([x, y, a]);
      }
      const all = [];
      for (let i = 1; i < pts.length; i++) {
        const [px, py, pa] = pts[i], per = o.per ?? 2;
        for (let j = 0; j < per; j++) {
          const sgn = (i + j) % 2 ? 1 : -1;
          all.push([px, py, pa + sgn * ((o.spread ?? 0.9) + (R() - 0.5) * 0.7), i / pts.length]);
        }
      }
      all.push([x, y, a + (R() - 0.5) * 0.4, 1]);
      all.sort(() => R() - 0.5);
      all.forEach(([px, py, pa, t], i) => {
        const len = o.len * (0.75 + 0.5 * R()) * (1 - 0.25 * t), wid = len * o.wid * (0.8 + 0.4 * R());
        if (!inside(px + Math.cos(pa) * len, py + Math.sin(pa) * len, 0.02)) return;
        let col = R() < (o.accent ?? 0.15) ? pick(R, pal.accent) : pick(R, pal.main);
        const b = (i / all.length < 0.4 ? 0.62 : 1.0) * (0.85 + 0.3 * R());
        col = [col[0] * b, col[1] * b, col[2] * b];
        leaf(c, R, px, py, pa, len, wid, col, { belly: o.belly, tipw: o.tipw, shade: o.shade, gloss: o.gloss, rib: o.rib });
      });
    }
  };
}

// --- roses: compound leaves on thin canes; cell 2 with flowers, cell 3 one open flower
function rosette(c, R, x, y, r) {
  const g = c.createRadialGradient(x, y, 0, x, y, r);
  g.addColorStop(0, 'rgb(236,214,160)'); g.addColorStop(0.35, 'rgb(250,244,226)'); g.addColorStop(1, 'rgb(252,251,246)');
  for (let ring = 0; ring < 4; ring++) {
    const n = [7, 6, 5, 3][ring], rr = r * [1.0, 0.74, 0.5, 0.26][ring], a0 = R() * 6.3;
    for (let i = 0; i < n; i++) {
      const a = a0 + i * 6.283 / n + (R() - 0.5) * 0.3;
      c.save(); c.translate(x + Math.cos(a) * rr * 0.42, y + Math.sin(a) * rr * 0.42); c.rotate(a);
      c.beginPath(); c.ellipse(rr * 0.22, 0, rr * 0.5, rr * 0.46, 0, 0, 6.3);
      c.fillStyle = g; c.fill();
      c.strokeStyle = `rgba(150,140,110,${0.28 + 0.12 * ring})`; c.lineWidth = r * 0.03; c.stroke();
      c.restore();
    }
  }
  c.beginPath(); c.arc(x, y, r * 0.09, 0, 6.3); c.fillStyle = 'rgb(214,170,70)'; c.fill();
}

function drawRose(c, R, k) {
  const pal = PAL.rose;
  const compound = (x, y, a, s) => {                          // 5 leaflets on a petiole
    const x1 = x + Math.cos(a) * s, y1 = y + Math.sin(a) * s;
    stroke(c, x, y, x1, y1, 0.004, css(pal.twig));
    const b = 0.75 + 0.4 * R(), col = R() < 0.14 ? pick(R, pal.accent) : pick(R, pal.main);
    const cc = [col[0] * b, col[1] * b, col[2] * b], o = { belly: 0.42, tipw: 0.6, rib: 'rgba(120,150,90,0.6)', shade: 0.2 };
    for (const t of [0.45, 0.8]) for (const sgn of [-1, 1]) leaf(c, R, lerp(x, x1, t), lerp(y, y1, t), a + sgn * 1.05, s * 0.42, s * 0.14, cc, o);
    leaf(c, R, x1, y1, a, s * 0.5, s * 0.16, cc, o);
  };
  if (k === 3) {
    for (let i = 0; i < 5; i++) compound(0.5, 0.5, i * 1.257 + R(), 0.3);
    rosette(c, R, 0.5, 0.5, 0.36);
    return;
  }
  const flowers = [];
  for (let s = 0; s < 3; s++) {
    let x = 0.5 + (s - 1) * 0.02, y = 0.99, a = -Math.PI / 2 + (s - 1) * 0.55 + (R() - 0.5) * 0.3;
    for (let i = 0; i < 7; i++) {
      a += (R() - 0.5) * 0.35;
      const x1 = x + Math.cos(a) * 0.11, y1 = y + Math.sin(a) * 0.11;
      if (!inside(x1, y1, 0.12)) break;
      stroke(c, x, y, x1, y1, 0.007, css(pal.twig, 0.9 + 0.2 * R()));
      x = x1; y = y1;
      const sgn = i % 2 ? 1 : -1, la = a + sgn * (0.9 + R() * 0.5), s2 = 0.15 + R() * 0.06;
      if (inside(x + Math.cos(la) * s2 * 1.5, y + Math.sin(la) * s2 * 1.5, 0.03)) compound(x, y, la, s2);
    }
    if (inside(x, y, 0.15)) flowers.push([x, y]);
  }
  if (k === 2) for (const [x, y] of flowers) rosette(c, R, x, y, 0.1 + R() * 0.035);
  if (k === 1) for (const [x, y] of flowers.slice(0, 1)) {       // a bud
    c.beginPath(); c.ellipse(x, y - 0.02, 0.022, 0.034, 0, 0, 6.3); c.fillStyle = 'rgb(244,240,222)'; c.fill();
    c.beginPath(); c.ellipse(x, y, 0.02, 0.018, 0, 0, 6.3); c.fillStyle = css(pal.main[0]); c.fill();
  }
}

// --- conifer boughs.  0: a bough from the side (the cell's left = its under side, where the sprays hang),
//     1: a flat frond from above, 2: the tuft at a bough's end seen end-on, 3: a dark dense mass
function drawConifer(c, R, k) {
  const pal = PAL.conifer;
  const sprig = (x, y, a, len, b) => {                        // a branchlet feathered with needles
    const x1 = x + Math.cos(a) * len, y1 = y + Math.sin(a) * len;
    if (!inside(x1, y1, 0.045) || !inside(x, y, 0.045)) return;
    const col = R() < 0.18 ? pick(R, pal.accent) : pick(R, pal.main), cc = css(col, b * (0.8 + 0.4 * R()));
    c.strokeStyle = cc; c.lineCap = 'round';
    c.lineWidth = 0.0046;
    c.beginPath(); c.moveTo(x, y); c.lineTo(x1, y1); c.stroke();
    c.lineWidth = 0.0038;
    const n = Math.max(4, Math.round(len / 0.0105));
    c.beginPath();
    for (let i = 0; i < n; i++) {
      const t = (i + 0.5) / n, px = lerp(x, x1, t), py = lerp(y, y1, t), nl = 0.019 * (1 - 0.5 * t);
      for (const s of [-1, 1]) { c.moveTo(px, py); c.lineTo(px + Math.cos(a + s * 0.95) * nl, py + Math.sin(a + s * 0.95) * nl); }
    }
    c.stroke();
  };
  const frond = (x, y, a, len, w, depth, b, taper = 0.45) => {
    const x1 = x + Math.cos(a) * len, y1 = y + Math.sin(a) * len;
    if (!inside(x1, y1, 0.05)) return;
    stroke(c, x, y, x1, y1, w, css(pal.twig, 0.8 + 0.3 * R()));
    const n = Math.round(len / 0.032);
    for (let i = 1; i <= n; i++) {
      const t = i / (n + 0.5), px = lerp(x, x1, t), py = lerp(y, y1, t);
      for (const s of [-1, 1]) {
        const aa = a + s * (0.7 + R() * 0.45), ll = len * (0.36 + 0.2 * R()) * (1 - taper * t);
        if (depth > 0 && ll > 0.07) frond(px, py, aa, ll, w * 0.6, depth - 1, b, taper);
        else sprig(px, py, aa, Math.max(0.03, ll), b);
      }
    }
    sprig(x1, y1, a, 0.05, b);
  };
  const up = -Math.PI / 2;
  if (k === 0) {
    for (let pass = 0; pass < 2; pass++) {
      const b = pass ? 1 : 0.55;
      stroke(c, 0.56, 0.99, 0.6, 0.08, 0.012, css(pal.twig));
      for (let i = 0; i < 17; i++) {
        const t = (i + R()) / 17, x = lerp(0.56, 0.6, t), y = lerp(0.97, 0.1, t);
        frond(x, y, Math.PI + 0.25 + R() * 0.5, (0.2 + 0.24 * R()) * (1 - 0.45 * t), 0.006, 1, b, 0.3);   // hanging
        if (R() < 0.8) frond(x, y, -0.75 - R() * 0.4, (0.1 + 0.1 * R()) * (1 - 0.3 * t), 0.005, 0, b, 0.3);  // the upper side
      }
      frond(0.6, 0.12, up - 0.15, 0.07, 0.005, 0, b);
    }
  } else if (k === 1) {
    for (let pass = 0; pass < 2; pass++) {
      const b = pass ? 1 : 0.55;
      stroke(c, 0.5, 0.99, 0.5, 0.07, 0.012, css(pal.twig));
      for (let i = 0; i < 18; i++) {
        const t = (i + R()) / 18, y = lerp(0.96, 0.1, t), w = 0.36 * Math.sin(Math.PI * Math.min(1, 0.18 + 0.9 * t)) * (1 - 0.35 * t);
        for (const s of [-1, 1]) frond(0.5, y, up + s * (0.95 + R() * 0.3), w * (0.8 + 0.4 * R()), 0.006, 1, b, 0.35);
      }
    }
  } else {
    const dark = k === 3 ? 0.55 : 1, n = k === 3 ? 30 : 17, rad = k === 3 ? 0.4 : 0.34;
    for (let pass = 0; pass < 2; pass++) {
      const b = (pass ? 1 : 0.5) * dark;
      for (let i = 0; i < n; i++) {
        let a = R() * 6.283;
        if (k === 2 && Math.sin(a) < -0.2 && R() < 0.6) a = -a;                // more of them hang than rise
        const r0 = R() * 0.1;
        frond(0.5 + Math.cos(a) * r0, 0.5 + Math.sin(a) * r0, a + (R() - 0.5) * 0.5, rad * (0.55 + 0.45 * R()), 0.006, 1, b, 0.3);
      }
    }
  }
}

// ---- the atlases ------------------------------------------------------------------------------------------------------
// through: colour and amount of the light that comes through the leaves; vary: [brightness +-, warm / cool +-, the
// shade of class 0]; sway: m at the card's tip
const LEAVES = {
  leaf_oak: { size: 1024, seed: 101, draw: drawOak, rough: 1.0, cut: 0.3, sway: 0.012, through: [1.0, 0.92, 0.6, 0.2], vary: [0.14, 0.04, 0.62], env: 0.9 },
  leaf_green: { size: 1024, seed: 202, rough: 0.92, cut: 0.38, sway: 0.03, through: [0.95, 1.05, 0.35, 0.7], vary: [0.1, 0.05, 0.38], env: 0.9,
    draw: drawCluster(PAL.green, { n: 330, len: 0.085, wid: 0.33, rad: 0.43, hang: 0.5, rib: 'rgba(150,170,90,0.4)',
      cells: [{}, { n: 300, core: 0.5 }, { n: 230, holes: 0.25 }, { n: 100, rad: 0.36, holes: 0.05, twigs: 8 }] }) },
  leaf_gold: { size: 1024, seed: 303, rough: 0.92, cut: 0.38, sway: 0.03, through: [1.25, 1.0, 0.3, 1.0], vary: [0.09, 0.04, 0.45], env: 0.9,
    draw: drawCluster(PAL.gold, { n: 300, len: 0.08, wid: 0.36, rad: 0.43, hang: 0.6, belly: 0.5, tipw: 0.8, rib: 'rgba(250,224,130,0.35)', accent: 0.24,
      cells: [{}, { n: 270, core: 0.5 }, { n: 200, holes: 0.25 }, { n: 90, rad: 0.36, holes: 0.05, twigs: 8 }] }) },
  leaf_red: { size: 512, seed: 404, rough: 0.92, cut: 0.38, sway: 0.03, through: [1.3, 0.55, 0.3, 1.0], vary: [0.1, 0.04, 0.36], env: 0.9,
    draw: drawCluster(PAL.red, { n: 330, len: 0.085, wid: 0.34, rad: 0.43, hang: 0.5, rib: 'rgba(230,120,70,0.3)', accent: 0.26,
      cells: [{}, { n: 300, core: 0.5 }, { n: 230, holes: 0.3 }, { n: 100, rad: 0.36, holes: 0.05, twigs: 8 }] }) },
  leaf_olive: { size: 512, seed: 505, rough: 0.95, cut: 0.38, sway: 0.025, through: [0.9, 1.0, 0.45, 0.4], vary: [0.1, 0.04, 0.38], env: 0.9,
    draw: drawCluster(PAL.olive, { n: 360, len: 0.075, wid: 0.3, rad: 0.43, hang: 0.3, accent: 0.22,
      cells: [{}, { n: 330, core: 0.5 }, { n: 250, holes: 0.25 }, { n: 110, rad: 0.36, holes: 0.05, twigs: 8 }] }) },
  leaf_sapling: { size: 512, seed: 606, rough: 0.92, cut: 0.38, sway: 0.03, through: [0.95, 1.05, 0.45, 0.6], vary: [0.12, 0.05, 0.6], env: 0.9,
    draw: drawShoot(PAL.sapling, { len: 0.16, wid: 0.3, stems: 2, fan: 0.7, segs: 8, height: 0.78, per: 2, rib: 'rgba(170,180,130,0.5)', accent: 0.2,
      cells: [{}, { stems: 3 }, { stems: 1, per: 3 }, { stems: 2, segs: 6, height: 0.6 }] }) },
  leaf_boxwood: { size: 512, seed: 707, rough: 0.9, cut: 0.4, sway: 0.006, through: [0.9, 1.05, 0.35, 0.35], vary: [0.12, 0.04, 0.35], env: 0.9,
    draw: drawCluster(PAL.boxwood, { n: 330, len: 0.07, wid: 0.42, rad: 0.45, belly: 0.5, tipw: 0.85, gloss: 0.1, accent: 0.22, twigs: 3,
      cells: [{}, { n: 310, core: 0.5 }, { n: 260, holes: 0.35 }, { n: 60, rad: 0.3, cy: 0.6, twigs: 4, core: 1.0 }] }) },
  leaf_laurel: { size: 1024, seed: 808, rough: 0.85, cut: 0.4, sway: 0.012, through: [0.85, 1.05, 0.35, 0.4], vary: [0.12, 0.04, 0.32], env: 0.9,
    draw: (c, R, k) => (k === 3
      ? drawShoot(PAL.laurel, { len: 0.3, wid: 0.2, stems: 1, segs: 7, height: 0.66, per: 2, spread: 0.75, gloss: 0.3, rib: 'rgba(130,160,90,0.7)', stemW: 0.014 })
      : drawCluster(PAL.laurel, { n: 60, len: 0.27, wid: 0.2, rad: 0.34, belly: 0.4, tipw: 0.5, gloss: 0.3, rib: 'rgba(120,150,84,0.7)', hang: 0.35, core: 0.8, twigs: 3,
        cells: [{}, { n: 54 }, { n: 42, holes: 0.5 }] }))(c, R, k) },
  leaf_rose: { size: 1024, seed: 909, draw: drawRose, rough: 0.9, cut: 0.4, sway: 0.015, through: [0.9, 1.05, 0.4, 0.5], vary: [0.08, 0.03, 0.4], env: 0.9 },
  leaf_conifer: { size: 1024, seed: 1010, draw: drawConifer, rough: 1.0, cut: 0.33, sway: 0.02, through: [0.9, 1.0, 0.45, 0.25], vary: [0.14, 0.05, 0.3], env: 0.85 },
};

// colour of empty texels = the colour of the nearest leaf (two sweeps), so mip-maps and soft edges do not darken
function bleed(d, w, h) {
  const n = w * h, ok = new Uint8Array(n);
  let sr = 0, sg = 0, sb = 0, cnt = 0;
  for (let i = 0; i < n; i++) if (d[i * 4 + 3] > 48) { ok[i] = 1; sr += d[i * 4]; sg += d[i * 4 + 1]; sb += d[i * 4 + 2]; cnt++; }
  const mr = cnt ? sr / cnt : 80, mg = cnt ? sg / cnt : 90, mb = cnt ? sb / cnt : 50;
  const copy = (i, j) => { d[i * 4] = d[j * 4]; d[i * 4 + 1] = d[j * 4 + 1]; d[i * 4 + 2] = d[j * 4 + 2]; ok[i] = 2; };
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const i = y * w + x;
    if (ok[i]) continue;
    if (x > 0 && ok[i - 1]) copy(i, i - 1); else if (y > 0 && ok[i - w]) copy(i, i - w);
  }
  for (let y = h - 1; y >= 0; y--) for (let x = w - 1; x >= 0; x--) {
    const i = y * w + x;
    if (ok[i] === 1) continue;
    if (x < w - 1 && ok[i + 1] === 1) copy(i, i + 1);
    else if (y < h - 1 && ok[i + w] === 1) copy(i, i + w);
    else if (!ok[i]) { if (x < w - 1 && ok[i + 1]) copy(i, i + 1); else if (y < h - 1 && ok[i + w]) copy(i, i + w); }
  }
  for (let i = 0; i < n; i++) if (!ok[i]) { d[i * 4] = mr; d[i * 4 + 1] = mg; d[i * 4 + 2] = mb; }
}

function atlasTexture(ctx, spec) {
  const { THREE } = ctx;
  const size = ctx.quality === 'low' ? spec.size / 2 : spec.size;
  const [nx, ny] = ATLAS, S = size / nx;
  const cv = makeCanvas(size, size), c = cv.getContext('2d', { willReadFrequently: true });
  for (let k = 0; k < nx * ny; k++) {
    const R = rng(spec.seed * 31 + k * 7);
    c.save();
    c.translate((k % nx) * S, Math.floor(k / nx) * S);
    c.beginPath(); c.rect(S * 0.01, S * 0.01, S * 0.98, S * 0.985); c.clip();
    c.scale(S, S);
    spec.draw(c, R, k);
    c.restore();
  }
  const img = c.getImageData(0, 0, size, size);
  bleed(img.data, size, size);
  const t = new THREE.DataTexture(new Uint8Array(img.data.buffer), size, size, THREE.RGBAFormat);
  t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.magFilter = THREE.LinearFilter; t.minFilter = THREE.LinearMipmapLinearFilter; t.generateMipmaps = true;
  t.anisotropy = Math.min(4, ctx.anisotropy || 1);
  t.needsUpdate = true;
  return t;
}

function foliageMaterial(ctx, spec) {
  const { THREE } = ctx;
  const map = atlasTexture(ctx, spec);
  let samples = 0;
  try { const gl = ctx.renderer.getContext(); samples = gl.getParameter(gl.SAMPLES); } catch (e) { samples = 0; }
  const a2c = samples >= 2;
  const m = new THREE.MeshStandardMaterial({ map, roughness: spec.rough, metalness: 0, side: THREE.DoubleSide, alphaTest: spec.cut });
  m.alphaToCoverage = a2c;
  m.shadowSide = THREE.DoubleSide;
  m.envMapIntensity = spec.env ?? 0.8;
  const U = {
    uPlTime: shared.time,
    uPlSway: { value: spec.sway },
    uPlAtlas: { value: new THREE.Vector2(ATLAS[0], ATLAS[1]) },
    uPlTex: { value: new THREE.Vector2(map.image.width, map.image.height) },
    uPlThrough: { value: new THREE.Vector3(spec.through[0], spec.through[1], spec.through[2]).multiplyScalar(spec.through[3]) },
    uPlVar: { value: new THREE.Vector3(...spec.vary) },
    uPlMode: { value: new THREE.Vector2(a2c ? 0 : 2, 0) },      // x: 0 alpha to coverage, 1 stochastic, 2 plain cut-out; y: frame
  };
  m.userData.plant = U;
  // the refinement passes of picture.js render into a target without multisampling: there the cut-out is stochastic
  m.onBeforeRender = (renderer) => {
    const rt = renderer.getRenderTarget();
    U.uPlMode.value.set(rt ? (rt.samples > 0 ? 0 : 1) : (a2c ? 0 : 2), renderer.info.render.frame % 4096);
  };
  m.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, U);
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nuniform float uPlTime;\nuniform float uPlSway;\nuniform vec2 uPlAtlas;\nvarying vec3 vPl;')
      .replace('#include <begin_vertex>', `#include <begin_vertex>
      {
        vec2 plC = floor( uv );
        float plW = fract( ( 1.0 - ( uv.y - plC.y ) ) * uPlAtlas.y );       // 0 at the card's root .. 1 at its tip
        vPl = vec3( plC.x, - plC.y - 1.0, plW );
        float plPh = dot( position, vec3( 0.9, 0.6, 1.1 ) );
        float plA = uPlSway * plW * plW * min( uPlTime, 1.0 ) * ( 0.65 + 0.35 * sin( uPlTime * 0.37 + plPh * 0.08 ) );
        transformed += plA * vec3( sin( uPlTime * 1.7 + plPh ), 0.4 * sin( uPlTime * 2.3 + plPh * 1.3 ), cos( uPlTime * 1.3 + plPh * 0.8 ) );
      }`);
    const lights = THREE.ShaderChunk.lights_fragment_begin.split('#if ( NUM_DIR_LIGHTS > 0 ) && defined( RE_Direct )');
    const dir = lights[1].split('#if ( NUM_RECT_AREA_LIGHTS > 0 )');
    dir[0] = dir[0]
      .replace('getDirectionalLightInfo( directionalLight, directLight );', 'getDirectionalLightInfo( directionalLight, directLight );\n\t\tplSun = directLight.color;')
      .replace('RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );',
        `RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
        {
          float plBack = saturate( - dot( geometryNormal, directLight.direction ) );
          float plVL = saturate( dot( geometryViewDir, - directLight.direction ) );
          plThrough += mix( directLight.color, plSun, 0.4 ) * ( 0.75 * plBack + 0.35 * plVL * plVL );
        }`);
    const lightsChunk = lights[0] + '#if ( NUM_DIR_LIGHTS > 0 ) && defined( RE_Direct )' + dir.join('#if ( NUM_RECT_AREA_LIGHTS > 0 )');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>
      uniform vec3 uPlThrough;
      uniform vec3 uPlVar;
      uniform vec2 uPlTex;
      uniform vec2 uPlMode;
      varying vec3 vPl;
      float plCov = 1.0;
      vec3 plSun = vec3( 0.0 );
      vec3 plThrough = vec3( 0.0 );`)
      .replace('#include <map_fragment>', `#include <map_fragment>
      {
        float plH1 = fract( vPl.x * 0.6180339 + 0.21 ), plH2 = fract( vPl.x * 0.3819660 + 0.57 );
        diffuseColor.rgb *= ( 1.0 + uPlVar.x * ( plH1 * 2.0 - 1.0 ) ) * mix( vec3( 1.0 + uPlVar.y, 1.0, 1.0 - uPlVar.y ), vec3( 1.0 - uPlVar.y, 1.0, 1.0 + 0.5 * uPlVar.y ), plH2 );
        diffuseColor.rgb *= mix( uPlVar.z, 1.0, clamp( vPl.y / 7.0, 0.0, 1.0 ) );
      }`)
      .replace('#include <alphatest_fragment>', `
      #ifdef USE_ALPHATEST
      {
        float plA = diffuseColor.a;
        vec2 plT = vMapUv * uPlTex;
        float plLod = 0.5 * log2( max( dot( dFdx( plT ), dFdx( plT ) ), dot( dFdy( plT ), dFdy( plT ) ) ) + 1e-8 );
        float plSharp = clamp( ( plA - alphaTest ) / max( fwidth( plA ), 1e-4 ) + 0.5, 0.0, 1.0 );
        plCov = mix( plSharp, clamp( plA * 1.12, 0.0, 1.0 ), clamp( plLod - 0.3, 0.0, 1.0 ) );
        float plN = fract( 52.9829189 * fract( dot( gl_FragCoord.xy + 5.588238 * uPlMode.y, vec2( 0.06711056, 0.00583715 ) ) ) );
        if ( uPlMode.x > 1.5 ) {                 // no multisampling at all: a plain cut-out
          if ( plA < alphaTest ) discard;
          plCov = 1.0;
        } else if ( uPlMode.x > 0.5 ) {          // a refinement pass into a plain target: stochastic, the passes average to the coverage
          if ( plCov <= plN * 0.98 + 0.01 ) discard;
          plCov = 1.0;
        } else {                                 // alpha to coverage on the multisampled canvas
          if ( plCov < 0.999 ) plCov = clamp( plCov + ( plN - 0.5 ) * 0.22, 0.0, 1.0 );
          if ( plCov < 0.03 ) discard;
        }
      }
      #endif`)
      .replace('#include <normal_fragment_begin>', THREE.ShaderChunk.normal_fragment_begin.replace('normal *= faceDirection;', ''))
      .replace('#include <lights_fragment_begin>', lightsChunk)
      .replace('#include <lights_fragment_end>', '#include <lights_fragment_end>\n\treflectedLight.directDiffuse += plThrough * BRDF_Lambert( material.diffuseColor * uPlThrough );')
      .replace('#include <opaque_fragment>', 'gl_FragColor = vec4( outgoingLight, plCov );');
  };
  m.customProgramCacheKey = () => 'plants-leaf-' + (a2c ? 'a2c' : 'cut');
  return m;
}

export function register(lib) {
  lib.onTick((s) => { shared.time.value = s; });
  lib.add('bark', (ctx) => barkMaterial(ctx, BARKS.oak));
  lib.add('bark_redwood', (ctx) => barkMaterial(ctx, BARKS.redwood));
  lib.add('bark_young', youngBark);
  lib.add('shrub_core', shrubCore);
  lib.add('stake_wood', { color: 0xb09a78, roughness: 0.9 });
  lib.add('plant_tie', { color: 0x1c1c1c, roughness: 0.7 });
  for (const [name, spec] of Object.entries(LEAVES)) lib.add(name, (ctx) => foliageMaterial(ctx, spec), { cutout: true });
}
