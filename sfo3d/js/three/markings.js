// Surface-marking ribbons (taxiway centrelines, holding positions, enhanced centrelines, edges, service roads, stand
// lead-ins, stop bars, red equipment boxes) for the three.js renderer: TSL port of js/live/markings.js MARK_VS/MARK_FS.
// The ribbon geometry is built unchanged by js/live/markings.js buildMarkings / buildStandMarks (via js/live/world.js).
// Vertex: each line keeps a minimum on-screen half width of 0.75 px, with its opacity reduced in proportion (area-
// correct), so thin FAA lines stay stable at a distance. Fragment: dashes anti-aliased with fwidth, averaging out far
// away; fade between 2.5 and 6 km. Lit by three.js (sun, CSM shadows, IBL) with an up normal.
import { THREE, TSL } from './lib.js';
import { geometryOf } from './convert.js';
const { Fn, attribute, varying, vec3, vec4, float, texture, max, mod, smoothstep, length, fwidth, positionWorld, cameraPosition, cameraViewMatrix, uniform, normalize } = TSL;

export function markingMaterial({ noiseTex, pxScale, reversed }) {
  const off = reversed ? 1 : -1;
  const mat = new THREE.MeshStandardNodeMaterial({ side: THREE.DoubleSide, transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: off * 2, polygonOffsetUnits: off * 6, roughness: 0.6, metalness: 0 });
  const aPos = attribute('position', 'vec3'), aNrm = attribute('normal', 'vec3'), aExt = attribute('extra', 'vec4');
  // aNrm.xz = unit perpendicular, aNrm.y = dash duty ratio; aExt = (half width, side -1/+1, distance along, dash period)
  const dist = length(aPos.sub(cameraPosition)); const px = dist.mul(pxScale).mul(0.75); const hw = max(aExt.x, px);
  mat.positionNode = aPos.add(vec3(aNrm.x, 0.0, aNrm.z).mul(aExt.y).mul(hw));
  const vA = varying(aExt.x.div(hw), 'vA'), vAlong = varying(aExt.z, 'vAlong'), vPeriod = varying(aExt.w, 'vPeriod'), vDuty = varying(aNrm.y.mul(aExt.w), 'vDuty');
  const col = attribute('color', 'vec4');
  mat.colorNode = Fn(() => {
    const wp = positionWorld; return vec4(col.rgb.mul(texture(noiseTex, wp.xz.mul(0.23)).r.mul(0.18).add(0.82)), 1.0);
  })();
  mat.opacityNode = Fn(() => {
    const a = col.a.mul(vA).toVar();
    const fw = fwidth(vAlong).add(1e-4);
    const f = mod(vAlong, max(vPeriod, 1e-3));
    const dash = smoothstep(fw.negate(), fw, f).mul(float(1.0).sub(smoothstep(vDuty.sub(fw), vDuty.add(fw), f))).mul(float(1.0).sub(smoothstep(vPeriod.mul(0.35), vPeriod, fw)));
    // far away the dash pattern averages to its duty ratio
    const avg = vDuty.div(max(vPeriod, 1e-3));
    const dashed = dash.add(avg.mul(smoothstep(vPeriod.mul(0.35), vPeriod, fw)));
    a.mulAssign(TSL.select(vPeriod.greaterThan(0.0), dashed, float(1.0)));
    const d = length(cameraPosition.sub(positionWorld));
    a.mulAssign(float(1.0).sub(smoothstep(2500.0, 6000.0, d)));
    return a;
  })();
  mat.normalNode = normalize(cameraViewMatrix.mul(vec4(0, 1, 0, 0)).xyz);
  return mat;
}
export function markingMeshes(world, mat) {
  const group = new THREE.Group(); group.name = 'markings';
  for (const it of world.items) if (it.prog === 'mark' && it.mesh) { const m = new THREE.Mesh(geometryOf(it.mesh), mat); m.frustumCulled = false; m.receiveShadow = true; m.renderOrder = 1; m.matrixAutoUpdate = false; group.add(m); }
  return group;
}
