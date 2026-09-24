// Sky, sun, image-based lighting and aerial perspective for the three.js renderer.
// Ported from the current renderer (same physics, same constants):
//   - single-scattering Rayleigh + Mie sky precompute: js/shaders/common.js SKY_PRECOMPUTE_FS (Re 6360 km, Ra 6420 km,
//     bR (5.8, 13.5, 33.1)e-6, Hr 7994 m, Hm 1200 m, ozone bO x1.8, g 0.76, 32 view / 8 light steps)
//   - sun colour from the transmittance: js/renderer.js sunTransmittance (imported, not copied)
//   - ambient terms (sky-up, horizon, ground bounce) from a 64x32 readback: js/renderer.js Renderer.setupSky
//   - sky dome with sun disk, cirrus and the METAR cloud layer: js/shaders/env.js SKY_FS
//   - reflection/IBL environment with clouds and a ground below the horizon: env.js ENV_FS, here rendered into a
//     cube by PMREMGenerator.fromScene (GGX-prefiltered IBL instead of box-filtered equirect mips)
//   - exponential height fog with sky-coloured in-scatter and Mie sun glow: common.js applyFog, as scene.fogNode
import { THREE, TSL } from './lib.js';
import { sunTransmittance } from '../renderer.js';
const { Fn, uniform, vec2, vec3, vec4, float, uv, texture, dot, exp, pow, sqrt, max, min, mix, smoothstep, clamp, normalize, length, abs, sin, cos, acos, atan, Loop, If, Break, select, positionWorld, positionWorldDirection, cameraPosition, fract } = TSL;
const PI = Math.PI;

