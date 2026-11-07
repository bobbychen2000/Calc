// Jet bridges (instanced unit parts, animatable) and ground service vehicles
import { Mesh } from '../gl.js';
import { Geo } from '../geom.js';
import { m4, v3, rng, lerp, smoother } from '../math.js';
import { stToWorld, GROUND_Y } from '../geo.js';
import { TYPES } from '../aircraft/model.js';

const G = GROUND_Y;
const stW = (p, h = 0) => stToWorld(p[0], p[1], h);
const stD = (d) => { const a = stToWorld(d[0], d[1], 0), o = stToWorld(0, 0, 0); return v3.norm([a[0] - o[0], 0, a[2] - o[2]]); };

// unit meshes
function unitBox(col, ext, uvLen = true) { const g = new Geo(); g.box([0, -0.5, -0.5], [1, 0.5, 0.5], col, ext); // uv: x along, y vertical 0..1
  for (let i = 0; i < g.nv; i++) { g.uv[i * 2] = g.pos[i * 3]; g.uv[i * 2 + 1] = g.pos[i * 3 + 1] + 0.5; } return g; }
function unitCyl(col, ext, seg = 20) { const g = new Geo(); g.cylinder(1, 1, seg, col, ext, null, true); return g; }

function inst(M, data = [0, 0, 0, 0]) { // 3x4 rows + data
  return [M[0], M[4], M[8], M[12], M[1], M[5], M[9], M[13], M[2], M[6], M[10], M[14], ...data];
}
// unit cylinder (axis y 0..1, radius 1) -> centered at c, axis direction ax, radius r, length l
function cylMat(c, ax, r, l) {
  const y = v3.norm(ax); const x = v3.norm(Math.abs(y[1]) > 0.9 ? v3.cross([1, 0, 0], y) : v3.cross(y, [0, 1, 0])); const z = v3.cross(x, y);
  const B = new Float32Array([x[0] * r, x[1] * r, x[2] * r, 0, y[0] * l, y[1] * l, y[2] * l, 0, z[0] * r, z[1] * r, z[2] * r, 0, c[0] - y[0] * l / 2, c[1] - y[1] * l / 2, c[2] - y[2] * l / 2, 1]);
  return B;
}
// matrix mapping unit box (x:0..1, y,z: -0.5..0.5) onto segment a->b with height h (y) and width w, keeping y up
function segBox(a, b, h, w, roll = 0) {
  const d = v3.sub(b, a); const L = v3.len(d); const f = v3.mul(d, 1 / L);
  const r = v3.norm(v3.cross(f, [0, 1, 0])); const u = v3.cross(r, f);
  const B = new Float32Array([f[0], f[1], f[2], 0, u[0], u[1], u[2], 0, r[0], r[1], r[2], 0, a[0], a[1], a[2], 1]);
  return { M: m4.mul(B, m4.scale(L, h, w)), L };
}

