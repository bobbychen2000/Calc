// Look module "fixtures": materials of the exterior fixtures family (model/fixtures.py), registered by name
// (see ../materials.js for the contract).  Shared surfaces (trim_white, roof_seam, gutter_dark, metal_awning,
// pergola_metal, fence_wood, chimney_cap ...) belong to looks/surfaces.js and are only USED by the builders.
//
// Everything here is procedural and deterministic (seeded): five small canvases, ~20 ms in total.
// Texture orientation: the GLB's UVs are (u, -v) and the canvases are uploaded with flipY = false, so the TOP of a
// canvas is "up" on a wall and v = 1 of the builders' 0..1 UVs.

function rng(seed) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6D2B79F5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// a canvas texture drawn in nominal pixels (w x h); halved on the low quality tier
function tex(ctx, w, h, draw, opt = {}) {
  const T = ctx.THREE;
  const q = ctx.quality === 'low' ? 0.5 : 1;
  const c = document.createElement('canvas');
  c.width = Math.max(4, Math.round(w * q));
  c.height = Math.max(4, Math.round(h * q));
  const g = c.getContext('2d');
  g.scale(c.width / w, c.height / h);
  draw(g, w, h);
  const t = new T.CanvasTexture(c);
  t.flipY = false;
  t.wrapS = opt.clampS ? T.ClampToEdgeWrapping : T.RepeatWrapping;
  t.wrapT = opt.clampT ? T.ClampToEdgeWrapping : T.RepeatWrapping;
  t.colorSpace = opt.data ? T.NoColorSpace : T.SRGBColorSpace;
  t.anisotropy = ctx.anisotropy || 1;
  t.generateMipmaps = true;
  t.minFilter = T.LinearMipmapLinearFilter;
  t.magFilter = T.LinearFilter;
  if (opt.repeat) t.repeat.set(opt.repeat[0], opt.repeat[1]);
  t.needsUpdate = true;
  return t;
}

const rgb = (r, g, b, a = 1) => `rgba(${r | 0},${g | 0},${b | 0},${a})`;

// vertical wood grain: long soft streaks over a base colour, a few darker checks; tiles in both directions
function woodGrain(g, w, h, base, seed, { streaks = 260, contrast = 0.16, knots = 0 } = {}) {
  const R = rng(seed);
  g.fillStyle = rgb(...base);
  g.fillRect(0, 0, w, h);
  for (let i = 0; i < streaks; i++) {
    const x = R() * w, len = h * (0.25 + R() * 0.9), y = R() * h, wd = 0.6 + R() * 2.6;
    const d = (R() - 0.55) * 2 * contrast;
    g.fillStyle = d < 0 ? rgb(0, 0, 0, -d) : rgb(255, 236, 200, d * 0.8);
    for (const yy of [y, y - h]) g.fillRect(x, yy, wd, len);            // wrap vertically
    if (x + wd > w) for (const yy of [y, y - h]) g.fillRect(x - w, yy, wd, len);
  }
  for (let i = 0; i < knots; i++) {
    const x = R() * w, y = R() * h, r = 2 + R() * 4;
    const gr = g.createRadialGradient(x, y, 0, x, y, r * 2.2);
    gr.addColorStop(0, rgb(40, 22, 12, 0.55));
    gr.addColorStop(1, rgb(40, 22, 12, 0));
    g.fillStyle = gr;
    g.fillRect(x - r * 3, y - r * 3, r * 6, r * 6);
  }
}

// ---- the textures ---------------------------------------------------------------------------------------------------

// one PV module: black frame, 6 x 20 half-cut cells, hairline gaps and bus bars (512 x 768 = 1.134 x 1.722 m)
function solarTex(ctx) {
  return tex(ctx, 512, 768, (g, w, h) => {
    const R = rng(11);
    g.fillStyle = '#060709';
    g.fillRect(0, 0, w, h);
    g.fillStyle = '#17181b';                       // anodised frame: a lighter arris on its inner edge
    g.fillRect(0, 0, w, h);
    g.fillStyle = '#0b0c0e';
    g.fillRect(2, 2, w - 4, h - 4);
    const m = 11;
    g.fillStyle = '#05070a';
    g.fillRect(m, m, w - 2 * m, h - 2 * m);
    const cols = 6, rows = 20, cw = (w - 2 * m - 6) / cols, ch = (h - 2 * m - 10) / rows;
    for (let j = 0; j < rows; j++) {
      for (let i = 0; i < cols; i++) {
        const x = m + 3 + i * cw, y = m + 3 + j * ch + (j >= rows / 2 ? 4 : 0);
        const k = 0.92 + R() * 0.16;
        g.fillStyle = rgb(15 * k, 23 * k, 40 * k);
        g.fillRect(x + 0.8, y + 0.8, cw - 1.6, ch - 1.6);
        g.fillStyle = 'rgba(140,160,200,0.045)';
        for (let b = 1; b < 9; b++) g.fillRect(x + (b * cw) / 9, y + 0.8, 0.7, ch - 1.6);
      }
    }
  }, { clampS: true, clampT: true });
}

