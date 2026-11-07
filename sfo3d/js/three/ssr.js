// Screen-space reflections of objects in wet pavement (close-out round 3, env-2; spec §7.6 "SSR on the high tier";
// environment review look2-4: in daylight rain the wet apron mirrored only the sky / IBL and the lamp sprites, while the
// reference sfo_rain_day_t2_2011_960.jpg (CC BY 2.0) shows mirror images of stairs, GSE and aircraft on the wet stand).
// For a ground fragment (the paved airfield is flat: normal +y) the reflected view ray is marched in VIEW space through
// the current frame's pre-pass depth (js/three/engine.js 'prepass' tiers: high / ultra / medium; the phone tier draws in
// one MRT pass and has no depth before the ground is shaded: no SSR there): N steps at geometric distances t_i =
// T0 q^i up to T_MAX. A step where the ray is behind the visible surface AND that surface is not the ground itself is a
// candidate (its reconstructed world height must exceed the reflecting fragment's by GROUND_EPS + PIX_K pixel rows of
// height at its depth: a ray reflected upwards off the flat pavement cannot meet the pavement again, but at grazing
// views one pixel row spans tens of metres of ground, so a depth sampled one row off puts the pavement "above itself");
// 6 bisection steps between the last step in front and the candidate; accepted when the refined point lies behind the
// surface by less than a thickness (THICK_M + THICK_K x depth: a front face, not a ray passing behind a silhouette) and
// that surface still passes the ground test; otherwise the march goes on. (Close-out round 3 dev checks, skytest.html
// ?ssr=1 / ?ssr=dbg: the thickness tested at the coarse step - up to 30 % of t - rejected the 100-150 m reflections;
// without the pixel-row tolerance false hits filled a 90-460 m band and contour arcs that moved with the TRAA jitter.)
// The radiance at the hit is the PREVIOUS frame's resolved HDR image (TRAA history,
// js/three/engine.js traaNode: un-jittered, pre-exposed, without the light sprites, which renderer3 mirrors itself),
// reprojected with the previous frame's view-projection (renderer3 ssrPrevVP) - the usual "previous-frame SSR" (one frame
// of latency; exact for a still camera). The term is added to the ground's emission as
//   dL = w x specW x (L_hit - L_env)
// L_env = the sky the material's IBL already mirrors along that ray (sky.js skyAlong for a mirror, its blurred sky for a
// rough film), specW = the split-sum specular weight F0 x A + B (Karis 2014 analytic approximation of the DFG term, F0 0.04)
// that three applies to that IBL radiance, and w = confidence: the gloss (1 at roughness <= 0.08, 0 at >= 0.4: the wet film
// 0.22 keeps ~0.57, puddles 0.03 all; dry pavement 0.8-0.95 none), the screen-edge fade (4 % of the frame), the
// ray-distance fade (the last 25 % of T_MAX) and the history being valid (renderer3 ssrOn: off until 2 frames after a
// camera cut, a resize or the first frame). Blur of a rough film's reflection is not modelled (the single history sample
// is sharp; TRAA softens it): I. Off-screen or occluded reflected objects fall back to the sky (the SSR limit).
import { THREE, TSL } from './lib.js';
const { Fn, vec2, vec3, vec4, float, uniform, dot, max, min, clamp, mix, smoothstep, step, exp2, normalize, reflect, select, If, Loop, Break, abs, texture, length, positionWorld, cameraPosition, cameraViewMatrix, cameraWorldMatrix, cameraProjectionMatrix, cameraNear, cameraFar, perspectiveDepthToViewZ, screenSize } = TSL;

export const SSR_N = 24, SSR_T0 = 0.4, SSR_TMAX = 160, SSR_THICK_M = 1.5, SSR_THICK_K = 0.02, SSR_MAX_DIST = 900, SSR_EDGE = 0.04;
export const SSR_ROUGH = [0.08, 0.4], SSR_GROUND_EPS = 0.3, SSR_PIX_K = 2.0;
const Q_STEP = Math.pow(SSR_TMAX / SSR_T0, 1 / (SSR_N - 1));

