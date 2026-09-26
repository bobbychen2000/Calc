// Renderer core for live3.html: three.js r186 WebGPURenderer (WebGPU where the browser has it, automatic WebGL 2
// fallback), camera, sun with cascaded shadow maps, apron floodlight field (js/three/flood.js), and the TSL post chain:
//   high/medium: depth+normal+velocity pre-pass -> GTAO (fed into the ambient term via builtinAOContext) -> lit pass
//                -> TRAA (MSAA off) -> + light sprites (own pass, after TRAA) -> exposure -> bloom -> AgX + look -> grade
//   low (phones): one pass with MRT (colour, normal, velocity) -> half-resolution GTAO applied to the colour -> TRAA
//                -> the same sprite / bloom / AgX / grade chain (bloom at a lower resolution)
// Decisions and their sources: docs/research/engine.md (verified), docs/research/engine_impl.md (this port).
// Review round 1 (25 Sep 2026) changes, each explained where it is made: bloom threshold in exposed (display) units
// with a luminance clamp; AgX with a log-domain contrast look around 18 % grey instead of a display-linear S-curve;
// vignette + dither; light sprites composited after TRAA; TRAA fed a correct reversed depth (vendored three patch,
// tools/build3/build.mjs); per-cascade normal-offset (1.25 texels) and slope-scaled depth bias; low-tier cascade range
// from the tier's shadow distance; device-loss / init-failure hooks for the app.
// Review round 2 (26 Sep 2026): the look contrast acts on log LUMINANCE only (per channel it raised every channel ratio
// to the power 1.8: navy shade, pastel paint), with a look saturation that rises on the AgX shoulder; GTAO's noise
// rotation driven by the engine's own frame counter (three's frameId steps by the number of passes per frame, which
// cycled only a few patterns and left a static mottle); low tier: 3 cascades, the AO in the ambient term (previous
// frame's GTAO, reprojected) instead of multiplied into the sunlit colour; contrast-adaptive sharpening after TRAA;
// shadow-casting floodlight spots for the masts nearest the view (js/three/flood.js MastSpot), GTAO on the flood term.
import { THREE, TSL } from './lib.js';
import { FloodLight, FloodLightNode, MastSpot, MastSpotNode, MAST_LAYER } from './flood.js';
const { pass, mrt, output, velocity, normalView, packNormalToRGB, unpackRGBToNormal, sample, screenUV, screenCoordinate, screenSize, builtinAOContext, vec2, vec3, vec4, float, mix, uniform, saturation, pow, max, min, clamp, dot, log2, Fn, mat3, luminance, sRGBTransferOETF, fract, sin, smoothstep, normalWorldGeometry, sqrt } = TSL;

// quality tiers (js/live/app.js QUALITY, plus the new-renderer settings). resSteps: the render-scale steps the dynamic
// resolution may use (quantised, js/three/renderer3.js resize); shadowDist: range of the last cascade on the 2-cascade tier
// floodSpots / spotMap: shadow-casting floodlight masts near the view and their shadow-map size (js/three/flood.js);
// livMB: GPU budget for brand livery textures (js/three/aircraft.js LiveryCache evicts the least recently used beyond it)
export const QUALITY3 = {
  high: { name: 'high', dprMax: 2, maxPx: 3.2e6, shadow: 2048, cascades: 3, shadowRadius: 2, ao: 'prepass', aoScale: 0.5, traa: true, bloom: true, bloomScale: 0.5, terrainStep: 15, mapRes: 1.0, aptRes: 0.8, cityRes: 4096, skyRes: 1024, lod: 1800, shadowDist: 1600, aniso: 16, maxTex: 0, floodSpots: 2, spotMap: 2048, livMB: 320 },
  medium: { name: 'medium', dprMax: 1.5, maxPx: 2.0e6, shadow: 2048, cascades: 3, shadowRadius: 2, ao: 'prepass', aoScale: 0.5, traa: true, bloom: true, bloomScale: 0.5, terrainStep: 20, mapRes: 1.25, aptRes: 1.0, cityRes: 4096, skyRes: 1024, lod: 1300, shadowDist: 1100, aniso: 8, maxTex: 2048, floodSpots: 2, spotMap: 2048, livMB: 160 },
  // low (phones): 3 cascades x 1024^2 (review round 2: 2 cascades left rooftop units without shadows), the first split
  // closer than the rig's, the last at least the tier's shadow distance
  low: { name: 'low', dprMax: 2, maxPx: 1.1e6, shadow: 1024, cascades: 3, shadowRadius: 3, ao: 'mrt', aoScale: 0.5, traa: true, bloom: true, bloomScale: 0.25, terrainStep: 30, mapRes: 1.6, aptRes: 1.25, cityRes: 2048, skyRes: 512, lod: 1000, shadowDist: 700, aniso: 4, maxTex: 1024, floodSpots: 1, spotMap: 1024, livMB: 64,
    splits: (r, Q) => { const a = r[0] * 0.8, b = Math.max(a * 2.5, r[1] * 0.8); return [a, b, Math.max(b * 1.5, Math.min(r[r.length - 1], Math.max(Q.shadowDist, r[1] * 1.6)))]; } },
};

