// forked from sfo3d@e3218d6 js/world/gates.js
// Ground service vehicle meshes for SHA Live 3D (instanced): belt loaders, baggage tug + carts, catering trucks, fuel
// truck, GPU, cones (sfo3d, unchanged) and, new for sha3d, self-propelled passenger stairs and an apron bus for the remote
// stands (no ZSSS ground-handling source: their dimensions and use are inferred, see STAIRS / BUS below).
// sha3d changes: the SFO airport-grid import (stToWorld) and sfo3d's legacy offline GateSystem class (the old renderer's
// fixed-mesh bridges, js/scene.js) are removed - the jet bridges are js/live/gate_system.js; vehicleSettings() also lists
// the stair platform heights (stairsNNN keys, one mesh per 0.1 m of door sill).
import { Mesh } from '../gl.js';
import { Geo } from '../geom.js';
import { m4 } from '../math.js';
import { TYPES } from '../aircraft/model.js';

function inst(M, data = [0, 0, 0, 0]) { // 3x4 rows + data
  return [M[0], M[4], M[8], M[12], M[1], M[5], M[9], M[13], M[2], M[6], M[10], M[14], ...data];
}
export { inst };

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
// the conveyor end's distance from the centre line at station X for conveyor top S: every point of the end face's top
// edge 0.03 m outside the rendered starboard skin (T.fit.skinHW; procedural airframes: the elliptical section + 0.05 m).
// face = [aX, aY]: the top edge's half extent from its centre to one corner, aX along the fuselage (m aft), aY outboard
// (js/live/gates.js passes the conveyor's yaw: at 72 deg off the axis the corners are 0.43 m fore / aft and 0.14 m in /
// out of the centre); default the conveyor's half width along the axis. Before close-out round 5 the end was placed by
// its centre line only and its forward (737 NG / MAX aft doors) or aft corner (A319 aft door) went 0.04-0.12 m into the
// closed cargo-door skin where the keel rises aft (aircraft verifier c4 F3, belt_w2.mjs)
export const BELT_W = 0.9;
export function beltEndY(T, X, S, face = null) {
  const [aX, aY] = face || [BELT_W / 2, 0]; let y = null;
  if (T.fit && T.fit.skinHW) for (const t of [-1, -0.5, 0, 0.5, 1]) { const v = T.fit.skinHW(X + aX * t, S); if (v != null && (y == null || v - aY * t > y)) y = v - aY * t; }
  if (y != null) return y + 0.03;
  const a = Math.max(0.5, ((T.fit && T.fit.renderedCrown) || T.Hc + T.R) - T.Hc); return T.R * Math.sqrt(Math.max(0, 1 - ((S - T.Hc) / a) ** 2)) + Math.abs(aY) + 0.05;
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
// every conveyor / box / stair setting the types need (the meshes are built once, before any placement; memoised, so a
// checker that rebuilds the meshes later gets the same keys even after a model was re-seated by fit.js seatType:
// placeVehicles snaps such a type to the nearest setting)
let VSET = null;
export function vehicleSettings() {
  if (VSET) return VSET;
  const belts = {}, caterings = {}, stairs = {};
  for (const [k, T] of Object.entries(TYPES)) { if (!T || !T.wing || !T.doors || k.startsWith('biz_')) continue;
    const fam = beltFamily(k); if (fam) for (const d of ['fwd', 'aft']) { const D = beltDoor(T, fam, d); if (D) belts[beltKey(D.S)] = D.S; }
    const F = cateringFloor(T); if (F != null) caterings[cateringKey(F)] = F;
    for (const D of stairDoors(T)) stairs[stairKey(D.S)] = D.S; }
  return (VSET = { belts, caterings, stairs });
}
// ---------------------------------------------------------------- passenger stairs and apron bus (sha3d, remote stands)
// Self-propelled passenger stairs (sha3d; no ZSSS ground-handling source: the unit, its size and the two-stair practice
// are INFERRED from common practice): platform 1.8 m deep x 1.7 m wide with 1.0 m handrails, floor at the door sill;
// flight 1.3 m wide at 38 deg down to a 1.0 m bottom step over a truck chassis (0.4-0.95 m, 2.2 m wide); driver cab at
// the front left under the platform where the platform is high enough (sill >= 2.35 m). Local frame: x forward (towards
// the fuselage), z right, y up; the platform's front edge at x = xFront = 0.
// The doors a remote stand boards through: door 1L and the last left door (narrow bodies: front + rear boarding), or door
// 1L and the second-bridge door (door 2L, wide bodies). x = station from the nose tip, S = sill above the apron (door 1:
// the fitted dockSill; aft: the door-1 sill + the model's pitch over the door spacing, as cateringFloor), hw = the widest
// rendered skin half width over the door opening (the stair's front edge stops 0.15 m outside it, as the bridge cab).
export function stairDoors(T) {
  if (!T || !T.doors || !T.doors.length) return [];
  const p = T.fit && T.fit.pitch ? Math.sin(T.fit.pitch.a) : 0; const s1 = T.dockSill ?? T.sill ?? (T.Hc - 0.3 * T.R);
  const x1 = T.dockX1 ?? T.doors[0]; const wide = T.dock2 != null || T.R > 2.6;
  const skin = (x, S, fb) => { if (!(T.fit && T.fit.skinHW)) return fb; let w = null; for (let y = S; y <= S + 1.9; y += 0.1) { const v = T.fit.skinHW(x, y); if (v != null && (w == null || v > w)) w = v; } return w ?? fb; };
  const out = [{ x: x1, S: q10(s1), hw: T.dockHW ?? T.R, door: 1 }];
  let xa = null, Sa = null, hwa = null;
  if (wide && T.dockX2 != null) { xa = T.dockX2; Sa = T.dockSill2 ?? (s1 + p * (xa - x1)); hwa = T.dockHW2 ?? null; }
  else { xa = wide ? T.doors[1] : T.doors[T.doors.length - 1]; if (xa != null) Sa = s1 + p * (xa - x1); }
  if (xa != null && xa - x1 > 6) out.push({ x: xa, S: q10(Sa), hw: hwa ?? skin(xa, Sa, T.R), door: 2 });
  return out;
}
const q10 = (S) => Math.max(1.0, Math.round(S * 10) / 10);
export const stairKey = (S) => 'stairs' + Math.round(S * 100);
const STAIR_ANGLE = 38 * Math.PI / 180;
export function stairShape(S) {
  const xFront = 0, xP0 = xFront - 1.8, run = Math.max(0.6, (S - 1.0) / Math.tan(STAIR_ANGLE));
  const x0 = Math.min(xP0 - run - 0.3, xFront - 5.0);
  return { S, xFront, xP0, run, x0, cab: S >= 2.35, cabTop: Math.min(2.3, S - 0.3) };
}
// hull (local boxes [x0, x1, z0, z1, y0, y1, closure]): chassis, cab, the flight in three steps of height, the platform;
// the platform's front 0.6 m is the closure (it may meet the fuselage skin: placeVehicles tests it with no margin)
export function stairHull(S) {
  const h = stairShape(S); const out = [[h.x0, h.xFront - 0.4, -1.1, 1.1, 0, 0.95]];
  if (h.cab) out.push([h.xFront - 2.4, h.xFront - 0.4, -1.1, -0.2, 0, h.cabTop]);
  for (let k = 0; k < 3; k++) out.push([h.xP0 - h.run * (1 - k / 3), h.xP0 - h.run * (1 - (k + 1) / 3), -0.75, 0.75, 0, 1.0 + (S - 1.0) * (k + 1) / 3 + 1.0]);
  out.push([h.xP0, h.xFront - 0.6, -0.9, 0.9, 0.95, S + 1.05]);
  out.push([h.xFront - 0.6, h.xFront, -0.9, 0.9, S - 0.4, S + 1.05, 1]);
  return out;
}
// apron bus (inferred: a 14 m low-floor airside bus, 3.0 m wide, 3.1 m high, doors on the right side; no ZSSS fleet
// source). Local frame as above: x forward, z right.
export const BUS_HULL = [[-7.0, 7.0, -1.5, 1.5, 0, 3.1]];
// local shape (x forward to the aircraft end, y up, z right): conveyor box from (x0, y0) tilted by th about z; its top
// surface ends at (xe, S); chassis -2.5..2.4 m up to chassisTop; cab on the left (-z) side up to 2.05 m
export function beltShape(S) {
  const x0 = -2.9, y0 = 0.75, len = 8.0, thick = BELT_THICK, w = BELT_W;
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
  // passenger stairs (sha3d): one mesh per platform height (stairShape)
  const steel = [0.42, 0.43, 0.45, 1], rail = [0.92, 0.72, 0.1, 1], E_STEP = [0.55, 0.3, 0, 0];
  for (const [k, S] of Object.entries(set.stairs || {})) { const h = stairShape(S); const g = new Geo();
    g.box([h.x0, 0.4, -1.1], [h.xFront - 0.4, 0.95, 1.1], paint, E_PAINT);                                   // chassis
    if (h.cab) { g.box([h.xFront - 2.4, 0.95, -1.1], [h.xFront - 0.4, h.cabTop - 0.5, -0.2], paint, E_PAINT); g.box([h.xFront - 2.35, h.cabTop - 0.5, -1.08], [h.xFront - 0.45, h.cabTop, -0.22], glass, E_GLASS); }
    g.box([h.xP0, S - 0.15, -0.85], [h.xFront, S, 0.85], steel, E_STEP);                                    // platform
    for (const z of [-0.85, 0.85]) { g.box([h.xP0, S + 0.95, z - 0.03], [h.xFront - 0.1, S + 1.0, z + 0.03], rail, E_PAINT); for (const x of [h.xP0 + 0.05, h.xFront - 0.15]) g.box([x - 0.03, S, z - 0.03], [x + 0.03, S + 1.0, z + 0.03], rail, E_PAINT); }
    g.box([h.xP0, 0.95, -0.6], [h.xP0 + 0.5, S - 0.15, 0.6], steel, E_METAL);                               // platform column
    // flight: stringers, steps (0.2 m risers), handrails
    const nS = Math.max(2, Math.round((S - 1.0) / 0.2)), dx = h.run / nS, dy = (S - 1.0) / nS;
    for (let i = 0; i < nS; i++) { const x = h.xP0 - h.run + i * dx, y = 1.0 + i * dy; g.box([x, y, -0.65], [x + dx + 0.02, y + 0.06, 0.65], steel, E_STEP); }
    const sl = Math.hypot(h.run, S - 1.0), fl = m4.mul(m4.translate(h.xP0 - h.run, 1.0, 0), m4.rotZ(STAIR_ANGLE));
    for (const z of [-0.68, 0.68]) { g.box([0, -0.3, z - 0.04], [sl, 0.05, z + 0.04], steel, E_METAL, fl); g.box([0, 0.95, z - 0.03], [sl, 1.0, z + 0.03], rail, E_PAINT, fl); }
    for (const t of [0.35, 0.7]) { const x = h.xP0 - h.run * (1 - t); g.box([x - 0.12, 0.95, -0.5], [x + 0.12, 1.0 + (S - 1.0) * t - 0.25, 0.5], steel, E_METAL); }
    wheels(g, [h.x0 + 1.0, h.xFront - 1.6], 1.0, 0.4, 0.28); M[k] = g; }
  // apron bus (sha3d): lower body, window band with pillars, roof, two double doors on the right (+z) side
  { const g = new Geo(); const body = [0.93, 0.94, 0.95, 1];
    g.box([-7.0, 0.35, -1.5], [7.0, 1.05, 1.5], body, E_PAINT); g.box([-6.95, 1.05, -1.48], [6.95, 2.55, 1.48], glass, E_GLASS);
    for (let x = -6.9; x <= 6.9; x += 1.38) for (const z of [-1.5, 1.45]) g.box([x - 0.06, 1.05, z], [x + 0.06, 2.55, z + 0.05], body, E_PAINT);
    g.box([-7.0, 2.55, -1.5], [7.0, 3.1, 1.5], body, E_PAINT); g.box([-5.0, 3.1, -1.0], [-2.6, 3.3, 1.0], body, E_PAINT); // roof + A/C pod
    for (const x of [-3.2, 3.2]) g.box([x - 0.75, 0.3, 1.5], [x + 0.75, 2.5, 1.53], [0.25, 0.27, 0.3, 1], E_GLASS);   // doors (right side)
    g.box([-0.4, 0.5, 1.5], [0.4, 0.9, 1.52], [0.85, 0.65, 0.1, 1], E_PAINT);
    wheels(g, [-5.3, 5.3], 1.35, 0.5, 0.32); M.bus = g; }
  return M;
}
