// Sky, sun, image-based lighting, fog and clouds for the three.js renderer.
// Ported from the current renderer (same physics, same constants):
//   - single-scattering Rayleigh + Mie sky precompute: js/shaders/common.js SKY_PRECOMPUTE_FS (Re 6360 km, Ra 6420 km,
//     bR (5.8, 13.5, 33.1)e-6, Hr 7994 m, Hm 1200 m, ozone bO x1.8, g 0.76, 32 view / 8 light steps)
//   - sun colour from the transmittance and the ambient terms from a CPU evaluation of the same model
//     (js/env/atmo/sky_model.js skyAmbientCPU / modelLight)
//   - sky dome with sun disk and cirrus: js/shaders/env.js SKY_FS
//   - reflection/IBL environment with clouds and a ground below the horizon: env.js ENV_FS, here rendered into a
//     cube by PMREMGenerator.fromScene (GGX-prefiltered IBL instead of box-filtered equirect mips)
// Environment step 3 (2026-11-05, docs/research/environment_impl.md §3; spec docs/research/environment_spec.md §4, §7):
//   - fog: the piecewise-constant σ(y) slabs of EnvState (spec §4.4 / §7.3; js/env/atmo/sky_model.js renderSlabs) with
//     the exact optical depth along each view ray, no see-through cap (the old 0.97 opacity cap and the 0.004 m⁻¹
//     density cap are gone); in-scatter = the blurred sky (clear air) blended to the ambient sky radiance in dense fog;
//     the background (sky) is attenuated by the non-cloud slabs (and by a cloud slab the camera is in)
//   - clouds: up to 6 reported layers (spec §4.5 / §7.4), each a density d = smoothstep(thr ± 0.08, n) of the app's
//     cloud texture at two octaves, thr solved on the CPU so that the area mean of d is the layer's de-summed coverage;
//     layers based below 5,000 ft are drawn as planes (cloudSlabMaterial; base and top), higher layers in the sky
//     shader; the sun (or Moon) light is multiplied by the product of (1 − d) over the layers above the point (each
//     layer casts its own shadow)
//   - Moon disc with its phase from the geometry (sphere normal · Sun direction seen from the Moon), C171 luminance;
//     night-sky floor from EnvState (natural ÷ D + artificial, spec §4.9); no stars (Q12 default: takram stars.bin not
//     shipped, no starfield with verified open terms)
//   - lightning: a glow around the flash direction and a sky-wide brightening for the flash envelope (spec §4.6, I)
//   - pre-exposure (spec §7.2): the sky textures are rendered at sunI × pre (preBake) and sampled × preRel = pre /
//     preBake; every light uniform below is set CPU-side already × pre (js/three/renderer3.js)
import { THREE, TSL } from './lib.js';
import { skyAmbientCPU, modelLight, SIGMA_CLEAR, CLEAR_TOP, MAX_SLABS, MAX_CLOUD_LAYERS, CLOUD_RAMP, CLOUD_DETAIL, MOON_TERM } from '../env/atmo/sky_model.js';
export { skyAmbientCPU };
const { Fn, uniform, vec2, vec3, vec4, float, uv, texture, dot, exp, pow, sqrt, max, min, mix, smoothstep, clamp, normalize, length, abs, sin, cos, acos, atan, Loop, If, Break, select, positionWorld, positionWorldDirection, cameraPosition, fract, step } = TSL;
const PI = Math.PI;

// ---------------------------------------------------------------- atmosphere constants (SKY_PRECOMPUTE_FS)
const Re = 6360e3, Ra = 6420e3, Hr = 7994.0, Hm = 1200.0;
const bR = vec3(5.8e-6, 13.5e-6, 33.1e-6), bO = vec3(0.65e-6, 1.881e-6, 0.085e-6).mul(1.8);
// background path length cap inside a slab the camera is in, for near-horizontal rays (m; beyond it the sky model's
// own aerial perspective holds, I)
const BG_MAX = 50000.0;

const raySphere = Fn(([ro, rd, r]) => {
  const b = dot(ro, rd), c = dot(ro, ro).sub(r.mul(r)); const d = b.mul(b).sub(c).toVar();
  const out = vec2(-1.0).toVar();
  If(d.greaterThanEqual(0.0), () => { const s = sqrt(d); out.assign(vec2(b.negate().sub(s), b.negate().add(s))); });
  return out;
}).setLayout({ name: 'raySphere', type: 'vec2', inputs: [{ name: 'ro', type: 'vec3' }, { name: 'rd', type: 'vec3' }, { name: 'r', type: 'float' }] });