// ---------------------------------------------------------------- atmosphere constants (SKY_PRECOMPUTE_FS)
const Re = 6360e3, Ra = 6420e3, Hr = 7994.0, Hm = 1200.0;
const bR = vec3(5.8e-6, 13.5e-6, 33.1e-6), bO = vec3(0.65e-6, 1.881e-6, 0.085e-6).mul(1.8);

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
    this.u = {
      sunDir: uniform(new THREE.Vector3(0, 1, 0)), sunColor: uniform(new THREE.Color(1, 1, 1)), skyUp: uniform(new THREE.Color(0.3, 0.4, 0.6)),
      skyHorizon: uniform(new THREE.Color(0.5, 0.55, 0.6)), ground: uniform(new THREE.Color(0.1, 0.1, 0.1)),
      fog: uniform(new THREE.Vector4(0.0001, 1 / 700, 1, 0.97)), cloud: uniform(new THREE.Vector4(0.12, 1500, 14000, 0.5)), cloudWind: uniform(new THREE.Vector2(0, 0)),
      time: uniform(0), night: uniform(0), skyFloor: uniform(new THREE.Color(0, 0, 0)), mie: uniform(21e-6), sunI: uniform(20), camH: uniform(30), skyClouds: uniform(1), refPos: uniform(new THREE.Vector3(0, 60, 0)),
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
    this.light = null;
  }
  // ------------------------------------------------------------ cloud helpers (common.js cloudDensityAt / cloudShadow)
  cloudDensityAt(xz) {
    const U = this.u; const c = U.cloud;
    const p = xz.add(U.cloudWind.mul(U.time)).div(c.z);
    const n = texture(this.cloudTex, p).r;
    return smoothstep(float(1.0).sub(c.x), float(1.0).sub(c.x).add(0.28), n);
  }
  cloudShadow(wp) {
    const U = this.u;
    return Fn(() => {
      const r = float(1.0).toVar();
      If(U.cloud.x.greaterThan(0.001), () => {
        const t = U.cloud.y.sub(wp.y).div(max(U.sunDir.y, 0.05));
        const p = wp.xz.add(U.sunDir.xz.mul(t));
        r.assign(float(1.0).sub(U.cloud.w.mul(this.cloudDensityAt(p))));
      });
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
      const sunUp = clamp(U.sunDir.y.mul(1.2).add(0.08), 0.0, 1.0);
      col.addAssign(msR.mul(bR).add(msM.mul(bM).mul(0.9)).mul(U.sunI).mul(0.055).mul(sunUp));
      return vec4(col, 1.0);
    })();
  }
  // ------------------------------------------------------------ SKY_FS: cloud layer and cirrus
  cloudLayer(ro, rd, bg) {
    const U = this.u;
    return Fn(() => {
      const out = vec3(bg).toVar();
      If(U.cloud.x.greaterThan(0.001).and(rd.y.greaterThan(0.002)).and(ro.y.lessThan(U.cloud.y)), () => {
        const t = U.cloud.y.sub(ro.y).div(rd.y).toVar();
        const p = ro.xz.add(rd.xz.mul(t)).toVar();
        const d = this.cloudDensityAt(p).mul(texture(this.noiseTex, p.mul(0.00021).add(U.time.mul(0.0004))).b.mul(0.6).add(0.7)).toVar();
        d.assign(clamp(d, 0.0, 1.0));
        const d2 = this.cloudDensityAt(p.add(U.sunDir.xz.div(max(U.sunDir.y, 0.2)).mul(180.0)));
        const selfSh = exp(d2.mul(-2.2));
        const mu = dot(rd, U.sunDir); const g = 0.55;
        const hg = float(1 - g * g).div(pow(float(1 + g * g).sub(mu.mul(2 * g)), 1.5)).mul(0.25);
        const lit = U.sunColor.mul(selfSh.mul(0.55).add(0.08)).mul(hg.mul(1.8).add(0.6)).mul(0.45).add(U.skyUp.mul(0.55)).add(U.skyHorizon.mul(0.15)).mul(mix(1.0, 0.72, d)).toVar();
        const alpha = smoothstep(0.0, 0.6, d).mul(float(1.0).sub(smoothstep(18000.0, 60000.0, t)));
        lit.assign(mix(bg, lit, exp(t.mul(-0.00004))));
        out.assign(mix(bg, lit, alpha));
      });
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
  // sky seen along direction rd from the camera (background)
  backgroundNode() {
    const U = this.u;
    return Fn(() => {
      const rd = normalize(positionWorldDirection).toVar();
      const col = this.baseTex.sample(dirToEquirect(rd)).rgb.toVar();
      const mu = dot(rd, U.sunDir); const sunR = 0.99998918;
      If(mu.greaterThan(sunR), () => { const r = sqrt(max(0.0, float(1.0).sub(float(1.0).sub(mu).div(1.0 - sunR)))); col.addAssign(U.sunColor.mul(900.0).mul(r.mul(0.6).add(0.4))); });
      const ci = this.cirrus(cameraPosition, rd).mul(0.22).mul(float(1.0).sub(U.cloud.x.mul(0.6)));
      col.assign(mix(col, U.sunColor.mul(0.25).mul(pow(max(mu, 0.0), 8.0).mul(2.0).add(1.0)).add(U.skyUp.mul(0.9)), ci));
      If(U.skyClouds.greaterThan(0.5), () => { col.assign(this.cloudLayer(cameraPosition, rd, col)); });
      return col;
    })();
  }
  // ENV_FS: environment seen from refPos along d (clouds from below, ground/water below the horizon)
  envColor(d) {
    const U = this.u;
    return Fn(() => {
      const rd = normalize(d).toVar();
      const col = this.baseTex.sample(dirToEquirect(rd)).rgb.toVar();
      If(rd.y.greaterThan(0.0).and(U.cloud.x.greaterThan(0.001)), () => {
        const t = U.cloud.y.sub(U.refPos.y).div(max(rd.y, 0.01)).toVar(); const p = U.refPos.xz.add(rd.xz.mul(t));
        const dd = this.cloudDensityAt(p); const d2 = this.cloudDensityAt(p.add(U.sunDir.xz.div(max(U.sunDir.y, 0.2)).mul(180.0)));
        const mu = dot(rd, U.sunDir); const g = 0.55; const hg = float(1 - g * g).div(pow(float(1 + g * g).sub(mu.mul(2 * g)), 1.5)).mul(0.25);
        const lit = U.sunColor.mul(exp(d2.mul(-2.2)).mul(0.55).add(0.08)).mul(hg.mul(1.8).add(0.6)).mul(0.45).add(U.skyUp.mul(0.55)).add(U.skyHorizon.mul(0.15));
        const a = smoothstep(0.0, 0.6, dd).mul(float(1.0).sub(smoothstep(18000.0, 60000.0, t)));
        col.assign(mix(col, mix(col, lit, exp(t.mul(-0.00004))), a));
      });
      col.assign(max(col, U.skyFloor)); // night: moon / city-glow floor (js/live/app.js applyEnv)
      If(rd.y.lessThan(0.0), () => {
        const hz = max(this.baseTex.sample(vec2(dirToEquirect(rd).x, 0.49)).rgb, U.skyFloor);
        col.assign(mix(hz, U.ground.mul(0.9), smoothstep(0.0, -0.35, rd.y)));
      });
      return col;
    })();
  }
  // blurred sky radiance for fog in-scatter (skyEnv(hd, 5.0) in applyFog): the 64x32 precompute, bilinear
  skyEnvBlur(d) { return this.smallTex.sample(dirToEquirect(normalize(d))).rgb; }
  // applyFog as a fog node: returns { color, factor } for TSL.fog()
  fogNode() {
    const U = this.u;
    const color = Fn(() => {
      const dv = positionWorld.sub(cameraPosition); const dist = length(dv); const rd = dv.div(max(dist, 1e-3));
      const hd = normalize(vec3(rd.x, max(rd.y, 0.0).mul(0.5).add(0.035), rd.z));
      const inscat = this.skyEnvBlur(hd).toVar();
      const mu = dot(rd, U.sunDir); const g = 0.75;
      const hg = float(1 - g * g).div(pow(float(1 + g * g).sub(mu.mul(2 * g)), 1.5)).div(4 * PI);
      return inscat.add(U.sunColor.mul(hg).mul(U.fog.z).mul(0.08));
    })();
    const factor = Fn(() => {
      const dv = positionWorld.sub(cameraPosition); const dist = length(dv).toVar(); const rd = dv.div(max(dist, 1e-3)).toVar();
      const a = U.fog.x, b = U.fog.y; const ch = cameraPosition.y;
      const fogAmt = float(0).toVar();
      If(abs(rd.y).greaterThan(1e-4), () => { fogAmt.assign(a.mul(exp(b.negate().mul(ch))).mul(float(1.0).sub(exp(b.negate().mul(rd.y).mul(dist)))).div(b.mul(rd.y))); })
        .Else(() => { fogAmt.assign(a.mul(exp(b.negate().mul(ch))).mul(dist)); });
      const T = max(exp(fogAmt.negate()), float(1.0).sub(U.fog.w));
      return float(1.0).sub(T);
    })();
    return TSL.fog(color, factor);
  }
  // ------------------------------------------------------------ per-environment setup (Renderer.setupSky)
  // light terms on the CPU (synchronous, so js/live/app.js can post-process R.light right after setupSky as it does with
  // the old renderer); the GPU sky textures are rendered by renderSky() once the renderer is ready
  static lightFor(env) {
    const { up, hz } = skyAmbientCPU(env.sunDir, env.mie, env.sunI, 30);
    const T = sunTransmittance(env.sunDir, env.mie, 30);
    const sunColor = T.map(t => t * env.sunI);
    const E = sunColor.map((s, k) => s * Math.max(env.sunDir[1], 0) + up[k] * Math.PI);
    const ground = E.map(e => e * 0.16 / Math.PI);
    const cc = env.cloud ? env.cloud[0] : 0;
    const direct = sunColor.map(s => s * (1 - 0.55 * cc));
    return { sunDir: env.sunDir, sunColor: direct, skyUp: up.map(v => v * (1 + 0.3 * cc)), skyHorizon: hz.map((v, k) => v * 0.6 + ground[k] * 0.4), ground };
  }
  setEnv(env) {
    const U = this.u;
    U.sunDir.value.set(...env.sunDir); U.mie.value = env.mie; U.sunI.value = env.sunI; U.camH.value = 30;
    U.fog.value.set(...env.fog); U.cloud.value.set(...env.cloud); U.cloudWind.value.set(...env.cloudWind); U.refPos.value.set(...(env.refPos || [0, 60, 0]));
    U.skyClouds.value = env.slab ? 0 : 1;
  }
  renderSky(renderer) {
    const prevRT = renderer.getRenderTarget();
    renderer.setRenderTarget(this.base); this.quad.render(renderer);
    renderer.setRenderTarget(this.small); this.quad.render(renderer);
    renderer.setRenderTarget(prevRT);
  }
  applyLight(L) {
    const U = this.u; U.sunColor.value.setRGB(...L.sunColor); U.skyUp.value.setRGB(...L.skyUp); U.skyHorizon.value.setRGB(...L.skyHorizon); U.ground.value.setRGB(...L.ground);
  }
  // GGX-prefiltered environment (PMREM) of the ENV_FS composition
  updateEnvironment(renderer, scene) {
    if (!this.pmrem) this.pmrem = new THREE.PMREMGenerator(renderer);
    const rt = this.pmrem.fromScene(this.envScene, 0, 0.1, 100, { size: 256, renderTarget: this.envRT || null });
    this.envRT = rt; scene.environment = rt.texture;
    return rt.texture;
  }
}

// CPU evaluation of SKY_PRECOMPUTE_FS on a 32x16 equirect grid and the ambient integration of js/renderer.js
// setupSky (sky-up: cosine-weighted upper hemisphere; horizon: 0 < d.y < 0.5 band). Same constants and step counts
// as the shader; the grid is coarser than the old 64x32 readback (the averages differ by < 1 %).
export function skyAmbientCPU(sunDir, mie, sunI, camH = 30) {
  const NX = 32, NY = 16; const bRc = [5.8e-6, 13.5e-6, 33.1e-6], bOc = [0.65e-6 * 1.8, 1.881e-6 * 1.8, 0.085e-6 * 1.8];
  const rs = (ro, rd, r) => { const b = ro[0] * rd[0] + ro[1] * rd[1] + ro[2] * rd[2], c = ro[0] * ro[0] + ro[1] * ro[1] + ro[2] * ro[2] - r * r; const d = b * b - c; if (d < 0) return [-1, -1]; const q = Math.sqrt(d); return [-b - q, -b + q]; };
  const g = 0.76; let up = [0, 0, 0], wu = 0, hz = [0, 0, 0], wh = 0;
  for (let y = 0; y < NY; y++) for (let x = 0; x < NX; x++) {
    const th = (y + 0.5) / NY * Math.PI, phi = ((x + 0.5) / NX - 0.5) * 2 * Math.PI;
    const d = [Math.sin(th) * Math.sin(phi), Math.cos(th), -Math.sin(th) * Math.cos(phi)];
    if (d[1] <= 0) continue;
    let rd = d.slice(); if (rd[1] < 0.02) { rd[1] = 0.02 + (0.02 - rd[1]) * 0.02; const l = Math.hypot(...rd); rd = rd.map(v => v / l); }
    const ro = [0, Re + camH, 0];
    let tmax = rs(ro, rd, Ra)[1]; const tg = rs(ro, rd, Re); if (tg[0] > 0) tmax = Math.min(tmax, tg[0]);
    const N = 32, seg = tmax / N; let t = 0; const sumR = [0, 0, 0], sumM = [0, 0, 0], msR = [0, 0, 0], msM = [0, 0, 0]; let odR = 0, odM = 0;
    const mu = rd[0] * sunDir[0] + rd[1] * sunDir[1] + rd[2] * sunDir[2];
    const pR = 3 / (16 * Math.PI) * (1 + mu * mu), pM = 3 / (8 * Math.PI) * ((1 - g * g) * (1 + mu * mu)) / ((2 + g * g) * Math.pow(1 + g * g - 2 * g * mu, 1.5));
    for (let i = 0; i < N; i++) {
      const p = [ro[0] + rd[0] * (t + seg * 0.5), ro[1] + rd[1] * (t + seg * 0.5), ro[2] + rd[2] * (t + seg * 0.5)]; const h = Math.hypot(...p) - Re;
      const hr = Math.exp(-h / Hr) * seg, hm = Math.exp(-h / Hm) * seg; odR += hr; odM += hm;
      const sl = rs(p, sunDir, Ra)[1] / 8; let odlR = 0, odlM = 0, ok = true;
      for (let j = 0; j < 8; j++) { const q = [p[0] + sunDir[0] * sl * (j + 0.5), p[1] + sunDir[1] * sl * (j + 0.5), p[2] + sunDir[2] * sl * (j + 0.5)]; const hq = Math.hypot(...q) - Re; if (hq < 0) { ok = false; break; } odlR += Math.exp(-hq / Hr) * sl; odlM += Math.exp(-hq / Hm) * sl; }
      for (let k = 0; k < 3; k++) {
        if (ok) { const att = Math.exp(-((bRc[k] + bOc[k]) * (odR + odlR) + mie * 1.1 * (odM + odlM))); sumR[k] += att * hr; sumM[k] += att * hm; }
        const tv = Math.exp(-((bRc[k] + bOc[k]) * odR + mie * 1.1 * odM)); msR[k] += tv * hr; msM[k] += tv * hm;
      }
      t += seg;
    }
    const sunUp = Math.min(1, Math.max(0, sunDir[1] * 1.2 + 0.08));
    const col = [0, 1, 2].map(k => (sumR[k] * bRc[k] * pR + sumM[k] * mie * pM) * sunI + (msR[k] * bRc[k] + msM[k] * mie * 0.9) * sunI * 0.055 * sunUp);
    const sa = Math.sin(th); const w = d[1] * sa;
    for (let k = 0; k < 3; k++) up[k] += col[k] * w; wu += w;
    if (d[1] < 0.5) { for (let k = 0; k < 3; k++) hz[k] += col[k] * sa; wh += sa; }
  }
  return { up: up.map(v => v / wu), hz: hz.map(v => v / wh) };
}
