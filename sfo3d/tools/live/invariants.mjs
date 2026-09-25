// Physical-plausibility invariant checker for the live traffic engine, on REAL recorded traffic.
//
// Replays the relay's SSE event sequence (tools/live/build_stream.py: the recorder files through sfo_live_server.py's
// own merge) through the app's engine in node -- js/live/feed.js parsePayload, js/live/traffic.js Traffic,
// js/live/ground.js GroundPhysics, wired as js/live/app.js wires them -- on a simulated clock at 10 Hz, and checks EVERY
// frame of what the app would draw. The jet bridges are emulated with js/live/gates.js's own prepBridge()/pose()/
// setOccupant()/anim code (LiveGateSystem instance without its WebGL constructor), fed by the same onGateChange the app
// uses (app.js applyGate/poseST).
//
// Invariant classes (counts = frames at 10 Hz; episodes = contiguous runs per aircraft, gap <= 2 s):
//   overlap.gnd           two ground aircraft planforms intersect (fuselage/wing/stabiliser convex pieces, SAT)
//   clear.stand           two STATIONARY ground aircraft closer than the ICAO Annex 14 s.3.13.6 stand clearance
//                         (3 m code A/B, 4.5 m code C, 7.5 m code D-F; the larger code of the pair)
//   clear.taxi            a moving ground aircraft within 1 m of another (and not overlapping)
//   overlap.lowair        an aircraft < 15 m AGL over a ground aircraft's planform with < 6 m vertical separation
//   building              planform sample point (1 m grid) inside a building (js/live/ground.js buildingGrid)
//   offpave.mask / .union gear point (nose, both mains) off the rendered pavement mask / off mask UNION OSM net
//   bridge.hit.fus|wing|tail  aircraft part inside a jet bridge (walkway, rotunda, tunnel, drive column, cab) in 3-D
//                         (height bands from the type table vs gates.js bridge floor heights)
//   bridge.misdock        a bridge docked (k > 0.5) whose door target is > 1.5 m from the displayed door of its occupant
//   bridge.orphan         a bridge docked (k > 0.5) with no displayed aircraft within 10 m of its door target
//   bridge.attached.moving  occupant moving (> 0.3 m/s) while its bridge is still > 50 % extended
//   gnd.speed.taxi        > 35 kt on the surface more than 100 m from every runway centreline
//   gnd.acc / gnd.lat / gnd.jerk / gnd.yaw / gnd.slip   longitudinal > 3.5 m/s2 (rollout; 2.0 m/s2 taxi), lateral
//                         > 3 m/s2, jerk > 6 m/s3, yaw rate > 25 deg/s, sideslip at the main gear > 5 deg (> 1 m/s)
//   gnd.reverse           moving backwards > 0.5 m/s outside a push-back
//   gnd.spin              stopped (< 0.2 m/s) but yawing > 2.5 deg/s
//   gnd.slide             reference point moves > 0.15 m/s while the body's wheel speed is 0 (tow code path)
//   air.acc / air.lat / air.turn / air.vacc / air.vs      along-track > 3 m/s2, lateral > 6 m/s2 (31 deg bank; x1.7
//                         light), turn > 7 deg/s (x1.8 light), vertical acc > 3 m/s2, |vs| > 8000 fpm below 10,000 ft
//   teleport              a frame displacement that differs from the previous velocity * dt by > 20 m (+ reason)
//   jump.gnd_1_20m / jump.air_5_20m  the same deviation > 1 m on the ground (> 100 m/s2 implied) / > 5 m in the air
//   hdg.flip              heading change > 20 deg in one 0.1 s frame
//   vert.ground           ground aircraft with y != GROUND_Y;  vert.below: y < GROUND_Y
//   vert.float            airborne, < 1 m AGL, < 50 kt, not a rotorcraft, inside SFO (hovering on the ramp);
//                         vert.float.other_airfield: the same elsewhere (GA fields, where GROUND_Y is not the terrain)
//   vert.lowfly           airborne < 60 m AGL inside the airport more than 400 m from every runway centreline
//   rwy.change.final      the displayed runway of an aircraft on final changes
//   rwy.td.before_thr     displayed touchdown before the landing threshold (a < 0) of the assigned runway
//   rwy.td.offrunway      displayed touchdown not on the assigned runway's pavement (|c| > 30.5 m) / wrong runway
//   rwy.td.norwy          touchdown displayed with no assigned runway
//   rwy.truth.*           engine events vs an independent raw-data detector: landings (runway of the first fast
//                         ground report), take-offs (runway of the last fast ground report), go-arounds (descending
//                         >= 400 fpm at > 90 kt below 1200 ft within 6 nm, aligned with a runway, then climbed >= 400 ft
//                         without a ground report; runway = nearest centreline at the lowest point). Limitation: E175
//                         landings flagged airborne down to ~50 kt can be missed by the landing detector.
//   phase.*               displayed phase contradicts displayed geometry (air phase on the ground, ground phase in
//                         the air, 'taxi' > 50 kt on a runway, 'gate' > 30 m from its stand, 'landing'/'takeoff' off a
//                         runway, push-back moving forward, flicker = > 3 phase changes within 30 s)
//
// Usage: CANVAS_MODULE=/abs/node_modules/@napi-rs/canvas/index.js node tools/live/invariants.mjs --stream S.jsonl.gz
//          [--gates G.jsonl.gz] [--from ISO|epoch] [--until ISO|epoch] [--warm 600] [--root <code root>] [--out R.json]
//          [--fast] (skip surface/pair/bridge checks) [--trace <hex>] (per-0.5 s display/target/park state to stderr)
// --from/--until bound the CHECKED window; the replay starts --warm seconds earlier (tracks, stands, delay settle).
// --root runs another copy of the code (e.g. a frozen snapshot) with the same data layout.
import fs from 'fs'; import path from 'path'; import zlib from 'zlib'; import readline from 'readline'; import { fileURLToPath } from 'url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2); const opt = (k, d) => { const i = argv.indexOf('--' + k); return i >= 0 ? argv[i + 1] : d; };
const ROOT = path.resolve(opt('root', path.resolve(HERE, '..', '..')));
const STREAM = opt('stream'); const GATES = opt('gates', STREAM && path.join(path.dirname(STREAM), 'gates.jsonl.gz'));
const pt = (s) => s == null ? null : /^\d+(\.\d+)?$/.test(s) ? +s : Date.parse(s) / 1000;
const FROM = pt(opt('from')), UNTIL = pt(opt('until')), WARM = +opt('warm', 600), DT = 0.1, LAT = 0.08;
const FAST = argv.includes('--fast'); // skip the surface / pair / bridge checks (kinematics, phases, runways, truth only)
const TRACE = opt('trace', null); // hex: print that aircraft's display/target/park state every 0.5 s to stderr
const OUTF = opt('out', STREAM ? STREAM.replace(/stream\.jsonl\.gz$/, 'invariants.json') : 'invariants.json');
if (!STREAM) { console.error('--stream required'); process.exit(1); }

let createCanvas;
for (const m of [process.env.CANVAS_MODULE, '@napi-rs/canvas'].filter(Boolean)) { try { ({ createCanvas } = await import(m)); break; } catch (e) { } }
if (!createCanvas) { console.error('no canvas module: set CANVAS_MODULE'); process.exit(1); }
globalThis.document = { createElement: () => createCanvas(1, 1), hidden: false };
globalThis.localStorage = { getItem: () => null, setItem: () => { }, removeItem: () => { } };

