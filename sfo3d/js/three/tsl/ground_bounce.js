// Local ground bounce for the light objects get from below (close-out round 3, env-10; engine_closeout.md R2.3).
// The IBL (js/three/sky.js envColor -> PMREM) has ONE ground below the horizon: radiance G = E x a_IBL / pi (renderer3:
// L.ground from the horizontal illuminance E and the whole-airfield mean albedo a_IBL of the airfield bake, grass and sand
// included: (0.303, 0.275, 0.211)), x 0.9 and blended in over the first 20 deg below the horizon. Objects on the apron
// stand on concrete (0.321, 0.306, 0.269) or asphalt, objects on the infield on grass: their light from below is that of
// the ground AROUND them. This adds, per fragment, the difference between the local ground and the IBL ground to the
// diffuse light:
//   dL = albedo x (1 - metalness) x ao x G x 0.9 x C_RAMP x (k_loc - 1) x (1 - n.y) / 2
// with (1 - n.y) / 2 the view factor of a surface with normal n to an infinite ground plane (exact for a uniform ground),
// C_RAMP = 0.85 for the horizon blend of the IBL ground (I: the cosine-weighted share of the ground directions within 20
// deg of the horizon is ~30 % at n.y = 0, at half weight), and k_loc = (local albedo / a_IBL) per channel (clamped to
// 0.5 .. 2) from the airfield bake (js/three/ground.js GroundBakes.apt: rgb albedo, a coverage) at the ground point the
// surface faces: xz + n.xz x min(h, 30 m), averaged over a footprint of 2 h + 8 m (8-96 m; h = height above the apron)
// through the bake's mip chain; outside the airfield bake k_loc = 1 (the IBL as before). Only the albedo changes: the
// ground's lighting is the IBL's (sunlit; the object's own shadow on the ground under it is not modelled, as before: I).
// The specular reflection of the ground is unchanged (dielectric F0 0.04: the diffuse term dominates; I). The night
// floodlight bounce (js/three/flood.js bounce) keeps the field mean (open, documented in environment_impl.md R3).
// Users: js/three/objects.js (terminals, bridges, GSE, masts, cars), js/three/aircraft.js; js/three/buildings3d.js (the
// buildings track's file) can call groundBounce() the same way (docs/requests/env_closeout.md Round 3).
import { THREE, TSL } from '../lib.js';
import { GROUND_Y } from '../../geo.js';
const { vec2, vec3, float, texture, dot, max, min, clamp, mix, step, log2, positionWorld } = TSL;

export const C_RAMP = 0.85, K_MIN = 0.5, K_MAX = 2.0, OFFSET_MAX_M = 30, FOOT_MIN_M = 8, FOOT_MAX_M = 96;
// ref: { tex (THREE.Texture of the airfield bake), AR [s0, t0, w, h] (APT rect in the airport grid), Vw, Uw (grid axes),
// res (m per texel), G (sky.u.ground uniform: the IBL ground radiance x pre) }; set by renderer3 before the materials
export const GB = { ref: null, aIBL: TSL.uniform(new THREE.Vector3(1, 1, 1)), on: TSL.uniform(0) };
export function setGroundRef(ref) { GB.ref = ref; }
/** Added diffuse radiance (pre-exposed sky units, as the emissive slot) for a surface of diffuse albedo `albedo`
 *  (vec3), metalness `metal` (float), ambient occlusion `ao` (float) and world normal `n` (vec3, unit). */
export function groundBounce(albedo, metal, ao, n) {
  const R = GB.ref; if (!R) return vec3(0.0);
  const wp = positionWorld; const h = max(wp.y.sub(GROUND_Y), 0.5);
  const p = wp.xz.add(n.xz.mul(min(h, OFFSET_MAX_M)));
  const st = vec2(dot(p, vec2(R.Vw[0], R.Vw[1])), dot(p, vec2(R.Uw[0], R.Uw[1])));
  const auv = vec2(st.x.sub(R.AR[0]).div(R.AR[2]), float(1.0).sub(st.y.sub(R.AR[1]).div(R.AR[3])));
  const inA = step(0.0, auv.x).mul(step(auv.x, 1.0)).mul(step(0.0, auv.y)).mul(step(auv.y, 1.0));
  const foot = clamp(h.mul(2.0).add(FOOT_MIN_M), FOOT_MIN_M, FOOT_MAX_M);
  const a = texture(R.tex, clamp(auv, 0.0, 1.0)).level(max(log2(foot.div(R.res)), 0.0));
  const k = mix(vec3(1.0), clamp(a.rgb.div(max(GB.aIBL, vec3(1e-3))), K_MIN, K_MAX), a.a.mul(inA).mul(GB.on));
  const vf = float(1.0).sub(clamp(n.y, -1.0, 1.0)).mul(0.5);
  return albedo.mul(float(1.0).sub(metal)).mul(ao).mul(R.G).mul(0.9 * C_RAMP).mul(k.sub(1.0)).mul(vf);
}