/** Karis 2014 (UE4 mobile) EnvBRDFApprox: the split-sum DFG term F0 x A + B for roughness r and n.v. */
export const envBRDF = (F0, r, NoV) => {
  const c0 = vec4(-1.0, -0.0275, -0.572, 0.022), c1 = vec4(1.0, 0.0425, 1.04, -0.04);
  const q = c0.mul(r).add(c1);
  const a004 = min(q.x.mul(q.x), exp2(NoV.mul(-9.28))).mul(q.x).add(q.y);
  const AB = vec2(-1.04, 1.04).mul(a004).add(q.zw);
  return AB.x.mul(F0).add(AB.y);
};

// The ground material is also drawn by the depth / normal PRE-PASS, which writes the very depth texture the march reads:
// sampling it there is a WebGL feedback loop (GL_INVALID_OPERATION, the draw is skipped; seen on the dev page, close-out
// round 3). The term is therefore built only for passes without an MRT (the lit scene pass of the prepass tiers); in
// any pass with an MRT (the pre-pass; the phone tier's single pass) it is vec3(0) and samples nothing.
class SceneOnlyNode extends THREE.Node {
  static get type() { return 'SceneOnlyNode'; }
  constructor(node) { super('vec3'); this.node = node; }
  setup(builder) { const m = builder.renderer && builder.renderer.getMRT ? builder.renderer.getMRT() : null; return m ? vec3(0.0) : this.node; }
}

/** ctx: { depth (pre-pass depth TextureNode), history (THREE.Texture of the previous resolved frame), prevVP (uniform
 *  Matrix4), on (uniform 0 / 1), sky (js/three/sky.js Sky: skyAlong / skyEnvBlur) }. Returns (rough) => vec3 dL for the
 *  current ground fragment (positionWorld, flat normal). */