const imp = (p) => import(path.join(ROOT, p));
const { AIRPORT } = await imp('data/sfo_airport.js'); const { DETAILS } = await imp('data/sfo_details.js'); const { STANDS } = await imp('data/sfo_stands.js');
const { PAINT } = await imp('data/sfo_paint.js'); const { PAVEMENT } = await imp('data/sfo_pavement.js');
let TAXIGRAPH = null; try { ({ TAXIGRAPH } = await imp('data/sfo_taxigraph.js')); } catch (e) { console.error('no taxi graph'); }
const { standGates, paintAirportMapReal, endZoneRects } = await imp('js/live/airport.js');
const TR = await imp('js/live/traffic.js'); const { Traffic, RWY, hdgVec } = TR;
const antOf = TR.antOf || ((T) => TR.ANT * T.L);   // position reference behind the nose (per family, traffic.js)
const { GroundPhysics, buildingGrid, pavedUnion } = await imp('js/live/ground.js');
const { parsePayload } = await imp('js/live/feed.js');
const { TYPES } = await imp('js/aircraft/types.js');
const GEO = await imp('js/geo.js'); const { GROUND_Y, worldToST } = GEO; const toLL = GEO.worldToWgs84 || GEO.worldToLL; const toW = GEO.wgs84ToWorld || GEO.llToWorld;
const { LiveGateSystem } = await imp('js/live/gates.js');

const gates = standGates(STANDS);
const apt = paintAirportMapReal(AIRPORT, gates, undefined, DETAILS, { paint: PAINT, pavement: PAVEMENT, endZones: endZoneRects() });
const building = buildingGrid(AIRPORT);
let simNow = 0, checkFrom = Infinity;
// ---- jet bridges: gates.js code on an instance without the WebGL constructor
const gsys = Object.create(LiveGateSystem.prototype); gsys.gates = gates; gsys.anims = new Map(); gsys.dirty = false;
for (const g of gates) for (const b of g.bridges || []) gsys.prepBridge(g, b);
let booted = false;
// (as js/live/app.js: the bridge docks to the DRAWN pose the aircraft came to rest in, tr.dockPose; an alternative (MARS)
// stand without bridges uses its base stand's bridges; only aircraft with a 3-D airframe are docked)
const poseST = (tr) => { const T = tr.model && TYPES[tr.model.t] || TYPES.a320; const P = tr.dockPose || (tr.parkPos ? { x: tr.parkPos[0], z: tr.parkPos[1], hdg: tr.parkHdg } : { x: tr.last.x, z: tr.last.z, hdg: tr.last.hd }); const h = hdgVec(P.hdg); const k = antOf(T);
  const n = worldToST(P.x + h[0] * k, P.z + h[1] * k), o = worldToST(0, 0), d = worldToST(h[0], h[1]); return { nose: n, dir: [d[0] - o[0], d[1] - o[1]] }; };
const gateByName = new Map(gates.map(g => [g.name, g]));
const bridgeGate = (g) => (g.sharesBridgesOf && !(g.bridges && g.bridges.length) && gateByName.get(g.sharesBridgesOf)) || g;
const occ = new Map(); // physical gate name -> occupant track (as the bridge system was told)
function applyGate(g, tr) { const G = bridgeGate(g); const ty = tr && tr.model && TYPES[tr.model.t] ? tr.model.t : null; occ.set(G.name, ty ? tr : null); gsys.setOccupant(G, ty, booted, simNow, tr ? poseST(tr) : null, tr ? tr.info.icao : null); }
function bridgeK(g, b) { const a = gsys.anims.get(g.id); if (a) return gsys.docks(g, b) ? a.k : 0; return g.acType && gsys.docks(g, b) ? 1 : 0; }
function animStep(now) { for (const [id, a] of gsys.anims) { const u = Math.min(1, Math.max(0, (now - a.t0) / a.dur)); a.k = a.from + (a.to - a.from) * u; if (u >= 1) gsys.anims.delete(id); } }

const traffic = new Traffic({ gates, airport: AIRPORT, persist: false, centerlines: DETAILS.centerlines, taxigraph: TAXIGRAPH, stands: STANDS, onGateChange: (g, tr) => applyGate(g, tr) });
traffic.buildingAt = building; if (TRACE) traffic.debug = TRACE;
traffic.bridgeK = (g) => { const G = bridgeGate(g); const a = gsys.anims.get(G.id); return a ? a.k : (G.acType ? 1 : 0); };
const physics = new GroundPhysics({ paved: apt.paved, building, net: traffic.net });
const pavedMask = apt.paved, pavedAll = pavedUnion(apt.paved, traffic.net);

// ---------------------------------------------------------------- geometry helpers
const DEG = Math.PI / 180, KT = 0.514444, FT = 0.3048;
const wrapD = (a) => { a = (a + 180) % 360; if (a < 0) a += 360; return a - 180; };
const wrapPi = (a) => { a = (a + Math.PI) % (2 * Math.PI); if (a < 0) a += 2 * Math.PI; return a - Math.PI; };
const RW = RWY.map(R => ({ ...R }));
const rwyCoords = (R, x, z) => { const dx = x - R.thr[0], dz = z - R.thr[1]; return [dx * R.dir[0] + dz * R.dir[1], -dx * R.dir[1] + dz * R.dir[0]]; };
const rwyPhys = (R, x, z) => { const dx = x - R.start[0], dz = z - R.start[1]; return [dx * R.dir[0] + dz * R.dir[1], -dx * R.dir[1] + dz * R.dir[0]]; };
function runwaysAt(x, z, halfW = 30.5) { const out = []; for (const R of RW) { const [a, c] = rwyPhys(R, x, z); if (a > -5 && a < R.len + 5 && Math.abs(c) < halfW) out.push(R); } return out; }
function nearRunwayCL(x, z, ext = 0) { let best = 1e9; for (const R of RW) { const [a, c] = rwyPhys(R, x, z); const aa = Math.max(-ext, Math.min(R.len + ext, a)); best = Math.min(best, Math.hypot(a - aa, c)); } return best; }
const inAirport = (x, z) => x > -2700 && x < 1950 && z > -2350 && z < 1800;

// planform: convex pieces in body coordinates (x aft of the nose, y to the right) with height bands (m AGL)
const shapeCache = new Map();
function shapeOf(key) {
  let S = shapeCache.get(key); if (S) return S; const T = TYPES[key];
  const w = T.wing, span = w ? w.span / 2 : 16, le = w ? w.rootLE : T.L * 0.4, sw = Math.tan(((w && w.sweep) || 27) * DEG), rc = w ? w.rootC : 5, tc = w ? w.tipC : 1.5;
  const hs = T.hstab ? T.hstab.span / 2 : 5, hx = T.hstab ? T.hstab.x : T.L - 5, hrc = T.hstab ? (T.hstab.rootC || 3) : 3, htc = T.hstab ? (T.hstab.tipC || 1.2) : 1.2, hsw = Math.tan(((T.hstab && T.hstab.sweep) || 30) * DEG);
  const Hc = T.Hc || 3.5, R = T.R || 2, wy = w ? (w.y ?? 0.5) : 0.5, dih = Math.tan(((w && w.dihedral) || 5) * DEG), hy = T.hstab ? (T.hstab.y ?? 0.3) : 0.3, hdih = Math.tan(((T.hstab && T.hstab.dihedral) || 5) * DEG);
  const pieces = [
    { kind: 'fus', poly: [[0, -R], [T.L, -R], [T.L, R], [0, R]] },
    { kind: 'wing', poly: [[le, 0], [le + rc, 0], [le + span * sw + tc, span], [le + span * sw, span]] },
    { kind: 'wing', poly: [[le, 0], [le + span * sw, -span], [le + span * sw + tc, -span], [le + rc, 0]] },
    { kind: 'tail', poly: [[hx, 0], [hx + hs * hsw, hs], [hx + hs * hsw + htc, hs], [Math.min(T.L, hx + hrc), 0]] },
    { kind: 'tail', poly: [[hx, 0], [Math.min(T.L, hx + hrc), 0], [hx + hs * hsw + htc, -hs], [hx + hs * hsw, -hs]] },
  ];
  // sample points (1 m grid inside each piece + its outline) with height bands
  const pts = [];
  const inPoly = (P, x, y) => { let c = false; for (let i = 0, j = P.length - 1; i < P.length; j = i++) { const a = P[i], b = P[j]; if ((a[1] > y) !== (b[1] > y) && x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]) c = !c; } return c; };
  pieces.forEach((pc, pi) => {
    const P = pc.poly; let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9; for (const p of P) { x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0]); y0 = Math.min(y0, p[1]); y1 = Math.max(y1, p[1]); }
    const add = (x, y) => {
      const ay = Math.abs(y); let lo, hi;
      if (pc.kind === 'fus') { const e = Math.sqrt(Math.max(0, 1 - (ay / R) ** 2)) * R; lo = Hc - e; hi = Hc + e; }
      else if (pc.kind === 'wing') { const z = Hc - wy * R + ay * dih; lo = z - 0.35; hi = z + 0.35; }
      else { const z = Hc + hy * R + ay * hdih; lo = z - 0.3; hi = z + 0.3; }
      pts.push([x, y, lo, hi, pc.kind, pi]);
    };
    for (let x = Math.ceil(x0); x <= x1; x += 1) for (let y = Math.ceil(y0); y <= y1; y += 1) if (inPoly(P, x, y)) add(x, y);
    for (let i = 0; i < P.length; i++) { const a = P[i], b = P[(i + 1) % P.length]; const L = Math.hypot(b[0] - a[0], b[1] - a[1]); const n = Math.max(1, Math.ceil(L)); for (let k = 0; k < n; k++) add(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n); }
  });
  const gear = [[T.xNose ?? 3, 0], [T.xMain, (T.track || 6) / 2], [T.xMain, -(T.track || 6) / 2]];
  const code = (() => { const s = w ? w.span : 36; return s < 24 ? 'B' : s < 36 ? 'C' : s < 52 ? 'D' : s < 65 ? 'E' : 'F'; })();
  S = { T, pieces, pts, gear, code, reach: Math.hypot(T.L, span) + 2 }; shapeCache.set(key, S); return S;
}
// body pose in world: displayed reference point (ADS-B antenna) -> nose
function pose(tr) { const D = tr.disp; const key = tr.model && TYPES[tr.model.t] ? tr.model.t : null; if (!key) return null; const S = shapeOf(key); const f = hdgVec(D.hdg), r = [-f[1], f[0]]; const k = antOf(S.T); const nose = [D.x + f[0] * k, D.z + f[1] * k];
  const W = (x, y) => [nose[0] - f[0] * x + r[0] * y, nose[1] - f[1] * x + r[1] * y];
  const cx = S.T.L * 0.45; const c = W(cx, 0); return { tr, S, f, r, nose, W, c, polys: null }; }