// eight square pickets across the tile (u = 1 per picket), full height; colour and mask separately so the
// mip levels do not darken the cut edges
function picketTex(ctx) {
  const N = 8, pw = 64, w = N * pw, h = 128, frac = 0.40;
  const map = tex(ctx, w, h, (g) => {
    const R = rng(23);
    woodGrain(g, w, h, [158, 110, 72], 24, { streaks: 180, contrast: 0.14 });
    for (let i = 0; i < N; i++) {
      const k = (R() - 0.5) * 0.22;
      g.fillStyle = k < 0 ? rgb(30, 14, 6, -k) : rgb(255, 214, 160, k);
      g.fillRect(i * pw, 0, pw, h);
      const x0 = i * pw + (pw * (1 - frac)) / 2, x1 = x0 + pw * frac;
      g.fillStyle = 'rgba(0,0,0,0.20)';              // the arrises
      g.fillRect(x0, 0, 2, h);
      g.fillRect(x1 - 2, 0, 2, h);
    }
  }, { clampT: true, repeat: [1 / N, 1] });
  const mask = tex(ctx, w, h, (g) => {
    g.fillStyle = '#000';
    g.fillRect(0, 0, w, h);
    g.fillStyle = '#fff';
    for (let i = 0; i < N; i++) g.fillRect(i * pw + (pw * (1 - frac)) / 2, 0, pw * frac, h);
  }, { clampT: true, repeat: [1 / N, 1], data: true });
  return { map, mask };
}

// infrared heater face: three reflector bays in a dark frame, two element tubes (u along the length)
function heaterTex(ctx) {
  return tex(ctx, 384, 48, (g, w, h) => {
    g.fillStyle = '#1b1c1e';
    g.fillRect(0, 0, w, h);
    const bays = 3, m = 6, bw = (w - m * (bays + 1)) / bays;
    for (let i = 0; i < bays; i++) {
      const x = m + i * (bw + m);
      const gr = g.createLinearGradient(0, m, 0, h - m);
      gr.addColorStop(0, '#6e7072');
      gr.addColorStop(0.5, '#c9cbcc');
      gr.addColorStop(1, '#7c7e80');
      g.fillStyle = gr;
      g.fillRect(x, m, bw, h - 2 * m);
      g.fillStyle = 'rgba(30,30,32,0.35)';
      for (let k = 4; k < bw; k += 4) g.fillRect(x + k, m, 1, h - 2 * m);
      g.fillStyle = '#3a3634';
      g.fillRect(x + 3, h * 0.36, bw - 6, 3);
      g.fillRect(x + 3, h * 0.60, bw - 6, 3);
    }
  }, { clampS: true, clampT: true });
}

// lantern at dusk: the lamp's light scattered in the glass - a soft bright core fading to the frame
function glowTex(ctx) {
  return tex(ctx, 32, 128, (g, w, h) => {
    g.fillStyle = '#000';
    g.fillRect(0, 0, w, h);
    const gx = g.createLinearGradient(0, 0, w, 0);
    gx.addColorStop(0, 'rgba(255,255,255,0.30)');
    gx.addColorStop(0.5, 'rgba(255,255,255,1)');
    gx.addColorStop(1, 'rgba(255,255,255,0.30)');
    g.fillStyle = gx;
    g.fillRect(0, 0, w, h);
    const gy = g.createLinearGradient(0, 0, 0, h);
    gy.addColorStop(0, 'rgba(0,0,0,0.55)');
    gy.addColorStop(0.22, 'rgba(0,0,0,0.05)');
    gy.addColorStop(0.75, 'rgba(0,0,0,0)');
    gy.addColorStop(1, 'rgba(0,0,0,0.45)');
    g.fillStyle = gy;
    g.fillRect(0, 0, w, h);
  }, { clampS: true, clampT: true });
}

// dark-stained rough-sawn posts (tile 0.30 x 1.2 m)
function postTex(ctx) {
  return tex(ctx, 128, 512, (g, w, h) => woodGrain(g, w, h, [92, 67, 57], 41, { streaks: 200, contrast: 0.22, knots: 3 }),
    { repeat: [1 / 0.30, 1 / 1.2] });
}

