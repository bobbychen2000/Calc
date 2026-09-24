// PBR material for the procedurally built world objects (terminals, tower, ITB, garages, masts, EMAS beds, approach
// light piers, stand equipment, jet bridges, ground service vehicles): TSL port of js/shaders/objects.js OBJ_FS.
// Per-vertex inputs from js/geom.js Geo: color (rgba) and extra = (roughness, metalness, material id, emissive).
// Material ids (objects.js): 1 glass curtain wall, 2 concrete panels, 3 garage facade, 4 corrugated metal, 5 flat
// roof, 6 punched windows, 7 foliage, 9 jet-bridge tunnel (ribs + window strip), 11 garage roof with cars, 12 tower cab
// glass, 13 hangar door, 14 lamp lens (lit at night), 15 apron service facade, 16 tower LED glass ribbon,
// 20 vehicle paint (tinted per instance). Lighting, shadows, IBL reflections, fog and AO come from three.js; the
// old hemisphere ambient and its hand-made contact AO are replaced by PMREM IBL + GTAO (a mild height AO remains).
import { THREE, TSL } from './lib.js';
import { hash12 } from './tsl/common.js';
const { Fn, uniform, attribute, vec2, vec3, vec4, float, texture, dot, abs, max, min, mix, smoothstep, step, clamp, normalize, length, floor, fract, sin, atan, select, If, fwidth, positionWorld, cameraPosition, normalWorld, cameraViewMatrix } = TSL;

const gridLine = (x, period, w) => { const f = abs(fract(x.div(period).add(0.5)).sub(0.5)).mul(period); const fw = fwidth(x).mul(0.8); return float(1.0).sub(smoothstep(w, fw.add(w), f)); };