function worldPolys(B) { if (!B.polys) B.polys = B.S.pieces.map(pc => pc.poly.map(p => B.W(p[0], p[1]))); return B.polys; }
// SAT intersection and distance of convex polygons
function sepAxis(A, B) { for (const P of [A, B]) for (let i = 0; i < P.length; i++) { const a = P[i], b = P[(i + 1) % P.length]; const nx = -(b[1] - a[1]), nz = b[0] - a[0]; let amin = 1e18, amax = -1e18, bmin = 1e18, bmax = -1e18; for (const p of A) { const v = p[0] * nx + p[1] * nz; amin = Math.min(amin, v); amax = Math.max(amax, v); } for (const p of B) { const v = p[0] * nx + p[1] * nz; bmin = Math.min(bmin, v); bmax = Math.max(bmax, v); } if (amax < bmin || bmax < amin) return true; } return false; }
function segDist(p, a, b) { const dx = b[0] - a[0], dz = b[1] - a[1]; const L2 = dx * dx + dz * dz || 1; const u = Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L2)); return Math.hypot(p[0] - a[0] - dx * u, p[1] - a[1] - dz * u); }
function polyDist(A, B) { let d = 1e9; for (const P of [[A, B], [B, A]]) for (const p of P[0]) for (let i = 0; i < P[1].length; i++) d = Math.min(d, segDist(p, P[1][i], P[1][(i + 1) % P[1].length])); return d; }
function clearance(A, B) { // < 0 = overlap (value = - overlapping sample count, ~ m^2); else min distance (m)
  const PA = worldPolys(A), PB = worldPolys(B); let over = false, d = 1e9;
  for (const a of PA) for (const b of PB) { if (!sepAxis(a, b)) over = true; else d = Math.min(d, polyDist(a, b)); }
  if (!over) return d;
  let n = 0; const inv = (Bd, q) => { const dx = q[0] - Bd.nose[0], dz = q[1] - Bd.nose[1]; return [-(dx * Bd.f[0] + dz * Bd.f[1]), dx * Bd.r[0] + dz * Bd.r[1]]; };
  const inside = (P, x, y) => { let c = false; for (let i = 0, j = P.length - 1; i < P.length; j = i++) { const a = P[i], b = P[j]; if ((a[1] > y) !== (b[1] > y) && x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]) c = !c; } return c; };
  for (const p of A.S.pts) { const q = A.W(p[0], p[1]); const [x, y] = inv(B, q); if (B.S.pieces.some(pc => inside(pc.poly, x, y))) n++; }
  return -Math.max(1, n);
}

// ---------------------------------------------------------------- bridges in world coordinates (2-D boxes + height)
// returns boxes {c:[x,z], u:[ux,uz], hl (half length), hw (half width), lo, hi (m AGL), part}
function bridgeBoxes(g, b, k) {
  const P = gsys.pose(g, b, k); const G = GROUND_Y; const out = [];
  const seg = (A, B, w, lo0, lo1, h, part) => { const dx = B[0] - A[0], dz = B[2] - A[2]; const L = Math.hypot(dx, dz); if (L < 0.2) return; const n = Math.max(1, Math.ceil(L / 4)); for (let i = 0; i < n; i++) { const u0 = i / n, u1 = (i + 1) / n, um = (u0 + u1) / 2; const lo = lo0 + (lo1 - lo0) * um; out.push({ c: [A[0] + dx * um, A[2] + dz * um], u: [dx / L, dz / L], hl: L / n / 2, hw: w / 2, lo: lo - 0.1, hi: lo + h, part }); } };
  const rcTop = [P.rc[0], P.floorY, P.rc[2]];
  seg(P.attach, P.rc, 2.6, P.floorY - G, P.floorY - G, 3.0, 'walkway');
  out.push({ c: [P.rc[0], P.rc[2]], u: [1, 0], hl: 2.45, hw: 2.45, lo: P.floorY - G - 0.3, hi: P.floorY - G + 3.3, part: 'rotunda', round: 2.45 });
  out.push({ c: [P.rc[0], P.rc[2]], u: [1, 0], hl: 0.6, hw: 0.6, lo: 0, hi: P.floorY - G, part: 'pedestal', round: 0.6 });
  const cabBack = [P.cab[0] - P.facing[0] * 1.8, P.cab[1], P.cab[2] - P.facing[2] * 1.8];
  const dl = Math.hypot(cabBack[0] - rcTop[0], cabBack[2] - rcTop[2]) || 1; const dir = [(cabBack[0] - rcTop[0]) / dl, 0, (cabBack[2] - rcTop[2]) / dl];
  const s0 = [rcTop[0] + dir[0] * 2.2, rcTop[1], rcTop[2] + dir[2] * 2.2];
  seg(s0, cabBack, 2.82, s0[1] - G, cabBack[1] - G, 3.1, 'tunnel');
  // drive column (ground to tunnel) at 0.84 of the tunnel
  const du = [s0[0] + (cabBack[0] - s0[0]) * 0.84, s0[2] + (cabBack[2] - s0[2]) * 0.84];
  out.push({ c: du, u: [dir[0], dir[2]], hl: 0.6, hw: 1.6, lo: 0, hi: (s0[1] + (cabBack[1] - s0[1]) * 0.84) - G, part: 'column' });
  // cab box (-1.8..1.5 along facing, +-1.8 across) + bellows (to 1.5 + 0.45 + 0.4 k)
  const fl = Math.hypot(P.facing[0], P.facing[2]) || 1; const fu = [P.facing[0] / fl, P.facing[2] / fl]; const front = 1.5 + 0.45 + 0.4 * P.kk;
  const cc = [P.cab[0] + fu[0] * (front - 1.8) / 2, P.cab[2] + fu[1] * (front - 1.8) / 2];
  out.push({ c: cc, u: fu, hl: (front + 1.8) / 2, hw: 1.9, lo: P.cab[1] - G - 0.1, hi: P.cab[1] - G + 3.4, part: 'cab', front: [P.cab[0] + fu[0] * front, P.cab[2] + fu[1] * front] });
  return { boxes: out, door: P.door, P };
}
function boxPoly(bx) { if (bx.poly) return bx.poly; const P = []; if (bx.round) { for (let i = 0; i < 8; i++) { const a = i * Math.PI / 4; P.push([bx.c[0] + Math.cos(a) * bx.round * 1.083, bx.c[1] + Math.sin(a) * bx.round * 1.083]); } } else { const u = bx.u, v = [-u[1], u[0]]; for (const [sa, sc] of [[1, 1], [-1, 1], [-1, -1], [1, -1]]) P.push([bx.c[0] + u[0] * bx.hl * sa + v[0] * bx.hw * sc, bx.c[1] + u[1] * bx.hl * sa + v[1] * bx.hw * sc]); } return bx.poly = P; }
function inBox(bx, x, z) { const dx = x - bx.c[0], dz = z - bx.c[1]; if (bx.round) return Math.hypot(dx, dz) < bx.round; const a = dx * bx.u[0] + dz * bx.u[1], c = -dx * bx.u[1] + dz * bx.u[0]; return Math.abs(a) < bx.hl && Math.abs(c) < bx.hw; }
// displayed door (L1/L2) of an aircraft, same formula as gates.js doorOf
function doorW(B, which) { const T = B.S.T; const x = T.doors[Math.min(which - 1, T.doors.length - 1)]; const left = [-B.r[0], -B.r[1]]; const p = B.W(x + 0.5, 0); return [p[0] + left[0] * (T.R + 0.15), p[1] + left[1] * (T.R + 0.15)]; }

