// Rain and drizzle particles for the three.js renderer (environment spec §4.6 / §7.5; docs/research/environment_impl.md
// §3). Parameters from js/env/atmo/weather_fx.js rainParams (Marshall–Palmer count ratio, fall speed of the median
// volume diameter, streak = v × 1/60 s; the A-RAIN gate checks them): one instanced draw of camera-facing quads in a
// world-anchored lattice wrapped into a box of ±40 m around the camera (stable when the camera moves), each drop a
// streak along its velocity (fall speed + the METAR wind, true direction), drizzle a short blob that falls at 1.5 m/s.
// Drawn in the light-sprite pass (js/three/engine.js fxScene: after TRAA, additive, scene depth for occlusion as
// js/three/lights.js), because TRAA's history rejects thin fast streaks. Radiance (I): a drop refracts its
// surroundings, so a streak adds a fraction of the ambient sky radiance (skyUp × RAIN_K in renderer3), drawn at least
// 1 px wide and long (length energy kept; see k below). No rain above
// the base of the lowest BKN/OVC layer (rainTop). Splash sprites on the pavement are not drawn (I).
import { THREE, TSL } from './lib.js';
const { Fn, attribute, vec2, vec3, vec4, float, max, min, length, normalize, cross, dot, exp, uniform, mod, cameraPosition, cameraViewMatrix, cameraNear, cameraFar, Discard, If, varying, screenUV, perspectiveDepthToViewZ, select } = TSL;

export class Rain {
  constructor(maxN = 60000, opts = {}) {
    this.max = maxN;
    const g = new THREE.InstancedBufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array([-1, 0, 0, 1, 0, 0, 1, 1, 0, -1, 1, 0]), 3));
    g.setIndex([0, 1, 2, 0, 2, 3]);
    const seeds = new Float32Array(maxN * 4); let s = 0x9e3779b9;
    const r = () => { s ^= s << 13; s >>>= 0; s ^= s >> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
    for (let i = 0; i < maxN * 4; i++) seeds[i] = r();
    g.setAttribute('iS', new THREE.InstancedBufferAttribute(seeds, 4)); g.instanceCount = 0;
    this.u = { vel: uniform(new THREE.Vector3(0, -5, 0)), half: uniform(40), streak: uniform(0.08), width: uniform(0.0014), col: uniform(new THREE.Color(0, 0, 0)), time: uniform(0), fovScale: uniform(0.001), top: uniform(1e6), groundY: uniform(opts.groundY ?? 3),
      // floodlit drops (review look1-4: at night the streaks took only the sky radiance and vanished under 20-lx floods):
      // a drop refracts its surroundings (Garg & Nayar 2007: the drop's radiance is a weighted mean of the environment over
      // its ~165° field of view), so under the floods it adds E_flood / π (the lit surroundings' mean radiance, I) with the
      // same display weight as the sky term: floodC = flood colour x floods' intensity x RAIN_K / π (renderer3)
      floodC: uniform(new THREE.Color(0, 0, 0)), density: uniform(1) };
    const U = this.u;
    const m = new THREE.MeshBasicNodeMaterial({ transparent: true, depthWrite: false, depthTest: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide });
    m.fog = false;
    const iS = attribute('iS', 'vec4'), q = attribute('position', 'vec3');
    const vI = varying(float(0), 'vRainI'), vZ = varying(float(0), 'vRainZ'), vQ = varying(vec2(0), 'vRainQ'), vCol = varying(vec3(0), 'vRainC');
    const field = opts.floodField || null;   // (p) -> scalar floodlight irradiance (lamp units), js/three/sky.js floodField
    m.positionNode = Fn(() => {
      const box = U.half.mul(2.0);
      const lo = cameraPosition.sub(vec3(U.half));
      // world-anchored lattice point (seed x box) moved by the velocity, wrapped into the camera box
      const pw = mod(iS.xyz.mul(box).add(U.vel.mul(U.time.add(iS.w.mul(10.0)))).sub(lo), box).add(lo).toVar();
      const toC = cameraPosition.sub(pw); const d = max(length(toC), 0.05);
      const dirS = normalize(U.vel); const side = normalize(cross(dirS, toC.div(d)));
      const px = d.mul(U.fovScale);                                   // metres per pixel at the drop
      const w = max(U.width, px).mul(0.5), len = max(U.streak, px);   // >= 1 px wide and long
      // energy kept along the streak (a sub-pixel streak is drawn 1 px long at its length / px); across it the 1-px
      // streak stands for the drops of its pixel column (the drawn count is ~1e-4 of the physical one, so the
      // physical per-drop width factor would leave no rain visible at all: run 2, rain_day render; I, display weight)
      const k = max(U.streak, U.width).div(len);
      const above = select(pw.y.greaterThan(U.top).or(pw.y.lessThan(U.groundY)), float(0.0), float(1.0));
      vI.assign(k.mul(above).mul(max(float(1.0).sub(d.div(U.half.mul(1.2))), 0.0)).mul(U.density));
      vCol.assign(field ? U.col.add(U.floodC.mul(field(pw))) : U.col);
      const c = pw.sub(dirS.mul(len.mul(q.y))).add(side.mul(w.mul(q.x)));
      vZ.assign(cameraViewMatrix.mul(vec4(pw, 1.0)).z); vQ.assign(q.xy);
      return c;
    })();
    m.colorNode = Fn(() => {
      If(vI.lessThan(1e-4), () => { Discard(); });
      if (opts.depthNode) {
        const sceneZ = perspectiveDepthToViewZ(opts.depthNode.sample(screenUV).r, cameraNear, cameraFar);
        If(sceneZ.greaterThan(vZ.add(0.3)), () => { Discard(); });
      }
      return vec4(vCol.mul(vI).mul(exp(vQ.x.mul(vQ.x).mul(-2.0))), 1.0);
    })();
    this.mesh = new THREE.Mesh(g, m); this.mesh.frustumCulled = false; this.mesh.renderOrder = 9; this.mesh.name = 'rain'; this.mesh.visible = false;
    this.params = null;
  }
  // P = rainParams(...) or null; t (s); colour = raw sky units x pre; top = rain ceiling (world y)
  update(P, cam, t, colour, top, fovScale, showerK = 1, floodC = null) {
    const g = this.mesh.geometry, U = this.u; this.params = P;
    if (floodC) U.floodC.value.setRGB(floodC[0], floodC[1], floodC[2]); else U.floodC.value.setRGB(0, 0, 0);
    // per-streak weight: the drawn count is the tier budget's share of the high-tier count (weather_fx.js rainParams
    // P.density = count_tier / count_high); the weight is divided by it so the rain's visual density does not change with
    // the tier (review look1-8: the phone tier drew 5x fewer streaks of the same weight)
    U.density.value = P && P.density > 0 ? 1 / P.density : 1;
    if (!P || !(P.count > 0)) { this.mesh.visible = false; g.instanceCount = 0; return 0; }
    const n = Math.min(this.max, Math.round(P.count * showerK));
    g.instanceCount = n; this.mesh.visible = n > 0;
    U.vel.value.set(P.wind[0], -P.vFall, P.wind[1]); U.half.value = P.half; U.streak.value = P.streaks ? P.streak : 0; U.width.value = P.D0mm / 1000;
    U.col.value.setRGB(colour[0], colour[1], colour[2]); U.time.value = t; U.top.value = top; U.fovScale.value = fovScale;
    return n;
  }
}