// opts: { instanced: bool (per-instance iData: x = tunnel length, rgb/w = vehicle tint), instColor: bool (colour and
// extra per instance in iCol / iExt: unit boxes and cylinders of the bridges), noiseTex, night (uniform), time (uniform) }
export function objectMaterial(opts) {
  const { noiseTex, night, time } = opts;
  const mat = new THREE.MeshStandardNodeMaterial({ side: THREE.DoubleSide });
  const core = () => {
    const col = opts.instColor ? attribute('iCol', 'vec4') : attribute('color', 'vec4'); const ext = opts.instColor ? attribute('iExt', 'vec4') : attribute('extra', 'vec4');
    const LP = attribute('position', 'vec3'); const LN = normalize(attribute('normal', 'vec3')).toVar(); const vUV = attribute('uv', 'vec2');
    const idata = opts.instanced && !opts.instColor ? attribute('iData', 'vec4') : vec4(0);
    const wp = positionWorld; const dist = length(cameraPosition.sub(wp)).toVar();
    const albedo = col.rgb.toVar(); const rough = ext.x.toVar(), metal = ext.y.toVar(); const matId = floor(ext.z.add(0.5)).toVar(); const emis = ext.w;
    if (opts.instanced && !opts.instColor) albedo.assign(mix(albedo, idata.rgb, step(0.5, idata.w).mul(step(19.5, ext.z)).mul(step(ext.z, 20.5))));
    const wt = normalize(vec2(LN.z.negate(), LN.x).add(1e-5));
    const u = dot(LP.xz, wt).toVar(), v = LP.y.toVar();
    const ao = float(1.0).toVar(); const extraEmis = vec3(0).toVar(); const nPert = vec3(0).toVar();
    const isWall = float(1.0).sub(abs(LN.y));
    // noise samples used by several ids (sampled once, outside the branches)
    const nRoom = texture(noiseTex, vec2(floor(u.div(1.8)).mul(0.13), floor(v.div(3.9)).mul(0.37))).r;
    const nConc = texture(noiseTex, vec2(u, v).mul(0.05)).b, nGrime = texture(noiseTex, vec2(u.mul(0.1), 0.5)).g;
    const nCar = texture(noiseTex, vec2(floor(u.div(2.7)).mul(0.11), floor(v.div(3.3)).mul(0.23))).r, nCar2 = texture(noiseTex, vec2(floor(u.div(2.7)).mul(0.3), 0.1)).g;
    const nCorr = texture(noiseTex, vec2(u.mul(0.02), v.mul(0.1))).b;
    const nRoof = texture(noiseTex, wp.xz.mul(0.01)).b, nHvac = texture(noiseTex, floor(wp.xz.div(6.0)).mul(0.173)).r;
    const nWin = texture(noiseTex, vec2(floor(u.div(3.2)).mul(0.173), floor(v.div(3.5)).mul(0.311))).g;
    const nLeaf = texture(noiseTex, LP.xz.mul(0.4).add(LP.y.mul(0.3)).add(idata.xy)).g, nLeafN = texture(noiseTex, LP.xz.mul(0.9).add(LP.y)).rgb;
    If(matId.equal(1), () => { // glass curtain wall
      const mull = max(gridLine(u, 1.8, 0.035), gridLine(v, 3.9, 0.06)).mul(float(1.0).sub(smoothstep(150.0, 600.0, dist).mul(0.7)));
      const spandrel = step(fract(v.div(3.9)), 0.12);
      albedo.assign(mix(vec3(0.03, 0.042, 0.05), vec3(0.28, 0.29, 0.3), max(mull, spandrel.mul(0.5)).mul(isWall)));
      rough.assign(mix(0.05, 0.4, mull)); metal.assign(mix(0.0, 0.8, mull));
      albedo.addAssign(vec3(0.02, 0.018, 0.015).mul(nRoom).mul(float(1.0).sub(mull)).mul(isWall));
      extraEmis.addAssign(vec3(1.0, 0.86, 0.68).mul(night).mul(nRoom.mul(0.9).add(0.35)).mul(float(1.0).sub(mull)).mul(float(1.0).sub(spandrel)).mul(isWall).mul(0.9));
    }).ElseIf(matId.equal(2), () => { // concrete panels
      const seam = max(gridLine(u, 3.0, 0.02), gridLine(v, 1.5, 0.02));
      albedo.mulAssign(nConc.mul(0.2).add(0.9).mul(float(1.0).sub(seam.mul(0.25))));
      albedo.mulAssign(float(1.0).sub(smoothstep(3.0, 0.0, v).mul(nGrime).mul(0.25)));
    }).ElseIf(matId.equal(3), () => { // parking garage facade
      const lvl = fract(v.div(3.3));
      const open = step(0.28, lvl).mul(step(lvl, 0.9)).mul(isWall).mul(float(1.0).sub(gridLine(u, 9.0, 0.35)));
      const car = step(0.28, lvl).mul(step(lvl, 0.55)).mul(step(0.35, fract(u.div(2.7)))).mul(step(nCar, 0.6));
      const inside = mix(vec3(0.03), vec3(0.12, 0.13, 0.14).mul(nCar2.add(0.5)), car);
      albedo.assign(mix(albedo, inside, open)); rough.assign(mix(rough, 1.0, open));
      extraEmis.addAssign(vec3(0.9, 0.95, 1.0).mul(night).mul(open).mul(0.35));
    }).ElseIf(matId.equal(4), () => { // corrugated metal: 0.25 m ribs as a normal perturbation
      const rib = sin(u.mul(6.2831 / 0.25));
      nPert.assign(vec3(wt.x, 0.0, wt.y).mul(rib).mul(0.12).mul(isWall).mul(float(1.0).sub(smoothstep(20.0, 120.0, dist))));
      albedo.mulAssign(nCorr.mul(0.1).add(0.95)); albedo.mulAssign(float(1.0).sub(smoothstep(1.5, 0.0, v).mul(0.3)));
    }).ElseIf(matId.equal(5), () => { // flat roof
      albedo.mulAssign(nRoof.mul(0.35).add(0.8)); albedo.assign(mix(albedo, vec3(0.62, 0.62, 0.6), step(0.82, nHvac).mul(0.6)));
    }).ElseIf(matId.equal(6), () => { // punched windows
      const cx = fract(u.div(3.2)), cy = fract(v.div(3.5));
      const win = step(0.18, cx).mul(step(cx, 0.82)).mul(step(0.3, cy)).mul(step(cy, 0.85)).mul(isWall).mul(float(1.0).sub(smoothstep(300.0, 1200.0, dist).mul(0.6)));
      albedo.assign(mix(albedo, vec3(0.06, 0.07, 0.08), win)); rough.assign(mix(rough, 0.08, win));
      extraEmis.addAssign(vec3(1.0, 0.82, 0.6).mul(night).mul(win).mul(step(0.45, nWin)).mul(0.9));
    }).ElseIf(matId.equal(7), () => { // foliage
      albedo.mulAssign(nLeaf.mul(0.7).add(0.65)); ao.assign(smoothstep(-1.0, 1.0, LP.y).mul(0.3).add(0.7));
      nPert.assign(nLeafN.sub(0.5).mul(0.8));
    }).ElseIf(matId.equal(9), () => { // jet bridge tunnel: vertical ribs + window strip
      const along = vUV.x.mul(max(idata.x, 1.0)); const isSide = float(1.0).sub(abs(LN.y));
      albedo.mulAssign(sin(along.mul(6.2831 / 0.35)).mul(0.07).mul(isSide).add(0.93));
      const strip = step(0.5, vUV.y).mul(step(vUV.y, 0.72)).mul(isSide).mul(step(0.25, fract(along.div(1.4)))).mul(float(1.0).sub(abs(LN.x)));
      albedo.assign(mix(albedo, vec3(0.03, 0.04, 0.05), strip)); rough.assign(mix(rough, 0.08, strip));
      extraEmis.addAssign(vec3(1.0, 0.88, 0.7).mul(night).mul(strip).mul(0.7));
      albedo.mulAssign(float(1.0).sub(float(1.0).sub(smoothstep(0.0, 0.15, vUV.y)).mul(isSide).mul(0.25)));
    }).ElseIf(matId.equal(11), () => { // garage roof with parked cars
      const g = vec2(LP.x.div(2.7), LP.z.div(5.5)); const cf = fract(g); const cc = floor(g);
      const row = step(1.0, cc.y.sub(floor(cc.y.div(3.0)).mul(3.0)));
      const car = step(hash12(cc.add(5.3)), 0.62).mul(row).mul(step(0.15, cf.x)).mul(step(cf.x, 0.85)).mul(step(0.12, cf.y)).mul(step(cf.y, 0.88));
      albedo.assign(mix(albedo, vec3(0.8), row.mul(step(0.95, cf.x)).mul(0.6)));
      const h1 = hash12(cc.add(17.1));
      const carCol = select(h1.lessThan(0.25), vec3(0.72), select(h1.lessThan(0.47), vec3(0.025), select(h1.lessThan(0.65), vec3(0.14), select(h1.lessThan(0.75), vec3(0.42, 0.43, 0.45), select(h1.lessThan(0.85), vec3(0.33, 0.025, 0.02), select(h1.lessThan(0.94), vec3(0.02, 0.05, 0.19), vec3(0.28, 0.22, 0.14)))))));
      const fade = smoothstep(90.0, 450.0, dist);
      albedo.assign(mix(albedo, carCol, car.mul(float(1.0).sub(fade)))); albedo.assign(mix(albedo, albedo.mul(0.85).add(0.06), fade.mul(0.5))); rough.assign(mix(rough, 0.3, car));
    }).ElseIf(matId.equal(12), () => { // tower cab glass
      const mull = gridLine(atan(LP.z, LP.x).mul(10.0), 1.0, 0.03);
      albedo.assign(mix(vec3(0.02, 0.035, 0.04), vec3(0.3), mull)); rough.assign(mix(0.04, 0.5, mull)); metal.assign(0.0);
      extraEmis.addAssign(vec3(0.25, 0.4, 0.35).mul(night).mul(float(1.0).sub(mull)).mul(0.25));
    }).ElseIf(matId.equal(15), () => { // apron service facade: ribbed panels, roll-up doors, grime
      const hv = v.sub(3.0);
      albedo.mulAssign(float(1.0).sub(gridLine(u, 0.6, 0.04).mul(float(1.0).sub(smoothstep(40.0, 200.0, dist))).mul(0.12)));
      const cell = floor(u.div(14.0)); const fu = u.sub(cell.mul(14.0)); const hd = fract(sin(cell.mul(12.9898)).mul(43758.5453));
      const door = step(3.5, fu).mul(step(fu, 8.7)).mul(step(hv, 4.1)).mul(step(0.35, hd)).mul(isWall);
      const slat = sin(hv.mul(6.2831 / 0.14)).mul(0.1).add(0.9);
      albedo.assign(mix(albedo, vec3(0.44, 0.45, 0.46).mul(slat), door));
      albedo.assign(mix(albedo, vec3(0.2, 0.22, 0.25), step(10.2, fu).mul(step(fu, 11.2)).mul(step(hv, 2.2)).mul(step(hd, 0.6)).mul(isWall)));
      albedo.assign(mix(albedo, vec3(0.34, 0.35, 0.36), step(4.55, hv).mul(isWall)));
      albedo.mulAssign(float(1.0).sub(smoothstep(0.7, 0.0, hv).mul(isWall).mul(0.28)));
      extraEmis.addAssign(vec3(1.0, 0.85, 0.6).mul(night).mul(door).mul(step(0.8, hd)).mul(0.6));
    }).ElseIf(matId.equal(16), () => { // tower LED glass ribbon
      albedo.assign(vec3(0.03, 0.04, 0.05)); rough.assign(0.06); metal.assign(0.0);
      const wave = sin(v.mul(0.21).sub(time.mul(0.9))).mul(0.45).add(0.55);
      extraEmis.addAssign(mix(vec3(0.15, 0.45, 1.0), vec3(0.2, 0.9, 0.9), wave).mul(wave.mul(0.8).add(1.4)).mul(night));
    }).ElseIf(matId.equal(14), () => { // lamp lens
      extraEmis.addAssign(albedo.mul(night).mul(40.0)); rough.assign(0.1);
    }).ElseIf(matId.equal(13), () => { // hangar door
      albedo.mulAssign(sin(v.mul(6.2831 / 0.4)).mul(0.05).add(0.95).mul(float(1.0).sub(gridLine(u, 6.0, 0.08).mul(0.3))));
    });
    // mild ground-contact AO (the old shader used 0.55; GTAO now supplies most of the contact darkening)
    ao.mulAssign(select(matId.equal(7), float(1.0), mix(float(0.78), float(1.0), smoothstep(0.0, 4.0, wp.y.sub(3.0)))));
    const emissive = albedo.mul(emis).add(extraEmis);
    return { albedo, rough, metal, ao, emissive, nPert };
  };
  // one evaluation shared by several material slots: A runs core() once per shader build (Fn.once) and keeps its
  // nodes in R; B and C call A() first so they read the nodes of the same build (pattern tested in dev/oncetest.html)
  let R = null;
  const A = Fn(() => { R = core(); return vec4(R.albedo, R.rough); }).once();
  const B = Fn(() => { A(); return vec4(R.emissive, R.metal); }).once();
  const C = Fn(() => { A(); return vec4(R.nPert, R.ao); }).once();
  mat.colorNode = vec4(A().xyz, 1.0); mat.roughnessNode = A().w; mat.metalnessNode = B().w; mat.emissiveNode = B().xyz;
  mat.aoNode = C().w;
  mat.normalNode = normalize(cameraViewMatrix.mul(vec4(normalize(normalWorld.add(C().xyz)), 0.0)).xyz); // normalWorld is already flipped on back faces (as the old gl_FrontFacing flip)
  return mat;
}
