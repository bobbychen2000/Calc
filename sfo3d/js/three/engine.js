// Renderer core for live3.html: three.js r186 WebGPURenderer (WebGPU where the browser has it, automatic WebGL 2
// fallback), camera, sun with cascaded shadow maps, and the TSL post pipeline:
//   high/medium: depth+normal+velocity pre-pass -> GTAO (fed into the ambient term via builtinAOContext) -> lit pass
//                -> TRAA (MSAA off) -> bloom (high) -> AgX tone mapping (renderer output transform)
//   low (phones): one pass with MRT (colour, normal, velocity) -> half-resolution GTAO applied to the colour -> TRAA
// Decisions and their sources: docs/research/engine.md (verified), docs/research/engine_impl.md (this port).
import { THREE, TSL } from './lib.js';
const { pass, mrt, output, velocity, normalView, packNormalToRGB, unpackRGBToNormal, sample, screenUV, builtinAOContext, vec4, float, mix, uniform, renderOutput, saturation, pow, max, clamp, step, vec3 } = TSL;

// quality tiers (js/live/app.js QUALITY, plus the new-renderer settings)
export const QUALITY3 = {
  high: { name: 'high', dprMax: 2, maxPx: 3.2e6, shadow: 2048, cascades: 3, ao: 'prepass', aoScale: 0.5, traa: true, bloom: true, terrainStep: 15, mapRes: 1.0, aptRes: 0.8, cityRes: 4096, skyRes: 1024, lod: 1800, shadowDist: 1600, aniso: 16 },
  medium: { name: 'medium', dprMax: 1.5, maxPx: 2.0e6, shadow: 2048, cascades: 3, ao: 'prepass', aoScale: 0.5, traa: true, bloom: false, terrainStep: 20, mapRes: 1.25, aptRes: 1.0, cityRes: 4096, skyRes: 1024, lod: 1300, shadowDist: 1100, aniso: 8 },
  low: { name: 'low', dprMax: 2, maxPx: 1.1e6, shadow: 1024, cascades: 2, ao: 'mrt', aoScale: 0.5, traa: true, bloom: false, terrainStep: 30, mapRes: 1.6, aptRes: 1.25, cityRes: 2048, skyRes: 512, lod: 1000, shadowDist: 700, aniso: 4 },
};