// old renderer equirect convention (dirToEquirect in common.js): u = atan(d.x, -d.z)/2pi + 0.5, v = acos(d.y)/pi
export const dirToEquirect = (d) => vec2(atan(d.x, d.z.negate()).div(2 * PI).add(0.5), acos(clamp(d.y, -1.0, 1.0)).div(PI));
const equirectToDir = (u) => { const phi = u.x.sub(0.5).mul(2 * PI), th = u.y.mul(PI); return vec3(sin(th).mul(sin(phi)), cos(th), sin(th).mul(cos(phi)).negate()); };

export class Sky {
  constructor(engine, { cloudTex, noiseTex, baseRes = 1024 }) {
    this.E = engine; this.cloudTex = cloudTex; this.noiseTex = noiseTex;
    const V3 = () => uniform(new THREE.Vector3()), V4 = () => uniform(new THREE.Vector4());
    this.u = {
      sunDir: uniform(new THREE.Vector3(0, 1, 0)), sunColor: uniform(new THREE.Color(1, 1, 1)), skyUp: uniform(new THREE.Color(0.3, 0.4, 0.6)),
      skyHorizon: uniform(new THREE.Color(0.5, 0.55, 0.6)), ground: uniform(new THREE.Color(0.1, 0.1, 0.1)),
      fog: uniform(new THREE.Vector4(0.0001, 1 / 700, 1, 0.97)), cloud: uniform(new THREE.Vector4(0.12, 1500, 14000, 0.5)), cloudWind: uniform(new THREE.Vector2(0, 0)),
      time: uniform(0), night: uniform(0), skyFloor: uniform(new THREE.Color(0, 0, 0)), mie: uniform(21e-6), sunI: uniform(20), camH: uniform(30), skyClouds: uniform(1), refPos: uniform(new THREE.Vector3(0, 60, 0)),
      // environment step 3
      preRel: uniform(1),                                   // pre / preBake for the sky textures
      lightDir: uniform(new THREE.Vector3(0, 1, 0)),        // direction of the directional light (Sun, or the Moon at night): cloud shadows
      nSlabs: uniform(0), slab: Array.from({ length: MAX_SLABS }, V4), clearTop0: uniform(-1e6), // slab: (y0, y1, σ, isCloud)
      fogCol: uniform(new THREE.Color(0.5, 0.5, 0.5)), fogDense: uniform(0), sunGlow: uniform(1),
      nLayers: uniform(0), layA: Array.from({ length: MAX_CLOUD_LAYERS }, V4), layB: Array.from({ length: MAX_CLOUD_LAYERS }, V4), layC: Array.from({ length: MAX_CLOUD_LAYERS }, V4),
      // layA: (base y, thr, opacity, period m); layB: (off u, off v, drift x, drift z m/s); layC: (sun transmittance above, sky-shader layer 1/0, thickness m, 0)
      moonDir: V3(), moonRight: V3(), moonUp: V3(), moonSun: V3(), moonRad: uniform(0.0045), moonL: uniform(0),
      flash: uniform(new THREE.Vector4(0, 1, 0, 0)), flashCol: uniform(new THREE.Color(0, 0, 0)),
      wetFilm: uniform(0), wetPore: uniform(0), puddle: uniform(0),
    };
    const W = baseRes, H = baseRes / 2;
    const rtOpts = { type: THREE.HalfFloatType, depthBuffer: false, generateMipmaps: false, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, wrapS: THREE.RepeatWrapping, wrapT: THREE.ClampToEdgeWrapping };
    this.base = new THREE.RenderTarget(W, H, rtOpts); this.base.texture.wrapS = THREE.RepeatWrapping;
    this.small = new THREE.RenderTarget(64, 32, rtOpts); this.small.texture.wrapS = THREE.RepeatWrapping;
    this.preMat = new THREE.NodeMaterial(); this.preMat.colorNode = this.precomputeNode(); this.preMat.depthTest = false; this.preMat.depthWrite = false;
    this.quad = new THREE.QuadMesh(this.preMat);
    this.baseTex = texture(this.base.texture); this.smallTex = texture(this.small.texture);
    // IBL scene: inside-out sphere whose colour is the ENV_FS composition for its direction
    this.envScene = new THREE.Scene();
    const envMat = new THREE.MeshBasicNodeMaterial({ side: THREE.BackSide, depthWrite: false });
    envMat.colorNode = this.envColor(TSL.normalize(TSL.positionLocal)); envMat.fog = false;
    this.envScene.add(new THREE.Mesh(new THREE.SphereGeometry(10, 48, 24), envMat));
    this.pmrem = null; this.envRT = null;
    this.light = null; this.rawLight = null; this.pre = 1; this.preBake = 1; this.layers = [];
  }
  // ------------------------------------------------------------ cloud layers
  // density of layer k at world xz (0..1, x opacity): n = c(uv) + DETAIL (c(7.3 uv + c0) - 0.5), uv = (xz - drift t)/P + off
  layerDensity(k, xz) {
    const U = this.u; const A = U.layA[k], B = U.layB[k];
    const q = xz.sub(B.zw.mul(U.time)).div(A.w).add(B.xy);
    const n = texture(this.cloudTex, q).r.add(texture(this.cloudTex, q.mul(7.3).add(vec2(0.43, 0.71))).r.sub(0.5).mul(CLOUD_DETAIL));
    return smoothstep(A.y.sub(CLOUD_RAMP), A.y.add(CLOUD_RAMP), n).mul(A.z);
  }
  // transmittance of the directional light (Sun / Moon / flash) through every layer above wp (product of 1 - d)
  cloudShadow(wp) {
    const U = this.u;
    return Fn(() => {
      const r = float(1.0).toVar();
      for (let k = 0; k < MAX_CLOUD_LAYERS; k++) {
        If(U.nLayers.greaterThan(k + 0.5).and(wp.y.lessThan(U.layA[k].x)), () => {
          const t = U.layA[k].x.sub(wp.y).div(max(U.lightDir.y, 0.05));
          r.mulAssign(float(1.0).sub(this.layerDensity(k, wp.xz.add(U.lightDir.xz.mul(t)))));
        });
      }
      return r;
    })();
  }
  // ------------------------------------------------------------ SKY_PRECOMPUTE_FS
  precomputeNode() {
    const U = this.u;
    return Fn(() => {
      const rd = equirectToDir(uv()).toVar();
      const ro = vec3(0, float(Re).add(U.camH), 0);
      const rdd = rd.toVar();
      If(rdd.y.lessThan(0.02), () => { rdd.y.assign(float(0.02).add(float(0.02).sub(rdd.y).mul(0.02))); rdd.assign(normalize(rdd)); });
      const ta = raySphere(ro, rdd, float(Ra)); const tmax = ta.y.toVar();
      const tg = raySphere(ro, rdd, float(Re)); If(tg.x.greaterThan(0.0), () => { tmax.assign(min(tmax, tg.x)); });
      const bM = vec3(U.mie);
      const N = 32; const seg = tmax.div(N).toVar(); const t = float(0).toVar();
      const sumR = vec3(0).toVar(), sumM = vec3(0).toVar(), msR = vec3(0).toVar(), msM = vec3(0).toVar();
      const odR = float(0).toVar(), odM = float(0).toVar();
      const mu = dot(rdd, U.sunDir).toVar(); const g = 0.76;
      const pR = float(3.0 / (16.0 * PI)).mul(mu.mul(mu).add(1.0));
      const pM = float(3.0 / (8.0 * PI)).mul(float((1 - g * g)).mul(mu.mul(mu).add(1.0))).div(float(2.0 + g * g).mul(pow(float(1 + g * g).sub(mu.mul(2 * g)), 1.5)));
      Loop(N, () => {
        const p = ro.add(rdd.mul(t.add(seg.mul(0.5)))).toVar(); const h = length(p).sub(Re);
        const hr = exp(h.negate().div(Hr)).mul(seg), hm = exp(h.negate().div(Hm)).mul(seg);
        odR.addAssign(hr); odM.addAssign(hm);
        const tl = raySphere(p, U.sunDir, float(Ra)); const sl = tl.y.div(8.0).toVar();
        const odlR = float(0).toVar(), odlM = float(0).toVar(); const ok = float(1).toVar();
        Loop(8, ({ i }) => {
          const q = p.add(U.sunDir.mul(sl.mul(float(i).add(0.5)))); const hq = length(q).sub(Re).toVar();
          If(hq.lessThan(0.0), () => { ok.assign(0.0); Break(); });
          odlR.addAssign(exp(hq.negate().div(Hr)).mul(sl)); odlM.addAssign(exp(hq.negate().div(Hm)).mul(sl));
        });
        If(ok.greaterThan(0.5), () => {
          const tau = bR.add(bO).mul(odR.add(odlR)).add(bM.mul(1.1).mul(odM.add(odlM)));
          const att = exp(tau.negate()); sumR.addAssign(att.mul(hr)); sumM.addAssign(att.mul(hm));
        });
        const tv = exp(bR.add(bO).mul(odR).add(bM.mul(1.1).mul(odM)).negate()); msR.addAssign(tv.mul(hr)); msM.addAssign(tv.mul(hm));
        t.addAssign(seg);
      });
      const col = sumR.mul(bR).mul(pR).add(sumM.mul(bM).mul(pM)).mul(U.sunI).toVar();
      // multiple-scattering stand-in: as SKY_PRECOMPUTE_FS by day; below the horizon it decays with the sun's depression
      // (0.08 x exp(0.8 x elevation in deg)) instead of stopping at -3.8 deg (review round 1, dusk re-check). Since
      // environment step 3 the absolute level follows USNO Circular 171 through sunI (renderer3 / sky_model.js
      // sunCalibration: the model was 6x too bright at Sun -4...-9 deg)
      const sunUp = select(U.sunDir.y.greaterThanEqual(0.0), clamp(U.sunDir.y.mul(1.2).add(0.08), 0.0, 1.0), exp(U.sunDir.y.mul(45.8)).mul(0.08));
      col.addAssign(msR.mul(bR).add(msM.mul(bM).mul(0.9)).mul(U.sunI).mul(0.055).mul(sunUp));
      return vec4(col, 1.0);
    })();
  }
  // ------------------------------------------------------------ cloud layers in the sky shader (layers >= 5,000 ft)
  // composited from the highest to the lowest along rd from ro (below the layer). Lighting as SKY_FS cloudLayer: sun x
  // self-shadow x HG + sky; the sun term x the transmittance of the layers above (layC.x, area mean)
  cloudLayers(ro, rd, bg) {
    const U = this.u;
    return Fn(() => {
      const out = vec3(bg).toVar();
      const mu = dot(rd, U.sunDir); const g = 0.55;
      const hg = float(1 - g * g).div(pow(float(1 + g * g).sub(mu.mul(2 * g)), 1.5)).mul(0.25);
      for (let k = MAX_CLOUD_LAYERS - 1; k >= 0; k--) {
        const A = U.layA[k], C = U.layC[k];
        If(U.nLayers.greaterThan(k + 0.5).and(C.y.greaterThan(0.5)).and(rd.y.greaterThan(0.002)).and(ro.y.lessThan(A.x)), () => {
          const t = A.x.sub(ro.y).div(rd.y).toVar();
          const p = ro.xz.add(rd.xz.mul(t)).toVar();
          const d = this.layerDensity(k, p).toVar();
          const d2 = this.layerDensity(k, p.add(U.sunDir.xz.div(max(U.sunDir.y, 0.2)).mul(180.0)));
          const selfSh = exp(d2.mul(-2.2));
          const lit = U.sunColor.mul(C.x).mul(selfSh.mul(0.55).add(0.08)).mul(hg.mul(1.8).add(0.6)).mul(0.45).add(U.skyUp.mul(0.55)).add(U.skyHorizon.mul(0.15)).mul(mix(1.0, 0.72, d)).toVar();
          // lightning: cloud bodies lit from inside / below around the flash direction (I)
          lit.addAssign(U.flashCol.mul(U.flash.w).mul(pow(max(dot(rd, U.flash.xyz), 0.0), 6.0).mul(3.0).add(0.4)));
          const alpha = smoothstep(0.0, 0.6, d).mul(float(1.0).sub(smoothstep(18000.0, 60000.0, t)));
          lit.assign(mix(out, lit, exp(t.mul(-0.00004))));
          out.assign(mix(out, lit, alpha));
        });
      }
      return out;
    })();
  }
  cirrus(ro, rd) {
    const U = this.u; const nt = this.noiseTex;
    return Fn(() => {
      const r = float(0).toVar();
      If(rd.y.greaterThan(0.01), () => {
        const t = float(9000.0).sub(ro.y).div(rd.y); const p = ro.xz.add(rd.xz.mul(t));
        const q = vec2(p.x.mul(0.00008).add(p.y.mul(0.00003)), p.y.mul(0.0004).sub(p.x.mul(0.0001)));
        const n = texture(nt, q.mul(0.6).add(vec2(U.time.mul(0.0004), 0.0))).b.mul(0.7).add(texture(nt, q.mul(2.3)).g.mul(0.3));
        const s = texture(nt, p.mul(0.000021).add(0.3)).b;
        r.assign(smoothstep(0.55, 0.85, n).mul(smoothstep(0.55, 0.72, s)).mul(float(1.0).sub(smoothstep(30000.0, 90000.0, t))));
      });
      return r;
    })();
  }
  // Moon disc (radiance, sky units x pre) along rd: a sphere lit by the Sun direction seen from the Moon
  // (js/env/atmo/sky_model.js moonShade is the JS mirror the A-MOON gate checks)
  moonDisc(rd) {
    const U = this.u;
    return Fn(() => {
      const out = vec3(0).toVar();
      const mu = dot(rd, U.moonDir);
      If(U.moonL.greaterThan(0.0).and(mu.greaterThan(cos(U.moonRad))), () => {
        const x = dot(rd, U.moonRight).div(sin(U.moonRad)), y = dot(rd, U.moonUp).div(sin(U.moonRad));
        const r2 = x.mul(x).add(y.mul(y));
        const z = sqrt(max(float(1.0).sub(r2), 0.0));
        const n = U.moonRight.mul(x).add(U.moonUp.mul(y)).sub(U.moonDir.mul(z));
        const lit = smoothstep(-MOON_TERM, MOON_TERM, dot(n, U.moonSun));
        const edge = float(1.0).sub(smoothstep(0.96, 1.0, r2)); // anti-aliased rim
        out.assign(vec3(1.0, 0.96, 0.9).mul(U.moonL).mul(lit).mul(edge));
      });
      return out;
    })();
  }
  // background transmittance along rd from the camera: non-cloud slabs (excess over the sky model's clear air) and the
  // cloud slab the camera is in (spec §7.3, I)
  bgTransmittance(ro, rd) {
    const U = this.u;
    return Fn(() => {
      const tau = float(0).toVar(); const cy = ro.y;
      for (let k = 0; k < MAX_SLABS; k++) {
        const S = U.slab[k];
        If(U.nSlabs.greaterThan(k + 0.5), () => {
          const y0 = k === 0 ? float(-1e6) : S.x;
          const inside = cy.greaterThanEqual(y0).and(cy.lessThan(S.y));
          const use = S.w.lessThan(0.5).or(inside);
          const sig = select(S.w.lessThan(0.5), max(S.z.sub(SIGMA_CLEAR), 0.0), S.z);
          // path length inside [y0, y1] for a ray to infinity
          const up = max(S.y.sub(max(cy, y0)), 0.0).div(max(rd.y, 1e-4));
          const dn = max(min(cy, S.y).sub(y0), 0.0).div(max(rd.y.negate(), 1e-4));
          const len = min(select(rd.y.greaterThanEqual(0.0), up, dn), BG_MAX);
          If(use, () => { tau.addAssign(sig.mul(len)); });
        });
      }
      return exp(tau.negate());
    })();
  }
  fogInscatter(rd) {
    const U = this.u;
    const hd = normalize(vec3(rd.x, max(rd.y, 0.0).mul(0.5).add(0.035), rd.z));
    const clearIn = this.skyEnvBlur(hd);
    const mu = dot(rd, U.sunDir); const g = 0.75;
    const hg = float(1 - g * g).div(pow(float(1 + g * g).sub(mu.mul(2 * g)), 1.5)).div(4 * PI);
    return mix(clearIn, U.fogCol, U.fogDense).add(U.sunColor.mul(hg).mul(U.sunGlow).mul(0.08)).add(U.flashCol.mul(U.flash.w).mul(0.3));
  }
  // sky seen along direction rd from the camera (background): the composition below + the sun disk, attenuated by the
  // fog slabs towards the in-scatter colour
  backgroundNode() {
    const U = this.u;
    return Fn(() => {
      const rd = normalize(positionWorldDirection).toVar();
      const col = this.skyAlong(cameraPosition, rd).toVar();
      const mu = dot(rd, U.sunDir); const sunR = 0.99998918;
      // sun disc above the horizon only (below it the terrain / bay hides it; the ground of the sky dome is no surface)
      If(mu.greaterThan(sunR).and(rd.y.greaterThan(-0.002)), () => { const r = sqrt(max(0.0, float(1.0).sub(float(1.0).sub(mu).div(1.0 - sunR)))); col.addAssign(U.sunColor.mul(900.0).mul(r.mul(0.6).add(0.4)).mul(this.cloudShadowSky(cameraPosition, rd))); });
      const T = this.bgTransmittance(cameraPosition, rd);
      return mix(this.fogInscatter(rd), col, T);
    })();
  }
  // transmittance of the sky-shader layers along rd (for the sun disc: a cloud in front of it hides it)
  cloudShadowSky(ro, rd) {
    const U = this.u;
    return Fn(() => {
      const r = float(1.0).toVar();
      for (let k = 0; k < MAX_CLOUD_LAYERS; k++) {
        If(U.nLayers.greaterThan(k + 0.5).and(rd.y.greaterThan(0.002)).and(ro.y.lessThan(U.layA[k].x)), () => {
          const t = U.layA[k].x.sub(ro.y).div(rd.y);
          r.mulAssign(float(1.0).sub(this.layerDensity(k, ro.xz.add(rd.xz.mul(t)))));
        });
      }
      return r;
    })();
  }
  // sky radiance seen from ro along rd: precomputed sky, cirrus (only when no layer is reported), the Moon, the cloud
  // layers, the night floor (EnvState natural + artificial luminance, a little stronger and warmer towards the horizon,
  // where the Bay Area's light pollution sits: inferred) and, below the horizon, the horizon colour fading to the
  // ground. Used for the background (ro = camera) and for the water's reflections (ro = the water point).
  skyAlong(ro, rdIn) {
    const U = this.u;
    return Fn(() => {
      const rd = normalize(rdIn).toVar();
      const ru = normalize(vec3(rd.x, max(rd.y, 0.0), rd.z));
      const col = this.baseTex.sample(dirToEquirect(ru)).rgb.mul(U.preRel).toVar();
      const mu = dot(ru, U.sunDir);
      const ci = this.cirrus(ro, ru).mul(0.22).mul(select(U.nLayers.greaterThan(0.5), float(0.0), float(1.0)));
      col.assign(mix(col, U.sunColor.mul(0.25).mul(pow(max(mu, 0.0), 8.0).mul(2.0).add(1.0)).add(U.skyUp.mul(0.9)), ci));
      const hz = pow(float(1.0).sub(ru.y), 6.0);
      col.assign(max(col, U.skyFloor.mul(mix(vec3(1.0), vec3(2.2, 1.9, 1.5), hz))));
      col.addAssign(this.moonDisc(rd));
      col.assign(this.cloudLayers(ro, ru, col));
      If(rd.y.lessThan(0.0), () => { col.assign(mix(col, U.ground.mul(0.9), smoothstep(0.0, -0.35, rd.y))); });
      return col;
    })();
  }
  // ENV_FS: environment seen from refPos along d (clouds from below, ground/water below the horizon)
  envColor(d) {
    const U = this.u;
    return Fn(() => {
      const rd = normalize(d).toVar();
      const col = this.baseTex.sample(dirToEquirect(rd)).rgb.mul(U.preRel).toVar();
      col.assign(max(col, U.skyFloor)); // night: natural + artificial sky luminance (EnvState nightSky)
      If(rd.y.greaterThan(0.0), () => {
        // every layer from below (low slab layers too: the IBL is seen from below the deck)
        const mu = dot(rd, U.sunDir); const g = 0.55; const hg = float(1 - g * g).div(pow(float(1 + g * g).sub(mu.mul(2 * g)), 1.5)).mul(0.25);
        for (let k = MAX_CLOUD_LAYERS - 1; k >= 0; k--) {
          const A = U.layA[k], C = U.layC[k];
          If(U.nLayers.greaterThan(k + 0.5).and(U.refPos.y.lessThan(A.x)), () => {
            const t = A.x.sub(U.refPos.y).div(max(rd.y, 0.01)).toVar(); const p = U.refPos.xz.add(rd.xz.mul(t));
            const dd = this.layerDensity(k, p); const d2 = this.layerDensity(k, p.add(U.sunDir.xz.div(max(U.sunDir.y, 0.2)).mul(180.0)));
            const lit = U.sunColor.mul(C.x).mul(exp(d2.mul(-2.2)).mul(0.55).add(0.08)).mul(hg.mul(1.8).add(0.6)).mul(0.45).add(U.skyUp.mul(0.55)).add(U.skyHorizon.mul(0.15));
            const a = smoothstep(0.0, 0.6, dd).mul(float(1.0).sub(smoothstep(18000.0, 60000.0, t)));
            col.assign(mix(col, mix(col, lit, exp(t.mul(-0.00004))), a));
          });
        }
      });
      If(rd.y.lessThan(0.0), () => {
        const hz = max(this.baseTex.sample(vec2(dirToEquirect(rd).x, 0.49)).rgb.mul(U.preRel), U.skyFloor);
        col.assign(mix(hz, U.ground.mul(0.9), smoothstep(0.0, -0.35, rd.y)));
      });
      return col;
    })();
  }
  // low cloud layer k as a plane at its base (top = false: seen from below) or its top (top = true: seen from above),
  // following the camera (centre uniform), 40 km half extent. Shading as the old CLOUD_FS slab (js/shaders/env.js).
  cloudSlabMaterial(k, top, centre) {
    const U = this.u; const A = U.layA[k], C = U.layC[k];
    const m = new THREE.MeshBasicNodeMaterial({ transparent: true, depthWrite: false, side: THREE.DoubleSide });
    const p = TSL.attribute('position', 'vec3');
    const H = top ? A.x.add(C.z) : A.x;
    const extent = 40000.0;
    m.positionNode = vec3(p.x.mul(extent).add(centre.x), H, p.z.mul(extent).add(centre.y));
    const core = Fn(() => {
      const wp = positionWorld; const V = normalize(cameraPosition.sub(wp));
      const d = this.layerDensity(k, wp.xz).toVar();
      const d2 = this.layerDensity(k, wp.xz.add(U.sunDir.xz.div(max(U.sunDir.y, 0.25)).mul(70.0)));
      const mu = dot(V.negate(), U.sunDir); const g = 0.6; const hg = float(1 - g * g).div(pow(float(1 + g * g).sub(mu.mul(2 * g)), 1.5)).mul(0.08);
      const col = vec3(0).toVar(); const vis = float(0).toVar();
      if (!top) {
        If(cameraPosition.y.lessThan(H), () => {
          const od = float(1.0).sub(d);
          col.assign(U.skyUp.mul(0.5).add(U.ground.mul(0.3)).add(U.sunColor.mul(C.x).mul(od.mul(od).mul(0.14).add(0.035)).mul(hg.mul(6.0).add(0.5))));
          col.mulAssign(mix(float(1.0), float(0.82), d)); vis.assign(1.0);
        });
      } else {
        If(cameraPosition.y.greaterThan(H), () => {
          const shade = exp(d2.mul(-1.4));
          col.assign(U.sunColor.mul(C.x).mul(shade.mul(0.3).add(0.08)).mul(hg.mul(3.0).add(0.8)).add(U.skyUp.mul(0.8))); vis.assign(1.0);
        });
      }
      col.addAssign(U.flashCol.mul(U.flash.w).mul(0.6));
      const a = d.mul(vis).mul(float(1.0).sub(smoothstep(20000.0, 38000.0, length(wp.xz.sub(cameraPosition.xz)))));
      return vec4(col, a);
    }).once();
    m.colorNode = core().rgb; m.opacityNode = core().a;
    return m;
  }
  // blurred sky radiance for fog in-scatter (skyEnv(hd, 5.0) in applyFog): the 64x32 precompute, bilinear
  skyEnvBlur(d) { return this.smallTex.sample(dirToEquirect(normalize(d))).rgb.mul(this.u.preRel); }
  // fog along camera -> fragment through the slabs (exact piecewise optical depth; js/env/atmo/sky_model.js slabTau is
  // the JS mirror the A-FOG gate checks); returns TSL.fog(colour, factor)
  fogNode() {
    const U = this.u;
    const color = Fn(() => {
      const dv = positionWorld.sub(cameraPosition); const dist = length(dv); const rd = dv.div(max(dist, 1e-3));
      return this.fogInscatter(rd);
    })();
    const factor = Fn(() => {
      const a = cameraPosition, b = positionWorld;
      const L = length(b.sub(a)).toVar();
      const ylo = min(a.y, b.y).toVar(), yhi = max(a.y, b.y).toVar(); const h = yhi.sub(ylo).toVar();
      const tau = float(0).toVar();
      const frac = (y0, y1) => select(h.lessThan(1e-3), select(a.y.greaterThanEqual(y0).and(a.y.lessThan(y1)), float(1.0), float(0.0)), max(min(yhi, y1).sub(max(ylo, y0)), 0.0).div(max(h, 1e-3)));
      for (let k = 0; k < MAX_SLABS; k++) {
        const S = U.slab[k];
        If(U.nSlabs.greaterThan(k + 0.5), () => { tau.addAssign(S.z.mul(frac(k === 0 ? float(-1e6) : S.x, S.y)).mul(L)); });
      }
      tau.addAssign(frac(U.clearTop0, float(CLEAR_TOP)).mul(SIGMA_CLEAR).mul(L));
      return float(1.0).sub(exp(tau.negate()));
    })();
    return TSL.fog(color, factor);
  }
  // ------------------------------------------------------------ per-environment setup (Renderer.setupSky)
  // light terms on the CPU (synchronous, so js/live/app.js can post-process R.light right after setupSky as it does with
  // the old renderer); the GPU sky textures are rendered by renderSky() once the renderer is ready
  static lightFor(env) {
    const m = modelLight(env.sunDir, env.mie, env.sunI);
    const E = m.sunColor.map((s, k) => s * Math.max(env.sunDir[1], 0) + m.skyUp[k] * Math.PI);
    const ground = E.map(e => e * 0.16 / Math.PI);
    if (env.physical) return { sunDir: env.sunDir, sunColor: m.sunColor, skyUp: m.skyUp, skyHorizon: m.skyHorizon.map((v, k) => v * 0.6 + ground[k] * 0.4), ground };
    const cc = env.cloud ? env.cloud[0] : 0;
    const direct = m.sunColor.map(s => s * (1 - 0.55 * cc));
    return { sunDir: env.sunDir, sunColor: direct, skyUp: m.skyUp.map(v => v * (1 + 0.3 * cc)), skyHorizon: m.skyHorizon.map((v, k) => v * 0.6 + ground[k] * 0.4), ground };
  }
  setEnv(env) {
    const U = this.u;
    // the sky textures are rendered at sunI x pre (renderSky); until then the samples keep preRel = pre / the old preBake
    U.sunDir.value.set(...env.sunDir); U.mie.value = env.mie; U.sunI.value = env.sunI * this.pre; U.camH.value = 30; this._preNext = this.pre;
    U.fog.value.set(...env.fog); U.cloud.value.set(...env.cloud); U.cloudWind.value.set(...env.cloudWind); U.refPos.value.set(...(env.refPos || [0, 60, 0]));
    U.skyClouds.value = env.slab ? 0 : 1;
  }
  // fog slabs [{y0, y1, sigma, isCloud}] (sorted), in-scatter colour for dense fog (raw sky units) and its weight
  setSlabs(slabs, fogCol, dense) {
    const U = this.u; const n = Math.min(MAX_SLABS, slabs.length);
    for (let k = 0; k < MAX_SLABS; k++) { const s = slabs[k]; if (k < n) U.slab[k].value.set(s.y0, s.y1, s.sigma, s.isCloud ? 1 : 0); else U.slab[k].value.set(0, 0, 0, 0); }
    U.nSlabs.value = n; U.clearTop0.value = n ? slabs[n - 1].y1 : -1e6;
    this.rawFog = fogCol; U.fogDense.value = dense;
    this._applyPre();
  }
  // cloud layers (js/env/atmo/sky_model.js cloudLayers) + the mean sun transmittance above each
  setLayers(layers) {
    const U = this.u; const n = Math.min(MAX_CLOUD_LAYERS, layers.length); this.layers = layers.slice(0, n);
    for (let k = 0; k < MAX_CLOUD_LAYERS; k++) {
      const l = layers[k];
      if (k < n) {
        let Tab = 1; for (let j = k + 1; j < n; j++) Tab *= 1 - layers[j].own;
        U.layA[k].value.set(l.baseY, l.thr, l.opacity, l.scale); U.layB[k].value.set(l.off[0], l.off[1], l.drift[0], l.drift[1]); U.layC[k].value.set(Tab, l.slab ? 0 : 1, l.thickness, 0);
      } else { U.layA[k].value.set(1e7, 2, 0, 1000); U.layB[k].value.set(0, 0, 0, 0); U.layC[k].value.set(1, 0, 0, 0); }
    }
    U.nLayers.value = n;
  }
  setMoon(D) {
    const U = this.u;
    if (!D) { this.rawMoonL = 0; this._applyPre(); return; }
    U.moonDir.value.set(...D.dir); U.moonRight.value.set(...D.right); U.moonUp.value.set(...D.up); U.moonSun.value.set(...D.sunFromMoon); U.moonRad.value = D.rad;
    this.rawMoonL = D.units; this._applyPre();
  }
  // lightning: direction (unit, towards the flash), level 0..1 and the flash colour (raw sky units)
  setFlash(dir, level, col) { const U = this.u; U.flash.value.set(dir[0], dir[1], dir[2], level); this.rawFlash = col; this._applyPre(); }
  renderSky(renderer) {
    const prevRT = renderer.getRenderTarget();
    renderer.setRenderTarget(this.base); this.quad.render(renderer);
    renderer.setRenderTarget(this.small); this.quad.render(renderer);
    renderer.setRenderTarget(prevRT);
    if (this._preNext != null) { this.preBake = this._preNext; this.u.preRel.value = this.pre / this.preBake; }
  }
  // light uniforms (raw sky units); the shader sees them x pre
  applyLight(L) { this.rawLight = { sunColor: L.sunColor.slice(), skyUp: L.skyUp.slice(), skyHorizon: L.skyHorizon.slice(), ground: L.ground.slice(), skyFloor: (L.skyFloor || [0, 0, 0]).slice() }; this._applyPre(); }
  setPre(pre) { this.pre = pre; this.u.preRel.value = pre / (this.preBake || 1); this._applyPre(); }
  _applyPre() {
    const U = this.u, p = this.pre, L = this.rawLight;
    if (L) { U.sunColor.value.setRGB(...L.sunColor.map(v => v * p)); U.skyUp.value.setRGB(...L.skyUp.map(v => v * p)); U.skyHorizon.value.setRGB(...L.skyHorizon.map(v => v * p)); U.ground.value.setRGB(...L.ground.map(v => v * p)); U.skyFloor.value.setRGB(...L.skyFloor.map(v => v * p)); }
    if (this.rawFog) U.fogCol.value.setRGB(...this.rawFog.map(v => v * p));
    U.moonL.value = (this.rawMoonL || 0) * p;
    if (this.rawFlash) U.flashCol.value.setRGB(...this.rawFlash.map(v => v * p)); else U.flashCol.value.setRGB(0, 0, 0);
  }
  // GGX-prefiltered environment (PMREM) of the ENV_FS composition (rendered at the current pre-exposure)
  updateEnvironment(renderer, scene) {
    if (!this.pmrem) this.pmrem = new THREE.PMREMGenerator(renderer);
    const rt = this.pmrem.fromScene(this.envScene, 0, 0.1, 100, { size: 256, renderTarget: this.envRT || null });
    this.envRT = rt; scene.environment = rt.texture; this.preEnv = this.pre;
    return rt.texture;
  }
}
