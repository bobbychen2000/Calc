import { gl, Program, FBO, texture, fullscreen } from './gl.js';
import { m4, v3, clamp } from './math.js';
import { SKY_PRECOMPUTE_FS, FS_VERT } from './shaders/common.js';
import { POST_VS, MBLUR_FS, DOWN_FS, UP_FS, FINAL_FS } from './shaders/post.js';
import { SKY_VS, SKY_FS, ENV_FS } from './shaders/env.js';

const HF = () => ({ internal: gl.RGBA16F, format: gl.RGBA, type: gl.HALF_FLOAT });
const SHADOW_FS = `void main(){}`;

// Atmosphere constants (must match shader)
const Re = 6360e3, Ra = 6420e3, bR = [5.8e-6, 13.5e-6, 33.1e-6], Hr = 7994, Hm = 1200;
export function sunTransmittance(sunDir, mie, camH = 50) {
  // optical depth from camera to top of atmosphere along sunDir
  const ro = [0, Re + camH, 0]; const rd = sunDir;
  const b = v3.dot(ro, rd), c = v3.dot(ro, ro) - Ra * Ra; const t = -b + Math.sqrt(b * b - c);
  const N = 64; let odR = 0, odM = 0; const seg = t / N;
  for (let i = 0; i < N; i++) {
    const p = v3.add(ro, v3.mul(rd, seg * (i + 0.5))); const h = v3.len(p) - Re;
    if (h < 0) return [0, 0, 0];
    odR += Math.exp(-h / Hr) * seg; odM += Math.exp(-h / Hm) * seg;
  }
  const bO = [0.65e-6 * 1.8, 1.881e-6 * 1.8, 0.085e-6 * 1.8];
  return bR.map((br, k) => Math.exp(-((br + bO[k]) * odR + mie * 1.1 * odM)));
}

export class Renderer {
  constructor(W, H, opts = {}) {
    this.W = W; this.H = H; this.samples = opts.msaa ?? 4; this.shadowRes = opts.shadowRes || 4096;
    this.ms = new FBO(W, H, [HF(), HF()], 'rb', this.samples);
    this.resColor = new FBO(W, H, [HF()], null);
    this.resAux = new FBO(W, H, [HF()], null);
    this.mb = new FBO(W, H, [HF()], null);
    this.down = []; this.up = [];
    let w = W, h = H;
    for (let i = 0; i < 6; i++) { w = Math.max(1, w >> 1); h = Math.max(1, h >> 1); this.down.push(new FBO(w, h, [HF()], null)); this.up.push(new FBO(w, h, [HF()], null)); }
    this.final = new FBO(W, H, [{ internal: gl.RGBA8 }], null);
    this.shadowFBO = [0, 1, 2].map(() => new FBO(this.shadowRes, this.shadowRes, [], 'shadow'));
    this.progs = {};
    this.post = {
      mblur: new Program(POST_VS, MBLUR_FS), down: new Program(POST_VS, DOWN_FS), up: new Program(POST_VS, UP_FS), final: new Program(POST_VS, FINAL_FS),
    };
    this.skyProg = new Program(SKY_VS, SKY_FS);
    this.overlayTex = texture(W, H, { internal: gl.RGBA8 });
    this.pixels = null;
    this.frameUniforms = {};
    this.prev = null;
  }
  addProgram(name, vs, fs, defines = {}) {
    this.progs[name] = { main: new Program(vs, fs, defines), shadow: new Program(vs, SHADOW_FS, Object.assign({ SHADOW_PASS: 1 }, defines)) };
  }