export class Engine {
  constructor(parent, Q, opts = {}) { this.parent = parent; this.Q = Q; this.opts = opts; }
  async init() {
    const Q = this.Q; const q = new URLSearchParams(location.search);
    const forceWebGL = q.get('webgl') === '1' || this.opts.forceWebGL;
    const renderer = new THREE.WebGPURenderer({ canvas: this.opts.canvas || undefined, antialias: false, forceWebGL, reversedDepthBuffer: q.get('revz') !== '0', powerPreference: 'high-performance', alpha: false });
    await renderer.init();
    this.renderer = renderer; this.backend = renderer.backend.isWebGPUBackend ? 'webgpu' : 'webgl2';
    if (!this.opts.canvas) { renderer.domElement.id = 'gl'; this.parent.prepend(renderer.domElement); }
    renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFShadowMap;
    renderer.toneMapping = THREE.AgXToneMapping; renderer.toneMappingExposure = 1.0;
    this.reversed = !!renderer.reversedDepthBuffer;
    this.maxAniso = renderer.getMaxAnisotropy ? renderer.getMaxAnisotropy() : 16;
    const scene = new THREE.Scene(); this.scene = scene;
    const camera = new THREE.PerspectiveCamera(50, 16 / 9, 0.5, 180000); this.camera = camera;
    // sun + cascaded shadows (CSMShadowNode; splits follow the camera distance like js/renderer.js computeCascades)
    const sun = new THREE.DirectionalLight(0xffffff, 1); sun.castShadow = true;
    sun.shadow.mapSize.set(Q.shadow, Q.shadow); sun.shadow.camera.near = 1; sun.shadow.camera.far = 40000;
    // depth bias: none. A constant bias is scaled by each cascade camera's depth range (hundreds of metres with the
    // light margin), so the old -0.0003 detached every shadow from its caster by metres, and on the airport scale made
    // them vanish (observed in js/three/dev/shadowtest.html, 25 Sep 2026). A normal-offset bias alone keeps acne away.
    sun.shadow.bias = 0; sun.shadow.normalBias = 0.2; sun.shadow.radius = 2;
    const TW = this.opts.tweak || ''; // dev variants for js/three/dev/shadowtest.html
    if (TW === 'oldbias') sun.shadow.bias = -0.0003;
    this.splits = [84, 300, 960];
    this.csm = new THREE.CSMShadowNode(sun, TW === 'practical' ? { cascades: Q.cascades, maxFar: 3000, mode: 'practical', lightMargin: 600 } : { cascades: Q.cascades, maxFar: 3000, mode: 'custom', lightMargin: 600,
      customSplitsCallback: (n, near, far, target) => { const s = this.splits; for (let i = 0; i < n - 1; i++) target.push(Math.min(0.99, s[i] / far)); target.push(1); } });
    this.csm.fade = TW !== 'nofade';
    if (TW !== 'plain') sun.shadow.shadowNode = this.csm; else Object.assign(sun.shadow.camera, { left: -200, right: 200, top: 200, bottom: -200, near: 1, far: 3000 }); scene.add(sun); scene.add(sun.target); this.sun = sun;
    this.aoAmount = uniform(1.0);
    this.buildPipeline();
    return this;
  }
  buildPipeline() {
    const { renderer, scene, camera, Q } = this;
    const pipe = new THREE.RenderPipeline(renderer); this.pipe = pipe;
    let color, depth, vel;
    if (Q.ao === 'prepass') {
      const pre = pass(scene, camera); pre.name = 'prepass'; pre.transparent = false;
      pre.setMRT(mrt({ output: packNormalToRGB(normalView), velocity }));
      pre.getTexture('output').type = THREE.UnsignedByteType;
      const nrm = sample((u) => unpackRGBToNormal(pre.getTextureNode().sample(u)));
      depth = pre.getTextureNode('depth'); vel = pre.getTextureNode('velocity');
      const aoN = THREE.ao(depth, nrm, camera); aoN.resolutionScale = Q.aoScale; aoN.radius.value = 2.2; aoN.distanceExponent.value = 1.3; aoN.thickness.value = 1.5; aoN.scale.value = 1.0;
      this.aoNode = aoN;
      const sp = pass(scene, camera); sp.name = 'scene';
      sp.contextNode = builtinAOContext(mix(float(1.0), aoN.getTextureNode().sample(screenUV).r, this.aoAmount));
      color = sp; this.scenePass = sp;
    } else {
      const sp = pass(scene, camera); sp.name = 'scene';
      sp.setMRT(mrt({ output, normal: packNormalToRGB(normalView), velocity }));
      sp.getTexture('normal').type = THREE.UnsignedByteType;
      depth = sp.getTextureNode('depth'); vel = sp.getTextureNode('velocity');
      const nrm = sample((u) => unpackRGBToNormal(sp.getTextureNode('normal').sample(u)));
      const aoN = THREE.ao(depth, nrm, camera); aoN.resolutionScale = Q.aoScale; aoN.radius.value = 2.2; aoN.distanceExponent.value = 1.3; aoN.thickness.value = 1.5;
      this.aoNode = aoN;
      const c = sp.getTextureNode('output');
      color = vec4(c.rgb.mul(mix(float(1.0), aoN.getTextureNode().sample(screenUV).r.mul(0.6).add(0.4), this.aoAmount)), c.a); this.scenePass = sp;
    }
    let outN = color;
    if (Q.traa) { const tr = THREE.traa(color, depth, vel, camera); tr.useSubpixelCorrection = false; this.traaNode = tr; outN = tr; }
    if (Q.bloom) { const bl = THREE.bloom(outN, 0.12, 0.35, 2.2); this.bloomNode = bl; outN = outN.add(bl); }
    // output: AgX (exposure = renderer.toneMappingExposure), then the grade of the old renderer's final pass
    // (js/shaders/post.js: saturation, js/live/app.js post.sat = 1.1) in display-linear, then sRGB
    pipe.outputColorTransform = false;
    // plus an S-curve contrast around a display-linear pivot (the "punchy" look often paired with AgX: AgX base keeps
    // the darks much higher than the old ACES fit, e.g. bay water 101 vs 58 sRGB in the overview; contrast 1.35 at
    // pivot 0.45 brings it to ~80 and leaves the airfield mid-tones unchanged). ?contrast= / ?sat= override.
    this.grade = { sat: uniform(1.1), contrast: uniform(1.35), pivot: uniform(0.45) };
    const tm = renderOutput(outN, THREE.AgXToneMapping, THREE.NoColorSpace);
    const x = clamp(saturation(tm.rgb, this.grade.sat), 0.0, 1.0); const P = this.grade.pivot, G = this.grade.contrast;
    const lo = P.mul(pow(x.div(P), G)), hi = float(1.0).sub(float(1.0).sub(P).mul(pow(float(1.0).sub(x).div(float(1.0).sub(P)), G)));
    const graded = mix(hi, lo, step(x, vec3(P)));
    pipe.outputNode = renderOutput(vec4(graded, 1.0), THREE.NoToneMapping, THREE.SRGBColorSpace);
  }
  // rig camera {pos, target|dir, fov, near, far, shadowSplits} -> three camera + cascade splits
  setCamera(c, W, H) {
    const cam = this.camera;
    cam.position.set(c.pos[0], c.pos[1], c.pos[2]);
    const dir = c.dir || [c.target[0] - c.pos[0], c.target[1] - c.pos[1], c.target[2] - c.pos[2]];
    cam.up.set(0, 1, 0); cam.lookAt(c.pos[0] + dir[0], c.pos[1] + dir[1], c.pos[2] + dir[2]);
    const fovDeg = c.fov * 180 / Math.PI; const near = Math.max(0.2, c.near * (this.reversed ? 1 : 2)), far = c.far || 180000;
    const changed = Math.abs(cam.fov - fovDeg) > 1e-4 || Math.abs(cam.near - near) > 1e-3 || cam.far !== far || Math.abs(cam.aspect - W / H) > 1e-4;
    if (changed) { cam.fov = fovDeg; cam.near = near; cam.far = far; cam.aspect = W / H; cam.updateProjectionMatrix(); }
    cam.updateMatrixWorld();
    // cascades: [1.4d, 5d, 16d] clamped as js/live/controls.js camera().shadowSplits, capped by the tier's range
    const s = (c.shadowSplits || [300, 1500, 6000]).slice(0, this.Q.cascades);
    const maxFar = Math.max(200, s[s.length - 1]);
    const key = s.map(v => Math.round(v)).join(',') + ':' + Math.round(near * 100);
    if (key !== this._splitKey && this.csm.mainFrustum) { this._splitKey = key; this.splits = s; this.csm.maxFar = maxFar; this.csm.updateFrustums(); }
    else if (!this.csm.mainFrustum) { this.splits = s; this.csm.maxFar = maxFar; }
  }
  setSun(dir, color, intensityScale = 1) {
    const s = this.sun; s.position.set(dir[0] * 1000, dir[1] * 1000, dir[2] * 1000); s.target.position.set(0, 0, 0);
    const m = Math.max(color[0], color[1], color[2], 1e-6);
    s.color.setRGB(color[0] / m, color[1] / m, color[2] / m, THREE.LinearSRGBColorSpace); s.intensity = m * intensityScale;
    s.castShadow = dir[1] > 0.02; s.updateMatrixWorld(); s.target.updateMatrixWorld();
  }
  resize(cssW, cssH, pixelRatio) { this.renderer.setPixelRatio(pixelRatio); this.renderer.setSize(cssW, cssH, false); }
  render() { this.pipe.render(); }
}
