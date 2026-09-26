// PBR material for the procedurally built world objects (terminals, tower, ITB, garages, masts, EMAS beds, approach
// light piers, stand equipment, jet bridges, ground service vehicles): TSL port of js/shaders/objects.js OBJ_FS.
// Per-vertex inputs from js/geom.js Geo: color (rgba) and extra = (roughness, metalness, material id, emissive).
// Material ids (objects.js): 1 glass curtain wall, 2 concrete panels, 3 garage facade, 4 corrugated metal, 5 flat
// roof, 6 punched windows, 7 foliage, 9 jet-bridge tunnel (ribs + window strip), 11 garage roof with cars, 12 tower cab
// glass, 13 hangar door, 14 lamp lens (lit at night), 15 apron service facade, 16 tower LED glass ribbon,
// 20 vehicle paint (tinted per instance). Lighting, shadows, IBL reflections, fog and AO come from three.js; the
// old hemisphere ambient and its hand-made contact AO are replaced by PMREM IBL + GTAO (a mild height AO remains).
// Glass (review round 1: curtain walls, tower cab and LED ribbon read as near-black slots, real SFO terminal glass shows
// a grey-blue sky reflection by day, about (119,128,129) sRGB in a public photo of the International Terminal facade):
//   - coated architectural glass: MeshPhysicalNodeMaterial with IOR 2.0 on the glass ids (F0 = 0.11 instead of 0.04,
//     the reflectance of low-e / reflective-coated glazing is 10-20 %, inferred range) and a faint blue specular tint;
//   - the interior behind a curtain-wall pane is interior-mapped (the view ray is intersected with the hall behind the
//     facade: concourse() below), seen through a tinted pane; at night the hall is lit (ceiling brightest);
//   - per-pane variation of roughness and a small normal tilt, so the sky reflection breaks up pane by pane as real
//     glazing does (pane deflection), instead of one mirror.
// Review round 2 (26 Sep 2026):
//   - the curtain walls (id 1: only the terminal piers, halls, ITB, sky bridges and AirTrain stations use it) show a
//     CONCOURSE: one continuous hall behind the glass, 18-30 m deep, ceiling 9 m (tall halls 20 m) above the concourse
//     floor, all lit at night with a +-15 % variation per bay. The 5.4 m office rooms with blinds and 25 % dark rooms
//     read as office blocks, a black-and-white checkerboard at night; SFO's concourses are uniformly lit halls, open 24 h;
//   - flat roofs (id 5): a mid-grey membrane (x 0.8 of the vertex colour) with roll seams, panel tone variation, skylight
//     bands, rooftop units with a shadow side and a few solar arrays, aligned with the airport grid (the terminals are);
//     the satellite reference (docs/qa/ref/mosaic_stands_small.jpg) shows all of these, the old roof was flat white;
//   - garage roofs (id 11): the deck and stall lines only; the cars are instanced boxes that cast shadows (garageCars).
import { THREE, TSL } from './lib.js';
import { hash12, lampK } from './tsl/common.js';
import { Geo } from '../geom.js';
import { GROUND_Y, DIR_S, DIR_T } from '../geo.js';
const { Fn, uniform, attribute, vec2, vec3, vec4, float, texture, dot, abs, max, min, mix, smoothstep, step, clamp, normalize, length, floor, fract, sin, atan, select, If, fwidth, positionWorld, cameraPosition, normalWorld, cameraViewMatrix, modelWorldMatrixInverse, exp } = TSL;

const gridLine = (x, period, w) => { const f = abs(fract(x.div(period).add(0.5)).sub(0.5)).mul(period); const fw = fwidth(x).mul(0.8); return float(1.0).sub(smoothstep(w, fw.add(w), f)); };