export { inst };
export class GateSystem {
  constructor(gates) {
    this.gates = gates;
    const light = [0.82, 0.83, 0.84, 1], dark = [0.08, 0.08, 0.09, 1], gray = [0.45, 0.46, 0.48, 1];
    this.meshes = {
      tunnel: new Mesh(unitBox(light, [0.5, 0.2, 9, 0]).data()),
      cab: new Mesh(unitBox([0.7, 0.71, 0.72, 1], [0.45, 0.2, 9, 0]).data()),
      bellows: new Mesh(unitBox(dark, [0.9, 0, 0, 0]).data()),
      column: new Mesh(unitCyl(gray, [0.5, 0.6, 0, 0], 12).data()),
      rotunda: new Mesh(unitCyl([0.78, 0.79, 0.8, 1], [0.5, 0.3, 0, 0], 24).data()),
      wheel: new Mesh(unitCyl([0.06, 0.06, 0.06, 1], [0.9, 0, 0, 0], 12).data()),
      beam: new Mesh(unitBox(gray, [0.5, 0.6, 0, 0]).data()),
    };
    this.vehicleMeshes = buildVehicleMeshes(LEGACY_SET);
    this.animated = {}; // gateId -> k
    this.buildStatic();
  }
  bridgePose(g, k) {
    // k: 1 docked at L1 door, 0 retracted
    const f = stD(g.dir); const r = v3.norm(v3.cross(f, [0, 1, 0])); const left = v3.mul(r, -1);
    const outW = stD(g.outN);
    const T = TYPES[g.acType || (g.wide ? 'wide' : 'narrow')];
    const attach = stW(g.attach, G);
    const rc = v3.add(v3.add(attach, v3.mul(outW, 3.2)), v3.mul(left, g.wide ? 7 : 5));
    const floorY = G + 5.4;
    const nose = stW(g.nose, G);
    const doorX = T.doors[0];
    const sill = G + (T.dockSill ?? T.Hc - 0.3 * T.R); // published door-1 sill (js/aircraft/fit.js; docs/requests/aircraft_docking_fields.md)
    const door = v3.add(v3.sub(nose, v3.mul(f, T.dockX1 ?? doorX)), v3.mul(left, (T.dockHW ?? T.R) + 0.15)); // door CENTRE station
    door[1] = sill;
    // docked cab center (cab depth 3.4 m, away from fuselage along left)
    const cabDock = v3.add(door, v3.mul(left, 1.9));
    // retracted: cab pulled back toward pier, swung along pier face
    const along = v3.norm(v3.add(v3.mul(outW, 0.6), v3.mul(left, 0.8)));
    const cabPark = v3.add([rc[0], G + 4.2, rc[2]], v3.mul(along, 14));
    const kk = smoother(k);
    const cab = v3.lerp(cabPark, cabDock, kk);
    const cabFacing = v3.norm(v3.lerp(along, v3.mul(left, -1), kk)); // direction cab faces (toward aircraft when docked)
    return { rc, floorY, cab, cabFacing, left, door };
  }
  bridgeInstances(g, k, out) {
    const P = this.bridgePose(g, k); const M = this.meshes;
    const rc = P.rc; const rot = [rc[0], P.floorY - 0.2, rc[2]];
    // rotunda + column
    out.rotunda.push(inst(m4.mul(m4.translate(rc[0], P.floorY - 0.3, rc[2]), m4.scale(2.3, 3.3, 2.3))));
    out.column.push(inst(m4.mul(m4.translate(rc[0], G, rc[2]), m4.scale(0.55, P.floorY - G - 0.3, 0.55))));
    // tunnel from rotunda edge to cab back
    const cabBack = v3.sub(P.cab, v3.mul(P.cabFacing, 1.7));
    const startC = [rc[0], P.floorY + 1.3, rc[2]];
    const endC = [cabBack[0], P.cab[1] + 1.4, cabBack[2]];
    const dir = v3.norm(v3.sub(endC, startC));
    const s0 = v3.add(startC, v3.mul(dir, 2.0));
    const Lt = v3.dist(s0, endC);
    // three telescoping sections
    const secs = [[0, 0.42, 2.9, 2.5], [0.36, 0.74, 3.05, 2.65], [0.68, 1.0, 3.2, 2.8]];
    for (const [a, b, h, w] of secs) {
      const A = v3.add(s0, v3.mul(dir, Lt * a)), B = v3.add(s0, v3.mul(dir, Lt * b));
      const { M: mm, L } = segBox(A, B, h, w); out.tunnel.push(inst(mm, [L, 0, 0, 0]));
    }
    // cab
    const cabA = v3.sub(P.cab, v3.mul(P.cabFacing, 1.7)), cabB = v3.add(P.cab, v3.mul(P.cabFacing, 1.5));
    const cA = [cabA[0], P.cab[1] + 1.55, cabA[2]], cB = [cabB[0], P.cab[1] + 1.55, cabB[2]];
    out.cab.push(inst(segBox(cA, cB, 3.3, 3.4).M, [3.2, 0, 0, 0]));
    // bellows/canopy at aircraft side
    const bA = cB, bB = v3.add(cB, v3.mul(P.cabFacing, 0.5 + 0.3 * k));
    out.bellows.push(inst(segBox(bA, bB, 3.0, 3.1).M));
    // drive unit: legs + wheels under the outer tunnel near cab
    const du = v3.add(s0, v3.mul(dir, Lt * 0.84)); const yb = du[1] - 1.5;
    const side = v3.norm(v3.cross(dir, [0, 1, 0]));
    for (const sg of [-1, 1]) {
      const leg = v3.add(du, v3.mul(side, sg * 1.3));
      out.column.push(inst(m4.mul(m4.translate(leg[0], G + 0.45, leg[2]), m4.scale(0.18, yb - G - 0.45, 0.18))));
      out.wheel.push(inst(cylMat([leg[0], G + 0.45, leg[2]], side, 0.45, 0.35)));
    }
    const beamA = v3.add(du, v3.mul(side, -1.4)), beamB = v3.add(du, v3.mul(side, 1.4));
    out.beam.push(inst(segBox([beamA[0], G + 0.5, beamA[2]], [beamB[0], G + 0.5, beamB[2]], 0.4, 0.5).M));
  }
  buildStatic() {
    const R = rng(99);
    this.staticBuckets = { tunnel: [], cab: [], bellows: [], column: [], rotunda: [], wheel: [], beam: [] };
    this.vehicleBuckets = {}; for (const k in this.vehicleMeshes) this.vehicleBuckets[k] = [];
    for (const g of this.gates) {
      if (g.dynamic) continue;
      const docked = !g.empty;
      this.bridgeInstances(g, docked ? 1 : 0.0, this.staticBuckets);
      if (docked) this.placeServiceVehicles(g, R, this.vehicleBuckets);
    }
    // staging: rows of baggage carts/containers near each pier root
    for (const g of this.gates) { if (R() > 0.3) continue; const f = stD(g.dir); const r = v3.norm(v3.cross(f, [0, 1, 0])); const base = stW(g.attach, G);
      const p0 = v3.add(base, v3.add(v3.mul(f, -9), v3.mul(r, (R() < 0.5 ? -1 : 1) * (g.wide ? 22 : 15))));
      for (let i = 0; i < 4; i++) { const p = v3.add(p0, v3.mul(r, i * 3.3)); this.vehicleBuckets.cart.push(inst(m4.basis(r, [0, 1, 0], [p[0], G, p[2]]), [0.3 + R() * 0.4, 0.3, 0.35, 1])); } }
    this.bbox = [-2000, 0, -2000, 2000, 60, 2000];
    const all = this.gates.map(g => stW(g.nose, 0)); if (all.length) { this.bbox = [1e9, 0, 1e9, -1e9, 30, -1e9]; all.forEach(p => { this.bbox[0] = Math.min(this.bbox[0], p[0] - 120); this.bbox[2] = Math.min(this.bbox[2], p[2] - 120); this.bbox[3] = Math.max(this.bbox[3], p[0] + 120); this.bbox[5] = Math.max(this.bbox[5], p[2] + 120); }); }
  }
  // per-frame items; dyn: [{gate, k}] animated bridges; extraVehicles: {meshName: [instances]}
  items(dyn = [], extraVehicles = {}) {
    const out = [];
    const buckets = {}; for (const k in this.staticBuckets) buckets[k] = this.staticBuckets[k].slice();
    for (const d of dyn) this.bridgeInstances(d.gate, d.k, buckets);
    for (const k in buckets) { const m = this.meshes[k]; m.setInstances(new Float32Array(buckets[k].flat()), buckets[k].length); out.push({ mesh: m, prog: 'objI', bbox: this.bbox, castShadow: true, uniforms: { uEmissiveBoost: 1 } }); }
    for (const k in this.vehicleBuckets) { const list = this.vehicleBuckets[k].concat(extraVehicles[k] || []); const m = this.vehicleMeshes[k]; m.setInstances(new Float32Array(list.flat()), list.length); out.push({ mesh: m, prog: 'objI', bbox: this.bbox, castShadow: true, uniforms: { uEmissiveBoost: 1 }, shadowMaxCascade: 2 }); }
    return out;
  }
  placeServiceVehicles(g, R, B) {
    const T = TYPES[g.acType || (g.wide ? 'wide' : 'narrow')];
    const f = stD(g.dir); const r = v3.norm(v3.cross(f, [0, 1, 0]));
    const nose = stW(g.nose, G);
    const at = (along, side, yaw = 0) => { // along: meters behind nose, side: + right
      const p = v3.add(v3.sub(nose, v3.mul(f, along)), v3.mul(r, side));
      const c = Math.cos(yaw), s = Math.sin(yaw); const d = v3.norm(v3.add(v3.mul(f, c), v3.mul(r, s)));
      return m4.basis(d, [0, 1, 0], [p[0], G, p[2]]);
    };
    const tint = () => { const cs = [[0.95, 0.95, 0.95], [0.9, 0.75, 0.1], [0.15, 0.3, 0.6], [0.85, 0.3, 0.1], [0.4, 0.42, 0.45]]; return [...cs[Math.floor(R() * cs.length)], 1]; };
    // belt loader at forward cargo door (right side)
    if (R() < 0.8) B.beltLoader.push(inst(at(T.L * 0.22, T.R + 3.0, -1.35), tint()));
    // baggage tug + carts
    if (R() < 0.75) {
      const base = T.L * 0.3; B.tug.push(inst(at(base, T.R + 11, Math.PI), tint()));
      for (let i = 0; i < 3; i++) B.cart.push(inst(at(base + 3.2 + i * 3.4, T.R + 11, Math.PI), [0.3 + R() * 0.5, 0.3, 0.35, 1]));
    }
    // catering truck at R2 door
    if (R() < 0.45) B.catering.push(inst(at(T.doors[1] + 1, T.R + 3.5, -Math.PI / 2), [0.95, 0.95, 0.95, 1]));
    // fuel truck outboard of the right engine
    if (R() < 0.35 && T.eng.length) B.fuel.push(inst(at(T.xMain - 6, T.eng[T.eng.length - 1].z + 6.5, 0), [0.85, 0.85, 0.85, 1]));
    // GPU near nose
    if (R() < 0.6) B.gpu.push(inst(at(2.5, -3.5, 0.3), tint()));
    // cones at wingtips & nose
    for (const [a, s] of [[-1.5, 0], [T.L * 0.5, T.R + 0.2 + (g.wide ? 30 : 16.5)], [T.L * 0.5, -(T.R + 0.2 + (g.wide ? 30 : 16.5))], [T.L + 1.5, 0]]) B.cone.push(inst(at(a, s)));
  }
}