// ---------------------------------------------------------------- violation bookkeeping
const V = new Map(); // class -> {frames, eps, who: Map(hex -> {n, first, last, worst}), worst: [...]}
const checking = () => simNow >= checkFrom;
const iso = (ms) => new Date(ms).toISOString().slice(11, 21);
function viol(cls, tr, sev, extra = {}, x = null, z = null) {
  if (!checking()) return;
  let v = V.get(cls); if (!v) V.set(cls, v = { frames: 0, eps: 0, who: new Map(), worst: [] });
  v.frames++; const key = tr ? tr.hex : (extra.key || '-'); let w = v.who.get(key);
  if (!w || simNow - w.last > 2000) { v.eps++; w = { n: 0, first: simNow, last: simNow, max: -1e9 }; v.who.set(key, w); }
  w.n++; w.last = simNow;
  if (sev > w.max) {
    w.max = sev; const X = x ?? (tr ? tr.disp.x : 0), Z = z ?? (tr ? tr.disp.z : 0); const ll = toLL ? toLL(X, Z) : null;
    w.ex = { t: iso(simNow), hex: tr ? tr.hex : null, flight: tr ? (tr.info.flight || null) : null, type: tr ? (tr.info.icao || null) : null, reg: tr ? tr.info.reg || null : null, phase: tr ? tr.phase : null, mphase: tr ? tr.m.phase : null,
      x: +X.toFixed(1), z: +Z.toFixed(1), lat: ll ? +ll[0].toFixed(6) : null, lon: ll ? +ll[1].toFixed(6) : null, sev: +(+sev).toFixed(2), ...extra };
  }
}

// ---------------------------------------------------------------- independent truth from the raw payloads
const RAW = new Map(); // hex -> raw state
const truth = { landings: [], takeoffs: [], goarounds: [] };
function rawTruth(a, t) {
  if (!a.hex || a.veh) return; const w = toW(a.lat, a.lon, 0); const x = w[0], z = w[2]; const d = Math.hypot(x, z);
  let s = RAW.get(a.hex); if (!s) RAW.set(a.hex, s = { lastT: 0, air: null, arm: null, lastFastGnd: null, lastAirT: null, flight: null });
  if (t <= s.lastT) return; s.lastT = t; s.flight = a.flight || s.flight;
  const gs = a.gs ?? 0;
  // direction of motion: reported track in the air; on the surface the relay drops `track` (audit s.4.3), so use the
  // chord from the previous report, else the last airborne track
  const chord = s.lx != null && Math.hypot(x - s.lx, z - s.lz) > 15 ? Math.atan2(x - s.lx, -(z - s.lz)) / DEG : null; s.lx = x; s.lz = z;
  const dirDeg = a.ground ? (chord ?? s.airTrk) : (a.track ?? chord);
  if (!a.ground && a.track != null) s.airTrk = a.track;
  if (a.ground) {
    if (inAirport(x, z) && gs > 40) {
      const rs = runwaysAt(x, z, 40); let R = null;
      if (rs.length && dirDeg != null) { let bd = 30; for (const q of rs) { const dd = Math.abs(wrapD(dirDeg - q.hdg / DEG)); if (dd < bd) { bd = dd; R = q; } } }
      // landing: the first fast ground report after being airborne (within 60 s)
      if (s.air === true && s.lastAirT != null && t - s.lastAirT < 60000 && !s.landedT && R) { truth.landings.push({ hex: a.hex, flight: s.flight, t, rwy: R.name, a: Math.round(rwyCoords(R, x, z)[0]) }); s.landedT = t; }
      s.lastFastGnd = { t, rwy: R ? R.name : null };
    }
    s.air = false; s.arm = null; return;
  }
  // airborne
  if (s.air === false && s.lastFastGnd && t - s.lastFastGnd.t < 30000 && d < 6000 && !s.tookT) { truth.takeoffs.push({ hex: a.hex, flight: s.flight, t, rwy: s.lastFastGnd.rwy }); s.tookT = t; }
  s.air = true; s.lastAirT = t; if (s.landedT && t - s.landedT > 600000) s.landedT = null; if (s.tookT && t - s.tookT > 600000) s.tookT = null;
  const alt = a.altBaro; if (alt == null) return;
  // go-around detector: armed below 1200 ft within 6 nm, aligned with a runway and on its extended centreline, before
  // (or just past) the threshold, having descended
  const trk = a.track;
  // armed only by a real descent at approach speed: E175s report 'airborne' from ~50 kt on the take-off roll with
  // baro_rate -64..0 (24 Sep 15:25Z SKW6014), which must not arm the detector
  if (!s.arm && alt < 1200 && alt > 100 && gs > 90 && d < 11000 && trk != null && (a.baroRate ?? 0) <= -400) {
    let best = null; for (const R of RW) { if (Math.abs(wrapD(trk - R.hdg / DEG)) > 20) continue; const [aa, c] = rwyCoords(R, x, z); if (aa < 500 && aa > -12000 && Math.abs(c) < 300 + 0.05 * Math.abs(aa) && (!best || Math.abs(c) < best.c)) best = { R, c: Math.abs(c) }; }
    if (best) s.arm = { t, rwy: best.R.name, min: alt, minT: t };
  } else if (s.arm) {
    if (alt < s.arm.min) { s.arm.min = alt; s.arm.minT = t; let bc = 1e9; for (const R of RW) { if (Math.abs(wrapD((trk ?? 0) - R.hdg / DEG)) > 20) continue; const c = Math.abs(rwyCoords(R, x, z)[1]); if (c < bc) { bc = c; s.arm.rwy = R.name; } } }
    if (alt >= s.arm.min + 400 && (a.baroRate ?? 0) > 300) { truth.goarounds.push({ hex: a.hex, flight: s.flight, t: s.arm.minT, tClimb: t, rwy: s.arm.rwy, min: s.arm.min }); s.arm = null; }
    else if (t - s.arm.t > 300000 || d > 20000) s.arm = null;
  }
}

// ---------------------------------------------------------------- per-aircraft frame state
const K = new Map();
const EXC = { gAccRoll: 3.5, gAccTaxi: 2.0, gLat: 3.0, gJerk: 6.0, gYaw: 25, slip: 5, aAcc: 3.0, aLat: 6.0, aVacc: 3.0, aTurn: 7 };
const finalRwy = new Map(); // hex -> {rwy, t}
const phaseHist = new Map(); // hex -> [times of display-phase changes]
const surfCache = new Map(), pairCache = new Map(), offCells = new Map();

