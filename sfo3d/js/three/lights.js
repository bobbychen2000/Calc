// Point-light sprites (aircraft nav / strobe / beacon / landing / taxi lights, runway / approach / taxiway / PAPI
// lights, floodlight masts at night, bridge beacons and cab floodlights, markers for aircraft without a model):
// TSL port of js/shaders/sprites.js SPRITE_VS/SPRITE_FS as one instanced additive billboard draw.
// Sprite records are the existing ones ({p, c, i, s, dir?, k?, marker?}) from js/anim/lights.js lightSpriteFn,
// js/aircraft/fleet.js lightSprites, js/live/gates.js, js/live/items.js and js/live/app.js markerSprites.
// Drawn in their own pass AFTER TRAA (js/three/engine.js), with an un-jittered camera, and added to the resolved HDR
// image before exposure, bloom and tone mapping: through TRAA a one-frame strobe flash kept ~3-5 % of its energy and
// sprites on moving aircraft took the velocity of the background (review round 1). Occlusion: the pass has no scene
// depth, so each fragment compares the scene depth at its pixel (the main pass's depth texture) with the sprite's view
// depth (a halo over a nearer surface is hidden, over a farther one it shows, as with a hardware depth test).
// Occlusion, environment review round 2 (truth2-9, look2-1, look2-5):
//  - the core + halo are drawn or not as a whole: ONE test per sprite at the light's own projected pixel (the centre UV,
//    the same for every fragment of the quad), against a tolerance from the scene's depth slope there (the largest view-z
//    step to the 4 neighbouring pixels: a grazing ground plane under a runway light spans tens of metres per pixel, a wall
//    or fuselage seen face-on a few cm) + OCC_MOUNT_M (the lamp's offset from the surface it is mounted on, I) +
//    OCC_PREC × depth (reversed float depth buffer precision, generous). It replaces the slack that grew with distance
//    (2 m camera pull + 1 % of d + 0.5 m: 5.5 m at 300 m, 39.5 m at 3.7 km, through fuselages and bridges); the pull is gone;
//  - the fog aureole is forward scatter along the whole eye-to-lamp path, so geometry nearer than the lamp does not cut it
//    off: per pixel it keeps the part scattered in front of the surface there. Path geometry: a point at distance s on the
//    ray at angle θ from the lamp (distance D) scatters at ψ = θ D / (D − s); with u = D / (D − s) the contribution is
//    p(θ u) du / D (uniform in u), so with the aureole's Gaussian phase in θ the fraction in front of a surface at s_o is
//    F = 1 − erfc(a u_o) / erfc(a), a = θ / θ_aur, u_o = D / (D − s_o) (s_o / D = scene view depth / lamp view depth;
//    F = 1 behind the lamp). Small-angle, single-scatter model (I); erfc: Abramowitz & Stegun 7.1.26 (|ε| < 1.5e-7).
//    Before: every aureole fragment over nearer geometry was discarded - one-row horizontal cuts at each ALS station's
//    row (E7 night fog) and black aircraft silhouettes inside their own landing-light glow.
// Vertex: optional directional lobe pow(max(dir.toCam, 0), k); on-screen radius between 2.2 px (intensity scaled down
// to conserve energy) and 12 px (review round 1: a 1.4 m marker 17 m from the camera was a 110 px glare disk);
// a 1.6x glow. By day (night factor 0) intensities x 0.5;
// all intensities x lampK (lamp units -> the sky model's units once the lamps are on; js/three/tsl/common.js).
// Position lights by day (close-out round 3, env-6): js/env/aircraft_lights.js draws them over their LENS (s 0.08 m) by
// day, energy kept, at the lens luminance (2 x sunlit white paint at the regulatory 2 x minima) instead of the night
// footprint 0.22 m (9 % of white paint: invisible, engine-v3 residual); records with lens: true (iA.w) get no glare halo
// by day (halo x the night factor).
// Markers (records with marker: true; until js/live/app.js sets the flag, records without a direction and with s >= 0.6,
// which only the markers have) fade out between 150 m and 60 m from the camera.
// Fragment: core exp(-22 r^2) + halo 0.08 exp(-6 r^2); the halo is capped at 0.5 in exposed units, so a light never
// spreads into a saturated disk whatever the exposure.
// Aircraft position lights by day (close-out round 2, review finding engine-v3: the green position light at 38 m
// saturated to white with a halo, brighter than sunlit white paint). The day factor 0.5 x lampK (= 1 by day) is ~100x
// the night calibration (lamp units x LAMP_M); it stands in for the higher daytime intensity steps of airfield lighting,
// but a position light has one intensity day and night (14 CFR 25.1391, eCFR read 5 Nov 2026: forward red / green
// >= 40 cd from 0 to 10 deg off dead ahead, 30 cd to 20 deg, 5 cd to 110 deg; rear white >= 20 cd). Energy of a sprite:
// the core exp(-22 r^2) over the quad integrates to 0.143 x (s_eff / d)^2 sr, so a record gives
// E = i x k x 0.408 s^2 / d^2 (sky units; k = the day / night factor x lampK), i.e. at the night calibration
// (k = LAMP_M) i x 13.2 s^2 cd: the position-light records (js/aircraft/fleet.js: i 40, s 0.22; tail i 25, s 0.2) give
// 26 cd and 13 cd, within 1.6x of the rule's 40 / 20 cd, while the day factor made them ~2,600 cd. put(s, true) keeps
// them at the night calibration by day (renderer3: isPositionLight -> fixedK): a faint coloured point, the halo (0.08 x
// the core) below visibility. Strobes, beacons and landing / taxi lights keep the day factor: their records are tuned
// for the night look and ~100x below real units (landing light i 900, s 0.35: 1,450 cd at the night calibration
// against ~1e5 cd for real landing lights, inferred), and the day factor brings them into that range (~150,000 cd).
import { THREE, TSL } from './lib.js';
import { lampK } from './tsl/common.js';
const { Fn, attribute, vec2, vec3, vec4, float, max, min, pow, length, normalize, dot, exp, abs, sqrt, clamp, uniform, cameraPosition, cameraViewMatrix, cameraProjectionMatrix, cameraNear, cameraFar, Discard, If, varying, select, mix, smoothstep, screenUV, perspectiveDepthToViewZ } = TSL;
// occlusion tolerance (header): lamp offset from its mounting surface (I) and depth-precision term (I; reversed float depth)
export const OCC_MOUNT_M = 0.5, OCC_PREC = 2e-4;
// erfc(x), x >= 0 (Abramowitz & Stegun 7.1.26): t (a1 + t (a2 + ...)) exp(-x^2); the polynomial part only (exp separate)
const erfcPoly = (x) => { const t = float(1.0).div(x.mul(0.3275911).add(1.0)); return t.mul(t.mul(t.mul(t.mul(t.mul(1.061405429).sub(1.453152027)).add(1.421413741)).sub(0.284496736)).add(0.254829592)); };