// Concourse hall behind a terminal curtain-wall pane (interior mapping in the object's local frame = world for the
// terminals): floor at the concourse level (GROUND_Y + 5 m: the piers' apron level is 0-5 m, js/live/terminals.js; panes
// that start lower look into a hall from the ground), ceiling 9 m higher (20 m for panes above that: the tall halls),
// back wall 18-30 m deep per 20 m bay; no side walls (one continuous hall). Returns { day: albedo seen through the pane,
// night: emission (lamp units x nightE by the caller) }. Dimensions inferred from the glazing heights.
function concourse(u, v, LP, LN, wt) {
  const G = GROUND_Y;
  const camL = modelWorldMatrixInverse.mul(vec4(cameraPosition, 1.0)).xyz;
  const rd = normalize(LP.sub(camL));
  const T = vec3(wt.x, 0.0, wt.y);
  const ax = dot(rd, T), ay = rd.y, az = max(dot(rd, LN).negate(), 0.02);
  const bay = floor(u.div(20.0)); const hb = hash12(vec2(bay, 7.0)), hb2 = hash12(vec2(bay, 19.0));
  const depth = hb.mul(12.0).add(18.0);
  const floorY = select(v.lessThan(G + 5.0), float(G), float(G + 5.0));
  const ceilY = select(v.greaterThan(floorY.add(9.0)), floorY.add(20.0), floorY.add(9.0));
  const ty = select(ay.greaterThan(0.0), ceilY.sub(v).div(max(ay, 1e-4)), v.sub(floorY).div(max(ay.negate(), 1e-4)));
  const tz = depth.div(az);
  const t = min(ty, tz);
  const isBack = step(tz, ty), isCeil = float(1.0).sub(isBack).mul(step(0.0, ay)), isFloor = float(1.0).sub(isBack).mul(step(ay, 0.0));
  const hu = u.add(ax.mul(t)), hz = min(t.mul(az), depth); // hit point: along the facade, into the hall
  const hy = v.add(ay.mul(t)).sub(floorY);
  // ceiling: light fixtures on a 3 m x 3 m grid; back wall: shop / gate-lounge fronts (bright band) over seating (dark);
  // floor: terrazzo, brighter with distance (the glossy floor mirrors the lit hall)
  const lamp = step(0.72, fract(hu.div(3.0))).mul(step(0.72, fract(hz.div(3.0))));
  const shop = step(2.6, hy).mul(step(hy, 5.5)).mul(step(0.25, fract(hu.div(12.0).add(hb))));
  const seats = step(hy, 1.1).mul(step(0.3, fract(hu.div(1.2))));
  const wallC = mix(vec3(0.46, 0.44, 0.40), vec3(0.62, 0.58, 0.50), shop).mul(float(1.0).sub(seats.mul(0.55)));
  const ceilC = mix(vec3(0.72, 0.72, 0.70), vec3(0.95), lamp), floorC = vec3(0.42, 0.40, 0.37);
  const c = mix(mix(wallC, ceilC, isCeil), floorC, isFloor);
  const depthFade = exp(t.mul(-0.03)).mul(0.5).add(0.5);
  const day = c.mul(depthFade).mul(hb2.mul(0.2).add(0.9));
  const var15 = hb2.mul(0.3).add(0.85); // +-15 % per bay
  const nightE = vec3(1.0, 0.9, 0.76).mul(mix(mix(mix(float(0.55), float(0.9), shop), mix(float(0.7), float(2.2), lamp), isCeil), float(0.45), isFloor)).mul(depthFade).mul(var15).mul(0.8);
  return { day, night: nightE };
}
// Cars on the garage roofs (material id 11, js/world/buildings.js parkRoof) as instanced boxes on the stall grid that
// the roof shader draws its lines on (local x / 2.7 m, z / 5.5 m, every third row an aisle), about 60 % of the stalls
// taken; body + cabin, tinted per instance with the old shader's car colour mix (white, black, grey, silver, red, blue,
// brown). Returns an InstancedMesh (vehicle material) or null. Only stalls whose whole footprint lies on the roof.
const CAR_COLS = [[0.25, [0.72, 0.72, 0.72]], [0.47, [0.025, 0.025, 0.025]], [0.65, [0.14, 0.14, 0.14]], [0.75, [0.42, 0.43, 0.45]], [0.85, [0.33, 0.025, 0.02]], [0.94, [0.02, 0.05, 0.19]], [1.01, [0.28, 0.22, 0.14]]];
let carGeoCache = null;
export function garageCars(data, model, vehMat, tier) {
  if (!data || !data.extra || !data.pos) return null;
  const P = data.pos, N = data.nrm, X = data.extra, I = data.idx; const tris = [];
  const nt = I ? I.length / 3 : P.length / 9;
  for (let t = 0; t < nt; t++) {
    const a = I ? I[t * 3] : t * 3, b = I ? I[t * 3 + 1] : t * 3 + 1, c = I ? I[t * 3 + 2] : t * 3 + 2;
    if (Math.abs(X[a * 4 + 2] - 11) > 0.5 || !(N && N[a * 3 + 1] > 0.9)) continue;
    tris.push([P[a * 3], P[a * 3 + 2], P[b * 3], P[b * 3 + 2], P[c * 3], P[c * 3 + 2], (P[a * 3 + 1] + P[b * 3 + 1] + P[c * 3 + 1]) / 3]);
  }
  if (!tris.length) return null;
  const inTri = (x, z, T) => { const d1 = (x - T[2]) * (T[1] - T[3]) - (T[0] - T[2]) * (z - T[3]), d2 = (x - T[4]) * (T[3] - T[5]) - (T[2] - T[4]) * (z - T[5]), d3 = (x - T[0]) * (T[5] - T[1]) - (T[4] - T[0]) * (z - T[1]); return !((d1 < 0 || d2 < 0 || d3 < 0) && (d1 > 0 || d2 > 0 || d3 > 0)); };
  const onRoof = (x, z) => { for (const T of tris) if (inTri(x, z, T)) return T[6]; return null; };
  const hash = (i, j, k) => { const s = Math.sin(i * 127.1 + j * 311.7 + k * 74.7) * 43758.5453; return s - Math.floor(s); };
  const seen = new Set(); const cars = [];
  for (const T of tris) {
    const i0 = Math.floor(Math.min(T[0], T[2], T[4]) / 2.7), i1 = Math.floor(Math.max(T[0], T[2], T[4]) / 2.7);
    const j0 = Math.floor(Math.min(T[1], T[3], T[5]) / 5.5), j1 = Math.floor(Math.max(T[1], T[3], T[5]) / 5.5);
    for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) {
      const key = i + ',' + j; if (seen.has(key)) continue; seen.add(key);
      if (((j % 3) + 3) % 3 === 0) continue; // aisle
      if (hash(i, j, 1) > 0.62) continue;     // empty stall
      const cx = (i + 0.5) * 2.7, cz = (j + 0.5) * 5.5; const y = onRoof(cx, cz); if (y == null) continue;
      if (onRoof(cx - 1.1, cz - 2.5) == null || onRoof(cx + 1.1, cz + 2.5) == null || onRoof(cx - 1.1, cz + 2.5) == null || onRoof(cx + 1.1, cz - 2.5) == null) continue;
      const h = hash(i, j, 2); const col = CAR_COLS.find(e => h < e[0])[1];
      cars.push([cx + (hash(i, j, 3) - 0.5) * 0.3, y, cz + (hash(i, j, 4) - 0.5) * 0.6, (hash(i, j, 5) < 0.5 ? 0 : Math.PI) + (hash(i, j, 6) - 0.5) * 0.08, col]);
    }
  }
  if (!cars.length) return null;
  if (!carGeoCache) {
    const g = new Geo(); const E_PAINT = [0.35, 0, 20, 0], E_GLASS = [0.1, 0, 0, 0], E_TYRE = [0.9, 0, 0, 0];
    g.box([-0.9, 0.3, -2.25], [0.9, 0.95, 2.25], [0.8, 0.8, 0.8, 1], E_PAINT);        // body (tinted: material id 20)
    g.box([-0.8, 0.95, -1.15], [0.8, 1.45, 1.05], [0.06, 0.07, 0.08, 1], E_GLASS);      // cabin glass
    g.box([-0.78, 1.45, -1.05], [0.78, 1.5, 0.95], [0.8, 0.8, 0.8, 1], E_PAINT);        // roof panel
    g.box([-0.92, 0.0, -1.7], [0.92, 0.32, -1.1], [0.03, 0.03, 0.03, 1], E_TYRE); g.box([-0.92, 0.0, 1.1], [0.92, 0.32, 1.7], [0.03, 0.03, 0.03, 1], E_TYRE);
    const d = g.data(); const bg = new THREE.BufferGeometry();
    for (const [k, n, sz] of [['position', 'pos', 3], ['normal', 'nrm', 3], ['uv', 'uv', 2], ['color', 'col', 4], ['extra', 'extra', 4]]) bg.setAttribute(k, new THREE.BufferAttribute(new Float32Array(d[n]), sz));
    bg.setIndex(Array.from(d.idx)); carGeoCache = bg;
  }
  const g = carGeoCache.clone(); const n = cars.length; const iData = new Float32Array(n * 4);
  const o = new THREE.InstancedMesh(g, vehMat, n); const M = new THREE.Matrix4(), W = model ? new THREE.Matrix4().fromArray(model) : null; const Q = new THREE.Quaternion(), Y = new THREE.Vector3(0, 1, 0), S1 = new THREE.Vector3(1, 1, 1), Pp = new THREE.Vector3();
  cars.forEach(([x, y, z, yaw, col], k) => { Pp.set(x, y, z); M.compose(Pp, Q.setFromAxisAngle(Y, yaw), S1); if (W) M.premultiply(W); o.setMatrixAt(k, M); iData.set([col[0], col[1], col[2], 1], k * 4); });
  g.setAttribute('iData', new THREE.InstancedBufferAttribute(iData, 4));
  o.castShadow = tier !== 'low'; o.receiveShadow = true; o.instanceMatrix.needsUpdate = true; o.computeBoundingSphere(); o.name = 'garageCars';
  return o;
}
// opts: { instanced: bool (per-instance iData: x = tunnel length, rgb/w = vehicle tint), instColor: bool (colour and
// extra per instance in iCol / iExt: unit boxes and cylinders of the bridges), noiseTex, night (uniform), time (uniform) }
export function objectMaterial(opts) {
  const { noiseTex, night, time } = opts;
  const mat = new THREE.MeshPhysicalNodeMaterial({ side: THREE.DoubleSide });
  const core = () => {
    const col = opts.instColor ? attribute('iCol', 'vec4') : attribute('color', 'vec4'); const ext = opts.instColor ? attribute('iExt', 'vec4') : attribute('extra', 'vec4');
    const LP = attribute('position', 'vec3'); const LN = normalize(attribute('normal', 'vec3')).toVar(); const vUV = attribute('uv', 'vec2');
    const idata = opts.instanced && !opts.instColor ? attribute('iData', 'vec4') : vec4(0);
    const wp = positionWorld; const dist = length(cameraPosition.sub(wp)).toVar();
    const albedo = col.rgb.toVar(); const rough = ext.x.toVar(), metal = ext.y.toVar(); const matId = floor(ext.z.add(0.5)).toVar(); const emis = ext.w;
    if (opts.instanced && !opts.instColor) albedo.assign(mix(albedo, idata.rgb, step(0.5, idata.w).mul(step(19.5, ext.z)).mul(step(ext.z, 20.5))));
    const wt = normalize(vec2(LN.z.negate(), LN.x).add(1e-5));
    const u = dot(LP.xz, wt).toVar(), v = LP.y.toVar();
    const ao = float(1.0).toVar(); const extraEmis = vec3(0).toVar(); const nPert = vec3(0).toVar(); const ior = float(1.5).toVar(); const spec = vec3(1.0).toVar();
    const isWall = float(1.0).sub(abs(LN.y));
    // noise samples used by several ids (sampled once, outside the branches)
    const nConc = texture(noiseTex, vec2(u, v).mul(0.05)).b, nGrime = texture(noiseTex, vec2(u.mul(0.1), 0.5)).g;
    const nCar = texture(noiseTex, vec2(floor(u.div(2.7)).mul(0.11), floor(v.div(3.3)).mul(0.23))).r, nCar2 = texture(noiseTex, vec2(floor(u.div(2.7)).mul(0.3), 0.1)).g;
    const nCorr = texture(noiseTex, vec2(u.mul(0.02), v.mul(0.1))).b;
    const nRoof = texture(noiseTex, wp.xz.mul(0.01)).b;
    const nWin = texture(noiseTex, vec2(floor(u.div(3.2)).mul(0.173), floor(v.div(3.5)).mul(0.311))).g;
    const nLeaf = texture(noiseTex, LP.xz.mul(0.4).add(LP.y.mul(0.3)).add(idata.xy)).g, nLeafN = texture(noiseTex, LP.xz.mul(0.9).add(LP.y)).rgb;
    If(matId.equal(1), () => { // glass curtain wall: coated pane over a parallax room, mullions, spandrels
      const mull = max(gridLine(u, 1.8, 0.035), gridLine(v, 3.9, 0.06)).mul(float(1.0).sub(smoothstep(150.0, 600.0, dist).mul(0.7)));
      const spandrel = step(fract(v.div(3.9)), 0.12);
      const frame = max(mull, spandrel.mul(0.5)).mul(isWall);
      const pane = vec2(floor(u.div(1.8)), floor(v.div(3.9)));
      const hP = hash12(pane.add(vec2(17.0, 3.0))), hQ = hash12(pane.add(vec2(5.0, 41.0))), hR = hash12(pane.add(vec2(29.0, 7.0)));
      const room = concourse(u, v, LP, LN, wt);
      albedo.assign(mix(room.day.mul(vec3(0.24, 0.27, 0.29)), vec3(0.28, 0.29, 0.3), frame)); // through blue-green tinted glazing (first render: the rooms read warm tan)
      rough.assign(mix(hP.mul(0.05).add(0.03), 0.4, mull)); metal.assign(mix(0.0, 0.8, mull));
      ior.assign(mix(2.0, 1.5, frame)); spec.assign(mix(vec3(0.9, 0.96, 1.0), vec3(1.0), frame));
      nPert.assign(vec3(wt.x, 0.0, wt.y).mul(hQ.sub(0.5)).add(vec3(0.0, hR.sub(0.5), 0.0)).mul(0.03).mul(float(1.0).sub(frame)).mul(isWall));
      extraEmis.addAssign(room.night.mul(night).mul(float(1.0).sub(mull)).mul(float(1.0).sub(spandrel)).mul(isWall));
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
    }).ElseIf(matId.equal(5), () => { // flat roof: membrane, seams, panels, skylights, rooftop units, solar arrays
      const st = vec2(dot(wp.xz, vec2(DIR_S[0], DIR_S[2])), dot(wp.xz, vec2(DIR_T[0], DIR_T[2])));
      const far = smoothstep(150.0, 900.0, dist);
      albedo.mulAssign(nRoof.mul(0.3).add(0.72)); // mid-grey membrane (x ~0.8 of the vertex colour)
      const pc = floor(st.div(vec2(23.0, 31.0))); const hp = hash12(pc.add(3.7));
      albedo.mulAssign(hp.mul(0.16).add(0.92));                                              // panel tone variation
      albedo.mulAssign(float(1.0).sub(gridLine(st.x, 3.05, 0.04).mul(0.12).mul(float(1.0).sub(far)))); // membrane roll seams
      const sky = step(fract(st.y.div(48.0)), 0.065).mul(step(0.35, fract(st.x.div(9.0))));  // skylight bands (glass)
      albedo.assign(mix(albedo, vec3(0.1, 0.12, 0.14), sky.mul(0.85))); rough.assign(mix(rough, 0.15, sky));
      const hc = floor(st.div(9.0)); const hh = hash12(hc.add(11.0)); const hf = fract(st.div(9.0));
      const unit = step(hh, 0.14).mul(step(0.2, hf.x)).mul(step(hf.x, 0.75)).mul(step(0.25, hf.y)).mul(step(hf.y, 0.7));
      const unitSh = step(hh, 0.14).mul(step(0.75, hf.x)).mul(step(hf.x, 0.9)).mul(step(0.25, hf.y)).mul(step(hf.y, 0.7));
      albedo.assign(mix(albedo, vec3(0.62, 0.63, 0.62), unit)); albedo.mulAssign(float(1.0).sub(unitSh.mul(0.35)));
      const sc = floor(st.div(vec2(60.0, 40.0))); const hs = hash12(sc.add(29.0)); const sf = fract(st.div(vec2(60.0, 40.0)));
      const solar = step(hs, 0.12).mul(step(0.1, sf.x)).mul(step(sf.x, 0.9)).mul(step(0.15, sf.y)).mul(step(sf.y, 0.85)).mul(step(0.12, fract(st.y.div(2.2))));
      albedo.assign(mix(albedo, vec3(0.035, 0.05, 0.09), solar)); rough.assign(mix(rough, 0.25, solar));
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
    }).ElseIf(matId.equal(11), () => { // garage roof deck: stall lines and oil stains (the cars are instances: garageCars)
      const g = vec2(LP.x.div(2.7), LP.z.div(5.5)); const cf = fract(g); const cc = floor(g);
      const row = step(1.0, cc.y.sub(floor(cc.y.div(3.0)).mul(3.0)));
      const fade = smoothstep(90.0, 450.0, dist);
      albedo.assign(mix(albedo, vec3(0.8), row.mul(gridLine(LP.x, 2.7, 0.06)).mul(0.6).mul(float(1.0).sub(fade))));
      const stain = row.mul(step(0.3, cf.x)).mul(step(cf.x, 0.7)).mul(step(0.35, cf.y)).mul(step(cf.y, 0.65)).mul(step(hash12(cc.add(5.3)), 0.8));
      albedo.mulAssign(float(1.0).sub(stain.mul(0.12)));
    }).ElseIf(matId.equal(12), () => { // tower cab glass (coated, lighter cab interior behind it)
      const mull = gridLine(atan(LP.z, LP.x).mul(10.0), 1.0, 0.03);
      albedo.assign(mix(vec3(0.05, 0.06, 0.065), vec3(0.3), mull)); rough.assign(mix(0.04, 0.5, mull)); metal.assign(0.0);
      ior.assign(mix(2.0, 1.5, mull)); spec.assign(mix(vec3(0.9, 0.96, 1.0), vec3(1.0), mull));
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
    }).ElseIf(matId.equal(16), () => { // tower LED glass ribbon: coated glass (sky reflection by day), LED waterfall at night
      albedo.assign(vec3(0.05, 0.06, 0.07)); rough.assign(0.06); metal.assign(0.0); ior.assign(2.2); spec.assign(vec3(0.9, 0.96, 1.0));
      const wave = sin(v.mul(0.21).sub(time.mul(0.9))).mul(0.45).add(0.55);
      extraEmis.addAssign(mix(vec3(0.15, 0.45, 1.0), vec3(0.2, 0.9, 0.9), wave).mul(wave.mul(0.8).add(1.4)).mul(night));
    }).ElseIf(matId.equal(14), () => { // lamp lens
      extraEmis.addAssign(albedo.mul(night).mul(40.0)); rough.assign(0.1);
    }).ElseIf(matId.equal(13), () => { // hangar door
      albedo.mulAssign(sin(v.mul(6.2831 / 0.4)).mul(0.05).add(0.95).mul(float(1.0).sub(gridLine(u, 6.0, 0.08).mul(0.3))));
    });
    // mild ground-contact AO (the old shader used 0.55; GTAO now supplies most of the contact darkening)
    ao.mulAssign(select(matId.equal(7), float(1.0), mix(float(0.78), float(1.0), smoothstep(0.0, 4.0, wp.y.sub(3.0)))));
    // per-vertex emission (lamp heads etc.) in lamp units x lampK; the night terms above already carry nightE (opts.night)
    const emissive = albedo.mul(emis).mul(lampK).add(extraEmis);
    return { albedo, rough, metal, ao, emissive, nPert, ior, spec };
  };
  // one evaluation shared by several material slots: A runs core() once per shader build (Fn.once) and keeps its
  // nodes in R; B and C call A() first so they read the nodes of the same build (pattern tested in dev/oncetest.html)
  let R = null;
  const A = Fn(() => { R = core(); return vec4(R.albedo, R.rough); }).once();
  const B = Fn(() => { A(); return vec4(R.emissive, R.metal); }).once();
  const C = Fn(() => { A(); return vec4(R.nPert, R.ao); }).once();
  const D = Fn(() => { A(); return vec4(R.spec, R.ior); }).once();
  mat.colorNode = vec4(A().xyz, 1.0); mat.roughnessNode = A().w; mat.metalnessNode = B().w; mat.emissiveNode = B().xyz;
  mat.aoNode = C().w; mat.iorNode = D().w; mat.specularColorNode = D().xyz;
  mat.normalNode = normalize(cameraViewMatrix.mul(vec4(normalize(normalWorld.add(C().xyz)), 0.0)).xyz); // normalWorld is already flipped on back faces (as the old gl_FrontFacing flip)
  return mat;
}
