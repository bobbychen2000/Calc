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
// Vertex: optional directional lobe pow(max(dir.toCam, 0), k); on-screen radius between 2.2 px (intensity scaled down
// to conserve energy) and 12 px (review round 1: a 1.4 m marker 17 m from the camera was a 110 px glare disk);
// a 1.6x glow; pulled towards the camera by min(2 m, 5 % of the distance). By day (night factor 0) intensities x 0.5;
// all intensities x lampK (lamp units -> the sky model's units once the lamps are on; js/three/tsl/common.js).
// Markers (records with marker: true; until js/live/app.js sets the flag, records without a direction and with s >= 0.6,
// which only the markers have) fade out between 150 m and 60 m from the camera.
// Fragment: core exp(-22 r^2) + halo 0.08 exp(-6 r^2); the halo is capped at 0.5 in exposed units, so a light never
// spreads into a saturated disk whatever the exposure.
import { THREE, TSL } from './lib.js';
import { lampK } from './tsl/common.js';
const { Fn, attribute, vec2, vec3, vec4, float, max, min, pow, length, normalize, dot, exp, uniform, cameraPosition, cameraViewMatrix, cameraNear, cameraFar, Discard, If, varying, select, mix, smoothstep, screenUV, perspectiveDepthToViewZ } = TSL;

export class Sprites {
  // opts: { depthNode (scene depth texture node), expo (exposure uniform), night (uniform 0..1) }
  constructor(maxN = 24000, opts = {}) {
    this.max = maxN;
    const g = new THREE.InstancedBufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array([-1, -1, 0, 1, -1, 0, 1, 1, 0, -1, 1, 0]), 3));
    g.setIndex([0, 1, 2, 0, 2, 3]);
    this.aP = new THREE.InstancedBufferAttribute(new Float32Array(maxN * 4), 4); this.aC = new THREE.InstancedBufferAttribute(new Float32Array(maxN * 4), 4); this.aD = new THREE.InstancedBufferAttribute(new Float32Array(maxN * 4), 4);
    for (const a of [this.aP, this.aC, this.aD]) a.setUsage(THREE.DynamicDrawUsage);
    g.setAttribute('iP', this.aP); g.setAttribute('iC', this.aC); g.setAttribute('iD', this.aD); g.instanceCount = 0;
    this.camRight = uniform(new THREE.Vector3(1, 0, 0)); this.camUp = uniform(new THREE.Vector3(0, 1, 0)); this.fovScale = uniform(0.001);
    const expo = opts.expo || uniform(1.0), night = opts.night || uniform(1.0);
    const m = new THREE.MeshBasicNodeMaterial({ transparent: true, depthWrite: false, depthTest: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide });
    m.fog = false;
    const iP = attribute('iP', 'vec4'), iC = attribute('iC', 'vec4'), iD = attribute('iD', 'vec4'), q = attribute('position', 'vec3');
    const vI = varying(float(0), 'vSprI'), vZ = varying(float(0), 'vSprZ'), vTol = varying(float(0), 'vSprTol');
    m.positionNode = Fn(() => {
      const p = iP.xyz, size = iP.w; const toC = cameraPosition.sub(p); const d = length(toC); const tc = toC.div(max(d, 1e-3));
      const I = iC.w.mul(mix(float(0.5), float(1.0), night)).mul(lampK).toVar(); // lamp units (tsl/common.js)
      If(iD.w.greaterThan(0.0), () => { const c = max(dot(normalize(iD.xyz), tc), 0.0); I.mulAssign(pow(c, iD.w).mul(0.97).add(c.mul(0.03))); });
      If(iD.w.lessThan(-0.5), () => { I.mulAssign(smoothstep(60.0, 150.0, d)); }); // marker
      const pxSize = size.div(d.mul(this.fovScale)); const s = size.toVar();
      If(pxSize.lessThan(2.2), () => { const k = float(2.2).div(max(pxSize, 1e-4)); s.mulAssign(k); I.divAssign(k.mul(k)); })
        .ElseIf(pxSize.greaterThan(12.0), () => { s.mulAssign(float(12.0).div(pxSize)); });
      s.mulAssign(1.6); I.divAssign(1.6 * 1.6 * 0.35);
      vI.assign(I);
      const c = p.add(tc.mul(min(2.0, d.mul(0.05))));
      vZ.assign(cameraViewMatrix.mul(vec4(c, 1.0)).z); vTol.assign(d.mul(0.01).add(0.5));
      return c.add(this.camRight.mul(q.x).add(this.camUp.mul(q.y)).mul(s));
    })();
    const vQ = varying(q.xy, 'vSprQ'), vC = varying(iC.xyz, 'vSprC');
    m.colorNode = Fn(() => {
      const r2 = dot(vQ, vQ); If(r2.greaterThan(1.0), () => { Discard(); });
      if (opts.depthNode) {
        const sd = opts.depthNode.sample(screenUV).r;
        const sceneZ = perspectiveDepthToViewZ(sd, cameraNear, cameraFar);
        if (opts.debugDepth) return vec4(sd.mul(100.0), sceneZ.negate().div(1000.0), vZ.negate().div(1000.0), 1.0);
        If(sceneZ.greaterThan(vZ.add(vTol)), () => { Discard(); }); // a surface in front of the light
      }
      const halo = min(vI.mul(0.08), float(0.5).div(max(expo, 1e-3))).mul(exp(r2.mul(-6.0)));
      return vec4(vC.mul(vI.mul(exp(r2.mul(-22.0))).add(halo)), 1.0);
    })();
    this.mesh = new THREE.Mesh(g, m); this.mesh.frustumCulled = false; this.mesh.renderOrder = 10; this.mesh.name = 'sprites';
    this.n = 0;
  }
  begin() { this.n = 0; }
  put(s) {
    if (this.n >= this.max) return; const i = this.n++ * 4; const P = this.aP.array, C = this.aC.array, D = this.aD.array;
    P[i] = s.p[0]; P[i + 1] = s.p[1]; P[i + 2] = s.p[2]; P[i + 3] = s.s;
    C[i] = s.c[0]; C[i + 1] = s.c[1]; C[i + 2] = s.c[2]; C[i + 3] = s.i;
    const d = s.dir; if (d) { D[i] = d[0]; D[i + 1] = d[1]; D[i + 2] = d[2]; D[i + 3] = s.k || 4; }
    else { D[i] = 0; D[i + 1] = 1; D[i + 2] = 0; D[i + 3] = (s.marker || s.s >= 0.6) ? -1 : 0; }
  }
  end(camera, heightPx) {
    const g = this.mesh.geometry; g.instanceCount = this.n;
    for (const a of [this.aP, this.aC, this.aD]) { a.clearUpdateRanges(); a.addUpdateRange(0, this.n * 4); a.needsUpdate = true; }
    const e = camera.matrixWorld.elements; this.camRight.value.set(e[0], e[1], e[2]).normalize(); this.camUp.value.set(e[4], e[5], e[6]).normalize();
    this.fovScale.value = 2 * Math.tan(camera.fov * Math.PI / 360) / Math.max(1, heightPx);
  }
}