// GTAO radius (world metres): 4 m, so the sky occlusion under a wing, a fuselage or a jet bridge (4-6 m above the apron)
// is caught (review round 1: shade under aircraft was only 1/6 of sunlit concrete, about 1/30 in a reference photo;
// the old 2.2 m radius saw only contact creases)
const AO_RADIUS = 4.0;

// ---------------------------------------------------------------- AgX with a look (display transform)
// three r186 AgXToneMapping (src/nodes/display/ToneMappingFunctions.js: Troy Sobotka's AgX, Benjamin Wrensch's fit),
// re-implemented so a look can be applied inside it: contrast in the log2 encoding around 18 % grey (the encoding of
// 0.18 is 0.6061), then a saturation on the sigmoid output (as Blender's AgX looks do; review round 1: the power-curve
// S-curve at display-linear 0.45 lifted the blacks and flattened the image). Matrices copied from three (MIT).
// Review round 2: the contrast is applied to the log2 of the LUMINANCE and the same offset added to all three channels,
// so channel ratios are kept (per channel, contrast 1.8 raised every ratio to the power 1.8: open shade with scene B/R
// 1.9 came out at display B/R 4.6, navy; sunlit paint was pushed onto the shoulder and went pastel). The look saturation
// is sat.lo up to grey and rises to sat.hi on the shoulder (AgX's path to white desaturates bright colours: sunlit
// Federal Yellow and the red equipment boxes). tools/build3/grade_hdr.py applies the identical transform offline.
const SRGB_TO_2020 = mat3(vec3(0.6274, 0.0691, 0.0164), vec3(0.3293, 0.9195, 0.0880), vec3(0.0433, 0.0113, 0.8956));
const REC2020_TO_SRGB = mat3(vec3(1.6605, -0.1246, -0.0182), vec3(-0.5876, 1.1329, -0.1006), vec3(-0.0728, -0.0083, 1.1187));
const AGX_IN = mat3(vec3(0.856627153315983, 0.137318972929847, 0.11189821299995), vec3(0.0951212405381588, 0.761241990602591, 0.0767994186031903), vec3(0.0482516061458583, 0.101439036467562, 0.811302368396859));
const AGX_OUT = mat3(vec3(1.1271005818144368, -0.1413297634984383, -0.14132976349843826), vec3(-0.11060664309660323, 1.157823702216272, -0.11060664309660294), vec3(-0.016493938717834573, -0.016493938717834257, 1.2519364065950405));
const AGX_MIN = -12.47393, AGX_MAX = 4.026069, AGX_GREY = (Math.log2(0.18) - AGX_MIN) / (AGX_MAX - AGX_MIN);
const agxContrast = (x) => { const x2 = x.mul(x), x4 = x2.mul(x2); return x4.mul(x2).mul(15.5).sub(x4.mul(x).mul(40.14)).add(x4.mul(31.96)).sub(x2.mul(x).mul(6.868)).add(x2.mul(0.4298)).add(x.mul(0.1191)).sub(0.00232); };
export function agxLook(color, look) {
  return Fn(() => {
    const c2 = SRGB_TO_2020.mul(color);
    const c = max(AGX_IN.mul(c2), vec3(1e-10));
    const lg = log2(c).sub(AGX_MIN).div(AGX_MAX - AGX_MIN);
    const lY = log2(max(dot(c2, vec3(0.2627, 0.6780, 0.0593)), 1e-10)).sub(AGX_MIN).div(AGX_MAX - AGX_MIN);
    const x = clamp(lg.add(lY.sub(AGX_GREY).mul(float(look.contrast).sub(1.0))), 0.0, 1.0);
    const xl = clamp(lY.sub(AGX_GREY).mul(look.contrast).add(AGX_GREY), 0.0, 1.0);
    const k = mix(look.satLo, look.sat, clamp(xl.sub(AGX_GREY).div(0.85 - AGX_GREY), 0.0, 1.0));
    const s = agxContrast(x).toVar();
    const l = dot(s, vec3(0.2126, 0.7152, 0.0722)); s.assign(max(mix(vec3(l), s, k), vec3(0.0)));
    const o = pow(max(AGX_OUT.mul(s), vec3(0.0)), vec3(2.2));
    return clamp(REC2020_TO_SRGB.mul(o), 0.0, 1.0);
  })();
}

