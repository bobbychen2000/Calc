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
import { FIELD_LAYERS, LAMP_H, FLOOD_COLOR } from './flood.js';
import { GROUND_Y } from '../geo.js';
import { skyAmbientCPU, modelLight, SIGMA_CLEAR, CLEAR_TOP, MAX_SLABS, MAX_CLOUD_LAYERS, CLOUD_RAMP, CLOUD_DETAIL, MOON_TERM, PATCH_WAVES, PATCH_RAMP, LOBE_RAMP_M, HORIZ_SAMPLES, PATCH_R_M, PATCH_FADE_M, patchThreshold } from '../env/atmo/sky_model.js';
export { skyAmbientCPU };
const { Fn, uniform, vec2, vec3, vec4, float, uv, texture, texture3D, dot, exp, pow, sqrt, max, min, mix, smoothstep, clamp, normalize, length, abs, sin, cos, acos, atan, floor, Loop, If, Break, select, positionWorld, positionWorldDirection, cameraPosition, fract, step } = TSL;
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
  constructor(engine, { cloudTex, noiseTex, baseRes = 1024, horizSamples = HORIZ_SAMPLES, maxSlabs = MAX_SLABS, maxLayers = MAX_CLOUD_LAYERS }) {
    this.E = engine; this.cloudTex = cloudTex; this.noiseTex = noiseTex; this.horizN = horizSamples;
    // shader loop counts (review look1-12: the environment's GPU cost was the same on every tier): the phone tier
    // compiles 4 slabs / 4 cloud layers (the lowest ones: setSlabs / setLayers keep them), the others 6
    this.nS = Math.min(MAX_SLABS, maxSlabs); this.nL = Math.min(MAX_CLOUD_LAYERS, maxLayers);
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
      // horizontal structure of the lowest slab (review truth1-6; js/env/atmo/sky_model.js horizDelta is the mirror):
      // hPatch = (σ_patch − σ0, threshold, on, σ0), lobe[k] = (azimuth rad, σ_k − σ0, r0 m, top y)
      hOn: uniform(0), hPatch: uniform(new THREE.Vector4(0, 2, 0, 0)), nLobes: uniform(0), lobe: Array.from({ length: 4 }, V4),
      // apron floodlight in-scatter in the fog (review look1-1): floodFog = σ of the lowest slab while the floods are on
      // (0 = off), floodI = the floods' intensity (renderer3: on x LAMP_M x pre, as js/three/flood.js FloodLight),
      // floodRect = the field's box (x0, z0, width, depth)
      floodFog: uniform(0), floodI: uniform(0), floodRect: uniform(new THREE.Vector4(0, 0, 1, 1)),
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
      for (let k = 0; k < this.nL; k++) {
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
      for (let k = this.nL - 1; k >= 0; k--) {
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
  // ---- horizontal structure of the lowest slab: extra extinction at world point p (patch mask, sector lobes; review
  // truth1-6). CPU mirror: js/env/atmo/sky_model.js horizDelta / patchNoise / lobeWeight.
  horizDelta(p) {
    const U = this.u;
    let n = float(0.5);
    for (const [l, t, f] of PATCH_WAVES) n = n.add(sin(p.x.mul(Math.cos(t * PI / 180)).add(p.z.mul(Math.sin(t * PI / 180))).mul(2 * PI / l).add(f)).mul(0.125));
    const az = atan(p.x, p.z.negate()); const r = length(p.xz);
    const pd = select(U.hPatch.z.greaterThan(0.5), smoothstep(U.hPatch.y.sub(PATCH_RAMP), U.hPatch.y.add(PATCH_RAMP), n).mul(float(1.0).sub(smoothstep(PATCH_R_M, PATCH_R_M + PATCH_FADE_M, r))).mul(U.hPatch.x), float(0.0));
    let ld = float(0.0);
    for (let k = 0; k < 4; k++) {
      const Lb = U.lobe[k];
      const d0 = az.sub(Lb.x); const dd = d0.sub(floor(d0.add(PI).div(2 * PI)).mul(2 * PI));
      const ang = select(abs(dd).lessThan(PI / 4), cos(dd.mul(2.0)), float(0.0));
      const ramp = select(Lb.z.greaterThan(0.0), smoothstep(Lb.z, Lb.z.add(LOBE_RAMP_M), r), float(1.0));
      ld = ld.add(select(U.nLobes.greaterThan(k + 0.5).and(p.y.lessThan(Lb.w)), ang.mul(ramp).mul(Lb.y), float(0.0)));
    }
    return max(max(pd, ld), float(SIGMA_CLEAR).sub(U.hPatch.w));
  }
  // extra optical depth of the horizontal structure along a -> a + dir * len, over the part below the lowest slab's top
  // (stratified samples; this.horizN per tier)
  horizTau(a, dir, len) {
    const U = this.u; const N = this.horizN;
    return Fn(() => {
      const out = float(0).toVar();
      If(U.hOn.greaterThan(0.5), () => {
        const y1 = U.slab[0].y; const dy = dir.y.mul(len);
        const sc = y1.sub(a.y).div(select(abs(dy).lessThan(1e-6), float(1e-6), dy));
        const s0 = select(dy.lessThan(0.0), clamp(sc, 0.0, 1.0), float(0.0)), s1 = select(dy.greaterThan(0.0), clamp(sc, 0.0, 1.0), select(a.y.lessThan(y1).or(dy.lessThan(0.0)), float(1.0), float(0.0)));
        const span = max(s1.sub(s0), 0.0);
        If(span.greaterThan(0.0), () => {
          const sum = float(0).toVar();   // (jittered per pixel / frame as floodScatter; the CPU mirror takes the midpoints)
          const jit = TSL.interleavedGradientNoise(TSL.screenCoordinate.xy.add(fract(U.time.mul(5.31)).mul(64.0)));
          for (let k = 0; k < N; k++) sum.addAssign(this.horizDelta(a.add(dir.mul(len.mul(s0.add(span.mul(jit.add(k).div(N))))))));
          out.assign(sum.div(N).mul(len).mul(span));
        });
      });
      return out;
    })();
  }
  // ---- apron floodlight in-scatter (review look1-1: at night the fog received no light from the floods and the night-fog
  // views were black). Single scattering of the floodlight field (js/three/flood.js: the vector irradiance E_v and the
  // horizontal spread S of every mast, 3-D texture over the aprons, receiver heights 2-23 m) along the view ray below the
  // lamp height: L = ∫ σ F(s) p T(s) ds with the scalar irradiance F = |(E_v.y, S)| (exact for one lamp), an isotropic
  // phase p = 1/4π (I: fog droplets scatter forward, g ~ 0.85, so the side-lit glow may be over-estimated by ~2x),
  // T(s) = the lowest slab's extinction from where the ray enters it (+ the slabs above it the camera looks through),
  // FLOOD_SAMPLES stratified samples over at most 4 mean free paths. Multiple scattering is not modelled (I).
  // setFlood(light) must be called before fogNode() / backgroundNode() are built (renderer3 _buildStatic).
  setFlood(light) { this.flood = light; this.u.floodRect.value.copy(light.rect); }
  floodField(p) {
    const L = this.flood, r = this.u.floodRect; const NL = FIELD_LAYERS.length, H0 = FIELD_LAYERS[0], H1 = FIELD_LAYERS[NL - 1];
    const u = p.x.sub(r.x).div(r.z), v = p.z.sub(r.y).div(r.w);
    const inside = step(0.0, u).mul(step(u, 1.0)).mul(step(0.0, v)).mul(step(v, 1.0));
    const hgt = p.y.sub(GROUND_Y);
    const w = clamp(hgt, H0, H1).sub(H0).div(H1 - H0).mul((NL - 1) / NL).add(0.5 / NL);
    const above = float(1.0).sub(smoothstep(LAMP_H - 4.0, LAMP_H - 0.5, hgt));
    const f = texture3D(L.fieldTex, vec3(u, v, w)).level(0);   // explicit LOD: also sampled in the rain's vertex stage
    return length(vec2(max(f.y, 0.0), max(f.w, 0.0))).mul(inside).mul(above);
  }
  // (sample offsets jittered per pixel and frame: interleaved gradient noise, resolved by TRAA; the fixed stratified
  // offsets drew horizontal bands across the background in the first render, fix1_E9_squall_gate, 2026-11-05)
  floodScatter(a, dir, len, N = 6) {
    const U = this.u; if (!this.flood) return vec3(0.0);
    return Fn(() => {
      const out = vec3(0).toVar();
      If(U.floodFog.greaterThan(0.0).and(U.floodI.greaterThan(0.0)), () => {
        const sig = U.floodFog, yTop = min(float(GROUND_Y + LAMP_H), U.slab[0].y);   // inside the lowest slab only (e.g. MIFG: 6 ft)
        const dy = dir.y.mul(len); const dys = select(abs(dy).lessThan(1e-6), float(1e-6), dy);
        const sc = yTop.sub(a.y).div(dys);
        const s0 = select(dy.lessThan(0.0), clamp(sc, 0.0, 1.0), float(0.0));
        const s1 = select(dy.greaterThan(0.0), clamp(sc, 0.0, 1.0), select(a.y.lessThan(yTop).or(dy.lessThan(0.0)), float(1.0), float(0.0)));
        // entry into the lowest slab (the camera may be above it) and the optical depth of the slabs above it on the way
        const y1 = U.slab[0].y; const sIn = select(a.y.greaterThan(y1).and(dy.lessThan(0.0)), clamp(y1.sub(a.y).div(dys), 0.0, 1.0), float(0.0));
        const tauAbove = float(0).toVar();
        for (let k = 1; k < this.nS; k++) {
          const S = U.slab[k];
          If(U.nSlabs.greaterThan(k + 0.5).and(a.y.greaterThan(S.x)), () => { tauAbove.addAssign(S.z.mul(max(min(a.y, S.y).sub(max(y1, S.x)), 0.0)).div(max(abs(dir.y), 0.02))); });
        }
        const sEnd = min(s1, max(s0, sIn).add(min(float(4.0).div(sig), 1500.0).div(len)));   // <= 4 mean free paths, <= 1.5 km
        const span = max(sEnd.sub(s0), 0.0);
        If(span.greaterThan(0.0), () => {
          const sum = float(0).toVar();
          const jit = TSL.interleavedGradientNoise(TSL.screenCoordinate.xy.add(fract(U.time.mul(7.13)).mul(64.0)));
          for (let k = 0; k < N; k++) {
            const sk = s0.add(span.mul(jit.add(k).div(N)));
            const p = a.add(dir.mul(len.mul(sk)));
            sum.addAssign(this.floodField(p).mul(exp(sig.mul(len).mul(max(sk.sub(sIn), 0.0)).add(tauAbove).negate())));
          }
          out.assign(vec3(...FLOOD_COLOR).mul(U.floodI).mul(sum.mul(span.mul(len)).div(N)).mul(sig).div(4 * PI));
        });
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
      for (let k = 0; k < this.nS; k++) {
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
      // horizontal structure (patches, sector lobes, the gap bank) along the first 20 km of the ray (I)
      tau.addAssign(this.horizTau(ro, rd, float(20000.0)));
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
      return mix(this.fogInscatter(rd), col, T).add(this.floodScatter(cameraPosition, rd, float(3000.0), 8));
    })();
  }
  // transmittance of the sky-shader layers along rd (for the sun disc: a cloud in front of it hides it)
  cloudShadowSky(ro, rd) {
    const U = this.u;
    return Fn(() => {
      const r = float(1.0).toVar();
      for (let k = 0; k < this.nL; k++) {
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
      // night-sky floor with the light-pollution dome toward the horizon: up to 5 x the zenith value, warm, within ~10°
      // (review look1-7: the 2.2 x gain left the horizon sky black above the lit land; city sky glow rises steeply toward
      // the horizon, the factor is I / NV, Q14 parameter with the 3 mcd/m² zenith default)
      const hz = pow(float(1.0).sub(ru.y), 8.0);
      col.assign(max(col, U.skyFloor.mul(mix(vec3(1.0), vec3(5.0, 4.2, 3.2), hz))));
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
        for (let k = this.nL - 1; k >= 0; k--) {
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
          // (review look1-11: a marine-stratus base looked warm: the direct-sun term now fades out where the deck is
          // closed (x od: the base of a thick deck sees only multiply scattered, neutral light) and the ground bounce is
          // its luminance (the concrete's warm tint does not survive the diffuse bounce into the base, I))
          const gL = dot(U.ground, vec3(0.2126, 0.7152, 0.0722));
          col.assign(U.skyUp.mul(0.5).add(vec3(gL).mul(0.3)).add(U.sunColor.mul(C.x).mul(od.mul(od).mul(0.14).add(od.mul(0.035))).mul(hg.mul(6.0).add(0.5))));
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
    const factor = Fn(() => {
      const a = cameraPosition, b = positionWorld;
      const L = length(b.sub(a)).toVar();
      const ylo = min(a.y, b.y).toVar(), yhi = max(a.y, b.y).toVar(); const h = yhi.sub(ylo).toVar();
      const tau = float(0).toVar();
      const frac = (y0, y1) => select(h.lessThan(1e-3), select(a.y.greaterThanEqual(y0).and(a.y.lessThan(y1)), float(1.0), float(0.0)), max(min(yhi, y1).sub(max(ylo, y0)), 0.0).div(max(h, 1e-3)));
      for (let k = 0; k < this.nS; k++) {
        const S = U.slab[k];
        If(U.nSlabs.greaterThan(k + 0.5), () => { tau.addAssign(S.z.mul(frac(k === 0 ? float(-1e6) : S.x, S.y)).mul(L)); });
      }
      tau.addAssign(frac(U.clearTop0, float(CLEAR_TOP)).mul(SIGMA_CLEAR).mul(L));
      tau.addAssign(this.horizTau(a, b.sub(a).div(max(L, 1e-3)), L));   // patches / sector lobes (review truth1-6)
      return float(1.0).sub(exp(tau.negate()));
    }).once()();
    // in-scatter colour: the sky / ambient fog colour, plus the floodlight in-scatter along the ray (radiance L_f; the
    // fog blend multiplies the colour by the factor 1 − T, so the colour carries L_f / (1 − T))
    const color = Fn(() => {
      const dv = positionWorld.sub(cameraPosition); const dist = length(dv); const rd = dv.div(max(dist, 1e-3));
      return this.fogInscatter(rd).add(this.floodScatter(cameraPosition, rd, dist).div(max(factor, 1e-5)));
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
    const U = this.u; const n = Math.min(this.nS, slabs.length);
    for (let k = 0; k < MAX_SLABS; k++) { const s = slabs[k]; if (k < n) U.slab[k].value.set(s.y0, s.y1, s.sigma, s.isCloud ? 1 : 0); else U.slab[k].value.set(0, 0, 0, 0); }
    U.nSlabs.value = n; U.clearTop0.value = n ? slabs[n - 1].y1 : -1e6;
    // horizontal structure of the lowest slab (js/env/state.js horizontalFor)
    const H = n ? slabs[0].horiz : null, s0 = n ? slabs[0].sigma : 0;
    U.hOn.value = H ? 1 : 0;
    if (H && H.patch) U.hPatch.value.set(H.patch.sigma - s0, patchThreshold(H.patch.cover), 1, s0); else U.hPatch.value.set(0, 2, 0, s0);
    const Lb = H ? (H.lobes || []).slice(0, 4) : []; U.nLobes.value = Lb.length;
    for (let k = 0; k < 4; k++) { const l = Lb[k]; if (l) U.lobe[k].value.set(l.az * PI / 180, l.sigma - s0, l.r0, l.top); else U.lobe[k].value.set(0, 0, 0, -1e6); }
    this.rawFog = fogCol; U.fogDense.value = dense;
    this._applyPre();
  }
  // cloud layers (js/env/atmo/sky_model.js cloudLayers) + the mean sun transmittance above each
  setLayers(layers) {
    const U = this.u; const n = Math.min(this.nL, layers.length); this.layers = layers.slice(0, n);
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