async function* readLines(f) { const rl = readline.createInterface({ input: fs.createReadStream(f).pipe(zlib.createGunzip()), crlfDelay: Infinity }); for await (const l of rl) if (l) yield l; }
const plans = []; if (GATES && fs.existsSync(GATES)) for await (const l of readLines(GATES)) plans.push(JSON.parse(l));
const evIt = readLines(STREAM)[Symbol.asyncIterator]();
let nextEv = null; const pull = async () => { const r = await evIt.next(); nextEv = r.done ? null : JSON.parse(r.value); };
await pull();
const t0 = FROM != null ? FROM - WARM : nextEv.T;
while (nextEv && nextEv.T < t0) await pull();
if (!nextEv) { console.error('no events in window'); process.exit(1); }
simNow = (nextEv.T + LAT) * 1000; const tStart = simNow;
checkFrom = FROM != null ? FROM * 1000 : simNow + WARM * 1000;
const tEnd = UNTIL != null ? UNTIL * 1000 : Infinity;
let frames = 0, checkedFrames = 0, p = 0, evSeen = 0;
console.error(`replay from ${new Date(simNow).toISOString()} checking from ${new Date(checkFrom).toISOString()} code root ${ROOT}`);
const wall0 = Date.now();


while (simNow < tEnd && (nextEv || simNow < tStart + 1)) {
  while (p < plans.length && (plans[p].T + LAT) * 1000 <= simNow) { traffic.setPlan(plans[p].gates); p++; }
  while (nextEv && (nextEv.T + LAT) * 1000 <= simNow) {
    const P = parsePayload(nextEv.p, nextEv.T * 1000);
    if (simNow >= checkFrom - 1800e3) for (const a of P.aircraft) rawTruth(a, a.t);
    traffic.ingest(P, (nextEv.T + LAT) * 1000); evSeen++; await pull();
  }
  if (!nextEv) break;
  if (!booted && simNow - tStart > 30000) booted = true;
  traffic.update(simNow, DT); physics.resolve(traffic, DT); animStep(simNow); frames++;
  const chk = simNow >= checkFrom; if (chk) checkedFrames++;
  // ---------------- per aircraft
  const gnd = [], low = [];
  for (const tr of traffic.tracks.values()) {
    const D = tr.disp; if (!D.valid) continue; const veh = tr.vehicle;
    // faded out (a re-placement in progress, or not yet shown): not drawn -> not checked; its reappearance is a new start
    if (D.alpha != null && D.alpha < 0.5) { K.delete(tr.hex); tr._reset = null; continue; }
    const s = K.get(tr.hex); const T = tr.model && TYPES[tr.model.t];
    const near = Math.hypot(D.x, D.z) < 40000; const light = tr.info.category === 'A1' || (T && T.L < 20); const rotor = tr.info.category === 'A7';
    const bk = D.ground && T ? Math.max(1, (T.xMain ?? T.L * 0.47) - antOf(T)) : 0;
    const PX = D.x - Math.sin(D.hdg) * bk, PZ = D.z + Math.cos(D.hdg) * bk;
    const agl = D.y - GROUND_Y;
    if (chk && !veh && near) {
      // vertical placement
      if (D.ground && Math.abs(D.y - GROUND_Y) > 0.01) viol('vert.ground', tr, Math.abs(D.y - GROUND_Y), { y: +D.y.toFixed(2) });
      if (D.y < GROUND_Y - 0.01) viol('vert.below', tr, GROUND_Y - D.y);
      if (!D.ground && agl < 1 && D.gs < 50 * KT && !rotor) viol(inAirport(D.x, D.z) ? 'vert.float' : 'vert.float.other_airfield', tr, 50 - D.gs / KT, { agl: +agl.toFixed(2), gs: +(D.gs / KT).toFixed(0) });
      if (!D.ground && !rotor && agl < 60 && inAirport(D.x, D.z)) { const dc = nearRunwayCL(D.x, D.z, 4000); if (dc > 400) viol('vert.lowfly', tr, dc, { agl: +agl.toFixed(1), dRwyCL: Math.round(dc) }); }
      // wrong phase vs geometry
      const ph = tr.phase;
      if (D.ground && ['enroute', 'approach', 'departure', 'goaround'].includes(ph)) viol('phase.airphase_on_ground', tr, 1, { gs: +(D.gs / KT).toFixed(0) });
      if (D.ground && ph === 'final' && D.gs < 40 * KT) viol('phase.final_on_ground_slow', tr, 1, { gs: +(D.gs / KT).toFixed(0) });
      if (!D.ground && agl > 3 && ['gate', 'parked', 'taxi', 'pushback', 'holding', 'lineup', 'landing'].includes(ph)) viol('phase.gndphase_in_air', tr, agl, { agl: +agl.toFixed(1) });
      if (!D.ground && agl > 30 && ph === 'takeoff') viol('phase.takeoff_in_air_30m', tr, agl, { agl: +agl.toFixed(1) });
      if (D.ground && inAirport(D.x, D.z)) {
        const onR = runwaysAt(D.x, D.z).length > 0;
        if (ph === 'taxi' && onR && D.gs > 50 * KT) viol('phase.taxi_fast_on_runway', tr, D.gs / KT, { gs: +(D.gs / KT).toFixed(0) });
        if ((ph === 'landing' || ph === 'takeoff') && !runwaysAt(D.x, D.z, 45).length && D.gs > 30 * KT) viol('phase.rwyphase_off_runway', tr, nearRunwayCL(D.x, D.z), { gs: +(D.gs / KT).toFixed(0) });
        if (ph === 'gate' && tr.gate) { const dd = Math.hypot(D.x - tr.gate.w.x, D.z - tr.gate.w.z); if (dd > 30 + (T ? antOf(T) : 10)) viol('phase.gate_far_from_stand', tr, dd, { stand: tr.gate.name, d: Math.round(dd) }); }
        if (ph === 'pushback' && s && D.gs > 1.5) { const fx = Math.sin(D.hdg), fz = -Math.cos(D.hdg); const va = ((D.x - s.rx) * fx + (D.z - s.rz) * fz) / DT; if (va > 1.5) viol('phase.pushback_forward', tr, va, { v: +va.toFixed(1) }); }
        if (!onR && D.gs > 35 * KT && nearRunwayCL(D.x, D.z) > 100) viol('gnd.speed.taxi', tr, D.gs / KT, { gs: +(D.gs / KT).toFixed(0), dRwyCL: Math.round(nearRunwayCL(D.x, D.z)) });
      }
      // phase flicker
      const ph0 = s && s.ph; if (s && ph0 !== ph) { let H = phaseHist.get(tr.hex); if (!H) phaseHist.set(tr.hex, H = []); H.push(simNow); while (H.length && simNow - H[0] > 30000) H.shift(); if (H.length > 3) viol('phase.flicker', tr, H.length, { from: ph0, to: ph }); }
      // runway on final
      if (ph === 'final' && tr.m.rwy) { const f = finalRwy.get(tr.hex); if (f && f.rwy !== tr.m.rwy && simNow - f.t < 600000) viol('rwy.change.final', tr, 1, { from: f.rwy, to: tr.m.rwy }); finalRwy.set(tr.hex, { rwy: tr.m.rwy, t: simNow }); }
    }
    if (s && near && !veh) {
      const dx = PX - s.x, dz = PZ - s.z; const disp = Math.hypot(dx, dz); const vx = dx / DT, vz = dz / DT, vy = (D.y - s.y) / DT;
      // teleport / jump tests at the displayed reference point (the main-gear point used for the ground kinematics moves
      // by the antenna->main-gear offset when the air/ground state flips, which is not a displacement)
      const rdx = D.x - s.rx, rdz = D.z - s.rz; const pred = s.n0 >= 1 ? Math.hypot(rdx - s.rvx * DT, rdz - s.rvz * DT) : 0;
      const dh = wrapD((D.hdg - s.hdg) / DEG);
      if (chk) {
        if (pred > 20) viol('teleport', tr, pred, { d: +Math.hypot(rdx, rdz).toFixed(1), reset: tr._reset || null, g: D.ground ? 1 : 0 });
        else if (D.ground && s.g && pred > 1.0) viol('jump.gnd_1_20m', tr, pred, { d: +Math.hypot(rdx, rdz).toFixed(2), reset: tr._reset || null, towing: tr.ctl && tr.ctl.towing ? 1 : 0, v: +D.gs.toFixed(2), stand: tr.gate ? tr.gate.name : null, parkMode: tr.parkMode || null });
        else if (!D.ground && !s.g && pred > 5) viol('jump.air_5_20m', tr, pred, { d: +Math.hypot(rdx, rdz).toFixed(1), reset: tr._reset || null });
        if (Math.abs(dh) > 20) viol('hdg.flip', tr, Math.abs(dh), { dh: +dh.toFixed(0), g: D.ground ? 1 : 0, reset: tr._reset || null });
        // touchdown / liftoff transitions (display)
        if (D.ground && !s.g && tr.m.rwy !== undefined) {
          const R = RW.find(q => q.name === (tr.m.rwy || tr.arrRunway)); const ph = tr.phase;
          if (['landing', 'final'].includes(ph) || tr.m.phase === 'rollout') {
            if (!R) viol('rwy.td.norwy', tr, 1, { gs: +(D.gs / KT).toFixed(0) });
            else { const [aa, cc] = rwyCoords(R, D.x, D.z); const onIt = runwaysAt(D.x, D.z).includes(R);
              if (aa < 0) viol('rwy.td.before_thr', tr, -aa, { rwy: R.name, a: Math.round(aa), disp: R.disp });
              if (!onIt) viol('rwy.td.offrunway', tr, Math.abs(cc), { rwy: R.name, a: Math.round(aa), c: +cc.toFixed(1), physical: runwaysAt(D.x, D.z).map(q => q.name).join('/') || null }); }
          } else if (inAirport(D.x, D.z) && s.agl > 0.5) viol('vert.touch_nonlanding', tr, s.agl, { ph, mph: tr.m.phase });
        }
      }
      if (chk && s.n >= 2 && s.g === D.ground && pred <= 20) {
        const ax = (vx - s.vx) / DT, az = (vz - s.vz) / DT, ay = (vy - s.vy) / DT; const sp = Math.hypot(vx, vz); const hx = Math.sin(D.hdg), hz = -Math.cos(D.hdg);
        const yaw = Math.abs(dh) / DT;
        if (D.ground && inAirport(D.x, D.z)) {
          const along = ax * hx + az * hz, lat = -ax * hz + az * hx; const onR = runwaysAt(D.x, D.z).length > 0;
          if (Math.abs(along) > (onR ? EXC.gAccRoll : EXC.gAccTaxi)) viol(onR ? 'gnd.acc.runway' : 'gnd.acc.taxi', tr, Math.abs(along), { a: +along.toFixed(2), v: +sp.toFixed(1) });
          if (Math.abs(lat) > EXC.gLat) viol('gnd.lat', tr, Math.abs(lat), { a: +lat.toFixed(2), v: +sp.toFixed(1) });
          if (s.ax != null && sp > 0.5) { const j = Math.hypot(ax - s.ax, az - s.az) / DT; if (j > EXC.gJerk) viol('gnd.jerk', tr, j, { j: +j.toFixed(1), v: +sp.toFixed(1) }); }
          if (yaw > EXC.gYaw) viol('gnd.yaw', tr, yaw, { yaw: +yaw.toFixed(0), v: +sp.toFixed(1) });
          const vAlong = vx * hx + vz * hz;
          if (sp > 1) { let sl = Math.abs(wrapD(Math.atan2(vx, -vz) / DEG - D.hdg / DEG)); const rev = sl > 90; sl = Math.min(sl, 180 - sl); if (sl > EXC.slip) viol('gnd.slip', tr, sl, { slip: +sl.toFixed(0), v: +sp.toFixed(1) }); if (rev && vAlong < -0.5 && tr.m.phase !== 'pushback' && tr.phase !== 'pushback') viol('gnd.reverse', tr, -vAlong, { v: +vAlong.toFixed(1), mph: tr.m.phase }); }
          if (sp < 0.2 && yaw > 2.5) viol('gnd.spin', tr, yaw, { yaw: +yaw.toFixed(1) });
          if (sp > 0.15 && Math.abs(D.gs) < 0.01) viol('gnd.slide', tr, sp, { v: +sp.toFixed(2), towing: tr.ctl && tr.ctl.towing ? 1 : 0, stand: tr.gate ? tr.gate.name : null, dist: tr.parkPos ? +Math.hypot(tr.parkPos[0] - D.x, tr.parkPos[1] - D.z).toFixed(1) : null });
        } else if (!D.ground && Math.hypot(D.x, D.z) < 40000 && !rotor) {
          const tx = sp > 1 ? vx / sp : hx, tz = sp > 1 ? vz / sp : hz; const lf = light ? 1.7 : 1;
          const along = Math.abs(ax * tx + az * tz), lat = Math.abs(-ax * tz + az * tx) / lf;
          if (along > EXC.aAcc) viol('air.acc', tr, along, { a: +along.toFixed(2) });
          if (lat > EXC.aLat) viol('air.lat', tr, lat, { a: +lat.toFixed(2) });
          if (Math.abs(ay) > EXC.aVacc) viol('air.vacc', tr, Math.abs(ay), { a: +ay.toFixed(2), agl: +agl.toFixed(0) });
          if (yaw / (light ? 1.8 : 1) > EXC.aTurn) viol('air.turn', tr, yaw, { turn: +yaw.toFixed(1) });
          if (Math.abs(vy) * 196.85 > 8000 && D.y < 3100) viol('air.vs', tr, Math.abs(vy) * 196.85, { fpm: Math.round(vy * 196.85), agl: +agl.toFixed(0) });
        }
      }
      K.set(tr.hex, { x: PX, z: PZ, rx: D.x, rz: D.z, rvx: rdx / DT, rvz: rdz / DT, n0: (s.n0 || 0) + 1, y: D.y, vx, vz, vy, hdg: D.hdg, g: D.ground, n: s.g === D.ground ? s.n + 1 : 1, ax: s.g === D.ground && s.n >= 2 ? (vx - s.vx) / DT : null, az: s.g === D.ground && s.n >= 2 ? (vz - s.vz) / DT : null, ph: tr.phase, agl });
    } else K.set(tr.hex, { x: PX, z: PZ, rx: D.x, rz: D.z, rvx: 0, rvz: 0, n0: 0, y: D.y, vx: 0, vz: 0, vy: 0, hdg: D.hdg, g: D.ground, n: 1, ax: null, az: null, ph: tr.phase, agl });
    tr._reset = null;
    // bodies for the surface checks
    if (!veh && T && Math.abs(D.x) < 3200 && Math.abs(D.z) < 3200) {
      const B = pose(tr); if (!B) continue;
      if (D.ground) gnd.push(B); else if (agl < 15) low.push(B);
    }
  }
  for (const [hex] of K) if (!traffic.tracks.has(hex)) { K.delete(hex); surfCache.delete(hex); }
  if (frames % 600 === 0) pairCache.clear();
  if (TRACE && frames % 5 === 0) { const tr = traffic.tracks.get(TRACE); if (tr && tr.disp.valid) { const D = tr.disp, d = tr._dbg || {}; const f2 = (v) => v == null ? '-' : (+v).toFixed(1);
    console.error(iso(simNow), tr.phase, tr.m.phase, 'disp', f2(D.x), f2(D.z), 'y', f2(D.y), 'hdg', f2(D.hdg / DEG), 'v', f2(tr.ctl && tr.ctl.v), 'g', D.ground ? 1 : 0, '| tgt', f2(d.ox), f2(d.oz), 'tv', f2(Math.hypot(d.ovx || 0, d.ovz || 0)), d.stop ? 'STOP' : '', 'ex', f2(d.ex), '| park', tr.parkPos ? f2(tr.parkPos[0]) + ',' + f2(tr.parkPos[1]) + '@' + f2((tr.parkHdg ?? 0) / DEG) : '-', tr.parkMode || '', tr.gate ? tr.gate.name : '-', tr.ctl && tr.ctl.towing ? 'TOW' : '', tr.stale ? 'STALE' : '', tr.gate && tr.gate.dock && tr.parkPos ? 'dockPoseVsPark ' + f2(Math.hypot(poseST(tr).nose[0] - tr.gate.dock.nose[0], poseST(tr).nose[1] - tr.gate.dock.nose[1])) + 'm' : '', 'last', tr.last ? f2((simNow - tr.last.t) / 1000) + 's gs' + f2(tr.last.gs) + (tr.last.push ? ' PUSH' : '') + (tr.last.ground ? ' G' : ' A') : ''); } }
  if (!chk || FAST) { simNow += DT * 1000; continue; }
  // ---------------- surface: pavement, buildings (cached per aircraft while its displayed pose is unchanged)
  for (const B of gnd) {
    const tr = B.tr; const key = B.key = Math.round(tr.disp.x * 20) + ',' + Math.round(tr.disp.z * 20) + ',' + Math.round(tr.disp.hdg * 1000) + ',' + B.S.T.L;
    let C = surfCache.get(tr.hex);
    if (!C || C.key !== key) {
      C = { key, om: 0, ou: 0, worst: null, nb: 0, bk: null };
      for (const gp of B.S.gear) { const q = B.W(gp[0], gp[1]); if (!pavedMask(q[0], q[1])) { C.om++; C.worst = q; } if (!pavedAll(q[0], q[1])) { C.ou++; C.wu = q; } }
      for (const q0 of B.S.pts) { const q = B.W(q0[0], q0[1]); if (building(q[0], q[1])) { C.nb++; C.bk = C.bk || q0[4]; } }
      surfCache.set(tr.hex, C);
    }
    if (C.om) viol('offpave.mask', tr, C.om, { gearOff: C.om, gx: +C.worst[0].toFixed(1), gz: +C.worst[1].toFixed(1) });
    if (C.ou) { viol('offpave.union', tr, C.ou, { gearOff: C.ou, gx: +C.wu[0].toFixed(1), gz: +C.wu[1].toFixed(1), v: +tr.disp.gs.toFixed(1) }); const ck = Math.round(C.wu[0] / 25) * 25 + ',' + Math.round(C.wu[1] / 25) * 25; let cl = offCells.get(ck); if (!cl) offCells.set(ck, cl = { frames: 0, hex: new Set(), moving: 0 }); cl.frames++; cl.hex.add(tr.info.flight || tr.hex); if (tr.disp.gs > 0.3) cl.moving++; }
    if (C.nb) viol('building', tr, C.nb, { pts: C.nb, part: C.bk, moving: tr.disp.gs > 0.3 ? 1 : 0, stand: tr.gate ? tr.gate.name : null });
  }
  // ---------------- aircraft pairs
  for (let i = 0; i < gnd.length; i++) for (let j = i + 1; j < gnd.length; j++) {
    const A = gnd[i], B = gnd[j]; if (Math.hypot(A.c[0] - B.c[0], A.c[1] - B.c[1]) > (A.S.reach + B.S.reach) / 2 + 10) continue;
    const pk = A.tr.hex + '~' + B.tr.hex; let pc = pairCache.get(pk); if (!pc || pc.a !== A.key || pc.b !== B.key) pairCache.set(pk, pc = { a: A.key, b: B.key, c: clearance(A, B) }); const c = pc.c; const still = A.tr.disp.gs < 0.2 && B.tr.disp.gs < 0.2;
    const pair = [A.tr.info.flight || A.tr.hex, B.tr.info.flight || B.tr.hex].sort().join('~'); const key = [A.tr.hex, B.tr.hex].sort().join('~');
    const ex = { key, pair, other: B.tr.hex, types: (A.tr.info.icao || '?') + '/' + (B.tr.info.icao || '?'), phases: A.tr.phase + '/' + B.tr.phase, stands: (A.tr.gate ? A.tr.gate.name : '-') + '/' + (B.tr.gate ? B.tr.gate.name : '-'), stale: (A.tr.stale ? 1 : 0) + (B.tr.stale ? 1 : 0) };
    if (c < 0) viol('overlap.gnd', null, -c, { ...ex, area: -c, still: still ? 1 : 0 }, A.tr.disp.x, A.tr.disp.z);
    else if (still) { const code = [A.S.code, B.S.code].sort().pop(); const need = code <= 'B' ? 3 : code === 'C' ? 4.5 : 7.5; if (c < need) viol('clear.stand', null, need - c, { ...ex, clear: +c.toFixed(2), need }, A.tr.disp.x, A.tr.disp.z); }
    else if (c < 1) viol('clear.taxi', null, 1 - c, { ...ex, clear: +c.toFixed(2) }, A.tr.disp.x, A.tr.disp.z);
  }
  for (const L of low) for (const B of gnd) { if (Math.hypot(L.c[0] - B.c[0], L.c[1] - B.c[1]) > (L.S.reach + B.S.reach) / 2 + 5) continue; const c = clearance(L, B); const vs = L.tr.disp.y - GROUND_Y - (B.S.T.Hc + B.S.T.R) ; if (c < 0 && vs < 6) viol('overlap.lowair', null, -c, { key: L.tr.hex + '~' + B.tr.hex, pair: (L.tr.info.flight || L.tr.hex) + '~' + (B.tr.info.flight || B.tr.hex), vsep: +vs.toFixed(1), phases: L.tr.phase + '/' + B.tr.phase }, L.tr.disp.x, L.tr.disp.z); }
  // ---------------- jet bridges
  for (const g of gates) {
    if (!g.bridge) continue;
    for (const b of g.bridges) {
      const k = bridgeK(g, b);
      let BB = b._inv; const bkey = k.toFixed(3) + '|' + (g.acType || '') + '|' + JSON.stringify(g.dock || null);
      if (!BB || BB.bkey !== bkey) { BB = b._inv = bridgeBoxes(g, b, k); BB.bkey = bkey; let cx = 0, cz = 0; for (const bx of BB.boxes) { cx += bx.c[0]; cz += bx.c[1]; } cx /= BB.boxes.length; cz /= BB.boxes.length; let r = 0; for (const bx of BB.boxes) for (const q of boxPoly(bx)) r = Math.max(r, Math.hypot(q[0] - cx, q[1] - cz)); BB.cc = [cx, cz]; BB.r = r; BB.ver = (BB.ver || 0) + 1; }
      const ot = occ.get(g.name) || null;
      // aircraft inside the bridge: SAT of each planform piece against each bridge box, then 3-D point test
      for (const A of gnd) {
        if (Math.hypot(A.c[0] - BB.cc[0], A.c[1] - BB.cc[1]) > A.S.reach / 2 + BB.r + 2) continue;
        const own = ot && ot === A.tr && k > 0.05; const ck = A.key + '|' + bkey + '|' + (own ? 1 : 0);
        let H = b._hit && b._hit.get(A.tr.hex);
        if (!H || H.ck !== ck) {
          H = { ck, n: 0, hit: null }; const PA = worldPolys(A);
          for (const bx of BB.boxes) {
            if (own && bx.part === 'cab') continue; // the docked cab touches its own aircraft (bellows) by design
            const bp = boxPoly(bx);
            PA.forEach((pa, pi) => {
              if (sepAxis(pa, bp)) return;
              for (const q0 of A.S.pts) { if (q0[5] !== pi) continue; if (q0[3] < bx.lo || q0[2] > bx.hi) continue; const q = A.W(q0[0], q0[1]); if (!inBox(bx, q[0], q[1])) continue; H.n++; if (!H.hit || (q0[4] === 'fus' && H.hit.kind !== 'fus')) H.hit = { kind: q0[4], part: bx.part }; }
            });
          }
          if (!b._hit) b._hit = new Map(); b._hit.set(A.tr.hex, H);
        }
        if (H.n) viol('bridge.hit.' + H.hit.kind, A.tr, H.n, { stand: g.name, bridge: b.door, part: H.hit.part, k: +k.toFixed(2), own: own ? 1 : 0, pts: H.n, phase: A.tr.phase, v: +A.tr.disp.gs.toFixed(1) });
      }
      if (k > 0.5) {
        // door target vs the displayed door of the occupant
        const tgt = [BB.door[0], BB.door[2]];
        const Bo = ot && ot.disp && ot.disp.valid && traffic.tracks.has(ot.hex) ? gnd.find(q => q.tr === ot) : null;
        if (!Bo) { let nearest = 1e9; for (const A of gnd) { if (Math.hypot(A.c[0] - tgt[0], A.c[1] - tgt[1]) > A.S.reach) continue; const d = doorW(A, b.door); nearest = Math.min(nearest, Math.hypot(d[0] - tgt[0], d[1] - tgt[1])); } if (nearest > 10) viol('bridge.orphan', ot || null, nearest, { key: g.name + '/' + b.door, stand: g.name, bridge: b.door, k: +k.toFixed(2), occupant: ot ? ot.hex : null, removed: ot && ot.removed ? 1 : 0, nearestDoor: nearest > 1e8 ? null : +nearest.toFixed(1) }, tgt[0], tgt[1]); }
        else {
          const dW = doorW(Bo, b.door); const e = Math.hypot(dW[0] - tgt[0], dW[1] - tgt[1]);
          if (e > 1.5) {
            const pp = Bo.tr.parkPos; let parkErr = null, dispPark = null; if (pp) { const Tq = Bo.S.T; const f = hdgVec(Bo.tr.parkHdg ?? Bo.tr.disp.hdg), r = [-f[1], f[0]], k0 = antOf(Tq); const nose = [pp[0] + f[0] * k0, pp[1] + f[1] * k0]; const Bp = { S: Bo.S, r, W: (x, y) => [nose[0] - f[0] * x + r[0] * y, nose[1] - f[1] * x + r[1] * y] }; const dP = doorW(Bp, b.door); parkErr = +Math.hypot(dP[0] - tgt[0], dP[1] - tgt[1]).toFixed(2); dispPark = +Math.hypot(pp[0] - Bo.tr.disp.x, pp[1] - Bo.tr.disp.z).toFixed(2); }
            viol('bridge.misdock', Bo.tr, e, { stand: g.name, bridge: b.door, err: +e.toFixed(1), acType: g.acType, model: Bo.tr.model ? Bo.tr.model.t : null, parkMode: Bo.tr.parkMode || null, parkErr, dispPark, physOff: Bo.tr.physOff ? +Math.hypot(...Bo.tr.physOff).toFixed(2) : 0, towing: Bo.tr.ctl && Bo.tr.ctl.towing ? 1 : 0, v: +Bo.tr.disp.gs.toFixed(2), phase: Bo.tr.phase });
          }
          if (Bo.tr.disp.gs > 0.3) viol('bridge.attached.moving', Bo.tr, Bo.tr.disp.gs, { stand: g.name, bridge: b.door, k: +k.toFixed(2), v: +Bo.tr.disp.gs.toFixed(2), phase: Bo.tr.phase, mphase: Bo.tr.m.phase });
        }
      }
    }
  }
  simNow += DT * 1000;
  if (frames % 6000 === 0) console.error(iso(simNow), 'frames', frames, 'tracks', traffic.tracks.size, 'wall', ((Date.now() - wall0) / 1000).toFixed(0) + 's');
}