  // --- Sky precompute per lighting setup ---
  setupSky(env) {
    const { sunDir, mie, sunI } = env;
    if (!this.skyBase) {
      this.skyBase = new FBO(1024, 512, [HF()], null);
      this.skyPre = new Program(FS_VERT, SKY_PRECOMPUTE_FS);
      this.envProg = new Program(FS_VERT, ENV_FS);
      // env texture with mips
      const t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t);
      gl.texStorage2D(gl.TEXTURE_2D, 10, gl.RGBA16F, 512, 256);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      this.envTex = { tex: t }; this.envFB = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, this.envFB);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, t, 0);
    }
    gl.disable(gl.DEPTH_TEST); gl.disable(gl.BLEND);
    this.skyBase.bind(); this.skyPre.use().setAll({ uSunDir: sunDir, uMie: mie, uSunI: sunI, uCamH: 30 }); fullscreen();
    // integrate ambient from a small readback
    if (!this._skySmall) {
      try { this._skySmall = new FBO(64, 32, [{ internal: gl.RGBA32F, format: gl.RGBA, type: gl.FLOAT }], null); }
      catch (e) { this._skySmall = new FBO(64, 32, [{ internal: gl.RGBA16F, format: gl.RGBA, type: gl.HALF_FLOAT }], null); }
    }
    const small = this._skySmall;
    small.bind(); this.skyPre.use().setAll({ uSunDir: sunDir, uMie: mie, uSunI: sunI, uCamH: 30 }); fullscreen();
    const px = new Float32Array(64 * 32 * 4); gl.readPixels(0, 0, 64, 32, gl.RGBA, gl.FLOAT, px);
    let up = [0, 0, 0], wu = 0, hz = [0, 0, 0], wh = 0;
    for (let y = 0; y < 32; y++) for (let x = 0; x < 64; x++) {
      const th = (y + 0.5) / 32 * Math.PI, phi = ((x + 0.5) / 64 - 0.5) * 2 * Math.PI;
      const d = [Math.sin(th) * Math.sin(phi), Math.cos(th), -Math.sin(th) * Math.cos(phi)];
      const i = (y * 64 + x) * 4; const sa = Math.sin(th);
      if (d[1] > 0) { const w = d[1] * sa; for (let k = 0; k < 3; k++) up[k] += px[i + k] * w; wu += w; }
      if (d[1] > 0 && d[1] < 0.5) { const w = sa; for (let k = 0; k < 3; k++) hz[k] += px[i + k] * w; wh += w; }
    }
    up = up.map(v => v / wu); hz = hz.map(v => v / wh);
    const T = sunTransmittance(sunDir, mie, 30);
    const sunColor = T.map(t => t * sunI);
    // ground bounce radiance (albedo ~0.18)
    const E = sunColor.map((s, k) => s * Math.max(sunDir[1], 0) + up[k] * Math.PI);
    const ground = E.map(e => e * 0.16 / Math.PI);
    const cloudCover = env.cloud ? env.cloud[0] : 0;
    // overcast: reduce direct, increase diffuse
    const direct = sunColor.map(s => s * (1 - 0.55 * cloudCover));
    this.light = { sunDir, sunColor: direct, skyUp: up.map(v => v * (1 + 0.3 * cloudCover)), skyHorizon: hz.map((v, k) => v * 0.6 + ground[k] * 0.4), ground };
    // env compose
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.envFB); gl.viewport(0, 0, 512, 256);
    this.envProg.use();
    this.setLightUniforms(this.envProg, env);
    this.envProg.setAll({ uSkyBase: this.skyBase.tex[0], uRefPos: env.refPos || [0, 50, 0], uGroundCol: ground.map(g => g * 0.9) });
    fullscreen();
    gl.bindTexture(gl.TEXTURE_2D, this.envTex.tex); gl.generateMipmap(gl.TEXTURE_2D);
    this.env = env;
  }
  setLightUniforms(p, env) {
    const L = this.light;
    p.setAll({
      uSunDir: L.sunDir, uSunColor: L.sunColor, uSkyUp: L.skyUp, uSkyHorizon: L.skyHorizon, uGroundBounce: L.ground,
      uSkyTex: this.envTex, uNoise: env.noiseTex, uFog: env.fog, uCloud: env.cloud, uCloudWind: env.cloudWind, uCloudTex: env.cloudTex, uTime: env.time || 0,
    });
  }

  // --- camera & frustum ---
  computeCamera(cam) {
    // cam: {pos, target|dir, up, fov (vertical rad), near, split, far}
    const dir = cam.dir || v3.norm(v3.sub(cam.target, cam.pos));
    let up = cam.up || [0, 1, 0];
    if (cam.roll) { // roll around dir
      const r = v3.norm(v3.cross(dir, up)); const u = v3.cross(r, dir); const c = Math.cos(cam.roll), s = Math.sin(cam.roll);
      up = v3.add(v3.mul(u, c), v3.mul(r, s));
    }
    const view = m4.lookDir(dir, up);
    const aspect = this.W / this.H;
    // subpixel jitter not used
    const projNear = m4.perspective(cam.fov, aspect, cam.near, cam.split * 1.08);
    const projFar = m4.perspective(cam.fov, aspect, cam.split, cam.far);
    return { pos: cam.pos, dir, up, view, vpNear: m4.mul(projNear, view), vpFar: m4.mul(projFar, view), fov: cam.fov, aspect, near: cam.near, split: cam.split, far: cam.far };
  }
  frustumPlanes(vp) {
    const m = vp; const planes = [];
    const row = (i) => [m[i], m[4 + i], m[8 + i], m[12 + i]];
    const r0 = row(0), r1 = row(1), r2 = row(2), r3 = row(3);
    const add = (a, b, s) => a.map((v, i) => v + s * b[i]);
    for (const p of [add(r3, r0, 1), add(r3, r0, -1), add(r3, r1, 1), add(r3, r1, -1), add(r3, r2, 1), add(r3, r2, -1)]) {
      const l = Math.hypot(p[0], p[1], p[2]); planes.push(p.map(v => v / l));
    }
    return planes;
  }
  boxVisible(planes, bb, camPos) {
    if (!bb) return true;
    for (const p of planes) {
      const x = (p[0] > 0 ? bb[3] : bb[0]) - camPos[0], y = (p[1] > 0 ? bb[4] : bb[1]) - camPos[1], z = (p[2] > 0 ? bb[5] : bb[2]) - camPos[2];
      if (p[0] * x + p[1] * y + p[2] * z + p[3] < 0) return false;
    }
    return true;
  }

  // --- cascaded shadows ---
  computeCascades(C, splits) {
    const L = this.light.sunDir; const res = this.shadowRes; const out = [];
    let prev = C.near;
    const tanY = Math.tan(C.fov / 2), tanX = tanY * C.aspect;
    const right = v3.norm(v3.cross(C.dir, C.up)), upv = v3.cross(right, C.dir);
    for (let i = 0; i < 3; i++) {
      const d0 = i === 0 ? C.near : splits[i - 1] * 0.85, d1 = splits[i];
      // bounding sphere of frustum slice
      const corners = [];
      for (const d of [d0, d1]) for (const sx of [-1, 1]) for (const sy of [-1, 1])
        corners.push(v3.add(C.pos, v3.add(v3.mul(C.dir, d), v3.add(v3.mul(right, sx * tanX * d), v3.mul(upv, sy * tanY * d)))));
      let c = [0, 0, 0]; corners.forEach(p => c = v3.add(c, p)); c = v3.mul(c, 1 / 8);
      let r = 0; corners.forEach(p => r = Math.max(r, v3.dist(p, c)));
      r = Math.ceil(r);
      // light basis
      const lz = L; const lx = v3.norm(v3.cross([0, 1, 0.001], lz)); const ly = v3.cross(lz, lx);
      const texel = 2 * r / res;
      // snap center in light space
      let cx = v3.dot(c, lx), cy = v3.dot(c, ly), cz = v3.dot(c, lz);
      cx = Math.floor(cx / texel) * texel; cy = Math.floor(cy / texel) * texel;
      const depthR = Math.max(r, 3000);
      const view = new Float32Array([lx[0], ly[0], lz[0], 0, lx[1], ly[1], lz[1], 0, lx[2], ly[2], lz[2], 0, -cx, -cy, -cz, 1]);
      const proj = m4.ortho(-r, r, -r, r, -depthR - 1500, depthR);
      out.push({ vp: m4.mul(proj, view), texel, far: d1 });
      prev = d1;
    }
    return out;
  }

  drawItems(items, passName, vp, camPos, planes, filter) {
    for (const it of items) {
      if (filter && !filter(it)) continue;
      if (!this.boxVisible(planes, it.bbox, camPos)) continue;
      const pr = this.progs[it.prog]; if (!pr) continue;
      const p = passName === 'shadow' ? pr.shadow : pr.main;
      p.use();
      if (this._cur.get(p) !== this._frameId) { this._cur.set(p, this._frameId); this.applyFrameUniforms(p, passName); }
      p.set('uViewProj', vp); p.set('uCamPos', camPos);
      if (it.uniforms) p.setAll(typeof it.uniforms === 'function' ? it.uniforms() : it.uniforms);
      if (it.model) { p.set('uModel', it.model); p.set('uPrevModel', it.prevModel || it.model); }
      if (it.blend === 'add') { gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE); gl.depthMask(false); }
      else if (it.blend === 'alpha') { gl.enable(gl.BLEND); gl.blendFuncSeparate(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA, gl.ZERO, gl.ONE); gl.depthMask(false); }
      if (it.polyOffset && passName !== 'shadow') { gl.enable(gl.POLYGON_OFFSET_FILL); gl.polygonOffset(it.polyOffset[0], it.polyOffset[1]); }
      if (it.noCull) gl.disable(gl.CULL_FACE);
      it.mesh.draw();
      if (it.noCull) { if (this.cull) gl.enable(gl.CULL_FACE); }
      if (it.polyOffset) gl.disable(gl.POLYGON_OFFSET_FILL);
      if (it.blend) { gl.disable(gl.BLEND); gl.depthMask(true); }
    }
  }
  applyFrameUniforms(p, passName) {
    const F = this.frameUniforms; p.setAll(F.common);
    if (passName !== 'shadow') p.setAll(F.shadow);
    this.setLightUniforms(p, this.env);
  }

  _sync(label) { if (!this.profile) return; const px = new Uint8Array(4); gl.bindFramebuffer(gl.FRAMEBUFFER, this.final.fb); gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px); const n = performance.now(); this.prof[label] = (this.prof[label] || 0) + n - this._pt; this._pt = n; }
  render(scene, camIn, t, post) {
    if (this.profile) { this._pt = performance.now(); this._sync('pre'); this._pt = performance.now(); }
    const C = this.computeCamera(camIn); this.curCam = C;
    this._frameId = (this._frameId || 0) + 1; this._cur = this._cur || new Map();
    this.env.time = t;
    const prev = this.prev || C;
    // shadows
    const splits = camIn.shadowSplits || [120, 700, 3500];
    const cas = this.computeCascades(C, splits);
    this.frameUniforms.common = Object.assign({ uPrevCamPos: prev.pos, uTime: t }, this.extraCommon || {});
    this.frameUniforms.shadow = {
      uShadow0: this.shadowFBO[0].depth, uShadow1: this.shadowFBO[1].depth, uShadow2: this.shadowFBO[2].depth,
      uShadowMat0: cas[0].vp, uShadowMat1: cas[1].vp, uShadowMat2: cas[2].vp, uShadowSplits: splits, uShadowTexel: cas.map(c => c.texel), uShadowRes: this.shadowRes,
    };
    gl.enable(gl.DEPTH_TEST); gl.depthFunc(gl.LEQUAL); gl.disable(gl.BLEND);
    gl.enable(gl.CULL_FACE); gl.cullFace(gl.BACK); this.cull = true;
    for (let i = 0; i < 3; i++) {
      this.shadowFBO[i].bind(); gl.clear(gl.DEPTH_BUFFER_BIT);
      gl.enable(gl.POLYGON_OFFSET_FILL); gl.polygonOffset(1.5, 2.0);
      this.frameUniforms.common.uPrevViewProj = cas[i].vp;
      const planes = this.frustumPlanes(cas[i].vp);
      gl.disable(gl.CULL_FACE);
      this.drawItems(scene.items, 'shadow', cas[i].vp, [0, 0, 0], planes, it => it.castShadow && (!it.shadowMaxCascade || i < it.shadowMaxCascade));
      gl.enable(gl.CULL_FACE);
      gl.disable(gl.POLYGON_OFFSET_FILL);
    }
    this._sync('shadow');
    this._frameId++;
    // main passes
    this.ms.bind();
    gl.drawBuffers([gl.COLOR_ATTACHMENT0, gl.COLOR_ATTACHMENT1]);
    gl.clearBufferfv(gl.COLOR, 0, [0, 0, 0, 1]); gl.clearBufferfv(gl.COLOR, 1, [60000, 0, 0, 1]);
    const prevVP = m4.mul(m4.perspective(C.fov, C.aspect, C.near, C.far), prev.view);
    this.frameUniforms.common.uPrevViewProj = prevVP;
    // far range
    gl.clear(gl.DEPTH_BUFFER_BIT);
    const planesFar = this.frustumPlanes(C.vpFar);
    const distMin = (bb) => { if (!bb) return 0; const p = C.pos; const dx = Math.max(bb[0] - p[0], 0, p[0] - bb[3]), dy = Math.max(bb[1] - p[1], 0, p[1] - bb[4]), dz = Math.max(bb[2] - p[2], 0, p[2] - bb[5]); return Math.hypot(dx, dy, dz); };
    const distMax = (bb) => { if (!bb) return 1e9; const p = C.pos; const dx = Math.max(Math.abs(bb[0] - p[0]), Math.abs(bb[3] - p[0])), dy = Math.max(Math.abs(bb[1] - p[1]), Math.abs(bb[4] - p[1])), dz = Math.max(Math.abs(bb[2] - p[2]), Math.abs(bb[5] - p[2])); return Math.hypot(dx, dy, dz); };
    this.drawItems(scene.items, 'main', C.vpFar, C.pos, planesFar, it => !it.blend && !it.nearOnly && distMax(it.bbox) > C.split);
    // sky
    gl.depthMask(false);
    const invVP = m4.invert(C.vpFar);
    this.skyProg.use(); this.setLightUniforms(this.skyProg, this.env);
    this.skyProg.setAll({ uInvViewProj: invVP, uPrevViewProj: prevVP, uCamPos: C.pos, uSkyBase: this.skyBase.tex[0], uSunDiskScale: 1.0, uTime: t, uSkyClouds: this.env.slab ? 0 : 1 });
    fullscreen();
    gl.depthMask(true);
    this.curRange = [C.split, 1e9];
    { const fb = scene.items.filter(it => it.blend && it.bothPasses).map(it => ({ it, key: it.sortKey(C.pos) })).sort((a, b) => b.key - a.key).map(o => o.it);
      this.drawItems(fb, 'main', C.vpFar, C.pos, planesFar, () => true); }
    this._sync('far+sky');
    // near range
    gl.clear(gl.DEPTH_BUFFER_BIT);
    this._frameId++;
    const planesNear = this.frustumPlanes(C.vpNear);
    this.drawItems(scene.items, 'main', C.vpNear, C.pos, planesNear, it => !it.blend && distMin(it.bbox) < C.split * 1.08);
    this.curRange = [0, C.split];
    const blended = scene.items.filter(it => !!it.blend).map(it => ({ it, key: it.sortKey ? it.sortKey(C.pos) : -1e9 })).sort((a, b) => b.key - a.key).map(o => o.it);
    this.drawItems(blended, 'main', C.vpNear, C.pos, planesNear, it => !it.farOnly && distMin(it.bbox) < C.split * 1.08);
    this._sync('near');
    gl.disable(gl.CULL_FACE);
    gl.disable(gl.DEPTH_TEST);
    // resolve
    gl.bindFramebuffer(gl.READ_FRAMEBUFFER, this.ms.fb);
    gl.readBuffer(gl.COLOR_ATTACHMENT0); gl.bindFramebuffer(gl.DRAW_FRAMEBUFFER, this.resColor.fb);
    gl.blitFramebuffer(0, 0, this.W, this.H, 0, 0, this.W, this.H, gl.COLOR_BUFFER_BIT, gl.NEAREST);
    gl.readBuffer(gl.COLOR_ATTACHMENT1); gl.bindFramebuffer(gl.DRAW_FRAMEBUFFER, this.resAux.fb);
    gl.blitFramebuffer(0, 0, this.W, this.H, 0, 0, this.W, this.H, gl.COLOR_BUFFER_BIT, gl.NEAREST);
    gl.bindFramebuffer(gl.READ_FRAMEBUFFER, null); gl.bindFramebuffer(gl.DRAW_FRAMEBUFFER, null);
    this._sync('resolve');
    // motion blur
    let src = this.resColor.tex[0];
    if (post.shutter > 0) {
      this.mb.bind(); this.post.mblur.use().setAll({ uColor: this.resColor.tex[0], uAux: this.resAux.tex[0], uTexel: [1 / this.W, 1 / this.H], uShutter: post.shutter, uMaxPx: this.W * 0.03 }); fullscreen();
      src = this.mb.tex[0];
    }
    this._sync('mblur');
    // bloom
    let s = src;
    for (let i = 0; i < this.down.length; i++) { const f = this.down[i]; f.bind(); this.post.down.use().setAll({ uSrc: s, uTexel: [1 / (i === 0 ? this.W : this.down[i - 1].w), 1 / (i === 0 ? this.H : this.down[i - 1].h)], uFirst: i === 0 ? 1 : 0 }); fullscreen(); s = f.tex[0]; }
    let u = this.down[this.down.length - 1].tex[0];
    for (let i = this.down.length - 2; i >= 0; i--) { const f = this.up[i]; f.bind(); this.post.up.use().setAll({ uSrc: u, uBase: this.down[i].tex[0], uTexel: [1 / this.down[i + 1].w, 1 / this.down[i + 1].h], uMix: 1.0 }); fullscreen(); u = f.tex[0]; }
    this._sync('bloom');
    // final
    this.final.bind();
    this.post.final.use().setAll({
      uColor: src, uBloom: u, uOverlay: this.overlayTex, uExposure: post.exposure, uBloomMix: post.bloom ?? 0.012, uTime: t,
      uVignette: post.vignette ?? 0.25, uGrain: post.grain ?? 0.012, uLift: post.lift || [0, 0, 0], uGain: post.gain || [1, 1, 1], uSat: post.sat ?? 1.0, uFade: post.fade ?? 1.0, uRes: [this.W, this.H],
    });
    fullscreen();
    this._sync('final');
    this.prev = C;
    return C;
  }
  // copy the finished frame to the visible canvas (default framebuffer), scaling if needed
  present(cw, ch) {
    gl.bindFramebuffer(gl.READ_FRAMEBUFFER, this.final.fb); gl.bindFramebuffer(gl.DRAW_FRAMEBUFFER, null);
    gl.blitFramebuffer(0, 0, this.W, this.H, 0, 0, cw, ch, gl.COLOR_BUFFER_BIT, (cw === this.W && ch === this.H) ? gl.NEAREST : gl.LINEAR);
    gl.bindFramebuffer(gl.READ_FRAMEBUFFER, null);
  }
  resize(W, H) {
    if (W === this.W && H === this.H) return;
    const del = (f) => f && f.dispose && f.dispose();
    [this.ms, this.resColor, this.resAux, this.mb, this.final, ...this.down, ...this.up].forEach(del);
    this.W = W; this.H = H;
    this.ms = new FBO(W, H, [HF(), HF()], 'rb', this.samples);
    this.resColor = new FBO(W, H, [HF()], null); this.resAux = new FBO(W, H, [HF()], null); this.mb = new FBO(W, H, [HF()], null);
    this.down = []; this.up = []; let w = W, h = H;
    for (let i = 0; i < 6; i++) { w = Math.max(1, w >> 1); h = Math.max(1, h >> 1); this.down.push(new FBO(w, h, [HF()], null)); this.up.push(new FBO(w, h, [HF()], null)); }
    this.final = new FBO(W, H, [{ internal: gl.RGBA8 }], null);
    this.overlayTex = texture(W, H, { internal: gl.RGBA8 });
    this.pixels = null; this.prev = null;
  }
  readPixels() {
    if (!this.pixels) this.pixels = new Uint8Array(this.W * this.H * 4);
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.final.fb);
    gl.readPixels(0, 0, this.W, this.H, gl.RGBA, gl.UNSIGNED_BYTE, this.pixels);
    return this.pixels;
  }
  setOverlay(canvas) {
    gl.bindTexture(gl.TEXTURE_2D, this.overlayTex.tex);
    gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
    gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, gl.RGBA, gl.UNSIGNED_BYTE, canvas);
  }
}