// CSMShadowNode with a per-cascade slope-scaled depth bias (normal offset alone left acne on flat roofs on the 1024²
// low tier and dark seams at roof-part junctions: review round 1). The bias is 0.5 texel x tan(angle to the sun), at
// most 4 texels, in the cascade camera's depth units (orthographic: linear over near..far). three negates nothing: a
// negative bias moves the receiver towards the light for both depth conventions (ShadowNode.setupShadowCoord).
// PCF with a per-frame rotation of the sampling pattern (three r186 PCFShadowFilter rotates its 5-tap Vogel disk by
// interleaved gradient noise of the pixel position only: a fixed per-pixel pattern that TRAA cannot average, seen as a
// mottle wherever the shadow test is partial, e.g. fuselage sides at grazing sun and wing shadows; round-2 renders).
// Same taps, the noise offset by 5.588238 px per frame (Jimenez 2014, the temporal IGN offset), frame index mod 64.
const shadowFrame = uniform(0);
const pcfTemporal = Fn(({ depthTexture, shadowCoord, shadow, depthLayer }) => {
  const cmp = (uv) => { let d = TSL.texture(depthTexture, uv); if (depthTexture.isArrayTexture) d = d.depth(depthLayer); return d.compare(shadowCoord.z); };
  const mapSize = TSL.reference('mapSize', 'vec2', shadow).setGroup(TSL.renderGroup);
  const radius = TSL.reference('radius', 'float', shadow).setGroup(TSL.renderGroup);
  const rs = radius.div(mapSize.x);
  const phi = TSL.interleavedGradientNoise(screenCoordinate.xy.add(shadowFrame.mul(5.588238))).mul(6.28318530718);
  let acc = null; for (let i = 0; i < 5; i++) { const c = cmp(shadowCoord.xy.add(TSL.vogelDiskSample(i, 5, phi).mul(rs))); acc = acc ? acc.add(c) : c; }
  return acc.mul(1 / 5);
});
class CSM3 extends THREE.CSMShadowNode {
  _init(builder) {
    super._init(builder);
    this.biasU = [];
    for (const lw of this.lights) {
      if (Engine.temporalShadows) lw.shadow.filterNode = pcfTemporal;
      const texel = uniform(1.0), range = uniform(40000.0); this.biasU.push({ texel, range });
      lw.shadow.biasNode = Fn(() => {
        const ndl = clamp(dot(normalWorldGeometry, this.sunDirU), 0.05, 1.0);
        const tanA = min(sqrt(float(1.0).sub(ndl.mul(ndl))).div(ndl), 8.0);
        return tanA.mul(0.5).mul(texel).div(range).negate();
      })();
    }
  }
}