// ---------------------------------------------------------------- truth comparison (events within the checked window)
const inWin = (t) => t >= checkFrom && t <= simNow - 120000;
const EV = traffic.events.filter(e => inWin(e.t));
const byKind = (k) => EV.filter(e => e.kind === k);
const match = (list, ev, tol = 120000) => { const out = { matched: 0, rwyAgree: 0, rwyDiff: [], missed: [], extra: [] }; const used = new Set();
  for (const T of list.filter(q => inWin(q.t))) { const e = ev.find((q, i) => !used.has(i) && q.hex === T.hex && Math.abs(q.t - T.t) < tol); if (!e) { out.missed.push({ ...T, t: iso(T.t) }); continue; } used.add(ev.indexOf(e)); out.matched++; if (!T.rwy || e.rwy === T.rwy) out.rwyAgree++; else out.rwyDiff.push({ hex: T.hex, flight: T.flight, t: iso(T.t), truth: T.rwy, engine: e.rwy, how: e.how || null }); }
  ev.forEach((e, i) => { if (!used.has(i)) out.extra.push({ hex: e.hex, flight: e.flight, t: iso(e.t), rwy: e.rwy || null, how: e.how || null }); }); return out; };
const truthCmp = { landings: match(truth.landings, byKind('touchdown')), takeoffs: match(truth.takeoffs, byKind('liftoff')), goarounds: match(truth.goarounds, byKind('go-around'), 240000),
  truthN: { landings: truth.landings.filter(q => inWin(q.t)).length, takeoffs: truth.takeoffs.filter(q => inWin(q.t)).length, goarounds: truth.goarounds.filter(q => inWin(q.t)).length },
  engineN: Object.fromEntries(['touchdown', 'liftoff', 'go-around', 'runway-change', 'rejected-takeoff', 'takeoff-roll', 'in-block', 'off-block', 'exit'].map(k => [k, byKind(k).length])) };