export function makeSSR(ctx) {
  const { depth, history, prevVP, on, sky } = ctx; const DBG = +ctx.debug || 0;   // debug modes (dev page ?ssr=dbg&ssrdbg=k; written as grey, read back from the meter): 1 const 1, 2 hit, 3 hit x (surface y - ground y), 4 hit x scene depth, 5 hit x t, 6 candidates
  const hist = texture(history);
  const screenOf = (pv) => { const c = cameraProjectionMatrix.mul(vec4(pv, 1.0)); const n = c.xy.div(max(c.w, 1e-6)); return vec2(n.x.mul(0.5).add(0.5), n.y.mul(-0.5).add(0.5)); };
  const zAt = (uv) => perspectiveDepthToViewZ(depth.sample(uv).r, cameraNear, cameraFar);
  // world height of the visible surface along the view ray through the view-space point pv, at view depth zs
  const sceneY = (pv, zs) => cameraWorldMatrix.mul(vec4(pv.mul(zs.div(pv.z)), 1.0)).y;
  // vertical angle of one pixel (rad): one pixel row spans dS x pixA metres of height at view depth dS, so a depth sampled
  // one or two rows off at a grazing view puts the pavement up to ~2 x dS x pixA above itself: the ground tolerance
  const pixA = float(2.0).div(cameraProjectionMatrix.element(1).y.mul(screenSize.y));
  const above = (pv, zs, gy) => sceneY(pv, zs).greaterThan(gy.add(zs.negate().mul(pixA).mul(SSR_PIX_K)));
  return (rough) => new SceneOnlyNode(Fn(() => {
    const out = vec3(0.0).toVar();
    const wp = positionWorld; const toP = wp.sub(cameraPosition).toVar(); const dist = length(toP).toVar();
    const gloss = float(1.0).sub(smoothstep(SSR_ROUGH[0], SSR_ROUGH[1], rough));
    If(on.greaterThan(0.5).and(gloss.greaterThan(0.01)).and(dist.lessThan(SSR_MAX_DIST)), () => {
      const V = toP.div(max(dist, 1e-3)); const Rw = reflect(V, vec3(0.0, 1.0, 0.0)).toVar();
      const P0 = cameraViewMatrix.mul(vec4(wp, 1.0)).xyz.toVar(); const Dv = cameraViewMatrix.mul(vec4(Rw, 0.0)).xyz.toVar();
      const tHit = float(-1.0).toVar(), tPrev = float(0.0).toVar(), t = float(SSR_T0).toVar(), b = float(0.0).toVar();
      const gy = wp.y.add(SSR_GROUND_EPS); const nCand = float(0.0).toVar(), dbgY = float(0.0).toVar(), dbgZ = float(0.0).toVar();
      Loop(SSR_N, () => {
        const pv = P0.add(Dv.mul(t)).toVar(); const uv = screenOf(pv);
        If(uv.x.lessThan(0.0).or(uv.x.greaterThan(1.0)).or(uv.y.lessThan(0.0)).or(uv.y.greaterThan(1.0)).or(pv.z.greaterThan(-0.2)), () => { Break(); });
        const zs = zAt(uv).toVar();
        If(pv.z.negate().greaterThan(zs.negate()).and(zs.negate().lessThan(cameraFar.mul(0.9))).and(above(pv, zs, gy)), () => {
          // candidate: bisection between the last step in front of the surface and this one
          nCand.addAssign(1.0);
          const a = tPrev.toVar(); b.assign(t);
          Loop({ start: 0, end: 6, type: 'int', condition: '<', name: 'k' }, () => {
            const m = a.add(b).mul(0.5); const pm = P0.add(Dv.mul(m)); const zm = zAt(screenOf(pm));
            If(pm.z.negate().greaterThan(zm.negate()), () => { b.assign(m); }).Else(() => { a.assign(m); });
          });
          const pb = P0.add(Dv.mul(b)).toVar(); const zb = zAt(screenOf(pb)).toVar();
          If(pb.z.negate().sub(zb.negate()).lessThan(pb.z.negate().mul(SSR_THICK_K).add(SSR_THICK_M)).and(above(pb, zb, gy)), () => { tHit.assign(b); if (DBG) { dbgY.assign(sceneY(pb, zb).sub(wp.y)); dbgZ.assign(zb.negate()); } Break(); });
        });
        tPrev.assign(t); t.mulAssign(Q_STEP);
      });
      If(tHit.greaterThan(0.0), () => {
        const Ph = wp.add(Rw.mul(tHit));
        const uvNow = screenOf(P0.add(Dv.mul(tHit)));
        const pc = prevVP.mul(vec4(Ph, 1.0)); const pn = pc.xy.div(max(pc.w, 1e-6)); const uvPrev = vec2(pn.x.mul(0.5).add(0.5), pn.y.mul(-0.5).add(0.5));
        const inPrev = step(0.0, uvPrev.x).mul(step(uvPrev.x, 1.0)).mul(step(0.0, uvPrev.y)).mul(step(uvPrev.y, 1.0)).mul(step(0.0, pc.w));
        const edge = smoothstep(0.0, SSR_EDGE, uvNow.x).mul(smoothstep(0.0, SSR_EDGE, float(1.0).sub(uvNow.x))).mul(smoothstep(0.0, SSR_EDGE, uvNow.y)).mul(smoothstep(0.0, SSR_EDGE, float(1.0).sub(uvNow.y)));
        const far = float(1.0).sub(smoothstep(SSR_TMAX * 0.75, SSR_TMAX, tHit));
        const Lhit = hist.sample(clamp(uvPrev, 0.0, 1.0)).rgb;
        const Ru = vec3(Rw.x, max(Rw.y, 0.003), Rw.z);
        const Lenv = mix(sky.skyAlong(wp, Ru, 1), sky.skyEnvBlur(Ru), smoothstep(0.05, 0.3, rough));
        const NoV = max(V.y.negate(), 1e-3);
        out.assign(Lhit.sub(Lenv).mul(envBRDF(float(0.04), rough, NoV)).mul(gloss.mul(edge).mul(far).mul(inPrev)));
      });
      if (DBG) { const h = step(0.0, tHit); out.assign(vec3([float(0.0), float(1.0), h, h.mul(dbgY), h.mul(dbgZ), h.mul(max(tHit, 0.0)), nCand][DBG] || float(0.0))); }
    });
    return out;
  })());
}