export class Engine {
  static temporalShadows = true; // pcfTemporal (TRAA on every tier)
  constructor(parent, Q, opts = {}) { this.parent = parent; this.Q = Q; this.opts = opts; this.onLost = null; }
  async init() {
    const Q = this.Q; const q = new URLSearchParams(location.search);
    const forceWebGL = q.get('webgl') === '1' || this.opts.forceWebGL;
    const renderer = new THREE.WebGPURenderer({ canvas: this.opts.canvas || undefined, antialias: false, forceWebGL, reversedDepthBuffer: q.get('revz') !== '0', powerPreference: 'high-performance', alpha: false });
    // device loss (WebGPU: three's default handler only logs and stops rendering, the canvas froze with no message;
    // WebGL 2: the canvas also fires webglcontextlost, which js/live/app.js handles): keep three's bookkeeping, then
    // tell the app (js/three/renderer3.js turns it into the app's own 'context lost' message)
    const defLost = renderer.onDeviceLost.bind(renderer);
    renderer.onDeviceLost = (info) => { defLost(info); if (this.onLost) this.onLost(info); };
    await renderer.init();
    this.renderer = renderer; this.backend = renderer.backend.isWebGPUBackend ? 'webgpu' : 'webgl2';
    renderer.library.addLight(FloodLightNode, FloodLight); // apron floodlights as a light (js/three/flood.js)
    renderer.library.addLight(MastSpotNode, MastSpot);    // the masts nearest the view as shadow-casting spots
    if (!this.opts.canvas) { renderer.domElement.id = 'gl'; this.parent.prepend(renderer.domElement); }
    renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFShadowMap;
    renderer.toneMapping = THREE.NoToneMapping; renderer.toneMappingExposure = 1.0; // exposure + AgX are in the pipeline
    this.reversed = !!renderer.reversedDepthBuffer;
    this.maxAniso = renderer.getMaxAnisotropy ? renderer.getMaxAnisotropy() : 16;
    const scene = new THREE.Scene(); this.scene = scene;
    const camera = new THREE.PerspectiveCamera(50, 16 / 9, 0.5, 180000); this.camera = camera;
    camera.layers.enable(MAST_LAYER); // the mast geometry lives on its own layer (kept out of the floodlight spot shadow maps)
    // light sprites: own scene and an un-jittered copy of the camera, composited after TRAA (lights.js)
    this.fxScene = new THREE.Scene(); this.fxCam = new THREE.PerspectiveCamera();
    // sun + cascaded shadows (CSMShadowNode; splits follow the camera distance like js/renderer.js computeCascades)
    const sun = new THREE.DirectionalLight(0xffffff, 1); sun.castShadow = true;
    sun.shadow.mapSize.set(Q.shadow, Q.shadow); sun.shadow.camera.near = 1; sun.shadow.camera.far = 40000;
    // depth bias: the constant part is 0 (a depth-space constant is scaled by each cascade camera's depth range, the old
    // -0.0003 detached shadows by metres: js/three/dev/shadowtest.html); the slope-scaled part is CSM3's biasNode and
    // the normal offset is set per cascade to 1.25 texels in setCamera()
    sun.shadow.bias = 0; sun.shadow.normalBias = 0.2; sun.shadow.radius = Q.shadowRadius || 2;
    const TW = this.opts.tweak || ''; // dev variants for js/three/dev/shadowtest.html
    if (TW === 'oldbias') sun.shadow.bias = -0.0003;
    this.splits = [84, 300, 960]; this.sunDirU = uniform(new THREE.Vector3(0, 1, 0));
    const CSMClass = TW === 'nobias' ? THREE.CSMShadowNode : CSM3;
    this.csm = new CSMClass(sun, TW === 'practical' ? { cascades: Q.cascades, maxFar: 3000, mode: 'practical', lightMargin: 600 } : { cascades: Q.cascades, maxFar: 3000, mode: 'custom', lightMargin: 600,
      customSplitsCallback: (n, near, far, target) => { const s = this.splits; for (let i = 0; i < n - 1; i++) target.push(Math.min(0.99, s[i] / far)); target.push(1); } });
    this.csm.sunDirU = this.sunDirU;
    this.csm.fade = TW !== 'nofade';
    if (TW !== 'plain') sun.shadow.shadowNode = this.csm; else Object.assign(sun.shadow.camera, { left: -200, right: 200, top: 200, bottom: -200, near: 1, far: 3000 }); scene.add(sun); scene.add(sun.target); this.sun = sun;
    // apron floodlights (a FloodLight whose field is set by renderer3 once the masts are known) and the spot lights for
    // the masts nearest the view (renderer3 assigns them per frame; always in the scene, dark and without shadows by
    // day, so the lights setup of the materials never changes except at the sun's shadow switch, see setFloodSpots)
    const nSp = Q.floodSpots || 0; this.flood = new FloodLight(nSp); scene.add(this.flood);
    this.spots = [];
    for (let k = 0; k < nSp; k++) { const s = new MastSpot(Q.spotMap || 1024); s.castShadow = false; if (Engine.temporalShadows) s.shadow.filterNode = pcfTemporal; scene.add(s); scene.add(s.target); this.spots.push(s); }
    this.aoAmount = uniform(1.0); this.frameNo = 0;
    this.buildPipeline();
    return this;
  }
  // GTAO (three r186 GTAONode) assumes a standard depth buffer: getViewPosition() maps depth*2-1 on WebGL and it
  // discards depth >= 1 as sky. With the reversed depth buffer that turns every pixel into "fully occluded" (back-lit
  // walls and fuselages went black: js/three/dev/envtest.html, 25 Sep 2026). So GTAO gets (a) a proxy camera with the
  // same frustum but a standard projection and (b) the depth re-encoded for that projection by one full-screen pass
  // (float, nearest). Without the reversed depth buffer the pass is skipped. (TRAA has the same assumption in
  // TAAUtils.samplePreviousDepth; that one is patched in the vendored module instead, tools/build3/build.mjs, because
  // TRAA needs the real, jittered camera and copies the depth texture itself.)
  aoInputs(depth) {
    if (!this.reversed) return { depth, camera: this.camera };
    const aoCam = new THREE.PerspectiveCamera(); aoCam.coordinateSystem = this.renderer.coordinateSystem; this.aoCam = aoCam;
    this.aoNear = uniform(0.5); this.aoFar = uniform(180000);
    const vz = TSL.perspectiveDepthToViewZ(depth, this.aoNear, this.aoFar); // handles the reversed encoding
    const std = TSL.viewZToPerspectiveDepth(vz, this.aoNear, this.aoFar);
    const r = TSL.rtt(vec4(std, 0, 0, 1), null, null, { type: THREE.FloatType, minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter, depthBuffer: false, generateMipmaps: false });
    return { depth: r, camera: aoCam };
  }
  syncAOCamera() {
    const a = this.aoCam, c = this.camera; if (!a) return;
    a.fov = c.fov; a.aspect = c.aspect; a.near = c.near; a.far = c.far; a.updateProjectionMatrix();
    a.matrixWorld.copy(c.matrixWorld); a.matrixWorldInverse.copy(c.matrixWorldInverse);
    this.aoNear.value = c.near; this.aoFar.value = c.far;
  }
  buildPipeline() {
    const { renderer, scene, camera, Q } = this;
    const pipe = new THREE.RenderPipeline(renderer); this.pipe = pipe;
    let color, depth, vel;
    if (Q.ao === 'none' || Q.ao === false) { // AO off (js/three/perf.js flags, js/three/perf_phone.js phone tier): one scene pass without GTAO (a velocity target only for TRAA)
      const sp = pass(scene, camera); sp.name = 'scene';
      if (Q.traa) sp.setMRT(mrt({ output, velocity }));
      depth = sp.getTextureNode('depth'); vel = Q.traa ? sp.getTextureNode('velocity') : null;
      color = sp; this.scenePass = sp;
    } else if (Q.ao === 'prepass') {
      const pre = pass(scene, camera); pre.name = 'prepass'; pre.transparent = false;
      pre.setMRT(mrt({ output: packNormalToRGB(normalView), velocity }));
      pre.getTexture('output').type = THREE.UnsignedByteType;
      const nrm = sample((u) => unpackRGBToNormal(pre.getTextureNode().sample(u)));
      depth = pre.getTextureNode('depth'); vel = pre.getTextureNode('velocity');
      const ai = this.aoInputs(depth);
      const aoN = THREE.ao(ai.depth, nrm, ai.camera); aoN.resolutionScale = Q.aoScale; aoN.radius.value = AO_RADIUS; aoN.distanceExponent.value = 1.3; aoN.thickness.value = 2.5; aoN.scale.value = 1.15;
      aoN.useTemporalFiltering = !!Q.traa; // rotate GTAO's noise per frame so TRAA averages it (a static pattern left a mottle on fuselages and under wings)
      this.aoNode = aoN; this.wrapAOTemporal(aoN);
      const sp = pass(scene, camera); sp.name = 'scene';
      sp.contextNode = builtinAOContext(mix(float(1.0), aoN.getTextureNode().sample(screenUV).r, this.aoAmount));
      // the floodlight's direct term is occluded by the same AO (plain texture node of GTAO's target: GTAO is already
      // scheduled by the context above, and a pass-texture here would also run it inside the pre-pass)
      this.flood.aoNode = mix(float(1.0), TSL.texture(aoN.getTextureNode().value, screenUV).r, this.aoAmount);
      color = sp; this.scenePass = sp;
    } else {
      const sp = pass(scene, camera); sp.name = 'scene';
      sp.setMRT(mrt({ output, normal: packNormalToRGB(normalView), velocity }));
      sp.getTexture('normal').type = THREE.UnsignedByteType;
      depth = sp.getTextureNode('depth'); vel = sp.getTextureNode('velocity');
      const nrm = sample((u) => unpackRGBToNormal(sp.getTextureNode('normal').sample(u)));
      const ai = this.aoInputs(depth);
      const aoN = THREE.ao(ai.depth, nrm, ai.camera); aoN.resolutionScale = Q.aoScale; aoN.radius.value = AO_RADIUS; aoN.distanceExponent.value = 1.3; aoN.thickness.value = 2.5; aoN.scale.value = 1.15;
      aoN.useTemporalFiltering = !!Q.traa;
      this.aoNode = aoN; this.wrapAOTemporal(aoN);
      // review round 2: the AO multiplied the whole colour, so sunlit roofs got GTAO's noise and rooftop units lost their
      // shadows. It now enters the ambient term like on the other tiers, from the PREVIOUS frame's GTAO (this pass
      // produces the depth and normal GTAO needs), reprojected with this pixel's velocity; one frame of latency, no extra
      // geometry pass. aoReady keeps it off until GTAO has run once.
      this.aoReady = uniform(0);
      const prevUV = screenUV.sub(velocity.xy.mul(vec2(0.5, -0.5)));
      const aoPrev = mix(float(1.0), TSL.texture(aoN.getTextureNode().value, prevUV).r, this.aoAmount.mul(this.aoReady));
      sp.contextNode = builtinAOContext(aoPrev); this.flood.aoNode = aoPrev;
      const c = sp.getTextureNode('output');
      // the (zero) term keeps GTAO in the output graph, so the pipeline runs it after this pass every frame
      color = vec4(c.rgb.add(aoN.getTextureNode().sample(screenUV).r.mul(0.0)), c.a); this.scenePass = sp;
    }
    this.depthNode = depth; // scene depth for the light sprites' occlusion test (lights.js)
    let hdr = color;
    this.expo = uniform(0.45); // exposure: set per frame by renderer3
    this.casAmount = uniform(0.35);
    if (Q.traa) {
      const tr = THREE.traa(color, depth, vel, camera); tr.useSubpixelCorrection = false; this.traaNode = tr; hdr = tr;
      // contrast-adaptive sharpening (AMD FidelityFX CAS, 5-tap cross) on the resolved TRAA image (review round 2: the
      // TRAA output was visibly softer than the old MSAA image; liveries and window rows blurred at 30-60 m). The
      // amplitude is judged on exposed luminance compressed to 0..1 (x / (1 + x)), the filter applied to the HDR colour;
      // strength casAmount (renderer3: higher when the dynamic resolution renders fewer pixels).
      const tn = tr.getTextureNode(); const px = vec2(1.0).div(screenSize);
      const cC = tn.sample(screenUV), cN = tn.sample(screenUV.add(vec2(0.0, px.y))), cS = tn.sample(screenUV.sub(vec2(0.0, px.y))), cE = tn.sample(screenUV.add(vec2(px.x, 0.0))), cW = tn.sample(screenUV.sub(vec2(px.x, 0.0)));
      const lc = (c) => { const l = luminance(c.rgb).mul(this.expo); return l.div(l.add(1.0)); };
      const LC = lc(cC), LN = lc(cN), LS = lc(cS), LE = lc(cE), LW = lc(cW);
      const mn = min(LC, min(min(LN, LS), min(LE, LW))), mx = max(LC, max(max(LN, LS), max(LE, LW)));
      const amp = sqrt(clamp(min(mn, float(1.0).sub(mx)).div(max(mx, 1e-4)), 0.0, 1.0));
      const wgt = amp.mul(float(-1.0).div(mix(8.0, 5.0, this.casAmount)));
      hdr = vec4(max(cC.rgb.add(cN.rgb.add(cS.rgb).add(cE.rgb).add(cW.rgb).mul(wgt)).div(wgt.mul(4.0).add(1.0)), vec3(0.0)), 1.0);
    }
    // light sprites after TRAA (review round 1: a 1-frame strobe flash kept ~3-5 % of its energy through TRAA's history
    // weighting, and sprites on moving aircraft took the velocity of the background behind them)
    const lp = pass(this.fxScene, this.fxCam); lp.name = 'lights'; this.lightPass = lp;
    hdr = hdr.rgb.add(lp.rgb);
    // exposure (was renderer.toneMappingExposure inside the output transform)
    const exposed = hdr.mul(this.expo);
    let final = exposed;
    this.grade = { sat: uniform(1.0), contrast: uniform(1.6), lookSatLo: uniform(1.0), lookSat: uniform(1.8), // tools/build3/grade_hdr.py, engine_impl.md §4.4
      vignette: uniform(0.18), grain: uniform(0.0), time: uniform(0) };
    if (Q.bloom) {
      // bloom in exposed (display-referred) units, so the threshold means the same by day and by night (review round
      // 1: at night exposure 2.4 multiplied a scene-referred threshold, and everything above it bloomed into a veil).
      // Luminance clamp (soft, Karis-style): a pixel feeds at most ~8x white into the mip chain, so thousands of
      // 2-px light sprites cannot fill it.
      const lum = luminance(exposed);
      const bin = vec4(exposed.div(lum.div(8.0).add(1.0)), 1.0);
      // threshold 1.6 on the clamped value = 2.0 exposed = ~235 sRGB after AgX: only near-white and brighter (sun glints,
      // lamps, the sky next to the sun) blooms
      const bl = THREE.bloom(bin, 0.035, 0.25, 1.6); bl.smoothWidth.value = 1.0; bl.setResolutionScale(Q.bloomScale || 0.5);
      this.bloomNode = bl; final = final.add(bl.rgb);
    }
    // output: AgX + look -> saturation -> vignette (old FINAL_FS: 1 - v * smoothstep(0.15, 0.85, 1.6 r^2)) -> sRGB ->
    // ordered dither (+/- 0.5/255) and optional grain (old FINAL_FS), so gradients in sky and fog do not band
    pipe.outputColorTransform = false;
    const G = this.grade;
    const tm = agxLook(final, { contrast: G.contrast, sat: G.lookSat, satLo: G.lookSatLo });
    const graded = clamp(saturation(tm, G.sat), 0.0, 1.0);
    const d = screenUV.sub(0.5); const r2 = dot(d, d);
    const vig = graded.mul(float(1.0).sub(G.vignette.mul(smoothstep(0.15, 0.85, r2.mul(1.6)))));
    const enc = sRGBTransferOETF(vig);
    const h = (p) => fract(sin(dot(p, vec2(12.9898, 78.233))).mul(43758.5453));
    const px = screenCoordinate.xy;
    const dith = h(px.mul(1.37)).sub(0.5).div(255.0).add(h(px.add(fract(G.time.mul(17.13)).mul(1000.0))).sub(0.5).mul(G.grain));
    pipe.outputNode = vec4(enc.add(dith), 1.0);
    if (Q.aa === 'fxaa' && !Q.traa) pipe.outputNode = THREE.fxaa(pipe.outputNode); // js/three/perf.js phone tier: FXAA (display-referred input) instead of TRAA
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
    cam.updateMatrixWorld(); this.syncAOCamera();
    // cascades: the rig's [1.4d, 5d, 16d] (clamped, js/live/controls.js camera().shadowSplits). The 2-cascade tier used
    // to take the first two (the shadow range collapsed to 5 x the orbit distance, e.g. 300 m at a gate: review round
    // 1); it now keeps the first split and ends at the tier's shadow distance (or the rig's middle split, if larger).
    const r = c.shadowSplits || [300, 1500, 6000]; const Q = this.Q;
    const s = Q.splits ? Q.splits(r, Q) : Q.cascades >= r.length ? r.slice() : Q.cascades === 2 ? [r[0], Math.max(r[0] * 2, Math.min(r[r.length - 1], Math.max(Q.shadowDist, r[1] || 0)))] : r.slice(0, Q.cascades);
    const maxFar = Math.max(200, s[s.length - 1]);
    const key = s.map(v => Math.round(v)).join(',') + ':' + Math.round(near * 100);
    if (key !== this._splitKey && this.csm.mainFrustum) { this._splitKey = key; this.splits = s; this.csm.maxFar = maxFar; this.csm.updateFrustums(); }
    else if (!this.csm.mainFrustum) { this.splits = s; this.csm.maxFar = maxFar; }
    // per-cascade normal offset = 1.25 texels (0.2 m was < 1 texel of a 1024² map over hundreds of metres) and the
    // slope bias scale (CSM3)
    const L = this.csm.lights || [];
    for (let i = 0; i < L.length; i++) {
      const sc = L[i].shadow.camera; const texel = (sc.right - sc.left) / L[i].shadow.mapSize.width; sc.layers.enable(MAST_LAYER); // masts cast sun shadows
      L[i].shadow.normalBias = 1.25 * texel; L[i].shadow.radius = this.sun.shadow.radius;
      if (this.csm.biasU && this.csm.biasU[i]) { this.csm.biasU[i].texel.value = texel; this.csm.biasU[i].range.value = sc.far - sc.near; }
    }
    // un-jittered camera for the light-sprite pass (TRAA jitters this.camera inside the pipeline only)
    this.fxCam.copy(cam); this.fxCam.updateMatrixWorld();
  }
  setSun(dir, color, intensityScale = 1) {
    const s = this.sun; s.position.set(dir[0] * 1000, dir[1] * 1000, dir[2] * 1000); s.target.position.set(0, 0, 0);
    const m = Math.max(color[0], color[1], color[2], 1e-6);
    s.color.setRGB(color[0] / m, color[1] / m, color[2] / m, THREE.LinearSRGBColorSpace); s.intensity = m * intensityScale;
    s.castShadow = dir[1] > 0.02; s.updateMatrixWorld(); s.target.updateMatrixWorld();
    const l = Math.hypot(dir[0], dir[1], dir[2]) || 1; this.sunDirU.value.set(dir[0] / l, dir[1] / l, dir[2] / l);
  }
  // floodlight spots: list = [{x, z, ax, az} | null] per spot; on = lamps on (0..1 x LAMP_M), scale = field level factor.
  // Shadows only while the sun casts none (both switch in the same frame: a castShadow change rebuilds the lights setup
  // of every material, and one rebuild at the sun's switch is what the sun alone already costs)
  setFloodSpots(list, on, scale) {
    const F = this.flood; const cast = !this.sun.castShadow && on > 0;
    for (let k = 0; k < this.spots.length; k++) {
      const s = this.spots[k], m = list && list[k];
      if (m) { s.setMast(m.x, m.z, m.ax, m.az); F.spotU[k].set(m.x, m.z, m.ax, m.az); }
      F.spotOn[k] = m && on > 0 ? 1 : 0; s.intensity = m ? on : 0; s.scale = scale; s.castShadow = cast;
    }
  }
  // GTAO's noise rotation (three r186 GTAONode.updateBefore: _temporalRotations[frameId % 6], _spatialOffsets[frameId % 4])
  // from this engine's frame counter: three's frameId steps once per render call, i.e. by the number of passes per frame
  // (19-22 here), which visited only a few of the 24 patterns and left a static mottle (review round 2)
  wrapAOTemporal(aoN) { const ub = aoN.updateBefore.bind(aoN); aoN.updateBefore = (frame) => ub({ renderer: frame.renderer, frameId: this.frameNo }); }
  // (_sizing: js/three/renderer3.js owns the canvas size under live3 and lets only these writes through)
  resize(cssW, cssH, pixelRatio) { this._sizing = true; try { this.renderer.setPixelRatio(pixelRatio); this.renderer.setSize(cssW, cssH, false); } finally { this._sizing = false; } }
  // per-frame counters (info.render.drawCalls / triangles): three resets them from its own rAF loop, which we do not use
  render() {
    const I = this.renderer.info; I.autoReset = false; I.reset(); shadowFrame.value = (shadowFrame.value + 1) % 64;
    this.frameNo++; if (this.aoReady && this.frameNo > 2) this.aoReady.value = 1;
    this.pipe.render();
  }
}