// ----- vehicle meshes -----
// Belt loaders (close-out round 3, bridges-3): the conveyor's top end on the lower-deck cargo-door sill of the door it
// serves, at the RENDERED fuselage - the fitted model's own cargo-door object, stance and lower lobe (js/aircraft/fit.js
// T.fit.cargo / keelAt / skinHW, the aircraft track's cargoDoor() API; read here from T.fit so that the old offline scene,
// which does not load fit.js, is unchanged). Before, the sill came from BELT_PUB raised to 0.3 m above an UNPITCHED
// ellipse (2 Hc - crown) at 0.22 L / 0.66 L: when the 737 MAX stood nose-up its forward conveyor ended 0.29-0.36 m below
// the rendered skin, and the 737 NG ends missed it by up to 0.88 m (scratch belt_api.mjs). Per door:
//  - X: the model's cargo-door object (FG 737-800 cargodoorF / R, rendered centre) or the published station (SPEC cargoX:
//    A321 / A321neo); else 0.22 L / 0.66 L (A319 / A320 families; inferred, as before)
//  - S (conveyor top at its end): the drawn door's rendered sill; without a door object the middle of the type's published
//    sill range (SPEC cargo: 737 MAX ACAP D6-38A004 Rev K §2.3.2 rows D / L, A321 / A321neo C1 / C2) or of BELT_PUB below
//    (A319 / A320 families), never less than 0.05 m above the rendered keel at X; to 0.01 m (one mesh per setting)
//  - the end at the starboard skin's half width at (X, S) + 0.03 m (beltEndY)
// Published sill ranges kept as the fallback (m above the apron between the documents' weight / CG cases):
//  - Boeing 737 NG: forward cargo door 1.30-1.45, aft 1.63-1.80 (737NG ACAP Rev C §2.3.1 "C FWD CARGO DOOR" / "F AFT
//    CARGO DOOR" for the -600 ... -900ER, refs/cache/acap/737NG_REV_C.txt lines 1327-1442)
//  - Airbus A320 family: forward cargo door C1 1.81-1.93, aft C2 1.91-2.08 (Airbus AC A321 §2-3 Ground Clearances,
//    refs/cache/acap/AC_A321_jul2026.txt lines 3869-3874; the A319 / A320 take the A321's values - inferred, their AC is
//    not cached)
// Conveyor length 8.0 m, 0.9 m wide, BELT_THICK 0.3 m deep, rear end 0.75 m up (inferred, no datasheet).
const BELT_THICK = 0.3;
// the side rails (0.25 m) stop BELT_RAIL_GAP short of the conveyor's top end: the end section meets the sill and reaches
// into the open cargo door (the models draw the doors closed - full-length rails ran up to 0.62 m back and 0.29 m into the
// rendered lower lobe; scratch c3/bridges/scripts/beltmesh.mjs); inferred, no datasheet
export const BELT_RAIL_GAP = 0.7;
export const BELT_PUB = { b737: { fwd: [1.30, 1.45], aft: [1.63, 1.80] }, a320: { fwd: [1.81, 1.93], aft: [1.91, 2.08] } };
export const beltFamily = (k) => /^b73\d$|^b3[789x]m$/.test(k) ? 'b737' : /^a3(18|19|20|21)$|^a(19|20|21)n$/.test(k) ? 'a320' : null;
// the lowest skin of the unpitched elliptical section (procedural airframes without a fitted model only)
export function lowSkin(T) { const crown = (T.fit && T.fit.renderedCrown) || T.Hc + T.R; return T.Hc - (crown - T.Hc); }
// where the conveyor meets cargo door `door` ('fwd' / 'aft') of type T of belt family fam: {X, S, pub, keel, drawn} or null
export function beltDoor(T, fam, door) {
  if (!T || !fam) return null; const c = T.fit && T.fit.cargo && T.fit.cargo[door];
  const X = c && c.X != null ? c.X : T.L * (door === 'fwd' ? 0.22 : 0.66);
  const pub = (c && c.pub) || (BELT_PUB[fam] && BELT_PUB[fam][door]) || null;
  let S = c && c.sill != null ? c.sill : pub ? (pub[0] + pub[1]) / 2 : null; if (S == null) return null;
  const keel = T.fit && T.fit.keelAt ? T.fit.keelAt(X) : null;
  S = keel != null ? Math.max(S, keel + 0.05) : Math.max(S, lowSkin(T) + BELT_THICK);
  return { X, S: Math.round(S * 100) / 100, pub, keel, drawn: !!(c && c.sill != null) };
}
// the conveyor end's distance from the centre line at station X for conveyor top S: the rendered starboard skin + 0.03 m
// (T.fit.skinHW; procedural airframes: the elliptical section + 0.05 m)
export function beltEndY(T, X, S) {
  const v = T.fit && T.fit.skinHW ? T.fit.skinHW(X, S) : null; if (v != null) return v + 0.03;
  const a = Math.max(0.5, ((T.fit && T.fit.renderedCrown) || T.Hc + T.R) - T.Hc); return T.R * Math.sqrt(Math.max(0, 1 - ((S - T.Hc) / a) ** 2)) + 0.05;
}
// (old API, kept for the checkers: the conveyor top of that door)
export function beltSill(T, fam, door) { const D = beltDoor(T, fam, door); return D ? D.S : null; }
export const beltKey = (S) => 'belt' + Math.round(S * 100);
// catering truck: its box is lifted to the floor of the door it serves (the second door, R2): the rendered door-2 sill
// (T.dockSill2, else door 1's rendered sill raised by the model's nose-down pitch over the door spacing), to 0.2 m; at
// least 2.8 m (over the 2.6 m cab). Before: one box at 3.6-6.2 m for every type - 1.4 m under a 777's door 2 and up into
// the narrow bodies' tailplanes (review 2026-11-04: catering trucks fell from 20 to 11)
export function cateringFloor(T) {
  if (!T || !T.doors || T.doors[1] == null) return null;
  const s1 = T.dockSill ?? T.sill; const p = T.fit && T.fit.pitch ? Math.sin(T.fit.pitch.a) : 0;
  const s2 = T.dockSill2 ?? (s1 != null ? s1 + p * (T.doors[1] - T.doors[0]) : null); if (s2 == null) return null;
  return Math.max(2.8, Math.round(s2 * 5) / 5);
}
export const cateringKey = (F) => 'catering' + Math.round(F * 100);
// catering truck hull (local boxes [x0, x1, z0, z1, y0, y1], x towards the aircraft): chassis, cab, lifted box, column
export const cateringBoxes = (F) => [[-3.5, 3.0, -1.1, 1.1, 0, 1.6], [3.0, 4.55, -1.1, 1.1, 0, 2.6], [-3.4, 2.8, -1.2, 1.2, F, F + 2.6], [-3.0, 2.4, -0.3, 0.3, 1.6, F]];
// every conveyor / box setting the types at the contact stands need (the meshes are built once, before any placement;
// memoised, so a checker that rebuilds the meshes later - jobs/extract2d.mjs - gets the same keys even after a model was
// re-seated by fit.js seatType: placeVehicles snaps such a type to the nearest setting)
let VSET = null;
export function vehicleSettings() {
  if (VSET) return VSET;
  const belts = {}, caterings = {};
  for (const [k, T] of Object.entries(TYPES)) { if (!T || !T.wing || !T.doors || k.startsWith('biz_')) continue;
    const fam = beltFamily(k); if (fam) for (const d of ['fwd', 'aft']) { const D = beltDoor(T, fam, d); if (D) belts[beltKey(D.S)] = D.S; }
    const F = cateringFloor(T); if (F != null) caterings[cateringKey(F)] = F; }
  return (VSET = { belts, caterings });
}
// (the old offline renderer's GateSystem, js/scene.js, keeps its two fixed meshes)
const LEGACY_SET = { belts: { beltLoader: 1.55 }, caterings: { catering: 3.6 } };
// local shape (x forward to the aircraft end, y up, z right): conveyor box from (x0, y0) tilted by th about z; its top
// surface ends at (xe, S); chassis -2.5..2.4 m up to chassisTop; cab on the left (-z) side up to 2.05 m
export function beltShape(S) {
  const x0 = -2.9, y0 = 0.75, len = 8.0, thick = BELT_THICK, w = 0.9;
  let th = 0; for (let i = 0; i < 40; i++) th = Math.asin(Math.max(-0.5, Math.min(0.9, (S - y0 - thick * Math.cos(th)) / len)));
  return { x0, y0, len, thick, w, th, xe: x0 + len * Math.cos(th) - thick * Math.sin(th), S, chassisTop: 0.75, cabTop: 2.05 };
}
export function buildVehicleMeshes(set) { const M = vehicleGeos(set); const out = {}; for (const k in M) out[k] = new Mesh(M[k].data()); return out; }
// the vehicle geometries (Geo, local metres) - also read by the checkers; set: vehicleSettings() (computed after
// js/aircraft/fit.js has fitted the models: js/live/gates.js imports it first)
export function vehicleGeos(set = vehicleSettings()) {
  const T = (c) => [...c, 1];
  const paint = [0.9, 0.9, 0.9, 1], dark = [0.1, 0.1, 0.11, 1], glass = [0.05, 0.06, 0.07, 1];
  const E_PAINT = [0.45, 0, 20, 0], E_DARK = [0.8, 0, 0, 0], E_GLASS = [0.1, 0, 0, 0], E_METAL = [0.4, 0.8, 0, 0];
  const wheels = (g, xs, zw, r = 0.35, w = 0.25) => { for (const x of xs) for (const z of [-zw, zw]) g.cylinder(r, w, 10, dark, E_DARK, m4.mul(m4.translate(x, r, z + (z > 0 ? -w / 2 : w / 2) - w / 2 + w / 2), m4.rotX(Math.PI / 2))); };
  const M = {};
  { const g = new Geo(); g.box([-1.4, 0.35, -0.8], [1.4, 1.2, 0.8], paint, E_PAINT); g.box([-1.3, 1.2, -0.75], [-0.1, 2.0, 0.75], glass, E_GLASS); g.box([-1.35, 2.0, -0.8], [-0.05, 2.1, 0.8], paint, E_PAINT); wheels(g, [-0.9, 0.9], 0.8, 0.35); M.tug = g; }
  { const g = new Geo(); g.box([-1.5, 0.4, -0.85], [1.5, 0.55, 0.85], [0.3, 0.3, 0.32, 1], E_METAL); const bag = [[0.2, 0.2, 0.25], [0.5, 0.1, 0.1], [0.1, 0.2, 0.4], [0.35, 0.3, 0.2]]; for (let i = 0; i < 6; i++) g.box([-1.4 + (i % 3) * 0.95, 0.55, -0.8 + Math.floor(i / 3) * 0.8], [-0.55 + (i % 3) * 0.95, 1.0 + (i % 2) * 0.2, -0.05 + Math.floor(i / 3) * 0.8], T(bag[i % 4]), [0.8, 0, 20, 0]); g.box([-1.5, 1.3, -0.85], [1.5, 1.4, 0.85], [0.8, 0.8, 0.8, 1], E_METAL); wheels(g, [-1.0, 1.0], 0.85, 0.22, 0.15); M.cart = g; }
  // belt loaders: one mesh per conveyor setting (BELT_SILL: the top of the conveyor at the cargo-door sill)
  for (const [k, S] of Object.entries(set.belts)) { const B = beltShape(S); const g = new Geo();
    g.box([-2.5, 0.35, -1.05], [2.4, B.chassisTop, 1.05], paint, E_PAINT);                                  // chassis
    g.box([-2.5, B.chassisTop, -1.05], [-1.25, 1.95, -0.52], glass, E_GLASS); g.box([-2.55, 1.95, -1.08], [-1.2, 2.05, -0.5], paint, E_PAINT); // driver's cab (left side)
    const bm = m4.mul(m4.translate(B.x0, B.y0, 0), m4.rotZ(B.th)); g.box([0, 0, -B.w / 2], [B.len, B.thick, B.w / 2], dark, E_DARK, bm); // conveyor
    for (const sz of [-1, 1]) { g.box([0, B.thick, sz * B.w / 2 - 0.03], [B.len - BELT_RAIL_GAP, B.thick + 0.25, sz * B.w / 2 + 0.03], [0.85, 0.7, 0.1, 1], E_PAINT, bm); } // side rails (not on the end section)
    const xs = 1.6, ys = B.y0 + (xs - B.x0) * Math.tan(B.th); g.box([xs - 0.12, B.chassisTop, -0.3], [xs + 0.12, Math.max(B.chassisTop + 0.05, ys), 0.3], [0.3, 0.3, 0.32, 1], E_METAL); // lift strut
    wheels(g, [-1.6, 1.6], 1.0); M[k] = g; }
  // catering trucks: one mesh per box floor (cateringFloor); box 2.6 m tall on a scissor column (CATER_BOXES: the hull)
  for (const [k, F] of Object.entries(set.caterings)) { const g = new Geo(); g.box([-3.5, 0.5, -1.1], [3.0, 1.6, 1.1], paint, E_PAINT); g.box([3.0, 0.5, -1.1], [4.5, 2.6, 1.1], paint, E_PAINT); g.box([3.9, 1.6, -1.05], [4.55, 2.4, 1.05], glass, E_GLASS);
    g.box([-3.4, F, -1.2], [2.8, F + 2.6, 1.2], [0.95, 0.95, 0.95, 1], [0.5, 0, 2, 0]); g.box([-3.0, 1.6, -0.3], [2.4, F, 0.3], [0.3, 0.3, 0.32, 1], E_METAL); wheels(g, [-2.4, 3.6], 1.1, 0.45); M[k] = g; }
  { const g = new Geo(); g.box([2.5, 0.5, -1.2], [4.5, 2.8, 1.2], paint, E_PAINT); g.box([3.9, 1.7, -1.15], [4.55, 2.6, 1.15], glass, E_GLASS); g.cylinder(1.2, 6.0, 16, [0.85, 0.85, 0.86, 1], [0.35, 0.6, 0, 0], m4.mul(m4.translate(-3.8, 2.0, 0), m4.rotZ(-Math.PI / 2))); wheels(g, [-3, -1.5, 3.5], 1.2, 0.5); M.fuel = g; }
  { const g = new Geo(); g.box([-1.2, 0.3, -0.7], [1.2, 1.5, 0.7], paint, E_PAINT); wheels(g, [-0.8, 0.8], 0.7, 0.28); M.gpu = g; }
  { const g = new Geo(); g.lathe([[0.22, 0], [0.05, 0.75]], 10, [0.95, 0.35, 0.05, 1], [0.6, 0, 0, 0], null, true); M.cone = g; }
  return M;
}