export class Sprites {
  // opts: { depthNode (scene depth texture node), expo (exposure uniform), night (uniform 0..1), slopeTaps (2 | 4) }
  constructor(maxN = 24000, opts = {}) {
    this.max = maxN;
    const g = new THREE.InstancedBufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array([-1, -1, 0, 1, -1, 0, 1, 1, 0, -1, 1, 0]), 3));
    g.setIndex([0, 1, 2, 0, 2, 3]);
    this.aP = new THREE.InstancedBufferAttribute(new Float32Array(maxN * 4), 4); this.aC = new THREE.InstancedBufferAttribute(new Float32Array(maxN * 4), 4); this.aD = new THREE.InstancedBufferAttribute(new Float32Array(maxN * 4), 4);
    // iA = (aureole energy in the record's lamp units, aureole angular radius rad, lobe floor, 0) (environment review
    // look1-1 / look1-5: fog aureole; side / back floor of the directional lobe for lamps whose housing and lens glare
    // are seen from behind)
    this.aA = new THREE.InstancedBufferAttribute(new Float32Array(maxN * 4), 4);
    for (const a of [this.aP, this.aC, this.aD, this.aA]) a.setUsage(THREE.DynamicDrawUsage);
    g.setAttribute('iP', this.aP); g.setAttribute('iC', this.aC); g.setAttribute('iD', this.aD); g.setAttribute('iA', this.aA); g.instanceCount = 0;
    this.camRight = uniform(new THREE.Vector3(1, 0, 0)); this.camUp = uniform(new THREE.Vector3(0, 1, 0)); this.fovScale = uniform(0.001);
    this.depthOn = uniform(1); // QA: 0 turns the occlusion test off (SFO.R.sprites.depthOn.value = 0) to tell an occluded light from a missing one
    const expo = opts.expo || uniform(1.0), night = opts.night || uniform(1.0);
    const m = new THREE.MeshBasicNodeMaterial({ transparent: true, depthWrite: false, depthTest: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide });
    m.fog = false;
    const iP = attribute('iP', 'vec4'), iC = attribute('iC', 'vec4'), iD = attribute('iD', 'vec4'), iA = attribute('iA', 'vec4'), q = attribute('position', 'vec3');
    const vI = varying(float(0), 'vSprI'), vZ = varying(float(0), 'vSprZ'), vTol = varying(float(0), 'vSprTol');
    const vRat = varying(float(1), 'vSprRat'), vAL = varying(float(0), 'vSprAL'), vAr = varying(float(1), 'vSprAr');
    const vUVc = varying(vec2(0.5, 0.5), 'vSprUVc'), vLens = varying(iA.w, 'vSprLens');
    this.texel = uniform(new THREE.Vector2(1 / 1280, 1 / 720));   // one pixel of the scene depth texture (end())
    m.positionNode = Fn(() => {
      const p = iP.xyz, size = iP.w; const toC = cameraPosition.sub(p); const d = length(toC); const tc = toC.div(max(d, 1e-3));
      // branchless (review round 3): with the If / ElseIf size clamp, every sprite between 2.2 and 12 px (neither branch:
      // e.g. an aircraft nav light at 40 m, any light within ~100 m) was not drawn at all in the WebGL 2 backend;
      // only the sub-2.2 px ones were (observed: js/three/dev/envtest.html?sprites=1, row of lights at 20 m: 0 lit pixels,
      // at 175 m: 101; in the app a test sprite 12 m in front of the camera: nothing in the light pass). Same math:
      const cl = max(dot(normalize(iD.xyz), tc), 0.0);
      const lobe = max(select(iD.w.greaterThan(0.0), pow(cl, max(iD.w, 1e-3)).mul(0.97).add(cl.mul(0.03)), float(1.0)), iA.z);
      const mk = select(iD.w.lessThan(-0.5), smoothstep(60.0, 150.0, d), float(1.0)); // marker fade
      const pxSize = max(size.div(d.mul(this.fovScale)), 1e-4);
      const kUp = max(float(2.2).div(pxSize), 1.0), kDown = min(float(12.0).div(pxSize), 1.0); // >= 2.2 px (energy kept), <= 12 px
      const s = size.mul(kUp).mul(kDown).mul(1.6);
      const kk = mix(float(0.5), float(1.0), night).mul(lampK).mul(lobe).mul(mk);
      const I = iC.w.mul(kk).div(kUp.mul(kUp)).div(1.6 * 1.6 * 0.35); // lamp units (tsl/common.js)
      vI.assign(I);
      // fog aureole: a Gaussian of angular radius iA.y carrying the energy iA.x x k x 0.408 size^2 / d^2 at the eye (the
      // core's energy formula, header); the quad grows to 2 aureole radii, the core keeps its size (vRat = quad / core)
      const aOn = iA.x.greaterThan(0.0).and(iA.y.greaterThan(0.0));
      const sQ = select(aOn, max(s, iA.y.mul(d).mul(2.0)), s);
      vRat.assign(sQ.div(s)); vAr.assign(max(iA.y.mul(d).div(sQ), 1e-4));
      vAL.assign(select(aOn, iA.x.mul(kk).mul(0.408).mul(size.mul(size)).div(d.mul(d)).div(iA.y.mul(iA.y).mul(Math.PI)), float(0.0)));
      // the light's own view depth and projected pixel (centre UV, top-left origin as screenUV: engine.js TRAA reprojection)
      const pv = cameraViewMatrix.mul(vec4(p, 1.0)); vZ.assign(pv.z); vTol.assign(pv.z.negate().mul(OCC_PREC).add(OCC_MOUNT_M));
      const pc = cameraProjectionMatrix.mul(pv); const ndc = pc.xy.div(max(pc.w, 1e-6));
      vUVc.assign(vec2(ndc.x.mul(0.5).add(0.5), ndc.y.mul(-0.5).add(0.5)));
      return p.add(this.camRight.mul(q.x).add(this.camUp.mul(q.y)).mul(sQ));
    })();
    const vQ = varying(q.xy, 'vSprQ'), vC = varying(iC.xyz, 'vSprC');
    m.colorNode = Fn(() => {
      const r2 = dot(vQ, vQ); If(r2.greaterThan(1.0), () => { Discard(); });
      let vis = float(1.0), aurF = float(1.0);
      if (opts.depthNode) {
        const zAt = (uv) => perspectiveDepthToViewZ(opts.depthNode.sample(uv).r, cameraNear, cameraFar);
        const tx = this.texel;
        const zC = zAt(vUVc);
        if (opts.debugDepth) return vec4(zC.negate().div(1000.0), vZ.negate().div(1000.0), 0.0, 1.0);
        // core: one test at the light's own pixel, tolerance = local depth slope + mount + precision (header)
        // (the phone tier, opts.slopeTaps 2, takes the vertical neighbours only: a grazing ground plane's slope is vertical
        // on screen; review look2-10)
        const vSl = max(abs(zAt(vUVc.add(vec2(0.0, tx.y))).sub(zC)), abs(zAt(vUVc.sub(vec2(0.0, tx.y))).sub(zC)));
        const slope = opts.slopeTaps === 2 ? vSl : max(vSl, max(abs(zAt(vUVc.add(vec2(tx.x, 0.0))).sub(zC)), abs(zAt(vUVc.sub(vec2(tx.x, 0.0))).sub(zC))));
        const hidden = zC.greaterThan(vZ.add(vTol).add(slope)).and(this.depthOn.greaterThan(0.5));
        vis = select(hidden, float(0.0), float(1.0));
        // aureole: the part of the forward scatter in front of the surface at THIS pixel (header)
        const zP = zAt(screenUV);
        const ratio = clamp(zP.div(min(vZ, -1e-3)), 0.0, 1.0);                    // s_o / D (both view z negative)
        const uo = float(1.0).div(max(float(1.0).sub(ratio), 1e-3));
        const a = sqrt(r2).div(max(vAr, 1e-4)), a1 = a.mul(uo);
        const rr = erfcPoly(a1).div(max(erfcPoly(a), 1e-12)).mul(exp(a.mul(a).sub(a1.mul(a1))));
        aurF = select(ratio.greaterThan(0.999).or(this.depthOn.lessThan(0.5)), float(1.0), clamp(float(1.0).sub(rr), 0.0, 1.0));
      }
      const rc2 = r2.mul(vRat.mul(vRat)); const inCore = select(rc2.lessThan(1.0), float(1.0), float(0.0)); // core radius in its own units
      const halo = min(vI.mul(0.08), float(0.5).div(max(expo, 1e-3))).mul(exp(rc2.mul(-6.0))).mul(select(vLens.greaterThan(0.5), night, float(1.0)));
      const aur = vAL.mul(exp(r2.div(vAr.mul(vAr)).negate())).mul(aurF);
      return vec4(vC.mul(vI.mul(exp(rc2.mul(-22.0))).add(halo).mul(inCore).mul(vis).add(aur)), 1.0);
    })();
    this.mesh = new THREE.Mesh(g, m); this.mesh.frustumCulled = false; this.mesh.renderOrder = 10; this.mesh.name = 'sprites';
    this.n = 0; this.fixedK = 1;
  }
  begin() { this.n = 0; }
  // aircraft position-light records (js/aircraft/fleet.js lightSprites: nav i 40 s 0.22, tail i 25 s 0.2; no direction).
  // Beacons (s 0.25), strobes (s 0.3) and the directional landing / taxi lights are not.
  static isPositionLight(s) { return !s.dir && s.s <= 0.22 && s.i <= 40; }
  // fixed: a light whose record is physical at the night calibration and whose intensity does not change between day and
  // night (aircraft position lights, isPositionLight); its record intensity is scaled by fixedK (renderer3: LAMP_M / the
  // shader's day / night factor), so it keeps the night calibration (lamp units x LAMP_M = sky units) by day too
  // kI: an extra intensity factor (renderer3: the fog transmittance camera -> light for records that do not carry it)
  // aur: aureole energy (lamp units, as s.i) and aurR its angular radius (rad), for records that do not carry them
  // (renderer3: non-photometric lamps in fog); records' own s.aur / s.aurR otherwise
  put(s, fixed = false, kI = 1, aur = null, aurR = 0) {
    if (this.n >= this.max) return; const i = this.n++ * 4; const P = this.aP.array, C = this.aC.array, D = this.aD.array, A = this.aA.array;
    const au = aur != null ? aur : (s.aur || 0), ar = aur != null ? aurR : (s.aurR || 0);
    A[i] = au > 0 && ar > 0 ? au * (fixed ? this.fixedK : 1) : 0; A[i + 1] = ar; A[i + 2] = s.floor || 0; A[i + 3] = s.lens ? 1 : 0;   // lens: a position light drawn at its lens size by day (js/env/aircraft_lights.js NAV_LENS_S): no glare halo by day
    P[i] = s.p[0]; P[i + 1] = s.p[1]; P[i + 2] = s.p[2]; P[i + 3] = s.s;
    C[i] = s.c[0]; C[i + 1] = s.c[1]; C[i + 2] = s.c[2]; C[i + 3] = (fixed ? s.i * this.fixedK : s.i) * kI;
    const d = s.dir; if (d) { D[i] = d[0]; D[i + 1] = d[1]; D[i + 2] = d[2]; D[i + 3] = s.k || 4; }
    else { D[i] = 0; D[i + 1] = 1; D[i + 2] = 0; D[i + 3] = (s.marker || (s.marker == null && s.s >= 0.6)) ? -1 : 0; }   // (marker: false = never a marker: renderer3's lamp reflections)
  }
  end(camera, heightPx) {
    const g = this.mesh.geometry; g.instanceCount = this.n;
    for (const a of [this.aP, this.aC, this.aD, this.aA]) { a.clearUpdateRanges(); a.addUpdateRange(0, this.n * 4); a.needsUpdate = true; }
    const e = camera.matrixWorld.elements; this.camRight.value.set(e[0], e[1], e[2]).normalize(); this.camUp.value.set(e[4], e[5], e[6]).normalize();
    this.fovScale.value = 2 * Math.tan(camera.fov * Math.PI / 360) / Math.max(1, heightPx);
    const h = Math.max(1, heightPx), w = Math.max(1, Math.round(h * (camera.aspect || 1))); this.texel.value.set(1 / w, 1 / h);
  }
}