// ---- registration -----------------------------------------------------------------------------------------------------
export function register(lib) {
  const day = (t) => t !== 'dusk';

  // black powder-coated lantern body; candle sleeve (white by day, the light source at dusk)
  lib.add('fx_lantern_frame', { color: 0x202124, roughness: 0.45, metalness: 0.35 });
  lib.add('fx_lamp_base', { color: 0x1a1a1b, roughness: 0.5, metalness: 0.4 });
  lib.add('fx_lamp_glow', { color: 0xf1ece2, roughness: 0.45, emissive: 0xffc070, emissiveDay: 0.04, emissiveDusk: 9.0 });

  // clear lantern glass: nearly invisible by day but for its reflections (kept at full strength over the
  // see-through part), filled with the lamp's warm scatter at dusk
  let glass = null;
  const glassTime = (t) => {
    if (!glass) return;
    glass.emissiveIntensity = day(t) ? 0.0 : 2.6;
    glass.opacity = day(t) ? 0.10 : 0.30;
  };
  lib.add('fx_lantern_glass', (ctx) => {
    const T = ctx.THREE;
    glass = new T.MeshStandardMaterial({
      color: 0xdfeaec, roughness: 0.04, metalness: 0.0, transparent: true, opacity: 0.10, side: T.DoubleSide,
      depthWrite: false, emissive: 0xffb866, emissiveMap: glowTex(ctx), emissiveIntensity: 0.0, envMapIntensity: 4.0,
    });
    glass.onBeforeCompile = (sh) => {
      sh.fragmentShader = sh.fragmentShader.replace('#include <opaque_fragment>', `
        vec3 fxAdd = totalSpecular + totalEmissiveRadiance;
        float fxA = clamp( diffuseColor.a + ( 1.0 - diffuseColor.a ) * clamp( max( fxAdd.r, max( fxAdd.g, fxAdd.b ) ), 0.0, 1.0 ), 0.0, 1.0 );
        outgoingLight = ( totalDiffuse * diffuseColor.a + fxAdd ) / max( fxA, 1e-4 );
        diffuseColor.a = fxA;
        #include <opaque_fragment>`);
    };
    glass.customProgramCacheKey = () => 'fx_lantern_glass';
    glassTime(ctx.time);
    return glass;
  }, { glass: true });
  lib.onTime(glassTime);

  // step lights (dark bronze plate, hooded slot) and recessed down-lights
  lib.add('fx_step_plate', { color: 0x3a322c, roughness: 0.5, metalness: 0.55 });
  lib.add('fx_step_glow', { color: 0x4a4540, roughness: 0.6, emissive: 0xffc98a, emissiveDay: 0.0, emissiveDusk: 5.0 });
  lib.add('fx_can_trim', { color: 0xdcdbd6, roughness: 0.6 });
  lib.add('fx_can_glow', { color: 0x5b5955, roughness: 0.5, emissive: 0xffd6a4, emissiveDay: 0.0, emissiveDusk: 6.5 });

  // PV modules: dark glass over blue-black cells
  lib.add('fx_solar_glass', (ctx) => new ctx.THREE.MeshStandardMaterial({
    map: solarTex(ctx), roughness: 0.12, metalness: 0.0, envMapIntensity: 1.25,
  }));
  lib.add('fx_solar_frame', { color: 0x141517, roughness: 0.45, metalness: 0.6 });

  // skylights, flashings, vents
  lib.add('fx_skylight_glass', (ctx) => {
    const m = new ctx.THREE.MeshStandardMaterial({ color: 0x7f97a6, roughness: 0.05, metalness: 0.0, envMapIntensity: 1.8 });
    return m;
  }, { noShadow: true });
  lib.add('fx_skylight_frame', { color: 0xe6e7e6, roughness: 0.5, metalness: 0.15 });
  lib.add('fx_flashing', { color: 0x2e3033, roughness: 0.5, metalness: 0.55 });
  lib.add('fx_vent_pipe', { color: 0x3f4146, roughness: 0.7 });
  lib.add('fx_vent_lead', { color: 0x8f9398, roughness: 0.55, metalness: 0.35 });
  lib.add('fx_spark_screen', { color: 0xa9adb0, roughness: 0.4, metalness: 0.7 });

  // pergola accessories
  lib.add('fx_heater_body', { color: 0x27282a, roughness: 0.45, metalness: 0.5 });
  lib.add('fx_heater_face', (ctx) => new ctx.THREE.MeshStandardMaterial({
    map: heaterTex(ctx), roughness: 0.32, metalness: 0.75,
  }));
  lib.add('fx_speaker', { color: 0x171819, roughness: 0.85 });

  // fence: stained posts, the picket band (cut-out), black gate hardware
  lib.add('fx_fence_post', (ctx) => new ctx.THREE.MeshStandardMaterial({ map: postTex(ctx), roughness: 0.9, metalness: 0 }));
  lib.add('fx_fence_pickets', (ctx) => {
    const T = ctx.THREE, t = picketTex(ctx);
    return new T.MeshStandardMaterial({
      map: t.map, alphaMap: t.mask, alphaTest: 0.36, alphaToCoverage: true, side: T.DoubleSide, roughness: 0.86, metalness: 0,
    });
  }, { cutout: true });
  lib.add('fx_iron', { color: 0x161616, roughness: 0.6, metalness: 0.5 });
}
