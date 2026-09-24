// Point-light sprites (aircraft nav / strobe / beacon / landing / taxi lights, runway / approach / taxiway / PAPI
// lights, floodlight masts at night, bridge beacons and cab floodlights, markers for aircraft without a model):
// TSL port of js/shaders/sprites.js SPRITE_VS/SPRITE_FS as one instanced additive billboard draw.
// Sprite records are the existing ones ({p, c, i, s, dir?, k?}) from js/anim/lights.js lightSpriteFn,
// js/aircraft/fleet.js lightSprites, js/live/gates.js and js/live/items.js.
// Vertex: optional directional lobe pow(max(dir.toCam, 0), k); a minimum on-screen size of 2.2 px with intensity
// scaled down to conserve energy; a 1.6x glow; pulled towards the camera by min(2 m, 5 % of the distance).
// Fragment: core exp(-22 r^2) + halo 0.08 exp(-6 r^2), additive, HDR (feeds bloom).
import { THREE, TSL } from './lib.js';
const { Fn, attribute, vec2, vec3, vec4, float, max, min, pow, length, normalize, dot, exp, uniform, cameraPosition, Discard, If, varying, select } = TSL;

export class Sprites {
  constructor(max = 24000) {
    this.max = max;
    const g = new THREE.InstancedBufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array([-1, -1, 0, 1, -1, 0, 1, 1, 0, -1, 1, 0]), 3));
    g.setIndex([0, 1, 2, 0, 2, 3]);
    this.aP = new THREE.InstancedBufferAttribute(new Float32Array(max * 4), 4); this.aC = new THREE.InstancedBufferAttribute(new Float32Array(max * 4), 4); this.aD = new THREE.InstancedBufferAttribute(new Float32Array(max * 4), 4);
    for (const a of [this.aP, this.aC, this.aD]) a.setUsage(THREE.DynamicDrawUsage);
    g.setAttribute('iP', this.aP); g.setAttribute('iC', this.aC); g.setAttribute('iD', this.aD); g.instanceCount = 0;
    this.camRight = uniform(new THREE.Vector3(1, 0, 0)); this.camUp = uniform(new THREE.Vector3(0, 1, 0)); this.fovScale = uniform(0.001);
    const m = new THREE.MeshBasicNodeMaterial({ transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide });
    m.fog = false;
    const iP = attribute('iP', 'vec4'), iC = attribute('iC', 'vec4'), iD = attribute('iD', 'vec4'), q = attribute('position', 'vec3');
    const vI = varying(float(0), 'vSprI');
    m.positionNode = Fn(() => {
      const p = iP.xyz, size = iP.w; const toC = cameraPosition.sub(p); const d = length(toC); const tc = toC.div(max(d, 1e-3));
      const I = iC.w.toVar();
      If(iD.w.greaterThan(0.0), () => { const c = max(dot(normalize(iD.xyz), tc), 0.0); I.mulAssign(pow(c, iD.w).mul(0.97).add(c.mul(0.03))); });
      const pxSize = size.div(d.mul(this.fovScale)); const s = size.toVar();
      If(pxSize.lessThan(2.2), () => { const k = float(2.2).div(max(pxSize, 1e-4)); s.mulAssign(k); I.divAssign(k.mul(k)); });
      s.mulAssign(1.6); I.divAssign(1.6 * 1.6 * 0.35);
      vI.assign(I);
      return p.add(this.camRight.mul(q.x).add(this.camUp.mul(q.y)).mul(s)).add(tc.mul(min(2.0, d.mul(0.05))));
    })();
    const vQ = varying(q.xy, 'vSprQ'), vC = varying(iC.xyz, 'vSprC');
    m.colorNode = Fn(() => {
      const r2 = dot(vQ, vQ); If(r2.greaterThan(1.0), () => { Discard(); });
      const k = exp(r2.mul(-22.0)).add(exp(r2.mul(-6.0)).mul(0.08));
      return vec4(vC.mul(vI).mul(k), 1.0);
    })();
    this.mesh = new THREE.Mesh(g, m); this.mesh.frustumCulled = false; this.mesh.renderOrder = 10; this.mesh.name = 'sprites';
    this.n = 0;
  }
  begin() { this.n = 0; }
  put(s) {
    if (this.n >= this.max) return; const i = this.n++ * 4; const P = this.aP.array, C = this.aC.array, D = this.aD.array;
    P[i] = s.p[0]; P[i + 1] = s.p[1]; P[i + 2] = s.p[2]; P[i + 3] = s.s;
    C[i] = s.c[0]; C[i + 1] = s.c[1]; C[i + 2] = s.c[2]; C[i + 3] = s.i;
    const d = s.dir; if (d) { D[i] = d[0]; D[i + 1] = d[1]; D[i + 2] = d[2]; D[i + 3] = s.k || 4; } else { D[i] = 0; D[i + 1] = 1; D[i + 2] = 0; D[i + 3] = 0; }
  }
  end(camera, heightPx) {
    const g = this.mesh.geometry; g.instanceCount = this.n;
    for (const a of [this.aP, this.aC, this.aD]) { a.clearUpdateRanges(); a.addUpdateRange(0, this.n * 4); a.needsUpdate = true; }
    const e = camera.matrixWorld.elements; this.camRight.value.set(e[0], e[1], e[2]).normalize(); this.camUp.value.set(e[4], e[5], e[6]).normalize();
    this.fovScale.value = 2 * Math.tan(camera.fov * Math.PI / 360) / Math.max(1, heightPx);
  }
}