for (const [k, list] of [['rwy.truth.landing_missed', truthCmp.landings.missed], ['rwy.truth.landing_wrong_rwy', truthCmp.landings.rwyDiff], ['rwy.truth.landing_extra', truthCmp.landings.extra], ['rwy.truth.takeoff_missed', truthCmp.takeoffs.missed], ['rwy.truth.takeoff_wrong_rwy', truthCmp.takeoffs.rwyDiff], ['rwy.truth.takeoff_extra', truthCmp.takeoffs.extra], ['rwy.truth.goaround_missed', truthCmp.goarounds.missed], ['rwy.truth.goaround_extra', truthCmp.goarounds.extra]])
  V.set(k, { frames: list.length, eps: list.length, who: new Map(list.map((q, i) => [q.hex + i, { n: 1, max: 1, ex: q }])), worst: [] });

const engineEvents = EV.filter(e => ['touchdown', 'liftoff', 'go-around', 'runway-change', 'rejected-takeoff'].includes(e.kind)).map(e => ({ ...e, t: iso(e.t) }));
const report = { engineEvents, meta: { stream: STREAM, root: ROOT, from: new Date(checkFrom).toISOString(), until: new Date(simNow).toISOString(), warm: WARM, frames, checkedFrames, dt: DT, wallS: Math.round((Date.now() - wall0) / 1000), counters: traffic.counters, delay: Math.round(traffic.delay) }, truth: truthCmp, classes: {} };
for (const [cls, v] of [...V.entries()].sort()) {
  const who = [...v.who.values()].sort((a, b) => b.max - a.max);
  const aircraft = new Set([...v.who.keys()]).size;
  report.classes[cls] = { frames: v.frames, episodes: v.eps, keys: aircraft, worst: who.slice(0, 12).map(w => ({ ...w.ex, frames: w.n })), longest: who.slice().sort((a, b) => b.n - a.n).slice(0, 6).map(w => ({ ...w.ex, frames: w.n })) };
}
report.offpaveCells = [...offCells.entries()].sort((a, b) => b[1].hex.size - a[1].hex.size || b[1].frames - a[1].frames).slice(0, 25).map(([k, v]) => { const [x, z] = k.split(',').map(Number); const ll = toLL(x, z); return { x, z, lat: +ll[0].toFixed(6), lon: +ll[1].toFixed(6), frames: v.frames, movingFrames: v.moving, aircraft: v.hex.size, who: [...v.hex].slice(0, 8) }; });
fs.writeFileSync(OUTF, JSON.stringify(report, null, 1));
console.log(`${OUTF}: checked ${checkedFrames} frames (${(checkedFrames * DT / 3600).toFixed(2)} h) in ${report.meta.wallS}s`);
for (const [cls, c] of Object.entries(report.classes)) console.log(cls.padEnd(28), String(c.frames).padStart(8), 'frames', String(c.episodes).padStart(6), 'episodes', String(c.keys).padStart(5), 'keys');
